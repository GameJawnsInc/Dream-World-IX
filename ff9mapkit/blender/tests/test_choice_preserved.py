"""Choices are LOGIC, so the Blender pipeline must (a) hint them in the scaffolded field.toml, (b)
never put them in the always-overwritten scene.toml, and (c) preserve a hand-authored ``[[choice]]``
through the two-file merge. (Re-export keeps an existing field.toml entirely -- see
``ops._write_split_files``: it writes the stub only when the file is absent.) bpy-free."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

BLENDER = Path(__file__).resolve().parents[1]
KIT_ROOT = BLENDER.parent
sys.path.insert(0, str(BLENDER))
sys.path.insert(0, str(KIT_ROOT))

from ff9mapkit_blender import bridge          # noqa: E402
from ff9mapkit import build                   # noqa: E402

_META = {"field_id": 4003, "field_name": "ROOM", "area": 11, "text_block": 1073, "borrow_bg": ""}


def test_logic_stub_hints_a_choice_and_avoids_the_sapphire_footgun():
    stub = bridge.field_logic_stub(_META, npcs=[{"name": "Vivi", "preset": "vivi"}])
    assert "[[choice]]" in stub and "[[choice.options]]" in stub
    assert '["Potion"' in stub and "[232, 1]" not in stub      # names, not the 232=Sapphire trap
    tomllib.loads(stub)                                         # the commented hint keeps it valid TOML


def test_scene_toml_never_holds_a_choice():
    # choices live ONLY in the field.toml (logic); the Blender-owned scene.toml is spatial-only.
    s = bridge.scene_toml("ROOM", '[camera]\nborrow = "camera.bgx"\n',
                          npcs=[{"name": "Vivi", "pos": [0, -700]}])
    assert "choice" not in s


def test_merge_preserves_a_hand_authored_choice():
    field_cfg = {"field": {"id": 4003, "name": "R", "area": 11},
                 "npc": [{"name": "Vivi", "preset": "vivi", "dialogue": "hi"}],
                 "choice": [{"npc": "Vivi", "prompt": "?", "options": [{"text": "Y"}, {"text": "N"}]}]}
    scene_cfg = {"camera": {"borrow": "camera.bgx"}, "npc": [{"name": "Vivi", "pos": [0, -700]}]}
    merged = build._merge_scene(field_cfg, scene_cfg)
    assert merged["choice"] == field_cfg["choice"]             # the choice survives the split untouched
    assert merged["npc"][0]["pos"] == [0, -700]                # ...and the NPC gets its Blender position
