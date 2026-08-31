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

from .channel import BUTTONS, PROTOCOL, Channel, HarnessError, State   # noqa: E402

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

#: A published document this recent counts as a LIVE game talking. The agent republishes ~30x/second,
#: so anything older is a photograph -- and a photograph satisfies most predicates just as well as a
#: running game does.
LIVE_WITHIN = 2.0

#: Stock FF9 field ids, read once from reference/field-manifest.tsv. `DictionaryPatch.txt` lists only
#: MOD registrations, so a membership test against it alone refuses all ~674 shipping rooms with a
#: false claim about a null `.eb`.
_STOCK_FIELDS: set[int] | None = None


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
        self._axes: dict[int, dict] = {}      # field id -> measured button->world basis
        self._last_error: str | None = None   # the agent's error latch as of the last successful ack
        self.engine_protocol: int | None = None   # what the DEPLOYED engine speaks, once it answers
        #: Prefix stamped onto every screenshot name. A suite sets it per scenario, because two
        #: scenarios both capturing "walk-before" otherwise overwrite each other's evidence in the
        #: one channel directory -- and the evidence you lose is always the failing run's.
        self.shot_prefix = ""
        #: Whether this session has ever reached a field. The title settle exists because Memoria is
        #: still LOADING the first time the title appears; on a re-entry (after a soft reset) it is
        #: pure dead time, and in a suite it is dead time once per scenario.
        self._booted_once = False
        #: One automatic screenshot per scenario, at its FIRST failure -- the moment worth seeing.
        self._shot_on_failure = True
        self._failure_shot_taken = False
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
        # instantly. With nothing running there is no observer, so the wait is skipped.
        self.channel.arm(force_cycle=bool(running))
        # The arm file gates a shared install: if this process dies without running stop(), the next
        # session's game silently boots with the harness live. __exit__ is not enough -- a bare
        # sys.exit or an unhandled raise outside the with-block skips it.
        atexit.register(self._atexit_disarm)
        self._log(f"channel {self.channel.dir}")

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
        """
        st = self.channel.state()
        if st is None:
            return
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
                f"worldwarp/teleport ack clean. Rebuild the DLL before trusting a text assertion."
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
        would fail to catch is silently overwriting the owner's game.
        """
        st = self.channel.state()
        if st is None:
            return
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
                for step in (lambda: self.channel.collect(self.run_dir),
                             self._collect_log,
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
        log = self.engine_log()
        if log is None:
            return
        try:
            shutil.copy2(log, self.run_dir / "Memoria.log")
        except OSError:
            pass

    def _log_hint(self) -> str:
        return f"Check {self.run_dir / 'Memoria.log'} once the run ends."

    # -- sending --------------------------------------------------------------------------------
    def send(self, *steps: str, wait: bool = True, timeout: float = 60.0) -> None:
        """Queue raw protocol steps and (by default) block until the game has finished them."""
        seq = self.channel.send(list(steps), alive=self._assert_alive)
        if not wait:
            return
        self._await_ack(seq, timeout, steps)

    def _await_ack(self, seq: int, timeout: float, steps) -> None:
        """Wait for the agent to finish OUR request -- proven by its own receipt, not by a number.

        ⚠ ``ack`` alone is not proof. It is a single counter on a component that outlives every
        scene, and after a leaked arm file it still carries a dead run's value; every step then
        "succeeds" in milliseconds having done nothing, and the first verb that measures the world
        reports a confident falsehood about the game. Requiring the published ``seq`` to have reached
        ours as well means the agent has demonstrably ACCEPTED this request, not merely finished
        something.
        """
        deadline = time.time() + timeout
        last: State | None = None
        while time.time() < deadline:
            self._assert_alive()
            last = self.channel.state()
            if last is not None and last.seq >= seq and last.ack >= seq and not last.busy:
                self._raise_if_this_step_failed(last, seq, steps)
                self._last_error = last.error
                return
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
                raise HarnessError(f"the game refused a step: {st.error} (steps={list(steps)})")
            return
        if st.error != self._last_error:
            raise HarnessError(f"the game refused a step: {st.error} (steps={list(steps)})")

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
    #: Engine log lines that explain a failure better than any driver-side symptom can.
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

    def diagnose(self, lines: int = 60, *, max_age: float = 300.0,
                 window: float = 30.0) -> str | None:
        """Explain a hang from the engine's own log, rather than from driver-side symptoms.

        A driver only ever sees "state stopped arriving", which looks identical whether the game
        crashed, black-screened on a bad warp, or was merely slow -- the least useful of those to be
        told. The log usually says what happened one line earlier.

        Refuses to speak from a STALE log: a marker older than `max_age` describes some previous run,
        and a confidently wrong diagnosis costs more than none at all.
        """
        log = self.engine_log()
        if log is None:
            return None
        try:
            if time.time() - log.stat().st_mtime > max_age:
                return None
            tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
        except OSError:
            return None
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

        for marker, explanation in self._LOG_MARKERS:
            if any(marker in line for line in recent):
                return f"{explanation} (from {log})"
        return None

    @property
    def state(self) -> State:
        st = self.channel.state()
        if st is None:
            self._assert_alive()          # a dead game should say so, not blame the arming
            hint = self.diagnose()
            raise HarnessError(
                f"no state published -- {self.channel.classify()}"
                + (f" -- {hint}" if hint else "")
            )
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

    # -- going somewhere ------------------------------------------------------------------------
    # `walk(direction, frames)` is a poor primitive and measurement says so: on the 30801 bench the
    # character runs at 30 units/frame, so a 75-frame hold "should" cover 2250 units -- and covered
    # 1014, because he reached the edge of the walkmesh and stopped. Open-loop frame counts encode a
    # distance nobody measured, saturate silently against geometry, and bake in a constant that is
    # wrong on the next field. Everything below is closed-loop against the published position.

    #: World units per frame, measured on 30801 (studies/test-harness/scenarios/calibrate_movement.py).
    #: Used only to SIZE a burst; every move is still verified against the real position afterwards, so
    #: a field where these are wrong costs an extra iteration rather than a wrong answer.
    RUN_SPEED = 30.0
    WALK_SPEED = 15.0

    #: A probe that covers less than this fraction of what was COMMANDED did not measure free
    #: movement. An absolute floor cannot tell "he walked 40 units freely" from "he was pushed 40
    #: units along a wall while 900 were asked for".
    PROBE_MIN_FRACTION = 0.35

    def distance_to(self, x: float, z: float) -> float:
        st = self._require_field("distance_to")
        if st.player_x is None:
            raise HarnessError("no player position published -- not on a field?")
        return ((st.player_x - x) ** 2 + (st.player_z - z) ** 2) ** 0.5

    def calibrate_axes(self, *, probe: int = 4, recalibrate: bool = False) -> dict:
        """Discover which BUTTON moves the character which way in WORLD space, on this field.

        This cannot be hard-coded. FF9 fields are viewed by a fixed camera that is frequently yawed,
        and movement is expressed in screen space (`FF9StateSystem.Field.twist`), so "up" is +z on one
        field, -x on another, and something diagonal on a third. A `walk_to` that assumed a mapping
        would work on the bench and quietly walk the wrong way in real rooms.

        So: press each axis briefly, measure the actual world displacement, and keep the basis. If a
        probe barely moves -- the usual cause is standing against a wall -- it retries the opposite
        direction and negates, which is why this is a probe and not a single press.
        """
        st = self._require_field("calibrate_axes")
        key = st.field_id
        if not recalibrate and key in self._axes:
            return self._axes[key]

        # Probe BOTH directions of each axis and cross-check them. A single probe cannot tell free
        # movement from a slide: pressed into a wall at an angle the engine keeps the character
        # moving, just not where he was sent, and the resulting unit vector is a perfectly
        # well-formed lie. The opposite press is the control -- free movement is antiparallel and of
        # similar length; a slide is neither.
        basis, detail = {}, {}
        for name, (fwd, back) in (("v", ("up", "down")), ("h", ("right", "left"))):
            a = self._probe_axis(fwd, probe)
            b = self._probe_axis(back, probe)
            if a is None and b is None:
                raise HarnessError(
                    f"could not calibrate the {name} axis on field {key}: neither {fwd} nor {back} "
                    f"moved the character more than {self.PROBE_MIN_FRACTION:.0%} of the "
                    f"{probe * self.RUN_SPEED:.0f} units commanded. Is he boxed in, or is control "
                    f"withheld?"
                )
            if a is not None and b is not None:
                anti = -(a[0][0] * b[0][0] + a[0][1] * b[0][1])      # +1 when truly opposite
                ratio = min(a[1], b[1]) / max(a[1], b[1])
                if anti < 0.85 or ratio < 0.5:
                    raise HarnessError(
                        f"the {name} axis on field {key} is not a free axis: {fwd} measured "
                        f"{_vec(a[0])} over {a[1]:.0f}u and {back} measured {_vec(b[0])} over "
                        f"{b[1]:.0f}u (antiparallel={anti:+.2f}, length ratio={ratio:.2f}). The "
                        f"character is sliding along something rather than walking. Move to clearer "
                        f"ground and recalibrate."
                    )
                vec, reach = a[0], min(a[1], b[1])
            elif a is not None:
                vec, reach = a[0], a[1]
            else:
                vec, reach = (-b[0][0], -b[0][1]), b[1]
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

    def _probe_axis(self, direction: str, frames: int):
        """Hold one direction briefly; return ``((ux, uz), magnitude)``, or None if it did not move.

        "Did not move" is judged against what was COMMANDED, not against an absolute floor. The old
        15-unit floor accepted a character shoved a few units sideways by a wall as a real
        measurement of that axis, cached the resulting basis, and then steered every later walk_to
        along the wall -- reporting the field as unreachable.
        """
        before = self.state
        self.walk(direction, frames)
        self.wait_frames(6)
        after = self.state
        if before.player_x is None or after.player_x is None:
            return None
        if after.field_id != before.field_id:
            raise HarnessError(
                f"probing {direction} left field {before.field_id} for {after.field_id} -- the probe "
                f"walked into a gateway. Calibrate somewhere with room around the character."
            )
        dx, dz = after.player_x - before.player_x, after.player_z - before.player_z
        mag = (dx * dx + dz * dz) ** 0.5
        if mag < frames * self.RUN_SPEED * self.PROBE_MIN_FRACTION:
            return None
        return ((dx / mag, dz / mag), mag)

    def walk_to(self, x: float, z: float, *, tolerance: float = 40.0, max_bursts: int = 24,
                strict: bool = True) -> bool:
        """Walk to a world (x, z), steering on the published position. Returns whether it arrived.

        Moves one axis at a time rather than solving a diagonal: the engine's diagonal is a single
        normalised vector split across both axes, so treating them independently converges in the same
        number of round trips without the trigonometry, and each leg is independently verifiable.

        The last leg deliberately drops to walk speed (Cancel held). At 30 units/frame a single run
        frame overshoots any tolerance tighter than ~32 units, so a run-only approach oscillates around
        the target forever and then fails on max_bursts.

        Gives up early when a burst produces no progress -- that is a wall or a walkmesh edge, and
        retrying it 24 times just turns a clear failure into a slow one.
        """
        # A tolerance under one WALK frame cannot be aimed for -- the smallest correction the engine
        # can make is one frame of travel, so the loop oscillates around the target and then fails on
        # max_bursts, reporting the field unreachable when the request was impossible.
        if tolerance < self.WALK_SPEED:
            raise HarnessError(
                f"tolerance {tolerance} is below the physical floor: one walk frame covers "
                f"{self.WALK_SPEED} units, so nothing closer than that can be aimed for."
            )
        basis = self.calibrate_axes()
        field = self.state.field_id
        stalls = 0
        for _ in range(max_bursts):
            st = self.state
            # Walking somewhere can END the field: step into a gateway and the destination is
            # loading, so there is no position to steer by. The first version treated that as an
            # error and then did arithmetic on None anyway, so a probe that successfully found a
            # gateway crashed the run instead of reporting it. Leaving the field is a legitimate
            # outcome of walking -- stop cleanly and let the caller notice.
            if st.field_id != field or st.player_x is None:
                return False
            dx, dz = x - st.player_x, z - st.player_z
            remaining = (dx * dx + dz * dz) ** 0.5
            if remaining <= tolerance:
                return True

            # Project the remaining offset onto each measured axis, and drive the bigger one.
            along_v = dx * basis["v"][0] + dz * basis["v"][1]
            along_h = dx * basis["h"][0] + dz * basis["h"][1]
            if abs(along_v) >= abs(along_h):
                direction, need = ("up" if along_v > 0 else "down"), abs(along_v)
                axis, sign = basis["v"], (1.0 if along_v > 0 else -1.0)
            else:
                direction, need = ("right" if along_h > 0 else "left"), abs(along_h)
                axis, sign = basis["h"], (1.0 if along_h > 0 else -1.0)

            slow = need < self.RUN_SPEED * 3
            speed = self.WALK_SPEED if slow else self.RUN_SPEED
            frames = max(1, min(45, int(need / speed)))
            steps = [f"hold {direction} {frames}"]
            if slow:
                steps.insert(0, f"hold cancel {frames}")
            self.send(*steps, f"wait {frames + 4}")

            after = self.state
            if after.field_id != field or after.player_x is None:
                return False          # the burst carried us out of the field -- see above
            mx, mz = after.player_x - st.player_x, after.player_z - st.player_z
            moved = (mx * mx + mz * mz) ** 0.5

            # THE BASIS CONSISTENCY CHECK. Calibration can be fooled -- a character pressed into a
            # wall keeps moving, just not where he was sent, and the resulting basis is a well-formed
            # lie that no static test on two unit vectors can catch. What a bad basis cannot fake is
            # agreement over time: if a burst covers a real distance in a direction that does not
            # project onto the axis it was sent along, the basis is wrong and every later burst is
            # steering by it. Say so, and throw the basis away, instead of grinding out max_bursts
            # and then blaming the field's geometry.
            if moved >= self.WALK_SPEED:
                projected = (mx * axis[0] + mz * axis[1]) * sign
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
        for patch in sorted(self.game_path.glob("*/DictionaryPatch.txt")):
            try:
                text = patch.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            read.append(patch)
            for m in re.finditer(r"^\s*FieldScene\s+(\d+)\s+(\d+)\s+(\S+)", text, re.MULTILINE):
                found[int(m.group(1))] = m.group(3)
            # Tolerate a two-column form rather than dropping the id entirely.
            for m in re.finditer(r"^\s*FieldScene\s+(\d+)\s+([A-Za-z_]\S*)", text, re.MULTILINE):
                found.setdefault(int(m.group(1)), m.group(2))
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

    def expect_field_change(self, *, timeout: float = 25.0, was: int | None = None) -> int:
        """Wait for the field id to change and return the new one.

        Waits for the destination to be PLAYABLE, not merely for the id to flip. The id changes the
        moment the engine accepts the transition, while the destination is still black -- and a
        scenario that continued there would issue its next steps into a loading screen.

        ⚠ The two waits are deliberately NOT merged, and callers must not swallow them together.
        "The field never changed" and "the field changed but the destination never handed over
        control" are opposite findings: the first means there is no gateway here, the second means
        there is one and it leads somewhere broken. Collapsing them reported a working gateway as a
        missing one.
        """
        was = self.state.field_id if was is None else was
        self.wait_for(lambda s: s.field_id != was and s.field_id > 0,
                      timeout=timeout, what=f"the field to change from {was}")
        landed = self.state.field_id
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
            tx, tz = home[0] + radius * math.sin(angle), home[1] + radius * math.cos(angle)
            record = self.cross(tx, tz, timeout=timeout)
            if record["landed"] is not None:
                found.append({"bearing": bearing, "toward": record["toward"],
                              "field": record["landed"], "travelled": record["travelled"]})
                self._log(f"transition on bearing {bearing}deg -> field {record['landed']}")
                self.warp(home_field)
                self.wait_frames(45)
                # The home point is FROZEN at the sweep's start: re-reading it after each warp made
                # every later bearing radiate from wherever the arrival happened to be, so the
                # sweep silently stopped being a circle.
                self.walk_to(home[0], home[1], tolerance=60, strict=False)
            else:
                if not record["reached"] and record["travelled"] < 0.5 * radius:
                    unswept.append(f"{bearing}deg (covered {record['travelled']:.0f} of {radius:.0f}u)")
                self.walk_to(home[0], home[1], tolerance=60, strict=False)

        if not found and unswept:
            raise HarnessError(
                f"the sweep of field {home_field} found no transitions, but {len(unswept)} of "
                f"{bearings} bearings were never actually walked: {'; '.join(unswept)}. That is 'I "
                f"did not look', not 'there is nothing here' -- move to open ground or lower the "
                f"radius."
            )
        return found

    # -- cutscenes ------------------------------------------------------------------------------

    def wait_control(self, *, timeout: float = 60.0, settle: float | None = None) -> State:
        """Wait until the player has control again. The end of a cutscene, expressed as a condition.

        ⚠ Control FLICKERS true for a moment as a field loads, before the script takes it away --
        so this requires the condition to hold, exactly as `watch_cutscene` does. The two used to
        differ, and the sibling without the settle returned the instant a cutscene began.
        """
        return self._wait_settled(
            lambda s: s.control and s.player_x is not None and not s.fading and not s.dialog_open,
            timeout=timeout, what="control to return to the player", settle=settle)

    def watch_cutscene(self, *, timeout: float = 90.0, advance_boxes: bool = True,
                       settle: float = 1.0) -> list[str]:
        """Sit through a cutscene, collecting its dialogue, until control returns.

        A cutscene is exactly the state a naive harness hangs in: control is withheld, so every
        movement verb silently does nothing and the run dies on an unrelated timeout much later.
        This makes waiting explicit and brings back the transcript, which is the part worth
        asserting on -- by the time control returns the text is gone from the state channel.

        Advances text boxes by default, since many scripted scenes will not proceed without a
        Confirm; pass advance_boxes=False to watch a self-playing scene without touching it.
        """
        pages: list[str] = []
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
                    self.wait_frames(8)
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
        raise HarnessError(
            f"control never returned within {timeout:.0f}s across {len(frames)} live frames -- the "
            f"cutscene is still running, waiting on input this did not send, or has soft-locked. "
            f"Collected {len(pages)} page(s) so far."
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
        """Select option `index` in an open choice dialogue and confirm it."""
        self.select(index, timeout=timeout)
        self.press("confirm", 4)
        self.wait_frames(12)

    #: gEventGlobal is Byte[2048], so bits run 0 .. 16383. See [[project-ff9-story-flags]] for the
    #: SAFE allocation band (8712+) -- this is only the physical range.
    MAX_FLAG_BIT = 2048 * 8 - 1

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

    def shot(self, name: str) -> Path:
        """Capture a frame from inside the engine. Returns the PNG path once it is on disk.

        The name is sanitised BEFORE it is sent, so the file the agent writes and the file this
        polls for are the same one. They used to diverge on any name containing a space -- the
        request line is split on whitespace, so ``shot("after chest")`` reached the agent as
        ``after``, and the wait then blamed the in-engine capture for a name the driver mangled.
        """
        name = _sanitize(f"{self.shot_prefix}-{name}" if self.shot_prefix else name)
        self.send(f"shot {name}")
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
        st = self.channel.state()
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

    def begin_scenario(self, label: str) -> None:
        """Start a fresh scenario on this session: clear checks, namespace its screenshots."""
        self.checks = []
        self.shot_prefix = label
        self._failure_shot_taken = False
        # ⚠ The agent's error latch is per-request on the engine side, but the DRIVER also keeps the
        # last one it saw to attribute blame. Carried across a scenario boundary it makes one
        # scenario's refusal raise against the next scenario's first innocent step.
        self._last_error = None
        # A basis is per-field AND per-scenario: the previous scenario may have left the character
        # somewhere its probes were deflected, and a cached bad basis steers every later walk.
        self._axes.clear()
        # `reset_agent` is documented as the isolation primitive and was only ever reached as a
        # RECOVERY rung -- so on the happy path (the previous scenario ended tidily) held buttons,
        # a stale watch list and a changed timescale carried straight into the next member. Run it
        # unconditionally: that is what makes it a primitive rather than a fallback.
        self.reset_agent()
        self.note(f"scenario {label}")

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
        self.checks.append(row)
        self._log(f"  {'PASS' if ok else 'FAIL'}  {description}" + (f"  [{detail}]" if detail else ""))
        if not ok and self._shot_on_failure and not self._failure_shot_taken:
            self._failure_shot_taken = True
            try:
                self.shot("FAILED")
            except Exception as err:
                self._log(f"  (could not photograph the failure: {err})")
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


def _sanitize(name: str) -> str:
    return "".join(c if (c.isalnum() or c in "-_.") else "_" for c in name) or "shot"
