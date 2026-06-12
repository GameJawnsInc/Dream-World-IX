"""[start_inventory] + [[equipment]] -- new-game starting bag + per-character default gear, rendered to the
mod-global CSV deltas (InitialItems.csv = full bag / highest-wins; DefaultEquipment.csv = partial / merged).

Pure renderers (item/char resolution, summing, clamping, the CSV text) run OFFLINE off the committed item-name
table -- no game data. The build-emit + validation are exercised in test_build.py (gated on the templates).
"""
from __future__ import annotations

import pytest

from ff9mapkit.content import equipment as EQP
from ff9mapkit.content import inventory as INV


# ---- [start_inventory] -> InitialItems.csv ----
def test_inventory_rows_resolves_sums_clamps_and_drops_noitem():
    rows = INV.inventory_rows([["Potion", 20], ["Potion", 90], [236, 1], ["Tent", 3], [255, 1]])
    assert rows == [(236, 99), (253, 3)]          # Potion 20+90+1=111 -> clamped 99; Tent 3; NoItem(255) dropped
    assert INV.inventory_rows(["Hi-Potion"]) == [(237, 1)]   # a bare name defaults to count 1


def test_inventory_render_header_and_named_rows():
    out = INV.render_initial_items([["Tent", 3], ["Potion", 5]])
    assert "# ItemID;Count" in out and "REPLACES the base" in out
    assert "\n236;5;# Potion\n" in out and "\n253;3;# Tent\n" in out


def test_inventory_unknown_name_raises():
    with pytest.raises(ValueError):
        INV.inventory_rows([["Megalixir", 1]])    # not an FF9 item


# ---- [[equipment]] -> DefaultEquipment.csv ----
def test_equipment_resolve_set_id_names_aliases_ids():
    assert EQP.resolve_set_id("steiner") == 3 and EQP.resolve_set_id("Steiner") == 3
    assert EQP.resolve_set_id("dagger") == 2 and EQP.resolve_set_id("salamander") == 7
    assert EQP.resolve_set_id("beatrix2") == 13 and EQP.resolve_set_id(7) == 7
    for bad in ("nobody", 99, None):
        with pytest.raises(ValueError):
            EQP.resolve_set_id(bad)


def test_equipment_rows_complete_row_omitted_slots_empty():
    # weapon + armor set; head/wrist/accessory OMITTED -> -1 (the row replaces the whole set, not a slot patch)
    rows = EQP.equipment_rows([{"character": "steiner", "weapon": "Excalibur", "armor": "Genji Armor"}])
    assert rows == [(3, [28, -1, -1, 189, -1])]
    # explicit empties + numeric ids resolve; rows sort by set id
    rows2 = EQP.equipment_rows([{"character": "vivi", "weapon": 78, "accessory": "none"},
                                {"character": "zidane", "weapon": "Dagger"}])
    assert rows2 == [(0, [1, -1, -1, -1, -1]), (1, [78, -1, -1, -1, -1])]


def test_equipment_render_is_partial_only_named_chars():
    out = EQP.render_default_equipment([{"character": "vivi", "weapon": 78}])
    assert "# Comment;Id;Weapon;Head;Wrist;Armor;Accessory" in out
    assert "\nVivi;1;78;-1;-1;-1;-1\n" in out
    assert "Zidane" not in out and "Steiner" not in out   # partial: only the authored character's row


def test_equipment_unknown_item_raises():
    with pytest.raises(ValueError):
        EQP.equipment_rows([{"character": "steiner", "weapon": "Notathing"}])


def test_inventory_count_clamps_to_at_least_one():
    assert INV.inventory_rows([["Potion", 0], ["Tent", -5]]) == [(236, 1), (253, 1)]   # min 1 per grant


def test_equipment_dedup_last_character_wins():
    rows = EQP.equipment_rows([{"character": "steiner", "weapon": "Excalibur"},
                               {"character": "steiner", "weapon": "Dagger"}])
    assert rows == [(3, [1, -1, -1, -1, -1])]            # the later Steiner row wins (1 = Dagger)


def test_equipment_bool_slot_rejected():
    with pytest.raises(ValueError):
        EQP.equipment_rows([{"character": "vivi", "weapon": True}])   # a bool is not an item
