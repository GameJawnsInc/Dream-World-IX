"""THE UAHO CARRY -- carry the REAL Uaho island mountain (block (0,0)) verbatim onto the
bench islet, replacing the falsified from-scratch massif synthesis.

Eight synth rounds each fixed a real, correctly-diagnosed defect class and each playtest
minted a new one ("still patchwork, still stretching") -- THE FORM LESSON again: the rock
texture organization is hand-authored; statistics reproduce its properties, not its look.
This is the CARRY LAW's 6th instance (beach1, shore components, canopy, mesa, spur):
carry the real bytes whole, synthesize only the seam.

The carry: blob = Uaho's rock component (+ any enclosed raised tris; the embedded Object
is a separate mesh part and is NOT carried); rim = the blob's outer once-edge ring at the
grass foot; a placement scan finds a plain-grass-mains pocket on the bench (exact 90-deg
rotations as fallbacks if the fit is snug -- rotation keeps UVs verbatim, det +1 keeps
winding); rim conforms to local ground (the mountain blocks by TOPO, the faithful
mechanism -- no step-law lift needed); hole carve + greedy zip + byte-decoded zip mains +
ring-owner normals (the proven carve machinery, exact-float welds). The zip band is the
ONLY synthetic material and it is plain flat grass.

Gates: single-rim-ring check, dropped-tris-all-plain-grass, annulus once-edges == 0,
down-facing == 0, near-miss weld audit, block bounds, census MISS == 0, rock-blocks /
grass-walks placement probes, Moguri-atlas alpha == 0 over new tris, and THE OFFLINE EYE
(top-down + 4 elevations + the game-texel close-up, to compare against uaho_views.png).

Usage:  py studies/overworld-topography/massif_carry.py [deploy]
"""
import math
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg
from ff9mapkit.world import extract as X
from ff9mapkit.world import grassland as G
from ff9mapkit.world import interior as IN
from ff9mapkit.world import mesh as M
from ff9mapkit.world import placement as P

GP = Path(_cfg.find_game_path(None))
MODW = GP / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
BK = Path(__file__).resolve().parents[2] / "backups"
OUTD = Path(__file__).with_name("out")
DONOR = (0, 0)
BLK = (2, 19)
BLOCK = 64.0
CX, CZ = 160.0, -1246.0                                    # the r31 seed-42 bench mint
CLEAR = 2.5
SCAN_BAND = CLEAR + 4.0                                    # hole + zip + decode cells: mains only
ROCK = {49, 7, 62}
kk3 = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

# ---- 1. the donor blob (rock component + enclosed raised tris) --------------------------------
don = X.read_block(*DONOR, disc=1)
dV = np.asarray(don.verts, dtype=np.float64) + np.array(
    [BLOCK * DONOR[0], 0.0, -BLOCK * DONOR[1]])
dU = np.asarray(don.uvs, dtype=np.float64)
dN = don.normals
dT = don.tangents
dntri = len(don.flat_index) // 3
dtri = [don.flat_index[3 * t:3 * t + 3] for t in range(dntri)]
dtopo = [X.decode_id(int(round(dT[i[0]][0])))["topograph"] for i in dtri]

d_edge = defaultdict(list)
for t, idx in enumerate(dtri):
    for a, b in ((0, 1), (1, 2), (2, 0)):
        d_edge[tuple(sorted((kk3(dV[idx[a]]), kk3(dV[idx[b]]))))].append(t)

adjR = defaultdict(set)
for e, ts in d_edge.items():
    r = [t for t in ts if dtopo[t] in ROCK]
    for i in range(len(r)):
        for j in range(i + 1, len(r)):
            adjR[r[i]].add(r[j]); adjR[r[j]].add(r[i])
seen, comps = set(), []
for s in range(dntri):
    if dtopo[s] not in ROCK or s in seen:
        continue
    comp = {s}; st = [s]
    while st:
        t = st.pop()
        for t2 in adjR[t]:
            if t2 not in comp:
                comp.add(t2); st.append(t2)
    seen |= comp
    comps.append(comp)
comps.sort(key=len, reverse=True)
blob = set(comps[0])
print(f"donor rock component: {len(blob)} tris (next {[len(c) for c in comps[1:3]]})",
      flush=True)


def once_edges(tset):
    eu_ = Counter()
    for t in tset:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eu_[tuple(sorted((kk3(dV[dtri[t][a]]), kk3(dV[dtri[t][b]]))))] += 1
    return [e for e, n in eu_.items() if n == 1]


def chain_rings(edges):
    """All simple cycles in a degree-2 edge set."""
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    bad = [p for p, l in adj.items() if len(l) != 2]
    assert not bad, f"ring set not degree-2 ({len(bad)} odd points)"
    unused = set(map(tuple, (tuple(sorted(e)) for e in edges)))
    rings = []
    while unused:
        e0 = next(iter(unused))
        ring = [e0[0]]
        prev = None
        while True:
            # pick the neighbor whose edge is still unused
            nxt = None
            for p in adj[ring[-1]]:
                if p != prev and tuple(sorted((ring[-1], p))) in unused:
                    nxt = p
                    break
            if nxt is None:
                break
            unused.discard(tuple(sorted((ring[-1], nxt))))
            prev = ring[-1]
            ring.append(nxt)
            if ring[-1] == ring[0]:
                ring.pop()
                break
        assert len(ring) == len({*ring}) and len(ring) >= 3, "degenerate ring"
        rings.append(ring)
    return rings


def signed_area(ring):
    s = 0.0
    for i in range(len(ring)):
        x1, z1 = ring[i][0], ring[i][2]
        x2, z2 = ring[(i + 1) % len(ring)][0], ring[(i + 1) % len(ring)][2]
        s += x1 * z2 - x2 * z1
    return s / 2


rings0 = chain_rings(once_edges(blob))
rings0.sort(key=lambda r: -abs(signed_area(r)))
if len(rings0) > 1:                                        # inner rings enclose non-rock islands
    inner_pts = {p for r in rings0[1:] for p in r}
    seeds = []
    for e in once_edges(blob):
        if e[0] in inner_pts and e[1] in inner_pts:
            seeds += [t for t in d_edge[e] if t not in blob]
    st = list(seeds)
    added = 0
    while st:
        t = st.pop()
        if t in blob:
            continue
        blob.add(t); added += 1
        for a, b in ((0, 1), (1, 2), (2, 0)):
            for t2 in d_edge[tuple(sorted((kk3(dV[dtri[t][a]]), kk3(dV[dtri[t][b]]))))]:
                if t2 not in blob and dtopo[t2] not in ROCK:
                    st.append(t2)
    print(f"enclosed raised tris flooded in: {added}", flush=True)
oe = once_edges(blob)
rings1 = chain_rings(oe)
assert len(rings1) == 1, f"blob rim is {len(rings1)} rings, want 1"
rim = rings1[0]
assert len(rim) == len(oe), "rim ring does not use every once-edge"
rim_set = set(rim)
bpts = np.array([dV[i] for t in blob for i in dtri[t]])
c_local = ((bpts[:, 0].min() + bpts[:, 0].max()) / 2,
           (bpts[:, 2].min() + bpts[:, 2].max()) / 2)
r_rim = max(math.hypot(p[0] - c_local[0], p[2] - c_local[1]) for p in rim)
print(f"blob: {len(blob)} tris, extent {bpts[:, 0].max() - bpts[:, 0].min():.0f}x"
      f"{bpts[:, 2].max() - bpts[:, 2].min():.0f}u y[{bpts[:, 1].min():.1f},"
      f"{bpts[:, 1].max():.1f}] topos {dict(Counter(dtopo[t] for t in blob))}; "
      f"rim {len(rim)} pts y[{min(p[1] for p in rim):.1f},{max(p[1] for p in rim):.1f}] "
      f"max plan radius {r_rim:.1f}u", flush=True)

# ---- 1b. de-tilt: the donor mountain stands on sloped ground (rim y 2.3..8.0). Carried
# onto a flat bench, a raw rim conform would shear the foot courses by up to ~5u -- the
# exact stretch class the carry exists to escape. Fit a least-squares plane over the RIM
# feet and subtract it from the WHOLE blob (an affine shear, ~10deg, texel distortion
# ~1.5%); the rim conform then handles only the mesa-scale residual. Normals get the
# shear's inverse-transpose.
Amat = np.array([[p[0] - c_local[0], p[2] - c_local[1], 1.0] for p in rim])
bvec = np.array([p[1] for p in rim])
(ta, tb, tc), *_ = np.linalg.lstsq(Amat, bvec, rcond=None)
res0 = bvec - Amat @ np.array([ta, tb, tc])
print(f"de-tilt: rim plane slope {math.degrees(math.atan(math.hypot(ta, tb))):.1f}deg, "
      f"residual [{res0.min():+.2f},{res0.max():+.2f}]u", flush=True)


def detilt_p(p):
    return (p[0], p[1] - ta * (p[0] - c_local[0]) - tb * (p[2] - c_local[1]), p[2])


def detilt_n(n):
    v3 = np.array([n[0] + ta * n[1], n[1], n[2] + tb * n[1]])
    return (v3 / (np.linalg.norm(v3) or 1.0)).tolist()


dV2 = np.array([detilt_p(p) for p in dV])
dN2 = [detilt_n(n) for n in dN]
rim2 = [detilt_p(p) for p in rim]

# ---- 2. the bench + the placement scan ---------------------------------------------------------
bx, by = BLK
src = MODW / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
bm = M.blockmesh_from_ff9mesh(src, disc=1, x=bx, y=by, lod="0_1", part="terrain")
gpos = [[v[0] + BLOCK * bx, v[1], v[2] - BLOCK * (by + 1) + BLOCK] for v in bm.verts]
gtris = list(bm.tris)
gnrm = [list(n) for n in bm.chan_arrays[X.CH_NRM]]
guv = [list(u) for u in bm.chan_arrays[X.CH_UV]]
gtan = [list(t) for t in bm.chan_arrays[X.CH_TAN]]
gtopo = [X.decode_id(int(round(gtan[t[0]][0])))["topograph"] for t in gtris]
assert not any(tp in ROCK for tp in gtopo), "bench not pristine -- restore the .bak first"
lo_u, hi_u = G.FAM_REGION["main"][0], G.FAM_REGION["main"][2]
plain = []
for tdx, tri in enumerate(gtris):
    plain.append(gtopo[tdx] == 0 and
                 all(lo_u - 0.02 <= guv[i][0] <= hi_u + 0.02 for i in tri))
tri_c = [((gpos[tri[0]][0] + gpos[tri[1]][0] + gpos[tri[2]][0]) / 3,
          (gpos[tri[0]][2] + gpos[tri[1]][2] + gpos[tri[2]][2]) / 3)
         for tri in gtris]
nonplain_c = np.array([tri_c[t] for t in range(len(gtris)) if not plain[t]])
print(f"bench: {len(gtris)} tris ({sum(plain)} plain-grass mains)", flush=True)


def rot_pt(p, k):
    dx3, dz3 = p[0] - c_local[0], p[2] - c_local[1]
    for _ in range(k):
        dx3, dz3 = dz3, -dx3
    return (c_local[0] + dx3, p[1], c_local[1] + dz3)


def rot_n(n, k):
    nx, nz = n[0], n[2]
    for _ in range(k):
        nx, nz = nz, -nx
    return [nx, n[1], nz]


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


cands = []                                                 # (score, dmin, ROT, gx, gz)
BX0, BX1 = BLOCK * bx, BLOCK * (bx + 1)
BZ0, BZ1 = -BLOCK * (by + 1), -BLOCK * by
for ROT in (0, 1, 2, 3):
    poly_pts = np.array([(p[0], p[2]) for p in (rot_pt(q, ROT) for q in rim)])
    for gx in range(int(CX) - 10, int(CX) + 11, 2):
        for gz in range(int(CZ) - 10, int(CZ) + 11, 2):
            pp = poly_pts + np.array([gx - c_local[0], gz - c_local[1]])
            # the hole band must stay inside THIS block (the mint spills a few coast
            # tris into (2,18) the scan can't see)
            if pp[:, 0].min() < BX0 + SCAN_BAND + 2 or pp[:, 0].max() > BX1 - SCAN_BAND - 2 \
                    or pp[:, 1].min() < BZ0 + SCAN_BAND + 2 or pp[:, 1].max() > BZ1 - SCAN_BAND - 2:
                continue
            # numpy prefilter: nearest non-plain centroid to any poly vertex
            dmin = float(np.sqrt(
                ((nonplain_c[:, None, :] - pp[None, :, :]) ** 2).sum(axis=2).min()))
            cands.append((dmin + (0.75 if ROT == 0 else 0.0), dmin, ROT, gx, gz))
cands.sort(reverse=True)
print(f"scan: best raw clearance {cands[0][1]:.1f}u (rot {cands[0][2] * 90}deg) "
      f"of {len(cands)} in-bounds candidates", flush=True)
chosen = None
for score, dmin, ROT, gx, gz in cands[:60]:
    if dmin < SCAN_BAND:
        break
    DX, DZ = gx - c_local[0], gz - c_local[1]
    rim_poly = [(p[0] + DX, p[2] + DZ) for p in (rot_pt(q, ROT) for q in rim)]
    ok = True                                              # exact: no non-plain tri in the band
    for tdx, tri in enumerate(gtris):
        if plain[tdx]:
            continue
        cx2, cz2 = tri_c[tdx]
        if pip(cx2, cz2, rim_poly) or near(cx2, cz2, rim_poly, SCAN_BAND) or any(
                pip(gpos[i][0], gpos[i][2], rim_poly) or
                near(gpos[i][0], gpos[i][2], rim_poly, SCAN_BAND) for i in tri):
            ok = False
            break
    if ok:
        chosen = (ROT, gx, gz, dmin)
        break
assert chosen, (f"no lawful placement -- best raw clearance {cands[0][1]:.1f}u "
                f"vs SCAN_BAND {SCAN_BAND}")
ROT, TX, TZ, dmin = chosen
DX, DZ = TX - c_local[0], TZ - c_local[1]
rim_poly = [(p[0] + DX, p[2] + DZ) for p in (rot_pt(q, ROT) for q in rim)]
print(f"placement: rot {ROT * 90}deg, blob centre -> ({TX},{TZ}) "
      f"(clearance {dmin:.1f}u)", flush=True)

# ---- 3. hole carve ------------------------------------------------------------------------------
drop = set()
for tdx, tri in enumerate(gtris):
    for i in tri:
        if pip(gpos[i][0], gpos[i][2], rim_poly) or \
                near(gpos[i][0], gpos[i][2], rim_poly, CLEAR):
            drop.add(tdx)
            break
fams = Counter(gtopo[t] for t in drop)
print(f"bench tris dropped: {len(drop)} (topos {dict(fams)})", flush=True)
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
hole_es = [e for e, n in eu2.items() if n == 1 and e in dropped_edges]
holes = chain_rings(hole_es)
assert len(holes) == 1, f"hole is {len(holes)} rings, want 1"
hole = holes[0]
print(f"hole ring: {len(hole)} positions", flush=True)


def nearest_ring_y(px, pz):
    return min(hole, key=lambda h: (h[0] - px) ** 2 + (h[2] - pz) ** 2)[1]


# ---- 4. anchor + carry (rim conforms to local ground; interior verbatim-relative) --------------
# rim membership + conform targets key on the ORIGINAL donor positions -- de-tilt/rot
# float precision can never split a weld
rim_med = float(np.median([p[1] for p in rim2]))
ground_med = float(np.median([p[1] for p in hole]))
DY = ground_med - rim_med
# conform = a SMOOTH Shepard blend over the rim deltas (finite 7u support), never a
# rim-only yank: yanking just the rim vert stretches the foot course by the full
# de-tilt residual (up to ~3u) -- the exact stretch class the carry exists to escape.
# Blended, each foot course moves WITH its rim verts; the correction fades to zero
# up-flank. Pure function of plan position -> welds can't split.
BLEND = 7.0
rim_nodes = []
for p in rim_set:
    pr = rot_pt(detilt_p(p), ROT)
    delta = nearest_ring_y(pr[0] + DX, pr[2] + DZ) - (pr[1] + DY)
    rim_nodes.append((pr[0] + DX, pr[2] + DZ, delta))
print(f"rim conform deltas after de-tilt: [{min(n[2] for n in rim_nodes):+.2f},"
      f"{max(n[2] for n in rim_nodes):+.2f}]u (blended over {BLEND}u)", flush=True)


def conform_off(px, pz):
    wsum = osum = 0.0
    for (nx2, nz2, dl) in rim_nodes:
        dd2 = (px - nx2) ** 2 + (pz - nz2) ** 2
        if dd2 > BLEND * BLEND:
            continue
        w = (1.0 - math.sqrt(dd2) / BLEND) ** 2 / (dd2 + 0.04)
        wsum += w
        osum += w * dl
    return osum / wsum if wsum > 0 else 0.0


def carry_vert(i):
    pr = rot_pt(dV2[i], ROT)
    px, pz = pr[0] + DX, pr[2] + DZ
    return [px, pr[1] + DY + conform_off(px, pz), pz]


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
crims = chain_rings([e for e, n in c_edge.items() if n == 1])
assert len(crims) == 1, "carried rim split into rings -- conform collapsed a weld"
crim = crims[0]
rim_nrm = {}
for t in blob:
    for k in range(3):
        key = kk3(carried[t][k])
        rim_nrm.setdefault(key, rot_n(dN2[dtri[t][k]], ROT))
print(f"carried: peak y {max(p[1] for ps in carried.values() for p in ps):.1f}, "
      f"DY {DY:+.2f}", flush=True)

# ---- 5. zip annulus (the proven machinery) ------------------------------------------------------
hole_ord = list(hole)
rim_ord = list(crim)
if signed_area(hole_ord) * signed_area(rim_ord) < 0:
    rim_ord.reverse()
h0 = hole_ord[0]
k0 = min(range(len(rim_ord)),
         key=lambda k: (rim_ord[k][0] - h0[0]) ** 2 + (rim_ord[k][2] - h0[2]) ** 2)
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
    if tdx in drop or not plain[tdx]:
        continue
    kept_by_cell[cell_of(*tri_c[tdx])].append(tdx)
QUADS = [(u, v) for u in (0, 1) for v in (0, 1)]
ORIS = (0, 90, 180, 270)
_dec = {}


def decode_cell(cell):
    if cell in _dec:
        return _dec[cell]
    best2 = None
    for tdx in kept_by_cell.get(cell, []):
        tri = gtris[tdx]
        for q in QUADS:
            for o in ORIS:
                err = 0.0
                for i in tri:
                    mu, mv = G.mains_uv(gpos[i][0], gpos[i][2], cell, q, o)
                    err = max(err, abs(mu - guv[i][0]), abs(mv - guv[i][1]))
                if err < 1e-4:
                    best2 = (q, o)
                    break
            if best2:
                break
        if best2:
            break
    if best2 is None:
        import random as _r
        i2, j2 = cell
        rr = _r.Random((i2 * 73856093) ^ (j2 * 19349663) ^ 0xF95)
        best2 = (QUADS[rr.randrange(4)], ORIS[rr.randrange(4)])
    _dec[cell] = best2
    return best2


pos_nrm = {}
for tdx, tri in enumerate(gtris):
    if tdx in drop:
        continue
    for i in tri:
        pos_nrm.setdefault(kk3(gpos[i]), list(gnrm[i]))

ID0 = float(X.encode_id(topograph=0))
new_parents = []                                           # (corners8, idall, fam)
for t in blob:                                             # the mountain, verbatim channels
    tri = dtri[t]
    idall = float(dT[tri[0]][0])
    nr = [rot_n(dN2[tri[k]], ROT) for k in range(3)]
    corners = tuple((*carried[t][k], dU[tri[k]][0], dU[tri[k]][1], *nr[k])
                    for k in range(3))
    new_parents.append((corners, idall, "mountain"))
zip_rise = 0.0
zip_ny_min = 1.0
for tri3 in zip_tris:
    a, b, c = (np.asarray(p, dtype=float) for p in tri3)
    nrm = np.cross(b - a, c - a)
    nl = float(np.linalg.norm(nrm)) or 1.0
    zip_ny_min = min(zip_ny_min, abs(float(nrm[1])) / nl)
    zip_rise = max(zip_rise, float(max(p[1] for p in tri3) - min(p[1] for p in tri3)))
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

# ---- 6. gates + assembly ------------------------------------------------------------------------
for corners, idall, fam in new_parents:
    for p in corners:
        assert BLOCK * bx + 0.5 < p[0] < BLOCK * (bx + 1) - 0.5 and \
            -BLOCK * (by + 1) + 0.5 < p[2] < -BLOCK * by - 0.5, \
            f"{fam} leaves block {BLK}: {p[:3]}"
down = 0
maxe = 0.0
for corners, _, _ in new_parents:
    a, b, c = (np.asarray(p[:3]) for p in corners)
    if np.cross(b - a, c - a)[1] < 0:
        down += 1
    for pq in ((a, b), (b, c), (c, a)):
        maxe = max(maxe, float(np.linalg.norm(pq[0] - pq[1])))
ring_pts = np.array([list(p) for p in hole_ord] + [list(rimw(p)) for p in rim_ord])
nm = 0
for a_ in range(len(ring_pts)):
    dd = np.sum((ring_pts - ring_pts[a_]) ** 2, axis=1)
    nm += int(((dd > 1e-9) & (dd < 0.0025)).sum())
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
new_bm = X.BlockMesh(
    name=bm.name, disc=1, x=bx, y=by, lod="0_1", vcount=len(pos), stride=48,
    channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
    chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm, X.CH_UV: uv, X.CH_TAN: tan},
    flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])
# once-edge gate = BASELINE-SUBTRACTED: the pristine mint has its own legal once-edges
# (coast T-junctions, block-border edges); the carve must not ADD any
eu0 = Counter()
for tri in gtris:
    w = [gpos[i] for i in tri]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        eu0[tuple(sorted((kk3(w[a]), kk3(w[b]))))] += 1
once0 = {e for e, n in eu0.items() if n == 1}
eu3 = Counter()
for t in range(len(tris)):
    w = [(pos[i][0] + BLOCK * bx, pos[i][1], pos[i][2] - BLOCK * (by + 1) + BLOCK)
         for i in tris[t]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        eu3[tuple(sorted((kk3(w[a]), kk3(w[b]))))] += 1
inner_once = [e for e, n in eu3.items() if n == 1 and e not in once0]
for e in inner_once[:6]:
    print(f"  NEW ONCE EDGE: {e[0]} -- {e[1]}", flush=True)
print(f"GATES: down={down} maxEdge={maxe:.1f} nearMiss={nm // 2} "
      f"annulusOnce={len(inner_once)} zipRise={zip_rise:.2f} zipNyMin={zip_ny_min:.2f}",
      flush=True)
assert down == 0 and nm == 0 and not inner_once and maxe < 9.0
assert zip_rise <= 2.34 and zip_ny_min > 0.1

changed = {BLK: new_bm}
IN.census_gate(changed, disc=1)
_wml = [("Terrain", new_bm)]


class _W:
    pass


_w = _W()
_w.verts = [(p[0] + BLOCK * bx, p[1], p[2] - BLOCK * (by + 1) + BLOCK) for p in pos]
_w.tangents = tan
_w.flat_index = flat
_wml = [("Terrain", _w)]
gy, nm_, _, tp = P.place(_wml, TX, TZ)
print(f"census MISS=0; blob centre grounds: y={gy:.2f} {nm_} topo {tp}", flush=True)
assert nm_ == "Terrain" and tp in ROCK, "blob centre must ground on carried rock"
r_out = max(math.hypot(px - TX, pz - TZ) for (px, pz) in rim_poly) + 4.0
gy2, nm2, _, tp2 = P.place(_wml, TX - r_out, TZ)
print(f"grass probe west of the rim: y={gy2:.2f} {nm2} topo {tp2}", flush=True)
assert nm2 == "Terrain" and tp2 == 0

# ---- 7. THE OFFLINE EYE -------------------------------------------------------------------------
MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
    "textures" / "res(1_24)_terrain.png"
atlas = Image.open(MOG).convert("RGBA")
AW, AH = atlas.size
APX = atlas.load()


def at_b(u_, v_):
    fx = (u_ % 1.0) * AW - 0.5
    fy = (1.0 - v_ % 1.0) * AH - 0.5
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - x0, fy - y0
    a4 = [0.0, 0.0, 0.0, 0.0]
    for (dx2, dy2, wg) in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                           (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        px_, py_ = min(max(x0 + dx2, 0), AW - 1), min(max(y0 + dy2, 0), AH - 1)
        r, g2, b2, al = APX[px_, py_]
        a4[0] += r * wg; a4[1] += g2 * wg; a4[2] += b2 * wg; a4[3] += al * wg
    return a4[3], (int(a4[0]), int(a4[1]), int(a4[2]))


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
print(f"atlas gate: transparent-sampling tris = {blank} (want 0)", flush=True)
assert blank == 0

LDIR = (-0.5, 0.7, -0.3)
_l = math.sqrt(sum(q * q for q in LDIR)); LDIR = tuple(q / _l for q in LDIR)


def raster(img, sx, sy, uv3, n3, W, H):
    op = img.load()
    x0, x1 = int(min(sx)), int(max(sx)) + 1
    y0, y1 = int(min(sy)), int(max(sy)) + 1
    if x1 < 0 or x0 >= W or y1 < 0 or y0 >= H:
        return
    d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
    if abs(d) < 1e-9:
        return
    for pyx in range(max(0, x0), min(W, x1)):
        for pyy in range(max(0, y0), min(H, y1)):
            w0 = ((sy[1] - sy[2]) * (pyx - sx[2]) + (sx[2] - sx[1]) * (pyy - sy[2])) / d
            w1 = ((sy[2] - sy[0]) * (pyx - sx[2]) + (sx[0] - sx[2]) * (pyy - sy[2])) / d
            w2 = 1 - w0 - w1
            if w0 < 0 or w1 < 0 or w2 < 0:
                continue
            aa, rgb = at_b(w0 * uv3[0][0] + w1 * uv3[1][0] + w2 * uv3[2][0],
                           w0 * uv3[0][1] + w1 * uv3[1][1] + w2 * uv3[2][1])
            if aa < 24:
                continue
            nx = sum(w * n3[k][0] for k, w in enumerate((w0, w1, w2)))
            ny = sum(w * n3[k][1] for k, w in enumerate((w0, w1, w2)))
            nz = sum(w * n3[k][2] for k, w in enumerate((w0, w1, w2)))
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            f = 0.55 + 0.45 * max(0.0, (nx * LDIR[0] + ny * LDIR[1] + nz * LDIR[2]) / nl)
            op[pyx, pyy] = tuple(min(255, int(c * f)) for c in rgb[:3])


rt = []                                                    # final world tris for the eye
for t in range(len(tris)):
    rt.append(dict(
        w=[(pos[i][0] + BLOCK * bx, pos[i][1], pos[i][2] - BLOCK * (by + 1) + BLOCK)
           for i in tris[t]],
        uv=[uv[i] for i in tris[t]], n=[nrm[i] for i in tris[t]]))
OUTD.mkdir(exist_ok=True)
SC = 16
HW, HH = 24.0, 18.0
RW, RH = int(2 * HW * SC), int(HH * SC)
views = []
for name, azd in (("fromS", 90), ("fromW", 0), ("fromN", 270), ("fromE", 180)):
    azr = math.radians(azd)
    vx, vz = math.cos(azr), math.sin(azr)
    rx, rz = -vz, vx
    img = Image.new("RGB", (RW, RH), (150, 178, 210))
    rec = sorted(range(len(rt)),
                 key=lambda t2: max((p[0] - TX) * vx + (p[2] - TZ) * vz
                                    for p in rt[t2]["w"]))
    for t2 in rec:
        t = rt[t2]
        sx = [((p[0] - TX) * rx + (p[2] - TZ) * rz + HW) * SC for p in t["w"]]
        sy = [(HH - p[1]) * SC for p in t["w"]]
        raster(img, sx, sy, t["uv"], t["n"], RW, RH)
    views.append(img)
gap = 8
sheet = Image.new("RGB", (RW, (RH + gap) * 4 - gap), (10, 10, 10))
for k, img in enumerate(views):
    sheet.paste(img, (0, k * (RH + gap)))
sheet.save(OUTD / "massif_carry_views.png")
print(f"-> {OUTD / 'massif_carry_views.png'}")
SCc, HWc, HHc = 44, 9.0, 12.0
RWc, RHc = int(2 * HWc * SCc), int(HHc * SCc)
img = Image.new("RGB", (RWc, RHc), (150, 178, 210))
vx, vz, rx, rz = 1.0, 0.0, 0.0, 1.0
rec = sorted(range(len(rt)),
             key=lambda t2: max((p[0] - TX) * vx + (p[2] - TZ) * vz for p in rt[t2]["w"]))
for t2 in rec:
    t = rt[t2]
    sx = [((p[0] - TX) * rx + (p[2] - TZ) * rz + HWc) * SCc for p in t["w"]]
    sy = [((HHc + 1.5) - p[1]) * SCc for p in t["w"]]
    raster(img, sx, sy, t["uv"], t["n"], RWc, RHc)
img.save(OUTD / "massif_carry_close.png")
print(f"-> {OUTD / 'massif_carry_close.png'} (west face at game texel scale)")
S2 = 8
img = Image.new("RGB", (int(BLOCK * S2), int(BLOCK * S2)), (24, 40, 72))
for t2 in sorted(range(len(rt)), key=lambda t3: min(p[1] for p in rt[t3]["w"])):
    t = rt[t2]
    sx = [(p[0] - bx * BLOCK) * S2 for p in t["w"]]
    sy = [(-p[2] - by * BLOCK) * S2 for p in t["w"]]
    raster(img, sx, sy, t["uv"], t["n"], int(BLOCK * S2), int(BLOCK * S2))
img.save(OUTD / "massif_carry_top.png")
print(f"-> {OUTD / 'massif_carry_top.png'}")

print(f"suggested teleport: ({math.floor(TX - r_out - 2) + 0.5}, {math.floor(TZ) + 0.5}) "
      f"on the west grass, face east")

# ---- 8. deploy ----------------------------------------------------------------------------------
if len(sys.argv) > 1 and sys.argv[1] == "deploy":
    BK.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(src, BK / f"{src.name}.{ts}")
    outp = M.deploy_override(new_bm, mod_folder="FF9CustomMap-world", part="Terrain")
    print(f"deployed -> {outp} ({len(new_bm.tris)} tris)")
    print("DONE -- re-run world-mirror, then F6 world re-entry + teleport above.")
else:
    print("dry run only -- re-run with 'deploy' to write.")
