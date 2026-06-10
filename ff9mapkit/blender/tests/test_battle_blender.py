"""Offline validation of the bpy-free battle-map (BBG geometry) bridge (NO bpy import).

The Blender battle loop is: parse a kit FBX -> groups -> Blender mesh data (import), reshape, then
Blender mesh data -> groups -> emit FBX (export). These tests pin the pure conversions so the bpy
operators (which only do the bpy<->plain-list extraction) stay trivial + trustworthy.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # .../ff9mapkit/blender
from ff9mapkit_blender import bridge                            # noqa: E402
from ff9mapkit_blender.vendor import battle_fbx                 # noqa: E402


def _groups():
    return [
        {"name": "Group_2", "verts": [[-1, 0, -1], [1, 0, -1], [1, 0, 1], [-1, 0, 1]],
         "normals": [[0, 1, 0]] * 4, "uvs": [[0, 0], [1, 0], [1, 1], [0, 1]],
         "submeshes": [{"texture": "image6", "tris": [[0, 1, 2], [0, 2, 3]]}]},
        {"name": "Group_0", "verts": [[0, 0, 0], [0, 10, 0], [5, 0, 0]],
         "normals": None, "uvs": [[0, 0], [0, 1], [1, 0]],
         "submeshes": [{"texture": "image0", "tris": [[0, 1, 2]]},
                       {"texture": "image1", "tris": [[2, 1, 0]]}]},
    ]


def test_unity_blender_transform_is_an_involution():
    verts = [[10.0, -2135.0, 7.5], [0, 0, 0], [-3, 4, 5]]
    rt = [list(v) for v in bridge.battle_blender_to_unity(bridge.battle_unity_to_blender(verts))]
    assert rt == [list(v) for v in verts]
    # ground (Unity y=0) maps to a flat Blender z=0 plane (legible to reshape)
    bl = bridge.battle_unity_to_blender([[1, 0, 2], [3, 0, 4]])
    assert all(abs(v[2]) < 1e-9 for v in bl)


def test_group_meshdata_roundtrip():
    g = _groups()[1]                                      # the 2-submesh Group_0
    md = bridge.group_to_blender_meshdata(g)
    assert md["name"] == "Group_0"
    assert md["materials"] == ["image0", "image1"]        # one material slot per submesh
    assert md["face_material"] == [0, 1]                  # one tri each, in slot order
    back = bridge.blender_meshdata_to_group(
        md["name"], md["verts"], md["faces"], md["face_material"], md["materials"], md["uvs"])
    assert back["verts"] == g["verts"]                    # positions verbatim (involution)
    assert back["uvs"] == g["uvs"]
    assert [(sm["texture"], sm["tris"]) for sm in back["submeshes"]] == \
        [("image0", [[0, 1, 2]]), ("image1", [[2, 1, 0]])]   # submeshes + winding preserved


def test_full_loop_parse_meshdata_emit_matches_geometry():
    # the whole import->export path at the data level: FBX -> groups -> meshdata -> groups -> FBX.
    orig, _ = battle_fbx.emit_fbx(_groups())
    parsed = battle_fbx.parse_fbx(orig)
    rebuilt = []
    for g in parsed:
        md = bridge.group_to_blender_meshdata(g)
        rebuilt.append(bridge.blender_meshdata_to_group(
            md["name"], md["verts"], md["faces"], md["face_material"], md["materials"], md["uvs"]))
    # geometry (verts/uvs/submeshes/textures) reproduced; normals are Blender-recomputed on real export
    for a, b in zip(_groups(), rebuilt):
        assert a["verts"] == b["verts"]
        assert a["uvs"] == b["uvs"]
        assert [(s["texture"], s["tris"]) for s in a["submeshes"]] == \
            [(s["texture"], s["tris"]) for s in b["submeshes"]]
    assert battle_fbx.validate_groups(rebuilt) == []


def test_export_emits_blender_normals():
    g = _groups()[0]
    md = bridge.group_to_blender_meshdata(g)
    normals_bl = [[0, 0, 1]] * len(md["verts"])           # Blender up = Unity up after the map
    out = bridge.blender_meshdata_to_group(
        md["name"], md["verts"], md["faces"], md["face_material"], md["materials"], md["uvs"],
        normals=normals_bl)
    assert out["normals"] is not None and len(out["normals"]) == len(g["verts"])
    text, _ = battle_fbx.emit_fbx([out])
    assert "LayerElementNormal" in text                   # normals survive to the FBX
