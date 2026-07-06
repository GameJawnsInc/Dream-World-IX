"""``[[character]]`` / ``[[leveling]]`` -- author the PLAYER-side balance CSVs (``Data/Characters``) as deltas:
the Phase-5 twin of :mod:`actiondelta` (which does the enemy/ability side). See ``docs/BATTLE_DESIGN.md`` §8.

  [[character]]               # per-character base stats (BaseStats.csv, CharacterId 0-11)
  character = "Vivi"          #   name (Zidane..Beatrix) or a 0-11 id
  strength = 30              #   any of: dexterity / strength / magic / will / gems
  magic = 40

  [[leveling]]                # the 99-step growth curve (Leveling.csv, by level 1-99)
  level = 50                  #   1-99
  exp = 250000               #   experience to the NEXT level (UInt32)
  bonus_hp = 4000            #   HP at this level grows BonusHP*Strength/50 (UInt16)
  bonus_mp = 600             #   MP grows BonusMP*Magic/100 (UInt16)

WHY the two channels differ (this is the whole design):
  * **BaseStats.csv merges PER-ID** -- ``EnumerateCsvFromLowToHigh`` then ``result[id]=row`` (``ff9level.cs:30``),
    so a PARTIAL file overrides only the characters it lists; the base supplies the other 11. A delta is legal.
  * **Leveling.csv is read WHOLE-FILE** -- ``GetCsvWithHighestPriority`` (``ff9level.cs:53``) returns the single
    highest-priority file (it never accumulates rows) and the loader GATES at ``levels.Length >= 99``
    (``ff9level.cs:59``). So a partial Leveling.csv would **WIPE** every level it omits -> we read the base 99
    rows LIVE, patch the named levels, and re-emit ALL 99. (Like ``InitialItems.csv``, a higher-priority stacked
    mod folder's Leveling.csv SHADOWS ours -- warned.)

Both read the base CSV LIVE from the install (provenance: only your overrides live in the toml; the emitted CSV
is mod build-output, never committed). The full ``#`` header block is preserved verbatim. Narrow engine column
types (Byte / UInt16 / UInt32) are RANGE-CHECKED offline so an out-of-range value fails the build/lint -- never
the game's boot (``CsvParser.Byte`` would overflow -> ``ff9level`` ``ConfirmQuit`` at load). cp1252 + LF, matching
the install.
"""
from __future__ import annotations

import re

_U16 = 0xFFFF
_U32 = 0xFFFFFFFF
_I32 = 2 ** 31 - 1

# committed CharacterId name->id (the open-source Memoria enum, CharacterId.cs: Zidane=0 .. Beatrix=11). The
# 8-11 guests (Cinna/Marcus/Blank/Beatrix) are valid BaseStats ids too. Provenance-clean (enum names, no SE data).
CHARACTER_IDS = {
    "zidane": 0, "vivi": 1, "garnet": 2, "steiner": 3, "freya": 4, "quina": 5, "eiko": 6, "amarant": 7,
    "cinna": 8, "marcus": 9, "blank": 10, "beatrix": 11,
}
_MAX_CHAR_ID = 11

# The custom ADDITIVE band for a genuine NEW (13th+) CharacterId -- a party member ALONGSIDE the 12 canon
# characters (memory project-ff9-13th-character). The engine loads any CSV row whose Id is beyond 0-11 (the
# BaseStats/CharacterParameters gates are MINIMUMS, `for i < 12` -- a 13th id-12 row PASSES), and every
# runtime table (FF9StateGlobal.player is a Dictionary<CharacterId,PLAYER>, the menu/battle iterate it) is
# dynamic, so id 12 needs ZERO DLL. id 12 is the in-game-proven first slot; 13-15 also load (undefined enum
# values cast fine) but stay unproven -- keep the band tight.
CUSTOM_CHAR_MIN = 12
CUSTOM_CHAR_MAX = 15


def _resolve_new_char_id(token, ctx) -> int:
    """A NEW (13th+) CharacterId in the additive band CUSTOM_CHAR_MIN..MAX. A base id 0-11 is NOT a new
    character -- those are seeded by the base game -- so it is rejected here (use ``[[character]]`` to tune them)."""
    if isinstance(token, bool) or not isinstance(token, (int, str)):
        raise CharacterDeltaError(f"{ctx} needs an 'id' ({CUSTOM_CHAR_MIN}-{CUSTOM_CHAR_MAX}, a NEW character)")
    try:
        nid = int(token)
    except (ValueError, TypeError):
        raise CharacterDeltaError(f"{ctx} id must be an integer {CUSTOM_CHAR_MIN}-{CUSTOM_CHAR_MAX} (got {token!r})")
    if not CUSTOM_CHAR_MIN <= nid <= CUSTOM_CHAR_MAX:
        raise CharacterDeltaError(f"{ctx} id {nid} is out of the custom band {CUSTOM_CHAR_MIN}-{CUSTOM_CHAR_MAX} "
                                  f"(0-11 are the base game's -- a NEW character uses {CUSTOM_CHAR_MIN}+)")
    return nid

# friendly TOML key -> (BaseStats column name, max). Dexterity/Strength/Magic/Will are Byte (the base stat; the
# engine formula later clamps the DERIVED stat to 50/99). Gems is UInt32.
CHARACTER_FIELDS = {
    "dexterity": ("dexterity", 0xFF), "dex": ("dexterity", 0xFF),
    "strength": ("strength", 0xFF), "str": ("strength", 0xFF),
    "magic": ("magic", 0xFF), "mag": ("magic", 0xFF),
    "will": ("will", 0xFF), "spirit": ("will", 0xFF),
    "gems": ("gems", _U32),
}

# Leveling has NO id column -- it is keyed by ROW ORDER (line N = level N). friendly key -> (column INDEX, max).
LEVELING_FIELDS = {
    "exp": (0, _U32), "experience": (0, _U32),
    "bonus_hp": (1, _U16), "hp": (1, _U16),
    "bonus_mp": (2, _U16), "mp": (2, _U16),
}
_LEVEL_COUNT = 99

# committed SupportAbility names by id (the open-source Memoria enum SupportAbility.cs: id 0-62 real, 63=Void
# sentinel). Provenance-clean (enum names, no SE data). The CSV's Comment column ("Auto-Reflect") differs from
# these enum names ("AutoReflect"), so we key by Id and match input by a normalized name (strip non-alphanumerics).
_SA_NAMES = (
    "AutoReflect", "AutoFloat", "AutoHaste", "AutoRegen", "AutoLife", "HP10", "HP20", "MP10", "MP20", "Accuracy",
    "Distract", "LongReach", "MPAttack", "BirdKiller", "BugKiller", "StoneKiller", "UndeadKiller", "DragonKiller",
    "DevilKiller", "BeastKiller", "ManEater", "HighJump", "MasterThief", "StealGil", "Healer", "AddStatus",
    "GambleDefence", "Chemist", "PowerThrow", "PowerUp", "ReflectNull", "Reflectx2", "MagElemNull", "Concentrate",
    "HalfMP", "HighTide", "Counter", "Cover", "ProtectGirls", "Eye4Eye", "BodyTemp", "Alert", "Initiative",
    "LevelUp", "AbilityUp", "Millionaire", "FleeGil", "GuardianMog", "Insomniac", "Antibody", "BrightEyes",
    "Loudmouth", "RestoreHP", "Jelly", "ReturnMagic", "AbsorbMP", "AutoPotion", "Locomotion", "ClearHeaded",
    "Boost", "OdinSword", "Mug", "Bandit", "Void",
)
_MAX_SA_ID = len(_SA_NAMES) - 1   # 63 (Void)


def _norm_sa(s) -> str:
    return re.sub(r"[^0-9a-z]", "", str(s).lower())


_SA_BY_NORM = {_norm_sa(n): i for i, n in enumerate(_SA_NAMES)}
# id 60's CSV display Comment is "Odin's Sword" (possessive) -> normalizes to "odinssword" (the apostrophe-s adds
# an extra 's'), differing from the enum "OdinSword" -> "odinsword". It is the ONLY one of 64 whose display name
# diverges this way, so alias it -> a user copying the name the `ability-gems` catalog prints resolves correctly.
_SA_BY_NORM.setdefault("odinssword", 60)


class CharacterDeltaError(ValueError):
    pass


def _csv_path(name, game):
    from ..config import find_game_path
    return find_game_path(game) / "StreamingAssets" / "Data" / "Characters" / name


def _to_int(value, key) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise CharacterDeltaError(f"{key} must be an integer (got {value!r})")
    try:
        return int(value)
    except ValueError:
        raise CharacterDeltaError(f"{key} must be an integer (got {value!r})")


def _range(v, vmax, key) -> str:
    if not 0 <= v <= vmax:
        raise CharacterDeltaError(f"{key}={v} out of range (0-{vmax})")
    return str(v)


# ---- read the base CSV (cp1252, byte-faithful), preserving the FULL header block verbatim -----------------
def _read_csv(path) -> tuple:
    """Parse a ``Data/Characters`` CSV -> ``(header_lines, legend_cols, data_rows)``:
      * ``header_lines`` -- every ``#`` line (comments / ``#!`` options / legend / type row), VERBATIM + in order.
      * ``legend_cols``  -- ``{lower column name: index}`` from the first ``#``-legend with an ``id`` field (BaseStats
                            has one; Leveling does NOT -> ``{}``, the caller keys by row order instead).
      * ``data_rows``    -- the list of ``;``-split data rows, IN ORDER (verbatim cells, for re-emit)."""
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    header: list = []
    legend: "dict | None" = None
    rows: list = []
    for raw in data.decode("cp1252", errors="replace").splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("#"):
            header.append(raw)                              # keep comments/#!/legend/types verbatim
            if legend is None and not s.startswith("#!"):
                fields = [f.strip().split("(")[0].strip().lower() for f in s.lstrip("#").strip().split(";")]
                if "id" in fields and len(fields) > 1:
                    legend = {name: i for i, name in enumerate(fields)}
            continue
        rows.append(raw.split(";"))
    return header, (legend or {}), rows


# ---- read-live catalog (for the `characters` CLI -- the import->SEE->tune view) ---------------------------
def basestats_catalog(game=None):
    """``[(name, id, [(stat, value)...])...]`` per character from the live BaseStats.csv, or None if unreadable
    (offline-safe). The provenance-clean READ side (names/ids/the live values shown, never committed)."""
    try:
        _header, cols, rows = _read_csv(_csv_path("BaseStats.csv", game))
    except (FileNotFoundError, OSError, RuntimeError):
        return None
    if not cols or not rows:
        return None
    nidx = cols.get("comment", 0)
    out = []
    for cells in rows:
        try:
            cid = int(cells[cols["id"]].strip())
        except (ValueError, IndexError, KeyError):
            continue
        name = cells[nidx].strip() if nidx < len(cells) else str(cid)
        stats = [(s, cells[cols[s]].strip()) for s in ("dexterity", "strength", "magic", "will", "gems")
                 if cols.get(s) is not None and cols[s] < len(cells)]
        out.append((name, cid, stats))
    return sorted(out, key=lambda t: t[1])


def ability_gems_catalog(game=None):
    """``[(name, id, gems)...]`` per SupportAbility from the live AbilityGems.csv, or None if unreadable. The
    name is the CSV's display Comment (e.g. ``Auto-Reflect``); ``[[ability_gem]]`` accepts that, the enum name
    (``AutoReflect``), or the id."""
    try:
        _h, cols, rows = _read_csv(_csv_path("Abilities/AbilityGems.csv", game))
    except (FileNotFoundError, OSError, RuntimeError):
        return None
    if not cols or not rows:
        return None
    nidx, gem_col = cols.get("comment", 0), cols.get("gems", cols.get("gemscount", 2))
    out = []
    for cells in rows:
        try:
            aid = int(cells[cols["id"]].strip())
        except (ValueError, IndexError, KeyError):
            continue
        name = cells[nidx].strip() if nidx < len(cells) else _SA_NAMES[aid] if aid <= _MAX_SA_ID else str(aid)
        gems = cells[gem_col].strip() if gem_col < len(cells) else "?"
        out.append((name, aid, gems))
    return sorted(out, key=lambda t: t[1])


# ---- [[character]] -> BaseStats.csv (per-id PARTIAL delta) ------------------------------------------------
def _resolve_char_id(token):
    if token is None or isinstance(token, bool):
        raise CharacterDeltaError("[[character]] needs a 'character' (a name or a 0-11 id)")
    if isinstance(token, int) or (isinstance(token, str) and token.strip().lstrip("-").isdigit()):
        cid = int(token)
        if not 0 <= cid <= _MAX_CHAR_ID:
            raise CharacterDeltaError(f"[[character]] id {cid} out of range (0-{_MAX_CHAR_ID})")
        return cid
    cid = CHARACTER_IDS.get(str(token).strip().lower())
    if cid is None:
        raise CharacterDeltaError(f"[[character]] unknown character {token!r} "
                                  f"(known: {', '.join(n.title() for n in CHARACTER_IDS)})")
    return cid


def build_basestats_delta(entries, *, game=None, new_rows=()) -> tuple:
    """Read the base BaseStats.csv + apply ``[[character]]`` entries -> (delta_text, warnings). A PARTIAL delta:
    only the changed character rows are emitted; the engine supplies the rest per-id. ``new_rows`` seeds genuine
    NEW (13th+) characters from ``[[playable]]``: each ``{id, borrow, name, overrides}`` clones a donor 0-11 row,
    re-ids it into the custom band, and applies the author's stat overrides -- the engine's per-id merge accepts
    the extra id (its coverage gate is a MINIMUM)."""
    try:
        header, cols, rows = _read_csv(_csv_path("BaseStats.csv", game))
    except (FileNotFoundError, OSError, RuntimeError) as ex:
        raise CharacterDeltaError(f"[[character]] needs your FF9 install to read the base BaseStats.csv ({ex})")
    if not cols or not rows:
        raise CharacterDeltaError("could not parse the base BaseStats.csv (no id-legend / no rows)")
    if not isinstance(entries, list):
        raise CharacterDeltaError("[[character]] must be a list of tables")
    idx = cols["id"]
    by_id = {}
    for cells in rows:
        try:
            by_id[int(cells[idx].strip())] = cells
        except (ValueError, IndexError):
            continue
    warnings: list = []
    changed: dict = {}
    for nr in (new_rows or ()):                             # [[playable]] -> a NEW character's BaseStats row
        nid = _resolve_new_char_id(nr.get("id"), "[[playable]]")
        bid = _resolve_char_id(nr.get("borrow"))           # the donor (a base char 0-11) to clone stats from
        if bid not in by_id:
            raise CharacterDeltaError(f"[[playable]] borrow id {bid} is not in the base BaseStats.csv")
        if nid in by_id:
            raise CharacterDeltaError(f"[[playable]] id {nid} is already defined (a duplicate 13th character)")
        cells = list(by_id[bid])                           # clone the donor row, re-id + rename it
        cells[idx] = str(nid)
        nidx = cols.get("comment", 0)                      # BaseStats Comment is col 0 -- the menu-name label
        if nidx < len(cells):
            cells[nidx] = str(nr.get("name") or f"Char{nid}")
        for k, v in (nr.get("overrides") or {}).items():
            spec = CHARACTER_FIELDS.get(k)
            if spec is None:
                raise CharacterDeltaError(f"[[playable]] id {nid} stats: unknown field {k!r} "
                                          f"(known: {', '.join(sorted(set(s[0] for s in CHARACTER_FIELDS.values())))})")
            col, vmax = spec
            ci = cols.get(col)
            if ci is None or ci >= len(cells):
                raise CharacterDeltaError(f"[[playable]] id {nid}: base row has no column {col!r}")
            cells[ci] = _range(_to_int(v, f"[[playable]] {k}"), vmax, f"[[playable]] id {nid} stats {k}")
        by_id[nid] = cells
        changed.setdefault(nid, "playable")
    for n, e in enumerate(entries):
        if not isinstance(e, dict):
            raise CharacterDeltaError(f"[[character]] #{n} must be a table (got {type(e).__name__})")
        cid = _resolve_char_id(e.get("character"))
        if cid not in by_id:
            raise CharacterDeltaError(f"[[character]] id {cid} is not in the base BaseStats.csv")
        if cid in changed:
            warnings.append(f"[[character]] #{n} and #{changed[cid]} both target id {cid} -- they MERGE "
                            f"(a field set by both: the later wins)")
        changed.setdefault(cid, n)
        cells = by_id[cid]
        for k, v in e.items():
            if k == "character":
                continue
            spec = CHARACTER_FIELDS.get(k)
            if spec is None:
                raise CharacterDeltaError(f"[[character]] {e.get('character')!r}: unknown field {k!r} "
                                          f"(known: {', '.join(sorted(set(s[0] for s in CHARACTER_FIELDS.values())))})")
            col, vmax = spec
            ci = cols.get(col)
            if ci is None or ci >= len(cells):
                raise CharacterDeltaError(f"[[character]] id {cid}: base row has no column {col!r}")
            cells[ci] = _range(_to_int(v, f"{e.get('character')} {k}"), vmax, f"[[character]] {e.get('character')!r} {k}")
    note = "# ff9mapkit [[character]] -- a partial BaseStats.csv delta (merged per-CharacterId over the base)."
    out = [note] + header + [";".join(by_id[c]) for c in sorted(changed)]
    return "\n".join(out) + "\n", warnings


# ---- [[leveling]] -> Leveling.csv (WHOLE-FILE; read all 99, patch by level, re-emit all 99) ----------------
def build_leveling_file(entries, *, game=None) -> tuple:
    """Read the base Leveling.csv + apply ``[[leveling]]`` entries -> (full_99_row_text, warnings). WHOLE-FILE:
    the engine reads only the highest-priority Leveling.csv and gates at >=99 rows, so we re-emit ALL 99."""
    try:
        header, _cols, rows = _read_csv(_csv_path("Leveling.csv", game))
    except (FileNotFoundError, OSError, RuntimeError) as ex:
        raise CharacterDeltaError(f"[[leveling]] needs your FF9 install to read the base Leveling.csv ({ex})")
    if len(rows) < _LEVEL_COUNT:
        raise CharacterDeltaError(f"the base Leveling.csv has {len(rows)} rows, need >= {_LEVEL_COUNT}")
    if not isinstance(entries, list):
        raise CharacterDeltaError("[[leveling]] must be a list of tables")
    warnings: list = []
    seen: dict = {}
    for n, e in enumerate(entries):
        if not isinstance(e, dict):
            raise CharacterDeltaError(f"[[leveling]] #{n} must be a table (got {type(e).__name__})")
        lvl = _to_int(e.get("level"), "[[leveling]] level")
        if not 1 <= lvl <= _LEVEL_COUNT:
            raise CharacterDeltaError(f"[[leveling]] level {lvl} out of range (1-{_LEVEL_COUNT})")
        if lvl in seen:
            warnings.append(f"[[leveling]] #{n} and #{seen[lvl]} both target level {lvl} -- the later wins")
        seen.setdefault(lvl, n)
        overrides = [k for k in e if k != "level"]
        if not overrides:
            raise CharacterDeltaError(f"[[leveling]] level {lvl} sets no fields (give exp / bonus_hp / bonus_mp)")
        cells = rows[lvl - 1]                               # row order == level (line N = level N)
        for k in overrides:
            spec = LEVELING_FIELDS.get(k)
            if spec is None:
                raise CharacterDeltaError(f"[[leveling]] level {lvl}: unknown field {k!r} "
                                          f"(known: exp, bonus_hp, bonus_mp)")
            ci, vmax = spec
            if ci >= len(cells):
                raise CharacterDeltaError(f"[[leveling]] level {lvl}: base row has no column index {ci}")
            cells[ci] = _range(_to_int(e[k], f"level {lvl} {k}"), vmax, f"[[leveling]] level {lvl} {k}")
    warnings.append("[[leveling]] -> Leveling.csv is WHOLE-FILE (highest-priority-wins): it REPLACES the entire "
                    "growth curve, and a stacked higher-priority mod folder's Leveling.csv would SHADOW it")
    note = "# ff9mapkit [[leveling]] -- the COMPLETE 99-row Leveling.csv (whole-file; patched levels + the base rest)."
    out = [note] + header + [";".join(r) for r in rows[:_LEVEL_COUNT]] + [";".join(r) for r in rows[_LEVEL_COUNT:]]
    return "\n".join(out) + "\n", warnings


# ---- [[ability_gem]] -> AbilityGems.csv (per-SupportAbility PARTIAL delta; the gem-COST balance lever) -----
def _resolve_sa_id(token):
    if token is None or isinstance(token, bool):
        raise CharacterDeltaError("[[ability_gem]] needs an 'ability' (a SupportAbility name or a 0-63 id)")
    if isinstance(token, int) or (isinstance(token, str) and token.strip().lstrip("-").isdigit()):
        aid = int(token)
        if not 0 <= aid <= _MAX_SA_ID:
            raise CharacterDeltaError(f"[[ability_gem]] id {aid} out of range (0-{_MAX_SA_ID})")
        return aid
    aid = _SA_BY_NORM.get(_norm_sa(token))
    if aid is None:
        raise CharacterDeltaError(f"[[ability_gem]] unknown ability {token!r} "
                                  f"(a SupportAbility name like 'Auto-Haste'/'AutoHaste', or a 0-{_MAX_SA_ID} id)")
    return aid


def build_ability_gems_delta(entries, *, game=None) -> tuple:
    """Read the base AbilityGems.csv + apply ``[[ability_gem]]`` entries -> (delta_text, warnings). A PARTIAL
    delta keyed per-SupportAbility (``EnumerateCsvFromLowToHigh``, ff9abil.cs:409); only the changed rows are
    emitted, the base supplies the other 63. The ``#! IncludeBoosted`` option + the Boosted column are preserved
    verbatim in the header/rows (load-bearing: the engine parses Boosted only when that option is present)."""
    try:
        header, cols, rows = _read_csv(_csv_path("Abilities/AbilityGems.csv", game))
    except (FileNotFoundError, OSError, RuntimeError) as ex:
        raise CharacterDeltaError(f"[[ability_gem]] needs your FF9 install to read the base AbilityGems.csv ({ex})")
    if not cols or not rows:
        raise CharacterDeltaError("could not parse the base AbilityGems.csv (no id-legend / no rows)")
    if not isinstance(entries, list):
        raise CharacterDeltaError("[[ability_gem]] must be a list of tables")
    idx = cols["id"]
    gem_col = cols.get("gems", cols.get("gemscount", 2))
    by_id = {}
    for cells in rows:
        try:
            by_id[int(cells[idx].strip())] = cells
        except (ValueError, IndexError):
            continue
    warnings: list = []
    changed: dict = {}
    for n, e in enumerate(entries):
        if not isinstance(e, dict):
            raise CharacterDeltaError(f"[[ability_gem]] #{n} must be a table (got {type(e).__name__})")
        aid = _resolve_sa_id(e.get("ability"))
        if aid not in by_id:
            raise CharacterDeltaError(f"[[ability_gem]] id {aid} is not in the base AbilityGems.csv")
        if aid in changed:
            warnings.append(f"[[ability_gem]] #{n} and #{changed[aid]} both target ability {aid} -- the later wins")
        changed.setdefault(aid, n)
        overrides = [k for k in e if k != "ability"]
        if not overrides:
            raise CharacterDeltaError(f"[[ability_gem]] {e.get('ability')!r} sets no fields (give gems = N)")
        for k in overrides:
            if k != "gems":
                raise CharacterDeltaError(f"[[ability_gem]] {e.get('ability')!r}: unknown field {k!r} (known: gems)")
            cells = by_id[aid]
            if gem_col >= len(cells):
                raise CharacterDeltaError(f"[[ability_gem]] id {aid}: base row has no gems column")
            cells[gem_col] = _range(_to_int(e[k], f"{e.get('ability')} gems"), _I32,
                                    f"[[ability_gem]] {e.get('ability')!r} gems")
    note = "# ff9mapkit [[ability_gem]] -- a partial AbilityGems.csv delta (merged per-SupportAbility over the base)."
    out = [note] + header + [";".join(by_id[a]) for a in sorted(changed)]
    return "\n".join(out) + "\n", warnings


# ---- CharacterPresetId 0-19 (the per-preset Abilities/<Name>.csv learn files + the CommandSets/menu_type key) -
# DISTINCT from CHARACTER_IDS (0-11): guests split into two preset slots (Cinna1/2 etc.), and the canonical enum
# NAME is the filename. Committed open-source names (CharacterPresetId.cs); provenance-clean.
_PRESET_NAMES = ("Zidane", "Vivi", "Garnet", "Steiner", "Freya", "Quina", "Eiko", "Amarant",
                 "Cinna1", "Cinna2", "Marcus1", "Marcus2", "Blank1", "Blank2", "Beatrix1", "Beatrix2",
                 "StageZidane", "StageCinna", "StageMarcus", "StageBlank")
PRESET_IDS = {n.lower(): i for i, n in enumerate(_PRESET_NAMES)}
_MAX_PRESET_ID = len(_PRESET_NAMES) - 1
_AMBIGUOUS_PRESETS = {"cinna": ("Cinna1", "Cinna2"), "marcus": ("Marcus1", "Marcus2"),
                      "blank": ("Blank1", "Blank2"), "beatrix": ("Beatrix1", "Beatrix2")}
# A CUSTOM preset band for a 13th+ character's OWN ability kit (project-ff9-ability-preset-system). The engine keys
# CommandSets/menu_type/learn by a Dictionary with MINIMUM-only coverage gates (LoadBattleCommandSets requires 0-19
# PRESENT, accepts higher ids), and an undefined enum id stringifies to its DECIMAL, so preset 20 resolves to the
# numeric learn file Abilities/20.csv -- ZERO-DLL, no enum member, no directive. The custom "name" IS str(id).
_PRESET_CUSTOM_MIN = 20     # char 12 -> preset 20, char 13 -> 21, ... (parallel to CUSTOM_CHAR_MIN)
_PRESET_CUSTOM_MAX = 23


def _resolve_preset(token, ctx="[[learn]]"):
    """A CharacterPresetId name or 0-19 id -> (id, canonical_name). A custom-band id 20-23 -> (id, str(id)) (its
    numeric learn-file name Abilities/<id>.csv). Bare Cinna/Marcus/Blank/Beatrix = ambiguous."""
    if token is None or isinstance(token, bool):
        raise CharacterDeltaError(f"{ctx} needs a 'preset' (a CharacterPresetId name or a 0-{_MAX_PRESET_ID} id)")
    if isinstance(token, int) or (isinstance(token, str) and token.strip().lstrip("-").isdigit()):
        pid = int(token)
        if 0 <= pid <= _MAX_PRESET_ID:
            return pid, _PRESET_NAMES[pid]
        if _PRESET_CUSTOM_MIN <= pid <= _PRESET_CUSTOM_MAX:     # a 13th+ char's OWN preset -> numeric file name
            return pid, str(pid)
        raise CharacterDeltaError(f"{ctx} preset id {pid} out of range (0-{_MAX_PRESET_ID}, or custom "
                                  f"{_PRESET_CUSTOM_MIN}-{_PRESET_CUSTOM_MAX})")
    key = str(token).strip().lower()
    if key in _AMBIGUOUS_PRESETS:
        raise CharacterDeltaError(f"{ctx} preset {token!r} is ambiguous -- use {' or '.join(_AMBIGUOUS_PRESETS[key])}")
    pid = PRESET_IDS.get(key)
    if pid is None:
        raise CharacterDeltaError(f"{ctx} unknown preset {token!r} (a CharacterPresetId name or 0-{_MAX_PRESET_ID} id)")
    return pid, _PRESET_NAMES[pid]


# ---- [[character_param]] -> CharacterParameters.csv (PARTIAL per-id; FIXED-INDEX cols -- legend names are stale) -
# All numerics are CsvParser.Byte (0-255; the legend type row "Int32;Boolean" is a LIE). Cols 6/7 are Strings.
CHARACTER_PARAM_FIELDS = {
    "row": (1, "int", 0xFF), "win_pose": (2, "int", 0xFF), "category": (3, "int", 0xFF),
    "menu_type": (4, "preset", 0xFF), "preset": (4, "preset", 0xFF),
    "equipment_set": (5, "int", 0xFF), "equip_set": (5, "int", 0xFF),
    "serial_formula": (6, "str", 0), "name_keyword": (7, "str", 0),
}


def _resolve_char_id_as(token, ctx):
    try:
        return _resolve_char_id(token)
    except CharacterDeltaError as ex:
        raise CharacterDeltaError(str(ex).replace("[[character]]", ctx, 1))


def _encode_param(value, kind, vmax, key) -> str:
    if kind == "str":
        s = str(value)
        if ";" in s:
            raise CharacterDeltaError(f"{key}: a String value can't contain ';' (the CSV delimiter)")
        return s
    if kind == "preset":
        return str(_resolve_preset(value, key)[0])         # a CharacterPresetId: bounded to 0-19 (name OR id), NOT
    return str(_range(_to_int(value, key), vmax, key))     # 0-255 -- a 20-254 menu_type crashes at battle entry


def build_character_params_delta(entries, *, game=None, new_rows=()) -> tuple:
    """Read CharacterParameters.csv + apply ``[[character_param]]`` -> (partial delta, warnings). PER-id (0-11):
    only the changed rows are emitted; the base supplies the rest. Columns are written by FIXED INDEX. ``new_rows``
    seeds a genuine NEW (13th+) character from ``[[playable]]``: each ``{id, borrow, name, overrides}`` clones a
    donor 0-11 row (its CommandSet/EquipmentSet/serial formula), re-ids it, and applies overrides. This row is
    the ALLOCATOR -- ``FF9Play_Init`` builds a PLAYER for every loaded CharacterParameters Id, so an id-12 row
    is what brings the 13th character into existence (memory project-ff9-13th-character)."""
    try:
        header, cols, rows = _read_csv(_csv_path("CharacterParameters.csv", game))
    except (FileNotFoundError, OSError, RuntimeError) as ex:
        raise CharacterDeltaError(f"[[character_param]] needs your FF9 install to read CharacterParameters.csv ({ex})")
    if not rows:
        raise CharacterDeltaError("could not parse the base CharacterParameters.csv (no rows)")
    if not isinstance(entries, list):
        raise CharacterDeltaError("[[character_param]] must be a list of tables")
    idx = cols.get("id", 0)                                  # Id is col 0 (the legend may not name it)
    by_id, warnings, changed = {}, [], {}
    for cells in rows:
        try:
            by_id[int(cells[idx].strip())] = cells
        except (ValueError, IndexError):
            continue
    for nr in (new_rows or ()):                             # [[playable]] -> a NEW character's CharacterParameters row
        nid = _resolve_new_char_id(nr.get("id"), "[[playable]]")
        bid = _resolve_char_id(nr.get("borrow"))           # the donor (a base char 0-11) to clone identity from
        if bid not in by_id:
            raise CharacterDeltaError(f"[[playable]] borrow id {bid} is not in the base CharacterParameters.csv")
        if nid in by_id:
            raise CharacterDeltaError(f"[[playable]] id {nid} is already defined (a duplicate 13th character)")
        cells = list(by_id[bid])                           # clone the donor row, re-id it
        cells[idx] = str(nid)
        name = str(nr.get("name") or f"Char{nid}")
        if cells and cells[-1].lstrip().startswith("#"):   # the trailing `# Name` comment cell
            cells[-1] = f"# {name}"
        else:
            cells.append(f"# {name}")
        for k, v in (nr.get("overrides") or {}).items():
            spec = CHARACTER_PARAM_FIELDS.get(k)
            if spec is None:
                raise CharacterDeltaError(f"[[playable]] id {nid} params: unknown field {k!r} "
                                          f"(known: {', '.join(sorted(CHARACTER_PARAM_FIELDS))})")
            ci, kind, vmax = spec
            if ci >= len(cells):
                raise CharacterDeltaError(f"[[playable]] id {nid}: base row has no column index {ci}")
            cells[ci] = _encode_param(v, kind, vmax, f"[[playable]] id {nid} params {k}")
        by_id[nid] = cells
        changed.setdefault(nid, "playable")
    for n, e in enumerate(entries):
        if not isinstance(e, dict):
            raise CharacterDeltaError(f"[[character_param]] #{n} must be a table (got {type(e).__name__})")
        cid = _resolve_char_id_as(e.get("character"), "[[character_param]]")
        if cid not in by_id:
            raise CharacterDeltaError(f"[[character_param]] id {cid} is not in the base CharacterParameters.csv")
        if cid in changed:
            warnings.append(f"[[character_param]] #{n} and #{changed[cid]} both target id {cid} -- the later wins")
        changed.setdefault(cid, n)
        cells = by_id[cid]
        for k, v in e.items():
            if k == "character":
                continue
            spec = CHARACTER_PARAM_FIELDS.get(k)
            if spec is None:
                raise CharacterDeltaError(f"[[character_param]] {e.get('character')!r}: unknown field {k!r} "
                                          f"(known: {', '.join(sorted(CHARACTER_PARAM_FIELDS))})")
            ci, kind, vmax = spec
            if ci >= len(cells):
                raise CharacterDeltaError(f"[[character_param]] id {cid}: base row has no column index {ci}")
            cells[ci] = _encode_param(v, kind, vmax, f"[[character_param]] {e.get('character')!r} {k}")
    note = "# ff9mapkit [[character_param]] -- a partial CharacterParameters.csv delta (merged per-CharacterId)."
    return "\n".join([note] + header + [";".join(by_id[c]) for c in sorted(changed)]) + "\n", warnings


# ---- BattleParameters.csv -> a NEW serial row (the custom battle LOOK for a 13th character) -----------------
# COSMETIC only (model/34 anims/avatar/bones; NOT combat stats -- those are BaseStats). Per-serial partial delta
# (EnumerateCsvFromLowToHigh; coverage gate = a MINIMUM 0-18). A new character gets an independent battle model by
# adding a serial >=19 that CLONES a donor serial's row (its 34 anims + avatar + bones) and only swaps the ModelId
# to a minted GEO -- the clips bind to the minted mesh by bone NAME (memory project-ff9-13th-character /
# project-ff9-custom-models). Verified engine-side: btl_mot.SetPlayerDefMotion loads the 34 anims by NAME;
# BattlePlayerCharacter.CreatePlayer reads BattleParameterList[serial].ModelId -> ModelFactory.CreateModel.
_BATTLE_SERIAL_MIN = 19             # 0-18 are the base game's serials (the coverage gate is `at least 19`)


def build_battle_params_delta(new_serials, *, game=None) -> tuple:
    """Read the base BattleParameters.csv + add NEW serial rows -> (partial delta, warnings). Each entry
    ``{id (serial>=19), borrow (a donor serial), model (a GEO name), trance_model?, avatar?, comment}`` clones the
    donor serial's row and swaps ModelId (+ TranceModelId, + AvatarSprite) -- everything else (the 34 anim names,
    bones, offsets) is carried verbatim, so the minted mesh animates via the donor's clips."""
    try:
        header, cols, rows = _read_csv(_csv_path("BattleParameters.csv", game))
    except (FileNotFoundError, OSError, RuntimeError) as ex:
        raise CharacterDeltaError(f"[[playable]] custom battle model needs your FF9 install to read the base "
                                  f"BattleParameters.csv ({ex})")
    if not cols or not rows:
        raise CharacterDeltaError("could not parse the base BattleParameters.csv (no id-legend / no rows)")
    if not isinstance(new_serials, list):
        raise CharacterDeltaError("battle_params must be a list of tables")
    idx = cols["id"]
    model_col = cols.get("modelid")
    trance_col = cols.get("trancemodelid")
    avatar_col = cols.get("avatarsprite")
    if model_col is None:
        raise CharacterDeltaError("the base BattleParameters.csv legend has no ModelId column")
    by_id = {}
    for cells in rows:
        try:
            by_id[int(cells[idx].strip())] = cells
        except (ValueError, IndexError):
            continue
    warnings, changed = [], {}
    for nr in new_serials:
        if not isinstance(nr, dict):
            raise CharacterDeltaError(f"battle_params entry must be a table (got {type(nr).__name__})")
        sid = _to_int(nr.get("id"), "battle serial id")
        if sid < _BATTLE_SERIAL_MIN:
            raise CharacterDeltaError(f"[[playable]] battle serial {sid} must be >= {_BATTLE_SERIAL_MIN} "
                                      f"(0-{_BATTLE_SERIAL_MIN - 1} are the base game's)")
        bser = _to_int(nr.get("borrow"), "battle borrow serial")
        if bser not in by_id:
            raise CharacterDeltaError(f"[[playable]] battle borrow serial {bser} is not in the base BattleParameters.csv")
        if sid in by_id:
            raise CharacterDeltaError(f"[[playable]] battle serial {sid} is already defined")
        model = str(nr.get("model") or "").strip()
        avatar = nr.get("avatar")
        if not model and not avatar:                       # a row must change SOMETHING (a model and/or a portrait)
            raise CharacterDeltaError(f"[[playable]] battle serial {sid} needs a 'model' (GEO name) and/or an 'avatar'")
        cells = list(by_id[bser])                          # clone the donor serial's whole row
        remap = nr.get("anim_names_remap")                 # custom_battle_anims -> re-point the row's normal animset
        if remap:                                          # value-based (only ANH cells match) -> layout-proof
            cells = [remap.get(c, c) for c in cells]
        cells[idx] = str(sid)
        if model:                                          # custom battle model -> swap ModelId (+ TranceModelId)
            cells[model_col] = model
            if trance_col is not None and trance_col < len(cells):
                cells[trance_col] = str(nr.get("trance_model") or model)
        if avatar and avatar_col is not None and avatar_col < len(cells):   # custom portrait -> swap AvatarSprite
            cells[avatar_col] = str(avatar)
        cmt = str(nr.get("comment") or f"serial{sid}")
        if cells and cells[-1].lstrip().startswith("#"):   # the trailing `# Name` comment cell
            cells[-1] = f"# {cmt}"
        else:
            cells.append(f"# {cmt}")
        by_id[sid] = cells
        changed.setdefault(sid, "playable")
    note = "# ff9mapkit [[playable]] -- a partial BattleParameters.csv delta (new custom-character serial rows)."
    return "\n".join([note] + header + [";".join(by_id[s]) for s in sorted(changed)]) + "\n", warnings


def resolve_donor_battle(borrow_id, *, game=None) -> tuple:
    """A base character's (0-11) DONOR battle identity -> ``(serial:int, model_geo:str)``: read its
    CharacterParameters serial-formula (col 6) and, when it is a plain integer, its BattleParameters ModelId.
    Raises CharacterDeltaError if the formula isn't a literal serial (a scenario-dependent donor like Zidane/
    Garnet -- the author must then give an explicit battle model source)."""
    try:
        _h, cp_cols, cp_rows = _read_csv(_csv_path("CharacterParameters.csv", game))
        _h2, bp_cols, bp_rows = _read_csv(_csv_path("BattleParameters.csv", game))
    except (FileNotFoundError, OSError, RuntimeError) as ex:
        raise CharacterDeltaError(f"[[playable]] custom battle model needs your FF9 install ({ex})")
    cp_by = {}
    for cells in cp_rows:
        try:
            cp_by[int(cells[cp_cols.get('id', 0)].strip())] = cells
        except (ValueError, IndexError):
            continue
    if borrow_id not in cp_by:
        raise CharacterDeltaError(f"[[playable]] borrow id {borrow_id} is not in CharacterParameters.csv")
    formula = cp_by[borrow_id][6].strip() if len(cp_by[borrow_id]) > 6 else ""
    if not formula.lstrip("-").isdigit():
        raise CharacterDeltaError(f"[[playable]] borrow id {borrow_id} has a scenario-dependent battle serial "
                                  f"formula ({formula!r}), so its battle model can't be auto-picked -- set BOTH "
                                  f"battle_model_from = \"<GEO>\" (the model to mint) AND battle_borrow_serial = "
                                  f"<0-18> (the BattleParameters row to clone anims/avatar from)")
    serial = int(formula)
    bp_idx = bp_cols["id"]
    mcol = bp_cols.get("modelid")
    bp_by = {}
    for cells in bp_rows:
        try:
            bp_by[int(cells[bp_idx].strip())] = cells
        except (ValueError, IndexError):
            continue
    if serial not in bp_by or mcol is None or mcol >= len(bp_by[serial]):
        raise CharacterDeltaError(f"[[playable]] donor serial {serial} has no BattleParameters ModelId")
    return serial, bp_by[serial][mcol].strip()


# ---- custom_battle_anims: a MINTED battle model's OWN independent animset (so editing it never touches the donor) -
# The 34 AnimationId cells of a serial row are attached at battle entry by NAME (player: btl_mot.SetPlayerDefMotion
# -> AnimationFactory.AddAnimWithAnimatioName; enemy: btl_init.OrganizeEnemyData -- verified in-source). That resolves
# ANH_<grp>_<form>_<tok>_X to the folder of GEO_<grp>_<form>_<tok> -- the anim's OWN embedded token, NOT the model
# that plays it (e.g. Steiner's serial-7 ModelId is GEO_MAIN_B0_018 but his anims are token 007). So a minted model
# that borrows the donor's anim NAMES shares the donor's clip folder (editing them touches the donor). Independence:
# take the row's NORMAL AnimationId block (the first contiguous run of ANH_ cells; the trance block, if present, is a
# separate later run kept shared in v1), re-point every cell to the MINTED model's token (ANH_<mintgrp>_<mintform>_
# M###_<suffix>), register each with `3DModelAnimation <key> <name>` (DataPatchers.cs:598 -> AnimationDB[key]=name;
# the model GEO + anim ANH must share the middle block), and copy each clip from ITS OWN source folder (the anim's
# token, not the ModelId) to Animations/<mintId>/<key>.anim. A missing clip FREEZES the motion (btl_mot.cs:226), so
# the build ships EVERY re-pointed clip or fails loud -- never re-points a name whose source clip it can't copy.
_BATTLE_ANIM_KEY_BASE = 1_000_000   # fresh AnimationDB keys for a minted animset (real ids run < ~20k; the engine's
                                    # own custom-anim example uses 100000 -- we stay an order above, per-mint banded).
                                    # SAFETY: FF9BattleDB.GEO / AnimationDB are TwoWayDictionary(allowDuplicateValues=
                                    # true), so a `3DModelAnimation`'s reverse (name->key) write only lands when the
                                    # name is NEW. A fresh key + a NOVEL M### name therefore add entries, never rebind
                                    # a real one -> the donor's name->key + key->name stay intact (Vivi is untouched).


def _anh_parts(name):
    """(grp, form, token, suffix) for an ``ANH_<grp>_<form>_<token>_<suffix..>`` name, else None."""
    p = str(name).split("_")
    if len(p) < 5 or p[0] != "ANH":
        return None
    return p[1], p[2], p[3], "_".join(p[4:])


def _first_anh_run(cells) -> list:
    """The cell VALUES of the first maximal contiguous run of ANH_ cells -- the NORMAL AnimationId block. The row
    layout is Id;Avatar;Model;Trance;GlowColor;AnimationId[0..33];AttackSequence;... (+ an optional later
    TranceAnimationId[0..33] block), so the first ANH_ run is exactly the normal 34, bounded by non-ANH cells."""
    run, started = [], False
    for c in cells:
        if _anh_parts(c) is not None:
            run.append(c)
            started = True
        elif started:
            break                                          # end of the first (normal) run; the trance run is later
    return run


def battle_animset_remap(normal_cells, mint_geo, mint_id, name_to_src) -> dict:
    """PURE (no install): the plan to give a minted battle model its own NORMAL animset. ``normal_cells`` is the
    row's normal AnimationId block (:func:`_first_anh_run`); ``name_to_src`` maps each anim name -> its source
    ``(src_geo_id, src_key)`` (the anim's OWN clip folder + key). Each cell is re-pointed to a mint-token twin
    ``ANH_<mintgrp>_<mintform>_<minttok>_<suffix>`` + a fresh AnimationDB key. Returns ``{names:{donor:mint},
    clips:[(src_geo_id,src_key,dst_key)], directives:[...], warnings:[...]}``. A cell whose source can't be
    resolved is LEFT shared with the donor (not re-pointed) so it can never freeze -- and warned."""
    mg = str(mint_geo).split("_")
    if len(mg) < 4:
        return {"names": {}, "clips": [], "directives": [], "warnings": [
            f"custom_battle_anims: can't parse mint GEO name ({mint_geo!r})"]}
    m_grp, m_form, m_tok = mg[1], mg[2], mg[3]
    names, clips, directives, warnings = {}, [], [], []
    seen = {}                                              # donor_name -> dst_key (a name repeats across cells)
    for cell in normal_cells:
        parts = _anh_parts(cell)
        if not parts or cell in seen:
            continue
        src = name_to_src.get(cell)
        if src is None:
            warnings.append(f"custom_battle_anims: no source clip for {cell!r} -- left shared with the donor")
            continue
        src_geo_id, src_key = src
        dst_key = _BATTLE_ANIM_KEY_BASE + (int(mint_id) - 6000) * 100 + len(seen)
        mint_name = f"ANH_{m_grp}_{m_form}_{m_tok}_{parts[3]}"
        seen[cell] = dst_key
        names[cell] = mint_name
        clips.append((int(src_geo_id), int(src_key), dst_key))
        directives.append(f"3DModelAnimation {dst_key} {mint_name}")
    if not names:
        warnings.append("custom_battle_anims: no re-pointable normal anims found (the serial row has no resolvable "
                        "AnimationId clips) -- the animset stays shared with the donor")
    return {"names": names, "clips": clips, "directives": directives, "warnings": warnings}


def plan_battle_animset(serial_to_clone, mint_geo, mint_id, *, game=None, name_to_src=None) -> dict:
    """Resolve :func:`battle_animset_remap` from the install: read the donor serial's row, take its NORMAL
    AnimationId block, and for each anim NAME resolve its source ``(src_geo_id, src_key)`` -- the clip's OWN folder
    (from the anim's embedded GEO token, NOT the row's ModelId) + key, both from the baked catalog. Returns
    ``{names, clips:[(src_geo_id,src_key,dst_key)], directives, warnings, mint_id}``. ``name_to_src`` can be
    injected (tests); by default it is built from the catalog."""
    try:
        _h, bp_cols, bp_rows = _read_csv(_csv_path("BattleParameters.csv", game))
    except (FileNotFoundError, OSError, RuntimeError) as ex:
        raise CharacterDeltaError(f"[[playable]] custom_battle_anims needs your FF9 install ({ex})")
    idx = bp_cols["id"]
    by_id = {}
    for cells in bp_rows:
        try:
            by_id[int(cells[idx].strip())] = cells
        except (ValueError, IndexError):
            continue
    ser = int(serial_to_clone)
    if ser not in by_id:
        raise CharacterDeltaError(f"[[playable]] custom_battle_anims: donor serial {ser} has no BattleParameters row")
    normal_cells = _first_anh_run(by_id[ser])
    if name_to_src is None:
        # Build {anim_name -> (src_geo_id, src_key)} for the block's anims: src_key from the baked AnimationDB
        # reverse, src_geo_id from the anim's OWN embedded GEO token (Animations/<that geoId>/ holds the clip).
        from .. import catalog
        from ..models import extract as _extract
        name_to_key = {v: k for k, v in catalog.ANIMATIONS.items()}
        name_to_src, geo_cache = {}, {}
        for cell in set(normal_cells):
            parts = _anh_parts(cell)
            key = name_to_key.get(cell)
            if not parts or key is None:
                continue
            src_geo = f"GEO_{parts[0]}_{parts[1]}_{parts[2]}"
            if src_geo not in geo_cache:
                try:
                    geo_cache[src_geo] = _extract.resolve_geo(src_geo)[1]
                except (ValueError, KeyError, FileNotFoundError, OSError, RuntimeError):
                    geo_cache[src_geo] = None
            if geo_cache[src_geo] is not None:
                name_to_src[cell] = (geo_cache[src_geo], key)
    plan = battle_animset_remap(normal_cells, mint_geo, mint_id, name_to_src)
    plan["mint_id"] = int(mint_id)                         # the DEST folder: Animations/<mint_id>/<dst_key>.anim
    plan["serial"] = ser                                   # the donor serial -> battle_motion_labels for the edit loop
    return plan


# The 34 battle-motion slots of a BattleParameters row, in order (btl_mot.cs:22-55 MP_* comments) -- so the Blender
# edit loop can name each Action by what it DOES ("23_attack", "27_cast") instead of a raw clip key.
_BATTLE_MOTION_LABELS = (
    "idle", "idle_low_hp", "hit", "hit_hard", "ko", "getup_low_hp", "getup_ko", "fall_low_hp", "fall_ko",
    "ready", "to_ready", "low_hp_to_ready", "to_defend", "defend", "defend_to_idle", "cover", "dodge", "flee",
    "victory", "victory_loop", "to_run", "run", "run_to_attack", "attack", "jump_back", "attack_to_idle",
    "to_cast", "cast", "cast_end", "step_forward", "step_back", "item", "ready_to_idle", "special",
)


def battle_motion_labels(serial_to_clone, *, game=None, name_to_key=None) -> dict:
    """``{src_clip_key -> "NN_motion"}`` for a donor serial's normal battle animset (the 34 MP_* slots in order,
    first slot per unique clip). Lets the Blender edit loop name each Action ("23_attack", "27_cast") instead of
    the raw numeric key the modeler saw in Blender's Action list."""
    try:
        _h, bp_cols, bp_rows = _read_csv(_csv_path("BattleParameters.csv", game))
    except (FileNotFoundError, OSError, RuntimeError) as ex:
        raise CharacterDeltaError(f"[[playable]] custom_battle_anims needs your FF9 install ({ex})")
    idx = bp_cols["id"]
    by_id = {}
    for cells in bp_rows:
        try:
            by_id[int(cells[idx].strip())] = cells
        except (ValueError, IndexError):
            continue
    ser = int(serial_to_clone)
    if ser not in by_id:
        raise CharacterDeltaError(f"[[playable]] custom_battle_anims: donor serial {ser} has no BattleParameters row")
    normal = _first_anh_run(by_id[ser])
    if name_to_key is None:
        from .. import catalog
        name_to_key = {v: k for k, v in catalog.ANIMATIONS.items()}
    out: dict = {}
    for i, cell in enumerate(normal[:len(_BATTLE_MOTION_LABELS)]):
        key = name_to_key.get(cell)
        if key is None or int(key) in out:                 # first slot that uses a clip wins its label
            continue
        out[int(key)] = f"{i:02d}_{_BATTLE_MOTION_LABELS[i]}"
    return out


# ---- [[command_set]] -> CommandSets.csv (PARTIAL per-preset; tab-padded -> strip + index slots by position) ----
COMMANDSET_SLOTS = {
    "attack": 1, "defend": 2, "ability1": 3, "ability2": 4, "item": 5, "change": 6,
    "attack_trance": 7, "defend_trance": 8, "ability1_trance": 9, "ability2_trance": 10,
    "item_trance": 11, "change_trance": 12,
}
_MAX_COMMAND_ID = 47           # BattleCommandId slot value; >=48 = system/boundary


def _norm_cmd(s) -> str:
    return " ".join(str(s).strip().lower().replace("_", " ").split())


# BattleCommandId -> id (Memoria's open-source enum names, provenance-clean; player-assignable = 0-47, < BoundaryCheck
# 48). Friendly names + a few short aliases so [playable.abilities] command slots read 'Black Magic' not 22.
BATTLE_COMMANDS = {_norm_cmd(k): v for k, v in {
    "Attack": 1, "Steal": 2, "Jump": 3, "Defend": 4, "Change": 7, "Focus": 13, "Accumulate": 13, "Item": 14,
    "Throw": 15, "Summon": 16, "Summon Garnet": 16, "White Magic Garnet": 17, "White Magic": 19,
    "White Magic Eiko": 19, "Summon Eiko": 20, "Double White Magic": 21, "Black Magic": 22, "Double Black Magic": 23,
    "Blue Magic": 24, "Skill": 25, "Dyne": 26, "Dragon": 27, "Flair": 28, "Elan": 29, "Sword Art": 30,
    "Sword Magic": 31, "Magic Sword": 31, "Holy Sword": 32, "Holy White Magic": 34,
    "Blk Mag": 22, "Wht Mag": 19, "Blu Mag": 24, "None": 0,
}.items()}


# The ability-submenu commands whose menu is populated from the CHARACTER's learned abilities (magic / summon /
# skill), so a slot set to one of these opens to (its Commands.csv pool INTERSECT the learn list). If the author
# CHANGES such a slot away from the donor's without adding matching abilities to learn=[...], the menu can be EMPTY.
_LEARN_POOL_COMMANDS = {16, 17, 19, 20, 21, 22, 23, 24, 25, 28, 34}


def _resolve_command(token, ctx="[playable.abilities]") -> int:
    """A BattleCommandId name (Memoria enum / a friendly alias like 'Blk Mag') or a 0-47 id -> the id."""
    if token is None or isinstance(token, bool):
        raise CharacterDeltaError(f"{ctx}: a command needs a BattleCommandId name or a 0-{_MAX_COMMAND_ID} id")
    if isinstance(token, int) or (isinstance(token, str) and token.strip().lstrip("-").isdigit()):
        cid = int(token)
        if not 0 <= cid <= _MAX_COMMAND_ID:
            raise CharacterDeltaError(f"{ctx}: command id {cid} out of range (0-{_MAX_COMMAND_ID}, player-assignable)")
        return cid
    cid = BATTLE_COMMANDS.get(_norm_cmd(token))
    if cid is None:
        raise CharacterDeltaError(f"{ctx}: unknown command {token!r} (a BattleCommandId name like 'Black Magic' / "
                                  f"'Blk Mag' / 'Skill', or a 0-{_MAX_COMMAND_ID} id)")
    return cid


def build_command_set_delta(entries, *, game=None, new_rows=()) -> tuple:
    """Read CommandSets.csv + apply ``[[command_set]]`` -> (partial delta, warnings). PER-preset (0-19): re-point
    a character's battle-menu command SLOTS to existing BattleCommandIds (e.g. give Vivi a different ability
    command). The file is tab-padded + its legend collides Attack(Trance), so slots are written by FIXED INDEX
    and every emitted cell is stripped clean."""
    try:
        header, cols, rows = _read_csv(_csv_path("CommandSets.csv", game))
    except (FileNotFoundError, OSError, RuntimeError) as ex:
        raise CharacterDeltaError(f"[[command_set]] needs your FF9 install to read CommandSets.csv ({ex})")
    if not rows:
        raise CharacterDeltaError("could not parse the base CommandSets.csv (no rows)")
    if not isinstance(entries, list):
        raise CharacterDeltaError("[[command_set]] must be a list of tables")
    idx = cols.get("id", 0)
    by_id, warnings, changed = {}, [], {}
    for cells in rows:
        try:
            by_id[int(cells[idx].strip())] = [c.strip() for c in cells]   # strip the tab-padding
        except (ValueError, IndexError):
            continue
    for n, e in enumerate(entries):
        if not isinstance(e, dict):
            raise CharacterDeltaError(f"[[command_set]] #{n} must be a table (got {type(e).__name__})")
        pid, pname = _resolve_preset(e.get("preset"), "[[command_set]]")
        if pid not in by_id:
            raise CharacterDeltaError(f"[[command_set]] preset {pname} (id {pid}) is not in the base CommandSets.csv")
        if pid in changed:
            warnings.append(f"[[command_set]] #{n} and #{changed[pid]} both target preset {pname} -- the later wins")
        changed.setdefault(pid, n)
        cells = by_id[pid]
        for k, v in e.items():
            if k == "preset":
                continue
            slot = COMMANDSET_SLOTS.get(k)
            if slot is None:
                raise CharacterDeltaError(f"[[command_set]] {pname}: unknown slot {k!r} "
                                          f"(known: {', '.join(sorted(COMMANDSET_SLOTS))})")
            if slot >= len(cells):
                raise CharacterDeltaError(f"[[command_set]] {pname}: base row has no slot index {slot}")
            cid = _to_int(v, f"[[command_set]] {pname} {k}")
            if not 0 <= cid <= _MAX_COMMAND_ID:
                raise CharacterDeltaError(f"[[command_set]] {pname} {k}={cid} out of range (0-{_MAX_COMMAND_ID})")
            cells[slot] = str(cid)
    for nr in new_rows:                                    # [[playable.abilities]] -> a NEW custom-preset command set
        cid_new = _to_int(nr.get("id"), "command_set new preset id")
        if not _PRESET_CUSTOM_MIN <= cid_new <= _PRESET_CUSTOM_MAX:
            raise CharacterDeltaError(f"[[playable.abilities]] custom preset {cid_new} out of the custom band "
                                      f"{_PRESET_CUSTOM_MIN}-{_PRESET_CUSTOM_MAX}")
        clone = _to_int(nr.get("clone_from"), "command_set clone_from")   # a base preset 0-19 to clone the row from
        if clone not in by_id:
            raise CharacterDeltaError(f"[[playable.abilities]] menu_from preset {clone} is not in the base CommandSets.csv")
        if cid_new in by_id:
            raise CharacterDeltaError(f"[[playable.abilities]] custom preset {cid_new} is already defined")
        cells = list(by_id[clone])                         # clone the donor row (fixed Attack/Defend/Item/Change slots)
        cells[idx] = str(cid_new)
        for slotname, val in (nr.get("slots") or {}).items():
            slot = COMMANDSET_SLOTS.get(slotname)
            if slot is None or slot >= len(cells):
                raise CharacterDeltaError(f"[[playable.abilities]] preset {cid_new}: bad command slot {slotname!r}")
            new_cmd = _resolve_command(val, f"[[playable.abilities]] {slotname}")
            donor_val = by_id[clone][slot].strip() if slot < len(by_id[clone]) else ""
            if new_cmd in _LEARN_POOL_COMMANDS and str(new_cmd) != donor_val:   # a pool command CHANGED from the donor
                warnings.append(f"[[playable.abilities]] preset {cid_new}: {slotname}={val!r} draws its menu spells "
                                f"from the LEARN list -- ensure abilities.learn includes abilities in that command's "
                                f"pool (with ap = 0), or its battle menu may open EMPTY")
            cells[slot] = str(new_cmd)
        cmt = str(nr.get("comment") or f"preset{cid_new}")
        if cells and cells[-1].lstrip().startswith("#"):
            cells[-1] = f"# {cmt}"
        else:
            cells.append(f"# {cmt}")
        by_id[cid_new] = cells
        changed.setdefault(cid_new, "playable")
    note = "# ff9mapkit [[command_set]] -- a partial CommandSets.csv delta (merged per-preset over the base)."
    return "\n".join([note] + header + [";".join(by_id[c]) for c in sorted(changed)]) + "\n", warnings


# ---- MINT a unique command -> Commands.csv (a NEW magic-list command with its OWN ability pool) --------------
# A 13th char's OWN command (not a remix of Black/White Magic): a new Commands.csv row `Id;Type;MainEntry;ListEntry`
# with Type=1 (Ability) and ListEntry = a hand-picked pool of ACTIVE-ability ids. The engine (CharacterCommands.
# LoadBattleCommands + BattleHUD.DisplayAbility) reads any row generically; the shown spells = ListEntry INTERSECT
# the character's learned abilities. Zero-DLL: `EnumerateCsvFromLowToHigh` MERGES per-id, so a partial file
# adds/overrides just a custom-band id. The base supplies 0-46 (0-44 are REQUIRED by the loader). Id 46 (Reserve4)
# is a defined-but-unreferenced "None" placeholder, and 35-40 are unused "Magic" placeholder rows -> overriding any
# is safe (no base CommandSet references them). We deliberately SKIP 45 (AccessMenu -- reserved for the .ini [Battle]
# AccessMenus option) and 47 (EnemyAtk). Ids 48-99 are ENGINE-RESERVED (LoadBattleCommands logs an error). So the
# custom band is the safe unused low ids. Name: a `com_name.mes` overlay (a per-lang sentence array;
# project-ff9-ability-preset-system).
_CMD_CUSTOM_BAND = (46, 35, 36, 37, 38, 39, 40)      # allocate 46 first, then the unused RedMagic/YellowMagic/WhiteMagicCinna slots
_MAX_ACTIVE_ABILITY = 191                            # a ListEntry pool entry is an active-ability id (BattleAbilityId), 0-191


def _resolve_active_ability(token, *, game=None, ctx="command pool") -> int:
    """An active-ability name / ``AA:n`` / ``0-191`` id -> the active-ability id (BattleAbilityId) for a command
    ListEntry. Rejects support-ability (``SA:``) tokens -- a command pool holds ACTIVE abilities only."""
    if token is None or isinstance(token, bool):
        raise CharacterDeltaError(f"{ctx}: an ability needs a name or a 0-{_MAX_ACTIVE_ABILITY} id")
    s = str(token).strip()
    up = s.upper()
    if up.startswith("SA:"):
        raise CharacterDeltaError(f"{ctx}: {s!r} is a support ability -- a command pool holds ACTIVE abilities only")
    if up.startswith("AA:"):
        s = up[3:]
    if s.lstrip("-").isdigit():
        n = int(s)
        if not 0 <= n <= _MAX_ACTIVE_ABILITY:
            raise CharacterDeltaError(f"{ctx}: ability id {n} out of range (0-{_MAX_ACTIVE_ABILITY})")
        return n
    from . import actiondelta as _ad                  # an active-ability NAME -> id (live Actions.csv, needs install)
    try:
        _o, _l, cols, rows = _ad._read_raw(_ad._csv_path("Actions.csv", game))
        return _ad._resolve_id(s, rows, _ad._name_index(rows, cols), kind="command pool ability",
                               max_id=_MAX_ACTIVE_ABILITY)
    except _ad.ActionDeltaError as ex:
        raise CharacterDeltaError(f"{ctx}: {ex}")
    except (FileNotFoundError, OSError, RuntimeError) as ex:
        raise CharacterDeltaError(f"{ctx}: an ability name needs the install to resolve via Actions.csv ({ex})")


def build_commands_delta(new_commands, *, game=None) -> tuple:
    """``[playable.abilities] command1/command2`` inline tables -> a PARTIAL ``Commands.csv`` delta (merged per-id
    over the base). Each ``{id, name, abilities:[name/id]}`` becomes a ``Id;1;MainEntry;ListEntry;# name`` row: a
    magic-list command (Type 1 = Ability) whose ListEntry is its own resolved ability POOL. Returns ``(text,
    warnings)``. Reuses the base file's ``#! IncludeId`` header so the merged row keys on its own Id column."""
    if not new_commands:
        return "", []
    try:
        header, cols, rows = _read_csv(_csv_path("Commands.csv", game))
    except (FileNotFoundError, OSError, RuntimeError) as ex:
        raise CharacterDeltaError(f"[playable.abilities] a minted command needs your FF9 install to read Commands.csv ({ex})")
    warnings, out_rows, seen = [], [], set()
    for nc in new_commands:
        cid = _to_int(nc.get("id"), "minted command id")
        if cid not in _CMD_CUSTOM_BAND:
            raise CharacterDeltaError(f"[playable.abilities] minted command id {cid} is not in the safe custom band "
                                      f"{list(_CMD_CUSTOM_BAND)} (46 Reserve4 + the unused 35-40; 48-99 are engine-reserved)")
        if cid in seen:
            raise CharacterDeltaError(f"[playable.abilities] minted command id {cid} is defined twice")
        seen.add(cid)
        name = str(nc.get("name") or "").strip()
        if not name:
            raise CharacterDeltaError(f"[playable.abilities] minted command {cid} needs a 'name'")
        abils = nc.get("abilities") or []
        if not isinstance(abils, list) or not abils:
            raise CharacterDeltaError(f"[playable.abilities] minted command {name!r} needs a non-empty 'abilities' pool")
        pool = [_resolve_active_ability(a, game=game, ctx=f"[playable.abilities] command {name!r} pool") for a in abils]
        if len(set(pool)) != len(pool):
            warnings.append(f"[playable.abilities] command {name!r} lists a duplicate ability in its pool")
        # Id ; Type(1=Ability) ; MainEntry(=first pool entry, matching base rows) ; ListEntry(comma-space) ; # name
        out_rows.append(f"{cid};1;{pool[0]};{', '.join(str(p) for p in pool)};# {name}")
    note = "# ff9mapkit [playable.abilities] -- a partial Commands.csv delta (a minted unique command, merged per-id)."
    return "\n".join([note] + header + out_rows) + "\n", warnings


def build_command_name_overlay(new_commands) -> str:
    """The minted commands -> a ``com_name.mes`` overlay body: one ``[TXID=<id>]<name>[ENDN]`` sentence per command.
    Cumulatively merged by the engine (``ImportWithCumulativeModFiles``) over the base command names -> it renames
    ONLY the minted ids, leaving every other command untouched."""
    return "".join(f"[TXID={_to_int(nc['id'], 'minted command id')}]{str(nc['name']).strip()}[ENDN]"
                   for nc in (new_commands or []))


# ---- [[learn]] -> Abilities/<Preset>.csv (WHOLE-FILE per preset; the ability-progression curve) -------------
def _resolve_learn_token(token, *, game=None) -> str:
    """An ability -> the canonical Abilities-CSV cell. Forms: ``0`` / ``AA:n`` / ``SA:n`` (passthrough + range);
    an SA NAME -> ``SA:id`` (committed table); an active-ability NAME -> ``AA:id`` (live Actions.csv, needs install)."""
    if token is None or isinstance(token, bool):
        raise CharacterDeltaError("[[learn.ability]] needs an 'ability' (0, AA:n, SA:n, or a name)")
    s = str(token).strip()
    if s == "0":
        return "0"
    up = s.upper()
    if up.startswith(("AA:", "SA:")):
        n = _to_int(up[3:], f"[[learn]] {up[:2]}")
        vmax = 191 if up.startswith("AA:") else _MAX_SA_ID
        if not 0 <= n <= vmax:
            raise CharacterDeltaError(f"[[learn]] {up[:3]}{n} out of range (0-{vmax})")
        return f"{up[:3]}{n}"
    said = _SA_BY_NORM.get(_norm_sa(s))                      # an SA name (committed) -> SA:id
    if said is not None:
        return f"SA:{said}"
    from . import actiondelta as _ad                        # else an active-ability name -> AA:id (live Actions.csv)
    try:
        _o, _l, cols, rows = _ad._read_raw(_ad._csv_path("Actions.csv", game))
        aid = _ad._resolve_id(s, rows, _ad._name_index(rows, cols), kind="learn.ability", max_id=191)
    except _ad.ActionDeltaError as ex:
        raise CharacterDeltaError(f"[[learn.ability]] {ex}")
    except (FileNotFoundError, OSError, RuntimeError) as ex:
        raise CharacterDeltaError(f"[[learn.ability]] {s!r}: an active-ability name needs the install to resolve "
                                  f"via Actions.csv ({ex})")
    return f"AA:{aid}"


def _group_learns(learns):
    """``[[learn]]`` blocks -> ``{preset_name: {abilities:[...], removes:[...]}}`` (blocks for the same preset MERGE)."""
    grouped: dict = {}
    for n, e in enumerate(learns if isinstance(learns, list) else [learns]):
        if not isinstance(e, dict):
            raise CharacterDeltaError(f"[[learn]] #{n} must be a table (got {type(e).__name__})")
        _pid, pname = _resolve_preset(e.get("preset"), "[[learn]]")
        g = grouped.setdefault(pname, {"abilities": [], "removes": []})
        abil = e.get("ability", [])
        g["abilities"] += abil if isinstance(abil, list) else [abil]
        rem = e.get("remove", [])
        g["removes"] += rem if isinstance(rem, list) else [rem]
    return grouped


def build_learn_file(preset_name, abilities, removes, *, game=None, read_from=None) -> tuple:
    """Read Abilities/<read_from or preset_name>.csv + apply the learn edits -> (WHOLE-FILE text, warnings). Override
    an existing token's AP, append a new token, drop a removed token, re-emit ALL rows (the whole file replaces the
    base, highest-priority-wins). Rows are ``<token>;<ap>;# <name>``. ``read_from`` seeds a CUSTOM preset's file
    ([[playable.abilities]]) from a base donor's learn list (the custom preset has no base file of its own)."""
    src = read_from or preset_name
    try:
        header, _cols, rows = _read_csv(_csv_path(f"Abilities/{src}.csv", game))
    except (FileNotFoundError, OSError, RuntimeError) as ex:
        raise CharacterDeltaError(f"[[learn]] preset {preset_name}: can't read Abilities/{src}.csv -- "
                                  f"presets 0-15 must exist; Stage* (16-19) have no base file ({ex})")
    by_token: dict = {}
    order: list = []
    for cells in rows:
        tok = cells[0].strip() if cells else ""
        if tok and tok not in by_token:
            by_token[tok] = [c.strip() for c in cells]
            order.append(tok)
    warnings: list = []
    for r in removes or []:                                  # drop removed tokens
        tok = _resolve_learn_token(r, game=game)
        if tok in by_token:
            del by_token[tok]
            order.remove(tok)
        else:
            warnings.append(f"[[learn]] {preset_name}: remove {r!r} ({tok}) is not in the base list -- ignored")
    for ab in abilities or []:                               # override AP / append new
        if not isinstance(ab, dict):
            raise CharacterDeltaError(f"[[learn]] {preset_name}: each [[learn.ability]] must be a table")
        tok = _resolve_learn_token(ab.get("ability"), game=game)
        ap = _to_int(ab.get("ap", 0), f"[[learn]] {preset_name} {tok} ap")
        if not 0 <= ap <= _I32:                            # CharacterAbility.Ap is Int32 (CsvParser.Int32), NOT UInt32
            raise CharacterDeltaError(f"[[learn]] {preset_name} {tok}: ap {ap} out of range (0-{_I32})")
        if tok in by_token:
            cells = by_token[tok]
            while len(cells) < 2:
                cells.append("0")
            cells[1] = str(ap)
        else:
            name = str(ab.get("name", "")).strip()
            by_token[tok] = [tok, str(ap), f"# {name}" if name else f"# {tok}"]
            order.append(tok)
    note = f"# ff9mapkit [[learn]] -- the COMPLETE {preset_name} learn list (whole-file; highest-priority-wins)."
    warnings.append(f"[[learn]] -> Abilities/{preset_name}.csv is WHOLE-FILE: it REPLACES the entire learn list, "
                    f"and a stacked higher-priority mod folder's {preset_name}.csv would SHADOW it")
    return "\n".join([note] + header + [";".join(by_token[t]) for t in order]) + "\n", warnings


def validate_learn(entry) -> list:
    """Offline structural problems for ``[[learn]]`` (empty => OK). Token FORMS (0/AA:/SA:/SA-name) check offline;
    an active-ability NAME defers to build (it needs the install's Actions.csv)."""
    if not isinstance(entry, dict):
        return ["[[learn]] must be a table (preset = \"...\", [[learn.ability]] blocks)"]
    problems: list = []
    try:
        _resolve_preset(entry.get("preset"), "[[learn]]")
    except CharacterDeltaError as ex:
        problems.append(str(ex))
    abil = entry.get("ability", [])
    abil = abil if isinstance(abil, list) else [abil]
    if not abil and not entry.get("remove"):
        problems.append("[[learn]] sets nothing (add a [[learn.ability]] block or remove = [...])")
    for ab in abil:
        if not isinstance(ab, dict) or ab.get("ability") is None:
            problems.append("[[learn.ability]] needs an 'ability' (0, AA:n, SA:n, or a name)")
            continue
        s = str(ab.get("ability")).strip().upper()
        if s == "0" or s.startswith(("AA:", "SA:")) or _SA_BY_NORM.get(_norm_sa(s)) is not None:
            try:
                _resolve_learn_token(ab.get("ability"))      # offline-resolvable form -> check the range now
            except CharacterDeltaError as ex:
                problems.append(str(ex))
        # else: an active-ability name -> resolution (+ presence) deferred to build (needs the install)
    return problems


# ---- mod-write stage -------------------------------------------------------------------------------------
def write_character_data(layout, *, characters=None, levelings=None, ability_gems=None, character_params=None,
                         command_sets=None, learns=None, new_basestats=None, new_params=None, battle_params=None,
                         command_set_new_rows=None, learns_new=None, new_commands=None, game=None) -> list:
    """Emit BaseStats / Leveling / AbilityGems / CharacterParameters / CommandSets (per-id deltas) + the per-preset
    Abilities/<Name>.csv learn lists into ``layout``. cp1252 + LF. ``new_basestats`` / ``new_params`` seed genuine
    NEW (13th+) characters (``[[playable]]``) into the BaseStats / CharacterParameters deltas; ``battle_params``
    adds a new BattleParameters serial row (a custom battle LOOK). Those files are written whenever there is EITHER
    a base-char delta OR a new character."""
    warnings: list = []
    # BaseStats + CharacterParameters merge new-character seed rows with any base-char deltas (one file each).
    if characters or new_basestats:
        text, w = build_basestats_delta(characters or [], game=game, new_rows=new_basestats or [])
        layout.base_stats_csv.parent.mkdir(parents=True, exist_ok=True)
        layout.base_stats_csv.write_text(text, encoding="cp1252", errors="replace", newline="\n")
        warnings += w
    if character_params or new_params:
        text, w = build_character_params_delta(character_params or [], game=game, new_rows=new_params or [])
        layout.character_parameters_csv.parent.mkdir(parents=True, exist_ok=True)
        layout.character_parameters_csv.write_text(text, encoding="cp1252", errors="replace", newline="\n")
        warnings += w
    if battle_params:                                   # [[playable]] custom battle model -> a new serial row
        text, w = build_battle_params_delta(battle_params, game=game)
        layout.battle_parameters_csv.parent.mkdir(parents=True, exist_ok=True)
        layout.battle_parameters_csv.write_text(text, encoding="cp1252", errors="replace", newline="\n")
        warnings += w
    for entries, path, builder in ((levelings, layout.leveling_csv, build_leveling_file),
                                   (ability_gems, layout.ability_gems_csv, build_ability_gems_delta)):
        if entries:
            text, w = builder(entries, game=game)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="cp1252", errors="replace", newline="\n")
            warnings += w
    if command_sets or command_set_new_rows:                # CommandSets: base-preset re-points + custom-preset new rows
        text, w = build_command_set_delta(command_sets or [], game=game, new_rows=command_set_new_rows or [])
        layout.command_sets_csv.parent.mkdir(parents=True, exist_ok=True)
        layout.command_sets_csv.write_text(text, encoding="cp1252", errors="replace", newline="\n")
        warnings += w
    if new_commands:                                        # [playable.abilities] minted unique command(s) -> Commands.csv + names
        text, w = build_commands_delta(new_commands, game=game)
        layout.commands_csv.parent.mkdir(parents=True, exist_ok=True)
        layout.commands_csv.write_text(text, encoding="cp1252", errors="replace", newline="\n")
        warnings += w
        overlay = build_command_name_overlay(new_commands)  # a per-lang com_name.mes overlay (same text every lang)
        from ..config import LANGS
        for lang in LANGS:
            p = layout.command_name_mes(lang)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(overlay, encoding="cp1252", errors="replace", newline="\n")
    if learns:                                              # the learn lists are a FILE SET (one whole file per preset)
        for pname, g in _group_learns(learns).items():
            text, w = build_learn_file(pname, g["abilities"], g["removes"], game=game)
            p = layout.abilities_csv(pname)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="cp1252", errors="replace", newline="\n")
            warnings += w
    for ln in learns_new or []:                             # [[playable.abilities]] -> a custom preset's Abilities/<id>.csv
        text, w = build_learn_file(ln["preset_name"], ln.get("abilities", []), ln.get("removes", []),
                                   read_from=ln.get("read_from"), game=game)
        p = layout.abilities_csv(ln["preset_name"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="cp1252", errors="replace", newline="\n")
        warnings += w
    return warnings


def validate_character_param(entry) -> list:
    """Offline structural problems for ``[[character_param]]`` (empty => OK; field resolution at build)."""
    if not isinstance(entry, dict):
        return ["[[character_param]] must be a table (character = \"...\", a field = value)"]
    problems = []
    if entry.get("character") is None:
        problems.append("[[character_param]] needs a 'character' (a name or a 0-11 id)")
    overrides = [k for k in entry if k != "character"]
    if not overrides:
        problems.append("[[character_param]] sets no fields (e.g. row = 1, menu_type = \"Steiner\")")
    for k in overrides:
        if k not in CHARACTER_PARAM_FIELDS:
            problems.append(f"[[character_param]]: unknown field {k!r} (known: {', '.join(sorted(CHARACTER_PARAM_FIELDS))})")
            continue
        ci, kind, vmax = CHARACTER_PARAM_FIELDS[k]
        try:
            _encode_param(entry[k], kind, vmax, f"[[character_param]] {k}")
        except CharacterDeltaError as ex:
            problems.append(str(ex))
    return problems


def validate_command_set(entry) -> list:
    """Offline structural problems for ``[[command_set]]`` (empty => OK)."""
    if not isinstance(entry, dict):
        return ["[[command_set]] must be a table (preset = \"...\", a slot = command id)"]
    problems = []
    try:
        _resolve_preset(entry.get("preset"), "[[command_set]]")
    except CharacterDeltaError as ex:
        problems.append(str(ex))
    overrides = [k for k in entry if k != "preset"]
    if not overrides:
        problems.append("[[command_set]] sets no slots (e.g. ability1 = 8)")
    for k in overrides:
        if k not in COMMANDSET_SLOTS:
            problems.append(f"[[command_set]]: unknown slot {k!r} (known: {', '.join(sorted(COMMANDSET_SLOTS))})")
            continue
        try:
            cid = _to_int(entry[k], f"[[command_set]] {k}")
            if not 0 <= cid <= _MAX_COMMAND_ID:
                problems.append(f"[[command_set]] {k}={cid} out of range (0-{_MAX_COMMAND_ID})")
        except CharacterDeltaError as ex:
            problems.append(str(ex))
    return problems


# ---- offline (no-install) structural + range validation --------------------------------------------------
def validate_character(entry) -> list:
    problems: list = []
    if not isinstance(entry, dict):
        return ["[[character]] must be a table (character = \"...\", a stat = value)"]
    ch = entry.get("character")
    if ch is None or isinstance(ch, bool):
        problems.append("[[character]] needs a 'character' (a name or a 0-11 id)")
    elif not isinstance(ch, (int, str)):
        problems.append(f"[[character]] character must be a name or a 0-11 id (got {type(ch).__name__})")
    elif isinstance(ch, str) and not ch.strip().lstrip("-").isdigit() and ch.strip().lower() not in CHARACTER_IDS:
        problems.append(f"[[character]] unknown character {ch!r}")
    overrides = [k for k in entry if k != "character"]
    if not overrides:
        problems.append(f"[[character]] {entry.get('character')!r} sets no stats (give e.g. strength = 30)")
    for k in overrides:
        spec = CHARACTER_FIELDS.get(k)
        if spec is None:
            problems.append(f"[[character]] {entry.get('character')!r}: unknown field {k!r}")
            continue
        try:
            _range(_to_int(entry[k], k), spec[1], f"[[character]] {entry.get('character')!r} {k}")
        except CharacterDeltaError as ex:
            problems.append(str(ex))
    return problems


def validate_leveling(entry) -> list:
    problems: list = []
    if not isinstance(entry, dict):
        return ["[[leveling]] must be a table (level = N, a field = value)"]
    lvl = entry.get("level")
    if lvl is None or isinstance(lvl, bool) or not isinstance(lvl, (int, str)):
        problems.append("[[leveling]] needs a 'level' (1-99)")
    else:
        try:
            lv = int(lvl)
            if not 1 <= lv <= _LEVEL_COUNT:
                problems.append(f"[[leveling]] level {lv} out of range (1-{_LEVEL_COUNT})")
        except (ValueError, TypeError):
            problems.append(f"[[leveling]] level must be an integer 1-{_LEVEL_COUNT} (got {lvl!r})")
    overrides = [k for k in entry if k != "level"]
    if not overrides:
        problems.append("[[leveling]] sets no fields (give exp / bonus_hp / bonus_mp)")
    for k in overrides:
        spec = LEVELING_FIELDS.get(k)
        if spec is None:
            problems.append(f"[[leveling]] level {entry.get('level')}: unknown field {k!r} (known: exp, bonus_hp, bonus_mp)")
            continue
        try:
            _range(_to_int(entry[k], k), spec[1], f"[[leveling]] {k}")
        except CharacterDeltaError as ex:
            problems.append(str(ex))
    return problems


def validate_ability_gem(entry) -> list:
    problems: list = []
    if not isinstance(entry, dict):
        return ["[[ability_gem]] must be a table (ability = \"...\", gems = N)"]
    ab = entry.get("ability")
    if ab is None or isinstance(ab, bool):
        problems.append("[[ability_gem]] needs an 'ability' (a SupportAbility name or a 0-63 id)")
    elif not isinstance(ab, (int, str)):
        problems.append(f"[[ability_gem]] ability must be a name or a 0-{_MAX_SA_ID} id (got {type(ab).__name__})")
    elif isinstance(ab, str) and not ab.strip().lstrip("-").isdigit() and _norm_sa(ab) not in _SA_BY_NORM:
        problems.append(f"[[ability_gem]] unknown ability {ab!r}")
    overrides = [k for k in entry if k != "ability"]
    if not overrides:
        problems.append(f"[[ability_gem]] {entry.get('ability')!r} sets no fields (give gems = N)")
    for k in overrides:
        if k != "gems":
            problems.append(f"[[ability_gem]] {entry.get('ability')!r}: unknown field {k!r} (known: gems)")
            continue
        try:
            _range(_to_int(entry[k], k), _I32, f"[[ability_gem]] {entry.get('ability')!r} gems")
        except CharacterDeltaError as ex:
            problems.append(str(ex))
    return problems
