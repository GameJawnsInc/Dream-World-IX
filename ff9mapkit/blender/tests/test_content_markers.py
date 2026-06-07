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
from ff9mapkit_blender.vendor import bgx, cam         # noqa: E402
from ff9mapkit.build import FieldProject, build_mod   # noqa: E402
from ff9mapkit.config import ModLayout, LANGS         # noqa: E402
from ff9mapkit.eb import EbScript, disasm             # noqa: E402


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


# --- event-zone markers (Phase 1) ---------------------------------------------------------
def test_events_to_toml_is_valid_and_complete():
    events = [
        {"name": "chest", "zone": [(-700, -2400), (700, -2400), (700, -1900), (-700, -1900)],
         "message": "You got a Potion!", "give_item": [232, 1], "gil": 1000,
         "set_flag": [200, 1], "once": True},
        {"name": "lever", "zone": [(0, 0), (100, 0), (100, 100), (0, 100)], "set_flag": 201,
         "once": False, "requires_flag": 200},
    ]
    doc = tomllib.loads(bridge.events_to_toml(events))
    assert doc["event"][0]["name"] == "chest" and len(doc["event"][0]["zone"]) == 4
    assert doc["event"][0]["give_item"] == [232, 1] and doc["event"][0]["gil"] == 1000
    assert doc["event"][0]["set_flag"] == [200, 1] and doc["event"][0]["once"] is True
    assert doc["event"][1]["set_flag"] == [201, 1]      # a bare int index -> [idx, 1]
    assert doc["event"][1]["once"] is False and doc["event"][1]["requires_flag"] == 200


def test_event_scene_field_split_keeps_zone_and_logic_apart():
    events = [{"name": "chest", "zone": [(-700, -2400), (700, -2400), (700, -1900), (-700, -1900)],
               "message": "You got a Potion!", "set_flag": [200, 1], "once": True}]
    # scene.toml: ONLY spatial (name + zone), no logic
    scene = tomllib.loads(bridge.scene_toml("ROOM", '[camera]\nborrow = "camera.bgx"\n', events=events))
    assert scene["event"][0]["name"] == "chest" and len(scene["event"][0]["zone"]) == 4
    assert "message" not in scene["event"][0] and "set_flag" not in scene["event"][0]
    # field.toml stub: the logic (name + message + set_flag), NO zone
    meta = {"field_id": 4009, "field_name": "ROOM", "area": 11, "text_block": 1073}
    field = tomllib.loads(bridge.field_logic_stub(meta, events=events))
    assert field["event"][0]["name"] == "chest"
    assert field["event"][0]["message"] == "You got a Potion!"
    assert field["event"][0]["set_flag"] == [200, 1] and "zone" not in field["event"][0]


def test_event_markers_build_into_a_field(tmp_path):
    proj = tmp_path / "proj"; proj.mkdir()
    eye = (0.0, -3000.0, 3000.0)
    R_bl = bridge.look_at_blender(eye, (0.0, 0.0, 0.0))
    c = bridge.blender_cam_to_ff9(eye, R_bl, bridge.H_to_lens(497, bridge.DEFAULT_SENSOR, 384))
    (proj / "camera.bgx").write_text(bgx.build(c, []), encoding="utf-8")
    verts = [(-1000.0, -2000.0, 0.0), (1000.0, -2000.0, 0.0), (1000.0, 0.0, 0.0), (-1000.0, 0.0, 0.0)]
    (proj / "walkmesh.obj").write_text(bridge.mesh_to_ff9_obj(verts, [(0, 1, 2), (0, 2, 3)]), encoding="utf-8")

    events = [{"name": "chest", "zone": [(-900, -1900), (900, -1900), (900, -1500), (-900, -1500)],
               "message": "You found a chest!", "set_flag": [200, 1], "once": True}]
    # exactly what Blender writes: zone in the scene, actions in the field stub, merged by name.
    (proj / "room.scene.toml").write_text(
        bridge.scene_toml("EVT_ROOM",
                          '[camera]\nborrow = "camera.bgx"\n\n[walkmesh]\nobj = "walkmesh.obj"\n',
                          events=events), encoding="utf-8")
    meta = {"field_id": 4011, "field_name": "EVT_ROOM", "area": 11, "text_block": 1073}
    (proj / "room.field.toml").write_text(bridge.field_logic_stub(meta, events=events), encoding="utf-8")

    out = tmp_path / "mod"
    info = build_mod([FieldProject.load(proj / "room.field.toml")], out, mod_name="FF9CustomMap")
    assert info["dictionary"] == ["FieldScene 4011 11 EVT_ROOM EVT_ROOM 1073"]
    mes = ModLayout(out).mes_path("us", 1073).read_text(encoding="utf-8")
    assert "You found a chest!" in mes


# --- waypoint markers (movement points) ---------------------------------------------------
def test_markers_to_toml_and_scene_split():
    markers = [{"name": "door", "pos": (0, -700)}, {"name": "altar", "pos": (100, 200)}]
    d = tomllib.loads(bridge.markers_to_toml(markers))
    assert d["marker"][0] == {"name": "door", "pos": [0, -700]}
    # markers are spatial-only -> they land in the scene.toml (no logic counterpart)
    scene = tomllib.loads(bridge.scene_toml("R", '[camera]\nborrow = "c.bgx"\n', markers=markers))
    assert [m["name"] for m in scene["marker"]] == ["door", "altar"]


def test_waypoint_marker_builds_into_a_field(tmp_path):
    proj = tmp_path / "proj"; proj.mkdir()
    eye = (0.0, -3000.0, 3000.0)
    R = bridge.look_at_blender(eye, (0.0, 0.0, 0.0))
    c = bridge.blender_cam_to_ff9(eye, R, bridge.H_to_lens(497, bridge.DEFAULT_SENSOR, 384))
    (proj / "camera.bgx").write_text(bgx.build(c, []), encoding="utf-8")
    verts = [(-1000.0, -2000.0, 0.0), (1000.0, -2000.0, 0.0), (1000.0, 0.0, 0.0), (-1000.0, 0.0, 0.0)]
    (proj / "walkmesh.obj").write_text(bridge.mesh_to_ff9_obj(verts, [(0, 1, 2), (0, 2, 3)]), encoding="utf-8")
    # scene: an NPC position + a named movement marker (the walk target) -- both spatial
    (proj / "room.scene.toml").write_text(
        bridge.scene_toml("WP_ROOM", '[camera]\nborrow = "camera.bgx"\n\n[walkmesh]\nobj = "walkmesh.obj"\n',
                          npcs=[{"name": "Vivi", "pos": (0, -200)}],
                          markers=[{"name": "spot", "pos": (0, -1500)}]), encoding="utf-8")
    # field: NPC logic + a cutscene that walks to the marker BY NAME
    (proj / "room.field.toml").write_text(
        '[field]\nid = 4012\nname = "WP_ROOM"\narea = 11\ntext_block = 1073\n\n'
        '[[npc]]\nname = "Vivi"\npreset = "vivi"\n\n'
        '[cutscene]\nactor = "Vivi"\nonce = false\nsteps = [ { walk = "spot" } ]\n', encoding="utf-8")
    from ff9mapkit.build import validate
    p = FieldProject.load(proj / "room.field.toml")
    assert not any("spot" in m for m in validate(p))           # the marker resolves (merged from scene)
    info = build_mod([p], tmp_path / "mod", mod_name="FF9CustomMap")
    assert info["dictionary"] == ["FieldScene 4012 11 WP_ROOM WP_ROOM 1073"]


# --- multi-camera: camera array + switch zones (Phase A bridge) -------------------------
def test_multicam_bridge_toml_is_valid():
    import tomllib
    cams = tomllib.loads(bridge.cameras_borrow_toml(["camera0.bgx", "camera1.bgx", "camera2.bgx"]))
    assert [c["borrow"] for c in cams["camera"]] == ["camera0.bgx", "camera1.bgx", "camera2.bgx"]
    zones = tomllib.loads(bridge.camera_zones_to_toml([
        {"to_camera": 1, "zone": [(100, -1900), (900, -1900), (900, -1500), (100, -1500)]},
        {"to_camera": 0, "zone": [(-900, -1900), (-100, -1900), (-100, -1500), (-900, -1500)]}]))
    assert zones["camera_zone"][0]["to_camera"] == 1 and len(zones["camera_zone"][0]["zone"]) == 4
    assert zones["camera_zone"][1]["to_camera"] == 0
    lay = tomllib.loads(bridge.layers_to_toml([{"image": "bg0.png", "z": 4000, "camera": 0},
                                               {"image": "bg1.png", "z": 4000, "camera": 1}]))
    assert "camera" not in lay["layers"][0]            # camera 0 is the default -> omitted
    assert lay["layers"][1]["camera"] == 1


def _bcam(yaw_deg, tmp_path, name):
    """A posed FF9 camera written to a one-CAMERA .bgx (what the Blender export does per camera)."""
    eye = (0.0, -3000.0, 3000.0)
    R = bridge.look_at_blender(eye, (0.0, 0.0, 0.0))
    c = bridge.blender_cam_to_ff9(eye, R, bridge.H_to_lens(497, bridge.DEFAULT_SENSOR, 384))
    c.r, c.t = cam.synth_r_t(cam.decompose(c)["C"], cam.decompose(c)["R_ortho"], c.proj)  # keep it valid
    (tmp_path / name).write_text(bgx.build(c, []), encoding="utf-8")
    return name


def test_multicam_field_builds_with_two_cameras_and_a_switch_zone(tmp_path):
    proj = tmp_path / "proj"; proj.mkdir()
    c0 = _bcam(0.0, proj, "camera0.bgx")
    c1 = _bcam(25.0, proj, "camera1.bgx")
    verts = [(-1200.0, -2000.0, 0.0), (1200.0, -2000.0, 0.0), (1200.0, 0.0, 0.0), (-1200.0, 0.0, 0.0)]
    (proj / "walkmesh.obj").write_text(bridge.mesh_to_ff9_obj(verts, [(0, 1, 2), (0, 2, 3)]), encoding="utf-8")
    cam_block = bridge.cameras_borrow_toml([c0, c1])
    zone_block = bridge.camera_zones_to_toml(
        [{"to_camera": 1, "zone": [(100, -1900), (1100, -1900), (1100, -1500), (100, -1500)]}])
    (proj / "mc.field.toml").write_text(
        '[field]\nid = 4012\nname = "MULTICAM_T"\narea = 11\ntext_block = 1073\n\n'
        + cam_block + '\n\n[walkmesh]\nobj = "walkmesh.obj"\nframe = "world"\n\n'
        + '[player]\nspawn = [0, -900]\n\n' + zone_block + "\n", encoding="utf-8")

    out = tmp_path / "mod"
    info = build_mod([FieldProject.load(proj / "mc.field.toml")], out, mod_name="FF9CustomMap")
    fbg = info["fields"][0]
    # the built scene .bgx carries BOTH cameras
    scene_bgx = ModLayout(out).fieldmap_dir(fbg) / f"{fbg}.bgx"
    assert len(cam.parse_bgx_cameras(str(scene_bgx))) == 2
    # the script got a SETCAM (0x7E) switch from the camera zone
    eb = ModLayout(out).eb_path("us", f"EVT_{info['dictionary'][0].split()[4]}.eb.bytes").read_bytes()
    s = EbScript.from_bytes(eb)
    ops = {i.op for ent in s.entries for fn in ent.funcs for i in disasm.iter_code(eb, fn.abs_start, fn.abs_end)}
    assert 0x7E in ops          # SetFieldCamera injected by the switch zone
