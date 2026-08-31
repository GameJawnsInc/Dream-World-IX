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

#: Must match the DRIVER's protocol: this stand-in models the agent AS SPECIFIED, and
#: publishing an older version would make every offline run exercise the DEGRADED path instead
#: of the real one -- a suite permanently in a compatibility mode it is not meant to be testing.
PROTOCOL = 3

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
        self.walkmesh = walkmesh
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
            self._schedule(args[0], max(1, num(1, 30)))
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
            self.battle_commands.append([num(i, 0) for i in range(5)])
            self._block(2)
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
        elif op == "quit":
            self.returncode = 0
        else:
            raise RuntimeError(f"unknown op '{op}'")

    def _block(self, frames: int) -> None:
        self.block_until = max(self.block_until, self.frame + max(0, frames))

    def _schedule(self, button: str, frames: int) -> None:
        self.down_at[button] = self.frame + 1
        self.held[button] = self.frame + 1 + frames

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
            "v": PROTOCOL, "frame": self.frame, "seq": self.seq, "ack": self.ack,
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
            "escape_held": 0,
            "turn": {"slot": -1, "ready": [], "done": []},
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

    def end_battle(self, result: int = 1, *, exp: int = 120, gil: int = 88) -> None:
        """Finish the battle. ⚠ Refuses under isDebug, exactly as the engine's auto-end does."""
        if self.battle_debug:
            return
        self.battle_result = result
        self.battle_bonus = {"exp": exp, "gil": gil, "ap": 3, "items": 1}
        self.battle_active = False
        self.ui_state = "FieldHUD"

    # -- test conveniences ---------------------------------------------------------------------
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
