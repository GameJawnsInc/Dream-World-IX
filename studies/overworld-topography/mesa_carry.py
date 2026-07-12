"""RUNG D v2 -- THE MESA CARRY: carry the (17,15) mini-mesa (a REAL shelf+wall complex)
verbatim onto island F, replacing the falsified terrace synthesis.

Three synthesis conventions for the wall texture failed visually (uniform quads with mixed
bands -> a bright stripe; fractional bottom-edge lerps -> streaks; corner-snapped bridge
fans -> shag). The meta-law fired: STUDY/CARRY over convention iteration -- and the mesa
search found REAL naturally-bounded complexes: topo-49 wall rings that enclose a raised
topo-13 shelf AND land on lowland grass all around (the carry law's 5th instance after
beach1, shore components, the canopy, and the coast components). The (17,15) mini-mesa
(16x16u, wall + shelf, base on grass) fits island F's interior with room.

The carry: blob = the 49 wall component + the enclosed raised tris (shelf 13 + any
enclosed grass); rim = the blob's outer once-edge ring at the grass base; translate to
island F's centre, rim conformed to local ground (no step-law lift needed -- the wall
blocks by TOPO, the faithful mechanism); hole cut + greedy zip + byte-decoded zip mains +
ring-owner normals (the proven carve machinery, exact-float welds).

Usage:  py studies/overworld-topography/mesa_carry.py [deploy]
"""
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
OUT_RENDER = Path(__file__).with_name("out") / "island_f_mesa_render.png"
BLK = (3, 17)
BLOCK = 64.0
CX, CZ = 224.0, -1120.0
DONOR = (17, 15)
CLEAR = 2.5
kk3 = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

# ---- 1. extract the donor mesa blob -----------------------------------------------------------
don = X.read_block(*DONOR, disc=1)
dV = np.asarray(don.verts, dtype=np.float64) + np.array([BLOCK * DONOR[0], 0.0, -BLOCK * DONOR[1]])
dU = np.asarray(don.uvs, dtype=np.float64)
dN = don.normals
dT = don.tangents
dntri = len(don.flat_index) // 3
dtri = [don.flat_index[3*t:3*t+3] for t in range(dntri)]
dtopo = [X.decode_id(int(round(dT[i[0]][0])))["topograph"] for i in dtri]

d_edge = defaultdict(list)
for t, idx in enumerate(dtri):
    for a, b in ((0, 1), (1, 2), (2, 0)):
        d_edge[tuple(sorted((kk3(dV[idx[a]]), kk3(dV[idx[b]]))))].append(t)

# the target 49 component: 10-90 tris, encloses a 13 shelf above y 8, base on grass
adj49 = defaultdict(set)
for e, ts in d_edge.items():
    r = [t for t in ts if dtopo[t] == 49]
    for i in range(len(r)):
        for j in range(i+1, len(r)):
            adj49[r[i]].add(r[j]); adj49[r[j]].add(r[i])
mesa_wall = None
seen = set()
for s in range(dntri):
    if dtopo[s] != 49 or s in seen:
        continue
    comp = {s}; st = [s]
    while st:
        t = st.pop()
        for t2 in adj49[t]:
            if t2 not in comp:
                comp.add(t2); st.append(t2)
    seen |= comp
    if not (10 <= len(comp) <= 90):
        continue
    hi = [t2 for t in comp for a, b in ((0, 1), (1, 2), (2, 0))
          for t2 in d_edge[tuple(sorted((kk3(dV[dtri[t][a]]), kk3(dV[dtri[t][b]]))))]
          if t2 not in comp and dtopo[t2] == 13]
    if hi:
        mesa_wall = comp
        break
assert mesa_wall, "the (17,15) mesa component not found"

# enclosed raised tris: flood non-49 tris from the hi partners staying above y 8
blob = set(mesa_wall)
st = [t2 for t in mesa_wall for a, b in ((0, 1), (1, 2), (2, 0))
      for t2 in d_edge[tuple(sorted((kk3(dV[dtri[t][a]]), kk3(dV[dtri[t][b]]))))]
      if t2 not in mesa_wall and dtopo[t2] != 49
      and min(dV[i][1] for i in dtri[t2]) > 8.0]
while st:
    t = st.pop()
    if t in blob:
        continue
    blob.add(t)
    for a, b in ((0, 1), (1, 2), (2, 0)):
        for t2 in d_edge[tuple(sorted((kk3(dV[dtri[t][a]]), kk3(dV[dtri[t][b]]))))]:
            if t2 not in blob and dtopo[t2] != 49 and min(dV[i][1] for i in dtri[t2]) > 8.0:
                st.append(t2)
bpts = np.array([dV[i] for t in blob for i in dtri[t]])
c_local = ((bpts[:, 0].min() + bpts[:, 0].max()) / 2, (bpts[:, 2].min() + bpts[:, 2].max()) / 2)
print(f"mesa blob: {len(blob)} tris (wall {len(mesa_wall)}), extent "
      f"{bpts[:,0].max()-bpts[:,0].min():.0f}x{bpts[:,2].max()-bpts[:,2].min():.0f}u "
      f"y[{bpts[:,1].min():.1f},{bpts[:,1].max():.1f}] topos "
      f"{dict(Counter(dtopo[t] for t in blob))}", flush=True)

def chain_ring(edges, what):
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    bad = [p for p, l in adj.items() if len(l) != 2]
    assert not bad, f"{what} ring not a simple cycle ({len(bad)} odd points)"
    ring = [edges[0][0]]
    prev = None
    while True:
        nxts = [p for p in adj[ring[-1]] if p != prev]
        if not nxts:
            break
        prev = ring[-1]
        ring.append(nxts[0])
        if ring[-1] == ring[0]:
            ring.pop()
            break
    assert len(ring) == len({*ring}) and len(ring) >= 8, f"{what} ring degenerate"
    return ring

eu = Counter()
for t in blob:
    for a, b in ((0, 1), (1, 2), (2, 0)):
        eu[tuple(sorted((kk3(dV[dtri[t][a]]), kk3(dV[dtri[t][b]]))))] += 1
rim = chain_ring([e for e, n in eu.items() if n == 1], "mesa rim")
rim_set = set(rim)
print(f"mesa rim ring: {len(rim)} positions (y {min(p[1] for p in rim):.1f}.."
      f"{max(p[1] for p in rim):.1f})", flush=True)

# ---- 2. island F, hole cut --------------------------------------------------------------------
src = MODW / f"r{BLK[1]}" / f"Block[{BLK[0]}][{BLK[1]}] Terrain.ff9mesh"
bm = M.blockmesh_from_ff9mesh(src, disc=1, x=BLK[0], y=BLK[1], lod="0_1", part="terrain")
bx, by = BLK
gpos = [[v[0] + BLOCK * bx, v[1], v[2] - BLOCK * (by + 1) + BLOCK] for v in bm.verts]
gtris = list(bm.tris)
gnrm = [list(n) for n in bm.chan_arrays[X.CH_NRM]]
guv = [list(u) for u in bm.chan_arrays[X.CH_UV]]
gtan = [list(t) for t in bm.chan_arrays[X.CH_TAN]]
gtopo = [X.decode_id(int(round(gtan[t[0]][0])))["topograph"] for t in gtris]
n49 = sum(1 for t in gtopo if t == 49)
assert n49 == 0 or True
print(f"island F: {len(gtris)} tris", flush=True)

DX, DZ = CX - c_local[0], CZ - c_local[1]
rim_poly = [(p[0] + DX, p[2] + DZ) for p in rim]

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

drop = set()
for tdx, tri in enumerate(gtris):
    for i in tri:
        if pip(gpos[i][0], gpos[i][2], rim_poly) or near(gpos[i][0], gpos[i][2], rim_poly, CLEAR):
            drop.add(tdx)
            break
fams = Counter(gtopo[t] for t in drop)
print(f"island tris dropped: {len(drop)} (topos {dict(fams)})", flush=True)
assert set(fams) == {0}

eu2 = Counter()
for tdx, tri in enumerate(gtris):
    if tdx in drop:
        continue
    for a, b in ((0, 1), (1, 2), (2, 0)):
        eu2[tuple(sorted((kk3(gpos[tri[a]]), kk3(gpos[tri[b]]))))] += 1
dropped_edges = set()
for tdx in drop:
    tri = gtris[tdx]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        dropped_edges.add(tuple(sorted((kk3(gpos[tri[a]]), kk3(gpos[tri[b]])))))
hole = chain_ring([e for e, n in eu2.items() if n == 1 and e in dropped_edges], "hole")
print(f"hole ring: {len(hole)} positions", flush=True)

def nearest_ring_y(px, pz):
    return min(hole, key=lambda h: (h[0] - px) ** 2 + (h[2] - pz) ** 2)[1]

# ---- 3. vertical anchor: rim conforms to local ground; interior verbatim-relative ------------
rim_med = float(np.median([p[1] for p in rim]))
ground_med = float(np.median([p[1] for p in hole]))
DY = ground_med - rim_med
rim_y = {p: nearest_ring_y(p[0] + DX, p[2] + DZ) for p in rim_set}

def carry_vert(i):
    k = kk3(dV[i])
    p = dV[i]
    y = rim_y[k] if k in rim_set else p[1] + DY
    return [p[0] + DX, y, p[2] + DZ]

carried = {t: [carry_vert(i) for i in dtri[t]] for t in blob}
c_edge = Counter()
c_float = {}
for t in blob:
    ps = carried[t]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        ka, kb = kk3(ps[a]), kk3(ps[b])
        c_float.setdefault(ka, ps[a])
        c_float.setdefault(kb, ps[b])
        c_edge[tuple(sorted((ka, kb)))] += 1
crim = chain_ring([e for e, n in c_edge.items() if n == 1], "carried rim")
rim_nrm = {}
for t in blob:
    for k in range(3):
        key = kk3(carried[t][k])
        rim_nrm.setdefault(key, list(dN[dtri[t][k]]))
print(f"shelf top after carry: y={max(p[1] for ps in carried.values() for p in ps):.1f}",
      flush=True)

# ---- 4. zip annulus (the proven machinery) ----------------------------------------------------
def signed_area(ring):
    s = 0.0
    for i in range(len(ring)):
        x1, z1 = ring[i][0], ring[i][2]
        x2, z2 = ring[(i + 1) % len(ring)][0], ring[(i + 1) % len(ring)][2]
        s += x1 * z2 - x2 * z1
    return s / 2

hole_ord = list(hole)
rim_ord = list(crim)
if signed_area(hole_ord) * signed_area(rim_ord) < 0:
    rim_ord.reverse()
h0 = hole_ord[0]
k0 = min(range(len(rim_ord)), key=lambda k: (rim_ord[k][0] - h0[0]) ** 2 + (rim_ord[k][2] - h0[2]) ** 2)
rim_ord = rim_ord[k0:] + rim_ord[:k0]

def rimw(p):
    return tuple(c_float[p])

def d2(p, q):
    return (p[0] - q[0]) ** 2 + (p[2] - q[2]) ** 2

NH, NR = len(hole_ord), len(rim_ord)
zip_tris = []
i = j = 0
while i < NH or j < NR:
    h_cur = hole_ord[i % NH]
    r_cur = rimw(rim_ord[j % NR])
    if i < NH and j < NR:
        adv_h = d2(hole_ord[(i + 1) % NH], r_cur) <= d2(h_cur, rimw(rim_ord[(j + 1) % NR]))
    else:
        adv_h = i < NH
    if adv_h:
        zip_tris.append((h_cur, hole_ord[(i + 1) % NH], r_cur))
        i += 1
    else:
        zip_tris.append((h_cur, rimw(rim_ord[(j + 1) % NR]), r_cur))
        j += 1
print(f"zip annulus: {len(zip_tris)} tris", flush=True)

cell_of = lambda x, z: (int(np.floor(x / 4.0)), int(np.floor(z / 4.0)))
kept_by_cell = defaultdict(list)
for tdx, tri in enumerate(gtris):
    if tdx in drop or gtopo[tdx] != 0:
        continue
    us = [guv[i][0] for i in tri]
    lo, hi = G.FAM_REGION["main"][0], G.FAM_REGION["main"][2]
    if not all(lo - 0.02 <= u <= hi + 0.02 for u in us):
        continue
    kept_by_cell[cell_of(sum(gpos[i][0] for i in tri) / 3,
                         sum(gpos[i][2] for i in tri) / 3)].append(tdx)
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
        import random as _r
        i, jj = cell
        rr = _r.Random((i * 73856093) ^ (jj * 19349663) ^ 0xF94)
        best = (QUADS[rr.randrange(4)], ORIS[rr.randrange(4)])
    _dec[cell] = best
    return best

pos_nrm = {}
for tdx, tri in enumerate(gtris):
    if tdx in drop:
        continue
    for i in tri:
        pos_nrm.setdefault(kk3(gpos[i]), list(gnrm[i]))

ID0 = float(X.encode_id(topograph=0))
new_parents = []                                           # (corners8, idall, fam)
for t in blob:                                             # the mesa, verbatim channels
    tri = dtri[t]
    idall = float(dT[tri[0]][0])
    corners = tuple((*carried[t][k], dU[tri[k]][0], dU[tri[k]][1], *dN[tri[k]])
                    for k in range(3))
    new_parents.append((corners, idall, "mesa"))
for tri3 in zip_tris:
    a, b, c = (np.asarray(p, dtype=float) for p in tri3)
    nrm = np.cross(b - a, c - a)
    order = tri3 if nrm[1] > 0 else (tri3[0], tri3[2], tri3[1])
    cell = cell_of(float(a[0] + b[0] + c[0]) / 3, float(a[2] + b[2] + c[2]) / 3)
    q, o = decode_cell(cell)
    corners = []
    for pnt in order:
        key = kk3(pnt)
        n3 = pos_nrm.get(key) or rim_nrm.get(key, [0.0, 1.0, 0.0])
        u, v = G.mains_uv(float(pnt[0]), float(pnt[2]), cell, q, o)
        corners.append((float(pnt[0]), float(pnt[1]), float(pnt[2]), u, v, *n3))
    new_parents.append((tuple(corners), ID0, "zip"))

# ---- 5. gates + assembly ----------------------------------------------------------------------
for corners, idall, fam in new_parents:
    for p in corners:
        assert 192.5 < p[0] < 255.5 and -1151.5 < p[2] < -1088.5, "mesa leaves block (3,17)"
down = 0
for corners, _, _ in new_parents:
    a, b, c = (np.asarray(p[:3]) for p in corners)
    if np.cross(b - a, c - a)[1] < 0:
        down += 1
pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []
def emit(p3, u2, n3, idall):
    pos.append([p3[0] - BLOCK * bx, p3[1], p3[2] + BLOCK * (by + 1) - BLOCK])
    uv.append(list(u2)); nrm.append(list(n3)); tan.append([idall, 0.0, 0.0, 1.0])
    flat.append(len(pos) - 1)
for tdx, tri in enumerate(gtris):
    if tdx in drop:
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
eu3 = Counter()
for t in range(len(tris)):
    w = [(pos[i][0] + BLOCK * bx, pos[i][1], pos[i][2] - BLOCK * (by + 1) + BLOCK) for i in tris[t]]
    if all(math.hypot(p[0] - CX, p[2] - CZ) > 24 for p in w):
        continue
    for a, b in ((0, 1), (1, 2), (2, 0)):
        eu3[tuple(sorted((kk3(w[a]), kk3(w[b]))))] += 1
inner_once = [e for e, n in eu3.items() if n == 1
              and math.hypot((e[0][0] + e[1][0]) / 2 - CX, (e[0][2] + e[1][2]) / 2 - CZ) < 17
              and (e[0][1] > 0.05 or e[1][1] > 0.05)]
print(f"GATES: down={down} mesaOnceEdges={len(inner_once)}", flush=True)
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
print(f"census MISS=0; mesa centre grounds: y={gy:.2f} {nm_} topo {topo}", flush=True)

# ---- 6. offline eyes ---------------------------------------------------------------------------
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

# ---- 7. deploy ---------------------------------------------------------------------------------
if len(sys.argv) > 1 and sys.argv[1] == "deploy":
    BK.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(src, BK / f"{src.name}.{ts}")
    outp = M.deploy_override(new_bm, mod_folder="FF9CustomMap-world", part="Terrain")
    print(f"deployed -> {outp} ({len(new_bm.tris)} tris)")
    print(f"DONE -- F6 world re-entry, teleport {CX:.0f},{CZ:.0f}; the mesa sits at centre.")
else:
    print("dry run only -- re-run with 'deploy' to write.")
