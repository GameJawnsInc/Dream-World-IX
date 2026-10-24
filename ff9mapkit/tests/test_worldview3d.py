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


def test_a_lowered_floor_reaches_the_view_and_the_status_page_leaves_the_stack(app, monkeypatch):
    """set_view_floor (a carry card's room, worlddoc.CARD_VIEW_FLOOR) lands on the view and on its host, before or
    after the view exists. And once the view is up the status page leaves the stack: a stacked layout's height for
    width is its tallest page's, and the hidden page's wrapped teach line otherwise outranks the floor (the card under
    the view was squeezed instead). No GL offscreen, so a plain widget stands in for the view."""
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QWidget

    class StubView(QWidget):
        gl_failed, picked = Signal(str), Signal(object)
        ghost_moved, ghost_dropped = Signal(float, float), Signal(float, float)
        camera_changed, party_moved = Signal(bool), Signal(float, float, float)

        def __init__(self):
            super().__init__()
            self.setMinimumSize(240, V.MIN_VIEW_H)

        def set_scene(self, *_a):
            pass

        def focus(self, *_a):
            pass

        def set_overlays(self, *_a):
            pass

        def set_ghost(self, *_a):
            pass

        def game_mode(self):
            return False
    monkeypatch.setattr(V, "WorldView3D", StubView)
    panel = V.WorldView3DPanel(pick_palette("mist"))
    assert panel._host.hasHeightForWidth()                   # anti-vacuity: the status page's wrap is there to lose
    panel.set_view_floor(48)                                 # before the view exists
    panel._finish(object(), object(), None)
    assert panel.view.minimumHeight() == 48 and panel._host.minimumHeight() == 48
    assert panel._stack.indexOf(panel._status) < 0 and panel._stack.currentWidget() is panel.view
    assert not panel._host.hasHeightForWidth()
    panel.set_view_floor(None)
    assert panel.view.minimumHeight() == V.MIN_VIEW_H and panel._host.minimumHeight() == 0
    panel._show_message("The 3D view needs OpenGL", "a later message")   # a fresh status page goes back in
    assert panel._stack.currentWidget() is panel._status and "needs OpenGL" in panel.status_text()


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
    # THE GAME'S FOG (C18): the shader fogs as world.fog's software twin does, and the fog is really there
    for vn, c in out["fog"].items():                         # (no coverage: fully fogged land IS the sky's colour;
        assert c["blob"] == 0, (vn, c)                       #  the views above hold coverage without the fog)
        assert c["differ"] < 0.01 * c["pixels"], (vn, c)
        assert 0.3 < c["fogged_frac"] < 0.95, (vn, c)        # not vacuous: the ramp grades the frame
    assert out["fog_mutation"]["blob"] > 100, out["fog_mutation"]


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


# ------------------------------------------------------------------ rung A1: the pick
GROUND = ("Terrain", np.array([[-50.0, 0.0, 50.0], [150.0, 0.0, 50.0], [-50.0, 0.0, -150.0], [150.0, 0.0, -150.0]]),
          np.zeros((4, 2)), np.array([(0, 1, 2), (1, 3, 2)]))          # up-facing: (e1 x e2).y > 0
PICK_VIEW = dict(kind="persp", eye=(20.0, 40.0, -90.0), at=(30.0, 0.0, -30.0), fov=50.0)


def _lid(y, down):
    v = np.array([[20.0, y, -40.0], [40.0, y, -40.0], [30.0, y, -20.0]])
    return ("Object", v, np.zeros((3, 2)), np.array([(0, 1, 2)] if down else [(0, 2, 1)]))


def test_a_pick_lands_on_the_point_render_projects_to_that_pixel():
    """The ray and the projection are one: a click at pixel (i, j)'s centre hits the surface point render.project
    puts on pixel (i, j) -- so the pin stands where you clicked, at any window size."""
    res = (321, 207)
    packed = V.pack([GROUND])
    rng = np.random.default_rng(9)
    for px, py in zip(rng.integers(0, res[0], 40), rng.integers(120, res[1], 40)):
        hit = V.pick(packed, PICK_VIEW, res, px + 0.5, py + 0.5)
        assert hit is not None and hit[1] == "Terrain" and abs(hit[0][1]) < 1e-9
        sx, sy, _ = R.project(PICK_VIEW, np.array([hit[0]]), res)
        assert abs(sx[0] - px) < 1e-6 and abs(sy[0] - py) < 1e-6


def test_a_pick_takes_the_nearest_face_it_can_see_and_skips_back_faces():
    res = (320, 200)
    sx, sy, _ = R.project(PICK_VIEW, np.array([[30.0, 9.0, -33.0]]), res)
    mx, my = sx[0] + 0.5, sy[0] + 0.5
    up = V.pick(V.pack([GROUND, _lid(9.0, down=False)]), PICK_VIEW, res, mx, my)
    assert up[1] == "Object" and up[0][1] == pytest.approx(9.0)
    down = V.pick(V.pack([GROUND, _lid(9.0, down=True)]), PICK_VIEW, res, mx, my)
    assert down[1] == "Terrain" and down[0][1] == pytest.approx(0.0)  # culled in the view, so not pickable
    assert V.pick(V.pack([GROUND]), PICK_VIEW, res, 160.5, 2.5) is None   # above the horizon: sky


def _mouse(w, kind, pos, button=None):
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    b = Qt.MouseButton.LeftButton if button is None else button
    t = {"press": QEvent.Type.MouseButtonPress, "move": QEvent.Type.MouseMove,
         "release": QEvent.Type.MouseButtonRelease}[kind]
    held = Qt.MouseButton.NoButton if kind == "release" else b
    ev = QMouseEvent(t, QPointF(*pos), QPointF(*pos), b if kind != "move" else Qt.MouseButton.NoButton, held,
                     Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(w, ev)


def test_a_click_picks_and_a_drag_orbits_through_real_event_delivery(app):
    """Driven through QApplication.sendEvent (the skill's law: a fence that calls the handlers directly bypasses
    Qt's delivery). A press that wanders under CLICK_SLOP is a click: it picks and the camera holds still; past it,
    the same press is a drag: the camera orbits and nothing is picked."""
    w = V.WorldView3D()
    w.resize(320, 200)
    w.packed = V.pack([GROUND])
    w.camera = V.OrbitCamera(target=(30.0, 0.0, -30.0), yaw=10.0, pitch=40.0, dist=80.0)
    got = []
    w.picked.connect(got.append)
    yaw0 = w.camera.yaw
    _mouse(w, "press", (160, 120))
    _mouse(w, "move", (162, 121))
    _mouse(w, "release", (162, 121))
    assert len(got) == 1 and got[0] is not None and got[0][1] == "Terrain"
    assert w.camera.yaw == yaw0 and w.marker == got[0][0]
    _mouse(w, "press", (160, 120))
    _mouse(w, "move", (200, 120))
    _mouse(w, "release", (200, 120))
    assert len(got) == 1 and w.camera.yaw != yaw0


def test_the_pin_stands_on_the_point():
    t = V.pin_tris((5.0, 2.0, -7.0), 10.0)
    assert t.shape == (12, 3) and t[:, 1].min() == pytest.approx(2.0) and t[:, 1].max() == pytest.approx(12.0)
    assert np.allclose(t[:, [0, 2]].mean(axis=0), (5.0, -7.0))


def test_a_pick_fills_the_strip_and_the_copy_and_teleport_buttons_follow_it(app, tmp_path, monkeypatch):
    from ff9mapkit.world import pointinfo as PI
    from ff9mapkit.workspace.worlddoc import WorldDoc
    sent = []
    doc = WorldDoc(pick_palette("mist"), game_path_fn=lambda: tmp_path, on_teleport=lambda x, z: sent.append((x, z)))
    doc._census, doc._game = SimpleNamespace(root=tmp_path / "FF9CustomMap-world"), tmp_path
    doc.set_view_mode("3d", sync=True)
    doc._view3d.site = R.RenderSite(cells=(), game=tmp_path, mod_root=tmp_path / "FF9CustomMap-world")
    seen = []

    def fake(site, wx, wz, **_k):
        seen.append((wx, wz))
        return {"world": (wx, wz), "block": (1, 1), "cell": (3, 2), "local": (36.5, -6.25),
                "ground": {"modelled": True, "note": "", "y": 5.0, "part": "Terrain", "idall": 0, "topograph": 0,
                           "area": 14, "event": 0, "walkable": True, "canopy": False, "stand_y": 5.0,
                           "sheets": [(5.0, "Terrain", 0)], "stacked": False, "shadowed": False},
                "owners": {"shown": "FF9CustomMap-world", "in_stack": True, "parts": {"Terrain": "stock"},
                           "hidden": []}, "ledger": None, "landmark": {"name": "Dali", "dist": 8.0}}
    monkeypatch.setattr(PI, "point_info", fake)
    doc._on_pick(((100.5, 5.0, -70.25), "Terrain"), sync=True)
    assert seen == [(100.5, -70.25)]
    assert doc.sel_title.text() == "Point x 100.50, z -70.25" and doc.sel_chip.text() == "walkable"
    assert "block 1,1 · cell 3,2" in doc.sel_facts.text() and "Dali" in doc.sel_parts.text()
    assert doc.copy_btn.text() == "Copy position" and not doc.teleport_btn.isHidden()
    doc.copy_btn.click()
    assert QApplication.clipboard().text() == "100.50 -70.25"
    doc.teleport_btn.click()
    assert sent == [(100.5, -70.25)]
    doc._on_pick(None)                                       # a click on sky clears the point
    assert doc._point is None and doc.sel_title.text() == "Sky"


def test_without_the_dev_teleport_the_button_never_shows(app, tmp_path):
    from ff9mapkit.workspace.worlddoc import WorldDoc
    doc = WorldDoc(pick_palette("mist"), game_path_fn=lambda: tmp_path)
    doc._census, doc._game = SimpleNamespace(root=tmp_path / "FF9CustomMap-world"), tmp_path
    doc.set_view_mode("3d", sync=True)
    doc._on_pick(((100.5, 5.0, -70.25), "Terrain"), sync=True)
    assert doc.teleport_btn.isHidden() and not doc.open_btn.isHidden()


def test_a_superseded_point_read_never_overwrites_the_newer_pick(app, tmp_path):
    from ff9mapkit.workspace.worlddoc import WorldDoc
    doc = WorldDoc(pick_palette("mist"), game_path_fn=lambda: tmp_path)
    doc._point = ((2.0, 0.0, -2.0), "Terrain")
    doc.sel_facts.setText("newer")
    doc._finish_point(((1.0, 0.0, -1.0), "Terrain"), {"bogus": True}, None)   # an older click's late answer
    assert doc.sel_facts.text() == "newer"


# ------------------------------------------------------------------ the whole FolderNames stack
def _doc_with_ini(app, tmp_path, folder, names):
    from ff9mapkit.workspace.worlddoc import WorldDoc
    (tmp_path / "Memoria.ini").write_text("[Mod]\nFolderNames = " + ", ".join(f'"{n}"' for n in names) + "\n",
                                          encoding="utf-8")
    doc = WorldDoc(pick_palette("mist"), game_path_fn=lambda: tmp_path)
    doc._census, doc._game = SimpleNamespace(root=tmp_path / folder), tmp_path
    return doc


def test_the_3d_page_draws_the_games_folder_order_by_default_and_says_so(app, tmp_path):
    doc = _doc_with_ini(app, tmp_path, "FF9CustomMap-world", ["FF9CustomMap", "FF9CustomMap-world", "MoguriMain"])
    assert doc.draw_box.isHidden()                           # a 3D-page control: the chart never shows it
    site, cap = doc._render_site()
    assert [p.name for p in site.stack] == ["FF9CustomMap", "FF9CustomMap-world", "MoguriMain"]
    assert cap.endswith("FF9CustomMap › FF9CustomMap-world › MoguriMain › stock") and "⚠" not in cap
    doc.set_view_mode("3d", sync=True)
    assert not doc.draw_box.isHidden() and doc._view3d.caption.text() == cap


def test_a_folder_the_game_does_not_load_is_named_and_only_this_folder_draws_it(app, tmp_path):
    doc = _doc_with_ini(app, tmp_path, "FF9CustomMap-lab", ["FF9CustomMap", "FF9CustomMap-world"])
    site, cap = doc._render_site()
    assert "FF9CustomMap-lab is not in FolderNames" in cap
    doc.draw_box.setCurrentIndex(doc.draw_box.findData("folder"))
    site, cap = doc._render_site()
    assert site.stack is None and site.mod_root.name == "FF9CustomMap-lab" and cap.startswith("Drawn: only")


def test_an_unreadable_ini_falls_back_to_one_folder_and_says_why(app, tmp_path):
    from ff9mapkit.workspace.worlddoc import WorldDoc
    doc = WorldDoc(pick_palette("mist"), game_path_fn=lambda: tmp_path)
    doc._census, doc._game = SimpleNamespace(root=tmp_path / "FF9CustomMap-world"), tmp_path   # no Memoria.ini
    site, cap = doc._render_site()
    assert site.stack is None and "could not be read" in cap


# ------------------------------------------------------------------ C7: the game's own camera
def test_ground_is_the_highest_up_facing_surface_under_a_point():
    packed = V.pack([GROUND, _lid(9.0, down=False)])
    assert V.ground_y(packed, 30.0, -33.0) == pytest.approx(9.0)          # the lid, over the ground
    assert V.ground_y(packed, 0.0, 0.0) == pytest.approx(0.0)
    assert V.ground_y(V.pack([GROUND, _lid(9.0, down=True)]), 30.0, -33.0) == pytest.approx(0.0)   # faces down
    assert V.ground_y(packed, 500.0, 500.0) is None and V.ground_y(None, 0.0, 0.0) is None


def test_the_game_camera_is_the_decoded_pose_and_meets_the_orbit_camera():
    from ff9mapkit.world import gamecam as G
    s = G.Settings(field_of_view=58.0)
    cam = V.GameCamera((30.0, 0.0, -30.0), 45.0, settings=s, area=14, ground=lambda x, z: 0.0)
    want = G.pose((30.0, 0.0, -30.0), 45.0, settings=s, area=14, ground=lambda x, z: 0.0)
    got = cam.view()
    assert got["eye"] == pytest.approx(want["eye"]) and got["at"] == pytest.approx(want["at"])
    assert got["fov"] == pytest.approx(want["fov"]) and got["near"] == V.NEAR
    orb = V.OrbitCamera(target=(30.0, 0.0, -30.0), yaw=10.0, pitch=40.0, dist=80.0)
    gc = V.GameCamera.from_orbit(orb, (30.0, 0.0, -30.0))
    assert gc.rotation == pytest.approx(190.0)
    e, a = np.asarray(gc.view()["eye"]), np.asarray(gc.view()["at"])
    oe, oa = np.asarray(orb.eye()), np.asarray(orb.target)
    d1, d2 = (a - e)[[0, 2]], (oa - oe)[[0, 2]]
    assert np.dot(d1, d2) / np.linalg.norm(d1) / np.linalg.norm(d2) > 0.999   # both look the same way
    assert gc.to_orbit().yaw == pytest.approx(10.0) and gc.to_orbit().target == gc.player


def test_in_the_game_camera_a_click_stands_the_party_and_a_drag_turns_it(app):
    w = V.WorldView3D()
    w.resize(320, 200)
    w.packed = V.pack([GROUND])
    w.set_camera(V.GameCamera((30.0, 0.0, -30.0), 0.0, ground=lambda x, z: 0.0))
    moved, picked = [], []
    w.party_moved.connect(lambda *p: moved.append(p))
    w.picked.connect(picked.append)
    r0 = w.camera.rotation
    _mouse(w, "press", (160, 150))
    _mouse(w, "release", (160, 150))
    assert picked and picked[0] is not None and moved and w.camera.player == pytest.approx(picked[0][0])
    _mouse(w, "press", (160, 150))
    _mouse(w, "move", (200, 150))
    _mouse(w, "release", (200, 150))
    assert w.camera.rotation != r0 and len(moved) == 1                    # a drag turns it and stands no one
    w.camera.zoom(3)
    w.camera.pan(10, 10, 200)
    assert w.camera.player == pytest.approx(picked[0][0])                 # the game's camera neither zooms nor pans
    changed = []
    w.camera_changed.connect(changed.append)
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    QApplication.sendEvent(w, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Home, Qt.KeyboardModifier.NoModifier))
    assert not w.game_mode() and changed == [False]


def test_the_panel_toggle_stands_the_party_at_the_pick_and_returns_to_the_orbit(app):
    from ff9mapkit.editor.theme import pick_palette
    p = V.WorldView3DPanel(pick_palette("dark"))
    p.view = V.WorldView3D()                                              # (offscreen has no GL to build one)
    p.view.camera_changed.connect(p._camera_changed)
    p.view.packed = V.pack([GROUND, _lid(9.0, down=False)])
    p.view.marker = (30.0, 9.0, -33.0)
    p.game_btn.setChecked(True)
    cam = p.view.camera
    assert p.view.game_mode() and cam.player == pytest.approx((30.0, 9.0, -33.0)) and cam.area == 14
    assert p.game_btn.text() == "Free view"                               # it names where it takes you
    p.game_btn.setChecked(False)
    assert not p.view.game_mode() and p.view.camera.target == pytest.approx((30.0, 9.0, -33.0))
    p.game_btn.setChecked(True)
    p.view.camera_changed.emit(False)                                     # Home in the view: the button follows
    assert not p.game_btn.isChecked() and p.game_btn.text() == "As the game sees it"


def test_the_game_camera_seats_each_vehicle_as_the_game_does(app):
    """C8, measured in game: on foot / a chocobo on the ground, the Blue Narciss at the water's surface less 0.703,
    a flyer at the height spin, raised to the ground below and never above the 42.1875 ceiling."""
    from ff9mapkit.editor.theme import pick_palette
    p = V.WorldView3DPanel(pick_palette("dark"))
    p.view = V.WorldView3D()
    p.view.packed = V.pack([GROUND, _lid(9.0, down=False)])
    p.view.marker = (30.0, 9.0, -33.0)
    p.game_btn.setChecked(True)
    assert p.vehicle_box.isVisibleTo(p) and not p.alt_spin.isVisibleTo(p)
    cam = p.view.camera
    assert cam.mode == 0 and cam.player[1] == pytest.approx(9.0)
    p.vehicle_box.setCurrentIndex(p.vehicle_box.findData(7))
    assert cam.mode == 7 and cam.player[1] == pytest.approx(9.0 + V.BOAT_DRAFT)
    p.vehicle_box.setCurrentIndex(p.vehicle_box.findData(8))
    assert p.alt_spin.isVisibleTo(p)
    p.alt_spin.setValue(30.0)
    assert cam.player[1] == pytest.approx(30.0)
    p.alt_spin.setValue(2.0)                                              # below the lid: raised onto it
    assert cam.player[1] == pytest.approx(9.0)
    from ff9mapkit.world import gamecam as G
    want = G.pose(cam.player, cam.rotation, mode=8, ground=cam.ground)
    assert cam.view()["eye"] == pytest.approx(want["eye"]) and cam.view()["fov"] == pytest.approx(want["fov"])
    p.game_btn.setChecked(False)
    assert not p.vehicle_box.isVisibleTo(p) and not p.alt_spin.isVisibleTo(p)
