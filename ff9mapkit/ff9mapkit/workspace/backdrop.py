"""The click-authoring backdrop — Rung 0 of ``studies/click-authoring/PLAN.md``.

:class:`BackdropCanvas` shows a field's background ART under its CAMERA and turns clicks into
exact world floor coordinates through the proven plane homography.

THE FRAME LAW (HOP 1 — widget px -> canvas px): the graphics SCENE is the logical painted
canvas — ``sceneRect = (0, 0, range.w, range.h)``, 384x448 for a single screen. The art
pixmap, whatever its file resolution (painted layers ship at 4x; the retired HTML tracer
displayed at 2x), is transformed to fill exactly that rect at ``set_backdrop`` time, and
display zoom lives in the view transform. So widget->canvas is ``viewportTransform`` and
NOTHING else — the three coordinate scales (logical / display / layer) never meet a call site.

HOP 2 (canvas px -> world) is :func:`ff9mapkit.imagefield.click_to_world`: the ONE
conversion, horizon-guarded (a click at/above the horizon REFUSES — ``click_refused`` — never
clamps to absurd depth) and self-checked (every accepted click re-projects through
``cam.to_canvas`` and must land back on the click: the inv3-not-transpose tripwire).

View grammar = the atlas family's (Ctrl+scroll zoom / Ctrl+0 fit / Ctrl+1 1:1, pan by drag);
a press-release pair that travels no further than the slop is a CLICK, so panning and
placement share the left button without a mode. The canvas is painted, so CALIBRE reaches it
via ``set_scale`` and themes via ``retheme`` (the mapview rule).
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QTransform
from PySide6.QtWidgets import QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView, QLabel

from .. import imagefield
from ..scene import cam as _cam

_ZOOM_MIN, _ZOOM_MAX = 0.1, 8.0
_CLICK_SLOP_PX = 4          # press->release travel at/under this = a click, past it = a pan


class BackdropCanvas(QGraphicsView):
    """A background pixmap + a camera; clicks become world floor points.

    Rung 0 is the primitive only: it emits, it never writes — hosts (the tracing and
    placement rungs) own every document mutation."""

    floor_clicked = Signal(float, float)     # world (x, z) of an accepted left-click
    click_refused = Signal(str)              # why a click produced no floor point

    def __init__(self, palette, *, scale=100):
        super().__init__()
        self.pal = palette
        self._scale = scale if scale in range(50, 301) else 100
        self._cam = None
        self._pixmap = None
        self._zoom = 1.0
        self._fit_pending = False
        self._press_pos = None
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor(palette["surface"]))
        self.setAccessibleName("Field backdrop")
        self.setAccessibleDescription(
            "The field's background art under its camera: click the floor to get an exact "
            "world position; the dashed line is the camera's horizon, above which no floor exists")
        self._hint = QLabel("Ctrl+scroll zooms · Ctrl+0 fits · click the floor", self.viewport())
        self._hint.setObjectName("backdropHint")   # selector-scoped (the round-9 census law)
        self._hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._style_hint()

    # -- text + geometry (CALIBRE) --
    def _font(self, pt, bold=False):
        weight = QFont.Weight.DemiBold if bold else QFont.Weight.Normal
        return QFont("Segoe UI", max(1, round(pt * self._scale / 100)), weight)

    def set_scale(self, pct):
        pct = pct if pct in range(50, 301) else 100
        if pct == self._scale:
            return
        self._scale = pct
        self._style_hint()
        self._rebuild()

    def retheme(self, palette):
        self.pal = palette
        self.setBackgroundBrush(QColor(palette["surface"]))
        self._style_hint()
        self._rebuild()

    def _style_hint(self):
        surf = QColor(self.pal["surface"])
        self._hint.setFont(self._font(8))
        self._hint.setStyleSheet(
            "QLabel#backdropHint {"
            f"color: {self.pal['muted']};"
            f"background: rgba({surf.red()},{surf.green()},{surf.blue()},0.86);"
            "border-radius: 9px; padding: 2px 9px; }")
        self._place_hint()

    def _place_hint(self):
        self._hint.adjustSize()                    # measure AFTER polish -- construction adjustSize lies
        vp = self.viewport()
        self._hint.move(vp.width() - self._hint.width() - 10,
                        vp.height() - self._hint.height() - 8)

    # -- public: content --
    def set_backdrop(self, pixmap, cam, *, refit=True):
        """Feed the surface its two inputs (either may be None: art-only preview, or a bare
        camera frame). ``refit`` on a FIELD change only — a same-field re-render keeps the
        user's zoom/pan (the map's own contract)."""
        self._pixmap = pixmap
        self._cam = cam
        if refit:
            self.resetTransform()
            self._zoom = 1.0
            self._fit_pending = True
        self._rebuild()

    def camera(self):
        return self._cam

    # -- public: THE two conversions --
    def click_to_world(self, pt) -> tuple:
        """Widget/viewport point -> world floor (x, z). HOP 1 is the view transform alone;
        HOP 2 is the imagefield conversion (horizon guard + round-trip self-check). Raises
        :class:`ff9mapkit.imagefield.ImageFieldError` when there is no floor under the click."""
        if self._cam is None:
            raise imagefield.ImageFieldError("this backdrop has no camera — clicks cannot "
                                             "resolve to world coordinates")
        c = self._widget_to_canvas(pt)
        return imagefield.click_to_world(self._cam, (c.x(), c.y()))

    def world_to_click(self, p) -> QPointF:
        """World floor (x, z) -> the widget/viewport point it appears under (the inverse
        hop pair, same two laws)."""
        if self._cam is None:
            raise imagefield.ImageFieldError("this backdrop has no camera — world points "
                                             "cannot resolve to widget coordinates")
        cx, cy = imagefield.world_to_click(self._cam, (p[0], p[1]))
        return self.viewportTransform().map(QPointF(cx, cy))

    def _widget_to_canvas(self, pt) -> QPointF:
        """HOP 1, the ONLY widget->canvas conversion: the view transform, float-exact
        (``mapToScene`` would quantize to integer px first)."""
        inv, _ = self.viewportTransform().inverted()
        return inv.map(QPointF(pt))

    # -- the canvas frame --
    def _frame_wh(self):
        if self._cam is not None and self._cam.range and self._cam.range[0]:
            return int(self._cam.range[0]), int(self._cam.range[1])
        if self._pixmap is not None and not self._pixmap.isNull():
            return self._pixmap.width(), self._pixmap.height()
        return imagefield.CANVAS_W, imagefield.CANVAS_H

    def _rebuild(self):
        sc, pal = self._scene, self.pal
        sc.clear()
        w, h = self._frame_wh()
        sc.setSceneRect(QRectF(0, 0, w, h))
        if self._pixmap is not None and not self._pixmap.isNull():
            item = sc.addPixmap(self._pixmap)      # whatever its resolution, it FILLS the frame
            item.setTransform(QTransform.fromScale(w / self._pixmap.width(),
                                                   h / self._pixmap.height()))
            item.setData(0, "backdrop")
        border = QPen(QColor(pal["border"]), 1.0)
        border.setCosmetic(True)
        frame = sc.addRect(QRectF(0, 0, w, h), border)
        frame.setData(0, "frame")
        self._draw_horizon(w, h)

    def _draw_horizon(self, w, h):
        """The refusal boundary, visible: a dashed line at ``horizon_canvas_y`` with a
        screen-fixed label. Off-frame horizons draw nothing (a horizon above the frame means
        every canvas row is floor; below it, none is — the guard still refuses either way)."""
        if self._cam is None:
            return
        hy = _cam.horizon_canvas_y(self._cam)
        if not 0 <= hy < h:
            return
        pen = QPen(QColor(self.pal["warn"]), 1.6)
        pen.setCosmetic(True)                      # must survive fit zoom (the atlas lesson)
        pen.setDashPattern([6, 4])
        line = self._scene.addLine(0, hy, w, hy, pen)
        line.setData(0, "horizon")
        anchor = self._scene.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
        anchor.setPos(6, hy)
        anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
        anchor.setData(0, "horizonlabel")
        t = QGraphicsSimpleTextItem("horizon — no floor above", anchor)
        t.setFont(self._font(8))
        t.setBrush(QColor(self.pal["warn"]))
        t.setPos(0, -14)                           # screen px, riding the zoom-immune anchor

    # -- view grammar (the atlas family's) --
    def _fit(self):
        r = self._scene.sceneRect()
        if r.isEmpty():
            return
        vw, vh = max(1, self.viewport().width()), max(1, self.viewport().height())
        z = min(vw / max(1.0, r.width()), vh / max(1.0, r.height())) * 0.97
        z = max(_ZOOM_MIN, min(_ZOOM_MAX, z))
        self.resetTransform()
        self.scale(z, z)
        self._zoom = z
        self.centerOn(r.center())

    def paintEvent(self, ev):                      # noqa: N802 (Qt override)
        if self._fit_pending:                      # deferred to the first REAL paint: at set time
            self._fit_pending = False              # the tab may be hidden, the viewport stale
            self._fit()
        super().paintEvent(ev)

    def resizeEvent(self, ev):                     # noqa: N802 (Qt override)
        super().resizeEvent(ev)
        self._place_hint()

    def wheelEvent(self, event):                   # noqa: N802 (Qt override)
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            f = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            z = max(_ZOOM_MIN, min(_ZOOM_MAX, self._zoom * f))
            if z != self._zoom:
                self.scale(z / self._zoom, z / self._zoom)
                self._zoom = z
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event):                # noqa: N802 (Qt override)
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_0:
                self._fit()
                event.accept()
                return
            if event.key() == Qt.Key.Key_1:
                self.resetTransform()
                self._zoom = 1.0
                event.accept()
                return
        super().keyPressEvent(event)

    # -- click vs pan: slop, not modes --
    def mousePressEvent(self, event):              # noqa: N802 (Qt override)
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position()
        super().mousePressEvent(event)             # the pan machinery still runs

    def mouseReleaseEvent(self, event):            # noqa: N802 (Qt override)
        press, self._press_pos = self._press_pos, None
        super().mouseReleaseEvent(event)
        if (press is None or event.button() != Qt.MouseButton.LeftButton
                or self._cam is None):
            return
        travel = (event.position() - press).manhattanLength()
        if travel > _CLICK_SLOP_PX:
            return                                 # it was a pan
        try:
            x, z = self.click_to_world(event.position())
        except imagefield.ImageFieldError as e:
            self.click_refused.emit(str(e))
            return
        self.floor_clicked.emit(x, z)
