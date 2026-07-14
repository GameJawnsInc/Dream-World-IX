"""THE DAGUERREO MASSIF ANATOMY -- the turning-wall study, on v4's donor as ONE specimen.

Every prior wall study (plateau_edge, rock_wall_language, wall_anatomy) sampled STRAIGHT
escarpment runs in aggregate; the v3 bend-carry then died at exactly the places those
studies never measured -- turns, ridges, arm joins (THE FORM LESSON). The v4 transplant
put a real HORSESHOE massif (donor blocks (5-6,15-16), carried verbatim to island F v4)
in our own fork: the first turning/branching mountain we fully own. This study reads the
REAL donor bytes (identical to the deployed island at rot0/shift0) and asks, per unknown:

  A. TILE-OR-MURAL GATE -- does this massif speak the 128px tile language at all?
     (The BAKED-TERRAIN LAW warns some highland blocks are murals; check before assuming.)
  B. THE TURN QUESTION -- neighbor-pair atlas offsets tagged by local FACING DELTA:
     does WINDOWED CONTINUATION (46% atlas-adjacent) hold at bends, or do bends reset /
     repeat / jump the window?  Plus quad width and filler-tri density vs turn.
  C. THE STRIP-BREAK QUESTION -- within a course, side-welded quad runs (= strips):
     how long are they, and do strip ENDS cluster at bends?
  D. THE RIDGE QUESTION -- both faces are topo-49 (no grass behind): do inner/outer
     faces weld at the ridge (one component) or float?  Which tile rows cap a ridge?
  E. FEET -- outer foot (lowland grass) vs the NEW probe: the hanging-bowl rim
     (topo-13 at ~15.2): weld class + dihedral + which rows the wall uses against a
     mid-level shelf (are role bands LOCAL to a wall run or keyed to absolute height?).
  F. THE FALLS/RIVER CARVE -- do the falls sheets cover a HOLE in the Terrain wall or
     lie over continuous rock?  What tiles do falls-adjacent wall tris use?  Is the
     river channel carved below the bowl floor, and in what topo?

Artifacts -> out/daguerreo_massif.json + out/massif_cols.png + out/massif_rows.png.
Run from the repo root: py studies/overworld-topography/daguerreo_massif_anatomy.py
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
from ff9mapkit.world import extract as X                   # noqa: E402

BLOCKS = [(5, 15), (6, 15), (7, 15), (5, 16), (6, 16), (7, 16)]
BLOCK = 64.0
TILE_U, TILE_V = 0.0625, 0.03125
OUTD = Path(__file__).with_name("out")
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

# ---- load: terrain (world frame) + the water/object parts --------------------------------------
tris = []                                                  # merged world-frame terrain tris
for (bx, by) in BLOCKS:
    bm = X.read_block(bx, by, disc=1, part="terrain")
    V, N, U, T = bm.verts, bm.normals, bm.uvs, bm.tangents
    idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
    for i in idx:
        w = [(V[j][0] + BLOCK * bx, V[j][1], V[j][2] - BLOCK * by) for j in i]
        tris.append(dict(w=w, n=[tuple(N[j]) for j in i],
                         uv=[(float(U[j][0]), float(U[j][1])) for j in i],
                         topo=X.decode_id(int(round(T[i[0]][0])))["topograph"],
                         blk=(bx, by)))
parts_w = defaultdict(list)                                # falls/river/riverjoint/object tris
for (bx, by) in BLOCKS:
    for part in ("falls", "river", "riverjoint", "object"):
        try:
            pm = X.read_block(bx, by, disc=1, part=part)
        except Exception:
            continue
        idx = np.asarray(pm.flat_index, dtype=np.int64).reshape(-1, 3)
        for i in idx:
            parts_w[part].append([(pm.verts[j][0] + BLOCK * bx, pm.verts[j][1],
                                   pm.verts[j][2] - BLOCK * by) for j in i])
print(f"terrain tris {len(tris)}; parts: "
      f"{ {p: len(v) for p, v in parts_w.items()} }", flush=True)

# geometric (winding = render side = outward, per the carry-facing law) face normals
for t in tris:
    a, b, c = (np.array(t["w"][k]) for k in range(3))
    fn = np.cross(b - a, c - a)
    L = np.linalg.norm(fn) or 1.0
    t["fn"] = fn / L
    t["cen"] = (a + b + c) / 3.0

# ---- wall components (topo 49), cross-block welded ----------------------------------------------
wall = [ti for ti, t in enumerate(tris) if t["topo"] == 49]
edge_tris = defaultdict(list)
for ti, t in enumerate(tris):
    p = [kk(v) for v in t["w"]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        edge_tris[tuple(sorted((p[a], p[b])))].append(ti)
adj = defaultdict(set)
for ts in edge_tris.values():
    r = [t for t in ts if tris[t]["topo"] == 49]
    for i in range(len(r)):
        for j in range(i + 1, len(r)):
            adj[r[i]].add(r[j]); adj[r[j]].add(r[i])
comps = []
seen = set()
for s in wall:
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
massif = sorted(comps[0])
ys = [v[1] for t in massif for v in tris[t]["w"]]
print(f"\n== D. COMPONENTS: {len(comps)} wall comps, sizes {[len(c) for c in comps[:6]]}...")
print(f"   massif = comp0: {len(massif)} tris, y [{min(ys):.1f}, {max(ys):.1f}] "
      f"(ONE component => inner+outer faces edge-WELD through the ridge)" if len(ys) else "")
mset = set(massif)

# bowl centroid (topo 13) -> inner/outer face classification
bowl_c = np.mean([tris[ti]["cen"] for ti, t in enumerate(tris) if tris[ti]["topo"] == 13],
                 axis=0)
for t in massif:
    d = bowl_c - tris[t]["cen"]
    tris[t]["inner"] = (tris[t]["fn"][0] * d[0] + tris[t]["fn"][2] * d[2]) > 0
n_in = sum(1 for t in massif if tris[t]["inner"])
print(f"   bowl centroid ({bowl_c[0]:.0f},{bowl_c[2]:.0f}); faces: "
      f"{n_in} inner / {len(massif) - n_in} outer")

# ---- A. tile groups (union-find over uv-equal shared edges, 128px rect guard) -------------------
parent = {t: t for t in massif}
def find(t):
    while parent[t] != t:
        parent[t] = parent[parent[t]]
        t = parent[t]
    return t
members = {t: {t} for t in massif}
uv_of = {}                                                 # (tri, vertkey) -> uv
for t in massif:
    for k in range(3):
        uv_of[(t, kk(tris[t]["w"][k]))] = tris[t]["uv"][k]
def bbox_of(ts):
    us = [tris[t]["uv"][k][0] for t in ts for k in range(3)]
    vs = [tris[t]["uv"][k][1] for t in ts for k in range(3)]
    return min(us), min(vs), max(us), max(vs)
for e, ts in edge_tris.items():
    w2 = [t for t in ts if t in mset]
    if len(w2) != 2:
        continue
    t1, t2 = w2
    if not all(abs(uv_of[(t1, p)][0] - uv_of[(t2, p)][0]) < 1e-5 and
               abs(uv_of[(t1, p)][1] - uv_of[(t2, p)][1]) < 1e-5 for p in e):
        continue                                           # UV seam
    r1, r2 = find(t1), find(t2)
    if r1 == r2:
        continue
    u0, v0, u1, v1 = bbox_of(members[r1] | members[r2])
    if (u1 - u0) > TILE_U + 1e-4 or (v1 - v0) > TILE_V + 1e-4:
        continue                                           # the grouping guard
    parent[r2] = r1
    members[r1] |= members[r2]
    del members[r2]
group_of = {t: find(t) for t in massif}

# guard-hit rate: uv-CONTINUOUS edges the rect guard refused = mural evidence
cont, guard_hits, seams = 0, 0, 0
for e, ts in edge_tris.items():
    w2 = [t for t in ts if t in mset]
    if len(w2) != 2:
        continue
    t1, t2 = w2
    if all(abs(uv_of[(t1, p)][0] - uv_of[(t2, p)][0]) < 1e-5 and
           abs(uv_of[(t1, p)][1] - uv_of[(t2, p)][1]) < 1e-5 for p in e):
        cont += 1
        if group_of[t1] != group_of[t2]:
            guard_hits += 1
    else:
        seams += 1

corner_u, corner_v = [], []
groups = {}
for r, ts in members.items():
    u0, v0, u1, v1 = bbox_of(ts)
    corner_u += [u0, u1]; corner_v += [v0, v1]
    ys2 = [v[1] for t in ts for v in tris[t]["w"]]
    fn = np.sum([tris[t]["fn"] for t in ts], axis=0)
    L = math.hypot(fn[0], fn[2]) or 1.0
    groups[r] = dict(n=len(ts), u0=u0, v0=v0, du=u1 - u0, dv=v1 - v0,
                     ymin=min(ys2), ymax=max(ys2),
                     az=math.atan2(fn[2] / L, fn[0] / L),
                     inner=bool(np.mean([tris[t]["inner"] for t in ts]) > 0.5),
                     cen=np.mean([tris[t]["cen"] for t in ts], axis=0))
cu = np.array(corner_u) % TILE_U
cv = np.array(corner_v) % TILE_V
hu = np.histogram(cu, bins=16, range=(0, TILE_U))[0]
hv = np.histogram(cv, bins=16, range=(0, TILE_V))[0]
pu = float(np.argmax(np.bincount((cu / TILE_U * 16).astype(int) % 16,
                                 minlength=16))) * TILE_U / 16
pv = float(np.argmax(np.bincount((cv / TILE_V * 16).astype(int) % 16,
                                 minlength=16))) * TILE_V / 16
full_u = float(np.mean(np.abs([g["du"] for g in groups.values()]) > TILE_U - 0.004))
tile_ids = Counter()
for r, g in groups.items():
    g["col"] = round((g["u0"] - pu) / TILE_U)
    g["row"] = round((g["v0"] - pv) / TILE_V)
    tile_ids[(g["col"], g["row"])] += 1
peak_u = max(hu) / max(1.0, np.mean(hu))
peak_v = max(hv) / max(1.0, np.mean(hv))
print(f"\n== A. TILE-OR-MURAL GATE")
print(f"   {len(groups)} groups / {len(massif)} tris; distinct snapped tiles "
      f"{len(tile_ids)}; top8 {tile_ids.most_common(8)}")
print(f"   corner phase peakiness u {peak_u:.1f}x / v {peak_v:.1f}x (flat=1 => mural, "
      f"sharp => lattice); full-128px-u groups {full_u:.0%}")
print(f"   uv-continuous edges {cont} (rect-guard refusals {guard_hits}), seams {seams}")
print(f"   wall uv bbox: u [{min(corner_u):.3f},{max(corner_u):.3f}] "
      f"v [{min(corner_v):.3f},{max(corner_v):.3f}] "
      f"(known interior wall region: u 0.004-0.642, v 0.109-0.363)")

# ---- B. THE TURN QUESTION: neighbor atlas offsets tagged by facing delta ------------------------
pairs = []
seen_pairs = set()
for e, ts in edge_tris.items():
    w2 = [t for t in ts if t in mset]
    if len(w2) != 2:
        continue
    r1, r2 = group_of[w2[0]], group_of[w2[1]]
    if r1 == r2 or (min(r1, r2), max(r1, r2)) in seen_pairs:
        continue
    seen_pairs.add((min(r1, r2), max(r1, r2)))
    g1, g2 = groups[r1], groups[r2]
    dfa = abs((g1["az"] - g2["az"] + math.pi) % (2 * math.pi) - math.pi)
    pairs.append(dict(du=round((g2["u0"] - g1["u0"]) / TILE_U, 2),
                      dv=round((g2["v0"] - g1["v0"]) / TILE_V, 2),
                      turn=math.degrees(dfa)))
def bucket_stats(sel):
    n = len(sel)
    if not n:
        return dict(n=0)
    same = sum(1 for p in sel if abs(p["du"]) < 0.15 and abs(p["dv"]) < 0.15)
    adj1 = sum(1 for p in sel if (abs(abs(p["du"]) - 1) < 0.15 and abs(p["dv"]) < 0.15)
               or (abs(p["du"]) < 0.15 and abs(abs(p["dv"]) - 1) < 0.15))
    wrap = sum(1 for p in sel if abs(abs(p["du"]) - 3) < 0.3 and abs(p["dv"]) < 0.3)
    far = n - same - adj1 - wrap
    return dict(n=n, same=round(same / n, 2), adj=round(adj1 / n, 2),
                wrap3=round(wrap / n, 2), other=round(far / n, 2))
print(f"\n== B. THE TURN QUESTION ({len(pairs)} neighbor pairs)")
for name, lo, hi in (("straight <15deg", 0, 15), ("gentle 15-35", 15, 35),
                     ("sharp >35deg", 35, 999)):
    st = bucket_stats([p for p in pairs if lo <= p["turn"] < hi])
    print(f"   {name:16} {st}")

# ---- B2 + C. quads, courses, strips --------------------------------------------------------------
e2w = defaultdict(list)
for e, ts in edge_tris.items():
    for t in ts:
        if t in mset:
            e2w[e].append(t)
paired, quads = {}, []
for e, ts in e2w.items():
    if len(ts) != 2 or ts[0] in paired or ts[1] in paired:
        continue
    vs = {kk(v) for t in ts for v in tris[t]["w"]}
    if len(vs) != 4:
        continue
    vs = sorted(vs, key=lambda p: p[1])
    lo, hi = vs[:2], vs[2:]
    if abs(lo[0][1] - lo[1][1]) > 1.5 or abs(hi[0][1] - hi[1][1]) > 1.5:
        continue
    paired[ts[0]] = paired[ts[1]] = len(quads)
    fn = tris[ts[0]]["fn"] + tris[ts[1]]["fn"]
    L = math.hypot(fn[0], fn[2]) or 1.0
    quads.append(dict(tris=list(ts), lo=lo, hi=hi,
                      w=math.hypot(hi[1][0] - hi[0][0], hi[1][2] - hi[0][2]),
                      h=(hi[0][1] + hi[1][1]) / 2 - (lo[0][1] + lo[1][1]) / 2,
                      y=sum(p[1] for p in lo + hi) / 4,
                      az=math.atan2(fn[2] / L, fn[0] / L),
                      cen=np.mean([np.array(p) for p in lo + hi], axis=0)))
lone = [t for t in massif if t not in paired]
print(f"\n== B2. QUADS: {len(quads)} quads ({2 * len(quads)}/{len(massif)} tris = "
      f"{2 * len(quads) / max(1, len(massif)):.0%}), lone/filler {len(lone)}")

# quad side-neighbors (shared vertical edge = 2 shared verts) + local turn per quad
q_of_vert = defaultdict(set)
for qi, q in enumerate(quads):
    for p in q["lo"] + q["hi"]:
        q_of_vert[p].add(qi)
side = defaultdict(set)
for p, qs in q_of_vert.items():
    for a in qs:
        for b in qs:
            if a < b and len({*quads[a]["lo"], *quads[a]["hi"]} &
                             {*quads[b]["lo"], *quads[b]["hi"]}) >= 2 and \
                    abs(quads[a]["y"] - quads[b]["y"]) < 2.0:
                side[a].add(b); side[b].add(a)
for qi, q in enumerate(quads):
    turns = [abs((q["az"] - quads[o]["az"] + math.pi) % (2 * math.pi) - math.pi)
             for o in side[qi]]
    q["turn"] = math.degrees(max(turns)) if turns else 0.0
w_str = [q["w"] for q in quads if q["turn"] < 15]
w_bnd = [q["w"] for q in quads if q["turn"] > 35]
print(f"   quad width med: straight {np.median(w_str):.2f}u (n {len(w_str)}) vs "
      f"bend>35deg {np.median(w_bnd):.2f}u (n {len(w_bnd)})")
# filler-tri density vs local turn: nearest-quad turn at each lone tri
lone_turns = []
qcen = np.array([q["cen"] for q in quads])
for t in lone:
    c = tris[t]["cen"]
    d2 = (qcen[:, 0] - c[0]) ** 2 + (qcen[:, 2] - c[2]) ** 2
    lone_turns.append(quads[int(np.argmin(d2))]["turn"])
all_turns = [q["turn"] for q in quads]
print(f"   local-turn med: at filler tris {np.median(lone_turns):.0f}deg vs "
      f"all quads {np.median(all_turns):.0f}deg (filler>>all => filler lives at bends)")

# strips: union-find of side-welded quads within a course
sp = list(range(len(quads)))
def sfind(a):
    while sp[a] != a:
        sp[a] = sp[sp[a]]
        a = sp[a]
    return a
for a, bs in side.items():
    for b in bs:
        ra, rb = sfind(a), sfind(b)
        if ra != rb:
            sp[rb] = ra
strips = defaultdict(list)
for qi in range(len(quads)):
    strips[sfind(qi)].append(qi)
slen = sorted((len(v) for v in strips.values()), reverse=True)
end_turns = []
for ss in strips.values():
    if len(ss) < 2:
        continue
    for qi in ss:
        if len(side[qi] & set(ss)) == 1:                   # a strip END quad
            end_turns.append(quads[qi]["turn"])
print(f"\n== C. STRIPS: {len(strips)} strips, len med {np.median(slen):.0f} "
      f"p90 {np.percentile(slen, 90):.0f} max {slen[0]}")
print(f"   strip-END local turn med {np.median(end_turns):.0f}deg vs all "
      f"{np.median(all_turns):.0f}deg (ends>>all => strips BREAK at bends)")

# course-to-course vert sharing (shingle check on THIS specimen)
qys = sorted((q["y"], qi) for qi, q in enumerate(quads))
courses = []
for y, qi in qys:
    if courses and y - courses[-1]["ys"][-1] < 2.0:
        courses[-1]["ys"].append(y); courses[-1]["q"].append(qi)
    else:
        courses.append(dict(ys=[y], q=[qi]))
share = []
for ci in range(len(courses) - 1):
    hi_v = {p for qi in courses[ci]["q"] for p in quads[qi]["hi"]}
    lo_v = {p for qi in courses[ci + 1]["q"] for p in quads[qi]["lo"]}
    if hi_v:
        share.append(len(hi_v & lo_v) / len(hi_v))
print(f"   {len(courses)} y-courses; course-to-course vert share "
      f"{[round(s, 2) for s in share]} (0.0 everywhere = shingled free strips)")

# ---- D. THE RIDGE: shared wall edges that are local maxima --------------------------------------
ridge_edges = []
for e, ts in edge_tris.items():
    w2 = [t for t in ts if t in mset]
    if len(w2) != 2:
        continue
    ey = min(e[0][1], e[1][1])
    if ey < 12.0:
        continue
    opp = []
    for t in w2:
        rest = [kk(v) for v in tris[t]["w"] if kk(v) not in e]
        opp.extend(rest)
    if opp and all(p[1] < ey - 0.3 for p in opp):
        ridge_edges.append((e, w2))
rlen = sum(math.dist(e[0], e[1]) for e, _ in ridge_edges)
rys = [p[1] for e, _ in ridge_edges for p in e]
rdeg = Counter()
for e, _ in ridge_edges:
    rdeg[e[0]] += 1; rdeg[e[1]] += 1
branch = sum(1 for v, d in rdeg.items() if d >= 3)
ridge_rows = Counter()
for e, w2 in ridge_edges:
    for t in w2:
        g = groups[group_of[t]]
        ridge_rows[(g["col"], g["row"])] += 1
print(f"\n== D. RIDGE: {len(ridge_edges)} local-max edges, total {rlen:.0f}u, "
      f"y [{min(rys):.1f},{max(rys):.1f}]" if ridge_edges else "\n== D. RIDGE: none >12u")
if ridge_edges:
    print(f"   branch verts (deg>=3): {branch} (spur joins); "
          f"ridge-tile top6 {ridge_rows.most_common(6)}")
    innerouter = Counter(("inner" if tris[t]["inner"] else "outer")
                         for _, w2 in ridge_edges for t in w2)
    print(f"   ridge edges border: {dict(innerouter)} (both => the weld goes OVER the top)")

# ---- E. FEET: boundary classes, welds, dihedrals -------------------------------------------------
def face_dihedral(t1, t2):
    return math.degrees(math.acos(max(-1, min(1, float(np.dot(tris[t1]["fn"],
                                                               tris[t2]["fn"]))))))
foot = defaultdict(lambda: dict(n=0, weld=0, dih=[], rows=Counter(), y=[]))
all_wall_verts = {kk(v) for t in massif for v in tris[t]["w"]}
other_verts = {kk(v) for ti, t in enumerate(tris) if ti not in mset for v in t["w"]}
for e, ts in edge_tris.items():
    w2 = [t for t in ts if t in mset]
    o2 = [t for t in ts if t not in mset]
    if not w2 or not o2:
        continue
    tp = tris[o2[0]]["topo"]
    cls = ("grass0" if tp in (0, 1, 2, 3, 42) else
           "shelf13" if tp == 13 else "forest37" if tp == 37 else
           "river48" if tp == 48 else f"topo{tp}")
    f = foot[cls]
    f["n"] += 1
    f["weld"] += all(p in other_verts for p in e)
    f["dih"].append(face_dihedral(w2[0], o2[0]))
    g = groups[group_of[w2[0]]]
    f["rows"][g["row"]] += 1
    f["y"].append((e[0][1] + e[1][1]) / 2)
print(f"\n== E. FEET / BOUNDARIES (wall vs non-wall edges)")
for cls, f in sorted(foot.items(), key=lambda kv: -kv[1]["n"]):
    print(f"   {cls:9} n {f['n']:4} weld {f['weld'] / f['n']:.0%} "
          f"y med {np.median(f['y']):5.1f} dihedral med {np.median(f['dih']):5.1f}deg "
          f"wall rows {dict(f['rows'].most_common(4))}")

# ---- F. THE FALLS/RIVER CARVE --------------------------------------------------------------------
print(f"\n== F. FALLS / RIVER vs THE WALL")
for part in ("falls", "river"):
    pts = parts_w.get(part, [])
    if not pts:
        continue
    pcen = np.array([np.mean(p, axis=0) for p in pts])
    pys = [v[1] for p in pts for v in p]
    print(f"   {part}: {len(pts)} tris, y [{min(pys):.1f},{max(pys):.1f}]")
    near_rows = Counter()
    near_n = 0
    for t in massif:
        c = tris[t]["cen"]
        d2 = (pcen[:, 0] - c[0]) ** 2 + (pcen[:, 2] - c[2]) ** 2
        if d2.min() < 9.0:
            near_n += 1
            g = groups[group_of[t]]
            near_rows[(g["col"], g["row"])] += 1
    print(f"     wall tris within 3u: {near_n}; their tiles top6 {near_rows.most_common(6)}")
    # hole check: wall boundary once-edges (edges with NO second tri at all) under the footprint
    holes = 0
    for e, ts in edge_tris.items():
        if len(ts) != 1 or ts[0] not in mset:
            continue
        mx = (e[0][0] + e[1][0]) / 2
        mz = (e[0][2] + e[1][2]) / 2
        d2 = (pcen[:, 0] - mx) ** 2 + (pcen[:, 2] - mz) ** 2
        if d2.min() < 9.0:
            holes += 1
    print(f"     UNMATCHED wall boundary edges within 3u of {part}: {holes} "
          f"(0 => the wall is CONTINUOUS behind it; >0 => a literal hole)")
# terrain under the river: carved channel?
if "river" in parts_w:
    rcen = np.array([np.mean(p, axis=0) for p in parts_w["river"]])
    under = Counter()
    dy = []
    for ti, t in enumerate(tris):
        c = t["cen"]
        d2 = (rcen[:, 0] - c[0]) ** 2 + (rcen[:, 2] - c[2]) ** 2
        i = int(np.argmin(d2))
        if d2[i] < 2.25:
            under[t["topo"]] += 1
            dy.append(c[1] - rcen[i][1])
    print(f"   terrain under the river (<1.5u plan): topo {dict(under)}; "
          f"depth vs water med {np.median(dy):+.2f}u (negative = carved below)")

# ---- G. ROUND-2 PRECISION ------------------------------------------------------------------------
print(f"\n== G. PRECISION ROUND")
# G1. what ARE the jumps at sharp bends? (and the straight-run 'other' for contrast)
def is_lawful(p):
    return (abs(p["du"]) < 0.15 and abs(p["dv"]) < 0.15) or \
           ((abs(abs(p["du"]) - 1) < 0.15 and abs(p["dv"]) < 0.15) or
            (abs(p["du"]) < 0.15 and abs(abs(p["dv"]) - 1) < 0.15)) or \
           (abs(abs(p["du"]) - 3) < 0.3 and abs(p["dv"]) < 0.3)
sharp_o = Counter((p["du"], p["dv"]) for p in pairs if p["turn"] >= 35 and not is_lawful(p))
str_o = Counter((p["du"], p["dv"]) for p in pairs if p["turn"] < 15 and not is_lawful(p))
row_pres_s = sum(c for (du, dv), c in sharp_o.items() if abs(dv) < 0.3)
row_pres_t = sum(c for (du, dv), c in str_o.items() if abs(dv) < 0.3)
print(f"   G1 sharp-bend jumps ({sum(sharp_o.values())}): row-preserving {row_pres_s}; "
      f"top {sharp_o.most_common(8)}")
print(f"      straight 'other' ({sum(str_o.values())}): row-preserving {row_pres_t}; "
      f"top {str_o.most_common(8)}")

# G2. the falls 'hole' -- real, or block-frame key artifacts?
def on_frame(p):
    return min(p[0] % BLOCK, BLOCK - p[0] % BLOCK) < 0.05 or \
           min(-p[2] % BLOCK, BLOCK - (-p[2] % BLOCK)) < 0.05
if "falls" in parts_w:
    fcen = np.array([np.mean(p, axis=0) for p in parts_w["falls"]])
    hole_frame, hole_real, real_pts = 0, 0, []
    for e, ts in edge_tris.items():
        if len(ts) != 1 or ts[0] not in mset:
            continue
        mx, mz = (e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2
        if ((fcen[:, 0] - mx) ** 2 + (fcen[:, 2] - mz) ** 2).min() >= 9.0:
            continue
        if on_frame(e[0]) and on_frame(e[1]):
            hole_frame += 1
        else:
            hole_real += 1
            real_pts.append((round(mx, 1), round((e[0][1] + e[1][1]) / 2, 1), round(mz, 1)))
    print(f"   G2 falls boundary edges: ON-FRAME (key artifacts) {hole_frame}, "
          f"REAL hole edges {hole_real} at {real_pts[:8]}")

# G3. vertical weld, measured locally (does course N+1's top share verts with course N's bottom?)
hi_all = set()
for q in quads:
    hi_all.update(q["hi"])
vweld = sum(1 for q in quads if any(p in hi_all for p in q["lo"]))
print(f"   G3 quads whose LO verts weld to another quad's HI: {vweld}/{len(quads)} "
      f"({vweld / max(1, len(quads)):.0%}) (big escarpments measured 0%)")

# G4. the cap: up-facing massif rock (the horseshoe top is NOT a knife ridge)
caps = [t for t in massif if tris[t]["fn"][1] > 0.3]
if caps:
    cys = [v[1] for t in caps for v in tris[t]["w"]]
    crows = Counter(groups[group_of[t]]["row"] for t in caps)
    ccols = Counter(groups[group_of[t]]["col"] for t in caps)
    print(f"   G4 up-facing cap tris (ny>0.3): {len(caps)}, y [{min(cys):.1f},{max(cys):.1f}], "
          f"rows {dict(crows.most_common(6))} cols {dict(ccols.most_common(8))}")

# G5. row -> height table (the facade role structure, numerically)
rowtab = defaultdict(list)
for g in groups.values():
    rowtab[g["row"]].append((g["ymin"], g["ymax"]))
print(f"   G5 row -> y (n, ymin med, ymax med):")
for row in sorted(rowtab):
    ymins = [a for a, b in rowtab[row]]
    ymaxs = [b for a, b in rowtab[row]]
    print(f"      row {row:2}: n {len(rowtab[row]):3}  y {np.median(ymins):5.1f}"
          f" .. {np.median(ymaxs):5.1f}")

# G6. per-block massif tris (confirms the cross-frame weld carried the component)
print(f"   G6 massif per block: {dict(Counter(tris[t]['blk'] for t in massif))}")

# G7. the lattice check: is the massif the standard terrain lattice, draped steep?
mv = np.array(sorted({kk(v) for t in massif for v in tris[t]["w"]}))
d2m = (mv[:, None, 0] - mv[None, :, 0]) ** 2 + (mv[:, None, 2] - mv[None, :, 2]) ** 2
np.fill_diagonal(d2m, 1e9)
nn = np.sqrt(d2m.min(axis=1))
qh = [q["h"] for q in quads]
print(f"   G7 massif verts {len(mv)}: NN plan spacing med {np.median(nn):.2f}u "
      f"p10 {np.percentile(nn, 10):.2f} p90 {np.percentile(nn, 90):.2f} "
      f"(standard lattice ~4.2u); quad course height med {np.median(qh):.2f}u")

# ---- renders -------------------------------------------------------------------------------------
S = 4
x0, x1 = 5 * 64.0, 8 * 64.0
z1, z0 = -15 * 64.0, -17 * 64.0
W, H = int((x1 - x0) * S), int((z1 - z0) * S)
def paint(px, tri2d, color):
    xs = [p[0] for p in tri2d]; ys3 = [p[1] for p in tri2d]
    xmin, xmax = max(0, int(min(xs))), min(W - 1, int(max(xs)) + 1)
    ymin, ymax = max(0, int(min(ys3))), min(H - 1, int(max(ys3)) + 1)
    (ax, ay), (bx2, by2), (cx, cy) = tri2d
    d = (by2 - cy) * (ax - cx) + (cx - bx2) * (ay - cy)
    if abs(d) < 1e-9:
        return
    for yy in range(ymin, ymax + 1):
        for xx in range(xmin, xmax + 1):
            w0 = ((by2 - cy) * (xx - cx) + (cx - bx2) * (yy - cy)) / d
            w1 = ((cy - ay) * (xx - cx) + (ax - cx) * (yy - cy)) / d
            if w0 >= -0.001 and w1 >= -0.001 and (1 - w0 - w1) >= -0.001:
                px[xx, yy] = color
def to2d(v):
    return ((v[0] - x0) * S, (z1 - v[2]) * S)
for mode, fname in (("col", "massif_cols.png"), ("row", "massif_rows.png")):
    img = Image.new("RGB", (W, H), (18, 18, 26))
    px = img.load()
    order = sorted(range(len(tris)), key=lambda ti: min(v[1] for v in tris[ti]["w"]))
    for ti in order:
        t = tris[ti]
        t2 = [to2d(v) for v in t["w"]]
        if ti in mset:
            g = groups[group_of[ti]]
            k = (g["col"] % 16) / 16.0 if mode == "col" else (g["row"] % 32) / 32.0
            r, g2, b = colorsys.hsv_to_rgb(k, 0.85, 0.95)
            paint(px, t2, (int(r * 255), int(g2 * 255), int(b * 255)))
        else:
            y = float(np.mean([v[1] for v in t["w"]]))
            g3 = int(60 + min(1.0, y / 30.0) * 120)
            paint(px, t2, (g3, g3, g3 - 20))
    for part, col in (("river", (40, 90, 230)), ("riverjoint", (40, 90, 230)),
                      ("falls", (140, 200, 255)), ("object", (240, 160, 40))):
        for p in parts_w.get(part, []):
            paint(px, [to2d(v) for v in p], col)
    OUTD.mkdir(exist_ok=True)
    img.save(OUTD / fname)
    print(f"-> {OUTD / fname}")

OUTD.mkdir(exist_ok=True)
(OUTD / "daguerreo_massif.json").write_text(json.dumps(dict(
    massif_tris=len(massif), comps=[len(c) for c in comps], groups=len(groups),
    tiles={f"{c},{r}": n for (c, r), n in tile_ids.items()},
    phase=[pu, pv], corner_peak=[peak_u, peak_v],
    pairs=pairs, quad_n=len(quads), lone=len(lone),
    strips=slen, course_share=[round(s, 3) for s in share],
    ridge=dict(edges=len(ridge_edges), length=rlen, branch=branch,
               tiles={f"{c},{r}": n for (c, r), n in ridge_rows.most_common()}),
    feet={cls: dict(n=f["n"], weld=f["weld"], y=round(float(np.median(f["y"])), 1),
                    dih=round(float(np.median(f["dih"])), 1))
          for cls, f in foot.items()},
    g_round=dict(
        sharp_jumps=[[du, dv, n] for (du, dv), n in sharp_o.most_common()],
        straight_other=[[du, dv, n] for (du, dv), n in str_o.most_common()],
        vweld=[vweld, len(quads)],
        caps=dict(n=len(caps), rows={str(k): v for k, v in crows.items()}) if caps else None,
        row_y={str(row): [round(float(np.median([a for a, b in rowtab[row]])), 1),
                          round(float(np.median([b for a, b in rowtab[row]])), 1)]
               for row in sorted(rowtab)},
        nn_spacing=[round(float(np.median(nn)), 2), round(float(np.percentile(nn, 90)), 2)],
        course_h=round(float(np.median(qh)), 2),
    ),
), indent=1))
print(f"-> {OUTD / 'daguerreo_massif.json'}")
