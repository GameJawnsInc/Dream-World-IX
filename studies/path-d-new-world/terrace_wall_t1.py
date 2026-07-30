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

Gates before any write: one-window per tri, band membership, adjacency-rate report,
watertight (0 new once-edges), drop completeness, census MISS=0, the moat/coast margin,
plus face renders (4 compass segments) + a planview for the offline eye. --apply deploys
to Disc9 (backing the bench cells up under the MAIN repo's backups/) only when green.

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
from collections import defaultdict
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
def load_language():
    d = json.loads(DECODE.read_text())
    pu, pv = d["phase"]
    tiles = {tuple(int(v) for v in k.split(",")): n for k, n in d["tiles"].items()}
    blocks = defaultdict(int)
    for g in d["groups"]:
        blocks[tuple(g["blk"])] += 1
    top_blocks = [b for b, _ in sorted(blocks.items(), key=lambda kv: -kv[1])[:6]]
    return pu, pv, tiles, top_blocks


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


def plan_columns(n_st, tiles):
    """Per (course, column) -> (col,row): u-continuation with +-1 col steps, band wrap,
    occasional same-tile repeat and row drift -- the measured windowed-continuation regime.
    Only tiles present in the stock catalogue are used."""
    rng = random.Random(SEED ^ 0x5EED)
    plan = []
    for ci, role in enumerate(("crest", "body", "foot")):
        rows, cols = BANDS[role]
        rows = [r for r in rows]
        cols = [c for c in cols]
        legal = [(c, r) for c in cols for r in rows if (c, r) in tiles]
        assert legal, f"no catalogued tiles for the {role} band"
        cur = legal[rng.randrange(len(legal))]
        out = []
        for s in range(n_st):
            out.append(cur)
            r = rng.random()
            if r < 0.11:
                nxt = cur                                   # same-tile repeat (the 11%)
            else:
                ic = cols.index(cur[0])
                step = 1 if r < 0.75 else -1
                nc = cols[(ic + step) % len(cols)]          # band wrap = window translate
                nr = cur[1]
                if rng.random() < 0.22:
                    ir = rows.index(nr)
                    nr = rows[max(0, min(len(rows) - 1, ir + rng.choice((-1, 1))))]
                nxt = (nc, nr) if (nc, nr) in tiles else cur
            cur = nxt
        if role == "foot":                                  # the true foot course prefers row 10
            out = [(c, FOOT_ROW) if (c, FOOT_ROW) in tiles else (c, r) for (c, r) in out]
        plan.append(out)
    return plan


# ---------------------------------------------------------------- zip (the SPUR bridge walk)
def bridge(low, high, outward_of):
    """Greedy bridge walk low->high; both are closed rings (first point re-appended)."""
    out = []
    i, j = 0, 0
    while i < len(low) - 1 or j < len(high) - 1:
        ci, cj = i < len(low) - 1, j < len(high) - 1
        if ci and cj:
            step_low = math.dist(low[i + 1], high[j]) <= math.dist(low[i], high[j + 1])
        else:
            step_low = ci
        tri = [low[i], low[i + 1], high[j]] if step_low else [low[i], high[j + 1], high[j]]
        if len({kk(p) for p in tri}) == 3:
            out.append(tri)
        if step_low:
            i += 1
        else:
            j += 1
    fixed = []
    for tri in out:
        a, b, c = (np.array(p) for p in tri)
        fn = np.cross(b - a, c - a)
        o = outward_of(np.mean([p[0] for p in tri]), np.mean([p[2] for p in tri]))
        if fn[0] * o[0] + fn[2] * o[1] < 0:
            tri = [tri[0], tri[2], tri[1]]
        fixed.append(tri)
    return fixed


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
    foot_c = [tuple(p) for p in foot] + [tuple(foot[0])]
    print(f"foot ring: {len(foot)} lattice verts")

    # ---- the three courses --------------------------------------------------------------------
    crest_course = bridge(ring1c, crest_c, outward_of)      # low=ring1, high=crest verts
    body_course = []
    for i in range(n_st):
        a, b = ring2c[i], ring2c[i + 1]
        c, d = ring1c[i], ring1c[i + 1]
        for tri in ([a, b, c], [b, d, c]):
            a2, b2, c2 = (np.array(p) for p in tri)
            fn = np.cross(b2 - a2, c2 - a2)
            o = outward_of(float(np.mean([p[0] for p in tri])),
                           float(np.mean([p[2] for p in tri])))
            if fn[0] * o[0] + fn[2] * o[1] < 0:
                tri = [tri[0], tri[2], tri[1]]
            body_course.append(tri)
    foot_course = bridge(foot_c, ring2c, outward_of)        # low=jagged foot, high=ring2
    courses = [("crest", crest_course), ("body", body_course), ("foot", foot_course)]
    print("courses:", {r: len(c) for r, c in courses})

    # ---- the tile-language UVs ----------------------------------------------------------------
    pu, pv, tiles, top_blocks = load_language()
    plan = plan_columns(n_st, tiles)
    need = {cr for row in plan for cr in row}
    ex = exemplar_orientations(pu, pv, need, top_blocks)
    missing = [cr for cr in need if cr not in ex]
    assert ex, "no calibrated exemplar quad found in any decode block -- cannot orient tiles"
    # a tile with no real full-quad exemplar falls back to a calibrated one from the same plan row
    for i3, row in enumerate(plan):
        fixed_row = []
        for cr in row:
            if cr in ex:
                fixed_row.append(cr)
            else:
                fixed_row.append(next((c for c in row if c in ex), sorted(ex)[0]))
        plan[i3] = fixed_row
    print(f"exemplars: {len(ex)} calibrated, {len(missing)} fell back")

    y_spans = [(COURSE_Y[1], TOP_Y), (COURSE_Y[2], COURSE_Y[1]), (None, COURSE_Y[2])]
    wall_out = []                                           # (tri, uv3, role)
    adjacency = []
    for ci, (role, ctris) in enumerate(courses):
        prow = plan[ci]
        u_phase = 0.5 * (ci % 2)                            # THE DUAL-PHASE STAGGER, in texture:
        for k in range(1, n_st):                            # alternate courses' column boundaries
            adjacency.append((prow[k][0] - prow[k - 1][0], prow[k][1] - prow[k - 1][1]))
        for tri in ctris:
            thc = math.atan2(float(np.mean([p[2] for p in tri])) - CENTER[1],
                             float(np.mean([p[0] for p in tri])) - CENTER[0])
            s = ((thc % (2 * math.pi)) / (2 * math.pi) * n_st - u_phase) % n_st
            wcol = max(0, min(n_st - 1, int(s)))
            e2 = ex[prow[wcol]]
            ylo, yhi = y_spans[ci]
            uvt = []
            for p in tri:
                thp = math.atan2(p[2] - CENTER[1], p[0] - CENTER[0])
                sp = ((thp % (2 * math.pi)) / (2 * math.pi) * n_st - u_phase) % n_st
                if sp < wcol - 0.5:                          # wrap seam
                    sp += n_st
                su = max(0.0, min(1.0, sp - wcol))
                if ylo is None:                              # foot: local low = the jagged foot y
                    y_lo_l = min(q[1] for q in tri)
                    y_hi_l = COURSE_Y[2]
                else:
                    y_lo_l, y_hi_l = ylo, yhi
                h = max(0.0, min(1.0, (p[1] - y_lo_l) / max(0.8, y_hi_l - y_lo_l)))
                uvt.append((e2["u0"] + su * (e2["u1"] - e2["u0"]),
                            e2["v_lo"] + h * (e2["v_hi"] - e2["v_lo"])))
            wall_out.append((tri, uvt, role, prow[wcol]))
    n_adj = len(adjacency)
    n_pm1 = sum(1 for (dc, dr) in adjacency if abs(dc) <= 1 and abs(dr) <= 1 and (dc, dr) != (0, 0))
    n_same = sum(1 for a in adjacency if a == (0, 0))
    print(f"adjacency: +-1 {n_pm1 / n_adj:.0%}, same-tile {n_same / n_adj:.0%} "
          f"(measured stock regime ~46% + ~11%; band wraps are the remainder)")

    # ---- TOP UVs: one grass-family main window per tri, keyed on the centroid cell ------------
    rngq = random.Random(SEED ^ 0xA11)
    cell_qo = {}
    top_out = []
    for t3, cell in top_tris:
        if cell not in cell_qo:
            cell_qo[cell] = (rngq.randrange(2) * 1, rngq.randrange(2), rngq.randrange(4))
        qx, qz, ori = cell_qo[cell]
        cc = (int(cell[0] // CELL), int(-cell[1] // CELL))
        uvt = [G.ground_uv(p[0], p[2], (cell[0] / CELL, -cell[1] / CELL), (qx, qz), ori)
               for p in t3]
        top_out.append((t3, uvt))

    # ---- gates --------------------------------------------------------------------------------
    fails = []
    for tri, uvt, role, cr in wall_out:                     # one-window + band membership
        col, row = cr
        e2 = ex[cr]
        for (u, v) in uvt:
            if not (e2["u0"] - 1e-4 <= u <= e2["u1"] + 1e-4 and
                    e2["v0"] - 1e-4 <= v <= e2["v1"] + 1e-4):
                fails.append(f"one-window: {role} uv ({u:.4f},{v:.4f}) outside the measured "
                             f"rect of ({col},{row})")
                break
        rows, cols = BANDS[role]
        if role == "foot":
            rows = tuple(rows) + (FOOT_ROW,)
        if row not in rows or col not in cols:
            fails.append(f"band: {role} tile ({col},{row}) outside its role band")
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
