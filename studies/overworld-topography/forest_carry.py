"""RUNG A v3 -- VERBATIM FOREST CARRY: transplant block (15,15)'s single canopy
blob (132 tris, grass-bounded) onto the pad (3,14) whole: geometry/UV/topo verbatim,
rim snapped to pad ground, pad lattice hole + grass zip annulus. Gates: crack/
up-facing/grain/weld-audit/bounds."""
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X
from ff9mapkit.world import mesh as M

from ff9mapkit import config as _cfg
GP = Path(_cfg.find_game_path(None))
SRC = GP / r"FF9CustomMap-world\FF9_Data\WorldMap\Disc1\0_1\r14\Block[3][14] Terrain.ff9mesh"
BK = Path(__file__).resolve().parents[2] / "backups"
PAD_H = 3.0
TARGET = (32.0, -32.0)                     # pad-local target center for the blob

# ---- 1. extract the donor blob verbatim ---------------------------------------
don = X.read_block(15, 15)
dv = np.asarray(don.verts, dtype=np.float64)
duv = np.asarray(don.uvs, dtype=np.float64)
dtan = don.tangents
dtopo = [X.decode_id(int(dtan[t[0]][0]))["topograph"] for t in don.tris]
kf = lambda a, i: (round(a[i][0], 3), round(a[i][1], 3), round(a[i][2], 3))
ftris = [t for t in range(len(don.tris)) if dtopo[t] == 37]
# single blob (proven by the scan) -- take all 37 tris
blob = ftris
bpts = np.array([dv[i] for t in blob for i in don.tris[t]])
c_local = ((bpts[:, 0].min() + bpts[:, 0].max()) / 2, (bpts[:, 2].min() + bpts[:, 2].max()) / 2)
print(f"donor blob: {len(blob)} tris, extent "
      f"{bpts[:,0].max()-bpts[:,0].min():.0f}x{bpts[:,2].max()-bpts[:,2].min():.0f}u", flush=True)

# blob rim ring: once-edges of the blob (position-keyed), chained in order
edge_use = Counter()
for t in blob:
    tri = don.tris[t]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        e = tuple(sorted((kf(dv, tri[a]), kf(dv, tri[b]))))
        edge_use[e] += 1
rim_edges = [e for e, n in edge_use.items() if n == 1]
adjr = defaultdict(list)
for a, b in rim_edges:
    adjr[a].append(b)
    adjr[b].append(a)
start = rim_edges[0][0]
rim = [start]
prev = None
while True:
    nxts = [p for p in adjr[rim[-1]] if p != prev]
    if not nxts:
        break
    prev = rim[-1]
    rim.append(nxts[0])
    if rim[-1] == start:
        rim.pop()
        break
print(f"rim ring: {len(rim)} positions (h {min(p[1] for p in rim):.1f}..{max(p[1] for p in rim):.1f})", flush=True)
assert len(rim) >= 12
rim_set = set(rim)

# translation donor-local -> pad-local
DX, DZ = TARGET[0] - c_local[0], TARGET[1] - c_local[1]
rim_med = float(np.median([p[1] for p in rim]))
DY = PAD_H - rim_med

# THE CANOPY STEP LAW: wall faces are VERTICAL curtains; the engine's step-up
# ceiling is 2.34375u (w_nwpHit rayStartOffsetY). Set each rim (wall-base) vert
# so every adjacent wall face rises <= MAX_RISE -- the grass annulus slopes up
# to meet it (like donor ground rising toward a real forest).
MAX_RISE = 2.2
rim_y = {p: PAD_H for p in rim_set}
for t in blob:
    tri = don.tris[t]
    ks = [kf(dv, i) for i in tri]
    if not any(k in rim_set for k in ks):
        continue
    top = max(dv[i][1] + DY for i, k in zip(tri, ks) if k not in rim_set) if \
        any(k not in rim_set for k in ks) else None
    if top is None:
        continue
    need = top - MAX_RISE
    for k in ks:
        if k in rim_set and need > rim_y[k]:
            rim_y[k] = need
print(f"rim lifts: max {max(rim_y.values()) - PAD_H:.2f}u above pad ground "
      f"({sum(1 for y in rim_y.values() if y > PAD_H + 0.01)} of {len(rim_y)} verts lifted)", flush=True)

def carry_vert(i):
    k = kf(dv, i)
    p = dv[i]
    y = rim_y[k] if k in rim_set else p[1] + DY
    return [p[0] + DX, y, p[2] + DZ]

# ---- 2. load the pad, cut the hole ----------------------------------------------
bm = M.blockmesh_from_ff9mesh(SRC, disc=1, x=3, y=14, lod="0_1", part="terrain")
v = bm.chan_arrays[X.CH_POS]
uv = bm.chan_arrays[X.CH_UV]
nrm = bm.chan_arrays.get(X.CH_NRM)
tan = bm.chan_arrays[X.CH_TAN]
ptopo = [X.decode_id(int(tan[t[0]][0]))["topograph"] for t in bm.tris]

# NOTE: this pad may still carry the v2 dome -- rebuild it fresh first? The v2 backup
# is the PRE-dome pad; restore from it in-memory by requiring the caller to have re-run
# world-reclaim OR use the backup. We use the ff9mesh AS ON DISK -- so restore first!
print("pad tris:", len(bm.tris), flush=True)

rim_poly = np.array([(p[0] + DX, p[2] + DZ) for p in rim])

def inside_poly(x, z):
    n = len(rim_poly)
    c = False
    j = n - 1
    for i in range(n):
        xi, zi = rim_poly[i]
        xj, zj = rim_poly[j]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi + 1e-12) + xi:
            c = not c
        j = i
    return c

def near_poly(x, z, d):
    n = len(rim_poly)
    for i in range(n):
        x1, z1 = rim_poly[i]
        x2, z2 = rim_poly[(i + 1) % n]
        px, pz = x2 - x1, z2 - z1
        L2 = px * px + pz * pz + 1e-12
        t01 = max(0, min(1, ((x - x1) * px + (z - z1) * pz) / L2))
        ddx, ddz = x - (x1 + t01 * px), z - (z1 + t01 * pz)
        if ddx * ddx + ddz * ddz < d * d:
            return True
    return False

CLEAR = 2.5                                  # annulus clearance around the rim
drop = set()
for t, tri in enumerate(bm.tris):
    for i in tri:
        x, z = v[i][0], v[i][2]
        if inside_poly(x, z) or near_poly(x, z, CLEAR):
            drop.add(t)
            break
print(f"pad tris dropped for the hole: {len(drop)} "
      f"(topos {dict(Counter(ptopo[t] for t in drop))})", flush=True)
assert all(ptopo[t] in (0,) for t in drop), "hole reaches non-grass pad tris -- move TARGET"

# hole boundary ring of the remaining pad: once-edges among dropped-vs-kept
kv = lambda i: (round(v[i][0], 3), round(v[i][1], 3), round(v[i][2], 3))
edge_use2 = Counter()
for t, tri in enumerate(bm.tris):
    if t in drop:
        continue
    for a, b in ((0, 1), (1, 2), (2, 0)):
        edge_use2[tuple(sorted((kv(tri[a]), kv(tri[b]))))] += 1
# candidate hole-ring edges: once-edges whose both ends are near the poly
hole_edges = [e for e, n in edge_use2.items() if n == 1
              and near_poly(e[0][0], e[0][2], CLEAR + 6.5) and near_poly(e[1][0], e[1][2], CLEAR + 6.5)]
adjh = defaultdict(list)
for a, b in hole_edges:
    adjh[a].append(b)
    adjh[b].append(a)
deg_bad = [p for p, l in adjh.items() if len(l) != 2]
assert not deg_bad, f"hole ring not a simple cycle ({len(deg_bad)} odd-degree points)"
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
assert len(hole) >= 12

# ---- 3. zip annulus between hole ring (grass, y=PAD_H) and blob rim (y=PAD_H) -----
# ---- carried blob geometry (exact floats -- the zip must share THESE bits) --------
carried = {t: [carry_vert(i) for i in don.tris[t]] for t in blob}
kk3 = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
c_edge_use = Counter()
c_float = {}
for t in blob:
    ps = carried[t]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        ka, kb = kk3(ps[a]), kk3(ps[b])
        c_float.setdefault(ka, ps[a])
        c_float.setdefault(kb, ps[b])
        c_edge_use[tuple(sorted((ka, kb)))] += 1
c_rim_edges = [e for e, n in c_edge_use.items() if n == 1]
adjc = defaultdict(list)
for a, b in c_rim_edges:
    adjc[a].append(b)
    adjc[b].append(a)
start = c_rim_edges[0][0]
crim = [start]
prev = None
while True:
    nxts = [p for p in adjc[crim[-1]] if p != prev]
    if not nxts:
        break
    prev = crim[-1]
    crim.append(nxts[0])
    if crim[-1] == start:
        crim.pop()
        break
print(f"carried rim ring: {len(crim)} positions (from {len(c_rim_edges)} once-edges)", flush=True)
assert len(crim) == len(c_rim_edges), "carried rim is not a simple cycle"

def signed_area(ring):
    s = 0.0
    for k in range(len(ring)):
        x1, z1 = ring[k][0], ring[k][2]
        x2, z2 = ring[(k + 1) % len(ring)][0], ring[(k + 1) % len(ring)][2]
        s += x1 * z2 - x2 * z1
    return s / 2
hole_ord = list(hole)                                   # CHAIN order (adjacency-true)
rim_ord = list(crim)                                    # CARRIED-float keys, chain order
if signed_area(hole_ord) * signed_area(rim_ord) < 0:
    rim_ord.reverse()
# grass UV basis: copy the modal grass tile triplet of the pad (stretch is acceptable on the bench)
gtile = None
for t, tri in enumerate(bm.tris):
    if t not in drop and ptopo[t] == 0:
        gtile = [list(uv[i]) for i in tri]
        break
NH, NR = len(hole_ord), len(rim_ord)
def rimw(p):
    return tuple(c_float[p])                        # the carried vert's EXACT floats
# rotate the rim ring so rim_ord[0] is spatially nearest hole_ord[0]
h0 = hole_ord[0]
k0 = min(range(NR), key=lambda k: (rim_ord[k][0] - h0[0]) ** 2 + (rim_ord[k][2] - h0[2]) ** 2)
rim_ord = rim_ord[k0:] + rim_ord[:k0]
def d2(p, q):
    return (p[0] - q[0]) ** 2 + (p[2] - q[2]) ** 2
zip_tris = []
i = j = 0
while i < NH or j < NR:
    h_cur = hole_ord[i % NH]
    r_cur = rimw(rim_ord[j % NR])
    can_h, can_r = i < NH, j < NR
    if can_h and can_r:
        adv_h = d2(hole_ord[(i + 1) % NH], r_cur) <= d2(h_cur, rimw(rim_ord[(j + 1) % NR]))
    else:
        adv_h = can_h
    if adv_h:
        zip_tris.append((h_cur, hole_ord[(i + 1) % NH], r_cur))
        i += 1
    else:
        zip_tris.append((h_cur, rimw(rim_ord[(j + 1) % NR]), r_cur))
        j += 1
print(f"zip annulus: {len(zip_tris)} tris (greedy bridge walk)", flush=True)

# ---- 4. assemble the new mesh ------------------------------------------------------
NV, NU, NN, NT, NI = [], [], [], [], []
def emit(p, u, n, t4):
    NV.append(list(p)); NU.append(list(u)); NN.append(list(n)); NT.append(list(t4))
    NI.append(len(NV) - 1)
UP = [0.0, 1.0, 0.0]
GRASS_T = float(X.encode_id(topograph=0))
# kept pad tris
for t, tri in enumerate(bm.tris):
    if t in drop:
        continue
    for i in tri:
        emit(v[i], uv[i], nrm[i] if nrm else UP, tan[i])
# carried blob tris (verbatim channels; translated)
for t in blob:
    tri = don.tris[t]
    for i in tri:
        emit(carry_vert(i), duv[i], don.normals[i] if don.normals else UP, dtan[i])
# zip annulus (grass)
for tri3 in zip_tris:
    a, b, c = (np.asarray(p, dtype=np.float64) for p in tri3)
    n = np.cross(b - a, c - a)
    order = (a, b, c) if n[1] > 0 else (a, c, b)
    for k, p in enumerate(order):
        emit(p, gtile[k], UP, [GRASS_T, 0.0, 0.0, 1.0])

new = X.BlockMesh(name=bm.name, disc=1, x=3, y=14, lod="0_1", vcount=len(NV), stride=48,
                  channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
                  chan_arrays={X.CH_POS: NV, X.CH_NRM: NN, X.CH_UV: NU, X.CH_TAN: NT},
                  flat_index=NI, tris=[[NI[k], NI[k+1], NI[k+2]] for k in range(0, len(NI), 3)],
                  raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])

# ---- 5. GATES -----------------------------------------------------------------------
va = np.asarray(NV)
down = 0
maxe = 0.0
for k in range(0, len(NI), 3):
    a, b, c = va[k], va[k+1], va[k+2]
    n = np.cross(b - a, c - a)
    if n[1] < 0:
        down += 1
    for pq in ((a, b), (b, c), (c, a)):
        maxe = max(maxe, float(np.linalg.norm(pq[0] - pq[1])))
oob = int(((va[:, 0] < -0.5) | (va[:, 0] > 64.5) | (va[:, 2] < -64.5) | (va[:, 2] > 0.5)).sum())
# weld audit: near-miss pairs (<0.05u apart but not identical) around the two rings
ring_pts = np.array([list(p) for p in hole_ord] + [list(rimw(p)) for p in rim_ord])
nm = 0
for a_ in range(len(ring_pts)):
    d2 = np.sum((ring_pts - ring_pts[a_]) ** 2, axis=1)
    nm += int(((d2 > 1e-9) & (d2 < 0.0025)).sum())
# crack gate: once-edges of the whole mesh should form only the block frame + sand/sea borders --
# count once-edges INSIDE the annulus zone (should be 0)
eu = Counter()
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
for k in range(0, len(NI), 3):
    for a, b in ((0, 1), (1, 2), (2, 0)):
        eu[tuple(sorted((kk(va[k + a]), kk(va[k + b]))))] += 1
inner_once = [e for e, n in eu.items() if n == 1
              and near_poly((e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2, CLEAR + 5.0)]
# the CANOPY STEP gate: every carried wall face must rise <= the 2.34375 step ceiling
worst_rise = 0.0
for t in blob:
    ps = carried[t]
    ks = [kk3(p) for p in ps]
    if any(k in {kk3(c_float[r]) for r in crim} for k in ks):
        rise = max(p[1] for p in ps) - min(p[1] for p in ps)
        worst_rise = max(worst_rise, rise)
print(f"GATES: down={down} maxEdge={maxe:.1f} oob={oob} nearMiss={nm//2} "
      f"annulusOnceEdges={len(inner_once)} worstWallRise={worst_rise:.2f}")
assert worst_rise <= 2.34, f"a wall face still rises {worst_rise:.2f} > the 2.34 step ceiling"
if inner_once:
    hset, rset = set(hole_ord), {kk(rimw(p)) for p in rim_ord}
    print(f"  ring sizes: rim_edges={len(rim_edges)} rim_chain={len(rim)} "
          f"hole_edges={len(hole_edges)} hole_chain={len(hole)}")
    for e in inner_once[:12]:
        side = ("hole" if e[0] in hset or e[1] in hset else
                "rim" if e[0] in rset or e[1] in rset else "??")
        print(f"  once-edge [{side}] {e[0]} -- {e[1]}")
assert down == 0 and oob == 0 and nm == 0 and not inner_once and maxe < 9.0

# ---- 6. backup + deploy ----------------------------------------------------------------
BK.mkdir(exist_ok=True)
bak = BK / f"Block[3][14] Terrain.ff9mesh.{time.strftime('%Y%m%d-%H%M%S')}"
shutil.copyfile(SRC, bak)
out = M.deploy_override(new, mod_folder="FF9CustomMap-world", part="Terrain")
print(f"backup -> {bak}\ndeployed -> {out} ({len(new.tris)} tris)")
