"""Phase 2: Blender content markers (NPC / gateway / player spawn) -> field.toml -> build.

Validates the bpy-free side of the marker pipeline: the coordinate mapping for floor markers,
the TOML formatters (parse as valid TOML), and a full dry run where an NPC (with dialogue), a
gateway, and a player spawn flow through the REAL ff9mapkit builder into a compiled field.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

BLENDER = Path(__file__).resolve().parents[1]
KIT_ROOT = BLENDER.parent
sys.path.insert(0, str(BLENDER))
sys.path.insert(0, str(KIT_ROOT))

from ff9mapkit_blender import bridge                  # noqa: E402
from ff9mapkit_blender.vendor import bgx              # noqa: E402
from ff9mapkit.build import FieldProject, build_mod   # noqa: E402
from ff9mapkit.config import ModLayout, LANGS         # noqa: E402


def test_marker_floor_pos_maps_blender_to_ff9_xz():
    # a floor marker at Blender (x, y, 0): FF9 x = Blender x, FF9 z = Blender y (y<->z swap, floor y=0)
    assert bridge.marker_floor_pos((300.0, -700.0, 0.0)) == (300, -700)
    assert bridge.marker_floor_pos((-1234.6, 880.4, 0.0)) == (-1235, 880)


def test_npcs_to_toml_is_valid_and_complete():
    npcs = [
        {"pos": (0, -700), "name": "Vivi", "preset": "vivi", "dialogue": 'He said "hi"\nthen left'},
        {"pos": (400, -200), "model": 21, "animset": 0, "anims": [2494, 2501, 2501, 2499, 2497]},
    ]
    doc = tomllib.loads(bridge.npcs_to_toml(npcs))
    assert doc["npc"][0]["preset"] == "vivi"
    assert doc["npc"][0]["pos"] == [0, -700]
    assert doc["npc"][0]["dialogue"] == 'He said "hi"\nthen left'   # escaping round-trips
    assert doc["npc"][1]["model"] == 21 and doc["npc"][1]["anims"] == [2494, 2501, 2501, 2499, 2497]


def test_gateways_and_player_toml_valid():
    gw = [{"to": 100, "entrance": 4, "zone": [(-700, -2400), (700, -2400), (700, -1900), (-700, -1900)]}]
    doc = tomllib.loads(bridge.gateways_to_toml(gw))
    assert doc["gateway"][0]["to"] == 100 and len(doc["gateway"][0]["zone"]) == 4
    assert tomllib.loads(bridge.player_to_toml((12, -345)))["player"]["spawn"] == [12, -345]


def test_markers_build_into_a_field(tmp_path):
    proj = tmp_path / "proj"; proj.mkdir()
    eye = (0.0, -3000.0, 3000.0)
    R_bl = bridge.look_at_blender(eye, (0.0, 0.0, 0.0))
    c = bridge.blender_cam_to_ff9(eye, R_bl, bridge.H_to_lens(497, bridge.DEFAULT_SENSOR, 384))
    (proj / "camera.bgx").write_text(bgx.build(c, []), encoding="utf-8")
    verts = [(-1000.0, -2000.0, 0.0), (1000.0, -2000.0, 0.0), (1000.0, 0.0, 0.0), (-1000.0, 0.0, 0.0)]
    (proj / "walkmesh.obj").write_text(bridge.mesh_to_ff9_obj(verts, [(0, 1, 2), (0, 2, 3)]), encoding="utf-8")

    npc_block = bridge.npcs_to_toml([{"pos": (0, -700), "name": "Greeter", "preset": "vivi",
                                      "dialogue": "Welcome to my room."}])
    gw_block = bridge.gateways_to_toml([{"to": 100, "entrance": 0,
                                         "zone": [(-900, -1900), (900, -1900), (900, -1500), (-900, -1500)]}])
    player_block = bridge.player_to_toml((0, -900))
    (proj / "room.field.toml").write_text(
        '[field]\nid = 4009\nname = "MARKER_ROOM"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\nborrow = "camera.bgx"\n\n'
        '[walkmesh]\nobj = "walkmesh.obj"\n\n'
        + player_block + "\n\n" + npc_block + "\n\n" + gw_block + "\n", encoding="utf-8")

    out = tmp_path / "mod"
    info = build_mod([FieldProject.load(proj / "room.field.toml")], out, mod_name="FF9CustomMap")
    assert info["dictionary"] == ["FieldScene 4009 11 MARKER_ROOM MARKER_ROOM 1073"]
    L = ModLayout(out)
    for lang in LANGS:
        assert L.eb_path(lang, "EVT_MARKER_ROOM.eb.bytes").is_file()
    # the NPC dialogue became a .mes entry
    mes = L.mes_path("us", 1073).read_text(encoding="utf-8")
    assert "Welcome to my room." in mes
