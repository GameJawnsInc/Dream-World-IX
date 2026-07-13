"""THE REAL-WALL MESH ORGANIZATION STUDY -- how actual FF9 interior escarpments are BUILT.

The tile decode (rock_wall_language.py) gave the atlas organization; three synthesis rounds
then each minted a new failure mode (band stripe, cone trap, fan smears, corner smears,
long-edge spans, the moat breach). The meta-law fired again: study the real MESH before
synthesizing more. Questions this answers, per real wall component:

  1. QUADS -- what fraction of wall tris pair into clean quads? width/height distributions.
  2. COURSES -- do stacked courses SHARE verts (welded) or float free?
  3. WELDS -- crest-to-grass and foot-to-ground: identity welds or T-junctions?
  4. NORMALS -- what do real wall vertex normals look like (face-aligned? up? smoothed)?
  5. BENDS -- how sharply do real crest lines turn per station, and what does the mesh do
     at a bend (narrower quads? fans? tile choice)?
  6. UV -- confirm corner assignment + u continuity at the QUAD-STRIP level.

Pure offline; writes out/wall_anatomy.json + prints the digest.
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X

OUT = Path(__file__).with_name("out") / "wall_anatomy.json"
TILE_U, TILE_V = 0.0625, 0.03125
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))

# ---- 1. find interior wall components across disc 1 -------------------------------------------
comps_all = []
for (bx, by) in X.list_blocks(disc=1):
    try:
        bm = X.read_block(bx, by, disc=1)
    except Exception:
        continue
    V, N, U, T = bm.verts, bm.normals, bm.uvs, bm.tangents
    ntri = len(bm.flat_index) // 3
    tri_idx = [bm.flat_index[3 * t:3 * t + 3] for t in range(ntri)]
    topo = [X.decode_id(int(round(T[i[0]][0])))["topograph"] for i in tri_idx]
    wall = [t for t in range(ntri) if topo[t] == 49]
    if len(wall) < 40:
        continue
    edge_tris = defaultdict(list)
    for t in wall:
        i = tri_idx[t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((kk(V[i[a]]), kk(V[i[b]]))))].append(t)
    adj = defaultdict(set)
    for ts in edge_tris.values():
        for i2 in range(len(ts)):
            for j2 in range(i2 + 1, len(ts)):
                adj[ts[i2]].add(ts[j2])
                adj[ts[j2]].add(ts[i2])
    seen = set()
    for s in wall:
        if s in seen:
            continue
        comp = {s}
        st = [s]
        while st:
            t = st.pop()
            for t2 in adj[t]:
                if t2 not in comp:
                    comp.add(t2)
                    st.append(t2)
        seen |= comp
        ys = [V[j][1] for t in comp for j in tri_idx[t]]
        if len(comp) >= 40 and min(ys) >= 1.0 and (max(ys) - min(ys)) >= 8.0:
            comps_all.append(((bx, by), comp, bm, tri_idx, topo))
comps_all.sort(key=lambda c: -len(c[1]))
print(f"interior wall components (>=40 tris, base >=1, height >=8): {len(comps_all)}", flush=True)

# ---- 2. per-component anatomy ------------------------------------------------------------------
digest = []
for (blk, comp, bm, tri_idx, topo) in comps_all[:8]:
    V, N, U = bm.verts, bm.normals, bm.uvs
    comp = sorted(comp)

    # --- quad pairing: two comp tris sharing an edge whose union is 4 verts, 2 up + 2 down
    e2t = defaultdict(list)
    for t in comp:
        i = tri_idx[t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e2t[tuple(sorted((kk(V[i[a]]), kk(V[i[b]]))))].append(t)
    paired = {}
    quads = []
    for e, ts in e2t.items():
        if len(ts) != 2 or ts[0] in paired or ts[1] in paired:
            continue
        vs = {kk(V[j]) for t in ts for j in tri_idx[t]}
        if len(vs) != 4:
            continue
        vs = sorted(vs, key=lambda p: p[1])
        lo, hi = vs[:2], vs[2:]
        if abs(lo[0][1] - lo[1][1]) > 1.5 or abs(hi[0][1] - hi[1][1]) > 1.5:
            continue                                       # not a course-aligned quad
        paired[ts[0]] = paired[ts[1]] = len(quads)
        quads.append({"tris": ts, "lo": lo, "hi": hi})
    lone = [t for t in comp if t not in paired]

    # --- per-quad measurements
    widths, heights, rects, corner_pure = [], [], [], 0
    uv_of = {}
    for t in comp:
        i = tri_idx[t]
        for j in i:
            uv_of[kk(V[j])] = (U[j][0], U[j][1])
    for q in quads:
        (a, b), (c, d) = q["lo"], q["hi"]
        widths.append(math.hypot(d[0] - c[0], d[2] - c[2]))
        heights.append((c[1] + d[1]) / 2 - (a[1] + b[1]) / 2)
        us = [uv_of[p][0] for p in (a, b, c, d)]
        vs2 = [uv_of[p][1] for p in (a, b, c, d)]
        rects.append((round(min(us), 5), round(min(vs2), 5),
                      round(max(us) - min(us), 5), round(max(vs2) - min(vs2), 5)))
        # corner purity: every vert's uv at one of the rect's 4 corners (tol 1e-4)?
        u0, v0 = min(us), min(vs2)
        u1, v1 = max(us), max(vs2)
        pure = all(min(abs(uu - u0), abs(uu - u1)) < 1e-4 and
                   min(abs(vv - v0), abs(vv - v1)) < 1e-4
                   for uu, vv in (uv_of[p] for p in (a, b, c, d)))
        corner_pure += pure

    # --- course stacking: quad mean-y clusters; vert sharing between adjacent courses
    if quads:
        qys = [(sum(p[1] for p in q["lo"] + q["hi"]) / 4, qi) for qi, q in enumerate(quads)]
        qys.sort()
        courses = []
        for y, qi in qys:
            if courses and y - courses[-1]["y"][-1] < 2.0:
                courses[-1]["y"].append(y)
                courses[-1]["q"].append(qi)
            else:
                courses.append({"y": [y], "q": [qi]})
        share = []
        for ci in range(len(courses) - 1):
            lo_verts = {p for qi in courses[ci + 1]["q"] for p in quads[qi]["hi"]}
            hi_verts = {p for qi in courses[ci]["q"] for p in quads[qi]["lo"]}
            if hi_verts:
                share.append(len(lo_verts & hi_verts) / len(hi_verts))
    else:
        courses, share = [], []

    # --- welds: wall boundary verts vs non-wall tris (identity + T-junction)
    comp_set = set(comp)
    wall_verts = {kk(V[j]) for t in comp for j in tri_idx[t]}
    ys_all = [p[1] for p in wall_verts]
    y_lo, y_hi = min(ys_all), max(ys_all)
    top_verts = {p for p in wall_verts if p[1] > y_hi - 1.5}
    bot_verts = {p for p in wall_verts if p[1] < y_lo + 1.5}
    other_verts = set()
    other_edges = []
    for t in range(len(tri_idx)):
        if t in comp_set or topo[t] == 49:
            continue
        i = tri_idx[t]
        pts = [kk(V[j]) for j in i]
        other_verts.update(pts)
        for a, b in ((0, 1), (1, 2), (2, 0)):
            other_edges.append((pts[a], pts[b]))
    def weld_stats(vv):
        ident = sum(1 for p in vv if p in other_verts)
        tjunc = 0
        for p in vv:
            if p in other_verts:
                continue
            for a, b in other_edges:
                ex, ez = b[0] - a[0], b[2] - a[2]
                L2 = ex * ex + ez * ez + (b[1] - a[1]) ** 2
                if L2 < 1e-9:
                    continue
                t01 = ((p[0] - a[0]) * ex + (p[2] - a[2]) * ez +
                       (p[1] - a[1]) * (b[1] - a[1])) / L2
                if t01 <= 0.01 or t01 >= 0.99:
                    continue
                q = (a[0] + t01 * (b[0] - a[0]), a[1] + t01 * (b[1] - a[1]),
                     a[2] + t01 * (b[2] - a[2]))
                if (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2 < 0.01:
                    tjunc += 1
                    break
        return ident, tjunc, len(vv)

    # --- normals: stored vertex normals on wall verts
    nys = []
    for t in comp:
        for j in tri_idx[t]:
            n3 = N[j]
            L = math.sqrt(n3[0] ** 2 + n3[1] ** 2 + n3[2] ** 2) or 1.0
            nys.append(n3[1] / L)

    # --- bends: top-course top-edge chain turn angles + lone-tri correlation
    turn_stats, lone_near_bend = [], 0
    if courses:
        top_q = courses[-1]["q"] if len(courses) > 1 else courses[0]["q"]
        # chain the top edges of the top course
        pts = []
        for qi in top_q:
            pts.extend(quads[qi]["hi"])
        # order by nearest-neighbour walk from an extreme point
        pts = list({p for p in pts})
        if len(pts) >= 3:
            chain = [min(pts, key=lambda p: (p[0], p[2]))]
            rest = [p for p in pts if p != chain[0]]
            while rest:
                nxt = min(rest, key=lambda p: (p[0] - chain[-1][0]) ** 2 + (p[2] - chain[-1][2]) ** 2)
                if math.hypot(nxt[0] - chain[-1][0], nxt[2] - chain[-1][2]) > 8.0:
                    break
                chain.append(nxt)
                rest.remove(nxt)
            for i2 in range(1, len(chain) - 1):
                p2, v2, q2 = chain[i2 - 1], chain[i2], chain[i2 + 1]
                a1 = math.atan2(v2[2] - p2[2], v2[0] - p2[0])
                a2 = math.atan2(q2[2] - v2[2], q2[0] - v2[0])
                turn_stats.append(abs((a2 - a1 + math.pi) % (2 * math.pi) - math.pi))
            bends = [chain[i2] for i2 in range(1, len(chain) - 1)
                     if math.degrees(turn_stats[i2 - 1]) > 35]
            for t in lone:
                c3 = [sum(V[j][k2] for j in tri_idx[t]) / 3 for k2 in range(3)]
                if any((c3[0] - b3[0]) ** 2 + (c3[2] - b3[2]) ** 2 < 36 for b3 in bends):
                    lone_near_bend += 1

    ti, tt, tn = weld_stats(top_verts)
    bi, bt, bn = weld_stats(bot_verts)
    d2 = {
        "block": blk, "tris": len(comp), "quads": len(quads), "lone": len(lone),
        "quad_frac": round(2 * len(quads) / max(1, len(comp)), 3),
        "width_med": round(float(np.median(widths)), 2) if widths else None,
        "width_p10_p90": [round(float(np.percentile(widths, p)), 2) for p in (10, 90)] if widths else None,
        "height_med": round(float(np.median(heights)), 2) if heights else None,
        "corner_pure_frac": round(corner_pure / max(1, len(quads)), 3),
        "n_courses": len(courses),
        "course_vert_share": [round(s, 2) for s in share],
        "top_weld": {"identity": ti, "tjunction": tt, "of": tn},
        "bot_weld": {"identity": bi, "tjunction": bt, "of": bn},
        "normal_ny": {"med": round(float(np.median(nys)), 3),
                      "p10": round(float(np.percentile(nys, 10)), 3),
                      "p90": round(float(np.percentile(nys, 90)), 3)},
        "turn_deg": {"med": round(math.degrees(float(np.median(turn_stats))), 1),
                     "p90": round(math.degrees(float(np.percentile(turn_stats, 90))), 1),
                     "max": round(math.degrees(max(turn_stats)), 1)} if turn_stats else None,
        "lone_near_bend": lone_near_bend,
    }
    digest.append(d2)
    print(json.dumps(d2), flush=True)

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(digest, indent=1))
print(f"\n-> {OUT}", flush=True)
