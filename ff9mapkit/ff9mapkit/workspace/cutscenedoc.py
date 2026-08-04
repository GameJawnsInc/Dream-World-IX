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
from PySide6.QtGui import QBrush, QColor, QFontMetrics, QPen
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QPlainTextEdit, QPushButton, QScrollArea, QSlider, QSplitter, QStackedLayout,
    QVBoxLayout, QWidget,
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
        self.on_pick_stage = on_pick_stage         # arm a one-shot canvas click -> value
        self.scene = None                          # the open (scene, step) target; insert_at
        self.step_i = None                         # not None = ADD mode (insert at that row)
        self.insert_at = None
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
        close_btn = QPushButton("Close")
        close_btn.setProperty("role", "quiet")
        close_btn.clicked.connect(lambda: self.on_close())
        head.addWidget(close_btn)
        hw = QWidget()
        hw.setLayout(head)
        v.addWidget(hw)
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
        self.pick_btn.setToolTip("Click a point on the stage below — it lands here as x, z.")
        self.pick_btn.clicked.connect(lambda: self.on_pick_stage and self.on_pick_stage())
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
        self.say_preview = forms_qt._wrap_preview_panel(
            self.value_text, lambda: self.value_text.toPlainText(),
            wrap_width_fn or (lambda: None))
        v.addWidget(self.say_preview)
        self.hint = widgets.caption("")
        v.addWidget(self.hint)
        v.addWidget(QLabel("Actor:"))
        self.actor = QComboBox()
        self.actor.setEditable(True)               # the cast completes; free text stays legal
        self.actor.setAccessibleName("Cutscene step actor")
        self.actor.lineEdit().setPlaceholderText("blank = sole cast member / narration voice")
        v.addWidget(self.actor)
        self.with_prev = QCheckBox("Runs with the previous beat")
        self.with_prev.setAccessibleName("Cutscene step runs in parallel with the previous beat")
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
        self.x_signal = _erow("signal", "Signal when typed (n or blank):", QLineEdit(),
                              "fire the text signal as the line finishes typing — pair with "
                              "'Wait for text signal'")
        v.addWidget(self.extras)
        self.note = widgets.caption("")
        self.note.setWordWrap(True)
        v.addWidget(self.note)

    # -- kind plumbing --
    def current_kind(self):
        return self.kind.currentData()

    def _is_text(self):
        return self.current_kind() in forms.TEXT_STEPS

    def _on_kind(self, _i=0):
        k = self.current_kind()
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
            "Fork this beat alongside the one above it (both finish before the next)."
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
            getattr(self, f"x_{key}").setText("" if v is None else str(v))
        self.x_instant.setChecked(bool(step.get("instant")))
        self.x_hold.setChecked(bool(step.get("hold")))
        self.title.setText(f"Step {step_i} — edit" if insert_at is None
                           else f"New step — lands at row {insert_at}")
        self.note.setText("")
        widgets.set_state(self.note, "")
        self._on_kind()
        self.show()

    def read_step(self) -> dict:
        """The step the widgets describe. Raises ValueError with the field named."""
        k = self.current_kind()
        raw = (self.value_text.toPlainText().replace("\\n", "\n") if self._is_text()
               else self.value_line.text())
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
                    step[key] = s
            for key in ("window", "speed", "duration", "signal"):
                s = getattr(self, f"x_{key}").text().strip()
                if s:
                    try:
                        step[key] = int(s)
                    except ValueError:
                        raise ValueError(f"{key} must be a whole number (got {s!r})")
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
        self._board = None                         # the storyboard model (when the strip is on)
        self._guide_state = "nofield"
        self._wmesh = None                         # the staging lane's cached walkmesh (per field)
        self._last_stage = None                    # the last StagingResult (tests/snaps read it)
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
                actions=[("Add a scene", self._add_scene)],
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
        bar = QWidget()
        bh = QHBoxLayout(bar)
        bh.setContentsMargins(10, 4, 10, 0)
        bh.setSpacing(10)
        self.scene_title = widgets.role_label("—", "cardtitle")
        bh.addWidget(self.scene_title)
        self.scene_gate = widgets.ElideLabel("", min_ch=8)
        bh.addWidget(self.scene_gate, 1)
        self.add_step_btn = widgets.ElideButton("＋ Step")
        self.add_step_btn.setProperty("role", "quiet")
        self.add_step_btn.setToolTip("Insert a step after the selected row (at the end when "
                                     "nothing is selected).")
        self.add_step_btn.clicked.connect(self._add_step)
        bh.addWidget(self.add_step_btn)
        self.settings_btn = widgets.ElideButton("✎ Settings")
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
            "Scrub the scene BEAT by BEAT — positions chain the way the compiler chains "
            "them, the say line shows with its final in-game wrapping.\n"
            "No clock, on purpose: a say waits for the player, so seconds would be fiction.")
        self.board_btn.toggled.connect(self._toggle_board)
        bh.addWidget(self.board_btn)
        cl.addWidget(bar)
        # the scene-settings card (hidden until ✎ Settings): the extended CUTSCENE_SPEC through
        # the shared form builder, Apply-committed (a per-keystroke checkpoint would spam undo)
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
        # the form SCROLLS inside a capped well: ten spec fields put a ~700px floor under the
        # card, and a pane denied its height must scroll, never clip (the round-13 law)
        sc_host = QWidget()
        self._settings_host = QVBoxLayout(sc_host)
        self._settings_host.setContentsMargins(0, 0, 0, 0)
        self._settings_scroll = QScrollArea()
        self._settings_scroll.setWidgetResizable(True)
        self._settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._settings_scroll.setWidget(sc_host)
        self._settings_scroll.setMaximumHeight(int(340 * self._scale / 100))
        sc_lay.addWidget(self._settings_scroll)
        self.settings_note = widgets.caption("")
        self.settings_note.setWordWrap(True)
        sc_lay.addWidget(self.settings_note)
        self._settings_getters = None
        self.settings_card.hide()
        cl.addWidget(self.settings_card)
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
        self._ladder_actions = {"move": self._move_step, "edit": self._edit_step,
                                "dup": self._dup_step, "delete": self._del_step}
        self.ladder = StepLadder(self.pal, actions=self._ladder_actions,
                                 on_select=self._on_step_select)
        lscroll = QScrollArea()
        lscroll.setWidgetResizable(True)
        lscroll.setWidget(self.ladder)             # h-bar as-needed: denied width must scroll,
        lscroll.setFrameShape(QFrame.Shape.NoFrame)   # never clip (the round-13 law)
        self._vsplit.addWidget(lscroll)
        self.editor = StepEditor(
            self.pal, on_apply=self._apply_step, on_close=self._close_editor,
            pick_anim=self._pick_anim_for_step, on_pick_stage=self._arm_stage_pick,
            wrap_width_fn=lambda: cutscenescan.wrap_width(self._merged()))
        # the editor SCROLLS in its splitter slot: with the pacing drawer open it is taller
        # than any slot the vsplit can honestly give it (snap-measured 1604px of minimum
        # against an 850px window -- the round-13 clip, pre-empted)
        self._editor_scroll = QScrollArea()
        self._editor_scroll.setWidgetResizable(True)
        self._editor_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._editor_scroll.setWidget(self.editor)
        self._editor_scroll.hide()
        self._vsplit.addWidget(self._editor_scroll)
        self.canvas = CutsceneStage(self.pal, scale=self._scale,
                                    on_move=self._on_stage_move,
                                    on_insert=self._on_stage_insert,
                                    on_delete=self._on_stage_delete)
        self._vsplit.addWidget(self.canvas)
        k = self._scale / 100
        self._vsplit.setSizes([int(320 * k), 0, int(300 * k)])
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
            self._settings_scroll.setMaximumHeight(int(340 * pct / 100))

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
        sibling scene.toml per call, so staging and the board see spatial truth."""
        same_field = member == self._member
        if not same_field:
            if self.board_btn.isChecked():
                self.board_btn.setChecked(False)   # another field: the board is void
            if self.settings_btn.isChecked():
                self.settings_btn.setChecked(False)
            self._close_editor()
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
        handles = self._stage_handles()
        self.canvas.set_edit(bool(handles))
        self.canvas.set_selected_step(self._selected_step)
        self.canvas.set_scene(cutscenescan.stage_model(raw, self._scene), refit=refit,
                              handles=handles)
        if self.settings_card.isVisible():
            self._fill_settings()                  # ops fired; the card reflects the write target
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
        handles = self._stage_handles()
        self.canvas.set_edit(bool(handles))
        self.canvas.set_selected_step(self._selected_step)
        self.canvas.set_scene(cutscenescan.stage_model(raw, self._scene), handles=handles)

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
        if self._stage_armed and self._wmesh is not None:
            self._restage_timer.start()            # the armed lane: re-judge on the warm mesh

    def _add_scene(self):
        if self._raw is None:
            return
        label = cutscenescan.add_scene(self._raw)
        self._scene = len(cutscenescan.scene_rows(self._raw)) - 1
        self._selected_step = None
        self._after_edit(label)

    def _dup_scene(self):
        if self._raw is None:
            return
        label = cutscenescan.duplicate_scene(self._raw, self._scene)
        self._scene += 1
        self._after_edit(label)

    def _del_scene(self):
        if self._raw is None:
            return
        self._close_editor()
        label = cutscenescan.delete_scene(self._raw, self._scene)
        self._scene = max(0, self._scene - 1)
        self._selected_step = None
        self._after_edit(label)

    # -- scene settings (Apply-committed: a per-keystroke checkpoint would spam undo) --
    def _toggle_settings(self, on):
        self.settings_card.setVisible(on)
        if on:
            self._fill_settings()

    def _fill_settings(self):
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

    def _steps(self):
        blocks = forms.all_blocks((self._raw or {}).get("cutscene"))
        b = blocks[self._scene] if 0 <= self._scene < len(blocks) else {}
        return b.get("steps") if isinstance(b.get("steps"), list) else []

    def _edit_step(self, i):
        st = self._steps()
        if not 0 <= i < len(st):
            return
        self._selected_step = i
        self.editor.open_step(self._scene, i, st[i], self._cast())
        self._editor_scroll.show()
        self._open_editor_guard()
        self._render()

    def _add_step(self):
        if self._raw is None:
            return
        at = (self._selected_step + 1) if self._selected_step is not None else len(self._steps())
        self.editor.open_step(self._scene, None, {"say": ""}, self._cast(), insert_at=at)
        self._editor_scroll.show()
        self._open_editor_guard()

    def _open_editor_guard(self):
        s = self._vsplit.sizes()                   # opening must not crush the stage to a sliver
        if s[1] < 120:                             # (the behavior editor's snap-caught guard):
            e = max(150, min(340, self.editor.sizeHint().height()))   # the ladder yields first,
            total = sum(s)                                            # the canvas stays usable
            canvas = max(140, min(s[2], total - e - 160))
            self._vsplit.setSizes([max(120, total - e - canvas), e, canvas])

    def _close_editor(self):
        self.editor.hide()
        if hasattr(self, "_editor_scroll"):
            self._editor_scroll.hide()             # the scroll well must not linger as a blank band
        self.editor.scene = self.editor.step_i = self.editor.insert_at = None
        self._disarm_stage_pick()

    def _apply_step(self):
        if self._raw is None:
            return
        try:
            step = self.editor.read_step()
        except ValueError as e:
            self.editor.note.setText(str(e))
            widgets.set_state(self.editor.note, "error")
            return
        self.editor.note.setText("")
        widgets.set_state(self.editor.note, "")
        if self.editor.insert_at is not None:      # ADD: insert, then ADVANCE -- the next Apply
            at = self.editor.insert_at             # lands the NEXT line. The conversation loop
            label = cutscenescan.add_step(self._raw, self._scene, at, step)   # the old form's
            self.editor.insert_at = at + 1         # same-kind overwrite made impossible.
            self.editor.title.setText(f"New step — lands at row {self.editor.insert_at}")
            self._selected_step = at
            (self.editor.value_text.clear() if self.editor._is_text()
             else self.editor.value_line.clear())
        else:
            i = self.editor.step_i
            label = cutscenescan.update_step(self._raw, self._scene, i, step,
                                             managed=STEP_EDITOR_KEYS)
            self._selected_step = i
        self._after_edit(label)

    def _move_step(self, i, delta):
        st = self._steps()
        j = i + (1 if delta > 0 else -1)
        if not (0 <= i < len(st)) or not (0 <= j < len(st)):
            return                                 # the boundary: nothing to move past
        self._close_editor()                       # indices shift under a structural edit
        label = cutscenescan.move_step(self._raw, self._scene, i, delta)
        if self._selected_step == i:
            self._selected_step = j
        self._after_edit(label)

    def _dup_step(self, i):
        if not 0 <= i < len(self._steps()):
            return
        self._close_editor()
        label = cutscenescan.duplicate_step(self._raw, self._scene, i)
        self._selected_step = i + 1
        self._after_edit(label)

    def _del_step(self, i):
        if not 0 <= i < len(self._steps()):
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

    def _arm_stage_pick(self):
        self.canvas.on_sim_click = self._stage_picked
        self.canvas.set_sim_mode(True)             # the base canvas's one-click input lane

    def _disarm_stage_pick(self):
        if self.canvas.on_sim_click is not None:
            self.canvas.on_sim_click = None
            self.canvas.set_sim_mode(False)

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
        self._after_edit(label)

    def _on_stage_insert(self, lid):
        _kind, k, i, j = lid
        try:
            label = cutscenescan.insert_path_point(self._raw, k, i, j)
        except ValueError as e:                    # a NAMED point: refuse and say why
            self._say_problem(str(e))
            return
        self._after_edit(label)

    def _on_stage_delete(self, lid):
        _kind, k, i, j = lid
        try:
            label = cutscenescan.delete_path_point(self._raw, k, i, j)
        except ValueError as e:                    # the 1-point floor: refuse and say why
            self._say_problem(str(e))
            return
        self._after_edit(label)

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
            return res, [], None

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
