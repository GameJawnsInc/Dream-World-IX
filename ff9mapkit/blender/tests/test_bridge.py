"""Offline validation of the bpy-free Blender<->FF9 bridge (NO bpy import).

The gate for Tier 2: the camera mapping must be correct before any Blender code matters.
  * round-trip: every real FF9 camera -> Blender params -> back to FF9 reproduces r/t (<=1).
  * semantic anchor: a Blender camera posed (from first principles, pure Blender look-at) to
    look down at the origin yields an FF9 camera that (a) sits where expected, (b) has the
    expected downward pitch, (c) projects the floor right-side-up and roughly centered.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# make the add-on package importable (it's bpy-guarded, so import is safe without Blender)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # .../ff9mapkit/blender
from ff9mapkit_blender import bridge                            # noqa: E402
from ff9mapkit_blender.vendor import bgi as B                   # noqa: E402
from ff9mapkit_blender.vendor import cam as C                   # noqa: E402

# the 6 real cameras (same dataset as ff9mapkit/tests/test_cameras.py)
CAMS = [
    ("GRGR", 497, (0, 0), (0, -248, 5018), (384, 448), 543, (160, 224, 112, 336),
     [1, 0, 0, 0, 0.6047363, -0.7109375, 0, 0.7617188, 0.6477051]),
    ("TSHP0", 529, (0, -63), (-27, 831, 4006), (480, 320), -102, (160, 320, 112, 208),
     [1, 0, 0, 0, 0.8251953, -0.4360352, 0, 0.4672852, 0.8840332]),
    ("TSHP1_90y", 421, (0, 51), (31, 151, 867), (320, 240), 4, (160, 160, 112, 128),
     [0.006103516, 0, 1, 0.04003906, 0.932373, -0.0002441406, -0.9990234, 0.04296875, 0.006103516]),
    ("BSHP0", 385, (80, 0), (-313, 72, 2842), (384, 272), -105, (160, 224, 112, 160),
     [0.9995117, 0, -0.02758789, -0.01245117, 0.814209, -0.4562988, 0.02392578, 0.4890137, 0.8718262]),
    ("GZML0", 606, (0, 0), (582, -358, 6999), (576, 432), -51, (160, 416, 112, 320),
     [0.9121094, 0, 0.4099121, 0.1166992, 0.8886719, -0.2600098, -0.3903809, 0.3054199, 0.8686523]),
    ("TRNO0_inv", 1166, (-81, -70), (3962, 4378, -4190), (464, 448), -1272, (160, 304, 112, 336),
     [-0.9829102, 0, 0.1843262, 0.02612305, 0.9226074, 0.1391602, -0.1821289, 0.1518555, -0.9714355]),
]

import pytest


def _make(rec):
    name, proj, off, t, rng, dz, vp, om = rec
    c = C.Cam()
    c.proj = proj
    c.centerOffset = list(off)
    c.t = list(t)
    c.range = list(rng)
    c.depthOffset = dz
    c.viewport = list(vp)
    c.r = [[int(round(om[i * 3 + j] * C.ROT)) for j in range(3)] for i in range(3)]
    return name, c


@pytest.mark.parametrize("rec", CAMS, ids=[c[0] for c in CAMS])
def test_camera_roundtrip(rec):
    name, orig = _make(rec)
    k = C.decompose(orig)["k"]                       # use the camera's own k so r compares exactly
    b = bridge.ff9_cam_to_blender(orig)
    back = bridge.blender_cam_to_ff9(
        b["location"], b["rotation"], b["lens"], sensor_width=b["sensor_width"],
        range_wh=tuple(orig.range), depth_offset=orig.depthOffset,
        viewport=tuple(orig.viewport), center_offset=tuple(orig.centerOffset), k=k)
    dr = max(abs(back.r[i][j] - orig.r[i][j]) for i in range(3) for j in range(3))
    dt = max(abs(back.t[i] - orig.t[i]) for i in range(3))
    assert dr <= 1, f"{name}: r drift {dr}"
    assert dt <= 1, f"{name}: t drift {dt}"


def test_semantic_lookdown():
    # Pose a Blender camera (Z-up world) above & behind the origin, looking at it ~45 deg down.
    eye = (0.0, -3000.0, 3000.0)
    R_bl = bridge.look_at_blender(eye, (0.0, 0.0, 0.0))
    H = 497
    lens = bridge.H_to_lens(H, bridge.DEFAULT_SENSOR, 384)
    c = bridge.blender_cam_to_ff9(eye, R_bl, lens, range_wh=(384, 448))
    d = C.decompose(c)
    # (a) camera position maps as expected: FF9 C = M_FB * eye = (0, 3000, -3000)
    assert abs(d["C"][0] - 0) < 1 and abs(d["C"][1] - 3000) < 1 and abs(d["C"][2] + 3000) < 1
    # (b) ~45 deg downward pitch
    assert abs(C.pitch_deg(c) - 45.0) < 2.0
    # (c) floor projects right-side-up + centered. Use the RAW GTE projection (no field offset):
    #     origin's raw x is 0 (centered); a point toward +z (back) sits higher on screen than one
    #     toward -z (front) -> not mirrored.
    sx0, _, _ = C.project((0, 0, 0), c)
    assert abs(sx0) < 1e-6                     # origin horizontally centered (raw)
    # in the painted canvas (top-left origin, Y down) the floor's back edge sits HIGHER (smaller
    # canvasY) than its front edge — the right-side-up relationship every real FF9 floor camera has.
    cy_back = C.to_canvas((0, 0, 1500), c)[1]
    cy_front = C.to_canvas((0, 0, -1500), c)[1]
    assert cy_back < cy_front
    assert 0 < cy_back < 448 and 0 < cy_front < 448   # both land on the canvas


def test_pitch_warning_range():
    assert C.pitch_warning(30) is None
    assert C.pitch_warning(48) is None
    assert C.pitch_warning(65) is not None


# --- Phase 1: viewport guide geometry + layer TOML (bpy-free) ---------------------------
def test_ff9_blender_vert_roundtrip():
    pts = [(0, 0, 0), (123, 0, -456), (-800, 0, 1200), (50, 0, 50)]
    back = bridge.blender_verts_to_ff9(bridge.ff9_verts_to_blender(pts))
    for a, b in zip(pts, back):
        assert max(abs(a[i] - b[i]) for i in range(3)) < 1e-9


def test_floor_guide_geometry():
    _, c = _make(CAMS[0])                       # GRGR
    g = bridge.floor_guide_geometry(c, 130.0, 420.0, nx=6, nz=6)
    assert len(g["grid_verts"]) == 7 * 7        # (nx+1)*(nz+1)
    assert len(g["grid_faces"]) == 6 * 6
    # floor grid lies on the Blender floor plane (z=0, since FF9 y=0 -> Blender z)
    assert all(abs(v[2]) < 1e-6 for v in g["grid_verts"])
    # every quad indexes 4 distinct, in-range verts
    n = len(g["grid_verts"])
    for f in g["grid_faces"]:
        assert len(set(f)) == 4 and all(0 <= i < n for i in f)
    # the 'back' marker maps to the same Blender point as projecting FF9 (0,0,zb)
    labels = dict(g["markers"])
    assert "back" in labels and "front" in labels and "origin" in labels
    assert max(abs(labels["origin"][i]) for i in range(3)) < 1e-6
    # back marker == ff9 (0,0,zb) -> blender
    exp = bridge.ff9_verts_to_blender([(0, 0, g["zb"])])[0]
    assert max(abs(labels["back"][i] - exp[i]) for i in range(3)) < 1e-6


def test_layers_to_toml():
    t = bridge.layers_to_toml([{"image": "back.png", "z": 4000}, ("floor.png", 3000)])
    assert '[[layers]]\nimage = "back.png"\nz = 4000' in t
    assert '[[layers]]\nimage = "floor.png"\nz = 3000' in t
    # parseable as TOML
    import tomllib
    d = tomllib.loads(t)
    assert [l["image"] for l in d["layers"]] == ["back.png", "floor.png"]
    assert [l["z"] for l in d["layers"]] == [4000, 3000]


def test_floor_quad_blender():
    _, c = _make(CAMS[0])
    q = bridge.floor_quad_blender(c, 130.0, 420.0)
    assert len(q) == 4
    assert all(abs(v[2]) < 1e-6 for v in q)     # flat on the Blender floor (z=0)
    # corners match the guide frame's BL/BR/FR/FL
    g = bridge.floor_guide_geometry(c, 130.0, 420.0)
    fx, zb, zf = g["half_width"], g["zb"], g["zf"]
    exp = bridge.ff9_verts_to_blender([(-fx, 0, zb), (fx, 0, zb), (fx, 0, zf), (-fx, 0, zf)])
    for a, b in zip(q, exp):
        assert max(abs(a[i] - b[i]) for i in range(3)) < 1e-6


def test_paint_template_lines():
    _, c = _make(CAMS[0])
    t = bridge.paint_template_lines(c, 130.0, 420.0, scale=4, nx=8, nz=8)
    assert t["size"] == (384 * 4, 448 * 4)
    assert len(t["grid"]) == (8 + 1) + (8 + 1)      # longitudinal + latitudinal
    assert len(t["outline"]) == 4                   # quad
    # outline back edge y < front edge y (back is higher on the canvas)
    (_, by0), (_, by1) = t["outline"][0]            # back edge
    (_, fy0), _ = t["outline"][2]                   # front edge start
    assert max(by0, by1) < fy0


def test_bgi_walkmesh_to_blender_roundtrip():
    """Import FF9 Field: a real field's .bgi -> editable Blender mesh -> back to FF9 = same verts."""
    from ff9mapkit_blender.vendor import bgi
    data = bgi.quad([(-100, 50), (100, 50), (100, -50), (-100, -50)]).to_bytes()
    wm = bgi.BgiWalkmesh.from_bytes(data)
    expected = [(v.x, v.y, v.z) for v in wm.verts]
    bl_verts, faces = bridge.bgi_walkmesh_to_blender(data)
    assert len(bl_verts) == len(expected) == 4
    assert len(faces) == len(wm.tris) == 2
    back = bridge.blender_verts_to_ff9(bl_verts)
    for a, b in zip(back, expected):
        assert all(abs(x - y) < 1e-6 for x, y in zip(a, b))


# --- Export Field: multi-floor walkmesh (material slot -> floor) --------------------------
_BL_VERTS = [(0, 0, 0), (100, 0, 0), (100, 100, 0), (0, 100, 0),     # Blender (z-up) ground quad
             (0, 200, 50), (100, 200, 50), (50, 300, 50)]            # a raised ledge
_BL_FACES = [(0, 1, 2), (0, 2, 3), (4, 5, 6)]
_FLOOR_IDS = [0, 0, 1]                                               # 2 material slots = 2 floors


def test_mesh_to_ff9_obj_emits_floor_groups():
    """Per-face floor_ids -> one `o floor_N` group each; load_obj_floors reconstructs the partition."""
    import os
    import tempfile
    text = bridge.mesh_to_ff9_obj(_BL_VERTS, _BL_FACES, _FLOOR_IDS)
    assert text.count("\no floor_") == 2
    fd, path = tempfile.mkstemp(suffix=".obj")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
        _verts, faces, floor_ids = B.load_obj_floors(path)
        assert len(faces) == 3
        assert floor_ids == [0, 0, 1]
    finally:
        os.unlink(path)
    # a single floor (or None) writes a flat list, no `o` groups
    assert "o floor_" not in bridge.mesh_to_ff9_obj(_BL_VERTS, _BL_FACES, [0, 0, 0])
    assert "o floor_" not in bridge.mesh_to_ff9_obj(_BL_VERTS, _BL_FACES, None)


def test_mesh_to_bgi_bytes_multifloor():
    """Distinct floor_ids -> a world-frame multi-floor .bgi (org=0); single floor -> flat builder."""
    wm = B.BgiWalkmesh.from_bytes(bridge.mesh_to_bgi_bytes(_BL_VERTS, _BL_FACES, _FLOOR_IDS))
    assert len(wm.floors) == 2
    assert [t.floor_ndx for t in wm.tris] == [0, 0, 1]
    assert (wm.orgPos.x, wm.orgPos.y, wm.orgPos.z) == (0, 0, 0)
    flat = B.BgiWalkmesh.from_bytes(bridge.mesh_to_bgi_bytes(_BL_VERTS, _BL_FACES, None))
    assert len(flat.floors) == 1
