"""The Battle-document form specs: the [battlemap] / [scene] / [[scene.enemy]] entity round-trip (tk-free).

Same contract as the field editor's forms (test_editor_forms): ``build_entity(spec, entity_to_values(spec,
e)) == e`` for any entity whose keys the spec covers -- so a form authored in the Battle document serialises
back to exactly the battle.toml shape the build (``ff9mapkit.battle``) consumes.
"""

from __future__ import annotations

import pytest

from ff9mapkit.editor import battle_forms as bf
from ff9mapkit.editor import forms


@pytest.mark.parametrize("spec,entity", [
    # [battlemap]: the override case (bbg + fbx), the repoint case, and the full mint case with cosmetics
    (bf.BATTLEMAP_SPEC, {"bbg": "BBG_B013", "fbx": "BBG_B013.fbx"}),
    (bf.BATTLEMAP_SPEC, {"bbg": "BBG_B013", "repoint_scene": 67}),
    (bf.BATTLEMAP_SPEC, {"bbg": "BBG_B999", "scene_id": 5000, "scene_name": "MYFIGHT",
                         "char_tint": [128, 64, 200], "shadow": 40}),
    # [scene]: the formation
    (bf.SCENE_SPEC, {"monster_count": 4, "camera": 0, "ap": 120, "pattern": 0}),
    # [[scene.enemy]]: stats + element/status affinities + 4-item rewards + flags + placement + re-skin
    (bf.ENEMY_SPEC, {"slot": 0, "type": 0, "hp": 1500, "mp": 80, "gil": 999, "exp": 250,
                     "speed": 20, "strength": 18, "magic": 5, "spirit": 12, "level": 12,
                     "category": 2, "hit_rate": 40, "phys_def": 10, "phys_evade": 4,
                     "mag_def": 8, "mag_evade": 2, "blue_magic": 0, "win_card": 17,
                     "null": ["Fire"], "absorb": ["Water"], "half": ["Wind"], "weak": ["Ice", "Thunder"],
                     "resist_status": ["Poison", "Sleep"], "auto_status": ["Float"],
                     "initial_status": ["Haste"],
                     "drop": ["Potion", "Ether", "none", "none"], "steal": [232, 0, 255, 255],
                     "flags": ["die_atk", "die_dmg"], "pos": [300, -400], "y": 0, "rot": 64,
                     "model": 12, "model_scene": "EF_R007", "model_type": 1, "ai_entry": 2}),
])
def test_battle_spec_roundtrip(spec, entity):
    assert forms.build_entity(spec, forms.entity_to_values(spec, entity)) == entity


def test_enemy_affinities_and_rewards_parse_to_lists():
    # element/status/drop fields are STRLIST -> a comma list of names (or ids) becomes a real TOML list
    e = forms.build_entity(bf.ENEMY_SPEC,
                           {"slot": 1, "weak": "Fire, Ice", "drop": "Potion, none, none, none",
                            "flags": "die_dmg"})
    assert e == {"slot": 1, "weak": ["Fire", "Ice"], "drop": ["Potion", "none", "none", "none"],
                 "flags": ["die_dmg"]}


def test_battlemap_keeps_only_set_fields():
    # only the set fields survive; bbg is the lone required key, blanks are omitted
    e = forms.build_entity(bf.BATTLEMAP_SPEC,
                           {"bbg": "BBG_B013", "fbx": "", "scene_id": "", "scene_name": "",
                            "repoint_scene": "", "char_tint": "", "shadow": ""})
    assert e == {"bbg": "BBG_B013"}


def test_char_tint_is_a_three_int_list():
    e = forms.build_entity(bf.BATTLEMAP_SPEC, {"bbg": "BBG_B013", "char_tint": "128, 128, 128"})
    assert e["char_tint"] == [128, 128, 128]


def test_specs_have_no_duplicate_keys():
    for spec in (bf.BATTLEMAP_SPEC, bf.SCENE_SPEC, bf.ENEMY_SPEC):
        keys = [f.key for f in spec]
        assert len(keys) == len(set(keys)), keys
