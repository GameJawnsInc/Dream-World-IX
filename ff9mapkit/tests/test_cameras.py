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

# fbg_n11_ldbm_map158_lb_plz_0 (field 559) camera 0 -- the donor that exposed the to_canvas
# centerOffset bug (WATERWORKS bench 30420): the largest GTE centerOffset seen so far ([26, 400]
# on a 512x400 canvas), so the offset-less map put every canvas point a whole screen off.
MAP158 = ("LDBM_PLZ", 960, (26, 400), (79, -4643, 12147), (512, 400), -989, (160, 352, 112, 288),
          [1, 0.005371094, -0.001220703, -0.002929688, 0.3371582, -0.8703613,
           -0.004638672, 0.9326172, 0.361084])


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


@pytest.mark.parametrize("rec", CAMS + [MAP158], ids=[c[0] for c in CAMS] + [MAP158[0]])
def test_to_canvas_matches_engine_actor_frame(rec):
    """to_canvas must equal the ENGINE actor position (project_screen, which uses the real
    projectionOffset incl. centerOffset) mapped into the canvas frame -- the definitional identity
    canvas = (engine.x + HFW, HFH - engine.y). Holds for offset-0 AND real offset cameras."""
    _, cam = _make(rec)
    for P in PTS:
        ex, ey, _ = C.project_screen(P, cam)
        cx, cy = C.to_canvas(P, cam)
        assert abs(cx - (ex + C.HALF_FIELD_W)) < 1e-9
        assert abs(cy - (C.HALF_FIELD_H - ey)) < 1e-9


def test_to_canvas_offset_zero_reduces_to_historical_form():
    # novel (kit-authored) cameras always have centerOffset [0,0]: the map must stay byte-identical
    # to the historical offset-less form there, so nothing downstream of `ff9mapkit new` moves.
    _, grgr = _make(CAMS[0])
    assert grgr.centerOffset == [0, 0]
    for P in PTS:
        px, py, _ = C.project(P, grgr)
        assert C.to_canvas(P, grgr) == (px + grgr.range[0] / 2.0, grgr.range[1] / 2.0 - py)


def test_map158_center_offset_regression():
    """The proven WATERWORKS-bench case: the map158 spawn (-3247, -134, -2344) must land at canvas
    ~(16.5, 386.2) -- ON the 512x400 canvas -- not at the offset-less (-9.5, -13.8), which is OFF it.
    Also: solve_z_for_canvasY must invert the corrected map on this real offset camera."""
    _, cam = _make(MAP158)
    P = (-3247, -134.0, -2344)
    cx, cy = C.to_canvas(P, cam)
    assert abs(cx - 16.47) < 0.05 and abs(cy - 386.18) < 0.05
    assert 0 <= cx <= cam.range[0] and 0 <= cy <= cam.range[1]
    # the offset-less form is off-canvas -- the bug this test pins
    px, py, _ = C.project(P, cam)
    ox, oy = px + cam.range[0] / 2.0, cam.range[1] / 2.0 - py
    assert ox < 0 and oy < 0
    # the inverse stays exact through the offset fold
    for z in (-2344, -1000, 500):
        cyz = C.to_canvas((-3247, -134.0, z), cam)[1]
        assert abs(C.solve_z_for_canvasY(cam, cyz, x=-3247, y=-134.0) - z) < 0.5


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


def test_template_layers_compose_to_single():
    """The per-layer split (grid/outline/height) overlaid in order must reproduce the SINGLE combined
    template byte-for-byte -- so opting into multi-PNG never changes what gets drawn."""
    from ff9mapkit.scene import guide as G
    _, cam = _make(CAMS[0])
    fr = G.frame_floor(cam, back_canvas_y=160.0, front_canvas_y=400.0)
    S = 4
    cw, ch = G._canvas_wh(cam)
    W, H = cw * S, ch * S
    wall_h = abs(fr.zb - fr.zf)
    combined = bytearray(W * H * 4)                       # what render_paint_template draws
    for layer, _o, _d in G.PAINT_TEMPLATE_LAYERS:
        G._draw_template_layer(combined, W, H, layer, cam, fr, S, 8, 8, wall_h)
    overlay = bytearray(W * H * 4)                        # per-layer buffers composited in order
    for layer, _o, _d in G.PAINT_TEMPLATE_LAYERS:
        buf = bytearray(W * H * 4)
        G._draw_template_layer(buf, W, H, layer, cam, fr, S, 8, 8, wall_h)
        for i in range(3, len(buf), 4):
            if buf[i]:                                    # non-transparent pixel overwrites (same as combined)
                overlay[i - 3:i + 1] = buf[i - 3:i + 1]
    assert overlay == combined


def test_render_paint_template_layers_writes_manifest(tmp_path):
    import json
    import os
    from ff9mapkit.scene import guide as G
    _, cam = _make(CAMS[0])
    fr = G.frame_floor(cam, back_canvas_y=160.0, front_canvas_y=400.0)
    files = G.render_paint_template_layers(cam, fr, str(tmp_path), basename="pt")
    assert [os.path.basename(f) for f in files] == \
        ["pt_grid.png", "pt_outline.png", "pt_height.png", "pt.manifest.json"]
    for f in files[:3]:                                   # each layer is a real, non-empty PNG
        assert os.path.getsize(f) > 0
        with open(f, "rb") as fh:
            assert fh.read(8) == b"\x89PNG\r\n\x1a\n"
    man = json.loads((tmp_path / "pt.manifest.json").read_text())
    assert man["version"] == 1 and man["scale"] == 4
    assert man["canvas_size"] == [384 * 4, 448 * 4]
    assert [L["type"] for L in man["layers"]] == ["grid", "outline", "height"]
    assert man["layers"][0]["opacity"] == 0.35 and man["layers"][1]["type"] == "outline"


def test_frame_floor_shallow_pitch_raises_gracefully():
    """A row that is GENUINELY past the horizon still refuses, with the horizon named.

    This test used to assert pitch 8 refused rows 205/432 -- it encoded the pole-spanning-bisection
    bug (that camera's horizon is Y~158, so BOTH rows are reachable). A near-level camera is the
    real refusal: at pitch 2 the horizon sits at Y~208, just BELOW the back row 205."""
    from ff9mapkit.scene import guide as G
    c = G.make_camera(2, 4500, fov_x_deg=42)
    assert C.horizon_canvas_y(c) > 205                      # the back row really is past it
    with pytest.raises(ValueError, match="horizon"):
        G.frame_floor(c, back_canvas_y=205, front_canvas_y=432)
    assert isinstance(C.horizon_canvas_y(c), float)
    # a steep enough camera frames fine
    c2 = G.make_camera(40, 4500, fov_x_deg=42)
    fr = G.frame_floor(c2, back_canvas_y=205, front_canvas_y=432)
    assert fr.zb != fr.zf


def test_solve_z_low_pitch_takes_the_front_branch():
    """THE REGRESSION: the row solver must not lose a row to the projection pole.

    `project` divides by |res.z|, so past the pole at res.z = 0 the same canvas row is re-produced
    MIRRORED by points behind the camera. The old bisection bracketed [-30000, +30000] -- a window
    that SPANS that pole -- so its two-endpoint sign test came back same-sign and returned None for
    rows with a perfectly good front-branch root. Measured at pitch 15 / distance 3000: rows 365,
    420 and 440 all returned None. Their true roots re-project to the row exactly."""
    from ff9mapkit.scene import guide as G
    c = G.make_camera(15.0, 3000.0, fov_x_deg=42.2)
    for row, want in ((365, -1649.6), (420, -1899.6), (440, -1970.4)):
        z = C.solve_z_for_canvasY(c, row)
        assert z is not None, f"row {row} lost (the pole-spanning-bracket bug)"
        assert abs(z - want) < 1.0, f"row {row}: z={z}"
        assert abs(C.to_canvas((0, 0, z), c)[1] - row) < 1e-6      # it really lands on that row
        assert C.project((0, 0, z), c)[2] > 0                      # ...and IN FRONT of the camera


@pytest.mark.parametrize("pitch", [15.0, 20.0])
@pytest.mark.parametrize("dist", [1500.0, 3000.0, 4500.0])
def test_frame_floor_low_pitch_frames_on_the_requested_rows(pitch, dist):
    """frame_floor must SUCCEED at pitch 15/20 (it raised at every distance before) and the quad it
    hands back must land on the rows that were asked for -- the whole point of the function."""
    from ff9mapkit.scene import guide as G
    c = G.make_camera(pitch, dist, fov_x_deg=42.2)
    fr = G.frame_floor(c, back_canvas_y=205, front_canvas_y=432)
    assert fr.zb > fr.zf and fr.half_width > 0                     # back edge is the far one
    for P in fr.corners_world:
        assert C.project(P, c)[2] > 0, f"{P} is behind the camera"
    rows = [C.to_canvas(P, c)[1] for P in fr.corners_world]         # BL, BR, FR, FL
    assert max(abs(r - 205) for r in rows[:2]) < 1.0                # rounded to int world z
    assert max(abs(r - 432) for r in rows[2:]) < 1.0
    # ...and the walkmesh corners the caller ships are those same world corners
    assert G.walkmesh_corners(fr) == [(p[0], p[2]) for p in fr.corners_world]


@pytest.mark.parametrize("rec", CAMS + [MAP158], ids=[c[0] for c in CAMS] + [MAP158[0]])
def test_solve_z_exact_on_every_real_camera_front_branch(rec):
    """The inverse must round-trip to_canvas for EVERY world z genuinely in front of a real donor
    camera. The old bisection lost 112 of these 886 samples -- ALL 32 on TRNO0_inv, whose
    r[2][2] < 0 puts its entire front branch at negative z, i.e. on the far side of its pole."""
    _, cam = _make(rec)
    n = 0
    for zi in range(-8000, 8001, 100):
        z = float(zi)
        if C.project((0, 0, z), cam)[2] <= 500:        # skip the near-degenerate depths
            continue
        n += 1
        got = C.solve_z_for_canvasY(cam, C.to_canvas((0, 0, z), cam)[1])
        assert got is not None and abs(got - z) < 1e-6, f"z={z} -> {got}"
    assert n >= 30, f"only {n} in-front samples -- the sweep stopped testing anything"


@pytest.mark.parametrize("rec", CAMS + [MAP158], ids=[c[0] for c in CAMS] + [MAP158[0]])
def test_horizon_canvas_y_is_the_front_branch_asymptote(rec):
    """horizon_canvas_y must be the row a RECEDING FRONT-branch floor CONVERGES to, and the closed
    form is that limit exactly. The retired z = +1e7 probe was wrong two ways: it rode the same
    |res.z| mirror (on TRNO0_inv, whose +z is BEHIND the camera, that probe is past the pole and
    reported row 321 for a true horizon of -13 -- a 334-row lie under the workspace's "no floor
    above" line and imagefield's row cap), and 1e7 is not infinity anyway: the residual is O(1/z),
    which is still 6.5 rows out on LDBM_PLZ."""
    _, cam = _make(rec)
    hy = C.horizon_canvas_y(cam)
    sign = 1.0 if C._row_coeffs(cam)[3] > 0 else -1.0           # recede along the FRONT branch
    assert C.project((0, 0, sign * 1.0e7), cam)[2] > 0
    err = [abs(C.to_canvas((0, 0, sign * d), cam)[1] - hy) for d in (1.0e7, 1.0e9, 1.0e11)]
    assert err[2] < 0.01, err                                   # converges TO the closed form
    assert err[0] > 50 * err[2], err                            # ...at the O(1/z) rate, so 1e7 is not it
    assert C.canvas_row_z(cam, hy)[0] is None                   # the horizon row itself has no z
    assert "horizon" in C.canvas_row_z(cam, hy)[1]


@pytest.mark.parametrize("rec", CAMS + [MAP158], ids=[c[0] for c in CAMS] + [MAP158[0]])
def test_canvas_row_z_reason_names_the_truly_reachable_side(rec):
    """The refusal message is load-bearing (guide.frame_floor quotes it), so fence that it is TRUE:
    the side of the horizon it names must be the side that actually solves. Deriving that from
    sign(G) alone -- the obvious guess -- is wrong on TRNO0_inv and on any det < 0 camera; it takes
    sign(G * (E*B - A*G)), because E + G*z = H*det/den identically."""
    _, cam = _make(rec)
    hy = C.horizon_canvas_y(cam)
    A, B, E, G = C._row_coeffs(cam)
    side = "larger" if G * (E * B - A * G) > 0 else "smaller"
    for row in range(-600, 1200, 3):
        if abs(row - hy) <= 1.0:                               # skip the knife edge
            continue
        solved = C.solve_z_for_canvasY(cam, float(row), zlo=None, zhi=None) is not None
        assert solved == ((row > hy) if side == "larger" else (row < hy)), \
            f"row {row} vs horizon {hy:.1f}: reachable={solved}, message claims {side}-Y"
    off = hy + (400.0 if side == "smaller" else -400.0)         # a row on the UNreachable side
    why = C.canvas_row_z(cam, off)[1]
    assert why and f"{side}-Y" in why, why


def test_canvas_row_z_refuses_a_camera_with_no_z_dependence():
    """A yaw-90 camera looks along x, so world z slides ACROSS the screen and never changes the row:
    no row determines a z. The old bisection's `if fa == 0: return a` handed back the bracket end
    (-30000) for the one row that matched -- a silent fabrication."""
    from ff9mapkit.scene import guide as G
    c = G.make_camera(20.0, 3000.0, fov_x_deg=42.2, yaw_deg=90.0)
    row = C.to_canvas((0, 0, -1200.0), c)[1]
    assert abs(C.to_canvas((0, 0, 2500.0), c)[1] - row) < 1e-9   # z really does not move the row
    z, why = C.canvas_row_z(c, row)
    assert z is None and "does not move" in why


def test_solve_z_window_bounds_the_answer():
    """zlo/zhi keep their old meaning -- a root outside the window is refused, not returned -- so the
    default +/-30000 still fences a row so near the horizon that the floor recedes past what a
    walkmesh Int16 coordinate could hold."""
    from ff9mapkit.scene import guide as G
    c = G.make_camera(15.0, 60000.0, fov_x_deg=42.2)             # absurdly distant -> huge roots
    assert C.solve_z_for_canvasY(c, 432) is None
    far = C.solve_z_for_canvasY(c, 432, zlo=None, zhi=None)
    assert far is not None and abs(far) > 30000
    assert abs(C.to_canvas((0, 0, far), c)[1] - 432) < 1e-6      # ...and it IS the right root
    assert "Int16" in C.canvas_row_z(c, 432)[1]


def test_walkmesh_int16_bound_raises_gracefully():
    from ff9mapkit.scene import bgi as B
    B.build_flat([(-800, 0, -800), (800, 0, -800), (0, 0, 800)], [(0, 1, 2)])   # ok
    with pytest.raises(ValueError, match="Int16"):
        B.build_flat([(-50000, 0, 0), (50000, 0, 0), (0, 0, 50000)], [(0, 1, 2)])


def test_parse_bgx_cameras_rejects_malformed_line():
    # a non-numeric token in a CAMERA field must not silently revert that field to the Cam
    # default (e.g. Position -> [0, 0, 0]) -- it has to surface, naming the bad line
    text = "CAMERA\nViewDistance: 1024\nPosition: 100, oops, 300\nRange: 384, 448\n"
    with pytest.raises(ValueError, match="Position"):
        C.parse_bgx_cameras_text(text)
