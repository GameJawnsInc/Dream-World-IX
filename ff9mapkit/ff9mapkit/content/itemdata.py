"""``[[weapon]]`` / ``[[armor]]`` / ``[[item]]`` -- tune EXISTING item stats via partial CSV deltas (no DLL).

The engine MERGES ``Data/Items/{Weapons,Armors,Items}.csv`` by id low->high, **whole-row-wins**
(``AssetManager.EnumerateCsvFromLowToHigh``), so a mod ships a PARTIAL delta = the base file's header block
(verbatim, so ``CsvReader`` parses the same columns + ``#!`` options) + only the patched rows, each COMPLETE.

The base rows are read LIVE from the user's install (the same provenance-clean pattern as :mod:`ff9mapkit.itemstats`)
-- so the kit commits NO game data; the delta is GENERATED at build time into the mod folder. Item-data patches
therefore need a reachable install (they degrade with a clear error otherwise).

* ``[[weapon]]`` patches the item's ItemAttack (``Weapons.csv``: ``Power`` / ``Elements`` + ``category`` /
  ``status_index`` / ``rate`` -- the weapon's class, the ``StatusSets.csv`` row it inflicts on hit, and that
  status's percent chance), located via the item's ``WeaponId`` in ``Items.csv``.
* ``[[armor]]`` patches its ItemDefence (``Armors.csv``: ``P.Def`` / ``P.Eva`` / ``M.Def`` / ``M.Eva``) via ``ArmorId``.
* ``[[item]]`` patches its ItemInfo (``Items.csv``: ``Price`` / ``SellingPrice`` + ``equippable_by`` -- the list of
  characters who can equip it, which REWRITES the item's 12 equip-by-character bits) by item id directly.

    [[weapon]]
    name = "Mage Masher"
    power = 30
    elements = ["Fire"]
    category = ["short-range", "throw"]   # weapon class (here: throwable)
    status_index = 9                      # a StatusSets.csv row -> the status it can inflict on hit
    rate = 30                             # 30% chance to inflict that status

    [[armor]]
    name = "Bronze Armor"
    p_def = 20

    [[item]]
    name = "Excalibur"
    price = 5000
    equippable_by = ["Vivi", "Garnet"]   # exactly these characters can equip it (replaces the current set)

* ``[[equip_bonus]]`` patches the item's ItemStats (``Stats.csv``: the equip stat bonuses ``speed`` / ``strength`` /
  ``magic`` / ``spirit`` -- the input the engine's level-up accumulator reads, ``ff9play.cs:302-305`` -- plus the
  elemental-affinity bitmasks ``attack_element`` / ``guard_element`` / ``absorb_element`` / ``half_element`` /
  ``weak_element``), located via the item's ``BonusId`` in ``Items.csv``. ★ ``BonusId`` is SHARED: ~100 items point
  at the all-zero ``Empty`` row 0, so a block on such an item can't edit row 0 in place (it would buff every other
  no-bonus item) -- it MINTS a fresh ``Stats.csv`` row and repoints the item's ``BonusId`` in an ``Items.csv`` delta,
  isolating the edit. An item whose ``BonusId`` is dedicated (used by it alone) is edited in place.

    [[equip_bonus]]
    name = "Bone Wrist"
    strength = 3
    weak_element = ["Fire"]
"""
from __future__ import annotations

from .. import items as _items
from .. import itemstats as _itemstats

POWER_CAP = 255           # weapon Power / armor defence are small byte-range values in practice
PRICE_CAP = 9_999_999     # gil cap; a price above it is pointless (you can't hold that much gil)
RATE_CAP = 100            # a weapon's status-infliction Rate is a 0-100 percent chance (the engine clamps all
                          # accuracy to 100 -- BattleCalculator.cs; physical hit is fixed 100, so Rate ONLY gates
                          # the on-hit status, applied from add_status[StatusIndex] -- SBattleCalculator.cs:188).
STATUS_INDEX_CAP = 65535  # StatusIndex references a StatusSets.csv row; the REAL membership check is install-gated
                          # in build.validate (an over-range id is a KeyNotFound crash, like the Phase-4 trap).
_ELEM_BY_NAME = {name.lower(): bit for bit, name in _itemstats.ELEMENTS}   # "fire" -> 1, ...


def _norm(s) -> str:
    """Loose name key: lowercased, alphanumerics only -- so "short-range" / "ShortRange" / "short range" match."""
    return "".join(ch for ch in str(s).strip().lower() if ch.isalnum())


# WeaponCategory bits (Memoria.Data.WeaponCategory) by friendly name (+ the engine enum name "OfsDim" for bit 8).
_CATEGORY_BY_NAME = {_norm(name): bit for bit, name in _itemstats.WEAPON_CATEGORY}
_CATEGORY_BY_NAME["ofsdim"] = 8
_CHAR_BY_NAME = {c.lower(): c for c in _itemstats.CHARS}   # equip-by-character names -> canonical CHARS

# Which Items.csv FK column + which target CSV a block patches, and the editable {toml key: CSV column} maps.
_WEAPON_COLS = {"power": "Power", "elements": "Elements",
                "category": "Category", "status_index": "StatusIndex", "rate": "Rate"}
_ARMOR_COLS = {"p_def": "P.Def", "p_eva": "P.Eva", "m_def": "M.Def", "m_eva": "M.Eva"}
_ITEM_COLS = {"price": "Price", "sell": "SellingPrice"}    # equippable_by is handled separately (12-column rewrite)

STAT_CAP = 255            # equip stat bonuses (dex/str/mgc/wpr) are Byte columns in Stats.csv (ItemStats.cs)
# [[equip_bonus]] -> the ItemStats (Stats.csv) row of an EQUIPPABLE item: the 4 growth-stat bonuses (the input
# the 32-level level-up accumulator reads, ff9play.cs:302-305) + the 5 elemental-affinity bitmask columns. Keys
# map to the Stats.csv legend (★ Dexterity = FF9 "Speed", Will = FF9 "Spirit").
_EQUIP_BONUS_STATS = {"speed": "Dexterity", "strength": "Strength", "magic": "Magic", "spirit": "Will"}
# Keys 1:1 with the Stats.csv column names (so the emitted delta matches the file the user can inspect). Engine
# meaning (ItemStats.cs raw[6..10] -> p_up_attr/def_attr): attack_element = STRENGTHENS attacks/magic of that
# element (a damage boost while worn), NOT "adds the element on hit"; guard_element = NULLIFY (immune); the other
# three = absorb (heal from) / take half / take extra damage. All are Byte element bitmasks.
_EQUIP_BONUS_ELEMS = {"attack_element": "AttackElement", "guard_element": "GuardElement",
                      "absorb_element": "AbsorbElement", "half_element": "HalfElement",
                      "weak_element": "WeakElement"}
EQUIP_BONUS_KEYS = (*_EQUIP_BONUS_STATS, *_EQUIP_BONUS_ELEMS)


def encode_elements(names) -> int:
    """A list of element names (or a 0-255 bitmask int) -> the element bitmask. Raises ValueError on an unknown
    name, an out-of-range / wrong-typed value. ★ Range-checked: the Elements column is a Byte (element bits sum to
    255), so a bare int MUST be 0..255 -- else the engine's ``Byte.Parse`` OverflowExceptions and HARD-QUITS at
    weapon load. Every bad input raises ValueError so the single ``except ValueError`` in build/validate suffices."""
    if isinstance(names, bool):                           # bool is an int subclass -- reject before the int path
        raise ValueError("elements must be a list of element names or a 0-255 bitmask, not a bool")
    if isinstance(names, int):
        if not 0 <= names <= 255:
            raise ValueError(f"element bitmask {names} out of range 0..255")
        return names
    if names is None:
        return 0
    if not isinstance(names, (list, tuple)):
        raise ValueError(f"elements must be a list of element names (or a 0-255 bitmask), got {names!r}")
    mask = 0
    for n in names:
        bit = _ELEM_BY_NAME.get(str(n).strip().lower())
        if bit is None:
            raise ValueError(f"unknown element {n!r} (one of {', '.join(nm for _, nm in _itemstats.ELEMENTS)})")
        mask |= bit
    return mask


def encode_category(names) -> int:
    """A list of weapon-category names (``short-range`` / ``long-range`` / ``throw`` / ``offset``) OR a 0-255
    bitmask int -> the WeaponCategory byte. Raises ValueError on an unknown name / out-of-range value -- the
    Category column is a ``CsvParser.Byte`` so a >255 int would OverflowException + HARD-QUIT at weapon load
    (the same trap as ``elements``). ``throw`` makes the weapon eligible for Amarant's Throw command."""
    if isinstance(names, bool):
        raise ValueError("category must be a list of category names or a 0-255 bitmask, not a bool")
    if isinstance(names, int):
        if not 0 <= names <= 255:
            raise ValueError(f"category bitmask {names} out of range 0..255")
        return names
    if names is None:
        return 0
    if not isinstance(names, (list, tuple)):
        raise ValueError(f"category must be a list of category names (or a 0-255 bitmask), got {names!r}")
    mask = 0
    for n in names:
        bit = _CATEGORY_BY_NAME.get(_norm(n))
        if bit is None:
            raise ValueError(f"unknown weapon category {n!r} "
                             f"(one of {', '.join(nm for _, nm in _itemstats.WEAPON_CATEGORY)})")
        mask |= bit
    return mask


def encode_characters(names) -> list:
    """A list of party-character names -> the canonical :data:`itemstats.CHARS` subset (de-duped, validated).
    Raises ValueError on a non-list or an unknown name. ``[[item]] equippable_by`` uses this to REWRITE the 12
    equip-by-character bits of an item (the listed characters can equip it; everyone else cannot)."""
    if not isinstance(names, (list, tuple)):
        raise ValueError(f"equippable_by must be a list of character names (any of {', '.join(_itemstats.CHARS)})")
    out: list = []
    for n in names:
        c = _CHAR_BY_NAME.get(str(n).strip().lower())
        if c is None:
            raise ValueError(f"unknown character {n!r} (one of {', '.join(_itemstats.CHARS)})")
        if c not in out:
            out.append(c)
    return out


def _clamp_int(value, lo, hi, what) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{what} must be an int (got {value!r})")
    return max(lo, min(hi, value))


# --- raw CSV read (preserve the header block verbatim; rows keyed by the Id column) ----------------

def read_base_csv(text: str):
    """Parse a Memoria item CSV TEXT into ``(header_text, cols, id_col, rows_by_id)``. ``header_text`` is every
    leading line up to the first data row, verbatim (the ``#!`` options + ``#``-legend + separators -- so a
    re-emit parses identically). ``cols`` = column-name -> index (from the legend). ``rows_by_id`` = {id:
    raw_row_string}. The first data row is the first line whose first non-space char is NOT ``#`` (a Stats.csv
    ``Comment`` cell may itself contain ``#``, so only a LEADING ``#`` marks a comment)."""
    header, cols, id_col, rows = [], None, None, {}
    in_data = False
    for line in text.splitlines():
        s = line.strip()
        if not in_data and (not s or s.startswith("#")):
            header.append(line)
            if cols is None and s.startswith("#"):
                fields = [f.strip() for f in s.lstrip("#").strip().split(";")]
                if "Id" in fields and len(fields) > 1:
                    cols = {n: i for i, n in enumerate(fields)}
                    id_col = cols["Id"]
            continue
        in_data = True
        if id_col is None:
            continue
        parts = line.split(";")
        try:
            iid = int(parts[id_col].strip())
        except (ValueError, IndexError):
            continue
        rows[iid] = line
    return "\n".join(header), (cols or {}), id_col, rows


def _set_col(row: str, idx: int, value) -> str:
    """Replace column ``idx`` of a ``;``-joined row with ``value`` (other cells -- incl. a trailing ``# name``
    comment -- preserved verbatim)."""
    parts = row.split(";")
    if idx >= len(parts):
        raise ValueError(f"row has {len(parts)} columns; cannot set column {idx}")
    parts[idx] = str(value)
    return ";".join(parts)


def _fk_of(items_rows, items_cols, item_id: int, fk_col: str, kind: str) -> int:
    """The ``WeaponId`` / ``ArmorId`` of an item (from its ``Items.csv`` row). Raises if the item is missing or
    not of that kind (FK < 0)."""
    row = items_rows.get(item_id)
    if row is None:
        raise ValueError(f"item id {item_id} has no Items.csv row")
    parts = row.split(";")
    idx = items_cols.get(fk_col)
    try:
        fk = int(parts[idx].strip())
    except (TypeError, ValueError, IndexError):
        fk = -1
    if fk < 0:
        raise ValueError(f"{_items.name_of(item_id) or item_id} is not a {kind} (no {fk_col})")
    return fk


def _edits_for(block, col_map, cols) -> dict:
    """{CSV column index: new cell value} for a patch block, applying only the keys the block sets + clamps."""
    edits = {}
    for key, csv_col in col_map.items():
        if key not in block:
            continue
        idx = cols.get(csv_col)
        if idx is None:
            raise ValueError(f"this install's CSV has no {csv_col!r} column")
        v = block[key]
        if key == "elements":
            edits[idx] = encode_elements(v)
        elif key == "category":
            edits[idx] = encode_category(v)
        elif key in ("price", "sell"):
            edits[idx] = _clamp_int(v, 0, PRICE_CAP, key)
        elif key == "status_index":
            edits[idx] = _clamp_int(v, 0, STATUS_INDEX_CAP, key)
        elif key == "rate":
            edits[idx] = _clamp_int(v, 0, RATE_CAP, key)
        else:
            edits[idx] = _clamp_int(v, 0, POWER_CAP, key)
    return edits


def _equip_mask_edits(names, cols) -> dict:
    """{Items.csv character-column index: 0/1} that REWRITES an item's 12 equip-by-character bits to exactly
    ``names`` (each listed character -> 1, every other -> 0). Raises if the install's Items.csv lacks a column."""
    wanted = set(encode_characters(names))
    edits = {}
    for ch in _itemstats.CHARS:
        idx = cols.get(ch)
        if idx is None:
            raise ValueError(f"this install's Items.csv has no {ch!r} equip column")
        edits[idx] = 1 if ch in wanted else 0
    return edits


# --- delta builders (text) ------------------------------------------------------------------------

def _emit(header: str, rows_by_id: dict, banner: str) -> str:
    body = "\n".join(rows_by_id[k] for k in sorted(rows_by_id))
    return f"{banner}\n{header}\n{body}\n"


def build_weapons_delta(items_text: str, weapons_text: str, weapons) -> "str | None":
    """A partial ``Weapons.csv`` text from ``[[weapon]]`` blocks (or ``None`` if none patch). Each block:
    ``name`` (item name/id) + any of ``power`` / ``elements``."""
    icols_t = read_base_csv(items_text)
    wheader, wcols, _wid, wrows = read_base_csv(weapons_text)
    _iheader, icols, _iid, irows = icols_t
    patched: dict = {}
    for b in weapons:
        iid = _items.resolve(b["name"])
        wid = _fk_of(irows, icols, iid, "WeaponId", "weapon")
        base = patched.get(wid, wrows.get(wid))
        if base is None:
            raise ValueError(f"no Weapons.csv row for WeaponId {wid} ({b['name']})")
        for idx, val in _edits_for(b, _WEAPON_COLS, wcols).items():
            base = _set_col(base, idx, val)
        patched[wid] = base
    if not patched:
        return None
    return _emit(wheader, patched, "# ff9mapkit [[weapon]] -- Weapons.csv delta (merged by id, whole-row, over the base)")


def build_armors_delta(items_text: str, armors_text: str, armors) -> "str | None":
    iheader_t = read_base_csv(items_text)
    aheader, acols, _aid, arows = read_base_csv(armors_text)
    _ih, icols, _iid, irows = iheader_t
    patched: dict = {}
    for b in armors:
        iid = _items.resolve(b["name"])
        aid = _fk_of(irows, icols, iid, "ArmorId", "armor")
        base = patched.get(aid, arows.get(aid))
        if base is None:
            raise ValueError(f"no Armors.csv row for ArmorId {aid} ({b['name']})")
        for idx, val in _edits_for(b, _ARMOR_COLS, acols).items():
            base = _set_col(base, idx, val)
        patched[aid] = base
    if not patched:
        return None
    return _emit(aheader, patched, "# ff9mapkit [[armor]] -- Armors.csv delta (merged by id, whole-row, over the base)")


def build_items_delta(items_text: str, items, *, bonusid_repoints=None) -> "str | None":
    """A partial ``Items.csv`` text from ``[[item]]`` blocks (keyed by item id directly). Each block: ``name`` +
    any of ``price`` / ``sell`` / ``equippable_by`` (the latter REWRITES the item's 12 equip-by-character bits).
    ``bonusid_repoints`` ({item_id: new BonusId}) additionally repoints those items' ``BonusId`` column (from
    :func:`build_equip_bonus_delta`'s mint path) -- ALL channels compose on one row (the engine merges whole-row,
    so price + equippable_by + a repointed BonusId must ship together in the same Items.csv row)."""
    header, cols, _idcol, rows = read_base_csv(items_text)
    patched: dict = {}
    for b in items:
        iid = _items.resolve(b["name"])
        base = patched.get(iid, rows.get(iid))
        if base is None:
            raise ValueError(f"no Items.csv row for item id {iid} ({b['name']})")
        for idx, val in _edits_for(b, _ITEM_COLS, cols).items():
            base = _set_col(base, idx, val)
        if "equippable_by" in b:
            for idx, val in _equip_mask_edits(b["equippable_by"], cols).items():
                base = _set_col(base, idx, val)
        patched[iid] = base
    if bonusid_repoints:
        bcol = cols.get("BonusId")
        if bcol is None:
            raise ValueError("this install's Items.csv has no BonusId column (can't repoint an equip bonus)")
        for item_id, new_bonus in bonusid_repoints.items():
            base = patched.get(item_id, rows.get(item_id))
            if base is None:
                raise ValueError(f"no Items.csv row for item id {item_id} (equip-bonus repoint)")
            patched[item_id] = _set_col(base, bcol, new_bonus)
    if not patched:
        return None
    return _emit(header, patched, "# ff9mapkit [[item]] -- Items.csv delta (merged by id, whole-row, over the base)")


# --- equip stat bonuses (Stats.csv / ItemStats) ---------------------------------------------------

def _edits_for_bonus(block, scols) -> dict:
    """{Stats.csv column index: new cell value} for an ``[[equip_bonus]]`` block (stat ints clamped 0-255;
    element keys via :func:`encode_elements`)."""
    edits = {}
    for key, csv_col in _EQUIP_BONUS_STATS.items():
        if key in block:
            idx = scols.get(csv_col)
            if idx is None:
                raise ValueError(f"this install's Stats.csv has no {csv_col!r} column")
            edits[idx] = _clamp_int(block[key], 0, STAT_CAP, key)
    for key, csv_col in _EQUIP_BONUS_ELEMS.items():
        if key in block:
            idx = scols.get(csv_col)
            if idx is None:
                raise ValueError(f"this install's Stats.csv has no {csv_col!r} column")
            edits[idx] = encode_elements(block[key])
    return edits


def _mint_comment(new_id: int, name) -> str:
    """The Comment cell (col 0) of a kit-minted Stats.csv row. Sanitized: ``;`` would split into extra columns
    (shifting the Id); a leading ``#`` would make CsvReader SKIP the whole line. The "Bonus NNNN # " prefix means
    the cell never starts with ``#``, so the row always parses as data."""
    safe = str(name).replace(";", ",").replace("\n", " ").replace("\r", " ").strip()
    return f"Bonus {new_id:04d} # {safe} (ff9mapkit)"


def _synthetic_stat_row(width: int, new_id: int, name, id_col: int) -> str:
    """An all-zero Stats.csv row (for an item whose current BonusId is Empty/dangling -- nothing to seed from).
    ``width`` must hold every edited column (>= the real header width, so a >11-column modded Stats.csv is safe)."""
    parts = ["0"] * max(width, 11)
    parts[0] = _mint_comment(new_id, name)
    parts[id_col] = str(new_id)
    return ";".join(parts)


def build_equip_bonus_delta(items_text: str, stats_text: str, equip_bonuses):
    """A partial ``Stats.csv`` text from ``[[equip_bonus]]`` blocks + the ``{item_id: new BonusId}`` repoints its
    mint path needs in ``Items.csv``. Returns ``(stats_delta | None, repoints)``.

    Each block: ``name`` (equippable item) + any of ``speed`` / ``strength`` / ``magic`` / ``spirit`` +
    ``attack_element`` / ``guard_element`` / ``absorb_element`` / ``half_element`` / ``weak_element``. An item whose
    ``BonusId`` is DEDICATED (used by it alone, and not the shared Empty row 0) is edited in place; otherwise a fresh
    row is minted (seeded from the item's current bonus values so unchanged stats carry) and the item is repointed,
    so the edit can NEVER leak onto another item that shared the row."""
    _ih, icols, _iid_col, irows = read_base_csv(items_text)
    sheader, scols, sid_col, srows = read_base_csv(stats_text)
    bcol = icols.get("BonusId")
    if bcol is None:
        raise ValueError("this install's Items.csv has no BonusId column (can't tune equip bonuses)")
    # How many items point at each BonusId -- only a row used by exactly ONE item (and not the shared row 0) is
    # safe to edit in place; everything else mints a fresh row.
    users: dict = {}
    for row in irows.values():
        parts = row.split(";")
        try:
            bid = int(parts[bcol].strip())
        except (ValueError, IndexError):
            continue
        users[bid] = users.get(bid, 0) + 1
    used_ids = {0} | set(srows) | set(users)              # include 0 so a mint NEVER lands on the Empty row
    mint_next = max(used_ids) + 1
    row_width = max((len(r.split(";")) for r in srows.values()), default=0)
    row_width = max(row_width, len(scols), 11)            # a synthetic seed must hold every edited column

    # Coalesce blocks per resolved item FIRST -- so two [[equip_bonus]] on the SAME item MERGE (later block wins
    # per column) on BOTH the in-place and the mint path. (Without this, two blocks on a shared-row item would each
    # mint a separate row, the last repoint would win, and the first block's edits would be silently lost + orphan a
    # half-minted row.) first-seen order keeps the minted ids deterministic.
    per_item: dict = {}
    order: list = []
    for b in equip_bonuses:
        iid = _items.resolve(b["name"])
        e = _edits_for_bonus(b, scols)
        if not e:
            continue
        if iid not in per_item:
            per_item[iid] = {"name": b["name"], "edits": {}}
            order.append(iid)
        per_item[iid]["edits"].update(e)

    patched: dict = {}
    repoints: dict = {}
    for iid in order:
        name = per_item[iid]["name"]
        edits = per_item[iid]["edits"]
        irow = irows.get(iid)
        if irow is None:
            raise ValueError(f"no Items.csv row for item id {iid} ({name})")
        try:
            cur = int(irow.split(";")[bcol].strip())
        except (ValueError, IndexError):
            cur = 0
        dedicated = cur != 0 and cur in srows and users.get(cur, 0) == 1
        if dedicated:
            base = srows[cur]                             # 1:1 by definition, so touched once
            for idx, val in edits.items():
                base = _set_col(base, idx, val)
            patched[cur] = base
        else:
            new_id = mint_next
            mint_next += 1
            seed = srows.get(cur)
            if seed is None:
                seed = _synthetic_stat_row(row_width, new_id, name, sid_col)
            else:
                seed = _set_col(seed, sid_col, new_id)
                seed = _set_col(seed, 0, _mint_comment(new_id, name))
            for idx, val in edits.items():
                seed = _set_col(seed, idx, val)
            patched[new_id] = seed
            repoints[iid] = new_id
    if not patched:
        return None, {}
    return (_emit(sheader, patched,
                  "# ff9mapkit [[equip_bonus]] -- Stats.csv delta (ItemStats, merged by id, whole-row, over the base)"),
            repoints)


# --- write into the mod (reads the install's base CSVs) -------------------------------------------

def _base_dir(game=None):
    from ..config import find_game_path
    return find_game_path(game) / "StreamingAssets" / "Data" / "Items"


# The base CSVs are cp1252 (e.g. byte 0x92 = the apostrophe in "What's That!?"), NOT UTF-8 -- and a delta must
# round-trip those bytes so the engine (which reads them the same non-UTF-8 way) parses it identically. We
# decode/encode cp1252 and strip a leading UTF-8 BOM at the byte level (else it would corrupt the first header
# line). Edited cells are ASCII digits; unchanged cells (incl. comment names) keep their exact bytes.
CSV_ENCODING = "cp1252"


def _read_text(path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):                   # a UTF-8 BOM -> drop it (cp1252 would mangle it)
        raw = raw[3:]
    return raw.decode(CSV_ENCODING, errors="replace")


def write_item_data(layout, weapons=(), armors=(), items=(), equip_bonuses=(), *, game=None) -> None:
    """Emit the ``[[weapon]]`` / ``[[armor]]`` / ``[[item]]`` / ``[[equip_bonus]]`` deltas into ``layout``'s mod
    root. Reads the base rows from the install (raises a clear ValueError if it isn't reachable -- the deltas need
    the base columns). An ``[[equip_bonus]]`` mint repoints an item's BonusId, so its Items.csv repoints merge into
    the same Items.csv delta as any ``[[item]]`` price edits."""
    if not (weapons or armors or items or equip_bonuses):
        return
    from ..config import ConfigError                       # a RuntimeError (no resolvable install), NOT OSError --
    try:                                                  # catch it too so build.py's `except ValueError` warns+skips
        d = _base_dir(game)
        items_text = _read_text(d / "Items.csv")
    except (OSError, ConfigError) as e:
        raise ValueError("item-data patches ([[weapon]]/[[armor]]/[[item]]/[[equip_bonus]]) need your FF9 install "
                         f"to read the base Items.csv columns: {e}") from e
    repoints: dict = {}
    stats_delta = None
    if equip_bonuses:
        try:
            stats_text = _read_text(d / "Stats.csv")
        except OSError as e:
            raise ValueError("equip-bonus patches ([[equip_bonus]]) need your FF9 install to read the base "
                             f"Stats.csv columns -- couldn't read {d / 'Stats.csv'}: {e}") from e
        stats_delta, repoints = build_equip_bonus_delta(items_text, stats_text, equip_bonuses)
    plan = []
    if weapons:
        plan.append((layout.weapons_csv, build_weapons_delta(items_text, _read_text(d / "Weapons.csv"), weapons)))
    if armors:
        plan.append((layout.armors_csv, build_armors_delta(items_text, _read_text(d / "Armors.csv"), armors)))
    if items or repoints:
        plan.append((layout.items_csv, build_items_delta(items_text, items, bonusid_repoints=repoints)))
    if stats_delta is not None:
        plan.append((layout.stats_csv, stats_delta))
    for path, text in plan:
        if text is None:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding=CSV_ENCODING, newline="\n")
