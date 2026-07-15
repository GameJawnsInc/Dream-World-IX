"""RUNG D v3 -- THE TWO-LEVEL ISLAND, BEND-CARRY EDITION: island F as lowland-south /
plateau-north, walled by a REAL escarpment strip bent along the crest.

Why v3: three synthesis rounds each minted a new failure mode; the wall-anatomy study
(wall_anatomy.py) then showed real walls are organized nothing like synth quads --
SHINGLED FREE STRIPS (zero course welds), TOPS FLOAT just OUTSIDE the grass edge (zero
crest welds, never under walkable grass), FEET WELD to the ground, NORMALS are smoothed
up-leaning terrain normals, UVs fractional, crests jagged. So v3 CARRIES: donor (17,12)'s
23.6u-tall 81u ribbon escarpment (corr(d,drop)=-0.96), parameterized (s,d,h) against its
smoothed crest, bent along OUR smoothed crest ring in 2 shingle-overlapped laps, verts+UVs
+normals verbatim (normals yaw-rotated with the bend). The land side CLIPS at ground level
(feet weld by cut); the sea side keeps free bases. The corridor zip (proven v2 machinery)
bridges the clip-edge contact line to the south chain, ending >=4u inland (THE MOAT LAW v2).

Usage:  py studies/overworld-topography/two_level_v3.py [deploy]
        (deploy expects the PRISTINE island F on disk -- re-run the world-island mint first)
"""
import json
import math
import os
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
from ff9mapkit.world.island import build_landmass

GP = Path(_cfg.find_game_path(None))
MODW = GP / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
BK = Path(__file__).resolve().parents[2] / "backups"
OUT_RENDER = Path(__file__).with_name("out") / "island_f_twolevel_v3_render.png"
BLK = (3, 17)
BLOCK = 64.0
CX, CZ = 224.0, -1120.0

PLATEAU_Y = 17.0
Z_CHORD = -1116.0
GROUND_Y = 3.2                                             # the islet's flat lowland level
RAISE = PLATEAU_Y - GROUND_Y
CLEAR = 2.5                                                # strip clear on the PLATEAU side
TRIM_Y = 2.8                                               # THE MOAT LAW: rim-height chain ends
INLAND = 0.0                                               # moat arbitration belongs to the
#   rule-f gate (sea-under-zip scanned directly); a blunt plan-distance trim ate the rim-top
#   verts (~1.2u from the outline but moat-protected by the kept band beneath them)
D_MID = 8.0                                                # the ribbon's anchor depth: mapping
#   along the mid-depth offset curve splits corner distortion between top (compression) and
#   foot (stretch) instead of the foot taking (r+d)/r alone (the cone trap in miniature)
DONOR = (17, 12)                                           # the ribbon escarpment (anatomy pick)
SEA_H_MIN = -19.5                                          # carry window below the donor crest
TUCK_Y, TUCK_D = 0.0, 0.0                                # tops float a WHISKER below+outside
#   (the donor's own crest-to-grass gap median is 0.00 -- a 0.35 tuck left a visible sliver)
LAP_OV = 6.0                                               # shingle overlap between laps
BAY_FILL = 4.5                                             # hull-closure: bays shallower than
#   this fill with raised grass (the mid-depth anchor BRIDGES concavities < D_MID, leaving
#   void pockets behind the wall -- small bays must close, not be followed)
kk3 = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

def seg_chord_z(x):
    return Z_CHORD + 1.6 * math.sin(0.11 * x)

def north_of_chord(x, z):
    return z > seg_chord_z(x)

# ---- 1. THE DONOR: extract + (s,d,h)-parameterize the real escarpment -------------------------
dbm = X.read_block(*DONOR, disc=1)
dV, dN, dU, dT = dbm.verts, dbm.normals, dbm.uvs, dbm.tangents
dntri = len(dbm.flat_index) // 3
dtri = [dbm.flat_index[3 * t:3 * t + 3] for t in range(dntri)]
dtopo = [X.decode_id(int(round(dT[i[0]][0])))["topograph"] for i in dtri]
wall49 = [t for t in range(dntri) if dtopo[t] == 49]
e2t = defaultdict(list)
for t in wall49:
    i = dtri[t]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        e2t[tuple(sorted((kk3(dV[i[a]]), kk3(dV[i[b]]))))].append(t)
dadj = defaultdict(set)
for ts in e2t.values():
    for i2 in range(len(ts)):
        for j2 in range(i2 + 1, len(ts)):
            dadj[ts[i2]].add(ts[j2])
            dadj[ts[j2]].add(ts[i2])
seen, comps = set(), []
for s in wall49:
    if s in seen:
        continue
    comp, st = {s}, [s]
    while st:
        t = st.pop()
        for t2 in dadj[t]:
            if t2 not in comp:
                comp.add(t2)
                st.append(t2)
    seen |= comp
    comps.append(comp)
dcomp = sorted(max(comps, key=len))
dverts = sorted({kk3(dV[j]) for t in dcomp for j in dtri[t]})
d_yhi = max(p[1] for p in dverts)
top = [p for p in dverts if p[1] > d_yhi - 2.2]
chain = [min(top, key=lambda p: (p[0], p[2]))]
rest = [p for p in top if p != chain[0]]
while rest:
    nxt = min(rest, key=lambda p: (p[0] - chain[-1][0]) ** 2 + (p[2] - chain[-1][2]) ** 2)
    if math.hypot(nxt[0] - chain[-1][0], nxt[2] - chain[-1][2]) > 9.0:
        break
    chain.append(nxt)
    rest.remove(nxt)
assert not rest, "donor crest chain did not consume all top verts"

def box_smooth(pts, w=3):
    n = len(pts)
    out = []
    for i in range(n):
        lo, hi = max(0, i - w), min(n, i + w + 1)
        out.append(tuple(sum(p[k] for p in pts[lo:hi]) / (hi - lo) for k in range(len(pts[0]))))
    return out

dsm = box_smooth([(p[0], p[1], p[2]) for p in chain])       # smoothed donor crest (x,y,z)
dcum = [0.0]
for i in range(1, len(dsm)):
    dcum.append(dcum[-1] + math.hypot(dsm[i][0] - dsm[i - 1][0], dsm[i][2] - dsm[i - 1][2]))
L_D = dcum[-1]

def donor_sdh(p):
    """(s, d, h, theta) of a donor vert vs the smoothed donor crest; +d = downhill"""
    best = None
    for i in range(len(dsm) - 1):
        ax, ay, az = dsm[i]
        bx, by_, bz = dsm[i + 1]
        vx, vz = bx - ax, bz - az
        L2 = (vx * vx + vz * vz) or 1e-9
        t01 = max(0.0, min(1.0, ((p[0] - ax) * vx + (p[2] - az) * vz) / L2))
        qx, qz = ax + t01 * vx, az + t01 * vz
        qy = ay + t01 * (by_ - ay)
        d2 = (p[0] - qx) ** 2 + (p[2] - qz) ** 2
        if best is None or d2 < best[0]:
            cross = vx * (p[2] - qz) - vz * (p[0] - qx)
            best = (d2, dcum[i] + t01 * (dcum[i + 1] - dcum[i]),
                    math.copysign(math.sqrt(d2), cross), p[1] - qy,
                    math.atan2(vz, vx))
    return best[1], best[2], best[3], best[4]

dpar = {}                                                  # vert key -> (s, d, h, theta)
for p in dverts:
    dpar[p] = donor_sdh(p)

# THE INTERIOR WINDOW: the donor ribbon TAPERS at its ends; a lap seam pairing a tapered
# end with a tapered start pinches open. Carry only the run where the wall is full-height.
_bins = defaultdict(float)
for p in dverts:
    s, dd, h, _ = dpar[p]
    _bins[int(s // 2)] = min(_bins[int(s // 2)], h)
_deep = sorted(b for b, hmin in _bins.items() if hmin <= -9.0)
_best, _cur = [], []
for b in _deep:
    if _cur and b > _cur[-1] + 2:                          # bridge single-bin shallow gaps
        if len(_cur) > len(_best):
            _best = _cur
        _cur = []
    _cur.append(b)
if len(_cur) > len(_best):
    _best = _cur
S_LO, S_HI = _best[0] * 2.0, (_best[-1] + 1) * 2.0
L_EFF = S_HI - S_LO

# the donor's LOCAL foot line: min h per 2u of arc (the wall's depth varies along the run)
_bkeys = sorted(_bins)
_bc = np.array([(k + 0.5) * 2.0 for k in _bkeys])
_bv = np.array([_bins[k] for k in _bkeys], dtype=float)
def h_bot(s):
    return float(np.interp(s, _bc, _bv))

# THE WANDER CORRECTION (donor side): the TRUE crest meanders +/-2u around the smoothed
# centerline; tops must be referenced to the TRUE edge or the carried top wanders off the
# target boundary leaving see-through gaps
chain_xz = [(p[0], p[2]) for p in chain]
def _near_open(px, pz, poly):
    best, q = 1e18, (px, pz)
    for i in range(len(poly) - 1):
        ax, az = poly[i]
        bx2, bz2 = poly[i + 1]
        vx, vz = bx2 - ax, bz2 - az
        L2 = (vx * vx + vz * vz) or 1e-9
        t01 = max(0.0, min(1.0, ((px - ax) * vx + (pz - az) * vz) / L2))
        qx, qz = ax + t01 * vx, az + t01 * vz
        d2 = (px - qx) ** 2 + (pz - qz) ** 2
        if d2 < best:
            best, q = d2, (qx, qz)
    return math.sqrt(best), q

ddelta = []
for i in range(len(dsm)):
    a = dsm[max(0, i - 1)]
    b = dsm[min(len(dsm) - 1, i + 1)]
    tx, tz = b[0] - a[0], b[2] - a[2]
    dd_, q = _near_open(dsm[i][0], dsm[i][2], chain_xz)
    cross = tx * (q[1] - dsm[i][2]) - tz * (q[0] - dsm[i][0])
    ddelta.append(math.copysign(dd_, cross))

def delta_d(s):
    i = max(0, int(np.searchsorted(dcum, s, side="right")) - 1)
    i = min(i, len(ddelta) - 2)
    t01 = (s - dcum[i]) / max(1e-9, dcum[i + 1] - dcum[i])
    return ddelta[i] + max(0.0, min(1.0, t01)) * (ddelta[i + 1] - ddelta[i])
win = [p for p in dverts if dpar[p][2] >= SEA_H_MIN]
d_max_win = max(dpar[p][1] for p in win)
# the LAND-side reach: over land the wall only descends to ground (RAISE deep) -- clear
# the strip for THAT footprint, not the full sea-depth window (over-clearing pushed the
# south chain into the coast and the inland trim ate it)
d_land = max(dpar[p][1] for p in dverts if dpar[p][2] >= -(RAISE + 1.0))
print(f"donor {DONOR}: {len(dcomp)} tris, crest run {L_D:.0f}u (interior window "
      f"[{S_LO:.0f},{S_HI:.0f}] = {L_EFF:.0f}u), window d_max {d_max_win:.1f}u, "
      f"land-side d_max {d_land:.1f}u", flush=True)
CLEAR_OUT = d_land + 3.5                                   # land footprint + apron + margin

# ---- 2. island F: deterministic rebuild == deployed bytes ------------------------------------
built = build_landmass(center=(CX, CZ), base_radius=26, seed=15, lobes=1, n_patches=0,
                       stamps="auto")
assert set(built["blocks"]) == {BLK}
import tempfile
_tmp = Path(tempfile.mkdtemp(prefix="ff9_twolevel3_"))
ref = M.write_ff9mesh(built["blocks"][BLK], _tmp / "ref.ff9mesh").read_bytes()
src = MODW / f"r{BLK[1]}" / f"Block[{BLK[0]}][{BLK[1]}] Terrain.ff9mesh"
pristine = src.read_bytes() == ref
print(f"deployed island F pristine: {pristine}", flush=True)

gpos = built["world"]["pos"]
gtris = built["world"]["tris"]
gmeta = built["world"]["meta"]
gnrm = built["world"]["nrm"]
outline = built["outline"]
print(f"island F rebuild: {len(gtris)} tris, CLEAR_OUT {CLEAR_OUT:.1f}u", flush=True)

# ---- 3. partition (asymmetric strip + sliver prune; NO shave -- crests are jagged) -------------
tri_cx = np.array([sum(gpos[i][0] for i in t) / 3 for t in gtris])
tri_cz = np.array([sum(gpos[i][2] for i in t) / 3 for t in gtris])
tri_fam = [gmeta[i][2] for i in range(len(gtris))]
north = np.array([north_of_chord(tri_cx[i], tri_cz[i]) for i in range(len(gtris))])

def near_chord(x, z):
    dz2 = z - seg_chord_z(x)
    return -CLEAR_OUT < dz2 < CLEAR

drop = set()
for i, t in enumerate(gtris):
    if tri_fam[i] == "rock":
        if north[i]:
            drop.add(i)
        continue
    if any(near_chord(gpos[j][0], gpos[j][2]) for j in t):
        drop.add(i)

def side_components(want_north):
    edge_map = defaultdict(list)
    for i2, t2 in enumerate(gtris):
        if i2 in drop or bool(north[i2]) != want_north:
            continue
        for a2, b2 in ((0, 1), (1, 2), (2, 0)):
            edge_map[tuple(sorted((kk3(gpos[t2[a2]]), kk3(gpos[t2[b2]]))))].append(i2)
    adjc = defaultdict(set)
    for ts in edge_map.values():
        for ii in range(len(ts)):
            for jj in range(ii + 1, len(ts)):
                adjc[ts[ii]].add(ts[jj])
                adjc[ts[jj]].add(ts[ii])
    seen2, comps2 = set(), []
    for s2 in range(len(gtris)):
        if s2 in seen2 or s2 in drop or bool(north[s2]) != want_north:
            continue
        comp2, st = {s2}, [s2]
        while st:
            t3 = st.pop()
            for t4 in adjc[t3]:
                if t4 not in comp2:
                    comp2.add(t4)
                    st.append(t4)
        seen2 |= comp2
        comps2.append(comp2)
    return sorted(comps2, key=len, reverse=True)

for want in (True, False):
    for c in side_components(want)[1:]:
        drop |= c
print(f"dropped: {len(drop)} tris ({dict(Counter(tri_fam[i] for i in drop))})", flush=True)

# ---- 4. boundary chains -------------------------------------------------------------------------
def boundary_edges():
    eu = Counter()
    for i2, t2 in enumerate(gtris):
        if i2 in drop:
            continue
        for a2, b2 in ((0, 1), (1, 2), (2, 0)):
            eu[tuple(sorted((kk3(gpos[t2[a2]]), kk3(gpos[t2[b2]]))))] += 1
    dropped_edges = set()
    for i2 in drop:
        t2 = gtris[i2]
        for a2, b2 in ((0, 1), (1, 2), (2, 0)):
            dropped_edges.add(tuple(sorted((kk3(gpos[t2[a2]]), kk3(gpos[t2[b2]])))))
    once = [e for e, n2 in eu.items() if n2 == 1 and e in dropped_edges]
    south_e = [e for e in once if not north_of_chord((e[0][0] + e[1][0]) / 2,
                                                     (e[0][2] + e[1][2]) / 2)]
    north_e = [e for e in once if north_of_chord((e[0][0] + e[1][0]) / 2,
                                                 (e[0][2] + e[1][2]) / 2)]
    return south_e, north_e

def chain_open(edges, what):
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    ends = [p for p, l in adj.items() if len(l) == 1]
    assert len(ends) == 2, f"{what}: {len(ends)} chain ends (want 2)"
    ch = [ends[0]]
    prev = None
    while True:
        nxts = [p for p in adj[ch[-1]] if p != prev]
        if not nxts:
            break
        prev = ch[-1]
        ch.append(nxts[0])
    assert len(ch) == len(edges) + 1, f"{what}: broken chain"
    return ch

def chain_closed(edges, what):
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    bad = [p for p, l in adj.items() if len(l) != 2]
    assert not bad, f"{what}: {len(bad)} odd-degree points"
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
    assert len(ring) == len({*ring}), f"{what} degenerate"
    assert len(ring) == len(edges), f"{what}: more than one ring"
    return ring

south_chain_e, north_chain_e = boundary_edges()
south_chain = chain_open(south_chain_e, "south hole chain")
north_ring = chain_closed(north_chain_e, "north boundary ring")

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

outline_poly = list(outline)

# NOTE (found round 4): the mint's Sea4 is a FULL-CELL plane under the whole island, not
# a thin lap. The pristine safety is the MOAT alone: sea only enters the movement cache if
# a query can RETURN it, i.e. within candidate reach (~1.5u) of the Terrain coverage edge
# (the outline). So the trap condition is OUTLINE PROXIMITY of walkable ground -- not
# "sea beneath" (that is everywhere).
def dist_to_poly(px, pz, poly):
    best = 1e18
    n = len(poly)
    for i in range(n):
        ax, az = poly[i]
        bx, bz = poly[(i + 1) % n]
        vx, vz = bx - ax, bz - az
        L2 = (vx * vx + vz * vz) or 1e-9
        t01 = max(0.0, min(1.0, ((px - ax) * vx + (pz - az) * vz) / L2))
        best = min(best, (px - (ax + t01 * vx)) ** 2 + (pz - (az + t01 * vz)) ** 2)
    return math.sqrt(best)

# THE MOAT LAW (+v2): rim-height chain ends AND >=INLAND from the outline
n_trim = 0
while len(south_chain) > 2 and (south_chain[0][1] < TRIM_Y or
                                dist_to_poly(south_chain[0][0], south_chain[0][2], outline_poly) < INLAND):
    south_chain.pop(0)
    n_trim += 1
while len(south_chain) > 2 and (south_chain[-1][1] < TRIM_Y or
                                dist_to_poly(south_chain[-1][0], south_chain[-1][2], outline_poly) < INLAND):
    south_chain.pop()
    n_trim += 1
print(f"chains: south {len(south_chain)} pts ({n_trim} trimmed to rim+inland), "
      f"north ring {len(north_ring)} pts", flush=True)

# ---- 5. OUR centerline: the raised crest ring, smoothed + framed -------------------------------
# THE HULL CLOSURE: close small bays (deviation <= BAY_FILL) of the raised boundary with
# raised-grass FILL fans; the wall builds against the CLOSED polygon (the mid-depth anchor
# cannot follow concavities smaller than D_MID -- they would become void pockets)
ring_raised = [(p[0], p[1] + RAISE, p[2]) for p in north_ring]
_pts2 = [(p[0], p[2]) for p in ring_raised]
def _hull_idx(pts):
    idx = sorted(range(len(pts)), key=lambda i: (pts[i][0], pts[i][1]))
    def half(seq):
        out = []
        for i in seq:
            while len(out) >= 2:
                ox, oz = pts[out[-2]]
                ax, az = pts[out[-1]]
                bx, bz = pts[i]
                if (ax - ox) * (bz - oz) - (az - oz) * (bx - ox) <= 0:
                    out.pop()
                else:
                    break
            out.append(i)
        return out
    lo = half(idx)
    hi = half(list(reversed(idx)))
    return set(lo[:-1] + hi[:-1])

_on_hull = _hull_idx(_pts2)
n_ring = len(ring_raised)
fill_raw = []                                              # raised-grass fan tris (world xyz)
keep_flag = [True] * n_ring
_i0 = next(i for i in range(n_ring) if i in _on_hull)
_i = _i0
while True:
    _j = (_i + 1) % n_ring
    span = []
    while _j not in _on_hull:
        span.append(_j)
        _j = (_j + 1) % n_ring
    if span:
        A, B = ring_raised[_i], ring_raised[_j]
        dev = max(_near_open(ring_raised[k][0], ring_raised[k][2],
                             [(A[0], A[2]), (B[0], B[2])])[0] for k in span)
        if dev <= BAY_FILL:
            seq = [A] + [ring_raised[k] for k in span] + [B]
            for k in range(1, len(seq) - 1):
                fill_raw.append((seq[0], seq[k], seq[k + 1]))
            for k in span:
                keep_flag[k] = False
        else:
            print(f"  (bay at ({A[0]:.0f},{A[2]:.0f}) kept: deviation {dev:.1f} > "
                  f"{BAY_FILL})", flush=True)
    _i = _j
    if _i == _i0:
        break
crest_true = [ring_raised[k] for k in range(n_ring) if keep_flag[k]]
crest_poly = [(p[0], p[2]) for p in crest_true]
print(f"hull closure: {n_ring - len(crest_true)} bay verts -> {len(fill_raw)} fill tris; "
      f"crest {len(crest_true)} pts", flush=True)
def resample3_closed(pts, spacing):
    n = len(pts)
    cum = [0.0]
    for i in range(1, n + 1):
        a, b = pts[i - 1], pts[i % n]
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    per = cum[-1]
    m = max(8, int(round(per / spacing)))
    out = []
    for s in range(m):
        dd = per * s / m
        i = max(0, int(np.searchsorted(cum, dd)) - 1)
        t01 = (dd - cum[i]) / max(1e-9, cum[i + 1] - cum[i])
        a, b = pts[i % n], pts[(i + 1) % n]
        out.append((a[0] + t01 * (b[0] - a[0]), a[1] + t01 * (b[1] - a[1]),
                    a[2] + t01 * (b[2] - a[2])))
    return out

def box_smooth_closed(pts, w=3):
    n = len(pts)
    return [tuple(sum(pts[(i + k) % n][q] for k in range(-w, w + 1)) / (2 * w + 1)
                  for q in range(3)) for i in range(n)]

R = box_smooth_closed(resample3_closed(crest_true, 1.5))
NR = len(R)
cumR = [0.0]
for i in range(1, NR + 1):
    cumR.append(cumR[-1] + math.hypot(R[i % NR][0] - R[i - 1][0], R[i % NR][2] - R[i - 1][2]))
PER = cumR[-1]
sR = sum(R[i][0] * R[(i + 1) % NR][2] - R[(i + 1) % NR][0] * R[i][2] for i in range(NR))
sgnR = 1.0 if sR > 0 else -1.0

# THE MID-DEPTH ANCHOR CURVE O: the fold-filtered outward offset of R at D_MID, the
# ribbon's texel-true mapping axis
def offset_ring2(src_xz, D, dense_sp=1.0):
    n = len(src_xz)
    cum = [0.0]
    for i in range(1, n + 1):
        a, b = src_xz[i - 1], src_xz[i % n]
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    per = cum[-1]
    m = max(8, int(round(per / dense_sp)))
    dense = []
    for s in range(m):
        dd = per * s / m
        i = max(0, int(np.searchsorted(cum, dd)) - 1)
        t01 = (dd - cum[i]) / max(1e-9, cum[i + 1] - cum[i])
        a, b = src_xz[i % n], src_xz[(i + 1) % n]
        dense.append((a[0] + t01 * (b[0] - a[0]), a[1] + t01 * (b[1] - a[1])))
    s2 = sum(dense[i][0] * dense[(i + 1) % m][1] - dense[(i + 1) % m][0] * dense[i][1]
             for i in range(m))
    sgn = 1.0 if s2 > 0 else -1.0
    pts = []
    for i in range(m):
        px, pz = dense[(i - 1) % m]
        qx, qz = dense[(i + 1) % m]
        tx, tz = qx - px, qz - pz
        L = math.hypot(tx, tz) or 1.0
        pts.append((dense[i][0] + sgn * tz / L * D, dense[i][1] - sgn * tx / L * D))
    def dsrc(p):
        best = 1e18
        for i in range(m):
            ax, az = dense[i]
            bx2, bz2 = dense[(i + 1) % m]
            vx, vz = bx2 - ax, bz2 - az
            L2 = (vx * vx + vz * vz) or 1e-9
            t01 = max(0.0, min(1.0, ((p[0] - ax) * vx + (p[1] - az) * vz) / L2))
            dx, dz = p[0] - (ax + t01 * vx), p[1] - (az + t01 * vz)
            best = min(best, dx * dx + dz * dz)
        return math.sqrt(best)
    return [p for p in pts if dsrc(p) > D - 0.3]

R_xz = [(p[0], p[2]) for p in R]
O = offset_ring2(R_xz, D_MID)
NO = len(O)
cumO = [0.0]
for i in range(1, NO + 1):
    cumO.append(cumO[-1] + math.hypot(O[i % NO][0] - O[i - 1][0], O[i % NO][1] - O[i - 1][1]))
PER_O = cumO[-1]

def ring_param_R(px, pz):
    best, bd = 0.0, 1e18
    for i in range(NR):
        ax, az = R[i][0], R[i][2]
        bx2, bz2 = R[(i + 1) % NR][0], R[(i + 1) % NR][2]
        vx, vz = bx2 - ax, bz2 - az
        L2 = (vx * vx + vz * vz) or 1e-9
        t01 = max(0.0, min(1.0, ((px - ax) * vx + (pz - az) * vz) / L2))
        d2 = (px - (ax + t01 * vx)) ** 2 + (pz - (az + t01 * vz)) ** 2
        if d2 < bd:
            bd, best = d2, cumR[i] + t01 * (cumR[i + 1] - cumR[i])
    return best

def crest_y_at(sr):
    sr %= PER
    i = max(0, int(np.searchsorted(cumR, sr, side="right")) - 1)
    t01 = (sr - cumR[i]) / max(1e-9, cumR[i + 1] - cumR[i])
    return R[i % NR][1] + t01 * (R[(i + 1) % NR][1] - R[i % NR][1])

# per O vertex: the crest height AND the true boundary's wander vs R (our side of the
# wander correction -- positive = the true edge lies OUTWARD of R, i.e. toward O)
O_crest_y, O_delta = [], []
for p in O:
    sr = ring_param_R(p[0], p[1])
    O_crest_y.append(crest_y_at(sr))
    i = max(0, int(np.searchsorted(cumR, sr, side="right")) - 1)
    t01 = (sr - cumR[i]) / max(1e-9, cumR[i + 1] - cumR[i])
    rx = R[i % NR][0] + t01 * (R[(i + 1) % NR][0] - R[i % NR][0])
    rz = R[i % NR][2] + t01 * (R[(i + 1) % NR][2] - R[i % NR][2])
    best, qq = 1e18, (rx, rz)
    for k2 in range(len(crest_poly)):
        ax, az = crest_poly[k2]
        bx2, bz2 = crest_poly[(k2 + 1) % len(crest_poly)]
        vx, vz = bx2 - ax, bz2 - az
        L2 = (vx * vx + vz * vz) or 1e-9
        tt = max(0.0, min(1.0, ((rx - ax) * vx + (rz - az) * vz) / L2))
        qx, qz = ax + tt * vx, az + tt * vz
        d2 = (rx - qx) ** 2 + (rz - qz) ** 2
        if d2 < best:
            best, qq = d2, (qx, qz)
    sign = 1.0 if ((qq[0] - rx) * (p[0] - rx) + (qq[1] - rz) * (p[1] - rz)) > 0 else -1.0
    O_delta.append(sign * math.sqrt(best))

def anchor_at(sq):
    sq %= PER_O
    i = max(0, int(np.searchsorted(cumO, sq, side="right")) - 1)
    t01 = (sq - cumO[i]) / max(1e-9, cumO[i + 1] - cumO[i])
    a, b = O[i % NO], O[(i + 1) % NO]
    px = a[0] + t01 * (b[0] - a[0])
    pz = a[1] + t01 * (b[1] - a[1])
    cy = O_crest_y[i % NO] + t01 * (O_crest_y[(i + 1) % NO] - O_crest_y[i % NO])
    dl = O_delta[i % NO] + t01 * (O_delta[(i + 1) % NO] - O_delta[i % NO])
    tx, tz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(tx, tz) or 1.0
    # O and R share orientation; outward on O uses the same handedness sign
    nx, nz = sgnR * tz / L, -sgnR * tx / L
    return px, pz, cy, nx, nz, math.atan2(tz, tx), dl

print(f"our ring: {NR} pts / {PER:.0f}u; anchor curve O: {NO} pts / {PER_O:.0f}u, "
      f"laps {math.ceil(PER_O / (L_EFF - LAP_OV))}", flush=True)

# ---- 6. THE BEND-CARRY --------------------------------------------------------------------------
ID49 = float(X.encode_id(topograph=49))
ID13 = float(X.encode_id(topograph=13))
ID0 = float(X.encode_id(topograph=0))
new_parents = []                                           # (corners8, idall, fam)

n_laps = math.ceil(PER_O / (L_EFF - LAP_OV))
vshift = {}                                                # (lap, donor key) -> extra outward push

def crest_edge_at(px, pz):
    """the nearest point ON the boundary polygon + its lerped y (an exact edge weld)"""
    best, out = 1e18, (px, 17.0, pz)
    n = len(crest_poly)
    for i in range(n):
        ax, az = crest_poly[i]
        bx2, bz2 = crest_poly[(i + 1) % n]
        vx, vz = bx2 - ax, bz2 - az
        L2 = (vx * vx + vz * vz) or 1e-9
        t01 = max(0.0, min(1.0, ((px - ax) * vx + (pz - az) * vz) / L2))
        qx, qz = ax + t01 * vx, az + t01 * vz
        d2 = (px - qx) ** 2 + (pz - qz) ** 2
        if d2 < best:
            qy = crest_true[i][1] + t01 * (crest_true[(i + 1) % n][1] - crest_true[i][1])
            best, out = d2, (qx, qy, qz)
    return out

def place_vert(lap, p, j):
    """one carried vert's world position -- DETERMINISTIC per (lap, key), so shared verts
    always land together (a per-tri nudge tears shared edges; per-key shifts cannot)"""
    s, dd, h, th_d = dpar[p]
    s0 = lap * (L_EFF - LAP_OV)
    ox, oz, cy, nx, nz, th_o, dl_o = anchor_at(s0 + (s - S_LO))
    # THE WANDER CORRECTION: reference d to the TRUE crest on both sides
    dd_eff = (dd - delta_d(s)) + dl_o + TUCK_D + 0.06 * lap + vshift.get(("w", lap, p), 0.0)
    wx = ox + nx * (dd_eff - D_MID)
    wz = oz + nz * (dd_eff - D_MID)
    wy = cy + h - TUCK_Y
    if h > -1.0:
        # THE TOP SNAP: the donor's top row WELDS onto the boundary polygon (its own tops
        # sit at gap 0.00 against their grass -- a floating top left the plateau SLIT)
        wx, wy, wz = crest_edge_at(wx, wz)
    else:
        # every deeper vert stays OUTSIDE the boundary (rule-f at the plateau edge)
        for _ in range(2):
            if pip(wx, wz, crest_poly):
                bd = dist_to_poly(wx, wz, crest_poly) + 0.25
                wx += nx * bd
                wz += nz * bd
            else:
                break
    n3 = dN[j]
    rot = th_o - th_d
    cd, sd_ = math.cos(rot), math.sin(rot)
    return (wx, wy, wz, dU[j][0], dU[j][1],
            n3[0] * cd - n3[2] * sd_, n3[1], n3[0] * sd_ + n3[2] * cd)

def place_vert_foot(lap, p, j):
    """THE FOOT STRIP: the donor's real foot course (its fringe + ground weld, the bottom
    band above its LOCAL foot line) seated AT OUR GROUND -- the grass->mountain transition
    the mid-body clip destroyed. Shingle-legal: overlaps the main carry above it."""
    s, dd, h, th_d = dpar[p]
    s0 = lap * (L_EFF - LAP_OV)
    ox, oz, cy, nx, nz, th_o, dl_o = anchor_at(s0 + (s - S_LO))
    dd_eff = (dd - delta_d(s)) + dl_o + TUCK_D + 0.06 * lap + vshift.get(("f", lap, p), 0.0)
    wx = ox + nx * (dd_eff - D_MID)
    wz = oz + nz * (dd_eff - D_MID)
    rel = h - h_bot(s)
    if rel < 1.0:
        wy = GROUND_Y - 0.04                               # the bottom ROW welds FLAT to our
        #   flat lowland (the donor's foot rode its own uneven ground; a bin-interp foot
        #   line left the strip's bottom jagged + floating)
    else:
        wy = max(GROUND_Y + rel, GROUND_Y - 0.04)
    n3 = dN[j]
    rot = th_o - th_d
    cd, sd_ = math.cos(rot), math.sin(rot)
    return (wx, wy, wz, dU[j][0], dU[j][1],
            n3[0] * cd - n3[2] * sd_, n3[1], n3[0] * sd_ + n3[2] * cd)

wall_src = []                                              # ("w"|"f", lap, keys, jidx)
for lap in range(n_laps):
    s0 = lap * (L_EFF - LAP_OV)
    if s0 >= PER_O:
        break
    for t in dcomp:
        i = dtri[t]
        keys = [kk3(dV[j]) for j in i]
        pars = [dpar[p] for p in keys]
        smin = min(pr[0] for pr in pars) - S_LO
        smax = max(pr[0] for pr in pars) - S_LO
        if smax < -0.01 or smin > L_EFF + 0.01:
            continue                                        # fully outside the window
        # (straddlers stay -- they just overlap the neighbour lap; culling them bit
        # saw-tooth tears into every seam)
        if lap < n_laps - 1 and smin > (L_EFF - LAP_OV):
            continue                                        # the next lap re-covers it
        if s0 + smin >= PER_O + LAP_OV:
            continue                                        # past ring closure
        if sum(pr[2] for pr in pars) / 3 >= SEA_H_MIN:
            wall_src.append(("w", lap, keys, list(i)))
        rel = [pr[2] - h_bot(pr[0]) for pr in pars]
        if sum(rel) / 3 <= 6.0 and min(rel) >= -3.0:
            wall_src.append(("f", lap, keys, list(i)))      # the foot-course band

GHOST_ID = 4078.0                                          # the engine's own RAY-SKIP idall:
#   renders normally, invisible to every ground query (WMPhysics skips it) -- uncacheable
ghost_src = set()                                          # wall_src indices emitted as ghosts
FLIP = False                                               # set by the facing check below

parent_src_idx = []                                        # new_parents pos -> wall_src idx

def build_wall_parents():
    global parent_src_idx
    parent_src_idx = []
    out = []
    for m, (kind, lap, keys, i) in enumerate(wall_src):
        fn = place_vert if kind == "w" else place_vert_foot
        pts = tuple(fn(lap, p, j) for p, j in zip(keys, i))
        if kind == "f":
            cxm = sum(p[0] for p in pts) / 3
            czm = sum(p[2] for p in pts) / 3
            if not pip(cxm, czm, outline_poly):
                continue                                    # the sea side keeps free bases
        if FLIP:
            pts = (pts[0], pts[2], pts[1])
        out.append((pts, GHOST_ID if m in ghost_src else ID49,
                    "wall-ghost" if m in ghost_src else ("wall" if kind == "w"
                                                         else "wall-foot")))
        parent_src_idx.append(m)
    return out

# THE CARRY FACING CHECK: the (tangent, downhill) handedness of the donor vs the
# (tangent, outward) handedness of our ring can MIRROR the carry -- mirrored winding
# backface-culls the entire near wall in-game (the engine culls; the offline painter
# doesn't). Score both facings the same way and flip globally on mismatch.
def _facing_score(tris_pts, outward_fn):
    sc = 0.0
    for pts, ow in zip(tris_pts, outward_fn):
        (ax, ay, az), (bx2, by2, bz2), (cx2, cy2, cz2) = pts
        nx3 = (by2 - ay) * (cz2 - az) - (bz2 - az) * (cy2 - ay)
        nz3 = (bx2 - ax) * (cy2 - ay) - (by2 - ay) * (cx2 - ax)
        sc += nx3 * ow[0] + nz3 * ow[1]
    return sc

_d_tris, _d_out = [], []
for t in dcomp[::3]:
    i = dtri[t]
    _d_tris.append([dV[i[0]], dV[i[1]], dV[i[2]]])
    s, dd, h, th_d = dpar[kk3(dV[i[0]])]
    _d_out.append((-math.sin(th_d), math.cos(th_d)))       # the donor's +d (downhill) dir
_o_tris, _o_out = [], []
for (kind, lap, keys, i) in wall_src[::3]:
    if kind != "w":
        continue
    _o_tris.append([place_vert(lap, p, j)[:3] for p, j in zip(keys, i)])
    s, dd, h, _ = dpar[keys[0]]
    _, _, _, oNx, oNz, _, _ = anchor_at(lap * (L_EFF - LAP_OV) + (s - S_LO))
    _o_out.append((oNx, oNz))
FLIP = (_facing_score(_o_tris, _o_out) > 0) != (_facing_score(_d_tris, _d_out) > 0)
print(f"facing check: {'MIRRORED -- flipping carried winding' if FLIP else 'faithful'}",
      flush=True)

new_parents = build_wall_parents()
print(f"carried wall tris: {len(new_parents)} ({n_laps} laps)", flush=True)

def poly_nearest(px, pz, poly):
    best, q = 1e18, (px, pz)
    n = len(poly)
    for i in range(n):
        ax, az = poly[i]
        bx2, bz2 = poly[(i + 1) % n]
        vx, vz = bx2 - ax, bz2 - az
        L2 = (vx * vx + vz * vz) or 1e-9
        t01 = max(0.0, min(1.0, ((px - ax) * vx + (pz - az) * vz) / L2))
        qx, qz = ax + t01 * vx, az + t01 * vz
        d2 = (px - qx) ** 2 + (pz - qz) ** 2
        if d2 < best:
            best, q = d2, (qx, qz)
    return math.sqrt(best), q

# THE RULE-(f) SCAN, parent-level (pre-assembly): a NEW blocked WALL tri strictly below a
# walkable surface. Used both as the FIX ORACLE (nudge offenders outward until clean) and
# as the final gate.
WALKT = {0, 1, 2, 3, 10, 11, 12, 13, 37, 42}
def ruleF_scan(report=False):
    entries = []
    for i2, t in enumerate(gtris):
        if i2 in drop:
            continue
        _, idall, fam, _ = gmeta[i2]
        lift = north[i2] and fam != "rock"
        tp = 13 if lift else X.decode_id(int(round(idall)))["topograph"]
        p3 = [(gpos[j][0], gpos[j][1] + (RAISE if lift else 0.0), gpos[j][2]) for j in t]
        entries.append((p3, tp, "raised" if lift else f"kept-{fam}", -1))
    for m, (corners, idall, fam) in enumerate(new_parents):
        tp = X.decode_id(int(round(idall)))["topograph"]
        entries.append(([p[:3] for p in corners], tp, fam, m))
    bkt = defaultdict(list)
    for si, (p3, tp, src2, m) in enumerate(entries):
        xs3 = [p[0] for p in p3]
        zs3 = [p[2] for p in p3]
        for bx3 in range(int(min(xs3) // 4), int(max(xs3) // 4) + 1):
            for bz3 in range(int(min(zs3) // 4), int(max(zs3) // 4) + 1):
                bkt[(bx3, bz3)].append(si)
    offend = {}
    nviol = 0
    for wx in np.arange(CX - 30, CX + 30.01, 0.75):
        for wz in np.arange(CZ - CLEAR_OUT - 8, CZ + 16.01, 0.75):
            hs = []
            for si in bkt.get((int(wx // 4), int(wz // 4)), ()):
                p3, tp, src2, m = entries[si]
                (ax, ay, az), (bx2, by2, bz2), (cx2, cy2, cz2) = p3
                det = (bz2 - cz2) * (ax - cx2) + (cx2 - bx2) * (az - cz2)
                if abs(det) < 1e-12:
                    continue
                w0 = ((bz2 - cz2) * (wx - cx2) + (cx2 - bx2) * (wz - cz2)) / det
                w1 = ((cz2 - az) * (wx - cx2) + (ax - cx2) * (wz - cz2)) / det
                w2 = 1 - w0 - w1
                if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
                    continue
                hs.append((w0 * ay + w1 * by2 + w2 * cy2, tp, src2, m))
            wk = [h for h in hs if h[1] in WALKT]
            if not wk:
                continue
            topw = max(wk, key=lambda h: h[0])
            for h in hs:
                if h[1] in WALKT:
                    continue
                if h[0] < topw[0] - 0.05 and h[2] in ("wall", "wall-foot"):
                    nviol += 1
                    dep, _ = poly_nearest(wx, wz, crest_poly)
                    if not pip(wx, wz, crest_poly):
                        dep = 0.4
                    offend[h[3]] = max(offend.get(h[3], 0.0), dep)
                    if report and nviol <= 6:
                        print(f"  ruleF: ({wx:.1f},{wz:.1f}) wall y={h[0]:.2f} under "
                              f"{topw[2]} y={topw[0]:.2f}", flush=True)
                    break
    return nviol, offend

for _fix in range(5):
    nviol, offend = ruleF_scan()
    if not nviol:
        break
    if _fix < 2:
        for m, dep in offend.items():
            if m >= len(parent_src_idx):
                continue
            kind, lap, keys, _ = wall_src[parent_src_idx[m]]
            for p in keys:
                vshift[(kind, lap, p)] = max(vshift.get((kind, lap, p), 0.0), dep + 0.5)
        print(f"  rule-f fix pass {_fix}: {nviol} points, {len(offend)} tris' verts "
              f"shifted", flush=True)
    else:
        # non-convergent offenders (corner tris stretch under divergent normals instead
        # of translating): GHOST them -- idall 4078 renders but no ray ever hits it, so
        # it cannot be cached; no hole, no trap
        ghost_src.update(parent_src_idx[m] for m in offend if m < len(parent_src_idx))
        print(f"  rule-f fix pass {_fix}: ghosted {len(offend)} non-convergent corner "
              f"tris", flush=True)
    new_parents = build_wall_parents()                     # shared verts move TOGETHER

# LAND CLIP: feet weld by CUT -- clip wall tris at ground level where over land; the clip
# edge (y == GROUND_Y) is the contact line the zip welds to. Sea side keeps free bases.
def clip_poly(poly, axis, val, keep_ge):
    out2 = []
    for ii in range(len(poly)):
        a2, b2 = poly[ii], poly[(ii + 1) % len(poly)]
        da = (a2[axis] - val) if keep_ge else (val - a2[axis])
        db = (b2[axis] - val) if keep_ge else (val - b2[axis])
        if da >= 0:
            out2.append(a2)
        if (da >= 0) != (db >= 0):
            t01 = da / (da - db)
            out2.append(tuple(a2[k2] + t01 * (b2[k2] - a2[k2]) for k2 in range(len(a2))))
    return out2

clipped, clip_edge = [], []
for corners, idall, fam in new_parents:
    if fam != "wall" or all(p[1] >= GROUND_Y for p in corners):
        clipped.append((corners, idall, fam))
        continue
    # clip iff the BELOW-GROUND part is over land (border tris keep sea-side free bases)
    below = clip_poly(list(corners), 1, GROUND_Y, False)
    if len(below) < 3:
        clipped.append((corners, idall, fam))
        continue
    bxm = sum(p[0] for p in below) / len(below)
    bzm = sum(p[2] for p in below) / len(below)
    if not pip(bxm, bzm, outline_poly) and             not any(pip(p[0], p[2], outline_poly) for p in below):
        clipped.append((corners, idall, fam))              # fully-sea below-part: free base
        continue
    poly = clip_poly(list(corners), 1, GROUND_Y, True)
    if len(poly) < 3:
        continue
    for p in poly:
        if abs(p[1] - GROUND_Y) < 1e-6:
            clip_edge.append(p)
    for k2 in range(1, len(poly) - 1):
        tri = (poly[0], poly[k2], poly[k2 + 1])
        e1 = [tri[1][q] - tri[0][q] for q in range(3)]
        e2 = [tri[2][q] - tri[0][q] for q in range(3)]
        cx_ = e1[1] * e2[2] - e1[2] * e2[1]
        cy_ = e1[2] * e2[0] - e1[0] * e2[2]
        cz_ = e1[0] * e2[1] - e1[1] * e2[0]
        if cx_ * cx_ + cy_ * cy_ + cz_ * cz_ < 1e-12:
            continue
        clipped.append((tri, idall, fam))
new_parents = clipped
# the corridor welds to THE FOOT STRIP's ground verts (the real donor foot line), not the
# mid-body clip edge
contact = []
for corners, idall, fam in new_parents:
    if fam == "wall-foot":
        for p in corners:
            if abs(p[1] - GROUND_Y) <= 0.35:
                contact.append(p)
contact.extend(clip_edge)                                  # fallback anchors where the
#   strip is absent -- without them the zip cuts straight across and leaves holes
contact = [p for p in contact if p[2] < seg_chord_z(p[0]) + 1.5]   # the corridor is the
#   chord side; mouth-side feet pollute the arc ordering (the swooping zip)
print(f"wall tris after the land clip: {sum(1 for _, _, f in new_parents if f == 'wall')} "
      f"+ {sum(1 for _, _, f in new_parents if f == 'wall-foot')} foot, "
      f"contact pts {len(contact)}", flush=True)

# ---- 7. the corridor zip: south chain <-> the contact line -------------------------------------
def ring_param(px, pz):
    best, bd = 0.0, 1e18
    for i in range(NR):
        ax, az = R[i][0], R[i][2]
        bx, bz = R[(i + 1) % NR][0], R[(i + 1) % NR][2]
        vx, vz = bx - ax, bz - az
        L2 = (vx * vx + vz * vz) or 1e-9
        t01 = max(0.0, min(1.0, ((px - ax) * vx + (pz - az) * vz) / L2))
        d2 = (px - (ax + t01 * vx)) ** 2 + (pz - (az + t01 * vz)) ** 2
        if d2 < bd:
            bd, best = d2, cumR[i] + t01 * (cumR[i + 1] - cumR[i])
    return best

# contact -> ordered land arc: EVERY unique contact vert (the zip welds vertex-exact to
# the clip edge -- binning left slivers), ordered by ring param; keep inland >= 2.0
cuniq = {}
for p in contact:
    # INSIDE the outline and >=2u from it (unsigned distance passed sea-side clip verts!)
    if not pip(p[0], p[2], outline_poly) or dist_to_poly(p[0], p[2], outline_poly) < 2.0:
        continue
    k2 = kk3(p)
    if k2 not in cuniq:
        cuniq[k2] = (ring_param(p[0], p[2]), p)
csorted = sorted(cuniq.values(), key=lambda e: e[0])
assert len(csorted) >= 4, "no usable contact line"
# the contact points live on the chord side only; find the wrap gap and unroll
gaps = [(csorted[(i + 1) % len(csorted)][0] - csorted[i][0]) % PER for i in range(len(csorted))]
cut = max(range(len(csorted)), key=lambda i: gaps[i])
order = csorted[cut + 1:] + csorted[:cut + 1]
land_arc = [(e[1][0], GROUND_Y, e[1][2]) for e in order]
sc = list(south_chain)
if (((sc[0][0] - land_arc[0][0]) ** 2 + (sc[0][2] - land_arc[0][2]) ** 2) +
        ((sc[-1][0] - land_arc[-1][0]) ** 2 + (sc[-1][2] - land_arc[-1][2]) ** 2) >
        ((sc[0][0] - land_arc[-1][0]) ** 2 + (sc[0][2] - land_arc[-1][2]) ** 2) +
        ((sc[-1][0] - land_arc[0][0]) ** 2 + (sc[-1][2] - land_arc[0][2]) ** 2)):
    land_arc = land_arc[::-1]

def cum_arc(ch):
    c = [0.0]
    for a2, b2 in zip(ch, ch[1:]):
        c.append(c[-1] + math.hypot(b2[0] - a2[0], b2[2] - a2[2]))
    return c

cs, cl = cum_arc(sc), cum_arc(land_arc)
ps = [d / max(1e-9, cs[-1]) for d in cs]
pl = [d / max(1e-9, cl[-1]) for d in cl]
zip_tris = []
i = j = 0
while i < len(sc) - 1 or j < len(land_arc) - 1:
    can_i = i < len(sc) - 1
    can_j = j < len(land_arc) - 1
    if can_i and (not can_j or ps[i + 1] <= pl[j + 1]):
        zip_tris.append((sc[i], sc[i + 1], land_arc[j]))
        i += 1
    else:
        zip_tris.append((sc[i], land_arc[j + 1], land_arc[j]))
        j += 1
print(f"lowland zip: {len(zip_tris)} tris over {len(land_arc)} contact pts", flush=True)

# zip mains: cell-clip + byte-decode (the proven v2 machinery)
cell_of = lambda x, z: (int(np.floor(x / 4.0)), int(np.floor(z / 4.0)))
kept_by_cell = defaultdict(list)
for i2, t in enumerate(gtris):
    if i2 in drop or tri_fam[i2] != "main" or north[i2]:
        continue
    kept_by_cell[cell_of(tri_cx[i2], tri_cz[i2])].append(i2)
QUADS = [(u, v) for u in (0, 1) for v in (0, 1)]
ORIS = (0, 90, 180, 270)
_dec = {}
def decode_cell(cell):
    if cell in _dec:
        return _dec[cell]
    best = None
    for tdx in kept_by_cell.get(cell, []):
        t = gtris[tdx]
        uvv = gmeta[tdx][3]
        for q in QUADS:
            for o in ORIS:
                err = 0.0
                for jj, (u, v) in zip(t, uvv):
                    mu, mv = G.mains_uv(gpos[jj][0], gpos[jj][2], cell, q, o)
                    err = max(err, abs(mu - u), abs(mv - v))
                if err < 1e-4:
                    best = (q, o)
                    break
            if best:
                break
        if best:
            break
    if best is None:
        import random as _r
        ii, jj = cell
        rr = _r.Random((ii * 73856093) ^ (jj * 19349663) ^ 0xF95)
        best = (QUADS[rr.randrange(4)], ORIS[rr.randrange(4)])
    _dec[cell] = best
    return best

pos_nrm = {}
for i2, t in enumerate(gtris):
    if i2 in drop:
        continue
    for jj in t:
        pos_nrm.setdefault(kk3(gpos[jj]), list(gnrm[jj]))

def clip_decode_emit(tri_list, idall, fam, dec_fn, verge=False):
    """cell-clip raw grass tris, byte-decode each piece's OWN cell, emit; the VERGE RULE
    (a piece within candidate reach of the outline emits BLOCKED -- same grass texture,
    census stays covered, the cache-shadow trap can't arm) applies when verge=True"""
    pieces = []
    for tri3 in tri_list:
        corners6 = []
        for pnt in tri3:
            n3 = pos_nrm.get(kk3(pnt), [0.0, 1.0, 0.0])
            corners6.append((float(pnt[0]), float(pnt[1]), float(pnt[2]), *n3))
        xs2 = [c[0] for c in corners6]
        zs2 = [c[2] for c in corners6]
        cx0, cx1 = int(np.floor(min(xs2) / 4.0)), int(np.floor((max(xs2) - 1e-9) / 4.0))
        cz0, cz1 = int(np.floor(min(zs2) / 4.0)), int(np.floor((max(zs2) - 1e-9) / 4.0))
        for ci in range(cx0, cx1 + 1):
            for cj in range(cz0, cz1 + 1):
                p = list(corners6)
                p = clip_poly(p, 0, ci * 4.0, True)
                if len(p) >= 3:
                    p = clip_poly(p, 0, (ci + 1) * 4.0, False)
                if len(p) >= 3:
                    p = clip_poly(p, 2, cj * 4.0, True)
                if len(p) >= 3:
                    p = clip_poly(p, 2, (cj + 1) * 4.0, False)
                if len(p) < 3:
                    continue
                for k2 in range(1, len(p) - 1):
                    tri = (p[0], p[k2], p[k2 + 1])
                    e1 = [tri[1][q] - tri[0][q] for q in range(3)]
                    e2 = [tri[2][q] - tri[0][q] for q in range(3)]
                    cxp = e1[1] * e2[2] - e1[2] * e2[1]
                    cyp = e1[2] * e2[0] - e1[0] * e2[2]
                    czp = e1[0] * e2[1] - e1[1] * e2[0]
                    if cxp * cxp + cyp * cyp + czp * czp < 1e-12:
                        continue
                    pieces.append(((ci, cj), tri))
    nv = 0
    for cell, tri in pieces:
        a, b, c = (np.asarray(p[:3], dtype=float) for p in tri)
        nrm = np.cross(b - a, c - a)
        order2 = tri if nrm[1] > 0 else (tri[0], tri[2], tri[1])
        q, o = dec_fn(cell)
        corners = []
        for pnt in order2:
            u, v = G.mains_uv(float(pnt[0]), float(pnt[2]), cell, q, o)
            corners.append((float(pnt[0]), float(pnt[1]), float(pnt[2]), u, v,
                            pnt[3], pnt[4], pnt[5]))
        if verge and any(not pip(p[0], p[2], outline_poly) or
                         dist_to_poly(p[0], p[2], outline_poly) < 2.0 for p in order2):
            new_parents.append((tuple(corners), ID49, "verge"))
            nv += 1
        else:
            new_parents.append((tuple(corners), idall, fam))
    return len(pieces), nv

npieces, n_verge = clip_decode_emit(zip_tris, ID0, "zip", decode_cell, verge=True)
print(f"zip pieces after the cell clip: {npieces} ({n_verge} verge-blocked at the "
      f"coverage edge)", flush=True)

# the hull-closure FILLS: raised grass, decoded from ANY kept main (north cells included)
kept_by_cell_all = defaultdict(list)
for i2, t in enumerate(gtris):
    if i2 in drop or tri_fam[i2] != "main":
        continue
    kept_by_cell_all[cell_of(tri_cx[i2], tri_cz[i2])].append(i2)
_dec_all = {}
def decode_cell_all(cell):
    if cell in _dec_all:
        return _dec_all[cell]
    best = None
    for tdx in kept_by_cell_all.get(cell, []):
        t = gtris[tdx]
        uvv = gmeta[tdx][3]
        for q in QUADS:
            for o in ORIS:
                err = 0.0
                for jj, (u, v) in zip(t, uvv):
                    mu, mv = G.mains_uv(gpos[jj][0], gpos[jj][2], cell, q, o)
                    err = max(err, abs(mu - u), abs(mv - v))
                if err < 1e-4:
                    best = (q, o)
                    break
            if best:
                break
        if best:
            break
    if best is None:
        import random as _r
        ii, jj = cell
        rr = _r.Random((ii * 73856093) ^ (jj * 19349663) ^ 0xF95)
        best = (QUADS[rr.randrange(4)], ORIS[rr.randrange(4)])
    _dec_all[cell] = best
    return best

nfp, _ = clip_decode_emit(fill_raw, ID13, "fill", decode_cell_all)
print(f"bay-fill pieces: {nfp}", flush=True)

# ---- 8. assemble --------------------------------------------------------------------------------
pos, nrm2, uv2, tan2, flat, tris2, tri_src = [], [], [], [], [], [], []
bx, by = BLK
def emit(p3, u_, n_, idall):
    pos.append([p3[0] - BLOCK * bx, p3[1], p3[2] + BLOCK * (by + 1) - BLOCK])
    uv2.append(list(u_)); nrm2.append(list(n_)); tan2.append([idall, 0.0, 0.0, 1.0])
    flat.append(len(pos) - 1)
for i2, t in enumerate(gtris):
    if i2 in drop:
        continue
    _, idall, fam, uvv = gmeta[i2]
    lift = north[i2] and fam != "rock"
    for jj, (u, v) in zip(t, uvv):
        w = gpos[jj]
        emit([w[0], w[1] + (RAISE if lift else 0.0), w[2]], (u, v), gnrm[jj],
             ID13 if lift else idall)
    tris2.append([flat[-3], flat[-2], flat[-1]])
    tri_src.append("raised" if lift else f"kept-{fam}")
for corners, idall, fam in new_parents:
    for p in corners:
        emit(p[:3], (p[3], p[4]), (p[5], p[6], p[7]), idall)
    tris2.append([flat[-3], flat[-2], flat[-1]])
    tri_src.append(fam)
new_bm = X.BlockMesh(name=built["blocks"][BLK].name, disc=1, x=bx, y=by, lod="0_1",
                     vcount=len(pos), stride=48,
                     channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
                     chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm2, X.CH_UV: uv2, X.CH_TAN: tan2},
                     flat_index=flat, tris=tris2, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])

# ---- 9. gates -----------------------------------------------------------------------------------
down = 0
for corners, _, f in new_parents:
    if f != "zip":
        continue
    a, b, c = (np.asarray(p[:3]) for p in corners)
    if np.cross(b - a, c - a)[1] < 0:
        down += 1
import dataclasses
plane = M.fill_missing_grid_quads(X.read_block(12, 0, disc=1, part="sea4"))
hid = lambda nm_: M.hidden_block_mesh(name=nm_, disc=1, x=bx, y=by)  # noqa: E731
sea = dataclasses.replace(plane, x=bx, y=by, name=f"Block[{bx}][{by}] Sea4")
meshlist = [("Object", hid("Object")), ("Terrain", new_bm), ("Sea1", hid("Sea1")),
            ("Sea2", hid("Sea2")), ("Sea3", hid("Sea3")), ("Sea4", sea), ("Sea5", hid("Sea5"))]
cen = P.census(meshlist)
walk_zip = [c for c, _, f in new_parents if f == "zip"]
zmoat = min(p[1] for c in walk_zip for p in c)
zinl = min((dist_to_poly(p[0], p[2], outline_poly) if pip(p[0], p[2], outline_poly)
            else -dist_to_poly(p[0], p[2], outline_poly))
           for c in walk_zip for p in c)                   # SIGNED: negative = over sea

# THE RULE-(f) GATE: no NEW blocked tri under (or coplanar with) a walkable surface, and no
# walkable NEW tri with any blocked tri beneath -- scanned on a 0.75u grid over the strip band
WALKT = {0, 1, 2, 3, 10, 11, 12, 13, 37, 42}
viol, _ = ruleF_scan(report=True)
print(f"GATES: zipDown={down} censusMISS={len(cen['miss'])} zipMinY={zmoat:.2f} "
      f"zipInland={zinl:.1f} ruleF={viol}", flush=True)
assert down == 0 and len(cen["miss"]) == 0
assert zmoat >= 2.4 and zinl >= 1.8, "THE MOAT LAW: walkable zip within candidate reach " \
    "of the outline"
assert viol == 0, f"RULE (f): {viol} blocked-under/at-walkable points involving NEW geometry"
lx, lz = CX - BLOCK * bx, CZ + BLOCK * (by + 1) - BLOCK
gy, nm_, _, topo2 = P.place(meshlist, lx - 1.5, lz + 13.5)
print(f"plateau probe ({CX - 1.5:.1f},{CZ + 13.5:.1f}): y={gy:.2f} {nm_} topo {topo2}", flush=True)
gy2, nm2_, _, topo3 = P.place(meshlist, lx + 2.5, lz - 17.5)
print(f"lowland probe ({CX + 2.5:.1f},{CZ - 17.5:.1f}): y={gy2:.2f} {nm2_} topo {topo3}", flush=True)
assert topo2 == 13 and abs(gy - PLATEAU_Y) < 1.6
assert topo3 == 0 and gy2 < 5

# ---- 10. render ---------------------------------------------------------------------------------
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
    for (dx2, dy2, wgt) in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                            (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        px_, py_ = min(max(x0 + dx2, 0), W_ - 1), min(max(y0 + dy2, 0), H_ - 1)
        r, gg, b, a = PX[px_, py_]
        acc_[0] += r * wgt; acc_[1] += gg * wgt; acc_[2] += b * wgt; aa += a * wgt
    return aa, (int(acc_[0]), int(acc_[1]), int(acc_[2]))
SC = 16
lo_x = min(v[0] for v in pos) + BLOCK * bx - 2
hi_x = max(v[0] for v in pos) + BLOCK * bx + 2
lo_z = min(v[2] for v in pos) - BLOCK * (by + 1) + BLOCK - 2
hi_z = max(v[2] for v in pos) - BLOCK * (by + 1) + BLOCK + 2
RW, RH = int((hi_x - lo_x) * SC) + 2, int((hi_z - lo_z) * SC) + 2
out = Image.new("RGB", (RW, RH), (24, 40, 72))
op = out.load()
LDIR = (-0.45, 0.8, -0.35)
_l = math.sqrt(sum(q * q for q in LDIR)); LDIR = tuple(q / _l for q in LDIR)
DBG = bool(os.environ.get("DEBUG_CLASS"))
CLASS_RGB = {"raised": (60, 220, 60), "kept-main": (20, 120, 20), "kept-rock": (150, 110, 70),
             "kept-forest": (0, 80, 0), "kept-stamp": (120, 200, 120),
             "wall": (150, 150, 160), "zip": (240, 220, 40), "verge": (170, 140, 30),
             "fill": (110, 235, 110), "wall-foot": (110, 100, 120)}
order_rows = sorted(range(len(tris2)), key=lambda t: min(pos[i][1] for i in tris2[t]))
for t in order_rows:
    p3 = [(pos[i][0] + BLOCK * bx, pos[i][1], pos[i][2] - BLOCK * (by + 1) + BLOCK) for i in tris2[t]]
    q3 = [uv2[i] for i in tris2[t]]
    n3 = [nrm2[i] for i in tris2[t]]
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
            if DBG:
                aa, rgb = 255.0, CLASS_RGB.get(tri_src[t], (255, 0, 255))
            else:
                aa, rgb = at_b(w0 * q3[0][0] + w1 * q3[1][0] + w2 * q3[2][0],
                               w0 * q3[0][1] + w1 * q3[1][1] + w2 * q3[2][1])
            nx = sum(w * n3[k2][0] for k2, w in enumerate((w0, w1, w2)))
            ny = sum(w * n3[k2][1] for k2, w in enumerate((w0, w1, w2)))
            nz = sum(w * n3[k2][2] for k2, w in enumerate((w0, w1, w2)))
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            f = 0.55 + 0.45 * max(0.0, (nx * LDIR[0] + ny * LDIR[1] + nz * LDIR[2]) / nl)
            op[pyx, RH - 1 - pyz] = (255, 255, 255) if aa < 24 else \
                tuple(min(255, int(cc * f)) for cc in rgb[:3])
OUT_RENDER.parent.mkdir(exist_ok=True)
out.save(OUT_RENDER)
print(f"render -> {OUT_RENDER}", flush=True)

# ---- 11. deploy ---------------------------------------------------------------------------------
if len(sys.argv) > 1 and sys.argv[1] == "deploy":
    assert pristine, "deployed island F is not pristine -- re-run the world-island mint first"
    BK.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(src, BK / f"{src.name}.{ts}")
    outp = M.deploy_override(new_bm, mod_folder="FF9CustomMap-world", part="Terrain")
    print(f"deployed -> {outp} ({len(new_bm.tris)} tris)")
    print(f"DONE -- world re-entry; teleport {CX + 2.5:.1f},{CZ - 17.5:.1f} = the lowland; "
          f"{CX - 1.5:.1f},{CZ + 13.5:.1f} = the plateau top.")
else:
    print("dry run only -- re-run with 'deploy' to write.")
