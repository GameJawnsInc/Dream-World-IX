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
from PySide6.QtCore import QObject, QProcess, Qt, QTimer, Signal
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
              "census": "the placement census", "error": "the carve", "ring": "the ring accounting",
              "weld": "the exact-weld law", "atlas": "the atlas gate", "skip": "the bank skip law"}
WHOLE_MAP = ((768.0, -640.0), 767.0)    # read_deployed_blocks' near/reach that spans all 24 columns once
SEAM_MAP = ((0.0, -640.0), 767.0)       # ...the same 24 columns read across x = 0: columns 12-23 west of it, unwrapped
WORLD_W = 1536.0                        # the world's width: x wraps here (24 columns of 64u)
SEAM_BAND = 384.0                       # a centre this near x = 0 is judged in the seam frame (each frame's own cut,
                                        # x = 0/1536 east, x = +-768 seam, then lies 384u+ from every shape)


def seam_frame(x) -> bool:
    """Is a centre at world ``x`` (folded into [0, 1536)) judged in the seam frame, the soup read across x = 0?"""
    return x < SEAM_BAND or x >= WORLD_W - SEAM_BAND


def frame_x(x) -> float:
    """World ``x`` (folded) as its frame spells it: the seam frame runs [-768, 768), the east frame [0, 1536)."""
    return x - WORLD_W if seam_frame(x) and x >= WORLD_W / 2.0 else x


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

        def failed(err):                                 # no finished signal comes for a start that failed: the
            if err == QProcess.ProcessError.FailedToStart and self.proc is proc:   # job ends here, as a failed one
                self.proc = None                         # (it stayed busy, and a card's write never ended:
                done(-1, f"the job could not start: {proc.errorString()}")      # review of the C19 fixes, round 5)
        proc.finished.connect(fin)
        proc.errorOccurred.connect(failed)
        self.proc = proc
        self._failed = failed
        proc.start(str(argv[0]), [str(a) for a in argv[1:]])

    def kill(self):
        proc, self.proc = self.proc, None
        if proc is not None and proc.state() != QProcess.ProcessState.NotRunning:
            proc.finished.disconnect()
            proc.kill()
            proc.waitForFinished(2000)

    def busy(self):
        return self.proc is not None

    def wait(self, msecs=120000) -> bool:
        """Block until the running job ends and its ``done`` has run (the Workspace closing: a job writing the live
        folder runs to its end, never killed half way). True when it ended; ``done`` may have started the next job,
        so ``busy()`` after it says nothing about this one."""
        proc = self.proc
        if proc is None:
            return True
        ended = bool(proc.waitForFinished(msecs))
        if self.proc is proc and proc.state() == QProcess.ProcessState.NotRunning                 and proc.error() == QProcess.ProcessError.FailedToStart:
            self._failed(QProcess.ProcessError.FailedToStart)    # (its errorOccurred not delivered yet)
        return ended or proc.state() == QProcess.ProcessState.NotRunning


def _no_window() -> int:
    """``CREATE_NO_WINDOW`` when this process has no console (the Workspace runs windowless): QProcess's own rule, so
    a job opens no console window. 0 elsewhere."""
    if sys.platform != "win32":
        return 0
    import ctypes
    return 0 if ctypes.windll.kernel32.GetConsoleWindow() else subprocess.CREATE_NO_WINDOW


def _run_done(done, *args):
    """Run a job's or a step's done; one that raises is reported, never let out of ``wait()``: the Workspace closing
    waits every writing job one after another, and a done that raised left that loop with the next job never
    waited for (QProcessRunner's done ran inside Qt's emission, which reported it: review of the perf commits, J2)."""
    try:
        done(*args)
    except Exception:                                    # noqa: BLE001 -- reported as an unhandled error is
        sys.excepthook(*sys.exc_info())


class JobRunner(QObject):
    """The cards' and the recipe bar's runner: one job at a time, its process started and waited for on a worker
    thread (``subprocess.Popen``, stdout and stderr merged), ``done(code, text)`` back on the window's thread. A
    process started on the GUI thread froze the window 0.5-1.2 s in bursts, inside the start itself (QProcess.start;
    PERF.md tier 2). The contract is :class:`QProcessRunner`'s: ``kill`` ends a job without its done, ``wait`` blocks
    until it ends and runs its done there, and a program that cannot start ends as a failed job."""

    _ended = Signal(object)                              # the job (a dict) whose result is in

    def __init__(self):
        super().__init__()
        self._job = None                                 # the running job, until its done is handed back or it is killed
        self._ended.connect(self._deliver, Qt.ConnectionType.QueuedConnection)

    def start(self, argv, cwd, done):
        self.kill()
        job = {"argv": [str(a) for a in argv], "cwd": str(cwd), "done": done, "proc": None, "result": None,
               "killed": False, "delivered": False}
        job["thread"] = threading.Thread(target=self._run, args=(job,), daemon=True)
        self._job = job
        job["thread"].start()

    def _run(self, job):                                 # (the worker: touches only its job)
        # the output goes to a FILE: done follows the job's own exit, where a pipe's EOF waited for every process
        # that inherited its write end -- a QProcess the shell started meanwhile, a child the job left running
        # (review of the perf commits, J1)
        out = None
        try:
            try:                                         # (the file too: a job always ends -- review round 2)
                out = tempfile.TemporaryFile()
                proc = subprocess.Popen(job["argv"], cwd=job["cwd"], stdin=subprocess.DEVNULL, stdout=out,
                                        stderr=subprocess.STDOUT, creationflags=_no_window())
            except Exception as e:                       # noqa: BLE001 -- any failed start ends the job (review, J4)
                job["result"] = (-1, f"the job could not start: {e}")
            else:
                job["proc"] = proc
                if job["killed"]:                        # (kill ran between the start and this line)
                    proc.kill()
                code = proc.wait()
                try:
                    out.seek(0)
                    text = out.read().decode("utf-8", "replace")
                except Exception as e:                   # noqa: BLE001 -- the job ended; its words could not be read
                    text = f"(the job's output could not be read: {e})"
                job["result"] = (code, text)
        except Exception as e:                           # noqa: BLE001 -- whatever broke, the job ends, failed
            job["result"] = job["result"] or (-1, f"the job failed in its runner: {e}")
        finally:
            if out is not None:
                try:
                    out.close()
                except OSError:
                    pass
            try:
                self._ended.emit(job)
            except RuntimeError:                         # the runner died with its window
                pass

    def _deliver(self, job):
        if job is not self._job or job["delivered"] or job["killed"] or job["result"] is None:
            return
        job["delivered"] = True
        self._job = None
        _run_done(job["done"], *job["result"])

    def kill(self):
        job, self._job = self._job, None
        if job is None:
            return
        job["killed"] = True
        proc = job["proc"]
        if proc is not None and proc.poll() is None:
            proc.kill()
        job["thread"].join(2.0)

    def busy(self):
        return self._job is not None

    def wait(self, msecs=120000) -> bool:
        """Block until the running job ends and its ``done`` has run (the Workspace closing: a job writing the live
        folder runs to its end, never killed half way). True when it ended; ``done`` may have started the next job,
        so ``busy()`` after it says nothing about this one."""
        job = self._job
        if job is None:
            return True
        job["thread"].join(msecs / 1000.0)
        if job["thread"].is_alive():
            return False
        self._deliver(job)                               # its done runs now; the queued delivery then finds it done
        return True


class StepWorker(QObject):
    """A card's draft bookkeeping -- an Accept's history snapshot and its record -- on a worker thread, one at a time,
    ``done(result, error)`` back on the window's thread; inline with ``sync`` (the test and snap lane). A whole-map
    step (a sink's) froze the window 1.7-2.4 s with warm files and 7-12 s with a fresh draft's (PERF.md tier 2).
    Never killed: a step cut half way leaves the draft without its record, so ``wait`` (the card closing, the
    Workspace closing) blocks until it ends and runs its done there."""

    _ended = Signal(object)

    def __init__(self, *, sync=False):
        super().__init__()
        self._sync, self._job = sync, None
        self._ended.connect(self._deliver, Qt.ConnectionType.QueuedConnection)

    def start(self, fn, done):
        job = {"fn": fn, "done": done, "out": None, "delivered": False}
        self._job = job
        if self._sync:
            self._run(job, emit=False)
            self._deliver(job)
            return
        job["thread"] = threading.Thread(target=self._run, args=(job,), daemon=True)
        job["thread"].start()

    def _run(self, job, emit=True):
        try:
            job["out"] = (job["fn"](), None)
        except Exception as e:                           # noqa: BLE001 -- handed to done, on the window's thread
            job["out"] = (None, e)
        if emit:
            try:
                self._ended.emit(job)
            except RuntimeError:                         # the card died with its window
                pass

    def _deliver(self, job):
        if job is not self._job or job["delivered"] or job["out"] is None:
            return
        job["delivered"] = True
        self._job = None
        _run_done(job["done"], *job["out"])

    def busy(self):
        return self._job is not None

    def wait(self, msecs=120000) -> bool:
        job = self._job
        if job is None:
            return True
        if "thread" in job:
            job["thread"].join(msecs / 1000.0)
            if job["thread"].is_alive():
                return False
        self._deliver(job)
        return True


class CarryTool(QWidget):
    """A carry card under the 3D view. ``panel`` is the World tab's :class:`WorldView3DPanel`; ``source_fn()`` the
    mod folder the tab shows; ``game_fn()`` the install; ``on_changed(draft)`` re-reads the view after an Accept
    or a discard. ``on_reload(x, z)`` (dev checkout: the shell's world reload) makes the running game re-read the
    world after a Promote. ``runner``, ``drafts_root``, ``ask``, ``outline_fn(donor)``, ``soup_fn(folder)`` (an
    island ``SoupIndex``) and ``sync`` (background reads inline) are the test and snap seams; ``seam_soup_fn(folder)``
    is the soup read across x = 0 (none when only ``soup_fn`` is injected: that card keeps to the east frame).

    THE SEAM (rung C10): a soup read in [0, 1536) is cut at x = 0, so a shape there met no ground under its west
    half. ``center`` is always folded into [0, 1536), as the verbs spell it; a centre within ``SEAM_BAND`` of x = 0 is
    judged in the SEAM FRAME, a second whole-map soup read across x = 0 (``SEAM_MAP``: columns 12-23 west of it,
    unwrapped, as the verbs' own read window keys them), and the ghost and the cheap laws use :meth:`fcenter`, the
    centre as that frame spells it. The view draws the seam twice (``worldview3d.seam_copies``), so the ghost stands
    on the island at either end.

    A subclass names its shape (``TITLE``, ``NOUN``, ``PART``, ``VERB``, ``GATES``) and supplies the parts that
    differ: ``_edit_module``, ``_build_handles``, ``donor``, ``_cmd``, ``_shape``, ``_preview_at``, ``_pass_text``
    and ``_preview_text``.

    A card whose verb has a handle table (``world/handles.py``, rung B2) names it in ``HANDLE_TABLE`` and maps every
    handle on the table's gui surface in ``HANDLES``: to the widget attribute that sets it, or to the rule (prose)
    that does. Its spins stop where the table says (:meth:`_fit`); the fence holds the map to the table.

    EDITING A PLACED STEP (rung C9): a card that can set its handles from a recipe row (:meth:`load_row`) opens on a
    placed step's row (:meth:`edit_row`), the recipe bar having lifted the step and the ones after it out of the
    draft; Accept writes the edited shape in the step's place and hands back (``on_accepted``), and Cancel edit or
    closing the card puts the draft back (``on_cancel``). Promote, Revert and Discard wait while an edit is open.

    A card whose handles wait on a read (the sink's island list, a coast block's windows, the river's shape: rung C12)
    holds the row (``_pending_row``) and seats it when the read comes in (:meth:`_seat_row`). Seated, the handles must
    say the row back exactly (:meth:`_said_back`: an edit that changes nothing changes nothing); a row they cannot
    say refuses the edit (``on_cancel(note)``) and the draft goes back."""

    TITLE, NOUN, PART, VERB = "Shape", "shape", "shape", "world-?"
    GATES = GATE_WORDS
    HANDLE_TABLE = None                                  # the verb's table in world/handles.py, when it has one
    HANDLES = {}                                         # handle -> the widget attribute, or the rule, that sets it
    _extra_rows = ()
    CHECK_TIME = "about seven seconds"                   # a passing world-forest dry run, measured (C1)
    _bg_done = Signal(str, int, object, object)          # (what, serial, result, error) from a worker thread
    opened = Signal(bool)                                # the card opened (True) or was put away (False)
    writing_changed = Signal(bool)                       # a job that writes started (True) or ended (False)

    def __init__(self, pal, panel, *, game_fn, source_fn, on_changed=None, runner=None, drafts_root=None,
                 ask=None, outline_fn=None, soup_fn=None, sync=False, on_reload=None, seam_soup_fn=None):
        super().__init__()
        self.FE = FE = self._edit_module()
        self.pal, self.panel = pal, panel
        self._game_fn, self._source_fn, self._on_changed = game_fn, source_fn, on_changed
        self._runner = runner or JobRunner()
        self._drafts_root = drafts_root
        self._ask = ask or self._ask_dialog
        self._outline_fn = outline_fn or (lambda donor: FE.outline(donor, game=self._game_fn()))
        self._soup_fn = soup_fn or self._read_soup
        # an injected soup is in one frame only: no seam frame then, unless the seam's own soup is injected too
        self._seam_soup_fn = seam_soup_fn or (None if soup_fn else (lambda folder: self._read_soup(folder, seam=True)))
        self._sync = sync
        self._steps = StepWorker(sync=sync)              # an Accept's history step, off the window's thread
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
        self._seam = False                               # the frame _ix is read in: across x = 0 (True) or not
        self._soups = {}                                 # (folder, seam) -> SoupIndex, until the island changes
        self._soup_gen = 0                               # which island the soups read: _drop_soups moves it on
        self._preview = None                             # the last preview
        self._ghost = None                               # (tris, rim) of the drawn ghost
        self._verdict = None                             # (handles key, verdict dict) of the last finished job
        self._job = None                                 # ("check" | "accept", key) while one runs
        self._editing = None                             # (label, on_accepted, on_cancel) while editing a placed step
        self._pending_row = None                         # a row to edit, waiting on the card's read to seat it
        self._seating = False
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
        self.title_lbl = widgets.role_label(self.TITLE, "cardtitle")
        row.addWidget(self.title_lbl)
        self._build_handles(row)
        row.addStretch(1)
        self.close_btn = QPushButton("Close")
        self.close_btn.setProperty("role", "quiet")
        self.close_btn.setToolTip(f"Put the {self.NOUN} tool away (the draft keeps what you accepted).")
        self.close_btn.clicked.connect(self.close_tool)
        self.writing_changed.connect(lambda _on: self._sync_buttons())   # Close / Cancel edit wait for a write
        row.addWidget(self.close_btn)
        card.addLayout(row)
        for extra in self._extra_rows:                   # handles that would widen the first row past the window
            card.addLayout(extra)
        self.verdict_lbl = QLabel()
        self.verdict_lbl.setProperty("role", "banner")
        self.verdict_lbl.setWordWrap(True)
        self.verdict_lbl.setAccessibleName(f"{self.TITLE} verdict")
        card.addWidget(self.verdict_lbl)
        brow = self.accept_row = QHBoxLayout()
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
        self.discard_btn = QPushButton("Discard draft")
        self.discard_btn.setProperty("role", "quiet")
        self.discard_btn.setToolTip("Delete the draft and everything accepted into it.")
        self.discard_btn.clicked.connect(self._discard)
        brow.addWidget(self.discard_btn)
        brow.addStretch(1)
        card.addLayout(brow)
        # The draft line, then rung C4's actions beside it: the draft into the live folder (world-promote: refuses
        # over another deploy's bytes, backs up and ledgers each write, mirrors disc 4, snapshots first so Revert is
        # exact), then the game follows. Two rows, because one row of Accept, Copy, the draft line, Promote, Revert,
        # Show and Discard floored the window at 1348px at 150%; and the line wraps here beside at most three
        # buttons, not squeezed between five (three lines at 150%, clipped in a 1280x850 window).
        brow = self.draft_row = QHBoxLayout()
        brow.setSpacing(8)
        self.draft_lbl = widgets.role_label("", "caption")
        self.draft_lbl.setWordWrap(True)
        self.draft_lbl.setAccessibleName("Draft")
        brow.addWidget(self.draft_lbl, 1)
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
        card.addLayout(brow)
        self._say(f"Click the map where the {self.NOUN} goes. Drag its ghost to move it.", "")
        self._sync_buttons()

    # -- the handle table --
    def _handle(self, name):
        from ..world import handles as HD
        return HD.handle(self.HANDLE_TABLE, name)

    def _fit(self, spin, name):
        """Set ``spin``'s stops to the handle's range in the table (an angle wraps: its top is its bottom again), and
        return the top (the verb's ceiling, for the tooltip)."""
        h = self._handle(name)
        lo, top = h.range()
        if h.wraps:
            spin.setRange(int(lo), int(top) - 1)
            spin.setWrapping(True)
        else:
            spin.setRange(lo, top)
        return top

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

    def _accept_calls(self, draft, report, report4):
        """Accept's commands (after ``python -m ff9mapkit``), run in order: one call by default. A verb whose disc-4
        step is a REPLAY (the sink, the coast morphs) adds the replay's own call, which a draft cannot make itself
        (``world.sinkedit``: THE DRAFT'S DISC-4 HALF); the first call's verdict is the step's."""
        return [self._cmd(draft, dry_run=False, report=report)]

    def _step_cells(self, verdict):
        """The cells an Accept may write (the history snapshots them first): the dry run's own blocks."""
        from ..world import recipe as RC
        return [tuple(b) for b in (verdict or {}).get("blocks") or []] or RC.row_cells(self.row())

    def _show_point(self, v):
        """Where Show in game puts the party after this accepted verdict (the shape's centre)."""
        return tuple(v["center"]) if v.get("center") else None

    def _outline_loaded(self, donor, ol):
        """A donor's outline arrived (a subclass may set a handle from it)."""

    def _read_failed(self, what, err):
        """A read the card needs failed (``what``: "island", or the card's PART); a card holding a row on it refuses the
        edit (MountainTool)."""

    def load_row(self, row):
        """Set the handles from a recipe row of this card's table and place the ghost there (rung C9); a row the
        handles cannot say raises ValueError, naming what. A card that must read first holds the row in
        ``_pending_row`` and calls :meth:`_try_seat`."""
        raise ValueError(f"the {self.NOUN} card cannot open a placed step")

    def _seat_row(self, row):
        """Seat a held row: set the handles that waited on a read. False while the read is not in; ValueError when the
        row is not one the handles can say."""
        return True

    def _try_seat(self):
        """Seat the held row if its read is in, and hold the handles to it. A refusal raises while the card is being
        opened (the bar reports it), and once the edit is open it cancels the edit with the reason."""
        row = self._pending_row
        if row is None or self._seating:                 # seating sets handles, and a handle asks for the read again
            return
        self._seating = True
        try:
            if not self._seat_row(row):
                return
            self._pending_row = None
            self._said_back(row)
        except ValueError as e:
            self._pending_row = None
            if self._editing is None:
                raise
            self._refuse_edit(str(e))
        finally:
            self._seating = False

    def _said_back(self, row, mine=None):
        """Raise ValueError unless the handles build ``row`` again, key for key, both as the editor writes a row
        (``recipe.canon``: a default spelled out or a full turn is the same step)."""
        from ..world import recipe as RC
        mine, row = RC.canon(self.row() if mine is None else mine), RC.canon(row)
        diff = sorted(k for k in set(mine) | set(row) if mine.get(k) != row.get(k))
        if diff:
            raise ValueError(f"the card would not say its {', '.join(diff)} back as the step has "
                             + ("it" if len(diff) == 1 else "them"))

    # -- editing a placed step (rung C9) --
    def edit_row(self, row, *, label, on_accepted, on_cancel):
        """Open on a placed step: its row's handles, judged against the draft as it was before the step."""
        self._editing = None
        self._pending_row = None
        self.load_row(row)
        if self._pending_row is None:
            self._said_back(row)
        self._editing = (label, on_accepted, on_cancel)
        self.title_lbl.setText(f"Edit {self.NOUN}")
        self.title_lbl.setToolTip(f"Editing the placed step {label}: move, turn or retune it, then Accept the edit.")
        self.accept_btn.setText("Accept the edit")
        self.accept_btn.setToolTip(f"Write the edited {self.NOUN} in the step's place ({self.VERB} against the draft), "
                                   "then put the steps after it back on top.")
        self.close_btn.setText("Cancel edit")
        self.close_btn.setToolTip("Put the draft back exactly as it was before this edit.")
        self._sync_buttons()

    def editing(self):
        return self._editing is not None

    def _refuse_edit(self, why):
        """The open edit's row turned out, once the card's read came in, not to be one its handles can say: put the
        card away and the draft back, saying why."""
        cancel = self._editing[2]
        self._end_edit()
        self.close_tool()
        cancel(f"Not opened in its card: {why}. Delete still works.")

    def _end_edit(self):
        """Leave edit mode (the handover or the cancel is the caller's)."""
        self._editing = None
        self.title_lbl.setText(self.TITLE)
        self.title_lbl.setToolTip("")
        self.accept_btn.setText("Accept into draft")
        self.accept_btn.setToolTip(f"Write this {self.NOUN} into the draft ({self.VERB} without --dry-run, against "
                                   "the draft folder). The install is not touched.")
        self.close_btn.setText("Close")
        self.close_btn.setToolTip(f"Put the {self.NOUN} tool away (the draft keeps what you accepted).")

    # -- the folders --
    def source(self) -> Path:
        return Path(self._source_fn())

    def draft(self):
        """The source's draft folder if one was made, else None."""
        from ..world import draft as D
        p = D.draft_path(self.source(), root=self._drafts_root)
        return p if D.is_draft(p) else None             # (a stat while draft.json stands: PERF.md 7)

    def target(self) -> Path:
        """Where the shape is judged and written: the draft once it exists, else the source (read only)."""
        return self.draft() or self.source()

    # -- lifecycle --
    def open_tool(self):
        self.show()
        self.opened.emit(True)
        self._drop_soups()                               # the other tool may have written the draft meanwhile
        self._refresh_draft_label()
        self._load_soup()
        self._load_outline(self.donor())

    @property
    def _job(self):
        """``(kind, key)`` of the running job, or None; setting it says when a job that writes starts or ends."""
        return self.__dict__.get("_job_v")

    @_job.setter
    def _job(self, v):
        was = self.writing()
        self.__dict__["_job_v"] = v
        if self.writing() != was:
            self.writing_changed.emit(not was)

    def close_tool(self):
        """Put the card away. A job that writes (Accept, Promote, Revert promote) is waited for, never killed: a
        Promote cut off half way leaves the live folder half written with no record to revert from (review of the
        C19 fixes, third round). A Check, a dry run, is killed."""
        self._timer.stop()
        self.finish_writes()                             # (its done runs: an Accept's may close this card itself)
        self._runner.kill()
        self._job = None
        self._pending_row = None
        if self._editing is not None:                    # closing an edit cancels it: the draft goes back
            cancel = self._editing[2]
            self._end_edit()
            cancel()
        self.center = self._ghost = None
        self.panel.set_overlays([])
        self.panel.set_ghost(None)
        self.hide()
        self.opened.emit(False)

    def finish_writes(self):
        """Wait for the card's write to end, every call of it: a two-call Accept (the sink's, the coast morph's: disc
        1, then disc 4's replay) starts its second call in the first's end, and waiting for one then killing the runner
        cut the disc-4 call (review of the C19 fixes, fourth round)."""
        wait = getattr(self._runner, "wait", None)
        for _ in range(64):                              # (bounded: a runner that never ends must not spin the GUI)
            if not self.writing():
                break
            if self._steps.busy():                       # an Accept's snapshot or record: its end starts the next leg
                if not self._steps.wait():
                    break
                continue
            if wait is None or not self._runner.busy() or not wait():
                break

    def writing(self) -> bool:
        """A job of this card writes the draft or the live folder now (Accept, Promote, Revert promote, the draft's
        copy): closing the card would kill it half way."""
        return self._job is not None and self._job[0] != "check"

    def closing_runner(self):
        """The Workspace is closing (``WorldDoc.shutdown``): a Check, a dry run that writes nothing, stops; the runner of
        a job that writes (Accept, Promote, Revert promote) is handed back to be waited for. None when nothing runs."""
        if self._job is not None and self._job[0] == "check":
            self._runner.kill()
            self._job = None
            return None
        if self._steps.busy():                           # an Accept's history step (its end may start a job)
            return self._steps
        return self._runner if self._runner.busy() else None

    def handles(self):
        """The handles as the command spells them: the stale guard every verdict is matched against."""
        if self.center is None:
            return None
        return tuple(self._cmd("-", dry_run=False))

    def row(self) -> dict:
        """The recipe row Accept records (rung C3): parsed from the very command it runs."""
        from ..world import recipe as RC
        return RC.row_for(self._cmd("-", dry_run=False))

    def island_changed(self):
        """The draft moved under the tool (an Accept, an undo, a redo, an opened recipe): read the island and the
        draft again. A hidden card only forgets: it reads both when it opens, and its line's walk of the draft cost
        every change 1-9 s on a worker for a label nobody saw (PERF.md 2)."""
        self._drop_soups()
        self._verdict = None
        if not self.isHidden():
            self._refresh_draft_label()
            self._load_soup()

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

    def _read_soup(self, folder, seam=False):
        """Every deployed Terrain block of ``folder`` as one island soup (about half a second for 94 blocks), read in
        [0, 1536) or, ``seam``, across x = 0 (the verbs' own unwrapped window: one contiguous frame there)."""
        from ..world import interior as IN
        (near, reach) = SEAM_MAP if seam else WHOLE_MAP
        blocks = IN.read_deployed_blocks(str(folder), near=near, reach=reach, game=self._game_fn())
        return self.FE.SoupIndex(IN.soup_from_blocks(blocks))

    def _drop_soups(self):
        """The island changed: every cached soup is stale, and so is every read still running (its path is the same
        and its bytes are not: a read begun before an Edit lifted the step out decided the held row's ground --
        review of the C12 fixes)."""
        self._soups = {}
        self._ix = self._ix_for = None
        self._soup_gen += 1
        self._soup_reading = set()

    def _load_soup(self):
        """Both frames' soups (:meth:`_read_frames`)."""
        self._read_frames()

    def _read_frames(self):
        """Both frames' soups, each from the cache or read on a worker: the current frame's first -- the one the
        preview reads -- and the other frame's once it lands, so a click near x = 0 seldom waits for one. Read at
        once, the two fought for the GIL and the preview's landed at 1.5-1.9 s instead of 0.8 (PERF.md 7)."""
        target = self.target()
        reading = self.__dict__.setdefault("_soup_reading", set())
        for seam in (self._seam, not self._seam):
            if seam and self._seam_soup_fn is None:
                continue
            if (target, seam) in self._soups:
                if seam == self._seam:
                    self._ix, self._ix_for = self._soups[(target, seam)], target
                continue
            if (target, seam, self._soup_gen) in reading:
                if seam == self._seam:
                    return                                   # the preview's frame is on its way: then the other
                continue
            if seam != self._seam and (target, self._seam, self._soup_gen) in reading:
                return                                       # (the other frame waits for the preview's)
            reading.add((target, seam, self._soup_gen))
            fn = self._seam_soup_fn if seam else self._soup_fn

            def read(fn=fn, seam=seam, gen=self._soup_gen):  # its error carries its generation and frame too: a
                try:                                         # stale read's failure must not wipe the live island
                    return (gen, target, seam, fn(target))
                except Exception as e:                       # noqa: BLE001 -- surfaced on the GUI thread
                    return (gen, target, seam, e)
            self._bg("soup", read)
            if seam == self._seam:
                return                                       # the other frame's read starts when this one lands

    def fcenter(self):
        """The centre as the current soup's frame spells it (the ghost and the cheap laws); ``center`` is the folded
        centre the command and the row name."""
        if self.center is None:
            return None
        return (frame_x(self.center[0]) if self._seam else self.center[0], self.center[1])

    def _set_center(self, x, z):
        """Put the centre at world ``(x, z)``, folded into [0, 1536) (a pick on the view's seam copy, a drag across
        the seam), and judge it in its frame: a frame change swaps the soup (read once per frame)."""
        step = self.FE.CENTRE_STEP
        self.center = ((round(x / step) * step) % WORLD_W, round(z / step) * step)
        seam = seam_frame(self.center[0]) and self._seam_soup_fn is not None
        if seam != self._seam:
            self._seam = seam
            self._ix = self._ix_for = None
            self._load_soup()

    def _load_outline(self, donor):
        if donor in self._outlines:
            self._outline_loaded(donor, self._outlines[donor])
            return
        def read():                                      # its error names its donor too: a failed read of another
            try:                                         # massif cancelled a held row's edit (review of the C12
                return (donor, self._outline_fn(donor))  # fixes, fifth round)
            except Exception as e:                       # noqa: BLE001 -- surfaced on the GUI thread
                return (donor, e)
        self._bg("outline", read)

    def _on_bg(self, what, _serial, result, err):
        if err is not None:
            if what == "soup":
                self._ix, self._ix_for = None, None
                self._say(f"The island could not be read: {err}", "error")
                self._read_failed("island", err)
            elif what == "outline":
                self._say(f"The {self.PART} could not be read: {err}", "error")
                self._read_failed(self.PART, err)
            elif what == "draft":
                self._job = None
                self._say(f"The draft could not be made: {err}", "error")
                self._sync_buttons()
            return
        if what == "soup":
            gen, target, seam, ix = result
            if gen != self._soup_gen:
                return                                   # begun before the island changed: not the island now
            self.__dict__.setdefault("_soup_reading", set()).discard((target, seam, gen))
            if not isinstance(ix, Exception) and not self.isHidden():
                self._soups.setdefault((target, seam), ix)
                self._read_frames()                      # the other frame's turn (a cached one only fills the ix)
            if isinstance(ix, Exception):
                if (target, seam) == (self.target(), self._seam):
                    self._ix, self._ix_for = None, None
                    self._say(f"The island could not be read: {ix}", "error")
                    self._read_failed("island", ix)
                return
            self._soups[(target, seam)] = ix
            if (target, seam) != (self.target(), self._seam):
                return                                   # a frame (or a draft) the tool has moved off meanwhile
            self._ix_for, self._ix = target, ix
        elif what == "outline":
            donor, ol = result
            if isinstance(ol, Exception):
                if donor == self.donor():
                    self._say(f"The {self.PART} could not be read: {ol}", "error")
                    self._read_failed(self.PART, ol)
                return
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
        self._set_center(x, z)
        self._pick_y = float(y)
        self._handles_changed()

    def drag_to(self, x, z):
        self._set_center(x, z)
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
        self.panel.set_ghost({"center": self.fcenter(), "y": gy, "poly": rim[:, [0, 2]]})
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
        self.close_btn.setEnabled(not self.writing())    # a write is never cut off (Cancel edit would accept it)
        has_draft = self.draft() is not None
        edited, last = self._draft_state if has_draft else (0, None)
        free = self._editing is None                     # an open edit holds the draft: these wait for it
        self.discard_btn.setVisible(has_draft and free)
        self.discard_btn.setEnabled(self._job is None)
        self.promote_btn.setVisible(has_draft and edited > 0 and free)
        self.promote_btn.setEnabled(self._job is None)
        self.revert_btn.setVisible(last is not None and free)
        self.revert_btn.setEnabled(self._job is None)
        self.show_btn.setVisible(self._on_reload is not None and self._show_target() is not None and free)

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
        tmp = Path(tempfile.mkdtemp(prefix=f"ff9_{self.NOUN}_"))
        report = tmp / "verdict.json"
        if kind == "accept":
            calls = self._accept_calls(draft, report, tmp / "verdict4.json")
        else:
            calls = [self._cmd(draft, dry_run=True, report=report)]
        self._job = (kind, key)
        self._disc4 = None
        self._say(f"Checking every gate ({self.CHECK_TIME})…" if kind == "check"
                  else f"Writing the {self.NOUN} into the draft of {self.source().name}"
                       + (", disc 1 then disc 4…" if len(calls) > 1 else "…"), "")
        self._sync_buttons()
        if kind == "accept":                             # rung C3: the step's cells, snapshotted before it writes --
            from ..world import draft as D               # on a worker; the card writes from here (PERF.md tier 2)
            cells = self._step_cells(self._current_verdict())
            self._steps.start(lambda: D.begin_step(draft, cells),
                              lambda _r, err: self._snapshotted(kind, key, calls, report, tmp, err))
            return
        self._launch(kind, key, calls, report, tmp)

    def _snapshotted(self, kind, key, calls, report, tmp, err):
        if self._job != (kind, key):
            return
        if err is not None:                              # nothing was written: the draft stands as it was
            self._job = None
            self._say(f"Not written: the draft's history could not be snapshotted ({err}).", "error")
            self._sync_buttons()
            return
        self._launch(kind, key, calls, report, tmp)

    def _launch(self, kind, key, calls, report, tmp):
        pre = [sys.executable, "-m", "ff9mapkit", "--game", str(self._game_fn())]

        def step(k, code, text):
            if self._job != (kind, key):
                return
            if k == 0 and len(calls) > 1:                # the first call's verdict decides; the rest follow it
                v = self.FE.read_verdict(report)
                if v is not None and v.get("ok"):
                    self._runner.start(pre + calls[1], kit_cwd(), lambda c, t: step(1, c, t))
                    return
            if k == 1:                                   # disc 4's own call: it passed, refused, or died (no verdict:
                v4 = self.FE.read_verdict(tmp / "verdict4.json")   # it may have written, round 3 H5)
                self._disc4 = "died" if v4 is None else bool(v4.get("ok"))
                code = 0
            self._job_done(kind, key, report, code, text)
        self._runner.start(pre + calls[0], kit_cwd(), lambda code, text: step(0, code, text))

    def _job_done(self, kind, key, report, code, text):
        if self._job != (kind, key):
            return                                       # superseded (a handle moved, or the tool closed)
        v = self.FE.read_verdict(report)
        if v is None:
            last = [ln for ln in text.splitlines() if ln.strip()][-1:] or [f"exit code {code}"]
            v = {"ok": False, "dry_run": kind == "check", "died": True,      # (the verb may have written: H3)
                 "refused": {"gate": "error", "message": f"the job ended without a verdict: {last[0]}", "where": []}}
        if kind == "accept":                             # the step goes into the recipe, or back out of the draft,
            from ..world import draft as D               # on a worker: the card writes until it is recorded
            from ..world import recipe as RC
            d = self.draft()
            if v["ok"]:
                row = RC.row_for(list(key))           # the handles the job ran with, not the current ones
                work = lambda: D.commit_step(d, row, RC.label(row))   # noqa: E731
            else:
                work = lambda: D.abort_step(d)                       # noqa: E731
            self._steps.start(work, lambda _r, err: self._recorded(kind, key, v, err))
            return
        self._job = None
        self._verdict = (key, v)
        self._redraw()

    def _recorded(self, kind, key, v, err):
        if self._job != (kind, key):
            return
        if err is not None and v["ok"]:                  # a commit that failed leaves its step whole: taken back
            from ..world import draft as D               # now, not by whatever the user clicks next (round 3, H3)
            d = self.draft()
            self._steps.start(lambda: D.abort_step(d), lambda _r, err2: self._not_recorded(kind, key, err, err2))
            return
        self._job = None
        if err is not None and not v["ok"]:              # a refused Accept: nothing was written, only its pending
            self._verdict = (key, v)                     # snapshot stays (review of the perf commits, F1)
            self._redraw()
            if v.get("died"):                            # a verb that died may have written: never "unchanged" (H3)
                self._say(f"{self.verdict_lbl.text()} The draft may hold a half write: its history snapshot could not "
                          f"be put back ({err}), so it is taken back when the next step begins.", "error")
            else:
                self._say(f"{self.verdict_lbl.text()} The draft is unchanged, but its history snapshot could not be "
                          f"cleared ({err}).", "error")
            return
        self._verdict = (key, v)
        if kind == "accept" and v["ok"]:
            self._accepted(v)
            return
        self._redraw()

    def _not_recorded(self, kind, key, err, err2):
        if self._job != (kind, key):
            return
        self._job = None
        self._verdict = None
        way_out = ("Cancel edit, or Accept the edit again, takes it back first" if self._editing is not None else
                   "the next step, Undo, Redo or Promote takes it back first")   # (an open edit hides Undo: R4-4)
        self._say(f"Not written: its history step could not be recorded ({err}), so "
                  + ("the write was taken back and the draft is as it was." if err2 is None else
                     f"the write is in the draft until it can be taken back ({err2}): {way_out}."), "error")
        self._sync_buttons()

    def _accepted(self, v):
        disc4 = getattr(self, "_disc4", None)
        note = (" Disc 4 refused the same edit, so disc 4 keeps its own ground there (as the verb's replay would)."
                if disc4 is False else
                " Disc 4's call ended without a verdict, so disc 4 may hold a half write: Undo takes it back with "
                "the rest of the step." if disc4 == "died" else "")
        pt = self._show_point(v)
        if pt is not None:
            self._last_center = pt
        if self._editing is not None:                    # an edit: the bar puts the steps after it back, and says
            done = self._editing[1]                      # the note, the card closing here (round 4, R4-5)
            self._end_edit()
            self._verdict = None
            self.close_tool()
            done(note.strip()) if note else done()
            return
        import re
        # the blocks whose bytes changed (the read window is wider, and a sink writes several parts per block)
        written = v.get("written") or []
        n = len({m.groups() for m in (re.search(r"Block\[(\d+)\]\[(\d+)\]", str(p)) for p in written) if m}) \
            or len(written) or len(v.get("blocks") or [])  # (a mint's verdict names its blocks, not its files)
        self.center = self._ghost = None
        self._verdict = None
        self.panel.set_overlays([])
        self.panel.set_ghost(None)
        self._say(f"In the draft: {n} block{'s' if n != 1 else ''} written. The view now draws the draft in place "
                  f"of {self.source().name}. Click to place another {self.NOUN}." + note, "warn" if note else "ok")
        if self._on_changed is not None:                 # the tab reads the island and the draft line again, once,
            self._on_changed(self.draft())               # for every card (island_changed): reading them here too
        else:                                            # was thrown away by its generation bump (PERF.md 2)
            self.island_changed()

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
        self._drop_soups()                               # the live folder (and the draft) moved: read them again
        self._refresh_draft_label()
        self._load_soup()
        if self._on_changed is not None:                 # promoted: the game's stack has it; reverted: only the draft
            self._on_changed(None if kind == "promote" else self.draft())

    def _show_target(self):
        return self._last_center

    def _show_in_game(self):
        """The game re-reads the world and the party goes to the shape: the point folded onto the grid here, the one
        call site, since the engine's teleport refuses x/64 >= 24 and a carry across the seam is centred at 1536 or
        past it (review of C23)."""
        t = self._show_target()
        if t is not None and self._on_reload is not None:
            from ..world.frames import wrap_world_xz
            self._on_reload(*(float(c) for c in wrap_world_xz(*t)))

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
        self._drop_soups()
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
    HANDLE_TABLE = "forest"
    HANDLES = {"center": "the click (and the drag)", "donor": "donor_box", "rot": "angle", "spread": "spread"}

    def _edit_module(self):
        from ..world import forestedit
        return forestedit

    def _build_handles(self, row):
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
        self._fit(self.angle, "rot")
        self.angle.setSingleStep(5)
        self.angle.setSuffix("°")
        self.angle.setAccessibleName("Forest angle")
        self.angle.setToolTip("Turn the canopy about its centre, clockwise seen from above (world-forest --rot).")
        self.angle.valueChanged.connect(lambda _v: self._handles_changed())
        row.addWidget(self.angle)
        row.addWidget(widgets.role_label("Spread", "caption"))
        self.spread = QDoubleSpinBox()
        top = self._fit(self.spread, "spread")             # the law's ceiling is the handle's stop
        self.spread.setSingleStep(FE.SPREAD_STEP)
        self.spread.setDecimals(2)
        self.spread.setSuffix("×")
        self.spread.setAccessibleName("Forest spread")
        self.spread.setToolTip(f"Widen the canopy in plan, heights kept (world-forest --spread). It stops at "
                               f"×{top:g}, the widest judged in game.")
        self.spread.valueChanged.connect(lambda _v: self._handles_changed())
        row.addWidget(self.spread)

    def donor(self):
        """The picked donor block ``(bx, by)`` (the combo holds it as the ``--donor`` spelling: PySide's findData
        does not match tuple data reliably)."""
        return tuple(int(v) for v in str(self.donor_box.currentData()).split(","))

    def _cmd(self, target, *, dry_run, report=None):
        return self.FE.command(target, self.center, self.donor(), spread=self.spread.value(),
                               rot_deg=self.angle.value(), dry_run=dry_run, report=report)

    def load_row(self, row):
        ix = self.donor_box.findData(str(row["donor"]))
        if ix < 0:
            raise ValueError(f"its canopy {row['donor']} is not one the card lists")
        if float(row.get("reach", 96.0)) != 96.0:
            raise ValueError("its reach is not a handle of the card")
        self.donor_box.setCurrentIndex(ix)
        self.angle.setValue(int(round(float(row.get("rot", 0.0)))) % 360)
        self.spread.setValue(float(row.get("spread", 1.0)))
        self.place(*row["center"])

    def _shape(self, ol, ground_y):
        return self.FE.placed(ol, self.fcenter(), spread=self.spread.value(), rot_deg=self.angle.value(),
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
