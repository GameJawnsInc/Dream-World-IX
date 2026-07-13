"""UAHO FLOW ANATOMY -- the flank UV-FLOW FIELD of the real small mountain, in detail.

The carry is verbatim on the bench; per the study discipline the next step is one
component studied deep. Chosen: THE UV-FLOW FIELD. The anatomy measured Uaho ~84%
uv-continuous; every synth round mapped per-quad windows = 100% cut edges vs the real
~16% -- the cut TOPOLOGY is the never-studied variable that plausibly explains
"patchwork" even after the window mechanics were approved in-game. Unknowns:

  A. PATCH DECOMPOSITION -- maximal uv-continuous patches: how many, how big, what
     shape (one giant chart per face? strips? a single sheet?).
  B. CHART STRUCTURE -- is a patch ONE affine chart (a flat unroll: fit uv = A.p + b,
     residual in px), and how much does the per-tri gradient direction drift inside it?
  C. CUT PLACEMENT -- where the painter cuts: edge orientation (contour vs downhill),
     height/azimuth position (course boundaries? the ridge? random?), and the atlas
     JUMP across each cut (a col band wrap 9->6? a row jump? a free re-anchor?).
  D. BAND TRAVERSAL -- how the flow walks cols 6-9 / rows 10->8: window advance per
     world unit along contour and height, inside one patch.
  E. THE APEX -- who owns the peak: fan size, one patch or many, uv convergence.
  F. THE FOOT -- does the boundary course belong to the big flow patch or is the
     fringe its own chart?

Artifacts -> out/uaho_flow.json + uaho_flow_top.png + uaho_flow_views.png (patch
colors). Run from the repo root.
"""
import colorsys
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

BLK = (0, 0)
TILE_U, TILE_V = 0.0625, 0.03125
ROCK = {49, 7, 62}
GRASS = {0, 1, 2, 3, 42}
EPS = 0.0015                                               # ~3px u / ~6px v agreement
OUTD = Path(__file__).with_name("out")
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

bm = X.read_block(*BLK, disc=1, part="terrain")
V, N, U, T = bm.verts, bm.normals, bm.uvs, bm.tangents
idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
ntri = len(idx)
topo = [X.decode_id(int(round(T[i[0]][0])))["topograph"] for i in idx]
tri_pts = [[tuple(V[j]) for j in i] for i in idx]
tri_uv = [[(float(U[j][0]), float(U[j][1])) for j in i] for i in idx]

stage1 = json.loads((OUTD / "daguerreo_massif.json").read_text())
pu, pv = stage1["phase"]

# ---- the mountain component (as uaho_anatomy) ------------------------------------------------------
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
uv_at = {}                                                 # (tri, vertkey) -> uv
for t in mt:
    for k in range(3):
        uv_at[(t, kk(tri_pts[t][k]))] = tri_uv[t][k]
ys_all = [p[1] for t in mt for p in tri_pts[t]]
peak_t = max(mt, key=lambda t: max(p[1] for p in tri_pts[t]))
peak_p = max((p for p in tri_pts[peak_t]), key=lambda p: p[1])
hi_half = [t for t in mt if np.mean([p[1] for p in tri_pts[t]]) > (min(ys_all) + max(ys_all)) / 2]
cxm = float(np.mean([np.mean([p[0] for p in tri_pts[t]]) for t in hi_half]))
czm = float(np.mean([np.mean([p[2] for p in tri_pts[t]]) for t in hi_half]))
print(f"mountain: {len(mt)} tris, peak {tuple(round(v, 1) for v in peak_p)}")

# ---- A. uv-continuity edges + patch decomposition --------------------------------------------------
int_edges = []                                             # (e, t1, t2) interior rock edges
for e, ts in edge_tris.items():
    r = [t for t in ts if t in mset]
    if len(r) == 2:
        int_edges.append((e, r[0], r[1]))
cont, cuts = [], []
for e, t1, t2 in int_edges:
    d = max(abs(uv_at[(t1, e[0])][0] - uv_at[(t2, e[0])][0]),
            abs(uv_at[(t1, e[0])][1] - uv_at[(t2, e[0])][1]),
            abs(uv_at[(t1, e[1])][0] - uv_at[(t2, e[1])][0]),
            abs(uv_at[(t1, e[1])][1] - uv_at[(t2, e[1])][1]))
    (cont if d < EPS else cuts).append((e, t1, t2))
parent = {t: t for t in mt}
def find(t):
    while parent[t] != t:
        parent[t] = parent[parent[t]]
        t = parent[t]
    return t
for e, t1, t2 in cont:
    r1, r2 = find(t1), find(t2)
    if r1 != r2:
        parent[r1] = r2
patches = defaultdict(list)
for t in mt:
    patches[find(t)].append(t)
plist = sorted(patches.values(), key=len, reverse=True)
print(f"\n== A. PATCHES: {len(int_edges)} interior edges, {len(cont)} continuous "
      f"({len(cont) / len(int_edges):.0%}), {len(cuts)} cuts")
print(f"   {len(plist)} patches; sizes {[len(p) for p in plist[:12]]}"
      f"{' ...' if len(plist) > 12 else ''}")
pid_of = {}
for pi, p in enumerate(plist):
    for t in p:
        pid_of[t] = pi
for pi, p in enumerate(plist[:6]):
    cen = np.array([np.mean([q for pt in tri_pts[t] for q in [pt]], axis=0) for t in p])
    azs = [math.degrees(math.atan2(c[2] - czm, c[0] - cxm)) % 360 for c in cen]
    yy = [c[1] for c in cen]
    us = [uv for t in p for uv in tri_uv[t]]
    colspan = sorted({int(math.floor((u[0] - pu) / TILE_U)) for u in us})
    rowspan = sorted({int(math.floor((u[1] - pv) / TILE_V)) for u in us})
    print(f"   patch {pi}: {len(p)} tris, y[{min(yy):.1f},{max(yy):.1f}] "
          f"az[{min(azs):.0f},{max(azs):.0f}] cols {colspan} rows {rowspan}")

# ---- B. chart structure per big patch ---------------------------------------------------------------
print(f"\n== B. CHART STRUCTURE (affine uv = A.p + b per patch)")
for pi, p in enumerate(plist[:4]):
    rows, ru, rv = [], [], []
    for t in p:
        for k in range(3):
            rows.append([*tri_pts[t][k], 1.0])
            ru.append(tri_uv[t][k][0])
            rv.append(tri_uv[t][k][1])
    Am = np.array(rows)
    su, *_ = np.linalg.lstsq(Am, np.array(ru), rcond=None)
    sv, *_ = np.linalg.lstsq(Am, np.array(rv), rcond=None)
    res_u = (Am @ su - ru) * 2048
    res_v = (Am @ sv - rv) * 4096
    # per-tri du gradient direction drift (plan angle of grad u)
    angs = []
    for t in p:
        a, b, c = (np.array(q) for q in tri_pts[t])
        m = np.array([b - a, c - a])[:, [0, 2]]             # plan 2x2
        if abs(np.linalg.det(m)) < 1e-9:
            continue
        du = np.array([tri_uv[t][1][0] - tri_uv[t][0][0], tri_uv[t][2][0] - tri_uv[t][0][0]])
        g = np.linalg.solve(m, du)
        angs.append(math.degrees(math.atan2(g[1], g[0])) % 360)
    angs = np.array(angs)
    if len(angs):
        med = float(np.median(angs))
        drift = float(np.percentile(np.abs((angs - med + 180) % 360 - 180), 90))
    else:
        drift = 0.0
    print(f"   patch {pi}: affine residual u p90 {np.percentile(np.abs(res_u), 90):.0f}px "
          f"v p90 {np.percentile(np.abs(res_v), 90):.0f}px; grad-u plan-angle drift p90 "
          f"{drift:.0f}deg over {len(p)} tris")

# ---- C. cut placement -------------------------------------------------------------------------------
print(f"\n== C. CUTS ({len(cuts)})")
jumps = Counter()
ori_hist = Counter()
for e, t1, t2 in cuts:
    dy = abs(e[0][1] - e[1][1])
    L = math.dist(e[0], e[1])
    ori = "downhill" if dy / max(L, 1e-6) > 0.45 else "contour"
    ori_hist[ori] += 1
    du1 = uv_at[(t2, e[0])][0] - uv_at[(t1, e[0])][0]
    dv1 = uv_at[(t2, e[0])][1] - uv_at[(t1, e[0])][1]
    jumps[(round(du1 / TILE_U), round(dv1 / TILE_V))] += 1
print(f"   orientation: {dict(ori_hist)}")
print(f"   atlas jumps (tiles, du x dv): {jumps.most_common(10)}")
cut_y = [min(e[0][1], e[1][1]) for e, _, _ in cuts]
cut_az = [math.degrees(math.atan2((e[0][2] + e[1][2]) / 2 - czm,
                                  (e[0][0] + e[1][0]) / 2 - cxm)) % 360 for e, _, _ in cuts]
print(f"   cut y: med {np.median(cut_y):.1f} spread [{min(cut_y):.1f},{max(cut_y):.1f}]")
print(f"   cut az bins (30deg): "
      f"{Counter(int(a // 30) * 30 for a in cut_az).most_common(12)}")

# ---- D. band traversal inside the biggest patch -----------------------------------------------------
print(f"\n== D. BAND TRAVERSAL (patch 0)")
p0 = plist[0]
for t in p0[:0]:
    pass
gu_t, gu_h, gv_t, gv_h = [], [], [], []
for t in p0:
    a, b, c = (np.array(q) for q in tri_pts[t])
    e1, e2 = b - a, c - a
    n3 = np.cross(e1, e2)
    nl = np.linalg.norm(n3)
    if nl < 1e-9:
        continue
    n3 /= nl
    up = np.array([0.0, 1.0, 0.0])
    dh = up - n3 * n3[1]                                   # downhill (up projected)
    if np.linalg.norm(dh) < 1e-6:
        continue
    dh /= np.linalg.norm(dh)
    ct = np.cross(n3, dh)                                  # contour dir
    m = np.array([[e1 @ ct, e1 @ dh], [e2 @ ct, e2 @ dh]])
    if abs(np.linalg.det(m)) < 1e-9:
        continue
    duv1 = np.array([tri_uv[t][1][0] - tri_uv[t][0][0], tri_uv[t][2][0] - tri_uv[t][0][0]])
    dvv1 = np.array([tri_uv[t][1][1] - tri_uv[t][0][1], tri_uv[t][2][1] - tri_uv[t][0][1]])
    gu = np.linalg.solve(m, duv1)
    gv = np.linalg.solve(m, dvv1)
    gu_t.append(gu[0] * 2048); gu_h.append(gu[1] * 2048)
    gv_t.append(gv[0] * 4096); gv_h.append(gv[1] * 4096)
print(f"   grad u: along-contour med {np.median(np.abs(gu_t)):.0f}px/u, "
      f"up-surface med {np.median(np.abs(gu_h)):.0f}px/u")
print(f"   grad v: along-contour med {np.median(np.abs(gv_t)):.0f}px/u, "
      f"up-surface med {np.median(np.abs(gv_h)):.0f}px/u "
      f"(sign up-surface: {np.median(gv_h):+.0f})")

# ---- E. the apex ------------------------------------------------------------------------------------
pk = kk(peak_p)
fan = [t for t in mt if pk in [kk(q) for q in tri_pts[t]]]
fan_p = {pid_of[t] for t in fan}
fan_uv = {tuple(np.round(uv_at[(t, pk)], 4)) for t in fan}
print(f"\n== E. APEX: fan of {len(fan)} tris, patches {sorted(fan_p)}, "
      f"{len(fan_uv)} distinct uv at the peak key")
for t in fan:
    us = [q[0] for q in tri_uv[t]]
    vs = [q[1] for q in tri_uv[t]]
    print(f"   tri {t}: patch {pid_of[t]} col {int(math.floor((min(us) - pu) / TILE_U))} "
          f"row {int(math.floor((min(vs) - pv) / TILE_V))} "
          f"uv@peak ({uv_at[(t, pk)][0]:.4f},{uv_at[(t, pk)][1]:.4f})")

# ---- F. the foot ------------------------------------------------------------------------------------
foot_tris = set()
for e, ts in edge_tris.items():
    r = [t for t in ts if t in mset]
    g = [t for t in ts if t not in mset and topo[t] in GRASS]
    if len(r) == 1 and len(g) == 1:
        foot_tris.add(r[0])
fp = Counter(pid_of[t] for t in foot_tris)
print(f"\n== F. FOOT: {len(foot_tris)} boundary rock tris in patches {fp.most_common(8)}")

# ---- renders: patch-colored plan + views ------------------------------------------------------------
S2 = 8
imgs = {}
def pcol(t):
    if t in pid_of:
        pi = pid_of[t]
        if len(plist[pi]) == 1:
            return (245, 245, 245)
        r3, g3, b3 = colorsys.hsv_to_rgb((pi * 0.147) % 1.0, 0.85, 0.95)
        return (int(r3 * 255), int(g3 * 255), int(b3 * 255))
    y = float(np.mean([p[1] for p in tri_pts[t]]))
    g3 = int(60 + min(1.0, y / 20.0) * 100)
    return (g3, g3, g3 - 20)
def paint(img, t2d, color, W, H):
    px2 = img.load()
    xs = [p[0] for p in t2d]; ys3 = [p[1] for p in t2d]
    (ax, ay), (bx, by), (cx2, cy2) = t2d
    d = (by - cy2) * (ax - cx2) + (cx2 - bx) * (ay - cy2)
    if abs(d) < 1e-9:
        return
    for yy in range(max(0, int(min(ys3))), min(H - 1, int(max(ys3)) + 1) + 1):
        for xx in range(max(0, int(min(xs))), min(W - 1, int(max(xs)) + 1) + 1):
            w0 = ((by - cy2) * (xx - cx2) + (cx2 - bx) * (yy - cy2)) / d
            w1 = ((cy2 - ay) * (xx - cx2) + (ax - cx2) * (yy - cy2)) / d
            if w0 >= -0.001 and w1 >= -0.001 and (1 - w0 - w1) >= -0.001:
                px2[xx, yy] = color
img = Image.new("RGB", (64 * S2, 64 * S2), (18, 18, 26))
for t in sorted(range(ntri), key=lambda t: min(p[1] for p in tri_pts[t])):
    paint(img, [(p[0] * S2, -p[2] * S2) for p in tri_pts[t]], pcol(t), 64 * S2, 64 * S2)
OUTD.mkdir(exist_ok=True)
img.save(OUTD / "uaho_flow_top.png")
print(f"\n-> {OUTD / 'uaho_flow_top.png'}")
SC = 14
HW, HH = 30.0, 24.0
RW, RH = int(2 * HW * SC), int(HH * SC)
views = []
for azd in (90, 0, 270, 180):
    azr = math.radians(azd)
    vx, vz = math.cos(azr), math.sin(azr)
    rx, rz = -vz, vx
    img = Image.new("RGB", (RW, RH), (150, 178, 210))
    rec = sorted(range(ntri),
                 key=lambda t: max((p[0] - cxm) * vx + (p[2] - czm) * vz for p in tri_pts[t]))
    for t in rec:
        sx = [((p[0] - cxm) * rx + (p[2] - czm) * rz + HW) * SC for p in tri_pts[t]]
        sy = [(HH - p[1]) * SC for p in tri_pts[t]]
        paint(img, list(zip(sx, sy)), pcol(t), RW, RH)
    views.append(img)
sheet = Image.new("RGB", (RW, (RH + 8) * 4 - 8), (10, 10, 10))
for k, im2 in enumerate(views):
    sheet.paste(im2, (0, k * (RH + 8)))
sheet.save(OUTD / "uaho_flow_views.png")
print(f"-> {OUTD / 'uaho_flow_views.png'}")

(OUTD / "uaho_flow.json").write_text(json.dumps(dict(
    edges=len(int_edges), continuous=len(cont), cuts=len(cuts),
    patches=[len(p) for p in plist],
    jumps={f"{a},{b}": n for (a, b), n in jumps.most_common()},
    cut_orientation=dict(ori_hist),
    apex_fan=len(fan), apex_patches=sorted(fan_p), apex_uvs=len(fan_uv),
    foot_patches={str(k): v for k, v in fp.most_common()},
), indent=1))
print(f"-> {OUTD / 'uaho_flow.json'}")
