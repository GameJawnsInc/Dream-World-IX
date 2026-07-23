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
    QApplication, QComboBox, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel,
    QPushButton, QStackedLayout, QVBoxLayout, QWidget,
)

from .. import config
from . import icons, widgets, worldscan

_CELL = 30                                        # one block's edge at 100% text scale (scene px)
_MARGIN = 26                                      # room for the row/col index labels
_ZOOM_MIN, _ZOOM_MAX = 0.3, 4.0                   # a 24x20 chart never needs the map's 0.15 floor
_GRID_ALPHA = 90                                  # the graticule: present, sub-informational (70 was
#                                                   invisible on the light palette -- snap-measured)
_KIND_ALPHA = {"land": 165, "water": 120, "stub": 90}


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

    def __init__(self, palette, *, on_select=None, scale=100):
        super().__init__()
        self.pal = palette                         # RAW palette, direct indexing -- the mapview rule
        self.on_select = on_select
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
        if self._selected is not None and (census is None or self._selected not in census.cells):
            self._selected = None
        self._draw()

    def select(self, key):
        """Programmatic selection (tests, keyboard) -- repaints rings + fires on_select."""
        if self._census is None or (key is not None and key not in self._census.cells):
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
        bits.append("Click for details.")
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
        if self._census is not None and not self._census.cells:
            t = self._ignore_zoom(sc.addSimpleText("No overrides in this folder.", self._font(9)))
            t.setBrush(muted)
            t.setPos(w / 2, h / 2)

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
    def _cell_at(self, view_pos):
        if self._census is None:
            return None
        sp = self.mapToScene(view_pos)
        cell = self.cell_px()
        bx, by = math.floor(sp.x() / cell), math.floor(sp.y() / cell)
        return (bx, by) if (bx, by) in self._census.cells else None

    def mousePressEvent(self, event):              # noqa: N802 (Qt override)
        if event.button() == Qt.MouseButton.LeftButton:
            hit = self._cell_at(event.position().toPoint())
            if hit is not None and hit != self._selected:
                self.select(hit)
        super().mousePressEvent(event)             # ScrollHandDrag panning still owns the drag

    def mouseMoveEvent(self, event):               # noqa: N802 (Qt override)
        if not event.buttons():
            over = self._cell_at(event.position().toPoint())
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor if over
                                      else Qt.CursorShape.OpenHandCursor)
        super().mouseMoveEvent(event)

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
        if step is not None and self._census is not None and self._census.cells:
            self._step_selection(step)
            event.accept()
            return
        super().keyPressEvent(event)

    def _step_selection(self, step):
        """Arrow keys walk the DEPLOYED blocks: the nearest deployed cell in that direction (keyboard
        parity with the click -- a canvas the keyboard cannot enter is a mouse-only surface)."""
        cells = self._census.cells
        if self._selected is None:
            self.select(min(cells))
            return
        sx, sy = self._selected
        dx, dy = step
        best, best_d = None, None
        for (bx, by) in cells:
            vx, vy = bx - sx, by - sy
            if (vx, vy) == (0, 0) or (dx and (vx * dx <= 0)) or (dy and (vy * dy <= 0)):
                continue
            d = (vx * vx + vy * vy, abs(vy) if dx else abs(vx))   # nearest, then straightest
            if best_d is None or d < best_d:
                best, best_d = (bx, by), d
        if best is not None:
            self.select(best)


class WorldDoc(QWidget):
    """The World tab: folder picker + Rescan over the :class:`AtlasCanvas`, with a details card for the
    selected block. All state is a :class:`~ff9mapkit.workspace.worldscan.WorldCensus`; all filesystem
    reads happen inside :meth:`refresh` (user-invoked, worker thread) -- never at construction, never on
    tab show."""

    _scan_done = Signal(object, object, object)    # (census | None, stock grid | None, error | None)

    def __init__(self, pal, *, on_setup=None, scale=100, game_path_fn=None):
        super().__init__()
        self.pal = pal
        self.on_setup = on_setup
        self._game_path_fn = game_path_fn          # None -> config.find_game_path, resolved at CALL time
        self._scale = scale
        self._census = None
        self._selected = None
        self._trees = []
        self._busy = False
        self._guide_state = ("scan", "")
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
        self.rescan_btn.clicked.connect(lambda: self.refresh())
        head.addWidget(self.rescan_btn)
        self.summary_lbl = widgets.role_label("", "caption")
        self.summary_lbl.setAccessibleName("Scan summary")
        head.addWidget(self.summary_lbl, 1)
        v.addLayout(head)
        self.canvas = AtlasCanvas(self.pal, on_select=self._on_select, scale=self._scale)
        v.addWidget(self.canvas, 1)
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
        sh.addLayout(brow)
        v.addWidget(strip)
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

    def retheme(self, pal):
        self.pal = pal
        if hasattr(self, "canvas"):
            self.canvas.retheme(pal)
            self._fill_legend()                    # the swatch pixmaps are palette-baked at build time
        if self._stack.currentWidget() is self._guide_page:
            self._show_guide(*self._guide_state)   # rebuild: the glyph pixmap is palette-tinted

    # -- the scan --
    def refresh(self, *, sync=False, folder=None):
        """Scan (or rescan) the deployed worldmap tree. Reads the game path + folder list on the GUI
        thread (cheap stats), then runs the real census on a worker; ``sync=True`` is the deterministic
        test/snap lane. Never called by the shell -- every invocation is a user gesture."""
        if self._busy:
            return
        fn = self._game_path_fn or config.find_game_path
        try:
            game = fn()
        except config.ConfigError as e:
            self._show_guide("nogame", str(e))
            return
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
        self.rescan_btn.setEnabled(True)
        self.rescan_btn.setText("Rescan")
        if err is not None:
            self._show_guide("error", err)
            return
        self._census = census
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
        if self._selected is not None and self._selected not in census.cells:
            self._selected = None
        self._on_select(self._selected)

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
        c = self._census.cells.get(key) if (self._census is not None and key is not None) else None
        if c is None:
            self.sel_title.setText("No block selected")
            self.sel_facts.setText("Click a block on the atlas — or arrow-key through them.")
            self.sel_parts.setText("")
            self._set_chip("", "info")
            self.copy_btn.setEnabled(False)
            self.open_btn.setEnabled(False)
            return
        cx, cz = worldscan.block_center(c.bx, c.by)
        self.sel_title.setText(f"Block[{c.bx}][{c.by}] — {c.kind}")
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

    def _copy_coords(self):
        if self._selected is None:
            return
        cx, cz = worldscan.block_center(*self._selected)
        QApplication.clipboard().setText(f"{cx:g} {cz:g}")
        self.copy_btn.setText("Copied ✓")          # text feedback, not motion (reduced-motion-safe)
        QTimer.singleShot(1400, lambda: self.copy_btn.setText("Copy centre coords"))

    def _open_folder(self):
        c = self._census.cells.get(self._selected) if self._census is not None else None
        if c is not None and c.dirpath is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(c.dirpath)))

    def _on_folder_pick(self, _ix):
        picked = self.folder_box.currentData()
        if picked is not None:
            self.refresh(folder=picked)
