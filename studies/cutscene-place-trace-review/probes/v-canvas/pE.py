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
quadw = [(-400.0, 700.0), (400.0, 700.0), (400.0, 1300.0), (-400.0, 1300.0)]
c, cam = mk(); c.set_region_mode(True)
c.set_regions([{"i": 0, "quad": quadw, "label": "door0", "kind": "gateway", "warn": None}]); settle()
changed = []; c.region_changed.connect(lambda i, q: changed.append(("emit", q)))
corner = wpx(c, *IF.world_to_click(cam, quadw[2]))
mouse(c, T.MouseButtonPress, corner, L, L); mouse(c, T.MouseMove, corner + QPoint(15, 10), NB, L)
print("drag", c._drag and c._drag["kind"])
seen = []
orig_exec = QMenu.exec
def fake(self, *a):
    seen.append([x.text() for x in self.actions()])
    return [x for x in self.actions() if x.text().startswith("Walk-out")][0]
QMenu.exec = fake
pos = corner + QPoint(15, 10)
print("items at pos", [(it.data(0), it.data(2)) for it in c.items(pos)])
c.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Reason.Mouse, pos, c.viewport().mapToGlobal(pos)))
QMenu.exec = orig_exec
print("menu seen", seen, "changed after ctx", len(changed), "drag still", bool(c._drag))
mouse(c, T.MouseButtonRelease, pos, L, NB); settle()
for e in changed: print([(round(x), round(z)) for x, z in e[1]])
