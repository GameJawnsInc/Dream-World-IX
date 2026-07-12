"""RUNG D -- THE TERRACE: a mid-shelf (topo 13, y~17) ringed by stacked rock-wall courses,
synthesized from the decoded interior languages onto ISLAND F (the terrace islet).

Composes the plateau-edge laws + the rock-wall tile language:
* the MID-SHELF class: flat grass-mains shelf pinned at ~17u, topo 13, ringed by 49
  (unreachable on foot BY DESIGN -- the NO-FOOT-PASS finding: FF9's altitude worlds never
  connect by walking; a ramp would be off-language);
* STACKED WALLS at the real slope (58 deg = the measured p75; courses ~4.5u tall = the
  course-quantization law), landing on island F's lowland grass;
* the WALL BANDS: top course = the crest band (atlas row 4, cols 4-7), middle = upper-body
  (row 7, cols 0-3), foot = lower-body/base (row 10, cols 6-9); ONE 128x128px tile per
  quad, u advancing along the ring with the 4-column band wrap (the windowed continuation);
  the learned lattice phase from out/rock_tiles.json;
* NO LIP ROW: shelf mains run to the crest edge (the soft ~50-deg crest falls out of the
  58-deg wall meeting the ~7-deg shelf);
* the foot welds to the island by the PROVEN carve machinery (hole cut + chained rings +
  greedy zip annulus + byte-decoded per-cell zip mains + ring-owner normals).

Gates: every wall UV inside its course band rect, annulus once-edges 0 (foot weld AND the
terrace surface), down-facing 0, near-miss weld audit, census MISS=0 (+ the shelf-centre
probe grounds Terrain topo 13), Moguri-atlas alpha 0, shaded render.

Usage:  py studies/overworld-topography/terrace_build.py [deploy]
"""
import json
import math
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg
from ff9mapkit.world import extract as X
from ff9mapkit.world import grassland as G
from ff9mapkit.world import mesh as M
from ff9mapkit.world import placement as P

GP = Path(_cfg.find_game_path(None))
MODW = GP / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
BK = Path(__file__).resolve().parents[2] / "backups"
OUT_RENDER = Path(__file__).with_name("out") / "island_f_terrace_render.png"
BLK = (3, 17)
BLOCK = 64.0
CX, CZ = 224.0, -1120.0                                    # island F centre = the terrace centre

SHELF_Y = 17.0                                             # the mid-shelf altitude (15.7-18.3 real)
SHELF_R = 6.5
WALL_SLOPE = 58.0                                          # deg (real p75)
N_COURSES = 3
TILE_U, TILE_V = 0.0625, 0.03125
COURSE_BANDS = [(4, (4, 5, 6, 7)),                         # top: crest band row 4
                (7, (0, 1, 2, 3)),                         # middle: upper-body row 7
                (10, (6, 7, 8, 9))]                        # foot: base row 10
CLEAR = 2.5
RING_BAND = CLEAR + 6.5
SEED = 7
kk3 = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

_rt = json.loads((Path(__file__).with_name("out") / "rock_tiles.json").read_text())
PU, PV = _rt["phase"]
print(f"tile lattice phase: PU={PU:.5f} PV={PV:.5f}", flush=True)

# THE PER-BLOCK FLOAT DIALECT law: emission floats are BYTE-READ from the decoded groups,
# never typed from the lattice -- each tile id's rect = the modal exact (u0, v0, du, dv)
# over its real occurrences (real rects sit just inside Moguri's transparent gutters).
_tile_rect = {}
_cnt = defaultdict(Counter)
for g in _rt["groups"]:
    col = int(round((g["u0"] - PU) / TILE_U))
    row = int(round((g["v0"] - PV) / TILE_V))
    _cnt[(col, row)][(round(g["u0"], 5), round(g["v0"], 5), round(g["du"], 5), round(g["dv"], 5))] += 1
for tid, c in _cnt.items():
    _tile_rect[tid] = c.most_common(1)[0][0]

def tile_rect(col, row):
    u0, v0, du, dv = _tile_rect[(col, row)]
    return u0, v0, du, dv

# ---- 1. island F, deployed ------------------------------------------------------------------
src = MODW / f"r{BLK[1]}" / f"Block[{BLK[0]}][{BLK[1]}] Terrain.ff9mesh"
bm = M.blockmesh_from_ff9mesh(src, disc=1, x=BLK[0], y=BLK[1], lod="0_1", part="terrain")
bx, by = BLK
gpos = [[v[0] + BLOCK * bx, v[1], v[2] - BLOCK * (by + 1) + BLOCK] for v in bm.verts]
gtris = list(bm.tris)
gnrm = [list(n) for n in bm.chan_arrays[X.CH_NRM]]
guv = [list(u) for u in bm.chan_arrays[X.CH_UV]]
gtan = [list(t) for t in bm.chan_arrays[X.CH_TAN]]
gtopo = [X.decode_id(int(round(gtan[t[0]][0])))["topograph"] for t in gtris]
print(f"island F: {len(gtris)} tris", flush=True)

# ---- 2. the terrace geometry -----------------------------------------------------------------
from ff9mapkit.world.mesh import blob_outline
outline, radii = blob_outline(CX, CZ, base_radius=SHELF_R, seed=SEED, undulation=0.10,
                              n_corners=2, corner_strength=0.15)
n0 = len(outline)
# resample the ring to ~4.4u stations (one tile per quad along the ring)
cum = [0.0]
for i in range(1, n0 + 1):
    a, b = outline[i - 1], outline[i % n0]
    cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
per = cum[-1]
nst = max(8, int(round(per / 4.4)))
stations = []
for s in range(nst):
    d = per * s / nst
    i = max(0, np.searchsorted(cum, d) - 1)
    t01 = (d - cum[i]) / max(1e-9, cum[i + 1] - cum[i])
    a, b = outline[i % n0], outline[(i + 1) % n0]
    stations.append((a[0] + t01 * (b[0] - a[0]), a[1] + t01 * (b[1] - a[1])))
print(f"shelf ring: {nst} stations, perimeter {per:.0f}u", flush=True)

run_per_course = 4.5 / math.tan(math.radians(WALL_SLOPE))
drops = [4.5, 4.5, None]                                   # the last course conforms to ground

def outward(p):
    dx, dz = p[0] - CX, p[1] - CZ
    L = math.hypot(dx, dz) or 1.0
    return dx / L, dz / L

rings = [[(p[0], SHELF_Y, p[1]) for p in stations]]        # ring 0 = the crest (shelf edge)
for k in range(1, N_COURSES + 1):
    ring = []
    for s, p in enumerate(stations):
        ox, oz = outward(p)
        x = p[0] + ox * run_per_course * k
        z = p[1] + oz * run_per_course * k
        if k < N_COURSES:
            y = SHELF_Y - sum(drops[:k])
        else:
            y = None                                       # foot: conform to ground later
        ring.append((x, y, z))
    rings.append(ring)

# hole cut at the FOOT polygon + CLEAR
foot_poly = [(p[0], p[2]) for p in rings[-1]]

def pip(px, pz, poly):
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, zi = poly[i]
        xj, zj = poly[j]
        if (zi > pz) != (zj > pz) and px < (xj - xi) * (pz - zi) / (zj - zi + 1e-12) + xi:
            c = not c
        j = i
    return c

def near(px, pz, poly, d):
    for i in range(len(poly)):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % len(poly)]
        ex, ez = x2 - x1, z2 - z1
        L2 = ex * ex + ez * ez + 1e-12
        t01 = max(0.0, min(1.0, ((px - x1) * ex + (pz - z1) * ez) / L2))
        ddx, ddz = px - (x1 + t01 * ex), pz - (z1 + t01 * ez)
        if ddx * ddx + ddz * ddz < d * d:
            return True
    return False

drop_set = set()
for tdx, tri in enumerate(gtris):
    for i in tri:
        if pip(gpos[i][0], gpos[i][2], foot_poly) or near(gpos[i][0], gpos[i][2], foot_poly, CLEAR):
            drop_set.add(tdx)
            break
fams = Counter(gtopo[t] for t in drop_set)
print(f"island tris dropped: {len(drop_set)} (topos {dict(fams)})", flush=True)
assert set(fams) == {0}, "the hole reaches non-grass island tris -- move/shrink the terrace"

edge_use = Counter()
for tdx, tri in enumerate(gtris):
    if tdx in drop_set:
        continue
    for a, b in ((0, 1), (1, 2), (2, 0)):
        edge_use[tuple(sorted((kk3(gpos[tri[a]]), kk3(gpos[tri[b]]))))] += 1
dropped_edges = set()
for tdx in drop_set:
    tri = gtris[tdx]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        dropped_edges.add(tuple(sorted((kk3(gpos[tri[a]]), kk3(gpos[tri[b]])))))
# the hole ring EXACTLY: kept once-edges that were shared with a dropped tri (no geometric
# filter -- island F is compact and a band filter catches the coast rim's own once-edges)
hole_edges = [e for e, n in edge_use.items() if n == 1 and e in dropped_edges]
adjh = defaultdict(list)
for a, b in hole_edges:
    adjh[a].append(b)
    adjh[b].append(a)
bad = [p for p, l in adjh.items() if len(l) != 2]
assert not bad, f"hole ring not simple ({len(bad)} odd points)"
start = hole_edges[0][0]
hole = [start]
prev = None
while True:
    nxts = [p for p in adjh[hole[-1]] if p != prev]
    if not nxts:
        break
    prev = hole[-1]
    hole.append(nxts[0])
    if hole[-1] == start:
        hole.pop()
        break
print(f"hole ring: {len(hole)} positions", flush=True)

def nearest_ring_y(px, pz):
    return min(hole, key=lambda h: (h[0] - px) ** 2 + (h[2] - pz) ** 2)[1]

rings[-1] = [(x, nearest_ring_y(x, z), z) for (x, y, z) in rings[-1]]  # foot conforms

# ---- 3. emit the terrace tris ----------------------------------------------------------------
ID13 = float(X.encode_id(topograph=13))
ID49 = float(X.encode_id(topograph=49))
ID0 = float(X.encode_id(topograph=0))
new_parents = []                                           # (corners8 x3, idall, fam)

# shelf: crest ring + interior 4u lattice, Delaunay, mains per cell
import random as _rand
rng = _rand.Random(SEED)
shelf_pts = [(p[0], SHELF_Y, p[2]) for p in rings[0]]
xs = [p[0] for p in shelf_pts]
zs = [p[2] for p in shelf_pts]
interior = []
gx = math.floor(min(xs) / 4) * 4
while gx <= max(xs):
    gz = math.floor(min(zs) / 4) * 4
    while gz <= max(zs):
        if pip(gx, gz, [(p[0], p[2]) for p in shelf_pts]) and \
           all((gx - p[0]) ** 2 + (gz - p[2]) ** 2 > 1.6 ** 2 for p in shelf_pts):
            interior.append((gx, SHELF_Y + rng.uniform(-0.3, 0.3), gz))
        gz += 4
    gx += 4
allp = shelf_pts + interior
from ff9mapkit.world.island import _delaunay
tri_i = _delaunay([(p[0], p[2]) for p in allp])
shelf_cells = sorted({(math.floor(sum(allp[i][0] for i in t) / 3 / 4),
                       math.floor(sum(allp[i][2] for i in t) / 3 / 4)) for t in tri_i})
cq, co = G.assign_mains(shelf_cells, seed=0xF93)
n_shelf = 0
for t in tri_i:
    ccx = sum(allp[i][0] for i in t) / 3
    ccz = sum(allp[i][2] for i in t) / 3
    if not pip(ccx, ccz, [(p[0], p[2]) for p in shelf_pts]):
        continue
    cell = (math.floor(ccx / 4), math.floor(ccz / 4))
    a, b, c = (np.asarray(allp[i]) for i in t)
    nrm = np.cross(b - a, c - a)
    order = (a, b, c) if nrm[1] > 0 else (a, c, b)
    corners = []
    for pnt in order:
        u, v = G.mains_uv(float(pnt[0]), float(pnt[2]), cell, cq[cell], co[cell])
        corners.append((float(pnt[0]), float(pnt[1]), float(pnt[2]), u, v, 0.0, 1.0, 0.0))
    new_parents.append((tuple(corners), ID13, "shelf"))
    n_shelf += 1
print(f"shelf: {n_shelf} tris over {len(shelf_cells)} cells", flush=True)

# walls: per course, one 128px tile per quad, u advancing with the 4-col band wrap
n_wall = 0
for k in range(N_COURSES):
    row, cols = COURSE_BANDS[k]
    top, bot = rings[k], rings[k + 1]
    for s in range(nst):
        s2 = (s + 1) % nst
        col = cols[s % 4]
        u0, v0, du_, dv_ = tile_rect(col, row)
        tl = (*top[s], u0, v0)
        tr = (*top[s2], u0 + du_, v0)
        bl = (*bot[s], u0, v0 + dv_)
        br = (*bot[s2], u0 + du_, v0 + dv_)
        for tri3 in ((tl, bl, tr), (tr, bl, br)):
            a, b, c = (np.asarray(p[:3]) for p in tri3)
            nrm = np.cross(b - a, c - a)
            order = tri3 if nrm[1] > 0 else (tri3[0], tri3[2], tri3[1])
            corners = tuple((p[0], p[1], p[2], p[3], p[4], 0.0, 1.0, 0.0) for p in order)
            new_parents.append((corners, ID49, "wall"))
            n_wall += 1
print(f"walls: {n_wall} tris ({N_COURSES} courses x {nst} stations)", flush=True)

# zip annulus: hole ring <-> foot ring (the proven greedy bridge; exact floats)
foot_f = {kk3(p): p for p in rings[-1]}
rim_ord = [kk3(p) for p in rings[-1]]
hole_ord = list(hole)

def signed_area(ring):
    s = 0.0
    for i in range(len(ring)):
        x1, z1 = ring[i][0], ring[i][2]
        x2, z2 = ring[(i + 1) % len(ring)][0], ring[(i + 1) % len(ring)][2]
        s += x1 * z2 - x2 * z1
    return s / 2

if signed_area(hole_ord) * signed_area(rim_ord) < 0:
    rim_ord.reverse()
h0 = hole_ord[0]
k0 = min(range(len(rim_ord)), key=lambda k: (rim_ord[k][0] - h0[0]) ** 2 + (rim_ord[k][2] - h0[2]) ** 2)
rim_ord = rim_ord[k0:] + rim_ord[:k0]

def d2(p, q):
    return (p[0] - q[0]) ** 2 + (p[2] - q[2]) ** 2

NH, NR = len(hole_ord), len(rim_ord)
zip_tris = []
i = j = 0
while i < NH or j < NR:
    h_cur = hole_ord[i % NH]
    r_cur = tuple(foot_f[rim_ord[j % NR]])
    if i < NH and j < NR:
        adv_h = d2(hole_ord[(i + 1) % NH], r_cur) <= d2(h_cur, tuple(foot_f[rim_ord[(j + 1) % NR]]))
    else:
        adv_h = i < NH
    if adv_h:
        zip_tris.append((h_cur, hole_ord[(i + 1) % NH], r_cur))
        i += 1
    else:
        zip_tris.append((h_cur, tuple(foot_f[rim_ord[(j + 1) % NR]]), r_cur))
        j += 1
print(f"zip annulus: {len(zip_tris)} tris", flush=True)

# zip mains: byte-decode island F's per-cell (quad, ori) from kept tris
cell_of = lambda x, z: (int(np.floor(x / 4.0)), int(np.floor(z / 4.0)))
kept_by_cell = defaultdict(list)
for tdx, tri in enumerate(gtris):
    if tdx in drop_set or gtopo[tdx] != 0:
        continue
    us = [guv[i][0] for i in tri]
    lo, hi = G.FAM_REGION["main"][0], G.FAM_REGION["main"][2]
    if not all(lo - 0.02 <= u <= hi + 0.02 for u in us):
        continue
    ccx = sum(gpos[i][0] for i in tri) / 3
    ccz = sum(gpos[i][2] for i in tri) / 3
    kept_by_cell[cell_of(ccx, ccz)].append(tdx)
QUADS = [(u, v) for u in (0, 1) for v in (0, 1)]
ORIS = (0, 90, 180, 270)
_dec = {}

def decode_cell(cell):
    if cell in _dec:
        return _dec[cell]
    best = None
    for tdx in kept_by_cell.get(cell, []):
        tri = gtris[tdx]
        for q in QUADS:
            for o in ORIS:
                err = 0.0
                for i in tri:
                    mu, mv = G.mains_uv(gpos[i][0], gpos[i][2], cell, q, o)
                    err = max(err, abs(mu - guv[i][0]), abs(mv - guv[i][1]))
                if err < 1e-4:
                    best = (q, o)
                    break
            if best:
                break
        if best:
            break
    if best is None:
        i, jj = cell
        rr = _rand.Random((i * 73856093) ^ (jj * 19349663) ^ 0xF93)
        best = (QUADS[rr.randrange(4)], ORIS[rr.randrange(4)])
    _dec[cell] = best
    return best

pos_nrm = {}
for tdx, tri in enumerate(gtris):
    if tdx in drop_set:
        continue
    for i in tri:
        pos_nrm.setdefault(kk3(gpos[i]), list(gnrm[i]))
for tri3 in zip_tris:
    a, b, c = (np.asarray(p, dtype=float) for p in tri3)
    nrm = np.cross(b - a, c - a)
    order = tri3 if nrm[1] > 0 else (tri3[0], tri3[2], tri3[1])
    ccx = float(a[0] + b[0] + c[0]) / 3
    ccz = float(a[2] + b[2] + c[2]) / 3
    cell = cell_of(ccx, ccz)
    q, o = decode_cell(cell)
    corners = []
    for pnt in order:
        key = kk3(pnt)
        n3 = pos_nrm.get(key, [0.0, 1.0, 0.0])
        u, v = G.mains_uv(float(pnt[0]), float(pnt[2]), cell, q, o)
        corners.append((float(pnt[0]), float(pnt[1]), float(pnt[2]), u, v, *n3))
    new_parents.append((tuple(corners), ID0, "zip"))

# smoothed normals for the terrace (shelf+walls) -- position-welded over the NEW soup
acc = defaultdict(lambda: [0.0, 0.0, 0.0])
for corners, idall, fam in new_parents:
    if fam == "zip":
        continue
    a, b, c = (np.asarray(p[:3]) for p in corners)
    nrm = np.cross(b - a, c - a)
    for p in corners:
        v = acc[kk3(p)]
        v[0] += nrm[0]; v[1] += nrm[1]; v[2] += nrm[2]
sm = {}
for k, v in acc.items():
    L = math.sqrt(sum(q * q for q in v)) or 1.0
    sm[k] = [v[0] / L, v[1] / L, v[2] / L]
patched = []
for corners, idall, fam in new_parents:
    if fam == "zip":
        patched.append((corners, idall, fam))
        continue
    corners = tuple((p[0], p[1], p[2], p[3], p[4], *sm[kk3(p)]) for p in corners)
    patched.append((corners, idall, fam))
new_parents = patched

# ---- 4. gates --------------------------------------------------------------------------------
for corners, idall, fam in new_parents:                    # bounds: single block
    for p in corners:
        assert 192.5 < p[0] < 255.5 and -1151.5 < p[2] < -1088.5, "terrace leaves block (3,17)"
_legal_rects = {tile_rect(c, r) for (r, cs) in COURSE_BANDS for c in cs}
for corners, idall, fam in new_parents:                    # every wall tri INSIDE a byte-read rect
    if fam != "wall":
        continue
    us = [p[3] for p in corners]
    vs = [p[4] for p in corners]
    ok = any(u0 - 1e-5 <= min(us) and max(us) <= u0 + du_ + 1e-5 and
             v0 - 1e-5 <= min(vs) and max(vs) <= v0 + dv_ + 1e-5
             for (u0, v0, du_, dv_) in _legal_rects)
    assert ok, f"wall tri uv outside every byte-read band rect: u{min(us):.4f}-{max(us):.4f} v{min(vs):.4f}-{max(vs):.4f}"
down = 0
for corners, _, _ in new_parents:
    a, b, c = (np.asarray(p[:3]) for p in corners)
    if np.cross(b - a, c - a)[1] <= 0:
        down += 1
# assemble the final block mesh
pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []
def emit(p3, u2, n3, idall):
    pos.append([p3[0] - BLOCK * bx, p3[1], p3[2] + BLOCK * (by + 1) - BLOCK])
    uv.append(list(u2)); nrm.append(list(n3)); tan.append([idall, 0.0, 0.0, 1.0])
    flat.append(len(pos) - 1)
for tdx, tri in enumerate(gtris):
    if tdx in drop_set:
        continue
    for i in tri:
        emit(gpos[i], guv[i], gnrm[i], gtan[i][0])
    tris.append([flat[-3], flat[-2], flat[-1]])
for corners, idall, fam in new_parents:
    for p in corners:
        emit(p[:3], (p[3], p[4]), (p[5], p[6], p[7]), idall)
    tris.append([flat[-3], flat[-2], flat[-1]])
new_bm = X.BlockMesh(name=bm.name, disc=1, x=bx, y=by, lod="0_1", vcount=len(pos), stride=48,
                     channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
                     chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm, X.CH_UV: uv, X.CH_TAN: tan},
                     flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])
# crack gate: once-edges near the whole terrace region (world keys)
eu = Counter()
for t in range(len(tris)):
    w = [(pos[i][0] + BLOCK * bx, pos[i][1], pos[i][2] - BLOCK * (by + 1) + BLOCK)
         for i in tris[t]]
    if all(math.hypot(p[0] - CX, p[2] - CZ) > 26 for p in w):
        continue
    for a, b in ((0, 1), (1, 2), (2, 0)):
        eu[tuple(sorted((kk3(w[a]), kk3(w[b]))))] += 1
inner_once = [e for e, n in eu.items() if n == 1
              and math.hypot((e[0][0] + e[1][0]) / 2 - CX, (e[0][2] + e[1][2]) / 2 - CZ) < 19
              and (e[0][1] > 0.05 or e[1][1] > 0.05)]      # y=0 = the coast outline base, not ours
print(f"GATES: down={down} terraceOnceEdges={len(inner_once)}", flush=True)
for e in inner_once[:8]:
    print(f"  once-edge {e[0]} -- {e[1]}", flush=True)
assert down == 0 and not inner_once

import dataclasses
plane = M.fill_missing_grid_quads(X.read_block(12, 0, disc=1, part="sea4"))
hid = lambda nm_: M.hidden_block_mesh(name=nm_, disc=1, x=bx, y=by)  # noqa: E731
sea = dataclasses.replace(plane, x=bx, y=by, name=f"Block[{bx}][{by}] Sea4")
meshlist = [("Object", hid("Object")), ("Terrain", new_bm), ("Sea1", hid("Sea1")),
            ("Sea2", hid("Sea2")), ("Sea3", hid("Sea3")), ("Sea4", sea), ("Sea5", hid("Sea5"))]
cen = P.census(meshlist)
assert len(cen["miss"]) == 0, f"placement MISS: {cen['miss'][:4]}"
lx, lz = CX - BLOCK * bx, CZ + BLOCK * (by + 1) - BLOCK
gy, nm_, _, topo = P.place(meshlist, lx, lz)
print(f"census MISS=0; shelf centre grounds: y={gy:.2f} {nm_} topo {topo}", flush=True)
assert nm_ == "Terrain" and topo == 13 and abs(gy - SHELF_Y) < 0.6

# atlas alpha + shaded render
from PIL import Image
MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
    "textures" / "res(1_24)_terrain.png"
img = Image.open(MOG).convert("RGBA")
W_, H_ = img.size
PX = img.load()
def at_b(u_, v_):
    fx = (u_ % 1.0) * W_ - 0.5
    fy = (1.0 - v_ % 1.0) * H_ - 0.5
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - x0, fy - y0
    acc_ = [0.0, 0.0, 0.0]
    aa = 0.0
    for (dx2, dy2, wgt) in ((0, 0, (1-tx)*(1-ty)), (1, 0, tx*(1-ty)), (0, 1, (1-tx)*ty), (1, 1, tx*ty)):
        px_, py_ = min(max(x0 + dx2, 0), W_ - 1), min(max(y0 + dy2, 0), H_ - 1)
        r, gg, b, a = PX[px_, py_]
        acc_[0] += r*wgt; acc_[1] += gg*wgt; acc_[2] += b*wgt; aa += a*wgt
    return aa, (int(acc_[0]), int(acc_[1]), int(acc_[2]))
blank = 0
for corners, _, _ in new_parents:
    nb = 0
    for ii in range(11):
        for jj in range(11 - ii):
            w0, w1 = ii / 10.0, jj / 10.0
            w2 = 1 - w0 - w1
            if w2 < -1e-9:
                continue
            u_ = w0*corners[0][3] + w1*corners[1][3] + w2*corners[2][3]
            v_ = w0*corners[0][4] + w1*corners[1][4] + w2*corners[2][4]
            if at_b(u_, v_)[0] < 24:
                nb += 1
    if nb:
        blank += 1
print(f"atlas gate: transparent-sampling tris = {blank} (want 0)", flush=True)
assert blank == 0
SC = 16
lo_x = min(v[0] for v in pos) + BLOCK * bx - 2
hi_x = max(v[0] for v in pos) + BLOCK * bx + 2
lo_z = min(v[2] for v in pos) - BLOCK * (by + 1) + BLOCK - 2
hi_z = max(v[2] for v in pos) - BLOCK * (by + 1) + BLOCK + 2
RW, RH = int((hi_x - lo_x) * SC) + 2, int((hi_z - lo_z) * SC) + 2
out = Image.new("RGB", (RW, RH), (24, 40, 72))
op = out.load()
LDIR = (-0.45, 0.8, -0.35)
_l = math.sqrt(sum(q*q for q in LDIR)); LDIR = tuple(q/_l for q in LDIR)
for t in range(len(tris)):
    p3 = [(pos[i][0] + BLOCK * bx, pos[i][1], pos[i][2] - BLOCK * (by + 1) + BLOCK) for i in tris[t]]
    q3 = [uv[i] for i in tris[t]]
    n3 = [nrm[i] for i in tris[t]]
    xs_ = [(pp[0] - lo_x) * SC for pp in p3]
    zs_ = [(pp[2] - lo_z) * SC for pp in p3]
    x0, x1 = int(min(xs_)), int(max(xs_)) + 1
    z0, z1 = int(min(zs_)), int(max(zs_)) + 1
    d = (zs_[1]-zs_[2])*(xs_[0]-xs_[2]) + (xs_[2]-xs_[1])*(zs_[0]-zs_[2])
    if abs(d) < 1e-9:
        continue
    for pyx in range(max(0, x0), min(RW, x1)):
        for pyz in range(max(0, z0), min(RH, z1)):
            w0 = ((zs_[1]-zs_[2])*(pyx-xs_[2]) + (xs_[2]-xs_[1])*(pyz-zs_[2])) / d
            w1 = ((zs_[2]-zs_[0])*(pyx-xs_[2]) + (xs_[0]-xs_[2])*(pyz-zs_[2])) / d
            w2 = 1 - w0 - w1
            if w0 < 0 or w1 < 0 or w2 < 0:
                continue
            aa, rgb = at_b(w0*q3[0][0] + w1*q3[1][0] + w2*q3[2][0],
                           w0*q3[0][1] + w1*q3[1][1] + w2*q3[2][1])
            nx = sum(w * n3[k][0] for k, w in enumerate((w0, w1, w2)))
            ny = sum(w * n3[k][1] for k, w in enumerate((w0, w1, w2)))
            nz = sum(w * n3[k][2] for k, w in enumerate((w0, w1, w2)))
            nl = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
            f = 0.55 + 0.45 * max(0.0, (nx*LDIR[0] + ny*LDIR[1] + nz*LDIR[2]) / nl)
            op[pyx, RH-1-pyz] = (255, 255, 255) if aa < 24 else \
                tuple(min(255, int(cc*f)) for cc in rgb[:3])
OUT_RENDER.parent.mkdir(exist_ok=True)
out.save(OUT_RENDER)
print(f"render -> {OUT_RENDER}", flush=True)

# ---- 5. deploy -------------------------------------------------------------------------------
if len(sys.argv) > 1 and sys.argv[1] == "deploy":
    BK.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(src, BK / f"{src.name}.{ts}")
    outp = M.deploy_override(new_bm, mod_folder="FF9CustomMap-world", part="Terrain")
    print(f"deployed -> {outp} ({len(new_bm.tris)} tris)")
    print(f"DONE -- relaunch (first-time block), teleport {CX:.0f},{CZ:.0f} lands ON the shelf.")
else:
    print("dry run only -- re-run with 'deploy' to write.")
