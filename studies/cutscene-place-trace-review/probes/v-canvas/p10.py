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
from ff9mapkit.scene import cam as _cam
c, cam = mk(); c.set_region_mode(True)
print("cam C", _cam.decompose(cam)["C"])
print("bottom-centre ground", IF.click_to_world(cam, (192, 447)))
quadw = [(-300.0, -600.0), (300.0, -600.0), (300.0, 1500.0), (-300.0, 1500.0)]
c.set_regions([{"i": 0, "quad": quadw, "label": "z", "kind": "event", "warn": None}]); settle()
got = []; c.region_changed.connect(lambda i, q: got.append(q))
grab = IF.world_to_click(cam, (0.0, 1400.0)); print("grab px", grab)
gp = wpx(c, *grab)
mouse(c, T.MouseButtonPress, gp, L, L); print("drag", c._drag and c._drag["kind"])
tgt = wpx(c, 192, 446)
mouse(c, T.MouseMove, tgt, NB, L); mouse(c, T.MouseButtonRelease, tgt, L, NB); settle()
for q in got:
    print("emitted", [(round(x), round(z)) for x, z in q])
    for w in q:
        try: IF.world_to_click(cam, w); print("  ok", w)
        except IF.ImageFieldError as e: print("  REFUSED", w, str(e)[:60])
print("law items visible:", [it.isVisible() for it in c._region_law_items.get(0, [])])
