"""PREDICT the ground-query workload of cost_session.py's circle walk on each refinement arm -- offline, over the
EXACT arm meshes cost_build.py wrote, with the engine's query and cache rules. Registers the numbers before any run.

The engine work per WORLD TICK (WorldTPS 28 on this install; w_frameMainRoutine -> w_movementUpdate + w_cameraUpdate,
ff9.cs:3809-3813, run MainLoopUpdateCount times a frame, WMScriptDirector.cs:299-304, FPSManager.cs:77-111):
  * the controlled walker, on foot: w_movementControl (ff9.cs:5547-5603) probes the step target with
    w_movementRoundCheck (:5682-5698) on its 10-slot cache ring, then probes the 3D-normalised step -- on flat ground
    the same point -- on the same ring: 2 cached probes a tick;
  * the camera eye: w_cameraSetEyeAim (:2935-2988) on foot is FUZZY (:5979, flg_fly false) -> 4 sky probes at
    eye +-5.5u in x and z, each on its own ring w_cameraHit[0..3], with IgnoreExceptions (no filters);
  * a parked non-player actor (not exercised: see cost_PLAN.md) re-grounds with cache = null EVERY tick (:5191-5199).
A probe = WMBlock.Raycast (WMBlock.cs:137-183): walk the ring from the newest slot (cache.Number + i) % 10, each
non-empty slot ONE triangle test (RaycastOnSpecifiedTriangle: 3x TransformPoint + intersect, WMPhysics.cs:50-69);
on a hit stop; else a FULL SCAN of the block's walk meshes in registration order (Terrain is the first on this cell)
in buffer order, each iterated tri the same 3x TransformPoint + intersect (all tris up-facing, so the cheap filters,
WMPhysics.cs:15-29, never skip one), the first containing tri wins, and it is written to slot (Number+1) % 10.
So cost = TRIANGLE TESTS, one unit each. ms = tests x c, c (seconds per test in Unity 5.2.3 Mono) UNKNOWN: bracketed.

The walk (cost_session.py): "up" + L1 held together. L1 turns the camera PsxRot(32) = 2.8125 deg a tick
(ff9.cs:6137-6141) and "up" walks rotation + stick (:6166), so he walks a CIRCLE of radius v / omega = 0.4375 /
0.049087 = 8.913u, centred on the cell centre C. The eye trails him by the camera distance D (ff9.cs:2688-2689;
posstat 0 = 5000/256 = 19.53u, up to 7000/256 = 27.34u -- bracketed), so the four camera probes ride a circle of
radius sqrt(r^2 + D^2) +- 5.5u: they all stay inside the 64u cell when C is its centre (checked below).

Calibrations (asserted): the vectorised first-hit locator agrees with a brute-force loop at x1 and x16; a stationary
probe costs exactly ONE test once its ring is warm (the idle control's premise).

Writes out/cost_predict.json; prints the registered table.
Rerun:  py studies/terrain-malleability/ingame/cost_predict.py     (after cost_build.py)
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "gap_area_layer"))
import arealib as A                                                # noqa: E402

SCRATCH = Path(os.environ.get("COST_SCRATCH", r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX"
                                              r"\8b61f6d3-b0c2-4ade-9f22-b2bc267b1c8d\scratchpad\cost"))
ARMS_DIR = SCRATCH / "arms"
OUT = HERE / "out"

STEP = 0.4375                         # on-foot step a tick (README 7 / RESULTS 2: 2.34375 rise per 0.4375u tick)
OMEGA = math.radians(2.8125)          # PsxRot(32) a tick, ff9.cs:6140
RADIUS = STEP / OMEGA                 # 8.913u
FUZZ = 5.5                            # ff9.cs:2948
C_LOCAL = (32.37, -32.61)             # the circle centre, block-local (world 1376.37, -96.61): off-lattice
TPS = 28.0                            # Memoria.ini [Graphics] WorldTPS = 28
D_SET = (19.53, 23.44, 27.34)         # camera distance: posstat 0 / 1 / 3 (5000, 6000, 7000 / 256)
WARM, TICKS, IDLE = 128, 600, 60
C_SET_US = (0.1, 0.25, 0.5, 1.0)      # seconds per tri test, bracketed (Mono icall TransformPoint x3 + managed math)


class Locator:
    """First containing triangle in BUFFER ORDER for plan points (block-local) -- the full scan's depth."""

    def __init__(self, V):
        self.V = V
        a, b, c = V[:, 0], V[:, 1], V[:, 2]
        self.a, self.b, self.c = a, b, c
        self.d = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])

    def _inside(self, ti, x, z):
        a, b, c, d = self.a[ti], self.b[ti], self.c[ti], self.d[ti]
        w0 = ((b[..., 2] - c[..., 2]) * (x - c[..., 0]) + (c[..., 0] - b[..., 0]) * (z - c[..., 2])) / d
        w1 = ((c[..., 2] - a[..., 2]) * (x - c[..., 0]) + (a[..., 0] - c[..., 0]) * (z - c[..., 2])) / d
        return (w0 >= -1e-7) & (w1 >= -1e-7) & (1 - w0 - w1 >= -1e-7)

    def first(self, pts, chunk=128):
        """[N] index of the first containing tri, len(V) when none (a full miss scans everything)."""
        n = len(self.V)
        out = np.full(len(pts), n, np.int64)
        idx = np.arange(n)
        for s in range(0, len(pts), chunk):
            p = pts[s:s + chunk]
            ins = self._inside(idx[:, None], p[None, :, 0], p[None, :, 1])
            hit = ins.any(axis=0)
            out[s:s + chunk] = np.where(hit, ins.argmax(axis=0), n)
        return out

    def contains(self, t, p):
        return bool(self._inside(np.array([t]), np.array([p[0]]), np.array([p[1]]))[0])


class Ring:
    """The 10-slot s_moveCHRCache semantics of WMBlock.Raycast (WMBlock.cs:145-179)."""

    def __init__(self):
        self.slot = [-1] * 10
        self.number = 0

    def probe(self, loc: Locator, p, depth: int) -> tuple[int, bool]:
        tests = 0
        for i in range(10):
            s = (self.number + i) % 10
            t = self.slot[s]
            if t < 0:
                continue
            tests += 1
            if loc.contains(t, p):
                return tests, True
        tests += min(depth + 1, len(loc.V))
        if depth < len(loc.V):
            self.number = (self.number + 1) % 10
            self.slot[self.number] = depth
        return tests, False


def u(h):
    return np.array([math.cos(h), math.sin(h)])


def workload(loc: Locator, D: float, h0: float = 0.3, sign: int = +1) -> dict:
    """Walk WARM + TICKS ticks of the circle; score only the last TICKS. Then IDLE stationary ticks."""
    C = np.array(C_LOCAL)
    P = C - RADIUS * u(h0 + sign * math.pi / 2)
    walker = Ring()
    cams = [Ring() for _ in range(4)]
    offs = [np.array(o) for o in ((FUZZ, 0.0), (-FUZZ, 0.0), (0.0, FUZZ), (0.0, -FUZZ))]
    path_w, path_c, heads = [], [], []
    for t in range(WARM + TICKS):
        h = h0 + sign * OMEGA * (t + 1)
        P = P + STEP * u(h)
        E = P - (D - 0.25) * u(h)                    # eye behind him, + dirVector/4 (normalised, :2940-2942)
        path_w.append(P.copy())
        path_c.append([E + o for o in offs])
        heads.append(h)
    pw = np.array(path_w)
    pc = np.array(path_c).reshape(-1, 2)
    dw = loc.first(pw)
    dc = loc.first(pc).reshape(-1, 4)
    w_tests, c_tests, w_scans, c_scans, per_tick = 0, 0, 0, 0, []
    for t in range(WARM + TICKS):
        tw = tc = 0
        for _ in range(2):                           # probe 1 + the normalised re-probe of the same point
            k, hit = walker.probe(loc, pw[t], int(dw[t]))
            tw += k
            if t >= WARM and not hit:
                w_scans += 1
        for j in range(4):
            k, hit = cams[j].probe(loc, pc[t * 4 + j], int(dc[t, j]))
            tc += k
            if t >= WARM and not hit:
                c_scans += 1
        if t >= WARM:
            w_tests += tw
            c_tests += tc
            per_tick.append(tw + tc)
    idle = []
    for _ in range(IDLE):                            # stationary: same points every tick
        tw = sum(walker.probe(loc, pw[-1], int(dw[-1]))[0] for _ in range(2))
        tc = sum(cams[j].probe(loc, pc[-4 + j], int(dc[-1, j]))[0] for j in range(4))
        idle.append(tw + tc)
    inside = lambda q: (q[:, 0] > 0) & (q[:, 0] < 64) & (q[:, 1] < 0) & (q[:, 1] > -64)   # noqa: E731
    pt = np.array(per_tick)
    return {"D": D, "tests_per_tick": round(float(pt.mean()), 1), "walker_per_tick": round(w_tests / TICKS, 1),
            "camera_per_tick": round(c_tests / TICKS, 1), "p95_per_tick": float(np.percentile(pt, 95)),
            "max_per_tick": int(pt.max()), "walker_scan_rate": round(w_scans / (2 * TICKS), 3),
            "camera_scan_rate": round(c_scans / (4 * TICKS), 3),
            "mean_scan_depth_frac": round(float(np.concatenate([dw[WARM:], dc[WARM:].ravel()]).mean() / len(loc.V)), 3),
            "idle_per_tick": round(float(np.mean(idle[-30:])), 2),
            "walker_inside_cell": bool(inside(pw).all()), "camera_inside_cell_frac": round(float(inside(pc).mean()), 4),
            "walker_radius_fit": round(float(np.linalg.norm(pw - np.array(C_LOCAL), axis=1).mean()), 3)}


def workload_straight(loc: Locator, D: float) -> dict:
    """The TRANSLATION to ordinary play: a straight walk east along the cell's middle row (camera trailing at D, so
    its probes move at the walker's 0.4375u a tick, not the circle's ~1.05u), 40 ticks of warm-up then up to TICKS --
    the walker turns round at the far side (teleported back to the start, rings kept warm)."""
    walker, cams = Ring(), [Ring() for _ in range(4)]
    offs = [np.array(o) for o in ((FUZZ, 0.0), (-FUZZ, 0.0), (0.0, FUZZ), (0.0, -FUZZ))]
    x0, x1, z = D + FUZZ + 1.0, 63.0, C_LOCAL[1]
    pw, pc = [], []
    x = x0
    for _ in range(40 + TICKS):
        x = x + STEP if x + STEP < x1 else x0
        pw.append(np.array([x, z]))
        pc.append([np.array([x - (D - 0.25), z]) + o for o in offs])
    pw = np.array(pw)
    pc = np.array(pc).reshape(-1, 2)
    dw, dc = loc.first(pw), loc.first(pc).reshape(-1, 4)
    tot = []
    for t in range(40 + TICKS):
        n = sum(walker.probe(loc, pw[t], int(dw[t]))[0] for _ in range(2))
        n += sum(cams[j].probe(loc, pc[t * 4 + j], int(dc[t, j]))[0] for j in range(4))
        if t >= 40:
            tot.append(n)
    return {"D": D, "tests_per_tick": round(float(np.mean(tot)), 1)}


def calibrate(loc: Locator, rng) -> None:
    pts = rng.uniform([0.5, -63.5], [63.5, -0.5], size=(12, 2))
    fast = loc.first(pts)
    for k, p in enumerate(pts):
        brute = next((t for t in range(len(loc.V)) if loc.contains(t, p)), len(loc.V))
        assert brute == fast[k], f"locator disagrees with brute force at {p}: {fast[k]} vs {brute}"
    r = Ring()
    p = pts[0]
    r.probe(loc, p, int(fast[0]))
    assert r.probe(loc, p, int(fast[0])) == (1, True), "a warm stationary probe must cost exactly one test"


def main() -> int:
    man = json.loads((ARMS_DIR / "cost_manifest.json").read_text(encoding="utf-8"))
    rng = np.random.default_rng(10)
    res = {"model": {"step": STEP, "omega_deg": 2.8125, "radius": round(RADIUS, 3), "fuzz": FUZZ, "centre_local": C_LOCAL,
                     "tps": TPS, "warm_ticks": WARM, "ticks": TICKS, "c_us": C_SET_US}, "arms": {}}
    for arm in ("1", "4", "16", "64"):
        V, _ids = A.read_ff9mesh_arrays(ARMS_DIR / man["arms"][arm]["file"])
        loc = Locator(V)
        if arm in ("1", "16"):
            calibrate(loc, rng)
        rows = [workload(loc, D) for D in D_SET]
        rows_cw = workload(loc, D_SET[0], sign=-1)                 # the other turn sense: must agree
        npc = int(loc.first(np.array([C_LOCAL]))[0]) + 1          # a parked actor at C: a full scan every tick
        straight = workload_straight(loc, D_SET[1])
        res["arms"][arm] = {"tris": len(V), "by_D": rows, "cw_check": rows_cw, "parked_actor_tests_per_tick": npc,
                            "straight_walk": straight}
        mid = rows[1]
        print(f"x{arm:<2} {len(V):>6} tris | tests/tick {mid['tests_per_tick']:>8} (walker {mid['walker_per_tick']}, "
              f"camera {mid['camera_per_tick']}; D 19.5..27.3: {rows[0]['tests_per_tick']}..{rows[2]['tests_per_tick']}; "
              f"other turn sense {rows_cw['tests_per_tick']}) | scan rate w {mid['walker_scan_rate']} "
              f"c {mid['camera_scan_rate']} | idle {mid['idle_per_tick']} | straight walk {straight['tests_per_tick']} "
              f"| parked actor {npc}/tick | cam probes inside cell {mid['camera_inside_cell_frac']}")
    base = res["arms"]["1"]["by_D"][1]["tests_per_tick"]
    print("\nregistered cost table (D = 23.44u; ms per tick = tests x c; tick frames carry it):")
    print(f"{'arm':>4} {'x stock':>8} " + " ".join(f"{'c=' + str(c) + 'us':>12}" for c in C_SET_US) + "   ms/s @28 TPS (c=0.25)  @112 (ts 4)")
    for arm, row in res["arms"].items():
        t = row["by_D"][1]["tests_per_tick"]
        row["x_vs_x1"] = round(t / base, 1)
        row["ms_per_tick"] = {str(c): round(t * c / 1000.0, 3) for c in C_SET_US}
        print(f"x{arm:>3} {row['x_vs_x1']:>8} " + " ".join(f"{t * c / 1000.0:>12.3f}" for c in C_SET_US)
              + f"   {t * 0.25e-3 * TPS:>10.1f}            {t * 0.25e-3 * TPS * 4:>8.1f}")
    OUT.mkdir(exist_ok=True)
    (OUT / "cost_predict.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT / 'cost_predict.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
