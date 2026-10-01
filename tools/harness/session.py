#!/usr/bin/env python3
"""The harness driver: own an FF9 process, drive it, assert on what it does.

This is the half that runs outside the game. The half inside is memoria-patch s83
(``Memoria/Harness/HarnessAgent.cs``); the two meet over :mod:`tools.harness.channel`.

The shape of a scenario::

    from harness import Session

    with Session(label="chest") as g:
        g.newgame()
        g.warp(30810)
        g.walk("up", 45)
        g.press("confirm")
        g.expect_text("Potion")
        g.shot("after-chest")

Every wait is bounded and every failure carries the last known state, because the failure mode that
makes an automated harness worse than useless is one that hangs or reports a green run it never
actually observed.

PROCESS SAFETY. One FF9 install is shared by every concurrent worktree on this machine, and it is also
the machine the owner plays on. So the default refuses to start when an FF9 is already running rather
than racing it, and it only ever kills a process this session launched itself.
"""
from __future__ import annotations

import atexit
import collections
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))

from ff9mapkit.config import find_game_path                      # noqa: E402
from ff9mapkit.content.doorface import STEP_PER_CALL              # noqa: E402

from .artifacts import STATE_RING, StateRing, StepLog, build_env         # noqa: E402
from .channel import (ARM_CYCLE_TIMEOUT, BUTTONS, PROTOCOL, Channel, FightTimeout, HarnessError,   # noqa: E402
                      State, StepRefused)
from .logs import (MEMORIA_LOG, PARSERS, UNITY_LOG, UNITY_LOG_PATH,     # noqa: E402
                   LogException, frame_after, line_start_offset, read_from, split_lines)
from .tickrate import CALLS_PER_TICK, TAIL_TICKS, Rate, TickClock, read_field_tps   # noqa: E402

REPO = Path(__file__).resolve().parents[2]
RUNS = REPO / ".harness-runs"

#: How long to wait for a launched game to boot far enough to publish its first state. Generous: a cold
#: start pays Steam, the Memoria patcher and the p0data mount before a single frame renders.
BOOT_TIMEOUT = 240.0

#: Seconds to hold on the title screen before starting a new game. The title appears while Memoria is
#: still loading, and starting during that window makes the opening cutscene stutter badly -- owner
#: -observed. Costs nothing on a scenario that warps away, so it is the default rather than a flag.
TITLE_SETTLE = 10.0

#: Window size for a harness launch. Deliberately modest: the harness reads state and captures frames
#: from inside the engine, so a big window buys nothing and costs GPU, boot time and your screen.
DEFAULT_SIZE = (1280, 720)

#: Highest legal field id. `fldMapNo` is Int16, so anything above this wraps to a different (possibly
#: REAL) field, and a wait for the id you asked for can never be satisfied.
MAX_FIELD_ID = 32767

#: Where FF9 (Steam) keeps the player's saves. Unity's persistentDataPath under LocalLow. The
#: harness never writes here -- it BACKS IT UP and then asserts the engine sandboxed away from it.
PLAYER_SAVE_DIR = Path(os.path.expandvars(
    r"%USERPROFILE%\AppData\LocalLow\SquareEnix\FINAL FANTASY IX\Steam\EncryptedSavedData"))

#: A published document this recent counts as a LIVE game talking. The agent republishes every 2nd frame --
#: 15 to 30 times a second, as the harness renders at ~31 or ~60 fps (harness.tickrate) -- so anything older
#: is a photograph -- and a photograph satisfies most predicates just as well as a running game does.
LIVE_WITHIN = 2.0

#: How long state.json may stay unreadable before the CHANNEL, not one read, is called dead. A single
#: `Channel.state()` of None is not that: the agent rewrites the file in place, so it is EMPTY between
#: the truncate and the bytes, and MEASURED 2026-09-23 that gap reaches ~80 ms at p99 and ~200 ms at
#: worst against the channel's own ~30 ms parse retry. Five times the worst gap, and the same order
#: as the channel's lock budget; a dead channel costs this once, then raises.
STATE_MISS_BUDGET = 1.0

#: How many notes of Unity's log size to keep -- 15 minutes at one a second, far past any `window`
#: a diagnosis asks about. See Session.UNITY_NOTE_EVERY for why the notes exist at all.
UNITY_NOTES = 900

#: A log last written more than this long before OUR launch is a previous run's. Slack, not
#: precision: a stale log is minutes or hours older, and the game writes both within a second.
LAUNCH_SLACK = 2.0

#: Stock FF9 field ids, read once from reference/field-manifest.tsv. `DictionaryPatch.txt` lists only
#: MOD registrations, so a membership test against it alone refuses all ~674 shipping rooms with a
#: false claim about a null `.eb`.
_STOCK_FIELDS: set[int] | None = None


class ProbeLeftControl(HarnessError):
    """A calibration probe set something off: it walked into a gateway, or into anything else that took
    control away. ``field`` is where the probe started, ``direction`` the button it held.

    A HarnessError, so every caller that already stops on one still does; :meth:`Session.route_to` catches
    it to report the crossing as a record instead of steering on into a room it is no longer in."""

    def __init__(self, message: str, *, field: int, direction: str):
        super().__init__(message)
        self.field, self.direction = field, direction


class Transcript(list):
    """What :meth:`Session.watch_cutscene` returns: the scene's distinct pages -- the plain list every caller
    has always read -- plus ``choices``, one record per choice the scene was waited through under
    ``choices="default"``: ``{"index", "text", "prompt", "count", "field", "frame"}``, the ABSOLUTE index the
    game's cursor rested on and the words of that option. Empty without the opt-in, which takes no choice."""

    def __init__(self, pages=(), choices=()):
        super().__init__(pages)
        self.choices: list[dict] = list(choices)


def stock_field_ids() -> set[int]:
    """Field ids the base game ships, so the warp guard does not refuse a real room."""
    global _STOCK_FIELDS
    if _STOCK_FIELDS is not None:
        return _STOCK_FIELDS
    found: set[int] = set()
    # `<hw-export>.txt \t <field id> \t <name>` -- no header row. The HW index is NOT the field id,
    # which is why only column 1 is read.
    manifest = REPO / "reference" / "field-manifest.tsv"
    try:
        for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines():
            cols = line.split("\t")
            if len(cols) >= 2 and cols[1].strip().isdigit():
                found.add(int(cols[1].strip()))
    except OSError:
        pass
    _STOCK_FIELDS = found
    return found


def scan_registrations(game_path: Path) -> list[tuple[Path, list[tuple[int, str]]]]:
    """Every `FieldScene` registration, PER MOD FOLDER, in the order the files sort.

    One entry per readable ``<mod folder>/DictionaryPatch.txt``: ``(patch_path, [(id, name), ...])``.
    Kept per folder rather than flattened because WHICH folder serves an id is a fact worth having:
    ids are a GLOBAL namespace (EventDB is shared across every stacked folder), so the same id in two
    folders is the classic null-``.eb`` black screen, and a bench that "vanished" is usually one that
    another lane's folder still serves. A folder that cannot be read is simply absent from the list --
    the caller decides whether an empty answer means "nothing registered" or "could not look".

    The directive is ``FieldScene <id> <area> <NAME> ...`` -- the second column is the AREA index,
    not the name, which is why the name is the third field.
    """
    out: list[tuple[Path, list[tuple[int, str]]]] = []
    for patch in sorted(Path(game_path).glob("*/DictionaryPatch.txt")):
        try:
            text = patch.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rows: dict[int, str] = {}
        for m in re.finditer(r"^\s*FieldScene\s+(\d+)\s+(\d+)\s+(\S+)", text, re.MULTILINE):
            rows[int(m.group(1))] = m.group(3)
        # Tolerate a two-column form rather than dropping the id entirely.
        for m in re.finditer(r"^\s*FieldScene\s+(\d+)\s+([A-Za-z_]\S*)", text, re.MULTILINE):
            rows.setdefault(int(m.group(1)), m.group(2))
        out.append((patch, sorted(rows.items())))
    return out


def launch_args(width: int, height: int, monitor: int = 0) -> list[str]:
    """The arguments the Memoria launcher's Play button passes to FF9.exe.

    THIS IS WHY THE HARNESS DOES NOT CLICK PLAY. Started bare, ``FF9.exe`` hands off to
    ``FF9_Launcher.exe`` and exits 0 -- so a naive launch looks like an instant crash while a WPF
    launcher window sits there waiting for a human, and after a DLL update it also stacks a changelog
    dialog in front. ``-runbylauncher`` is the flag that suppresses the handoff; the rest mirror
    ``UiLauncherPlayButton.StartGameProcess`` so the game gets the display setup it expects.

    Both of those gates are launcher-side WPF, so skipping the launcher removes both at once -- no GUI
    automation, nothing to go stale when the launcher is restyled.

    Windowed on purpose (``-screen-fullscreen 0``): exclusive fullscreen is what makes the external
    PrintWindow capture return an all-black frame, and a windowed game leaves the machine usable. This
    is a command-line argument only -- nothing in the user's saved display settings is touched.
    """
    return [
        "-runbylauncher", "-single-instance",
        "-monitor", str(monitor),
        "-screen-width", str(width),
        "-screen-height", str(height),
        "-screen-fullscreen", "0",
    ]


def _pids_of(image: str) -> list[int]:
    """PIDs of a running image. Uses tasklist rather than psutil, which is not a kit dependency."""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image}", "/NH", "/FO", "CSV"],
            capture_output=True, text=True, timeout=20,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    pids = []
    for line in out.splitlines():
        parts = [p.strip('" ') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == image.lower():
            try:
                pids.append(int(parts[1]))
            except ValueError:
                pass
    return pids


def ff9_pids() -> list[int]:
    """PIDs of any running FF9 game process (not the launcher)."""
    return _pids_of("FF9.exe")


def _launcher_running() -> bool:
    return bool(_pids_of("FF9_Launcher.exe"))


class Session:
    """A single harness run: launch (or attach), drive, assert, tear down, keep the artifacts."""

    def __init__(
        self,
        *,
        label: str = "run",
        game_path: str | os.PathLike | None = None,
        attach: bool = False,
        keep_open: bool = False,
        run_dir: str | os.PathLike | None = None,
        boot_timeout: float = BOOT_TIMEOUT,
        verbose: bool = True,
        window_size: tuple[int, int] = DEFAULT_SIZE,
        pid_probe=None,
        launcher=None,
        save_dir: str | os.PathLike | None = None,
        state_ring: int = STATE_RING,
        repo_root: str | os.PathLike | None = None,
    ):
        self.window_size = window_size
        # ``pid_probe`` / ``launcher`` are the test seam. They exist so the offline suite can drive a
        # protocol stand-in without ever resolving, launching or killing the real shared install --
        # the same "pin the path through a seam, never read the real file" rule the deploy tooling
        # learned the hard way. Production leaves both None.
        self._pid_probe = pid_probe or ff9_pids
        self._launcher = launcher
        # The player's save folder is a REAL path on a shared machine, so the tests must pin it the
        # same way they pin the game path -- through a seam, never by reading the real thing. The
        # deploy tooling learned this the hard way when a pinned id leaked into the owner's GUI.
        self.save_dir = Path(save_dir) if save_dir else PLAYER_SAVE_DIR
        self.label = label
        self.game_path = Path(game_path) if game_path else find_game_path()
        self.attach = attach
        self.keep_open = keep_open
        self.boot_timeout = boot_timeout
        self.verbose = verbose
        self.channel = Channel(self.game_path, label=label)
        self.proc: subprocess.Popen | None = None
        self._launched = False
        self.checks: list[dict] = []
        #: What the last fight() actually did -- turns taken, result, the epoch it fought.
        #: None until one runs. See fight() for why the TURN COUNT is worth keeping.
        self.last_fight: dict | None = None
        #: What the last leave_battle() pressed and where it stopped (research/o3_design.md H8). None until one runs.
        self.last_leave: dict | None = None
        self._axes: dict[int, dict] = {}      # field id -> measured button->world basis
        self._priors: dict[int, dict | None] = {}   # field id -> PREDICTED basis (key_prior), never a measurement
        #: Unseen blockers route_to(unstick=True) walked into on the CURRENT field visit: (field id, [(x, z)]).
        #: Kept only while every published sample shows that field with control held -- see _observe --
        #: and each for ROUTE_BLOCKER_TTL from when it went in (_blocker_at; see _visit_blockers).
        self._blockers: tuple[int, list] = (-1, [])
        self._blocker_at: dict = {}
        self._events = None                   # the install's field event bundle, opened on first key_prior
        self._last_error: str | None = None   # the agent's error latch as of the last successful ack
        self.engine_protocol: int | None = None   # what the DEPLOYED engine speaks, once it answers
        self._story_starts = 0                # storytrace() turned the s88 trace on this many times
        #: Prefix stamped onto every screenshot name. A suite sets it per scenario, because two
        #: scenarios both capturing "walk-before" otherwise overwrite each other's evidence in the
        #: one channel directory -- and the evidence you lose is always the failing run's.
        self.shot_prefix = ""
        #: Whether this session has ever reached a field. The title settle exists because Memoria is
        #: still LOADING the first time the title appears; on a re-entry (after a soft reset) it is
        #: pure dead time, and in a suite it is dead time once per scenario.
        self._booted_once = False
        #: Automatic evidence on a failed check -- the state ring flushed and a screenshot -- capped
        #: per scenario (FAILURE_EVIDENCE_CAP), because re-running to see the moment costs the suite.
        self._shot_on_failure = True
        self._evidence = 0
        self._last_failure_frame: int | None = None
        #: The last ~10 s of published state (~20 s at 31 fps: artifacts.STATE_RING), fed by the reads
        #: every wait already makes (the channel's observer) -- no thread, no extra poll. Flushed to
        #: states-<tag>.jsonl on failure and always once at stop, BEFORE quit, which is the moment
        #: state-final.json gets wrong.
        self._ring = StateRing(state_ring)
        #: The game's render rate and field tick rate, MEASURED from the same reads (harness.tickrate.TickClock:
        #: consecutive published frames paired with their write time) -- every press is sized, and every rule
        #: judged, by :meth:`rate`, never by a frame count taken to mean a distance. The tick rate is the ini's
        #: ``[Graphics] FieldTPS`` (30 when it does not say) until a published tick counter measures it.
        self._clock = TickClock(read_field_tps(self.game_path))
        #: Every move of the measured rate the clock reported (:meth:`_note_rate`): ``(before, now)`` as dicts --
        #: the first estimate of the launch, and any later move past harness.tickrate.CHANGE_FRACTION (the 60 -> 31
        #: switch seen once mid-launch). Logged as it happens and carried in report.json.
        self.rate_changes: list[dict] = []
        #: The movement cross-check's strikes in a row (:meth:`_check_movement`): free presses that moved him
        #: outside what the measured rate says, since the last one that did not.
        self._strikes: list[str] = []
        #: Whether the newest state read says the field INHIBITS RUNNING (``input.dash_inh`` 1: stock's DASHOFF,
        #: EventEngine.DoEventCode.cs:3009-3012 -- the Prima Vista cargo room, the Palace Dungeon, a Lindblum inn
        #: region): a run hold then walks, one MovePC call a tick (FieldMapActorController.cs:196-198). Read on every
        #: state, like the clock (:meth:`_observe`); what :meth:`_gait` answers.
        self._dash_inh = False
        #: The published frames the last :meth:`_pressed` measured between (its settled reads before and after): the
        #: span the movement cross-check asks the clock about (TickClock.excess_ticks -- a hitch in it).
        self._press_span: tuple | None = None
        #: (time, byte size) of Unity's log, noted on the same reads -- see UNITY_NOTE_EVERY.
        self._unity_notes: collections.deque = collections.deque(maxlen=UNITY_NOTES)
        #: The control-loss probe a routed walk arms (:meth:`route_to`, :meth:`route_cross`): ``{"live", "lost"}`` --
        #: once ``live``, the first state ANY read of the call returns with control gone is kept in ``lost``
        #: (:meth:`_observe`), so the record says where control went whichever wait read it. None: no walk armed one.
        self._loss_probe: dict | None = None
        self.channel.observer = self._observe
        #: steps.jsonl -- every request with its accept/ack latency. Drops are counted, never raised.
        self._steps = StepLog()
        self._steps_logged = 0
        self._steps_dropped = 0
        #: Where a suite member's artifacts land (bound by the runner BEFORE its baseline ladder, so
        #: the ladder's steps and a POISONED ring belong to the member they were spent on).
        self.scenario_dir: Path | None = None
        self._phase = "run"
        self._env_extra: dict = {}
        self.repo_root = Path(repo_root) if repo_root else REPO
        self._boot_started: float | None = None
        self._boot_seconds: float | None = None
        self._first_state: str | None = None
        #: Set by SuiteRunner. When true, `self.checks` belongs to ONE MEMBER of a suite, so a
        #: whole-run verdict computed from it would describe the last scenario and label it the run.
        self._suite_owned = False
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.run_dir = Path(run_dir) if run_dir else RUNS / f"{stamp}-{label}"

    # -- lifecycle ------------------------------------------------------------------------------
    def __enter__(self) -> "Session":
        try:
            self.start()
        except BaseException:
            # A failed start must still tear down. Without this, an exception in start() means
            # __exit__ never runs and the `arm` file is left behind on an install shared by every
            # other worktree -- so the next person's game silently boots with the harness live.
            self.stop(failed=True)
            raise
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.stop(failed=exc is not None)
        return False

    def start(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        # FIRST, before the pid probe, the claim, the arm and the launch: a run that dies in boot
        # still documents the install it died against, and the DLL is hashed before the game opens it.
        self.write_env()
        running = self._pid_probe()
        if running and not self.attach:
            raise HarnessError(
                f"FF9 is already running (pid {running[0]}). The harness will not race a session it "
                f"does not own -- close the game, or pass attach=True to drive the live one."
            )
        if not running and self.attach:
            raise HarnessError("attach=True but no FF9 process is running.")

        self._backup_player_saves()
        # Refuse a shared channel BEFORE touching it: reset() deletes events.jsonl and every PNG, so
        # doing it while another live run owns the arm destroys their evidence, not just ours.
        self.channel.claim()
        self.channel.reset()
        # A game that is already up must OBSERVE the disarm before the re-arm, or the agent never
        # resets its sequence numbers and every step we send is discarded as stale while acking
        # instantly. With nothing running there is no observer, so the wait is skipped. The cycle
        # waits for the agent's own disarm document (channel.ARM_CYCLE_TIMEOUT); one it never saw is
        # said here -- _adopt_agent's sequence check still guards the requests, not the held keys.
        if self.channel.arm(force_cycle=bool(running)) is False:
            self._log(f"!! the agent published no disarm within {ARM_CYCLE_TIMEOUT:.0f}s of the arm file going (an "
                      f"engine that does not publish `armed`, a faulted agent, or a game stalled that long): "
                      f"re-armed anyway -- if it never saw the cycle, its held keys, error latch and story "
                      f"tracer are the last run's")
        # The arm file gates a shared install: if this process dies without running stop(), the next
        # session's game silently boots with the harness live. __exit__ is not enough -- a bare
        # sys.exit or an unhandled raise outside the with-block skips it.
        atexit.register(self._atexit_disarm)
        self._log(f"channel {self.channel.dir}")

        # A rate is never carried across launches (the regime is the launch's: 31 or 60 fps for a whole run),
        # so whatever the clock saw before this start -- a previous game on the shared channel -- is forgotten.
        self._clock.reset()
        self._strikes.clear()
        self._boot_started = time.time()
        if not running:
            exe = self.game_path / "x64" / "FF9.exe"
            if self._launcher is not None:
                self._log("launching via the injected launcher")
                self.proc = self._launcher(exe)
            else:
                if not exe.exists():
                    raise HarnessError(f"no FF9.exe at {exe}")
                args = launch_args(*self.window_size)
                self._log(f"launching {exe} {' '.join(args)}")
                # CWD is the GAME ROOT, not x64. UiLauncherPlayButton.StartGameProcess never sets a
                # WorkingDirectory, so the game inherits the launcher's -- the root, where Memoria.ini,
                # FontList and the mod folders live. Launching from x64 instead gets much further than
                # you would expect and then dies inside EncryptFontManager.SetDefaultFont, because the
                # font lookup is relative to the working directory. Memoria.log lands here too.
                self.proc = subprocess.Popen([str(exe), *args], cwd=str(self.game_path))
            self._launched = True
        else:
            self._log(f"attaching to pid {running[0]}")

        self._await_agent()
        self._adopt_agent()
        self._boot_seconds = round(time.time() - self._boot_started, 1)
        self.write_env()                      # now with the engine's protocol and first state
        self._assert_save_sandbox()

    def _adopt_agent(self) -> None:
        """Reconcile the driver's sequence counter and protocol with the agent that actually answered.

        Two failure modes, both of which have exactly one symptom -- a step that acks without running:

        1. The agent kept a HIGH ``_seq`` from a previous run (a lost arm-cycle race, or a future
           engine that does not reset). Our counter restarts at 0, so every request we write is
           discarded as stale while its published ``ack`` satisfies our wait instantly. Starting
           above the agent's own counter makes that unreachable regardless of what it did on arm.
        2. The deployed DLL is OLDER than this driver. Every ``State`` accessor degrades a missing
           section to a sentinel, so a version skew reads as game data rather than as a mismatch.
           An older engine is DEGRADED but usable, so it warns rather than refusing -- and the
           degradation is recorded in the report, because "we ran against an engine that publishes
           the raw dialogue source" is exactly the kind of caveat a green result must carry. A
           NEWER engine is refused outright: this driver does not know what its keys mean.

        ⚠ Reads through :attr:`state`, which raises on a dead channel. It used to read the channel
        once and RETURN on None, so one stalled publish skipped both defences without a word.
        """
        st = self.state
        self.engine_protocol = st.protocol
        if st.protocol is not None and st.protocol > PROTOCOL:
            raise HarnessError(
                f"protocol mismatch: this driver speaks {PROTOCOL}, the deployed engine speaks "
                f"{st.protocol}. Update the driver -- reading a newer channel by guesswork is how a "
                f"skew turns into game data."
            )
        if st.protocol is not None and st.protocol < PROTOCOL:
            self._log(
                f"!! the deployed engine speaks protocol {st.protocol}, this driver speaks "
                f"{PROTOCOL}. Running DEGRADED: dialogue `texts` is the raw SOURCE (tags and "
                f"un-substituted variables), the choice index space is unpublished, and refusals of "
                f"worldwarp/teleport ack clean; below 5 the co-op `netsync` block and verbs are "
                f"absent. Rebuild the DLL before trusting a text assertion."
            )
        if st.seq > 0:
            self._log(f"the agent is at seq {st.seq} (it did not reset on arm) -- continuing above it")
            self.channel.seed_seq(st.seq)
        self._last_error = st.error

    # -- the player's saves ---------------------------------------------------------------------
    # ⚠ MEASURED, NOT SUSPECTED. On 2026-08-31 `scenarios/save_untouched.py` showed that an ordinary
    # `newgame(); warp()` -- the opening of EVERY scenario -- changed both of the owner's live save
    # containers, because EventEngine autosaves on field entry and DisableAutoSave is 0 here. Manual
    # slots survived; the autosave did not. Two defences, because one of them needs a rebuilt DLL:
    #   1. back the containers up before the game is even launched (always, cheap, driver-only), and
    #   2. assert the engine redirected its save path into the channel (protocol >= 2).

    def _backup_player_saves(self) -> int:
        """Copy the live save containers into the run directory before anything can touch them."""
        if not self.save_dir.is_dir():
            return 0
        dest = self.run_dir / "saves-before"
        n = 0
        for path in sorted(self.save_dir.glob("SavedData_ww*.dat")):
            try:
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest / path.name)
                n += 1
            except OSError as err:
                self._log(f"could not back up {path.name}: {err}")
        if n:
            self._log(f"backed up {n} save container(s) to {dest}")
        return n

    def _changed_player_saves(self) -> list[str]:
        """Which of the backed-up containers the run moved. Empty is the only acceptable answer."""
        import filecmp

        dest = self.run_dir / "saves-before"
        if not dest.is_dir():
            return []
        moved = []
        for backup in sorted(dest.glob("*.dat")):
            live = self.save_dir / backup.name
            try:
                if not live.exists() or not filecmp.cmp(backup, live, shallow=False):
                    moved.append(backup.name)
            except OSError:
                pass
        return moved

    def _assert_save_sandbox(self) -> None:
        """Verify the engine moved its save path off the player's file -- never assume it.

        A sandbox that is trusted rather than checked is a check that cannot fail, and the thing it
        would fail to catch is silently overwriting the owner's game. So a read that finds nothing
        RAISES (via :attr:`state`); returning on it let one stalled publish skip this check.
        """
        st = self.state
        sandboxed = st.raw.get("save_sandboxed")
        if sandboxed is None:
            self._log("!! this engine does not sandbox saves (protocol < 2): an autosave on field "
                      f"entry WILL write {self.save_dir}. A copy is in {self.run_dir / 'saves-before'}.")
            return
        if not sandboxed:
            try:
                st = self.wait_for(lambda s: s.raw.get("save_sandboxed") is True, timeout=5.0,
                                   what="the engine to sandbox its save path")
            except HarnessError as err:
                raise HarnessError(
                    f"the engine did NOT redirect its save path, so an autosave on field entry "
                    f"would overwrite the player's game in {self.save_dir}. Refusing to run. "
                    f"({err})"
                ) from err
        self._log(f"saves sandboxed to {st.raw.get('save_path')}")

    def _atexit_disarm(self) -> None:
        try:
            self.channel.disarm()
        except Exception:
            pass

    def _await_agent(self) -> None:
        """Block until the in-game agent publishes its first state."""
        deadline = time.time() + self.boot_timeout
        while time.time() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                extra = ""
                if self.proc.returncode == 0 and _launcher_running():
                    extra = ("FF9_Launcher is up, so the game handed off to it instead of starting -- "
                             "the -runbylauncher argument did not reach it. ")
                raise HarnessError(
                    f"the game exited during boot (code {self.proc.returncode}). {extra}"
                    f"{self._log_hint()}"
                )
            st = self.channel.state()
            if st is not None:
                self._first_state = repr(st)
                self._log(f"agent up after {self.boot_timeout - (deadline - time.time()):.0f}s -- {st!r}")
                return
            time.sleep(0.25)
        raise HarnessError(
            f"the agent never published state within {self.boot_timeout:.0f}s. Either the running "
            f"engine predates memoria-patch s83, or it never reached the title screen. "
            f"{self._log_hint()}"
        )

    def stop(self, failed: bool = False) -> None:
        try:
            # FIRST, while the agent still answers: the collect below must take a closed trace.
            self._close_story_trace()
            if self._launched and not self.keep_open and self.proc and self.proc.poll() is None:
                self._log("asking the game to quit")
                try:
                    self.send("quit", wait=False)
                    self.proc.wait(timeout=15)
                except (subprocess.TimeoutExpired, HarnessError):
                    self._log("quit did not land -- terminating")
                    self.proc.kill()
        except Exception as err:
            # Deliberately broad. Whatever goes wrong while shutting the game down, the `finally`
            # below MUST still run: it is the only thing that removes `arm` from a shared install.
            # Leaving the harness armed because a kill misbehaved would hand the next session's game
            # a live harness it never asked for.
            self._log(f"teardown: could not stop the game cleanly ({err})")
        finally:
            # DISARM FIRST. Everything else here is bookkeeping that can fail -- a locked PNG, a full
            # disk, an unwritable run dir -- and any of those raising used to skip the disarm and
            # leave a shared install armed for the next worktree's game. Artifacts are worth less
            # than the gate.
            try:
                self.channel.disarm()
            finally:
                # The ring's content is the game BEFORE `quit` (nothing polls after it), which is
                # exactly the moment state-final.json -- captured after -- gets wrong.
                for step in (lambda: self.channel.collect(self.run_dir),
                             self._collect_log,
                             lambda: self.flush_states("final"),
                             lambda: self._write_report(failed)):
                    try:
                        step()
                    except Exception as err:                       # noqa: BLE001 - see above
                        self._log(f"teardown: {step} failed ({err})")
            moved = self._changed_player_saves()
            if moved:
                self._log("!! THIS RUN CHANGED THE PLAYER'S SAVE: " + ", ".join(moved)
                          + f" -- the pre-run copies are in {self.run_dir / 'saves-before'}")
            self._log(f"artifacts in {self.run_dir}")

    def _collect_log(self) -> None:
        """Archive BOTH exception logs into the run directory, under their own file names.

        Which one an exception lands in is decided by who caught it (see :mod:`harness.logs`), so a
        run dir holding only Memoria.log is missing every uncaught field/world exception.
        output_log.txt is rewritten on every launch: teardown is the last moment this run's copy
        exists. One the game never wrote this launch is a previous run's, and is left out rather
        than filed as this one's evidence -- Memoria.log timestamps every line, so a stale copy of
        it documents itself; Unity's does not.
        """
        for name, log in self._log_paths():
            if name == UNITY_LOG and self._predates_launch(log):
                self._log(f"not archiving {log}: the game never wrote it this launch")
                continue
            try:
                shutil.copy2(log, self.run_dir / name)
            except OSError as err:
                self._log(f"teardown: could not archive {name} ({err})")

    def _log_hint(self) -> str:
        return (f"Check {self.run_dir / MEMORIA_LOG} (caught exceptions -- all battle code) and "
                f"{self.run_dir / UNITY_LOG} (uncaught ones) once the run ends.")

    # -- sending --------------------------------------------------------------------------------
    def send(self, *steps: str, wait: bool = True, timeout: float = 60.0) -> None:
        """Queue raw protocol steps and (by default) block until the game has finished them.

        Every request leaves a row in ``steps.jsonl`` -- the literal steps, when the agent ACCEPTED
        it (``accept_ms``) and when it FINISHED it (``ack_ms``) -- written in a ``finally`` so a
        refusal, a timeout and a dead game all leave their row too. A row with ``accept_ms`` null
        is a request the agent never read; one with ``ack_ms`` null is one it read and never
        finished. That distinction used to cost a re-run.
        """
        row = {
            "kind": "step", "t": time.time(),
            "at": _dt.datetime.now().isoformat(timespec="milliseconds"),
            "scenario": self.scenario_dir.name if self.scenario_dir is not None else None,
            "phase": self._phase, "seq": None, "steps": list(steps), "awaited": bool(wait),
            "accept_ms": None, "ack_ms": None, "frame": None, "error": None,
        }
        try:
            row["seq"] = self.channel.send(list(steps), alive=self._assert_alive)
            if wait:
                self._await_ack(row["seq"], timeout, steps, row=row)
        except HarnessError as err:
            row["error"] = str(err)
            raise
        finally:
            self._ledger(row)

    def _await_ack(self, seq: int, timeout: float, steps, row: dict | None = None) -> State:
        """Wait for the agent to finish OUR request -- proven by its own receipt, not by a number.

        ⚠ ``ack`` alone is not proof. It is a single counter on a component that outlives every
        scene, and after a leaked arm file it still carries a dead run's value; every step then
        "succeeds" in milliseconds having done nothing, and the first verb that measures the world
        reports a confident falsehood about the game. Requiring the published ``seq`` to have reached
        ours as well means the agent has demonstrably ACCEPTED this request, not merely finished
        something.
        """
        sent = time.time()
        deadline = sent + timeout
        last: State | None = None
        accepted = False
        while time.time() < deadline:
            self._assert_alive()
            last = self.channel.state()
            if last is not None and not accepted and last.seq >= seq:
                accepted = True
                if row is not None:
                    row["accept_ms"] = round((time.time() - sent) * 1000, 1)
            if last is not None and last.seq >= seq and last.ack >= seq and not last.busy:
                if row is not None:
                    row["ack_ms"] = round((time.time() - sent) * 1000, 1)
                    row["frame"] = last.frame
                self._raise_if_this_step_failed(last, seq, steps)
                self._last_error = last.error
                return last
            time.sleep(0.02)
        raise HarnessError(
            f"steps {list(steps)} were not acknowledged within {timeout:.0f}s "
            f"({self.channel.classify()}; last state: {last!r})"
        )

    def _raise_if_this_step_failed(self, st: State, seq: int, steps) -> None:
        """Blame THIS step only for an error THIS step caused.

        ⚠ The agent's error is a LATCH: it is set on any refusal and cleared only when the harness
        re-arms. So the first refused step used to make every later healthy step raise, quoting a
        stale message against an innocent request -- which is how one bad warp turned into a sweep
        reporting every remaining field as unreachable. Prefer the agent's own ``error_seq`` stamp
        where it publishes one; otherwise fall back to "the message changed since our last good ack",
        which is exact for every case except an identical error repeating.
        """
        if not st.error:
            return
        if st.error_seq is not None:
            if st.error_seq >= seq:
                raise StepRefused(st.error, steps)
            return
        if st.error != self._last_error:
            raise StepRefused(st.error, steps)

    def _sleep_alive(self, seconds: float) -> None:
        """Sleep, but keep noticing if the game dies -- a plain sleep turns a crash into a timeout."""
        deadline = time.time() + seconds
        while time.time() < deadline:
            self._assert_alive()
            time.sleep(min(0.25, max(0.0, deadline - time.time())))

    def _assert_alive(self) -> None:
        if self.proc is not None and self.proc.poll() is not None:
            raise HarnessError(
                f"the game exited (code {self.proc.returncode}) mid-run. {self._log_hint()}"
            )

    # -- observing ------------------------------------------------------------------------------
    #: Lines, in EITHER exception log, that explain a failure better than any driver-side symptom can.
    #:
    #: ⚠ Every marker here must be something that does NOT happen in normal play. `invalidFieldMapID`
    #: was in this list and had to be removed: the engine emits it during an ordinary New Game boot,
    #: so it matched on every run and confidently blamed a bad warp for whatever had actually gone
    #: wrong. A marker that fires routinely is worse than no marker at all.
    _LOG_MARKERS = (
        ("NullReferenceException", "the engine threw a NullReferenceException"),
        ("Cannot load the field", "the engine failed to load a field"),
        ("[ff9mk harness] disarmed after an unhandled error",
         "the harness agent disarmed itself after an internal error"),
    )

    #: `dd.MM.yyyy HH:mm:ss |L| message`
    _LOG_TS = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4}) (\d{2}):(\d{2}):(\d{2}) \|")

    def engine_log(self) -> Path | None:
        """The engine log for THIS run -- the most recently written one.

        `Memoria.Prime.Log` opens `Memoria.log` by RELATIVE name, so it lands in whatever working
        directory the process was given: the game root for a launcher-style start, `x64/` for others.
        Both files exist on this install and one of them is usually stale by hours. Picking by a fixed
        order rather than by mtime is not a style question -- it made `diagnose()` report a
        NullReferenceException from a run eight hours earlier as the cause of a live hang, which is
        worse than saying nothing. Newest wins, and this is the one `_collect_log` archives too.
        """
        candidates = [p for p in (self.game_path / "Memoria.log",
                                  self.game_path / "x64" / "Memoria.log") if p.exists()]
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_mtime)

    def unity_log(self) -> Path | None:
        """Unity's own log, ``x64/FF9_Data/output_log.txt`` -- where every UNCAUGHT exception goes.

        The other half of :meth:`engine_log`, and not optional: an exception lands in exactly one of
        the two, decided by who catches it (see :mod:`harness.logs`). Rewritten on every launch.
        """
        path = self.game_path / UNITY_LOG_PATH
        return path if path.exists() else None

    def _log_paths(self) -> list[tuple[str, Path]]:
        """``[(name, path)]`` for each of the two logs that exists -- Memoria.log newest-wins."""
        return [(name, path) for name, path in ((MEMORIA_LOG, self.engine_log()),
                                                (UNITY_LOG, self.unity_log())) if path is not None]

    def _predates_launch(self, log: Path) -> bool:
        """Whether ``log`` was last written before the game THIS session launched -- a previous run's.

        Always False for an attached game: its logs are the live process's, however quiet.
        """
        if not self._launched or self._boot_started is None:
            return False
        try:
            return log.stat().st_mtime < self._boot_started - LAUNCH_SLACK
        except OSError:
            return True

    #: How often (seconds) the size of Unity's log is noted, riding the state reads every wait
    #: already makes -- no thread, no extra poll. output_log.txt carries NO timestamps, so these
    #: notes are the only thing that lets diagnose() honour its `window` there: the size at the last
    #: note before the cutoff is where "recent" begins.
    UNITY_NOTE_EVERY = 1.0

    def _observe(self, st: State) -> None:
        """Every State a read returns: into the ring, into the tick clock (:meth:`rate` -- the render rate is
        measured from exactly these reads, no extra poll), and a note of how long Unity's log is -- and the end
        of a field VISIT for the unseen blockers route_to remembers. A sample on another field, or with
        control gone (a gateway, a scene, a warp's fade: anything that may move the room's people),
        drops them. Here and not at the verbs, so no way of leaving can forget to."""
        self._ring.push(st)
        self._clock.observe(st)
        probe = self._loss_probe
        if probe is not None and probe["live"] and probe["lost"] is None and not st.control:
            probe["lost"] = {"frame": st.frame, "field": st.field_id, "x": st.player_x, "z": st.player_z,
                             "control": st.control}
        inp = st.raw.get("input")
        self._dash_inh = isinstance(inp, dict) and inp.get("dash_inh") == 1
        self._note_unity_log()
        if self._blockers[1] and (st.field_id != self._blockers[0] or not st.control):
            self._blockers = (-1, [])
            self._blocker_at = {}

    def _note_unity_log(self) -> None:
        now = time.time()
        if self._unity_notes and now - self._unity_notes[-1][0] < self.UNITY_NOTE_EVERY:
            return
        log = self.unity_log()
        try:
            size = log.stat().st_size if log is not None else None
        except OSError:
            size = None
        self._unity_notes.append((now, size))

    def _unity_offset_at(self, cutoff: float) -> int:
        """Where Unity's log stood at ``cutoff``: the size at the last note taken at or before it.

        Errs toward INCLUDING: with no note that old (a young session, a game that never published)
        it is 0, the way an untimestamped Memoria line is kept rather than dropped. (A noted size
        past the file's end -- rewritten since -- is :func:`harness.logs.read_from`'s to handle.)
        """
        at = 0
        for t, noted in self._unity_notes:
            if t > cutoff:
                break
            at = noted or 0
        return at

    def log_mark(self) -> dict[str, tuple[Path, int]]:
        """A mark in BOTH logs, for :meth:`exceptions_since`: ``{name: (path, byte offset)}``.

        The offset is snapped back to the start of any line the game is still writing, so a mark can
        never split an exception's header from its own frames.
        """
        mark: dict[str, tuple[Path, int]] = {}
        for name, log in self._log_paths():
            try:
                mark[name] = (log, line_start_offset(log))
            except OSError:
                pass
        return mark

    def exceptions_since(self, mark: dict | None = None) -> list[LogException]:
        """Every exception either log recorded after ``mark`` (from :meth:`log_mark`).

        ``mark=None`` means the whole of each current log: on a game this session launched that is
        this launch (both logs are rewritten on launch, and one the game has not written since is
        skipped); on an ATTACHED game it includes whatever came before you attached, so take a mark.

        Memoria.log's come first, then output_log.txt's, each in the order written; nothing orders
        them against each other, because Unity's log has no timestamps. Filter with
        ``LogException.through(...)`` / ``.name`` / ``.log`` -- e.g. battle code is always in
        Memoria.log, because the battle loop catches everything it throws.

        A log absent from the mark, or no longer the file the mark was taken in (newest-wins moved
        to the other Memoria.log), is read from its start: all of it is newer than the mark.
        """
        out: list[LogException] = []
        for name, log in self._log_paths():
            if self._predates_launch(log):
                continue
            offset = 0
            if mark and name in mark:
                marked, at = mark[name]
                if Path(marked) == log:
                    offset = int(at)
            try:
                text = read_from(log, offset)
            except OSError:
                continue
            out.extend(PARSERS[name](split_lines(text)))
        return out

    def diagnose(self, lines: int = 60, *, max_age: float = 300.0,
                 window: float = 30.0) -> str | None:
        """Explain a hang from the engine's own logs, rather than from driver-side symptoms.

        A driver only ever sees "state stopped arriving", which looks identical whether the game
        crashed, black-screened on a bad warp, or was merely slow -- the least useful of those to be
        told. The log usually says what happened one line earlier.

        BOTH logs, because which one holds the exception is decided by who caught it: battle code is
        caught and lands in Memoria.log; an uncaught field/world exception (a MonoBehaviour's
        ``Update`` throwing) lands ONLY in Unity's output_log.txt. Reading one of them leaves every
        hang the other explains looking like a driver fault. Every log that has a marker is
        reported, the most recently written first.

        Refuses to speak from a STALE log: one last written more than `max_age` ago, or before the
        game this session launched, describes some previous run, and a confidently wrong diagnosis
        costs more than none at all.
        """
        now = time.time()
        live = []
        for name, log in self._log_paths():
            try:
                mtime = log.stat().st_mtime
            except OSError:
                continue
            if now - mtime > max_age or self._predates_launch(log):
                continue
            live.append((mtime, name, log))
        found = []
        for _mtime, name, log in sorted(live, key=lambda row: row[0], reverse=True):
            try:
                recent = (self._recent_memoria(log, lines, window) if name == MEMORIA_LOG
                          else self._recent_unity(log, lines, window, now))
            except OSError:
                continue
            why = self._explain(recent)
            if why:
                found.append(f"{why} (from {log})")
        return "; ".join(found) or None

    def _recent_memoria(self, log: Path, lines: int, window: float) -> list[str]:
        """Memoria.log's last ``lines`` lines, minus any timestamped before the ``window``."""
        tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
        # Only lines from the last `window` seconds may explain a failure happening NOW. Without
        # this a marker from earlier in the same run -- boot noise, a previous scenario step -- gets
        # offered as the cause of something minutes later.
        cutoff = _dt.datetime.now() - _dt.timedelta(seconds=window)
        recent = []
        for line in tail:
            m = self._LOG_TS.match(line)
            if m:
                d, mo, y, hh, mm, ss = (int(g) for g in m.groups())
                try:
                    if _dt.datetime(y, mo, d, hh, mm, ss) < cutoff:
                        continue
                except ValueError:
                    pass
            recent.append(line)
        return recent

    def _recent_unity(self, log: Path, lines: int, window: float, now: float) -> list[str]:
        """output_log.txt's lines written inside the ``window``, at most the last ``lines`` of them.

        The same rule as Memoria.log's with no timestamps to apply it by: a file not written since
        the cutoff contributes nothing (exact), and otherwise reading starts where the file stood at
        the cutoff, per the size notes (:meth:`_unity_offset_at`).
        """
        if now - log.stat().st_mtime > window:
            return []
        offset = self._unity_offset_at(now - window)
        return split_lines(read_from(log, offset))[-lines:]

    def _explain(self, recent: list[str]) -> str | None:
        """The first marker ``recent`` holds, with the frame its newest occurrence was thrown at."""
        for marker, explanation in self._LOG_MARKERS:
            hits = [i for i, line in enumerate(recent) if marker in line]
            if hits:
                where = frame_after(recent, hits[-1])
                return explanation + (f" at {where}" if where else "")
        return None

    @property
    def state(self) -> State:
        """The latest published state. Rides out a transient miss; raises when the channel is dead.

        ⚠ ONE None FROM THE CHANNEL IS NOT "NO STATE". This raised on the first one, and a scenario
        polling it every 4 ms through a ride at ``state_every(1)`` died on ``no state published --
        OK`` while the game went on publishing: the read had landed in the agent's in-place rewrite
        (see :data:`STATE_MISS_BUDGET`). Only a channel unreadable for the whole budget raises, and
        the message names which kind of dead it is.
        """
        st = self._read_state()
        if st is None:
            self._assert_alive()          # a dead game should say so, not blame the arming
            hint = self.diagnose()
            raise HarnessError(
                f"no state published: state.json stayed unreadable for {STATE_MISS_BUDGET:.1f}s -- "
                f"{self.channel.classify()}" + (f" -- {hint}" if hint else "")
            )
        return st

    def _read_state(self) -> State | None:
        """One read that rides out a transient miss. ``None`` only when the channel stayed
        unreadable for :data:`STATE_MISS_BUDGET` -- the caller reports that, never a single miss.

        Readable is all this waits for. Whether a document is LIVE is the waits' business, as it
        always was: a photograph a hung agent left is returned here with or without a miss first.
        """
        st = self.channel.state()
        deadline = time.time() + STATE_MISS_BUDGET
        while st is None and time.time() < deadline:
            self._assert_alive()          # a game that died mid-miss says so now, not after the budget
            time.sleep(0.01)
            st = self.channel.state()
        return st

    def wait_for(self, predicate, *, timeout: float = 20.0, what: str = "condition") -> State:
        """Poll until ``predicate(state)`` is true. Raises with the last state seen on timeout.

        Two things this refuses to do, both of which produced durable false verdicts about the game:

        **It will not honour a predicate against a FROZEN channel.** The last ``state.json`` a hung
        or crashed agent left behind still satisfies most predicates, so a wait can "succeed"
        against a game that stopped publishing minutes ago -- and the run then reports on a
        photograph. A sample only counts once the agent's frame counter has moved.

        **It will not report a broken predicate as a broken game.** A predicate that raises on every
        single sample used to be swallowed silently and time out with the game-condition message,
        which ``expect()`` then wrote into report.json as a failure of the game. The distinction is
        named in the error.
        """
        deadline = time.time() + timeout
        last: State | None = None
        base_frame: int | None = None
        fresh = 0                 # samples whose frame counter had advanced since we started
        evaluated = 0             # samples on which the predicate ran to completion
        raised: Exception | None = None
        while time.time() < deadline:
            self._assert_alive()
            last = self.channel.state()
            if last is not None:
                if base_frame is None:
                    base_frame = last.frame
                elif last.frame > base_frame:
                    fresh += 1
                try:
                    ok = bool(predicate(last))
                    evaluated += 1
                except (TypeError, KeyError, AttributeError, IndexError, ValueError) as err:
                    # A predicate reading a field that is legitimately null right now. Counted, not
                    # ignored: if it is EVERY sample, the predicate is the bug.
                    raised, ok = err, False
                # Liveness, two ways. A frame that advanced is proof outright; failing that, a
                # document the agent wrote moments ago is good enough. What this rejects is the
                # photograph a hung agent left behind -- valid JSON that satisfies the predicate and
                # has not moved in minutes. Honouring a fresh first sample keeps a genuinely
                # transient condition (a box that opens and closes) observable.
                if ok and (fresh > 0 or (last.age is not None and last.age <= LIVE_WITHIN)
                           or last.age is None):
                    return last
            time.sleep(0.03)

        if evaluated == 0 and raised is not None:
            raise HarnessError(
                f"the predicate for {what} raised on all samples and never returned a verdict: "
                f"{raised!r}. This is a broken assertion, not a game failure."
            )
        if last is None:
            raise HarnessError(
                f"timed out after {timeout:.0f}s waiting for {what}: the agent published nothing at "
                f"all -- {self.channel.classify()}"
            )
        if fresh == 0:
            hint = self.diagnose()
            raise HarnessError(
                f"timed out after {timeout:.0f}s waiting for {what}, and the agent's frame counter "
                f"never moved off {base_frame} -- the channel is frozen, so this says nothing about "
                f"the condition. {self.channel.classify()}" + (f" -- {hint}" if hint else "")
            )
        raise HarnessError(
            f"timed out after {timeout:.0f}s waiting for {what} over {fresh} live samples "
            f"(last state: {last!r})"
        )

    #: How long a "the player is free" condition must HOLD before it is believed. Control flickers
    #: true for a moment as a field loads, before the entry script takes it away again -- a single
    #: sample made `watch_cutscene` return 0 pages on one run and 5 on the next.
    SETTLE = 1.0

    def _wait_settled(self, predicate, *, timeout: float, what: str, settle: float | None = None) -> State:
        """Wait for a condition to hold CONTINUOUSLY for ``settle`` seconds.

        Factored out because the load-flicker fix was applied to ``watch_cutscene`` and not to its
        sibling ``wait_control``, which is exactly the shape of divergence that makes one verb
        trustworthy and the other quietly flaky. One implementation, two callers.
        """
        settle = self.SETTLE if settle is None else settle
        deadline = time.time() + timeout
        held_since: float | None = None
        last: State | None = None
        while time.time() < deadline:
            last = self.wait_for(predicate, timeout=max(0.5, deadline - time.time()), what=what)
            held_since = time.time() if held_since is None else held_since
            time.sleep(0.05)
            probe = self.channel.state()
            try:
                still = probe is not None and bool(predicate(probe))
            except (TypeError, KeyError, AttributeError, IndexError, ValueError):
                still = False
            if not still:
                held_since = None
                continue
            if time.time() - held_since >= settle:
                return probe
        raise HarnessError(
            f"timed out after {timeout:.0f}s waiting for {what} to hold for {settle:.1f}s "
            f"(last state: {last!r})"
        )

    def wait_playable(self, *, timeout: float = 60.0) -> State:
        """Wait until the player actually has control on a field -- not merely 'the field loaded'.

        The distinction matters constantly: a field is loaded, faded in and rendering long before its
        entry script hands control over, and a scenario that starts walking too early silently drops
        its input on the floor and then fails somewhere unrelated.
        """
        # `control` alone is NOT enough. It reads EventEngine.GetUserControl(), a global flag that can
        # already be true while GetControlChar() still returns null a few frames into a field load --
        # so a scenario that measures the player's position at that moment gets None and any
        # movement assertion silently compares against nothing. Require a KNOWN position too.
        return self.wait_for(
            lambda s: (s.ui_state == "FieldHUD" and s.control and not s.fading
                       and s.player_x is not None),
            timeout=timeout, what="the player to have control at a known position on a field",
        )

    def wait_world(self, *, timeout: float = 90.0) -> State:
        """Wait until the player is standing on the OVERWORLD with control.

        Separate from :meth:`wait_playable` because the two map types publish different coordinate
        spaces through the same key -- see :meth:`_require_field`.
        """
        return self.wait_for(
            lambda s: (s.ui_state == "WorldHUD" and not s.fading
                       and s.world_x is not None and s.world_z is not None),
            timeout=timeout, what="the player to be standing on the world map",
        )

    def _require_field(self, verb: str) -> State:
        """Refuse a FIELD verb when the game is not on a field.

        ⚠ `player.x/z` does NOT go null on the overworld -- `GetControlChar()` returns the world
        actor and its `pos[]` is `RealPosition * 256`. So the movement verbs do not fail loudly
        there; they converge in a space 256x off, and `_probe_axis`'s "did it move" floor can never
        trip. A confident wrong number is the worst outcome available, so the guard is on the map
        type rather than on a null.
        """
        st = self.state
        if st.ui_state != "FieldHUD":
            where = "the world map" if st.ui_state == "WorldHUD" else f"ui_state={st.ui_state!r}"
            raise HarnessError(
                f"{verb} is a FIELD verb and the game is on {where}. Field positions are in field "
                f"units; the overworld publishes world.x/world.z in world units (player.* there is "
                f"the same value x256). Use the world verbs, or warp to a field first."
            )
        return st

    # -- acting ---------------------------------------------------------------------------------
    def press(self, button: str, frames: int = 2) -> None:
        self.send(f"press {_button(button)} {int(frames)}")

    def hold(self, button: str, frames: int) -> None:
        """Start holding a button WITHOUT blocking -- pair with :meth:`wait_frames` or another action."""
        self.send(f"hold {_button(button)} {int(frames)}", wait=False)

    def release(self, button: str) -> None:
        self.send(f"release {_button(button)}")

    def walk(self, direction: str, frames: int = 60) -> None:
        """Hold a direction for ``frames`` and wait it out -- the everyday 'move the character' verb."""
        self.send(f"hold {_button(direction)} {int(frames)}", f"wait {int(frames) + 2}")

    def wait_frames(self, frames: int) -> None:
        self.send(f"wait {int(frames)}")

    # -- turning in place (memoria-patch s90) -----------------------------------------------------
    #: turn_in_place: the most frames the agent's ``turn`` holds its keys (HarnessAgent.TurnMaxFrames).
    TURN_MAX_FRAMES = 36000
    #: turn_in_place: frames of ``state.frame`` past the request's ack within which the turn's ``turn_end`` must come.
    #: The agent reports a turn once the field has run TurnSettlePasses (2) event passes on its final facing after
    #: the keys lift -- 3-5 frames at 30 Hz ticks on a 60 Hz display, the ack itself landing a frame after the lift;
    #: a field that runs no event pass that long (timescale 0, a stalled field) has not judged it.
    TURN_END_FRAMES = 120

    def turn_in_place(self, directions, frames: int, *, timeout: float = 10.0) -> dict:
        """Turn him IN PLACE toward ``directions`` for ``frames`` frames -- memoria-patch s90's ``turn`` -- and return
        its ``turn_end``, PARSED (channel.parse_turn_end): ``{"frame", "why", "frames", "yaw0", "yaw", "face",
        "moved"}``. ``directions`` is one pad name or several (``"up"``, ``"up+right"``, ``("up", "right")``, the
        aliases ``north``/``south``/``west``/``east`` too). At the RUN rate, two MovePC calls a 30 Hz tick -- and only
        at it: a walked turn is ``hold cancel`` over the same frames IN THE SAME REQUEST, and the agent runs every step
        of a request whatever another step's refusal (HarnessAgent.DrainQueue), so a refused walked turn would still
        hold Cancel for its frames -- on a walk under way (the ``held`` refusal: it flips his speed) or on whatever
        took control (a choice window's Cancel). Nothing here needs the walk rate, so nothing here can press that.

        THE VERB (HarnessAgent.BeginTurn / ServiceTurn / EndTurn, s90). It holds the direction KEYS and feeds no analog
        axis: MovePC builds the 8-way target from the keys, zeroes the step because the axis is under the stick
        threshold, and lerps his yaw 40% of the way to the target each call (FieldMapActorController.cs:698-764) -- he
        turns and does not step. Non-blocking and frame-counted like ``hold``, so it is sent with a ``wait`` of its
        frames + 2 (the keys lift the frame after their last; the ack lands after that). THE FIELD JUDGES THE TURN
        AFTER ITS KEYS LIFT: the region pass that reads the final facing runs an event pass after the MovePC call that
        wrote it, so the agent keeps the turn open until the field has run 2 event passes since the lift and only then
        writes ``turn_end`` -- usually AFTER the ack. So this polls the event log for the first ``turn_end`` after this
        request's ``accepted`` receipt (never reading the outcome at the ack), within TURN_END_FRAMES frames of it and
        ``timeout`` seconds. The agent retries an event append the driver's read collided with on its NEXT event
        (HarnessAgent.FlushEvents), so a report not seen by then is asked for once more with a ``wait 1`` -- whose
        own receipt flushes it -- before this gives up (HarnessError: the field ran no event pass on his final facing;
        the turn stays open on the agent, a hold of a direction is refused until its ``turn_end``, and ``reset`` clears
        it).

        ``why`` is ``"ended"`` -- the keys lifted and the field ran its passes on the final facing with him under
        control, on the same field and actor: a gate there had its read and did not take him -- or the token that CUT
        it (``field``, ``player``, ``control``, ``movement``, ``actor``, ``hud``, ``unreadable``, ``axis``). ``control``
        is not proof a door fired (a script can take him): the field changing is. ``face`` is the facing byte the
        gate compares (content.doorface.gate_value_from_face); ``yaw``/``face``/``moved`` are None off a field or
        after the field id or controlled actor changed. ``moved`` over 0.25 was not a turn in place (a push-out, a
        wall's edge force, a human's stick, a script).

        Refused -- nothing pressed: the request is the ``turn`` and its ``wait``, and a ``wait`` is never refused -- it
        raises :class:`channel.TurnRefused`, ``kind`` naming the agent's stable message (channel.TURN_REFUSALS), read
        from the error latch of the very sample that acked the request (:class:`channel.StepRefused`), never from a
        second read of state.json, which a healthy game can answer None mid-rewrite. Off a field or with a UI over it
        the AGENT refuses (TurnBlocker's ``field`` / ``hud``: ``kind`` "blocked"), so a caller handles a UI that comes
        up between its own look and this call as that refusal, not as a driver error; the field verbs' world-map guard
        (:meth:`_require_field`) is for positions, and a turn reads none. NEVER SENT to an engine that cannot
        (State.facing_status "cannot": no ``player.face`` key, a pre-s90 DLL, which has no ``turn`` verb): that raises
        HarnessError here, as does a button that is not a direction, a pair of opposite directions, or ``frames``
        outside 1..TURN_MAX_FRAMES."""
        from .channel import DIRECTIONS, parse_turn_end, turn_refusal
        dirs = []
        for d in ([directions] if isinstance(directions, str) else list(directions)):
            for part in str(d).split("+"):
                key = _button(part)
                if key not in DIRECTIONS:
                    raise HarnessError(f"turn_in_place turns him toward a DIRECTION (up/down/left/right, or "
                                       f"north/south/west/east) -- {part!r} is not one")
                if DIRECTIONS[key] not in dirs:
                    dirs.append(DIRECTIONS[key])
        if not dirs:
            raise HarnessError("turn_in_place needs a direction")
        if {"up", "down"} <= set(dirs) or {"left", "right"} <= set(dirs):
            raise HarnessError(f"turn_in_place({dirs}): opposite directions cancel to no direction (the engine's "
                               f"atan2(-0, -0) would face him -180 degrees, where nobody pressed)")
        frames = int(frames)
        if not 1 <= frames <= self.TURN_MAX_FRAMES:
            raise HarnessError(f"turn_in_place holds its keys 1..{self.TURN_MAX_FRAMES} frames -- got {frames}")
        if self.state.facing_status == "cannot":
            raise HarnessError(
                "turn_in_place needs memoria-patch s90: this engine publishes no player.face, so it has no `turn` "
                "verb either (a pre-s90 DLL) -- nothing was sent. A walked press turns him too, and moves him.")
        before = len(self.channel.events())
        try:
            self.send(f"turn {'+'.join(dirs)} {frames}", f"wait {frames + 2}")
        except StepRefused as err:
            if err.error.startswith("turn: "):
                raise turn_refusal(err.error[len("turn: "):]) from err
            raise
        seq, start = self.channel.seq, self.state.frame
        deadline = time.time() + timeout
        nudged = False
        while True:
            evs = self.channel.events()[before:]
            got = next((k for k, e in enumerate(evs)
                        if e.get("kind") == "accepted" and str(e.get("seq")) == str(seq)), -1)
            # no receipt yet (the agent still holds it back): an earlier turn's report is all a search could find
            end = next((e for e in evs[got + 1:] if e.get("kind") == "turn_end"), None) if got >= 0 else None
            if end is not None:
                return parse_turn_end(end)
            now = self.channel.state()
            if (now is not None and now.frame - start > self.TURN_END_FRAMES) or time.time() > deadline:
                if not nudged:
                    nudged = True
                    self.send("wait 1")               # its own receipt flushes a report the agent still holds
                    continue
                raise HarnessError(
                    f"turn_in_place({'+'.join(dirs)}, {frames}): no turn_end within {self.TURN_END_FRAMES} frames "
                    f"of the ack ({self.channel.classify()}) -- the field ran no event pass on his final facing "
                    f"(timescale 0, a stalled field). The turn is still open on the agent: a hold or press of a "
                    f"direction is refused until its turn_end, and `reset` clears it. Last state: {now!r}")
            self._assert_alive()
            time.sleep(0.02)

    # -- going somewhere ------------------------------------------------------------------------
    # `walk(direction, frames)` is a poor primitive and measurement says so: on the 30801 bench the
    # character runs at 30 units/frame, so a 75-frame hold "should" cover 2250 units -- and covered
    # 1014, because he reached the edge of the walkmesh and stopped. Open-loop frame counts encode a
    # distance nobody measured, saturate silently against geometry, and bake in a constant that is
    # wrong on the next field. Everything below is closed-loop against the published position.
    #
    # THE CLOCK A PRESS IS PLANNED BY (harness.tickrate). He does not move per RENDER FRAME: field logic runs on
    # wall-clock ticks, FieldTPS (30) a second (FPSManager.cs:77-111, HonoBehaviorSystem.cs:106 at stock 6b8bb2d5),
    # and a tick moves him one MovePC call walking, two running, 30u each (FieldMapActorController.cs:198-209). So
    # "30 units a frame" was true only at the 60 fps the bench was measured at -- and the harness has rendered at
    # ~31 fps for whole launches, where a frame carries him twice that, and once at ~105. Every press here is
    # planned by the MEASURED rate (:meth:`rate`), asking it for one of three kinds of number: the AVERAGE to SIZE
    # a press (Rate.speed / frames_for: wrong costs an iteration), an UPPER bound for every RULE a press keeps
    # (Rate.reach: how far he CAN have gone -- a zone he must not enter, a body he must not touch), a LOWER bound,
    # in whole ticks, for anything that must be SURE (Rate.calls_sure / frames_for_ticks). A frame count taken to
    # mean a distance is the one thing nothing here does any more -- and the constants that did (the per-frame run
    # and walk speeds, the frames of movement tail) are gone, so a site that still asks fails loudly instead of
    # silently judging half the reach.
    #
    # THE "AT 60 FPS" FIGURES QUOTED BELOW are an EXACT clock's -- the fake's published rt, a future engine's. Today's
    # engine is timed by the state file's mtime, whose estimate is widened MTIME_WIDEN either way: at a steady 60 fps
    # its spread is 58.8-61.2, and wherever N x 30 / fps is whole a sure count takes a frame more and a reach a tick
    # more (a tick sure in 3 frames, not 2; the push lock 29, not 28; a settle a third still publish) -- honest at a
    # 59.94 Hz display, and pinned by test_tickrate's test_todays_engine_at_a_steady_60_pays_a_tick_each_way.

    #: Half of one MovePC call's step (content.doorface.STEP_PER_CALL): a DISTANCE, the same at every render rate --
    #: the tolerance "moved at all", "in contact" and "one step past" are judged by, and the closest a walk can aim
    #: (a call steps a whole 30u; a target nearer than half a step is as often passed as reached). It was once
    #: spelled WALK_SPEED (15u, a walked frame at 60 fps), which is why it is 15 and not rescaled with the rate.
    HALF_STEP = STEP_PER_CALL / 2.0
    #: One field tick of RUNNING, in world units: two MovePC calls (tickrate.CALLS_PER_TICK) of STEP_PER_CALL. A
    #: distance, never rescaled: the tail a burst may carry beyond its ticks (:meth:`_burst_is_evidence`), how near
    #: a trigger's radius counts as within its reach (:meth:`_npc_fired`), a walker's fastest plausible walk
    #: (:meth:`_npc_read`: two of these a tick).
    RUN_TICK = CALLS_PER_TICK["run"] * STEP_PER_CALL
    #: A need nearer than this is WALKED (Cancel held) -- walk_to's bursts and a smooth leg's holds
    #: (:meth:`_plan_hold`): a run steps a whole RUN_TICK at a time, so a run press overshoots any tighter aim. A
    #: DISTANCE, a run tick and a half: once ``3 x`` the run speed a frame, 90u at 60 fps -- but 180u at 30 fps and
    #: 45u at 120, where a 3-frame run burst for a 50u need is sure of no tick at all.
    WALK_UNDER = 1.5 * RUN_TICK

    #: :meth:`rate` ``require=True``: seconds it waits for a MEASURED rate before it refuses -- seconds of the GAME'S
    #: clock (its published ``rt``, else the state file's mtime) AND of the wall's, both: what it waits for is counted on
    #: the game's clock -- the visit's first harness.tickrate.ARRIVAL_SECONDS (1 s) of steady frames, then MIN_PAIRS (8)
    #: pairs of published frames, another half second at 31 fps publishing every other frame -- so 2 s from the first
    #: frame with control covers the slowest regime seen. On the real engine the two clocks are one. A stand-in whose
    #: frame loop runs slower than its virtual render rate (a busy machine, the nightly gate's six workers) lives its
    #: second of arrival over several of the wall's, and a wall-only budget refused a rate on a healthy fake. After the
    #: first estimate the rate carries across fields and the wait costs nothing.
    RATE_WAIT = 2.0
    #: ... and at most this many seconds of the WALL whatever the game's clock did: a game that publishes nothing new
    #: (hung, paused, a frozen stand-in) has a clock that never moves, and the wait must still end.
    RATE_WAIT_CAP = 10.0
    #: :meth:`_measured_rate`: seconds between its reads while it waits for a measured rate. The clock pairs only
    #: consecutive published frames at most harness.tickrate.PAIR_MAX_FRAMES (8) apart, so the reads must come round
    #: faster than that many frames: at the settle's own 20 ms a stand-in turning 960 frames a second (the suite's Dali
    #: fakes, a quarter of the wall clock) moved ~19 frames between two reads, paired none, and a wait that happened
    #: to need one raised for want of a rate on a healthy game. 2 ms is every publish of that loop, and a real game
    #: (a publish every 2nd frame: 14 ms apart at 144 fps) is read several times a publish -- for well under RATE_WAIT,
    #: once a launch in practice.
    RATE_POLL = 0.002
    #: The movement cross-check (:meth:`_check_movement`): this many measured presses IN A ROW that moved him outside
    #: what the rate says a press of their frames can -- further than Rate.reach, or (a press whose line ran free of
    #: walls) less than its sure calls step -- and the driver refuses to plan by that rate any longer. One is a script
    #: moving him, a platform, a push-out; three in a row is the rate.
    MOVEMENT_STRIKES = 3
    #: The fraction of its sure calls' 30u steps a FREE press is judged short against (:meth:`_check_movement`):
    #: PSXMovementMethod (on in this install) scales every step by the floor's |n.up| -- cos(slope),
    #: FieldMapActorController.cs:740-741 at stock 6b8bb2d5, WalkMesh.cs:2666-2677 -- so a healthy walk up a slope
    #: steps short (stock 350's door to 353 stands on 0.854; two run ticks there read 104u and 113u). No floor holds
    #: everywhere: a census of the 722 stock walkmeshes finds a triangle steeper than 60 degrees on about one field in
    #: seven (ladders and cliff faces a script walks him down, the steepest near vertical). Half is 60 degrees of
    #: slope -- far steeper than Dali's gated door regions (350's door to 353 the steepest measured, 31 degrees) -- and
    #: what it still catches is a tick rate at half the ini's or less.
    SLOPE_STEP_FLOOR = 0.5

    def rate(self, require: bool = False) -> Rate:
        """The game's render and field tick rate as the driver has measured it (harness.tickrate.Rate, from
        :attr:`_clock`, fed by every state read) -- what EVERY press is sized by and every rule judged by.

        Before the clock has measured anything the answer is the calibrated 60 fps (``Rate.ready`` False), which
        SIZING may lean on: a press sized wrong costs an iteration of a closed loop. ``require=True`` is for a site
        whose error cannot be undone -- a press whose reach is judged against a zone, a trigger, a body: at 31 fps
        the default halves every reach -- and so is a ``stale`` one, measured before an unobserved stretch in which
        the rate could have switched (harness.tickrate.STALE_GAP_SECONDS). It reads the game until a measured rate
        is there -- RATE_WAIT of the game's clock and the wall's, RATE_WAIT_CAP at most (:meth:`_measured_rate`) --
        and then RAISES (HarnessError, naming what the clock has): it never guesses. In practice the arrival settle
        and calibration have measured it long before the first such press."""
        rate = self._clock.rate()
        self._note_rate()
        if rate.ready or not require:
            return rate
        measured = self._measured_rate()
        if measured is not None:
            return measured
        st = self.channel.state()
        raise HarnessError(
            f"no MEASURED render rate after {self.RATE_WAIT:.1f}s of reads (of the game's clock and the wall's) -- "
            f"the clock has "
            f"{self._clock.rate().describe()}. A press whose reach must keep a zone or a trigger is judged at the "
            f"measured rate or not pressed at all (at 31 fps the calibrated 60's reach is half the truth). The clock "
            f"pairs frames only on a field, with control or a dialog, nothing fading, past the visit's first second; "
            f"last state: {st!r}")

    #: The render rate a WAIT or a SPAN that must LAST is sized at while none is MEASURED (``Rate.ready`` False: before
    #: the launch's first estimate, or a stale one): four times the calibrated 60 fps, past any rate the harness has
    #: rendered at (~105 the most, once). Sized there, a wait lasts at least its seconds and a stillness at least its
    #: ticks at any rate the game can truly be running -- the calibrated default's 4 frames of settle are ONE tick at
    #: 120 fps and less than one at 144, so a settle could stop between two ticks, mid-walk. Too long costs only frames:
    #: flee() releases its bumpers the moment its wait ends; a settle waits a few frames more.
    UNMEASURED_FPS = 240.0

    def _rate_at_most(self) -> Rate:
        """The rate a wait or a span that must LAST is sized by: :meth:`rate` when it is MEASURED, else UNMEASURED_FPS
        (``ready`` False: never a reach to judge by) -- the fastest the game can be taken to run, so Rate.frames_at_least
        and Rate.frames_for_ticks are sure of their seconds and ticks at whatever it truly runs at."""
        rate = self.rate()
        if rate.ready:
            return rate
        fast = self.UNMEASURED_FPS
        return Rate(fast, fast, fast, rate.tick_hz)

    def _measured_rate(self) -> Rate | None:
        """A MEASURED rate (``Rate.ready``): the clock's own at once when it has one, else after reading the game
        until it does -- until RATE_WAIT seconds have passed on the game's own clock AND the wall's, at most
        RATE_WAIT_CAP of the wall -- else None. :meth:`rate` ``require=True`` raises on the None; a step that has an
        answer for "no rate" (the facing press: nothing pressed, ``faced`` False) asks here."""
        rate = self._clock.rate()
        began = time.time()
        game0 = None                                      # the game's clock at the wait's first read
        while not rate.ready:
            self._assert_alive()
            st = self.channel.state()                     # every read feeds the clock (the channel's observer)
            rate = self._clock.rate()
            if rate.ready:
                break
            now = _game_seconds(st)
            game0 = now if game0 is None else game0
            waited = time.time() - began
            if waited >= self.RATE_WAIT_CAP or (waited >= self.RATE_WAIT and (
                    now is None or game0 is None or now - game0 >= self.RATE_WAIT)):
                break
            time.sleep(self.RATE_POLL)                # faster than the clock's pairs are apart (RATE_POLL)
        self._note_rate()
        return rate if rate.ready else None

    def _note_rate(self) -> None:
        """Log -- and keep in :attr:`rate_changes`, for report.json -- a move of the measured rate the clock reports
        (TickClock.changed: the launch's first estimate, then any move past CHANGE_FRACTION)."""
        moved = self._clock.changed()
        if moved is None:
            return
        before, now = moved
        self.rate_changes.append({"before": before.as_dict(), "now": now.as_dict(), "t": round(time.time(), 3)})
        self._log(f"  rate: {now.describe()}" + ("" if not before.ready else f" (was {before.describe()})"))

    @staticmethod
    def _tail_frames(rate: Rate) -> int:
        """The frames the movement TAIL can last after a press's own: tickrate.TAIL_TICKS of wall time -- the frames
        sure to hold that many ticks (Rate.frames_for_ticks: 2 at 60 fps, 1 at 30, 4 at 120). A TIME, what a walker
        is given to walk after a press ends; the tail's DISTANCE is Rate.reach's own."""
        return rate.frames_for_ticks(TAIL_TICKS)

    @staticmethod
    def _frames_within(ticks: float, rate: Rate) -> int:
        """The most frames sure to run no more than ``ticks`` field ticks -- a CAP in time (Rate.frames_at_most of
        ``ticks / tick_hz`` seconds), at least one: 6 frames for 3 ticks at 60 fps, 3 at 30, 12 at 120."""
        return max(1, rate.frames_at_most(float(ticks) / rate.tick_hz))

    def _frames_lasting(self, seconds: float, rate: Rate | None = None) -> int:
        """The frames a WAIT of ``seconds`` is held for -- the fewest sure to last at least that long at ``rate``
        (default :meth:`rate`; Rate.frames_at_least), at least one: 90 frames for 1.5 s at 60 fps, 45 at 30, 180 at
        120. Every time budget the route verbs keep is SECONDS (ROUTE_WAIT_SECONDS, the ROUTE_WALKER_*_SECONDS): a
        walker steps, a freeze counts down and a script runs on the wall clock, once a field tick; a frame count stood
        for a time only at the rate it was written at. The agent's ``wait`` counts FRAMES, so this is what it is
        sent -- and what a walker's measured speed a frame is multiplied by, the same stretch of its path at any
        rate."""
        return max(1, (self.rate() if rate is None else rate).frames_at_least(float(seconds)))

    @staticmethod
    def _least_frames(rate: Rate) -> int:
        """The fewest frames SURE to hold one field tick at ``rate`` (Rate.frames_for_ticks(1): 2 at 60 fps, 1 at
        30, 4 at 120) -- the least press that is sure to run a MovePC call at all. Fewer can fall between two ticks
        and run none -- no step, no turn -- so a press of fewer that moved him nothing says nothing about a wall
        (:meth:`_walk_leg`: the next press from there is this long)."""
        return rate.frames_for_ticks(1)

    def _gait(self, gait: str) -> str:
        """The gait a hold of ``gait`` truly runs at: a RUN is a walk while the newest state says the field inhibits
        running (:attr:`_dash_inh`; FieldMapActorController.cs:196-198) -- one MovePC call a tick, not two. Asked
        wherever a run's calls must be SURE (the calls a hold or a turn is credited with, the movement cross-check) and
        by the push throughout (its lock, its tail, its line): a lock counted in run ticks never opens on a walk.
        Where any other press is SIZED or its REACH judged, the run's own figures are the larger and stay on the safe
        side."""
        return "walk" if gait == "run" and self._dash_inh else gait

    #: :meth:`_calls_turned`: how near a whole count of calls -- whole TICKS of them, so pairs running -- a count read
    #: off the yaw (content.doorface.calls_from_turn) must lie to be taken as the calls that ran. The yaw's print (0.001
    #: degree) moves even a 14-call run turn's count by under 0.01 -- and a count that far from whole was no turn toward
    #: that heading. It is not the heading's uncertainty: that is the caller's ``spread`` (below).
    CALLS_WHOLE = 0.25

    def _calls_turned(self, yaw0, yaw1, target: float, gait: str, spread: float = 0.0) -> int | None:
        """The WHOLE MovePC calls a press or in-place turn held toward the heading ``target`` (degrees: the pad's --
        content.doorface.yaw_of of its calibrated world direction) RAN, read off his yaw before and after it (``yaw0``
        / ``yaw1``: ``player.yaw``, ``turn_end``'s ``yaw0`` / ``yaw`` -- published by memoria-patch s90): doorface.
        calls_from_turn, taken to the nearest whole ticks' worth of calls at the gait truly held (:meth:`_gait`;
        tickrate.CALLS_PER_TICK: one a tick walking, two running -- a run's calls come in PAIRS) where it lies within
        CALLS_WHOLE of it. After the fact and exact: the ticks a hitched frame caught up in a burst, and the phase a
        short press fell in, which no render rate can see -- where Rate.calls_sure only bounds them from below.

        ONLY AS EXACT AS THE HEADING. ``target`` is a calibrated measurement, true within ``spread`` degrees (the leg's
        heading spread, :meth:`_heading_spread`), and the count off a long turn moves by a whole call for a few tenths
        of a degree of it (7 calls from 20 degrees off read 7.85 with the pad 0.2 degrees off) -- so the count is taken
        only where the heading's WHOLE uncertainty reads the same whole count: at ``target`` and at ``target`` +-
        ``spread`` alike. None when a yaw is not published, the two are no turn toward ``target`` (a script, a push),
        or the heading's uncertainty spans two counts: the caller keeps the count the frames are sure of."""
        from ff9mapkit.content import doorface
        if yaw0 is None or yaw1 is None:
            return None
        per = CALLS_PER_TICK[self._gait(gait)]
        counts = set()
        for aim in ((target,) if spread <= 0 else (target - spread, target, target + spread)):
            k = doorface.calls_from_turn(yaw0, yaw1, aim)
            if k is None:
                return None
            whole = per * round(k / per)
            if abs(k - whole) > self.CALLS_WHOLE:
                return None
            counts.add(int(whole))
        return counts.pop() if len(counts) == 1 else None

    def _face_wait_frames(self) -> int:
        """The frames the facing step waits, standing in a gated door's region with control, for the door to fire on
        its own before anything is pressed or turned (ROUTE_FACE_WAIT_TICKS): the fewest sure to hold that many field
        ticks at the measured rate (:meth:`rate`, Rate.frames_for_ticks: 4 at 60 fps, 2 at 30, 8 at 120). The
        region's tag 2 runs once a TICK (EventEngine.ProcessEvents.cs:174-178), so a door the walk already faces fires
        within them, and its crossing is landed as the walk's own -- not as the facing step's, which it never was."""
        return self._rate_at_most().frames_for_ticks(self.ROUTE_FACE_WAIT_TICKS)

    def _check_movement(self, moved: float | None, frames: int, gait: str, rate: Rate, *, free: bool = False,
                        what: str = "press", span: tuple | None = None) -> None:
        """THE MOVEMENT CROSS-CHECK: a measured press -- ``frames`` of ``gait`` that moved him ``moved`` (settled at
        both ends) -- against what ``rate`` says those frames can do, at the gait he truly held (:meth:`_gait`: a run
        on a dash-inhibited field is a walk). Further than Rate.reach (the most its ticks and the tail can carry him)
        OUTRAN the rate; ``free`` (its line ran clear of walls for its whole reach, so nothing stopped a step) and
        short of the whole calls it is sure of (Rate.calls_sure x STEP_PER_CALL, on the steepest floor a walk meets:
        SLOPE_STEP_FLOOR) FELL SHORT -- but a press that moved him nothing is a hold on movement (the pad mask), not a
        rate, and is not judged. Each such press is a strike; a press within the bounds clears them.
        MOVEMENT_STRIKES in a row RAISE: every reach the driver judges is wrong by the same factor, and pressing on
        would walk him into what the reach was checked against. Not judged at all before the rate is measured, or
        when ``moved`` is None (control or the field went).

        A HITCH is not the rate. ``span`` -- the published frames the measurement began and ended on (its settled
        reads) -- lets the clock say how many ticks more than the rate accounts for those frames took
        (TickClock.excess_ticks: one frame of 120 ms at 60 fps catches up four, FPSManager.cs:94-99, and Rate.reach
        is no bound through it). An overshoot within those ticks is logged as the hitch's, neither a strike nor a
        clear: three hitched presses in a row are three hitches, not a wrong rate.

        What moves him further than his ticks: F1 SPEED MODE (Memoria.ini [Cheats] SpeedFactor -- FastForwardFactor,
        FPSManager.cs:83-97, which the engine publishes nowhere), a [Graphics] FieldTPS other than the ini the driver
        read, or the Run/Walk option (``cfg.move``, FieldMapActorController.cs:198: it inverts Cancel, so a press held
        as a walk runs). What moves a free press less: a FieldTPS below the ini's (dash-inhibit cannot: it is read,
        and turns only a run into a walk)."""
        import math
        if moved is None or not rate.ready:
            return
        gait = self._gait(gait)
        hi = rate.reach(frames, gait)
        lo = rate.calls_sure(frames, gait) * STEP_PER_CALL * self.SLOPE_STEP_FLOOR
        if moved > hi + 0.5:
            extra = self._clock.excess_ticks(span[0], span[1], rate) if span is not None else 0.0
            if extra >= 0.5 and moved <= hi + CALLS_PER_TICK[gait] * STEP_PER_CALL * math.ceil(extra) + 0.5:
                self._log(f"  movement: {what} of {frames} {gait} frame(s) moved him {moved:.0f}u, past the {hi:.0f}u "
                          f"it can reach -- in frames that ran {extra:.1f} tick(s) more than {rate.describe()} "
                          f"accounts for: a HITCH, not a strike")
                return
            strike = f"{what} of {frames} {gait} frame(s) moved him {moved:.0f}u, past the {hi:.0f}u it can reach"
        elif free and self.HALF_STEP <= moved < lo - 1.0:
            strike = (f"{what} of {frames} {gait} frame(s) moved him {moved:.0f}u on free floor, short of the "
                      f"{lo:.0f}u its sure calls step even up the steepest walkable slope")
        else:
            self._strikes.clear()
            return
        self._strikes.append(strike)
        self._log(f"  movement: {strike} at {rate.describe()} (strike {len(self._strikes)} of {self.MOVEMENT_STRIKES})")
        if len(self._strikes) >= self.MOVEMENT_STRIKES:
            strikes, self._strikes = self._strikes, []
            raise HarnessError(
                f"{len(strikes)} presses in a row moved him outside what the measured rate says ({rate.describe()}): "
                + "; ".join(strikes) + ". The driver judges every reach by that rate, so it will not press on. "
                "Further than it can reach: F1 SPEED MODE is on (Memoria.ini [Cheats] SpeedFactor -- the engine "
                "publishes no FastForwardFactor), or [Graphics] FieldTPS is not the ini's. Less than its sure calls: "
                "the field inhibits running (a run hold walks), or FieldTPS is lower. Turn the speed mode off, or "
                "fix the ini the driver read.")

    #: A probe that covers less than this fraction of what was COMMANDED did not measure free
    #: movement. An absolute floor cannot tell "he walked 40 units freely" from "he was pushed 40
    #: units along a wall while 900 were asked for".
    PROBE_MIN_FRACTION = 0.35

    def _burst_is_evidence(self, moved: float, frames: int, gait: str, rate: Rate | None = None) -> bool:
        """Is this burst's displacement -- ``frames`` of ``gait`` (``"run"`` / ``"walk"``) that moved him ``moved``
        -- attributable to THIS burst, and worth judging a basis on? Judged at ``rate`` (default: :meth:`rate`).

        ⚠ THE OLD TEST WAS `moved >= 15`, an absolute floor, and it is how a wall came to be
        reported as a broken axis calibration -- intermittently, because the distance the engine
        nudges a blocked character straddles it. Judged against the COMMAND instead, in both
        directions, with the numbers that came out of the game:

        * **TOO LITTLE** -- 24 units moved when 1350 were commanded (30820, pressed into a wall).
          He is BLOCKED, not mis-steered. This is the same law ``_probe_axis`` already applies, and
          the same mistake it already fixed once, found here at a second site. The floor is
          PROBE_MIN_FRACTION of the burst's AVERAGE travel at the rate (Rate.speed x frames).
        * **TOO MUCH** -- 114 units moved when one frame of ``left`` was pressed (30820, credited
          with the tail of the previous ``down``). Movement past what the burst's frames can carry
          was not all caused by this burst, so it says nothing about the direction this burst
          pressed. ``walk_to`` concluded the BASIS was wrong: a well-argued verdict about entirely
          the wrong thing, and the reason gateway_check failed on some runs and not others. The
          ceiling is the frames' field ticks at the SLOW end of the rate's spread -- ``frames x
          tick_hz / fps_lo``, UNROUNDED -- at the gait's calls a tick, 30u each, plus one running
          tick (RUN_TICK) of tail. At 60 fps that is the old ceiling at every count, odd or even
          (30u a run frame, 15 a walked one, and two run frames), so the 114u above is still too
          much; at 31 fps a frame carries a whole tick, where the old per-frame ceiling called every
          run burst of three frames or more "too much" and the basis check below it never ran.
          Not Rate.ticks_most's ceiling: that answers a RULE, which must hold at the one phase in
          which an odd count's extra tick falls -- and credited here it made one run frame worth
          two ticks and the recorded 30820 tail evidence. A clean burst that did run its extra tick
          and its tail (``hold down 31`` covered 1020u on 30801: sixteen ticks and one more) is
          only not judged -- the check skips it, never a basis it should have kept.

        A basis that is genuinely wrong sends the character walking FREELY in the wrong direction,
        so he covers very nearly what was commanded and still fails the projection test that
        follows.
        """
        rate = self.rate() if rate is None else rate
        least = self.PROBE_MIN_FRACTION * rate.speed(gait) * frames          # (a gait that is not one: ValueError)
        if moved < self.HALF_STEP:
            return False
        most = CALLS_PER_TICK[gait] * STEP_PER_CALL * frames * rate.tick_hz / rate.fps_lo + self.RUN_TICK
        return least <= moved <= most + 1e-6

    #: How many times to step away from whatever is in the way and re-measure an axis before
    #: refusing. Calibrating with your back to a wall is a fact about the arrival position, not
    #: about the field, and the arrival position varies between runs -- which is exactly the shape
    #: of an intermittent failure.
    CALIBRATE_ATTEMPTS = 3
    #: How far to run when backing off, world units -- a DISTANCE, sized into frames at the measured rate
    #: (Rate.frames_for: 8 run frames at 60 fps, 4 at 30): further than a probe (120 at 60 fps) so the retry is
    #: measuring somewhere genuinely different, short enough not to cross a room. (Once 8 FRAMES, which at 31 fps
    #: ran ~480u.)
    CLEARANCE_UNITS = 240.0

    def _back_off(self, direction: str, field: int) -> bool:
        """Walk a little way in ``direction`` to find clearer ground. False if it got us nowhere.

        ⚠ IT REFUSES TO LEAVE THE FIELD. Backing off can walk into a gateway, and a calibration that
        silently continued in the NEXT room would cache that room's basis under this room's id --
        a wrong answer with no symptom until something steered by it.
        """
        before = self.settle()
        rate = self.rate()
        frames = rate.frames_for(self.CLEARANCE_UNITS, "run")
        self.walk(direction, frames)
        after = self.settle()
        if after.field_id != field or after.player_x is None:
            raise HarnessError(
                f"backing off {direction} to calibrate field {field} left the field "
                f"(now {after.field_id}). There is a gateway right next to the calibration spot; "
                f"calibrate somewhere with room around the character."
            )
        if before.player_x is None:
            return False
        moved = ((after.player_x - before.player_x) ** 2
                 + (after.player_z - before.player_z) ** 2) ** 0.5
        self._check_movement(moved if after.control else None, frames, "run", rate, what="a back-off",
                             span=(before.frame, after.frame))
        return moved > self.HALF_STEP

    def distance_to(self, x: float, z: float) -> float:
        st = self._require_field("distance_to")
        if st.player_x is None:
            raise HarnessError("no player position published -- not on a field?")
        return ((st.player_x - x) ** 2 + (st.player_z - z) ** 2) ** 0.5

    def calibrate_axes(self, *, probe: int = 4, recalibrate: bool = False, hazards=(),
                       prior: dict | None = None) -> dict:
        """Discover which BUTTON moves the character which way in WORLD space, on this field.

        This cannot be hard-coded. FF9 fields are viewed by a fixed camera that is frequently yawed,
        and movement is expressed in screen space (`FF9StateSystem.Field.twist`), so "up" is +z on one
        field, -x on another, and something diagonal on a third. A `walk_to` that assumed a mapping
        would work on the bench and quietly walk the wrong way in real rooms.

        So: press each axis briefly, measure the actual world displacement, and keep the basis. If a
        probe barely moves -- the usual cause is standing against a wall -- it retries the opposite
        direction and negates, which is why this is a probe and not a single press.

        ``hazards`` (polygons, world ``[x, z]`` corners) and ``prior`` (a PREDICTED basis, e.g.
        :meth:`key_prior`) switch to :meth:`_calibrate_clear_of`, the mode :meth:`route_to` uses: a
        character who just arrived through a door is standing beside its gateway, and a blind probe
        in the wrong direction walks him straight back out. Without them this is unchanged.
        """
        st = self._require_field("calibrate_axes")
        key = st.field_id
        if not recalibrate and key in self._axes:
            return self._axes[key]
        if hazards or prior is not None:
            return self._calibrate_clear_of(key, hazards, prior, probe)

        # Probe BOTH directions of each axis and cross-check them. A single probe cannot tell free
        # movement from a slide: pressed into a wall at an angle the engine keeps the character
        # moving, just not where he was sent, and the resulting unit vector is a perfectly
        # well-formed lie. The opposite press is the control -- free movement is antiparallel and of
        # similar length; a slide is neither.
        basis, detail = {}, {}
        for name, (fwd, back) in (("v", ("up", "down")), ("h", ("right", "left"))):
            vec = reach = None
            trouble = ""
            for attempt in range(self.CALIBRATE_ATTEMPTS):
                last_try = attempt == self.CALIBRATE_ATTEMPTS - 1
                a = self._probe_axis(fwd, probe)
                b = self._probe_axis(back, probe)
                if a is None and b is None:
                    raise HarnessError(
                        f"could not calibrate the {name} axis on field {key}: neither {fwd} nor "
                        f"{back} moved the character more than {self.PROBE_MIN_FRACTION:.0%} of the "
                        f"{probe * self.rate().speed('run'):.0f} units commanded. Is he boxed in, or is "
                        f"control withheld?"
                    )
                if a is None or b is None:
                    # One side is entirely blocked. The other still measured the axis, so the
                    # DIRECTION is known -- but a measurement taken with your back to a wall is
                    # worth re-taking from clear ground before it is cached for the whole field.
                    free_name, free = (back, b) if a is None else (fwd, a)
                    if not last_try and self._back_off(free_name, key):
                        trouble = f"{fwd if a is None else back} was blocked"
                        continue
                    vec = free[0] if a is not None else (-free[0][0], -free[0][1])
                    reach = free[1]
                    break

                anti = -(a[0][0] * b[0][0] + a[0][1] * b[0][1])      # +1 when truly opposite
                ratio = min(a[1], b[1]) / max(a[1], b[1])
                roomier = fwd if a[1] >= b[1] else back
                if anti >= 0.85 and ratio >= 0.5:
                    vec, reach = a[0], min(a[1], b[1])
                    break

                # ⚠ RETRY BEFORE REFUSING, and the reason is that this refusal is about WHERE THE
                # CHARACTER IS STANDING, not about the field. `ratio` low with `anti` at +1.00 means
                # the two probes agree perfectly on the axis and one of them ran out of room -- a
                # false negative, and a coin-flip one, since the arrival position varies. Backing
                # off along the roomier direction and re-measuring is what a person would do.
                trouble = (f"{fwd} measured {_vec(a[0])} over {a[1]:.0f}u and {back} measured "
                           f"{_vec(b[0])} over {b[1]:.0f}u (antiparallel={anti:+.2f}, length "
                           f"ratio={ratio:.2f})")
                if not last_try and self._back_off(roomier, key):
                    continue
                raise HarnessError(
                    f"the {name} axis on field {key} is not a free axis: {trouble}. The character "
                    f"is sliding along something rather than walking, and backing off along "
                    f"{roomier} did not find clearer ground in "
                    f"{self.CALIBRATE_ATTEMPTS} attempts. Calibrate from open ground."
                )
            if trouble:
                self._log(f"  calibrate {name}: retried after {trouble}")
            basis[name] = vec
            detail[name] = reach

        # Two screen axes should be close to perpendicular. ⚠ This test is computed from UNIT
        # vectors, so it is identically zero under any rigid rotation and CANNOT by itself falsify a
        # deflected probe -- which is why the antiparallel/length cross-check above exists. It is
        # kept because it does catch the remaining case: two axes that were each deflected onto the
        # same wall.
        skew = abs(basis["v"][0] * basis["h"][0] + basis["v"][1] * basis["h"][1])
        if skew > 0.35:
            raise HarnessError(
                f"axis calibration on field {key} looks deflected: up={_vec(basis['v'])} "
                f"right={_vec(basis['h'])} are not perpendicular (|dot|={skew:.2f}). Something "
                f"(an NPC, a wall) pushed a probe. Move to clearer ground and recalibrate."
            )

        self._axes[key] = basis
        self._log(f"axes on field {key}: up={_vec(basis['v'])} ({detail['v']:.0f}u) "
                  f"right={_vec(basis['h'])} ({detail['h']:.0f}u) |dot|={skew:.2f}")
        return basis

    #: How long to wait for the character to come to rest before measuring a displacement, and
    #: how still he has to be. Two consecutive samples within half a unit is the engine's own
    #: resolution -- the published position is exact, not interpolated -- over at least the frames
    #: sure to hold SETTLE_TICKS field ticks (see :meth:`settle`).
    SETTLE_TIMEOUT = 3.0
    SETTLE_SAMPLES = 2
    SETTLE_EPSILON = 0.5
    SETTLE_TICKS = 2

    def settle(self, *, timeout: float | None = None) -> State:
        """Wait until the published position stops changing, and return that state.

        ⚠ A HOLD OF N FRAMES DOES NOT PRODUCE EXACTLY N FRAMES OF MOVEMENT, and every displacement
        this driver measures used to assume it did. Measured on bench 30801: ``hold down 31``
        commands 930 units and covers **1020** -- the engine samples input on one frame and applies
        movement on a later one, so travel continues for several frames after the button is up.

        That tail does not vanish; it lands in the NEXT measurement window and is attributed to
        whatever was pressed there. On 30820 it produced this, one frame of `left` covering 114
        units of pure -z::

            down  f=31 cmd=930 moved=960.0 proj=+960.0  (60,-777) -> (60,-1737)
            left  f=1  cmd= 30 moved=114.0 proj=  -0.0  (60,-1737) -> (60,-1851)

        `walk_to` concluded the axis BASIS was wrong -- a confident, well-argued verdict about the
        wrong thing, which is what made `gateway_check` fail on some runs and pass on others.

        STILL MEANS STILL THROUGH FIELD TICKS, not publishes. He moves only on a tick -- FieldTPS a
        second on the wall clock, whole, a frame holding 0, 1 or several (FPSManager.cs:77-111 at
        stock 6b8bb2d5) -- so two samples at one spot say nothing when no tick ran between them. At
        120 fps a tick falls on every 4th frame and two publishes a frame or two apart can both sit
        between ticks, mid-walk; a settle that stopped there left the rest of the movement to land in
        the next press -- the 30820 failure above, at a rate the bench never ran at. So the stillness
        must also SPAN at least the frames sure to hold SETTLE_TICKS ticks at the measured rate
        (:meth:`rate`, Rate.frames_for_ticks: 4 frames at an exact 60 fps -- which two still samples a
        publish apart always spanned, so nothing changes there -- 2 at 30, 8 at 120; on today's engine,
        timed by the state file's mtime, a 60 fps estimate's spread makes it 5, and a settle waits a
        third still publish). Before any rate is measured, at UNMEASURED_FPS (:meth:`_rate_at_most`:
        16 frames): the calibrated default's 4 are one tick at 120 fps. Two ticks, not one: the
        published position lags its own frame's ticks (the agent's Update ran before the actors' in
        the one frame measured -- an order Unity does not fix, so the lag may come and go), and the
        first tick of the span may be one no sample shows yet.

        Polls the state file directly, so settling costs no round trip to the game. Returns the last
        state seen even if it never settles: something legitimately moving (a platform, a scripted
        walk) is not this method's business to refuse, and the callers all have their own verdicts.
        """
        deadline = time.time() + (self.SETTLE_TIMEOUT if timeout is None else timeout)
        span = self._rate_at_most().frames_for_ticks(self.SETTLE_TICKS)      # sure of them: before any measurement too
        last: State | None = None
        still = 0
        since = -1                        # the frame the stillness began on: the sample the first still one matched
        while time.time() < deadline:
            self._assert_alive()
            st = self.channel.state()
            if st is None:
                time.sleep(0.02)
                continue
            if (last is not None and st.player_x is not None and last.player_x is not None
                    and abs(st.player_x - last.player_x) <= self.SETTLE_EPSILON
                    and abs(st.player_z - last.player_z) <= self.SETTLE_EPSILON
                    and st.frame > last.frame):
                if still == 0:
                    since = last.frame
                still += 1
                if still >= self.SETTLE_SAMPLES and st.frame - since >= span:
                    return st
            elif last is None or st.frame > last.frame:
                still = 0
            last = st
            time.sleep(0.02)
        if last is not None:
            self._log(f"  settle: the character was still moving after "
                      f"{self.SETTLE_TIMEOUT:.0f}s at {last.pos}")
        return last if last is not None else self.state

    def _probe_axis(self, direction: str, frames: int, *, slow: bool = False,
                    watch_control: bool = False):
        """Hold one direction briefly; return ``((ux, uz), magnitude)``, or None if it did not move.

        "Did not move" is judged against what was COMMANDED, not against an absolute floor. The old
        15-unit floor accepted a character shoved a few units sideways by a wall as a real
        measurement of that axis, cached the resulting basis, and then steered every later walk_to
        along the wall -- reporting the field as unreachable.

        ``slow`` holds Cancel too (walk speed: one MovePC call a tick, half a run's). ``watch_control`` also
        refuses a probe after which the player no longer has control -- see :class:`ProbeLeftControl`.
        What was commanded is the probe's AVERAGE travel at the measured rate (:meth:`rate`, Rate.speed x
        frames): at 31 fps a run frame carries him ~57u, and a floor of a third of the 60 fps 30u would pass
        a character shoved along a wall. Every probe that moved him is checked against the rate too
        (:meth:`_check_movement`).
        """
        # ⚠ BOTH ENDS SETTLED. The old code waited a flat 6 frames, which is a guess at the
        # engine's movement tail -- and the tail is not a constant: `hold down 31` covers 1020 units
        # for 930 commanded, and on 30820 it ran ~5 frames past the hold. A probe that measures
        # during the tail reports a length that is part its own and part the previous probe's.
        before = self.settle()
        rate = self.rate()
        gait = "walk" if slow else "run"
        if slow:
            self.send(f"hold cancel {int(frames) + 1}", f"hold {_button(direction)} {int(frames)}",
                      f"wait {int(frames) + 2}")
        else:
            self.walk(direction, frames)
        after = self.settle()
        if not watch_control and (before.player_x is None or after.player_x is None):
            return None
        if after.field_id != before.field_id:
            raise ProbeLeftControl(
                f"probing {direction} left field {before.field_id} for {after.field_id} -- the probe "
                f"walked into a gateway. Calibrate somewhere with room around the character.",
                field=before.field_id, direction=direction)
        # ⚠ THE FIELD ID IS THE LAST THING TO CHANGE. A gateway's walk-in trigger runs ExitField,
        # which zeroes usercontrol on the frame it fires (DoEventCode.cs:866) and auto-walks the
        # player out; the id flips only when the next room loads, a fade later. A probe settled in
        # between reads "same field" -- and the next press lands in the destination. Stock 350
        # ping-ponged with 351 eighty times that way.
        if watch_control and before.control and not after.control:
            raise ProbeLeftControl(
                f"probing {direction} on field {before.field_id} took control away (at "
                f"({after.player_x}, {after.player_z})) -- the probe fired a trigger, most likely "
                f"a gateway's ExitField.", field=before.field_id, direction=direction)
        if before.player_x is None or after.player_x is None:
            return None
        dx, dz = after.player_x - before.player_x, after.player_z - before.player_z
        mag = (dx * dx + dz * dz) ** 0.5
        self._check_movement(mag if after.control else None, int(frames), gait, rate, what="a probe",
                             span=(before.frame, after.frame))
        if mag < frames * rate.speed(gait) * self.PROBE_MIN_FRACTION:
            return None
        return ((dx / mag, dz / mag), mag)

    #: Clearance a probe keeps from a hazard polygon, world units: one MovePC call's step (a run frame at 60
    #: fps), so the prior's angular error over a probe's reach (a few units per degree) cannot carry it in. A
    #: DISTANCE: how far a press can carry him -- its movement tail included -- is Rate.reach's to say.
    PROBE_HAZARD_PAD = 30.0
    #: A measured axis within this of its predicted direction (cos ~ 15 deg) agrees with the prior.
    PRIOR_AGREE = 0.96

    def _probe_is_clear(self, start, direction, reach: float, hazards, spread: float = 0.0, *, discs=()) -> bool:
        """Would a probe from ``start`` along unit ``direction`` for ``reach`` stay out of every hazard?

        One he stands within PROBE_HAZARD_PAD of may not be approached any closer than he already
        is. One he stands IN may be left but not re-entered: the probe may stay inside or cross its
        boundary once, never twice (:class:`~ff9mapkit.content.pathfind.Keepout` ``leave``) -- and the
        NEXT probe, planned from where this one ended, then sees it as a door beside him. Judged from
        ``start``, so the caller passes where he stands NOW, not where calibration began.

        ``spread`` (radians; route_to(smooth=True)'s holds and pushes, :meth:`_heading_spread`) is how far
        off ``direction`` the press may truly head: the calibrated basis is a measurement, and over a hold
        of a thousand units a degree is seventeen. Then the rule is kept by the whole FAN of lines within
        ``spread`` either side -- judged on the triangle from ``start`` to the fan's two edges at ``reach /
        cos(spread)``, which holds every line of it whole: a region he stands in must be left at most once
        along both edges and the middle (exact for a convex region, as every stock gateway zone is -- a
        straight line leaves one once), and any other must keep the rule's gap from the whole triangle.
        At 0 -- calibration's probes -- the single line, as before.

        ``discs`` (route_to(npcs=True): the published objects its plan kept, :meth:`_npc_discs`) are held to
        the same rule by the same line or fan, each at its own radius ``R`` and ``pad``: kept ``pad`` off
        ``R``, or -- one he stands nearer than that, or inside -- never approached closer than he stands."""
        import math
        from ff9mapkit.content import pathfind
        from ff9mapkit.scene import routes
        end = (start[0] + direction[0] * reach, start[1] + direction[1] * reach)
        edges = [_turn(direction, -spread), _turn(direction, spread)] if spread > 0 else []
        far = [(start[0] + e[0] * reach / math.cos(spread), start[1] + e[1] * reach / math.cos(spread))
               for e in edges]
        for d in discs:
            gap = math.hypot(start[0] - d["x"], start[1] - d["z"]) - d["R"]
            near = (max(0.0, pathfind.poly_gap(d["x"], d["z"], (start, far[0], far[1]))) if edges
                    else routes.seg_dist_xz(d["x"], d["z"], start, end))
            if near - d["R"] < min(d["pad"], gap) - 0.5:
                return False
        for poly in hazards:
            gap = pathfind.poly_gap(start[0], start[1], poly)
            if gap < 0:
                keep = pathfind.Keepout(poly, self.PROBE_HAZARD_PAD, leave=True)
                if any(keep.blocks_leg(start, (start[0] + e[0] * reach, start[1] + e[1] * reach))
                       for e in [direction, *edges]):
                    return False
            elif not edges:
                if pathfind.seg_poly_gap(start, end, poly) < min(self.PROBE_HAZARD_PAD, gap) - 0.5:
                    return False
            else:
                fan = (start, far[0], far[1])
                clear = min(pathfind.seg_poly_gap(fan[i], fan[(i + 1) % 3], poly) for i in range(3))
                if clear >= 0 and pathfind.poly_gap(poly[0][0], poly[0][1], fan) < 0:
                    clear = -1.0                          # the region lies wholly inside the fan
                if clear < min(self.PROBE_HAZARD_PAD, gap) - 0.5:
                    return False
        return True

    def _blind_probe_is_clear(self, here, hazards, rate: Rate | None = None, frames: int = 1) -> bool:
        """Is a BLIND probe (no prior: its direction is unknown) of ``frames`` walked frames safe from ``here``? Only
        if no hazard's boundary lies within the probe's whole reach -- the most its frames and the movement tail
        can carry him at ``rate`` (Rate.reach: one frame 60u at 60 fps -- PLAN: ``walk f=1 commanded=15
        settled=30`` -- and at 31 fps a frame holds a whole tick or two; two frames at 60 fps reach no further) --
        plus PROBE_HAZARD_PAD, in ANY direction. ``rate`` defaults to a MEASURED one (:meth:`rate`
        ``require=True``): the probe is pressed on this answer."""
        from ff9mapkit.scene import routes
        rate = self.rate(require=True) if rate is None else rate
        reach = rate.reach(frames, "walk") + self.PROBE_HAZARD_PAD
        for poly in hazards:
            n = len(poly)
            if min(routes.seg_dist_xz(here[0], here[1], poly[i], poly[(i + 1) % n]) for i in range(n)) < reach:
                return False
        return True

    def _calibrate_clear_of(self, key: int, hazards, prior: dict | None, probe: int) -> dict:
        """:meth:`calibrate_axes` for a character standing beside things he must not walk into.

        THE PROBE ORDER COMES FROM THE PRIOR. ``prior`` predicts each button's world direction (from
        the field's own TWIST, :meth:`key_prior`); a direction whose probe -- its reach plus the
        movement tail -- would enter or approach a hazard is never pressed, a run probe that would is
        tried again as a short walk probe, and an axis with only one safe side is measured one-sided.
        A one-sided measurement has no opposite press to cross-check a wall slide against, so it must
        AGREE with the prior (PRIOR_AGREE) or the calibration refuses. An axis with no safe side at
        all -- or one whose only safe side is blocked -- is DERIVED from the other: a digital press is
        rotated by a pure Y rotation (``FieldMapActorController.cs:712-720``), so up is always
        ``(-right.z, right.x)``. Never both derived: at least one axis is always a measurement.

        Without a prior every probe is a one-frame walk (the shortest press there is to SEND -- not the
        shortest SURE of a tick: one that moved nothing where a frame may hold no tick is pressed again
        for the frames that are, :meth:`_least_frames`), and both sides of an axis must agree the usual
        way. A blind probe's direction is unknown, so it is pressed only where it is safe in EVERY
        direction (:meth:`_blind_probe_is_clear`, at its own length); beside a hazard, blind calibration
        refuses instead of guessing -- pass ``prior``.

        EACH PROBE IS JUDGED FROM WHERE THE CHARACTER STANDS WHEN IT IS PRESSED: a one-sided probe
        moves him 120-180u, so the next axis's probes do not start where calibration did -- and AT THE MEASURED
        RATE (:meth:`rate` ``require=True`` whenever there is a hazard to keep): a probe's reach is the most its
        frames can carry him (Rate.reach), which at 31 fps is twice the 60 fps figure -- a 4-frame run probe
        240u and its tail, not 120. No measured rate, no probe: it raises rather than guess.

        EVERY PROBE WATCHES CONTROL: one that fires a gateway raises :class:`ProbeLeftControl` rather
        than measuring on in the next room. No backing off -- a back-off is a blind run of CLEARANCE_UNITS.
        """
        from ff9mapkit.content import pathfind   # noqa: F401 -- fail here, not mid-probe, if absent
        polys = [[(float(p[0]), float(p[1])) for p in poly] for poly in hazards]
        st = self.settle()
        if st.player_x is None:
            raise HarnessError(f"calibrate_axes on field {key}: no player position published")
        basis: dict = {}
        how: dict = {}
        for name, (fwd, back) in (("v", ("up", "down")), ("h", ("right", "left"))):
            plan = []                                         # the buttons pressed on this axis
            got = []                                          # [(button, sign, unit, length)]
            for button, sign in ((fwd, 1.0), (back, -1.0)):
                # the rate FIRST (nothing to keep clear of: any reach will do): a wait for it lets frames pass, and
                # the position the probe is judged from is read after it
                rate = self.rate(require=bool(polys))
                st = self.state                               # settled: the previous probe settled it
                if st.player_x is None:
                    raise HarnessError(f"calibrate_axes on field {key}: no player position published")
                here = (st.player_x, st.player_z)
                if prior is None:
                    if not self._blind_probe_is_clear(here, polys, rate):
                        raise HarnessError(
                            f"calibrate_axes on field {key}: a blind probe from ({here[0]:.0f}, "
                            f"{here[1]:.0f}) could reach one of {len(polys)} hazard region(s) -- its "
                            f"direction is what calibration is for. Pass prior= (key_prior(<field>), or "
                            f"movement.key_move_basis(<TWIST>) for a fork), or calibrate from open ground.")
                    frames, slow = 1, True
                else:
                    u = (prior[name][0] * sign, prior[name][1] * sign)
                    for frames, slow in ((probe, False), (2, True)):
                        if self._probe_is_clear(here, u, rate.reach(frames, "walk" if slow else "run"), polys):
                            break
                    else:
                        continue                              # both lengths lead into a hazard
                plan.append(button)
                m = self._probe_axis(button, frames, slow=slow, watch_control=True)
                if m is None and prior is None and rate.ticks_sure(frames) < 1:
                    # a blind probe of one frame may fall between two field ticks and run no MovePC call at all (at
                    # 120 fps three times in four): that is no wall. Pressed again for the frames SURE of a tick
                    # (:meth:`_least_frames`) -- judged blind again at their reach, from where he stands now
                    frames = self._least_frames(rate)
                    st = self.state
                    if st.player_x is not None and self._blind_probe_is_clear((st.player_x, st.player_z), polys,
                                                                              rate, frames):
                        m = self._probe_axis(button, frames, slow=slow, watch_control=True)
                if m is not None:
                    got.append((button, sign, m[0], m[1]))
            vec = None
            if len(got) == 2:
                (_b, _s, a, la), (_b2, _s2, b, lb) = got
                anti = -(a[0] * b[0] + a[1] * b[1])
                if anti >= 0.85 and min(la, lb) / max(la, lb) >= 0.5:
                    vec, how[name] = a, f"{fwd}/{back} {min(la, lb):.0f}u"
                    if prior is not None and a[0] * prior[name][0] + a[1] * prior[name][1] < self.PRIOR_AGREE:
                        how[name] += f", DISAGREES with the prior {_vec(prior[name])}"
            elif len(got) == 1 and prior is None:
                # blind, one side blocked: the old one-sided rule (the measurement is all there is)
                button, sign, u, length = got[0]
                vec, how[name] = (u[0] * sign, u[1] * sign), f"{button} alone {length:.0f}u, blind"
            if vec is None and prior is not None:
                for button, sign, u, length in got:
                    cand = (u[0] * sign, u[1] * sign)
                    if cand[0] * prior[name][0] + cand[1] * prior[name][1] >= self.PRIOR_AGREE:
                        vec, how[name] = cand, f"{button} alone {length:.0f}u, agrees with the prior"
                        break
                if vec is None and got:
                    raise HarnessError(
                        f"the {name} axis on field {key} disagrees with its prior: measured "
                        f"{[(b, _vec(u), round(ln)) for b, _s, u, ln in got]} against predicted "
                        f"{_vec(prior[name])}. A slide along a wall, or the prior is wrong for this "
                        f"field (a TWIST changed after Main_Init?). Calibrate from open ground.")
            if vec is None and got and prior is None:
                raise HarnessError(
                    f"the {name} axis on field {key} is not a free axis: "
                    f"{[(b, _vec(u), round(ln)) for b, _s, u, ln in got]} (probed blind, the fewest walk "
                    f"frames each, beside {len(polys)} hazard region(s)). Calibrate from open ground.")
            if vec is None:
                how[name] = (f"not probed: {fwd} and {back} both lead into a hazard" if not plan
                             else f"{'/'.join(plan)} blocked")
            basis[name] = vec
        if basis["v"] is None and basis["h"] is None:
            raise HarnessError(
                f"could not calibrate field {key} without risking a hazard: v {how['v']}; h "
                f"{how['h']}. The character is boxed in between trigger regions -- move him first.")
        if basis["v"] is None:
            basis["v"], how["v"] = (-basis["h"][1], basis["h"][0]), f"derived from right ({how['v']})"
        elif basis["h"] is None:
            basis["h"], how["h"] = (basis["v"][1], -basis["v"][0]), f"derived from up ({how['h']})"
        skew = abs(basis["v"][0] * basis["h"][0] + basis["v"][1] * basis["h"][1])
        if skew > 0.35:
            raise HarnessError(
                f"axis calibration on field {key} looks deflected: up={_vec(basis['v'])} "
                f"right={_vec(basis['h'])} are not perpendicular (|dot|={skew:.2f}). Something "
                f"(an NPC, a wall) pushed a probe. Move to clearer ground and recalibrate.")
        self._axes[key] = basis
        self._log(f"axes on field {key} (clear of {len(polys)} region(s)): up={_vec(basis['v'])} "
                  f"[{how['v']}] right={_vec(basis['h'])} [{how['h']}] |dot|={skew:.2f}")
        return basis

    def walk_to(self, x: float, z: float, *, tolerance: float = 40.0, max_bursts: int = 24,
                strict: bool = True, halt_on_transition: bool = False, slides: bool = False) -> bool:
        """Walk to a world (x, z), steering on the published position. Returns whether it arrived.

        Moves one axis at a time rather than solving a diagonal: the engine's diagonal is a single
        normalised vector split across both axes, so treating them independently converges in the same
        number of round trips without the trigonometry, and each leg is independently verifiable.

        The last leg deliberately drops to walk speed (Cancel held) under WALK_UNDER. A run tick is 60
        units -- a run frame 30 at 60 fps, ~57 at 31 -- so a run press overshoots any tight tolerance, and
        a run-only approach oscillates around the target forever and then fails on max_bursts. A burst is
        SIZED at the measured rate's average speed (:meth:`rate`, Rate.frames_for) -- at 31 fps half the
        frames 60 fps would take -- and capped at ROUTE_HOLD_TICKS of field ticks, like a smooth hold. A
        burst that may have run NO field tick (fewer frames than one is sure to hold, Rate.ticks_sure --
        a 25u walked hop is one frame at 60 fps, a quarter tick at 120) and moved him nothing proves
        nothing: no stall, and the next burst is the fewest frames sure of a tick (:meth:`_least_frames`,
        :meth:`_walk_leg`'s own rule) -- counted as a wall, two such in a row read open floor as a wall.

        Gives up early when a burst produces no progress -- that is a wall or a walkmesh edge, and
        retrying it 24 times just turns a clear failure into a slow one.

        ``halt_on_transition`` stops (returning False) the moment the player has lost control, before
        another burst is issued. A gateway takes control on the frame it fires but the field id only
        changes a fade later, so without it the next "correction" burst is pressed during the fade and
        its hold carries into the DESTINATION -- where, at an arrival spot beside the door, it walks the
        player straight back. :meth:`route_to` always sets it; the default keeps the old loop.

        ``slides`` is for a LIVE room (:meth:`route_to` ``unstick``). A burst pressed into someone
        standing a little off the pressed line is pushed back out along the line from that body's
        centre (FieldMapActorController.cs:776-797): he slides SIDEWAYS, and the basis check below
        reads that as a wrong basis -- raises, and throws a good basis away. With ``slides`` such a
        burst ends the walk instead (not arrived, basis kept), for the caller to treat as a stall.
        """
        # A tolerance under half a MovePC step cannot be aimed for -- the smallest correction the engine
        # can make is one call of travel, so the loop oscillates around the target and then fails on
        # max_bursts, reporting the field unreachable when the request was impossible.
        if tolerance < self.HALF_STEP:
            raise HarnessError(
                f"tolerance {tolerance} is below the physical floor: one MovePC call steps him "
                f"{STEP_PER_CALL:g} units, so nothing closer than half of one ({self.HALF_STEP:g}) can be "
                f"aimed for."
            )
        basis = self.calibrate_axes()
        field = self.state.field_id
        stalls = 0
        least = 1                     # the least burst: sure of a tick after one that may have run none (below)
        for _ in range(max_bursts):
            # ⚠ SETTLED, so this burst's displacement is this burst's. The engine's movement runs a
            # few frames behind the input, so the previous burst is often still carrying the
            # character when the next one is issued -- see settle().
            st = self.settle()
            # Walking somewhere can END the field: step into a gateway and the destination is
            # loading, so there is no position to steer by. The first version treated that as an
            # error and then did arithmetic on None anyway, so a probe that successfully found a
            # gateway crashed the run instead of reporting it. Leaving the field is a legitimate
            # outcome of walking -- stop cleanly and let the caller notice.
            if st.field_id != field or st.player_x is None:
                return False
            if halt_on_transition and not st.control:
                return False          # something took control (a gateway's ExitField): no more presses
            dx, dz = x - st.player_x, z - st.player_z
            remaining = (dx * dx + dz * dz) ** 0.5
            if remaining <= tolerance:
                return True

            direction, need, axis, sign = _press_axis(basis, dx, dz)
            rate = self.rate()
            slow = need < self.WALK_UNDER                          # under a run tick and a half: walk it
            gait = "walk" if slow else "run"
            frames = max(least, min(self._frames_within(self.ROUTE_HOLD_TICKS, rate), rate.frames_for(need, gait)))
            steps = [f"hold {direction} {frames}"]
            if slow:
                steps.insert(0, f"hold cancel {frames}")
            self.send(*steps, f"wait {frames + 4}")

            after = self.settle()
            if after.field_id != field or after.player_x is None:
                return False          # the burst carried us out of the field -- see above
            if halt_on_transition and not after.control:
                return False          # ...or into a trigger; its scripted walk is not this burst's
            mx, mz = after.player_x - st.player_x, after.player_z - st.player_z
            moved = (mx * mx + mz * mz) ** 0.5
            self._check_movement(moved if after.control else None, frames, gait, rate, what="a burst",
                                 span=(st.frame, after.frame))

            # THE BASIS CONSISTENCY CHECK. Calibration can be fooled -- a character pressed into a
            # wall keeps moving, just not where he was sent, and the resulting basis is a well-formed
            # lie that no static test on two unit vectors can catch. What a bad basis cannot fake is
            # agreement over time: if a burst covers a real distance in a direction that does not
            # project onto the axis it was sent along, the basis is wrong and every later burst is
            # steering by it. Say so, and throw the basis away, instead of grinding out max_bursts
            # and then blaming the field's geometry.
            if self._burst_is_evidence(moved, frames, gait, rate):
                projected = (mx * axis[0] + mz * axis[1]) * sign
                if projected < 0.35 * moved and slides:
                    self._log(f"  walk_to: holding {direction} slid him {moved:.0f}u along ({mx:+.0f},{mz:+.0f}) "
                              f"-- round someone in the way, not a wrong basis; stopping here")
                    break
                if projected < 0.35 * moved:
                    self._axes.pop(field, None)
                    raise HarnessError(
                        f"the axis basis for field {field} disagrees with what the game did: "
                        f"holding {direction} moved {moved:.0f}u along ({mx:+.0f},{mz:+.0f}), which "
                        f"projects only {projected:.0f}u onto the calibrated axis {_vec(axis)}. The "
                        f"basis was probably measured against a wall; it has been discarded. "
                        f"Recalibrate from open ground."
                    )

            # An overshoot counts as a stall. Without it, a loop that steps past the target and back
            # again shows progress every time and burns all 24 bursts before failing.
            left = (x - after.player_x) * axis[0] + (z - after.player_z) * axis[1]
            overshot = left * sign < 0 and abs(left) > tolerance
            if moved < 1.0 and rate.ticks_sure(frames) < 1:
                # a burst whose frames may all fall between two field ticks ran no MovePC call, perhaps -- and moved
                # nothing: no wall, no stall (_walk_leg's own rule). The next burst is sure of a tick
                least = self._least_frames(rate)
                continue
            least = 1
            stalls = stalls + 1 if (moved < 1.0 or overshot) else 0
            if stalls >= 2:
                break

        # ONE final sample decides the verdict, the reported position AND the reported distance.
        # Taking three (as this used to) lets the message describe a position the verdict was not
        # computed from -- and on a character still settling they genuinely differ.
        final = self.state
        if final.field_id != field or final.player_x is None:
            return False
        gap = ((final.player_x - x) ** 2 + (final.player_z - z) ** 2) ** 0.5
        arrived = gap <= tolerance
        if not arrived and strict:
            raise HarnessError(
                f"could not reach ({x}, {z}): stopped at ({final.player_x}, {final.player_z}), "
                f"{gap:.0f} units away. A wall, a walkmesh edge, or an unreachable target."
            )
        return arrived

    def climb(self, button: str = "up", *, until, burst_frames: int = 30, max_bursts: int = 80,
              stall_bursts: int = 3, start_timeout: float = 5.0) -> dict:
        """Climb the ladder a scene has put him on, by holding ``button`` (research/o2_design.md H2: 115's ladder --
        its Confirm runs e15 t3, DisableMove, and the climb loop reads B_KEY(16) every tick) until ``until(state)``.

        A CLIMB RUNS WITH CONTROL OFF. It first waits up to ``start_timeout`` for control to go (the press that
        started it takes it); still held then, nothing is pressed and it ends ``"not-started"``. Then it holds
        ``button`` in BURSTS -- ``hold <button> <burst_frames>`` and ``wait <burst_frames + 2>`` in one request, as
        :meth:`walk` does -- and reads the state after each. First match ends it: ``until(st)`` -> "until"; the field
        changed -> "field"; control back -> "control" (he slid to the bottom: its EnableMove); y moved less than 1u in
        each of ``stall_bursts`` bursts in a row, counted from the first -> "stalled" (a ladder the button does not
        climb); ``max_bursts`` spent -> "bursts". It never presses or holds anything but ``button``: Down and Right
        DESCEND (B_KEY(96)).

        Returns ``{"ended", "bursts", "frames", "y0", "y1", "ys"}``: the bursts and frames held, his y before the
        first burst and after the last, and after each (``ys``)."""
        button = _button(button)
        st = self._require_field("climb")
        field = st.field_id
        out = {"ended": None, "bursts": 0, "frames": 0, "y0": st.player_y, "y1": st.player_y, "ys": []}
        try:
            st = self.wait_for(lambda s: not s.control or s.field_id != field, timeout=start_timeout,
                               what="the climb to take control")
        except HarnessError as err:
            if "live samples" not in str(err):
                raise                                 # a frozen or silent channel says nothing about the climb
            out["ended"] = "not-started"
            self._log(f"  climb: control still held {start_timeout:.0f}s after it was asked for: not started")
            return out
        out["y0"] = out["y1"] = last = st.player_y
        still = 0
        for n in range(1, max(1, int(max_bursts)) + 1):
            self.send(f"hold {button} {int(burst_frames)}", f"wait {int(burst_frames) + 2}")
            st = self.state
            y = st.player_y
            out["bursts"], out["frames"] = n, out["frames"] + int(burst_frames)
            out["ys"].append(y)
            out["y1"] = y
            if until(st):
                out["ended"] = "until"
                return out
            if st.field_id != field:
                out["ended"] = "field"
                return out
            if st.control:
                out["ended"] = "control"
                return out
            moved = abs(y - last) if None not in (y, last) else 0.0
            still = still + 1 if moved < 1.0 else 0
            last = y
            if still >= stall_bursts:
                out["ended"] = "stalled"
                self._log(f"  climb: {still} bursts of {button} moved him nothing (y {y}): stalled")
                return out
        out["ended"] = "bursts"
        return out

    def lunge(self, x: float, z: float, *, ticks: int = 10, avoid=(), walkmesh=None, margin: float | None = None,
              gait: str = "run") -> dict:
        """ONE hold toward (x, z) on the first live sample with control: no settle, no calibration, no plan -- the
        leave-at-once press (research/o2_design.md H3: 105's lookout, where Alleyway Jack's contact reaches him about
        1.5-2 s after control comes).

        It needs control NOW (one live sample) and a CACHED basis for the field (:meth:`calibrate_axes` ran on this
        field earlier): without either it raises, pressing nothing. The pad is the one of the eight (:func:`_eight_way`)
        nearest the bearing to the goal. The hold is ``Rate.frames_for_ticks(ticks)`` frames at the MEASURED rate
        (:meth:`rate` ``require=True``: its reach is judged), clipped to the longest that keeps its whole line -- out to
        ``Rate.reach(frames, gait)``, tail included -- on ``walkmesh`` (default: the install's for the field) at least
        cam.COLLISION_RADIUS_W off every wall, sampled every 16u; ``margin`` (default pathfind.KEEPOUT_MARGIN_W) clear
        of every ``avoid`` polygon (pathfind.seg_poly_gap); and short of the goal's projection on the line. A hold
        under the frames sure of one tick presses nothing (``pressed`` False).

        The hold is sent as ``hold <b> <frames>`` for each button of the pad and ``wait <frames + 2>``, in ONE request,
        and the state read once after it. Returns ``{"pressed", "pad", "frames", "from", "to", "travelled",
        "sample_frame", "done_frame"}``: ``sample_frame`` the frame of the control sample it acted on, ``done_frame``
        the frame of the read after the hold -- so a caller can read the latency."""
        import math
        from ff9mapkit.content import pathfind
        from ff9mapkit.scene import cam
        st = self.state
        if st.ui_state != "FieldHUD" or not st.control or st.player_x is None or st.fading:
            raise HarnessError(f"lunge needs control NOW, on a field: the newest sample has none ({st!r})")
        field = st.field_id
        basis = self._axes.get(field)
        if basis is None:
            raise HarnessError(f"lunge on field {field}: no CACHED basis -- it presses at once, and a calibration is "
                               f"a walk of its own. Calibrate on this field first (calibrate_axes, or a routed walk).")
        margin = pathfind.KEEPOUT_MARGIN_W if margin is None else float(margin)
        here = (float(st.player_x), float(st.player_z))
        dx, dz = float(x) - here[0], float(z) - here[1]
        buttons, u = max(_eight_way(basis), key=lambda p: p[1][0] * dx + p[1][1] * dz)
        pad = "+".join(buttons)
        ahead = u[0] * dx + u[1] * dz                     # the goal's projection on the pressed line
        rate = self.rate(require=True)
        floor = walkmesh if walkmesh is not None else self._stock_walkmesh(field)
        polys = [[(float(p[0]), float(p[1])) for p in poly] for poly in avoid]

        def clear(n: int) -> bool:
            reach = rate.reach(n, gait)
            if reach > ahead:
                return False
            end = (here[0] + u[0] * reach, here[1] + u[1] * reach)
            for k in range(1, int(math.ceil(reach / 16.0)) + 1):
                t = min(reach, 16.0 * k)
                px, pz = here[0] + u[0] * t, here[1] + u[1] * t
                if floor.point_on_walkmesh(px, pz) is None:
                    return False
                wall = floor.distance_to_boundary(px, pz)
                if wall is None or wall < cam.COLLISION_RADIUS_W:
                    return False
            return all(pathfind.seg_poly_gap(here, end, poly) >= margin for poly in polys)

        frames = rate.frames_for_ticks(int(ticks))
        while frames > 0 and not clear(frames):
            frames -= 1
        out = {"pressed": False, "pad": pad, "frames": 0, "from": [round(here[0]), round(here[1])], "to": None,
               "travelled": 0.0, "sample_frame": st.frame, "done_frame": None}
        if frames < rate.frames_for_ticks(1):
            self._log(f"  lunge: no hold of {pad} toward ({x:.0f}, {z:.0f}) from ({here[0]:.0f}, {here[1]:.0f}) "
                      f"keeps its line clear for a whole tick: nothing pressed")
            return out
        steps = [f"hold {b} {frames}" for b in buttons]
        if gait == "walk":
            steps.insert(0, f"hold cancel {frames}")
        self.send(*steps, f"wait {frames + 2}")
        after = self.state
        out.update(pressed=True, frames=frames, done_frame=after.frame)
        if after.player_x is not None:
            out["to"] = [round(after.player_x), round(after.player_z)]
            if after.field_id == field:
                out["travelled"] = round(math.hypot(after.player_x - here[0], after.player_z - here[1]), 1)
        return out

    def newgame(self, *, timeout: float = 120.0, playable: bool = False,
                settle: float | None = None) -> State:
        """Title screen -> New Game -> in-game.

        Waits for a FIELD to be up, NOT for control. New Game lands in the opening cutscene (stock
        field 70 unless a campaign has re-wired the override), where control is deliberately withheld
        for minutes -- so requiring it here hangs every scenario whose actual intent is "get in-game,
        then warp to the thing I am testing". Pass ``playable=True`` only when the scenario really
        does mean to play from the opening.

        ``settle`` holds on the title screen before starting. Memoria is still loading when the title
        first appears, and starting a new game during that window makes the opening cutscene run
        badly choppy -- which a scenario asserting on cutscene timing would then blame on itself.

        ⚠ That reason applies to the FIRST title only. Coming back to the title later -- which is
        exactly what a suite does between scenarios -- the game is fully loaded and the wait is pure
        dead time, once per scenario. So the default is the settle on a cold title and nothing on a
        re-entry. Pass an explicit number to override either way.
        """
        if settle is None:
            settle = 0.0 if self._booted_once else TITLE_SETTLE
        self.wait_for(lambda s: s.ui_state == "Title", timeout=timeout, what="the title screen")
        if settle > 0:
            self._log(f"settling {settle:.0f}s on the title (Memoria is still loading)")
            self._sleep_alive(settle)
        self.send("newgame")
        st = self.wait_for(lambda s: s.ui_state == "FieldHUD" and s.field_id > 0,
                           timeout=timeout, what="New Game to reach a field")
        self._booted_once = True
        return self.wait_playable(timeout=timeout) if playable else st

    def registered_fields(self) -> tuple[dict[int, str], list[Path]]:
        """Mod-registered field ids (id -> scene name) AND the patch files actually read.

        Read from the `DictionaryPatch.txt` of each mod folder, which CLAUDE.md is emphatic is the
        only truth about what is deployed -- it changes as other worktrees deploy, so it is read live
        rather than cached across runs.

        ⚠ Returns the file list too, because "nothing is registered" and "I could not read the
        registrations" are different facts and the caller must not merge them. A guard that treats an
        empty answer as permission disables itself in precisely the situation where it is least able
        to be sure.

        The directive is `FieldScene <id> <area> <NAME> ...` -- the second column is the AREA index,
        not the name, which is why group 3 is taken.
        """
        found: dict[int, str] = {}
        read: list[Path] = []
        for patch, rows in scan_registrations(self.game_path):
            read.append(patch)
            for fid, name in rows:
                found.setdefault(fid, name)
        return found, read

    def _check_field_id(self, field: int, verb: str, check_registered: bool) -> None:
        """Refuse a destination the engine cannot reach, and say which kind of unreachable it is.

        Warping to an unregistered id is not a harmless no-op: the engine sets `fldMapNo`, finds a
        null `.eb`, and hangs on a black screen with the game unrecoverable -- which reaches the
        driver as a generic timeout whose message points at control or position rather than at the
        actual mistake.
        """
        if not 0 <= field <= MAX_FIELD_ID:
            raise HarnessError(
                f"{verb}: field id {field} is out of range. `fldMapNo` is Int16, so anything above "
                f"{MAX_FIELD_ID} wraps onto a DIFFERENT (possibly real) field and the wait for the "
                f"id you asked for can never be satisfied."
            )
        if not check_registered:
            return
        available, read = self.registered_fields()
        if not read:
            raise HarnessError(
                f"{verb}: no DictionaryPatch.txt could be read under {self.game_path}, so whether "
                f"field {field} is deployed is unknown. Refusing rather than risking the null-.eb "
                f"black screen -- pass check_registered=False to override."
            )
        if field in available:
            return
        # ⚠ DictionaryPatch lists only MOD registrations. Every one of FF9's ~674 shipping rooms is
        # registered by the base game and appears in none of these files, so a membership test
        # against them alone would refuse a real field with a false claim about a null `.eb`.
        if field in stock_field_ids():
            return
        raise HarnessError(
            f"{verb}: field {field} is neither a stock FF9 field nor listed in any deployed "
            f"DictionaryPatch.txt ({', '.join(p.parent.name for p in read)}), so warping there "
            f"would black-screen the game on a null .eb. Deploy it first "
            f"(`py tools/deploy_field.py <toml> --id {field}`), or use one of: "
            f"{', '.join(str(i) for i in sorted(available))}."
        )

    def warp(self, field: int, *, entrance: int | None = None, scenario: int | None = None,
             timeout: float = 60.0, check_registered: bool = True) -> State:
        """Warp to a field and wait until it is actually playable.

        Refuses an UNREGISTERED id up front. Warping to one is not a harmless no-op: the engine sets
        `fldMapNo`, finds a null `.eb`, and hangs on a black screen with the game unrecoverable --
        which reaches the driver as a generic 60-second timeout whose message points at control or
        position rather than at the actual mistake. Since ids are a global namespace shared with
        every other worktree's deploys, the id you tested yesterday may simply not be there today.
        """
        field = int(field)
        self._check_field_id(field, "warp", check_registered)
        self.send(f"warp {field} {entrance if entrance is not None else -1} "
                  f"{scenario if scenario is not None else -1}")
        self.wait_for(lambda s: s.field_id == int(field), timeout=timeout,
                      what=f"field {field} to load")
        return self.wait_playable(timeout=timeout)

    def world_warp(self, field: int, *, entrance: int | None = None, scenario: int | None = None,
                   timeout: float = 60.0, check_registered: bool = True) -> State:
        """Enter a field FROM the overworld. Same guards as :meth:`warp`, and it waits for control.

        ⚠ The engine refuses this outright when the game is not on an overworld -- and until the
        agent reports refusals, that refusal ACKS CLEAN. The wait that follows then times out
        blaming a destination the engine never attempted, so the guard is here on the driver side.
        """
        field = int(field)
        self._check_field_id(field, "world_warp", check_registered)
        st = self.state
        if st.ui_state != "WorldHUD":
            raise HarnessError(
                f"world_warp enters a field FROM the overworld and the game is on "
                f"ui_state={st.ui_state!r}. The engine would refuse this silently; use warp() on a "
                f"field."
            )
        self.send(f"worldwarp {field} {entrance if entrance is not None else -1} "
                  f"{scenario if scenario is not None else -1}")
        self.wait_for(lambda s: s.field_id == field, timeout=timeout,
                      what=f"field {field} to load from the world map")
        return self.wait_playable(timeout=timeout)

    def teleport(self, x: float, z: float, *, verify: bool = True,
                 timeout: float = 10.0) -> State:
        """Overworld teleport (world units), verified against the position that resulted.

        ⚠ The engine has several refusal paths here -- not in world mode, outside the 24x20 grid --
        and each one currently ACKS CLEAN while doing nothing. A scenario that teleported, walked and
        then recorded a placement verdict about the map would be describing wherever it already was.
        So this asserts on the OUTCOME: the published world position moved to where it was sent.
        """
        st = self.state
        if st.ui_state != "WorldHUD":
            raise HarnessError(
                f"teleport is an OVERWORLD verb and the game is on ui_state={st.ui_state!r}. The "
                f"engine would refuse it silently and the run would go on believing it moved."
            )
        self.send(f"teleport {x} {z}")
        if not verify:
            return self.state
        return self.wait_for(
            lambda s: (s.world_x is not None
                       and ((s.world_x - x) ** 2 + (s.world_z - z) ** 2) ** 0.5 < 64.0),
            timeout=timeout,
            what=f"the world position to become ({x}, {z}) -- if it did not, the engine refused the "
                 f"teleport (outside the grid, or not in world mode)",
        )

    # -- crossing between fields ----------------------------------------------------------------
    # Gateways are the most common mechanic in this project and the hardest to eyeball: a trigger is
    # an invisible region, so "is the gateway where I think it is" has historically been a question
    # only a human walking into it could answer.

    def expect_field_change(self, *, timeout: float = 25.0, was: int | None = None,
                            record: dict | None = None) -> int:
        """Wait for the field id to change and return the new one.

        Waits for the destination to be PLAYABLE, not merely for the id to flip. The id changes the
        moment the engine accepts the transition, while the destination is still black -- and a
        scenario that continued there would issue its next steps into a loading screen.

        ⚠ The two waits are deliberately NOT merged, and callers must not swallow them together.
        "The field never changed" and "the field changed but the destination never handed over
        control" are opposite findings: the first means there is no gateway here, the second means
        there is one and it leads somewhere broken. Collapsing them reported a working gateway as a
        missing one.

        The id returned is where control came back, which is not always where the id first went: a
        room whose arrival scene puts him straight back where he came from, inside the wait, returns
        ``was``. ``record`` (a crossing record) gets that first id as ``changed_to`` the moment the id
        flips -- where the crossing ENTERED, whatever the wait for control then finds.
        """
        was = self.state.field_id if was is None else was
        self.wait_for(lambda s: s.field_id != was and s.field_id > 0,
                      timeout=timeout, what=f"the field to change from {was}")
        landed = self.state.field_id
        if record is not None:
            record["changed_to"] = landed
        try:
            return self.wait_playable(timeout=timeout).field_id
        except HarnessError as err:
            raise HarnessError(
                f"crossing from {was} reached field {landed}, but it never became playable within "
                f"{timeout:.0f}s -- the gateway WORKS and the destination is the problem. ({err})"
            ) from err

    def cross(self, x: float, z: float, *, expect: int | None = None,
              timeout: float = 20.0) -> dict:
        """Walk to (x, z) and report what happened, as a record rather than a bare id.

        Returns ``{"landed": id|None, "from": id, "reached": bool, "travelled": units}``. It returns
        rather than raises on "nothing happened": when probing for an invisible trigger, not crossing
        is the ordinary outcome and the caller wants to keep looking. ``travelled`` and ``reached``
        are what stop a sweep that never actually got near the target from being read as evidence
        that nothing is there.

        Pass `expect` to assert a specific destination.
        """
        st = self.state
        origin, ox, oz = st.field_id, st.player_x, st.player_z
        reached = self.walk_to(x, z, tolerance=45.0, strict=False)
        after = self.state
        travelled = 0.0
        if None not in (ox, oz, after.player_x, after.player_z) and after.field_id == origin:
            travelled = ((after.player_x - ox) ** 2 + (after.player_z - oz) ** 2) ** 0.5
        record = {"from": origin, "landed": None, "reached": bool(reached),
                  "travelled": round(travelled, 1), "toward": [round(x), round(z)]}
        try:
            record["landed"] = self.expect_field_change(timeout=timeout, was=origin)
        except HarnessError as err:
            # Only "the field never changed" is an ordinary negative. A destination that loaded and
            # then failed to hand over control is a real finding and must not be swallowed as one.
            if "never became playable" in str(err):
                raise
            # Re-read: a crossing can land after the wait expired.
            now = self.state.field_id
            if now != origin and now > 0:
                record["landed"] = now
        if expect is not None and record["landed"] != expect:
            raise HarnessError(f"crossing at ({x}, {z}) led to field {record['landed']}, "
                               f"expected {expect}")
        return record

    # -- routed walking ---------------------------------------------------------------------------
    # walk_to steers one axis at a time with no idea where the doors are. On stock 350 that was fatal:
    # the arrival from 351 stands 18u from 351's own gateway, and the first press toward the next exit
    # -- or the calibration probe before it -- stepped straight back through it, eighty times. The
    # routed verbs plan over the field's real walkmesh, keep out of every gateway region they were not
    # sent to, and stop pressing the moment anything takes control away.
    #
    # THE FRAME, measured before building on it: the published player position IS the field script's
    # coordinate space (stock 552's arrivals for entrances 3 and 5, 105's default, 1606's entrance 11
    # and 2507's entrance 128 each land on the script's own D9 x/z literal EXACTLY), and SetRegion
    # corners are the same script's literals; every recorded standing position of those fields lies on
    # the install's walkmesh through BgiWalkmesh.world_verts (vert + orgPos + floor.org), and 2507's
    # wall-slide samples sit 80-81u from its boundary -- the controller radius. No transform.

    #: A route leg is walked in chunks no longer than this: walk_to's one-axis steering turns a
    #: diagonal leg into an L whose corner sits up to half a chunk off the planned line.
    ROUTE_CHUNK_MAX = 360.0
    ROUTE_CHUNK_MIN = 48.0
    #: How close an intermediate chunk point must be reached; the final goal uses the caller's.
    ROUTE_WAYPOINT_TOLERANCE = 45.0
    #: Replans from wherever a leg stalled (a wall the grid did not see, an NPC) before giving up.
    ROUTE_REPLANS = 2
    #: route_to(unstick=True) at a stall with control held: SECONDS to WAIT before walking the same chunk again
    #: (:meth:`_frames_lasting`: 90 frames at 60 fps, 45 at 30, 180 at 120), how many times per stall, and how many
    #: waits one call may spend in all. An NPC walking through, or a movement freeze the agent cannot see (the
    #: script's pad mask), clears in that -- on the wall clock: a walker steps and a script counts once a field TICK,
    #: FieldTPS a second. (Once 90 FRAMES, which at 120 fps waited 0.75 s and the ladder climbed to a push sooner.)
    ROUTE_WAIT_SECONDS = 1.5
    ROUTE_WAITS = 2
    ROUTE_WAIT_BUDGET = 8
    #: route_to(unstick=True), still stuck after the waits: ONE unbroken hold INTO whoever is in the way.
    #: The engine lets the player through any body without object flag 16 (no NPC on stock 350 sets it)
    #: once he has pressed into it for 26 MovePC calls unbroken: CheckCollFallback counts sLockTimer up
    #: one a colliding call, flips it to -25 at 25, and the push-out is off until it counts back to 0
    #: (FieldMapActorController.cs:768-822). A walk_to burst never gets there -- a chunk is at most
    #: ROUTE_CHUNK_MAX, 12 run calls at any rate, and the gap before the next one resets the count. The lock is this
    #: many MovePC calls into him
    #: unbroken (the 27th is the first not pushed back) -- and a running player makes two a tick, in WHOLE ticks,
    #: so the hold is the fewest frames SURE to hold ceil(27 / 2) = 14 run ticks at the measured rate
    #: (Rate.frames_for_ticks: 28 frames at 60 fps, 14 at 30; frames sized at 30u a frame -- 27 -- ran 13.5 calls
    #: at 120 fps and never opened it); the hold then presses on for what the chunk needs.
    ROUTE_PUSH_LOCK_CALLS = 27
    ROUTE_PUSH_BUDGET = 6
    #: Unseen blockers one route_to(unstick=True) call may place, each followed by a replan round it.
    ROUTE_BLOCKERS = 3
    #: Seconds an unseen blocker is remembered on its field visit. People in a live room walk about --
    #: the Dali villagers do between frames -- so a blocker is a guess about where someone STOOD, and it
    #: ages out rather than steering the rest of the visit round someone who has left.
    ROUTE_BLOCKER_TTL = 20.0
    #: route_cross with a ``zone``: how long to wait for a crossing when the walk ended OUTSIDE it with
    #: control held. A gateway cannot fire from there; the wait only covers a trigger still settling.
    ROUTE_OUTSIDE_WAIT = 2.0
    #: route_to(smooth=True): the most FIELD TICKS one hold may run -- walk_to's own burst cap, so a hold that walks
    #: into the exit it was sent to (the one region it may enter) runs on into the ExitField fade no longer than a
    #: burst could: three quarters of a second of the fade's own ticks, the frames sure to run no more
    #: (:meth:`_frames_within`: 45 at 60 fps, 22 at 30 -- held as 45 FRAMES, a 30 fps game ran 1.5 s into the fade)
    #: -- and the most holds one leg may take (walk_to's max_bursts).
    ROUTE_HOLD_TICKS = 22.5
    ROUTE_HOLDS = 24
    #: route_to(smooth=True): the least heading error, degrees, a hold on a calibrated basis is planned for
    #: (:meth:`_heading_spread`). The longest hold runs ~1400u with its tail, and a line held that far is
    #: only as good as its direction: 2 degrees is 49u off at its end. The in-game run's two-sided
    #: calibrations agreed with their priors within that; its one-sided ones did not (352's up 6.3 degrees
    #: off the truth, 350's right 1.4) -- a basis that disagrees with its prior adds the disagreement.
    ROUTE_HEADING_FLOOR = 2.0
    #: route_to(smooth=True, zone=...): how far round him the last leg looks for a spot IN the zone where his
    #: centre can stand (:meth:`_zone_foothold`), once he is within HALF_STEP of the goal and still out.
    ROUTE_FOOTHOLD_REACH = 96.0
    #: route_to(face=...) / route_cross(gate=...) at a gated door: STOCK'S DOOR FACING GATE (content.doorface). On 102
    #: stock gateways -- 6 of stock 350's 9 walk-in doors -- the region's tag 2 lets the warp run only while he FACES
    #: his projection onto the zone's first edge, his yaw within 47/256 of a turn of it; and the yaw turns only while a
    #: direction is held, 40% of the way a MovePC call. A walk that stops in the zone facing elsewhere stands there with
    #: the door shut for good (350 -> 351: 10 of 10 session-2 runs, each a REAL miss). So a walk that ends IN a GATED
    #: door's region (scan_gateways' ``face_gate``: a door with no gate fires the first tick he stands in it, and one
    #: still shut is shut), with control and nothing fired ROUTE_FACE_WAIT_TICKS field ticks later (the frames sure to
    #: hold them at the measured rate, Rate.frames_for_ticks: 4 at 60 fps, 2 at 30, 8 at 120 -- once 4 FRAMES, which at
    #: 120 fps held a single tick, and a door that fired on the next one was landed as the facing press's), ends with a
    #: press that turns him to face it (:meth:`_face_the_door`): walked, the least reach
    #: a MovePC call can cost; ROUTE_FACE_CALLS WHOLE calls at the least (Rate.calls_sure), after which the
    #: nearest pad faces it from any yaw (doorface.worst_face_error); never planned past ROUTE_FACE_MAX_CALLS of one pad
    #: (3 degrees of the turn left: more buys nothing). Where no whole press keeps the rules, shorter bursts may,
    #: ROUTE_FACE_PRESSES presses in all at the most. Where a press may carry him is judged on a grid ROUTE_FACE_GRID
    #: units apart (:meth:`_face_reach`). That press is the OPEN loop, for an engine that cannot publish the facing;
    #: one that can (memoria-patch s90) turns him in place instead and reads the outcome (ROUTE_TURN_* below).
    ROUTE_FACE_WAIT_TICKS = 2
    ROUTE_FACE_CALLS = 4
    ROUTE_FACE_MAX_CALLS = 8
    ROUTE_FACE_PRESSES = 8
    ROUTE_FACE_GRID = 4.0
    #: route_to(face=...) on an engine that PUBLISHES the facing (memoria-patch s90, State.facing_status "known"): THE
    #: CLOSED LOOP (:meth:`_turn_to_the_door`). The facing step turns him IN PLACE (:meth:`turn_in_place`: the keys
    #: with no axis -- each MovePC call turns him 40% of the way and steps him nowhere) and judges the gate on the
    #: facing byte the engine reports once the field has judged it, instead of predicting it from a walked press. A
    #: turn is ROUTE_TURN_CALLS whole calls of the pad nearest the door's bearing at the RUN rate (two a 30 Hz tick),
    #: held for the frames SURE of them at the measured rate (Rate.frames_for_calls): twice ROUTE_FACE_CALLS, the
    #: margin for a rate taken wrong -- the calibrated default before any is measured, a switch not yet seen -- and in
    #: place, more calls cost only frames (the lerp converges on the pad, never past it). A turn the engine reports
    #: out of the window turns again, at most ROUTE_TURN_TRIES turns in all (refusals waited out included). A turn
    #: that MOVED his yaw, by less than ROUTE_TURN_SETTLED degrees, had nothing left to turn -- that pad heads where it
    #: left him -- and is not turned again: the next pad is ranked by what that heading says of the basis. A turn that
    #: did not move his yaw AT ALL (``yaw`` == ``yaw0`` at the agent's 0.001 print) proves no call ran: the calls come
    #: whole, 30 Hz ticks on the wall clock (FPSManager.cs:77-110), and a turn sized at a rate taken wrong (see above)
    #: can fit its frames between two -- or the pad already heads where he stands. Nothing is learnt from it: that pad
    #: is turned again
    #: for twice the frames (and every turn after it keeps the longer count), and only a second unmoved turn of it in
    #: a row settles it. A ``turn_end`` that moved him more than ROUTE_TURN_MOVED -- the agent's ceiling for a turn in
    #: place, the walkmesh re-projection's float noise (0.075u at +-16000, 0.18u at +-30000: HarnessAgent.BeginTurn)
    #: -- was not one: a push-out or a wall's edge force moved him, and it is judged as the press it was, from where
    #: it left him.
    ROUTE_TURN_CALLS = 2 * ROUTE_FACE_CALLS
    ROUTE_TURN_TRIES = 6
    ROUTE_TURN_SETTLED = 4.0
    ROUTE_TURN_MOVED = 0.25
    #: The ``turn`` refusals (channel.TURN_REFUSALS) a walked PRESS does not share, where the closed loop falls back to
    #: the open-loop press (:meth:`_face_the_door`) at once instead of waiting one out: ``cannot`` (``unknown op
    #: 'turn'``: the engine has no s90, whatever a sample said) and ``analog`` (``[AnalogControl] Enabled=0``: the key
    #: path steps him -- which a walked press does on purpose, planned for). ``overlap`` (a body he overlaps would push
    #: a turn in place out -- "step clear of that body first", the s90 contract) is waited out ONCE for that body,
    #: ROUTE_WAIT_SECONDS, as a walker walks on; the SAME body still on him after it is one that stays, and the press,
    #: planned to move him clear of the objects by its own rules, is the step. Every other refusal a press shares --
    #: without control, movement, a field HUD or a readable player MovePC turns no one; a direction held, a turn still
    #: being judged, a stick or a mouse walk would fight the press's keys as they fight the turn's -- and is waited
    #: out, or ends the step, in place.
    TURN_FALLBACK = ("cannot", "analog")
    #: route_to(npcs=True) plans round the field's published objects (memoria-patch s89, :meth:`_npc_discs`).
    #: A BODY is a disc of its published ``r`` -- the centre distance the engine keeps him at -- planned
    #: ROUTE_BODY_MARGIN wider, and a hold keeps ROUTE_BODY_PAD off ``r`` itself. Touching one costs a slide round
    #: it or a stall, never a wrong room, so its margin only has to carry the walk's own drift past it: a chunk's
    #: L or a hold strays up to ROUTE_CHUNK_MIN / 2 off a leg that close, leaving ROUTE_BODY_PAD. A TRIGGER
    #: (``range_r``, ``talk_r``) fires a script the walk did not choose -- a warp, a battle -- which is what an
    #: exit zone does, so it is kept out of like one: the call's ``margin`` wide, PROBE_HAZARD_PAD for a hold. A plan
    #: that cannot keep those margins keeps only the pads a hold keeps (the TIGHT radius, :meth:`_npc_discs` ``T``)
    #: before it gives any object up: a lane a margin closes is still a lane the walk can hold.
    ROUTE_BODY_MARGIN = 32.0
    ROUTE_BODY_PAD = 8.0
    #: The engine pairs the player with an object only while they are this close in y (WalkMesh.cs:922): a body
    #: on another floor neither blocks nor fires.
    NPC_DY_BAND = 400.0
    #: route_to(npcs=True): how far a published object must have moved since the plan before it can cause a
    #: re-plan -- an idle actor's position jitters; a walker covers this in a frame or two -- and how many re-plans
    #: one call may make for movement. After those a walker that keeps crossing the path is met by the stall
    #: ladder (a wait first: "wait for it" is a real answer), never re-planned round without end.
    ROUTE_NPC_MOVED = 16.0
    ROUTE_NPC_REPLANS = 4
    #: route_to(npcs=True, smooth=True): a hold whose line passes within ROUTE_WALKER_NEAR of a MOVING object's
    #: radius runs at most ROUTE_WALKER_HOLD_TICKS field ticks -- the frames sure to run no more
    #: (:meth:`_frames_within`: 6 at 60 fps, 3 at 30; six FRAMES were 360u of his run at 30 fps). The objects are
    #: read again only when a hold ends, and a walker covers a whole hold's length (up to ROUTE_HOLD_TICKS) before
    #: that read; near one, the reads come every ~180u of his walk (three run ticks), and a walker at run speed
    #: covers ROUTE_WALKER_NEAR in two such holds.
    #: A WALKING TRIGGER is not left to the cap: each point of a press must keep clear of it wherever it can have
    #: walked by the time he gets there, and the end until the next read (:meth:`_walker_clear`); a press that
    #: refuses (or cuts short, :meth:`_held_up`) is waited for, ROUTE_WALKER_WAIT_SECONDS at a time, standing still,
    #: within ROUTE_WALKER_BUDGET_SECONDS a call (:meth:`_outwait_walkers`) -- then the walk is ``boxed``. How many
    #: frames pass between two reads beyond the ones pressed is MEASURED, press by press (the send, its wait, the
    #: settle's polling -- ROUTE_WALKER_LAG_SECONDS until the first press says: the send's own 4-frame wait and the
    #: tail, twice over, at 60 fps). TIMES, all three, held as the frames sure to last them at the measured rate
    #: (:meth:`_frames_lasting`: the wait 8 frames at 60 fps, 16 at 120; the budget 480 and 960): a walker walks on the
    #: wall clock, a step a field tick -- and it is its speed A FRAME that the reads measure, so the frames it is given
    #: must be the frames that time holds. (As 8 / 480 / 12 FRAMES a 120 fps game waited half as long, and ``boxed``
    #: by walkers -- LIVE -- came at 4 s.)
    ROUTE_WALKER_HOLD_TICKS = 3
    ROUTE_WALKER_NEAR = 360.0
    ROUTE_WALKER_WAIT_SECONDS = 0.13
    ROUTE_WALKER_BUDGET_SECONDS = 8.0
    ROUTE_WALKER_LAG_SECONDS = 0.2
    #: route_to(npcs=True, smooth=True): a spot where no hold keeps the rules is boxed by the SPOT -- ``boxed`` at
    #: once -- unless it is the WALKERS among the objects that refuse the presses (:meth:`_boxers`, :meth:`_npc_walks`)
    #: whose going would free one. Then he stands still and reads again, ROUTE_WALKER_WAIT_SECONDS at a time within
    #: ROUTE_WALKER_BUDGET_SECONDS a call on the box's own tally (:meth:`_outwait_box`), and plans again from where a
    #: hold keeps the rules again -- ROUTE_BOX_REPLANS times a call, then the leg walks on from there; a box that
    #: outlasts the wait is ``boxed`` by walkers (``boxed_by``), the village and not the spot. A walker within its own
    #: step of contact with him (:meth:`_walker_step`), still ``moving``, that has not moved ROUTE_NPC_MOVED (summed
    #: read to read) in ROUTE_WALKER_HELD_SECONDS is HELD ON HIM (a time, :meth:`_frames_lasting`: 30 frames at 60 fps,
    #: 60 at 120 -- as 30 FRAMES, a walker pausing a quarter second at 120 fps read as held) -- the engine undoes every
    #: step a scripted walker takes
    #: into him (MoveToward.cs:187-189), so it walks on only once he moves -- and is stepped away from, not waited on
    #: (:meth:`_box_step`). Stock 350, session 2 run 2: two Dali
    #: children held on him for 21 s, seven crossings boxed. The zone's finish is no exception (:meth:`_walk_leg`): a
    #: walker in the way to a spot of the zone he could enter with the walkers gone (:meth:`_short_of_zone`) is waited
    #: on and stepped away from on the same tally -- session 3's stock run lost 350's door to 355 twice to a Dali child
    #: held on him there, each a REAL miss -- and nothing else at the zone's edge is: not a dead door, not a still body.
    ROUTE_WALKER_HELD_SECONDS = 0.5
    ROUTE_BOX_REPLANS = 4
    #: route_to(npcs=True): where a WALKING trigger will be is judged two ways. While he is moving, it may have come
    #: its speed a frame in ANY direction (a few frames: it cannot get far). While he STANDS (the end of a press, until
    #: the next read) it keeps to the LINE it was last seen walking along, either way -- a patrol turns back down its
    #: own beat -- give or take ROUTE_WALKER_TURN of its speed a frame (:meth:`_walker_path`); judged in any direction
    #: there, a walker anywhere in a room would forbid every press in it. And a plan first tries to keep off each
    #: walking trigger's line, ROUTE_WALKER_AHEAD_SECONDS of it either way (:meth:`_plan_npcs`) -- a time: the frames
    #: sure to last it (:meth:`_frames_lasting`: 120 at 60 fps, 240 at 120) times its measured speed a frame, the same
    #: stretch of its beat at any rate (as 120 FRAMES, a 120 fps game kept off one second of it, and a patrol came back
    #: onto a press's end judged off its beat).
    ROUTE_WALKER_TURN = 0.1
    ROUTE_WALKER_AHEAD_SECONDS = 2.0
    #: route_to(npcs=True): a stall is laid on a published body only when he is IN CONTACT with it -- his centre within
    #: HALF_STEP of its ``r`` (the engine holds it at ``r``) and the body within this many degrees of the press. One
    #: further off did not stop him, and one met off the line slides him round it (:meth:`_body_ahead`).
    ROUTE_CONTACT_ANGLE = 60.0
    #: route_to(npcs=True): samples read, ROUTE_NPC_READ_FRAMES apart, before a null ``objects`` (the engine could
    #: not say) is taken as "unknown" for the call.
    ROUTE_NPC_READS = 3
    ROUTE_NPC_READ_FRAMES = 4

    def key_prior(self, field: int) -> dict | None:
        """The PREDICTED button->world basis on stock ``field``, from its own script: ``{"v", "h"}``.

        :func:`ff9mapkit.content.movement.key_move_basis` of the Main_Init ``SetControlDirection``
        operand a keyboard press is rotated by (:meth:`_key_twist_operand`). A prediction, used only to
        choose which probes are safe to press -- ``calibrate_axes`` still measures. ``None`` when the
        field's script cannot be read (no install, a mod-only id): calibration then probes blind.
        """
        field = int(field)
        if field in self._priors:
            return self._priors[field]
        prior = None
        try:
            from ff9mapkit import eventscan
            from ff9mapkit.content import movement
            from ff9mapkit.extract import EventBundle
            if self._events is None:
                self._events = EventBundle(self.game_path)
            data = self._events.eb_for_id(field)
            if data:
                twist = eventscan.scan_control_twist(data)
                value = None if twist is None else twist[self._key_twist_operand()]
                if twist is None or value is not None:            # a computed operand predicts nothing
                    prior = movement.key_move_basis(value)
        except Exception as err:                                  # noqa: BLE001 -- no install: go blind
            self._log(f"  no movement prior for field {field}: {type(err).__name__}: {err}")
        self._priors[field] = prior
        return prior

    def _key_twist_operand(self) -> int:
        """Which SetControlDirection operand a harness press is rotated by: 1 (``twist.y``), or 0 when
        ``Memoria.ini [AnalogControl]`` has ``Enabled`` on and ``UseAbsoluteOrientation`` 1 or 2.

        The agent answers ``CheckPersistentDirectionInput`` as a KEYBOARD (s83), so the press is not
        stick movement, and ``FieldMapActorController.cs:715-718`` reads ``twist.x`` for keys only under
        ``UseAbsoluteOrientationKeys`` (``Control.cs:14``: setting 1 or 2). This install ships 3."""
        try:
            text = (self.game_path / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
        except OSError:
            return 1
        m = re.search(r"^\s*\[AnalogControl\]\s*$(.*?)(?=^\s*\[|\Z)", text, re.M | re.S)
        body = m.group(1) if m else ""

        def val(key: str, default: int) -> int:
            k = re.search(rf"^\s*{key}\s*=\s*(-?\d+)", body, re.M)
            return int(k.group(1)) if k else default

        return 0 if val("Enabled", 1) != 0 and val("UseAbsoluteOrientation", 3) in (1, 2) else 1

    def _stock_walkmesh(self, field: int):
        """The install's walkmesh for stock ``field`` -- :func:`ff9mapkit.extract.stock_walkmesh`."""
        try:
            from ff9mapkit import extract
            return extract.stock_walkmesh(field, game=self.game_path)
        except Exception as err:                                  # noqa: BLE001 -- say which, and how
            raise HarnessError(
                f"routing on field {field} needs its walkmesh, and the install's could not be read "
                f"({type(err).__name__}: {err}). A fork or a custom field has its own: pass "
                f"walkmesh=BgiWalkmesh.from_file(<its .bgi>)."
            ) from err

    def _await_landing(self, origin: int, timeout: float, record: dict | None = None) -> int | None:
        """After control went away on ``origin``: the field it led to, or None if control came back
        there instead (a trigger that was not a gateway). Raises -- like :meth:`cross` -- only for a
        destination that loaded and never became playable. ``record`` is expect_field_change's (its
        ``changed_to``)."""
        try:
            self.wait_for(lambda s: (s.field_id != origin and s.field_id > 0)
                          or (s.field_id == origin and s.control),
                          timeout=timeout, what=f"the field to change from {origin}, or control to return")
        except HarnessError:
            pass
        now = self.state.field_id
        if now == origin or now <= 0:
            return None
        return self.expect_field_change(timeout=timeout, was=origin, record=record)

    def _landed(self, origin: int, timeout: float, record: dict, handoff: bool) -> int | None:
        """A routed walk's landing after control went on ``origin``: :meth:`_await_landing`'s wait -- or, ``handoff``
        (route_to's), none at all: the field as it stands, the new id if it has already changed (``changed_to`` too),
        else None, and the record marked ``handoff``. The caller sits through the rest itself."""
        if not handoff:
            return self._await_landing(origin, timeout, record)
        record["handoff"] = True
        now = self.state.field_id
        if now == origin or now <= 0:
            return None
        record["changed_to"] = now
        return now

    def _route_chunks(self, legs, hazards, blockers=()) -> list:
        """Split each routed leg into walk_to targets ``(x, z, tolerance)`` short enough that the L of
        one-axis steering cannot reach a hazard: a chunk's corner strays at most half its length off
        the line, so a leg ``c`` clear of every hazard is cut into chunks of ``2 * (c -
        PROBE_HAZARD_PAD)``. A leg that starts INSIDE a hazard (walking out of the arrival door) counts
        as clearance 0 -- the shortest chunks, so the L strays least from a line planned to cross that
        boundary once. The tolerance is at most half a chunk -- a chunk end already within tolerance is
        'arrived' without a press, and two skipped chunks make one twice as long.

        ``blockers`` (unseen bodies, :meth:`route_to` ``unstick``) count too, OBSTACLE_R_W round. A
        detour is planned TANGENT to a body, and an L that cuts into it is pushed round it by the
        engine: a sideways slide that ends the walk as a stall (walk_to ``slides``), or a stall that
        places a needless blocker. Shorter chunks there cost bursts, not a wrong answer."""
        out = []
        for a, b in zip(legs, legs[1:]):
            chunk = self._leg_chunk(a, b, hazards, blockers)
            length = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
            n = max(1, int(-(-length // chunk)))
            tol = max(self.HALF_STEP + 1.0, min(self.ROUTE_WAYPOINT_TOLERANCE, length / n / 2.0))
            out.extend((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n, tol)
                       for k in range(1, n + 1))
        return out

    def _leg_chunk(self, a, b, hazards, blockers=()) -> float:
        """:meth:`_route_chunks`' chunk length for the leg a->b: ``2 * (c - PROBE_HAZARD_PAD)`` for the leg's
        clearance ``c`` from every hazard and every blocker (OBSTACLE_R_W round, or ``(x, z, r)``: a published
        object's own radius, route_to(npcs=True); a leg starting inside a hazard counts 0), within
        [ROUTE_CHUNK_MIN, ROUTE_CHUNK_MAX]. Half of it is how far a walk may stray from the leg: an L's corner
        under walk_to, a hold's end under route_to(smooth=True) (:meth:`_route_legs`)."""
        from ff9mapkit.content import pathfind
        from ff9mapkit.scene import routes
        gaps = [max(0.0, pathfind.seg_poly_gap(a, b, p)) for p in hazards]
        gaps += [max(0.0, routes.seg_dist_xz(p[0], p[1], a, b) - (p[2] if len(p) > 2 else pathfind.OBSTACLE_R_W))
                 for p in blockers]
        clear = min(gaps) if gaps else self.ROUTE_CHUNK_MAX
        return min(self.ROUTE_CHUNK_MAX, max(self.ROUTE_CHUNK_MIN, 2.0 * (clear - self.PROBE_HAZARD_PAD)))

    def _heading_spread(self, basis: dict, prior: dict | None) -> float:
        """How far off its calibrated direction a press on ``basis`` may truly head, in radians -- what a smooth
        hold's line is judged with (:meth:`_probe_is_clear` ``spread``). ROUTE_HEADING_FLOOR, plus the larger
        angle between a calibrated axis and its ``prior`` (:meth:`key_prior`): calibration accepts a one-sided
        measurement within PRIOR_AGREE of the prior (~16 degrees), and the in-game run took 352's up 6.3
        degrees off a truth its prior had exactly, so where the two disagree either may be the truth, and the
        hold is planned for both. With no prior, the most calibration ever lets a measured axis disagree with
        one: acos(PRIOR_AGREE)."""
        import math
        if prior is None:
            worst = math.acos(self.PRIOR_AGREE)
        else:
            worst = 0.0
            for k in ("v", "h"):
                b, p = basis[k], prior[k]
                cos = (b[0] * p[0] + b[1] * p[1]) / ((b[0] ** 2 + b[1] ** 2) * (p[0] ** 2 + p[1] ** 2)) ** 0.5
                worst = max(worst, math.acos(max(-1.0, min(1.0, cos))))
        return math.radians(self.ROUTE_HEADING_FLOOR) + worst

    def _route_legs(self, legs, hazards, blockers, *, spread: float, zone=None, floor=None, watch=None) -> list:
        """route_to(smooth=True)'s targets: every planned waypoint WHOLE, as ``(x, z, tolerance, leg)`` -- no
        chunks, ROUTE_WAYPOINT_TOLERANCE each (route_to puts the caller's on the last). ``leg`` is what the
        leg's holds are planned in (:meth:`_plan_hold`): ``from`` and ``to``, the ``hazards`` and ``blockers``
        its drift is judged against, the heading ``spread`` (:meth:`_heading_spread`), and ``pressed``, the
        ``(buttons, world direction)`` of its last hold, which is where :meth:`_blocker_ahead` puts a body he
        stopped against and :meth:`_push_through` insists -- and ``turned``, that hold again with the MovePC calls it
        is known to have spent turning him toward it (:meth:`_held_yaw`: where a facing step starts from), None once a
        press made along another line follows it (a push insists along the same one: it only turns him further toward
        it).
        ``watch`` (route_to(npcs=True)) is the call's view of
        the published objects: its ``discs`` bound every hold like the hazards do (:meth:`_leg_discs`), and it is
        read again after every hold (:meth:`_walk_leg`).

        THE LAST LEG AIMS AT THE GOAL ITSELF (``aim``: within HALF_STEP, the closest a press can steer),
        and is still judged by the caller's tolerance. The goal route_cross walks to is a point INSIDE a gateway
        zone (pathfind.region_goal), often only a few units in -- stock 350's 353 door: 2u -- so a walk that
        stops anywhere within 45u of it can stand him outside the zone with nothing fired. Given that ``zone``
        (route_to's), the last leg carries it, and the ``floor`` he walks, and FINISHES ON IT (:meth:`_walk_leg`)."""
        out = []
        for a, b in zip(legs, legs[1:]):
            out.append((float(b[0]), float(b[1]), self.ROUTE_WAYPOINT_TOLERANCE,
                        {"from": (float(a[0]), float(a[1])), "to": (float(b[0]), float(b[1])),
                         "hazards": hazards, "blockers": tuple(blockers), "spread": float(spread),
                         "pressed": None, "turned": None, "aim": None, "zone": None, "floor": None, "watch": watch}))
        if out:
            out[-1][3]["aim"] = self.HALF_STEP + 1.0
            out[-1][3]["zone"], out[-1][3]["floor"] = zone, floor
        return out

    def _zone_spots(self, here, zone, floor):
        """Every point within ROUTE_FOOTHOLD_REACH of ``here`` (rings of 4u, 36 bearings), nearest first, that lies in
        ``zone``, on ``floor`` and COLLISION_RADIUS_W off its walls -- where his CENTRE can stand; the engine keeps it
        that far off a wall, so a zone whose inner edge runs near that line is standable only in a sliver or a corner
        (stock 350's door to 353: only a 34u wedge by its east corner -- the grid region_goal samples misses it, and its
        goal stands 77u off the wall, where he cannot). A generator: the caller stops at the first it can use."""
        import math
        from ff9mapkit.content import pathfind
        from ff9mapkit.scene import cam
        for k in range(1, int(self.ROUTE_FOOTHOLD_REACH // 4) + 1):
            for j in range(36):
                a = math.radians(10 * j)
                q = (here[0] + 4 * k * math.cos(a), here[1] + 4 * k * math.sin(a))
                if pathfind.poly_gap(q[0], q[1], zone) >= 0:
                    continue
                if not self._can_stand(floor, q[0], q[1], cam.COLLISION_RADIUS_W):
                    continue
                yield q

    @staticmethod
    def _wall_gap(floor, x: float, z: float, memo: dict | None = None) -> float | None:
        """How far his centre at (``x``, ``z``) -- rounded to the integer point the floor is asked about -- stands off
        the walls of ``floor`` (a pathfind.PlayerWalkmesh): None off the open floor, ``inf`` on a floor with no wall
        edge at all (every edge a seam to another floor: nothing to keep off), else the distance to the nearest.
        ``memo`` keeps the answers by point, across one caller's many asks."""
        import math
        key = (int(round(x)), int(round(z)))
        if memo is not None and key in memo:
            return memo[key]
        gap = None
        if floor.point_on_walkmesh(*key) is not None:
            wall = floor.distance_to_boundary(*key)
            gap = math.inf if wall is None else wall
        if memo is not None:
            memo[key] = gap
        return gap

    @classmethod
    def _can_stand(cls, floor, x: float, z: float, least: float, memo: dict | None = None) -> bool:
        """Can his CENTRE stand at (``x``, ``z``) on ``floor``: on it, and at least ``least`` off its walls
        (:meth:`_wall_gap`) -- COLLISION_RADIUS_W where the engine keeps it (the radius push-out, ServiceChar), or
        less where he already stands nearer. The one test every standability judgement here makes."""
        gap = cls._wall_gap(floor, x, z, memo)
        return gap is not None and gap >= least

    @staticmethod
    def _covers(discs, q) -> list:
        """The ``discs`` standing over point ``q``: within a disc's ``R`` and ``pad`` -- where a hold keeps off it."""
        import math
        return [d for d in discs if math.hypot(q[0] - d["x"], q[1] - d["z"]) < d["R"] + d["pad"]]

    def _zone_foothold(self, here, zone, floor, discs=(), *, strict: bool = False):
        """Where the last leg presses to get INTO ``zone`` from ``here``, just outside it: the nearest point of
        :meth:`_zone_spots` -- in the zone, where his centre can stand, ROUTE_FOOTHOLD_REACH round him at most. None
        when no such point is that near.

        A point one of ``discs`` stands over -- within its ``R`` and ``pad``, where the leg's holds may not go
        (:meth:`_leg_discs`, route_to(npcs=True)) -- is passed over for the next one that is free: a Dali child standing
        on one end of a door's standable strip leaves the other end (rung-3 session 3, stock 350's door to 355). With
        every such point that near covered, the nearest covered one: the presses toward it are refused by what covers
        it, and that is a box by those objects, waited on while they walk (:meth:`_outwait_box`, :meth:`_boxers`) --
        or, ``strict``, None: no spot of the zone that near is free of them (:meth:`_short_of_zone`)."""
        covered = None
        for q in self._zone_spots(here, zone, floor):
            if self._covers(discs, q):
                covered = covered or q
                continue
            return q
        return None if strict else covered

    def _finish_target(self, here, zone, floor, discs=()):
        """Where the zone's finish (:meth:`_walk_leg`) presses from ``here``: the nearest spot in ``zone`` his centre
        can stand on ``floor`` that none of ``discs`` covers (:meth:`_zone_foothold`), or, with none that near (or no
        ``floor``), a point HALF_STEP past the zone's nearest edge (:func:`_into_zone`) -- pressing on into a wall is
        harmless, the engine stops his centre on its clearance line."""
        return ((floor is not None and self._zone_foothold(here, zone, floor, discs))
                or _into_zone(here, zone, self.HALF_STEP))

    def _plan_hold(self, basis: dict, here, target, leg: dict, exclude=(), *, sweep: bool = True,
                   rate: Rate | None = None, least: int = 1):
        """The next hold of a smooth routed leg (:meth:`_walk_leg`) toward ``target`` -- the leg's end, or a
        point just inside its zone: ``(buttons, (ux, uz), frames, slow)``, or None when no hold from ``here``
        keeps both rules below. Pads whose buttons are in ``exclude`` are not pressed (the zone finish: a pad
        that moved him nothing from here).

        AT ``rate`` (default :meth:`rate`; the walk that presses it passes a MEASURED one, ``require=True``): the
        length is SIZED at the rate's average speed (Rate.speed -- at 31 fps a run frame carries him ~57u, and a
        hold sized at 30u a frame ran twice past its aim and the next hold came back: a quarter of the in-game
        holds at 31 fps reversed the one before), and every rule below is judged at the most its frames can carry
        him (Rate.reach -- sized there too, the far half of every 31 fps press went unjudged).

        THE DIRECTION is one of the two pad directions (:func:`_eight_way`) either side of the bearing to
        ``target``: the one that gains the most ground toward it within the rules -- which is how a leg between
        two of the eight is walked, the next hold re-aiming from where this one ends. Only when neither can hold
        even the least press (``least`` frames walked: one, or -- after a press that may have run no tick moved
        him nothing -- the frames sure of one, :meth:`_least_frames`), any other that still gains ground (under 90
        degrees off): beside a door, a leg
        running along it has its own pad refused (the heading error could close on the door) and the next one
        closes on it outright, so the first step is AWAY from it. A run if any run fits, a walk (Cancel held)
        only when none does or ``target`` is nearer than WALK_UNDER (walk_to's rule: a run TICK overshoots any
        tighter tolerance -- a distance, a run tick and a half, whatever the frames). THE LENGTH is the longest -- up to what ``target`` needs (a run stops a frame
        short: its tail carries it) and ROUTE_HOLD_TICKS -- that keeps
          * THE ZONES: the straight line the hold covers -- Rate.reach of its frames: the most field ticks they
            can hold and the movement tail --
            passes :meth:`_probe_is_clear` of every ``leg["hazards"]`` region -- the calibration probe's own
            rule: a region he stands in may be left and never re-entered, one he stands beside never
            approached, any other kept PROBE_HAZARD_PAD clear -- and not that line alone but every line within
            ``leg["spread"]`` of it: the pressed direction is a calibrated MEASUREMENT (:meth:`_heading_spread`);
          * THE LEG: the line's end stays within the DRIFT of the leg still to walk -- from the point of the
            planned leg nearest ``here`` to ``leg["to"]`` -- less what the heading error can add at that length
            (``reach * tan(spread)``), or no further off that leg than he already is. The drift is the chunked
            walk's budget (:meth:`_leg_chunk`): half of that remaining leg's clearance less PROBE_HAZARD_PAD,
            re-judged every hold, so the pad's heading error -- up to 22.5 degrees -- is taken back at the next
            hold instead of carried down the leg, and a hold that meets a wall -- pushed back onto the floor,
            toward a leg that lies on it (on a floor convex where he walks) -- still slides PROBE_HAZARD_PAD clear
            of every region. Beside a door (or a blocker) the remaining leg's clearance is under ROUTE_CHUNK_MIN
            / 2 + PROBE_HAZARD_PAD and the drift is clamped up to ROUTE_CHUNK_MIN / 2: there it keeps nothing, the
            zone rule does, and so it never refuses the SMALLEST press there is (``least`` frames walked, at most
            their Rate.reach off the line). Without that, a leg leaving a door at an angle to both
            pads had no first step at all (stock 356, 6u beside its 350 door, sent to 353: the one zone-clear
            pad strayed 24.04u against a drift of 24). Judged from the REMAINING leg, the clamp binds only while
            he is still beside the door, not down the whole of a long leg.
          * THE OBJECTS (route_to(npcs=True)): the same fan keeps clear of every published object the plan kept,
            where it stands NOW (:meth:`_leg_discs`) -- a body ROUTE_BODY_PAD off its ``r``, a trigger
            PROBE_HAZARD_PAD off its radius, one he stands nearer than that never approached closer
            (:meth:`_probe_is_clear` ``discs``); the drift counts them like blockers, at their own radii. And a
            line that passes within ROUTE_WALKER_NEAR of a MOVING one's radius is held at most
            ROUTE_WALKER_HOLD_TICKS: they are read again only when the hold ends (:meth:`_walk_leg`). A MOVING TRIGGER
            is judged
            where it could have walked by the time he gets to each point of the line, and where he stands until the
            next read, not where it was read (:meth:`_walker_clear`) -- a patrol that walks into him fires its script
            as surely as he walks into it (``sweep`` False judges it where it was read: whether the walker alone is
            what refuses the press).
        Each rule that holds for a length holds for every shorter one, so the longest is found by bisection -- all
        but the walker's: a press that crosses a beat whole clears where a shorter one stopping on it does not. So with
        a walker the lengths above the bisection's are tried too, longest first; every length taken was checked."""
        import math
        from ff9mapkit.scene import routes
        rate = self.rate() if rate is None else rate
        b = leg["to"]
        dx, dz = target[0] - here[0], target[1] - here[1]
        dist = (dx * dx + dz * dz) ** 0.5
        if dist < 1.0:
            return None
        p = _nearest_on_seg(here, leg["from"], b)
        discs = self._leg_discs(leg)
        walkers, swept, still = self._press_discs(leg, sweep)
        blockers = list(leg["blockers"]) + [(d["x"], d["z"], d["R"]) for d in discs]
        drift = self._leg_chunk(p, b, leg["hazards"], blockers) / 2.0
        off = math.hypot(here[0] - p[0], here[1] - p[1]) + 0.5
        spread = leg["spread"]
        least = max(1, int(least))
        cap = max(least, self._frames_within(self.ROUTE_HOLD_TICKS, rate))
        order = sorted(_eight_way(basis), key=lambda p: -(p[1][0] * dx + p[1][1] * dz))
        for pads in (order[:2], order[2:]):
            for slow in ((True,) if dist < self.WALK_UNDER else (False, True)):
                gait = "walk" if slow else "run"
                speed = rate.speed(gait)
                best = None
                for buttons, u in pads:
                    along = u[0] * dx + u[1] * dz              # where the line pressed passes nearest the target
                    if along <= 0 or buttons in exclude:
                        continue

                    def fits(n, u=u, gait=gait, slow=slow):
                        reach = rate.reach(n, gait)
                        end = (here[0] + u[0] * reach, here[1] + u[1] * reach)
                        near = (slow and n == least) or (routes.seg_dist_xz(end[0], end[1], p, b)
                                                         <= max(drift - reach * math.tan(spread), off))
                        return near and self._press_clear(here, u, n, gait, leg, walkers, swept, still, rate)

                    top = min(cap, max(least, rate.frames_for(along, gait) - (0 if slow else 1)))
                    lo, hi = least - 1, top                  # least - 1: no press fits
                    while lo < hi:
                        mid = (lo + hi + 1) // 2
                        lo, hi = (mid, hi) if fits(mid) else (lo, mid - 1)
                    if swept:                         # across a walker's beat whole, where stopping on it may not:
                        lo = next((n for n in range(top, lo, -1) if fits(n)), lo)      # the longest that clears
                    lo = lo if lo >= least else 0
                    gain = lo * speed * along / dist
                    if lo and (best is None or gain > best[0]):
                        best = (gain, buttons, u, lo, slow)
                if best is not None:
                    return best[1:]
        return None

    def _press_discs(self, leg: dict, sweep: bool = True) -> tuple:
        """The published objects a smooth press is judged against (:meth:`_press_clear`), from the leg's discs where
        they stand now (:meth:`_leg_discs`): ``(walkers, swept, still)`` -- ``swept`` the WALKING triggers, judged where
        they can walk (``sweep`` False: none, every one judged where it was read -- whether the walker alone refuses a
        press), ``walkers`` every other moving object, ``still`` every disc that is not swept."""
        discs = self._leg_discs(leg)
        walkers = [d for d in discs if d["moving"]]
        swept = [d for d in walkers if d["kind"] == "trigger"] if sweep else []
        still = [d for d in discs if all(d is not s for s in swept)]
        walkers = [d for d in walkers if all(d is not s for s in swept)]    # a swept trigger is judged exactly
        return walkers, swept, still

    def _press_clear(self, here, u, n: int, gait: str, leg: dict, walkers, swept, still,
                     rate: Rate | None = None) -> bool:
        """Does a press from ``here`` along ``u`` -- ``n`` frames of ``gait`` (``"run"`` / ``"walk"``) at ``rate``
        (default :meth:`rate`), as far as those frames can carry him, its movement tail included (Rate.reach: the
        UPPER bound -- a rule is broken by where he CAN go) -- keep the rules every smooth press keeps, whatever it is
        pressed for (:meth:`_plan_hold`'s holds, :meth:`_face_the_door`'s turn)? Over the leg's heading ``spread``,
        the line: no ``leg["hazards"]`` region entered or approached, and every ``still`` object kept clear
        (:meth:`_probe_is_clear`); every WALKING trigger of ``swept`` kept clear wherever it can walk by the next read
        (:meth:`_walker_clear`, his pace the rate's average speed) and the press not ending on its beat
        (:meth:`_off_beat`); and a press held past ROUTE_WALKER_HOLD_TICKS only where no other moving object of
        ``walkers`` is within ROUTE_WALKER_NEAR of its line -- the objects are read again only when it ends
        (:meth:`_press_discs` sorts them)."""
        from ff9mapkit.scene import routes
        rate = self.rate() if rate is None else rate
        spread = leg["spread"]
        reach = rate.reach(n, gait)
        end = (here[0] + u[0] * reach, here[1] + u[1] * reach)
        if n > self._frames_within(self.ROUTE_WALKER_HOLD_TICKS, rate) and any(
                routes.seg_dist_xz(d["x"], d["z"], here, end) < d["R"] + self.ROUTE_WALKER_NEAR for d in walkers):
            return False
        until = n + self._walker_lag(leg.get("watch"))
        ends = [(here[0] + e[0] * reach, here[1] + e[1] * reach)
                for e in (_turn(u, spread * k / 2.0) for k in (-2, -1, 0, 1, 2))]
        if not all(self._walker_clear(here, u, reach, spread, d, rate.speed(gait), until)
                   and self._off_beat(here, ends, d) for d in swept):
            return False
        return self._probe_is_clear(here, u, reach, leg["hazards"], spread, discs=still)

    def _held_up(self, basis: dict, target, leg: dict, exclude=(), hold=False, rate: Rate | None = None) -> bool:
        """route_to(npcs=True, smooth=True): is the next hold toward ``target``, from where he stands now, refused or
        CUT SHORT by a WALKING trigger's reach alone (:meth:`_plan_hold` ``sweep``)? Short: under
        ROUTE_WALKER_HOLD_TICKS of run (three run ticks, RUN_TICK each: a distance), or under what the hold would be
        without the walkers if that is less -- the two holds compared by the ground they cover ON AVERAGE at ``rate``
        (default :meth:`rate`; Rate.speed x frames): a question of how much of the press the walkers took, which a
        wait answers, not a rule a press keeps (the hold itself was planned at Rate.reach). A walk that creeps along
        a patrol's beat a frame at a time stalls on its own overshoots, and the stall ladder then reads the walker's
        refusals as bodies -- waiting for the walker to go by is what gets him across. ``hold`` is the hold already
        planned from here, if the caller has it."""
        if not any(d["moving"] and d["kind"] == "trigger" for d in self._leg_discs(leg)):
            return False
        rate = self.rate() if rate is None else rate
        here = self._standing()
        if hold is False:
            hold = self._plan_hold(basis, here, target, leg, exclude, rate=rate)
        free = self._plan_hold(basis, here, target, leg, exclude, sweep=False, rate=rate)
        if free is None:
            return False                                  # not the walkers: the caller's own verdict stands

        def ground(h) -> float:
            return 0.0 if h is None else h[2] * rate.speed("walk" if h[3] else "run")
        return ground(hold) < min(ground(free), self.ROUTE_WALKER_HOLD_TICKS * self.RUN_TICK) - 0.5

    def _walkers_let_press(self, here, hold, leg: dict, rate: Rate | None = None) -> bool:
        """route_to(npcs=True, smooth=True): does ``hold``, planned from ``here``, still keep clear of every WALKING
        trigger by a read taken NOW -- the one it was planned on is as old as the planning, and a walker walks
        meanwhile? The same rules as the plan (:meth:`_walker_clear`, :meth:`_off_beat`) at the same ``rate``
        (default :meth:`rate`) -- the hold's reach Rate.reach, his pace its average -- with the tail's frames
        (:meth:`_tail_frames`) of head start for the send itself. True with no walker to ask about, or no fresh list
        to judge by."""
        watch = leg["watch"]
        if hold is None or not any(d["moving"] and d["kind"] == "trigger" for d in self._leg_discs(leg)):
            return True
        st = self.state
        if self._npc_view(watch, st) is None:
            return True
        rate = self.rate() if rate is None else rate
        _buttons, u, n, slow = hold
        gait = "walk" if slow else "run"
        pace = rate.speed(gait)
        reach = rate.reach(n, gait)
        spread = leg["spread"]
        ends = [(here[0] + e[0] * reach, here[1] + e[1] * reach)
                for e in (_turn(u, spread * k / 2.0) for k in (-2, -1, 0, 1, 2))]
        walking = [d for d in watch["discs"] if d["kind"] == "trigger" and d["moving"]]
        return all(self._walker_clear(here, u, reach, spread, d, pace, n + self._walker_lag(watch),
                                      lead=self._tail_frames(rate)) and self._off_beat(here, ends, d) for d in walking)

    def _walk_leg(self, x: float, z: float, tolerance: float, leg: dict, slides: bool) -> str:
        """route_to(smooth=True)'s walk to one planned waypoint (x, z), in place of walk_to: hold after hold from
        :meth:`_plan_hold`, each ONE continuous press -- two directions at once where the leg runs diagonal on
        the calibrated basis -- and a fresh aim only when one ends, instead of one-axis bursts with a settle
        between each. walk_to's contract otherwise, as route_to calls it (strict=False, halt_on_transition=
        True): settled at both ends of every hold; nothing pressed once control is gone; a stall is two holds
        in a row that moved nothing or overshot; a hold that covered real ground but not along what it
        pressed is a slide round someone under ``slides`` (the walk ends, a stall) and a wrong basis otherwise
        (discarded, raises). Holds go on until he is within ``leg["aim"]`` when it is tighter (the last leg
        without a zone, see :meth:`_route_legs` -- an overshoot past it then counts as a stall, so the aim costs
        a hold or two, never an oscillation).

        EVERY HOLD IS PLANNED AT A MEASURED RATE (:meth:`rate` ``require=True``, fetched afresh for each: a launch's
        regime can switch): sized at its average speed, its rules judged at the most it can reach -- so a hold at
        31 fps neither runs twice past its aim nor carries him past the line its zones were checked to. A walk with
        no measured rate raises rather than press on the calibrated 60 fps. And every hold is checked, once
        settled, against what that rate says it can move him (:meth:`_check_movement`). A press that may have run NO
        field tick -- fewer frames than one is sure to hold (Rate.ticks_sure) -- and moved him nothing proves nothing:
        no stall, no pad of the finish marked stuck; the next press from there is the fewest frames sure of a tick
        (:meth:`_least_frames`; a press that may run none only where no such press keeps the rules). At 120 fps a
        one-frame finish press runs no tick three times in four, and read as a wall its pad was given up and the
        finish could end outside the zone -- the door's strike, on a press that never ran.

        THE LAST LEG FINISHES ON ITS ``zone`` when it has one: standing in it is arrival wherever that is, and
        once within ``tolerance`` of the goal but still outside, the holds press INTO it -- walked, the zone rule
        still kept -- toward the nearest spot in it where his centre can stand and no object the holds keep clear
        of stands over (:meth:`_finish_target`), or, with none that near (or no ``floor``), a point HALF_STEP
        past the zone's nearest edge (:func:`_into_zone`):
        pressing on into a wall is harmless, the engine stops his centre on its clearance line -- but a pad that
        moved him nothing is not pressed again from that spot: the other side of the bearing slides along the
        wall instead (350's 353 wedge, reached diagonally into the wall 10u short of it). A press that moves
        him no nearer the zone is a stall; an overshoot of the goal that leaves him within ``tolerance`` is not
        -- the finish takes over from there. A goal a few units deep lies by that line (stock 350's door to
        353: 2u in, and 77u off the wall -- short of the line), so "within HALF_STEP of it" can stand him
        outside; and the smallest press moves ~30u, so a walk aimed that close bounces round it and stalls on
        the overshoots before it ever gets there (350's door to 450 in the wall-slide simulator). The zone,
        not the goal point, is the target -- and "arrived" means standing IN it, enforced at the return.

        THE ZONE'S EDGE DOES NOT END THE WAIT FOR WALKERS (rung-3 session 3, stock 350's door to 355, both attempts of
        the stock run: a Dali child -- a talk-only walker, a non-solid body of r 152 -- walked into him on the door
        step and stayed there, held: the engine undoes every step a scripted walker takes into him, MoveToward.cs:
        187-189. Its body stood between him and the one patch of the zone he can stand on; the finish found no press,
        stopped within ``tolerance`` and called that arrival -- a REAL miss, and two of them made the door
        unreachable). Under a ``watch`` the finish meets walkers as the rest of the leg does -- but only walkers that
        are the CAUSE. Every way it can end short of the zone -- no hold keeps the rules, two presses in a row moved
        him nothing or no nearer the zone, one slid him round someone (``slides``), the holds spent -- goes through
        ONE judgement first (:meth:`_outwait_hold`, by :meth:`_short_of_zone`): could he get into the zone with
        every walker gone, and does a walker stand in the way to that spot? Only then does he wait on them (where no
        hold keeps the rules, first as a box by them: :meth:`_outwait_box`), and step out of the way of any held on
        him (:meth:`_box_step`), within the call's ROUTE_WALKER_BUDGET_SECONDS, until none stands in that way: their
        letting go ends the leg "unboxed" (route_to plans again from where he stands, ROUTE_BOX_REPLANS times a call;
        after that the finish presses on from there), their outlasting the wait ends it "boxed" (``boxed_by`` walkers).
        What no walker's going would change -- the spot's geometry, a body that does not walk -- ends the finish
        short of the zone at once, "outside", however many walkers pace nearby: nothing is pushed there, nothing is
        waited on. The judgement the finish ended on is the one route_to records (``watch["held"]``: ``held_by``,
        ``pinned``) -- never judged again afterwards from elsewhere.

        UNDER A ``leg["watch"]`` (route_to(npcs=True)) the objects are read again after every hold
        (:meth:`_npc_moved`): the next hold is bounded by where they stand now, and one that moved onto the
        path still to walk ends the leg as "moved" -- route_to plans again from here. Where the only thing that
        refuses every hold is a WALKING trigger's reach (:meth:`_plan_hold` ``sweep``), he stands still until it
        has gone by (:meth:`_outwait_walkers`) instead of pressing toward it. And where no hold keeps the rules only
        because of WALKING objects among the ones that refuse them (:meth:`_boxers`: their going would free a press),
        the spot is not boxed yet: he waits for them to walk off -- stepping out of the way of any held on him -- and
        the leg ends "unboxed" once a hold keeps the rules again, so route_to plans again from there
        (:meth:`_outwait_box`; ROUTE_BOX_REPLANS times a call, then the leg walks on).

        Returns "arrived" (within ``tolerance`` of a leg with no ``zone``; with one, standing IN it -- nothing
        else), "outside" (the zone's finish ended within ``tolerance`` of the goal but outside the zone, with nothing
        further it may press and no walker in the way in: route_to ends the walk there -- not a stall, which a wait, a
        push or a blocker could change), "boxed" when no hold from
        where he stands keeps :meth:`_plan_hold`'s rules and he is not within ``tolerance`` -- nothing may be
        pressed from here, which is not a stall: a wait, a push or a blocker cannot change it -- and no walker's
        going would change that, or the call's wait for walkers is spent (at the zone's finish too: walkers that
        box him in or hold him out of the zone past that wait); "unboxed" (above), "moved" (above), or
        "short" (anything else: a stall, a slide, the holds spent, control gone)."""
        import math
        from ff9mapkit.content import doorface, pathfind
        field = self.state.field_id
        basis = self._axes[field]
        aim = min(tolerance, leg.get("aim") or tolerance)
        zone = leg.get("zone")
        watch = leg.get("watch")
        stalls = 0
        stuck: set = set()                        # the zone finish: pads that moved him nothing from here
        least = 1                                 # the least press: sure of a tick after one that may have run none
        if watch is not None:
            watch["held"] = None                  # what the finish found short of the zone: this leg's, never another's
        # measured BEFORE the position every hold is planned from is read: a wait for the rate lets frames -- and the
        # room's walkers -- go by, and a plan made after it from a read taken before it is a plan of a room that was
        self.rate(require=True)
        st = self.settle()
        for _ in range(self.ROUTE_HOLDS):
            if watch is not None:
                watch["held"] = None              # ... and this hold's, if any
            if st.field_id != field or st.player_x is None or not st.control:
                return "short"
            here = (st.player_x, st.player_z)
            if zone is not None and pathfind.poly_gap(here[0], here[1], zone) < 0:
                return "arrived"                  # in the region he was sent to, control held: a gated gateway
            if zone is None and math.hypot(x - here[0], z - here[1]) <= aim:
                return "arrived"
            within = math.hypot(x - here[0], z - here[1]) <= tolerance
            finish = zone is not None and within
            target = (x, z)
            if finish:
                target = self._finish_target(here, zone, leg.get("floor"), self._leg_discs(leg))
            exclude = stuck if finish else ()
            rate = self.rate(require=True)          # measured (above), and afresh: a launch's regime can switch
            hold = self._plan_hold(basis, here, target, leg, exclude, rate=rate, least=least)
            if hold is None and least > 1:          # none that long keeps the rules: a press that may run no tick
                hold = self._plan_hold(basis, here, target, leg, exclude, rate=rate)
            if watch is not None and self._held_up(basis, target, leg, exclude, hold, rate):
                # a WALKING trigger's reach is what refuses or cuts short the press from here: stand still until it
                # has gone by, rather than creep up to its beat -- or, where standing is not safe either, step out of
                # its way first
                got = self._outwait_walkers(watch, field,
                                            lambda: not self._held_up(basis, target, leg, exclude),
                                            lambda: self._walker_escape(basis, leg))
                if got != "clear":
                    return got
                st = self.state
                continue
            if hold is None:
                if watch is not None and not within:
                    # boxed by WALKING objects is not boxed: they walk off (or, held on him, walk on once he steps out
                    # of their way) -- wait for that, then plan again from where the presses are free
                    got = self._outwait_box(basis, target, leg, exclude, field)
                    if got == "clear":
                        if self._box_released(watch):
                            return "unboxed"
                        st = self.state
                        continue
                    if got != "boxed":
                        return got
                if within:
                    if finish and watch is not None:
                        # at the zone's edge the box is judged per cause: waited on only where walkers are what keep
                        # him out of a zone he could enter with them gone (what route_to then records, either way)
                        got = self._outwait_hold(basis, leg, field, box=(target, exclude))
                        if got == "clear":
                            if self._box_released(watch):
                                return "unboxed"
                            stalls, stuck, st = 0, set(), self.state
                            continue
                        if got is not None:
                            return got
                    break                         # nowhere further to press; the tolerance (the zone, if any) decides
                self._log(f"  route_to: no hold from ({here[0]:.0f}, {here[1]:.0f}) toward ({x:.0f}, {z:.0f}) "
                          f"keeps clear of the avoided regions and near the leg; nothing may be pressed from here")
                return "boxed"
            if watch is not None and not self._walkers_let_press(here, hold, leg, rate):
                # planning took frames a walker spent walking: judged again on a read taken now, the hold no longer
                # keeps clear -- wait for it (once at the least) as for any walker in the way
                got = self._outwait_walkers(watch, field,
                                            lambda: not self._held_up(basis, target, leg, exclude),
                                            lambda: self._walker_escape(basis, leg), first=True)
                if got != "clear":
                    return got
                st = self.state
                continue
            buttons, u, frames, slow = hold
            gait = "walk" if slow else "run"
            leg["pressed"] = (buttons, u)
            leg["turned"] = None              # the yaw the last hold left is no longer his: known again once measured
            steps = [f"hold {b} {frames}" for b in buttons]
            if slow:
                steps.insert(0, f"hold cancel {frames}")
            self.send(*steps, f"wait {frames + 4}")
            after = self.settle()
            if after.field_id != field or after.player_x is None or not after.control:
                return "short"        # out of the field, or into a trigger: its scripted walk is not this hold's
            if watch is not None:
                self._note_lag(watch, after.frame - st.frame - frames)      # read to read, beyond the press
                if self._npc_moved(after, watch):
                    return "moved"
            mx, mz = after.player_x - st.player_x, after.player_z - st.player_z
            moved = (mx * mx + mz * mz) ** 0.5
            self._check_movement(moved, frames, gait, rate, what="a hold", span=(st.frame, after.frame))
            # the yaw this hold leaves him (where a facing step starts, :meth:`_held_yaw`): every MovePC call it spent
            # turned him toward ``u`` -- the whole calls its frames are sure of at the rate and the gait truly held
            # (Rate.calls_sure: whole ticks, a run's in pairs -- a walk's on a dash-inhibited field, :meth:`_gait`), and
            # no more than the STEP_PER_CALL steps it moved him (a wall stops a step and not the turn; a hold on
            # movement stops both). Set only here, after the measurement: a hold that returned before it (an object
            # moved) left the yaw unknown
            leg["turned"] = ((buttons, u), min(rate.calls_sure(frames, self._gait(gait)),
                                               moved / doorface.STEP_PER_CALL))
            slid = False
            # walk_to's basis check, on the direction actually pressed (see there)
            if self._burst_is_evidence(moved, frames, gait, rate):
                projected = mx * u[0] + mz * u[1]
                if projected < 0.35 * moved and slides:
                    self._log(f"  route_to: holding {'+'.join(buttons)} slid him {moved:.0f}u along "
                              f"({mx:+.0f},{mz:+.0f}) -- round someone in the way, not a wrong basis; stopping here")
                    slid = True
                elif projected < 0.35 * moved:
                    self._axes.pop(field, None)
                    raise HarnessError(
                        f"the axis basis for field {field} disagrees with what the game did: holding "
                        f"{'+'.join(buttons)} moved {moved:.0f}u along ({mx:+.0f},{mz:+.0f}), which projects only "
                        f"{projected:.0f}u onto the calibrated direction {_vec(u)}. The basis was probably measured "
                        f"against a wall; it has been discarded. Recalibrate from open ground.")
            if not slid:
                gap = ((x - after.player_x) ** 2 + (z - after.player_z) ** 2) ** 0.5
                if finish:        # into the zone, past the goal point if need be: a press no nearer the zone stalls
                    overshot = (pathfind.poly_gap(after.player_x, after.player_z, zone)
                                >= pathfind.poly_gap(here[0], here[1], zone) - 0.5)
                else:             # past the goal -- unless it left him where the zone's finish takes over
                    overshot = ((x - after.player_x) * u[0] + (z - after.player_z) * u[1] < 0 and gap > aim
                                and (zone is None or gap > tolerance))
                if moved < 1.0 and rate.ticks_sure(frames) < 1:
                    # a press whose frames may all fall between two field ticks ran no MovePC call, perhaps -- and
                    # moved nothing: no wall, no stall, nothing learnt. The next press from here is sure of a tick
                    least = self._least_frames(rate)
                else:
                    least = 1
                    stalls = stalls + 1 if (moved < 1.0 or overshot) else 0
                    stuck = stuck | {buttons} if moved < 1.0 else set()
            if slid or stalls >= 2:
                if finish and watch is not None:
                    # two presses into the zone moved him nothing, or no nearer it -- or one slid him round someone:
                    # where a WALKER in the way in is the cause, it is waited on -- and stepped away from, held on him
                    got = self._outwait_hold(basis, leg, field)
                    if got == "clear":
                        if self._box_released(watch):
                            return "unboxed"
                        stalls, stuck, st = 0, set(), self.state
                        continue
                    if got is not None:
                        return got
                break
            st = after
        final = self.state
        if final.field_id != field or final.player_x is None:
            return "short"
        gap = math.hypot(final.player_x - x, final.player_z - z)
        if zone is None:
            return "arrived" if gap <= tolerance else "short"
        if pathfind.poly_gap(final.player_x, final.player_z, zone) < 0:
            return "arrived"
        if gap > tolerance:
            return "short"
        if watch is not None and watch["held"] is None and final.control:
            # an end short of the zone the finish has not judged yet -- the holds spent, or a slide or a stall that left
            # him within tolerance before the finish took over: judged as every other end of it is, before it ends
            got = self._outwait_hold(basis, leg, field)
            if got == "clear" and self._box_released(watch):
                return "unboxed"
            if got not in (None, "clear"):
                return got
            final = self.state                    # after a wait that let him go with no re-plan left: where it left him
            if final.field_id != field or final.player_x is None or not final.control:
                return "short"
            gap = math.hypot(final.player_x - x, final.player_z - z)
            if pathfind.poly_gap(final.player_x, final.player_z, zone) < 0:
                return "arrived"
            if gap > tolerance:
                return "short"
        # within tolerance of the goal is not in the zone: the finish found nothing further it may press, and no
        # walker in the way in (:meth:`_outwait_hold` judged so where he stands, into watch["held"]) -- the spot, or
        # what does not walk
        self._log(f"  route_to: the finish ended at ({final.player_x:.0f}, {final.player_z:.0f}), {gap:.0f}u from the "
                  f"goal and OUTSIDE its zone: nothing further gets him in")
        return "outside"

    @staticmethod
    def _held_yaw(leg: dict | None) -> tuple | None:
        """Where the walk's last hold left his yaw, when that is known: ``(yaw, off)``, degrees -- the yaw of the
        direction it held (content.doorface.yaw_of) and how far off that he may still face: what the hold's MovePC
        calls left of a turn from ANY yaw (180 * 0.6**calls, doorface.worst_face_error's first term) plus the leg's
        heading spread (the pad truly heads that far off its calibrated direction). From ``leg["turned"]``
        (:meth:`_walk_leg`); None -- unknown -- with no smooth leg, before its first hold, and once a press along
        another line followed it."""
        import math
        from ff9mapkit.content import doorface
        if leg is None or leg.get("turned") is None:
            return None
        (_buttons, u), calls = leg["turned"]
        return (doorface.yaw_of(*u), 180.0 * (1.0 - doorface.TURN_PER_CALL) ** calls + math.degrees(leg["spread"]))

    def _face_reach(self, here, u, reach: float, spread: float, floor, memo: dict, zone=None):
        """Every point a press from ``here`` along unit ``u``, covering ``reach``, can leave him at -- sampled
        ROUTE_FACE_GRID apart, ``here`` first -- as ``(points, slid, free)``: ``points`` all of them, ``slid`` the ones
        only a slide along a wall reaches (below), ``free`` how far EVERY line runs before the floor stops it (``reach``
        when none meets a wall). With ``zone`` (the door's region, the ENGINE's polygon: content.doorface.
        region_contains, IsInQuad), None as soon as one point is not IN it.

        FREE, he goes straight: along every line within ``spread`` (radians) of ``u`` -- five of them, as a hold's fan
        is judged -- until his centre can stand no further on ``floor`` (:meth:`_can_stand`: COLLISION_RADIUS_W off its
        walls, or no nearer than he already stands). THEN THE WALL. The engine keeps the part of a step along the wall
        -- a centre a step left within his radius of a wall edge is pushed back along the edge's normal onto the radius
        line (ServiceChar -> RadiusValid -> ServiceForces, FieldMapActorController.cs:947-1252 at stock 6b8bb2d5) --
        and a step projected onto any line through its start lands on the circle whose DIAMETER is that step (Thales)
        -- so each call of the rest moves him within that circle, and a run of calls, a slide round a corner too, stays
        within the disc whose diameter is the reach still to go, laid along the press from where the line met the wall
        (discs of diameters laid end to end add up to the disc of their sum). Every point of that disc his centre can
        stand on -- the disc widened for the lines between the five, and a grid step -- is a point the press can leave
        him at: a slide can take him anywhere in it, and one along a wall that crosses the zone's side takes him out of
        it (the fake's floor, which slides so, carries presses out of most of Dali's gated door zones from some of their
        standable points, 350's door to 351 among them). Where no line meets a wall there is no disc: the lines are all
        of it. Where one meets it head on the disc still counts a slide either way -- the price of not knowing the
        wall's line.

        ``memo`` keeps the floor's answers (:meth:`_wall_gap`), by integer point, across the calls of one facing
        step."""
        import math
        from ff9mapkit.content import doorface
        from ff9mapkit.scene import cam
        g = self.ROUTE_FACE_GRID
        own = self._wall_gap(floor, here[0], here[1], memo)
        least = min(cam.COLLISION_RADIUS_W, own if own is not None else 0.0) - 1.0

        def keeps(x, z) -> bool:
            return zone is None or doorface.region_contains(x, z, zone)

        pts, slid, free = [(float(here[0]), float(here[1]))], [], reach
        walls = []                                    # (where the line met the wall, the reach still to go, its line)
        for e in ([_turn(u, spread * k / 2.0) for k in (-2, -1, 0, 1, 2)] if spread > 0 else [u]):
            at, gone = here, 0.0
            while gone < reach:
                ahead = min(reach, gone + g)
                p = (here[0] + e[0] * ahead, here[1] + e[1] * ahead)
                if not self._can_stand(floor, p[0], p[1], least, memo):
                    break
                if not keeps(*p):
                    return None
                pts.append(p)
                at, gone = p, ahead
            free = min(free, gone)
            if reach - gone > 1e-6:
                walls.append((at, reach - gone, e))
        if not walls:
            return pts, slid, free
        centres = [(a[0] + e[0] * rest / 2.0, a[1] + e[1] * rest / 2.0) for a, rest, e in walls]
        cx, cz = sum(c[0] for c in centres) / len(centres), sum(c[1] for c in centres) / len(centres)
        rest = max(w[1] for w in walls)
        r = (max(math.hypot(c[0] - cx, c[1] - cz) + w[1] / 2.0 for c, w in zip(centres, walls))
             + rest / 2.0 * spread / 2.0 + g)
        for i in range(math.floor((cx - r) / g), math.ceil((cx + r) / g) + 1):
            for j in range(math.floor((cz - r) / g), math.ceil((cz + r) / g) + 1):
                x, z = i * g, j * g
                if (x - cx) ** 2 + (z - cz) ** 2 > r * r or not self._can_stand(floor, x, z, least, memo):
                    continue
                if not keeps(x, z):
                    return None
                pts.append((x, z))
                slid.append((x, z))
        return pts, slid, free

    def _slide_clear(self, here, slid, leg: dict, frames: int, rate: Rate | None = None) -> bool:
        """Do the points a press can only SLIDE him to (:meth:`_face_reach`'s ``slid``: along a wall, off the lines
        :meth:`_press_clear` judges) keep what those lines keep -- whatever the press is for, its movement tail
        included? No other zone of ``leg["hazards"]`` entered or approached nearer than PROBE_HAZARD_PAD (or than he
        already stands; one he stands IN is the lines' to leave, by their Keepout rule), and no published object of
        the leg (:meth:`_leg_discs`) neared past its ``pad`` off its radius ``R`` (or nearer than he already stands) --
        a WALKING one by as far again as it can walk by the next read (its ``speed`` a frame over the press, its tail's
        frames at ``rate`` -- :meth:`_tail_frames`, default :meth:`rate` -- and :meth:`_walker_lag`): a slide into a
        trigger's Range fires its script exactly as a straight walk into it would, and the door's record would carry
        the blame."""
        import math
        from ff9mapkit.content import pathfind
        if not slid:
            return True
        for poly in leg["hazards"]:
            gap = pathfind.poly_gap(here[0], here[1], poly)
            if gap >= 0 and any(pathfind.poly_gap(x, z, poly) < min(self.PROBE_HAZARD_PAD, gap) - 0.5
                                for x, z in slid):
                return False
        rate = self.rate() if rate is None else rate
        until = frames + self._tail_frames(rate) + self._walker_lag(leg.get("watch"))
        for d in self._leg_discs(leg):
            walk = d["speed"] * until if d["moving"] else 0.0
            need = min(d["pad"], math.hypot(here[0] - d["x"], here[1] - d["z"]) - d["R"]) - 0.5 + walk
            if any(math.hypot(x - d["x"], z - d["z"]) - d["R"] < need for x, z in slid):
                return False
        return True

    def _face_the_door(self, zone, record: dict, origin: int, walked: list, leg: dict, held=None, window=None,
                       walk_zone=None, timeout: float = 20.0) -> str | None:
        """route_to's last step at a GATED door (:meth:`route_to` ``face``) once the walk has ended standing IN its
        region ``zone`` -- world ``(x, z)`` corners, the ENGINE's polygon in the engine's order (scan_gateways'
        ``region``), membership by IsInQuad (content.doorface.region_contains) -- with control, and
        ROUTE_FACE_WAIT_TICKS field ticks on (:meth:`_face_wait_frames`) nothing has fired: turn him to FACE THE DOOR,
        as stock's gate needs, and give it its chance.

        THE GATE (content.doorface; Memoria 6b8bb2d5, stock line numbers). The region's tag 2 runs every tick he stands
        in it with control (EventEngine.ProcessEvents.cs:174-178 -> EventCollision.CollisionRequest, :281-284). On a
        class-2 door it computes the exit position -- his projection onto the region's FIRST EDGE, ``zone[0] ->
        zone[1]`` (EventEngine.DoEventCode.cs:2213-2240, ``case MJPOS``) -- and runs the warp only while his yaw is
        within the gate's ``window`` (``(lo, hi)``, scan_gateways' ``face_gate``: 47/256 of a turn for the stock (48,
        208); B_LT / B_GT strict, EBin.cs:722 / :735) of the bearing to it. The yaw moves only while a direction is
        held with control, 40% of the way a MovePC call, BEFORE the walls and bodies have their say -- a press into a
        wall turns him and moves him nowhere -- and standing keeps it exactly (FieldMapActorController.cs:744-761). The
        calls come WHOLE, a walked one a 30 Hz tick (:197-208, HonoBehaviorSystem.cs:106), in a phase nobody sees: a
        press of ``n`` walked frames counts the whole ticks its frames are SURE to hold at the measured rate
        (Rate.calls_sure: ``n`` times the ticks a frame holds at the fastest rate the measurement allows, rounded
        DOWN) -- never the average. The press is planned only at a MEASURED rate (:meth:`rate` ``require=True``): with
        none, nothing is pressed and the step ends ``faced`` False (LIVE) -- the calibrated 60 fps would credit a
        120 fps press twice the calls it ran, and at 31 fps judge half its reach.

        TWO WAYS, BY WHAT THE ENGINE CAN DO -- decided on the sample the step starts from:

          * THE CLOSED LOOP (State.facing_status "known": memoria-patch s90 publishes the facing byte the gate reads
            and turns him in place): :meth:`_turn_to_the_door` turns him IN PLACE toward the door and judges it on the
            MEASURED facing -- no step, so none of the press's zone-keeping, slide bound or bursts below is needed, and
            a door the press could not reach without leaving the region (stock 350's door to 353 from the tour's goal
            pocket) is faced where he stands. ``face_measured`` True where the engine's own report decided ``faced``.
          * THE OPEN LOOP (the engine CANNOT: facing_status "cannot", a pre-s90 DLL -- or "unknown", no facing this
            sample; or the turn is refused for a reason a press does not share, TURN_FALLBACK: ``unknown op``,
            ``[AnalogControl] Enabled=0`` -- or a body he overlaps that is still on him after the wait for it): the
            walked press below, UNCHANGED. The yaw is not read
            (``player.dir`` is PosObj.rot[1], which a field never writes), so whether he faces the door is PREDICTED
            from the presses; ``face_measured`` False.

        THE PRESS: one of the eight pads (:func:`_eight_way` of the calibrated basis), WALKED -- a run spends the same
        calls over the same ground with twice the tail, so it keeps the rules nowhere a walk does not -- for the fewest
        frames after which the prediction says he faces the door: ROUTE_FACE_CALLS whole calls at the least,
        ROUTE_FACE_MAX_CALLS of one pad at the most, and doorface.worst_face_error at most the window's
        doorface.face_limit_deg -- the turn left from his yaw before it (``held``, where the walk's last hold left it,
        :meth:`_held_yaw`, when that is known; any yaw when not), the pad's offset from the bearing at the WORST point
        the press can have taken him to by then (the bearing moves as he does), the leg's heading ``spread``, and a unit
        of the bytes' quantization. It keeps the rules. Every point it can have taken him to by the call the prediction
        says faced stands IN the region (:meth:`_face_reach`: along the line until the floor stops him, then as far as
        a slide along the wall can go) -- the gate is tested every tick he stands there, so it fires by then. And the
        WHOLE press, as far as its frames can carry him (Rate.reach, its tail included), keeps every rule a smooth hold
        keeps -- the rest
        of it runs on for a door that stays shut: its lines by :meth:`_press_clear` (no other zone of ``leg["hazards"]``
        entered or approached, no object ``leg["watch"]`` keeps neared, a walking trigger judged where it can walk --
        and, on a read taken just before it is sent, :meth:`_walkers_let_press`), the points only a slide along a wall
        reaches by :meth:`_slide_clear` (the same zones and objects, from where the slide takes him).

        Of the pads whose press keeps them all, the one that needs the fewest frames (the nearest, of two alike) --
        where the nearest pad's press breaks a rule, a farther pad's, with the calls its offset asks. Where no press
        does, a BURST: the longest press whose WHOLE travel, tail included, stays in the region and keeps the rules --
        of the pad the bursts so far pressed, whose whole calls add up (standing keeps the yaw), else of the nearest pad
        that has one, starting from the yaw the presses so far leave him (their own prediction) -- and then the choice
        again from where it left him, at most ROUTE_FACE_PRESSES presses in all, until one the prediction says faced
        has been made (stock 350's door to 351, where he can stand in a strip of the zone 30-60u wide along the wall: a
        burst of right to the wall, then up+right along it). A pad that could not face the door from where he stands
        with all its calls is never pressed. Nothing keeps the rules: nothing is pressed.

        EACH PRESS IS CHECKED against what it moved him. A press whose every line ran FREE for its own frames (no wall
        within them) moves him a full 30u a call it ran (a call never steps further), so one that moved him less than
        the calls it was counted for did not run them all -- a hold on movement (the pad mask: control kept, MovePC
        returns before it moves or turns anyone, FieldMapActorController.cs:586), or fewer ticks than the measured
        rate says: it is counted only by the whole calls its travel proves, and the step presses on -- and the press
        goes to the movement cross-check (:meth:`_check_movement`, ``free``) either way. (A press into a wall is not
        checkable so -- the wall stops the steps and not the turn -- and keeps its count.) Where the engine PUBLISHES
        his yaw (memoria-patch s90: this press is its fallback -- a ``turn`` refused for a reason a press does not
        share), the press's calls are read off the yaw instead, walled or free (:meth:`_calls_turned`: exact where it
        answers, a hitched frame's burst of ticks included): fewer than its frames are sure of re-judge the
        prediction, as a free press's short travel does.

        Standing in the zone the walk was sent into (``walk_zone``, the kit's quad) but in NO triangle of the region --
        the dead middle of a 5- to 8-point region, which IsInQuad never holds -- the door cannot fire at all, and no
        press is planned from there: ``faced`` False, as for a door no press could face.

        Returns "face" when control went away during its presses (or turns) -- the door fired, or something the press
        met did: the caller lands it as the walk's own loss of control is landed; a press so cut reads ``faced`` True
        (its prediction), a turn only where the field then changed (:meth:`_turn_landing`) -- else None, with
        ``record``'s ``faced``, ``face_measured``, ``face_err``, ``face_worst``, ``face_to``, ``face_calls``,
        ``face_pad`` and
        ``face_moved`` said (:meth:`route_to`; the calls and pad of the last pad pressed, the ones the prediction
        counts -- or turned, the ones the engine reported): all left None where he did not stand in the zone with
        control, or the door fired while he stood there (the caller waits for that crossing as for any). ``timeout``
        is route_to's: how long a turn's loss of control is waited on to say whether the field changed."""
        import math
        from ff9mapkit.content import doorface, pathfind
        window = doorface.FACE_WINDOW if window is None else (int(window[0]), int(window[1]))

        def standing(s) -> bool:
            return s.field_id == origin and s.player_x is not None and s.control

        def inside(s) -> bool:
            return standing(s) and doorface.region_contains(s.player_x, s.player_z, zone)
        q0, q1 = zone[0], zone[1]
        st = self.state
        if not inside(st):
            if walk_zone is not None and standing(st) and pathfind.poly_gap(st.player_x, st.player_z, walk_zone) < 0:
                record["face_to"] = list(doorface.calc_exit_position(st.player_x, st.player_z, q0, q1))
                record["faced"], record["face_measured"] = False, False
                self._log(f"  route_to: standing at ({st.player_x:.0f}, {st.player_z:.0f}) in the zone but in no "
                          f"triangle of the door's region (its dead middle: the gate never runs there) -- nothing "
                          f"pressed")
            return None
        self.wait_frames(self._face_wait_frames())
        st = self.state
        if not inside(st):
            return None
        record["face_to"] = list(doorface.calc_exit_position(st.player_x, st.player_z, q0, q1))
        record["faced"], record["face_measured"] = False, False
        if st.facing_status == "known":
            # the engine publishes the facing and turns him in place (s90): the closed loop -- unless the turn is
            # refused for a reason a walked press does not share (TURN_FALLBACK), when the press below is the step
            got = self._turn_to_the_door(zone, record, origin, window, timeout, math.degrees(leg["spread"]))
            if got != "press":
                return got
            # the press decides now, from scratch: what a turn before the fallback measured is not its prediction --
            # and a turn that ran has moved his yaw off where the walk's last hold left it (``held``): any yaw, then
            if record["face_pad"] is not None:
                held = None
            record.update(face_measured=False, face_err=None, face_worst=None, face_calls=None, face_pad=None)
            st = self.state
            if not inside(st):
                return None
        rate = self._measured_rate()                              # the press is judged at it, or not pressed at all
        if rate is None:
            self._log(f"  route_to: standing in the door's zone with nothing fired, and no MEASURED render rate "
                      f"({self._clock.rate().describe()}): the press's calls and reach cannot be judged -- nothing "
                      f"pressed")
            return None
        st = self.state                                           # read after any wait for the rate: frames went by
        if not inside(st):
            return None
        watch = leg.get("watch")
        if watch is not None:
            self._npc_view(watch, st)                             # the objects where they stand now
        here = (st.player_x, st.player_z)
        record["face_to"] = list(doorface.calc_exit_position(here[0], here[1], q0, q1))
        limit = doorface.face_limit_deg(window)
        spread_deg = math.degrees(leg["spread"])
        step = doorface.STEP_PER_CALL
        left = 1.0 - doorface.TURN_PER_CALL                       # what one call leaves of a turn
        memo: dict = {}
        walkers, swept, still = self._press_discs(leg)

        def turn_from(u, yaw) -> float:
            """How far his yaw may be from where pad ``u`` truly heads, before it is pressed: ``yaw`` =
            ``(centre, off)`` -- he faces within ``off`` of ``centre`` -- or None, anywhere (180)."""
            if yaw is None:
                return 180.0
            return min(180.0, doorface.angle_off(yaw[0], doorface.yaw_of(*u)) + yaw[1] + spread_deg)

        def sure(n: int) -> int:
            return rate.calls_sure(n, "walk")                     # whole walked calls: one a tick it is sure of

        def ruled(at, u, n: int, within=None):
            """Where the WHOLE press of ``n`` frames from ``at`` along ``u`` can leave him, as far as its frames can
            carry him (Rate.reach, its tail included; :meth:`_face_reach`), when it keeps every rule a smooth press
            keeps -- its lines (:meth:`_press_clear`) and its slides (:meth:`_slide_clear`) -- and, with ``within``,
            stays in that region all the way (a burst's rule); else None."""
            if not self._press_clear(at, u, n, "walk", leg, walkers, swept, still, rate):
                return None
            got = self._face_reach(at, u, rate.reach(n, "walk"), leg["spread"], leg["floor"], memo, within)
            return got if got is not None and self._slide_clear(at, got[1], leg, n, rate) else None

        def scan(u, at, spent: float, off: float):
            """``(frames, faced, worst, free)`` for pad ``u`` from ``at``, ``spent`` whole calls of it already made
            from a yaw ``off`` (:func:`turn_from`) off it: the fewest frames whose prediction says faced, in the
            region to that call and keeping the rules over the whole press (``faced`` True, ``worst`` the pad's
            largest offset from the bearing it can meet by then); else the longest burst whose whole travel stays in
            the region and keeps them, found by bisection -- a rule a press keeps, a shorter one keeps (``faced``
            False; 0 frames: none). ``free``: its lines run free of walls for all its frames at the rate's average
            walk (what a press is checked against after it is made). The fewest frames are the fewest SURE of the
            calls still wanted (Rate.frames_for_ticks: a walked call a tick); the most, those whose average calls
            reach ROUTE_FACE_MAX_CALLS."""
            need = max(1, rate.frames_for_calls(self.ROUTE_FACE_CALLS - spent, "walk"))
            most = int((self.ROUTE_FACE_MAX_CALLS - spent) / rate.per_frame() + 1e-9)
            if most < 1:
                return 0, False, None, False
            yaw = doorface.yaw_of(*u)
            for n in range(min(need, most), most + 1):
                faced_by = self._face_reach(at, u, sure(n) * step, leg["spread"], leg["floor"], memo, zone)
                travel = None if faced_by is None else ruled(at, u, n)
                if travel is None:
                    break
                worst = max(doorface.angle_off(yaw, doorface.bearing_deg(x, z, q0, q1)) for x, z in faced_by[0])
                if doorface.worst_face_error(worst, spent + sure(n), spread_deg, off) <= limit:
                    return n, True, worst, travel[2] >= n * rate.speed("walk") - 1e-6

            lo, hi = 0, most
            while lo < hi:
                mid = (lo + hi + 1) // 2
                lo, hi = (mid, hi) if ruled(at, u, mid, zone) is not None else (lo, mid - 1)
            got = ruled(at, u, lo, zone) if lo else None
            return lo, False, None, got is not None and got[2] >= lo * rate.speed("walk") - 1e-6

        pad, spent, est = None, 0.0, held          # the pad pressed so far, its whole calls, and his yaw before them
        moved = 0.0
        for _ in range(self.ROUTE_FACE_PRESSES):
            bearing = doorface.bearing_deg(here[0], here[1], q0, q1)
            now = (est if pad is None
                   else (doorface.yaw_of(*pad[1]), spread_deg + turn_from(pad[1], est) * left ** spent))
            whole, more, other = [], [], []                # presses that face it; bursts of this pad; of another
            for buttons, u in sorted(_eight_way(self._axes[origin]),
                                     key=lambda p: doorface.angle_off(doorface.yaw_of(*p[1]), bearing)):
                mine = pad is not None and buttons == pad[0]
                off, calls = (turn_from(u, est), spent) if mine else (turn_from(u, now), 0.0)
                if doorface.worst_face_error(doorface.angle_off(doorface.yaw_of(*u), bearing),
                                             self.ROUTE_FACE_MAX_CALLS, spread_deg, off) > limit:
                    continue                               # not even all its calls would face it from here
                n, done, worst, free = scan(u, here, calls, off)
                if n:
                    (whole if done else more if mine else other).append((n, buttons, u, done, mine, worst, free))
            pick = next((p for p in sorted(whole, key=lambda p: p[0]) + more + other
                         if self._walkers_let_press(here, (p[1], p[2], p[0], True), leg, rate)), None)
            if pick is None:
                break
            n, buttons, u, done, mine, worst, free = pick
            if not mine:
                est, pad, spent = now, (buttons, u), 0.0
            self._log(f"  route_to: standing in the door's zone at ({here[0]:.0f}, {here[1]:.0f}) with nothing fired: "
                      f"{n} walked frame(s) {'+'.join(buttons)} to face its exit point {tuple(record['face_to'])}"
                      + ("" if done else " (a burst)"))
            yaw0 = self.state.player_yaw                              # s90 publishes it; None before
            moved = self._pressed(origin, walked, f"hold cancel {n}", *[f"hold {b} {n}" for b in buttons],
                                  f"wait {n + 4}")
            self._check_movement(moved, n, "walk", rate, free=free, what="a facing press", span=self._press_span)
            got = sure(n)
            ran = None if moved is None else self._calls_turned(yaw0, self.state.player_yaw, doorface.yaw_of(*u),
                                                                "walk", spread_deg)
            if ran is not None:
                if ran != got:
                    self._log(f"  route_to: the press turned him {ran} call(s), read off his yaw, where its frames are "
                              f"sure of {got} at {rate.describe()}: counted {ran}")
                if ran < got:
                    done = done and doorface.worst_face_error(worst, spent + ran, spread_deg,
                                                              turn_from(u, est)) <= limit
                got = ran
            elif moved is not None and free and moved < got * step - 1.0:
                proved = int(math.floor((moved + 1.0) / step))
                self._log(f"  route_to: the press moved him {moved:.0f}u on free floor, where its {got} call(s) step "
                          f"{got * step:.0f}u -- they did not all run (a hold on movement, or fewer ticks than "
                          f"{rate.describe()} holds): counted {proved}")
                got = proved
                done = done and doorface.worst_face_error(worst, spent + got, spread_deg,
                                                          turn_from(u, est)) <= limit
            spent += got
            record["face_pad"], record["face_calls"] = "+".join(buttons), spent
            if moved is None or done:
                record["faced"] = True
                break
            st = self.state
            here = (st.player_x, st.player_z)
            if watch is not None:
                self._npc_view(watch, st)
                walkers, swept, still = self._press_discs(leg)
        if pad is None:
            self._log(f"  route_to: standing in the door's zone at ({here[0]:.0f}, {here[1]:.0f}) with nothing fired, "
                      f"and no press that faces its exit point {tuple(record['face_to'])} keeps the rules: nothing "
                      f"pressed")
            return None
        st = self.state
        if standing(st):
            here = (st.player_x, st.player_z)
        target = doorface.yaw_of(*pad[1])
        # the bound the prediction holds him to where the step left him, in units (the gate's), and -- when his yaw
        # before the pad was known -- the error its centre predicts; from an unknown yaw there is no centre to name
        record["face_worst"] = math.ceil(doorface.worst_face_error(
            doorface.angle_off(target, doorface.bearing_deg(here[0], here[1], q0, q1)), spent, spread_deg,
            turn_from(pad[1], est)) / doorface.UNIT_DEG - 1e-9)
        if est is not None:
            yaw = doorface.turn_step(est[0], target, spent)
            record["face_err"] = doorface.signed_error(doorface.gate_value(here[0], here[1], yaw, q0, q1))
        return "face" if moved is None else None

    def _turn_to_the_door(self, zone, record: dict, origin: int, window, timeout: float,
                          spread: float = 0.0) -> str | None:
        """:meth:`_face_the_door`'s CLOSED LOOP, on an engine that publishes the facing (memoria-patch s90): standing IN
        the door's region ``zone`` (the engine's polygon, its first edge ``zone[0] -> zone[1]``) with control and
        nothing fired, turn him IN PLACE toward the door and decide by what the ENGINE reports, never by a prediction.

        THE TURN. The pad (:func:`_eight_way` of the calibrated basis) whose heading -- content.doorface.yaw_of of its
        world direction, the field's twist already in the basis -- is nearest the bearing to the exit point
        (doorface.bearing_deg: his projection onto the first edge), held by :meth:`turn_in_place` at the run rate for
        the fewest frames SURE of the whole run ticks -- two calls each -- that make ROUTE_TURN_CALLS, at the measured
        rate (:meth:`rate`, Rate.frames_for_ticks: 8 frames at 60 fps, 4 at 30; a SIZE -- the engine reports what the
        turn did, and more calls in place only cost frames). He does not step, so no zone is left, entered or neared
        and no slide is bounded: the press's
        rules have nothing to keep. Its ``turn_end`` comes once the field has run its event passes on the final facing
        (HarnessAgent.ServiceTurn), so the outcome below is the gate's own.

        THE OUTCOME, by the ``turn_end``:
          * the field changed, or control went and the field then changed (the door's DisableMove runs in the pass
            that reads the facing -- Dali 350 e18 before any Wait -- so a door that fires ends the turn ``control``):
            the door fired. "face" -- landed by route_to as the walk's own loss of control is (``during`` "face"),
            ``faced`` True and, the field change seen, ``face_measured`` True (no final facing: ``face_err`` None).
            Control gone and never back within ``timeout``, the field unchanged, is landed the same way but is NO door
            (``control`` is not proof one fired: a talk the turn now faces, an ATE, a timed script take him as well --
            the s90 contract): ``faced`` False, ``face_measured`` False -- LIVE, never the door's strike
            (:meth:`_turn_landing`; a door that fires late is still landed by route_to's own wait).
          * ``ended``: the field judged the final facing and did not take him. The gate value is computed from the
            facing BYTE it reports -- doorface.gate_value_from_face, against the engine's exit point from his published
            position -- and in the window (doorface.gate_faced, the gate's own strict compare) the door read that
            facing and stayed shut: ``faced`` True, ``face_measured`` True, ``face_err`` that MEASURED signed error,
            ``face_worst`` its size -- a REAL miss, measured. Out of the window he is turned again, at most
            ROUTE_TURN_TRIES turns: the same pad while its turn still moved his yaw (fewer calls than planned -- a
            machine not the calibrated one), a different pad once one SETTLED (moved his yaw, under ROUTE_TURN_SETTLED
            degrees: that pad heads where it left him, outside the window -- pad offset and twist) -- ranked by the
            heading the settled one measured, the basis's own error carried over. A turn that did not move his yaw AT
            ALL proves no call ran (ROUTE_TURN_SETTLED's note): never read as settled, nor as a basis, until the same
            pad, turned again for twice the frames, is unmoved a second time in a row. A turn that moved him more than
            ROUTE_TURN_MOVED was not in place (a push-out, a wall's edge force): it is judged as the press it was, from
            where it left him, and if that is outside the region the gate never ran there -- ``faced`` False. None of
            the pads' headings within the window's doorface.face_limit_deg of the bearing, or the turns spent:
            ``faced`` False (``face_measured`` True where a turn's report was judged), LIVE -- the walker's limit,
            never the door's strike.
          * any other ``why`` -- a CUT (``movement``, ``hud``, ``actor``, ``unreadable``; ``player``/``control`` with
            control back on the same field -- a script or a talk took him, not the door): handled as the matching
            REFUSAL is -- waited out (ROUTE_WAIT_SECONDS for a hold on movement or a UI, ROUTE_FACE_WAIT_TICKS else) and
            turned again within the bound, never judged on the cut turn's byte (the field never had its passes on it)
            and never a strike. ``axis`` (a physical stick: a human at the controls) ends the step, ``faced`` False.

        A REFUSAL (:class:`channel.TurnRefused`, nothing pressed): one in TURN_FALLBACK returns "press" -- the walked
        press of the open loop is the step instead; ``overlap`` is waited out once for its body and returns "press"
        when the same body is still on him (TURN_FALLBACK's note); ``argument``/``opposite``/``other`` are the
        driver's own error and raise; ``axis``/``path`` (a human's stick or mouse walk) end the step, ``faced`` False;
        control or the field gone is landed as above; the rest are waited out and turned again within the bound.

        ``face_pad`` is the last pad turned, ``face_calls`` the whole calls the turns RAN -- each read off the yaws its
        ``turn_end`` reports toward the pad's heading, the basis's measured error carried (:meth:`_calls_turned`: at
        31 fps a count of frames recorded half the calls a turn ran -- the facing check's 4 of about 8 -- and a hitched
        frame's burst runs more than any rate is sure of) where the heading's uncertainty (``spread``, degrees: the
        leg's) reads ONE whole count, or where they do not say -- a long turn ends a fraction of a degree off the pad,
        and a tenth of one moves its count by a call -- the calls its reported ``frames`` are sure of at the run rate
        (Rate.calls_sure: whole ticks, in pairs): never more than ran. ``face_moved`` the largest ``moved`` a turn
        reported (0: in place). Returns "face", None (``record`` said), or "press" (fall back)."""
        import math
        from ff9mapkit.content import doorface
        from .channel import TurnRefused
        q0, q1 = zone[0], zone[1]
        limit = doorface.face_limit_deg(window)
        rate = self.rate()                                       # a SIZE: the engine reports what the turn did
        frames = rate.frames_for_calls(self.ROUTE_TURN_CALLS, self._gait("run"))
        pads = _eight_way(self._axes[origin])
        settled: set = set()                                     # pads whose heading a settled turn measured
        unmoved: set = set()                                     # pads whose last turn left his yaw exactly as it was
        basis = 0.0                                              # the basis's own error the settled turn measured
        waited_for: list = []                                    # the bodies an ``overlap`` refusal was waited out for
        for _ in range(self.ROUTE_TURN_TRIES):
            st = self.state
            if st.field_id != origin or not st.control:
                landed = self._turn_landing(origin, timeout, record)
                if landed is not None:
                    return landed
                st = self.state
            if st.ui_state != "FieldHUD":
                # a UI over the field (the agent's ``hud`` refusal, before it is asked): waited out like that refusal
                self._log(f"  route_to: {st.ui_state} is up over the field; waiting before the turn")
                self.wait_frames(self._frames_lasting(self.ROUTE_WAIT_SECONDS))
                continue
            here = (st.player_x, st.player_z)
            if here[0] is None or not doorface.region_contains(here[0], here[1], zone):
                self._log(f"  route_to: no longer in the door's region before a turn (at {here}): nothing turned")
                return None
            bearing = doorface.bearing_deg(here[0], here[1], q0, q1)
            ranked = sorted((doorface.angle_off(doorface.yaw_of(*u) + basis, bearing), buttons, u)
                            for buttons, u in pads if buttons not in settled)
            ranked = [r for r in ranked if r[0] <= limit]
            if not ranked:
                self._log(f"  route_to: no pad heads within {limit:.0f} degrees of the door's bearing "
                          f"({bearing:.1f}) once measured: the door cannot be faced from here -- LIVE")
                return None
            _off, buttons, u = ranked[0]
            try:
                end = self.turn_in_place(buttons, frames, timeout=timeout)
            except TurnRefused as err:
                if err.kind in self.TURN_FALLBACK:
                    self._log(f"  route_to: the turn was refused ({err.message}) -- a walked press does not share "
                              f"that: the open-loop press faces the door instead")
                    return "press"
                if err.kind == "overlap":
                    if err.uid in waited_for:
                        self._log(f"  route_to: the turn was refused again ({err.message}) -- that body stays on him: "
                                  f"the open-loop press, planned clear of the objects, faces the door instead")
                        return "press"
                    waited_for.append(err.uid)
                    self._log(f"  route_to: the turn was refused ({err.message}); waiting for that body to move on")
                    self.wait_frames(self._frames_lasting(self.ROUTE_WAIT_SECONDS))
                    continue
                if err.kind in ("argument", "opposite", "other"):
                    raise
                if err.kind in ("axis", "path"):
                    self._log(f"  route_to: the turn was refused ({err.message}): a human's input -- not fought")
                    return None
                st = self.state
                if st.field_id != origin or not st.control:
                    landed = self._turn_landing(origin, timeout, record)
                    if landed is not None:
                        return landed
                self._log(f"  route_to: the turn was refused ({err.message}); waiting it out")
                self.wait_frames(self._frames_lasting(self.ROUTE_WAIT_SECONDS)
                                 if err.why in ("movement", "hud", "actor") else self._face_wait_frames())
                continue
            record["face_pad"] = "+".join(buttons)
            ran = self._calls_turned(end["yaw0"], end["yaw"], doorface.yaw_of(*u) + basis, "run", spread)
            record["face_calls"] = (record["face_calls"] or 0) + (
                ran if ran is not None else rate.calls_sure(end["frames"] or 0, "run"))
            if end["moved"] is not None:
                record["face_moved"] = max(record["face_moved"] or 0.0, end["moved"])
            why = end["why"]
            st = self.state
            if why != "ended" or st.field_id != origin or not st.control:
                if why == "axis":
                    self._log("  route_to: the turn was cut by a physical stick: a human at the controls -- not fought")
                    return None
                if why in ("field", "control", "player") or st.field_id != origin or not st.control:
                    landed = self._turn_landing(origin, timeout, record)
                    if landed is not None:
                        return landed                # the field changed: the door fired
                self._log(f"  route_to: the turn was cut ({why}), nothing fired; turning again")
                self.wait_frames(self._frames_lasting(self.ROUTE_WAIT_SECONDS)
                                 if why in ("movement", "hud", "actor") else self._face_wait_frames())
                continue
            here = (st.player_x, st.player_z)
            if end["moved"] is not None and end["moved"] > self.ROUTE_TURN_MOVED:
                self._log(f"  route_to: the turn moved him {end['moved']:.2f}u -- not in place (a push-out or a "
                          f"wall's edge force): judged as the press it was, from ({here[0]:.0f}, {here[1]:.0f})")
                if not doorface.region_contains(here[0], here[1], zone):
                    return None                      # out of the region: the gate never ran on that facing there
            face = end["face"] if end["face"] is not None else st.player_face
            if face is None:
                continue
            v = doorface.gate_value_from_face(here[0], here[1], face, q0, q1)
            err = doorface.signed_error(v)
            record.update(face_measured=True, face_err=err, face_worst=abs(err))
            if doorface.gate_faced(v, window):
                record["faced"] = True
                self._log(f"  route_to: turned in place to face the door (measured error {err}/256, byte {face}) "
                          f"and the field judged it: still shut -- the door's REAL miss")
                return None
            if end["yaw"] is None or end["yaw0"] is None:
                continue
            turned = doorface.angle_off(end["yaw"], end["yaw0"])
            if turned > 0.0:
                unmoved.discard(buttons)             # a call ran: the next unmoved turn of it starts a new count
            elif buttons not in unmoved:
                # his yaw EXACTLY where it was: no call is proven to have run -- the turn's frames fit between two
                # 30 Hz ticks (a rate taken wrong: see ROUTE_TURN_CALLS), or the pad already heads where he stands.
                # Neither settled nor
                # a basis: the same pad again, for twice the frames -- and every turn after it keeps the longer count
                unmoved.add(buttons)
                frames = min(self.TURN_MAX_FRAMES, 2 * frames)
                self._log(f"  route_to: {record['face_pad']} did not move his yaw ({end['yaw']:.3f}) over "
                          f"{end['frames']} frame(s) -- no call is proven to have run; turning it again for "
                          f"{frames} frames")
                continue
            if turned <= self.ROUTE_TURN_SETTLED:
                settled.add(buttons)                 # this pad heads where it left him, outside the window
                basis = (end["yaw"] - doorface.yaw_of(*u) + 180.0) % 360.0 - 180.0
                self._log(f"  route_to: {record['face_pad']} settled at yaw {end['yaw']:.1f}, {err}/256 off the "
                          f"door -- it cannot face it; the basis heads {basis:+.1f} degrees off its calibration")
            else:
                self._log(f"  route_to: turned to yaw {end['yaw']:.1f}, still {err}/256 off the door; turning again")
        self._log(f"  route_to: {self.ROUTE_TURN_TRIES} turns and the door not faced -- LIVE")
        return None

    def _turn_landing(self, origin: int, timeout: float, record: dict) -> str | None:
        """Control went during (or just before) an in-place turn at the door: was it the door? Waits, as
        :meth:`_await_landing` does, for the field to change or control to come back on ``origin``. None when control
        came back on the same field (a script or a talk took him, not the door: a cut). Else "face" -- route_to lands
        it as the walk's own loss of control is, its own wait still catching a door that loads late -- with
        ``face_err`` / ``face_worst`` cleared (no final facing was the gate's to judge) and ``faced`` /
        ``face_measured`` True ONLY where the field changed: the door fired. Control gone and never back on an
        unchanged field is no door: ``control`` is not proof one fired (the s90 contract: a talk the turn now faces,
        an ATE, a timed script or a battle take him as well -- and a turn REFUSED for want of control pressed nothing
        at all), so it reads ``faced`` False, LIVE (dali_tour.unfaced), never the door's REAL miss."""
        try:
            self.wait_for(lambda s: (s.field_id != origin and s.field_id > 0) or (s.field_id == origin and s.control),
                          timeout=timeout, what=f"the field to change from {origin}, or control to return")
        except HarnessError:
            pass
        st = self.state
        if st.field_id == origin and st.control:
            return None
        fired = st.field_id != origin and st.field_id > 0
        record.update(faced=fired, face_measured=fired, face_err=None, face_worst=None)
        return "face"

    def route_to(self, x: float, z: float, *, avoid=(), margin: float | None = None,
                 tolerance: float = 45.0, walkmesh=None, prior="stock", timeout: float = 20.0,
                 unstick: bool = False, smooth: bool = False, zone=None, npcs: bool = False, face=None,
                 face_window=None, overlay_ok: bool = False, settle: float | None = None,
                 handoff: bool = False) -> dict:
        """Walk to (x, z) along a route over the field's walkmesh that keeps out of ``avoid``.

        ``overlay_ok`` is :meth:`wait_control`'s: start the walk under an async hint window he can walk with.
        ``settle`` is its too: how long control must hold before the walk starts (None: SETTLE; 0: walk on the first
        sample with control -- a driver that must leave at once, research/o2_design.md H1).

        ``handoff`` (opt-in; research/o2_design.md H1): when control goes away mid-walk (a step, a probe, a wait, the
        facing step) or the field changes, return AT ONCE -- no wait for the landing, for control to come back, or for
        the destination to become playable (:meth:`_await_landing` is not called): ``landed`` is the new id if the field
        has already changed, else None, and ``handoff`` True. The caller judges the crossing, and sits through any
        arrival scene, itself. Off, the landing is waited for as ever.

        Always, handoff or not: ``lost`` is ``{"frame", "field", "x", "z", "control"}`` of the FIRST state any read of
        the call returned with control gone, once control was held at its start (the loss probe, :meth:`_observe`) --
        where he stood when a door's ExitField, a walk-in trigger or a scene took control -- or None when control never
        went.

        ``avoid`` is a list of polygons (world ``[x, z]`` corners -- a field's gateway zones as
        ``eventscan.scan_gateways`` decodes them); the route stays ``margin`` clear of each, except a
        region the player is standing in or beside (:func:`ff9mapkit.content.pathfind.route_avoiding`).
        ``walkmesh`` defaults to the install's for the CURRENT field (a fork passes its own);
        ``prior`` to :meth:`key_prior` of it (``None`` = calibrate blind, which refuses -- raises --
        within a probe's reach of any ``avoid`` region; or pass a basis).

        In order: wait for settled control (an arrival walk-in is not a place to probe from);
        calibrate CLEAR of ``avoid`` (:meth:`_calibrate_clear_of`); plan from where that left him; walk
        the route in chunks with ``walk_to(strict=False, halt_on_transition=True)``, replanning from a
        stall up to ROUTE_REPLANS times. The instant control goes away -- a probe or a step fired a
        trigger -- it stops pressing and reports where that led.

        Every plan starts where he STANDS, even nearer a wall than the controller radius the route keeps --
        a scene can hand control back there (stock 352's wake: 22.8u off a closed strip on his floor, where a
        plan that treated the start like any other cell could not take a step): it steps straight onto a clear
        spot, as a start always could, or walks OUT of that band gaining clearance, never deeper and never along
        the wall -- never through a wall either way (route_avoiding ``leave_wall``). The engine pushes him out
        onto the radius line on his first moving frame, off the planned leg; the walk goes on from there.

        ``unstick`` (opt-in) is for a LIVE room -- people walking about, scripts that hold movement.
        The router knows walls and zones, not bodies, and the agent publishes nothing that tells a
        movement freeze with control held (the script's pad mask, EventInput.IsMovementControl) from a
        body in the way, so MOVEMENT decides, rung by rung (:meth:`_unstick_leg`). A chunk that stalls
        with control held is not a failure yet. WAIT ROUTE_WAIT_SECONDS and walk it again, ROUTE_WAITS
        times (ROUTE_WAIT_BUDGET per call): a freeze, or someone walking through, clears on its own.
        Still stuck: PUSH -- one unbroken hold into whoever stands there, long enough for the engine
        to let him through anyone without object flag 16 (ROUTE_PUSH_LOCK_CALLS), pressed only once a
        one-tick walked probe shows he really is stuck (an overshoot or a slide is not). Still stuck: an
        UNSEEN BLOCKER -- someone he cannot pass -- stands just ahead; it goes in as a point obstacle
        OBSTACLE_R_W (the collision distance) ahead of him along the axis he was pressing
        (:meth:`_blocker_ahead`), and the route is replanned round it, at most ROUTE_BLOCKERS times,
        by the same route_avoiding, so no replan ever enters an ``avoid`` zone. Each replan presses a
        way the blockers before it left open. If he never moves again after the first blocker went in
        -- every replan stalled on the spot, or this call's own blockers leave no way at all -- nothing
        tells a hold on movement from bodies on every side: ``frozen``, and this call's blockers are
        withdrawn as the misreadings they may be. If he DID move, and then the blockers seal the way,
        that is ``blocked``; its blockers are withdrawn too, so a phantom never outlives the call that
        could not use it. A blocker kept is remembered on this field VISIT for ROUTE_BLOCKER_TTL (a
        heuristic: people walk off) and dropped the moment a published sample shows another field or
        control gone (:meth:`_observe`); see :meth:`_plan_round` for the ones he has walked through.
        Walks under ``unstick`` pass ``slides`` to walk_to: sliding round someone is not a bad basis.

        ``smooth`` (opt-in) walks each planned leg WHOLE (:meth:`_route_legs`) instead of in chunks of
        one-axis walk_to bursts with a settle between each -- the choppy walk: every hold is one continuous
        press toward the leg's waypoint, two directions at once where the leg runs diagonal on the calibrated
        basis, re-aimed only when it ends (:meth:`_walk_leg`). The no-zone guarantee is kept per hold, not by
        chunk length: a hold is only as long as the straight line it covers, movement tail included, stays
        clear of every ``avoid`` region by the calibration probe's own rule -- and every line within the
        basis's heading error of it (:meth:`_heading_spread`: the calibrated direction is a measurement) --
        and its end stays within the chunked walk's own drift of the leg still to walk (:meth:`_plan_hold`).
        The stall, wait, push and blocker machinery runs on top unchanged; under it a push insists along the
        direction last held, only as far as that fan is clear too (:meth:`_push_through`), and a blocker goes
        ahead along it. A spot from which no hold keeps those rules is ``boxed``: nothing is pressed, and it is
        not a stall -- no wait, push or blocker (none can change it), no ``frozen``. Without ``smooth``
        walk_to is untouched, and so is every caller of it.

        ``zone`` (smooth only -- it raises without; the polygon the goal lies in, as route_cross passes it)
        makes the last leg FINISH ON IT: standing in it is arrival, and a walk that stops within one walk
        frame of the goal but still outside presses on into it (:meth:`_walk_leg`); ``reached`` then also
        counts standing in it. Under ``npcs`` the finish waits on walkers as the rest of the walk does -- but only on
        walkers that are the cause: ones standing in the way to a spot of the zone he could get into with every walker
        gone (:meth:`_short_of_zone`), waited on, and stepped away from when held on him, within the walk's
        ROUTE_WALKER_BUDGET_SECONDS, never taken for the door -- and a walk the finish ends OUTSIDE the zone says what
        it found holding him there (``held_by``, ``pinned``: its own judgement, recorded as it was made).

        ``face`` (opt-in: None, the default, faces nothing) is a door stock's FACING GATE keeps: its region, world
        ``[x, z]`` corners, the ENGINE's polygon in the engine's order -- the region's first edge first, every point
        (scan_gateways' ``region``; its ``zone`` for a 3- or 4-point one) -- and ``face_window`` its gate's compare
        constants (scan_gateways' ``face_gate``; None: the stock (48, 208)). Pass it for a GATED door only: one with no
        gate fires the first tick he stands in it with control, so one still shut is shut, and a press toward it
        would only walk him about for nothing (route_cross passes it on only for a ``gate``). When the walk ends
        standing IN that region (IsInQuad) with control and nothing fired, it ends with a step that turns him to face
        the door (:meth:`_face_the_door`): on an engine that publishes the facing (memoria-patch s90), a turn IN PLACE
        judged on the facing byte the engine reports once the field has judged it (:meth:`_turn_to_the_door`) -- he
        does not move, so nothing is left, entered or neared; on one that cannot, a walked press planned to leave him
        facing it -- never carrying him out of the region before the call that faces it, and never, its tail and a
        slide along a wall included, into another zone or at an object. A walk that ended ``frozen`` is not turned: a
        hold on movement holds the turn too.

        ``npcs`` (opt-in; it implies ``unstick``) plans round the field's OTHER ACTORS as the engine publishes
        them (memoria-patch s89, :attr:`State.objects`) instead of finding them by walking into them -- on a
        tight map a solid one is a true movement lock. Every object that collides with him (``coll``, standing
        within NPC_DY_BAND in y of a floor under it -- where the walk can meet it, on whatever level the route
        climbs to) is a disc of its published ``r`` in the same A* the zones are kept out of, ROUTE_BODY_MARGIN
        wider; one with a contact function is also a TRIGGER disc of its ``range_r`` (its ``talk_r`` where
        larger and it talks too), kept out of like a zone, ``margin`` wide: a Range the walk did not choose can
        warp the run or start a battle (:meth:`_npc_discs`) -- and a calibration probe keeps clear of the
        triggers as it does of the zones (:meth:`_npc_hazards`). The plan gives them up only as far as it must
        (:meth:`_plan_npcs`): the margins first, down to the pads a hold keeps; then a NON-SOLID body is planned
        THROUGH -- a push, the ladder's last rung -- only when no route goes round it, and a trigger radius is
        entered only when no route stays out, one object at a time, never a class at once, and then the record
        says so; a SOLID body never -- solids that seal every way even at the pad are ``blocked``, with nothing
        pressed (waited on only while one of them is walking: then the plan is made again after
        ROUTE_WAIT_SECONDS, within ROUTE_WAIT_BUDGET). The discs bound every hold and every chunk the way the zones
        do, where the objects stand NOW: they are read again after every hold (every chunk, chunked), and one
        that moved onto the path still to walk re-plans from where he stands, at most ROUTE_NPC_REPLANS times a
        call (:meth:`_npc_moved`); a WALKING trigger is held to where it could have walked by the next read, and
        a press that reach refuses is waited for, standing still (:meth:`_outwait_walkers`). A spot where no hold
        keeps the rules only because of WALKING objects -- their going would free a press -- is not ``boxed``: he
        waits for them to walk off -- stepping out of the way of any held on him, which walk on only once he moves --
        and plans again from where a press is free (:meth:`_outwait_box`); only a box the walkers are not the cause
        of (``boxed_by`` "spot"), or one that outlasts that wait ("walkers"), is ``boxed``. A push is never
        pressed into a solid object, nor along a line that meets a kept trigger or solid
        (:meth:`_push_through`); a stall pressed against a published body -- in contact, :meth:`_body_ahead` --
        that the plan did not go round where it stands now replans round it instead of guessing an unseen
        blocker (one it did go round gets the guess: the next plan would only repeat the last), and a walk held
        against one to the end is not ``frozen`` -- that verdict is for what nothing published can explain. When
        control goes away mid-walk inside a trigger's reach, that trigger is named in ``entered`` too
        (:meth:`_npc_fired`). When the engine publishes no
        objects (the key absent: pre-s89) the call is route_to(unstick=True) exactly, and ``npcs`` says
        "cannot"; when it publishes null through ROUTE_NPC_READS samples (it could not say) the walk is that
        same blind one and ``npcs`` says "unknown" -- never a plan that reads the field as empty. A null sample
        mid-walk leaves the last list read standing.

        Returns ``{"from", "landed", "reached", "travelled", "waypoints", "toward", "replans",
        "during", "waits", "cleared", "pushes", "pushed", "blockers", "remembered", "blocked",
        "frozen", "boxed", "boxed_by", "npcs", "avoided", "entered", "through", "sealed", "npc_replans", "npc_waits",
        "box_waits", "box_cleared", "boxers", "held_by", "pinned", "changed_to", "face_gate", "faced", "face_err",
        "face_worst", "face_to", "face_calls", "face_pad", "face_measured", "face_moved", "fps"}``: ``fps`` the
        measured render rate its presses were planned by, as the walk ended (Rate.as_dict: ``fps``, its spread, the
        ticks a frame, the ``source`` -- "default" when nothing was measured yet), so a record read tomorrow says what
        a frame count in it meant; ``landed``
        the field it ended up in (None = still here), ``changed_to`` the one the id first changed to (None: it
        never changed) -- they differ when that room's scene put him straight back (:meth:`expect_field_change`),
        ``landed`` then the origin -- ``reached`` whether it
        stood within ``tolerance`` of the goal (or, given ``zone``, in it: within tolerance is not IN the zone --
        route_cross's ``inside`` says which), ``travelled`` the distance actually covered (summed
        over the walk, not end-to-end), ``waypoints`` the first plan (None = no route exists),
        ``during`` what lost control -- "calibrate" (a probe), "walk" (a step), "wait" (during an
        unstick wait), "push" (during a push), "face" (during the press or turn that faces him to the door), None
        (nothing did). The rest stay zero/empty without
        ``unstick``: ``waits`` taken, the stalls a wait ``cleared``, ``pushes`` pressed and how many
        of them ``pushed`` him through, the ``blockers`` this call placed ([x, z]; ``replans`` counts
        the plans after the first that a stall caused), how many ``remembered`` ones its first plan went
        round, ``blocked`` and ``frozen`` as above; ``boxed`` (smooth only; or, under ``npcs``, a walk whose wait
        for walking triggers, or for walkers boxing him in, ran out) as above, and ``boxed_by`` why: "spot" (no
        press keeps the rules, and no walker's going would change that), "walkers" (the wait for them ran out), None
        (not boxed). Without ``npcs``,
        ``npcs`` is None and the rest empty/zero; with it, ``npcs`` is "listed", "cannot" or "unknown"
        (above), and every object a plan went round -- in the straight line's way, or hugged by the route --
        is in ``avoided``, every trigger radius a plan had to enter (or that reached him as control went) in
        ``entered`` (``kind`` "range" / "talk"), every non-solid body it had to push through in ``through``, and
        the solids that left no way at all in ``sealed``: each ``{"uid", "sid", "kind", "at", "radius", "solid",
        "moving"}``, once per object and kind over the call. ``npc_replans`` counts the plans an object's
        movement caused, ``npc_waits`` the waits a walking trigger's reach cost (ROUTE_WALKER_WAIT_SECONDS each),
        ``box_waits`` the waits (and steps out of the way) that walking objects boxing him in cost, ``box_cleared``
        the boxes they let go of, and ``boxers`` every object that refused the presses of a box walkers were among --
        at the zone's finish, too, every walker it waited on in the way in (:meth:`_outwait_hold`).
        ``held_by`` and ``pinned`` (``zone`` and ``npcs`` only; else None and empty) are the zone's finish's OWN
        verdict on a walk it ended short of the zone -- "outside", or "boxed" there by walkers -- as it judged it where
        it ended (:meth:`_short_of_zone`, never judged again): ``held_by`` "walkers" (walkers stood in the way to a
        spot of the zone he could have got into with them gone: the village, not the door), "bodies" (no such spot --
        bodies that do not walk stand in the way to the one the geometry leaves), None (the spot's geometry, or
        nothing published in the way), ``pinned`` those bodies. Any other end leaves them None and empty.
        ``face_gate`` is the gate the walk was asked to face (``[lo, hi]``, ``face_window`` or the stock one), None when
        it was given no ``face``. ``faced`` is the facing step's verdict (:meth:`_face_the_door`), and
        ``face_measured`` says what it rests on: True, the ENGINE's own report (the closed loop, s90: a turn in place
        whose ``turn_end`` gave the facing byte the gate read, or during which the field changed); False, a PREDICTION
        from the presses that turned him (the open loop: an engine that cannot publish the facing, or a turn refused
        for a reason a press does not share -- ``player.dir`` is PosObj.rot[1], which a field never writes), or a
        closed loop that measured nothing (every turn cut or refused); None with ``faced``. ``faced`` None: no step was
        taken -- no ``face``, he did not stand in its region with control once the walk ended, the door fired while he
        stood there, or the walk ended ``frozen``. True: a press was made that the prediction says leaves him facing
        the door, or a turn the field judged left him facing it (``face_measured``) -- nothing fired after it: the door
        stayed shut with him facing it -- or control went during its presses (``during`` "face"), or during its turns
        and the field then changed (``during`` "face", ``face_measured``). False: he stood inside with control,
        nothing fired, and no press that faces the door kept the rules above -- or the short ones that did ran out
        before the prediction said faced (they were pressed; nothing is scored faced before it says so) -- or no turn
        reached the window within the bound (every pad's measured heading outside it, the turns cut, refused or
        spent; a human at the controls) -- or control went during (or before) its turns and never came back on an
        unchanged field (``during`` "face": no door seen, ``control`` is not proof one fired) -- or he stood in the
        walk's ``zone`` but in the dead middle of the door's region, where the gate never runs. ``face_to`` the point
        the gate takes his bearing to (content.doorface.calc_exit_position: his projection onto the first edge) where
        the step began,
        ``face_pad`` the buttons it pressed or turned ("up+left"), ``face_calls`` the WHOLE MovePC calls it counted
        them for -- read off the published yaw where s90 publishes it (:meth:`_calls_turned`), else Rate.calls_sure at
        the measured rate (a press's fewer where a free press moved him less than they step; a turn's, of the frames
        the engine reported its keys down) -- ``face_worst`` the largest error, in 256ths, the
        step leaves him with where it left him (the prediction's doorface.worst_face_error, within the window's limit
        when ``faced`` is True; measured, the measured error's size), and ``face_err`` the gate's signed error, in
        256ths -- MEASURED (``face_measured``): the facing byte the engine reported at the last turn's end, against
        the engine's exit point from his published position (doorface.gate_value_from_face), None when the door fired
        (no final facing was the gate's to judge); PREDICTED: for the yaw the prediction's CENTRE gives him (the
        engine's formula, doorface.gate_value) -- None when his yaw before the step was unknown (a chunked walk, or
        none of the walk's holds measured), as the step's own bound is then all there is. ``face_moved`` the largest
        distance a turn's ``turn_end`` says it moved him (0 in place; over ROUTE_TURN_MOVED it was judged as the press
        it was), None when no turn ran. Each None when the step made no press or turn. ``lost`` and ``handoff`` as
        above.
        """
        probe = {"live": False, "lost": None}          # armed once control has held (see :meth:`_route_to`)
        outer, self._loss_probe = self._loss_probe, probe
        try:
            record = self._route_to(x, z, avoid=avoid, margin=margin, tolerance=tolerance, walkmesh=walkmesh,
                                    prior=prior, timeout=timeout, unstick=unstick, smooth=smooth, zone=zone,
                                    npcs=npcs, face=face, face_window=face_window, overlay_ok=overlay_ok,
                                    settle=settle, handoff=handoff, probe=probe)
        finally:
            self._loss_probe = outer
        record["lost"] = probe["lost"]
        return record

    def _route_to(self, x: float, z: float, *, avoid, margin, tolerance, walkmesh, prior, timeout, unstick, smooth,
                  zone, npcs, face, face_window, overlay_ok, settle, handoff, probe) -> dict:
        """:meth:`route_to`'s walk, every argument as it documents them; ``probe`` is the call's control-loss probe,
        armed (``live``) the moment control has held at the start."""
        from ff9mapkit.content import pathfind
        if zone is not None and not smooth:
            raise HarnessError(
                "route_to(zone=...) finishes the last leg on the zone, and only the smooth walk does that: pass "
                "smooth=True (route_cross passes its zone on only then). The chunked walk stops within "
                "tolerance of the goal, wherever that leaves him.")
        unstick = unstick or npcs
        margin = pathfind.KEEPOUT_MARGIN_W if margin is None else float(margin)
        st = self._require_field("route_to")
        origin = st.field_id
        polys = [[(float(p[0]), float(p[1])) for p in poly] for poly in avoid]
        zpoly = None if zone is None else [(float(p[0]), float(p[1])) for p in zone]
        fpoly = None if face is None else [(float(p[0]), float(p[1])) for p in face]
        if fpoly is not None and len(fpoly) < 3:
            raise HarnessError(f"route_to(face=...) is a door's region, 3 to 8 corners -- got {face!r}")
        record = {"from": origin, "landed": None, "reached": False, "travelled": 0.0,
                  "toward": [round(x), round(z)], "waypoints": None, "replans": 0, "during": None,
                  "waits": 0, "cleared": 0, "pushes": 0, "pushed": 0, "blockers": [], "remembered": 0,
                  "blocked": False, "frozen": False, "boxed": False, "boxed_by": None,
                  "npcs": None, "avoided": [], "entered": [], "through": [], "sealed": [], "npc_replans": 0,
                  "npc_waits": 0, "box_waits": 0, "box_cleared": 0, "boxers": [], "held_by": None, "pinned": [],
                  "changed_to": None, "face_gate": None, "faced": None, "face_err": None, "face_worst": None,
                  "face_to": None, "face_calls": None, "face_pad": None, "face_measured": None, "face_moved": None,
                  "fps": None, "lost": None, "handoff": False}
        if fpoly is not None:
            from ff9mapkit.content import doorface
            record["face_gate"] = list(doorface.FACE_WINDOW if face_window is None else map(int, face_window))
        self.wait_control(timeout=timeout, overlay_ok=overlay_ok, settle=settle)
        probe["live"] = True                  # control held: from here, the first read without it is where it went
        # the render rate, measured before anything is planned (a wait for it lets the room's walkers walk on, and the
        # plan below reads them after it): every probe, hold, push and facing press is judged at it, and each that
        # cannot be undone asks for it again -- raising, or pressing nothing, if it never came (:meth:`rate`)
        if self._measured_rate() is None:
            self._log(f"  route_to: no MEASURED render rate yet ({self._clock.rate().describe()}): presses are sized "
                      f"at it, and every rule that cannot be undone -- a probe or hold near a zone, a push, a walking "
                      f"trigger's reach -- asks for a measured one again, or refuses")
        wmesh = walkmesh if walkmesh is not None else self._stock_walkmesh(origin)
        if isinstance(prior, str):
            prior = self.key_prior(origin)
        # None: blind to bodies, as unstick is
        watch = self._npc_watch(margin, record, self._floor_heights(wmesh)) if npcs else None
        if watch is not None:
            watch["floor"] = wmesh
        try:
            if origin not in self._axes:     # always the clear-of mode, even with nothing to avoid:
                st = self.state              # (and clear of the published triggers: a probe fires one too)
                hazards = polys + (self._npc_hazards(watch, st) if watch is not None else [])
                self._calibrate_clear_of(origin, hazards, prior, 4)      # its probes watch control
        except ProbeLeftControl as err:
            self._log(f"  route_to: {err}")
            record["during"] = "calibrate"
            self._npc_fired(watch, record, origin)
            record["landed"] = self._landed(origin, timeout, record, handoff)
            record["fps"] = self.rate().as_dict()
            return record
        spread = self._heading_spread(self._axes[origin], prior) if smooth else 0.0
        known = self._visit_blockers(origin) if unstick else []
        fresh: list = []                  # the blockers THIS call placed, exact centres (all also in known)
        walked = [0.0]                    # distance covered, summed over every walk_to of the call
        first = None                      # walked[0] when this call's first blocker went in
        stalled = False
        ended = None                      # "boxed" / "outside": the leg that ended the walk there
        attempts = (self.ROUTE_BLOCKERS if unstick else self.ROUTE_REPLANS) + 1
        attempt = plans = 0               # the plans a stall caused / every plan made
        leg = None                        # the smooth leg walked last: its last hold is where the facing step starts

        def land(during: str, into) -> dict:
            """Control went away ``during`` a step of the walk: the record, with where that led -- the trigger radii
            he stood within reach of named (:meth:`_npc_fired`; ``into``, the zone the walk was sent into, takes
            control itself), the walkers' cost tallied, the landing waited for (:meth:`_await_landing`) -- or, under
            ``handoff``, not (:meth:`_landed`)."""
            record["travelled"] = round(walked[0], 1)
            record["during"] = during
            self._npc_fired(watch, record, origin, into)
            self._npc_tally(record, watch)
            record["landed"] = self._landed(origin, timeout, record, handoff)
            record["fps"] = self.rate().as_dict()
            return record

        while True:
            st = self.state
            here = (st.player_x, st.player_z)
            sealing = []
            if watch is not None:
                wps, sealing = self._plan_npcs(wmesh, st, (x, z), polys, margin, known, fresh, watch, record)
            else:
                wps = (self._plan_round(wmesh, here, (x, z), polys, margin, known, fresh) if unstick
                       else pathfind.route_avoiding(wmesh, here, (x, z), polys, margin, leave_wall=True))
            if wps is None:
                stalled = False
                self._log(f"  route_to: no route on field {origin} from ({here[0]:.0f}, {here[1]:.0f}) "
                          f"to ({x:.0f}, {z:.0f}) clear of {len(polys)} region(s)"
                          + (f" and {len(known)} unseen blocker(s)" if known else ""))
                walking = [d for d in sealing if d["moving"]]
                wait = self._frames_lasting(self.ROUTE_WAIT_SECONDS)
                if (walking and record["waits"] < self.ROUTE_WAIT_BUDGET
                        and self._walkers_let_stand(watch, wait)):
                    # a solid that is WALKING seals the way only until it has walked on: wait for it, then plan
                    # again from where the objects stand then ("wait for it" is the engine's own answer to a walker)
                    record["waits"] += 1
                    self._log(f"  route_to: walking SOLID object(s) {[d['uid'] for d in walking]} seal the way; "
                              f"waiting {wait} frames (wait {record['waits']})")
                    self.wait_frames(wait)
                    st = self.state
                    if st.field_id != origin or not st.control:
                        record["travelled"] = round(walked[0], 1)
                        record["during"] = "wait"
                        self._npc_tally(record, watch)
                        record["landed"] = self._landed(origin, timeout, record, handoff)
                        record["fps"] = self.rate().as_dict()
                        return record
                    continue
                if sealing:
                    # published SOLID bodies leave no way: a real outcome, with nothing to push through -- and this
                    # call's guesses go with it, as they do for any seal
                    self._withdraw(fresh, known)
                    record["blocked"] = True
                    self._npc_note(record["sealed"], sealing)
                    self._log(f"  route_to: SOLID object(s) {[d['uid'] for d in sealing]} seal every way: blocked")
                elif fresh:
                    # this call's own blockers sealed it (_plan_round has already planned without the
                    # older ones). They go -- a phantom never outlives the call that could not use it
                    # -- and whether the way is really shut depends on whether he moved since the first
                    self._withdraw(fresh, known)
                    if walked[0] - first < self.HALF_STEP:
                        record["frozen"], record["blockers"] = True, []
                        self._log("  route_to: and he has not moved since the first of them went in -- a hold "
                                  "on movement, or bodies on every side: not told apart; withdrawn")
                    else:
                        record["blocked"] = True
                break
            if plans == 0:
                record["waypoints"] = [list(w) for w in wps]
                record["remembered"] = len(known)
            plans += 1
            record["replans"] = attempt
            pts = [here] + [(float(a), float(b)) for a, b in wps]
            chunks = (self._route_legs(pts, polys, known, spread=spread, zone=zpoly, floor=wmesh, watch=watch)
                      if smooth else [(cx, cz, tol, None) for cx, cz, tol
                                      in self._route_chunks(pts, polys, self._chunk_blockers(known, watch))])
            stalled = moved = unboxed = False
            for i, (cx, cz, tol, leg) in enumerate(chunks):
                last = i == len(chunks) - 1
                tol = tolerance if last else tol
                got = None
                if watch is not None:
                    watch["path"] = [(c[0], c[1]) for c in chunks[i:]]
                    if leg is None:               # chunked: a WALKING trigger's reach is waited for before a chunk
                        waited = self._outwait_walkers(watch, origin, lambda: self._chunk_clear(cx, cz, watch))
                        got = None if waited == "clear" else ("wait" if waited == "short" else waited)
                if got is None:
                    before = self.state
                    got = self._route_leg(cx, cz, tol, last, origin, walked, slides=unstick, leg=leg)
                    if watch is not None and leg is None and before.player_x is not None:
                        # read to read, beyond what the chunk pressed: what a walking trigger's reach is sized by
                        pressed = self._chunk_frames(((cx - before.player_x) ** 2 + (cz - before.player_z) ** 2) ** 0.5)
                        self._note_lag(watch, self.state.frame - before.frame - pressed)
                if (watch is not None and (got == "stalled" or (got == "arrived" and not last))
                        and self._npc_moved(self.state, watch)):
                    got = "moved"                 # an object moved onto the path still to walk
                if got == "stalled" and unstick:
                    got = self._unstick_leg(cx, cz, tol, last, origin, walked, record, leg=leg, watch=watch)
                if got in ("walk", "wait", "push"):
                    return land(got, zpoly)
                if got == "boxed":
                    record["boxed"] = True        # no press keeps the rules: a replan from here plans the same
                    record["boxed_by"] = (watch or {}).get("boxed_by") or "spot"
                    ended = got
                    break
                if got == "outside":
                    ended = got
                    break                         # the zone's finish ended short of it, nothing further to press
                if got in ("stalled", "moved", "unboxed"):
                    stalled, moved, unboxed = got == "stalled", got == "moved", got == "unboxed"
                    break
            if moved:
                record["npc_replans"] += 1
                watch["moves"] = record["npc_replans"]
                st = self.state
                self._log(f"  route_to: an object moved onto the path ahead of ({st.player_x:.0f}, "
                          f"{st.player_z:.0f}); planning again from here (movement re-plan {record['npc_replans']} "
                          f"of at most {self.ROUTE_NPC_REPLANS})")
                continue
            if unboxed:
                # the walkers that boxed him in let a press through: the plan he walked went round where they stood
                # before they walked onto him -- plan again round where they stand now
                st = self.state
                self._log(f"  route_to: the walkers that boxed him in let a press through at ({st.player_x:.0f}, "
                          f"{st.player_z:.0f}); planning again from here (box {watch['box_cleared']} of at most "
                          f"{self.ROUTE_BOX_REPLANS} re-planned)")
                continue
            st = self.state
            if record["boxed"] or not stalled or attempt == attempts - 1:
                break
            attempt += 1
            if not unstick:
                self._log(f"  route_to: stalled at ({st.player_x:.0f}, {st.player_z:.0f}); replanning")
                continue
            first = walked[0] if first is None else first
            if watch is not None:
                body = self._body_ahead(st, self._press_dir(origin, (st.player_x, st.player_z), (cx, cz), leg), watch)
                if body is not None and self._npc_shifted(body, watch):
                    # pressed against a body the engine publishes, which the plan did not go round where it stands
                    # now: the next plan does, no guess needed. One it already went round, unmoved, it would plan
                    # round the same way again -- that stall is something the walkmesh does not show, and gets the
                    # unseen blocker below, as the blind walk would
                    self._log(f"  route_to: stuck at ({st.player_x:.0f}, {st.player_z:.0f}) against object "
                              f"{body['uid']} ({'solid' if body['solid'] else 'non-solid'}) at ({body['x']:.0f}, "
                              f"{body['z']:.0f}); replanning round where it stands")
                    continue
            body = self._blocker_ahead(origin, (st.player_x, st.player_z), (cx, cz), leg)
            known.append(body)
            fresh.append(body)
            self._blocker_at[body] = time.time()
            record["blockers"].append([round(body[0]), round(body[1])])
            self._log(f"  route_to: stuck at ({st.player_x:.0f}, {st.player_z:.0f}) with control held "
                      f"after {record['waits']} wait(s) and {record['pushes']} push(es): an unseen blocker "
                      f"at ({body[0]:.0f}, {body[1]:.0f}); replanning round it")
        against = None
        if stalled and first is not None and walked[0] - first < self.HALF_STEP and watch is not None:
            # with the objects published, a body he is held against is told apart from a hold on movement
            against = self._body_ahead(st, self._press_dir(origin, (st.player_x, st.player_z), (cx, cz), leg), watch)
            if against is not None:
                self._log(f"  route_to: held at ({st.player_x:.0f}, {st.player_z:.0f}) against object "
                          f"{against['uid']} at ({against['x']:.0f}, {against['z']:.0f}) -- a body, not a hold on "
                          f"movement; stopping")
        if stalled and first is not None and walked[0] - first < self.HALF_STEP and against is None:
            # Every replan since the first blocker -- each pressing a way the blockers before it left
            # open -- ended exactly where he stood. Bodies do not do that; a hold on MOVEMENT does (a
            # freeze that outlasted every wait), or walls and bodies on every side. The blockers were
            # misreadings of it: withdrawn, from the record and from the visit.
            self._withdraw(fresh, known)
            record["blockers"] = []
            record["frozen"] = True
            self._log(f"  route_to: did not move at all from ({st.player_x:.0f}, {st.player_z:.0f}) through "
                      f"{record['waits']} wait(s), {record['pushes']} push(es) and {len(fresh)} replan(s) in "
                      f"other directions -- movement is held (or he is boxed in); stopping")
        if fpoly is not None and not record["frozen"]:
            # the walk is over; standing IN a gated door's region with nothing fired, only facing it opens it
            turn = {"hazards": polys, "spread": self._heading_spread(self._axes[origin], prior), "watch": watch,
                    "floor": wmesh}
            if self._face_the_door(fpoly, record, origin, walked, turn, self._held_yaw(leg), record["face_gate"],
                                   zpoly, timeout=timeout) is not None:
                # control went during a facing press: the door fired, or a trigger the press met -- never told apart
                # from here, so every trigger he stands within reach of is named, in the door's region or not
                return land("face", None)
        st = self.state
        record["travelled"] = round(walked[0], 1)
        self._npc_tally(record, watch)
        record["reached"] = (st.field_id == origin and st.player_x is not None
                             and (((st.player_x - x) ** 2 + (st.player_z - z) ** 2) ** 0.5 <= tolerance
                                  or (zpoly is not None and pathfind.poly_gap(st.player_x, st.player_z, zpoly) < 0)))
        held = (watch or {}).get("held") if zpoly is not None and ended is not None else None
        if held is not None:
            # the zone's finish ended the walk short of it: what it judged holding him there, as it judged it (never
            # judged again here -- a second look from where the record is written is a second verdict)
            record["held_by"] = held["by"]
            self._npc_note(record["pinned"], held["who"])
            if held["who"]:
                self._log(f"  route_to: ended at ({st.player_x:.0f}, {st.player_z:.0f}) outside the zone, held short of "
                          f"it by {held['by']} {[d['uid'] for d in held['who']]}")
        record["fps"] = self.rate().as_dict()
        return record

    def _route_leg(self, cx: float, cz: float, tol: float, last: bool, origin: int, walked: list,
                   slides: bool = False, leg: dict | None = None) -> str:
        """walk_to one chunk end of a route -- or, given a smooth ``leg`` (:meth:`_route_legs`), walk to its
        waypoint in holds (:meth:`_walk_leg`); adds the distance covered to ``walked[0]``. Returns "arrived",
        "stalled", "boxed" (smooth only: nothing may be pressed from where he stands -- not a stall), "outside" (smooth,
        the zone's finish: within tolerance of the goal, outside the zone, nothing further to press -- the walk's end,
        not a stall), "moved"
        (smooth, route_to(npcs=True): an object moved onto the path ahead -- plan again), "unboxed" (smooth,
        route_to(npcs=True): walkers that boxed him in have let a press through -- plan again), or "walk" when control
        went away (a step fired a trigger, or the field changed).
        ``slides`` is walk_to's: a slide round someone ends the walk as a stall instead of raising.

        A chunk end missed by less than ROUTE_WAYPOINT_TOLERANCE is a near miss, not a stall: a tight
        chunk tolerance can be overshot by one frame's tail, and replanning from right beside the line
        would only plan the same line again. The LAST chunk (the goal) has no such slack."""
        before = self.state
        if leg is None:
            arrived = self.walk_to(cx, cz, tolerance=tol, strict=False, halt_on_transition=True, slides=slides)
            outcome = "arrived" if arrived else "short"
        else:
            outcome = self._walk_leg(cx, cz, tol, leg, slides)
            arrived = outcome == "arrived"
        after = self.state
        if after.field_id == origin and None not in (before.player_x, after.player_x):
            walked[0] += ((after.player_x - before.player_x) ** 2 + (after.player_z - before.player_z) ** 2) ** 0.5
        if after.field_id != origin or not after.control:
            return "walk"
        if outcome in ("boxed", "moved", "unboxed", "outside"):
            return outcome
        if arrived or (not last and ((after.player_x - cx) ** 2 + (after.player_z - cz) ** 2) ** 0.5
                       <= self.ROUTE_WAYPOINT_TOLERANCE):
            return "arrived"
        return "stalled"

    def _outwait(self, cx: float, cz: float, tol: float, last: bool, origin: int, walked: list,
                 record: dict, leg: dict | None = None, watch: dict | None = None) -> str:
        """route_to(unstick=True) at a stall with control held: WAIT ROUTE_WAIT_SECONDS (the frames sure to last it
        at the measured rate, :meth:`_frames_lasting`), then walk the same chunk (or smooth ``leg``) again --
        ROUTE_WAITS times, and never past the call's ROUTE_WAIT_BUDGET.
        Counts ``record["waits"]`` and, for a wait after which the chunk was reached, ``record["cleared"]``.
        Returns what the last :meth:`_route_leg` did ("boxed" included: that is not waited on again), or "wait"
        when control went away during a wait. Under route_to(npcs=True)'s ``watch`` a wait a WALKING trigger could
        reach him in is not stood through (:meth:`_walkers_let_stand`): the stall goes on up the ladder instead."""
        got = "stalled"
        for _ in range(self.ROUTE_WAITS):
            if record["waits"] >= self.ROUTE_WAIT_BUDGET:
                break
            wait = self._frames_lasting(self.ROUTE_WAIT_SECONDS)
            if not self._walkers_let_stand(watch, wait):
                self._log(f"  route_to: not waiting {wait} frames here: a walking trigger could reach him meanwhile")
                break
            record["waits"] += 1
            self.wait_frames(wait)
            st = self.state
            if st.field_id != origin or not st.control:
                return "wait"
            got = self._route_leg(cx, cz, tol, last, origin, walked, slides=True, leg=leg)
            if got == "arrived":
                record["cleared"] += 1
                self._log(f"  route_to: moving again after a wait (stall {record['cleared']} cleared)")
            if got != "stalled":
                return got
        return got

    def _unstick_leg(self, cx: float, cz: float, tol: float, last: bool, origin: int, walked: list,
                     record: dict, leg: dict | None = None, watch: dict | None = None) -> str:
        """route_to(unstick=True) at a stall with control held, rung by rung: the waits (:meth:`_outwait`),
        then a push (:meth:`_push_through`; given route_to(npcs=True)'s ``watch``, never into a solid object)
        and the chunk (or smooth ``leg``) walked again after it. The
        waits go FIRST because a push is one long blind hold: a freeze or a walker that clears in the middle
        of it lets him run the rest. Returns "arrived", "stalled" (still stuck -- route_to places a blocker),
        "boxed" (a smooth leg with no press that keeps the rules: nothing further is tried), "outside" (the zone's
        finish ended short of it with nothing further to press: the walk's end), "moved" (a smooth
        leg under a ``watch`` saw an object move onto the path), "unboxed" (walkers that boxed a smooth leg in let a
        press through: plan again), or "walk" / "wait" / "push" when control went away."""
        got = self._outwait(cx, cz, tol, last, origin, walked, record, leg, watch)
        if got != "stalled":
            return got
        pushed = self._push_through(cx, cz, origin, walked, record, leg, watch)
        if pushed in ("push", "stuck"):
            return "push" if pushed == "push" else "stalled"
        return self._route_leg(cx, cz, tol, last, origin, walked, slides=True, leg=leg)

    def _push_through(self, cx: float, cz: float, origin: int, walked: list, record: dict,
                      leg: dict | None = None, watch: dict | None = None) -> str:
        """Hold toward the chunk end ``(cx, cz)`` UNBROKEN for the frames sure to make ROUTE_PUSH_LOCK_CALLS run
        calls plus what the chunk still needs along the axis pressed -- the engine's pass-through for anyone
        without object flag 16 (see ROUTE_PUSH_LOCK_CALLS). Counts ``record["pushes"]`` / ``["pushed"]``,
        never past ROUTE_PUSH_BUDGET; adds what he covered to ``walked[0]``. Returns "pushed" (he went
        through), "free" (he was not stuck, so nothing was pushed), "stuck", or "push" when control
        went away.

        ALL OF IT AT A MEASURED RATE (:meth:`rate` ``require=True``): the lock is counted in whole run ticks
        (Rate.frames_for_ticks), every line judged at the most the frames can carry him (Rate.reach), and the
        rest sized at the average -- a push sized in frames at 30u a frame ran 180-450u past the line it checked
        at 31 fps, and at 120 fps held too few calls ever to open the lock.

        A ONE-TICK PROBE FIRST, at walk speed (the fewest frames sure of a tick: two at 60 fps): a push that
        meets nobody is a blind run of the whole hold, and walk_to also stops on an overshoot, a slide or
        max_bursts, none of them a body. Only a probe that moved him under a unit -- walk_to's own stall test --
        earns the push.

        Given a smooth ``leg`` it insists along the line the leg last HELD (``leg["pressed"]``: both
        buttons of a diagonal -- the line he stopped on), not one axis toward the chunk end. And the whole
        line is checked first, because a push runs blind for all of it once whoever stood there moves: lock,
        press and movement tail must pass :meth:`_probe_is_clear` of the leg's avoided regions, from where he
        stands, over the leg's heading ``spread``. The press after the lock shrinks to fit (never under 3
        frames); a push that cannot fit is not pressed ("stuck"). Both presses go to the movement cross-check
        (:meth:`_check_movement`).

        Given route_to(npcs=True)'s ``watch`` it is not pressed at all while a SOLID published object stands
        against him along that line (:meth:`_body_ahead`) -- the engine never lets him through one, so the hold
        would only wait out a lock that cannot open -- and the line, chunked or smooth, must also keep clear of
        every kept trigger and solid object (:meth:`_probe_is_clear` ``discs``): a push runs blind once the lock
        opens, and must not carry him on into a contact script beyond whoever he pushed through."""
        import math
        if record["pushes"] >= self.ROUTE_PUSH_BUDGET:
            return "stuck"
        rate = self.rate(require=True)          # the lock must be SURE and the line judged at its reach
        st = self.state
        dx, dz = cx - st.player_x, cz - st.player_z
        # the whole push at the gait he truly holds: a run -- or a walk, where the field inhibits running (:meth:`_gait`),
        # whose lock counted in run ticks (14) would run 14 calls and never open, and whose tail sized at a run's
        # speed would leave him inside whoever he pushed through
        gait = self._gait("run")
        lock = rate.frames_for_calls(self.ROUTE_PUSH_LOCK_CALLS, gait)
        if leg is None:
            button, need, axis, sign = _press_axis(self._axes[origin], dx, dz)
            buttons, u = (button,), (axis[0] * sign, axis[1] * sign)
        else:
            if leg["pressed"] is None:
                leg["pressed"] = max(_eight_way(self._axes[origin]), key=lambda p: p[1][0] * dx + p[1][1] * dz)
            buttons, u = leg["pressed"]
            need = max(0.0, u[0] * dx + u[1] * dz)
        tail = max(3, min(rate.frames_for(self.ROUTE_CHUNK_MAX, gait), rate.frames_for(need, gait)))
        hazards, spread = (leg["hazards"], leg["spread"]) if leg is not None else ((), 0.0)
        discs = [] if watch is None else [d for d in watch["discs"] if d["kind"] == "trigger" or d["solid"]]
        judged = leg is not None or watch is not None          # the chunked push, blind, is judged only then
        if watch is not None:
            solid = self._body_ahead(st, u, watch, solid=True)
            if solid is not None:
                self._log(f"  route_to: SOLID object {solid['uid']} at ({solid['x']:.0f}, {solid['z']:.0f}) stands "
                          f"against him along {'+'.join(buttons)}: never pushed")
                return "stuck"

        movers = [] if watch is None else [d for d in watch["discs"] if d["moving"] and d["kind"] == "trigger"]
        lag = self._walker_lag(watch)

        def fit(tail: int) -> int:
            """The longest press after the lock, up to ``tail``, whose whole push line is clear; 0 = none -- of a
            WALKING trigger by the most it can walk while the whole push runs (he may stand the lock out anywhere
            on the line)."""
            from ff9mapkit.scene import routes
            here = (self.state.player_x, self.state.player_z)

            def clear(n: int) -> bool:
                reach = rate.reach(lock + n, gait)
                end = (here[0] + u[0] * reach, here[1] + u[1] * reach)
                return (self._probe_is_clear(here, u, reach, hazards, spread, discs=discs)
                        and all(routes.seg_dist_xz(d["x"], d["z"], here, end) - d["R"] - d["pad"]
                                >= d["speed"] * (lock + n + lag) for d in movers))
            while tail >= 3 and not clear(tail):
                tail -= 1
            return tail if tail >= 3 else 0

        if judged and not fit(tail):
            self._log(f"  route_to: no push along {'+'.join(buttons)} from ({st.player_x:.0f}, {st.player_z:.0f}) "
                      f"keeps clear of the avoided regions{' and objects' if discs else ''}; not pressed")
            return "stuck"
        probe = self._least_frames(rate)
        moved = self._pressed(origin, walked, f"hold cancel {probe}", *[f"hold {b} {probe}" for b in buttons],
                              f"wait {probe + 4}")
        self._check_movement(moved, probe, "walk", rate, what="a push probe", span=self._press_span)
        if moved is None:
            return "push"
        if moved >= 1.0:
            return "free"
        if judged:
            tail = fit(tail)                          # judged again from where the probe left him
            if not tail:
                return "stuck"
        frames = lock + tail
        record["pushes"] += 1
        moved = self._pressed(origin, walked, *[f"hold {b} {frames}" for b in buttons], f"wait {frames + 4}")
        self._check_movement(moved, frames, gait, rate, what="a push", span=self._press_span)
        if moved is None:
            return "push"
        if moved < self.HALF_STEP:
            return "stuck"
        record["pushed"] += 1
        self._log(f"  route_to: one unbroken {frames}-frame hold {'+'.join(buttons)} took him {moved:.0f}u "
                  f"through whoever stood there (push {record['pushes']})")
        return "pushed"

    def _pressed(self, origin: int, walked: list, *steps: str) -> float | None:
        """Send ``steps``, settle, and add the displacement to ``walked[0]``: how far he went, or None when
        the field changed or control went away."""
        before = self.state
        self.send(*steps)
        after = self.settle()
        self._press_span = (before.frame, after.frame)      # what the movement cross-check times it by
        if after.field_id != origin or None in (before.player_x, after.player_x):
            return None
        moved = ((after.player_x - before.player_x) ** 2 + (after.player_z - before.player_z) ** 2) ** 0.5
        walked[0] += moved
        return moved if after.control else None

    def _withdraw(self, fresh: list, known: list) -> None:
        """Take this call's blockers ``fresh`` back out of the visit's ``known``."""
        for body in fresh:
            if body in known:
                known.remove(body)
            self._blocker_at.pop(body, None)

    def _blocker_ahead(self, field: int, here, toward, leg: dict | None = None) -> tuple[float, float]:
        """Where the body he stopped against stands: OBSTACLE_R_W (+1, so he is not inside it) from
        ``here`` along the direction he was PRESSING (:meth:`_press_dir`). A press that meets a body off its
        line does not stop him: the engine pushes him back out along the line from its centre and he slides
        round it (FieldMapActorController.cs:779-791). A dead stop means the body is on the line pressed. (Two
        bodies, or a body and a wall, can still stop him off that line; the replan then stalls again
        and the next blocker goes where that stall says.)"""
        from ff9mapkit.content import pathfind
        u = self._press_dir(field, here, toward, leg)
        r = pathfind.OBSTACLE_R_W + 1.0
        return (here[0] + u[0] * r, here[1] + u[1] * r)

    def _press_dir(self, field: int, here, toward, leg: dict | None = None) -> tuple[float, float]:
        """The world direction a stalled walk was pressing: walk_to's toward the chunk end ``toward`` -- one
        calibrated axis, not the leg's diagonal -- or, on a smooth ``leg``, the direction its last hold pressed
        (``leg["pressed"]``, a diagonal too)."""
        if leg is not None and leg["pressed"] is not None:
            return leg["pressed"][1]
        _button, _need, axis, sign = _press_axis(self._axes[field], toward[0] - here[0], toward[1] - here[1])
        return (axis[0] * sign, axis[1] * sign)

    def _visit_blockers(self, field: int) -> list:
        """The unseen blockers remembered on this visit to ``field`` -- the live list route_to adds to --
        less any placed more than ROUTE_BLOCKER_TTL ago. A different field starts a new visit (and
        :meth:`_observe` empties it the moment one ends)."""
        if self._blockers[0] != field:
            self._blockers = (field, [])
            self._blocker_at = {}
        known = self._blockers[1]
        now = time.time()
        for body in [b for b in known if now - self._blocker_at.get(b, now) > self.ROUTE_BLOCKER_TTL]:
            known.remove(body)
            self._blocker_at.pop(body, None)
        return known

    def _plan_round(self, wmesh, here, goal, polys, margin, known: list, fresh: list, discs=(), memo=None):
        """:func:`~ff9mapkit.content.pathfind.route_avoiding` round the visit's unseen blockers ``known``
        (updated in place; ``fresh`` = the ones this call placed), still clear of every ``polys`` zone -- and
        of ``discs``, ``(x, z, r)`` obstacles each kept its own ``r`` clear (route_to(npcs=True)'s published
        objects, :meth:`_plan_npcs`), which this never drops. ``memo`` is route_avoiding's: one per start, shared
        by every plan a caller makes from there. Planned from where he stands, so ``leave_wall``: a start nearer
        a wall than the controller radius gets out of that band first (:meth:`route_to`).

        A blocker he STANDS INSIDE is not there any more -- he could not stand in a body -- and is
        dropped. When the OLDER ones seal the way they may have walked off, so the plan is made again
        from this call's own evidence alone, and they are dropped if that finds a way (if they are
        still there the walk stalls on them and places them afresh)."""
        from ff9mapkit.content import pathfind
        inside = (pathfind.OBSTACLE_R_W - 1.0) ** 2
        for b in [b for b in known if (here[0] - b[0]) ** 2 + (here[1] - b[1]) ** 2 < inside]:
            known.remove(b)
            self._blocker_at.pop(b, None)
            if b in fresh:
                fresh.remove(b)
        wps = pathfind.route_avoiding(wmesh, here, goal, polys, margin, obstacles=list(known) + list(discs),
                                      memo=memo, leave_wall=True)
        older = [b for b in known if b not in fresh]
        if wps is None and older:
            wps = pathfind.route_avoiding(wmesh, here, goal, polys, margin, obstacles=list(fresh) + list(discs),
                                          memo=memo, leave_wall=True)
            if wps is not None:
                self._log(f"  route_to: {len(older)} remembered blocker(s) sealed the way; planned without them")
                for b in older:
                    known.remove(b)
                    self._blocker_at.pop(b, None)
        return wps

    # -- route_to(npcs=True): the field's published objects (memoria-patch s89) -------------------
    def _npc_watch(self, margin: float, record: dict, heights=None) -> dict | None:
        """route_to(npcs=True)'s view of the published objects for one call, or None -- with ``record["npcs"]``
        saying why -- when there is nothing to plan on: "cannot" (the key absent: an engine without s89) or
        "unknown" (null through ROUTE_NPC_READS samples, ROUTE_NPC_READ_FRAMES apart: the engine could not
        say). The walk is then route_to(unstick=True)'s, blind to bodies; nothing reads the field as empty.

        The view: ``objs`` (the last list read -- a null sample never replaces it), ``y`` (his), ``margin`` (the
        call's, a trigger's), ``heights`` (:meth:`_floor_heights` of the call's walkmesh -- what the |dy| band of a
        plan is judged by, :meth:`_npc_levels`; None judges it against his y), ``keep`` (the ``(uid, kind)`` discs
        the current plan keeps), ``planned`` (where each object stood when it was made), ``discs`` (the kept discs
        where they stand NOW -- what every hold is bounded by), ``path`` (the walk still ahead), ``moves`` (the
        re-plans movement has caused), ``seen`` / ``last`` / ``speed`` / ``heading`` / ``walked`` (where each object
        was last read, its velocity then, the pace it has been measured walking, the line it walks and whether any
        read published it ``moving``: :meth:`_npc_read`),
        ``floor`` (the call's walkmesh), ``waited`` / ``walker_waits`` (the frames, and the waits,
        walking triggers have cost the call: :meth:`_outwait_walkers`), ``box_waited`` / ``box_waits`` / ``box_cleared``
        / ``boxers`` (the same for walkers that boxed him in, the boxes they let go of, and every object that refused
        the presses of one: :meth:`_outwait_box`), ``boxed_by`` ("walkers" once a wait for walkers has run out: the
        call ends ``boxed``, and by them), ``held`` (the zone's finish's verdict on what keeps him out of the zone,
        :meth:`_short_of_zone` -- the last one it judged by, this hold's; route_to records it when the finish ends the
        walk) and ``lag`` (the most frames seen to pass
        between two reads beyond the ones pressed -- ROUTE_WALKER_LAG_SECONDS' frames until a press measures it:
        :meth:`_walker_clear`)."""
        st = self.state
        for _ in range(self.ROUTE_NPC_READS):
            if st.objects_status != "unknown":
                break
            self.wait_frames(self.ROUTE_NPC_READ_FRAMES)
            st = self.state
        record["npcs"] = st.objects_status
        if st.objects is None:
            self._log("  route_to: npcs asked for, but " + (
                "this engine publishes no objects (pre-s89)" if record["npcs"] == "cannot"
                else "the engine could not list the objects (null)") + ": bodies are found by walking into them")
            return None
        watch = {"objs": st.objects, "y": st.player_y, "margin": float(margin), "heights": heights, "keep": set(),
                 "planned": {}, "discs": [], "path": [], "moves": 0, "seen": {}, "speed": {}, "waited": 0,
                 "walker_waits": 0, "box_waited": 0, "box_waits": 0, "box_cleared": 0, "boxers": [], "boxed_by": None,
                 "held": None, "lag": None}
        self._npc_read(watch, st)
        return watch

    @staticmethod
    def _floor_heights(wmesh):
        """``(x, z) -> [the height of every walkmesh triangle over that point]`` on ``wmesh`` -- what a plan's |dy| band
        is judged by (:meth:`_npc_levels`) -- or None for a mesh with no triangles to read (the band is then judged
        against his y). A :class:`~ff9mapkit.content.pathfind.PlayerWalkmesh` answers for the mesh it views: a
        triangle closed to HIM is still a floor an actor stands on. BgiWalkmesh.height_at's interpolation, over
        every stacked floor rather than the first."""
        mesh = getattr(wmesh, "mesh", wmesh)
        if not all(hasattr(mesh, a) for a in ("tris", "tris_at", "world_verts")):
            return None
        wv = mesh.world_verts()

        def heights(x, z) -> list:
            out = []
            for ti in mesh.tris_at(x, z):
                a, b, c = (wv[k] for k in mesh.tris[ti].vtx)
                den = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
                if den == 0:
                    out.append(float(a[1]))
                    continue
                wa = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / den
                wb = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / den
                out.append(wa * a[1] + wb * b[1] + (1.0 - wa - wb) * c[1])
            return out
        return heights

    def _npc_levels(self, heights, here, y):
        """route_to(npcs=True)'s |dy| judgment for a PLAN: a predicate over a published object -- does it stand within
        NPC_DY_BAND of a floor under it, where the walk can meet it? -- or None when the frame cannot be told from
        where he stands (the band is then judged against his ``y`` now, as the engine judges it at this instant).

        The engine pairs him with an object only while |dy| < 400 (WalkMesh.cs:922), so an object on a level the
        route CLIMBS to is out of the band where he starts and in it where he gets there: judged against his y now,
        it is left out of the plan and of every hold until one hold can carry him into it.

        THE FRAME: the published ``y`` is not the walkmesh's height. In every recorded harness state that stood on a
        stock floor it is the height NEGATED -- ``y + height_at == 0`` exactly, at 105 and at four heights on 1606 --
        but neither sign is assumed: a frame ``y = s * height + c`` counts when it puts HIM on a floor under his own
        feet (``|c|`` under half the band), for either ``s``. Where every floor under him is near height 0 both do,
        and an object is then kept if either puts it on a level -- the conservative side. An object with no floor
        under it is kept (it may stand on a ledge the route passes under)."""
        if y is None:
            return None
        mine = heights(here[0], here[1])
        frames = {(s, float(y) - s * h) for s in (-1.0, 1.0) for h in mine
                  if abs(float(y) - s * h) < self.NPC_DY_BAND / 2}
        if not frames:
            return None

        def level(o) -> bool:
            under = heights(float(o["x"]), float(o["z"]))
            return not under or any(abs(float(o["y"]) - (s * h + c)) < self.NPC_DY_BAND
                                    for s, c in frames for h in under)
        return level

    def _npc_read(self, watch: dict, st: State) -> bool:
        """Take ``st``'s object list into ``watch`` -- ``objs``, his ``y`` -- and how each object has been seen to walk.
        ``speed`` keeps, per uid, the most per frame it covered over two STEADY reads running -- the same direction
        and within a fifth of the same pace, so a straight walk and not a turn or a stop between reads, which averages
        to a crawl (at most two run ticks, RUN_TICK each, a TICK -- the ticks a frame holds at the measured rate,
        :meth:`rate`: 60u a frame at 60 fps, 120 at 30 -- a script placing an actor is not a walk; a cap of 60u a
        frame dropped every walker faster than his run at 31 fps, the Dali children). ``heading`` keeps the direction
        (a unit vector) of the last read in which it covered at least half its likely pace a frame -- half its
        published speed (:meth:`_told_speed`), or else half the most it has been seen to cover: a read across a
        turn keeps the line it was walking, as a patrol turns back along it. ``walked`` keeps every uid any read has
        published ``moving`` (:meth:`_npc_walks`). False, changing nothing, for a sample with no list (null: the
        engine could not say) or no player position."""
        import math
        objs = st.objects
        if objs is None or st.player_x is None:
            return False
        cap = 2.0 * self.RUN_TICK * self.rate().per_frame()      # the fastest walk a frame: two run ticks a tick
        seen, speed = watch.setdefault("seen", {}), watch.setdefault("speed", {})
        heading, last = watch.setdefault("heading", {}), watch.setdefault("last", {})
        walked = watch.setdefault("walked", set())
        for o in objs:
            if o.get("x") is None or o.get("z") is None:
                continue
            uid, at = o.get("uid"), (float(o["x"]), float(o["z"]))
            if o.get("moving"):
                walked.add(uid)
            was = seen.get(uid)
            if was is not None and st.frame > was[2]:
                vel = ((at[0] - was[0]) / (st.frame - was[2]), (at[1] - was[1]) / (st.frame - was[2]))
                v = math.hypot(*vel)
                before = last.get(uid)
                if before is not None and 0.0 < v <= cap:
                    w = math.hypot(*before)
                    if (w > 0.0 and abs(v - w) <= 0.2 * max(v, w)
                            and vel[0] * before[0] + vel[1] * before[1] >= 0.95 * v * w):
                        speed[uid] = max(speed.get(uid, 0.0), v, w)
                last[uid] = vel
                told = self._told_speed(o)
                if 0.0 < v <= cap and v >= (told / 2.0 if told else max(speed.get(uid, 0.0), v)) / 2.0:
                    heading[uid] = (vel[0] / v, vel[1] / v)
            seen[uid] = (at[0], at[1], st.frame)
        watch["objs"], watch["y"] = objs, st.player_y
        return True

    @staticmethod
    def _told_speed(o: dict) -> float | None:
        """The engine's own walk speed for published object ``o``, per call of its walk (one an event tick), where the
        entry says: its ``range_r`` less its ``r`` and 60 (s89: range_r = r + speed + 60). None without a Range."""
        if o.get("range_r") is None or o.get("r") is None:
            return None
        return max(0.0, float(o["range_r"]) - float(o["r"]) - 60.0)

    def _npc_discs(self, objs, here, y, margin: float, heights=None, speeds=None, headings=None) -> list:
        """The obstacles route_to(npcs=True) plans round, from the published ``objs`` (s89), as seen from ``here`` by a
        player at height ``y``. Only objects the engine would pair with him, within NPC_DY_BAND in y (WalkMesh.cs:922):
        given ``heights`` (:meth:`_floor_heights`), of a floor under the object (:meth:`_npc_levels`) -- a plan, and
        every hold and chunk of it, is about where he WILL walk, and a route that climbs meets an object on the level
        it climbs to; without them (or where the frame cannot be told), of his ``y`` now -- the engine's own test at
        this instant, what a live contact check wants.

        A BODY disc for each object that collides with him (``coll``): radius ``R`` its ``r``, the centre
        distance the engine keeps him at. A TRIGGER disc for each with a contact function: radius its
        ``range_r`` -- where CollisionRequest requests its Range every tick he has control -- or its ``talk_r``
        where that is larger and it talks too (the talk search then requests the Range instead, facing it);
        the larger is the one that can fire first. A TALK-ONLY entry (``talk`` without ``range``: 350's Dali
        children) is a body and no trigger: inside its ``talk_r`` the talk search requests its tag-2 Range, which it
        does not have, and its tag-3 talk runs only on a Confirm press, which a routed walk never sends (s89's
        contract) -- its "!" is a prompt, not a reach. Each is ``{"uid", "sid", "kind" ("body" / "trigger"), "via"
        ("body" / "range" / "talk"), "x", "z", "R", "T", "P", "pad", "solid", "moving", "speed", "dir", "shown",
        "inside"}``: ``pad`` what a hold keeps off ``R`` (ROUTE_BODY_PAD / PROBE_HAZARD_PAD), ``T`` the TIGHT radius a
        plan keeps its legs outside at the least -- ``R`` plus that pad -- and ``P`` the one it keeps them outside
        first: ``R`` plus ROUTE_BODY_MARGIN for a body, the call's zone ``margin`` for a trigger (never under ``T``).
        A disc he already stands within ``T`` or ``P`` of has it shrunk to just under his distance, so a route may
        walk out of it and never deeper -- ``inside`` when he is within ``R`` itself (a trigger that has not fired,
        a walker that stopped on him). ``speed`` is how far a frame a WALKING one may come. Where the entry publishes
        the engine's own speed (:meth:`_told_speed`): its walk moves that a call, a call an event tick -- half of it a
        frame at 60 fps, all of it at 30, a quarter at 120 -- but that is a reading of the engine, not a measurement,
        so until ``speeds`` has MEASURED it (:meth:`_npc_read`: the most it covered over two steady reads running) the
        whole published speed is taken a frame (conservative at every rate up to 30 fps's tick a frame), and after, the
        measured pace, never under HALF the published one (60 fps's figure: at 30 the steady reads measure the whole
        call, and at 120 half is twice the truth: conservative both ways). A single read
        cannot measure it: one that spans a turn averages to a crawl, and a walker taken slower than it walks walks
        into him. Where the entry publishes none, the measured pace, never under one walked call a tick
        (STEP_PER_CALL x the ticks a frame holds at :meth:`rate`: 15u a frame at 60 fps, 30 at 30).
        ``dir`` the line ``headings`` last saw it walk along (a unit vector; None: not seen walking)."""
        import math
        level = None if heights is None else self._npc_levels(heights, here, y)
        out = []
        for o in objs:
            if o.get("x") is None or o.get("z") is None:
                continue
            if o.get("y") is not None:
                if level is not None:
                    if not level(o):
                        continue
                elif y is not None and abs(float(o["y"]) - float(y)) >= self.NPC_DY_BAND:
                    continue
            told = self._told_speed(o)                     # the engine's own walk speed, a call (one an event tick)
            steady = (speeds or {}).get(o.get("uid")) or 0.0
            if told:                                       # never under half a call a frame, once steady reads say
                speed = max(steady, told / 2.0) if steady else told
            else:
                speed = max(steady, STEP_PER_CALL * self.rate().per_frame())
            base = {"uid": o.get("uid"), "sid": o.get("sid"), "x": float(o["x"]), "z": float(o["z"]),
                    "solid": bool(o.get("solid")), "moving": bool(o.get("moving")), "shown": o.get("shown"),
                    "speed": speed, "dir": (headings or {}).get(o.get("uid"))}
            if o.get("coll") and o.get("r") is not None:
                r = float(o["r"])
                out.append(dict(base, kind="body", via="body", R=r, T=r + self.ROUTE_BODY_PAD,
                                P=r + self.ROUTE_BODY_MARGIN, pad=self.ROUTE_BODY_PAD))
            radius, via = None, None
            if o.get("range") and o.get("range_r") is not None:
                radius, via = float(o["range_r"]), "range"
            # talk_r reaches only through a Range: a talk-only entry's talk search requests a tag 2 it lacks
            talk = o.get("talk_r") if o.get("range") and o.get("talk") else None
            if talk is not None and float(talk) > (radius or 0.0):
                radius, via = float(talk), "talk"
            if radius is not None:
                out.append(dict(base, kind="trigger", via=via, R=radius, T=radius + self.PROBE_HAZARD_PAD,
                                P=radius + max(float(margin), self.PROBE_HAZARD_PAD), pad=self.PROBE_HAZARD_PAD))
        for d in out:
            dist = math.hypot(here[0] - d["x"], here[1] - d["z"])
            for key in ("T", "P"):
                if dist < d[key]:
                    d[key] = max(0.0, dist - 0.5)
            d["inside"] = dist < d["R"]
        return out

    def _plan_npcs(self, wmesh, st, goal, polys, margin, known: list, fresh: list, watch: dict, record: dict):
        """route_to(npcs=True)'s plan from where ``st`` stands him: :meth:`_plan_round` (walls, the ``polys`` zones,
        the unseen blockers) round the published objects (:meth:`_npc_discs` of the last list read -- ``st``'s own
        when it has one), giving up only as much as it must, in this order:
          0. THE SOLIDS ALONE, each at its tight radius ``T``. A SOLID body is never given up, and every plan below
             keeps a superset of these, so when they leave no route nothing does: ``(None, sealing)`` at once, the
             solids the route round the walls and zones alone passes within ``r`` of (all of them if it passes
             none) -- or ``(None, [])`` when that route does not exist either (no route, as without ``npcs``). Only
             a seal at ``r`` plus the pad a hold keeps is a movement lock: a lane a margin closes is still a lane.
          1. every disc at its plan radius ``P`` -- first with the line each WALKING trigger walks kept out of too
             (ROUTE_WALKER_AHEAD_SECONDS of it either way, at the speed it may walk: a route that stays off a patrol's
             beat where one can); else every disc at ``T`` -- a hold keeps that pad off each, so the route still
             enters nothing, only the slack for the walk's drift is gone. A WALKING trigger (its body too) is no
             obstacle beyond that line: where it stands now it will not be when he gets there, and a detour round it
             only puts a waypoint on its beat. The walk keeps every press and wait clear of where it walks
             (:meth:`_walker_clear`) instead, and it stays in ``watch["discs"]`` for that whatever the plan gave up.
          2. through NON-SOLID bodies with every trigger kept -- a push, the ladder's last rung, pressed only when
             he meets one; else into trigger radii with every body kept; else through the bodies the solids-only
             route crosses and into triggers after that. Each by :meth:`_npc_relax`: one object at a time, never a
             class -- a chest's Range across the only corridor does not let the route through a warp beyond it.
        A plan is taken only when no leg of it enters a disc it kept -- the grid's last hop to the exact goal is
        not checked by the string-pull, so a goal inside one would otherwise pass. Every plan of the call shares one
        memo of the floor's answers (route_avoiding ``memo``): they all start here, on one grid, and those answers
        are the planning's whole cost. Returns ``(waypoints, [])`` or ``(None, sealing)`` -- naming the sealing
        solids in the record is route_to's, which waits for a walking one first. The plan taken goes into ``watch``
        (``keep``, ``planned``, ``discs``) and the record: the kept objects it went round in ``avoided`` (in the
        straight line's way, or hugged by the route), the given-up triggers its legs enter in ``entered``, the
        given-up bodies in ``through``."""
        import math
        from ff9mapkit.scene import routes
        if st.objects is not None:
            self._npc_read(watch, st)
        here = (st.player_x, st.player_z)
        seen = self._npc_discs(watch["objs"], here, watch["y"], margin, watch.get("heights"), watch.get("speed"),
                               watch.get("heading"))
        # a WALKING trigger is no obstacle where it stands now -- it will not be there when he is -- and neither is its
        # body: the plan keeps off the line it walks where it can (``ahead``), and the walk keeps every press and wait
        # clear of where it walks
        walkers = {w["uid"] for w in seen if w["kind"] == "trigger" and w["moving"]}
        walking = [d for d in seen if d["moving"] and d["uid"] in walkers]
        every = [d for d in seen if all(d is not w for w in walking)]
        memo: dict = {}

        def enters(pts, d, radius) -> bool:
            return any(routes.seg_dist_xz(d["x"], d["z"], a, b) < radius - 0.5 for a, b in zip(pts, pts[1:]))

        def line(wps) -> list:
            return [here] + [(float(a), float(b)) for a, b in wps]

        def plan(kept, key="T"):
            wps = self._plan_round(wmesh, here, goal, polys, margin, known, fresh,
                                   discs=[(d["x"], d["z"], d[key]) for d in kept], memo=memo)
            return None if wps is None or any(enters(line(wps), d, min(d["R"], d[key])) for d in kept) else wps

        solids = [d for d in every if d["kind"] == "body" and d["solid"]]
        bodies = [d for d in every if d["kind"] == "body" and not d["solid"]]
        triggers = [d for d in every if d["kind"] == "trigger"]
        base = plan(solids)
        if base is None:
            bare = plan([]) if solids else None
            if bare is None:
                return None, []
            return None, [d for d in solids if enters(line(bare), d, d["R"])] or solids
        ahead = []                           # ROUTE_WALKER_AHEAD_SECONDS of each walking trigger's line, either way
        for d in [w for w in walking if w["kind"] == "trigger"]:
            beat = self._walker_path(d, self._frames_lasting(self.ROUTE_WALKER_AHEAD_SECONDS))
            steps = 0 if beat is None else int(math.dist(*beat) / 2.0 // max(1.0, d["R"] / 2.0))
            for k in [k for j in range(1, steps + 1) for k in (j, -j)]:
                at = (d["x"] + (beat[1][0] - d["x"]) * k / steps, d["z"] + (beat[1][1] - d["z"]) * k / steps)
                r = min(d["P"], max(0.0, math.hypot(here[0] - at[0], here[1] - at[1]) - 0.5))
                ahead.append({"x": at[0], "z": at[1], "R": r, "T": r, "P": r})
        wps, given = (plan(every + ahead, "P") if ahead else None), []
        if wps is None:
            wps = plan(every, "P") if every else base
        if wps is None:
            wps = plan(every) if bodies or triggers else base
        if wps is None and bodies:
            wps, given = self._npc_relax(plan, here, solids + triggers, bodies, None if triggers else base)
        if wps is None and triggers:
            wps, given = self._npc_relax(plan, here, solids + bodies, triggers, None if bodies else base)
        if wps is None:
            crossed = [d for d in bodies if enters(line(base), d, d["T"])]
            wps, given = self._npc_relax(plan, here, solids + [d for d in bodies if all(d is not c for c in crossed)],
                                         triggers, base)
            given = crossed + given
        pts = line(wps)
        kept = [d for d in every if all(d is not g for g in given)]
        watch["keep"] = {(d["uid"], d["kind"]) for d in kept + walking}
        watch["planned"] = {d["uid"]: (d["x"], d["z"]) for d in seen}
        watch["discs"] = kept + walking
        self._npc_note(record["avoided"], [
            d for d in kept if routes.seg_dist_xz(d["x"], d["z"], here, goal) < d["P"]
            or enters(pts, d, d["P"] + self.ROUTE_WAYPOINT_TOLERANCE)])
        entered = [d for d in given if d["kind"] == "trigger" and enters(pts, d, d["R"])]
        through = [d for d in given if d["kind"] == "body" and enters(pts, d, d["R"])]
        self._npc_note(record["entered"], entered)
        self._npc_note(record["through"], through)
        if entered or through:
            self._log(f"  route_to: no route stays clear of every object: this one "
                      + " and ".join(p for p in (
                          f"enters the trigger radius of {[d['uid'] for d in entered]}" if entered else "",
                          f"pushes through non-solid {[d['uid'] for d in through]}" if through else "") if p))
        return wps, []

    @staticmethod
    def _npc_relax(plan, here, fixed: list, pool: list, guide=None):
        """:meth:`_plan_npcs`' way of giving up as little of ``pool`` as it must while keeping every disc of ``fixed``:
        ``(waypoints, given_up)``, or ``(None, [])`` when no route keeps ``fixed`` alone. ``guide`` is that route --
        ``plan(fixed)`` when not given -- and the pool discs it passes inside the tight radius ``T`` of are the ones in
        the way. One: that one. Several: each given up ALONE, the first that routes -- a chest's Range across the only
        corridor does not open the way through an avoidable warp beyond it -- and only when none alone does, every
        one the guide crosses (the guide is then the route: it keeps ``fixed`` and enters no other). ``plan(kept)``
        is :meth:`_plan_npcs`' own: ``kept`` at their tight radius, every leg checked exactly."""
        from ff9mapkit.scene import routes
        guide = plan(fixed) if guide is None else guide
        if guide is None:
            return None, []
        pts = [here] + [(float(a), float(b)) for a, b in guide]
        crossed = [d for d in pool if any(routes.seg_dist_xz(d["x"], d["z"], a, b) < d["T"] - 0.5
                                          for a, b in zip(pts, pts[1:]))]
        if len(crossed) > 1:
            for d in crossed:
                wps = plan(fixed + [p for p in pool if p is not d])
                if wps is not None:
                    return wps, [d]
        return guide, crossed

    def _npc_moved(self, st: State, watch: dict) -> bool:
        """route_to(npcs=True), after every hold (every chunk, walked chunked), every wait for a walker and at every
        stall: read the objects again (:meth:`_npc_read`). The discs every hold keeps clear follow them
        (``watch["discs"]``: the plan's kept ``(uid, kind)`` discs where they stand now, and whole any object the
        plan never saw). True -- plan again from here -- when one of those has moved ROUTE_NPC_MOVED or more since
        the plan (or is new) and now comes within its radius and ``pad`` of the path still to walk
        (``watch["path"]``, from where he stands); never once the call has re-planned for movement
        ROUTE_NPC_REPLANS times, so a walker that keeps crossing the path cannot hold the call. A sample with no
        list (null: the engine could not say) changes nothing -- the last list read stands, and it is never read
        as the objects gone."""
        import math
        from ff9mapkit.scene import routes
        now = self._npc_view(watch, st)
        if now is None:
            return False
        here = (st.player_x, st.player_z)
        if watch["moves"] >= self.ROUTE_NPC_REPLANS:
            return False
        path = [here] + list(watch["path"])
        for d in now:
            was = watch["planned"].get(d["uid"])
            if was is not None and math.hypot(d["x"] - was[0], d["z"] - was[1]) < self.ROUTE_NPC_MOVED:
                continue
            if d["kind"] == "trigger" and d["moving"]:
                continue                          # a walking trigger: the plan never went round where it stood
            if any(routes.seg_dist_xz(d["x"], d["z"], a, b) < d["R"] + d["pad"] for a, b in zip(path, path[1:])):
                return True
        return False

    def _npc_view(self, watch: dict, st: State) -> list | None:
        """Read ``st``'s objects into ``watch`` (:meth:`_npc_read`) and bring the discs every hold keeps clear
        (``watch["discs"]``) to where they stand in it: the plan's kept ``(uid, kind)`` discs, and whole any object the
        plan never saw. None, changing nothing, for a sample with no list."""
        if not self._npc_read(watch, st):
            return None
        watch["discs"] = [d for d in self._npc_discs(watch["objs"], (st.player_x, st.player_z), st.player_y,
                                                     watch["margin"], watch.get("heights"), watch.get("speed"),
                                                     watch.get("heading"))
                          if (d["uid"], d["kind"]) in watch["keep"] or d["uid"] not in watch["planned"]]
        return watch["discs"]

    def _npc_shifted(self, d: dict, watch: dict) -> bool:
        """Would a plan made now go round published object ``d`` any differently from the plan he is walking? Only
        if that plan never saw it, or it has moved ROUTE_NPC_MOVED or more since (``watch["planned"]``); otherwise
        the plan would be made round it the same way again."""
        import math
        was = watch["planned"].get(d["uid"])
        return was is None or math.hypot(d["x"] - was[0], d["z"] - was[1]) >= self.ROUTE_NPC_MOVED

    def _body_ahead(self, st: State, u, watch: dict, *, solid: bool = False) -> dict | None:
        """The published body he stands pressed against along unit ``u``: of every body the last list read holds
        (:meth:`_npc_discs` by the engine's |dy| test where he stands now -- not only the ones a plan kept), the
        nearest he is IN CONTACT with -- his centre within HALF_STEP of its ``r``, where the engine holds it, and
        the body within ROUTE_CONTACT_ANGLE of ``u`` (one met further off the line slides him round it, it does not
        stop him); None when there is none. ``solid``: only a solid one. A body standing clear of him did not stop
        him, however near: laying the stall on it re-plans round a body the plan already went round, and never
        places the blocker the stall is really about -- a wall the walkmesh lacks, beside a villager."""
        import math
        here = (st.player_x, st.player_z)
        cos = math.cos(math.radians(self.ROUTE_CONTACT_ANGLE))
        best = None
        for d in self._npc_discs(watch["objs"], here, st.player_y, watch["margin"]):
            if d["kind"] != "body" or (solid and not d["solid"]):
                continue
            dx, dz = d["x"] - here[0], d["z"] - here[1]
            dist = math.hypot(dx, dz)
            if (dist < d["R"] + self.HALF_STEP and dx * u[0] + dz * u[1] >= cos * dist
                    and (best is None or dist < best[0])):
                best = (dist, d)
        return None if best is None else best[1]

    def _npc_fired(self, watch: dict | None, record: dict, origin: int, zone=None) -> None:
        """route_to(npcs=True), control gone before the walk ended: name in ``record["entered"]`` every published
        trigger he stands within reach of -- a run tick (RUN_TICK) past its radius, by the engine's |dy| test where he
        stands -- while he is still on ``origin`` and not in ``zone`` (the exit he was sent to, which takes control
        itself). The plan kept out of those, so one there is a Range that reached him -- a walker's, or one a walk
        strayed into -- and the record names it rather than leave ``entered`` empty beside a run that was warped."""
        import math
        from ff9mapkit.content import pathfind
        if watch is None:
            return
        st = self.state
        if st.field_id != origin or st.player_x is None:
            return
        here = (st.player_x, st.player_z)
        if zone is not None and pathfind.poly_gap(here[0], here[1], zone) < 0:
            return
        self._npc_read(watch, st)
        hit = [d for d in self._npc_discs(watch["objs"], here, st.player_y, watch["margin"])
               if d["kind"] == "trigger"
               and math.hypot(here[0] - d["x"], here[1] - d["z"]) < d["R"] + self.RUN_TICK]
        if hit:
            self._npc_note(record["entered"], hit)
            self._log(f"  route_to: control went at ({here[0]:.0f}, {here[1]:.0f}) within reach of trigger(s) "
                      f"{[d['uid'] for d in hit]}: a contact script the plan kept out of reached him")

    def _npc_hazards(self, watch: dict, st: State) -> list:
        """The published TRIGGERS as regions a calibration keeps its probes out of (route_to(npcs=True), before the
        first plan): every trigger disc of :meth:`_npc_discs`, at its ``R``, as the regular 16-gon that holds it -- a
        probe that fires one is lost like one that fires a gateway. A BODY is not one: a probe pressed into it costs
        a slide, which calibration's own cross-checks catch as they catch a wall, never a wrong room -- and a
        villager standing by the arrival must not refuse a calibration route_to(unstick=True) makes there."""
        import math
        n = 16
        out = []
        for d in self._npc_discs(watch["objs"], (st.player_x, st.player_z), st.player_y, watch["margin"],
                                 watch.get("heights"), watch.get("speed"), watch.get("heading")):
            k = d["R"] / math.cos(math.pi / n)
            if d["kind"] == "trigger" and k > 0:
                out.append([(d["x"] + k * math.cos(2 * math.pi * i / n), d["z"] + k * math.sin(2 * math.pi * i / n))
                            for i in range(n)])
        return out

    def _walker_clear(self, here, u, reach: float, spread: float, d: dict, pace: float, until: float,
                      stray: float = 0.0, lead: float = 0.0) -> bool:
        """May a press from ``here`` along unit ``u`` -- covering ``reach`` at ``pace`` units a frame, truly heading
        anywhere within ``spread`` (radians) of ``u`` and straying up to ``stray`` off that -- be made beside WALKING
        trigger ``d``, wherever it walks, until the objects are read again ``until`` frames on (the press and
        :meth:`_walker_lag`)?

        WHILE HE MOVES each point of the press is judged at the moment he gets there: ``l`` along it he is at frame
        ``l / pace``, and the nearest the fan's arc at ``l`` comes to ``d`` less that stray, less how far ``d`` can have
        come by then in any direction (its ``speed`` a frame, :meth:`_npc_discs`), must keep ``d["pad"]`` off its
        radius. WHILE HE STANDS at the end, until the read, ``d`` is taken to keep to the LINE it was last seen walking
        along (``dir``) -- either way along it: a patrol turns back down its own path -- give or take ROUTE_WALKER_TURN
        of its speed a frame (:meth:`_walker_path`); one not yet seen walking, in any direction there too. A walker he
        already stands nearer than that pad to may not gain on him at any point either. A disc read where it stood
        (:meth:`_probe_is_clear` ``discs``) is not enough: the press can move away from where a walker was and still
        meet where it will be -- and "never closer than he stands" is no rule for something that walks toward him.
        ``lead`` is a head start: frames the walker walks before the press begins (the read is that old when it is
        sent)."""
        import math
        from ff9mapkit.scene import routes
        wx, wz = d["x"] - here[0], d["z"] - here[1]
        dist = math.hypot(wx, wz)
        off = 0.0 if dist < 1e-9 else math.acos(max(-1.0, min(1.0, (wx * u[0] + wz * u[1]) / dist)))
        bend = math.cos(max(0.0, off - spread))        # the fan's heading nearest the bearing to d
        side = dist * math.sqrt(max(0.0, 1.0 - bend * bend))
        rate = d["speed"] / pace                       # the walker's reach per unit of his

        def gap(ell: float) -> float:                  # how near the fan's arc at ell comes to d, less the stray
            return math.sqrt(max(0.0, dist * dist + ell * ell - 2.0 * dist * ell * bend)) - stray

        need = min(d["R"] + d["pad"], dist - stray) - 0.5
        ahead = d["speed"] * lead
        # gap(l) - rate * l is convex in l (a distance to a point on a line, less a linear term): its least value on
        # [0, reach] is at the clamped stationary point -- l = dist*bend + rate*side / sqrt(1 - rate^2) -- or, when the
        # walker is as fast as he is, at the far end
        worst = reach if rate >= 1.0 else min(reach, max(0.0, dist * bend + rate * side / math.sqrt(1.0 - rate * rate)))
        if min(gap(0.0), gap(worst) - rate * worst, gap(reach) - rate * reach) - ahead < need:
            return False
        until += lead
        path = self._walker_path(d, until)
        if path is None:
            return gap(reach) - d["speed"] * until >= need
        a, b = path
        slack = self.ROUTE_WALKER_TURN * d["speed"] * until
        ends = [_turn(u, spread * k / 2.0) for k in (-2, -1, 0, 1, 2)]
        return all(routes.seg_dist_xz(here[0] + e[0] * reach, here[1] + e[1] * reach, a, b) - stray - slack >= need
                   for e in ends)

    @staticmethod
    def _walker_path(d: dict, frames: float):
        """Where WALKING disc ``d`` can be within ``frames`` of the read, keeping to the LINE it was last seen walking
        along (``dir``, :meth:`_npc_read`) in either direction -- ahead as it goes, or back the way it came, as a
        patrol does at the end of its beat -- at its ``speed``: the segment ``(a, b)``, or None when it has not been
        seen walking. The turns off that line are the caller's slack (ROUTE_WALKER_TURN)."""
        u = d.get("dir")
        if u is None:
            return None
        k = d["speed"] * frames
        return ((d["x"] - u[0] * k, d["z"] - u[1] * k), (d["x"] + u[0] * k, d["z"] + u[1] * k))

    def _walker_lag(self, watch: dict | None) -> float:
        """How many frames after what was pressed (or waited) the objects are read again, as a walking trigger's reach
        is judged (:meth:`_walker_clear`): the most the call has measured (``watch["lag"]``, :meth:`_note_lag`;
        ROUTE_WALKER_LAG_SECONDS' frames before it has one, :meth:`_frames_lasting`: 12 at 60 fps, 24 at 120 -- the
        settle's polling is wall-clock time, and a faster game fits more frames in it), taken half again over -- the
        settle polls the clock, not the frame counter, so the lag jitters."""
        lag = (watch or {}).get("lag")
        return 1.5 * (self._frames_lasting(self.ROUTE_WALKER_LAG_SECONDS) if lag is None else lag)

    @staticmethod
    def _note_lag(watch: dict, lag: float) -> None:
        """Keep the most frames seen to pass between two reads beyond those pressed or waited (``watch["lag"]``)."""
        watch["lag"] = lag if watch.get("lag") is None else max(watch["lag"], lag)

    def _standing(self) -> tuple[float, float]:
        """Where the published state stands him now, ``(x, z)``."""
        st = self.state
        return (st.player_x, st.player_z)

    def _stand_safe(self, here, d: dict, watch: dict, frames: float | None = None) -> bool:
        """Can he stand at ``here`` through ``frames`` (one wait for walkers, ROUTE_WALKER_WAIT_SECONDS' frames, by
        default) and the
        read after them without WALKING trigger ``d`` coming within its pad of him -- judged as a press's end is
        (:meth:`_walker_clear`: along the line it was last seen walking, give or take ROUTE_WALKER_TURN; in any
        direction before it has one)? A press of no reach: his pace (the rate's run) never enters it."""
        return self._walker_clear(here, (1.0, 0.0), 0.0, 0.0, d, self.rate().speed("run"),
                                  (self._frames_lasting(self.ROUTE_WALKER_WAIT_SECONDS) if frames is None else frames)
                                  + self._walker_lag(watch))

    def _walkers_let_stand(self, watch: dict | None, frames: float) -> bool:
        """route_to(npcs=True): may he stand where he is for ``frames`` -- an unstick wait, a wait for a walking
        solid -- with no WALKING trigger reaching him (:meth:`_stand_safe`)? Always, without a watch."""
        st = self.state
        if watch is None or st.player_x is None:
            return True
        return all(self._stand_safe((st.player_x, st.player_z), d, watch, frames)
                   for d in watch["discs"] if d["moving"] and d["kind"] == "trigger")

    def _off_beat(self, here, ends, d: dict) -> bool:
        """Do the ``ends`` of a press from ``here`` keep off WALKING trigger ``d``'s BEAT -- the line it walks,
        ROUTE_WALKER_AHEAD_SECONDS of it either way (:meth:`_walker_path`), ``R`` and ``pad`` wide? A press may cross a
        beat (the time that takes is :meth:`_walker_clear`'s to judge) but not stop on it, where the walker comes back
        along its path to a man who waits there; one that starts on it must end further off its line than it began.
        True for a walker with no heading to trust."""
        from ff9mapkit.scene import routes
        beat = self._walker_path(d, self._frames_lasting(self.ROUTE_WALKER_AHEAD_SECONDS))
        if beat is None:
            return True
        wide = d["R"] + d["pad"]
        now = routes.seg_dist_xz(here[0], here[1], *beat)
        for e in ends:
            off = routes.seg_dist_xz(e[0], e[1], *beat)
            if off < wide and off <= now + 0.5:
                return False
        return True

    def _walker_escape(self, basis: dict, leg: dict) -> bool:
        """route_to(npcs=True, smooth=True), waiting for walkers where standing is NOT safe (:meth:`_stand_safe`: a
        walking trigger could reach him before the read after a wait -- a press left him beside its path): one hold
        AWAY, ROUTE_WALKER_HOLD_TICKS at a run (the frames sure to run no more, at a MEASURED rate -- :meth:`rate`
        ``require=True`` -- and judged at the most they can carry him, Rate.reach), along whichever of the eight pad
        directions ends furthest from the
        line each such walker walks (:meth:`_walker_path`) -- and further than he stands now, or it is not worth a
        press -- while the press itself, as it runs, keeps clear of every walking trigger (:meth:`_walker_clear`) and
        off their beats bar leaving them (:meth:`_off_beat`), of every zone and every standing object
        (:meth:`_probe_is_clear`, the leg's heading spread), and ends where his centre can stand -- on the call's
        walkmesh, COLLISION_RADIUS_W off its walls, where a plan can start again; the leg's drift is not asked (he is
        getting out of the way). Better a press that does not make him safe than standing where it cannot be stood.
        True when it pressed one, False when none keeps the rules (he stands)."""
        import math
        from ff9mapkit.scene import cam, routes
        watch = leg["watch"]
        floor = watch.get("floor")
        rate = self.rate(require=True)                # before the read the step is judged from: a wait lets frames go
        st = self.state
        if st.player_x is None:
            return False
        here = (st.player_x, st.player_z)
        swept = [d for d in watch["discs"] if d["moving"] and d["kind"] == "trigger"]
        threat = [d for d in swept if not self._stand_safe(here, d, watch)]
        if not threat:
            return False
        still = [d for d in watch["discs"] if all(d is not s for s in swept)]
        n = self._frames_within(self.ROUTE_WALKER_HOLD_TICKS, rate)
        reach = rate.reach(n, "run")
        horizon = self._frames_lasting(self.ROUTE_WALKER_WAIT_SECONDS, rate) + self._walker_lag(watch)

        def score(at) -> float:
            return min(routes.seg_dist_xz(at[0], at[1], *(self._walker_path(d, horizon) or ((d["x"], d["z"]),) * 2))
                       - d["R"] for d in threat)
        best = (score(here), None, None)
        for buttons, u in _eight_way(basis):
            end = (here[0] + u[0] * reach, here[1] + u[1] * reach)
            if floor is not None and not self._can_stand(floor, end[0], end[1], cam.COLLISION_RADIUS_W):
                continue
            if not (all(self._walker_clear(here, u, reach, leg["spread"], d, rate.speed("run"),
                                           n + self._tail_frames(rate))
                        and self._off_beat(here, [end], d) for d in swept)
                    and self._probe_is_clear(here, u, reach, leg["hazards"], leg["spread"], discs=still)):
                continue
            if score(end) > best[0] + 0.5:
                best = (score(end), buttons, u)
        if best[1] is None:
            return False
        _score, buttons, u = best
        leg["pressed"] = (buttons, u)
        leg["turned"] = None                          # the yaw the last hold left is no longer his (:meth:`_held_yaw`)
        self._log(f"  route_to: standing at ({here[0]:.0f}, {here[1]:.0f}) is not safe from walking trigger(s) "
                  f"{[d['uid'] for d in threat]}: {n} frames {'+'.join(buttons)} out of the way")
        self.send(*[f"hold {b} {n}" for b in buttons], f"wait {n + 4}")
        after = self.settle()
        self._note_lag(watch, after.frame - st.frame - n)
        if after.field_id == st.field_id and after.player_x is not None:
            self._check_movement(math.hypot(after.player_x - here[0], after.player_z - here[1]) if after.control
                                 else None, n, "run", rate, what="a step out of a walker's way",
                                 span=(st.frame, after.frame))
        return True

    def _boxers(self, basis: dict, here, target, leg: dict, exclude=(), rate: Rate | None = None) -> list:
        """route_to(npcs=True, smooth=True), where :meth:`_plan_hold` finds no hold from ``here`` toward ``target``: the
        published objects that make the presses illegal. Every disc the leg's holds keep clear of (:meth:`_leg_discs`)
        that refuses the SMALLEST press -- one walk frame and its tail, as far as they can carry him at ``rate``
        (default :meth:`rate`; Rate.reach), which the leg's drift never refuses -- along a
        pad direction that gains ground toward ``target`` and that the zones alone let him make: by where it stands
        (:meth:`_probe_is_clear`), or, a WALKING trigger, by where it can walk (:meth:`_walker_clear`,
        :meth:`_off_beat`), each as :meth:`_plan_hold` judges it. None when the zones and the leg alone leave no hold
        either: that is the spot's geometry, and nothing walking off can change it."""
        discs = self._leg_discs(leg)
        rate = self.rate() if rate is None else rate
        if not discs or self._plan_hold(basis, here, target, dict(leg, watch=None), exclude, rate=rate) is None:
            return []
        dx, dz = target[0] - here[0], target[1] - here[1]
        reach = rate.reach(1, "walk")
        spread = leg["spread"]
        until = 1 + self._walker_lag(leg["watch"])
        pads = [u for buttons, u in _eight_way(basis) if u[0] * dx + u[1] * dz > 0 and buttons not in exclude
                and self._probe_is_clear(here, u, reach, leg["hazards"], spread)]

        def refuses(d, u) -> bool:
            if d["moving"] and d["kind"] == "trigger":
                ends = [(here[0] + e[0] * reach, here[1] + e[1] * reach)
                        for e in (_turn(u, spread * k / 2.0) for k in (-2, -1, 0, 1, 2))]
                return not (self._walker_clear(here, u, reach, spread, d, rate.speed("walk"), until)
                            and self._off_beat(here, ends, d))
            return not self._probe_is_clear(here, u, reach, (), spread, discs=[d])
        return [d for d in discs if any(refuses(d, u) for u in pads)]

    def _outwait_box(self, basis: dict, target, leg: dict, exclude, origin: int, way_in=None) -> str:
        """route_to(npcs=True, smooth=True): no hold from where he stands keeps :meth:`_plan_hold`'s rules -- toward
        the leg's end, or, at the zone's finish, toward the spot in the zone it presses for (:meth:`_walk_leg`). Boxed
        by the SPOT -- the zones and the leg alone refuse every press, or the objects that refuse them
        (:meth:`_boxers`) would refuse them still with every WALKER among them gone (:meth:`_npc_walks`; a hold
        planned without them) -- that is final, at once: "boxed", nothing pressed or waited. Boxed by WALKERS -- their
        going would free a press -- it is not: he stands still, reading the objects again, until a hold keeps the
        rules again (:meth:`_outwait_walkers` on the box's own tally, ROUTE_WALKER_BUDGET_SECONDS a call; a wait that
        runs out is ``boxed_by`` walkers) -- and steps out of the way of any held on him (:meth:`_box_step`), who never
        walk off while he stands. Every object that refused the presses of a box by walkers goes into the watch's
        ``boxers``. Returns "clear" (a hold keeps the rules: the caller plans again), "boxed" (the spot, or the wait
        spent), "moved" or "short" (:meth:`_outwait_walkers`).

        ``way_in`` (the zone's finish, asked only through :meth:`_outwait_hold`: the spot of the zone it found his to
        enter with every walker gone) asks more of "clear": no walker standing in the way to that spot either
        (:meth:`_short_of_zone`, judged at every read into ``watch["held"]`` -- the verdict the finish ends on if the
        wait runs out). A walker freed by his step walks on along its line, and a door's approach can be that line --
        a hold that keeps the rules while it is still crossing the door, and a plan made then, walk him straight back
        into it, held again."""
        watch = leg["watch"]
        here = self._standing()
        boxers = self._boxers(basis, here, target, leg, exclude)
        gone = {d["uid"] for d in boxers if self._npc_walks(d, watch)}
        without = dict(leg, watch=dict(watch, discs=[d for d in watch["discs"] if d["uid"] not in gone]))
        if not gone or self._plan_hold(basis, here, target, without, exclude) is None:
            return "boxed"
        self._npc_note(watch["boxers"], boxers)
        since: dict = {}

        def clear() -> bool:
            now = self.state
            if way_in is not None:
                watch["held"] = self._short_of_zone(now, leg["zone"], leg.get("floor"), watch, way_in)
                if watch["held"]["by"] == "walkers":
                    return False
            return self._plan_hold(basis, (now.player_x, now.player_z), target, leg, exclude) is not None
        return self._outwait_walkers(watch, origin, clear, lambda: self._box_step(basis, leg, since), first=True,
                                     boxers=[d for d in boxers if d["uid"] in gone])

    def _box_released(self, watch: dict) -> bool:
        """Walkers that boxed him in let him go (:meth:`_outwait_box`), or walkers in the way into the zone at its
        finish have left it (:meth:`_outwait_hold`): counted in the watch's ``box_cleared``. True while the call may
        still plan again from where he stands -- the plan he walked went round where they stood before --
        ROUTE_BOX_REPLANS times; False after that, and the leg walks on from there."""
        watch["box_cleared"] += 1
        return watch["box_cleared"] <= self.ROUTE_BOX_REPLANS

    def _short_of_zone(self, st: State, zone, floor, watch: dict, way=None) -> dict:
        """What keeps him out of ``zone`` where ``st`` stands him, outside it -- judged PER CAUSE, by the one rule the
        zone's finish waits by (:meth:`_outwait_hold`, :meth:`_outwait_box`) and route_to records (``held_by``,
        ``pinned``): ``{"by", "who", "way"}``.

        THE ZONE WITH THE WALKERS GONE. Of every published object the engine pairs with him where he stands (its |dy|
        test, :meth:`_npc_discs` -- not only the ones a plan kept), a WALKER is one :meth:`_npc_walks` says walks; every
        other disc -- a body that does not walk, a trigger -- stays where it stands. ``way`` is the nearest spot of the
        zone his centre can stand on (:meth:`_zone_spots`, ROUTE_FOOTHOLD_REACH round him) that none of THOSE covers
        (its ``R`` and ``pad``, as a hold keeps it): where he could get in were every walker gone. None, and no walker
        is the cause whatever the walkers do: no spot at all is the spot's GEOMETRY (``by`` None -- a dead door, or
        one standable only further off than the finish looks); spots all covered is what does not walk (``by``
        "bodies", ``who`` the bodies that do not walk standing in the way to the nearest spot the geometry leaves;
        ``by`` None when none does -- a trigger the finish keeps out of covers it). Without ``floor`` nothing says where
        he can stand: nothing is judged the walkers'.

        IN THE WAY, given a ``way``, a WALKER counts only when it stands IN it: its body, ``R`` and ``pad`` as a hold
        keeps it, over the spot or the straight way to it (routes.seg_dist_xz), or in CONTACT with him from that side
        -- its centre within HALF_STEP of its ``r``, within ROUTE_CONTACT_ANGLE of the bearing to the spot
        (:meth:`_body_ahead`'s rule: the engine pushes him out of a body only in contact, collDist <= 0, within 90
        degrees of where he faces -- FieldMapActorController.cs:772-779). Those are ``who``, ``by`` "walkers"; none,
        ``by`` None. A walker pacing its beat nearby is none of these, however near: a walker's step is undone only when
        that step itself would meet him (EventEngine.MoveToward.cs:187-189), and from a step off it exerts nothing on
        him. The reviewed failure: a dead door with a villager pacing 180-253u off it read as held by walkers -- LIVE,
        three attempts and a replay retried without end where two strikes would have broken it -- and a still villager
        in the doorway with a pacer 200u off, the same.

        ``way`` given -- a wait on walkers found to be the cause (:meth:`_outwait_hold`) judging again as it waits --
        is that spot, kept: only the walkers in the way to it from where he stands NOW are judged. He may have stepped
        out of a held walker's way (:meth:`_box_step`, up to ~210u), off the door and beyond ROUTE_FOOTHOLD_REACH of
        it, and a spot looked for again from there finds none -- a door the child still stands in, read as let go."""
        import math
        from ff9mapkit.scene import routes
        out = {"by": None, "who": [], "way": None}
        if st.player_x is None or (way is None and floor is None):
            return out
        here = (st.player_x, st.player_z)
        discs = self._npc_discs(watch["objs"], here, st.player_y, watch["margin"], None, watch.get("speed"),
                                watch.get("heading"))
        walking = {d["uid"] for d in discs if self._npc_walks(d, watch)}
        bare = None
        if way is None:
            fixed = [d for d in discs if d["uid"] not in walking]
            for q in self._zone_spots(here, zone, floor):
                bare = bare or q
                if not self._covers(fixed, q):
                    way = q
                    break
            if bare is None:
                return out                                 # no spot of the zone that near: the geometry's
        cos = math.cos(math.radians(self.ROUTE_CONTACT_ANGLE))

        def in_way(d, spot) -> bool:
            if routes.seg_dist_xz(d["x"], d["z"], here, spot) < d["R"] + d["pad"]:
                return True
            ux, uz = spot[0] - here[0], spot[1] - here[1]
            dx, dz = d["x"] - here[0], d["z"] - here[1]
            dist = math.hypot(dx, dz)
            return dist < d["R"] + self.HALF_STEP and dx * ux + dz * uz >= cos * dist * math.hypot(ux, uz)
        bodies = [d for d in discs if d["kind"] == "body"]
        if way is None:
            who = [d for d in bodies if d["uid"] not in walking and in_way(d, bare)]
            return {"by": "bodies" if who else None, "who": who, "way": None}
        who = [d for d in bodies if d["uid"] in walking and in_way(d, way)]
        return {"by": "walkers" if who else None, "who": who, "way": way}

    def _outwait_hold(self, basis: dict, leg: dict, origin: int, box=None) -> str | None:
        """route_to(npcs=True, smooth=True), the zone's finish (:meth:`_walk_leg`) about to end short of the zone: no
        press keeps the rules (``box``: the ``(target, exclude)`` its presses were planned toward), or two presses in a
        row moved him nothing or no nearer it, or one slid him round someone, or the holds are spent. It ends there only
        once this has judged the cause (:meth:`_short_of_zone`, into ``watch["held"]`` -- what route_to records):

          * NOT THE WALKERS -- no spot of the zone he could get into with every walker gone (the geometry, or what does
            not walk), or none standing in the way to one: None, at once. Nothing waited on or stepped from, however
            many walkers pace nearby; the finish's own verdict stands, and a body that does not walk is never waited on
            (it will not walk off) nor pushed.
          * THE WALKERS -- he stands still and reads again, ROUTE_WALKER_WAIT_SECONDS at a time on the box's own tally
            (:meth:`_outwait_walkers`, within ROUTE_WALKER_BUDGET_SECONDS a call; spent, ``boxed_by`` walkers), stepping
            out of the way of any HELD on him (:meth:`_box_step`: the engine undoes every step a scripted walker takes
            into him, MoveToward.cs:187-189, so one held there walks on only once he moves), until no walker stands in
            the way in -- a walker freed by his step walks on along its line, and a press made while it is still
            crossing the door only walks back into it. Where no press kept the rules, it is first the box by walkers
            (:meth:`_outwait_box` ``way_in``: walkers among what refuses the presses, whose going frees one); a box the
            spot's by that rule is still waited on here when a walker stands in the way in all the same. Rung-3 session
            3, stock 350's door to 355: a Dali child pressed against him on the door step, between him and the zone's
            one standable patch, both attempts of the stock run.

        Every walker waited on goes into the watch's ``boxers``. Returns None (not the walkers), else "clear" (no walker
        in the way in now: the finish presses again), "boxed" (the wait spent), "moved" or "short"
        (:meth:`_outwait_walkers`)."""
        watch = leg["watch"]
        zone, floor = leg["zone"], leg.get("floor")
        st = self.state
        if st.player_x is None:
            return None
        self._npc_read(watch, st)                          # a null sample leaves the last list read standing
        held = watch["held"] = self._short_of_zone(st, zone, floor, watch)
        way = held["way"]
        if way is None:
            return None                                    # not his to enter with every walker gone: not theirs
        if box is not None:
            got = self._outwait_box(basis, box[0], leg, box[1], origin, way_in=way)
            if got != "boxed" or watch["boxed_by"] == "walkers":
                return got
            # the spot's by the box's rule -- judged at once, nothing pressed or waited: ``held`` still stands
        if held["by"] != "walkers":
            return None
        self._npc_note(watch["boxers"], held["who"])
        since: dict = {}

        def free() -> bool:
            now = self.state
            if now.player_x is None:
                return True
            watch["held"] = self._short_of_zone(now, zone, floor, watch, way)     # the spot the wait is for, kept
            return watch["held"]["by"] != "walkers"
        return self._outwait_walkers(watch, origin, free, lambda: self._box_step(basis, leg, since), first=True,
                                     boxers=held["who"], held=True)

    def _npc_walks(self, d: dict, watch: dict) -> bool:
        """Is published object ``d`` a WALKER, as a box is judged (:meth:`_outwait_box`)? Published ``moving`` now -- a
        walker held on him still reads so (s89) -- or seen walking by this call: published ``moving`` by any read of it
        (``watch["walked"]``, :meth:`_npc_read`), or ROUTE_NPC_MOVED from where the plan saw it. ``moving`` is an
        instant's flag: a wanderer paused at a turn of its loop reads false between steps (stock 350's children). An
        object the plan never saw is none of these by that alone."""
        import math
        if d["moving"] or d["uid"] in watch.get("walked", ()):
            return True
        was = watch["planned"].get(d["uid"])
        return was is not None and math.hypot(d["x"] - was[0], d["z"] - was[1]) >= self.ROUTE_NPC_MOVED

    def _walker_step(self, d: dict) -> float:
        """How far one call of WALKING disc ``d``'s walk may carry it (a call an event tick): a TICK of its ``speed``
        (units a frame, over the ticks a frame holds at :meth:`rate` -- two frames at 60 fps, one at 30), and never
        under a tick of the most a walk covers (two run ticks, 2 * RUN_TICK: :meth:`_npc_read`'s bound on a walk) --
        a DISTANCE, the same at every rate. The engine undoes the WHOLE of a step that would bring it within ``r``
        of him (MoveToward.cs:187-189), so a walker held on him stops anywhere up to one step short of contact -- 350's
        children, faster than his run, well beyond the HALF_STEP his own contact is judged by (:meth:`_body_ahead`) --
        and a pace read before it walked into him is no bound on its step: none at all for one held since before the
        call, a crawl for one that stood about first."""
        return max(d["speed"] / self.rate().per_frame(), 2.0 * self.RUN_TICK)

    def _box_step(self, basis: dict, leg: dict, since: dict) -> bool:
        """route_to(npcs=True, smooth=True), boxed in by walkers (:meth:`_outwait_box`) or in the way into the zone at
        its finish (:meth:`_outwait_hold`), in place of a wait: one hold
        OUT OF THE WAY of the walkers HELD ON HIM, when there are any -- a non-solid body within its own step of contact
        with him (its centre within :meth:`_walker_step` of its ``r``), still published ``moving``, that has not MOVED
        ROUTE_NPC_MOVED in ROUTE_WALKER_HELD_SECONDS (its frames at the measured rate, :meth:`_frames_lasting`).
        Moved is SUMMED read to read, not the gap between two reads: the engine undoes a held walker's whole step
        (MoveToward.cs:187-189), so one held on him does not move at all, while a walker pacing a short beat nearby
        comes back to where it was at every turn and has walked all the while (the review's pacer, 45-100u clear of
        contact, read as held at each turn of its beat and stepped away from, 210u off the door, twice). The line it
        was last seen walking is no test of it: a held walker's line is from before it was held, and one that turned
        at a waypoint and was held on its first step still shows the old one. Any the engine pairs with him where he
        stands (the last list read, its |dy| test), not only the ones the plan kept -- one a re-plan gave up to walk
        through is held on him all the same. The engine undoes every step a scripted walker takes into him
        (MoveToward.cs:187-189): it walks on only once HE moves, so a wait for it waits on himself. ``since`` keeps, per
        walker that near, where and when it was last seen to move, how far it has walked since, and where it was read
        last.

        The hold runs along whichever of the eight pad directions ends furthest from the LINE each held walker walks
        (:meth:`_walker_path`, ROUTE_WALKER_AHEAD_SECONDS of it either way: freed, it walks on along it) -- the line it
        was last seen walking, or, never seen walking (held since before the call), the one from it to him: it is held
        BECAUSE its step comes at him, and a step straight away from it only leaves him on its way -- and further than
        he stands now, or it is not worth a press; of two about as far, the one that ends further from the leg's zones.
        It may press INTO a held walker -- that is the point -- which costs a slide round it (the push-out holds him at
        ``r``): the hold is far short of the engine's pass-through (ROUTE_PUSH_LOCK_CALLS), and a talk-only child fires
        nothing even then. So what a SLIDE could carry him into is kept out of the whole reach round him, whichever way
        the slide turns the press: every zone of the leg PROBE_HAZARD_PAD beyond it and every published trigger -- one
        the plan gave up included -- its ``pad`` beyond it (a walking one, what it can walk meanwhile too). The hold is
        the LONGEST that room leaves: ROUTE_WALKER_HOLD_TICKS at a run where it can, shorter, or walked, beside a door
        -- a short step still takes him off the walker's line, and the next one further -- and none only where not even
        one walk frame fits; each length judged, at a MEASURED rate (:meth:`rate` ``require=True``), by the most it can
        carry him (Rate.reach). Every other body -- a solid included, never pressed into -- keeps the fan rule
        (:meth:`_probe_is_clear`, the leg's heading spread); and the end stands on the call's walkmesh,
        COLLISION_RADIUS_W off its walls, where a plan can start. True when it pressed, False when he stands (none held
        on him yet, or no hold keeps those rules)."""
        import math
        from ff9mapkit.content import pathfind
        from ff9mapkit.scene import cam, routes
        watch = leg["watch"]
        # a press into what a slide could carry him to, judged at a MEASURED rate -- asked before the read the step is
        # judged from (a wait for it lets frames, and the walkers, go by)
        rate = self.rate(require=True)
        st = self.state
        if st.player_x is None:
            return False
        here = (st.player_x, st.player_z)
        held = []
        for d in self._npc_discs(watch["objs"], here, st.player_y, watch["margin"], None, watch.get("speed"),
                                 watch.get("heading")):
            if d["kind"] != "body" or d["solid"] or not d["moving"]:
                continue
            if math.hypot(here[0] - d["x"], here[1] - d["z"]) >= d["R"] + self._walker_step(d):
                since.pop(d["uid"], None)                  # a whole step off contact: nothing of his holds it
                continue
            was = since.get(d["uid"])
            walked = None if was is None else was[3] + math.hypot(d["x"] - was[4], d["z"] - was[5])
            if walked is None or walked >= self.ROUTE_NPC_MOVED:
                since[d["uid"]] = (d["x"], d["z"], st.frame, 0.0, d["x"], d["z"])   # seen walking: held from here, if
                continue
            since[d["uid"]] = (was[0], was[1], was[2], walked, d["x"], d["z"])
            if st.frame - was[2] >= self._frames_lasting(self.ROUTE_WALKER_HELD_SECONDS, rate):
                held.append(d)
        if not held:
            return False
        lag = self._walker_lag(watch) + self._tail_frames(rate)          # the walkers' time past the press itself
        room = min((pathfind.poly_gap(here[0], here[1], poly) - self.PROBE_HAZARD_PAD for poly in leg["hazards"]),
                   default=math.inf)
        triggers = [d for d in self._npc_discs(watch["objs"], here, st.player_y, watch["margin"], watch.get("heights"),
                                               watch.get("speed"), watch.get("heading")) if d["kind"] == "trigger"]

        def fits(n: int, gait: str) -> bool:
            reach = rate.reach(n, gait)
            return reach <= room and all(
                math.hypot(here[0] - d["x"], here[1] - d["z"]) - d["R"] - d["pad"]
                - (d["speed"] * (n + lag) if d["moving"] else 0.0) >= reach for d in triggers)
        # the longest reach first -- of two alike a run before a walk, then the more frames (Rate.reach is whole ticks:
        # at 60 fps five run frames reach as far as six)
        sizes = sorted(((n, slow) for n in range(1, self._frames_within(self.ROUTE_WALKER_HOLD_TICKS, rate) + 1)
                        for slow in (False, True)),
                       key=lambda s: (-rate.reach(s[0], "walk" if s[1] else "run"), s[1], -s[0]))
        size = next(((n, slow) for n, slow in sizes if fits(n, "walk" if slow else "run")), None)
        if size is None:
            return False
        n, slow = size
        reach = rate.reach(n, "walk" if slow else "run")
        bodies = [d for d in watch["discs"] if d["kind"] == "body" and all(d["uid"] != h["uid"] for h in held)]
        floor = watch.get("floor")

        def line(d):
            if d["dir"] is None:                      # never seen walking: it walks at him, or it would not be held
                bx, bz = here[0] - d["x"], here[1] - d["z"]
                k = math.hypot(bx, bz)
                d = dict(d, dir=(bx / k, bz / k)) if k > 1e-9 else d
            return (self._walker_path(d, self._frames_lasting(self.ROUTE_WALKER_AHEAD_SECONDS, rate))
                    or ((d["x"], d["z"]),) * 2)
        lines = [(d, line(d)) for d in held]

        def score(at) -> float:
            return min(routes.seg_dist_xz(at[0], at[1], *ab) - d["R"] for d, ab in lines)

        def clear_of_zones(at) -> float:
            return min((pathfind.poly_gap(at[0], at[1], poly) for poly in leg["hazards"]), default=math.inf)
        base, best = score(here), None
        for buttons, u in _eight_way(basis):
            end = (here[0] + u[0] * reach, here[1] + u[1] * reach)
            if floor is not None and not self._can_stand(floor, end[0], end[1], cam.COLLISION_RADIUS_W):
                continue
            if not self._probe_is_clear(here, u, reach, (), leg["spread"], discs=bodies):
                continue
            far, wide = score(end), clear_of_zones(end)
            if far <= base + 0.5:
                continue                              # no further off their lines: not worth a press
            if best is None or far > best[0] + 0.5 or (far > best[0] - 0.5 and wide > best[1] + 0.5):
                best = (far, wide, buttons, u)
        if best is None:
            return False
        _far, _wide, buttons, u = best
        leg["pressed"] = (buttons, u)
        leg["turned"] = None                          # the yaw the last hold left is no longer his (:meth:`_held_yaw`)
        self._log(f"  route_to: walker(s) {[d['uid'] for d in held]} held on him at ({here[0]:.0f}, {here[1]:.0f}) -- "
                  f"a walker walks on only once he moves: {n} frames {'+'.join(buttons)}{' walked' if slow else ''} "
                  f"out of their way")
        steps = [f"hold {b} {n}" for b in buttons]
        if slow:
            steps.insert(0, f"hold cancel {n}")
        self.send(*steps, f"wait {n + 4}")
        after = self.settle()
        self._note_lag(watch, after.frame - st.frame - n)
        if after.field_id == st.field_id and after.player_x is not None:
            self._check_movement(math.hypot(after.player_x - here[0], after.player_z - here[1]) if after.control
                                 else None, n, "walk" if slow else "run", rate,
                                 what="a step out of a held walker's way", span=(st.frame, after.frame))
        since.clear()
        return True

    def _chunk_frames(self, length: float, rate: Rate | None = None) -> int:
        """The frames a chunk of ``length`` presses, walked chunked: both arms of one-axis steering's L at a run, at the
        rate's average speed (``rate``, default :meth:`rate`; Rate.speed -- what walk_to sizes its bursts by: at 120 fps
        twice the frames of 60, and the time a walker is given to close in with them)."""
        import math
        return int(math.ceil(math.sqrt(2.0) * length / (self.rate() if rate is None else rate).speed("run")))

    def _outwait_walkers(self, watch: dict, origin: int, clear, escape=None, first: bool = False,
                         boxers=None, held: bool = False) -> str:
        """route_to(npcs=True): stand still while a WALKING trigger's reach refuses the next press (``clear()`` False),
        ROUTE_WALKER_WAIT_SECONDS at a time, reading the objects again after each (:meth:`_npc_moved`), within the
        call's ROUTE_WALKER_BUDGET_SECONDS -- each wait the frames sure to last its seconds at the measured rate
        (:meth:`_frames_lasting`), the tally the SECONDS those frames hold (frames over the measured fps), so a switch
        of the render rate mid-call neither stretches nor cuts the budget. A walker going elsewhere has gone by in a
        wait or two; one parked in the way
        spends the budget. Standing is not always safe -- a short press can leave him beside a walker's path, and it
        walks on toward him -- so, given ``escape`` (:meth:`_walker_escape`: True when it pressed him out of the way),
        that is tried in place of a wait that could not be stood through. Returns "clear" (``clear()`` holds, at once
        or after waits), "moved" (a read saw an object move onto the path still to walk: plan again), "boxed" (the
        budget is spent: nothing may be pressed -- and it is walkers that boxed him, not the spot: the watch's
        ``boxed_by`` says so) or "short" (the field or control went away while he stood). ``first`` waits once before
        ``clear()`` is asked at all (the caller has just seen a read it refuses).

        ``boxers`` (the WALKING objects among those whose discs refuse every press from here: :meth:`_outwait_box`)
        makes it the wait of a box: the same loop and budget on the box's own tally (``box_waited`` / ``box_waits``),
        so neither wait spends the other's frames, and ``escape`` is :meth:`_box_step`. ``held`` (with ``boxers``: the
        walkers holding him short of the zone at its finish, :meth:`_outwait_hold`) is the same wait on the same tally,
        told as what it is."""
        waited, waits = ("waited", "walker_waits") if boxers is None else ("box_waited", "box_waits")
        who = ("a walking trigger" if boxers is None
               else f"walking object(s) {list(dict.fromkeys(d['uid'] for d in boxers))}")
        what = "reaches every press" if boxers is None else "hold him short of the zone" if held else "box him in"
        told = False
        while first or not clear():
            first = False
            if watch[waited] >= self.ROUTE_WALKER_BUDGET_SECONDS - 1e-9:
                self._log(f"  route_to: {who} still {what} after {watch[waited]:.1f}s of waiting for walkers; "
                          f"nothing may be pressed from here")
                watch["boxed_by"] = "walkers"
                return "boxed"
            if not told:
                st = self.state
                self._log(f"  route_to: {who} could reach the next press from ({st.player_x:.0f}, "
                          f"{st.player_z:.0f}); standing still until it has gone by" if boxers is None else
                          f"  route_to: {who} hold him at ({st.player_x:.0f}, {st.player_z:.0f}), short of the zone "
                          f"-- the presses into it met them; standing still until they walk on" if held else
                          f"  route_to: {who} box him in at ({st.player_x:.0f}, {st.player_z:.0f}) -- every press "
                          f"toward the leg comes nearer one of them; standing still until they walk off")
                told = True
            watch[waits] += 1
            rate = self.rate()
            if escape is not None and escape():
                watch[waited] += self._frames_within(self.ROUTE_WALKER_HOLD_TICKS, rate) / rate.fps
            else:
                wait = self._frames_lasting(self.ROUTE_WALKER_WAIT_SECONDS, rate)
                watch[waited] += wait / rate.fps
                before = self.state
                self.wait_frames(wait)
                self._note_lag(watch, self.state.frame - before.frame - wait)
            st = self.state
            if st.field_id != origin or st.player_x is None or not st.control:
                return "short"
            if self._npc_moved(st, watch):
                return "moved"
        return "clear"

    def _chunk_clear(self, cx: float, cz: float, watch: dict) -> bool:
        """route_to(npcs=True), walked chunked: may the chunk to ``(cx, cz)`` be walked now, as far as the WALKING
        triggers go? :meth:`_walker_clear` of the chunk's line, strayed off by the L of one-axis steering (half the
        chunk, :meth:`_route_chunks`), walked at a run along both arms of that L (:meth:`_chunk_frames`), with the lag
        route_to measures around a chunk -- on the objects as a read taken now has them. A walking trigger's reach
        cannot be undone once it fires: judged at a MEASURED rate (:meth:`rate` ``require=True``, as every walker rule
        of the smooth walk is), never the calibrated default."""
        import math
        rate = self.rate()
        st = self.state
        if st.player_x is None:
            return True
        here = (st.player_x, st.player_z)
        self._npc_read(watch, st)                         # judged on a read taken now, not at the chunk before
        movers = [d for d in self._npc_discs(watch["objs"], here, st.player_y, watch["margin"], watch.get("heights"),
                                             watch.get("speed"), watch.get("heading"))
                  if d["kind"] == "trigger" and d["moving"]]
        if not movers:
            return True
        length = math.hypot(cx - here[0], cz - here[1])
        if length < 1.0:
            return True
        if not rate.ready:
            self.rate(require=True)                       # raises with none; the wait let them walk: judged afresh
            return self._chunk_clear(cx, cz, watch)
        frames = self._chunk_frames(length, rate)
        u = ((cx - here[0]) / length, (cz - here[1]) / length)
        until = frames + self._walker_lag(watch)
        return all(self._walker_clear(here, u, length, 0.0, d, length / frames, until, stray=length / 2.0,
                                      lead=self._tail_frames(rate)) for d in movers)

    @staticmethod
    def _chunk_blockers(known: list, watch: dict | None) -> list:
        """What the chunked walk sizes its chunks by (:meth:`_route_chunks`): the unseen blockers, and the
        published objects the plan keeps at their own radii (route_to(npcs=True))."""
        return list(known) + ([(d["x"], d["z"], d["R"]) for d in watch["discs"]] if watch is not None else [])

    @staticmethod
    def _leg_discs(leg: dict) -> list:
        """The published objects a smooth leg's holds keep clear of: its call's watch's ``discs``, where they
        stood at the last read (:meth:`_npc_moved`); none without route_to(npcs=True)."""
        watch = leg.get("watch")
        return watch["discs"] if watch is not None else []

    @staticmethod
    def _npc_note(into: list, discs) -> None:
        """Name each disc in a route_to record list, once per object and kind: ``{"uid", "sid", "kind", "at",
        "radius", "solid", "moving"}`` -- ``kind`` "body", "range" or "talk"."""
        have = {(e["uid"], e["kind"]) for e in into}
        for d in discs:
            if (d["uid"], d["via"]) in have:
                continue
            have.add((d["uid"], d["via"]))
            into.append({"uid": d["uid"], "sid": d["sid"], "kind": d["via"], "at": [round(d["x"]), round(d["z"])],
                         "radius": round(d["R"]), "solid": d["solid"], "moving": d["moving"]})

    @staticmethod
    def _npc_tally(record: dict, watch: dict | None) -> None:
        """What the call's walkers cost, from its ``watch`` into route_to's ``record`` (nothing without one):
        ``npc_waits`` (walking triggers' reach, :meth:`_outwait_walkers`) and ``box_waits`` / ``box_cleared`` /
        ``boxers`` (walkers that boxed him in, :meth:`_outwait_box`)."""
        if watch is not None:
            record["npc_waits"], record["box_waits"] = watch["walker_waits"], watch["box_waits"]
            record["box_cleared"], record["boxers"] = watch["box_cleared"], list(watch["boxers"])

    def route_cross(self, x: float, z: float, *, expect: int | None = None, avoid=(),
                    margin: float | None = None, timeout: float = 20.0, walkmesh=None,
                    prior="stock", unstick: bool = False, zone=None, smooth: bool = False,
                    npcs: bool = False, gate=None, region=None, settle: float | None = None,
                    overlay_ok: bool = False, handoff: bool = False) -> dict:
        """:meth:`route_to` a point inside a gateway region, then wait for the crossing like :meth:`cross`.

        ``(x, z)`` should be INSIDE the target region and standable --
        :func:`ff9mapkit.content.pathfind.region_goal` picks one -- and ``avoid`` every OTHER region of
        the field. Returns route_to's record with ``landed`` filled in when the field changed after
        the walk ended (and ``changed_to``, the field the id first went to, either way); ``expect``
        asserts the destination. A route that does not exist
        (``waypoints`` None), or a walk that already saw control go (``during`` set; route_to waited
        for that landing itself), is returned at once: there is no further crossing to wait for.
        ``unstick``, ``smooth`` and ``npcs`` are route_to's (waits, pushes, unseen blockers; whole-leg holds;
        planning round the published objects).

        ``zone`` (opt-in: the target region's polygon, the kit's quad -- scan_gateways' ``zone``) adds ``"inside"`` --
        where the walk ended with control held, was he standing IN the region, by the engine's own test (IsInQuad,
        content.doorface.region_contains, on ``region``: the engine's polygon, every point -- scan_gateways'
        ``region``; default ``zone``)? -- the difference between "the way there was blocked" and "he got there and
        nothing fired", which the goal distance behind ``reached`` cannot tell apart. And a walk that ended OUTSIDE it
        waits ROUTE_OUTSIDE_WAIT for the crossing, not ``timeout``: a gateway does not fire for someone standing
        outside its region (the dead middle of a 5- to 8-point one included). Without ``zone``, ``inside`` is None and
        the wait is unchanged. Under ``smooth`` it also goes to route_to, whose last leg then finishes IN the zone
        rather than within tolerance of the goal point -- and, under ``npcs`` too, waits on walkers at the zone's
        edge, and says in ``held_by`` / ``pinned`` what held a walk that still ended outside it (:meth:`route_to`).

        ``gate`` (opt-in, with ``zone``: scan_gateways' ``face_gate`` for this door -- ``[lo, hi]``, or True for the
        stock window; None: the door has no facing gate) is stock's DOOR FACING GATE: smooth or not, the walk goes to
        route_to with the door's ``region`` to FACE (``face``, ``face_window``) -- a walk that ends standing in it with
        nothing fired ends with a step that turns him to face the door (:meth:`_face_the_door`: a turn in place judged
        on the engine's own facing where it publishes one, s90; a walked press where it cannot), ``faced`` and the
        other ``face_*`` keys say what it did, and ``inside`` where that left him. The region's corners are the
        ENGINE's order, the first edge first: that edge is the one the gate takes his bearing to. A door with no gate
        is not faced: it fires for anyone standing in it, so one still shut stays shut however he turns.

        ``settle``, ``overlay_ok`` and ``handoff`` go to route_to (research/o2_design.md H1): the walk may start under a
        hint window he can walk with, and at once. With ``handoff``, a walk that ended with control held waits (at most
        ``timeout``) only for the field to change or control to go, then returns -- never for the destination to become
        playable, so an arrival scene is the caller's to sit through, and no "never became playable" is raised.
        ``lost`` (route_to's) covers this call's own waits too: where control first went, walk or wait.
        """
        from ff9mapkit.content import doorface
        door = zone if region is None else region
        if gate is not None and door is None:
            raise HarnessError("route_cross(gate=...) faces a door: give its zone (or its region)")
        record = self.route_to(x, z, avoid=avoid, margin=margin, tolerance=45.0, walkmesh=walkmesh,
                               prior=prior, timeout=timeout, unstick=unstick, smooth=smooth,
                               zone=zone if smooth else None, npcs=npcs, face=None if gate is None else door,
                               face_window=None if gate is None or gate is True else gate, settle=settle,
                               overlay_ok=overlay_ok, handoff=handoff)
        origin = record["from"]
        record["inside"] = None
        pending = record["landed"] is None and record["waypoints"] is not None and record["during"] is None
        probe = {"live": True, "lost": None}          # the walk's own probe ended with it: this call's waits
        outer, self._loss_probe = self._loss_probe, probe
        try:
            if zone is not None and record["landed"] is None and record["during"] is None:
                st = self.state
                standing = st.field_id == origin and st.player_x is not None and st.control
                record["inside"] = bool(standing and doorface.region_contains(st.player_x, st.player_z, door))
                if pending and standing and not record["inside"]:
                    # outside the zone with control: only a trigger still settling can take him now, so
                    # the full wait applies once one visibly has (the destination may take that long to
                    # become playable), and not otherwise
                    try:
                        self.wait_for(lambda s: s.field_id != origin or not s.control,
                                      timeout=min(timeout, self.ROUTE_OUTSIDE_WAIT),
                                      what=f"a crossing from outside the zone on field {origin}")
                    except HarnessError as err:
                        if "live samples" not in str(err):
                            raise                 # a frozen or silent channel says nothing about the zone
                        pending = False
            if pending and handoff:
                # handed off at the crossing: the field changing or control going is all this waits for
                try:
                    self.wait_for(lambda s: s.field_id != origin or not s.control, timeout=timeout,
                                  what=f"the crossing on field {origin} to begin")
                    record["handoff"] = True
                except HarnessError as err:
                    if "live samples" not in str(err):
                        raise                     # a frozen or silent channel says nothing about the crossing
                now = self.state.field_id
                if now != origin and now > 0:
                    record["landed"] = record["changed_to"] = now
            elif pending:
                try:
                    record["landed"] = self.expect_field_change(timeout=timeout, was=origin, record=record)
                except HarnessError as err:
                    if "never became playable" in str(err):
                        raise
                    now = self.state.field_id
                    if now != origin and now > 0:
                        record["landed"] = now
        finally:
            self._loss_probe = outer
            if record["lost"] is None:
                record["lost"] = probe["lost"]
        if expect is not None and record["landed"] != expect:
            raise HarnessError(f"routed crossing to ({x}, {z}) on field {origin} led to field "
                               f"{record['landed']}, expected {expect} ({record})")
        return record

    def find_transitions(self, *, radius: float = 1200.0, back_to: int | None = None,
                         bearings: int = 8, timeout: float = 15.0) -> list[dict]:
        """Walk outward on several bearings and report every spot that changed the field.

        Locating an invisible trigger otherwise means asking a human to walk into it. After each
        crossing it warps back and resumes, so one call maps the whole perimeter rather than stopping
        at the first exit found.

        ⚠ OVERSHOOTING IS FREE, UNDERSHOOTING LIES. `walk_to` stalls harmlessly against the mesh, so
        aiming past the wall costs nothing -- while a radius shorter than the gateway's distance
        returns "no transition here" having never been near it. The only gateway this verb has ever
        found sat at ~950 units against a shipped default of 420. Hence the default is now well past
        any bench.

        It also refuses to return a confident empty list: a leg that neither arrived nor covered a
        meaningful fraction of the radius did not test its bearing, and saying so is the difference
        between "there is no gateway" and "I did not look".
        """
        import math

        home_field = self.state.field_id if back_to is None else back_to
        st = self._require_field("find_transitions")
        hx, hz = st.player_x, st.player_z
        if hx is None or hz is None:
            raise HarnessError("find_transitions needs a known player position to sweep from")
        home = (hx, hz)
        found: list[dict] = []
        unswept: list[str] = []

        for i in range(bearings):
            angle = 2 * math.pi * i / bearings
            bearing = round(math.degrees(angle))
            # ⚠ EVERY BEARING MUST RADIATE FROM HOME, and walking back is not the same as arriving.
            # A leg that strands the character -- in a corner, against a wall -- used to hand the
            # next bearing a different origin, silently, and the sweep stopped being a circle. Three
            # southward bearings once reported "covered 0 of 950u" from a corner that has no south.
            self._resume_sweep(home, home_field)
            tx, tz = home[0] + radius * math.sin(angle), home[1] + radius * math.cos(angle)
            # WHERE THE LEG STARTS IS HALF THE STORY. A bearing that reports "covered 0 units" is
            # useless without knowing whether the character was at home or stuck in a corner from
            # the previous leg -- and the sweep only radiates from `home` if he actually got back.
            start = self.state
            self._log(f"  bearing {bearing}deg from {start.pos} toward ({tx:.0f},{tz:.0f})")
            record = self.cross(tx, tz, timeout=timeout)
            if record["landed"] is not None:
                found.append({"bearing": bearing, "toward": record["toward"],
                              "field": record["landed"], "travelled": record["travelled"]})
                self._log(f"transition on bearing {bearing}deg -> field {record['landed']}")
                self.warp(home_field)
                self.wait_frames(45)
            elif not record["reached"] and record["travelled"] < 0.5 * radius:
                # ⚠ THE START POSITION IS PART OF THE FINDING. "Covered 0 of 950" from home means
                # the bearing is walled; the same words from a corner mean the previous leg left
                # him there, which is a different problem with a different fix.
                unswept.append(f"{bearing}deg (covered {record['travelled']:.0f} of "
                               f"{radius:.0f}u, from {start.pos})")

        if not found and unswept:
            raise HarnessError(
                f"the sweep of field {home_field} found no transitions, but {len(unswept)} of "
                f"{bearings} bearings were never actually walked: {'; '.join(unswept)}. That is 'I "
                f"did not look', not 'there is nothing here' -- move to open ground or lower the "
                f"radius."
            )
        return found

    def _resume_sweep(self, home: tuple[float, float], field: int) -> bool:
        """Get the character back to the sweep's origin, warping if walking will not do it.

        ⚠ The home point is FROZEN at the sweep's start and is never re-read: re-reading it after a
        warp made every later bearing radiate from wherever the arrival happened to be. This puts
        the CHARACTER back at that fixed point, which is the other half of the same requirement.

        Returns whether he is near enough for the next bearing to mean anything. It does not raise:
        a sweep that cannot re-home is still allowed to report what it did see, and the per-bearing
        record now carries the start position so the report says which kind of nothing it found.
        """
        for attempt in range(2):
            st = self.state
            if st.field_id == field and st.player_x is not None:
                if ((st.player_x - home[0]) ** 2 + (st.player_z - home[1]) ** 2) ** 0.5 <= 120.0:
                    return True
                self.walk_to(home[0], home[1], tolerance=60, strict=False)
                st = self.state
                if (st.player_x is not None and st.field_id == field
                        and ((st.player_x - home[0]) ** 2
                             + (st.player_z - home[1]) ** 2) ** 0.5 <= 120.0):
                    return True
            if attempt == 0:
                # Walking did not do it -- a wall, a corner, or we are not even in the room any
                # more. The warp is the reset that always works.
                self._log(f"  sweep: could not walk back to {home}; warping to {field}")
                self.warp(field)
                self.wait_frames(45)
        st = self.state
        self._log(f"  sweep: still not home after warping -- at {st.pos}, wanted {home}")
        return False

    # -- cutscenes ------------------------------------------------------------------------------

    def wait_control(self, *, timeout: float = 60.0, settle: float | None = None, overlay_ok: bool = False) -> State:
        """Wait until the player has control again. The end of a cutscene, expressed as a condition.

        ⚠ Control FLICKERS true for a moment as a field loads, before the script takes it away --
        so this requires the condition to hold, exactly as `watch_cutscene` does. The two used to
        differ, and the sibling without the settle returned the instant a cutscene began.

        ``overlay_ok``: a window up WHILE he holds control counts as control -- an async hint the script shows
        and closes itself over free movement (Prima Vista 50's "Press the X button when the ? appears.", its
        timed "Light the candle..."), which no page-turn closes. Off by default: an open window otherwise means
        the scene still owns him.
        """
        return self._wait_settled(
            lambda s: (s.control and s.player_x is not None and not s.fading
                       and (overlay_ok or not s.dialog_open)),
            timeout=timeout, what="control to return to the player", settle=settle)

    #: Dialog.DialogGroupButton: the button group a choice window activates in the same coroutine step that
    #: puts its cursor on the script's default (Dialog.InitializeChoiceProcess: ActiveGroup, then
    #: SetCurrentChoice(defaultChoice)). Before it -- the window's open animation -- the agent publishes the
    #: group as '' and ``selected`` as whatever the POOLED window last held (Dialog.selectedChoice survives
    #: Reset); after Confirm it is '' again through the close animation, the choice block still published.
    #: Recorded: 30937 frames 900/906/936, 30921 frames 1012/1018/1050.
    CHOICE_GROUP = "Dialog.Choice"
    #: watch_cutscene(choices="default"): live frames a Confirmed choice is watched for leaving readiness before
    #: Confirm is pressed again, and how many Confirms one answer gets before the long wait. A prompt still
    #: TYPING is already ready -- DialogAnimator sets TextAnimation, then AfterShown -> InitializeChoice sets
    #: the group and the default cursor (DialogAnimator.cs:117-124, Dialog.cs:645-647, 161-164) -- and a
    #: Confirm then only completes the text (Dialog.OnKeyConfirm's TextAnimation branch, :798-808).
    CHOICE_CONFIRM_FRAMES = 20
    CHOICE_CONFIRMS = 3
    #: How many times one watch answers the SAME question (field, prompt and options, cursor) with its
    #: default before calling it a loop: a script that asks again after its own default answer.
    CHOICE_REPEATS = 3
    #: watch_cutscene: after the Confirm that turns a page, the field ticks it waits before it reads the next one --
    #: the frames sure to hold them at the measured rate (:meth:`rate`, Rate.frames_for_ticks: 8 frames at 60 fps, 4
    #: at 30, 16 at 120): the script takes the Confirm and opens its next box on its own ticks. As 8 FRAMES, a
    #: 120 fps game gave it two ticks, and a short page could open and close between two reads.
    CUTSCENE_PAGE_TICKS = 4
    #: choose(): its BLIND wait after the Confirm, in field ticks (12 frames at 60 fps, 6 at 30). The gap between one
    #: choice window and the next is 8 ticks (16 frames at 60 fps on 30937): as 12 FRAMES, a 31 fps game waited 12
    #: ticks and the next window's record was gone before anyone read it.
    CHOOSE_TICKS = 6

    def _choice_ready(self, st: State) -> bool:
        """Is a choice open and taking its answer -- its cursor on the game's default until someone moves it?
        True on ``group`` CHOICE_GROUP; also on a group the engine does not publish at all (None), where only
        watch_cutscene's hold (``settle``) stands between a stale cursor and the default."""
        return st.choice is not None and st.menu_group in (None, self.CHOICE_GROUP)

    def _take_default_choice(self, st: State, *, timeout: float = 5.0) -> dict | None:
        """Answer the ready choice in ``st`` with the option its cursor rests on -- the script's defaultChoice
        (Dialog.InitializeChoiceProcess), never an option of ours. :meth:`select` steers on the engine's own
        cursor (here it confirms the cursor is where ``st`` saw it), then Confirm, then a wait for the window
        to stop taking answers. Returns the choice's record (see :class:`Transcript`), or None when the window
        was still taking answers after ``timeout`` of live frames -- the Confirm did not land; the caller waits
        on it again. Nothing is recorded that the game did not take.

        ⚠ Not :meth:`choose`: its blind wait after Confirm (CHOOSE_TICKS) comes close to the gap between one choice
        window and the next (16 frames at 30937, 8 ticks), and a record of the second would then be missing. This
        watches the window leave readiness instead.

        A PROMPT STILL TYPING takes the first Confirm as "finish the text" (CHOICE_CONFIRM_FRAMES), so a window
        still taking answers CHOICE_CONFIRM_FRAMES live frames after a Confirm gets another -- up
        to CHOICE_CONFIRMS, the last one waited on for ``timeout`` -- instead of costing the whole timeout and
        a re-arm. Only on a published group: without one the choice block lingers through the close
        animation, and a second Confirm there would land on whatever comes next. (A voiced line holds the
        window, answer committed, until its voice ends; the second Confirm then closes it early -- the same
        answer.)

        Raises when the cursor rests on a DISABLED line (``disabled``, or outside ``active``): the game then
        has no default to take, and picking another option would be this harness's choice."""
        ch = dict(st.choice)
        index = int(ch.get("selected", -1))
        active = ch.get("active")
        disabled = list(ch.get("disabled") or [])
        if index < 0 or index in disabled or (active is not None and index not in active):
            raise HarnessError(
                f"a choice is waiting with its cursor on option {index}, which the script has disabled (active "
                f"{active}, disabled {disabled}): there is no default to take, and choosing another option would "
                f"be the harness's preference, not the game's. Pick one explicitly with choose().")
        names = self.options(timeout=timeout)
        pos = active.index(index) if active else index
        record = {"index": index, "text": names[pos] if 0 <= pos < len(names) else None,
                  "prompt": (ch.get("options") or [""])[0], "count": int(ch.get("count", 0)),
                  "field": st.field_id, "frame": st.frame}
        self.select(index, timeout=timeout)
        again = self.CHOICE_CONFIRMS - 1 if st.menu_group == self.CHOICE_GROUP else 0
        for _ in range(again):
            self.press("confirm", 4)
            if self._choice_left(self.CHOICE_CONFIRM_FRAMES, timeout):
                break
            self._log(f"  watch_cutscene: the choice still waits {self.CHOICE_CONFIRM_FRAMES} frames after a "
                      f"Confirm -- its prompt was still typing; Confirm again")
        else:
            self.press("confirm", 4)
            try:
                self.wait_for(lambda s: not self._choice_ready(s), timeout=timeout,
                              what=f"the choice to take option {index}")
            except HarnessError as err:
                if "live samples" not in str(err):
                    raise                 # a frozen or silent channel says nothing about the Confirm
                return None
        self._log(f"  watch_cutscene: took the default choice {index} {record['text']!r} on field {st.field_id}")
        return record

    def _choice_left(self, frames: int, timeout: float) -> bool:
        """After a Confirm: did the choice stop taking answers (:meth:`_choice_ready`) within ``frames`` live
        frames? False when it still took them that many frames on (or ``timeout`` passed first). Readiness
        alone decides: while a prompt types its published options can still grow (ChoicePhrases is built from
        the text parsed so far, :meth:`options`), and a window changing is not a window answered; the next
        choice cannot be ready before this one has closed and the next opened, both with no group."""
        start = None
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._assert_alive()
            st = self.channel.state()
            if st is not None:
                if not self._choice_ready(st):
                    return True
                start = st.frame if start is None else start
                if st.frame >= start + frames:
                    return False
            time.sleep(0.02)
        return False

    def watch_cutscene(self, *, timeout: float = 90.0, advance_boxes: bool = True,
                       settle: float = 1.0, choices: str | None = None) -> list[str]:
        """Sit through a cutscene, collecting its dialogue, until control returns.

        A cutscene is exactly the state a naive harness hangs in: control is withheld, so every
        movement verb silently does nothing and the run dies on an unrelated timeout much later.
        This makes waiting explicit and brings back the transcript, which is the part worth
        asserting on -- by the time control returns the text is gone from the state channel.

        Advances text boxes by default, since many scripted scenes will not proceed without a
        Confirm; pass advance_boxes=False to watch a self-playing scene without touching it.

        A CHOICE stops the Confirms by default -- picking an option is :meth:`choose`'s job -- and a scene
        waiting on one then never gives control back. ``choices="default"`` (opt-in) answers each choice
        with the option the game's own cursor rests on (``choice.selected`` once the window is ready: the
        script's defaultChoice), and carries on through the rest of the scene; each one taken is recorded
        in the returned :class:`Transcript`'s ``choices``. The choice is the game's, never a preference of
        the caller's, so there is no other policy: a cursor resting on a disabled line raises. A window is
        answered only once it is ready (:meth:`_choice_ready`) and has stayed so, unchanged, for
        ``settle`` -- the same hold the "control is back" condition needs. A script whose default answer
        asks the same question again would be answered until the timeout: the same question (field, prompt
        and options, cursor) is answered CHOICE_REPEATS times, and then this raises -- that branch is not
        the default's to take; choose() one.

        Returns a :class:`Transcript` -- a list of the pages, as before.
        """
        if choices not in (None, "default"):
            raise HarnessError(
                f"watch_cutscene(choices={choices!r}): the only policy is 'default', the option the game's "
                f"own cursor rests on. A scripted preference would pick the branch the run then reports on; "
                f"choose() one explicitly instead.")
        pages = Transcript()
        waiting = None                   # (snapshot, since, frame): a ready choice seen holding still
        asked: dict = {}                 # (field, options, cursor) -> answers taken this watch
        deadline = time.time() + timeout
        # Require the "it's over" condition to HOLD, not merely to occur. Control flickers true for a
        # moment as a field loads, before its script takes it away again -- so a single sample was
        # enough to return early with an empty transcript. The same bench, same verb, produced 0
        # pages on one run and 5 on the next until this was added. A flaky verb is worse than a
        # missing one, because it teaches you to distrust real results.
        settle_polls = int(settle / 0.05) or 1
        calm = 0
        samples = 0                      # documents read at all
        frames: set[int] = set()         # distinct agent frames -- proof the game was RUNNING
        while time.time() < deadline:
            self._assert_alive()
            st = self.channel.state()
            if st is None:
                time.sleep(0.05)
                continue
            samples += 1
            frames.add(st.frame)
            if st.dialog_open and st.text.strip():
                calm = 0
                text = st.text
                if not pages or pages[-1] != text:
                    pages.append(text)
                if advance_boxes and not st.choice:
                    self.press("confirm", 3)
                    self.wait_frames(self.rate().frames_for_ticks(self.CUTSCENE_PAGE_TICKS))
                    continue
            if choices and st.choice is not None:
                # the same rule as control coming back: a ready window must HOLD, unchanged, over live
                # frames before its cursor is believed to rest where the game put it
                calm = 0
                snap = (json.dumps(st.choice, sort_keys=True), st.menu_group,
                        (st.raw.get("menu") or {}).get("button"))
                if not self._choice_ready(st):
                    waiting = None
                elif waiting is None or waiting[0] != snap:
                    waiting = (snap, time.time(), st.frame)
                elif time.time() - waiting[1] >= settle and st.frame > waiting[2]:
                    waiting = None
                    key = (st.field_id, json.dumps(st.choice.get("options")), st.choice.get("selected"))
                    if asked.get(key, 0) >= self.CHOICE_REPEATS:
                        raise HarnessError(
                            f"field {st.field_id} asked {st.choice.get('options', [''])[0]!r} again after "
                            f"{asked[key]} default answers (option {st.choice.get('selected')}): the script "
                            f"re-asks after its own default, so waiting on it only loops. Taking another branch is "
                            f"not the default's to do -- choose() one. Collected {len(pages)} page(s).")
                    taken = self._take_default_choice(st)
                    if taken is not None:
                        asked[key] = asked.get(key, 0) + 1
                        pages.choices.append(taken)
                    continue
                time.sleep(0.05)
                continue
            if st.control and st.player_x is not None and not st.fading and not st.dialog_open:
                calm += 1
                if calm >= settle_polls:
                    return pages
            else:
                calm = 0
            time.sleep(0.05)
        # SOFT-LOCK IS THE MOST EXPENSIVE VERDICT THIS TOOL CAN EMIT, so it is reserved for the one
        # case that earns it: we watched a demonstrably LIVE game withhold control. A frozen channel
        # produces the identical symptom and used to produce the identical accusation -- which is
        # how "walking out of room 30820 hangs the game" got written into a commit and a study about
        # a game that was fine the whole time.
        if samples == 0:
            raise HarnessError(
                f"watch_cutscene saw no state at all in {timeout:.0f}s -- {self.channel.classify()}. "
                f"This says nothing about the cutscene."
            )
        if len(frames) <= 1:
            hint = self.diagnose()
            raise HarnessError(
                f"watch_cutscene read {samples} samples in {timeout:.0f}s and the agent's frame "
                f"counter never moved off {next(iter(frames))} -- the channel is frozen, so this is "
                f"NOT a soft-lock finding. {self.channel.classify()}" + (f" -- {hint}" if hint else "")
            )
        last = self.channel.state()
        open_choice = last is not None and last.choice is not None
        raise HarnessError(
            f"control never returned within {timeout:.0f}s across {len(frames)} live frames -- the "
            f"cutscene is still running, waiting on input this did not send, or has soft-locked. "
            f"Collected {len(pages)} page(s) so far"
            + (f", took {len(pages.choices)} default choice(s)" if choices else "") + "."
            + ("" if not open_choice else
               " A dialogue CHOICE is open: this waiter stops at one unless choices='default'." if not choices else
               f" A dialogue CHOICE is still open, unanswered (group {last.menu_group!r}): it never became ready "
               f"and held still, or it would not take its Confirm.")
        )

    # -- menus ----------------------------------------------------------------------------------
    # Driven by LABEL, never by keypress count. Counting is how the dialogue-choice off-by-one
    # silently picked the wrong option, and a menu is worse: entries are reordered by content changes
    # and hidden by story state, so "three downs from the top" means different things on different
    # saves.

    def open_menu(self, *, timeout: float = 15.0) -> State:
        """Open the field main menu."""
        if self.state.ui_state == "MainMenu":
            return self.state
        self.press("menu", 6)
        return self.wait_for(lambda s: s.ui_state == "MainMenu", timeout=timeout,
                             what="the main menu to open")

    def close_menu(self, *, timeout: float = 15.0) -> State:
        """Back out to the field."""
        for _ in range(4):
            if self.state.ui_state == "FieldHUD":
                return self.state
            self.press("cancel", 6)
            self.wait_frames(25)
        return self.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=timeout,
                             what="the menu to close")

    def menu_labels(self, *, direction: str = "down", max_steps: int = 30) -> list[str]:
        """Walk the highlighted entry around the menu, collecting the labels it lands on.

        Discovery rather than assumption: it reports what this menu actually offers on this save,
        which is also the error message worth having when `menu_pick` cannot find something.

        ⚠ It refuses to press blind. With no menu open there is no highlight to publish, so the old
        loop pumped 30 direction presses into whatever screen was live -- on a FieldHUD that WALKS
        THE CHARACTER, moving the thing under test -- and then returned an empty list that read as
        "this menu has no entries".
        """
        if not self.state.menu_label:
            try:
                self.wait_for(lambda s: bool(s.menu_label), timeout=2.0,
                              what="a highlighted menu entry to be published")
            except HarnessError as err:
                raise HarnessError(
                    f"no menu entry is highlighted (ui_state={self.state.ui_state!r}), so there is "
                    f"nothing to walk. Open a menu first -- pressing directions here would drive "
                    f"whatever screen IS live. ({err})"
                ) from err
        seen: list[str] = []
        for _ in range(max_steps):
            label = self.state.menu_label
            if label:
                if label in seen:
                    break                     # wrapped around
                seen.append(label)
            self.press(direction, 4)
            self.wait_frames(10)
        return seen

    def menu_pick(self, label: str, *, direction: str = "down", max_steps: int = 30,
                  confirm: bool = True) -> str:
        """Move the highlight onto `label` (case-insensitive) and confirm it.

        Verifies against the engine's own published highlight at every step, so a cursor that wraps,
        refuses to move, or starts somewhere unexpected fails loudly instead of confirming whatever
        happened to be under it.
        """
        want = label.strip().lower()
        seen: list[str] = []
        stuck = 0
        for _ in range(max_steps):
            current = self.state.menu_label
            if current and current.strip().lower() == want:
                if confirm:
                    self.press("confirm", 4)
                    self.wait_frames(25)
                return current
            if current:
                if seen and seen[-1] == current:
                    stuck += 1
                    if stuck >= 3:
                        raise HarnessError(
                            f"the menu highlight stopped moving on {current!r} while looking for "
                            f"{label!r}; seen so far: {seen}"
                        )
                else:
                    stuck = 0
                    if current in seen:
                        raise HarnessError(
                            f"{label!r} is not in this menu -- went all the way round and saw {seen}"
                        )
                    seen.append(current)
            self.press(direction, 4)
            self.wait_frames(10)
        raise HarnessError(f"gave up looking for {label!r} after {max_steps} steps; saw {seen}")

    # -- talking to things ----------------------------------------------------------------------
    # The narrative axis. These are closed-loop for the same reason movement is: dialogue timing is
    # not a constant. A box appears when the field script decides to show it, pages when the text
    # finishes typing out, and a choice is only selectable once `IsChoiceReady`. Pressing Confirm on
    # a fixed schedule either misses a page or eats two.

    def wait_dialogue(self, *, timeout: float = 10.0, want_text: bool = True) -> State:
        """Wait for a dialogue box to open -- and, by default, for it to actually SAY something.

        `open` and `has text` are separate moments. The box is constructed and registered in
        `ActiveDialogList` before its `Phrase` is assigned, so a probe that stops at `open` reads an
        empty string. That is not hypothetical: it cost a page of a real NPC's dialogue on the first
        run of talk_check, where one mage reported a box and no words. If the text never arrives the
        open box is still returned -- a genuinely wordless window is a legitimate thing to observe.
        """
        st = self.wait_for(lambda s: s.dialog_open, timeout=timeout, what="a dialogue box to open")
        if not want_text or st.text.strip():
            return st
        try:
            return self.wait_for(lambda s: s.dialog_open and bool(s.text.strip()),
                                 timeout=2.0, what="the dialogue box to have text")
        except HarnessError:
            return st

    def interact(self, *, timeout: float = 6.0, frames: int = 4) -> State | None:
        """Press Confirm and report the dialogue THIS press opened, or None if nothing responded.

        Returns rather than raises on silence: "I pressed Confirm here and nothing happened" is a
        legitimate and common finding for a scenario probing where a trigger actually is.

        ⚠ It refuses to credit a box that was ALREADY open. `wait_dialogue` is satisfied instantly by
        a leftover window from the previous step, so a probe of an inert spot used to return the
        previous NPC's dialogue and read as "this responded" -- attributing content to the wrong
        object, which is worse than finding nothing.
        """
        before = self.state
        if before.dialog_open:
            raise HarnessError(
                f"a dialogue box is already open ({before.text[:60]!r}); interact() cannot tell what "
                f"a new press opened. Page it out with advance() first."
            )
        self.press("confirm", frames)
        try:
            return self.wait_dialogue(timeout=timeout)
        except HarnessError:
            return None

    def read(self) -> str:
        """Whatever dialogue is on screen right now, as one string."""
        return self.state.text

    def advance(self, *, max_pages: int = 30, timeout: float = 10.0) -> list[str]:
        """Page through an open dialogue to its end, returning every DISTINCT page seen.

        Collecting the pages is the point: a scenario asserting on a conversation wants the whole
        thing, and by the time the box closes the text is gone from the state channel forever. Stops
        at a choice rather than blundering through it -- picking an option is `choose`'s job, and a
        Confirm here would silently take whichever option happened to be highlighted.
        """
        pages: list[str] = []
        for _ in range(max_pages):
            st = self.state
            if not st.dialog_open:
                break
            if st.choice:
                break
            # Let the page's text land before capturing it -- see wait_dialogue. Without this the
            # loop can photograph the gap between a box being registered and its Phrase being set,
            # record nothing, and then press Confirm through the words it was sent to read.
            if not st.text.strip():
                st = self.wait_dialogue(timeout=2.0)
                if not st.dialog_open:
                    break
            text = st.text
            if text.strip() and (not pages or pages[-1] != text):
                pages.append(text)
            self.press("confirm", 3)
            self.wait_frames(10)
        return pages

    def prompt(self, *, timeout: float = 10.0) -> str:
        """The question above an open choice -- everything before the first selectable line."""
        st = self.wait_for(lambda s: s.choice is not None, timeout=timeout,
                           what="a choice dialogue to be ready")
        raw = list(st.choice.get("options", []))
        return raw[0] if raw else ""

    def options(self, *, timeout: float = 10.0) -> list[str]:
        """The SELECTABLE options, indexed to match :meth:`select` / :meth:`choose`.

        ⚠ There is an off-by-one in the engine's raw array and it silently picks the wrong branch.
        `Dialog.ChoicePhrases` prepends the whole pre-choice header block as element 0
        (`phrases.Add(ParsedText.Substring(0, newLinePos))`), while `SelectChoice` counts only the
        selectable lines from zero. Caught in-game: asking for index 3 against the raw array, which
        reads "Minigames" there, left the cursor sitting on "Tetra Master". This drops the header so
        `options()[i]` is genuinely the option `select(i)` lands on.

        ⚠ It can also be SHORTER than `choice["count"]` -- the observed 15-option menu published only
        13 phrases, because ChoicePhrases is built from the currently parsed text. Treat `count` as
        authoritative for how many options exist and this list as the names of the ones visible.
        """
        st = self.wait_for(lambda s: s.choice is not None, timeout=timeout,
                           what="a choice dialogue to be ready")
        raw = list(st.choice.get("options", []))
        names = raw[1:] if len(raw) > 1 else raw
        count = int(st.choice.get("count", 0))
        active = st.choice.get("active")
        if active is None and len(names) != count:
            # ⚠ THE INDEX SPACES HAVE DIVERGED AND NOTHING HERE CAN RECONCILE THEM. A choice line
            # disabled by the field script is physically REMOVED from the parsed text (so it is
            # absent from these names) while `SelectChoice` still counts the ABSOLUTE list including
            # it. So names[i] is not the option select(i) lands on, and a scenario would confirm a
            # different story branch than the one it named -- and report green for a branch it never
            # tested. Refuse rather than guess; the engine has to publish the mapping.
            raise HarnessError(
                f"this dialogue offers {count} selectable options but published {len(names)} names "
                f"{names!r}, so the name list and the cursor index are different index spaces (some "
                f"lines are disabled by the script). Nothing driver-side can map between them. Use "
                f"select() with an ABSOLUTE index and assert on the resulting branch, or rebuild the "
                f"engine so the choice publishes its active indexes."
            )
        return names

    def option_index(self, name: str, *, timeout: float = 10.0) -> int:
        """The ABSOLUTE cursor index of the option reading ``name`` -- what ``select`` wants.

        Named lookup exists for the same reason `menu_pick` does: an index counted by a human from a
        screenshot is the single most reliable way to test the wrong branch.
        """
        st = self.wait_for(lambda s: s.choice is not None, timeout=timeout,
                           what="a choice dialogue to be ready")
        names = self.options(timeout=timeout)
        want = name.strip().lower()
        matches = [i for i, n in enumerate(names) if n.strip().lower() == want]
        if not matches:
            raise HarnessError(f"no option reads {name!r}; this dialogue offers {names!r}")
        if len(matches) > 1:
            raise HarnessError(f"{name!r} appears {len(matches)} times in {names!r} -- ambiguous")
        active = st.choice.get("active")
        if active:
            return int(active[matches[0]])
        return matches[0]

    def select(self, index: int, *, timeout: float = 10.0) -> int:
        """Move the choice cursor to `index` WITHOUT confirming. Returns where it ended up.

        Split from `choose` so cursor movement can be asserted on its own -- confirming an option
        navigates away, which destroys the evidence of whether the cursor ever got there. Steers on
        the engine's own `SelectChoice` rather than counting keypresses: a cursor that wraps, starts
        somewhere unexpected, or refuses to move cannot then silently pick the wrong option, which
        for a story scenario is the difference between testing a branch and testing the other one.
        """
        st = self.wait_for(lambda s: s.choice is not None, timeout=timeout,
                           what="a choice dialogue to be ready")
        count = int(st.choice.get("count", 0))
        if not 0 <= index < count:
            raise HarnessError(f"choice index {index} out of range (the dialogue offers {count})")

        for _ in range(count * 2 + 6):
            st = self.state
            if st.choice is None:
                raise HarnessError("the choice dialogue closed while selecting")
            current = int(st.choice.get("selected", 0))
            if current == index:
                return current
            self.press("down" if current < index else "up", 4)
            self.wait_frames(8)
        raise HarnessError(
            f"could not move the choice cursor to option {index}; it stopped at "
            f"{self.state.choice.get('selected') if self.state.choice else 'none'}"
        )

    def choose(self, index: int, *, timeout: float = 10.0) -> None:
        """Select option `index` in an open choice dialogue and confirm it -- then wait CHOOSE_TICKS field ticks, the
        frames sure to hold them at the measured rate (:meth:`rate`), for the window to take it."""
        self.select(index, timeout=timeout)
        self.press("confirm", 4)
        self.wait_frames(self.rate().frames_for_ticks(self.CHOOSE_TICKS))

    #: gEventGlobal is Byte[2048], so bits run 0 .. 16383. See [[project-ff9-story-flags]] for the
    #: SAFE allocation band (8712+) -- this is only the physical range.
    MAX_FLAG_BIT = 2048 * 8 - 1

    # -- battle -----------------------------------------------------------------------------------
    # The pillar the state channel was dark on. Everything here closes its loop on published state,
    # and every wait is anchored to `battle_epoch` -- because `btl_result` is 0 both DURING a battle
    # and BEFORE any battle has ever run, so it cannot tell those apart on its own.

    def start_battle(self, scene: int, *, group: int = -1, timeout: float = 60.0) -> State:
        """Boot a real battle from a field and wait until it is actually running.

        ⚠ Not the diorama. `NetSyncDiorama.Boot` is the cheap way to put a battle scene on screen and
        it sets `isDebug`, under which the battle CAN NEVER END -- so every result or reward
        assertion against it is vacuous. This uses the field's own encounter transition.
        """
        st = self.state
        if st.ui_state != "FieldHUD":
            raise HarnessError(
                f"start_battle needs a field to leave FROM (ui_state={st.ui_state!r}); the engine "
                f"routes the transition by the FIELD's nextMode."
            )
        before = st.battle_epoch
        self.send(f"battle {int(scene)} {int(group)}")
        return self.wait_battle(timeout=timeout, after_epoch=before)

    def wait_battle(self, *, timeout: float = 60.0, after_epoch: int | None = None) -> State:
        """Wait until a battle is genuinely up.

        Anchored on the epoch ADVANCING rather than on `active`, because `active` is also true for a
        diorama and because a stale battle scene would satisfy it. `after_epoch` defaults to whatever
        the epoch is now, which makes the common "trigger something, then wait" shape correct.
        """
        base = self.state.battle_epoch if after_epoch is None else after_epoch
        # ⚠ REQUIRE THE UNITS. `active` goes true while `btl_list` is still being built, so a wait
        # that stopped there handed the scenario an empty roster -- measured: the first live run
        # reported "0 party + 0 enemy" from a battle that seconds later had a full list and moving
        # ATB gauges. A battle nobody can see the combatants in is not yet a battle worth returning.
        st = self.wait_for(
            lambda s: s.in_battle and s.battle_epoch > base and s.units(),
            timeout=timeout,
            what=f"a real battle to start with its units listed (epoch past {base}; "
                 f"a diorama does not count)")
        self._log(f"battle {st.battle.get('scene')} up: epoch {base} -> {st.battle_epoch}, "
                  f"{len(st.units())} unit(s)")
        return st

    def wait_battle_over(self, *, timeout: float = 180.0) -> int:
        """Wait for the battle to END and return its result code.

        ⚠ It waits for the battle to stop being active AND for a non-zero result, because
        `btl_result` is 0 for the whole battle. A scenario that polled the result alone would read
        "in-progress" as an answer.
        """
        st = self.state
        if st.battle.get("debug"):
            raise HarnessError(
                "this battle is running with isDebug set (a diorama). Under isDebug the engine "
                "suppresses the auto-end, so it can never finish -- waiting for a result here would "
                "hang, and asserting one would be green having observed nothing."
            )
        # ANCHOR ON THE EPOCH. `result` is published always -- it has to be, since it is the answer
        # only after the fight -- so a bare "result != 0" would also be satisfied by the PREVIOUS
        # battle's result the instant this one starts. Requiring the epoch to still be the one we
        # are watching is what ties the answer to the question.
        epoch = st.battle_epoch
        st = self.wait_for(
            lambda s: s.battle_result != 0 and s.battle_epoch == epoch,
            timeout=timeout,
            what=f"battle {epoch} to reach a result")
        self._log(f"battle {epoch} result: {st.battle_result_name} ({st.battle_result})")
        return st.battle_result

    def expect_battle_result(self, kind: str, *, timeout: float = 180.0) -> bool:
        """Assert how the battle ended, by name ('victory', 'defeat', 'escape', ...)."""
        wanted = [k for k, v in State.BATTLE_RESULTS.items() if v == kind]
        if not wanted:
            raise HarnessError(f"unknown battle result {kind!r}; "
                               f"known: {sorted(set(State.BATTLE_RESULTS.values()))}")
        try:
            got = self.wait_battle_over(timeout=timeout)
        except HarnessError as err:
            return self.check(False, f"the battle ended in {kind}", str(err))
        return self.check(got in wanted, f"the battle ended in {kind}",
                          f"got {State.BATTLE_RESULTS.get(got, got)} ({got})")

    #: The battle HUD's NGUI groups, from `BattleHUD.Const.cs`. Three of them can be open after a
    #: command is confirmed and only ONE of them is a target cursor: `Battle.Ability` and
    #: `Battle.Item` are SUBMENUS. A predicate that accepted "any group but the command list" as
    #: the target cursor confirmed a Potion when it meant to confirm an enemy -- measured live
    #: 2026-09-04 (scenarios/battle_hud_check.py, the screenshot shows the item list open).
    BATTLE_COMMAND_GROUP = "Battle.Command"
    BATTLE_TARGET_GROUP = "Battle.Target"
    BATTLE_SUBMENU_GROUPS = ("Battle.Ability", "Battle.Item")

    def battle_pick(self, label: str, *, direction: str = "down", max_steps: int = 24,
                    confirm: bool = True) -> str:
        """Move the battle cursor onto `label` and confirm it -- BY NAME, never by press count.

        Asserted against the engine's own `ButtonGroupState.ActiveButton`, which is the value
        `BattleHUD.OnKeyConfirm` actually consumes -- not `UICamera.selectedObject`, which is the
        accessor a diagnostic reads. `UIKeyTrigger` prefers ActiveButton and only falls back to the
        selected object, so publishing the fallback was this arc's own law still live in the code.

        ⚠ THE COMMAND LIST IS A TWO-COLUMN GRID THAT DOES NOT WRAP. Measured live 2026-09-04: from
        `Steal`, twenty-four `down` presses saw `Steal -> Item` and then `Item` forever, and never
        `Attack`, which sits one row ABOVE the start point. The field main menu wraps, so the walk
        `menu_pick` uses -- one direction until the labels repeat -- is exactly wrong here: it can
        neither reach an entry above the cursor nor visit the right-hand column (Defend / Skill /
        Change) at all. So this searches the way a thumb does: `direction` to the edge, the other
        way to the other edge, then the neighbouring column, and it reads "the label stopped
        moving" as the edge rather than as a fault.
        """
        want = label.strip().lower()
        opposite = {"down": "up", "up": "down"}.get(direction, "up")
        seen: list[str] = []
        steps = 0

        def cursor() -> tuple[str, str]:
            c = self.state.battle_cursor
            return (c.get("group") or ""), (c.get("label") or "").strip()

        def nudge(button: str) -> bool:
            """One press; True if the label moved."""
            nonlocal steps
            _, before = cursor()
            self.press(button, 4)
            self.wait_frames(10)
            steps += 1
            _, after = cursor()
            return after != before

        def walk(button: str) -> bool:
            """Press `button` until the label stops changing. True if `want` was reached."""
            stalls = 0
            while steps < max_steps:
                group, cur = cursor()
                if group != self.BATTLE_COMMAND_GROUP:
                    # A closed cursor is not an edge of the grid. The list closes when the turn
                    # passes (the character went down, the fight ended) -- pressing on into
                    # nothing would read as "walked both columns, saw []".
                    st = self.state
                    why = ("the battle is over" if not st.in_battle
                           else f"the cursor is in {group!r} on {cur!r}" if group
                           else "no command list is open (turn.slot is "
                                f"{st.turn_slot}, result={st.battle_result_name})")
                    raise HarnessError(
                        f"battle_pick needs the command list ({self.BATTLE_COMMAND_GROUP}) open: "
                        f"{why}. Wait for a turn first.")
                if cur and cur.lower() == want:
                    return True
                if cur and cur not in seen:
                    seen.append(cur)
                if nudge(button):
                    stalls = 0
                else:
                    # A press that moved nothing is the EDGE of the grid, not a fault -- two in a
                    # row, so a press swallowed by a HUD animation does not end the walk early.
                    stalls += 1
                    if stalls >= 2:
                        return False
            return False

        found = False
        for column in (None, "right", "left"):
            if steps >= max_steps:
                break
            if column is not None and not nudge(column):
                continue                       # no column that way
            if walk(direction) or walk(opposite):
                found = True
                break
        if not found:
            group, cur = cursor()
            if cur and cur.lower() == want:
                found = True
        if not found:
            raise HarnessError(
                f"{label!r} is not on the battle command list -- walked both columns in {steps} "
                f"press(es) and saw {seen} (cursor now on {cursor()[1]!r})")
        current = cursor()[1]
        if confirm:
            self.press("confirm", 4)
            self.wait_frames(14)
        return current

    def accept_name(self, *, timeout: float = 30.0) -> State:
        """Take the naming screen's DEFAULT name and return to the field. Returns the state after it closes.

        A field script's ``Menu(1, char)`` opens NameSettingUI (EventService.OpenNameMenu -> ui_state
        "NameSetting") and blocks until it closes; no dialog is open meanwhile, so :meth:`watch_cutscene` and
        :meth:`advance` press nothing and wait out their timeout. The box opens focused on the prefilled
        default name (NameSettingUI.cs:146): the first Confirm takes focus off it, the next is OK and saves
        the name (:72-83, :107, :173). Cancel would refocus the box and Menu reset it, so neither is pressed.
        Each Confirm waits up to 2 s for the screen to close before the next, so no Confirm can fall through
        onto the page the script shows after it.
        """
        self.wait_for(lambda s: s.ui_state == "NameSetting", timeout=timeout, what="the naming screen")
        for _ in range(4):
            self.press("confirm", 4)
            try:
                st = self.wait_for(lambda s: s.ui_state != "NameSetting", timeout=2.0,
                                   what="the naming screen to close")
            except HarnessError:
                continue
            self._log(f"  accept_name: closed -> ui={st.ui_state}")
            return st
        raise HarnessError("the naming screen stayed up through 4 Confirms. The harness's Confirm may not reach "
                           "NameSettingUI; [Hacks] DisableNameChoice=1 in Memoria.ini skips the screen instead")

    def _dismiss_tutorial(self) -> bool:
        """Close the battle TUTORIAL screen if it is up; True if it was. battle.cs:100-105 opens it on the Masked
        Man's scene 336 before the first command, and no command menu opens while it is up, so a fight waiting
        for one waits out its whole timeout. One Confirm closes it (TutorialUI.cs:116-125)."""
        if self.state.ui_state != "Tutorial":
            return False
        for _ in range(4):
            self.press("confirm", 4)
            try:
                self.wait_for(lambda s: s.ui_state != "Tutorial", timeout=2.0, what="the battle tutorial to close")
            except HarnessError:
                continue
            self._log("  the battle tutorial screen: closed")
            return True
        raise HarnessError("the battle tutorial screen stayed up through 4 Confirms")

    def battle_act(self, command: str = "Attack", *, timeout: float = 30.0) -> bool:
        """Take one turn THROUGH THE HUD: pick a command by NAME, then confirm a target.

        This is the path that proves the menu itself works -- nothing in :meth:`act` presses a
        button. It steers, but never blindly: it waits for the command group, picks by name against
        the engine's own `ButtonGroupState.ActiveButton`, then waits for the TARGET group before
        confirming. Blind double-taps do not work -- measured: two confirms 16 frames apart left the
        cursor sitting in `Battle.Command` while the enemy chewed through Zidane's HP.

        ⚠ IT DRIVES ONE-STEP COMMANDS ONLY (Attack, Steal, Defend, Change). A command that opens the
        Ability or Item SUBMENU is refused rather than confirmed: the first cut treated "any group
        that is not the command list" as the target cursor and cheerfully confirmed a Potion. Cast
        an ability or use an item by name with :meth:`act`, or walk the submenu yourself.

        A battle TUTORIAL screen up first is closed on the way (:meth:`_dismiss_tutorial`).
        """
        deadline = time.time() + timeout
        while True:
            if time.time() >= deadline:
                return False
            try:
                st = self.wait_for(lambda s: ((s.battle_cursor.get("group") or "") == self.BATTLE_COMMAND_GROUP
                                              or s.ui_state == "Tutorial"),
                                   timeout=max(0.1, deadline - time.time()), what="the battle command menu")
            except HarnessError:
                return False
            if st.ui_state != "Tutorial":
                break
            self._dismiss_tutorial()
        try:
            self.battle_pick(command)
        except HarnessError as err:
            self._log(f"  battle_act: could not pick {command!r} ({err})")
            return False
        # Target selection is its own NGUI group. Waiting for it is what makes the second confirm
        # land on a target rather than re-opening the command list -- and it has to be THAT group,
        # not merely "something other than the command list".
        after = (self.BATTLE_TARGET_GROUP,) + self.BATTLE_SUBMENU_GROUPS
        try:
            st = self.wait_for(lambda s: (s.battle_cursor.get("group") or "") in after,
                               timeout=8.0, what="the target cursor")
        except HarnessError:
            # Some commands need no target and resolve straight away; that is not a failure.
            return True
        group = st.battle_cursor.get("group")
        if group in self.BATTLE_SUBMENU_GROUPS:
            self.press("cancel", 4)
            self.wait_frames(10)
            raise HarnessError(
                f"{command!r} opens the {group} submenu, not a target cursor. battle_act drives "
                f"one-step commands; use act({command!r}...) with the ability or item name, or walk "
                f"the submenu with battle_pick. (Backed out of it with Cancel.)")
        self.press("confirm", 4)
        self.wait_frames(20)
        return True

    def battle_command(self, slot: int, command: int, *, sub: int = 0, target: int = 0,
                       cursor: int = 0) -> None:
        """Issue an exact command, bypassing the cursor entirely.

        The difference between testing a damage formula and testing NGUI navigation. Goes through
        `BattleHUD.SendNetCommand`, which is the same entry point co-op uses to replay a remote
        player's command -- the game's own path rather than a second implementation of one.
        """
        self.send(f"battlecmd {int(slot)} {int(command)} {int(sub)} {int(target)} {int(cursor)}")

    def flee(self, *, timeout: float = 60.0) -> bool:
        """Hold L1+R1 to run away, and report whether the party actually LEFT.

        ⚠ FLEEING IS A DICE ROLL, not a duration. ``BattleHUD.Update`` counts UNBROKEN real seconds
        with both bumpers down and calls ``btl_sys.CheckEscape(true)`` -- the call that rolls --
        once per second past 1.0, resetting the counter the instant either bumper lifts. The roll
        is ``200 / avgEnemyLevel * avgPlayerLevel / 16`` percent with integer division throughout
        (BattleCalculator.cs:358): single digits against a levelled enemy. So this holds for the
        whole window and reports what happened; a False is usually variance, not a defect.

        ⚠ IT ISSUES ONE HOLD AND DOES NOT RE-ISSUE. That is not a style choice. Until s83 rev 4 a
        re-issued hold punched a one-frame hole in the press (``Schedule`` restarted ``_downFrame``
        at ``frameCount + 1``), the counter reset in that hole, and a flee re-issued every 0.8s
        never rolled ONCE -- while ``btl_escape_key``, set before the counter is even tested, kept
        the character running on screen the entire time. That is what the owner saw and reported as
        "the flee animation for a couple of seconds but he didn't actually leave". The engine now
        extends rather than restarts; issuing one hold means this verb is correct on both.

        Waits on ``escaping`` -- the queued ``SysEscape`` command -- as well as the result, because
        the result only lands once the party has finished leaving.
        """
        st = self.state
        if not st.in_battle:
            raise HarnessError("flee() needs a real battle in progress")
        # ⚠ REFUSE A NO-ESCAPE SCENE INSTEAD OF HOLDING FOREVER. `btl_escape_key` is set before
        # CheckEscape looks at the flag, so the character plays the running animation the whole
        # time and nothing on screen says it is futile -- owner-observed. Holding here is not a
        # slow escape, it is no escape, and returning False would blame the dice for a rule the
        # scene declared up front.
        if st.can_escape is False:
            raise HarnessError(
                f"battle scene {st.battle.get('scene')} forbids running "
                f"(btl_scene.Info.Runaway is false), so CheckEscape shows \"Cannot escape!\" and "
                f"never rolls. The character WILL play the running animation regardless -- that is "
                f"btl_escape_key, which is set before the flag is tested. Win, lose, or use a "
                f"different scene."
            )
        # One hold covering the whole window, plus a margin so it cannot lapse just before the
        # deadline. Both bumpers go in ONE request: a request's steps drain in a single pass and
        # share a _downFrame, and CheckEscape needs them down together. The hold is FRAMES and the
        # window is wall-clock SECONDS, so the frames are the ones SURE to last that long at the
        # measured render rate (:meth:`rate`, Rate.frames_at_least) -- at the 60 fps a frame count
        # once assumed, a 120 fps game lifted the keys halfway through the window and the dice took
        # the blame -- plus two seconds of margin. A battle pairs no frames (the clock measures on a
        # field), so the rate is the one the field before it measured, carried: it is the monitor's.
        # With NONE measured the hold is sized at UNMEASURED_FPS (:meth:`_rate_at_most`): a hold past the
        # window costs nothing -- both bumpers are released below the moment the wait ends -- and one short
        # of it costs the verdict, so the unknown is taken on the side that cannot lie.
        rate = self._rate_at_most()
        frames = rate.frames_at_least(timeout) + rate.frames_at_least(2.0)
        self.send(f"hold l1 {frames}", f"hold r1 {frames}", wait=False)
        escaped = False
        # ⚠ SAMPLED DURING THE HOLD, NOT AFTER IT. The first cut read escape_held from a snapshot
        # taken once the bumpers had already been released, where it is 0 by definition -- so every
        # unlucky roll came back as "the engine never saw the hold", which is a completely different
        # fault and would have sent the next reader to the input layer. The predicate runs on every
        # sample, which is the only place the value means anything.
        seen_held = []

        def done(s):
            if s.battle.get("escape_held"):
                seen_held.append(True)
            return s.escaping or s.battle_result != 0 or not s.in_battle

        ended: State | None = None
        try:
            ended = self.wait_for(done, timeout=timeout,
                                  what="the escape to roll (a few percent per second)")
        except HarnessError:
            ended = None
        finally:
            # ⚠ ALWAYS RELEASE. `hold` is non-blocking, so a bumper left down leaks into whatever
            # runs next -- and these two in particular keep the party running.
            self.send("release l1", "release r1")
        st = self.state
        # ⚠ "THE WAIT RETURNED" IS NOT "THE PARTY LEFT". `done` also fires when the battle ends for
        # ANY reason -- a wipe, an enemy fleeing, a victory landing mid-hold -- and the first cut
        # returned True on every one of them, reporting a defeat as a successful escape. Only the
        # queued SysEscape or the escape RESULT is the party actually leaving.
        escaped = bool(ended is not None and (ended.escaping or st.escaping
                                              or ended.battle_result == 4 or st.battle_result == 4))
        if ended is not None and not escaped:
            self._log(f"  flee: the battle ended before any roll landed -- "
                      f"result={st.battle_result_name}, not an escape")
            return False
        if not escaped:
            held = bool(seen_held)
            self._log(
                f"  flee: no roll landed in {timeout:.0f}s "
                f"(escape_held={held}; the engine {'saw' if held else 'NEVER SAW'} the hold)")
            # An engine that never set escape_held is a real fault -- the input is not arriving --
            # and it must not be reported as bad luck.
            if not held:
                raise HarnessError(
                    "the bumpers were held for the whole window and btl_escape_key never went high, "
                    "so the input is not reaching BattleHUD.Update at all. That is not the dice: "
                    "check that the agent is armed and that this is a battle, not the diorama.")
            return False
        self._log(f"  flee: escaping={st.escaping} result={st.battle_result_name}")
        return True

    # ---- PLAYING a battle -----------------------------------------------------------------
    # Everything above this line OBSERVES a battle. These take turns in one.

    #: The protocol that made a battle playable rather than merely visible.
    PLAY_PROTOCOL = 4

    #: TargetType values that mean "an ally" (Memoria.Data.TargetType).
    _ALLY_TARGETS = {1, 4, 7, 10}
    #: ...and the ones the engine forces onto a whole side, where a single id is not a legal answer.
    _GROUP_TARGETS = {6: 3, 7: 1, 8: 2, 12: 3}      # TargetType -> CursorGroup

    def _require_play_protocol(self, verb: str) -> None:
        proto = self.state.protocol or 0
        if proto < self.PLAY_PROTOCOL:
            raise HarnessError(
                f"{verb} needs protocol {self.PLAY_PROTOCOL}; the deployed engine speaks {proto}. "
                f"Rebuild and redeploy the DLL (py tools/build_memoria.py) and RELAUNCH the game -- "
                f"an engine change is not picked up by ~ Reload field.")

    def menus(self, slot: int | None = None, *, timeout: float = 10.0) -> dict:
        """Collect what one party slot can DO, and return it.

        A REQUEST, not a field of every state sample, because collecting it writes the HUD's
        ability-detail cache (``CollectNetMenus`` -> ``SetAbilityAp``) -- and an instrument that
        mutates the game thirty times a second in order to observe it is not an instrument. The
        cost is that the answer is a snapshot, so this waits for one stamped with THIS slot and
        THIS battle rather than trusting whatever is published.
        """
        self._require_play_protocol("menus()")
        st = self.state
        if not st.in_battle:
            raise HarnessError("menus() needs a real battle in progress")
        if slot is None:
            slot = st.turn_slot
            if slot < 0:
                raise HarnessError(
                    "menus() without a slot reads whoever the game is currently asking, and it is "
                    "asking nobody (turn.slot is -1). Wait for a turn first, or name a slot.")
        self.send(f"menus {int(slot)}")
        st = self.wait_for(lambda s: s.menu_is_for(int(slot)), timeout=timeout,
                           what=f"the command menu for slot {slot} to be published")
        return st.battle_menu

    def wait_turn(self, *, timeout: float = 90.0) -> int:
        """Wait until the game asks a party member for a command, and return that slot.

        ``turn.slot`` is ``BattleHUD.CurrentPlayerIndex``, which the HUD sets in ``SwitchPlayer``
        for the first ready slot that has not committed a command. It is the game's own "your move"
        -- not a guess assembled from ATB values.

        Raises rather than returning a sentinel if the battle ends while waiting, because a caller
        that gets -1 back tends to press on and command a slot in a fight that is over.
        """
        # ⚠ `turn_slot` is already gated on the command phase by the agent, so this cannot fire
        # on the stale slot the previous battle left behind -- the failure that froze a fight.
        st = self.wait_for(
            lambda s: s.turn_slot >= 0 or s.battle_result != 0 or not s.in_battle,
            timeout=timeout, what="a party member to be asked for a command")
        if st.turn_slot < 0:
            raise HarnessError(
                f"the battle ended before anyone was asked for a command "
                f"(result={st.battle_result_name}, in_battle={st.in_battle})")
        return st.turn_slot

    def act(self, command: str = "Attack", *, slot: int | None = None,
            target: str | int | None = None, timeout: float = 20.0) -> dict:
        """Take ONE turn: commit ``command`` for ``slot`` against ``target``, BY NAME throughout.

        This is the deterministic path -- it commits through ``BattleHUD.SendNetCommand``, the same
        entry point co-op uses to replay a command, after ``SetIdle()`` hands the slot back from the
        local menu. It tests the battle logic, NOT the HUD: nothing here presses a button, so a
        scenario that must prove the menu itself works wants :meth:`battle_act` instead.

        ``command`` is matched against the published menu in three places, in order: the command
        list ("Attack", "Defend", "Steal"), the ability list ("Fire", "Cure" -- the parent command
        is inferred), and the item list ("Potion"). The names are the engine's own, resolved from
        the character's preset, trance state and equipment, so no table here can drift out of date.
        """
        self._require_play_protocol("act()")
        if slot is None:
            slot = self.wait_turn()
        slot = int(slot)
        menu = self.menus(slot)
        st = self.state
        cmd, sub, ttype, for_dead, what = self._resolve_command(st, menu, command, slot)
        tar_id, cursor, tname = self._resolve_target(st, slot, target, ttype, for_dead)
        self._log(f"  act: slot {slot} {what} -> {tname} "
                  f"(cmd={cmd} sub={sub} tar=0x{tar_id:x} cursor={cursor})")
        self.send(f"battlecmd {slot} {cmd} {sub} {tar_id} {cursor}")
        # ⚠ CLOSED-LOOP ON THE OUTCOME, NOT THE ACK. The step acking only means the engine did not
        # throw; what matters is that the HUD stopped asking this slot, which is what SendNetCommand
        # achieves by adding it to InputFinishList. If the command had been refused, the slot would
        # NOT be in that list and the HUD would re-open its menu -- so this wait is exactly the
        # difference between "a command was sent" and "the turn was taken".
        self.wait_for(lambda s: s.turn_slot != slot or s.battle_result != 0 or not s.in_battle,
                      timeout=timeout,
                      what=f"slot {slot} to stop being asked for a command")
        return {"slot": slot, "command": what, "id": cmd, "sub": sub,
                "target": tname, "target_id": tar_id, "cursor": cursor}

    def _resolve_command(self, st, menu: dict, name: str, slot: int):
        """Name -> (commandId, sub, targetType, forDead, label). Raises with the real menu on a miss."""
        row = st.command(name)
        if row is not None:
            # ⚠ `offered` FIRST. A command can be both a sub-menu and one the HUD would not draw --
            # an ability command with nothing learned is precisely that -- and "the HUD would not
            # draw it" is the answer that stops the reader hunting for abilities that do not exist.
            if not row.get("offered", True):
                raise HarnessError(
                    f"{name!r} resolves for this character but the HUD would not draw it "
                    f"(no learned abilities, or a menu outside the ordinary six). Commanding it "
                    f"would be a claim about a move the player never had.")
            if int(row.get("type", -1)) == 1:
                subs = [a.get("name") for a in menu.get("abilities", [])
                        if a.get("menu") == row.get("menu")]
                raise HarnessError(
                    f"{name!r} is a sub-menu, not a move: name the ability itself. "
                    f"It offers {subs or 'nothing this character has learned'}.")
            return (int(row["id"]), int(row["sub"]), int(row.get("target", -1)),
                    bool(row.get("for_dead")), row.get("name") or name)

        ab = st.ability(name)
        if ab is not None:
            parent = next((c for c in menu.get("commands", [])
                           if c.get("menu") == ab.get("menu")), None)
            if parent is None:
                raise HarnessError(
                    f"{name!r} is in menu {ab.get('menu')} but no command claims that menu; the "
                    f"published menu is inconsistent, which should not happen -- re-run `menus`.")
            if not ab.get("enabled", True):
                raise HarnessError(
                    f"{name!r} is learned but not castable right now (no MP, silenced, or its "
                    f"supporting ability is off). The HUD greys it; committing it anyway would "
                    f"test a path the player cannot reach.")
            return (int(parent["id"]), int(ab["sub"]), int(ab.get("target", -1)),
                    bool(ab.get("for_dead")), f"{parent.get('name')}/{ab.get('name') or name}")

        it = st.item(name)
        if it is not None:
            parent = next((c for c in menu.get("commands", []) if c.get("menu") == 4), None)
            if parent is None:
                raise HarnessError(f"{name!r} is in the inventory but this character has no Item "
                                   f"command in battle.")
            return (int(parent["id"]), int(it["sub"]), int(it.get("target", -1)),
                    bool(it.get("for_dead")), f"{parent.get('name')}/{it.get('name') or name}")

        raise HarnessError(
            f"slot {slot} has no move called {name!r}. Commands: "
            f"{[c.get('name') for c in menu.get('commands', []) if c.get('offered')]}; "
            f"abilities: {[a.get('name') for a in menu.get('abilities', [])]}; "
            f"items: {[i.get('name') for i in menu.get('items', [])]}.")

    def _resolve_target(self, st, slot: int, target, ttype: int, for_dead: bool):
        """Pick who this lands on, and the cursor group that makes it legal.

        ``tar_id`` is a BITMASK of ``btl_id``s, not an index -- each unit's ``id`` is already the
        single bit for its slot, so a group target is those bits OR'd together.
        """
        units = st.units()
        me = next((u for u in units if int(u.get("slot", -1)) == slot), None)

        if isinstance(target, str):
            hit = st.unit(target)
            if hit is None:
                raise HarnessError(
                    f"no combatant called {target!r}; this battle has "
                    f"{[u.get('name') for u in units]}")
            return int(hit["id"]), 0, hit.get("name") or target
        if isinstance(target, int):
            hit = next((u for u in units if int(u.get("slot", -1)) == target), None)
            if hit is None:
                raise HarnessError(f"no combatant in slot {target}")
            return int(hit["id"]), 0, f"slot {target} ({hit.get('name')})"

        # ⚠ A FORCED-GROUP ABILITY CANNOT TAKE ONE TARGET. The engine's own cursor for TargetType
        # All/AllAlly/AllEnemy/Everyone is the group, and passing a single bit would be a command
        # the UI could never produce.
        if ttype in self._GROUP_TARGETS:
            want_player = ttype in (7,)
            side = [u for u in units
                    if u.get("alive") and u.get("targetable")
                    and (ttype in (6, 12) or bool(u.get("player")) is want_player)]
            if not side:
                raise HarnessError("nothing alive and targetable to aim a group command at")
            mask = 0
            for u in side:
                mask |= int(u["id"])
            return mask, self._GROUP_TARGETS[ttype], f"all ({len(side)})"

        if for_dead:
            dead = [u for u in units if u.get("player") and not u.get("alive")]
            if dead:
                return int(dead[0]["id"]), 0, dead[0].get("name") or "a fallen ally"

        if ttype in self._ALLY_TARGETS:
            hurt = sorted((u for u in units if u.get("player") and u.get("alive")),
                          key=lambda u: (int(u.get("hp", 0)) * 1000) // max(1, int(u.get("hp_max", 1))))
            if hurt:
                return int(hurt[0]["id"]), 0, hurt[0].get("name") or "an ally"
        if ttype < 0:
            # Defend and Change take no target; the UI passes the caster's own id.
            if me is not None:
                return int(me["id"]), 0, "self"

        foes = [u for u in units
                if not u.get("player") and u.get("alive") and u.get("targetable")]
        if foes:
            return int(foes[0]["id"]), 0, foes[0].get("name") or "an enemy"
        if me is not None:
            return int(me["id"]), 0, "self (nothing hostile left standing)"
        raise HarnessError("no legal target: the unit list is empty")

    def fight(self, *, command: str = "Attack", target: str | int | None = None,
              policy=None, timeout: float = 300.0, max_turns: int = 120,
              finish: bool = True) -> int:
        """Play the battle through to a RESULT, and return the result code.

        The default policy is the same one a bored player uses: attack the first enemy left
        standing, every turn. Pass ``policy(state, slot) -> dict`` for anything else; return
        ``None`` from it to pass this prompt back to the loop (it will be asked again).

        ⚠ It refuses the diorama outright rather than timing out inside it: under ``isDebug`` the
        engine suppresses the auto-end, so that fight can NEVER finish and every turn taken there
        proves nothing about a result.

        A battle TUTORIAL screen (the Masked Man's scene 336) is closed when it shows (:meth:`_dismiss_tutorial`).

        NO RESULT within the bounds raises :class:`FightTimeout` (a HarnessError: research/o3_design.md H7), its
        ``kind`` the bound that ran out -- "turns": ``max_turns`` command prompts answered (0 raises at the FIRST
        prompt, before any command: a fight stopped mid-battle by construction) -- or "timeout". A battle scene that
        GOES with no result before either bound runs out (a soft reset or a crash to the title mid-fight, an engine
        path that leaves the result 0) raises it with ``kind`` "gone" and its own message: no bound ran out, so
        ``timed_out`` is False and a caller that owns the bounds must not read it as one (the review, 11.7 #2).
        Either way, and on a result, :attr:`last_fight` records what the call did: ``turns``, ``result``, ``name``,
        ``epoch``, and ``seconds`` (wall time from the call), ``tutorials`` (screens this call closed) and
        ``timed_out``.
        """
        self._require_play_protocol("fight()")
        t0 = time.time()
        st = self.state
        # ⚠ THE DIORAMA CHECK COMES FIRST, and that ordering is the whole point: `in_battle` is
        # already false for a diorama by design, so a debug check placed below it can never run.
        # The generic "call start_battle first" would then be the answer to standing inside a
        # battle scene that simply cannot end -- true, and pointing at the wrong thing entirely.
        if st.battle.get("debug"):
            raise HarnessError(
                "this battle is running with isDebug set (a diorama). The engine suppresses the "
                "auto-end there, so it can never reach a result -- playing it out would time out "
                "having proved nothing.")
        if not st.in_battle:
            raise HarnessError("fight() needs a real battle in progress; call start_battle first")
        epoch = st.battle_epoch
        deadline = time.time() + timeout
        turns = tutorials = 0
        gone = False                        # the loop broke on the scene going with no result, not on a bound

        def record(result: int, timed_out: bool) -> None:
            # ⚠ RECORDED, because "it ended in victory" does not say the loop ever ran. The first live
            # run of this verb reported a clean victory having taken ZERO turns -- the single Attack
            # issued beforehand had already killed the only enemy, so the multi-turn path was untested
            # while the report looked complete. A scenario that means to exercise the loop asserts on
            # this; without it there is nothing to assert on. Both no-result exits record it too (H7).
            self.last_fight = {"turns": turns, "result": result,
                               "name": State.BATTLE_RESULTS.get(result, str(result)),
                               "epoch": epoch, "seconds": round(time.time() - t0, 3), "tutorials": tutorials,
                               "timed_out": timed_out}
        while time.time() < deadline:
            self._assert_alive()
            st = self.state
            if st.battle_epoch == epoch and (st.battle_result != 0 or not st.in_battle):
                gone = st.battle_result == 0
                break
            if st.ui_state == "Tutorial":
                if self._dismiss_tutorial():
                    tutorials += 1
                continue
            if st.turn_slot < 0:
                # Nobody is being asked: the enemies are acting, or an animation is playing. Not a
                # failure -- wait for the next prompt or for the fight to end.
                try:
                    self.wait_for(
                        lambda s: (s.turn_slot >= 0 or s.battle_result != 0 or not s.in_battle
                                   or s.ui_state == "Tutorial"),
                        timeout=min(10.0, max(0.5, deadline - time.time())),
                        what="the next turn or an outcome")
                except HarnessError:
                    pass
                continue
            if turns >= max_turns:
                record(st.battle_result, True)
                raise FightTimeout(
                    f"took {turns} turns without reaching a result. Either the party cannot hurt "
                    f"this enemy or something is healing it faster than {command!r} lands -- the "
                    f"roster is in the last state snapshot.", kind="turns")
            slot = st.turn_slot
            choice = {"command": command, "target": target}
            if policy is not None:
                picked = policy(st, slot)
                if picked is None:
                    self.wait_frames(10)
                    continue
                choice = dict(choice, **picked)
            try:
                self.act(choice["command"], slot=slot, target=choice.get("target"))
            except StepRefused as err:
                # The sample said "asking slot N" and the step landed after the HUD stopped asking: a scripted end
                # (the Masked Man's RunBattleCode after enough damage) or the next intro. Measured, story-o1e run 1.
                # Not a turn taken and not a failure: read the state again.
                if "not asking for commands" not in err.error:
                    raise
                self._log(f"  fight: the step for slot {slot} landed after the HUD stopped asking; reading again")
                self.wait_frames(10)
                continue
            turns += 1
        result = self.state.battle_result
        if result == 0 and gone:
            # the scene went with no result while time was left: no bound ran out (the review, 11.7 #2)
            record(0, False)
            self._log(f"fight: {turns} turn(s) -> the battle scene went away with no result")
            raise FightTimeout(
                f"the battle scene went away with no result after {time.time() - t0:.1f}s ({turns} turn(s) taken), "
                f"before its {timeout:.0f}s / {max_turns} turn bounds ran out", kind="gone")
        record(result, result == 0)
        self._log(f"fight: {turns} turn(s) -> {State.BATTLE_RESULTS.get(result, result)}")
        if result == 0:
            raise FightTimeout(
                f"the battle did not reach a result within {timeout:.0f}s ({turns} turn(s) taken)", kind="timeout")
        if finish:
            self.leave_battle()
        return result

    def leave_battle(self, *, timeout: float = 90.0, stop_on_field: bool = False) -> str:
        """Get past the battle-result screen and back to whatever comes after the fight.

        The result screen wants a confirm (sometimes several: spoils, level-ups, learned abilities),
        and a defeat goes to the Game Over menu instead, which no amount of confirming leaves. Both
        outcomes are reported rather than one of them hanging.

        ``stop_on_field`` (research/o3_design.md H8): before each Confirm, a sample with the battle scene GONE (not
        ``in_battle``, whatever ``ui_state`` still reads -- it lags as BattleResult while the next field loads) or
        the field HUD up stops the loop: never a Confirm into a loading field, or onto its first windows. The default
        is the loop as it always was. Either way :attr:`last_leave` records every press -- ``{"frame", "ui",
        "in_battle", "field", "result"}`` of the sample it was decided on -- and where the loop ended: ``ended`` (the
        UI state, which is also returned), ``field``, ``frame``, and ``stopped``: "field" (the stopping sample showed
        the field HUD), "scene-gone" (the battle scene gone, the field not up yet), "presses" (the Confirms ran out) or
        "timeout": ``timeout`` (wall seconds from the call) ran out, checked before each Confirm and after the field
        test -- a caller with a deadline bounds the loop by it (the review, research/o3_design.md 11.7 #1; the
        default 90 s outlasts the 40 Confirms at any normal frame rate, so a caller that passes none sees the loop as
        it always was).
        """
        presses: list = []
        stopped = "presses"
        deadline = time.time() + float(timeout)
        st = self.state
        for _ in range(40):
            self._assert_alive()
            st = self.state
            if (stop_on_field and (not st.in_battle or st.ui_state == "FieldHUD")) or (
                    not st.in_battle and st.ui_state not in ("BattleHUD", "BattleResult")):
                stopped = "field" if st.ui_state == "FieldHUD" else "scene-gone"
                break
            if time.time() >= deadline:
                stopped = "timeout"
                break
            presses.append({"frame": st.frame, "ui": st.ui_state, "in_battle": st.in_battle, "field": st.field_id,
                            "result": st.battle_result})
            self.press("confirm", 4)
            self.wait_frames(20)
        st = self.state
        self.last_leave = {"presses": presses, "ended": st.ui_state, "field": st.field_id, "frame": st.frame,
                           "stopped": stopped}
        self._log(f"  leave_battle: ui={st.ui_state} field={st.field_id} "
                  f"result={st.battle_result_name} presses={len(presses)} stopped={stopped}")
        return st.ui_state

    def flag(self, bit: int, value: bool = True) -> None:
        self._check_flag_bit(bit, "flag")
        self.send(f"flag {int(bit)} {1 if value else 0}")

    def poke(self, index: int, value: int) -> None:
        """Write one raw ``gEventGlobal`` byte."""
        self.send(f"byte {int(index)} {int(value)}")

    def watch(self, *bits: int) -> None:
        """Publish these story-flag bits in every subsequent state sample."""
        for bit in bits:
            self._check_flag_bit(bit, "watch")
        self.send("watch " + " ".join(str(int(b)) for b in bits))

    def unwatch(self) -> None:
        """Stop publishing watched bits -- part of resetting between scenarios."""
        self.send("unwatch")

    # -- co-op (netsync) benches ------------------------------------------------------------
    #: The protocol that turned the ~ menu's IMGUI bench buttons into verbs.
    NETSYNC_PROTOCOL = 5

    def netsync(self, sub: str, *args, timeout: float = 20.0) -> State:
        """Drive the co-op client's solo benches -- the ~ menu's IMGUI buttons, as verbs.

        ``selftest 1|0`` forces the selftest role for THIS process (Memoria.ini untouched; released
        on disarm, fault and ``reset``), ``bench 1|0`` is the F1 field-gate lever, ``l1 1|0`` the
        host-event flag the L2 lockstep engages under, ``advance`` / ``choice <index>`` inject one
        host frame against the frontmost open window, and ``unmatched`` a frame no window can match
        (the DialogWaitMs timeout proof). Returns a fresh state so the caller can read ``netsync``
        straight after.

        Refuses on an engine that predates the verbs: an older agent answers ``unknown op`` only
        AFTER the step is sent, which is a worse message and a wasted step.
        """
        if self.engine_protocol is not None and self.engine_protocol < self.NETSYNC_PROTOCOL:
            raise HarnessError(
                f"netsync: the deployed engine speaks protocol {self.engine_protocol}; the co-op "
                f"bench verbs need protocol {self.NETSYNC_PROTOCOL} (s83 rev 5). Rebuild the DLL."
            )
        self.send("netsync " + " ".join([str(sub), *(str(a) for a in args)]), timeout=timeout)
        return self.state

    # -- the story-write trace (memoria-patch s88) ---------------------------------------------
    def storytrace(self, on: bool = True, *, timeout: float = 10.0) -> State:
        """Start (``on``) or stop the engine's story-write trace: every ``gEventGlobal`` store, with the
        script position that made it, appended to ``story.jsonl`` beside events.jsonl (the row contract:
        studies/story-trace/PLAN.md). Starting writes an ``arm`` epoch; stopping flushes the suppressed
        counts and an ``off`` epoch. Arming the harness resets the tracer to off, so a run traces only
        from here. Returns the state that shows the change.

        Refuses unless ``state.json`` ADVERTISES the trace at the proto this driver reads: an older engine
        answers ``unknown op`` only after the step, and a trace it never wrote would read as "no script
        wrote anything" -- the one wrong answer this instrument must never give.

        ⚠ STOPPING PROVES THE FILE WHOLE, or raises. ``on`` going false is not enough: a tracer that
        FAULTED (``storytrace.error``) is already off, wrote no ``off``, and its file stops at the fault;
        and the engine appends once per frame, keeping rows buffered while the file is locked. So a stop
        returns only once story.jsonl holds exactly the ``rows`` the engine counted since the arm --
        raising on a fault, on rows that never landed, and on rows this arm never wrote.
        """
        from ff9mapkit.storytrace import PROTO

        cap = self.state.storytrace
        if cap is None:
            raise HarnessError(
                "storytrace: the deployed engine publishes no `storytrace` block -- it predates the story "
                "trace (memoria-patch s88). Rebuild the DLL.")
        if cap.get("proto") != PROTO:
            raise HarnessError(
                f"storytrace: the engine writes trace proto {cap.get('proto')}, this driver reads proto "
                f"{PROTO} -- update the one that is behind rather than read rows by guesswork.")
        on = bool(on)
        self.send(f"storytrace {1 if on else 0}", timeout=timeout)
        st = self.wait_for(lambda s: s.storytrace is not None and bool(s.storytrace.get("on")) == on,
                           timeout=timeout, what=f"the story trace to turn {'on' if on else 'off'}")
        if on:
            self._story_starts += 1
            return st
        return self._story_settled(st, timeout)

    def _story_settled(self, st: State, timeout: float) -> State:
        """After ``storytrace 0``: no hook writes while the tracer is off, so the published ``rows`` (every
        row since the arm -- a harness ``reset`` stops the trace but keeps counting) is final. Wait for the
        file to catch up to it, exactly."""
        deadline = time.time() + timeout
        while True:
            _raise_if_story_faulted(st)
            want = st.storytrace.get("rows")
            if isinstance(want, bool) or not isinstance(want, int):
                raise HarnessError(f"storytrace: the engine publishes no row count ({want!r}) -- not proto 1")
            have = _story_lines(self.channel.story_text())
            if have == want:
                return st
            if have > want:
                raise HarnessError(
                    f"storytrace: story.jsonl holds {have} rows but the engine wrote {want} since the arm -- "
                    f"{have - want} are another arm's (a leaked run's tail landing after the reset), so this "
                    f"file is not this run's trace")
            if time.time() >= deadline:
                raise HarnessError(
                    f"storytrace: {want - have} of the {want} rows the engine wrote never reached story.jsonl "
                    f"within {timeout:.0f}s -- the trace is incomplete")
            time.sleep(0.02)
            st = self.state

    def story_rows(self) -> list:
        """The live trace's rows so far, parsed and VALIDATED by the kit (``ff9mapkit.storytrace.Row``).

        An append in flight (an unterminated last line) waits for the next read; any complete line that
        breaks the contract raises, and so does a tracer that FAULTED -- its rows stop at the fault, and
        "so far" would read as "all". Refuses before :meth:`storytrace` started a trace in this session:
        no file then means "never traced", not "nothing was written".
        """
        from ff9mapkit.storytrace import TraceError, parse_text

        if not self._story_starts:
            raise HarnessError("story_rows: no story trace was started in this session -- call "
                               "storytrace() first. An absent story.jsonl is not 'no writes'.")
        _raise_if_story_faulted(self.state)
        text = self.channel.story_text()
        if text is None:
            return []
        try:
            return parse_text(text, live=True)
        except TraceError as err:
            raise HarnessError(f"story.jsonl breaks the row contract: {err}") from err

    def story_mark(self) -> tuple:
        """Where the trace stands -- ``(traces started, traced runs in story.jsonl)`` -- for
        :meth:`collect_story`. A suite takes it before each member runs."""
        return (self._story_starts, len(self._story_arm_lines()))

    def collect_story(self, dest: Path, mark: tuple) -> int:
        """Hand one member its own trace: if it started one since ``mark``, close it (verified, as
        :meth:`storytrace` does), then write the traced runs story.jsonl gained since ``mark`` to ``dest``.
        Returns how many (0: it traced nothing, and no file is written).

        The runs are written even when the close raises -- a cut run is still evidence, and the kit's
        reader marks it INCOMPLETE on its own -- and the close's error is re-raised after.
        """
        starts, runs = mark
        if self._story_starts == starts:
            return 0
        failure: HarnessError | None = None
        try:
            self.storytrace(False)
        except HarnessError as err:
            failure = err
        text = self.channel.story_text() or ""
        arms = self._story_arm_lines(text)
        if len(arms) > runs:
            body = "\n".join(text.split("\n")[arms[runs] - 1:])
            dest = Path(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(body[:body.rfind("\n") + 1], encoding="utf-8")   # complete lines only
        if failure is not None:
            raise failure
        return max(0, len(arms) - runs)

    def _story_arm_lines(self, text: str | None = None) -> list:
        """The 1-based line of every ``arm`` epoch in story.jsonl -- one per traced run."""
        from ff9mapkit.storytrace import TraceError, parse_text

        if text is None:
            text = self.channel.story_text()
        try:
            return [r.line for r in parse_text(text or "", live=True) if r.k == "e" and r.why == "arm"]
        except TraceError as err:
            raise HarnessError(f"story.jsonl breaks the row contract: {err}") from err

    def _close_story_trace(self) -> None:
        """Teardown's ``storytrace 0``, with its proof that the file is whole. ⚠ BEFORE the quit and the
        disarm: with no ``quit`` (keep_open, attach) the agent stops the trace only when it NOTICES the
        disarm, up to 30 frames after a collect that runs at once -- a file with no counts, no ``off`` and
        none of the last frames. Never raises (the disarm outranks the trace); a trace that is not whole
        is said loudly here, and the kit's reader marks the run INCOMPLETE on its own."""
        if not self._story_starts or (self.proc is not None and self.proc.poll() is not None):
            return
        try:
            self.storytrace(False, timeout=5.0)
        except Exception as err:                           # noqa: BLE001 - teardown
            self._log(f"!! the story trace did not close whole: {err}")

    def _check_flag_bit(self, bit: int, verb: str) -> None:
        # ⚠ A NEGATIVE BIT CORRUPTS THE STATE CHANNEL, not just this call. The agent's bound test is
        # `(n >> 3) < length`, and -1 >> 3 is -1 in C# too, so it passes -- then the array read
        # throws AFTER the key's comma is already in the document buffer, the catch does not roll
        # back, and every state.json from then on is invalid JSON. The driver reads that as "the
        # agent never published state" and concludes the deployed engine is unpatched. Refuse here.
        if not 0 <= int(bit) <= self.MAX_FLAG_BIT:
            raise HarnessError(
                f"{verb}: story-flag bit {bit} is outside gEventGlobal (0..{self.MAX_FLAG_BIT}). "
                f"Allocate from 8712 up -- 8512-8711 is stock read-mail payload and 8376-8511 is the "
                f"MOGNET lock band."
            )

    def control(self, enabled: bool = True) -> None:
        self.send(f"control {1 if enabled else 0}")

    def timescale(self, scale: float) -> None:
        """Speed the game up (or slow it down) -- a long walk need not cost real seconds.

        ⚠ NOT zero. At `Time.timeScale == 0` the engine runs zero LOGICAL ticks while the agent's
        frame-count scheduling keeps advancing on render frames: presses open and close, waits
        elapse, every step acks -- against a game that executed nothing. Nothing about that is
        distinguishable from success.
        """
        scale = float(scale)
        if scale <= 0.0:
            raise HarnessError(
                "timescale 0 pauses the game's logic while the harness keeps counting render "
                "frames, so every step would ack having done nothing. Use a small positive scale."
            )
        self.send(f"timescale {scale}")

    def state_every(self, frames: int) -> None:
        """Frames between state publications. Lower = finer traces, higher = less overhead."""
        self.send(f"stateevery {max(1, int(frames))}")

    def note(self, text: str) -> None:
        self.send("note " + text.replace("\n", " "))

    def shot(self, name: str, *, timeout: float = 60.0) -> Path:
        """Capture a frame from inside the engine. Returns the PNG path once it is on disk.

        The name is sanitised BEFORE it is sent, so the file the agent writes and the file this
        polls for are the same one. They used to diverge on any name containing a space -- the
        request line is split on whitespace, so ``shot("after chest")`` reached the agent as
        ``after``, and the wait then blamed the in-engine capture for a name the driver mangled.
        """
        name = _sanitize(f"{self.shot_prefix}-{name}" if self.shot_prefix else name)
        self.send(f"shot {name}", timeout=timeout)
        path = self.channel.shots / f"{name}.png"
        deadline = time.time() + 10
        while time.time() < deadline:
            if path.exists() and path.stat().st_size > 0:
                self._log(f"shot {path.name}")
                return path
            time.sleep(0.05)
        raise HarnessError(f"the screenshot {name} never appeared at {path}")

    def reset_agent(self) -> None:
        """Release every held button and clear the agent's per-run scratch state.

        The isolation primitive. ``hold`` is non-blocking and frame-counted, so a scenario that
        raises mid-hold leaves a button DOWN into whatever runs next -- and the agent only clears
        buttons on an arm transition. Falls back to explicit releases on an engine without the verb.
        """
        try:
            self.send("reset")
        except HarnessError:
            for button in ("up", "down", "left", "right", "confirm", "cancel", "menu", "special"):
                try:
                    self.send(f"release {button}")
                except HarnessError:
                    pass
            self.unwatch()
            self.timescale(1.0)

    # -- isolation between scenarios ------------------------------------------------------------
    # A suite runs many scenarios through ONE launch, which is only worth doing if a scenario that
    # leaves the game in a menu, mid-battle, mid-dialogue or on a black screen cannot poison the
    # next one. Everything here is about reaching a KNOWN state and then PROVING we reached it.

    #: The six buttons FF9's own soft reset watches (L1+L2+R1+R2+Start+Select).
    SOFT_RESET_BUTTONS = ("l1", "l2", "r1", "r2", "start", "select")

    def soft_reset(self, *, timeout: float = 45.0, frames: int = 8) -> State:
        """Return to the title screen from ANYWHERE, using the game's own soft reset.

        FF9's handler closes every dialog, hides the HUD, disables all button groups and the battle
        menu, un-pauses, normalises `btl_seq`, and replaces the scene with Title.

        ⚠ IT DOES NOT ESCAPE AN OPEN MENU, and that was measured rather than reasoned. An earlier
        version of this docstring claimed it reached "a battle, a stuck menu or a black screen"; the
        engine says otherwise and so does the game. `UIKeyTrigger.Update` runs
        `if (HandleMenuControlKeyPressCustomInput()) return;` BEFORE the soft-reset check, and that
        handler consumes `Control.Select` unconditionally (`:688`) -- note the neighbouring Pause
        branch (`:681`) IS guarded with `&& !SoftResetKeyPSXForPause`, so the authors protected the
        combo from one branch and not the other. Measured with
        `scenarios/soft_reset_reach.py`: from a FIELD, YES; from an open MainMenu, NO.

        That is why :meth:`restore_baseline` closes open UI FIRST. Nothing about a ladder works if a
        rung's reach is assumed.

        ⚠ ALL SIX BUTTONS MUST REPORT `IsInputDown` ON THE SAME FRAME, which is why they go in ONE
        request: every step of a request is drained in a single pass, so all six are scheduled with
        the same `_downFrame` and their Down edges coincide. Six separate `press` calls would never
        overlap, and the reset would simply never fire.

        ⚠ It is gated on `[Control] SoftReset` in Memoria.ini -- 1 on this install, but the ENGINE
        default is 0. So this asserts on the outcome (the title screen actually arriving) rather
        than returning and letting the caller assume it worked.
        """
        steps = [f"hold {b} {frames}" for b in self.SOFT_RESET_BUTTONS]
        self.send(*steps, f"wait {frames + 4}")
        try:
            st = self.wait_for(lambda s: s.ui_state == "Title", timeout=timeout,
                               what="the soft reset to return to the title screen")
        except HarnessError as err:
            raise HarnessError(
                f"the soft reset did not reach the title. Either `[Control] SoftReset` is 0 in "
                f"Memoria.ini (the engine default -- this needs it on), or the game is no longer "
                f"responding to input at all. ({err})"
            ) from err
        self._sleep_alive(0.5)          # let the scene transition finish before anyone acts on it
        return st

    def close_ui(self, *, attempts: int = 6, timeout: float = 20.0) -> State:
        """Back out of whatever is open until the game is on a field or the world map.

        THE RUNG THE SOFT RESET CANNOT BE. `UIKeyTrigger` swallows the soft-reset combo inside any
        menu (measured -- see :meth:`soft_reset`), and a scenario is far more likely to end in a menu
        or a dialogue than anywhere else, so a ladder without this step would poison every scenario
        after one that left the menu open. `warp` is no help either: it refuses outside FieldHUD.

        Cancel is the right key precisely BECAUSE the menu handler consumes it -- that is what backs
        a screen out. It stops as soon as the game is somewhere a soft reset works from.
        """
        for _ in range(attempts):
            st = self.channel.state()
            if st is None:
                break
            if st.ui_state in ("FieldHUD", "WorldHUD", "Title") and not st.dialog_open:
                return st
            self.press("cancel", 4)
            self.wait_frames(12)
        return self.wait_for(
            lambda s: s.ui_state in ("FieldHUD", "WorldHUD", "Title") and not s.dialog_open,
            timeout=timeout,
            what="the open menu or dialogue to close so a soft reset can be delivered")

    def at_baseline(self) -> tuple[bool, str]:
        """Is the game in the state a scenario is entitled to assume? Returns ``(ok, why)``.

        The baseline is the TITLE SCREEN, because every scenario in this arc opens with `newgame()`
        and that verb requires it. Checked rather than assumed: the entire point of a ladder is that
        each rung is verified.
        """
        # Rides out a stalled publish: a single miss read as "not at the baseline" climbs the ladder
        # for nothing, and on the final re-check it poisons a scenario that was ready to run.
        st = self._read_state()
        if st is None:
            return False, f"no state published -- {self.channel.classify()}"
        # ⚠ FRESHNESS FIRST. Every predicate below is satisfied just as well by the last document a
        # HUNG agent left behind, so without this the one rung whose entire job is verification is a
        # check that cannot fail: a dead game whose final state happened to say Title was certified
        # "at the title, idle", the scenario was launched against a corpse, and it was then filed as
        # `error` -- the runner blaming the game for the runner's own dead channel.
        if st.age is not None and st.age > LIVE_WITHIN:
            return False, f"the newest state is {st.age:.1f}s old -- {self.channel.classify()}"
        # Fault before disarm: a faulted agent also disarms itself, so testing `armed` first reported
        # every fault as a plain stand-down and threw away the error that explained it.
        if st.raw.get("faulted"):
            return False, f"the agent faulted: {st.error}"
        if st.armed is False:
            return False, "the agent has disarmed"
        if st.ui_state != "Title":
            return False, f"ui_state is {st.ui_state!r}, not Title"
        if st.held:
            return False, f"buttons still held: {st.held}"
        if st.dialog_open:
            return False, "a dialogue box is still open"
        try:
            scale = float(st.raw.get("timescale", 1.0))
        except (TypeError, ValueError):
            scale = 1.0
        if abs(scale - 1.0) > 0.01:
            return False, f"timescale is {scale}, not 1.0"
        return True, "at the title, idle"

    def restore_baseline(self) -> tuple[bool, str]:
        """Climb the recovery ladder until :meth:`at_baseline` agrees, one rung at a time.

        Every rung is followed by a RE-CHECK of the precondition rather than an assumption that it
        worked, and it escalates exactly one rung on failure.

        The caller decides what happens when the ladder runs out, and the right answer is to VOID
        the next scenario rather than fail it: a scenario that never ran cannot have failed, and
        recording it as a failure would be the harness blaming the game for its own inability to
        clean up. Given this arc's history, the runner's default must be to blame itself.
        """
        ok, why = self.at_baseline()
        if ok:
            return True, "already at the baseline"

        rungs = [
            ("release the harness's own state", self.reset_agent),
            # ⚠ BEFORE the soft reset, not after: the combo is swallowed inside any menu, so this is
            # the only rung that can get out of one -- and a menu is where scenarios end.
            ("close whatever UI is open", self.close_ui),
            ("soft reset to the title", self.soft_reset),
        ]
        troubles = []
        for name, rung in rungs:
            try:
                rung()
            except HarnessError as err:
                # Keep it: when the ladder runs out, THIS is the diagnosis. Reporting only the final
                # at_baseline complaint describes the symptom and discards the cause.
                troubles.append(f"{name}: {err}")
                self._log(f"  restore: {name} failed ({err})")
                continue
            ok, why = self.at_baseline()
            if ok:
                return True, f"restored by: {name}"
        detail = f"the ladder did not restore the baseline: {why}"
        if troubles:
            detail += " | rung failures: " + " ;; ".join(troubles)
        return False, detail

    # -- artifacts ------------------------------------------------------------------------------
    # Everything here is allowed to fail and nothing here may raise into the run: an artifact is
    # worth less than the disarm, less than the verdict, and less than the step it describes.

    #: Failed checks that get the ring flushed AND photographed, per scenario. Beyond it the check
    #: row says so ("shot_skipped"), because a scenario that fails forty checks does not need forty
    #: photographs of the same screen and a suite cannot afford them.
    FAILURE_EVIDENCE_CAP = 3
    #: A failure shot against a game that is still alive but slow must not cost the default 60 s.
    SHOT_TIMEOUT_ON_FAILURE = 8.0

    def _artifact_dir(self) -> Path:
        d = self.scenario_dir if self.scenario_dir is not None else self.run_dir
        d.mkdir(parents=True, exist_ok=True)
        return d

    def scenario_dir_for(self, label: str) -> Path:
        """Where a suite member's artifacts live -- ONE sanitiser for the directory, the shot prefix
        and the collect glob, so a label with a colon in it cannot lose its own evidence."""
        return self.run_dir / _sanitize(label)

    def bind_artifacts(self, label: str, *, phase: str = "run") -> Path:
        """Route steps, rings and evidence to a member's own directory from this moment on.

        The runner calls it BEFORE the recovery ladder with ``phase="baseline"``, so the ladder's
        steps and a POISONED ring land under the member they were spent on -- not under the
        previous one, and not at the run level where nobody would look.
        """
        self.scenario_dir = self.scenario_dir_for(label)
        self._phase = phase
        self._evidence = 0
        self._last_failure_frame = None
        return self.scenario_dir

    def unbind_artifacts(self) -> None:
        """Back to run-level routing (the quit row and the final ring belong to the run)."""
        self.scenario_dir = None
        self._phase = "run"

    def _ledger(self, row: dict) -> None:
        ok = self._steps.append(self.run_dir / "steps.jsonl", row)
        if self.scenario_dir is not None:
            ok = self._steps.append(self.scenario_dir / "steps.jsonl", row) and ok
        if ok:
            self._steps_logged += 1
            return
        self._steps_dropped += 1
        if self._steps_dropped == 1:
            self._log("!! steps.jsonl could not be written -- the step ledger for this run is incomplete")

    def states_since(self, frame: int) -> list[dict]:
        """The raw states the ring holds (every read the harness made keeps its sample: the last STATE_RING distinct
        frames, ~10-20 s) with a frame after ``frame``, oldest first (research/o2_design.md H6). A driver that takes
        the frame before a call reads, after it, every sample the call's own waits read -- a race lost inside a walk
        stays on record."""
        return self._ring.since(int(frame))

    def flush_states(self, tag: str) -> Path | None:
        """Write the ring (the last ~10 s of published state, ~20 at 31 fps) as ``states-<tag>.jsonl``. Never raises."""
        path = self._artifact_dir() / f"states-{_sanitize(tag)}.jsonl"
        try:
            n = self._ring.dump(path)
        except Exception as err:                           # noqa: BLE001 - an artifact, not the run
            self._log(f"  (could not write {path.name}: {err})")
            return None
        self._log(f"  {path.name} ({n} sample(s))")
        return path

    def evidence(self, tag: str) -> dict:
        """Flush the ring, then photograph -- under the cap, and only against a LIVE game.

        The ring goes first: a shot's own send/ack polls push newer frames into it, so flushing
        after the photograph would describe a moment after the failure. The shot is skipped, with
        the reason on the row, when the cap is reached, the channel is stale (a hung game would
        cost the whole ack timeout for a picture of nothing new), the game has exited, or the frame
        is the one already photographed.
        """
        out: dict = {"states": None, "shot": None, "shot_skipped": None}
        if self._evidence >= self.FAILURE_EVIDENCE_CAP:
            out["shot_skipped"] = f"cap of {self.FAILURE_EVIDENCE_CAP} per scenario reached"
            return out
        self._evidence += 1
        path = self.flush_states(tag)
        out["states"] = path.name if path is not None else None
        st = self.channel.state()
        if st is None or (st.age is not None and st.age > LIVE_WITHIN):
            out["shot_skipped"] = (f"channel stale"
                                   f"{'' if st is None else f' ({st.age:.1f}s)'}: {self.channel.classify()}")
            return out
        # (An exited game needs no gate of its own: shot() -> send() asserts the process is alive
        # before writing a request, and that refusal lands in shot_skipped below -- a second gate
        # here was a check that could not fail, proven by breaking it.)
        if st.frame == self._last_failure_frame:
            out["shot_skipped"] = f"same frame ({st.frame}) as the previous failure shot"
            return out
        try:
            shot = self.shot(tag, timeout=self.SHOT_TIMEOUT_ON_FAILURE)
            out["shot"] = shot.name
            self._last_failure_frame = st.frame
        except Exception as err:                           # noqa: BLE001 - see the section comment
            out["shot_skipped"] = f"could not photograph: {err}"
        return out

    def write_env(self, **extra) -> Path | None:
        """Write (or rewrite, merged) ``env.json``. Never raises; says so in the log if it cannot."""
        self._env_extra.update(extra)
        try:
            doc = build_env(self, **self._env_extra)
            path = self.run_dir / "env.json"
            path.write_text(json.dumps(doc, indent=2, default=str), encoding="utf-8")
            return path
        except Exception as err:                           # noqa: BLE001 - an artifact, not the run
            self._log(f"env.json not written ({err})")
            return None

    def _artifact_index(self) -> dict:
        try:
            states = sorted(p.name for p in self._artifact_dir().glob("states-*.jsonl"))
        except Exception:                                  # noqa: BLE001
            states = []
        return {"steps": "steps.jsonl", "env": "env.json", "states": states}

    def begin_scenario(self, label: str) -> None:
        """Start a fresh scenario on this session: clear checks, namespace its screenshots."""
        # FIRST, so the reset/note sends below are the new member's first rows, not the old one's last.
        self.bind_artifacts(label, phase="run")
        self.checks = []
        self.shot_prefix = label
        # ⚠ The agent's error latch is per-request on the engine side, but the DRIVER also keeps the
        # last one it saw to attribute blame. Carried across a scenario boundary it makes one
        # scenario's refusal raise against the next scenario's first innocent step.
        self._last_error = None
        # A basis is per-field AND per-scenario: the previous scenario may have left the character
        # somewhere its probes were deflected, and a cached bad basis steers every later walk.
        self._axes.clear()
        # ⚠ And the last fight's record. battle_play asserts `last_fight["turns"] >= 1`; carried
        # across the boundary, a member whose fight() raised before recording anything would be
        # judged on the PREVIOUS member's fight and pass. Its leave's record likewise.
        self.last_fight = None
        self.last_leave = None
        # `reset_agent` is documented as the isolation primitive and was only ever reached as a
        # RECOVERY rung -- so on the happy path (the previous scenario ended tidily) held buttons,
        # a stale watch list and a changed timescale carried straight into the next member. Run it
        # unconditionally: that is what makes it a primitive rather than a fallback.
        self.reset_agent()
        self.note(f"scenario {label}")
        self._ledger({"kind": "scenario", "t": time.time(),
                      "at": _dt.datetime.now().isoformat(timespec="milliseconds"), "scenario": label})

    def quit(self, *, timeout: float = 15.0) -> None:
        """Ask the game to exit, and wait for it.

        ⚠ Never fire-and-forget. Disarming clears the agent's queue, so a bare non-blocking ``quit``
        followed by teardown can have its step discarded before the agent ever runs it -- leaving a
        game running that the run believes it closed.
        """
        self.send("quit", wait=False)
        if self.proc is None:
            return
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                return
            time.sleep(0.1)
        raise HarnessError(f"the game did not exit within {timeout:.0f}s of a quit request")

    # -- asserting ------------------------------------------------------------------------------
    def check(self, ok: bool, description: str, detail: str = "") -> bool:
        """Record a pass/fail. Non-fatal -- the run continues so one scenario reports every failure.

        Every check carries a snapshot of the game AT THE MOMENT IT WAS MADE, and the first failure
        of a scenario is photographed automatically. Both exist for one reason: inside a suite,
        re-running to find out what the screen looked like costs the whole suite.
        """
        row = {"ok": bool(ok), "what": description, "detail": detail}
        try:
            st = self.channel.state()
            if st is not None:
                row["state"] = {
                    "frame": st.frame, "ui_state": st.ui_state, "field": st.field_id,
                    "pos": [st.player_x, st.player_z], "control": st.control,
                    "dialog": st.dialog_open, "held": st.held,
                }
        except Exception:                              # never let bookkeeping break a check
            pass
        # Join keys: which request this check followed, and when -- so a reader can find the row in
        # steps.jsonl and the sample in the ring without matching by order.
        row["at"] = _dt.datetime.now().isoformat(timespec="milliseconds")
        row["seq"] = self.channel.seq
        self.checks.append(row)
        self._log(f"  {'PASS' if ok else 'FAIL'}  {description}" + (f"  [{detail}]" if detail else ""))
        if not ok and self._shot_on_failure:
            # The snapshot above is the ring's newest sample; evidence() flushes BEFORE it photographs.
            row.update(self.evidence(f"FAILED-{self._evidence + 1}"))
        self._ledger({"kind": "check", "t": time.time(), "at": row["at"],
                      "scenario": self.scenario_dir.name if self.scenario_dir is not None else None,
                      "ok": bool(ok), "what": description, "seq": row["seq"],
                      "frame": (row.get("state") or {}).get("frame"),
                      "shot": row.get("shot"), "states": row.get("states")})
        return bool(ok)

    def expect(self, predicate, description: str, *, timeout: float = 10.0) -> bool:
        """Wait for a condition and record it as a check rather than raising."""
        try:
            st = self.wait_for(predicate, timeout=timeout, what=description)
            return self.check(True, description, repr(st))
        except HarnessError as err:
            return self.check(False, description, str(err))

    def expect_field(self, field: int, *, timeout: float = 30.0) -> bool:
        return self.expect(lambda s: s.field_id == int(field), f"on field {field}", timeout=timeout)

    def expect_text(self, fragment: str, *, timeout: float = 10.0) -> bool:
        """Assert that the dialogue on screen contains ``fragment``.

        ⚠ An empty fragment is refused. ``"" in anything`` is true, so ``expect_text("")`` passed
        with no dialogue on screen at all -- an assertion that cannot fail is worse than no
        assertion, because it goes into report.json as evidence.
        """
        if not fragment or not fragment.strip():
            raise HarnessError("expect_text needs a non-empty fragment: '' matches everything, "
                               "including an empty screen.")
        needle = fragment.lower()
        return self.expect(lambda s: s.dialog_open and needle in s.text.lower(),
                           f"dialogue contains {fragment!r}", timeout=timeout)

    def expect_flag(self, bit: int, value: bool = True, *, timeout: float = 10.0) -> bool:
        """Assert a watched story-flag bit.

        ⚠ An UNWATCHED bit publishes nothing, and ``None is False`` is False -- so asking about a
        bit nobody watched recorded ``FAIL flag N is False`` for a flag that genuinely was False.
        The bit is auto-watched here rather than mis-reported.
        """
        self._check_flag_bit(bit, "expect_flag")
        if self.state.flag(bit) is None:
            self.watch(bit)
            try:
                self.wait_for(lambda s: s.flag(bit) is not None, timeout=3.0,
                              what=f"flag {bit} to start being published")
            except HarnessError as err:
                return self.check(False, f"flag {bit} is {value}",
                                  f"the agent never published bit {bit} after watch() ({err})")
        return self.expect(lambda s: s.flag(bit) is value,
                           f"flag {bit} is {value}", timeout=timeout)

    @property
    def passed(self) -> bool:
        """Whether every recorded check passed. ⚠ A run with NO checks has not passed anything."""
        return bool(self.checks) and all(c["ok"] for c in self.checks)

    def _report_rate(self) -> dict:
        """The measured rate as the run ended (Rate.as_dict; ``source`` "default" when nothing was measured), for
        report.json -- beside :attr:`rate_changes`, every move of it the run saw."""
        self._note_rate()
        return self._clock.rate().as_dict()

    def _write_report(self, failed: bool) -> None:
        import json
        # ⚠ UNDER A SUITE THIS FILE MUST NOT CARRY A VERDICT. `self.checks` is rebound per scenario
        # by `begin_scenario`, so a whole-run verdict computed from it describes only the LAST member
        # -- and a ten-scenario suite whose first nine failed wrote `"passed": true` under the exact
        # filename this tool documents as the run's report. suite.json is the authority there; this
        # points at it rather than contradicting it.
        if self._suite_owned:
            report = {
                "label": self.label,
                "when": _dt.datetime.now().isoformat(timespec="seconds"),
                "game_path": str(self.game_path),
                "attached": self.attach,
                "raised": failed,
                "verdict": "see suite.json",
                "note": ("this run was a SUITE -- per-scenario verdicts are in suite.json and in each "
                         "<NN>-<name>/report.json. The session's own check list belongs to whichever "
                         "scenario ran last and is deliberately not scored here."),
                "driver_protocol": PROTOCOL,
                "engine_protocol": self.engine_protocol,
                "artifacts": self._artifact_index(),
                "steps_recorded": self._steps_logged,
                "steps_dropped": self._steps_dropped,
                "rate": self._report_rate(),
                "rate_changes": self.rate_changes,
            }
            (self.run_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            return

        # THREE outcomes, not two. A run that recorded nothing proved nothing, and calling that
        # "passed": true is the purest form of the failure this whole audit is about -- play.py
        # already refuses to call it a pass, and report.json used to say the opposite.
        if failed:
            verdict = "fail"
        elif not self.checks:
            verdict = "proved-nothing"
        else:
            verdict = "pass" if self.passed else "fail"
        report = {
            "label": self.label,
            "when": _dt.datetime.now().isoformat(timespec="seconds"),
            "game_path": str(self.game_path),
            "attached": self.attach,
            "raised": failed,
            "verdict": verdict,
            # The engine that was actually driven. A green run against an OLDER channel is green
            # under caveats (raw dialogue source, no choice index space, silent world refusals), and
            # a report that does not say so invites the result to be read as unconditional.
            "driver_protocol": PROTOCOL,
            "engine_protocol": self.engine_protocol,
            "checks_recorded": len(self.checks),
            "passed": verdict == "pass",
            "artifacts": self._artifact_index(),
            "steps_recorded": self._steps_logged,
            "steps_dropped": self._steps_dropped,
            # the render rate every press was sized and judged by -- a frame count in a record means nothing without it
            "rate": self._report_rate(),
            "rate_changes": self.rate_changes,
            "checks": self.checks,
        }
        (self.run_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[harness] {msg}", flush=True)


def _button(name: str) -> str:
    key = str(name).lower()
    if key not in BUTTONS:
        raise HarnessError(f"unknown button {name!r}; known: {', '.join(sorted(BUTTONS))}")
    return key


def _vec(v) -> str:
    return f"({v[0]:+.2f}, {v[1]:+.2f})"


def _game_seconds(st: State | None) -> float | None:
    """The GAME'S clock at ``st``, in seconds: its published ``rt`` (the fake game; a future engine) where there is one,
    else the state file's mtime (today's engine writes it once a publish) -- None when neither can be read. What a wait
    for something counted on the game's clock (the tick clock's arrival second) is bounded by, not the wall."""
    if st is None:
        return None
    rt = st.raw.get("rt")
    if isinstance(rt, (int, float)) and not isinstance(rt, bool):
        return float(rt)
    return st.mtime


def _press_axis(basis: dict, dx: float, dz: float):
    """The button walk_to presses to cover world offset (dx, dz): the calibrated axis the offset projects
    onto more. Returns ``(button, need, axis, sign)`` -- ``axis * sign`` is the world direction pressed."""
    along_v = dx * basis["v"][0] + dz * basis["v"][1]
    along_h = dx * basis["h"][0] + dz * basis["h"][1]
    if abs(along_v) >= abs(along_h):
        return ("up" if along_v > 0 else "down"), abs(along_v), basis["v"], (1.0 if along_v > 0 else -1.0)
    return ("right" if along_h > 0 else "left"), abs(along_h), basis["h"], (1.0 if along_h > 0 else -1.0)


def _eight_way(basis: dict) -> list:
    """The eight directions a pad presses on a calibrated basis, ``[(buttons, (ux, uz))]``: each axis alone, and
    each pair at once -- the engine normalises a two-key press before rotating it (FieldMapActorController.cs:
    698-712), so a pair walks the unit bisector of its two axes, at the speed one key does."""
    out = []
    for sv, vb in ((1.0, "up"), (0.0, None), (-1.0, "down")):
        for sh, hb in ((1.0, "right"), (0.0, None), (-1.0, "left")):
            if vb is None and hb is None:
                continue
            x = sv * basis["v"][0] + sh * basis["h"][0]
            z = sv * basis["v"][1] + sh * basis["h"][1]
            m = (x * x + z * z) ** 0.5
            out.append((tuple(b for b in (vb, hb) if b), (x / m, z / m)))
    return out


def _turn(u, angle: float) -> tuple[float, float]:
    """Unit ``u`` turned by ``angle`` radians in the XZ plane."""
    import math
    c, s = math.cos(angle), math.sin(angle)
    return (u[0] * c - u[1] * s, u[0] * s + u[1] * c)


def _nearest_on_seg(p, a, b) -> tuple[float, float]:
    """The point of segment a->b nearest ``p`` (XZ)."""
    dx, dz = b[0] - a[0], b[1] - a[1]
    n = dx * dx + dz * dz
    t = 0.0 if n == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / n))
    return (a[0] + t * dx, a[1] + t * dz)


def _into_zone(here, zone, depth: float) -> tuple[float, float]:
    """A point ``depth`` inside ``zone`` for someone standing outside it: past the point of its boundary nearest
    ``here``, straight on (toward the corner average when he stands on the boundary itself)."""
    n = len(zone)
    q = min((_nearest_on_seg(here, zone[i], zone[(i + 1) % n]) for i in range(n)),
            key=lambda c: (c[0] - here[0]) ** 2 + (c[1] - here[1]) ** 2)
    dx, dz = q[0] - here[0], q[1] - here[1]
    if dx * dx + dz * dz < 1e-6:
        dx = sum(c[0] for c in zone) / n - here[0]
        dz = sum(c[1] for c in zone) / n - here[1]
    m = (dx * dx + dz * dz) ** 0.5 or 1.0
    return (q[0] + dx / m * depth, q[1] + dz / m * depth)


def _sanitize(name: str) -> str:
    return "".join(c if (c.isalnum() or c in "-_.") else "_" for c in name) or "shot"


def _raise_if_story_faulted(st: State) -> None:
    """A tracer that FAULTED (StoryTrace.Fail) turned itself off with no ``off`` row: its file stops at the
    fault, and reading it as a whole run turns every later write into "never written"."""
    err = (st.storytrace or {}).get("error")
    if err:
        raise HarnessError(
            f"storytrace: the tracer FAULTED and turned itself off ({err}) -- story.jsonl stops at the fault "
            f"with no `off` epoch, so every write after it is missing, not absent. Re-arm to trace again.")


def _story_lines(text: str | None) -> int:
    """Complete (newline-terminated) rows in a story.jsonl body -- an append in flight is not one yet."""
    return sum(1 for ln in (text or "").split("\n")[:-1] if ln.strip())
