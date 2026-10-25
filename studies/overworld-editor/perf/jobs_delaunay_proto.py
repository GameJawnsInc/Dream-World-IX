"""Lane jobs: PROTOTYPE (monkeypatch here; the package is not edited) of world.island._delaunay, the Bowyer-Watson the
island mint runs inside every river composition (~8.5 s of a ~27 s river Check, jobs_river_split.py).

The original, per inserted point, scans EVERY live triangle with a Python incirc(). The patch keeps the original's
exact sequence of set operations -- the same triangles removed, the same new triangles added in the same order -- so
the returned list (the set's iteration order, which the mint's bytes follow) is the same; only the predicate is
vectorised: each live triangle's corners sit in numpy arrays, incirc is the same expression evaluated elementwise in
float64 (same operands, same operation order, no fused ops), and the "bad" list is then read off the set in its own
iteration order (a membership test per triangle instead of the arithmetic).

    py jobs_delaunay_proto.py capture       # record every _delaunay input of a river Check + an island Check
    py jobs_delaunay_proto.py bench [reps]  # each captured input: original vs patched, output list == (order too)
    py jobs_delaunay_proto.py e2e <verb>    # fresh children: the verb's Check verdict, unpatched vs patched, ==
"""
import contextlib
import io
import json
import pickle
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402

CAP = J.OUT / "delaunay_inputs.pkl"


def fast_delaunay(pts):
    import numpy as np
    minx = min(p[0] for p in pts)
    maxx = max(p[0] for p in pts)
    minz = min(p[1] for p in pts)
    maxz = max(p[1] for p in pts)
    d = max(maxx - minx, maxz - minz) * 10 + 10
    mx = (minx + maxx) / 2
    mz = (minz + maxz) / 2
    P_ = list(pts) + [(mx - 2 * d, mz - d), (mx, mz + 2 * d), (mx + 2 * d, mz - d)]
    n = len(pts)
    PX = np.array([float(p[0]) for p in P_], dtype=np.float64)
    PZ = np.array([float(p[1]) for p in P_], dtype=np.float64)
    cap = 64
    TA = np.zeros(cap, dtype=np.int64)
    TB = np.zeros(cap, dtype=np.int64)
    TC = np.zeros(cap, dtype=np.int64)
    alive = np.zeros(cap, dtype=bool)
    ids = {}
    tri_of = []
    count = 0

    def add(t):
        nonlocal cap, TA, TB, TC, alive, count
        if count == cap:
            cap *= 2
            TA, TB, TC = (np.resize(a, cap) for a in (TA, TB, TC))
            alive = np.concatenate([alive, np.zeros(cap - len(alive), dtype=bool)])
        TA[count], TB[count], TC[count] = t
        alive[count] = True
        ids[t] = count
        tri_of.append(t)
        count += 1

    tris = {(n, n + 1, n + 2)}
    add((n, n + 1, n + 2))
    for i in range(n):
        live = np.flatnonzero(alive[:count])
        a, b, c = TA[live], TB[live], TC[live]
        px, pz = PX[i], PZ[i]
        ax = PX[a] - px
        az = PZ[a] - pz
        bx = PX[b] - px
        bz = PZ[b] - pz
        cx = PX[c] - px
        cz = PZ[c] - pz
        det = ((ax*ax+az*az)*(bx*cz-cx*bz) - (bx*bx+bz*bz)*(ax*cz-cx*az) + (cx*cx+cz*cz)*(ax*bz-bx*az))
        o = (bx - ax) * (cz - az) - (bz - az) * (cx - ax)
        hit = np.where(o > 0, det > 0, det < 0)
        badset = {tri_of[k] for k in live[hit].tolist()}
        bad = [t for t in tris if t in badset]           # the original's order: the set's own iteration order
        ec = {}
        for t in bad:
            for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                k = (min(e), max(e))
                ec[k] = ec.get(k, 0) + 1
        tris -= set(bad)
        for t in bad:
            alive[ids.pop(t)] = False
        for (ea, eb), cnt in ec.items():
            if cnt == 1:
                t = (ea, eb, i)
                if t not in tris:
                    tris.add(t)
                    if t in ids:                          # (a triangle re-made after it was dropped: revive)
                        alive[ids[t]] = True
                    else:
                        add(t)
                else:
                    tris.add(t)
    return [t for t in tris if all(v < n for v in t)]


def capture():
    from ff9mapkit import cli
    from ff9mapkit.world import island as IS
    od = IS._delaunay
    got = []

    def rec(pts):
        out = od(pts)
        got.append({"pts": [tuple(p) for p in pts], "out": out})
        return out
    IS._delaunay = rec
    d = J.draft()
    for verb in ("river", "island"):
        n0 = len(got)
        rep = Path(tempfile.mkdtemp(prefix="jobs_dc_")) / "verdict.json"
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                cli.main(J.check_argv(verb, d, rep)[3:])
            except SystemExit:
                pass
        print(f"{verb}: {len(got) - n0} _delaunay calls, sizes {[len(g['pts']) for g in got[n0:]]}")
    CAP.write_bytes(pickle.dumps(got))


def bench(reps):
    from ff9mapkit.world import island as IS
    got = pickle.loads(CAP.read_bytes())
    res = []
    for g in got:
        pts = g["pts"]
        to, tp = [], []
        for r in range(reps):
            for arm in (("o", "p") if r % 2 == 0 else ("p", "o")):
                t = time.perf_counter()
                out = (IS._delaunay if arm == "o" else fast_delaunay)(pts)
                (to if arm == "o" else tp).append(time.perf_counter() - t)
                if arm == "p":
                    assert out == g["out"], "patched output differs (order included)"
                else:
                    assert out == g["out"], "original is not deterministic"
        res.append({"n": len(pts), "orig_min": min(to), "orig_med": statistics.median(to),
                    "fast_min": min(tp), "fast_med": statistics.median(tp), "identical": True})
        print(f"n={len(pts):5d}: original min {min(to):.3f}s med {statistics.median(to):.3f}s | patched min "
              f"{min(tp):.3f}s med {statistics.median(tp):.3f}s | output list identical (order included)", flush=True)
    (J.OUT / "delaunay_bench.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


def e2e_child(verb, out, patched):
    from ff9mapkit import cli
    from ff9mapkit.world import island as IS
    if patched:
        IS._delaunay = fast_delaunay
    d = J.draft()
    rep = Path(tempfile.mkdtemp(prefix="jobs_de_")) / "verdict.json"
    t = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            cli.main(J.check_argv(verb, d, rep)[3:])
        except SystemExit:
            pass
    Path(out).write_text(json.dumps({"s": time.perf_counter() - t,
                                     "verdict": json.loads(rep.read_text(encoding="utf-8"))}), encoding="utf-8")


def e2e(verb, n):
    from jobs_wall import job_env
    arms = {"unpatched": [], "patched": []}
    vs = {"unpatched": set(), "patched": set()}
    for i in range(n):
        for arm in (("unpatched", "patched") if i % 2 == 0 else ("patched", "unpatched")):
            out = Path(tempfile.mkdtemp(prefix="jobs_dex_")) / "r.json"
            subprocess.run([sys.executable, __file__, "e2e-child", verb, str(out), "1" if arm == "patched" else "0"],
                           cwd=str(J.kit_cwd()), env=job_env(), check=True)
            r = json.loads(out.read_text(encoding="utf-8"))
            arms[arm].append(r["s"])
            vs[arm].add(json.dumps(r["verdict"], sort_keys=True))
            print(f"{verb} {arm:9s} cli.main {r['s']:.2f}", flush=True)
    rec = {"verb": verb, **{a: {"min": min(x), "median": statistics.median(x), "runs": x} for a, x in arms.items()},
           "verdicts_identical": vs["unpatched"] == vs["patched"] and len(vs["unpatched"]) == 1}
    print(json.dumps(rec))
    p = J.OUT / "delaunay_e2e.json"
    allr = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    allr[verb] = rec
    p.write_text(json.dumps(allr, indent=1), encoding="utf-8")


if __name__ == "__main__":
    m = sys.argv[1]
    if m == "capture":
        capture()
    elif m == "bench":
        bench(int(sys.argv[2]) if len(sys.argv) > 2 else 3)
    elif m == "e2e":
        e2e(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3)
    elif m == "e2e-child":
        e2e_child(sys.argv[2], sys.argv[3], sys.argv[4] == "1")
