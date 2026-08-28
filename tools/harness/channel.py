#!/usr/bin/env python3
"""The wire protocol between the harness driver and the in-game agent (memoria-patch s83).

Two files in ``<game>/x64/ff9harness/`` carry everything:

* ``req.txt``    -- driver -> game. Line-oriented text, first line ``seq <n>``. Text rather than JSON
  because the game side must parse it inside the frame loop with no JSON library in Assembly-CSharp;
  hand-rolling a parser there would be a bug farm for no gain.
* ``state.json`` -- game -> driver. JSON, because here the asymmetry reverses: C# writes it with a
  StringBuilder and Python reads it for free.

``arm`` gates the whole mechanism: with no ``arm`` file the agent is inert and the engine behaves
exactly like an unpatched one. That matters because one FF9 install is shared by every concurrent
worktree on this machine.

The sequence number makes the request read IDEMPOTENT -- the agent may poll ``req.txt`` any number of
times, including mid-write, and only acts when the seq advances. That is what lets the driver write the
file with a plain atomic replace instead of a lock.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

PROTOCOL = 1

#: Names accepted for the virtual controller. Mirrors ParseControl in HarnessAgent.cs -- kept here as
#: data so the driver can reject a typo locally instead of shipping it to the game and reading back an
#: "unknown button" error three frames later.
BUTTONS = {
    "confirm", "ok", "x", "circle", "a",
    "cancel", "back", "b",
    "menu", "triangle", "y",
    "special", "square",
    "l1", "leftbumper", "r1", "rightbumper",
    "l2", "lefttrigger", "r2", "righttrigger",
    "start", "pause", "select",
    "up", "north", "down", "south", "left", "west", "right", "east",
}


class HarnessError(RuntimeError):
    """A harness-level failure: the game is gone, a step was refused, or a wait timed out."""


class State:
    """One sample of the game's state, as published by the agent.

    Attribute access is flattened for the fields a scenario actually asserts on (``field_id``,
    ``player_x`` ...); ``raw`` keeps the full document for anything not surfaced here yet.
    """

    __slots__ = ("raw",)

    def __init__(self, raw: dict):
        self.raw = raw

    # -- plumbing ---------------------------------------------------------------------------
    @property
    def frame(self) -> int:
        return int(self.raw.get("frame", -1))

    @property
    def ack(self) -> int:
        return int(self.raw.get("ack", -1))

    @property
    def busy(self) -> bool:
        return bool(self.raw.get("busy", False))

    @property
    def error(self) -> str | None:
        return self.raw.get("error")

    # -- where am I -------------------------------------------------------------------------
    @property
    def ui_state(self) -> str | None:
        return self.raw.get("ui_state")

    @property
    def scene(self) -> str | None:
        return self.raw.get("scene")

    @property
    def fading(self) -> bool:
        return bool(self.raw.get("fading", False))

    @property
    def sys_mode(self) -> int:
        return int(self.raw.get("sys_mode", -1))

    @property
    def scenario(self) -> int:
        return int(self.raw.get("scenario", -1))

    @property
    def field_id(self) -> int:
        return int(self.raw.get("field", {}).get("id", -1))

    @property
    def field_name(self) -> str | None:
        return self.raw.get("field", {}).get("name")

    @property
    def world_id(self) -> int:
        return int(self.raw.get("world", {}).get("id", -1))

    # -- the character ----------------------------------------------------------------------
    @property
    def player_x(self) -> float | None:
        return self.raw.get("player", {}).get("x")

    @property
    def player_y(self) -> float | None:
        return self.raw.get("player", {}).get("y")

    @property
    def player_z(self) -> float | None:
        return self.raw.get("player", {}).get("z")

    @property
    def pos(self) -> tuple[float | None, float | None, float | None]:
        return (self.player_x, self.player_y, self.player_z)

    @property
    def control(self) -> bool:
        """Whether the player currently has control -- false during cutscenes and transitions."""
        return bool(self.raw.get("player", {}).get("control", False))

    # -- what is on screen ------------------------------------------------------------------
    @property
    def dialog_open(self) -> bool:
        return bool(self.raw.get("dialog", {}).get("open", False))

    @property
    def texts(self) -> list[str]:
        return [t for t in self.raw.get("dialog", {}).get("texts", []) if t]

    @property
    def text(self) -> str:
        """Every open dialogue box joined -- the thing an assertion usually wants to match against."""
        return "\n".join(self.texts)

    @property
    def choice(self) -> dict | None:
        return self.raw.get("dialog", {}).get("choice")

    @property
    def held(self) -> list[str]:
        return list(self.raw.get("held", []))

    def flag(self, bit: int) -> bool | None:
        """A watched ``gEventGlobal`` bit. ``None`` unless the scenario called ``watch(bit)`` first."""
        return self.raw.get("flags", {}).get(str(bit))

    def __repr__(self) -> str:
        where = f"field {self.field_id}" if self.field_id > 0 else f"world {self.world_id}"
        return (f"<State frame={self.frame} {self.ui_state} {where} "
                f"pos=({_f(self.player_x)},{_f(self.player_z)}) control={self.control}"
                f"{' DIALOG' if self.dialog_open else ''}>")


def _f(v) -> str:
    return "?" if v is None else f"{v:.1f}"


class Channel:
    """The file-backed request/state channel. Owns nothing but the directory."""

    def __init__(self, game_path: Path):
        self.game_path = Path(game_path)
        self.dir = self.game_path / "x64" / "ff9harness"
        self.shots = self.dir / "shots"
        self._seq = 0

    # -- lifecycle --------------------------------------------------------------------------
    def reset(self) -> None:
        """Clear the channel for a fresh run. Leaves ``arm`` alone -- arming is a separate decision."""
        self.shots.mkdir(parents=True, exist_ok=True)
        for name in ("req.txt", "state.json", "state.json.tmp", "events.jsonl"):
            _unlink(self.dir / name)
        for png in self.shots.glob("*.png"):
            _unlink(png)
        self._seq = 0

    def arm(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "arm").write_text("armed by tools/harness\n", encoding="utf-8")

    def disarm(self) -> None:
        _unlink(self.dir / "arm")

    @property
    def armed(self) -> bool:
        return (self.dir / "arm").exists()

    # -- driver -> game ---------------------------------------------------------------------
    def send(self, steps: list[str]) -> int:
        """Queue ``steps`` in the game. Returns the sequence number to wait for."""
        self._seq += 1
        body = "\n".join([f"seq {self._seq}", *steps]) + "\n"
        _write_atomic(self.dir / "req.txt", body)
        return self._seq

    # -- game -> driver ---------------------------------------------------------------------
    def state(self, retries: int = 4, *, lock_budget: float = 1.0) -> State | None:
        """Latest published state, or ``None`` if the agent has not written one yet.

        Retries on a parse failure: the agent replaces the file atomically, but a virus scanner or a
        slow filesystem can still hand back a torn read, and a 1-in-500 flake would discredit every
        assertion built on top of this.

        ⚠ A Windows SHARING VIOLATION is not "no state" and must not be reported as one. The agent
        replaces this file ~30 times a second and a poller can easily collide with the replace; the
        engine side already tolerates that in both directions. Treating the resulting PermissionError
        as absence made the driver declare a perfectly healthy game dead, and that false verdict was
        then repeated as "walking out of the room hangs the game" -- a bug attributed to the game
        that lived entirely in the driver. Locks get their own, much longer, budget.
        """
        path = self.dir / "state.json"
        deadline = time.time() + lock_budget
        attempt = 0
        while True:
            try:
                # utf-8-SIG, not utf-8: .NET's File.WriteAllText with an explicit Encoding.UTF8
                # emits a BOM, and json.loads rejects the leading ﻿ outright. The symptom was
                # perfect: the agent published correct state every frame and the driver reported
                # "the agent never published state" for 90 seconds. Read tolerantly here rather than
                # relying on the engine being BOM-free, so an older deployed DLL still works.
                return State(json.loads(path.read_text(encoding="utf-8-sig")))
            except FileNotFoundError:
                return None
            except PermissionError:
                # The agent holds the file for the duration of its replace. Wait it out: at ~30
                # publishes/sec the window is sub-millisecond, so anything that outlasts the budget
                # is a real problem rather than a collision.
                if time.time() >= deadline:
                    return None
                time.sleep(0.005)
            except (ValueError, OSError):
                attempt += 1
                if attempt >= retries:
                    return None
                time.sleep(0.01)

    def events(self) -> list[dict]:
        path = self.dir / "events.jsonl"
        if not path.exists():
            return []
        out = []
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
        return out

    def collect(self, dest: Path) -> None:
        """Copy this run's artifacts (events + every screenshot) into ``dest``."""
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        events = self.dir / "events.jsonl"
        if events.exists():
            shutil.copy2(events, dest / "events.jsonl")
        state = self.dir / "state.json"
        if state.exists():
            shutil.copy2(state, dest / "state-final.json")
        if self.shots.is_dir() and any(self.shots.glob("*.png")):
            shots = dest / "shots"
            shots.mkdir(exist_ok=True)
            for png in self.shots.glob("*.png"):
                shutil.copy2(png, shots / png.name)


def _write_atomic(path: Path, text: str, attempts: int = 8) -> None:
    """Replace ``path`` atomically, surviving the Windows sharing violation.

    ``os.replace`` fails with ERROR_ACCESS_DENIED whenever the agent happens to have the target open
    at that instant. This is the mirror image of the race the agent's own ``WriteAtomic`` handles for
    ``state.json``, and it is not theoretical -- it killed a probe partway through the second field it
    was testing. Retry briefly, then fall back to a direct write: the agent already returns from a
    torn read and re-polls two frames later, and a partial file fails its ``seq`` parse and is
    ignored, so the worst case is one wasted poll rather than a dead run.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    for attempt in range(attempts):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.004 * (attempt + 1))
    path.write_text(text, encoding="utf-8")
    _unlink(tmp)


def _unlink(path: Path) -> None:
    try:
        path.unlink()
    except (FileNotFoundError, PermissionError):
        pass
