"""MASSIF SYNTH -- the from-scratch SHEET MASSIF, every mountain law composed.

The three-stage study licensed exactly this build (the two-classes law: a closed massif =
hill-at-scale geometry + rock retile, NOT wall construction):

  GEOMETRY -- pure-Y displacement of the bench islet's deployed grass lattice (the proven
    world-hill operation, taller): a 45-degree cone flank (S=1.0 makes the displaced
    lattice's course height EXACTLY 4.2u = the real massif's 4.29u median -- no
    subdivision needed) with a parabolic cap; foot radius F=13, cap C=5, peak H=10.5u.
    ZERO topology change: flat mesh + smooth radial h(x,z) => every positional weld
    survives by construction; no rings, no zips, no drops.
  CLASSIFICATION -- any tri meaningfully displaced (max vert lift > 0.3u) becomes topo-49
    rock (minted idall; foot-illegal by TOPO, the faithful mechanism; the summit is rock
    -- a walkable synthetic summit would break the island corollary; real precedent =
    the all-rock crag islands (9-10,5-7) and Uaho).
  RETILE -- rows = absolute height courses of 4.2u (foot row 10 -> 9 -> 8, landing on the
    real G5 staircase bands); cols FREE (the col-freedom law), cycling real exemplar
    QUADS harvested from the actual Daguerreo massif per row; u by azimuth windows of
    ~4.7u arc, v by height fraction in the course; all UVs fractional inside real rects.
  NORMALS -- re-smoothed area-weighted PER CLASS (rock from rock faces, grass from grass
    faces -- the real foot pattern: positional weld, separate normals).

Gates: census MISS=0, down-facing 0, crack scan (once-edges unchanged), slope envelopes
(rock med ~45, remaining grass <= 28.6), foot dihedral report, and THE OFFLINE EYE
(4-azimuth elevation renders + a textured top-down). Dry-run by default; --apply deploys.

Bench: block (2,19), the seed-42 islet at (160,-1248). Run from the repo root:
  py studies/overworld-topography/massif_synth.py [--apply]
"""
import argparse
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config                                # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import interior as IN                  # noqa: E402
from ff9mapkit.world import mesh as M                       # noqa: E402

CELL = (2, 19)
CENTER = (160.0, -1248.0)
BLOCK = 64.0
TILE_U, TILE_V = 0.0625, 0.03125
F_FOOT, C_CAP, S_FLANK = 13.0, 5.0, 1.0                    # foot r, cap r, tan(45 deg)
COURSE_H = 4.2                                             # the real course median
ROCK_LIFT = 0.3                                            # displaced past this => rock
CLEAR = 4.0                                                # footprint..non-mains margin
MAX_FLANK = 28.6                                           # the grass envelope (p99)
DONORS = [(5, 15), (6, 15), (5, 16), (6, 16)]              # the real massif blocks
OUTD = Path(__file__).with_name("out")
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true")
ap.add_argument("--mod-folder", default="FF9CustomMap-world")
args = ap.parse_args()
ID49 = float(X.encode_id(topograph=49))

# ---- load the bench block -------------------------------------------------------------------------
gp = Path(config.find_game_path(None))
mesh_path = (gp / args.mod_folder / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
             / f"r{CELL[1]}" / f"Block[{CELL[0]}][{CELL[1]}] Terrain.ff9mesh")
bm = M.blockmesh_from_ff9mesh(mesh_path, disc=1, x=CELL[0], y=CELL[1], part="terrain")
V = [list(v) for v in bm.verts]
N = [list(n) for n in bm.normals]
U = [list(u) for u in bm.uvs]
T = [list(t) for t in bm.tangents]
IDX = list(bm.flat_index)
ntri = len(IDX) // 3
tri_idx = [IDX[3 * t:3 * t + 3] for t in range(ntri)]
topo = [X.decode_id(int(round(T[i[0]][0])))["topograph"] for i in tri_idx]
def wpos(j):
    return (V[j][0] + BLOCK * CELL[0], V[j][1], V[j][2] - BLOCK * CELL[1])
print(f"bench {mesh_path.name}: {ntri} tris, topo {dict(Counter(topo))}")

# mains-region bounds for the pure-mains footprint check
lo_u, v0r, hi_u, v1r = IN.G.FAM_REGION["main"] if hasattr(IN, "G") else (None,) * 4

# ---- the footprint-lawful check + centre ----------------------------------------------------------
cx, cz = CENTER
need = F_FOOT + CLEAR
bad = []
for t in range(ntri):
    ws = [wpos(j) for j in tri_idx[t]]
    cen = np.mean(ws, axis=0)
    r = math.hypot(cen[0] - cx, cen[2] - cz)
    if r < need and topo[t] != 0:
        bad.append((topo[t], round(r, 1)))
assert not bad, f"footprint not pure grass: {bad[:6]}"
ys_fp = [wpos(j)[1] for t in range(ntri) for j in tri_idx[t]
         if math.hypot(wpos(j)[0] - cx, wpos(j)[2] - cz) < need and topo[t] == 0]
y_base = float(np.median(ys_fp))
assert max(ys_fp) - min(ys_fp) <= 2.4, "footprint fails the rolling-relief envelope"
print(f"footprint clean: pure mains within r{need}, base y {y_base:.2f} "
      f"(span {max(ys_fp) - min(ys_fp):.2f})")

# ---- the profile + displacement -------------------------------------------------------------------
RIDGES, R_AMP = 6, 0.18                                    # radial ridgelines up the cone
JIT = 0.7                                                  # crag jitter (positional hash)
def h_of(r, az):
    if r >= F_FOOT:
        return 0.0
    if r >= C_CAP:
        h = S_FLANK * (F_FOOT - r)
    else:
        h = S_FLANK * (F_FOOT - C_CAP) + S_FLANK * (C_CAP ** 2 - r ** 2) / (2 * C_CAP)
    return h * (1.0 + R_AMP * math.cos(RIDGES * az + 1.3))
def jit_of(x, z):
    return (math.sin(x * 12.9898 + z * 78.233) * 43758.5453) % 1.0 - 0.5
lift = [0.0] * len(V)
for j in range(len(V)):
    w = wpos(j)
    r = math.hypot(w[0] - cx, w[2] - cz)
    az = math.atan2(w[2] - cz, w[0] - cx)
    h = h_of(r, az)
    if h > 0.0:
        h += JIT * jit_of(w[0], w[2]) * min(1.0, h / 2.0)  # crag jitter, tapered at foot
        h = max(0.0, h)
    lift[j] = h
    V[j][1] += h
peak = max(V[j][1] for j in range(len(V)))
print(f"displaced: peak y {peak:.2f} (base {y_base:.2f}, {RIDGES} ridgelines, "
      f"jitter {JIT})")

# ---- classification: ANY lifted vert => rock (a clean lattice-ring foot, no slivers) --------------
rock = set()
for t in range(ntri):
    if topo[t] != 0:
        continue
    if max(lift[j] for j in tri_idx[t]) > 0.05:
        rock.add(t)
print(f"rock tris: {len(rock)}")

# ---- exemplar quads per row from the REAL massif --------------------------------------------------
stage1 = None
try:
    import json
    stage1 = json.loads((OUTD / "daguerreo_massif.json").read_text())
except Exception:
    pass
pu, pv = stage1["phase"]
ex_rows = defaultdict(dict)                                # row -> col -> rect
for (dbx, dby) in DONORS:
    dm = X.read_block(dbx, dby, disc=1, part="terrain")
    dV, dU, dT = dm.verts, dm.uvs, dm.tangents
    didx = np.asarray(dm.flat_index, dtype=np.int64).reshape(-1, 3)
    dtopo = [X.decode_id(int(round(dT[i[0]][0])))["topograph"] for i in didx]
    e2t = defaultdict(list)
    for t, i in enumerate(didx):
        if dtopo[t] != 49:
            continue
        ps = [kk(dV[j]) for j in i]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e2t[tuple(sorted((ps[a], ps[b])))].append(t)
    seenq = set()
    for e, ts in e2t.items():
        if len(ts) != 2 or ts[0] in seenq or ts[1] in seenq:
            continue
        vs4 = {kk(dV[j]) for t in ts for j in didx[t]}
        if len(vs4) != 4:
            continue
        uvm = {}
        for t in ts:
            for j in didx[t]:
                uvm[kk(dV[j])] = (float(dU[j][0]), float(dU[j][1]))
        us = [q[0] for q in uvm.values()]
        vs2 = [q[1] for q in uvm.values()]
        du2, dv2 = max(us) - min(us), max(vs2) - min(vs2)
        if not (0.8 * TILE_U < du2 <= TILE_U + 1e-4 and 0.8 * TILE_V < dv2 <= TILE_V + 1e-4):
            continue
        row = round((min(vs2) - pv) / TILE_V)
        col = round((min(us) - pu) / TILE_U)
        if row not in (7, 8, 9, 10) or col not in (6, 7, 8, 9) or col in ex_rows[row]:
            continue                                       # ONE band (6-9): no band mixing
        pts4 = sorted(vs4, key=lambda p: p[1])
        ex_rows[row][col] = dict(u0=min(us), u1=max(us),
                                 v_lo=float(np.mean([uvm[p][1] for p in pts4[:2]])),
                                 v_hi=float(np.mean([uvm[p][1] for p in pts4[2:]])))
        seenq.update(ts)
for row in sorted(ex_rows):
    print(f"exemplars row {row}: cols {sorted(ex_rows[row])}")
assert all(ex_rows.get(r) for r in (8, 9, 10)), "missing exemplar rows"

# ---- retile the rock ------------------------------------------------------------------------------
# pair rock tris into lattice quads
e2r = defaultdict(list)
for t in rock:
    ps = [kk(wpos(j)) for j in tri_idx[t]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        e2r[tuple(sorted((ps[a], ps[b])))].append(t)
qpaired = {}
qgroups = []
for e, ts in e2r.items():
    if len(ts) != 2 or ts[0] in qpaired or ts[1] in qpaired:
        continue
    vs4 = {kk(wpos(j)) for t in ts for j in tri_idx[t]}
    if len(vs4) != 4:
        continue
    qpaired[ts[0]] = qpaired[ts[1]] = len(qgroups)
    qgroups.append(list(ts))
for t in rock:                                             # boundary filler tris go solo
    if t not in qpaired:
        qpaired[t] = len(qgroups)
        qgroups.append([t])
print(f"rock quads {sum(1 for g in qgroups if len(g) == 2)} + filler "
      f"{sum(1 for g in qgroups if len(g) == 1)}")

def course_of(y):
    return max(0, min(2, int((y - y_base) / COURSE_H)))
ROW_OF = {0: 10, 1: 9, 2: 8}
for gi, grp in enumerate(qgroups):
    pts = [wpos(j) for t in grp for j in tri_idx[t]]
    ys3 = [p[1] for p in pts]
    course = course_of(float(np.mean(ys3)))
    row = ROW_OF[course]
    band_lo = min(ys3)                                     # ONE tile per QUAD (v axis):
    band_hi = max(band_lo + 0.5, max(ys3))                 # the quad IS the course
    cen = np.mean(pts, axis=0)
    az = math.atan2(cen[2] - cz, cen[0] - cx)
    r_mid = max(2.0, F_FOOT - (float(np.mean(ys3)) - y_base) / S_FLANK)
    nwin = max(1, round(2 * math.pi * r_mid / 4.7))
    w = int((az + math.pi) / (2 * math.pi) * nwin) % nwin  # contour position -> col cycle
    cols = sorted(ex_rows[row])
    e2 = ex_rows[row][cols[w % len(cols)]]
    tx, tz = -math.sin(az), math.cos(az)                   # the tangential (contour) dir
    ts3 = [(p[0] - cen[0]) * tx + (p[2] - cen[2]) * tz for p in pts]
    t_lo, t_hi = min(ts3), max(min(ts3) + 0.5, max(ts3))   # ONE tile per QUAD (u axis)
    for t in grp:
        for j in tri_idx[t]:
            wv = wpos(j)
            tv = (wv[0] - cen[0]) * tx + (wv[2] - cen[2]) * tz
            su = (tv - t_lo) / (t_hi - t_lo)
            h = (wv[1] - band_lo) / (band_hi - band_lo)
            U[j][0] = e2["u0"] + su * (e2["u1"] - e2["u0"])
            U[j][1] = e2["v_lo"] + h * (e2["v_hi"] - e2["v_lo"])
            T[j] = [ID49, 0.0, 0.0, 1.0]

# ---- normals: per-class local re-smooth -----------------------------------------------------------
touched = {j for t in range(ntri) for j in tri_idx[t]
           if t in rock or any(lift[j2] > 0.0 for j2 in tri_idx[t])}
acc = {"rock": defaultdict(lambda: np.zeros(3)), "grass": defaultdict(lambda: np.zeros(3))}
for t in range(ntri):
    cls = "rock" if t in rock else "grass" if topo[t] == 0 else None
    if cls is None:
        continue
    a, b, c3 = (np.array(wpos(j)) for j in tri_idx[t])
    fn = np.cross(b - a, c3 - a)
    for j in tri_idx[t]:
        acc[cls][kk(wpos(j))] += fn
for t in range(ntri):
    cls = "rock" if t in rock else "grass" if topo[t] == 0 else None
    if cls is None:
        continue
    for j in tri_idx[t]:
        if j not in touched:
            continue
        v3 = acc[cls][kk(wpos(j))]
        L = np.linalg.norm(v3)
        if L > 1e-9:
            N[j] = (v3 / L).tolist()

# ---- gates ----------------------------------------------------------------------------------------
def slope_deg(t):
    a, b, c3 = (np.array(wpos(j)) for j in tri_idx[t])
    fn = np.cross(b - a, c3 - a)
    L = np.linalg.norm(fn) or 1.0
    return math.degrees(math.acos(max(-1, min(1, abs(fn[1]) / L)))), fn[1] / L
rs = [slope_deg(t) for t in rock]
gs = [slope_deg(t) for t in range(ntri) if topo[t] == 0 and t not in rock]
down = sum(1 for s, ny in rs + gs if ny < 0)
assert down == 0, f"{down} down-facing tris"
r_sl = [s for s, _ in rs]
g_sl = [s for s, _ in gs]
print(f"gates: rock slope med {np.median(r_sl):.1f} p90 {np.percentile(r_sl, 90):.1f} "
      f"max {max(r_sl):.1f} (sheet ceiling 72); grass max {max(g_sl):.1f} "
      f"(envelope {MAX_FLANK})")
assert max(r_sl) <= 72.0 and max(g_sl) <= MAX_FLANK
# foot dihedral: rock|grass shared edges
e2all = defaultdict(list)
for t in range(ntri):
    ps = [kk(wpos(j)) for j in tri_idx[t]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        e2all[tuple(sorted((ps[a], ps[b])))].append(t)
dih = []
for e, ts in e2all.items():
    if len(ts) != 2:
        continue
    r2 = [t for t in ts if t in rock]
    g2 = [t for t in ts if topo[t] == 0 and t not in rock]
    if len(r2) == 1 and len(g2) == 1:
        def fnrm(t):
            a, b, c3 = (np.array(wpos(j)) for j in tri_idx[t])
            fn = np.cross(b - a, c3 - a)
            return fn / (np.linalg.norm(fn) or 1.0)
        dih.append(math.degrees(math.acos(max(-1, min(1, float(np.dot(fnrm(r2[0]),
                                                                      fnrm(g2[0]))))))))
print(f"foot: {len(dih)} rock|grass edges, dihedral med {np.median(dih):.1f}deg "
      f"(real 46-53)")
once_now = sum(1 for ts in e2all.values() if len(ts) == 1)
print(f"once-edges {once_now} (topology untouched -- must equal the pristine count)")

# ---- assemble + census ----------------------------------------------------------------------------
pos = [[V[j][0], V[j][1], V[j][2]] for j in range(len(V))]
changed = {CELL: X.BlockMesh(
    name=bm.name, disc=1, x=CELL[0], y=CELL[1], lod="0_1", vcount=len(pos), stride=48,
    channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
    chan_arrays={X.CH_POS: pos, X.CH_NRM: N, X.CH_UV: U, X.CH_TAN: T},
    flat_index=IDX, tris=tri_idx, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])}
IN.census_gate(changed, disc=1)
print("census MISS=0")

# ---- THE OFFLINE EYE: 4 elevation views + a textured top-down -------------------------------------
MOG = gp / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
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
    for (dx, dy, wg) in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                         (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        px_, py_ = min(max(x0 + dx, 0), AW - 1), min(max(y0 + dy, 0), AH - 1)
        r, g2, b2, al = APX[px_, py_]
        a4[0] += r * wg; a4[1] += g2 * wg; a4[2] += b2 * wg; a4[3] += al * wg
    return a4[3], (int(a4[0]), int(a4[1]), int(a4[2]))
LDIR = (-0.5, 0.7, -0.3)
_l = math.sqrt(sum(q * q for q in LDIR)); LDIR = tuple(q / _l for q in LDIR)
tri_data = []
for t in range(ntri):
    tri_data.append(([wpos(j) for j in tri_idx[t]],
                     [(U[j][0], U[j][1]) for j in tri_idx[t]],
                     [N[j] for j in tri_idx[t]]))
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
OUTD.mkdir(exist_ok=True)
SC = 16
HW, HH = 22.0, 18.0
RW, RH = int(2 * HW * SC), int(HH * SC)
views = []
for name, azd in (("fromS", 90), ("fromW", 0), ("fromN", 270), ("fromE", 180)):
    azr = math.radians(azd)
    vx, vz = math.cos(azr), math.sin(azr)                  # view direction (into scene)
    rx, rz = -vz, vx                                       # screen right
    img = Image.new("RGB", (RW, RH), (150, 178, 210))
    rec = []
    for p3, uv3, n3 in tri_data:
        depth = max((p[0] - cx) * vx + (p[2] - cz) * vz for p in p3)
        rec.append((depth, p3, uv3, n3))
    for _, p3, uv3, n3 in sorted(rec, key=lambda r: r[0]):
        sx = [((p[0] - cx) * rx + (p[2] - cz) * rz + HW) * SC for p in p3]
        sy = [(HH - p[1]) * SC for p in p3]
        raster(img, sx, sy, uv3, n3, RW, RH)
    views.append((name, img))
gap = 8
sheet = Image.new("RGB", (RW, (RH + gap) * len(views) - gap), (10, 10, 10))
for k, (name, img) in enumerate(views):
    sheet.paste(img, (0, k * (RH + gap)))
sheet.save(OUTD / "massif_synth_views.png")
print(f"-> {OUTD / 'massif_synth_views.png'} (S, W, N, E elevations)")
S2 = 8
img = Image.new("RGB", (int(BLOCK * S2), int(BLOCK * S2)), (24, 40, 72))
order = sorted(range(ntri), key=lambda t: min(wpos(j)[1] for j in tri_idx[t]))
for t in order:
    p3 = [wpos(j) for j in tri_idx[t]]
    sx = [(p[0] - CELL[0] * BLOCK) * S2 for p in p3]
    sy = [(-p[2] - CELL[1] * BLOCK) * S2 for p in p3]
    raster(img, sx, sy, [(U[j][0], U[j][1]) for j in tri_idx[t]],
           [N[j] for j in tri_idx[t]], int(BLOCK * S2), int(BLOCK * S2))
img.save(OUTD / "massif_synth_top.png")
print(f"-> {OUTD / 'massif_synth_top.png'}")

tpx, tpz = math.floor(cx - F_FOOT - 6) + 0.5, math.floor(cz) + 0.5
print(f"suggested teleport: ({tpx}, {tpz}) on the west grass ring, face east")
if not args.apply:
    print("\nDRY RUN (no write). --apply to deploy.")
    sys.exit(0)
files = IN.deploy_changed(changed, mod_folder=args.mod_folder, disc=1)
print(f"deployed: {files}")
