"""Probe 2: gestures through the viewport on a NATIVE hidden BackdropCanvas."""
import os, sys, tempfile
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"
os.environ.pop("QT_QPA_PLATFORM", None)
os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="bd_probe_")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")

from PySide6.QtCore import QPoint, QPointF, Qt, QEvent
from PySide6.QtGui import QPixmap, QMouseEvent, QKeyEvent, QContextMenuEvent
from PySide6.QtWidgets import QApplication, QMenu

app = QApplication.instance() or QApplication([])
from ff9mapkit import imagefield as IF
from ff9mapkit.scene import guide
from ff9mapkit.workspace.backdrop import BackdropCanvas
from ff9mapkit.workspace.shell import pick_palette

L, R, NB = Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton, Qt.MouseButton.NoButton
T = QEvent.Type


def settle(n=6):
    for _ in range(n):
        app.processEvents()


def mk(W=641, H=561):
    c = BackdropCanvas(pick_palette("dark"))
    c.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    pm = QPixmap(384 * 4, 448 * 4); pm.fill(Qt.GlobalColor.darkGray)
    cam = guide.make_camera(26.0, 3000.0, fov_x_deg=42.0)
    c.set_backdrop(pm, cam)
    c.resize(W, H); c.show(); settle(); c.viewport().repaint(); settle()
    return c, cam


def mouse(c, typ, pos, btn, btns):
    pos = QPointF(pos)
    ev = QMouseEvent(typ, pos, QPointF(c.viewport().mapToGlobal(pos.toPoint())), btn, btns,
                     Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(c.viewport(), ev)


def ctx(c, pos):
    ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, pos, c.viewport().mapToGlobal(pos))
    QApplication.sendEvent(c.viewport(), ev)


def wpx(c, cx, cy):
    p = c.viewportTransform().map(QPointF(cx, cy))
    return QPoint(round(p.x()), round(p.y()))


SQUARE = [(150.0, 250.0), (250.0, 250.0), (250.0, 350.0), (150.0, 350.0)]

print("=== A. sticky drag: buttonless moves after a lost release")
c, cam = mk()
calls = []
c.on_floor = lambda pts: calls.append(pts)
c.set_trace_mode(True); c.set_floor(SQUARE); settle()
p0 = wpx(c, *SQUARE[0])
mouse(c, T.MouseButtonPress, p0, L, L); settle()
print("  drag armed:", bool(c._drag), c._drag and c._drag.get("kind"))
mouse(c, T.MouseMove, p0 + QPoint(20, 10), NB, L); settle()
# The release is LOST (e.g. a modal menu / focus steal ate it). Buttonless hover moves:
mouse(c, T.MouseMove, p0 + QPoint(80, 60), NB, NB); settle()
print("  after a BUTTONLESS move: drag still live =", bool(c._drag), " anchor at",
      c._trace_items[0]["anchor"].pos().toTuple() if c._drag else None,
      " coords chip visible =", c._coords.isVisible())
# the user's next ordinary click somewhere else, to start panning
far = p0 + QPoint(150, 120)
mouse(c, T.MouseButtonPress, far, L, L); mouse(c, T.MouseButtonRelease, far, L, NB); settle()
print("  next click elsewhere committed:", calls[-1][0] if calls else None, " (vertex 0 was", SQUARE[0], ")")

print("=== B. Esc mid vertex drag")
c, cam = mk(); calls = []; c.on_floor = lambda pts: calls.append(pts)
c.set_trace_mode(True); c.set_floor(SQUARE); settle(); c.setFocus()
p0 = wpx(c, *SQUARE[1])
mouse(c, T.MouseButtonPress, p0, L, L); mouse(c, T.MouseMove, p0 + QPoint(40, 40), NB, L)
QApplication.sendEvent(c, QKeyEvent(T.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
print("  drag still live after Esc:", bool(c._drag))
mouse(c, T.MouseButtonRelease, p0 + QPoint(40, 40), L, NB); settle()
print("  commits after Esc+release:", len(calls))

print("=== C. double click in trace mode (two fast clicks)")
c, cam = mk(); calls = []; c.on_floor = lambda pts: calls.append(pts)
c.set_trace_mode(True); c.set_floor([]); settle()
q = wpx(c, 200, 330)
mouse(c, T.MouseButtonPress, q, L, L); mouse(c, T.MouseButtonRelease, q, L, NB)
q2 = q + QPoint(3, 0)
mouse(c, T.MouseButtonDblClick, q2, L, L); mouse(c, T.MouseButtonRelease, q2, L, NB); settle()
print("  vertices after press/release/dblclick/release:", len(c.floor()))

print("=== D. region mode: first corner of a NEW quad inside an existing region")
c, cam = mk()
c.set_region_mode(True)
quadw = [(-400.0, 700.0), (400.0, 700.0), (400.0, 1300.0), (-400.0, 1300.0)]
c.set_regions([{"i": 0, "quad": quadw, "label": "door0", "kind": "gateway", "warn": None}]); settle()
drawn, changed, refused = [], [], []
c.region_drawn.connect(drawn.append); c.region_changed.connect(lambda i, q: changed.append(q))
c.click_refused.connect(refused.append)
inside = wpx(c, *IF.world_to_click(cam, (0.0, 1000.0)))
mouse(c, T.MouseButtonPress, inside, L, L); mouse(c, T.MouseButtonRelease, inside, L, NB); settle()
print("  pending corners after a click inside region 0:", len(c._pending_region),
      " drawn", len(drawn), " changed", len(changed), " refused", refused)

print("=== E. region right-click (rotate) during a corner drag, then release")
c, cam = mk(); c.set_region_mode(True)
c.set_regions([{"i": 0, "quad": quadw, "label": "door0", "kind": "gateway", "warn": None}]); settle()
changed = []; c.region_changed.connect(lambda i, q: changed.append(q))
corner = wpx(c, *IF.world_to_click(cam, quadw[2]))
mouse(c, T.MouseButtonPress, corner, L, L); mouse(c, T.MouseMove, corner + QPoint(15, 10), NB, L)
orig_exec = QMenu.exec
QMenu.exec = lambda self, *a: [x for x in self.actions() if x.text().startswith("Walk-out")][0]
try:
    ctx(c, corner + QPoint(15, 10))
finally:
    QMenu.exec = orig_exec
mouse(c, T.MouseButtonRelease, corner + QPoint(15, 10), L, NB); settle()
print("  region_changed emissions for ONE gesture:", len(changed))
for q in changed:
    print("   ", [(round(x), round(z)) for x, z in q])

print("=== F. cursor-vs-press: cut-out furniture in REGION mode")
c, cam = mk(); c.set_region_mode(True)
pm = QPixmap(100, 80); pm.fill(Qt.GlobalColor.red)
c.set_cutouts([{"i": 0, "pixmap": pm, "rect": (40.0, 300.0, 60.0, 50.0), "contact": (70.0, 350.0),
                "label": "fg0", "bad": False, "locked": False}]); settle()
for it in c._scene.items():
    if it.data(0) == "cutoutimg" or it.data(2) == "cutoutpt":
        print("  ", it.data(0) or ("child of " + str(it.data(2))), "cursor:", it.cursor().shape() if it.hasCursor() else None)
moved = []; c.cutout_moved.connect(lambda *a: moved.append(a))
s = wpx(c, 70, 320)
mouse(c, T.MouseButtonPress, s, L, L); print("  press on the snip in region mode -> drag armed:", bool(c._drag))
mouse(c, T.MouseMove, s + QPoint(30, 0), NB, L); mouse(c, T.MouseButtonRelease, s + QPoint(30, 0), L, NB); settle()
print("  cutout_moved:", moved, " (the user saw the Move cursor)")
# PLACE mode as well
c.set_place_mode(True); settle()
for it in c._scene.items():
    if it.data(0) == "cutoutimg":
        print("  place mode cutoutimg cursor:", it.cursor().shape() if it.hasCursor() else None)

print("=== G. contact mode: a contact click on an existing snip's opaque body")
c, cam = mk(); c.set_contact_mode(True)
c.set_cutouts([{"i": 0, "pixmap": pm, "rect": (40.0, 300.0, 60.0, 50.0), "contact": (70.0, 350.0),
                "label": "fg0", "bad": False, "locked": False}]); settle()
got = []; c.contact_clicked.connect(lambda x, y: got.append((x, y)))
s = wpx(c, 60, 340)
mouse(c, T.MouseButtonPress, s, L, L); mouse(c, T.MouseButtonRelease, s, L, NB); settle()
print("  contact_clicked after a slop click on the snip body:", got)

print("=== H. horizon refusal hint + coords chip vs a mid-drag rebuild from a host signal")
c, cam = mk(); c.set_trace_mode(True); c.set_floor(SQUARE); settle()
p0 = wpx(c, *SQUARE[2])
mouse(c, T.MouseButtonPress, p0, L, L); mouse(c, T.MouseMove, p0 + QPoint(10, 10), NB, L)
c.set_markers([])        # any host feed mid-drag (e.g. a sibling refresh)
mouse(c, T.MouseMove, p0 + QPoint(30, 30), NB, L)
print("  drag survived a mid-gesture feed:", bool(c._drag), " (the press is now a pan?) dragMode",
      c.dragMode())
mouse(c, T.MouseButtonRelease, p0 + QPoint(30, 30), L, NB); settle()
print("  floor after release (vertex 2):", c.floor()[2])
