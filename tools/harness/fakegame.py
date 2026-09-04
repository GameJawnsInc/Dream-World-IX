#!/usr/bin/env python3
"""A protocol stand-in for the in-game agent, so the driver can be tested with no game running.

WHAT THIS PROVES, AND WHAT IT DOES NOT. It implements the s83 wire protocol -- sequence handling,
the arm transition, frame-stepped queue draining, state publication, screenshots -- plus just enough
of a world (a rectangular walkmesh, a run/walk speed, a gateway, a dialogue box, a menu cursor) for
the driver's closed-loop verbs to actually close their loops. A green run against it says the DRIVER
is correct: seq numbers advance, acks belong to the request that earned them, torn reads are
survived, timeouts fire, bad bases are rejected, artifacts land.

⚠ IT SAYS NOTHING ABOUT THE ENGINE. It models the agent as SPECIFIED, not the DLL as deployed -- so
a green suite means the driver still handles what it was taught, and nothing about whether a warp
lands, a button moves a character, or the bytes on disk behave. Those are only ever answered by a
real game, and this project has learned repeatedly that a passing offline gate is a regression
harness, not an oracle.

It exists because the alternative is worse: debugging the driver and the engine at the same time,
through a 40-second game launch, with no way to tell which half is lying.

THE FAULT MODES ARE THE POINT. ``FakeGame(mode=...)`` can be a game that freezes its frame counter,
one that slides the character along a wall instead of walking, one that hands over control before it
has a position, one whose agent kept a stale sequence number, and one that never resets on re-arm.
Each of those is a real failure this harness has produced or nearly produced, and each has a driver
behaviour that must be asserted rather than assumed.
"""
from __future__ import annotations

import json
import struct
import threading
import time
import zlib
from pathlib import Path

#: IMPORTED, not restated. This stand-in models the agent AS SPECIFIED, so publishing an older
#: version would put every offline run in the DEGRADED path instead of the real one -- a suite
#: permanently in a compatibility mode it is not meant to be testing. It was a second literal
#: until rev 4, and a second literal is a skew waiting for someone to bump only one of them: that
#: is exactly what happened, and 23 tests failed reporting the wrong cause.
from .channel import PROTOCOL

#: The real agent polls req.txt every 2 frames while idle and every 10 while a queue is running, and
#: the arm file every 30. Modelled because the driver's "do not overwrite an unaccepted request" gate
#: only means anything against a reader that is not instantaneous.
REQ_POLL_IDLE = 2
REQ_POLL_BUSY = 10
ARM_POLL = 30

RUN_SPEED = 30.0
WALK_SPEED = 15.0

#: FF9's own soft reset: L1+R1+L2+R2+Start+Select, all reporting IsInputDown on ONE frame.
#: Modelled with the same-frame requirement intact, because that requirement is the whole reason the
#: driver has to send all six in a single request -- six separate presses would never overlap, and a
#: stand-in that accepted them sequentially would let a broken driver pass.
SOFT_RESET_COMBO = ("l1", "l2", "r1", "r2", "start", "select")


class FakeGame:
    """Runs the agent's side of the protocol in a background thread at a simulated frame rate."""

    def __init__(self, game_path: Path, *, fps: float = 240.0, boot_state: str = "Title",
                 mode: str = "normal", walkmesh=(-600.0, -600.0, 600.0, 600.0),
                 resets_on_arm: bool = True, twist: float = 0.0):
        self.dir = Path(game_path) / "x64" / "ff9harness"
        self.shots = self.dir / "shots"
        self.fps = fps
        #: The protocol this stand-in claims to speak, or None to follow the module constant. A
        #: dial so a test can put an OLDER engine on the wire -- otherwise the driver's "rebuild
        #: the DLL" refusal is a guard that can never fire, which is the same shape as no guard.
        #: ⚠ None rather than a snapshot: the module constant is also monkeypatched by a test, and
        #: a value captured here at construction would silently ignore that.
        self.protocol: int | None = None
        self.mode = mode
        self.resets_on_arm = resets_on_arm
        #: Screen-to-world yaw, in degrees. FF9 fields are viewed by a fixed camera that is
        #: frequently yawed and movement is expressed in SCREEN space, so "up" is +z on one field
        #: and something diagonal on the next. A stand-in that always mapped up to +z would let a
        #: broken calibration pass, which is the one thing calibrate_axes exists to prevent.
        self.twist = float(twist)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.returncode: int | None = None

        # the simulated world
        self.frame = 0
        self.publish_frame = 0
        self.seq = -1
        self.ack = -1
        self.error_seq = -1
        self.pending_ack = False
        self.queue: list[list[str]] = []
        self.block_until = 0
        self.arm_seen = False
        self.armed = False
        self.arm_poll_frame = 0
        self.req_poll_frame = 0
        self.state_every = 2
        self.held: dict[str, int] = {}          # button -> absolute frame it is released on
        self.down_at: dict[str, int] = {}
        self.ui_state = boot_state
        self.field_id = -1
        self.player = [0.0, 0.0, 0.0]
        self.control = False
        self.has_position = True
        self.world = {"id": -1, "x": None, "z": None, "vehicle": 0}
        self.texts: list[str] = []
        self.raw_texts: list[str] = []
        self.choice: dict | None = None
        self.menu = {"selected": None, "hovered": None, "label": None, "group": None}
        self.menu_entries: list[str] = []
        self.menu_index = 0
        self.flags: dict[int, bool] = {}
        self.watch: list[int] = []
        self.error: str | None = None
        self.note = ""
        self.shots_taken = 0
        #: The co-op client's observables, at the engine's "nothing" sentinels. The stand-in models
        #: the GATES and the state block -- what each `netsync` verb refuses, what it publishes
        #: afterwards, and that `reset`/disarm release the override -- not the lockstep itself.
        self.netsync: dict = {
            "enabled": False, "role": "host", "instance": False, "selftest": False, "forced": False,
            "bench": False, "l1": False, "l1_pinned": False, "l1_forced_control": False,
            "suppress": False, "align_win": -1, "align_text": -1, "applied_seq": -1,
            "wait_armed": False, "wait_ms": -1, "wait_limit_ms": 8000, "pending": None,
        }
        self._lockstep_seq = 0
        self._wait_since_frame = 0
        self.walkmesh = walkmesh
        #: Frames the character keeps moving after the direction is released. ⚠ NOT ZERO, and the
        #: value is measured rather than chosen: on bench 30801 a hold covers what it commanded give
        #: or take ONE frame (`hold down 1` moves 60 units at run speed, `hold down 31` moves 900),
        #: so the engine's input pipeline runs about a frame behind. A stand-in that stopped dead on
        #: release could not reproduce that at all -- and the pathological case, where the tail lands
        #: inside the NEXT burst's measurement window and is attributed to the direction pressed
        #: there, is what a test raises this to reproduce.
        self.coast_frames = 1
        self._coast = None                  # (vx, vz, frames_left)
        #: Whether the agent has redirected its save path away from the player's folder. Modelled
        #: because the driver must VERIFY this rather than trust it -- an unchecked sandbox is a
        #: check that cannot fail, and what it would fail to catch is the owner's overwritten game.
        self.save_sandboxed = True
        #: `[Control] SoftReset` in Memoria.ini. The ENGINE default is 0; this install has it on.
        #: False here models the install where the recovery ladder's top rung simply does not exist,
        #: which the driver must report honestly rather than hang on.
        self.soft_reset_enabled = True
        self.soft_resets = 0
        # -- battle ----------------------------------------------------------------------------
        #: `party.battle_no`: monotonic, save-persistent, never reset. The ONE unambiguous "a battle
        #: started" edge -- modelled as such because every driver wait is anchored to it.
        self.battle_epoch = 7
        self.battle_active = False
        #: The diorama property that makes a whole class of assertion vacuous: under isDebug the
        #: engine suppresses the auto-end, so the battle CANNOT finish. The driver must refuse to
        #: wait for a result here rather than hang, and this is what lets a test prove it does.
        self.battle_debug = False
        #: btl_result. ⚠ 0 both DURING a battle and BEFORE any has run -- the ambiguity is the point.
        self.battle_result = 0
        self.battle_scene = -1
        self.battle_units: list[dict] = []
        self.battle_bonus = {"exp": 0, "gil": 0, "ap": 0, "items": 0}
        self.battle_commands: list[list[int]] = []
        #: Whose command menu is open -- BattleHUD.CurrentPlayerIndex. -1 between turns.
        self.battle_turn = -1
        self.battle_ready: list[int] = []
        self.battle_done: list[int] = []
        #: The last `menus` collection. ⚠ DELIBERATELY NOT CLEARED BETWEEN BATTLES, like the engine's
        #: own fields: a driver that trusts it without checking the stamp must be able to be caught.
        self.battle_menu: dict = {"slot": -1, "epoch": -1, "commands": [], "abilities": [],
                                  "items": []}
        #: cmd_status bit 0 -- a SysEscape command is queued and the party is leaving.
        self.escaping = False
        #: BattleHUD._runCounter: UNBROKEN real seconds with both bumpers down. Resets to 0 the
        #: instant either lifts, which is the whole reason a re-issued hold used to be fatal.
        self.run_counter = 0.0
        #: The per-roll escape chance, as a fraction. The engine computes it from levels; here it is
        #: a dial so a test can have a flee that always lands AND one that never does.
        self.escape_rate = 1.0
        #: When true the bumpers are held but the battle never sees them -- an input path that is
        #: not connected, as opposed to a roll that has not landed. flee() must tell them apart.
        self.deaf_bumpers = False
        #: btl_scene.Info.Runaway -- whether this scene permits running at all.
        self.scene_runaway = True
        #: ATB gained per frame, per side. ⚠ ZERO BY DEFAULT: a stand-in whose gauges fill on their
        #: own would make every battle test race a clock it did not ask for -- and the enemy would
        #: chew through the party in the middle of an assertion about HP. A test that wants turns
        #: turns them on, which also makes the turn machinery an explicit part of what it tests.
        self.atb_gain = 0
        self.enemy_hit = 90
        #: Frames between committing a command and its RESOLUTION -- when the damage lands and the
        #: slot leaves ready/done and can be asked again (btl_cmd dequeues, then
        #: InputFinishList.Remove). Without this a slot that acted once never acted again and no
        #: fight could be played out. A test that needs the "its turn is spent" refusal pins it
        #: high, so the refusal never races the resolution.
        self.cmd_resolve_frames = 45
        self.battle_pending: list[list] = []
        #: FF9BMenu_IsEnable(): the command phase is live. False through the opening camera and
        #: again once the fight is over -- which is exactly when everything else in the turn block
        #: is holding the LAST battle's contents.
        self.commands_enabled = False
        #: Frames of opening camera before InitialBattle() runs. ⚠ NOT ZERO BY DEFAULT: the stale
        #: window is the whole point, and a stand-in with no intro could not reproduce the freeze
        #: that a stale `turn.slot` caused in a real second battle.
        self.battle_intro_frames = 30
        self._intro_until = 0
        self.gateway: tuple[float, float, float, float, int] | None = None
        #: every op the fake ever executed, so a test can assert a step was DELIVERED rather than
        #: inferring it from a state that several other ops could also have produced.
        self.executed: list[list[str]] = []
        self.arm_transitions = 0

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
            if self.mode != "frozen":
                self.frame += 1
            try:
                self._poll_arm()
                if self.armed:
                    self._poll_request()
                    self._drain()
                    self._check_soft_reset()
                    self._step_world()
                    self._step_battle()
                    self._publish()
            except OSError as err:
                # Mirrors the agent's own try/catch. Without this a single transient sharing
                # violation killed the publisher thread, and every later wait then timed out
                # pointing at the wrong half of the system -- which is exactly how a harness
                # earns a reputation for being flaky when it is actually deterministic.
                self.error = str(err)
            time.sleep(period)

    def _poll_arm(self) -> None:
        """Model the agent's arm gate EXACTLY, including the part that bites.

        ⚠ The real agent compares the file's existence against its own flag and returns early when
        they agree. So rewriting an existing arm file is a no-op: sequence numbers are NOT reset,
        buttons are NOT released, the error latch is NOT cleared. A driver that re-arms by writing
        the file gets an agent still carrying a dead run's counters, and every request it sends is
        discarded as stale while acking instantly. Reproducing that here is the whole point.
        """
        if self.frame - self.arm_poll_frame < ARM_POLL:
            return
        self.arm_poll_frame = self.frame
        present = (self.dir / "arm").exists()
        if present == self.armed:
            return
        self.armed = present
        self.queue.clear()
        self.held.clear()
        self.down_at.clear()
        if present:
            self.arm_transitions += 1
            if self.resets_on_arm:
                self.seq = -1
                self.ack = -1
                self.error_seq = -1
                self.pending_ack = False
                self.block_until = 0
                self.error = None
                self.watch = []
                self.note = ""
            self._event("armed", protocol=PROTOCOL)
        else:
            self._release_netsync()            # the override is process-local: it dies with the run
            self._publish(force=True)          # a final document that says it stood down
            self._event("disarmed")

    def _poll_request(self) -> None:
        every = REQ_POLL_IDLE if not self.queue else REQ_POLL_BUSY
        if self.frame - self.req_poll_frame < every:
            return
        self.req_poll_frame = self.frame
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
        # The FIXED agent clears the error latch per request. Without this one refusal poisons every
        # later step, and the driver blames innocent requests for it.
        self.error = None
        self.pending_ack = True
        for line in lines[1:]:
            tok = line.split()
            if tok and not tok[0].startswith("#"):
                self.queue.append(tok)

    def _drain(self) -> None:
        while self.queue and self.frame >= self.block_until:
            step = self.queue.pop(0)
            self.executed.append(list(step))
            try:
                self._execute(step)
            except Exception as err:                       # mirrors the agent: report, never die
                self.error = f"{step[0]}: {err}"
                self.error_seq = self.seq
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

        def real(i, default=0.0):
            try:
                return float(args[i])
            except (IndexError, ValueError):
                return default

        if op == "wait":
            self._block(num(0, 1))
        elif op == "press":
            self._schedule(args[0], max(1, num(1, 2)))
            self._block(num(1, 2) + 2)
            self._menu_step(args[0])
        elif op == "hold":
            self._extend(args[0], max(1, num(1, 30)))
        elif op == "release":
            self.held.pop(args[0], None)
            self.down_at.pop(args[0], None)
        elif op == "newgame":
            if self.ui_state != "Title":
                raise RuntimeError("newgame: not at the title screen")
            self.ui_state = "FieldHUD"
            self.field_id = 70
            self.control = True
            self._block(3)
        elif op == "warp":
            self.field_id = num(0, -1)
            self.ui_state = "FieldHUD"
            self.control = True
            self.player = [0.0, 0.0, 0.0]
            self._block(3)
        elif op == "battle":
            if self.ui_state != "FieldHUD":
                raise RuntimeError("battle: field only")
            self.start_battle(num(0, -1), group=num(1, -1))
            self._block(3)
        elif op == "battlecmd":
            if not self.battle_active:
                raise RuntimeError("battlecmd: no battle HUD (not in a battle?)")
            self._battle_command(num(0, 0), num(1, 0), num(2, 0), num(3, 0), num(4, 0))
            self._block(2)
        elif op == "menus":
            if not self.battle_active:
                raise RuntimeError("menus: no battle HUD (not in a battle?)")
            self._collect_menus(num(0, -1))
        elif op == "worldwarp":
            if self.ui_state != "WorldHUD":
                raise RuntimeError("world warp: overworld only")
            self.field_id = num(0, -1)
            self.ui_state = "FieldHUD"
            self.control = True
            self._block(3)
        elif op == "teleport":
            if self.ui_state != "WorldHUD":
                raise RuntimeError("teleport: not in world mode")
            self.world["x"], self.world["z"] = real(0), real(1)
        elif op == "control":
            self.control = num(0, 1) != 0
        elif op == "flag":
            bit = num(0, -1)
            if bit < 0:
                raise RuntimeError(f"flag bit {bit} is out of range")
            self.flags[bit] = num(1, 1) != 0
        elif op == "byte":
            pass
        elif op == "watch":
            for a in args:
                try:
                    bit = int(a)
                except ValueError:
                    continue
                if bit < 0:
                    # The FIXED agent rejects this. The unfixed one appended the key and THEN threw,
                    # leaving a truncated document and an unparseable channel for the rest of the run.
                    raise RuntimeError(f"watch bit {bit} is out of range")
                if bit not in self.watch:
                    self.watch.append(bit)
        elif op == "unwatch":
            self.watch = []
        elif op == "reset":
            self.held.clear()
            self.down_at.clear()
            self.watch = []
            self.note = ""
            self.error = None
            self.state_every = 2
            self._release_netsync()
            self._block(2)
        elif op == "timescale":
            if real(0, 1.0) <= 0.0:
                raise RuntimeError("timescale must be positive")
        elif op == "stateevery":
            self.state_every = max(1, num(0, 2))
        elif op == "shot":
            self._write_png(args[0] if args else "shot")
            self._block(2)
        elif op == "note":
            self.note = " ".join(args)
        elif op == "netsync":
            self._netsync(args)
            self._block(2)
        elif op == "quit":
            self.returncode = 0
        else:
            raise RuntimeError(f"unknown op '{op}'")

    def _block(self, frames: int) -> None:
        self.block_until = max(self.block_until, self.frame + max(0, frames))

    def _schedule(self, button: str, frames: int) -> None:
        self.down_at[button] = self.frame + 1
        self.held[button] = self.frame + 1 + frames

    def _extend(self, button: str, frames: int) -> None:
        """Lengthen a hold in progress instead of restarting it (HarnessAgent.Extend).

        ⚠ THE ONE-FRAME HOLE THIS AVOIDS IS NOT COSMETIC. Restarting sets down_at to frame + 1, so
        on the frame the second hold arrives the button reads UP -- invisible to anything sampling
        it, fatal to anything counting unbroken held time. In the real engine that is
        BattleHUD._runCounter, and a flee re-issued every 0.8s therefore never rolled once.
        """
        if self._is_held(button):
            self.held[button] = max(self.held[button], self.frame + frames)
        else:
            self._schedule(button, frames)

    # -- the simulated world -------------------------------------------------------------------
    def _is_held(self, button: str) -> bool:
        return self.down_at.get(button, 1 << 30) <= self.frame < self.held.get(button, -1)

    def _step_world(self) -> None:
        """Move the character for one frame, so the driver's closed-loop verbs actually close.

        The basis is deliberately NOT the identity in every mode: FF9 fields are viewed by a yawed
        camera and movement is expressed in screen space, which is why `calibrate_axes` exists at
        all. A stand-in that always mapped "up" to +z would let a broken calibration pass.
        """
        if self.ui_state != "FieldHUD" or not self.control:
            return
        vx = vz = 0.0
        if self._is_held("up"):
            vz += 1.0
        if self._is_held("down"):
            vz -= 1.0
        if self._is_held("right"):
            vx += 1.0
        if self._is_held("left"):
            vx -= 1.0
        if vx == 0.0 and vz == 0.0:
            # Nothing held -- but the engine is still applying the last movement it sampled.
            if not self._coast:
                return
            vx, vz, left = self._coast
            self._coast = (vx, vz, left - 1) if left > 1 else None
            x = self.player[0] + vx
            z = self.player[2] + vz
            x0, z0, x1, z1 = self.walkmesh
            self.player[0] = min(max(x, x0), x1)
            self.player[2] = min(max(z, z0), z1)
            return
        mag = (vx * vx + vz * vz) ** 0.5
        vx, vz = vx / mag, vz / mag
        if self.twist:
            import math
            a = math.radians(self.twist)
            vx, vz = vx * math.cos(a) - vz * math.sin(a), vx * math.sin(a) + vz * math.cos(a)
        speed = WALK_SPEED if self._is_held("cancel") else RUN_SPEED

        if self.mode == "wall_slide":
            # Every press is projected onto one fixed wall direction. The character always MOVES --
            # which is why a "did it move at all" probe cannot detect this -- but never where he was
            # sent. A basis measured here is a well-formed lie.
            wall = (0.7071, 0.7071)
            along = vx * wall[0] + vz * wall[1]
            vx, vz = wall[0] * along, wall[1] * along
            if vx == 0.0 and vz == 0.0:
                return

        x = self.player[0] + vx * speed
        z = self.player[2] + vz * speed
        x0, z0, x1, z1 = self.walkmesh
        self.player[0] = min(max(x, x0), x1)
        self.player[2] = min(max(z, z0), z1)
        # Arm the tail with the velocity actually applied this frame.
        self._coast = ((vx * speed, vz * speed, self.coast_frames)
                       if self.coast_frames > 0 else None)

        if self.gateway is not None:
            gx0, gz0, gx1, gz1, dest = self.gateway
            if gx0 <= self.player[0] <= gx1 and gz0 <= self.player[2] <= gz1:
                self.field_id = dest
                self.player = [0.0, 0.0, 0.0]
                self.control = True

    def _check_soft_reset(self) -> None:
        """All six buttons reporting a DOWN EDGE on the same frame sends the game to the title.

        The real handler closes every dialog, hides the HUD, disables all button groups and the
        battle menu, un-pauses, normalises btl_seq and replaces the scene with Title -- which is why
        it is the only recovery rung that reaches a battle or a stuck menu. What matters for the
        driver is the observable end state, so that is what this models.
        """
        if not self.soft_reset_enabled:
            return
        if not all(self.down_at.get(b) == self.frame for b in SOFT_RESET_COMBO):
            return
        # ⚠ A MENU SWALLOWS THE COMBO, and the stand-in has to swallow it too. `UIKeyTrigger.Update`
        # runs `if (HandleMenuControlKeyPressCustomInput()) return;` before the soft-reset check, and
        # that handler consumes Control.Select unconditionally. MEASURED in-game
        # (scenarios/soft_reset_reach.py): from a field YES, from an open MainMenu NO. A stand-in
        # more forgiving than the engine is worse than none -- it certifies a ladder that cannot
        # actually climb.
        if self.ui_state not in ("FieldHUD", "WorldHUD"):
            return
        self.soft_resets += 1
        self.ui_state = "Title"
        self.field_id = -1
        self.control = False
        self.texts = []
        self.raw_texts = []
        self.choice = None
        self.menu = {"selected": None, "hovered": None, "label": None, "group": None}
        self.menu_entries = []
        self.player = [0.0, 0.0, 0.0]
        # ⚠ NOT held.clear(). FF9's handler does not release the player's buttons, and a stand-in
        # that did would make `reset_agent` -- the thing that actually releases them -- untestable:
        # it could be reduced to a no-op with every test still green.
        self._event("soft_reset")

    def _menu_step(self, button: str) -> None:
        # Cancel backs a screen OUT. Modelled because the close-UI recovery rung is built on it: the
        # soft-reset combo is swallowed inside a menu, so Cancel is the only way out of one, and a
        # stand-in whose menus could not be left would certify a ladder that cannot climb.
        if button in ("cancel", "back", "b") and self.ui_state == "MainMenu":
            self.ui_state = "FieldHUD"
            self.menu_entries = []
            self.menu = {"selected": None, "hovered": None, "label": None, "group": None}
            self.control = True
            return
        if not self.menu_entries:
            return
        if button == "down":
            self.menu_index = (self.menu_index + 1) % len(self.menu_entries)
        elif button == "up":
            self.menu_index = (self.menu_index - 1) % len(self.menu_entries)
        elif button in ("confirm", "ok") and self.choice is not None:
            self.choice = None
            return
        self.menu["label"] = self.menu_entries[self.menu_index]
        self.menu["selected"] = f"Button{self.menu_index}"
        if self.choice is not None:
            self.choice["selected"] = self.menu_index

    # -- publication ---------------------------------------------------------------------------
    def _publish(self, force: bool = False) -> None:
        if not force and self.frame - self.publish_frame < self.state_every:
            return
        self.publish_frame = self.frame
        held = [b for b in self.held if self._is_held(b)]
        px, py, pz = self.player
        if not self.has_position:
            px = py = pz = None
        doc = {
            "v": PROTOCOL if self.protocol is None else self.protocol, "frame": self.frame, "seq": self.seq, "ack": self.ack,
            "queue": len(self.queue),
            "busy": bool(self.queue) or self.frame < self.block_until,
            "armed": self.armed,
            "shots": self.shots_taken, "timescale": 1.0, "note": self.note,
            "error": self.error, "error_seq": self.error_seq,
            "debug_status": None,
            "save_path": str(self.dir / "save" / "SavedData_ww.dat"),
            "save_sandboxed": self.save_sandboxed,
            "ui_state": self.ui_state, "scene": "FieldMap", "fading": False,
            "sys_mode": 1, "scenario": 0,
            "field": {"id": self.field_id, "name": f"FBG_FAKE_{self.field_id}"},
            "world": dict(self.world),
            "player": {"x": px, "y": py, "z": pz,
                       "dir": 0, "floor": 0, "tri": 0, "control": self.control},
            "input": {"key_up": self._is_held("up"), "key_confirm": self._is_held("confirm"),
                      "move_key": bool(held), "dash_inh": 0, "axis_x": 0.0, "axis_y": 0.0},
            "dialog": {"open": bool(self.texts) or self.choice is not None,
                       "count": len(self.texts),
                       "texts": self.texts, "phrase_raw": self.raw_texts or self.texts,
                       "choice": self.choice},
            "menu": dict(self.menu),
            "battle": self._battle_doc(),
            "flags": {str(b): bool(self.flags.get(b, False)) for b in self.watch},
            "netsync": self._netsync_doc(),
            "held": held,
        }
        _publish_atomic(self.dir / "state.json", json.dumps(doc))

    def _event(self, kind: str, **kv) -> None:
        row = {"frame": self.frame, "kind": kind}
        row.update({k: str(v) for k, v in kv.items()})
        try:
            with (self.dir / "events.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row) + "\n")
        except OSError:
            pass

    def _write_png(self, name: str) -> None:
        """A real PNG -- the driver decodes it to check the frame is not uniformly blank."""
        safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in name) or "shot"
        # 4x1 with four different colours, so a "not a blank screen" check has something to find.
        rows = b"\x00" + bytes(range(12))
        png = (b"\x89PNG\r\n\x1a\n"
               + _chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 1, 8, 2, 0, 0, 0))
               + _chunk(b"IDAT", zlib.compress(rows))
               + _chunk(b"IEND", b""))
        (self.shots / f"{safe}.png").write_bytes(png)
        self.shots_taken += 1
        self._event("shot", name=name)

    # -- battle --------------------------------------------------------------------------------
    def _battle_doc(self) -> dict:
        # Outside a battle only the three cheap facts are published, exactly as the agent does --
        # because every OTHER value in FF9Battle is STALE rather than absent afterwards, and
        # publishing them on a field would hand a scenario a plausible, entirely historical battle.
        # `result`, `scene` and `bonus` ride alongside `epoch` and are published ALWAYS: they are
        # what a scenario needs AFTER the fight, and the epoch is what says which fight they belong
        # to. Everything below them is a mid-battle concept the engine leaves holding the previous
        # battle's contents, so publishing it on a field would be a plausible historical lie.
        doc = {"active": self.battle_active, "epoch": self.battle_epoch, "debug": self.battle_debug,
               "result": self.battle_result, "scene": self.battle_scene,
               "bonus": dict(self.battle_bonus)}
        if not self.battle_active:
            return doc
        doc.update({
            "phase": 4,
            # ⚠ escape_held says the BUMPERS ARE DOWN and nothing more -- it is set before every
            # gate. `escaping` is the queued SysEscape, i.e. the roll actually landed. A stand-in
            # that conflated them could not catch a driver that waits on the wrong one.
            "escape_held": 0 if self.deaf_bumpers else
                           (1 if (self._is_held("l1") and self._is_held("r1")) else 0),
            "escaping": self.escaping,
            # ⚠ btl_scene.Info. `runaway` false means CheckEscape shows "Cannot escape!" and NEVER
            # rolls -- while btl_escape_key still runs the animation. Modelled because the driver
            # refuses that scene up front, and an unmodelled block makes that a guard nothing fires.
            "scene_info": {"runaway": self.scene_runaway, "no_gameover": False,
                           "preemptive": False, "back_attack": False},
            # ⚠ GATED, exactly as the agent publishes it. `slot_raw` is the ungated value, which
            # during the intro is the PREVIOUS battle's -- and acting on it froze a real fight.
            "turn": {"enabled": self.commands_enabled,
                     "slot": self.battle_turn if self.commands_enabled else -1,
                     "slot_raw": self.battle_turn,
                     "ready": list(self.battle_ready) if self.commands_enabled else [],
                     "done": list(self.battle_done) if self.commands_enabled else []},
            "menu": dict(self.battle_menu),
            "units": [dict(u) for u in self.battle_units],
        })
        return doc

    def start_battle(self, scene: int, *, group: int = -1, debug: bool = False,
                     units: list[dict] | None = None) -> None:
        """Stand a battle up, advancing the epoch the way battle.InitBattle does."""
        self.battle_epoch += 1
        self.battle_active = True
        self.battle_debug = debug
        self.battle_result = 0                    # reset at START, which is why 0 is ambiguous
        self.battle_scene = scene
        self.ui_state = "BattleHUD"
        self.battle_bonus = {"exp": 0, "gil": 0, "ap": 0, "items": 0}
        # ⚠ battle_turn / ready / done are deliberately NOT cleared here. In the engine they are
        # reset by BattleHUD.InitialBattle(), which runs LATER than the battle scene goes live --
        # so through the opening camera they still hold the PREVIOUS fight's contents. That window
        # is what published a plausible "your move" for a battle that was not asking, and a
        # stand-in that tidied up here could not reproduce it. _step_battle clears them when the
        # intro ends, which is where the engine clears them too.
        self.commands_enabled = False
        self._intro_until = self.frame + self.battle_intro_frames
        self.battle_pending = []
        self.escaping = False
        self.run_counter = 0.0
        # ⚠ battle_menu is deliberately NOT cleared here either, for the same reason: a driver that
        # reads the menu without checking its epoch stamp has to be catchable.
        self.battle_units = units if units is not None else [
            # hp/hp_max are the LOGICAL values the HUD shows; hp_raw/hp_max_raw are cur.hp/max.hp,
            # what the AI reads as B_MEMBER (36)/(35). The enemy below carries the 10000 offset a
            # FLG_NON_DYING_BOSS gets under CustomBattleFlagsMeaning=1, so a test asserting on "the"
            # HP has to choose -- which is the whole reason both are published.
            {"slot": 0, "id": 1, "player": True, "name": "Zidane", "hp": 420, "hp_max": 600,
             "hp_raw": 420, "hp_max_raw": 600, "mp": 30, "mp_max": 40, "atb": 0, "atb_max": 6000,
             "can_act": True, "alive": True, "targetable": True, "level": 5, "status": "0"},
            {"slot": 1, "id": 2, "player": True, "name": "Vivi", "hp": 0, "hp_max": 380,
             "hp_raw": 0, "hp_max_raw": 380, "mp": 12, "mp_max": 20, "atb": 0, "atb_max": 6000,
             "can_act": False, "alive": True, "targetable": True, "level": 4, "status": "0"},
            {"slot": 4, "id": 16, "player": False, "name": "Masked Man", "hp": 1200,
             "hp_max": 1200, "hp_raw": 11200, "hp_max_raw": 11200, "mp": 0, "mp_max": 0,
             "atb": 3000, "atb_max": 6000, "can_act": True, "alive": True, "targetable": True,
             "level": 9, "status": "0"},
        ]

    #: What the stand-in's party can do. Shapes and TRAPS, not real FF9 ids: an Ability command
    #: that is a sub-menu rather than a move (type 1), an ability that is learned but not castable
    #: (enabled false), an item that targets the dead, and a command the HUD would not draw
    #: (offered false) -- each of which the driver has to refuse for its own distinct reason.
    MENU_COMMANDS = [
        {"menu": 0, "id": 1, "type": 0, "target": 2, "for_dead": False, "sub": 176,
         "offered": True, "name": "Attack"},
        {"menu": 1, "id": 2, "type": 4, "target": -1, "for_dead": False, "sub": 177,
         "offered": True, "name": "Defend"},
        {"menu": 2, "id": 4, "type": 1, "target": -1, "for_dead": False, "sub": 0,
         "offered": True, "name": "Blk Mag"},
        {"menu": 3, "id": 5, "type": 1, "target": -1, "for_dead": False, "sub": 0,
         "offered": False, "name": "Swd Art"},
        {"menu": 4, "id": 8, "type": 2, "target": -1, "for_dead": False, "sub": 0,
         "offered": True, "name": "Item"},
    ]
    MENU_ABILITIES = [
        {"menu": 2, "sub": 20, "mp": 6, "enabled": True, "target": 2, "for_dead": False,
         "name": "Fire"},
        {"menu": 2, "sub": 21, "mp": 6, "enabled": False, "target": 2, "for_dead": False,
         "name": "Blizzard"},
        # TargetType.AllEnemy: the engine's cursor for this is the GROUP, so a single target id
        # would be a command the UI could never have produced.
        {"menu": 2, "sub": 22, "mp": 18, "enabled": True, "target": 8, "for_dead": False,
         "name": "Meteor"},
    ]
    MENU_ITEMS = [
        {"sub": 1, "count": 9, "target": 1, "for_dead": False, "name": "Potion"},
        {"sub": 2, "count": 2, "target": 1, "for_dead": True, "name": "Phoenix Down"},
    ]

    def _collect_menus(self, slot: int) -> None:
        """The `menus` verb: refuse what the engine refuses, then stamp what it collected."""
        if not self.commands_enabled:
            raise RuntimeError("menus: the battle is not asking for commands yet")
        if slot < 0 or slot >= 32:
            raise RuntimeError("menus needs a party slot (0-31)")
        unit = next((u for u in self.battle_units if u["slot"] == slot), None)
        # ⚠ CollectNetMenus indexes _abilityDetailDict unguarded, so a slot with no party member --
        # or one asked during the battle intro -- throws in the engine. Modelled as the refusal the
        # agent turns it into, because a scenario has to be able to hit it.
        if unit is None or not unit.get("player"):
            raise RuntimeError(f"menus: slot {slot} has no ability detail yet")
        self.battle_menu = {
            "slot": slot, "epoch": self.battle_epoch,
            "commands": [dict(c) for c in self.MENU_COMMANDS],
            "abilities": [dict(a) for a in self.MENU_ABILITIES],
            "items": [dict(i) for i in self.MENU_ITEMS],
        }

    def _battle_command(self, slot: int, cmd: int, sub: int, tar_id: int, cursor: int) -> None:
        """Commit a command for a slot -- with the engine's own refusals, then its effect.

        ⚠ THE REFUSALS ARE THE POINT. SendNetCommand returns false for an enemy slot and for a slot
        whose turn is already spent, and a stand-in that accepted everything would let a driver bug
        through that the real engine rejects. What it does NOT model is the local-slot refusal:
        that one the agent now dissolves with SetIdle() before calling, so from here the slot is
        already free.
        """
        # ⚠ The guard that would have saved a frozen fight: a command queued on a battle still in
        # its opening camera wedges it solid -- no HUD, no ATB, the intro camera held indefinitely.
        if not self.commands_enabled:
            raise RuntimeError("battlecmd: the battle is not asking for commands yet")
        unit = next((u for u in self.battle_units if u["slot"] == slot), None)
        if unit is None:
            raise RuntimeError(f"battlecmd: the HUD refused the command for slot {slot} -- "
                               f"there is no unit in slot {slot}")
        if not unit.get("player"):
            raise RuntimeError(f"battlecmd: the HUD refused the command for slot {slot} -- "
                               f"slot {slot} is an ENEMY; only party slots take commands")
        if slot in self.battle_done:
            raise RuntimeError(f"battlecmd: the HUD refused the command for slot {slot} -- "
                               f"a command is already in flight for this slot")
        self.battle_commands.append([slot, cmd, sub, tar_id, cursor])
        self.battle_done.append(slot)
        if self.battle_turn == slot:
            self.battle_turn = -1           # SetIdle: the HUD stops asking
        unit["atb"] = 0
        self.battle_pending.append([self.frame + self.cmd_resolve_frames, slot, cmd, tar_id])

    def _resolve_commands(self) -> None:
        """Execute the commands whose time has come, then hand their slots back.

        The delay is not decoration: between committing and resolving, the slot sits in
        InputFinishList and the engine REFUSES a second command for it. Collapsing the two would
        make the stand-in accept something the real game rejects.
        """
        for entry in [e for e in self.battle_pending if e[0] <= self.frame]:
            self.battle_pending.remove(entry)
            _, slot, cmd, tar_id = entry
            # Only Attack and Fire do damage here; Defend and items resolve harmlessly. That is
            # enough for a fight to actually END, which is what makes fight() testable at all.
            if cmd in (1, 4):
                damage = 260 if cmd == 1 else 400
                for target in self.battle_units:
                    if tar_id & target["id"] and target["alive"]:
                        target["hp"] = max(0, target["hp"] - damage)
                        target["hp_raw"] = max(0, target["hp_raw"] - damage)
                        if target["hp"] == 0:
                            target["alive"] = False
                            target["targetable"] = False
            if slot in self.battle_done:
                self.battle_done.remove(slot)
            if slot in self.battle_ready:
                self.battle_ready.remove(slot)
        self._settle_battle()

    def _settle_battle(self) -> None:
        """End the fight when one side is gone. ⚠ Never under isDebug -- the diorama cannot end."""
        if not self.battle_active or self.battle_debug:
            return
        if not [u for u in self.battle_units if not u["player"] and u["alive"]]:
            self.end_battle(1)
        elif not [u for u in self.battle_units if u["player"] and u["alive"]]:
            self.end_battle(3)

    def _step_battle(self) -> None:
        """One frame of battle: gauges fill, the HUD asks somebody, enemies act, escapes roll."""
        if not self.battle_active:
            return

        # InitialBattle(): the opening camera ends, the HUD resets its turn bookkeeping, and only
        # THEN does the battle start asking for commands.
        if not self.commands_enabled and self.frame >= self._intro_until:
            self.battle_turn = -1
            self.battle_ready = []
            self.battle_done = []
            self.commands_enabled = True
        # ⚠ NOTHING RUNS DURING THE INTRO -- not the gauges, not the enemies, not the escape roll.
        # battle.cs gates BattleMainLoop on btl_phase, and BattleHUD.Update returns early while
        # _commandEnable is false, so the bumpers cannot even set btl_escape_key there. A stand-in
        # that ran combat through its own intro would let the party die before the fight began.
        if not self.commands_enabled:
            return

        # -- the escape roll. _runCounter counts UNBROKEN real seconds; either bumper lifting
        # resets it to zero, which is the defect class this whole model exists to preserve.
        if not self.deaf_bumpers and self._is_held("l1") and self._is_held("r1"):
            self.run_counter += 1.0 / self.fps
            if self.run_counter > 1.0:
                self.run_counter = 0.0
                if self._roll() < self.escape_rate:
                    self.escaping = True
        else:
            self.run_counter = 0.0
        if self.escaping:
            self.end_battle(4)
            self.escaping = False
            return

        self._resolve_commands()
        if not self.battle_active:
            return
        # A character who goes down mid-prompt stops being asked -- the HUD's own
        # _unconsciousStateList / RemovePlayerFromAction. Without this the turn would stay pinned
        # to a corpse and every later wait would time out against it.
        if self.battle_turn >= 0:
            asked = next((u for u in self.battle_units if u["slot"] == self.battle_turn), None)
            if asked is None or not asked["alive"]:
                self.battle_turn = -1

        for unit in self.battle_units:
            if not unit["alive"]:
                continue
            unit["atb"] = min(unit["atb_max"], unit["atb"] + self.atb_gain)
            ready = unit["atb"] >= unit["atb_max"]
            if unit["player"]:
                if ready and unit["slot"] not in self.battle_ready \
                        and unit["slot"] not in self.battle_done and unit.get("can_act", True):
                    self.battle_ready.append(unit["slot"])
            elif ready:
                unit["atb"] = 0
                victim = next((u for u in self.battle_units if u["player"] and u["alive"]), None)
                if victim is not None:
                    victim["hp"] = max(0, victim["hp"] - self.enemy_hit)
                    victim["hp_raw"] = max(0, victim["hp_raw"] - self.enemy_hit)
                    if victim["hp"] == 0:
                        victim["alive"] = False

        # The HUD asks the first ready slot that has not answered -- BattleHUD.UpdatePlayer.
        if self.battle_turn < 0:
            for slot in list(self.battle_ready):
                if slot not in self.battle_done:
                    self.battle_turn = slot
                    break
        self._settle_battle()

    def _roll(self) -> float:
        """A deterministic pseudo-roll, so a suite does not depend on the clock."""
        self._roll_state = (getattr(self, "_roll_state", 12345) * 1103515245 + 12345) & 0x7FFFFFFF
        return self._roll_state / float(0x7FFFFFFF)

    def end_battle(self, result: int = 1, *, exp: int = 120, gil: int = 88) -> None:
        """Finish the battle. ⚠ Refuses under isDebug, exactly as the engine's auto-end does."""
        if self.battle_debug:
            return
        self.battle_result = result
        self.battle_bonus = {"exp": exp, "gil": gil, "ap": 3, "items": 1}
        self.battle_active = False
        # ⚠ commands_enabled goes false at PHASE_MENU_OFF, but battle_turn does NOT get cleared --
        # the engine leaves it for InitialBattle. That is the stale value the next battle inherits.
        self.commands_enabled = False
        self.ui_state = "FieldHUD"

    # -- test conveniences ---------------------------------------------------------------------
    # -- co-op (netsync) benches ---------------------------------------------------------------
    def _netsync(self, args: list[str]) -> None:
        """The agent's `netsync` verb: the same gates, the same refusal texts, the same state."""
        sub = args[0].lower() if args else ""
        ns = self.netsync
        flag = (args[1] if len(args) > 1 else "1") != "0"
        if sub == "selftest":
            if flag:
                if ns["enabled"] and ns["role"] != "selftest":
                    raise RuntimeError(f"netsync selftest: co-op is configured live (role={ns['role']}) "
                                       f"-- refusing to override a real session")
                ns.update(enabled=True, role="selftest", instance=True, selftest=True, forced=True)
            else:
                self._release_netsync()
        elif sub in ("bench", "l1"):
            if not ns["selftest"]:
                raise RuntimeError(f"netsync {sub}: needs the selftest role (netsync selftest 1)")
            ns[sub] = flag
            if sub == "l1" and not flag:
                ns["l1_pinned"] = False
                ns["l1_forced_control"] = False
        elif sub in ("advance", "choice", "unmatched"):
            if sub != "unmatched" and not (self.texts or self.choice is not None):
                raise RuntimeError(f"netsync {sub}: no dialogue window is open")
            if not ns["instance"]:
                raise RuntimeError("netsync: no co-op client in this process (netsync selftest 1 first)")
            if not ns["selftest"]:
                raise RuntimeError(f"netsync: role is '{ns['role']}' -- the dialog bench needs the selftest role")
            if not ns["bench"]:
                raise RuntimeError("netsync: the field-gate bench is OFF (netsync bench 1)")
            if not ns["l1"]:
                raise RuntimeError("netsync: the L1 host-event flag is OFF (netsync l1 1) -- L2 engages only under L1")
            seq = self._lockstep_seq
            self._lockstep_seq = (seq + 1) & 0xFF
            if sub == "unmatched":
                ns["pending"] = {"field": self.field_id, "win": 15, "text": 0xFFFF,
                                 "kind": 0, "index": 0xFF, "seq": seq}
                ns["wait_armed"] = True
                self._wait_since_frame = self.frame
                return
            if sub == "choice":
                idx = int(args[1]) if len(args) > 1 else -1
                if idx < 0:
                    raise RuntimeError("netsync choice: needs a choice index")
                self.choice = None
                self.menu_entries = []
            # MATCHED: the engine drives the window's own OnKeyConfirm -- one page turns, the frame
            # is consumed, and with the window closed nothing is left under lockstep.
            if self.texts:
                self.texts = self.texts[1:]
                self.raw_texts = self.raw_texts[1:] if self.raw_texts else []
            ns.update(applied_seq=seq, pending=None, suppress=False, align_win=-1, align_text=-1)
        elif sub == "talk":
            # F3.1: the guest-side replay of a host's press-fired talk, by object uid (solo bench).
            if not ns["instance"]:
                raise RuntimeError("netsync talk: no co-op client in this process (netsync selftest 1 first)")
            if not ns["selftest"]:
                raise RuntimeError(f"netsync talk: role is '{ns['role']}' -- the bench needs the selftest role")
            if not ns["bench"]:
                raise RuntimeError("netsync talk: the field-gate bench is OFF (netsync bench 1)")
            uid = int(args[1]) if len(args) > 1 else -1
            if not 0 <= uid <= 0xFFFF:
                raise RuntimeError(f"netsync talk: uid {uid} is outside 0..65535")
            ns["last_talk_uid"] = uid
        else:
            raise RuntimeError(f"netsync: unknown sub-verb '{sub}' (selftest|bench|l1|advance|choice|unmatched|talk)")

    def _release_netsync(self) -> None:
        ns = self.netsync
        if not ns["forced"]:
            return                      # a session the harness did not force is left alone
        ns.update(enabled=False, role="selftest", instance=True, selftest=False, forced=False,
                  bench=False, l1=False, l1_pinned=False, l1_forced_control=False, suppress=False,
                  align_win=-1, align_text=-1, applied_seq=-1, wait_armed=False, wait_ms=-1,
                  pending=None)

    def _netsync_doc(self) -> dict:
        ns = self.netsync
        if ns["wait_armed"]:
            ns["wait_ms"] = int((self.frame - self._wait_since_frame) * 1000 / self.fps)
            if ns["wait_ms"] > ns["wait_limit_ms"]:
                ns.update(pending=None, wait_armed=False, wait_ms=-1)
        return dict(ns, pending=None if ns["pending"] is None else dict(ns["pending"]))

    def say(self, *pages: str, raw: str | None = None) -> None:
        """Put a dialogue box on screen. ``raw`` models the untagged SOURCE the engine also carries."""
        self.texts = list(pages)
        self.raw_texts = [raw] if raw else list(pages)

    def offer(self, options: list[str], *, header: str = "What now?",
              active: list[int] | None = None) -> None:
        """Open a choice dialogue. ``active`` models the absolute indexes of the ENABLED lines."""
        self.menu_entries = list(options)
        self.menu_index = 0
        self.choice = {"selected": 0, "count": len(options) if active is None else len(active),
                       "options": [header, *options]}
        if active is not None:
            self.choice["active"] = list(active)
        self.menu["label"] = options[0] if options else None

    def open_menu(self, entries: list[str], group: str = "MainMenu") -> None:
        self.ui_state = "MainMenu"
        self.menu_entries = list(entries)
        self.menu_index = 0
        self.menu = {"selected": "Button0", "hovered": None,
                     "label": entries[0] if entries else None, "group": group}


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
