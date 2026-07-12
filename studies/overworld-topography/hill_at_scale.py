"""RUNG C -- THE HILL AT SCALE: a real-language grass hill on island E.

The measured language (study 2026-07-12, all disc-1 lowland grass): slope envelope p50 6.5
deg / p90 15.7 / p99 28.6; PURE-GRASS lowland summits are real (e.g. (16,14) y 8.2 prom 4.2,
(17,15) prom 5.1, (9,17) prom 5.2 over ~20u), profile = gentle cap, mid-flanks 20-24 deg,
prominence 3.5-5.2 over 20-26u radius, all within the TERRACE LAW's lowland band (<= 8u).

The build: a raised-cosine dome (H=4.5, R=20 -> max flank 19.5 deg) Y-DISPLACED into the
DEPLOYED island E meshes by world-position rule -- mains UVs are XZ-linear so pure-Y motion
keeps every tile lawful; the existing rolling relief rides on top (real hills roll). Fams
classify straight from the deployed bytes (topo + UV family region): the footprint must be
pure grass MAINS, clear of the forest (topo 37 + its zip ring), the meadow stamps (UV in the
D/B regions), and the coast rim (topo 58). Normals re-smooth LOCALLY (only verts of displaced
tris -- the forest's donor-carried normals never change). Gates: flank-slope envelope,
cracks=0, down/walk-filter=0, census MISS=0, byte-stability outside the hill, shaded render.

Usage:  py studies/overworld-topography/hill_at_scale.py [deploy]
"""
import math
import shutil
import sys
import time
from collections import defaultdict
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
OUT_RENDER = Path(__file__).with_name("out") / "island_e_hill_render.png"
BLOCKS = [(4, 17), (4, 18), (5, 17), (5, 18), (6, 18)]
BLOCK = 64.0

H, R = 4.2, 18.0                                            # prominence / radius (in-language; max flank 20.1 deg)
MAX_FLANK = 28.6                                            # the measured grass p99 (deg)
FOREST_CLEAR = 12.0                                         # hill footprint clear of topo-37
STAMP_CLEAR = 4.0
RIM_CLEAR = 6.0
kk3 = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

# ---- 1. load the DEPLOYED island (the carved state is the base) ---------------------------
meshes = {}
gpos, gtris, gsrc = [], [], []                              # world soup + (blk, local tri idx)
for blk in BLOCKS:
    p = MODW / f"r{blk[1]}" / f"Block[{blk[0]}][{blk[1]}] Terrain.ff9mesh"
    bm = M.blockmesh_from_ff9mesh(p, disc=1, x=blk[0], y=blk[1], lod="0_1", part="terrain")
    meshes[blk] = bm
    bx, by = blk
    base = len(gpos)
    for k in range(bm.vcount):
        v = bm.verts[k]
        gpos.append([v[0] + BLOCK * bx, v[1], v[2] - BLOCK * (by + 1) + BLOCK])
    for t, tri in enumerate(bm.tris):
        gtris.append([tri[0] + base, tri[1] + base, tri[2] + base])
        gsrc.append((blk, t))
print(f"deployed island: {len(gtris)} tris across {len(BLOCKS)} blocks", flush=True)

# classify every tri from its bytes: topo + UV family region
def fam_of(blk, t):
    bm = meshes[blk]
    tri = bm.tris[t]
    topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
    if topo == 37:
        return "forest"
    if topo == 58:
        return "rock"
    if topo != 0:
        return f"topo{topo}"
    us = [bm.uvs[i][0] for i in tri]
    lo, hi = G.FAM_REGION["main"][0], G.FAM_REGION["main"][2]
    if all(lo - 0.02 <= u <= hi + 0.02 for u in us):
        return "main"
    return "stamp"                                          # D/B meadow regions

tri_fam = [fam_of(*gsrc[i]) for i in range(len(gtris))]
tri_cx = []
tri_cz = []
for tri in gtris:
    a, b, c = (gpos[i] for i in tri)
    tri_cx.append((a[0] + b[0] + c[0]) / 3)
    tri_cz.append((a[2] + b[2] + c[2]) / 3)
tri_cx = np.array(tri_cx)
tri_cz = np.array(tri_cz)
fam_arr = np.array(tri_fam)
forest_pts = np.array([(tri_cx[i], tri_cz[i]) for i in range(len(gtris)) if tri_fam[i] == "forest"])
stamp_pts = np.array([(tri_cx[i], tri_cz[i]) for i in range(len(gtris)) if tri_fam[i] == "stamp"])
rock_pts = np.array([(tri_cx[i], tri_cz[i]) for i in range(len(gtris)) if tri_fam[i] == "rock"])
print(f"fams: { {f: int((fam_arr == f).sum()) for f in set(tri_fam)} }", flush=True)

def mind(pts, x, z):
    if len(pts) == 0:
        return 1e9
    return float(np.sqrt(((pts[:, 0] - x) ** 2 + (pts[:, 1] - z) ** 2).min()))

# ---- 2. placement scan: a pure-mains disc of radius R + fade, clear of everything ----------
FOOT = R + 2.0
cands = []
for gx in range(280, 400, 4):
    for gz in range(-1208, -1096, 4):
        sel = (tri_cx - gx) ** 2 + (tri_cz - gz) ** 2 < FOOT ** 2
        if sel.sum() < 60:
            continue
        if not all(fam_arr[sel] == "main"):
            continue
        d_f = mind(forest_pts, gx, gz) - FOOT
        d_s = mind(stamp_pts, gx, gz) - FOOT
        d_r = mind(rock_pts, gx, gz) - FOOT
        if d_f < FOREST_CLEAR or d_s < STAMP_CLEAR or d_r < RIM_CLEAR:
            continue
        cands.append((round(min(d_f, d_s, d_r), 1), gx, gz))
assert cands, "no lawful hill placement on island E"
cands.sort(reverse=True)
_, CX, CZ = cands[0]
print(f"hill centre -> ({CX},{CZ})  (clearance {cands[0][0]}u, {len(cands)} candidates)", flush=True)

# ---- 3. displace Y (raised cosine), locally re-smooth normals ------------------------------
def lift(x, z):
    d = math.hypot(x - CX, z - CZ)
    if d >= R:
        return 0.0
    return H / 2.0 * (1.0 + math.cos(math.pi * d / R))

touched_tris = set()
for i, tri in enumerate(gtris):
    if any(lift(gpos[j][0], gpos[j][2]) > 1e-9 for j in tri):
        touched_tris.add(i)
        assert tri_fam[i] == "main", f"hill displaces a non-mains tri ({tri_fam[i]})"
for i in range(len(gpos)):
    gpos[i][1] += lift(gpos[i][0], gpos[i][2])

# local re-smooth: position-welded area-weighted normals for verts of touched tris
recompute = {kk3(gpos[j]) for i in touched_tris for j in gtris[i]}
acc = defaultdict(lambda: [0.0, 0.0, 0.0])
for tri in gtris:
    a, b, c = (np.asarray(gpos[j]) for j in tri)
    n = np.cross(b - a, c - a)
    for j in tri:
        k = kk3(gpos[j])
        if k in recompute:
            v = acc[k]
            v[0] += n[0]; v[1] += n[1]; v[2] += n[2]
new_nrm = {}
for k, v in acc.items():
    L = math.sqrt(sum(q * q for q in v)) or 1.0
    new_nrm[k] = [v[0] / L, v[1] / L, v[2] / L]

# ---- 4. gates ------------------------------------------------------------------------------
worst_slope = 0.0
down = 0
for i in touched_tris:
    a, b, c = (np.asarray(gpos[j]) for j in gtris[i])
    n = np.cross(b - a, c - a)
    L = float(np.linalg.norm(n)) or 1.0
    if n[1] <= 0:
        down += 1
    worst_slope = max(worst_slope, math.degrees(math.acos(min(1.0, abs(n[1]) / L))))
peak_y = max(gpos[j][1] for i in touched_tris for j in gtris[i])
print(f"GATES: displaced tris={len(touched_tris)} worstFlank={worst_slope:.1f}deg "
      f"(<= {MAX_FLANK}) down={down} peakY={peak_y:.2f}", flush=True)
assert worst_slope <= MAX_FLANK and down == 0
assert peak_y <= 8.6, "peak leaves the lowland band"

# crack scan over the hill region (position-keyed once-edges must be only the region border)
from collections import Counter
eu = Counter()
for i, tri in enumerate(gtris):
    if math.hypot(tri_cx[i] - CX, tri_cz[i] - CZ) > R + 8:
        continue
    for a, b in ((0, 1), (1, 2), (2, 0)):
        eu[tuple(sorted((kk3(gpos[tri[a]]), kk3(gpos[tri[b]]))))] += 1
inner_once = [e for e, n in eu.items() if n == 1
              and math.hypot((e[0][0] + e[1][0]) / 2 - CX, (e[0][2] + e[1][2]) / 2 - CZ) < R + 4]
print(f"crack gate: once-edges inside the hill region = {len(inner_once)} (want 0)", flush=True)
assert not inner_once

# radial profile print (compare with the real rings)
prof = []
for r0 in (0, 4, 8, 12, 16, 20):
    ys = [gpos[j][1] for i in touched_tris for j in gtris[i]
          if abs(math.hypot(gpos[j][0] - CX, gpos[j][2] - CZ) - r0) < 2]
    if ys:
        prof.append(f"{r0}:{np.median(ys):.1f}")
print(f"hill rings [{' '.join(prof)}]  (real e.g. (17,15): 4:7.2 8:6.8 12:6.3 16:5.7 20:4.9)",
      flush=True)

# ---- 5. write back per block; census; byte-stability -------------------------------------
import dataclasses
changed = {}
for blk in BLOCKS:
    bm = meshes[blk]
    bx, by = blk
    pos = [list(v) for v in bm.chan_arrays[X.CH_POS]]
    nrm = [list(v) for v in bm.chan_arrays[X.CH_NRM]]
    base = sum(meshes[b].vcount for b in BLOCKS[:BLOCKS.index(blk)])
    dirty = False
    for k in range(bm.vcount):
        w = gpos[base + k]
        newy = w[1]
        if abs(newy - pos[k][1]) > 1e-9:
            pos[k][1] = newy
            dirty = True
        kkey = kk3(w)
        if kkey in new_nrm:
            nrm[k] = list(new_nrm[kkey])
            dirty = True
    if dirty:
        ca = dict(bm.chan_arrays)
        ca[X.CH_POS] = pos
        ca[X.CH_NRM] = nrm
        changed[blk] = dataclasses.replace(bm, chan_arrays=ca)
print(f"blocks with hill changes: {sorted(changed)}", flush=True)

plane = M.fill_missing_grid_quads(X.read_block(12, 0, disc=1, part="sea4"))
for blk, bm in changed.items():
    bx, by = blk
    hid = lambda nm_: M.hidden_block_mesh(name=nm_, disc=1, x=bx, y=by)  # noqa: E731
    sea = dataclasses.replace(plane, x=bx, y=by, name=f"Block[{bx}][{by}] Sea4")
    cen = P.census([("Object", hid("Object")), ("Terrain", bm), ("Sea1", hid("Sea1")),
                    ("Sea2", hid("Sea2")), ("Sea3", hid("Sea3")), ("Sea4", sea),
                    ("Sea5", hid("Sea5"))])
    assert len(cen["miss"]) == 0, f"placement MISS in {blk}"
print("placement census: MISS=0 in changed blocks", flush=True)

# ---- 6. shaded render (offline eye) --------------------------------------------------------
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
        r, g, b, a = PX[px_, py_]
        acc_[0] += r*wgt; acc_[1] += g*wgt; acc_[2] += b*wgt; aa += a*wgt
    return aa, (int(acc_[0]), int(acc_[1]), int(acc_[2]))
SC = 16
lo_x = min(v[0] for v in gpos); hi_x = max(v[0] for v in gpos)
lo_z = min(v[2] for v in gpos); hi_z = max(v[2] for v in gpos)
RW, RH = int((hi_x - lo_x) * SC) + 2, int((hi_z - lo_z) * SC) + 2
out = Image.new("RGB", (RW, RH), (24, 40, 72))
op = out.load()
LDIR = (-0.45, 0.8, -0.35)
_l = math.sqrt(sum(q*q for q in LDIR)); LDIR = tuple(q/_l for q in LDIR)
for bi, blk in enumerate(BLOCKS):
    bm = changed.get(blk, meshes[blk])
    bx, by = blk
    uvs = bm.chan_arrays[X.CH_UV]
    nr = bm.chan_arrays[X.CH_NRM]
    ps = bm.chan_arrays[X.CH_POS]
    for tri in bm.tris:
        p3 = [(ps[i][0] + BLOCK * bx, ps[i][1], ps[i][2] - BLOCK * (by + 1) + BLOCK) for i in tri]
        q3 = [uvs[i] for i in tri]
        n3 = [nr[i] for i in tri]
        xs = [(pp[0] - lo_x) * SC for pp in p3]; zs = [(pp[2] - lo_z) * SC for pp in p3]
        x0, x1 = int(min(xs)), int(max(xs)) + 1; z0, z1 = int(min(zs)), int(max(zs)) + 1
        d = (zs[1]-zs[2])*(xs[0]-xs[2]) + (xs[2]-xs[1])*(zs[0]-zs[2])
        if abs(d) < 1e-9:
            continue
        for pyx in range(max(0, x0), min(RW, x1)):
            for pyz in range(max(0, z0), min(RH, z1)):
                w0 = ((zs[1]-zs[2])*(pyx-xs[2]) + (xs[2]-xs[1])*(pyz-zs[2])) / d
                w1 = ((zs[2]-zs[0])*(pyx-xs[2]) + (xs[0]-xs[2])*(pyz-zs[2])) / d
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

# ---- 7. deploy -----------------------------------------------------------------------------
if len(sys.argv) > 1 and sys.argv[1] == "deploy":
    BK.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    for blk, bm in sorted(changed.items()):
        dep = MODW / f"r{blk[1]}" / f"Block[{blk[0]}][{blk[1]}] Terrain.ff9mesh"
        shutil.copyfile(dep, BK / f"{dep.name}.{ts}")
        outp = M.deploy_override(bm, mod_folder="FF9CustomMap-world", part="Terrain")
        print(f"deployed -> {outp} ({len(bm.tris)} tris)", flush=True)
    print(f"DONE -- F6 world re-entry, teleport {CX},{CZ}; walk the hill from all sides.")
else:
    print("dry run only -- re-run with 'deploy' to write.")
