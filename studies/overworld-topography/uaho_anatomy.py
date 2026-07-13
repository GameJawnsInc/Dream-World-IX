"""UAHO ANATOMY -- the real SMALL island mountain, measured as the round-3 reference.

Two synth-massif rounds read as a mess in-game; the user pointed at the right specimen:
Uaho island (block (0,0)) carries a similarly-scaled real mountain (caveat: an Object part
is embedded in it -- identified and excluded from terrain stats). This study measures the
construction recipe our synthesis must copy, per unknown:

  A. PROFILE -- height/radius, slope by radius band (is the foot STEEP immediately, or is
     there a flat skirt like our failed round-2 ring?), cap shape.
  B. THE FOOT -- what the rock meets at ground level (grass? sand? lip?), boundary
     dihedral, boundary-course slopes and the tiles worn at the boundary.
  C. TILES -- rows/cols by height and by radius; full-tile-per-quad fraction; u/v grain
     orientation; fringe usage at the foot.
  D. MESH -- welded-sheet check (course weld share, up-facing fraction), quad plan width /
     3D height, plan compression by slope, vert spacing.
  E. RELIEF -- radial-profile residuals (jitter amplitude), azimuthal structure (ridges:
     how many, how strong), crest jaggedness.
  F. THE OBJECT -- bbox + footprint, so the synth knows what NOT to copy.

Artifacts -> out/uaho_anatomy.json + out/uaho_views.png + out/uaho_top.png +
out/uaho_cols.png / out/uaho_rows.png. Run from the repo root.
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import colorsys
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config                                # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402

BLK = (0, 0)
TILE_U, TILE_V = 0.0625, 0.03125
ROCK = {49, 7, 62}
OUTD = Path(__file__).with_name("out")
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

# ---- load ----------------------------------------------------------------------------------------
bm = X.read_block(*BLK, disc=1, part="terrain")
V, N, U, T = bm.verts, bm.normals, bm.uvs, bm.tangents
idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
ntri = len(idx)
topo = [X.decode_id(int(round(T[i[0]][0])))["topograph"] for i in idx]
print(f"Uaho terrain: {ntri} tris, topo {dict(Counter(topo))}")
try:
    om = X.read_block(*BLK, disc=1, part="object")
    oV = np.asarray(om.verts, dtype=np.float64)
    print(f"object part: {len(om.flat_index) // 3} tris, "
          f"x[{oV[:, 0].min():.1f},{oV[:, 0].max():.1f}] "
          f"y[{oV[:, 1].min():.1f},{oV[:, 1].max():.1f}] "
          f"z[{oV[:, 2].min():.1f},{oV[:, 2].max():.1f}]")
except Exception as e:
    oV = None
    print(f"object part: none ({e})")

tri_pts = [[tuple(V[j]) for j in i] for i in idx]
tri_uv = [[(float(U[j][0]), float(U[j][1])) for j in i] for i in idx]
tri_n = [[tuple(N[j]) for j in i] for i in idx]
cen = np.array([np.mean(p, axis=0) for p in tri_pts])
fn = []
for p in tri_pts:
    a, b, c = (np.array(q) for q in p)
    v3 = np.cross(b - a, c - a)
    fn.append(v3 / (np.linalg.norm(v3) or 1.0))
fn = np.array(fn)

# ---- the mountain component ----------------------------------------------------------------------
edge_tris = defaultdict(list)
for t in range(ntri):
    ps = [kk(p) for p in tri_pts[t]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        edge_tris[tuple(sorted((ps[a], ps[b])))].append(t)
adj = defaultdict(set)
for ts in edge_tris.values():
    r = [t for t in ts if topo[t] in ROCK]
    for i2 in range(len(r)):
        for j2 in range(i2 + 1, len(r)):
            adj[r[i2]].add(r[j2]); adj[r[j2]].add(r[i2])
seen, comps = set(), []
for s in [t for t in range(ntri) if topo[t] in ROCK]:
    if s in seen:
        continue
    comp = {s}; st = [s]
    while st:
        t = st.pop()
        for t2 in adj[t]:
            if t2 not in comp:
                comp.add(t2); st.append(t2)
    seen |= comp
    comps.append(comp)
comps.sort(key=len, reverse=True)
mt = sorted(comps[0])
mset = set(mt)
ys_all = [p[1] for t in mt for p in tri_pts[t]]
peak_t = max(mt, key=lambda t: max(p[1] for p in tri_pts[t]))
peak_p = max((p for p in tri_pts[peak_t]), key=lambda p: p[1])
# centre = area-weighted centroid of the high half
hi_half = [t for t in mt if cen[t][1] > (min(ys_all) + max(ys_all)) / 2]
cx, cz = float(np.mean([cen[t][0] for t in hi_half])), \
    float(np.mean([cen[t][2] for t in hi_half]))
print(f"\n== MOUNTAIN: {len(mt)} tris ({len(comps)} rock comps, next "
      f"{[len(c) for c in comps[1:4]]}), y [{min(ys_all):.1f},{max(ys_all):.1f}], "
      f"peak {tuple(round(v, 1) for v in peak_p)}, centre ({cx:.1f},{cz:.1f})")

# ---- A. profile ------------------------------------------------------------------------------------
rr = [math.hypot(c[0] - cx, c[2] - cz) for c in cen]
r_max = max(rr[t] for t in mt)
print(f"\n== A. PROFILE (r_max {r_max:.1f}u)")
for r0 in range(0, int(r_max) + 4, 4):
    sel = [t for t in mt if r0 <= rr[t] < r0 + 4]
    if not sel:
        continue
    sl = [math.degrees(math.acos(max(-1, min(1, abs(fn[t][1]))))) for t in sel]
    ysb = [cen[t][1] for t in sel]
    print(f"   r {r0:2}-{r0 + 4:2}: n {len(sel):3}  y med {np.median(ysb):5.1f} "
          f"max {max(ysb):5.1f}  slope med {np.median(sl):4.1f} p90 "
          f"{np.percentile(sl, 90):4.1f}")
up = float(np.mean([fn[t][1] > 0.3 for t in mt]))
print(f"   up-facing (ny>0.3): {up:.0%}")

# ---- B. the foot -----------------------------------------------------------------------------------
print(f"\n== B. FOOT (mountain vs non-rock edges)")
foot = defaultdict(lambda: dict(n=0, dih=[], y=[], sl=[]))
for e, ts in edge_tris.items():
    if len(ts) != 2:
        continue
    r2 = [t for t in ts if t in mset]
    o2 = [t for t in ts if t not in mset and topo[t] not in ROCK]
    if len(r2) == 1 and len(o2) == 1:
        f = foot[topo[o2[0]]]
        f["n"] += 1
        f["dih"].append(math.degrees(math.acos(max(-1, min(1, float(np.dot(
            fn[r2[0]], fn[o2[0]])))))))
        f["y"].append((e[0][1] + e[1][1]) / 2)
        f["sl"].append(math.degrees(math.acos(max(-1, min(1, abs(fn[r2[0]][1]))))))
for tp, f in sorted(foot.items(), key=lambda kv: -kv[1]["n"]):
    print(f"   vs topo {tp:3}: n {f['n']:3} y med {np.median(f['y']):5.1f} "
          f"dihedral med {np.median(f['dih']):5.1f} "
          f"ROCK-side slope med {np.median(f['sl']):4.1f}")

# ---- C+D. tiles + quads ----------------------------------------------------------------------------
uv_of = {}
for t in mt:
    for k in range(3):
        uv_of[(t, kk(tri_pts[t][k]))] = tri_uv[t][k]
e2m = defaultdict(list)
for t in mt:
    ps = [kk(p) for p in tri_pts[t]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        e2m[tuple(sorted((ps[a], ps[b])))].append(t)
paired, quads = {}, []
for e, ts in e2m.items():
    if len(ts) != 2 or ts[0] in paired or ts[1] in paired:
        continue
    vs4 = {kk(p) for t in ts for p in tri_pts[t]}
    if len(vs4) != 4:
        continue
    uvm = {kk(tri_pts[t][k]): tri_uv[t][k] for t in ts for k in range(3)}
    us = [q[0] for q in uvm.values()]
    vs2 = [q[1] for q in uvm.values()]
    pts4 = sorted(vs4, key=lambda p: p[1])
    w3 = math.hypot(pts4[3][0] - pts4[2][0], pts4[3][2] - pts4[2][2])
    h3 = (pts4[2][1] + pts4[3][1]) / 2 - (pts4[0][1] + pts4[1][1]) / 2
    paired[ts[0]] = paired[ts[1]] = len(quads)
    quads.append(dict(tris=list(ts), w=w3, h=h3,
                      du=max(us) - min(us), dv=max(vs2) - min(vs2),
                      u0=min(us), v0=min(vs2),
                      y=float(np.mean([p[1] for p in vs4]))))
lone = [t for t in mt if t not in paired]
full = [q for q in quads
        if 0.8 * TILE_U < q["du"] <= TILE_U + 1e-4 and 0.8 * TILE_V < q["dv"] <= TILE_V + 1e-4]
print(f"\n== C/D. QUADS: {len(quads)} ({2 * len(quads)}/{len(mt)} tris), lone {len(lone)}; "
      f"FULL-tile quads {len(full)} ({len(full) / max(1, len(quads)):.0%})")
print(f"   quad plan-width med {np.median([q['w'] for q in quads]):.2f} "
      f"3D-height med {np.median([q['h'] for q in quads]):.2f}")
# phase + tile ids
cu = np.array([q["u0"] for q in quads]) % TILE_U
cv = np.array([q["v0"] for q in quads]) % TILE_V
pu = float(np.bincount((cu / TILE_U * 16).astype(int) % 16, minlength=16).argmax()) \
    * TILE_U / 16
pv = float(np.bincount((cv / TILE_V * 16).astype(int) % 16, minlength=16).argmax()) \
    * TILE_V / 16
tiles_by_band = defaultdict(Counter)
y_lo = min(ys_all)
for q in quads:
    col = round((q["u0"] - pu) / TILE_U)
    row = round((q["v0"] - pv) / TILE_V)
    band = int((q["y"] - y_lo) / 4.2)
    tiles_by_band[band][(col, row)] += 1
    q["col"], q["row"] = col, row
for band in sorted(tiles_by_band):
    print(f"   y-band {band} ({y_lo + band * 4.2:.0f}-{y_lo + (band + 1) * 4.2:.0f}): "
          f"{tiles_by_band[band].most_common(8)}")
# course weld (G3)
hi_all = set()
for q in quads:
    pts4 = sorted({kk(p) for t in q["tris"] for p in tri_pts[t]}, key=lambda p: p[1])
    q["lo4"], q["hi4"] = pts4[:2], pts4[2:]
    hi_all.update(pts4[2:])
vweld = sum(1 for q in quads if any(p in hi_all for p in q["lo4"]))
print(f"   quads whose LO welds another quad's HI: {vweld}/{len(quads)} "
      f"({vweld / max(1, len(quads)):.0%})  (sheet class if high)")
mv = np.array(sorted({kk(p) for t in mt for p in tri_pts[t]}))
d2m = (mv[:, None, 0] - mv[None, :, 0]) ** 2 + (mv[:, None, 2] - mv[None, :, 2]) ** 2
np.fill_diagonal(d2m, 1e9)
nn = np.sqrt(d2m.min(axis=1))
print(f"   verts {len(mv)}: NN plan spacing med {np.median(nn):.2f} "
      f"p10 {np.percentile(nn, 10):.2f} p90 {np.percentile(nn, 90):.2f}")

# ---- E. relief -------------------------------------------------------------------------------------
print(f"\n== E. RELIEF")
vr = [math.hypot(p[0] - cx, p[2] - cz) for p in mv]
vy = mv[:, 1]
bins = np.arange(0, r_max + 2, 2)
prof = {}
for k in range(len(bins) - 1):
    sel = [i for i in range(len(mv)) if bins[k] <= vr[i] < bins[k + 1]]
    if sel:
        prof[k] = float(np.median([vy[i] for i in sel]))
res = []
for i in range(len(mv)):
    k = min(int(vr[i] / 2), len(bins) - 2)
    if k in prof:
        res.append(vy[i] - prof[k])
print(f"   radial residual (jitter): std {np.std(res):.2f} p10 "
      f"{np.percentile(res, 10):+.2f} p90 {np.percentile(res, 90):+.2f}")
nb = 24
az_max = [-1e9] * nb
for i in range(len(mv)):
    if 4.0 < vr[i] < r_max * 0.75:
        b = int((math.atan2(mv[i][2] - cz, mv[i][0] - cx) + math.pi) / (2 * math.pi) * nb) % nb
        az_max[b] = max(az_max[b], vy[i] - prof.get(min(int(vr[i] / 2),
                                                        len(bins) - 2), 0.0))
azv = [a for a in az_max if a > -1e8]
print(f"   azimuthal ridge structure (24 bins, mid-flank residual max): "
      f"spread {max(azv) - min(azv):.1f}u; bins {['%+.1f' % a for a in azv]}")

# ---- renders ---------------------------------------------------------------------------------------
gp = Path(config.find_game_path(None))
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
OUTD.mkdir(exist_ok=True)
SC = 14
HW, HH = 30.0, 24.0
RW, RH = int(2 * HW * SC), int(HH * SC)
views = []
for name, azd in (("fromS", 90), ("fromW", 0), ("fromN", 270), ("fromE", 180)):
    azr = math.radians(azd)
    vx, vz = math.cos(azr), math.sin(azr)
    rx, rz = -vz, vx
    img = Image.new("RGB", (RW, RH), (150, 178, 210))
    rec = sorted(range(ntri),
                 key=lambda t: max((p[0] - cx) * vx + (p[2] - cz) * vz for p in tri_pts[t]))
    for t in rec:
        sx = [((p[0] - cx) * rx + (p[2] - cz) * rz + HW) * SC for p in tri_pts[t]]
        sy = [(HH - p[1]) * SC for p in tri_pts[t]]
        raster(img, sx, sy, tri_uv[t], tri_n[t], RW, RH)
    views.append(img)
gap = 8
sheet = Image.new("RGB", (RW, (RH + gap) * 4 - gap), (10, 10, 10))
for k, img in enumerate(views):
    sheet.paste(img, (0, k * (RH + gap)))
sheet.save(OUTD / "uaho_views.png")
print(f"\n-> {OUTD / 'uaho_views.png'}")
S2 = 8
img = Image.new("RGB", (int(64 * S2), int(64 * S2)), (24, 40, 72))
for t in sorted(range(ntri), key=lambda t: min(p[1] for p in tri_pts[t])):
    sx = [p[0] * S2 for p in tri_pts[t]]
    sy = [-p[2] * S2 for p in tri_pts[t]]
    raster(img, sx, sy, tri_uv[t], tri_n[t], int(64 * S2), int(64 * S2))
img.save(OUTD / "uaho_top.png")
print(f"-> {OUTD / 'uaho_top.png'}")
# band renders (col / row hues) for the organization
for mode, fname in (("col", "uaho_cols.png"), ("row", "uaho_rows.png")):
    img = Image.new("RGB", (int(64 * S2), int(64 * S2)), (18, 18, 26))
    px2 = img.load()
    def paintf(tri2d, color):
        xs = [p[0] for p in tri2d]; ys3 = [p[1] for p in tri2d]
        (ax, ay), (bx, by), (cx2, cy2) = tri2d
        d = (by - cy2) * (ax - cx2) + (cx2 - bx) * (ay - cy2)
        if abs(d) < 1e-9:
            return
        for yy in range(max(0, int(min(ys3))), min(int(64 * S2) - 1, int(max(ys3)) + 1) + 1):
            for xx in range(max(0, int(min(xs))), min(int(64 * S2) - 1, int(max(xs)) + 1) + 1):
                w0 = ((by - cy2) * (xx - cx2) + (cx2 - bx) * (yy - cy2)) / d
                w1 = ((cy2 - ay) * (xx - cx2) + (ax - cx2) * (yy - cy2)) / d
                if w0 >= -0.001 and w1 >= -0.001 and (1 - w0 - w1) >= -0.001:
                    px2[xx, yy] = color
    for t in sorted(range(ntri), key=lambda t: min(p[1] for p in tri_pts[t])):
        t2d = [(p[0] * S2, -p[2] * S2) for p in tri_pts[t]]
        if t in paired:
            q = quads[paired[t]]
            k3 = (q["col"] % 16) / 16.0 if mode == "col" else (q["row"] % 32) / 32.0
            r3, g3, b3 = colorsys.hsv_to_rgb(k3, 0.85, 0.95)
            paintf(t2d, (int(r3 * 255), int(g3 * 255), int(b3 * 255)))
        elif t in mset:
            paintf(t2d, (240, 240, 240))
        else:
            y = float(np.mean([p[1] for p in tri_pts[t]]))
            g3 = int(60 + min(1.0, y / 20.0) * 120)
            paintf(t2d, (g3, g3, g3 - 20))
    img.save(OUTD / fname)
    print(f"-> {OUTD / fname}")

(OUTD / "uaho_anatomy.json").write_text(json.dumps(dict(
    tris=len(mt), y=[min(ys_all), max(ys_all)], centre=[cx, cz], r_max=r_max,
    up_facing=up, quads=len(quads), full_tile=len(full),
    vweld=[vweld, len(quads)],
    tiles_by_band={str(b): {f"{c},{r}": n for (c, r), n in tb.most_common()}
                   for b, tb in tiles_by_band.items()},
    phase=[pu, pv],
    foot={str(tp): dict(n=f["n"], y=round(float(np.median(f["y"])), 1),
                        dih=round(float(np.median(f["dih"])), 1),
                        rock_slope=round(float(np.median(f["sl"])), 1))
          for tp, f in foot.items()},
    jitter_std=float(np.std(res)),
), indent=1))
print(f"-> {OUTD / 'uaho_anatomy.json'}")
