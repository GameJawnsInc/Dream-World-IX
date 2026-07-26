"""The Behavior document -- rung A of the Behavior GUI: a READ-ONLY render of a field's
``[behavior]`` block (charter: ``studies/behavior-trees/GUI-VISION.md``).

Three surfaces inside one doc, all fed by :mod:`.behaviorscan`'s pure projections:

- **The Cast** (left): units / groups / pools / the data layer. Selecting a unit scopes the
  ladder and lights its radii on the stage.
- **The Ladder over the Stage** (center, stacked -- the owner's call on open question #1):
  branches as guarded priority rows, TOML order == priority order, the fallback labeled; below
  it the field's behavior geometry (posts, routes, refuges, scan/wander boxes, the selected
  unit's rings) in the map/world canvas grammar -- +z is UP-screen, the layout probe's frame.
- **The Instruments** (right): the compiler's own truth. ``validate()`` problems render
  always (pure, instant, from the OPEN document); the dry-compile report (blackboard map,
  byte histogram, flag indices) runs only behind the user's Compile click, on a worker
  thread, and reads the SAVED file -- the CLI's truth, labeled as such when the doc is dirty
  (the deploy-snapshot two-truths law).

Laws honoured by construction: no I/O at construction or on tab show (the startup-spend law --
the shell feeds the doc the already-parsed open dict); the canvas is painted, so CALIBRE
reaches it via ``set_scale`` and ``retheme`` redraws (the mapview rule); no widget stylesheet
except the canvas hint's selector-scoped one (the round-9 census shape); pane splits are NOT
persisted in rung A (nothing to fossilize); the doc EDITS nothing -- rung B owns writes.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QGraphicsEllipseItem, QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView,
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QScrollArea, QSplitter, QStackedLayout,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from . import behaviorscan, icons, widgets

_WORLD = 0.12                                     # world units -> scene px at zoom 1
_ZOOM_MIN, _ZOOM_MAX = 0.05, 6.0
_POST_R = 5                                       # a post marker's screen radius (px, zoom-immune)


class StageCanvas(QGraphicsView):
    """The behavior geometry as a chart: +z up-screen (the layout probe's frame, so the two
    instruments agree), Ctrl+scroll zoom / Ctrl+0 fit / Ctrl+1 1:1 (the atlas grammar). Posts
    and labels are screen-fixed furniture (the nameplate trick); rings and routes are real
    world geometry and scale with the zoom."""

    def __init__(self, palette, *, scale=100):
        super().__init__()
        self.pal = palette
        self._model = None
        self._selected = None                     # unit whose rings are lit
        self._scale = scale if scale in range(50, 301) else 100
        self._zoom = 1.0
        self._fit_pending = False
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor(palette["surface"]))
        self.setAccessibleName("Behavior stage")
        self.setAccessibleDescription(
            "The field's behavior geometry: unit posts, routes, refuges, scan boxes, and the "
            "selected unit's engagement radii")
        self._hint = QLabel("Ctrl+scroll zooms · Ctrl+0 fits", self.viewport())
        self._hint.setObjectName("behaviorHint")   # selector-scoped (the round-9 census law)
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
        self._draw()

    def retheme(self, palette):
        self.pal = palette
        self.setBackgroundBrush(QColor(palette["surface"]))
        self._style_hint()
        self._draw()

    def _style_hint(self):
        self._hint.setFont(self._font(8))
        surf = QColor(self.pal["surface"])
        self._hint.setStyleSheet(
            "QLabel#behaviorHint {"
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
    def set_model(self, model, selected=None, *, refit=False):
        """New geometry (+ the unit whose rings light). ``refit`` on a FIELD change only -- a
        same-field re-render keeps the user's zoom/pan (the map's own contract)."""
        self._model = model
        self._selected = selected
        if refit:
            self.resetTransform()
            self._zoom = 1.0
            self._fit_pending = True
        self._draw()

    def select_unit(self, name):
        if name != self._selected:
            self._selected = name
            self._draw()

    # -- frame mapping: +z is UP-screen (scene y grows down) --
    @staticmethod
    def _pt(x, z):
        return (x * _WORLD, -z * _WORLD)

    def _fit(self):
        r = self._scene.sceneRect()
        if r.isEmpty():
            return
        vw, vh = max(1, self.viewport().width()), max(1, self.viewport().height())
        z = min(vw / max(1.0, r.width()), vh / max(1.0, r.height())) * 0.94
        z = max(_ZOOM_MIN, min(3.0, z))
        self.resetTransform()
        self.scale(z, z)
        self._zoom = z
        self.centerOn(r.center())

    def paintEvent(self, ev):                      # noqa: N802 (Qt override)
        if self._fit_pending:                      # deferred to the first REAL paint: at set_model
            self._fit_pending = False              # time the tab may be hidden, the viewport stale
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

    # -- drawing --
    def _fixed(self, item):
        """Screen-fixed chart furniture (labels, post markers) -- readable at any zoom."""
        item.setFlag(item.GraphicsItemFlag.ItemIgnoresTransformations)
        return item

    def _anchor(self, x, z, tag):
        """A zero-size, zoom-immune anchor at a world point: its CHILDREN live in screen px
        (the nameplate trick -- readable furniture at any zoom)."""
        sx, sy = self._pt(x, z)
        anchor = self._scene.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
        anchor.setPos(sx, sy)
        anchor.setData(0, tag)
        return self._fixed(anchor)

    def _label(self, text, x, z, *, dx=8, dy=-16, color=None, bold=False, pt=8):
        anchor = self._anchor(x, z, "label")
        t = QGraphicsSimpleTextItem(text, anchor)
        t.setFont(self._font(pt, bold))
        t.setBrush(QBrush(QColor(color or self.pal["muted"])))
        t.setPos(dx, dy)                           # screen px, relative to the anchor
        return anchor

    def _marker(self, x, z, color, *, hollow=False, r=_POST_R, tag="post"):
        anchor = self._anchor(x, z, tag)
        dot = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r, anchor)
        dot.setPen(QPen(QColor(color), 1.6))
        dot.setBrush(QBrush(Qt.BrushStyle.NoBrush) if hollow else QBrush(QColor(color)))
        return anchor

    def _draw(self):
        sc, pal = self._scene, self.pal
        sc.clear()
        m = self._model
        if not m or m.get("bounds") is None:
            t = self._fixed(sc.addSimpleText(
                "No positions to draw — behavior units bind to named [[npc]]s with pos.",
                self._font(9)))
            t.setBrush(QBrush(QColor(pal["muted"])))
            sc.setSceneRect(-200, -60, 400, 120)
            t.setPos(-190, -8)
            return
        x0, z0, x1, z1 = m["bounds"]
        pad = max(120.0, 0.12 * max(x1 - x0, z1 - z0, 1))
        left, top = self._pt(x0 - pad, z1 + pad)
        right, bot = self._pt(x1 + pad, z0 - pad)
        sc.setSceneRect(QRectF(left, top, right - left, bot - top))

        def cosmetic(color, w=1.6, dash=None):
            pen = QPen(QColor(color), w)
            pen.setCosmetic(True)                  # rings/routes must survive fit zoom (the
            if dash:                               # atlas's vanishing-ring lesson)
                pen.setDashPattern(dash)
            return pen

        muted, border = pal["muted"], pal["border"]
        # wander + scan boxes (Chebyshev = squares in world frame). A wander box carries no
        # label of its own -- its unit's post sits at the centre and says whose it is
        # (snap-caught: the label pile-up at fit zoom was the canvas's dominant noise).
        for box, name in ([(w, None) for w in m["wanders"]]
                          + [(s, s["name"]) for s in m["scans"]]):
            bx0, by0 = self._pt(box["x"] - box["r"], box["z"] + box["r"])
            bx1, by1 = self._pt(box["x"] + box["r"], box["z"] - box["r"])
            it = sc.addRect(QRectF(bx0, by0, bx1 - bx0, by1 - by0),
                            cosmetic(border if name is None else muted, 1.2, [4, 4]))
            it.setData(0, "scan" if name else "wander")
            if name:
                self._label(f"scan · {name}", box["x"] - box["r"], box["z"] + box["r"],
                            dx=4, dy=4)
        # routes (patrol/march): real geometry, muted; the wrap leg only when closed
        for r in m["routes"]:
            pts = [self._pt(x, z) for x, z in r["points"]]
            seq = pts + [pts[0]] if r["closed"] and len(pts) > 2 else pts
            for a, b in zip(seq, seq[1:]):
                ln = sc.addLine(a[0], a[1], b[0], b[1], cosmetic(muted, 2.0))
                ln.setData(0, "route")
            for x, z in r["points"]:
                self._marker(x, z, muted, r=2.5, tag="routept")
            # label the FIRST LEG's midpoint, not point 0 -- a route usually starts at (or near)
            # its walker's post, and two labels on one spot was the snap's worst collision
            (ax, az), (bx2, bz2) = r["points"][0], r["points"][1 % len(r["points"])]
            self._label(f"{r['verb']} · {r['unit']}" + (" · auto" if r["auto"] else ""),
                        (ax + bx2) / 2, (az + bz2) / 2, dy=4)
        # flee refuges: numbered flags in priority order
        for ref in m["refuges"]:
            for i, (x, z) in enumerate(ref["points"], 1):
                self._marker(x, z, pal["warn"], hollow=True, r=4, tag="refuge")
                self._label(f"⚑{i} {ref['unit']}", x, z, color=pal["warn"], dy=-18)
        # the selected unit's rings: real world radii, quiet accent (selection state,
        # the one accent this canvas spends -- the map's ring language)
        rings = (m["rings"] or {}).get(self._selected or "", [])
        posts = {p["name"]: (p["x"], p["z"]) for p in m["posts"]}
        for ring in rings:
            cx = ring.get("x", posts.get(self._selected, (None, None))[0])
            cz = ring.get("z", posts.get(self._selected, (None, None))[1])
            if cx is None:
                continue
            rr = ring["radius"] * _WORLD
            sx, sy = self._pt(cx, cz)
            it = sc.addEllipse(sx - rr, sy - rr, 2 * rr, 2 * rr,
                               cosmetic(self.pal["accent"], 1.4, [5, 4]))
            it.setData(0, "ring")
        # posts + player last (loudest)
        for p in m["posts"]:
            col = muted if p["pooled"] else pal["success"]
            self._marker(p["x"], p["z"], col, hollow=p["pooled"])
            name = p["name"] + (" · pooled" if p["pooled"] else "")
            sel = p["name"] == self._selected
            self._label(name, p["x"], p["z"], color=pal["text"] if sel else muted,
                        bold=sel, pt=8.5)
        if m.get("player"):
            px, pz = m["player"]
            self._marker(px, pz, pal["text"], hollow=True, r=4, tag="player")
            self._label("player spawn", px, pz, color=pal["text"], dy=-18)


class LadderView(QWidget):
    """The selected unit's branches as read-only priority rows. Rebuilt per render (rows are
    few); each row: priority number, WHEN chips (ANDed), the DO verb + detail, decorator chips
    on the shoulder. The LAST unconditional row is the compiler's required fallback and says
    so. Rung B replaces these rows with editable ones -- keep this a plain vertical list."""

    def __init__(self, pal):
        super().__init__()
        self.pal = pal
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(10, 8, 10, 8)
        self._lay.setSpacing(6)
        self.setAccessibleName("Behavior ladder")

    def set_rows(self, unit_name, stats, rows):
        while self._lay.count():
            w = self._lay.takeAt(0).widget()
            if w is not None:
                w.setParent(None)                  # reparent NOW: a deleteLater-only clear leaves
                w.deleteLater()                    # zombie children until the loop runs (the
        #                                            harness's own DeferredDelete lesson)
        head = QHBoxLayout()
        head.setSpacing(10)
        title = widgets.role_label(unit_name or "—", "cardtitle")
        head.addWidget(title)
        if stats:
            head.addWidget(widgets.role_label(stats, "caption"))
        head.addStretch(1)
        hw = QWidget()
        hw.setLayout(head)
        self._lay.addWidget(hw)
        last_uncond = max((i for i, r in enumerate(rows) if r["unconditional"]), default=None)
        for i, row in enumerate(rows):
            self._lay.addWidget(self._row(row, fallback=(i == last_uncond and i == len(rows) - 1)))
        if not rows:
            self._lay.addWidget(widgets.caption(
                "This unit has no branches yet — every [[behavior.unit]] needs at least an "
                "unconditional fallback (patrol / hold / march / flee / wander / walk_to)."))
        self._lay.addStretch(1)

    def _chip(self, text):
        lab = widgets.role_label(text, "chip")
        lab.setProperty("mono", True)
        return lab

    def _row(self, row, *, fallback):
        frame = widgets.card()
        h = QHBoxLayout(frame)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(7)
        prio = widgets.role_label(str(row["index"]), "caption")
        prio.setProperty("mono", True)
        h.addWidget(prio)
        if row["conds"]:
            for ci, c in enumerate(row["conds"]):
                if ci:
                    h.addWidget(widgets.role_label("AND", "subtle"))
                h.addWidget(self._chip(c))
        else:
            h.addWidget(self._chip("always"))
        h.addWidget(widgets.role_label("→", "subtle"))
        verb = widgets.role_label(row["verb"], "cardtitle")
        verb.setProperty("mono", True)
        h.addWidget(verb)
        if row["detail"]:
            det = widgets.role_label(row["detail"], "caption")
            det.setProperty("mono", True)
            h.addWidget(det)
        h.addStretch(1)
        for d in row["decos"]:
            kind = "warn" if d.startswith(("raise ", "clear ")) else "info"
            h.addWidget(widgets.status_chip(d, kind))
        if fallback:
            h.addWidget(widgets.status_chip("fallback · required", "good"))
        frame.setAccessibleName(
            f"branch {row['index']}: " + (" and ".join(row["conds"]) or "always")
            + f" then {row['verb']}")
        return frame


class BehaviorDoc(QWidget):
    """The Behavior tab. The shell feeds it the OPEN field's parsed dict (``show_field``) on
    tab show / tree select -- never a file read; the Compile click is the only disk touch."""

    _compile_done = Signal(object)                 # CompileResult (worker -> GUI thread)

    def __init__(self, pal, *, scale=100):
        super().__init__()
        self.pal = pal
        self._scale = scale
        self._member = None
        self._path = None
        self._dirty = False
        self._raw = None
        self._result = None                        # the last CompileResult -- STATE, not widget
        #                                            visibility (a hidden tab must not forget it)
        self._selected_unit = None
        self._busy = False
        self._guide_state = "nofield"
        self._compile_done.connect(self._finish_compile)
        # The Instruments column is NOT one of this doc's panes: the shell docks it into its
        # INSPECTOR while this tab shows (owner's call -- a third in-doc column starved the
        # ladder of width). Built here, owned here; the shell only mounts/unmounts it.
        self.instruments = self._build_instruments()
        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._guide_page = self._build_guide(self._guide_state)
        self._stack.addWidget(self._guide_page)
        self._content = self._build_content()
        self._stack.addWidget(self._content)
        self._stack.setCurrentWidget(self._guide_page)

    # -- pages --
    def _build_guide(self, state):
        glyph = icons.pixmap("script", self.pal["muted"], 46)
        if state == "nobehavior":
            return widgets.empty_state(
                "", "This field has no [behavior] block",
                teach="Behavior gives named [[npc]]s compiled AI — patrols, chases, alarms, "
                      "combat — as priority branches in the field.toml. The format lives in "
                      "docs/BEHAVIOR.md; benches 30410-30418 are worked examples.",
                icon_pixmap=glyph)
        return widgets.empty_state(                # "nofield" -- the front door
            "", "Behavior renders a field's [behavior] block",
            teach="Open a campaign or a loose field and select a field in the tree — its "
                  "behavior units, ladders, and stage geometry render here, read-only.",
            icon_pixmap=glyph)

    def _show_guide(self, state):
        self._guide_state = state
        old = self._guide_page
        self._guide_page = self._build_guide(state)
        self._stack.addWidget(self._guide_page)
        self._stack.setCurrentWidget(self._guide_page)
        self._stack.removeWidget(old)
        old.deleteLater()

    def _build_content(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(10, 8, 10, 10)
        outer.setSpacing(8)
        head = QHBoxLayout()
        head.setSpacing(10)
        self.head_title = widgets.role_label("Behavior", "head")
        head.addWidget(self.head_title)
        self.head_sum = widgets.role_label("", "caption")
        head.addWidget(self.head_sum, 1)
        head.addStretch(0)
        outer.addLayout(head)
        split = QSplitter()
        split.setChildrenCollapsible(False)
        # cast rail
        self.cast = QTreeWidget()
        self.cast.setHeaderHidden(True)
        self.cast.setAccessibleName("Behavior cast")
        self.cast.setAccessibleDescription(
            "Units, groups, pools, and data (counters, tables, schedules, scans, HUD strips). "
            "Selecting a unit shows its ladder and lights its radii on the stage.")
        self.cast.itemSelectionChanged.connect(self._on_cast_select)
        split.addWidget(self.cast)
        # center: ladder over stage (stacked -- the ratified answer to open question #1)
        mid = QSplitter(Qt.Orientation.Vertical)
        mid.setChildrenCollapsible(False)
        self.ladder = LadderView(self.pal)
        lscroll = QScrollArea()
        lscroll.setWidgetResizable(True)
        lscroll.setWidget(self.ladder)             # h-bar stays as-needed: a denied width must
        lscroll.setFrameShape(QFrame.Shape.NoFrame)  # scroll, never clip (the round-13 law)
        mid.addWidget(lscroll)
        self.canvas = StageCanvas(self.pal, scale=self._scale)
        mid.addWidget(self.canvas)
        k = self._scale / 100
        mid.setSizes([int(340 * k), int(280 * k)])
        split.addWidget(mid)
        split.setStretchFactor(1, 1)
        # Ask for LESS than the realistic ~700px budget at a 1280 window (snap-measured: a
        # request over the available width let Qt starve the CENTER pane while rails kept theirs).
        split.setSizes([int(170 * k), int(530 * k)])
        outer.addWidget(split, 1)
        return page

    def _build_instruments(self):
        """The Problems/Compile column. A PLAIN widget, no scroll wrapper of its own -- its
        host (the shell inspector) already scrolls, and its h-bar is off, so everything in
        here must wrap or scroll internally (the report box scrolls itself)."""
        col = QWidget()
        v = QVBoxLayout(col)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(7)
        v.addWidget(widgets.role_label("PROBLEMS", "subtle"))
        self.problems_lbl = widgets.caption("")
        self.problems_lbl.setWordWrap(True)
        v.addWidget(self.problems_lbl)
        v.addWidget(widgets.role_label("COMPILE", "subtle"))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.compile_btn = QPushButton("Compile (dry)")
        self.compile_btn.setToolTip(
            "Dry-compile the SAVED field.toml through the real behavior compiler — the "
            "blackboard map, flag indices, and the byte histogram. Writes nothing.")
        self.compile_btn.clicked.connect(lambda: self.compile_now())
        row.addWidget(self.compile_btn)
        row.addStretch(1)
        v.addLayout(row)
        self.compile_note = widgets.caption("")
        self.compile_note.setWordWrap(True)
        v.addWidget(self.compile_note)
        self.flags_host = QWidget()
        self.flags_lay = QVBoxLayout(self.flags_host)
        self.flags_lay.setContentsMargins(0, 0, 0, 0)
        self.flags_lay.setSpacing(3)
        v.addWidget(self.flags_host)
        self.report_box = QPlainTextEdit()         # the app sheet makes any QPlainTextEdit the
        self.report_box.setReadOnly(True)          # mono well (log_bg + Cascadia)
        self.report_box.setAccessibleName("Compile report")
        self.report_box.setVisible(False)
        fm = QFontMetrics(self.report_box.font())
        self.report_box.setMinimumHeight(fm.lineSpacing() * 12)
        v.addWidget(self.report_box, 1)
        v.addStretch(0)
        return col

    # -- shell hooks --
    def crumb_label(self):
        return f"Behavior — {self._member}" if self._member else "Behavior"

    def set_scale(self, pct):
        self._scale = pct
        if hasattr(self, "canvas"):
            self.canvas.set_scale(pct)

    def retheme(self, pal):
        self.pal = pal
        if hasattr(self, "canvas"):
            self.canvas.retheme(pal)
            self.ladder.pal = pal
        if self._stack.currentWidget() is self._guide_page:
            self._show_guide(self._guide_state)    # rebuild: the glyph pixmap is palette-tinted
        elif self._raw is not None and self._member:
            self._render()                         # chips/canvas repaint under the new palette

    # -- the feed (shell-pushed, in-memory, no file I/O) --
    def show_none(self):
        self._member = self._path = self._raw = None
        self._set_result(None)                     # the docked inspector column must not keep a
        self.problems_lbl.setText("")              # dead project's report or problems
        widgets.set_state(self.problems_lbl, "")
        self._show_guide("nofield")

    def show_field(self, member, raw, path=None, *, dirty=False):
        """Render the OPEN field's parsed dict. ``path`` (the saved file) feeds the Compile
        lane; ``dirty`` labels which truth the instruments would read."""
        same_field = member == self._member
        self._member, self._raw, self._path, self._dirty = member, raw, path, dirty
        if not behaviorscan.has_behavior(raw):
            self._show_guide("nobehavior")
            return
        if not same_field:
            self._selected_unit = None
            self._set_result(None)                 # another field's report must not linger
        self._stack.setCurrentWidget(self._content)
        self._render(refit=not same_field)

    def _render(self, *, refit=False):
        raw = self._raw
        cast = behaviorscan.cast_model(raw)
        names = [u["name"] for u in cast["units"]]
        if self._selected_unit not in names:
            self._selected_unit = names[0] if names else None
        self.head_title.setText(self._member or "Behavior")
        self.head_sum.setText(behaviorscan.summary(raw))
        self._fill_cast(cast)
        self._fill_ladder(cast)
        self.canvas.set_model(behaviorscan.stage_model(raw), self._selected_unit, refit=refit)
        problems = behaviorscan.validate_problems(raw)
        if problems:
            self.problems_lbl.setText("\n".join(f"• {p}" for p in problems))
            widgets.set_state(self.problems_lbl, "error")
        else:
            self.problems_lbl.setText("No structural problems.")
            widgets.set_state(self.problems_lbl, "")
        note = ("Compiled from the SAVED file — unsaved edits are not included. Save first "
                "for current numbers." if self._dirty else "")
        if not self._has_result():
            self.compile_note.setText(note or "Nothing compiled yet.")

    def _fill_cast(self, cast):
        self.cast.blockSignals(True)
        self.cast.clear()

        def sect(title):
            it = QTreeWidgetItem([title])
            it.setFlags(Qt.ItemFlag.ItemIsEnabled)   # a heading, not a choice
            self.cast.addTopLevelItem(it)
            return it

        selected_item = None
        units_it = sect("UNITS")
        for u in cast["units"]:
            bits = []
            if u["hp"] is not None:
                bits.append(f"{u['hp']} hp")
            if u["pooled"]:
                bits.append(f"pooled{' · ' + str(u['pool']) if u['pool'] else ''}")
            row = QTreeWidgetItem([u["name"] + ("   · " + " · ".join(bits) if bits else "")])
            row.setToolTip(0, row.text(0))         # the rail elides; hover carries the full row
            row.setData(0, Qt.ItemDataRole.UserRole, ("unit", u["name"]))
            units_it.addChild(row)
            if u["name"] == self._selected_unit:
                selected_item = row
        for title, rows in (("GROUPS", [(g["name"], f"{len(g['members'])} members")
                                        for g in cast["groups"]]),
                            ("POOLS", [(p["name"], p["note"]) for p in cast["pools"]]),
                            ("DATA", [(d["name"], d["note"]) for d in cast["data"]])):
            if not rows:
                continue
            s = sect(title)
            for name, note in rows:
                it = QTreeWidgetItem([f"{name}   · {note}" if note else name])
                it.setToolTip(0, it.text(0))
                it.setData(0, Qt.ItemDataRole.UserRole, ("info", name))
                s.addChild(it)
        self.cast.expandAll()
        if selected_item is not None:
            self.cast.setCurrentItem(selected_item)
        self.cast.blockSignals(False)

    def _fill_ladder(self, cast):
        u = next((x for x in cast["units"] if x["name"] == self._selected_unit), None)
        stats = []
        if u:
            if u["hp"] is not None:
                stats.append(f"{u['hp']} hp")
            if u["speed"] is not None:
                stats.append(f"speed {u['speed']}")
            n = u["branches"]
            stats.append(f"{n} branch{'es' if n != 1 else ''}")
            if u["pooled"]:
                stats.append("pooled")
        rows = behaviorscan.ladder_model(self._raw, self._selected_unit) \
            if self._selected_unit else []
        self.ladder.set_rows(self._selected_unit, " · ".join(stats), rows)

    def _on_cast_select(self):
        items = self.cast.selectedItems()
        payload = items[0].data(0, Qt.ItemDataRole.UserRole) if items else None
        if payload and payload[0] == "unit" and payload[1] != self._selected_unit:
            self._selected_unit = payload[1]
            self._fill_ladder(behaviorscan.cast_model(self._raw))
            self.canvas.select_unit(payload[1])

    # -- the Compile lane (the doc's only disk touch; user-invoked, worker thread) --
    def compile_now(self, *, sync=False):
        if self._busy or self._raw is None:
            return
        if not self._path:
            self.compile_note.setText("This document has no saved file yet — save it first, "
                                      "then compile.")
            return
        self._busy = True
        self.compile_btn.setEnabled(False)
        self.compile_btn.setText("Compiling…")
        if sync:                                   # the deterministic test/snap lane
            self._finish_compile(behaviorscan.dry_compile(self._path))
            return
        path = self._path
        threading.Thread(target=self._worker, args=(path,), daemon=True).start()

    def _worker(self, path):
        res = behaviorscan.dry_compile(path)
        try:
            self._compile_done.emit(res)           # RuntimeError-guarded: the doc may be dead
        except RuntimeError:
            pass

    def _finish_compile(self, res):
        self._busy = False
        self.compile_btn.setEnabled(True)
        self.compile_btn.setText("Compile (dry)")
        self._set_result(res)

    def _has_result(self):
        return self._result is not None

    def _set_result(self, res):
        self._result = res
        while self.flags_lay.count():
            w = self.flags_lay.takeAt(0).widget()
            if w is not None:
                w.setParent(None)                  # see LadderView.set_rows -- no zombie rows
                w.deleteLater()
        if res is None:
            self.report_box.setVisible(False)
            self.report_box.setPlainText("")
            self.compile_note.setText("Nothing compiled yet.")
            return
        if not res.ok:
            self.compile_note.setText("\n".join(f"• {p}" for p in res.problems)
                                      or "Compile failed.")
            widgets.set_state(self.compile_note, "error")
            self.report_box.setVisible(False)
            return
        widgets.set_state(self.compile_note, "")
        head = f"Compiles — {res.new_bytes:,} B of new bytecode" if res.new_bytes else "Compiles."
        if res.stable_hash:
            head += f" · hash {res.stable_hash[:8]}"
        if self._dirty:
            head += "\nRead from the SAVED file — unsaved edits not included."
        self.compile_note.setText(head)
        for name, idx in list(res.public_flags) + list(res.pool_flags):
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            lab = widgets.role_label(f"{name} → {idx}", "caption")
            lab.setProperty("mono", True)
            h.addWidget(lab, 1)
            btn = QPushButton("Copy")              # short: the ~200px rail clipped the long form
            btn.setProperty("role", "quiet")
            btn.setToolTip(f"Copy `set_flag = [{idx}, 1]` — paste into a [[choice]] option row.")
            btn.clicked.connect(lambda _=False, i=idx:
                                QGuiApplication.clipboard().setText(f"set_flag = [{i}, 1]"))
            h.addWidget(btn)
            self.flags_lay.addWidget(row)
        text = res.report or ""
        if res.routed:
            text += "\n\nauto-routed legs:\n" + "\n".join(f"  {r}" for r in res.routed)
        if res.size_text:
            text += "\n\n" + res.size_text
        self.report_box.setPlainText(text.strip())
        self.report_box.setVisible(True)
