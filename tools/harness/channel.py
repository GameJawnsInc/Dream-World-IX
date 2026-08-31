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
PROTOCOL = 4

#: The agent polls the arm file every 30 frames (HarnessAgent.PollArm). A delete+create inside one
#: window is INVISIBLE to it -- ``armed == Active``, early return, no reset of seq/ack, no button
#: clear. So a re-arm has to outlast the poll to be a real transition, and this is that wait, sized
#: for a game running well below 60fps.
ARM_CYCLE_SECONDS = 0.85

#: A published document older than this is not a live game talking.
STALE_AFTER = 5.0


class HarnessError(RuntimeError):
    """A harness-level failure: the game is gone, a step was refused, or a wait timed out."""


def pid_alive(pid: int) -> bool:
    """Windows-safe liveness probe.

    ⚠ NEVER ``os.kill(pid, 0)`` here. On Windows CPython routes every signal but the console-control
    ones to ``TerminateProcess``, so the textbook liveness idiom would KILL the process it asks about
    -- in this case another agent's game, or another agent's driver.
    """
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    try:
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    except (OSError, AttributeError):
        return True                       # cannot tell -> assume alive, never steal another run's arm
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    return ctypes.get_last_error() == 5    # ERROR_ACCESS_DENIED -> it exists, we just cannot look


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


class State:
    """One sample of the game's state, as published by the agent.

    Attribute access is flattened for the fields a scenario actually asserts on (``field_id``,
    ``player_x`` ...); ``raw`` keeps the full document for anything not surfaced here yet.

    Accessors for values a NEWER agent publishes return ``None`` when the key is absent rather than a
    plausible default, so "this DLL does not publish that" can never be mistaken for game data.
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

    # -- lifecycle --------------------------------------------------------------------------
    def reset(self) -> None:
        """Clear the channel for a fresh run. Leaves ``arm`` alone -- arming is a separate decision."""
        self.shots.mkdir(parents=True, exist_ok=True)
        for name in ("req.txt", "state.json", "state.json.tmp", "events.jsonl"):
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

    def arm(self, *, force_cycle: bool = True) -> None:
        """Arm the agent -- as a REAL false->true transition, not merely 'a file exists'.

        ⚠ Writing over an existing ``arm`` file is a NO-OP as far as the agent is concerned. Its
        ``PollArm`` compares ``File.Exists`` against its own ``Active`` flag and returns early when
        they agree, so an already-armed agent never reaches the branch that resets ``_seq``/``_ack``,
        clears every held button and clears the error latch. A leaked arm file therefore hands the
        next run an agent that discards its requests as stale while acking instantly -- every step a
        silent no-op, and the first measurement blames the game.

        So: delete, wait out the agent's 30-frame poll so the disarm is OBSERVED, then create.
        ``force_cycle=False`` skips the wait when there is no game running to observe it.
        """
        self.claim()
        self.dir.mkdir(parents=True, exist_ok=True)
        if self.arm_path.exists():
            _unlink(self.arm_path)
            if force_cycle:
                time.sleep(ARM_CYCLE_SECONDS)
        self.arm_path.write_text(json.dumps({
            "pid": self.owner_pid,
            "label": self.label,
            "started": _dt.datetime.now().isoformat(timespec="seconds"),
            "tool": "tools/harness",
        }), encoding="utf-8")
        self._armed_by_us = True

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
        rewrites this file ~30 times a second and a poller can easily collide with it. Treating the
        resulting PermissionError as absence made the driver declare a perfectly healthy game dead,
        and that false verdict was then repeated as "walking out of the room hangs the game" -- a bug
        attributed to the game that lived entirely in the driver. Locks get their own, much longer,
        budget. Use :meth:`classify` to say WHICH of the reasons for ``None`` applies.
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
                return State(json.loads(body), mtime=mtime)
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
        MISSING (never written), LOCKED (a sharing violation we could not wait out), UNPARSEABLE
        (a torn or corrupt document -- e.g. an agent exception mid-append), STALE (a real document
        nobody has updated), DISARMED (the agent says so itself), OK.
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
