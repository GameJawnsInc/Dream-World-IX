"""S4 -- THE WALL CONTEXT CENSUS: is the mesa-carry bench a legitimate HOST at all?

Registered in studies/path-d-new-world/GROUND-JUNCTION-SYNTHESIS.md (S4). Eight build
rounds have each fixed the named defect and had the owner name a new one in the same
region. Explanation (c) says the CONTEXT is off-language: a ~61x57u / ~26u-tall stock mesa
seated on a ~50.6u-reach synthetic island with 6-10u of ground between wall foot and coast
is a configuration stock never authors, so every junction is compressed into a distance the
grammar has no vocabulary for.

This instrument measures, for EVERY stock disc-1 rock/wall component (world-welded, so
cross-block massifs are ONE component -- the prior per-block wall studies split them):

  C1 SIZE       -- plan footprint (AABB extent, oriented min-rect extent, convex-hull
                   area) and height (ymax-ymin).
  C2 SEATING    -- plan distance from the component's FOOT polyline to the coast, where
                   "coast" == the boundary of TERRAIN PRESENCE (see THE COAST SUBSTITUTION
                   below, calibrated against real sea/beach part geometry).
  C3 APPROACH   -- area of CONTIGUOUS walkable ground reachable from the foot at the foot's
                   own altitude, bucketed into 0-8 / 8-16 / 16-32 / 32-64u annuli.
  C4 HOST       -- the landmass (4-connected LAND cells, 4u grid) that hosts it: area,
                   equivalent radius, walkable area, block span.
  C5 PLACEMENT  -- OUR bench configuration's percentile in every distribution above, the
                   count of stock instances inside its joint envelope, and the SMALLEST
                   stock landmass that hosts a wall of our size class + what its ground does.

THE COAST SUBSTITUTION (declared, then calibrated -- do not read this as "sea geometry"):
sea is a SEPARATE per-block sub-mesh (sea1..sea6/beach1/beach2 -- 454 sea4 containers on
disc 1), not a topograph inside Terrain, and the coast-nav classes 53-56 are the KIT's own
emitted stamp, absent from stock. So the coast here is the outline of TERRAIN PRESENCE on a
4u cell grid: a cell is LAND if any terrain triangle centroid falls in it, and the coast is
the first non-LAND cell. Calibrated in the run: on sampled coastal blocks, what fraction of
non-LAND cells are actually covered by that block's sea/beach parts (and how much sea laps
UNDER land -- the known SEA4-UNDER-LAND overlap).

RESULT (disc 1, 260/260 blocks, 27790 rock tris, 33 world-welded banded components of which 5
have a walkable plateau/shelf top -- 2026-07-31):

  * FALSIFIED, and worth knowing: there is NO bimodal seat with a trough at our collar width.
    A 4-12u wall-foot-to-coast collar is 35.5% of ALL stock foot arc (17.8% at 4-8u + 17.7% at
    8-12u), and 8 of 33 components keep >50% of their foot inside it. "6-10u of ground before
    the sea" is NOT by itself off-language.
  * THE RINGED-COLLAR LAW (this is the off-language axis): stock never rings a whole wall in a
    thin collar. foot->coast MAX is med 32.1u / p10 15.3u; only 2 of 33 components stay under
    12u everywhere and BOTH are small topless crags. Of the 5 walkable-top (mesa-class)
    components, ZERO stay under 24u -- the tightest is the Daguerreo horseshoe at 16.9u. Every
    mesa-class component also has NON-ZERO contiguous approach ground in the 8-16u, 16-32u AND
    32-64u annuli (floors 456 / 691 / 52 u2). Our bench: max 10u, and 0u2 past 8u -> p0 in the
    mesa class on all four measures.
  * THE DONOR-SEAT MISMATCH: the (15,14) mesa is a deep-INLAND feature. Its own foot never
    comes within 14.42u of a coast (med 47.09u, max 69.65u; 59.5% of its foot arc is >40u out).
    Our 6-10u seat lies entirely BELOW its own minimum -- zero distributional overlap.
  * THE HOST THAT DOES EXIST: the Daguerreo horseshoe (5-7,15-16) -- 77x89.5u, 29.05u tall,
    shelf-topped -- sits on a 9264u2 / eq-r 54.3u SIX-BLOCK island with foot->coast med 8.72u
    and 48.7% host coverage. Our 8044u2 / eq-r 50.6u bench is within 15% of it. The bench is a
    plausible host FOR THAT DONOR (already a qualified `world-mountain --donor`), not for this
    one. Runner-up: the (9-10,5-7) crag island, 5312u2 / eq-r 41.1u, hosting a 62.7u x 20.6u
    topless crag at foot->coast med 9.19u.
  * THE MINIMUM HOST for the (15,14) donor, from the donor's own measured seat: eq radius >=56u
    just to clear its 14.42u minimum at the mesa's CORNERS (half-diagonal 41.7u -- the corners
    are the binding radius, and the corners are where the owner reports the meadowy tiles),
    >=74u to make the 16-32u annulus non-empty, >=76u for approach-area parity (15183u2),
    >=89u for median-seat parity. Bench today: 50.6u.

Read-only vs stock disc-1; touches nothing in the game install and nothing deployed.
Artifacts -> out/wall_context_census.json + out/wall_context.png
Regenerate: py -X utf8 wall_context_census.py
"""
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

BLOCK, CELL = 64.0, 4.0
CPB = int(BLOCK / CELL)                                     # 16 cells per block
ROCK = {49}                                                 # the wall class (the 5 prior wall studies' seed)
PLATEAU = {10, 11, 12}
SHELF = {13}
OUT = Path(__file__).with_name("out") / "wall_context_census.json"
PNG = Path(__file__).with_name("out") / "wall_context.png"

# on-foot walkable topographs -- verbatim from ff9mapkit/world/entrance.py:630-633
# (Memoria ff9.cs:1487 w_movementCheckTopographID limit {0x0010667F, 0xD8FF3CFF};
#  check[0] = topo 32-63, check[1] = topo 0-31)
WALKABLE = frozenset(t for t in range(64)
                     if (((0x0010667F >> (t - 32)) & 1) if t >= 32 else ((0xD8FF3CFF >> t) & 1)))

# ---- OUR CASE (the bench under study -- the numbers the parent task states) -----------------
CASE = dict(
    name="bench 9013 mesa carry (round 8, live)",
    mesa_ext=(61.0, 57.0),                                  # donor (15,14) mesa plan extent
    height=26.0,                                            # crest above its base
    island_reach=50.6,                                      # grass reach from island CENTER
    foot_to_coast=(6.0, 10.0),                              # ground between wall foot and coast
)
DONOR_BLOCK = (15, 14)

t0 = time.time()


def kk(v):
    return (round(v[0], 3), round(v[1], 3), round(v[2], 3))


def plan_tri_area(a, b, c):
    return 0.5 * abs((b[0] - a[0]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[0] - a[0]))


# =============================================================================================
# PASS 1 -- the world grids (LAND / WALKABLE / representative y) + every rock triangle
# =============================================================================================
blocks = X.list_blocks(disc=1)
GX = (max(b[0] for b in blocks) + 1) * CPB
GZ = (max(b[1] for b in blocks) + 1) * CPB
land = np.zeros((GZ, GX), dtype=bool)
walk = np.zeros((GZ, GX), dtype=bool)
ysum = np.zeros((GZ, GX), dtype=float)
ycnt = np.zeros((GZ, GX), dtype=float)
walk_area = np.zeros((GZ, GX), dtype=float)                 # plan area of walkable tris per cell

rock_tris = []            # (world a, b, c) for topo-49 tris
rock_edges = []           # welded-edge list per tri, for the union-find
rock_blocks = []
nb_read = nb_fail = 0
topo_hist = Counter()

for (bx, by) in blocks:
    try:
        bm = X.read_block(bx, by, disc=1, part="terrain")
    except Exception:                                       # noqa: BLE001
        nb_fail += 1
        continue
    nb_read += 1
    V = bm.chan_arrays[X.CH_POS]
    T = bm.chan_arrays[X.CH_TAN]
    ox, oz = BLOCK * bx, -BLOCK * by
    ntri = len(bm.flat_index) // 3
    for t in range(ntri):
        i0, i1, i2 = bm.flat_index[3 * t:3 * t + 3]
        topo = X.decode_id(int(round(T[i0][0])))["topograph"]
        topo_hist[topo] += 1
        a = (V[i0][0] + ox, V[i0][1], V[i0][2] + oz)
        b = (V[i1][0] + ox, V[i1][1], V[i1][2] + oz)
        c = (V[i2][0] + ox, V[i2][1], V[i2][2] + oz)
        cx = (a[0] + b[0] + c[0]) / 3.0
        cz = (a[2] + b[2] + c[2]) / 3.0
        cy = (a[1] + b[1] + c[1]) / 3.0
        gi = int(math.floor(cx / CELL))
        gj = int(math.floor(-cz / CELL))
        if 0 <= gi < GX and 0 <= gj < GZ:
            land[gj, gi] = True
            if topo in WALKABLE:
                walk[gj, gi] = True
                ysum[gj, gi] += cy
                ycnt[gj, gi] += 1.0
                walk_area[gj, gi] += plan_tri_area(a, b, c)
        if topo in ROCK:
            rock_tris.append((a, b, c))
            rock_blocks.append((bx, by))

rep_y = np.where(ycnt > 0, ysum / np.maximum(ycnt, 1e-9), np.nan)
print(f"[{time.time() - t0:6.1f}s] pass1: {nb_read} blocks read ({nb_fail} unreadable), grid "
      f"{GX}x{GZ} cells ({GX * CPB and CELL}u), LAND {int(land.sum())} cells "
      f"({int(land.sum()) * CELL * CELL:.0f}u2), WALKABLE {int(walk.sum())} cells, "
      f"rock tris {len(rock_tris)}")

# ---- THE COAST SUBSTITUTION, CALIBRATED ------------------------------------------------------
# On sampled coastal blocks: do the block's own sea/beach parts cover the non-LAND cells?
SEA_PARTS = ("sea1", "sea2", "sea3", "sea4", "sea5", "sea6", "beach1", "beach2")
env = X._worldmap_env(1)
have = defaultdict(set)
pat = re.compile(r"block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)")
for k in env.container:
    m = pat.search((k or "").lower())
    if m and m.group(3) in SEA_PARTS:
        have[(int(m.group(1)), int(m.group(2)))].add(m.group(3))

coastal_blocks = [xy for xy in blocks
                  if 0 < land[xy[1] * CPB:(xy[1] + 1) * CPB, xy[0] * CPB:(xy[0] + 1) * CPB].sum() < CPB * CPB
                  and have.get(xy)]
sample = coastal_blocks[::max(1, len(coastal_blocks) // 14)][:14]
cal = dict(sampled_blocks=[list(xy) for xy in sample], nonland_cells=0, nonland_sea_covered=0,
           land_cells=0, land_sea_covered=0)
for (bx, by) in sample:
    sea_cells = set()
    for part in sorted(have[(bx, by)]):
        try:
            sm = X.read_block(bx, by, disc=1, part=part)
        except Exception:                                   # noqa: BLE001
            continue
        SV = sm.chan_arrays[X.CH_POS]
        for t in range(len(sm.flat_index) // 3):
            idx = sm.flat_index[3 * t:3 * t + 3]
            cx = sum(SV[i][0] for i in idx) / 3.0
            cz = sum(SV[i][2] for i in idx) / 3.0
            sea_cells.add((int(math.floor(cx / CELL)), int(math.floor(-cz / CELL))))
    for li in range(CPB):
        for lj in range(CPB):
            gi, gj = bx * CPB + li, by * CPB + lj
            insea = (li, lj) in sea_cells
            if land[gj, gi]:
                cal["land_cells"] += 1
                cal["land_sea_covered"] += 1 if insea else 0
            else:
                cal["nonland_cells"] += 1
                cal["nonland_sea_covered"] += 1 if insea else 0
cal["nonland_is_sea_frac"] = round(cal["nonland_sea_covered"] / max(1, cal["nonland_cells"]), 3)
cal["sea_under_land_frac"] = round(cal["land_sea_covered"] / max(1, cal["land_cells"]), 3)
print(f"[{time.time() - t0:6.1f}s] COAST CALIBRATION on {len(sample)} coastal blocks: "
      f"non-LAND cells actually carrying sea/beach geometry = {cal['nonland_is_sea_frac']:.1%} "
      f"(n={cal['nonland_cells']}); sea laps UNDER land in {cal['sea_under_land_frac']:.1%} "
      f"of land cells (n={cal['land_cells']})")

# ---- distance-to-coast field (cells) ---------------------------------------------------------
# EDT of the LAND mask -> for each land cell, cells to the nearest non-LAND (ocean) cell.
edt_cells = ndimage.distance_transform_edt(land)
edt_u = edt_cells * CELL


def exact_coast_dist(x, z):
    """Plan distance from world (x,z) to the nearest non-LAND cell RECTANGLE (exact, not
    cell-centre): EDT gives the search bound, then brute force the candidate rectangles."""
    gi = int(math.floor(x / CELL))
    gj = int(math.floor(-z / CELL))
    if not (0 <= gi < GX and 0 <= gj < GZ) or not land[gj, gi]:
        return 0.0
    r = int(math.ceil(edt_u[gj, gi] / CELL)) + 2
    best = float(r * CELL + CELL)
    for dj in range(-r, r + 1):
        for di in range(-r, r + 1):
            jj, ii = gj + dj, gi + di
            if 0 <= jj < GZ and 0 <= ii < GX and land[jj, ii]:
                continue                                    # land -> not a coast candidate
            x0, x1 = ii * CELL, (ii + 1) * CELL             # the ocean cell's rectangle
            z1, z0 = -jj * CELL, -(jj + 1) * CELL
            dx = max(x0 - x, 0.0, x - x1)
            dz = max(z0 - z, 0.0, z - z1)
            d = math.hypot(dx, dz)
            if d < best:
                best = d
    return best


# ---- landmasses (4-connected LAND) -----------------------------------------------------------
lab, nlab = ndimage.label(land, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]))
lm_cells = ndimage.sum(np.ones_like(land, dtype=float), lab, index=range(1, nlab + 1))
lm_walk = ndimage.sum(walk.astype(float), lab, index=range(1, nlab + 1))
LM = {}
for L in range(1, nlab + 1):
    js, is_ = np.nonzero(lab == L)
    area = float(lm_cells[L - 1]) * CELL * CELL
    LM[L] = dict(cells=int(lm_cells[L - 1]), area=round(area, 1),
                 eq_radius=round(math.sqrt(area / math.pi), 1),
                 walk_area=round(float(lm_walk[L - 1]) * CELL * CELL, 1),
                 ext=(round((is_.max() - is_.min() + 1) * CELL, 1),
                      round((js.max() - js.min() + 1) * CELL, 1)),
                 blocks=int(len({(int(i) // CPB, int(j) // CPB) for i, j in zip(is_, js)})))
print(f"[{time.time() - t0:6.1f}s] {nlab} landmasses; largest {max(v['area'] for v in LM.values()):.0f}u2 "
      f"(eq r {max(v['eq_radius'] for v in LM.values()):.0f}u)")

# =============================================================================================
# PASS 2 -- world-welded rock components (edge adjacency across block borders)
# =============================================================================================
parent = list(range(len(rock_tris)))


def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a


def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[rb] = ra


edge_owner = defaultdict(list)
for t, (a, b, c) in enumerate(rock_tris):
    ka, kb, kc = kk(a), kk(b), kk(c)
    for e in (tuple(sorted((ka, kb))), tuple(sorted((kb, kc))), tuple(sorted((kc, ka)))):
        edge_owner[e].append(t)
for e, ts in edge_owner.items():
    for i in range(1, len(ts)):
        union(ts[0], ts[i])

comp_tris = defaultdict(list)
for t in range(len(rock_tris)):
    comp_tris[find(t)].append(t)
print(f"[{time.time() - t0:6.1f}s] pass2: {len(comp_tris)} raw world-welded rock components")

# ---- non-rock neighbour lookup (for the crest / foot classification) -------------------------
# Re-walk the blocks once, cheap (memoized reads), recording every non-rock tri edge + its topo.
nonrock_edge_topo = defaultdict(set)
for (bx, by) in blocks:
    try:
        bm = X.read_block(bx, by, disc=1, part="terrain")
    except Exception:                                       # noqa: BLE001
        continue
    V = bm.chan_arrays[X.CH_POS]
    T = bm.chan_arrays[X.CH_TAN]
    ox, oz = BLOCK * bx, -BLOCK * by
    for t in range(len(bm.flat_index) // 3):
        i0, i1, i2 = bm.flat_index[3 * t:3 * t + 3]
        topo = X.decode_id(int(round(T[i0][0])))["topograph"]
        if topo in ROCK:
            continue
        p = [(V[i][0] + ox, V[i][1], V[i][2] + oz) for i in (i0, i1, i2)]
        k = [kk(q) for q in p]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            nonrock_edge_topo[tuple(sorted((k[a], k[b])))].add(topo)

# =============================================================================================
# PASS 3 -- per-component measurement
# =============================================================================================
MIN_TRIS, MIN_YSPAN = 12, 6.0


def min_rect_extent(pts):
    """Oriented minimum-area bounding rectangle extent (w, l) via rotating calipers on the hull."""
    from scipy.spatial import ConvexHull
    P = np.asarray(pts, dtype=float)
    if len(P) < 3:
        return (0.0, 0.0), 0.0
    try:
        h = P[ConvexHull(P).vertices]
    except Exception:                                       # noqa: BLE001
        return (float(np.ptp(P[:, 0])), float(np.ptp(P[:, 1]))), 0.0
    best = None
    for i in range(len(h)):
        d = h[(i + 1) % len(h)] - h[i]
        n = np.linalg.norm(d)
        if n < 1e-9:
            continue
        d = d / n
        R = np.array([[d[0], d[1]], [-d[1], d[0]]])
        Q = h @ R.T
        w, l = float(np.ptp(Q[:, 0])), float(np.ptp(Q[:, 1]))
        if best is None or w * l < best[0]:
            best = (w * l, (max(w, l), min(w, l)))
    return best[1], best[0]


def hull_area(pts):
    from scipy.spatial import ConvexHull
    P = np.asarray(pts, dtype=float)
    if len(P) < 3:
        return 0.0
    try:
        return float(ConvexHull(P).volume)
    except Exception:                                       # noqa: BLE001
        return 0.0


def seg_dists(pt, segs):
    """Min distance from a 2D point to a set of segments (vectorized)."""
    A, B = segs
    AP = pt - A
    AB = B - A
    denom = np.maximum((AB * AB).sum(1), 1e-12)
    t = np.clip((AP * AB).sum(1) / denom, 0.0, 1.0)
    proj = A + t[:, None] * AB
    return np.hypot(*(pt - proj).T)


comps = []
for root, ts in comp_tris.items():
    if len(ts) < MIN_TRIS:
        continue
    P3 = np.array([q for t in ts for q in rock_tris[t]], dtype=float)
    ymin, ymax = float(P3[:, 1].min()), float(P3[:, 1].max())
    if ymax - ymin < MIN_YSPAN:
        continue

    # -- crest / foot classification from the component's boundary edges --------------------
    own_edges = Counter()
    for t in ts:
        k = [kk(q) for q in rock_tris[t]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            own_edges[tuple(sorted((k[a], k[b])))] += 1
    crest_topos, foot_edges_l, foot_pts = Counter(), [], []
    for e in own_edges:
        nb = nonrock_edge_topo.get(e)
        if not nb:
            continue
        if nb & (PLATEAU | SHELF):
            crest_topos.update(nb & (PLATEAU | SHELF))
        else:
            foot_edges_l.append(e)
            foot_pts.extend(e)
    if not foot_edges_l:                                    # no ground weld -> use the low band
        low = P3[P3[:, 1] <= ymin + 1.5]
        foot_pts = [tuple(q) for q in low]
    if not foot_pts:
        continue
    FP = np.array([[p[0], p[1], p[2]] for p in foot_pts], dtype=float)
    foot_y_med = float(np.median(FP[:, 1]))
    foot_y_span = float(FP[:, 1].max() - FP[:, 1].min())

    # -- C1 size ----------------------------------------------------------------------------
    plan = P3[:, [0, 2]]
    aabb = (float(np.ptp(plan[:, 0])), float(np.ptp(plan[:, 1])))
    (rw, rl), _ = min_rect_extent(plan)
    ha = hull_area(plan)

    # -- C2 foot-to-coast -------------------------------------------------------------------
    fu = np.unique(np.round(FP[:, [0, 2]], 2), axis=0)
    if len(fu) > 900:                                       # deterministic subsample
        fu = fu[np.linspace(0, len(fu) - 1, 900).astype(int)]
    fdist = np.array([exact_coast_dist(float(x), float(z)) for x, z in fu])
    comp_dist_min = min(float(fdist.min()),
                        min(exact_coast_dist(float(p[0]), float(p[2]))
                            for p in P3[np.linspace(0, len(P3) - 1, min(len(P3), 400)).astype(int)]))

    # -- C2b THE FOOT BAND HISTOGRAM (arc-length weighted) ----------------------------------
    # Does stock hold a wall foot at 4-12u from the coast at all, or is the seat BIMODAL --
    # either AT the water (rock is the coast) or well inland (>=12u of ground)? Our bench's
    # uniform 6-10u grass collar lives exactly in the candidate trough.
    BANDS = ((0, 2), (2, 4), (4, 8), (8, 12), (12, 20), (20, 40), (40, 1e9))
    band_len = {f"{lo}-{hi if hi < 1e9 else 'inf'}": 0.0 for lo, hi in BANDS}
    foot_arc = 0.0
    for e in foot_edges_l:
        L = math.hypot(e[1][0] - e[0][0], e[1][2] - e[0][2])
        dm = 0.5 * (exact_coast_dist(e[0][0], e[0][2]) + exact_coast_dist(e[1][0], e[1][2]))
        foot_arc += L
        for lo, hi in BANDS:
            if lo <= dm < hi:
                band_len[f"{lo}-{hi if hi < 1e9 else 'inf'}"] += L
                break

    # -- host landmass ----------------------------------------------------------------------
    votes = Counter()
    for x, z in fu:
        gi, gj = int(math.floor(x / CELL)), int(math.floor(-z / CELL))
        if 0 <= gi < GX and 0 <= gj < GZ and lab[gj, gi]:
            votes[int(lab[gj, gi])] += 1
    host = votes.most_common(1)[0][0] if votes else None

    # -- C3 contiguous approach ground, by annulus ------------------------------------------
    if len(foot_edges_l) >= 1:
        segA = np.array([[e[0][0], e[0][2]] for e in foot_edges_l], dtype=float)
        segB = np.array([[e[1][0], e[1][2]] for e in foot_edges_l], dtype=float)
    else:
        segA = segB = fu
    segs = (segA, segB)
    i0 = max(0, int(math.floor((plan[:, 0].min() - 70.0) / CELL)))
    i1 = min(GX - 1, int(math.ceil((plan[:, 0].max() + 70.0) / CELL)))
    j0 = max(0, int(math.floor((-plan[:, 1].max() - 70.0) / CELL)))
    j1 = min(GZ - 1, int(math.ceil((-plan[:, 1].min() + 70.0) / CELL)))
    YTOL = 3.0                                              # the foot's OWN altitude band
    elig, dmap = {}, {}
    for jj in range(j0, j1 + 1):
        for ii in range(i0, i1 + 1):
            if not walk[jj, ii] or not np.isfinite(rep_y[jj, ii]):
                continue
            if rep_y[jj, ii] > foot_y_med + YTOL:
                continue                                    # the plateau top / upper terrace
            cx, cz = (ii + 0.5) * CELL, -(jj + 0.5) * CELL
            d = float(seg_dists(np.array([cx, cz]), segs).min())
            if d > 66.0:
                continue
            elig[(jj, ii)] = True
            dmap[(jj, ii)] = d
    seeds = [k for k, d in dmap.items() if d <= 6.0]
    seen, stack = set(seeds), list(seeds)
    while stack:
        jj, ii = stack.pop()
        for njj, nii in ((jj + 1, ii), (jj - 1, ii), (jj, ii + 1), (jj, ii - 1)):
            if (njj, nii) in elig and (njj, nii) not in seen:
                seen.add((njj, nii))
                stack.append((njj, nii))
    ann = {"0-8": 0.0, "8-16": 0.0, "16-32": 0.0, "32-64": 0.0}
    for (jj, ii) in seen:
        d = dmap[(jj, ii)]
        key = "0-8" if d < 8 else "8-16" if d < 16 else "16-32" if d < 32 else "32-64" if d < 64 else None
        if key:
            ann[key] += float(walk_area[jj, ii])

    comps.append(dict(
        root=int(root), tris=len(ts), blocks=sorted({rock_blocks[t] for t in ts}),
        ymin=round(ymin, 2), ymax=round(ymax, 2), height=round(ymax - ymin, 2),
        aabb=[round(aabb[0], 1), round(aabb[1], 1)], maxext=round(max(aabb), 1),
        rect=[round(rw, 1), round(rl, 1)], rect_max=round(rw, 1), hull_area=round(ha, 1),
        foot_pts=int(len(fu)), foot_y_med=round(foot_y_med, 2), foot_y_span=round(foot_y_span, 2),
        foot_coast_min=round(float(fdist.min()), 2), foot_coast_med=round(float(np.median(fdist)), 2),
        foot_coast_p90=round(float(np.percentile(fdist, 90)), 2),
        foot_coast_max=round(float(fdist.max()), 2),
        comp_coast_min=round(comp_dist_min, 2),
        crest=dict(Counter({str(k): v for k, v in crest_topos.items()})),
        walkable_top=bool(crest_topos),
        host=host, host_area=(LM[host]["area"] if host else None),
        host_eq_r=(LM[host]["eq_radius"] if host else None),
        host_blocks=(LM[host]["blocks"] if host else None),
        ann={k: round(v, 1) for k, v in ann.items()},
        ann_total=round(sum(ann.values()), 1),
        foot_arc=round(foot_arc, 1),
        band_len={k: round(v, 1) for k, v in band_len.items()},
        band_frac={k: round(v / max(1e-9, foot_arc), 3) for k, v in band_len.items()},
        coverage=(round(ha / LM[host]["area"], 3) if host and LM[host]["area"] else None),
    ))

comps.sort(key=lambda c: -c["maxext"])
print(f"[{time.time() - t0:6.1f}s] pass3: {len(comps)} banded rock components "
      f"(>= {MIN_TRIS} tris, y-span >= {MIN_YSPAN}u); "
      f"{sum(1 for c in comps if c['walkable_top'])} have a WALKABLE TOP (plateau/shelf crest)")

# ---- CALIBRATION vs the 5 prior wall studies' unit -------------------------------------------
# plateau_edge.py / rock_wall_* extract PER-BLOCK crest-seeded components and report 76 over 48
# blocks. This instrument welds ACROSS block borders (a massif is one component), so its count
# MUST be smaller. Reproducing the prior number here is the calibration that the extraction and
# the topo decode agree with the studies that chose the donor.
by_block = defaultdict(list)
for t, xy in enumerate(rock_blocks):
    by_block[xy].append(t)
blk_comps = blk_blocks = 0
for xy, ts in by_block.items():
    p2 = {t: t for t in ts}

    def f2(a, p2=p2):
        while p2[a] != a:
            p2[a] = p2[p2[a]]
            a = p2[a]
        return a

    eo = defaultdict(list)
    for t in ts:
        k = [kk(q) for q in rock_tris[t]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eo[tuple(sorted((k[a], k[b])))].append(t)
    for e, tl in eo.items():
        for i in range(1, len(tl)):
            ra, rb = f2(tl[0]), f2(tl[i])
            if ra != rb:
                p2[rb] = ra
    grp = defaultdict(list)
    for t in ts:
        grp[f2(t)].append(t)
    hits = 0
    for root, g in grp.items():
        if len(g) < MIN_TRIS:
            continue
        P = np.array([q for t in g for q in rock_tris[t]], dtype=float)
        if float(P[:, 1].max() - P[:, 1].min()) < MIN_YSPAN:
            continue
        crest = False
        for t in g:
            k = [kk(q) for q in rock_tris[t]]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                nb = nonrock_edge_topo.get(tuple(sorted((k[a], k[b]))))
                if nb and nb & PLATEAU:
                    crest = True
        if crest:
            hits += 1
    blk_comps += hits
    blk_blocks += 1 if hits else 0
print(f"           CALIBRATION (per-BLOCK crest-seeded, the prior studies' unit): {blk_comps} "
      f"components over {blk_blocks} blocks (plateau_edge.py reported 76 over 48)")

# ---- label the donor mesa --------------------------------------------------------------------
donor = None
for c in comps:
    if DONOR_BLOCK in c["blocks"] and 40.0 <= c["maxext"] <= 90.0 and c["height"] >= 15.0:
        if donor is None or abs(c["maxext"] - 61.0) < abs(donor["maxext"] - 61.0):
            donor = c
if donor:
    donor["label"] = f"DONOR mesa (15,14)"
    print(f"           donor component: ext {donor['aabb']} rect {donor['rect']} h {donor['height']} "
          f"blocks {donor['blocks']} foot->coast min {donor['foot_coast_min']} med "
          f"{donor['foot_coast_med']} host {donor['host_area']}u2 (eq r {donor['host_eq_r']}u) "
          f"annuli {donor['ann']}")

# =============================================================================================
# C5 -- PLACE OUR CASE
# =============================================================================================
case_ext = max(CASE["mesa_ext"])
case_h = CASE["height"]
R = CASE["island_reach"]
case_island_area = math.pi * R * R
case_fc_lo, case_fc_hi = CASE["foot_to_coast"]
case_fc = (case_fc_lo + case_fc_hi) / 2.0
# bench annuli, analytic: a circular island radius R with the foot ring at R - case_fc.
# Ground exists ONLY between the foot ring and the coast, so every annulus past the coast is empty.
rf = R - case_fc
case_ann = {"0-8": round(math.pi * (R * R - max(rf, R - 8.0) ** 2), 1) if case_fc <= 8 else
                   round(math.pi * ((rf + 8.0) ** 2 - rf * rf), 1),
            "8-16": 0.0, "16-32": 0.0, "32-64": 0.0}
case_ann["total"] = case_ann["0-8"]


def pctl_of(vals, v):
    a = np.asarray(vals, dtype=float)
    return round(100.0 * float((a < v).mean()) + 100.0 * 0.5 * float((a == v).mean()), 1)


def stat(vals):
    a = np.asarray(vals, dtype=float)
    return dict(n=len(a), min=round(float(a.min()), 1), p10=round(float(np.percentile(a, 10)), 1),
                med=round(float(np.median(a)), 1), p90=round(float(np.percentile(a, 90)), 1),
                max=round(float(a.max()), 1))


ALL = comps
TOPPED = [c for c in comps if c["walkable_top"]]
POP = dict(all=ALL, walkable_top=TOPPED)

placement = {}
for pname, pop in POP.items():
    if not pop:
        continue
    placement[pname] = dict(
        n=len(pop),
        height=dict(stock=stat([c["height"] for c in pop]), case=case_h,
                    pct=pctl_of([c["height"] for c in pop], case_h)),
        maxext=dict(stock=stat([c["maxext"] for c in pop]), case=case_ext,
                    pct=pctl_of([c["maxext"] for c in pop], case_ext)),
        hull_area=dict(stock=stat([c["hull_area"] for c in pop]),
                       case=round(math.pi * 30.5 * 28.5, 1),
                       pct=pctl_of([c["hull_area"] for c in pop], math.pi * 30.5 * 28.5)),
        foot_coast_min=dict(stock=stat([c["foot_coast_min"] for c in pop]), case=case_fc_lo,
                            pct=pctl_of([c["foot_coast_min"] for c in pop], case_fc_lo)),
        foot_coast_med=dict(stock=stat([c["foot_coast_med"] for c in pop]), case=case_fc,
                            pct=pctl_of([c["foot_coast_med"] for c in pop], case_fc)),
        host_area=dict(stock=stat([c["host_area"] for c in pop if c["host_area"]]),
                       case=round(case_island_area, 1),
                       pct=pctl_of([c["host_area"] for c in pop if c["host_area"]], case_island_area)),
        host_eq_r=dict(stock=stat([c["host_eq_r"] for c in pop if c["host_eq_r"]]), case=R,
                       pct=pctl_of([c["host_eq_r"] for c in pop if c["host_eq_r"]], R)),
        ann={k: dict(stock=stat([c["ann"][k] for c in pop]), case=case_ann[k],
                     pct=pctl_of([c["ann"][k] for c in pop], case_ann[k]))
             for k in ("0-8", "8-16", "16-32", "32-64")},
        ann_total=dict(stock=stat([c["ann_total"] for c in pop]), case=case_ann["total"],
                       pct=pctl_of([c["ann_total"] for c in pop], case_ann["total"])),
    )

# ---- our SIZE CLASS + the joint envelope -----------------------------------------------------
SIZE_LO, SIZE_HI = 50.0, 75.0                               # plan max extent band around 61
H_LO, H_HI = 18.0, 34.0                                     # height band around 26
size_class = [c for c in comps if SIZE_LO <= c["maxext"] <= SIZE_HI and H_LO <= c["height"] <= H_HI]
size_class.sort(key=lambda c: c["host_area"] or 0.0)
smallest_hosts = size_class[:8]

joint = [c for c in comps
         if SIZE_LO <= c["maxext"] <= SIZE_HI and H_LO <= c["height"] <= H_HI
         and (c["host_eq_r"] or 1e9) <= 1.35 * R and c["foot_coast_med"] <= case_fc_hi + 4.0]
loose = [c for c in comps
         if (c["host_eq_r"] or 1e9) <= 1.35 * R and c["maxext"] >= 40.0]
tight_seat = [c for c in comps if c["foot_coast_med"] <= case_fc_hi and c["maxext"] >= SIZE_LO]

# =============================================================================================
# REPORT
# =============================================================================================
print("\n" + "=" * 92)
print("S4 THE CONTEXT CENSUS -- OUR CONFIGURATION vs THE STOCK ROCK/WALL POPULATION")
print("=" * 92)
print(f"population: {nb_read} disc-1 terrain blocks; {len(comps)} world-welded rock components "
      f"passing the band gate; {len(TOPPED)} with a walkable (plateau/shelf) top")
print(f"OUR CASE: mesa {CASE['mesa_ext'][0]}x{CASE['mesa_ext'][1]}u, h {case_h}u, host island "
      f"eq-radius {R}u (area {case_island_area:.0f}u2), foot->coast {case_fc_lo}-{case_fc_hi}u")

for pname in ("all", "walkable_top"):
    if pname not in placement:
        continue
    p = placement[pname]
    print(f"\n-- population '{pname}' (n={p['n']}) " + "-" * 50)
    for key, lab, unit in (("height", "height", "u"), ("maxext", "plan max extent", "u"),
                           ("hull_area", "plan hull area", "u2"),
                           ("foot_coast_min", "foot->coast MIN", "u"),
                           ("foot_coast_med", "foot->coast MED", "u"),
                           ("host_eq_r", "host landmass eq-radius", "u"),
                           ("host_area", "host landmass area", "u2"),
                           ("ann_total", "approach ground 0-64u total", "u2")):
        s = p[key]["stock"]
        print(f"   {lab:30s} stock min {s['min']:>9} p10 {s['p10']:>9} med {s['med']:>9} "
              f"p90 {s['p90']:>10} max {s['max']:>10} | OURS {p[key]['case']:>9}{unit} "
              f"= p{p[key]['pct']}")
    for k in ("0-8", "8-16", "16-32", "32-64"):
        s = p["ann"][k]["stock"]
        print(f"   {'approach ground ' + k + 'u':30s} stock min {s['min']:>9} p10 {s['p10']:>9} "
              f"med {s['med']:>9} p90 {s['p90']:>10} max {s['max']:>10} | OURS "
              f"{p['ann'][k]['case']:>9}u2 = p{p['ann'][k]['pct']}")

# ---- THE FOOT BAND HISTOGRAM (the seat-mode discriminant) ------------------------------------
BKEYS = ["0-2", "2-4", "4-8", "8-12", "12-20", "20-40", "40-inf"]
band_global = {pn: {k: 0.0 for k in BKEYS} for pn in POP}
for pn, pop in POP.items():
    for c in pop:
        for k in BKEYS:
            band_global[pn][k] += c["band_len"][k]
print(f"\n-- C2b THE SEAT-MODE DISCRIMINANT: wall-foot arc length by distance-to-coast band " + "-" * 4)
for pn in ("all", "walkable_top"):
    tot = max(1e-9, sum(band_global[pn].values()))
    print(f"   {pn:13s} (n={len(POP[pn])}, {tot:.0f}u of foot): " +
          "  ".join(f"{k}u {band_global[pn][k] / tot:5.1%}" for k in BKEYS))
# per-component: is any single component's foot MOSTLY (>50%) in the 4-12u window?
mid = [(c["blocks"][:2], round(c["band_frac"]["4-8"] + c["band_frac"]["8-12"], 3), c["maxext"],
        c["walkable_top"]) for c in comps
       if c["band_frac"]["4-8"] + c["band_frac"]["8-12"] > 0.5]
print(f"   components whose foot is >50% inside the 4-12u collar window: {len(mid)} of {len(comps)}"
      + (f" -> {mid}" if mid else ""))
print(f"   OUR CASE: 100% of the mesa foot sits in the 6-10u window (a uniform grass collar)")

# THE SHARPER TEST -- our bench is not "near a coast on one side", it is RINGED by a thin
# collar on EVERY side. Does stock ever confine a whole wall foot inside a <=12u collar?
print(f"\n-- C2c THE RINGED-COLLAR TEST (is the WHOLE foot inside a thin collar?) " + "-" * 18)
for cap in (12.0, 16.0, 24.0):
    hits = [c for c in comps if c["foot_coast_max"] <= cap]
    hitsT = [c for c in hits if c["walkable_top"]]
    print(f"   components with foot->coast MAX <= {cap:>4.0f}u (no side opens further inland): "
          f"{len(hits):>2} of {len(comps)}  (walkable-top: {len(hitsT)} of {len(TOPPED)})"
          + (f"  -> {[(c['blocks'][:2], c['maxext'], c['foot_coast_max'], c['walkable_top']) for c in hits[:6]]}" if hits else ""))
print(f"   stock foot->coast MAX: med {np.median([c['foot_coast_max'] for c in comps]):.1f}u "
      f"p10 {np.percentile([c['foot_coast_max'] for c in comps], 10):.1f}u "
      f"min {min(c['foot_coast_max'] for c in comps):.1f}u | OURS ~{case_fc_hi}u = "
      f"p{pctl_of([c['foot_coast_max'] for c in comps], case_fc_hi)}")
if donor:
    print(f"   THE DONOR's own seat, by band: {donor['band_frac']} "
          f"(min {donor['foot_coast_min']}u med {donor['foot_coast_med']}u max "
          f"{donor['foot_coast_max']}u) -- 0% of it inside our 6-10u window")

# how many components have a genuinely EMPTY outer annulus (ours are all empty past 8u)?
print(f"\n-- C3b EMPTY-ANNULUS TEST (ours: 0u2 in every annulus past 8u) " + "-" * 26)
for k in ("8-16", "16-32", "32-64"):
    z = [c for c in comps if c["ann"][k] <= 1.0]
    zt = [c for c in z if c["walkable_top"]]
    print(f"   components with ~zero contiguous approach ground in the {k}u annulus: "
          f"{len(z):>2} of {len(comps)}  (walkable-top: {len(zt)} of {len(TOPPED)})")

# ---- HOST COVERAGE (how much of its island the wall eats) ------------------------------------
cov = [(c["coverage"], c) for c in comps if c["coverage"] is not None]
cov.sort(key=lambda q: -q[0])
case_cov = (math.pi * 30.5 * 28.5) / case_island_area
print(f"\n-- HOST COVERAGE (wall plan hull area / host landmass area) " + "-" * 30)
print(f"   stock: med {np.median([q[0] for q in cov]):.3f} p90 "
      f"{np.percentile([q[0] for q in cov], 90):.3f} max {cov[0][0]:.3f} "
      f"(worst: blocks {cov[0][1]['blocks'][:2]} ext {cov[0][1]['aabb']} on a "
      f"{cov[0][1]['host_area']}u2 host)")
print(f"   the 5 hungriest: " +
      "; ".join(f"{q[1]['blocks'][:1]} {q[0]:.2f}" for q in cov[:5]))
print(f"   OURS: {math.pi * 30.5 * 28.5:.0f}u2 hull / {case_island_area:.0f}u2 island = "
      f"{case_cov:.3f} = p{pctl_of([q[0] for q in cov], case_cov)}")

# ---- THE ACTIONABLE MINIMUM HOST (arithmetic from the donor's OWN measured seat) -------------
mw2, ml2 = CASE["mesa_ext"][0] / 2.0, CASE["mesa_ext"][1] / 2.0
half_diag = math.hypot(mw2, ml2)
print(f"\n-- THE MINIMUM HOST for THIS donor, from the donor's own measured seat " + "-" * 18)
print(f"   the mesa's own plan half-extents {mw2:.1f} x {ml2:.1f}u -> half-DIAGONAL {half_diag:.1f}u "
      f"(the corner is the binding radius, and the corner is where the owner sees "
      f"'weird meadowy corner tiles')")
print(f"   bench collar today: {R - max(mw2, ml2):.1f}u at the mid-edges but only "
      f"{R - half_diag:.1f}u at the corners -- matching the stated 6-10u")
if donor:
    need_min, need_med = donor["foot_coast_min"], donor["foot_coast_med"]
    r_floor = half_diag + need_min
    r_med = half_diag + need_med
    r_area = math.sqrt((donor["ann_total"] + math.pi * mw2 * ml2) / math.pi)
    r_a32 = half_diag + 32.0
    print(f"   (a) FLOOR -- clear the donor's own MINIMUM foot->coast ({need_min}u) at the "
          f"corners: island eq radius >= {r_floor:.0f}u (area >= {math.pi * r_floor ** 2:.0f}u2)")
    print(f"   (b) APPROACH-AREA PARITY -- reproduce the donor's {donor['ann_total']:.0f}u2 of "
          f"contiguous approach ground: island eq radius >= {r_area:.0f}u "
          f"(area >= {math.pi * r_area ** 2:.0f}u2)")
    print(f"   (c) MEDIAN-SEAT PARITY -- give the corners the donor's MEDIAN seat "
          f"({need_med}u): island eq radius >= {r_med:.0f}u")
    print(f"   (d) to make the 16-32u annulus non-empty at all: island eq radius >= {r_a32:.0f}u")
    print(f"   TODAY: {R}u. Deficit vs (a) {r_floor - R:+.0f}u, vs (b) {r_area - R:+.0f}u, "
          f"vs (c) {r_med - R:+.0f}u")

print(f"\n-- OUR SIZE CLASS (plan max extent {SIZE_LO}-{SIZE_HI}u AND height {H_LO}-{H_HI}u): "
      f"{len(size_class)} stock components " + "-" * 8)
print(f"   {'blocks':22s} {'ext':>13} {'h':>6} {'foot->coast min/med':>21} "
      f"{'host area':>11} {'eq r':>7} {'blk':>4}  approach 0-8/8-16/16-32/32-64 (u2)")
for c in size_class[:14]:
    print(f"   {str(c['blocks'][:3]):22s} {str(c['aabb']):>13} {c['height']:>6} "
          f"{c['foot_coast_min']:>9}/{c['foot_coast_med']:<11} {c['host_area']:>11} "
          f"{c['host_eq_r']:>7} {c['host_blocks']:>4}  "
          f"{c['ann']['0-8']:.0f}/{c['ann']['8-16']:.0f}/{c['ann']['16-32']:.0f}/{c['ann']['32-64']:.0f}")

print(f"\n-- THE SMALLEST STOCK LANDMASS HOSTING OUR SIZE CLASS " + "-" * 34)
if smallest_hosts:
    c = smallest_hosts[0]
    print(f"   host area {c['host_area']}u2 (eq radius {c['host_eq_r']}u, {c['host_blocks']} blocks, "
          f"extent {tuple(float(q) for q in LM[c["host"]]["ext"])}u, walkable {LM[c['host']]['walk_area']}u2)")
    print(f"   its wall: blocks {c['blocks']} ext {c['aabb']}u h {c['height']}u; foot->coast "
          f"min {c['foot_coast_min']}u med {c['foot_coast_med']}u p90 {c['foot_coast_p90']}u")
    print(f"   the ground around it: 0-8u {c['ann']['0-8']:.0f}u2, 8-16u {c['ann']['8-16']:.0f}u2, "
          f"16-32u {c['ann']['16-32']:.0f}u2, 32-64u {c['ann']['32-64']:.0f}u2 "
          f"(total {c['ann_total']:.0f}u2); foot y span {c['foot_y_span']}u")

print(f"\n-- THE JOINT ENVELOPE TESTS " + "-" * 60)
print(f"   stock components in our size class ON a landmass of eq-radius <= {1.35 * R:.0f}u "
      f"AND foot->coast med <= {case_fc_hi + 4.0:.0f}u:  {len(joint)}")
print(f"   stock components >= 40u extent on ANY landmass of eq-radius <= {1.35 * R:.0f}u: "
      f"{len(loose)}" + (f"  -> {[ (c['blocks'][:2], c['maxext'], c['height'], c['host_eq_r']) for c in loose[:6] ]}" if loose else ""))
print(f"   stock components >= {SIZE_LO}u extent with foot->coast med <= {case_fc_hi}u: "
      f"{len(tight_seat)}" + (f"  -> {[ (c['blocks'][:2], c['maxext'], c['foot_coast_med'], c['host_eq_r']) for c in tight_seat[:6] ]}" if tight_seat else ""))

# smallest landmass that hosts ANY banded wall at all, and the size-vs-host relation
by_host = defaultdict(list)
for c in comps:
    if c["host"]:
        by_host[c["host"]].append(c)
host_rank = sorted(by_host.items(), key=lambda kv: LM[kv[0]]["area"])
print(f"\n-- THE HOST LADDER (smallest landmasses that host ANY banded wall) " + "-" * 22)
print(f"   {'area u2':>10} {'eq r':>7} {'blk':>4} {'nwalls':>7} {'biggest wall ext':>17} "
      f"{'its h':>6} {'foot->coast med':>16}")
for L, cs in host_rank[:12]:
    big = max(cs, key=lambda c: c["maxext"])
    print(f"   {LM[L]['area']:>10} {LM[L]['eq_radius']:>7} {LM[L]['blocks']:>4} {len(cs):>7} "
          f"{str(big['aabb']):>17} {big['height']:>6} {big['foot_coast_med']:>16}")

# the relation a builder can act on: host eq-radius vs biggest wall extent it carries
rel = []
for L, cs in by_host.items():
    big = max(cs, key=lambda c: c["maxext"])
    rel.append((LM[L]["eq_radius"], big["maxext"], LM[L]["area"], big["height"]))
rel.sort()
print(f"\n-- HOST SIZE vs THE BIGGEST WALL IT CARRIES (the actionable relation) " + "-" * 20)
for lo, hi in ((0, 40), (40, 60), (60, 90), (90, 140), (140, 250), (250, 1e9)):
    band = [r for r in rel if lo <= r[0] < hi]
    if band:
        print(f"   host eq-r {lo:>4}-{hi if hi < 1e9 else 'inf':>5}u (n={len(band):>3}): biggest wall "
              f"extent med {np.median([b[1] for b in band]):.0f}u max {max(b[1] for b in band):.0f}u; "
              f"wall/host-radius ratio med {np.median([b[1] / b[0] for b in band]):.2f} "
              f"max {max(b[1] / b[0] for b in band):.2f}")
case_ratio = case_ext / R
print(f"   OUR CASE: wall extent {case_ext}u / host eq-r {R}u = ratio {case_ratio:.2f}")
allratio = [b[1] / b[0] for b in rel]
print(f"   stock wall/host-radius ratio over all {len(rel)} hosts: med "
      f"{np.median(allratio):.2f} p90 {np.percentile(allratio, 90):.2f} "
      f"max {max(allratio):.2f}  -> OURS = p{pctl_of(allratio, case_ratio)}")

# =============================================================================================
# PNG -- the land map, our size class, and the seat comparison
# =============================================================================================
PNG.parent.mkdir(parents=True, exist_ok=True)
SC = 2
W, H = GX * SC, GZ * SC + 120
img = Image.new("RGB", (W, H), (12, 20, 34))
dr = ImageDraw.Draw(img)
for jj in range(GZ):
    for ii in range(GX):
        if not land[jj, ii]:
            continue
        col = (46, 78, 52) if walk[jj, ii] else (86, 82, 74)
        dr.rectangle([ii * SC, jj * SC, ii * SC + SC - 1, jj * SC + SC - 1], fill=col)
for c in comps:                                             # every banded wall, faint
    pts = np.array([q for t in comp_tris[c["root"]] for q in rock_tris[t]], dtype=float)
    dr.rectangle([pts[:, 0].min() / CELL * SC, -pts[:, 2].max() / CELL * SC,
                  pts[:, 0].max() / CELL * SC, -pts[:, 2].min() / CELL * SC],
                 outline=(120, 110, 100))
for c in TOPPED:                                            # the MESA class (plateau/shelf top)
    pts = np.array([q for t in comp_tris[c["root"]] for q in rock_tris[t]], dtype=float)
    dr.rectangle([pts[:, 0].min() / CELL * SC, -pts[:, 2].max() / CELL * SC,
                  pts[:, 0].max() / CELL * SC, -pts[:, 2].min() / CELL * SC],
                 outline=(120, 220, 255), width=2)
for c in size_class:
    # draw the component's plan bbox from its blocks' rock tris (recomputed cheaply)
    pts = np.array([q for t in comp_tris[c["root"]] for q in rock_tris[t]], dtype=float)
    x0, x1 = pts[:, 0].min(), pts[:, 0].max()
    z0, z1 = pts[:, 2].min(), pts[:, 2].max()
    dr.rectangle([x0 / CELL * SC, -z1 / CELL * SC, x1 / CELL * SC, -z0 / CELL * SC],
                 outline=(255, 210, 80))
if donor:
    pts = np.array([q for t in comp_tris[donor["root"]] for q in rock_tris[t]], dtype=float)
    dr.rectangle([pts[:, 0].min() / CELL * SC, -pts[:, 2].max() / CELL * SC,
                  pts[:, 0].max() / CELL * SC, -pts[:, 2].min() / CELL * SC],
                 outline=(255, 90, 90), width=2)
# the bench, to the same scale, bottom-left inset
bx0, by0 = 20, GZ * SC + 20
dr.text((8, GZ * SC + 4), "green = walkable land   grey = land, non-walkable   yellow = our SIZE "
                          "CLASS (50-75u ext, 18-34u h)   red = the DONOR mesa (15,14)",
        fill=(210, 210, 215))
rpx = R / CELL * SC
dr.ellipse([bx0, by0, bx0 + 2 * rpx, by0 + 2 * rpx], outline=(90, 200, 255))
mw, ml = CASE["mesa_ext"]
dr.rectangle([bx0 + rpx - mw / 2 / CELL * SC, by0 + rpx - ml / 2 / CELL * SC,
              bx0 + rpx + mw / 2 / CELL * SC, by0 + rpx + ml / 2 / CELL * SC],
             outline=(255, 90, 90))
dr.text((bx0 + 2 * rpx + 12, by0 + 6), f"THE BENCH, same scale: island eq-r {R}u (cyan) with the "
                                       f"{mw:.0f}x{ml:.0f}u mesa (red)", fill=(160, 200, 240))
dr.text((bx0 + 2 * rpx + 12, by0 + 22), f"wall/host-radius ratio {case_ratio:.2f} vs stock med "
                                        f"{np.median(allratio):.2f} / max {max(allratio):.2f}",
        fill=(160, 200, 240))
img.save(PNG)
print(f"\nrender -> {PNG}")

OUT.write_text(json.dumps(dict(
    meta=dict(blocks_read=nb_read, blocks_unreadable=nb_fail, grid=[GX, GZ], cell=CELL,
              rock_tris=len(rock_tris), raw_components=len(comp_tris),
              banded_components=len(comps), walkable_top=len(TOPPED),
              min_tris=MIN_TRIS, min_yspan=MIN_YSPAN, walkable_topos=sorted(WALKABLE),
              topo_hist={str(k): v for k, v in topo_hist.most_common()},
              runtime_s=round(time.time() - t0, 1)),
    coast_calibration=cal,
    unit_calibration=dict(per_block_crest_seeded_components=blk_comps, over_blocks=blk_blocks,
                          prior_study_reported="76 over 48 (plateau_edge.py, per-block unit)",
                          world_welded_components=len(comps)),
    seat_mode=dict(bands=BKEYS, arc_by_band=band_global,
                   n_components_mostly_in_4_12_window=len(mid),
                   members_mostly_in_window=[list(m[0]) for m in mid]),
    coverage=dict(stock_med=round(float(np.median([q[0] for q in cov])), 3),
                  stock_p90=round(float(np.percentile([q[0] for q in cov], 90)), 3),
                  stock_max=round(cov[0][0], 3), case=round(case_cov, 3),
                  case_pct=pctl_of([q[0] for q in cov], case_cov)),
    minimum_host=(dict(half_diag=round(half_diag, 1),
                       floor_eq_r=round(half_diag + donor["foot_coast_min"], 1),
                       area_parity_eq_r=round(math.sqrt((donor["ann_total"] + math.pi * mw2 * ml2) / math.pi), 1),
                       median_seat_eq_r=round(half_diag + donor["foot_coast_med"], 1),
                       annulus32_eq_r=round(half_diag + 32.0, 1), today_eq_r=R) if donor else None),
    case=dict(**{k: v for k, v in CASE.items()}, island_area=round(case_island_area, 1),
              annuli=case_ann, wall_host_ratio=round(case_ratio, 3)),
    placement=placement,
    size_class=dict(band=[SIZE_LO, SIZE_HI, H_LO, H_HI], n=len(size_class),
                    members=size_class[:40]),
    joint_envelope=dict(n_size_and_small_host_and_tight_seat=len(joint),
                        n_big_wall_on_small_host=len(loose),
                        n_big_wall_tight_seat=len(tight_seat),
                        members_loose=loose[:20], members_tight=tight_seat[:20]),
    host_ladder=[dict(area=LM[L]["area"], eq_r=LM[L]["eq_radius"], blocks=LM[L]["blocks"],
                      ext=LM[L]["ext"], walk_area=LM[L]["walk_area"], nwalls=len(cs),
                      biggest=max(cs, key=lambda c: c["maxext"]))
                 for L, cs in host_rank[:20]],
    donor=donor,
    components=comps,
), indent=0))
print(f"artifacts -> {OUT}")
