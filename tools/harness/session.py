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
        # Memoria.log is written relative to the working directory, so it lands at the game root for a
        # normal (and harness) launch but in x64/ for anything started from there. Take the NEWEST of
        # the two rather than a fixed preference -- picking the stale one silently hands you the wrong
        # session's log at exactly the moment you need the right one.
        found = [p for p in (self.game_path / "Memoria.log", self.game_path / "x64" / "Memoria.log")
                 if p.exists()]
        if not found:
            return
        newest = max(found, key=lambda p: p.stat().st_mtime)
        try:
            shutil.copy2(newest, self.run_dir / "Memoria.log")
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
    @property
    def state(self) -> State:
        st = self.channel.state()
        if st is None:
            raise HarnessError("no state published -- is the agent still armed?")
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
        stalls = 0
        for _ in range(max_bursts):
            st = self.state
            if st.player_x is None:
                raise HarnessError("lost the player position mid-walk")
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
            moved = ((after.player_x - st.player_x) ** 2 + (after.player_z - st.player_z) ** 2) ** 0.5
            stalls = stalls + 1 if moved < 1.0 else 0
            if stalls >= 2:
                break

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

    def warp(self, field: int, *, entrance: int | None = None, scenario: int | None = None,
             timeout: float = 60.0) -> State:
        """Warp to a field and wait until it is actually playable."""
        self.send(f"warp {int(field)} {entrance if entrance is not None else -1} "
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
