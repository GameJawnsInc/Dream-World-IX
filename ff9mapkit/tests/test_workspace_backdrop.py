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

pytest.importorskip("PySide6")

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


def test_cutout_furniture_renders_and_drags_one_emission_each(app):
    """set_cutouts renders the snip overlay + its contact handle; a drag is ONE emission per
    gesture through the same seam the vertex drags use (grab-relative, never corner-snapped)."""
    c, cam, _ = _trace_canvas(app)
    pm = QPixmap(100, 80)
    pm.fill(Qt.GlobalColor.red)
    c.set_cutouts([{"i": 0, "pixmap": pm, "rect": (100.0, 250.0, 50.0, 40.0),
                    "contact": (125.0, 290.0), "label": "fg0 · z 999",
                    "bad": False, "locked": False}])
    tags = _tags(c)
    assert "cutoutimg" in tags and "cutoutpt" in tags
    moved, anchored = [], []
    c.cutout_moved.connect(lambda i, x, y: moved.append((i, x, y)))
    c.contact_moved.connect(lambda i, x, y: anchored.append((i, x, y)))
    assert c._begin_cutout_drag(0, QPointF(110.0, 260.0))     # grabbed 10px inside the rect
    c._drag_canvas(130.0, 280.0)
    c._end_vertex_drag()
    assert moved == [(0, 120.0, 270.0)]                       # origin rode the grab delta
    assert c._begin_contact_drag(0)
    c._drag_canvas(140.0, 300.0)
    c._end_vertex_drag()
    assert anchored == [(0, 140.0, 300.0)]
    assert moved == [(0, 120.0, 270.0)]                       # the anchor drag moved no image


def test_locked_and_full_frame_cutouts_refuse_the_drag(app):
    c, cam, _ = _trace_canvas(app)
    pm = QPixmap(100, 80)
    pm.fill(Qt.GlobalColor.red)
    c.set_cutouts([{"i": 0, "pixmap": pm, "rect": None, "contact": (125.0, 290.0),
                    "label": "fg0", "bad": False, "locked": True},
                   {"i": 1, "pixmap": pm, "rect": (10.0, 10.0, 40.0, 30.0),
                    "contact": (30.0, 40.0), "label": "fg1", "bad": False, "locked": True}])
    assert not c._begin_cutout_drag(0, QPointF(120.0, 260.0))   # full-frame: registered art
    assert not c._begin_cutout_drag(1, QPointF(20.0, 20.0))     # locked snip: inert
    assert c._begin_contact_drag(0)                             # the ANCHOR always re-tunes


def test_grabbable_things_carry_the_move_cursor(app):
    """The hover affordance (owner-asked): the pan hand owns the whole drawspace, so every
    draggable item carries its OWN cursor — trace vertices (trace mode only), contact
    diamonds, and snip overlays; locked/full-frame overlays stay cursor-less (inert)."""
    from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsPolygonItem

    # Assert through the canvas's RETAINED wrappers (_kids/_cutout_items) — the originals the
    # app itself holds. ROOT-CAUSED (studies/pyside-gc-crash/): shiboken flips a wrapper to
    # Python-owned when parentItem() returns None, so the sweep helper's it.parentItem() made
    # dying wrappers DELETE the C++-owned items (crash-class, version-independent). The
    # retained path is safe because it never calls parentItem — keep it that way.
    def kid_cursors(canvas, cls):
        return [(k.cursor().shape() if k.hasCursor() else None)
                for k in canvas._kids if isinstance(k, cls)]

    c, cam, _ = _trace_canvas(app)
    c._commit_floor([(100.0, 300.0), (300.0, 300.0), (200.0, 430.0)])
    dot_cursors = kid_cursors(c, QGraphicsEllipseItem)   # the three vertex dots
    assert dot_cursors == [Qt.CursorShape.SizeAllCursor] * 3
    pm = QPixmap(40, 30)
    pm.fill(Qt.GlobalColor.red)
    c.set_cutouts([{"i": 0, "pixmap": pm, "rect": (50.0, 250.0, 40.0, 30.0),
                    "contact": (70.0, 280.0), "label": "fg0", "bad": False, "locked": False},
                   {"i": 1, "pixmap": pm, "rect": None, "contact": (200.0, 300.0),
                    "label": "fg1", "bad": False, "locked": True}])
    snip = c._cutout_items[0]
    assert snip.hasCursor() and snip.cursor().shape() == Qt.CursorShape.SizeAllCursor
    assert 1 not in c._cutout_items              # full-frame art is inert: never a drag target
    glyph_cursors = kid_cursors(c, QGraphicsPolygonItem)   # the two contact diamonds
    assert glyph_cursors == [Qt.CursorShape.SizeAllCursor] * 2
    c.set_contact_mode(True)                     # vertices go inert with the mode
    assert kid_cursors(c, QGraphicsEllipseItem) == [None, None, None]


@pytest.fixture(autouse=True)
def _deterministic_qt_teardown(qt_drain):
    """Widgets die HERE, not in a forced GC pass (THE GC-CHILD LAW's teardown half)."""
    yield
    qt_drain()


def test_a_press_through_crossing_furniture_still_grabs(app):
    """The says-Move-but-pans fix: a trace leg crossing a snip (or a contact diamond) must not
    eat the press — resolution scans EVERY item under the point by kind, matching what the
    hover cursor promises. The floor's closing leg here runs straight across both targets."""
    c, cam, calls = _trace_canvas(app)
    c._commit_floor([(60.0, 260.0), (340.0, 260.0), (200.0, 430.0)])   # leg y=260 spans the frame
    pm = QPixmap(40, 30)
    pm.fill(Qt.GlobalColor.red)
    c.set_cutouts([{"i": 0, "pixmap": pm, "rect": (100.0, 245.0, 40.0, 30.0),   # leg crosses it
                    "contact": (250.0, 260.0), "label": "fg0",                  # diamond ON the leg
                    "bad": False, "locked": False}])
    moved, anchored = [], []
    c.cutout_moved.connect(lambda i, x, y: moved.append((i, x, y)))
    c.contact_moved.connect(lambda i, x, y: anchored.append((i, x, y)))
    n0 = len(calls)
    wpt = c.viewportTransform().map(QPointF(120.0, 260.0))     # ON the leg, ON the snip's pixels
    QTest.mousePress(c.viewport(), Qt.MouseButton.LeftButton,
                     pos=QPoint(round(wpt.x()), round(wpt.y())))
    assert c._drag is not None and c._drag.get("kind") == "cimg"   # grabbed, not panned
    c._drag_canvas(140.0, 280.0)
    QTest.mouseRelease(c.viewport(), Qt.MouseButton.LeftButton,
                       pos=QPoint(round(wpt.x()) + 20, round(wpt.y()) + 20))
    assert len(moved) == 1 and len(calls) == n0                # one drag, no vertex appended
    wpt = c.viewportTransform().map(QPointF(250.0, 260.0))     # the diamond under the same leg
    QTest.mousePress(c.viewport(), Qt.MouseButton.LeftButton,
                     pos=QPoint(round(wpt.x()), round(wpt.y())))
    assert c._drag is not None and c._drag.get("kind") == "cpt"
    c._drag_canvas(255.0, 270.0)
    QTest.mouseRelease(c.viewport(), Qt.MouseButton.LeftButton,
                       pos=QPoint(round(wpt.x()) + 5, round(wpt.y()) + 10))
    assert len(anchored) == 1


def test_a_tag_miss_press_walk_leaves_the_scene_intact(app):
    """THE POISON-CALL FENCE (studies/pyside-gc-crash): press resolution must never call
    parentItem() — a None return flips the wrapper Python-owned, so the wrapper's DEATH
    deletes the C++-owned item (deterministic; probe_item_destroyed.py). A tag-MISS press
    (backdrop art, a trace leg, the frame) used to walk every hit to the None top and arm
    exactly that. Sweep the resolvers over every item as fresh wrappers — the itemAt()/
    items(pos) class — kill the wrappers, and the scene must not lose a single item."""
    import gc

    c, cam, _ = _trace_canvas(app)
    c._commit_floor([(100.0, 300.0), (300.0, 300.0), (200.0, 430.0)])
    pm = QPixmap(40, 30)
    pm.fill(Qt.GlobalColor.red)
    c.set_cutouts([{"i": 0, "pixmap": pm, "rect": (50.0, 250.0, 40.0, 30.0),
                    "contact": (70.0, 280.0), "label": "fg0", "bad": False, "locked": False}])
    n0 = len(c._scene.items())
    wrappers = c._scene.items()          # fresh temporaries where no retained wrapper exists
    for it in wrappers:                  # the mousePressEvent loop's exact resolver calls
        c._resolve_vertex(it)
        c._resolve_data(it, "cutoutpt")
        c._resolve_data(it, "cutoutimg")
    del wrappers, it
    gc.collect()
    assert len(c._scene.items()) == n0   # nothing armed, nothing deleted


def test_press_resolution_reads_the_hit_alone_children_included(app):
    """The parity half of the poison-call fence: a press lands on the VISIBLE furniture (a
    vertex dot, a contact diamond) — children of the tagged anchors — so with the ancestor
    walk banned, resolution must still find their handle through the hit item alone."""
    from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsPolygonItem

    c, cam, _ = _trace_canvas(app)
    c._commit_floor([(100.0, 300.0), (300.0, 300.0), (200.0, 430.0)])
    pm = QPixmap(40, 30)
    pm.fill(Qt.GlobalColor.red)
    c.set_cutouts([{"i": 0, "pixmap": pm, "rect": (50.0, 250.0, 40.0, 30.0),
                    "contact": (70.0, 280.0), "label": "fg0", "bad": False, "locked": False}])
    dots = [k for k in c._kids if isinstance(k, QGraphicsEllipseItem)]
    assert sorted(c._resolve_vertex(d) for d in dots) == [0, 1, 2]
    glyph = next(k for k in c._kids if isinstance(k, QGraphicsPolygonItem))
    assert c._resolve_data(glyph, "cutoutpt") == 0


# --------------------------------------------------------------------------- Rung 4: regions
def _region_canvas(app, tris=None):
    """A canvas in REGION mode (camera + optional walkmesh surface) with signal recorders."""
    c = BackdropCanvas(pick_palette("dark"))
    pm = QPixmap(384, 448)
    pm.fill(Qt.GlobalColor.darkGray)
    c.set_backdrop(pm, guide.make_camera(26.0, 3000.0, fov_x_deg=42.0))
    if tris is not None:
        c.set_surface(tris, [0] * len(tris))
    c.set_region_mode(True)
    c.resize(500, 560)
    c.show()
    QApplication.processEvents()
    drawn, changed, deleted, refused = [], [], [], []
    c.region_drawn.connect(drawn.append)
    c.region_changed.connect(lambda i, q: changed.append((i, q)))
    c.region_deleted.connect(deleted.append)
    c.click_refused.connect(refused.append)
    return c, drawn, changed, deleted, refused


_GW_QUAD = [(-300.0, 900.0), (300.0, 900.0), (300.0, 1500.0), (-300.0, 1500.0)]


def test_region_mode_is_exclusive_with_every_other(app):
    c, *_ = _region_canvas(app)
    assert c._region_mode
    c.set_trace_mode(True)
    assert c._trace_mode and not c._region_mode
    c.set_region_mode(True)
    assert c._region_mode and not c._trace_mode and not c._place_mode
    c.set_contact_mode(True)
    assert c._contact_mode and not c._region_mode


def test_four_clicks_emit_one_region_drawn_with_world_corners(app):
    c, drawn, *_ , refused = _region_canvas(app)
    for n, (x, z) in enumerate(_GW_QUAD):
        _click_at_world(c, (x, 0.0, z))
        if n == 1:                                       # mid-draw: pending renders, no emission
            assert not drawn and "regionpending" in _tags(c)
    assert not refused and len(drawn) == 1
    quad = drawn[0]
    assert len(quad) == 4
    for (gx, gz), (ex, ez) in zip(quad, _GW_QUAD):
        assert math.hypot(gx - ex, gz - ez) < 12.0       # integer widget-px quantization only
    assert "regionpending" not in _tags(c)               # the gesture consumed its corners


def test_escape_abandons_the_pending_quad(app):
    c, drawn, *_ = _region_canvas(app)
    _click_at_world(c, (-300.0, 0.0, 900.0))
    _click_at_world(c, (300.0, 0.0, 900.0))
    assert "regionpending" in _tags(c)
    QTest.keyClick(c, Qt.Key.Key_Escape)
    assert "regionpending" not in _tags(c) and not drawn


def test_set_regions_renders_the_laws_not_just_the_quads(app):
    """The census: kind by SHAPE (a gateway's walk-out edge + chevron), the fan audit painted
    (the notch-in-hull dart spills in warn), handles + corner indices only in region mode."""
    c, *_ = _region_canvas(app)
    dart = [(70.0, 1060.0), (100.0, 1000.0), (100.0, 1100.0), (0.0, 1100.0)]
    c.set_regions([
        {"i": 0, "quad": _GW_QUAD, "label": "door0 → 4005", "kind": "gateway", "warn": None},
        {"i": 1, "quad": dart, "label": "zone0", "kind": "event",
         "warn": "over-trigger ~31% — fires outside the drawn outline"},
    ])
    tags = _tags(c)
    assert tags.count("regionquad") == 2
    assert tags.count("regionedge") == 1                 # gateways only
    assert tags.count("regionchevron") == 1
    assert tags.count("regionlabel") == 2
    assert tags.count("regionpt") == 8                   # 4 corners x 2 quads, region mode
    assert tags.count("regionspill") >= 1                # the dart's fan swallows its notch
    assert tags.count("regiongap") == 0
    warn_tip = c._region_items[1].toolTip()
    assert "over-trigger" in warn_tip and "⚠" in warn_tip
    c.set_place_mode(True)                               # regions stay visible for context…
    tags = _tags(c)
    assert tags.count("regionquad") == 2 and tags.count("regionpt") == 0   # …but inert


def test_corner_and_whole_quad_drags_emit_once_each(app):
    c, drawn, changed, *_ = _region_canvas(app)
    c.set_regions([{"i": 0, "quad": _GW_QUAD, "label": "door0", "kind": "gateway",
                    "warn": None}])
    assert c._begin_region_corner_drag(0, 2)
    tx, ty = IF.world_point_to_click(c.camera(), (350.0, 0.0, 1600.0))
    c._drag_canvas(tx, ty)
    c._end_vertex_drag()
    assert len(changed) == 1
    i, quad = changed[0]
    assert i == 0 and math.hypot(quad[2][0] - 350.0, quad[2][1] - 1600.0) < 0.2
    assert quad[0] == _GW_QUAD[0]                        # the other corners never moved
    # whole-quad drag: grab the centre, move it +100/+100 in world
    changed.clear()
    c.set_regions([{"i": 0, "quad": _GW_QUAD, "label": "door0", "kind": "gateway",
                    "warn": None}])
    gx, gy = IF.world_point_to_click(c.camera(), (0.0, 0.0, 1200.0))
    assert c._begin_region_quad_drag(0, QPointF(gx, gy))
    nx, ny = IF.world_point_to_click(c.camera(), (100.0, 0.0, 1300.0))
    c._drag_canvas(nx, ny)
    c._end_vertex_drag()
    assert len(changed) == 1 and not drawn
    _, quad = changed[0]
    for (qx, qz), (ex, ez) in zip(quad, _GW_QUAD):
        assert math.hypot(qx - (ex + 100.0), qz - (ez + 100.0)) < 0.3


def test_region_menu_rotates_the_walkout_edge_and_deletes(app, monkeypatch):
    import types

    class _FakeMenu:
        pick = 0                                          # which added action exec() returns

        def __init__(self, parent=None):
            self.acts = []

        def addAction(self, text):
            tok = types.SimpleNamespace(text=text)
            self.acts.append(tok)
            return tok

        def exec(self, pos):
            return self.acts[_FakeMenu.pick]

    monkeypatch.setattr("PySide6.QtWidgets.QMenu", _FakeMenu)
    c, _, changed, deleted, _ = _region_canvas(app)
    retargeted = []
    c.region_retarget.connect(retargeted.append)
    c.set_regions([{"i": 0, "quad": _GW_QUAD, "label": "door0", "kind": "gateway",
                    "warn": None}])
    _FakeMenu.pick = 0                                    # gateways lead with Set target…
    c._region_menu(0, QPoint(0, 0))
    assert retargeted == [0]                              # the host asks + writes (Field(0) lesson)
    _FakeMenu.pick = 1                                    # then the walk-out rotate
    c._region_menu(0, QPoint(0, 0))
    assert changed == [(0, _GW_QUAD[1:] + _GW_QUAD[:1])]  # order rotated, geometry identical
    _FakeMenu.pick = 2
    c._region_menu(0, QPoint(0, 0))
    assert deleted == [0]


def test_event_menu_offers_reword_not_gateway_tools(app, monkeypatch):
    import types

    class _FakeMenu:
        pick = 0

        def __init__(self, parent=None):
            self.acts = []

        def addAction(self, text):
            tok = types.SimpleNamespace(text=text)
            self.acts.append(tok)
            return tok

        def exec(self, pos):
            return self.acts[_FakeMenu.pick]

    monkeypatch.setattr("PySide6.QtWidgets.QMenu", _FakeMenu)
    c, _, changed, deleted, _ = _region_canvas(app)
    reworded = []
    c.region_reword.connect(reworded.append)
    c.set_regions([{"i": 0, "quad": _GW_QUAD, "label": "zone0", "kind": "event",
                    "warn": None}])
    _FakeMenu.pick = 0                                    # events lead with Set message…
    c._region_menu(0, QPoint(0, 0))
    assert reworded == [0] and not changed and not deleted
    _FakeMenu.pick = 1                                    # then Delete (no gateway tools)
    c._region_menu(0, QPoint(0, 0))
    assert deleted == [0]


def test_zone_corners_project_at_the_mesh_floor_height(app):
    """A raised real floor (render y = -300): corners draw AT that height, an on-mesh pixel
    converts through the raycast, and an OFF-mesh pixel lands on the plane at the nearest
    floor height (donor door quads legitimately hang past the mesh edge)."""
    y = -300.0
    a, b, cc, d = (-1000.0, y, 500.0), (1000.0, y, 500.0), (1000.0, y, 2500.0), (-1000.0, y, 2500.0)
    c, *_ = _region_canvas(app, tris=[(a, b, cc), (a, cc, d)])
    c.set_regions([{"i": 0, "quad": [(0.0, 900.0), (200.0, 900.0), (200.0, 1100.0),
                                     (0.0, 1100.0)], "label": "door0", "kind": "gateway",
                    "warn": None}])
    ex, ey = IF.world_point_to_click(c.camera(), (0.0, y, 900.0))
    h = c._region_handle_items[(0, 0)]
    assert math.hypot(h.pos().x() - ex, h.pos().y() - ey) < 0.01
    on = c._px_to_zone_world(QPointF(*IF.world_point_to_click(c.camera(), (0.0, y, 900.0))))
    assert math.hypot(on[0] - 0.0, on[1] - 900.0) < 1e-6          # the raycast, exact
    off_px = IF.world_point_to_click(c.camera(), (5000.0, y, 2000.0))
    off = c._px_to_zone_world(QPointF(*off_px))
    assert math.hypot(off[0] - 5000.0, off[1] - 2000.0) < 1.0     # the plane at floor height


# --------------------------------------------------------------------------- the view grammar
# Every fence here delivers its input through QApplication.sendEvent(view.viewport(), ...), the
# path Qt itself takes, and runs at an ODD and an EVEN width (the skill's parity trap).

def _fitted(app, w, h=560):
    """A canvas shown at (w, h) whose deferred first-paint fit has really run."""
    c, cam = _canvas(app)
    c.resize(w, h)
    QApplication.processEvents()
    c.viewport().repaint()                     # the deferred fit runs in the first REAL paint
    QApplication.processEvents()
    assert not c._fit_pending
    return c, cam


def _ctrl_wheel(c, dy, dx=0, n=1):
    from PySide6.QtCore import QPoint as _P
    from PySide6.QtGui import QWheelEvent
    vp = c.viewport()
    pos = QPointF(vp.width() / 2, vp.height() / 2)
    for _ in range(n):
        ev = QWheelEvent(pos, QPointF(vp.mapToGlobal(pos.toPoint())), _P(0, 0), _P(dx, dy),
                         Qt.MouseButton.NoButton, Qt.KeyboardModifier.ControlModifier,
                         Qt.ScrollPhase.NoScrollPhase, False)
        QApplication.sendEvent(vp, ev)
        QApplication.processEvents()           # the scrollbars' layout lands between steps,
                                               # as it does for a real hand on a real wheel


def _ctrl_key(c, key):
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeyEvent
    QApplication.sendEvent(c, QKeyEvent(QEvent.Type.KeyPress, key,
                                        Qt.KeyboardModifier.ControlModifier))
    QApplication.processEvents()


def _art_fits(c):
    """The whole frame lies inside the viewport and neither scrollbar has a range."""
    r = c.mapFromScene(c._scene.sceneRect()).boundingRect()
    vp = c.viewport().rect()
    return (vp.contains(r) and c.verticalScrollBar().maximum() == 0
            and c.horizontalScrollBar().maximum() == 0)


@pytest.mark.parametrize("w", [501, 500])
def test_a_layout_shrink_refits_until_the_author_zooms(app, w):
    """T24: the Trace cut-out strip appearing (any layout shrink) must not crop the art behind a
    scrollbar while the author is still at the fit; once they have zoomed, their zoom stays."""
    c, _ = _fitted(app, w)
    assert _art_fits(c)
    c.resize(w, 470)                           # the strip row arrives: ~90 px shorter
    QApplication.processEvents()
    assert _art_fits(c), "a shrink left the art cropped behind a scrollbar"
    c.resize(w, 620)                           # and a grown window fills again
    QApplication.processEvents()
    grown = c.transform().m11()
    c.resize(w, 560)
    QApplication.processEvents()
    assert c.transform().m11() < grown
    _ctrl_wheel(c, 120)                        # the author zooms: from now on it is theirs
    z = c.transform().m11()
    c.resize(w, 470)
    QApplication.processEvents()
    assert c.transform().m11() == pytest.approx(z)
    _ctrl_key(c, Qt.Key.Key_0)                 # Ctrl+0 is the way back to following the layout
    c.resize(w, 560)
    QApplication.processEvents()
    assert _art_fits(c) and c.transform().m11() > z * 0.5
    _ctrl_key(c, Qt.Key.Key_1)                 # 1:1 is a chosen zoom too
    c.resize(w, 470)
    QApplication.processEvents()
    assert c.transform().m11() == pytest.approx(1.0)


@pytest.mark.parametrize("w", [501, 500])
def test_ctrl0_from_a_zoomed_view_fits_like_the_first_paint(app, w):
    """V4: Ctrl+0 measured the scrollbar-reduced viewport and fitted ~2% small."""
    c, _ = _fitted(app, w)
    first = c.transform().m11()
    _ctrl_wheel(c, 120, n=4)                   # in until the scrollbars show
    assert c.verticalScrollBar().maximum() > 0
    _ctrl_key(c, Qt.Key.Key_0)
    QApplication.processEvents()
    assert c.transform().m11() == pytest.approx(first, abs=1e-9)


@pytest.mark.parametrize("w", [501, 500])
def test_the_hint_pill_stays_in_its_corner_after_a_pan(app, w):
    """V2: the pill is a viewport child; QGraphicsView scrolls the viewport, children and all."""
    c, _ = _fitted(app, w)
    _ctrl_wheel(c, 120, n=6)
    sb = c.verticalScrollBar()
    hb = c.horizontalScrollBar()
    assert sb.maximum() > 0
    sb.setValue(sb.maximum())                  # exactly what ScrollHandDrag does
    hb.setValue(hb.maximum())
    QApplication.processEvents()
    vp, hint = c.viewport(), c._hint
    want = (vp.width() - hint.width() - 10, vp.height() - hint.height() - 8)
    assert (hint.x(), hint.y()) == want


@pytest.mark.parametrize("w", [501, 500])
def test_ctrl_wheel_zoom_follows_the_delta_and_ignores_a_sideways_wheel(app, w):
    """V5: a precision touchpad splits one 120 detent into small deltas -- eight 15s are ONE
    step, not eight; a horizontal Ctrl+wheel (dy == 0) is not a zoom-out."""
    c, _ = _fitted(app, w)
    z0 = c.transform().m11()
    _ctrl_wheel(c, 15, n=8)
    assert c.transform().m11() / z0 == pytest.approx(1.15, rel=1e-6)
    z1 = c.transform().m11()
    _ctrl_wheel(c, 0, dx=120)
    assert c.transform().m11() == pytest.approx(z1)
    _ctrl_wheel(c, -120)
    assert c.transform().m11() / z1 == pytest.approx(1 / 1.15, rel=1e-6)


# --------------------------------------------------------------------------- gestures, end to end
# Delivered through QApplication.sendEvent(view.viewport(), ...) with explicit button state, so a
# BUTTONLESS move really is buttonless (mouse tracking is on: AnchorUnderMouse turns it on).

def _mouse(c, kind, canvas_pt, *, button=Qt.MouseButton.LeftButton, buttons=None):
    """One mouse event at a CANVAS point. ``kind`` = press / move / release."""
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QMouseEvent
    t = {"press": QEvent.Type.MouseButtonPress, "move": QEvent.Type.MouseMove,
         "release": QEvent.Type.MouseButtonRelease}[kind]
    vp = c.viewport()
    wpt = c.viewportTransform().map(QPointF(*canvas_pt))
    pos = QPointF(round(wpt.x()), round(wpt.y()))
    if buttons is None:
        buttons = button if kind != "release" else Qt.MouseButton.NoButton
    btn = Qt.MouseButton.NoButton if kind == "move" else button
    ev = QMouseEvent(t, pos, QPointF(vp.mapToGlobal(pos.toPoint())), btn, buttons,
                     Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(vp, ev)


def _click(c, canvas_pt):
    _mouse(c, "press", canvas_pt)
    _mouse(c, "release", canvas_pt)


_TRI = [(100.0, 300.0), (300.0, 300.0), (200.0, 430.0)]


def test_a_drag_whose_release_was_lost_ends_on_the_next_buttonless_move(app):
    """V3: a release lost to a modal menu left the vertex following the HOVER, and the next
    ordinary click committed it at that stray spot."""
    c, cam, calls = _trace_canvas(app)
    c._commit_floor(_TRI)
    n0 = len(calls)
    _mouse(c, "press", _TRI[0])
    assert c._drag and c._drag["kind"] == "vertex"
    _mouse(c, "move", (130.0, 320.0))                        # still held: the vertex follows
    assert c._drag and c._drag["pt"] != _TRI[0]
    _mouse(c, "move", (220.0, 330.0), buttons=Qt.MouseButton.NoButton)   # the release never came
    assert c._drag is None and c.floor() == _TRI and len(calls) == n0
    a = c._trace_items[0]["anchor"]                          # the RETAINED wrapper
    assert (a.pos().x(), a.pos().y()) == _TRI[0]             # the handle went home
    _click(c, (220.0, 330.0))                                # the next click is just a click
    assert len(c.floor()) == 4 and c.floor()[0] == _TRI[0]


def test_escape_aborts_a_live_drag(app):
    """V8: Esc mid-drag puts the vertex back; the release then commits nothing."""
    c, cam, calls = _trace_canvas(app)
    c._commit_floor(_TRI)
    n0 = len(calls)
    _mouse(c, "press", _TRI[1])
    _mouse(c, "move", (320.0, 340.0))
    assert c._drag
    QTest.keyClick(c, Qt.Key.Key_Escape)
    assert c._drag is None and not c._coords.isVisible()
    _mouse(c, "release", (320.0, 340.0))
    assert c.floor() == _TRI and len(calls) == n0
    a = c._trace_items[1]["anchor"]
    assert (a.pos().x(), a.pos().y()) == _TRI[1]


def _snip(c, locked=False):
    pm = QPixmap(40, 30)
    pm.fill(Qt.GlobalColor.red)
    c.set_cutouts([{"i": 0, "pixmap": pm, "rect": (100.0, 320.0, 40.0, 30.0),
                    "contact": (120.0, 350.0), "label": "fg0", "bad": False, "locked": locked}])


def test_snips_and_contacts_show_move_only_where_a_press_drags_them(app):
    """V6: in the Regions tool a press on a snip pans or places a corner, so no Move cursor."""
    from PySide6.QtWidgets import QGraphicsPolygonItem
    c, cam, _ = _trace_canvas(app)
    _snip(c)
    c.set_region_mode(True)
    snip = c._cutout_items[0]
    assert not snip.hasCursor()
    assert not any(k.hasCursor() for k in c._kids if isinstance(k, QGraphicsPolygonItem))
    c.set_contact_mode(True)                                 # the Cut-outs tool: they drag again
    assert c._cutout_items[0].hasCursor()


def test_a_contact_click_on_a_snip_body_marks_a_contact(app):
    """V9: in contact mode a click that does not travel is a contact, even over a snip's
    opaque pixels; a press that travels still drags the snip."""
    c, cam, _ = _trace_canvas(app)
    _snip(c)
    c.set_contact_mode(True)
    got, moved = [], []
    c.contact_clicked.connect(lambda x, y: got.append((x, y)))
    c.cutout_moved.connect(lambda i, x, y: moved.append((i, x, y)))
    _click(c, (110.0, 330.0))                                # ON the snip's red body
    assert len(got) == 1 and not moved
    assert abs(got[0][0] - 110.0) <= 1.0 and abs(got[0][1] - 330.0) <= 1.0
    _mouse(c, "press", (110.0, 330.0))
    _mouse(c, "move", (150.0, 360.0))
    _mouse(c, "release", (150.0, 360.0))
    assert len(moved) == 1 and len(got) == 1
    c.set_trace_mode(True)                                   # tracing: a snip body is a grab,
    n = len(c.floor())                                       # never a vertex
    _click(c, (110.0, 330.0))                                # (no host re-fed the moved rect)
    assert len(c.floor()) == n and len(got) == 1


def test_a_first_corner_can_start_inside_an_existing_region(app):
    """P24: a click inside a drawn quad (no corners pending) is the first corner of a new one;
    a press that travels still moves the quad."""
    c, drawn, changed, _, refused = _region_canvas(app)
    c.set_regions([{"i": 0, "quad": _GW_QUAD, "label": "door0", "kind": "gateway",
                    "warn": None}])
    inside = IF.world_point_to_click(c.camera(), (0.0, 0.0, 1200.0))
    _click(c, inside)
    assert len(c._pending_region) == 1 and not changed and not refused
    QTest.keyClick(c, Qt.Key.Key_Escape)
    assert not c._pending_region
    _mouse(c, "press", inside)
    _mouse(c, "move", (inside[0] + 20, inside[1] + 10))
    _mouse(c, "release", (inside[0] + 20, inside[1] + 10))
    assert len(changed) == 1 and not c._pending_region


def test_the_hint_pill_speaks_the_current_tool_then_gets_out_of_the_way(app):
    """P18: the pill said 'click the floor' in every mode and sat over the art's bottom-right
    for good. It now says what THIS mode's click does, and hides after the first gesture
    (a mode change or a new field brings it back)."""
    c, cam, _ = _trace_canvas(app)
    hint = c._hint
    assert "outline" in hint.text() and hint.isVisibleTo(c)
    c.set_region_mode(True)
    assert "4 corners" in hint.text() and "Esc" in hint.text()
    assert "click the floor" not in hint.text()
    c.set_contact_mode(True)
    assert "base" in hint.text() and "click the floor" not in hint.text()
    c.set_place_mode(True)
    assert "click the floor" in hint.text()
    c.set_region_mode(True)
    _click(c, IF.world_point_to_click(cam, (0.0, 0.0, 1200.0)))   # one corner placed
    assert len(c._pending_region) == 1 and not hint.isVisibleTo(c)
    c.set_trace_mode(True)
    assert hint.isVisibleTo(c) and "outline" in hint.text()
    c.set_floor(_TRI)
    assert c._begin_vertex_drag(0)                           # a drag spends it too
    c._drag_canvas(110.0, 310.0)
    c._end_vertex_drag()
    assert not hint.isVisibleTo(c)
    bare =BackdropCanvas(pick_palette("dark"))
    bare.set_backdrop(None, None)
    assert "click" not in bare._hint.text()                  # no camera: nothing to click


def test_the_regions_tool_shows_the_traced_floor_edge(app):
    """T29: doors belong on the walkable edge, so the Regions tool keeps the floor outline and
    its outset ring in view -- inert, and without the vertex handles (a trace thing)."""
    c, cam, calls = _trace_canvas(app)
    c._commit_floor([(130.0, 200.0), (254.0, 200.0), (364.0, 440.0), (20.0, 440.0)])
    c.set_region_mode(True)
    tags = _tags(c)
    assert "traceline" in tags and "outset" in tags
    assert "tracept" not in tags                             # no vertex furniture to collide with
    n0 = len(calls)                                          # corners, not vertices
    _click(c, (200.0, 300.0))
    assert len(calls) == n0 and len(c._pending_region) == 1


# --------------------------------------------------------------------------- furniture ON the art
# The art is an ARBITRARY ground. These fences read RENDERED pixels (colour is font-independent,
# so offscreen colour holds) over art that spans the luminance range, in every shipped theme.

_ARTS = {"black": "#000000", "white": "#ffffff", "tan floor": "#9e8460", "navy wall": "#26293a"}


def _lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def _cr(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _furnished(app, theme, art):
    """Every kind of on-art furniture over a flat ``art`` ground: trace legs + vertices (one
    above the horizon), a contact, a gateway, a marker."""
    from PySide6.QtGui import QColor
    c = BackdropCanvas(pick_palette(theme), on_floor=lambda pts: None)
    pm = QPixmap(384, 448)
    pm.fill(QColor(art))
    c.set_backdrop(pm, guide.make_camera(20.0, 3000.0, fov_x_deg=42.0))   # horizon y ~54
    c.set_trace_mode(True)
    c.resize(500, 560)
    c.show()
    QApplication.processEvents()
    c.viewport().repaint()
    c.set_floor([(60.0, 30.0), (330.0, 120.0), (360.0, 430.0), (30.0, 430.0)])   # 0 is bad
    c.set_cutouts([{"i": 0, "pixmap": None, "rect": None, "contact": (200.0, 300.0),
                    "label": "fg0 · z 1073", "bad": False, "locked": True}])
    c.set_regions([{"i": 0, "quad": _GW_QUAD, "label": "door0 → 4005", "kind": "gateway",
                    "warn": None}])
    c.set_markers([{"pos": (0.0, 0.0, 2200.0), "label": "Mira", "kind": "npc"}])
    QApplication.processEvents()
    return c


def _viewport_rgb(c):
    img = c.viewport().grab().toImage()
    return lambda x, y: img.pixelColor(x, y).getRgb()[:3], img.width(), img.height()


def _label_rect(c, lab):
    base = c.mapFromScene(lab["anchor"].pos())
    p = lab["plate"].pos()
    return QPointF(base.x() + p.x(), base.y() + p.y()), lab["w"], lab["h"]


@pytest.mark.parametrize("theme", ["light", "dark", "mist", "dracula"])
@pytest.mark.parametrize("art", list(_ARTS))
def test_on_art_text_and_glyphs_hold_contrast_on_any_art(app, theme, art):
    """P20: every label's ink clears 4.5:1 against what is actually painted behind it, and
    every handle/glyph puts a pixel within 3:1-or-better reach of the art around it."""
    from collections import Counter
    c = _furnished(app, theme, _ARTS[art])
    px, W, H = _viewport_rgb(c)
    texts = [lab["text"].text() for lab in c._labels]
    assert any("door0" in t for t in texts) and any("fg0" in t for t in texts)
    assert any("Mira" in t for t in texts) and any("✕" in t for t in texts)
    for lab in c._labels:
        tl, w, h = _label_rect(c, lab)
        x0, y0 = int(tl.x()) + 2, int(tl.y()) + 2
        pts = [px(x, y) for y in range(y0, min(H, y0 + int(h) - 3))
               for x in range(x0, min(W, x0 + int(w) - 3)) if x >= 0 and y >= 0]
        assert pts, lab["text"].text()
        ground = Counter(pts).most_common(1)[0][0]
        ink = max(_cr(p, ground) for p in pts)
        assert ink >= 4.5, f"{theme}/{art}: '{lab['text'].text()}' ink {ink:.2f}:1"
    art_rgb = tuple(int(_ARTS[art][i:i + 2], 16) for i in (1, 3, 5))
    for anchor, box in c._glyphs:
        b = c.mapFromScene(anchor.pos())
        ring = [px(int(b.x() + dx), int(b.y() + dy)) for dy in range(-9, 10)
                for dx in range(-9, 10) if 0 <= b.x() + dx < W and 0 <= b.y() + dy < H]
        assert max(_cr(p, art_rgb) for p in ring) >= 3.0, f"{theme}/{art}: a glyph vanishes"


@pytest.mark.parametrize("theme", ["light", "dark", "mist", "dracula"])
def test_every_on_art_stroke_clears_3_to_1_against_its_casing(app, theme):
    """P20, the lines: a leg / outline / horizon / footprint edge is always adjacent to its own
    casing, so THAT pair carries the 3:1 non-text floor, whatever the art does. And the casing
    is really painted under the stroke (read from pixels on a mid-grey ground)."""
    from PySide6.QtGui import QColor
    c = _furnished(app, theme, "#808080")
    for key in ("accent", "warn", "error"):
        col = QColor(c.pal[key])
        case = c._casing(col)
        assert _cr(col.getRgb()[:3], case.getRgb()[:3]) >= 3.0, (theme, key)
    px, W, H = _viewport_rgb(c)
    a, b = (c.viewportTransform().map(QPointF(*p)) for p in ((360.0, 430.0), (30.0, 430.0)))
    mx, my = int((a.x() + b.x()) / 2), int((a.y() + b.y()) / 2)   # the leg 2 -> 3 (horizontal)
    column = [px(mx, y) for y in range(my - 4, my + 5)]
    case = c._casing(QColor(c.pal["accent"])).getRgb()[:3]
    grey = (128, 128, 128)                 # the casing pulls the leg's flank away from the art,
    toward = (lambda p: _lum(p) < _lum(grey)) if _lum(case) < _lum(grey) else \
        (lambda p: _lum(p) > _lum(grey))   # on the casing's side (antialiasing blends it)
    assert any(toward(p) and _cr(p, grey) >= 2.0 for p in column), \
        ("no casing under the leg", column, case)


def test_labels_never_overprint_each_other_or_a_handle(app):
    """P21: far-back zones compress to a few pixels; their labels used to pile into one
    unreadable cluster under the corner handles. Labels now take free tiers."""
    c, *_ = _region_canvas(app)
    quads = [[(x - 150.0, 2600.0), (x + 150.0, 2600.0), (x + 150.0, 2900.0), (x - 150.0, 2900.0)]
             for x in (-250.0, 0.0, 250.0)]
    c.set_regions([{"i": n, "quad": q, "label": f"zone{n} → 40{n}5", "kind": "event",
                    "warn": "over-trigger" if n == 1 else None} for n, q in enumerate(quads)])
    c.set_markers([{"pos": (0.0, 0.0, 2750.0), "label": "Mira", "kind": "npc"}])
    from PySide6.QtCore import QRectF
    rects = []
    for lab in c._labels:
        tl, w, h = _label_rect(c, lab)
        rects.append(QRectF(tl.x(), tl.y(), w, h))
    assert len(rects) == 4
    for a in range(len(rects)):
        for b in range(a + 1, len(rects)):
            assert not rects[a].intersects(rects[b]), (a, b)
    for anchor, box in c._glyphs:
        g = box.translated(c.mapFromScene(anchor.pos()).toPointF())
        assert not any(r.intersects(g) for r in rects), "a label hides a handle"
    assert not any(lab["text"].text() in "0123" for lab in c._labels)   # no corner indices
    lines = [it.zValue() for it in c._scene.items() if it.data(0) in ("casing", "regionquad")]
    assert all(lab["anchor"].zValue() > max(lines) for lab in c._labels)   # never struck out


def test_markers_speak_their_kind_by_shape(app):
    """P25: npc / prop / chest / spawn / arrival were five identical rings."""
    from PySide6.QtWidgets import QGraphicsPathItem
    c, _, _ = _place_canvas(app, [_RAMP])
    kinds = ["npc", "prop", "chest", "spawn", "arrival"]
    c.set_markers([{"pos": (-400.0 + 200 * n, 0.0, 1500.0), "label": k, "kind": k}
                   for n, k in enumerate(kinds)])
    shapes = {}
    for k in c._kids:                                     # RETAINED wrappers only
        if isinstance(k, QGraphicsPathItem) and k.data(2) == "marker" and \
                k.pen().color().name() == "#ffffff":     # the glyph itself, not its halo
            p = k.path()
            br = p.boundingRect()
            shapes[k.data(3)] = (round(br.width(), 1), round(br.height(), 1), p.elementCount())
    assert sorted(shapes) == sorted(kinds)
    assert len(set(shapes.values())) == len(kinds), shapes


def test_an_invalid_vertex_differs_by_shape_not_only_colour(app):
    """V13: a vertex above the horizon is a HOLLOW ring with a ✕ in its label."""
    from PySide6.QtWidgets import QGraphicsEllipseItem
    c, _, _ = _trace_canvas(app, pitch=20.0)                  # horizon y ~54
    c.set_floor([(130.0, 30.0), (254.0, 200.0), (364.0, 440.0)])
    dots = [k for k in c._kids if isinstance(k, QGraphicsEllipseItem)]
    styles = [d.brush().style() for d in dots]
    assert styles.count(Qt.BrushStyle.NoBrush) == 1 and styles.count(Qt.BrushStyle.SolidPattern) == 2
    texts = sorted(lab["text"].text() for lab in c._labels if "horizon" not in lab["text"].text())
    assert texts == ["0 ✕", "1", "2"]
