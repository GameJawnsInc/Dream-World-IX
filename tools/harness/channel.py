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
import uuid
import weakref
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

#: Arm nonce -> the Channel object in THIS process that wrote it (weakly held). With ``sibling_guard`` (instance-root
#: Sessions), an arm file naming this pid whose nonce maps to a channel still alive and still armed belongs to a live
#: sibling Session (a mistake that pointed two Sessions of one driver at one root): claim() refuses it and disarm() leaves
#: it. Any other same-pid arm -- a dead or collected Session object's leak, one written before nonces existed -- and every
#: same-pid arm on an unguarded channel is taken over exactly as before.
_LIVE_ARMS: "weakref.WeakValueDictionary" = weakref.WeakValueDictionary()

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


def _pl_prop(key: str, kind, doc: str) -> property:
    """[ff9mapkit netsync s138] One of the dress instrument's ``player`` keys (OUTSIDE netsync) as a read-only :class:`State`
    property, carrying its key for the test's table (:attr:`State.PLAYER_DRESS_ACCESSORS`). The s90 THREE CASES: None for
    an absent key (an engine before s138 -- :attr:`State.player_dress_status` "cannot") AND for null (no controlled actor:
    "unknown"); a value of the wrong type reads None too. A null string reads None here (never ""): for these keys null
    means "no actor", which is not a string."""
    def get(self):
        v = (self.raw.get("player") or {}).get(key)
        if kind is bool:
            return v if isinstance(v, bool) else None
        if kind is int:
            return v if isinstance(v, int) and not isinstance(v, bool) else None
        if kind is str:
            return v if isinstance(v, str) else None
        raise TypeError(f"_pl_prop: no reading for {kind!r}")
    get.__doc__ = doc
    get.__name__ = "player_" + key
    get.pl_key = key
    return property(get)


def _dress_prop(path: str, kind, doc: str) -> property:
    """[ff9mapkit netsync s138] One ``netsync.dress`` key (the dress instrument's block, netsync's LAST key) as a read-only
    :class:`State` property, carrying its path under ``netsync.dress`` for the test's table
    (:attr:`State.NETSYNC_DRESS_ACCESSORS`) -- the house reading (:meth:`State._dress_path`: a null string reads "")."""
    def get(self):
        return self._dress_path(path, kind)
    get.__doc__ = doc
    get.__name__ = "dress_" + path.replace(".", "_")
    get.dress_path = path
    return property(get)


def _ns_prop(path: str, kind, doc: str) -> property:
    """[ff9mapkit netsync R3 s120/s121] One key of a TOP-LEVEL ``netsync`` block the battle round added (s120's
    ``session``, s121's ``menu_refusal``) as a read-only :class:`State` property, carrying its dotted path under
    ``netsync`` for the test's table (:attr:`State.NETSYNC_TOP_ACCESSORS`)."""
    def get(self):
        return self._ns_path(path, kind)
    get.__doc__ = doc
    get.__name__ = "ns_" + path.replace(".", "_")
    get.ns_path = path
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

    # -- the controlled actor's BODY (memoria-patch s138, the dress instrument) ---------------
    # THREE CASES, the facing precedent: ``player.model`` ABSENT is an engine that cannot publish the body (s137 and
    # older), null is one that can and has no controlled actor this sample, a number is the body. The keys read the
    # controlled actor on ANY map (the same GetControlChar() as x/y/z). Harness keys only: nothing in the engine reads
    # them. `anim` is the clip ID -- ``battle.units[].anim`` is a clip NAME; `clip` is this id's NAME (AnimationDB, the
    # same derivation as ``netsync.dress.ghost.clip``). `model` is RAW: 65535 = no SetModel yet (the PosObj constructor's
    # default). `body` and `anim_geo` are the two WITNESSES no dress computes (both are read off the GameObject):
    # judge a model or a clip on them too, never on model / anim alone (R3-FIELD-MODEL-AUDIT.md 2.1 amendment 3).
    @property
    def player_dress_status(self) -> str:
        """``"cannot"`` (``player.model`` absent: an engine before s138), ``"unknown"`` (null: no controlled actor this
        sample) or ``"known"`` (:attr:`player_model` is the body's raw model id)."""
        p = self.raw.get("player") or {}
        if "model" not in p:
            return "cannot"
        v = p.get("model")
        return "known" if isinstance(v, int) and not isinstance(v, bool) else "unknown"

    player_model = _pl_prop("model", int, "s138: PosObj.model, RAW (65535 = no SetModel yet).")
    player_anim = _pl_prop("anim", int, "s138: PosObj.anim -- the clip ID (`battle.units[].anim` is a name; "
                                        ":attr:`player_clip` is this id's).")
    player_geo = _pl_prop("geo", str, "s138: FF9BattleDB.GEO[model] (TryGetValue): the GEO name SetModel builds from; None "
                                      "with no entry.")
    player_anim_geo = _pl_prop("anim_geo", str, "s138: the GEO folder (NetSyncVisitor.FolderOf) of the clip the Animation "
                                                "component ACTUALLY plays (its enabled state of the highest weight > 0) -- a "
                                                "WITNESS; None = nothing playing. Never judge it at anim 0 "
                                                "(ANH_MAIN_F0_STN_B) or on a 1-frame clip (stopped at once).")
    player_eye = _pl_prop("eye", int, "s138: PosObj.eye = -4 x SetModel's eye byte (Zidane's 93 -> -372).")
    player_uid = _pl_prop("uid", int, "s138: the controlled entry's uid.")
    player_sid = _pl_prop("sid", int, "s138: the controlled entry's sid (its entry index).")
    player_body = _pl_prop("body", str, "s138: the GEO-id stem (NetSyncVisitor.TextureStem) of the texture the actor's OWN "
                                        "mesh0 wears (HarnessAgent.BodyOf: never the first renderer depth-first -- Zidane's "
                                        "hidden battle_model0, a prop under a bone; battlewire.body_of is its twin) -- ZDN "
                                        "'98', FRJ '192', MOG '220': a WITNESS; None = no renderer / material / _MainTex / "
                                        "texture, or an UNNAMED texture (a loose-FBX or CustomModelField body): with a known "
                                        "model that is 'cannot judge', never a wrong body.")
    player_clip = _pl_prop("clip", str, "s138: AnimationDB[anim] (TryGetValue), the clip NAME; None with no entry.")
    player_clip_playing = _pl_prop("clip_playing", bool, "s138: Animation.IsPlaying(clip) on the actor -- False for no clip, "
                                                         "no Animation component or not playing.")
    player_frame_n = _pl_prop("frame_n", int, "s138: PosObj.frameN.")
    player_anim_frame = _pl_prop("anim_frame", int, "s138: PosObj.animFrame (what a script's f[7] reads).")
    player_meshflags = _pl_prop("meshflags", int, "s138: PosObj.meshflags (the HideMesh bits).")

    @property
    def object_models(self) -> list | None:
        """[ff9mapkit netsync s138] ``[(uid, sid, model), ...]`` of the listed field actors, in the list's order
        (``objects[].model``: PosObj.model RAW, 65535 = no SetModel yet) -- None unless :attr:`objects_status` is
        ``"listed"``, the ENGINE can publish the body (the instrument's other half, published by the same patch in every
        listed state: :attr:`player_dress_status` not ``"cannot"``) AND every entry carries an int ``uid`` / ``sid`` /
        ``model``. An s137 list has no ``model``: that is "cannot", never an empty answer -- and field 250's list is ALWAYS
        empty, so without the capability check an s137 [] would read as "no actor wears 98" (R3-FIELD-MODEL-AUDIT.md 2.1
        amendment 1's trap). [] is a listed field with no other actor, on an engine that can say so."""
        objs = self.objects
        if objs is None or self.player_dress_status == "cannot":
            return None
        out = []
        for o in objs:
            row = tuple((o or {}).get(k) for k in ("uid", "sid", "model"))
            if not all(isinstance(v, int) and not isinstance(v, bool) for v in row):
                return None
            out.append(row)
        return out

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

    # [ff9mapkit netsync R3 s118-s121] THE SITTING-A FIX ROUND (studies/battle-coop/R3-SITTING-A-FIXES.md): no new verb or op
    # -- each capability is its keys' PRESENCE, absent = None. s118 ``coop_handback_report``
    # (``host.handback.refused_report``), s119 ``coop_diorama_hold`` (``netsync.diorama.hold``), s120 ``coop_session_grace``
    # (``netsync.session.grace_ms``), s121 ``coop_menu_refusal`` (``netsync.menu_refusal.count``). s119-s121 are GUEST-side
    # and need a real transport (the selftest role returns before the watcher, the outage clock and the story mirror): on
    # the selftest role their blocks sit at rest -- a T2 wire replay is their bench.
    @property
    def coop_handback_report(self) -> bool | None:
        """s118: the hand-back needs a live guest -- a guest slot is guest-owned again only while its s114 report names THIS
        battle LIVE/BOOTING (``host.handback.refused_report``; no new op: ``bench boot declined|busy|stale``, and ``none``
        after the latch, keep the loopback guest's slots with the host). False = an engine that hands a slot back on any
        valid control frame."""
        return self._nb_cap("host.handback.refused_report", int)

    @property
    def coop_diorama_hold(self) -> bool | None:
        """s119: the diorama hold keyed on the PEER (``netsync.diorama.hold``). False = an engine whose guest leaves a stale
        battle lane at once while its hop is connected (the s56 predicate: behind the bridge any cut reads "over")."""
        if not isinstance(self.netsync, dict):
            return None
        return self._dio_path("hold", dict) is not None

    @property
    def coop_session_grace(self) -> bool | None:
        """s120: the session grace (``netsync.session.grace_ms``; ``hold.cap_ms`` reads it). False = an engine whose guest
        ends a mirrored session 3 s after its peer goes silent and caps a held diorama at 8 s."""
        if not isinstance(self.netsync, dict):
            return None
        return self._ns_path("session.grace_ms", int) is not None

    @property
    def coop_menu_refusal(self) -> bool | None:
        """s121: the audible menu refusal (``netsync.menu_refusal.count``). False = an engine whose mirroring guest drops
        the Menu key silently."""
        if not isinstance(self.netsync, dict):
            return None
        return self._ns_path("menu_refusal.count", int) is not None

    # ---- host: s118 the hand-back needs a live guest (inside s110's fixed ``handback`` block)
    coop_handback_refused_report = _nb_prop("host.handback.refused_report", int,
                                            "s118: refusal EPISODES -- a live control lane whose report (declined, busy, "
                                            "none after a diorama report on this battle, another battle) kept the slots "
                                            "here when the host's command phase was open with guest slots set -- "
                                            "monotonic, read DELTAS.")
    coop_handback_refused_now = _nb_prop("host.handback.refused_now", bool, "s118: the host keeps the guest's slots RIGHT "
                                                                            "NOW: the last valid frame's report refused "
                                                                            "and the lane is fresh (MenuStaleMs).")
    coop_handback_diorama_seen = _nb_prop("host.handback.diorama_seen", bool, "s118: the per-own-battle latch -- the guest "
                                                                              "reported a diorama state other than NONE "
                                                                              "about THIS battle (false = its NONE still "
                                                                              "owns: the panel-only guest).")

    # [ff9mapkit netsync s131] THE EXPIRED SEQ (studies/battle-coop/R3-SITTING-A-FIXES.md, "The hold-onset variance: the Pump
    # null RE-ADOPT"): no new verb or op -- the capability is the key's PRESENCE, absent = None. GUEST-side and transport-
    # only: the run-out needs a real peer lane (the selftest role's loopback writes the view directly and never runs out),
    # so on the stand-in and the selftest role the block sits at its sentinels -- a wire replay with a blackhole is its
    # bench. The counters are monotonic per PROCESS: read DELTAS across a cut.
    @property
    def coop_peer_adopt(self) -> bool | None:
        """s131: the peer adopt step (``netsync.battle.peer.expired``) -- once the host's battle view runs out of freshness,
        the transport's repeats of that (nonce, seq) are never adopted again. False = an engine whose guest RE-ADOPTS the
        host's frozen last frame after the run-out (s121 and older: a phantom second 2000 ms of a live lane whenever the
        cut's tail outlasts one Update, ~79% of cuts)."""
        return self._nb_cap("peer.expired", dict)

    # ---- peer: s131 the expired seq (the last key of ``peer``)
    coop_peer_expired = _nb_prop("peer.expired", dict, "s131: the whole ``expired`` block, copied.")
    coop_peer_expired_seq = _nb_prop("peer.expired.seq", int, "s131: the expired memo's seq -- the host frame whose "
                                                              "freshness ran out, refused while the transport repeats it; "
                                                              "-1 = none (no run-out since the last real adopt or a reset).")
    coop_peer_expired_nonce = _nb_prop("peer.expired.nonce", int, "s131: ...its host battle nonce; -1 = none.")
    coop_peer_expired_count = _nb_prop("peer.expired.count", int, "s131: freshness RUN-OUTS (Pump's stale branch nulled a "
                                                                  "view) -- monotonic, read DELTAS: +1 per cut or battle "
                                                                  "end, whatever its tail.")
    coop_peer_expired_refused = _nb_prop("peer.expired.refused", int, "s131: refused re-adopt EPISODES (run-outs whose "
                                                                      "frame the transport served again: the pre-s131 "
                                                                      "phantom 2000 ms) -- monotonic, read DELTAS: +1 for "
                                                                      "a tail >= ~one Update, +0 for a tail-0 cut.")
    coop_peer_expired_frames = _nb_prop("peer.expired.frames", int, "s131: refused repeat FRAMES -- monotonic, read DELTAS.")
    coop_peer_expired_ms = _nb_prop("peer.expired.ms", int, "s131: the last episode, its run-out to its last refused "
                                                            "repeat (the cut's tail less up to two Updates); -1 = none "
                                                            "yet.")

    # [ff9mapkit netsync s133] THE HOST ACTION-START LANE (studies/battle-coop/R3-DESIGN.md 3.3.2 as amended by
    # R3-ACTION-REPLAY-AUDIT.md 2.1): `netsync.battle.act.host` -- every action an own battle runs ships a START before its
    # first impact and an END after its last, each impact carries its id, type-1 header flags bit 5 says so. The capability
    # is the block's PRESENCE (absent = None per key, False for :attr:`coop_act_host`): an engine before s133 answers
    # `netsync actbench` "unknown sub-verb". Published in EVERY role (audit 3.6); `loop` and `tape` are fed only by the
    # selftest loopback and read zero elsewhere. Counters are per OWN BATTLE (reset at its rising edge, kept after it until
    # the next one starts) unless marked monotonic; the tape is per process (`actbench tape`).
    @property
    def coop_act_host(self) -> bool | None:
        """s133: the host action-start lane (``netsync.battle.act.host``; the verb ``actbench``). False = an engine whose
        host ships no action START/END records and no impact ids (s132 and older)."""
        return self._nb_cap("act.host", dict)

    coop_act_host_block = _nb_prop("act.host", dict, "s133: the whole ``act.host`` block, copied.")
    coop_act_host_on = _nb_prop("act.host.on", bool, "s133: this host ships STARTs/ENDs and impact ids NOW ([Netsync] "
                                                     "Enabled and the calibration lever not pulled).")
    coop_act_host_lever_off = _nb_prop("act.host.lever_off", bool, "s133: the selftest calibration lever `actbench "
                                                                   "hoststarts off` (the pre-s133 host).")
    coop_act_host_nonce = _nb_prop("act.host.nonce", int, "s133: the own battle these counts belong to; -1 = none yet.")
    coop_act_host_starts = _nb_prop("act.host.starts", int, "s133: START records queued this own battle.")
    coop_act_host_ends = _nb_prop("act.host.ends", int, "s133: END records queued (a displaced id's END included).")
    coop_act_host_ext_impacts = _nb_prop("act.host.ext_impacts", int, "s133: impacts that carried the id extension.")
    coop_act_host_noid_impacts = _nb_prop("act.host.noid_impacts", int, "s133: ...of them, id 0 (a nested CMD_DATA, a "
                                                                        "declined START, an ENDed lifecycle).")
    coop_act_host_scripted = _nb_prop("act.host.scripted", int, "s133: StartBtlSeq STARTs (never ENDed).")
    coop_act_host_open = _nb_prop("act.host.open", int, "s133: END-eligible ids open now.")
    coop_act_host_dropped = _nb_prop("act.host.dropped", int, "s133: type-6 frames the 64-frame action buffer dropped "
                                                              "(oldest first, every kind) this own battle -- the PER-TICK "
                                                              "burst budget only (Pump flushes it every in-battle tick).")
    coop_act_host_wire_dropped = _nb_prop("act.host.wire_dropped", int, "s133: type-6 frames the TRANSPORT's 64-frame "
                                                                        "out-queue dropped this own battle (a stalled or "
                                                                        "backlogged link; always 0 under the selftest "
                                                                        "loopback: no transport).")
    coop_act_host_unresolved = _nb_prop("act.host.unresolved", int, "s133: commands with no wire actor (no START, no "
                                                                    "id, no END).")
    coop_act_host_scripted_takeover = _nb_prop("act.host.scripted_takeover", int,
                                               "s133: StartBtlSeq over an open cmd[0] (its END went first).")
    coop_act_host_scripted_reentry = _nb_prop("act.host.scripted_reentry", int,
                                              "s133: a CommandEngine START on a CMD_DATA whose scripted sequence still ran.")
    coop_act_host_restarted = _nb_prop("act.host.restarted", int, "s133: a CommandEngine START over its own open id.")
    coop_act_host_no_end = _nb_prop("act.host.no_end", int, "s133: END-eligible ids open at a NORMAL close (a defect).")
    coop_act_host_cut = _nb_prop("act.host.cut", int, "s133: ...open at a reset mid-battle or a mid-action teardown.")
    coop_act_host_edge_declined = _nb_prop("act.host.edge_declined", int,
                                           "s133: STARTs declined before the own battle's rising edge -- monotonic per "
                                           "PROCESS, read DELTAS.")
    coop_act_host_kinds = _nb_prop("act.host.kinds", dict, "s133: STARTs by vfx kind, copied.")
    coop_act_host_kinds_none = _nb_prop("act.host.kinds.none", int, "s133: STARTs of kind 0 (no vfx).")
    coop_act_host_kinds_seq = _nb_prop("act.host.kinds.seq", int, "s133: ...kind 1 (the ability's .seq).")
    coop_act_host_kinds_enemy = _nb_prop("act.host.kinds.enemy", int, "s133: ...kind 2 (an enemy sequence, num = sub).")
    coop_act_host_kinds_special = _nb_prop("act.host.kinds.special", int, "s133: ...kind 3 (a SpecialEffect).")
    coop_act_host_kinds_common = _nb_prop("act.host.kinds.common", int, "s133: ...kind 4 (Defend / Change).")
    coop_act_host_kinds_unknown = _nb_prop("act.host.kinds.unknown", int, "s133: ...0xFF (the describe threw).")
    coop_act_host_vfx = _nb_prop("act.host.vfx", dict, "s133: the describe check (audit D2), copied.")
    coop_act_host_vfx_checked = _nb_prop("act.host.vfx.checked", int, "s133: CommandEngine STARTs checked against what "
                                                                      "SelectCommandVfx ran (SFXRework).")
    coop_act_host_vfx_drift = _nb_prop("act.host.vfx.drift", int, "s133: ...that disagreed (DescribeCommandVfx no "
                                                                  "longer mirrors it, or a CSV .seq's first use).")
    coop_act_host_vfx_unchecked = _nb_prop("act.host.vfx.unchecked", int, "s133: ...on the old engine (no "
                                                                          "runningActions to check).")
    coop_act_host_vfx_why = _nb_prop("act.host.vfx.why", str, "s133: the last drift, named; \"\" = none.")
    coop_act_host_last = _nb_prop("act.host.last", dict, "s133: the last START as shipped, decoded ({id, actor, flags, "
                                                         "cmd, sub, tar, cursor, info, magic, kind, num, patched, speed}); "
                                                         "None = none this battle.")
    coop_act_host_loop = _nb_prop("act.host.loop", dict, "s133: the selftest loopback's audit, copied.")
    coop_act_host_loop_starts = _nb_prop("act.host.loop.starts", int, "s133: STARTs the loopback received.")
    coop_act_host_loop_ends = _nb_prop("act.host.loop.ends", int, "s133: ENDs the loopback received.")
    coop_act_host_loop_impacts = _nb_prop("act.host.loop.impacts", int, "s133: impacts (stat ticks never count).")
    coop_act_host_loop_impacts_ext = _nb_prop("act.host.loop.impacts_ext", int, "s133: ...with the id extension.")
    coop_act_host_loop_stat = _nb_prop("act.host.loop.stat", int, "s133: stat ticks (flags bit 7, 46 bytes).")
    coop_act_host_loop_ext_bad = _nb_prop("act.host.loop.ext_bad", int, "s133: bad / unknown-fmt extensions, and "
                                                                        "START/END-flagged frames with none.")
    coop_act_host_loop_paired = _nb_prop("act.host.loop.paired", int, "s133: ENDs that closed an open END-eligible START.")
    coop_act_host_loop_orphans = _nb_prop("act.host.loop.orphans", int, "s133: an END with no open START, an impact "
                                                                        "naming no open id, a duplicate START id.")
    coop_act_host_loop_caster_mismatch = _nb_prop("act.host.loop.caster_mismatch", int,
                                                  "s133: an impact whose caster is not its START's actor.")
    coop_act_host_loop_no_end = _nb_prop("act.host.loop.no_end", int, "s133: STARTs the loopback saw open at a normal "
                                                                      "close.")
    coop_act_host_loop_cut = _nb_prop("act.host.loop.cut", int, "s133: ...open at a reset or a mid-action teardown.")
    coop_act_host_tape = _nb_prop("act.host.tape", dict, "s133: the `actbench tape` block, copied.")
    coop_act_host_tape_state = _nb_prop("act.host.tape.state", str, "s133: \"off\" | \"rec\" | \"stopped\" (\"\" = the "
                                                                    "catch line's null).")
    coop_act_host_tape_frames = _nb_prop("act.host.tape.frames", int, "s133: frames on the tape (at most 1024).")
    coop_act_host_tape_starts = _nb_prop("act.host.tape.starts", int, "s133: ...of them STARTs.")
    coop_act_host_tape_ms = _nb_prop("act.host.tape.ms", int, "s133: the last frame's offset from `tape rec`; -1 = none.")
    coop_act_host_tape_overflow = _nb_prop("act.host.tape.overflow", int, "s133: frames past the 1024 cap (counted, not "
                                                                          "recorded).")
    coop_act_host_tape_page = _nb_prop("act.host.tape.page", dict, "s133: the last `actbench tape dump` ({from, count, "
                                                                   "total, frames: [{i, ms, hex}]} -- compact upper-case "
                                                                   "hex); None = none.")

    # [ff9mapkit netsync s134] THE GUEST ACTION REPLAY (studies/battle-coop/R3-DESIGN.md 3.3.3 as amended by
    # R3-ACTION-REPLAY-AUDIT.md 2.2 and section 3): `netsync.battle.act.guest` -- an s133 host's action STARTs replayed on this
    # guest's battle diorama as the real clips, presentation only (the hit short-circuit; THE TRIPWIRE `calc_while_booted`).
    # The capability is the block's PRESENCE (absent = None per key, False for :attr:`coop_act_guest`): an s133 engine
    # answers the guest `actbench` ops "unknown op" / its usage. Published in EVERY role (audit 3.6). Counters are per
    # diorama BOOT (reset by each boot, kept after its teardown until the next) unless marked; `levers` are harness-scoped;
    # `rx_dropped` is monotonic per transport (read DELTAS). starts_rx == started + declined + queued + waiting +
    # discarded.pending; at rest ended + aborted + discarded.running == started (battlewire.act_guest_invariant /
    # act_guest_ends_balance).
    @property
    def coop_act_guest(self) -> bool | None:
        """s134: the guest action replay (``netsync.battle.act.guest``; `actbench feed|feedat|tape play|replay|rework|
        shortcircuit|knob|clear|teardown`). False = an engine whose guest replays no action (s133 and older)."""
        return self._nb_cap("act.guest", dict)

    coop_act_guest_block = _nb_prop("act.guest", dict, "s134: the whole ``act.guest`` block, copied.")
    coop_act_guest_on = _nb_prop("act.guest.on", bool, "s134: this guest would replay a START now ([Netsync] ActionReplay, "
                                                       "no `replay off` lever, SFXRework).")
    coop_act_guest_why = _nb_prop("act.guest.why", str, "s134: why not -- \"knob\" | \"lever\" | \"rework\" (\"\" = on).")
    coop_act_guest_rework = _nb_prop("act.guest.rework", bool, "s134: SFXRework as the replay sees it (after the "
                                                               "`rework off` lever).")
    coop_act_guest_knob = _nb_prop("act.guest.knob", int, "s134: the effective [Netsync] ActionReplay (1 / 0; a `knob` "
                                                          "lever wins in the selftest role).")
    coop_act_guest_host_caps = _nb_prop("act.guest.host_caps", int, "s134: the booted host's last header flags byte; -1 = "
                                                                    "none this boot.")
    coop_act_guest_bit5 = _nb_prop("act.guest.bit5", bool, "s134: the per-boot latch -- the booted host ships action "
                                                           "STARTs (CapActionStarts); never cleared by a null view.")
    coop_act_guest_levers = _nb_prop("act.guest.levers", dict, "s134: the selftest levers, copied.")
    coop_act_guest_lever_replay_off = _nb_prop("act.guest.levers.replay_off", bool, "s134: `actbench replay off` (the "
                                                                                    "pre-s134 guest).")
    coop_act_guest_lever_rework_off = _nb_prop("act.guest.levers.rework_off", bool, "s134: `actbench rework off`.")
    coop_act_guest_lever_shortcircuit_off = _nb_prop("act.guest.levers.shortcircuit_off", bool,
                                                     "s134: `actbench shortcircuit off`, armed for the NEXT replay "
                                                     "(one-shot).")
    coop_act_guest_lever_knob = _nb_prop("act.guest.levers.knob", int, "s134: `actbench knob 0|1` (-1 = the ini's).")
    coop_act_guest_inbox = _nb_prop("act.guest.inbox", int, "s134: bench frames waiting in the inbox.")
    coop_act_guest_starts_rx = _nb_prop("act.guest.starts_rx", int, "s134: START records received this boot.")
    coop_act_guest_ends_rx = _nb_prop("act.guest.ends_rx", int, "s134: END records received this boot.")
    coop_act_guest_started = _nb_prop("act.guest.started", int, "s134: replays launched this boot.")
    coop_act_guest_queued = _nb_prop("act.guest.queued", int, "s134: STARTs registered and undecided now.")
    coop_act_guest_waiting = _nb_prop("act.guest.waiting", int, "s134: STARTs parked in an actor's pending slot now.")
    coop_act_guest_running = _nb_prop("act.guest.running", int, "s134: replays in the sequencer now.")
    coop_act_guest_declined = _nb_prop("act.guest.declined", int, "s134: STARTs that never launched (every reason, noop "
                                                                  "and superseded included).")
    coop_act_guest_declined_why = _nb_prop("act.guest.declined_why", str, "s134: the last decline's reason (\"\" = none).")
    coop_act_guest_stale = _nb_prop("act.guest.stale", int, "s134: ...of them `stale` (the END came first).")
    coop_act_guest_backlog = _nb_prop("act.guest.backlog", int, "s134: ...`backlog`.")
    coop_act_guest_superseded = _nb_prop("act.guest.superseded", int, "s134: ...`superseded` (a newer START of the actor).")
    coop_act_guest_noop = _nb_prop("act.guest.noop", int, "s134: ...`noop` (kind none: no clip).")
    coop_act_guest_dropped = _nb_prop("act.guest.dropped", int, "s134: ...parked STARTs an abort-all declined (r8 / w3 / "
                                                                "leave / clear).")
    coop_act_guest_aborted = _nb_prop("act.guest.aborted", int, "s134: hard releases this boot.")
    coop_act_guest_abort_why = _nb_prop("act.guest.abort_why", str, "s134: the LAST abort's reason (\"\" = none) -- judge "
                                                                    "every abort by :attr:`coop_act_guest_aborts`.")
    coop_act_guest_aborts = _nb_prop("act.guest.aborts", dict, "s134: every abort this boot by its reason, copied ({pending, "
                                                               "host_end, cap, actor, fault, leave, w3, r8, clear}).")
    coop_act_guest_aborts_pending = _nb_prop("act.guest.aborts.pending", int, "s134: aborts `pending` (a parked START's "
                                                                              "1500 ms).")
    coop_act_guest_aborts_host_end = _nb_prop("act.guest.aborts.host_end", int, "s134: aborts `host-end` (the host's END "
                                                                                "+ 6 s).")
    coop_act_guest_aborts_cap = _nb_prop("act.guest.aborts.cap", int, "s134: aborts `cap` (the 90 s wall cap).")
    coop_act_guest_aborts_actor = _nb_prop("act.guest.aborts.actor", int, "s134: aborts `actor` (the actor gone).")
    coop_act_guest_aborts_fault = _nb_prop("act.guest.aborts.fault", int, "s134: aborts `fault` (a sequencer throw).")
    coop_act_guest_aborts_leave = _nb_prop("act.guest.aborts.leave", int, "s134: aborts `leave` (a Leave of the diorama).")
    coop_act_guest_aborts_w3 = _nb_prop("act.guest.aborts.w3", int, "s134: aborts `w3` (an injected end + 4 s, or the "
                                                                    "run-away hold's bound / break).")
    coop_act_guest_aborts_r8 = _nb_prop("act.guest.aborts.r8", int, "s134: aborts `r8` (the end's fade at black).")
    coop_act_guest_aborts_clear = _nb_prop("act.guest.aborts.clear", int, "s134: aborts `clear` (`actbench clear`).")
    coop_act_guest_discarded = _nb_prop("act.guest.discarded", dict, "s134: what a teardown's ActDiscardAll dropped, copied "
                                                                     "({pending, running}) -- apart from started / declined "
                                                                     "/ aborted.")
    coop_act_guest_discarded_pending = _nb_prop("act.guest.discarded.pending", int, "s134: parked STARTs a teardown "
                                                                                    "dropped.")
    coop_act_guest_discarded_running = _nb_prop("act.guest.discarded.running", int, "s134: running replays a teardown "
                                                                                    "dropped.")
    coop_act_guest_ended = _nb_prop("act.guest.ended", int, "s134: natural ends this boot.")
    coop_act_guest_faulted = _nb_prop("act.guest.faulted", int, "s134: sequencer throws (each an abort `fault`).")
    coop_act_guest_hits = _nb_prop("act.guest.hits", int, "s134: short-circuited hits (ActOnHit).")
    coop_act_guest_credits = _nb_prop("act.guest.credits", int, "s134: ...on a target no impact of that action had reached "
                                                                "yet.")
    coop_act_guest_paired = _nb_prop("act.guest.paired", int, "s134: impacts that named a record.")
    coop_act_guest_swing_skipped = _nb_prop("act.guest.swing_skipped", int, "s134: legacy player swings a replay replaced.")
    coop_act_guest_calc_while_booted = _nb_prop("act.guest.calc_while_booted", int,
                                                "s134: THE TRIPWIRE -- battle calculations while a diorama is booted (0 in "
                                                "every healthy boot).")
    coop_act_guest_var_refused = _nb_prop("act.guest.var_refused", int, "s134: a replay's btl_seq / cmd_status writes "
                                                                        "filtered.")
    coop_act_guest_old_host = _nb_prop("act.guest.old_host", bool, "s134: an impact without the action id arrived (the host "
                                                                   "predates action replay).")
    coop_act_guest_grace = _nb_prop("act.guest.grace", dict, "s134: the death-attack grace, copied.")
    coop_act_guest_grace_armed = _nb_prop("act.guest.grace.armed", int, "s134: graces armed this boot.")
    coop_act_guest_grace_mask = _nb_prop("act.guest.grace.mask", int, "s134: the btl_ids inside one now.")
    coop_act_guest_hold_through = _nb_prop("act.guest.hold_through", int, "s134: diorama holds a replay ran through.")
    coop_act_guest_end_held = _nb_prop("act.guest.end_held", int, "s134: end injections held for an acting replay.")
    coop_act_guest_rx_dropped = _nb_prop("act.guest.rx_dropped", int, "s134: the transport's inbound type-6 drops -- "
                                                                      "monotonic per transport, read DELTAS; -1 = none "
                                                                      "read.")
    coop_act_guest_battle_ms = _nb_prop("act.guest.battle_ms", int, "s134: the battle clock (ms since the boot, paused spans "
                                                                    "skipped); -1 = not booted.")
    coop_act_guest_paused_ms = _nb_prop("act.guest.paused_ms", int, "s134: the paused spans the clock skipped.")
    coop_act_guest_window = _nb_prop("act.guest.window", dict, "s134: the busy window, copied.")
    coop_act_guest_window_open = _nb_prop("act.guest.window.open", bool, "s134: a replay's busy window is open.")
    coop_act_guest_window_restores = _nb_prop("act.guest.window.restores", int, "s134: full restores (after an abort).")
    coop_act_guest_window_limited = _nb_prop("act.guest.window.limited", int, "s134: shared-lanes-only restores (after an "
                                                                              "end injection).")
    coop_act_guest_last = _nb_prop("act.guest.last", dict, "s134: the last START received ({id, actor, cmd, sub, kind, num, "
                                                           "speed, state, why, arrive_ms, launch_ms, first_hit_ms, end_ms, "
                                                           "hits}); None = none this boot.")

    # [ff9mapkit netsync s135] THE REPLAY HIT HOLD (studies/battle-coop/R3-DESIGN.md 3.3.4 as amended by
    # R3-ACTION-REPLAY-AUDIT.md 2.3): `netsync.battle.act.guest.hold`, the LAST key of `act.guest` -- numbers, the flinch and
    # deaths on the guest wait for the action replay's own hit (the HP and MP bars still follow the host). The capability is
    # the block's PRESENCE (absent = None per key, False for :attr:`coop_act_hold`): an s134 engine answers the `actbench
    # hold|lifeskip|unit` ops "unknown op" / its usage. Published in EVERY role; per diorama BOOT (reset by each boot, kept
    # after its teardown until the next) except the two levers. At rest (nothing held, no teardown discard) held == the sum
    # of rel_* and queued == rel_queued (battlewire.act_hold_at_rest). "hold" names three things: always the full path.
    @property
    def coop_act_hold(self) -> bool | None:
        """s135: the replay hit hold (``netsync.battle.act.guest.hold``; `actbench hold|lifeskip on|off`, `actbench unit
        <slot> <state>`). False = an engine whose guest shows numbers, the flinch and deaths when the host's impact
        ARRIVES (s134 and older)."""
        return self._nb_cap("act.guest.hold", dict)

    coop_act_hold_block = _nb_prop("act.guest.hold", dict, "s135: the whole ``act.guest.hold`` block, copied.")
    coop_act_hold_on = _nb_prop("act.guest.hold.on", bool, "s135: the hold is in force (false = `actbench hold off`: the "
                                                           "pre-s135 arrival path).")
    coop_act_hold_lifeskip = _nb_prop("act.guest.hold.lifeskip", bool, "s135: the reconciler's life-mask skip is in force "
                                                                       "(false = `actbench lifeskip off`).")
    coop_act_hold_held_now = _nb_prop("act.guest.hold.held_now", int, "s135: impacts held for their replay's hit now.")
    coop_act_hold_held = _nb_prop("act.guest.hold.held", int, "s135: impacts held this boot (LATE releases included).")
    coop_act_hold_queued_now = _nb_prop("act.guest.hold.queued_now", int, "s135: frames queued behind an older held life "
                                                                          "change now.")
    coop_act_hold_queued = _nb_prop("act.guest.hold.queued", int, "s135: frames queued this boot (audit amendment 5).")
    coop_act_hold_rel_hit = _nb_prop("act.guest.hold.rel_hit", int, "s135: held impacts released at their replay's hit.")
    coop_act_hold_rel_late = _nb_prop("act.guest.hold.rel_late", int, "s135: ...at once, the replay's hit having come first "
                                                                      "(a credit).")
    coop_act_hold_rel_end = _nb_prop("act.guest.hold.rel_end", int, "s135: ...at the replay's natural end (it never hit "
                                                                    "that target).")
    coop_act_hold_rel_hostdone = _nb_prop("act.guest.hold.rel_hostdone", int, "s135: ...at the host's END + 1500 ms.")
    coop_act_hold_rel_timeout = _nb_prop("act.guest.hold.rel_timeout", int, "s135: ...2500 ms (battle time) after arrival.")
    coop_act_hold_rel_abort = _nb_prop("act.guest.hold.rel_abort", int, "s135: ...when the replay aborted (or an abort-all "
                                                                        "dropped its pending START).")
    coop_act_hold_rel_replaced = _nb_prop("act.guest.hold.rel_replaced", int, "s135: ...when a newer START replaced its "
                                                                              "pending one (amendment 9).")
    coop_act_hold_rel_declined = _nb_prop("act.guest.hold.rel_declined", int, "s135: ...when its pending START declined "
                                                                              "otherwise (stale, noop, actor, ...).")
    coop_act_hold_rel_end_inject = _nb_prop("act.guest.hold.rel_end_inject", int, "s135: ...at the end injection "
                                                                                  "(amendment 2: before AllPlayersDown).")
    coop_act_hold_rel_queued = _nb_prop("act.guest.hold.rel_queued", int, "s135: queued frames released (any reason).")
    coop_act_hold_superseded = _nb_prop("act.guest.hold.superseded", int, "s135: releases whose life change a newer frame "
                                                                          "had overtaken (the figure and the flinch only).")
    coop_act_hold_discarded = _nb_prop("act.guest.hold.discarded", int, "s135: held + queued frames a teardown dropped "
                                                                        "(nothing applied).")
    coop_act_hold_life_mask = _nb_prop("act.guest.hold.life_mask", int, "s135: the wire-slot bits whose kill or revive "
                                                                        "waits now (the reconciler skips them).")
    coop_act_hold_mask_skips = _nb_prop("act.guest.hold.mask_skips", int, "s135: reconciler records the life mask "
                                                                          "skipped.")
    coop_act_hold_lag = _nb_prop("act.guest.hold.lag", dict, "s135: the paired releases' lag, copied ({n, min, p50, max}: "
                                                             "battle ms of hit minus arrival, negative = a credit).")
    coop_act_hold_lag_n = _nb_prop("act.guest.hold.lag.n", int, "s135: paired releases (hit and late) this boot.")
    coop_act_hold_lag_min = _nb_prop("act.guest.hold.lag.min", int, "s135: the smallest lag (ms; -1 with n 0).")
    coop_act_hold_lag_p50 = _nb_prop("act.guest.hold.lag.p50", int, "s135: the lower median lag (ms; -1 with n 0).")
    coop_act_hold_lag_max = _nb_prop("act.guest.hold.lag.max", int, "s135: the largest lag (ms; -1 with n 0) -- the real "
                                                                    "link's (amendment 10).")
    coop_act_hold_figs = _nb_prop("act.guest.hold.figs", list, "s135: the last 16 figures the action lane DISPLAYED, oldest "
                                                               "first ([{slot, value, via, arrival_ms, release_ms}]; via "
                                                               "\"arrival\" | a release reason | \"queued\").")

    # [ff9mapkit netsync s136] FALLBACK A, ONE STOCK CLIP PER UNCOVERED ACTION (studies/battle-coop/R3-DESIGN.md 3.3.5 as
    # amended by R3-ACTION-REPLAY-AUDIT.md 2.4): `netsync.battle.act.guest.fallback`, the LAST key of `act.guest` -- an impact
    # no action replay covers plays ONE stock clip chosen by its action (a player's MP_ITEM1 / MP_MAGIC / MP_ATTACK / none,
    # an enemy's scene-sequence clip), at most once per action. The capability is the block's PRESENCE (absent = None per
    # key, False for :attr:`coop_act_fallback`): an s135 engine answers `actbench fallback` "unknown op". Published in
    # EVERY role; per diorama BOOT (reset by each boot, kept after its teardown until the next) except the lever. Every
    # impact that reaches the motion step with a resolved caster counts exactly ONE of clips | deduped | covered | none |
    # guarded | backlog | collapsed (battlewire.act_fallback_decided).
    @property
    def coop_act_fallback(self) -> bool | None:
        """s136: fallback A (``netsync.battle.act.guest.fallback``; `actbench fallback on|off`). False = an engine whose
        guest swings only a player caster's MP_ATTACK for an impact no replay covers (s135 and older)."""
        return self._nb_cap("act.guest.fallback", dict)

    coop_act_fallback_block = _nb_prop("act.guest.fallback", dict, "s136: the whole ``act.guest.fallback`` block, copied.")
    coop_act_fallback_on = _nb_prop("act.guest.fallback.on", bool, "s136: fallback A is in force (false = `actbench fallback "
                                                                   "off`: the pre-s136 s110 player-only swing).")
    coop_act_fallback_clips = _nb_prop("act.guest.fallback.clips", int, "s136: clips WRITTEN this boot (one per actor per "
                                                                        "frame).")
    coop_act_fallback_deduped = _nb_prop("act.guest.fallback.deduped", int, "s136: impacts of an action that already had its "
                                                                            "decision (by id, or by caster within 500 ms).")
    coop_act_fallback_covered = _nb_prop("act.guest.fallback.covered", int, "s136: impacts a replay covers (no clip).")
    coop_act_fallback_none = _nb_prop("act.guest.fallback.none", int, "s136: actions that chose no clip (Defend / Change, "
                                                                      "an Idle-only or unparsable enemy sequence, ...).")
    coop_act_fallback_guarded = _nb_prop("act.guest.fallback.guarded", int, "s136: impacts the call-site guards refused "
                                                                            "(lethal, revive, hidden, a self-hit, acting, "
                                                                            "the end or a Leave -- nothing spent).")
    coop_act_fallback_backlog = _nb_prop("act.guest.fallback.backlog", int, "s136: impacts drained in a backlog Update (no "
                                                                            "clip; the key spent).")
    coop_act_fallback_collapsed = _nb_prop("act.guest.fallback.collapsed", int, "s136: clips overwritten on one actor in one "
                                                                                "frame (not in clips).")
    coop_act_fallback_parse_failed = _nb_prop("act.guest.fallback.parse_failed", int, "s136: enemy sequences that could not "
                                                                                      "be parsed (played as nothing).")
    coop_act_fallback_last = _nb_prop("act.guest.fallback.last", dict, "s136: the last clip written ({actor, clip, cmd, sub, "
                                                                       "keyed_by, kind, id, via, ms}); None = none this "
                                                                       "boot.")

    # [ff9mapkit netsync s137] THE TRANCE BURST TIMING (studies/battle-coop/R3-DESIGN.md 3.3.6 as amended by
    # R3-ACTION-REPLAY-AUDIT.md 2.5): `netsync.battle.act.guest.trance`, the LAST key of `act.guest` -- a trance MODEL change
    # the reconciler's probe asks for waits for the SysTrans replay's own hit, else a 400 ms grace of battle time after
    # nothing names the unit, capped at 2500 ms from the sample -- the unit's own burst in flight at most 8500 ms (the trance
    # status, the glow and the gauge follow the host at once, as before). The capability is the block's PRESENCE (absent =
    # None per key, False for :attr:`coop_act_trance`): an
    # s136 engine answers `actbench trancegrace` "unknown op". Published in EVERY role; per diorama BOOT (reset by each boot,
    # kept after its teardown until the next) except the lever. Every deferral ends exactly once
    # (battlewire.act_trance_accounted): deferred == swaps_by_* + moot + dropped + the bits of `pending`.
    @property
    def coop_act_trance(self) -> bool | None:
        """s137: the trance burst timing (``netsync.battle.act.guest.trance``; `actbench trancegrace on|off`). False = an
        engine whose guest swaps the trance model when the host's sample carries the bit (s136 and older)."""
        return self._nb_cap("act.guest.trance", dict)

    coop_act_trance_block = _nb_prop("act.guest.trance", dict, "s137: the whole ``act.guest.trance`` block, copied.")
    coop_act_trance_on = _nb_prop("act.guest.trance.on", bool, "s137: the grace is in force (false = `actbench trancegrace "
                                                               "off`: the pre-s137 timing).")
    coop_act_trance_gate = _nb_prop("act.guest.trance.gate", bool, "s137: a model change defers NOW (a booted diorama, bit 5 "
                                                                   "latched this boot, a guest that can replay, `on`).")
    coop_act_trance_deferred = _nb_prop("act.guest.trance.deferred", int, "s137: model changes recorded to wait for their "
                                                                          "SysTrans burst.")
    coop_act_trance_pending = _nb_prop("act.guest.trance.pending", int, "s137: the wire-slot bits (0-3) of the deferrals "
                                                                        "waiting now (0 = none).")
    coop_act_trance_swaps_by_hit = _nb_prop("act.guest.trance.swaps_by_hit", int, "s137: swapped at the SysTrans replay's own "
                                                                                  "hit.")
    coop_act_trance_swaps_by_grace = _nb_prop("act.guest.trance.swaps_by_grace", int, "s137: swapped 400 ms of battle time "
                                                                                      "after nothing named the unit.")
    coop_act_trance_swaps_by_cap = _nb_prop("act.guest.trance.swaps_by_cap", int, "s137: swapped 2500 ms of battle time after "
                                                                                  "the sample, the unit still named (its own "
                                                                                  "burst in flight: 8500 ms, the ceiling).")
    coop_act_trance_swaps_by_decline = _nb_prop("act.guest.trance.swaps_by_decline", int, "s137: swapped at once: its "
                                                                                          "SysTrans START declined, or the "
                                                                                          "gate fell.")
    coop_act_trance_swaps_by_end = _nb_prop("act.guest.trance.swaps_by_end", int, "s137: swapped at once: its SysTrans "
                                                                                  "replay ended or aborted unswapped.")
    coop_act_trance_swaps_by_inject = _nb_prop("act.guest.trance.swaps_by_inject", int, "s137: swapped at an end "
                                                                                        "injection's head.")
    coop_act_trance_moot = _nb_prop("act.guest.trance.moot", int, "s137: resolved with the worn model already matching.")
    coop_act_trance_dropped = _nb_prop("act.guest.trance.dropped", int, "s137: resolved with no swap (a Leave, the teardown, "
                                                                        "a dead unit, no unit, a fault).")
    coop_act_trance_immediate = _nb_prop("act.guest.trance.immediate", int, "s137: swapped at the sample, ungated (no bit 5, "
                                                                            "a guest that cannot replay, the lever).")
    coop_act_trance_on_arrival = _nb_prop("act.guest.trance.on_arrival", int, "s137: swapped at the sample, gated: its burst "
                                                                              "had already hit, declined or ended.")
    coop_act_trance_hit_unpaired = _nb_prop("act.guest.trance.hit_unpaired", int, "s137: SysTrans hits that swapped with no "
                                                                                  "deferral pending.")
    coop_act_trance_hit_untrusted = _nb_prop("act.guest.trance.hit_untrusted", int, "s137: SysTrans hits that swapped NOTHING: "
                                                                                    "the bit frozen by s135's life mask, or "
                                                                                    "contradicting the replay's own vfx.")
    coop_act_trance_present = _nb_prop("act.guest.trance.present", int, "s137: btl_stat.SetPresentColor calls.")
    coop_act_trance_last = _nb_prop("act.guest.trance.last", dict, "s137: the last swap or resolution ({slot, swapped, to, "
                                                                   "via, id, record_ms, ms}); None = none this boot.")

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
    # ---- [ff9mapkit netsync R3 s119] the diorama watcher's hold, keyed on the PEER (guest side; s120: ``cap_ms`` is the
    # session grace, ``why`` gains "stall_cap"). The watcher needs a real transport: on the selftest role ``state`` reads ""
    diorama_hold = _dio_prop("hold", dict, "s119: the whole ``hold`` block, copied.")
    diorama_hold_state = _dio_prop("hold.state", str, "s119: the last DioramaWatchStep verdict for the booted wire diorama "
                                                      "-- 'nothing' | 'hold' | 'leave_final' ('' = none booted).")
    diorama_hold_since_ms = _dio_prop("hold.since_ms", int, "s119: the stale stretch's age; -1 = the lane is not stale (it "
                                                            "runs on through a pending leave until the teardown).")
    diorama_hold_cap_ms = _dio_prop("hold.cap_ms", int, "s119: the hold cap in force (8000; from s120 the session grace, "
                                                        "by default 30000 on s120-s131, 40000 from s132) -- a LIVE read.")
    diorama_hold_settle_ms = _dio_prop("hold.settle_ms", int, "s119: the stale age a hold is COUNTED at, and the unbroken "
                                                              "peer-alive run an over-verdict needs (500) -- a LIVE read.")
    diorama_hold_holds = _dio_prop("hold.holds", int, "s119: holds counted -- monotonic, read DELTAS.")
    diorama_hold_resumes = _dio_prop("hold.resumes", int, "s119: holds that ended live on the SAME nonce -- monotonic.")
    diorama_hold_gaveup = _dio_prop("hold.gaveup", int, "s119: holds that hit the cap (s120: or the stall cap) -- "
                                                        "monotonic.")
    diorama_hold_last_ms = _dio_prop("hold.last_ms", int, "s119: the last counted hold's length when it ended (a resume, a "
                                                          "leave's teardown); -1 = none.")
    diorama_hold_peer_alive = _dio_prop("hold.peer_alive", bool, "s119: the last step's PEER-ALIVE read (IsConnected && "
                                                                 "GetRemote().Valid).")
    diorama_hold_host_field = _dio_prop("hold.host_field", int, "s119: the host's position-lane field the last step read "
                                                                "(0 throughout its battle; -1 = the peer is not alive).")
    diorama_hold_terminal = _dio_prop("hold.terminal", bool, "s119: this boot's end block read terminal while the lane was "
                                                             "live (the latch).")
    diorama_hold_why = _dio_prop("hold.why", str, "s119: the last LEAVE_FINAL's reason -- 'new_nonce' | 'terminal' | "
                                                  "'host_field' | 'cap' | (s120) 'stall_cap' ('' = none this boot).")

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

    # [ff9mapkit netsync R3 s120/s121] two TOP-LEVEL `netsync` blocks (between ``diorama`` and ``battle``): ``session`` (s120)
    # and ``menu_refusal`` (s121). The same reading again, from the ``netsync`` block itself.
    def _ns_path(self, path: str, kind):
        """``netsync.<path>`` read as ``kind`` (bool / int / str null -> "" / dict copied); None when any step is absent or
        the type is wrong."""
        node = self.netsync
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
        raise TypeError(f"_ns_path: no reading for {kind!r}")

    # ---- [ff9mapkit netsync R3 s120] THE SESSION GRACE (guest side; NetSyncClient.SessionTick, keyed on PEER-ALIVE). "none"
    # on a host or the selftest role (they hold no session); the counters are per PROCESS -- read DELTAS
    netsync_session = _ns_prop("session", dict, "s120: the whole ``session`` block, copied.")
    session_grace_ms = _ns_prop("session.grace_ms", int, "s120: [Netsync] SessionGraceMs in force (the exit ramp's wait AND "
                                                         "the diorama hold's cap -- one value) -- a LIVE read.")
    session_state = _ns_prop("session.state", str, "s120: 'none' | 'live' | 'grace' | 'ended' ('' = no NetSyncClient "
                                                   "instance).")
    session_left_ms = _ns_prop("session.left_ms", int, "s120: the grace left in this outage; -1 = not inside one.")
    session_out_ms = _ns_prop("session.out_ms", int, "s120: the outage's age; -1 = none (it runs on past a give-up until "
                                                     "the peer returns).")
    session_outages = _ns_prop("session.outages", int, "s120: outages started -- monotonic.")
    session_resumes = _ns_prop("session.resumes", int, "s120: peers back INSIDE the grace -- monotonic.")
    session_gaveup = _ns_prop("session.gaveup", int, "s120: graces run out -- monotonic.")
    session_last_ms = _ns_prop("session.last_ms", int, "s120: the last outage's length when the peer returned; -1 = none.")
    session_peer_alive = _ns_prop("session.peer_alive", bool, "s120: the last PEER-ALIVE read (IsConnected && "
                                                              "GetRemote().Valid).")
    session_seen_live = _ns_prop("session.seen_live", bool, "s120: this link carried a live peer (an outage needs a "
                                                            "session to lose).")
    session_mirroring = _ns_prop("session.mirroring", bool, "s120: IsMirroringStory -- the story mirror armed, the save "
                                                            "gates hold.")
    session_ramp_pending = _ns_prop("session.ramp_pending", bool, "s120: the exit ramp is pending.")
    session_ramp_cause = _ns_prop("session.ramp_cause", str, "s120: 'grace' | 'config' | 'unfollow' ('' = none pending).")
    session_overlay = _ns_prop("session.overlay", str, "s120: the status overlay -- 'off' | 'elsewhere' | 'no_code' | "
                                                       "'connecting' | 'waiting' | 'peer_elsewhere' | 'following' | "
                                                       "'peer_no_field' | 'reconnecting' ('' = none composed yet).")
    session_overlay_detail = _ns_prop("session.overlay_detail", int, "s120: its detail -- the seconds left for "
                                                                     "'reconnecting', 1 = a guest's hop up with no live "
                                                                     "peer for 'connecting', a field id, 0 = no detail; "
                                                                     "-1 = none composed yet.")
    session_ghost = _ns_prop("session.ghost", bool, "s120: the peer's ghost is spawned here.")
    session_ghost_held = _ns_prop("session.ghost_held", bool, "s120: the s56 blip-grace holds it frozen this frame.")
    # ---- [ff9mapkit netsync R3 s121] THE AUDIBLE MENU REFUSAL (guest side; NetSyncField.RefuseMainMenu): gate a bench's
    # press on ``menu_refusal_now`` == "audible", never on ui_state FieldHUD (under a dialogue window it reads "dialog")
    netsync_menu_refusal = _ns_prop("menu_refusal", dict, "s121: the whole ``menu_refusal`` block, copied.")
    menu_refusal_now = _ns_prop("menu_refusal.now", str, "s121: what a Menu press would do right now -- 'open' | 'off' | "
                                                         "'audible' | 'silent' | 'dialog' ('' = no UIManager) -- a LIVE "
                                                         "read.")
    menu_refusal_count = _ns_prop("menu_refusal.count", int, "s121: audible refusals (SFX 102 each) -- monotonic.")
    menu_refusal_lines = _ns_prop("menu_refusal.lines", int, "s121: of those, the ones that wrote the line -- a per-PROCESS "
                                                             "latch per (class, place), never cleared at session end "
                                                             "(count is the per-press signal) -- monotonic.")
    menu_refusal_silent = _ns_prop("menu_refusal.silent", int, "s121: s38's silent drops (a mirroring guest off FieldHUD / "
                                                               "WorldHUD) -- monotonic.")
    menu_refusal_last_state = _ns_prop("menu_refusal.last_state", str, "s121: the UIState name of the last refused press, "
                                                                       "either kind ('' = none yet).")
    menu_refusal_last_field = _ns_prop("menu_refusal.last_field", int, "s121: the place it named -- fldMapNo, or wldMapNo "
                                                                       "on WorldHUD; -1 = none yet.")
    menu_refusal_age_ms = _ns_prop("menu_refusal.age_ms", int, "s121: ms since that press; -1 = none yet.")
    menu_refusal_muted = _ns_prop("menu_refusal.muted", bool, "s121: FF9Sfx.muteSfx at the last audible refusal (the buzz "
                                                              "was asked for, the engine muted it).")

    # ---- [ff9mapkit netsync s138] THE DRESS INSTRUMENT (studies/battle-coop/R3-DESIGN.md 3.4.2 as amended by
    # R3-FIELD-MODEL-AUDIT.md 2.1, whose 3.1 nests the block as `netsync.dress`, netsync's LAST key): harness keys only, in
    # EVERY role. The capability is the block's PRESENCE (absent = None per key, False for :attr:`coop_dress_instr`): the
    # `coop_dress_*` family is this block's alone (its own table, :attr:`NETSYNC_DRESS_ACCESSORS`). THE NAMES: a key's
    # accessor is `coop_dress_<path>`; a fixed sub-object's WHOLE accessor is `coop_dress_<path>_block` (never the bare
    # `coop_dress_<path>`: audit 3.1 reserves `coop_dress_instr` / `_host` / `_self` / `_polish` for the rungs' BOOLEAN
    # capabilities -- s140's `self` container would collide). `ghost` is what the peer's ghost WEARS on this screen:
    # `model` / `geo` / `rig` the body the CURRENT ghost was built for, while `clip` already follows the caller's rig -- a
    # re-dress requested off FieldHUD is not applied, and the engine's Update has no fixed order against the publish, so
    # compare the ghost with the player on FieldHUD only, once its tuple has held 2+ consecutive FieldHUD publishes. `party`
    # is a LIVE read (FF9.party.member[i].Index, raw CharacterId: 0-7 the mains, 8-11 Cinna..Beatrix, 12+ custom; -1
    # (battlewire.PARTY_EMPTY) an empty seat, -2 (PARTY_UNREADABLE) a seat whose read threw -- never an empty one) -- never
    # the selftest mirror's NetSyncParty.Slots. THE RIG SPACE (battlewire.RIG_NAMES): -1 none, 0-7 the CharacterId rows, 8
    # the moogle (s139) -- never compared with a CharacterId at 8.
    def _dress_path(self, path: str, kind):
        """``netsync.dress.<path>`` read as ``kind`` (bool / int / str null -> "" / list copied / dict copied); None when any
        step is absent or the type is wrong."""
        ns = self.netsync
        node = ns.get("dress") if isinstance(ns, dict) else None
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
        if kind is list:
            return _json_copy(node) if isinstance(node, list) else None
        if kind is dict:
            return _json_copy(node) if isinstance(node, dict) else None
        raise TypeError(f"_dress_path: no reading for {kind!r}")

    @property
    def coop_dress_instr(self) -> bool | None:
        """s138: the dress instrument (``netsync.dress.ghost``; with it the ``player.*`` body keys and ``objects[].model``
        -- each half told by its own key: :attr:`player_dress_status`, :attr:`object_models`). False = an engine before
        s138 (no sub-verb, op or lever: nothing to refuse)."""
        if not isinstance(self.netsync, dict):
            return None
        return self._dress_path("ghost", dict) is not None

    @property
    def netsync_dress(self) -> dict | None:
        """s138: the whole ``netsync.dress`` block, copied (None when absent)."""
        ns = self.netsync
        v = ns.get("dress") if isinstance(ns, dict) else None
        return _json_copy(v) if isinstance(v, dict) else None

    coop_dress_ghost_block = _dress_prop("ghost", dict, "s138: the whole ``ghost`` block, copied (a FIXED sub-object; its "
                                                         "whole accessor is `_block`-suffixed, never `coop_dress_ghost`).")
    coop_dress_ghost_model = _dress_prop("ghost.model", int, "s138: the model id the CURRENT ghost was built to wear "
                                                             "(_ghostModel); -1 = no ghost.")
    coop_dress_ghost_geo = _dress_prop("ghost.geo", str, "s138: the GEO name CreateModel BUILT (FallbackGeo GEO_MAIN_F0_ZDN "
                                                         "when the id did not resolve or load); '' = no ghost.")
    coop_dress_ghost_clip = _dress_prop("ghost.clip", str, "s138: the clip DriveGhost last asked for (set even when its Play "
                                                           "failed) -- it already follows the CALLER's rig, ahead of a "
                                                           "re-dress deferred off FieldHUD; '' = none.")
    coop_dress_ghost_rig = _dress_prop("ghost.rig", int, "s138: the rig of the dress the ghost WEARS -- -1 undressed / no "
                                                         "ghost, 0-7 the CharacterId rows (s139: 8 the moogle). A deferred "
                                                         "off-FieldHUD re-dress keeps the old model and rig while DriveGhost "
                                                         "already plays the new rig's clips: judge rig with model on FieldHUD "
                                                         "only, the tuple held 2+ publishes.")
    coop_dress_ghost_playing = _dress_prop("ghost.playing", bool, "s138: Animation.IsPlaying(clip) on the ghost -- the "
                                                                  "witness `clip` alone cannot fake; False = no ghost.")
    coop_dress_ghost_body = _dress_prop("ghost.body", str, "s138: the ghost's worn-texture GEO-id stem (the player's own "
                                                           "rule: its mesh0); '' = no ghost (or an unnamed texture).")
    coop_dress_party = _dress_prop("party", list, "s138: the four party slots' raw CharacterId (FF9.party.member[i].Index); "
                                                  "-1 = an empty slot, -2 = an unreadable one (its read threw).")

    # ---- [ff9mapkit netsync s139] THE HOST'S DRESS RULE (R3-FIELD-MODEL-AUDIT.md 2.2, its 3.1 sentinels): `ghost` gains the
    # selftest `selfdress` levers AS SET at its end (published in every role; they ACT on the selftest role only) and `mode`;
    # `netsync.dress` gains `codec` and `rig_idle_frames` after `party`. The capability is `ghost.bench_mask`'s PRESENCE
    # (:attr:`coop_dress_host`; the bench probe ladder tells s139 by `codec` -- battlewire.DRESS_PROBES). The selftest
    # mirror under the forced role IS the guest and this machine its host: with GuestSlots pinned 0 a `GhostAs = auto` dresses
    # it as the MOOGLE (owner D2) -- read `mode` before judging what it wears.
    @property
    def coop_dress_host(self) -> bool | None:
        """s139: the host dress rule and section 8 (``netsync.dress.ghost.bench_mask``; the ``selfdress`` sub-verb). False =
        an engine whose host dresses its guest's ghost by the first named bit and ships no section 8 (s138 and older; it
        answers `netsync selfdress` with "unknown sub-verb")."""
        if not isinstance(self.netsync, dict):
            return None
        return self._dress_path("ghost.bench_mask", int) is not None

    coop_dress_ghost_bench_mask = _dress_prop("ghost.bench_mask", int, "s139: the `selfdress ghost <mask>` lever as set (the "
                                                                       "selftest mirror's dress mask, mode auto); -1 = off.")
    coop_dress_ghost_empty_mask = _dress_prop("ghost.empty_mask", int, "s139: the `selfdress empty <mask>` lever as set (those "
                                                                       "party slots read EMPTY to the dress rules); -1 = off.")
    coop_dress_ghost_rule = _dress_prop("ghost.rule", str, "s139: the `selfdress rule` lever as last set -- 's138' (THE "
                                                           "CALIBRATION: the pre-s139 selftest site) or 's139'; '' = never "
                                                           "set.")
    coop_dress_ghost_wire = _dress_prop("ghost.wire", int, "s139: the `selfdress wire <model>` lever as set (the mirror's wire "
                                                           "body: the guard's input, the undressed body); -1 = off.")
    coop_dress_ghost_wire_anim = _dress_prop("ghost.wire_anim", int, "s139: the raw clip `selfdress wire <model> <anim>` pins "
                                                                     "the stand-in wire body to (the raw-anim rule's "
                                                                     "input); -1 = none (it moves with the player's loco).")
    coop_dress_ghost_rest_mask = _dress_prop("ghost.rest_mask", int, "s139: CreateModel's own field-mode visibility of the "
                                                                     "ghost, snapshotted before the force-enable (bit i = "
                                                                     "renderer i, at most 16 -- the REST MASK); -1 = no "
                                                                     "ghost.")
    coop_dress_ghost_shown_mask = _dress_prop("ghost.shown_mask", int, "s139: the ghost's renderers enabled NOW, the same "
                                                                       "bits as `rest_mask`; -1 = no ghost.")
    coop_dress_ghost_hidden = _dress_prop("ghost.hidden", list, "s139: every ghost renderer disabled now, as its path under "
                                                                "the ghost's root (['short_hair']); None = no ghost (the "
                                                                "key null) or an engine before s139.")
    coop_dress_ghost_mode = _dress_prop("ghost.mode", str, "s139: the dress mode this screen's ghost reads -- 'bench:auto' "
                                                           "(the `ghost` lever, selftest role) or 'ini:' + the ini's trimmed "
                                                           "GhostAs ('ini:' = none); '' = no NetSyncClient instance.")
    coop_dress_codec = _dress_prop("codec", str, "s139: the dress codec proof's verdict -- 'ok' or 'fail: <row>' "
                                                 "(NetSyncClient.DressSelfTest, once per process in the selftest proof "
                                                 "block); '' = not run yet.")
    coop_dress_rig_idle_frames = _dress_prop("rig_idle_frames", list, "s139: one int per rig row (s139: nine -- 0-7 the "
                                                                      "CharacterId rows, 8 the moogle; s140: thirteen, 9-12 "
                                                                      "Cinna, Marcus, Blank, Beatrix) -- each idle clip's "
                                                                      "frame count, MEASURED once per process by the proof "
                                                                      "block (round(length x rate) + 1 on the clip loaded "
                                                                      "the AnimationFactory way); -1 = not measured. Judge "
                                                                      "it against the install's oracle, never alone.")
    coop_dress_mirror_party = _dress_prop("mirror_party", list, "s139: the PARTY MIRROR an old reader landed "
                                                                "(NetSyncParty.Slots' CharacterIds, -1 an absent slot) -- on "
                                                                "a live guest the witness that its s103 walker stepped past "
                                                                "the host's section 8; None = no mirror active (the key "
                                                                "null) or an engine before s139.")

    # ---- [ff9mapkit netsync s140] THE GUEST DRESSES ITSELF (R3-FIELD-MODEL-AUDIT.md 2.3, its 3.1 sentinels): `netsync.dress`
    # gains `self`, its LAST key -- a FIXED sub-object (always whole, every role: a host reads its sentinels) with `law_off`
    # a fixed sub-object inside it. The capability is `self`'s PRESENCE (:attr:`coop_dress_self`; the probe ladder's 140
    # rung, battlewire.DRESS_PROBES). THE ARM (`armed` = the arm AND the knob; `want_*` / `why` / `from`) is set at a FIELD
    # LOAD only (a `self` lever acts at the NEXT load); THE BODY's keys (`src`, `rig`, `net_byte`) read the CONTROLLED body --
    # every map keys on it, never on `want_rig` (amendment 5): after a Clear() `want_rig` reads -1 while `rig` still reads the
    # dress. `knob` is [Netsync] SelfDress read LIVE (never an arm state). Rig 9 is Cinna, CharacterId 9 Marcus: decode
    # `rig` / `want_rig` through battlewire.RIG_NAMES, `want_char` as a CharacterId.
    @property
    def coop_dress_self(self) -> bool | None:
        """s140: the guest's own dress (``netsync.dress.self``; the ``selfdress self|gate|law`` ops). False = an engine whose
        guest never dresses itself (s139 and older -- it answers `selfdress self` with "unknown op ... (ghost|empty|rule|
        wire|clear)")."""
        if not isinstance(self.netsync, dict):
            return None
        return self._dress_path("self", dict) is not None

    coop_dress_self_block = _dress_prop("self", dict, "s140: the whole ``self`` block, copied (a FIXED sub-object; its whole "
                                                      "accessor is `_block`-suffixed, never `coop_dress_self` -- the "
                                                      "capability).")
    coop_dress_self_knob = _dress_prop("self.knob", bool, "s140: [Netsync] SelfDress as read LIVE (default 1): 0 switches off "
                                                          "only THIS guest's own dressing (owner D1) -- never an arm state.")
    coop_dress_self_armed = _dress_prop("self.armed", bool, "s140: the arm AND the knob -- what SetModel's fresh dress reads.")
    coop_dress_self_src = _dress_prop("self.src", int, "s140: the controlled body's netDressSrc -- 98 dressed, 0 undressed; -1 "
                                                       "= no controlled body.")
    coop_dress_self_want_model = _dress_prop("self.want_model", int, "s140: section 8's model as last read (the host's, or the "
                                                                     "bench spec's); -1 = no section 8 read.")
    coop_dress_self_want_char = _dress_prop("self.want_char", int, "s140: section 8's charId as last read (a CharacterId 0-11, "
                                                                   "255 the moogle / no dress); -1 = no section 8 read.")
    coop_dress_self_want_rig = _dress_prop("self.want_rig", int, "s140: the rig section 8's model is (RigForModel; 9-12 = "
                                                                 "Cinna..Beatrix); -1 = none.")
    coop_dress_self_rig = _dress_prop("self.rig", int, "s140: the rig the CONTROLLED body wears (netSelfDress - 1); -1 = "
                                                       "undressed or no body. Every map keys on THIS, never want_rig.")
    coop_dress_self_why = _dress_prop("self.why", str, "s140: the latest decision -- 'armed', a disarm reason ('section "
                                                       "absent', 'section8_len', 'model 0', 'zidane', 'charid', 'no rig', 'not "
                                                       "mirroring', 'fault', 'cleared') or a SetModel outcome ('excluded', "
                                                       "'dressed'); '' = never decided.")
    coop_dress_self_uid = _dress_prop("self.uid", int, "s140: the uid last dressed (or re-attached on a warm return); -1.")
    coop_dress_self_net_byte = _dress_prop("self.net_byte", int, "s140: the controlled body's netSelfDress raw (rig + 1; 0 "
                                                                 "undressed); -1 = no body.")
    coop_dress_self_from = _dress_prop("self.from", str, "s140: where the arm came from -- 'host' (section 8 off the wire) or "
                                                         "'bench' (the selftest `self` spec); '' = none.")
    coop_dress_self_confirmed = _dress_prop("self.confirmed", int, "s140: DefinePlayerCharacter bound control to the dressed "
                                                                   "body -- per process.")
    coop_dress_self_ctl_elsewhere = _dress_prop("self.ctl_elsewhere", int, "s140: ...to ANOTHER body while one is dressed "
                                                                           "(a co-actor binder, D3) -- per process.")
    coop_dress_self_ctl_elsewhere_field = _dress_prop("self.ctl_elsewhere_field", int, "s140: the field of the last "
                                                                                       "ctl_elsewhere; -1 = none.")
    coop_dress_self_skip_npc = _dress_prop("self.skip_npc", int, "s140: a 98 SetModel on an entry that defines no player (the "
                                                                 "player gate) -- per process.")
    coop_dress_self_skip_second = _dress_prop("self.skip_second", int, "s140: a 98 SetModel while another DRESSED body holds "
                                                                       "control -- per process.")
    coop_dress_self_remaps = _dress_prop("self.remaps", int, "s140: a setter / RunAnimation id MapAndAttach changed -- per "
                                                             "process.")
    coop_dress_self_timeline_kept = _dress_prop("self.timeline_kept", int, "s140: a gesture kept its SOURCE frame count "
                                                                           "(KeepSourceTimeline) -- per process.")
    coop_dress_self_gate = _dress_prop("self.gate", bool, "s140: the player gate as it acts NOW -- false only under `selfdress "
                                                          "gate 0` on the selftest role.")
    coop_dress_self_bframe_remaps = _dress_prop("self.bframe_remaps", int, "s140: GetAnimDuration answered a loco family's "
                                                                           "NATIVE clip (the B_FRAME law) -- per process.")
    coop_dress_self_src_attached = _dress_prop("self.src_attached", int, "s140: the dressed body's clip count after the last "
                                                                         "AttachDress (a LAST-WRITE value: read it across an "
                                                                         "attach_cold / attach_warm delta); 0 = the attach law "
                                                                         "was off or none ran.")
    coop_dress_self_src_list_clips = _dress_prop("self.src_list_clips", int, "s140: of those, the SOURCE list's "
                                                                             "(GEO_MAIN_F0_ZDN) clips.")
    coop_dress_self_attach_cold = _dress_prop("self.attach_cold", int, "s140: AttachDress ran at site (a), SetModel after "
                                                                       "CreateModel -- per process: a load's delta.")
    coop_dress_self_attach_warm = _dress_prop("self.attach_warm", int, "s140: AttachDress ran at site (b), the warm-return "
                                                                       "rebuild (updateModelsToBeAdded) -- per process.")
    coop_dress_self_faults = _dress_prop("self.faults", int, "s140: a self-dress hook caught an exception -- per process.")
    coop_dress_self_parse_fallback = _dress_prop("self.parse_fallback", int, "s140: EntryDefinesPlayer answered by the "
                                                                             "character band after its parse threw.")
    coop_dress_self_defence_kept = _dress_prop("self.defence_kept", int, "s140: SetModel's defence branch kept a dress (0 in "
                                                                         "stock).")
    coop_dress_self_defence_dropped = _dress_prop("self.defence_dropped", int, "s140: ...dropped one (0 in stock).")
    coop_dress_self_bench_self = _dress_prop("self.bench_self", str, "s140: the `selfdress self` spec AS SET -- 'off' | 'auto' "
                                                                     "| 'auto <mask>' | a name; '' = never set (no section "
                                                                     "8).")
    coop_dress_self_law_off_block = _dress_prop("self.law_off", dict, "s140: the whole ``law_off`` block, copied (a FIXED "
                                                                      "sub-object: each s140 law's `law <name> off` lever AS "
                                                                      "SET).")
    coop_dress_self_law_off_bframe = _dress_prop("self.law_off.bframe", bool, "s140: `law bframe off` as set (the B_FRAME "
                                                                              "remap; it acts on the selftest role only).")
    coop_dress_self_law_off_attach = _dress_prop("self.law_off.attach", bool, "s140: `law attach off` as set (the source-list "
                                                                              "attach + stored loco ids).")
    coop_dress_self_law_off_alias = _dress_prop("self.law_off.alias", bool, "s140: `law alias off` as set (the idle-alias "
                                                                            "fallback).")
    coop_dress_self_law_off_timeline = _dress_prop("self.law_off.timeline", bool, "s140: `law timeline off` as set "
                                                                                  "(KeepSourceTimeline).")
    coop_dress_self_selftest = _dress_prop("self.selftest", str, "s140: the self-dress proof's verdict -- 'ok' or 'fail: "
                                                                 "<row>' (NetSyncSelfDress.SelfTest, once per process in the "
                                                                 "selftest proof block); '' = not run yet.")

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

    # [ff9mapkit netsync s134] the action replay made readable (after `z`, before `status`); None = no such unit / before s134
    def unit_anim(self, slot: int) -> str | None:
        """[ff9mapkit netsync s134] ``battle.units[].anim``: the current clip's NAME (an enemy sequence clip has no motion
        index); "" = none."""
        for u in self.battle.get("units", []):
            if isinstance(u, dict) and u.get("slot") == slot:
                v = u.get("anim", 0)
                return "" if v is None else v if isinstance(v, str) else None
        return None

    def unit_anim_frame(self, slot: int) -> int | None:
        """[ff9mapkit netsync s134] ``battle.units[].anim_frame`` (evt.animFrame)."""
        return self._unit_num(slot, "anim_frame", int)

    def unit_away(self, slot: int) -> float | None:
        """[ff9mapkit netsync s134] ``battle.units[].away`` (|pos - base_pos|: an attacker's run out and back)."""
        return self._unit_num(slot, "away", float)

    def unit_rot_y(self, slot: int) -> float | None:
        """[ff9mapkit netsync s134] ``battle.units[].rot_y`` (rot's yaw, degrees)."""
        return self._unit_num(slot, "rot_y", float)

    def unit_acting(self, slot: int) -> bool | None:
        """[ff9mapkit netsync s134] ``battle.units[].acting``: a co-op guest's running action replay acts with this unit."""
        for u in self.battle.get("units", []):
            if isinstance(u, dict) and u.get("slot") == slot:
                v = u.get("acting")
                return v if isinstance(v, bool) else None
        return None

    def unit_die_seq(self, slot: int) -> int | None:
        """[ff9mapkit netsync s134] ``battle.units[].die_seq`` (0 = none, 5+ = faded)."""
        return self._unit_num(slot, "die_seq", int)

    def unit_row(self, slot: int) -> int | None:
        """[ff9mapkit netsync s134] ``battle.units[].row`` (bi.row: a Change flips it)."""
        return self._unit_num(slot, "row", int)

    def unit_trance_model(self, slot: int) -> bool | None:
        """[ff9mapkit netsync s137] ``battle.units[].trance_model``: the unit WEARS its trance model now (gameObject ==
        tranceGo; false for a unit without one) -- read from the seated unit, never assumed. None = no such unit / before
        s137."""
        for u in self.battle.get("units", []):
            if isinstance(u, dict) and u.get("slot") == slot:
                v = u.get("trance_model")
                return v if isinstance(v, bool) else None
        return None

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
#: ``intro.swirl_clamp``, s114 ``live``; [ff9mapkit netsync R3 s119] ``hold``) -> its State accessor -- held against the
#: agent's keys the same way.
State.NETSYNC_DIORAMA_ACCESSORS = {p.fget.dio_path: name for name, p in vars(State).items()
                                   if isinstance(p, property) and hasattr(p.fget, "dio_path")}
#: [ff9mapkit netsync R3 s120/s121] Every key path of the top-level ``netsync.session`` (s120) and ``netsync.menu_refusal``
#: (s121) blocks (dotted under ``netsync``) -> its State accessor -- held against the agent's keys the same way.
State.NETSYNC_TOP_ACCESSORS = {p.fget.ns_path: name for name, p in vars(State).items()
                               if isinstance(p, property) and hasattr(p.fget, "ns_path")}
#: [ff9mapkit netsync s138] Every ``netsync.dress`` key path (dotted under ``netsync.dress``) -> its State accessor -- the
#: dress block's own table (never NETSYNC_TOP_ACCESSORS, whose law pins `session` / `menu_refusal`).
State.NETSYNC_DRESS_ACCESSORS = {p.fget.dress_path: name for name, p in vars(State).items()
                                 if isinstance(p, property) and hasattr(p.fget, "dress_path")}
#: [ff9mapkit netsync s138] Every ``player`` dress key (OUTSIDE netsync, battlewire.PLAYER_DRESS_KEYS) -> its State accessor.
State.PLAYER_DRESS_ACCESSORS = {p.fget.pl_key: name for name, p in vars(State).items()
                                if isinstance(p, property) and hasattr(p.fget, "pl_key")}


def _f(v) -> str:
    return "?" if v is None else f"{v:.1f}"


class Channel:
    """The file-backed request/state channel. Owns the directory and the arming lock."""

    def __init__(self, game_path: Path, *, label: str = "run", owner_pid: int | None = None,
                 nonce: str | None = None, sibling_guard: bool = False):
        self.game_path = Path(game_path)
        self.dir = self.game_path / "x64" / "ff9harness"
        self.shots = self.dir / "shots"
        self.label = label
        self.owner_pid = os.getpid() if owner_pid is None else int(owner_pid)
        #: This channel's own mark in the arm body, beside the pid. The pid alone cannot tell two Sessions of ONE process
        #: apart -- a duo drives two from one driver -- so a claim or disarm that matched on the pid would let one of them
        #: take or drop the other's arm. See :data:`_LIVE_ARMS` for why this changes nothing for a lone Session.
        self.nonce = nonce or uuid.uuid4().hex[:16]
        #: Whether claim() refuses, and disarm() leaves, a LIVE sibling's arm (same pid, another live armed Channel here).
        #: Off by default -- a lone Session on the shared install takes over any same-pid arm exactly as it always did
        #: (its own suite models a leaked arm that way) -- and on for an instance-root Session (harness.duo's two halves),
        #: where the root's claim is the first guard and this the second.
        self.sibling_guard = bool(sibling_guard)
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
        if self.sibling_guard and self._live_sibling(owner):
            raise HarnessError(
                f"another Session in THIS process already has {self.dir} armed: label {owner.get('label')!r}, "
                f"nonce {owner.get('nonce')}, started {owner.get('started')}. Two Sessions on one channel overwrite "
                f"each other's requests and evidence -- a duo needs two instance roots, not one twice."
            )
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
            "nonce": self.nonce,
        }), encoding="utf-8")
        self._armed_by_us = True
        _LIVE_ARMS[self.nonce] = self
        return seen

    def _live_sibling(self, owner: dict) -> bool:
        """Whether ``owner`` (an arm body) is another LIVE Channel of this very process -- same pid, a different nonce
        that a Channel here still holds (:data:`_LIVE_ARMS`)."""
        nonce = owner.get("nonce")
        try:
            pid = int(owner.get("pid", -1) or -1)
        except (TypeError, ValueError):
            return False
        if pid != self.owner_pid or not nonce or nonce == self.nonce:
            return False
        other = _LIVE_ARMS.get(nonce)
        return other is not None and other is not self and other._armed_by_us

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
            if self.sibling_guard and self._live_sibling(owner):
                _LIVE_ARMS.pop(self.nonce, None)
                self._armed_by_us = False
                return
        _unlink(self.arm_path)
        _LIVE_ARMS.pop(self.nonce, None)
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
