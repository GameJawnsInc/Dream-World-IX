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

import datetime as _dt
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))

from ff9mapkit.config import find_game_path                      # noqa: E402

from .channel import BUTTONS, Channel, HarnessError, State        # noqa: E402

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
    ):
        self.window_size = window_size
        # ``pid_probe`` / ``launcher`` are the test seam. They exist so the offline suite can drive a
        # protocol stand-in without ever resolving, launching or killing the real shared install --
        # the same "pin the path through a seam, never read the real file" rule the deploy tooling
        # learned the hard way. Production leaves both None.
        self._pid_probe = pid_probe or ff9_pids
        self._launcher = launcher
        self.label = label
        self.game_path = Path(game_path) if game_path else find_game_path()
        self.attach = attach
        self.keep_open = keep_open
        self.boot_timeout = boot_timeout
        self.verbose = verbose
        self.channel = Channel(self.game_path)
        self.proc: subprocess.Popen | None = None
        self._launched = False
        self.checks: list[dict] = []
        self._axes: dict[int, dict] = {}      # field id -> measured button->world basis
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

        self.channel.reset()
        self.channel.arm()
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
            self.channel.collect(self.run_dir)
            self._collect_log()
            self.channel.disarm()
            self._write_report(failed)
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
        seq = self.channel.send(list(steps))
        if not wait:
            return
        self._await_ack(seq, timeout, steps)

    def _await_ack(self, seq: int, timeout: float, steps) -> None:
        deadline = time.time() + timeout
        last: State | None = None
        while time.time() < deadline:
            self._assert_alive()
            last = self.channel.state()
            if last is not None and last.ack >= seq and not last.busy:
                if last.error:
                    raise HarnessError(f"the game refused a step: {last.error} (steps={list(steps)})")
                return
            time.sleep(0.02)
        raise HarnessError(
            f"steps {list(steps)} were not acknowledged within {timeout:.0f}s (last state: {last!r})"
        )

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
                "no state published" + (f" -- {hint}" if hint else
                                        " -- the agent is armed but stopped publishing; the game may "
                                        "be hung. Check Memoria.log in the run directory.")
            )
        return st

    def wait_for(self, predicate, *, timeout: float = 20.0, what: str = "condition") -> State:
        """Poll until ``predicate(state)`` is true. Raises with the last state seen on timeout."""
        deadline = time.time() + timeout
        last: State | None = None
        while time.time() < deadline:
            self._assert_alive()
            last = self.channel.state()
            if last is not None:
                try:
                    if predicate(last):
                        return last
                except Exception:            # a predicate reading a field that is null right now
                    pass
            time.sleep(0.03)
        raise HarnessError(f"timed out after {timeout:.0f}s waiting for {what} (last state: {last!r})")

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

    def distance_to(self, x: float, z: float) -> float:
        st = self.state
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
        st = self.state
        key = st.field_id
        if not recalibrate and key in self._axes:
            return self._axes[key]

        basis = {}
        for name, (fwd, back) in (("v", ("up", "down")), ("h", ("right", "left"))):
            vec = self._probe_axis(fwd, probe)
            if vec is None:
                vec = self._probe_axis(back, probe)
                if vec is not None:
                    vec = (-vec[0], -vec[1])
            if vec is None:
                raise HarnessError(
                    f"could not calibrate the {name} axis on field {key}: neither {fwd} nor {back} "
                    f"moved the character. Is he boxed in, or is control withheld?"
                )
            basis[name] = vec

        # A probe can be DEFLECTED rather than blocked -- walk into an NPC at an angle and the engine
        # slides the character along the collision instead of stopping him, so the measured vector is
        # real movement pointing the wrong way. That produces a skewed basis that still "works" and
        # sends every later walk_to off at an angle. Two screen axes should be close to perpendicular,
        # so a large dot product means a probe was pushed and the basis must not be trusted silently.
        skew = abs(basis["v"][0] * basis["h"][0] + basis["v"][1] * basis["h"][1])
        if skew > 0.35:
            raise HarnessError(
                f"axis calibration on field {key} looks deflected: up={_vec(basis['v'])} "
                f"right={_vec(basis['h'])} are not perpendicular (|dot|={skew:.2f}). Something "
                f"(an NPC, a wall) pushed a probe. Move to clearer ground and recalibrate."
            )

        self._axes[key] = basis
        self._log(f"axes on field {key}: up={_vec(basis['v'])} right={_vec(basis['h'])} "
                  f"(perpendicularity |dot|={skew:.2f})")
        return basis

    def _probe_axis(self, direction: str, frames: int):
        """Hold one direction briefly; return the unit world vector it produced, or None if it stalled."""
        before = self.state
        self.walk(direction, frames)
        self.wait_frames(6)
        after = self.state
        if before.player_x is None or after.player_x is None:
            return None
        dx, dz = after.player_x - before.player_x, after.player_z - before.player_z
        mag = (dx * dx + dz * dz) ** 0.5
        if mag < self.RUN_SPEED * 0.5:      # less than half a frame of travel: treat as blocked
            return None
        return (dx / mag, dz / mag)

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
            else:
                direction, need = ("right" if along_h > 0 else "left"), abs(along_h)

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
            moved = ((after.player_x - st.player_x) ** 2 + (after.player_z - st.player_z) ** 2) ** 0.5
            stalls = stalls + 1 if moved < 1.0 else 0
            if stalls >= 2:
                break

        final = self.state
        if final.field_id != field or final.player_x is None:
            return False
        arrived = self.distance_to(x, z) <= tolerance
        if not arrived and strict:
            st = self.state
            raise HarnessError(
                f"could not reach ({x}, {z}): stopped at ({st.player_x}, {st.player_z}), "
                f"{self.distance_to(x, z):.0f} units away. A wall, a walkmesh edge, or an "
                f"unreachable target."
            )
        return arrived

    def newgame(self, *, timeout: float = 120.0, playable: bool = False,
                settle: float = TITLE_SETTLE) -> State:
        """Title screen -> New Game -> in-game.

        Waits for a FIELD to be up, NOT for control. New Game lands in the opening cutscene (stock
        field 70 unless a campaign has re-wired the override), where control is deliberately withheld
        for minutes -- so requiring it here hangs every scenario whose actual intent is "get in-game,
        then warp to the thing I am testing". Pass ``playable=True`` only when the scenario really
        does mean to play from the opening.

        ``settle`` holds on the title screen before starting. Memoria is still loading when the title
        first appears, and starting a new game during that window makes the opening cutscene run
        badly choppy -- which a scenario asserting on cutscene timing would then blame on itself.
        The wait costs nothing on a run that warps away immediately, so it is on by default.
        """
        self.wait_for(lambda s: s.ui_state == "Title", timeout=timeout, what="the title screen")
        if settle > 0:
            self._log(f"settling {settle:.0f}s on the title (Memoria is still loading)")
            self._sleep_alive(settle)
        self.send("newgame")
        st = self.wait_for(lambda s: s.ui_state == "FieldHUD" and s.field_id > 0,
                           timeout=timeout, what="New Game to reach a field")
        return self.wait_playable(timeout=timeout) if playable else st

    def registered_fields(self) -> dict[int, str]:
        """Every field id currently registered by a deployed mod folder, id -> scene name.

        Read from the `DictionaryPatch.txt` of each mod folder, which CLAUDE.md is emphatic is the
        only truth about what is deployed -- it changes as other worktrees deploy, so it is read live
        rather than cached across runs.
        """
        found: dict[int, str] = {}
        for patch in sorted(self.game_path.glob("*/DictionaryPatch.txt")):
            try:
                text = patch.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in re.finditer(r"^\s*FieldScene\s+(\d+)\s+(\S+)", text, re.MULTILINE):
                found[int(m.group(1))] = m.group(2)
        return found

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
        if check_registered:
            available = self.registered_fields()
            if available and field not in available:
                raise HarnessError(
                    f"field {field} is not registered by any deployed mod folder, so warping there "
                    f"would black-screen the game on a null .eb. Deploy it first "
                    f"(`py tools/deploy_field.py <toml> --id {field}`), or use one of: "
                    f"{', '.join(str(i) for i in sorted(available))}."
                )
        self.send(f"warp {field} {entrance if entrance is not None else -1} "
                  f"{scenario if scenario is not None else -1}")
        self.wait_for(lambda s: s.field_id == int(field), timeout=timeout,
                      what=f"field {field} to load")
        return self.wait_playable(timeout=timeout)

    def world_warp(self, field: int, *, entrance: int | None = None,
                   scenario: int | None = None, timeout: float = 60.0) -> State:
        self.send(f"worldwarp {int(field)} {entrance if entrance is not None else -1} "
                  f"{scenario if scenario is not None else -1}")
        return self.wait_for(lambda s: s.field_id == int(field), timeout=timeout,
                             what=f"field {field} to load from the world map")

    def teleport(self, x: float, z: float) -> None:
        """Overworld teleport (world units)."""
        self.send(f"teleport {x} {z}")

    # -- crossing between fields ----------------------------------------------------------------
    # Gateways are the most common mechanic in this project and the hardest to eyeball: a trigger is
    # an invisible region, so "is the gateway where I think it is" has historically been a question
    # only a human walking into it could answer.

    def expect_field_change(self, *, timeout: float = 25.0, was: int | None = None) -> int:
        """Wait for the field id to change and return the new one.

        Waits for the destination to be PLAYABLE, not merely for the id to flip. The id changes the
        moment the engine accepts the transition, while the destination is still black -- and a
        scenario that continued there would issue its next steps into a loading screen.
        """
        was = self.state.field_id if was is None else was
        self.wait_for(lambda s: s.field_id != was and s.field_id > 0,
                      timeout=timeout, what=f"the field to change from {was}")
        return self.wait_playable(timeout=timeout).field_id

    def cross(self, x: float, z: float, *, expect: int | None = None,
              timeout: float = 20.0) -> int | None:
        """Walk to (x, z) and report the field it put us on, or None if we stayed put.

        Returns rather than raises on "nothing happened": when probing for an invisible trigger, not
        crossing is the ordinary outcome and the caller wants to keep looking, not handle an
        exception. Pass `expect` to assert a specific destination.
        """
        origin = self.state.field_id
        self.walk_to(x, z, tolerance=45.0, strict=False)
        try:
            landed = self.expect_field_change(timeout=timeout, was=origin)
        except HarnessError:
            return None
        if expect is not None and landed != expect:
            raise HarnessError(f"crossing at ({x}, {z}) led to field {landed}, expected {expect}")
        return landed

    def find_transitions(self, *, radius: float = 420.0, back_to: int | None = None,
                         bearings: int = 8, timeout: float = 15.0) -> list[dict]:
        """Walk outward on several bearings and report every spot that changed the field.

        Locating an invisible trigger otherwise means asking a human to walk into it. After each
        crossing it warps back and resumes, so one call maps the whole perimeter rather than stopping
        at the first exit found.
        """
        import math

        home_field = self.state.field_id if back_to is None else back_to
        st = self.state
        hx, hz = st.player_x, st.player_z
        found: list[dict] = []

        for i in range(bearings):
            angle = 2 * math.pi * i / bearings
            tx, tz = hx + radius * math.sin(angle), hz + radius * math.cos(angle)
            landed = self.cross(tx, tz, timeout=timeout)
            if landed is not None:
                found.append({"bearing": round(math.degrees(angle)), "toward": [round(tx), round(tz)],
                              "field": landed})
                self._log(f"transition on bearing {round(math.degrees(angle))}deg -> field {landed}")
                self.warp(home_field)
                self.wait_frames(45)
                st = self.state
                hx, hz = st.player_x, st.player_z
            else:
                self.walk_to(hx, hz, tolerance=60, strict=False)
        return found

    # -- cutscenes ------------------------------------------------------------------------------

    def wait_control(self, *, timeout: float = 60.0) -> State:
        """Wait until the player has control again. The end of a cutscene, expressed as a condition."""
        return self.wait_for(lambda s: s.control and s.player_x is not None and not s.fading,
                             timeout=timeout, what="control to return to the player")

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
        while time.time() < deadline:
            self._assert_alive()
            st = self.channel.state()
            if st is None:
                time.sleep(0.05)
                continue
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
        raise HarnessError(
            f"control never returned within {timeout:.0f}s -- the cutscene is still running, waiting "
            f"on input this did not send, or has soft-locked. Collected {len(pages)} page(s) so far."
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
        """
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
        """Press Confirm and report the dialogue it opened, or None if nothing responded.

        Returns rather than raises on silence: "I pressed Confirm here and nothing happened" is a
        legitimate and common finding for a scenario probing where a trigger actually is.
        """
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
        return raw[1:] if len(raw) > 1 else raw

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

    def flag(self, bit: int, value: bool = True) -> None:
        self.send(f"flag {int(bit)} {1 if value else 0}")

    def poke(self, index: int, value: int) -> None:
        """Write one raw ``gEventGlobal`` byte."""
        self.send(f"byte {int(index)} {int(value)}")

    def watch(self, *bits: int) -> None:
        """Publish these story-flag bits in every subsequent state sample."""
        self.send("watch " + " ".join(str(int(b)) for b in bits))

    def control(self, enabled: bool = True) -> None:
        self.send(f"control {1 if enabled else 0}")

    def timescale(self, scale: float) -> None:
        """Speed the game up (or slow it down) -- a long walk need not cost real seconds."""
        self.send(f"timescale {scale}")

    def note(self, text: str) -> None:
        self.send("note " + text.replace("\n", " "))

    def shot(self, name: str) -> Path:
        """Capture a frame from inside the engine. Returns the PNG path once it is on disk."""
        self.send(f"shot {name}")
        path = self.channel.shots / f"{_sanitize(name)}.png"
        deadline = time.time() + 10
        while time.time() < deadline:
            if path.exists() and path.stat().st_size > 0:
                self._log(f"shot {path.name}")
                return path
            time.sleep(0.05)
        raise HarnessError(f"the screenshot {name} never appeared at {path}")

    # -- asserting ------------------------------------------------------------------------------
    def check(self, ok: bool, description: str, detail: str = "") -> bool:
        """Record a pass/fail. Non-fatal -- the run continues so one scenario reports every failure."""
        self.checks.append({"ok": bool(ok), "what": description, "detail": detail})
        self._log(f"  {'PASS' if ok else 'FAIL'}  {description}" + (f"  [{detail}]" if detail else ""))
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
        return self.expect(lambda s: fragment.lower() in s.text.lower(),
                           f"dialogue contains {fragment!r}", timeout=timeout)

    def expect_flag(self, bit: int, value: bool = True, *, timeout: float = 10.0) -> bool:
        return self.expect(lambda s: s.flag(bit) is value,
                           f"flag {bit} is {value}", timeout=timeout)

    @property
    def passed(self) -> bool:
        return all(c["ok"] for c in self.checks)

    def _write_report(self, failed: bool) -> None:
        import json
        report = {
            "label": self.label,
            "when": _dt.datetime.now().isoformat(timespec="seconds"),
            "game_path": str(self.game_path),
            "attached": self.attach,
            "raised": failed,
            "passed": self.passed and not failed,
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
