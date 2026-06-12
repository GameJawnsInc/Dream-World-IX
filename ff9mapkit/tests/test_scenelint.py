"""Pure tests for the offline battle-balance lint (no game install).

The lint's job is TRUST -- quiet on well-designed vanilla fights, loud only on real problems. These assert the
trustworthy-default behaviour (incl. a normal late-game enemy producing ZERO findings), per the 562-scene
adversarial sweep that caught the original over-firing heuristics.
"""
from __future__ import annotations

import struct

from ff9mapkit import items
from ff9mapkit.battle import battlecsv, scenelint
from ff9mapkit.battle.scene_codec import MonParm, Pattern, Put, Scene


def _mon(**kw) -> MonParm:
    """A neutral SB2_MON_PARM (HP 100, Lv 5, def 10, weak nothing, no statuses) -- override via kwargs."""
    base = dict(
        resist_status=0, auto_status=0, initial_status=0, hp=100, mp=10, gil=10, exp=10,
        drop=(255, 255, 255, 255), steal=(255, 255, 255, 255), radius=0, geo=0, mot=(0,) * 6, mesh=(0, 0),
        flags=0, ap=0, speed=10, strength=10, magic=10, spirit=10, elem_pad=0, trans=0, cur_capa=0,
        max_capa=0, guard_element=0, absorb_element=0, half_element=0, weak_element=0, level=5,
        category=0, hit_rate=100, phys_def=10, phys_evade=0, mag_def=10, mag_evade=0, blue_magic=0,
        bone=(0,) * 4, die_sfx=0, konran=0, mes_cnt=0, icon_bone=(0,) * 6, icon_y=(0,) * 6, icon_z=(0,) * 6,
        start_sfx=0, shadow_x=0, shadow_z=0, shadow_bone=0, win_card=0, shadow_ofs_x=0, shadow_ofs_z=0,
        shadow_bone2=0, pad0=0, pad1=0, pad2=0)
    base.update(kw)
    return MonParm(**base)


def _scene(monsters, *, ap=0, flags=0) -> Scene:
    head = bytes([1, 1, len(monsters), 0]) + struct.pack("<H", flags) + b"\x00\x00"
    pat = Pattern(rate=10, monster_count=len(monsters), camera=0, pad0=0, ap=ap,
                  puts=[Put(0, 1, 0, 0, 0, 0, 0, 0) for _ in range(4)])
    return Scene(head=head, patterns=[pat], monsters=list(monsters), attacks=[], tail=b"")


def _codes(findings):
    return {f.code for f in findings}


def test_normal_late_game_enemy_is_clean():
    # the regression the 562-scene sweep demanded: an ordinary late enemy (Lv32, big HP, real reward, modest
    # defence, no all-element/all-status immunity, level not %5) must produce ZERO findings.
    f = scenelint.lint_scene(_scene([_mon(level=32, hp=3727, phys_def=10, mag_def=12, exp=400, gil=300)], ap=8))
    assert f == []


def test_status_immunity_flagged():
    mask = battlecsv.encode_status(scenelint._OFFENSIVE_STATUSES)
    assert "status_immune" in _codes(scenelint.lint_scene(_scene([_mon(resist_status=mask)], ap=5)))


def test_element_wall_flagged_when_resisting_seven_plus():
    seven = battlecsv.encode_elements(["Fire", "Ice", "Thunder", "Earth", "Water", "Wind", "Holy"])
    assert "element_wall" in _codes(scenelint.lint_scene(_scene([_mon(guard_element=seven)], ap=5)))
    # a normal enemy resisting one or two elements is NOT a wall
    two = battlecsv.encode_elements(["Fire", "Ice"])
    assert "element_wall" not in _codes(scenelint.lint_scene(_scene([_mon(half_element=two)], ap=5)))


def test_level5_only_and_death_gated():
    assert "level5" in _codes(scenelint.lint_scene(_scene([_mon(level=20)], ap=5)))      # %5, not Death-immune
    assert "level5" not in _codes(scenelint.lint_scene(_scene([_mon(level=21)], ap=5)))  # not a multiple of 5
    # Death-immune enemies are NOT flagged (LV5 Death wouldn't land)
    death = battlecsv.encode_status(["Death"])
    assert "level5" not in _codes(scenelint.lint_scene(_scene([_mon(level=20, resist_status=death)], ap=5)))
    assert "level5" not in _codes(scenelint.lint_scene(_scene([_mon(level=20, auto_status=death)], ap=5)))
    # the noisy LV4/LV3 divisibility notes are gone
    assert not (_codes(scenelint.lint_scene(_scene([_mon(level=12)], ap=5))) & {"level4", "level3"})


def test_no_reward_warns():
    f = scenelint.lint_scene(_scene([_mon(exp=0, gil=0)], ap=0))
    assert any(x.code == "no_reward" and x.severity == "warn" for x in f)
    assert "no_reward" not in _codes(scenelint.lint_scene(_scene([_mon(exp=0, gil=0)], ap=7)))  # AP is a reward


def test_bad_item_id_warns(monkeypatch):
    monkeypatch.setattr(items, "name_of", lambda i: None if i == 123 else "Potion")
    f = scenelint.lint_scene(_scene([_mon(drop=(123, 255, 255, 255))], ap=5))
    assert any(x.code == "bad_item" and x.severity == "warn" for x in f)


def test_defence_wall_band():
    # an AUTHORED wall (>= the weapon-power band) flags; a real-enemy-max defence (~24) does not
    assert "phys_wall" in _codes(scenelint.lint_scene(_scene([_mon(phys_def=255)], ap=5)))
    assert "mag_wall" in _codes(scenelint.lint_scene(_scene([_mon(mag_def=60)], ap=5)))
    assert not ({"phys_wall", "mag_wall"} & _codes(scenelint.lint_scene(_scene([_mon(phys_def=24, mag_def=24)], ap=5))))


def test_placeholder_type_skipped():
    # hp<=1 types (multipart/placeholder) are not linted as real combatants
    assert scenelint.lint_scene(_scene([_mon(hp=1, exp=0, gil=0)], ap=0)) == []


def test_format_findings_empty_and_grouped():
    assert "no balance problems" in scenelint.format_findings([])
    out = scenelint.format_findings([scenelint.Finding("warn", "x", "bad"), scenelint.Finding("info", "y", "note")])
    assert "1 warning(s), 1 note(s)" in out
    assert "[warn] bad" in out and "[info] note" in out
