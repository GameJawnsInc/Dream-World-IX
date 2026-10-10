"""The field's EventAnimation clip list (ff9mapkit.eventanim) -- what a battle return re-adds to a rebuilt model.

A battle return rebuilds every field model and re-adds only the field's ``EVT_<name>.txt`` list plus the five
locomotion slots, so a kit field (which shipped no list) lost the player's inactive fidget: the idle timer then
played a clip the model no longer had and Memoria's frame smoother threw every frame (studies/after-battle-clips:
260 NullReferenceExceptions without the list, none with it). These tests pin the scan, the two format rules the
engine's parser enforces with an exception (every model-line clip is on line 1; only a loadable clip is listed),
and that the build ships the list.
"""
from __future__ import annotations

import pytest
from PIL import Image

from ff9mapkit import eventanim
from ff9mapkit._animdb_all import ANIMATIONS
from ff9mapkit.eb import opcodes

from .test_main_init_prepend import _eb

RET = opcodes.RETURN
CONST_57 = bytes([0x7D, 57, 0, 0x7F])          # an EXPRESSION operand: the engine resolves it, the scan can't


def _player_and_npc() -> bytes:
    player = (opcodes.encode(eventanim.SET_MODEL_OP, 98, 93) + opcodes.encode(0x33, 200)
              + opcodes.encode(0x34, 25) + opcodes.encode(0x35, 38) + opcodes.encode(0x7A, 40)
              + opcodes.encode(0x7B, 41) + opcodes.encode(0x52, 57) + RET)
    npc = (opcodes.encode(eventanim.SET_MODEL_OP, 8, 50) + opcodes.encode(0x33, 148)
           + opcodes.encode(0x40, CONST_57, arg_flags=1)                   # RunAnimation(<expr>) -- skipped
           + RET)
    conductor = (opcodes.encode(0xBD, 3, 1896)                             # RunAnimationEx(entry, anim)
                 + opcodes.encode(0x119, 3, 0, 2089) + RET)                # SetLogicalAnimationEx(entry, kind, anim)
    return _eb([(0, RET)], [(0, player)], [(0, npc)], [(0, conductor)])


def test_scan_reads_every_clip_op_and_skips_an_expression_operand():
    clips, models = eventanim.scan(_player_and_npc())
    assert clips == {200, 25, 38, 40, 41, 57, 148, 1896, 2089}
    assert models == {98, 8}


def test_the_list_has_the_inactive_fidget_and_obeys_the_parsers_rules():
    text = eventanim.event_animation_text([_player_and_npc()])
    assert not text.startswith("﻿") and "\r" not in text
    first, *models = text.rstrip("\n").split("\n")
    assert first.startswith("animation:")
    listed = first[len("animation:"):].split(",")
    assert all(listed) and len(listed) == len(set(listed))
    by_model = {ln.split(":")[0]: ln.split(":")[1].split(",") for ln in models}
    # every model-line clip must be on line 1 (AddAnimToGameObject indexes the line-1 dictionary -- a miss throws)
    assert all(c and c in listed for clips in by_model.values() for c in clips)
    assert ANIMATIONS[57] in by_model["GEO_MAIN_F0_ZDN"]              # THE clip the battle return used to lose
    assert set(by_model["GEO_MAIN_F0_VIV"]) == {ANIMATIONS[148]}        # a family's own clips only
    assert "GEO_ACC_F0_SUP" in by_model and "GEO_MAIN_F0_GRN" in by_model   # cross-entry ops land on their owner


def test_an_unloadable_clip_is_never_listed():
    """A line-1 clip the engine cannot load reaches ``Animation.AddClip`` as null -- so a minted / unknown id is
    left to the script op that adds it (as before), and a field with nothing listable ships no list at all."""
    assert 60001 not in ANIMATIONS
    eb = _eb([(0, opcodes.encode(eventanim.SET_MODEL_OP, 98, 93) + opcodes.encode(0x40, 60001) + RET)])
    assert eventanim.scan(eb)[0] == {60001}
    assert eventanim.event_animation_text([eb]) is None


def test_languages_are_unioned():
    a = _eb([(0, opcodes.encode(0x33, 200) + RET)])
    b = _eb([(0, opcodes.encode(0x52, 57) + RET)])
    first = eventanim.event_animation_text([a, b]).split("\n")[0]
    assert ANIMATIONS[200] in first and ANIMATIONS[57] in first


def test_the_build_ships_the_list(tmp_path):
    from ff9mapkit.build import FieldProject, build_mod
    from ff9mapkit.config import ModLayout
    for png in ("back.png", "floor.png"):
        Image.new("RGBA", (768 * 2, 448 * 2), (40, 40, 40, 255)).save(tmp_path / png)
    toml = tmp_path / "fidget.field.toml"
    toml.write_text(
        '[field]\nid=4003\nname="FIDGETT"\narea=11\n\n'
        "[camera]\npitch=48\ndistance=4500\nfov=42.2\n\n"
        '[walkmesh]\nquad=[[-1220,257],[1220,257],[1220,-1931],[-1220,-1931]]\nframe="world"\n\n'
        '[[layers]]\nimage="back.png"\nz=4000\n[[layers]]\nimage="floor.png"\nz=3000\n\n'
        "[player]\nspawn=[0,-1200]\n\n"
        '[[npc]]\nname="vivi"\nmodel="GEO_MAIN_F0_VIV"\npos=[-500,-700]\ndialogue="Hi."\n',
        encoding="utf-8")
    out = tmp_path / "mod"
    build_mod([FieldProject.load(toml)], out, mod_name="FF9CustomMap")
    path = ModLayout(out).eventanimation_path("EVT_FIDGETT")
    assert path.name == "EVT_FIDGETT.txt.bytes"
    text = path.read_text(encoding="utf-8")
    zdn = [ln for ln in text.splitlines() if ln.startswith("GEO_MAIN_F0_ZDN:")]
    assert zdn and ANIMATIONS[57] in zdn[0].split(":")[1].split(",")


@pytest.mark.parametrize("op", sorted(eventanim.CLIP_ARG))
def test_every_clip_op_is_a_known_opcode(op):
    from ff9mapkit.content import npc
    from ff9mapkit.eb._optables import OP_NAMES
    if op == 0x35:                  # ARUN: unnamed in the optable (disasm prints op_35), the NPC run slot op
        assert op in npc._ANIM_OPS
        return
    assert "Animation" in OP_NAMES[op]
