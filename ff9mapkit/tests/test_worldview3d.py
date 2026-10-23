"""Fences for the World tab's 3D view (:mod:`ff9mapkit.workspace.worldview3d`, editor rung A0).

``world/render.py`` is the oracle. The pure half (the projection, the packing, the texture prep, the orbit camera)
runs headless here. The GPU half needs a real OpenGL context, which the offscreen platform these tests run on does
not have, so it runs in a child process on the native platform (``_worldview3d_native.py``) and is judged here:
blob 0 and coverage 0 against the software raster, AND each break-it mutation (texture V not flipped, the cull off,
a batch dropped) must be caught -- a comparison that cannot fail proves nothing. The child skips only when it
reports that no GL context exists. Nothing here reads the developer's install except the one bench test, which
says so and skips without one.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("PySide6", reason="GUI extra not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")

from PySide6.QtWidgets import QApplication                                      # noqa: E402

from ff9mapkit.editor.theme import pick_palette                                 # noqa: E402
from ff9mapkit.world import render as R                                         # noqa: E402
from ff9mapkit.workspace import worldview3d as V                                # noqa: E402

DRIVER = Path(__file__).with_name("_worldview3d_native.py")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


# ------------------------------------------------------------------ the projection
@pytest.mark.parametrize("view", [
    dict(kind="persp", eye=(348.0, 9.0, -524.0), at=(381.0, 2.0, -513.0), fov=50.0, reach=90.0),
    dict(kind="persp", eye=(1200.0, 300.0, -100.0), at=(768.0, 0.0, -640.0), fov=35.0),
    dict(kind="ortho", x0=362.0, x1=398.0, z0=-528.0, z1=-498.0),
], ids=["bench-sea_w", "high-overview", "bench-top"])
@pytest.mark.parametrize("res", [(960, 640), (321, 207)], ids=["even", "odd"])
def test_clip_matrix_lands_every_vertex_where_render_projects_it(view, res):
    """One projection: the GPU matrix, divided through, puts each vertex on render.project's pixel."""
    rng = np.random.default_rng(3)
    at = np.asarray(view.get("at", (380.0, 0.0, -513.0)))
    pts = at + rng.uniform(-40, 40, (500, 3)) * [1, 0.3, 1]
    sx, sy = V.window_xy(view, res, pts)
    rx, ry, _ = R.project(view, pts, res)
    assert np.abs(sx - rx).max() < 1e-6 and np.abs(sy - ry).max() < 1e-6


def test_orbit_camera_is_a_render_camera_looking_at_its_target():
    cam = V.OrbitCamera(target=(500.0, 4.0, -300.0), yaw=40.0, pitch=30.0, dist=120.0)
    v = cam.view()
    sx, sy, dep = R.project(v, np.array([cam.target]), (800, 600))
    assert abs(sx[0] - 400) < 1e-6 and abs(sy[0] - 300) < 1e-6 and dep[0] == pytest.approx(120.0)
    cam.orbit(10, 1000)                                      # pitch clamps; never under or over the poles
    assert cam.pitch == V.PITCH_MAX
    cam.zoom(-1000)
    assert cam.dist == V.DIST_MAX


# ------------------------------------------------------------------ the scene
def _tri(part, y=0.0, z=-10.0):
    verts = np.array([[0.0, y, z], [4.0, y, z], [2.0, y, z - 4.0]])
    return (part, verts, np.zeros((3, 2)), np.array([[0, 1, 2]]))


def test_pack_keeps_the_oracles_batch_order_across_parts():
    """Depth ties resolve first-drawn-wins in the oracle; the GPU must draw batches in the same order."""
    p = V.pack([_tri("Terrain"), _tri("Sea4"), _tri("Terrain", z=-20.0)])
    assert p.draws == [("Terrain", 0, 3), ("Sea4", 0, 3), ("Terrain", 3, 3)]
    assert p.arrays["Terrain"].shape == (6, 5) and p.arrays["Terrain"].dtype == np.float32
    assert p.tris == 3


def test_pack_applies_the_oracles_near_and_reach_rules_for_a_still():
    view = dict(kind="persp", eye=(2.0, 5.0, 0.0), at=(2.0, 0.0, -12.0), fov=50.0, reach=10.0)
    behind = ("Terrain", np.array([[0.0, 0.0, 1.0], [4.0, 0.0, 1.0], [2.0, 0.0, -4.0]]),
              np.zeros((3, 2)), np.array([[0, 1, 2]]))       # one vertex behind the eye
    far = _tri("Terrain", z=-40.0)                           # centroid ~29u from `at`, reach 10
    near = _tri("Terrain")
    kept = V.pack([behind, far, near], view)
    assert kept.tris == 1 and V.pack([behind, far, near]).tris == 3
    # ...and the oracle draws exactly the tri the pack kept (its own ntri count, read off a pure raster)
    site = R.RenderSite(cells=(), res=(64, 48), game=".")
    img = R.raster(view, [near], "n", site=site, tex_lookup=lambda p: None, verbose=False)
    img_all = R.raster(view, [behind, far, near], "a", site=site, tex_lookup=lambda p: None, verbose=False)
    assert (img == img_all).all()


def test_texture_prep_draws_a_blank_texel_white_and_everything_opaque():
    t = np.zeros((2, 2, 4), dtype=np.uint8)
    t[0, 0] = (10, 20, 30, 0)                                # alpha 0: the blank-tile law says white
    t[1, 1] = (40, 50, 60, 128)
    out = V.texture_rgba(t)
    assert tuple(out[0, 0]) == (255, 255, 255, 255) and tuple(out[1, 1]) == (40, 50, 60, 255)
    assert V.texture_rgba(None) is None
    assert t[0, 0, 0] == 10                                  # the renderer's cached array is never mutated


def test_compare_reads_lines_and_dots_as_precision_and_an_area_as_a_defect():
    a = np.zeros((20, 20, 3), dtype=np.uint8)
    b = a.copy()
    b[5, :] = 9                                              # a 1-px line (an edge-ownership tie)
    b[12, 3] = 9                                             # a dot (a texel-border pick)
    c = V.compare(a, b)
    assert c["differ"] == 21 and c["blob"] == 0
    b[14:18, 14:18] = 9                                      # a 4x4 area: a wrong texture or a lost tri
    assert V.compare(a, b)["blob"] == 4
    s = a.copy()
    s[0:2, 0:2] = R.SKY
    assert V.compare(a, s)["coverage"] == 4


# ------------------------------------------------------------------ no GL, no blank
def test_panel_says_it_needs_opengl_offscreen_and_builds_no_gl_widget(app):
    pal = pick_palette("mist")
    panel = V.WorldView3DPanel(pal)
    assert V.gl_available() is False                         # the platform these tests run on
    site = R.RenderSite(cells=((0, 0),), game="X:/nonexistent")
    assert panel.load(site, sync=True) is False
    assert "needs OpenGL" in panel.status_text()
    assert panel.view is None                                # never a GL view that could only paint its clear colour


def test_world_tab_builds_no_3d_page_until_asked_and_the_toggle_names_its_target(app, tmp_path):
    from ff9mapkit.workspace.worlddoc import WorldDoc
    doc = WorldDoc(pick_palette("mist"), game_path_fn=lambda: tmp_path)
    assert doc._view3d is None and doc.view3d_btn.text() == "3D view"
    doc._census, doc._game = SimpleNamespace(root=tmp_path / "FF9CustomMap-world"), tmp_path
    doc.set_view_mode("3d", sync=True)
    assert doc._view3d is not None and doc._views.currentWidget() is doc._view3d
    assert doc.view3d_btn.text() == "Chart view" and doc._legend_host.isHidden()
    assert "needs OpenGL" in doc._view3d.status_text()      # offscreen: the words, not a blank
    doc.view3d_btn.click()                                   # the real click path, not the seam
    assert doc._views.currentWidget() is doc.canvas and doc.view3d_btn.text() == "3D view"
    assert not doc._legend_host.isHidden()


# ------------------------------------------------------------------ the GPU against the oracle (native child)
def _native(mode):
    env = {k: v for k, v in os.environ.items() if k != "QT_QPA_PLATFORM"}
    r = subprocess.run([sys.executable, str(DRIVER), mode], capture_output=True, text=True, timeout=600,
                       env=env, cwd=str(DRIVER.parents[1]))
    assert r.returncode == 0, r.stderr[-3000:]
    out = json.loads(r.stdout.strip().splitlines()[-1])
    if not out["gl"]:
        pytest.skip(f"no OpenGL context on the native platform ({out.get('platform')})")
    return out


def test_gpu_still_matches_the_software_renderer_and_catches_each_mutation():
    out = _native("hermetic")
    for vn, c in out["views"].items():
        assert c["blob"] == 0 and c["coverage"] == 0, (vn, c)
        assert c["differ"] < 0.01 * c["pixels"], (vn, c)     # the two precision classes stay a sliver
        assert c["sky_frac"] < 0.95, (vn, c)                 # not vacuous: the scene fills the frame
    for mn, worst in out["mutations"].items():
        assert worst["blob"] > 100, (mn, worst)              # every break-it is an AREA the measure sees


def _has_install() -> bool:
    try:
        from ff9mapkit import config
        return Path(config.find_game_path(None)).is_dir()
    except Exception:                                        # noqa: BLE001
        return False


@pytest.mark.skipif(not _has_install(), reason="reads the install's V-shore bench (disc 9)")
def test_gpu_matches_the_committed_bench_cameras():
    """A0's acceptance on real blocks: the six committed V-shore cameras (render.BENCH_VIEWS), the stills the
    renderer was promoted against. Measured 2026-10-23: blob 0, coverage <= 2, differ 0.11-0.51%."""
    out = _native("bench")
    assert out["tris"] > 5000, out                           # the bench's blocks were really read
    for vn, c in out["views"].items():
        assert c["blob"] == 0 and c["coverage"] <= 4, (vn, c)
        assert c["differ"] < 0.01 * c["pixels"], (vn, c)
