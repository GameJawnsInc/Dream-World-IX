"""ROCK-WALL JUNCTION GRAMMAR -- how stock JOINS wall meshes (crest / corner / foot).

The strip-carry rung stopped 2026-07-31 as a plumbing stop (studies/path-d-new-world/
STRIP-CARRY-PREDICTION.md): across two playtests every defect lived on a MINTED JOIN --
the carried faces drew zero complaints. This fourth study on the shared wall instrument
(the same crest-seeded topo-49 components as rock_wall_language / instances / massing)
measures the three junction classes the defects point at:

  J1 CREST -- weld completeness along the top boundary (does stock ever leave a crest
     open?); cap anatomy (dip, outward extent/drop of crest-touching wall tris); the
     plateau fringe behind the weld (distance/dy profile over two rings + rim-row tile
     histogram vs far-field); the crest dihedral.
  J2 CORNER -- per horizontally-adjacent instance pair, binned by the plan turn between
     the two faces' outward normals: station widths, texel density each side + the jump,
     seam-u tile-boundary rate, mirroring, same-tile rate, shared-vert weld count,
     instance planarity. The question: what does stock's corner column DO that our
     minted mortar did not?
  J3 FOOT -- weld completeness along the bottom boundary (the pierce-vs-weld law); the
     ground side's topo/dip/outward-slope/tiles vs far-field; bottom-course anatomy.

Questions registered in studies/path-d-new-world/JUNCTION-GRAMMAR.md BEFORE this ran.
Read-only vs stock. Artifacts -> out/rock_wall_junctions.json + out/crest_section.png.
Regenerate: py -X utf8 rock_wall_junctions.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

PLATEAU = {10, 11, 12}
TILE_U, TILE_V = 0.0625, 0.03125
OUT = Path(__file__).with_name("out") / "rock_wall_junctions.json"
PNG = Path(__file__).with_name("out") / "crest_section.png"
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))   # noqa: E731

PU, PV = json.loads((Path(__file__).with_name("out") / "rock_tiles.json").read_text())["phase"]


def tile_of(uvs):
    us = [q[0] for q in uvs]
    vs = [q[1] for q in uvs]
    return (int(math.floor((min(us) - PU) / TILE_U + 0.5)),
            int(math.floor((min(vs) - PV) / TILE_V + 0.5)))


def tri_dip(a, b, c):
    fn = np.cross(b - a, c - a)
    L = float(np.linalg.norm(fn))
    if L < 1e-9:
        return None
    return math.degrees(math.acos(max(-1.0, min(1.0, abs(float(fn[1])) / L))))


def on_border(p):
    return (min(abs(p[0]), abs(p[0] - 64.0)) < 0.35 or
            min(abs(p[2]), abs(p[2] + 64.0)) < 0.35)


# ---- accumulators ---------------------------------------------------------------------------
top_classes = Counter()                                     # J1 weld completeness
bot_classes = Counter()                                     # J3 pierce-vs-weld
cap_recs = []                                               # (dip, out_ext, out_drop)
crest_touch_dips = []
crest_dihedral = []                                         # (wall dip, plateau dip)
fringe_prof = []                                            # (dist_behind, dy)
ring1_dips = []
fringe_tiles = Counter()
plat_far_tiles = Counter()
pair_recs = []                                              # J2 corner records
foot_ground_topo = Counter()
foot_ground_dips = []
foot_out_slopes = []                                        # ground third-vert dy/dist
foot_ground_tiles = Counter()
ground_far_tiles = Counter()
bottom_dips = []
bottom_tiles = Counter()
mid_dips = []
mid_tiles = Counter()
n_blocks = n_comps = 0

for (bx, by) in X.list_blocks(disc=1):
    try:
        bm = X.read_block(bx, by, disc=1)
    except Exception:                                       # noqa: BLE001
        continue
    V, U, T = bm.verts, bm.uvs, bm.tangents
    ntri = len(bm.flat_index) // 3
    tri_idx = [bm.flat_index[3 * t:3 * t + 3] for t in range(ntri)]
    topo = [X.decode_id(int(round(T[idx[0]][0])))["topograph"] for idx in tri_idx]
    if not any(t in PLATEAU for t in topo):
        continue

    edge_tris = defaultdict(list)
    for t, idx in enumerate(tri_idx):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((kk(V[idx[a]]), kk(V[idx[b]]))))].append(t)

    crest49 = set()
    for e, ts in edge_tris.items():
        if len(ts) == 2:
            pair = {topo[ts[0]], topo[ts[1]]}
            if 49 in pair and pair & PLATEAU:
                crest49.add(ts[0] if topo[ts[0]] == 49 else ts[1])
    adj49 = defaultdict(set)
    for e, ts in edge_tris.items():
        r = [t for t in ts if topo[t] == 49]
        for i in range(len(r)):
            for j in range(i + 1, len(r)):
                adj49[r[i]].add(r[j])
                adj49[r[j]].add(r[i])
    comp_of = {}
    seen = set()
    for s in crest49:
        if s in seen:
            continue
        comp = {s}
        st = [s]
        while st:
            t = st.pop()
            for t2 in adj49[t]:
                if t2 not in comp:
                    comp.add(t2)
                    st.append(t2)
        seen |= comp
        for t in comp:
            comp_of[t] = s
    wall_tris = set(comp_of)
    if not wall_tris:
        continue
    n_blocks += 1

    comp_tris = defaultdict(list)
    for t in wall_tris:
        comp_tris[comp_of[t]].append(t)
    comp_band = {}
    for root, ts in comp_tris.items():
        ys = [V[i][1] for t in ts for i in tri_idx[t]]
        y0, y1 = min(ys), max(ys)
        if y1 - y0 >= 6.0 and len(ts) >= 12:
            comp_band[root] = (y0, y1)
            n_comps += 1

    # ---- J1 + J3: boundary weld classification (one wall tri on the edge) -------------------
    crest_edges = []                                        # (edge, wall_tri, plateau_tri)
    foot_edges = []                                         # (edge, wall_tri, ground_tri)
    for e, ts in edge_tris.items():
        w = [t for t in ts if t in wall_tris]
        if len(w) != 1:
            continue
        o = [t for t in ts if t not in wall_tris]
        root = comp_of[w[0]]
        if root not in comp_band:
            continue
        y0, y1 = comp_band[root]
        ym = (e[0][1] + e[1][1]) / 2.0
        if any(topo[t] in PLATEAU for t in o):
            cls = "plateau"
            crest_edges.append((e, w[0], next(t for t in o if topo[t] in PLATEAU)))
        elif any(topo[t] == 49 for t in o):
            cls = "rock"
        elif o:
            cls = "ground"
            foot_edges.append((e, w[0], o[0]))
        elif on_border(e[0]) and on_border(e[1]):
            cls = "border"
        else:
            cls = "open"
        if ym >= y0 + 0.85 * (y1 - y0):
            top_classes[cls] += 1
        if ym <= y0 + 0.15 * (y1 - y0):
            bot_classes[cls] += 1

    # ---- J1: cap anatomy + dihedral + the plateau fringe ------------------------------------
    crest_pts = sorted({p for e, _, _ in crest_edges for p in e})
    CP = np.array(crest_pts) if crest_pts else np.zeros((0, 3))
    seen_cap = set()
    for e, wt, pt in crest_edges:
        a, b, c = (np.array(V[i], dtype=float) for i in tri_idx[wt])
        dw = tri_dip(a, b, c)
        pa, pb, pc = (np.array(V[i], dtype=float) for i in tri_idx[pt])
        dp = tri_dip(pa, pb, pc)
        if dw is None or dp is None:
            continue
        crest_dihedral.append((round(dw, 1), round(dp, 1)))
        if wt in seen_cap:
            continue
        seen_cap.add(wt)
        crest_touch_dips.append(round(dw, 1))
        # cap cross-section: off-edge verts vs the weld line, in plan
        ek = set(e)
        onv = [np.array(V[i], dtype=float) for i in tri_idx[wt] if kk(V[i]) in ek]
        offv = [np.array(V[i], dtype=float) for i in tri_idx[wt] if kk(V[i]) not in ek]
        if len(onv) == 2 and offv and dw < 35.0:
            e0, e1 = onv[0][[0, 2]], onv[1][[0, 2]]
            ed = e1 - e0
            L = float(np.linalg.norm(ed))
            if L > 1e-6:
                ext = max(abs(float(np.cross(ed / L, q[[0, 2]] - e0))) for q in offv)
                drop = float((onv[0][1] + onv[1][1]) / 2.0 -
                             np.mean([q[1] for q in offv]))
                cap_recs.append((round(dw, 1), round(ext, 2), round(drop, 2)))
    if len(CP):
        ring1 = {pt for _, _, pt in crest_edges}
        ring2 = set()
        for e, ts in edge_tris.items():
            if any(t in ring1 for t in ts):
                for t in ts:
                    if topo[t] in PLATEAU and t not in ring1:
                        ring2.add(t)
        for t in ring1:
            a, b, c = (np.array(V[i], dtype=float) for i in tri_idx[t])
            d = tri_dip(a, b, c)
            if d is not None:
                ring1_dips.append(round(d, 1))
        for t in ring1 | ring2:
            fringe_tiles[tile_of([U[i] for i in tri_idx[t]])] += 1
            for i in tri_idx[t]:
                p = np.array(V[i], dtype=float)
                dd = np.hypot(CP[:, 0] - p[0], CP[:, 2] - p[2])
                j = int(np.argmin(dd))
                fringe_prof.append((round(float(dd[j]), 2),
                                    round(float(p[1] - CP[j][1]), 2)))
        near = ring1 | ring2
        for t in range(ntri):
            if topo[t] in PLATEAU and t not in near:
                plat_far_tiles[tile_of([U[i] for i in tri_idx[t]])] += 1

    # ---- J2: instances (verbatim union-find) + corner pair records --------------------------
    parent = {t: t for t in wall_tris}

    def find(t):
        while parent[t] != t:
            parent[t] = parent[parent[t]]
            t = parent[t]
        return t

    def bbox_of(ts):
        us = [U[i][0] for t in ts for i in tri_idx[t]]
        vs = [U[i][1] for t in ts for i in tri_idx[t]]
        return min(us), min(vs), max(us), max(vs)

    members = {t: {t} for t in wall_tris}
    for e, ts in edge_tris.items():
        w = [t for t in ts if t in wall_tris]
        if len(w) != 2:
            continue
        t1, t2 = w
        uv1 = {kk(V[i]): tuple(np.round(U[i], 5)) for i in tri_idx[t1]}
        uv2 = {kk(V[i]): tuple(np.round(U[i], 5)) for i in tri_idx[t2]}
        if not all(uv1.get(p) == uv2.get(p) for p in e):
            continue
        r1, r2 = find(t1), find(t2)
        if r1 == r2:
            continue
        u0, v0, u1, v1 = bbox_of(members[r1] | members[r2])
        if (u1 - u0) > TILE_U + 1e-4 or (v1 - v0) > TILE_V + 1e-4:
            continue
        parent[r2] = r1
        members[r1] |= members[r2]
        del members[r2]

    inst_of_tri = {}
    inst = {}
    for r, ts in members.items():
        pts = []
        uvmap = {}
        for t in ts:
            for i in tri_idx[t]:
                pts.append((V[i][0], V[i][1], V[i][2], U[i][0], U[i][1]))
                uvmap[kk(V[i])] = (float(U[i][0]), float(U[i][1]))
        P = np.array(pts)
        n_sum = np.zeros(3)
        for t in ts:
            a, b, c = (np.array(V[i], dtype=float) for i in tri_idx[t])
            n_sum += np.cross(b - a, c - a)
        XZ = P[:, [0, 2]] - P[:, [0, 2]].mean(axis=0)
        if len(P) > 2 and float(np.abs(XZ).sum()) > 1e-9:
            w_, vec = np.linalg.eigh(np.cov(XZ.T))
            hdir = vec[:, int(np.argmax(w_))]
        else:
            hdir = np.array([1.0, 0.0])
        s = XZ @ hdir
        width = float(s.max() - s.min()) if len(P) else 0.0
        du = float(P[:, 3].max() - P[:, 3].min()) if len(P) else 0.0
        us_c = P[:, 3] - P[:, 3].mean()
        ss, su = float(np.std(s)), float(np.std(us_c))
        u_corr = float(np.mean(s * us_c)) / (ss * su) if ss > 1e-6 and su > 1e-9 else 0.0
        # planarity: RMS distance from the best-fit plane
        plan_rms = 0.0
        Q = np.unique(P[:, :3], axis=0)
        if len(Q) >= 4:
            Qc = Q - Q.mean(axis=0)
            _, sv, vt = np.linalg.svd(Qc, full_matrices=False)
            plan_rms = float(np.sqrt(np.mean((Qc @ vt[-1]) ** 2)))
        inst[r] = dict(cen=P[:, :3].mean(axis=0), n=n_sum, hdir=hdir, width=width,
                       dens=(du * 2048.0 / width if width > 0.5 else None),
                       u_corr=u_corr, plan_rms=plan_rms, keys=set(uvmap),
                       uvmap=uvmap, tile=tile_of([(p[3], p[4]) for p in pts]),
                       yspan=float(P[:, 1].max() - P[:, 1].min()))
        for t in ts:
            inst_of_tri[t] = r

    seen_pairs = set()
    for e, ts in edge_tris.items():
        w = sorted({inst_of_tri[t] for t in ts if t in inst_of_tri})
        if len(w) != 2 or tuple(w) in seen_pairs:
            continue
        seen_pairs.add(tuple(w))
        A, B = inst[w[0]], inst[w[1]]
        d = B["cen"] - A["cen"]
        if abs(d[1]) > math.hypot(d[0], d[2]):
            continue                                        # vertical pair: not a corner seam
        if A["yspan"] < 1.0 or B["yspan"] < 1.0:
            continue                                        # degenerate (flat cap) side
        nA, nB = A["n"].copy(), B["n"].copy()
        nA[1] = nB[1] = 0.0
        LA, LB = np.linalg.norm(nA), np.linalg.norm(nB)
        if LA < 1e-6 or LB < 1e-6:
            continue
        turn = math.degrees(math.acos(max(-1.0, min(1.0, float(nA @ nB) / (LA * LB)))))
        hd = np.array([d[0], d[2]])
        Lh = np.linalg.norm(hd)
        mirrored = None
        if Lh > 1e-6:
            senses = []
            for side in (A, B):
                sgn = 1.0 if float(side["hdir"] @ (hd / Lh)) >= 0 else -1.0
                senses.append(side["u_corr"] * sgn)
            if abs(senses[0]) >= 0.3 and abs(senses[1]) >= 0.3:
                mirrored = bool(senses[0] * senses[1] < 0)
        shared = A["keys"] & B["keys"]
        seam_edge = None
        if len(shared) >= 2:
            fr = []
            for side in (A, B):
                for p in shared:
                    u = side["uvmap"][p][0]
                    f = ((u - PU) / TILE_U) % 1.0
                    fr.append(min(f, 1.0 - f))
            seam_edge = bool(max(fr) < 0.12)
        dens_jump = None
        if A["dens"] and B["dens"]:
            dens_jump = abs(A["dens"] - B["dens"]) / ((A["dens"] + B["dens"]) / 2.0)
        pair_recs.append(dict(
            turn=round(turn, 1),
            w=[round(A["width"], 2), round(B["width"], 2)],
            dens=[round(A["dens"], 1) if A["dens"] else None,
                  round(B["dens"], 1) if B["dens"] else None],
            dj=round(dens_jump, 3) if dens_jump is not None else None,
            se=seam_edge, mir=mirrored, same=bool(A["tile"] == B["tile"]),
            sv=len(shared),
            pr=[round(A["plan_rms"], 3), round(B["plan_rms"], 3)]))

    # ---- J3: the ground side + the bottom course --------------------------------------------
    foot_wall = set()
    for e, wt, gt in foot_edges:
        foot_wall.add(wt)
        foot_ground_topo[topo[gt]] += 1
        a, b, c = (np.array(V[i], dtype=float) for i in tri_idx[gt])
        dg = tri_dip(a, b, c)
        if dg is not None:
            foot_ground_dips.append(round(dg, 1))
        foot_ground_tiles[tile_of([U[i] for i in tri_idx[gt]])] += 1
        ek = set(e)
        offv = [np.array(V[i], dtype=float) for i in tri_idx[gt] if kk(V[i]) not in ek]
        if offv:
            em = (np.array(e[0], dtype=float) + np.array(e[1], dtype=float)) / 2.0
            q = offv[0]
            dp = math.hypot(q[0] - em[0], q[2] - em[2])
            if dp > 0.3:
                foot_out_slopes.append(round(float(q[1] - em[1]) / dp, 3))
    wall_adj_ground = {t for e, ts in edge_tris.items() if any(t2 in wall_tris for t2 in ts)
                       for t in ts if topo[t] not in PLATEAU and topo[t] != 49}
    for t in range(ntri):
        if topo[t] in PLATEAU or topo[t] == 49:
            continue
        if t not in wall_adj_ground:
            ground_far_tiles[tile_of([U[i] for i in tri_idx[t]])] += 1
    crest_wall = {wt for _, wt, _ in crest_edges}
    for t in wall_tris:
        a, b, c = (np.array(V[i], dtype=float) for i in tri_idx[t])
        d = tri_dip(a, b, c)
        if d is None:
            continue
        tl = tile_of([U[i] for i in tri_idx[t]])
        if t in foot_wall:
            bottom_dips.append(round(d, 1))
            bottom_tiles[tl] += 1
        elif t not in crest_wall:
            mid_dips.append(round(d, 1))
            mid_tiles[tl] += 1

# ---- summaries ------------------------------------------------------------------------------
def pct(a, q):
    return round(float(np.percentile(a, q)), 2) if len(a) else None


def frac(cnt, k):
    tot = sum(cnt.values())
    return f"{cnt.get(k, 0)}/{tot} ({cnt.get(k, 0) / max(1, tot):.1%})"


print(f"population: {n_blocks} blocks, {n_comps} wall components (yspan >= 6u)\n")

print("== J1 THE CREST JUNCTION ==")
print(f"   top-band boundary classes: {dict(top_classes)}")
print(f"   -> welded to plateau: {frac(top_classes, 'plateau')};  OPEN (once-edges): "
      f"{frac(top_classes, 'open')}")
ct = [r[0] for r in cap_recs]
print(f"   crest-touching wall tris: {len(crest_touch_dips)}; dip med "
      f"{pct(crest_touch_dips, 50)} p25 {pct(crest_touch_dips, 25)} p75 "
      f"{pct(crest_touch_dips, 75)}; near-flat caps (dip<35): "
      f"{sum(1 for d in crest_touch_dips if d < 35) / max(1, len(crest_touch_dips)):.1%}")
print(f"   cap cross-section (dip<35 tris): n={len(cap_recs)}; outward extent med "
      f"{pct([r[1] for r in cap_recs], 50)}u p90 {pct([r[1] for r in cap_recs], 90)}u; "
      f"outward DROP med {pct([r[2] for r in cap_recs], 50)}u "
      f"(edge-y minus outer-y; +ve = cap falls outward)")
W = [a for a, b in crest_dihedral]
Pd = [b for a, b in crest_dihedral]
print(f"   dihedral across {len(crest_dihedral)} crest edges: wall dip med {pct(W, 50)} "
      f"vs plateau dip med {pct(Pd, 50)}; ring1 plateau dip med {pct(ring1_dips, 50)} "
      f"p90 {pct(ring1_dips, 90)}")
bins = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 6), (6, 8), (8, 12)]
print("   fringe profile behind the weld (dist -> dy vs crest):")
prof_json = []
for lo, hi in bins:
    dys = [dy for dd, dy in fringe_prof if lo <= dd < hi]
    prof_json.append(dict(bin=[lo, hi], n=len(dys), med=pct(dys, 50),
                          p25=pct(dys, 25), p75=pct(dys, 75)))
    print(f"      {lo:2d}-{hi:2d}u: n={len(dys):6d}  dy med {pct(dys, 50)}  "
          f"p25 {pct(dys, 25)}  p75 {pct(dys, 75)}")
print(f"   fringe tiles (2 rings): {fringe_tiles.most_common(8)}")
print(f"   far plateau tiles:      {plat_far_tiles.most_common(8)}")

print("\n== J2 THE CORNER COLUMN ==")
tb = [(0, 10), (10, 25), (25, 45), (45, 181)]
turns = [p["turn"] for p in pair_recs]
print(f"   horizontal instance pairs: {len(pair_recs)}; turn p50 {pct(turns, 50)} "
      f"p90 {pct(turns, 90)} p99 {pct(turns, 99)} max {max(turns) if turns else None}")
j2_json = []
for lo, hi in tb:
    ps = [p for p in pair_recs if lo <= p["turn"] < hi]
    wmin = [min(p["w"]) for p in ps]
    dj = [p["dj"] for p in ps if p["dj"] is not None]
    se = [p for p in ps if p["se"] is not None]
    mir = [p for p in ps if p["mir"] is not None]
    row = dict(bin=[lo, hi], n=len(ps),
               w_min_med=pct(wmin, 50), w_min_p25=pct(wmin, 25),
               dens_jump_med=pct(dj, 50), dens_jump_p90=pct(dj, 90),
               seam_tile_edge=(round(sum(1 for p in se if p["se"]) / len(se), 3)
                               if se else None),
               mirrored=(round(sum(1 for p in mir if p["mir"]) / len(mir), 3)
                         if mir else None),
               same_tile=round(sum(1 for p in ps if p["same"]) / max(1, len(ps)), 3),
               shared_verts_med=pct([p["sv"] for p in ps], 50),
               plan_rms_med=pct([max(p["pr"]) for p in ps], 50))
    j2_json.append(row)
    print(f"   turn {lo:3d}-{hi:3d}: n={row['n']:5d}  narrow-side width med "
          f"{row['w_min_med']}u (p25 {row['w_min_p25']})  dens jump med "
          f"{row['dens_jump_med']} p90 {row['dens_jump_p90']}  seam@tile-edge "
          f"{row['seam_tile_edge']}  mirrored {row['mirrored']}  same-tile "
          f"{row['same_tile']}  shared-verts med {row['shared_verts_med']}  "
          f"plan-rms med {row['plan_rms_med']}u")

print("\n== J3 THE WALL|GROUND WELD ==")
print(f"   bottom-band boundary classes: {dict(bot_classes)}")
print(f"   -> welded to ground: {frac(bot_classes, 'ground')};  OPEN (once-edges): "
      f"{frac(bot_classes, 'open')}")
print(f"   ground topo at the foot: {foot_ground_topo.most_common()}")
print(f"   ground dip at the foot: med {pct(foot_ground_dips, 50)} p90 "
      f"{pct(foot_ground_dips, 90)}; outward slope med {pct(foot_out_slopes, 50)} "
      f"(p25 {pct(foot_out_slopes, 25)} p75 {pct(foot_out_slopes, 75)}; "
      f"-ve = ground falls away from the wall)")
print(f"   foot ground tiles: {foot_ground_tiles.most_common(8)}")
print(f"   far ground tiles:  {ground_far_tiles.most_common(8)}")
print(f"   bottom course: n={len(bottom_dips)} dip med {pct(bottom_dips, 50)}; "
      f"mid-face: n={len(mid_dips)} dip med {pct(mid_dips, 50)}")
print(f"   bottom tiles: {bottom_tiles.most_common(8)}")
print(f"   mid tiles:    {mid_tiles.most_common(8)}")

# ---- crest cross-section render -------------------------------------------------------------
PNG.parent.mkdir(parents=True, exist_ok=True)
Wp, Hp = 760, 420
img = Image.new("RGB", (Wp, Hp), (24, 26, 30))
dr = ImageDraw.Draw(img)
SCX, SCY = 55.0, 24.0
x0, ymid = 60, Hp // 2
dr.line([(x0, ymid), (x0 + 12 * SCX, ymid)], fill=(90, 90, 100), width=1)
dr.text((x0 + 12 * SCX - 60, ymid + 4), "dy = 0", fill=(150, 150, 160))
for q, col in ((25, (90, 130, 100)), (50, (120, 220, 150)), (75, (90, 130, 100))):
    pts = []
    for lo, hi in bins:
        dys = [dy for dd, dy in fringe_prof if lo <= dd < hi]
        if dys:
            pts.append((x0 + (lo + hi) / 2 * SCX,
                        ymid - float(np.percentile(dys, q)) * SCY))
    if len(pts) >= 2:
        dr.line(pts, fill=col, width=2 if q == 50 else 1)
dr.text((10, 8), "plateau fringe behind the crest weld: dy vs distance (med + quartiles); "
                 "x = 0..12u behind", fill=(220, 220, 220))
dr.text((10, 24), f"{len(fringe_prof)} vert samples, {n_comps} components", fill=(160, 160, 170))
img.save(PNG)
print(f"\ncrest section render -> {PNG}")

OUT.write_text(json.dumps(dict(
    population=dict(blocks=n_blocks, comps=n_comps),
    j1=dict(top_classes=dict(top_classes), cap_recs=cap_recs,
            crest_touch_dips=crest_touch_dips, dihedral=crest_dihedral,
            ring1_dips=ring1_dips, fringe_profile=prof_json,
            fringe_tiles={f"{c},{r}": n for (c, r), n in fringe_tiles.most_common()},
            far_tiles={f"{c},{r}": n for (c, r), n in plat_far_tiles.most_common(24)}),
    j2=dict(bins=j2_json, pairs=pair_recs),
    j3=dict(bot_classes=dict(bot_classes), ground_topo=dict(foot_ground_topo),
            ground_dips=foot_ground_dips, out_slopes=foot_out_slopes,
            foot_tiles={f"{c},{r}": n for (c, r), n in foot_ground_tiles.most_common()},
            far_tiles={f"{c},{r}": n for (c, r), n in ground_far_tiles.most_common(24)},
            bottom_dips=bottom_dips, mid_dips_med=pct(mid_dips, 50),
            bottom_tiles={f"{c},{r}": n for (c, r), n in bottom_tiles.most_common()},
            mid_tiles={f"{c},{r}": n for (c, r), n in mid_tiles.most_common(24)})),
    indent=0))
print(f"artifacts -> {OUT}")
