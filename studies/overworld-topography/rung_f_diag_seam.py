"""RUNG F seam diagnostic -- classify the residual once-edges precisely so the rebuild is targeted."""
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

    # placed_R rectangle analysis
    cxs = [c[0] for c in placed]; czs = [c[1] for c in placed]
    x0, x1, z0, z1 = min(cxs), max(cxs), min(czs), max(czs)
    full_rect = (x1 - x0 + 1) * (z1 - z0 + 1)
    print(f"placed_R: {len(placed)} cells; bbox x[{x0},{x1}] z[{z0},{z1}] = {full_rect} full-rect cells; "
          f"missing {full_rect - len(placed)} interior cells")
    # which cells in the bbox rect are NOT placed?
    missing = [(cx, cz) for cx in range(x0, x1 + 1) for cz in range(z0, z1 + 1)
               if (cx, cz) not in placed]
    print(f"  missing cells sample: {missing[:20]}")
    # world extent of placed rect
    print(f"  world x[{x0*CELL:.0f},{(x1+1)*CELL:.0f}] z[{z0*CELL:.0f},{(z1+1)*CELL:.0f}]")

    # world soup
    gpos = []
    gtris = []
    for blk, bm in final.items():
        base = len(gpos)
        ox, oz = X.block_world_origin(blk[0], blk[1])
        for v in bm.verts:
            gpos.append((v[0] + ox, v[1], v[2] + oz))
        for tri in bm.tris:
            w = [(bm.verts[tri[q]][0] + ox, bm.verts[tri[q]][2] + oz) for q in range(3)]
            cx = sum(p[0] for p in w) / 3.0; cz = sum(p[1] for p in w) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            gtris.append((base + tri[0], base + tri[1], base + tri[2], cell in placed))

    ecnt = Counter()
    for (i, j, k, _c) in gtris:
        pts = [(round(gpos[v][0], 3), round(gpos[v][1], 3), round(gpos[v][2], 3)) for v in (i, j, k)]
        for q in range(3):
            if pts[q] == pts[(q + 1) % 3]:
                continue
            ecnt[tuple(sorted((pts[q], pts[(q + 1) % 3])))] += 1
    open_bad = [e for e, nn in ecnt.items() if nn == 1 and not (e[0][1] <= 1e-3 and e[1][1] <= 1e-3)]
    print(f"\nONCE-EDGES above skirt: {len(open_bad)}")

    # classify each once-edge by geometry
    def on_block_border(p):
        return abs(p[0] - round(p[0] / BLOCK) * BLOCK) < 1e-2 or abs(p[2] - round(p[2] / BLOCK) * BLOCK) < 1e-2

    def on_cell_grid_x(p):
        return abs(p[0] - round(p[0] / CELL) * CELL) < 1e-2

    def on_cell_grid_z(p):
        return abs(p[2] - round(p[2] / CELL) * CELL) < 1e-2

    cls = Counter()
    linebuckets = defaultdict(int)
    for (a, b) in open_bad:
        # is the edge colinear along x=const or z=const?
        dx = abs(a[0] - b[0]); dz = abs(a[2] - b[2]); dy = abs(a[1] - b[1])
        # which const line?
        if dx < 1e-2:  # vertical line x=const
            xv = round((a[0] + b[0]) / 2, 3)
            bord = abs(xv - round(xv / BLOCK) * BLOCK) < 1e-2
            linebuckets[("x", xv, "border" if bord else "cellgrid" if abs(xv - round(xv/CELL)*CELL) < 1e-2 else "offgrid")] += 1
            cls[("Xline", "border" if bord else "interior")] += 1
        elif dz < 1e-2:
            zv = round((a[2] + b[2]) / 2, 3)
            bord = abs(zv - round(zv / BLOCK) * BLOCK) < 1e-2
            linebuckets[("z", zv, "border" if bord else "cellgrid" if abs(zv - round(zv/CELL)*CELL) < 1e-2 else "offgrid")] += 1
            cls[("Zline", "border" if bord else "interior")] += 1
        else:
            # diagonal edge (a triangle hypotenuse) that is single-owned
            cls[("diag", "y0" if min(a[1], b[1]) < 1e-3 else "high")] += 1
    print("class tally:", dict(cls))
    print("line buckets (axis,coord,kind)->count:")
    for k in sorted(linebuckets, key=lambda t: -linebuckets[t]):
        print(f"   {k}: {linebuckets[k]}")

    # Y-span of once-edge endpoints (height mismatch signature)
    ys = [p[1] for e in open_bad for p in e]
    print(f"\nonce-edge endpoint Y range: {min(ys):.2f}..{max(ys):.2f}")
    # sample the diagonal / interior ones
    print("\nsample once-edges:")
    for e in open_bad[:14]:
        print("   ", e)

    # how many within 72u of centre (the R1 blocker zone)?
    cx_w = (x0 + x1 + 1) / 2 * CELL; cz_w = (z0 + z1 + 1) / 2 * CELL
    near = sum(1 for (a, b) in open_bad
               if math.hypot((a[0]+b[0])/2 - cx_w, (a[2]+b[2])/2 - cz_w) < 90)
    print(f"\nonce-edges within 90u of window centre ({cx_w:.0f},{cz_w:.0f}): {near}")


if __name__ == "__main__":
    main()
