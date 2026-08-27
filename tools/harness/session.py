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


def ff9_pids() -> list[int]:
    """PIDs of any running FF9. Uses tasklist rather than psutil, which is not a kit dependency."""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq FF9.exe", "/NH", "/FO", "CSV"],
            capture_output=True, text=True, timeout=20,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    pids = []
    for line in out.splitlines():
        parts = [p.strip('" ') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower().startswith("ff9"):
            try:
                pids.append(int(parts[1]))
            except ValueError:
                pass
    return pids


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
        pid_probe=None,
        launcher=None,
    ):
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
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.run_dir = Path(run_dir) if run_dir else RUNS / f"{stamp}-{label}"

    # -- lifecycle ------------------------------------------------------------------------------
    def __enter__(self) -> "Session":
        self.start()
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
                self._log(f"launching {exe}")
                self.proc = subprocess.Popen([str(exe)], cwd=str(exe.parent))
            self._launched = True
        else:
            self._log(f"attaching to pid {running[0]}")

        self._await_agent()

    def _await_agent(self) -> None:
        """Block until the in-game agent publishes its first state."""
        deadline = time.time() + self.boot_timeout
        while time.time() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                raise HarnessError(
                    f"the game exited during boot (code {self.proc.returncode}). "
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
        finally:
            self.channel.collect(self.run_dir)
            self._collect_log()
            self.channel.disarm()
            self._write_report(failed)
            self._log(f"artifacts in {self.run_dir}")

    def _collect_log(self) -> None:
        for candidate in (self.game_path / "x64" / "Memoria.log", self.game_path / "Memoria.log"):
            if candidate.exists():
                try:
                    shutil.copy2(candidate, self.run_dir / "Memoria.log")
                except OSError:
                    pass
                return

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
        return self.wait_for(
            lambda s: s.ui_state == "FieldHUD" and s.control and not s.fading,
            timeout=timeout, what="the player to have control on a field",
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

    def newgame(self, *, timeout: float = 120.0) -> State:
        """Title screen -> New Game -> control on a field."""
        self.wait_for(lambda s: s.ui_state == "Title", timeout=timeout, what="the title screen")
        self.send("newgame")
        return self.wait_playable(timeout=timeout)

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


def _sanitize(name: str) -> str:
    return "".join(c if (c.isalnum() or c in "-_.") else "_" for c in name) or "shot"
