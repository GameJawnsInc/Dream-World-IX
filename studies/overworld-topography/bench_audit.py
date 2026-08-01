"""BENCH AUDIT -- GATE T (tessellation) + the WALKABILITY pass, on deployed bytes.

The two gates the ground-junction synthesis said to bank regardless of the arc's next
move (studies/path-d-new-world/GROUND-JUNCTION-SYNTHESIS.md): the only gate in the arc
with demonstrated discriminating power (red on the live bytes, green on pristine AND
stock), and the one defect class that can strand a save (which no prior gate covered).

GATE T -- scoped to the GRASS class in the terrain part (stock's own object/entrance
parts legitimately run fine; an unscoped version refuses stock itself):
  * grass tri plan-area: >=85% inside stock's band, <=15% under 4u2
  * tris per 4u cell (grass): max <= 7 (stock grass map-wide max is 4-5; 7 leaves slack
    for lawful cell-corner splits), zero cells above

WALKABILITY -- the engine numbers, from Memoria source:
  * no short grass edge with a y-step over the 2.34375u climb ceiling (WMActor step)
  * no render-only grass facet: geometric ny <= 0.1 is SKIPPED by WMPhysics.Raycast's
    up-facing filter while still rendering as grass -- and the cache path
    (WMBlock.cs:155 -> WMPhysics.cs:49) applies NEITHER filter, so a cached bad
    triangle can ground the actor
  * grass steeper than 45 deg reported (stock grass: none; the rock class owns steep)

Usage:  py -X utf8 bench_audit.py [--src live|pristine|<dir>]
Read-only; exits 1 if any gate fails.
"""
import argparse
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import mesh as M                       # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LIVE = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc9" / "0_1"
CELLS = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]
GRASS_TOPO = {0, 1, 2, 3, 42}
CLIMB = 2.34375                                             # WMActor's step ceiling


def load(src):
    tris = []
    for (bx, by) in CELLS:
        for p in (src / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh",
                  src / f"Block[{bx}][{by}] Terrain.ff9mesh"):
            if p.is_file():
                break
        else:
            continue
        bm = M.blockmesh_from_ff9mesh(p, disc=9, x=bx, y=by, part="terrain")
        V = bm.chan_arrays[X.CH_POS]
        T = bm.chan_arrays[X.CH_TAN]
        ox, oz = 64.0 * bx, -64.0 * by
        for t in bm.tris:
            w = [(V[i][0] + ox, V[i][1], V[i][2] + oz) for i in t]
            tris.append((w, X.decode_id(int(round(T[t[0]][0])))["topograph"]))
    return tris


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="live")
    a = ap.parse_args()
    src = LIVE if a.src == "live" else Path(a.src) if a.src != "pristine" else \
        sorted(Path(r"C:\gd\Dream-World-IX\backups").glob("terrace-strip-prewall.*"))[-1]
    tris = load(src)
    g = [(w, t) for (w, t) in tris if t in GRASS_TOPO]
    print(f"src {src}\n{len(tris)} tris, {len(g)} grass")
    fails = []

    # ---- GATE T ----------------------------------------------------------------------------
    areas, cellcnt = [], Counter()
    bad_ny = steep = 0
    for w, t in g:
        p1, p2, p3 = (np.array(p) for p in w)
        n = np.cross(p2 - p1, p3 - p1)
        L = float(np.linalg.norm(n))
        areas.append(0.5 * abs((w[1][0] - w[0][0]) * (w[2][2] - w[0][2])
                               - (w[1][2] - w[0][2]) * (w[2][0] - w[0][0])))
        ny = abs(n[1]) / L if L > 1e-12 else 0.0
        if ny <= 0.1:
            bad_ny += 1
        elif math.degrees(math.acos(min(1.0, ny))) > 45.0:
            steep += 1
        cellcnt[(math.floor(sum(p[0] for p in w) / 3 / 4.0),
                 math.floor(sum(p[2] for p in w) / 3 / 4.0))] += 1
    in_band = sum(1 for ar in areas if 4.0 <= ar <= 10.0) / max(1, len(areas))
    tiny = sum(1 for ar in areas if ar < 4.0) / max(1, len(areas))
    cmax = max(cellcnt.values()) if cellcnt else 0
    n_over = sum(1 for v in cellcnt.values() if v > 7)
    print(f"GATE T: grass area med {np.median(areas):.2f}u2, in stock band 4-10u2: "
          f"{in_band:.0%}, under 4u2: {tiny:.0%}; tris/4u-cell max {cmax}, "
          f"cells over 7: {n_over}/{len(cellcnt)}")
    if in_band < 0.85:
        fails.append(f"T: only {in_band:.0%} of grass tris in stock's area band (need 85%)")
    if cmax > 7:
        fails.append(f"T: {n_over} cells over 7 tris/cell (max {cmax}; stock grass max 4-5)")

    # ---- WALKABILITY -----------------------------------------------------------------------
    ec = defaultdict(list)
    for w, t in g:
        k = [tuple(round(v, 3) for v in p) for p in w]
        for i, j in ((0, 1), (1, 2), (2, 0)):
            ec[tuple(sorted((k[i][::2], k[j][::2])))].append((k[i][1], k[j][1]))
    over = worst = 0
    for e, ys in ec.items():
        if math.dist(e[0], e[1]) >= 4.0:
            continue
        d = max(abs(y0 - y1) for y0, y1 in ys)
        if d > CLIMB:
            over += 1
            worst = max(worst, d)
    print(f"WALK: climb-ceiling edges {over} (worst {worst:.2f}u vs {CLIMB}); "
          f"render-only grass facets (ny<=0.1) {bad_ny}; grass >45deg {steep}")
    if over:
        fails.append(f"WALK: {over} short grass edges over the {CLIMB}u climb ceiling "
                     f"(worst {worst:.2f}u)")
    if bad_ny:
        fails.append(f"WALK: {bad_ny} render-only grass facets (the ground query skips "
                     f"them; the cache path does not)")

    print(f"gates: {len(fails)} failure(s)")
    for f in fails:
        print("  !!", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
