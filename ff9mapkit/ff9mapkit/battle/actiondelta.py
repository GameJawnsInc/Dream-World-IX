"""``[[battle_action]]`` / ``[[status]]`` -- author the shared PLAYER abilities + status definitions as
partial-CSV deltas (the kit's WIN over Hades Workshop: declarative, campaign-wide, provenance-clean).

  [[battle_action]]              # rebalance a shared ability (Actions.csv, id 0-191)
  action = "Fire"               #   name (resolved from the base CSV) or a 0-191 id
  power  = 30                   #   damage: power / element(s) / rate / mp / script / category / type
  element = ["Ice"]             #   element names -> the `elements` bitmask
  targets = "AllEnemy"          #   targeting (TargetType name/id) + menu_window (TargetDisplay) +
  default_ally = true           #   default_ally / for_dead / default_on_dead / camera (bools) + vfx1 / vfx2
  status_index = 70             #   the StatusSets.csv row this action inflicts/cures

  [[status]]                     # retune a status ailment (StatusData.csv, id 0-32)
  status = "Poison"
  tick = 30                     #   OprCount (per-tick effect, 0-255)
  duration = 0                  #   ContiCount (0 = until cured, 0-65535)
  clear_on_apply = ["Sleep"]    #   BattleStatus lists: what applying it CLEARS / what it grants IMMUNITY to
  immunity_provided = ["Poison"]

WHY a delta + read-base: the engine merges these CSVs by **whole-ROW replacement** keyed on id
(``FF9BattleDB`` / ``EnumerateCsvFromLowToHigh``), so a partial file overrides only the rows it lists while
the base supplies the rest. To change ONE field we must therefore emit the COMPLETE row with the base game's
other columns -- so this reads the base ``Actions.csv`` / ``StatusData.csv`` LIVE from the install (provenance:
the authored ``field.toml`` holds only your overrides; the emitted CSV is mod build-output, never committed).
★ The base file's ``#!`` option lines (e.g. ``#! IncludeCastingTitleType``) are LOAD-BEARING -- the engine
parses by column POSITION and ``#!`` toggles optional columns -- so the delta repeats them verbatim
(``CsvReader`` resets metadata per file). ★ The CSVs are **cp1252** (not UTF-8: a few names carry a 0x92 curly
apostrophe), read+written byte-faithfully. ★ Narrow engine column types (Byte/UInt16) are RANGE-CHECKED
offline: an out-of-range value would otherwise crash the battle DB at boot (``Byte.Parse`` overflow ->
``ConfirmQuit``). These blocks are mod-GLOBAL (always-on, not new-game-scoped); they live on a ``field.toml``
and emit at the mod-write stage. See ``docs/BATTLE_DESIGN.md`` Phase 3.
"""
from __future__ import annotations

import re

from . import battlecsv

_I32 = 2 ** 31 - 1
# friendly TOML key -> (CSV column, encoder, max). The capped columns are narrow engine types (Byte 0-255 /
# UInt16 0-65535); a value past the cap is rejected OFFLINE (else Byte.Parse overflows -> a boot crash).
ACTION_FIELDS = {
    "power": ("power", "int", _I32),
    "element": ("elements", "elements", 255), "elements": ("elements", "elements", 255),
    "rate": ("rate", "int", _I32),
    "mp": ("mp", "int", _I32),
    "script": ("scriptid", "script", _I32), "script_id": ("scriptid", "script", _I32),
    "category": ("category", "int", 255),
    "type": ("type", "int", 255),
    # targeting + presentation (cols 3-10): the engine parses these as TargetType/TargetDisplay ENUMS (by
    # ``Name(value)``), Booleans (``1``/``0``), and signed/unsigned Int16 anim ids -- see the encoders below.
    "targets": ("targets", "target_type", 0),
    "menu_window": ("menuwindow", "target_display", 0),
    "default_ally": ("defaultally", "bool", 0),
    "for_dead": ("fordead", "bool", 0),
    "default_on_dead": ("defaultondead", "bool", 0),
    "camera": ("defaultcamera", "bool", 0),
    "vfx1": ("animationid1", "sint", 32767), "animation1": ("animationid1", "sint", 32767),
    "vfx2": ("animationid2", "int", 65535), "animation2": ("animationid2", "int", 65535),
    "status_index": ("statusindex", "int", _I32),     # the StatusSets.csv row this action inflicts/cures
}
STATUS_FIELDS = {
    "tick": ("oprcount", "int", 255),
    "duration": ("conticount", "int", 65535),
    # what this status clears / blocks: a BattleStatus list (``Name(idx), ...``) via encode_status_list.
    "clear_on_apply": ("clearonapply", "statuslist", 0),
    "immunity_provided": ("immunityprovided", "statuslist", 0),
}
_ACTION_MAX_ID = 191
_STATUS_MAX_ID = 32
_STATUS_SET_MAX_ID = 65535     # StatusSetId is Int32; 0-38 are the base sets, >=39 = custom (the band an action's
#                                status_index points at). Cap generously -- catches a typo, never the real type.


class ActionDeltaError(ValueError):
    pass


def _norm_name(s: str) -> str:
    """Lowercase + straighten curly apostrophes so ``"Dragon's Crest"`` matches the cp1252 base name."""
    return s.strip().lower().replace("’", "'").replace("‘", "'")


# ---- read the base CSV (cp1252, byte-faithful), preserving the #! options + the column legend ---------
def _read_raw(path) -> tuple:
    """Parse a Memoria battle CSV for DELTA authoring -> ``(options, legend, cols, rows)``:
      * ``options`` -- the ``#!`` lines, VERBATIM (load-bearing: they toggle optional columns).
      * ``legend``  -- the ``# Comment;id;...`` header line (cosmetic; re-emitted for humans), or None.
      * ``cols``    -- column name (normalized lower, ``Foo(bar)``->``foo``) -> index.
      * ``rows``    -- ``{id: [cells...]}`` the FULL split cells of each data row (kept verbatim for re-emit).
    Decoded as cp1252 (the install's real encoding) so a 0x92 apostrophe round-trips byte-faithfully."""
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):                 # strip a stray UTF-8 BOM if one ever appears
        data = data[3:]
    options: list = []
    legend = None
    cols: "dict | None" = None
    rows: dict = {}
    for raw in data.decode("cp1252", errors="replace").splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("#!"):
            options.append(s)
            continue
        if s.startswith("#"):
            if cols is None:
                fields = [f.strip().split("(")[0].strip().lower() for f in s.lstrip("#").strip().split(";")]
                if "id" in fields and len(fields) > 1:
                    cols = {name: i for i, name in enumerate(fields)}
                    legend = s
            continue
        if cols is None:
            continue
        cells = raw.split(";")
        idx = cols["id"]
        if idx >= len(cells):
            continue
        try:
            rid = int(cells[idx].strip())
        except ValueError:
            continue
        rows[rid] = cells
    return options, legend, (cols or {}), rows


def _name_index(rows, cols) -> dict:
    """``{normalized Comment name: [ids]}`` from the base rows (a name may map to several ids -> ambiguous)."""
    nidx = cols.get("comment", 0)
    out: dict = {}
    for rid, cells in rows.items():
        if nidx < len(cells):
            nm = _norm_name(cells[nidx].split("#")[0])
            if nm:
                out.setdefault(nm, []).append(rid)
    return out


def _resolve_id(token, rows, names, *, kind, max_id):
    if token is None or isinstance(token, bool):
        raise ActionDeltaError(f"[[{kind}]] needs a '{kind}' (a name or a 0-{max_id} id)")
    if isinstance(token, int) or (isinstance(token, str) and token.strip().lstrip("-").isdigit()):
        rid = int(token)
        if not 0 <= rid <= max_id:
            raise ActionDeltaError(f"[[{kind}]] id {rid} out of range (0-{max_id})")
        if rid not in rows:
            raise ActionDeltaError(f"[[{kind}]] id {rid} is not in the base CSV")
        return rid
    ids = names.get(_norm_name(str(token)))
    if not ids:
        raise ActionDeltaError(f"[[{kind}]] unknown name {token!r} (not a row in the base CSV)")
    if len(ids) > 1:
        raise ActionDeltaError(f"[[{kind}]] name {token!r} is ambiguous (ids "
                               f"{', '.join(str(i) for i in sorted(ids))}) -- use the id")
    return ids[0]


# ---- value encoding + range guard (shared by build + offline validate) --------------------------------
def _to_int(value, key) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ActionDeltaError(f"{key} must be an integer (got {value!r})")
    try:
        return int(value)
    except ValueError:
        raise ActionDeltaError(f"{key} must be an integer (got {value!r})")


def _resolve_script(value) -> int:
    if isinstance(value, str) and not value.strip().lstrip("-").isdigit():
        sid = {n.lower(): i for i, n in battlecsv.SCRIPT_IDS.items()}.get(value.strip().lower())
        if sid is None:
            raise ActionDeltaError(f"unknown scriptId formula {value!r} (see `ff9mapkit battle-actions "
                                   f"--script-ids`)")
        return sid
    return _to_int(value, "script")


def _encode_value(key, value, spec, *, warnings=None) -> str:
    """Resolve + RANGE-CHECK an override value -> the CSV cell string. Raises ActionDeltaError offline (so a
    bad value fails the build/lint, never the game). ``warnings`` (optional) collects the script-catalog note."""
    col, enc, vmax = spec
    if enc == "int":
        v = _to_int(value, key)
    elif enc == "sint":                                  # a SIGNED column (Int16 anim id): -vmax-1 .. vmax
        v = _to_int(value, key)
        if not -(vmax + 1) <= v <= vmax:
            raise ActionDeltaError(f"{key}={v} out of range ({-(vmax + 1)}..{vmax})")
        return str(v)
    elif enc == "bool":
        return _encode_bool(value, key)                  # the CSV stores Booleans as 1/0
    elif enc in ("target_type", "target_display", "statuslist"):
        fn = {"target_type": battlecsv.encode_target_type, "target_display": battlecsv.encode_target_display,
              "statuslist": battlecsv.encode_status_list}[enc]
        try:
            return fn(value)                             # returns the final cell string (Name(value) / Name(idx) list)
        except (ValueError, TypeError) as ex:
            raise ActionDeltaError(f"{key}: {ex}")
    elif enc == "elements":
        try:
            v = battlecsv.encode_elements(value)
        except (ValueError, TypeError) as ex:
            raise ActionDeltaError(f"{key}: {ex}")
    elif enc == "script":
        v = _resolve_script(value)
        if warnings is not None and not battlecsv.is_stock_script(v):
            warnings.append(f"scriptId {v} is not in the externalized formula catalog -- re-pointing an action "
                            f"at an existing (incl. base-engine) formula is data, but a BRAND-NEW formula needs "
                            f"a Memoria.Scripts.<Mod>.dll (not the engine DLL)")
    else:
        raise ActionDeltaError(f"internal: bad encoder {enc!r}")
    if not 0 <= v <= vmax:
        raise ActionDeltaError(f"{key}={v} out of range (0-{vmax})")
    return str(v)


def _encode_bool(value, key) -> str:
    """A bool / 0|1 / "true"|"false" -> the CSV "1"/"0" cell."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int) and value in (0, 1):
        return str(value)
    if isinstance(value, str) and value.strip().lower() in ("0", "1", "true", "false"):
        return "1" if value.strip().lower() in ("1", "true") else "0"
    raise ActionDeltaError(f"{key} must be a boolean (true/false or 1/0)")


def _apply_entries(entries, rows, cols, names, fields_map, *, kind, max_id) -> tuple:
    """Apply ``[[kind]]`` override dicts onto the base ``rows`` in place. Returns (changed_ids, warnings)."""
    warnings: list = []
    changed: dict = {}                                  # id -> first entry index that touched it (dup lint)
    selector = "action" if kind == "battle_action" else "status"
    for n, e in enumerate(entries):
        rid = _resolve_id(e.get(selector), rows, names, kind=kind, max_id=max_id)
        if rid in changed:
            warnings.append(f"[[{kind}]] #{n} and #{changed[rid]} both target id {rid} -- they MERGE (a field "
                            f"set by both: the later wins)")
        changed.setdefault(rid, n)
        cells = rows[rid]
        for k, v in e.items():
            if k == selector:
                continue
            if k not in fields_map:
                raise ActionDeltaError(f"[[{kind}]] {e.get(selector)!r}: unknown field {k!r} "
                                       f"(known: {', '.join(sorted(fields_map))})")
            col = fields_map[k][0]
            ci = cols.get(col)
            if ci is None:
                warnings.append(f"[[{kind}]]: column {col!r} not present in this install's CSV -- {k} skipped")
                continue
            if ci >= len(cells):
                raise ActionDeltaError(f"[[{kind}]] id {rid}: base row has no column {col!r}")
            try:
                cells[ci] = _encode_value(k, v, fields_map[k], warnings=warnings)
            except ActionDeltaError as ex:
                raise ActionDeltaError(f"[[{kind}]] {e.get(selector)!r} {ex}")
    return list(changed), warnings


def _render(options, legend, rows, changed_ids, *, note) -> str:
    lines = [note]
    lines += options                                    # the #! option lines, VERBATIM (load-bearing)
    if legend:
        lines.append(legend)                            # the column legend (cosmetic, for humans)
    for rid in sorted(changed_ids):
        lines.append(";".join(rows[rid]))
    return "\n".join(lines) + "\n"


# ---- public: read the install + build the delta text -------------------------------------------------
def _csv_path(name, game):
    from ..config import find_game_path
    return find_game_path(game) / "StreamingAssets" / "Data" / "Battle" / name


def _build(name, entries, fields_map, *, kind, max_id, note, game):
    try:
        options, legend, cols, rows = _read_raw(_csv_path(name, game))
    except (FileNotFoundError, OSError, RuntimeError) as ex:   # incl. config.ConfigError (install not found)
        raise ActionDeltaError(f"[[{kind}]] needs your FF9 install to read the base {name} ({ex})")
    if not cols or not rows:
        raise ActionDeltaError(f"could not parse the base {name} (no id column / no rows)")
    changed, warnings = _apply_entries(entries, rows, cols, _name_index(rows, cols),
                                       fields_map, kind=kind, max_id=max_id)
    return _render(options, legend, rows, changed, note=note), warnings


# A NEW custom active ability (a 13th character's unique spell) is a NEW Actions.csv id past the packed base 0-191.
# The engine's aa_data is a Dictionary (FF9StateBattleSystem: no array bound) + the loader gate is a FLOOR (0-191 must
# exist, FF9BattleDB.cs:63) -> a per-id delta ADDS 192+. The BattleAbilityId space is "pooled" (÷192/×256); a ListEntry
# value V in 192-223 lands in pool 1 (idInPool 0-31, all ACTIVE), so the display/cast/learn round-trip is clean. RENDER
# safety = CLONE a stock donor row (keeps its animationId1/2 VFX + scriptId formula + targets valid) and override only
# the tuning fields -> the spell casts + animates as the donor but with Iviv's own power/element/mp. (project-ff9-ability-preset-system)
_CUSTOM_ACTION_MIN = 192
_CUSTOM_ACTION_MAX = 223
# The tuning fields an inline custom ability may override (a SAFE subset of ACTION_FIELDS): all range-guarded numeric /
# element / enum columns. `status_index` is EXCLUDED from the AUTHOR-facing overrides -- it points at a StatusSets ROW
# and the engine indexes add_status[statusIndex] with a DIRECT (KeyNotFound-throwing) indexer at cast, so a bad set = a
# crash. Instead a custom ability's `status = [...]` list is AUTO-MINTED into a StatusSets row (below) and the kit
# injects the resulting id as a TRUSTED `status_index` on the seed (the "SAFE because the row exists" invariant).
_CUSTOM_ACTION_OVERRIDES = frozenset(ACTION_FIELDS) - {"status_index"}
# The auto-minted StatusSets band for a custom ability's `status = [...]` (base sets are 0-38, hand-authored
# `[[status_set]]` are >=39; the auto band starts at 100 to stay clear of both). A row here is emitted in the SAME build.
_CUSTOM_STATUS_SET_MIN = 100
# scriptIds whose formula APPLIES the action's status set (calls TryAlter*Statuses): 9 MagicAttack, 11
# MagicApplyNegativeStatus, 103 MagicApplyPositiveStatus. A custom status spell should clone one of these donors --
# else the set is valid but nothing lands (a silent no-op the build warns about).
_STATUS_APPLYING_SCRIPTS = {"9", "11", "103"}


def _apply_new_actions(new_rows, rows, cols, names, warnings) -> list:
    """Mint custom NEW abilities: CLONE a donor row, re-id into the custom band (>=192), rename (the Comment cell +
    trailing ``# name``), and apply the safe overrides. Adds each new row into ``rows`` in place; returns the minted
    ids. A donor clone keeps every render/formula ref valid so the spell can't crash (recon lens C)."""
    minted, seen = [], set()
    idc, cmtc = cols.get("id"), cols.get("comment", 0)
    for n, nr in enumerate(new_rows if isinstance(new_rows, list) else [new_rows]):
        ctx = f"[[battle_ability]] #{n}"
        if not isinstance(nr, dict):
            raise ActionDeltaError(f"{ctx} must be a table")
        aid = _to_int(nr.get("id"), f"{ctx} id")
        if not _CUSTOM_ACTION_MIN <= aid <= _CUSTOM_ACTION_MAX:
            raise ActionDeltaError(f"{ctx}: custom ability id {aid} out of the band "
                                   f"{_CUSTOM_ACTION_MIN}-{_CUSTOM_ACTION_MAX} (0-191 are the packed base)")
        if aid in rows or aid in seen:
            raise ActionDeltaError(f"{ctx}: custom ability id {aid} is already defined")
        seen.add(aid)
        donor = _resolve_id(nr.get("from"), rows, names, kind="battle_ability from", max_id=_ACTION_MAX_ID)
        name = str(nr.get("name") or "").strip()
        if not name:
            raise ActionDeltaError(f"{ctx}: a custom ability needs a 'name'")
        if ";" in name or name.lstrip().startswith("#"):
            raise ActionDeltaError(f"{ctx}: name {name!r} can't contain ';' or start with '#' "
                                   f"(it would shift the CSV columns -> a boot crash)")
        cells = list(rows[donor])                          # clone the donor row VERBATIM (valid vfx/script/targets)
        if idc is not None and idc < len(cells):
            cells[idc] = str(aid)
        if cmtc < len(cells):
            cells[cmtc] = name
        if cells and cells[-1].lstrip().startswith("#"):   # the trailing "# Comment" cell -> the new name
            cells[-1] = f"# {name}"
        for k, v in (nr.get("overrides") or {}).items():
            if k not in _CUSTOM_ACTION_OVERRIDES:
                extra = " (clone a status-inflicting donor instead)" if k in ("status_index",) else ""
                raise ActionDeltaError(f"{ctx} {name!r}: field {k!r} can't be set on a custom ability{extra} "
                                       f"(overridable: {', '.join(sorted(_CUSTOM_ACTION_OVERRIDES))})")
            col = ACTION_FIELDS[k][0]
            ci = cols.get(col)
            if ci is None or ci >= len(cells):
                warnings.append(f"{ctx}: column {col!r} not present in this install's CSV -- {k} skipped")
                continue
            try:
                cells[ci] = _encode_value(k, v, ACTION_FIELDS[k], warnings=warnings)
            except ActionDeltaError as ex:
                raise ActionDeltaError(f"{ctx} {name!r} {ex}")
        # a KIT-INJECTED status_index = the id of an auto-minted StatusSets row (from `status = [...]`) -> SAFE because
        # that row is emitted in the SAME build. The author can't set status_index directly (excluded above). Warn on
        # the two silent-no-op traps: rate=0 (the HitRate gate never passes) + a non-status-applying donor script.
        si = nr.get("status_index")
        if si is not None:
            sc = cols.get("statusindex")
            if sc is not None and sc < len(cells):
                cells[sc] = str(_to_int(si, f"{ctx} status_index"))
                rc, scr = cols.get("rate"), cols.get("scriptid")
                if rc is not None and rc < len(cells) and cells[rc].strip() in ("0", ""):
                    warnings.append(f"{ctx} {name!r}: inflicts a status but rate=0 -> it will (almost) never land; "
                                    f"give it a rate (e.g. rate = 50)")
                if scr is not None and scr < len(cells) and cells[scr].strip() not in _STATUS_APPLYING_SCRIPTS:
                    warnings.append(f"{ctx} {name!r}: inflicts a status but the donor's script ({cells[scr].strip()}) "
                                    f"may not APPLY it -- clone a status-applying magic donor (e.g. from = \"Bio\")")
        rows[aid] = cells
        minted.append(aid)
    return minted


def build_actions_delta(entries, *, new_rows=(), game=None) -> tuple:
    """Read the base Actions.csv + apply ``[[battle_action]]`` retunes (existing ids 0-191) AND mint any custom NEW
    abilities (``new_rows``, cloned into the >=192 band) -> ONE merged partial Actions.csv delta ``(text, warnings)``.
    Both share one emission (the file is written once) so a minted action can't clobber a retune or vice-versa."""
    note = ("# ff9mapkit [[battle_action]] / minted custom ability -- a partial Actions.csv delta (merged over the "
            "base by the engine; the #! lines below are load-bearing).")
    try:
        options, legend, cols, rows = _read_raw(_csv_path("Actions.csv", game))
    except (FileNotFoundError, OSError, RuntimeError) as ex:
        raise ActionDeltaError(f"[[battle_action]] needs your FF9 install to read the base Actions.csv ({ex})")
    if not cols or not rows:
        raise ActionDeltaError("could not parse the base Actions.csv (no id column / no rows)")
    names = _name_index(rows, cols)
    changed, warnings = _apply_entries(entries or [], rows, cols, names, ACTION_FIELDS,
                                       kind="battle_action", max_id=_ACTION_MAX_ID)
    minted = _apply_new_actions(new_rows or [], rows, cols, names, warnings)
    changed = list(changed) + [m for m in minted if m not in changed]
    return _render(options, legend, rows, changed, note=note), warnings


def build_status_delta(entries, *, game=None) -> tuple:
    note = ("# ff9mapkit [[status]] -- a partial StatusData.csv delta (merged over the base by the engine; "
            "the #! lines below are load-bearing).")
    return _build("StatusData.csv", entries, STATUS_FIELDS, kind="status", max_id=_STATUS_MAX_ID,
                  note=note, game=game)


def build_status_sets(entries, *, game=None) -> tuple:
    """``[[status_set]]`` -> a partial ``StatusSets.csv`` (the named multi-status BUNDLES an action's
    ``status_index`` points at). Emits ONLY the author's rows -- the engine merges low->high BY ID
    (``FF9BattleDB.LoadStatusSets``), so no base read is needed (fully offline + provenance-clean). Row format
    ``Name;Id;StatusList`` with ``#! UnshiftStatuses`` (the ``Name(idx)`` status list, reusing the StatusData
    encoder). Returns (text, warnings)."""
    note = ("# ff9mapkit [[status_set]] -- a partial StatusSets.csv (merged per-id over the base; ids 0-38 are "
            "the base sets, use >=39 for a custom one). An action points at a set via its `status_index`.")
    lines, warnings, seen = [note, "#! UnshiftStatuses"], [], {}
    for n, e in enumerate(entries if isinstance(entries, list) else [entries]):
        ctx = f"[[status_set]] #{n}"
        if not isinstance(e, dict):
            raise ActionDeltaError(f"{ctx} must be a table")
        sid = _to_int(e.get("id"), f"{ctx} id")
        if not 0 <= sid <= _STATUS_SET_MAX_ID:
            raise ActionDeltaError(f"{ctx}: id {sid} out of range (0-{_STATUS_SET_MAX_ID}; 0-38 = base sets, "
                                   f">=39 = custom)")
        if sid in seen:
            warnings.append(f"{ctx}: id {sid} already set by #{seen[sid]} -- the later wins")
        seen[sid] = n
        name = re.sub(r"[;\r\n]+", " ", str(e.get("name", f"Set {sid}"))).strip() or f"Set {sid}"
        try:
            statuses = battlecsv.encode_status_list(e.get("statuses"))
        except (ValueError, TypeError) as ex:
            raise ActionDeltaError(f"{ctx}: {ex}")
        lines.append(f"{name};{sid};{statuses};# {name}")
    return "\n".join(lines) + "\n", warnings


def validate_status_sets(entries) -> list:
    """Offline structural + range problems for ``[[status_set]]`` (empty => OK)."""
    try:
        build_status_sets(entries)
    except ActionDeltaError as ex:
        return [str(ex)]
    return []


def _ability_list(value, ctx) -> str:
    """A list of active-ability ids (0-191, or ``"AA:n"`` tokens) -> the ``AA:n, AA:n`` Ability[] cell."""
    if value is None:
        return ""
    out = []
    for a in (value if isinstance(value, list) else [value]):
        if isinstance(a, str) and a.strip().upper().startswith("AA:"):
            a = a.strip()[3:]
        aid = _to_int(a, ctx)
        if not 0 <= aid <= _ACTION_MAX_ID:
            raise ActionDeltaError(f"{ctx}: ability id {aid} out of range (0-{_ACTION_MAX_ID})")
        out.append(f"AA:{aid}")
    return ", ".join(out)


def build_magic_sword_sets(entries, *, game=None) -> tuple:
    """``[[magic_sword_set]]`` -> a partial ``MagicSwordSets.csv`` (Steiner+Vivi-style combo unlocks): a
    Supporter's BaseAbilities unlock the Beneficiary's UnlockedAbilities, unless a blocking status is present.
    Per-id partial merge (``LoadMagicSwordSets`` via ``EnumerateCsvFromLowToHigh``) -> emits ONLY the author's
    rows (no base read; offline + provenance-clean). Row ``Id;Sup;Ben;AA[];AA[];Status[];Status[]``."""
    from . import characterdelta as _cd
    note = ("# ff9mapkit [[magic_sword_set]] -- a partial MagicSwordSets.csv (merged per-id over the base). The "
            "Supporter's base_abilities unlock the Beneficiary's unlocked_abilities (e.g. Vivi's Black Magic -> "
            "Steiner's Magic Sword), unless a blocking status is on the supporter/beneficiary.")
    lines, warnings, seen = [note, "#! IncludeStatusBlockers"], [], {}
    for n, e in enumerate(entries if isinstance(entries, list) else [entries]):
        ctx = f"[[magic_sword_set]] #{n}"
        if not isinstance(e, dict):
            raise ActionDeltaError(f"{ctx} must be a table")
        sid = _to_int(e.get("id"), f"{ctx} id")
        if not 0 <= sid <= _STATUS_SET_MAX_ID:
            raise ActionDeltaError(f"{ctx}: id {sid} out of range (0-{_STATUS_SET_MAX_ID})")
        if sid in seen:
            warnings.append(f"{ctx}: id {sid} already set by #{seen[sid]} -- the later wins")
        seen[sid] = n
        try:
            sup, ben = _cd._resolve_char_id(e.get("supporter")), _cd._resolve_char_id(e.get("beneficiary"))
        except _cd.CharacterDeltaError as ex:
            raise ActionDeltaError(f"{ctx} (supporter/beneficiary): {str(ex).split(': ', 1)[-1]}")
        base = _ability_list(e.get("base_abilities"), f"{ctx} base_abilities")
        unlocked = _ability_list(e.get("unlocked_abilities"), f"{ctx} unlocked_abilities")
        try:
            sup_b = battlecsv.encode_status_list(e.get("supporter_blocking_status"))
            ben_b = battlecsv.encode_status_list(e.get("beneficiary_blocking_status"))
        except (ValueError, TypeError) as ex:
            raise ActionDeltaError(f"{ctx}: {ex}")
        cmt = re.sub(r"[;\r\n]+", " ", str(e.get("name", f"magic sword set {sid}"))).strip() or f"set {sid}"
        lines.append(f"{sid};{sup};{ben};{base};{unlocked};{sup_b};{ben_b};# {cmt}")
    return "\n".join(lines) + "\n", warnings


def validate_magic_sword_sets(entries) -> list:
    """Offline structural + range problems for ``[[magic_sword_set]]`` (empty => OK)."""
    try:
        build_magic_sword_sets(entries)
    except ActionDeltaError as ex:
        return [str(ex)]
    return []


def write_battle_data(layout, *, actions=None, statuses=None, status_sets=None, magic_sword_sets=None,
                      new_actions=None, game=None) -> list:
    """Emit the Actions / StatusData / StatusSets / MagicSwordSets CSV deltas into ``layout`` (mod-write stage).
    Returns warnings. Written cp1252 (byte-faithful with the base) + LF; the engine StreamReader is EOL-agnostic.
    ``new_actions`` mints custom NEW abilities (id >=192) into the SAME Actions.csv delta as the ``[[battle_action]]``
    retunes -- one emission, so neither clobbers the other."""
    warnings: list = []
    if actions or new_actions:                              # Actions.csv: retunes + minted custom abilities, ONE file
        text, w = build_actions_delta(actions or [], new_rows=new_actions or [], game=game)
        layout.actions_csv.parent.mkdir(parents=True, exist_ok=True)
        layout.actions_csv.write_text(text, encoding="cp1252", errors="replace", newline="\n")
        warnings += w
    for entries, path, builder in ((statuses, layout.status_data_csv, build_status_delta),
                                   (status_sets, layout.status_sets_csv, build_status_sets),
                                   (magic_sword_sets, layout.magic_sword_sets_csv, build_magic_sword_sets)):
        if entries:
            text, w = builder(entries, game=game)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="cp1252", errors="replace", newline="\n")
            warnings += w
    return warnings


# ---- offline (no-install) structural + range validation ----------------------------------------------
def validate_entry(entry, *, kind) -> list:
    """Checks that don't need the install: structural + the value range/encoders (so `lint` catches an
    out-of-Byte-range value or a bad element/script name offline). The name->id resolution of the
    action/status itself happens at build (which has the install to read the base row)."""
    fields_map = ACTION_FIELDS if kind == "battle_action" else STATUS_FIELDS
    selector = "action" if kind == "battle_action" else "status"
    problems: list = []
    if not isinstance(entry, dict):
        return [f"[[{kind}]] must be a table ({selector} = \"...\", a field = value)"]
    if entry.get(selector) is None or isinstance(entry.get(selector), bool):
        problems.append(f"[[{kind}]] needs a '{selector}' (a name or an id)")
    overrides = [k for k in entry if k != selector]
    if not overrides:
        problems.append(f"[[{kind}]] {entry.get(selector)!r} sets no fields (give e.g. "
                        f"{'power = 30' if kind == 'battle_action' else 'tick = 30'})")
    for k in overrides:
        if k not in fields_map:
            problems.append(f"[[{kind}]] {entry.get(selector)!r}: unknown field {k!r} "
                            f"(known: {', '.join(sorted(fields_map))})")
            continue
        try:
            _encode_value(k, entry[k], fields_map[k])
        except ActionDeltaError as ex:
            problems.append(f"[[{kind}]] {entry.get(selector)!r} {ex}")
    return problems
