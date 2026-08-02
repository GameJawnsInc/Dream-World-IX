"""Measure THE V-SHORE GAP: deployed once-edges that hover above a surface below
(the floating-wall sightline class). For every once-edge of the live Terrain mesh,
sample its midpoint: if another up-facing surface lies below the edge by > 0.5u,
the edge is a HOVER edge -- the slit the owner photographs. Clusters + heights."""
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402


def main():
    world = W.load_world()
    hovers = []
    for bk, meshes in sorted(world.items()):
        for m in meshes:
            if m["name"] != "Terrain":
                continue
            ec = defaultdict(list)
            for ti, tri in enumerate(m["tris"]):
                vs = [tuple(round(v, 3) for v in p) for p in (tri[0], tri[1], tri[2])]
                for a, b in ((0, 1), (1, 2), (2, 0)):
                    ec[tuple(sorted((vs[a], vs[b])))].append(ti)
            for (va, vb), owners in ec.items():
                if len(owners) != 1:
                    continue
                mx, my, mz = ((va[0] + vb[0]) / 2, (va[1] + vb[1]) / 2,
                              (va[2] + vb[2]) / 2)
                # any surface below the edge midpoint? (all sheets, no topo filter
                # -- a sightline cares about render, not walkability)
                below = [s[0] for s in W.all_sheets(world, mx, mz)
                         if s[0] < my - 0.5]
                if below:
                    hovers.append((mx, mz, my, max(below),
                                   math.hypot(va[0] - vb[0], va[2] - vb[2])))
    print(f"{len(hovers)} hover once-edges (edge > 0.5 above a surface below)")
    # cluster by 8u cells
    cl = defaultdict(list)
    for h in hovers:
        cl[(int(h[0] // 8), int(h[1] // 8))].append(h)
    for key, hs in sorted(cl.items(), key=lambda kv: -len(kv[1]))[:15]:
        cx = sum(h[0] for h in hs) / len(hs)
        cz = sum(h[1] for h in hs) / len(hs)
        gap = max(h[2] - h[3] for h in hs)
        tot = sum(h[4] for h in hs)
        print(f"   ({cx:6.1f},{cz:7.1f}): {len(hs):3d} edges, {tot:5.1f}u total "
              f"length, max hover {gap:5.2f}u, edge y "
              f"{min(h[2] for h in hs):.2f}-{max(h[2] for h in hs):.2f}")


if __name__ == "__main__":
    main()
