"""SKEPTIC check for lane jobs, candidate D1 (island._delaunay vectorised; the lane's prototype is
jobs_delaunay_proto.fast_delaunay, imported here unchanged).

Beyond the lane's 6 captured inputs (re-run here once each), STRESS inputs the lane did not try, where a different
float evaluation or a different set history would show up first:
  * integer-valued grids (many exactly-cocircular quadruples: det == 0.0 exactly, the tie the predicate decides),
  * the same grid scaled by 1/3 (non-representable steps: ties broken by rounding),
  * random uniform points over a real input's extent, with a duplicate point and collinear runs mixed in,
  * a real input with every point jittered by 1e-9.
Each: the original's output list == the prototype's, ORDER INCLUDED. Timing: n=1718 captured input, alternating, 3 reps.

    py studies/overworld-editor/perf/verify_jobs_delaunay.py     -> out/perf/jobs/verify/delaunay.json
"""
import json
import pickle
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402
import jobs_delaunay_proto as DP  # noqa: E402
from ff9mapkit.world import island as IS  # noqa: E402

VOUT = J.OUT / "verify"
VOUT.mkdir(parents=True, exist_ok=True)


def cases():
    got = pickle.loads((J.OUT / "delaunay_inputs.pkl").read_bytes())
    for k, g in enumerate(got):
        yield f"captured{k}_n{len(g['pts'])}", g["pts"]
    for m in (8, 15, 24):
        grid = [(float(i), float(j)) for i in range(m) for j in range(m)]
        yield f"intgrid{m}", grid
        yield f"thirdgrid{m}", [(x / 3.0, z / 3.0) for x, z in grid]
        rng = random.Random(m)
        sh = grid[:]
        rng.shuffle(sh)
        yield f"intgrid{m}_shuffled", sh
    real = got[0]["pts"]
    xs, zs = [p[0] for p in real], [p[1] for p in real]
    for seed in (1, 2, 3):
        rng = random.Random(seed)
        pts = [(rng.uniform(min(xs), max(xs)), rng.uniform(min(zs), max(zs))) for _ in range(600)]
        pts += [(min(xs) + 3.0 * t, min(zs) + 2.0 * t) for t in range(12)]      # a collinear run
        yield f"random{seed}_n{len(pts)}", pts
    rng = random.Random(9)
    yield "captured0_jitter1e-9", [(x + rng.uniform(-1e-9, 1e-9), z + rng.uniform(-1e-9, 1e-9)) for x, z in real]


def main():
    res = {"cases": []}
    for name, pts in cases():
        try:
            o = IS._delaunay(pts)
            oerr = None
        except Exception as e:                           # noqa: BLE001
            o, oerr = None, repr(e)
        try:
            p = DP.fast_delaunay(pts)
            perr = None
        except Exception as e:                           # noqa: BLE001
            p, perr = None, repr(e)
        same = (oerr is None and perr is None and o == p) or (oerr is not None and perr is not None)
        rec = {"case": name, "n": len(pts), "identical_order_included": same, "same_set": (o is not None and p is
               not None and set(o) == set(p)), "orig_err": oerr, "proto_err": perr,
               "ntris": None if o is None else len(o)}
        print(json.dumps(rec), flush=True)
        res["cases"].append(rec)
    big = pickle.loads((J.OUT / "delaunay_inputs.pkl").read_bytes())[0]["pts"]
    to, tp = [], []
    for r in range(3):
        for arm in (("o", "p") if r % 2 == 0 else ("p", "o")):
            t = time.perf_counter()
            (IS._delaunay if arm == "o" else DP.fast_delaunay)(big)
            (to if arm == "o" else tp).append(time.perf_counter() - t)
    res["timing_n1718"] = {"orig_min": min(to), "orig_med": statistics.median(to), "proto_min": min(tp),
                           "proto_med": statistics.median(tp)}
    res["all_identical"] = all(c["identical_order_included"] for c in res["cases"])
    print(json.dumps({k: v for k, v in res.items() if k != "cases"}))
    (VOUT / "delaunay.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
