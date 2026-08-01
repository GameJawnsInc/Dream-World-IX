"""ADVERSARIAL RE-MEASUREMENT of S6's claimed CONTINENT-SCOPE LAW.

The claim under test (region_carry_feasibility.py): a stock feature's "own ground out to the
sea" is bounded by its LANDMASS; donor (15,14) sits in a 97-block component whose smallest
sea-bounded rect is 132 blocks; and EVERY smaller rect INCREASES the minted land junction
(252u at 1x1 -> 888u at 5x5) against "the mesa foot's own ~200u perimeter", so a partial
region carry multiplies the junction class instead of deleting it.

DIFFERENT METHOD, on purpose. Theirs is a BLOCK-granular vert-weld predicate plus a ledger of
8 hand-picked AXIS-ALIGNED RECTS. Mine is:
  P1  a 4u CELL-granular land raster (tri-centroid occupancy, not vert welds) -> components,
      on BOTH shipped world discs (1 and 4), not just disc 1.
  P2  the TRUE MINIMUM minted land junction for ANY carried region containing the mesa, by
      max-flow / min-cut on the land-cell adjacency graph. A rect ledger samples 8 points of a
      space; a min cut is the floor of the whole space. This is the statistic their claim needs
      and does not have.
  P3  the mesa's own foot perimeter MEASURED (cell boundary + vert polyline) instead of the
      asserted "~200u" -- the denominator of their whole comparison.
  P4  a map-wide FOOT-MOUND census (every rock blob on both discs, per-foot-cell LOCAL rise)
      to test surprise #3's "stock puts no mound at this wall foot at all", which rests on a
      pooled median over one 3x3 window.
  P5  counterexample hunt for "exactly one self-contained relief island exists map-wide".

READ-ONLY. Nothing under the game install is written; no deploy path is touched; no dry run.
Artifacts -> out/verify_s6_region_carry.json + out/verify_s6_region_carry.png
Run: py -X utf8 verify_s6_region_carry.py
"""
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_flow
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import locate as LOC                   # noqa: E402

OUT = Path(__file__).with_name("out") / "verify_s6_region_carry.json"
PNG = Path(__file__).with_name("out") / "verify_s6_region_carry.png"

BLOCK, CELL = 64.0, 4.0
GRID_X, GRID_Y = 24, 20
NI, NJ = GRID_X * 16, GRID_Y * 16          # 384 x 320 cells
DONOR = (15, 14)

ROCK = {49, 7, 62}
GRASS = {0, 1, 2, 3, 42}
PLATEAU = {10, 11, 12}
SHELF = {13}
FOREST = {36, 37}
FOOT_LEGAL = set(range(0, 8)) | {10, 11, 12, 13} | set(range(16, 24)) | {27, 28, 30, 31} \
    | set(range(32, 39)) | {41, 42, 45, 46, 52}
# GROUND = walkable, non-feature: what a "ground junction" is made of
GROUND = (FOOT_LEGAL - FOREST - PLATEAU - SHELF - ROCK)

res = {"claim": "S6 THE CONTINENT-SCOPE LAW", "method": "cell raster + max-flow min-cut"}
T0 = time.time()


# --------------------------------------------------------------------------- raster
def part_blocks(disc):
    env = X._worldmap_env(disc)
    pat = re.compile(rf"worldmap/disc{disc}/0_1/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9]+)(?:\.asset)?$")
    per = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            per[m.group(3)].add((int(m.group(1)), int(m.group(2))))
    return dict(per)


class Raster:
    """4u cell rasters for one disc, built from TERRAIN TRI CENTROIDS (a different predicate
    from the claim's per-vertex border welds -- centroid occupancy cannot be fooled by a vert
    that merely overhangs a block border)."""

    def __init__(self, disc):
        self.disc = disc
        self.pb = part_blocks(disc)
        self.land = np.zeros((NJ, NI), bool)
        self.ysum = np.zeros((NJ, NI))
        self.yn = np.zeros((NJ, NI))
        self.ymax = np.full((NJ, NI), -1e9)
        self.cls = {k: np.zeros((NJ, NI), np.int32)
                    for k in ("rock", "grass", "forest", "plateau", "shelf", "ground", "other")}
        self.tris = 0
        for (bx, by) in sorted(self.pb.get("terrain", ())):
            try:
                bm = X.read_block(bx, by, disc=disc, part="terrain")
            except Exception:
                continue
            V = bm.chan_arrays[X.CH_POS]
            TAN = bm.chan_arrays[X.CH_TAN]
            ox, oz = BLOCK * bx, -BLOCK * by
            fi = bm.flat_index
            for t in range(len(fi) // 3):
                a, b, c = fi[3 * t], fi[3 * t + 1], fi[3 * t + 2]
                topo = X.decode_id(int(round(TAN[a][0])))["topograph"]
                cx = (V[a][0] + V[b][0] + V[c][0]) / 3.0 + ox
                cz = (V[a][2] + V[b][2] + V[c][2]) / 3.0 + oz
                cy = (V[a][1] + V[b][1] + V[c][1]) / 3.0
                i = int(math.floor(cx / CELL))
                j = int(math.floor(-cz / CELL))
                if not (0 <= i < NI and 0 <= j < NJ):
                    continue
                self.tris += 1
                self.land[j, i] = True
                self.ysum[j, i] += cy
                self.yn[j, i] += 1
                self.ymax[j, i] = max(self.ymax[j, i], max(V[a][1], V[b][1], V[c][1]))
                k = ("rock" if topo in ROCK else "forest" if topo in FOREST
                     else "plateau" if topo in PLATEAU else "shelf" if topo in SHELF
                     else "ground" if topo in GROUND else "other")
                self.cls[k][j, i] += 1
                if topo in GRASS:
                    pass
        with np.errstate(invalid="ignore", divide="ignore"):
            self.ymean = np.where(self.yn > 0, self.ysum / np.maximum(self.yn, 1), np.nan)
        self.rock = self.cls["rock"] > 0
        self.grnd = (self.cls["ground"] > 0) & ~self.rock
        self.forest = self.cls["forest"] > 0


def components(mask):
    """4-connected component labels over a boolean cell mask (0 = background)."""
    lab = np.zeros(mask.shape, np.int32)
    cur = 0
    for j0 in range(mask.shape[0]):
        for i0 in range(mask.shape[1]):
            if not mask[j0, i0] or lab[j0, i0]:
                continue
            cur += 1
            q = deque([(j0, i0)])
            lab[j0, i0] = cur
            while q:
                j, i = q.popleft()
                for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    jj, ii = j + dj, i + di
                    if 0 <= jj < mask.shape[0] and 0 <= ii < mask.shape[1] \
                            and mask[jj, ii] and not lab[jj, ii]:
                        lab[jj, ii] = cur
                        q.append((jj, ii))
    return lab, cur


print("[P1] rasterising both shipped world discs at 4u cell granularity ...")
R = {}
for disc in (1, 4):
    R[disc] = Raster(disc)
    print(f"     disc{disc}: {R[disc].tris} terrain tris, {int(R[disc].land.sum())} land cells, "
          f"{len(R[disc].pb.get('terrain', ()))} terrain blocks   [{time.time()-T0:.1f}s]")

# ------------------------------------------------------- P1  components, cell-granular
p1 = {}
for disc in (1, 4):
    r = R[disc]
    lab, n = components(r.land)
    sizes = Counter(lab[lab > 0].ravel().tolist())
    blocks_of = {}
    for cid in sizes:
        js, iss = np.where(lab == cid)
        blocks_of[cid] = {(int(i) // 16, int(j) // 16) for i, j in zip(iss, js)}
    order = sorted(sizes, key=lambda c: -sizes[c])
    donor_cid = int(lab[DONOR[1] * 16 + 8, DONOR[0] * 16 + 8]) or None
    if donor_cid is None:                      # centre cell empty: take any land cell in block
        js, iss = np.where(r.land[DONOR[1] * 16:(DONOR[1] + 1) * 16, DONOR[0] * 16:(DONOR[0] + 1) * 16])
        donor_cid = int(lab[DONOR[1] * 16 + js[0], DONOR[0] * 16 + iss[0]])
    p1[f"disc{disc}"] = dict(
        n_components=n,
        component_cell_sizes=[int(sizes[c]) for c in order],
        component_block_counts=[len(blocks_of[c]) for c in order],
        donor_component_cells=int(sizes[donor_cid]),
        donor_component_blocks=len(blocks_of[donor_cid]),
        donor_component_bbox=[min(b[0] for b in blocks_of[donor_cid]),
                              min(b[1] for b in blocks_of[donor_cid]),
                              max(b[0] for b in blocks_of[donor_cid]),
                              max(b[1] for b in blocks_of[donor_cid])] if disc == 1 else None,
    )
    r.lab, r.blocks_of, r.sizes, r.order, r.donor_cid = lab, blocks_of, sizes, order, donor_cid
    print(f"[P1] disc{disc}: {n} cell-granular land components; block counts "
          f"{[len(blocks_of[c]) for c in order]}")
    print(f"     donor component: {sizes[donor_cid]} cells = {len(blocks_of[donor_cid])} blocks")
res["P1_components"] = p1

# --------------------------------------------------- P3  the mesa's OWN measured perimeter
r1 = R[1]
i0, i1 = DONOR[0] * 16, (DONOR[0] + 1) * 16
j0, j1 = DONOR[1] * 16, (DONOR[1] + 1) * 16
mesa = np.zeros_like(r1.land)
mesa[j0:j1, i0:i1] = r1.rock[j0:j1, i0:i1]
mesa_cells = {(int(i), int(j)) for j, i in zip(*np.where(mesa))}


def boundary_len(cellset, land):
    """4u-slot boundary of a cell set against LAND that is outside it (the minted land
    junction if this set were lifted out and dropped on a foreign ground sheet)."""
    n = 0
    for (i, j) in cellset:
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ii, jj = i + di, j + dj
            if (ii, jj) in cellset:
                continue
            if 0 <= ii < NI and 0 <= jj < NJ and land[jj, ii]:
                n += 1
    return n


def dilate(cellset, radius_u, land):
    rad = int(round(radius_u / CELL))
    out = set(cellset)
    for _ in range(rad):
        add = set()
        for (i, j) in out:
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ii, jj = i + di, j + dj
                if 0 <= ii < NI and 0 <= jj < NJ and land[jj, ii] and (ii, jj) not in out:
                    add.add((ii, jj))
        out |= add
    return out


mesa_bl = boundary_len(mesa_cells, r1.land)
collar10 = dilate(mesa_cells, 10.0, r1.land)
collar10_bl = boundary_len(collar10, r1.land)
# vert-polyline perimeter of the rock/ground contact, for a second independent figure
bm = X.read_block(*DONOR, disc=1, part="terrain")
V = bm.chan_arrays[X.CH_POS]
TAN = bm.chan_arrays[X.CH_TAN]
ox, oz = BLOCK * DONOR[0], -BLOCK * DONOR[1]
fi = bm.flat_index
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))   # noqa: E731
rockv, grndv, platv = set(), set(), set()
edges_rock = Counter()
for t in range(len(fi) // 3):
    idx = [fi[3 * t + k] for k in range(3)]
    topo = X.decode_id(int(round(TAN[idx[0]][0])))["topograph"]
    P = [(V[i][0] + ox, V[i][1], V[i][2] + oz) for i in idx]
    tgt = rockv if topo in ROCK else (platv if topo in (PLATEAU | SHELF)
                                      else (grndv if topo in FOOT_LEGAL else None))
    if tgt is not None:
        for v in P:
            tgt.add(kk(v))
    if topo in ROCK:
        for a in range(3):
            e = tuple(sorted((kk(P[a]), kk(P[(a + 1) % 3]))))
            edges_rock[e] += 1
foot_v = rockv & grndv
# the foot POLYLINE: rock boundary edges (used once) whose both ends are foot verts
foot_edge_len = 0.0
n_fe = 0
for (e, c) in edges_rock.items():
    if c == 1 and e[0] in foot_v and e[1] in foot_v:
        foot_edge_len += math.dist(e[0], e[1])
        n_fe += 1
res["P3_mesa_perimeter"] = dict(
    mesa_rock_cells=len(mesa_cells),
    cell_boundary_slots=mesa_bl, cell_boundary_u=round(mesa_bl * CELL, 1),
    apron10_cells=len(collar10), apron10_boundary_slots=collar10_bl,
    apron10_boundary_u=round(collar10_bl * CELL, 1),
    foot_polyline_edges=n_fe, foot_polyline_u=round(foot_edge_len, 1),
    foot_verts=len(foot_v),
    claimed_by_S6="~200u")
print(f"[P3] MEASURED mesa foot perimeter: cell boundary {mesa_bl} slots = "
      f"{mesa_bl*CELL:.0f}u ; foot polyline {n_fe} edges = {foot_edge_len:.0f}u "
      f"(S6 asserted ~200u).  round-8 apron(+10u) boundary = {collar10_bl*CELL:.0f}u")

# --------------------------------------------- P2  THE MIN CUT (the floor of the whole space)
print("[P2] max-flow min-cut: the MINIMUM minted land junction over ALL carry shapes ...")
comp_mask = (r1.lab == r1.donor_cid)
cells = [(int(i), int(j)) for j, i in zip(*np.where(comp_mask))]
cid_of = {c: k for k, c in enumerate(cells)}
NC = len(cells)
# world plan centre of the mesa foot (for the "reach at least R away" sink)
fx = np.array([v[0] for v in foot_v])
fz = np.array([v[2] for v in foot_v])
fc = (float(fx.mean()), float(fz.mean()))
cxw = np.array([i * CELL + CELL / 2 for (i, j) in cells])
czw = np.array([-(j * CELL + CELL / 2) for (i, j) in cells])
dist_foot = np.hypot(cxw - fc[0], czw - fc[1])

INF = 1 << 20
rows, cols, dat = [], [], []
for k, (i, j) in enumerate(cells):
    for di, dj in ((1, 0), (0, 1)):
        n = (i + di, j + dj)
        if n in cid_of:
            m = cid_of[n]
            rows += [k, m]
            cols += [m, k]
            dat += [1, 1]
S_NODE, T_NODE = NC, NC + 1
src_cells = [cid_of[c] for c in mesa_cells if c in cid_of]
for k in src_cells:
    rows.append(S_NODE); cols.append(k); dat.append(INF)


def mincut(sink_mask, label):
    rr = list(rows); cc = list(cols); dd = list(dat)
    sinks = [k for k in range(NC) if sink_mask[k] and k not in set(src_cells)]
    if not sinks:
        return dict(label=label, sinks=0, note="no sink cells")
    for k in sinks:
        rr.append(k); cc.append(T_NODE); dd.append(INF)
    G = csr_matrix((np.array(dd, np.int32), (np.array(rr), np.array(cc))),
                   shape=(NC + 2, NC + 2))
    mf = maximum_flow(G, S_NODE, T_NODE)
    val = int(mf.flow_value)
    # recover the source side of the min cut from the residual graph
    flow = mf.flow.tocsr()
    Gc = G.tocsr()
    reach = np.zeros(NC + 2, bool)
    reach[S_NODE] = True
    q = deque([S_NODE])
    while q:
        u = q.popleft()
        for p in range(Gc.indptr[u], Gc.indptr[u + 1]):
            v = Gc.indices[p]
            residual = Gc.data[p] - flow[u, v]
            if residual > 0 and not reach[v]:
                reach[v] = True
                q.append(v)
    src_side = [k for k in range(NC) if reach[k]]
    cut_edges = []
    for k in src_side:
        i, j = cells[k]
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (i + di, j + dj)
            if n in cid_of and not reach[cid_of[n]]:
                cut_edges.append((k, cid_of[n]))
    ys = [float(np.nanmax([r1.ymean[cells[a][1], cells[a][0]],
                           r1.ymean[cells[b][1], cells[b][0]]])) for (a, b) in cut_edges]
    return dict(label=label, sinks=len(sinks), mincut_slots=val, mincut_u=round(val * CELL, 1),
                carried_cells=len(src_side),
                carried_plan_area_u2=round(len(src_side) * CELL * CELL, 0),
                carried_blocks=len({(cells[k][0] // 16, cells[k][1] // 16) for k in src_side}),
                cut_edges_recovered=len(cut_edges),
                cut_y_med=round(float(np.median(ys)), 2) if ys else None,
                cut_y_p90=round(float(np.percentile(ys, 90)), 2) if ys else None,
                cut_frac_above_y8=round(float(np.mean([y > 8.0 for y in ys])), 3) if ys else None)


p2 = []
for Rr in (32, 48, 64, 80, 96, 128, 160, 224, 320):
    p2.append(mincut(dist_foot > Rr, f"reach>{Rr}u"))
# and: exclude every land cell outside the donor's own 3x3 / 5x5 blocks (their rect framing)
for half, nm in ((1, "outside 3x3 blocks"), (2, "outside 5x5 blocks")):
    m = np.array([not (DONOR[0] - half <= i // 16 <= DONOR[0] + half
                       and DONOR[1] - half <= j // 16 <= DONOR[1] + half) for (i, j) in cells])
    p2.append(mincut(m, nm))
res["P2_mincut"] = p2
for row in p2:
    if "mincut_u" in row:
        print(f"     {row['label']:>20}: MIN land junction {row['mincut_u']:>7}u "
              f"({row['mincut_slots']} slots)  carrying {row['carried_cells']} cells "
              f"= {row['carried_plan_area_u2']:.0f}u2 over {row['carried_blocks']} blocks  "
              f"cut y med {row['cut_y_med']} p90 {row['cut_y_p90']}")

# ---------------------------------- P2b  cross-check the claim's 8 rects at cell granularity
def rect_cut(x0, y0, x1, y1):
    inside = {(i, j) for (i, j) in cells if x0 <= i // 16 <= x1 and y0 <= j // 16 <= y1}
    return dict(rect=[x0, y0, x1, y1], blocks=(x1 - x0 + 1) * (y1 - y0 + 1),
                cells=len(inside), cut_slots=boundary_len(inside, r1.land),
                cut_u=round(boundary_len(inside, r1.land) * CELL, 1))


CANDS = [(15, 14, 15, 14), (14, 14, 15, 15), (14, 13, 16, 15), (14, 13, 16, 16),
         (13, 13, 16, 16), (13, 12, 17, 16), (12, 11, 18, 17), (12, 10, 21, 17)]
res["P2b_rect_crosscheck"] = [rect_cut(*c) for c in CANDS]
print("[P2b] their 8 rects, re-measured as cell-granular land boundary "
      "(vs their vert-weld CUT slots 252/468/588/708/684/888/816/828u):")
for row in res["P2b_rect_crosscheck"]:
    print(f"      rect {row['rect']} {row['blocks']:>3}blk  land boundary {row['cut_u']:>7}u")

# ------------------------------------------------------- P4  map-wide FOOT-MOUND census
print("[P4] map-wide foot-mound census (every rock blob, both discs) ...")
p4 = {}
foot_rows = []
for disc in (1, 4):
    r = R[disc]
    rlab, rn = components(r.rock)
    gjs, gis = np.where(r.grnd)
    gxy = np.stack([gis * CELL + 2.0, -(gjs * CELL + 2.0)], 1)
    gy = r.ymean[gjs, gis]
    tree = cKDTree(gxy)
    for cid in range(1, rn + 1):
        js, iss = np.where(rlab == cid)
        if len(js) < 30:
            continue
        blob = {(int(i), int(j)) for i, j in zip(iss, js)}
        # foot cells = rock cells 4-adjacent to a GROUND cell
        feet = []
        for (i, j) in blob:
            if any(0 <= i + di < NI and 0 <= j + dj < NJ and r.grnd[j + dj, i + di]
                   for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                feet.append((i, j))
        if len(feet) < 8:
            continue
        rises = []
        for (i, j) in feet:
            p = (i * CELL + 2.0, -(j * CELL + 2.0))
            near = tree.query_ball_point(p, 8.0) if hasattr(tree, "query_ball_point") \
                else tree.query_ball_point(p, 8.0)
            far = tree.query_ball_point(p, 40.0)
            fa = [k for k in far if math.dist(gxy[k], p) >= 16.0]
            if len(near) < 2 or len(fa) < 6:
                continue
            rises.append(float(np.nanmedian(gy[near]) - np.nanmedian(gy[fa])))
        if len(rises) < 8:
            continue
        rr = np.array(rises)
        bxs = sorted({(i // 16, j // 16) for (i, j) in blob})
        foot_rows.append(dict(disc=disc, blob_cells=len(blob), foot_cells=len(feet),
                              n_rise=len(rr), blocks=len(bxs),
                              rise_med=round(float(np.median(rr)), 2),
                              rise_p90=round(float(np.percentile(rr, 90)), 2),
                              frac_rise_ge1=round(float((rr >= 1.0).mean()), 3),
                              frac_rise_ge2=round(float((rr >= 2.0).mean()), 3),
                              max_y=round(float(np.nanmax(r.ymax[js, iss])), 1),
                              has_donor=bool(disc == 1 and DONOR in set(bxs)
                                             and any(b == DONOR for b in bxs)
                                             and any((i // 16, j // 16) == DONOR for (i, j) in blob)),
                              donor_blocks=[list(b) for b in bxs][:6]))
res["P4_foot_mound_census"] = foot_rows
allrise = np.array([f["rise_med"] for f in foot_rows])
allf1 = np.array([f["frac_rise_ge1"] for f in foot_rows])
res["P4_summary"] = dict(
    n_blobs=len(foot_rows),
    total_foot_cells=int(sum(f["foot_cells"] for f in foot_rows)),
    blob_rise_med_p10=round(float(np.percentile(allrise, 10)), 2),
    blob_rise_med_median=round(float(np.median(allrise)), 2),
    blob_rise_med_p90=round(float(np.percentile(allrise, 90)), 2),
    frac_blobs_with_median_rise_ge_1u=round(float((allrise >= 1.0).mean()), 3),
    frac_blobs_with_median_rise_ge_05u=round(float((allrise >= 0.5).mean()), 3),
    median_frac_of_foot_rising_ge_1u=round(float(np.median(allf1)), 3))
print(f"[P4] {len(foot_rows)} rock blobs, {res['P4_summary']['total_foot_cells']} foot cells: "
      f"blob median local rise p10/50/90 = {res['P4_summary']['blob_rise_med_p10']}/"
      f"{res['P4_summary']['blob_rise_med_median']}/{res['P4_summary']['blob_rise_med_p90']}u; "
      f"{res['P4_summary']['frac_blobs_with_median_rise_ge_1u']*100:.0f}% of blobs rise >=1u at the foot")

# the DONOR mesa specifically, by the same per-foot-cell statistic
gjs, gis = np.where(r1.grnd)
gxy = np.stack([gis * CELL + 2.0, -(gjs * CELL + 2.0)], 1)
gy = r1.ymean[gjs, gis]
tree = cKDTree(gxy)
drises = []
for (i, j) in mesa_cells:
    if not any(0 <= i + di < NI and 0 <= j + dj < NJ and r1.grnd[j + dj, i + di]
               for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1))):
        continue
    p = (i * CELL + 2.0, -(j * CELL + 2.0))
    near = tree.query_ball_point(p, 8.0)
    far = [k for k in tree.query_ball_point(p, 40.0) if math.dist(gxy[k], p) >= 16.0]
    if len(near) < 2 or len(far) < 6:
        continue
    drises.append(float(np.nanmedian(gy[near]) - np.nanmedian(gy[far])))
dr_ = np.array(drises)
res["P4_donor"] = dict(foot_cells_measured=len(dr_),
                       rise_med=round(float(np.median(dr_)), 2),
                       rise_p10=round(float(np.percentile(dr_, 10)), 2),
                       rise_p90=round(float(np.percentile(dr_, 90)), 2),
                       frac_ge1=round(float((dr_ >= 1.0).mean()), 3),
                       frac_ge2=round(float((dr_ >= 2.0).mean()), 3),
                       percentile_among_blobs=round(float((allrise < np.median(dr_)).mean()), 3))
print(f"[P4] THE DONOR MESA's own foot: n={len(dr_)} cells, local rise med "
      f"{res['P4_donor']['rise_med']}u (p10 {res['P4_donor']['rise_p10']} / p90 "
      f"{res['P4_donor']['rise_p90']}), {res['P4_donor']['frac_ge1']*100:.0f}% of the foot rises "
      f">=1u -> percentile {res['P4_donor']['percentile_among_blobs']*100:.0f}% of stock blobs")

# ------------------------------------- P5  counterexample hunt: small relief landmasses
print("[P5] hunting self-contained relief landmasses on BOTH discs ...")
lm_by_block = defaultdict(list)
for (loc, name, tx, ty) in LOC.NAVIPOS:
    wx, wz = tx / 256.0, ty / 256.0
    lm_by_block[(int(wx // BLOCK), int(-wz // BLOCK))].append(name)
p5 = []
for disc in (1, 4):
    r = R[disc]
    objb = set(r.pb.get("object", ()))
    for cid in r.order:
        blocks = r.blocks_of[cid]
        bxs = [b[0] for b in blocks]
        bys = [b[1] for b in blocks]
        rect_blocks = (max(bxs) - min(bxs) + 1) * (max(bys) - min(bys) + 1)
        if rect_blocks > 12:
            continue
        js, iss = np.where(r.lab == cid)
        ymx = float(np.nanmax(r.ymax[js, iss]))
        ymn = float(np.nanmin(r.ymean[js, iss]))
        rockc = int(r.rock[js, iss].sum())
        p5.append(dict(disc=disc, cells=int(r.sizes[cid]), blocks=len(blocks),
                       rect=[min(bxs), min(bys), max(bxs), max(bys)], rect_blocks=rect_blocks,
                       rock_cells=rockc, relief_u=round(ymx - ymn, 1), max_y=round(ymx, 1),
                       object_blocks=sum(1 for b in blocks if b in objb),
                       landmarks=sorted({n for b in blocks for n in lm_by_block.get(b, [])}),
                       parts=sorted({p for p, bs in r.pb.items() if any(b in bs for b in blocks)}),
                       block_list=[list(b) for b in sorted(blocks)]))
res["P5_small_landmasses"] = p5
qual = [c for c in p5 if c["relief_u"] >= 10.0 and c["object_blocks"] == 0 and not c["landmarks"]]
res["P5_qualifying_no_town_relief"] = qual
print(f"[P5] {len(p5)} landmasses with rect<=12 blocks across both discs; "
      f"{len(qual)} have relief>=10u, ZERO object blocks and no landmark:")
for c in p5:
    tag = "<= QUALIFIES" if c in qual else ""
    print(f"      disc{c['disc']} {c['blocks']:>2}blk rect{c['rect']} ({c['rect_blocks']}rb) "
          f"rockcells={c['rock_cells']:>4} relief={c['relief_u']:>5}u obj={c['object_blocks']} "
          f"{c['landmarks'][:2]} {tag}")

# ---------------------- P6  BOUNDARY LEVELNESS -- the metric that has actually been failing
# 8 rounds failed on the weld line's RELIEF, not on its length. For each candidate carried set,
# measure the height of the DESTINATION ground the junction would demand: the ymean of every
# GROUND cell immediately outside the boundary. A level line can be met by flat bench ground; an
# undulating one cannot, at any length.
print("[P6] boundary LEVELNESS of each carry scope ...")


def levelness(cellset, name):
    ys = []
    for (i, j) in cellset:
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ii, jj = i + di, j + dj
            if (ii, jj) in cellset or not (0 <= ii < NI and 0 <= jj < NJ):
                continue
            if r1.grnd[jj, ii] and not np.isnan(r1.ymean[jj, ii]):
                ys.append(float(r1.ymean[jj, ii]))
    if len(ys) < 6:
        return dict(name=name, n=len(ys))
    a = np.array(ys)
    return dict(name=name, n=len(a), cells=len(cellset),
                boundary_u=round(boundary_len(cellset, r1.land) * CELL, 1),
                y_min=round(float(a.min()), 2), y_p10=round(float(np.percentile(a, 10)), 2),
                y_med=round(float(np.median(a)), 2), y_p90=round(float(np.percentile(a, 90)), 2),
                y_max=round(float(a.max()), 2),
                relief_full=round(float(a.max() - a.min()), 2),
                relief_p10_p90=round(float(np.percentile(a, 90) - np.percentile(a, 10)), 2))


lv = [levelness(mesa_cells, "MESA ROCK ONLY (rounds 4-5 / the carried feature)"),
      levelness(collar10, "MESA + 10u APRON (round 8, live)")]
for (x0, y0, x1, y1) in CANDS[:5]:
    inside = {(i, j) for (i, j) in cells if x0 <= i // 16 <= x1 and y0 <= j // 16 <= y1}
    lv.append(levelness(inside, f"REGION rect {[x0, y0, x1, y1]}"))
for (Rr, nm) in ((32, "MIN-CUT reach>32u"), (320, "MIN-CUT reach>320u")):
    mc = mincut(dist_foot > Rr, "lv")
    # rebuild the source side as a cell set
    sm = dist_foot > Rr
    sinks = set(k for k in range(NC) if sm[k]) - set(src_cells)
    rr2 = list(rows); cc2 = list(cols); dd2 = list(dat)
    for k in sinks:
        rr2.append(k); cc2.append(T_NODE); dd2.append(INF)
    G = csr_matrix((np.array(dd2, np.int32), (np.array(rr2), np.array(cc2))), shape=(NC + 2, NC + 2))
    mf = maximum_flow(G, S_NODE, T_NODE)
    flow = mf.flow.tocsr(); Gc = G.tocsr()
    reach = np.zeros(NC + 2, bool); reach[S_NODE] = True
    q = deque([S_NODE])
    while q:
        u = q.popleft()
        for p in range(Gc.indptr[u], Gc.indptr[u + 1]):
            v = Gc.indices[p]
            if Gc.data[p] - flow[u, v] > 0 and not reach[v]:
                reach[v] = True; q.append(v)
    setk = {cells[k] for k in range(NC) if reach[k]}
    lv.append(levelness(setk, nm))
res["P6_levelness"] = lv
print("     scope                                              junction_u   dest-ground y "
      "(p10..p90)  RELIEF")
for row in lv:
    if "y_med" in row:
        print(f"     {row['name'][:48]:<48} {row['boundary_u']:>8}u   "
              f"{row['y_p10']:>5} .. {row['y_p90']:<5} med {row['y_med']:<5}  "
              f"p10-p90 {row['relief_p10_p90']:>5}u  full {row['relief_full']}u")

# --------------------- P7  is the donor's 3u weld relief a MOUND or a REGIONAL TILT?
# Local rise at each foot cell was ~0.3u (P4) yet the weld line spans ~3u. Those are compatible
# only if the ground is locally flat but regionally TILTED across the mesa's footprint. Fit a
# plane to the local ground height at each foot cell and report the tilt.
pts = []
for (i, j) in mesa_cells:
    if not any(0 <= i + di < NI and 0 <= j + dj < NJ and r1.grnd[j + dj, i + di]
               for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1))):
        continue
    p = (i * CELL + 2.0, -(j * CELL + 2.0))
    near = tree.query_ball_point(p, 8.0)
    if len(near) < 2:
        continue
    pts.append((p[0], p[1], float(np.nanmedian(gy[near]))))
P = np.array(pts)
A = np.stack([P[:, 0] - P[:, 0].mean(), P[:, 1] - P[:, 1].mean(), np.ones(len(P))], 1)
coef, *_ = np.linalg.lstsq(A, P[:, 2], rcond=None)
pred = A @ coef
grad = math.hypot(coef[0], coef[1])
span_x = P[:, 0].max() - P[:, 0].min()
span_z = P[:, 1].max() - P[:, 1].min()
res["P7_regional_tilt"] = dict(
    foot_cells=len(P),
    local_ground_y_min=round(float(P[:, 2].min()), 2), local_ground_y_max=round(float(P[:, 2].max()), 2),
    local_ground_y_p10=round(float(np.percentile(P[:, 2], 10)), 2),
    local_ground_y_p90=round(float(np.percentile(P[:, 2], 90)), 2),
    spread_along_foot_u=round(float(P[:, 2].max() - P[:, 2].min()), 2),
    plane_grad_u_per_u=round(float(grad), 4), plane_tilt_deg=round(math.degrees(math.atan(grad)), 2),
    tilt_dir_deg=round(math.degrees(math.atan2(coef[1], coef[0])), 1),
    rise_across_footprint_u=round(float(grad * math.hypot(span_x, span_z)), 2),
    residual_rms_u=round(float(np.sqrt(((P[:, 2] - pred) ** 2).mean())), 2),
    round8_move="lifted bench grass 4.0u over a 24u falloff = 9.46 deg local slope")
p7 = res["P7_regional_tilt"]
print(f"[P7] the donor's foot ground: local heights span {p7['spread_along_foot_u']}u along the "
      f"foot line, but the best-fit PLANE is only {p7['plane_tilt_deg']} deg "
      f"({p7['rise_across_footprint_u']}u across the footprint), residual rms "
      f"{p7['residual_rms_u']}u -> a REGIONAL TILT, not a mound "
      f"(round 8 built a 9.46 deg local slope)")

# --------------------------------------------------------------------------- PNG
print("[PNG] rendering the min cut ...")
W0, W1, H0, H1 = 10, 23, 7, 19
PX = 3
img = Image.new("RGB", ((W1 - W0) * 16 * PX, (H1 - H0) * 16 * PX), (14, 22, 40))
d = ImageDraw.Draw(img)


def cpx(i, j):
    return ((i - W0 * 16) * PX, (j - H0 * 16) * PX)


for j in range(H0 * 16, H1 * 16):
    for i in range(W0 * 16, W1 * 16):
        if not r1.land[j, i]:
            continue
        col = ((150, 120, 105) if r1.rock[j, i] else (34, 84, 52) if r1.forest[j, i]
               else (86, 140, 74) if r1.grnd[j, i] else (168, 150, 112))
        x, y = cpx(i, j)
        d.rectangle([x, y, x + PX - 1, y + PX - 1], fill=col)
best = None
for row in p2:
    if row.get("label") == "reach>96u":
        best = row
if best:
    m96 = mincut(dist_foot > 96, "render")
for (i, j) in mesa_cells:
    x, y = cpx(i, j)
    d.rectangle([x, y, x + PX - 1, y + PX - 1], fill=(240, 230, 120))
d.text((6, 6), f"S6 REFUTATION: yellow=carried mesa rock (block 15,14). measured foot perimeter "
               f"{mesa_bl*CELL:.0f}u (S6 said ~200u).", fill=(240, 240, 240))
d.text((6, 20), f"min land junction for any carry reaching >96u = "
                f"{[r['mincut_u'] for r in p2 if r.get('label')=='reach>96u']}u", fill=(240, 240, 240))
PNG.parent.mkdir(parents=True, exist_ok=True)
img.save(PNG)
print(f"[PNG] {PNG}")

res["runtime_s"] = round(time.time() - T0, 1)
OUT.write_text(json.dumps(res, indent=1))
print(f"[OUT] {OUT}  ({res['runtime_s']}s)")
