"""``[[weapon]]`` / ``[[armor]]`` / ``[[item]]`` -- tune EXISTING item stats via partial CSV deltas (no DLL).

The engine MERGES ``Data/Items/{Weapons,Armors,Items}.csv`` by id low->high, **whole-row-wins**
(``AssetManager.EnumerateCsvFromLowToHigh``), so a mod ships a PARTIAL delta = the base file's header block
(verbatim, so ``CsvReader`` parses the same columns + ``#!`` options) + only the patched rows, each COMPLETE.

The base rows are read LIVE from the user's install (the same provenance-clean pattern as :mod:`ff9mapkit.itemstats`)
-- so the kit commits NO game data; the delta is GENERATED at build time into the mod folder. Item-data patches
therefore need a reachable install (they degrade with a clear error otherwise).

* ``[[weapon]]`` patches the item's ItemAttack (``Weapons.csv``: ``Power`` / ``Elements``), located via the item's
  ``WeaponId`` in ``Items.csv``.
* ``[[armor]]`` patches its ItemDefence (``Armors.csv``: ``P.Def`` / ``P.Eva`` / ``M.Def`` / ``M.Eva``) via ``ArmorId``.
* ``[[item]]`` patches its ItemInfo (``Items.csv``: ``Price`` / ``SellingPrice``) by item id directly.

    [[weapon]]
    name = "Mage Masher"
    power = 30
    elements = ["Fire"]

    [[armor]]
    name = "Bronze Armor"
    p_def = 20

    [[item]]
    name = "Excalibur"
    price = 5000
"""
from __future__ import annotations

from .. import items as _items
from .. import itemstats as _itemstats

POWER_CAP = 255           # weapon Power / armor defence are small byte-range values in practice
PRICE_CAP = 9_999_999     # gil cap; a price above it is pointless (you can't hold that much gil)
_ELEM_BY_NAME = {name.lower(): bit for bit, name in _itemstats.ELEMENTS}   # "fire" -> 1, ...

# Which Items.csv FK column + which target CSV a block patches, and the editable {toml key: CSV column} maps.
_WEAPON_COLS = {"power": "Power", "elements": "Elements"}
_ARMOR_COLS = {"p_def": "P.Def", "p_eva": "P.Eva", "m_def": "M.Def", "m_eva": "M.Eva"}
_ITEM_COLS = {"price": "Price", "sell": "SellingPrice"}


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
        elif key in ("price", "sell"):
            edits[idx] = _clamp_int(v, 0, PRICE_CAP, key)
        else:
            edits[idx] = _clamp_int(v, 0, POWER_CAP, key)
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


def build_items_delta(items_text: str, items) -> "str | None":
    """A partial ``Items.csv`` text from ``[[item]]`` blocks (keyed by item id directly). Each block: ``name`` +
    any of ``price`` / ``sell``."""
    header, cols, _idcol, rows = read_base_csv(items_text)
    patched: dict = {}
    for b in items:
        iid = _items.resolve(b["name"])
        base = patched.get(iid, rows.get(iid))
        if base is None:
            raise ValueError(f"no Items.csv row for item id {iid} ({b['name']})")
        for idx, val in _edits_for(b, _ITEM_COLS, cols).items():
            base = _set_col(base, idx, val)
        patched[iid] = base
    if not patched:
        return None
    return _emit(header, patched, "# ff9mapkit [[item]] -- Items.csv delta (merged by id, whole-row, over the base)")


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


def write_item_data(layout, weapons=(), armors=(), items=(), *, game=None) -> None:
    """Emit the ``[[weapon]]`` / ``[[armor]]`` / ``[[item]]`` deltas into ``layout``'s mod root. Reads the base
    rows from the install (raises a clear ValueError if it isn't reachable -- the deltas need the base columns)."""
    if not (weapons or armors or items):
        return
    d = _base_dir(game)
    try:
        items_text = _read_text(d / "Items.csv")
    except OSError as e:
        raise ValueError("item-data patches ([[weapon]]/[[armor]]/[[item]]) need your FF9 install to read the "
                         f"base Items.csv columns -- couldn't read {d / 'Items.csv'}: {e}") from e
    plan = []
    if weapons:
        plan.append((layout.weapons_csv, build_weapons_delta(items_text, _read_text(d / "Weapons.csv"), weapons)))
    if armors:
        plan.append((layout.armors_csv, build_armors_delta(items_text, _read_text(d / "Armors.csv"), armors)))
    if items:
        plan.append((layout.items_csv, build_items_delta(items_text, items)))
    for path, text in plan:
        if text is None:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding=CSV_ENCODING, newline="\n")
