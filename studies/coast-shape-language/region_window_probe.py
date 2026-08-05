"""Find a cliff-base run that CROSSES an interior border of a donor rect.

The point of region-capable morphs is a window no single-cell call can express. This
locates one: it extracts the topo-58 base outline over the whole rect exactly the way
:class:`coastmorph.CliffWindow` does, chains it, and reports the runs that cross an
interior border and/or exceed 64u -- neither of which a single-cell window can hold.

  py studies/coast-shape-language/region_window_probe.py [--donor 6,6] [--size 2x2]
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import transplant as TR                 # noqa: E402
from ff9mapkit.world.coastmorph import _pk, BASE_Y_MAX       # noqa: E402
from ff9mapkit.world.extract import decode_id                # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--donor", default="6,6")
    ap.add_argument("--size", default="2x2")
    ap.add_argument("--disc", type=int, default=1)
    args = ap.parse_args()
    dbx, dby = (int(v) for v in args.donor.split(","))
    nx, ny = (int(v) for v in args.size.lower().split("x"))

    terr = []
    for cy in range(dby, dby + ny):
        for cx in range(dbx, dbx + nx):
            terr += TR.world_tris(cx, cy, "terrain", disc=args.disc)
    topo = lambda t3: decode_id(int(round(t3[0][3][0])))["topograph"]      # noqa: E731
    cliff = [t for t in terr if topo(t) == 58]
    print(f"rect ({dbx},{dby})+{nx}x{ny}: {len(terr)} terrain tris, "
          f"{len(cliff)} topo-58 cliff tris")
    if not cliff:
        print("   no cliff band here")
        return 0

    cnt = defaultdict(int)
    for t3 in cliff:
        ps = [v[0] for v in t3]
        for i in range(3):
            cnt[frozenset((_pk(ps[i]), _pk(ps[(i + 1) % 3])))] += 1
    land_edges = set()
    for t3 in terr:
        if topo(t3) == 58:
            continue
        ps = [v[0] for v in t3]
        for i in range(3):
            land_edges.add(frozenset((_pk(ps[i]), _pk(ps[(i + 1) % 3]))))

    x0, x1 = 64.0 * dbx, 64.0 * (dbx + nx)
    z0, z1 = -64.0 * (dby + ny), -64.0 * dby

    def on_frame(a, b, eps=0.02):
        for ax, lo, hi in ((0, x0, x1), (2, z0, z1)):
            for plane in (lo, hi):
                if abs(a[ax] - plane) < eps and abs(b[ax] - plane) < eps:
                    return True
        return False

    base = [e for e, c in cnt.items()
            if c == 1 and e not in land_edges and not on_frame(*tuple(e))
            and max(a[1] for a in e) < BASE_Y_MAX]
    print(f"   {len(base)} base edges (REGION frame)")

    adj = defaultdict(list)
    for e in base:
        a, b = tuple(e)
        adj[a].append(b)
        adj[b].append(a)
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

    seen, runs = set(), []
    for s in list(adj):                          # open runs first (degree-1 ends)
        if s not in seen and len(adj[s]) == 1:
            r = walk(s)
            if len(r) > 2:
                runs.append(r)
    # THEN the closed loops. An island's cliff base is a CLOSED ring -- it has no
    # degree-1 endpoint, so an endpoint-seeded walk misses it entirely. The first pass of
    # this probe reported only two short frame crumbs and none of the actual island.
    for s in list(adj):
        if s not in seen:
            r = walk(s)
            if len(r) > 2:
                runs.append(r)
    runs.sort(key=len, reverse=True)

    # interior border planes of this rect
    xs = [64.0 * (dbx + i) for i in range(1, nx)]
    zs = [-64.0 * (dby + i) for i in range(1, ny)]
    print(f"   interior borders: x={xs} z={zs}")
    print(f"   {len(runs)} base run(s):")
    for i, r in enumerate(runs[:8]):
        L = sum(math.dist(r[j][:3], r[j + 1][:3]) for j in range(len(r) - 1))
        cross = []
        for j in range(len(r) - 1):
            a, b = r[j], r[j + 1]
            for p in xs:
                if (a[0] - p) * (b[0] - p) < 0 or abs(a[0] - p) < .02:
                    cross.append(f"x={p:.0f}")
            for p in zs:
                if (a[2] - p) * (b[2] - p) < 0 or abs(a[2] - p) < .02:
                    cross.append(f"z={p:.0f}")
        tag = []
        if cross:
            tag.append("CROSSES " + ",".join(sorted(set(cross))))
        if L > 64.0:
            tag.append(f"LONGER THAN ONE CELL ({L:.1f}u)")
        print(f"      run {i}: {len(r):>3} verts  {L:7.1f}u  "
              f"({r[0][0]:.3f},{r[0][2]:.3f}) -> ({r[-1][0]:.3f},{r[-1][2]:.3f})"
              + ("  << " + " + ".join(tag) if tag else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
