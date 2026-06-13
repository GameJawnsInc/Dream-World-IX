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
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from ..editor.graphview import compute_layout


class CampaignMap(QGraphicsView):
    """A scrollable, pannable node-link map of a campaign. ``on_open(name)`` fires on double-clicking a
    node; the open member is highlighted (accent fill). Call :meth:`render` with a CampaignGraph."""

    def __init__(self, palette, *, on_open=None):
        super().__init__()
        self.pal = palette
        self.on_open = on_open
        self._layout = None
        self._current = None
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)        # click-drag to pan
        self.setBackgroundBrush(QColor(palette["surface"]))

    # -- public --
    def render(self, graph, current=None):
        self._layout = compute_layout(graph)
        self._current = current
        self._draw()

    def highlight(self, name):
        if self._layout is None:
            return
        self._current = name
        self._draw()

    def clear(self):
        self._scene.clear()
        self._layout = None
        self._current = None

    # -- drawing --
    def _draw(self):
        sc, pal, lay = self._scene, self.pal, self._layout
        sc.clear()
        if lay is None:
            return
        sc.setSceneRect(0, 0, lay.width, lay.height)
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
        sc.addPath(path, QPen(QColor(outline), 2 if outline != pal["border"] else 1), QBrush(QColor(fill)))
        title = sc.addSimpleText(n.name, QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setBrush(QBrush(QColor(tcol)))
        title.setPos(n.cx - title.boundingRect().width() / 2, n.y + 8)
        sub = sc.addSimpleText(f"id {n.new_id}" + ("" if n.mode == "borrow" else f" · {n.mode}"),
                               QFont("Segoe UI", 8))
        sub.setBrush(QBrush(QColor(sub_col)))
        sub.setPos(n.cx - sub.boundingRect().width() / 2, n.y + 26)

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

    def mouseDoubleClickEvent(self, event):                # noqa: N802 (Qt override)
        name = self._node_at(event.position().toPoint())
        if name and self.on_open:
            self.on_open(name)
        else:
            super().mouseDoubleClickEvent(event)
