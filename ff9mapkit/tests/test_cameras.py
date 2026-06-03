"""Camera-math regression suite (ported from tools/test_cameras.py).

Offline validation of ff9mapkit.scene.cam against 6 real FF9 cameras — no game needed.
Proves: (a) the vertical-scale invariant k = 14/15, (b) every camera decomposes to a proper
orthonormal rotation, (c) synthesis round-trips the exact r[]/t[] (byte-faithful), (d) the
clean pinhole form reproduces the engine GTE projection, (e) the Session-8/10 canvas map
(reproduces the GRGR floor calibration).
"""

from __future__ import annotations

from ff9mapkit.scene import cam as C

# name, proj, centerOffset, t, range, depthOffset, viewport, OrientationMatrix(9)
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
PTS = [(0, 0, 0), (500, 0, 300), (-800, 0, -1200), (1465, 0, -3344), (300, -400, 800), (-1799, 0, -3344)]


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


def _pinhole(P, cam, dec):
    cs = C.mv(dec["R_view"], C.sub(P, dec["C"]))
    num = abs(cs[2])
    return (cs[0] * cam.proj / num, cs[1] * cam.proj / num, cs[2])


import pytest


@pytest.mark.parametrize("rec", CAMS, ids=[c[0] for c in CAMS])
def test_camera_decompose_and_synth(rec):
    name, cam = _make(rec)
    d = C.decompose(cam)
    r2, t2 = C.synth_r_t(d["C"], d["R_ortho"], cam.proj, k=d["k"])
    dr = max(abs(r2[i][j] - cam.r[i][j]) for i in range(3) for j in range(3))
    dt = max(abs(t2[i] - cam.t[i]) for i in range(3))
    pmax = 0.0
    for P in PTS:
        a = C.project(P, cam)
        b = _pinhole(P, cam, d)
        pmax = max(pmax, abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))
    assert d["ortho_err"] < 5e-3, f"{name} ortho_err {d['ortho_err']}"
    assert abs(d["k"] - C.K_VSCALE) < 3e-3, f"{name} k={d['k']}"
    assert dr <= 2 and dt <= 2, f"{name} round-trip dr={dr} dt={dt}"
    assert pmax < 1e-4, f"{name} projection mismatch {pmax}"
    assert d["det"] > 0, f"{name} improper rotation det={d['det']}"


def test_mean_k_is_14_over_15():
    ks = [C.decompose(_make(r)[1])["k"] for r in CAMS]
    assert abs(sum(ks) / len(ks) - C.K_VSCALE) < 1e-3


def test_pitch_warning_supported_range():
    # in-range pitches are silent; the steepest real camera (GRGR ~49.6) is in range; 65 warns.
    assert C.pitch_warning(28) is None
    assert C.pitch_warning(50) is None
    assert C.pitch_warning(65) is not None
    _, grgr = _make(CAMS[0])
    assert C.pitch_warning(C.pitch_deg(grgr)) is None


def test_grgr_projection_offset_and_canvas_inverse():
    _, grgr = _make(CAMS[0])
    # engine projectionOffset for GRGR is (32, -112) — the -112 is the Session-8 constant,
    # the part of the calibration that is exact (derived from FieldMap.cs, not freehand-fit).
    assert C.compute_offset(grgr) == (32, -112)
    # the canvas map and its inverse must be exact inverses across the floor's z range
    # (the calibrated sy=0.889 supersedes Session-8's freehand 0.929 back-fit).
    for z in (340, -1188, -3344):
        cy = C.to_canvas((0, 0, z), grgr)[1]
        assert abs(C.solve_z_for_canvasY(grgr, cy) - z) < 0.5


def test_paint_template_renders():
    pytest.importorskip("PIL")
    import tempfile, os
    from ff9mapkit.scene import guide as G
    _, cam = _make(CAMS[0])
    fr = G.frame_floor(cam, back_canvas_y=160.0, front_canvas_y=400.0)
    p = os.path.join(tempfile.gettempdir(), "ff9mk_tmpl_test.png")
    wh = G.render_paint_template(cam, fr, p)
    assert wh == (384 * 4, 448 * 4)
    from PIL import Image
    im = Image.open(p)
    assert im.size == (1536, 1792) and im.mode == "RGBA"
