"""THE TERRACE WALL, rung T1 -- the registered prediction's test (TERRACE-WALL-PREDICTION.md).

One free-standing terrace: a topo-13 grass shelf plateau (y 17.0, inside stock's pinned
15.7-18.3 band) ringed by THREE stacked rock courses (~4.6u faces, inside the stacked-wall
4-10u language) descending crest -> body -> foot onto the lowland grass of the Disc9 bench
island at (416,-512). No ramp -- stock has no ramp class; the two levels are deliberately
not connected on foot.

Geometry = the SPUR mechanism generalized to a CLOSED ring (no end fans, no tangent-exit):
  * the plateau TOP is lattice-quantized: full 4u cells as quads, boundary cells clipped
    against the blob polygon (Sutherland-Hodgman per cell -- THE CELL CLIP law; no tri
    spans a cell);
  * the FOOT follows the lattice: kept-grass tris under the footprint drop, and the foot
    course zips (greedy bridge walk) from the jagged kept|dropped hole outline -- real feet
    follow the lattice, a smoothed line is off-language;
  * the CREST course zips the top's own boundary verts (identity weld) to the first clean
    station ring; the middle course is clean station quads.

UVs = the decoded interior rock-wall TILE LANGUAGE (out/rock_tiles.json, 8945 groups):
one 128px tile window per (course, column); role bands crest rows 3-4 x cols 4-7 / body
rows 6-9 x cols 0-3 / foot rows 7-10 x cols 6-9 (true foot row 10); u-continuation by +-1
col steps with band wrap + occasional same-tile repeats (the measured 46%+11% regime);
dual-phase stagger between courses. Tile V-ORIENTATION is calibrated from REAL exemplar
quads read out of the decode's own top stock blocks -- never assumed from the catalogue.

ROUND 3 (the remaining prediction round) rebuilds the tile layer on THE THREE INSTANCE LAWS
(`rock_wall_instances.py`, 2026-07-30): LAW 3 -- a wall column is one MEASURED vertical
chain foot -> body -> crest from the transition table (gated; round 1 tiled the courses
independently and read as "stamped together"); LAW 1 -- v-orientation per tile from the
stock MAJORITY, never one exemplar (round 1's flipped tiles); LAW 2 -- u-mirroring per
column at the measured p=0.12 (round 1 coin-flipped). The plateau top reuses junction L3
(`uvf_fix2.assign_mains_seeded` seeded with (quad,ori) decoded from the bench's own kept
grass) -- never a uniform-random draw (round 1's banding). Zip winding comes from the
chain-edge tangent (right-of-CCW-travel), exact on concave lattice jags -- an inverted
visible tri backface-culls in game as a hole while the once-edge audit stays balanced
(round 1's missing faces).

Gates before any write: one-window per tri, data-driven tile roles, THE LAW-3 chain gate,
the winding gate, watertight (0 new once-edges), drop completeness, census MISS=0, the
moat/coast margin, plus face renders (4 compass segments) + stock control strips through
the identical eye. --apply deploys to Disc9 (backing the bench cells up under the MAIN
repo's backups/) only when green.

Run from the repo root:  py -X utf8 studies/path-d-new-world/terrace_wall_t1.py [--apply]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit import config                                # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402
from ff9mapkit.world import interior as IN                  # noqa: E402
from ff9mapkit.world import mesh as M                       # noqa: E402

GAME = Path(config.find_game_path(None))
MOD = "FF9CustomMap-world"
DISC = 9
CELLS = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]    # the bench island's blocks
CENTER = (416.0, -512.0)
BLOCK, CELL = 64.0, 4.0
TILE_U, TILE_V = 0.0625, 0.03125
SEED = 7001

TOP_Y = 17.0                                                # stock shelf band 15.7-18.3
COURSE_Y = [17.0, 12.4, 7.8]                                # crest / ring1 / ring2 tops
RUN = 1.4                                                   # per-course outward run (~73 deg)
R_PLAT = 14.0                                               # plateau blob base radius
DROP_R_EXTRA = 3.6                                          # grass drop reach beyond the blob --
                                                            # keeps the foot faces near the 73-deg
                                                            # language instead of a flat skirt
STATION = 4.4                                               # column width target (u)
GRASS_TOPO = {0, 1, 2, 3, 42}
ROCK = 49
SHELF = 13
BANDS = {                                                   # course role -> (rows, cols)
    "crest": ((3, 4), (4, 5, 6, 7)),
    "body": ((6, 7, 8, 9), (0, 1, 2, 3)),
    "foot": ((7, 8, 9, 10), (6, 7, 8, 9)),
}
FOOT_ROW = 10
OUTD = HERE / "out" / "terrace_t1"
DECODE = ROOT / "studies" / "overworld-topography" / "out" / "rock_tiles.json"

kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))   # noqa: E731


# ---------------------------------------------------------------- load the deployed bench
def load_bench():
    root = GAME / MOD / "FF9_Data" / "WorldMap" / f"Disc{DISC}" / "0_1"
    tris, bms = [], {}
    for (bx, by) in CELLS:
        p = root / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if not p.is_file():
            continue
        bm = M.blockmesh_from_ff9mesh(p, disc=DISC, x=bx, y=by, part="terrain")
        bms[(bx, by)] = (p, bm)
        pos = bm.chan_arrays[X.CH_POS]
        nrm = bm.chan_arrays[X.CH_NRM]
        uv = bm.chan_arrays[X.CH_UV]
        tan = bm.chan_arrays[X.CH_TAN]
        ox, oz = BLOCK * bx, -BLOCK * by
        for t in bm.tris:
            w = [(pos[i][0] + ox, pos[i][1], pos[i][2] + oz) for i in t]
            topo = X.decode_id(int(round(tan[t[0]][0])))["topograph"]
            tris.append(dict(blk=(bx, by), w=w, n=[list(nrm[i]) for i in t],
                             uv=[list(uv[i]) for i in t], tan=[list(tan[i]) for i in t],
                             topo=topo,
                             cen=tuple(np.mean([w[k][j] for k in range(3)]) for j in range(3))))
    return tris, bms


# ---------------------------------------------------------------- the plateau blob + rings
def blob_poly(seed, n=64):
    rng = random.Random(seed)
    ph1, ph2 = rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi)
    pts = []
    for i in range(n):
        th = 2 * math.pi * i / n
        r = R_PLAT * (1 + 0.12 * math.sin(3 * th + ph1) + 0.07 * math.sin(5 * th + ph2))
        pts.append((CENTER[0] + r * math.cos(th), CENTER[1] + r * math.sin(th)))
    return pts


def poly_area2(pg):
    """Shoelace area over (x, z) pairs (2- or 3-component points)."""
    s = 0.0
    for i in range(len(pg)):
        p, q = pg[i], pg[(i + 1) % len(pg)]
        s += p[0] * q[-1] - q[0] * p[-1]
    return abs(s) / 2.0


def poly_clip_slivers(poly, a_min=0.3):
    """True if any boundary-cell clip of the outline is a KNIFE SLIVER (area < a_min u²) --
    the actual failure a tangent-grazing outline mints (degree-4 boundary knots, the
    lattice cousin of THE TANGENT-EXIT TRAP). The mint owns its seed; pick one that
    produces no sliver."""
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    x = math.floor(min(xs) / CELL) * CELL
    while x < max(xs):
        z = math.floor(min(zs) / CELL) * CELL
        while z < max(zs):
            corners = [(x, z), (x + CELL, z), (x + CELL, z + CELL), (x, z + CELL)]
            ins = [pinp(px, pz, poly) for (px, pz) in corners]
            if any(ins) and not all(ins):
                pg = clip_cell(poly, x, z)
                if pg and poly_area2(pg) < a_min:
                    return True
            z += CELL
        x += CELL
    return False


def poly_radius(poly, th):
    """Star-shaped radius of the poly at bearing th (linear in vertex angle)."""
    n = len(poly)
    a = (th % (2 * math.pi)) / (2 * math.pi) * n
    i0 = int(a) % n
    i1 = (i0 + 1) % n
    f = a - int(a)
    r0 = math.hypot(poly[i0][0] - CENTER[0], poly[i0][1] - CENTER[1])
    r1 = math.hypot(poly[i1][0] - CENTER[0], poly[i1][1] - CENTER[1])
    return r0 * (1 - f) + r1 * f


def ring_at(poly, out, y, n_st, phase=0.0):
    """n_st stations on the poly radially offset outward by `out`, at height y."""
    pts = []
    for i in range(n_st):
        th = 2 * math.pi * (i + phase) / n_st
        r = poly_radius(poly, th) + out
        pts.append((CENTER[0] + r * math.cos(th), y, CENTER[1] + r * math.sin(th)))
    return pts


def pinp(px, pz, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        (x1, z1), (x2, z2) = poly[i], poly[(i + 1) % n]
        if (z1 > pz) != (z2 > pz) and px < (x2 - x1) * (pz - z1) / (z2 - z1) + x1:
            inside = not inside
    return inside


def clip_cell(poly, cx0, cz0):
    """Sutherland-Hodgman: the blob poly clipped to lattice cell [cx0,cx0+4]x[cz0,cz0+4]."""
    out = [(p[0], p[1]) for p in poly]
    for (ax, side) in ((0, cx0), (0, cx0 + CELL), (1, cz0), (1, cz0 + CELL)):
        if not out:
            return []
        keepge = side in (cx0, cz0)
        nxt = []
        for i in range(len(out)):
            a, b = out[i], out[(i + 1) % len(out)]
            ain = (a[ax] >= side) if keepge else (a[ax] <= side)
            bin_ = (b[ax] >= side) if keepge else (b[ax] <= side)
            if ain:
                nxt.append(a)
            if ain != bin_:
                t = (side - a[ax]) / (b[ax] - a[ax])
                nxt.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        out = nxt
    return out


def centroid_fan(pg):
    """Triangulate a CONVEX polygon by fanning from its centroid. Collinear runs on the
    boundary (T-split insertions, clip corners) produce no degenerate triangle this way,
    and the centroid is interior so no new T-junction can appear on any outer edge."""
    pg = list(pg)
    if len(pg) == 3:
        return [tuple(pg)]
    cx = sum(p[0] for p in pg) / len(pg)
    cz = sum(p[-1] for p in pg) / len(pg)
    c = (cx, cz) if len(pg[0]) == 2 else (cx, pg[0][1], cz)
    return [(c, pg[i], pg[(i + 1) % len(pg)]) for i in range(len(pg))]


# ---------------------------------------------------------------- tile windows + exemplars
ANATOMY = ROOT / "studies" / "overworld-topography" / "out" / "rock_tile_instances.json"


def load_language():
    d = json.loads(DECODE.read_text())
    pu, pv = d["phase"]
    tiles = {tuple(int(v) for v in k.split(",")): n for k, n in d["tiles"].items()}
    blocks = defaultdict(int)
    for g in d["groups"]:
        blocks[tuple(g["blk"])] += 1
    top_blocks = [b for b, _ in sorted(blocks.items(), key=lambda kv: -kv[1])[:6]]
    return pu, pv, tiles, top_blocks


def load_anatomy():
    """The three instance laws (rock_wall_instances.py, 2026-07-30) as usable tables:
    per-tile majority v-orientation (LAW 1), the vertical transition table + per-tile
    crest/base roles (LAW 3). LAW 2's 12% mirror rate is applied at plan time."""
    d = json.loads(ANATOMY.read_text())
    v_votes = defaultdict(list)
    crest_n = Counter()
    base_n = Counter()
    n_inst = Counter()
    for inst in d["instances"]:
        t = tuple(inst["tile"])
        n_inst[t] += 1
        if abs(inst["v_corr"]) >= 0.3 and inst["yspan"] >= 1.0:
            v_votes[t].append(inst["v_corr"])
        if inst["crest_touch"]:
            crest_n[t] += 1
        if inst["base_touch"]:
            base_n[t] += 1
    v_up = {}                                               # True = atlas v DECREASES upward
    for t, cs in v_votes.items():
        up = sum(1 for c in cs if c < 0)
        v_up[t] = up * 2 >= len(cs)
    above = defaultdict(Counter)                            # LAW 3: below-tile -> above-tile counts
    for p in d["v_pairs"]:
        above[tuple(p["below"])][tuple(p["above"])] += 1
    crest_tiles = {t for t in n_inst if n_inst[t] >= 5 and crest_n[t] / n_inst[t] >= 0.5}
    foot_tiles = {t for t in n_inst if n_inst[t] >= 5 and base_n[t] / n_inst[t] >= 0.5}
    return v_up, above, crest_tiles, foot_tiles, n_inst


def exemplar_orientations(pu, pv, need, top_blocks):
    """(col,row) -> dict(u0,u1,v_lo,v_hi) measured from a REAL near-full-tile wall quad in
    the decode's own top stock blocks. v_lo = mean v of the two LOW verts -- the calibrated
    v-orientation; the catalogue alone cannot say which way is up."""
    ex = {}
    for (bx, by) in top_blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except Exception:                                   # noqa: BLE001
            continue
        pos = bm.chan_arrays[X.CH_POS]
        uv = bm.chan_arrays[X.CH_UV]
        tan = bm.chan_arrays[X.CH_TAN]
        e2t = defaultdict(list)
        for ti, t in enumerate(bm.tris):
            topo = X.decode_id(int(round(tan[t[0]][0])))["topograph"]
            if topo not in (49, 58, 31, 7, 62):
                continue
            ps = [kk(pos[i]) for i in t]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                e2t[tuple(sorted((ps[a], ps[b])))].append(ti)
        seen = set()
        for e, ts in e2t.items():
            if len(ts) != 2 or ts[0] in seen or ts[1] in seen:
                continue
            # flat meshes: every tri owns its verts, so the quad is 4 distinct POSITIONS
            uvm = {}
            for t2 in ts:
                for i in bm.tris[t2]:
                    uvm[kk(pos[i])] = (uv[i], pos[i][1])
            if len(uvm) != 4:
                continue
            us = [q[0][0] for q in uvm.values()]
            vv = [q[0][1] for q in uvm.values()]
            du, dv = max(us) - min(us), max(vv) - min(vv)
            if not (0.8 * TILE_U < du <= TILE_U + 1e-4 and 0.8 * TILE_V < dv <= TILE_V + 1e-4):
                continue
            col = round((min(us) - pu) / TILE_U)
            row = round((min(vv) - pv) / TILE_V)
            if (col, row) not in need or (col, row) in ex:
                continue
            pts = sorted(uvm.values(), key=lambda q: q[1])
            v_lo = float(np.mean([q[0][1] for q in pts[:2]]))
            v_hi = float(np.mean([q[0][1] for q in pts[2:]]))
            # store the MEASURED rect too: real quads sit on EITHER u-phase family, so the
            # one-window gate must judge against this rect, not a single-phase reconstruction
            ex[(col, row)] = dict(u0=min(us), u1=max(us), v_lo=v_lo, v_hi=v_hi,
                                  v0=min(vv), v1=max(vv))
            seen.update(ts)
        if all(k in ex for k in need):
            break
    return ex


def enum_chains(above, crest_tiles, foot_tiles):
    """THE LAW-3 CHAINS: every foot -> body -> crest path whose BOTH steps exist in the
    measured vertical transition table (contiguous atlas descent -- T1 round 1 tiled the
    courses independently and read as 'stamped together'). Weight = the product of the
    observed transition counts."""
    chains = []
    for t0, ups in above.items():
        if t0 not in foot_tiles:
            continue
        for t1, n01 in ups.items():
            for t2, n12 in above.get(t1, {}).items():
                if t2 in crest_tiles:
                    chains.append(([t0, t1, t2], n01 * n12))
    assert chains, "no measured foot->body->crest chain in the transition table"
    return chains


def plan_strips(n_st, chains):
    """Per wall column: one chain (count-weighted, seeded) + a p=0.12 mirror flag (LAW 2).
    Neighbour columns walk the body-tile atlas col by the measured +-1 / 11%-repeat regime."""
    by_bodycol = defaultdict(list)
    for ch, w in chains:
        by_bodycol[ch[1][0]].append((ch, w))
    cols_avail = sorted(by_bodycol)
    rng = random.Random(SEED ^ 0x5EED)

    def pick(fam):
        tot = sum(w for _, w in fam)
        x = rng.random() * tot
        for ch, w in fam:
            x -= w
            if x <= 0:
                return ch
        return fam[-1][0]

    plan = []                                               # per column: (chain, mirrored)
    ci = rng.randrange(len(cols_avail))
    for s in range(n_st):
        fam = by_bodycol[cols_avail[ci]]
        plan.append((pick(fam), rng.random() < 0.12))
        r = rng.random()
        if r >= 0.11:                                       # 11% same-col repeat, else +-1 walk
            step = 1 if r < 0.75 else -1
            ci = (ci + step) % len(cols_avail)
    return plan


# ---------------------------------------------------------------- zip (the SPUR bridge walk)
def bridge(low, high, outward_of=None):
    """Greedy bridge walk low->high; both are closed CCW rings (first point re-appended).

    WINDING (the round-1 'missing faces' fix): outward comes from the stepped CHAIN EDGE's
    tangent -- for a CCW ring in the xz plane, outward = right-of-travel = (tz, -tx). The
    old radial-from-centre test flips sign on concave lattice-jag switchbacks, and an
    inverted VISIBLE tri backface-culls in game as a hole while the once-edge audit stays
    balanced. The tangent rule is exact regardless of concavity."""
    out = []
    i, j = 0, 0
    while i < len(low) - 1 or j < len(high) - 1:
        ci, cj = i < len(low) - 1, j < len(high) - 1
        if ci and cj:
            step_low = math.dist(low[i + 1], high[j]) <= math.dist(low[i], high[j + 1])
        else:
            step_low = ci
        if step_low:
            tri = [low[i], low[i + 1], high[j]]
            tan = (low[i + 1][0] - low[i][0], low[i + 1][2] - low[i][2])
        else:
            tri = [low[i], high[j + 1], high[j]]
            tan = (high[j + 1][0] - high[j][0], high[j + 1][2] - high[j][2])
        if len({kk(p) for p in tri}) == 3:
            ow = (tan[1], -tan[0])                           # right of CCW travel = outward
            a, b, c = (np.array(p) for p in tri)
            fn = np.cross(b - a, c - a)
            if fn[0] * ow[0] + fn[2] * ow[1] < 0:
                tri = [tri[0], tri[2], tri[1]]
            out.append(tri)
        if step_low:
            i += 1
        else:
            j += 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    OUTD.mkdir(parents=True, exist_ok=True)

    tris, bms = load_bench()
    assert tris, "bench island not deployed at Disc9 (run the world-island mint first)"
    print(f"bench: {len(tris)} tris across {len(bms)} cells")

    poly = None
    for ds in range(40):
        cand = blob_poly(SEED + ds)
        if not poly_clip_slivers(cand):
            poly = cand
            print(f"blob seed {SEED + ds} (offset +{ds}): no lattice-clip slivers")
            break
    assert poly is not None, "no sliver-free blob seed in 40 tries -- widen the search"
    per = sum(math.dist(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))
    n_st = max(12, round(per / STATION))
    print(f"plateau blob r~{R_PLAT} perimeter {per:.1f}u -> {n_st} columns")

    def outward_of(px, pz):
        d = (px - CENTER[0], pz - CENTER[1])
        L = math.hypot(*d) or 1.0
        return (d[0] / L, d[1] / L)

    # ---- the plateau TOP: lattice cells clipped against the blob ------------------------------
    top_tris = []                                           # (p3, cell)
    cx0 = math.floor((CENTER[0] - R_PLAT * 1.3) / CELL) * CELL
    cx1 = math.ceil((CENTER[0] + R_PLAT * 1.3) / CELL) * CELL
    cz0 = math.floor((CENTER[1] - R_PLAT * 1.3) / CELL) * CELL
    cz1 = math.ceil((CENTER[1] + R_PLAT * 1.3) / CELL) * CELL
    x = cx0
    while x < cx1:
        z = cz0
        while z < cz1:
            corners = [(x, z), (x + CELL, z), (x + CELL, z + CELL), (x, z + CELL)]
            ins = [pinp(px, pz, poly) for (px, pz) in corners]
            if all(ins):
                a, b, c, d = [(px, TOP_Y, pz) for (px, pz) in corners]
                top_tris += [([a, b, c], (x, z)), ([a, c, d], (x, z))]
            elif any(ins):
                pg = clip_cell(poly, x, z)
                if len(pg) >= 3:
                    for t3 in centroid_fan(pg):
                        top_tris.append(([(p[0], TOP_Y, p[-1]) for p in t3], (x, z)))
            z += CELL
        x += CELL
    # up-winding for the top
    fixed_top = []
    for t3, cell in top_tris:
        a, b, c = (np.array(p) for p in t3)
        if np.cross(b - a, c - a)[1] < 0:
            t3 = [t3[0], t3[2], t3[1]]
        fixed_top.append((t3, cell))
    top_tris = fixed_top

    # T-VERTEX CONFORMANCE: a boundary cell's clip introduces verts on its own cell edges;
    # the neighbour's tris don't share them -> T-junctions -> phantom once-edges. Split any
    # top edge that carries another top vert (splits stay ON the edge, so every tri stays
    # inside its own cell -- THE CELL CLIP law survives the pass).
    allv = {(round(p[0], 3), round(p[2], 3)) for t3, _ in top_tris for p in t3}
    def _on_seg(p, a, b):
        ax, az, bx, bz = a[0], a[2], b[0], b[2]
        px, pz = p
        cross = (bx - ax) * (pz - az) - (bz - az) * (px - ax)
        if abs(cross) > 1e-3:
            return None
        L2 = (bx - ax) ** 2 + (bz - az) ** 2
        if L2 < 1e-9:
            return None
        t = ((px - ax) * (bx - ax) + (pz - az) * (bz - az)) / L2
        return t if 1e-4 < t < 1 - 1e-4 else None
    conformed = []
    n_split = 0
    for t3, cell in top_tris:
        pg = []
        for k in range(3):
            a, b = t3[k], t3[(k + 1) % 3]
            pg.append(a)
            ins = []
            for p in allv:
                if (round(a[0], 3), round(a[2], 3)) == p or (round(b[0], 3), round(b[2], 3)) == p:
                    continue
                t = _on_seg(p, a, b)
                if t is not None:
                    ins.append((t, (p[0], TOP_Y, p[1])))
            for _, p3 in sorted(ins):
                pg.append(p3)
                n_split += 1
        if len(pg) == 3:
            conformed.append((t3, cell))
        else:
            for tt in centroid_fan(pg):
                conformed.append((list(tt), cell))
    top_tris = conformed
    print(f"top: {len(top_tris)} shelf tris (lattice-clipped, {n_split} T-splits conformed)")

    # crest ring = the top's own boundary cycle (identity weld into the crest course)
    cnt = defaultdict(int)
    for t3, _ in top_tris:
        ps = [kk(p) for p in t3]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            cnt[tuple(sorted((ps[a], ps[b])))] += 1
    bedges = [e for e, n in cnt.items() if n == 1]
    adj = defaultdict(list)
    for a, b in bedges:
        adj[a].append(b)
        adj[b].append(a)
    deg_bad = [p for p, l in adj.items() if len(l) != 2]
    assert not deg_bad, f"top boundary not a simple cycle ({len(deg_bad)} odd-degree points)"
    start = bedges[0][0]
    crest = [start]
    prev = None
    while True:
        nxts = [p for p in adj[crest[-1]] if p != prev]
        if not nxts or nxts[0] == start:
            break
        prev = crest[-1]
        crest.append(nxts[0])
    assert len(crest) == len(bedges), \
        f"crest chain {len(crest)} verts != {len(bedges)} boundary edges (multiple loops?)"
    # orient CCW by angle
    th0 = [math.atan2(p[2] - CENTER[1], p[0] - CENTER[0]) for p in crest]
    if np.diff(np.unwrap(th0)).sum() < 0:
        crest = crest[::-1]
    # THE SEAM ALIGNMENT: start the chained ring at the vert nearest bearing 0, where the
    # station rings start -- an angular offset between the two rings folds the greedy zip
    # at the wrap (round 3's five down-facing crest tris at one vertex, gate-caught).
    k0 = min(range(len(crest)),
             key=lambda k: abs(math.atan2(crest[k][2] - CENTER[1], crest[k][0] - CENTER[0])))
    crest = crest[k0:] + crest[:k0]
    crest_c = [tuple(p) for p in crest] + [tuple(crest[0])]

    # ---- rings + the grass drop ---------------------------------------------------------------
    # both rings share station phase -- the stock dual-phase stagger is a TEXTURE phase
    # (implemented in the per-course u mapping below), NOT a ring rotation: rotating the
    # geometry shears every body quad half a column (round-1's diagonal smear).
    ring1 = ring_at(poly, RUN, COURSE_Y[1], n_st, phase=0.0)
    ring2 = ring_at(poly, 2 * RUN, COURSE_Y[2], n_st, phase=0.0)
    ring1c, ring2c = ring1 + [ring1[0]], ring2 + [ring2[0]]

    drop = set()
    dropped_cells = set()
    for ti, t in enumerate(tris):
        if t["topo"] not in GRASS_TOPO:
            continue
        px, pz = t["cen"][0], t["cen"][2]
        th = math.atan2(pz - CENTER[1], px - CENTER[0])
        if math.hypot(px - CENTER[0], pz - CENTER[1]) <= poly_radius(poly, th) + DROP_R_EXTRA:
            drop.add(ti)
            dropped_cells.add(t["blk"])
    assert drop, "nothing to drop -- wrong site?"
    print(f"drop: {len(drop)} grass tris in {sorted(dropped_cells)}")

    # the jagged foot ring = kept|dropped boundary edges of the KEPT mesh hole
    cnt2 = defaultdict(int)
    for ti, t in enumerate(tris):
        if ti in drop:
            continue
        ps = [kk(v) for v in t["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            cnt2[tuple(sorted((ps[a], ps[b])))] += 1
    pre_once_all = {e for e, n in cnt2.items() if n == 1}
    hole = []
    for e in pre_once_all:
        mx, mz = (e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2
        th = math.atan2(mz - CENTER[1], mx - CENTER[0])
        if math.hypot(mx - CENTER[0], mz - CENTER[1]) <= poly_radius(poly, th) + DROP_R_EXTRA + 3.0:
            hole.append(e)
    adj2 = defaultdict(list)
    for a, b in hole:
        adj2[a].append(b)
        adj2[b].append(a)
    deg_bad = [p for p, l in adj2.items() if len(l) != 2]
    assert not deg_bad, f"foot hole not a simple cycle ({len(deg_bad)} odd-degree points)"
    start = hole[0][0]
    foot = [start]
    prev = None
    while True:
        nxts = [p for p in adj2[foot[-1]] if p != prev]
        if not nxts or nxts[0] == start:
            break
        prev = foot[-1]
        foot.append(nxts[0])
    th0 = [math.atan2(p[2] - CENTER[1], p[0] - CENTER[0]) for p in foot]
    if np.diff(np.unwrap(th0)).sum() < 0:
        foot = foot[::-1]
    k0 = min(range(len(foot)),
             key=lambda k: abs(math.atan2(foot[k][2] - CENTER[1], foot[k][0] - CENTER[0])))
    foot = foot[k0:] + foot[:k0]                            # seam-aligned with the station rings
    foot_c = [tuple(p) for p in foot] + [tuple(foot[0])]
    print(f"foot ring: {len(foot)} lattice verts")

    # ---- the three courses --------------------------------------------------------------------
    crest_course = bridge(ring1c, crest_c, outward_of)      # low=ring1, high=crest verts
    body_course = []
    for i in range(n_st):
        a, b = ring2c[i], ring2c[i + 1]
        c, d = ring1c[i], ring1c[i + 1]
        ow = (b[2] - a[2], -(b[0] - a[0]))                  # right of CCW travel = outward
        for tri in ([a, b, c], [b, d, c]):
            a2, b2, c2 = (np.array(p) for p in tri)
            fn = np.cross(b2 - a2, c2 - a2)
            if fn[0] * ow[0] + fn[2] * ow[1] < 0:
                tri = [tri[0], tri[2], tri[1]]
            body_course.append(tri)
    foot_course = bridge(foot_c, ring2c, outward_of)        # low=jagged foot, high=ring2
    courses = [("crest", crest_course), ("body", body_course), ("foot", foot_course)]
    print("courses:", {r: len(c) for r, c in courses})

    # ---- the tile-language UVs (round 3: the three instance laws) -----------------------------
    pu, pv, tiles, top_blocks = load_language()
    v_up, above, crest_tiles, foot_tiles, n_inst = load_anatomy()
    chains = enum_chains(above, crest_tiles, foot_tiles)
    need = {t for ch, _ in chains for t in ch}
    ex = exemplar_orientations(pu, pv, need, top_blocks)
    # LAW 3 needs measured RECTS for every chain tile -- keep only fully-measured chains
    chains_m = [(ch, w) for ch, w in chains if all(t in ex for t in ch)]
    print(f"chains: {len(chains)} measured in the table, {len(chains_m)} fully rect-calibrated")
    assert chains_m, "no chain has rects for all three tiles -- widen the exemplar scan"
    plan = plan_strips(n_st, chains_m)

    def v_ends(tile):
        """(v_bottom, v_top) for a tile: rect from the exemplar, ORIENTATION from LAW 1's
        per-tile majority -- never from the one exemplar (T1 round 1's flipped tiles)."""
        e2 = ex[tile]
        if tile in v_up:
            up = v_up[tile]                                 # True = atlas v decreases upward
        else:
            up = e2["v_lo"] > e2["v_hi"]                    # no votes: the exemplar's own read
        return (e2["v1"], e2["v0"]) if up else (e2["v0"], e2["v1"])

    y_spans = [(COURSE_Y[1], TOP_Y), (COURSE_Y[2], COURSE_Y[1]), (None, COURSE_Y[2])]
    wall_out = []                                           # (tri, uv3, role, tile)
    col_steps = []
    for ci, (role, ctris) in enumerate(courses):
        chain_idx = 2 - ci                                  # chain = [foot, body, crest]
        u_phase = 0.5 * (ci % 2)                            # THE DUAL-PHASE STAGGER, in texture
        if ci == 1:
            for k in range(1, n_st):
                col_steps.append(plan[k][0][1][0] - plan[k - 1][0][1][0])
        for tri in ctris:
            thc = math.atan2(float(np.mean([p[2] for p in tri])) - CENTER[1],
                             float(np.mean([p[0] for p in tri])) - CENTER[0])
            s = ((thc % (2 * math.pi)) / (2 * math.pi) * n_st - u_phase) % n_st
            wcol = max(0, min(n_st - 1, int(s)))
            chain, mirrored = plan[wcol]
            tile = chain[chain_idx]
            e2 = ex[tile]
            v_bot, v_top = v_ends(tile)
            ylo, yhi = y_spans[ci]
            uvt = []
            for p in tri:
                thp = math.atan2(p[2] - CENTER[1], p[0] - CENTER[0])
                sp = ((thp % (2 * math.pi)) / (2 * math.pi) * n_st - u_phase) % n_st
                if sp < wcol - 0.5:                          # wrap seam
                    sp += n_st
                su = max(0.0, min(1.0, sp - wcol))
                if mirrored:                                 # LAW 2: p=0.12 per column
                    su = 1.0 - su
                if ylo is None:                              # foot: local low = the jagged foot y
                    y_lo_l = min(q[1] for q in tri)
                    y_hi_l = COURSE_Y[2]
                else:
                    y_lo_l, y_hi_l = ylo, yhi
                h = max(0.0, min(1.0, (p[1] - y_lo_l) / max(0.8, y_hi_l - y_lo_l)))
                uvt.append((e2["u0"] + su * (e2["u1"] - e2["u0"]),
                            v_bot + h * (v_top - v_bot)))
            wall_out.append((tri, uvt, role, tile))
    n_mir = sum(1 for ch, m in plan if m)
    n_pm1 = sum(1 for d in col_steps if abs(d) == 1)
    n_same = sum(1 for d in col_steps if d == 0)
    print(f"strips: {n_st} columns, {n_mir} mirrored ({n_mir / n_st:.0%}; LAW 2 says ~12%); "
          f"col walk +-1 {n_pm1 / len(col_steps):.0%} / repeat {n_same / len(col_steps):.0%}")
    # THE LAW-3 GATE: every column's two vertical steps exist in the measured table
    for k, (chain, _) in enumerate(plan):
        assert above[chain[0]].get(chain[1], 0) > 0 and above[chain[1]].get(chain[2], 0) > 0, \
            f"column {k} chain {chain} not a measured vertical path"
    print(f"LAW-3 gate: all {n_st} columns are measured foot->body->crest paths")

    # ---- TOP UVs: junction L3 REUSED -- never a uniform-random per-cell draw ------------------
    # (T1 round 1 re-derived the naive version and shipped the banded top; the folded policy is
    # uvf_fix2.assign_mains_seeded seeded with (quad,ori) ground truth DECODED from the bench's
    # own kept grass around the plateau.)
    sys.path.insert(0, str(ROOT / "studies" / "overworld-topography"))
    import uvf_fix2 as UF                                   # noqa: E402
    pre_quad, pre_ori = {}, {}
    for ti, t in enumerate(tris):
        if ti in drop or t["topo"] not in GRASS_TOPO:
            continue
        cx4, cz4 = t["cen"][0], t["cen"][2]
        ccell = (int(cx4 // CELL), int(-cz4 // CELL))
        if ccell in pre_quad:
            continue
        if math.hypot(cx4 - CENTER[0], cz4 - CENTER[1]) > R_PLAT + 24.0:
            continue
        qo = UF.decode_quad_ori(ccell, t["w"], [tuple(u2) for u2 in t["uv"]])
        if qo is not None:
            pre_quad[ccell], pre_ori[ccell] = qo
    def tri_cell(t3):
        """The canonical own-cell (floor(x/4), floor(-z/4)) of a tri's CENTROID -- the same
        convention the decode + mains_uv use; deriving it from the lattice ORIGIN is one
        cell off in j and makes every window a neighbour's (THE CELL CLIP law breaks)."""
        cx4 = float(np.mean([p[0] for p in t3]))
        cz4 = float(np.mean([p[2] for p in t3]))
        return (int(cx4 // CELL), int(-cz4 // CELL))

    top_cells = sorted({tri_cell(t3) for t3, _ in top_tris})
    q2, o2 = UF.assign_mains_seeded([c for c in top_cells if c not in pre_quad],
                                    dict(pre_quad), dict(pre_ori), seed=SEED ^ 0xF92)
    cell_qo = {c: (pre_quad[c], pre_ori[c]) for c in top_cells if c in pre_quad}
    cell_qo.update({c: (q2[c], o2[c]) for c in q2 if c in set(top_cells)})
    print(f"top L3 field: {len(pre_quad)} cells decoded from the bench's own grass, "
          f"{len(q2)} policy-resolved (assign_mains_seeded)")
    top_out = []
    for t3, cell in top_tris:
        ccell = tri_cell(t3)
        quad, ori = cell_qo[ccell]
        uvt = [G.ground_uv(p[0], p[2], ccell, quad, ori) for p in t3]
        top_out.append((t3, uvt))

    # ---- gates --------------------------------------------------------------------------------
    fails = []
    for tri, uvt, role, cr in wall_out:                     # one-window + data-driven roles
        e2 = ex[cr]
        for (u, v) in uvt:
            if not (e2["u0"] - 1e-4 <= u <= e2["u1"] + 1e-4 and
                    e2["v0"] - 1e-4 <= v <= e2["v1"] + 1e-4):
                fails.append(f"one-window: {role} uv ({u:.4f},{v:.4f}) outside the measured "
                             f"rect of {cr}")
                break
        if role == "foot" and cr not in foot_tiles:
            fails.append(f"role: foot tile {cr} is not base-touch-majority in stock")
        if role == "crest" and cr not in crest_tiles:
            fails.append(f"role: crest tile {cr} is not crest-touch-majority in stock")
    # watertight: recount over kept + wall + top
    cnt3 = defaultdict(int)
    def _acc(t3):
        ps = [kk(p) for p in t3]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            cnt3[tuple(sorted((ps[a], ps[b])))] += 1
    for ti, t in enumerate(tris):
        if ti not in drop:
            _acc(t["w"])
    for tri, _, _, _ in wall_out:
        _acc(tri)
    for t3, _ in top_out:
        _acc(t3)
    post_once = {e for e, n in cnt3.items() if n == 1}
    grew = post_once - pre_once_all
    if grew:
        fails.append(f"watertight: {len(grew)} NEW once-edges (sample {list(grew)[:2]})")
    consumed = [e for e in pre_once_all - post_once]
    # moat / coast margin: every new vert stays >= 6u inside the bench outline (radius 40)
    for tri, _, _, _ in wall_out:
        for p in tri:
            if math.hypot(p[0] - CENTER[0], p[2] - CENTER[1]) > 40.0 - 6.0:
                fails.append(f"moat: wall vert {kk(p)} within 6u of the bench outline")
    # THE WINDING GATE (D3's spirit, ported): no VISIBLE wall tri may face inward or down,
    # no top tri may face down; near-degenerates are exempt (they cull to nothing, no hole).
    n_degen = 0
    for tri, _, role, _ in wall_out:
        a, b, c = (np.array(p) for p in tri)
        fn = np.cross(b - a, c - a)
        L = float(np.linalg.norm(fn))
        if L < 2e-2:
            n_degen += 1
            continue
        rad = outward_of(float(np.mean([p[0] for p in tri])), float(np.mean([p[2] for p in tri])))
        horiz = math.hypot(fn[0], fn[2])
        if horiz > 0.3 * L and (fn[0] * rad[0] + fn[2] * rad[1]) / max(horiz, 1e-9) < -0.6:
            fails.append(f"winding: a visible {role} tri faces INWARD at {kk(tri[0])}")
        if fn[1] < -0.5 * L:
            fails.append(f"winding: a visible {role} tri faces DOWN at {kk(tri[0])}")
    for t3, _ in top_out:
        a, b, c = (np.array(p) for p in t3)
        fn = np.cross(b - a, c - a)
        if fn[1] < 0 and float(np.linalg.norm(fn)) > 2e-2:
            fails.append(f"winding: a top tri faces DOWN at {kk(t3[0])}")
    print(f"winding gate: {n_degen} near-degenerate wall tris (cull to nothing, exempt)")
    print(f"gates: {len(fails)} failure(s); foot-ring edges consumed: {len(consumed)}")
    for f in fails[:8]:
        print("  !!", f)

    # ---- assemble + census + renders ----------------------------------------------------------
    ID_ROCK = float(X.encode_id(topograph=ROCK))
    ID_SHELF = float(X.encode_id(topograph=SHELF))
    acc = defaultdict(lambda: np.zeros(3))
    def _nacc(t3):
        a, b, c = (np.array(p) for p in t3)
        fn = np.cross(b - a, c - a)
        for p in t3:
            acc[kk(p)] += fn
    for tri, _, _, _ in wall_out:
        _nacc(tri)
    for t3, _ in top_out:
        _nacc(t3)
    for ti, t in enumerate(tris):
        if ti not in drop:
            _nacc(t["w"])
    def snrm(p):
        v = acc[kk(p)]
        L = np.linalg.norm(v)
        return (v / L).tolist() if L > 1e-9 else [0.0, 1.0, 0.0]

    by_cell = defaultdict(lambda: ([], [], [], []))         # pos nrm uv tan per changed cell
    def emit(cell, p, u2, n2, t4):
        pos, nrm, uv, tan = by_cell[cell]
        pos.append([p[0] - BLOCK * cell[0], p[1], p[2] + BLOCK * cell[1]])
        nrm.append(list(n2)); uv.append(list(u2)); tan.append(list(t4))
    def cell_of(t3):
        cx = float(np.mean([p[0] for p in t3]))
        cz = float(np.mean([p[2] for p in t3]))
        return (int(cx // BLOCK), int(-cz // BLOCK))
    for ti, t in enumerate(tris):
        if ti in drop:
            continue
        for k in range(3):
            emit(t["blk"], t["w"][k], t["uv"][k], t["n"][k], t["tan"][k])
    for tri, uvt, _, _ in wall_out:
        c = cell_of(tri)
        for k in range(3):
            emit(c, tri[k], uvt[k], snrm(tri[k]), [ID_ROCK, 0.0, 0.0, 1.0])
    for t3, uvt in top_out:
        c = cell_of(t3)
        for k in range(3):
            emit(c, t3[k], uvt[k], snrm(t3[k]), [ID_SHELF, 0.0, 0.0, 1.0])
    changed = {}
    for cell, (pos, nrm, uv, tan) in by_cell.items():
        flat = list(range(len(pos)))
        changed[cell] = X.BlockMesh(
            name=f"Block[{cell[0]}][{cell[1]}] Terrain", disc=DISC, x=cell[0], y=cell[1],
            lod="0_1", vcount=len(pos), stride=48,
            channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
            chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm, X.CH_UV: uv, X.CH_TAN: tan},
            flat_index=flat, tris=[flat[3 * t2:3 * t2 + 3] for t2 in range(len(flat) // 3)],
            raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])
    IN.census_gate(changed, disc=1)                         # stock sea plane = the census rig
    print(f"census MISS=0 across {len(changed)} changed cells")

    # renders: planview + 4 compass face strips
    atlas_p = GAME / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
        "textures" / "res(1_24)_terrain.png"
    atlas = Image.open(atlas_p).convert("RGBA")
    AW, AH = atlas.size
    APX = atlas.load()
    def at_b(u2, v2):
        fx = (u2 % 1.0) * AW - 0.5
        fy = (1.0 - v2 % 1.0) * AH - 0.5
        x0, y0 = int(math.floor(fx)), int(math.floor(fy))
        tx, ty = fx - x0, fy - y0
        a4 = [0.0, 0.0, 0.0]
        for (dx, dy, wg) in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                             (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
            px_, py_ = min(max(x0 + dx, 0), AW - 1), min(max(y0 + dy, 0), AH - 1)
            r, g2, b2, _ = APX[px_, py_]
            a4[0] += r * wg; a4[1] += g2 * wg; a4[2] += b2 * wg
        return tuple(int(v) for v in a4)
    LDIR = (-0.5, 0.7, -0.3)
    _l = math.sqrt(sum(q * q for q in LDIR))
    LDIR = tuple(q / _l for q in LDIR)

    def render_strip(items, path, center, bearing, HW=20.0, HH=17.0, SC=22):
        """Vertex-lit elevation strip: per-pixel barycentric UV + Gouraud lambda from the
        supplied per-vertex normals -- the engine's own shading model, so stock and synth
        read through the SAME eye."""
        RW, RH = int(2 * HW * SC), int(HH * SC)
        img = Image.new("RGB", (RW, RH), (152, 178, 208))
        zbuf = np.full((RW, RH), -1e9)
        tvec = (-math.sin(bearing), math.cos(bearing))
        for tri, uvt, nrm3 in items:
            pts = []
            for p, u2 in zip(tri, uvt):
                s2 = (p[0] - center[0]) * tvec[0] + (p[2] - center[1]) * tvec[1]
                d2 = (p[0] - center[0]) * math.cos(bearing) + (p[2] - center[1]) * math.sin(bearing)
                pts.append((s2, p[1], d2, u2))
            if all(p[2] < 0 for p in pts):
                continue
            lams = [max(0.25, float(np.dot(np.array(n2), LDIR)) * 0.6 + 0.55) for n2 in nrm3]
            xs = [int((p[0] + HW) * SC) for p in pts]
            ys = [int((HH - p[1]) * SC) for p in pts]
            if max(xs) < 0 or min(xs) >= RW or max(ys) < 0 or min(ys) >= RH:
                continue
            a2, b2, c2 = (np.array((pts[k][0], pts[k][1])) for k in range(3))
            det = float(np.cross(b2 - a2, c2 - a2))
            if abs(det) < 1e-9:
                continue
            for px_ in range(max(0, min(xs)), min(RW - 1, max(xs)) + 1):
                for py_ in range(max(0, min(ys)), min(RH - 1, max(ys)) + 1):
                    sx = px_ / SC - HW
                    sy = HH - py_ / SC
                    w1 = float(np.cross(b2 - np.array((sx, sy)), c2 - np.array((sx, sy)))) / det
                    w2 = float(np.cross(c2 - np.array((sx, sy)), a2 - np.array((sx, sy)))) / det
                    w3 = 1 - w1 - w2
                    if w1 < -1e-6 or w2 < -1e-6 or w3 < -1e-6:
                        continue
                    dep = w1 * pts[0][2] + w2 * pts[1][2] + w3 * pts[2][2]
                    if dep <= zbuf[px_, py_]:
                        continue
                    zbuf[px_, py_] = dep
                    uu = w1 * pts[0][3][0] + w2 * pts[1][3][0] + w3 * pts[2][3][0]
                    vv = w1 * pts[0][3][1] + w2 * pts[1][3][1] + w3 * pts[2][3][1]
                    lam = w1 * lams[0] + w2 * lams[1] + w3 * lams[2]
                    col2 = at_b(uu, vv)
                    img.putpixel((px_, py_), tuple(int(ch * lam) for ch in col2))
        img.save(path)

    synth_items = [(tri, uvt, [snrm(p) for p in tri]) for tri, uvt, _, _ in wall_out]
    synth_items += [(t3, uvt, [snrm(p) for p in t3]) for t3, uvt in top_out]
    for name, bearing in (("E", 0.0), ("N", math.pi / 2), ("W", math.pi), ("S", -math.pi / 2)):
        render_strip(synth_items, OUTD / f"face_{name}.png", CENTER, bearing)

    # THE CALIBRATION CONTROL: a real stock wall through the SAME eye. If stock reads
    # faceted here too, the faceting is the instrument; only differences are findings.
    sbx, sby = top_blocks[0]
    sbm = X.read_block(sbx, sby, disc=1, part="terrain")
    spos = sbm.chan_arrays[X.CH_POS]
    suv = sbm.chan_arrays[X.CH_UV]
    snr = sbm.chan_arrays[X.CH_NRM]
    stan = sbm.chan_arrays[X.CH_TAN]
    sox, soz = BLOCK * sbx, -BLOCK * sby
    stock_items = []
    rock_pts = []
    for t in sbm.tris:
        topo = X.decode_id(int(round(stan[t[0]][0])))["topograph"]
        if topo not in (49, 58, 31, 7, 62):
            continue
        w3 = [(spos[i][0] + sox, spos[i][1], spos[i][2] + soz) for i in t]
        stock_items.append((w3, [suv[i] for i in t], [snr[i] for i in t]))
        rock_pts += [(p[0], p[2]) for p in w3]
    scx = float(np.mean([p[0] for p in rock_pts]))
    scz = float(np.mean([p[1] for p in rock_pts]))
    for name, bearing in (("N", math.pi / 2), ("E", 0.0)):
        render_strip(stock_items, OUTD / f"stock_control_{name}.png", (scx, scz), bearing,
                     HW=26.0, HH=34.0, SC=13)
    print(f"renders -> {OUTD} (incl. the stock control strips from block ({sbx},{sby}))")

    if fails:
        print("\nT1: GATES RED -- not deployable")
        return 1
    if not args.apply:
        print("\nT1: gates green (offline). Review the renders; re-run with --apply to deploy.")
        return 0

    # ---- deploy -------------------------------------------------------------------------------
    ts = time.strftime("%Y%m%d-%H%M%S")
    bdir = Path(r"C:\gd\Dream-World-IX\backups") / f"terrace-t1-prewall.{ts}"
    bdir.mkdir(parents=True, exist_ok=True)
    for cell, (p, _bm) in bms.items():
        shutil.copy2(p, bdir / p.name)
    written = []
    for cell, bm in sorted(changed.items()):
        written.append(M.deploy_override(bm, mod_folder=MOD, disc=DISC, part="Terrain"))
        print(f"deployed -> {written[-1]} ({len(bm.tris)} tris)")
    print(f"pre-wall bench backed up -> {bdir}")
    print("in game: ~ -> Go -> 9013 -> World -> teleport (416, -512); re-enter the world.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
