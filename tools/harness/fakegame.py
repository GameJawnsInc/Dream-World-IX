#!/usr/bin/env python3
"""A protocol stand-in for the in-game agent, so the driver can be tested with no game running.

WHAT THIS PROVES, AND WHAT IT DOES NOT. It implements the s83 wire protocol -- sequence handling,
the arm transition, frame-stepped queue draining, state publication, screenshots -- plus just enough
of a world (a rectangular walkmesh, the engine's 30 Hz field ticks behind a VIRTUAL render rate -- one MovePC call a
tick walking, two running -- a gateway, a dialogue box, a menu cursor, a body
standing in the way and the engine's walk-through-by-insisting, the field's actors published as s89's
``objects`` -- walkers and contact triggers included -- a freeze with control held, stock's door facing
gate, and s90's published facing with its in-place ``turn``) for the
driver's closed-loop verbs to actually close their loops. A green run against it says the DRIVER is
correct: seq numbers advance, acks belong to the request that earned them, torn reads are survived,
timeouts fire, bad bases are rejected, artifacts land.

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
import math
import os
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
from .channel import BUTTONS, DIRECTIONS, PROTOCOL
from .tickrate import CALLS_PER_TICK, DEFAULT_FIELD_TPS, MAX_DELTA_TIME, TickAccumulator

#: The real agent polls req.txt every 2 frames while idle and every 10 while a queue is running, and
#: the arm file every 30. Modelled because the driver's "do not overwrite an unaccepted request" gate
#: only means anything against a reader that is not instantaneous.
REQ_POLL_IDLE = 2
REQ_POLL_BUSY = 10
ARM_POLL = 30

#: ``[Graphics] FieldTPS``: the field ticks a second this stand-in runs (times `fast_forward`) -- the engine's
#: default and this install's (harness.tickrate.DEFAULT_FIELD_TPS, the one literal).
FIELD_TPS = DEFAULT_FIELD_TPS

#: The field ticks one frame of the fake's CALIBRATED model holds -- 60 fps, 30 Hz: half a tick. The unit a walker's
#: ``speed`` is given in (units a frame at 60 fps, so ``speed / WALKER_FRAME_TICKS`` a tick), which every walk written
#: before the tick model was written against.
WALKER_FRAME_TICKS = 0.5

#: SCollTimer after a push-out, in field ticks: the engine counts it down once a tick (ProcessEvents), and the push lock
#: counts only while it runs (see `_lock_fallback`). Four frames at 60 fps -- what the fake counted before ticks.
COLL_TICKS = 2.0

#: How the fake turns frames into field ticks (`FakeGame(ticks=...)`): "mean" -- every frame holds its AVERAGE,
#: ``tick_hz / render_fps`` (half a tick at 60 fps: smooth, what every walk written before this was written against);
#: "quantized" -- the engine's WHOLE ticks, FPSManager's accumulator (harness.tickrate.TickAccumulator): 0, 1 or more a
#: frame, in a phase nobody publishes.
TICK_MODES = ("mean", "quantized")

#: The clocks the fake can publish (`FakeGame(publish=...)`): "rt" -- the virtual realtime clock, seconds (a future
#: engine's ``Time.realtimeSinceStartup``); "ticks" -- the field ticks run so far (the s91 counter, a float in mean
#: mode); "mtime" -- no key: state.json's MODIFIED TIME is stamped with the virtual write time instead, and the loop
#: runs in real time (see `publish`), so the driver's mtime path measures the render rate.
PUBLISHED_CLOCKS = ("rt", "ticks", "mtime")

#: The most frames one ``turn`` may hold its keys (HarnessAgent.TurnMaxFrames; its ``frames`` is clamped to
#: 1..this, 30 when not given).
TURN_MAX_FRAMES = 36000
#: Memoria.ini ``[AnalogControl] StickThreshold`` (default 10, in hundredths: Configuration/Access/Control.cs:10):
#: the |axis| over which MovePC's axis branch walks him -- a `turn` is refused, or cut, over it.
STICK_THRESHOLD = 0.10

#: FF9's own soft reset: L1+R1+L2+R2+Start+Select, all reporting IsInputDown on ONE frame.
#: Modelled with the same-frame requirement intact, because that requirement is the whole reason the
#: driver has to send all six in a single request -- six separate presses would never overlap, and a
#: stand-in that accepted them sequentially would let a broken driver pass.
SOFT_RESET_COMBO = ("l1", "l2", "r1", "r2", "start", "select")
#: The UI states the ENGINE's soft-reset combo fires in: it is held through ``UIKeyTrigger.GetKey``, which answers
#: false outside these four (UIKeyTrigger.cs:94; research/o3_design.md 0.2 #9). `FakeGame.soft_reset_ui` defaults to
#: the narrower pair every test before H9 was written against; a test that models the engine passes this.
SOFT_RESET_ENGINE_UI = ("FieldHUD", "WorldHUD", "BattleHUD", "QuadMistBattle")
#: H9's movie skip dialog, as the ENGINE answers it -- the dialog's text aside (a test may stage any text in its slot):
#: FieldHUD.OnKeyConfirm puts the cursor on No (``ETb.sChoose = 1``, FieldHUD.cs:280) before it attaches the dialog,
#: whatever the dialog says, and OnKeyConfirmAfterDialogHidden skips on choice 0 ALONE (:430-433); any other answer
#: re-arms the hit area and the movie resumes (:434-440). Absolute indexes, never the fixture's: a skip ``default``
#: other than the cursor is refused when the scene is built (:meth:`FakeGame.scene`), so a fixture cannot flip the
#: sign of the skip.
SKIP_CURSOR = 1
SKIP_CHOICE = 0


class FakeGame:
    """Runs the agent's side of the protocol in a background thread at a simulated frame rate.

    Two rates, never one: the LOOP turns frames at `fps` a wall second (a test's speed), and each frame is one frame of
    a game rendering at `render_fps` on a virtual clock -- whose seconds become the engine's field ticks (`tick_mode`,
    `fast_forward`), and whose clocks the driver can time it by (`publish`). See "the clock" below."""

    def __init__(self, game_path: Path, *, fps: float = 240.0, boot_state: str = "Title",
                 mode: str = "normal", walkmesh=(-600.0, -600.0, 600.0, 600.0),
                 resets_on_arm: bool = True, twist: float = 0.0, render_fps: float = 60.0,
                 ticks: str = "mean", hitches: dict | None = None, publish=("rt",)):
        self.game_path = Path(game_path)
        self.dir = self.game_path / "x64" / "ff9harness"
        self.shots = self.dir / "shots"
        #: How fast the frame LOOP runs, in WALL-clock frames a second -- NOT a render rate: every frame is one
        #: `render_fps` frame of the virtual clock, however fast the loop turns it (240 by default, so a suite spends
        #: a quarter of the wall time a 60 fps game would). `FakeGame(fps=30)` tests nothing about 30 fps; set
        #: `render_fps`. (With "mtime" published the loop runs in real time at `render_fps` and ignores this.)
        self.fps = fps
        # -- the clock (see harness.tickrate): a VIRTUAL clock, frames -> seconds -> field ticks ----------------------
        if ticks not in TICK_MODES:
            raise ValueError(f"ticks must be one of {TICK_MODES}, not {ticks!r}")
        publish = tuple(publish)
        if any(p not in PUBLISHED_CLOCKS for p in publish):
            raise ValueError(f"publish takes only {PUBLISHED_CLOCKS}, not {publish!r}")
        #: FastForwardFactor (the F1 speed-mode cheat: Memoria.ini [Cheats] SpeedFactor): field ticks a second are
        #: FIELD_TPS x this (FPSManager.cs:95-97), and the engine publishes it nowhere -- a driver sees it only as
        #: movement that outruns its rate. 1 = off.
        self.fast_forward = 1.0
        self._tick_mode = ticks
        self._render_fps = self._positive_fps(render_fps)
        #: The clocks published (`PUBLISHED_CLOCKS`). The default, ``("rt",)``, lets the driver's TickClock time the
        #: fake by its VIRTUAL clock whatever the loop's pace; ``()`` publishes none, so the driver falls back on
        #: state.json's real mtime -- which follows the LOOP (`fps`), not `render_fps`, and only approximately
        #: (sleep overshoot); ``("mtime",)`` makes that path exact: the loop paces itself in real time on the virtual
        #: clock and stamps each state.json with its virtual write time, so the file's mtime IS the render clock.
        self.publish = publish
        #: Extra VIRTUAL seconds a frame takes, by frame number (``{frame: seconds}``): a hitch -- the frame runs the
        #: ticks those seconds hold on top of its own (the engine catches a long frame up in the next frame's
        #: ticks, FPSManager.cs:94-99, at most ~10: `MAX_DELTA_TIME`). :meth:`hitch` adds one to the next frame.
        self._hitches: dict[int, float] = {int(k): float(v) for k, v in (hitches or {}).items()}
        self.rt = 0.0                              # the virtual clock, seconds since the first frame
        self._rt_anchor, self._rt_frames = 0.0, 0  # rt = anchor + frames / render_fps (exact: no drift to add)
        self.ticks_run = 0.0                       # field ticks run since the first frame (int-valued when quantized)
        self._acc = TickAccumulator(FIELD_TPS)     # the engine's accumulator, for "quantized"
        self._dt = 0.0                             # this frame's virtual seconds (0 on a frame the counter froze)
        self._frame_ticks = 0.0                    # this frame's field ticks
        self._steps: list = []                     # ...as the world runs them: [avg] (mean), [1.0] * n (quantized)
        self._clock_frame = 0                      # the frame those are for (a test may step `frame` by hand)
        self._tick = 0.0                           # the step of `_steps` the world is running now
        self._plan: tuple | None = None            # the player's plan for this frame (`_player_plan`), once read
        self._wall0 = 0.0                          # time.time() the virtual clock's 0 is stamped at ("mtime")
        #: Unity rewrites output_log.txt on every launch. False models a game that died before it
        #: did, so the file on disk is the PREVIOUS launch's -- which the driver must not archive as
        #: this run's evidence, because nothing in an untimestamped log says it is stale.
        self.writes_unity_log = True
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
        #: A scripted scene with control withheld (:meth:`scene`): the beats still to play, where its choice
        #: window is ("opening" / "ready" / "closing") and the frame that ends that phase, every choice the
        #: scene was answered with (the absolute index taken), and when each window became READY as
        #: ``len(self.executed)`` then -- so a test can name the steps a waiter issued before it could answer.
        self._beats: list = []
        self._beat_phase: str | None = None
        self._beat_until = 0
        self._beat_frames = (6, 6)                 # (opening, closing) frames of a choice window
        self._typing_until = 0                     # a ready choice's prompt types on until this frame
        self.answered: list[int] = []
        self.readied: list[int] = []
        #: H9: a scene's MOVIE beat (:meth:`scene`) while it plays -- its skip dialog up included (MBG stays marked
        #: played until the movie ends) -- else None; and every movie as it went: ``{"frames", "start", "end",
        #: "played" (the frames it actually ran), "skips" (skip dialogs opened), "ended" ("played" | "skipped" |
        #: "warp")}``.
        self._movie: dict | None = None
        self.movies: list[dict] = []
        self._scene_control = True                 # what the scene's end does to control (:meth:`scene`'s ``control``)
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
        #: The story-write trace (s88), modelled as its CONTRACT: the `storytrace` verb's gates, the
        #: state block, and proto-1 rows -- the `arm`/`off` epochs, the harness's own pokes as `harness`
        #: rows, and a script store a test drives through :meth:`script_store`. Not the engine's
        #: suppression or its residue net: those are the DLL's to prove in-game. `storytrace_proto`
        #: None models an engine that predates the trace (no block published at all).
        self.storytrace_proto: int | None = 1
        self.story_on = False
        self.story_rows = 0
        self.story_error: str | None = None
        self.story_bytes = bytearray(2048)          # the modelled gEventGlobal the rows read old/new from
        self.scenario = 0
        self.donor = None                           # EffectiveFieldId: None = the field's own id
        #: The floor: one box ``(x0, z0, x1, z1)``, or a list of boxes whose UNION is walkable (a room
        #: opening into a corridor). A step that lands in none of them is clamped to the box he is in.
        #: Or a real walkmesh (anything with ``point_on_walkmesh``: a stock field's, through
        #: ``pathfind.PlayerWalkmesh``): his centre must stand on it -- see :meth:`_move_to`.
        self.walkmesh = walkmesh
        #: On a real walkmesh, how far his CENTRE is kept off every wall (``distance_to_boundary``) -- the
        #: engine's controller radius, cam.COLLISION_RADIUS_W, when a test sets it; None = anywhere on the mesh.
        #: A step that would come closer stops where it reaches that line, as the engine pushes him back out
        #: to it (2507's wall-slide samples sit 80-81u off its boundary), and the rest of the step slides on
        #: along the wall. A gateway zone only a few units deep past that line is then as hard to stand in as
        #: in the game. Placed nearer a wall than that (a scene's own spot), his first moving frame pushes him
        #: straight out onto the line, as the engine's does (:meth:`_pushed_out`).
        self.clearance: float | None = None
        #: Frames the character keeps moving after the direction is released. Measured on bench 30801,
        #: a hold covers what it commanded give or take ONE frame at 60 fps (`hold down 1` moves 60
        #: units at run speed, `hold down 31` moves 900) -- which the smooth 60 fps model (half a tick
        #: every frame) cannot reproduce without a frame of tail: a stand-in that stopped dead on
        #: release could not reproduce it at all -- and the pathological case, where the tail lands
        #: inside the NEXT burst's measurement window and is attributed to the direction pressed
        #: there, is what a test raises this to reproduce.
        #: Counted in FRAMES, moved in TICKS: a coast frame applies the last press to that frame's own ticks.
        #: ⚠ THE ENGINE RUNS NO SUCH COAST: HarnessAgent.IsHeld keys on the current Time.frameCount (:70-77) and MovePC
        #: reads the pad on every call (FieldMapActorController.cs:601-630) -- nothing buffers a key a frame. The bench's
        #: extra frame is the tick a one-frame hold catches in one phase of WHOLE ticks, and the published position's
        #: lag (tickrate.TAIL_TICKS). So None (the default) is ONE frame only where the smooth model is the fake -- 60
        #: fps, mean ticks, what every walk before the tick model was written against -- and NONE anywhere else: at
        #: 30 fps a frame is a whole tick, and a coast there moved him a tick the engine never runs, exactly Rate.reach
        #: with no slack (a sure-side test could not catch a tick of over-credit). A test that sets it gets what it sets.
        self.coast_frames: int | None = None
        self._coast = None                  # (dx, dz, calls a tick, frames_left): the last press's direction and gait
        #: THE PUBLISHED POSITION'S LAG, where a test models it: None (the default) publishes each frame's position with
        #: that frame's ticks run; else a predicate of the frame number -- true on a frame whose publish shows the
        #: position from BEFORE its own ticks, as the agent's does when its Update runs before HonoBehaviorSystem's (the
        #: one frame the research measured) -- an order Unity does not fix, so it may come and go (tickrate.TAIL_TICKS;
        #: Session.SETTLE_TICKS is two ticks for it).
        self.publish_lag = None
        self._pos_before = [0.0, 0.0, 0.0]  # the player's position before this frame's ticks (`publish_lag`)
        #: The field INHIBITS RUNNING (stock's DASHOFF, EventEngine.DoEventCode.cs:3009-3012): a run hold walks -- one
        #: MovePC call a tick, a turn's lerp too (FieldMapActorController.cs:196-198) -- and ``input.dash_inh`` reads 1,
        #: as the agent publishes it (AppendInput).
        self.dash_inhibit = False
        #: Whether the agent has redirected its save path away from the player's folder. Modelled
        #: because the driver must VERIFY this rather than trust it -- an unchecked sandbox is a
        #: check that cannot fail, and what it would fail to catch is the owner's overwritten game.
        self.save_sandboxed = True
        #: `[Control] SoftReset` in Memoria.ini. The ENGINE default is 0; this install has it on.
        #: False here models the install where the recovery ladder's top rung simply does not exist,
        #: which the driver must report honestly rather than hang on.
        self.soft_reset_enabled = True
        self.soft_resets = 0
        #: H9 (research/o3_design.md 3): the UI states the soft-reset combo fires in -- see :meth:`_check_soft_reset`.
        #: The default is today's pair; the engine's set is :data:`SOFT_RESET_ENGINE_UI` (BattleHUD among them,
        #: BattleResult never). A playing movie swallows the combo whatever this says.
        self.soft_reset_ui: tuple = ("FieldHUD", "WorldHUD")
        #: H9: True -- ``warp`` refuses unless ui_state is "FieldHUD", as the agent does (Ff9mkDebugMenu.Warp is false
        #: off the field HUD, and HarnessAgent throws "warp refused (not on a field?)"): nothing is written, nothing
        #: moves. False (the default): today's fake, a warp from any state.
        self.warp_field_only = False
        #: H9: False -- a warp lands with control OFF. The engine zeroes control at every field start (EventEngine.cs:
        #: 627) and a field that never grants it (61-63: research/o3_design.md 0.2 #4, #19) leaves it off; a test's
        #: director gives it where a field would. True (the default): today's warp, control handed over on arrival --
        #: which is how a smoke built on Session.warp() (its wait_playable needs control) passes here and hangs there.
        self.warp_arrive_control = True
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
        #: Scenes that open the battle TUTORIAL screen before the first command (battle.cs:100-105 opens it on
        #: scene 336, the Masked Man): ui_state "Tutorial", no command menu, until one Confirm closes it
        #: (TutorialUI.cs:116-125). A fight that waited for a command there would wait out its whole timeout.
        self.tutorial_scenes: set = set()
        self._tutorial = False
        #: H9 (research/o3_design.md 3), each None by default -- today's fake exactly. A SCRIPTED end, King Leo's
        #: latch (BSC_TH_E002 e1 t1 [587] ``cur.hp <= 10000``, latched at [601]): ``{"unit": name, "hp_raw_le": n,
        #: "result": r, "after_frames": k}`` -- the first time that unit's ``hp_raw`` is at or below ``n`` after a
        #: command resolves, the battle ends with ``r`` ``k`` frames later, whoever is standing; it latches once a
        #: battle. Without it, `_settle_battle` (one side gone) is the only end.
        self.battle_script_end: dict | None = None
        #: The ENGINE'S END ORDER (research/o3_design.md 0.2 #8): ``{"field": id, "fade_frames": a, "result_frames":
        #: b, "load_frames": c, "arrive_control": False}``. Every end (:meth:`end_battle`) then runs four phases: (1)
        #: the FADE, ``a`` frames -- the end's result published while the field id is still the battle's,
        #: ``battle_active`` True, ui BattleHUD, no command asked; (2) the OVER FRAME, one frame -- a result of 2 folds
        #: to 1 AND the field id becomes ``field``, together (HonoluluBattleMain.UpdateOverFrame), ui "BattleResult",
        #: still active; (3) BATTLERESULT, ``b`` frames, the same (no panel); (4) the LOAD, ``c`` frames --
        #: ``battle_active`` False, ui still "BattleResult" (the lag); then FieldHUD in ``field``, control as
        #: ``arrive_control`` says, a new visit (a fresh load). No sample ever pairs ``field`` with a result of 2.
        #: None: today's end -- the same field, FieldHUD at once.
        self.battle_exit: dict | None = None
        #: Every phase of a `battle_exit` end as it began: ``{"phase": "fade" | "over" | "load" | "field", "frame",
        #: "field", "result", "active", "ui"}`` -- the frame the scene went is the "load" row's.
        self.exits: list[dict] = []
        self._bexit: tuple | None = None           # (phase, the frame it ends on, the end's result) while one runs
        self._script_end: tuple | None = None      # (the frame it is due, its result) once the latch fired
        self._script_latched = False
        #: The naming screen (``Menu(1, char)``, a scene beat ``{"naming": char}``): each character named, in order.
        self.named: list[int] = []
        self._name_focus = False
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
        #: Walk-in gateway REGIONS per field, modelled on the engine's ExitField rather than on the
        #: instant `gateway` box above: ``{field id: [{"zone": [[x, z], ...], "to": id,
        #: "arrive": (x, z)}]}``. Stepping into a zone takes control on THAT frame; the field changes
        #: `exit_frames` later (the fade), and the player appears at ``arrive`` with control -- so a
        #: button still held at that moment walks him in the destination, which is the whole bug the
        #: routed verbs exist to avoid. ``exit_frames = 0`` changes the field on the same frame.
        #:
        #: As TreadQuad (TreadQuad.cs:6-22), the FIRST region in the list that contains his centre answers,
        #: and only it: a region that answers without firing shadows every region after it. Opt-in keys, each
        #: absent by default (and a region without them behaves exactly as above):
        #:   * ``"face"`` -- stock's DOOR FACING GATE (scan_gateways' ``face_gate``): the region fires only
        #:     while his yaw `_face_deg` faces his projection onto its first edge
        #:     (content.doorface.door_faced) -- True for the stock window (48, 208), or an explicit
        #:     ``[lo, hi]``. A region that fails it answers and fires nothing, and -- as the engine's tag 2
        #:     runs every tick he has control -- it is tested again on every frame he STANDS in it too, so a
        #:     press that turns him without moving him (into a wall) can fire it.
        #:   * ``"to": None`` -- a DEAD region: armed, answers, never fires (a stock region whose tag 2 returns
        #:     at once still blocks every region after it).
        #:   * ``"arrive_face"`` -- his yaw, in degrees, where he appears (applied with ``arrive``).
        #:   * ``"points"`` -- the ENGINE's polygon (scan_gateways' ``region``): membership by
        #:     content.doorface.region_contains (the ring of triplet triangles; a 5+-gon's middle is dead)
        #:     instead of the even-odd test on ``zone``, and the facing gate's first edge.
        #:   * ``"take": True`` -- a WALK-IN TRIGGER, not a gateway: entering it takes control on that frame
        #:     (its tag 2's DisableMove) and nothing warps -- logged in `fired` with ``to`` None. Control comes
        #:     back only when the test's scene gives it back.
        #:   * ``"arrive_control": False`` -- the destination arrives with control OFF: the arrival scene's to
        #:     hand back (a test's director gives it), as 101's Herald and 115's Puck hold it.
        #: ⚠ An UNGATED region fires only on a frame a step (or the coast after one) lands him in it, never
        #: while he stands there -- the engine re-tests those every tick too, but the suite's fixtures that
        #: place him inside a zone depend on the step-only rule, so only a gated region gets the standing test.
        self.regions: dict[int, list[dict]] = {}
        self.exit_frames = 0
        #: Every region that fired: ``{"frame", "from", "to", "executed"}`` -- ``executed`` is
        #: ``len(self.executed)`` at that moment, so a test can name the steps issued AFTER it.
        self.fired: list[dict] = []
        self._exit: tuple[int, int, tuple[float, float]] | None = None   # (due frame, dest, arrive)
        self._arrive_face: float | None = None     # the firing region's ``arrive_face``, applied on arrival
        self._arrive_control = True                # the firing region's ``arrive_control``, applied on arrival
        #: A LADDER, where a test models one (115's climb: e15 t3 DisableMove, then the climb loop reads B_KEY(16)
        #: every tick): ``{"top": y, "bottom": y, "step": units a field tick}`` -- y is ``player[1]``, the ``pos[1]``
        #: the agent publishes, and UP is the way from ``bottom`` to ``top``: on 115's real ladder it RISES as he climbs
        #: (stock rehearsal o2-rh-115: 0 -> 2691 in 9 bursts, then held there), so the model reads the direction from
        #: the pair rather than assuming one. While `climbing` (control OFF, as the climb runs), each field tick moves
        #: him ``step`` up while Up or Left is held and down while Down or Right is (B_KEY(96) descends); past ``top`` he is
        #: `climbed` (control stays off: the scene at the top takes over), past ``bottom`` the climb ends with
        #: control back (the bottom's EnableMove). None: no ladder.
        self.ladder: dict | None = None
        self.climbing = False
        self.climbed = False
        #: Bodies the walkmesh does not know about -- someone standing still in the way: ``{field id:
        #: [(x, z, r) or (x, z, r, solid), ...]}``, ``r`` centre to centre (WalkMesh.Collision). A step
        #: into one that has it in FRONT of him is pushed back out to ``r`` along the line from its
        #: centre (FieldMapActorController.cs:776-797), so a press at an angle slides him round it and a
        #: press straight at it stops him dead -- stock Zidane pressed into a Dali child on 350, six
        #: bursts, 0u. A push-out that lands in another body is undone, move and all.
        #: A body is PASSABLE unless ``solid`` (object flag 16, which no NPC on stock 350 sets): the
        #: engine's sLockTimer (CheckCollFallback, :822) counts one a colliding MovePC call, flips to
        #: -25 at 25, and the push-out is off until it counts back to 0 -- so one unbroken hold walks
        #: through him, and bursts with a pause between never do. Counted here in MovePC calls, a tick's
        #: calls (two running, one walking or idle) times the ticks a frame holds -- at the default 60 fps, mean
        #: ticks, a running frame one and a walking or idle frame half; whole calls one at a time when quantized.
        #:
        #: A body may also be a DICT -- the s89 object it models, published under ``objects`` (see
        #: `objects_mode`): ``{"x", "z", "r"}`` and optionally ``"y"`` (it collides only while |dy| < 400,
        #: WalkMesh.cs:922), ``"solid"``, ``"coll"`` (False: walk-through), ``"uid"`` / ``"sid"`` (default
        #: 128 + / 10 + its index), ``"shown"``; ``"range_r"`` -- a CONTACT trigger: with control, standing
        #: still or not, his centre inside it fires the entry's Range (CollisionRequest, every tick; logged
        #: in `touched`; only while ``coll``, as mode 2 keeps the pair rule), and with ``"talk_r"`` too it
        #: also fires inside that while he faces it; ``"to"`` / ``"arrive"`` make that Range a warp (stock
        #: 350's Vivi sends the run to 358); and ``"path"`` [(x, z), ...] with ``"speed"`` (units a frame of the
        #: calibrated 60 fps model -- ``speed / WALKER_FRAME_TICKS`` a field tick, as MoveToward steps once a tick, so
        #: the same units a SECOND at any `render_fps`) makes
        #: it a WALKER, back and forth along the path (``"once"``: to its end, then it stands), published
        #: ``moving`` -- and held while its next step would come within ``r`` of him (MoveToward stops on
        #: the player), still ``moving``.
        self.blockers: dict[int, list] = {}
        #: What `objects` / `pushout` publish: "listed" (the s89 agent: the list on a field, null off
        #: one), "null" (an agent that could not walk the list -- never a partial one) or "absent" (an
        #: engine without s89: no key at all).
        self.objects_mode = "listed"
        #: Every contact trigger that fired: ``{"frame", "field", "uid", "kind" ("range" / "talk"),
        #: "executed"}`` -- once per entry into its radius.
        self.touched: list[dict] = []
        #: Every step that met a body -- the push-out ran, or the step was refused: ``{"frame", "uid"}``.
        #: A router that sees the bodies should leave this empty.
        self.contacts: list[dict] = []
        self._in_trigger: set = set()             # (field, body index) whose trigger he stands in
        self._facing = (0.0, 1.0)                 # the direction last pressed (the talk search wants +-90 deg)
        #: His model yaw, Actor.rotAngle[1] in degrees (0 faces -z, 90 -x, +-180 +z, -90 +x) -- what a gated
        #: region reads (``regions`` ``"face"``). Every tick a held direction spends MovePC calls (a press, or the
        #: coast after one, whether or not he moves: a press into a wall turns him too) turns it toward that
        #: direction, 40% a call (content.doorface.turn_step; FieldMapActorController.cs:744-761 at stock 6b8bb2d5)
        #: -- a tick's calls its step over the 30u a call steps (content.doorface.movepc_calls): one a tick walking,
        #: two running, so a frame's the ticks it holds times that -- at the default 60 fps, mean ticks, a run frame
        #: one call and a walked one half, ON AVERAGE ("quantized" ticks, or `tick_phase`, turn him in whole calls
        #: instead). Standing, frozen or without control it holds. PRIVATE, and settable by a test: the agent
        #: publishes ``dir`` 0 on a field (PosObj.rot[1], which a field never writes), and so does this stand-in.
        self._face_deg = 0.0
        #: None (the default): a frame turns him by its ticks' calls -- in mean mode its AVERAGE, half a call a walked
        #: frame at 60 fps: smooth, and what every walk written before this was written against. 0 or 1: the
        #: engine's WHOLE calls FOR THE TURN ALONE, the precursor of ``ticks="quantized"`` kept for the tests pinned
        #: on it -- a 30 Hz tick on every other frame of the 60 fps model (FPSManager.cs:77-110 at stock), falling on
        #: the frames whose number is that phase mod 2, where the frame turns him by its tick's whole calls (a walked
        #: frame 1, a run frame 2; nothing on the frames between), and the settle passes of a turn count only there.
        #: Only the TURN is whole: the step stays a frame's average, as every walk in the suite measures it. A press of
        #: an odd number of walked frames then turns him the fewer whole calls in one phase and the more in the other
        #: -- what a planner that credits half calls cannot see (harness.tickrate.Rate.calls_sure). Refused (ValueError)
        #: unless the fake is that model: ``render_fps`` 60 and ``ticks`` "mean" -- `_check_legacy_knobs`.
        self.tick_phase: int | None = None
        #: The facing as memoria-patch s90 publishes it, and its in-place ``turn``. "absent" (the DEFAULT -- an
        #: engine without s90, what every walk written before it was written against): no ``player.yaw`` /
        #: ``player.face`` keys, and ``turn`` raises ``unknown op 'turn'`` as the old agent's Execute does.
        #: "published" (the s90 agent): on a field with a controlled character ``player.yaw`` is round(`_face_deg`,
        #: 3) and ``player.face`` content.doorface.facing_byte of it -- a JSON NUMBER, as state.json's numbers are --
        #: both null off one (HarnessAgent.PublishState); and ``turn <dir>[+<dir>] [frames]`` (:meth:`_begin_turn`)
        #: holds the direction KEYS with no axis, turning `_face_deg` by the frame's MovePC calls and never stepping
        #: him, then reports ``turn_end`` once the field has judged the final facing (:meth:`_service_turn`).
        self.facing_mode = "absent"
        #: `[AnalogControl] Enabled` in Memoria.ini. False models the install whose key path would STEP him (MovePC
        #: normalises the key vector and nothing zeroes it, FieldMapActorController.cs:710-711): the agent refuses
        #: every ``turn`` there (``[AnalogControl] Enabled=0 -- ...``).
        self.analog_control = True
        #: The event passes the agent lets the field run on a turn's final facing, after its keys lift, before it
        #: reports ``turn_end`` (HarnessAgent.TurnSettlePasses: the region pass that reads the facing runs a pass
        #: after the MovePC call that wrote it). Counted as the agent counts them -- FRAMES that ran a pass
        #: (HarnessAgent.ServiceTurn: "a frame that runs two passes counts once"): every frame in mean mode (each
        #: holds a share of a tick), the frames that ran a whole tick in quantized mode, and under `tick_phase` its
        #: tick frames. A test raises it to hold the report well past the request's ack.
        self.turn_settle_passes = 2
        #: MovePC calls one frame of an IN-PLACE turn spends, when set -- an override of the tick model. None: the
        #: frame's ticks times the gait's calls a tick (run: two; with ``cancel`` held, walk: one) -- at the default
        #: 60 fps, mean ticks, one call a run frame and half a walked one, the calibrated rate the driver used to plan
        #: by. Set, it is the calls every frame spends whatever `render_fps` says (the turn of a monitor that is not
        #: the calibrated one, before the fake had a render rate). Mean ticks only -- `_check_legacy_knobs`.
        self.turn_calls: float | None = None
        #: A HUMAN at the controls, as ``turn`` sees one: ``stick`` the |axis| a physical stick or key pushes
        #: (HarnessAgent.PhysicalAxis), ``click_path`` a click-to-move path pending (the controller's hasTarget /
        #: movePaths). Over STICK_THRESHOLD the agent refuses a turn (``a physical stick or key is pushing the axis``)
        #: and CUTS one open (``axis``); a pending path refuses one (``a click-to-move path is pending``). Neither
        #: moves him here -- the fake's walk is the harness's keys alone.
        self.stick = 0.0
        self.click_path = False
        #: The ``turn`` being reported, None when none is (HarnessAgent's _turnFrom / _turnLift / _turnField /
        #: _turnPo and its start): ``{"from", "lift", "field", "visit", "x", "y", "z", "yaw0", "passes"}``; and
        #: `_turn_keys`, the directions a turn holds (_turnMask) -- held keys no step is ever taken on (MoveHeld).
        self._turn_open: dict | None = None
        self._turn_keys: set = set()
        #: Bumped by every warp and every arrival: a new visit's actor is a new controlled actor, as a same-id reload
        #: makes new ones -- a turn begun on the old one is cut ("player"; "field" when the id changed too).
        self._visit = 0
        self._lock = 0.0                          # EventEngine.sLockTimer
        self._lock_free = 1                       # sLockFree: 0 while the last body touched is solid
        self._coll = 0.0                          # SCollTimer, in ticks (COLL_TICKS after a push-out)
        #: Movement FREEZES with control held -- MovePC's other gate, the script's pad mask
        #: (EventInput.IsMovementControl), which the agent does not publish: ``{field id: [{"zone":
        #: [[x, z], ...], "frames": n}]}``. Stepping into a zone holds all movement for ``n`` frames OF THE
        #: CALIBRATED 60 FPS -- ``n`` / 2 field TICKS: the script that masks the pad counts once a tick
        #: (ProcessEvents), whatever the render rate -- (None = for good) while `control` stays True. Each zone
        #: fires once; a warp ends a freeze. `_frozen_ticks` is in `ticks_run`; `_frozen_until`, in FRAMES, is a hold on
        #: movement a test lays on (or lifts) by hand -- a frame count it means literally, which replaces every hold.
        self.freezes: dict[int, list[dict]] = {}
        self._frozen_frames: float = 0
        self._frozen_ticks: float = 0
        self._froze: set = set()                  # (field id, index) of every freeze zone that fired
        #: every op the fake ever executed, so a test can assert a step was DELIVERED rather than
        #: inferring it from a state that several other ops could also have produced.
        self.executed: list[list[str]] = []
        self.arm_transitions = 0
        #: Publishes that STALL MID-REWRITE, one queued duration (seconds) consumed per publish --
        #: see :meth:`stall_publish`. Empty by default: the ordinary publish replaces the file.
        self._publish_stalls: list[float] = []
        #: events.jsonl appends that COLLIDE with the driver's read, by event kind: ``{"turn_end": 1}`` makes the next
        #: ``turn_end`` append fail as the agent's File.AppendAllText does while the driver has the log open
        #: (IOException). The agent keeps such rows BUFFERED and writes them with its next event, whatever that is
        #: (HarnessAgent.Event / FlushEvents) -- so a row can reach the log late, behind a row written after it was
        #: made, and only once something else is logged. `_pending_events` is that buffer.
        self.event_collisions: dict = {}
        self._pending_events: list = []
        #: Set while a stalled publish holds state.json truncated and EMPTY, so a test can read the
        #: channel inside the gap rather than hoping to land in it.
        self.stalling = threading.Event()

    # -- lifecycle -----------------------------------------------------------------------------
    def start(self) -> "FakeGame":
        self.shots.mkdir(parents=True, exist_ok=True)
        if self.writes_unity_log:
            self.unity_log.parent.mkdir(parents=True, exist_ok=True)
            self.unity_log.write_bytes(b"Initialize engine version: 5.2.3p2 (fakegame)\r\n")
        self._wall0 = time.time()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    # -- the clock -----------------------------------------------------------------------------
    # THE ENGINE'S TIME, MODELLED ON A VIRTUAL CLOCK. A frame is 1 / render_fps virtual seconds (plus any hitch), the
    # seconds become field ticks at tick_hz (FIELD_TPS x fast_forward) -- their average ("mean") or FPSManager's whole
    # ones ("quantized") -- and everything the engine does once a tick is done once a tick here: MovePC's steps (one
    # call walking, two running, 30u each: FieldMapActorController.cs:198-209 at stock 6b8bb2d5) and its turn (40% a
    # call), the push lock's count (a call at a time), SCollTimer, a walker's step, a contact's and a gated region's
    # re-test, a freeze's countdown (the script's pad mask counts ticks). Frame-counted things stay frame-counted, as
    # the agent counts them: holds, waits, publishes, polls -- and the fade, as a SIMPLIFICATION (its duration is the
    # engine's, not the agent's; no test yet runs a fade off 60 fps). At the defaults -- 60 fps, mean -- every frame is
    # half a tick, and the fake moves EXACTLY as it did when its speeds were 30u / 15u a frame.
    @staticmethod
    def _positive_fps(v) -> float:
        v = float(v)
        if not (math.isfinite(v) and v > 0):
            raise ValueError(f"render_fps must be a positive number of frames a second, not {v!r}")
        return v

    @property
    def render_fps(self) -> float:
        """The VIRTUAL render rate: the seconds a frame spans on the fake's clock (default 60). Settable mid-run -- a
        regime switch: the clock re-anchors, so rt stays continuous."""
        return self._render_fps

    @render_fps.setter
    def render_fps(self, value) -> None:
        value = self._positive_fps(value)
        self._check_legacy_knobs(render_fps=value)
        self._rt_anchor, self._rt_frames = self.rt, 0
        self._render_fps = value

    @property
    def tick_mode(self) -> str:
        """``"mean"`` or ``"quantized"`` (`TICK_MODES`), as constructed with ``ticks=``."""
        return self._tick_mode

    @tick_mode.setter
    def tick_mode(self, value: str) -> None:
        if value not in TICK_MODES:
            raise ValueError(f"ticks must be one of {TICK_MODES}, not {value!r}")
        self._check_legacy_knobs(tick_mode=value)
        self._tick_mode = value

    @property
    def tick_phase(self) -> int | None:
        return self._tick_phase

    @tick_phase.setter
    def tick_phase(self, value) -> None:
        if value is not None and value not in (0, 1):
            raise ValueError(f"tick_phase is None, 0 or 1, not {value!r}")
        self._check_legacy_knobs(tick_phase=value)
        self._tick_phase = value

    @property
    def turn_calls(self) -> float | None:
        return self._turn_calls

    @turn_calls.setter
    def turn_calls(self, value) -> None:
        self._check_legacy_knobs(turn_calls=value)
        self._turn_calls = None if value is None else float(value)

    def _check_legacy_knobs(self, **change) -> None:
        """Refuse a combination the two pre-tick knobs cannot mean: `tick_phase` is the 60 fps model's turn-only whole
        calls (a tick every other frame), so it needs ``render_fps`` 60 and mean ticks; `turn_calls` is calls a FRAME,
        which quantized frames (0, 1, 2 ticks) have no one value of. Checked on every change of any of the four, so
        no order of setting them can reach a silently wrong turn."""
        fps = change.get("render_fps", getattr(self, "_render_fps", 60.0))
        mode = change.get("tick_mode", getattr(self, "_tick_mode", "mean"))
        phase = change.get("tick_phase", getattr(self, "_tick_phase", None))
        calls = change.get("turn_calls", getattr(self, "_turn_calls", None))
        if phase is not None and (fps != 60.0 or mode != "mean"):
            raise ValueError(f"tick_phase models a 30 Hz tick every other frame of a 60 fps, mean-tick fake; this one "
                             f"is {fps:g} fps, {mode} -- use ticks='quantized' for whole ticks at any rate")
        if calls is not None and mode != "mean":
            raise ValueError("turn_calls is MovePC calls a frame, which quantized ticks (0, 1 or more a frame) have no "
                             "one value of -- leave it None and let the ticks turn him")

    @property
    def tick_hz(self) -> float:
        """Field ticks a second: FIELD_TPS x `fast_forward`."""
        return FIELD_TPS * self.fast_forward

    def hitch(self, seconds: float, *, frame: int | None = None) -> None:
        """Make ``frame`` (default: the next) take ``seconds`` more virtual time -- a stall the engine catches up in
        that frame's ticks."""
        at = self.frame + 1 if frame is None else int(frame)
        self._hitches[at] = self._hitches.get(at, 0.0) + float(seconds)

    def _advance_clock(self) -> None:
        """The virtual clock's frame: its seconds (``_dt``: 1 / render_fps + any hitch), ``rt``, and its field ticks
        (``_frame_ticks``; ``_steps`` as the world runs them -- one share in mean mode, one per whole tick quantized)."""
        self._clock_frame = self.frame
        extra = self._hitches.pop(self.frame, 0.0)
        self._rt_frames += 1
        if extra:
            self._rt_anchor += extra
        self.rt = self._rt_anchor + self._rt_frames / self._render_fps
        self._dt = 1.0 / self._render_fps + extra
        if self._tick_mode == "quantized":
            self._acc.fast_forward = self.fast_forward
            n = self._acc.advance(self._dt)
            self._frame_ticks, self._steps = float(n), [1.0] * n
        else:
            # the average, EXACT at the defaults: 30 / 60 is 0.5, so a run frame is 1.0 call and 30.0 units
            r = (self.tick_hz / self._render_fps if not extra
                 else self.tick_hz * min(self._dt, MAX_DELTA_TIME))
            self._frame_ticks, self._steps = r, [r]
        self.ticks_run += self._frame_ticks

    def _hold_frame(self) -> None:
        """A frame the counter did NOT advance on (``mode="frozen"``): no time passes, no tick runs."""
        self._clock_frame = self.frame
        self._dt, self._frame_ticks, self._steps = 0.0, 0.0, []

    def _frame_steps(self) -> list:
        """This frame's field ticks as the world runs them (`_steps`), the clock advanced first if the frame moved on
        without it -- a test that steps ``frame`` by hand and calls ``_step_world`` gets the same frame the loop
        would."""
        if self._clock_frame != self.frame:
            self._advance_clock()
        return self._steps

    # -- the two exception logs ----------------------------------------------------------------
    @property
    def unity_log(self) -> Path:
        return self.game_path / "x64" / "FF9_Data" / "output_log.txt"

    @property
    def memoria_log(self) -> Path:
        """The game ROOT's -- the working directory a launcher-style start gives the game."""
        return self.game_path / "Memoria.log"

    def throw(self, exc: str = "NullReferenceException",
              frames=("FieldMapActorController.MovePC ()",
                      "FieldMapActorController.UpdateMovement (Boolean copyLastPos)",
                      "HonoBehaviorSystem.Update ()"),
              *, message: str = "Object reference not set to an instance of an object",
              caught: bool = False) -> None:
        """Log an exception the way the engine does -- and in the log the engine would.

        Which log is decided by who CATCHES it. ``caught=True`` is one thrown under a Memoria
        ``catch (Exception err) { Log.Error(err); }`` -- all battle code, via
        ``HonoluluBattleMain.Update`` -- and lands in Memoria.log only, as timestamped ``|E|``
        lines. ``caught=False`` escaped a MonoBehaviour and lands in output_log.txt only, as an
        untimestamped block. The BYTES are a real run's, terminators included: Memoria.log is LF,
        and Unity ends every frame but the last with CR CR LF -- which a naive ``splitlines()``
        reads as a blank line, so a stand-in that wrote plain CRLF would pass a reader the real
        log breaks.
        """
        tail = " [0x00000] in <filename unknown>:0 "
        if caught:
            stamp = time.strftime("%d.%m.%Y %H:%M:%S")
            lines = [f"{stamp} |E| System.{exc}: {message}"]
            lines += [f"{stamp} |E|   at {f}{tail}" for f in frames]
            body, path = "".join(line + "\n" for line in lines), self.memoria_log
        else:
            trace = "\r\r\n".join(f"  at {f}{tail}" for f in frames)
            body = f"{exc}: {message}\r\n" + (trace + "\r\n" if trace else "")
            body += " \r\n(Filename:  Line: -1)\r\n\r\n"
            path = self.unity_log
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "ab") as f:
            f.write(body.encode("utf-8"))

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
                self._advance_clock()
            else:
                self._hold_frame()
            try:
                self._poll_arm()
                if self.armed:
                    self._poll_request()
                    self._drain()
                    self._check_soft_reset()
                    self._step_world()
                    self._step_scene()
                    self._step_battle()
                    self._service_turn()        # s90: end, or cut, an in-place turn
                    self._publish()
            except OSError as err:
                # Mirrors the agent's own try/catch. Without this a single transient sharing
                # violation killed the publisher thread, and every later wait then timed out
                # pointing at the wrong half of the system -- which is exactly how a harness
                # earns a reputation for being flaky when it is actually deterministic.
                self.error = str(err)
            if "mtime" in self.publish:
                self._pace_real_time()
            else:
                time.sleep(period)

    #: How far the real-time loop ("mtime" published) may fall behind the wall clock before it re-anchors rather than
    #: catch up: past this a stamp would read stale to the driver (Session's LIVE_WITHIN is 2 s).
    REALTIME_SLIP = 1.0

    def _pace_real_time(self) -> None:
        """Sleep until the wall clock reaches the virtual clock (``_wall0 + rt``), so each state.json stamped with its
        virtual write time is stamped at about the real moment it was written. A loop that has fallen behind (a busy
        machine) runs its frames back to back until it catches up -- their stamps stay exactly 1 / render_fps apart --
        and one more than REALTIME_SLIP behind re-anchors instead: a jump in the stamps the driver drops as a stall.
        A frozen frame advances nothing, so it just waits a frame."""
        if not self._steps and not self._dt:
            time.sleep(1.0 / self._render_fps)
            return
        ahead = self._wall0 + self.rt - time.time()
        if ahead > 0:
            time.sleep(ahead)
        elif ahead < -self.REALTIME_SLIP:
            self._wall0 -= ahead

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
        self._turn_open, self._turn_keys = None, set()     # s90: an arm transition clears a turn silently
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
            # s88: arming resets the tracer to OFF, silently -- an armed run that never sends
            # `storytrace 1` writes no story.jsonl at all
            self.story_on = False
            self.story_rows = 0
            self.story_error = None
            self._event("armed", protocol=PROTOCOL)
        else:
            self._story_stop()                 # the trace is dormant unless armed
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
        added = 0
        for line in lines[1:]:
            tok = line.split()
            if tok and not tok[0].startswith("#"):
                self.queue.append(tok)
                added += 1
        # the agent's receipt in the event log (HarnessAgent.PollRequest): what a turn's report is ordered after
        self._event("accepted", seq=seq, steps=added)

    def _drain(self) -> None:
        while self.queue and self.frame >= self.block_until:
            step = self.queue.pop(0)
            self.executed.append(list(step))
            try:
                self._execute(step)
            except Exception as err:                       # mirrors the agent: report, never die
                self.error = f"{step[0]}: {err}"
                self.error_seq = self.seq
                # ...and log it, as HarnessAgent.DrainQueue does: the error latch holds the LAST refusal of a
                # request, the event log every one
                self._event("error", op=step[0].lower(), message=str(err))
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
            button = _control(args[0])
            self._claim_for_move(button)               # s90: never a step inside a turn
            self._schedule(button, max(1, num(1, 2)))
            self._block(num(1, 2) + 2)
            self._menu_step(button)
        elif op == "hold":
            button = _control(args[0])
            self._claim_for_move(button)               # s90: never a step inside a turn
            self._extend(button, max(1, num(1, 30)))
        elif op == "release":
            # ⚠ A RELEASE MUST NEVER PRESS, and it lands NEXT frame (HarnessAgent `release`): a key down now stays
            # down this frame and lifts on the next -- so `release up` then `turn up` in one request is still a
            # direction down on the turn's frame, and refused, as the agent refuses it -- a key not down now (only
            # scheduled, or never pressed) is cleared outright
            button = _control(args[0])
            if self._is_held(button):
                self.held[button] = self.frame + 1
            else:
                self.held.pop(button, None)
                self.down_at.pop(button, None)
        elif op == "turn":
            # s90's in-place turn (an engine without it: `unknown op`, like any verb it never had)
            if self.facing_mode != "published":
                raise RuntimeError(f"unknown op '{op}'")
            self._begin_turn(_turn_directions(args[0] if args else ""), min(TURN_MAX_FRAMES, max(1, num(1, 30))))
        elif op == "newgame":
            if self.ui_state != "Title":
                raise RuntimeError("newgame: not at the title screen")
            self.ui_state = "FieldHUD"
            self.field_id = 70
            self.control = True
            self._block(3)
        elif op == "warp":
            # H9: the agent refuses a warp off the field HUD (Ff9mkDebugMenu.Warp, HarnessAgent.cs:652-656) -- before
            # anything is written -- when `warp_field_only` models it
            if self.warp_field_only and self.ui_state != "FieldHUD":
                raise RuntimeError("warp refused (not on a field?)")
            # ServicePendingWarp writes the entrance and the scenario straight into gEventGlobal BEFORE the map
            # changes, so the trace's residue net sees them in the OLD field (`_warp_writes`); -1 writes nothing
            self._warp_writes(num(1, -1), num(2, -1))
            self.field_id = num(0, -1)
            self.ui_state = "FieldHUD"
            self.control = self.warp_arrive_control     # H9: False -- control zeroed at the field start, not given
            if self._movie is not None:
                self._end_scene("warp")        # H9: the field load destroys MBG -- the movie and the scene it was in
            self.player = [0.0, 0.0, 0.0]
            self._visit += 1                   # a new visit's actor: a turn begun before it is cut
            self._in_trigger.clear()           # a new visit: a trigger he lands in fires afresh
            self._exit = None                  # a warp outruns any exit still fading
            self._arrive_control = True
            self.climbing = False              # ...and any climb
            self._frozen_frames = self._frozen_ticks = 0      # ...and any freeze
            self._lock, self._coll = 0.0, 0.0
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
            self._story_store("harness", bit >> 3, "Bit", int(self.flags[bit]), bit=bit)
        elif op == "byte":
            idx = num(0, -1)
            if not 0 <= idx < len(self.story_bytes):
                raise RuntimeError(f"byte index {idx} is out of range")
            self._story_store("harness", idx, "Byte", num(1, 0) & 0xFF)
        elif op == "storytrace":
            if self.storytrace_proto is None:          # a pre-s88 agent has no such verb
                raise RuntimeError(f"unknown op '{op}'")
            if num(0, 1) != 0:
                self._story_start()
            else:
                self._story_stop()
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
            self._turn_open, self._turn_keys = None, set()      # s90: cleared silently, one being judged included
            self.watch = []
            self.note = ""
            self.error = None
            self.state_every = 2
            self._release_netsync()
            self._story_stop()                 # one scenario's trace must not run on into the next
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
            self._story_stop()                 # the trace's last rows land before the window closes
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
        if self._exit is not None and self.frame >= self._exit[0]:
            self._step_exit_now()
        self._pos_before = list(self.player)
        self._plan, visit = None, self._visit
        for ticks in self._frame_steps():       # the frame's field ticks: one share (mean) or each whole one
            self._tick = ticks
            self._coll = max(0.0, self._coll - ticks)       # ProcessEvents counts SCollTimer down every tick
            if self.ui_state != "FieldHUD":
                continue
            self._step_walkers(ticks)
            if self.climbing and self._visit == visit:
                self._step_ladder(ticks)        # the climb runs with control OFF: before the skip below
            if not self.control or self._visit != visit:
                continue                        # control gone, or a warp mid-frame: no tick of it moves him there
            self._step_player()
            if self.control:
                self._fire_contacts()           # CollisionRequest: every tick he has control, moving or not
        if self._plan is None and self.ui_state == "FieldHUD" and self.control:
            self._player_plan()                 # a frame no tick ran on still reads the pad: a coast frame is spent

    def _step_ladder(self, ticks: float) -> None:
        """One field tick (or, in mean mode, the frame's share of one) of the `ladder` climb: ``step`` up a tick while
        Up or Left is held, down while Down or Right is (both ways at once: nowhere); past ``top`` the climb is over,
        `climbed`, with control still off; past ``bottom`` it is over with control back."""
        lad = self.ladder
        if lad is None:
            self.climbing = False
            return
        way = ((1 if self._is_held("up") or self._is_held("left") else 0)
               - (1 if self._is_held("down") or self._is_held("right") else 0))
        if not way:
            return
        top, bottom = float(lad["top"]), float(lad["bottom"])
        up = 1.0 if top > bottom else -1.0                 # the sign of a step toward the top in published y
        self.player[1] += way * up * float(lad["step"]) * ticks
        if (self.player[1] - top) * up > 0:
            self.climbing, self.climbed = False, True
        elif (bottom - self.player[1]) * up > 0:
            self.climbing, self.control = False, True

    def _player_plan(self) -> tuple:
        """What the controlled player does THIS FRAME, read once from the pad (IsHeld keys on the frame: every tick in
        it sees the same keys) -- ``("frozen",)``, ``("turn", ux, uz, calls a tick)`` (an s90 turn's keys, no axis),
        ``("idle",)``, ``("coast", dx, dz, calls a tick)`` (the last press still applied: its frame consumed here, once,
        however many ticks it holds), or ``("press", ux, uz, calls a tick)``: ``ux``/``uz`` the unit press after the
        twist, ``dx``/``dz`` the direction a step actually took (after the wall-slide projection)."""
        if self._frozen():
            self._coast = None                  # MovePC returns before it moves anyone
            return ("frozen",)
        vx = vz = 0.0
        if self._move_held("up"):
            vz += 1.0
        if self._move_held("down"):
            vz -= 1.0
        if self._move_held("right"):
            vx += 1.0
        if self._move_held("left"):
            vx -= 1.0
        gait = CALLS_PER_TICK["walk" if self._is_held("cancel") or self.dash_inhibit else "run"]
        if vx == 0.0 and vz == 0.0:
            turn = self._turn_keys_direction()
            if turn is not None:
                self._coast = None              # the keys' own sample replaces the last movement's
                self._facing = turn
                return ("turn", turn[0], turn[1], gait)     # s90: the keys of a `turn`, no axis -- he turns in place
            if not self._coast:
                return ("idle",)
            # Nothing held -- but the engine is still applying the last movement it sampled.
            dx, dz, c, left = self._coast
            self._coast = (dx, dz, c, left - 1) if left > 1 else None
            return ("coast", dx, dz, c)
        mag = (vx * vx + vz * vz) ** 0.5
        return ("press", *self._twisted(vx / mag, vz / mag), gait)

    def _twisted(self, vx: float, vz: float) -> tuple[float, float]:
        """A screen-space press as the world direction it moves him (`twist`)."""
        if not self.twist:
            return vx, vz
        a = math.radians(self.twist)
        return vx * math.cos(a) - vz * math.sin(a), vx * math.sin(a) + vz * math.cos(a)

    def _step_player(self) -> None:
        """The tick being run (`_tick`: one field tick, or in mean mode the frame's share of one -- so at the defaults
        this is once a frame) of the controlled player, on the frame's plan (`_plan`, read from the pad at the frame's
        first: :meth:`_player_plan`): the pad, the push-out, the floor, the regions. A tick's step is its MovePC calls
        x 30u -- one call walking, two running (FieldMapActorController.cs:198-209 at stock 6b8bb2d5) -- so at the
        defaults (60 fps, mean) a run frame steps 30u in one call and a walked frame 15u in half of one."""
        from ff9mapkit.content import doorface
        if self._plan is None:
            self._plan = self._player_plan()   # the pad, read once: every tick of a frame sees the same keys
        plan, ticks = self._plan, self._tick
        kind = plan[0]
        if kind == "frozen":
            self._retest_gated()
            return
        if kind == "idle":
            self._lock_fallback(ticks * CALLS_PER_TICK["walk"])   # MovePC still runs, once a tick
            self._retest_gated()
            return
        if kind == "turn":
            self._turn_in_place(plan[1], plan[2], ticks * plan[3])
            return
        if kind == "coast":
            _k, dx, dz, c = plan
            step = ticks * c * doorface.STEP_PER_CALL
            vx, vz = dx * step, dz * step
            calls = doorface.movepc_calls((vx * vx + vz * vz) ** 0.5)
            self._turn(vx, vz, calls)           # the coast is the press still being applied: it turns him too
            self._move_to(self.player[0] + vx, self.player[2] + vz, calls)
            self._enter_regions()
            self._enter_freezes()
            return
        _k, vx, vz, c = plan
        speed = ticks * c * doorface.STEP_PER_CALL
        calls = doorface.movepc_calls(speed)    # the MovePC calls this tick's step is worth (30u each)
        # the turn comes first, as in MovePC: the press turns him whether or not the step then moves him
        self._turn(vx, vz, calls)

        if self.mode == "wall_slide":
            # Every press is projected onto one fixed wall direction. The character always MOVES --
            # which is why a "did it move at all" probe cannot detect this -- but never where he was
            # sent. A basis measured here is a well-formed lie.
            wall = (0.7071, 0.7071)
            along = vx * wall[0] + vz * wall[1]
            vx, vz = wall[0] * along, wall[1] * along
            if vx == 0.0 and vz == 0.0:
                return

        moved = self._move_to(self.player[0] + vx * speed, self.player[2] + vz * speed, calls)
        # Arm the tail with the direction and gait actually applied this tick.
        coast = self._coast_frames()
        self._coast = (vx, vz, c, coast) if coast > 0 and moved else None

        if self.gateway is not None:
            gx0, gz0, gx1, gz1, dest = self.gateway
            if gx0 <= self.player[0] <= gx1 and gz0 <= self.player[2] <= gz1:
                self.field_id = dest
                self.player = [0.0, 0.0, 0.0]
                self.control = True
        self._enter_regions()
        self._enter_freezes()

    @property
    def _frozen_until(self) -> float:
        """A hold on movement in FRAMES, as a test lays one by hand (movement held while ``frame`` is below it)."""
        return self._frozen_frames

    @_frozen_until.setter
    def _frozen_until(self, frame: float) -> None:
        """Lay -- or, with a frame already past, lift -- a hold in frames; it REPLACES every hold, a zone's tick-counted
        freeze included (a test that lifts "the" hold lifts it, whichever kind the walk stepped on)."""
        self._frozen_frames, self._frozen_ticks = frame, 0

    def _frozen(self) -> bool:
        """Whether movement is held this frame: a zone's freeze still counting its ticks, or a hold a test laid on in
        frames."""
        return self.frame < self._frozen_frames or self.ticks_run < self._frozen_ticks

    def _coast_frames(self) -> int:
        """`coast_frames` as set, or -- None -- one frame at the calibrated model (60 fps, mean ticks) and none off it
        (see `coast_frames`)."""
        if self.coast_frames is not None:
            return int(self.coast_frames)
        return 1 if self._render_fps == 60.0 and self._tick_mode == "mean" else 0

    def _move_held(self, button: str) -> bool:
        """A direction held to MOVE: down, and not a ``turn`` key (HarnessAgent.MoveHeld: a turn key feeds no
        axis)."""
        return self._is_held(button) and button not in self._turn_keys

    def _turn_keys_direction(self) -> tuple[float, float] | None:
        """The world direction the s90 ``turn`` keys down this frame compose (after the twist) -- MovePC's key branch
        builds the 8-way target from them (FieldMapActorController.cs:698-708) -- or None when no turn key is down (or
        they cancel: refused at the start, never composed here)."""
        keys = [b for b in self._turn_keys if self._is_held(b)]
        if not keys:
            return None
        vx = (1.0 if "right" in keys else 0.0) - (1.0 if "left" in keys else 0.0)
        vz = (1.0 if "up" in keys else 0.0) - (1.0 if "down" in keys else 0.0)
        if vx == 0.0 and vz == 0.0:
            return None
        mag = (vx * vx + vz * vz) ** 0.5
        return self._twisted(vx / mag, vz / mag)

    def _turn_in_place(self, vx: float, vz: float, calls: float) -> None:
        """A tick of an s90 ``turn`` whose keys are down (and no other direction: the agent refuses both ways) toward
        world direction (``vx``, ``vz``): the stick-threshold test zeroes the step because the axis is under threshold
        (FieldMapActorController.cs:736-737), and the facing lerp (:749-764) keys on the booleans -- so `_face_deg`
        turns by the tick's MovePC calls (``calls``; `turn_calls` a frame when set) and he takes no step. The zero step
        still runs the push-outs a step would (:meth:`_move_to` to where he stands: a body he overlaps, or a wall nearer
        than his radius, moves him -- what ``turn_end``'s ``moved`` witnesses), and the region he stands in is
        re-tested, a gated door he now faces firing (:meth:`_retest_gated`)."""
        if self.turn_calls is not None:
            calls = self.turn_calls
        self._turn(vx, vz, calls)
        before = (self.player[0], self.player[2])
        self._move_to(before[0], before[1], calls)
        if (self.player[0], self.player[2]) != before:
            self._enter_regions()               # pushed: a step's rule
        else:
            self._retest_gated()                # standing: the gated region's every-tick re-test

    def _turn(self, vx: float, vz: float, calls: float) -> None:
        """His yaw (`_face_deg`) after a frame that held world direction (``vx``, ``vz``) -- the press after the
        twist, as MovePC's ``moveVec`` -- for ``calls`` MovePC calls (the frame's average): content.doorface.turn_step
        toward ``yaw_of(vx, vz)``; under `tick_phase`, the tick's whole calls on a tick frame and none between.
        Called on every frame a direction is applied, BEFORE the step: whatever the walls or a body then do to his
        position, the yaw has turned (FieldMapActorController.cs:744-761 precede the collision at :762, at stock)."""
        from ff9mapkit.content import doorface
        if self.tick_phase is not None:
            if self.frame % 2 != self.tick_phase:
                return                          # no tick this frame: MovePC does not run
            calls = round(2 * calls)            # the tick's whole calls: a walked frame's 1, a run frame's 2
        self._face_deg = doorface.turn_step(self._face_deg, doorface.yaw_of(vx, vz), calls)

    def _move_to(self, x: float, z: float, calls: float = 1.0) -> bool:
        """One frame's step to (x, z), worth ``calls`` MovePC calls: kept on the floor (`walkmesh`), and --
        while sLockTimer is not negative -- pushed out of a body it enters that is in front of him (see
        `blockers`), refused (False, he stays put) when the push-out lands in another. Then the lock's
        count for the frame (CheckCollFallback). Only a body that collides is met: ``coll``, and within
        400 of him in y (WalkMesh.Collision's pair rule and its |dy| band)."""
        ox, oz = self.player[0], self.player[2]
        if (x, z) != (ox, oz):
            m = ((x - ox) ** 2 + (z - oz) ** 2) ** 0.5
            self._facing = ((x - ox) / m, (z - oz) / m)
        bodies = [(d["x"], d["z"], d["r"], bool(d.get("solid")), i) for i, d in self._bodies()
                  if d.get("coll", True) and abs(float(d.get("y", 0.0)) - self.player[1]) < 400]
        pushed = False
        for b in bodies:
            bx, bz, r = b[0], b[1], b[2]
            d = ((x - bx) ** 2 + (z - bz) ** 2) ** 0.5
            if d >= r:
                continue
            self.contacts.append({"frame": self.frame, "uid": self._uid(b[4])})
            self._lock_free = 0 if b[3] else 1
            if not self._lock_free:
                self._lock = 0.0
            # facing = the step (the engine lerps toward it); the push-out wants the body within +-90 deg
            if self._lock >= 0 and (x - ox) * (bx - x) + (z - oz) * (bz - z) >= 0:
                if d < 1e-6:
                    self._lock_fallback(calls)
                    return False
                x, z = bx + (x - bx) / d * r, bz + (z - bz) / d * r
                self._coll = COLL_TICKS
                pushed = True
            break                                   # WalkMesh.Collision answers with ONE body
        on = getattr(self.walkmesh, "point_on_walkmesh", None)
        if on is not None and self.clearance is not None:
            # his centre kept `clearance` off every wall -- pushed out onto that line where he stands closer (placed
            # there), or, where no push lands him on it, never closer still: the step stops on that line, and its
            # rest slides on along the wall
            def wall(px, pz):
                d = self.walkmesh.distance_to_boundary(int(round(px)), int(round(pz)))
                return -1.0 if d is None or on(int(round(px)), int(round(pz))) is None else d
            least = max(0.0, min(self.clearance, wall(ox, oz)))     # off the mesh (an arrival): onto it

            def floor(px, pz):
                return wall(px, pz) >= least
            if not floor(x, z):
                lo, hi = 0.0, 1.0
                for _ in range(16):
                    mid = (lo + hi) / 2
                    lo, hi = (mid, hi) if floor(ox + (x - ox) * mid, oz + (z - oz) * mid) else (lo, mid)
                bx, bz = ox + (x - ox) * lo, oz + (z - oz) * lo
                # the rest of the step, slid along the wall: its component along the nearest bearing (15-degree
                # steps either side) that still stands -- the engine keeps the part of a step along the wall
                import math
                rx, rz = x - bx, z - bz
                x, z = bx, bz
                for deg in (15, 30, 45, 60, 75):
                    c = math.cos(math.radians(deg))
                    for s in (math.sin(math.radians(deg)), -math.sin(math.radians(deg))):
                        px, pz = bx + (rx * c - rz * s) * c, bz + (rx * s + rz * c) * c
                        if floor(px, pz):
                            x, z = px, pz
                            break
                    else:
                        continue
                    break
            if 0.0 <= wall(ox, oz) < self.clearance and 0.0 <= wall(x, z) < self.clearance:
                # placed nearer a wall than his radius (a scene's own spot): where the step ends -- kept on the floor
                # above, as the engine's triangle walk keeps it -- is pushed straight out onto the radius line, as the
                # engine pushes it on his first moving frame
                x, z = self._pushed_out(x, z, wall) or (x, z)
        elif on is not None:
            # a real walkmesh: his centre must stand on it -- a step off keeps whichever one axis of it
            # still does (a crude slide along the edge), or he stays put
            def floor(px, pz):
                return on(int(round(px)), int(round(pz))) is not None
            if not floor(x, z):
                x, z = next(((px, pz) for px, pz in ((x, oz), (ox, z)) if floor(px, pz)), (ox, oz))
        else:
            boxes = self.walkmesh if isinstance(self.walkmesh[0], (tuple, list)) else [self.walkmesh]
            if not any(b[0] <= x <= b[2] and b[1] <= z <= b[3] for b in boxes):
                x0, z0, x1, z1 = next((b for b in boxes if b[0] <= ox <= b[2] and b[1] <= oz <= b[3]), boxes[0])
                x, z = min(max(x, x0), x1), min(max(z, z0), z1)
        if pushed and any((x - b[0]) ** 2 + (z - b[1]) ** 2 < (b[2] - 1e-6) ** 2 for b in bodies):
            self._lock_fallback(calls)
            return False
        self.player[0], self.player[2] = x, z
        self._lock_fallback(calls)
        return True

    def _pushed_out(self, x: float, z: float, wall):
        """Where the engine's push off the walls puts a centre standing nearer one than his radius: straight away from
        it, onto the radius line (FieldMapActorController.RadiusValid -> ServiceForces: one force lands it exactly
        there, several are averaged). Modelled as the move to ``clearance`` off every wall along whichever of 64
        bearings stands it furthest off them, over floor all the way -- again from there while a second wall holds
        it (a corner: 352's pocket between strip and back wall takes five). None when no bearing gets further out:
        the caller keeps its never-closer-still rule."""
        import math
        for _ in range(16):                         # each round nearer the line, or it gives up
            d = wall(x, z)
            if d >= self.clearance:
                return x, z
            r = self.clearance - d + 0.5
            best = None
            for k in range(64):
                ux, uz = math.cos(k * math.pi / 32), math.sin(k * math.pi / 32)
                if any(wall(x + ux * r * s / 8, z + uz * r * s / 8) < 0 for s in range(1, 9)):
                    continue                            # off the floor on the way: not a push he gets
                there = wall(x + ux * r, z + uz * r)
                if best is None or there > best[0]:
                    best = (there, x + ux * r, z + uz * r)
            if best is None or best[0] <= d:
                return None
            x, z = best[1], best[2]
        return (x, z) if wall(x, z) >= self.clearance else None

    def _lock_fallback(self, calls: float) -> None:
        """FieldMapActorController.CheckCollFallback, ``calls`` times over: while SCollTimer runs, count
        sLockTimer up by sLockFree -- flipping it to -25 at 25, which turns the push-out off -- else
        reset a non-negative count to 0 and count a negative one back up to it. WHOLE calls (a quantized run tick's
        two) are counted one at a time, as the engine calls it once a MovePC -- so the flip at 25 lands on the call
        that reaches it; a mean frame's share of a call (half a call a walked frame at 60 fps) is counted at once."""
        n = round(calls)
        if n > 1 and abs(calls - n) < 1e-9:
            for _ in range(n):
                self._lock_call(1.0)
        else:
            self._lock_call(calls)

    def _lock_call(self, calls: float) -> None:
        """One CheckCollFallback, worth ``calls`` MovePC calls (see :meth:`_lock_fallback`)."""
        if self._coll > 0:
            self._lock = -25.0 if self._lock >= 25 else self._lock + self._lock_free * calls
        elif self._lock >= 0:
            self._lock = 0.0
        else:
            self._lock = min(0.0, self._lock + calls)

    # -- the field's other actors (s89) ---------------------------------------------------------
    def _bodies(self) -> list:
        """This field's `blockers` as ``(index, dict)`` -- a tuple is ``(x, z, r[, solid])``."""
        out = []
        for i, b in enumerate(self.blockers.get(self.field_id, ())):
            if not isinstance(b, dict):
                b = {"x": b[0], "z": b[1], "r": b[2], "solid": len(b) > 3 and bool(b[3])}
            out.append((i, b))
        return out

    def _uid(self, i: int) -> int:
        b = self.blockers.get(self.field_id, ())[i]
        return int(b.get("uid", 128 + i)) if isinstance(b, dict) else 128 + i

    @staticmethod
    def _walking(b: dict) -> bool:
        return bool(b.get("path")) and float(b.get("speed", 0)) > 0 and not b.get("_done")

    def _step_walkers(self, ticks: float) -> None:
        """Every walker (a body with a ``path``) one tick along it (or, in mean mode, the frame's share of one:
        ``ticks``) -- ``speed / WALKER_FRAME_TICKS`` units a tick, MoveToward's step a tick -- unless that step would
        bring it within ``r`` of the player, where it waits, still moving (MoveToward.cs:187-189)."""
        for _i, b in self._bodies():
            if not self._walking(b):
                continue
            path = b["path"]
            k = b.setdefault("_k", 1 if len(path) > 1 else 0)
            tx, tz = path[k]
            dx, dz = tx - b["x"], tz - b["z"]
            dist = (dx * dx + dz * dz) ** 0.5
            step = min(float(b["speed"]) * (ticks / WALKER_FRAME_TICKS), dist)
            nx, nz = (b["x"] + dx / dist * step, b["z"] + dz / dist * step) if dist > 0 else (tx, tz)
            px, pz = self.player[0], self.player[2]
            near = ((nx - px) ** 2 + (nz - pz) ** 2) ** 0.5
            if near < b["r"] and near < ((b["x"] - px) ** 2 + (b["z"] - pz) ** 2) ** 0.5:
                continue                                   # held by him
            b["x"], b["z"] = nx, nz
            if step < dist:
                continue
            if len(path) < 2 or (b.get("once") and k == len(path) - 1):
                b["_done"] = True
                continue
            way = b.setdefault("_way", 1)
            if not 0 <= k + way < len(path):
                way = b["_way"] = -way
            b["_k"] = k + way

    def _fire_contacts(self) -> None:
        """CollisionRequest, modelled for the triggers it can fire: his centre inside a body's ``range_r`` (the
        mode-2 search: the pair rule, so only while ``coll``; |dy| < 400), or -- for an entry with both
        functions -- inside ``talk_r`` while he faces it (+-90 degrees). Logged once per entry into the radius
        (`touched`); a ``"to"`` makes it an ExitField, control taken now and the field changed a fade later."""
        px, pz = self.player[0], self.player[2]
        for i, b in self._bodies():
            rr, tr = b.get("range_r"), b.get("talk_r")
            if rr is None or abs(float(b.get("y", 0.0)) - self.player[1]) >= 400:
                continue
            dx, dz = b["x"] - px, b["z"] - pz
            dist = (dx * dx + dz * dz) ** 0.5
            kind = "range" if b.get("coll", True) and dist < rr else None
            if kind is None and tr is not None and dist < tr and dx * self._facing[0] + dz * self._facing[1] > 0:
                kind = "talk"
            key = (self.field_id, i)
            if kind is None:
                self._in_trigger.discard(key)
                continue
            if key in self._in_trigger:
                continue
            self._in_trigger.add(key)
            self.touched.append({"frame": self.frame, "field": self.field_id, "uid": self._uid(i), "kind": kind,
                                 "executed": len(self.executed)})
            if b.get("to") is not None and self._exit is None:
                self.control = False
                self._coast = None
                self._exit = (self.frame + self.exit_frames, int(b["to"]), tuple(b.get("arrive", (0, 0))))
                self._arrive_control = True
                if self.exit_frames <= 0:
                    self._step_exit_now()
                return

    def _objects_doc(self) -> list:
        """``objects`` as the s89 agent publishes it, for this field's bodies."""
        out = []
        for i, b in self._bodies():
            coll = bool(b.get("coll", True))
            rr, tr = b.get("range_r"), b.get("talk_r")
            shown = bool(b.get("shown", True))
            out.append({"uid": self._uid(i), "sid": int(b.get("sid", 10 + i)),
                        "x": float(b["x"]), "y": float(b.get("y", 0.0)), "z": float(b["z"]),
                        "range": rr is not None, "talk": tr is not None,
                        "r": float(b["r"]), "solid": coll and bool(b.get("solid")), "coll": coll,
                        "range_r": float(rr) if rr is not None and coll else None,
                        "talk_r": float(tr) if tr is not None else None,
                        "shown": shown, "moving": self._walking(b),
                        "flags": (1 if shown else 0) | (0 if coll else 14) | (16 if b.get("solid") else 0)})
        return out

    def _enter_freezes(self) -> None:
        """A step into one of this field's `freezes` zones holds movement from the next frame on."""
        x, z = self.player[0], self.player[2]
        for i, f in enumerate(self.freezes.get(self.field_id, ())):
            if (self.field_id, i) not in self._froze and _in_poly(x, z, f["zone"]):
                self._froze.add((self.field_id, i))
                n = f.get("frames")
                self._frozen_ticks = float("inf") if n is None else self.ticks_run + int(n) * WALKER_FRAME_TICKS
                self._coast = None

    def _region_at(self, x: float, z: float):
        """The region that ANSWERS for a centre at (``x``, ``z``): the first of this field's `regions` containing it
        (TreadQuad's first match) -- by its engine polygon ``points`` (content.doorface.region_contains) when it has
        one, else by the even-odd test on its ``zone`` -- or None."""
        from ff9mapkit.content import doorface
        for r in self.regions.get(self.field_id, ()):
            pts = r.get("points")
            if doorface.region_contains(x, z, pts) if pts is not None else _in_poly(x, z, r["zone"]):
                return r
        return None

    def _faces(self, r: dict) -> bool:
        """Whether region ``r``'s facing gate lets it fire now: True when it has none (no ``"face"``); else
        content.doorface.door_faced of his centre and `_face_deg` against its first edge (``points`` when it has
        them, else ``zone``), with the stock window for ``"face": True`` or the given ``[lo, hi]``."""
        face = r.get("face")
        if not face:
            return True
        from ff9mapkit.content import doorface
        q = r.get("points") or r["zone"]
        window = doorface.FACE_WINDOW if face is True else (int(face[0]), int(face[1]))
        return doorface.door_faced(self.player[0], self.player[2], self._face_deg, q[0], q[1], window)[0]

    def _enter_regions(self) -> None:
        """ExitField, modelled: a step into one of this field's `regions` takes control now and
        schedules the field change (see `regions`) -- when the region that answers (the first containing
        him) is live (``to`` not None) and, if gated (``face``), faced. A region that answers without firing
        ends the search: no region after it is tried."""
        if not self.control or self._exit is not None:
            return
        r = self._region_at(self.player[0], self.player[2])
        if r is None or not self._faces(r):
            return
        if r.get("take"):
            # a walk-in trigger (see `regions`): its tag 2 takes control this tick, and nothing warps
            self.fired.append({"frame": self.frame, "from": self.field_id, "to": None,
                               "executed": len(self.executed)})
            self.control = False
            self._coast = None
            return
        if r.get("to") is None:
            return
        self.fired.append({"frame": self.frame, "from": self.field_id, "to": int(r["to"]),
                           "executed": len(self.executed)})
        self.control = False
        self._coast = None
        self._exit = (self.frame + self.exit_frames, int(r["to"]), tuple(r["arrive"]))
        self._arrive_face = r.get("arrive_face")
        self._arrive_control = bool(r.get("arrive_control", True))
        if self.exit_frames <= 0:
            self._step_exit_now()

    def _retest_gated(self) -> None:
        """CollisionRequest on a frame he STANDS -- nothing held and no coast, or frozen: the engine runs the tag 2
        of the region he stands in every tick he has control (EventEngine.ProcessEvents.cs:174-178 at stock
        6b8bb2d5, then EventCollision.cs:281-284), so a gated door whose
        facing a blocked press has turned fires without a step. Only when the answering region IS gated (see
        `regions`: ungated regions keep the step-only rule)."""
        if not self.control or self._exit is not None:
            return
        r = self._region_at(self.player[0], self.player[2])
        if r is not None and r.get("face"):
            self._enter_regions()

    def _step_exit_now(self) -> None:
        _due, dest, arrive = self._exit
        self._exit = None
        self.field_id = dest
        self._visit += 1
        self.player = [float(arrive[0]), 0.0, float(arrive[1])]
        if self._arrive_face is not None:          # the firing region's ``arrive_face`` (see `regions`)
            self._face_deg = float(self._arrive_face)
            self._arrive_face = None
        self._in_trigger.clear()
        self._coast = None
        self.control = self._arrive_control        # the firing region's ``arrive_control`` (see `regions`)
        self._arrive_control = True

    # -- the in-place turn (memoria-patch s90) ------------------------------------------------------
    # Modelled as the agent's CONTRACT (the s90 DRIVER.md, and where they differ HarnessAgent.cs: BeginTurn,
    # ServiceTurn, EndTurn, TurnBlocker, ClaimForMove): the refusals, in the agent's order and words, raised
    # through the ordinary error path; the keys held with no axis, so he turns and never steps
    # (:meth:`_turn_in_place`); the report held until the field has judged the final facing, a door that fires in
    # those passes reported as the `control` that took him. Not the engine's float noise: a turn in place moves him
    # exactly 0, unless a push-out does (then ``moved`` says how far).
    def _on_field(self) -> bool:
        """A field is up with a controlled character: what the agent publishes ``player.yaw`` / ``face`` on."""
        return (self.field_id > 0 and self.ui_state not in ("Title", "WorldHUD", "BattleHUD")
                and not self.battle_active and self.has_position)

    def _turn_blocker(self) -> str | None:
        """HarnessAgent.TurnBlocker's token -- why the field would not honour a turn now -- for the fake's world,
        in the agent's order: ``field`` (no field up), ``player`` (no controlled character: `has_position` off),
        ``control``, ``movement`` (a hold on movement, `_frozen`), ``hud`` (a UI other than the field HUD);
        None when it would."""
        if self.field_id <= 0 or self.ui_state in ("Title", "WorldHUD", "BattleHUD") or self.battle_active:
            return "field"
        if not self.has_position:
            return "player"
        if not self.control:
            return "control"
        if self._frozen():
            return "movement"
        if self.ui_state != "FieldHUD":
            return "hud"
        return None

    def _turn_keys_from(self, frame: int) -> set:
        """The turn keys down on ``frame`` or any later one (HarnessAgent.TurnKeysFrom: down on [down, up))."""
        return {b for b in self._turn_keys if self.held.get(b, -1) > frame}

    def _begin_turn(self, dirs: list, frames: int) -> None:
        """``turn`` (HarnessAgent.BeginTurn): every refusal raises before anything is pressed, in the agent's order
        and words -- no field / player / control / movement / HUD; the last turn still being judged; a turn in
        progress on another visit; `analog_control` off; any direction down now or on a later frame (the turn's own
        keys exempt while composing onto it); opposite directions (turn keys still down counted); a human's `stick`
        over STICK_THRESHOLD, or a `click_path` pending; a collidable body he overlaps. Then the turn is committed --
        its start kept while its keys are down, so two turns sent while the first's keys are down compose into one
        report -- and each key is held by `_extend`, as `hold` holds."""
        import math
        why = self._turn_blocker()
        if why is not None:
            raise RuntimeError(f"needs a field with a controlled player under user control ({why})")
        f = self.frame
        t = self._turn_open
        if t is not None and (t["lift"] is not None or not self._turn_keys_from(f)):
            raise RuntimeError("the last turn's keys are up and the field is still judging it -- wait for its turn_end")
        if t is not None and (t["field"] != self.field_id or t["visit"] != self._visit):
            raise RuntimeError("the turn in progress began on another actor or field -- it is cut this frame; turn "
                               "again after its turn_end")
        if not self.analog_control:
            raise RuntimeError("[AnalogControl] Enabled=0 -- MovePC's key path would step him, not turn him")
        fresh = self._turn_open is None
        for d in ("up", "down", "left", "right"):
            if not fresh and d in self._turn_keys:
                continue
            if self._is_held(d) or self.held.get(d, -1) > f + 1:
                raise RuntimeError(f"{d.capitalize()} is held or scheduled -- release it (and let it lift) first")
        every = self._turn_keys_from(f + 1) | set(dirs)
        if {"up", "down"} <= every or {"left", "right"} <= every:
            raise RuntimeError("opposite directions cancel to no direction")
        if self.stick > STICK_THRESHOLD:
            raise RuntimeError(f"a physical stick or key is pushing the axis (|a| {_fmt(self.stick)}) -- MovePC's "
                               f"axis branch would walk him")
        if self.click_path:
            raise RuntimeError("a click-to-move path is pending -- the turn keys would consume it")
        px, py, pz = self.player
        for i, b in self._bodies():
            if (b.get("coll", True) and abs(float(b.get("y", 0.0)) - py) < 400
                    and math.hypot(b["x"] - px, b["z"] - pz) < b["r"]):
                raise RuntimeError(f"overlapping object uid {self._uid(i)} -- a turn toward it would push him out")
        if fresh:
            self._turn_open = {"from": f + 1, "lift": None, "field": self.field_id, "visit": self._visit,
                               "x": px, "y": py, "z": pz, "yaw0": self._face_deg, "passes": 0}
        self._turn_keys = self._turn_keys_from(f) | set(dirs)
        for d in dirs:
            self._extend(d, frames)

    def _claim_for_move(self, button: str) -> None:
        """``hold`` / ``press`` of a DIRECTION while a turn is open (HarnessAgent.ClaimForMove): refused -- it would
        hand MovePC an axis inside what the driver believes is a turn in place, or a walk inside the passes the field
        judges it on; refused too while a turn key is still down when this key would go down. Otherwise the key's
        stale turn bit is dropped, so the hold feeds the axis. Any other button passes."""
        if button not in ("up", "down", "left", "right"):
            return
        if self._turn_open is not None:
            raise RuntimeError("a `turn` is still open (its keys down, or up and being judged) -- wait for its "
                               "turn_end")
        if self._turn_keys_from(self.frame + 1) or (button in self._turn_keys and self._is_held(button)):
            raise RuntimeError("a `turn` key is still down -- release it (and let it lift) first")
        self._turn_keys.discard(button)

    def _service_turn(self) -> None:
        """Once a frame, after the world's (HarnessAgent.ServiceTurn): end, or cut, the turn being reported. While its
        keys are down it is CUT the moment the field stops honouring it (`_turn_blocker`, the field id or the visit
        changing, a human's `stick` over STICK_THRESHOLD: ``axis``) -- `turn_end` with that token, the keys lifted on
        the next frame by the release rule. Once they
        lift, the report stays open `turn_settle_passes` passes after the lift frame (frames that ran a tick -- every
        frame in mean mode; or under `tick_phase` the tick frames) under the same tests: a gated door that fires on the
        final facing takes
        control, and is reported as that ``control``; ``ended`` means the field ran its passes on that facing and
        nothing took him."""
        f = self.frame
        t = self._turn_open
        if t is None:
            if self._turn_keys and not self._turn_keys_from(f):
                self._turn_keys = set()             # a cut turn's keys have lifted: the bits are stale
            return
        down = bool(self._turn_keys_from(f))
        if not down and t["lift"] is None:
            t["lift"], t["passes"] = f, 0           # the facing is final; the field's next passes read it
            self._turn_keys = set()
        why = self._turn_blocker()
        if why is None and self.field_id != t["field"]:
            why = "field"
        if why is None and self._visit != t["visit"]:
            why = "player"
        if why is None and self.stick > STICK_THRESHOLD:
            why = "axis"                            # a human's stick crossed the threshold: he would walk
        if why is None:
            if down:
                return
            # a frame that RAN a pass counts once (HarnessAgent.ServiceTurn): every frame of mean ticks, a frame that
            # ran a whole tick when quantized, and under tick_phase its tick frames
            if f > t["lift"] and self._frame_steps() and (self.tick_phase is None or f % 2 == self.tick_phase):
                t["passes"] += 1
            if t["passes"] < self.turn_settle_passes:
                return
            why = "ended"
        if not down:
            self._end_turn(why, t["lift"] - t["from"])
            return
        for b in list(self._turn_keys):             # lifted by the release rule: never a press
            if self.held.get(b, -1) <= f:
                continue
            if f >= self.down_at.get(b, 1 << 30):
                self.held[b] = f + 1
            else:
                self.held.pop(b, None)
                self.down_at.pop(b, None)
        self._end_turn(why, f + 1 - t["from"])

    def _end_turn(self, why: str, frames: int) -> None:
        """``turn_end`` (HarnessAgent.EndTurn), every value but ``frame`` a STRING as the agent's event writer quotes
        them: ``why``, ``frames`` (the frames its keys were down), ``yaw0`` / ``yaw`` (degrees, "0.###"), ``face``
        (content.doorface.facing_byte of the yaw) and ``moved`` (3-D distance from the start) -- the last three null
        off a field or on another field id or visit than the turn began on."""
        import math
        from ff9mapkit.content import doorface
        t = self._turn_open
        same = self._on_field() and self.field_id == t["field"] and self._visit == t["visit"]
        yaw = self._face_deg if same else None
        moved = (math.sqrt((self.player[0] - t["x"]) ** 2 + (self.player[1] - t["y"]) ** 2
                           + (self.player[2] - t["z"]) ** 2) if same else None)
        self._event("turn_end", why=why, frames=max(0, int(frames)), yaw0=_fmt(t["yaw0"]), yaw=_fmt(yaw),
                    face=None if yaw is None else doorface.facing_byte(yaw), moved=_fmt(moved))
        self._turn_open = None

    def _check_soft_reset(self) -> None:
        """All six buttons reporting a DOWN EDGE on the same frame sends the game to the title.

        The real handler closes every dialog, hides the HUD, disables all button groups and the
        battle menu, un-pauses, normalises btl_seq and replaces the scene with Title -- which is why
        it is the only recovery rung that reaches a battle or a stuck menu. What matters for the
        driver is the observable end state, so that is what this models.

        WHERE IT FIRES is `soft_reset_ui` (H9, research/o3_design.md 0.2 #9). The reset is held through
        ``UIKeyTrigger.GetKey``, which answers false outside FieldHUD / WorldHUD / BattleHUD / QuadMistBattle
        (UIKeyTrigger.cs:94) -- so in the ENGINE it fires from BattleHUD mid-fight (on the combo's second held frame:
        the down frame's Select is the menu handler's) and NEVER from BattleResult: the battle's end sequence swallows
        it. The default here is the narrower pair every test before H9 was written against; a test that models the
        engine passes :data:`SOFT_RESET_ENGINE_UI`, and a reset from BattleHUD then ends the battle with the scene.
        And while a MOVIE plays (a scene's movie beat, its skip dialog included) the combo is swallowed whatever the
        set says: ``HandleBoosterButton``, which holds the reset, returns at once while MBG is marked played
        (UIKeyTrigger.cs:241, MBG.cs:607-610).
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
        if self._movie is not None or self.ui_state not in self.soft_reset_ui:
            return
        if self.ui_state == "BattleHUD":
            # mid-fight, from a set that holds it: the battle goes with the scene -- nothing of it is up at the title
            self.battle_active = False
            self.commands_enabled = False
            self._tutorial = False
            self._bexit = self._script_end = None
            self.battle_pending = []
        self.soft_resets += 1
        self.ui_state = "Title"
        self.field_id = -1
        self.control = False
        self.texts = []
        self.raw_texts = []
        self.choice = None
        self._beats, self._beat_phase = [], None
        self.menu = {"selected": None, "hovered": None, "label": None, "group": None}
        self.menu_entries = []
        self.player = [0.0, 0.0, 0.0]
        # ⚠ NOT held.clear(). FF9's handler does not release the player's buttons, and a stand-in
        # that did would make `reset_agent` -- the thing that actually releases them -- untestable:
        # it could be reduced to a no-op with every test still green.
        self._event("soft_reset")

    # -- the battle HUD's cursor ---------------------------------------------------------------
    #: The command list as the HUD lays it out: a TWO-COLUMN grid that does NOT wrap vertically.
    #: Measured live 2026-09-04 -- from `Steal`, `down` reaches `Item` and then moves nothing, and
    #: `Attack` (one row up) is never seen by a one-direction walk. A stand-in whose battle menu
    #: wrapped, or had one column, would certify a battle_pick that cannot find half the commands.
    BATTLE_GRID = [["Attack", "Defend"], ["Steal", "Skill"], ["Item", "Change"]]
    #: What each command opens on confirm (BattleHUD.Const.cs group names). `Attack`/`Steal` go to
    #: the target cursor; `Skill` and `Item` open SUBMENUS -- distinct groups a driver must not
    #: mistake for the target cursor (the first cut confirmed a Potion that way).
    BATTLE_OPENS = {"Attack": "Battle.Target", "Steal": "Battle.Target", "Skill": "Battle.Ability",
                    "Item": "Battle.Item"}
    BATTLE_SUBMENU_ROWS = {"Battle.Item": ["Potion", "Hi-Potion"], "Battle.Ability": ["Flee"]}

    def _open_battle_cursor(self) -> None:
        self._grid_pos = [0, 0]
        self._battle_pending_cmd = None
        self._sub_index = 0
        self._set_battle_cursor("Battle.Command", self.BATTLE_GRID[0][0])

    def _close_battle_cursor(self) -> None:
        self.menu = {"selected": None, "hovered": None, "label": None, "group": None,
                     "button": None, "button_label": None}

    def _set_battle_cursor(self, group: str, label: str) -> None:
        self.menu = {"selected": f"btn_{label}", "hovered": None, "label": label, "group": group,
                     "button": f"btn_{label}", "button_label": label}

    def _battle_menu_step(self, button: str) -> None:
        group = self.menu.get("group")
        if group == "Battle.Command":
            r, c = self._grid_pos
            if button == "down":
                r = min(r + 1, len(self.BATTLE_GRID) - 1)        # clamp: no wrap
            elif button == "up":
                r = max(r - 1, 0)
            elif button == "right":
                c = min(c + 1, len(self.BATTLE_GRID[0]) - 1)
            elif button == "left":
                c = max(c - 1, 0)
            elif button in ("confirm", "ok"):
                label = self.BATTLE_GRID[r][c]
                opens = self.BATTLE_OPENS.get(label)
                if opens is None:
                    # Defend / Change: no target, committed straight away.
                    self._battle_command(self.battle_turn, 2, 177, 0, 0)
                    self._close_battle_cursor()
                    return
                self._battle_pending_cmd = label
                self._sub_index = 0
                if opens == "Battle.Target":
                    foe = next((u for u in self.battle_units
                                if not u["player"] and u["alive"] and u["targetable"]), None)
                    self._set_battle_cursor(opens, foe["name"] if foe else "nobody")
                else:
                    self._set_battle_cursor(opens, self.BATTLE_SUBMENU_ROWS[opens][0])
                return
            self._grid_pos = [r, c]
            self._set_battle_cursor("Battle.Command", self.BATTLE_GRID[r][c])
            return
        if group in ("Battle.Item", "Battle.Ability"):
            rows = self.BATTLE_SUBMENU_ROWS[group]
            if button in ("cancel", "back", "b"):
                self._set_battle_cursor("Battle.Command", self.BATTLE_GRID[self._grid_pos[0]][self._grid_pos[1]])
            elif button == "down":
                self._sub_index = min(self._sub_index + 1, len(rows) - 1)
                self._set_battle_cursor(group, rows[self._sub_index])
            elif button == "up":
                self._sub_index = max(self._sub_index - 1, 0)
                self._set_battle_cursor(group, rows[self._sub_index])
            elif button in ("confirm", "ok"):
                # Picking an item/ability then opens the target cursor, as the HUD does.
                foe = next((u for u in self.battle_units if not u["player"] and u["alive"]), None)
                self._set_battle_cursor("Battle.Target", foe["name"] if foe else "nobody")
            return
        if group == "Battle.Target":
            if button in ("cancel", "back", "b"):
                self._set_battle_cursor("Battle.Command", self.BATTLE_GRID[self._grid_pos[0]][self._grid_pos[1]])
            elif button in ("confirm", "ok"):
                foe = next((u for u in self.battle_units
                            if not u["player"] and u["alive"] and u["targetable"]), None)
                cmd = {"Attack": (1, 176), "Steal": (3, 178)}.get(self._battle_pending_cmd, (8, 1))
                self._battle_command(self.battle_turn, cmd[0], cmd[1], foe["id"] if foe else 0, 0)
                self._close_battle_cursor()

    def _menu_step(self, button: str) -> None:
        if self.ui_state == "Tutorial":
            if button in ("confirm", "ok"):
                self._tutorial = False
                self.ui_state = "BattleHUD"
            return
        if self._beats:
            self._scene_press(button)
            return
        if str(self.menu.get("group") or "").startswith("Battle."):
            self._battle_menu_step(button)
            return
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
        px, py, pz = self._pos_before if self.publish_lag is not None and self.publish_lag(self.frame) else self.player
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
            "sys_mode": 1, "scenario": self.scenario,
            "field": {"id": self.field_id, "name": f"FBG_FAKE_{self.field_id}"},
            "world": dict(self.world),
            # floor/tri mirror s83 faithfully, dead values and all: PosObj's battle-entry snapshot
            # reads 0/0 until the session's first battle (State.player_tri_battle_snapshot).
            "player": {"x": px, "y": py, "z": pz,
                       "dir": 0, "floor": 0, "tri": 0, "control": self.control},
            "input": {"key_up": self._is_held("up"), "key_confirm": self._is_held("confirm"),
                      "move_key": bool(held), "dash_inh": int(self.dash_inhibit), "axis_x": 0.0, "axis_y": 0.0},
            "dialog": {"open": bool(self.texts) or self.choice is not None,
                       "count": len(self.texts),
                       "texts": self.texts, "phrase_raw": self.raw_texts or self.texts,
                       "choice": self.choice},
            "menu": dict(self.menu),
            "battle": self._battle_doc(),
            "flags": {str(b): self._watched_bit(b) for b in self.watch},
            "netsync": self._netsync_doc(),
            "held": held,
        }
        if self.facing_mode == "published":
            # s90: the yaw raw (to 0.001) and the gate's facing byte, both null exactly together -- off a field or with
            # no controlled character; published with or without user control (a scripted turn moves the yaw too)
            from ff9mapkit.content import doorface
            on = self._on_field()
            doc["player"]["yaw"] = round(self._face_deg, 3) if on else None
            doc["player"]["face"] = doorface.facing_byte(self._face_deg) if on else None
        if self.storytrace_proto is not None:
            doc["storytrace"] = {"proto": self.storytrace_proto, "on": self.story_on,
                                 "rows": self.story_rows, "suppressed": 0, "error": self.story_error}
        if self.objects_mode != "absent":
            # s89: both null off a field or on any failure, never a partial list
            listed = self.objects_mode == "listed" and self.ui_state == "FieldHUD"
            doc["objects"] = self._objects_doc() if listed else None
            doc["pushout"] = ({"slock": int(self._lock), "scoll": math.ceil(self._coll - 1e-9),
                               "slockfree": int(self._lock_free), "fallback": True} if listed else None)
        # the clocks (`publish`): the virtual realtime clock and the ticks run, IN the document -- what a driver pairs
        # frames with before it falls back on the file's mtime (harness.tickrate.TickClock)
        if "rt" in self.publish:
            doc["rt"] = self.rt
        if "ticks" in self.publish:
            doc["ticks"] = int(self.ticks_run) if self._tick_mode == "quantized" else self.ticks_run
        stamp = self._wall0 + self.rt if "mtime" in self.publish else None
        if self._publish_stalls:
            _publish_in_place(self.dir / "state.json", json.dumps(doc),
                              stall=self._publish_stalls.pop(0), began=self.stalling,
                              stop=self._stop, mtime=stamp)
        else:
            _publish_atomic(self.dir / "state.json", json.dumps(doc), mtime=stamp)

    def stall_publish(self, seconds: float, *, times: int = 1) -> None:
        """Make the next ``times`` publishes stall MID-REWRITE for ``seconds`` each.

        THE REAL AGENT'S SHAPE, which the ordinary publish here is not. ``HarnessAgent.WriteAtomic``
        writes state.json IN PLACE (``FileMode.Create``: truncate, then the bytes land), so between
        the two the file is EMPTY -- and MEASURED 2026-09-23 with that exact open mode at 60 Hz, the
        gap has a median of 0.7 ms and a p99 of ~80 ms (max ~200 ms, an on-access scan holding the
        rewrite). The channel's own parse retry spans ~30 ms, so a stall past it turned a healthy
        game into "no state published" (studies/platform-land/rung0_land.py, 40-frame ride).

        The frame loop blocks for the stall, as the game's main thread does inside the write. A
        long stall is the game hung INSIDE the publish; ``stop()`` cuts it short, so a test's
        teardown never waits one out.
        """
        self._publish_stalls.extend([float(seconds)] * max(1, int(times)))

    def _event(self, kind: str, **kv) -> None:
        # every value but `frame` a STRING, as the agent's Event() writes them -- or null (its Str of a null)
        row = {"frame": self.frame, "kind": kind}
        row.update({k: None if v is None else str(v) for k, v in kv.items()})
        # buffered first and flushed whole, as HarnessAgent.Event / FlushEvents: an append that fails keeps every row
        # it carried for the next event's append (`event_collisions` makes one fail on purpose)
        self._pending_events.append(json.dumps(row))
        if self.event_collisions.get(kind, 0) > 0:
            self.event_collisions[kind] -= 1
            return
        try:
            with (self.dir / "events.jsonl").open("a", encoding="utf-8") as fh:
                fh.write("\n".join(self._pending_events) + "\n")
            self._pending_events.clear()
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
        self._tutorial = scene in self.tutorial_scenes
        if self._tutorial:
            self.ui_state = "Tutorial"
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
        self._bexit = self._script_end = None     # H9: no end running, and the latch not yet fired, in a new battle
        self._script_latched = False
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
            self._close_battle_cursor()
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
        self._script_latch()
        self._settle_battle()

    def _script_latch(self) -> None:
        """`battle_script_end`'s latch (H9): ONCE a battle, the first time the named unit's ``hp_raw`` is at or below
        ``hp_raw_le`` after a command resolves, the end is due ``after_frames`` later with ``result`` -- whoever is
        standing then (:meth:`_step_battle` ends it)."""
        se = self.battle_script_end
        if se is None or self._script_latched:
            return
        unit = next((u for u in self.battle_units if u.get("name") == se["unit"]), None)
        if unit is not None and int(unit["hp_raw"]) <= int(se["hp_raw_le"]):
            self._script_latched = True
            self._script_end = (self.frame + max(0, int(se.get("after_frames", 0))), int(se["result"]))

    def _settle_battle(self) -> None:
        """End the fight when one side is gone. ⚠ Never under isDebug -- the diorama cannot end."""
        if not self.battle_active or self.battle_debug or self._bexit is not None:
            return
        if not [u for u in self.battle_units if not u["player"] and u["alive"]]:
            self.end_battle(1)
        elif not [u for u in self.battle_units if u["player"] and u["alive"]]:
            self.end_battle(3)

    def _step_battle(self) -> None:
        """One frame of battle: gauges fill, the HUD asks somebody, enemies act, escapes roll. While a `battle_exit`
        end runs, only its phases do (:meth:`_step_battle_exit`); a `battle_script_end` that is due ends the battle."""
        if self._bexit is not None:
            self._step_battle_exit()
            return
        if not self.battle_active:
            return
        if self._script_end is not None and self.frame >= self._script_end[0]:
            result, self._script_end = self._script_end[1], None
            self.end_battle(result)                     # the scripted end: whoever is standing
            return

        # InitialBattle(): the opening camera ends, the HUD resets its turn bookkeeping, and only
        # THEN does the battle start asking for commands.
        if not self.commands_enabled and self.frame >= self._intro_until and not self._tutorial:
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
            self.run_counter += self._dt           # REAL seconds: the frame's, on the virtual clock
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
        if not self.battle_active or self._bexit is not None:      # it ended (with `battle_exit`: the fade began)
            return
        # A character who goes down mid-prompt stops being asked -- the HUD's own
        # _unconsciousStateList / RemovePlayerFromAction. Without this the turn would stay pinned
        # to a corpse and every later wait would time out against it.
        if self.battle_turn >= 0:
            asked = next((u for u in self.battle_units if u["slot"] == self.battle_turn), None)
            if asked is None or not asked["alive"]:
                self.battle_turn = -1
                self._close_battle_cursor()

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
                    self._open_battle_cursor()        # the command list opens on that slot
                    break
        self._settle_battle()

    def _roll(self) -> float:
        """A deterministic pseudo-roll, so a suite does not depend on the clock."""
        self._roll_state = (getattr(self, "_roll_state", 12345) * 1103515245 + 12345) & 0x7FFFFFFF
        return self._roll_state / float(0x7FFFFFFF)

    def end_battle(self, result: int = 1, *, exp: int = 120, gil: int = 88) -> None:
        """Finish the battle. ⚠ Refuses under isDebug, exactly as the engine's auto-end does. With `battle_exit` set
        (H9) the end runs the engine's four phases from here -- the FADE first, the result published at the battle's
        own field (:meth:`_step_battle_exit` runs the rest); without it, today's end: the same field, FieldHUD at
        once. An end already running is not begun again."""
        if self.battle_debug or self._bexit is not None:
            return
        self.battle_result = result
        self.battle_bonus = {"exp": exp, "gil": gil, "ap": 3, "items": 1}
        if self.battle_exit is not None and self.battle_active:
            # (1) the FADE (btl_scrp.cs:785-799: the result set, SEQ_DEFEATCLOSE_FADEOUT begun) -- fldMapNo still the
            # battle's field, the scene still up, the HUD asking nobody
            self._close_battle_cursor()
            self.commands_enabled = False
            self._bexit = ("fade", self.frame + max(0, int(self.battle_exit.get("fade_frames", 0))), result)
            self._exit_mark("fade")
            return
        self.battle_active = False
        self._close_battle_cursor()
        # ⚠ commands_enabled goes false at PHASE_MENU_OFF, but battle_turn does NOT get cleared --
        # the engine leaves it for InitialBattle. That is the stale value the next battle inherits.
        self.commands_enabled = False
        self.ui_state = "FieldHUD"

    def _step_battle_exit(self) -> None:
        """A `battle_exit` end, phase by phase, in the engine's order (research/o3_design.md 0.2 #8): the FADE runs
        out; then ONE call of HonoluluBattleMain.UpdateOverFrame (:721-741) folds a result of 2 into 1 AND sets
        ``fldMapNo`` to the exit field -- the same frame, the scene still up -- and GoToBattleResult (ui BattleResult,
        its InitialEvent hiding every panel); then the scene goes (``battle_active`` False) while the UI still reads
        BattleResult through the load; then FieldHUD in the exit field, a fresh visit, control as ``arrive_control``
        says (the engine zeroes it at every field start: EventEngine.cs:627)."""
        phase, until, result = self._bexit
        if self.frame < until:
            return
        ex = self.battle_exit
        if phase == "fade":
            self.battle_result = 1 if result == 2 else result
            self.field_id = int(ex["field"])
            self.ui_state = "BattleResult"
            self._bexit = ("result", self.frame + 1 + max(0, int(ex.get("result_frames", 0))), result)
            self._exit_mark("over")
        elif phase == "result":
            self.battle_active = False
            self._bexit = ("load", self.frame + max(0, int(ex.get("load_frames", 0))), result)
            self._exit_mark("load")
        else:
            self._bexit = None
            self.ui_state = "FieldHUD"
            self.control = bool(ex.get("arrive_control", False))
            self._visit += 1                       # a fresh load: a new visit's actor
            self._in_trigger.clear()
            self._exit_mark("field")

    def _exit_mark(self, phase: str) -> None:
        """One row of `exits`: the phase a `battle_exit` end entered, and what it publishes there."""
        self.exits.append({"phase": phase, "frame": self.frame, "field": self.field_id, "result": self.battle_result,
                           "active": self.battle_active, "ui": self.ui_state})

    # -- test conveniences ---------------------------------------------------------------------
    # -- the story-write trace (s88) -----------------------------------------------------------
    def _story_row(self, kind: str, **kv) -> None:
        """Append one proto-1 row: the common fields, then the kind's own (StoryTrace.BeginRow)."""
        mode = 3 if self.ui_state == "WorldHUD" else 2 if self.battle_active else 1
        fld = self.field_id
        row = {"k": kind, "f": self.frame, "p": self.frame, "m": mode, "fld": fld,
               "don": fld if self.donor is None else self.donor, "sc": self.scenario, **kv}
        with (self.dir / "story.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
        self.story_rows += 1

    def _story_start(self) -> None:
        if self.story_error is not None:
            raise RuntimeError(f"storytrace: turned itself off earlier ({self.story_error}); re-arm the "
                               f"harness to clear it")
        self.story_on = True
        self._story_row("e", why="arm")

    def _story_stop(self) -> None:
        if not self.story_on:
            return
        self._story_row("e", why="off")
        self.story_on = False

    def _story_store(self, src: str, byte: int, width: str, new: int, *, bit: int = -1,
                     sid: int = -1, tag: int = -1, ip: int = -1) -> None:
        """A store to the modelled gEventGlobal, and -- when tracing -- its `w` row. Only a script row
        names its writer (StoryTrace.AfterStore): cs/harness rows carry -1 attribution."""
        if width == "Bit":
            old = (self.story_bytes[byte] >> (bit & 7)) & 1
            self.story_bytes[byte] = (self.story_bytes[byte] & ~(1 << (bit & 7))) | (new << (bit & 7))
        elif width == "Byte":
            old = self.story_bytes[byte]
            self.story_bytes[byte] = new
        else:
            old = self.story_bytes[byte] | (self.story_bytes[byte + 1] << 8)
            self.story_bytes[byte:byte + 2] = bytes((new & 0xFF, (new >> 8) & 0xFF))
        if not self.story_on:
            return
        script = src == "eb"
        self._story_row("w", src=src, sid=sid if script else -1, uid=sid if script else -1,
                        lvl=0 if script else -1, ip=ip if script else -1, tag=tag if script else -1,
                        add=0, byte=byte, w=width, bit=bit, old=old, new=new, same=int(old == new))

    def _warp_writes(self, entrance: int, scenario: int) -> None:
        """The debug warp's own writes (Ff9mkDebugMenu.ServicePendingWarp): ``entrance`` (when >= 0) as Int16 at byte
        2 (FieldEntrance) and ``scenario`` (when >= 0) as UInt16 at bytes 0-1 (ScenarioCounter, also the published
        ``scenario``), straight into gEventGlobal before the map changes -- no script and no store hook runs, so a
        trace sees them only through its residue net: one ``r`` row (``why`` "frame") per byte that changed,
        stamped with the field he is warping FROM (rung 1: "seen in field 70 before the load")."""
        before = bytes(self.story_bytes[0:4])
        if scenario >= 0:
            v = scenario & 0xFFFF
            self.story_bytes[0:2] = bytes((v & 0xFF, v >> 8))
            self.scenario = scenario
        if entrance >= 0:
            v = entrance & 0xFFFF                      # Int16, two's complement
            self.story_bytes[2:4] = bytes((v & 0xFF, v >> 8))
        if not self.story_on:
            return
        for b in range(4):
            if self.story_bytes[b] != before[b]:
                self._story_row("r", byte=b, old=before[b], new=self.story_bytes[b], why="frame")

    def _watched_bit(self, bit: int) -> bool:
        """A watched bit as the agent publishes it: read from the modelled gEventGlobal (`story_bytes`), which the
        ``flag`` verb, ``byte`` and :meth:`script_store` all write -- so a script's store shows in ``flags``."""
        byte = bit >> 3
        return 0 <= byte < len(self.story_bytes) and bool((self.story_bytes[byte] >> (bit & 7)) & 1)

    def script_store(self, sid: int, tag: int, ip: int, byte: int, width: str, new: int, *,
                     bit: int = -1) -> None:
        """Model a field script's store (an ``eb`` row). ``width`` is ``Bit`` / ``Byte`` / ``UInt16``."""
        self._story_store("eb", byte, width, new, bit=bit, sid=sid, tag=tag, ip=ip)

    def story_fault(self, why: str = "story.jsonl has not accepted an append") -> None:
        """The tracer turning itself off (StoryTrace.Fail): off, no `off` epoch, the reason published."""
        self.story_on = False
        self.story_error = why

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

    def scene(self, *beats, stale: int = 0, opening: int = 6, closing: int = 6, control: bool = True) -> None:
        """Play a scripted scene with control withheld, beat by beat; control comes back after the last -- unless
        ``control`` is False: a scene in a field that never grants it (61-63, research/o3_design.md 0.2 #4), whose
        script moves on with control still off (H9; the default is as it always was). A
        beat is a page (a str) that Confirm turns, or a CHOICE (a dict: ``options``; ``default``, the script's
        defaultChoice -- the ABSOLUTE index its cursor starts on; optionally ``header``, and ``disabled``, the
        absolute indexes the script's mask leaves out; ``typing``, frames its prompt types on once the window
        is ready) that Confirm answers at the cursor, into :attr:`answered`, or the NAMING screen (a dict
        ``{"naming": char}``: ui_state "NameSetting", no dialog; two Confirms keep the default name, into
        :attr:`named`), or a MOVIE (H9: a dict ``{"movie": frames, "skip": {"header", "options"[, "default"]}}``): no
        dialog and no control for ``frames`` frames, ui FieldHUD -- and with ``skip``, a Confirm while it plays opens
        the skip dialog (FieldHUD.cs:275-286), a choice beat with its cursor on No, :data:`SKIP_CURSOR` (``ETb.sChoose
        = 1``, :280) -- a ``default`` given must be that cursor (ValueError here otherwise); answering option 0,
        :data:`SKIP_CHOICE`, ends the movie (:430-433), any other answer resumes it for the frames it had left
        (:434-440). With ``skip``'s opt-in ``armed_after`` (frames) the hit area takes no Confirm until the movie has
        played that far (MBG.Play arms it; no dialog before the first frame). While a movie plays (its dialog up
        included) the soft-reset combo is swallowed, and a warp ends it with its scene (:attr:`movies` records each).

        A choice window as the engine publishes it (recorded at 30937 frames 900/906/936 and 30921): for
        ``opening`` frames it is up with group '' and no button and ``selected`` reads ``stale`` -- whatever
        the pooled window last held (Dialog.selectedChoice survives Reset) -- and it takes no answer; then
        group ``Dialog.Choice``, the cursor on the default (no button when that line is disabled: choiceList
        holds null there), answers taken; after one, ``closing`` frames with group '' again and the choice
        still published, then the next beat. While the prompt TYPES (the window already ready: the engine sets
        the group and the default cursor in AfterShown, with the text still animating) a Confirm only
        finishes the text (Dialog.OnKeyConfirm's TextAnimation branch) and is not an answer.

        Each dict beat is COPIED: a movie keeps its countdown (``_left``) on its beat, and the caller's dict must not
        carry it into the next scene that stages it (a replayed movie would then play no frame at all)."""
        for b in beats:                                  # checked before anything changes: the engine's cursor only
            skip = b.get("skip") if isinstance(b, dict) and "movie" in b else None
            if skip and int(skip.get("default", SKIP_CURSOR)) != SKIP_CURSOR:
                raise ValueError(f"a movie's skip dialog opens with its cursor on No, option {SKIP_CURSOR} (ETb.sChoose "
                                 f"= 1, FieldHUD.cs:280), and skips on option {SKIP_CHOICE} alone (:430): default "
                                 f"{skip['default']!r} models no engine")
        self._beats = [dict(b) if isinstance(b, dict) else b for b in beats]
        self._beat_frames = (int(opening), int(closing))
        self._scene_control = bool(control)
        self.control = False
        self._next_beat(stale)

    def _next_beat(self, stale: int = 0) -> None:
        self.menu = {"selected": None, "hovered": None, "label": None, "group": None}
        self._beat_phase = None
        if not self._beats:
            self.texts, self.raw_texts, self.choice = [], [], None
            self.control = self._scene_control
            return
        beat = self._beats[0]
        if isinstance(beat, str):
            self.say(beat)
            self.choice = None
            return
        if "naming" in beat:
            # NameSettingUI: no dialog, the box focused on the prefilled default name (NameSettingUI.cs:146)
            self.texts, self.raw_texts, self.choice = [], [], None
            self.ui_state, self._name_focus = "NameSetting", True
            return
        if "movie" in beat:
            # H9: a movie -- MBG marked played (`_movie`) from its first frame to its last; resumed with the frames
            # it had left (``_left``) after its skip dialog, ended here when that dialog took the skip
            if "_left" not in beat:
                beat["_left"] = max(0, int(beat["movie"]))
                self._movie = beat
                self.movies.append({"frames": beat["_left"], "start": self.frame, "end": None, "played": 0,
                                    "skips": 0, "ended": None})
            if beat["_left"] <= 0:
                if self._movie is beat:
                    self._movie_over("played")
                self._beats.pop(0)
                self._next_beat()
                return
            self.texts, self.raw_texts, self.choice = [], [], None
            self._beat_phase = "movie"
            return
        header = beat.get("header", "What now?")
        disabled = list(beat.get("disabled", ()))
        active = [i for i in range(len(beat["options"])) if i not in disabled]
        shown = [beat["options"][i] for i in active]
        self.say("\n".join([header, *shown]))
        self.choice = {"selected": stale, "count": len(beat["options"]), "active": active, "disabled": disabled,
                       "options": [header, *shown]}
        self.menu = {"selected": None, "hovered": None, "label": None, "group": "", "button": None}
        self._beat_phase, self._beat_until = "opening", self.frame + self._beat_frames[0]

    def _choice_cursor(self, index: int) -> None:
        self.choice["selected"] = index
        button = None if index in self.choice["disabled"] else f"Choice#{index}"
        self.menu = {"selected": button, "hovered": None, "label": None, "group": "Dialog.Choice", "button": button}

    def _movie_over(self, how: str) -> None:
        """The playing movie ends (``how``: "played", "skipped" or "warp"): MBG no longer marked played."""
        self._movie = None
        if self.movies and self.movies[-1]["end"] is None:
            self.movies[-1].update(end=self.frame, ended=how)

    def _end_scene(self, why: str) -> None:
        """A scene cut short (a warp's field load): its movie ended, every beat dropped, its window closed."""
        if self._movie is not None:
            self._movie_over(why)
        self._beats, self._beat_phase = [], None
        self.texts, self.raw_texts, self.choice = [], [], None
        self.menu = {"selected": None, "hovered": None, "label": None, "group": None}

    def _step_scene(self) -> None:
        """A choice window's frame-driven phases: opening -> ready, closing -> the next beat; and a playing movie's
        frames (H9), the next beat when they run out."""
        if self._beats and self._beat_phase == "movie":
            beat = self._beats[0]
            beat["_left"] -= 1
            self.movies[-1]["played"] += 1
            if beat["_left"] <= 0:
                self._movie_over("played")
                self._beats.pop(0)
                self._next_beat()
            return
        if not self._beats or self._beat_phase not in ("opening", "closing") or self.frame < self._beat_until:
            return
        if self._beat_phase == "opening":
            self._beat_phase = "ready"
            self._choice_cursor(int(self._beats[0]["default"]))
            self._typing_until = self.frame + int(self._beats[0].get("typing", 0))
            self.readied.append(len(self.executed))
        else:
            self._beats.pop(0)
            self._next_beat()

    def _scene_press(self, button: str) -> None:
        """A press during a scene: Confirm turns a page or answers a READY choice; up/down move a ready
        choice's cursor over the enabled lines, clamped (Dialog.MoveCurrentChoice); nothing else acts."""
        if isinstance(self._beats[0], str):
            if button in ("confirm", "ok"):
                self._beats.pop(0)
                self._next_beat()
            return
        if "naming" in self._beats[0]:
            # the first Confirm takes focus off the box, the next is OK and saves (NameSettingUI.cs:72-83, :107,
            # :173); Cancel puts focus back on the box
            if button in ("confirm", "ok") and self._name_focus:
                self._name_focus = False
            elif button in ("confirm", "ok"):
                self.named.append(int(self._beats[0]["naming"]))
                self.ui_state = "FieldHUD"
                self._beats.pop(0)
                self._next_beat()
            elif button in ("cancel", "back", "b"):
                self._name_focus = True
            return
        if "movie" in self._beats[0]:
            # H9: a Confirm during a movie with a skip dialog opens it (FieldHUD.cs:275-286), the cursor on No
            # (SKIP_CURSOR: ETb.sChoose = 1, whatever the fixture's text); the movie waits under it with the frames it
            # has left. Opt-in (``armed_after``, frames; default 0, the hit area live from the first frame): the hit
            # area arms only that far into the movie -- MBG.Play sets it active (MBG.cs:207), and until the first frame
            # decodes MBG.IsFinished() refuses the dialog (:597-600) -- so a Confirm before then does nothing to it
            beat = self._beats[0]
            if button in ("confirm", "ok") and beat.get("skip") and self._beat_phase == "movie":
                skip = beat["skip"]
                if self.movies[-1]["played"] < int(skip.get("armed_after", 0)):
                    return
                self.movies[-1]["skips"] += 1
                self._beats.insert(0, {"header": skip.get("header", ""), "options": list(skip["options"]),
                                       "default": SKIP_CURSOR, "_movie": beat})
                self._next_beat()
            return
        if self._beat_phase != "ready":
            return
        if button in ("confirm", "ok") and self.frame < self._typing_until:
            self._typing_until = self.frame              # the text completes; nothing is answered
        elif button in ("confirm", "ok"):
            self.answered.append(int(self.choice["selected"]))
            movie = self._beats[0].get("_movie")
            if movie is not None and int(self.choice["selected"]) == SKIP_CHOICE:
                # the engine's own rule, never the fixture's default: choice 0 skips (FieldHUD.cs:430-433) and the
                # movie ends under its closing dialog; any other answer resumes it (:434-440)
                movie["_left"] = 0
                self._movie_over("skipped")
            self.menu = {"selected": None, "hovered": None, "label": None, "group": "", "button": None}
            self._beat_phase, self._beat_until = "closing", self.frame + self._beat_frames[1]
        elif button in ("up", "down"):
            active = self.choice["active"]
            at = active.index(self.choice["selected"]) if self.choice["selected"] in active else 0
            at = max(0, min(len(active) - 1, at + (1 if button == "down" else -1)))
            self._choice_cursor(active[at])

    def open_menu(self, entries: list[str], group: str = "MainMenu") -> None:
        self.ui_state = "MainMenu"
        self.menu_entries = list(entries)
        self.menu_index = 0
        self.menu = {"selected": "Button0", "hovered": None,
                     "label": entries[0] if entries else None, "group": group}


def _control(name: str) -> str:
    """A ``press`` / ``hold`` / ``release`` button as the agent keys it (HarnessAgent.ParseControl): the direction
    aliases ``north`` / ``south`` / ``west`` / ``east`` ARE ``up`` / ``down`` / ``left`` / ``right`` -- one Control,
    one held key: a ``hold north`` walks him up, and a ``turn`` refuses it as the Up it is. The other buttons keep the
    name they were sent as (nothing in the fake tells their aliases apart)."""
    return DIRECTIONS.get(str(name).lower(), name)


def _turn_directions(arg: str) -> list:
    """``up``, ``up+right``, ... as the agent parses a ``turn``'s directions (HarnessAgent.ParseTurnDirections over
    ParseControl): ``+``-joined names or aliases, directions only, each to its Control name -- and its refusals in its
    words."""
    if not arg:
        raise RuntimeError("needs a direction (up|down|left|right, '+'-joined)")
    out = []
    for part in arg.split("+"):
        name = part.lower()
        if name not in BUTTONS:
            raise RuntimeError(f"unknown button '{part}'")
        if name not in DIRECTIONS:
            raise RuntimeError(f"'{part}' is not a direction (up|down|left|right, '+'-joined)")
        out.append(DIRECTIONS[name])
    return out


def _fmt(v) -> str | None:
    """A float as the agent's Fmt writes it: C#'s ``"0.###"`` -- at most three decimals, no trailing zeros -- or None
    for a missing one."""
    if v is None:
        return None
    s = f"{float(v):.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _in_poly(x: float, z: float, poly) -> bool:
    """(x, z) inside polygon ``poly`` ([[x, z], ...]), even-odd rule -- the stand-in's IsInQuad."""
    inside = False
    n = len(poly)
    for i in range(n):
        ax, az = poly[i]
        bx, bz = poly[(i + 1) % n]
        if (az > z) != (bz > z) and x < ax + (z - az) * (bx - ax) / (bz - az):
            inside = not inside
    return inside


def _stamp(path: Path, mtime: float | None) -> None:
    """Set ``path``'s modified time to ``mtime`` (epoch seconds) -- the fake's VIRTUAL write time, when it publishes
    "mtime" -- or leave the real one (None). A stamp that cannot land costs one sample's time, never the publish."""
    if mtime is None:
        return
    try:
        ns = int(round(mtime * 1e9))
        os.utime(path, ns=(ns, ns))
    except OSError:
        pass


def _publish_atomic(path: Path, text: str, attempts: int = 6, *, mtime: float | None = None) -> None:
    """Replace ``path`` atomically, retrying the Windows sharing violation.

    ``os.replace`` fails with ERROR_ACCESS_DENIED whenever the reader happens to have the target
    open at that instant -- a real collision at a 60 Hz write against a 30 Hz poll, not a theoretical
    one. Retry briefly, then fall back to a direct write: the reader retries parse failures, so a
    torn read costs one poll, whereas a failed publish costs the whole run.

    ``mtime`` stamps the file's modified time (:func:`_stamp`) BEFORE the rename, which keeps it -- so no reader ever
    stats the new document with the wrong time. (The stamp changes only WHICH time the file carries; the
    read-body-then-stat race of a driver against the next rewrite is still there, as in the game.)
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    _stamp(tmp, mtime)
    for attempt in range(attempts):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            time.sleep(0.002 * (attempt + 1))
    path.write_text(text, encoding="utf-8")
    _stamp(path, mtime)
    try:
        tmp.unlink()
    except OSError:
        pass


def _publish_in_place(path: Path, text: str, *, stall: float, began: threading.Event,
                      stop: threading.Event, mtime: float | None = None) -> None:
    """``HarnessAgent.WriteAtomic`` as deployed: truncate in place, then write -- gap held open.

    Python's ``open(..., "w")`` is CREATE_ALWAYS with read+write sharing, like the agent's
    ``FileMode.Create`` + ``FileShare.Read``: a reader is never locked out, it reads an empty file.
    """
    try:
        with open(path, "w", encoding="utf-8") as fh:
            began.set()
            stop.wait(stall)
            fh.write(text)
        _stamp(path, mtime)
    finally:
        began.clear()


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
