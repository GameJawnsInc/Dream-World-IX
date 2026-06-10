"""The editor's tk-free forms layer: parsers, entity<->form round-trip, and cutscene steps."""

from __future__ import annotations

import pytest

from ff9mapkit.editor import forms


# --- parsers ----------------------------------------------------------------------------
def test_parse_optint():
    assert forms.parse_optint("") is None
    assert forms.parse_optint("  42 ") == 42
    with pytest.raises(ValueError):
        forms.parse_optint("nope")


def test_parse_coord_and_pair_accept_comma_or_space():
    assert forms.parse_coord("0, -700") == [0, -700]
    assert forms.parse_coord("400 -200") == [400, -200]
    assert forms.parse_pair("232, 1") == [232, 1]
    assert forms.parse_coord("") is None
    with pytest.raises(ValueError):
        forms.parse_coord("1 2 3")


def test_parse_zone_requires_4_or_5_points():
    z = forms.parse_zone("-700 -2400; 700 -2400; 700 -1900; -700 -1900")
    assert z == [[-700, -2400], [700, -2400], [700, -1900], [-700, -1900]]
    assert forms.parse_zone("") is None
    with pytest.raises(ValueError):
        forms.parse_zone("0 0; 1 1; 2 2")            # only 3 points


# --- entity <-> form values round-trip ---------------------------------------------------
@pytest.mark.parametrize("spec,entity", [
    (forms.NPC_SPEC, {"name": "Vivi", "preset": "vivi", "pos": [0, -700], "dialogue": "hi",
                      "requires_flag": 200}),
    (forms.GATEWAY_SPEC, {"name": "door", "to": 4000, "entrance": 0,
                          "zone": [[-1100, -2400], [1100, -2400], [1100, -1750], [-1100, -1750]]}),
    (forms.EVENT_SPEC, {"name": "chest", "message": "got it", "give_item": [232, 1], "gil": 1000,
                        "set_flag": [200, 1], "once": False,
                        "zone": [[-700, -2400], [700, -2400], [700, -1900], [-700, -1900]]}),
    (forms.ENCOUNTER_SPEC, {"scene": 67, "freq": 200, "battle_music": 0}),
    (forms.MUSIC_SPEC, {"song": 9}),
    (forms.FIELD_SPEC, {"id": 4003, "name": "ROOM", "area": 11, "text_block": 1073}),
    (forms.CHOICE_SPEC, {"npc": "Vivi", "prompt": "What'll it be?", "tail": "UPR"}),
    (forms.CHOICE_SPEC, {"zone": [[300, -400], [700, -400], [700, -800], [300, -800]],
                         "prompt": "Pull the lever?", "once": False}),
    (forms.CHOICE_OPTION_SPEC, {"text": "Yes", "reply": "ok", "give_item": ["Potion", 1],
                                "gil": -100, "set_flag": [8001, 1]}),
])
def test_entity_form_roundtrip(spec, entity):
    assert forms.build_entity(spec, forms.entity_to_values(spec, entity)) == entity


def test_empty_optionals_are_omitted():
    e = forms.build_entity(forms.NPC_SPEC, {"name": "A", "preset": "", "dialogue": "", "pos": "",
                                            "model": "", "animset": "", "requires_flag": ""})
    assert e == {"name": "A"}                          # only the set field survives


def test_once_bool_omitted_when_default_true():
    # once defaults to True -> omitted; once=False -> written
    on = forms.build_entity(forms.EVENT_SPEC, {"name": "e", "message": "m", "once": True})
    off = forms.build_entity(forms.EVENT_SPEC, {"name": "e", "message": "m", "once": False})
    assert "once" not in on and off["once"] is False


# --- cutscene steps ---------------------------------------------------------------------
def test_make_step_and_summary():
    assert forms.make_step("say", "hello") == {"say": "hello"}
    assert forms.make_step("wait", "30") == {"wait": 30}
    assert forms.make_step("walk", "0, -800") == {"walk": [0, -800]}
    assert forms.make_step("face_player", "") == {"face_player": True}
    assert forms.make_step("set_flag", "201, 1") == {"set_flag": [201, 1]}
    assert forms.step_summary({"walk": [0, -800]}) == "walk: 0, -800"
    assert forms.step_summary({"face_player": True}) == "face_player"
    with pytest.raises(ValueError):
        forms.make_step("wait", "")                   # needs a value


def test_step_value_text_roundtrip():
    for step in ({"say": "hi"}, {"wait": 30}, {"walk": [1, 2]}, {"set_flag": [200, 1]},
                 {"animation": 7302}, {"face_player": True}):
        k = forms.step_key(step)
        assert forms.make_step(k, forms.step_value_text(step)) == step


# --- movement steps: names, coords, routes, gestures (script-builder coverage) -------------
def test_parse_point_accepts_coords_or_a_name():
    assert forms.parse_point("0, -800") == [0, -800]
    assert forms.parse_point("400 -200") == [400, -200]
    assert forms.parse_point("fountain") == "fountain"     # a marker name
    assert forms.parse_point("@player") == "@player"       # an entity ref
    with pytest.raises(ValueError):
        forms.parse_point("")


def test_parse_path_mixes_names_and_coords():
    assert forms.parse_path("door; fountain; @player") == ["door", "fountain", "@player"]
    assert forms.parse_path("0 0; 100 200") == [[0, 0], [100, 200]]
    with pytest.raises(ValueError):
        forms.parse_path("   ")


def test_parse_anim_id_or_name():
    assert forms.parse_anim("7302") == 7302
    assert forms.parse_anim("glad") == "glad"
    with pytest.raises(ValueError):
        forms.parse_anim("")


def test_make_step_covers_all_kinds():
    assert forms.make_step("walk", "fountain") == {"walk": "fountain"}
    assert forms.make_step("walk", "0, -800") == {"walk": [0, -800]}
    assert forms.make_step("path", "a; b") == {"path": ["a", "b"]}
    assert forms.make_step("teleport", "@player") == {"teleport": "@player"}
    assert forms.make_step("animation", "glad") == {"animation": "glad"}
    assert forms.make_step("animation", "7302") == {"animation": 7302}
    assert forms.make_step("face_player", "") == {"face_player": True}


def test_step_value_text_round_trips_new_kinds():
    for step in ({"walk": "fountain"}, {"walk": [0, -800]}, {"path": ["a", [1, 2]]},
                 {"animation": "glad"}, {"animation": 7302}, {"teleport": "@player"}):
        k = forms.step_key(step)
        assert forms.make_step(k, forms.step_value_text(step)) == step
    assert "fountain" in forms.step_summary({"walk": "fountain"})


def test_step_help_covers_every_step_type():
    assert set(forms.STEP_HELP) == set(forms.STEP_KIND)


# --- choices (give_item by name/id, option summaries) ------------------------------------
def test_parse_itemcount_name_or_id():
    assert forms.parse_itemcount("Potion, 1") == ["Potion", 1]
    assert forms.parse_itemcount("236") == [236, 1]
    assert forms.parse_itemcount("236, 2") == [236, 2]
    assert forms.parse_itemcount("Phoenix Down, 3") == ["Phoenix Down", 3]   # name may contain spaces
    assert forms.parse_itemcount("") is None
    with pytest.raises(ValueError):
        forms.parse_itemcount(", 2")                  # no item


def test_choice_and_option_summaries():
    ch = {"npc": "Vivi", "prompt": "What'll it be?", "options": [{"text": "Yes"}, {"text": "No"}]}
    s = forms.choice_summary(ch)
    assert "Vivi" in s and "(2)" in s
    o = {"text": "Buy", "reply": "ok", "give_item": ["Potion", 1], "gil": -100, "set_flag": [8001, 1]}
    summ = forms.option_summary(o)
    assert all(t in summ for t in ("Buy", "reply", "item", "-100g", "8001"))


def test_marker_and_dialogue_specs_round_trip():
    m = {"name": "spot", "pos": [10, -20]}
    assert forms.build_entity(forms.MARKER_SPEC, forms.entity_to_values(forms.MARKER_SPEC, m)) == m
    d = {"wrap": 0}
    assert forms.build_entity(forms.DIALOGUE_SPEC, forms.entity_to_values(forms.DIALOGUE_SPEC, d)) == d


def test_section_help_present_for_all_sections():
    for key in ("field", "camera", "dialogue", "encounter", "music", "cutscene",
                "npc", "gateway", "event", "marker"):
        assert forms.SECTION_HELP.get(key)


# ---- F2: name-tolerant story-flag fields (FLAGREF / FLAGPAIR) ----------------------------
def test_parse_flagref_accepts_name_or_index():
    assert forms.parse_flagref("") is None
    assert forms.parse_flagref(" 8512 ") == 8512
    assert forms.parse_flagref("boss_dead") == "boss_dead"      # a NAME passes through (resolved at build)


def test_parse_flagpair_accepts_name_or_index():
    assert forms.parse_flagpair("") is None
    assert forms.parse_flagpair("8512, 1") == [8512, 1]
    assert forms.parse_flagpair("boss_dead") == ["boss_dead", 1]    # value defaults to 1
    assert forms.parse_flagpair("boss_dead, 0") == ["boss_dead", 0]


def test_flag_fields_roundtrip_names_and_advertise_catalog():
    e = forms.build_entity(forms.EVENT_SPEC,
                           {"name": "chest", "requires_flag": "gate", "set_flag": "gate, 1"})
    assert e["requires_flag"] == "gate" and e["set_flag"] == ["gate", 1]
    vals = forms.entity_to_values(forms.EVENT_SPEC, e)
    assert vals["requires_flag"] == "gate" and vals["set_flag"] == "gate, 1"
    rf = next(f for f in forms.NPC_SPEC if f.key == "requires_flag")
    assert rf.kind == forms.FLAGREF and rf.catalog == "flag"        # editor renders a Browse picker
    sf = next(f for f in forms.EVENT_SPEC if f.key == "set_flag")
    assert sf.kind == forms.FLAGPAIR


def test_flagref_index_still_roundtrips():
    e = forms.build_entity(forms.NPC_SPEC, {"name": "v", "requires_flag": "8700"})
    assert e["requires_flag"] == 8700                              # a numeric index stays an int
