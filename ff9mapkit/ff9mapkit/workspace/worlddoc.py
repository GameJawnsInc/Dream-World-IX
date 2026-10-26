"""The World document -- an ATLAS of the deployed custom overworld.

The overworld pillar (world-island / world-transplant / world-mountain / world-mirror) is the kit's
largest body of shipped content with zero GUI presence: every deployed island lives as loose
``Block[x][y]`` files under a mod folder, visible only to Explorer. This tab draws the engine's fixed
24x20 block grid as a chart and paints every deployed override onto it -- land, water carries, arming
stubs, donors, and the Disc4 mirror's health -- with a details card that hands you the block-centre
world coordinates for the debug menu's overworld teleport.

Laws this surface honours by construction:

- **No I/O uninvited.** Construction touches NOTHING (the startup-spend law), and no scan runs on tab
  show: every filesystem read is behind the user's own Scan / Rescan click, so a headless run, the
  smoke, and the a11y sweep never read the developer's install (the round-9 isolation law -- the
  recurring disease three review rounds running). The scan itself runs on a worker thread and
  marshals back via a Signal (the warm-only law's shape); ``refresh(sync=True)`` is the deterministic
  lane for tests and gui_snap.
- **The canvas is painted**, so CALIBRE reaches it only by hand: every text size derives from
  ``self._scale`` (the mapview rule), wired from ``shell._apply_text_scale``; ``retheme`` redraws.
- **One accent per surface**: the guide page's primary action (Scan) wears it via ``empty_state``;
  the atlas page has none -- selection's accent ring is the campaign map's established language,
  a drawn state, not a second CTA.
"""

from __future__ import annotations

import math
import threading

from PySide6.QtCore import QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QBrush, QColor, QDesktopServices, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication, QComboBox, QGraphicsRectItem, QGraphicsScene, QGraphicsSimpleTextItem,
    QGraphicsView, QHBoxLayout, QLabel, QPushButton, QStackedLayout, QVBoxLayout, QWidget,
)

from .. import config
from . import icons, widgets, worldscan

_CELL = 30                                        # one block's edge at 100% text scale (scene px)
_MARGIN = 26                                      # room for the row/col index labels
_ZOOM_MIN, _ZOOM_MAX = 0.3, 4.0                   # a 24x20 chart never needs the map's 0.15 floor
_GRID_ALPHA = 90                                  # the graticule: present, sub-informational (70 was
#                                                   invisible on the light palette -- snap-measured)
_KIND_ALPHA = {"land": 165, "water": 120, "stub": 90}
CARD_VIEW_FLOOR = 32                              # the 3D view's floor while a carry card is open (px)
STEP_MARK_H = 14.0                                # the picked step's pin on the 3D view (world units; rung C9)


def _fmt_bytes(n: int) -> str:
    if n >= 1 << 20:
        return f"{n / (1 << 20):.1f} MB"
    if n >= 1 << 10:
        return f"{n / (1 << 10):.0f} KB"
    return f"{n} B"


class _ChartScene(QGraphicsScene):
    """The scene owns its ground (the mapview law -- scene.render() grabs must see it too): the surface
    fill plus the 24x20 block graticule. Lines, not dots: this canvas IS a coordinate chart, and the
    lattice is the same grid the engine streams blocks on. Reads the palette through its view so a
    retheme needs no re-wiring."""

    def __init__(self, view):
        super().__init__(view)
        self._view = view

    def drawBackground(self, painter, rect):       # noqa: N802 (Qt override)
        painter.save()
        painter.fillRect(rect, QColor(self._view.pal["surface"]))
        cell = self._view.cell_px()
        line = QColor(self._view.pal["border"])
        line.setAlpha(_GRID_ALPHA)
        painter.setPen(QPen(line, 0))
        w, h = worldscan.GRID_COLS * cell, worldscan.GRID_ROWS * cell
        x0 = math.floor(max(rect.left(), 0) / cell) * cell
        x1 = min(rect.right(), w)
        y1 = min(rect.bottom(), h)
        x = x0
        while x <= x1 + 0.5:
            if rect.left() - cell <= x:
                painter.drawLine(int(x), int(max(rect.top(), 0)), int(x), int(y1))
            x += cell
        y = math.floor(max(rect.top(), 0) / cell) * cell
        while y <= y1 + 0.5:
            if rect.top() - cell <= y:
                painter.drawLine(int(max(rect.left(), 0)), int(y), int(min(rect.right(), w)), int(y))
            y += cell
        edge = QColor(self._view.pal["border"])
        painter.setPen(QPen(edge, 0))
        painter.drawRect(QRectF(0, 0, w, h))       # the map's true boundary: beyond it nothing streams
        painter.restore()


class AtlasCanvas(QGraphicsView):
    """The 24x20 overworld block grid with every deployed override painted on. Click a block to select
    it (``on_select((bx, by) | None)`` fires); arrow keys walk the deployed blocks; Ctrl+scroll zooms,
    Ctrl+0 refits, Ctrl+1 is 1:1. All the interaction grammar is the campaign map's, so the two
    canvases feel like one instrument."""

    def __init__(self, palette, *, on_select=None, on_name=None, scale=100):
        super().__init__()
        self.pal = palette                         # RAW palette, direct indexing -- the mapview rule
        self.on_select = on_select
        self.on_name = on_name                     # double-click on a deployed block -> name its landmass
        self._census = None
        self._stock = {}                           # (bx,by) -> "L"/"~": the real map's own geography
        self._selected = None
        self._cells = {}                           # (bx,by) -> the cell's ring item (selection repaint)
        self._scale = scale if scale in range(50, 301) else 100
        self._zoom = 1.0
        self._fit_pending = False
        self._scene = _ChartScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor(palette["surface"]))
        self.setAccessibleName("World atlas")
        self.setAccessibleDescription(
            "The overworld's 24 by 20 block grid with every deployed override painted on it")
        self._hint = QLabel("Ctrl+scroll zooms · Ctrl+0 fits · click a block", self.viewport())
        self._hint.setObjectName("worldHint")      # selector-scoped sheet below (the round-9 census law)
        self._hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._style_hint()
        self._draw()

    # -- text + geometry (CALIBRE) --
    def cell_px(self) -> float:
        """One block's edge in scene px -- geometry follows the dial like the map's poster cards."""
        return _CELL * self._scale / 100

    def _font(self, pt, bold=False):
        weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
        return QFont("Segoe UI", max(1, round(pt * self._scale / 100)), weight)

    def set_scale(self, pct):
        pct = pct if pct in range(50, 301) else 100
        if pct == self._scale:
            return
        self._scale = pct
        self._style_hint()
        self._draw()

    def _style_hint(self):
        self._hint.setFont(self._font(8))
        surf = QColor(self.pal["surface"])
        self._hint.setStyleSheet(
            "QLabel#worldHint {"
            f"color: {self.pal['muted']};"
            f"background: rgba({surf.red()},{surf.green()},{surf.blue()},0.86);"
            "border-radius: 9px; padding: 2px 9px; }")
        self._place_hint()

    def _place_hint(self):
        self._hint.adjustSize()                    # measure AFTER polish -- construction adjustSize lies
        vp = self.viewport()
        self._hint.move(vp.width() - self._hint.width() - 10,
                        vp.height() - self._hint.height() - 8)

    # -- public --
    def set_census(self, census, stock=None):
        if census is not self._census:
            self.resetTransform()
            self._zoom = 1.0
            self._fit_pending = True               # a NEW scan fits; a redraw keeps the user's view
        self._census = census
        self._stock = stock or {}
        if census is None:
            self._selected = None                  # an EMPTY selected block survives a rescan: any
        self._draw()                               # in-grid block is a real place, deployed or not

    def select(self, key):
        """Programmatic selection (tests, keyboard) -- repaints rings + fires on_select. ANY in-grid
        block is selectable: a deployed cell shows its census, an empty one its stock geography and
        (on clean ocean) its worth as a build site -- the click that used to be dead."""
        if self._census is None or (key is not None and not worldscan.block_in_grid(*key)):
            key = None
        self._selected = key
        self._draw()
        if self.on_select:
            self.on_select(key)

    def retheme(self, palette):
        self.pal = palette
        self.setBackgroundBrush(QColor(palette["surface"]))
        self._style_hint()
        self._draw()

    # -- fit --
    def _fit(self):
        r = self._scene.sceneRect()
        vw, vh = max(1, self.viewport().width()), max(1, self.viewport().height())
        z = min(1.0, vw / max(1.0, r.width()), vh / max(1.0, r.height()))
        z = max(_ZOOM_MIN, z)
        self.resetTransform()
        self.scale(z, z)
        self._zoom = z
        self.centerOn(r.center())

    def paintEvent(self, ev):                      # noqa: N802 (Qt override)
        if self._fit_pending:                      # deferred to the first REAL paint: at set_census time
            self._fit_pending = False              # the tab may be hidden and the viewport a stale guess
            self._fit()
        super().paintEvent(ev)

    def resizeEvent(self, ev):                     # noqa: N802 (Qt override)
        super().resizeEvent(ev)
        self._place_hint()

    # -- drawing --
    def _ignore_zoom(self, item):
        """Axis labels are CHART FURNITURE, not content: they render at screen size no matter the zoom
        (the legend law's scene-side sibling -- at fit zoom a scaled 7pt label is mush)."""
        item.setFlag(item.GraphicsItemFlag.ItemIgnoresTransformations)
        return item

    def _cell_tip(self, c):
        cx, cz = worldscan.block_center(c.bx, c.by)
        reals = [f"{p.name} {p.tris} tris" for p in
                 (c.parts.get(n) for n in worldscan.PART_ORDER) if p is not None and not p.blank]
        blanks = sum(1 for p in c.parts.values() if p.blank)
        bits = [f"Block[{c.bx}][{c.by}] — {c.kind}", f"centre x {cx:g}, z {cz:g}"]
        if c.donor_raw:
            bits.append(f"donor {c.donor_raw}")
        if reals:
            bits.append(" · ".join(reals) + (f" · {blanks} blanked" if blanks else ""))
        if c.mirror and c.mirror != "current":
            bits.append(f"⚠ Disc4 mirror {c.mirror} — rerun world-mirror")
        bits.append("Click for details. Double-click to name this landmass.")
        return "\n".join(bits)

    def _kind_fill(self, kind):
        col = QColor(self.pal[{"land": "success", "water": "accent", "stub": "muted"}[kind]])
        col.setAlpha(_KIND_ALPHA[kind])
        return col

    def stock_fill(self):
        """The stock-land ground tint: the quietest fill on the canvas -- geography is CONTEXT here,
        and the deployed cells must stay the loudest thing on their own map."""
        col = QColor(self.pal["muted"])
        col.setAlpha(58)
        return col

    def _draw(self):
        sc, pal = self._scene, self.pal
        sc.clear()
        self._cells = {}
        cell = self.cell_px()
        k = self._scale / 100
        w, h = worldscan.GRID_COLS * cell, worldscan.GRID_ROWS * cell
        sc.setSceneRect(-_MARGIN * k - 6, -_MARGIN * k - 6,
                        w + _MARGIN * k * 2 + 12, h + _MARGIN * k * 2 + 12)
        font_ix = self._font(8)
        muted = QBrush(QColor(pal["muted"]))
        ix_h = QFontMetrics(font_ix).height()
        for bx in range(0, worldscan.GRID_COLS, 2):        # every-2 index labels: a graticule caption,
            t = self._ignore_zoom(sc.addSimpleText(str(bx), font_ix))   # not 44 competing numbers
            t.setBrush(muted)
            t.setPos(bx * cell + cell / 2 - 4, -ix_h - 8)
        for by in range(0, worldscan.GRID_ROWS, 2):
            t = self._ignore_zoom(sc.addSimpleText(str(by), font_ix))
            t.setBrush(muted)
            t.setPos(-QFontMetrics(font_ix).horizontalAdvance(str(by)) - 12,
                     by * cell + cell / 2 - ix_h / 2)
        deployed = set(self._census.cells) if self._census is not None else set()
        fill = self.stock_fill()
        for (bx, by), cls in self._stock.items():  # the REAL world's landmasses, under everything:
            if cls != "L" or (bx, by) in deployed:  # a deployed block owns its pixel outright -- no
                continue                            # stock tint bleeding through a translucent fill
            it = sc.addRect(QRectF(bx * cell + 0.5, by * cell + 0.5, cell - 1, cell - 1),
                            QPen(Qt.PenStyle.NoPen), QBrush(fill))
            it.setData(0, "stock")
            it.setZValue(-0.05)                    # ground: below every override plate
        for c in (self._census.cells.values() if self._census is not None else ()):
            self._block(c, cell)
        if (self._selected is not None and self._census is not None
                and self._selected not in self._census.cells):
            bx, by = self._selected                # an EMPTY block's selection ring (deployed cells
            rim = QPainterPath()                   # draw their own inside _block)
            rim.addRoundedRect(QRectF(bx * cell + 1.5, by * cell + 1.5, cell - 3, cell - 3), 3.0, 3.0)
            pen = QPen(QColor(pal["accent"]), 3)
            pen.setCosmetic(True)
            sc.addPath(rim, pen).setData(0, "sel")
        if self._census is not None:
            self._plates(cell)
        if self._census is not None and not self._census.cells:
            t = self._ignore_zoom(sc.addSimpleText("No overrides in this folder.", self._font(9)))
            t.setBrush(muted)
            t.setPos(w / 2, h / 2)

    def _plates(self, cell):
        """Landmass NAMEPLATES: one screen-sized pill per NAMED component, anchored above its top
        edge. The anchor item ignores the zoom and the pill/text are its children in SCREEN px --
        so plates stay readable at any zoom AND stay centred (the axis-label trick, plus geometry)."""
        sc, pal = self._scene, self.pal
        font = self._font(8, bold=True)
        fm = QFontMetrics(font)
        for comp in self._census.components():
            name = self._census.name_for(min(comp))
            if not name:
                continue
            top = min(by for _bx, by in comp)
            xs = [bx for bx, by in comp if by == top]          # centre over the TOP row's span
            ax = (min(xs) + max(xs) + 1) / 2 * cell
            anchor = QGraphicsRectItem(0, 0, 0, 0)
            anchor.setPen(QPen(Qt.PenStyle.NoPen))
            anchor.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIgnoresTransformations)
            anchor.setPos(ax, top * cell)
            anchor.setZValue(0.2)
            anchor.setData(0, "plate")
            sc.addItem(anchor)
            text = fm.elidedText(name, Qt.TextElideMode.ElideRight, 170)
            tw = fm.horizontalAdvance(text)
            th = fm.height()
            plate = QColor(pal["surface"])
            plate.setAlpha(230)                               # the poster scrim's fenced ground
            pill = sc.addRect(-tw / 2 - 6, -th - 9, tw + 12, th + 5)   # scene-created THEN
            pill.setParentItem(anchor)             # parented: a constructor-parented child is
                                                   # Python-owned to shiboken and double-frees
                                                   # (THE GC-CHILD LAW, backdrop.py:_child)
            pill.setPen(QPen(Qt.PenStyle.NoPen))
            pill.setBrush(QBrush(plate))
            t = sc.addSimpleText(text)
            t.setParentItem(anchor)
            t.setFont(font)
            t.setBrush(QBrush(QColor(pal["text"])))
            t.setPos(-tw / 2, -th - 7)

    def _block(self, c, cell):
        sc, pal = self._scene, self.pal
        key = (c.bx, c.by)
        rect = QRectF(c.bx * cell + 1.5, c.by * cell + 1.5, cell - 3, cell - 3)
        rim = QPainterPath()
        rim.addRoundedRect(rect, 3.0, 3.0)
        body = sc.addPath(rim, QPen(Qt.PenStyle.NoPen), QBrush(self._kind_fill(c.kind)))
        body.setData(0, "cell")                    # tests census cells by TAG, not paint heuristics
        body.setData(1, key)                       # (the mapview ribbon-tag law)
        if key == self._selected:
            ring = QPen(QColor(pal["accent"]), 3)  # selection speaks the map's open-node language
        elif c.mirror in ("stale", "missing"):
            ring = QPen(QColor(pal["warn"]), 2)    # the one warning worth a ring: rerun world-mirror
        else:
            ring = QPen(QColor(pal["border"]), 1)
        ring.setCosmetic(True)                     # constant SCREEN width: at fit zoom a scaled 2px
        edge = sc.addPath(rim, ring)               # warn ring disappears -- the snap round's finding
        self._cells[key] = edge
        if c.has_real_object:                      # buildings marker (shape, not colour-only: legend + tip)
            d = max(3.0, cell * 0.13)
            dotc = QColor(pal["text"])
            dotc.setAlpha(200)
            sc.addEllipse(rect.right() - d - 2, rect.top() + 2, d, d,
                          QPen(Qt.PenStyle.NoPen), QBrush(dotc))
        if c.kind != "land" and c.donor is not None:      # a donor-diverted water/stub cell
            d = max(3.0, cell * 0.13)
            open_pen = QPen(QColor(pal["text"]), 1)
            open_pen.setCosmetic(True)
            sc.addEllipse(rect.left() + 2, rect.top() + 2, d, d,
                          open_pen, QBrush(Qt.BrushStyle.NoBrush))
        tip = self._cell_tip(c)
        for it in (body, edge):
            it.setToolTip(tip)

    # -- interaction --
    def _block_at(self, view_pos):
        """The grid block under the cursor -- ANY block, deployed or not; None off the 24x20 map."""
        if self._census is None:
            return None
        sp = self.mapToScene(view_pos)
        cell = self.cell_px()
        bx, by = math.floor(sp.x() / cell), math.floor(sp.y() / cell)
        return (bx, by) if worldscan.block_in_grid(bx, by) else None

    def mousePressEvent(self, event):              # noqa: N802 (Qt override)
        if event.button() == Qt.MouseButton.LeftButton:
            hit = self._block_at(event.position().toPoint())
            if hit is not None and hit != self._selected:
                self.select(hit)
        super().mousePressEvent(event)             # ScrollHandDrag panning still owns the drag

    def mouseMoveEvent(self, event):               # noqa: N802 (Qt override)
        if not event.buttons():
            over = self._block_at(event.position().toPoint())
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor if over
                                      else Qt.CursorShape.OpenHandCursor)
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):        # noqa: N802 (Qt override) -- name a landmass
        key = self._block_at(event.position().toPoint())
        if (key is not None and self.on_name and self._census is not None
                and key in self._census.cells):
            self.on_name(key)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

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
        step = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0),
                Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}.get(event.key())
        if step is not None and self._census is not None:
            self._step_selection(step)
            event.accept()
            return
        super().keyPressEvent(event)

    def _step_selection(self, step):
        """Arrow keys walk the GRID one block at a time (keyboard parity with the click -- every
        block answers now, so plain chart-cursor steps are the honest semantics), clamped at the
        map edge. No selection yet -> start on the first deployed block, else the map's middle."""
        if self._selected is None:
            cells = self._census.cells
            self.select(min(cells) if cells else (worldscan.GRID_COLS // 2, worldscan.GRID_ROWS // 2))
            return
        bx = min(worldscan.GRID_COLS - 1, max(0, self._selected[0] + step[0]))
        by = min(worldscan.GRID_ROWS - 1, max(0, self._selected[1] + step[1]))
        if (bx, by) != self._selected:
            self.select((bx, by))


class WorldDoc(QWidget):
    """The World tab: folder picker + Rescan over the :class:`AtlasCanvas`, with a details card for the
    selected block. All state is a :class:`~ff9mapkit.workspace.worldscan.WorldCensus`; all filesystem
    reads happen inside :meth:`refresh` (user-invoked, worker thread) -- never at construction, never on
    tab show."""

    _scan_done = Signal(object, object, object)    # (census | None, stock grid | None, error | None)
    _point_done = Signal(object, object, object)   # (the pick it answers, point_info | None, error | None)

    def __init__(self, pal, *, on_setup=None, scale=100, game_path_fn=None, on_teleport=None,
                 drafts_root=None, forest_runner=None, forest_seams=None, on_reload=None,
                 mountain_runner=None, mountain_seams=None, recipe_runner=None, recipe_seams=None,
                 sink_runner=None, sink_seams=None, coast_runner=None, coast_seams=None, island_runner=None,
                 island_seams=None, transplant_runner=None, transplant_seams=None, river_runner=None,
                 river_seams=None, hill_runner=None, hill_seams=None):
        super().__init__()
        self.pal = pal
        self.on_setup = on_setup
        self._game_path_fn = game_path_fn          # None -> config.find_game_path, resolved at CALL time
        self._scale = scale
        self._census = None
        self._stock_grid = {}                      # the real map's land/sea, once a scan derived it
        self._stock_known = False                  # False = geography unreadable: never claim "free"
        self._selected = None
        self._trees = []
        self._game = None                          # the install the last scan read (the 3D view reads it too)
        self._view3d = None                        # the 3D page: built on the user's first "3D view" click
        self._point = None                         # the 3D pick the strip shows: ((x, y, z), part) or None
        self._point_info = None                    # its facts, once read (world.pointinfo.point_info)
        self._on_teleport = on_teleport            # (x, z) -> None: the shell's dev-checkout harness job, or None
        self._forest = None                        # the forest tool (rung C1): built on the first Forest click
        self._drafts_root = drafts_root            # None -> world.draft.drafts_dir() (tests pin a tmp dir)
        self._forest_runner = forest_runner        # None -> the tool's QProcess runner (tests inject one)
        self._forest_seams = forest_seams or {}    # ForestTool's outline_fn / soup_fn / sync (tests, gui_snap)
        self._mountain = None                      # the mountain tool (rung C2): built on the first Mountain click
        self._mountain_runner = mountain_runner    # ...and its seams, as the forest's
        self._mountain_seams = mountain_seams or {}
        self._sink = None                          # the sink tool (rung C5): built on the first Sink click
        self._sink_runner = sink_runner
        self._sink_seams = sink_seams or {}
        self._coast = None                         # the coast tool (rung C5): built on the first Coast click
        self._coast_runner = coast_runner
        self._coast_seams = coast_seams or {}
        self._island = None                        # the island tool (rung C5): built on the first Island click
        self._island_runner = island_runner
        self._island_seams = island_seams or {}
        self._transplant = None                    # the transplant tool (rung C5): built on the first Carry click
        self._transplant_runner = transplant_runner
        self._transplant_seams = transplant_seams or {}
        self._river = None                         # the river tool (rung C5): built on the first Move-the-river click
        self._river_runner = river_runner
        self._river_seams = river_seams or {}
        self._hill = None                          # the hill tool (rung 6): built on the first Add-a-hill click
        self._hill_runner = hill_runner
        self._hill_seams = hill_seams or {}
        self._recipe = None                        # the recipe bar (rung C3): built with the 3D page
        self._recipe_runner = recipe_runner        # ...its world-fuse runner and its seams (ask, file dialogs)
        self._recipe_seams = recipe_seams or {}
        self._on_reload = on_reload                # (x, z) -> None: the shell's dev-checkout world reload, or None
        self._point_done.connect(self._finish_point)
        self._busy = False
        self._guide_state = ("scan", "")
        self._ask_name = self._ask_name_dialog     # the modal seam: tests/snaps inject, prod asks
        self._scan_done.connect(self._finish)
        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._guide_page = self._build_guide(*self._guide_state)
        self._stack.addWidget(self._guide_page)
        self._atlas_page = self._build_atlas()
        self._stack.addWidget(self._atlas_page)
        self._stack.setCurrentWidget(self._guide_page)

    # -- pages --
    def _build_guide(self, state, detail):
        """The pre-scan / problem page: one teaching empty-state per situation. Rebuilt per state (and
        per retheme -- the glyph pixmap is palette-tinted at build time)."""
        glyph = icons.pixmap("pin", self.pal["muted"], 46)
        if state == "nogame":
            # The title already carries the finding; the teach line carries only the way out (the
            # first cut prepended the ConfigError text and the snap read "not found" twice).
            teach = "Point the kit at your FF9 install in Setup & health, then scan again."
            acts = [("Open Setup && health…", self.on_setup) if self.on_setup else None,
                    ("Scan again", self.refresh)]           # && -- a lone & is eaten as a mnemonic
            return widgets.empty_state("", "FF9 install not found",
                                       teach=teach, actions=acts, icon_pixmap=glyph)
        if state == "notrees":
            return widgets.empty_state(
                "", "No worldmap overrides deployed yet",
                teach="The world verbs (world-island, world-transplant, world-mountain) write "
                      f"Block[x][y] overrides into a mod folder like FF9CustomMap-world under {detail}. "
                      "Deploy one, then rescan.",
                actions=[("Rescan", self.refresh)], icon_pixmap=glyph)
        if state == "error":
            return widgets.empty_state("", "The scan failed",
                                       teach=detail or "Unknown error.",
                                       actions=[("Rescan", self.refresh)], icon_pixmap=glyph)
        return widgets.empty_state(                # "scan" -- the front door
            "", "See your custom overworld at a glance",
            teach="Scanning reads the deployed Block[x][y] overrides from your game's mod folders "
                  "(islands, mountains, water carries, donors, the Disc4 mirror). It only reads — "
                  "nothing is written.",
            actions=[("Scan install", self.refresh)], icon_pixmap=glyph)

    def _show_guide(self, state, detail=""):
        self._guide_state = (state, detail)
        old = self._guide_page
        self._guide_page = self._build_guide(state, detail)
        self._stack.addWidget(self._guide_page)
        self._stack.setCurrentWidget(self._guide_page)
        self._stack.removeWidget(old)
        old.deleteLater()

    def _build_atlas(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(10, 8, 10, 10)
        v.setSpacing(8)
        head = QHBoxLayout()
        head.setSpacing(8)
        self.folder_box = QComboBox()
        self.folder_box.setAccessibleName("World mod folder")
        self.folder_box.setToolTip("Which mod folder's worldmap tree the atlas shows.")
        self.folder_box.activated.connect(self._on_folder_pick)
        head.addWidget(self.folder_box)
        self.rescan_btn = QPushButton("Rescan")
        self.rescan_btn.setToolTip("Re-read the deployed overrides from disk (read-only).")
        self.rescan_btn.clicked.connect(self._rescan)
        head.addWidget(self.rescan_btn)
        self.summary_lbl = widgets.role_label("", "caption")
        self.summary_lbl.setAccessibleName("Scan summary")
        # WRAPS, never clips or elides: the stale-mirror note at the summary's end is a warning that must
        # stay on the face (test_worlddoc), and the 3D toggle beside it cut it to "rerun wo" at 150%.
        self.summary_lbl.setWordWrap(True)
        head.addWidget(self.summary_lbl, 1)
        # The 3D view (editor rung A0) is a second PAGE over the same census, not a second tab: the
        # details strip below serves both. Quiet tier (the atlas page has no CTA), and NOT checkable: no
        # QPushButton:checked rule exists, so a checked quiet button looks unchecked (snap-caught). The
        # label names the view the click goes TO, so the words always carry the state.
        self._mode3d = False
        self.view3d_btn = QPushButton()
        self.view3d_btn.setProperty("role", "quiet")
        self.view3d_btn.clicked.connect(lambda: self._on_view3d(not self._mode3d))
        self._label_view_btn()
        # What the 3D page draws: the game's whole FolderNames stack (the default: what you will see in game), or
        # only this folder over stock (a scratch folder the game does not load yet). It lives on the 3D page's own
        # bar (handed over when the page is built): in this row it squeezed the wrapped summary into a clip at 150%.
        self.draw_box = QComboBox()
        self.draw_box.addItem("As the game loads it", "stack")
        self.draw_box.addItem("Only this folder", "folder")
        self.draw_box.setAccessibleName("3D view draws")
        self.draw_box.setToolTip("As the game loads it: every folder in Memoria.ini's FolderNames, highest priority "
                                 "first, each file from the first folder holding it. Only this folder: the picked "
                                 "folder over stock, for previewing a folder the game does not load.")
        self.draw_box.activated.connect(lambda _ix: self._load_view3d())
        self.draw_box.hide()
        # THE MAP EDITOR'S TOOLS (rungs C1, C2, C5), one menu on the 3D page's bar: five buttons there set the window's
        # floor (1003px at 100%, 1336 at 150%) and crowded the caption out. Each is an action of the menu, the card's
        # own open_*; their tooltips say which verb judges it.
        from PySide6.QtWidgets import QMenu
        self.tools_btn = QPushButton("Edit the map")
        self.tools_btn.setProperty("role", "quiet")
        self.tools_btn.setToolTip("Add a forest, a mountain, a hill or an island, shape or carry a coast, move the "
                                  "river or sink an island: each tool's "
                                  "card shows where it is lawful, its own world verb judges it, and Accept writes it to "
                                  "a draft the game does not load.")
        menu = QMenu(self.tools_btn)
        self.tool_actions = {}
        for key, text, tip in (
                ("forest", "Add forest", "Place a real stock canopy on a deployed island: click where it goes, drag, "
                 "turn and spread it; every world-forest gate judges it."),
                ("mountain", "Add mountain", "Place a real stock rock massif on a deployed island: drag, turn, spread "
                 "and heighten it; every world-mountain gate judges it."),
                ("hill", "Add a hill", "Raise a grass hill on a deployed island: click where it goes, drag it, set "
                 "its height and radius; the flank and peak laws show live, and world-hill judges it."),
                ("island", "Add an island", "Mint a new island on open ocean: click where it goes, drag it, set its "
                 "radius, lobes, height, ground and shape; world-island judges it."),
                ("coast", "Shape a coast", "Morph a real island's coast in place: click a cliff or a beach; only the "
                 "lawful windows and depths are offered, and world-transplant judges it."),
                ("transplant", "Carry a coast", "Carry a real coastal block, whole, onto an open-ocean cell: pick "
                 "the donor and the turn, click the cell; world-transplant judges it."),
                ("river", "Move the river", "Move the carried river, whole, to another open-ocean placement: click "
                 "where it goes; world-river --move-from judges it, the old river taken out only once it passes."),
                ("sink", "Sink an island", "Sink a real island into open water: click it; world-sink judges it.")):
            act = menu.addAction(text)
            act.setToolTip(tip)
            act.triggered.connect(lambda _c=False, k=key: getattr(self, f"open_{k}")())
            self.tool_actions[key] = act
        menu.setToolTipsVisible(True)
        self.tools_btn.setMenu(menu)
        self.tools_btn.hide()
        head.addWidget(self.view3d_btn)
        v.addLayout(head)
        self.canvas = AtlasCanvas(self.pal, on_select=self._on_select,
                                  on_name=self._name_landmass, scale=self._scale)
        self._views = QStackedLayout()
        self._views.setContentsMargins(0, 0, 0, 0)
        self._views.addWidget(self.canvas)
        views_host = QWidget()
        views_host.setLayout(self._views)
        v.addWidget(views_host, 1)
        self._forest_slot = QVBoxLayout()          # the carry cards' place: under the view, over the strip
        self._forest_slot.setContentsMargins(0, 0, 0, 0)
        v.addLayout(self._forest_slot)
        self._legend_host = QWidget()
        self._legend_lay = QHBoxLayout(self._legend_host)
        self._legend_lay.setContentsMargins(2, 0, 2, 0)
        self._legend_lay.setSpacing(10)
        self._fill_legend()
        v.addWidget(self._legend_host)
        # The details STRIP, not a tall kv card: the first snap round measured the six-row card
        # squeezing the canvas to ~290px and the whole atlas to 12px cells -- on this surface the
        # CHART is the document and the details are its caption.
        strip = widgets.card()
        sh = QHBoxLayout(strip)
        sh.setContentsMargins(14, 10, 14, 10)
        sh.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(2)
        trow = QHBoxLayout()
        trow.setSpacing(8)
        self.sel_title = widgets.role_label("No block selected", "cardtitle")
        self.sel_title.setAccessibleName("Selected block")
        trow.addWidget(self.sel_title)
        self.sel_chip = widgets.status_chip("", "info")
        self.sel_chip.hide()
        trow.addWidget(self.sel_chip)
        trow.addStretch(1)
        left.addLayout(trow)
        self.sel_facts = widgets.role_label("Click a block on the atlas — or arrow-key through them.",
                                            "caption")
        self.sel_facts.setWordWrap(True)
        self.sel_facts.setAccessibleName("Selected block facts")
        left.addWidget(self.sel_facts)
        self.sel_parts = widgets.role_label("", "caption")
        self.sel_parts.setWordWrap(True)
        self.sel_parts.setAccessibleName("Selected block parts")
        left.addWidget(self.sel_parts)
        sh.addLayout(left, 1)
        brow = QVBoxLayout()
        brow.setSpacing(6)
        self.copy_btn = QPushButton("Copy centre coords")
        self.copy_btn.setToolTip("Copy the block-centre world x z — paste into the debug menu's "
                                 "overworld teleport (~ → World).")
        self.copy_btn.clicked.connect(self._copy_coords)
        self.copy_btn.setEnabled(False)
        brow.addWidget(self.copy_btn)
        self.open_btn = QPushButton("Open block folder")
        self.open_btn.setProperty("role", "quiet")
        self.open_btn.setToolTip("Show this block's override files in Explorer.")
        self.open_btn.clicked.connect(self._open_folder)
        self.open_btn.setEnabled(False)
        brow.addWidget(self.open_btn)
        # The siting ENHANCEMENT: on a clean open-ocean block (stock says no geometry, this folder
        # says no overrides) the strip offers a paste-ready world-island command for exactly that
        # block. Quiet tier, and it REPLACES the folder button (an empty block never has a folder)
        # rather than stacking under it -- a strip that grows on selection shrinks the canvas out
        # from under its own fit (snap-caught: scrollbars + a clipped bottom row).
        self.site_btn = QPushButton("Copy world-island command")
        self.site_btn.setProperty("role", "quiet")
        self.site_btn.setToolTip("Copy a ready-to-run world-island command targeting this open-ocean "
                                 "block (paste into a terminal at the kit root).")
        self.site_btn.clicked.connect(self._copy_site_cmd)
        self.site_btn.hide()
        brow.addWidget(self.site_btn)
        # The 3D pick's second-slot button (the same one-slot swap): move the running game's party to the
        # picked point. Dev checkout only -- the shell passes on_teleport only when tools/world_teleport.py
        # (the harness) is there, and the button never shows without it.
        self.teleport_btn = QPushButton("Teleport game here")
        self.teleport_btn.setProperty("role", "quiet")
        self.teleport_btn.setToolTip("Move the party in the running game to this point (the debug menu's overworld "
                                     "teleport, sent through the test harness; the game must be on the world map).")
        self.teleport_btn.clicked.connect(self._teleport)
        self.teleport_btn.hide()
        brow.addWidget(self.teleport_btn)
        sh.addLayout(brow)
        v.addWidget(strip)
        self._strip = strip
        return page

    def _fill_legend(self):
        """The fill encoding as a WIDGET row, not scene content: the first snap round photographed the
        in-scene legend as mush at fit zoom -- a legend that teaches the canvas must not need the
        canvas's zoom to read (the map's screen-fixed-hint law, applied to the key)."""
        from PySide6.QtGui import QPixmap
        while self._legend_lay.count():
            it = self._legend_lay.takeAt(0)
            if it.widget() is not None:
                it.widget().deleteLater()

        def dot(fill, ring, ring_w=1):
            pm = QPixmap(11, 11)
            pm.fill(Qt.GlobalColor.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QPen(QColor(ring), ring_w))
            p.setBrush(QBrush(fill) if fill is not None else QBrush(Qt.BrushStyle.NoBrush))
            p.drawRoundedRect(QRectF(1, 1, 9, 9), 2.5, 2.5)
            p.end()
            lab = QLabel()
            lab.setPixmap(pm)
            lab.setAccessibleName("")                       # decorative; the caption beside it speaks
            return lab

        def cap(text):
            lab = widgets.role_label(text, "caption")
            return lab

        self._legend_lay.addWidget(dot(self.canvas.stock_fill(), self.pal["border"]))
        self._legend_lay.addWidget(cap("stock land"))
        for kind, label in (("land", "your land"), ("water", "water carry"), ("stub", "stub only")):
            self._legend_lay.addWidget(dot(self.canvas._kind_fill(kind), self.pal["border"]))
            self._legend_lay.addWidget(cap(label))
        self._legend_lay.addWidget(dot(None, self.pal["warn"], 2))
        self._legend_lay.addWidget(cap("mirror stale"))
        self._legend_lay.addWidget(cap("▪ buildings · ◦ donor cell"))
        self._legend_lay.addStretch(1)

    # -- shell hooks --
    def crumb_label(self):
        if self._census is not None:
            return f"World — {self._census.root.name}"
        return "World"

    def set_scale(self, pct):
        self._scale = pct
        if hasattr(self, "canvas"):
            self.canvas.set_scale(pct)
        if self._view3d is not None:
            self._view3d.set_scale(pct)

    def retheme(self, pal):
        self.pal = pal
        if hasattr(self, "canvas"):
            self.canvas.retheme(pal)
            self._fill_legend()                    # the swatch pixmaps are palette-baked at build time
        if self._view3d is not None:
            self._view3d.retheme(pal)
        for tool in self._carry_tools():
            tool.retheme(pal)
        if self._recipe is not None:
            self._recipe.retheme(pal)
        if self._stack.currentWidget() is self._guide_page:
            self._show_guide(*self._guide_state)   # rebuild: the glyph pixmap is palette-tinted

    # -- the scan --
    def _rescan(self):
        """The Rescan button: re-read the folder AND every cell the 3D view drew (its memo trusts files' times)."""
        if self._view3d is not None:
            self._view3d.forget_cells()
        self.refresh()

    def refresh(self, *, sync=False, folder=None):
        """Scan (or rescan) the deployed worldmap tree. Reads the game path + folder list on the GUI
        thread (cheap stats), then runs the real census on a worker; ``sync=True`` is the deterministic
        test/snap lane. Never called by the shell -- every invocation is a user gesture."""
        if self._busy or self._held() or self._cards_write():
            return                                 # (a draft the recipe bar holds, a card writing: the folder waits)
        fn = self._game_path_fn or config.find_game_path
        try:
            game = fn()
        except config.ConfigError as e:
            self._show_guide("nogame", str(e))
            return
        self._game = game
        self._trees = worldscan.find_world_trees(game)
        if not self._trees:
            self._show_guide("notrees", str(game))
            return
        current = folder
        if current is None and 0 <= self.folder_box.currentIndex() < len(self._trees):
            picked = self.folder_box.currentData()
            current = picked if picked in self._trees else None
        target = current or self._trees[0]
        self.folder_box.blockSignals(True)
        self.folder_box.clear()
        for t in self._trees:
            self.folder_box.addItem(t.name, t)
        self.folder_box.setCurrentIndex(self._trees.index(target))
        self.folder_box.blockSignals(False)
        self._busy = True
        self.rescan_btn.setEnabled(False)
        self.rescan_btn.setText("Scanning…")
        if sync:
            try:
                self._finish(worldscan.scan_tree(target), worldscan.stock_context(game), None)
            except Exception as e:                 # noqa: BLE001 -- surfaced, never swallowed
                self._finish(None, None, str(e))
            return
        threading.Thread(target=self._worker, args=(target, game), daemon=True).start()

    def _worker(self, target, game):
        try:
            census = worldscan.scan_tree(target)
            # The stock geography rides the same worker: first-ever call reads a p0data bundle
            # (seconds), every later call is one cached JSON. None = underivable -> no layer.
            stock, err = worldscan.stock_context(game), None
        except Exception as e:                     # noqa: BLE001 -- surfaced on the GUI thread
            census, stock, err = None, None, str(e)
        try:
            self._scan_done.emit(census, stock, err)   # RuntimeError-guarded: the doc may be dead
        except RuntimeError:
            pass

    def _finish(self, census, stock, err):
        self._busy = False
        self.rescan_btn.setEnabled(not self._held() and not self._cards_write())
        self.rescan_btn.setText("Rescan")
        if err is not None:
            self._show_guide("error", err)
            return
        for tool in self._carry_tools():           # a card writing as the scan lands ends in the folder it wrote
            tool.finish_writes()                   # (its Accept committed to the new folder's draft: fourth round)
        self._census = census
        self._stock_grid = stock or {}
        self._stock_known = stock is not None
        self._stack.setCurrentWidget(self._atlas_page)
        self.canvas.set_census(census, stock)
        n = len(census.cells)
        if n == 0:
            self.summary_lbl.setText("No Block[x][y] overrides in this folder.")
        else:
            stale = len(census.stale_cells)
            if not census.has_disc4:
                mirror = "no Disc4 tree — run world-mirror"
            elif stale:
                mirror = f"Disc4 mirror: {stale} stale — rerun world-mirror"
            else:
                mirror = "Disc4 mirror current"
            bits = [f"{n} blocks", f"{census.landmasses} landmass{'es' if census.landmasses != 1 else ''}",
                    _fmt_bytes(census.total_bytes), mirror]
            if census.strays:
                bits.append(f"{len(census.strays)} stray files")
            self.summary_lbl.setText(" · ".join(bits))
        self._on_select(self._selected)            # re-derive the strip: the block may have changed
        #                                            class (deployed <-> empty) across the rescan
        for tool in self._carry_tools():
            if not tool.isHidden():
                tool.close_tool()                  # its folder may have changed under it
        for tool in self._carry_tools():           # ...and every card, open or not, forgets its per-folder reads
            tool.island_changed()                  # (block holders, where the river is: review of the C12 fixes)
        if self._recipe is not None:
            self._recipe.refresh()                 # ...and the draft the bar reads with it
        self._sync_draw_box()
        if self._mode3d:                           # a rescan (or a new folder) re-reads the 3D page too
            self._load_view3d()
            if self._recipe is not None:
                self._recipe.settle()              # the folder shown may owe its game a promote (rung C19)

    # -- the 3D page --
    def _render_site(self):
        """``(RenderSite, caption)`` for the 3D page: the game's FolderNames stack, or this folder over stock. Sets
        ``_caption_plain`` when the caption only restates the stack the draw box names (no warning in it): only then
        may an open carry card fold it away."""
        self._caption_plain = False
        from ..world import mesh as M
        from ..world import render as R
        cells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
        here = self._census.root.name
        one = R.RenderSite(cells=cells, disc=1, game=self._game, mod_root=self._census.root)
        mode = self.draw_box.currentData()
        draft = self._draft() if mode == "draft" else None
        if draft is not None:
            stack = R.game_stack(self._game)
            if stack is None:
                return (R.RenderSite(cells=cells, disc=1, game=self._game, mod_root=draft),
                        f"Drawn: only the draft of {here} over stock (Memoria.ini could not be read). The game "
                        "does not load the draft.")
            names = [p.name for p in stack]
            roots = [draft if p.name == here else p for p in stack] if here in names else [draft] + list(stack)
            order = " › ".join((f"the draft of {here}" if p == draft else p.name) for p in roots)
            self._caption_plain = True
            return (R.RenderSite(cells=cells, disc=1, game=self._game, stack=tuple(roots)),
                    f"Drawn with your draft in place of {here}: {order} › stock. The game does not load the draft.")
        if mode == "folder":
            return one, (f"Drawn: only {here} over stock. The game reads every folder in Memoria.ini's "
                         "FolderNames, so a block another folder overrides looks different in game; a picked "
                         "point says where.")
        stack = R.game_stack(self._game)
        if stack is None:
            return one, (f"Memoria.ini could not be read, so this draws only {here} over stock, not the "
                         "game's folder order.")
        names = [p.name for p in stack]
        cap = "Drawn as the game loads it, first folder first: " + " › ".join(names + ["stock"])
        if here not in names:
            cap += (f". ⚠ {here} is not in FolderNames, so the game does not load it and neither does this "
                    "view; choose Only this folder to see it.")
        else:
            self._caption_plain = True
        return R.RenderSite(cells=cells, disc=1, game=self._game, stack=stack), cap

    def _draft(self):
        """The shown folder's draft (``world.draft``), or None."""
        if self._census is None:
            return None
        from ..world import draft as D
        p = D.draft_path(self._census.root, root=self._drafts_root)
        return p if D.is_draft(p) else None

    def _sync_draw_box(self):
        """Offer "With the draft" exactly while the shown folder has one."""
        have = self._draft() is not None
        ix = self.draw_box.findData("draft")
        if have and ix < 0:
            self.draw_box.insertItem(1, "With the draft", "draft")
        elif not have and ix >= 0:
            if self.draw_box.currentIndex() == ix:
                self.draw_box.setCurrentIndex(0)
            self.draw_box.removeItem(ix)

    def _carry_tools(self):
        return [t for t in (self._forest, self._mountain, self._hill, self._sink, self._coast, self._island,
                            self._transplant, self._river) if t is not None]

    def _open_carry(self, which, *, sync=False, edit=False):
        """The 3D view first (the tools work on it), then that tool's card under it; one card at a time, and the
        ghost's drag goes to the open one. While the recipe bar holds the draft (an edit open, its steps going back,
        an in-game step's chain) no card opens but the edit's own (``edit``): another closed the editing card, whose
        cancel started the promote back under the new card, or wrote the draft under the open edit -- a Discard
        deleted the draft and what the game was owed (review of the C19 fixes, third round)."""
        if self._census is None or self._chain_writes() or (self._held() and not edit):
            return None
        if not self._mode3d:
            self._on_view3d(True, sync=sync)
        tool = getattr(self, f"_{which}")
        if tool is None:
            if which == "forest":
                from .worldforest import ForestTool as Tool
            elif which == "sink":
                from .worldsink import SinkTool as Tool
            elif which == "coast":
                from .worldcoast import CoastTool as Tool
            elif which == "island":
                from .worldisland import IslandTool as Tool
            elif which == "transplant":
                from .worldtransplant import TransplantTool as Tool
            elif which == "river":
                from .worldriver import RiverTool as Tool
            elif which == "hill":
                from .worldhill import HillTool as Tool
            else:
                from .worldmountain import MountainTool as Tool
            tool = Tool(self.pal, self._view3d, game_fn=lambda: self._game, source_fn=lambda: self._census.root,
                        on_changed=self._draft_changed, runner=getattr(self, f"_{which}_runner"),
                        drafts_root=self._drafts_root, on_reload=self._on_reload, **getattr(self, f"_{which}_seams"))
            setattr(self, f"_{which}", tool)
            self._forest_slot.addWidget(tool)
            tool.opened.connect(lambda _on: self._sync_card_room())
            tool.writing_changed.connect(lambda _on: self._sync_locks())
            self._view3d.ghost_moved.connect(lambda x, z, t=tool: t.drag_to(x, z) if not t.isHidden() else None)
            self._view3d.ghost_dropped.connect(lambda x, z, t=tool: t.drop_at(x, z) if not t.isHidden() else None)
        for other in self._carry_tools():
            if other is not tool and not other.isHidden():
                other.close_tool()
        tool.open_tool()
        return tool

    def _sync_card_room(self):
        """While a carry card is open the page makes room for it: card and strip together floored the page at 931px
        tall at 150% (984 with the mountain's second row), so in a 1280x850 window the card's verdict and draft line
        were clipped. The block strip goes (a click places the shape, and the card speaks for it), the 3D view's
        floor drops to ``CARD_VIEW_FLOOR`` so the view gives way before the card's words do, and a PLAIN caption
        folds (the draw box names the stack and the card's draft line names the draft; a caption carrying a warning
        stays). The room is for the recipe bar above the cards too (rung C3). Close restores all three."""
        open_ = any(not t.isHidden() for t in self._carry_tools())
        self._strip.setVisible(not open_)
        if self._view3d is not None:
            self._view3d.set_view_floor(CARD_VIEW_FLOOR if open_ else None)
            self._view3d.fold_caption(open_ and getattr(self, "_caption_plain", False))

    def open_forest(self, *, sync=False):
        """The Forest button."""
        return self._open_carry("forest", sync=sync)

    def open_mountain(self, *, sync=False):
        """The Mountain button."""
        return self._open_carry("mountain", sync=sync)

    def open_sink(self, *, sync=False):
        """The Sink button."""
        return self._open_carry("sink", sync=sync)

    def open_coast(self, *, sync=False):
        """The Coast button."""
        return self._open_carry("coast", sync=sync)

    def open_island(self, *, sync=False):
        """The Island button."""
        return self._open_carry("island", sync=sync)

    def open_transplant(self, *, sync=False):
        """The Carry-a-coast menu entry."""
        return self._open_carry("transplant", sync=sync)

    def open_hill(self, *, sync=False):
        """The Add-a-hill menu entry."""
        return self._open_carry("hill", sync=sync)

    def open_river(self, *, sync=False):
        """The Move-the-river menu entry."""
        return self._open_carry("river", sync=sync)

    # -- a placed step (rung C9) --
    EDIT_CARDS = {"forest": "forest", "mountain": "mountain", "hill": "hill", "island": "island",
                  "transplant": "transplant", "sink": "sink", "morph": "coast",
                  "river": "river"}                    # a table -> the card that opens on its rows

    def _mark_step(self, step):
        """Mark the picked step's place on the view (a pin at its anchor), or clear the mark; a card's own drawing
        is never overwritten."""
        if self._view3d is None or any(not t.isHidden() for t in self._carry_tools()):
            return
        from ..world import recipe as RC
        pt = None if step is None else RC.anchor(step.get("row") or {})
        if pt is None:
            self._view3d.set_overlays([])
            return
        from .worldforest import _rgb
        from .worldview3d import ground_y, pin_tris
        packed = self._view3d.view.packed if self._view3d.view is not None else None
        y = ground_y(packed, *pt) if packed is not None else None
        self._view3d.set_overlays([(pin_tris((pt[0], 0.0 if y is None else y, pt[1]), STEP_MARK_H, w_frac=0.14),
                                    _rgb(self.pal["accent"]), 1.0, False)])

    def _edit_step(self, row, label):
        """The recipe bar lifted a placed step out of the draft: open its card on the step's row."""
        which = self.EDIT_CARDS.get(row.get("table"))
        tool = self._open_carry(which, edit=True) if which else None
        if tool is None:
            self._recipe.cancel_edit(f"Not opened: a {row.get('table')} step has no card that opens on it.", "error")
            return
        try:
            tool.edit_row(row, label=label, on_accepted=self._recipe.edit_accepted,
                          on_cancel=lambda note=None: self._recipe.cancel_edit(note, "error" if note else ""))
        except ValueError as e:
            tool.close_tool()
            self._recipe.cancel_edit(f"Not opened in its card: {e}. Delete still works.", "error")

    def _held(self) -> bool:
        return self._recipe is not None and self._recipe.holding()

    def _cards_write(self) -> bool:
        return any(t.writing() for t in self._carry_tools())

    def _sync_locks(self):
        """What may change under the draft and the cards now: :meth:`_on_bar_hold`'s locks, and while a card writes
        (its Accept, Promote or Revert promote) every control that would close it waits -- the menu (one card at a
        time), the view toggle, the folder box and Rescan (review of the C19 fixes, third round)."""
        self._on_bar_hold(self._held())

    def _on_bar_hold(self, held):
        """The recipe bar holds the draft (an edit open, a recipe going in, an in-game step's chain): the folder box and
        Rescan wait for it, as Undo and Open do. A switch closed the edit's card and its cancel went to the new
        folder's draft, leaving the first folder's game reverted. The Edit the map menu waits too: no card opens
        but the edit's own (:meth:`_open_carry`). While the chain writes the live folder and the draft's records (its
        revert, its promote back), no card is open either: a card's Promote, Revert promote, Discard or Accept would
        write the same folder or draft at the same moment (review of C19)."""
        writes = self._cards_write()
        why = ("Waits for the recipe bar (in the 3D view), which holds this folder's draft (an edit open, or a recipe "
               "going in)."
               if held else "Waits for the card, which is writing (its Accept, Promote or Revert promote)."
               if writes else "")
        self.folder_box.setEnabled(not held and not writes)
        self.folder_box.setToolTip(why or "Which mod folder's worldmap tree the atlas shows.")
        self.rescan_btn.setEnabled(not held and not writes and not self._busy)
        self.rescan_btn.setToolTip(why or "Re-read the deployed overrides from disk (read-only).")
        self.view3d_btn.setEnabled(not writes)       # (the chart closes the cards)
        self.tools_btn.setEnabled(not held and not writes)   # no card opens but the edit's own (_open_carry too)
        if held:                                   # ...and a card open when the bar began holding is put away: its
            for tool in self._carry_tools():       # Accept or Discard wrote the draft under a put-back or a recipe
                if not tool.isHidden() and not tool.editing() and not tool.writing():    # (fourth round; a card
                    tool.close_tool()              # that writes was refused the bar's start)

    def _chain_writes(self) -> bool:
        return self._recipe is not None and self._recipe.writing_live()

    def _draft_changed(self, draft):
        """An Accept wrote the draft (or a discard removed it, an undo or redo moved it): draw it, or go back to the
        game's stack; the recipe bar and every tool read the draft again."""
        if self._recipe is not None:
            self._recipe.refresh()
        for tool in self._carry_tools():
            tool.island_changed()
        self._sync_draw_box()
        ix = self.draw_box.findData("draft" if draft is not None else "stack")
        self.draw_box.setCurrentIndex(max(0, ix))
        self._load_view3d()
        if self._point is not None:                # its facts were read from the site drawn before: read again
            self._on_pick(self._point, place=False)

    def _on_view3d(self, on, *, sync=False):
        """The user's toggle. First use builds the panel (importing the GL module only now: the Workspace
        never pays for OpenGL at start, and the offscreen smoke never constructs a GL widget) and loads the
        whole map on a worker; ``sync=True`` is the deterministic lane for tests and gui_snap."""
        self._mode3d = bool(on)
        self._label_view_btn()
        self.draw_box.setVisible(bool(on))
        if on and self._recipe is None and self._census is not None:
            from .worldrecipe import RecipeBar
            self._recipe = RecipeBar(self.pal, game_fn=lambda: self._game, source_fn=lambda: self._census.root,
                                     on_changed=self._draft_changed, runner=self._recipe_runner,
                                     drafts_root=self._drafts_root, on_select=self._mark_step,
                                     on_edit=self._edit_step, on_hold=self._on_bar_hold,
                                     cards_writing=lambda: any(t.writing() for t in self._carry_tools()),
                                     **self._recipe_seams)
            self._forest_slot.insertWidget(0, self._recipe)
        if self._recipe is not None:
            self._recipe.setVisible(bool(on))
            if on:
                self._recipe.refresh()
        self.tools_btn.setVisible(bool(on))
        if not on:
            for tool in self._carry_tools():
                tool.close_tool()
        if not on:
            self._views.setCurrentWidget(self.canvas)
            self._legend_host.show()
            return
        if self._view3d is None:
            from .worldview3d import WorldView3DPanel
            self._view3d = WorldView3DPanel(self.pal, scale=self._scale)
            self._view3d.picked.connect(self._on_pick)
            self._view3d.add_control(self.tools_btn)     # each control goes in front: the draws, then the tools
            self._view3d.add_control(self.draw_box)
            self._views.addWidget(self._view3d)
            self._load_view3d(sync=sync)
        self._focus_view3d()
        self._views.setCurrentWidget(self._view3d)
        self._legend_host.hide()                   # the legend teaches the chart's fills, not the terrain
        if self._recipe is not None:
            self._recipe.settle()                  # a promote the game is owed from a Workspace that died mid-edit

    def shutdown(self):
        """The Workspace is closing (the shell's closeEvent). Every job that writes the live folder or a draft runs to
        its end, never killed half way: the recipe bar's (one job's end may start the next: the chain's next revert,
        the promote back) and a card's Accept, Promote or Revert promote (whose end may hand the bar its put-back). A
        card's Check, a dry run, stops. Then an edit of a step that is in the game is cancelled and its steps promoted
        back, so the game is left as it was (rung C19; review of its fixes: shutdown once returned with the chain's
        next job running, and cancelled an edit under its card's running Accept)."""
        for _ in range(256):
            runners = [t.closing_runner() for t in self._carry_tools()]
            if self._recipe is not None:
                runners.append(self._recipe.closing_runner())
            busy = [r for r in runners if r is not None]
            if busy:
                if not busy[0].wait():
                    return                         # it never ended: leave it (what the game is owed is on disk)
                continue
            if self._recipe is None or not self._recipe.close_in_game_edit():
                return

    def set_view_mode(self, mode, *, sync=False):
        """``"chart"`` or ``"3d"`` -- the toggle, for tests and gui_snap."""
        want = mode == "3d"
        if self._mode3d != want:
            self._on_view3d(want, sync=sync)

    def _label_view_btn(self):
        if self._mode3d:
            self.view3d_btn.setText("Chart view")
            self.view3d_btn.setToolTip("Back to the block chart.")
        else:
            self.view3d_btn.setText("3D view")
            self.view3d_btn.setToolTip("Show the map in 3D the way the engine binds it: stock land under this "
                                       "folder's overrides (read-only; loads on first use, about five seconds). "
                                       "Drag to orbit, right-drag to pan, wheel to zoom, Home to re-frame.")

    def _load_view3d(self, *, sync=False):
        if self._view3d is None or self._census is None:
            return
        site, caption = self._render_site()
        self._view3d.set_caption(caption)
        self._sync_card_room()                     # a plain caption folds while a card is open, a warning never
        self._view3d.load(site, sync=sync)
        self._focus_view3d()

    def _focus_view3d(self):
        if self._view3d is not None and self._selected is not None:
            self._view3d.focus(*worldscan.block_center(*self._selected))

    # -- the 3D pick (rung A1) --
    def _on_pick(self, hit, *, sync=False, place=True):
        """A click on the 3D view: select its block on the chart (so the chart agrees on return), then show the
        point's facts -- read on a worker (the first read of a stock block opens its bundle, about a second);
        ``sync=True`` is the deterministic lane."""
        if hit is None:
            self._point = self._point_info = None
            self.sel_title.setText("Sky")
            self.sel_facts.setText("Nothing under the cursor: click land or sea.")
            self.sel_parts.setText("")
            self._set_chip("", "info")
            return
        (x, y, z), part = hit
        if not 0.0 <= x < 1536.0:                  # a pick on the view's seam copy: the point it copies (rung C10)
            x = x % 1536.0
            hit = ((x, y, z), part)
        for tool in self._carry_tools() if place else ():
            if not tool.isHidden():
                tool.place(x, z, y)                # a tool is open: a click puts its shape there
        if place and self._recipe is not None and all(t.isHidden() for t in self._carry_tools()):
            self._recipe.pick(x, z)                # no tool open: a click picks the step placed there (rung C9)
        from ..world import frames
        key = frames.world_to_block(*frames.wrap_world_xz(x, z))
        self.canvas.select(key)                    # -> _on_select: the block strip, and the point cleared
        self._point = hit
        self.copy_btn.setText("Copy position")
        self.copy_btn.setEnabled(True)
        self.sel_title.setText(f"Point x {x:.2f}, z {z:.2f}")
        self.sel_facts.setText("Reading the ground here…")
        self.sel_parts.setText("")
        self._set_chip("", "info")
        self._swap_site(False, point=True)
        site = self._view3d.site if self._view3d is not None else None
        if site is None:
            return
        if sync:
            self._work_point(hit, site)
        else:
            threading.Thread(target=self._work_point, args=(hit, site), daemon=True).start()

    def _work_point(self, hit, site):
        from ..world import pointinfo
        try:
            out = (hit, pointinfo.point_info(site, hit[0][0], hit[0][2]), None)
        except Exception as e:                     # noqa: BLE001 -- surfaced on the GUI thread
            out = (hit, None, f"{type(e).__name__}: {e}")
        try:
            self._point_done.emit(*out)
        except RuntimeError:
            pass

    def _finish_point(self, hit, info, err):
        if hit is not self._point:                 # a later click (or a selection) superseded this read
            return
        from ..world import pointinfo
        if err is not None:
            self.sel_facts.setText(f"The ground query failed: {err}")
            return
        self._point_info = info
        lines = pointinfo.describe(info)
        self.sel_facts.setText(" · ".join(lines[:2]))
        self.sel_parts.setText(" · ".join(lines[2:]))
        g = info["ground"]
        if not g["modelled"]:
            self._set_chip("not modelled", "warn")
        elif g["part"] == "MISS":
            self._set_chip("no ground", "warn")
        elif g["walkable"]:
            self._set_chip("walkable", "good")
        else:
            self._set_chip("not walkable", "info")

    def _teleport(self):
        if self._point is None or self._on_teleport is None:
            return
        (x, _y, z), _part = self._point
        self._on_teleport(x, z)

    # -- selection / details --
    def _set_chip(self, text, kind):
        """Restyle the mirror chip: setText alone leaves the old kind's tint (setProperty needs the
        repolish -- widgets.set_state's own law) and the accessible name must follow the words."""
        if not text:
            self.sel_chip.hide()
            return
        self.sel_chip.setText(text)
        self.sel_chip.setProperty("kind", kind)
        widgets.repolish(self.sel_chip)
        self.sel_chip.setAccessibleName(f"{kind}: {text}")
        self.sel_chip.show()

    def _on_select(self, key):
        self._selected = key
        self._point = self._point_info = None      # a chart selection ends the 3D pick
        self.copy_btn.setText("Copy centre coords")
        if key is None or self._census is None:
            self.sel_title.setText("No block selected")
            self.sel_facts.setText("Click a block on the atlas — or arrow-key through them.")
            self.sel_parts.setText("")
            self._set_chip("", "info")
            self.copy_btn.setEnabled(False)
            self._swap_site(False)
            self.open_btn.setEnabled(False)
            return
        c = self._census.cells.get(key)
        if c is None:
            self._select_empty(key)
            return
        self._swap_site(False)                     # a deployed block's strip is the census, not siting
        cx, cz = worldscan.block_center(c.bx, c.by)
        nm = self._census.name_for(key)
        self.sel_title.setText(f"Block[{c.bx}][{c.by}] — {c.kind}" + (f" · “{nm}”" if nm else ""))
        facts = [f"centre x {cx:g}, z {cz:g}"]
        if c.donor_raw:
            facts.append(f"donor {c.donor_raw}")
        if c.backups:
            facts.append(f"{c.backups} .bak file{'s' if c.backups != 1 else ''}")
        self.sel_facts.setText(" · ".join(facts))
        reals = [f"{p.name} {p.tris} tris" for p in
                 (c.parts.get(nm) for nm in worldscan.PART_ORDER) if p is not None and not p.blank]
        blanks = sum(1 for p in c.parts.values() if p.blank)
        stub = c.parts.get("Terrain")
        if stub is not None and stub.blank:
            reals.insert(0, "Terrain (arming stub)")
        self.sel_parts.setText((" · ".join(reals) if reals else "no readable parts") +
                               (f" · {blanks} blanked" if blanks else ""))
        if not c.mirror:
            self._set_chip("no Disc4 tree — run world-mirror", "warn")
        elif c.mirror == "current":
            self._set_chip("Disc4 current" + (f" (+{c.pins} pins)" if c.pins else ""), "good")
        else:
            self._set_chip(f"Disc4 {c.mirror} — rerun world-mirror", "warn")
        self.copy_btn.setEnabled(True)
        self.open_btn.setEnabled(c.dirpath is not None)

    def _swap_site(self, siting, *, point=False):
        """ONE of the quiet buttons occupies the strip's second slot -- swapping keeps the strip's
        height (and therefore the canvas's fit) constant across every selection."""
        tele = point and self._on_teleport is not None
        self.site_btn.setVisible(siting and not point)
        self.teleport_btn.setVisible(tele)
        self.open_btn.setVisible(not siting and not tele)

    def _select_empty(self, key):
        """The strip for an UNDEPLOYED block: its stock geography, its centre, and -- only when the
        verdict is certain clean ocean -- the free-site call + the paste-ready world-island command."""
        bx, by = key
        cx, cz = worldscan.block_center(bx, by)
        self.sel_facts.setText(f"centre x {cx:g}, z {cz:g} · nothing deployed here")
        self.copy_btn.setEnabled(True)
        self.open_btn.setEnabled(False)
        cls = self._stock_grid.get(key)
        if not self._stock_known:
            self.sel_title.setText(f"Block[{bx}][{by}] — stock world")
            self.sel_parts.setText("Stock geography unknown (the install's assets couldn't be read), "
                                   "so this block can't be certified as a free site.")
            self._set_chip("", "info")
            self._swap_site(False)
        elif cls == "L":
            self.sel_title.setText(f"Block[{bx}][{by}] — stock land")
            self.sel_parts.setText("The real map owns this block. The atlas only charts it — "
                                   "reshaping stock land goes through the world verbs' own gates.")
            self._set_chip("stock land", "info")
            self._swap_site(False)
        elif cls == "~":
            self.sel_title.setText(f"Block[{bx}][{by}] — stock coastal water")
            self.sel_parts.setText("The real map ships sea meshes here (a coastal shelf block) — "
                                   "not a clean island site.")
            self._set_chip("stock water", "info")
            self._swap_site(False)
        else:
            self.sel_title.setText(f"Block[{bx}][{by}] — open ocean")
            self.sel_parts.setText("No stock geometry and no overrides in this folder: "
                                   "world-island can build here.")
            self._set_chip("free site", "good")
            self._swap_site(True)
            self.site_btn.setEnabled(True)

    # -- nameplates --
    def _ask_name_dialog(self, current):
        """An INSTANCE QInputDialog, never the static getText: the statics exec in C++ where no
        harness/test patch can see them (the round-8 QMessageBox law). Returns (text, accepted)."""
        from PySide6.QtWidgets import QDialog, QInputDialog
        dlg = QInputDialog(self)
        dlg.setWindowTitle("Name this landmass")
        dlg.setLabelText("Shown as a nameplate over the landmass on the atlas.\n"
                         "Leave empty to remove the name.")
        dlg.setTextValue(current)
        ok = dlg.exec() == QDialog.DialogCode.Accepted
        return dlg.textValue(), ok

    def _name_landmass(self, key):
        """Double-click on a deployed block: name (or rename / un-name) its whole landmass. Writes
        atlas-names.json IN the scanned mod folder -- the name describes that folder's content and
        travels with it."""
        if self._census is None or key not in self._census.cells:
            return
        current = self._census.name_for(key) or ""
        text, ok = self._ask_name(current)
        if not ok or text.strip() == current:
            return
        worldscan.set_landmass_name(self._census, key, text)
        self.canvas.select(key)                    # redraw (plates) + refresh the strip's title

    def _copy_site_cmd(self):
        if self._selected is None or self._census is None:
            return
        bx, by = self._selected
        cmd = f"py -m ff9mapkit world-island --mod-folder {self._census.root.name} --cell {bx},{by}"
        QApplication.clipboard().setText(cmd)
        self.site_btn.setText("Copied ✓")
        QTimer.singleShot(1400, lambda: self.site_btn.setText("Copy world-island command"))

    def _copy_coords(self):
        if self._point is not None:                # the 3D pick: the canonical pair, as the debug menu copies it
            (x, _y, z), _part = self._point
            QApplication.clipboard().setText(f"{x:.2f} {z:.2f}")
            back = "Copy position"
        elif self._selected is not None:
            cx, cz = worldscan.block_center(*self._selected)
            QApplication.clipboard().setText(f"{cx:g} {cz:g}")
            back = "Copy centre coords"
        else:
            return
        self.copy_btn.setText("Copied ✓")          # text feedback, not motion (reduced-motion-safe)
        QTimer.singleShot(1400, lambda: self.copy_btn.setText(back))

    def _open_folder(self):
        c = self._census.cells.get(self._selected) if self._census is not None else None
        if c is not None and c.dirpath is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(c.dirpath)))

    def _on_folder_pick(self, _ix):
        picked = self.folder_box.currentData()
        if picked is not None:
            self.refresh(folder=picked)
