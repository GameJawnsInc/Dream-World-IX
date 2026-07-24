"""RUNG F seam diagnostic 2 -- for each residual once-edge, find the opposing vertex and diagnose
whether it is a missed-splittable T-junction (opposing vert strictly interior) or a genuine gap."""
from __future__ import annotations
import math, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg
from ff9mapkit.world import extract as X
import rung_f_layout as RFL

BLOCK = 64.0
CELL = 4.0


def main():
    gr = Path(_cfg.find_game_path(None))
    comp = RFL.compose(gr)
    final = comp["final_blocks"]
    placed = comp["placed_R"]

    gpos = []
    gtris = []
    for blk, bm in final.items():
        base = len(gpos)
        ox, oz = X.block_world_origin(blk[0], blk[1])
        for v in bm.verts:
            gpos.append((v[0] + ox, v[1], v[2] + oz))
        for tri in bm.tris:
            gtris.append((base + tri[0], base + tri[1], base + tri[2]))

    # all vertices (dedup by rounded pos)
    allv = set()
    for (x, y, z) in gpos:
        allv.add((round(x, 3), round(y, 3), round(z, 3)))
    allv = list(allv)
    # XZ spatial index of verts
    vidx = defaultdict(list)
    for v in allv:
        vidx[(math.floor(v[0] / CELL), math.floor(v[2] / CELL))].append(v)

    ecnt = Counter()
    for (i, j, k) in gtris:
        pts = [(round(gpos[v][0], 3), round(gpos[v][1], 3), round(gpos[v][2], 3)) for v in (i, j, k)]
        for q in range(3):
            if pts[q] == pts[(q + 1) % 3]:
                continue
            ecnt[tuple(sorted((pts[q], pts[(q + 1) % 3])))] += 1
    open_bad = [e for e, nn in ecnt.items() if nn == 1 and not (e[0][1] <= 1e-3 and e[1][1] <= 1e-3)]
    print(f"\nONCE-EDGES above skirt: {len(open_bad)}")

    # for each once-edge, look for a vertex (not an endpoint) that lies near its XZ span
    missed_tjunction = 0
    genuine_gap = 0
    tj_ydiffs = []
    gap_dists = []
    for (a, b) in open_bad:
        ax, az = a[0], a[2]; bx, bz = b[0], b[2]
        abx, abz = bx - ax, bz - az
        L2 = abx * abx + abz * abz
        # candidate verts near midpoint
        mx, mz = (ax + bx) / 2, (az + bz) / 2
        best_int = None  # (perp_dist, t, ydiff, vert)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for v in vidx.get((math.floor(mx / CELL) + di, math.floor(mz / CELL) + dj), ()):
                    if v == a or v == b:
                        continue
                    t = ((v[0] - ax) * abx + (v[2] - az) * abz) / L2 if L2 > 1e-12 else -1
                    if t <= 0.02 or t >= 0.98:
                        continue
                    cx, cz = ax + t * abx, az + t * abz
                    perp = math.hypot(v[0] - cx, v[2] - cz)
                    ey = a[1] + t * (b[1] - a[1])
                    ydiff = abs(ey - v[1])
                    if best_int is None or perp < best_int[0]:
                        best_int = (perp, t, ydiff, v)
        if best_int is not None and best_int[0] < 0.2:
            missed_tjunction += 1
            tj_ydiffs.append(best_int[2])
        else:
            genuine_gap += 1
            gap_dists.append(best_int[0] if best_int else 99)
    print(f"missed T-junctions (opposing vert within 0.2u perp of the edge span): {missed_tjunction}")
    if tj_ydiffs:
        print(f"   their edge-vs-vert Y diffs: min {min(tj_ydiffs):.3f} max {max(tj_ydiffs):.3f} "
              f"median {sorted(tj_ydiffs)[len(tj_ydiffs)//2]:.3f}")
        print(f"   ydiff hist: {Counter(round(y,1) for y in tj_ydiffs)}")
    print(f"genuine gaps (no opposing vert on the span): {genuine_gap}")
    if gap_dists:
        print(f"   nearest-vert perp dists: {sorted(round(d,2) for d in gap_dists)[:20]}")

    # Are the once-edges owned by carried, fill, or frame tris? tag each tri
    # carried = cell in placed AND matches a low-Y ecotone (y<2.5 typical); approximate by y.
    # Instead: classify the two verts of each once-edge by Y band.
    yband = Counter()
    for (a, b) in open_bad:
        lo = min(a[1], b[1]); hi = max(a[1], b[1])
        tag = "both_low(<2)" if hi < 2.0 else "both_high(>2.5)" if lo > 2.5 else "mixed"
        yband[tag] += 1
    print(f"once-edge Y bands: {dict(yband)}")


if __name__ == "__main__":
    main()
