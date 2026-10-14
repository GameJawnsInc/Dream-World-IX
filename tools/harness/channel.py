#!/usr/bin/env python3
"""The wire protocol between the harness driver and the in-game agent (memoria-patch s83).

Three files in ``<game>/x64/ff9harness/`` carry everything:

* ``arm``        -- the gate. Its CONTENT is the owning run's identity (pid, label, start time); the
  engine only tests existence, so the body is free and we spend it on mutual exclusion.
* ``req.txt``    -- driver -> game. Line-oriented text, first line ``seq <n>``. Text rather than JSON
  because the game side must parse it inside the frame loop with no JSON library in Assembly-CSharp;
  hand-rolling a parser there would be a bug farm for no gain.
* ``state.json`` -- game -> driver. JSON, because here the asymmetry reverses: C# writes it with a
  StringBuilder and Python reads it for free.

``arm`` gates the whole mechanism: with no ``arm`` file the agent is inert and the engine behaves
exactly like an unpatched one. That matters because one FF9 install is shared by every concurrent
worktree on this machine.

THE SEQUENCE NUMBER IS THE CONTRACT, AND BOTH HALVES OF IT MATTER. The agent ignores a request whose
``seq`` does not advance, which makes the read idempotent -- it may poll ``req.txt`` any number of
times, including mid-write. The published ``seq`` is the agent's receipt for the request it ACCEPTED,
and ``ack`` is its receipt for having FINISHED it. A driver that waits on ``ack`` alone is not
waiting on its own request: after an unnoticed arm leak the agent keeps a high ``_seq`` from a dead
run, discards every new request as stale, and publishes an ``ack`` that satisfies the wait instantly.
Every step then becomes a silent no-op reported as success, and the first thing that measures the
world blames the game. So: **wait on seq AND ack, and never overwrite a request the agent has not yet
accepted.**
"""
from __future__ import annotations

import ctypes
import datetime as _dt
import json
import os
import re
import shutil
import time
from pathlib import Path

#: The wire version this driver speaks. Bumped with every change to what ``state.json`` MEANS, not
#: merely to what it contains.
#:
#: 1 -- the original s83 channel.
#: 2 -- ``texts`` is the RENDERED dialogue (was the raw source), the choice publishes its index
#:      space, and the agent reports ``armed`` / ``error_seq`` / ``debug_status``.
#: 3 -- the ``battle`` block: units, ATB, result, rewards, the command cursor; ``battle`` and
#:      ``battlecmd`` verbs.
#: 4 -- the battle can be PLAYED, not only watched: ``battle.menu`` (what a slot can do, by name,
#:      with the exact arguments to command it), ``battle.escaping`` (the escape rolled AND won,
#:      as opposed to ``escape_held``, which only means the bumpers are down), the ``menus`` verb,
#:      ``battlecmd`` accepted for the LOCAL slot, and a re-issued ``hold`` that no longer drops a
#:      frame between the old window and the new one.
#: 5 -- the ``netsync`` block (the co-op client + the F3 dialogue-lockstep observables: the window
#:      under lockstep, a HELD frame and its timeout clock, whether local input is suppressed) and
#:      the ``netsync`` verb family -- ``selftest``/``bench``/``l1``/``advance``/``choice``/
#:      ``unmatched`` -- so the F1-F3 solo benches run unattended instead of behind IMGUI buttons.
#:      (Additive, same version: ``player.listener`` and the ``netsync talk <uid>`` sub-verb --
#:      the F3.1 talk-relay bench; s88's ``storytrace`` and s89's ``objects``; s90's ``player.yaw`` /
#:      ``player.face``, the ``turn`` verb and its ``turn_end`` event -- :attr:`State.facing_status`.)
#:      (Additive, same version: s96, the F3.2 host-authoritative dialogue. ``netsync.dialogue`` =
#:      ``"authority"`` names the contract -- absent = the F3 lockstep. NOT a bump on purpose: a bump
#:      makes every other session's rev-5 driver refuse the engine, and only the co-op scenarios read
#:      ``netsync``. The F3 keys stay, PINNED to "nothing": ``l1_pinned``/``l1_forced_control``/
#:      ``wait_armed`` false, ``align_win``/``align_text``/``applied_seq``/``wait_ms``/``wait_limit_ms``
#:      -1, ``pending`` null; ``suppress`` keeps its meaning but rises from the frame a line OPENS
#:      under the lock. New keys: the bench levers ``lock``/``stale``, ``lock_engaged``, ``unlocked``
#:      (the ~ menu panic unlock, until the next field load), ``windows[]`` {win, text, field, cls =
#:      locked|orphaned|local, state, page, inh}, ``inbox`` {count, heads[]}, ``host_settled_ms`` (-1 =
#:      not settled), ``orphan_closes``, ``chip`` (null = none). New sub-verbs ``lock 1|0``,
#:      ``hostscene 0|1`` (alias ``l1``), ``stale 1|0``, ``unlock``, ``click``, ``drag <dy>``;
#:      ``advance``/``choice``/``unmatched`` now feed the guest's inbox and need ``lock 1``. A driver
#:      checks :attr:`State.dialogue_authority` before asserting on a new key.)
#:      (Additive, same version, [ff9mapkit netsync F3.3]: s97's ``netsync.diorama`` block {booted, boot,
#:      boot_why, boot_field, boot_x, boot_z, primed, returns, last_return, last_return_field, resuming} and
#:      sub-verbs ``dioboot <scene> [pattern]`` / ``dioleave`` -- :attr:`State.diorama_warm_return`; s98's
#:      section-7 ring keys ``wire``/``epoch``/``head_seq``/``last_seen``/``gaps``/``heartbeat``/
#:      ``host_stalled``/``host_flags``/``host_open[]``/``cursor``/``key_ignored``/``host_frozen``/
#:      ``host_menu``/``host_battle`` and the bench host ``host <op> [n ...]`` -- :attr:`State.dialogue_ring`;
#:      s99's script-key relay keys ``key_tick``/``key_hold``/``key_reader``/``keys[]``/``key_served``/
#:      ``key_expired``/``key_gaveup``/``key_taps``/``tap_record``/``tape``/``replay_left`` and ``tap-record
#:      1|0`` / ``replay [[paced] 1|0]`` -- :attr:`State.script_key_relay`. ``dialogue`` stays "authority":
#:      each capability is told by its own key's PRESENCE, never by a tag.)
PROTOCOL = 5

#: The agent polls the arm file every 30 FRAMES (HarnessAgent.PollArm). A delete+create inside one
#: window is INVISIBLE to it -- ``armed == Active``, early return, no reset of seq/ack, no button
#: clear. So a re-arm has to outlast the poll to be a real transition -- and the agent SAYS when it
#: has seen the disarm: the frame its poll finds the arm file gone, it publishes one last document,
#: ``"armed": false`` (HarnessAgent.cs:396-409, the s83 agent), before it stops publishing. The arm
#: cycle waits for that document (:meth:`Channel.arm`), at most this long -- 30 frames down to 10
#: fps. It used to sleep 0.85 s, which was shorter than the poll at the ~31 fps the harness has
#: rendered at for whole launches (a second): an attach-mode re-arm could go unobserved there, and
#: the held keys, the error latch and the story tracer were never reset.
ARM_CYCLE_TIMEOUT = 3.0

#: How often the arm cycle reads state.json for the agent's disarm document -- a few times a frame at
#: any render rate the harness has seen.
ARM_CYCLE_POLL = 0.005

#: A published document older than this is not a live game talking.
STALE_AFTER = 5.0

#: How long state.json may sit EMPTY and still be a publish in flight. The agent rewrites it IN PLACE
#: (``FileMode.Create``: truncate, then the bytes land). MEASURED 2026-09-23 with that exact open mode
#: at 60 Hz: the gap is ~0.7 ms at the median, ~80 ms at p99, ~200 ms at worst -- an on-access scan
#: holding the rewrite. Empty for longer than this, the game hung or died inside the publish.
MID_WRITE_WITHIN = 0.5


class HarnessError(RuntimeError):
    """A harness-level failure: the game is gone, a step was refused, or a wait timed out."""


class StepRefused(HarnessError):
    """The agent REFUSED a step of the request that was just acked -- its error latch, stamped with this request
    (Session._raise_if_this_step_failed). ``error`` is the latch's own text, ``"<op>: <message>"`` (HarnessAgent.
    DrainQueue: the LAST refusal of the request), exactly as the state that carried the ack published it -- so a
    caller that classifies a refusal reads it HERE, from the sample the verdict was made on, never from a second read
    of state.json (which can come back None mid-rewrite on a healthy game, :meth:`Channel.state`). ``steps`` the
    request's steps; ``state`` that sample itself (None where a refusal is raised without one) -- what the game
    published with the refusal, so a caller can ask whether the state explains it (Session.fight: no battle HUD
    with the battle gone)."""

    def __init__(self, error: str, steps, *, state: "State | None" = None):
        super().__init__(f"the game refused a step: {error} (steps={list(steps)})")
        self.error, self.steps, self.state = str(error), list(steps), state


class BattleGone(HarnessError):
    """The battle a command menu was read for ENDED -- its scene gone, its epoch unchanged -- after the ``menus`` step
    acked and before the menu it collected was read (Session.menus: the battle doc carries ``menu`` only while the
    battle is up, so that wait would run out its timeout on a menu that can never come), or before Session.act
    resolved against it. Not a refusal: the step ran, and the battle it ran in is over. ``state`` the sample that showed
    it gone, ``epoch`` the battle's. Session.fight reads it as the battle's end (the result returned, or FightTimeout
    kind "gone"); every ``except HarnessError`` still catches it."""

    def __init__(self, message: str, *, state: "State", epoch: int):
        super().__init__(message)
        self.state, self.epoch = state, int(epoch)


class FightTimeout(HarnessError):
    """``Session.fight`` reached NO RESULT (research/o3_design.md H7): ``kind`` "turns" -- it answered ``max_turns``
    command prompts (0: it raised at the first one, before any command) -- or "timeout": a bound ran out, and the
    message is the one the plain HarnessError carried before. ``kind`` "gone" -- the battle scene went away with no
    result while both bounds still held (a soft reset or a crash to the title mid-fight, an engine path that leaves the
    result 0): no bound ran out, so a caller that owns the bounds must not read it as one (the review, research/
    o3_design.md 11.7 #2). Every ``except HarnessError`` still catches it. Typed because a caller that owns the fight's
    bounds (the beat-table driver's battle beat: its V15) must tell this from an instrument failure, which stays a
    plain HarnessError."""

    def __init__(self, message: str, *, kind: str):
        super().__init__(message)
        self.kind = str(kind)


def pid_alive(pid: int) -> bool:
    """Windows-safe liveness probe.

    ⚠ NEVER ``os.kill(pid, 0)`` here. On Windows CPython routes every signal but the console-control
    ones to ``TerminateProcess``, so the textbook liveness idiom would KILL the process it asks about
    -- in this case another agent's game, or another agent's driver.
    """
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    try:
        handle = _kernel32().OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    except (OSError, AttributeError):
        return True                       # cannot tell -> assume alive, never steal another run's arm
    if handle:
        _kernel32().CloseHandle(handle)
        return True
    # ERROR_ACCESS_DENIED -> it exists, we just cannot look. ⚠ `ctypes.get_last_error()` only
    # carries a value for a library opened with `use_last_error=True`; read through the plain
    # `ctypes.windll.kernel32` it is always 0, so this branch could never fire and a live process
    # this user may not open -- another account's driver, an elevated game -- read as DEAD, and its
    # arm was adopted. A liveness probe that cannot say "alive but not mine" is the wrong shape here.
    return ctypes.get_last_error() == 5


_K32 = None


def _kernel32():
    """kernel32 opened with the last-error capture that `ctypes.get_last_error()` reads from."""
    global _K32
    if _K32 is None:
        _K32 = ctypes.WinDLL("kernel32", use_last_error=True)
    return _K32


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

#: The four DIRECTIONS among :data:`BUTTONS`, each alias to its Control name -- ParseControl's names, directions
#: only: what the s90 ``turn`` verb takes (HarnessAgent.ParseTurnDirections), ``+``-joined.
DIRECTIONS = {"up": "up", "north": "up", "down": "down", "south": "down",
              "left": "left", "west": "left", "right": "right", "east": "right"}


# -- the in-place turn (memoria-patch s90) ----------------------------------------------------------
class TurnRefused(HarnessError):
    """The agent REFUSED a ``turn`` (HarnessAgent.BeginTurn: every refusal throws before anything is pressed, the rest
    of the request still runs and acks). ``kind`` is the refusal named by the agent's own stable message
    (:func:`turn_refusal`), ``message`` those words, ``why`` the TurnBlocker token of a ``"blocked"`` one
    (``field``, ``player``, ``control``, ``movement``, ``actor``, ``hud``, ``unreadable``), ``uid`` the body of an
    ``"overlap"``."""

    def __init__(self, message: str, *, kind: str, why: str | None = None, uid: int | None = None):
        super().__init__(f"the game refused the turn ({kind}): {message}")
        self.message, self.kind, self.why, self.uid = message, kind, why, uid


#: The agent's refusal messages for ``turn``, by their stable PREFIX (HarnessAgent.cs, s90: BeginTurn,
#: ParseTurnDirections, ParseControl, and Execute's default for an engine without the verb), each to its ``kind``:
#:   * ``argument``   -- ``needs a direction ...`` / ``'x' is not a direction ...`` / ``unknown button 'x'``;
#:   * ``blocked``    -- ``needs a field with a controlled player under user control (<why>)`` -- TurnBlocker's token;
#:   * ``unreadable`` -- ``the player's field, position or facing is unreadable``;
#:   * ``judging``    -- ``the last turn's keys are up and the field is still judging it``: wait for its turn_end;
#:   * ``cut``        -- ``the turn in progress began on another actor or field``: turn again after its turn_end;
#:   * ``analog``     -- ``[AnalogControl] Enabled=0``: this install cannot turn in place (the key path steps him);
#:   * ``held``       -- ``<Dir> is held or scheduled``: a direction is down now or on a later frame;
#:   * ``opposite``   -- ``opposite directions cancel to no direction``;
#:   * ``axis``       -- ``a physical stick or key is pushing the axis``: a human is at the controls;
#:   * ``path``       -- ``a click-to-move path is pending``: a mouse walk is in progress;
#:   * ``overlap``    -- ``overlapping object uid N``: a turn toward that body would push him out;
#:   * ``cannot``     -- ``unknown op 'turn'``: an engine without s90, whatever a sample said.
TURN_REFUSALS = (
    ("needs a direction", "argument"),
    ("unknown button", "argument"),
    ("needs a field with a controlled player under user control", "blocked"),
    ("the player's field, position or facing is unreadable", "unreadable"),
    ("the last turn's keys are up and the field is still judging it", "judging"),
    ("the turn in progress began on another actor or field", "cut"),
    ("[AnalogControl] Enabled=0", "analog"),
    ("opposite directions cancel", "opposite"),
    ("a physical stick or key is pushing the axis", "axis"),
    ("a click-to-move path is pending", "path"),
    ("overlapping object uid", "overlap"),
    ("unknown op 'turn'", "cannot"),
)


def turn_refusal(message: str) -> TurnRefused:
    """The agent's ``turn`` refusal ``message`` (the error latch's text after ``turn: ``) as a :class:`TurnRefused`,
    classified on the stable prefixes of :data:`TURN_REFUSALS` -- and the two whose variable part leads: ``'x' is not
    a direction ...`` (``argument``) and ``<Dir> is held or scheduled ...`` (``held``). A message none of them
    matches is ``kind`` ``"other"``: an agent newer than this driver, never guessed at."""
    text = str(message).strip()
    for prefix, kind in TURN_REFUSALS:
        if text.startswith(prefix):
            why = uid = None
            if kind == "blocked":
                m = re.search(r"\((\w+)\)", text)
                why = m.group(1) if m else None
            elif kind == "overlap":
                m = re.match(r"overlapping object uid (-?\d+)", text)
                uid = int(m.group(1)) if m else None
            return TurnRefused(text, kind=kind, why=why, uid=uid)
    if re.match(r"'[^']*' is not a direction", text):
        return TurnRefused(text, kind="argument")
    if re.match(r"(Up|Down|Left|Right) is held or scheduled", text):
        return TurnRefused(text, kind="held")
    return TurnRefused(text, kind="other")


def parse_turn_end(ev: dict) -> dict:
    """A ``turn_end`` event (s90, HarnessAgent.EndTurn) with its values PARSED: the agent's event writer quotes every
    value but ``frame`` (``{"why": "ended", "frames": "8", "yaw0": "69.12", "yaw": "-85.301", "face": "195", "moved":
    "0"}``), so each is read back here -- ``frame`` / ``frames`` / ``face`` ints, ``yaw0`` / ``yaw`` / ``moved``
    floats, ``why`` the token (``ended``; else what cut it: ``field``, ``player``, ``control``, ``movement``,
    ``actor``, ``hud``, ``unreadable``, ``axis``). ``yaw``, ``face`` and ``moved`` are None where the agent wrote null:
    off a field at the end, or on another field id or controlled actor than the turn began on (a door's warp, a
    same-id reload) -- read the new state instead."""
    def num(key, cast):
        v = ev.get(key)
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return cast(float(v)) if cast is int else cast(v)
    return {"frame": num("frame", int), "why": ev.get("why"), "frames": num("frames", int),
            "yaw0": num("yaw0", float), "yaw": num("yaw", float), "face": num("face", int),
            "moved": num("moved", float)}


def _json_copy(v):
    """A deep copy of a parsed-JSON value (dicts and lists all the way down) -- an accessor never hands out the raw doc."""
    if isinstance(v, dict):
        return {k: _json_copy(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_json_copy(x) for x in v]
    return v


def _nb_prop(path: str, kind, doc: str) -> property:
    """[ff9mapkit netsync B4] One ``netsync.battle`` key as a read-only :class:`State` property. ``path`` is dotted under
    ``netsync.battle`` (``"host.caps"``, ``"end.end_leave.trigger"``); ``kind`` is how it reads (:meth:`State._nb_key`).
    Every such property carries its path, so the test can hold the table against the agent's published keys."""
    def get(self):
        return self._nb_key(path, kind)
    get.__doc__ = doc
    get.__name__ = "nb_" + path.replace(".", "_")
    get.nb_path = path
    return property(get)


def _dio_prop(path: str, kind, doc: str) -> property:
    """[ff9mapkit netsync R3 s111] One ``netsync.diorama`` key BELOW the F3.3 block (s111's ``intro``, s112's
    ``intro.swirl_clamp``, s114's ``live``) as a read-only :class:`State` property, carrying its path for the test's table
    (:attr:`State.NETSYNC_DIORAMA_ACCESSORS`)."""
    def get(self):
        return self._dio_path(path, kind)
    get.__doc__ = doc
    get.__name__ = "dio_" + path.replace(".", "_")
    get.dio_path = path
    return property(get)


class State:
    """One sample of the game's state, as published by the agent.

    Attribute access is flattened for the fields a scenario actually asserts on (``field_id``,
    ``player_x`` ...); ``raw`` keeps the full document for anything not surfaced here yet.

    Accessors for values a NEWER agent publishes return ``None`` when the key is absent rather than a
    plausible default, so "this DLL does not publish that" can never be mistaken for game data.

    ⚠ ``raw`` is the agent's document UNTOUCHED, so it still carries ``player.tri`` / ``player.floor``
    under names that read as live. They are not -- see :attr:`player_tri_battle_snapshot`, the only
    sanctioned reader. ``tests/test_harness.py`` refuses a harness scenario that reads the bare keys.
    """

    __slots__ = ("raw", "read_at", "mtime")

    def __init__(self, raw: dict, read_at: float | None = None, mtime: float | None = None):
        self.raw = raw
        self.read_at = time.time() if read_at is None else read_at
        #: When the agent last WROTE this document. The only liveness signal available from a single
        #: sample -- a hung agent leaves a perfectly valid state.json that satisfies most predicates.
        self.mtime = mtime

    @property
    def age(self) -> float | None:
        """Seconds since the agent wrote this, or ``None`` when that could not be read."""
        return None if self.mtime is None else max(0.0, self.read_at - self.mtime)

    # -- plumbing ---------------------------------------------------------------------------
    @property
    def frame(self) -> int:
        return int(self.raw.get("frame", -1))

    @property
    def seq(self) -> int:
        """The last request the agent ACCEPTED. -1 before any request, or after a fresh arm."""
        return int(self.raw.get("seq", -1))

    @property
    def ack(self) -> int:
        """The last request the agent FINISHED."""
        return int(self.raw.get("ack", -1))

    @property
    def protocol(self) -> int | None:
        v = self.raw.get("v")
        return None if v is None else int(v)

    @property
    def armed(self) -> bool | None:
        """Whether the agent believes it is armed. ``None`` on an engine that does not publish it."""
        return self.raw.get("armed")

    @property
    def busy(self) -> bool:
        return bool(self.raw.get("busy", False))

    @property
    def error(self) -> str | None:
        return self.raw.get("error")

    @property
    def error_seq(self) -> int | None:
        """The request the published error belongs to. ``None`` on an engine that does not stamp it."""
        v = self.raw.get("error_seq")
        return None if v is None else int(v)

    @property
    def debug_status(self) -> str | None:
        """The debug menu's own last status line -- why an engine action refused."""
        return self.raw.get("debug_status")

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

    @property
    def world_x(self) -> float | None:
        return self.raw.get("world", {}).get("x")

    @property
    def world_z(self) -> float | None:
        return self.raw.get("world", {}).get("z")

    @property
    def world_pos(self) -> tuple[float | None, float | None]:
        return (self.world_x, self.world_z)

    @property
    def vehicle(self) -> int:
        return int(self.raw.get("world", {}).get("vehicle", -1))

    @property
    def world_y(self) -> float | None:
        """The world actor's HEIGHT in world units -- ``player.y / 256`` on the overworld, None off it.

        The agent publishes no world y of its own, but the controlled actor's pos[] is RealPosition
        x 256 (the teleport writes it back that way: ``py = RealPosition.y * 256``), so this is the
        same space as world.x/z and the terrain mesh. ⚠ A teleport KEEPS the old height until
        movement re-grounds it -- read this after a step, never straight after a teleport.
        """
        if not self.on_world:
            return None
        y = self.player_y
        return None if y is None else y / 256.0

    @property
    def on_world(self) -> bool:
        """On the overworld -- as opposed to on a field. See ``Session.wait_world``."""
        return self.ui_state == "WorldHUD"

    @property
    def on_field(self) -> bool:
        return self.ui_state == "FieldHUD"

    # -- the character ----------------------------------------------------------------------
    # ⚠ player.* is the ENGINE'S CONTROLLED ACTOR, whichever map is up. On the overworld
    # GetControlChar() returns the world actor and its pos[] is RealPosition x 256 -- so these are
    # NOT null there, they are a different coordinate space. Steering a field verb on them would
    # converge 256x off and report confident wrong numbers, which is why the field verbs assert
    # ui_state == "FieldHUD" rather than merely checking for None.
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

    # -- the field's other actors (memoria-patch s89) ----------------------------------------
    # THREE CASES, AND ONLY ONE OF THEM IS A LIST. The key ABSENT is an engine that cannot publish
    # objects (pre-s89); null is an engine that can and does not know right now (off a field, or its
    # walk of the object list failed -- it never publishes a partial list); a list is the objects.
    # ``objects`` is None for both of the first two, never [], so neither can be iterated as an empty
    # field -- "unknown" read as "no obstacles" would plan a leg straight through a solid body.
    # ``objects_status`` names which.
    @property
    def objects_status(self) -> str:
        """``"cannot"`` (the key is absent: this engine publishes no objects), ``"unknown"`` (null: it
        does, and could not say this sample) or ``"listed"`` (``objects`` is the list -- [] is a field
        with no other actor)."""
        if "objects" not in self.raw:
            return "cannot"
        return "listed" if isinstance(self.raw.get("objects"), list) else "unknown"

    @property
    def objects(self) -> list[dict] | None:
        """Every actor on the field other than the controlled player, as s89 publishes them: ``uid``,
        ``sid``, ``x``/``y``/``z`` (the ``player`` frame), ``r`` (the centre distance the engine keeps
        him from it; it only collides while ``|dy| < 400``), ``solid`` (never let through), ``coll``
        (false: walk-through), ``range``/``talk`` (it HAS a contact / talk function), ``range_r`` /
        ``talk_r`` (where those fire -- a trigger zone, not a wall), ``shown``, ``moving``, ``flags``.
        ``r``/``solid``/``coll``/``range_r``/``talk_r`` are relations to the player and null without
        one. ``None`` unless :attr:`objects_status` is ``"listed"`` -- never an empty list for "cannot"
        or "unknown"."""
        objs = self.raw.get("objects")
        return objs if isinstance(objs, list) else None

    @property
    def pushout(self) -> dict | None:
        """The engine's push-through state, published beside ``objects`` (s89): ``slock``
        (``sLockTimer``; < 0 = the walk-through window is open and every non-solid body passable),
        ``scoll``, ``slockfree`` (0 = the closest contact is solid) and ``fallback`` (whether the
        release runs on this field at all). ``None`` when absent or null -- :attr:`objects_status`
        tells which, as the two keys are published and nulled together."""
        po = self.raw.get("pushout")
        return po if isinstance(po, dict) else None

    # -- the facing (memoria-patch s90) ------------------------------------------------------
    # THREE CASES, AND ONLY ONE OF THEM IS A FACING -- the objects_status precedent. The ``face`` key ABSENT from
    # ``player`` is an engine that CANNOT publish the facing (pre-s90 -- and one that cannot ``turn`` either: the one
    # probe covers both halves of the patch); null is an engine that can and has none this sample (off a field --
    # title, battle, world map -- or no controlled character); a number is the facing. "Cannot" is never read as
    # "nothing there": a driver that took a pre-s90 engine's missing key for "no facing right now" would wait for one
    # that never comes, and one that took null for "cannot" would give up a turn the engine can make.
    # ``player.dir`` is NOT the facing on a field: it is PosObj.rot[1], which only the world map writes (0 on every
    # field, whatever way he faces). The agent publishes both keys whenever a controlled character stands on a field,
    # with or without user control -- ``yaw`` follows a scripted turn too (HarnessAgent.PublishState, s90).
    @property
    def facing_status(self) -> str:
        """``"cannot"`` (``player.face`` absent: this engine publishes no facing and has no ``turn`` verb),
        ``"unknown"`` (null: it does, and there is none this sample) or ``"known"`` (:attr:`player_face` is the
        byte)."""
        p = self.raw.get("player") or {}
        if "face" not in p:
            return "cannot"
        return "known" if isinstance(p.get("face"), int) and not isinstance(p.get("face"), bool) else "unknown"

    @property
    def player_yaw(self) -> float | None:
        """``Actor.rotAngle[1]`` in DEGREES, raw, to 0.001: 0 faces -z, 90 -x, +-180 +z, -90 +x. MovePC's lerp leaves
        it in [-180, 180] (FieldMapActorController.cs:759-764), a script's direct set of a byte in [0, 358.6]
        (EventEngine.cs:1180-1188) -- never assume a range. For a gate decision read :attr:`player_face`, the byte
        the gate compares; the yaw is for measuring a turn (its lerp) and for the eye. None when absent or null
        (:attr:`facing_status` says which)."""
        v = (self.raw.get("player") or {}).get("yaw")
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    @property
    def player_face(self) -> int | None:
        """The ``.eb`` facing byte, 0..255 in 256ths of a turn (0 = -z, 64 = -x, 128 = +z, 192 = +x) -- obj(250).f[3],
        computed by the engine's OWN getvobj (EBin.HarnessFacingByte): the exact value a stock door gate compares
        (content.doorface.gate_value_from_face). Every gate decision uses this, never a byte re-derived from
        :attr:`player_yaw`. None when absent or null (:attr:`facing_status` says which)."""
        v = (self.raw.get("player") or {}).get("face")
        return v if isinstance(v, int) and not isinstance(v, bool) else None

    # -- the walkmesh triangle: NOT PUBLISHED LIVE ------------------------------------------
    # No agent yet publishes the triangle or floor the player stands on. What s83 publishes under
    # player.tri / player.floor is a battle-entry snapshot, so it is exposed only under names that
    # say so. The patch that would publish the live value is scoped, unbuilt, in
    # studies/test-harness/PLAYER-TRI-PATCH-PLAN.md.
    @property
    def player_tri_battle_snapshot(self) -> int | None:
        """⚠ NOT THE TRIANGLE THE PLAYER STANDS ON -- the one they stood on when the field was last left
        for a battle.

        The agent publishes ``PosObj.activeTri`` as ``player.tri``, and that field is not live. Its only
        writer is ``EventEngine.BackupPosObjData`` (``EventEngine.cs:1441``), which copies the actor
        controller's value on the way into a battle (an encounter, a scripted battle, the ~ menu's
        battle jump) or a Tetra Master game. ``PosObj.copy`` only copies it between contexts, and
        neither constructor sets it. So it reads 0 before the session's first battle, which cannot be
        told apart from a real triangle 0. After a battle it holds still however far the player walks.
        The engine reads it back exactly once, on the return trip: ``FieldMap.RestoreModels``
        (``FieldMap.cs:522-528``) seeds the respawned actor's controller with it. It is a seed for the
        post-battle respawn, never a reading of where the player is.

        The live value is ``fieldMapActorController.activeTri``, the one ``.eb``'s ``B_BGIID`` reads
        (``BGI.cs:11-20``). Until an agent publishes it, a triangle-level fact about where the player
        stands comes from ``expr:B_PTR(250) B_BGIID`` in the field (a raw uid, so ``const(250)`` reads
        -1) or from ``scene.bgi.BgiWalkmesh`` at the published x/z, never from here. ``None`` when the
        key is absent.
        """
        v = self.raw.get("player", {}).get("tri")
        return None if v is None else int(v)

    @property
    def player_floor_battle_snapshot(self) -> int | None:
        """⚠ NOT THE FLOOR THE PLAYER IS ON -- the same battle-entry snapshot as
        :attr:`player_tri_battle_snapshot`, with one more distortion.

        ``PosObj.activeFloor`` is a ``Byte``, while the controller's is an ``Int32`` whose "no floor"
        is -1. The backup casts it, so -1 lands as 255. It is decoded back to -1 here; ``raw`` still
        says 255. ``None`` when the key is absent.
        """
        v = self.raw.get("player", {}).get("floor")
        if v is None:
            return None
        v = int(v)
        return -1 if v == 255 else v

    # -- what is on screen ------------------------------------------------------------------
    @property
    def dialog_open(self) -> bool:
        return bool(self.raw.get("dialog", {}).get("open", False))

    @property
    def texts(self) -> list[str]:
        """The RENDERED dialogue, as the player reads it (agent >= protocol 2)."""
        return [t for t in self.raw.get("dialog", {}).get("texts", []) if t]

    @property
    def raw_texts(self) -> list[str]:
        """The dialogue SOURCE, tags and all -- ``Dialog.Phrase``. Evidence, not an assertion target.

        On an older agent ``texts`` IS this, which is why ``expect_text`` can fail against words the
        player plainly sees: the source carries ``[STRT=…]`` runs and un-substituted variables.
        """
        return [t for t in self.raw.get("dialog", {}).get("phrase_raw", []) if t]

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

    # -- co-op (netsync) --------------------------------------------------------------------
    @property
    def storytrace(self) -> dict | None:
        """The story-write trace's block (memoria-patch s88): ``proto``, ``on``, ``rows``, ``suppressed``
        and ``error`` (why the tracer turned itself off, null while healthy). ``None`` on an engine without
        the trace -- a CAPABILITY, additive under protocol 5, so "this DLL cannot trace" is never read as
        an empty story.jsonl, i.e. "no script wrote anything"."""
        st = self.raw.get("storytrace")
        return st if isinstance(st, dict) else None

    @property
    def netsync(self) -> dict | None:
        """The co-op client's observables (agent >= protocol 5), or None on an engine without them.

        ``None`` rather than ``{}`` on purpose: "the engine does not publish this" and "co-op is
        off" are different facts, and a scenario asserting on lockstep state must be able to tell
        them apart instead of reading an absent section as a disengaged client. Which dialogue
        contract the keys describe -- the F3 lockstep or the F3.2 authority -- is
        :attr:`dialogue_authority`.
        """
        return self.raw.get("netsync")

    @property
    def lockstep_pending(self) -> dict | None:
        """The dialogue frame HELD in the guest's one-slot holder (field/win/text/kind/index/seq).

        F3 lockstep only: an F3.2 engine (:attr:`dialogue_authority`) has no holder and pins ``pending``
        to null, so this is None there whatever the guest is doing -- read :attr:`dialogue_inbox_count`."""
        ns = self.netsync
        return None if ns is None else ns.get("pending")

    @property
    def lockstep_suppressed(self) -> bool:
        """Whether the guest's own Confirm/Cancel are being swallowed by the lockstep right now.

        ⚠ False on an engine with no ``netsync`` block too -- the F3 reading. :attr:`dialogue_suppressed`
        tells "cannot" (None) from "not swallowing" (False)."""
        ns = self.netsync
        return bool(ns.get("suppress", False)) if ns else False

    # F3.2 (s96): host-authoritative dialogue. Every accessor below reads an ABSENT key -- or no block -- as
    # None, "this engine cannot", never as "nothing there": a guest assertion that read an F3 engine's missing
    # `lock_engaged` as False would be green against the wrong DLL. Check :attr:`dialogue_authority` first.
    def _ns_key(self, key: str, kind):
        ns = self.netsync
        if not isinstance(ns, dict) or key not in ns:
            return None
        v = ns[key]
        # bool is an int subclass: an int reader must never take True for 1, nor a bool reader 1 for True
        if kind is int and (isinstance(v, bool) or not isinstance(v, int)):
            return None
        if kind is not int and not isinstance(v, kind):
            return None
        return v

    @property
    def dialogue_authority(self) -> bool | None:
        """Whether the engine speaks the F3.2 host-authoritative dialogue contract (``netsync.dialogue`` ==
        ``"authority"``, s96). False: the block is there without the tag -- the F3 lockstep engine, whose
        guest is driven by the one-slot holder (:attr:`lockstep_pending`). None: no ``netsync`` block at all
        (an engine below protocol 5), or a tag this driver does not know -- a contract it cannot read."""
        ns = self.netsync
        if not isinstance(ns, dict):
            return None
        tag = ns.get("dialogue")
        if tag is None:
            return False
        return True if tag == "authority" else None

    @property
    def dialogue_lock_engaged(self) -> bool | None:
        """THE LOCK (s96): a following guest's lines are the host's to drive -- session (or the bench lock)
        && on a field && this field not panic-unlocked. None on an engine without it."""
        return self._ns_key("lock_engaged", bool)

    @property
    def dialogue_unlocked(self) -> bool | None:
        """The ~ menu panic unlock (``netsync unlock``) is in force -- until the next field load."""
        return self._ns_key("unlocked", bool)

    @property
    def dialogue_suppressed(self) -> bool | None:
        """The guest's own dialogue keys / clicks are swallowed right now (``suppress``): under the lock, from
        the frame a lockable, non-``inh`` line OPENS. Unlike :attr:`lockstep_suppressed`, None on an engine
        that publishes no ``suppress``."""
        return self._ns_key("suppress", bool)

    @property
    def dialogue_windows(self) -> list[dict] | None:
        """Every line the guest tracks (s96 ``windows[]``): ``win``, ``text``, ``field``, ``cls`` (locked /
        orphaned / local), ``state`` (the Dialog state), ``page``, ``inh`` (FlagButtonInh: a script-polled
        line, never suppressed). ``[]`` = none tracked; None = an engine without the tracker."""
        wins = self._ns_key("windows", list)
        return None if wins is None else [dict(w) for w in wins if isinstance(w, dict)]

    @property
    def dialogue_inbox(self) -> dict | None:
        """The host events waiting on the guest (s96 ``inbox``): ``count`` and ``heads`` -- the earliest event
        of each window key (field/win/text/kind/index/seq/scene/age_ms/tried), at most 8."""
        inbox = self._ns_key("inbox", dict)
        if inbox is None:
            return None
        return dict(inbox, heads=[dict(h) for h in inbox.get("heads") or [] if isinstance(h, dict)])

    @property
    def dialogue_inbox_count(self) -> int | None:
        """How many host events wait in the guest's inbox. None on an engine without the inbox."""
        inbox = self._ns_key("inbox", dict)
        v = None if inbox is None else inbox.get("count")
        return v if isinstance(v, int) and not isinstance(v, bool) else None

    @property
    def dialogue_host_settled_ms(self) -> int | None:
        """How long the host has read SETTLED (scene down, no relayed start, co-located or provably away), in
        ms; -1 = not settled. The orphan rule acts once this passes OrphanGraceMs. None = cannot."""
        return self._ns_key("host_settled_ms", int)

    @property
    def dialogue_orphan_closes(self) -> int | None:
        """Lines the orphan rule auto-closed this session (a line the host provably lacks, closed at reading
        pace) -- monotonic, so assert on a DELTA. None on an engine without the rule."""
        return self._ns_key("orphan_closes", int)

    @property
    def dialogue_chip(self) -> str | None:
        """The co-op chip's text. ``""`` when the engine draws none right now (it publishes null), None when it
        cannot draw one at all -- the absent key and the empty chip must not read alike."""
        ns = self.netsync
        if not isinstance(ns, dict) or "chip" not in ns:
            return None
        v = ns["chip"]
        return "" if v is None else str(v)

    # [ff9mapkit netsync F3.3] C3 (s98): THE DIALOGUE RING -- the host's taps ride state section 7 (wire v14) with an
    # epoch, a heartbeat, the host's flags and its open windows. The same law as F3.2: an ABSENT key reads None ("this
    # engine cannot" -- an s96/s97 DLL), never 0 / False / [] ("nothing there"). Check :attr:`dialogue_ring` first.
    #: Section 7's host-flags byte (``host_flags``), bit by name: b0 the host's sticky scene, b1 its user control, b2 an
    #: input-taking (non-[NFOC]) line open, b3 on a live field, b4 a non-HUD UI (menu/shop/pause), b5 in battle.
    HOST_FLAG_BITS = {"scene": 0x01, "control": 0x02, "line": 0x04, "on_field": 0x08, "menu": 0x10, "battle": 0x20}

    @property
    def dialogue_ring(self) -> bool | None:
        """Whether the engine delivers the host's dialogue taps through the section-7 RING (s98: ``netsync.wire`` is
        published, 14 or later). False: a ``netsync`` block without ``wire`` -- an s96/s97 engine, whose taps ride the
        type-7 FIFO and whose bench has no ``host`` verb; None: no ``netsync`` block at all."""
        ns = self.netsync
        if not isinstance(ns, dict):
            return None
        wire = self._ns_key("wire", int)
        return wire is not None and wire >= 14

    @property
    def dialogue_wire(self) -> int | None:
        """The co-op wire version THIS engine speaks (14 = the dialogue ring; a v13/v14 pair is refused). None = cannot."""
        return self._ns_key("wire", int)

    @property
    def dialogue_epoch(self) -> int | None:
        """The host epoch the guest last saw on its lane (1..65535, drawn fresh per host session); -1 = no section 7
        seen yet. A change clears the inbox and re-baselines at the new head -- no history replays."""
        return self._ns_key("epoch", int)

    @property
    def dialogue_head_seq(self) -> int | None:
        """The newest event in the host's ring (u16, skips 0: 65535 -> 1); -1 = no section 7 on the lane right now."""
        return self._ns_key("head_seq", int)

    @property
    def dialogue_last_seen(self) -> int | None:
        """The guest's merge baseline -- the newest ring seq merged (or skipped as history); -1 = not baselined (no
        session: a rising session baselines at the host's head, so what the ring held before it never replays)."""
        return self._ns_key("last_seen", int)

    @property
    def dialogue_gaps(self) -> int | None:
        """Ring gaps the guest detected on this lane (each logged once; their lines fall to the orphan rule) --
        monotonic until the transport resets, so assert on a DELTA."""
        return self._ns_key("gaps", int)

    @property
    def dialogue_heartbeat(self) -> int | None:
        """The host's heartbeat in the latest section 7 (a host Update counter); -1 = no section on the lane."""
        return self._ns_key("heartbeat", int)

    @property
    def dialogue_host_stalled(self) -> bool | None:
        """R6: the host's heartbeat sat still HostStallMs (10 s) on a live lane -- a HUNG host; the lock let go."""
        return self._ns_key("host_stalled", bool)

    @property
    def dialogue_host_flags(self) -> int | None:
        """Section 7's flags byte (:data:`HOST_FLAG_BITS`); -1 = no section on the lane. :attr:`dialogue_host_flag_set`
        names the bits."""
        return self._ns_key("host_flags", int)

    @property
    def dialogue_host_flag_set(self) -> frozenset[str] | None:
        """The names of the set :attr:`dialogue_host_flags` bits (``{"scene", "line", "on_field"}``, ...). None when the
        engine cannot publish them OR no section 7 is on the lane right now (-1) -- an empty set means a section with no
        bit set, never "no section"."""
        flags = self.dialogue_host_flags
        if flags is None or flags < 0:
            return None
        return frozenset(name for name, bit in self.HOST_FLAG_BITS.items() if flags & bit)

    @property
    def dialogue_host_open(self) -> list[dict] | None:
        """The host's open windows per section 7 (``host_open[]``): ``win``, ``text``, ``cursor`` (-1 = not a ready
        choice), ``page``, ``flags`` (b0 choice, b1 complete, b2 inh). ``[]`` = none (or no section); None = cannot."""
        rows = self._ns_key("host_open", list)
        return None if rows is None else [dict(r) for r in rows if isinstance(r, dict)]

    @property
    def dialogue_cursor(self) -> int | None:
        """R4: the host cursor the guest's cursor lock enforced on its last tick (-1 = none) -- the cursor MIRROR."""
        return self._ns_key("cursor", int)

    @property
    def dialogue_key_ignored(self) -> int | None:
        """KEY events this guest ignored: every KEY on an s98 engine (counted, not relayed), only a KEY with no
        host-owned button on s99. Monotonic per lane: assert on a delta."""
        return self._ns_key("key_ignored", int)

    @property
    def bench_host_frozen(self) -> bool | None:
        """The bench host's ``host freeze`` lever (its heartbeat stopped: a hung host, R6)."""
        return self._ns_key("host_frozen", bool)

    @property
    def bench_host_menu(self) -> bool | None:
        """The bench host's ``host menu`` lever (section 7 b4 -- the chip's 'in a menu' variant, R7)."""
        return self._ns_key("host_menu", bool)

    @property
    def bench_host_battle(self) -> bool | None:
        """The bench host's ``host battle`` lever (section 7 b5 -- the chip's 'in a battle' variant, R7)."""
        return self._ns_key("host_battle", bool)

    # [ff9mapkit netsync F3.3] R5 (s99): THE SCRIPT-KEY RELAY -- a host-driven scene's control-off script button polls
    # (B_KEYON/B_KEY) answer to the host's relayed press. Absent ``key_hold`` = an engine whose guest ignores KEY.
    @property
    def script_key_relay(self) -> bool | None:
        """Whether the engine relays script button-polls (s99: ``netsync.key_hold`` is published). False: a ``netsync``
        block without it (s98 counts KEY and ignores it; older engines have no KEY); None: no ``netsync`` block."""
        ns = self.netsync
        if not isinstance(ns, dict):
            return None
        return self._ns_key("key_hold", bool) is not None

    @property
    def script_key_tick(self) -> int | None:
        """The event engine's script KEY TICK: one per EventEngine.ServiceEvents -- field, battle AND world map, so it keeps
        counting through a battle. 0 before the first (a static Int32); -1 only when the agent's netsync block failed to
        build (its catch literal). A relayed press is served for exactly one of them. It counts on vanilla too (inert)."""
        return self._ns_key("key_tick", int)

    @property
    def script_key_hold(self) -> bool | None:
        """The script-key lock on this field: the lock engaged AND (the host busy or holding input here, or a KEY still
        waiting for this field) -- whatever the guest's control (the poll itself also needs control OFF)."""
        return self._ns_key("key_hold", bool)

    @property
    def script_key_reader(self) -> int | None:
        """The last reader uid whose host-owned bits a locked guest masked (-1 = none yet) -- the uid a ``netsync host
        key <uid> <bits>`` must name to reach that poll."""
        return self._ns_key("key_reader", int)

    @property
    def script_keys(self) -> list[dict] | None:
        """The relayed KEY list (``keys[]``, at most 8): ``seq``, ``field``, ``uid``, ``bits`` (compact: b0 Select b1
        Triangle b2 Circle b3 Cross b4 Square b5 Cancel b6 Confirm b7 MenuControl b8 Special b9 Menu), ``cursor`` (-1 =
        none), ``age_ms``, ``state`` (pending = behind the ordering guard, stored, active = served this key tick)."""
        rows = self._ns_key("keys", list)
        return None if rows is None else [dict(r) for r in rows if isinstance(r, dict)]

    @property
    def script_key_served(self) -> int | None:
        """KEYs served to a poll this lane -- monotonic: assert on a delta."""
        return self._ns_key("key_served", int)

    @property
    def script_key_expired(self) -> int | None:
        """KEYs dropped unserved this lane (another field, the 20 s TTL, both sides idle 1500 ms, the cap, a purge)."""
        return self._ns_key("key_expired", int)

    @property
    def script_key_gaveup(self) -> int | None:
        """KEYs the ordering guard (or the cursor wait) gave up on after KeyGuardMs and released anyway."""
        return self._ns_key("key_gaveup", int)

    @property
    def script_key_taps(self) -> int | None:
        """KEY taps THIS process made (a host's ring, or the tap-record tape)."""
        return self._ns_key("key_taps", int)

    @property
    def bench_tap_record(self) -> bool | None:
        """R9: the ``tap-record`` lever (this copy's real host taps record onto the tape while the bench lock is OFF)."""
        return self._ns_key("tap_record", bool)

    @property
    def bench_tape(self) -> int | None:
        """R9: events on the tape (dialog taps + key taps)."""
        return self._ns_key("tape", int)

    @property
    def bench_replay_left(self) -> int | None:
        """R9: taped events a running ``replay`` has yet to feed into the bench host's ring (0 = done / none)."""
        return self._ns_key("replay_left", int)

    # [ff9mapkit netsync F3.3] DIO-1 (s97): THE DIORAMA WARM RETURN. An engine without it publishes no ``diorama`` block:
    # read that as "cannot", never as "cold".
    def _dio_key(self, key: str, kind):
        dio = self.diorama
        if dio is None or key not in dio:
            return None
        v = dio[key]
        if kind is int and (isinstance(v, bool) or not isinstance(v, int)):
            return None
        if kind is not int and not isinstance(v, kind):
            return None
        return v

    @property
    def diorama_warm_return(self) -> bool | None:
        """Whether the engine publishes the DIO-1 warm-return bench (s97: ``netsync.diorama``). None: no ``netsync``
        block at all."""
        ns = self.netsync
        if not isinstance(ns, dict):
            return None
        return isinstance(ns.get("diorama"), dict)

    @property
    def diorama(self) -> dict | None:
        """The ``netsync.diorama`` block, copied: ``booted``, ``boot`` (warm|cold|null), ``boot_why``, ``boot_field``,
        ``boot_x``/``boot_z`` (the controlled actor at a WARM boot -- the ``player.x/z`` source), ``primed``,
        ``returns``, ``last_return`` (warm|cold|reinit-missing|null -- the branch StartEvents REPORTED),
        ``last_return_field``, ``resuming`` (a battle-return bracket open on the live field). None = cannot."""
        dio = self._ns_key("diorama", dict)
        return None if dio is None else dict(dio)

    @property
    def diorama_booted(self) -> bool | None:
        return self._dio_key("booted", bool)

    @property
    def diorama_boot(self) -> str | None:
        """The last boot's return decision: ``"warm"`` (the stock battle-return slot primed) or ``"cold"``; ``""`` = no
        boot yet (published null); None = cannot."""
        dio = self.diorama
        if dio is None or "boot" not in dio:
            return None
        return "" if dio["boot"] is None else str(dio["boot"])

    @property
    def diorama_boot_why(self) -> str | None:
        """The cold reason (one human line); ``""`` = none (a warm boot, or no boot yet); None = cannot."""
        dio = self.diorama
        if dio is None or "boot_why" not in dio:
            return None
        return "" if dio["boot_why"] is None else str(dio["boot_why"])

    @property
    def diorama_boot_field(self) -> int | None:
        return self._dio_key("boot_field", int)

    @property
    def diorama_boot_xz(self) -> tuple[float, float] | None:
        """The controlled actor's (x, z) at a WARM boot -- the same source as ``player.x/z``. None when the last boot was
        not warm (published null), or the engine cannot."""
        x, z = self._dio_key("boot_x", (int, float)), self._dio_key("boot_z", (int, float))
        if x is None or z is None or isinstance(x, bool) or isinstance(z, bool):
            return None
        return float(x), float(z)

    @property
    def diorama_primed(self) -> bool | None:
        """Our warm copy still sits in the engine's battle-return slot (true from a warm boot to its return)."""
        return self._dio_key("primed", bool)

    @property
    def diorama_returns(self) -> int | None:
        """Diorama returns this process -- bumped at the return's StartEvents, BEFORE the actors are placed: compare
        positions only once ``player.control`` is back. Monotonic: assert on a delta."""
        return self._dio_key("returns", int)

    @property
    def diorama_last_return(self) -> str | None:
        """The branch the last return's StartEvents REPORTED: ``"warm"`` (Main_Reinit called), ``"cold"`` (Main_Init),
        ``"reinit-missing"`` (the reinit branch with no Main_Reinit -- a frozen field); ``""`` = none yet; None = cannot."""
        dio = self.diorama
        if dio is None or "last_return" not in dio:
            return None
        return "" if dio["last_return"] is None else str(dio["last_return"])

    @property
    def diorama_last_return_field(self) -> int | None:
        return self._dio_key("last_return_field", int)

    @property
    def diorama_resuming(self) -> bool | None:
        """A battle-return bracket is open on the live field right now (Main_Reinit still running / objects suspended):
        a warm proof asserts it False once control is back, so a frozen field cannot pass on position alone."""
        return self._dio_key("resuming", bool)

    # [ff9mapkit netsync B4] [ff9mapkit netsync B5] s100-s110: THE BATTLE CO-OP LANE -- ``netsync.battle`` (host / peer /
    # menu / end). The same law as F3.2/F3.3, one level deeper: every key is told by its PRESENCE -- an engine without the
    # patch that added it publishes no key, and every accessor below reads that as None ("this engine cannot"), never as
    # 0 / False / [] ("nothing there"). Check the stage's capability property first (``coop_host_gates`` ..
    # ``coop_exit_with_host``, then s106-s110 ``coop_menu_content`` / ``coop_ready_mirror`` / ``coop_result_manifest`` /
    # ``coop_result_replay`` / ``coop_slot_handback``). Strings the engine publishes as null ("none yet") read ``""``; a
    # null RECORD (``host.end``, ``peer.end``, ``menu.captured``; s106-s110 ``menu.roster`` / ``bench_roster`` /
    # ``pending`` / ``feed``, ``host.manifest``, ``host.handback.last``, ``end.replay.screen`` / ``fp``: "none") reads
    # None like an absent one -- tell the two apart by the capability. Counters marked monotonic are per PROCESS: assert
    # on a DELTA. Records and lists are copied DEEP.
    def _nb_key(self, path: str, kind):
        """``netsync.battle.<path>`` read as ``kind``: bool / int (a bool is never an int, an int never a bool), str (null
        -> ""), list (a copy; dict rows copied), dict (a copy; null -> None). None when any step of the path is absent or
        the value has the wrong type."""
        ns = self.netsync
        node = ns.get("battle") if isinstance(ns, dict) else None
        parts = path.split(".")
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        if kind is bool:
            return node if isinstance(node, bool) else None
        if kind is int:
            return node if isinstance(node, int) and not isinstance(node, bool) else None
        if kind is str:
            if node is None:
                return ""
            return node if isinstance(node, str) else None
        if kind is list:
            # [ff9mapkit netsync B5] a DEEP copy: the s106-s110 records nest (manifest rows -> learns, roster slots -> cmds)
            return _json_copy(node) if isinstance(node, list) else None
        if kind is dict:
            return _json_copy(node) if isinstance(node, dict) else None
        raise TypeError(f"_nb_key: no reading for {kind!r}")

    def _nb_cap(self, path: str, kind) -> bool | None:
        """A stage's capability: None = no ``netsync`` block at all; else whether ``netsync.battle.<path>`` is published
        with the right type (an engine before that stage reads False)."""
        if not isinstance(self.netsync, dict):
            return None
        return self._nb_key(path, kind) is not None

    @property
    def coop_host_gates(self) -> bool | None:
        """s100 (B4/B5 stage 1): the host's command-phase gates and the ``netsync.battle`` block -- the verbs
        ``guestslots`` / ``bcmd`` / ``hostgates``. False = a netsync block without ``battle`` (s99 and older)."""
        ns = self.netsync
        if not isinstance(ns, dict):
            return None
        return isinstance(ns.get("battle"), dict)

    @property
    def coop_containment(self) -> bool | None:
        """s101 (stage 2): the guest containment backstop R9 + G2 (``menu.r9_refused``; the verbs ``containment`` /
        ``bctl``; ``battle.units[].cmd_busy``)."""
        return self._nb_cap("menu.r9_refused", int)

    @property
    def coop_stock_menu(self) -> bool | None:
        """s102 (stage 3): the guest stock menu's capture (``menu.captures``; the verb ``bmenu``; ``battle.hud`` /
        ``battle.seq``)."""
        return self._nb_cap("menu.captures", int)

    @property
    def coop_end_trailer(self) -> bool | None:
        """s103 (stage 4): the host END BLOCK on the type-1 lane (``host.end_trail``; the verb ``endbench``;
        ``battle.result_ui``)."""
        return self._nb_cap("host.end_trail", list)

    @property
    def coop_presentation(self) -> bool | None:
        """s104 (stage 5): the guest's victory presentation (``netsync.battle.end`` with ``r8_hits``; ``endbench
        guest``)."""
        return self._nb_cap("end.r8_hits", int)

    @property
    def coop_exit_with_host(self) -> bool | None:
        """s105 (stage 6): the guest's exit with the host (``end.end_leave``; ``endbench exit``)."""
        return self._nb_cap("end.end_leave", dict)

    @property
    def coop_menu_content(self) -> bool | None:
        """s106 (stage 7): the roster-fed menu content (``menu.content_hits``; the verb ``bbench`` with its ``roster`` /
        ``content`` ops; ``battle.hud.mirrored``)."""
        return self._nb_cap("menu.content_hits", dict)

    @property
    def coop_ready_mirror(self) -> bool | None:
        """s107 (stage 8): the production ready mirror + ``[Netsync] GuestStockMenu`` (``menu.stock_owns``; the ``bbench``
        feed ops ``start|stop|ready|caps|mode|freeze|unmap|knob``)."""
        return self._nb_cap("menu.stock_owns", bool)

    @property
    def coop_result_manifest(self) -> bool | None:
        """s108 (stage 9): the host result manifest (``host.manifest_captures``; ``endbench manifest``)."""
        return self._nb_cap("host.manifest_captures", int)

    @property
    def coop_result_replay(self) -> bool | None:
        """s109 (stage 10): the guest result-screen replay (``end.replay``; ``endbench replay|quit|fieldsong``;
        ``battle.result_ui.replay``)."""
        return self._nb_cap("end.replay", dict)

    @property
    def coop_slot_handback(self) -> bool | None:
        """s110 (stage 11): the host's guest-slot hand-back (``host.handback``; the NAMED ops ``bench lapse`` / ``bench
        handback`` -- ⚠ an engine before it reads them as ``bench 1``: probe this first, never send them on False)."""
        return self._nb_cap("host.handback", dict)

    @property
    def coop_peer_end_manifest(self) -> dict | None:
        """s108: ``peer.end.manifest`` -- the DECODED manifest beside the peer end block (the bench seam's preset, or the
        live lane's), copied one level. None = no peer end, no flags b1, a body that did not decode (``peer.end
        .manifest_why`` says which), or an engine before s108."""
        return self._nb_key("peer.end.manifest", dict)

    @property
    def coop_battle(self) -> dict | None:
        """The whole ``netsync.battle`` block, copied one level deep (each sub-object a new dict). None = cannot."""
        b = self.netsync.get("battle") if isinstance(self.netsync, dict) else None
        return None if not isinstance(b, dict) else {k: dict(v) if isinstance(v, dict) else v for k, v in b.items()}

    # ---- host: MY own battle as I stream it (s100; the end block s103)
    coop_host_gates_off = _nb_prop("host.gates_off", bool, "The selftest calibration lever ``hostgates 0`` is pulled.")
    coop_host_guest_slots = _nb_prop("host.guest_slots", int, "The battle lane's GuestSlots, a ``guestslots`` override "
                                                               "included (bit per party slot).")
    coop_host_cmd_phase = _nb_prop("host.cmd_phase", bool, "The pumps' last read of the command phase: PHASE_NORMAL && "
                                                           "FF9BMenu_IsEnable.")
    coop_host_caps = _nb_prop("host.caps", int, "The type-1 header flags byte of the last own-battle sample (bit 1 = a "
                                                "command-phase-gated host); -1 = no own battle.")
    coop_host_ready_mask = _nb_prop("host.ready_mask", int, "The Ready bits of the last own-battle sample (bit per btl "
                                                            "slot); -1 = no own battle.")
    coop_host_cmd_refused = _nb_prop("host.cmd_refused", int, "Intake-guard refusals (a command outside the command "
                                                              "phase) -- monotonic per process.")
    coop_host_cmd_dropped = _nb_prop("host.cmd_dropped", int, "Every other command decline (malformed, not a guest slot, "
                                                              "an empty mask, ...) -- monotonic per process.")
    coop_host_cmd_queued = _nb_prop("host.cmd_queued", int, "Commands queued through SendNetCommand -- monotonic per "
                                                            "process.")
    coop_host_refused_why = _nb_prop("host.refused_why", str, "The last intake refusal's reason ('' = none yet).")
    coop_host_dropped_why = _nb_prop("host.dropped_why", str, "The last drop's reason ('' = none yet).")
    coop_host_roster_lag = _nb_prop("host.roster_lag", int, "Frames from the command phase opening to its first roster; "
                                                            "-1 = none yet this opening.")
    coop_host_loop_cmds = _nb_prop("host.loop_cmds", int, "``bcmd`` frames still parked on the selftest loopback "
                                                          "(drained only inside an own battle).")
    coop_host_end = _nb_prop("host.end", dict, "s103: the END BLOCK the last own-battle sample shipped (kind, kind_name, "
                                               "phase, seq, result, ui, res_state, loading, flags, win_pose, manifest_len); "
                                               "None = no own battle, the ``endbench host off`` lever, or cannot.")
    coop_host_end_trail = _nb_prop("host.end_trail", list, "s103: every DISTINCT 'kind/ui/state' the host shipped this "
                                                           "own battle ('-' = no result screen, an L suffix = Loading) -- "
                                                           "kept after the battle until the next one.")
    coop_host_end_edges = _nb_prop("host.end_edges", int, "s103: samples an end-state change FORCED this own battle (the "
                                                          "stage's effect; 0 under ``endbench host cadence|off``).")
    coop_host_end_changes = _nb_prop("host.end_changes", int, "s103: end-state changes the tracker DETECTED this own "
                                                              "battle (under every lever: the instrument).")
    coop_host_end_mode = _nb_prop("host.end_mode", str, "s103: the ``endbench host`` lever -- 'on' | 'cadence' | 'off'.")
    coop_host_end_cmd = _nb_prop("host.end_cmd", str, "s103: the ``endbench cmd`` one-shot -- '' | 'armed' | "
                                                      "'fired <kind>' | 'failed: ...'.")
    # ---- peer: the battle view I parsed (the selftest loopback's own battle, or a real peer's)
    coop_peer_live = _nb_prop("peer.live", bool, "The parsed battle lane is live (fresh).")
    coop_peer_seq = _nb_prop("peer.seq", int, "The live view's seq; -1 = no live lane.")
    coop_peer_nonce = _nb_prop("peer.nonce", int, "The live view's battle nonce; -1 = no live lane.")
    coop_peer_caps = _nb_prop("peer.caps", int, "The live view's whole header flags byte (bit 1 = a gated host); -1 = no "
                                                "live lane.")
    coop_peer_ready_mask = _nb_prop("peer.ready_mask", int, "The live view's Ready bits; -1 = no live lane.")
    coop_peer_end = _nb_prop("peer.end", dict, "s103: the peer END BLOCK as TryGetPeerEnd serves it -- the selftest "
                                               "``endbench`` seam first (bench True, nonce 181), else the live lane's "
                                               "trailer; host.end's fields + rows, bench, nonce, wire_seq. None = neither "
                                               "(or cannot).")
    coop_peer_end_trail = _nb_prop("peer.end_trail", list, "s103: the same walk as PARSED off the lane (restarted by a "
                                                           "new battle nonce, kept after the lane falls).")
    coop_peer_trailer_bad = _nb_prop("peer.trailer_bad", int, "s103: malformed trailers ignored -- monotonic per process.")
    coop_peer_trailer_skipped = _nb_prop("peer.trailer_skipped", int, "s103: unknown-fmt trailer records skipped -- "
                                                                      "monotonic per process.")
    coop_peer_trailer_why = _nb_prop("peer.trailer_why", str, "s103: the last malformed trailer's reason ('' = none).")
    # ---- menu: the guest's battle menu lane
    coop_menu_roster_slots = _nb_prop("menu.roster_slots", list, "The slots the parsed peer roster carries menus for, "
                                                                 "ascending ([] = no live lane or no roster).")
    coop_menu_r9_refused = _nb_prop("menu.r9_refused", int, "s101: R9 refusals THIS diorama boot (reset by each boot, "
                                                            "kept after the teardown until the next).")
    coop_menu_r9_total = _nb_prop("menu.r9_total", int, "s101: R9 refusals this process -- monotonic.")
    coop_menu_r9_cmd = _nb_prop("menu.r9_cmd", int, "s101: the last refused cmd_no this boot; -1 = none.")
    coop_menu_r9_site = _nb_prop("menu.r9_site", str, "s101: the caller chain that tried it ('BattleHUD.SendNetCommand "
                                                      "< ...'; '' = none).")
    coop_menu_guest_owned = _nb_prop("menu.guest_owned", int, "s101: bit per party slot IsGuestOwnedSlot reads true for "
                                                              "now (G2 holds it 0 inside a diorama).")
    coop_menu_contained = _nb_prop("menu.contained", bool, "s101: NetSyncDiorama.Active -- the predicate R9 and G2 key "
                                                           "on.")
    coop_menu_containment_off = _nb_prop("menu.containment_off", bool, "s101: the calibration lever ``containment 0``.")
    coop_menu_captures = _nb_prop("menu.captures", int, "s102: stock commits forwarded as v1 frames -- monotonic.")
    coop_menu_capture_refused = _nb_prop("menu.capture_refused", int, "s102: stock commits refused (outside the v1 "
                                                                      "scope, or no wire unit) -- monotonic.")
    coop_menu_capture_why = _nb_prop("menu.capture_why", str, "s102: the last capture refusal ('' = none).")
    coop_menu_capture_off = _nb_prop("menu.capture_off", bool, "s102: the calibration lever ``bmenu capture off``.")
    coop_menu_outbox = _nb_prop("menu.outbox", int, "s102: forwarded frames waiting for a transport (no production "
                                                    "drain until stage 8).")
    coop_menu_bench_open = _nb_prop("menu.bench_open", int, "s102: local slots ``bmenu open`` queued this boot (bit per "
                                                            "slot).")
    coop_menu_side_refused = _nb_prop("menu.side_refused", int, "s102: side-path gates fired (OpenMainMenu, manual "
                                                                "Trance, the Vivi swap) -- monotonic.")
    coop_menu_side_why = _nb_prop("menu.side_why", str, "s102: the last side refusal ('' = none).")
    coop_menu_captured = _nb_prop("menu.captured", dict, "s102: the last stock commit this boot forwarded, DECODED by the "
                                                         "host's own decoder (slot, action, menu, id, mask, cursor, "
                                                         "local_slot, cmd, site, hex, action_name). None = none this "
                                                         "boot (or cannot).")
    # ---- end: the guest's presentation of the host's end (s104) and its exit with the host (s105)
    coop_present_injected = _nb_prop("end.injected", bool, "s104: InjectEnd changed the phase this boot (a victory or "
                                                           "close kind).")
    coop_present_held = _nb_prop("end.held", bool, "s104: a defeat/escape HELD this boot (the HUD off, the phase "
                                                   "untouched).")
    coop_present_kind = _nb_prop("end.kind", int, "s104: the host kind presented this boot; -1 = none.")
    coop_present_kind_name = _nb_prop("end.kind_name", str, "s104: its name ('' = none).")
    coop_present_action = _nb_prop("end.action", str, "s104: 'victory' | 'close' | 'hold' ('' = none).")
    coop_present_inject_phase = _nb_prop("end.inject_phase", int, "s104: the btl_phase InjectEnd wrote; -1 = none.")
    coop_present_inject_seq = _nb_prop("end.inject_seq", int, "s104: the btl_seq InjectEnd wrote (4 = "
                                                              "SEQ_MENU_OFF_VICTORY_WITH_ENEMY); -1 = none.")
    coop_present_inject_ms = _nb_prop("end.inject_ms", int, "s104: ms since the injection while this boot lives; -1 "
                                                            "otherwise.")
    coop_present_r8_hits = _nb_prop("end.r8_hits", int, "s104: ManageBattleEnd refusals this boot -- non-decreasing, NOT "
                                                        "per frame (33 of every 256 WAIT frames skip): assert a rise over "
                                                        "seconds, never between polls.")
    coop_present_r8_first_ms = _nb_prop("end.r8_first_ms", int, "s104: injection -> the first R8 hit (the guest's own "
                                                                "presentation done); -1 = none.")
    coop_present_w1_armed = _nb_prop("end.w1_armed", bool, "s104: the host reached ui >= 1 since the injection.")
    coop_present_watchdog = _nb_prop("end.watchdog", str, "s104: 'W1' | 'W2' | 'W2+W1' ('' = none fired).")
    coop_present_blocker = _nb_prop("end.blocker", str, "s104: W2's named blocker ('' = W2 did not fire).")
    coop_present_why = _nb_prop("end.why", str, "s104: the latest reason the end is not presented ('' = presented, or "
                                                "nothing to present).")
    coop_present_faulted = _nb_prop("end.faulted", bool, "s104: EndTick threw and stopped for this boot.")
    coop_present_hud_reasserts = _nb_prop("end.hud_reasserts", int, "s104: a swallowed HUD hide re-applied.")
    coop_present_guest_mode = _nb_prop("end.guest_mode", str, "s104: the ``endbench guest`` lever -- 'on' | 'off' | "
                                                              "'settle'.")
    coop_present_ach_held = _nb_prop("end.ach_held", int, "s104: achievement reports a booted diorama held -- monotonic "
                                                          "per process.")
    coop_present_ach_enemy_no = _nb_prop("end.ach_enemy_no", int, "s104: the save-persistent battle-achievement counter "
                                                                  "R8 protects (an invariant probe); -1 = unreadable.")
    coop_present_music = _nb_prop("end.music", int, "s104: the current music id (the stock victory tail plays song 5).")
    coop_present_btl_flag = _nb_prop("end.btl_flag", int, "s104: the raw btl_flag (32 = BTL_PLAY_END_SONG, 64 = "
                                                          "BTL_END_LOAD).")
    coop_exit_mode = _nb_prop("end.exit_mode", str, "s105: the ``endbench exit`` lever -- 'on' | 'off'.")
    coop_end_leave = _nb_prop("end.end_leave", dict, "s105: the whole ``end_leave`` block, copied.")
    coop_exit_trigger = _nb_prop("end.end_leave.trigger", str, "s105: the host exit that latched -- 'result-hide' | "
                                                               "'game-over' | 'title' ('' = not yet).")
    coop_exit_latched_ms = _nb_prop("end.end_leave.latched_ms", int, "s105: ms since the latch while this boot lives; "
                                                                     "-1 otherwise.")
    coop_exit_tries = _nb_prop("end.end_leave.tries", int, "s105: Leave() calls the end-leave made (1 per second at "
                                                           "most).")
    coop_exit_deferred = _nb_prop("end.end_leave.deferred", int, "s105: attempts a scene fade deferred.")
    coop_exit_requested = _nb_prop("end.end_leave.requested", bool, "s105: the end-leave's Leave issued its Replace.")
    coop_exit_request_ms = _nb_prop("end.end_leave.request_ms", int, "s105: latch -> request, ms; -1 = none.")
    coop_exit_why = _nb_prop("end.end_leave.why", str, "s105: why it has not left ('' = requested).")
    coop_exit_settled = _nb_prop("end.end_leave.settled", bool, "s105: a Leave of a FINISHED fight settled the return "
                                                                "this boot.")
    coop_exit_via = _nb_prop("end.end_leave.via", str, "s105: 'end-leave' | 'leave' ('' = no settle).")
    coop_exit_stamp = _nb_prop("end.end_leave.stamp", int, "s105: the btl_result decided for the return (pending or "
                                                           "written); -1 = none.")
    coop_exit_stamp_host = _nb_prop("end.end_leave.stamp_host", int, "s105: the host's raw result it came from; -1 = no "
                                                                     "settle.")
    coop_exit_stamped = _nb_prop("end.end_leave.stamped", int, "s105: what the teardown wrote; -1 = not yet / never.")
    coop_exit_stamped_was = _nb_prop("end.end_leave.stamped_was", int, "s105: the guest's own btl_result just before; "
                                                                       "-1 = none.")
    coop_exit_music_shut = _nb_prop("end.end_leave.music_shut", bool, "s105: ff9ShutdownStateBattleResult ran at the "
                                                                      "Leave.")
    coop_exit_music_why = _nb_prop("end.end_leave.music_why", str, "s105: why it did not ('' = it did, or no settle).")
    coop_exit_wipe_lifted = _nb_prop("end.end_leave.wipe_lifted", bool, "s105: the teardown lifted this boot's injected "
                                                                        "end fade.")
    coop_declined = _nb_prop("end.declined", dict, "s105: the watcher's late-join declines, copied.")
    coop_declined_count = _nb_prop("end.declined.count", int, "s105: late joins declined -- monotonic per process.")
    coop_declined_nonce = _nb_prop("end.declined.nonce", int, "s105: the last declined battle nonce; -1 = none.")
    coop_declined_why = _nb_prop("end.declined.why", str, "s105: its reason ('' = none).")
    # ---- menu: s106 (stage 7) the roster-fed content
    coop_menu_mirrored = _nb_prop("menu.mirrored", list, "s106: the LOCAL party slots (ascending) whose stock panels draw "
                                                         "the menu roster inside a diorama ([] = none).")
    coop_menu_roster_src = _nb_prop("menu.roster_src", str, "s106: the menu roster in effect -- 'bench' | 'peer' ('' = "
                                                            "none).")
    coop_menu_roster_sig = _nb_prop("menu.roster_sig", str, "s106: its content signature '0x...' (battlewire."
                                                            "roster_sig_text; equal = the same content; '' = none).")
    coop_menu_roster_gen = _nb_prop("menu.roster_gen", int, "s106: the content generation the HUD last saw (moves only "
                                                            "while a diorama menu is up).")
    coop_menu_roster_painted = _nb_prop("menu.roster_painted", int, "s106: the generation the HUD last repainted for.")
    coop_menu_content_off = _nb_prop("menu.content_off", int, "s106: the ``bbench content`` lever -- bit per hook turned "
                                                              "OFF (1 command .. 64 refresh; 0 = production).")
    coop_content_hits = _nb_prop("menu.content_hits", dict, "s106: the whole ``content_hits`` block, copied.")
    coop_content_hits_command = _nb_prop("menu.content_hits.command", int, "s106: hook (1) answers that replaced stock "
                                                                           "content -- monotonic per process.")
    coop_content_hits_grey = _nb_prop("menu.content_hits.grey", int, "s106: hook (2) -- monotonic.")
    coop_content_hits_ability = _nb_prop("menu.content_hits.ability", int, "s106: hook (3) -- monotonic.")
    coop_content_hits_bag = _nb_prop("menu.content_hits.bag", int, "s106: hook (4) -- monotonic.")
    coop_content_hits_count = _nb_prop("menu.content_hits.count", int, "s106: hook (5) -- monotonic.")
    coop_content_hits_cast = _nb_prop("menu.content_hits.cast", int, "s106: hook (6) -- monotonic.")
    coop_content_hits_refresh = _nb_prop("menu.content_hits.refresh", int, "s106: hook (7), repaints -- monotonic.")
    coop_menu_content_faults = _nb_prop("menu.content_faults", int, "s106: hook faults swallowed -- monotonic.")
    coop_menu_content_why = _nb_prop("menu.content_why", str, "s106: the last hook fault ('' = none).")
    coop_menu_mute_held = _nb_prop("menu.mute_held", bool, "s106: a repaint's MuteActiveSound is still held.")
    coop_menu_roster = _nb_prop("menu.roster", dict, "s106: the menu roster ({slots[] {wire, cmds[] {menu, cmd, type, "
                                                     "abils, on}}, items[] {id, count}}); None = none (or cannot).")
    coop_menu_bench_roster = _nb_prop("menu.bench_roster", dict, "s106: what ``bbench roster`` armed (src, bytes, slot, "
                                                                 "wire, the markers ...; -1 = not fabricated); None = "
                                                                 "no bench roster (or cannot).")
    # ---- menu: s107 (stage 8) the production ready mirror
    coop_stock_owns = _nb_prop("menu.stock_owns", bool, "s107: the stock menu (not the digit panel) owns the guest's "
                                                        "slots right now.")
    coop_stock_why = _nb_prop("menu.why", str, "s107: the first missing ownership condition, or 'waiting: <gate>' ('' = "
                                               "serving).")
    coop_stock_knob = _nb_prop("menu.knob", int, "s107: the effective [Netsync] GuestStockMenu, 1/0.")
    coop_stock_knob_bench = _nb_prop("menu.knob_bench", int, "s107: the ``bbench knob`` override; -1 = the ini.")
    coop_assist_slot = _nb_prop("menu.assist_slot", int, "s107: the WIRE slot the digit panel serves; -1 = none.")
    coop_stranded = _nb_prop("menu.stranded", list, "s107: WIRE slots Ready but stranded to the digit panel this turn "
                                                    "(no local seat, refused by the feeder, or no roster after 2.5 s).")
    coop_pending = _nb_prop("menu.pending", dict, "s107: {slot (local), wire, ms, seqs} -- the lowest forwarded command "
                                                  "awaiting the host's verdict; None = none (or cannot).")
    coop_pending_mask = _nb_prop("menu.pending_mask", int, "s107: LOCAL slots with a pending command.")
    coop_mirror_refused = _nb_prop("menu.refused", int, "s107: pending commands the host left Ready >= 2.5 s and >= 3 "
                                                        "samples (reopened with a buzzer) -- monotonic.")
    coop_stock_sent = _nb_prop("menu.sent", int, "s107: forwarded frames handed to a transport (the socket or the bench "
                                                 "host) -- monotonic.")
    coop_mirror = _nb_prop("menu.mirror", dict, "s107: the whole ``mirror`` block, copied.")
    coop_mirror_serving = _nb_prop("menu.mirror.serving", bool, "s107: the mirror's last tick served.")
    coop_mirror_open = _nb_prop("menu.mirror.open", int, "s107: LOCAL slots the mirror holds on ReadyQueue (a mask).")
    coop_mirror_fed = _nb_prop("menu.mirror.fed", int, "s107: slots the mirror opened -- monotonic.")
    coop_mirror_accepted = _nb_prop("menu.mirror.accepted", int, "s107: pending commands whose bit fell -- monotonic.")
    coop_mirror_obsolete = _nb_prop("menu.mirror.obsolete", int, "s107: pending commands a new nonce or a KO voided -- "
                                                                 "monotonic.")
    coop_mirror_closed = _nb_prop("menu.mirror.closed", int, "s107: slots the mirror closed -- monotonic.")
    coop_mirror_no_roster = _nb_prop("menu.mirror.no_roster", int, "s107: WIRE slots Ready but absent from the menu "
                                                                   "roster (waiting; a mask).")
    coop_mirror_faulted = _nb_prop("menu.mirror.faulted", bool, "s107: the mirror faulted this boot (the digit panel "
                                                                "serves).")
    coop_mirror_fault_why = _nb_prop("menu.mirror.fault_why", str, "s107: why ('' = none).")
    coop_feed = _nb_prop("menu.feed", dict, "s107: the selftest bench feed ({guest_slots, ready, caps, mode, frozen, "
                                            "unmap, nonce, seq, live, menu_open, frames, taken, accepted, refused, bad, "
                                            "last}); None = not running (or cannot).")
    # ---- host / peer: s108 (stage 9) the result manifest
    coop_host_manifest = _nb_prop("host.manifest", dict, "s108: the host's last captured manifest (battlewire."
                                                         "published_manifest's shape); None = none this battle (or "
                                                         "cannot).")
    coop_host_manifest_bytes = _nb_prop("host.manifest_bytes", int, "s108: the captured manifest's ENCODED size while "
                                                                    "its battle lasts -- NOT a shipping signal (read "
                                                                    "host.end.flags & 2 / manifest_len).")
    coop_host_manifest_captures = _nb_prop("host.manifest_captures", int, "s108: manifests captured -- monotonic.")
    coop_host_manifest_skipped = _nb_prop("host.manifest_skipped", int, "s108: result screens that captured nothing -- "
                                                                        "monotonic.")
    coop_host_manifest_why = _nb_prop("host.manifest_why", str, "s108: why the last InitialNormal captured nothing ('' = "
                                                                "it did).")
    coop_host_manifest_mode = _nb_prop("host.manifest_mode", str, "s108: the ``endbench manifest host`` lever -- 'on' | "
                                                                  "'off'.")
    coop_host_overflow = _nb_prop("host.overflow", bool, "s108: the sticky host tap in UpdateItem (an item did not fit).")
    coop_host_learned = _nb_prop("host.learned", list, "s108: each ApLearned the host's screen fired: [{slot, abil, "
                                                       "ap_at}].")
    coop_peer_manifest_bad = _nb_prop("peer.manifest_bad", int, "s108: flags-b1 bodies that did not decode -- monotonic.")
    coop_peer_manifest_bad_why = _nb_prop("peer.manifest_bad_why", str, "s108: the last one's reason ('' = none).")
    coop_peer_manifest_nonce = _nb_prop("peer.manifest_nonce", int, "s108: the battle nonce of the manifest the guest "
                                                                    "STORED off the live lane; -1 = none.")
    coop_peer_manifest_rx = _nb_prop("peer.manifest_rx", int, "s108: distinct manifests stored -- monotonic (the bench "
                                                              "seam never stores one).")
    coop_peer_bench_manifest = _nb_prop("peer.bench_manifest", int, "s108: the ``endbench manifest`` preset in the "
                                                                    "template; 0 = none.")
    coop_peer_bench_manifest_note = _nb_prop("peer.bench_manifest_note", str, "s108: a marker that preset could not "
                                                                              "choose ('' = every one).")
    # ---- end: s109 (stage 10) the result-screen replay
    coop_replay = _nb_prop("end.replay", dict, "s109: the whole ``replay`` block, copied.")
    coop_replay_mode = _nb_prop("end.replay.mode", str, "s109: the ``endbench replay`` lever -- 'on' | 'off' | 'local'.")
    coop_replay_armed = _nb_prop("end.replay.armed", bool, "s109: armed this boot.")
    coop_replay_pending = _nb_prop("end.replay.pending", bool, "s109: armed, the screen's Show not run yet.")
    coop_replay_opened = _nb_prop("end.replay.opened", bool, "s109: the Show took the arm.")
    coop_replay_live = _nb_prop("end.replay.live", bool, "s109: pending, or on screen and neither closed nor aborted.")
    coop_replay_closed = _nb_prop("end.replay.closed", bool, "s109: its own hide tail ran.")
    coop_replay_aborted = _nb_prop("end.replay.aborted", bool, "s109: a leave / the teardown / a fault ended it first.")
    coop_replay_abort_why = _nb_prop("end.replay.abort_why", str, "s109: why ('' = not aborted).")
    coop_replay_refused = _nb_prop("end.replay.refused", bool, "s109: no manifest row matched a seated member (sticky).")
    coop_replay_verdict = _nb_prop("end.replay.verdict", int, "s109: the last ArmVerdict (battlewire.ARM_*); -1 = never "
                                                              "asked this boot.")
    coop_replay_why = _nb_prop("end.replay.why", str, "s109: its reason (battlewire.arm_why; '' = go or never asked).")
    coop_replay_row_mask = _nb_prop("end.replay.row_mask", int, "s109: the valid rows at the arm.")
    coop_replay_seated_mask = _nb_prop("end.replay.seated_mask", int, "s109: the seated slots at the arm.")
    coop_replay_manifest_rows = _nb_prop("end.replay.manifest_rows", int, "s109: the manifest's rows at the arm.")
    coop_replay_host_state_at_arm = _nb_prop("end.replay.host_state_at_arm", int, "s109: the host's ResultState at the "
                                                                                  "arm; -1 = not armed.")
    coop_replay_bench = _nb_prop("end.replay.bench", bool, "s109: armed off the endbench seam.")
    coop_replay_arm_ms = _nb_prop("end.replay.arm_ms", int, "s109: injection -> arm; -1 = not armed.")
    coop_replay_open_ms = _nb_prop("end.replay.open_ms", int, "s109: arm -> Show; -1 = not opened.")
    coop_replay_close_ms = _nb_prop("end.replay.close_ms", int, "s109: arm -> its hide tail; -1 = not closed.")
    coop_replay_exit_waited = _nb_prop("end.replay.exit_waited", bool, "s109: the end-leave waited for it.")
    coop_replay_exit_wait_ms = _nb_prop("end.replay.exit_wait_ms", int, "s109: latch -> the wait's end; -1 = never / still "
                                                                        "waiting.")
    coop_replay_screen = _nb_prop("end.replay.screen", dict, "s109: the result screen's own replay receipts (state, "
                                                             "host_state, follow, steps, trail, local_confirms, rows, "
                                                             "gil, learned, overflow_shown, writes, ...); None = no "
                                                             "result screen object (or cannot).")
    coop_replay_fp = _nb_prop("end.replay.fp", dict, "s109: THE WRITE GUARD's fingerprint read LIVE (hash, gil, items, "
                                                     "item_sum, players, level_sum, exp_sum, pa_sum, cards, abilities, "
                                                     "passive); None = unreadable (or cannot).")
    # ---- host: s110 (stage 11) the guest-slot hand-back
    coop_handback = _nb_prop("host.handback", dict, "s110: the whole ``handback`` block, copied.")
    coop_handback_off = _nb_prop("host.handback.off", bool, "s110: the ``bench handback 0`` calibration lever.")
    coop_handback_held = _nb_prop("host.handback.held", int, "s110: the guest slot the host's own window holds; -1 = none "
                                                             "/ between battles.")
    coop_handback_held_ms = _nb_prop("host.handback.held_ms", int, "s110: how long; -1 = none.")
    coop_handback_owed = _nb_prop("host.handback.owed", bool, "s110: the held slot is guest-owned again (a hand-back is "
                                                              "due).")
    coop_handback_g6_mask = _nb_prop("host.handback.g6_mask", int, "s110: Ready bits G6 withheld in the last own-battle "
                                                                   "sample; -1 = no sample.")
    coop_handback_captures = _nb_prop("host.handback.captures", int, "s110: holds of a guest slot by the host's window -- "
                                                                     "monotonic.")
    coop_handback_returns = _nb_prop("host.handback.returns", int, "s110: hand-backs fired -- monotonic.")
    coop_handback_deferred = _nb_prop("host.handback.deferred", int, "s110: holds whose hand-back waited (a submenu, a "
                                                                     "hidden HUD) -- monotonic.")
    coop_handback_faults = _nb_prop("host.handback.faults", int, "s110: attempts that threw -- monotonic.")
    coop_handback_last = _nb_prop("host.handback.last", dict, "s110: {slot, frame, held_ms, why ('handed back' | "
                                                              "'deferred: ...')}; None = none yet (or cannot).")
    coop_handback_lapse = _nb_prop("host.handback.lapse", dict, "s110: the whole ``lapse`` block, copied.")
    coop_lapse_active = _nb_prop("host.handback.lapse.active", bool, "s110: a ``bench lapse`` stall is in force.")
    coop_lapse_hold = _nb_prop("host.handback.lapse.hold", bool, "s110: ...as ``hold`` (until ``bench lapse end``).")
    coop_lapse_left_ms = _nb_prop("host.handback.lapse.left_ms", int, "s110: ms left on a TIMED lapse; -1 = none or "
                                                                      "hold.")
    coop_lapse_count = _nb_prop("host.handback.lapse.count", int, "s110: lapses armed -- monotonic.")
    coop_lapse_end_frame = _nb_prop("host.handback.lapse.end_frame", int, "s110: the frame the last lapse ended (a "
                                                                          "hand-back's latency is last.frame - this); "
                                                                          "-1 = not yet.")

    # [ff9mapkit netsync R3 s111-s117] BATTLE CO-OP ROUND 3 (studies/battle-coop/R3-DESIGN.md 5.1): the same law -- every
    # key told by its PRESENCE, absent = None ("this engine cannot"). The capabilities: s111 ``coop_intro_mirror``
    # (``netsync.diorama.intro``), s112 ``coop_swirl_clamp`` (``netsync.diorama.intro.swirl_clamp``), s113
    # ``coop_wait_parity`` (``host.wait``), s114 ``coop_start_hold`` (``host.start_hold``), s115 ``coop_flee``
    # (``end.flee``), s116 ``coop_flee_gil`` (``end.flee.msg_gil``), s117 ``coop_defeat`` (``end.follow_msg``). ⚠ s111-s114
    # ride the OLD ``bench`` sub-verb: an engine before each reads its op as ``bench 1`` -- probe first.
    @property
    def coop_intro_mirror(self) -> bool | None:
        """s111: the battle intro mirror (``netsync.diorama.intro``; ``host.cfg`` / ``host.intro``; the ``bench intro`` /
        ``bench cfg`` ops, ``battle ... rand``, ``dioboot ... [wire] [skip|play|own] [rand]``)."""
        if not isinstance(self.netsync, dict):
            return None
        return self._dio_path("intro", dict) is not None

    @property
    def coop_swirl_clamp(self) -> bool | None:
        """s112: the diorama swirl clamp (``netsync.diorama.intro.swirl_clamp``; ``bench swirl local|clamp``)."""
        if not isinstance(self.netsync, dict):
            return None
        return self._dio_path("intro.swirl_clamp", dict) is not None

    @property
    def coop_wait_parity(self) -> bool | None:
        """s113: Wait parity (``host.wait``; ``menu.ctl``; ``bench waitparity`` / ``bench ctl`` / ``bench cfg atb`` /
        ``bench lapse ... reserve``)."""
        return self._nb_cap("host.wait", dict)

    @property
    def coop_start_hold(self) -> bool | None:
        """s114: the start hold (``host.start_hold``; ``menu.ctl`` nonce/boot; ``netsync.diorama.live``; ``bench boot`` /
        ``bench starthold``)."""
        return self._nb_cap("host.start_hold", dict)

    @property
    def coop_flee(self) -> bool | None:
        """s115: the guest's flee presentation (``end.flee``; ``end_leave.reverted``; ``battle.units[].mot|disappear|z``;
        ``endbench guest hold|nor9b``)."""
        return self._nb_cap("end.flee", dict)

    @property
    def coop_flee_gil(self) -> bool | None:
        """s116: the host's "Dropped N Gil" relayed (``end.flee.msg_gil``; ``host.flee_gil``; ``host.end`` / ``peer.end``
        ``flee_gil``; ``endbench fleegil``)."""
        return self._nb_cap("end.flee.msg_gil", int)

    @property
    def coop_defeat(self) -> bool | None:
        """s117: the guest's defeat presentation (``end.follow_msg``; ``endbench kill`` / ``phase-defeat``)."""
        return self._nb_cap("end.follow_msg", str)

    # ---- host: s111 the intro mirror's host half
    coop_host_cfg = _nb_prop("host.cfg", dict, "s111: the whole ``cfg`` block, copied (LIVE reads).")
    coop_cfg_atb = _nb_prop("host.cfg.atb", int, "s111: cfg.atb -- 0 Active, 1 Wait (a ``bench cfg atb`` override shows "
                                                 "here); -1 = unreadable.")
    coop_cfg_skip_btl_camera = _nb_prop("host.cfg.skip_btl_camera", int, "s111: cfg.skip_btl_camera (0 = skip the intro "
                                                                         "camera on a random encounter; a ``bench cfg "
                                                                         "skipcam`` override shows here).")
    coop_cfg_speed = _nb_prop("host.cfg.speed", int, "s111: [Battle] Speed.")
    coop_cfg_swirl_frames = _nb_prop("host.cfg.swirl_frames", int, "s111: [Graphics] BattleSwirlFrames.")
    coop_host_intro = _nb_prop("host.intro", dict, "s111: the whole ``intro`` block, copied.")
    coop_intro_off = _nb_prop("host.intro.off", bool, "s111: the ``bench intro 0`` calibration lever.")
    coop_intro_published = _nb_prop("host.intro.published", int, "s111: the intro the last own-battle sample carried (1 "
                                                                 "skip, 0 play; -1 = no intro bits or no own battle).")
    coop_intro_own_skip = _nb_prop("host.intro.own_skip", int, "s111: the rising edge's latch (1 skipped, 0 played; -1 = "
                                                               "none / between battles).")
    # ---- host / menu: s113 Wait parity
    coop_host_wait = _nb_prop("host.wait", dict, "s113: the whole ``wait`` block, copied.")
    coop_wait_parity_off = _nb_prop("host.wait.parity_off", bool, "s113: the ``bench waitparity 0`` calibration lever.")
    coop_wait_menu = _nb_prop("host.wait.menu", int, "s113: byte 1 of the last valid control frame the host parsed (0 "
                                                     "shut, 1 legacy, 2 root, 3 below the root; -1 = none).")
    coop_wait_open = _nb_prop("host.wait.open", bool, "s113: RemoteMenuOpen now (turn-based freezes on it).")
    coop_wait_deep = _nb_prop("host.wait.deep", bool, "s113: RemoteMenuDeep now (the Wait branch freezes on it).")
    coop_wait_legacy_seen = _nb_prop("host.wait.legacy_seen", bool, "s113: a legacy 1 arrived this own battle.")
    coop_lapse_reserve = _nb_prop("host.handback.lapse.reserve", bool, "s113: the running lapse re-serves the guest's "
                                                                       "last frame for 2000 ms first (``reserve``).")
    coop_menu_ctl = _nb_prop("menu.ctl", dict, "s113: the whole ``ctl`` block, copied.")
    coop_ctl_menu = _nb_prop("menu.ctl.menu", int, "s113: byte 1 of the control frame my guest side built last (-1 = "
                                                   "none).")
    coop_ctl_hex = _nb_prop("menu.ctl.hex", str, "s113: that frame ('' = none).")
    coop_ctl_src = _nb_prop("menu.ctl.src", str, "s113: what decided byte 1 -- 'none' | 'bench' | 'digit' | 'stock' | "
                                                 "'root' ('' = none).")
    coop_ctl_nonce = _nb_prop("menu.ctl.nonce", int, "s114: the host battle nonce that frame's trailer reports on (-1 = "
                                                     "none).")
    coop_ctl_boot = _nb_prop("menu.ctl.boot", int, "s114: its boot state 0-4 (-1 = none).")
    coop_ctl_boot_name = _nb_prop("menu.ctl.boot_name", str, "s114: its name ('' = none).")
    # ---- host: s114 the start hold
    coop_start_hold_block = _nb_prop("host.start_hold", dict, "s114: the whole ``start_hold`` block, copied.")
    coop_hold_off = _nb_prop("host.start_hold.off", bool, "s114: the cap reads 0 (StartHoldMs 0, or ``bench starthold "
                                                          "0``).")
    coop_hold_cap_ms = _nb_prop("host.start_hold.cap_ms", int, "s114: the cap now (LIVE).")
    coop_hold_state = _nb_prop("host.start_hold.state", str, "s114: 'idle' | 'off' | 'intro' | 'primed' | 'holding' | "
                                                             "'late' | 'released' | 'not_armed'.")
    coop_hold_nonce = _nb_prop("host.start_hold.nonce", int, "s114: the own battle's nonce (-1 between).")
    coop_hold_why = _nb_prop("host.start_hold.why", str, "s114: the opening's decision ('booting' | 'late' | 'live' | "
                                                         "'declined' | 'busy' | 'none' | 'link' | 'stale nonce' | 'old "
                                                         "guest' | 'no word yet' | 'unknown'; '' = undecided).")
    coop_hold_release = _nb_prop("host.start_hold.release", str, "s114: 'live' | 'declined' | 'link' | 'old guest' | "
                                                                 "'cap' | 'ended' | 'off' ('' = none).")
    coop_hold_held_ms = _nb_prop("host.start_hold.held_ms", int, "s114: running while it holds, else the released hold's "
                                                                 "length; -1 = none.")
    coop_hold_late_ms = _nb_prop("host.start_hold.late_ms", int, "s114: a late arm's offset from the opening; -1 = none.")
    coop_hold_count = _nb_prop("host.start_hold.count", int, "s114: holds armed -- monotonic.")
    coop_hold_released = _nb_prop("host.start_hold.released", dict, "s114: releases per reason, copied -- monotonic.")
    coop_hold_released_live = _nb_prop("host.start_hold.released.live", int, "s114: -- monotonic.")
    coop_hold_released_declined = _nb_prop("host.start_hold.released.declined", int, "s114: -- monotonic.")
    coop_hold_released_link = _nb_prop("host.start_hold.released.link", int, "s114: -- monotonic.")
    coop_hold_released_oldguest = _nb_prop("host.start_hold.released.oldguest", int, "s114: -- monotonic.")
    coop_hold_released_cap = _nb_prop("host.start_hold.released.cap", int, "s114: -- monotonic.")
    coop_hold_released_ended = _nb_prop("host.start_hold.released.ended", int, "s114: -- monotonic.")
    coop_hold_guest = _nb_prop("host.start_hold.guest", dict, "s114: the guest's last report as parsed, copied.")
    coop_hold_guest_r3 = _nb_prop("host.start_hold.guest.r3", bool, "s114: a trailer arrived at all this process.")
    coop_hold_guest_lane_ms = _nb_prop("host.start_hold.guest.lane_ms", int, "s114: since the last valid control frame; "
                                                                             "-1 = none within a minute.")
    coop_hold_guest_fmt = _nb_prop("host.start_hold.guest.fmt", int, "s114: byte 2 of the last valid frame (1 a report, 0 "
                                                                     "a 2-byte frame; -1 = none).")
    coop_hold_guest_nonce = _nb_prop("host.start_hold.guest.nonce", int, "s114: the report's host battle nonce (-1 = "
                                                                         "none).")
    coop_hold_guest_boot = _nb_prop("host.start_hold.guest.boot", int, "s114: the report's boot state (-1 = none).")
    coop_hold_guest_boot_name = _nb_prop("host.start_hold.guest.boot_name", str, "s114: its name ('' = none).")
    # ---- host / end: s115-s117 flee and defeat
    coop_host_flee_gil = _nb_prop("host.flee_gil", int, "s116: the host tap's receipt -- the gil this own battle's stock "
                                                        "escape tail dropped (-1 = none; kept until the next own battle).")
    coop_exit_reverted = _nb_prop("end.end_leave.reverted", int, "s115: the local btl_result the scoped no-leak rule "
                                                                 "reverted (-1 = none).")
    coop_end_flee = _nb_prop("end.flee", dict, "s115: the whole ``flee`` block, copied.")
    coop_flee_r9b = _nb_prop("end.flee.r9b", int, "s115: the escape tail's STATE half skipped by R9b this boot.")
    coop_flee_bypassed = _nb_prop("end.flee.bypassed", int, "s115: the ``guest nor9b`` lever let stock run it (the red).")
    coop_flee_overload = _nb_prop("end.flee.overload", bool, "s115: an IOverloadOnFleeScript was loaded at R9b.")
    coop_flee_ability_flag = _nb_prop("end.flee.ability_flag", bool, "s115: LIVE btl_flag & BTL_FLAG_ABILITY_FLEE.")
    coop_flee_gil_now = _nb_prop("end.flee.gil_now", int, "s115: LIVE party.gil -- read it WHILE booted (the teardown's "
                                                          "Restore puts it back).")
    coop_flee_penalty = _nb_prop("end.flee.penalty", int, "s115: the stock default method's gil penalty (frozen at R9b, "
                                                          "else live while booted; -1 otherwise).")
    coop_flee_msg_gil = _nb_prop("end.flee.msg_gil", int, "s116: the HOST's \"Dropped N Gil\" figure this boot's run-away "
                                                          "showed (-1 = none).")
    coop_follow_msg = _nb_prop("end.follow_msg", str, "s117: the stock follow message this boot's end showed -- "
                                                      "'annihilated' | 'dropped-gil' ('' = none).")

    # ---- netsync.diorama: s111 the intro mirror's guest half (THIS boot only; sentinels between boots)
    diorama_intro = _dio_prop("intro", dict, "s111: the whole ``intro`` block, copied (``swirl_clamp`` inside).")
    diorama_intro_wire = _dio_prop("intro.wire", int, "s111: the host's choice the boot carries (1 skip, 0 play; -1 = none "
                                                      "-- a manual boot, the F6 wire bench, an s110 host).")
    diorama_intro_applied = _dio_prop("intro.applied", str, "s111: the last SkipBattleIntro answer -- 'skip' | 'play' ('' "
                                                            "= no call yet).")
    diorama_intro_own = _dio_prop("intro.own", str, "s111: the stock value it was handed ('skip' | 'play' | '').")
    diorama_intro_off = _dio_prop("intro.off", bool, "s111: the ``bench intro 0`` lever.")
    diorama_intro_calls = _dio_prop("intro.calls", int, "s111: stock-site calls the HOST's choice decided this boot.")
    diorama_intro_normal_ms = _dio_prop("intro.normal_ms", int, "s111: Boot -> the first steady frame, swirl included; "
                                                                "-1 = not yet.")
    diorama_intro_swirl_frames = _dio_prop("intro.swirl_frames", int, "s111: this process's own BattleSwirlFrames (s112: "
                                                                      "the ``bench swirl local`` stand-in while set).")
    # ---- s112 the swirl clamp
    diorama_swirl_clamp = _dio_prop("intro.swirl_clamp", dict, "s112: the whole ``swirl_clamp`` block, copied.")
    diorama_swirl_ini = _dio_prop("intro.swirl_clamp.ini", int, "s112: [Netsync] DioramaSwirlFrames as loaded (-1 = keep "
                                                                "own).")
    diorama_swirl_clamp_now = _dio_prop("intro.swirl_clamp.clamp", int, "s112: what a diorama swirl applies now (-1 = "
                                                                        "off).")
    diorama_swirl_src = _dio_prop("intro.swirl_clamp.src", str, "s112: 'ini' | 'bench'.")
    diorama_swirl_bench_local = _dio_prop("intro.swirl_clamp.bench_local", int, "s112: the ``bench swirl local`` stand-in "
                                                                                "(-1 = none).")
    diorama_swirl_diorama = _dio_prop("intro.swirl_clamp.diorama", bool, "s112: the LAST swirl was a diorama's.")
    diorama_swirl_own = _dio_prop("intro.swirl_clamp.own", int, "s112: its own length (frames).")
    diorama_swirl_used = _dio_prop("intro.swirl_clamp.used", int, "s112: the frames it played.")
    diorama_swirl_clamped = _dio_prop("intro.swirl_clamp.clamped", bool, "s112: used != own.")
    diorama_swirl_dwell_ms = _dio_prop("intro.swirl_clamp.dwell_ms", int, "s112: SFX_Rush's constructor -> its first done "
                                                                          "frame; -1 = not done / none.")
    diorama_swirl_swirls = _dio_prop("intro.swirl_clamp.swirls", int, "s112: swirls this process -- monotonic.")
    diorama_swirl_dioramas = _dio_prop("intro.swirl_clamp.dioramas", int, "s112: ...inside a booted diorama -- "
                                                                          "monotonic.")
    diorama_swirl_clamps = _dio_prop("intro.swirl_clamp.clamps", int, "s112: ...shortened by the clamp -- monotonic.")
    # ---- s114 the start-hold report's LIVE latch
    diorama_live = _dio_prop("live", dict, "s114: the whole ``live`` block, copied.")
    diorama_live_latched = _dio_prop("live.latched", bool, "s114: this boot's first steady frame came with a host sample in "
                                                           "hand.")
    diorama_live_ms = _dio_prop("live.ms", int, "s114: Boot -> that frame; -1 = not yet.")
    diorama_live_nonce = _dio_prop("live.nonce", int, "s114: the host battle nonce of the sample in hand then; -1 = none.")

    # [ff9mapkit netsync R3 s111] s111/s112/s114 publish INSIDE ``netsync.diorama`` (the F3.3 block): ``intro`` (with s112's
    # ``swirl_clamp``) and ``live``. The same reading as ``_nb_key``, one block over.
    def _dio_path(self, path: str, kind):
        """``netsync.diorama.<path>`` read as ``kind`` (bool / int / str null -> "" / dict copied / (int, float) a
        number); None when any step is absent or the type is wrong."""
        node = self.diorama
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        if kind is bool:
            return node if isinstance(node, bool) else None
        if kind is int:
            return node if isinstance(node, int) and not isinstance(node, bool) else None
        if kind is str:
            return "" if node is None else node if isinstance(node, str) else None
        if kind is dict:
            return _json_copy(node) if isinstance(node, dict) else None
        raise TypeError(f"_dio_path: no reading for {kind!r}")

    def unit_mot(self, slot: int) -> int | None:
        """[ff9mapkit netsync R3 s115] ``battle.units[].mot`` for btl ``slot``: the current clip as the unit's own motion
        index (a player's 17 = MP_ESCAPE, 4 = MP_DISABLE; -1 = none of its own). None = no such unit / before s115."""
        return self._unit_num(slot, "mot", int)

    def unit_disappear(self, slot: int) -> int | None:
        """[ff9mapkit netsync R3 s115] ``battle.units[].disappear`` (bi.disappear: 5 once the escape fade finished)."""
        return self._unit_num(slot, "disappear", int)

    def unit_z(self, slot: int) -> float | None:
        """[ff9mapkit netsync R3 s115] ``battle.units[].z`` (pos.z: falls while a runner runs; None = unreadable)."""
        return self._unit_num(slot, "z", float)

    def _unit_num(self, slot: int, key: str, kind):
        for u in self.battle.get("units", []):
            if isinstance(u, dict) and u.get("slot") == slot:
                v = u.get(key)
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    return None
                if kind is int:
                    return v if isinstance(v, int) else None
                return float(v)
        return None

    # -- what is highlighted ----------------------------------------------------------------
    @property
    def menu_label(self) -> str | None:
        """Visible text of the highlighted menu entry, e.g. ``"Status"``.

        The thing that makes menu navigation assertable rather than blind. Without it, picking an
        entry means counting keypresses -- which is exactly how the dialogue-choice off-by-one
        silently selected the wrong option.
        """
        return self.raw.get("menu", {}).get("label")

    @property
    def menu_selected(self) -> str | None:
        """Name of the focused GameObject (NGUI keyboard focus, else pointer hover)."""
        menu = self.raw.get("menu", {})
        return menu.get("selected") or menu.get("hovered")

    @property
    def menu_group(self) -> str | None:
        """NGUI's active button GROUP -- the only published tell that a menu SUB-screen changed.

        ``ui_state`` does not move for a sub-screen: confirming "Status" enters character select and
        ``ui_state`` stays ``MainMenu``. Asserting a menu was actually entered or left needs this.
        ``None`` on an engine that does not publish it.
        """
        return self.raw.get("menu", {}).get("group")

    # -- the battle ---------------------------------------------------------------------------
    #: ``btl_result``. ⚠ 0 is AMBIGUOUS: it is the value during a battle AND before any battle has
    #: ever run this session, because the engine resets it at battle START and never clears it after.
    #: It is only meaningful joined to :attr:`battle_epoch`.
    BATTLE_RESULTS = {
        0: "in-progress", 1: "victory", 2: "victory-no-pose", 3: "defeat",
        4: "escape", 5: "interruption", 6: "gameover", 7: "enemy-flee",
    }

    @property
    def battle(self) -> dict:
        return self.raw.get("battle", {})

    @property
    def in_battle(self) -> bool:
        """A REAL battle: on the battle scene and not the diorama.

        ⚠ ``IsBattleScene()`` is also true for "BattleMapDebug" and "SpecialEffectDebugRoom". Those
        run with ``isDebug``, under which the battle can never END -- so a result or reward assertion
        there is green-having-observed-nothing, and they must not read as "in a battle".
        """
        b = self.battle
        return bool(b.get("active")) and not b.get("debug")

    @property
    def battle_epoch(self) -> int:
        """``party.battle_no`` -- monotonic and save-persistent, so only DELTAS mean anything.

        It is the one unambiguous "a battle started" edge the engine offers; every other field is
        either stale between battles or ambiguous during one.
        """
        return int(self.battle.get("epoch", -1))

    @property
    def battle_result(self) -> int:
        return int(self.battle.get("result", 0))

    @property
    def battle_result_name(self) -> str:
        return self.BATTLE_RESULTS.get(self.battle_result, f"unknown({self.battle_result})")

    @property
    def battle_phase(self) -> int:
        """⚠ STALE OUTSIDE A BATTLE -- nothing resets it, so on a field it is the last fight's."""
        return int(self.battle.get("phase", -1))

    @property
    def battle_seq(self) -> int | None:
        """[ff9mapkit netsync B4] ``btl_seq`` -- the phase's sub-step (s102: the victory / defeat / escape tails key on it:
        MENU_OFF seq 4 = SEQ_MENU_OFF_VICTORY_WITH_ENEMY, VICTORY seq 2 = the WAIT). Mid-battle only, like ``phase``: None
        outside a battle AND on an engine before s102 -- read :attr:`coop_stock_menu` to tell them apart."""
        v = self.battle.get("seq")
        return v if isinstance(v, int) and not isinstance(v, bool) else None

    @property
    def battle_hud(self) -> dict | None:
        """[ff9mapkit netsync B4] ``battle.hud`` (s102, BattleHUD.NetDescribeHud) -- the live stock command panels AS
        DRAWN, copied: ``group``, ``panel`` ("target" | "ability" | "item" | "command" | "none"), ``shown``, ``slot``,
        ``menu`` / ``cmd`` / ``sub``, ``double_cast``, ``cursor_type``, ``target_cursor``, ``trance_menu``,
        ``manual_trance``, ``auto``, ``hiding``, ``main_menu``, ``can_force_next``, ``force_next``, ``caption``,
        ``commands[]`` {menu, id, label, state (2 on / 1 grey / 0 blank, as drawn), raw} and ``rows[]`` {i, id, label,
        number, state, raw} -- both [] while no menu is up. None = no HUD, outside a battle, or an engine before s102."""
        hud = self.battle.get("hud")
        if not isinstance(hud, dict):
            return None
        return _json_copy(hud)

    @property
    def battle_hud_mirrored(self) -> bool | None:
        """[ff9mapkit netsync B4] ``battle.hud.mirrored`` (s106): the slot the HUD serves draws the menu ROSTER (the host's
        content), not the stand-in's local state. None = no HUD, or an engine before s106 (:attr:`coop_menu_content`)."""
        hud = self.battle.get("hud")
        v = hud.get("mirrored") if isinstance(hud, dict) else None
        return v if isinstance(v, bool) else None

    @property
    def battle_result_ui(self) -> dict | None:
        """[ff9mapkit netsync B5] ``battle.result_ui`` (s103) -- the stock result screen read LIVE: ``state`` (ResultState
        0 Start .. 6 End, 7 Hide, 8 None), ``loading``, ``paused``; s108 adds the screen's own view (``labels`` {exp, ap,
        gil_receive, gil_current, card}, ``card_shown``, ``model`` {default_exp, default_ap, default_gil, gil_value,
        gil_current, party_gil, card}, ``rows`` [{slot, shown, name, level, exp, next, dim, level_ups, exp_value,
        exp_current, ap_value, ap_current, need_exp, need_ap}], ``items`` [{id, count, shown, name, number}] -- dropped
        whole on a fault), s109 ``replay`` (this show is the guest's write-nothing replay). Copied deep. None = not on the
        result screen, outside a battle, or an engine before s103 (:attr:`coop_end_trailer`)."""
        r = self.battle.get("result_ui")
        return _json_copy(r) if isinstance(r, dict) else None

    @property
    def battle_result_replay(self) -> bool | None:
        """[ff9mapkit netsync B5] ``battle.result_ui.replay`` (s109): the result screen up is the guest's write-nothing
        REPLAY of the host's. None = no result screen, or an engine before s109 (:attr:`coop_result_replay`)."""
        r = self.battle.get("result_ui")
        v = r.get("replay") if isinstance(r, dict) else None
        return v if isinstance(v, bool) else None

    def unit_cmd_busy(self, slot: int) -> int | None:
        """[ff9mapkit netsync B4] ``battle.units[].cmd_busy`` (s101) for the unit in btl ``slot``: bit i set while its
        cmd[i] is queued or executing (bit 0 = its ATB command -- R9's receipt). None = no such unit, or an engine before
        s101 (no key)."""
        for u in self.battle.get("units", []):
            if isinstance(u, dict) and u.get("slot") == slot:
                v = u.get("cmd_busy")
                return v if isinstance(v, int) and not isinstance(v, bool) else None
        return None

    @property
    def battle_cursor(self) -> dict:
        """The battle command/target cursor. Rides the same NGUI focus the menu does."""
        menu = self.raw.get("menu", {})
        return {"group": menu.get("group"), "button": menu.get("button"),
                "label": menu.get("button_label") or menu.get("label")}

    def units(self, *, player: bool | None = None, alive: bool | None = None) -> list[dict]:
        """Every combatant, optionally filtered. Empty outside a battle.

        ⚠ Each unit carries HP TWICE. ``hp``/``hp_max`` are the LOGICAL values the HUD shows;
        ``hp_raw``/``hp_max_raw`` are ``cur.hp``/``max.hp``, which is what the AI script reads as
        B_MEMBER (36)/(35). They differ by 10000 for an enemy flagged FLG_NON_DYING_BOSS when
        ``[Battle] CustomBattleFlagsMeaning = 1``, so an assertion about "the" HP is right about one
        of them and wrong about the other depending on the enemy.

        ⚠ ``alive`` is the Death STATUS BIT, not ``hp == 0``: a unit under a DeathChanger effect sits
        at 0 HP alive, and the HUD's own liveness test is the status.
        """
        out = list(self.battle.get("units", []))
        if player is not None:
            out = [u for u in out if bool(u.get("player")) is player]
        if alive is not None:
            out = [u for u in out if bool(u.get("alive")) is alive]
        return out

    @property
    def battle_message(self) -> str | None:
        """The on-screen battle message, e.g. "Cannot escape!". ``None`` when none is showing.

        ⚠ Transient. Messages expire on a tick counter and the channel publishes every other frame,
        so a miss means NOT OBSERVED, never "not shown".
        """
        return self.battle.get("message")

    @property
    def escaping(self) -> bool:
        """The escape ROLLED AND WON: a ``SysEscape`` command is queued (``cmd_status`` bit 0).

        ⚠ THIS IS THE ONE TO WAIT ON, not ``escape_held``. ``btl_escape_key`` is set the instant
        both bumpers are down -- before every gate -- and it is what makes the character play the
        running animation. So it reports that the input arrived and nothing whatever about the
        outcome, which is how a flee that never once rolled looked, on screen and in this file,
        exactly like one that was working.

        Between held and escaping lies a dice roll, once per real second of UNBROKEN holding:
        ``200 / avgEnemyLevel * avgPlayerLevel / 16`` percent, integer division throughout. Single
        digits against a levelled enemy. A flee still going is unlucky, not stuck.
        """
        return bool(self.battle.get("escaping", False))

    @property
    def turn_slot(self) -> int:
        """The party slot whose command menu is OPEN -- who the game is waiting on. -1 when none.

        ``BattleHUD.CurrentPlayerIndex``, which the HUD sets in ``SwitchPlayer`` for the first ready
        slot that has not yet given a command. The HUD serialises input, so there is at most one,
        and -1 is the ordinary state between turns rather than a fault.

        ⚠ ALREADY GATED ON :attr:`commands_enabled` BY THE AGENT, and it has to be. The raw field is
        reset by ``InitialBattle()``, which runs LATER than the battle scene goes live -- so through
        the opening camera of the SECOND battle in a session it still holds the PREVIOUS fight's
        slot. Acting on that injected a command into a battle mid-intro and froze it solid. The
        ungated value is :attr:`turn_slot_raw`, for telling that window apart from a real turn.
        """
        return int(self.battle.get("turn", {}).get("slot", -1))

    @property
    def turn_slot_raw(self) -> int:
        """``CurrentPlayerIndex`` UNGATED -- stale between battles. For diagnosis, never for acting."""
        return int(self.battle.get("turn", {}).get("slot_raw", -1))

    @property
    def commands_enabled(self) -> bool:
        """``FF9BMenu_IsEnable()``: the battle's command phase is live and it is asking for input.

        False through the opening camera and again from ``PHASE_MENU_OFF``, which is exactly when
        every other field in the turn block is holding the last fight's contents.
        """
        return bool(self.battle.get("turn", {}).get("enabled", False))

    @property
    def ready_slots(self) -> list[int]:
        """Slots with a full ATB that have not yet committed a command (``ready`` minus ``done``).

        Supplementary to :attr:`turn_slot`, which is the one the HUD is actually asking. A slot can
        be ready and unasked because another slot's menu is up.
        """
        turn = self.battle.get("turn", {})
        done = set(turn.get("done") or [])
        return [int(s) for s in (turn.get("ready") or []) if int(s) not in done]

    @property
    def battle_menu(self) -> dict:
        """What one party slot can do, as of the last ``menus`` request.

        ⚠ A SNAPSHOT, NOT A LIVE VIEW. ``menus`` is a request because collecting it writes the HUD's
        ability cache, and an instrument that mutates the game 30 times a second to observe it is
        not an instrument. So this answers about whenever it was last asked -- which is why it
        carries ``slot`` and ``epoch``. Use :meth:`menu_is_for` rather than trusting it.
        """
        return self.battle.get("menu", {})

    def menu_is_for(self, slot: int) -> bool:
        """Is the published menu THIS slot's, in THIS battle?"""
        menu = self.battle_menu
        return (int(menu.get("slot", -1)) == int(slot)
                and int(menu.get("epoch", -2)) == self.battle_epoch
                and self.battle_epoch >= 0)

    def command(self, name: str) -> dict | None:
        """A command from the published menu, by the name the player would read.

        ⚠ ``offered`` is not ``usable``: a command with ``offered`` false is one the HUD would not
        draw at all (an ability command with nothing learned, a monster-transform menu). It is
        returned anyway, because a scenario asking why something is missing deserves the entry
        rather than a bare None -- but sending it is a claim about a move the player never had.
        """
        return _by_name(self.battle_menu.get("commands"), name)

    def ability(self, name: str) -> dict | None:
        """A learned ability from the published menu. ``enabled`` false = learned but not castable
        right now (no MP, silenced); the HUD greys it and still lists it."""
        return _by_name(self.battle_menu.get("abilities"), name)

    def item(self, name: str) -> dict | None:
        """A battle-usable inventory item from the published menu."""
        return _by_name(self.battle_menu.get("items"), name)

    @property
    def can_escape(self) -> bool | None:
        """Whether this battle scene permits running at all (``btl_scene.Info.Runaway``).

        When false the engine still sets ``btl_escape_key`` -- so the character plays the running
        animation indefinitely -- and ``CheckEscape`` shows "Cannot escape!" without ever rolling.
        Holding the bumpers there is not a slow escape; it is no escape.
        """
        info = self.battle.get("scene_info")
        return None if info is None else bool(info.get("runaway"))

    def unit(self, name: str) -> dict | None:
        want = name.strip().lower()
        for u in self.battle.get("units", []):
            if (u.get("name") or "").strip().lower() == want:
                return u
        return None

    def flag(self, bit: int) -> bool | None:
        """A watched ``gEventGlobal`` bit. ``None`` unless the scenario called ``watch(bit)`` first."""
        return self.raw.get("flags", {}).get(str(bit))

    def __repr__(self) -> str:
        where = f"field {self.field_id}" if self.field_id > 0 else f"world {self.world_id}"
        return (f"<State frame={self.frame} seq={self.seq}/{self.ack} {self.ui_state} {where} "
                f"pos=({_f(self.player_x)},{_f(self.player_z)}) control={self.control}"
                f"{' DIALOG' if self.dialog_open else ''}>")


#: [ff9mapkit netsync B4] Every ``netsync.battle`` key path (dotted under ``netsync.battle``) -> the State accessor that
#: reads it -- the table test_harness_netsync.py holds against the agent's published keys, patch by patch.
State.NETSYNC_BATTLE_ACCESSORS = {p.fget.nb_path: name for name, p in vars(State).items()
                                  if isinstance(p, property) and hasattr(p.fget, "nb_path")}
#: [ff9mapkit netsync R3 s111] Every ``netsync.diorama`` key path below the F3.3 block (s111 ``intro``, s112
#: ``intro.swirl_clamp``, s114 ``live``) -> its State accessor -- held against the agent's keys the same way.
State.NETSYNC_DIORAMA_ACCESSORS = {p.fget.dio_path: name for name, p in vars(State).items()
                                   if isinstance(p, property) and hasattr(p.fget, "dio_path")}


def _f(v) -> str:
    return "?" if v is None else f"{v:.1f}"


class Channel:
    """The file-backed request/state channel. Owns the directory and the arming lock."""

    def __init__(self, game_path: Path, *, label: str = "run", owner_pid: int | None = None):
        self.game_path = Path(game_path)
        self.dir = self.game_path / "x64" / "ff9harness"
        self.shots = self.dir / "shots"
        self.label = label
        self.owner_pid = os.getpid() if owner_pid is None else int(owner_pid)
        self._seq = 0
        self._armed_by_us = False
        #: Called with every State this channel successfully reads -- the ONE feed for the state
        #: ring. Every wait, ack and check already polls through :meth:`state`, so recording here
        #: costs no extra read and no thread. Wrapped: a broken observer must never turn a healthy
        #: read into "no state published".
        self.observer = None

    @property
    def seq(self) -> int:
        """The sequence number of the last request this driver wrote (0 before any)."""
        return self._seq

    # -- lifecycle --------------------------------------------------------------------------
    def reset(self) -> None:
        """Clear the channel for a fresh run. Leaves ``arm`` alone -- arming is a separate decision."""
        self.shots.mkdir(parents=True, exist_ok=True)
        # story.jsonl is the s88 trace sink: the engine only ever APPENDS to it, so a run that did not
        # clear it would read the previous run's rows as its own.
        for name in ("req.txt", "state.json", "state.json.tmp", "events.jsonl", "story.jsonl"):
            _unlink(self.dir / name)
        for png in self.shots.glob("*.png"):
            _unlink(png)
        self._seq = 0

    @property
    def arm_path(self) -> Path:
        return self.dir / "arm"

    def arm_owner(self) -> dict | None:
        """Who currently holds the arm, or ``None`` if it is unheld or unreadable."""
        try:
            body = self.arm_path.read_text(encoding="utf-8-sig", errors="replace")
        except (FileNotFoundError, PermissionError, OSError):
            return None
        try:
            owner = json.loads(body)
        except ValueError:
            return {"pid": -1, "label": "?", "started": "?", "legacy": body.strip()[:80]}
        return owner if isinstance(owner, dict) else None

    def claim(self) -> None:
        """Refuse to run if another LIVE harness run has this shared install armed.

        One install, ~26 concurrent worktrees. Two drivers sharing one channel do not merely
        interleave: each ``reset()`` deletes the other's ``events.jsonl`` and every captured PNG, and
        each ``send`` overwrites the other's pending request. Failing loudly here is cheap; the
        alternative is two runs that both report on a game neither of them was driving.
        """
        owner = self.arm_owner()
        if owner is None:
            return
        pid = int(owner.get("pid", -1) or -1)
        if pid > 0 and pid != self.owner_pid and pid_alive(pid):
            raise HarnessError(
                f"another harness run already has this install armed: pid {pid}, label "
                f"{owner.get('label')!r}, started {owner.get('started')}. One FF9 install is shared "
                f"by every worktree -- wait for it, or remove {self.arm_path} if you know that run "
                f"is dead."
            )

    def arm(self, *, force_cycle: bool = True) -> bool | None:
        """Arm the agent -- as a REAL false->true transition, not merely 'a file exists'.

        ⚠ Writing over an existing ``arm`` file is a NO-OP as far as the agent is concerned. Its
        ``PollArm`` compares ``File.Exists`` against its own ``Active`` flag and returns early when
        they agree, so an already-armed agent never reaches the branch that resets ``_seq``/``_ack``,
        clears every held button and clears the error latch. A leaked arm file therefore hands the
        next run an agent that discards its requests as stale while acking instantly -- every step a
        silent no-op, and the first measurement blames the game.

        So: delete, wait until the agent has OBSERVED the disarm -- its published final document says
        ``"armed": false`` (:data:`ARM_CYCLE_TIMEOUT`) -- then create. ``force_cycle=False`` skips the
        wait when there is no game running to observe it.

        Returns whether the disarm was seen: True (the agent published it), False (not within
        ARM_CYCLE_TIMEOUT -- an agent that publishes no ``armed``, a faulted one, which publishes
        nothing while disarmed, or a game stalled that long: the caller says so, and its own check of
        the agent's sequence number still guards every request), None (no cycle: no arm file to
        delete, or ``force_cycle`` False). An agent the last document already shows DISARMED needs no
        wait: the arm below is a real transition whenever it next polls.
        """
        self.claim()
        self.dir.mkdir(parents=True, exist_ok=True)
        seen = None
        if self.arm_path.exists():
            before = self.state() if force_cycle else None
            _unlink(self.arm_path)
            if force_cycle:
                seen = True if before is not None and before.armed is False else self._await_disarm(before)
                # The disarm just observed ran a still-tracing agent's StoryTrace.Stop, whose last append
                # (residue, counts, `off`) lands AFTER reset() cleared story.jsonl -- a leaked arm's tail
                # that would open this run's trace. The arm below resets the tracer, so none of this
                # run's rows exist yet.
                _unlink(self.story_path)
        self.arm_path.write_text(json.dumps({
            "pid": self.owner_pid,
            "label": self.label,
            "started": _dt.datetime.now().isoformat(timespec="seconds"),
            "tool": "tools/harness",
        }), encoding="utf-8")
        self._armed_by_us = True
        return seen

    def _await_disarm(self, before: State | None) -> bool:
        """Read state.json until the agent's DISARM document is there -- ``"armed": false``, written after
        ``before`` (the last document read before the arm file went: a later frame, or any when there was
        none) -- at most ARM_CYCLE_TIMEOUT. The agent writes it on the frame its poll (every 30 frames)
        finds the arm file gone, having released every held button, stopped the story tracer and cleared
        its queue (HarnessAgent.PollArm); an ``armed`` true document meanwhile is the agent not having
        polled yet. True once seen, False at the timeout."""
        deadline = time.time() + ARM_CYCLE_TIMEOUT
        while True:
            st = self.state()
            if (st is not None and st.armed is False
                    and (before is None or st.frame > before.frame)):
                return True
            if time.time() >= deadline:
                return False
            time.sleep(ARM_CYCLE_POLL)

    def disarm(self) -> None:
        """Remove OUR arm. Never another live run's -- stealing it would silently un-gate their game."""
        owner = self.arm_owner()
        if owner is not None:
            pid = int(owner.get("pid", -1) or -1)
            if pid > 0 and pid != self.owner_pid and pid_alive(pid):
                return
        _unlink(self.arm_path)
        self._armed_by_us = False

    @property
    def armed(self) -> bool:
        return self.arm_path.exists()

    # -- driver -> game ---------------------------------------------------------------------
    def send(self, steps: list[str], *, accept_budget: float = 2.0, alive=None) -> int:
        """Queue ``steps`` in the game. Returns the sequence number to wait for.

        ⚠ ``req.txt`` is a single LAST-WRITE-WINS slot and the agent polls it every 2 frames when
        idle. Overwriting it before the agent has read the previous request destroys that request
        outright -- and because the survivor's ack satisfies the wait for the one that vanished, the
        loss is invisible. The documented ``hold()`` then ``wait_frames()`` pairing writes twice
        milliseconds apart and is exactly this shape. So a new request waits for the agent's receipt
        for the last one, which is what the published ``seq`` is for.
        """
        if self._seq > 0:
            self._await_accept(self._seq, accept_budget, alive)
        self._seq += 1
        body = "\n".join([f"seq {self._seq}", *steps]) + "\n"
        _write_atomic(self.dir / "req.txt", body)
        return self._seq

    def _await_accept(self, seq: int, budget: float, alive=None) -> None:
        deadline = time.time() + budget
        last: State | None = None
        while time.time() < deadline:
            if alive is not None:
                alive()
            last = self.state()
            if last is not None and last.seq >= seq:
                return
            time.sleep(0.005)
        raise HarnessError(
            f"the agent never accepted request {seq} within {budget:.1f}s (published seq="
            f"{last.seq if last else 'none'}). Overwriting req.txt now would destroy that request "
            f"silently. The agent may be disarmed, faulted or paused -- {self.classify()}."
        )

    def seed_seq(self, published_seq: int) -> None:
        """Adopt an agent that is AHEAD of us, instead of writing requests it will discard.

        Belt and braces for the arm transition: if for any reason the agent kept a high ``_seq``
        (a future engine that does not reset, a poll window we lost a race with), continuing from 0
        means every request is stale and every ack is somebody else's. Start above it instead.
        """
        if published_seq > self._seq:
            self._seq = int(published_seq)

    # -- game -> driver ---------------------------------------------------------------------
    def state(self, retries: int = 4, *, lock_budget: float = 1.0) -> State | None:
        """Latest published state, or ``None`` if the agent has not written one yet.

        Retries on a parse failure: the agent writes the file in place, so a poller can catch a
        partly written document, and a 1-in-500 flake would discredit every assertion built on this.

        ⚠ A Windows SHARING VIOLATION is not "no state" and must not be reported as one. The agent
        rewrites this file every 2nd frame -- 15 to 30 times a second at the ~31 or ~60 fps the harness
        renders at -- and a poller can easily collide with it. Treating the
        resulting PermissionError as absence made the driver declare a perfectly healthy game dead,
        and that false verdict was then repeated as "walking out of the room hangs the game" -- a bug
        attributed to the game that lived entirely in the driver. Locks get their own, much longer,
        budget. Use :meth:`classify` to say WHICH of the reasons for ``None`` applies.

        ⚠ ``None`` IS ONE READ, NOT A VERDICT. The parse retry spans ~30 ms, and the agent's in-place
        rewrite can hold the file EMPTY for longer (:data:`MID_WRITE_WITHIN`), so a healthy game
        yields the odd ``None`` -- more of them at ``stateevery 1``, which rewrites every frame.
        Loop on it, or read through ``Session.state``, which rides it out.
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
                body = path.read_text(encoding="utf-8-sig")
                try:
                    mtime = path.stat().st_mtime
                except OSError:
                    mtime = None
                st = State(json.loads(body), mtime=mtime)
                obs = self.observer
                if obs is not None:
                    try:
                        obs(st)
                    except Exception:                      # noqa: BLE001 - an artifact, not the read
                        pass
                return st
            except FileNotFoundError:
                return None
            except PermissionError:
                if time.time() >= deadline:
                    return None
                time.sleep(0.005)
            except (ValueError, OSError):
                attempt += 1
                if attempt >= retries:
                    return None
                time.sleep(0.01)

    def classify(self) -> str:
        """Name the reason ``state()`` is unhappy, instead of leaving the driver to guess.

        Every wrong verdict this harness has ever produced came from one symptom -- "no state" --
        being read as one specific cause. These are the causes, distinguished at the file level:
        MISSING (never written), LOCKED (a sharing violation we could not wait out), EMPTY (truncated
        for a rewrite: in flight, or hung inside the publish), UNPARSEABLE (a torn or corrupt
        document -- e.g. an agent exception mid-append), STALE (a real document nobody has updated),
        DISARMED (the agent says so itself), OK.
        """
        path = self.dir / "state.json"
        if not path.exists():
            return "MISSING: the agent has never published state (is the deployed DLL patched with s83?)"
        try:
            body = path.read_text(encoding="utf-8-sig")
        except PermissionError:
            return "LOCKED: state.json is held by the agent and did not free up"
        except OSError as err:
            return f"UNREADABLE: {err}"
        if not body.strip():
            # Not UNPARSEABLE's "the agent threw mid-document": the agent builds the whole document
            # before it opens the file, so a throw leaves the OLD one. Empty is the in-place rewrite.
            try:
                age = time.time() - path.stat().st_mtime
            except OSError:
                age = None
            if age is not None and age > MID_WRITE_WITHIN:
                return (f"EMPTY: state.json was truncated for a rewrite {age:.1f}s ago and its bytes "
                        f"never landed -- the game hung or died INSIDE the publish")
            return ("EMPTY: state.json is mid-rewrite -- the agent truncates it in place, then "
                    "writes, and this read landed in between. Transient unless it persists")
        try:
            doc = json.loads(body)
        except ValueError as err:
            return (f"UNPARSEABLE: state.json is not valid JSON ({err}). The agent writes it in one "
                    f"pass, so this is a torn read only if it recovers -- if it persists, the agent "
                    f"threw partway through building the document.")
        age = time.time() - path.stat().st_mtime
        if doc.get("armed") is False:
            return "DISARMED: the agent published a final document and stood down"
        if age > STALE_AFTER:
            return (f"STALE: the newest state.json is {age:.0f}s old, so the agent has stopped "
                    f"publishing (game hung, crashed, or disarmed)")
        return "OK"

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

    @property
    def story_path(self) -> Path:
        """The story-write trace's sink (s88), beside events.jsonl."""
        return self.dir / "story.jsonl"

    def story_text(self, *, lock_budget: float = 1.0) -> str | None:
        """The live story.jsonl, or ``None`` when the engine never wrote one.

        The agent APPENDS once per frame, so a read can collide with the append (a sharing violation --
        waited out on the same budget as :meth:`state`, never reported as absence) or land mid-append,
        leaving an unterminated last line; that one is the parser's to hold back (``parse_text(live=True)``).
        """
        deadline = time.time() + lock_budget
        while True:
            try:
                return self.story_path.read_text(encoding="utf-8-sig")
            except FileNotFoundError:
                return None
            except PermissionError:
                if time.time() >= deadline:
                    raise HarnessError(f"story.jsonl stayed locked for {lock_budget:.1f}s -- the agent "
                                       f"holds it mid-append") from None
                time.sleep(0.005)

    def collect(self, dest: Path) -> None:
        """Copy this run's artifacts (events, the story trace, every screenshot) into ``dest``."""
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        for name in ("events.jsonl", "story.jsonl"):
            src = self.dir / name
            if src.exists():
                shutil.copy2(src, dest / name)
        state = self.dir / "state.json"
        if state.exists():
            shutil.copy2(state, dest / "state-final.json")
        if self.shots.is_dir() and any(self.shots.glob("*.png")):
            shots = dest / "shots"
            shots.mkdir(exist_ok=True)
            for png in self.shots.glob("*.png"):
                shutil.copy2(png, shots / png.name)


def _by_name(rows, name: str) -> dict | None:
    """Find a menu row by its displayed name, tolerantly.

    Exact case-insensitive match first, then a unique prefix. The prefix arm exists because FF9's
    own labels are abbreviated and inconsistent about it ("Wht Mag", "Swd Art"), and a scenario
    that has to spell those exactly is a scenario that breaks on a localisation change. An AMBIGUOUS
    prefix returns None rather than guessing -- picking one of two plausible commands silently is
    the exact failure mode this driver exists to refuse.
    """
    want = (name or "").strip().lower()
    if not want:
        return None
    rows = list(rows or [])
    for row in rows:
        if (row.get("name") or "").strip().lower() == want:
            return row
    hits = [r for r in rows if (r.get("name") or "").strip().lower().startswith(want)]
    return hits[0] if len(hits) == 1 else None


def _write_atomic(path: Path, text: str, attempts: int = 8) -> None:
    """Replace ``path`` atomically, surviving the Windows sharing violation.

    ``os.replace`` fails with ERROR_ACCESS_DENIED whenever the agent happens to have the target open
    at that instant. This is the mirror image of the race the agent's own writer handles for
    ``state.json``, and it is not theoretical -- it killed a probe partway through the second field it
    was testing. Retry briefly, then fall back to a direct write: a partial file fails its ``seq``
    parse and is ignored, so the worst case is one wasted poll rather than a dead run.
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
