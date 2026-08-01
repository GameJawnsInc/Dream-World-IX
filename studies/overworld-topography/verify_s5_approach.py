"""ADVERSARIAL RE-MEASUREMENT of THE APPROACH-GROUND LAW (S5).

The claim under attack (wall_approach_ground.py / out/wall_approach_ground.json):
  "stock's approach ground is a SHORT LIP then a LEVEL TERRACE, never a ramp; the weld
   relief is the regional ground field sampled at the foot (inheritance ratio 0.99/1.01/
   1.37 at 8/16/32u); 0 of 45 components are pedestals; only 34% of the ground within 64u
   of a foot is at local lowland; therefore a 50.6u flat island CANNOT host the (15,14)
   donor with ANY falloff and the whole island datum must be raised."

DIFFERENT METHOD, on purpose. The claim's instrument is a per-component RAY MARCH from
foot stations, whose own limits admit that 690/936 stations die on rock inside 12u, so
every number past 16u is a survivorship subsample (n falls 45 -> 8 features). This
instrument removes stations, marching and component segmentation entirely:

  M1 THE FIELD CENSUS (station-free, no survivorship). Rasterise EVERY disc-1 lower-world
     ground triangle onto a global 2u plan grid by exact barycentric evaluation (4x denser
     than the claim's 4u cell-centre grid), rasterise rock and upper-world separately, then
     take a Euclidean DISTANCE TRANSFORM from the rock mask. Every ground cell now carries
     (distance to the nearest wall foot, height). Height is de-datumed PER BLOCK (y minus
     that 64u block's own p10 ground), which is the same "local lowland" idea with no
     component in the loop. Statistics: median excess by distance band, per-block
     regression of excess on distance, and the share of ground at lowland by distance band.
     n is ~10^5 cells over ALL rock-bearing blocks instead of 936 stations over 30 blocks.

  M2 THE POPULATION ATTACK. The claim seeds components on a 49|PLATEAU crest edge, so it
     can only see walls with plateau grass ON TOP. Re-run with that seed DROPPED (every
     topo-49 component, same y-span >= 6u / >= 12 tri keep gates) and report how much of
     stock's rock the claim never looked at.

  M3 THE COUNTEREXAMPLE HUNT. For every component in the widened population, measure on
     the 2u raster: weld relief, the ground height SPAN and lowland share inside the
     bench's own 50.6u radius, and the annulus excess profile (0-8 / 8-16 / 16-32 /
     32-56u). PEDESTAL is then tested directly and without a ratio: near excess >= 1.5u
     that resolves to <= 0.5u with a flat (<= 2.5u span) far annulus. The claim says the
     census holds ZERO of these.

  M4 THE DONOR, re-measured independently, plus whether its mesa continues past the block
     frame (the claim's unit is per-block, so a continuing mesa means its 4.36u weld line
     is a frame-cut fragment).

Read-only against stock disc-1. Writes only out/verify_s5_approach.json (+ .png).
Run: cd studies/overworld-topography && py -X utf8 verify_s5_approach.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

PLATEAU = {10, 11, 12}
ROCKY = {49, 7, 62, 58}
UPPER = PLATEAU | {36}
G = 2.0                                                     # raster cell, u  (claim used 4.0)
DONOR_BLK = (15, 14)
R_ISLAND = 50.6                                             # the bench island's grass reach
OUT = Path(__file__).with_name("out") / "verify_s5_approach.json"
PNG = Path(__file__).with_name("out") / "verify_s5_approach.png"
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))   # noqa: E731
fk = lambda p: (round(p[0], 2), round(p[1], 2), round(p[2], 2))   # noqa: E731


def pct(a, q):
    return round(float(np.percentile(a, q)), 2) if len(a) else None


# ==================================================================== pass 1: rasterise
blocks = X.list_blocks(disc=1)
NX = (max(b[0] for b in blocks) + 1) * int(64 / G)
NZ = (max(b[1] for b in blocks) + 1) * int(64 / G)
GY = np.full((NX, NZ), np.nan, dtype=np.float32)
ROCK = np.zeros((NX, NZ), dtype=bool)
UP = np.zeros((NX, NZ), dtype=bool)
BLKID = np.full((NX, NZ), -1, dtype=np.int32)

per_block_mesh = {}
n_read = n_fail = 0
n_gtri = 0
for (bx, by) in blocks:
    try:
        bm = X.read_block(bx, by, disc=1, part="terrain")
    except Exception:                                       # noqa: BLE001
        n_fail += 1
        continue
    n_read += 1
    V, T = bm.verts, bm.tangents
    ox, oz = 64.0 * bx, -64.0 * by
    ntri = len(bm.flat_index) // 3
    tri_idx = [bm.flat_index[3 * t:3 * t + 3] for t in range(ntri)]
    topo = [X.decode_id(int(round(T[idx[0]][0])))["topograph"] for idx in tri_idx]
    per_block_mesh[(bx, by)] = (V, tri_idx, topo, ox, oz)
    bid = bx * 1000 + by
    for t, idx in enumerate(tri_idx):
        a, b, c = V[idx[0]], V[idx[1]], V[idx[2]]
        wx = (a[0] + ox, b[0] + ox, c[0] + ox)
        wz = (a[2] + oz, b[2] + oz, c[2] + oz)
        i0, i1 = int(math.floor(min(wx) / G)), int(math.floor(max(wx) / G))
        j0, j1 = int(math.floor(-max(wz) / G)), int(math.floor(-min(wz) / G))
        i0, i1 = max(0, i0), min(NX - 1, i1)
        j0, j1 = max(0, j0), min(NZ - 1, j1)
        if topo[t] in ROCKY:
            ROCK[i0:i1 + 1, j0:j1 + 1] = True
            continue
        if topo[t] in UPPER:
            UP[i0:i1 + 1, j0:j1 + 1] = True
            continue
        e1x, e1z = wx[1] - wx[0], wz[1] - wz[0]
        e2x, e2z = wx[2] - wx[0], wz[2] - wz[0]
        det = e1x * e2z - e2x * e1z
        if abs(det) < 1e-9:
            continue
        n_gtri += 1
        y0, y1, y2 = a[1], b[1], c[1]
        for i in range(i0, i1 + 1):
            qx = (i + 0.5) * G
            for j in range(j0, j1 + 1):
                qz = -(j + 0.5) * G
                px, pz = qx - wx[0], qz - wz[0]
                u = (px * e2z - e2x * pz) / det
                if u < -1e-6:
                    continue
                v = (e1x * pz - px * e1z) / det
                if v < -1e-6 or u + v > 1.0 + 1e-6:
                    continue
                y = y0 + u * (y1 - y0) + v * (y2 - y0)
                if np.isnan(GY[i, j]) or y > GY[i, j]:
                    GY[i, j] = y
                    BLKID[i, j] = bid

HASG = ~np.isnan(GY)
print(f"read {n_read}/{len(blocks)} blocks ({n_fail} unreadable); {n_gtri} lower-world "
      f"ground tris rasterised at {G}u -> {int(HASG.sum())} ground cells, "
      f"{int(ROCK.sum())} rock cells, {int(UP.sum())} upper cells")

# distance (u) from every cell to the nearest ROCK cell -- the station-free "distance to a
# wall foot".  Also distance to the nearest NO-LAND cell, to separate coast effects.
DR = ndimage.distance_transform_edt(~ROCK) * G
NOLAND = ~(HASG | ROCK | UP)
DS = ndimage.distance_transform_edt(~NOLAND) * G

# per-block lowland datum: p10 of that block's own ground
low_of = {}
for bid in np.unique(BLKID[HASG]):
    ys = GY[HASG & (BLKID == bid)]
    if len(ys) >= 20:
        low_of[int(bid)] = float(np.percentile(ys, 10))
LOW = np.full((NX, NZ), np.nan, dtype=np.float32)
for bid, lv in low_of.items():
    LOW[BLKID == bid] = lv
EX = GY - LOW                                               # excess over local lowland

# ============================================================ M1 THE FIELD CENSUS
BANDS = ((0.0, 4.0), (4.0, 8.0), (8.0, 16.0), (16.0, 32.0), (32.0, 64.0))
m1 = {}
sel0 = HASG & ~np.isnan(LOW) & (DR <= 64.0)
print("\n== M1 FIELD CENSUS -- ground excess over its own block's lowland, by distance to "
      "the nearest rock cell ==")
print("   (station-free: every ground cell in every rock-bearing block, no marching, no "
      "survivorship)")
for a, b in BANDS:
    m = sel0 & (DR >= a) & (DR < b)
    e = EX[m]
    lab = f"{a:g}-{b:g}"
    m1[lab] = dict(n=int(m.sum()), med=pct(e, 50), p25=pct(e, 25), p75=pct(e, 75),
                   p90=pct(e, 90),
                   at_lowland=round(float(np.mean(e <= 0.75)), 3) if len(e) else None)
    print(f"   {lab:>7}u  n={m1[lab]['n']:7d}  excess p25 {m1[lab]['p25']:6}  MED "
          f"{m1[lab]['med']:6}  p75 {m1[lab]['p75']:6}  p90 {m1[lab]['p90']:6}   "
          f"share within 0.75u of lowland {m1[lab]['at_lowland']}")

# the same, on the OPEN-GROUND subsample only (>= 24u of land seaward of the cell) so the
# coast cannot be blamed for the decay
m1o = {}
selo = sel0 & (DS >= 24.0)
for a, b in BANDS:
    m = selo & (DR >= a) & (DR < b)
    e = EX[m]
    m1o[f"{a:g}-{b:g}"] = dict(n=int(m.sum()), med=pct(e, 50),
                               at_lowland=round(float(np.mean(e <= 0.75)), 3) if len(e) else None)
print("   interior-only control (cells >=24u from any non-land):  "
      + "  ".join(f"{k}={v['med']}({v['n']})" for k, v in m1o.items()))

# per-block regression of excess on distance-to-rock: does ground DESCEND outward?
slopes, r_s = [], []
for bid in sorted(low_of):
    m = sel0 & (BLKID == bid) & (DR <= 32.0)
    if int(m.sum()) < 200:
        continue
    d, e = DR[m].astype(float), EX[m].astype(float)
    if float(np.std(d)) < 1.0:
        continue
    sl = float(np.polyfit(d, e, 1)[0])
    slopes.append(sl)
    r_s.append(float(np.corrcoef(d, e)[0, 1]))
m1r = dict(n_blocks=len(slopes), slope_med=round(float(np.median(slopes)), 4),
           slope_p25=round(float(np.percentile(slopes, 25)), 4),
           slope_p75=round(float(np.percentile(slopes, 75)), 4),
           n_negative=int(sum(1 for s in slopes if s < 0)),
           r_med=round(float(np.median(r_s)), 3))
print(f"   per-block regression excess ~ dist(0-32u): n={m1r['n_blocks']} blocks, slope MED "
      f"{m1r['slope_med']} u/u (p25 {m1r['slope_p25']} p75 {m1r['slope_p75']}), "
      f"DESCENDING in {m1r['n_negative']}/{m1r['n_blocks']} blocks, corr MED {m1r['r_med']}")

# the decay LENGTH: at what distance does the median excess fall to half its 0-4u value,
# and where does the at-lowland share cross 50%?
prof = []
for d0 in range(0, 64, 2):
    m = sel0 & (DR >= d0) & (DR < d0 + 2)
    e = EX[m]
    prof.append((d0 + 1.0, int(m.sum()), pct(e, 50),
                 round(float(np.mean(e <= 0.75)), 3) if len(e) else None))
e_near = prof[0][2]
half = next((p[0] for p in prof if p[2] is not None and p[2] <= 0.5 * e_near), None)
cross = next((p[0] for p in prof if p[3] is not None and p[3] >= 0.5), None)
print(f"   0-2u median excess {e_near}u -> falls below half ({round(0.5 * e_near, 2)}u) at "
      f"d={half}u; the at-lowland share crosses 50% at d={cross}u")

# ============================================================ M2 the WIDENED population
def components(topo, tri_idx, V, crest_seeded):
    edge_tris = defaultdict(list)
    for t, idx in enumerate(tri_idx):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((kk(V[idx[a]]), kk(V[idx[b]]))))].append(t)
    adj = defaultdict(set)
    for e, ts in edge_tris.items():
        r = [t for t in ts if topo[t] == 49]
        for i in range(len(r)):
            for j in range(i + 1, len(r)):
                adj[r[i]].add(r[j])
                adj[r[j]].add(r[i])
    if crest_seeded:
        seeds = set()
        for e, ts in edge_tris.items():
            if len(ts) == 2:
                pair = {topo[ts[0]], topo[ts[1]]}
                if 49 in pair and pair & PLATEAU:
                    seeds.add(ts[0] if topo[ts[0]] == 49 else ts[1])
    else:
        seeds = {t for t, tp in enumerate(topo) if tp == 49}
    comp_of, seen, comps = {}, set(), {}
    for s in sorted(seeds):
        if s in seen:
            continue
        comp, st = {s}, [s]
        while st:
            t = st.pop()
            for t2 in adj[t]:
                if t2 not in comp:
                    comp.add(t2)
                    st.append(t2)
        seen |= comp
        comps[s] = sorted(comp)
        for t in comp:
            comp_of[t] = s
    keep = {}
    for root, ts in comps.items():
        ys = [V[i][1] for t in ts for i in tri_idx[t]]
        if max(ys) - min(ys) >= 6.0 and len(ts) >= 12:
            keep[root] = ts
    return keep, comp_of, edge_tris


narrow_n = wide_n = 0
narrow_blk, wide_blk = set(), set()
wide = []
for blk, (V, tri_idx, topo, ox, oz) in sorted(per_block_mesh.items()):
    if 49 not in topo:
        continue
    kn, _, _ = components(topo, tri_idx, V, True)
    kw, comp_of, edge_tris = components(topo, tri_idx, V, False)
    narrow_n += len(kn)
    wide_n += len(kw)
    if kn:
        narrow_blk.add(blk)
    if kw:
        wide_blk.add(blk)
    for root, ts in kw.items():
        foot = []
        for e, es in edge_tris.items():
            w = [t for t in es if t in comp_of and comp_of[t] == root]
            if len(w) != 1:
                continue
            o = [t for t in es if comp_of.get(t) != root]
            if not o or any(topo[t] in PLATEAU or topo[t] in ROCKY for t in o):
                continue
            for p in (e[0], e[1]):
                foot.append((p[0] + ox, p[1], p[2] + oz))
        if len(foot) < 4:
            continue
        fv = {fk(p): p for p in foot}
        wide.append(dict(blk=blk, root=root, tris=len(ts), foot=list(fv.values()),
                         ys=(min(V[i][1] for t in ts for i in tri_idx[t]),
                             max(V[i][1] for t in ts for i in tri_idx[t]))))
print(f"\n== M2 POPULATION -- the crest seed's cost ==")
print(f"   crest-seeded (the claim's population): {narrow_n} components in "
      f"{len(narrow_blk)} blocks")
print(f"   ALL topo-49 components, same keep gates: {wide_n} components in "
      f"{len(wide_blk)} blocks  ->  the claim looked at "
      f"{round(100.0 * narrow_n / max(1, wide_n), 1)}% of stock's walls, in "
      f"{round(100.0 * len(narrow_blk) / max(1, len(wide_blk)), 1)}% of its rock-bearing "
      f"blocks")
print(f"   measurable (>=4 foot edges): {len(wide)}")

# ============================================================ M3 THE COUNTEREXAMPLE HUNT
ANN = ((0.0, 8.0), (8.0, 16.0), (16.0, 32.0), (32.0, 56.0))
feats = []
for w in wide:
    fpts = w["foot"]
    ys = [p[1] for p in fpts]
    relief = round(max(ys) - min(ys), 2)
    fx = np.array([p[0] for p in fpts])
    fz = np.array([p[2] for p in fpts])
    ext = [round(float(fx.max() - fx.min()), 1), round(float(fz.max() - fz.min()), 1)]
    # raster cells within R_ISLAND of ANY foot vert
    i0 = max(0, int((fx.min() - R_ISLAND) / G) - 1)
    i1 = min(NX - 1, int((fx.max() + R_ISLAND) / G) + 1)
    j0 = max(0, int((-fz.max() - R_ISLAND) / G) - 1)
    j1 = min(NZ - 1, int((-fz.min() + R_ISLAND) / G) + 1)
    ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1), indexing="ij")
    qx = (ii + 0.5) * G
    qz = -(jj + 0.5) * G
    dmin = np.full(qx.shape, 1e9, dtype=np.float32)
    for k in range(len(fx)):
        np.minimum(dmin, np.hypot(qx - fx[k], qz - fz[k]), out=dmin)
    gy = GY[i0:i1 + 1, j0:j1 + 1]
    ok = ~np.isnan(gy)
    if int(ok.sum()) < 40:
        continue
    d_ok = dmin[ok]
    y_ok = gy[ok].astype(float)
    low = float(np.percentile(y_ok[d_ok <= 64.0], 10)) if (d_ok <= 64.0).sum() >= 20 \
        else float(np.percentile(y_ok, 10))
    host = {}
    for R in (8.0, 16.0, 32.0, R_ISLAND):
        v = y_ok[d_ok <= R]
        host[f"{R:g}"] = dict(n=int(len(v)),
                              span=round(float(v.max() - v.min()), 2) if len(v) >= 8 else None,
                              flat=round(float(np.mean(v <= low + 0.75)), 3) if len(v) >= 8 else None)
    ann = {}
    for a, b in ANN:
        v = y_ok[(d_ok >= a) & (d_ok < b)] - low
        ann[f"{a:g}-{b:g}"] = dict(n=int(len(v)), med=pct(v, 50), p90=pct(v, 90),
                                   span=round(float(v.max() - v.min()), 2) if len(v) >= 8 else None)
    near = ann["0-8"]["med"]
    far = ann["16-32"]["med"]
    far2 = ann["32-56"]
    # PEDESTAL, tested directly: a near rise that resolves back to a flat plane.
    pedestal = (near is not None and far is not None and near >= 1.5 and far <= 0.5
                and far2["span"] is not None and far2["span"] <= 2.5
                and far2["n"] >= 40)
    # can a CALM plane host it? the bench's own budget: 4.15u of span inside 50.6u
    calm = (host[f"{R_ISLAND:g}"]["span"] is not None
            and host[f"{R_ISLAND:g}"]["span"] <= 4.15)
    feats.append(dict(blk=list(w["blk"]), tris=w["tris"],
                      height=round(w["ys"][1] - w["ys"][0], 1), relief=relief,
                      weld_y=[round(min(ys), 2), round(max(ys), 2)], extent=ext,
                      foot_verts=len(fpts), lowland=round(low, 2), host=host, ann=ann,
                      pedestal=bool(pedestal), calm_host=bool(calm),
                      compact=bool(ext[0] < 63.9 and ext[1] < 63.9 and w["tris"] < 700),
                      donor=bool(w["blk"] == DONOR_BLK
                                 and w["tris"] == max(x["tris"] for x in wide
                                                      if x["blk"] == DONOR_BLK))))
print(f"\n== M3 measured {len(feats)} widened components on the 2u raster ==")
rel = [f["relief"] for f in feats]
print(f"   weld relief: n={len(rel)} p10 {pct(rel, 10)} p25 {pct(rel, 25)} MED "
      f"{pct(rel, 50)} p75 {pct(rel, 75)} max {max(rel)}   "
      f"(claim: MED 4.44 over its 45)")
donor = next((f for f in feats if f["donor"]), None)
if donor:
    print(f"   DONOR (15,14): relief {donor['relief']} y {donor['weld_y']} ext "
          f"{donor['extent']} tris {donor['tris']} -> percentile "
          f"{round(100.0 * sum(1 for v in rel if v <= donor['relief']) / len(rel), 1)}%")

for a, b in ANN:
    k = f"{a:g}-{b:g}"
    v = [f["ann"][k]["med"] for f in feats if f["ann"][k]["med"] is not None]
    print(f"   annulus {k:>7}u  n={len(v):3d} features  median excess over own lowland: "
          f"p25 {pct(v, 25)} MED {pct(v, 50)} p75 {pct(v, 75)}"
          + (f"   | DONOR {donor['ann'][k]['med']}" if donor else ""))

ped = [f for f in feats if f["pedestal"]]
calm = [f for f in feats if f["calm_host"]]
print(f"\n   PEDESTALS (near excess >=1.5u -> <=0.5u by 16-32u, far annulus flat <=2.5u): "
      f"{len(ped)}/{len(feats)}      (the claim states ZERO of 45)")
for f in sorted(ped, key=lambda f: -f["relief"])[:14]:
    print(f"      blk {str(f['blk']):9s} tris {f['tris']:4d} h {f['height']:5.1f} relief "
          f"{f['relief']:5.2f} ext {str(f['extent']):14s} excess "
          f"{f['ann']['0-8']['med']:5} -> {f['ann']['8-16']['med']:5} -> "
          f"{f['ann']['16-32']['med']:5} -> {f['ann']['32-56']['med']:5}  far span "
          f"{f['ann']['32-56']['span']}")
print(f"\n   CALM HOSTS (ground spans <= 4.15u -- the bench's own budget -- inside 50.6u of "
      f"the foot): {len(calm)}/{len(feats)}")
big = [f for f in calm if f["relief"] >= 3.0]
print(f"      of which weld relief >= 3.0u (the donor's own class): {len(big)}")
for f in sorted(big, key=lambda f: -f["relief"])[:14]:
    print(f"      blk {str(f['blk']):9s} tris {f['tris']:4d} h {f['height']:5.1f} relief "
          f"{f['relief']:5.2f} host50 span {f['host']['50.6']['span']:5} flat "
          f"{f['host']['50.6']['flat']:5} ext {str(f['extent']):14s}")
hs = [f["host"]["50.6"]["span"] for f in feats if f["host"]["50.6"]["span"] is not None]
hsc = [f["host"]["50.6"]["span"] for f in feats
       if f["compact"] and f["host"]["50.6"]["span"] is not None]
print(f"   host span inside 50.6u: n={len(hs)} min {min(hs)} p10 {pct(hs, 10)} p25 "
      f"{pct(hs, 25)} MED {pct(hs, 50)} (compact MED {pct(hsc, 50)})"
      + (f" | DONOR {donor['host']['50.6']['span']}" if donor else ""))

# ============================================================ M4 the donor, independently
print("\n== M4 THE DONOR (15,14) ==")
d4 = {}
V, tri_idx, topo, ox, oz = per_block_mesh[DONOR_BLK]
# does the mesa continue past the block frame? count 49 tris touching each frame edge
fr = Counter()
for t, idx in enumerate(tri_idx):
    if topo[t] != 49:
        continue
    for i in idx:
        x, _y, z = V[i]
        if abs(x) < 0.05:
            fr["W"] += 1
        if abs(x - 64.0) < 0.05:
            fr["E"] += 1
        if abs(z) < 0.05:
            fr["N"] += 1
        if abs(z + 64.0) < 0.05:
            fr["S"] += 1
d4["donor_frame_49_verts"] = dict(fr)
print(f"   topo-49 verts ON the donor block's frame: {dict(fr)} "
      f"(non-zero => the mesa continues into the neighbour and the claim's per-block weld "
      f"line is a FRAGMENT)")
for nb in ((14, 14), (16, 14), (15, 13), (15, 15)):
    if nb in per_block_mesh:
        _V, _ti, _tp, _a, _b = per_block_mesh[nb]
        d4[f"nb_{nb[0]}_{nb[1]}_49tris"] = sum(1 for x in _tp if x == 49)
print("   neighbour 49-tri counts: "
      + ", ".join(f"{k.replace('nb_', '').replace('_49tris', '')}={v}"
                  for k, v in d4.items() if k.startswith("nb_")))
# independent weld relief: ground verts COINCIDENT with a 49 vert
p49 = {kk(V[i]) for t, idx in enumerate(tri_idx) if topo[t] == 49 for i in idx}
gvw = [V[i] for t, idx in enumerate(tri_idx) if topo[t] not in ROCKY | UPPER
       for i in idx if kk(V[i]) in p49]
if gvw:
    gy2 = [p[1] for p in gvw]
    d4["weld_relief_coincident_verts"] = round(max(gy2) - min(gy2), 2)
    d4["weld_y_coincident"] = [round(min(gy2), 2), round(max(gy2), 2)]
    print(f"   independent weld relief (ground verts coincident with a 49 vert, whole "
          f"block): {d4['weld_relief_coincident_verts']}u, y {d4['weld_y_coincident']} "
          f"(claim 4.36u, y [3.0, 7.35])")
if donor:
    d4["raster"] = dict(relief=donor["relief"], host=donor["host"], ann=donor["ann"])

# ====================================== M5 THE SEMIVARIOGRAM -- how much does stock's ground
# change over a given plan LAG?  This is the quantity a destination sheet must actually match,
# and unlike a slope band it does not assume the change is monotone.  The bench's round-8 ramp
# is 4u over 24u, i.e. |dy| = 0.167 * lag; stock's own |dy| at each lag is measured here.
rng = np.random.default_rng(20260731)
gi, gj = np.nonzero(sel0)
print("\n== M5 SEMIVARIOGRAM -- |dy| between two ground cells LAG apart (same block) ==")
m5 = {}
for lag in (4, 8, 12, 16, 24, 32, 48):
    steps = int(round(lag / G))
    got = []
    for _ in range(6):
        ang = rng.uniform(0, 2 * math.pi, size=len(gi))
        di = np.round(steps * np.cos(ang)).astype(int)
        dj = np.round(steps * np.sin(ang)).astype(int)
        i2 = np.clip(gi + di, 0, NX - 1)
        j2 = np.clip(gj + dj, 0, NZ - 1)
        ok = sel0[i2, j2] & (BLKID[i2, j2] == BLKID[gi, gj])
        if ok.sum() < 50:
            continue
        got.append(np.abs(GY[gi[ok], gj[ok]] - GY[i2[ok], j2[ok]]).astype(float))
    v = np.concatenate(got) if got else np.array([])
    m5[str(lag)] = dict(n=int(len(v)), med=pct(v, 50), p75=pct(v, 75), p90=pct(v, 90),
                        bench=round(4.0 * min(1.0, lag / 24.0), 2))
    print(f"   lag {lag:>2}u  n={m5[str(lag)]['n']:7d}  |dy| MED {m5[str(lag)]['med']:5} "
          f"p75 {m5[str(lag)]['p75']:5} p90 {m5[str(lag)]['p90']:5}   | the bench ramp "
          f"demands {m5[str(lag)]['bench']}u over this lag  -> "
          f"{round(m5[str(lag)]['bench'] / max(0.01, m5[str(lag)]['p90']), 1)}x stock's p90")

# ====================================== M6 IS THE DONOR'S WELD RELIEF A TILT OR AN EXCURSION?
def plane_fit(pts):
    A = np.array([[p[0], p[2], 1.0] for p in pts])
    y = np.array([p[1] for p in pts])
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ sol
    return dict(tilt=round(math.degrees(math.atan(math.hypot(sol[0], sol[1]))), 2),
                resid=round(float(np.std(res)), 2),
                r2=round(1.0 - float(np.var(res)) / float(np.var(y)), 3))


dw = next(w for w in wide if w["blk"] == DONOR_BLK
          and w["tris"] == max(x["tris"] for x in wide if x["blk"] == DONOR_BLK))
pf = plane_fit(dw["foot"])
yv = np.array([p[1] for p in dw["foot"]])
lo = float(yv.min())
d4["weld_plane"] = pf
d4["weld_hist"] = {f"+{k}-{k + 1}u": int(((yv - lo >= k) & (yv - lo < k + 1)).sum())
                   for k in range(0, 6)}
d4["weld_share_within_1u"] = round(float(np.mean(yv - lo <= 1.0)), 3)
d4["weld_share_within_2u"] = round(float(np.mean(yv - lo <= 2.0)), 3)
print("\n== M6 THE DONOR WELD LINE: tilt or excursion? ==")
print(f"   plane fit: tilt {pf['tilt']} deg, r2 {pf['r2']}, resid {pf['resid']}u  "
      f"(n={len(yv)} foot verts)")
print(f"   height histogram above the weld minimum: {d4['weld_hist']}")
print(f"   share of the weld line within 1u of its own minimum: "
      f"{d4['weld_share_within_1u']};  within 2u: {d4['weld_share_within_2u']}")

# ====================================== M7 CAN A CALM HOST CARRY A BIG FOOTPRINT?
print("\n== M7 CALM HOST vs FOOTPRINT SIZE ==")
m7 = {}
for lo_e, hi_e in ((0, 24), (24, 40), (40, 64), (64, 999)):
    pop = [f for f in feats if lo_e <= max(f["extent"]) < hi_e
           and f["host"]["50.6"]["span"] is not None]
    sp = [f["host"]["50.6"]["span"] for f in pop]
    m7[f"{lo_e}-{hi_e}"] = dict(n=len(pop), min=min(sp) if sp else None, p10=pct(sp, 10),
                                med=pct(sp, 50),
                                n_calm=sum(1 for f in pop if f["calm_host"]))
    q = m7[f"{lo_e}-{hi_e}"]
    print(f"   footprint {lo_e:>2}-{hi_e:<3}u  n={q['n']:3d}  host50 span min {q['min']:5} "
          f"p10 {q['p10']:5} MED {q['med']:5}   calm (<=4.15u): {q['n_calm']}")
donorclass = [f for f in feats if max(f["extent"]) >= 40 and f["relief"] >= 3.0
              and f["host"]["50.6"]["span"] is not None]
donorclass.sort(key=lambda f: f["host"]["50.6"]["span"])
print(f"   DONOR CLASS (footprint >=40u AND weld relief >=3u): n={len(donorclass)}; "
      f"calmest hosts:")
for f in donorclass[:8]:
    print(f"      blk {str(f['blk']):9s} tris {f['tris']:4d} relief {f['relief']:5.2f} ext "
          f"{str(f['extent']):14s} host50 span {f['host']['50.6']['span']:5} flat "
          f"{f['host']['50.6']['flat']:5} ann "
          f"{f['ann']['0-8']['med']:5}->{f['ann']['16-32']['med']:5}->"
          f"{f['ann']['32-56']['med']:5}")

# ============================================================ the picture
W, H = 1180, 560
im = Image.new("RGB", (W, H), (18, 18, 22))
dr = ImageDraw.Draw(im)
L, R, TP, BT = 74, W - 250, 56, H - 58
YLO, YHI = -0.5, 4.5
sx = lambda d: L + (R - L) * d / 64.0                        # noqa: E731
sy = lambda y: BT - (BT - TP) * (y - YLO) / (YHI - YLO)      # noqa: E731
for y in np.arange(0.0, 4.6, 0.5):
    dr.line([L, sy(y), R, sy(y)], fill=(44, 44, 52))
    dr.text((L - 36, sy(y) - 6), f"{y:.1f}", fill=(140, 140, 150))
for d in range(0, 65, 8):
    dr.line([sx(d), TP, sx(d), BT], fill=(36, 36, 44))
    dr.text((sx(d) - 6, BT + 8), f"{d}", fill=(140, 140, 150))
pts = [(p[0], p[2]) for p in prof if p[2] is not None]
dr.line([q for d, y in pts for q in (sx(d), sy(y))], fill=(110, 200, 140), width=4)
bench = [(d, 4.0 * max(0.0, 1.0 - d / 24.0)) for d in range(0, 66, 2)]
dr.line([q for d, y in bench for q in (sx(d), sy(y))], fill=(230, 70, 90), width=3)
cl = [(2, 1.68), (8, 1.68), (16, 0.82), (32, 1.31), (48, 1.16), (64, 0.85)]
dr.line([q for d, y in cl for q in (sx(d), sy(y))], fill=(255, 200, 60), width=2)
for i, (lab, col) in enumerate((
        ("THIS instrument: median ground excess", (110, 200, 140)),
        ("  (all disc-1 ground cells, 2u, no stations)", (110, 200, 140)),
        ("claim's high-side median (n 33->6)", (255, 200, 60)),
        ("bench round 8 (4u over 24u)", (230, 70, 90)))):
    dr.rectangle([R + 16, TP + 24 + 22 * i, R + 38, TP + 36 + 22 * i], fill=col)
    dr.text((R + 44, TP + 24 + 22 * i), lab, fill=(225, 225, 230))
dr.text((L, 16), "THE APPROACH GROUND, station-free: median ground height above its own "
        "block's lowland vs distance to the nearest rock", fill=(235, 235, 240))
dr.text((L, 34), f"n={int(sel0.sum())} ground cells, all {len(low_of)} rock-bearing disc-1 "
        f"blocks   |   half-decay at {half}u, at-lowland share crosses 50% at {cross}u",
        fill=(160, 160, 170))
dr.text((L, H - 26), "Stock's approach ground does NOT come back down -- but it never rises "
        f"much either: median excess {e_near}u at the foot, {m1['16-32']['med']}u at 16-32u, "
        f"{m1['32-64']['med']}u at 32-64u. The size of the effect is ~1u, not 4u.",
        fill=(200, 210, 200))
PNG.parent.mkdir(exist_ok=True)
im.save(PNG)
print(f"\nrender -> {PNG}")

OUT.write_text(json.dumps(dict(
    method="station-free 2u raster + rock distance transform; widened 49-component census",
    population=dict(blocks_read=n_read, ground_tris=n_gtri, cell=G,
                    ground_cells=int(HASG.sum()), rock_cells=int(ROCK.sum()),
                    cells_in_64u=int(sel0.sum()), rock_blocks=len(low_of),
                    crest_seeded_comps=narrow_n, all49_comps=wide_n,
                    crest_blocks=len(narrow_blk), all49_blocks=len(wide_blk),
                    measured=len(feats)),
    m1_field_census=m1, m1_interior_control=m1o, m1_regression=m1r,
    m1_profile=[dict(d=p[0], n=p[1], med=p[2], at_lowland=p[3]) for p in prof],
    m1_half_decay_u=half, m1_lowland_cross_u=cross,
    m3=dict(relief_med=pct(rel, 50), n_pedestal=len(ped), n_calm_host=len(calm),
            n_calm_host_relief3=len(big),
            host50_min=min(hs), host50_med=pct(hs, 50), host50_compact_med=pct(hsc, 50),
            pedestals=[dict(blk=f["blk"], tris=f["tris"], relief=f["relief"],
                            ann={k: v["med"] for k, v in f["ann"].items()},
                            far_span=f["ann"]["32-56"]["span"]) for f in ped],
            calm_relief3=[dict(blk=f["blk"], tris=f["tris"], relief=f["relief"],
                               host50=f["host"]["50.6"]) for f in big]),
    m5_semivariogram=m5, m6_donor_weld=dict(plane=d4.get("weld_plane"),
                                            hist=d4.get("weld_hist"),
                                            within1u=d4.get("weld_share_within_1u"),
                                            within2u=d4.get("weld_share_within_2u")),
    m7_calm_by_footprint=m7,
    m7_donor_class=[dict(blk=f["blk"], tris=f["tris"], relief=f["relief"],
                         extent=f["extent"], host50=f["host"]["50.6"],
                         ann={k: v["med"] for k, v in f["ann"].items()})
                    for f in donorclass[:12]],
    m4_donor=d4, features=feats,
), indent=1))
print(f"json -> {OUT}")
