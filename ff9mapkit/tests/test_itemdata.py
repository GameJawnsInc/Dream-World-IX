"""[[weapon]] / [[armor]] / [[item]] -- tune existing item stats via partial CSV deltas (no DLL).

The engine merges Data/Items/{Weapons,Armors,Items}.csv by id (whole-row), so a delta = the base header
(verbatim) + only the patched rows (each complete). The base rows are read live from the install. These tests
pin the delta builders with SYNTHETIC base-CSV text (install-free), plus install-gated end-to-end + validate.
"""
from __future__ import annotations

import pytest

from ff9mapkit import abilities as _abilities
from ff9mapkit import items as _items
from ff9mapkit import itemstats as _itemstats
from ff9mapkit.battle import battlecsv as _battlecsv
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


# ==== [[equip_bonus]] -> Stats.csv (ItemStats) -- the level-up-growth + affinity lever =====================
# Items.csv WITH a BonusId column: Mage Masher has a DEDICATED bonus (id 5, used by it alone) -> edited in place;
# Dagger + Wrist + Potion all point at the shared Empty row 0 -> any edit MINTS a fresh row + repoints.
ITEMS_CSV_B = (
    "#! IncludeId\n"
    "# Id;WeaponId;ArmorId;EffectId;Price;SellingPrice;BonusId\n"
    "# Int32;Int32;Int32;Int32;UInt32;Int32;Int32\n"
    f"{MM};{MM};-1;-1;500;250;5;# {MM} - Mage Masher\n"
    f"{DAGGER};{DAGGER};-1;-1;320;160;0;# {DAGGER} - Dagger\n"
    f"{WRIST};-1;{WRIST};-1;130;65;0;# {WRIST} - Wrist\n"
    f"{POTION};-1;-1;5;50;25;0;# {POTION} - Potion\n"
)
STATS_CSV = (
    "# Comment;Id;Dexterity;Strength;Magic;Will;AttackElement;GuardElement;AbsorbElement;HalfElement;WeakElement\n"
    "#;Int32;Byte;Byte;Byte;Byte;Byte;Byte;Byte;Byte;Byte\n"
    "Bonus 0000 # Empty;0;0;0;0;0;0;0;0;0;0\n"
    "Bonus 0005 # Mage Masher;5;0;2;0;0;0;0;0;0;0\n"        # MM's own dedicated row (str 2)
)


def _stat_row(delta, sid):
    _h, cols, _idc, rows = ID.read_base_csv(delta)
    return rows[sid].split(";"), cols


def test_equip_bonus_edits_dedicated_row_in_place():
    # Mage Masher owns bonus id 5 -> str 2->9 is patched IN PLACE; no mint, no Items.csv repoint
    delta, repoints = ID.build_equip_bonus_delta(ITEMS_CSV_B, STATS_CSV, [{"name": "Mage Masher", "strength": 9}])
    assert repoints == {}
    parts, cols = _stat_row(delta, 5)
    assert parts[cols["Strength"]] == "9" and parts[cols["Id"]] == "5"
    assert "Comment;Id;Dexterity" in delta                 # base header preserved


def test_equip_bonus_mints_and_repoints_for_shared_empty_row():
    # Dagger points at the shared Empty row 0 -> editing it would buff 3 items, so it MINTS a fresh row + repoints
    delta, repoints = ID.build_equip_bonus_delta(ITEMS_CSV_B, STATS_CSV, [{"name": "Dagger", "strength": 3}])
    assert list(repoints) == [DAGGER]
    new_id = repoints[DAGGER]
    assert new_id == 6                                      # max(used ids {0,5}) + 1
    parts, cols = _stat_row(delta, new_id)
    assert parts[cols["Strength"]] == "3" and parts[cols["Id"]] == str(new_id)
    assert parts[0].startswith("Bonus 0006") and "ff9mapkit" in parts[0]   # minted comment, never starts with '#'
    assert 0 not in ID.read_base_csv(delta)[3]             # the shared Empty row 0 is UNTOUCHED


def test_equip_bonus_mint_seeds_unchanged_columns_zero():
    # a minted row seeded from Empty(0) keeps the other stats at their seed value (0), only the edit changes
    delta, repoints = ID.build_equip_bonus_delta(ITEMS_CSV_B, STATS_CSV, [{"name": "Wrist", "magic": 4}])
    parts, cols = _stat_row(delta, repoints[WRIST])
    assert parts[cols["Magic"]] == "4" and parts[cols["Strength"]] == "0" and parts[cols["Dexterity"]] == "0"


def test_equip_bonus_two_shared_edits_get_distinct_ids():
    delta, repoints = ID.build_equip_bonus_delta(
        ITEMS_CSV_B, STATS_CSV, [{"name": "Dagger", "strength": 3}, {"name": "Wrist", "spirit": 5}])
    assert repoints[DAGGER] == 6 and repoints[WRIST] == 7   # monotonic, no reuse
    assert len(ID.read_base_csv(delta)[3]) == 2             # two minted rows


def test_equip_bonus_two_blocks_same_item_merge_on_mint_path():
    # ★ review #1: two blocks on the SAME shared-row item COALESCE into ONE minted row carrying BOTH edits
    # (not two rows where the first edit is lost) -- regardless of block order
    delta, repoints = ID.build_equip_bonus_delta(
        ITEMS_CSV_B, STATS_CSV, [{"name": "Dagger", "strength": 3}, {"name": "Dagger", "magic": 7}])
    assert list(repoints) == [DAGGER]                      # one item -> one repoint
    assert len(ID.read_base_csv(delta)[3]) == 1            # ONE minted row, no orphan
    parts, cols = _stat_row(delta, repoints[DAGGER])
    assert parts[cols["Strength"]] == "3" and parts[cols["Magic"]] == "7"   # both edits land


def test_equip_bonus_two_blocks_same_item_merge_in_place():
    # the dedicated (in-place) path also merges two blocks on one item
    delta, repoints = ID.build_equip_bonus_delta(
        ITEMS_CSV_B, STATS_CSV, [{"name": "Mage Masher", "strength": 9}, {"name": "Mage Masher", "magic": 4}])
    assert repoints == {}
    parts, cols = _stat_row(delta, 5)
    assert parts[cols["Strength"]] == "9" and parts[cols["Magic"]] == "4"


def test_equip_bonus_later_block_wins_per_column():
    delta, _r = ID.build_equip_bonus_delta(
        ITEMS_CSV_B, STATS_CSV, [{"name": "Mage Masher", "strength": 9}, {"name": "Mage Masher", "strength": 20}])
    parts, cols = _stat_row(delta, 5)
    assert parts[cols["Strength"]] == "20"                 # the later block's value for the same column wins


def test_equip_bonus_element_affinity():
    delta, _r = ID.build_equip_bonus_delta(
        ITEMS_CSV_B, STATS_CSV, [{"name": "Mage Masher", "weak_element": ["Fire"], "attack_element": ["Ice"]}])
    parts, cols = _stat_row(delta, 5)
    assert parts[cols["WeakElement"]] == "1" and parts[cols["AttackElement"]] == "2"


def test_equip_bonus_clamps_stat():
    delta, _r = ID.build_equip_bonus_delta(ITEMS_CSV_B, STATS_CSV, [{"name": "Mage Masher", "strength": 9999}])
    parts, cols = _stat_row(delta, 5)
    assert parts[cols["Strength"]] == str(ID.STAT_CAP)


def test_equip_bonus_none_when_empty():
    assert ID.build_equip_bonus_delta(ITEMS_CSV_B, STATS_CSV, []) == (None, {})


def test_equip_bonus_mints_for_dangling_bonusid():
    # an item whose BonusId is not in Stats.csv -> synthesize an all-zero seed, mint + repoint (never crash)
    items = ITEMS_CSV_B.replace(f"{POTION};-1;-1;5;50;25;0;", f"{POTION};-1;-1;5;50;25;99;")
    delta, repoints = ID.build_equip_bonus_delta(items, STATS_CSV, [{"name": "Potion", "strength": 1}])
    parts, cols = _stat_row(delta, repoints[POTION])
    assert parts[cols["Strength"]] == "1"
    assert repoints[POTION] == 100                          # max(used ids incl. the dangling 99) + 1


# ---- Items.csv merge: a price edit AND a BonusId repoint land on ONE row -----------------------
def test_items_delta_merges_price_and_bonus_repoint():
    d = ID.build_items_delta(ITEMS_CSV_B, [{"name": "Dagger", "price": 1}], bonusid_repoints={DAGGER: 6})
    _h, cols, _idc, rows = ID.read_base_csv(d)
    row = rows[DAGGER].split(";")
    assert row[cols["Price"]] == "1" and row[cols["BonusId"]] == "6"   # both edits on the same row


# ---- validate ([[equip_bonus]]) ---------------------------------------------------------------
def test_validate_equip_bonus_no_name_and_no_field(tmp_path):
    probs = validate(_proj(BASE + '\n[[equip_bonus]]\nstrength = 3\n\n[[equip_bonus]]\nname = "Dagger"\n', tmp_path))
    assert any("[[equip_bonus]] #0 needs a `name`" in p for p in probs)
    assert any("sets no editable field" in p and "Dagger" in p for p in probs)


def test_validate_equip_bonus_bad_element_and_negative(tmp_path):
    probs = validate(_proj(
        BASE + '\n[[equip_bonus]]\nname = "Dagger"\nweak_element = ["Bogus"]\nstrength = -1\n', tmp_path))
    assert any("weak_element:" in p and "Bogus" in p for p in probs)
    assert any("strength cannot be negative" in p for p in probs)


@pytest.mark.skipif(not _itemstats.available(), reason="equippable check needs the install's item CSVs")
def test_validate_equip_bonus_not_equippable(tmp_path):
    probs = validate(_proj(BASE + '\n[[equip_bonus]]\nname = "Potion"\nstrength = 3\n', tmp_path))
    assert any("'Potion' is not equippable" in p for p in probs)


# ---- install-gated end-to-end -----------------------------------------------------------------
@pytest.mark.skipif(not _itemstats.available(), reason="write_item_data reads the install's base Stats.csv")
def test_emit_equip_bonus_writes_stats_and_repoint(tmp_path):
    # Mage Masher (vanilla BonusId 0 = shared Empty) -> mints a Stats row + repoints its Items.csv BonusId
    class P:
        raw = {"equip_bonus": [{"name": "Mage Masher", "strength": 5, "weak_element": ["Fire"]}]}
        path = tmp_path / "f.toml"
    layout = ModLayout(tmp_path / "mod")
    warns = _emit_item_data([P()], layout)
    assert not [w for w in warns if "skipped" in w]
    assert layout.stats_csv.exists() and layout.items_csv.exists()   # both channels written
    # the minted Stats row carries the edit
    _h, scols, _i, srows = ID.read_base_csv(layout.stats_csv.read_text(encoding="cp1252"))
    assert any(r.split(";")[scols["Strength"]] == "5" for r in srows.values())
    # Mage Masher's Items.csv BonusId was repointed off the shared Empty 0
    _h2, icols, _i2, irows = ID.read_base_csv(layout.items_csv.read_text(encoding="cp1252"))
    mm_row = irows[MM].split(";")
    assert mm_row[icols["BonusId"]] != "0"


# ==== quick-win column cluster: weapon category/status_index/rate + item equippable_by ======================
# Faithful fixtures mirroring the real column layout (Weapons.csv: Category col 2, StatusIndex 3, Power 6,
# Elements 7, Rate 8; Items.csv: the 12 Zidane..Beatrix equip-by-character Bit columns at the tail).
WEAPONS_CSV_FULL = (
    "#! IncludeHitSfx\n"
    "# Comment;Id;Category;StatusIndex;Model;ScriptId;Power;Elements;Rate;Offset1;Offset2;HitSfx\n"
    "# ;Int32;Byte;Int32;String;Int32;Int32;Byte;Int32;Int16;Int16;Byte\n"
    f"Mage Masher;{MM};5;9;GEO_X;1;14;0;20;81;166;2\n"
    f"Dagger;{DAGGER};5;0;GEO_Y;1;12;0;0;17;200;1\n"
)
ITEMS_CSV_EQUIP = (
    "#! IncludeId\n"
    "# Id;WeaponId;ArmorId;EffectId;Price;SellingPrice;"
    "Zidane;Vivi;Garnet;Steiner;Freya;Quina;Eiko;Amarant;Cinna;Marcus;Blank;Beatrix\n"
    "# Int32;Int32;Int32;Int32;UInt32;Int32;Bit;Bit;Bit;Bit;Bit;Bit;Bit;Bit;Bit;Bit;Bit;Bit\n"
    f"{MM};{MM};-1;-1;500;250;1;0;0;0;0;0;0;0;0;0;0;0;# {MM} - Mage Masher\n"
    f"{WRIST};-1;{WRIST};-1;130;65;1;1;1;1;1;1;1;1;0;0;0;0;# {WRIST} - Wrist\n"
)


# ---- encode_category / encode_characters codecs -----------------------------------------------
def test_encode_category():
    assert ID.encode_category(["short-range", "throw"]) == 5     # 1 | 4
    assert ID.encode_category(["ShortRange"]) == 1               # loose name match (no hyphen, any case)
    assert ID.encode_category(["offset"]) == 8 and ID.encode_category(["ofsdim"]) == 8   # bit-8 alias
    assert ID.encode_category(4) == 4                            # in-range bitmask passes through
    assert ID.encode_category(None) == 0 and ID.encode_category([]) == 0
    for bad in (256, -1):                                        # Byte column -> a >255 int would crash weapon load
        with pytest.raises(ValueError, match="range"):
            ID.encode_category(bad)
    with pytest.raises(ValueError, match="unknown weapon category"):
        ID.encode_category(["Bogus"])
    with pytest.raises(ValueError):
        ID.encode_category(True)


def test_encode_characters():
    assert ID.encode_characters(["Vivi", "Garnet"]) == ["Vivi", "Garnet"]
    assert ID.encode_characters(["vivi", "VIVI"]) == ["Vivi"]    # case-insensitive + de-duped
    assert ID.encode_characters([]) == []
    with pytest.raises(ValueError, match="unknown character"):
        ID.encode_characters(["Nobody"])
    with pytest.raises(ValueError, match="list of character names"):
        ID.encode_characters("Vivi")                            # a bare string is not a list


# ---- weapon delta: category / status_index / rate ---------------------------------------------
def test_build_weapons_delta_category_status_rate():
    d = ID.build_weapons_delta(
        ITEMS_CSV, WEAPONS_CSV_FULL,
        [{"name": "Dagger", "category": ["short-range", "throw"], "status_index": 9, "rate": 30}])
    _h, cols, _idc, rows = ID.read_base_csv(d)
    row = rows[DAGGER].split(";")
    assert row[cols["Category"]] == "5" and row[cols["StatusIndex"]] == "9" and row[cols["Rate"]] == "30"
    assert row[cols["Power"]] == "12"                           # untouched columns preserved


def test_build_weapons_delta_clamps_rate():
    d = ID.build_weapons_delta(ITEMS_CSV, WEAPONS_CSV_FULL, [{"name": "Dagger", "rate": 999}])
    _h, cols, _idc, rows = ID.read_base_csv(d)
    assert rows[DAGGER].split(";")[cols["Rate"]] == str(ID.RATE_CAP)   # 0-100 percent


def test_build_weapons_delta_category_bitmask_int():
    d = ID.build_weapons_delta(ITEMS_CSV, WEAPONS_CSV_FULL, [{"name": "Dagger", "category": 4}])
    _h, cols, _idc, rows = ID.read_base_csv(d)
    assert rows[DAGGER].split(";")[cols["Category"]] == "4"


# ---- item delta: equippable_by (12-column rewrite) --------------------------------------------
def test_build_items_delta_equippable_by():
    # Mage Masher is Zidane-only -> equippable_by=["Vivi","Garnet"] sets exactly those (Zidane cleared)
    d = ID.build_items_delta(ITEMS_CSV_EQUIP, [{"name": "Mage Masher", "equippable_by": ["Vivi", "Garnet"]}])
    _h, cols, _idc, rows = ID.read_base_csv(d)
    row = rows[MM].split(";")
    assert row[cols["Vivi"]] == "1" and row[cols["Garnet"]] == "1"
    assert row[cols["Zidane"]] == "0" and row[cols["Steiner"]] == "0"   # everyone unlisted -> 0 (full rewrite)


def test_build_items_delta_equippable_by_only_no_price():
    # an [[item]] block with ONLY equippable_by (no price/sell) still emits a row
    d = ID.build_items_delta(ITEMS_CSV_EQUIP, [{"name": "Wrist", "equippable_by": ["Zidane"]}])
    assert d is not None
    _h, cols, _idc, rows = ID.read_base_csv(d)
    row = rows[WRIST].split(";")
    assert row[cols["Zidane"]] == "1" and row[cols["Vivi"]] == "0"      # the 8 mains collapsed to just Zidane


def test_build_items_delta_equippable_and_price_merge():
    # price + equippable_by compose on ONE Items.csv row (whole-row merge)
    d = ID.build_items_delta(ITEMS_CSV_EQUIP, [{"name": "Mage Masher", "price": 1, "equippable_by": ["Steiner"]}])
    _h, cols, _idc, rows = ID.read_base_csv(d)
    row = rows[MM].split(";")
    assert row[cols["Price"]] == "1" and row[cols["Steiner"]] == "1" and row[cols["Zidane"]] == "0"


# ---- validate (quick-win cluster) -------------------------------------------------------------
def test_validate_weapon_category_bad(tmp_path):
    probs = validate(_proj(BASE + '\n[[weapon]]\nname = "Dagger"\ncategory = ["Bogus"]\n', tmp_path))
    assert any("category:" in p and "Bogus" in p for p in probs)


def test_validate_weapon_rate_negative(tmp_path):
    probs = validate(_proj(BASE + '\n[[weapon]]\nname = "Dagger"\nrate = -5\n', tmp_path))
    assert any("rate cannot be negative" in p for p in probs)


def test_validate_item_equippable_by_bad(tmp_path):
    probs = validate(_proj(BASE + '\n[[item]]\nname = "Potion"\nequippable_by = ["Nobody"]\n', tmp_path))
    assert any("equippable_by:" in p and "Nobody" in p for p in probs)


def test_validate_item_only_equippable_by_is_editable(tmp_path):
    # equippable_by counts as an editable field -> no "sets no editable field" complaint (Wrist = equippable)
    probs = validate(_proj(BASE + '\n[[item]]\nname = "Wrist"\nequippable_by = ["Vivi"]\n', tmp_path))
    assert not any("sets no editable field" in p for p in probs)


@pytest.mark.skipif(not _itemstats.available(), reason="the no-op equippability check needs the install's CSVs")
def test_validate_item_equippable_by_noop_on_consumable(tmp_path):
    # equippable_by on a non-equippable item (Potion) writes inert bits -> a best-effort "no effect" lint warning
    probs = validate(_proj(BASE + '\n[[item]]\nname = "Potion"\nequippable_by = ["Vivi"]\n', tmp_path))
    assert any("equippable_by has no effect" in p for p in probs)


@pytest.mark.skipif(not _battlecsv.available(), reason="status_index range-guard needs Data/Battle/StatusSets.csv")
def test_validate_weapon_status_index_out_of_range(tmp_path):
    probs = validate(_proj(BASE + '\n[[weapon]]\nname = "Dagger"\nstatus_index = 999999\n', tmp_path))
    assert any("status_index 999999 references no row" in p for p in probs)


# ---- install-gated end-to-end (real Items.csv 12-column equip write) --------------------------
@pytest.mark.skipif(not _itemstats.available(), reason="write_item_data reads the install's base Items.csv")
def test_emit_item_data_equippable_by_install(tmp_path):
    class P:
        raw = {"item": [{"name": "Mage Masher", "equippable_by": ["Vivi", "Garnet"]}]}
        path = tmp_path / "f.toml"
    layout = ModLayout(tmp_path / "mod")
    warns = _emit_item_data([P()], layout)
    assert not [w for w in warns if "skipped" in w]
    _h, cols, _idc, rows = ID.read_base_csv(layout.items_csv.read_text(encoding="cp1252"))
    row = rows[MM].split(";")
    assert row[cols["Vivi"]] == "1" and row[cols["Garnet"]] == "1" and row[cols["Zidane"]] == "0"


# ==== [[item]] teaches -- the abilities a piece of gear teaches (Items.csv AbilityIds) =====================
# Items.csv WITH an AbilityIds column (a comma-list of AA:X/SA:X tokens inside ONE semicolon-cell).
ITEMS_CSV_ABIL = (
    "#! IncludeId\n"
    "# Id;WeaponId;ArmorId;EffectId;Price;SellingPrice;AbilityIds\n"
    "# Int32;Int32;Int32;Int32;UInt32;Int32;Ability[]\n"
    f"{MM};{MM};-1;-1;500;250;AA:101;# {MM} - Mage Masher\n"
    f"{DAGGER};{DAGGER};-1;-1;320;160;0;# {DAGGER} - Dagger\n"
)


def test_ability_tokens_tokens_and_clear():
    # tokens/ids resolve mod-agnostically (no install); an empty list -> the "0" no-abilities sentinel
    assert ID.ability_tokens(["AA:104", "SA:19"]) == "AA:104, SA:19"
    assert ID.ability_tokens([211]) == "SA:19"            # the int abil_id for SA:19 (192 + 19) round-trips
    assert ID.ability_tokens([]) == "0"


def test_ability_tokens_dedup_and_errors():
    assert ID.ability_tokens(["AA:104", "AA:104"]) == "AA:104"   # dups collapse, first-seen order
    with pytest.raises(ValueError):
        ID.ability_tokens(["AA:bogus"])
    with pytest.raises(ValueError):
        ID.ability_tokens("AA:104")                       # a bare string is not a list


def test_build_items_delta_teaches_rewrites_abilityids():
    # Dagger teaches nothing (0) -> teaching it AA:104 + SA:19 rewrites the AbilityIds cell (one ;-cell, commas ok)
    d = ID.build_items_delta(ITEMS_CSV_ABIL, [{"name": "Dagger", "teaches": ["AA:104", "SA:19"]}])
    _h, cols, _idc, rows = ID.read_base_csv(d)
    row = rows[DAGGER].split(";")
    assert row[cols["AbilityIds"]] == "AA:104, SA:19"


def test_build_items_delta_teaches_clear():
    d = ID.build_items_delta(ITEMS_CSV_ABIL, [{"name": "Mage Masher", "teaches": []}])
    _h, cols, _idc, rows = ID.read_base_csv(d)
    assert rows[MM].split(";")[cols["AbilityIds"]] == "0"   # AA:101 -> "0" (replace, not add)


def test_build_items_delta_teaches_composes_with_price():
    d = ID.build_items_delta(ITEMS_CSV_ABIL, [{"name": "Dagger", "price": 1, "teaches": ["AA:104"]}])
    _h, cols, _idc, rows = ID.read_base_csv(d)
    row = rows[DAGGER].split(";")
    assert row[cols["Price"]] == "1" and row[cols["AbilityIds"]] == "AA:104"   # both on one row


def test_validate_item_teaches_bad_token(tmp_path):
    probs = validate(_proj(BASE + '\n[[item]]\nname = "Dagger"\nteaches = ["AA:nope"]\n', tmp_path))
    assert any("teaches:" in p for p in probs)


def test_validate_item_teaches_not_a_list(tmp_path):
    probs = validate(_proj(BASE + '\n[[item]]\nname = "Dagger"\nteaches = "AA:104"\n', tmp_path))
    assert any("teaches must be a list" in p for p in probs)


def test_validate_item_only_teaches_is_editable(tmp_path):
    # teaches counts as an editable field -> no "sets no editable field" complaint
    probs = validate(_proj(BASE + '\n[[item]]\nname = "Dagger"\nteaches = ["AA:104"]\n', tmp_path))
    assert not any("sets no editable field" in p for p in probs)


@pytest.mark.skipif(not _abilities.available(), reason="resolving an ability NAME needs the install's pool CSVs")
def test_validate_item_teaches_unknown_name(tmp_path):
    probs = validate(_proj(BASE + '\n[[item]]\nname = "Dagger"\nteaches = ["Definitely Not An Ability"]\n', tmp_path))
    assert any("teaches:" in p and "unknown ability" in p for p in probs)


@pytest.mark.skipif(not _abilities.available(), reason="resolving an ability NAME needs the install's pool CSVs")
def test_emit_item_data_teaches_by_name_install(tmp_path):
    # a NAME ("Soul Blade") resolves to its token via the live pools and lands in the real Items.csv AbilityIds cell
    class P:
        raw = {"item": [{"name": "Dagger", "teaches": ["Soul Blade"]}]}
        path = tmp_path / "f.toml"
    layout = ModLayout(tmp_path / "mod")
    warns = _emit_item_data([P()], layout)
    assert not [w for w in warns if "skipped" in w]
    _h, cols, _idc, rows = ID.read_base_csv(layout.items_csv.read_text(encoding="cp1252"))
    assert rows[DAGGER].split(";")[cols["AbilityIds"]] == "AA:104"   # Soul Blade = action 104


def test_is_token_classifies_malformed_tokens():
    # review (medium): a token-SHAPED string (even malformed) is a token -> lint checks it WITHOUT the install
    assert _abilities.is_token("AA:nope") and _abilities.is_token("SA:") and _abilities.is_token("AA:104")
    assert _abilities.is_token(211) and _abilities.is_token("99")
    assert not _abilities.is_token("Soul Blade")          # a NAME (no colon) needs the pools
    with pytest.raises(ValueError):
        _abilities.resolve(None, "AA:nope")               # token-shaped but malformed -> clear reject, no install


def test_validate_teaches_bad_token_offline(tmp_path, monkeypatch):
    # the gap the review caught: a malformed AA:/SA: token is flagged even with NO install (is_token routes it to
    # resolve -> a build-blocking lint error, instead of being silently skipped offline)
    monkeypatch.setattr(_abilities, "available", lambda *a, **k: False)
    probs = validate(_proj(BASE + '\n[[item]]\nname = "Dagger"\nteaches = ["AA:nope"]\n', tmp_path))
    assert any("teaches:" in p for p in probs)


@pytest.mark.skipif(not _itemstats.available(), reason="the no-effect equippability check needs the install's CSVs")
def test_validate_teaches_noop_on_consumable(tmp_path):
    # mirror equippable_by: teaches on a non-equippable item (Potion) is inert -> a best-effort lint warning
    probs = validate(_proj(BASE + '\n[[item]]\nname = "Potion"\nteaches = ["AA:104"]\n', tmp_path))
    assert any("teaches has no effect" in p for p in probs)
