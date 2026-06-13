"""[[weapon]] / [[armor]] / [[item]] -- tune existing item stats via partial CSV deltas (no DLL).

The engine merges Data/Items/{Weapons,Armors,Items}.csv by id (whole-row), so a delta = the base header
(verbatim) + only the patched rows (each complete). The base rows are read live from the install. These tests
pin the delta builders with SYNTHETIC base-CSV text (install-free), plus install-gated end-to-end + validate.
"""
from __future__ import annotations

import pytest

from ff9mapkit import items as _items
from ff9mapkit import itemstats as _itemstats
from ff9mapkit.content import itemdata as ID
from ff9mapkit.build import FieldProject, validate, _emit_item_data
from ff9mapkit.config import ModLayout

MM = _items.resolve("Mage Masher")        # a weapon item
DAGGER = _items.resolve("Dagger")         # a weapon item
WRIST = _items.resolve("Wrist")           # an armlet (armor) item
POTION = _items.resolve("Potion")         # a consumable (neither weapon nor armor)

# synthetic base CSVs keyed to the real resolved ids (Comment col first for weapons/armors; Id first for items)
ITEMS_CSV = (
    "#! IncludeId\n"
    "# Id;WeaponId;ArmorId;EffectId;Price;SellingPrice\n"
    "# Int32;Int32;Int32;Int32;UInt32;Int32\n"
    f"{MM};{MM};-1;-1;500;250;# {MM} - Mage Masher\n"
    f"{DAGGER};{DAGGER};-1;-1;320;160;# {DAGGER} - Dagger\n"
    f"{WRIST};-1;{WRIST};-1;130;65;# {WRIST} - Wrist\n"
    f"{POTION};-1;-1;5;50;25;# {POTION} - Potion\n"
)
WEAPONS_CSV = (
    "# Comment;Id;Power;Elements\n"
    "# ;Int32;Int32;Byte\n"
    f"Mage Masher;{MM};14;0\n"
    f"Dagger;{DAGGER};12;0\n"
)
ARMORS_CSV = (
    "# Comment;Id;P.Def;P.Eva;M.Def;M.Eva\n"
    "# ;Int32;Int32;Int32;Int32;Int32\n"
    f"Wrist;{WRIST};0;5;0;3\n"
)


# ---- the codec: element encode ----------------------------------------------------------------
def test_encode_elements():
    assert ID.encode_elements(["Fire"]) == 1
    assert ID.encode_elements(["Fire", "Thunder"]) == 5
    assert ID.encode_elements([]) == 0
    assert ID.encode_elements(8) == 8                     # an in-range bitmask passes through
    assert ID.encode_elements(None) == 0
    with pytest.raises(ValueError):
        ID.encode_elements(["Bogus"])


def test_encode_elements_rejects_bad_inputs():
    # ★ every bad input is a ValueError (so the single except ValueError in build/validate catches it) -- a raw
    # int > 255 would OverflowException -> HARD-QUIT the game at weapon load (review finding #1); bool/float would
    # be an uncaught TypeError that aborts lint (#2).
    for bad in (999, 256, -1):
        with pytest.raises(ValueError, match="out of range"):
            ID.encode_elements(bad)
    for bad in (True, 3.5, {"a": 1}):
        with pytest.raises(ValueError):
            ID.encode_elements(bad)


# ---- read_base_csv: header preservation + id keying -------------------------------------------
def test_read_base_csv_keys_by_id_and_keeps_header():
    header, cols, id_col, rows = ID.read_base_csv(WEAPONS_CSV)
    assert "Comment;Id;Power;Elements" in header and cols["Power"] == 2 and id_col == 1
    assert MM in rows and rows[MM].startswith("Mage Masher;")


def test_read_base_csv_comment_in_comment_cell():
    # a Stats.csv-style row whose Comment cell itself contains '#': only a LEADING '#' marks a comment line
    text = "# Comment;Id;Dexterity\n# ;Int32;Byte\nBonus 0000 # Empty;0;0\nBonus 0001 # Wrist;1;3\n"
    _h, cols, _idc, rows = ID.read_base_csv(text)
    assert 0 in rows and 1 in rows and rows[1] == "Bonus 0001 # Wrist;1;3"


def test_set_col_preserves_trailing_comment():
    row = f"{MM};{MM};-1;-1;500;250;# {MM} - Mage Masher"
    out = ID._set_col(row, 4, 1)                          # Price -> 1
    assert out == f"{MM};{MM};-1;-1;1;250;# {MM} - Mage Masher"


# ---- weapon delta -----------------------------------------------------------------------------
def test_build_weapons_delta_power_and_elements():
    d = ID.build_weapons_delta(ITEMS_CSV, WEAPONS_CSV, [{"name": "Mage Masher", "power": 99, "elements": ["Fire"]}])
    row = d.strip().splitlines()[-1]
    assert row == f"Mage Masher;{MM};99;1"               # Power 14->99, Elements 0->1 (Fire)
    assert "Comment;Id;Power;Elements" in d              # base header preserved


def test_build_weapons_delta_only_patched_rows():
    d = ID.build_weapons_delta(ITEMS_CSV, WEAPONS_CSV, [{"name": "Dagger", "power": 50}])
    data_rows = [ln for ln in d.splitlines() if not ln.startswith("#")]
    assert len(data_rows) == 1 and data_rows[0] == f"Dagger;{DAGGER};50;0"   # Mage Masher untouched -> not emitted


def test_build_weapons_delta_merges_same_weapon():
    d = ID.build_weapons_delta(ITEMS_CSV, WEAPONS_CSV,
                               [{"name": "Mage Masher", "power": 99}, {"name": "Mage Masher", "elements": ["Ice"]}])
    assert d.strip().splitlines()[-1] == f"Mage Masher;{MM};99;2"   # both edits land (Ice = 2)


def test_build_weapons_delta_rejects_non_weapon():
    with pytest.raises(ValueError, match="not a weapon"):
        ID.build_weapons_delta(ITEMS_CSV, WEAPONS_CSV, [{"name": "Potion", "power": 99}])


def test_build_weapons_delta_clamps_power():
    d = ID.build_weapons_delta(ITEMS_CSV, WEAPONS_CSV, [{"name": "Dagger", "power": 9999}])
    assert d.strip().splitlines()[-1] == f"Dagger;{DAGGER};{ID.POWER_CAP};0"


def test_build_weapons_delta_none_when_empty():
    assert ID.build_weapons_delta(ITEMS_CSV, WEAPONS_CSV, []) is None


# ---- armor delta ------------------------------------------------------------------------------
def test_build_armors_delta():
    d = ID.build_armors_delta(ITEMS_CSV, ARMORS_CSV, [{"name": "Wrist", "p_def": 50, "m_def": 9}])
    assert d.strip().splitlines()[-1] == f"Wrist;{WRIST};50;5;9;3"   # P.Def 0->50, M.Def 0->9


def test_build_armors_delta_rejects_non_armor():
    with pytest.raises(ValueError, match="not a armor"):
        ID.build_armors_delta(ITEMS_CSV, ARMORS_CSV, [{"name": "Dagger", "p_def": 9}])


# ---- item (Items.csv) delta -------------------------------------------------------------------
def test_build_items_delta_price():
    d = ID.build_items_delta(ITEMS_CSV, [{"name": "Mage Masher", "price": 1, "sell": 1}])
    assert d.strip().splitlines()[-1] == f"{MM};{MM};-1;-1;1;1;# {MM} - Mage Masher"


def test_build_items_delta_clamps_price():
    d = ID.build_items_delta(ITEMS_CSV, [{"name": "Potion", "price": 99_999_999}])
    assert f";{ID.PRICE_CAP};" in d.strip().splitlines()[-1]


# ---- validate ([[weapon]]/[[armor]]/[[item]]) -------------------------------------------------
BASE = """
[field]
id = 4003
name = "ITEMROOM"
area = 11
text_block = 1073
[camera]
pitch = 45
[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]
[player]
spawn = [0, -300]
"""


def _proj(toml, tmp_path):
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    return FieldProject.load(p)


def test_validate_no_name_and_no_field(tmp_path):
    probs = validate(_proj(BASE + '\n[[weapon]]\npower = 30\n\n[[armor]]\nname = "Wrist"\n', tmp_path))
    assert any("[[weapon]] #0 needs a `name`" in p for p in probs)
    assert any("[[armor]] 'Wrist' sets no editable field" in p for p in probs)


def test_validate_bad_element_and_negative(tmp_path):
    probs = validate(_proj(BASE + '\n[[weapon]]\nname = "Dagger"\nelements = ["Bogus"]\npower = -1\n', tmp_path))
    assert any("elements:" in p and "Bogus" in p for p in probs)
    assert any("power cannot be negative" in p for p in probs)


def test_validate_unknown_item(tmp_path):
    probs = validate(_proj(BASE + '\n[[item]]\nname = "Definitely Not An Item"\nprice = 5\n', tmp_path))
    assert any("Definitely Not An Item" in p for p in probs)


def test_validate_bad_elements_no_crash(tmp_path):
    # review #1/#2: an out-of-range int / a bool elements value must be a clean lint PROBLEM, never a crash
    probs = validate(_proj(BASE + '\n[[weapon]]\nname = "Dagger"\nelements = 999\n', tmp_path))
    assert any("out of range" in p for p in probs)
    probs = validate(_proj(BASE + '\n[[weapon]]\nname = "Dagger"\nelements = true\n', tmp_path))
    assert any("elements:" in p for p in probs)


@pytest.mark.skipif(not _itemstats.available(), reason="type check needs the install's item CSVs")
def test_validate_type_check_install(tmp_path):
    probs = validate(_proj(BASE + '\n[[weapon]]\nname = "Potion"\npower = 30\n', tmp_path))
    assert any("'Potion' is not a weapon" in p for p in probs)


# ---- install-gated end-to-end (the build hook writes real deltas) -----------------------------
@pytest.mark.skipif(not _itemstats.available(), reason="write_item_data reads the install's base CSVs")
def test_emit_item_data_writes_deltas(tmp_path):
    class P:
        raw = {"weapon": [{"name": "Mage Masher", "power": 99}], "item": [{"name": "Mage Masher", "price": 1}]}
        path = tmp_path / "f.toml"
    layout = ModLayout(tmp_path / "mod")
    warns = _emit_item_data([P()], layout)
    assert not [w for w in warns if "skipped" in w]
    assert layout.weapons_csv.exists() and layout.items_csv.exists()
    assert not layout.armors_csv.exists()                 # no [[armor]] -> not written
    # read the emitted delta by its own legend (the real Weapons.csv has Power at col 6, not a fixed index)
    _h, cols, _idc, rows = ID.read_base_csv(layout.weapons_csv.read_text(encoding="cp1252"))
    wrow = next(iter(rows.values())).split(";")
    assert wrow[cols["Power"]] == "99"                    # Power column patched


def test_emit_item_data_dup_warns(tmp_path):
    class P:
        raw = {"weapon": [{"name": "Dagger", "power": 30}, {"name": "Dagger", "power": 40}]}
        path = tmp_path / "f.toml"
    warns = _emit_item_data([P()], ModLayout(tmp_path / "mod"))
    assert any("tuned in two blocks" in w for w in warns)
