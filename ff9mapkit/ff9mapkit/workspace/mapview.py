"""A QGraphicsView campaign MAP for the Workspace -- the visual twin of the project tree.

The placement is the SAME tk-free core the tkinter Campaign Editor used: ``editor.graphview.compute_layout``
lays a :class:`..campaign.CampaignGraph` out top-down in BFS levels (entry at the top, unreachable members
below) and returns absolute node/edge/seam coordinates. This module RENDERS that ``GraphLayout`` into a Qt
scene and turns a double-click into an open-member call. The rendering has since grown past the tk twin --
gateway ribbons (curved, two-way pairs merged into one both-ends line), rounded art windows, a quiet dot
grid, Ctrl+scroll zoom, and CALIBRE-scaled text -- but the LAYOUT stays the shared pure core, so node
placement remains unit-testable headless and identical to what the layout tests pin.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF)
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from ..editor.graphview import compute_layout

_THUMB_H = 86                                   # the art band inside a node at 100% text scale
_ART_R = 5                                      # the art window's corner rounding (inside the r=10 card)
_GRID = 26                                      # dot-grid pitch (px, scene units)
_ZOOM_MIN, _ZOOM_MAX = 0.35, 2.5                # Ctrl+scroll clamp


class _DotGridScene(QGraphicsScene):
    """The scene owns its ground: the surface fill + a whisper-quiet dot grid -- the cartography feel
    under the nodes. On the SCENE (not the view) so any renderer sees it (the view, scene.render()
    grabs, a future print/export). Decorative, sub-informational by design: border-on-surface is
    already a low pair and the alpha takes it well below any floor that applies to MEANING (it encodes
    none). Reads the palette through its view so a retheme needs no re-wiring."""

    def __init__(self, view):
        super().__init__(view)
        self._view = view

    def drawBackground(self, painter, rect):       # noqa: N802 (Qt override)
        painter.save()                             # pen/brush changes must not leak into item painting
        painter.fillRect(rect, QColor(self._view.pal["surface"]))
        dot = QColor(self._view.pal["border"])
        dot.setAlpha(110)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(dot)
        x = math.floor(rect.left() / _GRID) * _GRID
        while x <= rect.right():
            y = math.floor(rect.top() / _GRID) * _GRID
            while y <= rect.bottom():
                painter.drawRect(QRectF(x, y, 2.0, 2.0))
                y += _GRID
            x += _GRID
        painter.restore()


class CampaignMap(QGraphicsView):
    """A scrollable, pannable, Ctrl+scroll-zoomable node-link map of a campaign. ``on_open(name)`` fires
    on double-clicking a node; the open member is highlighted (accent fill). Call :meth:`render` with a
    CampaignGraph.

    ``thumbs`` (optional) is ``thumbs(name) -> png path | None`` -- when ANY member has a ready background
    thumbnail, nodes grow an art band showing the actual room (the layout falls back to the classic compact
    boxes while nothing is cached, so a game-less machine sees exactly the old map). ``scale`` is the
    CALIBRE text dial (an int percent) -- the map is custom-painted, so no QSS role can reach its text;
    the shell hands the dial in here the same way it does for the painted Home hero."""

    def __init__(self, palette, *, on_open=None, thumbs=None, scale=100):
        super().__init__()
        # A RAW palette, deliberately. This module reads only raw tokens (see `_draw_empty`), so a derive()
        # here would have zero consumers -- the `info` mistake, which this file's sibling comments spend
        # real words warning about. And raw + DIRECT INDEXING is the property worth having: a derived key
        # read from here now raises LOUDLY, instead of a `.get` quietly serving a fallback forever.
        self.pal = palette
        self.on_open = on_open
        self.thumbs = thumbs
        self._graph = None
        self._layout = None
        self._current = None
        self._use_thumbs = False
        self._scale = scale if scale in range(50, 301) else 100
        self._band_h = _THUMB_H                        # re-derived per render (scales with the dial)
        self._zoom = 1.0
        self._scene = _DotGridScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)        # click-drag to pan
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)   # zoom at the cursor
        self.setBackgroundBrush(QColor(palette["surface"]))
        self._draw_empty()                                             # teaching empty-state until a campaign opens

    # -- text (CALIBRE) --
    def _font(self, pt, bold=False):
        """A scene font at the dial's size -- the ONLY place map text sizes come from."""
        weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
        return QFont("Segoe UI", max(1, round(pt * self._scale / 100)), weight)

    def set_scale(self, pct):
        """The CALIBRE dial moved: re-derive every font + the art-band/node geometry and redraw."""
        pct = pct if pct in range(50, 301) else 100
        if pct == self._scale:
            return
        self._scale = pct
        if self._graph is not None:
            self.render(self._graph, self._current)
        else:
            self._draw_empty()

    # -- public --
    def render(self, graph, current=None):
        if graph is not self._graph:               # a NEW campaign: reset the user's zoom; a rerender
            self.resetTransform()                  # (same graph object -- thumb arrivals, highlight,
            self._zoom = 1.0                       # retheme) must NOT yank it
        self._graph = graph
        self._current = current
        k = self._scale / 100
        fm_t = QFontMetrics(self._font(10, bold=True))
        fm_s = QFontMetrics(self._font(8))
        text_zone = 8 + fm_t.height() + 2 + fm_s.height() + 9
        self._use_thumbs = bool(self.thumbs) and any(self.thumbs(n.name) for n in graph.nodes)
        if self._use_thumbs:                       # any art ready -> lay out with room for the art band
            self._band_h = round(_THUMB_H * k)
            self._layout = compute_layout(graph, node_w=round(176 * k),
                                          node_h=6 + self._band_h + 2 + text_zone)
        else:                                      # the classic compact boxes, dial-sized
            self._layout = compute_layout(graph, node_w=round(160 * k), node_h=text_zone)
        self._draw()

    def rerender(self):
        """Redraw from the stored graph (e.g. when a background thumbnail lands) -- a no-op when empty."""
        if self._graph is not None:
            self.render(self._graph, self._current)

    def highlight(self, name):
        if self._layout is None:
            return
        self._current = name
        self._draw()

    def clear(self):
        self._graph = None
        self._layout = None
        self._current = None
        self.resetTransform()
        self._zoom = 1.0
        self._draw_empty()                         # a teaching empty-state, not a black void

    def retheme(self, palette):
        """Re-tint on a LIVE theme switch: the map is custom-painted (QSS can't reach a QGraphicsScene), so
        the shell must hand it the new palette and redraw -- the stored graph if a campaign is open, else the
        empty-state. Without this, nodes / legend / the empty message keep the old theme's colours."""
        self.pal = palette
        self.setBackgroundBrush(QColor(palette["surface"]))
        if self._graph is not None:
            self.rerender()
        else:
            self._draw_empty()

    def resizeEvent(self, ev):                     # noqa: N802 (Qt override) -- re-center the empty message
        super().resizeEvent(ev)
        if self._layout is None:
            self._draw_empty()

    # -- drawing --
    def _draw_empty(self):
        """A centered teaching empty-state (no campaign open) -- the visual twin of the tree's empty state,
        so the Map tab never shows a bare canvas."""
        sc, pal = self._scene, self.pal
        sc.clear()
        vw = max(self.viewport().width(), 480)
        vh = max(self.viewport().height(), 320)
        sc.setSceneRect(0, 0, vw, vh)
        cx, cy = vw / 2, vh / 2
        # `muted`, NOT `text_subtle`, AND THE PREVIOUS ROUND ALREADY DECIDED THIS. KEYLINE moved the
        # TREE's icons OFF text_subtle ONTO muted and wrote the reason into its fence: text_subtle "is
        # fenced for TEXT against the elevation ramp and was never fenced as ink for a DRAWING: 3.06
        # (light) / 3.12 (solarized-light) -- a hair over the 3.0 non-text floor... muted is the same
        # tier's honest value." This glyph is the same icons.pixmap() family on the same $surface ground.
        #
        # This line read `pal.get("text_subtle", pal["muted"])`, which fell back 100% of the time in every
        # palette -- so it SAID text_subtle and DREW muted. Round 6 "fixed" the lie by making text_subtle
        # real, which dropped this glyph 5.08-6.99 -> 3.06-4.14: a 40% contrast cut onto the exact tier,
        # at the exact numbers, the round before had just moved the tree AWAY from. The `.get` was a lie
        # that told the truth; only the lie needed removing.
        subtle = pal["muted"]

        def _centered(text, font, color, dy):
            it = sc.addSimpleText(text, font)
            it.setBrush(QBrush(QColor(color)))
            br = it.boundingRect()
            it.setPos(cx - br.width() / 2, cy + dy)
            return it

        from . import icons                              # the ◇ glyph -> the campaign (layers) SVG icon
        k = self._scale / 100
        _pm = icons.pixmap("campaign", subtle, round(46 * k))
        _pit = sc.addPixmap(_pm)
        _pit.setPos(cx - (_pm.width() / _pm.devicePixelRatio()) / 2, cy - round(82 * k))
        _centered("No campaign open", self._font(13, bold=True), pal["text"], -24 * k)
        _centered("This map draws a campaign's fields and the gateways between them.",
                  self._font(9), pal["muted"], 6 * k)
        _centered("Open a campaign from the tree, or create one from Home.",
                  self._font(9), pal["muted"], 24 * k)

    def _draw(self):
        sc, pal, lay = self._scene, self.pal, self._layout
        if lay is None:
            self._draw_empty()
            return
        sc.clear()
        band = QFontMetrics(self._font(8)).height() + 22       # the legend strip above the map
        legend_w = self._draw_legend(-band)                    # may run wider than a small campaign
        sc.setSceneRect(-16, -band - 8, max(lay.width, 560, legend_w + 10) + 32, lay.height + band + 28)
        self._draw_edges(lay)                                  # ribbons under the nodes
        muted = QColor(pal["muted"])
        seam_font = self._font(8)
        plate = QColor(pal["surface"])
        plate.setAlpha(215)                                    # seam labels sit over ribbon crossings on
        for s in lay.seams:                                    # dense maps -- give each a quiet backing
            pen = QPen(muted, 1)
            pen.setDashPattern([2, 3])
            sc.addLine(s.nx, s.ny, s.x, s.y, pen)
            t = sc.addSimpleText("~ " + s.label, seam_font)
            t.setBrush(QBrush(muted))
            br = t.boundingRect()
            t.setPos(s.x + 4, s.y - br.height() / 2)
            t.setZValue(0.2)
            sc.addRect(s.x + 2, s.y - br.height() / 2 - 1, br.width() + 4, br.height() + 2,
                       QPen(Qt.PenStyle.NoPen), QBrush(plate)).setZValue(0.1)
        for n in lay.nodes:
            self._node(n)

    def _draw_legend(self, y):
        """A swatch legend along the top band so the node-colour / edge encoding is self-explanatory,
        ending with the one interaction the canvas can't advertise on its own (Ctrl+scroll zoom)."""
        sc, pal = self._scene, self.pal
        font = self._font(8)
        fm = QFontMetrics(font)
        dot = 9
        dy = (fm.height() - dot) / 2
        x = 6
        for col, label in ((pal["success"], "entry"), (pal["warn"], "needs export"),
                           (pal["error"], "unreachable"), (pal["accent"], "open")):
            sc.addEllipse(x, y + dy, dot, dot, QPen(QColor(col), 1), QBrush(QColor(col)))
            t = sc.addSimpleText(label, font)
            t.setBrush(QBrush(QColor(pal["muted"])))
            t.setPos(x + dot + 5, y)
            x += dot + 5 + t.boundingRect().width() + 16
        for label in ("→ gateway", "↔ both ways", "– – gated", "~ seam", "Ctrl+scroll to zoom"):
            t = sc.addSimpleText(label, font)
            t.setBrush(QBrush(QColor(pal["muted"])))
            t.setPos(x, y)
            x += t.boundingRect().width() + 16
        return x

    # -- edges --
    def _draw_edges(self, lay):
        """Gateway ribbons. Two passes:

        1. MERGE + CLASSIFY. Two-way pairs (A->B plus B->A, the overwhelmingly common case -- rooms
           connect both directions) merge into ONE ribbon with an arrowhead at each end; the old view
           drew both lines on top of each other and the four overlapping heads were the map's dominant
           noise. Each ribbon then knows which SIDE of each node it touches (bottom->top for the BFS
           flow, side-to-side within a row).
        2. DISTRIBUTE. All ribbons touching one node side get evenly spaced anchor points, ordered by
           where their other end lies -- without this every ribbon clamps to the same corner and busy
           nodes grow a braid of crossing curves at the border."""
        by = lay.by_name
        pairs = {}
        for e in lay.edges:
            key = (e.frm, e.to) if e.frm <= e.to else (e.to, e.frm)
            pairs.setdefault(key, []).append(e)
        ribbons = []
        for es in pairs.values():
            two_way = (len(es) == 2 and es[0].frm == es[1].to and es[0].to == es[1].frm
                       and es[0].gated == es[1].gated)
            if two_way:
                a, b = by[es[0].frm], by[es[0].to]
                if a.y > b.y:                      # normalize top-down; arrows land on both ends anyway
                    a, b = b, a
                ribbons.append({"a": a, "b": b, "gated": es[0].gated, "both": True})
            else:
                ribbons.extend({"a": by[e.frm], "b": by[e.to], "gated": e.gated, "both": False}
                               for e in es)
        slots = {}                                 # (node name, side) -> [(other-end key, ribbon, end)]
        for r in ribbons:
            a, b = r["a"], r["b"]
            if b.y >= a.y + a.h - 1:               # downward (the BFS-normal case)
                r["kind"] = "v"
                sides = (("bottom", a, "s", b.cx), ("top", b, "e", a.cx))
            elif a.y >= b.y + b.h - 1:             # upward (a lone back-edge)
                r["kind"] = "v"
                sides = (("top", a, "s", b.cx), ("bottom", b, "e", a.cx))
            elif a.cx <= b.cx:                     # same row: side to side
                r["kind"] = "h"
                sides = (("right", a, "s", b.cy), ("left", b, "e", a.cy))
            else:
                r["kind"] = "h"
                sides = (("left", a, "s", b.cy), ("right", b, "e", a.cy))
            for side, node, end, sortkey in sides:
                slots.setdefault((node.name, side), []).append((sortkey, r, end))
        for (name, side), lst in slots.items():
            node = by[name]
            lst.sort(key=lambda t: t[0])
            for i, (_k, r, end) in enumerate(lst):
                frac = (i + 1) / (len(lst) + 1)
                if side in ("top", "bottom"):
                    r[end] = (node.x + 12 + (node.w - 24) * frac,
                              node.y if side == "top" else node.y + node.h)
                else:
                    r[end] = (node.x if side == "left" else node.x + node.w,
                              node.y + 10 + (node.h - 20) * frac)
        for r in ribbons:
            self._ribbon(r)

    def _ribbon(self, r):
        """One gateway as a cubic ribbon: leaves/enters node borders VERTICALLY (top-down flow), so
        connections read as a flowchart instead of the old centre-to-centre diagonal slashes. A ribbon
        spanning multiple rows bows out toward the nearer map edge instead of lancing through them."""
        muted = QColor(self.pal["muted"])
        (sx, sy), (ex, ey) = r["s"], r["e"]
        path = QPainterPath(QPointF(sx, sy))
        if r["kind"] == "v":
            dy = ey - sy
            sgn = 1 if dy >= 0 else -1
            pull = min(90.0, max(18.0, abs(dy) * 0.35)) * sgn
            c1 = QPointF(sx, sy + pull)
            c2 = QPointF(ex, ey - pull)
            rows = abs(dy) / (r["a"].h + 72)       # ~how many BFS rows this ribbon spans
            if rows > 1.6:                         # a multi-row lance -> bow it aside, out of the flow
                side = -1 if (sx + ex) / 2 <= self._layout.width / 2 else 1
                bulge = min(170.0, 52 + abs(dy) * 0.06) * side
                c1 += QPointF(bulge, 0)
                c2 += QPointF(bulge, 0)
        else:
            dx = ex - sx
            c1 = QPointF(sx + dx * 0.4, sy)
            c2 = QPointF(ex - dx * 0.4, ey)
        path.cubicTo(c1, c2, QPointF(ex, ey))
        pen = QPen(muted, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        if r["gated"]:
            pen.setDashPattern([5, 3])
        self._scene.addPath(path, pen)
        self._arrow_head(c2.x(), c2.y(), ex, ey, muted)        # tangent-aligned at the tip
        if r["both"]:
            self._arrow_head(c1.x(), c1.y(), sx, sy, muted)

    _MODE_GLOSS = {"borrow": "BG-borrow — reuses the real field's art",
                   "native": "native scene — ships its own art",
                   "editable": "editable scene — re-authorable art",
                   "verbatim": "verbatim — ships the real field's script + dialogue"}

    def _node_tooltip(self, n):
        bits = [f"{n.name} — id {n.new_id}", self._MODE_GLOSS.get(n.mode, n.mode)]
        if not n.reachable:
            bits.append("⚠ Not reachable from the entry field.")
        elif n.needs_export:
            bits.append("⚠ Needs a Blender export.")
        elif n.is_entry:
            bits.append("Entry field (where the campaign starts).")
        bits.append("Double-click to open.")
        return "\n".join(bits)

    def _cover_art(self, src, iw, band):
        """The thumbnail as a rounded-corner COVER crop of the art window (iw x band, logical px),
        rendered at the screen's device pixel ratio -- the icons.pixmap() idiom; a DPR=1 pixmap
        stretched over a HiDPI footprint is visibly blurrier than the vector nodes around it."""
        dpr = self.devicePixelRatioF()
        dev_w, dev_h = round(iw * dpr), round(band * dpr)
        s = max(dev_w / src.width(), dev_h / src.height())
        scaled = src.scaled(math.ceil(src.width() * s), math.ceil(src.height() * s),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation)
        cx = (scaled.width() - dev_w) // 2
        cy = (scaled.height() - dev_h) // 2
        crop = scaled.copy(cx, cy, dev_w, dev_h)
        out = QPixmap(dev_w, dev_h)
        out.fill(Qt.GlobalColor.transparent)
        p = QPainter(out)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, dev_w, dev_h), _ART_R * dpr, _ART_R * dpr)
        p.setClipPath(clip)
        p.drawPixmap(0, 0, crop)
        p.end()
        out.setDevicePixelRatio(dpr)
        return out

    def _node(self, n):
        sc, pal = self._scene, self.pal
        fm_t = QFontMetrics(self._font(10, bold=True))
        if not n.reachable:
            outline = pal["error"]
        elif n.needs_export:
            outline = pal["warn"]
        elif n.is_entry:
            outline = pal["success"]
        else:
            outline = pal["border"]
        current = (n.name == self._current)
        fill = pal["accent"] if current else pal["surface_btn"]
        tcol = pal["accent_fg"] if current else pal["text"]
        sub_col = pal["accent_fg"] if current else pal["muted"]
        path = QPainterPath()
        path.addRoundedRect(QRectF(n.x, n.y, n.w, n.h), 10, 10)
        body = sc.addPath(path, QPen(QColor(outline), 2 if outline != pal["border"] else 1), QBrush(QColor(fill)))
        items = [body]
        ty = n.y + 8                                       # where the title starts (below the art band, if any)
        if self._use_thumbs:
            band = self._band_h
            iw = int(n.w) - 12
            ty = n.y + 6 + band + 8
            png = self.thumbs(n.name) if self.thumbs else None
            src = QPixmap(png) if png else QPixmap()
            if not src.isNull():
                img = sc.addPixmap(self._cover_art(src, iw, band))
                img.setPos(n.x + 6, n.y + 6)
                items.append(img)
                seat = QPainterPath()                      # a hairline seat so the art reads as a window
                seat.addRoundedRect(QRectF(n.x + 6, n.y + 6, iw, band), _ART_R, _ART_R)
                items.append(sc.addPath(seat, QPen(QColor(pal["border"]), 1)))
            else:                                          # no art YET for this member: a quiet placeholder band
                ph = QPainterPath()
                ph.addRoundedRect(QRectF(n.x + 6, n.y + 6, iw, band), _ART_R, _ART_R)
                items.append(sc.addPath(ph, QPen(QColor(pal["border"]), 1), QBrush(QColor(pal["surface"]))))
        title_txt = fm_t.elidedText(n.name, Qt.TextElideMode.ElideMiddle, int(n.w) - 12)
        title = sc.addSimpleText(title_txt, self._font(10, bold=True))
        title.setBrush(QBrush(QColor(tcol)))
        title.setPos(n.cx - title.boundingRect().width() / 2, ty)
        sub = sc.addSimpleText(f"id {n.new_id} · {n.mode}", self._font(8))   # show the mode for every node
        sub.setBrush(QBrush(QColor(sub_col)))
        sub.setPos(n.cx - sub.boundingRect().width() / 2, ty + fm_t.height() + 2)
        tip = self._node_tooltip(n)                       # status + mode gloss + the double-click affordance
        items += [title, sub]
        for item in items:
            item.setToolTip(tip)

    def _arrow_head(self, x1, y1, x2, y2, color, size=11):
        dx, dy = x2 - x1, y2 - y1
        d = math.hypot(dx, dy)
        if d == 0:
            return
        ux, uy = dx / d, dy / d
        bx, by = x2 - ux * size, y2 - uy * size           # base of the head, back along the line
        px, py = -uy, ux                                  # perpendicular
        head = QPolygonF([QPointF(x2, y2),
                          QPointF(bx + px * size * 0.5, by + py * size * 0.5),
                          QPointF(bx - px * size * 0.5, by - py * size * 0.5)])
        self._scene.addPolygon(head, QPen(color, 0), QBrush(color))

    # -- interaction --
    def wheelEvent(self, event):                           # noqa: N802 (Qt override)
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            f = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            z = max(_ZOOM_MIN, min(_ZOOM_MAX, self._zoom * f))
            if z != self._zoom:
                self.scale(z / self._zoom, z / self._zoom)
                self._zoom = z
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event):                        # noqa: N802 (Qt override) -- Ctrl+0 = 1:1
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_0:
            self.resetTransform()
            self._zoom = 1.0
            event.accept()
            return
        super().keyPressEvent(event)

    def _node_at(self, view_pos):
        if self._layout is None:
            return None
        sp = self.mapToScene(view_pos)
        for n in self._layout.nodes:
            if n.x <= sp.x() <= n.x + n.w and n.y <= sp.y() <= n.y + n.h:
                return n.name
        return None

    def mouseMoveEvent(self, event):                       # noqa: N802 (Qt override)
        if not event.buttons():                            # plain hover (not a pan-drag): hint that nodes open
            over = self._node_at(event.position().toPoint())
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor if over else Qt.CursorShape.OpenHandCursor)
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):                # noqa: N802 (Qt override)
        name = self._node_at(event.position().toPoint())
        if name and self.on_open:
            self.on_open(name)
        else:
            super().mouseDoubleClickEvent(event)
