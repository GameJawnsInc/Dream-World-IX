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

_U16 = 0xFFFF
_U32 = 0xFFFFFFFF

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


# ---- mod-write stage -------------------------------------------------------------------------------------
def write_character_data(layout, *, characters=None, levelings=None, game=None) -> list:
    """Emit BaseStats.csv / Leveling.csv into ``layout`` (mod-write stage). Returns warnings. cp1252 + LF."""
    warnings: list = []
    for entries, path, builder in ((characters, layout.base_stats_csv, build_basestats_delta),
                                   (levelings, layout.leveling_csv, build_leveling_file)):
        if entries:
            text, w = builder(entries, game=game)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="cp1252", errors="replace", newline="\n")
            warnings += w
    return warnings


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
