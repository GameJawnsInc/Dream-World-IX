"""Pure tests for [[playable]] -- defining a genuine 13th (NEW CharacterId) party member (no install).

The parse/normalize path, the per-language CharacterDefaultName directive lines, the BaseStats/CharacterParameters
seed shapes, the recruit + name registry, and validation. The engine-facing CSV seeding (cloning a donor row into
the custom band) is exercised offline in test_characterdelta.py against the synthetic base CSVs; the build-level
wiring (recruit into Main_Init, name lines into DictionaryPatch) in test_party.py."""
from __future__ import annotations

import pytest

from ff9mapkit.content import playable as PL
from ff9mapkit.config import LANGS


# ---- parse / normalize ------------------------------------------------------------------------
def test_parse_minimal_defaults_id_12():
    s = PL.parse_playable({"name": "Marcus", "borrow": "vivi"})
    assert s["id"] == 12 and s["borrow_id"] == 1 and s["recruit"] is False
    assert s["name"] == "Marcus"
    # a unique NameKeyword is defaulted (so the engine's keyword->id registration can't collide with the donor's)
    assert s["params"]["name_keyword"] == "CU12"
    # every language symbol gets the name
    assert set(s["names"]) == {l.upper() for l in LANGS}
    assert all(v == "Marcus" for v in s["names"].values())


def test_parse_explicit_id_and_borrow_int():
    s = PL.parse_playable({"id": 13, "name": "Ark", "borrow": 3})
    assert s["id"] == 13 and s["borrow_id"] == 3 and s["params"]["name_keyword"] == "CU13"


def test_parse_per_language_names_and_overrides():
    s = PL.parse_playable({"name": "Marcus", "borrow": "vivi",
                           "names": {"jp": "マーカス", "us": "Mark"},
                           "stats": {"strength": 24, "magic": 30},
                           "params": {"equip_set": "vivi", "name_keyword": "MRC2"}})
    assert s["names"]["JP"] == "マーカス" and s["names"]["US"] == "Mark" and s["names"]["FR"] == "Marcus"
    assert s["stats"] == {"strength": 24, "magic": 30}
    assert s["params"]["equip_set"] == 1 and s["params"]["name_keyword"] == "MRC2"   # "vivi" -> set id 1; explicit keyword kept


def test_parse_rejects_bad_inputs():
    with pytest.raises(PL.PlayableError):
        PL.parse_playable({"borrow": "vivi"})                         # no name
    with pytest.raises(PL.PlayableError):
        PL.parse_playable({"name": "X"})                              # no borrow
    with pytest.raises(PL.PlayableError):
        PL.parse_playable({"name": "X", "borrow": "vivi", "id": 5})   # id in the base band (not new)
    with pytest.raises(PL.PlayableError):
        PL.parse_playable({"name": "X", "borrow": "vivi", "id": 99})  # id out of the custom band
    with pytest.raises(PL.PlayableError):
        PL.parse_playable({"name": "X", "borrow": 12})                # borrow must be a base char 0-11
    with pytest.raises(PL.PlayableError):
        PL.parse_playable({"name": "X", "borrow": "nope"})            # unknown donor
    with pytest.raises(PL.PlayableError):
        PL.parse_playable({"name": "X", "borrow": "vivi", "stats": {"nope": 1}})    # unknown stat field
    with pytest.raises(PL.PlayableError):
        PL.parse_playable({"name": "X", "borrow": "vivi", "params": {"nope": 1}})   # unknown param field
    with pytest.raises(PL.PlayableError):
        PL.parse_playable({"name": "X", "borrow": "vivi", "names": {"zz": "Y"}})    # unknown language
    with pytest.raises(PL.PlayableError):
        PL.parse_playable({"name": "X", "borrow": "vivi", "recruit": "yes"})        # recruit not a bool


def test_parse_rejects_csv_hostile_name():
    # a ';' or '#' in the name would corrupt the BaseStats/CharacterParameters CSV row (delimiter / comment marker)
    for bad in ("Foo;Bar", "#Hero", "A;B", "Ace #1"):
        with pytest.raises(PL.PlayableError):
            PL.parse_playable({"name": bad, "borrow": "vivi"})
    assert PL.parse_playable({"name": "Iviv", "borrow": "vivi"})["name"] == "Iviv"   # a clean name is fine


def test_equip_set_accepts_a_character_name():
    # equip_set / equipment_set take a numeric EquipmentSetId OR a character name (resolved here to the id)
    s = PL.parse_playable({"name": "Iviv", "borrow": "vivi", "params": {"equip_set": "steiner"}})
    assert s["params"]["equip_set"] == 3                                            # Steiner's EquipmentSetId
    s2 = PL.parse_playable({"name": "Iviv", "borrow": "vivi", "params": {"equipment_set": 5}})
    assert s2["params"]["equipment_set"] == 5                                        # a bare int still works
    with pytest.raises(PL.PlayableError):
        PL.parse_playable({"name": "Iviv", "borrow": "vivi", "params": {"equip_set": "nope"}})   # unknown name


def test_parse_all_dedups_ids():
    specs = PL.parse_all([{"name": "A", "borrow": "vivi", "id": 12},
                          {"name": "B", "borrow": "steiner", "id": 13}])
    assert [s["id"] for s in specs] == [12, 13]
    with pytest.raises(PL.PlayableError):
        PL.parse_all([{"name": "A", "borrow": "vivi", "id": 12},
                      {"name": "B", "borrow": "vivi", "id": 12}])      # duplicate id
    assert PL.parse_all(None) == []


# ---- the CharacterDefaultName directive lines -------------------------------------------------
def test_name_directive_lines():
    specs = PL.parse_all([{"name": "Marcus", "borrow": "vivi", "names": {"jp": "マーカス"}}])
    lines = PL.name_directive_lines(specs)
    assert len(lines) == len(LANGS)                                   # one line per language
    assert "CharacterDefaultName 12 US Marcus" in lines
    assert "CharacterDefaultName 12 JP マーカス" in lines
    # every line is `CharacterDefaultName <id> <UPPER-SYM> <name>`
    for ln in lines:
        toks = ln.split()
        assert toks[0] == "CharacterDefaultName" and toks[1] == "12" and toks[2].isupper()


# ---- seeds for the CSV builders + recruit/registry --------------------------------------------
def test_basestats_and_params_seeds():
    specs = PL.parse_all([{"name": "Marcus", "borrow": "vivi", "id": 12,
                           "stats": {"strength": 24}, "params": {"equip_set": "vivi"}}])
    bs = PL.basestats_seeds(specs)[0]
    assert bs == {"id": 12, "borrow": 1, "name": "Marcus", "overrides": {"strength": 24}}
    pr = PL.params_seeds(specs)[0]
    assert pr["id"] == 12 and pr["borrow"] == 1 and pr["name"] == "Marcus"
    assert pr["overrides"]["equip_set"] == 1 and pr["overrides"]["name_keyword"] == "CU12"   # "vivi" -> set id 1


def test_recruit_ids_and_registry():
    specs = PL.parse_all([{"name": "Marcus", "borrow": "vivi", "id": 12, "recruit": True},
                          {"name": "Ark", "borrow": "steiner", "id": 13}])
    assert PL.recruit_ids(specs) == [12]                             # only the recruit=true one
    assert PL.registry(specs) == {"marcus": 12, "ark": 13}


def test_validate_playable():
    assert PL.validate_playable({"name": "Marcus", "borrow": "vivi"}) == []
    assert PL.validate_playable({"borrow": "vivi"})                  # missing name -> a problem
    assert PL.validate_playable({"name": "X", "borrow": 99})         # bad donor -> a problem
