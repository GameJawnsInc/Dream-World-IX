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


def build_basestats_delta(entries, *, game=None) -> tuple:
    """Read the base BaseStats.csv + apply ``[[character]]`` entries -> (delta_text, warnings). A PARTIAL delta:
    only the changed character rows are emitted; the engine supplies the rest per-id."""
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


def _resolve_preset(token, ctx="[[learn]]"):
    """A CharacterPresetId name or 0-19 id -> (id, canonical_name). Bare Cinna/Marcus/Blank/Beatrix = ambiguous."""
    if token is None or isinstance(token, bool):
        raise CharacterDeltaError(f"{ctx} needs a 'preset' (a CharacterPresetId name or a 0-{_MAX_PRESET_ID} id)")
    if isinstance(token, int) or (isinstance(token, str) and token.strip().lstrip("-").isdigit()):
        pid = int(token)
        if not 0 <= pid <= _MAX_PRESET_ID:
            raise CharacterDeltaError(f"{ctx} preset id {pid} out of range (0-{_MAX_PRESET_ID})")
        return pid, _PRESET_NAMES[pid]
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
    if kind == "preset" and isinstance(value, str) and not value.strip().lstrip("-").isdigit():
        return str(_range(_resolve_preset(value, key)[0], vmax, key))
    return str(_range(_to_int(value, key), vmax, key))


def build_character_params_delta(entries, *, game=None) -> tuple:
    """Read CharacterParameters.csv + apply ``[[character_param]]`` -> (partial delta, warnings). PER-id (0-11):
    only the changed rows are emitted; the base supplies the rest. Columns are written by FIXED INDEX."""
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


# ---- [[command_set]] -> CommandSets.csv (PARTIAL per-preset; tab-padded -> strip + index slots by position) ----
COMMANDSET_SLOTS = {
    "attack": 1, "defend": 2, "ability1": 3, "ability2": 4, "item": 5, "change": 6,
    "attack_trance": 7, "defend_trance": 8, "ability1_trance": 9, "ability2_trance": 10,
    "item_trance": 11, "change_trance": 12,
}
_MAX_COMMAND_ID = 47           # BattleCommandId slot value; >=48 = system/boundary


def build_command_set_delta(entries, *, game=None) -> tuple:
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
    note = "# ff9mapkit [[command_set]] -- a partial CommandSets.csv delta (merged per-preset over the base)."
    return "\n".join([note] + header + [";".join(by_id[c]) for c in sorted(changed)]) + "\n", warnings


# ---- mod-write stage -------------------------------------------------------------------------------------
def write_character_data(layout, *, characters=None, levelings=None, ability_gems=None, character_params=None,
                         command_sets=None, game=None) -> list:
    """Emit BaseStats / Leveling / AbilityGems / CharacterParameters / CommandSets into ``layout``. cp1252 + LF."""
    warnings: list = []
    for entries, path, builder in ((characters, layout.base_stats_csv, build_basestats_delta),
                                   (levelings, layout.leveling_csv, build_leveling_file),
                                   (ability_gems, layout.ability_gems_csv, build_ability_gems_delta),
                                   (character_params, layout.character_parameters_csv, build_character_params_delta),
                                   (command_sets, layout.command_sets_csv, build_command_set_delta)):
        if entries:
            text, w = builder(entries, game=game)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="cp1252", errors="replace", newline="\n")
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
