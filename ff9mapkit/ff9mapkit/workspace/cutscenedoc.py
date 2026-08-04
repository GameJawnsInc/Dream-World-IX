"""The Cutscene document — the redesigned authoring surface for a field's ``[[cutscene]]``
dispatch (plan: the Cutscene doc tab, Behavior-tab idiom; review record:
``studies/cutscene-authoring/REVIEW.md``).

Four surfaces inside one doc, all fed by :mod:`.cutscenescan`'s pure projections:

- **The scene rail** (left): every scene of the dispatch — its gate ("plays at beat 100"),
  narration vs cast, step count. The old form edited scene #0 and hid the rest; the rail IS
  the dispatch.
- **The step ladder** (center): steps as 0-based rows in the ladder grammar (the build's own
  lint addresses), parallel beats marked (``‖ with previous``), say lines readable in place.
- **The stage** (below): a top-down chart of the scene's STAGING — markers, the cast's start
  posts, every movement leg chained the way the compiler chains it. Staging verdicts paint
  on the exact leg that stalls (the sweep-jam idiom).
- **The storyboard** (a strip): BEAT-indexed, never a clock — ``say`` blocks on the player,
  so a seconds axis would be fiction (the review's §4 verdict). Scrub beats; the say line
  shows with its final in-game wrapping; the honesty ledger sits on the strip's face.

The instruments column (PROBLEMS live from the open doc + the staging check + Open the .toml)
docks into the shell's inspector while this tab shows — the Behavior contract exactly.

Laws honoured by construction: no I/O at construction or on tab show (the shell feeds the
already-parsed open dict; the ONE disk read is the staging check's walkmesh, user-invoked,
then warm); the canvas is painted, so CALIBRE reaches it via ``set_scale`` and ``retheme``
redraws; edits (the flip commit) go op → ``on_edit(member, label)`` → the shell's checkpoint —
this doc never composes an undo label and never touches a file.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QPushButton, QScrollArea, QSlider,
    QSplitter, QStackedLayout, QVBoxLayout, QWidget,
)

from .. import dialogue as _dlg
from . import cutscenescan, icons, widgets
from .behaviordoc import StageCanvas


class CutsceneStage(StageCanvas):
    """The scene's staging as a chart. Subclasses :class:`StageCanvas` for the machinery a
    canvas must never paraphrase — the GC-child law (``_child``), the no-``parentItem()``
    grab resolution, the one-callback-per-drop drag, the label de-collision pass, zoom/fit —
    and overrides only ``_draw`` (+ its own model setters). ``+z`` is UP-screen, the layout
    probe's frame, same as the Behavior stage."""

    SPACING_KINDS = ("post", "player", "target")   # a dragged walk target gets the ~192u ring

    def __init__(self, palette, *, scale=100, on_move=None, on_insert=None, on_delete=None):
        super().__init__(palette, scale=scale, on_move=on_move,
                         on_insert=on_insert, on_delete=on_delete)
        self.setAccessibleName("Cutscene stage")
        self.setAccessibleDescription(
            "The scene's staging: markers, the cast's start posts, other NPCs as obstacles, "
            "and each actor's movement legs; staging problems paint on the failing leg")
        self._board = None                         # cutscenescan.storyboard dict (or None)
        self._beat = 0
        self._verdict_rows = []                    # cutscenescan.stage_verdicts rows
        self._selected_step = None                 # ladder selection -> the accented leg

    # -- model setters (each ends in one _draw; the host renders, never the reverse) --
    def set_scene(self, model, *, refit=False, handles=None):
        """New staging geometry (``cutscenescan.stage_model``). ``refit`` on a field/scene
        switch only — a same-scene re-render keeps the user's zoom/pan."""
        super().set_model(model, None, refit=refit, handles=handles)

    def set_storyboard(self, board, beat=0):
        """Enter/refresh storyboard mode (``None`` leaves it): the chart shows the ACTIVE
        beat — its legs accented, every cast position at end-of-beat, prior legs as a faint
        trail — instead of the whole scene's legs at once."""
        self._board = board
        self._beat = int(beat)
        self._draw()

    def set_verdicts(self, rows):                  # overrides the SweepResult-shaped base
        """Painted staging verdicts (``cutscenescan.stage_verdicts`` rows). Persist across
        redraws until the host replaces them — a redraw must not silently un-say a stall."""
        self._verdict_rows = list(rows or [])
        self._draw()

    def set_selected_step(self, idx):
        if idx == self._selected_step:
            return
        self._selected_step = idx
        self._draw()

    # -- drawing --
    def _pts(self):
        """Every world point the current model/board/verdicts place — the bounds source."""
        m = self._model or {}
        pts = [(mk["x"], mk["z"]) for mk in m.get("markers", [])]
        pts += [(c["x"], c["z"]) for c in m.get("cast", []) if c.get("placed")]
        pts += [(o["x"], o["z"]) for o in m.get("obstacles", [])]
        if m.get("player"):
            pts.append(m["player"])
        for leg in m.get("legs", []):
            pts += list(leg["points"])
        for v in self._verdict_rows:
            pts += [v["a"], v["b"]]
        if self._board:
            for b in self._board.get("beats", []):
                pts += list(b["positions"].values())
        return pts

    def _polyline(self, points, pen, tag):
        for a, b in zip(points, points[1:]):
            p0, p1 = self._pt(a[0], a[1]), self._pt(b[0], b[1])
            ln = self._scene.addLine(p0[0], p0[1], p1[0], p1[1], pen)
            ln.setData(0, tag)

    def _draw(self):
        sc, pal = self._scene, self.pal
        self._reset_scene()
        m = self._model
        pts = self._pts()
        if not m or not pts:
            t = self._fixed(sc.addSimpleText(
                "Nothing to stage yet — a cast member, a marker, or the player spawn "
                "gives this scene a floor.", self._font(9)))
            t.setBrush(QBrush(QColor(pal["muted"])))
            sc.setSceneRect(-260, -60, 520, 120)
            t.setPos(-250, -8)
            return
        x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
        z0, z1 = min(p[1] for p in pts), max(p[1] for p in pts)
        pad = max(120.0, 0.12 * max(x1 - x0, z1 - z0, 1))
        left, top = self._pt(x0 - pad, z1 + pad)
        right, bot = self._pt(x1 + pad, z0 - pad)
        from PySide6.QtCore import QRectF
        sc.setSceneRect(QRectF(left, top, right - left, bot - top))

        def cosmetic(color, w=1.6, dash=None, alpha=None):
            c = QColor(color)
            if alpha is not None:
                c.setAlpha(alpha)
            pen = QPen(c, w)
            pen.setCosmetic(True)                  # legs must survive fit zoom (the atlas's
            if dash:                               # vanishing-ring lesson)
                pen.setDashPattern(dash)
            return pen

        cast_names = {c["name"] for c in m.get("cast", [])}
        # markers -- the named points a walk can aim at (review B5: they were on no canvas)
        for mk in m.get("markers", []):
            self._marker(mk["x"], mk["z"], pal["muted"], hollow=True, r=4, tag="marker")
            self._label(mk["name"], mk["x"], mk["z"])
        # other NPCs -- the obstacles a walk must clear
        for o in m.get("obstacles", []):
            self._marker(o["x"], o["z"], pal["muted"], r=3, tag="npc")
            self._label(o["name"], o["x"], o["z"])
        # the player spawn, when the player is not ON stage
        if m.get("player") and "player" not in cast_names:
            px, pz = m["player"]
            self._marker(px, pz, pal["text"], hollow=True, r=5, tag="player")
            self._label("player spawn", px, pz)
        board = self._board if (self._board and self._board.get("beats")) else None
        # the cast's START posts: solid in scene mode, hollow origin-ghosts under a storyboard
        for c in m.get("cast", []):
            if not c.get("placed"):
                continue
            self._marker(c["x"], c["z"], pal["accent"], hollow=board is not None,
                         r=5, tag="post")
            if board is None:
                self._label(c["name"], c["x"], c["z"], color=pal["text"], bold=True)
        if board is None:
            # SCENE mode: every movement leg, chained the way the compiler chains it
            for leg in m.get("legs", []):
                sel = leg["step"] == self._selected_step
                pen = cosmetic(pal["accent"] if sel else pal["muted"],
                               2.2 if sel else 1.6,
                               dash=([2, 3] if leg["kind"] == "teleport" else None))
                self._polyline(leg["points"], pen, "leg")
                tx, tz = leg["points"][-1]
                self._marker(tx, tz, pal["accent"] if sel else pal["muted"],
                             hollow=True, r=3, tag="target")
        else:
            # STORYBOARD mode: the trail up to the active beat, then the beat itself
            beats = board["beats"]
            k = max(0, min(self._beat, len(beats) - 1))
            for b in beats[:k]:
                for leg in b["legs"]:
                    self._polyline(leg["points"], cosmetic(pal["muted"], 1.0, alpha=90),
                                   "trail")
            for leg in beats[k]["legs"]:
                self._polyline(leg["points"], cosmetic(pal["accent"], 2.0), "beatleg")
            for name, (bx, bz) in beats[k]["positions"].items():
                self._marker(bx, bz, pal["text"], r=5, tag="beatpos")
                self._label(name, bx, bz, color=pal["text"], bold=True)
        # staging verdicts: the failing leg, at the exact spot (the sweep-jam idiom)
        for v in self._verdict_rows:
            (ax, az), (bx, bz) = v["a"], v["b"]
            p0, p1 = self._pt(ax, az), self._pt(bx, bz)
            ln = sc.addLine(p0[0], p0[1], p1[0], p1[1], cosmetic(pal["error"], 3.0))
            ln.setData(0, "verdict")
            self._marker(bx, bz, pal["error"], hollow=True, r=4, tag="verdict")
            self._label(f"step {v['step']} stalls here", bx, bz,
                        color=pal["error"], dy=-28, tip=v["text"])
        # the honesty placard: dropped legs must be SAID, not implied walkable
        if m.get("unresolved"):
            n = m["unresolved"]
            t = self._fixed(sc.addSimpleText(
                f"{n} movement target{'s' if n != 1 else ''} unresolved — not drawn "
                f"(unknown name / unplaced actor)", self._font(8)))
            t.setBrush(QBrush(QColor(pal["warn"])))
            t.setPos(left + 8, top + 6)
            t.setData(0, "unresolved")
        self._draw_handles()                       # the edit layer, topmost for itemAt
        self._decollide_labels()


class _StepRow(QFrame):
    """One ladder card. A QFrame with the card role (widgets.card's shape) plus a click-to-
    select seam — selection drives the stage's accented leg (and, at the flip, the editor)."""

    def __init__(self, on_click=None):
        super().__init__()
        self.setProperty("role", "card")
        self._on_click = on_click

    def mousePressEvent(self, event):              # noqa: N802 (Qt override)
        if self._on_click:
            self._on_click()
        super().mousePressEvent(event)


class StepLadder(QWidget):
    """The scene's steps as 0-based rows (the build's own lint addresses steps 0-based; a
    surface that counts differently makes every warning a riddle). Rows stay dumb — every
    mutation goes through the host's ``actions`` dict ({} = read-only), which owns the raw
    dict and the shell's undo contract. Selection is a render concern and stays here."""

    def __init__(self, pal, actions=None, on_select=None):
        super().__init__()
        self.pal = pal
        self.actions = actions or {}
        self.on_select = on_select
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(10, 8, 10, 8)
        self._lay.setSpacing(6)
        self._idx_chips = []                       # the storyboard's ▶ beat sweep writes these
        self._selected = None
        self._beat_marks = set()
        self.setAccessibleName("Cutscene steps")

    def set_beat_marks(self, idxs):
        """Mark the steps in the storyboard's ACTIVE beat. Shape, not colour: ▶ on the
        index chip (the behavior ladder's own sim idiom)."""
        self._beat_marks = set(idxs or ())
        for i, lab in enumerate(self._idx_chips):
            lab.setText(self._chip_text(i))

    def _chip_text(self, i):
        if i in self._beat_marks:
            return f"▶ {i}"
        if i == self._selected:
            return f"▸ {i}"
        return str(i)

    def set_rows(self, rows, selected=None):
        self._selected = selected
        self._idx_chips = []
        while self._lay.count():
            w = self._lay.takeAt(0).widget()
            if w is not None:
                w.hide()                           # HIDE FIRST: reparenting a VISIBLE widget to
                w.setParent(None)                  # None makes it a top-level OS window for the
                w.deleteLater()                    # instant before deleteLater lands -- a reorder
        #                                            sprayed phantom "pythonw" windows (playtest-
        #                                            caught in the behavior ladder; same teardown,
        #                                            copied not paraphrased).
        for row in rows:
            self._lay.addWidget(self._row(row))
        if not rows:
            self._lay.addWidget(widgets.caption(
                "No steps yet — a cutscene is an ordered list of beats: say a line, walk an "
                "actor, wait, open/close windows, set a flag."))
        self._lay.addStretch(1)

    def _row(self, row):
        i = row["idx"]
        frame = _StepRow(on_click=(lambda i=i: self.on_select(i)) if self.on_select else None)
        h = QHBoxLayout(frame)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(7)
        idx = widgets.role_label(self._chip_text(i), "caption")
        idx.setProperty("mono", True)
        idx.setMinimumWidth(idx.fontMetrics().horizontalAdvance("▶ 88"))   # ▶ must not reflow
        h.addWidget(idx)
        self._idx_chips.append(idx)
        # rowtools sit LEFT, pinned beside the index (a right-aligned control inside an
        # h-scrolling row lives off-screen -- the behavior ladder's snap-caught law)
        if self.actions:
            for glyph, tip, cb in (
                    ("↑", "Move this step up", lambda _=False, s=i: self.actions["move"](s, -1)),
                    ("↓", "Move this step down", lambda _=False, s=i: self.actions["move"](s, +1)),
                    ("✎", "Edit this step", lambda _=False, s=i: self.actions["edit"](s)),
                    ("⧉", "Duplicate this step", lambda _=False, s=i: self.actions["dup"](s)),
                    ("✕", "Remove this step (Ctrl+Z undoes)",
                     lambda _=False, s=i: self.actions["delete"](s))):
                btn = QPushButton(glyph)
                btn.setProperty("role", "rowtool")
                btn.setToolTip(tip)
                btn.setAccessibleName(f"{tip} — step {i}")
                btn.clicked.connect(cb)
                h.addWidget(btn)
        if row["actor"]:
            chip = widgets.role_label(row["actor"], "chip")
            chip.setProperty("mono", True)
            h.addWidget(chip)
        verb = widgets.role_label(row["verb"], "cardtitle")
        verb.setProperty("mono", True)
        h.addWidget(verb)
        if row["detail"]:
            det = widgets.ElideLabel(row["detail"], mono=not row["is_text"])
            det.setToolTip(row["detail"])
            h.addWidget(det, 1)
        else:
            h.addStretch(1)
        if row["with_prev"]:
            h.addWidget(widgets.status_chip("‖ with previous", "info"))
        if row["extras"]:
            ex = widgets.status_chip("+" + ", ".join(row["extras"]), "info")
            ex.setToolTip("Extra keys on this step: " + ", ".join(row["extras"]))
            h.addWidget(ex)
        frame.setAccessibleName(
            f"step {i}: " + (f"{row['actor']} " if row["actor"] else "") + row["verb"]
            + (" runs with the previous beat" if row["with_prev"] else ""))
        return frame


class CutsceneDoc(QWidget):
    """The Cutscene tab. The shell feeds it the OPEN field's parsed dict (``show_field``) on
    tab show / tree select — never a file read; the doc's ONE disk touch is the staging
    check's walkmesh (user-invoked, then warm for re-judges — the two-truths split, stated
    on the button)."""

    _stage_done = Signal(object)                   # (gen, StagingResult, verdict_rows, wmesh|None)

    def __init__(self, pal, *, scale=100, on_edit=None, flag_names_fn=None,
                 pick_anim=None, open_toml=None):
        super().__init__()
        self.pal = pal
        self._scale = scale
        self.on_edit = on_edit                     # (member, label) -> the shell's checkpoint hook
        self.flag_names_fn = flag_names_fn         # the campaign's [[flag]] table for the mesh load
        self.pick_anim = pick_anim                 # the animation-picker seam (the flip spends it)
        self.open_toml = open_toml                 # (member) -> open the file in the OS editor
        self._member = None
        self._path = None
        self._raw = None
        self._merged_fn = None                     # the scene.toml split: markers/positions can
        #                                            live in the sibling file; STAGING and the
        #                                            board must see the MERGED doc
        self._dirty = False
        self._scene = 0                            # the rail's selected scene (0-based, lint's own)
        self._selected_step = None
        self._board = None                         # the storyboard model (when the strip is on)
        self._guide_state = "nofield"
        self._wmesh = None                         # the staging lane's cached walkmesh (per field)
        self._stage_busy = False
        self._stage_armed = False                  # first EXPLICIT check arms auto re-judges
        self._stage_gen = 0                        # field switch/close drops in-flight results
        self._stage_done.connect(self._finish_stage)
        self._restage_timer = QTimer(self)
        self._restage_timer.setSingleShot(True)
        self._restage_timer.setInterval(500)
        self._restage_timer.timeout.connect(self._restage)
        # the instruments column is NOT a doc pane: the shell docks it into its INSPECTOR
        # while this tab shows (the Behavior contract)
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
        glyph = icons.pixmap("play", self.pal["muted"], 46)
        if state == "noscene":
            return widgets.empty_state(
                "", "This field has no [[cutscene]] scene",
                teach="A cutscene is an ordered list of steps that runs with control locked: "
                      "say lines, walks, animations, windows, flags. A CAST (actors = "
                      "[names]) stages NPCs and the player; no cast = narration. Repeat "
                      "[[cutscene]] blocks — each gated to its own story beat — for the "
                      "per-field dispatch (at most one fires per load).",
                icon_pixmap=glyph)
        return widgets.empty_state(                # "nofield" -- the front door
            "", "Cutscene stages a field's [[cutscene]] scenes",
            teach="Open a campaign or a loose field and select a field in the tree — its "
                  "scenes, steps, staging, and the beat storyboard render here.",
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
        self.head_title = widgets.role_label("Cutscene", "head")
        head.addWidget(self.head_title)
        self.head_sum = widgets.ElideLabel("")     # yields width, never floors the doc minimum
        head.addWidget(self.head_sum, 1)
        outer.addLayout(head)
        split = QSplitter()
        split.setChildrenCollapsible(False)
        # the scene rail: the dispatch, visible at last
        rail_col = QWidget()
        rv = QVBoxLayout(rail_col)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(4)
        self.rail = QListWidget()
        self.rail.setAccessibleName("Cutscene scenes")
        self.rail.setAccessibleDescription(
            "Every [[cutscene]] scene of this field's dispatch, with its story gate. "
            "At most one fires per field load.")
        self.rail.currentRowChanged.connect(self._on_scene_select)
        rv.addWidget(self.rail, 1)
        split.addWidget(rail_col)
        # center: the scene bar OUTSIDE the scroll, then ladder over stage
        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(4)
        bar = QWidget()
        bh = QHBoxLayout(bar)
        bh.setContentsMargins(10, 4, 10, 0)
        bh.setSpacing(10)
        self.scene_title = widgets.role_label("—", "cardtitle")
        bh.addWidget(self.scene_title)
        self.scene_gate = widgets.ElideLabel("", min_ch=12)
        bh.addWidget(self.scene_gate, 1)
        self.board_btn = QPushButton("▶ Storyboard")
        self.board_btn.setProperty("role", "quiet")
        self.board_btn.setCheckable(True)
        self.board_btn.setToolTip(
            "Scrub the scene BEAT by BEAT — positions chain the way the compiler chains "
            "them, the say line shows with its final in-game wrapping.\n"
            "No clock, on purpose: a say waits for the player, so seconds would be fiction.")
        self.board_btn.toggled.connect(self._toggle_board)
        bh.addWidget(self.board_btn)
        cl.addWidget(bar)
        # the storyboard strip (hidden until ▶ Storyboard)
        self.board_bar = QWidget()
        sv = QVBoxLayout(self.board_bar)
        sv.setContentsMargins(10, 0, 10, 0)
        sv.setSpacing(2)
        srow = QHBoxLayout()
        srow.setSpacing(8)
        for glyph, d, name in (("◀", -1, "Previous beat"), ("▶", +1, "Next beat")):
            b = QPushButton(glyph)                 # text glyphs, the rowtool family's idiom --
            b.setProperty("role", "quiet")         # NOT U+23xx media glyphs (the emoji-face law)
            b.setToolTip(name)
            b.setAccessibleName(name)
            b.clicked.connect(lambda _=False, k=d: self._show_beat(self._beat_pos() + k))
            srow.addWidget(b)
        self.board_slider = QSlider(Qt.Orientation.Horizontal)
        self.board_slider.setAccessibleName("Storyboard beat")   # a slider is a real Tab stop
        self.board_slider.setToolTip("Scrub the scene's beats")
        self.board_slider.valueChanged.connect(self._on_board_scrub)
        self.board_slider.setMinimumWidth(int(120 * self._scale / 100))   # never a sliver
        srow.addWidget(self.board_slider, 1)
        self.board_pos = widgets.role_label("", "caption")
        self.board_pos.setProperty("mono", True)
        srow.addWidget(self.board_pos)
        sv.addLayout(srow)
        self.board_say = QLabel("")                # the beat's line, PRE-wrapped by the build's
        self.board_say.setProperty("mono", True)   # own wrapper -- what the FF9 window shows
        self.board_say.setAccessibleName("The say line at this beat")
        self.board_say.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        sv.addWidget(self.board_say)
        self.board_note = widgets.ElideLabel("")   # the honesty ledger's one-line face
        sv.addWidget(self.board_note)
        self.board_bar.hide()
        cl.addWidget(self.board_bar)
        self._vsplit = QSplitter(Qt.Orientation.Vertical)
        self._vsplit.setChildrenCollapsible(False)
        self._ladder_actions = {}                  # the flip wires move/edit/dup/delete here
        self.ladder = StepLadder(self.pal, actions=self._ladder_actions,
                                 on_select=self._on_step_select)
        lscroll = QScrollArea()
        lscroll.setWidgetResizable(True)
        lscroll.setWidget(self.ladder)             # h-bar as-needed: denied width must scroll,
        lscroll.setFrameShape(QFrame.Shape.NoFrame)   # never clip (the round-13 law)
        self._vsplit.addWidget(lscroll)
        self.canvas = CutsceneStage(self.pal, scale=self._scale)
        self._vsplit.addWidget(self.canvas)
        k = self._scale / 100
        self._vsplit.setSizes([int(320 * k), int(300 * k)])
        cl.addWidget(self._vsplit, 1)
        split.addWidget(center)
        split.setStretchFactor(1, 1)
        # under-budget on purpose: an over-budget request lets Qt starve the CENTER pane
        # (the behavior splitter's snap-measured lesson)
        split.setSizes([int(170 * k), int(530 * k)])
        self._hsplit = split
        outer.addWidget(split, 1)
        return page

    def _build_instruments(self):
        """The Problems/Staging column (docked into the shell inspector). The host scrolls and
        its h-bar is off, so everything here wraps or scrolls internally."""
        col = QWidget()
        v = QVBoxLayout(col)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(7)
        v.addWidget(widgets.role_label("PROBLEMS", "subtle"))
        self.problems_lbl = widgets.caption("")
        self.problems_lbl.setWordWrap(True)
        v.addWidget(self.problems_lbl)
        v.addWidget(widgets.role_label("STAGING", "subtle"))
        srow = QHBoxLayout()
        srow.setSpacing(8)
        self.stage_btn = QPushButton("Check the staging")
        self.stage_btn.setAccessibleName("Check that every cutscene walk can reach its target")
        self.stage_btn.setToolTip(
            "Walk every cast scene against the field's walkmesh — a blocked leg paints on "
            "the stage at the exact spot, with the build's own sentence. Walkmesh from the "
            "SAVED file; steps from the open document. After the first check, edits "
            "re-judge automatically on the warm mesh.")
        self.stage_btn.clicked.connect(lambda: self.stage_now())
        srow.addWidget(self.stage_btn)
        srow.addStretch(1)
        v.addLayout(srow)
        self.stage_note = widgets.caption("")
        self.stage_note.setWordWrap(True)
        v.addWidget(self.stage_note)
        self.stage_list = QListWidget()
        self.stage_list.setAccessibleName("Cutscene staging problems")
        self.stage_list.setVisible(False)
        v.addWidget(self.stage_list, 1)
        self.toml_btn = QPushButton("Open the .toml")
        self.toml_btn.setProperty("role", "quiet")
        self.toml_btn.setToolTip("Open this field's .toml in your editor — every key the "
                                 "forms don't reach is authorable there.")
        self.toml_btn.clicked.connect(self._open_toml)
        v.addWidget(self.toml_btn)
        v.addStretch(0)
        return col

    def _open_toml(self):
        if self.open_toml and self._member:
            self.open_toml(self._member)

    # -- shell hooks --
    def crumb_label(self):
        return f"Cutscene — {self._member}" if self._member else "Cutscene"

    def set_scale(self, pct):
        self._scale = pct
        if hasattr(self, "canvas"):
            self.canvas.set_scale(pct)
            self.board_slider.setMinimumWidth(int(120 * pct / 100))

    def retheme(self, pal):
        self.pal = pal
        if hasattr(self, "canvas"):
            self.canvas.retheme(pal)
            self.ladder.pal = pal
        if self._stack.currentWidget() is self._guide_page:
            self._show_guide(self._guide_state)    # rebuild: the glyph pixmap is palette-tinted
        elif self._raw is not None and self._member:
            self._render()

    # -- the feed (shell-pushed, in-memory, no file I/O) --
    def show_none(self):
        if self.board_btn.isChecked():
            self.board_btn.setChecked(False)
        self._member = self._path = self._raw = self._merged_fn = None
        self.problems_lbl.setText("")              # the docked column must not keep a dead
        widgets.set_state(self.problems_lbl, "")   # project's report
        self._reset_stage()
        self._show_guide("nofield")

    def show_field(self, member, raw, path=None, *, dirty=False, merged_fn=None):
        """Render the OPEN field's parsed dict — BY REFERENCE, the feed contract (the flip's
        ops mutate exactly the buffer the Editor and Save see). ``merged_fn`` re-merges the
        sibling scene.toml per call, so staging and the board see spatial truth."""
        same_field = member == self._member
        if not same_field and self.board_btn.isChecked():
            self.board_btn.setChecked(False)       # another field: the board is void
        self._member, self._raw, self._path = member, raw, path
        self._merged_fn, self._dirty = merged_fn, dirty
        if not cutscenescan.scene_rows(raw):
            if not same_field:
                self._reset_stage()
            self._show_guide("noscene")
            return
        if not same_field:
            self._scene = 0
            self._selected_step = None
            self._reset_stage()
        self._stack.setCurrentWidget(self._content)
        self._render(refit=not same_field)

    def _merged(self) -> dict:
        return self._merged_fn() if self._merged_fn else (self._raw or {})

    def _base_dir(self):
        return self._path.parent if self._path is not None else "."

    # -- render --
    def _render(self, *, refit=False):
        raw = self._merged()
        rows = cutscenescan.scene_rows(raw)
        if not rows:
            self._show_guide("noscene")
            return
        self._scene = max(0, min(self._scene, len(rows) - 1))
        self.head_title.setText(self._member or "Cutscene")
        n = len(rows)
        self.head_sum.setText(
            f"{n} scene{'s' if n != 1 else ''} — a story-event dispatch (at most one fires "
            f"per load)" if n > 1 else "1 scene")
        self.rail.blockSignals(True)
        self.rail.clear()
        for r in rows:
            kind = "narration" if r["narration"] else f"cast {len(r['cast'])}"
            text = (f"{r['label']} · {r['gate']} · {kind} · {r['steps']} "
                    f"step{'s' if r['steps'] != 1 else ''}")
            self.rail.addItem(text)
            it = self.rail.item(self.rail.count() - 1)
            tip = text + (("\ncast: " + ", ".join(r["cast"])) if r["cast"] else "")
            if not r["once"]:
                tip += "\nreplays every visit (once = false)"
            it.setToolTip(tip)
        self.rail.setCurrentRow(self._scene)
        self.rail.blockSignals(False)
        r = rows[self._scene]
        self.scene_title.setText(r["label"])
        self.scene_gate.setText(r["gate"] + (" · narration" if r["narration"] else
                                             " · cast: " + ", ".join(r["cast"])))
        lrows = cutscenescan.ladder_rows(raw, self._scene)
        if self._selected_step is not None and self._selected_step >= len(lrows):
            self._selected_step = None
        self.ladder.set_rows(lrows, selected=self._selected_step)
        self.canvas.set_selected_step(self._selected_step)
        self.canvas.set_scene(cutscenescan.stage_model(raw, self._scene), refit=refit)
        problems = cutscenescan.dispatch_problems(raw) + cutscenescan.scene_problems(raw)
        if problems:
            self.problems_lbl.setText("\n".join(f"• {p}" for p in problems))
            widgets.set_state(self.problems_lbl, "error")
        else:
            self.problems_lbl.setText("No structural problems.")
            widgets.set_state(self.problems_lbl, "")
        if self.board_btn.isChecked():
            self._refresh_board()

    def _on_scene_select(self, row):
        if row < 0 or row == self._scene:
            return
        self._scene = row
        self._selected_step = None
        self._render()
        if self._stage_armed and self._wmesh is not None:
            self._restage_timer.start()            # scene switch re-judges on the warm mesh

    def _on_step_select(self, i):
        self._selected_step = None if i == self._selected_step else i
        raw = self._merged()
        self.ladder.set_rows(cutscenescan.ladder_rows(raw, self._scene),
                             selected=self._selected_step)
        if self.board_btn.isChecked():
            self.ladder.set_beat_marks(self._beat_steps())
        self.canvas.set_selected_step(self._selected_step)

    # -- the storyboard strip --
    def _toggle_board(self, on):
        self.board_bar.setVisible(on)
        if on:
            self._refresh_board()
        else:
            self._board = None
            self.ladder.set_beat_marks(())
            self.canvas.set_storyboard(None)

    def _beat_pos(self):
        return self.board_slider.value()

    def _beat_steps(self):
        b = (self._board or {}).get("beats") or []
        k = max(0, min(self._beat_pos(), len(b) - 1))
        return set(b[k]["step_idxs"]) if b else set()

    def _refresh_board(self):
        """(Re)build the storyboard for the selected scene — pure dict work on the GUI
        thread (routing only when the staging mesh is already warm; the cold path draws
        straight legs and the ledger says so)."""
        self._board = cutscenescan.storyboard(self._merged(), self._base_dir(),
                                              self._wmesh, self._scene)
        beats = self._board.get("beats") or []
        err = self._board.get("error")
        self.board_slider.blockSignals(True)
        self.board_slider.setMaximum(max(0, len(beats) - 1))
        self.board_slider.setEnabled(bool(beats))
        self.board_slider.blockSignals(False)
        if err:
            self.board_say.setText(err)
            widgets.set_state(self.board_say, "error")
            self.board_pos.setText("")
            self.board_note.setFullText("the storyboard needs every name to resolve — "
                                        "fix the step above, or run Check")
            self.ladder.set_beat_marks(())
            self.canvas.set_storyboard(None)
            return
        widgets.set_state(self.board_say, "")
        notes = self._board.get("notes") or []
        self.board_note.setFullText("offline storyboard — beats, not seconds (hover for why)")
        self.board_note.setToolTip("\n".join(notes))
        self._show_beat(min(self._beat_pos(), max(0, len(beats) - 1)))

    def _on_board_scrub(self, v):
        if self._board is not None:
            self._show_beat(v)

    def _show_beat(self, k):
        beats = (self._board or {}).get("beats") or []
        if not beats:
            return
        k = max(0, min(int(k), len(beats) - 1))
        self.board_slider.blockSignals(True)
        self.board_slider.setValue(k)
        self.board_slider.blockSignals(False)
        b = beats[k]
        self.board_pos.setText(f"beat {k + 1} of {len(beats)}")
        if b["say"] is not None:
            ww = cutscenescan.wrap_width(self._merged())
            line = _dlg.wrap_preview(b["say"], ww) if ww is not None else b["say"]
            who = f"{b['say_actor']}:\n" if b["say_actor"] else ""
            self.board_say.setText(who + line)
        else:
            self.board_say.setText("(no line this beat)")
        self.ladder.set_beat_marks(set(b["step_idxs"]))
        self.canvas.set_storyboard(self._board, k)

    # -- the staging lane (the one disk read; the shell's old strip, moved home) --
    def stage_now(self, *, sync=False):
        raw = self._merged()
        if self._stage_busy or self._raw is None:
            return
        if not cutscenescan.has_cast_scene(raw):
            res = cutscenescan.StagingResult(
                scenes=len(cutscenescan.scene_rows(raw)))
            self._finish_stage((self._stage_gen, res, [], self._wmesh))
            return
        if self._wmesh is None and not self._path:
            self.stage_note.setText("This document has no saved file yet — the walkmesh "
                                    "comes from disk, so save first, then check.")
            widgets.set_state(self.stage_note, "warn")
            return
        self._stage_busy = True
        self.stage_btn.setEnabled(False)
        self.stage_btn.setText("Checking…")
        import copy as _copy
        snap = _copy.deepcopy(raw)                 # the worker must never race the GUI's dict
        gen, path, wmesh = self._stage_gen, self._path, self._wmesh
        flags = self.flag_names_fn() if self.flag_names_fn else None
        base = self._base_dir()
        if sync:                                   # the deterministic test/snap lane
            self._finish_stage((gen, *self._stage_work(path, snap, base, wmesh, flags)))
            return
        threading.Thread(target=self._stage_worker,
                         args=(gen, path, snap, base, wmesh, flags), daemon=True).start()

    @staticmethod
    def _stage_work(path, raw, base_dir, wmesh, flag_names):
        if wmesh is None:
            wmesh, err = cutscenescan.load_walkmesh(path, flag_names)
            if wmesh is None:
                res = cutscenescan.StagingResult()
                res.error = f"No walkmesh resolved — {err}"
                return res, [], None
        res = cutscenescan.check_staging(raw, base_dir, wmesh)
        rows = cutscenescan.stage_verdicts(raw, base_dir, wmesh)
        return res, rows, wmesh

    def _stage_worker(self, gen, path, raw, base_dir, wmesh, flags):
        payload = (gen, *self._stage_work(path, raw, base_dir, wmesh, flags))
        try:
            self._stage_done.emit(payload)         # RuntimeError-guarded: the doc may be dead
        except RuntimeError:
            pass

    def _finish_stage(self, payload):
        gen, res, rows, wmesh = payload
        if gen != self._stage_gen:
            return                                 # a stale field's verdicts never paint
        self._stage_busy = False
        self.stage_btn.setEnabled(True)
        self.stage_btn.setText("Check the staging")
        if wmesh is not None:
            self._wmesh = wmesh
            self._stage_armed = True
        self.stage_note.setText(res.summary())
        widgets.set_state(self.stage_note,
                          "warn" if (res.warnings or res.skipped or res.error) else "")
        self.stage_list.clear()
        for w in res.warnings:
            self.stage_list.addItem(f"⚠ {w}")
        for lbl, why in res.skipped:
            self.stage_list.addItem(f"? {lbl} not checked — {why}")
        self.stage_list.setVisible(self.stage_list.count() > 0)
        self.canvas.set_verdicts(rows)
        if self.board_btn.isChecked():
            self._refresh_board()                  # the warm mesh upgrades straight legs to routes

    def _restage(self):
        if self._stage_busy:
            self._restage_timer.start()            # let the in-flight run land first
            return
        self.stage_now()

    def _reset_stage(self):
        """Field switch / project close: another field's mesh or verdicts must not linger."""
        self._stage_gen += 1
        self._restage_timer.stop()
        self._wmesh = None
        self._stage_armed = False
        self._stage_busy = False
        self.stage_btn.setEnabled(True)
        self.stage_btn.setText("Check the staging")
        self.stage_note.setText("")
        widgets.set_state(self.stage_note, "")
        self.stage_list.clear()
        self.stage_list.setVisible(False)
        if hasattr(self, "canvas"):
            self.canvas.set_verdicts([])
