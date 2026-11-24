"""Probe 1: view grammar + hover + hint pinning on a NATIVE hidden BackdropCanvas."""
import os, sys, tempfile
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"
os.environ.pop("QT_QPA_PLATFORM", None)
os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="bd_probe_")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")

from PySide6.QtCore import QPoint, QPointF, Qt, QEvent
from PySide6.QtGui import QPixmap, QWheelEvent, QMouseEvent, QKeyEvent
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])
print("platform", app.platformName())
from ff9mapkit.scene import guide
from ff9mapkit.workspace.backdrop import BackdropCanvas
from ff9mapkit.workspace.shell import pick_palette


def settle(n=6):
    for _ in range(n):
        app.processEvents()


def mk(w, h):
    c = BackdropCanvas(pick_palette("dark"))
    c.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    pm = QPixmap(384 * 4, 448 * 4); pm.fill(Qt.GlobalColor.darkGray)
    cam = guide.make_camera(26.0, 3000.0, fov_x_deg=42.0)
    c.set_backdrop(pm, cam)
    c.resize(w, h)
    c.show(); settle()
    c.viewport().repaint(); settle()
    return c


def state(c, tag):
    t = c.viewportTransform()
    vp = c.viewport()
    hb, vb = c.horizontalScrollBar(), c.verticalScrollBar()
    hint = c._hint.geometry()
    want = (vp.width() - c._hint.width() - 10, vp.height() - c._hint.height() - 8)
    print(f"  [{tag}] vp={vp.width()}x{vp.height()} m11={t.m11():.5f} dx={t.dx():.3f} dy={t.dy():.3f} "
          f"zoom={c._zoom:.5f} hbar={hb.isVisible()}({hb.minimum()}..{hb.maximum()}) "
          f"vbar={vb.isVisible()}({vb.minimum()}..{vb.maximum()}) hint=({hint.x()},{hint.y()}) want={want}")


def wheel(c, pos, dy, dx=0, mods=Qt.KeyboardModifier.ControlModifier, pixel=None):
    gp = c.viewport().mapToGlobal(pos)
    ev = QWheelEvent(QPointF(pos), QPointF(gp), pixel or QPoint(0, 0), QPoint(dx, dy),
                     Qt.MouseButton.NoButton, mods, Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(c.viewport(), ev)


def mouse(c, typ, pos, btn, btns, mods=Qt.KeyboardModifier.NoModifier):
    gp = c.viewport().mapToGlobal(pos)
    ev = QMouseEvent(typ, QPointF(pos), QPointF(gp), btn, btns, mods)
    QApplication.sendEvent(c.viewport(), ev)


def key(c, k, mods=Qt.KeyboardModifier.NoModifier):
    QApplication.sendEvent(c, QKeyEvent(QEvent.Type.KeyPress, k, mods))


for (W, H) in ((641, 561), (640, 560)):
    print(f"=== window {W}x{H}")
    c = mk(W, H)
    print("  viewport mouseTracking:", c.viewport().hasMouseTracking(), " view:", c.hasMouseTracking())
    state(c, "after first paint fit")
    for k in range(5):
        key(c, Qt.Key.Key_0, Qt.KeyboardModifier.ControlModifier); settle()
    state(c, "after 5x Ctrl+0")
    for k in range(5):
        c._rebuild(); settle()
    state(c, "after 5 rebuilds")
    # zoom in at a corner point
    p = QPoint(60, 60)
    mouse(c, QEvent.Type.MouseMove, p, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton); settle()
    before = c._widget_to_canvas(QPointF(p))
    wheel(c, p, 120); settle()
    after = c._widget_to_canvas(QPointF(p))
    print(f"  anchor under mouse: canvas@cursor before=({before.x():.2f},{before.y():.2f}) after=({after.x():.2f},{after.y():.2f})")
    state(c, "after ctrl+wheel in")
    for _ in range(6):
        wheel(c, p, 120); settle()
    state(c, "after 7 ctrl+wheel in (hint pinned?)")
    # pan via scrollbars
    c.horizontalScrollBar().setValue(c.horizontalScrollBar().maximum()); settle()
    c.verticalScrollBar().setValue(c.verticalScrollBar().maximum()); settle()
    state(c, "after scroll to max")
    key(c, Qt.Key.Key_0, Qt.KeyboardModifier.ControlModifier); settle()
    state(c, "after Ctrl+0 from zoomed")
    # horizontal-only Ctrl wheel (trackpad sideways / tilt wheel)
    z0 = c._zoom
    wheel(c, p, 0, dx=120); settle()
    print(f"  ctrl + HORIZONTAL wheel: zoom {z0:.4f} -> {c._zoom:.4f}")
    # high-res wheel: 8 notches of 15 = one 120 detent
    z0 = c._zoom
    for _ in range(8):
        wheel(c, p, 15); settle()
    print(f"  ctrl + 8x15 (one physical detent on a hi-res wheel): zoom {z0:.4f} -> {c._zoom:.4f} (x{c._zoom/z0:.3f}; a 120 detent is x1.15)")
    key(c, Qt.Key.Key_0, Qt.KeyboardModifier.ControlModifier); settle()
    state(c, "fit")
    c.resize(W - 200, H - 150); settle(); c.viewport().repaint(); settle()
    state(c, "after shrink resize (no refit?)")
    c.resize(W + 300, H + 200); settle(); c.viewport().repaint(); settle()
    state(c, "after grow resize")
    # Ctrl+1 then hint
    key(c, Qt.Key.Key_1, Qt.KeyboardModifier.ControlModifier); settle()
    state(c, "after Ctrl+1")
    # focus policy
    print("  focusPolicy:", c.focusPolicy())
    c.close(); c.deleteLater(); settle()
