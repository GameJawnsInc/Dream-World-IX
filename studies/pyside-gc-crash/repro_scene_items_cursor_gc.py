"""Minimal PURE-PySide6 reproducer for the Workspace GC access violation (THE GC-CHILD LAW,
layer 2: the fresh-retrieval-wrapper flake).

Mirrors test_workspace_backdrop.py::test_grabbable_things_carry_the_move_cursor at its PRE-FIX
shape (commit 9ebfbd2f) with zero ff9mapkit imports: a QGraphicsView subclass whose scene is
rebuilt (scene.clear() + re-add) five times per round — backdrop pixmap, MaskShape snip pixmaps
carrying SizeAllCursor, ItemIgnoresTransformations anchor rects with scene-created-then-
setParentItem children (ellipse dots, polygon diamonds, simple-text labels), cosmetic/dashed
pens, tooltips — then swept via FRESH scene.items() retrieval wrappers reading data()/
parentItem()/cursor()/hasCursor().

Observed upstream: Python 3.14.4 + PySide6 6.11.1 (offscreen), the suite intermittently died
with a native access violation during garbage collection; the fresh-wrapper sweep flaked
~1-in-3 while the retained-wrapper rewrite was 8/8 deterministic, with widget parking and every
ownership fix already in place.

Knobs (env):
  ROUNDS   iterations per process                      (default 40)
  SWEEP    fresh | retained                            (default fresh)   <- the suspect axis
  PARK     1 keep canvases alive (post-fix parking) |
           0 drop each canvas to GC (pre-parking)      (default 1)
  GCH      gc.collect() iterations between rounds and at exit — pytest's
           gc_collect_harder constant                  (default 5)
  AGGRO    1 = gc.set_threshold(50, 3, 2) to make the AUTOMATIC collector fire
           mid-sweep (the suite's mid-run GC analog)   (default 0)

Exit: prints one line per round; an access violation kills the process (Windows exit
0xC0000005 = 3221225477). "ALL ROUNDS DONE" then interpreter shutdown mirrors pytest's
session end (QApplication never torn down explicitly).
"""

import gc
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt                      # noqa: E402
from PySide6.QtGui import (QBrush, QColor, QFont, QPainter, QPen,   # noqa: E402
                           QPixmap, QPolygonF, QTransform)
from PySide6.QtWidgets import (QApplication, QGraphicsEllipseItem,  # noqa: E402
                               QGraphicsPixmapItem, QGraphicsPolygonItem,
                               QGraphicsScene, QGraphicsView, QLabel)

HORIZON_Y = 120.0        # stands in for guide.make_camera(pitch=10).horizon_canvas_y
_HANDLE_R = 4.5


def mark_grabbable(*items):
    for it in items:
        it.setCursor(Qt.CursorShape.SizeAllCursor)


class Canvas(QGraphicsView):
    """BackdropCanvas's Qt object graph, math stripped (the geometry values are irrelevant to
    GC; the item classes, ownership moves, and rebuild cadence are the mirror)."""

    def __init__(self):
        super().__init__()
        self._pixmap = None
        self._trace = []
        self._trace_mode = False
        self._contact_mode = False
        self._cutouts = []
        self._trace_items = []
        self._cutout_items = {}
        self._contact_items = {}
        self._kids = []                  # strong refs to child items (the app-side belt)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor("#1e1f26"))
        self._hint = QLabel("Ctrl+scroll zooms · Ctrl+0 fits · click the floor", self.viewport())
        self._hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._coords = QLabel("", self.viewport())
        self._coords.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._coords.hide()
        sheet = ("QLabel { color: #9a9db1; background: rgba(30,31,38,0.86);"
                 " border-radius: 9px; padding: 2px 9px; }")
        for lab in (self._hint, self._coords):
            lab.setFont(self._font(8))
            lab.setStyleSheet(sheet)

    def _font(self, pt):
        return QFont("Segoe UI", pt)

    def _child(self, item, parent):
        """Adopt a SCENE-CREATED item as parent's child (the shipped ownership pattern)."""
        item.setParentItem(parent)
        self._kids.append(item)
        return item

    # -- the public surface the failing test drives --
    def set_backdrop(self, pm):
        self._pixmap = pm
        self.resetTransform()
        self._rebuild()

    def set_trace_mode(self, on):
        self._trace_mode = bool(on)
        if on:
            self._contact_mode = False
        self._rebuild()

    def set_contact_mode(self, on):
        self._contact_mode = bool(on)
        if on:
            self._trace_mode = False
        self._rebuild()

    def set_cutouts(self, cutouts):
        self._cutouts = list(cutouts or [])
        self._rebuild()

    def commit_floor(self, pts):
        self._trace = [tuple(p) for p in pts]
        self._rebuild()

    # -- the rebuild: scene.clear() then the full item zoo, same order as the app --
    def _rebuild(self):
        sc = self._scene
        self._trace_items = []
        self._cutout_items = {}
        self._contact_items = {}
        self._kids = []                            # the old scene's children die WITH the clear
        self._coords.hide()
        sc.clear()
        w, h = 384.0, 448.0
        sc.setSceneRect(QRectF(0, 0, w, h))
        if self._pixmap is not None and not self._pixmap.isNull():
            item = sc.addPixmap(self._pixmap)
            item.setTransform(QTransform.fromScale(w / self._pixmap.width(),
                                                   h / self._pixmap.height()))
            item.setData(0, "backdrop")
        self._draw_cutouts(w, h)
        border = QPen(QColor("#3c3f52"), 1.0)
        border.setCosmetic(True)
        frame = sc.addRect(QRectF(0, 0, w, h), border)
        frame.setData(0, "frame")
        self._draw_horizon(w, h)
        self._draw_trace()

    def _draw_horizon(self, w, h):
        pen = QPen(QColor("#d7a65f"), 1.6)
        pen.setCosmetic(True)
        pen.setDashPattern([6, 4])
        line = self._scene.addLine(0, HORIZON_Y, w, HORIZON_Y, pen)
        line.setData(0, "horizon")
        anchor = self._scene.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
        anchor.setPos(6, HORIZON_Y)
        anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
        anchor.setData(0, "horizonlabel")
        t = self._child(self._scene.addSimpleText("horizon — no floor above"), anchor)
        t.setFont(self._font(8))
        t.setBrush(QColor("#d7a65f"))
        t.setPos(0, -14)

    def _draw_cutouts(self, w, h):
        for c in self._cutouts:
            pm = c.get("pixmap")
            if pm is None or pm.isNull():
                continue
            it = self._scene.addPixmap(pm)
            it.setData(0, "cutoutimg")
            it.setData(1, c["i"])
            r = c.get("rect")
            if r is None:                          # full-frame: registered art, inert
                it.setTransform(QTransform.fromScale(w / pm.width(), h / pm.height()))
                it.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            else:
                x, y, rw, rh = r
                it.setTransform(QTransform.fromScale(rw / pm.width(), rh / pm.height()))
                it.setPos(x, y)
                if c.get("locked"):
                    it.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                else:
                    it.setShapeMode(QGraphicsPixmapItem.ShapeMode.MaskShape)
                    mark_grabbable(it)
                self._cutout_items[c["i"]] = it
        for c in self._cutouts:
            cx, cy = c["contact"]
            color = QColor("#e06c75" if c.get("bad") else "#d7a65f")
            anchor = self._scene.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
            anchor.setPos(cx, cy)
            anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
            anchor.setData(0, "cutoutpt")
            anchor.setData(1, c["i"])
            dia = QPolygonF([QPointF(0, -5), QPointF(5, 0), QPointF(0, 5), QPointF(-5, 0)])
            gl = self._child(self._scene.addPolygon(dia), anchor)
            gl.setPen(QPen(color, 1.6))
            gl.setBrush(QBrush(color))
            mark_grabbable(gl)
            if c.get("label"):
                t = self._child(self._scene.addSimpleText(str(c["label"])), anchor)
                t.setFont(self._font(8))
                t.setBrush(QBrush(color))
                t.setPos(7, -16)
            anchor.setToolTip("the floor-contact anchor — occlusion flips here; drag to re-anchor")
            self._contact_items[c["i"]] = anchor

    def _draw_trace(self):
        self._trace_items = []
        if not (self._trace_mode or self._contact_mode) or not self._trace:
            return
        sc = self._scene
        pen = QPen(QColor("#61afef"), 1.6)
        pen.setCosmetic(True)
        pts = [QPointF(cx, cy) for cx, cy in self._trace]
        for a, b in zip(pts, pts[1:]):
            ln = sc.addLine(a.x(), a.y(), b.x(), b.y(), pen)
            ln.setData(0, "traceline")
        if len(pts) > 2:
            dash = QPen(pen)
            dash.setDashPattern([4, 4])
            ln = sc.addLine(pts[-1].x(), pts[-1].y(), pts[0].x(), pts[0].y(), dash)
            ln.setData(0, "traceline")
        # the collision-outset ring (a dashed cosmetic polygon, trivially offset)
        open_pen = QPen(QColor("#9a9db1"), 1.2)
        open_pen.setCosmetic(True)
        open_pen.setDashPattern([2, 3])
        cx0 = sum(p.x() for p in pts) / len(pts)
        cy0 = sum(p.y() for p in pts) / len(pts)
        ring = [QPointF(cx0 + (p.x() - cx0) * 1.12, cy0 + (p.y() - cy0) * 1.12) for p in pts]
        outset = sc.addPolygon(QPolygonF(ring), open_pen)
        outset.setData(0, "outset")
        outset.setToolTip("+48u collision outset — the walkmesh edge the build emits")
        for i, (cx, cy) in enumerate(self._trace):
            anchor = sc.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
            anchor.setPos(cx, cy)
            anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
            anchor.setData(0, "tracept")
            anchor.setData(1, i)
            dot = self._child(
                sc.addEllipse(-_HANDLE_R, -_HANDLE_R, 2 * _HANDLE_R, 2 * _HANDLE_R), anchor)
            dot.setPen(QPen(QColor("#61afef"), 1.6))
            dot.setBrush(QBrush(QColor("#61afef")))
            t = self._child(sc.addSimpleText(str(i)), anchor)
            t.setFont(self._font(8))
            t.setBrush(QBrush(QColor("#61afef")))
            t.setPos(6, -16)
            if self._trace_mode:
                mark_grabbable(dot)
            self._trace_items.append({"anchor": anchor, "i": i})


# -- the PRE-FIX test body, verbatim shape ------------------------------------------------

def fresh_cursors(canvas, tag, cls=None):
    """The suspect: FRESH scene.items() retrieval wrappers + parentItem()/data()/cursor()."""
    out = []
    for it in canvas._scene.items():
        p = it.parentItem()
        where = p if tag in ("tracept", "cutoutpt") else it
        if (where is not None and where.data(0) == tag
                and (cls is None or isinstance(it, cls))):
            out.append(it.cursor().shape() if it.hasCursor() else None)
    return out


def retained_cursors(canvas, cls):
    """The control: the post-fix retained-wrapper read (the app's own _kids)."""
    return [(k.cursor().shape() if k.hasCursor() else None)
            for k in canvas._kids if isinstance(k, cls)]


def round_once(sweep):
    c = Canvas()
    pm = QPixmap(384, 448)
    pm.fill(Qt.GlobalColor.darkGray)
    c.set_backdrop(pm)
    c.set_trace_mode(True)
    c.resize(500, 560)
    c.show()
    QApplication.processEvents()
    c.commit_floor([(100.0, 300.0), (300.0, 300.0), (200.0, 430.0)])
    if sweep == "fresh":
        dots = fresh_cursors(c, "tracept", QGraphicsEllipseItem)
    else:
        dots = retained_cursors(c, QGraphicsEllipseItem)
    assert dots and all(s == Qt.CursorShape.SizeAllCursor for s in dots), dots
    pm2 = QPixmap(40, 30)
    pm2.fill(Qt.GlobalColor.red)
    c.set_cutouts([{"i": 0, "pixmap": pm2, "rect": (50.0, 250.0, 40.0, 30.0),
                    "contact": (70.0, 280.0), "label": "fg0", "bad": False, "locked": False},
                   {"i": 1, "pixmap": pm2, "rect": None, "contact": (200.0, 300.0),
                    "label": "fg1", "bad": False, "locked": True}])
    snip = c._cutout_items[0]
    assert snip.hasCursor() and snip.cursor().shape() == Qt.CursorShape.SizeAllCursor
    if sweep == "fresh":
        imgs = {it.data(1): it.hasCursor() for it in c._scene.items()
                if it.data(0) == "cutoutimg"}
        assert imgs == {0: True, 1: False}, imgs
        assert Qt.CursorShape.SizeAllCursor in fresh_cursors(c, "cutoutpt")
        glyphs = fresh_cursors(c, "cutoutpt", QGraphicsPolygonItem)
    else:
        glyphs = retained_cursors(c, QGraphicsPolygonItem)
    assert Qt.CursorShape.SizeAllCursor in glyphs, glyphs
    c.set_contact_mode(True)
    if sweep == "fresh":
        assert fresh_cursors(c, "tracept", QGraphicsEllipseItem) == [None, None, None]
    else:
        assert retained_cursors(c, QGraphicsEllipseItem) == [None, None, None]
    return c


def main():
    rounds = int(os.environ.get("ROUNDS", "40"))
    sweep = os.environ.get("SWEEP", "fresh")
    park = os.environ.get("PARK", "1") == "1"
    gch = int(os.environ.get("GCH", "5"))
    if os.environ.get("AGGRO", "0") == "1":
        gc.set_threshold(50, 3, 2)
    app = QApplication.instance() or QApplication([])
    parked = []
    for i in range(rounds):
        c = round_once(sweep)
        if park:
            c.hide()
            parked.append(c)                       # conftest.qt_drain's keep-alive analog
        else:
            del c                                  # pre-parking: the graph dies under GC
        QApplication.processEvents()
        for _ in range(gch):                       # pytest gc_collect_harder(5)
            gc.collect()
        print(f"round {i + 1}/{rounds} ok", flush=True)
    for _ in range(gch):                           # session-end cleanup()'s forced pass
        gc.collect()
    print("ALL ROUNDS DONE", flush=True)
    # No app teardown on purpose: pytest never destroys the QApplication either; interpreter
    # shutdown now finalizes parked widgets + wrappers in whatever order — the crash window.


if __name__ == "__main__":
    main()
