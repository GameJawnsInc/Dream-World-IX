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
