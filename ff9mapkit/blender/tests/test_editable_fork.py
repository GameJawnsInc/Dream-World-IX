"""Blender editable-fork re-export parity (bpy-free side).

When you `ff9mapkit import --editable` a real field and re-export from Blender, the field.toml must
build identically to the CLI: a custom scene over the forked field with the real camera, per-depth
art (occlusion + light/shadow shaders preserved), and a WORLD-frame walkmesh (no character offset).
These cover the bpy-free formatters (`layers_to_toml` shader, `editable_field_toml`) and a full dry
run through the REAL builder. The multi-floor seam reconcile itself is covered by the kit's
test_export.py + the in-game proof; here we assert the emitted structure + layers/shaders survive.
"""

from __future__ import annotations

import struct
import sys
import tomllib
import zlib
from pathlib import Path

BLENDER = Path(__file__).resolve().parents[1]
KIT_ROOT = BLENDER.parent
sys.path.insert(0, str(BLENDER))
sys.path.insert(0, str(KIT_ROOT))

from ff9mapkit_blender import bridge                  # noqa: E402
from ff9mapkit_blender.vendor import bgx              # noqa: E402
from ff9mapkit.build import FieldProject, build_mod   # noqa: E402
from ff9mapkit.config import ModLayout, LANGS         # noqa: E402


def _png(path, w, h):
    """Write a minimal valid RGBA PNG (transparent) of size w x h -- no PIL."""
    def chunk(typ, data):
        body = typ + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)
    raw = b"".join(b"\x00" + b"\x00\x00\x00\x00" * w for _ in range(h))   # filter 0 + transparent
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw))
           + chunk(b"IEND", b""))
    path.write_bytes(png)


# --------------------------------------------------------------------------- formatters
def test_layers_to_toml_carries_shader_when_present():
    doc = tomllib.loads(bridge.layers_to_toml([
        {"image": "layer_04088_None.png", "z": 4088},                       # opaque -> no shader key
        {"image": "layer_00553_1.png", "z": 553, "shader": "PSX/FieldMap_Abr_1"},
        ("layer_00008_2.png", 8, "PSX/FieldMap_Abr_2"),                      # tuple form
    ]))
    assert "shader" not in doc["layers"][0]
    assert doc["layers"][1]["shader"] == "PSX/FieldMap_Abr_1"
    assert doc["layers"][2]["z"] == 8 and doc["layers"][2]["shader"] == "PSX/FieldMap_Abr_2"


def test_editable_field_toml_structure_multifloor():
    meta = {"field_id": 4003, "field_name": "GRGR_EDIT", "area": 21, "text_block": 1073}
    layers = [{"image": "layer_04088_None.png", "z": 4088},
              {"image": "layer_00553_1.png", "z": 553, "shader": "PSX/FieldMap_Abr_1"}]
    doc = tomllib.loads(bridge.editable_field_toml(meta, layers, has_links=True))
    assert doc["field"]["id"] == 4003 and doc["field"]["area"] == 21
    assert doc["camera"]["borrow"] == "camera.bgx"
    wm = doc["walkmesh"]
    assert wm["obj"] == "walkmesh.obj"
    assert wm["links"] == "walkmesh.links.toml"          # multi-floor: ships the seam sidecar
    assert wm["frame"] == "world"                         # forked frame: verbatim verts
    assert "character_offset" not in wm                   # real-field frame -> no flat-room shift
    assert doc["layers"][1]["shader"] == "PSX/FieldMap_Abr_1"


def test_editable_field_toml_single_floor_omits_links():
    meta = {"field_id": 4005, "field_name": "GLGV_EDIT", "area": 36, "text_block": 1073}
    doc = tomllib.loads(bridge.editable_field_toml(meta, [{"image": "back.png", "z": 4000}],
                                                   has_links=False))
    assert doc["walkmesh"]["obj"] == "walkmesh.obj" and doc["walkmesh"]["frame"] == "world"
    assert "links" not in doc["walkmesh"]                 # single floor -> obj rebuild is lossless


# --------------------------------------------------------------------------- full dry run
def test_editable_fork_builds_with_layers_and_shaders(tmp_path):
    proj = tmp_path / "proj"; proj.mkdir()
    # exact extracted camera (preserved on re-export)
    eye = (0.0, -3000.0, 3000.0)
    R_bl = bridge.look_at_blender(eye, (0.0, 0.0, 0.0))
    c = bridge.blender_cam_to_ff9(eye, R_bl, bridge.H_to_lens(497, bridge.DEFAULT_SENSOR, 384))
    (proj / "camera.bgx").write_text(bgx.build(c, []), encoding="utf-8")
    # world-frame walkmesh (single floor here; the verts ARE the in-game positions)
    verts = [(-1000.0, 0.0, -1000.0), (1000.0, 0.0, -1000.0), (1000.0, 0.0, 1000.0), (-1000.0, 0.0, 1000.0)]
    (proj / "walkmesh.obj").write_text(
        bridge.mesh_to_ff9_obj(verts, [(0, 1, 2), (0, 2, 3)]), encoding="utf-8")
    # per-depth art: a back (opaque) + a foreground occluder + a light (additive shader)
    for name in ("back.png", "front.png", "light.png"):
        _png(proj / name, 96, 112)                        # 6:7 == the 384x448 canvas aspect
    layers = [{"image": "back.png", "z": 4000},
              {"image": "front.png", "z": 8},
              {"image": "light.png", "z": 553, "shader": "PSX/FieldMap_Abr_1"}]
    meta = {"field_id": 4007, "field_name": "FORK_EDIT", "area": 21, "text_block": 1073}
    (proj / "fork_edit.field.toml").write_text(
        bridge.editable_field_toml(meta, layers, spawn=(0, 0), has_links=False), encoding="utf-8")

    out = tmp_path / "mod"
    info = build_mod([FieldProject.load(proj / "fork_edit.field.toml")], out, mod_name="FF9CustomMap")
    assert info["dictionary"] == ["FieldScene 4007 21 FORK_EDIT FORK_EDIT 1073"]
    L = ModLayout(out)
    fm = L.fieldmap_dir("FBG_N21_FORK_EDIT")
    scene = (fm / "FBG_N21_FORK_EDIT.bgx").read_text(encoding="utf-8")
    # all three layers shipped; the light layer kept its additive shader
    for name in ("back.png", "front.png", "light.png"):
        assert name in scene and (fm / name).is_file()
    assert "PSX/FieldMap_Abr_1" in scene
    # world-frame walkmesh present; per-lang scripts built
    assert (fm / "FBG_N21_FORK_EDIT.bgi.bytes").is_file()
    for lang in LANGS:
        assert L.eb_path(lang, "EVT_FORK_EDIT.eb.bytes").is_file()
