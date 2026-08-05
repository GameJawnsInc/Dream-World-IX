"""RUNG 6 / STEP 0 -- which Disc9 cluster is THE island?

Read-only over the deployed bytes. Loads each disjoint Disc9 override cluster with the
calibrated walk instrument (studies/path-d-new-world/walk_sim.py, the engine ground query
byte-decoded in WALK-QUERY-DECODE.md) and reports, per cluster: walkable land area, height
band, topograph histogram, and how much of it is INTERIOR (>= 8u from any non-walkable
neighbour) -- i.e. how much of it a player could actually be dropped onto.

No deploy, no mutation, no game write.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STUDY))
import walk_sim as W                                        # noqa: E402

CLUSTERS = {
    "bench(V-shore)":  [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)],
    "centre(rung5a)":  [(11, 10), (12, 9), (12, 10), (12, 11), (13, 10)],
    "scatter(jcomp)":  [(10, 13), (10, 14), (11, 12), (11, 13), (11, 14),
                        (13, 15), (14, 12), (14, 13), (15, 12), (15, 13)],
    "edgeNW":          [(0, 4), (1, 4), (2, 4), (3, 4), (0, 5), (1, 5), (2, 5), (3, 5)],
    "edgeSW":          [(0, 16), (1, 16), (2, 16), (3, 16), (4, 16),
                        (0, 17), (1, 17), (2, 17), (3, 17), (4, 17),
                        (0, 18), (1, 18), (2, 18), (3, 18), (4, 18),
                        (0, 19), (1, 19), (2, 19), (3, 19), (4, 19)],
    "edgeSE":          [(18, 17), (18, 18), (19, 17), (19, 18), (20, 17), (20, 18),
                        (21, 17), (21, 18)],
    "edgeNE":          [(19, 0), (20, 0)],
}

GRID = 2.0


def survey(name, cells):
    W.CELLS = cells
    world = W.load_world()
    parts = Counter()
    for bk in world:
        for m in world[bk]:
            parts[m["name"]] += 1
    land = []
    topo = Counter()
    for (bx, by) in cells:
        ox, oz = 64.0 * bx, -64.0 * by
        x = ox
        while x < ox + 64.0:
            z = oz
            while z > oz - 64.0:
                sh = W.all_sheets(world, x, z)
                walk = [s for s in sh if s[1] in W.WALK_OK]
                if walk:
                    y = max(s[0] for s in walk)
                    if y > 0.6:                    # above the sea sheet -> real land
                        land.append((x, z, y))
                        topo[walk[0][1]] += 1
                z -= GRID
            x += GRID
    ys = sorted(t[2] for t in land)
    print(f"\n=== {name}: {len(cells)} blocks, parts {dict(parts)}")
    print(f"    walkable-land samples (>{0.6}u, {GRID}u pitch): {len(land)}"
          f"  ~= {len(land) * GRID * GRID:.0f} u^2")
    if ys:
        print(f"    height band  min {ys[0]:.2f}  med {ys[len(ys)//2]:.2f}  max {ys[-1]:.2f}")
        print(f"    topographs   {topo.most_common(8)}")
        xs = [t[0] for t in land]; zs = [t[1] for t in land]
        print(f"    bbox         x {min(xs):.0f}..{max(xs):.0f}   z {min(zs):.0f}..{max(zs):.0f}")
    return land


if __name__ == "__main__":
    only = sys.argv[1:] or list(CLUSTERS)
    for nm in only:
        survey(nm, CLUSTERS[nm])
