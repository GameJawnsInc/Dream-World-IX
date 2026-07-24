"""The "How it all fits" concept map -- a static node-link diagram of the domain model so a newcomer can see
the whole mental model at a glance: the spine (Journey ▸ Campaign ▸ Field ▸ what a field contains) plus the
off-spine referenced siblings (Battle / Overworld / Save). Each box opens its plain-language concept card.

Reuses the campaign-map DRAWING idiom (rounded nodes + arrowed edges, :mod:`.mapview`) but with a FIXED
hand-laid layout instead of a computed one -- the graph here is the vocabulary, not a project.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QDialog, QGraphicsScene, QGraphicsView, QLabel, QVBoxLayout

_NW, _NH = 150, 46                                  # node box size

# (term, title, subtitle, x, y).  term resolves via workspace.concepts; None term = a non-card label.
_NODES = [
    ("journey", "Journey", "the whole arc", 20, 20),
    ("campaign", "Campaign", "a chain of fields", 200, 20),
    ("field", "Field", "one explorable screen", 380, 20),
    ("gateway", "Gateway", "a door to another screen", 300, 120),
    ("story-flag", "Story flag", "a remembered on/off", 470, 120),
    ("encounter", "Encounter", "a random battle", 640, 120),
    ("bbg", "Battle", "the fight scene", 60, 210),
    ("overworld", "Overworld", "the world map", 230, 210),
    ("savepoint", "Save point", "opens the save menu", 400, 210),
]
# arrows: (from_index, to_index)
_EDGES = [(0, 1), (1, 2), (2, 3), (2, 4), (2, 5)]

# The spine is the trunk -- Journey ▸ Campaign ▸ Field -- everything else hangs off Field.  An edge
# whose BOTH ends are spine nodes is a trunk link (heavier); an edge into a leaf is a field-child (light).
_SPINE = (0, 1, 2)
_PLINTH_PAD = 12                                    # lip of raised band around the spine trio
_W_SPINE, _W_CHILD = 3, 1                           # per-edge pen weights: trunk vs field-child


def _is_spine_edge(a, b):
    return a in _SPINE and b in _SPINE


class ConceptMapView(QGraphicsView):
    """A read-only diagram; clicking a box calls ``on_concept(term)``.

    ``scale`` is CALIBRE's percent: the layout table is DESIGN-size (100%) and every drawn coordinate,
    box, and font multiplies by ``scale/100`` (the mapview idiom -- the scene is QPainter territory, so
    no stylesheet reaches it and it has to be told). The dialog is modal + rebuilt per open, so the
    scale is a constructor fact, not a live signal."""

    def __init__(self, palette, on_concept, scale=100):
        super().__init__()
        self.pal = palette
        self.on_concept = on_concept
        self._k = (scale if scale in range(50, 301) else 100) / 100
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QColor(palette["surface"]))
        self.setMinimumSize(round(820 * self._k), round(300 * self._k))
        self._boxes = []                            # (x, y, term) -- SCALED coords, same frame as clicks
        self._draw()

    def _font(self, pt, bold=False):
        """A scene font at the dial's size -- the only place this map's text sizes come from."""
        return QFont("Segoe UI", max(1, round(pt * self._k)),
                     QFont.Weight.Bold if bold else QFont.Weight.Normal)

    def _draw(self):
        sc, pal, k = self._scene, self.pal, self._k
        sc.clear()
        muted = QColor(pal["muted"])
        # The trunk plinth: a quiet raised band behind the spine trio, painted FIRST so the nodes and
        # arrows sit on top of it -- it fuses Journey ▸ Campaign ▸ Field into one backbone instead of
        # three loose boxes.  Elevation token (surface_btn) + a neutral border, no accent.
        nw, nh = _NW * k, _NH * k
        sx = [_NODES[i][3] * k for i in _SPINE]
        sy = [_NODES[i][4] * k for i in _SPINE]
        px, py = min(sx) - _PLINTH_PAD * k, min(sy) - _PLINTH_PAD * k
        pw = (max(sx) + nw) - min(sx) + 2 * _PLINTH_PAD * k
        ph = nh + 2 * _PLINTH_PAD * k
        plinth = QPainterPath()
        plinth.addRoundedRect(px, py, pw, ph, 12 * k, 12 * k)
        sc.addPath(plinth, QPen(QColor(pal["border"]), 1), QBrush(QColor(pal["surface_btn"])))
        for a, b in _EDGES:                          # arrows under the nodes, trunk links heavier
            ax, ay = _NODES[a][3] * k + nw / 2, _NODES[a][4] * k + nh
            bx, by = _NODES[b][3] * k + nw / 2, _NODES[b][4] * k
            weight = _W_SPINE if _is_spine_edge(a, b) else _W_CHILD
            sc.addLine(ax, ay, bx, by, QPen(muted, weight))
        for term, title, sub, x, y in _NODES:
            x, y = x * k, y * k
            path = QPainterPath()
            path.addRoundedRect(x, y, nw, nh, 8 * k, 8 * k)
            outline = pal["accent"] if term else pal["border"]
            sc.addPath(path, QPen(QColor(outline), 1), QBrush(QColor(pal["surface_btn"])))
            t = sc.addSimpleText(title, self._font(10, bold=True))
            t.setBrush(QBrush(QColor(pal["text"])))
            t.setPos(x + 10 * k, y + 6 * k)
            s = sc.addSimpleText(sub, self._font(8))
            s.setBrush(QBrush(muted))
            s.setPos(x + 10 * k, y + 25 * k)
            self._boxes.append((x, y, term))
        self.setSceneRect(sc.itemsBoundingRect().adjusted(-16 * k, -16 * k, 16 * k, 16 * k))

    def mousePressEvent(self, event):                # noqa: N802 (Qt override)
        p = self.mapToScene(event.position().toPoint())
        nw, nh = _NW * self._k, _NH * self._k
        for x, y, term in self._boxes:
            if term and x <= p.x() <= x + nw and y <= p.y() <= y + nh:
                self.on_concept(term)
                return
        super().mousePressEvent(event)


def show_concept_map(parent, palette, on_concept, scale=100):
    """Open the 'How it all fits' map dialog. ``on_concept(term)`` opens that term's concept card.
    ``scale`` = CALIBRE's percent (the shell passes its live ``_text_scale``); the view's minimum and
    every drawn glyph track it, so the dialog's size stays a function of its content -- round 8's last
    deliberately-unconverted popup, converted."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("How it all fits")
    lay = QVBoxLayout(dlg)
    intro = QLabel("The pieces of a Dream World IX project, and how they nest. Click any box to learn what "
                   "it is. Everything comes from your own copy of the game.")
    intro.setWordWrap(True)
    intro.setProperty("role", "muted")
    lay.addWidget(intro)
    lay.addWidget(ConceptMapView(palette, on_concept, scale=scale))
    return dlg
