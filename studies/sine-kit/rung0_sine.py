"""RUNG 0 of the sine kit -- computed prop motion, in-game, against an exact oracle.

    py studies/sine-kit/sine0_bench.py deploy
    py tools/play.py studies/sine-kit/rung0_sine.py --label sine-rung0

The bench (field 30945, bench/sine0.field.toml + the daemon sine0_bench.py seats) moves two kit props every tick with
MoveInstantXZYEx 0xAD + TurnInstantEx 0x87 driven by B_SIN/B_COS/B_SIN2, and mirrors -- BEFORE each tick's writes --
the clock the previous writes used and both props' published transform (obj(uid).f[0..3]) into Global Int16s. Every
published sample therefore carries its own clock t, and sine0_bench.predict(t) says exactly what the engine must hold.

LATCH the daemon holds (Wait 1) until the player is bound, movement is enabled and both props are ready -- run 1's
      bare Wait(45) threw at field entry (InvalidCast in getvobj's unguarded f[3], NullReference in 0xAD)
PRE  P0 30945 is served by FF9CustomMap alone; P1 the DEPLOYED .eb (every language) carries the daemon, aimed at the
     real prop uids; P2 the float32 rsin predictor is within one unit of the float64 sine over a whole turn
C0   the daemon runs: >= 200 distinct clock values, spanning more than one full bob period (256 ticks)
C1   UNIT + AMPLITUDE + PERIOD: every sampled position of A and B == predict(t) (the orbit r = 300, 128 ticks a
     turn; B's bob +-60, 256 ticks) -- exact, or the worst error and the exact share are reported
C2   FACING: both props' facing byte == predict(t) (the +192 tangent), mod 256
C3   OPERAND ORDER: A's height operand reads back -150 on every sample (0xAD's 2nd operand is the height, not z) and
     B's bob shows ONLY in f[1], while both stay on the r = 300 circle
C4   SINGLE-DAEMON PHASE LOCK: B sits diametrically opposite A in every sample (the 128-unit offset)
C5   NO ENGINE OVERRIDE BETWEEN TICKS: C1 holds on read-before-write mirrors, i.e. after a full engine frame -- no
     walkmesh re-ground (pathing is off), no smoother drift, no snap
C6   THE ANGLE CONVENTION, calibrated on the engine's own movement: hold each d-pad direction, measure the player's
     world displacement, and require the engine's facing byte to equal the byte that direction implies under
     "0 south, 64 west, 128 north, 192 east" (direction(a) = (-sin a, -cos a)) -- which is what makes C2's +192 the
     TANGENT and not just a stored number
NC-THROW  no NullReference / InvalidCast / IndexOutOfRange through the event engine or the evaluator
"""
from __future__ import annotations

import math
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(HERE))
import sine0_bench as SB  # noqa: E402
from ff9mapkit.config import LANGS, ModLayout  # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException"}
KEYS = ("t", "ax", "ay", "az", "ar", "bx", "by", "bz", "br", "pr", "gate")


def _i16(st, byte_index) -> int:
    v = sum(1 << i for i in range(16) if st.flag(byte_index * 8 + i))
    return v - 0x10000 if v & 0x8000 else v


def _mirrors(st) -> dict:
    return {k: _i16(st, SB.M[k]) for k in KEYS} | {"T": _i16(st, SB.T), "frame": st.frame}


def _watch(g) -> None:
    bits = []
    for off in [SB.T] + [SB.M[k] for k in KEYS]:
        bits += [off * 8 + i for i in range(16)]
    g.watch(*bits)


def _preflight(g) -> None:
    folders = [p.parent.name for p in GAME.glob("*/DictionaryPatch.txt")
               if re.search(rf"FieldScene {SB.FIELD_ID}\b", p.read_text(encoding="utf-8", errors="replace"))]
    g.check(folders == ["FF9CustomMap"], "P0: 30945 is served by FF9CustomMap alone", str(folders))
    live = ModLayout(GAME / SB.MOD_FOLDER)
    langs = [L for L in LANGS if live.eb_path(L, f"EVT_{SB.FIELD_NAME}.eb.bytes").exists()]
    patched = [L for L in langs if SB.is_patched(live.eb_path(L, f"EVT_{SB.FIELD_NAME}.eb.bytes").read_bytes())]
    uids = SB.prop_uids(live.eb_path(langs[0], f"EVT_{SB.FIELD_NAME}.eb.bytes").read_bytes()) if langs else None
    g.check(bool(langs) and patched == langs, "P1: every deployed language .eb carries the daemon",
            f"langs {langs} patched {patched}")
    g.check(uids == (2, 3), "P1: the daemon drives the real prop uids (balloon 2, cask 3)", str(uids))
    worst = max(abs(SB.rsin(a) - 4096 * math.sin(a * 2 * math.pi / 4096)) for a in range(4096))
    g.check(worst < 1.0, "P2: the float32 rsin predictor is within one unit of float64 sin*4096 over a turn",
            f"{worst:.4f}")


def _collect(g, seconds: float) -> dict:
    """Every distinct clock value seen, with its mirrors."""
    got: dict = {}
    deadline = time.time() + seconds
    last = None
    while time.time() < deadline:
        st = g.state
        if st.frame != last:
            last = st.frame
            m = _mirrors(st)
            if m["T"] > 0:
                got.setdefault(m["t"], m)
        time.sleep(0.005)
    return got


def _dir_to_byte(dx: float, dz: float) -> int:
    """The facing byte whose direction (-sin a, -cos a) is (dx, dz) -- the '0 south, 64 west' convention."""
    return round(math.atan2(-dx, -dz) / (2 * math.pi) * 256) % 256


def _angdiff(a: int, b: int) -> int:
    d = (a - b) % 256
    return min(d, 256 - d)


def run(g) -> None:
    _preflight(g)
    g.note("sine kit rung 0")
    g.newgame()
    mark = g.log_mark()
    g.warp(SB.FIELD_ID)
    g.wait_for(lambda s: s.field_id == SB.FIELD_ID, timeout=60, what="field 30945")
    g.state_every(1)
    _watch(g)
    st = g.wait_for(lambda s: _i16(s, SB.T) > 5, timeout=30, what="the daemon's clock running")
    gate = _i16(st, SB.M["gate"])
    print(f"[sine-rung0] the daemon held {gate} tick(s) at its latch (player bound + movement enabled + both props "
          f"ready) before moving anything")
    g.check(gate > 0, "LATCH: the daemon waited at its latch -- the field was NOT yet safe when it started (run 1's "
            "bare Wait(45) threw there)", str(gate))
    g.shot("1-orbit")

    samples = _collect(g, 12.0)
    g.shot("2-orbit-later")
    ts = sorted(samples)
    span = (ts[-1] - ts[0]) if ts else 0
    print(f"[sine-rung0] {len(ts)} distinct clock values, t {ts[:1]}..{ts[-1:]} (span {span})")
    if len(ts) >= 2:
        a, b = samples[ts[0]], samples[ts[-1]]
        if b["frame"] != a["frame"]:
            print(f"[sine-rung0] cadence: {(ts[-1] - ts[0]) / (b['frame'] - a['frame']):.3f} ticks per published frame")
    g.check(len(ts) >= 200 and span > 256, "C0: the daemon runs -- >= 200 distinct clock values over more than one "
            "full bob period", f"{len(ts)} values, span {span}")

    pos_keys = ("ax", "ay", "az", "bx", "by", "bz")
    worst, exact, bad = 0, 0, []
    for t in ts:
        m, p = samples[t], SB.predict(t)
        err = max(abs(m[k] - p[k]) for k in pos_keys)
        worst = max(worst, err)
        exact += err == 0
        if err > 1 and len(bad) < 5:
            bad.append((t, {k: (m[k], p[k]) for k in pos_keys if m[k] != p[k]}))
    print(f"[sine-rung0] C1 positions: worst |err| {worst}, exact in {exact}/{len(ts)}")
    g.check(bool(ts) and worst <= 1, "C1: every sampled position of both props == predict(t) (r 300, 128 ticks a "
            "turn; the bob +-60 over 256) within one unit", f"worst {worst}, exact {exact}/{len(ts)}, e.g. {bad}")
    g.check(bool(ts) and exact == len(ts), "C1: ...and EXACTLY -- the float32 rsin + truncating B_DIV predictor is "
            "the engine's own arithmetic", f"exact {exact}/{len(ts)}")

    fbad = [(t, samples[t]["ar"], SB.predict(t)["ar"], samples[t]["br"], SB.predict(t)["br"]) for t in ts
            if _angdiff(samples[t]["ar"], SB.predict(t)["ar"]) > 1 or _angdiff(samples[t]["br"], SB.predict(t)["br"]) > 1]
    g.check(bool(ts) and not fbad, "C2: both props' facing byte == predict(t) (the +192 tangent) within one unit",
            str(fbad[:5]))

    ay = {samples[t]["ay"] for t in ts}
    by = {samples[t]["by"] for t in ts}
    radius_bad = [t for t in ts for w in "ab"
                  if abs(math.hypot(samples[t][w + "x"] - SB.CX, samples[t][w + "z"] - SB.CZ) - SB.R) > 2]
    g.check(ay == {-SB.H} and len(by) >= 40 and min(by) >= -SB.H - SB.BOB and max(by) <= -SB.H + SB.BOB
            and not radius_bad, "C3: operand order -- A's height operand reads back -150 always, B's bob lives ONLY "
            "in f[1] (>= 40 distinct heights within +-60), both stay on the r = 300 circle",
            f"A heights {sorted(ay)[:5]}, B {len(by)} heights {min(by, default=None)}..{max(by, default=None)}, "
            f"off-circle {radius_bad[:5]}")

    opp_bad = [t for t in ts if abs((samples[t]["bx"] - SB.CX) + (samples[t]["ax"] - SB.CX)) > 1
               or abs((samples[t]["bz"] - SB.CZ) + (samples[t]["az"] - SB.CZ)) > 1]
    g.check(bool(ts) and not opp_bad, "C4: single-daemon phase lock -- B is diametrically opposite A in every sample",
            str(opp_bad[:5]))

    # C6: the angle convention on the engine's own walk
    basis = g.calibrate_axes()
    print(f"[sine-rung0] axes: {basis}")
    rows = []
    # hold() does NOT block: hold 30 frames, let the turn finish (16), then measure a STRAIGHT stretch (16..24)
    # while still held -- the displacement then has no turning arc in it (run 2's first cut measured through the
    # turn and mixed two headings). 30 frames a leg ~ 900u: right/up/left/down trace a square inside the mesh.
    for button in ("right", "up", "left", "down"):
        g.hold(button, 30)
        g.wait_frames(16)
        s0 = g.state
        g.wait_frames(8)
        s1 = g.state
        g.wait_frames(14)                                  # the hold ends, the player stops
        dx, dz = s1.player_x - s0.player_x, s1.player_z - s0.player_z
        face = _i16(s1, SB.M["pr"])
        want = _dir_to_byte(dx, dz)
        rows.append((button, round(dx), round(dz), face, want))
        print(f"[sine-rung0] C6 {button}: moved ({dx:.0f},{dz:.0f}) -> facing byte {face}, convention says {want}")
    g.shot("3-walk")
    ok = all(math.hypot(dx, dz) >= 100 and _angdiff(face, want) <= 4 for _b, dx, dz, face, want in rows)
    g.check(ok, "C6: the angle convention on the engine's own walk -- for each d-pad direction the player's facing "
            "byte == the byte its world displacement implies under '0 south, 64 west, 128 north, 192 east'",
            str(rows))

    every = g.exceptions_since(mark)
    ours = [e for e in every if e.name in THROWS and any(k in fr for fr in e.trace for k in ("EventEngine", "EBin"))]
    print(f"[sine-rung0] exceptions since the mark: {len(every)}")
    g.check(not ours, "NC-THROW: no NullReference / InvalidCast / IndexOutOfRange through the event engine or the "
            "evaluator", str([(e.name, e.where) for e in ours[:5]]))
    g.quit()
