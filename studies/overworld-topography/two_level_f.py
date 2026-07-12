"""RUNG D v3 -- THE TWO-LEVEL ISLAND: island F rebuilt as lowland south + plateau north,
joined by a synthesized escarpment in the decoded interior-wall language.

Why this shape: the mesa search proved FF9 HAS NO FREE-STANDING MESA -- flat terraces
exist only as EDGES of larger highland (escarpments, riverbanks). A two-level island IS
that shape: the plateau is an edge-bounded half, not a floating cone, so the CONE-PERIMETER
TRAP vanishes (a straight-ish chord wall has ~equal course lengths -> clean 4.4u quads,
sparse fans only on the curved coast arc).

The composition (every piece a measured law):
* the CHORD WALL: 3 courses at the real 58-deg slope, single band descent (crest row 4 ->
  band B rows 9 -> 10; mixing bands = the round-1 bright stripe), one byte-read 128px tile
  per ~4.4u interval, corner-assignment fans at count changes;
* the PLATEAU: island F's own north grass raised +13.7 to shelf height ~17 (topo flipped
  0 -> 13, the real class at that altitude -- same grass tiles per the look-family law);
  the raised coastal rim verts BECOME the wall's crest ring on the sea side (weld by
  identity);
* the SEA CLIFF: on the north coast the wall courses descend past the waterline and
  terminate FREE (THE FREE-BASE LAW: zero 49 base edges land on walkable terrain; bases
  end at/below the waterline) -- no foot weld needed over the sea; the island's own
  coastal wall band + foam-height outline are DROPPED along that arc (replaced);
* the LOWLAND WELD: the chord side's foot conforms to ground and zips to the south grass
  with the proven carve machinery (byte-decoded per-cell zip mains).

Unreachable on foot BY DESIGN (topo 49 blocks; the NO-FOOT-PASS law).

Usage:  py studies/overworld-topography/two_level_f.py [deploy]
        (deploy expects the PRISTINE island F on disk -- re-run the world-island mint first)
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
from ff9mapkit.world.island import build_landmass

GP = Path(_cfg.find_game_path(None))
MODW = GP / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
BK = Path(__file__).resolve().parents[2] / "backups"
OUT_RENDER = Path(__file__).with_name("out") / "island_f_twolevel_render.png"
BLK = (3, 17)
BLOCK = 64.0
CX, CZ = 224.0, -1120.0

PLATEAU_Y = 17.0                                           # the shelf class (15.7-18.3)
Z_CHORD = -1116.0                                          # plateau = z > chord (north)
WALL_SLOPE = 58.0
COURSES = [(4, (4, 5, 6, 7)), (9, (6, 7, 8, 9)), (10, (6, 7, 8, 9))]
DROPS = [4.6, 4.6, 4.6]
TILE_SPACING = 4.4
CLEAR = 2.5
SEA_BASE_Y = -0.8                                          # free base below the waterline
kk3 = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

TILE_U, TILE_V = 0.0625, 0.03125
_rt = json.loads((Path(__file__).with_name("out") / "rock_tiles.json").read_text())
PU, PV = _rt["phase"]
_cnt = defaultdict(Counter)
for g in _rt["groups"]:
    col = int(round((g["u0"] - PU) / TILE_U))
    row = int(round((g["v0"] - PV) / TILE_V))
    _cnt[(col, row)][(round(g["u0"], 5), round(g["v0"], 5), round(g["du"], 5), round(g["dv"], 5))] += 1
TILE_RECT = {tid: c.most_common(1)[0][0] for tid, c in _cnt.items()}

# ---- 1. island F: deterministic rebuild == deployed bytes ------------------------------------
built = build_landmass(center=(CX, CZ), base_radius=26, seed=15, lobes=1, n_patches=0,
                       relief="auto", stamps="auto")
assert set(built["blocks"]) == {BLK}
import tempfile
_tmp = Path(tempfile.mkdtemp(prefix="ff9_twolevel_"))
ref = M.write_ff9mesh(built["blocks"][BLK], _tmp / "ref.ff9mesh").read_bytes()
src = MODW / f"r{BLK[1]}" / f"Block[{BLK[0]}][{BLK[1]}] Terrain.ff9mesh"
pristine = src.read_bytes() == ref
print(f"deployed island F pristine: {pristine}", flush=True)

gpos = built["world"]["pos"]
gtris = built["world"]["tris"]
gmeta = built["world"]["meta"]                             # (blk, idall, fam, uvv)
gnrm = built["world"]["nrm"]
outline = built["outline"]                                 # [(x, z)] the y=0 coast ring
rim = built["rim"]                                         # [(x, z)] the grass/wall weld ring
print(f"island F rebuild: {len(gtris)} tris, outline {len(outline)} pts", flush=True)

def seg_chord_z(x):
    return Z_CHORD + 1.6 * math.sin(0.11 * x)              # the gently-curved chord line

def north_of_chord(x, z):
    return z > seg_chord_z(x)

# ---- 2. classify + partition the island ------------------------------------------------------
# tri classes: 'rock' (the coastal wall band), 'grass'; north/south by centroid
tri_cx = np.array([sum(gpos[i][0] for i in t) / 3 for t in gtris])
tri_cz = np.array([sum(gpos[i][2] for i in t) / 3 for t in gtris])
tri_fam = [gmeta[i][2] for i in range(len(gtris))]
north = np.array([north_of_chord(tri_cx[i], tri_cz[i]) for i in range(len(gtris))])

# the chord CLEAR strip through the grass (the wall + zip will replace it)
def near_chord(x, z, d):
    return abs(z - seg_chord_z(x)) < d

drop = set()
for i, t in enumerate(gtris):
    if tri_fam[i] == "rock":
        if north[i]:
            drop.add(i)                                    # the north coastal wall band: replaced
        continue
    if any(near_chord(gpos[j][0], gpos[j][2], CLEAR) for j in t):
        drop.add(i)
fams = Counter(tri_fam[i] for i in drop)
print(f"dropped: {len(drop)} tris ({dict(fams)})", flush=True)

# hole ring on the SOUTH side of the chord strip (for the lowland zip): kept-south once-edges
# that were shared with dropped tris
eu = Counter()
for i, t in enumerate(gtris):
    if i in drop:
        continue
    for a, b in ((0, 1), (1, 2), (2, 0)):
        eu[tuple(sorted((kk3(gpos[t[a]]), kk3(gpos[t[b]]))))] += 1
dropped_edges = set()
for i in drop:
    t = gtris[i]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        dropped_edges.add(tuple(sorted((kk3(gpos[t[a]]), kk3(gpos[t[b]])))))
once = [e for e, n in eu.items() if n == 1 and e in dropped_edges]
south_chain_e = [e for e in once if not north_of_chord((e[0][0] + e[1][0]) / 2,
                                                       (e[0][2] + e[1][2]) / 2)]
north_chain_e = [e for e in once if north_of_chord((e[0][0] + e[1][0]) / 2,
                                                   (e[0][2] + e[1][2]) / 2)]

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

south_chain = chain_open(south_chain_e, "south hole chain")

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
    return ring

# the kept-north region's boundary is a CLOSED ring (chord edge + the rim arc where the
# coast band dropped) -- it IS the crest loop
north_ring = chain_closed(north_chain_e, "north boundary ring")
print(f"chord chains: south {len(south_chain)} pts, north ring {len(north_ring)} pts", flush=True)

# ---- 3. the raised plateau ---------------------------------------------------------------------
RAISE = PLATEAU_Y - 3.2
ID13 = float(X.encode_id(topograph=13))
raised_keys = {}
for i, t in enumerate(gtris):
    if i in drop or not north[i] or tri_fam[i] == "rock":
        continue
    for j in t:
        raised_keys[kk3(gpos[j])] = True
for i in range(len(gpos)):
    k = kk3(gpos[i])
    if k in raised_keys:
        pass                                               # marker only; the raise happens at emit
def raise_y(p):
    return [p[0], p[1] + RAISE, p[2]]

# crest ring = the north boundary ring RAISED (exact kept floats + RAISE -- welds to the
# raised plateau by identity); is_chord per vert steers the course offset direction
crest = [(p[0], p[1] + RAISE, p[2]) for p in north_ring]
crest_is_chord = [near_chord(p[0], p[2], CLEAR + 3.5) for p in north_ring]
print(f"crest loop: {len(crest)} pts ({sum(crest_is_chord)} chord-side)", flush=True)

# ---- 4. the wall course rings -----------------------------------------------------------------
# offset DIRECTION per crest vert: chord side = southward (-chord normal); coast side =
# radially outward from the island centre
def offset_dir(x, z, isch):
    if isch:
        dzdx = 1.6 * 0.11 * math.cos(0.11 * x)
        nx, nz = dzdx, -1.0                                # normal pointing SOUTH of the chord
        L = math.hypot(nx, nz)
        return nx / L, nz / L
    dx, dz = x - CX, z - CZ
    L = math.hypot(dx, dz) or 1.0
    return dx / L, dz / L

run = 4.6 / math.tan(math.radians(WALL_SLOPE))
ring_polys = [[(p[0], p[2]) for p in crest]]
for k in range(1, len(COURSES) + 1):
    poly = []
    for (x, y, z), isch in zip(crest, crest_is_chord):
        ox, oz = offset_dir(x, z, isch)
        poly.append((x + ox * run * k, z + oz * run * k))
    ring_polys.append(poly)

def resample_ring(poly_pts, spacing=TILE_SPACING):
    n = len(poly_pts)
    cum = [0.0]
    for i in range(1, n + 1):
        a, b = poly_pts[i - 1], poly_pts[i % n]
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    per = cum[-1]
    m = max(8, int(round(per / spacing)))
    out = []
    for s in range(m):
        d = per * s / m
        i = max(0, int(np.searchsorted(cum, d)) - 1)
        t01 = (d - cum[i]) / max(1e-9, cum[i + 1] - cum[i])
        a, b = poly_pts[i % n], poly_pts[(i + 1) % n]
        out.append((a[0] + t01 * (b[0] - a[0]), a[1] + t01 * (b[1] - a[1])))
    return out

# ring 0 = the crest verts VERBATIM (welds to the plateau by identity); rings 1..3 resampled
rings = [crest]
for k in range(1, len(COURSES) + 1):
    rings.append([(x, None, z) for (x, z) in resample_ring(ring_polys[k])])

# classify ring verts land/sea + assign y: over land -> course height (foot conforms to
# ground); over sea -> course height capped, foot at SEA_BASE_Y
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
south_ground = {}                                          # nearest south-chain ground y
def nearest_south_y(px, pz):
    return min(south_chain, key=lambda h: (h[0] - px) ** 2 + (h[2] - pz) ** 2)[1]

for k in range(1, len(COURSES) + 1):
    yk = PLATEAU_Y - sum(DROPS[:k])
    newring = []
    for (x, _, z) in rings[k]:
        over_land = pip(x, z, outline_poly)
        if k < len(COURSES):
            y = max(yk, SEA_BASE_Y)
        else:
            y = nearest_south_y(x, z) if over_land else SEA_BASE_Y
        newring.append((x, y, z))
    rings[k] = newring
for k in range(len(rings)):
    print(f"  ring {k}: {len(rings[k])} verts", flush=True)

# ---- 5. emit ----------------------------------------------------------------------------------
ID49 = float(X.encode_id(topograph=49))
ID0 = float(X.encode_id(topograph=0))
new_parents = []

def d2xz(p, q):
    return (p[0] - q[0]) ** 2 + (p[2] - q[2]) ** 2

for k, (row, cols) in enumerate(COURSES):
    T = rings[k]
    B = rings[k + 1]
    NT, NB = len(T), len(B)
    b0 = min(range(NB), key=lambda j: d2xz(B[j], T[0]))
    Br = B[b0:] + B[:b0]
    # orientation: both rings built from the same loop direction; verify by signed area
    def sa(ring):
        s = 0.0
        for i in range(len(ring)):
            x1, z1 = ring[i][0], ring[i][2]
            x2, z2 = ring[(i + 1) % len(ring)][0], ring[(i + 1) % len(ring)][2]
            s += x1 * z2 - x2 * z1
        return s / 2
    if sa(T) * sa(Br) < 0:
        Br = Br[::-1]
        b0 = min(range(NB), key=lambda j: d2xz(Br[j], T[0]))
        Br = Br[b0:] + Br[:b0]
    walk = []
    i = j = 0
    while i < NT or j < NB:
        t_cur = T[i % NT]
        b_cur = Br[j % NB]
        if i < NT and j < NB:
            adv_t = d2xz(T[(i + 1) % NT], b_cur) <= d2xz(t_cur, Br[(j + 1) % NB])
        else:
            adv_t = i < NT
        s = min(i, NT - 1) % NT
        if adv_t:
            walk.append((s, (("T", i % NT), ("T", (i + 1) % NT), ("B", j % NB))))
            i += 1
        else:
            walk.append((s, (("T", i % NT), ("B", (j + 1) % NB), ("B", j % NB))))
            j += 1
    for s, tri in walk:
        col = cols[s % 4]
        u0, v0, du_, dv_ = TILE_RECT[(col, row)]
        b_idxs = sorted(idx for side, idx in tri if side == "B")
        pts = []
        for side, idx in tri:
            if side == "T":
                p = T[idx]
                right = (idx == (s + 1) % NT)
                pts.append((p[0], p[1], p[2], u0 + (du_ if right else 0.0), v0))
            else:
                p = Br[idx]
                if len(b_idxs) == 2:
                    right = (idx == max(b_idxs)) if max(b_idxs) - min(b_idxs) == 1 \
                        else (idx == min(b_idxs))
                else:
                    t01 = ((idx / NB - s / NT) * NT) % NT
                    if t01 > NT / 2:
                        t01 -= NT
                    right = t01 > 0.5
                pts.append((p[0], p[1], p[2], u0 + (du_ if right else 0.0), v0 + dv_))
        a, b, c = (np.asarray(p[:3]) for p in pts)
        nrm = np.cross(b - a, c - a)
        if float(np.linalg.norm(nrm)) < 1e-9:
            continue
        order = pts if nrm[1] > 0 else (pts[0], pts[2], pts[1])
        # near-vertical wall tris keep their winding (ny ~ 0 is fine; topo blocks anyway)
        corners = tuple((p[0], p[1], p[2], p[3], p[4], 0.0, 1.0, 0.0) for p in order)
        new_parents.append((corners, ID49, "wall"))
print(f"wall tris: {len(new_parents)}", flush=True)

# the lowland zip: south_chain <-> ring3's LAND section
foot = rings[-1]
land_foot = [p for p in foot if pip(p[0], p[2], outline_poly)]
# ... the zip walks the whole foot ring against the south chain openly: use only the land
# section ordered along the chord (west->east by x)
land_foot.sort(key=lambda p: p[0])
sc = sorted(south_chain, key=lambda p: p[0])
zip_tris = []
i = j = 0
while i < len(sc) - 1 or j < len(land_foot) - 1:
    h_cur = sc[min(i, len(sc) - 1)]
    r_cur = land_foot[min(j, len(land_foot) - 1)]
    can_h = i < len(sc) - 1
    can_r = j < len(land_foot) - 1
    if can_h and can_r:
        adv_h = d2xz(sc[i + 1], r_cur) <= d2xz(h_cur, land_foot[j + 1])
    else:
        adv_h = can_h
    if adv_h:
        zip_tris.append((h_cur, sc[i + 1], r_cur))
        i += 1
    else:
        zip_tris.append((h_cur, land_foot[j + 1], r_cur))
        j += 1
print(f"lowland zip: {len(zip_tris)} tris", flush=True)

# zip mains: byte-decode per cell from kept south grass
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
for tri3 in zip_tris:
    a, b, c = (np.asarray(p, dtype=float) for p in tri3)
    nrm = np.cross(b - a, c - a)
    if float(np.linalg.norm(nrm)) < 1e-9:
        continue
    order = tri3 if nrm[1] > 0 else (tri3[0], tri3[2], tri3[1])
    cell = cell_of(float(a[0] + b[0] + c[0]) / 3, float(a[2] + b[2] + c[2]) / 3)
    q, o = decode_cell(cell)
    corners = []
    for pnt in order:
        u, v = G.mains_uv(float(pnt[0]), float(pnt[2]), cell, q, o)
        n3 = pos_nrm.get(kk3(pnt), [0.0, 1.0, 0.0])
        corners.append((float(pnt[0]), float(pnt[1]), float(pnt[2]), u, v, *n3))
    new_parents.append((tuple(corners), ID0, "zip"))

# ---- 6. assemble: kept south verbatim; kept north raised (topo -> 13); new tris ---------------
pos, nrm2, uv2, tan2, flat, tris2 = [], [], [], [], [], []
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
for corners, idall, fam in new_parents:
    for p in corners:
        emit(p[:3], (p[3], p[4]), (p[5], p[6], p[7]), idall)
    tris2.append([flat[-3], flat[-2], flat[-1]])
new_bm = X.BlockMesh(name=built["blocks"][BLK].name, disc=1, x=bx, y=by, lod="0_1",
                     vcount=len(pos), stride=48,
                     channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
                     chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm2, X.CH_UV: uv2, X.CH_TAN: tan2},
                     flat_index=flat, tris=tris2, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])

# ---- 7. gates ----------------------------------------------------------------------------------
down = sum(1 for corners, _, f in new_parents if f == "zip"
           for _ in [0]
           if np.cross(np.asarray(corners[1][:3]) - np.asarray(corners[0][:3]),
                       np.asarray(corners[2][:3]) - np.asarray(corners[0][:3]))[1] < 0)
import dataclasses
plane = M.fill_missing_grid_quads(X.read_block(12, 0, disc=1, part="sea4"))
hid = lambda nm_: M.hidden_block_mesh(name=nm_, disc=1, x=bx, y=by)  # noqa: E731
sea = dataclasses.replace(plane, x=bx, y=by, name=f"Block[{bx}][{by}] Sea4")
meshlist = [("Object", hid("Object")), ("Terrain", new_bm), ("Sea1", hid("Sea1")),
            ("Sea2", hid("Sea2")), ("Sea3", hid("Sea3")), ("Sea4", sea), ("Sea5", hid("Sea5"))]
cen = P.census(meshlist)
print(f"GATES: zipDown={down} censusMISS={len(cen['miss'])}", flush=True)
assert down == 0 and len(cen["miss"]) == 0
lx, lz = CX - BLOCK * bx, CZ + BLOCK * (by + 1) - BLOCK
gy, nm_, _, topo = P.place(meshlist, lx, lz + 12)          # north (less-negative z) = plateau
print(f"plateau probe grounds: y={gy:.2f} {nm_} topo {topo}", flush=True)
gy2, nm2_, _, topo2 = P.place(meshlist, lx, lz - 18)       # south = lowland
print(f"lowland probe grounds: y={gy2:.2f} {nm2_} topo {topo2}", flush=True)
assert topo == 13 and abs(gy - PLATEAU_Y) < 1.5
assert topo2 == 0 and gy2 < 5

# ---- 8. render ---------------------------------------------------------------------------------
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
order_rows = sorted(range(len(tris2)),
                    key=lambda t: min(pos[i][1] for i in tris2[t]))   # paint low first
for t in order_rows:
    p3 = [(pos[i][0] + BLOCK * bx, pos[i][1], pos[i][2] - BLOCK * (by + 1) + BLOCK) for i in tris2[t]]
    q3 = [uv2[i] for i in tris2[t]]
    n3 = [nrm2[i] for i in tris2[t]]
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
            nx = sum(w * n3[k2][0] for k2, w in enumerate((w0, w1, w2)))
            ny = sum(w * n3[k2][1] for k2, w in enumerate((w0, w1, w2)))
            nz = sum(w * n3[k2][2] for k2, w in enumerate((w0, w1, w2)))
            nl = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
            f = 0.55 + 0.45 * max(0.0, (nx*LDIR[0] + ny*LDIR[1] + nz*LDIR[2]) / nl)
            op[pyx, RH-1-pyz] = (255, 255, 255) if aa < 24 else \
                tuple(min(255, int(cc*f)) for cc in rgb[:3])
OUT_RENDER.parent.mkdir(exist_ok=True)
out.save(OUT_RENDER)
print(f"render -> {OUT_RENDER}", flush=True)

# ---- 9. deploy ---------------------------------------------------------------------------------
if len(sys.argv) > 1 and sys.argv[1] == "deploy":
    assert pristine, "deployed island F is not pristine -- re-run the world-island mint first"
    BK.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(src, BK / f"{src.name}.{ts}")
    outp = M.deploy_override(new_bm, mod_folder="FF9CustomMap-world", part="Terrain")
    print(f"deployed -> {outp} ({len(new_bm.tris)} tris)")
    print(f"DONE -- world re-entry; teleport {CX:.0f},{CZ + 18:.0f} = lowland at the wall's foot.")
else:
    print("dry run only -- re-run with 'deploy' to write.")
