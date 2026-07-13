"""MASSIF SYNTH v3 -- the from-scratch mountain, rebuilt to the MEASURED Uaho recipe.

Rounds 1-2 (cone + per-quad full tiles on the 4.2u lattice) read as a mess in-game; the
user pointed at Uaho (0,0) -- the only REAL mountain at this scale -- and uaho_anatomy.py
measured the actual recipe. v3 copies it:

  SHAPE -- NOT a cone: an offset main summit + a lower shoulder knoll, max()-blended
    (a natural saddle ridge); 47-degree flanks easing into a ~20-degree grass APRON
    (Uaho: steep at every radius, grass climbing ~2.5u up the foot, dihedral ~33);
    azimuthal modulation + ~1.1u positional crag jitter (Uaho residual std 1.9);
    the rock/grass line WANDERS (a noisy shoulder threshold -- grass tongues).
  MESH -- the real resolution: 2u, not the 4.2u lattice (Uaho quad width med 2.0, vert
    NN med 1.5): every tri whose cell touches the build disk splits 1->4; the
    subdivision boundary sits in FLAT grass so its colinear T-verts are exact.
  UV -- THE CONTINUOUS-FLOW DISCOVERY: Uaho has ZERO full-tile quads -- small quads
    sample sub-tile windows of a CONTINUOUS atlas flow. Cols 6-9 and rows 10->8 are
    physically contiguous in the atlas, so the whole flank maps as ONE field:
    u sweeps the 4-col band around the contour (sawtooth wrap), v scrolls up the rows
    with height. Every interior rock edge is uv-continuous -- the painted grain flows
    down the slope exactly like the real faces.
  NORMALS -- per-class local re-smooth (rock from rock, grass from grass).

Gates: census MISS=0, down-facing 0, slope envelopes (rock<=72, grass apron<=28.6),
T-boundary flatness, coast clearance via an adaptive fit (the shape scales to the
bench's measured grass reach), and THE OFFLINE EYE (4 elevations + top-down).

Bench: block (2,19), the seed-42 islet at (160,-1248). Run from the repo root:
  py studies/overworld-topography/massif_synth.py [--apply]
"""
import argparse
import json
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
S_FLANK = 1.10                                             # tan(47.7) -- Uaho med ~48
S_APRON = 0.364                                            # tan(20) -- the grass shoulder
APRON_H = 2.0                                              # grass climbs this high
JIT = 1.1                                                  # crag jitter (Uaho std 1.9 incl ridges)
SHOULDER_NOISE = 0.9                                       # the rock/grass line wanders
MAX_FLANK = 28.6
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
tris = []                                                  # world-frame flat tri records
idx0 = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
for i in idx0:
    tris.append(dict(
        w=[[bm.verts[j][0] + BLOCK * CELL[0], bm.verts[j][1],
            bm.verts[j][2] - BLOCK * CELL[1]] for j in i],
        n=[list(bm.normals[j]) for j in i],
        uv=[list(bm.uvs[j]) for j in i],
        tan=[list(bm.tangents[j]) for j in i],
        topo=X.decode_id(int(round(bm.tangents[i[0]][0])))["topograph"]))
print(f"bench: {len(tris)} tris, topo {dict(Counter(t['topo'] for t in tris))}")
assert not any(t["topo"] == 49 for t in tris), "bench not pristine -- restore the .bak first"

# ---- adaptive fit: measure the grass reach around the centre --------------------------------------
cx, cz = CENTER
avail = 1e9
for t in tris:
    if t["topo"] == 0:
        continue
    c = np.mean(t["w"], axis=0)
    avail = min(avail, math.hypot(c[0] - cx, c[2] - cz))
avail -= 1.5                                               # margin to the nearest non-grass
ys_fp = [v[1] for t in tris if t["topo"] == 0 for v in t["w"]
         if math.hypot(v[0] - cx, v[2] - cz) < avail]
y_base = float(np.median(ys_fp))
# desired shape (unscaled): main node + shoulder knoll
H_MAIN, CAP_MAIN = 9.4, 3.0
H_SHLD, CAP_SHLD = 4.4, 2.2
SHLD_OFF, SHLD_AZ = 7.5, 0.9                               # offset of the shoulder knoll
def node_reach(H, cap):
    return (H - APRON_H) / S_FLANK + cap / 2 + APRON_H / S_APRON
reach = max(node_reach(H_MAIN, CAP_MAIN),
            SHLD_OFF + node_reach(H_SHLD, CAP_SHLD)) + 1.2  # + foot wobble
scale = min(1.0, avail / reach)
H_MAIN *= scale; CAP_MAIN *= scale; H_SHLD *= scale; CAP_SHLD *= scale; SHLD_OFF *= scale
print(f"grass reach {avail:.1f}u, shape reach {reach:.1f}u -> scale {scale:.2f} "
      f"(H_main {H_MAIN:.1f})")
NODES = [(cx, cz, H_MAIN, CAP_MAIN),
         (cx + SHLD_OFF * math.cos(SHLD_AZ), cz + SHLD_OFF * math.sin(SHLD_AZ),
          H_SHLD, CAP_SHLD)]

def node_h(d, H, cap):
    """Peak H at d=0: parabola cap -> 47-deg flank -> 20-deg apron -> 0."""
    d_flank = cap / 2 + (H - APRON_H - S_FLANK * cap / 2) / S_FLANK
    d_foot = d_flank + APRON_H / S_APRON
    if d >= d_foot:
        return 0.0
    if d >= d_flank:
        return (d_foot - d) * S_APRON
    if d >= cap:
        return APRON_H + (d_flank - d) * S_FLANK
    return H - S_FLANK * d * d / (2 * cap)
def base_h(x, z):
    az = math.atan2(z - cz, x - cx)
    m = 1.0 + 0.14 * math.cos(2 * az + 0.7) + 0.09 * math.cos(5 * az + 2.1)
    best = 0.0
    for (nx2, nz2, H, cap) in NODES:
        best = max(best, node_h(math.hypot(x - nx2, z - nz2) / max(0.35, m), H, cap))
    return best
def hash01(x, z):
    return (math.sin(x * 12.9898 + z * 78.233) * 43758.5453) % 1.0

# ---- subdivision (1->4) inside the build disk ------------------------------------------------------
R_SUB = avail + 0.5
def mid(a, b):
    return [(a[k] + b[k]) / 2 for k in range(len(a))]
out_tris = []
n_sub = 0
for t in tris:
    inside = any(math.hypot(v[0] - cx, v[2] - cz) < R_SUB for v in t["w"])
    if not inside or t["topo"] != 0:
        out_tris.append(t)
        continue
    n_sub += 1
    w, n3, uv, tn = t["w"], t["n"], t["uv"], t["tan"]
    mw = [mid(w[0], w[1]), mid(w[1], w[2]), mid(w[2], w[0])]
    mn = [mid(n3[0], n3[1]), mid(n3[1], n3[2]), mid(n3[2], n3[0])]
    muv = [mid(uv[0], uv[1]), mid(uv[1], uv[2]), mid(uv[2], uv[0])]
    for tri3 in (([w[0], mw[0], mw[2]], [n3[0], mn[0], mn[2]], [uv[0], muv[0], muv[2]]),
                 ([mw[0], w[1], mw[1]], [mn[0], n3[1], mn[1]], [muv[0], uv[1], muv[1]]),
                 ([mw[2], mw[1], w[2]], [mn[2], mn[1], n3[2]], [muv[2], muv[1], uv[2]]),
                 ([mw[0], mw[1], mw[2]], [mn[0], mn[1], mn[2]], [muv[0], muv[1], muv[2]])):
        out_tris.append(dict(w=[list(p) for p in tri3[0]], n=[list(p) for p in tri3[1]],
                             uv=[list(p) for p in tri3[2]], tan=[list(tn[0])] * 3,
                             topo=0))
tris = out_tris
print(f"subdivided {n_sub} grass tris 1->4 inside r{R_SUB:.1f}: now {len(tris)} tris")

# ---- displacement ----------------------------------------------------------------------------------
for t in tris:
    if t["topo"] != 0:
        continue
    for v in t["w"]:
        hb = base_h(v[0], v[2])
        if hb <= 0.0:
            continue
        jsc = min(1.0, max(0.0, (hb - APRON_H) / 2.5))     # no jitter on the grass apron
        h = hb + JIT * (hash01(v[0], v[2]) - 0.5) * 2.0 * jsc
        v[1] += max(0.0, h)
peak = max(v[1] for t in tris for v in t["w"])
print(f"displaced: peak y {peak:.2f}")

# ---- classification: rock where the SHAPE height clears a wandering shoulder ----------------------
rock = set()
for ti, t in enumerate(tris):
    if t["topo"] != 0:
        continue
    c = np.mean(t["w"], axis=0)
    sh = APRON_H * (0.38 + 0.42 * hash01(c[0] * 0.37 + 11.3, c[2] * 0.37))
    if base_h(c[0], c[2]) > sh:
        rock.add(ti)
print(f"rock tris: {len(rock)}")

# ---- THE CONTINUOUS UV FIELD (u: the 4-col band around the contour; v: rows by height) -------------
stage1 = json.loads((OUTD / "daguerreo_massif.json").read_text())
pu, pv = stage1["phase"]
U_B0 = pu + 6 * TILE_U + 0.0005                            # col-6 left edge (tiny inset)
U_SPAN = 4 * TILE_U - 0.001
V_FOOT = pv + 10 * TILE_V + TILE_V - 0.0005                # row-10 BOTTOM edge
h_rock0 = APRON_H * 0.8                                    # the flow anchors at the rock line
# THE MEASURED UAHO DENSITY: v = one tile row per 2.6u of height (50 px/u), u = the
# 4-col band per 27.2u of contour (19 px/u). u is CYLINDRICAL PER COURSE: each 2.6u
# height band sweeps at its own mid radius, so arc density holds everywhere (a single
# radial az field compressed 10x at the apex -- the round-3 chevron/warp verdict).
V_PER_U = TILE_V / 2.6
BAND_ARC = 27.2                                            # 4 cols x 6.8u per col
course_r = {}
for ti in rock:
    for k in range(3):
        v = tris[ti]["w"][k]
        hs = base_h(v[0], v[2])
        c = int(max(0.0, hs - h_rock0) / 2.6)
        course_r.setdefault(c, []).append(math.hypot(v[0] - cx, v[2] - cz))
course_r = {c: float(np.median(rs)) for c, rs in course_r.items()}
print(f"uv field: v 50px/u, u 19px/u cylindrical per course; course radii "
      f"{ {c: round(r, 1) for c, r in sorted(course_r.items())} }")
for ti in rock:
    t = tris[ti]
    hss = [max(0.0, base_h(v[0], v[2]) - h_rock0) for v in t["w"]]
    c = int(float(np.mean(hss)) / 2.6)
    r_c = max(2.0, course_r.get(c, 3.0))
    ph = []
    for v in t["w"]:
        az = math.atan2(v[2] - cz, v[0] - cx)
        ph.append((az * r_c / BAND_ARC) % 1.0)
    if max(ph) - min(ph) > 0.5:                            # the tri straddles the band wrap:
        ph = [p + 1.0 if p < 0.5 else p for p in ph]       # unwrap so u interpolates forward
        base = math.floor(min(ph))
        ph = [p - base for p in ph]
    for k in range(3):
        v = t["w"][k]
        u_f = U_B0 + ph[k] * U_SPAN
        r = math.hypot(v[0] - cx, v[2] - cz)
        if r < 2.5:                                        # the apex: freeze u
            u_f = U_B0 + 0.5 * U_SPAN + (u_f - U_B0 - 0.5 * U_SPAN) * (r / 2.5)
        t["uv"][k][0] = u_f
        # THE SMOOTH-FIELD LAW: v follows the SMOOTH shape height at (x,z), never the
        # jittered vertex y -- jitter reversals fold the sampled strip (chevrons);
        # the crags show through SHADING (normals), the texture flows over them.
        t["uv"][k][1] = V_FOOT - hss[k] * V_PER_U
        t["tan"][k] = [ID49, 0.0, 0.0, 1.0]

# ---- normals: per-class local re-smooth ------------------------------------------------------------
acc = {"rock": defaultdict(lambda: np.zeros(3)), "grass": defaultdict(lambda: np.zeros(3))}
for ti, t in enumerate(tris):
    cls = "rock" if ti in rock else "grass" if t["topo"] == 0 else None
    if cls is None:
        continue
    a, b, c3 = (np.array(p) for p in t["w"])
    fn = np.cross(b - a, c3 - a)
    for k in range(3):
        acc[cls][kk(t["w"][k])] += fn
for ti, t in enumerate(tris):
    cls = "rock" if ti in rock else "grass" if t["topo"] == 0 else None
    if cls is None:
        continue
    near = any(math.hypot(p[0] - cx, p[2] - cz) < R_SUB for p in t["w"])
    if not near:
        continue
    for k in range(3):
        v3 = acc[cls][kk(t["w"][k])]
        L = np.linalg.norm(v3)
        if L > 1e-9:
            t["n"][k] = (v3 / L).tolist()

# ---- gates -----------------------------------------------------------------------------------------
def geo(t):
    a, b, c3 = (np.array(p) for p in t["w"])
    fn = np.cross(b - a, c3 - a)
    L = np.linalg.norm(fn) or 1.0
    return math.degrees(math.acos(max(-1, min(1, abs(fn[1]) / L)))), fn[1] / L
r_sl = [geo(tris[ti]) for ti in rock]
g_sl = [geo(t) for ti, t in enumerate(tris) if t["topo"] == 0 and ti not in rock]
assert sum(1 for _, ny in r_sl + g_sl if ny < 0) == 0, "down-facing tris"
print(f"gates: rock slope med {np.median([s for s, _ in r_sl]):.1f} "
      f"p90 {np.percentile([s for s, _ in r_sl], 90):.1f} max {max(s for s, _ in r_sl):.1f}; "
      f"grass max {max(s for s, _ in g_sl):.1f} (envelope {MAX_FLANK})")
assert max(s for s, _ in r_sl) <= 72.0 and max(s for s, _ in g_sl) <= MAX_FLANK
# T-boundary flatness: every subdivision-boundary vert must be undisplaced
for t in tris:
    for v in t["w"]:
        r = math.hypot(v[0] - cx, v[2] - cz)
        if R_SUB - 2.2 < r < R_SUB + 2.2:
            assert base_h(v[0], v[2]) == 0.0, f"displacement at the T boundary r{r:.1f}"
print("T boundary flat (all displacement well inside the subdivision disk)")

# ---- assemble + census -----------------------------------------------------------------------------
pos, nrm, uv2, tan2, flat = [], [], [], [], []
for t in tris:
    for k in range(3):
        pos.append([t["w"][k][0] - BLOCK * CELL[0], t["w"][k][1],
                    t["w"][k][2] + BLOCK * CELL[1]])
        nrm.append(list(t["n"][k]))
        uv2.append(list(t["uv"][k]))
        tan2.append(list(t["tan"][k]))
        flat.append(len(pos) - 1)
changed = {CELL: X.BlockMesh(
    name=bm.name, disc=1, x=CELL[0], y=CELL[1], lod="0_1", vcount=len(pos), stride=48,
    channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
    chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm, X.CH_UV: uv2, X.CH_TAN: tan2},
    flat_index=flat, tris=[flat[3 * t2:3 * t2 + 3] for t2 in range(len(flat) // 3)],
    raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])}
IN.census_gate(changed, disc=1)
print("census MISS=0")

# ---- THE OFFLINE EYE -------------------------------------------------------------------------------
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
SC = 16
HW, HH = 24.0, 18.0
RW, RH = int(2 * HW * SC), int(HH * SC)
views = []
for name, azd in (("fromS", 90), ("fromW", 0), ("fromN", 270), ("fromE", 180)):
    azr = math.radians(azd)
    vx, vz = math.cos(azr), math.sin(azr)
    rx, rz = -vz, vx
    img = Image.new("RGB", (RW, RH), (150, 178, 210))
    rec = sorted(range(len(tris)),
                 key=lambda t2: max((p[0] - cx) * vx + (p[2] - cz) * vz
                                    for p in tris[t2]["w"]))
    for t2 in rec:
        t = tris[t2]
        sx = [((p[0] - cx) * rx + (p[2] - cz) * rz + HW) * SC for p in t["w"]]
        sy = [(HH - p[1]) * SC for p in t["w"]]
        raster(img, sx, sy, t["uv"], t["n"], RW, RH)
    views.append(img)
gap = 8
OUTD.mkdir(exist_ok=True)
sheet = Image.new("RGB", (RW, (RH + gap) * 4 - gap), (10, 10, 10))
for k, img in enumerate(views):
    sheet.paste(img, (0, k * (RH + gap)))
sheet.save(OUTD / "massif_synth_views.png")
print(f"-> {OUTD / 'massif_synth_views.png'}")
# game-texel-scale close-up (the low-res views hid the round-3 chevrons)
SCc, HWc, HHc = 44, 9.0, 12.0
RWc, RHc = int(2 * HWc * SCc), int(HHc * SCc)
img = Image.new("RGB", (RWc, RHc), (150, 178, 210))
vx, vz, rx, rz = 1.0, 0.0, 0.0, 1.0                        # looking east at the west face
rec = sorted(range(len(tris)),
             key=lambda t2: max((p[0] - cx) * vx + (p[2] - cz) * vz for p in tris[t2]["w"]))
for t2 in rec:
    t = tris[t2]
    sx = [((p[0] - cx) * rx + (p[2] - cz) * rz + HWc) * SCc for p in t["w"]]
    sy = [((HHc + 1.5) - p[1]) * SCc for p in t["w"]]
    raster(img, sx, sy, t["uv"], t["n"], RWc, RHc)
img.save(OUTD / "massif_synth_close.png")
print(f"-> {OUTD / 'massif_synth_close.png'} (west face at game texel scale)")
S2 = 8
img = Image.new("RGB", (int(BLOCK * S2), int(BLOCK * S2)), (24, 40, 72))
for t2 in sorted(range(len(tris)), key=lambda t3: min(p[1] for p in tris[t3]["w"])):
    t = tris[t2]
    sx = [(p[0] - CELL[0] * BLOCK) * S2 for p in t["w"]]
    sy = [(-p[2] - CELL[1] * BLOCK) * S2 for p in t["w"]]
    raster(img, sx, sy, t["uv"], t["n"], int(BLOCK * S2), int(BLOCK * S2))
img.save(OUTD / "massif_synth_top.png")
print(f"-> {OUTD / 'massif_synth_top.png'}")

print(f"suggested teleport: ({math.floor(cx - avail - 3) + 0.5}, {math.floor(cz) + 0.5}) "
      f"on the west grass, face east")
if not args.apply:
    print("\nDRY RUN (no write). --apply to deploy.")
    sys.exit(0)
files = IN.deploy_changed(changed, mod_folder=args.mod_folder, disc=1)
print(f"deployed: {files}")
