"""``tools/harness/tickrate.py`` -- the driver's model of the game's clock -- and the fake game's tick model.

WHAT THESE PIN. The engine moves the player per 30 Hz FIELD TICK, not per render frame (FPSManager.cs:77-111,
HonoBehaviorSystem.cs:106, FieldMapActorController.cs:198-209 at stock 6b8bb2d5), and this machine has rendered at ~31,
~60 and once ~105 fps under the harness. So a press is planned from a MEASURED rate: an average for sizing, an upper
bound for any rule, a lower bound -- in whole ticks -- for anything that must be sure. The pure half checks those bounds
against a port of the engine's own tick accumulator, and the estimator (TickClock) against the shapes the archived
rings showed: a 31 fps regime, field loads, the read/stat race, a mid-run switch. The fake half checks that the stand-in
turns frames into ticks the same way -- and, at its defaults (60 fps, mean ticks), exactly as it moved before.

The bound tests assert the OLD model's failure (15u / 30u a frame, a tick every two frames) beside the new model's
pass, so they cannot pass vacuously; every rule of the estimator and the fake was broken once, on a scratch copy, and
its test here watched go red -- except the same-field and not-fading tests of a pair, which the arrival rule makes
redundant (a field change and a fade each start a visit whose first second is never paired).
"""

import itertools
import json
import math
import pathlib
import random
import sys
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

from harness import Channel, State                                   # noqa: E402
from harness import tickrate as T                                    # noqa: E402
from harness.artifacts import read_memoria_ini                       # noqa: E402
from harness.fakegame import FakeGame                                # noqa: E402


# --------------------------------------------------------------------------- the engine, as the tests' oracle
def _engine_ticks(dts, tps=30.0, ff=1.0):
    """FPSManager.AdvanceUpdateCounter at stock 6b8bb2d5, transcribed here on its own (not through TickAccumulator):
    the first frame is the reset branch (:79-88, one tick, target T/ff); then each frame ``next -= deltaTime`` and
    ``while (2*ff*next < T) { next += T/ff; count++ }`` (:94-99), deltaTime capped at a third of a second."""
    target, nxt, out = 1.0 / tps, None, []
    for dt in dts:
        if nxt is None:
            nxt = target / ff
            out.append(1)
            continue
        nxt -= min(dt, 1.0 / 3.0)
        count = 0
        while 2 * ff * nxt < target:
            nxt += target / ff
            count += 1
        out.append(count)
    return out


def _window_counts(ticks, n, start=60):
    """The tick count of every ``n``-frame window of ``ticks`` from ``start`` on (a hold of n frames, at every phase)."""
    cum = [0, *itertools.accumulate(ticks)]
    return [cum[i + n] - cum[i] for i in range(start, len(ticks) - n)]


# --------------------------------------------------------------------------- a published ring, synthesised
def _st(frame, *, rt=None, mtime=None, field=350, control=True, dialog=False, fading=False, ui="FieldHUD",
        ticks=None, timescale=None):
    raw = {"frame": frame, "field": {"id": field}, "ui_state": ui, "fading": fading,
           "player": {"control": control}, "dialog": {"open": dialog}}
    if rt is not None:
        raw["rt"] = rt
    if ticks is not None:
        raw["ticks"] = ticks
    if timescale is not None:
        raw["timescale"] = timescale
    at = rt if mtime is None else mtime
    return State(raw, read_at=(at or 0.0) + 0.002, mtime=mtime)


def _publish_times(dts, every=2, t0=1000.0):
    """``(frame, time)`` of every ``every``-th frame of a run whose frames last ``dts`` seconds -- what the agent
    publishes (every 2nd frame by default)."""
    out, t = [], t0
    for f, dt in enumerate(dts, start=1):
        t += dt
        if f % every == 0:
            out.append((f, t))
    return out


def _clock_of(dts, *, kind="mtime", every=2, write_noise=0.0, seed=3, **st):
    """A TickClock fed the published ring of frame times ``dts`` on ``kind``'s clock (``"rt"`` in the document, or
    the state file's ``"mtime"``, with up to ``write_noise`` seconds of lateness per write)."""
    rnd = random.Random(seed)
    clock = T.TickClock()
    for f, t in _publish_times(dts, every):
        w = t + (rnd.uniform(0.0, write_noise) if write_noise else 0.0)
        clock.observe(_st(f, rt=t if kind == "rt" else None, mtime=w if kind == "mtime" else None, **st))
    return clock


FPS_SET = (28.0, 31.2, 60.0, 120.0, 144.0)


# --------------------------------------------------------------------------- the bounds, against the engine
@pytest.mark.parametrize("kind", ["rt", "mtime"])
@pytest.mark.parametrize("fps", FPS_SET)
def test_ticks_bound_the_engine_accumulator(fps, kind):
    """For a hold of N = 1..27 frames at a steady render rate, the ticks the engine's accumulator actually runs --
    at EVERY phase -- lie in [ticks_sure(N), ticks_most(N)] of the rate the clock measured from the same run's
    published frames. The old model (sure: floor(N/2) ticks; most: N/2 + 1) fails at 120 fps (a 2-frame hold is not
    sure of a tick) and at 31.2 (8 frames run 7-8 ticks, not at most 5)."""
    dts = [1.0 / fps] * 3000
    rate = _clock_of(dts[: int(3 * fps)], kind=kind).rate()
    assert rate.ready and rate.source == kind and rate.fps == pytest.approx(fps, rel=1e-6)
    widen = 0.02 if kind == "mtime" else 0.0                        # the mtime clock's own noise (2%), allowed for
    assert (rate.fps_lo, rate.fps_hi) == pytest.approx((fps / (1 + widen), fps * (1 + widen)), rel=1e-6)
    ticks = _engine_ticks(dts)
    old_sure_fails = old_most_fails = False
    for n in range(1, 28):
        seen = _window_counts(ticks, n)
        assert rate.ticks_sure(n) <= min(seen) and max(seen) <= rate.ticks_most(n), (fps, n, min(seen), max(seen))
        old_sure_fails |= n // 2 > min(seen)
        old_most_fails |= max(seen) > n / 2 + 1
    assert old_sure_fails == (fps > 60.0)
    assert old_most_fails == (fps < 60.0)


@pytest.mark.parametrize("fps", FPS_SET)
def test_ticks_bound_the_engine_accumulator_through_frame_jitter(fps):
    """With every frame +-5% off the mean (uniform) and each write stamped up to 4 ms late (the mtime clock's own
    noise), the sure count still never exceeds what a window ran, and the REACH -- ticks_most plus its tail tick --
    never falls short of it."""
    rnd = random.Random(11)
    dts = [(1.0 / fps) * (1.0 + rnd.uniform(-0.05, 0.05)) for _ in range(4000)]
    rate = _clock_of(dts[: int(3 * fps)], write_noise=0.004).rate()
    assert rate.ready and rate.fps == pytest.approx(fps, rel=0.03)
    ticks = _engine_ticks(dts)
    for n in range(1, 28):
        seen = _window_counts(ticks, n)
        assert rate.ticks_sure(n) <= min(seen), (fps, n, rate)
        assert max(seen) <= rate.ticks_most(n) + T.TAIL_TICKS, (fps, n, rate)
        assert rate.reach(n, "run") >= max(seen) * 2 * 30.0


def test_the_accumulator_is_the_engines():
    """TickAccumulator is FPSManager's loop: it agrees with the independent transcription frame for frame over a
    jittered run with hitches, its first frame is the reset branch's one tick, 60 fps alternates 0 / 1, and one long
    frame is caught up in that frame's ticks -- 50 ms 1-2, 157 ms 4-5 -- but never past a third of a second."""
    rnd = random.Random(5)
    dts = [(1.0 / 31.2) * (1 + rnd.uniform(-0.1, 0.1)) for _ in range(500)]
    dts[100] += 0.157
    dts[300] += 1.2
    acc = T.TickAccumulator()
    assert [acc.advance(dt) for dt in dts] == _engine_ticks(dts)
    acc = T.TickAccumulator()
    sixty = [acc.advance(1.0 / 60.0) for _ in range(40)]
    assert sixty[0] == 1 and set(sixty[1:]) == {0, 1} and sum(sixty[1:]) == 19
    for long_ms, want in ((50, {1, 2}), (157, {4, 5})):
        seen = set()
        for warm in range(1, 12):
            acc = T.TickAccumulator()
            for _ in range(warm):
                acc.advance(1.0 / 31.5)
            seen.add(acc.advance(long_ms / 1000.0))
        assert seen <= want and seen, (long_ms, seen)
    acc = T.TickAccumulator()
    acc.advance(1.0 / 60.0)
    assert acc.advance(5.0) <= 11                                   # a 5 s stall is dropped, not caught up
    fast = T.TickAccumulator(fast_forward=3.0)
    assert sum(fast.advance(1.0 / 60.0) for _ in range(601)) == pytest.approx(900, abs=2)   # F1 speed mode: 90 a second


def test_running_calls_come_in_pairs():
    """A running tick is TWO MovePC calls, so the calls a press is sure of are whole ticks' worth: 3 frames at 60 fps
    are sure of one tick -- 2 run calls, never the 3 that floor(3 frames x 1 call a frame) credited -- and 1 walk call.
    Whatever the rate, a sure run count is even."""
    r = T.Rate.default()
    assert r.ticks_sure(3) == 1 and r.calls_sure(3, "run") == 2 and r.calls_sure(3, "walk") == 1
    assert r.calls_sure(4, "run") == 4 and r.calls_sure(8, "run") == 8
    m = T.Rate(31.2, 30.6, 31.8, source="mtime", samples=20, frame=500)
    assert all(m.calls_sure(n, "run") % 2 == 0 for n in range(40))
    assert m.calls_sure(3, "run") == 2 * math.floor(3 * 30 / 31.8)
    with pytest.raises(ValueError, match="gait"):
        r.calls_sure(3, "sprint")


def test_reach_at_60_is_the_old_reach_for_even_frames():
    """THE 60 FPS GUARD. At the calibrated 60 fps -- the default, and the fake's exact published clock -- an even hold's
    reach is the old ``(frames + 2) x speed`` and its sure ticks the old ``frames / 2``, walking and running."""
    measured = _clock_of([1.0 / 60.0] * 240, kind="rt").rate()
    assert measured.ready and (measured.fps_lo, measured.fps_hi) == pytest.approx((60.0, 60.0), rel=1e-9)
    for r in (T.Rate.default(), measured):
        for n in range(0, 42, 2):
            assert r.reach(n, "run") == (n + 2) * 30.0 and r.reach(n, "walk") == (n + 2) * 15.0
            assert r.ticks_sure(n) == n // 2 == r.ticks_most(n)
        assert r.speed("run") == pytest.approx(30.0) and r.speed("walk") == pytest.approx(15.0)
        assert r.frames_for_ticks(1) == 2 and r.frames_for_ticks(4) == 8 and r.frames_for_ticks(14) == 28


# --------------------------------------------------------------------------- the estimator, against the ring shapes
def test_a_31_fps_ring_gives_about_one_tick_a_frame():
    """The ~31 fps regime (rung3b, the facing runs: 2-frame write intervals spread 56-71 ms around 64): a frame holds
    about 0.96 ticks, so a run frame covers ~58u, not 30 -- and 8 run frames can reach 540u, where the old model
    judged 300."""
    rnd = random.Random(2)
    dts = [(1.0 / 31.2) * (1 + rnd.uniform(-0.06, 0.06)) for _ in range(200)]
    rate = _clock_of(dts, write_noise=0.004).rate()
    assert rate.ready and rate.source == "mtime" and rate.samples >= T.MIN_PAIRS
    assert rate.fps == pytest.approx(31.2, rel=0.02)
    assert rate.per_frame() == pytest.approx(0.96, abs=0.03)
    assert rate.speed("run") == pytest.approx(57.7, rel=0.03)
    assert rate.fps_lo < rate.fps < rate.fps_hi and rate.fps_hi / rate.fps_lo < 1.2
    assert rate.reach(8, "run") >= 540.0 > (8 + 2) * 30.0


def test_a_field_load_in_the_window_is_not_a_rate():
    """A warp at 60 fps: a fade at 10 fps, a 0.3 s gap across the field change, and -- with control back and nothing
    fading -- the new field's first second at 20 fps, before it settles to 60. None of it is a rate: the fade by its
    flag, the change by its field id, the arrival by ARRIVAL_SECONDS. At every read the estimate stays the steady 60,
    its spread above 55; without the arrival rule the 20 fps frames would have pulled it under."""
    clock, f, t = T.TickClock(), 0, 1000.0
    ests = []

    def run(n, fps, **st):
        nonlocal f, t
        for _ in range(n):
            f, t = f + 2, t + 2.0 / fps
            clock.observe(_st(f, mtime=t, **st))
            ests.append(clock.rate())

    run(150, 60.0, field=350)                                       # 5 s steady on 350
    run(3, 10.0, field=350, fading=True, control=False)             # the fade out
    t += 0.3
    run(3, 10.0, field=351, fading=True, control=False)             # the new field, still fading in
    run(10, 20.0, field=351)                                        # arrived: control back, slow frames
    run(90, 60.0, field=351)                                        # settled
    ready = [r for r in ests if r.ready]
    assert len(ready) > 150
    assert all(r.fps == pytest.approx(60.0, rel=0.01) and r.fps_lo > 55.0 for r in ready), \
        min(ready, key=lambda r: r.fps_lo)

    unguarded = T.TickClock()                                       # the arrival frames, paired: not steady
    for i in range(12):
        unguarded.observe(_st(2 * i, mtime=1000.0 + i * 0.1))
    assert not unguarded.rate().ready                               # the first second of a visit is no rate


def test_a_scripted_stall_without_control_or_dialog_is_not_a_rate():
    """story-rung1's field 552: with control gone and no dialog up (a scripted event), 4 frames took 368 ms and 6 took
    434 -- a stall, not the render rate. Only frames with control, or with a dialog up, are paired."""
    clock, f, t = T.TickClock(), 0, 1000.0
    for i in range(120):                                            # 4 s of 60 fps with control
        f, t = f + 2, t + 2 / 60.0
        clock.observe(_st(f, mtime=t))
    before = clock.rate()
    for _ in range(6):                                              # the scripted stall: ~11 fps, no control
        f, t = f + 4, t + 0.368
        clock.observe(_st(f, mtime=t, control=False))
    for _ in range(15):                                             # a slow scripted stretch: 20 fps, no control
        f, t = f + 2, t + 0.1
        clock.observe(_st(f, mtime=t, control=False))
    assert clock.rate() == before                                   # none of it a pair: the estimate stands
    for _ in range(30):                                             # a dialog: the same 60 fps, paired
        f, t = f + 2, t + 2 / 60.0
        clock.observe(_st(f, mtime=t, control=False, dialog=True))
    after = clock.rate()
    assert before.ready and after.fps == pytest.approx(60.0, rel=0.01) and after.fps_lo > 55.0
    assert after.frame == f                                         # the dialog's frames were the estimate's


def test_the_read_stat_race_does_not_move_the_median():
    """The driver reads the body THEN stats the file: a rewrite between the two stamps frame g with frame g+2's write
    time. It only ever makes a write look LATER -- so a frame read again keeps its EARLIEST mtime: with one publish in
    three raced and every one of them read again, the estimate is the clean ring's exactly (uncorrected, a third of
    the pairs would read half the rate and the spread would open to it). A raced read left standing costs one slow
    pair and one dropped one, which the median rides out: one in six, never re-read, within 1% of the truth."""
    dts = [1.0 / 31.2] * 400
    clean = _clock_of(dts).rate()
    assert clean.fps == pytest.approx(31.2, rel=1e-6)
    pubs = _publish_times(dts)

    def raced_ring(every, reread):
        clock = T.TickClock()
        for i, (f, t) in enumerate(pubs):
            raced = i % every == 1 and i + 1 < len(pubs)
            clock.observe(_st(f, mtime=pubs[i + 1][1] if raced else t))
            if raced and reread:
                clock.observe(_st(f, mtime=t))                      # the same frame, read again: its true write
        return clock.rate()

    corrected = raced_ring(3, reread=True)
    assert (corrected.fps, corrected.fps_lo, corrected.fps_hi) == pytest.approx(
        (clean.fps, clean.fps_lo, clean.fps_hi), rel=1e-9)
    standing = raced_ring(6, reread=False)
    assert standing.ready and standing.fps == pytest.approx(clean.fps, rel=0.01)
    assert standing.ticks_sure(8) <= clean.ticks_sure(8) and standing.ticks_most(8) >= clean.ticks_most(8)


def test_a_rate_is_default_until_eight_steady_pairs():
    """Until MIN_PAIRS steady pairs, the answer is the calibrated 60 fps, ``ready`` False -- what only sizing may lean
    on -- and changed() reports nothing; the eighth pair makes it a measurement, reported once, as a change from the
    default."""
    clock = T.TickClock()
    assert clock.rate() == T.Rate.default() and not clock.rate().ready and clock.changed() is None
    f, t = 0, 0.0
    clock.observe(_st(f, rt=t))
    while t < T.ARRIVAL_SECONDS - 1e-9:                             # the visit's first second: frames, no pairs
        f, t = f + 2, t + 2 / 31.2
        clock.observe(_st(f, rt=t))
    for pairs in range(1, T.MIN_PAIRS + 1):
        f, t = f + 2, t + 2 / 31.2
        clock.observe(_st(f, rt=t))
        rate = clock.rate()
        if pairs < T.MIN_PAIRS:
            assert not rate.ready and rate.fps == 60.0 and clock.changed() is None, pairs
    assert rate.ready and rate.source == "rt" and rate.samples == T.MIN_PAIRS and rate.fps == pytest.approx(31.2)
    before, now = clock.changed()
    assert not before.ready and now == rate and clock.changed() is None


@pytest.mark.parametrize("old,new", [(60.0, 31.2), (31.2, 60.0)])
def test_a_regime_switch_is_reported_within_a_second(old, new):
    """s1c dropped from 60 to 31 mid-launch. A run of MIN_PAIRS pairs all more than CHANGE_FRACTION off the window's
    median is a new rate: the window restarts there, so within a second of the switch the estimate IS the new rate
    and changed() has said so -- not after half the 2 s window, as a plain median would (1.3 s for 60 -> 31)."""
    rnd = random.Random(4)
    clock, f, t = T.TickClock(), 0, 1000.0
    for _ in range(int(3 * old / 2)):                               # 3 s at the old rate
        f, t = f + 2, t + 2 / old
        clock.observe(_st(f, mtime=t + rnd.uniform(0, 0.002)))
    assert clock.changed()[1].fps == pytest.approx(old, rel=0.02) and clock.changed() is None
    switched, reported = t, None
    while t < switched + 1.0:
        f, t = f + 2, t + 2 / new
        clock.observe(_st(f, mtime=t + rnd.uniform(0, 0.002)))
        c = clock.changed()
        if c is not None and reported is None:
            reported = t - switched
            assert c[0].fps == pytest.approx(old, rel=0.02) and c[1].fps == pytest.approx(new, rel=0.03), c
    assert reported is not None and reported < 1.0
    assert clock.rate().fps == pytest.approx(new, rel=0.03)


def test_a_steady_ring_with_a_wobbling_write_time_is_never_a_switch():
    """rs-rung0's writes wobble on a 100 ms cycle -- 2-frame intervals of 27.6, 34.2 and 38.3 ms, 60 fps on
    average: pairs from 52 to 73 fps. That is noise, not a regime: after its first report the clock never reports a
    change, and the estimate stays within 3% of 60."""
    clock, f, t = T.TickClock(), 0, 1000.0
    cycle = (0.0276, 0.0342, 0.0382)
    reports = []
    for i in range(900):
        f, t = f + 2, t + cycle[i % 3]
        clock.observe(_st(f, mtime=t))
        c = clock.changed()
        if c:
            reports.append(c)
    assert len(reports) == 1 and reports[0][1].fps == pytest.approx(60.0, rel=0.03)
    assert clock.rate().fps == pytest.approx(60.0, rel=0.03)


def test_a_game_crawling_below_four_fps_is_never_a_rate():
    """Two published frames more than PAIR_MAX_SECONDS apart are a stall, not a rate -- so a game crawling at 3 fps
    for seconds, control and all, never makes one: the answer stays the default, ``ready`` False, and a caller that
    must be sure waits and then raises rather than plan by it."""
    clock = T.TickClock()
    for i in range(40):
        clock.observe(_st(2 * i, mtime=1000.0 + i * 2 / 3.0))
    assert not clock.rate().ready


def test_a_stall_between_two_published_frames_is_not_a_pair():
    """Two published frames more than PAIR_MAX_SECONDS apart, on the same field with control, are a hitch: counted as
    a pair they would be a 3 fps rate. Seven steady pairs and a 0.6 s stall are still not a rate; the eighth steady
    pair is, and the stall is not among its pairs."""
    clock, f, t = T.TickClock(), 0, 1000.0
    clock.observe(_st(f, mtime=t))
    while t < 1000.0 + T.ARRIVAL_SECONDS:                           # the visit's first second: no pairs
        f, t = f + 2, t + 2 / 60.0
        clock.observe(_st(f, mtime=t))
    for _ in range(7):
        f, t = f + 2, t + 2 / 60.0
        clock.observe(_st(f, mtime=t))
    f, t = f + 2, t + 0.6                                           # the stall
    clock.observe(_st(f, mtime=t))
    assert not clock.rate().ready
    f, t = f + 2, t + 2 / 60.0
    clock.observe(_st(f, mtime=t))
    r = clock.rate()
    assert r.ready and r.samples == T.MIN_PAIRS and r.fps == pytest.approx(60.0)


def test_a_published_tick_counter_is_the_tick_rate():
    """A published ``ticks`` counter (the s91 plan; the fake's ``publish=("rt", "ticks")``) makes the tick rate a
    MEASUREMENT: F1 speed mode's 90 ticks a second, invisible to the ini, is 1.5 ticks a frame at 60 fps."""
    clock, ticks = T.TickClock(), 0.0
    for i in range(200):
        clock.observe(_st(2 * i, rt=i * 2 / 60.0, ticks=ticks))
        ticks += 3.0
    r = clock.rate()
    assert r.source == "ticks" and r.fps == pytest.approx(60.0) and r.tick_hz == pytest.approx(90.0)
    assert r.per_frame() == pytest.approx(1.5) and r.speed("run") == pytest.approx(90.0)


def test_the_published_timescale_scales_the_tick_rate():
    """Time.timeScale scales deltaTime, so the ticks a second too: at timescale 0.5 a 60 fps frame holds a quarter
    tick -- from the ini's FieldTPS and the published value, no counter needed."""
    clock = T.TickClock(field_tps=30.0)
    for i in range(200):
        clock.observe(_st(2 * i, rt=i * 2 / 60.0, timescale=0.5))
    assert clock.rate().tick_hz == pytest.approx(15.0) and clock.rate().per_frame() == pytest.approx(0.25)


def test_a_frame_counter_that_goes_back_is_a_new_launch():
    """Time.frameCount never goes back within a process, so a published frame lower than the last is another launch
    -- and a rate is never carried across launches: the clock starts over and reports the new one afresh."""
    clock = _clock_of([1.0 / 60.0] * 300, kind="rt")
    assert clock.rate().fps == pytest.approx(60.0) and clock.changed() is not None
    clock.observe(_st(4, rt=5000.0))
    assert not clock.rate().ready and clock.changed() is None
    for i in range(3, 200):
        clock.observe(_st(2 * i, rt=5000.0 + i * 2 / 31.2))
    assert clock.rate().fps == pytest.approx(31.2) and not clock.changed()[0].ready


def test_a_rate_last_seen_before_an_unobserved_stretch_is_stale():
    """s1c switched from 60 to 31 fps in a 221 s stretch nobody read. A launch measured at 60, then THIRTY SECONDS with no
    read, then the game at 31: the estimate from before the gap is STALE -- never ``ready``, so a press that must be
    judged waits for the rate to be measured again -- and while the fresh pairs are fewer than MIN_PAIRS its spread
    already takes in theirs (a reach at 31, not 60's half of it). The eighth fresh pair is a new estimate, ready, at 31.
    Kept as it was, the old estimate answered 60 fps, ready, and reach(8, "run") = 360u where 31 fps can carry 480."""
    clock, f, t = T.TickClock(), 0, 1000.0
    for _ in range(90):                                             # 3 s at 60, measured
        f, t = f + 2, t + 2 / 60.0
        clock.observe(_st(f, mtime=t))
    before = clock.rate()
    assert before.ready and before.fps == pytest.approx(60.0) and before.reach(8, "run") == 360.0
    t += 30.0                                                       # nobody reads for 30 s; the game drops to 31
    f += 2 * 30 * 31
    clock.observe(_st(f, mtime=t))
    stale = clock.rate()
    assert not stale.ready and stale.fps == pytest.approx(60.0) and stale.stale and "STALE" in stale.describe()
    for fresh in range(1, T.MIN_PAIRS):
        f, t = f + 2, t + 2 / 31.0
        clock.observe(_st(f, mtime=t))
        r = clock.rate()
        assert not r.ready and r.fps_lo <= 31.0 / 1.02 + 1e-9 and r.reach(8, "run") >= 480.0, (fresh, r)
    f, t = f + 2, t + 2 / 31.0
    clock.observe(_st(f, mtime=t))
    now = clock.rate()
    assert now.ready and not now.stale and now.fps == pytest.approx(31.0) and now.samples == T.MIN_PAIRS


def test_fresh_pairs_that_disagree_with_a_carried_estimate_widen_it():
    """A slow field load: 3 s at 60 on 350, a second and a half of fade the driver READ (no unobserved stretch), the new
    field's quarantined first second -- and the game renders at 31 now. The visit's first few pairs are fewer than
    MIN_PAIRS and the 60 fps ones are more than a window behind, so the estimate is the one CARRIED from 350 -- but its
    spread takes in the fresh pairs' median, so a reach is judged at 31 from the first of them, not the eighth."""
    clock, f, t = T.TickClock(), 0, 1000.0

    def run(n, fps, **st):
        nonlocal f, t
        for _ in range(n):
            f, t = f + 2, t + 2.0 / fps
            clock.observe(_st(f, mtime=t, **st))

    run(90, 60.0, field=350)
    run(15, 10.0, field=350, fading=True, control=False)            # the fade and the load, read throughout
    run(16, 31.0, field=351)                                        # arrived: the quarantined second
    carried = clock.rate()
    assert carried.ready and carried.fps == pytest.approx(60.0) and carried.fps_lo > 58.0
    run(3, 31.0, field=351)                                         # three steady pairs at 31
    r = clock.rate()
    assert r.ready and r.fps == pytest.approx(60.0) and r.fps_lo <= 31.0 / 1.02 + 1e-9, r
    assert r.fps_hi >= carried.fps_hi and r.reach(8, "run") >= 480.0 > carried.reach(8, "run")


def test_a_dip_and_back_never_credits_a_press_ticks_it_did_not_run():
    """great-margulis' platform ring: a 60 fps launch that dropped to 31 for half a second, on one field with control,
    and came straight back. Eight pairs off the median are a regime switch -- the MEDIAN follows it -- but a spread
    fitted to the dip alone said 33 fps for the first frames back at 60, and a press judged SURE of three ticks in four
    frames ran two. Held for a window after each switch, the spread keeps the band before it: at every published frame
    the sure count of a press of 2 to 28 frames starting there is at most what the engine's own accumulator runs in
    those frames. (Its REACH is behind until the switch is seen -- MIN_PAIRS pairs: that is the estimator's lag.)"""
    dts = [1 / 60.0] * 180 + [1 / 31.0] * 19 + [1 / 60.0] * 180
    ticks = _engine_ticks(dts)
    cum = [0, *itertools.accumulate(ticks)]
    clock, t = T.TickClock(), 1000.0
    worst = []
    for i, dt in enumerate(dts, start=1):
        t += dt
        if i % 2:
            continue
        clock.observe(_st(i, rt=t))
        r = clock.rate()
        if not r.ready:
            continue
        for n in (2, 4, 8, 14, 28):
            if i + n <= len(dts):
                ran = cum[i + n] - cum[i]                           # frames i+1 .. i+n
                if r.ticks_sure(n) > ran:
                    worst.append((i, n, r.ticks_sure(n), ran, r.describe()))
    assert not worst, worst[:5]
    assert clock.rate().fps == pytest.approx(60.0)


def test_reach_is_judged_at_the_spreads_slow_end():
    """The upper bound divides by ``fps_lo``, never the median: on today's engine (mtime, a spread) that is the one
    extra tick that keeps a zone -- a 60 fps mtime estimate reaches 360u in 8 run frames, where the median said 300."""
    r = T.Rate(31.2, 30.0, 33.0, source="mtime", samples=24, frame=900)
    for n in range(1, 40):
        assert r.ticks_most(n) == math.ceil(n * 30.0 / 30.0 - 1e-6), n
        assert r.reach(n, "run") == 60.0 * (r.ticks_most(n) + T.TAIL_TICKS)
    assert r.ticks_most(26) == 26 > math.ceil(26 * 30.0 / 31.2 - 1e-6)
    m60 = T.Rate(60.0, 60.0 / 1.02, 60.0 * 1.02, source="mtime", samples=30, frame=900)
    assert m60.reach(8, "run") == 360.0


def test_a_field_change_whose_fade_was_not_read_is_still_a_new_visit():
    """The driver's reads missed the fade (a long wait, a blocked send): the first frame it sees is already on the new
    field, control back, its first second slow. The field id alone starts the visit's quarantine -- else its slow pairs
    trip a regime switch and the estimate falls to 20 fps, crediting a press calls that never ran."""
    clock, f, t = T.TickClock(), 0, 1000.0
    ests = []

    def run(n, fps, **st):
        nonlocal f, t
        for _ in range(n):
            f, t = f + 2, t + 2.0 / fps
            clock.observe(_st(f, mtime=t, **st))
            ests.append(clock.rate())

    run(150, 60.0, field=350)
    run(10, 20.0, field=351)                                         # no fading frame read: arrived, slow
    run(90, 60.0, field=351)
    ready = [r for r in ests if r.ready]
    assert ready and all(r.fps == pytest.approx(60.0, rel=0.01) and r.fps_lo > 55.0 for r in ready), \
        min(ready, key=lambda r: r.fps_lo)


def test_the_clock_says_how_many_ticks_a_hitch_added():
    """A hitch -- one frame of 130 ms at 60 fps -- catches up four ticks in that frame (FPSManager.cs:94-99), which no
    rate foresees: Rate.reach is no bound through it. TickClock.excess_ticks says afterwards what the published frames
    of a span took beyond what the rate accounts for, in ticks: about 3.4 across the hitch, 0 where there was none, 0
    where either end was never read."""
    clock, t = T.TickClock(), 1000.0
    for i in range(1, 121):
        t += 2 / 60.0 + (0.13 - 1 / 60.0 if i == 100 else 0.0)
        clock.observe(_st(2 * i, rt=t))
    r = clock.rate()
    assert r.ready and r.fps == pytest.approx(60.0)
    assert clock.excess_ticks(180, 220, r) == pytest.approx((0.13 - 1 / 60.0) * 30.0, abs=0.01)
    assert clock.excess_ticks(100, 140, r) == 0.0 and clock.excess_ticks(181, 220, r) == 0.0


# --------------------------------------------------------------------------- the Rate's own laws
def test_a_rate_refuses_what_it_cannot_plan_by():
    """A spread that does not hold its own median, a rate that is not positive, an unknown source, a negative frame
    count and an unknown gait are refused where they are made -- never planned by."""
    with pytest.raises(ValueError, match="does not contain"):
        T.Rate(60.0, 61.0, 62.0)
    with pytest.raises(ValueError, match="positive"):
        T.Rate(0.0, 0.0, 0.0)
    with pytest.raises(ValueError, match="source"):
        T.Rate(60.0, 60.0, 60.0, source="guess")
    with pytest.raises(ValueError, match="negative"):
        T.Rate.default().ticks_sure(-2)
    with pytest.raises(ValueError, match="gait"):
        T.Rate.default().speed("jog")
    with pytest.raises(ValueError, match="field_tps"):
        T.TickClock(field_tps=0)


def test_todays_engine_at_a_steady_60_pays_a_tick_each_way():
    """TODAY'S ENGINE is timed by the state file's mtime, whose estimate is widened MTIME_WIDEN (2%) -- so at an exact,
    jitter-free 60 fps the spread is 58.8-61.2, and wherever N x 30 / fps is whole the bounds move a tick from the
    exact clock's: a 2-frame walk reaches 90u (60 on the fake's rt), 4 run frames 240u (180); a tick is sure only in 3
    frames (2), two in 5 -- a settle's stillness waits a third still publish -- and the push lock's 14 ticks take 29
    frames (28). Honest: the display runs at 59.94 Hz, where 2 frames can hold 2 ticks. What the driver's docstrings
    quote as "at 60 fps" is the exact clock's; this is the cost on today's (the s91 engine's published clock is not
    widened)."""
    clock = T.TickClock()
    f, t = 0, 1000.0
    for _ in range(300):
        f, t = f + 2, t + 2 / 60.0
        clock.observe(_st(f, mtime=t))
    r = clock.rate()
    assert r.ready and r.source == "mtime" and (r.fps_lo, r.fps_hi) == pytest.approx((60 / 1.02, 61.2), rel=1e-6)
    assert (r.reach(2, "walk"), r.reach(4, "run"), r.reach(8, "run")) == (90.0, 240.0, 360.0)
    assert (r.frames_for_ticks(1), r.frames_for_ticks(2), r.frames_for_ticks(14)) == (3, 5, 29)
    exact = _clock_of([1.0 / 60.0] * 600, kind="rt").rate()
    assert (exact.reach(2, "walk"), exact.frames_for_ticks(1), exact.frames_for_ticks(14)) == (60.0, 2, 28)


def test_a_press_is_sure_only_of_its_whole_calls():
    """The engine turns and steps in WHOLE calls, a walked one a tick, in a phase nobody sees: at half a tick a frame
    (60 fps) 8 frames are 4 calls, 9 are 4 or 5 -- sure of 4 -- and 3 are sure of 1; one frame is sure of none. A RUN
    tick is two calls and the ticks are whole, so the calls come in PAIRS: 1-4 run frames are sure of 0, 2, 2, 4. At 31
    fps (just under a tick a frame) a 4-frame walk is sure of 3, at 30 of 4. (Once doorface.sure_calls: Rate.calls_sure
    is the one owner of the law now.)"""
    r = T.Rate.default()
    assert [r.calls_sure(n, "walk") for n in (1, 2, 3, 8, 9, 10)] == [0, 1, 1, 4, 4, 5]
    assert [r.calls_sure(n, "run") for n in (1, 2, 3, 4)] == [0, 2, 2, 4]
    assert T.Rate(31.0, 31.0, 31.0).calls_sure(4, "walk") == 3 and T.Rate(30.0, 30.0, 30.0).calls_sure(4, "walk") == 4


def test_calls_become_frames_in_whole_ticks():
    """frames_for_calls: the fewest frames of a gait sure to make so many MovePC calls -- whole ticks, a run's in
    PAIRS: the push lock's 27 run calls are 14 ticks (28 frames at 60 fps, 14 at 30), a turn's 8 are 4 (8 frames), the
    facing press's 4 walked calls 4 ticks (8 frames); no calls, no frames."""
    r60, r30 = T.Rate.default(), T.Rate(30.0, 30.0, 30.0)
    assert (r60.frames_for_calls(27, "run"), r30.frames_for_calls(27, "run")) == (28, 14)
    assert r60.frames_for_calls(8, "run") == 8 and r60.frames_for_calls(4, "walk") == 8
    assert r60.frames_for_calls(0, "walk") == 0 and r60.frames_for_calls(0.5, "walk") == 2


def test_a_count_within_float_noise_of_a_whole_one_is_that_whole_one():
    """An epoch-scale mtime's last bit is ~2.4e-7 s -- a few parts in a million of a 2-frame interval -- so a true 30 fps
    measures 29.99997 one read and 30.00003 the next. A count that far from whole is the whole count: 600u of run is 10
    frames at either (it was 9 at one and 10 at the other -- the smooth-hold [mtime] test's reversal), and 2 frames are
    sure of 2 ticks and hold at most 2. A true fraction of a tick is never rounded away."""
    for fps in (29.99997, 30.0, 30.00003):
        r = T.Rate(fps, fps, fps, source="mtime", samples=20, frame=100)
        assert r.frames_for(600.0, "run") == 10 and r.ticks_sure(2) == 2 == r.ticks_most(2), fps
        assert r.frames_for_ticks(4) == 4 and r.frames_at_least(1.5) == 45, fps
    assert T.Rate(30.1, 30.1, 30.1).ticks_sure(2) == 1 and T.Rate(29.9, 29.9, 29.9).ticks_most(2) == 3


def test_frames_for_ticks_and_the_time_budgets():
    """frames_for_ticks is the least N sure of the ticks at the spread's fast end; frames_at_least a wait that lasts at
    least its seconds even at the fast end, frames_at_most a cap that lasts no more at the slow end; frames_for sizes
    by the average and never answers zero."""
    r = T.Rate(31.2, 30.0, 33.0, source="mtime", samples=24, frame=900)
    for k in range(1, 30):
        n = r.frames_for_ticks(k)
        assert r.ticks_sure(n) >= k > r.ticks_sure(n - 1)
    assert r.frames_for_ticks(0) == 0
    assert r.frames_at_least(1.5) == math.ceil(1.5 * 33.0) and r.frames_at_least(1.5) / 33.0 >= 1.5
    assert r.frames_at_most(0.5) == math.floor(0.5 * 30.0) and r.frames_at_most(0.5) / 30.0 <= 0.5
    assert r.frames_for(600.0, "run") == math.floor(600.0 / r.speed("run")) and r.frames_for(1.0, "walk") == 1
    d = r.as_dict()
    assert d["source"] == "mtime" and d["samples"] == 24 and d["per_frame"] == pytest.approx(30 / 31.2, abs=1e-4)
    assert "31.2 fps" in r.describe() and "not measured" in T.Rate.default().describe()


def test_field_tps_follows_the_ini_the_way_the_engine_reads_it(tmp_path):
    """``[Graphics] FieldTPS`` through the harness's own ini reader (LAST wins): honoured only in a section whose
    ``Enabled`` reads exactly 1 (a disabled section resets to the defaults, IniReader.cs:285-286), 30 when absent,
    unparseable or not positive -- and env.json's Graphics row carries it."""
    ini = tmp_path / "Memoria.ini"
    assert T.read_field_tps(tmp_path) == 30.0                       # no ini at all
    for text, want in (("[Graphics]\nEnabled = 1\nFieldTPS = 60\n", 60.0),
                       ("[Graphics]\nEnabled = 0\nFieldTPS = 60\n", 30.0),
                       ("[Graphics]\nEnabled = true\nFieldTPS = 60\n", 30.0),
                       ("[Graphics]\nFieldTPS = 60\n", 30.0),
                       ("[Graphics]\nEnabled = 1\nFieldTPS = fast\n", 30.0),
                       ("[Graphics]\nEnabled = 1\nFieldTPS = -5\n", 30.0),
                       ("[Graphics]\nEnabled = 1\nFieldTPS = 45\n[Graphics]\nFieldTPS = 25\n", 25.0)):
        ini.write_text(text, encoding="utf-8")
        assert T.read_field_tps(tmp_path) == want, text
    ini.write_text("[Graphics]\nEnabled = 1\nFieldFPS = -1\nFieldTPS = 30\nVSync = 1\nTileSize = 32\n",
                   encoding="utf-8")
    assert read_memoria_ini(ini)["Graphics"] == {"Enabled": "1", "FieldFPS": "-1", "FieldTPS": "30", "VSync": "1"}


# --------------------------------------------------------------------------- the fake game's tick model
def _hand(game, **kw):
    """A FakeGame on field 30820 with control at the origin, no coast (a released press stops dead), stepped by
    :func:`_frames` -- the clock advancing with each frame, as the loop's does."""
    fake = FakeGame(game, **kw)
    fake.ui_state, fake.field_id, fake.control = "FieldHUD", 30820, True
    fake.coast_frames = 0
    return fake


def _frames(fake, n, *buttons):
    """Step ``fake`` ``n`` frames holding ``buttons`` for exactly those frames."""
    for _ in range(n):
        fake.frame += 1
        for b in buttons:
            fake.down_at[b], fake.held[b] = fake.frame, fake.frame + 1
        fake._step_world()


@pytest.fixture
def game(tmp_path):
    (tmp_path / "x64").mkdir()
    return tmp_path


def test_the_fake_at_its_defaults_moves_exactly_as_before(game):
    """THE 60 FPS GUARD, FAKE HALF. At the defaults (60 fps, mean ticks) a frame is exactly half a tick: a run frame
    30.0u in 1.0 call, a walked one 15.0u in 0.5 -- bit for bit the old per-frame literals -- the virtual clock 1/60 s a
    frame, and the coast after a press one more frame of it."""
    fake = _hand(game)
    _frames(fake, 4, "up")
    assert fake.player[2] == 120.0 and fake._frame_ticks == 0.5 and fake.rt == pytest.approx(4 / 60.0)
    _frames(fake, 4, "up", "cancel")
    assert fake.player[2] == 180.0
    fake.coast_frames = 1
    _frames(fake, 3, "right")
    _frames(fake, 1)
    assert fake.player[0] == 120.0 and fake.ticks_run == pytest.approx(6.0)


@pytest.mark.parametrize("fps,run_frame", [(30.0, 60.0), (31.2, 30 * 60 / 31.2), (120.0, 15.0)])
def test_the_fake_moves_per_tick_at_its_render_rate(game, fps, run_frame):
    """At another render rate a frame holds 30 / fps ticks, so it moves 60u a tick running and 30 walking whatever
    the frame count: a run frame 60u at 30 fps, 15u at 120 -- the SAME distance a second -- and its turn spends the
    ticks' calls (two a running tick)."""
    from ff9mapkit.content import doorface
    fake = _hand(game, render_fps=fps)
    n = int(fps / 4)                                                # a quarter second of frames (the box ends at 600)
    _frames(fake, n, "up")
    assert fake.player[2] == pytest.approx(n * run_frame) and fake.player[2] == pytest.approx(1800.0 * n / fps)
    fake2 = _hand(game, render_fps=fps)
    _frames(fake2, 3, "right", "cancel")
    assert fake2.player[0] == pytest.approx(3 * run_frame / 2)
    calls = 3 * (30.0 / fps)                                        # walking: one call a tick
    assert fake2._face_deg == pytest.approx(doorface.turn_step(0.0, -90.0, calls))


def test_quantized_ticks_are_the_engines_whole_ticks(game):
    """``ticks="quantized"``: each frame runs FPSManager's whole ticks -- the fake's count IS the accumulator's -- and
    a tick is a whole step: at 120 fps a 2-frame run hold moves 0 or 60u, never the 30 an average would say, and the
    frames between ticks move nothing."""
    fake = _hand(game, render_fps=120.0, ticks="quantized")
    acc, want = T.TickAccumulator(), []
    moved = []
    for _ in range(30):
        before = fake.player[2]
        _frames(fake, 1, "up")
        want.append(acc.advance(1.0 / 120.0))
        moved.append(fake.player[2] - before)
    assert fake.ticks_run == sum(want) and moved == [60.0 * k for k in want]
    assert set(want[1:]) == {0, 1}
    two = [moved[i] + moved[i + 1] for i in range(1, 28)]
    assert set(two) == {0.0, 60.0}


def test_the_coast_is_a_frame_even_when_no_tick_runs_in_it(game):
    """A coast a test ASKS for (``coast_frames``: the smooth 60 fps model's stand-in for the tick a one-frame hold
    catches in one phase -- the engine itself buffers no key, see FakeGame.coast_frames) is counted in FRAMES and moved
    in the ticks that frame runs. At 120 fps quantized a tick falls on about one frame in four, so a one-frame press on a
    tick frame steps him one tick (60u), its coast frame runs no tick and moves him nothing -- and is spent: the next
    tick frame, a few frames on, does not carry the old press."""
    fake = _hand(game, render_fps=120.0, ticks="quantized")
    fake.coast_frames = 1
    acc = T.TickAccumulator()
    ticks = [acc.advance(1.0 / 120.0) for _ in range(40)]
    k = next(i for i in range(2, 30) if ticks[i] == 1 and ticks[i + 1] == 0)   # frame k + 1 (1-based) ran a tick
    _frames(fake, k)
    _frames(fake, 1, "up")
    assert fake.player[2] == 60.0
    _frames(fake, 8)                                                # the coast frame, then two more tick frames
    assert fake.player[2] == 60.0 and fake._coast is None


def test_the_fake_coasts_only_at_its_calibrated_model(game):
    """The engine runs no coast (IsHeld keys on the current frame, MovePC reads the pad every call). The fake's default
    coast is its 60 fps MEAN model's alone -- where a frame is half a tick and the bench's extra frame stands for the
    tick a one-frame hold catches in one phase: one frame there, as before. Anywhere else, none: at 30 fps a one-, two-
    and four-frame run hold move 60, 120 and 240u -- their ticks -- where a frame of coast added a whole tick more,
    exactly Rate.reach with no slack."""
    at60 = FakeGame(game)
    at60.ui_state, at60.field_id, at60.control = "FieldHUD", 30820, True
    _frames(at60, 3, "up")
    _frames(at60, 2)
    assert at60.player[2] == 120.0                                  # 3 frames and the coast frame: 4 x 30u
    for mode in ("mean", "quantized"):
        for n, want in ((1, 60.0), (2, 120.0), (4, 240.0)):
            fake = FakeGame(game, render_fps=30.0, ticks=mode)
            fake.ui_state, fake.field_id, fake.control = "FieldHUD", 30820, True
            _frames(fake, 1)                                        # the quantized first frame's reset tick
            _frames(fake, n, "up")
            _frames(fake, 3)
            assert fake.player[2] == want, (mode, n, fake.player[2])
    fake = FakeGame(game, render_fps=30.0)
    fake.coast_frames = 1                                           # a test that asks gets what it asks for
    fake.ui_state, fake.field_id, fake.control = "FieldHUD", 30820, True
    _frames(fake, 1, "up")
    _frames(fake, 2)
    assert fake.player[2] == 120.0


@pytest.mark.parametrize("fps", [60.0, 120.0])
def test_a_freeze_holds_the_ticks_its_script_counts_at_any_rate(game, fps):
    """A freeze (the script's pad mask) is counted by its script, once a field TICK: ``frames: n`` is n frames of the
    calibrated 60 fps -- n / 2 ticks -- so 20 holds movement 20 frames at 60 fps and 40 at 120, the same ten ticks. As
    frames it held half the ticks at 120, and a wait-versus-freeze test off 60 fps would have raced a shorter freeze
    than the engine's."""
    fake = _hand(game, render_fps=fps, walkmesh=(-2000.0, -2000.0, 2000.0, 2000.0))
    fake.freezes = {30820: [{"zone": [[-10, 20], [10, 20], [10, 60], [-10, 60]], "frames": 20}]}
    held = 0
    for _ in range(400):
        z = fake.player[2]
        _frames(fake, 1, "up")
        if fake._froze and fake.player[2] == z:
            held += 1
        elif held:
            break
    assert fake._froze and held == int(20 * fps / 60.0) - 1, (fps, held)       # the freeze frames after its own


def test_a_hitch_is_caught_up_in_its_frame(game):
    """A hitch (`hitch`, or ``hitches={frame: seconds}``) makes one frame longer on the virtual clock: it runs the ticks
    those seconds hold -- 157 ms at 60 fps quantized, 4-6 ticks, a running press 60u each -- and rt carries the time."""
    fake = _hand(game, ticks="quantized")
    _frames(fake, 4, "up")
    z, rt = fake.player[2], fake.rt
    fake.hitch(0.157)
    _frames(fake, 1, "up")
    assert fake._frame_ticks in (4.0, 5.0, 6.0) and fake.player[2] - z == 60.0 * fake._frame_ticks
    assert fake.rt - rt == pytest.approx(0.157 + 1 / 60.0)
    mean = _hand(game, hitches={3: 0.1})
    _frames(mean, 3, "up")
    assert mean.player[2] == pytest.approx(30.0 + 30.0 + 60.0 * (0.1 + 1 / 60.0) * 30.0)


def test_the_push_lock_counts_calls_not_frames(game):
    """The walk-through lock (sLockTimer) counts MovePC calls into a body: 25, then it flips on the next. At 60 fps
    that is the 26th run frame; at 120 fps, half a call a frame, TWICE the frames (the first 15u step does not reach
    him yet) -- so a hold sized in frames at 60 fps (27) never opens it at 120, and one sized in ticks does.
    Quantized, the flip lands on the call that reaches 25, two calls a tick."""
    def frames_to_open(**kw):
        fake = _hand(game, **kw)
        fake.blockers = {30820: [{"x": 0.0, "z": 100.0, "r": 80.0}]}
        for n in range(1, 400):
            _frames(fake, 1, "up")
            if fake._lock < 0:
                return n
        return None
    at60 = frames_to_open()
    at120 = frames_to_open(render_fps=120.0)
    assert at60 == 26 and at120 == 2 * at60
    rate120 = T.Rate(120.0, 120.0, 120.0, source="rt", samples=30, frame=1)
    assert rate120.frames_for_ticks(13) == 52 >= at120 - 1 > 27
    acc, ticks, frame = T.TickAccumulator(), 0, 0
    while ticks < 13:                                               # 13 run ticks: 26 calls, the 26th flips it
        frame, ticks = frame + 1, ticks + acc.advance(1.0 / 120.0)
    assert frames_to_open(render_fps=120.0, ticks="quantized") == frame


@pytest.mark.parametrize("fps", [60.0, 120.0])
def test_the_push_timer_runs_two_ticks_at_any_render_rate(game, fps):
    """SCollTimer, set on every push-out, runs two field TICKS: while it runs the lock keeps its count (MovePC is still
    called once a tick with nothing held), and once it runs out the count drops to 0 -- so a pause of 1.5 ticks
    between bursts keeps the walk-through coming and one of 2.5 ticks loses it. At 120 fps those are 6 and 10 frames,
    not the 3 and 5 that frames at 60 fps would say."""
    per_tick = fps / 30.0
    for pause, kept in ((1.5, True), (2.5, False)):
        fake = _hand(game, render_fps=fps)
        fake.blockers = {30820: [{"x": 0.0, "z": 100.0, "r": 80.0}]}
        _frames(fake, int(10 * per_tick), "up")                     # ten ticks into him: the count is running
        assert fake._lock > 0
        _frames(fake, int(pause * per_tick))
        assert (fake._lock > 0) is kept, (fps, pause, fake._lock, fake._coll)


def test_a_walker_covers_the_same_ground_a_second_at_any_rate(game):
    """A walker's ``speed`` is units a frame of the calibrated 60 fps model -- speed / 0.5 a tick, as MoveToward steps
    once a tick -- so one second of frames carries it the same distance at 30, 60 or 144 fps."""
    for fps in (30.0, 60.0, 144.0):
        fake = _hand(game, render_fps=fps)
        fake.player = [0.0, 0.0, -500.0]
        fake.blockers = {30820: [{"x": 0.0, "z": 0.0, "r": 40.0, "path": [(0.0, 0.0), (1000.0, 0.0)], "speed": 5.0}]}
        _frames(fake, int(fps))
        assert fake.blockers[30820][0]["x"] == pytest.approx(300.0), fps


@pytest.mark.parametrize("ticks", ["mean", "quantized"])
def test_a_turns_report_waits_two_frames_that_ran_a_tick(game, ticks):
    """An s90 ``turn`` reports once the field has run TurnSettlePasses passes on the final facing -- counted as the
    agent counts them, frames that ran a pass. Mean ticks run a share of one every frame, so at 120 fps the report
    comes two frames after the lift; quantized, a tick falls on about every fourth frame, and the report waits for the
    second frame after the lift that ran one -- the engine's accumulator says which. The turn itself spends whole run
    calls, two a tick."""
    from ff9mapkit.content import doorface
    fake = _hand(game, render_fps=120.0, ticks=ticks)
    fake.facing_mode = "published"
    fake.dir.mkdir(parents=True, exist_ok=True)
    fake._execute(["turn", "right", "8"])                           # keys down frames 1-8, lifted on 9
    acc, ran, calls = T.TickAccumulator(), {}, 0.0
    while not (fake.dir / "events.jsonl").exists() or "turn_end" not in (fake.dir / "events.jsonl").read_text():
        fake.frame += 1
        fake._step_world()
        fake._service_turn()
        ran[fake.frame] = acc.advance(1.0 / 120.0) if ticks == "quantized" else 0.25
        calls += 2 * ran[fake.frame] if fake.frame <= 8 else 0.0
        assert fake.frame < 60
    lifted = 9
    settled = [f for f in sorted(ran) if f > lifted and ran[f] > 0][:2]
    ends = [json.loads(ln) for ln in (fake.dir / "events.jsonl").read_text().splitlines() if "turn_end" in ln]
    assert len(ends) == 1 and ends[0]["frame"] == settled[-1] == fake.frame
    assert fake._face_deg == pytest.approx(doorface.turn_step(0.0, -90.0, calls))
    if ticks == "mean":
        assert settled == [10, 11]


def test_the_legacy_turn_knobs_are_refused_off_the_model_they_mean(game):
    """`tick_phase` is the 60 fps mean model's turn-only whole calls, `turn_calls` calls a frame: set against a model
    where they cannot mean that -- another render rate, quantized ticks -- they are refused, in either order."""
    fake = FakeGame(game, render_fps=30.0)
    with pytest.raises(ValueError, match="tick_phase"):
        fake.tick_phase = 0
    fake = FakeGame(game)
    fake.tick_phase = 1
    with pytest.raises(ValueError, match="tick_phase"):
        fake.render_fps = 120.0
    with pytest.raises(ValueError, match="tick_phase"):
        fake.tick_mode = "quantized"
    fake = FakeGame(game, ticks="quantized")
    with pytest.raises(ValueError, match="turn_calls"):
        fake.turn_calls = 0.5
    with pytest.raises(ValueError, match="ticks"):
        FakeGame(game, ticks="exact")
    with pytest.raises(ValueError, match="publish"):
        FakeGame(game, publish=("frames",))
    with pytest.raises(ValueError, match="render_fps"):
        FakeGame(game, render_fps=0)


# --------------------------------------------------------------------------- the fake's clocks, through the channel
def _armed_fake(game, **kw):
    """The fake started, armed, on field 350 with control -- publishing -- and a Channel whose observer feeds a
    TickClock, exactly as Session's read path does."""
    fake = FakeGame(game, **kw)
    fake.ui_state, fake.field_id, fake.control = "FieldHUD", 350, True
    ch = Channel(game)
    ch.reset()
    ch.arm(force_cycle=False)
    clock = T.TickClock()
    ch.observer = clock.observe
    fake.start()
    return fake, ch, clock


def _measure(ch, clock, *, budget=6.0, want=None):
    """Read the channel (every read feeds the clock) until the rate is ready -- and, with ``want``, until it holds
    that many pairs -- or the budget runs out."""
    deadline = time.time() + budget
    while time.time() < deadline:
        ch.state()
        r = clock.rate()
        if r.ready and (want is None or r.samples >= want):
            return r
        time.sleep(0.003)
    return clock.rate()


@pytest.mark.parametrize("publish,keys", [(("rt",), {"rt"}), (("rt", "ticks"), {"rt", "ticks"}), ((), set()),
                                          (("mtime",), set())])
def test_the_fake_publishes_the_clocks_it_is_asked_for(game, publish, keys):
    """``rt`` and ``ticks`` ride IN the document when asked; with "mtime" neither does, and state.json's modified time
    is the virtual write time (the clock's anchor + rt) instead of the moment the bytes landed."""
    fake, ch, _clock = _armed_fake(game, publish=publish)
    try:
        deadline = time.time() + 5.0
        st = None
        while time.time() < deadline and (st is None or st.frame < 40):
            st = ch.state()
            time.sleep(0.01)
        assert st is not None and st.frame >= 40
        assert {k for k in ("rt", "ticks") if k in st.raw} == keys
        if "rt" in keys:
            assert st.raw["rt"] == pytest.approx(st.frame / 60.0, abs=2 / 60.0)
        if "ticks" in keys:
            assert st.raw["ticks"] == pytest.approx(st.raw["rt"] * 30.0, abs=1.0)
        if "mtime" in publish:
            fake.mode = "frozen"                                    # hold still so the file and rt agree
            time.sleep(0.2)
            doc = json.loads((ch.dir / "state.json").read_text(encoding="utf-8-sig"))
            stamp = (ch.dir / "state.json").stat().st_mtime
            assert stamp == pytest.approx(fake._wall0 + doc["frame"] / 60.0, abs=2e-3)
            fake.mode = "normal"
    finally:
        fake.stop()


@pytest.mark.parametrize("fps", [31.2, 60.0, 120.0])
def test_the_tickclock_times_the_fake_by_its_published_rt(game, fps):
    """The default fake publishes its virtual clock: the driver's TickClock, fed by the channel's observer, measures the
    RENDER rate exactly -- whatever the loop's own wall pace (240 a second here)."""
    fake, ch, clock = _armed_fake(game, render_fps=fps)
    try:
        r = _measure(ch, clock, want=12)
    finally:
        fake.stop()
    assert r.ready and r.source == "rt" and r.fps == pytest.approx(fps, rel=1e-6)
    assert (r.fps_lo, r.fps_hi) == pytest.approx((fps, fps), rel=1e-6)


def test_the_tickclock_times_the_fake_by_the_state_files_mtime(game):
    """``publish=("mtime",)``: no clock in the document, so the driver falls back on state.json's mtime -- today's
    engine -- and the fake, running in real time and stamping each write with its virtual time, is measured at its
    render rate through that path too (within the mtime widening)."""
    fake, ch, clock = _armed_fake(game, render_fps=30.0, publish=("mtime",))
    try:
        r = _measure(ch, clock, budget=8.0, want=12)
    finally:
        fake.stop()
    assert r.ready and r.source == "mtime" and r.fps == pytest.approx(30.0, rel=0.03)
    assert r.fps_lo <= 30.0 <= r.fps_hi
