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

Rung 1 adds TRACE mode: the floor polygon authored directly on the art — click to append a
vertex (below the horizon only), drag a handle to move it, right-click to delete, with the
live +48u collision-outset preview derived through the same conversions. The canvas never
touches a document: a completed gesture ends in ONE ``on_floor(points)`` callback and the
host owns the write + undo (the StageCanvas contract). Vertices are kept in CANVAS px (the
authoring truth, exactly the HTML tracer's frame); world coordinates are derived per render,
so a pitch change re-judges every vertex against the new horizon (invalid ones mark red and
suspend the outset preview instead of silently mis-projecting).
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF, QTransform
from PySide6.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsPolygonItem, QGraphicsScene, QGraphicsSimpleTextItem,
    QGraphicsView, QLabel,
)

from .. import imagefield
from ..scene import cam as _cam
from .widgets import mark_grabbable

_ZOOM_MIN, _ZOOM_MAX = 0.1, 8.0
_CLICK_SLOP_PX = 4          # press->release travel at/under this = a click, past it = a pan
_HANDLE_R = 4               # a trace vertex handle's screen radius (px, zoom-immune)


class BackdropCanvas(QGraphicsView):
    """A background pixmap + a camera; clicks become world floor points.

    Rung 0 is the primitive; Rung 1's trace mode authors the floor polygon on it. The canvas
    emits, it never writes — hosts own every document mutation."""

    floor_clicked = Signal(float, float)     # world (x, z) of an accepted left-click (plane mode)
    surface_clicked = Signal(object)         # a walkmesh hit dict (place mode; see _emit_surface)
    contact_clicked = Signal(float, float)   # CANVAS px of a click (contact mode; the host judges
                                             # it through occluder_z — ONE owner of both refusals)
    cutout_moved = Signal(int, float, float)   # a snip overlay drag ended: (index, new x, new y)
    contact_moved = Signal(int, float, float)  # a contact-handle drag ended: (index, cx, cy)
    click_refused = Signal(str)              # why a click produced no floor point

    def __init__(self, palette, *, scale=100, on_floor=None):
        super().__init__()
        self.pal = palette
        self._scale = scale if scale in range(50, 301) else 100
        self._cam = None
        self._pixmap = None
        self._zoom = 1.0
        self._fit_pending = False
        self._press_pos = None
        self._trace_mode = False
        self._trace = []                     # [(cx, cy)] canvas px — the authoring truth
        self._trace_items = []               # [{anchor, i}] rebuilt per render
        self._drag = None                    # live vertex drag, cleared by every _rebuild
        self.on_floor = on_floor             # ONE call per completed gesture (add/move/delete)
        self._place_mode = False             # Rung 3: clicks raycast the field's walkmesh
        self._contact_mode = False           # Rung 2: clicks are occluder ground contacts (canvas px)
        self._surface_tris = []              # RENDER-frame triangles (mesh_world_tris's output)
        self._surface_floors = []            # floor index per triangle (or empty)
        self._markers = []                   # [{pos: (x,y,z) render frame, label, kind}]
        self._cutouts = []                   # rung 2 previews: see set_cutouts
        self._cutout_items = {}              # i -> the overlay pixmap item (live drag target)
        self._contact_items = {}             # i -> the contact anchor item (live drag target)
        self._kids = []                      # STRONG refs to child items (labels/dots/glyphs):
                                             # a parented QGraphicsItem whose only Python wrapper
                                             # dies can be GC-DELETED on the C++ side mid-handler
                                             # (shiboken ownership), leaving itemAt() wrappers
                                             # stale and the scene teardown double-freeing
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        # FULL viewport repaints: the native partial-update path mis-computes exposed regions
        # for a TRANSFORMED, alpha-MASKED pixmap being dragged — the backdrop vanished under a
        # moving cut-out (owner playtest; offscreen full-frame renders cannot show it). The
        # scene is a few hundred items in a 384x448 frame — full repaints are cheap, artifacts
        # are not.
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
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
        self._coords = QLabel("", self.viewport())  # live world readout while a vertex drags
        self._coords.setObjectName("backdropHint")
        self._coords.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._coords.hide()
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
        sheet = ("QLabel#backdropHint {"
                 f"color: {self.pal['muted']};"
                 f"background: rgba({surf.red()},{surf.green()},{surf.blue()},0.86);"
                 "border-radius: 9px; padding: 2px 9px; }")
        for lab in (self._hint, self._coords):
            lab.setFont(self._font(8))
            lab.setStyleSheet(sheet)
        self._coords.setStyleSheet(sheet.replace(self.pal["muted"], self.pal["text"], 1))
        self._place_hint()

    def _child(self, item, parent):
        """Adopt a SCENE-CREATED item as ``parent``'s child. THE GC-CHILD LAW: an item
        constructed with a parent argument is PYTHON-owned to shiboken, so its wrapper's GC
        deletes the C++ child under a live scene (stale itemAt hits mid-handler) and its
        finalizer double-frees after a scene.clear() (an exit access violation). Creating via
        ``scene.addX`` then ``setParentItem`` keeps ownership C++-side both ways; ``_kids``
        keeps the wrapper alive as a belt."""
        item.setParentItem(parent)
        self._kids.append(item)
        return item

    def _place_hint(self):
        self._hint.adjustSize()                    # measure AFTER polish -- construction adjustSize lies
        vp = self.viewport()
        self._hint.move(vp.width() - self._hint.width() - 10,
                        vp.height() - self._hint.height() - 8)
        self._coords.adjustSize()
        self._coords.move(10, vp.height() - self._coords.height() - 8)

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

    # -- public: Rung 1 trace mode --
    def set_trace_mode(self, on):
        on = bool(on)
        if on == self._trace_mode:
            return
        self._trace_mode = on
        if on:
            self._place_mode = False           # one click semantics at a time
            self._contact_mode = False
        self._rebuild()

    # -- public: Rung 3 place mode --
    def set_place_mode(self, on):
        """Clicks raycast the loaded walkmesh (``set_surface``) instead of the y=0 plane.
        Exclusive with the other modes — one click semantics at a time."""
        on = bool(on)
        if on == self._place_mode:
            return
        self._place_mode = on
        if on:
            self._trace_mode = False
            self._contact_mode = False
        self._rebuild()

    # -- public: Rung 2 contact mode --
    def set_contact_mode(self, on):
        """Clicks are occluder GROUND CONTACTS: a slop click emits ``contact_clicked`` with the
        raw CANVAS pixel and nothing else — the host judges it through ``imagefield.occluder_z``
        (the one owner of BOTH refusals: above-horizon and z >= Z_BASE 'trace the base, not the
        body'). Exclusive with trace/place for CLICKS; the traced polygon keeps RENDERING for
        context, but its handles go inert (no drag, no append, no delete)."""
        on = bool(on)
        if on == self._contact_mode:
            return
        self._contact_mode = on
        if on:
            self._trace_mode = False
            self._place_mode = False
        self._rebuild()

    def set_surface(self, tris, floors=None):
        """Feed the field's walkmesh in the RENDER frame (``imagefield.mesh_world_tris``'s
        output — the y-flip already applied there, never here). Drawn as the live walkable
        footprint; place-mode clicks intersect exactly these triangles."""
        self._surface_tris = list(tris or [])
        self._surface_floors = list(floors or [])
        self._rebuild()

    def set_markers(self, markers):
        """Placed-content markers: ``[{"pos": (x, y, z) render frame, "label": str}, ...]``.
        Screen-fixed furniture at each point's projected pixel; points behind the camera are
        skipped (they are not on this canvas)."""
        self._markers = list(markers or [])
        self._rebuild()

    def set_cutouts(self, cutouts):
        """Rung 2's foreground previews: ``[{"i", "pixmap" (QPixmap|None), "rect" ((x, y, w, h)
        canvas px | None = fill the frame), "contact" ((cx, cy)), "label", "bad", "locked"}]``.
        A full-frame cut-out (rect None) renders registered and inert; a SNIP renders at its
        rect and DRAGS (alpha-masked hits, so clicks through its transparent sky still trace) —
        one ``cutout_moved`` per completed drag. Every cut-out gets a draggable contact handle
        (``contact_moved``) — the depth anchor is authored geometry, exactly like a vertex."""
        self._cutouts = list(cutouts or [])
        self._rebuild()

    def set_floor(self, pts):
        """Feed the trace polygon (canvas px) WITHOUT firing ``on_floor`` — the host's own
        writes route here (load, undo/redo); user gestures route through ``_commit_floor``."""
        self._trace = [tuple(p) for p in (pts or [])]
        self._rebuild()

    def floor(self):
        return list(self._trace)

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
        self._drag = None                          # scene.clear() deletes any grabbed item
        self._trace_items = []
        self._cutout_items = {}
        self._contact_items = {}
        self._kids = []                            # the old scene's children die WITH the clear
        self._coords.hide()
        sc.clear()
        w, h = self._frame_wh()
        sc.setSceneRect(QRectF(0, 0, w, h))
        if self._pixmap is not None and not self._pixmap.isNull():
            item = sc.addPixmap(self._pixmap)      # whatever its resolution, it FILLS the frame
            item.setTransform(QTransform.fromScale(w / self._pixmap.width(),
                                                   h / self._pixmap.height()))
            item.setData(0, "backdrop")
        self._draw_cutout_overlays(w, h)           # art layers, under every instrument
        border = QPen(QColor(pal["border"]), 1.0)
        border.setCosmetic(True)
        frame = sc.addRect(QRectF(0, 0, w, h), border)
        frame.setData(0, "frame")
        self._draw_surface()
        self._draw_horizon(w, h)
        self._draw_trace()
        self._draw_cutout_handles()                # grab furniture TOPMOST (the behaviordoc law)
        self._draw_markers()

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
        t = self._child(self._scene.addSimpleText("horizon — no floor above"), anchor)
        t.setFont(self._font(8))
        t.setBrush(QColor(self.pal["warn"]))
        t.setPos(0, -14)                           # screen px, riding the zoom-immune anchor

    # -- Rung 3: the walkable footprint + placed-content markers --
    def _draw_surface(self):
        """The walkmesh as a live footprint (the compose_background idiom, vector form):
        translucent fills + cosmetic outlines, one item per triangle. Behind-camera triangles
        are simply not on this canvas."""
        if not self._surface_tris or self._cam is None:
            return
        acc = QColor(self.pal["accent"])
        fill = QColor(acc)
        fill.setAlpha(26)
        edge = QColor(acc)
        edge.setAlpha(130)
        pen = QPen(edge, 1.0)
        pen.setCosmetic(True)
        for a, b, c in self._surface_tris:
            try:
                pts = [imagefield.world_point_to_click(self._cam, p) for p in (a, b, c)]
            except imagefield.ImageFieldError:
                continue
            it = self._scene.addPolygon(QPolygonF([QPointF(x, y) for x, y in pts]),
                                        pen, QBrush(fill))
            it.setData(0, "meshtri")

    def _draw_markers(self):
        if not self._markers or self._cam is None:
            return
        color = QColor(self.pal["text"])
        for m in self._markers:
            try:
                cx, cy = imagefield.world_point_to_click(self._cam, m["pos"])
            except imagefield.ImageFieldError:
                continue                       # behind the camera: not on this canvas
            anchor = self._scene.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
            anchor.setPos(cx, cy)
            anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
            anchor.setData(0, "marker")
            ring = self._child(self._scene.addEllipse(-4, -4, 8, 8), anchor)
            ring.setPen(QPen(color, 1.6))
            ring.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            dot = self._child(self._scene.addEllipse(-1.5, -1.5, 3, 3), anchor)
            dot.setPen(QPen(Qt.PenStyle.NoPen))
            dot.setBrush(QBrush(color))
            if m.get("label"):
                t = self._child(self._scene.addSimpleText(str(m["label"])), anchor)
                t.setFont(self._font(8))
                t.setBrush(QBrush(color))
                t.setPos(7, -15)               # screen px, riding the zoom-immune anchor

    # -- Rung 2: cut-out previews + their contact handles --
    def _draw_cutout_overlays(self, w, h):
        """The attached foregrounds ON the art (drawn right after the backdrop, before every
        instrument): a full-frame cut-out fills the frame inert; a snip sits at its rect with
        ALPHA-MASKED hit testing (a press on its transparent surround falls through to tracing/
        panning — only the object itself grabs)."""
        from PySide6.QtWidgets import QGraphicsPixmapItem
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
                else:                              # the object's pixels grab; its sky doesn't
                    it.setShapeMode(QGraphicsPixmapItem.ShapeMode.MaskShape)
                    mark_grabbable(it)             # the move cursor follows the opaque pixels
                self._cutout_items[c["i"]] = it

    def _draw_cutout_handles(self):
        """Contact anchors, drawn AFTER the trace so they sit topmost — grab furniture must
        never hide under a leg it happens to cross (the behaviordoc handles-last law)."""
        for c in self._cutouts:
            cx, cy = c["contact"]
            color = QColor(self.pal["error"] if c.get("bad") else self.pal["warn"])
            anchor = self._scene.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
            anchor.setPos(cx, cy)
            anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
            anchor.setData(0, "cutoutpt")
            anchor.setData(1, c["i"])
            dia = QPolygonF([QPointF(0, -5), QPointF(5, 0), QPointF(0, 5), QPointF(-5, 0)])
            gl = self._child(self._scene.addPolygon(dia), anchor)
            gl.setPen(QPen(color, 1.6))
            gl.setBrush(QBrush(color))
            mark_grabbable(gl)                     # the anchor re-tunes in trace + contact modes
            if c.get("label"):
                t = self._child(self._scene.addSimpleText(str(c["label"])), anchor)
                t.setFont(self._font(8))
                t.setBrush(QBrush(color))
                t.setPos(7, -16)                   # screen px, riding the zoom-immune anchor
            anchor.setToolTip("the floor-contact anchor — occlusion flips here; drag to re-anchor"
                              + (" (INVALID: no floor under it)" if c.get("bad") else ""))
            self._contact_items[c["i"]] = anchor

    def _resolve_data(self, item, tag):
        try:
            while item is not None:
                if item.data(0) == tag:
                    return item.data(1)
                item = item.parentItem()
        except RuntimeError:                       # a stale itemAt wrapper: treat as a miss
            pass
        return None

    def _surface_payload(self, hit):
        """The ``surface_clicked`` dict: the VISIBLE hit first-class (its (x, z) is what
        placement writes), every stacked hit listed nearest-first — ``len(stacked) > 1`` means
        a bridge/floor stack under this pixel, and hosts disambiguate rather than guess."""
        fl = self._surface_floors

        def row(s, ti, pos):
            return {"pos": pos, "xz": (pos[0], pos[2]),
                    "floor": fl[ti] if ti < len(fl) else None, "tri": ti, "s": s}

        rows = [row(*h) for h in hit["hits"]]
        top = dict(rows[0])
        top["stacked"] = rows
        return top

    # -- Rung 1: the trace layer --
    def _trace_worlds(self):
        """Per-vertex world (X, Z), or None where the vertex has no floor under it (above the
        horizon after a pitch change, or no camera). Derived per render — canvas px stay the
        truth, so a camera swap re-judges every vertex instead of silently mis-projecting."""
        out = []
        for p in self._trace:
            if self._cam is None:
                out.append(None)
                continue
            try:
                out.append(imagefield.click_to_world(self._cam, p))
            except imagefield.ImageFieldError:
                out.append(None)
        return out

    def _draw_trace(self):
        self._trace_items = []
        if not (self._trace_mode or self._contact_mode) or not self._trace:
            return                             # contact mode keeps the polygon VISIBLE, inert
        pal, sc = self.pal, self._scene
        worlds = self._trace_worlds()
        pen = QPen(QColor(pal["accent"]), 1.6)
        pen.setCosmetic(True)                      # legs must survive fit zoom (the atlas lesson)
        pts = [QPointF(cx, cy) for cx, cy in self._trace]
        for a, b in zip(pts, pts[1:]):
            ln = sc.addLine(a.x(), a.y(), b.x(), b.y(), pen)
            ln.setData(0, "traceline")
        if len(pts) > 2:                           # the closing leg, dashed (the tracer's idiom)
            dash = QPen(pen)
            dash.setDashPattern([4, 4])
            ln = sc.addLine(pts[-1].x(), pts[-1].y(), pts[0].x(), pts[0].y(), dash)
            ln.setData(0, "traceline")
        self._draw_outset(worlds)
        for i, (cx, cy) in enumerate(self._trace):
            bad = worlds[i] is None
            color = QColor(pal["error"] if bad else pal["accent"])
            anchor = sc.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
            anchor.setPos(cx, cy)
            anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
            anchor.setData(0, "tracept")
            anchor.setData(1, i)
            dot = self._child(
                self._scene.addEllipse(-_HANDLE_R, -_HANDLE_R, 2 * _HANDLE_R, 2 * _HANDLE_R),
                anchor)
            dot.setPen(QPen(color, 1.6))
            dot.setBrush(QBrush(color))
            t = self._child(self._scene.addSimpleText(str(i)), anchor)
            t.setFont(self._font(8))
            t.setBrush(QBrush(color))
            t.setPos(6, -16)                       # screen px, riding the zoom-immune anchor
            if self._trace_mode:                   # vertices drag only while TRACING (contact
                mark_grabbable(dot)                # mode renders them inert context)
            if bad:
                anchor.setToolTip("above the horizon — the build will refuse this vertex")
            self._trace_items.append({"anchor": anchor, "i": i})

    def _draw_outset(self, worlds):
        """The +48u collision-outset ring the build will actually emit, derived through the
        SAME conversions (world outset -> re-projected per vertex). Suspended while any vertex
        is invalid — a preview computed from partial geometry would lie."""
        if len(worlds) < 3 or any(w is None for w in worlds):
            return
        try:
            grown = imagefield.outset_polygon([tuple(w) for w in worlds],
                                              imagefield.COLLISION_OUTSET)
            ring = [imagefield.world_to_click(self._cam, g) for g in grown]
        except imagefield.ImageFieldError:
            return
        pen = QPen(QColor(self.pal["muted"]), 1.2)
        pen.setCosmetic(True)
        pen.setDashPattern([2, 3])
        it = self._scene.addPolygon(QPolygonF([QPointF(cx, cy) for cx, cy in ring]), pen)
        it.setData(0, "outset")
        it.setToolTip(f"+{imagefield.COLLISION_OUTSET:g}u collision outset — the walkmesh "
                      f"edge the build emits so the player centre reaches the visual edge")

    # -- trace gestures: press resolves a handle, move updates ONLY the grabbed items, release
    # commits ONE callback and the re-render redraws everything (the StageCanvas contract)
    def _resolve_vertex(self, item):
        try:
            while item is not None:
                if item.data(0) == "tracept":
                    return int(item.data(1))
                item = item.parentItem()
        except RuntimeError:                       # a stale itemAt wrapper (the GC-deleted-child
            pass                                   # class _kids prevents) must never kill a press
        return None

    def _begin_vertex_drag(self, i):
        if not 0 <= i < len(self._trace_items):
            return False
        self._drag = {"kind": "vertex", "i": i, "pt": tuple(self._trace[i])}
        self._update_coords()
        return True

    def _begin_contact_drag(self, i):
        c = next((c for c in self._cutouts if c["i"] == i), None)
        if c is None or i not in self._contact_items:
            return False
        self._drag = {"kind": "cpt", "i": i, "pt": tuple(c["contact"]), "start": tuple(c["contact"])}
        self._update_coords()
        return True

    def _begin_cutout_drag(self, i, grab):
        """``grab`` = the press point in canvas px; the snip drags by its grabbed spot, never
        snapping its corner to the cursor."""
        c = next((c for c in self._cutouts if c["i"] == i), None)
        if c is None or c.get("rect") is None or c.get("locked") or i not in self._cutout_items:
            return False
        x, y, w, h = c["rect"]
        self._drag = {"kind": "cimg", "i": i, "grab": (grab.x() - x, grab.y() - y),
                      "pt": (x, y), "start": (x, y), "wh": (w, h)}
        self._update_coords()
        return True

    def _drag_canvas(self, cx, cy):
        """One drag step, CANVAS px (tests drive this directly — the testable seam)."""
        d = self._drag
        if not d:
            return
        if d.get("kind") == "cpt":
            d["pt"] = (cx, cy)
            self._contact_items[d["i"]].setPos(cx, cy)
        elif d.get("kind") == "cimg":
            d["pt"] = (cx - d["grab"][0], cy - d["grab"][1])
            self._cutout_items[d["i"]].setPos(*d["pt"])
        else:
            d["pt"] = (cx, cy)
            self._trace_items[d["i"]]["anchor"].setPos(cx, cy)
        self._update_coords()

    def _end_vertex_drag(self):
        """Release commits ONE emission per gesture, per drag kind (the StageCanvas contract)."""
        d, self._drag = self._drag, None
        self._coords.hide()
        if not d:
            return
        if d.get("kind") == "cpt":
            if d["pt"] != d["start"]:
                self.contact_moved.emit(d["i"], round(d["pt"][0], 1), round(d["pt"][1], 1))
            return
        if d.get("kind") == "cimg":
            if d["pt"] != d["start"]:
                self.cutout_moved.emit(d["i"], round(d["pt"][0], 1), round(d["pt"][1], 1))
            return
        if d["pt"] != tuple(self._trace[d["i"]]):
            pts = list(self._trace)
            pts[d["i"]] = (round(d["pt"][0], 1), round(d["pt"][1], 1))
            self._commit_floor(pts)

    def _delete_vertex(self, i):
        if 0 <= i < len(self._trace):
            self._commit_floor(self._trace[:i] + self._trace[i + 1:])

    def _commit_floor(self, pts):
        """Every completed gesture funnels here: re-render, then exactly ONE host callback."""
        self._trace = [tuple(p) for p in pts]
        self._rebuild()
        if self.on_floor:
            self.on_floor(list(self._trace))

    def _update_coords(self):
        d = self._drag
        if not d:
            return
        cx, cy = d["pt"]
        kind = d.get("kind", "vertex")
        if kind == "cimg":
            self._coords.setText(f"fg{d['i']} · canvas {cx:.0f},{cy:.0f}")
            self._coords.show()
            self._place_hint()
            return
        who = f"fg{d['i']} contact" if kind == "cpt" else f"vertex {d['i']}"
        head = f"{who} · canvas {cx:.0f},{cy:.0f}"
        if self._cam is not None:
            try:
                X, Z = imagefield.click_to_world(self._cam, (cx, cy))
                head += f" · world x {X:.0f} · z {Z:.0f}"
            except imagefield.ImageFieldError:
                head += " · above the horizon"
        self._coords.setText(head)
        self._coords.show()
        self._place_hint()

    def _vertex_menu(self, i, global_pos):
        """The list-op menu, behind a seam so tests drive the choice without a popup."""
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        rm = menu.addAction(f"Delete vertex {i}")
        act = menu.exec(global_pos)
        if act is rm:
            self._delete_vertex(i)

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

    # -- click vs pan: slop, not modes. In trace mode a press ON a handle starts a drag;
    # a slop-click elsewhere appends a vertex; everything else stays a pan.
    def mousePressEvent(self, event):              # noqa: N802 (Qt override)
        if event.button() == Qt.MouseButton.LeftButton:
            # EVERY item under the press, topmost-first — never itemAt alone. itemAt returns
            # only the topmost item, so a trace leg / outset ring / label crossing a grabbable
            # thing ATE the press and fell through to pan, while Qt's hover CURSOR looks
            # through cursor-less items — the exact says-Move-but-pans mismatch the owner hit.
            # Kind priority (vertex > contact anchor > snip) matches the furniture's z-order.
            under = self.items(event.position().toPoint())
            if self._trace_mode:
                for it in under:
                    i = self._resolve_vertex(it)
                    if i is not None and self._begin_vertex_drag(i):
                        event.accept()
                        return
            if self._trace_mode or self._contact_mode:   # cut-out furniture drags in both modes
                for it in under:
                    ci = self._resolve_data(it, "cutoutpt")
                    if ci is not None and self._begin_contact_drag(int(ci)):
                        event.accept()
                        return
                for it in under:
                    ci = self._resolve_data(it, "cutoutimg")
                    if ci is not None and self._begin_cutout_drag(
                            int(ci), self._widget_to_canvas(event.position())):
                        event.accept()
                        return
            self._press_pos = event.position()
        super().mousePressEvent(event)             # the pan machinery still runs

    def mouseMoveEvent(self, event):               # noqa: N802 (Qt override)
        if self._drag:
            sp = self._widget_to_canvas(event.position())
            self._drag_canvas(sp.x(), sp.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):            # noqa: N802 (Qt override)
        if self._drag and event.button() == Qt.MouseButton.LeftButton:
            self._end_vertex_drag()
            event.accept()
            return
        press, self._press_pos = self._press_pos, None
        super().mouseReleaseEvent(event)
        if (press is None or event.button() != Qt.MouseButton.LeftButton
                or self._cam is None):
            return
        travel = (event.position() - press).manhattanLength()
        if travel > _CLICK_SLOP_PX:
            return                                 # it was a pan
        if self._contact_mode:                     # Rung 2: the raw canvas pixel; the host judges it
            c = self._widget_to_canvas(event.position())
            self.contact_clicked.emit(c.x(), c.y())
            return
        if self._place_mode:                       # Rung 3: the click raycasts the walkmesh
            c = self._widget_to_canvas(event.position())
            try:
                hit = imagefield.click_to_surface(self._cam, self._surface_tris,
                                                  (c.x(), c.y()))
            except imagefield.ImageFieldError as e:
                self.click_refused.emit(str(e))
                return
            self.surface_clicked.emit(self._surface_payload(hit))
            return
        try:
            x, z = self.click_to_world(event.position())
        except imagefield.ImageFieldError as e:
            self.click_refused.emit(str(e))
            return
        if self._trace_mode:
            c = self._widget_to_canvas(event.position())
            self._commit_floor(self._trace + [(round(c.x(), 1), round(c.y(), 1))])
            return
        self.floor_clicked.emit(x, z)

    def contextMenuEvent(self, event):             # noqa: N802 (Qt override)
        if not self._trace_mode:
            return super().contextMenuEvent(event)
        i = next((v for v in (self._resolve_vertex(it) for it in self.items(event.pos()))
                  if v is not None), None)
        if i is None:
            return super().contextMenuEvent(event)
        self._vertex_menu(i, event.globalPos())
        event.accept()
