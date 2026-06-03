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
