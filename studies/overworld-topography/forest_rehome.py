"""RUNG B -- FOREST RE-HOME: carry block (15,15)'s canopy blob onto ISLAND E (the
grass-island canvas), retiring the flat (3,14) bench.

Composes the proven `forest_carry.py` recipe (CANOPY CARRY + STEP + ROUND-AFTER-TRANSLATE
WELD laws) with island E's own machinery, upgrading the two bench-only shortcuts:

* the carve runs on the island's WORLD soup (deterministic rebuild of the deployed seed-55
  landmass), so the blob may straddle 64u block borders -- new tris re-split with the
  island's own border discipline (generic-lerp S-H clip carrying uv+normal);
* the zip annulus gets FAITHFUL per-cell mains UVs: each 4u cell's (quadrant, orientation)
  is DECODED from the kept tris' own UV bytes (16-hypothesis exact match), never re-derived
  (assign_mains is a sequential RNG -- unreproducible without the exact original cell set);
  fully-dropped cells fall back to a deterministic in-language pick (avoid-same vs W/S).
  Zip normals copy their ring owners (island smoothed / donor rim) -- hard-up normals are
  off-language on rolling ground.

Gates: dropped-tris-all-plain-grass, simple hole ring, annulus once-edges == 0, worst wall
AND zip face rise <= 2.34375 (the engine step ceiling), zip walk-filter ny > 0.1, grain,
near-miss weld audit, per-changed-block placement census MISS == 0 (blob centre grounds on
topo 37), Moguri-atlas alpha == 0 over new tris, byte-differential (rebuild == deployed
bytes for untouched blocks), and the shaded top-down render (the offline eye).

Usage:  py studies/overworld-topography/forest_rehome.py [deploy]
"""
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
from ff9mapkit.world.island import build_landmass, _sea_plane, BLOCK

GP = Path(_cfg.find_game_path(None))
MODW = GP / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
BK = Path(__file__).resolve().parents[2] / "backups"
OUT_RENDER = Path(__file__).with_name("out") / "island_e_forest_render.png"

CENTER, RADIUS, SEED, LOBES = (344, -1152), 46, 55, 3      # island E, as deployed
DONOR_BLK = (15, 15)                                        # the clean canopy donor
CLEAR = 2.5                                                 # annulus clearance
SCAN_BAND = CLEAR + 4.0                                     # mains-only zone: dropped + hole-boundary tris
RING_BAND = CLEAR + 6.5                                     # hole-ring once-edge capture (the proven filter)
MAX_RISE = 2.25                                             # per-face ceiling (engine 2.34375)
SAFE_RISE = 2.10                                            # neighborhood lift bound (one step inside)
LIFT_REACH = 0.9                                            # canopy neighborhood radius for the lift
S_STEP = 0.65                                               # engine foot step ~0.44/frame + margin
GATE_CLIMB = 2.30                                           # single-step crossing ceiling (engine 2.34375)
RIM_MARGIN = 5.0                                            # envelope keeps this far from the coast rim
kk3 = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

# ---- 1. deterministic island E rebuild --------------------------------------------------
print("rebuilding island E (seed 55) ...", flush=True)
built = build_landmass(center=CENTER, base_radius=RADIUS, seed=SEED, lobes=LOBES,
                       stamps="auto")
gpos = built["world"]["pos"]
gtris = built["world"]["tris"]
gmeta = built["world"]["meta"]
gnrm = built["world"]["nrm"]
blocks = sorted(built["blocks"])
print("blocks:", blocks, flush=True)

# byte-differential (informational): which deployed blocks match the CLEAN rebuild? A
# mismatch = a prior carve deploy -- fine, the deploy step below converges by byte-compare.
import tempfile
_tmp = Path(tempfile.mkdtemp(prefix="ff9_rehome_ref_"))
ref_bytes = {}
for blk, bm in built["blocks"].items():
    p = M.write_ff9mesh(bm, _tmp / f"ref_{blk[0]}_{blk[1]}.ff9mesh")
    ref_bytes[blk] = p.read_bytes()
    dep = MODW / f"r{blk[1]}" / f"Block[{blk[0]}][{blk[1]}] Terrain.ff9mesh"
    assert dep.exists(), f"deployed file missing: {dep}"
    state = "clean-rebuild" if dep.read_bytes() == ref_bytes[blk] else "prior-carve"
    print(f"  deployed {blk}: {state}", flush=True)

# ---- 2. donor blob, verbatim, in WORLD frame --------------------------------------------
don = X.read_block(*DONOR_BLK)
dv = np.asarray(don.verts, dtype=np.float64)
dv_w = dv + np.array([BLOCK * DONOR_BLK[0], 0.0, -BLOCK * DONOR_BLK[1]])
duv = np.asarray(don.uvs, dtype=np.float64)
dnrm = don.normals
dtan = don.tangents
dtopo = [X.decode_id(int(dtan[t[0]][0]))["topograph"] for t in don.tris]
blob = [t for t in range(len(don.tris)) if dtopo[t] == 37]
bpts = np.array([dv_w[i] for t in blob for i in don.tris[t]])
c_local = ((bpts[:, 0].min() + bpts[:, 0].max()) / 2, (bpts[:, 2].min() + bpts[:, 2].max()) / 2)
ext = (bpts[:, 0].max() - bpts[:, 0].min(), bpts[:, 2].max() - bpts[:, 2].min())
print(f"donor blob: {len(blob)} tris, extent {ext[0]:.0f}x{ext[1]:.0f}u", flush=True)

def chain_ring(edges, what):
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    bad = [p for p, l in adj.items() if len(l) != 2]
    assert not bad, f"{what} ring not a simple cycle ({len(bad)} odd-degree points)"
    start = edges[0][0]
    ring = [start]
    prev = None
    while True:
        nxts = [p for p in adj[ring[-1]] if p != prev]
        if not nxts:
            break
        prev = ring[-1]
        ring.append(nxts[0])
        if ring[-1] == start:
            ring.pop()
            break
    assert len(ring) == len({*ring}) and len(ring) >= 12, f"{what} ring degenerate"
    return ring

edge_use = Counter()
for t in blob:
    tri = don.tris[t]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        edge_use[tuple(sorted((kk3(dv_w[tri[a]]), kk3(dv_w[tri[b]]))))] += 1
rim = chain_ring([e for e, n in edge_use.items() if n == 1], "donor rim")
rim_set = set(rim)
print(f"donor rim ring: {len(rim)} positions", flush=True)

# ---- 3. placement scan: the envelope must sit on PLAIN GRASS MAINS only ------------------
rim_poly_local = [(p[0], p[2]) for p in rim]
coast = built["rim"]                                        # the island's grass/wall weld ring

def poly_at(dx, dz):
    return [(x + dx, z + dz) for (x, z) in rim_poly_local]

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

def coast_d2(px, pz):
    return min((px - x) ** 2 + (pz - z) ** 2 for (x, z) in coast)

tri_c = []
for tidx, tri in enumerate(gtris):
    a, b, c = (gpos[i] for i in tri)
    tri_c.append(((a[0] + b[0] + c[0]) / 3, (a[2] + b[2] + c[2]) / 3))

cands = []
gx0 = 4 * round((CENTER[0] - 40) / 4)
gz0 = 4 * round((CENTER[1] - 40) / 4)
for gx in range(gx0, gx0 + 84, 4):
    for gz in range(gz0, gz0 + 84, 4):
        dx, dz = gx - c_local[0], gz - c_local[1]
        poly = poly_at(dx, dz)
        ok = True
        seen = 0
        for tidx, tri in enumerate(gtris):
            cx, cz = tri_c[tidx]
            hit = pip(cx, cz, poly) or near(cx, cz, poly, SCAN_BAND)
            if not hit:
                hit = any(pip(gpos[i][0], gpos[i][2], poly) or
                          near(gpos[i][0], gpos[i][2], poly, SCAN_BAND) for i in tri)
            if not hit:
                continue
            seen += 1
            _, idall, fam, _ = gmeta[tidx]
            topo = X.decode_id(int(round(idall)))["topograph"]
            if fam != "main" or topo != 0:
                ok = False
                break
            for i in tri:
                if coast_d2(gpos[i][0], gpos[i][2]) < RIM_MARGIN ** 2:
                    ok = False
                    break
            if not ok:
                break
        if ok and seen >= 40:
            d_rim = min(coast_d2(x, z) for (x, z) in poly) ** 0.5
            cands.append((round(d_rim, 1), -gx, gx, gz))
assert cands, "no lawful placement -- island E has no plain-grass pocket for this blob"
cands.sort(reverse=True)
d_rim, _, TX, TZ = cands[0]
DX, DZ = TX - c_local[0], TZ - c_local[1]
print(f"placement: blob centre -> world ({TX},{TZ})  (rim clearance {d_rim}u, "
      f"{len(cands)} lawful candidates)", flush=True)

# ---- 4. carve the hole -------------------------------------------------------------------
poly = poly_at(DX, DZ)
drop = set()
for tidx, tri in enumerate(gtris):
    for i in tri:
        if pip(gpos[i][0], gpos[i][2], poly) or near(gpos[i][0], gpos[i][2], poly, CLEAR):
            drop.add(tidx)
            break
dropped_fams = Counter(gmeta[t][2] for t in drop)
print(f"island tris dropped for the hole: {len(drop)} (fams {dict(dropped_fams)})", flush=True)
assert set(dropped_fams) <= {"main"}, "hole reaches non-mains island tris -- placement bug"

edge_use2 = Counter()
for tidx, tri in enumerate(gtris):
    if tidx in drop:
        continue
    for a, b in ((0, 1), (1, 2), (2, 0)):
        edge_use2[tuple(sorted((kk3(gpos[tri[a]]), kk3(gpos[tri[b]]))))] += 1
hole_edges = [e for e, n in edge_use2.items() if n == 1
              and near(e[0][0], e[0][2], poly, RING_BAND) and near(e[1][0], e[1][2], poly, RING_BAND)]
hole = chain_ring(hole_edges, "hole")
print(f"hole ring: {len(hole)} positions", flush=True)

# island smoothed normal per position (for zip corners on the hole ring)
pos_nrm = {}
for tidx, tri in enumerate(gtris):
    if tidx in drop:
        continue
    for i in tri:
        pos_nrm.setdefault(kk3(gpos[i]), list(gnrm[i]))

# ---- 5. vertical anchor + THE CANOPY STEP LAW (comprehensive form) ------------------------
# The engine's climb check is SURFACE-to-SURFACE across ONE STEP (~0.44u/frame on foot):
# crossing the un-hittable vertical wall, the candidate lands up to a step INSIDE, so the
# effective climb = the wall jump + one step of interior dome slope. The bench's per-face
# 2.2 left 0.14u of margin and the dome slope ate it (the island E stuck report). Lift each
# rim vert against the NEIGHBORHOOD canopy max within LIFT_REACH (one step) at SAFE_RISE.
ground_med = float(np.median([p[1] for p in hole]))
rim_med = float(np.median([p[1] for p in rim]))
DY = ground_med - rim_med

def nearest_ring_y(px, pz):
    return min(hole, key=lambda h: (h[0] - px) ** 2 + (h[2] - pz) ** 2)[1]

interior = [(dv_w[i][0], dv_w[i][1] + DY, dv_w[i][2])
            for t in blob for i in don.tris[t] if kk3(dv_w[i]) not in rim_set]
rim_y = {}
for p in rim_set:
    rim_y[p] = nearest_ring_y(p[0] + DX, p[2] + DZ)
for t in blob:                                             # per-face floor (always applies)
    tri = don.tris[t]
    ks = [kk3(dv_w[i]) for i in tri]
    tops = [dv_w[i][1] + DY for i, k in zip(tri, ks) if k not in rim_set]
    if not tops or not any(k in rim_set for k in ks):
        continue
    need = max(tops) - MAX_RISE
    for k in ks:
        if k in rim_set and need > rim_y[k]:
            rim_y[k] = need
# per-STATION lift along each rim edge: the launch pad (the zip surface at the wall base,
# lerped between the edge's rim verts) must sit within SAFE_RISE of the EXACT canopy surface
# one step inside every station -- vert-radius neighborhoods miss mid-edge stations on the
# donor's long (up to 8u) rim edges. Both endpoints lift (lerp-safe, slightly conservative).
def canopy_y_at(px, pz):
    """Exact carried-canopy surface height at (px, pz) in the DONOR frame (+DY), or None."""
    for t in blob:
        tri = don.tris[t]
        a, b, c = (dv_w[i] for i in tri)
        d = (b[2]-c[2])*(a[0]-c[0]) + (c[0]-b[0])*(a[2]-c[2])
        if abs(d) < 1e-12:
            continue
        w0 = ((b[2]-c[2])*(px-c[0]) + (c[0]-b[0])*(pz-c[2])) / d
        w1 = ((c[2]-a[2])*(px-c[0]) + (a[0]-c[0])*(pz-c[2])) / d
        w2 = 1 - w0 - w1
        if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
            continue
        return w0*a[1] + w1*b[1] + w2*c[1] + DY
    return None

SAFE_TARGET = SAFE_RISE                                    # pad-to-canopy bound per station
nrim = len(rim)
for e0 in range(nrim):
    p, q = rim[e0], rim[(e0 + 1) % nrim]
    ex, ez = q[0] - p[0], q[2] - p[2]
    el = (ex * ex + ez * ez) ** 0.5
    if el < 1e-6:
        continue
    nxi, nzi = -ez / el, ex / el                           # a normal; resolve inward below
    mx, mz = p[0] + ex * 0.5, p[2] + ez * 0.5
    if canopy_y_at(mx + nxi * 0.4, mz + nzi * 0.4) is None:
        nxi, nzi = -nxi, -nzi                              # flip toward the canopy side
    nst = max(1, int(el / 0.4))
    for s in range(nst + 1):
        t01 = s / nst
        sx, sz = p[0] + ex * t01, p[2] + ez * t01
        tops = []
        for dd in (0.15, 0.3, 0.45, 0.6, 0.75):
            cy = canopy_y_at(sx + nxi * dd, sz + nzi * dd)
            if cy is not None:
                tops.append(cy)
        if not tops:
            continue
        need = max(tops) - SAFE_TARGET
        for k in (p, q):
            if need > rim_y[k]:
                rim_y[k] = need
lifts = [rim_y[p] - nearest_ring_y(p[0] + DX, p[2] + DZ) for p in rim_set]
print(f"rim lifts vs local ground: max {max(lifts):.2f}u "
      f"({sum(1 for v in lifts if v > 0.01)} of {len(lifts)} lifted)", flush=True)

def carry_vert(i):
    k = kk3(dv_w[i])
    p = dv_w[i]
    y = rim_y[k] if k in rim_set else p[1] + DY
    return [p[0] + DX, y, p[2] + DZ]

# carried rim ring from the CARRIED floats (the round-after-translate weld law)
carried = {t: [carry_vert(i) for i in don.tris[t]] for t in blob}
c_edge_use = Counter()
c_float = {}
for t in blob:
    ps = carried[t]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        ka, kb = kk3(ps[a]), kk3(ps[b])
        c_float.setdefault(ka, ps[a])
        c_float.setdefault(kb, ps[b])
        c_edge_use[tuple(sorted((ka, kb)))] += 1
crim = chain_ring([e for e, n in c_edge_use.items() if n == 1], "carried rim")
rim_nrm = {}                                                # carried rim key -> donor normal
for t in blob:
    tri = don.tris[t]
    for k in range(3):
        key = kk3(carried[t][k])
        if key in c_float:
            rim_nrm.setdefault(key, list(dnrm[tri[k]]))

def signed_area(ring):
    s = 0.0
    for k in range(len(ring)):
        x1, z1 = ring[k][0], ring[k][2]
        x2, z2 = ring[(k + 1) % len(ring)][0], ring[(k + 1) % len(ring)][2]
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
print(f"zip annulus: {len(zip_tris)} tris", flush=True)

# ---- 6. zip UVs: DECODE each cell's mains (quad, ori) from the kept bytes ----------------
cell_of = lambda x, z: (int(np.floor(x / 4.0)), int(np.floor(z / 4.0)))
kept_main_by_cell = defaultdict(list)
for tidx, tri in enumerate(gtris):
    if tidx in drop or gmeta[tidx][2] != "main":
        continue
    cx, cz = tri_c[tidx]
    kept_main_by_cell[cell_of(cx, cz)].append(tidx)

QUADS = [(u, v) for u in (0, 1) for v in (0, 1)]
ORIS = (0, 90, 180, 270)
_decoded = {}

def decode_cell(cell):
    if cell in _decoded:
        return _decoded[cell]
    best = None
    for tidx in kept_main_by_cell.get(cell, []):
        tri = gtris[tidx]
        uvv = gmeta[tidx][3]
        for quad in QUADS:
            for ori in ORIS:
                err = 0.0
                for i, (u, v) in zip(tri, uvv):
                    mu, mv = G.mains_uv(gpos[i][0], gpos[i][2], cell, quad, ori)
                    err = max(err, abs(mu - u), abs(mv - v))
                if err < 1e-4:
                    best = (quad, ori)
                    break
            if best:
                break
        if best:
            break
    if best is None:                                       # fully-dropped cell: in-language pick
        import random as _r
        i, j = cell
        rng = _r.Random((i * 73856093) ^ (j * 19349663) ^ 0xF91)
        avoid = {q for n in ((i - 1, j), (i, j - 1))
                 for q in ([_decoded[n][0]] if n in _decoded else [])}
        choices = [q for q in QUADS if q not in avoid] or QUADS
        best = (choices[rng.randrange(len(choices))], ORIS[rng.randrange(4)])
    _decoded[cell] = best
    return best

# ---- 7. new-parent list + border split (generic lerp keeps uv AND normal) ----------------
GRASS_ID = float(X.encode_id(topograph=0))

def split_borders8(parents):
    """island._split_at_borders, generalized: corners are (x,y,z,u,v,nx,ny,nz)."""
    import math as _m
    def clip(poly, axis, val, keep_ge):
        out = []
        for ii in range(len(poly)):
            a, b = poly[ii], poly[(ii + 1) % len(poly)]
            da = (a[axis] - val) if keep_ge else (val - a[axis])
            db = (b[axis] - val) if keep_ge else (val - b[axis])
            if da >= 0:
                out.append(a)
            if (da >= 0) != (db >= 0):
                t = da / (da - db)
                out.append(tuple(a[k] + t * (b[k] - a[k]) for k in range(len(a))))
        return out
    out = defaultdict(list)
    for corners, idall, fam in parents:
        xs = [c[0] for c in corners]
        zs = [c[2] for c in corners]
        bx0, bx1 = int(_m.floor(min(xs) / BLOCK)), int(_m.floor((max(xs) - 1e-9) / BLOCK))
        bz0, bz1 = int(_m.floor(min(zs) / BLOCK)), int(_m.floor((max(zs) - 1e-9) / BLOCK))
        for bx in range(bx0, bx1 + 1):
            for bz in range(bz0, bz1 + 1):
                p = [tuple(c) for c in corners]
                if bx1 > bx0:
                    p = clip(p, 0, bx * BLOCK, True)
                    if len(p) >= 3:
                        p = clip(p, 0, (bx + 1) * BLOCK, False)
                if bz1 > bz0 and len(p) >= 3:
                    p = clip(p, 2, bz * BLOCK, True)
                    if len(p) >= 3:
                        p = clip(p, 2, (bz + 1) * BLOCK, False)
                if len(p) < 3:
                    continue
                for k in range(1, len(p) - 1):
                    tri = (p[0], p[k], p[k + 1])
                    # THE WALL LAW: degeneracy = TRUE 3D area, never plan area (canopy rim
                    # walls are vertical curtains -- plan-degenerate but REAL surface)
                    e1 = [tri[1][q] - tri[0][q] for q in range(3)]
                    e2 = [tri[2][q] - tri[0][q] for q in range(3)]
                    cx_ = e1[1] * e2[2] - e1[2] * e2[1]
                    cy_ = e1[2] * e2[0] - e1[0] * e2[2]
                    cz_ = e1[0] * e2[1] - e1[1] * e2[0]
                    if cx_ * cx_ + cy_ * cy_ + cz_ * cz_ < 1e-12:
                        continue
                    out[(bx, -bz - 1)].append((tri, idall, fam))
    return out

new_parents = []
for t in blob:                                             # the canopy, verbatim channels
    tri = don.tris[t]
    idall = float(dtan[tri[0]][0])
    corners = tuple((*carried[t][k], duv[tri[k]][0], duv[tri[k]][1], *dnrm[tri[k]])
                    for k in range(3))
    new_parents.append((corners, idall, "forest"))
worst_zip_rise = 0.0
zip_ny_min = 1.0
for tri3 in zip_tris:                                      # the grass annulus
    a, b, c = (np.asarray(p, dtype=np.float64) for p in tri3)
    n = np.cross(b - a, c - a)
    order = (a, b, c) if n[1] > 0 else (a, c, b)
    nl = float(np.linalg.norm(n)) or 1.0
    zip_ny_min = min(zip_ny_min, abs(float(n[1])) / nl)
    worst_zip_rise = max(worst_zip_rise, float(max(p[1] for p in tri3) - min(p[1] for p in tri3)))
    ccx = float(a[0] + b[0] + c[0]) / 3
    ccz = float(a[2] + b[2] + c[2]) / 3
    cell = cell_of(ccx, ccz)
    quad, ori = decode_cell(cell)
    corners = []
    for pnt in order:
        key = kk3(pnt)
        nrm3 = pos_nrm.get(key) or rim_nrm[key]
        u, v = G.mains_uv(float(pnt[0]), float(pnt[2]), cell, quad, ori)
        corners.append((float(pnt[0]), float(pnt[1]), float(pnt[2]), u, v, *nrm3))
    new_parents.append((tuple(corners), GRASS_ID, "zip"))
new_by_block = split_borders8(new_parents)
print(f"new tris split across blocks: { {b: len(l) for b, l in sorted(new_by_block.items())} }",
      flush=True)
assert set(new_by_block) <= set(built["blocks"]), "carve leaked outside island E's blocks"

# ---- 8. assemble per-block meshes (kept tris byte-exact; new tris appended) ---------------
changed = {}
for blk in blocks:
    bx, by = blk
    pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []
    def emit(p, u_, n_, t4):
        pos.append(list(p)); nrm.append(list(n_)); uv.append(list(u_)); tan.append(list(t4))
        flat.append(len(pos) - 1)
    n_kept = 0
    for tidx, tri in enumerate(gtris):
        tblk, idall, fam, uvv = gmeta[tidx]
        if tblk != blk or tidx in drop:
            continue
        n_kept += 1
        for vid, (u, v) in zip(tri, uvv):
            w = gpos[vid]
            emit([w[0] - BLOCK * bx, w[1], w[2] + BLOCK * (by + 1) - BLOCK],
                 (u, v), gnrm[vid], [idall, 0.0, 0.0, 1.0])
        tris.append([flat[-3], flat[-2], flat[-1]])
    n_new = 0
    for corners, idall, fam in new_by_block.get(blk, []):
        n_new += 1
        for c in corners:
            emit([c[0] - BLOCK * bx, c[1], c[2] + BLOCK * (by + 1) - BLOCK],
                 (c[3], c[4]), [c[5], c[6], c[7]], [idall, 0.0, 0.0, 1.0])
        tris.append([flat[-3], flat[-2], flat[-1]])
    bm0 = built["blocks"][blk]
    changed[blk] = X.BlockMesh(
        name=bm0.name, disc=1, x=bx, y=by, lod="0_1", vcount=len(pos), stride=48,
        channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
        chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm, X.CH_UV: uv, X.CH_TAN: tan},
        flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])
    print(f"  block {blk}: kept {n_kept}, new {n_new}", flush=True)

# ---- 9. GATES ------------------------------------------------------------------------------
worst_wall = 0.0
crim_keys = {kk3(c_float[r]) for r in crim}
for t in blob:
    ps = carried[t]
    if any(kk3(p) in crim_keys for p in ps):
        worst_wall = max(worst_wall, max(p[1] for p in ps) - min(p[1] for p in ps))
all_new_world = [c for corners, _, _ in new_parents for c in corners]
va = np.array([[c[0], c[1], c[2]] for c in all_new_world])
maxe = 0.0
down = 0
for kdx in range(0, len(va), 3):
    a, b, c = va[kdx], va[kdx + 1], va[kdx + 2]
    n = np.cross(b - a, c - a)
    if n[1] < 0:
        down += 1
    for pq in ((a, b), (b, c), (c, a)):
        maxe = max(maxe, float(np.linalg.norm(pq[0] - pq[1])))
ring_pts = np.array([list(p) for p in hole_ord] + [list(rimw(p)) for p in rim_ord])
nm = 0
for a_ in range(len(ring_pts)):
    dd = np.sum((ring_pts - ring_pts[a_]) ** 2, axis=1)
    nm += int(((dd > 1e-9) & (dd < 0.0025)).sum())
# annulus crack gate on the FINAL per-block union (position-keyed across blocks)
eu = Counter()
for blk in blocks:
    bm = changed[blk]
    v_ = bm.chan_arrays[X.CH_POS]
    bx, by = blk
    for tri in bm.tris:
        w = [(v_[i][0] + BLOCK * bx, v_[i][1], v_[i][2] - BLOCK * (by + 1) + BLOCK) for i in tri]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eu[tuple(sorted((kk3(w[a]), kk3(w[b]))))] += 1
inner_once = [e for e, n in eu.items() if n == 1
              and near((e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2, poly, RING_BAND + 2.0)]
print(f"GATES: down={down} maxEdge={maxe:.1f} nearMiss={nm // 2} annulusOnce={len(inner_once)} "
      f"wallRise={worst_wall:.2f} zipRise={worst_zip_rise:.2f} zipNyMin={zip_ny_min:.2f}",
      flush=True)
assert down == 0 and nm == 0 and not inner_once and maxe < 9.0
assert worst_wall <= 2.34 and worst_zip_rise <= 2.34 and zip_ny_min > 0.1

# placement census per changed block + the blob-centre probe
plane = _sea_plane(1)
import dataclasses
for blk in blocks:
    bx, by = blk
    hid = lambda nm_: M.hidden_block_mesh(name=nm_, disc=1, x=bx, y=by)  # noqa: E731
    sea = dataclasses.replace(plane, x=bx, y=by, name=f"Block[{bx}][{by}] Sea4")
    meshlist = [("Object", hid("Object")), ("Terrain", changed[blk]),
                ("Sea1", hid("Sea1")), ("Sea2", hid("Sea2")), ("Sea3", hid("Sea3")),
                ("Sea4", sea), ("Sea5", hid("Sea5"))]
    cen = P.census(meshlist)
    assert len(cen["miss"]) == 0, f"placement MISS in {blk}: {cen['miss'][:4]}"
    lx, lz = TX - BLOCK * bx, TZ + BLOCK * (by + 1) - BLOCK
    if 0.0 <= lx <= BLOCK and -BLOCK <= lz <= 0.0:
        gy, nm_, _, topo = P.place(meshlist, lx, lz)
        print(f"  blob centre grounds in {blk}: y={gy:.2f} {nm_} topo {topo}", flush=True)
        assert nm_ == "Terrain" and topo == 37, "blob centre must ground on canopy topo 37"
print("placement census: MISS=0 in all blocks", flush=True)

# ---- 9b. THE PERIMETER WALK-IN GATE (the honest oracle for the step law) -------------------
# Simulate the engine's climb rule around the WHOLE rim on the final assembled meshes: a
# single foot step (~0.44u/frame; S_STEP with margin) crossing the rim anywhere must climb
# <= GATE_CLIMB (engine ceiling 2.34375). Ground is sampled at 0.05u along inward transects;
# every ordered pair within one step gates. Descent is always legal (ff9.rayDistance is dead
# code in WMBlock.Raycast, source-verified).
_wv, _wt, _wf = [], [], []
for blk in blocks:
    bm = changed[blk]
    bx, by = blk
    base = len(_wv)
    for k in range(bm.vcount):
        v_ = bm.chan_arrays[X.CH_POS][k]
        _wv.append((v_[0] + BLOCK * bx, v_[1], v_[2] - BLOCK * (by + 1) + BLOCK))
        _wt.append(bm.chan_arrays[X.CH_TAN][k])
    _wf.extend(i + base for i in bm.flat_index)
class _W:
    pass
_w = _W()
_w.verts, _w.tangents, _w.flat_index = _wv, _wt, _wf
_wml = [("Terrain", _w)]
rim_pts = [rimw(p) for p in rim_ord]
RES = 0.05
SPAN = 1.2
NSAMP = int(2 * SPAN / RES) + 1
WIN = int(S_STEP / RES)
worst_climb = (0.0, None)
for e0 in range(len(rim_pts)):
    a = rim_pts[e0]
    b = rim_pts[(e0 + 1) % len(rim_pts)]
    ex, ez = b[0] - a[0], b[2] - a[2]
    el = (ex * ex + ez * ez) ** 0.5
    if el < 1e-6:
        continue
    nxo, nzo = ez / el, -ex / el                          # edge normal (side resolved below)
    nst = max(1, int(el / 0.5))
    for s in range(nst + 1):
        t01 = s / nst
        sx, sz = a[0] + ex * t01, a[2] + ez * t01
        if pip(sx + nxo * 0.8, sz + nzo * 0.8, poly):     # ensure (nxo,nzo) points OUT
            nxo, nzo = -nxo, -nzo
        prof = []
        for k in range(NSAMP):                            # d from +SPAN (outside) to -SPAN (inside)
            d = SPAN - k * RES
            hy, nm_, _, _tp = P.place(_wml, sx + nxo * d, sz + nzo * d, sky=True)
            prof.append(hy if nm_ != "MISS" else None)
        for i0 in range(NSAMP):                           # single-step crossing pairs
            if prof[i0] is None:
                continue
            for j0 in range(i0 + 1, min(i0 + WIN + 1, NSAMP)):
                if prof[j0] is None:
                    continue
                climb = prof[j0] - prof[i0]
                if climb > worst_climb[0]:
                    worst_climb = (climb, (round(sx, 1), round(sz, 1)))
print(f"perimeter walk-in gate: worst single-step climb {worst_climb[0]:.2f} at "
      f"{worst_climb[1]} (ceiling {GATE_CLIMB})", flush=True)
assert worst_climb[0] <= GATE_CLIMB, \
    f"a rim segment still climbs {worst_climb[0]:.2f} > {GATE_CLIMB} at {worst_climb[1]}"

# ---- 10. offline eyes: atlas alpha over new tris + shaded render ---------------------------
try:
    from PIL import Image
    MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
        "textures" / "res(1_24)_terrain.png"
    img = Image.open(MOG).convert("RGBA")
    W, H = img.size
    PX = img.load()
    import math as _m
    def at_b(u_, v_):
        fx = (u_ % 1.0) * W - 0.5
        fy = (1.0 - v_ % 1.0) * H - 0.5
        x0, y0 = int(_m.floor(fx)), int(_m.floor(fy))
        tx, ty = fx - x0, fy - y0
        acc = [0.0, 0.0, 0.0]
        aa = 0.0
        for (dx2, dy2, wgt) in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                                (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
            px_, py_ = min(max(x0 + dx2, 0), W - 1), min(max(y0 + dy2, 0), H - 1)
            r, g, b, a = PX[px_, py_]
            acc[0] += r * wgt; acc[1] += g * wgt; acc[2] += b * wgt; aa += a * wgt
        return aa, (int(acc[0]), int(acc[1]), int(acc[2]))
    blank = 0
    for corners, _, _ in new_parents:
        nb = 0
        for ii in range(11):
            for jj in range(11 - ii):
                w0, w1 = ii / 10.0, jj / 10.0
                w2 = 1 - w0 - w1
                if w2 < -1e-9:
                    continue
                u_ = w0 * corners[0][3] + w1 * corners[1][3] + w2 * corners[2][3]
                v_ = w0 * corners[0][4] + w1 * corners[1][4] + w2 * corners[2][4]
                if at_b(u_, v_)[0] < 24:
                    nb += 1
        if nb:
            blank += 1
    print(f"atlas gate over new tris: transparent-sampling = {blank} (want 0)", flush=True)
    assert blank == 0
    # shaded top-down of the carved island
    SC = 16
    allv, alltris, alluv, allnrm = [], [], [], []
    for blk in blocks:
        bm = changed[blk]
        v_ = bm.chan_arrays[X.CH_POS]
        u_ = bm.chan_arrays[X.CH_UV]
        n_ = bm.chan_arrays[X.CH_NRM]
        bx, by = blk
        base = len(allv)
        for k in range(len(v_)):
            allv.append([v_[k][0] + BLOCK * bx, v_[k][1], v_[k][2] - BLOCK * (by + 1) + BLOCK])
            alluv.append(u_[k])
            allnrm.append(n_[k])
        for tri in bm.tris:
            alltris.append([tri[0] + base, tri[1] + base, tri[2] + base])
    lo_x = min(v_[0] for v_ in allv); hi_x = max(v_[0] for v_ in allv)
    lo_z = min(v_[2] for v_ in allv); hi_z = max(v_[2] for v_ in allv)
    RW, RH = int((hi_x - lo_x) * SC) + 2, int((hi_z - lo_z) * SC) + 2
    outim = Image.new("RGB", (RW, RH), (24, 40, 72))
    op = outim.load()
    LDIR = (-0.45, 0.8, -0.35)
    _l = _m.sqrt(sum(q * q for q in LDIR))
    LDIR = tuple(q / _l for q in LDIR)
    for tri in alltris:
        p3 = [allv[i] for i in tri]
        q3 = [alluv[i] for i in tri]
        n3 = [allnrm[i] for i in tri]
        xs_ = [(pp[0] - lo_x) * SC for pp in p3]
        zs_ = [(pp[2] - lo_z) * SC for pp in p3]
        x0, x1 = int(min(xs_)), int(max(xs_)) + 1
        z0, z1 = int(min(zs_)), int(max(zs_)) + 1
        d = (zs_[1] - zs_[2]) * (xs_[0] - xs_[2]) + (xs_[2] - xs_[1]) * (zs_[0] - zs_[2])
        if abs(d) < 1e-9:
            continue
        for pyx in range(max(0, x0), min(RW, x1)):
            for pyz in range(max(0, z0), min(RH, z1)):
                w0 = ((zs_[1] - zs_[2]) * (pyx - xs_[2]) + (xs_[2] - xs_[1]) * (pyz - zs_[2])) / d
                w1 = ((zs_[2] - zs_[0]) * (pyx - xs_[2]) + (xs_[0] - xs_[2]) * (pyz - zs_[2])) / d
                w2 = 1 - w0 - w1
                if w0 < 0 or w1 < 0 or w2 < 0:
                    continue
                aa, rgb = at_b(w0 * q3[0][0] + w1 * q3[1][0] + w2 * q3[2][0],
                               w0 * q3[0][1] + w1 * q3[1][1] + w2 * q3[2][1])
                nx = sum(w * n3[k][0] for k, w in enumerate((w0, w1, w2)))
                ny = sum(w * n3[k][1] for k, w in enumerate((w0, w1, w2)))
                nz = sum(w * n3[k][2] for k, w in enumerate((w0, w1, w2)))
                nl = _m.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
                f = 0.55 + 0.45 * max(0.0, (nx * LDIR[0] + ny * LDIR[1] + nz * LDIR[2]) / nl)
                op[pyx, RH - 1 - pyz] = (255, 255, 255) if aa < 24 else \
                    tuple(min(255, int(cc * f)) for cc in rgb[:3])
    OUT_RENDER.parent.mkdir(exist_ok=True)
    outim.save(OUT_RENDER)
    print(f"render -> {OUT_RENDER}", flush=True)
except ImportError:
    print("(PIL missing -- atlas gate + render skipped; DO NOT deploy blind)", flush=True)
    raise

# ---- 11. deploy (converge by byte-compare: write every block whose final bytes differ) -------
final_bytes = {}
for blk in blocks:
    p = M.write_ff9mesh(changed[blk], _tmp / f"fin_{blk[0]}_{blk[1]}.ff9mesh")
    final_bytes[blk] = p.read_bytes()
touched = sorted(b for b in blocks
                 if final_bytes[b] != (MODW / f"r{b[1]}" / f"Block[{b[0]}][{b[1]}] Terrain.ff9mesh").read_bytes())
print(f"blocks whose bytes change: {touched}", flush=True)
if len(sys.argv) > 1 and sys.argv[1] == "deploy":
    BK.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    for blk in touched:
        dep = MODW / f"r{blk[1]}" / f"Block[{blk[0]}][{blk[1]}] Terrain.ff9mesh"
        shutil.copyfile(dep, BK / f"{dep.name}.{ts}")
        out = M.deploy_override(changed[blk], mod_folder="FF9CustomMap-world", part="Terrain")
        print(f"deployed -> {out} ({len(changed[blk].tris)} tris)", flush=True)
    print("DONE -- F6 world re-entry, teleport 344,-1152, walk INTO and OVER the canopy.")
else:
    print("dry run only -- re-run with 'deploy' to write.")
