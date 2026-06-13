"""Character ABILITY data -- the AP/ability-mastery half of the #5 save editor.

Two pieces, both provenance-clean (ship/commit nothing -- the same live-read pattern as :mod:`ff9mapkit.itemstats`
and :mod:`ff9mapkit.keyitems`):

* a mod-agnostic **id<->token codec** (``AA:X`` active / ``SA:X`` support <-> the integer ``abil_id`` the save
  stores in ``players[].pa_extended[].id``), mirroring Memoria's ``CsvParser.AnyAbility`` / ``ff9abil``; and
* a best-effort **name + AP-requirement** lookup, read LIVE from the install's per-character pool CSVs
  ``<install>/StreamingAssets/Data/Characters/Abilities/<Preset>.csv`` (rows ``AA:101;40;# Flee`` --
  token ; AP-to-master ; ``# name``).

★ The codec ALWAYS works (pure arithmetic). The name/AP lookup is BEST-EFFORT: it reads the base-game CSVs, so
an id that a mod (e.g. Moguri) introduced -- not present in the base pool -- resolves to ``None`` and the editor
falls back to the raw ``AA:X``/``SA:X`` token. The save's own ``pa_extended`` is the source of truth for which
abilities a character has; this module only enriches it with names + the master threshold.

The id<->token math (Memoria ``ff9abil``/``CsvParser.AnyAbility``): each ability has a global integer ``abil_id``;
``mod = abil_id % 256`` is < 192 for ACTIVE (``AA``) and >= 192 for SUPPORT (``SA``); ``pool = abil_id // 256``.
For ``AA:X`` -> ``abil_id = (X // 192) * 256 + X % 192``; for ``SA:X`` -> ``(X // 64) * 256 + X % 64 + 192``.

Usage::

    from ff9mapkit import abilities
    abilities.encode_token("AA:108")          # -> 108
    abilities.decode_token(192)               # -> "SA:0"
    abilities.name_of(108)                    # -> "Thievery"  (or None if the install isn't reachable)
    abilities.ap_required(0, 108)             # -> 100  (Zidane preset=0; or None)
    abilities.resolve(0, "Thievery")          # -> 108
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# CharacterPresetId (Memoria.Data.Characters.CharacterPresetId) -> the per-pool CSV basename. menu_type in the
# save == this preset id. Only 0-15 ship a pool CSV (16+ are stage doubles with no learnable set).
PRESET_NAMES = {0: "Zidane", 1: "Vivi", 2: "Garnet", 3: "Steiner", 4: "Freya", 5: "Quina", 6: "Eiko",
                7: "Amarant", 8: "Cinna1", 9: "Cinna2", 10: "Marcus1", 11: "Marcus2", 12: "Blank1",
                13: "Blank2", 14: "Beatrix1", 15: "Beatrix2"}

_AP_MAX = 255                                              # the old-format `pa` cell is a Byte; AP-to-master <= 255
_ROW_RE = re.compile(r"#\s*(.+?)\s*$")                     # the trailing `# Name` comment on a pool-CSV row

_POOL_CACHE: dict = {}      # menu_type -> [Ability, ...] (or False = tried + unavailable)
_GLOBAL_NAMES = None        # None = not built; dict {abil_id: name} unioned across every preset pool


# --- the mod-agnostic id <-> token codec (pure arithmetic; always available) ----------------------

def kind_of(abil_id: int) -> str:
    """``"AA"`` (active) if ``abil_id % 256 < 192`` else ``"SA"`` (support) -- the engine's split (ff9abil)."""
    return "AA" if abil_id % 256 < 192 else "SA"


def decode_token(abil_id: int) -> str:
    """An integer ``abil_id`` -> its ``"AA:X"`` / ``"SA:X"`` token (the inverse of :func:`encode_token`)."""
    if isinstance(abil_id, bool) or not isinstance(abil_id, int):
        raise TypeError(f"abil_id must be an int (got {type(abil_id).__name__})")
    pool, mod = divmod(abil_id, 256)
    if mod < 192:
        return f"AA:{pool * 192 + mod}"
    return f"SA:{pool * 64 + (mod - 192)}"


def encode_token(token) -> int:
    """An ``"AA:X"`` / ``"SA:X"`` token (or a plain integer / digit string) -> the integer ``abil_id``. Mirrors
    Memoria ``CsvParser.AnyAbility``. Raises ValueError on a malformed token."""
    if isinstance(token, bool):
        raise ValueError("ability cannot be a boolean")
    if isinstance(token, int):
        if token < 0:
            raise ValueError(f"abil_id cannot be negative (got {token})")
        return token
    s = str(token).strip()
    m = re.fullmatch(r"(AA|SA):(-?\d+)", s, re.IGNORECASE)
    if m:
        kind, x = m.group(1).upper(), int(m.group(2))
        if x < 0:
            raise ValueError(f"ability index cannot be negative in {token!r}")
        if kind == "AA":
            return (x // 192) * 256 + x % 192
        return (x // 64) * 256 + x % 64 + 192
    if re.fullmatch(r"\d+", s):
        return int(s)
    raise ValueError(f"not an ability token: {token!r} (expected AA:X, SA:X, or a numeric abil_id)")


# --- best-effort name + AP-requirement, read live from the install's pool CSVs ---------------------

@dataclass(frozen=True)
class Ability:
    """One row of a character's learnable-ability pool CSV."""
    index: int                                            # row position (== the old-format `pa` array index)
    abil_id: int                                          # the global integer id stored in pa_extended
    token: str                                            # "AA:X" / "SA:X"
    kind: str                                             # "AA" | "SA"
    ap_req: int                                           # AP needed to master (the row's 2nd column)
    name: "str | None"                                    # the row's `# comment` name (None if absent)


def _norm(s) -> str:
    return "".join(c for c in str(s).lower() if c.isalnum())


def pool_for_preset(menu_type: int, game=None) -> list:
    """The ordered learnable-ability pool for a preset (``menu_type``), read live from
    ``<install>/.../Abilities/<Preset>.csv`` and cached. ``[]`` if the install/file isn't reachable or the preset
    has no pool (16+)."""
    if menu_type is None:                                 # no preset known (e.g. a save missing info.menu_type)
        return []                                         # -> no base pool; callers fall back to token/AP_CAP
    if menu_type in _POOL_CACHE:
        return _POOL_CACHE[menu_type] or []
    name = PRESET_NAMES.get(int(menu_type))
    if name is None:
        _POOL_CACHE[menu_type] = False
        return []
    try:
        from .config import find_game_path
        p = find_game_path(game) / "StreamingAssets" / "Data" / "Characters" / "Abilities" / f"{name}.csv"
        text = p.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:                                      # noqa: BLE001 -- install not reachable -> degrade
        _POOL_CACHE[menu_type] = False
        return []
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split(";")
        if len(parts) < 2:
            continue
        try:
            abil_id = encode_token(parts[0].strip())
            ap_req = int(parts[1].strip())
        except ValueError:
            continue
        m = _ROW_RE.search(s)
        nm = m.group(1).strip() if m else None
        out.append(Ability(index=len(out), abil_id=abil_id, token=decode_token(abil_id),
                            kind=kind_of(abil_id), ap_req=ap_req, name=nm or None))
    _POOL_CACHE[menu_type] = out or False
    return out


def _pool_index(menu_type: int, game=None) -> dict:
    """``{abil_id: Ability}`` for a preset (last row wins on a dup id)."""
    return {a.abil_id: a for a in pool_for_preset(menu_type, game)}


def _global_names(game=None) -> dict:
    """``{abil_id: name}`` unioned across every preset pool (for naming an id when the preset is unknown)."""
    global _GLOBAL_NAMES
    if _GLOBAL_NAMES is not None:
        return _GLOBAL_NAMES
    names: dict = {}
    for mt in PRESET_NAMES:
        for a in pool_for_preset(mt, game):
            if a.name and a.abil_id not in names:
                names[a.abil_id] = a.name
    _GLOBAL_NAMES = names
    return names


def name_of(abil_id: int, menu_type=None, game=None) -> "str | None":
    """The display name for an ``abil_id`` -- from the given preset's pool if ``menu_type`` is set, else from the
    global union. ``None`` if unknown (a modded id not in the base pools, or the install isn't reachable)."""
    if menu_type is not None:
        a = _pool_index(menu_type, game).get(int(abil_id))
        if a is not None and a.name:
            return a.name
    return _global_names(game).get(int(abil_id))


def ap_required(menu_type, abil_id: int, game=None) -> "int | None":
    """The AP needed to master ``abil_id`` for a preset, or ``None`` if that id isn't in the (base) pool."""
    a = _pool_index(menu_type, game).get(int(abil_id))
    return a.ap_req if a is not None else None


def resolve(menu_type, ability, game=None) -> int:
    """An ability NAME / ``AA:X`` / ``SA:X`` / numeric id -> the integer ``abil_id``. A token / id is decoded
    directly (mod-agnostic, no install needed). A NAME is matched case/space/punct-insensitively against the
    preset's pool first, then the global union. Raises ValueError on an unknown name."""
    if isinstance(ability, bool):
        raise ValueError("ability cannot be a boolean")
    if isinstance(ability, int):
        return encode_token(ability)
    s = str(ability).strip()
    if re.fullmatch(r"(?:AA|SA):-?\d+|\d+", s, re.IGNORECASE):
        return encode_token(s)
    key = _norm(s)
    if menu_type is not None:
        for a in pool_for_preset(menu_type, game):
            if a.name and _norm(a.name) == key:
                return a.abil_id
    for aid, nm in _global_names(game).items():           # then any character's pool
        if _norm(nm) == key:
            return aid
    raise ValueError(f"unknown ability {ability!r} (use an AA:X / SA:X token or a numeric id, or run "
                     "`ff9mapkit items --abilities` to list names)")


def available(game=None) -> bool:
    """True if at least one preset pool CSV could be read (so ability NAMES/AP are live)."""
    return any(pool_for_preset(mt, game) for mt in (0, 1, 2))


def _reset_cache():                                       # for tests
    global _GLOBAL_NAMES
    _POOL_CACHE.clear()
    _GLOBAL_NAMES = None
