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

# ======================================================================== H20-H21: O7's levels and squeeze
#: H20 (research/o7_design.md 3.1): how far from his height an open triangle under him may lie and still be HIS. The
#: engine keeps the actor on its active triangle and crosses only a shared edge to a neighbour; nearest-within-this is
#: that graph wherever stacked levels lie further apart than it and a step changes his height by less. A 60-u tick step
#: on stock 154's steepest open triangle (tri 205, the west flight, 52.8 deg) changes his height by 79.1, on 163's
#: (tri 134) by 63.0; 154's stacked open triangles lie at least 1298 apart (a stair over the ground; the balcony 1711
#: over it) -- test_fake_level_meshes_hold_the_levels_premises measures each.
LEVEL_STEP_DY = 200.0
#: H20: the engine's own "same level" pairing band (WalkMesh.cs:922), the stand-in for "his own surface": a wall is his
#: when its height at the point nearest him lies within this of his. Sound while stacked levels lie more than twice it
#: apart.
LEVEL_BAND = 400.0
#: H21 (research/o7_design.md 3.2): how far under the controller's radius a side a PINCH may be and still let him
#: through -- an ESTIMATE over 163's measured 3.3-u overlap (0.2 #12) that R-STAIR measures (F5); a NO-GO there is the
#: fallback end, never a wider slack.
SQUEEZE_SLACK_W = 8.0
#: H21: the spacing of the search across a pinch for its widest point.
SQUEEZE_SAMPLE_W = 2.0

# ======================================================================== H25: O8's knight walker
#: H25 (research/o8_design.md 3.2): a walker's ``start`` terms on the player's PUBLISHED y -- the release its height
#: gate reads (164 e1 t1 ip178's test read through ip187's JMP_IF loop: ``{"y_ge": 8400}``).
_WALKER_TESTS = {"y_ge": lambda y, h: y >= h, "y_gt": lambda y, h: y > h,
                 "y_le": lambda y, h: y <= h, "y_lt": lambda y, h: y < h}


def _walker_knobs(b: dict) -> None:
    """H25's keys read STRICT on a walker's first step (the H23 ``hold`` reader's place): ``start`` None or exactly
    one of :data:`_WALKER_TESTS`' terms to a number (a bool is no number); ``store`` None or a dict of exactly
    ``after_ticks`` -- a number >= 0 -- and ``args`` -- the seven ``[sid, tag, ip, byte, width, new, bit]`` of a
    :meth:`FakeGame.script_store`; ``path`` (H25b, the review's #2) ``[[x, z], ...]`` or ``[[x, z, y], ...]`` -- y the
    walker's level at the point, on every point or none -- numbers all. A ValueError names the fault."""
    def num(v) -> bool:
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    path = b.get("path")
    if path is not None and not (isinstance(path, (list, tuple)) and all(
            isinstance(p, (list, tuple)) and len(p) in (2, 3) and all(num(v) for v in p) for p in path)
            and len({len(p) for p in path}) <= 1):
        raise ValueError(f"a walker's path is [[x, z], ...] or [[x, z, y], ...] (y its level at the point, on every point "
                         f"or none), not {path!r}")
    start, store = b.get("start"), b.get("store")
    if start is not None and not (isinstance(start, dict) and len(start) == 1 and set(start) <= set(_WALKER_TESTS)
                                  and num(next(iter(start.values())))):
        raise ValueError(f"a walker's start is exactly one of {sorted(_WALKER_TESTS)} to a number (his published y), "
                         f"not {start!r}")
    if store is not None and not (isinstance(store, dict) and set(store) == {"after_ticks", "args"}
                                  and num(store["after_ticks"]) and store["after_ticks"] >= 0
                                  and isinstance(store["args"], (list, tuple)) and len(store["args"]) == 7):
        raise ValueError(f"a walker's store is {{'after_ticks': n >= 0, 'args': [sid, tag, ip, byte, width, new, bit]}}, "
                         f"not {store!r}")


class Levels:
    """H20 (research/o7_design.md 3.1): a STACKED walkmesh as the engine walks one actor on it -- stock 154's balcony
    1711 over its ground, its floor indices mixing both heights (0.2 #7), which the kit's floor-blind
    ``point_on_walkmesh`` and ``distance_to_boundary`` cannot tell apart. Over a kit walkmesh: a ``PlayerWalkmesh``
    (its open triangles) or a ``BgiWalkmesh`` (every triangle), its world verts in PSX y (up negative).

      * :meth:`tri_under` -- among the open triangles containing (x, z), the one whose height there is NEAREST his and
        within ``step_dy`` of it, else None: the actor stays on its active triangle and crosses only a shared edge
        (the walkmesh traversal), which this is wherever stacked levels lie more than ``step_dy`` apart and a step
        changes his height by less; :meth:`tri_nearest` -- the same without the bound (a placement, GetTriIdxAtPos,
        FieldMapActorController.cs:1279-1306);
      * :meth:`height` -- the interpolated PSX height on a triangle;
      * :meth:`wall_gap` -- the XZ distance to the nearest WALL of his level: an edge of an open triangle with no open
        neighbour (PlayerWalkmesh's rule, per triangle -- not per floor index), kept when its height at its point
        nearest him lies within ``band`` of his; None off his level;
      * :meth:`squeeze` -- H21 (3.2), with ``squeeze_slack`` set: a PINCH's midline.

    The fake walks him on it through ``fake.levels`` (:meth:`FakeGame._move_to`)."""

    def __init__(self, wmesh, *, step_dy: float = LEVEL_STEP_DY, band: float = LEVEL_BAND,
                 squeeze_slack: float | None = None):
        from ff9mapkit.scene import bgi
        mesh = getattr(wmesh, "mesh", wmesh)                 # a PlayerWalkmesh's raw mesh, or a BgiWalkmesh
        closed = frozenset(getattr(wmesh, "closed", ()) or ())
        for name, v in (("step_dy", step_dy), ("band", band)):
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not v > 0:
                raise ValueError(f"Levels: {name} is a positive number of world units, not {v!r}")
        if squeeze_slack is not None and (not isinstance(squeeze_slack, (int, float))
                                          or isinstance(squeeze_slack, bool) or squeeze_slack < 0):
            raise ValueError(f"Levels: squeeze_slack is None or a number of world units >= 0, not {squeeze_slack!r}")
        self.mesh = mesh
        self.step_dy, self.band = float(step_dy), float(band)
        self.squeeze_slack = None if squeeze_slack is None else float(squeeze_slack)
        self._wv = mesh.world_verts()
        tris = mesh.tris
        self.open = frozenset(i for i in range(len(tris)) if i not in closed)
        walls = []
        for ti in sorted(self.open):
            t = tris[ti]
            for k, (i, j) in enumerate(bgi.SLOT_PAIRS):
                n = t.nbr[k]
                if 0 <= n < len(tris) and n in self.open:
                    continue                                 # an open neighbour across this edge: not a wall
                a, b = self._wv[t.vtx[i]], self._wv[t.vtx[j]]
                dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
                walls.append((a[0], a[1], a[2], dx, dy, dz, dx * dx + dz * dz))
        self._walls = walls

    def height(self, ti: int, x: float, z: float) -> float:
        """The PSX height (up negative) of triangle ``ti``'s plane at (x, z), barycentric over its world verts."""
        a, b, c = (self._wv[k] for k in self.mesh.tris[ti].vtx)
        den = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if den == 0:
            return float(a[1])
        wa = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / den
        wb = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / den
        return wa * a[1] + wb * b[1] + (1.0 - wa - wb) * c[1]

    def tri_nearest(self, x: float, z: float, h: float) -> int | None:
        """The open triangle containing (x, z) whose height there is nearest ``h`` (ties: the lower id), else None."""
        best = None
        for ti in self.mesh.tris_at(x, z):
            if ti not in self.open:
                continue
            d = abs(self.height(ti, x, z) - h)
            if best is None or d < best[0]:
                best = (d, ti)
        return None if best is None else best[1]

    def tri_under(self, x: float, z: float, h: float) -> int | None:
        """His triangle at (x, z): :meth:`tri_nearest` when within ``step_dy`` of ``h``, else None (no triangle of his
        level there -- the edge of a balcony, over the ground below it)."""
        ti = self.tri_nearest(x, z, h)
        return ti if ti is not None and abs(self.height(ti, x, z) - h) <= self.step_dy else None

    def wall_gap(self, x: float, z: float, h: float) -> float | None:
        """The XZ distance from (x, z) to the nearest wall of HIS level (a wall whose height at its point nearest him
        lies within ``band`` of ``h``); None when no triangle of his level is under him (:meth:`tri_under`); infinity
        when no wall of his level stands anywhere."""
        if self.tri_under(x, z, h) is None:
            return None
        best = math.inf
        for ax, ay, az, dx, dy, dz, l2 in self._walls:
            t = 0.0 if l2 == 0 else ((x - ax) * dx + (z - az) * dz) / l2
            t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
            if abs(ay + t * dy - h) > self.band:
                continue                                     # another level's wall
            d = math.hypot(x - (ax + t * dx), z - (az + t * dz))
            if d < best:
                best = d
        return best

    def squeeze(self, x: float, z: float, ux: float, uz: float, h: float, clearance: float):
        """H21 (research/o7_design.md 3.2): where a step ending at (x, z) along (ux, uz) is placed in a PINCH -- the
        point of the LARGEST wall gap on the segment across the step through its end, ``clearance`` either side, each
        side only as far as his level's floor runs (the corridor's midline, where the engine's opposing pushes average
        out: RadiusValid pushes each wall's force out to the controller's radius, ServiceForces averages several x
        1.05, FieldMapActorController.cs:1060-1254) -- ``(px, pz)``, kept when that gap is at least ``clearance -
        squeeze_slack``. None -- the caller's rule as ever -- without ``squeeze_slack``, off his level, for no step, where
        a point across stands at the full ``clearance`` (no pinch: a press into a wall), or where the pinch is narrower
        than that bound (he stops: the radius cannot fit)."""
        if self.squeeze_slack is None or self.tri_under(x, z, h) is None:
            return None
        n = math.hypot(ux, uz)
        if n < 1e-9:
            return None
        px, pz = -uz / n, ux / n                             # across the step
        best = None
        for side in (1.0, -1.0):
            t = 0.0
            while t <= clearance + 1e-9:
                qx, qz = x + side * t * px, z + side * t * pz
                g = self.wall_gap(qx, qz, h)
                if g is None:
                    break                                    # off his level: no further this side
                if g >= clearance:
                    return None                              # room at the full radius across: no pinch here
                if best is None or g > best[0]:
                    best = (g, qx, qz)
                t += SQUEEZE_SAMPLE_W
        if best is None or best[0] < clearance - self.squeeze_slack:
            return None
        return best[1], best[2]


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
        #: The overworld on foot (None: the world position never moves, as before). Set a dict to walk him:
        #: ``speed`` u/frame while "up" is held, along the CAMERA yaw ``cam`` (deg, atan2(dz, dx) -- the
        #: engine's RotTrue = camera rotation + stick direction, ff9.cs:6162); ``turn`` deg/frame that L1
        #: adds to the camera (R1 the opposite; 0 = the bumpers do not reach it); ``lag`` frames the actor
        #: takes to come onto the camera's line from a standstill facing elsewhere; ``blocked(x, z)`` and
        #: ``height(x, z)`` the ground. x wraps at 1536, as the real map does. Published player.* is the
        #: world position x 256 (s83's GetControlChar pos[]), y included -- and a teleport keeps y until
        #: he next moves (the engine's InitSlice re-grounds it, not the teleport).
        self.overworld: dict | None = None
        self._ow_yaw: float | None = None          # the actor's own yaw, easing onto the camera's
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
        self.no_encounter = False          # s94: the F4 booster
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
        #: H13 (research/o5_design.md 3.1), OPT-IN: the sink's same-value SUPPRESSION (:meth:`_story_site`). False (the
        #: default): every store is a row, as above. True: the engine's per-site rule -- a site's first same-value store
        #: and its first STORY_CHANGE_ROWS changes are rows, the rest counted -- and the counts closed as ``c`` rows at
        #: every epoch's close (:meth:`_story_counts`). `story_suppressed` counts the stores it did not emit (the
        #: published ``suppressed`` stays 0: no reader reads it); `_story_sites` is the running epoch's site table.
        self.story_suppress = False
        self.story_suppressed = 0
        self._story_sites: dict = {}
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
        #: H26 (research/o8_design.md 3.1), OPT-IN: the clearance PER FIELD -- ``{field id: radius}``, read through
        #: :meth:`_clearance` wherever a step reads `clearance` (the levels' radius rule, the never-closer rule, H21's
        #: squeeze and the push-out). Empty (the default): every field walks at `clearance`, today's one value. One run
        #: crosses fields whose controllers differ -- 164's Steiner is radius 80 (DoEventCode.cs:1507-1508, through
        #: EffectiveFieldId), 165's 120.
        self.clearances: dict = {}
        #: H20 (research/o7_design.md 3.1), OPT-IN: a STACKED walkmesh's levels, by field id -- ``{field id:
        #: Levels}``. Empty (the default): today's fake. On a field with an entry, :meth:`_move_to` keeps him on ONE
        #: level of it (the open triangle under him within a step of his height), walls him in by his own level's walls
        #: alone, and publishes his height in ``player[1]`` (the agent's ``pos[1]``: f[1] = -pos[1]); a scripted
        #: placement sets it (:meth:`place_height`). `clearance` is required there (ValueError otherwise), and a level's
        #: ``squeeze_slack`` turns on H21's pinch rule.
        self.levels: dict = {}
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
        #: H16b (research/o6_design.md 3.2): fields whose running scene SWALLOWS the soft reset -- O1d's measurement (a
        #: soft reset through Alexandria's running opening scene did not reach the title: PLAN.md O1, story-o1d),
        #: whatever the engine's reason. Empty by default: the combo fires as :meth:`_check_soft_reset` says.
        self.reset_blocked_fields: set = set()
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
        #: THE COMMAND RACE, pinned: ``{"result": r, "nth": n, "op": "battlecmd" | "menus"}`` -- the battle ENDS with
        #: ``r`` (0: the scene goes with no result) as its ``n``-th (default 1) step ``op`` (default "battlecmd")
        #: arrives, BEFORE that step runs: an end (King Leo's scripted one in battle 338) landing between a driver's
        #: read of "asking slot N" and its command, which the step then meets as the agent does -- no battle HUD; with
        #: `battle_exit`, the fade's "not asking". With ``"after": a`` (frames) the step RUNS instead -- a ``menus``
        #: collects its menu and the request acks as usual -- and the end lands ``a`` frames later, after the drain (0:
        #: the step's own frame, so no published sample ever carries that menu): the end between the ack and the
        #: driver's read of the menu, which the battle doc carries only while the battle is up. Once a battle. None
        #: (the default): no such end.
        self.battle_end_on_command: dict | None = None
        self._race_steps = 0                       # this battle's steps of the raced op, for `battle_end_on_command`
        self._race_due: tuple | None = None        # (the frame it is due, its result): an `after` end, scheduled
        #: The naming screen (``Menu(1, char)``, a scene beat ``{"naming": char}``): each character named, in order.
        self.named: list[int] = []
        #: H17 (research/o6_design.md 3.3): the name a visit's naming screen SAVED, by character -- what PLAYER.Name
        #: holds after its OK; empty until one is saved, so a page's [STNR] renders the pre-filled default.
        self.names: dict[int, str] = {}
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
        #:   * ``"walkout"`` -- H16 (research/o6_design.md 3.1): ExitField's WALK-OUT, ``{"to": [x, z], "speed": u,
        #:     "stop_z": z}`` (``speed`` default 60, ``stop_z`` default None): from the fire to the switch he keeps
        #:     moving toward ``to`` at ``speed`` units a field tick -- MOVJ, at the speed of his last controlled frame
        #:     (HonoUpdate's 60 for a run) -- control off, and stops at ``to`` or, ``stop_z`` given, once his z passes
        #:     it (where pathing holds his centre a radius short of the floor's end). Without it he stands where the
        #:     region took him, as ever. The switch itself waits on `exit_gate` when a test holds one.
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
        self._walkout: dict | None = None          # H16: the firing region's walk-out, until the switch
        #: H16's GATE (research/o6_design.md 3.1, rev. 2): a ``threading.Event`` a TEST holds; None (the default) is
        #: today's fake. With it, a scheduled exit's switch waits, once its ``exit_frames`` have run, until the event is
        #: set -- he stands where the walk-out left him meanwhile -- so a test can fix which side of route_to's return
        #: the switch falls on, whatever the harness thread's load.
        self.exit_gate = None
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
        # -- H10-H12 (research/o4_design.md 3): the machine beats, opt-in -------------------------------------------
        #: The machine beat running now -- a ``{"keyon_pair": knobs}`` or ``{"chanbara": knobs}`` scene beat
        #: (:meth:`_start_machine`) -- else None. It reads the agent's HELD keys per frame and runs whole field ticks
        #: (:class:`_Machine`), so a press is judged on the frame and the tick it lands on, never at execute time.
        self._machine = None
        #: H11: one row per prompt the Chanbara beat armed -- ``{"fight", "n", "dbtn", "value", "arm_tick", "arm_frame",
        #: "edge_tick", "edge_frame", "j", "result", "sb38", "max_combo"}`` -- its arm tick S, the tick its key's edge
        #: landed on and the TRUE j (the tests' oracle for the driver's j bounds); ``result`` "hit", "miss" or "timeout";
        #: ``sb38`` and ``max_combo`` what the roll's filters read.
        self.chanbara_log: list[dict] = []
        #: H11: the fight's Map variables as the last score read them (``I30`` .. ``I50``, ``b47`` ...), for a test.
        self.chanbara_vars: dict = {}
        #: H11: what EMinigame reported to Steam: "Encore" once a score of 75 or more is read (EMinigame.cs:34-38).
        self.achievements: list[str] = []
        #: H11: the gil AddGi gave after page 128 (its ``[NUMB=1]``).
        self.gil = 0
        #: H10/H11: every window a machine beat listed, as it went -- ``{"event": "open" | "close" | "gone", "kind",
        #: "slot", "text", "frame", "tick", "rt"}`` (``tick`` the beat's own field-tick count).
        self.machine_log: list[dict] = []
        #: H14 (research/o5_design.md 3.2): every step a visit beat (:class:`_VisitBeat`) started, as it started --
        #: ``{"index", "field", "at", "kind", "tick", "frame"}``: the visit's ``index`` knob, the field it ran in, the
        #: step's place (``"7"``; ``"12.1.0"`` inside a choice's branch "1"; ``"8.s.0"`` in a side scene), its kind, and
        #: the beat's tick and the fake's frame it began on. With ``stairs`` rows of the height test's loss
        #: (``kind`` "lost": where the contour took control) and of a side scene or the back door firing.
        self.visit_log: list[dict] = []

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
        while not self._stop.is_set() and self.returncode is None:
            self._frame_once()
            if "mtime" in self.publish:
                self._pace_real_time()
            else:
                time.sleep(1.0 / self.fps)          # read each frame: a test may change the loop's pace mid-run

    def _frame_once(self) -> None:
        """One frame of the loop -- what :meth:`_run` turns, and what a test that steps the fake BY HAND calls. A
        machine beat (H10/H11) runs its frame before the publish under ``publish_order`` "agent_last" and after it under
        "agent_first" (:meth:`_step_machine`): a sample of frame f then shows its state after the ticks of frames <= f-1
        -- the engine's measured order, the agent's Update before HonoBehaviorSystem's (tickrate.py:67-69)."""
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
                self._step_machine("agent_last")
                self._step_battle()
                self._service_turn()        # s90: end, or cut, an in-place turn
                self._publish()
                self._step_machine("agent_first")
        except OSError as err:
            # Mirrors the agent's own try/catch. Without this a single transient sharing
            # violation killed the publisher thread, and every later wait then timed out
            # pointing at the wrong half of the system -- which is exactly how a harness
            # earns a reputation for being flaky when it is actually deterministic.
            self.error = str(err)

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
            # H17: New Game rebuilds every player with its CharacterDefaultName (FF9Play_New, ff9play.cs:131-144): a
            # name an earlier run saved never reaches this one's [STNR] pages (the review, research/o6_design.md 11.7 #2)
            self.names = {}
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
            self._race_end(op)
            if not self.battle_active:
                raise RuntimeError("battlecmd: no battle HUD (not in a battle?)")
            self._battle_command(num(0, 0), num(1, 0), num(2, 0), num(3, 0), num(4, 0))
            self._block(2)
        elif op == "menus":
            self._race_end(op)
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
            self.no_encounter = False          # s94: reset switches the booster off again
            self._block(2)
        elif op == "noencounter":                      # s94: the F4 booster, set directly
            self.no_encounter = num(0, 1) != 0
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
        if self._exit is not None and self.frame >= self._exit[0] and self._exit_open():
            self._step_exit_now()
        if self._exit is None:
            self._walkout = None                # H16: the exit landed, or a warp outran it: no walk-out is left
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
            if self._walkout is not None and self._visit == visit:
                self._step_walkout(ticks)       # H16: ExitField's walk-out runs with control OFF, until the switch
            if not self.control or self._visit != visit:
                continue                        # control gone, or a warp mid-frame: no tick of it moves him there
            self._step_player()
            if self.control:
                self._fire_contacts()           # CollisionRequest: every tick he has control, moving or not
        if self._plan is None and self.ui_state == "FieldHUD" and self.control:
            self._player_plan()                 # a frame no tick ran on still reads the pad: a coast frame is spent
        if self.ui_state == "WorldHUD" and self.overworld is not None:
            self._step_overworld()

    def _step_overworld(self) -> None:
        """One frame on foot on the overworld (see ``overworld``): the bumpers turn the camera, "up" walks
        the actor along it once his own yaw has eased on, ground that is ``blocked`` stops him, and his
        height follows ``height`` -- published, like the engine, as player.* = world x 256."""
        import math
        ow = self.overworld
        if self.world["x"] is None:
            return
        turn = float(ow.get("turn", 2.8125))
        if self._is_held("leftbumper") or self._is_held("l1"):
            ow["cam"] = (ow.get("cam", 0.0) + turn) % 360.0
        if self._is_held("rightbumper") or self._is_held("r1"):
            ow["cam"] = (ow.get("cam", 0.0) - turn) % 360.0
        x, z = self.world["x"], self.world["z"]
        if self._is_held("up"):
            cam = ow.get("cam", 0.0)
            if self._ow_yaw is None:
                self._ow_yaw = cam
            lag = max(1, int(ow.get("lag", 3)))
            d = (cam - self._ow_yaw + 180.0) % 360.0 - 180.0
            self._ow_yaw = (self._ow_yaw + d / lag) % 360.0 if abs(d) > 0.01 else cam
            sp = float(ow.get("speed", 1.0))
            nx = (x + sp * math.cos(math.radians(self._ow_yaw))) % 1536.0
            nz = z + sp * math.sin(math.radians(self._ow_yaw))
            blocked = ow.get("blocked")
            if blocked is None or not blocked(nx, nz):
                x, z = nx, nz
                self.world["x"], self.world["z"] = x, z
                height = ow.get("height")
                self._ow_y = float(height(x, z)) if height is not None else 0.0
        y = getattr(self, "_ow_y", 0.0)
        self.player = [x * 256.0, y * 256.0, z * 256.0]

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

    def _exit_open(self) -> bool:
        """H16's gate: whether a due exit may switch the field now -- always, unless a test holds `exit_gate` unset."""
        return self.exit_gate is None or self.exit_gate.is_set()

    def _walkout_of(self, r: dict) -> dict | None:
        """H16 (research/o6_design.md 3.1): a firing region's ``walkout``, read STRICT and armed from where he stands --
        or None without the key (today's ExitField: he stands where it took him)."""
        w = r.get("walkout")
        if w is None:
            return None
        if not isinstance(w, dict) or "to" not in w or not set(w) <= {"to", "speed", "stop_z"}:
            raise ValueError(f"a region's walkout is {{'to': [x, z], 'speed': u, 'stop_z': z | None}}, not {w!r}")
        tx, tz = (float(v) for v in w["to"])
        stop = None if w.get("stop_z") is None else float(w["stop_z"])
        way = 1.0 if tz >= self.player[2] else -1.0        # the sign of his z along the walk-out
        return {"to": (tx, tz), "speed": float(w.get("speed", 60.0)), "stop_z": stop, "way": way,
                "done": stop is not None and (self.player[2] - stop) * way >= 0}

    def _step_walkout(self, ticks: float) -> None:
        """H16: one field tick (in mean mode, the frame's share of one) of ExitField's walk-out -- MOVJ toward ``to`` at
        ``speed`` a tick (DoEventCode.cs:860-869; EventEngine.MoveToward.cs:15-30, :166), control off -- held at ``to``,
        or where his z passes ``stop_z`` (pathing holding his centre a radius short of the floor's end:
        research/o6_design.md 0.2 #6, an ESTIMATE the game measures)."""
        w = self._walkout
        if w["done"]:
            return
        x, z = self.player[0], self.player[2]
        (tx, tz), step = w["to"], w["speed"] * ticks
        d = math.hypot(tx - x, tz - z)
        nx, nz = (tx, tz) if d <= step else (x + (tx - x) / d * step, z + (tz - z) / d * step)
        w["done"] = d <= step
        stop = w["stop_z"]
        if stop is not None and (nz - stop) * w["way"] >= 0:
            t = (stop - z) / (nz - z) if nz != z else 1.0
            nx, nz, w["done"] = x + (nx - x) * t, stop, True
        self.player[0], self.player[2] = nx, nz

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
        400 of him in y (WalkMesh.Collision's pair rule and its |dy| band).

        H20 (research/o7_design.md 3.1), OPT-IN: on a field with an entry in `levels` the floor is HIS LEVEL of a
        stacked walkmesh -- the clearance rule below, its walls his level's (:meth:`Levels.wall_gap`) and its floor the
        open triangle under him within a step of his height (:meth:`Levels.tri_under`, his height ``-player[1]``) --
        and his height is published after the step (``player[1]``, minus the height there); `clearance` is required.
        H21 (3.2): with the level's ``squeeze_slack``, a PINCH -- a corridor with no point across it at `clearance` --
        is passed down to ``clearance - squeeze_slack`` (:meth:`Levels.squeeze`), where the engine's opposing pushes
        average out at its midline. H26 (research/o8_design.md 3.1), OPT-IN: every rule here reads THIS field's
        clearance (:meth:`_clearance`, read once a step): `clearances`' entry for the field, else `clearance`."""
        ox, oz = self.player[0], self.player[2]
        ax, az = x - ox, z - oz                     # the step as pressed (H21's refused step reads it)
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
        lv = self.levels.get(self.field_id)         # H20 (opt-in): his level of a stacked walkmesh
        clearance = self._clearance()               # H26 (opt-in): THIS field's radius, else the one value
        h = None
        if lv is not None and clearance is None:
            raise ValueError(f"fake.levels[{self.field_id}]: a level is walked at the controller's radius -- set "
                             f"fake.clearance (Steiner's: 120) or fake.clearances[{self.field_id}]")
        if lv is not None or (on is not None and clearance is not None):
            # his centre kept `clearance` off every wall -- pushed out onto that line where he stands closer (placed
            # there), or, where no push lands him on it, never closer still: the step stops on that line, and its
            # rest slides on along the wall
            if lv is not None:
                h = -float(self.player[1])          # his height (PSX y, up negative): f[1] = -pos[1]

                def wall(px, pz):
                    d = lv.wall_gap(px, pz, h)
                    return -1.0 if d is None else d
            else:
                def wall(px, pz):
                    d = self.walkmesh.distance_to_boundary(int(round(px)), int(round(pz)))
                    return -1.0 if d is None or on(int(round(px)), int(round(pz))) is None else d
            squeeze = lv is not None and lv.squeeze_slack is not None     # H21 (opt-in)
            squeezed = False
            least = max(0.0, min(clearance, wall(ox, oz)))          # off the mesh (an arrival): onto it

            def floor(px, pz):
                return wall(px, pz) >= least
            if not floor(x, z):
                ex, ez = x, z                       # H21: the step's own end
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
                slid = False
                for deg in (15, 30, 45, 60, 75):
                    c = math.cos(math.radians(deg))
                    for s in (math.sin(math.radians(deg)), -math.sin(math.radians(deg))):
                        px, pz = bx + (rx * c - rz * s) * c, bz + (rx * s + rz * c) * c
                        if floor(px, pz):
                            x, z = px, pz
                            slid = True
                            break
                    else:
                        continue
                    break
                if squeeze and not slid:
                    # H21: neither the never-closer rule nor a slide stands -- in a PINCH (no point across the step's
                    # end at full clearance) the opposing pushes average out at its midline: placed there when the
                    # pinch is no narrower than clearance - squeeze_slack a side; else he stops, as ever
                    got = lv.squeeze(ex, ez, ex - ox, ez - oz, h, clearance)
                    if got is not None:
                        x, z = got
                        squeezed = True
            if not squeezed and 0.0 <= wall(ox, oz) < clearance and 0.0 <= wall(x, z) < clearance:
                got = lv.squeeze(x, z, x - ox, z - oz, h, clearance) if squeeze else None
                if got is not None:
                    # H21: inside a pinch his place is its midline, where the pushes balance -- never pushed back out
                    # of it along the corridor to a spot at full clearance
                    x, z = got
                else:
                    # placed nearer a wall than his radius (a scene's own spot): where the step ends -- kept on the
                    # floor above, as the engine's triangle walk keeps it -- is pushed straight out onto the radius
                    # line, as the engine pushes it on his first moving frame
                    got = self._pushed_out(x, z, wall)
                    if (squeeze and got is not None and (got[0] - ox) * ax + (got[1] - oz) * az < 0
                            and lv.squeeze(ox, oz, ax, az, h, clearance) is not None):
                        # H21 at a pinch NARROWER than its bound (research/o8_design.md 11.4 PART B, #1): standing on a
                        # pinch's midline (he fits where he stands), a step that no squeeze places further in is pushed
                        # out BEHIND where it started, against the press -- back out of the pinch along the corridor,
                        # then squeezed in again on the next press: a jitter at its mouth, never a stop. The engine
                        # refuses that step (IsRadiusValid fails; a pushed position across a wall is rejected:
                        # FieldMapActorController.cs:975-993, 1188-1254): he stays where he stands -- he stops, as
                        # Levels.squeeze says
                        got = (ox, oz)
                    x, z = got or (x, z)
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
        if lv is not None:                          # H20: his height where the step left him, on his level
            ti = lv.tri_under(x, z, h)
            if ti is not None:
                self.player[1] = -lv.height(ti, x, z)
        self._lock_fallback(calls)
        return True

    def place_height(self, x: float, z: float, h: float) -> None:
        """H20 (research/o7_design.md 3.1): a scripted placement's HEIGHT -- ``h`` the PSX y operand of the bytes'
        MoveInstantXZY (up negative; 154 e15 t0 ip2827's ``Map.Int16[2]``, -1741). With a level entry for this field
        ``player[1]`` is minus the height of the open triangle under (x, z) nearest ``h`` -- no step bound: a placement
        lands on the nearest-height triangle (GetTriIdxAtPos, FieldMapActorController.cs:1279-1306) -- else (no entry,
        or no open triangle under (x, z)) minus ``h``. His x and z are the caller's."""
        lv = self.levels.get(self.field_id)
        ti = None if lv is None else lv.tri_nearest(x, z, h)
        self.player[1] = -float(h) if ti is None else -lv.height(ti, x, z)

    def _clearance(self) -> float | None:
        """H26 (research/o8_design.md 3.1): the engine radius his centre keeps off a wall in THIS field -- the field's
        entry in ``clearances``, else ``clearance`` (today's one value). 164's Steiner is radius 80 (DoEventCode.cs:
        1507-1508, through EffectiveFieldId), 165's 120."""
        return self.clearances.get(self.field_id, self.clearance)

    def _pushed_out(self, x: float, z: float, wall):
        """Where the engine's push off the walls puts a centre standing nearer one than his radius: straight away from
        it, onto the radius line (FieldMapActorController.RadiusValid -> ServiceForces: one force lands it exactly
        there, several are averaged). Modelled as the move to ``clearance`` off every wall along whichever of 64
        bearings stands it furthest off them, over floor all the way -- again from there while a second wall holds
        it (a corner: 352's pocket between strip and back wall takes five). None when no bearing gets further out:
        the caller keeps its never-closer-still rule. H26 (research/o8_design.md 3.1): THIS field's clearance
        (:meth:`_clearance`)."""
        import math
        clearance = self._clearance()
        for _ in range(16):                         # each round nearer the line, or it gives up
            d = wall(x, z)
            if d >= clearance:
                return x, z
            r = clearance - d + 0.5
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
        return (x, z) if wall(x, z) >= clearance else None

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
        bring it within ``r`` of the player, where it waits, still moving (MoveToward.cs:187-189).

        H23 (research/o7_design.md 3.4), opt-in: a walker's ``hold`` -- ``{"within": r, "latch_below": y1,
        "unlatch_above": y2, "at": [k, ...]}`` -- keeps it standing at a path index in ``at`` (its placement is index
        0) while his XZ distance is under ``within`` OR its latch is set (154 e5 t1 ip263 / ip486: ``B_DISTANCEA < 3600
        || Map.Byte[30] == 1``). The latch sets the first tick his published y is under ``latch_below`` (e11 t1 ip14 /
        ip33: ``f[1] > -600``) and then clears once it is over ``unlatch_above`` (ip128 / ip147: ``f[1] < -500``) --
        each tick, in that order; it starts clear (e15 t0 ip2116 ``Map.Byte[30] := 2``). Held, it stands -- its script
        waits in ip263's loop, no walk runs: ``objects`` publishes it ``moving`` False. Elsewhere on its path it walks
        without a wait (e5 t1 ip316-ip474).

        H25 (research/o8_design.md 3.2), opt-in: THE KNIGHT -- a walker carrying ``start`` or ``store`` (read STRICT on
        its first step: :func:`_walker_knobs`). ``start``, exactly one of ``{"y_ge": h}`` / ``{"y_gt": h}`` /
        ``{"y_le": h}`` / ``{"y_lt": h}`` on his PUBLISHED y (``player[1]``), holds it at its placement (``_held``:
        ``objects`` publishes it ``moving`` False) until the first tick it holds, when it walks -- and it is LATCHED,
        never held by it again (164 e1 t1 ip178 ``obj(uid=250).f[1] > -8400`` looped by ip187's JMP_IF, released at y >=
        8400). ``store``, ``{"after_ticks": n, "args": [sid, tag, ip, byte, width, new, bit]}``: once its ``once`` path's
        last index is reached, ``n`` field ticks later :meth:`script_store` is called ONCE (``_stored``: 164 e1 t1
        ip221-ip230, the stand anim and RunAnimation(9920), then ``Bit[3811] := 1``) -- the countdown runs before the
        walking skip (a done walker still counts), and it lives on the BODY: a visit that ends first takes its bodies
        with it (:meth:`_VisitBeat.end`) and the store never comes. And such a body is "held by him" only at |its y - his
        published y| < 400 (WalkMesh.Collision's pair band, WalkMesh.cs:919-921: the knight on loop 2 never pairs with
        Steiner on loop 1); every other walker keeps the XZ-only rule. H25b (the review's #2), opt-in: a path whose
        points carry a third coordinate -- the walker's LEVEL there, read off the mesh -- moves its ``y`` with its x
        and z, linearly along each leg (the knight climbs loop 2 from his placement's 11255 to his seat's 11896), so
        the pair band and ``objects`` read the level it stands on; a two-coordinate path keeps ``y`` as given."""
        for _i, b in self._bodies():
            h25 = b.get("start") is not None or b.get("store") is not None
            if h25:                                        # H25: read strict once, then the store's countdown
                if "_h25" not in b:
                    _walker_knobs(b)
                    b["_h25"] = True
                store = b.get("store")
                if store is not None and b.get("_done") and not b.get("_stored"):
                    b["_left"] = b.get("_left", float(store["after_ticks"])) - ticks
                    if b["_left"] <= 1e-9:
                        b["_stored"] = True
                        args = store["args"]
                        self.script_store(int(args[0]), int(args[1]), int(args[2]), int(args[3]), str(args[4]),
                                          int(args[5]), bit=int(args[6]))
            if not self._walking(b):
                continue
            start = b.get("start")
            if start is not None and not b.get("_started"):          # H25: held at its placement until released
                (term, h), = start.items()
                y = self.player[1]
                if y is None or not _WALKER_TESTS[term](float(y), float(h)):
                    b["_held"] = True
                    continue
                b["_started"], b["_held"] = True, False      # LATCHED: never held by it again
            hold = b.get("hold")
            if hold is not None:                           # H23: the latch, then the hold at its stops
                y = self.player[1]
                if not b.get("_latch") and y < float(hold["latch_below"]):
                    b["_latch"] = True
                if b.get("_latch") and y > float(hold["unlatch_above"]):
                    b["_latch"] = False
                b["_held"] = b.setdefault("_at", 0) in hold["at"] and bool(
                    b.get("_latch") or math.hypot(b["x"] - self.player[0], b["z"] - self.player[2])
                    < float(hold["within"]))
                if b["_held"]:
                    continue                               # held at its stop: its script waits, no walk runs
            path = b["path"]
            k = b.setdefault("_k", 1 if len(path) > 1 else 0)
            tx, tz = path[k][0], path[k][1]
            dx, dz = tx - b["x"], tz - b["z"]
            dist = (dx * dx + dz * dz) ** 0.5
            step = min(float(b["speed"]) * (ticks / WALKER_FRAME_TICKS), dist)
            nx, nz = (b["x"] + dx / dist * step, b["z"] + dz / dist * step) if dist > 0 else (tx, tz)
            px, pz = self.player[0], self.player[2]
            near = ((nx - px) ** 2 + (nz - pz) ** 2) ** 0.5
            paired = not h25 or (self.player[1] is not None
                                 and abs(float(b.get("y", 0.0)) - float(self.player[1])) < 400)    # H25: the pair band
            if paired and near < b["r"] and near < ((b["x"] - px) ** 2 + (b["z"] - pz) ** 2) ** 0.5:
                continue                                   # held by him
            b["x"], b["z"] = nx, nz
            if len(path[k]) > 2:                           # H25b: its level moves with it, linearly along the leg
                ty = float(path[k][2])
                y0 = float(b.get("y", ty))
                b["y"] = ty if step >= dist else y0 + (ty - y0) * step / dist
            if hold is not None:
                b["_at"] = k if step >= dist else None     # H23: the stop it stands at, None between two
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
                        "shown": shown, "moving": self._walking(b) and not b.get("_held"),    # H23: a held walker stands
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
        self._walkout = self._walkout_of(r)        # H16 (opt-in): he walks on until the switch
        if self.exit_frames <= 0 and self._exit_open():
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
        self._walkout = None                       # H16: the field changes under the walk-out
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
        if self.field_id in self.reset_blocked_fields:
            return                              # H16b: a running scene there swallows it (O1d)
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
        self._race_steps, self._race_due = 0, None
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

    def _race_end(self, op: str) -> None:
        """`battle_end_on_command`: as its ``n``-th step ``op`` of the battle arrives, the battle ends first, and the
        step meets whatever that end left -- or, with ``after``, the step runs and the end is due ``after`` frames on
        (:meth:`_step_battle` ends it, after the drain)."""
        race = self.battle_end_on_command
        if race is None or not self.battle_active or op != race.get("op", "battlecmd"):
            return
        self._race_steps += 1
        if self._race_steps == int(race.get("nth", 1)):
            if race.get("after") is None:
                self.end_battle(int(race["result"]))
            else:
                self._race_due = (self.frame + max(0, int(race["after"])), int(race["result"]))

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
        if self._race_due is not None and self.frame >= self._race_due[0]:
            result, self._race_due = self._race_due[1], None
            self.end_battle(result)                     # `battle_end_on_command`'s `after` end
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
        if self.story_suppress:                     # H13 (opt-in): a re-arm closes the running epoch's counts first
            if self.story_on:                       # (Start: Sync, then Resync's EmitCounts, StoryTrace.cs:170-176),
                self._story_counts()                # and every epoch starts with no site
            self._story_sites.clear()
        self.story_on = True
        self._story_row("e", why="arm")

    def _story_stop(self) -> None:
        if not self.story_on:
            return
        if self.story_suppress:                     # H13 (opt-in): Stop's EmitCounts, before its `off` (:198-202)
            self._story_counts()
        self._story_row("e", why="off")
        self.story_on = False

    def _story_store(self, src: str, byte: int, width: str, new: int, *, bit: int = -1,
                     sid: int = -1, tag: int = -1, ip: int = -1) -> None:
        """A store to the modelled gEventGlobal, and -- when tracing -- its `w` row. Only a script row
        names its writer (StoryTrace.AfterStore): cs/harness rows carry -1 attribution. ``old`` is the variable as
        its width reads it (the row contract): an Int16 signed, so a second store of -1 reads old -1, never 65535."""
        if width == "Bit":
            old = (self.story_bytes[byte] >> (bit & 7)) & 1
            self.story_bytes[byte] = (self.story_bytes[byte] & ~(1 << (bit & 7))) | (new << (bit & 7))
        elif width == "Byte":
            old = self.story_bytes[byte]
            self.story_bytes[byte] = new
        else:
            old = self.story_bytes[byte] | (self.story_bytes[byte + 1] << 8)
            if width == "Int16" and old >= 0x8000:
                old -= 0x10000
            self.story_bytes[byte:byte + 2] = bytes((new & 0xFF, (new >> 8) & 0xFF))
        if not self.story_on:
            return
        script = src == "eb"
        if self.story_suppress and not self._story_site(src, sid if script else -1, tag if script else -1,
                                                         ip if script else -1, byte, width, bit, old, new):
            return                                  # H13 (opt-in): the sink counted it -- no row
        self._story_row("w", src=src, sid=sid if script else -1, uid=sid if script else -1,
                        lvl=0 if script else -1, ip=ip if script else -1, tag=tag if script else -1,
                        add=0, byte=byte, w=width, bit=bit, old=old, new=new, same=int(old == new))

    def _story_site(self, src: str, sid: int, tag: int, ip: int, byte: int, width: str, bit: int, old: int,
                    new: int) -> bool:
        """H13 (research/o5_design.md 3.1), ``story_suppress`` on: the sink's per-site rule (StoryTrace.AfterStore,
        StoryTrace.cs:374-401) -- True when this store's ``w`` row is EMITTED. The SITE is the engine's key ``(fld, m,
        src, sid, tag, ip, byte, w, bit)`` (StoryTrace.cs:101-110), ``fld`` the field id NOW (``fldMapNo``, :374) and
        ``m`` the row's mode, the attribution the row's own (-1 off a script row). Per epoch a site keeps whether it
        emitted a SAME-VALUE row -- only a same-value store sets that (:383-388), so a site whose first store was a
        change still emits its first same-value one -- its changes emitted, at most :data:`STORY_CHANGE_ROWS`
        (:391-394), what it counted (``n``, ``last``: :396-401) and the ``don`` its rows carry (EffectiveFieldId of its
        field: ``fake.donor`` when the site opened). A store not emitted is counted (``story_suppressed``): no row,
        ``story_rows`` unchanged -- the file stays exactly the rows the state block counts."""
        mode = 3 if self.ui_state == "WorldHUD" else 2 if self.battle_active else 1
        key = (self.field_id, mode, src, sid, tag, ip, byte, width, bit)
        site = self._story_sites.get(key)
        if site is None:
            site = self._story_sites[key] = {"same": False, "changes": 0, "n": 0, "last": None,
                                             "don": self.field_id if self.donor is None else self.donor}
        if old == new:
            emit, site["same"] = not site["same"], True
        else:
            emit = site["changes"] < STORY_CHANGE_ROWS
            site["changes"] += int(emit)
        if not emit:
            site["n"] += 1
            site["last"] = new
            self.story_suppressed += 1
        return emit

    def _story_counts(self) -> None:
        """H13: the running epoch's counts closed (StoryTrace.EmitCounts, StoryTrace.cs:540-557) -- one ``c`` row per site
        that counted a store, in site-creation order (the reader never reads their order), stamped with the SITE's
        ``fld``/``don``/``m`` and the flush's ``f``/``p``/``sc`` -- then the site table cleared, as the engine clears it
        at every epoch (Resync, Stop: :199, :532)."""
        for (fld, m, src, sid, tag, ip, byte, width, bit), site in self._story_sites.items():
            if site["n"]:
                self._story_row("c", m=m, fld=fld, don=site["don"], src=src, sid=sid, tag=tag, ip=ip, byte=byte,
                                w=width, bit=bit, n=site["n"], last=site["last"])
        self._story_sites.clear()

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
        if "keyon_pair" in beat or "chanbara" in beat or "visit" in beat:
            self._start_machine(beat)                # H10/H11/H14 (research/o4_design.md 3, o5 3.2): a machine beat
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

    # -- H10-H12 (research/o4_design.md 3): the machine beats ----------------------------------------------------------
    def _start_machine(self, beat: dict) -> None:
        """A machine beat begins (:meth:`_next_beat`'s dispatch): ``{"keyon_pair": knobs}`` (H10, :class:`_KeyonPairBeat`),
        ``{"chanbara": knobs}`` (H11, :class:`_ChanbaraBeat`) or ``{"visit": knobs}`` (H14, :class:`_VisitBeat`;
        research/o5_design.md 3.2), its knobs checked strict here. No dialog yet, control as
        the scene left it (off); from its first frame on the machine owns the published dialog (its windows), the choice,
        the menu group and the bodies until it ends -- its own end pops the beat and moves the scene on, a warp (any new
        visit) cuts it with its scene (:meth:`_Machine.frame`). A press reaches it only through the HELD keys it reads per
        frame: :meth:`_scene_press` leaves a beat in phase "machine" alone."""
        self.texts, self.raw_texts, self.choice = [], [], None
        self._beat_phase = "machine"
        if "visit" in beat:
            self._machine = _VisitBeat(self, beat["visit"])
            return
        knobs = beat["keyon_pair"] if "keyon_pair" in beat else beat["chanbara"]
        self._machine = (_KeyonPairBeat if "keyon_pair" in beat else _ChanbaraBeat)(self, knobs)

    def _step_machine(self, slot: str) -> None:
        """The running machine beat's frame, in the slot its ``publish_order`` names (:meth:`_frame_once`)."""
        if self._machine is not None:
            self._machine.frame(self, slot)

    def open_menu(self, entries: list[str], group: str = "MainMenu") -> None:
        self.ui_state = "MainMenu"
        self.menu_entries = list(entries)
        self.menu_index = 0
        self.menu = {"selected": "Button0", "hovered": None,
                     "label": entries[0] if entries else None, "group": group}


# ======================================================================== H10-H12: the machine beats (O4)
#: H10/H11 (research/o4_design.md 3): the agent's Control for every name a ``press`` / ``hold`` may carry --
#: HarnessAgent.ParseControl (HarnessAgent.cs:1430-1449), aliases included: ``circle``, ``x``, ``a`` and ``ok`` are
#: CONFIRM (the Cross bit, never Circle's), ``b``/``back`` Cancel, ``triangle``/``y`` Menu, ``square`` Special,
#: ``start`` Pause. Read only by the machine beats (:meth:`_Machine.level`); :func:`_control`, every other model's,
#: keeps the name as it was sent.
AGENT_CONTROL = {"confirm": "confirm", "ok": "confirm", "x": "confirm", "circle": "confirm", "a": "confirm",
                 "cancel": "cancel", "back": "cancel", "b": "cancel",
                 "menu": "menu", "triangle": "menu", "y": "menu",
                 "special": "special", "square": "special",
                 "l1": "l1", "leftbumper": "l1", "r1": "r1", "rightbumper": "r1",
                 "l2": "l2", "lefttrigger": "l2", "r2": "r2", "righttrigger": "r2",
                 "start": "pause", "pause": "pause", "select": "select",
                 "up": "up", "north": "up", "down": "down", "south": "down",
                 "left": "left", "west": "left", "right": "right", "east": "right"}
#: The bits each Control sets in the engine's input word (ETb.GetInputs = FPSManager.DelayedInputs & 0x3FFFFFF) under
#: cfg.control 0, New Game's identity logicalToButton (research/o4_design.md 0.2 #6): GetKeyMaskFromControl
#: (EventInput.cs:476-534) is the logical bit OR the physical button's -- Cross 0x4000, Circle 0x2000, Triangle 0x1000,
#: Square 0x8000, L1 0x400, R1 0x800, L2 0x100, R2 0x200 -- the four directions are set straight by ProcessInput
#: (:328-346), Pause sets Start 0x8 (:303-305) and Select 0x1.
CONTROL_BITS = {"confirm": 0x20000 | 0x4000, "cancel": 0x10000 | 0x2000, "menu": 0x1000000 | 0x1000,
                "special": 0x80000 | 0x8000, "l1": 0x100000 | 0x400, "r1": 0x200000 | 0x800,
                "l2": 0x400000 | 0x100, "r2": 0x800000 | 0x200, "pause": 0x8, "select": 0x1,
                "up": 0x10, "right": 0x20, "down": 0x40, "left": 0x80}
#: What the KEYON pairs' loops read (64 e13 t1 ip868 / ip1404 / ip1156; 150 e2 t1 ip538): logical Confirm or Special.
KEYON_PAIR_BITS = 0x20000 | 0x80000
#: e3 t1's eight KEYON checks in ip order (64 e3 t1 ip34-363): ``(bit, Byte[46] value, wrong code)`` -- a pressed bit
#: sets Byte[47] 2 when Byte[46] is its value, else Byte[47] 3 and Byte[46] its wrong code (so two keys in a tick miss).
CHANBARA_KEYS = ((0x80, 0, 11), (0x20, 1, 10), (0x1000, 2, 10), (0x40, 3, 11), (0x4000, 4, 10), (0x10, 5, 11),
                 (0x2000, 6, 11), (0x8000, 7, 11))
CHANBARA_WRONG = {value: wrong for _bit, value, wrong in CHANBARA_KEYS}
#: Byte[46] -> the prompt's button (window 112 + Byte[46], 64 e20 t1 ip789-852; block 2's mes 112-119) and its MOBI.
CHANBARA_DBTN = ("LEFT", "RIGHT", "TRIANGLE", "DOWN", "CROSS", "UP", "CIRCLE", "SQUARE")
CHANBARA_MOBI = (267, 269, 272, 270, 274, 268, 273, 271)
#: 64's windows the visit shows (block 2, US -- the research's mes_64_105_128): ``mes -> (STRT, TAIL, source,
#: rendered)``. The agent publishes the rendered text as ``texts`` (tags gone, [ZDNE] Zidane's name, ``{0}`` the
#: [NUMB] the score fills in) and ``[STRT=..][TAIL=..]`` + the source as ``phrase_raw`` -- the form O3 measured on
#: 105 (INFERRED for the rest; research/o4_design.md 3: R-CHANBARA's F1 replaces it). 124-127's "rendered" is the
#: choice's prompt; its lines are the knob ``choice_lines``.
CHANBARA_MES = {
    105: ("70,2", "LORF", "Blank\n“En garde!”[INCS][TIME=-1]", "Blank\n“En garde!”"),
    106: ("171,2", "UPLF", "[ZDNE]\n“Expect no quarter from me!”[INCS][TIME=-1]",
          "Zidane\n“Expect no quarter from me!”"),
    107: ("152,2", "LORF", "Blank\n“We shall finish this later!”[INCS][TIME=-1]", "Blank\n“We shall finish this later!”"),
    108: ("109,2", "UPLF", "[ZDNE]\n“Come back here!”[INCS][TIME=-1]", "Zidane\n“Come back here!”"),
    109: ("193,2", "LORF", "Blank\n“Is that the best thou canst do!?”[INCS][TIME=-1]",
          "Blank\n“Is that the best thou canst do!?”"),
    110: ("83,2", "UPLF", "[ZDNE]\n“Die, traitor!”[INCS][TIME=-1]", "Zidane\n“Die, traitor!”"),
    111: ("233,5", "DEFT", "[IMME][CENT=233]To follow Blank’s lead, enter the correct\n[CENT=209]commands from the "
                           "following choices:\n[XTAB=88][YADD=6][DBTN=UP][MOBI=268][XTAB=132][DBTN=TRIANGLE][MOBI=272]\n"
                           "[CENT=77][DBTN=LEFT][MOBI=267][FEED=6][DBTN=RIGHT][MOBI=269][FEED=13][DBTN=SQUARE][MOBI=271]"
                           "[FEED=6][DBTN=CIRCLE][MOBI=273]\n[XTAB=88][YSUB=6][DBTN=DOWN][MOBI=270][XTAB=132]"
                           "[DBTN=CROSS][MOBI=274]",
          "To follow Blank’s lead, enter the correct\ncommands from the following choices:"),
    120: ("156,2", "DEFT", "[WDTH=0,96,64,0,-1][IMME]Of the 100 nobles watching,\n[NUMB=0] were impressed.",
          "Of the 100 nobles watching,\n{0} were impressed."),
    121: ("102,2", "DEFT", "[IMME]Queen Brahne was\nnot impressed.", "Queen Brahne was\nnot impressed."),
    122: ("134,2", "DEFT", "[WDTH=0,96,64,0,-1][IMME]Of 100 nobles watching,\n[NUMB=0] were impressed.",
          "Of 100 nobles watching,\n{0} were impressed."),
    123: ("102,2", "DEFT", "[IMME]Queen Brahne was\nquite impressed.", "Queen Brahne was\nquite impressed."),
    124: ("174,4", "DEFT", "[PCHC=2,1][IMME]The audience is booing...\nPerform the fight scene again?\n[CHOO]"
                           "[MOVE=18,0]Yes\n[MOVE=18,0]No", "The audience is booing...\nPerform the fight scene again?"),
    125: ("174,4", "DEFT", "[PCHC=2,1][IMME]The audience did not enjoy it.\nPerform the fight scene again?\n[CHOO]"
                           "[MOVE=18,0]Yes\n[MOVE=18,0]No",
          "The audience did not enjoy it.\nPerform the fight scene again?"),
    126: ("175,4", "DEFT", "[PCHC=2,1][IMME]The audience seemed to like it.\nPerform the fight scene again?\n[CHOO]"
                           "[MOVE=18,0]Yes\n[MOVE=18,0]No",
          "The audience seemed to like it.\nPerform the fight scene again?"),
    127: ("174,4", "DEFT", "[PCHC=2,1][IMME]They demand an encore!\nPerform the fight scene again?\n[CHOO]"
                           "[MOVE=18,0]Yes\n[MOVE=18,0]No", "They demand an encore!\nPerform the fight scene again?"),
    128: ("147,1", "DEFT", "[WDTH=0,147,64,1,-1][IMME]They shower you with [C8B040][HSHD][NUMB=1] Gil[C8C8C8][HSHD]!",
          "They shower you with {0} Gil!"),
}
#: A machine beat's frame runs after the publish ("agent_first": a sample of frame f shows its state after the ticks
#: of frames <= f-1, the engine's measured order, tickrate.py:67-69) or before it ("agent_last": frames <= f).
PUBLISH_ORDERS = ("agent_first", "agent_last")
#: H10's knobs and defaults (research/o4_design.md 3): the pair's texts (and sources), the second window ``lag_ticks``
#: after the first (106 after e13's Wait(15), ip816), its INCS/250 gate ``gate_ticks`` after the second opened (an
#: ESTIMATE: <= 250), every window's close tween (``close_frames`` + ``close_s``), the publication order.
KEYON_PAIR_DEFAULTS = {"texts": None, "raw": None, "lag_ticks": 15, "gate_ticks": 40, "close_s": 0.09,
                       "close_frames": 1, "publish_order": "agent_first"}
#: H11's and H12's knobs and defaults (research/o4_design.md 3) -- each an engine value, or where unmeasured the
#: research's estimate (named so): ``seed`` (the rolls: SYSVAR[0] is Unity's unseeded Random.Range(0, 256)); ``sa``
#: (Memoria.ini SwordplayAssistance); ``bonus_fires`` (EMinigame's +30% hook fires: False models a fork whose
#: EffectiveFieldId wrap fails); ``walk_in_s`` (measured, story-o3 run 6); ``gates`` (each KEYON pair's INCS/250 gate
#: in ticks, by its first window's mes: ESTIMATES); the tweens (``close_s``/``close_frames``, ``open_s``/
#: ``open_frames``); ``reaction`` (ticks from a pass's arm to its WAIT, by the previous result Byte[45]: 99 the first
#: pass's Wait(30), 0/1 a LEFT/RIGHT hit's slide + WaitAnimation + Wait(22), the 30-frame clips -- ESTIMATES);
#: ``reqsw_ticks`` (RunScript(2,13,11)'s wait for e13); ``publish_order``; the prompts' ``prompt_raw`` /
#: ``prompt_text`` (INFERRED); ``arm_after_111`` (T0 + 12); ``walk_off_s``, ``walk_back_s`` (the encore's walk back,
#: stage 7: not in section 3's list, an ESTIMATE like walk_off_s); ``exit_wait_ticks`` (stage 9's Wait(65));
#: ``exit_to`` (REQUIRED: where Field(150) lands); ``choice_lines`` (the encore choice's published lines -- O1's
#: lesson: the first lost); ``encore`` (False: no choice, the No branch at once); ``slides`` (the LEFT/RIGHT slides
#: move the bodies); and H12's faults: ``lost`` (instance numbers whose presses the game never reads), ``miss_read``
#: (instance numbers whose right key the game scores as a miss), ``score_override`` (the score the page shows),
#: ``extra_prompts`` (passes armed past the bytes' 49), ``menu_on_triangle`` (a Triangle edge opens the main menu),
#: ``unsubstituted_once`` (122/120 and 128 publish their raw [NUMB=n] once -- for ``unsubstituted_frames`` frames from
#: that first publish, 1 by default: a drive test's way to make sure a read lands on it), ``replay_on_no`` (No replays
#: too), ``tutorial`` (False: stage 2 shows no 111 -- T0 the tick after its Wait(5) -- so the driver enters the zone on
#: its first prompt, research/o4_design.md 2.4.2).
CHANBARA_DEFAULTS = {
    "seed": 0, "sa": 1, "bonus_fires": True, "walk_in_s": 1.83, "gates": {"105": 40, "107": 40, "109": 40},
    "close_s": 0.09, "close_frames": 1, "open_s": 0.105, "open_frames": 2,
    "reaction": {99: 30, 0: 28, 1: 28, "others": 30}, "reqsw_ticks": 0, "publish_order": "agent_first",
    "prompt_raw": "[STRT=54,1][TAIL=UPRF][IMME]Press [DBTN={dbtn}][MOBI={mobi}] ![TIME=-1]",
    "prompt_text": "Press  !", "arm_after_111": 12, "walk_off_s": 2.0, "walk_back_s": 2.0, "exit_wait_ticks": 65,
    "exit_to": None, "choice_lines": ("es", "No"), "encore": True, "slides": True,
    "lost": (), "miss_read": (), "score_override": None, "extra_prompts": 0, "menu_on_triangle": False,
    "unsubstituted_once": False, "unsubstituted_frames": 1, "replay_on_no": False, "tutorial": True}
#: Blank's and Zidane's x where the fight begins (arbitrary: only a slide's delta is ever read). Blank is published
#: as the field object sid 20 (64 e0 t0 ip449's InitObject(20)); Zidane is the player.
CHANBARA_BLANK_X, CHANBARA_ZIDANE_X = 600.0, 0.0
#: The stage handshake after the fight's last pass (the Byte[26]/Bit[230] sync, e2's stage := 4 the tick after):
#: an ESTIMATE in ticks.
CHANBARA_SYNC_TICKS = 3
#: 64 e0 t0's gEventGlobal stores at entrance 100 (research/o4_design.md 4.4, 4.6): ``(ip, byte, width, value, bit)``.
CHANBARA_MAIN_INIT = ((22, 191 >> 3, "Bit", 0, 191), (49, 184 >> 3, "Bit", 0, 184), (57, 9, "Int16", -1, -1),
                      (119, 13, "Byte", 0, -1), (138, 11, "Int16", -1, -1), (200, 14, "Byte", 0, -1),
                      (416, 3815 >> 3, "Bit", 0, 3815), (425, 475, "Byte", 0, -1), (475, 8, "Byte", 125, -1))


def _machine_knobs(defaults: dict, given, what: str) -> dict:
    """A machine beat's knobs over its defaults, STRICT: an unknown knob is a ValueError (a typo is never a default),
    and so is a ``publish_order`` not in :data:`PUBLISH_ORDERS`."""
    if not isinstance(given, dict):
        raise ValueError(f"{what}: its knobs are a dict, not {given!r}")
    unknown = sorted(set(given) - set(defaults))
    if unknown:
        raise ValueError(f"{what}: unknown knob(s) {unknown} -- its knobs are {sorted(defaults)}")
    out = {**defaults, **given}
    if out["publish_order"] not in PUBLISH_ORDERS:
        raise ValueError(f"{what}: publish_order {out['publish_order']!r} is not one of {PUBLISH_ORDERS}")
    return out


class _Win:
    """One dialog window a machine beat lists (activeDialogList's order is the beat's list's): its ``slot`` (the
    script's window id), its ``kind`` -- "page" and "choice" take the UI's Confirm, "prompt" and "keyon" only a script's
    read ([TIME=-1] inhibits UI paging, DialogBoxSymbols.cs:811-826) -- the agent's ``text`` (rendered) and ``raw``
    (phrase_raw), and its life: OPENING (a page or a choice takes Confirm only once complete: the box grows from 0.3 to
    1 at deltaTime / 0.15 and AfterShown follows a frame on, DialogAnimator.cs:43-47, :61-126 -- ``open_s`` of the
    fake's clock, then ``open_frames``; research/o4_design.md 0.3 #1), listed, then CLOSING (one WaitForEndOfFrame,
    then 0 -> 0.6 at deltaTime / 0.15, DialogAnimator.cs:144-173 -- ``close_frames``, then ``close_s``; 0.2 #1) until it
    is gone from the list."""

    def __init__(self, fake, slot: int, kind: str, text: str, raw: str, *, unsub: str | None = None):
        self.slot, self.kind, self.text, self.raw = slot, kind, text, raw
        self.frame0, self.rt0 = fake.frame, fake.rt
        self.ready_at = None                       # the frame its opening ends on (a page's, a choice's)
        self.complete = kind not in ("page", "choice")
        self.closing = self.gone = False
        self.tween_frame = self.tween_rt = None
        self.unsub, self.unsub_mark = unsub, fake.publish_frame      # H12: the text its FIRST publish shows
        self.header, self.lines, self.cursor, self.answer = "", [], 0, None   # a choice's

    def shown(self) -> str:
        return self.text if self.unsub is None else self.unsub

    def close(self, fake, close_frames: int) -> None:
        if not self.closing:
            self.closing = True
            self.tween_frame = fake.frame + int(close_frames)

    def timers(self, fake, k: dict) -> None:
        """At a frame's start: the opening's end, the close tween's end, and (H12) an unsubstituted text's first
        publish behind it."""
        if not self.complete:
            if self.ready_at is None and fake.rt - self.rt0 >= float(k["open_s"]) - 1e-9:
                self.ready_at = fake.frame + int(k["open_frames"])
            if self.ready_at is not None and fake.frame >= self.ready_at:
                self.complete = True
        if self.closing and not self.gone:
            if self.tween_rt is None and fake.frame >= self.tween_frame:
                self.tween_rt = fake.rt
            if self.tween_rt is not None and fake.rt - self.tween_rt >= float(k["close_s"]) - 1e-9:
                self.gone = True
        if self.unsub is not None and fake.publish_frame - self.unsub_mark >= int(k.get("unsubstituted_frames", 1)):
            self.unsub = None


class _Machine:
    """What the machine beats share (research/o4_design.md 3, "The input model"). Per FRAME: the LEVEL -- the OR of
    the bits of every key the agent holds this frame (its down-at-frame+1 Schedule, :meth:`FakeGame._is_held`), each
    name mapped the AGENT's way (:data:`AGENT_CONTROL` -> :data:`CONTROL_BITS`); FPSManager's delayed inputs -- after a
    frame that ran a field tick the accumulator is this frame's level (FlushDelayedInputs), after one that ran none it
    ORs it in (CollectDelayedInputs), FPSManager.cs:77-139 (the release bookkeeping, which matters only for a key
    released and pressed again between two ticks, modelled as the plain OR); and the UI's own per-frame reads (a key's
    DOWN frame: a page's Confirm, a choice's cursor). Per whole field TICK of the frame (floor(ticks_run) crossings:
    whole ticks in "quantized" mode, every other frame at 60 fps "mean"): the edge ETb.ProcessKeyEvents makes, ``keyon
    = acc & ~skey; skey = acc`` (ETb.cs:50-56) -- one edge a press, none for a key held across ticks -- and the beat's
    script. Then its windows are published. A frame runs once, in the slot its ``publish_order`` names; a warp (any new
    visit) cuts the beat with its scene."""

    def __init__(self, fake, knobs: dict):
        self.k = knobs
        self.windows: list = []
        self.tick = 0
        self.acc = self.skey = self.keyon = 0
        self._ran = 1                              # the ticks the previous frame ran: the first frame flushes
        self._ticks_seen = fake.ticks_run
        self._frame_seen = fake.frame              # a frame is run once (a frozen counter repeats its number)
        self.visit0 = fake._visit
        self.done = False
        self.script = None
        self.queued: list = []                     # windows a test's director asked for (:meth:`queue_window`)

    # -- the agent's keys, as the engine reads them
    def level(self, fake) -> int:
        bits = 0
        for name in list(fake.held):
            if fake._is_held(name):
                bits |= CONTROL_BITS.get(AGENT_CONTROL.get(str(name).lower(), ""), 0)
        return bits & 0x3FFFFFF

    def downs(self, fake) -> set:
        """The Controls whose key goes DOWN on this frame -- the agent reports Down on exactly its down frame
        (HarnessAgent.cs:60-77): what the UI's per-frame reads take."""
        out = set()
        for name, at in list(fake.down_at.items()):
            if at == fake.frame and fake._is_held(name):
                c = AGENT_CONTROL.get(str(name).lower())
                if c is not None:
                    out.add(c)
        return out

    def log(self, fake, event: str, w: _Win) -> None:
        fake.machine_log.append({"event": event, "kind": w.kind, "slot": w.slot, "text": w.text, "frame": fake.frame,
                                 "tick": self.tick, "rt": round(fake.rt, 6)})

    def open(self, fake, slot: int, kind: str, text: str, raw: str, *, unsub: str | None = None) -> _Win:
        """A window joins the list THIS tick (ETb.NewMesWin: a window of its slot still open is closed first -- one
        already in its tween keeps it, ``ForceClose`` being a no-op there; research/o4_design.md 0.2 #1)."""
        for old in self.windows:
            if old.slot == slot and not old.closing:
                old.close(fake, self.k["close_frames"])
                self.log(fake, "close", old)
        w = _Win(fake, slot, kind, text, raw, unsub=unsub)
        self.windows.append(w)
        self.log(fake, "open", w)
        return w

    def close(self, fake, w: _Win) -> None:
        if not w.closing:
            w.close(fake, self.k["close_frames"])
            self.log(fake, "close", w)

    def queue_window(self, slot: int, kind: str, text: str, raw: str) -> None:
        """A test's hand from ANOTHER thread (a director): a window this beat opens at its next frame -- a page the
        script never waits on (an unclaimed dialog, a page in a quiet window). The list is the loop thread's, so the
        director only queues; the beat's own frame opens it."""
        self.queued.append((int(slot), str(kind), str(text), str(raw)))

    # -- the frame
    def frame(self, fake, slot: str) -> None:
        if self.done:
            return
        if slot == "agent_last" and fake._visit != self.visit0:
            self.cut(fake)                         # a warp or a scripted move: a new visit ends the beat
            return
        if slot != self.k["publish_order"] or fake.frame == self._frame_seen:
            return
        self._frame_seen = fake.frame
        while self.queued:
            self.open(fake, *self.queued.pop(0))
        for w in self.windows:
            was = w.gone
            w.timers(fake, self.k)
            if w.gone and not was:
                self.log(fake, "gone", w)
        self.windows = [w for w in self.windows if not w.gone]
        self.ui(fake)
        n = int(math.floor(fake.ticks_run + 1e-9) - math.floor(self._ticks_seen + 1e-9))
        self._ticks_seen = fake.ticks_run
        level = self.level(fake)
        self.acc = level if self._ran > 0 else (self.acc | level)     # Flush / CollectDelayedInputs
        self._ran = n
        for _ in range(max(0, n)):
            self.keyon = self.acc & ~self.skey                        # ETb.ProcessKeyEvents
            self.skey = self.acc
            self.tick += 1
            if fake.ui_state == "FieldHUD":                           # a menu up holds the field (H12)
                self.on_tick(fake)
            if self.done:
                return
        self.publish(fake)

    def ui(self, fake) -> None:
        """The UI's per-frame reads: a Confirm going down closes a COMPLETE page (in its opening it is dropped,
        Dialog.cs:762-797); a complete choice's cursor moves on Up / Down and a Confirm answers it at the cursor (in its
        opening a Confirm only sets SelectChoice to its default, Dialog.cs:798-802: nothing moves, nothing closes)."""
        downs = self.downs(fake)
        if not downs:
            return
        for w in self.windows:
            if w.closing or not w.complete:
                continue
            if w.kind == "page" and "confirm" in downs:
                self.close(fake, w)
            elif w.kind == "choice":
                if "down" in downs:
                    w.cursor = min(len(w.lines) - 1, w.cursor + 1)
                if "up" in downs:
                    w.cursor = max(0, w.cursor - 1)
                if "confirm" in downs:
                    w.answer = w.cursor
                    fake.answered.append(w.cursor)
                    self.close(fake, w)

    def on_tick(self, fake) -> None:
        try:
            next(self.script)
        except StopIteration:
            if not self.done:
                self.finish(fake)

    def publish(self, fake) -> None:
        """The beat's windows as the agent publishes them: ``texts`` / ``phrase_raw`` per listed window (a closing one
        until its tween ends), a choice's ``choice`` and menu group ('' while it opens or closes, Dialog.Choice ready)."""
        listed = [w for w in self.windows if not w.gone]
        fake.texts = [w.shown() for w in listed]
        fake.raw_texts = [w.raw for w in listed]
        ch = next((w for w in listed if w.kind == "choice"), None)
        if ch is None:
            fake.choice = None
            fake.menu = {"selected": None, "hovered": None, "label": None, "group": None}
            return
        fake.choice = {"selected": ch.cursor, "count": len(ch.lines), "active": list(range(len(ch.lines))),
                       "disabled": [], "options": [ch.header, *ch.lines]}
        ready = ch.complete and not ch.closing
        button = f"Choice#{ch.cursor}" if ready else None
        fake.menu = {"selected": button, "hovered": None, "label": None, "group": "Dialog.Choice" if ready else "",
                     "button": button}

    # -- the end
    def end(self, fake) -> None:
        """What the beat set up and must take down (a subclass's bodies)."""

    def finish(self, fake) -> None:
        """The beat's own end: popped, and the scene moves on (:meth:`FakeGame._next_beat`)."""
        self.done = True
        self.end(fake)
        fake._machine = None
        if fake._beats:
            fake._beats.pop(0)
        fake._next_beat()

    def cut(self, fake) -> None:
        """A warp (any new visit) cut the beat: it and its scene are gone, its windows with them."""
        self.done = True
        self.end(fake)
        fake._machine = None
        fake._beats, fake._beat_phase = [], None
        fake.texts, fake.raw_texts, fake.choice = [], [], None
        fake.menu = {"selected": None, "hovered": None, "label": None, "group": None}


class _KeyonPairBeat(_Machine):
    """H10 (research/o4_design.md 3): THE KEYON PAIR -- 64's 105/106 and 107/108, 150's 98/99, staged on their own.
    Window a, then b ``lag_ticks`` later, both [INCS][TIME=-1] (a Confirm does not page them: ``kind`` "keyon"); from
    ``gate_ticks`` after b opened (the INCS/250 gate, e13 ip825-859) each tick reads ``keyon & (Confirm | Special)``
    (ip865-885) -- an edge before the gate is consumed by its tick and lost -- and the first such edge closes both
    (ip888/891). The beat ends once both are gone (their tweens run out)."""

    def __init__(self, fake, knobs):
        k = _machine_knobs(KEYON_PAIR_DEFAULTS, knobs, "keyon_pair")
        texts = k["texts"]
        if not isinstance(texts, (list, tuple)) or len(texts) != 2 or not all(isinstance(t, str) for t in texts):
            raise ValueError(f"keyon_pair: texts is the pair's two texts, not {texts!r}")
        raw = k["raw"] if k["raw"] is not None else list(texts)
        if not isinstance(raw, (list, tuple)) or len(raw) != 2:
            raise ValueError(f"keyon_pair: raw is the pair's two sources, not {raw!r}")
        k["raw"] = list(raw)
        super().__init__(fake, k)
        self.script = self._script(fake)

    def _script(self, fake):
        k = self.k
        a = self.open(fake, 1, "keyon", k["texts"][0], k["raw"][0])
        for _ in range(int(k["lag_ticks"])):
            yield
        b = self.open(fake, 0, "keyon", k["texts"][1], k["raw"][1])
        for _ in range(int(k["gate_ticks"])):
            yield
        while not self.keyon & KEYON_PAIR_BITS:
            yield
        self.close(fake, a)
        self.close(fake, b)
        while not (a.gone and b.gone):
            yield


class _ChanbaraBeat(_Machine):
    """H11 (research/o4_design.md 3): THE CHANBARA VISIT -- 64 at entrance 100 from its arrival to Field(150), one beat
    (the score pages depend on the fight). Main_Init's stores (trace on: ``script_store``, the engine's values); stage 1,
    the walk-in (``walk_in_s``); stage 2, the KEYON pair 105/106 (105 three ticks into the stage, 106 at fifteen: e20's
    Wait(3), e13's Wait(15)) and its gate; Wait(5); the tutorial 111 (a page: WindowSync, slot 6) -- T0 the tick it is
    gone; the first arm at T0 + ``arm_after_111``; stage 3, THE FIGHT; the stage handshake; stage 4, the pair 107/108
    (at 25 and 37: e20's Wait(25), e13's Wait(37)); stage 5, the walk-off; stage 6, the score (and on Yes stages 7, 8 --
    the 109/110 pair, no 111 -- and 3 again); stage 9, Field(``exit_to``).

    THE FIGHT, per field tick in the engine's object order -- e2, e4, e3, e13, e20 (Main_Init's InitCode(4),
    InitCode(3), InitObject 5, 6, 13, 20 append in that order, Obj.cs:31-45; EBin.ProcessCode walks the list once a
    tick):
      * e4 (``sa`` >= 2): ``Byte[52] > 0 and Int16[34] < 50`` refills TimeLeft to 50 (EMinigame.cs:23-30);
      * e3 (a prompt up, ``Byte[47] == 1``): the eight checks in ip order (:data:`CHANBARA_KEYS`) on this tick's EDGE,
        Start held a LEVEL miss (ip412), CloseWindow(1) on a hit or a miss (ip459/484), then TimeLeft-- (the hit tick
        decrements too: a hit at the j-th poll credits 50 - j);
      * e13: Zidane's slide, a tick behind Blank's (0.3 #3);
      * e20, the pass machine: ARM (the roll and its filters, ip462-707; while ``Int16[34] < 49``: Byte[47] 1, the
        no-repeat Byte[44], TimeLeft 50 and window 112 + Byte[46] LISTED THIS TICK, ip721-852), REACT for
        ``reaction[Byte[45]] + reqsw_ticks`` ticks (a LEFT / RIGHT hit before it: SByte[38] -/+ 1 and the slide, Blank
        -60 a tick from S+1 to -300 after S+5, Zidane from S+2 to S+6), then the WAIT while ``TimeLeft > 0 and
        Byte[47] == 1``, then SCORE (a timeout: Byte[47] 3, CloseWindow; a hit: I30 += TimeLeft, I32 += I40, I40 + 1; a
        miss: I40 0; I42 the max; Byte[45] := Byte[46]; Int16[34] + 1) and the next ARM IN THE SAME TICK -- so a timeout,
        or a hit later than the reaction, re-arms at once, the old window still in its tween beside the new (0.2 #1, #2).
        Pass 49 arms nothing: the PHANTOM pass credits pass 48's result again (I32 1225, I42 50 on 49 hits).

    The score (e4 t1 ip208-537): (I30 + I32) // 29; EMinigame's hook (``bonus_fires``: +30% at ``sa`` >= 1, then
    "Encore" at >= 75); H12's ``score_override``; the clamp; the gil; ip338's store when Byte[475] is below it; 120/121
    (max combo below 50) or 122, Wait(5), 123 and ip390's Bit[3815] := 1 AFTER 123; Wait(10); the choice by band (124
    < 25, 125 < 50, 126 < 75, else 127) with its cursor on Yes (0); No: Wait(15), 128, the gil; Yes: the encore.
    ``fake.chanbara_log`` keeps every prompt's arm tick, edge tick and true j."""

    def __init__(self, fake, knobs):
        k = _machine_knobs(CHANBARA_DEFAULTS, knobs, "chanbara")
        if not isinstance(k["exit_to"], int) or isinstance(k["exit_to"], bool):
            raise ValueError(f"chanbara: exit_to (the field Field(150) lands in) is required, not {k['exit_to']!r}")
        k["gates"] = {**CHANBARA_DEFAULTS["gates"], **{str(m): int(t) for m, t in (knobs.get("gates") or {}).items()}}
        k["reaction"] = {**CHANBARA_DEFAULTS["reaction"],
                         **{("others" if r == "others" else int(r)): int(t)
                            for r, t in (knobs.get("reaction") or {}).items()}}
        k["lost"], k["miss_read"] = {int(n) for n in k["lost"]}, {int(n) for n in k["miss_read"]}
        k["choice_lines"] = list(k["choice_lines"])
        super().__init__(fake, k)
        import random
        self.rng = random.Random(k["seed"])
        self.v = dict.fromkeys(("I30", "I32", "I34", "I36", "I40", "I42", "I48", "I50", "sb38", "sb39", "b27", "b44",
                                "b45", "b46", "b47", "b52"), 0)
        self.fight = 0                             # fights begun (the encore's is the second)
        self.instance = 0                          # prompts armed in this fight (1-based)
        self.prompt = self.row = None              # the armed prompt's window and its chanbara_log row
        self.phase = None                          # e20's: "arm" / "react" / "wait" / "done"
        self.arm_tick = self.react = 0
        self.slides: list = []                     # [body, x0, dir, start tick]
        self.t0_tick = None
        self.field = fake.field_id
        self.blank = {"x": CHANBARA_BLANK_X, "z": 0.0, "r": 1.0, "sid": 20, "uid": 20, "coll": False}
        fake.blockers[self.field] = [*fake.blockers.get(self.field, ()), self.blank]
        fake.player = [CHANBARA_ZIDANE_X, 0.0, 0.0]
        self.script = self._script(fake)

    # -- the input (H12 ``lost``) and the UI (H12 ``menu_on_triangle``)
    def level(self, fake) -> int:
        if self.phase in ("react", "wait") and self.v["b47"] == 1 and self.instance in self.k["lost"]:
            return 0                               # the agent took the press; the game's input path dropped it
        return super().level(fake)

    def ui(self, fake) -> None:
        if self.k["menu_on_triangle"] and fake.ui_state == "FieldHUD" and "menu" in self.downs(fake):
            fake.ui_state = "MainMenu"             # IsMenuControlEnable on: the menu, the prompt left armed
        super().ui(fake)

    def on_tick(self, fake) -> None:
        super().on_tick(fake)
        if not self.done:
            self._slide_tick(fake)

    def end(self, fake) -> None:
        bodies = fake.blockers.get(self.field)
        if bodies is not None:
            fake.blockers[self.field] = [b for b in bodies if b is not self.blank]

    # -- the script's pieces
    def _wait_s(self, fake, seconds):
        until = fake.rt + float(seconds)
        while fake.rt < until - 1e-9:
            yield

    def _ticks(self, n):
        for _ in range(int(n)):
            yield

    def _open_mes(self, fake, slot: int, kind: str, mes: int, *, numb=None) -> _Win:
        strt, tail, src, text = CHANBARA_MES[mes]
        shown = text.format(numb) if numb is not None else text
        unsub = None
        if numb is not None and self.k["unsubstituted_once"]:
            unsub = text.format(f"[NUMB={1 if mes == 128 else 0}]")
        return self.open(fake, slot, kind, shown, f"[STRT={strt}][TAIL={tail}]{src}", unsub=unsub)

    def _pair(self, fake, a: int, b: int, a_at: int, b_at: int, gate: int):
        """A KEYON pair (H10's rule): a ``a_at`` ticks into the stage (slot 1, e20's), b at ``b_at`` (slot 0, e13's),
        the gate ``gate`` ticks after b opened, then the first Confirm or Special EDGE closes both."""
        yield from self._ticks(a_at)
        wa = self._open_mes(fake, 1, "keyon", a)
        yield from self._ticks(b_at - a_at)
        wb = self._open_mes(fake, 0, "keyon", b)
        yield from self._ticks(gate)
        while not self.keyon & KEYON_PAIR_BITS:
            yield
        self.close(fake, wa)
        self.close(fake, wb)

    def _page(self, fake, mes: int, *, numb=None):
        """WindowSync(5|6, 0, mes): a page the UI's Confirm closes once complete; the script resumes the tick it is
        gone."""
        w = self._open_mes(fake, 6 if mes == 111 else 5, "page", mes, numb=numb)
        while not w.gone:
            yield
        return w

    def _choice(self, fake, mes: int):
        """WindowSync(5, 0, mes): the encore choice, its cursor on Yes -- ETb.sChoose 0 after a flags-0 WindowSync
        (ETb.cs:100-104) -- answered by the UI; the script resumes the tick it is gone, with the answer."""
        strt, tail, src, header = CHANBARA_MES[mes]
        lines = list(self.k["choice_lines"])
        w = self.open(fake, 5, "choice", "\n".join([header, *lines]), f"[STRT={strt}][TAIL={tail}]{src}")
        w.header, w.lines, w.cursor = header, lines, 0
        while not w.gone:
            yield
        return w.answer

    def _script(self, fake):
        k, v = self.k, self.v
        for ip, byte, width, value, bit in CHANBARA_MAIN_INIT:      # 64 e0 t0 at entrance 100
            fake.script_store(0, 0, ip, byte, width, value, bit=bit)
        yield from self._wait_s(fake, k["walk_in_s"])               # stage 1
        first = True
        while True:
            for key in v:                                           # e13 stage 2 / 8: every minigame var := 0
                v[key] = 0
            if first:
                yield from self._pair(fake, 105, 106, 3, 15, k["gates"]["105"])     # stage 2
                yield from self._ticks(5)                           # SetDialogProgression(0), Wait(5)
                if k["tutorial"]:                                   # H12: False -- no 111 (the zone entered on a prompt)
                    yield from self._page(fake, 111)                # WindowSync(6, 0, 111)
                self.t0_tick = self.tick                            # T0: the tick 111 is gone
            else:
                yield from self._pair(fake, 109, 110, 3, 15, k["gates"]["109"])     # stage 8: no tutorial
            yield from self._ticks(k["arm_after_111"])              # Wait(10), the sync, e2's Byte[24] := 3
            yield from self._fight(fake)                            # stage 3
            yield from self._ticks(CHANBARA_SYNC_TICKS)
            yield from self._pair(fake, 107, 108, 25, 37, k["gates"]["107"])        # stage 4
            yield from self._wait_s(fake, k["walk_off_s"])          # stage 5
            again = yield from self._score(fake)                    # stage 6
            if not again:
                break
            yield from self._wait_s(fake, k["walk_back_s"])         # stage 7: the walk back
            first = False
        fake.script_store(2, 1, 331, 8, "Byte", 0)                  # stage 9 (64 e2 t1 ip331)
        yield from self._ticks(k["exit_wait_ticks"])                # Wait(65), ip478
        fake.script_store(2, 1, 528, 2, "Int16", 325)               # ip528
        self.windows = []
        fake.field_id = int(k["exit_to"])                           # Field(150), ip536: a fresh visit
        fake.player = [0.0, 0.0, 0.0]
        fake._visit += 1
        fake._in_trigger.clear()
        self.finish(fake)

    # -- stage 3
    def _fight(self, fake):
        self.fight += 1
        self.instance = 0
        self.v["b45"] = 99                                          # e20 stage 3's start (ip440)
        self.phase = "arm"
        while True:
            self._fight_tick(fake)
            if self.phase == "done":
                return
            yield

    def _fight_tick(self, fake) -> None:
        k, v = self.k, self.v
        # e4: under SwordplayAssistance >= 2 every sid-4 token fetch refills TimeLeft (EMinigame.cs:23-30)
        if k["sa"] >= 2 and v["b52"] > 0 and v["I34"] < 50:
            v["b52"] = 50
        # e3: the poll, only while a prompt is up (ip23)
        if v["b47"] == 1:
            for bit, value, wrong in CHANBARA_KEYS:
                if self.keyon & bit:
                    if v["b46"] == value:
                        v["b47"] = 2
                    else:
                        v["b47"], v["b46"] = 3, wrong
            if self.acc & 0x8:                                      # Start HELD: a level read (B_KEY(8), ip412)
                v["b47"], v["b46"] = 3, 11
            if v["b47"] == 2 and self.instance in k["miss_read"]:  # H12: the right key scored as a miss
                v["b47"], v["b46"] = 3, CHANBARA_WRONG[v["b46"]]
            if v["b47"] in (2, 3):
                self.close(fake, self.prompt)                       # CloseWindow(1), ip459 / ip484
                self.row.update(edge_tick=self.tick, edge_frame=fake.frame, j=self.tick - self.row["arm_tick"],
                                result="hit" if v["b47"] == 2 else "miss")
            if v["b52"] > 0:
                v["b52"] -= 1
        # e20: the pass machine
        if self.phase == "arm":
            self._arm(fake)
        elif self.phase == "react" and self.tick - self.arm_tick >= self.react:
            self.phase = "wait"
        if self.phase == "wait" and not (v["b52"] > 0 and v["b47"] == 1):
            if v["b47"] == 1:                                       # the timeout, ip1397-1424
                v["b47"], v["b46"] = 3, 11
                self.close(fake, self.prompt)
                self.row["result"] = "timeout"
            if v["b47"] == 2:                                       # ip1438-1474
                v["I30"] += v["b52"]
                v["I32"] += v["I40"]
                v["I40"] += 1
            if v["b47"] == 3:                                       # ip1490
                v["I40"] = 0
            if v["I40"] > v["I42"]:                                 # ip1498-1508
                v["I42"] = v["I40"]
            v["b45"] = v["b46"]                                     # ip1534
            v["I34"] += 1                                           # ip1541
            if v["I34"] < 50 + int(k["extra_prompts"]):             # ip1546: the next pass, IN THIS TICK
                self._arm(fake)
            else:
                self.phase = "done"

    def _arm(self, fake) -> None:
        k, v = self.k, self.v
        v["b46"] = 88                                               # the roll and its filters, ip451-707
        while v["b46"] == 88:
            v["b46"] = self.rng.randrange(256) & 7
            if v["sb38"] in (-1, 0) and v["b46"] == 0:
                v["b46"] = 88
            if v["sb38"] in (1, 2) and v["b46"] == 1:
                v["b46"] = 88
            if v["I42"] < 10 and v["b46"] in (3, 5):
                v["b46"] = 88
            if v["I42"] < 15 and v["b46"] == 6:
                v["b46"] = 2
            if v["I42"] < 15 and v["b46"] == 7:
                v["b46"] = 4
            if v["b46"] == v["b44"]:
                v["b46"] = 88
        if v["I34"] < 49 + int(k["extra_prompts"]):                # ip710: passes 0..48 show their prompt
            v["b47"], v["b44"], v["b52"] = 1, v["b46"], 50         # ip721-736
            self.instance += 1
            dbtn = CHANBARA_DBTN[v["b46"]]
            self.prompt = self.open(fake, 1, "prompt", k["prompt_text"],
                                    k["prompt_raw"].format(dbtn=dbtn, mobi=CHANBARA_MOBI[v["b46"]]))
            self.row = {"fight": self.fight, "n": self.instance, "dbtn": dbtn, "value": v["b46"], "arm_tick": self.tick,
                        "arm_frame": fake.frame, "edge_tick": None, "edge_frame": None, "j": None, "result": None,
                        "sb38": v["sb38"], "max_combo": v["I42"]}       # what the roll's filters read
            fake.chanbara_log.append(self.row)
        prev = v["b45"]                                             # the reaction to the previous result (ip861-1370)
        self.react = int(k["reaction"].get(prev, k["reaction"]["others"])) + int(k["reqsw_ticks"])
        if prev in (0, 1):
            d = -1 if prev == 0 else 1
            v["sb38"] += d                                          # ip918 / ip1066
            if k["slides"]:
                self.slides.append(["blank", self.blank["x"], d, self.tick])
                self.slides.append(["player", fake.player[0], d, self.tick + 1])
        self.arm_tick = self.tick
        self.phase = "react"

    def _slide_tick(self, fake) -> None:
        """Each running slide's step this tick: -/+60 a tick, k = 1..5 ticks past its start (Blank's start the arm tick,
        Zidane's a tick later: e13 takes the request the next tick; each loop's i = 0 moves nothing, 0.3 #3)."""
        keep = []
        for s in self.slides:
            body, x0, d, start = s
            kk = self.tick - start
            if kk >= 1:
                x = x0 + d * 60.0 * min(kk, 5)
                if body == "blank":
                    self.blank["x"] = x
                else:
                    fake.player[0] = x
            if kk < 5:
                keep.append(s)
        self.slides = keep

    # -- stage 6
    def _score(self, fake):
        k, v = self.k, self.v
        v["I48"] = (v["I30"] + v["I32"]) // 29                      # ip208
        if k["bonus_fires"]:                                        # EMinigame at sid 4 ip 223 (EMinigame.cs:12-21)
            if k["sa"] >= 1:
                v["I48"] += v["I48"] // 10 * 3
            if v["I48"] >= 75:
                fake.achievements.append("Encore")                  # EMinigame.cs:34-38
        if k["score_override"] is not None:                         # H12: a fork that scores differently
            v["I48"] = int(k["score_override"])
        if v["I48"] > 100:                                          # ip233
            v["I48"] = 100
        if v["I48"] <= 0:                                           # ip252
            v["I48"] = 1
        v["I50"] = ((v["I30"] // 5 + v["I32"]) + v["I42"] * 2 + v["I40"] * 2) // 2 + 1     # ip260
        if v["I48"] == 100:                                         # ip296-307
            v["I50"] = 10000
        fake.chanbara_vars = dict(v)
        if fake.story_bytes[475] < v["I48"]:                        # ip327-338
            fake.script_store(4, 1, 338, 475, "Byte", v["I48"])
        if v["I42"] < 50:                                           # ip346-366
            yield from self._page(fake, 120, numb=v["I48"])
            yield from self._ticks(5)
            yield from self._page(fake, 121)
        else:                                                       # ip375-390
            yield from self._page(fake, 122, numb=v["I48"])
            yield from self._ticks(5)
            yield from self._page(fake, 123)
            fake.script_store(4, 1, 390, 3815 >> 3, "Bit", 1, bit=3815)
        yield from self._ticks(10)                                  # ip399
        if k["encore"]:
            mes = 124 if v["I48"] < 25 else 125 if v["I48"] < 50 else 126 if v["I48"] < 75 else 127
            answer = yield from self._choice(fake, mes)
        else:
            answer = 1
        if answer == 0 or k["replay_on_no"]:                        # ip476: Yes (or H12's replay on No)
            return True
        v["b27"] = 1                                                # ip509
        yield from self._ticks(15)                                  # ip517
        yield from self._page(fake, 128, numb=v["I50"])             # ip531
        fake.gil += v["I50"]                                        # AddGi, ip537
        return False


# ======================================================================== H13-H15: O5's sink and visit beat
#: H13 (research/o5_design.md 3.1): StoryTrace.ChangeRowsPerSite (StoryTrace.cs:56) -- the CHANGING stores the sink emits
#: per site per epoch (:391-394); later ones are counted, as every same-value store after a site's first is.
STORY_CHANGE_ROWS = 64
#: H14 (research/o5_design.md 3.2): a visit beat's step kinds -- each step names exactly one -- and the other keys each
#: kind may carry; anything else is a ValueError when the beat starts (:func:`_visit_steps`), never a default. ``text`` /
#: ``raw`` (a pair's ``texts`` / ``raws``) are what the agent publishes: default ``mes N`` and ``[STRT=0,0]`` + it.
VISIT_STEP_KEYS = {"store": (), "wait": (), "place": (), "grant": (), "field": (), "stairs": (),
                   "page": ("slot", "typing_s", "text", "raw", "async"), "timed": ("slot", "ticks", "text", "raw"),
                   "pair": ("lag", "gate", "texts", "raws"),
                   "choice": ("slot", "header", "lines", "typing_s", "gap", "stale", "branch", "raw"),
                   # H17, H18 (research/o6_design.md 3.3, 3.4): Menu(1, char)'s naming screen -- ``name`` the default it
                   # pre-fills -- and the regions' tag 2 with ExitField's walk-out (its knobs :data:`DOOR_DEFAULTS`)
                   "naming": ("name",), "door": (),
                   # H24 (the O7 review's finding, 159 e16 t1's own order): a page's ``async`` -- WindowAsync: the
                   # script runs on while it is up -- and WaitWindow(slot), the hold until that slot's window is gone
                   "wait_window": ()}
#: H14's knobs and defaults (research/o5_design.md 3.2), each the engine's value or the design's named estimate:
#: ``steps`` (REQUIRED: the visit's step list); ``index`` (its 1-based position in the route -- what H15's per-visit faults
#: are keyed by); ``field_to`` (a ``field`` step's ``to`` -> the field id it lands in); ``donor`` (the visit's
#: ``fake.donor``: on F the member's donor, DataPatchers' EffectiveFieldId; None on S -- and in the donor's own field);
#: O4's tweens (``open_s``/``open_frames``, ``close_s``/``close_frames``); ``ready_lag_frames`` (a choice's frames between
#: its group and ``isChoiceReady``, Dialog.cs:161-164); ``wait_scale`` (the ``wait`` steps only: a test runs 0.25);
#: ``publish_order``; ``bodies`` (the visit's published objects, as ``fake.blockers`` dicts) -- then H15's faults
#: (research/o5_design.md 3.3), each absent by default: see :class:`_VisitBeat` -- and O6's (research/o6_design.md 3.3,
#: 3.5), each absent by default too: ``name_typed`` (the name a naming screen's OK saves: a typed name's stand-in),
#: ``naming_deaf`` (the screen drops its first k Confirms), ``unparsed_frames`` (``{mes: k}``: that window publishes its
#: raw text, tags included, for its first k frames) and ``door_misroute`` (``{door name: field_to key}``: that door's
#: Field() lands there).
VISIT_DEFAULTS = {
    "steps": None, "index": None, "field_to": {}, "donor": None, "open_s": 0.105, "open_frames": 2, "close_s": 0.09,
    "close_frames": 1, "ready_lag_frames": 1, "wait_scale": 1.0, "publish_order": "agent_first", "bodies": (),
    "store_override": None, "grant_at": None, "land_real": None, "reask": False, "stray_confirm_at_ready": False,
    "cursor_to": None, "confirm_deaf": 0, "gap_ticks": None, "no_contour": False, "side_scene_at": None,
    "error_window": None, "name_typed": None, "naming_deaf": 0, "unparsed_frames": None, "door_misroute": None}
#: H17 (research/o6_design.md 3.3): the text tag a page renders as Steiner's name -- [STNR], a constant replace tag
#: (FFIXTextTag.cs:390) resolved to PLAYER.Name of CharacterId 3 (DialogBoxSymbols.cs:67-68) -- and the default
#: NameSettingUI pre-fills (CharacterDefaultName), rendered until a naming screen's OK saves another (``fake.names``).
STNR_TAG, STNR_CHAR, STNR_NAME = "[STNR]", 3, "Steiner"
#: H18 (research/o6_design.md 3.4): a ``door`` step's knobs and defaults -- ``doors``, the regions' tag 2 in ENTRY order
#: (each a dict of :data:`DOOR_KEYS`), and ``speed``, the walk-out's u a field tick (MOVJ at his last controlled frame's
#: speed: HonoUpdate's 60 for a run, FieldMapActorController.cs:210-211). A door holds every :data:`DOOR_NEEDS` --
#: ``name``, ``points`` (IsInQuad's polygon), ``stores`` (its tag 2's stores before its Field(), each a store's 7
#: values), ``ticks`` (its fade's op_22 wait: e23's 25), ``to`` (a ``field_to`` key) -- and optionally ``z_gt`` (its z
#: term: e23 t2 ip38's f[2] > 1333) and ``walkout`` (``{"to": [x, z], "stop_z": z | None}``: ExitField's walk toward
#: MJPOS's point). H22 (research/o7_design.md 3.3): a door's HEIGHT terms ``y_gt`` / ``y_le`` -- his published y past it /
#: at or under it (154 e8 t2 ip38's ``f[1] < -100``: the balcony branch y > 100, the ground branch y <= 100) -- and the
#: step's ``scenes`` (:data:`SCENE_KEYS`): an object's one-shot scene, tested after the doors each tick he has control.
DOOR_DEFAULTS = {"doors": (), "speed": 60.0, "scenes": ()}
DOOR_KEYS = ("name", "points", "z_gt", "y_gt", "y_le", "stores", "ticks", "to", "walkout")
DOOR_NEEDS = ("name", "points", "stores", "ticks", "to")
#: H22 (research/o7_design.md 3.3): a door step's SCENE -- ``name``; ``any_of`` (a dict of ``x_lt`` / ``x_gt`` / ``z_lt``
#: / ``z_gt``: ANY holding fires -- 159 e16 t1 ip390's B_OROR); ``unless_bit`` (the gEventGlobal bit whose 1 disarms it,
#: read from the modelled array -- ip390's ``Bit[3796] == 0``; None: never disarmed); ``steps`` (its pages, stores and
#: waits, :data:`SCENE_STEP_KINDS` -- H24's WaitWindow among them); ``regrant`` ("in_place", the only form: ip711
#: EnableMove with no Walk).
SCENE_KEYS = ("name", "any_of", "unless_bit", "steps", "regrant")
SCENE_NEEDS = ("name", "any_of", "steps")
SCENE_TESTS = ("x_lt", "x_gt", "z_lt", "z_gt")
SCENE_STEP_KINDS = ("page", "store", "wait", "wait_window")
#: A ``stairs`` step's knobs and defaults (153 e3 t1 stage 6, its side scenes, its back door and stage 17;
#: research/o5_design.md 3.2): ``scenes`` (each ``{"points", "z_gt", "pages"}``: e26 -- its quad AND z > 1333 -- and e27,
#: live in stage 6 alone; ``pages`` page steps); ``back_door`` (``{"points", "stores", "exit_ticks", "to"}``: e28, live
#: while he has control, any stage; ``to`` a ``field_to`` key); ``contour`` (the floor-blind stand-in for the height test:
#: a polygon) or ``height_at`` (a callable: the real mesh's PSX y under (x, z), or None off it); ``level`` (ip859's
#: -450); ``teleport_ticks`` (the loss to CreateObject ip1466: the stage switch, op_1C, Wait(1), the Bit[160] test -- an
#: ESTIMATE, R-STAIRS measures); ``teleport``; ``climb`` (stage 17's scripted walk) at ``climb_speed`` (SetWalkSpeed(37),
#: u a tick); ``regrant_at`` (a side scene's Walk(1105,-78), ip1230).
STAIRS_DEFAULTS = {"scenes": (), "back_door": None, "contour": None, "height_at": None, "level": -450,
                   "teleport_ticks": 3, "teleport": (-1165.0, 856.0),
                   "climb": ((-1419.0, 602.0), (-1602.0, 298.0), (-1631.0, 10.0), (-1631.0, -140.0),
                             (-1416.0, -378.0), (-978.0, -554.0), (-329.0, -624.0)),
                   "climb_speed": 37.0, "regrant_at": (1105.0, -78.0)}
#: H15's ``error_window``: the page 153 e0 t0 lists when Byte[13] arrived 2 or 9 (window 56, ip2304: O3's text), and the
#: store its error branch makes where the ambient branch makes ip119's (153 e0 t0 ip97 ``Byte[13] := 9``; 154's is
#: ip101 -- not modelled per field: a test of it reads the V-class, never the row).
VISIT_ERROR_TEXT = "Error Env Play()  Slot=1"
VISIT_ERROR_STORE = (0, 0, 97, 13, "Byte", 9, -1)


def _visit_steps(steps, k: dict, where: str) -> None:
    """H14's steps checked STRICT before the beat runs any (research/o5_design.md 3.2): a list of dicts, each naming
    exactly one kind of :data:`VISIT_STEP_KEYS` and only that kind's keys; a store of its 7 values; a pair of two
    windows; a ``field`` step's ``to`` -- and a back door's -- a ``field_to`` key; a choice's ``lines`` a non-empty list
    of strings, its ``branch`` steps and a ``stairs`` step's side-scene ``pages`` steps themselves; a ``stairs`` step's
    knobs :data:`STAIRS_DEFAULTS`' and -- unless H15's ``no_contour`` -- a ``contour`` or a ``height_at``; H17's
    ``naming`` a character id (an int >= 0) and its ``name`` a non-empty str; H18's ``door`` read by
    :func:`_door_knobs` (research/o6_design.md 3.3, 3.4); H20's ``place`` and ``grant`` two numbers ``[x, z]`` or three,
    ``[x, z, h]`` (research/o7_design.md 3.1); H24's page ``async`` a bool and ``wait_window`` a window slot, an int >=
    0 (the O7 review's finding: 159 e16 t1's WindowAsync / WaitWindow)."""
    if not isinstance(steps, (list, tuple)):
        raise ValueError(f"{where}: the steps are a list, not {steps!r}")
    for i, step in enumerate(steps):
        at = f"{where}[{i}]"
        if not isinstance(step, dict):
            raise ValueError(f"{at}: a step is a dict, not {step!r}")
        kinds = [kd for kd in VISIT_STEP_KEYS if kd in step]
        if len(kinds) != 1:
            raise ValueError(f"{at}: a step names exactly one of {sorted(VISIT_STEP_KEYS)}, not {sorted(step)}")
        kind = kinds[0]
        extra = sorted(set(step) - {kind, *VISIT_STEP_KEYS[kind]})
        if extra:
            raise ValueError(f"{at}: a {kind} step has no {extra} (it takes {list(VISIT_STEP_KEYS[kind])})")
        xz = step.get(kind) if kind in ("place", "grant") else None
        if kind in ("place", "grant") and not (isinstance(xz, (list, tuple)) and len(xz) in (2, 3) and all(
                isinstance(v, (int, float)) and not isinstance(v, bool) for v in xz)):
            raise ValueError(f"{at}: a {kind} is [x, z], or [x, z, h] with h the PSX y it places him at, not {xz!r}")
        if kind == "store" and (not isinstance(step["store"], (list, tuple)) or len(step["store"]) != 7):
            raise ValueError(f"{at}: a store is [sid, tag, ip, byte, width, value, bit], not {step['store']!r}")
        if kind == "pair" and (not isinstance(step["pair"], (list, tuple)) or len(step["pair"]) != 2):
            raise ValueError(f"{at}: a pair is [[mes, slot], [mes, slot]], not {step['pair']!r}")
        if kind == "field" and str(step["field"]) not in k["field_to"]:
            raise ValueError(f"{at}: field {step['field']!r} is not in field_to {sorted(k['field_to'])}")
        if kind == "choice":
            lines = step.get("lines")
            if not isinstance(lines, (list, tuple)) or not lines or not all(isinstance(x, str) for x in lines):
                raise ValueError(f"{at}: a choice's lines are a non-empty list of strings, not {lines!r}")
            for a, sub in dict(step.get("branch") or {}).items():
                _visit_steps(sub, k, f"{at}.branch[{a}]")
        if kind == "stairs":
            s = step["stairs"]
            if not isinstance(s, dict):
                raise ValueError(f"{at}: the stairs' knobs are a dict, not {s!r}")
            unknown = sorted(set(s) - set(STAIRS_DEFAULTS))
            if unknown:
                raise ValueError(f"{at}: the stairs have no knob {unknown} (they take {sorted(STAIRS_DEFAULTS)})")
            if s.get("contour") is None and s.get("height_at") is None and not k["no_contour"]:
                raise ValueError(f"{at}: the stairs' height test needs a contour or a height_at")
            for n, sc in enumerate(s.get("scenes") or ()):
                _visit_steps(sc.get("pages") or [], k, f"{at}.scenes[{n}]")
            bd = s.get("back_door")
            if bd is not None and str(bd.get("to")) not in k["field_to"]:
                raise ValueError(f"{at}: the back door's to {bd.get('to')!r} is not in field_to {sorted(k['field_to'])}")
        if kind == "naming":
            char = step["naming"]
            if not isinstance(char, int) or isinstance(char, bool) or char < 0:
                raise ValueError(f"{at}: a naming step names a character id, an int >= 0, not {char!r}")
            if "name" in step and (not isinstance(step["name"], str) or not step["name"]):
                raise ValueError(f"{at}: a naming step's name is the default it pre-fills, a non-empty str, not "
                                 f"{step['name']!r}")
        if kind == "page" and not isinstance(step.get("async", False), bool):
            raise ValueError(f"{at}: a page's async is a bool (WindowAsync), not {step['async']!r}")
        if kind == "wait_window":
            slot = step["wait_window"]
            if not isinstance(slot, int) or isinstance(slot, bool) or slot < 0:
                raise ValueError(f"{at}: a wait_window step names a window slot, an int >= 0, not {slot!r}")
        if kind == "door":
            _door_knobs(step["door"], k, at)


def _door_knobs(d, k: dict, at: str) -> None:
    """H18's ``door`` step checked STRICT (research/o6_design.md 3.4): its knobs :data:`DOOR_DEFAULTS`' -- ``speed`` a
    positive number, ``doors`` a non-empty list in entry order -- and each door a dict holding every
    :data:`DOOR_NEEDS` and nothing outside :data:`DOOR_KEYS`: ``points`` a polygon of three points or more, each
    store its 7 values, ``ticks`` an int >= 0, ``to`` a ``field_to`` key, ``z_gt`` a number, ``walkout`` ``{"to":
    [x, z], "stop_z": z | None}``. H22 (research/o7_design.md 3.3): a door's ``y_gt`` and ``y_le`` numbers; the step's
    ``scenes`` a list, each a dict holding every :data:`SCENE_NEEDS` and nothing outside :data:`SCENE_KEYS` -- ``name`` a
    non-empty str, ``any_of`` a non-empty dict of :data:`SCENE_TESTS` to numbers, ``unless_bit`` None or an int >= 0,
    ``steps`` visit steps (:func:`_visit_steps`) of :data:`SCENE_STEP_KINDS` alone, ``regrant`` "in_place". A ValueError
    names the first fault."""
    if not isinstance(d, dict):
        raise ValueError(f"{at}: the door's knobs are a dict, not {d!r}")
    unknown = sorted(set(d) - set(DOOR_DEFAULTS))
    if unknown:
        raise ValueError(f"{at}: the door has no knob {unknown} (it takes {sorted(DOOR_DEFAULTS)})")
    speed = d.get("speed", DOOR_DEFAULTS["speed"])
    if not isinstance(speed, (int, float)) or isinstance(speed, bool) or not speed > 0:
        raise ValueError(f"{at}: the door's walk-out speed is a positive number of u a tick, not {speed!r}")
    doors = d.get("doors")
    if not isinstance(doors, (list, tuple)) or not doors:
        raise ValueError(f"{at}: a door step's doors are a non-empty list, in entry order, not {doors!r}")
    for n, door in enumerate(doors):
        w = f"{at}.doors[{n}]"
        if not isinstance(door, dict):
            raise ValueError(f"{w}: a door is a dict, not {door!r}")
        if [x for x in DOOR_NEEDS if x not in door] or set(door) - set(DOOR_KEYS):
            raise ValueError(f"{w}: a door holds {list(DOOR_NEEDS)} and optionally z_gt, y_gt, y_le and walkout, not "
                             f"{sorted(door)}")
        if not isinstance(door["points"], (list, tuple)) or len(door["points"]) < 3:
            raise ValueError(f"{w}: a door's points are a polygon, [[x, z], ...] of three or more, not "
                             f"{door['points']!r}")
        for s in door["stores"]:
            if not isinstance(s, (list, tuple)) or len(s) != 7:
                raise ValueError(f"{w}: a store is [sid, tag, ip, byte, width, value, bit], not {s!r}")
        if not isinstance(door["ticks"], int) or isinstance(door["ticks"], bool) or door["ticks"] < 0:
            raise ValueError(f"{w}: a door's ticks are an int >= 0 (its fade's wait), not {door['ticks']!r}")
        if str(door["to"]) not in k["field_to"]:
            raise ValueError(f"{w}: the door's to {door['to']!r} is not in field_to {sorted(k['field_to'])}")
        for term in ("z_gt", "y_gt", "y_le"):                     # H22: the height terms beside the z term
            v = door.get(term)
            if v is not None and (not isinstance(v, (int, float)) or isinstance(v, bool)):
                raise ValueError(f"{w}: a door's {term} is a number, not {v!r}")
        wo = door.get("walkout")
        if wo is not None and (not isinstance(wo, dict) or "to" not in wo or set(wo) - {"to", "stop_z"}
                               or not isinstance(wo["to"], (list, tuple)) or len(wo["to"]) != 2):
            raise ValueError(f"{w}: a door's walkout is {{'to': [x, z], 'stop_z': z | None}}, not {wo!r}")
    scenes = d.get("scenes", DOOR_DEFAULTS["scenes"])
    if not isinstance(scenes, (list, tuple)):
        raise ValueError(f"{at}: a door step's scenes are a list, not {scenes!r}")
    for n, sc in enumerate(scenes):                               # H22: an object's one-shot scene
        w = f"{at}.scenes[{n}]"
        if not isinstance(sc, dict) or [x for x in SCENE_NEEDS if x not in sc] or set(sc) - set(SCENE_KEYS):
            raise ValueError(f"{w}: a scene holds {list(SCENE_NEEDS)} and optionally unless_bit and regrant, not "
                             f"{sorted(sc) if isinstance(sc, dict) else sc!r}")
        if not isinstance(sc["name"], str) or not sc["name"]:
            raise ValueError(f"{w}: a scene's name is a non-empty str, not {sc['name']!r}")
        tests = sc["any_of"]
        if not isinstance(tests, dict) or not tests or set(tests) - set(SCENE_TESTS) or not all(
                isinstance(v, (int, float)) and not isinstance(v, bool) for v in tests.values()):
            raise ValueError(f"{w}: a scene's any_of is a non-empty dict of {list(SCENE_TESTS)} to numbers, not "
                             f"{tests!r}")
        bit = sc.get("unless_bit")
        if bit is not None and (not isinstance(bit, int) or isinstance(bit, bool) or bit < 0):
            raise ValueError(f"{w}: a scene's unless_bit is None or a gEventGlobal bit, an int >= 0, not {bit!r}")
        if sc.get("regrant", "in_place") != "in_place":
            raise ValueError(f"{w}: a scene's regrant is 'in_place' (EnableMove where he stands, no Walk), not "
                             f"{sc['regrant']!r}")
        _visit_steps(sc["steps"], k, f"{w}.steps")
        odd = [s for s in sc["steps"] if not any(kd in s for kd in SCENE_STEP_KINDS)]
        if odd:
            raise ValueError(f"{w}: a scene's steps are pages, stores and waits ({list(SCENE_STEP_KINDS)}), not {odd!r}")


class _VisitBeat(_Machine):
    """H14 (research/o5_design.md 3.2): ONE FIELD VISIT, from its arrival to its Field(), played as a STEP LIST per field
    tick, with O4's window model unchanged (:class:`_Win`: the opening drop, the close tween; :class:`_Machine`: the
    per-frame UI Confirm, the per-tick KEYON edge, the publication order). A scene of visit beats plays a route: each
    ends by moving the field (a fresh visit) and finishing, so the next starts in the new field. The steps
    (:data:`VISIT_STEP_KEYS`, checked strict by :func:`_visit_steps`):

      * ``{"store": [sid, tag, ip, byte, width, value, bit]}`` -- a script store (:meth:`FakeGame.script_store`; H13
        decides its row); ``value`` "answer" stores the last choice's answer (153 e3 t1 ip1741's ``SYSVAR[9]``);
      * ``{"wait": ticks}`` -- the script's op_22 / walks, scaled by ``wait_scale``;
      * ``{"place": [x, z]}`` -- a scripted move of the player, control untouched;
      * ``{"page": mes, ...}`` -- WindowSync (or WindowAsync + WaitWindow): listed THIS tick (ETb.NewMesWin), complete
        after its opening; with ``typing_s`` its text types on for that long of the game's clock after the opening -- a
        Confirm then only completes it (Dialog.cs:798-808), the next closes it; the script resumes the tick it is gone.
        H24: ``async`` True is WindowAsync ALONE -- listed this tick, the script goes on at once while it is up (159 e16
        t1's RunAnimation + WaitAnimation pairs and stores under pages 296, 298, 299 and 300);
      * ``{"wait_window": slot}`` -- H24's WaitWindow(slot): the script holds until no window of that slot is listed;
      * ``{"timed": mes, "ticks": t, ...}`` -- a [TIME=t] window: Confirm-inert, closing itself ``t`` ticks after it
        opened (then its tween); the script does not wait;
      * ``{"pair": [[mes, slot], [mes, slot]], "lag", "gate"}`` -- H10's KEYON pair (:meth:`_pair`);
      * ``{"choice": mes, "lines", ...}`` -- ``gap`` ticks after the previous window is GONE, a WindowSync choice GATED as
        the engine gates SelectChoice (:meth:`_choice`, :meth:`ui`, :meth:`publish`); then ``branch[str(answer)]``;
      * ``{"grant": [x, z]}`` -- EnableMove: control, the player at (x, z);
      * ``{"stairs": knobs}`` -- 153's stage 6, its side scenes and back door, the height test and stage 17
        (:meth:`_stairs`, :data:`STAIRS_DEFAULTS`);
      * ``{"naming": char, "name": default}`` -- H17 (research/o6_design.md 3.3): Menu(1, char), the naming screen over
        the field -- ui "NameSetting", no window -- which holds the script until its OK (:meth:`_naming`, :meth:`ui`);
      * ``{"door": knobs}`` -- H18 (research/o6_design.md 3.4): the regions' tag 2 while he has control, ExitField's
        walk-out, the door's stores and its Field() (:meth:`_door`, :data:`DOOR_DEFAULTS`);
      * ``{"field": to}`` -- Field(): the field becomes ``field_to[to]`` (a fresh visit, control off), the beat finishes.

    H17's NAME ON THE PAGE: every window's text has [STNR] rendered as the name the naming screen saved
    (``fake.names``), the default until one is saved (:meth:`open`); its raw keeps the tag, as phrase_raw does.

    H15's faults (research/o5_design.md 3.3), each absent by default: ``store_override`` ``{ip: value}`` (a fork that
    stores another value at a site); ``grant_at`` ``{index: [x, z]}`` (control granted after that visit's leading stores,
    where the bytes grant none -- then the script holds); ``land_real`` ``{to: id}`` (a ``field`` step landing in the
    REAL id: a Field() the chain did not retarget); ``reask`` (a choice asked again once its answer is gone, ``gap`` ticks
    later); ``stray_confirm_at_ready`` (the fake itself answers a choice the first frame it takes answers -- input no
    witness saw); ``cursor_to`` ``{"after_frames": n, "index": i}`` (the game moves the cursor to ``i`` ``n`` frames after
    the first Down/Up that moved it: outside input after the driver's select) or ``{"at_confirm": True, "index": i}``
    (in the frame the answering Confirm goes down, after every published sample); ``confirm_deaf`` (a choice drops its
    first k Confirms once it takes answers); ``gap_ticks`` (every choice's ``gap``); ``no_contour`` (the height test never
    fires); ``side_scene_at`` (the n-th MOVING tick of a stage-6 period -- or a list, one per period: a side scene fires
    wherever he stands, the first scene's pages: a mis-walk's stand-in); ``error_window`` ``{index: value}`` (Byte[13]
    arrived ``value``: the leading stores take the error branch's :data:`VISIT_ERROR_STORE`, and window 56,
    :data:`VISIT_ERROR_TEXT`, waits). ``fake.visit_log`` keeps every step's start.

    O6's faults (H17, H19: research/o6_design.md 3.3, 3.5), each absent by default: ``name_typed`` (the name the naming
    screen's OK saves -- outside input typed into the box: the page witness's V13); ``naming_deaf`` (the screen drops
    its first k Confirms -- 4 or more and accept_name raises: the stuck screen); ``unparsed_frames`` ``{mes: k}`` (that
    window publishes its RAW text, tags included, for its first k frames: the TextParser's ``ParsedText =
    InitialText`` before Parse, TextParser.cs:54-60 -- a state the engine is not expected to publish, kept to test the
    page witness's guard); ``door_misroute`` ``{door name: field_to key}`` (that door's Field() lands there: a
    misrouted fork operand's stand-in)."""

    def __init__(self, fake, knobs):
        k = _machine_knobs(VISIT_DEFAULTS, knobs, "visit")
        if not isinstance(k["steps"], (list, tuple)) or not k["steps"]:
            raise ValueError(f"visit: steps is a non-empty list of steps, not {k['steps']!r}")
        k["field_to"] = {str(t): int(f) for t, f in dict(k["field_to"] or {}).items()}
        k["land_real"] = {str(t): int(f) for t, f in dict(k["land_real"] or {}).items()}
        k["store_override"] = {int(ip): int(v) for ip, v in dict(k["store_override"] or {}).items()}
        k["grant_at"] = {int(n): [float(c) for c in xz] for n, xz in dict(k["grant_at"] or {}).items()}
        k["error_window"] = {int(n): int(v) for n, v in dict(k["error_window"] or {}).items()}
        k["unparsed_frames"] = {int(m): int(n) for m, n in dict(k["unparsed_frames"] or {}).items()}
        k["door_misroute"] = {str(d): str(t) for d, t in dict(k["door_misroute"] or {}).items()}
        astray = sorted(t for t in k["door_misroute"].values() if t not in k["field_to"])
        if astray:
            raise ValueError(f"visit: door_misroute sends a door to {astray}, not in field_to {sorted(k['field_to'])}")
        typed, deaf = k["name_typed"], k["naming_deaf"]
        if typed is not None and (not isinstance(typed, str) or not typed):
            raise ValueError(f"visit: name_typed is the name the OK saves, a non-empty str, or None, not {typed!r}")
        if not isinstance(deaf, int) or isinstance(deaf, bool) or deaf < 0:
            raise ValueError(f"visit: naming_deaf is the Confirms the naming screen drops, an int >= 0, not {deaf!r}")
        cur = k["cursor_to"]
        if cur is not None and not (isinstance(cur, dict) and "index" in cur
                                    and set(cur) <= {"index", "after_frames", "at_confirm"}
                                    and ("after_frames" in cur) != bool(cur.get("at_confirm"))):
            raise ValueError(f"visit: cursor_to is {{'after_frames': n, 'index': i}} or {{'at_confirm': True, "
                             f"'index': i}}, not {cur!r}")
        side = k["side_scene_at"]
        k["side_scene_at"] = [] if side is None else [int(side)] if isinstance(side, int) else [int(n) for n in side]
        _visit_steps(k["steps"], k, "visit")
        super().__init__(fake, k)
        self.field = fake.field_id
        donor = k["donor"]
        fake.donor = None if donor is None or int(donor) == fake.field_id else int(donor)
        self.bodies = [dict(b) for b in k["bodies"]]
        if self.bodies:
            fake.blockers[self.field] = [*fake.blockers.get(self.field, ()), *self.bodies]
        self.answer = None                         # the last choice's answer: a store's "answer"
        self.choice_closed = False                 # a choice of this visit closed: the group '' since (:meth:`publish`)
        self.deaf = int(k["confirm_deaf"])         # H15: Confirms still to drop
        self.move = None                           # H15 cursor_to: the move due, (frame, index)
        self.moved = False                         # ...scheduled once
        self.strayed = False                       # H15 stray_confirm_at_ready: fired once
        self.naming = None                         # H17: the naming screen while it is up (:meth:`_naming`)
        self.script = self._script(fake)

    # -- the UI: the engine's gating of a page's type-out and a choice's answer
    def open(self, fake, slot: int, kind: str, text: str, raw: str, *, unsub: str | None = None,
             mes=None) -> _Win:
        """:meth:`_Machine.open`, every window given the type-out state :meth:`ui` reads -- none (``typing_s`` 0) unless
        its step sets one -- so a window a director queues (:meth:`_Machine.queue_window`) is a plain page here too.
        H17 (research/o6_design.md 3.3): its TEXT has [STNR] rendered as the name the naming screen saved -- the
        default until one is (``fake.names``; DialogBoxSymbols.cs:67-68), resolved as the window's parser first runs --
        its raw keeping the tag; and ``mes`` (the step's) keyed in ``unparsed_frames``: its raw text published for its
        first k frames (:meth:`shown`)."""
        text = text.replace(STNR_TAG, fake.names.get(STNR_CHAR, STNR_NAME))
        w = super().open(fake, slot, kind, text, raw, unsub=unsub)
        w.typing_s, w.typed, w.done_frame, w.done_rt = 0.0, False, None, None
        n = self.k["unparsed_frames"].get(mes)
        w.mes, w.unparsed_until = mes, (fake.frame + int(n) if n else None)
        return w

    def typing(self, fake, w) -> bool:
        """Whether a page's or a choice's text still TYPES: complete, ``typing_s`` > 0, not yet completed by a Confirm,
        and less than ``typing_s`` of the game's clock since its opening ended."""
        return (not w.typed and w.typing_s > 0 and w.done_rt is not None
                and fake.rt - w.done_rt < w.typing_s - 1e-9)

    def shown(self, fake, w) -> str:
        """A window's text as the agent publishes it: whole, but for a page or a choice that types -- its first
        character through the opening, then a share of it as its type-out runs (the raw holds the whole source from the
        first sample: ``phrase_raw``). H17: an UNPARSED window (``unparsed_frames``) publishes its raw text, tags
        included, until its k frames are out (research/o6_design.md 3.3)."""
        if w.unparsed_until is not None and fake.frame < w.unparsed_until:
            return w.raw
        if w.kind not in ("page", "choice") or w.typing_s <= 0 or w.typed:
            return w.text
        if w.done_rt is None:
            return w.text[:1]
        frac = (fake.rt - w.done_rt) / w.typing_s
        return w.text if frac >= 1.0 else w.text[:max(1, int(len(w.text) * frac))]

    def take(self, fake, w) -> None:
        """The choice answered at its cursor (Dialog.Hide: the group '' from this Confirm on, Dialog.cs:629)."""
        w.answer = w.cursor
        fake.answered.append(w.cursor)
        self.choice_closed = True
        self.close(fake, w)

    def ui(self, fake) -> None:
        """The UI's per-frame reads, gated as the engine gates them (research/o5_design.md 3.2): a window's opening ends
        (``done_frame``: AfterShown; a choice's cursor then on its default 0, ETb.cs:100-103); a Confirm going down
        closes a COMPLETE page -- or, while it types, only completes its text (Dialog.cs:803-807); on a complete choice
        Down/Up move the cursor (OnItemSelect, CompleteAnimation, :826-835) and a Confirm answers at it -- but in its
        first ``ready_lag_frames`` it commits SelectChoice and hides nothing (:787-789), and while its prompt types it
        only completes the text. The cursor WRAPS: Dialog.cs:157 links the choice buttons with
        NGUIExtension.SetKeyNevigation (NGUIExtension.cs:17-29: the last button's onDown is the first, the first's onUp
        the last), and UIKeyNavigation.GetDown/GetUp take an active onDown/onUp before anything else
        (UIKeyNavigation.cs:94-95, :108-109) -- a Down on the last line lands on the first (O4's machines and the
        generic beat clamp: theirs, pinned, untouched). In a window's opening nothing is taken (a Confirm there sets
        SelectChoice to the default and closes nothing, :798-801). H15's choice faults act here. H17: while the naming
        screen is up, its keys are the screen's (:meth:`_naming_keys`) and no window takes one."""
        k = self.k
        lag = int(k["ready_lag_frames"])
        cur = k["cursor_to"]
        for w in self.windows:
            if w.kind in ("page", "choice") and w.complete and w.done_frame is None:
                w.done_frame, w.done_rt = fake.frame, fake.rt
                if w.kind == "choice":
                    w.cursor = 0
        ch = next((w for w in self.windows if w.kind == "choice" and w.complete and not w.closing), None)
        if ch is not None:
            if self.move is not None and fake.frame >= self.move[0]:
                ch.cursor, self.move = int(self.move[1]), None          # H15: the game moved it
            if k["stray_confirm_at_ready"] and not self.strayed and fake.frame >= ch.done_frame + lag:
                self.strayed = True
                self.take(fake, ch)                                     # H15: answered by no press of the driver's
                return
        downs = self.downs(fake)
        if self.naming is not None:                                     # H17: the naming screen takes the keys
            self._naming_keys(fake, downs)
            return
        if not downs:
            return
        for w in self.windows:
            if w.closing or not w.complete:
                continue
            if w.kind == "page" and "confirm" in downs:
                if self.typing(fake, w):
                    w.typed = True                                      # the type-out completed; nothing closed
                else:
                    self.close(fake, w)
            elif w.kind == "choice":
                before = w.cursor
                if "down" in downs:                                     # WRAPS, as the engine's navigation does
                    w.cursor = (w.cursor + 1) % len(w.lines)
                if "up" in downs:
                    w.cursor = (w.cursor - 1) % len(w.lines)
                if w.cursor != before and cur is not None and "after_frames" in cur and not self.moved:
                    self.moved = True
                    self.move = (fake.frame + int(cur["after_frames"]), int(cur["index"]))
                if "confirm" not in downs or fake.frame < w.done_frame + lag:
                    continue                                            # the ready-lag frame: committed, nothing hidden
                if self.typing(fake, w):
                    w.typed = True
                    continue
                if self.deaf > 0:
                    self.deaf -= 1                                      # H15: dropped
                    continue
                if cur is not None and cur.get("at_confirm"):
                    w.cursor = int(cur["index"])                        # H15: moved in the Confirm's own frame
                self.take(fake, w)

    def publish(self, fake) -> None:
        """The visit's windows as the agent publishes them -- :meth:`_Machine.publish`'s shape, with a typing window's
        text as it stands (:meth:`shown`) and, once a choice of the visit has closed, the menu group '' where it reads
        None: the engine's DisableAllGroup at the answering Confirm (Dialog.cs:629, ButtonGroupState.cs:291) leaves it ''
        until another group activates. A choice in its opening publishes ``selected`` as its ``stale`` cursor (the
        pooled window's last) and the group ''; complete, the group ``Dialog.Choice`` (its ready-lag frames included)."""
        listed = [w for w in self.windows if not w.gone]
        fake.texts = [self.shown(fake, w) for w in listed]
        fake.raw_texts = [w.raw for w in listed]
        ch = next((w for w in listed if w.kind == "choice"), None)
        if ch is None:
            fake.choice = None
            fake.menu = {"selected": None, "hovered": None, "label": None, "group": "" if self.choice_closed else None}
            return
        fake.choice = {"selected": ch.cursor, "count": len(ch.lines), "active": list(range(len(ch.lines))),
                       "disabled": [], "options": [ch.header, *ch.lines]}
        ready = ch.complete and not ch.closing
        button = f"Choice#{ch.cursor}" if ready else None
        fake.menu = {"selected": button, "hovered": None, "label": None, "group": "Dialog.Choice" if ready else "",
                     "button": button}

    def on_tick(self, fake) -> None:
        """A field tick: every [TIME=t] window due closes itself (:meth:`_timed`), then the script runs."""
        for w in self.windows:
            if w.kind == "timed" and not w.closing and self.tick >= w.close_tick:
                self.close(fake, w)
        super().on_tick(fake)

    def end(self, fake) -> None:
        """The visit's bodies are taken down with it, and its donor: the field's own id until a visit says otherwise."""
        bodies = fake.blockers.get(self.field)
        if bodies is not None and self.bodies:
            fake.blockers[self.field] = [b for b in bodies if not any(b is o for o in self.bodies)]
        fake.donor = None

    # -- the script
    def _log(self, fake, at: str, kind: str, **kv) -> None:
        fake.visit_log.append({"index": self.k["index"], "field": fake.field_id, "at": at, "kind": kind,
                               "tick": self.tick, "frame": fake.frame, **kv})

    @staticmethod
    def _ticks(n):
        for _ in range(max(0, int(n))):
            yield

    def _script(self, fake):
        """The visit: its leading stores (Main_Init's prologue), then -- H15 -- ``error_window``'s error branch (the
        stores with the error store for ip119's, window 56, nothing after) or ``grant_at``'s control (then nothing
        after), else every other step in turn (:meth:`_run`)."""
        k = self.k
        steps = list(k["steps"])
        lead = next((i for i, s in enumerate(steps) if "store" not in s), len(steps))
        err = k["error_window"].get(k["index"])
        if err is not None:
            fake.story_bytes[13] = err & 0xFF            # the value it arrived with: no store, no row
            for i, step in enumerate(steps[:lead]):
                self._log(fake, str(i), "store")
                s = step["store"]
                self._store(fake, VISIT_ERROR_STORE if (int(s[3]), str(s[4])) == (13, "Byte") else s)
            self._log(fake, "error", "page")
            yield from self._page(fake, {"page": 56, "slot": 1, "text": VISIT_ERROR_TEXT, "raw": VISIT_ERROR_TEXT})
            return
        yield from self._run(fake, steps[:lead], "")
        grant = k["grant_at"].get(k["index"])
        if grant is not None:
            self._log(fake, "grant_at", "grant")
            self._grant(fake, grant)
            while True:
                yield
        yield from self._run(fake, steps[lead:], "", base=lead)

    def _run(self, fake, steps, path: str, base: int = 0):
        """Each step in turn, logged as it starts (``fake.visit_log``); a ``field`` step -- or the back door, or H18's
        door -- ends the beat, and nothing after it runs."""
        for i, step in enumerate(steps, base):
            if self.done:
                return
            kind = next(kd for kd in VISIT_STEP_KEYS if kd in step)
            at = f"{path}{i}"
            self._log(fake, at, kind)
            if kind == "store":
                self._store(fake, step["store"])
            elif kind == "wait":
                yield from self._ticks(round(float(step["wait"]) * float(self.k["wait_scale"])))
            elif kind == "place":
                self._place(fake, step["place"])
            elif kind == "grant":
                self._grant(fake, step["grant"])
            elif kind == "page":
                yield from self._page(fake, step)
            elif kind == "timed":
                self._timed(fake, step)
            elif kind == "pair":
                yield from self._pair(fake, step)
            elif kind == "choice":
                yield from self._choice(fake, step, at)
            elif kind == "stairs":
                yield from self._stairs(fake, step["stairs"], at)
            elif kind == "naming":
                yield from self._naming(fake, step)
            elif kind == "door":
                yield from self._door(fake, step["door"], at)
            elif kind == "wait_window":
                yield from self._wait_window(int(step["wait_window"]))
            else:
                self._field(fake, str(step["field"]))

    def _store(self, fake, args) -> None:
        """A script store (:meth:`FakeGame.script_store`): ``value`` "answer" is the last choice's answer; H15's
        ``store_override`` replaces the value stored at an ip."""
        sid, tag, ip, byte, width, value, bit = args
        if value == "answer":
            value = self.answer
        value = self.k["store_override"].get(int(ip), value)
        fake.script_store(int(sid), int(tag), int(ip), int(byte), str(width), int(value), bit=int(bit))

    def _place(self, fake, xz) -> None:
        """A scripted move: the player published where it puts him (no coast carries a press on from there). H20
        (research/o7_design.md 3.1): ``[x, z, h]`` -- ``h`` the PSX y operand of the bytes' MoveInstantXZY -- places his
        height too (:meth:`FakeGame.place_height`); ``[x, z]`` leaves it as it was."""
        fake.player[0], fake.player[2] = float(xz[0]), float(xz[1])
        if len(xz) == 3:
            fake.place_height(float(xz[0]), float(xz[1]), float(xz[2]))
        fake._coast = None

    def _grant(self, fake, xz) -> None:
        """EnableMove (153 e3 t1 ip785, after WaitWindow(1) ip752 and Map.Bit[158] := 1 ip755): control, him at (x, z)."""
        self._place(fake, xz)
        fake.control = True

    def _open_mes(self, fake, step: dict, kind: str):
        """The window of a page / timed step as the agent publishes it -- ``text`` (default ``mes N``) and its ``raw``
        (default ``[STRT=0,0]`` + the text) -- with the type-out state :meth:`typing` reads; its mes (the step's) is
        what H17's ``unparsed_frames`` keys."""
        text = str(step.get("text", f"mes {step[kind]}"))
        w = self.open(fake, int(step.get("slot", 0)), kind, text, str(step.get("raw", f"[STRT=0,0]{text}")),
                      mes=step[kind])
        w.typing_s, w.typed, w.done_frame, w.done_rt = float(step.get("typing_s") or 0.0), False, None, None
        return w

    def _page(self, fake, step: dict):
        w = self._open_mes(fake, step, "page")
        if step.get("async"):                        # H24: WindowAsync -- listed this tick, the script goes on at once
            return
        while not w.gone:
            yield

    def _wait_window(self, slot: int):
        """H24 (the O7 review's finding): WaitWindow(``slot``) -- the script holds until no window of that slot is
        listed (159 e16 t1 ip534, ip558, ip577, ip669 after its WindowAsync pages), the tick it is gone; none up: it goes
        on at once."""
        while any(w.slot == slot and not w.gone for w in self.windows):
            yield

    def _timed(self, fake, step: dict) -> None:
        """A [TIME=t] [NFOC] window (153's 137, 140): Confirm-inert -- kind "timed": the UI takes Confirm on a page and
        a choice alone -- closing itself ``ticks`` after it opened (:meth:`on_tick`); the script goes on at once."""
        w = self._open_mes(fake, step, "timed")
        w.close_tick = self.tick + int(step["ticks"])

    def _pair(self, fake, step: dict):
        """H10's KEYON pair (153's 134/135 and 139/138, 154's three, 153@316's two): a, then b ``lag`` ticks later, both
        [INCS][TIME=-1] (kind "keyon": no UI Confirm pages them); from ``gate`` ticks after b each tick reads ``keyon &
        (Confirm | Special)`` -- an edge before the gate is consumed by its tick and lost -- and the first such EDGE
        closes both (the KEYON check, e.g. 153 e3 t1 ip2336); the script resumes once both are gone. Each window's mes
        is what H17's ``unparsed_frames`` keys."""
        (ma, sa), (mb, sb) = step["pair"]
        texts = list(step.get("texts") or (f"mes {ma}", f"mes {mb}"))
        raws = list(step.get("raws") or [f"[STRT=0,0]{t}[INCS][TIME=-1]" for t in texts])
        a = self.open(fake, int(sa), "keyon", texts[0], raws[0], mes=ma)
        yield from self._ticks(int(step.get("lag", 15)))
        b = self.open(fake, int(sb), "keyon", texts[1], raws[1], mes=mb)
        yield from self._ticks(int(step.get("gate", 40)))
        while not self.keyon & KEYON_PAIR_BITS:
            yield
        self.close(fake, a)
        self.close(fake, b)
        while not (a.gone and b.gone):
            yield

    def _choice(self, fake, step: dict, at: str):
        """A WindowSync choice ``gap`` ticks after the previous window is GONE -- the script resumed the tick it went:
        e31's WaitAnimation rest, e2's stage tick and e3's open (research/o5_design.md 0.2 #14); H15's ``gap_ticks``
        overrides it -- its text the header and its lines, ``selected`` its ``stale`` cursor until it is complete
        (:meth:`ui`, :meth:`publish`). The script resumes the tick it is gone, its answer kept for a store's "answer";
        then ``branch[str(answer)]``'s steps. H15's ``reask``: once gone, the same choice is asked again, ``gap`` ticks
        later, before the branch."""
        k = self.k
        gap = int(k["gap_ticks"] if k["gap_ticks"] is not None else step.get("gap", 2))
        header, lines = str(step.get("header", "")), [str(x) for x in step["lines"]]
        text = "\n".join([header, *lines])
        for _ask in range(2 if k["reask"] else 1):
            yield from self._ticks(gap)
            w = self.open(fake, int(step.get("slot", 0)), "choice", text, str(step.get("raw", f"[STRT=0,0]{text}")))
            w.typing_s, w.typed, w.done_frame, w.done_rt = float(step.get("typing_s") or 0.0), False, None, None
            w.header, w.lines, w.stale = header, lines, int(step.get("stale", 0))
            w.cursor = w.stale
            while not w.gone:
                yield
            self.answer = w.answer
        yield from self._run(fake, (step.get("branch") or {}).get(str(self.answer), ()), f"{at}.{self.answer}.")

    @staticmethod
    def _contour(s: dict, x: float, z: float) -> bool:
        """THE HEIGHT TEST (153 e3 t1 ip859, ``obj(uid=255).f[1] > -450`` failing): his height on the real mesh at or
        below ``level`` (PSX y: up is negative), or -- floor-blind -- his centre inside ``contour``."""
        if s["height_at"] is not None:
            h = s["height_at"](x, z)
            return h is not None and h <= float(s["level"])
        return _in_poly(x, z, s["contour"])

    @staticmethod
    def _height(fake, s: dict) -> None:
        """With ``height_at``: the published y is minus his height there (f[1] is -pos[1], EBin.cs:1785-1793)."""
        if s["height_at"] is not None:
            h = s["height_at"](fake.player[0], fake.player[2])
            if h is not None:
                fake.player[1] = -float(h)

    def _stairs(self, fake, knobs: dict, at: str):
        """153 e3 t1 STAGE 6 and its neighbours (research/o5_design.md 3.2), per field tick while he has control: (1)
        the regions' tag 2 tests in entry order -- each side scene (e26: its quad AND z > ``z_gt``; e27: its quad), live
        in stage 6 alone: the first hit takes control (DisableMove ip88 / ip68), lists its pages (rule 7's), places him
        at ``regrant_at`` (Walk(1105,-78) ip1230) and grants control again (ip1266): stage 6 again; then the back door
        (e28, its quad, live whenever he has control): control off, its stores (e28 t2 ip38, ip227), and ``exit_ticks``
        later its Field() -- the beat ends there; (2) THE HEIGHT TEST (:meth:`_contour`): the first tick it holds takes
        control (ip874-915), ``teleport_ticks`` later CreateObject puts him at ``teleport`` (ip1466) and stage 17 walks
        him along ``climb`` at ``climb_speed`` u a tick; then the next step. H15: ``no_contour`` -- the test never fires;
        ``side_scene_at`` -- at the n-th MOVING tick of a stage-6 period (a tick he stands somewhere new: the walk's, not
        the settle's before it) a side scene fires wherever he stands. ``fake.visit_log`` rows: "scene", "back_door",
        "lost" (each with his x, z)."""
        from ff9mapkit.content import doorface
        s = {**STAIRS_DEFAULTS, **knobs}
        fires, period, moving = self.k["side_scene_at"], 0, 0
        last = (fake.player[0], fake.player[2])
        while True:
            x, z = fake.player[0], fake.player[2]
            self._height(fake, s)
            if fake.control:
                if (x, z) != last:
                    moving += 1
                last = (x, z)
                scene = next((sc for sc in s["scenes"] if doorface.region_contains(x, z, sc["points"])
                              and z > float(sc.get("z_gt", float("-inf")))), None)
                if scene is None and period < len(fires) and moving == fires[period] and s["scenes"]:
                    scene = s["scenes"][0]
                if scene is not None:
                    fake.control, fake._coast = False, None
                    self._log(fake, f"{at}.s", "scene", x=x, z=z)
                    yield from self._run(fake, scene.get("pages") or (), f"{at}.s.")
                    self._grant(fake, s["regrant_at"])
                    period, moving, last = period + 1, 0, (fake.player[0], fake.player[2])
                    yield
                    continue
                bd = s["back_door"]
                if bd is not None and doorface.region_contains(x, z, bd["points"]):
                    fake.control, fake._coast = False, None
                    self._log(fake, f"{at}.d", "back_door", x=x, z=z)
                    for args in bd.get("stores") or ():
                        self._store(fake, args)
                    yield from self._ticks(int(bd.get("exit_ticks", 0)))
                    self._field(fake, str(bd["to"]))
                    return
                if not self.k["no_contour"] and self._contour(s, x, z):
                    fake.control, fake._coast = False, None
                    self._log(fake, f"{at}.l", "lost", x=x, z=z)
                    yield from self._ticks(int(s["teleport_ticks"]))
                    self._place(fake, s["teleport"])
                    self._height(fake, s)
                    speed = float(s["climb_speed"])
                    for tx, tz in s["climb"]:
                        tx, tz = float(tx), float(tz)
                        while (fake.player[0], fake.player[2]) != (tx, tz):
                            yield
                            px, pz = fake.player[0], fake.player[2]
                            d = math.hypot(tx - px, tz - pz)
                            if d <= speed:
                                fake.player[0], fake.player[2] = tx, tz
                            else:
                                fake.player[0], fake.player[2] = px + (tx - px) / d * speed, pz + (tz - pz) / d * speed
                            self._height(fake, s)
                    yield
                    return
            yield

    def _naming(self, fake, step: dict):
        """H17 (research/o6_design.md 3.3): Menu(1, char) -- EventService.StartMenu opens NameSettingUI over the field
        (DoEventCode.cs:2317-2341): ui "NameSetting", no window listed, the box focused on the pre-filled default
        (CharacterDefaultName, NameSettingUI.cs:137-151; the step's ``name``). The script stands still while it is up --
        :meth:`_Machine.frame` runs a tick's script only on FieldHUD ("a menu up holds the field"), the engine's Menu
        blocking the event code -- and :meth:`ui` takes the screen's keys (:meth:`_naming_keys`); the script resumes the
        tick the screen closes."""
        fake.ui_state = "NameSetting"
        self.naming = {"char": int(step["naming"]), "name": step.get("name"), "focus": True,
                       "deaf": int(self.k["naming_deaf"])}
        yield
        self.naming = None

    def _naming_keys(self, fake, downs: set) -> None:
        """H17: NameSettingUI's keys (NameSettingUI.cs:72-83, :107, :173), as the scene beat's naming rule reads them: a
        Confirm going down while the box is focused takes the focus off it; the next is OK -- the name saved
        (``name_typed``, else the pre-filled default) into ``fake.named`` / ``fake.names``, the field HUD back (the
        script resumes in this frame's tick); a Cancel puts the focus back on the box. ``naming_deaf``: the screen drops
        its first k Confirms."""
        n = self.naming
        if "confirm" in downs:
            if n["deaf"] > 0:
                n["deaf"] -= 1                                          # H17: dropped
            elif n["focus"]:
                n["focus"] = False
            else:
                typed = self.k["name_typed"]
                name = typed if typed is not None else n["name"]
                fake.named.append(n["char"])
                if name is not None:
                    fake.names[n["char"]] = name
                fake.ui_state = "FieldHUD"
                self.naming = None
        elif "cancel" in downs:
            n["focus"] = True

    def _door(self, fake, knobs: dict, at: str):
        """H18 (research/o6_design.md 3.4): THE REGIONS' TAG 2, every field tick he has control, in ENTRY order (the
        engine runs region objects by entry: e23, e24, e25) -- each door's polygon (doorface.region_contains: IsInQuad)
        and, with ``z_gt``, his z past it (153 e23 t2 ip38's f[2] > 1333; its f[1] > -100 ground half is the
        floor-blind fake's ground). The first hit FIRES: control off (ExitField ip59) and a visit_log row "fire" (the
        door's name, where he stood); then ``ticks`` ticks (e23: 25 -- ip153's op_22(25); ip95's op_22(1) is skipped) of
        ExitField's WALK-OUT -- with ``walkout``, toward its ``to`` at ``speed`` u a tick (MOVJ at his last controlled
        frame's speed, DoEventCode.cs:860-869, EventEngine.MoveToward.cs:15-30), held at ``to`` or where his z passes
        ``stop_z`` (pathing's hold a radius short of the floor's end: 0.2 #6); without it he stands -- then, the exit
        gate set or absent (``fake.exit_gate``, H16: he stands meanwhile), the door's ``stores`` and its Field() in the
        same tick (ip203, then ip211). H19's ``door_misroute`` sends that Field() to another ``field_to`` key, and
        ``land_real`` applies to it (:meth:`_field`).

        H22 (research/o7_design.md 3.3): a door's HEIGHT terms -- ``y_gt`` / ``y_le``, his published y past it / at or
        under it (154 e8 t2 ip38's ``f[1] < -100``: one polygon, two doors in entry order, the balcony's and the
        ground's) -- beside ``z_gt``; and the step's SCENES, tested after the doors each tick he has control (159's
        regions e10-e12 precede Steiner's e16, and the engine runs objects by entry): an ARMED scene -- its ``unless_bit``
        clear in the modelled gEventGlobal -- whose ``any_of`` holds (any one: ip390's B_OROR) FIRES: control off (ip445
        DisableMove), a visit_log row "scene" (its name, where he stood), its steps -- pages, stores, waits -- then
        control back where he stands (``regrant`` "in_place": ip711 EnableMove, no Walk), and the doors' loop goes on. A
        scene whose own steps store its ``unless_bit`` (ip672) cannot fire again."""
        from ff9mapkit.content import doorface
        s = {**DOOR_DEFAULTS, **knobs}
        while True:
            if fake.control:
                x, z, y = fake.player[0], fake.player[2], fake.player[1]
                door = next((d for d in s["doors"] if doorface.region_contains(x, z, d["points"])
                             and (d.get("z_gt") is None or z > float(d["z_gt"]))
                             and (d.get("y_gt") is None or y > float(d["y_gt"]))
                             and (d.get("y_le") is None or y <= float(d["y_le"]))), None)
                if door is not None:
                    break
                scene = next((sc for sc in s["scenes"] if self._scene_fires(fake, sc, x, z)), None)
                if scene is not None:                            # H22: an object's scene takes control here
                    fake.control, fake._coast = False, None
                    self._log(fake, f"{at}.s", "scene", name=scene["name"], x=x, z=z)
                    yield from self._run(fake, scene["steps"], f"{at}.s.")
                    if self.done:
                        return
                    fake.control, fake._coast = True, None      # ip711 EnableMove: where he stands, no Walk
                    yield
                    continue
            yield
        fake.control, fake._coast = False, None
        self._log(fake, f"{at}.{door['name']}", "fire", name=door["name"], x=x, z=z)
        wo = door.get("walkout")
        walk = None
        if wo is not None:
            tx, tz = (float(v) for v in wo["to"])
            stop = None if wo.get("stop_z") is None else float(wo["stop_z"])
            way = 1.0 if tz >= z else -1.0
            walk = {"to": (tx, tz), "stop_z": stop, "way": way, "done": stop is not None and (z - stop) * way >= 0}
        for _ in range(int(door["ticks"])):
            yield
            if walk is not None:
                self._walk_out(fake, walk, float(s["speed"]))
        while not fake._exit_open():
            yield
        for args in door["stores"]:
            self._store(fake, args)
        self._field(fake, self.k["door_misroute"].get(str(door["name"]), str(door["to"])))

    @staticmethod
    def _scene_fires(fake, sc: dict, x: float, z: float) -> bool:
        """H22 (research/o7_design.md 3.3): whether a door step's scene fires with him standing at (x, z) -- ARMED (no
        ``unless_bit``, or that gEventGlobal bit clear in the modelled array: ip390's ``Bit[3796] == 0``) and ANY of its
        ``any_of`` tests holding (ip390's B_OROR: x < -1600 || x > 1600 || z < 800)."""
        bit = sc.get("unless_bit")
        if bit is not None and (fake.story_bytes[bit >> 3] >> (bit & 7)) & 1:
            return False
        tests = {"x_lt": lambda v: x < v, "x_gt": lambda v: x > v, "z_lt": lambda v: z < v, "z_gt": lambda v: z > v}
        return any(tests[key](float(v)) for key, v in sc["any_of"].items())

    @staticmethod
    def _walk_out(fake, w: dict, step: float) -> None:
        """H18's walk-out, one field tick: ``step`` u toward ``to``, held there or where his z passes ``stop_z``."""
        if w["done"]:
            return
        x, z = fake.player[0], fake.player[2]
        tx, tz = w["to"]
        d = math.hypot(tx - x, tz - z)
        nx, nz = (tx, tz) if d <= step else (x + (tx - x) / d * step, z + (tz - z) / d * step)
        w["done"] = d <= step
        stop = w["stop_z"]
        if stop is not None and (nz - stop) * w["way"] >= 0:
            t = (stop - z) / (nz - z) if nz != z else 1.0
            nx, nz, w["done"] = x + (nx - x) * t, stop, True
        fake.player[0], fake.player[2] = nx, nz

    def _field(self, fake, to: str) -> None:
        """Field() (153 e3 t1 ip3158, 154 e2 t1 ip1528, 153 e18 t1 ip1085; e28's ip235): the field becomes ``field_to[to]``
        -- H15's ``land_real``: the REAL id -- a fresh visit with control off (the engine zeroes it at a field's start)
        and no window; the beat finishes, and the scene's next beat starts in the new field."""
        fid = self.k["land_real"].get(to, self.k["field_to"][to])
        self.windows = []
        fake.field_id = int(fid)
        fake.player = [0.0, 0.0, 0.0]
        fake.control, fake._coast = False, None
        fake._visit += 1
        fake._in_trigger.clear()
        self.finish(fake)


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
