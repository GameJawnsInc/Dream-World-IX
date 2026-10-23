"""The World tab's carry tools (overworld editor rungs C1 and C2): place a real stock shape on a deployed island in
the 3D view. :class:`ForestTool` carries a canopy (``world-forest``); :class:`worldmountain.MountainTool` a rock
massif (``world-mountain``). Both are :class:`CarryTool`, which holds everything the two share.

You click the map where the shape goes, drag its ghost, turn it and size it; the cheap laws preview while you
move, and when you let go the tool runs the verb with ``--dry-run`` and draws its verdict where the gates refuse.
Accept runs the same command without ``--dry-run`` against a DRAFT (``world.draft``: the folder's world files copied
out of the install), and the view then draws the draft in place of the folder. The game never sees a draft until
its edits are promoted (rung C4: Promote, Revert promote, Show in game).

THE CLI STAYS THE ORACLE: a tool never carves in the Workspace's process. Every judgement is the command the
tool's edit module builds (``world.forestedit.command`` / ``world.mountainedit.command``), run as a subprocess
(the runner seam), and its ``--report-json`` verdict.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import numpy as np
from PySide6.QtCore import QProcess, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QSpinBox,
                               QVBoxLayout, QWidget)

from . import widgets

CHECK_DELAY_MS = 600            # handles still this long -> the check runs (a drag fires it on release, at once)
RIBBON_H = 1.2                  # the ghost rim's band height (world units)
MARK_H = 7.0                    # a refusal mark's height
GHOST_ALPHA = 0.42
GATE_WORDS = {"footprint": "the footprint law", "hole": "the hole carve", "leak": "the deployed-blocks bound",
              "geometry": "the geometry gate", "step": "the canopy step law", "walk-in": "the walk-in simulation",
              "census": "the placement census", "error": "the carve"}
WHOLE_MAP = ((768.0, -640.0), 767.0)    # read_deployed_blocks' near/reach that spans all 24 columns once


def _rgb(hexcolour):
    h = str(hexcolour).lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def kit_cwd() -> Path:
    """The directory a ``python -m ff9mapkit`` job runs in, so it imports THIS package (the checkout's, not an
    installed copy's): ``-m`` puts the working directory first on ``sys.path``."""
    import ff9mapkit
    return Path(ff9mapkit.__file__).resolve().parents[1]


class QProcessRunner:
    """The default runner: one ``QProcess`` per job, stdout and stderr merged, ``done(code, text)`` on exit."""

    def __init__(self):
        self.proc = None

    def start(self, argv, cwd, done):
        self.kill()
        proc = QProcess()
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.setWorkingDirectory(str(cwd))
        out = []
        proc.readyReadStandardOutput.connect(lambda: out.append(bytes(proc.readAllStandardOutput()).decode(
            "utf-8", "replace")))

        def fin(code, _status):
            if self.proc is proc:
                self.proc = None
            out.append(bytes(proc.readAllStandardOutput()).decode("utf-8", "replace"))
            done(code, "".join(out))
        proc.finished.connect(fin)
        self.proc = proc
        proc.start(str(argv[0]), [str(a) for a in argv[1:]])

    def kill(self):
        proc, self.proc = self.proc, None
        if proc is not None and proc.state() != QProcess.ProcessState.NotRunning:
            proc.finished.disconnect()
            proc.kill()
            proc.waitForFinished(2000)

    def busy(self):
        return self.proc is not None


class CarryTool(QWidget):
    """A carry card under the 3D view. ``panel`` is the World tab's :class:`WorldView3DPanel`; ``source_fn()`` the
    mod folder the tab shows; ``game_fn()`` the install; ``on_changed(draft)`` re-reads the view after an Accept
    or a discard. ``on_reload(x, z)`` (dev checkout: the shell's world reload) makes the running game re-read the
    world after a Promote. ``runner``, ``drafts_root``, ``ask``, ``outline_fn(donor)``, ``soup_fn(folder)`` (an
    island ``SoupIndex``) and ``sync`` (background reads inline) are the test and snap seams.

    A subclass names its shape (``TITLE``, ``NOUN``, ``PART``, ``VERB``, ``GATES``) and supplies the parts that
    differ: ``_edit_module``, ``_build_handles``, ``donor``, ``_cmd``, ``_shape``, ``_preview_at``, ``_pass_text``
    and ``_preview_text``."""

    TITLE, NOUN, PART, VERB = "Shape", "shape", "shape", "world-?"
    GATES = GATE_WORDS
    _extra_rows = ()
    CHECK_TIME = "about seven seconds"                   # a passing world-forest dry run, measured (C1)
    _bg_done = Signal(str, int, object, object)          # (what, serial, result, error) from a worker thread

    def __init__(self, pal, panel, *, game_fn, source_fn, on_changed=None, runner=None, drafts_root=None,
                 ask=None, outline_fn=None, soup_fn=None, sync=False, on_reload=None):
        super().__init__()
        self.FE = FE = self._edit_module()
        self.pal, self.panel = pal, panel
        self._game_fn, self._source_fn, self._on_changed = game_fn, source_fn, on_changed
        self._runner = runner or QProcessRunner()
        self._drafts_root = drafts_root
        self._ask = ask or self._ask_dialog
        self._outline_fn = outline_fn or (lambda donor: FE.outline(donor, game=self._game_fn()))
        self._soup_fn = soup_fn or self._read_soup
        self._sync = sync
        self._on_reload = on_reload
        self._last_center = None                         # where Show in game goes (the last accepted shape)
        self._draft_state = (0, None)                    # (edited disc-1 blocks, the last unreverted promote)
        self._bg_done.connect(self._on_bg)
        self._serial = 0
        self.center = None                               # (x, z) on the editor's grid, or None until a click
        self._pick_y = 0.0
        self._outlines = {}                              # donor -> outline (a stock read, once per donor)
        self._ix = None                                  # the island soup the preview reads (SoupIndex)
        self._ix_for = None                              # the folder it was read from
        self._preview = None                             # the last preview
        self._ghost = None                               # (tris, rim) of the drawn ghost
        self._verdict = None                             # (handles key, verdict dict) of the last finished job
        self._job = None                                 # ("check" | "accept", key) while one runs
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._check)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = widgets.card()
        outer.addWidget(frame)
        card = QVBoxLayout(frame)
        card.setContentsMargins(14, 10, 14, 10)
        card.setSpacing(6)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(widgets.role_label(self.TITLE, "cardtitle"))
        self._build_handles(row)
        row.addStretch(1)
        self.close_btn = QPushButton("Close")
        self.close_btn.setProperty("role", "quiet")
        self.close_btn.setToolTip(f"Put the {self.NOUN} tool away (the draft keeps what you accepted).")
        self.close_btn.clicked.connect(self.close_tool)
        row.addWidget(self.close_btn)
        card.addLayout(row)
        for extra in self._extra_rows:                   # handles that would widen the first row past the window
            card.addLayout(extra)
        self.verdict_lbl = QLabel()
        self.verdict_lbl.setProperty("role", "banner")
        self.verdict_lbl.setWordWrap(True)
        self.verdict_lbl.setAccessibleName(f"{self.TITLE} verdict")
        card.addWidget(self.verdict_lbl)
        brow = QHBoxLayout()
        brow.setSpacing(8)
        self.accept_btn = QPushButton("Accept into draft")
        self.accept_btn.setObjectName("accent")
        self.accept_btn.setToolTip(f"Write this {self.NOUN} into the draft ({self.VERB} without --dry-run, against "
                                   "the draft folder). The install is not touched.")
        self.accept_btn.clicked.connect(self._accept)
        brow.addWidget(self.accept_btn)
        self.copy_btn = QPushButton("Copy command")
        self.copy_btn.setProperty("role", "quiet")
        self.copy_btn.setToolTip(f"Copy the {self.VERB} command Accept runs, to run it by hand.")
        self.copy_btn.clicked.connect(self._copy_command)
        brow.addWidget(self.copy_btn)
        self.draft_lbl = widgets.role_label("", "caption")
        self.draft_lbl.setWordWrap(True)
        self.draft_lbl.setAccessibleName("Draft")
        brow.addWidget(self.draft_lbl, 1)
        # rung C4: the draft into the live folder (world-promote: refuses over another deploy's bytes, backs up and
        # ledgers each write, mirrors disc 4, snapshots first so Revert is exact), then the game follows
        self.promote_btn = QPushButton("Promote")
        self.promote_btn.setToolTip("Write the draft's edits into the live mod folder (world-promote): each file is "
                                    "backed up first, the disc-4 mirror runs, and Revert promote puts them back.")
        self.promote_btn.clicked.connect(self._promote)
        brow.addWidget(self.promote_btn)
        self.revert_btn = QPushButton("Revert promote")
        self.revert_btn.setProperty("role", "quiet")
        self.revert_btn.setToolTip("Put the live folder back exactly as it was before the last promote "
                                   "(world-promote --revert). The edits stay in the draft.")
        self.revert_btn.clicked.connect(self._revert)
        brow.addWidget(self.revert_btn)
        self.show_btn = QPushButton("Show in game")
        self.show_btn.setProperty("role", "quiet")
        self.show_btn.setToolTip("Make the running game re-read the world map (a quick trip through a bench field "
                                 "and back) and put the party at the edit. The game must be on the world map, on foot.")
        self.show_btn.clicked.connect(self._show_in_game)
        brow.addWidget(self.show_btn)
        self.discard_btn = QPushButton("Discard draft")
        self.discard_btn.setProperty("role", "quiet")
        self.discard_btn.setToolTip("Delete the draft and everything accepted into it.")
        self.discard_btn.clicked.connect(self._discard)
        brow.addWidget(self.discard_btn)
        card.addLayout(brow)
        self._say(f"Click the map where the {self.NOUN} goes. Drag its ghost to move it.", "")
        self._sync_buttons()

    # -- what a subclass supplies --
    def _edit_module(self):
        raise NotImplementedError

    def _build_handles(self, row):
        """Add the shape's handles to the card's first row (a donor picker, an angle, its sizes); a second row goes
        in ``self._extra_rows``."""
        raise NotImplementedError

    def donor(self):
        raise NotImplementedError

    def _cmd(self, target, *, dry_run, report=None) -> list:
        """The verb's argv (after ``python -m ff9mapkit``) for the current handles against ``target``."""
        raise NotImplementedError

    def _shape(self, ol, ground_y):
        """The ghost ``(tris, rim)`` at the current handles, its rim seated on ``ground_y``."""
        raise NotImplementedError

    def _preview_at(self, ol, rim):
        """The cheap laws for the placed ghost: ``{"ok", "where", "why", ...}``."""
        raise NotImplementedError

    def _pass_text(self, v, where):
        """``(text, state)`` for a passing dry run."""
        raise NotImplementedError

    def _preview_text(self, pv):
        """``(text, state)`` for a preview the cheap laws refuse."""
        raise NotImplementedError

    def _show_point(self, v):
        """Where Show in game puts the party after this accepted verdict (the shape's centre)."""
        return tuple(v["center"]) if v.get("center") else None

    def _outline_loaded(self, donor, ol):
        """A donor's outline arrived (a subclass may set a handle from it)."""

    # -- the folders --
    def source(self) -> Path:
        return Path(self._source_fn())

    def draft(self):
        """The source's draft folder if one was made, else None."""
        from ..world import draft as D
        p = D.draft_path(self.source(), root=self._drafts_root)
        return p if D.read_meta(p) is not None else None

    def target(self) -> Path:
        """Where the shape is judged and written: the draft once it exists, else the source (read only)."""
        return self.draft() or self.source()

    # -- lifecycle --
    def open_tool(self):
        self.show()
        self._ix = self._ix_for = None                   # the other tool may have written the draft meanwhile
        self._refresh_draft_label()
        self._load_soup()
        self._load_outline(self.donor())

    def close_tool(self):
        self._timer.stop()
        self._runner.kill()
        self._job = None
        self.center = self._ghost = None
        self.panel.set_overlays([])
        self.panel.set_ghost(None)
        self.hide()

    def handles(self):
        """The handles as the command spells them: the stale guard every verdict is matched against."""
        if self.center is None:
            return None
        return tuple(self._cmd("-", dry_run=False))

    # -- background reads --
    def _bg(self, what, fn):
        self._serial += 1
        serial = self._serial
        if self._sync:                                   # the deterministic lane: tests and gui_snap
            try:
                out = (fn(), None)
            except Exception as e:                       # noqa: BLE001 -- surfaced like the threaded lane
                out = (None, e)
            self._on_bg(what, serial, *out)
            return

        def run():
            try:
                out = (fn(), None)
            except Exception as e:                       # noqa: BLE001 -- surfaced on the GUI thread
                out = (None, e)
            try:
                self._bg_done.emit(what, serial, *out)
            except RuntimeError:                         # the tool died while the worker read
                pass
        threading.Thread(target=run, daemon=True).start()

    def _read_soup(self, folder):
        """Every deployed Terrain block of ``folder`` as one island soup (about half a second for 94 blocks)."""
        from ..world import interior as IN
        (near, reach) = WHOLE_MAP
        blocks = IN.read_deployed_blocks(str(folder), near=near, reach=reach, game=self._game_fn())
        return self.FE.SoupIndex(IN.soup_from_blocks(blocks))

    def _load_soup(self):
        target = self.target()
        if self._ix is not None and self._ix_for == target:
            return
        self._bg("soup", lambda: (target, self._soup_fn(target)))

    def _load_outline(self, donor):
        if donor in self._outlines:
            self._outline_loaded(donor, self._outlines[donor])
            return
        self._bg("outline", lambda: (donor, self._outline_fn(donor)))

    def _on_bg(self, what, _serial, result, err):
        if err is not None:
            if what == "soup":
                self._ix, self._ix_for = None, None
                self._say(f"The island could not be read: {err}", "error")
            elif what == "outline":
                self._say(f"The {self.PART} could not be read: {err}", "error")
            elif what == "draft":
                self._job = None
                self._say(f"The draft could not be made: {err}", "error")
                self._sync_buttons()
            return
        if what == "soup":
            self._ix_for, self._ix = result
        elif what == "outline":
            donor, ol = result
            self._outlines[donor] = ol
            if donor == self.donor():
                self._outline_loaded(donor, ol)
        elif what == "draftinfo":
            self._show_draft_info(*result)
            return
        elif what == "draft":
            self._refresh_draft_label()
            kind, draft = result
            if self._job is None or self._job[1] != self.handles():
                self._job = None                         # a handle moved while the copy ran: judge the new spot
                self._handles_changed(at_once=True)
                return
            self._run_job(kind, draft)
            return
        self._redraw()
        if self.center is not None and self._job is None and self._current_verdict() is None:
            self._timer.start(0)                         # a click that landed before the read: judge it now

    # -- the handles --
    def place(self, x, z, y=0.0):
        """A click on the map (the World tab forwards its pick while the tool is open): the ghost goes there."""
        step = self.FE.CENTRE_STEP
        self.center = (round(x / step) * step, round(z / step) * step)
        self._pick_y = float(y)
        self._handles_changed()

    def drag_to(self, x, z):
        step = self.FE.CENTRE_STEP
        self.center = (round(x / step) * step, round(z / step) * step)
        self._timer.stop()
        self._redraw()

    def drop_at(self, x, z):
        self.drag_to(x, z)
        self._handles_changed(at_once=True)

    def _handles_changed(self, *, at_once=False):
        self._load_outline(self.donor())
        if self._job is not None and self._job[0] == "check":
            self._runner.kill()                          # a moved handle makes the running check moot
            self._job = None
        self._redraw()
        if self.center is not None:
            self._timer.start(0 if at_once else CHECK_DELAY_MS)

    def _redraw(self):
        """The ghost, the cheap laws' preview and the last verdict's marks, from the current handles."""
        ol = self._outlines.get(self.donor())
        if self.center is None or ol is None or self._ix is None:
            if self.center is not None:
                self._say(f"Reading the {self.PART} and the island…", "")
            self._sync_buttons()
            return
        _t0, rim0 = self._shape(ol, 0.0)
        ys = [y for y in (self._ix.ground_y(x, z) for x, _y, z in rim0) if y is not None]
        gy = float(np.median(ys)) if ys else self._pick_y
        tris, rim = self._shape(ol, gy)
        self._ghost = (tris, rim)
        self._preview = self._preview_at(ol, rim)
        verdict = self._current_verdict()
        if verdict is not None:
            kind = "good" if verdict["ok"] else "bad"
            where = [] if verdict["ok"] else (verdict.get("refused") or {}).get("where") or []
        elif not self._preview["ok"]:
            kind, where = "bad", self._preview["where"]
        else:
            kind, where = "pending", []
        colour = _rgb(self.pal["success"] if kind == "good" else self.pal["error"] if kind == "bad"
                      else self.pal["accent"])
        mark = _rgb(self.pal["error"])
        from .worldview3d import pin_tris, ribbon_tris
        overlays = [(tris.reshape(-1, 3), colour, GHOST_ALPHA, True), (ribbon_tris(rim, RIBBON_H), colour, 1.0, False)]
        for x, z in where[:24]:
            y = self._ix.ground_y(x, z)
            overlays.append((pin_tris((x, gy if y is None else y, z), MARK_H, w_frac=0.18), mark, 1.0, False))
        self.panel.set_overlays(overlays)
        self.panel.set_ghost({"center": self.center, "y": gy, "poly": rim[:, [0, 2]]})
        self._explain()
        self._sync_buttons()

    def _current_verdict(self):
        if self._verdict is None or self._verdict[0] != self.handles():
            return None
        return self._verdict[1]

    def _explain(self):
        if self._job is not None:
            return
        v = self._current_verdict()
        x, z = self.center
        where = f"at x {x:g}, z {z:g}"
        if v is not None:
            if v["ok"]:
                if v.get("dry_run"):
                    self._say(*self._pass_text(v, where))
                return
            ref = v.get("refused") or {}
            gate = self.GATES.get(ref.get("gate"), "a gate")
            detail = f" ({ref['detail']})" if ref.get("detail") else ""
            marks = " The marks show where." if ref.get("where") else ""
            self._say(f"Refused by {gate}{detail}: {ref.get('message', '')}.{marks}", "error")
            return
        pv = self._preview
        if pv is not None and not pv["ok"]:
            self._say(*self._preview_text(pv))
            return
        self._say(f"Footprint lawful {where}. Checking every gate when you let go…", "")

    def _say(self, text, state):
        self.verdict_lbl.setText(text)
        widgets.set_state(self.verdict_lbl, state)

    def _sync_buttons(self):
        v = self._current_verdict()
        self.accept_btn.setEnabled(self._job is None and v is not None and v["ok"] and bool(v.get("dry_run")))
        self.copy_btn.setEnabled(self.center is not None)
        has_draft = self.draft() is not None
        edited, last = self._draft_state if has_draft else (0, None)
        self.discard_btn.setVisible(has_draft)
        self.discard_btn.setEnabled(self._job is None)
        self.promote_btn.setVisible(has_draft and edited > 0)
        self.promote_btn.setEnabled(self._job is None)
        self.revert_btn.setVisible(last is not None)
        self.revert_btn.setEnabled(self._job is None)
        self.show_btn.setVisible(self._on_reload is not None and self._show_target() is not None)

    def _refresh_draft_label(self):
        """The draft line. Its counts walk both trees (about half a second), so a worker reads them."""
        from ..world import draft as D
        d = self.draft()
        src = self.source().name
        if d is None:
            self.draft_lbl.setText(f"Accept writes to a draft of {src} outside the install; the game does not "
                                   "load it.")
        else:
            self.draft_lbl.setText(f"Draft of {src}. The game does not load it.")
            self._bg("draftinfo", lambda: (d, {(bx, by) for disc, bx, by in D.edited_blocks(d) if disc == 1},
                                           D.stale(d), D.last_promote(d)))
        self._sync_buttons()

    def _show_draft_info(self, d, blocks, stale, last=None):
        if d != self.draft():
            return
        self._draft_state = (len(blocks), last)
        self._sync_buttons()
        src, n = self.source().name, len(blocks)
        self.draft_lbl.setText(f"Draft of {src}: {n} block{'s' if n != 1 else ''} edited. The game does not "
                               "load it." + (f" ⚠ {src} changed since the draft was made ({len(stale)} files)."
                                             if stale else ""))

    # -- the jobs (the CLI is the oracle) --
    def _check(self):
        if self.center is None or self._preview is None or not self._preview["ok"]:
            return
        if self._current_verdict() is not None or self._job is not None:
            return
        self._start("check")

    def _accept(self):
        v = self._current_verdict()
        if v is None or not v["ok"]:
            return
        self._start("accept")

    def _start(self, kind):
        """Make the draft first if there is none (a worker copies the folder's world files, once), then run."""
        if self.draft() is None:
            from ..world import draft as D
            src, game, root = self.source(), self._game_fn(), self._drafts_root
            self._job = (kind, self.handles())
            self._say(f"Making a draft of {src.name} outside the install (once)…", "")
            self._sync_buttons()
            self._bg("draft", lambda: (kind, D.ensure_draft(src, game=game, root=root)))
            return
        self._run_job(kind, self.draft())

    def argv(self, kind, draft, report):
        game = self._game_fn()
        return [sys.executable, "-m", "ff9mapkit", "--game", str(game)] + self._cmd(
            draft, dry_run=kind == "check", report=report)

    def _run_job(self, kind, draft):
        key = self.handles()
        if key is None:
            self._job = None
            return
        report = Path(tempfile.mkdtemp(prefix=f"ff9_{self.NOUN}_")) / "verdict.json"
        self._job = (kind, key)
        self._say(f"Checking every gate ({self.CHECK_TIME})…" if kind == "check"
                  else f"Writing the {self.NOUN} into the draft of {self.source().name}…", "")
        self._sync_buttons()
        self._runner.start(self.argv(kind, draft, report), kit_cwd(),
                           lambda code, text: self._job_done(kind, key, report, code, text))

    def _job_done(self, kind, key, report, code, text):
        if self._job != (kind, key):
            return                                       # superseded (a handle moved, or the tool closed)
        self._job = None
        v = self.FE.read_verdict(report)
        if v is None:
            last = [ln for ln in text.splitlines() if ln.strip()][-1:] or [f"exit code {code}"]
            v = {"ok": False, "dry_run": kind == "check",
                 "refused": {"gate": "error", "message": f"the job ended without a verdict: {last[0]}", "where": []}}
        self._verdict = (key, v)
        if kind == "accept" and v["ok"]:
            self._accepted(v)
            return
        self._redraw()

    def _accepted(self, v):
        pt = self._show_point(v)
        if pt is not None:
            self._last_center = pt
        n = len(v.get("written") or [])                  # the blocks whose bytes changed (the read window is wider)
        self.center = self._ghost = None
        self._verdict = None
        self._ix = self._ix_for = None                   # the island changed: re-read it from the draft
        self.panel.set_overlays([])
        self.panel.set_ghost(None)
        self._refresh_draft_label()
        self._say(f"In the draft: {n} block{'s' if n != 1 else ''} written. The view now draws the draft in place "
                  f"of {self.source().name}. Click to place another {self.NOUN}.", "ok")
        self._load_soup()
        if self._on_changed is not None:
            self._on_changed(self.draft())

    def _copy_command(self):
        """Accept's command, to run by hand: always against the DRAFT's path, never the live folder (before the
        first check there is no draft yet, and the command then refuses: no deployed island there)."""
        if self.center is None:
            return
        from ..world import draft as D
        argv = ["ff9mapkit"] + self._cmd(D.draft_path(self.source(), root=self._drafts_root), dry_run=False)
        QGuiApplication.clipboard().setText(subprocess.list2cmdline(argv))

    # -- promote and the game follows (rung C4; the CLI is the oracle here too: world-promote) --
    def _promote(self):
        d = self.draft()
        if d is None or self._job is not None:
            return
        n = self._draft_state[0]
        if not self._ask("Promote the draft?", f"Write the draft's {n} edited block{'s' if n != 1 else ''} into "
                         f"{self.source().name} in the game folder? Each file is backed up first and the disc-4 "
                         "mirror runs; Revert promote puts the folder back exactly. The game shows it on its next "
                         "world load."):
            return
        self._run_promote(d, revert=False)

    def _revert(self):
        d = self.draft()
        if d is None or self._job is not None:
            return
        if not self._ask("Revert the promote?", f"Put {self.source().name} back exactly as it was before the last "
                         "promote? The edits stay in the draft."):
            return
        self._run_promote(d, revert=True)

    def _run_promote(self, d, *, revert):
        report = Path(tempfile.mkdtemp(prefix="ff9_promote_")) / "verdict.json"
        argv = [sys.executable, "-m", "ff9mapkit", "--game", str(self._game_fn()), "world-promote", str(d),
                "--report-json", str(report)] + (["--revert"] if revert else [])
        kind = "revert" if revert else "promote"
        self._job = (kind, None)
        self._say(("Reverting the promote in " if revert else "Promoting the draft into ") + f"{self.source().name}…",
                  "")
        self._sync_buttons()
        self._runner.start(argv, kit_cwd(), lambda code, text: self._promote_done(kind, report, code, text))

    def _promote_done(self, kind, report, code, text):
        if self._job != (kind, None):
            return
        self._job = None
        v = self.FE.read_verdict(report) or {"ok": False, "error": ([ln for ln in text.splitlines() if ln.strip()][-1:]
                                                                    or [f"exit code {code}"])[0]}
        src = self.source().name
        if not v.get("ok"):
            self._say(f"The {kind} did not run: {v.get('error')}", "error")
            self._sync_buttons()
            return
        cells = v.get("cells") or []
        if self._last_center is None and cells:
            bx, by = cells[0]
            self._last_center = (64.0 * bx + 32.0, -(64.0 * by + 32.0))
        follow = " Show in game makes the running game re-read it." if self._on_reload is not None else \
            " The game shows it on its next world load."
        if kind == "promote":
            self._say(f"Promoted into {src}: {len(cells)} block{'s' if len(cells) != 1 else ''}, each file backed "
                      f"up, disc 4 mirrored.{follow}", "ok")
        else:
            self._say(f"Reverted: {src} is exactly as it was before the promote; the edit is still in the draft."
                      f"{follow}", "ok")
        self._ix = self._ix_for = None                   # the live folder (and the draft) moved: read them again
        self._refresh_draft_label()
        self._load_soup()
        if self._on_changed is not None:                 # promoted: the game's stack has it; reverted: only the draft
            self._on_changed(None if kind == "promote" else self.draft())

    def _show_target(self):
        return self._last_center

    def _show_in_game(self):
        t = self._show_target()
        if t is not None and self._on_reload is not None:
            self._on_reload(*t)

    def _ask_dialog(self, title, text):
        return QMessageBox.question(self, title, text) == QMessageBox.StandardButton.Yes

    def _discard(self):
        from ..world import draft as D
        d = self.draft()
        if d is None or self._job is not None:
            return
        n = len(D.edited_blocks(d))
        if not self._ask("Discard the draft?", f"Delete the draft of {self.source().name} and the {n} edited "
                         f"block file set{'s' if n != 1 else ''} in it? The install is not touched."):
            return
        D.discard(d, root=self._drafts_root)
        self._ix = self._ix_for = None
        self._verdict = None
        self._refresh_draft_label()
        self._load_soup()
        self._say(f"Draft discarded. Click the map where the {self.NOUN} goes.", "")
        if self._on_changed is not None:
            self._on_changed(None)

    def retheme(self, pal):
        self.pal = pal
        self._redraw()


class ForestTool(CarryTool):
    """The forest card (rung C1): a qualified canopy, its angle and its spread, judged by ``world-forest``."""

    TITLE, NOUN, PART, VERB = "Forest", "forest", "canopy", "world-forest"

    def _edit_module(self):
        from ..world import forestedit
        return forestedit

    def _build_handles(self, row):
        from ..world import interior as IN
        FE = self.FE
        self.donor_box = QComboBox()
        self.donor_box.setAccessibleName("Canopy donor")
        self.donor_box.setToolTip("Which stock canopy to carry, whole. Only canopies the donor catalogue has "
                                  "qualified (grass all round, walled all round) are listed.")
        for r in FE.canopy_donors():
            self.donor_box.addItem(f"{r['name']} ({r['blocks']})", "{},{}".format(*r["donor"]))   # str: findData
            self.donor_box.setItemData(self.donor_box.count() - 1, r.get("note", ""), 3)   # Qt.ToolTipRole
        self.donor_box.currentIndexChanged.connect(lambda _ix: self._handles_changed())
        row.addWidget(self.donor_box)
        row.addWidget(widgets.role_label("Angle", "caption"))
        self.angle = QSpinBox()
        self.angle.setRange(0, 359)
        self.angle.setWrapping(True)
        self.angle.setSingleStep(5)
        self.angle.setSuffix("°")
        self.angle.setAccessibleName("Forest angle")
        self.angle.setToolTip("Turn the canopy about its centre, clockwise seen from above (world-forest --rot).")
        self.angle.valueChanged.connect(lambda _v: self._handles_changed())
        row.addWidget(self.angle)
        row.addWidget(widgets.role_label("Spread", "caption"))
        self.spread = QDoubleSpinBox()
        self.spread.setRange(1.0, IN.FOREST_SPREAD_MAX)    # the law's ceiling is the handle's stop
        self.spread.setSingleStep(FE.SPREAD_STEP)
        self.spread.setDecimals(2)
        self.spread.setSuffix("×")
        self.spread.setAccessibleName("Forest spread")
        self.spread.setToolTip(f"Widen the canopy in plan, heights kept (world-forest --spread). It stops at "
                               f"×{IN.FOREST_SPREAD_MAX:g}, the widest judged in game.")
        self.spread.valueChanged.connect(lambda _v: self._handles_changed())
        row.addWidget(self.spread)

    def donor(self):
        """The picked donor block ``(bx, by)`` (the combo holds it as the ``--donor`` spelling: PySide's findData
        does not match tuple data reliably)."""
        return tuple(int(v) for v in str(self.donor_box.currentData()).split(","))

    def _cmd(self, target, *, dry_run, report=None):
        return self.FE.command(target, self.center, self.donor(), spread=self.spread.value(),
                               rot_deg=self.angle.value(), dry_run=dry_run, report=report)

    def _shape(self, ol, ground_y):
        return self.FE.placed(ol, self.center, spread=self.spread.value(), rot_deg=self.angle.value(),
                              ground_y=ground_y)

    def _preview_at(self, ol, rim):
        return self.FE.footprint_preview(self._ix, rim[:, [0, 2]])

    def _pass_text(self, v, where):
        r = v.get("report") or {}
        return (f"Passes every gate {where}: {r.get('blob_tris')} canopy triangles, {r.get('dropped')} island "
                f"triangles carved, {r.get('zip_tris')} in the grass zip; wall rise {r.get('wall_rise')} (the "
                "ceiling is 2.34). Accept writes it to the draft.", "ok")

    def _preview_text(self, pv):
        if pv["why"] == "no island here":
            return (f"Not on an island in {self.target().name}: the forest carries onto deployed kit islands only.",
                    "warn")
        return (f"Not here: the footprint reaches {pv['why']}. A forest needs open grass under its whole rim, clear "
                "of the coast.", "warn")
