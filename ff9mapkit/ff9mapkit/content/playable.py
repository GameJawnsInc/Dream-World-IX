"""``[[playable]]`` -- define a genuine 13th (or 14th..) PLAYABLE character: a NEW ``CharacterId`` that joins
the party ALONGSIDE the 12 canon characters (NOT a reskin of an existing slot). Tier C of the PC/party map.

★ ZERO-DLL, save-safe (memory ``project-ff9-13th-character``; every claim verified against the Memoria source).
The engine model:
  * ``FF9StateGlobal.player`` is a ``Dictionary<CharacterId, PLAYER>`` and ``FF9Play_Init`` allocates a PLAYER
    for **every loaded CharacterParameters row** -- so a ``CharacterParameters.csv`` row with ``Id=12`` (the
    ALLOCATOR) brings the 13th character into existence. The BaseStats / CharacterParameters coverage gates are
    MINIMUMS (``for i < 12``), so an extra id-12 row PASSES; the menu / battle / equip UIs all iterate the
    dictionary, so the 13th appears for free.
  * The menu/battle NAME comes from a ``CharacterDefaultName <id> <SYM> <name>`` DictionaryPatch directive
    (``DataPatchers`` patches ``CharacterNamesFormatter.DefaultNamesByLang`` at launch, no 0-11 clamp).
  * Recruit is pure ``.eb``: ``B_PARTYADD`` (op 0x6D) with the new id -> the party. Author it with ``recruit =
    true`` here, or ``[party] add = ["<name>"]`` / ``[party] add = [12]``.

This block DEFINES the character (mod-global -- put it on the ENTRY field, like ``[[equipment]]``). It clones a
base character 0-11 (``borrow``) for the stat/identity/model bytes -- so a minimal ``[[playable]]`` is a fully
working, fightable, save-persistent party member -- then applies the author's overrides on top.

    [[playable]]
    id     = 12          # optional; default 12 (the first free slot). Band 12-15 (12 is in-game-proven).
    name   = "Marcus"    # the menu/battle name -> CharacterDefaultName for every language
    borrow = "vivi"      # a base character 0-11 to clone stats / command-set / equip-set / battle-model from
    recruit = true       # optional: also ADD this character to the party at THIS field's load (a one-block proof)
    names  = { jp = "マーカス" }              # optional per-language names (unlisted langs fall back to `name`)
    stats  = { strength = 24, magic = 30 }   # optional BaseStats overrides (same keys as [[character]])
    params = { equip_set = "vivi" }          # optional CharacterParameters overrides (same keys as [[character_param]])

Caveats carried by the recon (do NOT open the in-game name-entry screen for the custom char -- its name comes
from the DictionaryPatch; and FF9 renders only the party LEADER in fields, so the 13th shows in the menu/battle,
not as a walking field follower). See ``project-ff9-13th-character`` and ``project-ff9-pc-party-system``.
"""
from __future__ import annotations

from ..config import LANGS
from ..battle import characterdelta as _cd


class PlayableError(ValueError):
    pass


def _lang_symbol(lang: str) -> str:
    """A kit lang code (lowercase ``us``/``jp``/...) -> the engine ``DefaultNamesByLang`` symbol (uppercase
    ``US``/``JP``/...). The 7 symbols are US/UK/JP/GR/FR/IT/ES (``CharacterNamesFormatter.cs``)."""
    return str(lang).upper()


def _default_name_keyword(nid: int) -> str:
    """A UNIQUE ``NameKeyword`` for the custom char. The engine registers ``NameKeyword -> Id``
    (``RegisterCustomNameKeywork``), so reusing the donor's keyword would collide with the donor's own text tag
    -> generate a distinct 4-char token (matches the CSV String column)."""
    return f"CU{nid:02d}"          # e.g. CU12 -- distinct from every base keyword (ZDNE/VIVI/...)


def parse_playable(entry, *, n: int = 0) -> dict:
    """One ``[[playable]]`` table -> a normalized spec, or raise :class:`PlayableError`. Pure (no install):
    ``{id, name, names:{SYM: str for every language}, borrow_id, stats:{}, params:{}, recruit:bool}``."""
    if not isinstance(entry, dict):
        raise PlayableError(f"[[playable]] #{n} must be a table (id / name / borrow ...)")
    try:
        nid = _cd._resolve_new_char_id(entry.get("id", _cd.CUSTOM_CHAR_MIN), "[[playable]]")
    except _cd.CharacterDeltaError as ex:
        raise PlayableError(str(ex))
    name = entry.get("name")
    if not (isinstance(name, str) and name.strip()):
        raise PlayableError(f"[[playable]] id {nid} needs a 'name' (the menu/battle name)")
    name = " ".join(name.split())
    borrow = entry.get("borrow")
    if borrow is None:
        raise PlayableError(f"[[playable]] id {nid} needs a 'borrow' (a base character 0-11 to clone from)")
    try:
        borrow_id = _cd._resolve_char_id(borrow)
    except _cd.CharacterDeltaError:
        raise PlayableError(f"[[playable]] id {nid}: borrow {borrow!r} is not a base character (a name "
                            f"Zidane..Beatrix or a 0-11 id)")
    # per-language names: `name` for every symbol, then overridden by `names = { us = ..., jp = ... }`
    names = {_lang_symbol(l): name for l in LANGS}
    raw_names = entry.get("names")
    if raw_names is not None:
        if not isinstance(raw_names, dict):
            raise PlayableError(f"[[playable]] id {nid}: 'names' must be a table (e.g. names = {{ jp = \"...\" }})")
        for k, v in raw_names.items():
            sym = _lang_symbol(k)
            if sym not in names:
                raise PlayableError(f"[[playable]] id {nid}: unknown language {k!r} in 'names' "
                                    f"(use one of {', '.join(sorted(LANGS))})")
            if not (isinstance(v, str) and v.strip()):
                raise PlayableError(f"[[playable]] id {nid}: names.{k} must be a non-empty string")
            names[sym] = " ".join(v.split())
    stats = entry.get("stats") or {}
    params = entry.get("params") or {}
    if not isinstance(stats, dict):
        raise PlayableError(f"[[playable]] id {nid}: 'stats' must be a table (strength = 24, ...)")
    if not isinstance(params, dict):
        raise PlayableError(f"[[playable]] id {nid}: 'params' must be a table (equip_set = \"vivi\", ...)")
    # offline key checks (typos caught by lint without the install; value/range resolution is at build)
    for k in stats:
        if k not in _cd.CHARACTER_FIELDS:
            raise PlayableError(f"[[playable]] id {nid} stats: unknown field {k!r} (known: "
                                f"{', '.join(sorted(set(s[0] for s in _cd.CHARACTER_FIELDS.values())))})")
    for k in params:
        if k not in _cd.CHARACTER_PARAM_FIELDS:
            raise PlayableError(f"[[playable]] id {nid} params: unknown field {k!r} "
                                f"(known: {', '.join(sorted(_cd.CHARACTER_PARAM_FIELDS))})")
    params = dict(params)
    params.setdefault("name_keyword", _default_name_keyword(nid))     # a unique tag by default
    recruit = entry.get("recruit", False)
    if not isinstance(recruit, bool):
        raise PlayableError(f"[[playable]] id {nid}: 'recruit' must be true/false")
    return {"id": nid, "name": name, "names": names, "borrow_id": borrow_id,
            "stats": dict(stats), "params": params, "recruit": recruit}


def parse_all(entries) -> list:
    """A list of ``[[playable]]`` tables -> ``[spec]``, raising on a duplicate id."""
    if entries is None:
        return []
    if not isinstance(entries, list):
        entries = [entries]
    specs, seen = [], {}
    for n, e in enumerate(entries):
        spec = parse_playable(e, n=n)
        if spec["id"] in seen:
            raise PlayableError(f"[[playable]] id {spec['id']} is defined twice (#{seen[spec['id']]} and #{n})")
        seen[spec["id"]] = n
        specs.append(spec)
    return specs


def basestats_seeds(specs) -> list:
    """Specs -> the ``new_rows`` for :func:`characterdelta.build_basestats_delta`."""
    return [{"id": s["id"], "borrow": s["borrow_id"], "name": s["name"], "overrides": s["stats"]} for s in specs]


def params_seeds(specs) -> list:
    """Specs -> the ``new_rows`` for :func:`characterdelta.build_character_params_delta`."""
    return [{"id": s["id"], "borrow": s["borrow_id"], "name": s["name"], "overrides": s["params"]} for s in specs]


def name_directive_lines(specs) -> list:
    """The mod-global ``CharacterDefaultName <id> <SYM> <name>`` DictionaryPatch lines (one per language),
    ordered by spec then LANGS. DataPatchers reads these at LAUNCH (a relaunch, not F6, applies a name change)."""
    lines = []
    for s in specs:
        for lang in LANGS:
            sym = _lang_symbol(lang)
            lines.append(f"CharacterDefaultName {s['id']} {sym} {s['names'][sym]}")
    return lines


def recruit_ids(specs) -> list:
    """The ids that asked to be recruited at their field's load (``recruit = true``)."""
    return [s["id"] for s in specs if s["recruit"]]


def registry(specs) -> dict:
    """``name (lowercased) -> id`` -- lets ``[party] add = ["<custom name>"]`` recruit a custom character."""
    return {s["name"].lower(): s["id"] for s in specs}


def validate_playable(entry) -> list:
    """Offline structural problems for one ``[[playable]]`` (empty => OK)."""
    try:
        parse_playable(entry)
        return []
    except PlayableError as ex:
        return [str(ex)]
