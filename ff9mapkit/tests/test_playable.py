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


def test_custom_battle_model_defaults():
    s = PL.parse_playable({"name": "Iviv", "borrow": "vivi", "custom_battle_model": True})
    assert s["custom_battle_model"] and s["battle_model_id"] == 6100 and s["battle_serial"] == 19
    assert s["params"]["serial_formula"] == "19"                     # the character is pointed at the new serial
    s2 = PL.parse_playable({"name": "X", "borrow": "vivi", "id": 13, "custom_battle_model": True})
    assert s2["battle_model_id"] == 6101 and s2["battle_serial"] == 20   # per-character defaults
    # no flag -> the battle fields don't leak
    plain = PL.parse_playable({"name": "Y", "borrow": "vivi"})
    assert plain["custom_battle_model"] is False and plain["battle_model_id"] is None
    assert "serial_formula" not in plain["params"]


def test_custom_battle_model_explicit_and_errors():
    s = PL.parse_playable({"name": "X", "borrow": "vivi", "custom_battle_model": True,
                           "battle_model_id": 6500, "battle_serial": 25, "battle_model_from": "GEO_MAIN_B0_007"})
    assert s["battle_model_id"] == 6500 and s["battle_serial"] == 25 and s["battle_model_from"] == "GEO_MAIN_B0_007"
    assert s["params"]["serial_formula"] == "25"
    with pytest.raises(PL.PlayableError):                            # battle fields need the flag
        PL.parse_playable({"name": "X", "borrow": "vivi", "battle_model_id": 6500})
    with pytest.raises(PL.PlayableError):                            # mint id below the 6000 band
        PL.parse_playable({"name": "X", "borrow": "vivi", "custom_battle_model": True, "battle_model_id": 500})
    with pytest.raises(PL.PlayableError):                            # serial below 19
        PL.parse_playable({"name": "X", "borrow": "vivi", "custom_battle_model": True, "battle_serial": 5})
    with pytest.raises(PL.PlayableError):                            # explicit serial_formula collides with the flag
        PL.parse_playable({"name": "X", "borrow": "vivi", "custom_battle_model": True, "params": {"serial_formula": "3"}})


def test_custom_serial_specs():
    specs = PL.parse_all([{"name": "Iviv", "borrow": "vivi", "custom_battle_model": True},
                          {"name": "Plain", "borrow": "steiner", "id": 13}])
    bs = PL.custom_serial_specs(specs)
    assert len(bs) == 1                                              # only the one needing a custom serial row
    assert bs[0]["playable_id"] == 12 and bs[0]["borrow_id"] == 1 and bs[0]["custom_model"] is True
    assert bs[0]["model_id"] == 6100 and bs[0]["serial"] == 19 and bs[0]["model_from"] is None
    assert bs[0]["borrow_serial"] is None and bs[0]["portrait"] is None and bs[0]["avatar"] is None
    assert bs[0]["custom_anims"] is False                            # default: the minted model shares donor clips


def test_custom_battle_anims():
    # custom_battle_anims gives the minted battle model its OWN editable animset (requires custom_battle_model).
    with pytest.raises(PL.PlayableError):                            # needs the model mint (binds to its id)
        PL.parse_playable({"name": "Iviv", "borrow": "vivi", "custom_battle_anims": True})
    with pytest.raises(PL.PlayableError):                            # must be a bool
        PL.parse_playable({"name": "Iviv", "borrow": "vivi", "custom_battle_model": True, "custom_battle_anims": "yes"})
    s = PL.parse_playable({"name": "Iviv", "borrow": "vivi",
                           "custom_battle_model": True, "custom_battle_anims": True})
    assert s["custom_battle_anims"] is True
    assert PL.custom_serial_specs([s])[0]["custom_anims"] is True    # carried to the build


def test_abilities_parse_and_seeds():
    # [playable.abilities] gives the char its OWN custom preset (20) + command menu + learn list
    s = PL.parse_playable({"name": "Iviv", "borrow": "vivi", "abilities": {
        "command1": "Black Magic", "command2": "White Magic", "learn": [{"ability": "Fire", "ap": 0}]}})
    assert s["ability_preset_id"] == 20                              # custom band (char 12 -> preset 20)
    assert s["ability_menu_from"] == (1, "Vivi")                     # menu_from defaults to the borrow donor's preset
    assert s["ability_slots"]["ability1"] == "Black Magic" and s["ability_slots"]["ability2"] == "White Magic"
    assert s["ability_slots"]["ability1_trance"] == "Black Magic"    # trance mirrors the regular slot by default
    assert s["params"]["menu_type"] == 20                            # CharacterParameters col-4 -> the custom preset
    cs, ls = PL.command_set_seeds([s]), PL.learn_seeds([s])
    assert cs[0]["id"] == 20 and cs[0]["clone_from"] == 1 and cs[0]["slots"]["ability1"] == "Black Magic"
    assert ls[0]["preset_name"] == "20" and ls[0]["read_from"] == "Vivi" and ls[0]["abilities"][0]["ability"] == "Fire"


def test_abilities_errors():
    with pytest.raises(PL.PlayableError):                            # a base preset (must be the custom band)
        PL.parse_playable({"name": "X", "borrow": "vivi", "abilities": {"preset": "vivi"}})
    with pytest.raises(PL.PlayableError):                            # unknown command
        PL.parse_playable({"name": "X", "borrow": "vivi", "abilities": {"command1": "Nonsense"}})
    with pytest.raises(PL.PlayableError):                            # params.menu_type collides with the abilities block
        PL.parse_playable({"name": "X", "borrow": "vivi", "abilities": {}, "params": {"menu_type": 5}})
    with pytest.raises(PL.PlayableError):                            # two custom chars can't share a preset
        PL.parse_all([{"name": "A", "borrow": "vivi", "id": 12, "abilities": {"preset": 20}},
                      {"name": "B", "borrow": "steiner", "id": 13, "abilities": {"preset": 20}}])
    # a spec without an abilities block leaves the preset unset (borrows the donor's, as before)
    plain = PL.parse_playable({"name": "X", "borrow": "vivi"})
    assert plain["ability_preset_id"] is None and PL.command_set_seeds([plain]) == []


def test_abilities_menu_from_validation():
    # a GUEST borrow (CharacterId 8-11 != PresetId) needs an explicit menu_from -- else a silent misalignment
    with pytest.raises(PL.PlayableError):
        PL.parse_playable({"name": "X", "borrow": "cinna", "abilities": {}})
    # a Stage preset (16-19) has a CommandSet but NO learn file to seed from -> rejected offline (not a late build error)
    with pytest.raises(PL.PlayableError):
        PL.parse_playable({"name": "X", "borrow": "vivi", "abilities": {"menu_from": "StageZidane"}})
    # a guest borrow WITH an explicit base menu_from is fine
    s = PL.parse_playable({"name": "X", "borrow": "cinna", "abilities": {"menu_from": "zidane"}})
    assert s["ability_menu_from"] == (0, "Zidane")


def test_minted_command_parse_and_autoseed():
    # command1 as an inline TABLE mints a unique command with its own pool
    s = PL.parse_playable({"name": "Iviv", "borrow": "vivi", "abilities": {
        "command1": {"name": "Spark", "abilities": ["Fire", "Blizzard", "Cure"]},
        "command2": "White Magic", "learn": [{"ability": "Protect", "ap": 0}]}})
    assert s["minted_commands"] == [{"name": "Spark", "abilities": ["Fire", "Blizzard", "Cure"], "slot": "ability1"}]
    # the pool auto-seeds the learn list at ap=0 (the explicit Protect is kept; pool spells appended once)
    learned = {l["ability"]: l["ap"] for l in s["ability_learn"]}
    assert learned == {"Protect": 0, "Fire": 0, "Blizzard": 0, "Cure": 0}


def test_minted_command_autoseed_respects_explicit_ap():
    # an explicit learn entry for a pool ability WINS (its ap is not overwritten by the ap=0 auto-seed) -- same form
    s = PL.parse_playable({"name": "Iviv", "borrow": "vivi", "abilities": {
        "command1": {"name": "Spark", "abilities": ["Fire"]}, "learn": [{"ability": "Fire", "ap": 99}]}})
    assert [l for l in s["ability_learn"] if l["ability"] == "Fire"] == [{"ability": "Fire", "ap": 99}]


def test_minted_command_autoseed_different_token_form_explicit_wins():
    # the pool names an ability ("Fire") that the author ALSO learns in a DIFFERENT token form ("AA:25", ap 500).
    # The seeds are PREPENDED so build_learn_file (last-write-wins after token resolution) keeps the author's ap 500.
    s = PL.parse_playable({"name": "Iviv", "borrow": "vivi", "abilities": {
        "command1": {"name": "Spark", "abilities": ["Fire"]}, "learn": [{"ability": "AA:25", "ap": 500}]}})
    # seed (Fire, ap 0) comes FIRST, the explicit (AA:25, ap 500) LAST -> the explicit wins once both resolve to AA:25
    assert s["ability_learn"] == [{"ability": "Fire", "ap": 0}, {"ability": "AA:25", "ap": 500}]


def test_minted_command_allocation_and_seeds():
    specs = PL.parse_all([{"name": "Iviv", "borrow": "vivi", "id": 12, "abilities": {
        "command1": {"name": "Spark", "abilities": ["Fire"]}, "command2": "White Magic"}}])
    s = specs[0]
    assert s["minted_commands"][0]["id"] == 46                     # first custom-band command id
    assert s["ability_slots"]["ability1"] == 46                    # the slot is rewritten to the minted id
    assert s["ability_slots"]["ability1_trance"] == 46             # and mirrors into trance
    assert PL.command_seeds(specs) == [{"id": 46, "name": "Spark", "abilities": ["Fire"]}]
    # the CommandSet row for the custom preset points ability1 at the minted id
    assert PL.command_set_seeds(specs)[0]["slots"]["ability1"] == 46


def test_minted_command_explicit_trance_pin_wins():
    specs = PL.parse_all([{"name": "Iviv", "borrow": "vivi", "id": 12, "abilities": {
        "command1": {"name": "Spark", "abilities": ["Fire"]}, "command1_trance": "Black Magic"}}])
    s = specs[0]
    assert s["ability_slots"]["ability1"] == 46 and s["ability_slots"]["ability1_trance"] == "Black Magic"


def test_minted_command_errors():
    with pytest.raises(PL.PlayableError):                          # a table on a trance slot can't mint a command
        PL.parse_playable({"name": "X", "borrow": "vivi", "abilities": {
            "command1_trance": {"name": "Y", "abilities": ["Fire"]}}})
    with pytest.raises(PL.PlayableError):                          # missing name
        PL.parse_playable({"name": "X", "borrow": "vivi", "abilities": {"command1": {"abilities": ["Fire"]}}})
    with pytest.raises(PL.PlayableError):                          # empty pool
        PL.parse_playable({"name": "X", "borrow": "vivi", "abilities": {"command1": {"name": "Y", "abilities": []}}})
    with pytest.raises(PL.PlayableError):                          # unknown key in the inline table
        PL.parse_playable({"name": "X", "borrow": "vivi", "abilities": {
            "command1": {"name": "Y", "abilities": ["Fire"], "foo": 1}}})


def test_minted_command_band_exhaustion():
    from ff9mapkit.battle import characterdelta as CD
    # 4 custom chars (presets 20-23) each minting BOTH command slots = 8 commands > the 7-slot band -> a clear error
    entries = [{"name": f"C{i}", "borrow": "vivi", "id": 12 + i, "abilities": {
        "command1": {"name": f"K{i}a", "abilities": ["Fire"]},
        "command2": {"name": f"K{i}b", "abilities": ["Fire"]}} } for i in range(4)]
    assert len(CD._CMD_CUSTOM_BAND) == 7
    with pytest.raises(PL.PlayableError):
        PL.parse_all(entries)


def test_custom_ability_in_pool_mints_and_learns():
    # an inline TABLE in a command pool mints a custom ability (a unique spell cloned from a donor)
    specs = PL.parse_all([{"id": 12, "name": "Iviv", "borrow": "vivi", "abilities": {
        "command1": {"name": "Spark", "abilities": [
            "Cure", {"name": "Voltflare", "from": "Fire", "power": 55, "element": ["Thunder"], "mp": 18}]}}}])
    s = specs[0]
    # the inline-table marker is replaced by the allocated custom-ability id (192); the stock 'Cure' is kept verbatim
    assert s["minted_commands"][0]["abilities"] == ["Cure", 192]
    assert s["minted_actions"] == [{"name": "Voltflare", "from": "Fire",
                                    "overrides": {"power": 55, "element": ["Thunder"], "mp": 18}, "id": 192}]
    assert PL.action_seeds(specs) == s["minted_actions"]
    # the command ListEntry holds the RAW id 192; the learn file holds the AA:192 form (the two are deliberately different)
    assert PL.command_seeds(specs)[0]["abilities"] == ["Cure", 192]
    assert {"ability": "AA:192", "ap": 0} in s["ability_learn"]


def test_custom_ability_errors():
    def mk(pool_entry):
        return {"name": "X", "borrow": "vivi", "abilities": {"command1": {"name": "S", "abilities": [pool_entry]}}}
    with pytest.raises(PL.PlayableError):                        # missing name
        PL.parse_playable(mk({"from": "Fire"}))
    with pytest.raises(PL.PlayableError):                        # missing from (the donor to clone)
        PL.parse_playable(mk({"name": "Y"}))
    with pytest.raises(PL.PlayableError):                        # a bare id >=192 must be minted via a table
        PL.parse_playable(mk(192))
    with pytest.raises(PL.PlayableError):                        # ';' in a custom ability name
        PL.parse_playable(mk({"name": "a;b", "from": "Fire"}))


def test_custom_ability_allocation_and_exhaustion():
    from ff9mapkit.battle import actiondelta as AD
    # allocated sequentially from the band start (192, 193, ...) across the build
    specs = PL.parse_all([{"id": 12, "name": "A", "borrow": "vivi", "abilities": {
        "command1": {"name": "S", "abilities": [{"name": "c1", "from": "Fire"}, {"name": "c2", "from": "Fire"}]}}}])
    assert [ca["id"] for ca in PL.action_seeds(specs)] == [AD._CUSTOM_ACTION_MIN, AD._CUSTOM_ACTION_MIN + 1]
    # more customs than the band has slots -> a clear error (not an IndexError)
    n = AD._CUSTOM_ACTION_MAX - AD._CUSTOM_ACTION_MIN + 1
    pool = [{"name": f"c{i}", "from": "Fire"} for i in range(n + 1)]
    with pytest.raises(PL.PlayableError):
        PL.parse_all([{"id": 12, "name": "A", "borrow": "vivi", "abilities": {
            "command1": {"name": "S", "abilities": pool}}}])


def test_anim_edits_persists_blender_edits():
    # anim_edits = a .glb the BUILD ships onto the animset (survives re-deploy); requires custom_battle_anims.
    with pytest.raises(PL.PlayableError):                            # needs custom_battle_anims (edits that animset)
        PL.parse_playable({"name": "Iviv", "borrow": "vivi", "custom_battle_model": True, "anim_edits": "x.glb"})
    with pytest.raises(PL.PlayableError):                            # must be a path string
        PL.parse_playable({"name": "Iviv", "borrow": "vivi", "custom_battle_model": True,
                           "custom_battle_anims": True, "anim_edits": 123})
    s = PL.parse_playable({"name": "Iviv", "borrow": "vivi", "custom_battle_model": True,
                           "custom_battle_anims": True, "anim_edits": "iviv_anims.glb"})
    assert s["anim_edits"] == "iviv_anims.glb"
    assert PL.custom_serial_specs([s])[0]["anim_edits"] == "iviv_anims.glb"     # carried to the build


def test_duplicate_battle_model_id_and_serial_rejected():
    # two custom characters must not share a battle_model_id (same Models/ + animset band) or serial (row collision)
    with pytest.raises(PL.PlayableError):
        PL.parse_all([{"name": "A", "borrow": "vivi", "id": 12, "custom_battle_model": True, "battle_model_id": 6100},
                      {"name": "B", "borrow": "steiner", "id": 13, "custom_battle_model": True, "battle_model_id": 6100}])
    with pytest.raises(PL.PlayableError):
        PL.parse_all([{"name": "A", "borrow": "vivi", "id": 12, "custom_battle_model": True, "battle_serial": 19},
                      {"name": "B", "borrow": "steiner", "id": 13, "custom_battle_model": True, "battle_serial": 19}])
    # the DEFAULTS never collide (per-slot): two plain custom-model chars parse fine
    ok = PL.parse_all([{"name": "A", "borrow": "vivi", "id": 12, "custom_battle_model": True},
                       {"name": "B", "borrow": "steiner", "id": 13, "custom_battle_model": True}])
    assert [s["battle_model_id"] for s in ok] == [6100, 6101]


def test_custom_battle_borrow_serial():
    # a scenario-formula donor (Zidane/Garnet/...) needs an explicit battle model + anim-source serial
    s = PL.parse_playable({"name": "Zephyr", "borrow": "garnet", "custom_battle_model": True,
                           "battle_model_from": "GEO_MAIN_B0_006", "battle_borrow_serial": 2})
    assert s["battle_borrow_serial"] == 2 and s["battle_model_from"] == "GEO_MAIN_B0_006"
    assert PL.custom_serial_specs([s])[0]["borrow_serial"] == 2
    with pytest.raises(PL.PlayableError):                            # serial out of the base range 0-18
        PL.parse_playable({"name": "X", "borrow": "vivi", "custom_battle_model": True, "battle_borrow_serial": 25})
    with pytest.raises(PL.PlayableError):                            # needs the flag
        PL.parse_playable({"name": "X", "borrow": "vivi", "battle_borrow_serial": 2})
    # default -> None (derive from borrow)
    assert PL.parse_playable({"name": "X", "borrow": "vivi",
                              "custom_battle_model": True})["battle_borrow_serial"] is None


def test_portrait_parsing():
    s = PL.parse_playable({"name": "Iviv", "borrow": "vivi", "portrait": "iviv.png"})
    assert s["portrait"] == "iviv.png" and s["avatar"] == "face_cu12"
    assert s["params"]["serial_formula"] == "19"                    # a portrait alone needs a custom serial row
    assert s["custom_battle_model"] is False and s["battle_model_id"] is None   # ...but NO model mint
    cs = PL.custom_serial_specs([s])
    assert len(cs) == 1 and cs[0]["custom_model"] is False
    assert cs[0]["portrait"] == "iviv.png" and cs[0]["avatar"] == "face_cu12"
    # portrait + custom_battle_model coexist (custom model AND custom face)
    s2 = PL.parse_playable({"name": "X", "borrow": "vivi", "custom_battle_model": True, "portrait": "x.png"})
    assert s2["avatar"] == "face_cu12" and s2["battle_model_id"] == 6100
    with pytest.raises(PL.PlayableError):                           # portrait must be a path string
        PL.parse_playable({"name": "X", "borrow": "vivi", "portrait": 5})


def test_validate_playable():
    assert PL.validate_playable({"name": "Marcus", "borrow": "vivi"}) == []
    assert PL.validate_playable({"borrow": "vivi"})                  # missing name -> a problem
    assert PL.validate_playable({"name": "X", "borrow": 99})         # bad donor -> a problem
