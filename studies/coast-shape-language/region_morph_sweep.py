"""Which BORDER-CROSSING morphs actually build? (predictions R-3 / R-4)

A region window that no single cell can express is only a capability if a morph on it
survives every law gate. This sweeps the cliff verbs over every base run of a donor rect,
at every window that crosses an interior border, and reports what builds and -- as
importantly -- the BINDING refusal for what does not.

  py studies/coast-shape-language/region_morph_sweep.py [--donor 7,17] [--size 4x2]
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import transplant as TR                 # noqa: E402
from ff9mapkit.world import coastmorph as CM                 # noqa: E402
from ff9mapkit.world.coastmorph import _pk, BASE_Y_MAX       # noqa: E402
from ff9mapkit.world.extract import decode_id                # noqa: E402


def base_runs(dbx, dby, nx, ny, disc=1):
    terr = []
    for cy in range(dby, dby + ny):
        for cx in range(dbx, dbx + nx):
            terr += TR.world_tris(cx, cy, "terrain", disc=disc)
    topo = lambda t3: decode_id(int(round(t3[0][3][0])))["topograph"]      # noqa: E731
    cnt, land = defaultdict(int), set()
    for t3 in terr:
        ps = [v[0] for v in t3]
        for i in range(3):
            e = frozenset((_pk(ps[i]), _pk(ps[(i + 1) % 3])))
            if topo(t3) == 58:
                cnt[e] += 1
            else:
                land.add(e)
    x0, x1 = 64.0 * dbx, 64.0 * (dbx + nx)
    z0, z1 = -64.0 * (dby + ny), -64.0 * dby

    def onf(a, b, eps=0.02):
        for ax, lo, hi in ((0, x0, x1), (2, z0, z1)):
            for pl in (lo, hi):
                if abs(a[ax] - pl) < eps and abs(b[ax] - pl) < eps:
                    return True
        return False

    base = [e for e, c in cnt.items()
            if c == 1 and e not in land and not onf(*tuple(e))
            and max(a[1] for a in e) < BASE_Y_MAX]
    adj = defaultdict(list)
    for e in base:
        a, b = tuple(e)
        adj[a].append(b)
        adj[b].append(a)
    seen, runs = set(), []

    def walk(s):
        run, cur, prev = [s], s, None
        seen.add(s)
        while True:
            nxt = [q for q in adj[cur] if q != prev]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            if cur in seen:
                break
            seen.add(cur)
            run.append(cur)
        return run

    for s in list(adj):
        if s not in seen and len(adj[s]) == 1:
            r = walk(s)
            if len(r) > 2:
                runs.append(r)
    for s in list(adj):                              # closed rings have no endpoint
        if s not in seen:
            r = walk(s)
            if len(r) > 2:
                runs.append(r)
    return sorted(runs, key=len, reverse=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--donor", default="7,17")
    ap.add_argument("--size", default="4x2")
    ap.add_argument("--disc", type=int, default=1)
    args = ap.parse_args()
    dbx, dby = (int(v) for v in args.donor.split(","))
    nx, ny = (int(v) for v in args.size.lower().split("x"))
    size = (nx, ny)

    runs = base_runs(dbx, dby, nx, ny, args.disc)
    print(f"rect ({dbx},{dby})+{nx}x{ny}: {len(runs)} base run(s)")

    built, refusals = [], Counter()
    for ri, run in enumerate(runs):
        cx = [int(v[0] // 64) for v in run]
        cz = [int((-v[2]) // 64) for v in run]
        changes = [k for k in range(len(run) - 1)
                   if cx[k] != cx[k + 1] or cz[k] != cz[k + 1]]
        for i in changes:
            for span in (2, 3, 4, 5, 6, 8, 10):
                lo, hi = max(0, i - span), min(len(run) - 1, i + span)
                if (cx[lo], cz[lo]) == (cx[hi], cz[hi]):
                    continue                       # not actually border-crossing
                A = (run[lo][0], run[lo][2])
                B = (run[hi][0], run[hi][2])
                L = sum(math.dist(run[j][:3], run[j + 1][:3]) for j in range(lo, hi))
                gaps = hi - lo
                trials = [("cliff_bump", CM.cliff_bump, d) for d in (2.5, 2.0, 1.5, 1.0)]
                if gaps % 4 == 0:
                    trials += [("cliff_headland", CM.cliff_headland, d)
                               for d in (8.0, 6.0, 4.0, 3.0)]
                    trials += [("cliff_bay", CM.cliff_bay, d) for d in (6.0, 4.0, 3.0)]
                for name, fn, d in trials:
                    try:
                        tw = fn((dbx, dby), A, B, d, size=size, disc=args.disc)
                        built.append((name, d, A, B, gaps, L, (cx[lo], cz[lo]),
                                      (cx[hi], cz[hi]), tw))
                    except Exception as e:                     # noqa: BLE001
                        refusals[str(e).split(" -- ")[0][:72]] += 1

    print(f"\nBUILT: {len(built)} border-crossing morph(s)")
    seen_win = set()
    for name, d, A, B, gaps, L, ca, cb, tw in built:
        key = (A, B)
        if key in seen_win:
            continue
        seen_win.add(key)
        print(f"   {name} depth {d}: ({A[0]:.3f},{A[1]:.3f}) -> ({B[0]:.3f},{B[1]:.3f})")
        print(f"      gaps={gaps} L={L:.1f}u  cell {ca} -> {cb}"
              + ("   << LONGER THAN ONE CELL" if L > 64.0 else ""))
        print("      " + "  ".join(f"{t.gate()['gate']}={t.gate()['applied']}"
                                   f"/{t.gate()['expected']} ok={t.gate()['ok']}"
                                   for t in tw))
        if len(seen_win) >= 6:
            break
    print(f"\nBINDING REFUSALS (top {min(8, len(refusals))} of {sum(refusals.values())}):")
    for msg, n in refusals.most_common(8):
        print(f"   x{n:<4} {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
