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
    # [scene]: the formation + the encounter rules (flags) + opening-camera tweak floats
    (bf.SCENE_SPEC, {"monster_count": 4, "camera": 0, "ap": 120, "pattern": 0,
                     "flags": ["back_attack", "no_escape"], "camera_yaw": 15.0, "camera_zoom": 1.5}),
    # [[scene.ai_phase]]: the boss-enrage branch (note the 'else' key)
    (bf.AI_PHASE_SPEC, {"entry": 1, "tag": 1, "stat": "hp", "below": 0.5, "then": 2, "else": 0}),
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


@pytest.mark.parametrize("spec,entity", [
    (bf.CHARACTER_SPEC, {"character": "Vivi", "strength": 30, "magic": 40}),
    (bf.BATTLE_ACTION_SPEC, {"action": "Fire", "power": 30, "element": ["Ice"], "mp": 6, "status_index": 70}),
    (bf.STATUS_SPEC, {"status": "Poison", "tick": 30, "duration": 0, "clear_on_apply": ["Sleep"]}),
    (bf.ABILITY_GEM_SPEC, {"ability": "Auto-Haste", "gems": 12}),
    (bf.CHARACTER_PARAM_SPEC, {"character": "Steiner", "row": 1, "menu_type": "Steiner"}),
    (bf.COMMAND_SET_SPEC, {"preset": "Vivi", "ability1": 8, "ability2": 9, "change_trance": 12}),
    (bf.LEVELING_SPEC, {"level": 50, "exp": 250000, "bonus_hp": 4000, "bonus_mp": 600}),
])
def test_player_spec_roundtrip(spec, entity):
    # the player/ability tuning specs serialise back to exactly the battle.toml block the build consumes
    assert forms.build_entity(spec, forms.entity_to_values(spec, entity)) == entity


def test_player_tables_registry_is_consistent():
    # every PLAYER_TABLES row exposes a spec, label, selector (present in its spec), and a default that
    # round-trips through build_entity (so "Add party tuning" seeds a valid, savable entry).
    for key, label, spec, selector, default in bf.PLAYER_TABLES:
        assert bf.PLAYER_SPECS[key] is spec and bf.PLAYER_LABEL[key] == label
        assert selector in {f.key for f in spec}, (key, selector)
        assert forms.build_entity(spec, forms.entity_to_values(spec, default)) == default


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


# ---- donor baseline (the read-only "what you're tuning from" panel) -----------------------------------
def _one_enemy_raw16(**stats):
    """A minimal 1-pattern / 1-type scene raw16 with put[0] -> type 0 and a MonParm carrying `stats`."""
    from ff9mapkit.battle import scene_codec as sc
    mon = sc.MonParm.unpack(bytes(116))                     # an all-zero record, then set the scalars we test
    for k, v in stats.items():
        setattr(mon, k, v)
    puts = [sc.Put(0, 1, 0, 0, 0, 0, 0, 0)] + [sc.Put(0, 0, 0, 0, 0, 0, 0, 0) for _ in range(3)]
    pat = sc.Pattern(rate=100, monster_count=1, camera=0, pad0=0, ap=10, puts=puts)
    scene = sc.Scene(head=bytes([0, 1, 1, 0, 0, 0, 0, 0]), patterns=[pat], monsters=[mon], attacks=[], tail=b"")
    return sc.serialize_scene(scene)


def test_donor_baseline_resolves_type_and_reads_stats():
    from ff9mapkit.workspace.battledoc import donor_baseline
    raw16 = _one_enemy_raw16(hp=1500, strength=22, magic=7, gil=84, exp=33, level=12)
    # explicit type
    res = donor_baseline(raw16, {"slot": 0, "type": 0})
    assert res is not None
    type_no, pairs = res
    assert type_no == 0
    d = dict(pairs)
    assert d["HP"] == 1500 and d["Str"] == 22 and d["Mag"] == 7 and d["Gil"] == 84 and d["Lv"] == 12
    # no explicit type -> resolved from pattern-0's put at the slot (put[0] -> type 0)
    assert donor_baseline(raw16, {"slot": 0})[0] == 0


def test_mes_strings_splits_and_strips_prefixes():
    from ff9mapkit.workspace.battledoc import _mes_strings
    raw = b"[STRT=33,1]Goblin[ENDN][STRT=27,1]Fang[ENDN][STRT=28,1]Knife[ENDN]"
    assert _mes_strings(raw) == ["Goblin", "Fang", "Knife"]   # [STRT=..] stripped, split on [ENDN], trailing empty dropped


def test_donor_scene_facts_decodes_flags_and_counts():
    from ff9mapkit.battle import scene_codec as sc
    from ff9mapkit.workspace.battledoc import donor_scene_facts
    mon = sc.MonParm.unpack(bytes(116))
    pat = sc.Pattern(100, 1, 0, 0, 10, [sc.Put(0, 1, 0, 0, 0, 0, 0, 0)] + [sc.Put(0, 0, 0, 0, 0, 0, 0, 0)] * 3)
    # header flags 0x22 = back_attack (0x02) + can't-escape/Runaway (0x20)
    import struct
    head = bytes([0, 1, 1, 0]) + struct.pack("<H", 0x22) + b"\x00\x00"
    raw16 = sc.serialize_scene(sc.Scene(head=head, patterns=[pat], monsters=[mon], attacks=[], tail=b""))
    d = dict(donor_scene_facts(raw16))
    assert d["Current flags"] == "back_attack, no_escape"
    assert d["Patterns"] == 1 and d["Enemy types"] == 1 and d["Attacks"] == 0
    assert donor_scene_facts(b"\x00\x01") is None             # truncated -> None, no crash


def test_donor_baseline_none_when_type_out_of_range_or_unparseable():
    from ff9mapkit.battle import scene_codec as sc
    from ff9mapkit.workspace.battledoc import donor_baseline
    raw16 = _one_enemy_raw16(hp=10)
    assert donor_baseline(raw16, {"slot": 0, "type": 5}) is None     # only type 0 exists
    assert donor_baseline(b"\x00\x01", {"slot": 0}) is None          # truncated raw16 -> no crash, just None
    # a put that references a type the scene doesn't have -> None (not an IndexError)
    mon = sc.MonParm.unpack(bytes(116))
    puts = [sc.Put(9, 1, 0, 0, 0, 0, 0, 0)] + [sc.Put(0, 0, 0, 0, 0, 0, 0, 0) for _ in range(3)]
    pat = sc.Pattern(rate=100, monster_count=1, camera=0, pad0=0, ap=10, puts=puts)
    bad = sc.serialize_scene(sc.Scene(head=bytes([0, 1, 1, 0, 0, 0, 0, 0]), patterns=[pat],
                                      monsters=[mon], attacks=[], tail=b""))
    assert donor_baseline(bad, {"slot": 0}) is None                  # put[0] -> type 9, only type 0 exists
