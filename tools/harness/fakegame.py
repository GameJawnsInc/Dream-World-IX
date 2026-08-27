#!/usr/bin/env python3
"""A protocol stand-in for the in-game agent, so the driver can be tested with no game running.

WHAT THIS PROVES, AND WHAT IT DOES NOT. It implements the s83 wire protocol -- sequence handling,
frame-stepped queue draining, state publication, screenshots, the arm gate -- and nothing else. A
green run against it says the DRIVER is correct: seq numbers advance, acks are awaited properly,
torn reads are survived, timeouts fire, artifacts land. It says NOTHING about whether the engine
patch behaves, whether a warp lands, or whether a button press moves a character. Those are only
ever answered by a real game, and this project has learned repeatedly that a passing offline gate is
a regression harness, not an oracle.

It exists because the alternative is worse: debugging the driver and the engine at the same time,
through a 40-second game launch, with no way to tell which half is lying.
"""
from __future__ import annotations

import json
import struct
import threading
import time
import zlib
from pathlib import Path


class FakeGame:
    """Runs the agent's side of the protocol in a background thread at a simulated frame rate."""

    def __init__(self, game_path: Path, *, fps: float = 120.0, boot_state: str = "Title"):
        self.dir = Path(game_path) / "x64" / "ff9harness"
        self.shots = self.dir / "shots"
        self.fps = fps
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.returncode: int | None = None

        # the simulated world
        self.frame = 0
        self.seq = -1
        self.ack = -1
        self.pending_ack = False
        self.queue: list[list[str]] = []
        self.block_until = 0
        self.held: dict[str, int] = {}
        self.ui_state = boot_state
        self.field_id = -1
        self.player = [0.0, 0.0, 0.0]
        self.control = False
        self.texts: list[str] = []
        self.flags: dict[int, bool] = {}
        self.watch: list[int] = []
        self.error: str | None = None
        self.note = ""
        self.shots_taken = 0

    # -- lifecycle -----------------------------------------------------------------------------
    def start(self) -> "FakeGame":
        self.shots.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    # Popen-compatible surface, so Session can treat this exactly like a launched game.
    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        deadline = time.time() + (timeout or 5)
        while time.time() < deadline:
            if self.returncode is not None:
                return self.returncode
            time.sleep(0.01)
        raise TimeoutError("fake game did not exit")

    def kill(self):
        self.returncode = -9
        self.stop()

    # -- the frame loop ------------------------------------------------------------------------
    def _run(self) -> None:
        period = 1.0 / self.fps
        while not self._stop.is_set() and self.returncode is None:
            self.frame += 1
            try:
                if (self.dir / "arm").exists():
                    self._poll_request()
                    self._drain()
                    self._publish()
            except OSError as err:
                # Mirrors the agent's own try/catch. Without this a single transient sharing
                # violation killed the publisher thread, and every later wait then timed out
                # pointing at the wrong half of the system -- which is exactly how a harness
                # earns a reputation for being flaky when it is actually deterministic.
                self.error = str(err)
            time.sleep(period)

    def _poll_request(self) -> None:
        req = self.dir / "req.txt"
        if not req.exists():
            return
        try:
            lines = req.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        if not lines:
            return
        head = lines[0].split()
        if len(head) < 2 or head[0] != "seq":
            return
        try:
            seq = int(head[1])
        except ValueError:
            return
        if seq <= self.seq:
            return
        self.seq = seq
        self.pending_ack = True
        for line in lines[1:]:
            tok = line.split()
            if tok and not tok[0].startswith("#"):
                self.queue.append(tok)

    def _drain(self) -> None:
        while self.queue and self.frame >= self.block_until:
            step = self.queue.pop(0)
            try:
                self._execute(step)
            except Exception as err:                       # mirrors the agent: report, never die
                self.error = f"{step[0]}: {err}"
        # Persistent latch, not a frame-local "was busy" -- see the matching comment in
        # HarnessAgent.DrainQueue. A blocking final step empties the queue one frame before the block
        # elapses, so a frame-local flag is already false by the time the ack is due.
        if self.pending_ack and not self.queue and self.frame >= self.block_until:
            self.pending_ack = False
            self.ack = self.seq
            self._event("ack", seq=self.ack)

    def _execute(self, step: list[str]) -> None:
        op, args = step[0].lower(), step[1:]

        def num(i, default=0):
            try:
                return int(args[i])
            except (IndexError, ValueError):
                return default

        if op == "wait":
            self._block(num(0, 1))
        elif op == "press":
            self.held[args[0]] = self.frame + num(1, 2)
            self._block(num(1, 2) + 2)
        elif op == "hold":
            self.held[args[0]] = self.frame + num(1, 30)
        elif op == "release":
            self.held.pop(args[0], None)
        elif op == "newgame":
            if self.ui_state != "Title":
                raise RuntimeError("not at the title screen")
            self.ui_state = "FieldHUD"
            self.field_id = 70
            self.control = True
            self._block(3)
        elif op == "warp":
            self.field_id = num(0, -1)
            self.ui_state = "FieldHUD"
            self.control = True
            self._block(3)
        elif op == "worldwarp":
            self.field_id = num(0, -1)
            self._block(3)
        elif op == "teleport":
            self.player = [float(args[0]), 0.0, float(args[1])]
        elif op == "control":
            self.control = num(0, 1) != 0
        elif op == "flag":
            self.flags[num(0, -1)] = num(1, 1) != 0
        elif op == "byte":
            pass
        elif op == "watch":
            self.watch = [int(a) for a in args]
        elif op in ("timescale", "stateevery", "unwatch"):
            pass
        elif op == "shot":
            self._write_png(args[0] if args else "shot")
            self._block(2)
        elif op == "note":
            self.note = " ".join(args)
        elif op == "quit":
            self.returncode = 0
        else:
            raise RuntimeError(f"unknown op '{op}'")

    def _block(self, frames: int) -> None:
        self.block_until = max(self.block_until, self.frame + max(0, frames))

    # -- publication ---------------------------------------------------------------------------
    def _publish(self) -> None:
        held = [b for b, until in self.held.items() if self.frame < until]
        doc = {
            "v": 1, "frame": self.frame, "seq": self.seq, "ack": self.ack,
            "queue": len(self.queue),
            "busy": bool(self.queue) or self.frame < self.block_until,
            "shots": self.shots_taken, "timescale": 1.0, "note": self.note, "error": self.error,
            "ui_state": self.ui_state, "scene": "FieldMap", "fading": False,
            "sys_mode": 1, "scenario": 0,
            "field": {"id": self.field_id, "name": f"FBG_FAKE_{self.field_id}"},
            "world": {"id": -1, "x": None, "z": None, "vehicle": 0},
            "player": {"x": self.player[0], "y": self.player[1], "z": self.player[2],
                       "dir": 0, "floor": 0, "tri": 0, "control": self.control},
            "dialog": {"open": bool(self.texts), "count": len(self.texts),
                       "texts": self.texts, "choice": None},
            "flags": {str(b): bool(self.flags.get(b, False)) for b in self.watch},
            "held": held,
        }
        _publish_atomic(self.dir / "state.json", json.dumps(doc))

    def _event(self, kind: str, **kv) -> None:
        row = {"frame": self.frame, "kind": kind}
        row.update({k: str(v) for k, v in kv.items()})
        with (self.dir / "events.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")

    def _write_png(self, name: str) -> None:
        """A real 1x1 PNG -- the driver checks size>0, and a valid file keeps the artifact dir honest."""
        safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in name) or "shot"
        raw = b"\x00\xff\x00\x00"                                   # one opaque red pixel, filter 0
        png = (b"\x89PNG\r\n\x1a\n"
               + _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
               + _chunk(b"IDAT", zlib.compress(raw))
               + _chunk(b"IEND", b""))
        (self.shots / f"{safe}.png").write_bytes(png)
        self.shots_taken += 1
        self._event("shot", name=name)


def _publish_atomic(path: Path, text: str, attempts: int = 6) -> None:
    """Replace ``path`` atomically, retrying the Windows sharing violation.

    ``os.replace`` fails with ERROR_ACCESS_DENIED whenever the reader happens to have the target
    open at that instant -- a real collision at a 60 Hz write against a 30 Hz poll, not a theoretical
    one. Retry briefly, then fall back to a direct write: the reader retries parse failures, so a
    torn read costs one poll, whereas a failed publish costs the whole run.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    for attempt in range(attempts):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            time.sleep(0.002 * (attempt + 1))
    path.write_text(text, encoding="utf-8")
    try:
        tmp.unlink()
    except OSError:
        pass


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
