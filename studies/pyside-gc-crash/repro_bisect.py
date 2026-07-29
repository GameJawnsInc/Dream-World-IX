"""Delta-debugging variant of repro_scene_items_cursor_gc.py — env flags STRIP one element
each so the minimal trigger set can be found. Default (no flags) = the full firing mirror
with the fresh-wrapper sweep.

Flags (each 1 = REMOVE the element):
  NOVIEW        bare QGraphicsScene, no QGraphicsView/QLabels/show/processEvents
  NOANCHORFLAG  no ItemIgnoresTransformations on anchors
  NOMASK        no MaskShape on the snip pixmap
  NOCHILD       children stay TOP-LEVEL scene items (no setParentItem adoption)
  NOCURSOR      no setCursor anywhere AND the sweep skips cursor()/hasCursor()
  NOSWEEPCUR    setCursor stays, but the sweep reads only data()/parentItem()
  NOSWEEP       no fresh scene.items() sweeps at all
  NOPIX         no pixmap items (backdrop + cutout imgs skipped)
  NOTEXT        no QGraphicsSimpleTextItem children
  NOGC          no forced gc.collect loops (automatic GC only)
  ONESWEEP      sweep once per round instead of after every rebuild
"""

import faulthandler
import gc
import os

faulthandler.enable()
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt                      # noqa: E402
from PySide6.QtGui import (QBrush, QColor, QFont, QPainter, QPen,   # noqa: E402
                           QPixmap, QPolygonF, QTransform)
from PySide6.QtWidgets import (QApplication, QGraphicsPixmapItem,   # noqa: E402
                               QGraphicsScene, QGraphicsView, QLabel)

F = {k: os.environ.get(k, "0") == "1"
     for k in ("NOVIEW", "NOANCHORFLAG", "NOMASK", "NOCHILD", "NOCURSOR", "NOSWEEPCUR",
               "NOSWEEP", "NOPIX", "NOTEXT", "NOGC", "ONESWEEP")}
HORIZON_Y = 120.0
_HANDLE_R = 4.5


class Canvas:
    def __init__(self):
        if F["NOVIEW"]:
            self.view = None
            self._scene = QGraphicsScene()
        else:
            self.view = QGraphicsView()
            self._scene = QGraphicsScene(self.view)
            self.view.setScene(self._scene)
            self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            hint = QLabel("hint", self.view.viewport())
            hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self._hint = hint
        self._pixmap = None
        self._trace = []
        self._trace_mode = False
        self._contact_mode = False
        self._cutouts = []
        self._cutout_items = {}
        self._contact_items = {}
        self._trace_items = []
        self._kids = []

    def _adopt(self, item, parent):
        if not F["NOCHILD"]:
            item.setParentItem(parent)
        self._kids.append(item)
        return item

    def _grab(self, it):
        if not F["NOCURSOR"]:
            it.setCursor(Qt.CursorShape.SizeAllCursor)

    def set_backdrop(self, pm):
        self._pixmap = None if F["NOPIX"] else pm
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
        self._cutouts = [] if F["NOPIX"] else list(cutouts or [])
        self._rebuild()

    def commit_floor(self, pts):
        self._trace = [tuple(p) for p in pts]
        self._rebuild()

    def _text(self, s, anchor, color):
        if F["NOTEXT"]:
            return
        t = self._adopt(self._scene.addSimpleText(s), anchor)
        t.setFont(QFont("Segoe UI", 8))
        t.setBrush(QBrush(QColor(color)))
        t.setPos(6, -16)

    def _rebuild(self):
        sc = self._scene
        self._trace_items = []
        self._cutout_items = {}
        self._contact_items = {}
        self._kids = []
        sc.clear()
        w, h = 384.0, 448.0
        sc.setSceneRect(QRectF(0, 0, w, h))
        if self._pixmap is not None:
            item = sc.addPixmap(self._pixmap)
            item.setTransform(QTransform.fromScale(w / self._pixmap.width(),
                                                   h / self._pixmap.height()))
            item.setData(0, "backdrop")
        for c in self._cutouts:
            it = sc.addPixmap(c["pixmap"])
            it.setData(0, "cutoutimg")
            it.setData(1, c["i"])
            r = c.get("rect")
            if r is None:
                it.setTransform(QTransform.fromScale(w / c["pixmap"].width(),
                                                     h / c["pixmap"].height()))
                it.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            else:
                x, y, rw, rh = r
                it.setTransform(QTransform.fromScale(rw / c["pixmap"].width(),
                                                     rh / c["pixmap"].height()))
                it.setPos(x, y)
                if c.get("locked"):
                    it.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                else:
                    if not F["NOMASK"]:
                        it.setShapeMode(QGraphicsPixmapItem.ShapeMode.MaskShape)
                    self._grab(it)
                self._cutout_items[c["i"]] = it
        for c in self._cutouts:
            cx, cy = c["contact"]
            anchor = sc.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
            anchor.setPos(cx, cy)
            if not F["NOANCHORFLAG"]:
                anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
            anchor.setData(0, "cutoutpt")
            anchor.setData(1, c["i"])
            dia = QPolygonF([QPointF(0, -5), QPointF(5, 0), QPointF(0, 5), QPointF(-5, 0)])
            gl = self._adopt(sc.addPolygon(dia), anchor)
            gl.setPen(QPen(QColor("#d7a65f"), 1.6))
            gl.setBrush(QBrush(QColor("#d7a65f")))
            self._grab(gl)
            self._text(str(c.get("label", "")), anchor, "#d7a65f")
            self._contact_items[c["i"]] = anchor
        border = QPen(QColor("#3c3f52"), 1.0)
        border.setCosmetic(True)
        frame = sc.addRect(QRectF(0, 0, w, h), border)
        frame.setData(0, "frame")
        pen = QPen(QColor("#d7a65f"), 1.6)
        pen.setCosmetic(True)
        pen.setDashPattern([6, 4])
        line = sc.addLine(0, HORIZON_Y, w, HORIZON_Y, pen)
        line.setData(0, "horizon")
        anchor = sc.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
        anchor.setPos(6, HORIZON_Y)
        if not F["NOANCHORFLAG"]:
            anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
        anchor.setData(0, "horizonlabel")
        self._text("horizon — no floor above", anchor, "#d7a65f")
        if (self._trace_mode or self._contact_mode) and self._trace:
            pen = QPen(QColor("#61afef"), 1.6)
            pen.setCosmetic(True)
            pts = [QPointF(cx, cy) for cx, cy in self._trace]
            for a, b in zip(pts, pts[1:]):
                ln = sc.addLine(a.x(), a.y(), b.x(), b.y(), pen)
                ln.setData(0, "traceline")
            for i, (cx, cy) in enumerate(self._trace):
                anchor = sc.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
                anchor.setPos(cx, cy)
                if not F["NOANCHORFLAG"]:
                    anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
                anchor.setData(0, "tracept")
                anchor.setData(1, i)
                dot = self._adopt(
                    sc.addEllipse(-_HANDLE_R, -_HANDLE_R, 2 * _HANDLE_R, 2 * _HANDLE_R),
                    anchor)
                dot.setPen(QPen(QColor("#61afef"), 1.6))
                dot.setBrush(QBrush(QColor("#61afef")))
                self._text(str(i), anchor, "#61afef")
                if self._trace_mode:
                    self._grab(dot)
                self._trace_items.append({"anchor": anchor, "i": i})


def sweep(canvas, tag):
    if F["NOSWEEP"]:
        return []
    out = []
    for it in canvas._scene.items():
        p = it.parentItem()
        where = p if tag in ("tracept", "cutoutpt") else it
        if where is not None and where.data(0) == tag:
            if F["NOCURSOR"] or F["NOSWEEPCUR"]:
                out.append(None)
            else:
                out.append(it.cursor().shape() if it.hasCursor() else None)
    return out


def round_once():
    c = Canvas()
    pm = QPixmap(384, 448)
    pm.fill(Qt.GlobalColor.darkGray)
    c.set_backdrop(pm)
    c.set_trace_mode(True)
    if c.view is not None:
        c.view.resize(500, 560)
        c.view.show()
        QApplication.processEvents()
    c.commit_floor([(100.0, 300.0), (300.0, 300.0), (200.0, 430.0)])
    sweep(c, "tracept")
    pm2 = QPixmap(40, 30)
    pm2.fill(Qt.GlobalColor.red)
    c.set_cutouts([{"i": 0, "pixmap": pm2, "rect": (50.0, 250.0, 40.0, 30.0),
                    "contact": (70.0, 280.0), "label": "fg0", "locked": False},
                   {"i": 1, "pixmap": pm2, "rect": None, "contact": (200.0, 300.0),
                    "label": "fg1", "locked": True}])
    if not F["ONESWEEP"]:
        sweep(c, "cutoutimg")
        sweep(c, "cutoutpt")
    c.set_contact_mode(True)
    if not F["ONESWEEP"]:
        sweep(c, "tracept")
    return c


def main():
    rounds = int(os.environ.get("ROUNDS", "10"))
    gch = 0 if F["NOGC"] else int(os.environ.get("GCH", "5"))
    app = QApplication.instance() or QApplication([])
    parked = []
    for i in range(rounds):
        c = round_once()
        if c.view is not None:
            c.view.hide()
        parked.append(c)
        if not F["NOVIEW"]:
            QApplication.processEvents()
        for _ in range(gch):
            gc.collect()
        print(f"round {i + 1}/{rounds} ok", flush=True)
    for _ in range(gch):
        gc.collect()
    print("ALL ROUNDS DONE", flush=True)


if __name__ == "__main__":
    main()
