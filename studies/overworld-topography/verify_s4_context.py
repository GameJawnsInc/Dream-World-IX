"""ADVERSARIAL RE-MEASUREMENT of S4's claimed RINGED-COLLAR LAW (wall_context_census.py).

The claim under attack (verbatim headline): "Stock never rings a rock mass in a thin ground
collar ... foot->coast MAX is med 32.1u / p10 15.3u; only 2 of 33 components stay under 12u on
every side and both are small topless crags, and 0 of the 5 plateau/shelf-topped (mesa-class)
components stay under 24u anywhere (tightest 16.93u). Every mesa-class component also has
non-zero contiguous approach ground in the 8-16u, 16-32u and 32-64u annuli ... OURS ~10u = p6.1
overall, p0 among the 5 mesa-class ... 0u2 past 8u."

FOUR DELIBERATELY DIFFERENT METHODS (not a rerun):

  M1  LAND by TRIANGLE RASTERIZATION, not triangle-CENTROID.  Their LAND mask marks the one cell
      holding a tri's centroid.  Stock ground tris are LARGER than a 4u cell (block (12,12): 506
      tris for 4096u2), so a centroid mask punches false holes in solid interior ground, and every
      false hole is a false "coast".  M1 remeasures every foot->coast under a coverage mask and
      reports the delta as the instrument's own error bar.

  M2  MESA CLASS by GEOMETRY, not by the topo-10/13 crest label.  Their n=5 comes from requiring a
      welded rock component to touch a PLATEAU(10-12)/SHELF(13) tri.  M2 instead asks the physical
      question -- is there walkable ground >=8u ABOVE this component's foot inside its own plan
      hull -- and separately builds a SIZE-PEER population (components whose plan extent is within
      2x of our 61u mesa), because their 5 "mesa-class" objects include a 708x474u 65-block
      continental range.

  M3  THE BENCH MEASURED, not modelled.  Their limit (2) declares the bench side analytic: "a disc
      of radius 50.6u with the mesa centred", from which they DERIVE 0u2 in every annulus past 8u.
      The round-8 bench is live as loose .ff9mesh under FF9CustomMap-world/Disc9 blocks (5..7)x(7..8)
      -- 4920 tris, 346 of them topo-49.  M3 READS IT (read-only) and runs the identical foot->coast
      / annulus pipeline on the real carried mesa.

  M4  ARC-FRACTION and p90 instead of MAX.  foot->coast MAX is a single-point order statistic over a
      subsampled foot polyline: one stray vertex near one false hole sets it.  M4 reports the
      fraction of foot ARC beyond 16u and beyond 32u, which cannot be moved by one point.

RESULT (2026-07-31) -- THE STOCK SIDE REPRODUCES EXACTLY; THE CASE SIDE COLLAPSES.
Stock, under their own mask: foot->coast MAX med 32.14u / p10 15.27u, <=12u 2/33, <=16u 4/33,
<=24u 9/33, donor (15,14) 14.42/47.09/69.65 -- every headline number reproduced to 2 decimals.
But the bench was MODELLED, and the model is wrong by 2.6x on the headline and by infinity on two
of the four annuli:

  measure            THEIR ANALYTIC DISC          M3 MEASURED from the live .ff9mesh
  foot->coast MAX    ~10u   = p6.1 / p0 topped    25.89u  = p33.3 all / p20.0 topped
  foot->coast MED    8u (uniform 6-10u)           17.92u  (min 4.0, p90 25.2)
  annulus 8-16u      0u2    = p1.5 / p0           1920u2  = p51.5 all / p40 topped
  annulus 16-32u     0u2    = p1.5 / p0           1184u2  = p16.7 all / p10 topped
  annulus 32-64u     0u2    = p4.5 / p0           0u2     = p4.5 / p0   <-- the ONE that survives
  approach TOTAL     2342u2 = p12.1 / p0          5168u2  = p21.2 all / p20.0 topped
  host               8044u2 / eq-r 50.6u (disc)   7488u2  / eq-r 48.8u

70% of the bench mesa's 183.7u foot arc (= 97.0% of the donor's own foot) sits BEYOND 12u from the
coast; 30% beyond 20u. The bench's measured MAX of 25.89u is ABOVE the 24u gate the law itself uses
to condemn it, and 53% WIDER than the only stock ISLAND mesa's 16.93u. The law's prose clause
"0 of the 5 mesa-class stay under 24u anywhere (tightest 16.93u)" is self-contradictory and
disagrees with its own numbers list ("<=24u = 9/33 (1/5)").

M1: the centroid LAND mask calls 1667 cells (4.5% of land) ocean though terrain covers them, 358 of
them fully INTERIOR = false coasts. Under a coverage mask the donor's foot->coast min moves
14.42u -> 42.04u, so the derived MINIMUM-HOST ladder (>=56/74/76/89u) rests on a 28u artifact.
M4: arc-fraction >= 16u -- bench 0.552 vs stock med 0.429 (all) / 0.454 (topped) / 0.280
(size-peer) = p60-p70: the bench is MORE open than the stock median, not less.
Uniformity (max-min)/med -- bench 1.22 = p24 all / p40 topped; the DONOR's own seat is 1.17 and the
stock island mesa is 1.94, so "uniformity, not width" is not the off-language axis either.

Read-only against stock disc-1 AND against the live bench: opens files for reading only, writes
nothing under the game install, deploys nothing.
Artifacts -> out/verify_s4_context.json + out/verify_s4_context.png
Run: py -X utf8 verify_s4_context.py
"""
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import extract as X                                    # noqa: E402
from ff9mapkit.world import mesh as MSH                                     # noqa: E402

BLOCK, CELL = 64.0, 4.0
CPB = int(BLOCK / CELL)
ROCK = {49}
PLATEAU, SHELF = {10, 11, 12}, {13}
OUT = Path(__file__).with_name("out") / "verify_s4_context.json"
PNG = Path(__file__).with_name("out") / "verify_s4_context.png"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
BENCH_ROOT = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc9" / "0_1"
BENCH_BLOCKS = [(bx, by) for by in (7, 8) for bx in (5, 6, 7)]

WALKABLE = frozenset(t for t in range(64)
                     if (((0x0010667F >> (t - 32)) & 1) if t >= 32 else ((0xD8FF3CFF >> t) & 1)))

# barycentric sample set for M1's coverage rasterization: a 7-level triangular grid (36 points),
# so a tri of plan edge <=14u is sampled at <=2.3u spacing -- finer than the 4u cell.
_BARY = np.array([[i / 7.0, j / 7.0, 1.0 - i / 7.0 - j / 7.0]
                  for i in range(8) for j in range(8 - i)], dtype=float)

t0 = time.time()


def kk(v):
    return (round(v[0], 3), round(v[1], 3), round(v[2], 3))


def plan_tri_area(a, b, c):
    return 0.5 * abs((b[0] - a[0]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[0] - a[0]))


# =================================================================================================
# a reusable "world" builder -- used for BOTH stock disc-1 and the live bench, so the two sides are
# measured by literally the same code (their instrument modelled one side analytically).
# =================================================================================================
class World:
    def __init__(self, name, tris, topos, gx, gz):
        """tris: (N,3,3) world-space; topos: (N,) topograph."""
        self.name = name
        self.tris = tris
        self.topos = topos
        self.GX, self.GZ = gx, gz
        A = tris[:, :, 0]
        Z = tris[:, :, 2]
        Y = tris[:, :, 1]
        cx, cz, cy = A.mean(1), Z.mean(1), Y.mean(1)

        # -- their mask: CENTROID only -------------------------------------------------------
        self.land_c = np.zeros((gz, gx), dtype=bool)
        gi = np.floor(cx / CELL).astype(int)
        gj = np.floor(-cz / CELL).astype(int)
        ok = (gi >= 0) & (gi < gx) & (gj >= 0) & (gj < gz)
        self.land_c[gj[ok], gi[ok]] = True

        # -- M1's mask: full triangle COVERAGE ------------------------------------------------
        self.land_r = np.zeros((gz, gx), dtype=bool)
        self.walk_r = np.zeros((gz, gx), dtype=bool)
        ysum = np.zeros((gz, gx), dtype=float)
        ycnt = np.zeros((gz, gx), dtype=float)
        walkmask = np.array([t in WALKABLE for t in topos], dtype=bool)
        for b in _BARY:
            px = A @ b
            pz = Z @ b
            py = Y @ b
            ii = np.floor(px / CELL).astype(int)
            jj = np.floor(-pz / CELL).astype(int)
            m = (ii >= 0) & (ii < gx) & (jj >= 0) & (jj < gz)
            self.land_r[jj[m], ii[m]] = True
            mw = m & walkmask
            self.walk_r[jj[mw], ii[mw]] = True
            np.add.at(ysum, (jj[mw], ii[mw]), py[mw])
            np.add.at(ycnt, (jj[mw], ii[mw]), 1.0)
        self.rep_y = np.where(ycnt > 0, ysum / np.maximum(ycnt, 1e-9), np.nan)

        # walkable plan area per cell (rasterized: cell area x coverage) -- M1 unit
        self.cell_area = CELL * CELL

        # -- their walkable mask (centroid) for the hole comparison ---------------------------
        self.walk_c = np.zeros((gz, gx), dtype=bool)
        okw = ok & walkmask
        self.walk_c[gj[okw], gi[okw]] = True

        self.edt = {}
        for tag, mask in (("c", self.land_c), ("r", self.land_r)):
            self.edt[tag] = ndimage.distance_transform_edt(mask) * CELL

    def coast_dist(self, x, z, tag):
        """Exact plan distance from (x,z) to the nearest non-LAND cell RECTANGLE (same definition
        the census used, so the only variable is the MASK)."""
        mask = self.land_c if tag == "c" else self.land_r
        gi = int(math.floor(x / CELL))
        gj = int(math.floor(-z / CELL))
        if not (0 <= gi < self.GX and 0 <= gj < self.GZ) or not mask[gj, gi]:
            return 0.0
        r = int(math.ceil(self.edt[tag][gj, gi] / CELL)) + 2
        best = float(r * CELL + CELL)
        for dj in range(-r, r + 1):
            for di in range(-r, r + 1):
                jj, ii = gj + dj, gi + di
                if 0 <= jj < self.GZ and 0 <= ii < self.GX and mask[jj, ii]:
                    continue
                x0, x1 = ii * CELL, (ii + 1) * CELL
                z1, z0 = -jj * CELL, -(jj + 1) * CELL
                d = math.hypot(max(x0 - x, 0.0, x - x1), max(z0 - z, 0.0, z - z1))
                if d < best:
                    best = d
        return best


def build_components(tris, topos):
    """world-welded topo-49 components (the census's own unit, so the UNIT is not the variable)."""
    ridx = [i for i, t in enumerate(topos) if t in ROCK]
    parent = {i: i for i in ridx}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    eo = defaultdict(list)
    for i in ridx:
        k = [kk(tris[i][q]) for q in range(3)]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eo[tuple(sorted((k[a], k[b])))].append(i)
    for e, ts in eo.items():
        for j in range(1, len(ts)):
            ra, rb = find(ts[0]), find(ts[j])
            if ra != rb:
                parent[rb] = ra
    grp = defaultdict(list)
    for i in ridx:
        grp[find(i)].append(i)

    nonrock_edge_topo = defaultdict(set)
    for i, tp in enumerate(topos):
        if tp in ROCK:
            continue
        k = [kk(tris[i][q]) for q in range(3)]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            nonrock_edge_topo[tuple(sorted((k[a], k[b])))].add(tp)
    return grp, nonrock_edge_topo


def measure(world, grp, nonrock_edge_topo, tris, topos, min_tris=12, min_yspan=6.0, tag_list=("c", "r")):
    from scipy.spatial import ConvexHull
    out = []
    for root, ts in grp.items():
        if len(ts) < min_tris:
            continue
        P3 = np.array([tris[i][q] for i in ts for q in range(3)], dtype=float)
        ymin, ymax = float(P3[:, 1].min()), float(P3[:, 1].max())
        if ymax - ymin < min_yspan:
            continue
        own = set()
        for i in ts:
            k = [kk(tris[i][q]) for q in range(3)]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                own.add(tuple(sorted((k[a], k[b]))))
        crest_topos, foot_edges, foot_pts = Counter(), [], []
        for e in own:
            nb = nonrock_edge_topo.get(e)
            if not nb:
                continue
            if nb & (PLATEAU | SHELF):
                crest_topos.update(nb & (PLATEAU | SHELF))
            else:
                foot_edges.append(e)
                foot_pts.extend(e)
        if not foot_pts:
            low = P3[P3[:, 1] <= ymin + 1.5]
            foot_pts = [tuple(q) for q in low]
        if not foot_pts:
            continue
        FP = np.array(foot_pts, dtype=float)
        foot_y_med = float(np.median(FP[:, 1]))
        plan = P3[:, [0, 2]]
        aabb = (float(np.ptp(plan[:, 0])), float(np.ptp(plan[:, 1])))

        fu = np.unique(np.round(FP[:, [0, 2]], 2), axis=0)
        if len(fu) > 700:
            fu = fu[np.linspace(0, len(fu) - 1, 700).astype(int)]

        rec = dict(root=int(root), tris=len(ts), aabb=[round(aabb[0], 1), round(aabb[1], 1)],
                   maxext=round(max(aabb), 1), height=round(ymax - ymin, 2),
                   ymin=round(ymin, 2), ymax=round(ymax, 2),
                   foot_y_med=round(foot_y_med, 2),
                   foot_y_span=round(float(FP[:, 1].max() - FP[:, 1].min()), 2),
                   crest_label=dict(Counter({str(k): v for k, v in crest_topos.items()})),
                   topo_topped=bool(crest_topos), nblocks=len({(int(math.floor(x / BLOCK)),
                                                               int(math.floor(-z / BLOCK)))
                                                              for x, z in plan}))
        # plan hull, for the geometric crest test + coverage
        try:
            hull = ConvexHull(plan)
            rec["hull_area"] = round(float(hull.volume), 1)
            hv = plan[hull.vertices]
        except Exception:                                                   # noqa: BLE001
            rec["hull_area"] = 0.0
            hv = plan

        # ---- foot->coast under BOTH masks (M1) ----------------------------------------------
        for tag in tag_list:
            fd = np.array([world.coast_dist(float(x), float(z), tag) for x, z in fu])
            arc = 0.0
            arc16 = arc32 = 0.0
            bands = {"0-2": 0.0, "2-4": 0.0, "4-8": 0.0, "8-12": 0.0, "12-20": 0.0,
                     "20-40": 0.0, "40-inf": 0.0}
            for e in foot_edges:
                L = math.hypot(e[1][0] - e[0][0], e[1][2] - e[0][2])
                dm = 0.5 * (world.coast_dist(e[0][0], e[0][2], tag)
                            + world.coast_dist(e[1][0], e[1][2], tag))
                arc += L
                if dm >= 16.0:
                    arc16 += L
                if dm >= 32.0:
                    arc32 += L
                for lo, hi, key in ((0, 2, "0-2"), (2, 4, "2-4"), (4, 8, "4-8"), (8, 12, "8-12"),
                                    (12, 20, "12-20"), (20, 40, "20-40"), (40, 1e9, "40-inf")):
                    if lo <= dm < hi:
                        bands[key] += L
                        break
            rec[f"fc_{tag}"] = dict(
                min=round(float(fd.min()), 2), med=round(float(np.median(fd)), 2),
                p90=round(float(np.percentile(fd, 90)), 2), max=round(float(fd.max()), 2),
                arc=round(arc, 1),
                arc_frac_ge16=round(arc16 / max(1e-9, arc), 3),
                arc_frac_ge32=round(arc32 / max(1e-9, arc), 3),
                bands={k: round(v, 1) for k, v in bands.items()})

        # ---- M2 geometric crest: walkable ground >=8u above the foot INSIDE the plan hull ----
        i0 = max(0, int(math.floor(plan[:, 0].min() / CELL)))
        i1 = min(world.GX - 1, int(math.ceil(plan[:, 0].max() / CELL)))
        j0 = max(0, int(math.floor(-plan[:, 1].max() / CELL)))
        j1 = min(world.GZ - 1, int(math.ceil(-plan[:, 1].min() / CELL)))
        # point-in-hull via the hull's half-planes
        try:
            eqs = ConvexHull(plan).equations
        except Exception:                                                   # noqa: BLE001
            eqs = None
        top_cells = 0
        for jj in range(j0, j1 + 1):
            for ii in range(i0, i1 + 1):
                if not world.walk_r[jj, ii] or not np.isfinite(world.rep_y[jj, ii]):
                    continue
                if world.rep_y[jj, ii] < foot_y_med + 8.0:
                    continue
                p = np.array([(ii + 0.5) * CELL, -(jj + 0.5) * CELL])
                if eqs is not None and np.any(eqs[:, :2] @ p + eqs[:, 2] > CELL):
                    continue
                top_cells += 1
        rec["top_cells"] = top_cells
        rec["geo_topped"] = top_cells >= 4                      # >=64u2 of high walkable ground

        # ---- contiguous approach ground by annulus (rasterized cells, M1 unit) --------------
        segA = np.array([[e[0][0], e[0][2]] for e in foot_edges], dtype=float) if foot_edges else fu
        segB = np.array([[e[1][0], e[1][2]] for e in foot_edges], dtype=float) if foot_edges else fu

        def dseg(pt):
            AP = pt - segA
            AB = segB - segA
            den = np.maximum((AB * AB).sum(1), 1e-12)
            tt = np.clip((AP * AB).sum(1) / den, 0.0, 1.0)
            pr = segA + tt[:, None] * AB
            return float(np.hypot(*(pt - pr).T).min())

        ii0 = max(0, int(math.floor((plan[:, 0].min() - 70.0) / CELL)))
        ii1 = min(world.GX - 1, int(math.ceil((plan[:, 0].max() + 70.0) / CELL)))
        jj0 = max(0, int(math.floor((-plan[:, 1].max() - 70.0) / CELL)))
        jj1 = min(world.GZ - 1, int(math.ceil((-plan[:, 1].min() + 70.0) / CELL)))
        elig, dmap = set(), {}
        for jj in range(jj0, jj1 + 1):
            for ii in range(ii0, ii1 + 1):
                if not world.walk_r[jj, ii] or not np.isfinite(world.rep_y[jj, ii]):
                    continue
                if world.rep_y[jj, ii] > foot_y_med + 3.0:
                    continue
                d = dseg(np.array([(ii + 0.5) * CELL, -(jj + 0.5) * CELL]))
                if d > 66.0:
                    continue
                elig.add((jj, ii))
                dmap[(jj, ii)] = d
        seeds = [k for k, d in dmap.items() if d <= 6.0]
        seen, stack = set(seeds), list(seeds)
        while stack:
            jj, ii = stack.pop()
            for n in ((jj + 1, ii), (jj - 1, ii), (jj, ii + 1), (jj, ii - 1)):
                if n in elig and n not in seen:
                    seen.add(n)
                    stack.append(n)
        ann = {"0-8": 0.0, "8-16": 0.0, "16-32": 0.0, "32-64": 0.0}
        for c in seen:
            d = dmap[c]
            k = "0-8" if d < 8 else "8-16" if d < 16 else "16-32" if d < 32 else "32-64"
            ann[k] += CELL * CELL
        rec["ann"] = ann
        rec["ann_total"] = round(sum(ann.values()), 1)
        out.append(rec)
    out.sort(key=lambda c: -c["maxext"])
    return out


# =================================================================================================
# STOCK disc-1
# =================================================================================================
blocks = X.list_blocks(disc=1)
tri_l, topo_l = [], []
nb = 0
for (bx, by) in blocks:
    try:
        bm = X.read_block(bx, by, disc=1, part="terrain")
    except Exception:                                                       # noqa: BLE001
        continue
    nb += 1
    V = bm.chan_arrays[X.CH_POS]
    T = bm.chan_arrays[X.CH_TAN]
    ox, oz = BLOCK * bx, -BLOCK * by
    for t in range(len(bm.flat_index) // 3):
        i0, i1, i2 = bm.flat_index[3 * t:3 * t + 3]
        topo_l.append(X.decode_id(int(round(T[i0][0])))["topograph"])
        tri_l.append([[V[i][0] + ox, V[i][1], V[i][2] + oz] for i in (i0, i1, i2)])
STRI = np.array(tri_l, dtype=float)
STOPO = np.array(topo_l, dtype=int)
GX = (max(b[0] for b in blocks) + 1) * CPB
GZ = (max(b[1] for b in blocks) + 1) * CPB
stock = World("stock-disc1", STRI, STOPO, GX, GZ)
print(f"[{time.time()-t0:6.1f}s] STOCK: {nb} blocks, {len(STRI)} tris "
      f"({int((STOPO==49).sum())} topo-49), grid {GX}x{GZ}")

# ---- M1 CALIBRATION: how many false holes does the centroid mask punch? -------------------------
false_hole = stock.land_r & ~stock.land_c
lab_c, n_c = ndimage.label(stock.land_c, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]))
lab_r, n_r = ndimage.label(stock.land_r, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]))
# INTERIOR false holes: a false-hole cell all 4 of whose neighbours are land under the coverage mask
nbr = (np.roll(stock.land_r, 1, 0) & np.roll(stock.land_r, -1, 0)
       & np.roll(stock.land_r, 1, 1) & np.roll(stock.land_r, -1, 1))
interior_hole = false_hole & nbr
m1 = dict(land_c_cells=int(stock.land_c.sum()), land_r_cells=int(stock.land_r.sum()),
          false_hole_cells=int(false_hole.sum()), interior_false_hole_cells=int(interior_hole.sum()),
          false_hole_frac_of_land=round(float(false_hole.sum()) / max(1, stock.land_r.sum()), 4),
          landmasses_centroid=int(n_c), landmasses_coverage=int(n_r))
print(f"[{time.time()-t0:6.1f}s] M1: centroid LAND {m1['land_c_cells']} cells vs coverage LAND "
      f"{m1['land_r_cells']} -> {m1['false_hole_cells']} cells the centroid mask calls OCEAN that "
      f"actually carry terrain ({m1['false_hole_frac_of_land']:.1%}); of those "
      f"{m1['interior_false_hole_cells']} are fully INTERIOR (surrounded by land) = false coasts")

grp, nre = build_components(STRI, STOPO)
print(f"[{time.time()-t0:6.1f}s] {len(grp)} raw welded rock components")
SC_ = measure(stock, grp, nre, STRI, STOPO)
print(f"[{time.time()-t0:6.1f}s] {len(SC_)} banded components; topo-labelled topped "
      f"{sum(c['topo_topped'] for c in SC_)}; GEOMETRICALLY topped (walkable ground >=8u above "
      f"the foot inside its own plan hull) {sum(c['geo_topped'] for c in SC_)}")

# =================================================================================================
# M3 -- THE BENCH, MEASURED
# =================================================================================================
btri, btopo = [], []
for (bx, by) in BENCH_BLOCKS:
    p = BENCH_ROOT / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
    bm = MSH.blockmesh_from_ff9mesh(p, disc=9, x=bx, y=by, lod="0_1", part="Terrain")
    V = bm.chan_arrays[X.CH_POS]
    T = bm.chan_arrays[X.CH_TAN]
    ox, oz = BLOCK * bx, -BLOCK * by
    for t in range(len(bm.flat_index) // 3):
        i0, i1, i2 = bm.flat_index[3 * t:3 * t + 3]
        btopo.append(X.decode_id(int(round(T[i0][0])))["topograph"])
        btri.append([[V[i][0] + ox, V[i][1], V[i][2] + oz] for i in (i0, i1, i2)])
BTRI = np.array(btri, dtype=float)
BTOPO = np.array(btopo, dtype=int)
bench = World("bench-9013", BTRI, BTOPO, 9 * CPB, 10 * CPB)
bgrp, bnre = build_components(BTRI, BTOPO)
BC = measure(bench, bgrp, bnre, BTRI, BTOPO, min_tris=8, min_yspan=4.0)
BC.sort(key=lambda c: -c["tris"])
bmesa = BC[0] if BC else None
bench_land_area = float(bench.land_r.sum()) * CELL * CELL
bench_walk_area = float(bench.walk_r.sum()) * CELL * CELL
# island eq radius, measured
bl, bn = ndimage.label(bench.land_r, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]))
bsz = ndimage.sum(np.ones_like(bench.land_r, float), bl, index=range(1, bn + 1))
bmain = int(np.argmax(bsz)) + 1
bmain_area = float(bsz[bmain - 1]) * CELL * CELL
print(f"[{time.time()-t0:6.1f}s] M3 BENCH read from the live mod folder: {len(BTRI)} tris "
      f"({int((BTOPO==49).sum())} topo-49); LAND {bench_land_area:.0f}u2, walkable "
      f"{bench_walk_area:.0f}u2, largest landmass {bmain_area:.0f}u2 "
      f"(eq r {math.sqrt(bmain_area/math.pi):.1f}u); {len(BC)} rock components")
if bmesa:
    print(f"           the carried mesa: {bmesa['aabb']}u ext, h {bmesa['height']}u, "
          f"foot y span {bmesa['foot_y_span']}u, topo-topped {bmesa['topo_topped']} "
          f"geo-topped {bmesa['geo_topped']} ({bmesa['top_cells']} high walkable cells)")
    for tag in ("c", "r"):
        f = bmesa[f"fc_{tag}"]
        print(f"           MEASURED foot->coast (mask={tag}): min {f['min']} med {f['med']} "
              f"p90 {f['p90']} MAX {f['max']}  arc {f['arc']}u  frac>=16u {f['arc_frac_ge16']} "
              f"frac>=32u {f['arc_frac_ge32']}")
    print(f"           MEASURED approach annuli: {bmesa['ann']} (total {bmesa['ann_total']}u2)")

# =================================================================================================
# THE HEAD-TO-HEAD
# =================================================================================================
def st(v):
    a = np.asarray(v, float)
    return dict(n=len(a), min=round(float(a.min()), 2), p10=round(float(np.percentile(a, 10)), 2),
                med=round(float(np.median(a)), 2), p90=round(float(np.percentile(a, 90)), 2),
                max=round(float(a.max()), 2))


def pct(v, x):
    a = np.asarray(v, float)
    return round(100.0 * float((a < x).mean()) + 50.0 * float((a == x).mean()), 1)


POPS = {
    "all(33-equiv)": SC_,
    "topo-topped (their n=5)": [c for c in SC_ if c["topo_topped"]],
    "geo-topped (M2)": [c for c in SC_ if c["geo_topped"]],
    "SIZE PEERS 30-122u ext (M2)": [c for c in SC_ if 30.0 <= c["maxext"] <= 122.0],
    "geo-topped AND size-peer": [c for c in SC_ if c["geo_topped"] and 30.0 <= c["maxext"] <= 122.0],
}
print("\n" + "=" * 96)
print("HEAD-TO-HEAD: foot->coast MAX (their headline) under BOTH masks, over FIVE populations")
print("=" * 96)
report = {}
for pn, pop in POPS.items():
    if not pop:
        continue
    row = dict(n=len(pop))
    for tag in ("c", "r"):
        mx = [c[f"fc_{tag}"]["max"] for c in pop]
        row[f"max_{tag}"] = st(mx)
        row[f"le12_{tag}"] = sum(1 for v in mx if v <= 12.0)
        row[f"le16_{tag}"] = sum(1 for v in mx if v <= 16.0)
        row[f"le24_{tag}"] = sum(1 for v in mx if v <= 24.0)
        row[f"arcfrac16_{tag}"] = st([c[f"fc_{tag}"]["arc_frac_ge16"] for c in pop])
        row[f"arcfrac32_{tag}"] = st([c[f"fc_{tag}"]["arc_frac_ge32"] for c in pop])
    if bmesa:
        for tag in ("c", "r"):
            row[f"bench_pct_max_{tag}"] = pct([c[f"fc_{tag}"]["max"] for c in pop],
                                              bmesa[f"fc_{tag}"]["max"])
            row[f"bench_pct_arc16_{tag}"] = pct([c[f"fc_{tag}"]["arc_frac_ge16"] for c in pop],
                                                bmesa[f"fc_{tag}"]["arc_frac_ge16"])
    report[pn] = row
    print(f"\n-- {pn} (n={len(pop)})")
    for tag, lab in (("c", "centroid mask (THEIRS)"), ("r", "coverage mask (M1)")):
        s = row[f"max_{tag}"]
        print(f"   foot->coast MAX, {lab:24s}: min {s['min']:>7} p10 {s['p10']:>7} med {s['med']:>7} "
              f"p90 {s['p90']:>7} max {s['max']:>7} | <=12u {row[f'le12_{tag}']}/{len(pop)} "
              f"<=16u {row[f'le16_{tag}']}/{len(pop)} <=24u {row[f'le24_{tag}']}/{len(pop)}")
        if bmesa:
            print(f"   {'':26s}   BENCH MEASURED max {bmesa[f'fc_{tag}']['max']}u = "
                  f"p{row[f'bench_pct_max_{tag}']}; arc-frac>=16u {bmesa[f'fc_{tag}']['arc_frac_ge16']} "
                  f"vs stock med {row[f'arcfrac16_{tag}']['med']} = p{row[f'bench_pct_arc16_{tag}']}")

# annulus emptiness, re-tested with the measured bench
print("\n" + "=" * 96)
print("THE EMPTY-ANNULUS CLAIM ('OURS 0u2 past 8u -> p0 mesa-class') vs the MEASURED bench")
print("=" * 96)
ann_rows = {}
for pn, pop in POPS.items():
    if not pop:
        continue
    r = {}
    for k in ("0-8", "8-16", "16-32", "32-64"):
        vals = [c["ann"][k] for c in pop]
        r[k] = dict(stock=st(vals), n_zero=sum(1 for v in vals if v <= 1.0),
                    bench=(bmesa["ann"][k] if bmesa else None),
                    bench_pct=(pct(vals, bmesa["ann"][k]) if bmesa else None))
    ann_rows[pn] = r
    print(f"\n-- {pn} (n={len(pop)})")
    for k in ("0-8", "8-16", "16-32", "32-64"):
        s = r[k]["stock"]
        print(f"   {k+'u annulus':16s} stock min {s['min']:>8} med {s['med']:>9} max {s['max']:>9} "
              f"| zero in {r[k]['n_zero']}/{len(pop)} | BENCH MEASURED {r[k]['bench']:>8}u2 "
              f"= p{r[k]['bench_pct']}")

# the donor, re-measured
donor = None
for c in SC_:
    if 40.0 <= c["maxext"] <= 90.0 and c["height"] >= 15.0:
        pl = np.array([STRI[i][q] for i in grp[c["root"]] for q in range(3)])
        bxs = {(int(math.floor(x / BLOCK)), int(math.floor(-z / BLOCK)))
               for x, z in pl[:, [0, 2]]}
        if (15, 14) in bxs and (donor is None or abs(c["maxext"] - 61.0) < abs(donor["maxext"] - 61.0)):
            donor = c
if donor:
    print("\n" + "=" * 96)
    print("THE DONOR (15,14) RE-MEASURED under both masks (their 'min 14.42u, med 47.09u')")
    print("=" * 96)
    for tag, lab in (("c", "centroid (THEIRS)"), ("r", "coverage (M1)")):
        f = donor[f"fc_{tag}"]
        print(f"   {lab:20s} min {f['min']:>7} med {f['med']:>7} p90 {f['p90']:>7} max {f['max']:>7} "
              f"| arc {f['arc']}u frac>=16u {f['arc_frac_ge16']} frac>=32u {f['arc_frac_ge32']}")
    print(f"   ext {donor['aabb']} h {donor['height']} annuli {donor['ann']} "
          f"(total {donor['ann_total']}u2) geo_topped {donor['geo_topped']} "
          f"top_cells {donor['top_cells']}")

# the ONE stock island mesa (their near-match) re-measured, and the parity target it implies
horseshoe = None
for c in SC_:
    if c["topo_topped"] and 60.0 <= c["maxext"] <= 100.0 and c["height"] > 25.0:
        horseshoe = c
if horseshoe:
    print("\n-- THE STOCK ISLAND MESA (their 'Daguerreo horseshoe') re-measured " + "-" * 24)
    for tag in ("c", "r"):
        f = horseshoe[f"fc_{tag}"]
        print(f"   mask {tag}: min {f['min']} med {f['med']} p90 {f['p90']} max {f['max']} "
              f"arc {f['arc']}u frac>=16u {f['arc_frac_ge16']}")
    print(f"   ext {horseshoe['aabb']} h {horseshoe['height']} annuli {horseshoe['ann']} "
          f"total {horseshoe['ann_total']}u2")

# =================================================================================================
# PNG -- the measured bench next to the stock island mesa, same scale
# =================================================================================================
PNG.parent.mkdir(parents=True, exist_ok=True)
SCp = 4
panelW = 40 * CPB * 0 + 0
img = Image.new("RGB", (1180, 620), (14, 20, 32))
dr = ImageDraw.Draw(img)


def draw_patch(mask_land, mask_walk, tris, topos, i0, i1, j0, j1, ox, oy, title, sub):
    dr.text((ox, oy - 26), title, fill=(225, 228, 235))
    dr.text((ox, oy - 12), sub, fill=(150, 185, 225))
    for jj in range(j0, j1):
        for ii in range(i0, i1):
            if not mask_land[jj, ii]:
                continue
            col = (52, 88, 58) if mask_walk[jj, ii] else (92, 86, 76)
            dr.rectangle([ox + (ii - i0) * SCp, oy + (jj - j0) * SCp,
                          ox + (ii - i0) * SCp + SCp - 1, oy + (jj - j0) * SCp + SCp - 1], fill=col)
    for i, tp in enumerate(topos):
        if tp != 49:
            continue
        p = tris[i]
        xs = [ox + (q[0] / CELL - i0) * SCp for q in p]
        ys = [oy + (-q[2] / CELL - j0) * SCp for q in p]
        dr.polygon(list(zip(xs, ys)), outline=(230, 120, 110))


# bench panel
bi = np.nonzero(bench.land_r.any(0))[0]
bj = np.nonzero(bench.land_r.any(1))[0]
draw_patch(bench.land_r, bench.walk_r, BTRI, BTOPO, bi.min() - 1, bi.max() + 2, bj.min() - 1,
           bj.max() + 2, 30, 60,
           "THE ROUND-8 BENCH, MEASURED from the live .ff9mesh (not modelled as a disc)",
           f"land {bench_land_area:.0f}u2  walkable {bench_walk_area:.0f}u2  "
           f"foot->coast max {bmesa['fc_r']['max'] if bmesa else '?'}u  "
           f"annuli {bmesa['ann'] if bmesa else ''}")
# stock island mesa panel
if horseshoe:
    pl = np.array([STRI[i][q] for i in grp[horseshoe["root"]] for q in range(3)])
    i0 = int(pl[:, 0].min() / CELL) - 14
    i1 = int(pl[:, 0].max() / CELL) + 15
    j0 = int(-pl[:, 2].max() / CELL) - 14
    j1 = int(-pl[:, 2].min() / CELL) + 15
    draw_patch(stock.land_r, stock.walk_r, STRI, STOPO, max(0, i0), min(GX, i1), max(0, j0),
               min(GZ, j1), 620, 60, "THE STOCK ISLAND MESA (5-6,15-16), same scale",
               f"foot->coast max {horseshoe['fc_r']['max']}u  annuli {horseshoe['ann']}")
dr.text((30, 560), "green = walkable land   grey = land, non-walkable   red outline = topo-49 rock",
        fill=(200, 205, 212))
dr.text((30, 578), "The two panels are the same scale. If the bench's collar were 'thin on every "
                   "side' and the stock island mesa's were not, that would be visible here.",
        fill=(170, 180, 195))
img.save(PNG)

OUT.write_text(json.dumps(dict(
    meta=dict(stock_blocks=nb, stock_tris=len(STRI), rock_tris=int((STOPO == 49).sum()),
              banded_components=len(SC_), runtime_s=round(time.time() - t0, 1),
              bench_blocks=[list(b) for b in BENCH_BLOCKS], bench_tris=len(BTRI),
              bench_rock_tris=int((BTOPO == 49).sum())),
    m1_mask_calibration=m1,
    m2_class_counts={k: len(v) for k, v in POPS.items()},
    head_to_head=report,
    annulus=ann_rows,
    bench=dict(land_area=round(bench_land_area, 1), walk_area=round(bench_walk_area, 1),
               main_landmass_area=round(bmain_area, 1),
               main_eq_r=round(math.sqrt(bmain_area / math.pi), 1),
               n_rock_components=len(BC), mesa=bmesa, all_components=BC),
    donor=donor, stock_island_mesa=horseshoe,
    stock_components=SC_,
), indent=0))
print(f"\nartifacts -> {OUT}\nrender -> {PNG}\ntotal {time.time()-t0:.1f}s")
