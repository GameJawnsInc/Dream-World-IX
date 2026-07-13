"""UAHO PROBE -- one GORE PANEL re-mapped generatively on the bench carry.

The flow anatomy minted THE GORE-PANEL LAW: a small mountain's texture = ~8 azimuth
panels, each ONE affine chart (u ~ 36px/u contour + 20 shear; v ~ -39px/u up + 14 shear;
band cols 6-10 rows 7-11), seams downhill with (+-4,0) band-wrap jumps dominant, apex =
two panels meeting, foot fringe inside the panels. This probe confirms the law the
Stage-2 way: ONE panel (the 12-tri west face, az 235-279) gets a SYNTHETIC affine chart
built from the LAW's parameters -- magnitudes = law medians, orientation/signs continued
from the north-neighbor panel across their seam, v anchored at the row-10 bottom at the
foot. Geometry, seams, every other panel: verbatim bytes. If the probed face reads
seamless in-game, the law is generative material for world-mountain.

Operates directly on the DEPLOYED bench block (2,19) (uvs are verbatim, so the patch
decomposition is identical to the donor study). Backup -> repo backups/.

Usage:  py studies/overworld-topography/uaho_probe_panel.py [deploy]
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
from ff9mapkit.world import mesh as M

GP = Path(_cfg.find_game_path(None))
MODW = GP / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
BK = Path(__file__).resolve().parents[2] / "backups"
OUTD = Path(__file__).with_name("out")
BLK = (2, 19)
BLOCK = 64.0
TILE_U, TILE_V = 0.0625, 0.03125
ROCK = {49, 7, 62}
EPS = 0.0015
# THE LAW'S GENERATIVE PARAMETERS (uaho_flow_anatomy medians, in px/world-unit)
GU_T, GU_H = 36.0, 20.0                                    # u: along contour + up shear
GV_T, GV_H = 14.0, 39.0                                    # v: contour shear + up (v falls)
import json
stage1 = json.loads((OUTD / "daguerreo_massif.json").read_text())
pu, pv = stage1["phase"]
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

# ---- load the bench, find the mountain, rebuild the panels -----------------------------------------
src = MODW / f"r{BLK[1]}" / f"Block[{BLK[0]}][{BLK[1]}] Terrain.ff9mesh"
bm = M.blockmesh_from_ff9mesh(src, disc=1, x=BLK[0], y=BLK[1], lod="0_1", part="terrain")
bx, by = BLK
gpos = [[v[0] + BLOCK * bx, v[1], v[2] - BLOCK * (by + 1) + BLOCK] for v in bm.verts]
gtris = list(bm.tris)
gnrm = [list(n) for n in bm.chan_arrays[X.CH_NRM]]
guv = [list(u) for u in bm.chan_arrays[X.CH_UV]]
gtan = [list(t) for t in bm.chan_arrays[X.CH_TAN]]
gtopo = [X.decode_id(int(round(gtan[t[0]][0])))["topograph"] for t in gtris]
rock = [t for t in range(len(gtris)) if gtopo[t] in ROCK]
assert rock, "no mountain on the bench -- deploy the carry first"
uv_at = {}
for t in rock:
    for k in range(3):
        uv_at[(t, kk(gpos[gtris[t][k]]))] = tuple(guv[gtris[t][k]])
edge_tris = defaultdict(list)
for t in rock:
    ps = [kk(gpos[i]) for i in gtris[t]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        edge_tris[tuple(sorted((ps[a], ps[b])))].append(t)
parent = {t: t for t in rock}
def find(t):
    while parent[t] != t:
        parent[t] = parent[parent[t]]
        t = parent[t]
    return t
n_cont = 0
for e, ts in edge_tris.items():
    if len(ts) != 2:
        continue
    t1, t2 = ts
    d = max(abs(uv_at[(t1, e[0])][0] - uv_at[(t2, e[0])][0]),
            abs(uv_at[(t1, e[0])][1] - uv_at[(t2, e[0])][1]),
            abs(uv_at[(t1, e[1])][0] - uv_at[(t2, e[1])][0]),
            abs(uv_at[(t1, e[1])][1] - uv_at[(t2, e[1])][1]))
    if d < EPS:
        n_cont += 1
        r1, r2 = find(t1), find(t2)
        if r1 != r2:
            parent[r1] = r2
patches = defaultdict(list)
for t in rock:
    patches[find(t)].append(t)
plist = sorted(patches.values(), key=len, reverse=True)
print(f"bench mountain: {len(rock)} tris, panels {[len(p) for p in plist]}")
assert [len(p) for p in plist][:4] == [47, 21, 21, 12], "panel structure differs from the study"

hi = [t for t in rock
      if np.mean([gpos[i][1] for i in gtris[t]]) > 8.0]
cxm = float(np.mean([np.mean([gpos[i][0] for i in gtris[t]]) for t in hi]))
czm = float(np.mean([np.mean([gpos[i][2] for i in gtris[t]]) for t in hi]))
target = [p for p in plist if len(p) == 12]
assert len(target) == 1, "expected exactly one 12-tri panel"
panel = target[0]
pid_of = {}
for pi, p in enumerate(plist):
    for t in p:
        pid_of[t] = pi
p_az = [math.degrees(math.atan2(np.mean([gpos[i][2] for i in gtris[t]]) - czm,
                                np.mean([gpos[i][0] for i in gtris[t]]) - cxm)) % 360
        for t in panel]
print(f"probe panel: 12 tris, az [{min(p_az):.0f},{max(p_az):.0f}] (the west face)")

# ---- the seam to the NORTH neighbor: orientation + anchor continuation -----------------------------
panel_set = set(panel)
panel_keys = {kk(gpos[i]) for t in panel for i in gtris[t]}
seams = defaultdict(list)                                  # neighbor pid -> [(key, uv_n, uv_p)]
for e, ts in edge_tris.items():
    if len(ts) != 2:
        continue
    inp = [t for t in ts if t in panel_set]
    out = [t for t in ts if t not in panel_set]
    if len(inp) == 1 and len(out) == 1:
        for key in e:
            seams[pid_of[out[0]]].append((key, uv_at[(out[0], key)], uv_at[(inp[0], key)]))
print(f"seam neighbors: { {pi: len(v) for pi, v in seams.items()} }")
# the anchor neighbor = the biggest seam share (the north neighbor, patch 2 in the study)
anchor_pid = max(seams, key=lambda pi: len(seams[pi]))
anch = seams[anchor_pid]

# fit the ANCHOR NEIGHBOR's affine chart to get orientation signs (its real flow direction)
nb = plist[anchor_pid]
rows, ru, rv = [], [], []
for t in nb:
    for i in gtris[t]:
        rows.append([*gpos[i], 1.0])
        ru.append(guv[i][0])
        rv.append(guv[i][1])
Am = np.array(rows)
su, *_ = np.linalg.lstsq(Am, np.array(ru), rcond=None)
sv, *_ = np.linalg.lstsq(Am, np.array(rv), rcond=None)

# panel frame: contour tangent at the panel's mid azimuth + up
mid_az = math.radians((min(p_az) + max(p_az)) / 2)
tx, tz = -math.sin(mid_az), math.cos(mid_az)
# sign of u along the contour: match the neighbor's real du along the same tangent
sgn_u = 1.0 if (su[0] * tx + su[2] * tz) >= 0 else -1.0
sgn_uh = 1.0 if su[1] >= 0 else -1.0                       # u's up-shear sign from neighbor
sgn_vt = 1.0 if (sv[0] * tx + sv[2] * tz) >= 0 else -1.0   # v's contour-shear sign
print(f"anchor neighbor: panel {anchor_pid} ({len(nb)} tris); signs u_t {sgn_u:+.0f} "
      f"u_h {sgn_uh:+.0f} v_t {sgn_vt:+.0f}")

def s_of(p):
    return (p[0] - cxm) * tx + (p[2] - czm) * tz

# THE BAND-SWEEP LAW (the per-panel measurement is decisive): EVERY panel's u spans
# exactly 4.0 tiles (one full sweep of the col band) and its v ~2.5-3.3 tiles ending at
# the foot rows 10-11, REGARDLESS of world size (H 4.8..10.9u) -- the painter unrolled
# each face's box onto one band sweep x ~3 rows; texel density varies per panel and the
# (+-4,0) seam jumps ARE the sweep wraps. Constant-density (39px/u) was the wrong read:
# it halved the probe face's density (rows 10-11 only). Generative form: normalized box.
pk_ys = sorted(p[1] for p in ({kk(gpos[i]) for t in panel for i in gtris[t]}))
y0 = pk_ys[0]
verts = sorted({kk(gpos[i]) for t in panel for i in gtris[t]})
S_ALL = [s_of(p) for p in verts]
H_ALL = [p[1] for p in verts]
s_lo, s_hi = min(S_ALL), max(S_ALL)
h_lo, h_hi = min(H_ALL), max(H_ALL)
V_SPAN = 3.0 * TILE_V
def gen_uv(p):
    sn = (s_of(p) - s_lo) / max(s_hi - s_lo, 0.1)
    if sgn_u < 0:
        sn = 1.0 - sn
    hn = (p[1] - h_lo) / max(h_hi - h_lo, 0.1)
    u = pu + 6 * TILE_U + 0.0008 + sn * (4 * TILE_U - 0.0016)
    v = (pv + 10.9 * TILE_V) - hn * V_SPAN
    return u, v
uv_new = {p: gen_uv(np.array(p, dtype=float)) for p in verts}
# band check: the chart must stay inside the contiguous rock band (cols 6-10, rows 7-11)
cols = sorted({math.floor((u - pu) / TILE_U) for u, v in uv_new.values()})
vrows = sorted({math.floor((v - pv) / TILE_V) for u, v in uv_new.values()})
print(f"generated chart: cols {cols} rows {vrows}; "
      f"foot v-frac {[round(((uv_new[p][1] - pv) % TILE_V) / TILE_V, 2) for p in verts if p[1] < y0 + 0.6][:6]}")
# shift whole cols/rows by band wraps if the chart walked out of the contiguous region
while min(cols) < 6:
    u0 += 4 * TILE_U
    uv_new = {p: (u + 4 * TILE_U, v) for p, (u, v) in uv_new.items()}
    cols = [c + 4 for c in cols]
while max(cols) > 10:
    u0 -= 4 * TILE_U
    uv_new = {p: (u - 4 * TILE_U, v) for p, (u, v) in uv_new.items()}
    cols = [c - 4 for c in cols]
assert min(cols) >= 6 and max(cols) <= 10, f"chart leaves the col band: {cols}"
assert min(vrows) >= 7 and max(vrows) <= 11, f"chart leaves the row band: {vrows}"
# report the seam jumps the probe creates (must be in-law: small, or +-4 wraps)
for pi2, sm in seams.items():
    js = [(round((nuv[0] - uv_new[key][0]) / TILE_U, 1),
           round((nuv[1] - uv_new[key][1]) / TILE_V, 1)) for key, nuv, _ in sm]
    print(f"  seam to panel {pi2}: jumps {Counter(js).most_common(4)}")

# ---- apply + gates ----------------------------------------------------------------------------------
changedk = 0
for t in panel:
    for k in range(3):
        i = gtris[t][k]
        u, v = uv_new[kk(gpos[i])]
        if abs(guv[i][0] - u) > 1e-9 or abs(guv[i][1] - v) > 1e-9:
            changedk += 1
        guv[i][0], guv[i][1] = u, v
print(f"panel re-mapped: {changedk} corner uvs written")

MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
    "textures" / "res(1_24)_terrain.png"
atlas = Image.open(MOG).convert("RGBA")
AW, AH = atlas.size
APX = atlas.load()
def at_b(u_, v_):
    fx = (u_ % 1.0) * AW - 0.5
    fy = (1.0 - v_ % 1.0) * AH - 0.5
    x0, y0_ = int(math.floor(fx)), int(math.floor(fy))
    txx, tyy = fx - x0, fy - y0_
    a4 = [0.0, 0.0, 0.0, 0.0]
    for (dx2, dy2, wg) in ((0, 0, (1 - txx) * (1 - tyy)), (1, 0, txx * (1 - tyy)),
                           (0, 1, (1 - txx) * tyy), (1, 1, txx * tyy)):
        px_, py_ = min(max(x0 + dx2, 0), AW - 1), min(max(y0_ + dy2, 0), AH - 1)
        r, g2, b2, al = APX[px_, py_]
        a4[0] += r * wg; a4[1] += g2 * wg; a4[2] += b2 * wg; a4[3] += al * wg
    return a4[3], (int(a4[0]), int(a4[1]), int(a4[2]))
blank = 0
for t in panel:
    for ii in range(11):
        for jj in range(11 - ii):
            w0, w1 = ii / 10.0, jj / 10.0
            w2 = 1 - w0 - w1
            if w2 < -1e-9:
                continue
            u_ = sum(w * guv[gtris[t][k]][0] for k, w in enumerate((w0, w1, w2)))
            v_ = sum(w * guv[gtris[t][k]][1] for k, w in enumerate((w0, w1, w2)))
            aa_, rgb_ = at_b(u_, v_)
            if aa_ < 24 and sum(rgb_) < 90:
                blank += 1
print(f"atlas gate over the probed panel: blank samples = {blank} (want 0)")
assert blank == 0

# ---- offline eye: the west face at game texel scale -------------------------------------------------
LDIR = (-0.5, 0.7, -0.3)
_l = math.sqrt(sum(q * q for q in LDIR)); LDIR = tuple(q / _l for q in LDIR)
def raster(img, sx, sy, uv3, n3, W, H):
    op = img.load()
    x0, x1 = int(min(sx)), int(max(sx)) + 1
    y0_, y1 = int(min(sy)), int(max(sy)) + 1
    if x1 < 0 or x0 >= W or y1 < 0 or y0_ >= H:
        return
    d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
    if abs(d) < 1e-9:
        return
    for pyx in range(max(0, x0), min(W, x1)):
        for pyy in range(max(0, y0_), min(H, y1)):
            w0 = ((sy[1] - sy[2]) * (pyx - sx[2]) + (sx[2] - sx[1]) * (pyy - sy[2])) / d
            w1 = ((sy[2] - sy[0]) * (pyx - sx[2]) + (sx[0] - sx[2]) * (pyy - sy[2])) / d
            w2 = 1 - w0 - w1
            if w0 < 0 or w1 < 0 or w2 < 0:
                continue
            aa, rgb = at_b(w0 * uv3[0][0] + w1 * uv3[1][0] + w2 * uv3[2][0],
                           w0 * uv3[0][1] + w1 * uv3[1][1] + w2 * uv3[2][1])
            if aa < 24 and sum(rgb) < 90:
                continue
            nx = sum(w * n3[k][0] for k, w in enumerate((w0, w1, w2)))
            ny = sum(w * n3[k][1] for k, w in enumerate((w0, w1, w2)))
            nz = sum(w * n3[k][2] for k, w in enumerate((w0, w1, w2)))
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            f = 0.55 + 0.45 * max(0.0, (nx * LDIR[0] + ny * LDIR[1] + nz * LDIR[2]) / nl)
            op[pyx, pyy] = tuple(min(255, int(c * f)) for c in rgb[:3])
SCc, HWc, HHc = 44, 10.0, 12.0
RWc, RHc = int(2 * HWc * SCc), int(HHc * SCc)
img = Image.new("RGB", (RWc, RHc), (150, 178, 210))
vx, vz, rx, rz = 1.0, 0.0, 0.0, 1.0                        # camera east of point, looking... west face
rec = sorted(range(len(gtris)),
             key=lambda t2: max((gpos[i][0] - cxm) * vx + (gpos[i][2] - czm) * vz
                                for i in gtris[t2]))
for t2 in rec:
    tri = gtris[t2]
    sx = [((gpos[i][0] - cxm) * rx + (gpos[i][2] - czm) * rz + HWc) * SCc for i in tri]
    sy = [((HHc + 1.5) - gpos[i][1]) * SCc for i in tri]
    raster(img, sx, sy, [guv[i] for i in tri], [gnrm[i] for i in tri], RWc, RHc)
OUTD.mkdir(exist_ok=True)
img.save(OUTD / "uaho_probe_west.png")
print(f"-> {OUTD / 'uaho_probe_west.png'} (west face, probed panel in place)")

# ---- write ------------------------------------------------------------------------------------------
pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []
for t, tri in enumerate(gtris):
    for i in tri:
        pos.append([gpos[i][0] - BLOCK * bx, gpos[i][1], gpos[i][2] + BLOCK * (by + 1) - BLOCK])
        nrm.append(list(gnrm[i])); uv.append(list(guv[i]))
        tan.append([gtan[i][0], 0.0, 0.0, 1.0])
        flat.append(len(pos) - 1)
    tris.append([flat[-3], flat[-2], flat[-1]])
new_bm = X.BlockMesh(
    name=bm.name, disc=1, x=bx, y=by, lod="0_1", vcount=len(pos), stride=48,
    channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
    chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm, X.CH_UV: uv, X.CH_TAN: tan},
    flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])
if len(sys.argv) > 1 and sys.argv[1] == "deploy":
    BK.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(src, BK / f"{src.name}.{ts}")
    outp = M.deploy_override(new_bm, mod_folder="FF9CustomMap-world", part="Terrain")
    print(f"deployed -> {outp}")
    print("DONE -- re-run world-mirror; teleport (136.5,-1245.5) face east: the WEST face's"
          " 12-tri panel is the synthetic chart.")
else:
    print("dry run only -- re-run with 'deploy' to write.")
