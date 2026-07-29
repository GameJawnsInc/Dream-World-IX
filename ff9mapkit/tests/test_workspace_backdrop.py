"""BackdropCanvas — click-authoring Rung 0 (studies/click-authoring/PLAN.md).

Pins the widget half of the two-hop architecture: the SCENE is the logical painted canvas
(the three-scales law — a 4x art file still yields canvas-frame coordinates), the two
conversions route through the view transform + the self-asserting imagefield pair, the
horizon renders and refuses, and a click emits WORLD coordinates. The pure-math gate (grid
round-trip < 1e-9, inv3-not-transpose) lives in ``ff9mapkit/tests/test_imagefield.py``.

Coordinate transforms are font-independent, so offscreen geometry is honest here (the
offscreen lie is about TEXT widths)."""

from __future__ import annotations

import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt          # noqa: E402
from PySide6.QtGui import QPixmap                       # noqa: E402
from PySide6.QtTest import QTest                        # noqa: E402
from PySide6.QtWidgets import QApplication              # noqa: E402

from ff9mapkit import imagefield as IF                  # noqa: E402
from ff9mapkit.scene import cam as C                    # noqa: E402
from ff9mapkit.scene import guide                       # noqa: E402
from ff9mapkit.workspace.backdrop import BackdropCanvas  # noqa: E402
from ff9mapkit.workspace.shell import pick_palette      # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _canvas(app, *, art_scale=4, cam=True, pitch=26.0):
    """A realized canvas: 4x art (the painted-layer resolution) unless told otherwise."""
    c = BackdropCanvas(pick_palette("dark"))
    pm = QPixmap(384 * art_scale, 448 * art_scale) if art_scale else None
    if pm is not None:
        pm.fill(Qt.GlobalColor.darkGray)
    camera = guide.make_camera(pitch, 3000.0, fov_x_deg=42.0) if cam else None
    c.set_backdrop(pm, camera)
    c.resize(500, 560)
    c.show()
    QApplication.processEvents()
    return c, camera


def _tags(canvas):
    return [it.data(0) for it in canvas._scene.items() if it.data(0)]


def test_the_scene_frame_is_the_logical_canvas(app):
    """THE FRAME LAW: 4x-resolution art still gives a 384x448 scene — the art item is
    transformed INTO the frame, so no call site ever sees the layer scale."""
    c, _ = _canvas(app, art_scale=4)
    assert c._scene.sceneRect().size().toSize().width() == 384
    assert c._scene.sceneRect().size().toSize().height() == 448
    art = [it for it in c._scene.items() if it.data(0) == "backdrop"]
    assert len(art) == 1
    br = art[0].sceneBoundingRect()
    assert (round(br.width()), round(br.height())) == (384, 448)


def test_widget_roundtrip_survives_display_zoom(app):
    """HOP 1 is the view transform alone: after an arbitrary zoom + pan, world_to_click ->
    click_to_world still recovers the world point (no ad-hoc scale could survive this)."""
    c, cam = _canvas(app)
    c.scale(1.7, 1.7)
    c.translate(31, -17)
    for cpt in ((200.0, 380.0), (60.0, 300.0), (340.0, 430.0)):
        X, Z = IF.click_to_world(cam, cpt)
        wpt = c.world_to_click((X, Z))
        gx, gz = c.click_to_world(wpt)
        assert math.hypot(gx - X, gz - Z) < 1e-6


def test_click_emits_world_coords(app):
    """A left click on the floor emits floor_clicked with the same world point the pure
    conversion computes for that widget position."""
    c, cam = _canvas(app)
    got, refused = [], []
    c.floor_clicked.connect(lambda x, z: got.append((x, z)))
    c.click_refused.connect(refused.append)
    wpt = c.world_to_click((0.0, 1500.0))          # mid-floor, guaranteed below the horizon
    pos = QPoint(round(wpt.x()), round(wpt.y()))
    QTest.mouseClick(c.viewport(), Qt.MouseButton.LeftButton, pos=pos)
    assert not refused and len(got) == 1
    ex, ez = c.click_to_world(QPointF(pos))        # same integer pixel through the public path
    assert math.hypot(got[0][0] - ex, got[0][1] - ez) < 1e-9


def test_click_above_horizon_refuses(app):
    """The horizon guard reaches the mouse path: above the line -> click_refused, no
    floor_clicked, no silent clamp. Pitch 10 puts the horizon ON the canvas (y~142; the
    default 26 has it just off-frame at y~-3.6)."""
    c, cam = _canvas(app, pitch=10.0)
    got, refused = [], []
    c.floor_clicked.connect(lambda x, z: got.append((x, z)))
    c.click_refused.connect(refused.append)
    hy = C.horizon_canvas_y(cam)
    wpt = c.viewportTransform().map(QPointF(192.0, hy - 8))
    QTest.mouseClick(c.viewport(), Qt.MouseButton.LeftButton,
                     pos=QPoint(round(wpt.x()), round(wpt.y())))
    assert not got and len(refused) == 1 and "horizon" in refused[0]


def test_horizon_line_is_drawn_at_the_camera_horizon(app):
    c, cam = _canvas(app, pitch=10.0)              # horizon on-canvas at this pitch
    lines = [it for it in c._scene.items() if it.data(0) == "horizon"]
    assert len(lines) == 1
    hy = C.horizon_canvas_y(cam)
    assert abs(lines[0].line().y1() - hy) < 1e-9
    assert "horizonlabel" in _tags(c)


def test_off_frame_horizon_draws_nothing(app):
    """The default-pitch camera's horizon is just ABOVE the frame (y~-3.6): every canvas row
    is floor, so there is no boundary to draw — and the guard still refuses via the math."""
    c, _ = _canvas(app, pitch=26.0)
    assert "horizon" not in _tags(c)


def test_no_camera_is_inert_art_preview(app):
    """Art without a camera: the frame is the art's own pixels, no horizon, and a click
    neither emits nor crashes (click_to_world raises the honest error instead)."""
    c, _ = _canvas(app, art_scale=1, cam=False)
    assert c._scene.sceneRect().width() == 384      # art px 1:1 when no camera owns the frame
    assert "horizon" not in _tags(c)
    got, refused = [], []
    c.floor_clicked.connect(lambda x, z: got.append((x, z)))
    c.click_refused.connect(refused.append)
    QTest.mouseClick(c.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(200, 300))
    assert not got and not refused
    with pytest.raises(IF.ImageFieldError, match="no camera"):
        c.click_to_world(QPointF(200, 300))


def test_a_pan_is_not_a_click(app):
    """The slop law: press and release far apart = the user panned; nothing emits."""
    c, _ = _canvas(app)
    got, refused = [], []
    c.floor_clicked.connect(lambda x, z: got.append((x, z)))
    c.click_refused.connect(refused.append)
    QTest.mousePress(c.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(200, 400))
    QTest.mouseMove(c.viewport(), QPoint(240, 360))
    QTest.mouseRelease(c.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(240, 360))
    assert not got and not refused


# ---------------------------------------------------------------- Rung 1: the trace layer

def _trace_canvas(app, pitch=10.0):
    """A realized trace-mode canvas + the on_floor call log."""
    calls = []
    c = BackdropCanvas(pick_palette("dark"), on_floor=lambda pts: calls.append(pts))
    pm = QPixmap(384, 448)
    pm.fill(Qt.GlobalColor.darkGray)
    c.set_backdrop(pm, guide.make_camera(pitch, 3000.0, fov_x_deg=42.0))
    c.set_trace_mode(True)
    c.resize(500, 560)
    c.show()
    QApplication.processEvents()
    return c, c.camera(), calls


def test_trace_click_appends_a_vertex(app):
    """A slop-click on the floor appends a vertex at the clicked CANVAS px — one on_floor
    callback per click, handles + legs rendered."""
    c, cam, calls = _trace_canvas(app)
    want = ((100.0, 300.0), (300.0, 300.0), (200.0, 430.0))
    for cpt in want:
        wpt = c.viewportTransform().map(QPointF(*cpt))
        QTest.mouseClick(c.viewport(), Qt.MouseButton.LeftButton,
                         pos=QPoint(round(wpt.x()), round(wpt.y())))
    assert len(calls) == 3 and len(c.floor()) == 3
    for (ex, ey), (gx, gy) in zip(want, c.floor()):
        assert abs(gx - ex) <= 1 and abs(gy - ey) <= 1   # integer widget px quantization only
    tags = _tags(c)
    assert tags.count("tracept") == 3 and "traceline" in tags


def test_trace_click_above_horizon_refused_not_added(app):
    c, cam, calls = _trace_canvas(app)
    refused = []
    c.click_refused.connect(refused.append)
    hy = C.horizon_canvas_y(cam)
    wpt = c.viewportTransform().map(QPointF(192.0, hy - 8))
    QTest.mouseClick(c.viewport(), Qt.MouseButton.LeftButton,
                     pos=QPoint(round(wpt.x()), round(wpt.y())))
    assert not calls and not c.floor() and len(refused) == 1


def test_outset_preview_rings_the_polygon(app):
    """>=3 valid vertices -> the +48u collision ring, re-projected through the SAME
    conversions, drawn strictly outside the traced polygon. set_floor is the host's write
    path and must NOT echo on_floor."""
    c, cam, calls = _trace_canvas(app)
    c.set_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    assert not calls
    rings = [it for it in c._scene.items() if it.data(0) == "outset"]
    assert len(rings) == 1
    poly = rings[0].polygon()
    xs = [p.x() for p in poly]
    ys = [p.y() for p in poly]
    assert min(xs) < 20 and max(xs) > 364 and max(ys) > 440


def test_pitch_change_marks_bad_vertices_and_suspends_outset(app):
    """Canvas px stay the truth: a camera swap re-judges every vertex. The two back vertices
    land above the shallower camera's horizon -> error-marked with the refusal tooltip, and
    the outset preview SUSPENDS rather than lie from partial geometry."""
    c, _, calls = _trace_canvas(app, pitch=20.0)     # horizon y ~54
    c.set_floor([(130, 100), (254, 100), (364, 440), (20, 440)])
    assert [it for it in c._scene.items() if it.data(0) == "outset"]
    c.set_backdrop(c._pixmap, guide.make_camera(6.0, 3000.0, fov_x_deg=42.0), refit=False)
    tags = _tags(c)
    assert "outset" not in tags and tags.count("tracept") == 4
    bad = [it for it in c._scene.items() if it.data(0) == "tracept" and it.toolTip()]
    assert len(bad) == 2


def test_vertex_drag_commits_once_via_the_seam(app):
    """The StageCanvas contract: move updates only the grabbed handle; release commits ONE
    callback with the new list (tests drive the canvas-frame seam directly)."""
    c, cam, calls = _trace_canvas(app)
    c.set_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    assert c._begin_vertex_drag(1)
    c._drag_canvas(260.0, 210.0)
    c._drag_canvas(262.0, 214.0)
    assert not calls                                  # the drag never writes mid-gesture
    c._end_vertex_drag()
    assert len(calls) == 1 and c.floor()[1] == (262.0, 214.0)


def test_delete_vertex_commits_once(app):
    c, cam, calls = _trace_canvas(app)
    c.set_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    c._delete_vertex(0)
    assert len(calls) == 1 and len(c.floor()) == 3 and c.floor()[0] == (254.0, 200.0)


# ---------------------------------------------------------------- Rung 3: place mode

_RAMP = ((-500.0, 0.0, 800.0), (500.0, 0.0, 800.0), (0.0, 400.0, 1600.0))
_LOWER = ((-2000.0, 0.0, 400.0), (2000.0, 0.0, 400.0), (0.0, 0.0, 6000.0))
_UPPER = ((-400.0, 500.0, 1200.0), (400.0, 500.0, 1200.0), (0.0, 500.0, 2000.0))


def _place_canvas(app, tris, floors=None):
    c = BackdropCanvas(pick_palette("dark"))
    pm = QPixmap(384, 448)
    pm.fill(Qt.GlobalColor.darkGray)
    c.set_backdrop(pm, guide.make_camera(26.0, 3000.0, fov_x_deg=42.0))
    c.set_surface(tris, floors)
    c.set_place_mode(True)
    c.resize(500, 560)
    c.show()
    QApplication.processEvents()
    hits, refused = [], []
    c.surface_clicked.connect(hits.append)
    c.click_refused.connect(refused.append)
    return c, hits, refused


def _click_at_world(c, p):
    cx, cy = IF.world_point_to_click(c.camera(), p)
    wpt = c.viewportTransform().map(QPointF(cx, cy))
    QTest.mouseClick(c.viewport(), Qt.MouseButton.LeftButton,
                     pos=QPoint(round(wpt.x()), round(wpt.y())))


def test_place_click_hits_the_sloped_surface(app):
    """A click on a RAMP triangle emits the walkmesh hit — the exact case the plane model
    cannot serve; the footprint renders as meshtri items."""
    c, hits, refused = _place_canvas(app, [_RAMP], [0])
    p = tuple((_RAMP[0][i] * 0.4 + _RAMP[1][i] * 0.3 + _RAMP[2][i] * 0.3) for i in range(3))
    _click_at_world(c, p)
    assert not refused and len(hits) == 1
    got = hits[0]
    # integer WIDGET px quantization only: at fit zoom one widget px ≈ 0.8 canvas px, and one
    # canvas px at this ramp's depth spans ~3-4 world units — so within ~6u IS sub-pixel exact
    assert math.dist(got["pos"], p) < 6.0
    assert got["xz"] == (got["pos"][0], got["pos"][2]) and got["floor"] == 0
    assert len(got["stacked"]) == 1
    assert "meshtri" in _tags(c)


def test_place_click_reports_stacked_floors(app):
    """A bridge over a floor: the visible (upper) hit is first-class, both hits listed
    nearest-first with their floor ids — the host's disambiguation data."""
    c, hits, refused = _place_canvas(app, [_LOWER, _UPPER], [0, 1])
    p_up = tuple((_UPPER[0][i] * 0.4 + _UPPER[1][i] * 0.3 + _UPPER[2][i] * 0.3)
                 for i in range(3))
    _click_at_world(c, p_up)
    assert not refused and len(hits) == 1
    got = hits[0]
    assert got["floor"] == 1 and abs(got["pos"][1] - 500.0) < 1e-6
    assert len(got["stacked"]) == 2
    assert got["stacked"][1]["floor"] == 0          # the buried floor, second
    assert got["stacked"][0]["s"] < got["stacked"][1]["s"]


def test_place_click_off_mesh_refuses(app):
    c, hits, refused = _place_canvas(app, [_UPPER], [0])
    QTest.mouseClick(c.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(20, 20))
    assert not hits and len(refused) == 1 and "no walkmesh" in refused[0]


def test_modes_are_exclusive(app):
    """One click semantics at a time: enabling place mode turns trace off and vice versa."""
    c, _, _ = _place_canvas(app, [_RAMP])
    c.set_trace_mode(True)
    assert c._trace_mode and not c._place_mode
    c.set_place_mode(True)
    assert c._place_mode and not c._trace_mode


def test_markers_render_and_skip_behind_camera(app):
    c, _, _ = _place_canvas(app, [_RAMP])
    cz = C.decompose(c.camera())["C"][2]
    c.set_markers([{"pos": (0.0, 0.0, 1200.0), "label": "moggy"},
                   {"pos": (100.0, 0.0, 1500.0), "label": "spawn"},
                   {"pos": (0.0, 0.0, cz - 5000.0), "label": "ghost"}])   # behind: skipped
    assert _tags(c).count("marker") == 2


def test_bare_camera_frame_uses_cam_range(app):
    """No art at all (a scrolling field's wider Range must still frame correctly)."""
    c = BackdropCanvas(pick_palette("dark"))
    cam = guide.make_camera(10.0, 3000.0, fov_x_deg=42.0, range_wh=(768, 448))
    c.set_backdrop(None, cam)
    assert c._scene.sceneRect().width() == 768
    assert "horizon" in _tags(c)


# ---------------------------------------------------------------- Rung 2: contact mode

def test_contact_click_emits_the_raw_canvas_pixel(app):
    """Contact mode emits the CANVAS px of a slop click and nothing else — the host owns the
    judgement (occluder_z is the one owner of both refusals), so the canvas must not filter."""
    c, cam, _ = _trace_canvas(app)
    c.set_contact_mode(True)
    got = []
    c.contact_clicked.connect(lambda x, y: got.append((x, y)))
    wpt = c.viewportTransform().map(QPointF(230.0, 320.0))
    QTest.mouseClick(c.viewport(), Qt.MouseButton.LeftButton,
                     pos=QPoint(round(wpt.x()), round(wpt.y())))
    assert len(got) == 1
    assert abs(got[0][0] - 230.0) <= 1.0 and abs(got[0][1] - 320.0) <= 1.0   # integer-px quantized


def test_contact_mode_is_exclusive_but_keeps_the_trace_visible(app):
    """Arming contacts turns tracing OFF for clicks yet keeps the polygon RENDERED for context —
    and a click neither appends a vertex nor fires on_floor."""
    c, cam, calls = _trace_canvas(app)
    c._commit_floor([(100.0, 300.0), (300.0, 300.0), (200.0, 430.0)])
    n0 = len(calls)
    c.set_contact_mode(True)
    assert c._contact_mode and not c._trace_mode
    assert "traceline" in _tags(c) and "tracept" in _tags(c)   # visible, inert
    wpt = c.viewportTransform().map(QPointF(150.0, 350.0))
    QTest.mouseClick(c.viewport(), Qt.MouseButton.LeftButton,
                     pos=QPoint(round(wpt.x()), round(wpt.y())))
    assert len(c.floor()) == 3 and len(calls) == n0            # no vertex appended
    c.set_trace_mode(True)
    assert not c._contact_mode
