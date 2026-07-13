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
import json
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
# THE ALCOVE FLOOR CARRY: the notch's flat floor (donor x 32-38 z -38..-31, y 5.3,
# cave-floor tiles -- the Object roof's ground) is mountain-attached terrain. Without it
# the blob rim OSCILLATES 1.5<->6.3 inside the notch and no smooth ground apron can meet
# it (the v3 zip slope gate tripped). Carrying it verbatim closes the high box; only the
# Object mesh itself (a separate part) stays behind.
NBOX = lambda c: 31.0 < c[0] < 40.5 and -38.5 < c[2] < -30.5
seeds = []
for e in once_edges(blob):
    for t in d_edge[e]:
        if t not in blob and dtopo[t] == 0:                # floor tris only, never canopy
            c = dV[dtri[t]].mean(axis=0)
            if NBOX(c) and min(dV[i][1] for i in dtri[t]) > 4.5:
                seeds.append(t)
st = list(seeds)
added = 0
while st:
    t = st.pop()
    if t in blob:
        continue
    c = dV[dtri[t]].mean(axis=0)
    if not (NBOX(c) and min(dV[i][1] for i in dtri[t]) > 4.5):
        continue
    blob.add(t)
    added += 1
    for a, b in ((0, 1), (1, 2), (2, 0)):
        for t2 in d_edge[tuple(sorted((kk3(dV[dtri[t][a]]), kk3(dV[dtri[t][b]]))))]:
            if t2 not in blob and dtopo[t2] == 0:
                st.append(t2)
print(f"alcove floor carried: {added} tris (verbatim, incl. the cave-floor tiles)",
      flush=True)

oe = once_edges(blob)
rings1 = chain_rings(oe)
rings1.sort(key=lambda r: -abs(signed_area(r)))
if len(rings1) > 1:                                        # fill enclosed pockets whole
    inner_pts = {p for r in rings1[1:] for p in r}
    st = [t for e in oe if e[0] in inner_pts and e[1] in inner_pts
          for t in d_edge[e] if t not in blob]
    filled = 0
    while st:
        t = st.pop()
        if t in blob:
            continue
        blob.add(t)
        filled += 1
        for a, b in ((0, 1), (1, 2), (2, 0)):
            for t2 in d_edge[tuple(sorted((kk3(dV[dtri[t][a]]), kk3(dV[dtri[t][b]]))))]:
                if t2 not in blob:
                    st.append(t2)
    print(f"enclosed pocket filled: {filled} tris (verbatim)", flush=True)
    oe = once_edges(blob)
    rings1 = chain_rings(oe)
    rings1.sort(key=lambda r: -abs(signed_area(r)))
# rings beyond the outer one must be OBJECT APERTURES -- the falls-aperture law at
# mountain scale: literal holes in the terrain whose boundary is exactly the embedded
# Object mesh's vertex set (Uaho: the alcove back wall). Carried as verbatim PLUGS below.
om = X.read_block(*DONOR, disc=1, part="object")
oV = np.asarray(om.verts, dtype=np.float64)
oU = np.asarray(om.uvs, dtype=np.float64)
oN = om.normals
otris = [om.flat_index[3 * t:3 * t + 3] for t in range(len(om.flat_index) // 3)]
okeys = {kk3(p) for p in oV}
apertures = []
for r in rings1[1:]:
    assert all(p in okeys for p in r), f"extra ring is NOT an object aperture: {r[:3]}"
    apertures.append(r)
rim = rings1[0]
assert len(rim) == len(oe) - sum(len(r) for r in apertures), "ring accounting"
if apertures:
    print(f"object apertures: {[len(r) for r in apertures]} pts "
          f"(plugged with the object's own tris)", flush=True)
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

# ---- 2b. THE MINT-HOLE PATCH: the r31 seed-42 mint ships a MISSING grass tri (three
# once-edges forming a closed 3-cycle at (143.5, 3.2, -1263.8) -- the in-game "sliver";
# a kit bug, flagged separately). Detect every once-edge 3-cycle above sea level and
# fill it with its neighbors' own language: each corner copies uv/normal/id from a
# coincident entry whose tri shares the patch tri's 4u cell (same mains mapping).
eu_h = Counter()
for tri in gtris:
    w = [gpos[i] for i in tri]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        eu_h[tuple(sorted((kk3(w[a]), kk3(w[b]))))] += 1
oh = [e for e, n in eu_h.items() if n == 1
      and e[0][1] > 0.5 and e[1][1] > 0.5]
adj_h = defaultdict(set)
for a, b in oh:
    adj_h[a].add(b)
    adj_h[b].add(a)
holes3 = set()
for a in adj_h:
    for b in adj_h[a]:
        for c in adj_h[b]:
            if c != a and c in adj_h[a]:
                holes3.add(tuple(sorted((a, b, c))))
ent_at = defaultdict(list)                                 # position -> vertex entries
for tdx, tri in enumerate(gtris):
    for i in tri:
        ent_at[kk3(gpos[i])].append((tdx, i))
cell4 = lambda x, z: (math.floor(x / 4.0), math.floor(z / 4.0))
n_orig = len(gtris)


def decode_cell_early(ccell):
    """The cell's (quad, ori) from any kept tri that exact-matches the mains language."""
    for tdx in range(n_orig):
        tri = gtris[tdx]
        tc = np.mean([gpos[j] for j in tri], axis=0)
        if cell4(tc[0], tc[2]) != ccell:
            continue
        for q in [(u2, v2) for u2 in (0, 1) for v2 in (0, 1)]:
            for o in (0, 90, 180, 270):
                err = 0.0
                for j in tri:
                    mu, mv = G.mains_uv(gpos[j][0], gpos[j][2], ccell, q, o)
                    err = max(err, abs(mu - guv[j][0]), abs(mv - guv[j][1]))
                if err < 1e-4:
                    return q, o
    return None


for cyc in sorted(holes3):
    cen = np.mean([list(p) for p in cyc], axis=0)
    ccell = cell4(cen[0], cen[2])
    # uv = the centroid cell's OWN decoded mapping evaluated at the corners -- the
    # mint's convention for cell-straddling tris. (Corner-copies from coincident
    # entries mix NEIGHBORING cells' mappings when the hole straddles a cell edge =
    # the round-7 "weird texture" zipper stripe.)
    qo = decode_cell_early(ccell)
    assert qo, f"mint-hole cell {ccell} has no decodable mains tri"
    q, o = qo
    a3, b3, c3 = (np.array(p) for p in cyc)
    order = cyc if np.cross(b3 - a3, c3 - a3)[1] > 0 else (cyc[0], cyc[2], cyc[1])
    new_idx = []
    for p in order:
        pick = ent_at[p][0][1]                             # normal/id from any twin entry
        gpos.append(list(gpos[pick]))
        gnrm.append(list(gnrm[pick]))
        guv.append(list(G.mains_uv(p[0], p[2], ccell, q, o)))
        gtan.append(list(gtan[pick]))
        new_idx.append(len(gpos) - 1)
    gtris.append(new_idx)
    gtopo.append(X.decode_id(int(round(gtan[new_idx[0]][0])))["topograph"])
    print(f"mint hole PATCHED at ({cen[0]:.1f},{cen[2]:.1f}) y {cen[1]:.1f} "
          f"(cell {ccell} quad {q} ori {o})", flush=True)
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
# PRISTINE once-edge baseline, captured BEFORE any mutation: computed after the lift it
# cancels self-consistent weld splits and the crack gate goes blind (the round-5 crack)
eu0 = Counter()
for tri in gtris:
    w = [gpos[i] for i in tri]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        eu0[tuple(sorted((kk3(w[a]), kk3(w[b]))))] += 1
once0 = {e for e, n in eu0.items() if n == 1}


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

# ---- 3. anchor + carry: ROCK RIGID, THE GROUND CONFORMS ----------------------------------------
# v3 architecture. v1/v2 blended the ROCK down to the flat bench (a Shepard conform over
# the rim deltas) -- and smeared the whole low east lobe: the 7u support covered most of
# it, verbatim uvs over moved verts = 1.2-2.5x vertical stretch (the in-game "stretched
# section", mist-hidden at the first approval; both panel-probe verdicts were confounded
# by it). THE ROCK-RIGID LAW: carried rock never deforms beyond the global affine
# (de-tilt + DY); ALL seating deformation goes to the GRASS -- at real Uaho the ground
# RISES to meet the high foot, so the bench gets a donor-shaped apron lift (pure-Y
# displacement of kept plain-grass verts, the proven hill-at-scale mechanism) rising
# from bench ground to the rigid rim over GBLEND, tapered at block borders (a displaced
# border vert would crack against the neighbor block's twin) AND near non-plain tris
# (the coast band must not deform).
rim_med = float(np.median([p[1] for p in rim2]))
near_ys = [gpos[i][1] for tdx, tri in enumerate(gtris) if plain[tdx] for i in tri
           if not pip(gpos[i][0], gpos[i][2], rim_poly)
           and near(gpos[i][0], gpos[i][2], rim_poly, CLEAR + 3.0)]
ground_med = float(np.median(near_ys))
DY = ground_med - rim_med


def carry_vert(i):
    pr = rot_pt(dV2[i], ROT)
    return [pr[0] + DX, pr[1] + DY, pr[2] + DZ]


GBLEND = 12.0
rim_nodes = []                                             # (x, z, RIGID rim height)
for p in rim_set:
    pr = rot_pt(detilt_p(p), ROT)
    rim_nodes.append((pr[0] + DX, pr[2] + DZ, pr[1] + DY))
print(f"rigid rim heights: [{min(n[2] for n in rim_nodes):.2f},"
      f"{max(n[2] for n in rim_nodes):.2f}] vs ground med {ground_med:.2f} "
      f"(the grass apron absorbs the difference over {GBLEND}u)", flush=True)
# positions touched by ANY non-plain tri: the lift must be EXACTLY zero there --
# worldmap meshes don't share vertex entries (welds = coincident positions), so a
# lift applied to the grass-side entry but not the coast-side twin SPLITS the weld
# (the round-5 crack at the grass/coast boundary: sea visible through the sliver)
nonplain_pos = np.array(sorted({(kk3(gpos[i])[0], kk3(gpos[i])[2])
                                for tdx, tri in enumerate(gtris) if not plain[tdx]
                                for i in tri}))


def ground_lift(px, pz, py, dnp):
    """Pure-Y apron field: 0 far away -> (rim height - ground) at the rim."""
    wsum = hsum = 0.0
    dmin2 = 1e18
    for (nx2, nz2, hy) in rim_nodes:
        dd2 = (px - nx2) ** 2 + (pz - nz2) ** 2
        dmin2 = min(dmin2, dd2)
        if dd2 > GBLEND * GBLEND:
            continue
        w = 1.0 / (dd2 + 0.04)
        wsum += w
        hsum += w * hy
    if wsum <= 0.0 or dmin2 >= GBLEND * GBLEND:
        return 0.0
    W = (1.0 - math.sqrt(dmin2) / GBLEND) ** 2
    bt = min(1.0, (min(px - BLOCK * bx, BLOCK * (bx + 1) - px,
                       pz + BLOCK * (by + 1), -BLOCK * by - pz) - 0.5) / 3.0)
    pt = min(1.0, (dnp - 2.5) / 3.0)                       # die before the coast band
    return max(0.0, bt) * max(0.0, pt) * W * (hsum / wsum - py)


# lift by POSITION (computed once per unique position, dnp = exact distance to the
# nearest non-plain VERTEX position -- centroids under-measure at big coast tris),
# then applied to EVERY coincident vertex entry so no weld can split
cand = {}
for tdx, tri in enumerate(gtris):
    if not plain[tdx]:
        continue
    for i in tri:
        k = kk3(gpos[i])
        if k in cand:
            continue
        dnp = float(np.sqrt(((nonplain_pos - np.array([k[0], k[2]])) ** 2)
                            .sum(axis=1).min()))
        cand[k] = ground_lift(k[0], k[2], gpos[i][1], dnp)
lift_of = {}
lift_max = 0.0
for i in range(len(gpos)):
    lf = cand.get(kk3(gpos[i]), 0.0)
    if abs(lf) > 1e-6:
        gpos[i][1] += lf
        lift_of[i] = lf
        lift_max = max(lift_max, abs(lf))
print(f"ground apron: {len(lift_of)} vertex entries lifted "
      f"({sum(1 for v in cand.values() if abs(v) > 1e-6)} positions, "
      f"max {lift_max:.2f}u)", flush=True)

# ---- 3b. hole carve (on the LIFTED bench; the drop test is plan-only) ---------------------------
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
crims.sort(key=lambda r: -abs(signed_area(r)))
assert len(crims) == 1 + len(apertures), "carried ring count changed in transit"
crim = crims[0]

# THE APERTURE PLUGS: the Object mesh's own geometry + uv, verbatim, carried as terrain
# (its uvs sample painted rock/dirt in the terrain atlas -- verified offline, 0 blank;
# winding up-facing). id = the adjacent rock's; normals de-tilted + rotated; verts snap
# to the carried blob floats so the plug welds shut.
plug_parents = []
if apertures:
    ap_pts = {p for r in apertures for p in r}
    ap_carried = {}
    for t in blob:
        tri = dtri[t]
        for k in range(3):
            k0 = kk3(dV[tri[k]])
            if k0 in ap_pts:
                ap_carried[k0] = carried[t][k]
    plug_id = None
    for r in apertures:
        for i2 in range(len(r)):
            e = tuple(sorted((r[i2], r[(i2 + 1) % len(r)])))
            for t2 in d_edge.get(e, ()):
                if dtopo[t2] in ROCK:
                    plug_id = float(dT[dtri[t2][0]][0])
                    break
            if plug_id:
                break
        if plug_id:
            break
    assert plug_id is not None

    def carry_pt(p):
        pr = rot_pt(detilt_p(p), ROT)
        return [pr[0] + DX, pr[1] + DY, pr[2] + DZ]

    # the object's own uvs target the OBJECT material -- in the TERRAIN atlas they
    # sample GRASS (the in-game round-3 verdict: "the object hole is filled with
    # grass"). The plug instead CONTINUES the surrounding rock chart: fit the affine of
    # the collar (the rock tris touching the aperture, largest uv-continuous group) and
    # evaluate it at the plug verts -- the panel's own flow extended across the hole,
    # exactly how every within-panel edge already flows (the gore-panel law).
    collar = [t for t in blob if dtopo[t] in ROCK
              and any(kk3(dV[i]) in ap_pts for i in dtri[t])]
    cpar = {t: t for t in collar}

    def cfind(t):
        while cpar[t] != t:
            cpar[t] = cpar[cpar[t]]
            t = cpar[t]
        return t

    cuv = {(t, kk3(dV[i])): (dU[i][0], dU[i][1]) for t in collar for i in dtri[t]}
    for t1 in collar:
        for t2 in collar:
            if t2 <= t1:
                continue
            shared = [kk3(dV[i]) for i in dtri[t1]
                      if kk3(dV[i]) in {kk3(dV[j]) for j in dtri[t2]}]
            if len(shared) < 2:
                continue
            if all(abs(cuv[(t1, s)][0] - cuv[(t2, s)][0]) < 0.0015
                   and abs(cuv[(t1, s)][1] - cuv[(t2, s)][1]) < 0.0015 for s in shared):
                r1, r2 = cfind(t1), cfind(t2)
                if r1 != r2:
                    cpar[r1] = r2
    groups = defaultdict(list)
    for t in collar:
        groups[cfind(t)].append(t)
    cg = max(groups.values(), key=len)
    rows_, ru_, rv_ = [], [], []
    for t in cg:
        for i in dtri[t]:
            rows_.append([dV[i][0], dV[i][1], dV[i][2], 1.0])
            ru_.append(dU[i][0])
            rv_.append(dU[i][1])
    Am_ = np.array(rows_)
    cu_, *_ = np.linalg.lstsq(Am_, np.array(ru_), rcond=None)
    cv_, *_ = np.linalg.lstsq(Am_, np.array(rv_), rcond=None)
    res_u = float(np.percentile(np.abs(Am_ @ cu_ - ru_) * 2048, 90))
    res_v = float(np.percentile(np.abs(Am_ @ cv_ - rv_) * 4096, 90))
    print(f"plug chart: collar {len(collar)} tris, biggest continuous group {len(cg)}, "
          f"affine residual p90 u{res_u:.0f} v{res_v:.0f} px", flush=True)

    def plug_uv(p):
        v4 = np.array([p[0], p[1], p[2], 1.0])
        return float(v4 @ cu_), float(v4 @ cv_)

    for tri in otris:
        corners = []
        for i in tri:
            w = ap_carried.get(kk3(oV[i])) or carry_pt(oV[i])
            n3 = rot_n(detilt_n(oN[i]), ROT)
            uu, vv = plug_uv(oV[i])
            corners.append((*w, uu, vv, *n3))
        plug_parents.append((tuple(corners), plug_id, "plug"))
    stage1 = json.loads((OUTD / "daguerreo_massif.json").read_text())
    puA, pvA = stage1["phase"]
    pcols = sorted({math.floor((c[3] - puA) / 0.0625)
                    for cs, _, _ in plug_parents for c in cs})
    prows = sorted({math.floor((c[4] - pvA) / 0.03125)
                    for cs, _, _ in plug_parents for c in cs})
    print(f"aperture plugs: {len(plug_parents)} object tris carried as terrain "
          f"(id {plug_id:.0f}, chart cols {pcols} rows {prows})", flush=True)
    assert min(pcols) >= 5 and max(pcols) <= 10 and min(prows) >= 6 and max(prows) <= 12, \
        "plug chart left the rock band"
rim_nrm = {}
for t in blob:
    for k in range(3):
        key = kk3(carried[t][k])
        rim_nrm.setdefault(key, rot_n(dN2[dtri[t][k]], ROT))
print(f"carried: peak y {max(p[1] for ps in carried.values() for p in ps):.1f}, "
      f"DY {DY:+.2f}", flush=True)

# ---- 5. zip annulus (the proven machinery) ------------------------------------------------------
hole_ord = list(hole)
rim_base = list(crim)
if signed_area(hole_ord) * signed_area(rim_base) < 0:
    rim_base.reverse()


def rimw(p):
    return tuple(c_float[p])


def d2(p, q):
    return (p[0] - q[0]) ** 2 + (p[2] - q[2]) ** 2


# minimal-total-chord DP zip: the greedy walk stalls on the floor-mouth CONCAVITY into
# 17.5u chords at any rotation; the DP strip between the two rings is optimal and
# concavity-immune (30x27 states)
i0, j0 = min(((i, j) for i in range(len(hole_ord)) for j in range(len(rim_base))),
             key=lambda ij: d2(hole_ord[ij[0]], rimw(rim_base[ij[1]])))
H = hole_ord[i0:] + hole_ord[:i0]
R = rim_base[j0:] + rim_base[:j0]
NH, NR = len(H), len(R)
Rw = [rimw(p) for p in R]
INF = 1e18
cost = [[INF] * (NR + 1) for _ in range(NH + 1)]
back = [[None] * (NR + 1) for _ in range(NH + 1)]
cost[0][0] = 0.0
for i in range(NH + 1):
    for j in range(NR + 1):
        c0 = cost[i][j]
        if c0 >= INF:
            continue
        if i < NH:
            nc = c0 + math.sqrt(d2(H[(i + 1) % NH], Rw[j % NR]))
            if nc < cost[i + 1][j]:
                cost[i + 1][j] = nc
                back[i + 1][j] = "h"
        if j < NR:
            nc = c0 + math.sqrt(d2(H[i % NH], Rw[(j + 1) % NR]))
            if nc < cost[i][j + 1]:
                cost[i][j + 1] = nc
                back[i][j + 1] = "r"
zip_tris = []
i, j = NH, NR
while i > 0 or j > 0:
    if back[i][j] == "h":
        zip_tris.append((H[(i - 1) % NH], H[i % NH], Rw[j % NR]))
        i -= 1
    else:
        zip_tris.append((H[i % NH], Rw[j % NR], Rw[(j - 1) % NR]))
        j -= 1
rim_ord = R
zip_maxe = 0.0
for tri3 in zip_tris:
    for a, b in ((0, 1), (1, 2), (2, 0)):
        zip_maxe = max(zip_maxe, math.sqrt(d2(tri3[a], tri3[b])))
print(f"zip annulus: {len(zip_tris)} tris (DP, max chord {zip_maxe:.1f}u)", flush=True)

# ---- 5b. apron + zip shading: re-smooth the CHANGED grass in place ------------------------------
# the lift tilts the real surface up to ~15deg but kept verts still wore the mint's
# flat-ground normals, and the zip interpolated donor-rock normals across its whole
# band -- together = the in-game "seam in the grass" ring (round 4). Re-smooth
# area-weighted over the FINAL geometry, applied only where the ground actually moved
# (blended by lift magnitude -> exact mint normals at the region edge, no new seam);
# rim verts keep the donor's feet-weld normals.
acc = defaultdict(lambda: np.zeros(3))


def acc_tri(p3):
    a, b, c3 = (np.asarray(q, dtype=float) for q in p3)
    fn = np.cross(b - a, c3 - a)
    if fn[1] < 0:
        fn = -fn
    for q in p3:
        acc[kk3(q)] += fn


for tdx, tri in enumerate(gtris):
    if tdx not in drop:
        acc_tri([gpos[i] for i in tri])
for t in blob:
    acc_tri(carried[t])
for tri3 in zip_tris:
    acc_tri(list(tri3))
n_ns = 0
for i, lf in lift_of.items():
    s = min(1.0, abs(lf) / 0.4)
    v3 = acc[kk3(gpos[i])]
    L = float(np.linalg.norm(v3))
    if s <= 0.0 or L < 1e-9:
        continue
    nb2 = np.asarray(gnrm[i], dtype=float) * (1 - s) + (v3 / L) * s
    nb2 /= (np.linalg.norm(nb2) or 1.0)
    gnrm[i] = nb2.tolist()
    n_ns += 1
print(f"apron re-smooth: {n_ns} vert normals blended by lift", flush=True)

# NOTE -- the donor's Object alcove (donor x 32-38 z -38..-31: a flat y-5.3 pocket
# wearing cave-floor tiles cols 0-2 rows 24-25, roofed by a 5-tri Object mesh in the
# separate object part) carries over OPEN, its rock walls unfringed (the painter never
# dressed what the roof hid). That is a STRUCTURE FINDING, kept as-is per the user: the
# bench exists to study real mountain anatomy, and small mountains carry embedded
# object ensembles the terrain alone doesn't close. A fringe synth-patch was built,
# deployed, and REVERTED (2026-07-13) -- do not paper over donor structure.
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
new_parents.extend(plug_parents)
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
    # plain positional mains, UNCLAMPED -- the mesa/forest-proven form. (An earlier
    # cell clamp smeared edge texels down the DP zip's long chords = grass streaks; it
    # existed only for the alpha-blind atlas gate's false positives, which the
    # transparent-AND-dark gate resolved.)
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
# once-edge gate = BASELINE-SUBTRACTED against the PRISTINE snapshot (captured before
# the lift): the mint has its own legal once-edges; the build must not ADD any --
# including lift-split welds ANYWHERE in the block
eu3 = Counter()
for t in range(len(tris)):
    w = [(pos[i][0] + BLOCK * bx, pos[i][1], pos[i][2] - BLOCK * (by + 1) + BLOCK)
         for i in tris[t]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        eu3[tuple(sorted((kk3(w[a]), kk3(w[b]))))] += 1
inner_once = [e for e, n in eu3.items() if n == 1 and e not in once0]
for e in inner_once[:6]:
    print(f"  NEW ONCE EDGE: {e[0]} -- {e[1]}", flush=True)
worst_rig = 0.0                                            # THE ROCK-RIGID GATE
for t in blob:
    tri = dtri[t]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        d0 = float(np.linalg.norm(dV[tri[a]] - dV[tri[b]]))
        if d0 > 0.05:
            worst_rig = max(worst_rig, abs(math.dist(carried[t][a], carried[t][b]) / d0 - 1.0))
g_worst = 0.0                                              # the apron slope envelope
for tdx, tri in enumerate(gtris):
    if tdx in drop or not plain[tdx]:
        continue
    a, b, c3 = (np.array(gpos[i]) for i in tri)
    fn = np.cross(b - a, c3 - a)
    L = float(np.linalg.norm(fn)) or 1.0
    g_worst = max(g_worst, math.degrees(math.acos(max(-1, min(1, abs(fn[1]) / L)))))
print(f"GATES: down={down} maxEdge={maxe:.1f} nearMiss={nm // 2} "
      f"annulusOnce={len(inner_once)} zipRise={zip_rise:.2f} zipNyMin={zip_ny_min:.2f} "
      f"rockRigid={worst_rig * 100:.1f}% apronSlope={g_worst:.1f}deg", flush=True)
assert down == 0 and nm == 0 and not inner_once and maxe < 9.0
assert zip_rise <= 2.34 and zip_ny_min >= 0.83, \
    "zip steeper than the grass envelope (0.83 ~ 34deg allows the alcove-mouth bank)"
assert worst_rig < 0.035, "carried rock deformed beyond the de-tilt affine"
assert g_worst <= 29.5, "the ground apron exceeds the grass slope envelope"

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
            aa_, rgb_ = at_b(u_, v_)
            # blank = transparent AND dark: Moguri paints some in-tile edge strips with
            # alpha 0 (grass colors, alpha-ignored opaque shader renders them fine);
            # true gutter garbage is transparent AND near-black
            if aa_ < 24 and sum(rgb_) < 90:
                nb += 1
    if nb:
        blank += 1
        print(f"  BLANK {fam} nb={nb} uv {[(round(c[3], 4), round(c[4], 4)) for c in corners]}"
              f" at ({corners[0][0]:.1f},{corners[0][2]:.1f})", flush=True)
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
for fname, (vx, vz, rx, rz), lbl in (
        ("massif_carry_close.png", (1.0, 0.0, 0.0, 1.0), "west face"),
        ("massif_carry_close_e.png", (-1.0, 0.0, 0.0, -1.0), "east face (the notch)")):
    img = Image.new("RGB", (RWc, RHc), (150, 178, 210))
    rec = sorted(range(len(rt)),
                 key=lambda t2: max((p[0] - TX) * vx + (p[2] - TZ) * vz
                                    for p in rt[t2]["w"]))
    for t2 in rec:
        t = rt[t2]
        sx = [((p[0] - TX) * rx + (p[2] - TZ) * rz + HWc) * SCc for p in t["w"]]
        sy = [((HHc + 1.5) - p[1]) * SCc for p in t["w"]]
        raster(img, sx, sy, t["uv"], t["n"], RWc, RHc)
    img.save(OUTD / fname)
    print(f"-> {OUTD / fname} ({lbl} at game texel scale)")
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
