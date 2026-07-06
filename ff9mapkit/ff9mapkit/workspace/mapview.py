"""A QGraphicsView campaign MAP for the Workspace -- the visual twin of the project tree.

The placement is the SAME tk-free core the tkinter Campaign Editor uses: ``editor.graphview.compute_layout``
lays a :class:`..campaign.CampaignGraph` out top-down in BFS levels (entry at the top, unreachable members
below) and returns absolute node/edge/seam coordinates. This module only RENDERS that ``GraphLayout`` into
a Qt scene (rounded-rect nodes coloured by health, arrowed gateway edges -- dashed when gated -- and dashed
seam stubs) and turns a double-click into an open-member call. So both editors draw the identical map.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from ..editor.graphview import compute_layout

_THUMB_H = 86                                   # the art band inside a node (when any thumbnail is ready)


class CampaignMap(QGraphicsView):
    """A scrollable, pannable node-link map of a campaign. ``on_open(name)`` fires on double-clicking a
    node; the open member is highlighted (accent fill). Call :meth:`render` with a CampaignGraph.

    ``thumbs`` (optional) is ``thumbs(name) -> png path | None`` -- when ANY member has a ready background
    thumbnail, nodes grow an art band showing the actual room (the layout falls back to the classic compact
    boxes while nothing is cached, so a game-less machine sees exactly the old map). The taller node size is
    passed explicitly HERE so the shared tk layout defaults stay untouched."""

    def __init__(self, palette, *, on_open=None, thumbs=None):
        super().__init__()
        self.pal = palette
        self.on_open = on_open
        self.thumbs = thumbs
        self._graph = None
        self._layout = None
        self._current = None
        self._use_thumbs = False
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)        # click-drag to pan
        self.setBackgroundBrush(QColor(palette["surface"]))

    # -- public --
    def render(self, graph, current=None):
        self._graph = graph
        self._current = current
        self._layout = compute_layout(graph)
        self._use_thumbs = bool(self.thumbs) and any(self.thumbs(n.name) for n in self._layout.nodes)
        if self._use_thumbs:                       # any art ready -> relay out with room for the art band
            self._layout = compute_layout(graph, node_w=176, node_h=_THUMB_H + 52)
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
        self._scene.clear()
        self._graph = None
        self._layout = None
        self._current = None

    # -- drawing --
    def _draw(self):
        sc, pal, lay = self._scene, self.pal, self._layout
        sc.clear()
        if lay is None:
            return
        sc.setSceneRect(0, -42, max(lay.width, 560), lay.height + 42)   # a band at the top holds the legend
        self._draw_legend(-34)
        muted = QColor(pal["muted"])
        for e in lay.edges:                                            # edges under the nodes
            pen = QPen(muted, 2)
            if e.gated:
                pen.setDashPattern([5, 3])
            sc.addLine(e.x1, e.y1, e.x2, e.y2, pen)
            self._arrow_head(e.x1, e.y1, e.x2, e.y2, muted)
        for s in lay.seams:
            pen = QPen(muted, 1)
            pen.setDashPattern([2, 3])
            sc.addLine(s.nx, s.ny, s.x, s.y, pen)
            t = sc.addSimpleText("~ " + s.label, QFont("Segoe UI", 8))
            t.setBrush(QBrush(muted))
            t.setPos(s.x + 4, s.y - 7)
        for n in lay.nodes:
            self._node(n)

    def _draw_legend(self, y):
        """A swatch legend along the top band so the node-colour / edge-dash encoding is self-explanatory
        (the tkinter Campaign Editor ships the same)."""
        sc, pal = self._scene, self.pal
        font = QFont("Segoe UI", 8)
        x = 6
        for col, label in ((pal["success"], "entry"), (pal["warn"], "needs export"),
                           (pal["error"], "unreachable"), (pal["accent"], "open")):
            sc.addEllipse(x, y + 2, 10, 10, QPen(QColor(col), 1), QBrush(QColor(col)))
            t = sc.addSimpleText(label, font)
            t.setBrush(QBrush(QColor(pal["muted"])))
            t.setPos(x + 14, y)
            x += 14 + t.boundingRect().width() + 16
        for label in ("→ gateway", "– – gated", "~ seam"):
            t = sc.addSimpleText(label, font)
            t.setBrush(QBrush(QColor(pal["muted"])))
            t.setPos(x, y)
            x += t.boundingRect().width() + 16

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

    def _node(self, n):
        sc, pal = self._scene, self.pal
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
            ty = n.y + _THUMB_H + 12
            png = self.thumbs(n.name) if self.thumbs else None
            pm = QPixmap(png) if png else QPixmap()
            if not pm.isNull():
                iw = int(n.w - 12)
                pm = pm.scaledToWidth(iw, Qt.TransformationMode.SmoothTransformation)
                if pm.height() > _THUMB_H:                 # center-crop to the band (rooms are portrait-ish)
                    pm = pm.copy(0, (pm.height() - _THUMB_H) // 2, iw, _THUMB_H)
                img = sc.addPixmap(pm)
                img.setPos(n.x + 6, n.y + 6)
                items.append(img)
            else:                                          # no art YET for this member: a quiet placeholder band
                ph = sc.addRect(n.x + 6, n.y + 6, n.w - 12, _THUMB_H,
                                QPen(QColor(pal["border"]), 1), QBrush(QColor(pal["surface"])))
                items.append(ph)
        title = sc.addSimpleText(n.name, QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setBrush(QBrush(QColor(tcol)))
        title.setPos(n.cx - title.boundingRect().width() / 2, ty)
        sub = sc.addSimpleText(f"id {n.new_id} · {n.mode}", QFont("Segoe UI", 8))   # show the mode for every node
        sub.setBrush(QBrush(QColor(sub_col)))
        sub.setPos(n.cx - sub.boundingRect().width() / 2, ty + 18)
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
