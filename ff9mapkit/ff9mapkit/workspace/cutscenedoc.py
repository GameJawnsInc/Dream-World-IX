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

from PySide6.QtCore import QEvent, Qt, Signal, QTimer
from PySide6.QtGui import QBrush, QColor, QFontMetrics, QPen
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QPlainTextEdit, QPushButton, QScrollArea, QSlider, QSplitter, QStackedLayout, QStyle,
    QStyledItemDelegate, QStyleOptionViewItem, QVBoxLayout, QWidget,
)

from .. import dialogue as _dlg
from ..editor import forms
from . import cutscenescan, forms_qt, icons, widgets
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
        self._fit_zoom = None                      # the zoom the last fit chose

    # -- the re-fit on a pane change (backdrop.BackdropCanvas's rule: only until the author zooms)
    def _fit(self):
        super()._fit()
        self._fit_zoom = self._zoom

    def resizeEvent(self, ev):                     # noqa: N802 (Qt override)
        """The split or the storyboard strip changed the stage's size: re-fit while the stage
        still shows the zoom a fit chose. A zoom the author chose (any other) is never reset."""
        super().resizeEvent(ev)
        # the zoom pill sat on the routed leg and a name in a short stage: there it gives way
        self._hint.setVisible(self.viewport().height() >= 6 * self._hint.height())
        if (self._zoom == self._fit_zoom and not self._fit_pending
                and not self._scene.sceneRect().isEmpty()):
            self._fit()

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

    def reveal_verdict(self, v):
        """Bring one verdict's stall point (and its label above/right of it) into view from its
        own DOCUMENT point: scrolls only when needed, never zooms -- the author's zoom stays."""
        sx, sy = self._pt(*v["b"])
        self.ensureVisible(sx, sy, 1, 1, 140, 60)

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


# Every step key the EDITOR owns -- authoritative on Apply (absent = pop, so a cleared speaker
# really clears). Anything else riding a step (dim / window_pos / box / ...) is PRESERVED by
# cutscenescan.update_step -- the old form's extras rule, with the editor owning more keys.
# The text-pacing family here is the message-box vocabulary the compiler ALREADY reads off a
# say/open step (build.py routes the step dict through content.text.dress_window verbatim).
STEP_EDITOR_KEYS = ("actor", "with_prev", "speaker", "tail", "style", "window",
                    "speed", "instant", "duration", "hold", "signal")


class StepEditor(QFrame):
    """The inline step editor (the BranchEditor idiom): kind-swapped value widgets with the
    live wrap preview, the cast combo, ``with_prev``, and the kind-aware extras drawer — the
    pacing/window vocabulary (speaker/tail/style/window/[SPED]/[IMME]/[TIME]/hold/signal) the
    compiler already accepts on a text step and no GUI could write. Apply hands the parsed
    step to the host; nothing here touches the raw dict."""

    def __init__(self, pal, *, on_apply, on_close, pick_anim=None, on_pick_stage=None,
                 wrap_width_fn=None):
        super().__init__()
        self.setProperty("role", "card")
        self.pal = pal
        self.on_apply = on_apply
        self.on_close = on_close
        self.pick_anim = pick_anim                 # (current_text) -> picked | None
        self.on_pick_stage = on_pick_stage         # (on) arm/disarm a one-shot canvas click
        self.scene = None                          # the open (scene, step) target; insert_at
        self.step_i = None                         # not None = ADD mode (insert at that row)
        self.insert_at = None
        self._signal_true = False                  # the opened step said signal = true
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(8)
        self.title = widgets.role_label("Step", "cardtitle")
        head.addWidget(self.title)
        head.addStretch(1)
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setToolTip("Write this step into the open document (Ctrl+Z undoes).")
        self.apply_btn.clicked.connect(lambda: self.on_apply())
        head.addWidget(self.apply_btn)
        self.close_btn = close_btn = QPushButton("Close")
        close_btn.setProperty("role", "quiet")
        close_btn.clicked.connect(lambda: self.on_close())
        head.addWidget(close_btn)
        hw = QWidget()
        hw.setLayout(head)
        v.addWidget(hw)
        # What the editor has to SAY (a refusal, an Apply error) goes right under the header:
        # the panel is taller than the ladder pane at every text size and the pane keeps its TOP
        # in view, so a note at the bottom was written where nobody could see it (final review).
        self.note = widgets.caption("")
        self.note.setWordWrap(True)
        self.note.hide()                           # no words, no room
        v.addWidget(self.note)
        v.addWidget(QLabel("Type:"))
        self.kind = QComboBox()
        self.kind.setAccessibleName("Cutscene step type")
        for k in forms.STEP_KIND:
            self.kind.addItem(forms.STEP_LABEL.get(k, k), k)
        self.kind.currentIndexChanged.connect(self._on_kind)
        v.addWidget(self.kind)
        self.value_label = QLabel("Value:")        # a valueless step (raise / face_player) hides it
        v.addWidget(self.value_label)
        vrow = QHBoxLayout()
        vrow.setContentsMargins(0, 0, 0, 0)
        self.value_line = QLineEdit()
        self.value_line.setAccessibleName("Cutscene step value")
        vrow.addWidget(self.value_line, 1)
        self.anim_browse = QPushButton("Browse…")  # gesture names are RIG-scoped; nobody memorizes
        self.anim_browse.setAccessibleName("Browse animations this actor's model can play")
        self.anim_browse.setToolTip("Preview the clips this step's actor can play and pick one.")
        self.anim_browse.clicked.connect(self._browse_anim)
        vrow.addWidget(self.anim_browse)
        self.pick_btn = QPushButton("Pick on the stage")
        self.pick_btn.setProperty("role", "quiet")
        self.pick_btn.setAccessibleName("Pick this movement target by clicking the stage")
        self.pick_btn.setToolTip("Click a point on the stage below — it lands here as x, z. "
                                 "Press again to cancel.")
        self.pick_btn.setCheckable(True)           # checked = armed: the next stage press is taken
        self.pick_btn.clicked.connect(lambda on: self.on_pick_stage and self.on_pick_stage(on))
        vrow.addWidget(self.pick_btn)
        v.addLayout(vrow)
        self.value_text = QPlainTextEdit()
        self.value_text.setAccessibleName("Cutscene step dialogue")
        self.value_text.setTabChangesFocus(True)
        fm = QFontMetrics(self.value_text.font())
        self.value_text.setMinimumHeight(fm.lineSpacing() * 5)   # the old 64px box held ~3 lines
        self.value_text.setMaximumHeight(fm.lineSpacing() * 9)   # of text that spans [PAGE]s
        self.value_text.setToolTip('Multi-line: press Enter for a line break ("\\n" also works). '
                                   "Use [PAGE] for a new window.")
        v.addWidget(self.value_text)
        self.say_preview = forms_qt._wrap_preview_panel(   # what the BUILD emits, not the raw text
            self.value_text, self._preview_text, wrap_width_fn or (lambda: None))
        for box in self.say_preview.findChildren(QPlainTextEdit):   # read-only: a name, no tab stop
            box.setAccessibleName("In-game wrap preview")
            box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        v.addWidget(self.say_preview)
        self.hint = widgets.caption("")
        v.addWidget(self.hint)
        v.addWidget(QLabel("Actor:"))
        self.actor = QComboBox()
        self.actor.setEditable(True)               # the cast completes; free text stays legal
        self.actor.setAccessibleName("Cutscene step actor")
        self.actor.lineEdit().setPlaceholderText("blank = sole cast member / narration voice")
        v.addWidget(self.actor)
        self.with_prev = QCheckBox("Runs together with the previous step")
        self.with_prev.setAccessibleName("Cutscene step runs together with the previous step")
        v.addWidget(self.with_prev)
        # the kind-aware extras drawer -- text steps get the whole window/pacing family,
        # movement steps just the walk speed; everything blank = absent = byte-identical output
        self.extras = widgets.disclosure("Line & pacing extras")
        ex = self.extras.content_layout
        self._extra_rows = {}

        def _erow(key, label, widget, tip):
            lab = QLabel(label)
            widget.setAccessibleName(f"Cutscene step {key}")
            widget.setToolTip(tip)
            ex.addWidget(lab)
            ex.addWidget(widget)
            self._extra_rows[key] = (lab, widget)
            return widget

        self.x_speaker = _erow("speaker", "Speaker name:", QLineEdit(),
                               "optional name before the line, e.g. Vivi (or [VIVI])")
        self.x_speaker.textChanged.connect(self.say_preview.refresh)   # the name line re-wraps
        self.x_tail = _erow("tail", "Window tail:", QLineEdit(),
                            "speech-bubble pointer corner (UPR/UPL/LOR/LOC/…); blank = default")
        self.x_style = _erow("style", "Window style:", QLineEdit(),
                             "plain / notail / transparent / caption / a raw flags byte")
        self.x_window = _erow("window", "Window id (0-7):", QLineEdit(),
                              "which window slot — two ids keep two windows on screen at once")
        self.x_speed = _erow("speed", "Speed:", QLineEdit(),
                             "text step: typewriter speed ([SPED=n]) · walk/route: units per frame")
        self.x_instant = _erow("instant", "", QCheckBox("Pop fully drawn ([IMME])"),
                               "no typewriter — the selector/system-window convention")
        self.x_duration = _erow("duration", "Auto-close after (frames):", QLineEdit(),
                                "[TIME=n]: the window closes itself; the player can't dismiss it "
                                "early. 0 re-grants dismissal.")
        self.x_hold = _erow("hold", "", QCheckBox("Hold until a script closes it ([TIME=-1])"),
                            "undismissable, no auto-close — the unison shape (close it with a "
                            "'Close a window' step)")
        self.x_signal = _erow("signal", "Signal when typed (+, a number, or blank):", QLineEdit(),
                              'fire the text signal as the line finishes typing: "+" adds one '
                              "to it, a number sets it, blank sends none — pair with "
                              "'Wait for text signal'")
        v.addWidget(self.extras)

    def tab_chain(self):
        """The editor's keyboard order: what the step IS first, then Apply and Close (built first,
        in the header, they used to come before every field). Hidden ones are skipped by Qt."""
        return [self.kind, self.value_line, self.anim_browse, self.pick_btn, self.value_text,
                self.actor, self.with_prev, self.extras.toggle_button,
                *(w for _lab, w in self._extra_rows.values()), self.apply_btn, self.close_btn]

    def say(self, text=""):
        """The editor's one line of words: shown while it has any, gone (no gap) when it has not."""
        self.note.setText(text)
        self.note.setVisible(bool(text))

    # -- kind plumbing --
    def current_kind(self):
        return self.kind.currentData()

    def _is_text(self):
        return self.current_kind() in forms.TEXT_STEPS

    def _typed_text(self):
        """The dialogue as the step will hold it: a typed backslash-n is a line break."""
        return self.value_text.toPlainText().replace("\\n", "\n")

    def _preview_text(self):
        text = self._typed_text()
        if not text:
            return ""
        sp = self.x_speaker.text().strip() if hasattr(self, "x_speaker") else ""
        return cutscenescan.say_as_built(sp, text)

    def _on_kind(self, _i=0):
        k = self.current_kind()
        if self.pick_btn.isChecked() and self.on_pick_stage:
            self.on_pick_stage(False)              # a new kind / a newly opened step: the armed
        #                                            pick belonged to the old one
        self.hint.setText(forms.STEP_HELP.get(k, ""))
        text = self._is_text()
        valueless = forms.STEP_KIND.get(k) == forms.BOOL
        # carry the typed value across the swap (the old form's courtesy)
        if text and self.value_line.text() and not self.value_text.toPlainText():
            self.value_text.setPlainText(self.value_line.text())
        elif not text and self.value_text.toPlainText() and not self.value_line.text():
            self.value_line.setText(self.value_text.toPlainText().replace("\n", "\\n"))
        self.value_text.setVisible(text)
        self.say_preview.setVisible(text)
        self.value_line.setVisible(not text and not valueless)
        self.value_label.setVisible(not valueless)
        self.anim_browse.setVisible(k == "animation")
        self.pick_btn.setVisible(k in ("walk", "teleport") and self.on_pick_stage is not None)
        self._sync_with_prev()
        # the drawer: text steps get the window/pacing family; movement gets walk speed only
        movement = k in ("walk", "path")
        for key, (lab, w) in self._extra_rows.items():
            show = text if key != "speed" else (text or movement)
            lab.setVisible(show and bool(lab.text()))
            w.setVisible(show)
        self._extra_rows["speed"][0].setText(
            "Typewriter speed ([SPED=n]):" if text else "Walk speed (units/frame):")
        self.extras.setVisible(text or movement)

    def _sync_with_prev(self):
        k = self.current_kind()
        row = self.insert_at if self.insert_at is not None else (self.step_i or 0)
        ok = k in forms.PARALLEL_STEPS and (row or 0) > 0
        self.with_prev.setEnabled(ok)
        if not ok:
            self.with_prev.setChecked(False)
        self.with_prev.setToolTip(
            "Run this step alongside the one above it (both finish before the next)."
            if ok else
            ("Step 0 has nothing to run with." if (row or 0) == 0 else
             f"Only {', '.join(forms.PARALLEL_STEPS)} can run in parallel."))

    def _browse_anim(self):
        if self.pick_anim:
            val = self.pick_anim(self.actor.currentText().strip(), self.value_line.text())
            if val:
                self.value_line.setText(val)

    # -- open / read --
    def open_step(self, scene, step_i, step, cast, *, insert_at=None):
        """Load a step (edit mode) or a fresh default (add mode, ``insert_at`` = landing row)."""
        self.scene, self.step_i, self.insert_at = scene, step_i, insert_at
        step = step or {}
        k = forms.step_key(step) or "say"
        idx = list(forms.STEP_KIND).index(k) if k in forms.STEP_KIND else 0
        self.kind.setCurrentIndex(idx)
        val = forms.step_value_text(step)
        if k in forms.TEXT_STEPS:
            self.value_text.setPlainText(step.get(k, ""))
            self.value_line.clear()
        else:
            self.value_line.setText(val)
            self.value_text.clear()
        self.actor.blockSignals(True)
        self.actor.clear()
        self.actor.addItems(list(cast))
        self.actor.setEditText(step.get("actor", ""))
        self.actor.blockSignals(False)
        self.with_prev.setChecked(bool(step.get("with_prev")))
        for key in ("speaker", "tail", "style"):
            getattr(self, f"x_{key}").setText(str(step.get(key, "") or ""))
        for key in ("window", "speed", "duration", "signal"):
            v = step.get(key)
            # signal = true means exactly what "+" means to the build ([INCS]): show it as "+"
            getattr(self, f"x_{key}").setText("" if v is None else "+" if v is True else str(v))
        self._signal_true = step.get("signal") is True   # read_step gives true back, unchanged
        self.x_instant.setChecked(bool(step.get("instant")))
        self.x_hold.setChecked(bool(step.get("hold")))
        self.title.setText(f"Step {step_i} — edit" if insert_at is None
                           else f"New step — lands at row {insert_at}")
        self.say("")
        widgets.set_state(self.note, "")
        self._on_kind()
        # NO self.show() here: on the FIRST edit the editor is still PARENTLESS, and showing a
        # parentless widget makes it a top-level OS window for the instant before set_inset
        # reparents it (playtest-caught flicker -- the phantom-window law, entry side). Only
        # set_inset shows, AFTER seating.

    def typed_state(self) -> dict:
        """What the author can SEE and type, as one comparable value: the kind, the visible
        value box, the actor, and the extras. The dirty test compares two of these, so a step
        opens clean whatever keys it holds that the editor cannot write back."""
        return {"kind": self.kind.currentIndex(),
                "value": (self.value_text.toPlainText() if self._is_text()
                          else self.value_line.text()),
                "actor": self.actor.currentText(), "with_prev": self.with_prev.isChecked(),
                "instant": self.x_instant.isChecked(), "hold": self.x_hold.isChecked(),
                **{k: getattr(self, f"x_{k}").text() for k in
                   ("speaker", "tail", "style", "window", "speed", "duration", "signal")}}

    def read_step(self) -> dict:
        """The step the widgets describe. Raises ValueError with the field named."""
        k = self.current_kind()
        raw = self._typed_text() if self._is_text() else self.value_line.text()
        step = forms.make_step(k, raw)
        a = self.actor.currentText().strip()
        if a:
            step["actor"] = a
        if self.with_prev.isEnabled() and self.with_prev.isChecked():
            step["with_prev"] = True
        text, movement = self._is_text(), k in ("walk", "path")
        if text:
            for key in ("speaker", "tail", "style"):
                s = getattr(self, f"x_{key}").text().strip()
                if s:
                    # an all-digit style is the raw flags BYTE: content.text.resolve_style reads
                    # a string as a style NAME, so "128" must go back as the int 128
                    step[key] = (int(s) if key == "style" and s.isdecimal() and s.isascii()
                                 else s)
            for key in ("window", "speed", "duration", "signal"):
                s = getattr(self, f"x_{key}").text().strip()
                if key == "signal" and s == "+":
                    step[key] = True if self._signal_true else "+"
                    continue
                if s:
                    try:
                        step[key] = int(s)
                    except ValueError:
                        raise ValueError(
                            f'signal must be "+", a whole number, or blank (got {s!r})'
                            if key == "signal" else f"{key} must be a whole number (got {s!r})")
            if self.x_instant.isChecked():
                step["instant"] = True
            if self.x_hold.isChecked():
                step["hold"] = True
        elif movement:
            s = self.x_speed.text().strip()
            if s:
                try:
                    step["speed"] = int(s)
                except ValueError:
                    raise ValueError(f"speed must be a whole number (got {s!r})")
        return step


class _StepRow(QFrame):
    """One ladder card. A QFrame with the card role (widgets.card's shape) plus a click-to-
    select seam — selection drives the stage's accented leg (and, at the flip, the editor).
    A row is a keyboard stop too: Up / Down select the row above / below, Enter edits it."""

    def __init__(self, on_click=None, on_key=None):
        super().__init__()
        self.setObjectName("cutsceneStep")         # the selected / focused rules are scoped to it
        self.setProperty("role", "card")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._on_click = on_click
        self._on_key = on_key

    def mousePressEvent(self, event):              # noqa: N802 (Qt override)
        if self._on_click:
            self._on_click()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):                # noqa: N802 (Qt override)
        key = {Qt.Key.Key_Up: "up", Qt.Key.Key_Down: "down", Qt.Key.Key_Return: "enter",
               Qt.Key.Key_Enter: "enter"}.get(event.key())
        if key and self._on_key and not event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier:
            self._on_key(key)
            event.accept()
            return
        super().keyPressEvent(event)


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
        self._rows = []                            # the row frames, in step order
        self._follow = None                        # the row a rebuild hands the keyboard focus to
        self._inset = None                         # THE ACCORDION: one foreign panel unfolded
        #                                            inside the ladder (the step editor under its
        #                                            row / the settings above row 0). The ladder
        #                                            HOSTS it, never owns it -- see set_inset.
        self.setAccessibleName("Cutscene steps")

    # -- the accordion seam (playtest feedback: separate bands cluttered the column) --
    def set_inset(self, widget, at=0):
        """Unfold ONE host-owned panel inside the ladder at layout index ``at`` (row *i*'s
        editor sits at ``i + 1``; the settings card at ``0``). The host re-insets after every
        ``set_rows`` -- the ladder LIFTS the inset there instead of deleting it, because the
        panel (the one StepEditor instance) must outlive every refill."""
        self._lift_inset()
        self._inset = widget
        self._lay.insertWidget(max(0, min(at, self._lay.count() - 1)), widget)
        widget.show()

    def _lift_inset(self):
        """Take the inset OUT without killing it. Hide FIRST, then reparent: a visible widget
        reparented to None is a top-level OS window for an instant (the phantom-window law)."""
        if self._inset is not None:
            self._inset.hide()
            self._inset.setParent(None)
            self._inset = None

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

    def _focused(self):
        """``(tool, step)`` of the row tool or row that holds the keyboard focus, or None."""
        fw = QApplication.focusWidget()
        for i, row in enumerate(self._rows):
            if fw is row:
                return ("row", i)
            if fw is not None and row.isAncestorOf(fw) and fw.property("tool"):
                return (fw.property("tool"), i)
        return None

    def _on_row_key(self, i, key):
        if key == "enter":
            if self.actions:
                self.actions["edit"](i)
            return
        j = i + (1 if key == "down" else -1)
        if 0 <= j < len(self._rows) and self.on_select:
            self._follow = j                       # the rebuild puts the focus on the new row
            if j != self._selected:
                self.on_select(j)
            else:
                self._refocus(("row", j))

    def _refocus(self, had):
        """Give the focus back after a rebuild: the same tool on the step's row (the host may have
        named another row in ``_follow``), or the row itself when that tool is disabled there."""
        tool, i = had
        if self._follow is not None:
            i, self._follow = self._follow, None
        if not self._rows:
            return
        row = self._rows[max(0, min(i, len(self._rows) - 1))]
        row.show()                                 # added rows show on a queued call: now
        target = next((b for b in row.findChildren(QPushButton)
                       if b.property("tool") == tool and b.isEnabled()), row)
        target.setFocus(Qt.FocusReason.OtherFocusReason)

    def set_rows(self, rows, selected=None):
        had = self._focused()                      # a rebuild destroys the focused tool: find it first
        self._selected = selected
        self._idx_chips = []
        self._rows = []
        self._lift_inset()                         # the accordion panel is LIFTED, never deleted
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
            frame = self._row(row, len(rows))
            self._rows.append(frame)
            self._lay.addWidget(frame)
        if had is not None:
            self._refocus(had)
        self._follow = None
        if not rows:
            self._lay.addWidget(widgets.caption(
                "No steps yet — a cutscene is an ordered list of steps: say a line, walk an "
                "actor, wait, open/close windows, set a flag."))
        self._lay.addStretch(1)

    def _row(self, row, n):
        i = row["idx"]
        frame = _StepRow(on_click=(lambda i=i: self.on_select(i)) if self.on_select else None,
                         on_key=lambda key, i=i: self._on_row_key(i, key))
        frame.setProperty("selected", i == self._selected)   # the visible selection (C24): a
        #                                                       rule, so the storyboard's beat
        #                                                       marks on the chip cannot hide it
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
                    ("pencil", "Edit this step (click again to fold)",
                     lambda _=False, s=i: self.actions["edit"](s)),
                    ("⧉", "Duplicate this step", lambda _=False, s=i: self.actions["dup"](s)),
                    ("✕", "Remove this step (Ctrl+Z undoes)",
                     lambda _=False, s=i: self.actions["delete"](s))):
                if glyph == "pencil":              # SVG, never U+270E (the pixelly-fallback law)
                    btn = QPushButton()
                    btn.setIcon(icons.icon("pencil", self.pal["text"]))
                else:
                    btn = QPushButton(glyph)
                btn.setProperty("role", "rowtool")
                btn.setProperty("tool", glyph)     # a rebuild gives the focus back by this
                btn.setToolTip(tip)
                btn.setAccessibleName(f"{tip} — step {i}")
                # nothing to move past: the first row's up and the last row's down are no stop
                btn.setEnabled(not (glyph == "↑" and i == 0 or glyph == "↓" and i == n - 1))
                btn.clicked.connect(cb)
                h.addWidget(btn)
        if row["actor"]:
            chip = widgets.role_label(row["actor"], "chip")
            chip.setProperty("mono", True)
            h.addWidget(chip)
        if row["speaker"]:                         # who TALKS, in the actor's slot: the body face,
            spk = widgets.role_label(               # not the actor's mono, and "as" beside an actor
                ("as " if row["actor"] else "") + row["speaker"], "chip")
            spk.setToolTip(f"The name shown on this line: {row['speaker']}")
            h.addWidget(spk)
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
        if row["extras"]:                          # a quiet note of what else the step sets,
            ex = widgets.caption(", ".join(row["extras"]))   # not a chip that reads like a button
            ex.setToolTip("Also set on this step: " + ", ".join(row["extras"])
                          + " (open the step to see them)")
            h.addWidget(ex)
        frame.setAccessibleName(
            f"step {i}: " + (f"{row['actor']} " if row["actor"] else "") + row["verb"]
            + (f" as {row['speaker']}" if row["speaker"] else "")
            + (" runs together with the previous step" if row["with_prev"] else ""))
        return frame


class _WrapHintDelegate(QStyledItemDelegate):
    """A word-wrapped row's height, measured at the width the row's text is PAINTED at. The
    stock hint wraps at the whole row width while the sheet's item padding and rail narrow the
    painted text, so a long sentence lost its last line to an ellipsis."""

    def sizeHint(self, option, index):             # noqa: N802 (Qt override)
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        w = opt.widget
        st = w.style() if w is not None else QApplication.style()
        inset = opt.rect.width() - st.subElementRect(
            QStyle.SubElement.SE_ItemViewItemText, opt, w).width()
        if 0 < inset < opt.rect.width():
            opt.rect.setWidth(opt.rect.width() - inset)
        return super().sizeHint(opt, index)


class CutsceneDoc(QWidget):
    """The Cutscene tab. The shell feeds it the OPEN field's parsed dict (``show_field``) on
    tab show / tree select — never a file read; the doc's ONE disk touch is the staging
    check's walkmesh (user-invoked, then warm for re-judges — the two-truths split, stated
    on the button)."""

    _stage_done = Signal(object)                   # (gen, StagingResult, verdict_rows, wmesh|None)

    def __init__(self, pal, *, scale=100, on_edit=None, flag_names_fn=None,
                 pick_anim=None, open_toml=None, pick=None):
        super().__init__()
        self.pal = pal
        self._scale = scale
        self.on_edit = on_edit                     # (member, label) -> the shell's checkpoint hook
        self.flag_names_fn = flag_names_fn         # the campaign's [[flag]] table for the mesh load
        self.pick_anim = pick_anim                 # (member, actor, cast, current) -> anim | None
        self.open_toml = open_toml                 # (member) -> open the file in the OS editor
        self.pick = pick                           # the catalog Browse seam for the settings form
        self._member = None
        self._path = None
        self._raw = None
        self._merged_fn = None                     # the scene.toml split: markers/positions can
        #                                            live in the sibling file; STAGING and the
        #                                            board must see the MERGED doc
        self._dirty = False
        self._scene = 0                            # the rail's selected scene (0-based, lint's own)
        self._selected_step = None
        self._ed_block = None                      # the open editor's scene dict and step dict:
        self._ed_step = None                       # found by IDENTITY at Apply, never by index
        self._ed_typed = None                      # the editor's widgets as loaded (the dirty test)
        self._board = None                         # the storyboard model (when the strip is on)
        self._guide_state = "nofield"
        self._wmesh = None                         # the staging lane's cached walkmesh (per field)
        self._last_stage = None                    # the last StagingResult (tests/snaps read it)
        self._verdicts = []                        # EVERY scene's verdict rows; the stage paints
        #                                            only the selected scene's (_paint_verdicts)
        self._stage_busy = False
        self._stage_armed = False                  # first EXPLICIT check arms auto re-judges
        self._stage_explicit = False               # the run in flight is the button's, not a re-judge
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
    def _build_guide(self, state, note=""):
        glyph = icons.pixmap("play", self.pal["muted"], 46)
        if state == "noscene":
            return widgets.empty_state(
                "", "This field has no [[cutscene]] scene",
                teach=(note + "\n\n" if note else "") + "A cutscene is an ordered list of steps that runs with control locked: "
                      "say lines, walks, animations, windows, flags. A CAST (actors = "
                      "[names]) stages NPCs and the player; no cast = narration. Repeat "
                      "[[cutscene]] blocks — each gated to its own story beat — for the "
                      "per-field dispatch (at most one fires per load).",
                actions=[("Add a scene", self._add_scene)],
                icon_pixmap=glyph)
        return widgets.empty_state(                # "nofield" -- the front door
            "", "Cutscene stages a field's [[cutscene]] scenes",
            teach="Open a campaign or a loose field and select a field in the tree — its "
                  "scenes, steps, staging, and the storyboard render here.",
            icon_pixmap=glyph)

    def _show_guide(self, state, note=""):
        self._guide_state = state
        old = self._guide_page
        self._guide_page = self._build_guide(state, note)
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
        # no sideways scroll: a list that scrolls never elides, and cut a row mid-glyph over a
        # permanent scrollbar; elided, the row's tooltip carries the whole line
        self.rail.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.rail.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.rail.currentRowChanged.connect(self._on_scene_select)
        rv.addWidget(self.rail, 1)
        self.add_scene_btn = QPushButton("＋ Add scene…")
        self.add_scene_btn.setProperty("role", "quiet")
        self.add_scene_btn.setToolTip("Append a scene to the dispatch (a runnable narration "
                                      "mint — give it a cast and a gate in Settings).")
        self.add_scene_btn.clicked.connect(self._add_scene)
        rv.addWidget(self.add_scene_btn)
        split.addWidget(rail_col)
        # center: the scene bar OUTSIDE the scroll, then ladder over stage
        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(4)
        # the scene bar: title + gate LEAD, the five scene buttons TAIL. A SpillRow, because one
        # non-wrapping row floored the whole window (828px at 150% -> 1290 with a field open);
        # the buttons drop to a second line only when the column cannot hold both.
        lead = QWidget()
        lh = QHBoxLayout(lead)
        lh.setContentsMargins(0, 0, 0, 0)
        lh.setSpacing(10)
        self.scene_title = widgets.role_label("—", "cardtitle")
        lh.addWidget(self.scene_title)
        self.scene_gate = widgets.ElideLabel("", min_ch=8)
        lh.addWidget(self.scene_gate, 1)
        tail = QWidget()
        bh = QHBoxLayout(tail)
        bh.setContentsMargins(0, 0, 0, 0)
        bh.setSpacing(10)
        self.add_step_btn = widgets.ElideButton("＋ Step")
        self.add_step_btn.setProperty("role", "quiet")
        self.add_step_btn.setToolTip("Insert a step after the selected row (at the end when "
                                     "nothing is selected).")
        self.add_step_btn.clicked.connect(self._add_step)
        bh.addWidget(self.add_step_btn)
        self.settings_btn = widgets.ElideButton("Settings")
        self.settings_btn.setIcon(icons.icon("pencil", self.pal["text"]))   # SVG, never U+270E
        self.settings_btn.setProperty("role", "quiet")
        self.settings_btn.setCheckable(True)
        self.settings_btn.setToolTip("The scene's cast, gates, and story writes — every "
                                     "[[cutscene]] block key the forms own.")
        self.settings_btn.toggled.connect(self._toggle_settings)
        bh.addWidget(self.settings_btn)
        self.dup_scene_btn = widgets.ElideButton("⧉ Scene")
        self.dup_scene_btn.setProperty("role", "quiet")
        self.dup_scene_btn.setToolTip("Duplicate this scene (mind the gate — two scenes with "
                                      "the same gate are a build error, and PROBLEMS says so).")
        self.dup_scene_btn.clicked.connect(self._dup_scene)
        bh.addWidget(self.dup_scene_btn)
        self.del_scene_btn = widgets.ElideButton("− Scene")
        self.del_scene_btn.setProperty("role", "quiet")
        self.del_scene_btn.setToolTip("Delete THIS scene only (Ctrl+Z undoes; the file changes "
                                      "on Save, not now).")
        self.del_scene_btn.clicked.connect(self._del_scene)
        bh.addWidget(self.del_scene_btn)
        self.board_btn = widgets.ElideButton("▶ Storyboard")
        self.board_btn.setProperty("role", "quiet")
        self.board_btn.setCheckable(True)
        self.board_btn.setToolTip(
            "Step through the scene one MOMENT at a time (the steps that run together) — "
            "positions chain the way the compiler chains "
            "them, the say line shows with its final in-game wrapping.\n"
            "No clock, on purpose: a say waits for the player, so seconds would be fiction.")
        self.board_btn.toggled.connect(self._toggle_board)
        bh.addWidget(self.board_btn)
        self.scene_bar = widgets.SpillRow(lead, tail)
        cl.addWidget(self.scene_bar)
        # the scene-settings card -- THE ACCORDION (playtest feedback: a separate band per
        # panel cluttered the column): it unfolds INSIDE the ladder above row 0, mutually
        # exclusive with the step editor, and scrolls WITH the ladder (one scrollbar). Built
        # here, parentless until _sync_insets seats it. Apply-committed (a per-keystroke
        # checkpoint would spam undo).
        self.settings_card = widgets.card()
        sc_lay = QVBoxLayout(self.settings_card)
        sc_lay.setContentsMargins(10, 8, 10, 8)
        sc_lay.setSpacing(6)
        sc_head = QHBoxLayout()
        sc_head.addWidget(widgets.role_label("Scene settings", "cardtitle"))
        sc_head.addStretch(1)
        self.settings_apply = QPushButton("Apply")
        self.settings_apply.setToolTip("Write these settings into the open document "
                                       "(Ctrl+Z undoes).")
        self.settings_apply.clicked.connect(self._apply_settings)
        sc_head.addWidget(self.settings_apply)
        schw = QWidget()
        schw.setLayout(sc_head)
        sc_lay.addWidget(schw)
        self._settings_host = QVBoxLayout()
        self._settings_host.setContentsMargins(0, 0, 0, 0)
        sc_lay.addLayout(self._settings_host)
        self.settings_note = widgets.caption("")
        self.settings_note.setWordWrap(True)
        sc_lay.addWidget(self.settings_note)
        self._settings_getters = None
        self._settings_built = None                # _settings_key() of the form on show
        self.settings_card.hide()
        # the storyboard strip (hidden until ▶ Storyboard)
        self.board_bar = QWidget()
        sv = QVBoxLayout(self.board_bar)
        sv.setContentsMargins(10, 0, 10, 0)
        sv.setSpacing(2)
        srow = QHBoxLayout()
        srow.setSpacing(8)
        for glyph, d, name in (("◀", -1, "Previous moment"), ("▶", +1, "Next moment")):
            b = QPushButton(glyph)                 # text glyphs, the rowtool family's idiom --
            b.setProperty("role", "quiet")         # NOT U+23xx media glyphs (the emoji-face law)
            b.setToolTip(name)
            b.setAccessibleName(name)
            b.clicked.connect(lambda _=False, k=d: self._show_beat(self._beat_pos() + k))
            srow.addWidget(b)
        self.board_slider = QSlider(Qt.Orientation.Horizontal)
        self.board_slider.setAccessibleName("Storyboard moment")   # a slider is a real Tab stop
        self.board_slider.setToolTip("Scrub the scene's moments")
        self.board_slider.valueChanged.connect(self._on_board_scrub)
        self.board_slider.setMinimumWidth(int(120 * self._scale / 100))   # never a sliver
        srow.addWidget(self.board_slider, 1)
        self.board_pos = widgets.role_label("", "caption")
        self.board_pos.setProperty("mono", True)
        srow.addWidget(self.board_pos)
        sv.addLayout(srow)
        self.board_say = QLabel("")                # the beat's line, PRE-wrapped by the build's
        self.board_say.setProperty("mono", True)   # own wrapper -- what the FF9 window shows
        self.board_say.setAccessibleName("The say line at this moment")
        self.board_say.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        sv.addWidget(self.board_say)
        self.board_note = widgets.ElideLabel("")   # the honesty ledger's one-line face
        sv.addWidget(self.board_note)
        self.board_bar.hide()
        cl.addWidget(self.board_bar)
        self._vsplit = QSplitter(Qt.Orientation.Vertical)
        self._vsplit.setChildrenCollapsible(False)
        self._ladder_actions = {"move": self._move_step, "edit": self._edit_step,
                                "dup": self._dup_step, "delete": self._del_step}
        self.ladder = StepLadder(self.pal, actions=self._ladder_actions,
                                 on_select=self._on_step_select)
        self._lscroll = QScrollArea()
        self._lscroll.setWidgetResizable(True)
        self._lscroll.setWidget(self.ladder)       # h-bar as-needed: denied width must scroll,
        self._lscroll.setFrameShape(QFrame.Shape.NoFrame)   # never clip (the round-13 law)
        self._vsplit.addWidget(self._lscroll)
        # the step editor is the ladder's OTHER accordion panel: it unfolds under its row and
        # scrolls with the list, so the conversation stays visible around the line being
        # written. Parentless until _sync_insets seats it.
        self.editor = StepEditor(
            self.pal, on_apply=self._apply_step, on_close=self._close_editor,
            pick_anim=self._pick_anim_for_step, on_pick_stage=self._arm_stage_pick,
            wrap_width_fn=lambda: cutscenescan.wrap_width(self._merged()))
        self.editor.hide()
        self.canvas = CutsceneStage(self.pal, scale=self._scale,
                                    on_move=self._on_stage_move,
                                    on_insert=self._on_stage_insert,
                                    on_delete=self._on_stage_delete)
        self._vsplit.addWidget(self.canvas)
        k = self._scale / 100
        self._vsplit.setSizes([int(340 * k), int(280 * k)])
        # _balance_split owns this split from here: the ladder pane takes its content up to half
        # while the author has not dragged the handle (splitterMoved fires only on a drag).
        self._split_chosen = False
        self._vsplit.splitterMoved.connect(self._split_dragged)
        self._balance_timer = QTimer(self)         # a resize re-balances AFTER the splitter laid
        self._balance_timer.setSingleShot(True)    # itself out (a filter runs before it does)
        self._balance_timer.setInterval(0)
        self._balance_timer.timeout.connect(self._balance_split)
        self._vsplit.installEventFilter(self)
        cl.addWidget(self._vsplit, 1)
        split.addWidget(center)
        split.setStretchFactor(1, 1)
        # under-budget on purpose: an over-budget request lets Qt starve the CENTER pane
        # (the behavior splitter's snap-measured lesson). 200, not the behavior rail's 170:
        # a scene row carries its GATE ("plays at beat 100") and the snap showed it eliding.
        split.setSizes([int(200 * k), int(500 * k)])
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
        # The two buttons ELIDE: a QPushButton's floor is its whole label, and the docked column
        # took that floor wider than the Inspector at 150% ("Check the stagi", cut at the edge).
        # Their floor is set in _yield_buttons, re-derived from the text-size dial.
        self.stage_btn = widgets.ElideButton("")
        self._stage_label("Check the staging")
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
        self.stage_list.setToolTip("Click a problem to select its step and show it on the stage.")
        # the docked inspector is narrow: the build's sentence WRAPS (a sideways-scrolling list
        # showed a stub of it), and a row is a door to its step and its spot on the stage
        self.stage_list.setWordWrap(True)
        self.stage_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.stage_list.setResizeMode(QListWidget.ResizeMode.Adjust)   # re-wrap when docked
        self.stage_list.setItemDelegate(_WrapHintDelegate(self.stage_list))
        self.stage_list.itemClicked.connect(self._on_stage_item)
        self.stage_list.itemActivated.connect(self._on_stage_item)   # Enter: the keyboard's click
        self.stage_list.setVisible(False)
        v.addWidget(self.stage_list, 1)
        self.toml_btn = widgets.ElideButton("Open the .toml")
        self.toml_btn.setProperty("role", "quiet")
        self.toml_btn.setToolTip("Open this field's .toml in your editor — every key the "
                                 "forms don't reach is authorable there.")
        self.toml_btn.clicked.connect(self._open_toml)
        v.addWidget(self.toml_btn)
        v.addStretch(0)
        self._yield_buttons()
        return col

    def _yield_buttons(self):
        """The instruments' buttons may shrink (eliding) to a floor that scales with the dial;
        the column then fits whatever width the Inspector gives it."""
        for b in (self.stage_btn, self.toml_btn):
            b.setMinimumWidth(int(72 * self._scale / 100))

    def _stage_label(self, text):
        """Relabel the staging button. ElideButton names itself after its label; this button's
        name says what it checks."""
        self.stage_btn.setText(text)
        self.stage_btn.setAccessibleName("Check that every cutscene walk can reach its target")

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
            self._balance_split()                  # the floors are in dial units
        self._yield_buttons()

    def retheme(self, pal):
        self.pal = pal
        if hasattr(self, "canvas"):
            self.canvas.retheme(pal)
            self.ladder.pal = pal
            self.settings_btn.setIcon(icons.icon("pencil", pal["text"]))
            # (the ladder rows' pencil re-tints on the _render below -- rows rebuild)
        if self._stack.currentWidget() is self._guide_page:
            self._show_guide(self._guide_state)    # rebuild: the glyph pixmap is palette-tinted
        elif self._raw is not None and self._member:
            self._render()

    # -- the feed (shell-pushed, in-memory, no file I/O) --
    def show_none(self):
        if self.board_btn.isChecked():
            self.board_btn.setChecked(False)
        if self.settings_btn.isChecked():
            self.settings_btn.setChecked(False)
        self._close_editor()
        self._member = self._path = self._raw = self._merged_fn = None
        self.problems_lbl.setText("")              # the docked column must not keep a dead
        widgets.set_state(self.problems_lbl, "")   # project's report
        self._reset_stage()
        self._show_guide("nofield")

    def show_field(self, member, raw, path=None, *, dirty=False, merged_fn=None):
        """Render the OPEN field's parsed dict — BY REFERENCE, the feed contract (the flip's
        ops mutate exactly the buffer the Editor and Save see). ``merged_fn`` re-merges the
        sibling scene.toml per call, so staging and the board see spatial truth.
        "Same field" is the member AND its file: a copied field or a re-imported fork keeps the
        name, and must not inherit the other file's warm walkmesh or verdict."""
        same_field = member == self._member and path == self._path
        if not same_field:
            if self.board_btn.isChecked():
                self.board_btn.setChecked(False)   # another field: the board is void
            if self.settings_btn.isChecked():
                self.settings_btn.setChecked(False)
            self._close_editor()
        elif self.editor.scene is not None:
            # the same field re-fed (undo / redo / reload swap the buffer; the Editor tree edits
            # it in place): the editor follows its own scene and step, or closes if they are gone
            if raw is not self._raw:
                self._rebind_editor(raw)
            loc = self._editor_locate(raw) if self.editor.scene is not None else None
            if loc is None:
                self._close_editor()
            else:
                self._scene, self.editor.scene = loc[0], loc[0]
                if loc[1] is not None:
                    self.editor.step_i = self._selected_step = loc[1]
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
        if same_field and self._stage_armed and self._wmesh is not None:
            self._restage_timer.start()            # undo / redo / another tab's edit re-judge too

    def follow_history(self, member, path, data):
        """Undo / Redo is about to feed ``data`` in place of the buffer this doc shows: select
        the scene the history step touched -- the one it put back (an undone delete, a redone
        add or copy), the one before the one it took away (an undone add or copy, a redone
        delete), or the one whose content it changed. Found from the two buffers themselves, and
        only when they are the same field (member AND file); a field the doc is not showing keeps
        its own selection rules."""
        if self._raw is None or member != self._member or path != self._path:
            return
        old, new = cutscenescan._blocks(self._raw), cutscenescan._blocks(data)
        n = min(len(old), len(new))
        first = next((i for i in range(n) if old[i] != new[i]), n)
        if len(new) == len(old) and first == n:
            return                                 # no scene changed: keep the selection
        k = first if len(new) >= len(old) else first - 1
        k = max(0, min(k, len(new) - 1))
        if k != self._scene:
            self._scene, self._selected_step = k, None

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
            steps = f"{r['steps']} step{'s' if r['steps'] != 1 else ''}"
            # What tells scenes apart FIRST and SHORT, on two lines that each elide right: the
            # rail has room for about 13 characters a line at 125%, and the gate's sentence
            # ("plays at beat 100") lost its number there. The header and the tooltip keep it.
            text = f"#{r['idx']} · {r['gate'].removeprefix('plays at ')}\n{steps} · {kind}"
            self.rail.addItem(text)
            it = self.rail.item(self.rail.count() - 1)
            tip = (f"{r['label']} · {steps}\n{kind} · {r['gate']}"
                   + (("\ncast: " + ", ".join(r["cast"])) if r["cast"] else ""))
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
        handles = self._stage_handles()
        self.canvas.set_edit(bool(handles))
        self.canvas.set_selected_step(self._selected_step)
        self._paint_verdicts()                     # a scene switch re-filters the rows
        self.canvas.set_scene(cutscenescan.stage_model(raw, self._scene), refit=refit,
                              handles=handles)
        if self.settings_btn.isChecked() and self._settings_key() != self._settings_built:
            self._fill_settings()                  # isChecked, not isVisible (a never-shown test
        #                                            window lies). Only when what the form shows
        #                                            really changed: a rebuild throws away typing.
        self._sync_insets()
        self._balance_timer.start()                # the ladder's content just changed; its
        #                                            new rows count once they are shown (queued)
        problems = cutscenescan.dispatch_problems(raw) + cutscenescan.scene_problems(
            raw, self.flag_names_fn() if self.flag_names_fn else None)
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
        if self._editor_refuses():                 # the rail must not show a scene it did not open
            self.rail.blockSignals(True)
            self.rail.setCurrentRow(self._scene)
            self.rail.blockSignals(False)
            return
        self._close_editor()                       # the editor's (scene, step) target is stale
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
        self._sync_insets()                        # set_rows lifted the accordion panel
        handles = self._stage_handles()
        self.canvas.set_edit(bool(handles))
        self.canvas.set_selected_step(self._selected_step)
        self.canvas.set_scene(cutscenescan.stage_model(raw, self._scene), handles=handles)

    def _sync_insets(self):
        """Seat THE accordion panel after any ladder refill: the settings card above row 0, or
        the open step editor under its row (add mode: AT the landing row, so the panel follows
        the typing point as Apply advances). At most one -- the modes are exclusive."""
        # "open" is the TARGET state (scene set by open_step, cleared by _close_editor) --
        # never visibility: the lift itself hides, and a never-shown test window lies anyway.
        if self.settings_btn.isChecked():
            self.ladder.set_inset(self.settings_card, at=0)
        elif self.editor.scene is not None:
            at = ((self.editor.step_i + 1) if self.editor.insert_at is None
                  else self.editor.insert_at)
            self.ladder.set_inset(self.editor, at=at)
        self._chain_tabs()

    def _chain_tabs(self):
        """Rebuilt rows join the window's focus chain LAST (after the toolbar, Deploy and the
        Inspector). Put them back in reading order: the scene bar, each row and its tools (the open
        step editor under its row), then the stage."""
        seq = [self.board_btn]
        lay = self.ladder._lay
        for n in range(lay.count()):
            w = lay.itemAt(n).widget()
            if isinstance(w, _StepRow):
                seq += [w] + [b for b in w.findChildren(QPushButton) if b.property("tool")]
            elif w is self.editor:
                seq += self.editor.tab_chain()
        seq.append(self.canvas)
        for a, b in zip(seq, seq[1:]):
            QWidget.setTabOrder(a, b)

    # -- edits (all through cutscenescan's pure ops; the shell checkpoints via on_edit) --
    def _after_edit(self, label):
        """One committed mutation of the open dict: re-render, then hand the shell its undo
        step. The doc renders FIRST so a standalone (shell-less) host still shows the edit."""
        if not cutscenescan.scene_rows(self._raw or {}):
            self._show_guide("noscene")            # the last scene was deleted
        else:
            if self._stack.currentWidget() is self._guide_page:
                self._stack.setCurrentWidget(self._content)   # a first scene on a bare field
            self._render()
        if self.on_edit and self._member:
            self.on_edit(self._member, label)
        if self._stage_busy:
            self._stage_moved = True               # a check in flight judged the OLD scenes: its rows
        #                                            must not paint (see _finish_stage)
        if self._stage_armed and self._wmesh is not None:
            self._restage_timer.start()            # the armed lane: re-judge on the warm mesh

    def _editor_dirty(self):
        """Would closing the step editor throw away the author's typing? Judged only from what
        the author can see. Add mode: a value in the visible value box. Edit mode: the editor's
        widgets differ from what they showed when the step was loaded (``_ed_typed``, re-taken
        at Apply and when a stage drag rewrites the value) -- so a step opens clean whatever
        keys it holds that the editor normalises, and an unreadable value typed in is typing."""
        ed = self.editor
        if ed.scene is None:
            return False
        if ed.insert_at is not None:
            return bool(ed.typed_state()["value"])
        return ed.typed_state() != self._ed_typed

    def _editor_refuses(self):
        """Refuse a gesture that would close (or reload) a DIRTY step editor, and say how to go
        on. A clean editor closes as before; nothing is ever applied on the author's behalf."""
        if not self._editor_dirty():
            return False
        self.editor.say("This step has changes that are not applied. Apply them, or "
                                 "Close to drop them, then try again.")
        widgets.set_state(self.editor.note, "error")
        self._reveal_editor()
        return True

    def _add_scene(self):
        if self._raw is None or self._editor_refuses():
            return
        self._close_editor()                       # the selection moves to the new scene
        label = cutscenescan.add_scene(self._raw)
        self._scene = len(cutscenescan.scene_rows(self._raw)) - 1
        self._selected_step = None
        self._after_edit(label)

    def _dup_scene(self):
        if self._raw is None or self._editor_refuses():
            return
        self._close_editor()                       # the selection moves to the copy
        label = cutscenescan.duplicate_scene(self._raw, self._scene)
        self._scene += 1
        self._after_edit(label)

    def _del_scene(self):
        if self._raw is None or self._editor_refuses():
            return
        self._close_editor()
        k, n = self._scene, len(self._steps())
        label = cutscenescan.delete_scene(self._raw, self._scene)
        self._scene = max(0, self._scene - 1)
        self._selected_step = None
        self._after_edit(label)
        # no confirm (undo-first, as the step delete): say what went and how to get it back, where
        # the author is looking -- the next render puts the summary back
        said = f"Deleted scene #{k} ({n} step{'s' if n != 1 else ''}) — Ctrl+Z restores it."
        if self._stack.currentWidget() is self._guide_page:
            self._show_guide("noscene", said)      # that was the last scene
        else:
            self.head_sum.setText(said)

    # -- scene settings (Apply-committed: a per-keystroke checkpoint would spam undo) --
    def _toggle_settings(self, on):
        if on:
            self._close_editor()                   # the accordion holds ONE panel at a time
            self._fill_settings()                  # (NO show here -- the card may be parentless,
        else:                                      # and only set_inset shows, AFTER seating:
            self.settings_card.hide()              # the phantom-window flicker's other half)
        if self._raw is not None and self._stack.currentWidget() is self._content:
            self._render()                         # seat / clear the inset

    def _settings_key(self):
        """What the settings form is built FROM: the scene and the values the form shows (not
        the steps -- a stage drag must not wipe a typed gate). Another field never reaches this
        comparison: show_field closes the card on a field switch (member AND path)."""
        blocks = forms.all_blocks((self._raw or {}).get("cutscene"))
        if not 0 <= self._scene < len(blocks):
            return None
        # the COUNT too: Apply writes by index, and a scene added or removed elsewhere can put a
        # twin with equal values (Duplicate Scene makes them) at this index (final review).
        # Scenes have no id of their own, so a change that KEEPS the count -- a hand-edited
        # .toml reloaded with one scene removed and another added -- is not seen here.
        return (self._scene, len(blocks),
                forms.entity_to_values(forms.CUTSCENE_SPEC, blocks[self._scene]))

    def _fill_settings(self):
        self._settings_built = self._settings_key()
        while self._settings_host.count():
            w = self._settings_host.takeAt(0).widget()
            if w is not None:
                w.hide()                           # hide-first teardown (the phantom-window law)
                w.setParent(None)
                w.deleteLater()
        blocks = forms.all_blocks((self._raw or {}).get("cutscene"))
        if not (0 <= self._scene < len(blocks)):
            self._settings_getters = None
            return
        form, getters = forms_qt.build_form(
            forms.CUTSCENE_SPEC,
            forms.entity_to_values(forms.CUTSCENE_SPEC, blocks[self._scene]),
            self.pal, pick=self.pick, wrap_width=None)
        self._settings_host.addWidget(form)
        self._settings_getters = getters
        self.settings_note.setText("")
        widgets.set_state(self.settings_note, "")

    def _apply_settings(self):
        if self._settings_getters is None or self._raw is None:
            return
        try:
            entity = forms.build_entity(forms.CUTSCENE_SPEC,
                                        forms_qt.read(self._settings_getters))
        except ValueError as e:
            self.settings_note.setText(str(e))
            widgets.set_state(self.settings_note, "error")
            return
        managed = tuple(f.key for f in forms.CUTSCENE_SPEC)
        self._after_edit(cutscenescan.apply_scene_settings(self._raw, self._scene,
                                                           entity, managed))

    # -- step edits --
    def _cast(self):
        blocks = forms.all_blocks((self._raw or {}).get("cutscene"))
        b = blocks[self._scene] if 0 <= self._scene < len(blocks) else {}
        return [str(a) for a in b["actors"]] if isinstance(b.get("actors"), list) else []

    def _block_now(self):
        blocks = forms.all_blocks((self._raw or {}).get("cutscene"))
        return blocks[self._scene] if 0 <= self._scene < len(blocks) else None

    def _steps(self):
        b = self._block_now() or {}
        return b.get("steps") if isinstance(b.get("steps"), list) else []

    def _edit_step(self, i):
        st = self._steps()
        if not 0 <= i < len(st):
            return
        if (self.editor.scene is not None and self.editor.insert_at is None
                and self.editor.step_i == i):
            self._close_editor()                   # reclicking the open row's Edit FOLDS it
            self._render()
            return
        if self._editor_refuses():                 # another row's pencil would load over it
            return
        if self.settings_btn.isChecked():
            self.settings_btn.setChecked(False)    # the accordion holds ONE panel at a time
        self._selected_step = i
        self.editor.open_step(self._scene, i, st[i], self._cast())
        self._ed_block, self._ed_step = self._block_now(), st[i]
        self._ed_typed = self.editor.typed_state()
        self._render()                             # seats the editor under its row
        self._balance_split(opened=True)
        self._reveal_editor()

    def _add_step(self):
        if self._raw is None or self._editor_refuses():
            return
        if self.settings_btn.isChecked():
            self.settings_btn.setChecked(False)
        at = (self._selected_step + 1) if self._selected_step is not None else len(self._steps())
        self.editor.open_step(self._scene, None, {"say": ""}, self._cast(), insert_at=at)
        self._ed_block, self._ed_step = self._block_now(), None
        self._sync_insets()                        # no data changed -- just seat the panel
        self._balance_split(opened=True)
        self._reveal_editor()

    def _split_dragged(self, *_):
        self._split_chosen = True                  # the author's split is a choice: keep it

    def eventFilter(self, obj, ev):                # noqa: N802 (Qt override)
        if obj is self._vsplit and ev.type() == QEvent.Type.Resize and not self._split_chosen:
            self._balance_timer.start()
        return super().eventFilter(obj, ev)

    def _balance_split(self, *, board=False, opened=False):
        """THE one owner of the ladder / stage split. Until the author drags the handle, the
        ladder pane takes its content's height, up to half -- a short scene leaves no dead pane
        and the stage gets the rest. While a panel is open the split is left alone, except that
        opening the step editor still gets a usable ladder (the old guard: up to 300 px at 100%,
        the stage keeps 140). The storyboard's
        toggle keeps the stage at least 200 px at 100% (or half), even under a dragged split."""
        s = self._vsplit.sizes()
        total = sum(s)
        if len(s) != 2 or total <= 0:
            return                                 # not laid out yet: the resize will come back
        k = self._scale / 100
        if self.settings_btn.isChecked() or self.editor.scene is not None:
            if not opened:
                return                             # a panel's split is set when it opens, only
            need = int(300 * k)                    # the panel's guard, as it always was
            ladder = s[0] if s[0] >= need else total - max(140, total - need)
        else:
            floor = min(int(200 * k), total // 2)
            if self._split_chosen:
                ladder = s[0]
                if not board:
                    floor = 0                      # a dragged stage keeps its size
            else:
                content = self.ladder.sizeHint().height() + 2 * self._lscroll.frameWidth()
                ladder = min(content, total // 2)
            ladder = max(0, min(ladder, total - floor))
        if ladder != s[0]:
            self._vsplit.setSizes([ladder, total - ladder])

    def _reveal_editor(self):
        """Bring the editor into view TOP FIRST, with the row above it (the line being edited, or
        the one an add lands after): Apply/Close and the conversation. A panel taller than the
        viewport is never centred -- that scrolled its header and its row away. Otherwise the
        least scroll that shows the whole panel. Deferred: the rows were just rebuilt, and their
        geometry exists only once the layout has run."""
        QTimer.singleShot(0, self._scroll_to_editor)

    def _scroll_to_editor(self):
        lay = self.ladder._lay
        idx = lay.indexOf(self.editor)
        if self.editor.scene is None or idx < 0:
            return                                 # closed (or moved off) before the layout ran
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.Type.LayoutRequest)   # a first seat's rows
        above = lay.itemAt(idx - 1).widget() if idx > 0 else None
        top = (above if above is not None else self.editor).y() - 8
        bottom = self.editor.geometry().bottom() + 8
        sb = self._lscroll.verticalScrollBar()
        vh = self._lscroll.viewport().height()
        lo, hi = bottom - vh, max(0, top)
        sb.setValue(hi if lo > hi else max(lo, min(sb.value(), hi)))
        if self.editor.note.isVisible():           # in a pane too short for the row above, the
            self._lscroll.ensureWidgetVisible(self.editor.note, 0, 4)   # header AND the words:
                                                   # the words win (Apply sits right above them)

    def _close_editor(self):
        self.editor.hide()                         # hidden takes no space; the next refill lifts it
        self.editor.scene = self.editor.step_i = self.editor.insert_at = None
        self._ed_block = self._ed_step = None
        self._disarm_stage_pick()

    def _editor_locate(self, raw):
        """``(scene, step)`` indices of the open editor's scene dict and step dict in ``raw``,
        found by IDENTITY (ADD mode: ``(scene, None)``), or None when either is gone. An index
        is only where a row sits NOW -- an in-place writer shifts it under the editor."""
        blocks = forms.all_blocks((raw or {}).get("cutscene"))
        k = next((n for n, b in enumerate(blocks) if b is self._ed_block), None)
        if k is None or self.editor.insert_at is not None:
            return None if k is None else (k, None)
        st = blocks[k].get("steps") if isinstance(blocks[k].get("steps"), list) else []
        i = next((n for n, s in enumerate(st) if s is self._ed_step), None)
        return None if i is None else (k, i)

    def _rebind_editor(self, raw):
        """A NEW buffer (undo / redo / reload) holds copies, so identity is lost and the editor's
        scene must be re-found by its contents. ITS OWN INDEX FIRST, and under both rules: the
        scene there is still equal to the one it opened on, or (edit mode) its row still holds an
        equal step. Only when its own index fails both may it move, and then only to the ONE
        other scene equal to it -- with duplicated scenes about ("Duplicate scene" makes them
        routine), "some equal scene" used to carry the editor into a scene the author never
        opened, and Apply wrote their line there. Otherwise unbind: the caller closes."""
        blocks = forms.all_blocks((raw or {}).get("cutscene"))
        k0, i = self.editor.scene, self.editor.step_i
        add = self.editor.insert_at is not None

        def own(n):
            if not 0 <= n < len(blocks):
                return False
            if blocks[n] == self._ed_block:
                return True
            st = blocks[n].get("steps") if isinstance(blocks[n].get("steps"), list) else []
            return (not add) and 0 <= i < len(st) and st[i] == self._ed_step

        k = k0 if own(k0) else None
        if k is None:
            equal = [n for n in range(len(blocks)) if n != k0 and blocks[n] == self._ed_block]
            k = equal[0] if len(equal) == 1 else None
        if k is None:
            self._ed_block = self._ed_step = None
            return
        self._ed_block = blocks[k]
        if not add:
            self._ed_step = self._ed_block["steps"][i]

    def _apply_step(self):
        if self._raw is None:
            return
        try:
            step = self.editor.read_step()
        except ValueError as e:
            self.editor.say(str(e))
            widgets.set_state(self.editor.note, "error")
            self._reveal_editor()
            return
        loc = self._editor_locate(self._raw)
        if loc is None:                            # its scene or its step is gone (an edit elsewhere)
            self.editor.say("This step is no longer in the scene (it was removed "
                                     "elsewhere) — Close, then open the step again.")
            widgets.set_state(self.editor.note, "error")
            self._reveal_editor()
            return
        k = self.editor.scene = loc[0]
        if loc[1] is not None:
            self.editor.step_i = loc[1]
        self.editor.say("")
        widgets.set_state(self.editor.note, "")
        self._disarm_stage_pick()                  # Apply ends the pick (it would steal a drag)
        if self.editor.insert_at is not None:      # ADD: insert, then ADVANCE -- the next Apply
            at = min(self.editor.insert_at,        # lands the NEXT line. The conversation loop
                     len(self._ed_block.get("steps") or []))   # (clamped: rows may have gone)
            label = cutscenescan.add_step(self._raw, k, at, step)   # the old form's
            self.editor.insert_at = at + 1         # same-kind overwrite made impossible.
            self.editor._sync_with_prev()          # a new row: with_prev is judged by row too
            self.editor.title.setText(f"New step — lands at row {self.editor.insert_at}")
            self._selected_step = at
            self.editor.value_text.clear()         # both: a value carried across a kind
            self.editor.value_line.clear()         # switch must not linger in the hidden box
            self._after_edit(label)
            self._reveal_editor()                  # the panel just advanced a row -- keep it in view
        else:
            i = self.editor.step_i
            label = cutscenescan.update_step(self._raw, k, i, step,
                                             managed=STEP_EDITOR_KEYS)
            self._ed_step = self._ed_block["steps"][i]     # update_step wrote a NEW dict there
            self._ed_typed = self.editor.typed_state()     # what is shown is now applied
            self._selected_step = i
            self._after_edit(label)

    def _move_step(self, i, delta):
        st = self._steps()
        j = i + (1 if delta > 0 else -1)
        if not (0 <= i < len(st)) or not (0 <= j < len(st)):
            return                                 # the boundary: nothing to move past
        if self._editor_refuses():
            return
        self._close_editor()                       # indices shift under a structural edit
        label = cutscenescan.move_step(self._raw, self._scene, i, delta)
        if self._selected_step == i:
            self._selected_step = j
        self.ladder._follow = j                    # the keyboard stays on the moved step
        self._after_edit(label)

    def _dup_step(self, i):
        if not 0 <= i < len(self._steps()) or self._editor_refuses():
            return
        self._close_editor()
        label = cutscenescan.duplicate_step(self._raw, self._scene, i)
        self._selected_step = i + 1
        self.ladder._follow = i + 1                # ...on the copy
        self._after_edit(label)

    def _del_step(self, i):
        if not 0 <= i < len(self._steps()) or self._editor_refuses():
            return
        self._close_editor()
        label = cutscenescan.remove_step(self._raw, self._scene, i)
        if self._selected_step is not None and self._selected_step >= len(self._steps()):
            self._selected_step = None
        self._after_edit(label)

    # -- the stage as an INPUT device --
    def _pick_anim_for_step(self, actor, current):
        if self.pick_anim and self._member:
            return self.pick_anim(self._member, actor, self._cast(), current)
        return None

    def _arm_stage_pick(self, on=True):
        """The pick button's toggle. Armed SHOWS: the button stays pressed and the stage wears a
        crosshair, because the next left press on the stage is taken (not a drag, not a pan)."""
        if not on:
            self._disarm_stage_pick()
            return
        self.canvas.on_sim_click = self._stage_picked
        self.canvas.set_sim_mode(True)             # the base canvas's one-click input lane
        self.canvas.viewport().setCursor(Qt.CursorShape.CrossCursor)

    def _disarm_stage_pick(self):
        self.editor.pick_btn.setChecked(False)
        if self.canvas.on_sim_click is not None:
            self.canvas.on_sim_click = None
            self.canvas.set_sim_mode(False)
            self.canvas.viewport().setCursor(Qt.CursorShape.OpenHandCursor)   # the pan's own

    def _stage_picked(self, x, z):
        self._disarm_stage_pick()
        self.editor.value_line.setText(f"{int(round(x))}, {int(round(z))}")

    def _stage_handles(self):
        """The SELECTED movement step's target as a draggable handle (a path: one per point) —
        the ``stage_handles`` row schema, so the inherited drag machinery works unchanged.
        Dragging a NAMED target rewrites it to the literal coordinate; the op's label says so."""
        i = self._selected_step
        if i is None or self._raw is None:
            return None
        model = cutscenescan.stage_model(self._merged(), self._scene)
        leg = next((leg for leg in model["legs"] if leg["step"] == i), None)
        if leg is None:
            return None
        k = self._scene
        if leg["kind"] == "path":
            return [{"id": ("path_pt", k, i, j), "x": p[0], "z": p[1], "kind": "target",
                     "label": f"step {i} path point {j}", "list_id": ("path_pt", k, i, j)}
                    for j, p in enumerate(leg["points"][1:])]
        return [{"id": ("target", k, i), "x": leg["points"][-1][0], "z": leg["points"][-1][1],
                 "kind": "target", "label": f"step {i} {leg['kind']} target", "list_id": None}]

    def _say_problem(self, text):
        self.problems_lbl.setText(text)
        widgets.set_state(self.problems_lbl, "warn")

    def _on_stage_move(self, hid, x, z):
        if self._raw is None:
            return
        if hid[0] == "target":
            _kind, k, i = hid
            label = cutscenescan.set_step_target(self._raw, k, i, x, z)
        else:
            _kind, k, i, j = hid
            label = cutscenescan.set_step_target(self._raw, k, i, x, z, waypoint=j)
        self._show_dragged_value(k, i)
        self._after_edit(label)

    def _show_dragged_value(self, k, i):
        """A stage edit of the OPEN step lands in the editor's value too -- else its next
        Apply writes the old target back over the drag."""
        if (self.editor.scene is not None and self._editor_locate(self._raw) == (k, i)
                and self.editor.current_kind() == forms.step_key(self._ed_step)):
            self.editor.value_line.setText(forms.step_value_text(self._ed_step))
            if self._ed_typed is not None:         # the drag is applied: not the author's typing
                self._ed_typed["value"] = self.editor.value_line.text()

    def _on_stage_insert(self, lid):
        _kind, k, i, j = lid
        try:
            label = cutscenescan.insert_path_point(self._raw, k, i, j)
        except ValueError as e:                    # a NAMED point: refuse and say why
            self._say_problem(str(e))
            return
        self._show_dragged_value(k, i)
        self._after_edit(label)

    def _on_stage_delete(self, lid):
        _kind, k, i, j = lid
        try:
            label = cutscenescan.delete_path_point(self._raw, k, i, j)
        except ValueError as e:                    # the 1-point floor: refuse and say why
            self._say_problem(str(e))
            return
        self._show_dragged_value(k, i)
        self._after_edit(label)

    # -- the storyboard strip --
    def _toggle_board(self, on):
        self.board_bar.setVisible(on)
        if on:                                     # the strip takes its height from this split:
            self._vsplit.parentWidget().layout().activate()   # lay it out now, then keep the
            self._balance_split(board=True)        # stage its floor (the stage re-fits itself)
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
            self._board_text(err)
            widgets.set_state(self.board_say, "error")
            self.board_pos.setText("")
            self.board_note.setFullText("the storyboard needs every name to resolve — "
                                        "fix the step above, or run the toolbar Check")
            self.ladder.set_beat_marks(())
            self.canvas.set_storyboard(None)
            return
        widgets.set_state(self.board_say, "")
        notes = self._board.get("notes") or []
        self.board_note.setFullText("offline storyboard — moments, not seconds (hover for why)")
        self.board_note.setToolTip("\n".join(notes))
        if not beats:                              # every step deleted: nothing of the old board
            self._board_text("No steps yet — add one to storyboard this scene.", placeholder=True)
            self.board_pos.setText("")
            self.ladder.set_beat_marks(())
            self.canvas.set_storyboard(None)
            return
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
        self.board_pos.setText(f"moment {k + 1} of {len(beats)}")
        if b["say"] is not None:
            ww = cutscenescan.wrap_width(self._merged())
            line = cutscenescan.say_as_built(b["say_speaker"], b["say"])   # the build's line
            self._board_text(_dlg.wrap_preview(line, ww) if ww is not None else line)
        else:
            self._board_text("(no line at this moment)", placeholder=True)
        self.ladder.set_beat_marks(set(b["step_idxs"]))
        self.canvas.set_storyboard(self._board, k)

    def _board_text(self, text, *, placeholder=False):
        """The strip's line: the game window's mono for a real line (or the error), a quiet
        caption for a placeholder -- an empty state must not out-shout the scene title."""
        self.board_say.setProperty("role", "caption" if placeholder else None)
        self.board_say.setProperty("mono", not placeholder)
        widgets.repolish(self.board_say)
        self.board_say.setText(text)

    # -- the staging lane (the one disk read; the shell's old strip, moved home) --
    def stage_now(self, *, sync=False, warm=False):
        """Check the staging. An explicit check (the button) reads the walkmesh from the SAVED
        file every time, as its tooltip promises -- a regenerate or re-export may have replaced
        it. Only the automatic re-judge (``warm=True``) rides the cached mesh."""
        raw = self._merged()
        if self._stage_busy or self._raw is None:
            return
        self._stage_explicit = not warm            # only the author's own check moves the view
        if not cutscenescan.has_cast_scene(raw):
            res = cutscenescan.StagingResult(
                scenes=len(cutscenescan.scene_rows(raw)))
            self._finish_stage((self._stage_gen, res, [], self._wmesh))
            return
        wmesh = self._wmesh if warm else None
        if wmesh is None and not self._path:
            self.stage_note.setText("This document has no saved file yet — the walkmesh "
                                    "comes from disk, so save first, then check.")
            widgets.set_state(self.stage_note, "warn")
            return
        self._stage_busy = True
        self._stage_moved = False
        self.stage_btn.setEnabled(False)
        self._stage_label("Checking…")
        import copy as _copy
        snap = _copy.deepcopy(raw)                 # the worker must never race the GUI's dict
        gen, path = self._stage_gen, self._path
        flags = self.flag_names_fn() if self.flag_names_fn else None
        base = self._base_dir()
        if sync:                                   # the deterministic test/snap lane
            self._finish_stage((gen, *self._stage_work(path, snap, base, wmesh, flags)))
            return
        threading.Thread(target=self._stage_worker,
                         args=(gen, path, snap, base, wmesh, flags), daemon=True).start()

    @staticmethod
    def _stage_work(path, raw, base_dir, wmesh, flag_names):
        # NEVER raises: an exception out of the worker used to strand the old form's button
        # disabled and reading "Checking…" forever -- _finish_stage is the only re-enable.
        try:
            if wmesh is None:
                wmesh, err = cutscenescan.load_walkmesh(path, flag_names)
                if wmesh is None:
                    res = cutscenescan.StagingResult()
                    res.error = f"No walkmesh resolved — {err}"
                    return res, [], None
            res = cutscenescan.check_staging(raw, base_dir, wmesh)
            rows = cutscenescan.stage_verdicts(raw, base_dir, wmesh)
            return res, rows, wmesh
        except Exception as e:                     # noqa: BLE001 -- the message is the teaching
            res = cutscenescan.StagingResult()
            res.error = f"Could not check the staging — {e}"
            return res, [], wmesh                  # None only when no floor was loaded

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
        self._last_stage = res                     # the tests'/snaps' deterministic readback
        self._stage_busy = False
        self.stage_btn.setEnabled(True)
        self._stage_label("Check the staging")
        if wmesh is not None:
            self._wmesh = wmesh
            self._stage_armed = True
        else:                                      # the floor did not load: nothing may be judged
            self._wmesh = None                     # on the OLD one (an edit's re-judge would paint
            self._stage_armed = False              # its checkmark over this error)
            self._restage_timer.stop()
        self.stage_note.setText(res.summary())
        widgets.set_state(self.stage_note,
                          "warn" if (res.warnings or res.skipped or res.error) else "")
        self._verdicts = list(rows or [])
        if getattr(self, "_stage_moved", False):   # the scenes were edited while this ran: a stall
            self._stage_moved = False              # would paint on whichever scene now has its
            self._verdicts = []                    # number. Paint nothing; judge the doc as it is.
            if self._stage_armed and self._wmesh is not None:
                self._restage_timer.start()
        self.stage_list.clear()
        unused = list(self._verdicts)              # each sentence is ONE verdict row's own text
        for w in res.warnings:                     # (stage_verdicts is parity-fenced to it)
            v = next((r for r in unused if r["text"] == w), None)
            if v is not None:
                unused.remove(v)
            self._stage_item(f"⚠ {self._scene_words(w)}", v)
        for lbl, why in res.skipped:
            k = int(lbl.split("#")[1]) if "#" in lbl else 0
            self._stage_item(f"? {self._scene_words(lbl)} not checked — {why}", {"scene": k})
        self.stage_list.setVisible(self.stage_list.count() > 0)
        self._paint_verdicts()
        if self._stage_explicit:                   # the author asked: show them where it stalls
            mine = [r for r in self._verdicts if r.get("scene") == self._scene]
            if mine:
                self.canvas.reveal_verdict(mine[0])
        if self.board_btn.isChecked():
            self._refresh_board()                  # the warm mesh upgrades straight legs to routes

    @staticmethod
    def _scene_words(text):
        """The build labels a scene ``[cutscene] #k`` -- and the ONLY scene of a field plain
        ``[cutscene]``; the rail and PROBLEMS call it ``scene #k``. One name for one scene in
        this column (the leading label only -- the sentence is the build's own)."""
        if text.startswith("[cutscene] #"):
            return "scene " + text[len("[cutscene] "):]
        if text == "[cutscene]" or text.startswith("[cutscene] "):
            return "scene #0" + text[len("[cutscene]"):]
        return text

    def _stage_item(self, text, where):
        self.stage_list.addItem(text)
        self.stage_list.item(self.stage_list.count() - 1).setData(Qt.ItemDataRole.UserRole, where)

    def _on_stage_item(self, item):
        """A staging row is a door: select its scene and step, and show its stall on the stage
        (scrolled into view from the verdict's own point; the zoom stays the author's)."""
        where = item.data(Qt.ItemDataRole.UserRole)
        if not where or self._raw is None:
            return
        k = where["scene"]
        if k != self._scene:
            self.rail.setCurrentRow(k)             # the rail's own path (a dirty editor refuses)
            if self._scene != k:
                return
        step = where.get("step")
        if step is not None and step != self._selected_step:
            self._on_step_select(step)
        if "b" in where:
            self.canvas.reveal_verdict(where)

    def _paint_verdicts(self):
        """The stage shows ONE scene, so it paints only that scene's verdicts: another scene's
        stall would land on this scene's step of the same number (a different, fine step)."""
        self.canvas.set_verdicts([r for r in self._verdicts if r.get("scene") == self._scene])

    def _restage(self):
        if self._stage_busy:
            self._restage_timer.start()            # let the in-flight run land first
            return
        self.stage_now(warm=True)

    def _reset_stage(self):
        """Field switch / project close: another field's mesh or verdicts must not linger."""
        self._stage_gen += 1
        self._restage_timer.stop()
        self._wmesh = None
        self._stage_armed = False
        self._stage_busy = False
        self.stage_btn.setEnabled(True)
        self._stage_label("Check the staging")
        self.stage_note.setText("")
        widgets.set_state(self.stage_note, "")
        self.stage_list.clear()
        self.stage_list.setVisible(False)
        self._verdicts = []
        if hasattr(self, "canvas"):
            self.canvas.set_verdicts([])
