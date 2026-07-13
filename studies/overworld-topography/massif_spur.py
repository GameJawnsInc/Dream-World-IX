"""MASSIF SPUR -- Stage 3: the smallest synthetic SHEET graft on the REAL massif.

The anatomy study (Stage 1) proved the massif is a welded lattice-sheet, and the probes
(Stage 2) proved cols are cosmetically free while rows are height courses. The minimal
synthesis test those laws allow: bulge ONE course of the massif's foot outward over the
grass ring -- a shoulder. Everything welds to REAL floats by construction:

  - drop the grass tris under the footprint (flood-fill anchored on the chosen foot
    segment) and the segment's real bottom-course wall quads;
  - the boundary ring = exactly the edges that lost one tri (kept|dropped edges),
    chained into one cycle: the grass hole outline (the new jagged foot -- real feet
    follow the lattice, a smoothed line would be off-language), the exposed sheet
    edge above, and the two short side welds;
  - zip the ring's low chain to its high chain with the greedy bridge walk = ONE new
    course of tris; all its verts are ring floats (positional weld = the real mechanism);
  - retile: the new course takes row 10 (its y-band IS the foot band), cols cycling
    freely in the row-10 inventory (THE COL-FREEDOM LAW), fractional UVs lerped from a
    real row-10 exemplar quad; tangents = a minted topo-49 idall; normals re-smoothed
    area-weighted over the local rock.

Gates: ring fully consumed (no new once-edges), drop completeness, the census MISS=0,
coast clearance, and THE OFFLINE EYE (an elevation render of the graft face, before /
after / marked) -- iterate offline, deploy with --apply only when it reads clean.

Run from the repo root: py studies/overworld-topography/massif_spur.py [--apply]
"""
import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config                                # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import interior as IN                  # noqa: E402
from ff9mapkit.world import mesh as M                       # noqa: E402

CELLS = [(1, 16), (2, 16), (1, 17), (2, 17)]
BLOCK = 64.0
TILE_U, TILE_V = 0.0625, 0.03125
GRASS = {0, 1, 2, 3, 42}
DEPTH = 3.5                                                # outward bulge at mid-window
RUN_MIN, RUN_MAX = 9.0, 16.0
FALLS_XZ = (119.5, -1085.0)                                # deployed falls footprint centre
OUTD = Path(__file__).with_name("out")
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true")
ap.add_argument("--mod-folder", default="FF9CustomMap-world")
args = ap.parse_args()

stage1 = json.loads((OUTD / "daguerreo_massif.json").read_text())
pu, pv = stage1["phase"]
ID49 = float(X.encode_id(topograph=49))

# ---- load the deployed cells (flat meshes) into one world-frame tri table -----------------------
gp = Path(config.find_game_path(None))
root = gp / args.mod_folder / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
tris = []                                                  # per tri: dict
bms = {}
for (bx, by) in CELLS:
    p = root / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
    if not p.exists():
        continue
    bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
    bms[(bx, by)] = bm
    idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
    for i in idx:
        w = [(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1], bm.verts[j][2] - BLOCK * by)
             for j in i]
        tris.append(dict(w=w, n=[list(bm.normals[j]) for j in i],
                         uv=[list(bm.uvs[j]) for j in i],
                         tan=[list(bm.tangents[j]) for j in i],
                         topo=X.decode_id(int(round(bm.tangents[i[0]][0])))["topograph"],
                         blk=(bx, by)))
print(f"cells loaded {sorted(bms)}; tris {len(tris)}")
for t in tris:
    a, b, c = (np.array(t["w"][k]) for k in range(3))
    fn = np.cross(b - a, c - a)
    t["fn"] = fn / (np.linalg.norm(fn) or 1.0)
    t["cen"] = (a + b + c) / 3.0

edge_tris = defaultdict(list)
for ti, t in enumerate(tris):
    ps = [kk(v) for v in t["w"]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        edge_tris[tuple(sorted((ps[a], ps[b])))].append(ti)

# ---- the foot polylines (49|grass edges, y<7) ----------------------------------------------------
foot_edges = []                                            # (e, rock_ti, grass_ti)
for e, ts in edge_tris.items():
    if len(ts) != 2 or max(e[0][1], e[1][1]) > 7.0:
        continue
    tp = {tris[ts[0]]["topo"], tris[ts[1]]["topo"]}
    if 49 in tp and tp & GRASS:
        r, g = (ts[0], ts[1]) if tris[ts[0]]["topo"] == 49 else (ts[1], ts[0])
        foot_edges.append((e, r, g))
adjp = defaultdict(list)
for ei, (e, r, g) in enumerate(foot_edges):
    adjp[e[0]].append(ei)
    adjp[e[1]].append(ei)

def outward(ei):
    e, r, g = foot_edges[ei]
    d = tris[g]["cen"] - tris[r]["cen"]
    L = math.hypot(d[0], d[2]) or 1.0
    return (d[0] / L, d[2] / L)

# chain the foot edges into polylines
seen_e = set()
polylines = []
for ei in range(len(foot_edges)):
    if ei in seen_e:
        continue
    e = foot_edges[ei][0]
    chain = [e[0], e[1]]
    seen_e.add(ei)
    for end in (0, 1):
        while True:
            tip = chain[-1] if end == 0 else chain[0]
            nxt = [x for x in adjp[tip] if x not in seen_e]
            if not nxt:
                break
            e2 = foot_edges[nxt[0]][0]
            seen_e.add(nxt[0])
            other = e2[1] if e2[0] == tip else e2[0]
            if end == 0:
                chain.append(other)
            else:
                chain.insert(0, other)
    polylines.append(chain)
print(f"foot polylines: {[len(c) for c in polylines]}")

# grass ground lookup (plan barycentric)
grass_t = [ti for ti, t in enumerate(tris) if t["topo"] in GRASS]
def grass_at(px, pz):
    for ti in grass_t:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tris[ti]["w"]
        d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
        if abs(d) < 1e-9:
            continue
        w0 = ((bz - cz) * (px - cx) + (cx - bx) * (pz - cz)) / d
        w1 = ((cz - az) * (px - cx) + (ax - cx) * (pz - cz)) / d
        if w0 >= -0.001 and w1 >= -0.001 and (1 - w0 - w1) >= -0.001:
            return w0 * ay + w1 * by + (1 - w0 - w1) * cy
    return None

# ---- pick the window -----------------------------------------------------------------------------
def edge_of(a, b):
    for ei, (e, r, g) in enumerate(foot_edges):
        if {e[0], e[1]} == {a, b}:
            return ei
    return None
best = None
why = Counter()
for chain in polylines:
    if len(chain) < 3:
        continue
    for i in range(len(chain) - 2):
        for j in range(i + 2, min(i + 6, len(chain))):
            pts = chain[i:j + 1]
            run = sum(math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][2] - pts[k][2])
                      for k in range(len(pts) - 1))
            if not (RUN_MIN <= run <= RUN_MAX):
                why["run"] += 1
                continue
            A, B = np.array(pts[0]), np.array(pts[-1])
            chord = B - A
            cl = math.hypot(chord[0], chord[2]) or 1.0
            dev = max(abs((p[0] - A[0]) * chord[2] / cl - (p[2] - A[2]) * chord[0] / cl)
                      for p in pts[1:-1])
            if dev > 1.5:
                why["dev"] += 1
                continue
            eis = [edge_of(pts[k], pts[k + 1]) for k in range(len(pts) - 1)]
            if None in eis:
                why["edge"] += 1
                continue
            ons = [outward(ei) for ei in eis]
            ox = sum(o[0] for o in ons) / len(ons)
            oz = sum(o[1] for o in ons) / len(ons)
            L = math.hypot(ox, oz) or 1.0
            ox, oz = ox / L, oz / L
            mid = (A + B) / 2.0
            # one cell with margin (footprint reaches DEPTH+1.5 outward)
            cell = (int(math.floor(pts[0][0] / BLOCK)), int(math.floor(-pts[0][2] / BLOCK)))
            ok_cell = all(int(math.floor(p[0] / BLOCK)) == cell[0] and
                          int(math.floor(-p[2] / BLOCK)) == cell[1] for p in pts)
            m = 5.5
            ok_cell &= all(m < p[0] - cell[0] * BLOCK < BLOCK - m and
                           m < -p[2] - cell[1] * BLOCK < BLOCK - m
                           for p in pts)
            if not ok_cell or cell not in bms:
                why["cell"] += 1
                continue
            if math.hypot(mid[0] - FALLS_XZ[0], mid[2] - FALLS_XZ[1]) < 15.0:
                why["falls"] += 1
                continue
            clear = True
            for st in (0.25, 0.5, 0.75):
                sp = A + (B - A) * st
                for d2 in (2.0, 4.0, 6.0, 8.0):
                    gy = grass_at(sp[0] + ox * d2, sp[2] + oz * d2)
                    if gy is None or gy > 6.5:
                        clear = False
                        break
                if not clear:
                    break
            if not clear:
                why["clear"] += 1
                continue
            score = run - dev * 2 + (2.0 if oz < -0.3 else 0.0)   # prefer south-facing
            best = best or []
            best.append(dict(pts=[tuple(p) for p in pts], eis=eis, out=(ox, oz),
                             cell=cell, run=run, dev=dev, score=score))
if not best:
    sys.exit(f"no lawful window found; rejections {dict(why)}")
best.sort(key=lambda w: -w["score"])
print(f"{len(best)} candidate windows (rejections {dict(why)}); trying by score...")
def pinp(px, pz, poly):
    ins = False
    for i2 in range(len(poly)):
        x1, z1 = poly[i2]
        x2, z2 = poly[(i2 + 1) % len(poly)]
        if (z1 > pz) != (z2 > pz):
            xx = x1 + (pz - z1) / (z2 - z1) * (x2 - x1)
            if px < xx:
                ins = not ins
    return ins
def mean_y(seg):
    return float(np.mean([p[1] for p in seg[1:-1]])) if len(seg) > 2 else 0.0
def chain_small(edges):
    """chain_ring without the >=12-point floor (a one-course graft ring is small)."""
    adj2 = defaultdict(list)
    for a, b in edges:
        adj2[a].append(b)
        adj2[b].append(a)
    bad = [p for p, l in adj2.items() if len(l) != 2]
    if bad:
        raise ValueError(f"spur ring not a simple cycle ({len(bad)} odd-degree points)")
    start = edges[0][0]
    rg = [start]
    prev = None
    while True:
        nxts = [p for p in adj2[rg[-1]] if p != prev]
        if not nxts:
            break
        prev = rg[-1]
        rg.append(nxts[0])
        if rg[-1] == start:
            rg.pop()
            break
    if len(rg) != len({*rg}) or len(rg) < 6:
        raise ValueError("spur ring degenerate")
    return rg

def attempt(win):
    """Drop + ring + split for one candidate window; (None, reason) when unlawful."""
    pts, eis = win["pts"], win["eis"]
    ox, oz = win["out"]
    cell = win["cell"]
    A, B = pts[0], pts[-1]
    npts = len(pts)
    off_pts = []
    for k in range(npts - 2, 0, -1):
        tpar = k / (npts - 1)
        d = DEPTH * math.sin(math.pi * tpar) ** 0.8
        off_pts.append((pts[k][0] + ox * d, pts[k][2] + oz * d))
    poly = [(p[0], p[2]) for p in pts] + off_pts
    drop = set()
    frontier = [foot_edges[ei][2] for ei in eis]
    while frontier:
        ti = frontier.pop()
        if ti in drop or tris[ti]["topo"] not in GRASS:
            continue
        c = tris[ti]["cen"]
        if not pinp(c[0], c[2], poly):
            continue
        drop.add(ti)
        ps = [kk(v) for v in tris[ti]["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            for t2 in edge_tris[tuple(sorted((ps[a], ps[b])))]:
                if t2 not in drop:
                    frontier.append(t2)
    n_grass = len(drop)
    for ei in eis:
        r = foot_edges[ei][1]
        drop.add(r)
        ps = [kk(v) for v in tris[r]["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            for t2 in edge_tris[tuple(sorted((ps[a], ps[b])))]:
                if t2 == r or tris[t2]["topo"] != 49 or t2 in drop:
                    continue
                vs = {kk(v) for tt in (r, t2) for v in tris[tt]["w"]}
                if len(vs) == 4:                           # the quad partner
                    drop.add(t2)
    if {tris[ti]["blk"] for ti in drop} - {cell}:
        return None, "drop leaks cells"
    ring_edges = [e for e, ts in edge_tris.items()
                  if len([t for t in ts if t not in drop]) == 1
                  and len([t for t in ts if t in drop]) == 1]
    try:
        ring = chain_small(ring_edges)
    except ValueError as exc:
        return None, str(exc)
    if kk(ring[0]) == kk(ring[-1]):
        ring = ring[:-1]
    ka, kb = kk(A), kk(B)
    ring_k = [kk(p) for p in ring]
    if ka not in ring_k or kb not in ring_k:
        return None, "window ends off the ring"
    ia, ib = ring_k.index(ka), ring_k.index(kb)
    seg1 = ring[ia:ib + 1] if ia < ib else ring[ia:] + ring[:ib + 1]
    seg2 = ring[ib:ia + 1] if ib < ia else ring[ib:] + ring[:ia + 1]
    if len(seg1) < 2 or len(seg2) < 2:
        return None, "bad ring split"
    low, high = (seg1, seg2) if mean_y(seg1) < mean_y(seg2) else (seg2, seg1)
    high = high[::-1]                                      # both now A -> B
    if kk(low[0]) != kk(high[0]):
        low = low[::-1]
    if not (kk(low[0]) == kk(high[0]) and kk(low[-1]) == kk(high[-1])):
        return None, "chain endpoints mismatch"
    lo_int = low[1:-1] or low
    hi_int = high[1:-1] or high
    sep = min(p[1] for p in hi_int) - max(p[1] for p in lo_int)
    if sep < 1.5:                                          # THE CLEAN-BOUNDARY GATE
        return None, f"jagged exposed boundary (separation {sep:.2f}u)"
    return dict(pts=pts, eis=eis, out=(ox, oz), cell=cell, poly=poly, drop=drop,
                n_grass=n_grass, ring=ring, ring_k=ring_k, low=low, high=high), None

built = None
for win in best:
    built, reason = attempt(win)
    if built:
        print(f"window OK: cell {win['cell']} run {win['run']:.1f}u dev {win['dev']:.2f} "
              f"outward ({win['out'][0]:+.2f},{win['out'][1]:+.2f})")
        break
    print(f"   window at {tuple(round(v, 1) for v in win['pts'][0])}: {reason}")
if not built:
    sys.exit("no window survives the clean-boundary gate")
pts, eis, (ox, oz), cell = built["pts"], built["eis"], built["out"], built["cell"]
A, B = pts[0], pts[-1]
poly, drop, ring, ring_k = built["poly"], built["drop"], built["ring"], built["ring_k"]
low, high = built["low"], built["high"]
n_grass_drop = built["n_grass"]
for p in pts:
    print(f"   foot {tuple(round(v, 2) for v in p)}")
print(f"drop: {n_grass_drop} grass + {len(drop) - n_grass_drop} wall; ring {len(ring)} "
      f"pts -> low {len(low)} (y~{mean_y(low):.1f}) / high {len(high)} "
      f"(y~{mean_y(high):.1f})")

# ---- zip: the one new course (chord-parameterized) -----------------------------------------------
cdx, cdz = B[0] - A[0], B[2] - A[2]
cln = math.hypot(cdx, cdz) or 1.0
cdx, cdz = cdx / cln, cdz / cln
def chord_s(px, pz):
    return (px - A[0]) * cdx + (pz - A[2]) * cdz
def profile(seg):
    ss = np.array([chord_s(p[0], p[2]) for p in seg])
    ys3 = np.array([p[1] for p in seg])
    order = np.argsort(ss)
    return ss[order], ys3[order]
plo_s, plo_y = profile(low)
phi_s, phi_y = profile(high)
new_tris = []                                              # (p3x3, key: 'zip')
i2, j2 = 0, 0
while i2 < len(low) - 1 or j2 < len(high) - 1:
    can_i = i2 < len(low) - 1
    can_j = j2 < len(high) - 1
    if can_i and can_j:
        dli = math.dist(low[i2 + 1], high[j2])
        dhj = math.dist(low[i2], high[j2 + 1])
        step_low = dli <= dhj
    else:
        step_low = can_i
    tri = [low[i2], low[i2 + 1], high[j2]] if step_low else \
        [low[i2], high[j2 + 1], high[j2]]
    if len({kk(p) for p in tri}) == 3:                     # skip the endpoint pinches
        new_tris.append(tri)
    if step_low:
        i2 += 1
    else:
        j2 += 1
# outward winding
fixed = []
for tri in new_tris:
    a, b, c = (np.array(p) for p in tri)
    fn = np.cross(b - a, c - a)
    if fn[0] * ox + fn[2] * oz < 0:
        tri = [tri[0], tri[2], tri[1]]
    fixed.append(tri)
new_tris = fixed
print(f"zip: {len(new_tris)} new course tris")

# ---- tiles + uvs (row 10, free cols, fractional from a real exemplar) ----------------------------
# real row-10 exemplar QUADS (near-full tile, proven cols only) across all loaded cells
ex = {}
wall_all = [ti for ti, t in enumerate(tris) if t["topo"] == 49 and ti not in drop]
e2w2 = defaultdict(list)
for ti in wall_all:
    ps = [kk(v) for v in tris[ti]["w"]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        e2w2[tuple(sorted((ps[a], ps[b])))].append(ti)
seenq = set()
for e, ts in e2w2.items():
    if len(ts) != 2 or ts[0] in seenq or ts[1] in seenq:
        continue
    vs4 = {kk(v) for t2 in ts for v in tris[t2]["w"]}
    if len(vs4) != 4:
        continue
    uvm = {}
    for t2 in ts:
        for k in range(3):
            uvm[kk(tris[t2]["w"][k])] = tris[t2]["uv"][k]
    us = [uv2[0] for uv2 in uvm.values()]
    vs2 = [uv2[1] for uv2 in uvm.values()]
    du2, dv2 = max(us) - min(us), max(vs2) - min(vs2)
    if not (0.8 * TILE_U < du2 <= TILE_U + 1e-4 and 0.8 * TILE_V < dv2 <= TILE_V + 1e-4):
        continue
    row = round((min(vs2) - pv) / TILE_V)
    col = round((min(us) - pu) / TILE_U)
    if row != 10 or col not in (6, 7, 8, 9) or col in ex:
        continue
    pts4 = sorted(vs4, key=lambda p: p[1])
    v_lo = float(np.mean([uvm[p][1] for p in pts4[:2]]))
    v_hi = float(np.mean([uvm[p][1] for p in pts4[2:]]))
    ex[col] = dict(u0=min(us), u1=max(us), v_lo=v_lo, v_hi=v_hi)
    seenq.update(ts)
cols_avail = sorted(ex)
assert cols_avail, "no row-10 exemplar quad found"
print(f"row-10 exemplar quads: { {c: {k: round(v2, 4) for k, v2 in d.items()}
                                  for c, d in ex.items()} }")

span = chord_s(B[0], B[2])
nwin = max(1, round(span / 4.7))
uv_new = []
for tri in new_tris:
    s_c = float(np.mean([chord_s(p[0], p[2]) for p in tri]))
    w = max(0, min(nwin - 1, int(s_c / span * nwin)))
    e2 = ex[cols_avail[w % len(cols_avail)]]
    s0, s1 = w * span / nwin, (w + 1) * span / nwin
    uvt = []
    for p in tri:
        s_p = max(0.0, min(span, chord_s(p[0], p[2])))
        su = (s_p - s0) / max(1e-9, s1 - s0)
        y_lo_l = float(np.interp(s_p, plo_s, plo_y))
        y_hi_l = float(np.interp(s_p, phi_s, phi_y))
        h = (p[1] - y_lo_l) / max(0.8, y_hi_l - y_lo_l)
        uvt.append((e2["u0"] + max(0.0, min(1.0, su)) * (e2["u1"] - e2["u0"]),
                    e2["v_lo"] + max(0.0, min(1.0, h)) * (e2["v_hi"] - e2["v_lo"])))
    uv_new.append(uvt)
for tn, (tri, uvt) in enumerate(zip(new_tris, uv_new)):
    row_s = " | ".join(f"({p[0]:.1f},{p[1]:.1f},{p[2]:.1f}) s{chord_s(p[0], p[2]):5.1f}"
                       f" uv({u2[0]:.4f},{u2[1]:.4f})" for p, u2 in zip(tri, uvt))
    print(f"   zip{tn}: {row_s}")

# ---- normals: area-weighted over local rock (kept sheet + new course) ----------------------------
acc = defaultdict(lambda: np.zeros(3))
for ti, t in enumerate(tris):
    if ti in drop or t["topo"] != 49:
        continue
    a, b, c = (np.array(t["w"][k]) for k in range(3))
    fn = np.cross(b - a, c - a)
    for k in range(3):
        acc[kk(t["w"][k])] += fn
for tri in new_tris:
    a, b, c = (np.array(p) for p in tri)
    fn = np.cross(b - a, c - a)
    for p in tri:
        acc[kk(p)] += fn
def smooth_n(p):
    v = acc[kk(p)]
    L = np.linalg.norm(v)
    return (v / L).tolist() if L > 1e-9 else [0.0, 1.0, 0.0]

# ---- gates ----------------------------------------------------------------------------------------
# ring consumed: recount edges over kept + new
cnt = defaultdict(int)
for ti, t in enumerate(tris):
    if ti in drop:
        continue
    ps = [kk(v) for v in t["w"]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        cnt[tuple(sorted((ps[a], ps[b])))] += 1
pre_once = {e for e, n in cnt.items() if n == 1}
for tri in new_tris:
    ps = [kk(p) for p in tri]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        cnt[tuple(sorted((ps[a], ps[b])))] += 1
post_once = {e for e, n in cnt.items() if n == 1}
new_once = post_once - (pre_once - {tuple(sorted((x, y))) for x, y
                                    in zip(ring_k, ring_k[1:] + ring_k[:1])})
ring_set = set()
for k in range(len(ring_k)):
    ring_set.add(tuple(sorted((ring_k[k], ring_k[(k + 1) % len(ring_k)]))))
leftover = {e for e in post_once if e in ring_set}
assert not leftover, f"ring not consumed: {len(leftover)} edges"
grew = post_once - pre_once
assert not grew, f"new once-edges introduced: {list(grew)[:3]}"
# drop completeness: no kept grass centroid inside the poly
for ti in grass_t:
    if ti not in drop:
        c = tris[ti]["cen"]
        assert not pinp(c[0], c[2], poly), f"kept grass inside the footprint at {c}"
# coast clearance: new verts far from pre-existing once-edges (the outline)
outline = [e for e in pre_once if e not in ring_set]
for tri in new_tris:
    for p in tri:
        for e in outline:
            mx, mz = (e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2
            assert (p[0] - mx) ** 2 + (p[2] - mz) ** 2 > 3.5 ** 2, \
                f"new vert {p} within 3.5u of the outline"
ys_new = [p[1] for tri in new_tris for p in tri]
print(f"gates: ring consumed, no new once-edges, drop complete, coast clear; "
      f"new course y [{min(ys_new):.1f},{max(ys_new):.1f}] (row-10 band 3.6-7.5)")

# ---- assemble the changed cell --------------------------------------------------------------------
bm0 = bms[cell]
pos, nrm, uv, tan, flat = [], [], [], [], []
def emit(p, u_, n_, t4):
    pos.append([p[0] - BLOCK * cell[0], p[1], p[2] + BLOCK * cell[1]])
    nrm.append(list(n_)); uv.append(list(u_)); tan.append(list(t4))
    flat.append(len(pos) - 1)
for ti, t in enumerate(tris):
    if t["blk"] != cell or ti in drop:
        continue
    for k in range(3):
        emit(t["w"][k], t["uv"][k], t["n"][k], t["tan"][k])
for tri, uvt in zip(new_tris, uv_new):
    for k in range(3):
        emit(tri[k], uvt[k], smooth_n(tri[k]), [ID49, 0.0, 0.0, 1.0])
changed = {cell: X.BlockMesh(
    name=bm0.name, disc=1, x=cell[0], y=cell[1], lod="0_1", vcount=len(pos), stride=48,
    channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
    chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm, X.CH_UV: uv, X.CH_TAN: tan},
    flat_index=flat, tris=[flat[3 * t2:3 * t2 + 3] for t2 in range(len(flat) // 3)],
    raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])}
IN.census_gate(changed, disc=1)
print("census MISS=0")

# ---- the offline eye: elevation render of the graft face (before/after) -------------------------
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
mid = ((A[0] + B[0]) / 2, (A[2] + B[2]) / 2)
tdir = (B[0] - A[0], B[2] - A[2])
tl = math.hypot(*tdir) or 1.0
tdir = (tdir[0] / tl, tdir[1] / tl)
SC = 26
HW, HH = 16.0, 14.0                                        # half-width u, height span
RW, RH = int(2 * HW * SC), int(HH * SC)
LDIR = (-0.5, 0.7, -0.3)
_l = math.sqrt(sum(q * q for q in LDIR)); LDIR = tuple(q / _l for q in LDIR)
def face_render(tri_list):
    img = Image.new("RGB", (RW, RH), (150, 178, 210))
    op = img.load()
    rec = []
    for (p3, uv3, n3) in tri_list:
        depth = max((p[0] - mid[0]) * ox + (p[2] - mid[1]) * oz for p in p3)
        rec.append((depth, p3, uv3, n3))
    for _, p3, uv3, n3 in sorted(rec, key=lambda r: r[0]):  # far first
        sx = [((p[0] - mid[0]) * tdir[0] + (p[2] - mid[1]) * tdir[1] + HW) * SC for p in p3]
        sy = [(HH - p[1]) * SC for p in p3]
        x0, x1 = int(min(sx)), int(max(sx)) + 1
        y0, y1 = int(min(sy)), int(max(sy)) + 1
        if x1 < 0 or x0 >= RW or y1 < 0 or y0 >= RH:
            continue
        d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
        if abs(d) < 1e-9:
            continue
        for pyx in range(max(0, x0), min(RW, x1)):
            for pyy in range(max(0, y0), min(RH, y1)):
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
    return img
def near_face(t):
    c = t["cen"] if isinstance(t, dict) else np.mean(t, axis=0)
    return abs((c[0] - mid[0]) * tdir[0] + (c[2] - mid[1]) * tdir[1]) < HW + 4 and \
        -6 < (c[0] - mid[0]) * ox + (c[2] - mid[1]) * oz < 30
before = face_render([(t["w"], t["uv"], t["n"]) for t in tris if near_face(t)])
after_list = [(t["w"], t["uv"], t["n"]) for ti, t in enumerate(tris)
              if ti not in drop and near_face(t)]
after_list += [(tri, uvt, [smooth_n(p) for p in tri])
               for tri, uvt in zip(new_tris, uv_new) if near_face(tri)]
after = face_render(after_list)
marked = after.copy()
dr = ImageDraw.Draw(marked)
for p in (A, B):
    cx = ((p[0] - mid[0]) * tdir[0] + (p[2] - mid[1]) * tdir[1] + HW) * SC
    cy = (HH - p[1]) * SC
    dr.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], outline=(255, 220, 40), width=3)
gap = 10
sheet = Image.new("RGB", (RW, RH * 3 + gap * 2), (10, 10, 10))
sheet.paste(before, (0, 0)); sheet.paste(after, (0, RH + gap))
sheet.paste(marked, (0, 2 * (RH + gap)))
OUTD.mkdir(exist_ok=True)
sheet.save(OUTD / "massif_spur_face.png")
print(f"-> {OUTD / 'massif_spur_face.png'} (top: pristine, middle: the spur, "
      f"bottom: graft ends marked)")

tpx = mid[0] + ox * 10.0
tpz = mid[1] + oz * 10.0
tpx, tpz = math.floor(tpx) + 0.5, math.floor(tpz) + 0.5
print(f"suggested look teleport: ({tpx}, {tpz}), face the massif "
      f"(bearing ({-ox:+.2f},{-oz:+.2f}))")

if not args.apply:
    print("\nDRY RUN (no write). Re-run with --apply to deploy the spur.")
    sys.exit(0)
files = IN.deploy_changed(changed, mod_folder=args.mod_folder, disc=1)
print(f"deployed: {files}")
