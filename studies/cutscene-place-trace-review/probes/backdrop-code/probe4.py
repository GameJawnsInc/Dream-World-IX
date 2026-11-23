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
import tempfile, pathlib
d = pathlib.Path(tempfile.mkdtemp(prefix="bd_art_"))
img = QPixmap(768, 896); img.fill(Qt.GlobalColor.darkGray)
p2 = d / "room@2x.png"; img.save(str(p2))
for path in (d / "plain.png", p2):
    if not path.exists(): img.save(str(path))
    pm = QPixmap(str(path))
    c, cam = mk()
    c.set_backdrop(pm, cam); settle()
    it = [i for i in c._scene.items() if i.data(0) == "backdrop"][0]
    r = it.sceneBoundingRect()
    print(path.name, "dpr", pm.devicePixelRatio(), "w", pm.width(), "-> art scene rect", (r.x(), r.y(), r.width(), r.height()), "frame", c._scene.sceneRect().size().toTuple())
# snip cutout with dpr 2
pm = QPixmap(str(p2))
c, cam = mk(); c.set_trace_mode(True)
c.set_cutouts([{"i": 0, "pixmap": pm, "rect": (40.0, 300.0, 60.0, 50.0), "contact": (70.0, 350.0), "label": "fg0", "bad": False, "locked": False}]); settle()
it = [i for i in c._scene.items() if i.data(0) == "cutoutimg"][0]
print("snip @2x rect want (40,300,60,50) got", it.sceneBoundingRect().getRect())
