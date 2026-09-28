#!/usr/bin/env python3
"""The game's clock as the driver has to plan by it: render frames, 30 Hz field ticks, MovePC calls -- pure, no
Session import.

WHY THIS EXISTS. The driver used to hold movement as units PER RENDER FRAME (15 walking, 30 running), measured once
on a machine rendering at 60 fps. The engine does not move him per frame. Field logic runs on WALL-CLOCK TICKS:
``FPSManager.AdvanceUpdateCounter`` (FPSManager.cs:77-111 at stock 6b8bb2d5) turns each frame's ``Time.deltaTime``
into a whole number of ticks against a ``1 / FieldTPS`` grid, and ``HonoBehaviorSystem.Update`` runs every actor that
many times (HonoBehaviorSystem.cs:106). Each tick a walking player makes ONE MovePC call and a running one TWO
(FieldMapActorController.cs:198-209: "Running movement for the PC (60/tick) is done by moving twice at the walking
speed (30/tick)"), and each call steps 30 units (``content.doorface.STEP_PER_CALL``) and turns him 40% of the way to
the pad (:756). So a frame is only a sampling window: at 60 fps it holds half a tick, at 31 fps about one, at 120 a
quarter -- and the harness has measured all three regimes on this machine (31 and 60 for whole launches, ~105 once).
Every frame-denominated speed was right only at 60.

THE MODEL, IN THREE KINDS OF NUMBER. A caller that plans a press asks a :class:`Rate` for exactly one of:

* the AVERAGE -- :meth:`Rate.speed`, :meth:`Rate.frames_for`: for SIZING a press, where being wrong costs one more
  iteration of a closed loop and nothing else;
* an UPPER bound -- :meth:`Rate.reach`, :meth:`Rate.ticks_most`: for any rule that must not be broken (a zone he
  must not enter, a body he must not touch) -- how far he CAN have gone;
* a LOWER bound -- :meth:`Rate.ticks_sure`, :meth:`Rate.calls_sure`, :meth:`Rate.frames_for_ticks`: for anything
  that must be SURE (the calls that turned him, the calls that opened a push lock) -- in WHOLE ticks, so a running
  press counts its calls in pairs.

Time budgets are asked in seconds (:meth:`Rate.frames_at_least` for a wait that must last, :meth:`Rate.frames_at_most`
for a cap that must not). The bounds come from the measured rate's spread, not from the engine's quantisation
alone: an N-frame hold spends ``floor`` or ``ceil`` of ``N * tick_hz / fps`` ticks depending on a phase nobody
publishes, and the fps itself is only known to within that spread.

WHERE THE RATE COMES FROM. :class:`TickClock` watches every state the driver reads (Session feeds it from the same
observer hook the state ring rides -- no extra poll, no thread) and pairs consecutive published frames with their
WRITE time: a published tick counter ``ticks`` when the agent has one, a published realtime clock ``rt`` (the fake
game; a future engine), else the state file's mtime (today's engine: sub-millisecond, and within 1-2% over a 2 s
window -- measured over 79 archived launches). A field load, a fade, an arrival's first second, a scripted stretch
with neither control nor a dialog, and a stall of more than half a second are not a rate and are never paired
(:class:`TickClock` says why each). Until it has seen :data:`MIN_PAIRS` steady pairs the clock answers the
calibrated 60 fps (``source == "default"``), which only SIZING may lean on -- a site whose error cannot be undone
must wait for ``ready``.

WHAT THIS DOES NOT KNOW. FastForwardFactor (the F1 speed-mode cheat, FPSManager.cs:83/95/97) is unpublished by
today's engine, and ``[Graphics] FieldTPS`` is read from the ini, not observed -- only a published ``ticks`` counter
measures the tick rate itself. A driver that sees movement outrun :meth:`Rate.reach` should say so loudly, naming
those two and the Run/Walk option (``cfg.move``, FieldMapActorController.cs:198: it inverts what Cancel does, so a
press held as a walk runs), never guess. (Dash-inhibit -- :197, a run hold walks on a field that forbids running --
only ever SHORTENS a run; the agent publishes it, ``input.dash_inh``, and the driver reads it as the gait.) Nor does
a Rate know a HITCH inside a press: one long frame is caught up in that frame's ticks (FPSManager.cs:94-99), up to
about ten, which no render rate foresees -- :meth:`TickClock.excess_ticks` says afterwards what one added.
"""
from __future__ import annotations

import collections
import dataclasses
import math
import statistics
from dataclasses import dataclass

# ff9mapkit is on sys.path whenever this package is imported: harness/__init__ imports session first, and
# session.py puts it there (as the fake game relies on too). IMPORTED, not restated: one literal per law.
from ff9mapkit.content.doorface import STEP_PER_CALL

#: MovePC calls a field tick makes, by gait: walking one, running two, each stepping STEP_PER_CALL (30u) --
#: FieldMapActorController.cs:198-209 at stock 6b8bb2d5. So a tick moves him 30u walking and 60u running on flat
#: ground (PSXMovementMethod scales a step by cos(slope), :740-741), whatever the render rate.
CALLS_PER_TICK = {"walk": 1, "run": 2}

#: Ticks a press can still move him after its frames, as :meth:`Rate.reach` counts them. Not a coast the engine
#: runs (MovePC reads the key on every call and nothing buffers it): the published position lags its own frame's
#: ticks (the agent's Update ran before HonoBehaviorSystem's in the one frame measured), and a tick's worth of
#: movement can land after the press's last published frame. One tick is the bound the harness has measured (its old
#: two-frame tail, PROBE_TAIL_FRAMES, read 1-1.5 ticks at 60 fps), and it also carries the one-tick slack the frame
#: jitter of a real render loop needs on top of the rate's spread (test_tickrate: +-5% frame jitter never exceeds it).
#: NOT a HITCH: one frame of 120 ms at 60 fps catches up four ticks in that frame (FPSManager.cs:94-99), and the
#: archived rings' in-control windows hold such a frame about one in twenty-five -- every window that outran
#: ticks_most + this held one, and none that did not (the review's 268,095-window census). A press with a hitch in
#: it can outrun :meth:`Rate.reach`; :meth:`TickClock.excess_ticks` measures by how much, afterwards.
TAIL_TICKS = 1

#: The render rate a Rate answers before any is measured: the rate the harness's old per-frame constants were
#: calibrated at (bench 30801). Only SIZING may lean on it -- ``Rate.ready`` is False while it is the answer.
DEFAULT_FPS = 60.0

#: ``[Graphics] FieldTPS`` when the ini does not say: the engine's own default (GraphicsSection.cs:39 at stock
#: 6b8bb2d5), which a DISABLED section resets every value to (IniReader.cs:285-286; the section's own default is
#: disabled, GraphicsSection.cs:33).
DEFAULT_FIELD_TPS = 30.0

#: The window the rate is estimated over, in the clock's own seconds: the newest pairs this far back. The data
#: report's steady-stretch error for a 2 s window of mtime pairs: p50 0.1% / p90 0.4% at 60 fps, 0.2% / 2.3% at 31.
WINDOW_SECONDS = 2.0

#: Steady pairs the first estimate needs, and the length of a run of pairs that declares a REGIME SWITCH (below).
#: Eight 2-frame pairs is a quarter second at 60 fps, half a second at 31.
MIN_PAIRS = 8

#: A pair is two consecutive PUBLISHED frames at most this many frames apart (the agent publishes every 2nd frame;
#: a driver that polls slower than it publishes skips some) ...
PAIR_MAX_FRAMES = 8

#: ... and at most this many seconds apart: a longer gap is a stall or a load, whose few frames say nothing about
#: the steady rate (a field load costs 0.6-2.1 s below 25 fps, single frames up to 288 ms -- the run data's loads).
PAIR_MAX_SECONDS = 0.5

#: ... and not in the first this-many seconds of a field VISIT -- from its first frame with control (or a dialog) and
#: nothing fading; a fade starts a new visit too, so a same-id reload is one. A load does not end when the fade does:
#: the frames right after an arrival, with control already back and nothing fading, still run at 14-48 fps on this
#: machine (story-rung2's arrival on 552, 60 fps regime), and a sparse driver can hold nothing else in a window. The
#: rate carries across fields, so this costs nothing but the first estimate's wait.
ARRIVAL_SECONDS = 1.0

#: How far the p25 / p75 of the pair rates are widened when the time is the state file's mtime: the write lands at a
#: varying point inside its frame, and the driver reads the body THEN stats the file, so a rewrite in between stamps
#: an older frame with a newer time. 2% is the data report's p90 error of 1-2 s mtime windows at 31 fps. A published
#: clock (``rt`` / ``ticks``) is written in the document itself and is not widened.
MTIME_WIDEN = 0.02

#: A move of the rate by more than this fraction is a CHANGE: :meth:`TickClock.changed` reports it, and a run of
#: MIN_PAIRS pairs all this far off the window's median (the same way) restarts the window at the run -- so a regime
#: switch (60 -> 31, seen once mid-launch) is the estimate's MEDIAN within MIN_PAIRS pairs, not after half the
#: window. Its SPREAD keeps the pre-switch band too for WINDOW_SECONDS after (:meth:`TickClock._switch`): eight pairs
#: are half a second at 31 fps, and a DIP that long is not a regime -- great-margulis' platform ring dropped to 31
#: for frames 912-926 of a 60 fps launch, on one field with control, then came straight back; fitted to the dip alone
#: the spread said 33 fps for a third of a second of 60, and a press judged SURE of three ticks ran two.
CHANGE_FRACTION = 0.15

#: An UNOBSERVED STRETCH: two consecutive samples at least this many seconds apart on their clock -- the driver read
#: nothing in between (a sleep, a stalled process, a game that published nothing). The estimate from before one is
#: STALE (``Rate.stale``, never ``ready``) until MIN_PAIRS fresh pairs measure the rate again: the one mid-launch
#: switch the archive holds (s1c, 60 -> 31) happened in a 221 s stretch nobody read. A fade, a load, a battle and a
#: scripted scene the driver READ are not one: their frames are seen, never paired, and the rate -- the monitor's,
#: not the room's -- carries across them (an arrival's slow second cannot tell a switch from a load: see
#: ARRIVAL_SECONDS; a switch there is the estimate once the visit's first MIN_PAIRS pairs are in).
STALE_GAP_SECONDS = WINDOW_SECONDS

#: How many distinct published frames the clock keeps -- far more than a window holds (2 s at 144 fps publishing
#: every frame is 288), so the window, not this, is what bounds an estimate.
MAX_SAMPLES = 1024

#: Where a Rate's numbers came from: none measured yet, the state file's mtime, a published realtime clock, or a
#: published tick counter (whose tick rate is then MEASURED, fast-forward and timescale included).
SOURCES = ("default", "mtime", "rt", "ticks")

#: Slack on a floor / ceil of a count, RELATIVE to it (never under this much absolute), so float noise in a rate that
#: is exactly 60 or 30 cannot turn N/2 into N/2 + 1: a published clock ticking 1/60 s a frame, and an epoch-scale mtime
#: whose last bit is ~2.4e-7 s -- a few parts in a million of a 2-frame interval, so a median of 29.99997 fps at a
#: true 30 floored 600u of run to 9 frames one read and 10 the next (the smooth-hold [mtime] test's reversal). A count
#: within this fraction of a whole one IS that whole one: 1e-5 of a tick is a microsecond.
_EPS = 1e-5


def _floor(x: float) -> int:
    """``floor(x)``, a count within _EPS of the next whole one taken as it (float noise, not a fraction of a tick)."""
    return int(math.floor(x + _EPS * max(1.0, abs(x))))


def _ceil(x: float) -> int:
    """``ceil(x)``, a count within _EPS of the whole one below taken as it."""
    return int(math.ceil(x - _EPS * max(1.0, abs(x))))


def _gait_calls(gait: str) -> int:
    """CALLS_PER_TICK of ``gait`` -- ``"walk"`` or ``"run"``, nothing else (a typo is refused, never read as walk)."""
    try:
        return CALLS_PER_TICK[gait]
    except KeyError:
        raise ValueError(f"gait must be one of {sorted(CALLS_PER_TICK)}, not {gait!r}") from None


def _frames(frames) -> int:
    """A frame count as the int it must be: never negative (a press cannot last minus two frames)."""
    n = int(frames)
    if n < 0:
        raise ValueError(f"a frame count cannot be negative ({frames!r})")
    return n


@dataclass(frozen=True)
class Rate:
    """One estimate of the render rate and the field tick rate, and every conversion between frames, ticks, MovePC
    calls, units and seconds that a press is planned by (see the module docstring for which kind a caller wants).

    ``fps`` is the median render rate, ``fps_lo`` / ``fps_hi`` the spread it is known within (p25 / p75 of the pair
    rates, widened :data:`MTIME_WIDEN` on mtime): an upper bound on ticks divides by ``fps_lo``, a lower bound by
    ``fps_hi``. ``tick_hz`` is field ticks per second -- ``[Graphics] FieldTPS`` x the published timescale, or
    MEASURED when ``source`` is ``"ticks"``. ``samples`` is the pairs the estimate used, ``frame`` the newest frame
    in it (-1 for the default). ``stale``: measured, but before an UNOBSERVED STRETCH (:data:`STALE_GAP_SECONDS`) --
    sizing may still use it, nothing that must be judged may (``ready`` is False). Frozen, and checked at
    construction: a Rate whose spread does not contain its own median, or whose rates are not positive, is refused
    rather than planned by."""

    fps: float
    fps_lo: float
    fps_hi: float
    tick_hz: float = DEFAULT_FIELD_TPS
    source: str = "default"
    samples: int = 0
    frame: int = -1
    stale: bool = False

    def __post_init__(self):
        for name in ("fps", "fps_lo", "fps_hi", "tick_hz"):
            v = getattr(self, name)
            if not (isinstance(v, (int, float)) and math.isfinite(v) and v > 0):
                raise ValueError(f"Rate.{name} must be a positive finite number, not {v!r}")
        if not self.fps_lo <= self.fps <= self.fps_hi:
            raise ValueError(f"Rate spread [{self.fps_lo}, {self.fps_hi}] does not contain its fps {self.fps}")
        if self.source not in SOURCES:
            raise ValueError(f"Rate.source must be one of {SOURCES}, not {self.source!r}")

    @classmethod
    def default(cls, tick_hz: float = DEFAULT_FIELD_TPS) -> "Rate":
        """The calibrated 60 fps, spread-free -- what a clock answers before it has measured anything."""
        return cls(DEFAULT_FPS, DEFAULT_FPS, DEFAULT_FPS, float(tick_hz))

    @property
    def ready(self) -> bool:
        """Whether this is a MEASURED rate that still holds: False for the default and for a ``stale`` estimate, which
        sizing may use and nothing else."""
        return self.source != "default" and not self.stale

    # -- the average: SIZING only ----------------------------------------------------------------------------------
    def per_frame(self) -> float:
        """Field ticks one frame holds on average: ``tick_hz / fps`` (0.5 at 60 fps, about 0.96 at 31.2)."""
        return self.tick_hz / self.fps

    def speed(self, gait: str) -> float:
        """Units one frame of a held ``gait`` moves him ON AVERAGE: ``calls a tick x 30 x per_frame`` (walk 15 / run
        30 at 60 fps; 28.8 / 57.7 at 31.2). For SIZING a press only -- a rule judges :meth:`reach`."""
        return _gait_calls(gait) * STEP_PER_CALL * self.per_frame()

    def frames_for(self, units: float, gait: str) -> int:
        """The frames to hold ``gait`` to cover about ``units``: ``floor(units / speed)``, at least one. Sizing: the
        closed loop measures what it actually covered."""
        return max(1, _floor(float(units) / self.speed(gait)))

    # -- the upper bound: RULES -------------------------------------------------------------------------------------
    def ticks_most(self, frames: int) -> int:
        """The most field ticks ``frames`` frames can hold: ``ceil(frames * tick_hz / fps_lo)`` -- unless a HITCH
        falls in them (TAIL_TICKS: a long frame catches its ticks up, :meth:`TickClock.excess_ticks`)."""
        return max(0, _ceil(_frames(frames) * self.tick_hz / self.fps_lo))

    def reach(self, frames: int, gait: str) -> float:
        """The farthest a ``frames``-frame hold of ``gait`` can carry him, tail included: ``calls a tick x 30 x
        (ticks_most + TAIL_TICKS)``. At 60 fps with an even ``frames`` this is the old ``(frames + 2) x speed``; an
        odd one holds a tick more in one phase than the old model credited. On flat ground, and without a HITCH in
        the press (see TAIL_TICKS): a rule judged at it holds through every jitter of a steady render loop, not
        through a frame that stalls 120 ms -- which no rate measured before the press can foresee."""
        return _gait_calls(gait) * STEP_PER_CALL * (self.ticks_most(frames) + TAIL_TICKS)

    # -- the lower bound: anything that must be SURE ----------------------------------------------------------------
    def ticks_sure(self, frames: int) -> int:
        """The field ticks ``frames`` frames are sure to hold: ``floor(frames * tick_hz / fps_hi)``."""
        return max(0, _floor(_frames(frames) * self.tick_hz / self.fps_hi))

    def calls_sure(self, frames: int, gait: str) -> int:
        """The MovePC calls a ``frames``-frame hold of ``gait`` is sure to make: calls a tick x :meth:`ticks_sure` --
        WHOLE ticks, so a running press counts its calls in PAIRS (3 frames at 60 fps are sure of one tick: 2 run
        calls, never 3). The one owner of that law (content.doorface's planner helpers count calls, never frames)."""
        return _gait_calls(gait) * self.ticks_sure(frames)

    def frames_for_ticks(self, ticks: int) -> int:
        """The fewest frames sure to hold ``ticks`` ticks: the least N with ``ticks_sure(N) >= ticks`` (2 frames a
        tick at 60 fps; 0 for no ticks)."""
        ticks = int(ticks)
        if ticks <= 0:
            return 0
        n = max(1, _ceil(ticks * self.fps_hi / self.tick_hz))
        while self.ticks_sure(n) < ticks:
            n += 1
        while n > 1 and self.ticks_sure(n - 1) >= ticks:
            n -= 1
        return n

    def frames_for_calls(self, calls: float, gait: str) -> int:
        """The fewest frames of ``gait`` sure to make ``calls`` MovePC calls: :meth:`frames_for_ticks` of the whole
        ticks those calls need -- ``ceil(calls / calls a tick)``, a run's in PAIRS (27 run calls are 14 ticks: 28
        frames at 60 fps, 14 at 30; 4 walked calls are 4 ticks, 8 frames at 60)."""
        return self.frames_for_ticks(_ceil(float(calls) / _gait_calls(gait)))

    # -- time budgets -----------------------------------------------------------------------------------------------
    def frames_at_least(self, seconds: float) -> int:
        """Frames of a wait that is sure to last at least ``seconds``: ``ceil(seconds * fps_hi)``."""
        return max(0, _ceil(float(seconds) * self.fps_hi))

    def frames_at_most(self, seconds: float) -> int:
        """Frames of a cap that is sure to last no more than ``seconds``: ``floor(seconds * fps_lo)``."""
        return max(0, _floor(float(seconds) * self.fps_lo))

    # -- the record -------------------------------------------------------------------------------------------------
    def as_dict(self) -> dict:
        """The estimate as a record carries it (a press's ``record["fps"]``, env.json, a rate-change line)."""
        return {"fps": round(self.fps, 3), "fps_lo": round(self.fps_lo, 3), "fps_hi": round(self.fps_hi, 3),
                "tick_hz": round(self.tick_hz, 3), "per_frame": round(self.per_frame(), 4), "source": self.source,
                "samples": self.samples, "frame": self.frame, "stale": self.stale}

    def describe(self) -> str:
        """One line for a log: ``31.2 fps (30.5-31.9, mtime, 24 pairs to frame 5334), 0.962 ticks a frame at 30 Hz``
        -- ``not measured`` for the default, ``STALE`` for an estimate from before an unobserved stretch."""
        if self.source == "default":
            where = "not measured"
        else:
            where = f"{self.source}, {self.samples} pairs to frame {self.frame}" + (", STALE" if self.stale else "")
        return (f"{self.fps:.1f} fps ({self.fps_lo:.1f}-{self.fps_hi:.1f}, {where}), "
                f"{self.per_frame():.3f} ticks a frame at {self.tick_hz:g} Hz")


#: Unity's cap on one frame's ``Time.deltaTime`` (``Time.maximumDeltaTime``, 1/3 s by default; Memoria never sets it
#: -- no hit in the source). Unity runtime behaviour, NOT verified in source: a stall longer than this is dropped, not
#: caught up, so one frame runs at most about ten field ticks.
MAX_DELTA_TIME = 1.0 / 3.0


class TickAccumulator:
    """``FPSManager.AdvanceUpdateCounter`` (FPSManager.cs:77-111 at stock 6b8bb2d5), ported: the WHOLE field ticks a
    frame of ``dt`` seconds runs. Each frame ``next -= deltaTime`` (:94), then ``while (2 * ff * next < T) { next +=
    T / ff; count++ }`` (:95-99) with ``T = 1 / tps`` (:67-68) -- scaled game time crossing a ``1 / (tps * ff)`` grid,
    rounded at the half tick, so ``next`` stays in [T/2, 3T/2) and a frame runs 0, 1 or several ticks. The FIRST frame
    takes the reset branch (:79-88): one tick, and the target re-armed at ``T / ff`` -- what the engine does on any
    frame after one nobody read the counter on. ``dt`` is capped at :data:`MAX_DELTA_TIME` first, as Unity caps
    ``Time.deltaTime``. The fake game's "quantized" ticks, and the tests' oracle for the Rate's bounds."""

    def __init__(self, tps: float = DEFAULT_FIELD_TPS, fast_forward: float = 1.0):
        self.tps, self.fast_forward = float(tps), float(fast_forward)
        self._next: float | None = None

    def advance(self, dt: float) -> int:
        """The ticks the next frame, ``dt`` seconds long, runs."""
        target, ff = 1.0 / self.tps, self.fast_forward
        if self._next is None:
            self._next = target / ff
            return 1
        self._next -= min(float(dt), MAX_DELTA_TIME)
        count = 0
        while 2.0 * ff * self._next < target:
            self._next += target / ff
            count += 1
        return count


def field_tps_from_ini(doc: dict | None) -> float:
    """``[Graphics] FieldTPS`` as the ENGINE would take it from a :func:`harness.artifacts.read_memoria_ini` document
    (LAST wins, as the engine's parser): the field's ticks a second, :data:`DEFAULT_FIELD_TPS` when the ini is
    missing, the key absent or unparseable (IniValue.TryParseInt32, IniValue.cs:113 -- invariant integer), the value
    not positive, or the section not enabled -- ``Enabled`` must read exactly ``1`` (TryParseBoolean, :123), and a
    section that is not resets every value to its default (IniReader.cs:285-286). SceneDirector.cs:34 sets it as the
    field's main-loop speed."""
    graphics = (doc or {}).get("Graphics") or {}
    if str(graphics.get("Enabled", "")).strip() != "1":
        return DEFAULT_FIELD_TPS
    try:
        tps = int(str(graphics.get("FieldTPS", "")).strip())
    except ValueError:
        return DEFAULT_FIELD_TPS
    return float(tps) if tps > 0 else DEFAULT_FIELD_TPS


def read_field_tps(game_path) -> float:
    """:func:`field_tps_from_ini` of ``<game_path>/Memoria.ini`` -- the default when it cannot be read."""
    from pathlib import Path
    from .artifacts import read_memoria_ini
    return field_tps_from_ini(read_memoria_ini(Path(game_path) / "Memoria.ini"))


def _num(v) -> float | None:
    """A published number, or None for anything else (a bool is not a number here: JSON true is not a clock)."""
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


class _Sample:
    """One distinct published frame: its number, whether it can be paired (on a field, steady), and its clocks."""

    __slots__ = ("frame", "field", "steady", "rt", "ticks", "mtime", "timescale")

    def __init__(self, frame, field, steady, rt, ticks, mtime, timescale):
        self.frame, self.field, self.steady = frame, field, steady
        self.rt, self.ticks, self.mtime, self.timescale = rt, ticks, mtime, timescale


class _Pair:
    """Two consecutive samples as a rate: ``fps`` frames over seconds on ``clock`` (``"rt"`` / ``"mtime"``), and --
    for the ``"ticks"`` source -- the ticks it ran."""

    __slots__ = ("source", "clock", "start", "end", "t_end", "fps", "dticks", "dt")

    def __init__(self, source, clock, start, end, t_end, fps, dticks, dt):
        self.source, self.clock, self.start, self.end = source, clock, start, end
        self.t_end, self.fps, self.dticks, self.dt = t_end, fps, dticks, dt


class TickClock:
    """The render rate, measured from the states the driver reads anyway -- see the module docstring.

    Feed it EVERY state read (:meth:`observe`; Session wires it to the channel's observer). A frame read twice is one
    sample: the second read only ever corrects the first's mtime DOWN, because the read/stat race can only stamp a
    frame with a LATER write's time, never an earlier one. A pair is two consecutive samples, both STEADY -- on a
    field (``ui_state`` FieldHUD, a field id), not fading, with control or a dialog up (story-rung1's 368 ms frames came
    in a scripted stretch with neither), and past the visit's first :data:`ARRIVAL_SECONDS` -- on the SAME field, at
    most :data:`PAIR_MAX_FRAMES` frames and :data:`PAIR_MAX_SECONDS` apart, on one clock: so no field load, fade, menu,
    battle, scripted stall or arrival's slow second is ever a rate. The estimate (:meth:`rate`) is the median of the
    pair rates over the last :data:`WINDOW_SECONDS` of the newest pair's clock, with p25 / p75 as its spread; it needs
    :data:`MIN_PAIRS` pairs, keeps the last estimate while a window has fewer (a quiet driver, a battle, a long
    dialog-less cutscene), and answers :meth:`Rate.default` until the first. The rate carries across fields -- it is
    the monitor's, not the room's (the archived launches held one regime on every field) -- so only the first
    estimate of a launch waits on an arrival.

    A CARRIED ESTIMATE IS CHECKED, never trusted blind. Kept while the window holds fewer than MIN_PAIRS pairs, its
    spread takes in the median of the fresh pairs it has when that median lies outside it -- so a rate that moved
    turns a reach conservative (and a sure count lower) at the first pairs that say so, not at the eighth. And an
    estimate from before an UNOBSERVED STRETCH (:data:`STALE_GAP_SECONDS` with no read) is ``stale``: never
    ``ready`` until MIN_PAIRS fresh pairs measure the rate again -- nothing that must be judged is judged by a rate
    last seen before a gap in which it could have halved (the s1c switch), however few fresh pairs have come in.

    A REGIME SWITCH restarts the window: a run of at least MIN_PAIRS newest pairs that all lie more than
    :data:`CHANGE_FRACTION` off the median of the pairs before them, the same way, is a new rate, and the pairs before
    the run are dropped for good -- the estimate's MEDIAN follows the switch within MIN_PAIRS pairs instead of after
    half the window. Its SPREAD keeps the band the pairs before the run had, for WINDOW_SECONDS after the run began:
    a dip of eight pairs and straight back (the platform ring's half second at 31 in a 60 fps launch) must not leave
    a spread fitted to the dip -- the bound must hold whichever way the game goes next. The rate is never carried
    across launches: a frame number that goes BACK (``Time.frameCount`` never does within one process) resets the
    clock, and a caller that relaunches calls :meth:`reset`."""

    def __init__(self, field_tps: float = DEFAULT_FIELD_TPS):
        tps = float(field_tps)
        if not (math.isfinite(tps) and tps > 0):
            raise ValueError(f"field_tps must be a positive number of ticks a second, not {field_tps!r}")
        #: ``[Graphics] FieldTPS`` -- :func:`field_tps_from_ini`; the tick rate unless a counter is published.
        self.field_tps = tps
        self._samples: collections.deque = collections.deque(maxlen=MAX_SAMPLES)
        self._last: Rate | None = None           # the newest measured estimate
        self._reported: Rate | None = None       # the estimate changed() last reported
        self._since = -1                         # a regime switch's first frame: pairs starting before it are gone
        self._held: tuple | None = None          # (fps_lo, fps_hi, t) the band before a switch whose run began at t
        self._stale_from = -1                    # the first frame after the newest unobserved stretch
        self._arrival: tuple | None = None       # (field id, rt, mtime) of the current visit's first steady frame

    def reset(self) -> None:
        """Forget everything: a new launch's rate is measured afresh, and its first estimate is reported again."""
        self._samples.clear()
        self._last = self._reported = None
        self._since = -1
        self._held = None
        self._stale_from = -1
        self._arrival = None

    # -- intake -----------------------------------------------------------------------------------------------------
    def observe(self, st) -> None:
        """Take one state read (a :class:`harness.channel.State`). O(1): it rides every read the driver makes."""
        f = st.frame
        if f < 0:
            return
        mtime = _num(st.mtime)
        if self._samples:
            last = self._samples[-1]
            if f == last.frame:
                if mtime is not None and (last.mtime is None or mtime < last.mtime):
                    last.mtime = mtime       # the race only makes a write look LATER: the earliest read is the truth
                return
            if f < last.frame:
                self.reset()                 # the frame counter went back: another process, another rate
        raw = st.raw
        rt = _num(raw.get("rt"))
        if self._samples:
            last = self._samples[-1]
            gap = (rt - last.rt if rt is not None and last.rt is not None
                   else mtime - last.mtime if mtime is not None and last.mtime is not None else None)
            if gap is not None and gap >= STALE_GAP_SECONDS:
                self._stale_from = f         # nothing was read for that long: what came before is stale
        if self._arrival is None or self._arrival[0] != st.field_id or st.fading:
            self._arrival = (st.field_id, None, None)         # a new visit (or a fade: a same-id reload is one too)
        eligible = (st.field_id > 0 and st.ui_state == "FieldHUD" and not st.fading
                    and (st.control or st.dialog_open))
        _fld, rt0, mt0 = self._arrival
        if eligible and rt0 is None and mt0 is None:
            self._arrival = (st.field_id, rt, mtime)          # the visit's first steady frame: the quarantine's start
            rt0, mt0 = rt, mtime
        settled = ((rt is not None and rt0 is not None and rt - rt0 >= ARRIVAL_SECONDS)
                   or (mtime is not None and mt0 is not None and mtime - mt0 >= ARRIVAL_SECONDS))
        self._samples.append(_Sample(f, st.field_id, eligible and settled, rt, _num(raw.get("ticks")), mtime,
                                     _num(raw.get("timescale"))))

    # -- the estimate -----------------------------------------------------------------------------------------------
    def rate(self) -> Rate:
        """The newest estimate: measured from the current window when it holds MIN_PAIRS pairs, else the last one
        measured -- its spread widened to the fresh pairs' median where that lies outside it (:meth:`_checked`) --
        else :meth:`Rate.default` at the ini's tick rate (``ready`` False). ``stale`` (never ``ready``) when its newest
        pair came before an unobserved stretch (:data:`STALE_GAP_SECONDS`)."""
        est = self._estimate()
        if est is not None:
            self._last = est
        last = self._last
        if last is None:
            return Rate.default(self.field_tps * self._timescale())
        if est is None:
            last = self._checked(last)
        if last.frame < self._stale_from:
            return dataclasses.replace(last, stale=True)
        return last

    def _checked(self, last: Rate) -> Rate:
        """``last`` -- an estimate CARRIED because the window holds fewer than MIN_PAIRS pairs -- with its spread
        taking in the median of the window's pairs newer than it, widened as an estimate's own is, where that median
        lies outside it: a reach judged by it is conservative and a sure count lower at the first fresh pairs that say
        the rate moved, never only once MIN_PAIRS of them have. Unchanged when none are newer or they agree."""
        fresh = [p for p in self._window() if p.start >= last.frame]
        if not fresh:
            return last
        m = statistics.median(p.fps for p in fresh)
        if last.fps_lo <= m <= last.fps_hi:
            return last
        widen = MTIME_WIDEN if fresh[-1].clock == "mtime" else 0.0
        return dataclasses.replace(last, fps_lo=min(last.fps_lo, m / (1.0 + widen)),
                                   fps_hi=max(last.fps_hi, m * (1.0 + widen)))

    def changed(self) -> tuple[Rate, Rate] | None:
        """``(before, now)`` when the rate moved since the last report -- the first measured estimate (``before``
        the default), then any move of the fps or of the ticks a frame by more than :data:`CHANGE_FRACTION` -- else
        None. Each report is consumed: the next compares with ``now``. For the run's log / env.json, so a mid-run
        switch is on the record."""
        now = self.rate()
        if not now.ready:
            return None
        before = self._reported
        if before is None:
            self._reported = now
            return Rate.default(now.tick_hz), now
        moved = max(abs(now.fps / before.fps - 1.0), abs(now.per_frame() / before.per_frame() - 1.0))
        if moved > CHANGE_FRACTION:
            self._reported = now
            return before, now
        return None

    def _timescale(self) -> float:
        """The newest published ``timescale`` (Time.timeScale: it scales deltaTime, so the ticks a second too), 1
        when none is."""
        for s in reversed(self._samples):
            if s.timescale is not None and s.timescale > 0:
                return s.timescale
        return 1.0

    @staticmethod
    def _pair(a: _Sample, b: _Sample) -> _Pair | None:
        """``a`` then ``b`` as a rate, or None when they are not a steady pair (see the class docstring)."""
        if not (a.steady and b.steady and a.field == b.field):
            return None
        df = b.frame - a.frame
        if not 0 < df <= PAIR_MAX_FRAMES:
            return None
        if a.rt is not None and b.rt is not None:
            clock, ta, tb = "rt", a.rt, b.rt
        elif a.mtime is not None and b.mtime is not None:
            clock, ta, tb = "mtime", a.mtime, b.mtime
        else:
            return None
        dt = tb - ta
        if not 0.0 < dt <= PAIR_MAX_SECONDS:
            return None
        dticks = None
        if a.ticks is not None and b.ticks is not None:
            dticks = b.ticks - a.ticks
            if dticks < 0:
                return None                  # the counter restarted between them: not a rate
        return _Pair("ticks" if dticks is not None else clock, clock, a.frame, b.frame, tb, df / dt, dticks, dt)

    def _window(self) -> list[_Pair]:
        """The pairs of the current window, oldest first: the newest steady pair's source and clock, back
        WINDOW_SECONDS of that clock, none starting before a detected regime switch."""
        samples = self._samples
        out: list[_Pair] = []
        key = t_newest = None
        for i in range(len(samples) - 1, 0, -1):
            if samples[i].frame <= self._since:
                break
            p = self._pair(samples[i - 1], samples[i])
            if p is None or p.start < self._since:
                continue
            if key is None:
                key, t_newest = (p.source, p.clock), p.t_end
            elif (p.source, p.clock) != key:
                continue
            if p.t_end < t_newest - WINDOW_SECONDS:
                break
            out.append(p)
        out.reverse()
        return out

    def _switch(self, pairs: list[_Pair]) -> list[_Pair]:
        """``pairs`` restarted at a regime switch when its newest MIN_PAIRS pairs all lie more than CHANGE_FRACTION
        off the median of the pairs before them, the same way -- the run extended back over every earlier pair that is
        just as far off -- else unchanged. The switch is remembered (``_since``) so the old pairs stay dropped, and so
        is the BAND the pairs before the run had (``_held``, joined to one still held from an earlier switch), which
        the estimate's spread keeps for WINDOW_SECONDS from the run's start (:meth:`_estimate`)."""
        if len(pairs) < 2 * MIN_PAIRS:
            return pairs
        ref = statistics.median(p.fps for p in pairs[:-MIN_PAIRS])
        hi, lo = ref * (1.0 + CHANGE_FRACTION), ref / (1.0 + CHANGE_FRACTION)
        tail = pairs[-MIN_PAIRS:]
        if all(p.fps > hi for p in tail):
            off = lambda p: p.fps > hi          # noqa: E731 - the side the run is on
        elif all(p.fps < lo for p in tail):
            off = lambda p: p.fps < lo          # noqa: E731
        else:
            return pairs
        k = len(pairs) - MIN_PAIRS
        while k > 0 and off(pairs[k - 1]):
            k -= 1
        band_lo, band_hi = self._band(pairs[:k])
        t0 = pairs[k].t_end - pairs[k].dt
        if self._held is not None and t0 - self._held[2] < WINDOW_SECONDS:
            band_lo, band_hi = min(band_lo, self._held[0]), max(band_hi, self._held[1])
        self._held = (band_lo, band_hi, t0)
        self._since = pairs[k].start
        return pairs[k:]

    @staticmethod
    def _band(pairs: list[_Pair]) -> tuple[float, float]:
        """The spread ``pairs`` give an estimate: their p25 / p75 (the one pair's rate for fewer than two), widened
        MTIME_WIDEN when their clock is the mtime -- the same spread :meth:`_estimate` takes."""
        rates = [p.fps for p in pairs]
        if len(rates) >= 2:
            q1, _q2, q3 = statistics.quantiles(rates, n=4, method="inclusive")
        else:
            q1 = q3 = rates[0]
        widen = MTIME_WIDEN if pairs[-1].clock == "mtime" else 0.0
        return q1 / (1.0 + widen), q3 * (1.0 + widen)

    def _estimate(self) -> Rate | None:
        """A Rate from the current window, or None when it holds fewer than MIN_PAIRS pairs (or its tick counter ran
        no ticks: a paused game is not a rate). Within WINDOW_SECONDS of a regime switch its spread also holds the
        band from before it (``_held``): the median has moved, the bounds have not yet learnt which way it stays."""
        pairs = self._switch(self._window())
        if len(pairs) < MIN_PAIRS:
            return None
        rates = [p.fps for p in pairs]
        fps = statistics.median(rates)
        q1, q3 = self._band(pairs)
        if self._held is not None:
            if pairs[-1].t_end - self._held[2] < WINDOW_SECONDS:
                q1, q3 = min(q1, self._held[0]), max(q3, self._held[1])
            else:
                self._held = None                    # the new rate has held a whole window: its own band stands
        if pairs[-1].source == "ticks":
            ticks, secs = sum(p.dticks for p in pairs), sum(p.dt for p in pairs)
            if ticks <= 0:
                return None
            tick_hz = ticks / secs
        else:
            tick_hz = self.field_tps * self._timescale()
        return Rate(fps=fps, fps_lo=min(fps, q1), fps_hi=max(fps, q3),
                    tick_hz=tick_hz, source=pairs[-1].source, samples=len(pairs), frame=pairs[-1].end)

    # -- after the fact ---------------------------------------------------------------------------------------------
    def excess_ticks(self, f0: int, f1: int, rate: Rate) -> float:
        """How many field ticks MORE than ``rate`` can account for the frames ``f0`` .. ``f1`` may have run -- the
        seconds the clock saw pass between those two published frames (both must have been read; their shared clock,
        rt or mtime) beyond ``(f1 - f0) / fps_lo``, in ticks: a HITCH in them (one frame of 120 ms at 60 fps is four
        ticks caught up in that frame, FPSManager.cs:94-99) -- 0 when they ran as the rate says, or when either frame
        was not read. The span's ENDS only, so the mtime's write jitter is paid twice, never once a pair: a hitch
        anywhere between them, however the reads fell, shows as the time it took."""
        a = b = None
        for s in self._samples:
            if s.frame == f0:
                a = s
            elif s.frame == f1:
                b = s
        if a is None or b is None or f1 <= f0:
            return 0.0
        if a.rt is not None and b.rt is not None:
            took = b.rt - a.rt
        elif a.mtime is not None and b.mtime is not None:
            took = b.mtime - a.mtime
        else:
            return 0.0
        return max(0.0, (took - (f1 - f0) / rate.fps_lo) * rate.tick_hz)
