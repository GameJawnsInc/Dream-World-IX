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
from PySide6.QtGui import (
    QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF, QTransform,
)
from PySide6.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsPolygonItem, QGraphicsScene, QGraphicsSimpleTextItem,
    QGraphicsView, QLabel,
)

from .. import imagefield
from ..editor.theme import _contrast as _hex_contrast, derive
from ..scene import cam as _cam
from .widgets import mark_grabbable


def _contrast(a: QColor, b: QColor) -> float:
    return _hex_contrast(a.name(), b.name())

_ZOOM_MIN, _ZOOM_MAX = 0.1, 8.0
_CLICK_SLOP_PX = 4          # press->release travel at/under this = a click, past it = a pan
_HANDLE_R = 4               # a trace vertex handle's screen radius (px, zoom-immune)
_LABEL_TIERS = 3            # how far a label may be pushed from home, in plate heights


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
    region_drawn = Signal(object)            # rung 4: a 4-corner quad completed — [(x, z)] * 4
    region_changed = Signal(int, object)     # a region gesture ended: (index, its new [(x, z)] quad)
    region_deleted = Signal(int)             # the region menu's delete — the host owns the doc op
    region_retarget = Signal(int)            # "Set gateway target…" — the host asks + writes
    region_reword = Signal(int)              # "Set message…" (events) — the host asks + writes
    marker_moved = Signal(int, object)       # place mode: a marker dragged — (index, walkmesh hit)
    marker_clicked = Signal(int)             # place mode: a press on a marker that did not travel
    marker_deleted = Signal(int)             # the marker menu's delete — the host owns the doc op
    click_refused = Signal(str)              # why a click produced no floor point

    def __init__(self, palette, *, scale=100, on_floor=None):
        super().__init__()
        self.pal = palette
        self._scale = scale if scale in range(50, 301) else 100
        self._cam = None
        self._pixmap = None
        self._zoom = 1.0
        self._fit_pending = False
        self._fit_zoom = None                # the zoom the last fit chose: while the view still
                                             # sits at it, a resize re-fits (a fitted view has no
                                             # scroll range, so there is no pan to lose)
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
        self._marker_items = {}              # i -> the marker anchor (live drag target)
        self._cutouts = []                   # rung 2 previews: see set_cutouts
        self._cutout_items = {}              # i -> the overlay pixmap item (live drag target)
        self._contact_items = {}             # i -> the contact anchor item (live drag target)
        self._region_mode = False            # rung 4: clicks author trigger-region quads
        self._regions = []                   # the fed rows: see set_regions
        self._region_items = {}              # i -> the quad polygon item (live drag target)
        self._region_handle_items = {}       # (i, corner) -> the corner anchor (live drag target)
        self._region_edge_items = {}         # i -> the walk-out edge line (gateways)
        self._region_law_items = {}          # i -> [spill/gap overlay items] (hidden mid-drag)
        self._region_label_items = {}        # i -> the label anchor (follows a live drag)
        self._region_case_items = {}         # i -> the casings under its quad/edge (follow too)
        self._pending_region = []            # world (x, z) corners of the quad being drawn
        self._labels = []                    # on-art labels, for the de-collision pass (P21)
        self._glyphs = []                    # haloed glyphs: obstacles for that pass
        self._ink = derive(palette)
        self._kids = []                      # STRONG refs to child items (labels/dots/glyphs):
                                             # a parented QGraphicsItem whose only Python wrapper
                                             # dies can be GC-DELETED on the C++ side mid-handler
                                             # (shiboken ownership), leaving itemAt() wrappers
                                             # stale and the scene teardown double-freeing
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
        self._hint = QLabel("", self.viewport())   # the mode's own words: _sync_hint
        self._hint.setObjectName("backdropHint")   # selector-scoped (the round-9 census law)
        self._hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._coords = QLabel("", self.viewport())  # live world readout while a vertex drags
        self._coords.setObjectName("backdropHint")
        self._coords.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._coords.hide()
        self._style_hint()
        self._sync_hint()

    def _sync_hint(self):
        """The pill says what a click does in THIS mode (P18), and is shown again: called on a
        mode change and a new field. The first click or drag hides it -- it covers the art's
        bottom-right, where the near floor edge, doors and contacts live."""
        if self._cam is None:
            what = ""                              # nothing on this canvas resolves a click
        elif self._region_mode:
            what = "click 4 corners"               # (Esc: the tool's tooltip -- this pill hides on
            #                                        the first corner, before Esc can do anything)
        elif self._contact_mode:
            what = "click the object's base"
        elif self._trace_mode:
            what = "click the floor's outline"
        else:
            what = "click the floor"
        self._hint.setText(f"{what} · Ctrl+scroll zooms" if what else
                           "Ctrl+scroll zooms · Ctrl+0 fits")
        self._hint.show()
        self._place_hint()

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
        keeps the wrapper alive as a belt. Data slots 2/3 carry the anchor's own tag so
        press resolution reads the hit alone — never a parentItem() walk, the poison call
        (studies/pyside-gc-crash)."""
        item.setParentItem(parent)
        item.setData(2, parent.data(0))            # the anchor's tag, resolvable in place
        item.setData(3, parent.data(1))
        self._kids.append(item)
        return item

    # -- ON-ART furniture: the art is an ARBITRARY ground (P20) --
    # A hand-painted background spans every luminance, so no single UI token survives on it
    # (accent on the tan fixture floor measured 1.11-1.83:1). Three rules, each one ground the
    # furniture brings with it instead of borrowing the art:
    #   TEXT sits on an opaque surface PLATE in an ink the theme already fences at 4.5:1 on its
    #     surface (text / warn_text / error_text) -- the art never touches a glyph.
    #   HANDLES + GLYPHS wear a two-tone halo, a white ring inside a black one: whatever the art,
    #     one of the pair clears 4.5:1 against it (black/white straddle every luminance).
    #   LINES ride a casing in black or white, whichever is further from the stroke; every
    #     stroke token clears 3:1 against its own casing, the colour it is always adjacent to.
    def _casing(self, color):
        c = QColor(color)
        return QColor(0, 0, 0) if _contrast(c, QColor(0, 0, 0)) >= _contrast(c, QColor(255, 255, 255)) \
            else QColor(255, 255, 255)

    def _cased_pen(self, color, width, dash=None):
        """The (casing, stroke) pens of a cased line: the casing a solid 2 px wider underlay."""
        stroke = QPen(QColor(color), width)
        stroke.setCosmetic(True)
        if dash:
            stroke.setDashPattern(dash)
        case = QPen(self._casing(color), width + 2.0)
        case.setCosmetic(True)
        return case, stroke

    def _halo(self, anchor, path, grab=False, hollow=False):
        """The black outer ring under a handle/glyph (added BEFORE it, so it paints below);
        the glyph's own pen is the white inner ring. A tagged child, so a press on the rim
        resolves like a press on the glyph."""
        k = QColor(0, 0, 0)
        pen = QPen(k, 4.4)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        under = self._child(self._scene.addPath(
            path, pen, QBrush(Qt.BrushStyle.NoBrush) if hollow else QBrush(k)), anchor)
        self._glyphs.append((anchor, path.boundingRect().adjusted(-2.2, -2.2, 2.2, 2.2)))
        if grab:
            mark_grabbable(under)
        return under

    @staticmethod
    def _ring_pen():
        return QPen(QColor(255, 255, 255), 1.4)

    def _label(self, anchor, text, ink, dx=6, dy=None, tip=None):
        """On-art text: an opaque surface plate + an ink fenced on that surface, both children
        of ``anchor`` (zoom-immune), registered for the de-collision pass (P21). By default the
        plate sits up-right of the anchor with its bottom clear of the anchor's own glyph.
        ``tip``: the tooltip of the thing it names, for a label that may sit outside it."""
        sc = self._scene
        anchor.setZValue(1)                        # over every leg / outline / ring: a line
                                                   # drawn later must not strike the text out
        plate = self._child(sc.addPath(QPainterPath(), QPen(Qt.PenStyle.NoPen),
                                       QBrush(QColor(self.pal["surface"]))), anchor)
        t = self._child(sc.addSimpleText(str(text)), anchor)
        for it in (plate, t):                      # a label is NOT its anchor's grab handle: it
            if anchor.data(0) != "regionlabel":    # can sit tiers away, and a press there would
                it.setData(2, None)                # snap the vertex to the cursor (P21, after
                it.setData(3, None)                # review); a click on it is a floor click. A
            if tip:                                # ZONE label keeps its tag: no press resolves
                it.setToolTip(tip)                 # it, only the right-click menu does -- and the
                                                   # warning it carries says "right-click it"
        t.setFont(self._font(8))
        t.setBrush(QBrush(QColor(ink)))
        br = t.boundingRect()
        w, h = br.width() + 6, br.height() + 2
        if dy is None:
            dy = -h - 8                            # plate bottom at -9: clear of a r<=8 glyph
        rr = QPainterPath()
        rr.addRoundedRect(QRectF(0, 0, w, h), 3, 3)
        plate.setPath(rr)
        lab = {"anchor": anchor, "plate": plate, "text": t, "dx": dx, "dy": dy, "w": w, "h": h}
        self._labels.append(lab)
        self._set_label_pos(lab, dx, dy)
        return t

    @staticmethod
    def _set_label_pos(lab, dx, dy):
        lab["plate"].setPos(dx - 3, dy - 1)
        lab["text"].setPos(dx, dy)

    def _decollide_labels(self):
        """Shuffle overlapping labels to free vertical tiers (behaviordoc.StageCanvas's pass,
        in plate units). Labels live in SCREEN px, so what collides depends on the transform:
        re-run after every rebuild, fit, zoom and resize. Anchors never move -- only each
        label's offset does, so the leader point stays honest."""
        vw, vh = self.viewport().width(), self.viewport().height()
        placed = []                                # every glyph is an obstacle: a label must
        for a, box in self._glyphs:                # never hide a handle it happens to cross
            try:
                placed.append(box.translated(self.mapFromScene(a.pos()).toPointF()))
            except RuntimeError:
                return
        for lab in self._labels:
            try:
                base = self.mapFromScene(lab["anchor"].pos())
            except RuntimeError:                   # scene rebuilt under a stale list
                return
            w, h, step = lab["w"], lab["h"], lab["h"] + 1
            dx = lab["dx"]
            mirrored = vw > 40 and base.x() + dx + w > vw - 2
            if mirrored:
                dx = -dx - w                       # off the right edge: mirror to the left
            # At most _LABEL_TIERS tiers either way: a label pushed further than that stops
            # reading as its anchor's (no leader line says whose it is), so past the cap it
            # overprints near home instead. Never off the viewport: a clipped label is LOST,
            # an overprinted one is still there (P21, after review).
            # The OTHER side of its own glyph comes before any tier: a label lifted off a
            # neighbour's glyph landed beside that neighbour, and read as its name.
            cands = [(dx, lab["dy"])]
            if not mirrored and base.x() - lab["dx"] - w - 3 >= 1:
                cands.append((-lab["dx"] - w, lab["dy"]))
            cands += [(dx, lab["dy"] - step * k) for k in range(1, _LABEL_TIERS + 1)]
            cands += [(dx, lab["dy"] + step * k) for k in range(1, _LABEL_TIERS + 1)
                      if lab["dy"] + step * k >= 8]   # a DOWN tier clears the anchor's own glyph

            def rect(c):
                return QRectF(base.x() + c[0] - 3, base.y() + c[1] - 1, w, h)

            def onscreen(c):
                r = rect(c)
                return r.top() >= 1 and (vh <= 40 or r.bottom() <= vh - 1)

            visible = [c for c in cands if onscreen(c)] or cands[:1]
            pick = next((c for c in visible if not any(rect(c).intersects(p) for p in placed)),
                        visible[0])
            self._set_label_pos(lab, *pick)
            placed.append(rect(pick))

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
            self._sync_hint()                      # a new field: the pill teaches again
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
            self._region_mode = False
        self._sync_hint()
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
            self._region_mode = False
        self._sync_hint()
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
            self._region_mode = False
        self._sync_hint()
        self._rebuild()

    # -- public: Rung 4 region mode --
    def set_region_mode(self, on):
        """Clicks author TRIGGER-REGION quads: four accepted clicks build one region
        (``region_drawn``), a corner or whole-quad drag re-shapes an existing one
        (``region_changed``), right-click offers rotate-the-walk-out-edge / delete. Exclusive
        with the other click semantics; the fed regions keep RENDERING in place mode for
        context (doc truth, like markers), but only region mode makes them grabbable."""
        on = bool(on)
        if on == self._region_mode:
            return
        self._region_mode = on
        self._pending_region = []
        if on:
            self._trace_mode = False
            self._place_mode = False
            self._contact_mode = False
        self._sync_hint()
        self._rebuild()

    def set_regions(self, rows):
        """Feed the trigger regions: ``[{"i", "quad" ([(x, z)] * 4, world), "label", "kind"
        ("gateway"|"event"), "warn" (str|None)}]``. The canvas derives each row's engine-fan
        audit (:func:`ff9mapkit.imagefield.zone_fan_audit`) per render and PAINTS the
        disagreement — a dead zone hatches in error, an over-trigger spill washes in warn —
        so the law is visible, not just accepted. Corners project at the walkmesh's height
        when a surface is loaded (zone corners may hang OFF the mesh — that is normal donor
        layout), on the y=0 plane otherwise."""
        self._regions = list(rows or [])
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
        skipped (they are not on this canvas). In place mode a marker is a grab handle: a drag
        emits ``marker_moved``, a press that does not travel ``marker_clicked`` (never a second
        placement on top of it), its menu ``marker_deleted`` -- each by its index in this list.
        ``locked`` (the host's reason it refuses every gesture): no grab cursor, no drag, no menu;
        the tooltip gives the reason and a click still only emits ``marker_clicked``. ``keep``:
        movable but never deleted -- no menu."""
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
        self._marker_items = {}
        self._region_items = {}
        self._region_handle_items = {}
        self._region_edge_items = {}
        self._region_law_items = {}
        self._region_label_items = {}
        self._region_case_items = {}               # i -> [quad casing, edge casing?]
        self._kids = []                            # the old scene's children die WITH the clear
        self._labels = []                          # every _label call, for the de-collision pass
        self._glyphs = []                          # (anchor, screen box) of every haloed glyph
        self._ink = derive(pal)                    # the *_text inks fenced on the plate's surface
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
        self._draw_regions()
        self._draw_pending_region()                # renders on a bare canvas too (first quad)
        self._draw_horizon(w, h)
        self._draw_trace()
        self._draw_cutout_handles()                # grab furniture TOPMOST (the behaviordoc law)
        self._draw_region_handles()
        self._draw_markers()
        self._decollide_labels()

    def _draw_horizon(self, w, h):
        """The refusal boundary, visible: a dashed line at ``horizon_canvas_y`` with a
        screen-fixed label. A horizon ABOVE the frame (every canvas row is floor) is marked on
        the top edge with how far off it is -- the default Trace pitch puts it 4 px up, and the
        tooltip that says to line it up had nothing to point at (finding T27). Only for a host
        that sets ``mark_horizon_off_frame`` (Trace, where the author lines the horizon up; on a
        field's own camera in Place it is not an instrument). Below the frame, none is floor:
        nothing drawn (the guard still refuses either way)."""
        if self._cam is None:
            return
        hy = _cam.horizon_canvas_y(self._cam)
        if hy < 0 and getattr(self, "mark_horizon_off_frame", False):
            case, pen = self._cased_pen(self.pal["warn"], 1.6, [2, 4])
            self._scene.addLine(0, 0, w, 0, case).setData(0, "casing")
            self._scene.addLine(0, 0, w, 0, pen).setData(0, "horizonedge")
            anchor = self._scene.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
            anchor.setPos(6, 0)
            anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
            anchor.setData(0, "horizonedgelabel")
            # short: the plate sits ON the art's top strip, where the eye level is matched (at
            # 150% the long form spanned the whole photo and ran off its right edge -- review)
            self._label(anchor, f"↑ horizon {max(1, round(-hy))} px",
                        self._ink["warn_text"], dx=0, dy=2)
            return
        if not 0 <= hy < h:
            return
        case, pen = self._cased_pen(self.pal["warn"], 1.6, [6, 4])   # cosmetic: survives fit zoom
        self._scene.addLine(0, hy, w, hy, case).setData(0, "casing")
        line = self._scene.addLine(0, hy, w, hy, pen)
        line.setData(0, "horizon")
        anchor = self._scene.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
        anchor.setPos(6, hy)
        anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
        anchor.setData(0, "horizonlabel")
        self._label(anchor, "horizon — no floor above", self._ink["warn_text"], dx=3)

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
        case, pen = self._cased_pen(acc, 1.0)
        polys = []
        for a, b, c in self._surface_tris:
            try:
                pts = [imagefield.world_point_to_click(self._cam, p) for p in (a, b, c)]
            except imagefield.ImageFieldError:
                continue
            polys.append(QPolygonF([QPointF(x, y) for x, y in pts]))
        for poly in polys:                         # every casing first: a casing must never
            self._scene.addPolygon(poly, case).setData(0, "casing")   # cut a neighbour's edge
        for poly in polys:
            it = self._scene.addPolygon(poly, pen, QBrush(fill))
            it.setData(0, "meshtri")

    @staticmethod
    def _marker_path(kind):
        """Placed content speaks its KIND by shape (P25), not only through its label: npc a
        circle, prop a square, chest a lidded box, spawn a triangle, arrival a diamond."""
        p = QPainterPath()
        if kind == "prop":
            p.addRect(QRectF(-4.5, -4.5, 9, 9))
        elif kind == "chest":
            p.addRect(QRectF(-6, -4, 12, 8))
            p.moveTo(-6, -1)
            p.lineTo(6, -1)                        # the lid seam
        elif kind == "spawn":
            p.addPolygon(QPolygonF([QPointF(0, -6), QPointF(5.5, 4), QPointF(-5.5, 4)]))
            p.closeSubpath()
        elif kind == "arrival":
            p.addPolygon(QPolygonF([QPointF(0, -6), QPointF(6, 0), QPointF(0, 6),
                                    QPointF(-6, 0)]))
            p.closeSubpath()
        else:                                      # npc and anything unknown
            p.addEllipse(QPointF(0, 0), 5, 5)
        return p

    def _draw_markers(self):
        if not self._markers or self._cam is None:
            return
        color = QColor(self.pal["text"])
        grab = self._place_mode                    # the Place tool's handles only (P16): inert
        for i, m in enumerate(self._markers):      # under Regions corners and on the Trace tab
            try:
                cx, cy = imagefield.world_point_to_click(self._cam, m["pos"])
            except imagefield.ImageFieldError:
                continue                       # behind the camera: not on this canvas
            anchor = self._scene.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
            anchor.setPos(cx, cy)
            anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
            anchor.setData(0, "marker")
            anchor.setData(1, i)
            path = self._marker_path(m.get("kind"))
            free = grab and not m.get("locked")    # the host refuses every gesture on a locked one
            halo = self._halo(anchor, path, free)
            # a marker the host will never move LOOKS fixed in a still image too: the muted ink
            # (never hollow -- hollow means INVALID on this canvas, and this marker is fine)
            ink = QColor(self.pal["muted"]) if grab and not free else color
            gl = self._child(self._scene.addPath(path, self._ring_pen(), QBrush(ink)), anchor)
            if grab:
                name = m.get("label") or m.get("kind")
                if free:
                    mark_grabbable(gl)
                tip = (f"{name}: {m['locked']}" if not free
                       else f"{name}: drag to move it" if m.get("keep")
                       else f"{name}: drag to move it, right-click for its menu")
                halo.setToolTip(tip)
                gl.setToolTip(tip)
            if m.get("label"):
                self._label(anchor, m["label"], self.pal["text"], dx=8)
            self._marker_items[i] = anchor

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
                    if self._trace_mode or self._contact_mode:   # where a press drags it (V6)
                        mark_grabbable(it)         # the move cursor follows the opaque pixels
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
            grab = self._trace_mode or self._contact_mode   # the press gate's modes only (V6)
            halo = QPainterPath()
            halo.addPolygon(dia)
            halo.closeSubpath()
            self._halo(anchor, halo, grab, hollow=bool(c.get("bad")))
            gl = self._child(self._scene.addPolygon(dia), anchor)
            gl.setPen(self._ring_pen())
            if c.get("bad"):                       # INVALID speaks by shape too: hollow (V13)
                gl.setPen(QPen(color, 2.2))
                gl.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            else:
                gl.setBrush(QBrush(color))
            if grab:
                mark_grabbable(gl)                 # the anchor re-tunes in trace + contact modes
            if c.get("label"):
                self._label(anchor, str(c["label"]) + (" ✕" if c.get("bad") else ""),
                            self._ink["error_text"] if c.get("bad") else self.pal["text"],
                            dx=8)
            anchor.setToolTip("the floor-contact anchor — occlusion flips here; drag to re-anchor"
                              + (" (INVALID: no floor under it)" if c.get("bad") else ""))
            self._contact_items[c["i"]] = anchor

    # -- Rung 4: trigger regions drawn on the art --
    def _zone_y(self, x, z):
        """The render-frame height a zone corner sits at: the walkmesh's floor under (x, z)
        when a surface is loaded (nearest-vertex fallback covers off-mesh corners — normal
        donor layout), the y=0 plane otherwise."""
        if self._surface_tris:
            eye = tuple(_cam.decompose(self._cam)["C"]) if self._cam is not None else None
            y = imagefield.floor_y_at(self._surface_tris, x, z, eye)
            if y is not None:
                return y
        return 0.0

    def _zone_px(self, x, z):
        """A zone corner's canvas pixel (raises ImageFieldError behind the camera)."""
        return imagefield.world_point_to_click(self._cam, (x, self._zone_y(x, z), z))

    def _px_to_zone_world(self, c, h_hint=0.0):
        """Canvas point -> the (x, z) a zone corner lands at: the walkmesh raycast when the
        pixel hits it (you click what you see), else the plane at the nearest floor height —
        a zone corner is a PLAN-space object and may legitimately hang off the mesh. Raises
        ImageFieldError at/above the horizon (the standing refusal, never a clamp)."""
        if self._surface_tris:
            try:
                hit = imagefield.click_to_surface(self._cam, self._surface_tris,
                                                  (c.x(), c.y()))
                return (hit["pos"][0], hit["pos"][2])
            except imagefield.ImageFieldError:
                x, z = imagefield.click_to_plane(self._cam, (c.x(), c.y()), h_hint)
                y = imagefield.floor_y_at(self._surface_tris, x, z)
                if y is not None and abs(y - h_hint) > 1e-6:   # one refine pass: land on the
                    x, z = imagefield.click_to_plane(self._cam, (c.x(), c.y()), y)  # real floor
                return (x, z)
        return imagefield.click_to_world(self._cam, (c.x(), c.y()))

    def _region_row(self, i):
        return next((r for r in self._regions if r["i"] == i), None)

    def _region_pts_px(self, quad):
        """Every corner's canvas pixel, or None if any corner is unprojectable."""
        try:
            return [self._zone_px(x, z) for x, z in quad]
        except imagefield.ImageFieldError:
            return None

    def _draw_regions(self):
        """The fed trigger regions ON the art (any mode — they are doc truth, like markers):
        the quad the author drew, its engine-fan DISAGREEMENT painted (dead zone = error
        hatch, over-trigger spill = warn wash — the law rendered, not just accepted), and a
        gateway's walk-out edge (q0→q1, the edge ``CalculateExitPosition`` walks the player
        across) marked with a zoom-immune chevron. Kind speaks by SHAPE: gateways solid,
        events dashed."""
        if not self._regions or self._cam is None:
            return
        sc, pal = self._scene, self.pal
        for r in self._regions:
            pts = self._region_pts_px(r["quad"])
            if pts is None or len(pts) < 4:
                continue
            i = r["i"]
            warn = r.get("warn")
            color = QColor(pal["warn"] if warn else pal["accent"])
            case, pen = self._cased_pen(color, 1.6,
                                        [5, 3] if r.get("kind") == "event" else None)
            fill = QColor(color)
            fill.setAlpha(22)
            poly = QPolygonF([QPointF(x, y) for x, y in pts])
            cpoly = sc.addPolygon(poly, case)
            cpoly.setData(0, "casing")
            self._region_case_items[i] = [cpoly]
            it = sc.addPolygon(poly, pen, QBrush(fill))
            it.setData(0, "regionquad")
            it.setData(1, i)
            tip = str(r.get("label") or f"zone {i}")
            if warn:
                tip += f"\n⚠ {warn}"
            it.setToolTip(tip)
            if self._region_mode:
                mark_grabbable(it)
            # the fan audit, painted: what the engine tests vs what the author drew
            audit = imagefield.zone_fan_audit(r["quad"])
            law_items = []
            if max(audit["gap"], audit["spill"]) > 0.02:
                drawn = QPainterPath()
                drawn.addPolygon(poly)
                drawn.closeSubpath()
                fan = QPainterPath()
                for t in imagefield.fan_triangles(r["quad"]):
                    tp = self._region_pts_px(list(t))
                    if tp is None:
                        continue
                    p = QPainterPath()
                    p.addPolygon(QPolygonF([QPointF(x, y) for x, y in tp]))
                    p.closeSubpath()
                    fan = fan.united(p)
                if audit["gap"] > 0.02:
                    g = QColor(pal["error"])
                    g.setAlpha(70)
                    gi = sc.addPath(drawn.subtracted(fan), QPen(Qt.PenStyle.NoPen), QBrush(g))
                    gi.setData(0, "regiongap")
                    gi.setData(1, i)
                    gi.setToolTip(f"DEAD ZONE (~{audit['gap']:.0%} of the drawn area): the "
                                  f"engine's IsInQuad fan never tests here — the trigger "
                                  f"silently won't fire. Use a convex quad (collinear points "
                                  f"are the usual cause).")
                    law_items.append(gi)
                if audit["spill"] > 0.02:
                    s = QColor(pal["warn"])
                    s.setAlpha(55)
                    si = sc.addPath(fan.subtracted(drawn), QPen(Qt.PenStyle.NoPen), QBrush(s))
                    si.setData(0, "regionspill")
                    si.setData(1, i)
                    si.setToolTip(f"OVER-TRIGGER (~{audit['spill']:.0%} of what actually "
                                  f"fires): the engine's fan covers this un-drawn area too — "
                                  f"a non-convex or self-crossing quad fires past its own "
                                  f"outline. Make the quad convex.")
                    law_items.append(si)
            self._region_law_items[i] = law_items
            if r.get("kind") == "gateway":
                (x0, y0), (x1, y1) = pts[0], pts[1]
                ecase, epen = self._cased_pen(color, 3.2)
                cedge = sc.addLine(x0, y0, x1, y1, ecase)
                cedge.setData(0, "casing")
                self._region_case_items[i].append(cedge)
                edge = sc.addLine(x0, y0, x1, y1, epen)
                edge.setData(0, "regionedge")
                edge.setData(1, i)
                edge.setToolTip("the walk-out edge (drawn thick, with an arrow): the exit walks "
                                "the player across this edge into the fade — right-click the zone "
                                "to move it to the next edge")
                self._region_edge_items[i] = edge
                mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                cx = sum(p[0] for p in pts) / len(pts)
                cy = sum(p[1] for p in pts) / len(pts)
                ex, ey = mx - cx, my - cy              # outward = away from the quad's centre
                el = (ex * ex + ey * ey) ** 0.5 or 1.0
                anchor = sc.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
                anchor.setPos(mx, my)
                anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
                anchor.setData(0, "regionchevron")
                anchor.setData(1, i)
                ux, uy = ex / el, ey / el
                tipx, tipy = 7 * ux, 7 * uy
                px, py = -uy, ux
                chev = QPolygonF([QPointF(tipx, tipy),
                                  QPointF(4 * px - 2 * ux, 4 * py - 2 * uy),
                                  QPointF(-4 * px - 2 * ux, -4 * py - 2 * uy)])
                halo = QPainterPath()
                halo.addPolygon(chev)
                halo.closeSubpath()
                self._halo(anchor, halo)
                gl = self._child(sc.addPolygon(chev), anchor)
                gl.setPen(self._ring_pen())
                gl.setBrush(QBrush(color))
            # the label, zoom-immune at the quad's centre
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            lab = sc.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
            lab.setPos(cx, cy)
            lab.setFlag(lab.GraphicsItemFlag.ItemIgnoresTransformations)
            lab.setData(0, "regionlabel")
            lab.setData(1, i)
            if r.get("label") or warn:
                self._label(lab, ("⚠ " if warn else "") + str(r.get("label") or ""),
                            self._ink["warn_text"] if warn else pal["text"], tip=tip)
            self._region_items[i] = it
            self._region_label_items[i] = lab

    def _draw_pending_region(self):
        """The quad mid-draw: accepted corners + the legs between them (the 4th click
        completes and emits — nothing here persists past it)."""
        if not self._region_mode or not self._pending_region or self._cam is None:
            return
        sc, pal = self._scene, self.pal
        pts = self._region_pts_px(self._pending_region)
        if pts is None:
            return
        case, pen = self._cased_pen(pal["accent"], 1.6)
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            sc.addLine(ax, ay, bx, by, case).setData(0, "casing")
            ln = sc.addLine(ax, ay, bx, by, pen)
            ln.setData(0, "regionpending")
        for n, (x, y) in enumerate(pts):
            anchor = sc.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
            anchor.setPos(x, y)
            anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
            anchor.setData(0, "regionpending")
            box = QRectF(-_HANDLE_R, -_HANDLE_R, 2 * _HANDLE_R, 2 * _HANDLE_R)
            halo = QPainterPath()
            halo.addEllipse(box)
            self._halo(anchor, halo)
            dot = self._child(sc.addEllipse(box), anchor)
            dot.setPen(self._ring_pen())
            dot.setBrush(QBrush(QColor(pal["accent"])))
            self._label(anchor, str(n), pal["text"])

    def _draw_region_handles(self):
        """Corner handles, region mode only, TOPMOST (the handles-last law): squares (a
        vertex-dot is a trace thing). No corner INDEX labels: four per quad overprinted every
        far-back zone into an unreadable cluster (P21), and the order they spoke for -- the
        walk-out edge, corners 0->1 -- is already drawn, as the gateway's chevron edge."""
        if not self._region_mode or not self._regions or self._cam is None:
            return
        sc = self._scene
        for r in self._regions:
            pts = self._region_pts_px(r["quad"])
            if pts is None:
                continue
            color = QColor(self.pal["warn"] if r.get("warn") else self.pal["accent"])
            for ci, (x, y) in enumerate(pts):
                anchor = sc.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
                anchor.setPos(x, y)
                anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
                anchor.setData(0, "regionpt")
                anchor.setData(1, (r["i"], ci))
                box = QRectF(-_HANDLE_R, -_HANDLE_R, 2 * _HANDLE_R, 2 * _HANDLE_R)
                halo = QPainterPath()
                halo.addRect(box)
                self._halo(anchor, halo, grab=True)
                sq = self._child(sc.addRect(box), anchor)
                sq.setPen(self._ring_pen())
                sq.setBrush(QBrush(color))
                mark_grabbable(sq)
                self._region_handle_items[(r["i"], ci)] = anchor

    def _region_h_hint(self, quad):
        """The drag/click plane height for a region: its corners' mean floor height (one
        stable plane per gesture — a corner sliding between stacked floors mid-drag would
        judder)."""
        ys = [self._zone_y(x, z) for x, z in quad]
        return sum(ys) / len(ys) if ys else 0.0

    def _begin_region_corner_drag(self, i, ci):
        r = self._region_row(i)
        if r is None or (i, ci) not in self._region_handle_items:
            return False
        quad = [tuple(p) for p in r["quad"]]
        self._drag = {"kind": "rpt", "i": i, "ci": ci, "quad": quad,
                      "start": list(quad), "h": self._region_h_hint(quad)}
        self._hide_region_law(i)
        self._update_coords()
        return True

    def _begin_region_quad_drag(self, i, grab_canvas):
        r = self._region_row(i)
        if r is None or i not in self._region_items:
            return False
        quad = [tuple(p) for p in r["quad"]]
        h = self._region_h_hint(quad)
        try:
            gw = self._px_to_zone_world(grab_canvas, h)
        except imagefield.ImageFieldError:
            return False
        self._drag = {"kind": "rquad", "i": i, "quad": quad, "start": list(quad),
                      "grab": gw, "h": h}
        self._hide_region_law(i)
        self._update_coords()
        return True

    def _hide_region_law(self, i):
        for it in self._region_law_items.get(i, []):
            it.setVisible(False)                   # stale mid-drag; the release rebuild re-judges

    def _move_region_items(self, i, quad):
        """One live drag step's redraw: the polygon, the walk-out edge, the handles, and the
        label follow the quad; the law overlays stay hidden until the release re-judge."""
        pts = self._region_pts_px(quad)
        if pts is None:
            return
        poly = QPolygonF([QPointF(x, y) for x, y in pts])
        if i in self._region_items:
            self._region_items[i].setPolygon(poly)
        if i in self._region_edge_items:
            self._region_edge_items[i].setLine(pts[0][0], pts[0][1], pts[1][0], pts[1][1])
        for k, case in enumerate(self._region_case_items.get(i, [])):   # casings ride along
            if k == 0:
                case.setPolygon(poly)
            else:
                case.setLine(pts[0][0], pts[0][1], pts[1][0], pts[1][1])
        for ci, (x, y) in enumerate(pts):
            a = self._region_handle_items.get((i, ci))
            if a is not None:
                a.setPos(x, y)
        lab = self._region_label_items.get(i)
        if lab is not None:
            lab.setPos(sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

    def _region_menu(self, i, global_pos):
        """The region list-op menu, behind a seam (tests drive the choice without a popup)."""
        from PySide6.QtWidgets import QMenu
        r = self._region_row(i)
        if r is None:
            return
        menu = QMenu(self)
        tgt = rot = word = None
        if r.get("kind") == "gateway":
            tgt = menu.addAction("Set gateway target…")
            rot = menu.addAction("Walk-out edge → next edge (rotate corners)")
        else:
            word = menu.addAction("Set message…")
        rm = menu.addAction(f"Delete {r.get('label') or f'zone {i}'}")
        act = menu.exec(global_pos)
        if act is None:
            return
        if act is tgt:
            self.region_retarget.emit(i)
        elif act is word:
            self.region_reword.emit(i)
        elif act is rot:
            q = [tuple(p) for p in r["quad"]]
            self.region_changed.emit(i, q[1:] + q[:1])
        elif act is rm:
            self.region_deleted.emit(i)

    def _resolve_data(self, item, tag):
        """Resolve a press hit to ``tag``'s payload from the hit item ALONE. NEVER walk
        parentItem() here: when it returns None (any tag-miss hit — the art, a leg, the
        frame) shiboken flips the wrapper Python-owned, and the wrapper's death then
        DELETES the C++-owned item (studies/pyside-gc-crash). Children carry their
        anchor's tag in data slots 2/3 (``_child`` stamps them), so the hit itself
        always holds the answer."""
        try:
            if item is not None:
                if item.data(0) == tag:
                    return item.data(1)
                if item.data(2) == tag:
                    return item.data(3)
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
        if not (self._trace_mode or self._contact_mode or self._region_mode) or not self._trace:
            return                             # contact + region modes keep the polygon VISIBLE,
                                               # inert: a door belongs on the walkable edge (T29)
        pal, sc = self.pal, self._scene
        worlds = self._trace_worlds()
        case, pen = self._cased_pen(pal["accent"], 1.6)   # cosmetic: legs survive fit zoom
        pts = [QPointF(cx, cy) for cx, cy in self._trace]
        legs = [(a, b, pen) for a, b in zip(pts, pts[1:])]
        if len(pts) > 2:                           # the closing leg, dashed (the tracer's idiom)
            dash = QPen(pen)
            dash.setDashPattern([4, 4])
            legs.append((pts[-1], pts[0], dash))
        for a, b, _ in legs:                       # casings first, under every leg
            sc.addLine(a.x(), a.y(), b.x(), b.y(), case).setData(0, "casing")
        for a, b, p in legs:
            ln = sc.addLine(a.x(), a.y(), b.x(), b.y(), p)
            ln.setData(0, "traceline")
        self._draw_outset(worlds)
        if self._region_mode:
            return                             # the edge only: dots + indices are trace furniture
        for i, (cx, cy) in enumerate(self._trace):
            bad = worlds[i] is None
            color = QColor(pal["error"] if bad else pal["accent"])
            anchor = sc.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
            anchor.setPos(cx, cy)
            anchor.setFlag(anchor.GraphicsItemFlag.ItemIgnoresTransformations)
            anchor.setData(0, "tracept")
            anchor.setData(1, i)
            box = QRectF(-_HANDLE_R, -_HANDLE_R, 2 * _HANDLE_R, 2 * _HANDLE_R)
            halo = QPainterPath()
            halo.addEllipse(box)
            self._halo(anchor, halo, grab=self._trace_mode, hollow=bad)
            dot = self._child(self._scene.addEllipse(box), anchor)
            if bad:                                # INVALID speaks by SHAPE as well as colour:
                dot.setPen(QPen(color, 2.2))       # a hollow ring and a ✕ (V13)
                dot.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            else:
                dot.setPen(self._ring_pen())
                dot.setBrush(QBrush(color))
            self._label(anchor, f"{i} ✕" if bad else str(i),
                        self._ink["error_text"] if bad else pal["text"])
            if self._trace_mode:                   # vertices drag only while TRACING (contact
                mark_grabbable(dot)                # mode renders them inert context)
            if bad:
                anchor.setToolTip("above the horizon — the build will refuse this vertex")
            self._trace_items.append({"anchor": anchor, "i": i})

    def _draw_outset(self, worlds):
        """The +48u collision-outset ring the build will actually emit: the build's OWN ring
        (``imagefield.walk_edge`` -- repeats dropped, sharp tips bevelled), re-projected per
        vertex. Suspended while any vertex is invalid, and for an outline the build refuses —
        a preview computed from partial geometry would lie."""
        if len(worlds) < 3 or any(w is None for w in worlds):
            return
        try:
            grown = imagefield.walk_edge([tuple(w) for w in worlds])
            ring = [imagefield.world_to_click(self._cam, g) for g in grown]
        except imagefield.ImageFieldError:
            return
        poly = QPolygonF([QPointF(cx, cy) for cx, cy in ring])
        case, pen = self._cased_pen(QColor(255, 255, 255), 1.2, [2, 3])   # a light line on a
        self._scene.addPolygon(poly, case).setData(0, "casing")          # dark underlay
        it = self._scene.addPolygon(poly, pen)
        it.setData(0, "outset")
        it.setToolTip(f"+{imagefield.COLLISION_OUTSET:g}u collision outset — the walkmesh "
                      f"edge the build emits so the player centre reaches the visual edge")

    # -- trace gestures: press resolves a handle, move updates ONLY the grabbed items, release
    # commits ONE callback and the re-render redraws everything (the StageCanvas contract)
    def _resolve_vertex(self, item):
        i = self._resolve_data(item, "tracept")    # the hit alone — see _resolve_data
        return None if i is None else int(i)

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

    def _begin_marker_drag(self, i):
        if not 0 <= i < len(self._markers) or i not in self._marker_items:
            return False
        p = self._marker_items[i].pos()
        self._drag = {"kind": "marker", "i": i, "pt": (p.x(), p.y())}
        self._update_coords()
        return True

    def _marker_menu(self, i, global_pos):
        """The marker's list-op menu, behind a seam (tests drive the choice without a popup).
        The host owns the delete -- and refuses what it may not delete, saying why."""
        from PySide6.QtWidgets import QMenu
        if not 0 <= i < len(self._markers):
            return
        m = self._markers[i]
        menu = QMenu(self)
        rm = menu.addAction(f"Delete {m.get('label') or m.get('kind')}")
        if menu.exec(global_pos) is rm:
            self.marker_deleted.emit(i)

    def _drag_canvas(self, cx, cy):
        """One drag step, CANVAS px (tests drive this directly — the testable seam)."""
        d = self._drag
        if not d:
            return
        if d.get("kind") == "marker":
            d["pt"] = (cx, cy)
            self._marker_items[d["i"]].setPos(cx, cy)
        elif d.get("kind") == "cpt":
            d["pt"] = (cx, cy)
            self._contact_items[d["i"]].setPos(cx, cy)
        elif d.get("kind") == "cimg":
            d["pt"] = (cx - d["grab"][0], cy - d["grab"][1])
            self._cutout_items[d["i"]].setPos(*d["pt"])
        elif d.get("kind") == "rpt":
            try:
                w = self._px_to_zone_world(QPointF(cx, cy), d["h"])
            except imagefield.ImageFieldError:
                return                             # above the horizon: the corner stays put
            d["quad"][d["ci"]] = w
            self._move_region_items(d["i"], d["quad"])
        elif d.get("kind") == "rquad":
            try:
                w = self._px_to_zone_world(QPointF(cx, cy), d["h"])
            except imagefield.ImageFieldError:
                return
            dx, dz = w[0] - d["grab"][0], w[1] - d["grab"][1]
            d["quad"] = [(x + dx, z + dz) for x, z in d["start"]]
            self._move_region_items(d["i"], d["quad"])
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
        self._hint.hide()                          # a drag, too, is the first gesture (P18)
        if d.get("kind") == "marker":              # re-raycast where it was let go (P16)
            m = self._markers[d["i"]]
            try:
                hit = imagefield.click_to_surface(self._cam, self._surface_tris, d["pt"])
            except imagefield.ImageFieldError as e:
                self._rebuild()                    # it goes back where the document has it
                self.click_refused.emit(f"{m.get('label') or m.get('kind')} is back where it "
                                        f"was — {e}")
                return
            self.marker_moved.emit(d["i"], self._surface_payload(hit))
            self._rebuild()                        # document truth: the host's re-feed moves it
            return
        if d.get("kind") == "cpt":
            if d["pt"] != d["start"]:
                self.contact_moved.emit(d["i"], round(d["pt"][0], 1), round(d["pt"][1], 1))
            return
        if d.get("kind") == "cimg":
            if d["pt"] != d["start"]:
                self.cutout_moved.emit(d["i"], round(d["pt"][0], 1), round(d["pt"][1], 1))
            return
        if d.get("kind") in ("rpt", "rquad"):
            if d["quad"] != d["start"]:
                self.region_changed.emit(
                    d["i"], [(round(x, 1), round(z, 1)) for x, z in d["quad"]])
            self._rebuild()                        # document truth: a host that took the change
            return                                 # re-fed it; one that refused it did not (V10)
        if d["pt"] != tuple(self._trace[d["i"]]):
            if self._cam is not None:              # the click's own refusal, for a drag (V7)
                try:
                    imagefield.click_to_world(self._cam, d["pt"])
                except imagefield.ImageFieldError as e:
                    self._rebuild()                # the vertex goes back where it was
                    self.click_refused.emit(str(e))
                    return
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
        kind = d.get("kind", "vertex")
        if kind in ("rpt", "rquad"):
            q = d["quad"]
            if kind == "rpt":                      # (no corner number: the art draws none)
                x, z = q[d["ci"]]
                head = f"zone {d['i']} · corner at world x {x:.0f} · z {z:.0f}"
            else:
                cx0 = sum(p[0] for p in q) / len(q)
                cz0 = sum(p[1] for p in q) / len(q)
                head = f"zone {d['i']} · centre x {cx0:.0f} · z {cz0:.0f}"
            self._coords.setText(head)
            self._coords.show()
            self._place_hint()
            return
        cx, cy = d["pt"]
        if kind == "marker":
            m = self._markers[d["i"]]
            head = str(m.get("label") or m.get("kind"))
            try:
                hit = imagefield.click_to_surface(self._cam, self._surface_tris, (cx, cy))
                head += f" · world x {hit['pos'][0]:.0f} · z {hit['pos'][2]:.0f}"
            except imagefield.ImageFieldError:
                head += " · off the walkable floor"
            self._coords.setText(head)
            self._coords.show()
            self._place_hint()
            return
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
        """Fit the frame to the view. Measured from ``maximumViewportSize()`` -- the viewport
        as if no scrollbar had range -- never from the live viewport, which a zoomed
        transform's scrollbars have shrunk (Ctrl+0 from a zoomed view fitted ~2% small, V4).
        The fit is a STATE the view stays in (``_fit_zoom``) until the author picks their own
        zoom, so a layout change re-fits instead of cropping the art (T24)."""
        r = self._scene.sceneRect()
        if r.isEmpty():
            return
        m = self.maximumViewportSize()
        vw, vh = max(1, m.width()), max(1, m.height())
        z = min(vw / max(1.0, r.width()), vh / max(1.0, r.height())) * 0.97
        z = max(_ZOOM_MIN, min(_ZOOM_MAX, z))
        self.resetTransform()
        self.scale(z, z)
        self._zoom = z
        self._fit_zoom = z
        self.centerOn(r.center())
        self._decollide_labels()                   # screen-px labels re-negotiate per zoom

    def paintEvent(self, ev):                      # noqa: N802 (Qt override)
        if self._fit_pending:                      # deferred to the first REAL paint: at set time
            self._fit_pending = False              # the tab may be hidden, the viewport stale
            self._fit()
        super().paintEvent(ev)

    def resizeEvent(self, ev):                     # noqa: N802 (Qt override)
        super().resizeEvent(ev)
        if self._zoom == self._fit_zoom and not self._fit_pending:   # still at the fit:
            self._fit()                                              # follow the layout (T24)
        else:
            self._decollide_labels()               # the right-edge mirror reads the width
        self._place_hint()

    def scrollContentsBy(self, dx, dy):            # noqa: N802 (Qt override)
        """The pills are viewport children and QWidget::scroll moves them with the art: re-pin
        after every scroll (V2; floorplandoc's identical fix)."""
        super().scrollContentsBy(dx, dy)
        self._place_hint()

    def wheelEvent(self, event):                   # noqa: N802 (Qt override)
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            dy = event.angleDelta().y()            # a sideways wheel is not a zoom (V5), and a
            if dy:                                 # touchpad's small deltas are a fraction of
                f = 1.15 ** (dy / 120)             # one 120 detent, not one step each
                z = max(_ZOOM_MIN, min(_ZOOM_MAX, self._zoom * f))
                if z != self._zoom:
                    self.scale(z / self._zoom, z / self._zoom)
                    self._zoom = z
                    self._decollide_labels()
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event):                # noqa: N802 (Qt override)
        if event.key() == Qt.Key.Key_Escape and self._drag:
            self._cancel_drag()                    # Esc aborts a live drag (V8)
            event.accept()
            return
        if (event.key() == Qt.Key.Key_Escape and self._region_mode
                and self._pending_region):
            self._pending_region = []              # abandon the quad mid-draw
            self._rebuild()
            event.accept()
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_0:
                self._fit()
                event.accept()
                return
            if event.key() == Qt.Key.Key_1:
                self.resetTransform()
                self._zoom = 1.0
                self._decollide_labels()
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
            if self._place_mode:                   # a placed marker out-ranks the floor (P16)
                for it in under:
                    mi = self._resolve_data(it, "marker")
                    if (mi is not None and not self._markers[int(mi)].get("locked")
                            and self._begin_marker_drag(int(mi))):
                        self._drag["press"] = event.position()   # no travel = a click on it
                        event.accept()
                        return
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
                        self._drag["press"] = event.position()   # a no-travel release may
                        event.accept()                           # still be a click (V9)
                        return
            if self._region_mode and not self._pending_region:   # mid-draw, clicks are corners
                for it in under:                   # corner handles out-rank the quad body
                    pay = self._resolve_data(it, "regionpt")
                    if pay is not None and self._begin_region_corner_drag(*pay):
                        event.accept()
                        return
                for it in under:
                    for tag in ("regionquad", "regionedge"):
                        ri = self._resolve_data(it, tag)
                        if ri is not None and self._begin_region_quad_drag(
                                int(ri), self._widget_to_canvas(event.position())):
                            self._drag["press"] = event.position()   # ...or a corner (P24)
                            event.accept()
                            return
            self._press_pos = event.position()
        super().mousePressEvent(event)             # the pan machinery still runs

    def _cancel_drag(self):
        """Abandon a live drag: the re-render redraws every item from the fed truth, which a
        drag never touches before its release -- so this IS the restore (V3, V8)."""
        self._coords.hide()
        self._rebuild()                            # clears _drag with the scene

    def mouseMoveEvent(self, event):               # noqa: N802 (Qt override)
        if self._drag and not event.buttons() & Qt.MouseButton.LeftButton:
            self._cancel_drag()                    # its release was lost (a modal menu took it):
                                                   # never let a drag follow the HOVER (V3)
        if self._drag:
            sp = self._widget_to_canvas(event.position())
            self._drag_canvas(sp.x(), sp.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):            # noqa: N802 (Qt override)
        if self._drag and event.button() == Qt.MouseButton.LeftButton:
            d = self._drag
            press = d.get("press")                 # set only where a click competes with a grab
            if (press is None or (event.position() - press).manhattanLength() > _CLICK_SLOP_PX
                    or (d.get("kind") == "cimg" and not self._contact_mode)):
                self._end_vertex_drag()
                event.accept()
                return
            if d.get("kind") == "marker":          # a click ON a marker places nothing: the
                self._cancel_drag()                # host says what it is and how to move it
                self._hint.hide()
                self.marker_clicked.emit(d["i"])
                event.accept()
                return
            self._cancel_drag()                    # it never travelled: a CLICK, not a drag --
            event.accept()                         # a contact on a snip's body (V9), the first
        else:                                      # corner inside a drawn quad (P24)
            press, self._press_pos = self._press_pos, None
            super().mouseReleaseEvent(event)
        if (press is None or event.button() != Qt.MouseButton.LeftButton
                or self._cam is None):
            return
        travel = (event.position() - press).manhattanLength()
        if travel > _CLICK_SLOP_PX:
            return                                 # it was a pan
        self._hint.hide()                          # a click: the pill has been read (P18)
        if self._contact_mode:                     # Rung 2: the raw canvas pixel; the host judges it
            c = self._widget_to_canvas(event.position())
            self.contact_clicked.emit(c.x(), c.y())
            return
        if self._region_mode:                      # Rung 4: four corners build one region
            c = self._widget_to_canvas(event.position())
            h = (self._zone_y(*self._pending_region[-1]) if self._pending_region else 0.0)
            try:
                w = self._px_to_zone_world(c, h)
            except imagefield.ImageFieldError as e:
                self.click_refused.emit(str(e))
                return
            self._pending_region.append((round(w[0], 1), round(w[1], 1)))
            if len(self._pending_region) >= 4:
                quad, self._pending_region = list(self._pending_region), []
                self.region_drawn.emit(quad)       # the host writes + re-feeds set_regions
            self._rebuild()
            return
        if self._place_mode:                       # Rung 3: the click raycasts the walkmesh
            for it in self.items(event.position().toPoint()):
                mi = self._resolve_data(it, "marker")
                if mi is not None:                 # a locked marker: it pans, but a click on it
                    self.marker_clicked.emit(int(mi))   # places nothing -- the host says why
                    return
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
        if self._region_mode:
            if self._pending_region:               # right-click abandons the quad mid-draw
                self._pending_region = []
                self._rebuild()
                event.accept()
                return
            for it in self.items(event.pos()):
                for tag in ("regionpt", "regionquad", "regionedge", "regionlabel"):
                    pay = self._resolve_data(it, tag)
                    if pay is not None:
                        i = pay[0] if tag == "regionpt" else int(pay)
                        self._region_menu(i, event.globalPos())
                        event.accept()
                        return
            return super().contextMenuEvent(event)
        if self._place_mode:
            for it in self.items(event.pos()):
                mi = self._resolve_data(it, "marker")
                if mi is not None:
                    m = self._markers[int(mi)]
                    if not (m.get("locked") or m.get("keep")):   # no Delete the host refuses
                        self._marker_menu(int(mi), event.globalPos())
                    event.accept()
                    return
            return super().contextMenuEvent(event)
        if not self._trace_mode:
            return super().contextMenuEvent(event)
        i = next((v for v in (self._resolve_vertex(it) for it in self.items(event.pos()))
                  if v is not None), None)
        if i is None:
            return super().contextMenuEvent(event)
        self._vertex_menu(i, event.globalPos())
        event.accept()
