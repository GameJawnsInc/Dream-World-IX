"""ROCK-WALL RIM GRAMMAR -- how stock CONSTRUCTS the crest rim (the 5th wall study).

The junction-aware round scored PARTIAL (studies/path-d-new-world/JUNCTION-AWARE-
PREDICTION.md): faces/seams/foot passed in-game; the CREST RIM failed on form. J1
measured the crest statistically; this instrument decodes its CONSTRUCTION:

  R1 RIM RING -- deformed lattice course vs lattice clip: plan lattice residuals
     (crest vs ring-1 inner boundary vs far plateau), ring-1 tris per crest edge,
     ring-1 tri shape vs far field (plan area / min angle / sliver fraction),
     inner-boundary alignment + offset vs the crest.
  R2 SILHOUETTE -- ordered crest chains: segment lengths, plan turns, sign
     alternation of large turns, y-jitter.
  R3 TOP COURSE -- both sides of the weld: ring-1 vs ring-2 tiles, which tile edge
     sits ON the weld (plateau + wall side), wall top-course height + rows vs mid.
  R4 OVERHANG -- signed outward excursion of near-crest wall verts beyond the crest
     line (the jut budget) + the setback profile at fixed drops.
  R5 FOOT SHADE -- stock's bottom-course row-10 usage (fraction, v-subrange, band
     height) + REAL atlas luminance (vanilla bundle pixels) of row 10 vs mid rows.

Questions registered in studies/path-d-new-world/RIM-GRAMMAR.md BEFORE this ran.
Read-only vs stock disc-1. Artifacts -> out/rock_wall_rim.json + out/rim_courses.png.
Regenerate: py -X utf8 rock_wall_rim.py
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
OUT = Path(__file__).with_name("out") / "rock_wall_rim.json"
PNG = Path(__file__).with_name("out") / "rim_courses.png"
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))   # noqa: E731

PU, PV = json.loads((Path(__file__).with_name("out") / "rock_tiles.json").read_text())["phase"]


def tile_of(uvs):
    us = [q[0] for q in uvs]
    vs = [q[1] for q in uvs]
    return (int(math.floor((min(us) - PU) / TILE_U + 0.5)),
            int(math.floor((min(vs) - PV) / TILE_V + 0.5)))


def frac_uv(u, v):
    return (((u - PU) / TILE_U) % 1.0, ((v - PV) / TILE_V) % 1.0)


def lat_res(p):
    """Plan distance to the 4u block lattice."""
    rx = p[0] % 4.0
    rz = p[2] % 4.0
    return math.hypot(min(rx, 4.0 - rx), min(rz, 4.0 - rz))


def plan_area(a, b, c):
    return 0.5 * abs((b[0] - a[0]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[0] - a[0]))


def plan_min_angle(a, b, c):
    P = [np.array([q[0], q[2]]) for q in (a, b, c)]
    best = None
    for i in range(3):
        v1 = P[(i + 1) % 3] - P[i]
        v2 = P[(i + 2) % 3] - P[i]
        L1, L2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if L1 < 1e-9 or L2 < 1e-9:
            return None
        ang = math.degrees(math.acos(max(-1.0, min(1.0, float(v1 @ v2) / (L1 * L2)))))
        best = ang if best is None else min(best, ang)
    return best


def build_chains(edges):
    """Ordered polylines from an edge set (kk-keyed endpoints -> lists of 3D points)."""
    adj = defaultdict(set)
    pt3 = {}
    for e in edges:
        a, b = e
        adj[a].add(b)
        adj[b].add(a)
        pt3[a] = np.array(a, dtype=float)
        pt3[b] = np.array(b, dtype=float)
    done = set()
    chains = []

    def walk(a, b):
        ch = [a, b]
        done.add(frozenset((a, b)))
        while len(adj[ch[-1]]) == 2:
            nxt = [q for q in adj[ch[-1]] if frozenset((ch[-1], q)) not in done]
            if not nxt:
                break
            done.add(frozenset((ch[-1], nxt[0])))
            ch.append(nxt[0])
        return ch

    for a in adj:
        if len(adj[a]) != 2:                                # endpoints + junction nodes
            for b in adj[a]:
                if frozenset((a, b)) not in done:
                    chains.append(walk(a, b))
    for a in adj:                                           # pure cycles
        for b in adj[a]:
            if frozenset((a, b)) not in done:
                chains.append(walk(a, b))
    return [[pt3[q] for q in ch] for ch in chains if len(ch) >= 2]


# ---- accumulators ---------------------------------------------------------------------------
res_crest, res_inner, res_far = [], [], []                  # R1 lattice residuals
r1_shape = dict(ring=dict(area=[], mina=[]), far=dict(area=[], mina=[]))
inner_align, inner_off = [], []                             # R1 inner boundary vs crest
n_ring1_tris = n_crest_edges = 0
seg_lens, turn_mags, alt_flags, dy_edge, y_detr = [], [], [], [], []   # R2
ring1_tiles, ring2_tiles = Counter(), Counter()             # R3 plateau side
plat_dv, plat_du, plat_fv_on = [], [], []
wall_top_tiles, wall_mid_tiles = Counter(), Counter()       # R3 wall side
wall_course_h, wall_fv_on, wall_dv = [], [], []
jut_exc, setback = [], defaultdict(list)                    # R4
bot_row_hist = Counter()                                    # R5
row10_fv, row10_h, bot_other_h = [], [], []
row10_span, row10_vy_up = [], []                            # unwrapped v-row span / orientation
top_span, top_vy_up = [], []                                # same for the wall TOP course
n_blocks = n_comps = 0
render_comps = []                                           # top-3 largest, for the PNG

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
        if max(ys) - min(ys) >= 6.0 and len(ts) >= 12:
            comp_band[root] = (min(ys), max(ys))
            n_comps += 1

    # ---- boundary edges (crest + foot), gated to banded components --------------------------
    crest_edges, foot_edges = [], []                        # (edge, wall_tri, other_tri)
    for e, ts in edge_tris.items():
        w = [t for t in ts if t in wall_tris]
        if len(w) != 1 or comp_of[w[0]] not in comp_band:
            continue
        o = [t for t in ts if t not in wall_tris]
        if any(topo[t] in PLATEAU for t in o):
            crest_edges.append((e, w[0], next(t for t in o if topo[t] in PLATEAU)))
        elif o and all(topo[t] != 49 for t in o):
            foot_edges.append((e, w[0], o[0]))
    if not crest_edges:
        continue
    n_crest_edges += len(crest_edges)

    # ---- R2: silhouette over ordered chains (per component) ---------------------------------
    comp_crest = defaultdict(list)
    for e, wt, pt in crest_edges:
        comp_crest[comp_of[wt]].append((e, wt, pt))
    for root, ces in comp_crest.items():
        chains = build_chains([e for e, _, _ in ces])
        for ch in chains:
            ys = [p[1] for p in ch]
            med_y = float(np.median(ys))
            for p in ch:
                y_detr.append(round(float(p[1] - med_y), 2))
            turns_here = []
            for i in range(len(ch) - 1):
                d = ch[i + 1] - ch[i]
                seg_lens.append(round(float(math.hypot(d[0], d[2])), 2))
                dy_edge.append(round(abs(float(d[1])), 2))
            for i in range(1, len(ch) - 1):
                a = (ch[i] - ch[i - 1])[[0, 2]]
                b = (ch[i + 1] - ch[i])[[0, 2]]
                La, Lb = np.linalg.norm(a), np.linalg.norm(b)
                if La < 1e-6 or Lb < 1e-6:
                    continue
                ang = math.degrees(math.acos(max(-1.0, min(1.0, float(a @ b) / (La * Lb)))))
                sgn = 1.0 if float(a[0] * b[1] - a[1] * b[0]) >= 0 else -1.0
                turn_mags.append(round(ang, 1))
                turns_here.append((ang, sgn))
            big = [(m, s) for m, s in turns_here if m > 15.0]
            for i in range(1, len(big)):
                alt_flags.append(1 if big[i][1] != big[i - 1][1] else 0)
        if len(ces) >= 8:                                   # candidate for the render
            render_comps.append(dict(n=len(ces), block=(bx, by),
                                     edges=[e for e, _, _ in ces], _blockdata=None))

    # ---- R1: the rim ring's construction ----------------------------------------------------
    ring1 = {pt for _, _, pt in crest_edges}
    n_ring1_tris += len(ring1)
    ring2 = set()
    for e, ts in edge_tris.items():
        if any(t in ring1 for t in ts):
            for t in ts:
                if topo[t] in PLATEAU and t not in ring1:
                    ring2.add(t)
    crest_keys = {p for e, _, _ in crest_edges for p in e}
    inner_edges = []
    for e, ts in edge_tris.items():
        r1 = [t for t in ts if t in ring1]
        r2p = [t for t in ts if topo[t] in PLATEAU and t not in ring1]
        if len(r1) == 1 and r2p:
            inner_edges.append(e)
    inner_keys = {p for e in inner_edges for p in e} - crest_keys
    for p in crest_keys:
        res_crest.append(round(lat_res(p), 2))
    for p in inner_keys:
        res_inner.append(round(lat_res(p), 2))
    far_seen = set()
    for t in range(ntri):
        if topo[t] in PLATEAU and t not in ring1 and t not in ring2:
            a, b, c = (np.array(V[i], dtype=float) for i in tri_idx[t])
            ar, ma = plan_area(a, b, c), plan_min_angle(a, b, c)
            if ma is not None:
                r1_shape["far"]["area"].append(round(ar, 2))
                r1_shape["far"]["mina"].append(round(ma, 1))
            for i in tri_idx[t]:
                p = kk(V[i])
                if p not in far_seen:
                    far_seen.add(p)
                    res_far.append(round(lat_res(p), 2))
    for t in ring1:
        a, b, c = (np.array(V[i], dtype=float) for i in tri_idx[t])
        ar, ma = plan_area(a, b, c), plan_min_angle(a, b, c)
        if ma is not None:
            r1_shape["ring"]["area"].append(round(ar, 2))
            r1_shape["ring"]["mina"].append(round(ma, 1))
    CM = np.array([[(e[0][0] + e[1][0]) / 2.0, (e[0][2] + e[1][2]) / 2.0]
                   for e, _, _ in crest_edges])
    CD = []
    for e, _, _ in crest_edges:
        d = np.array([e[1][0] - e[0][0], e[1][2] - e[0][2]])
        L = np.linalg.norm(d)
        CD.append(d / L if L > 1e-9 else np.array([1.0, 0.0]))
    CD = np.array(CD)
    for e in inner_edges:
        m = np.array([(e[0][0] + e[1][0]) / 2.0, (e[0][2] + e[1][2]) / 2.0])
        j = int(np.argmin(np.hypot(CM[:, 0] - m[0], CM[:, 1] - m[1])))
        d = np.array([e[1][0] - e[0][0], e[1][2] - e[0][2]])
        L = np.linalg.norm(d)
        if L < 1e-9:
            continue
        d = d / L
        ang = math.degrees(math.acos(max(-1.0, min(1.0, abs(float(d @ CD[j]))))))
        inner_align.append(round(ang, 1))
        a3, b3 = np.array(crest_edges[j][0][0]), np.array(crest_edges[j][0][1])
        a2, b2 = a3[[0, 2]], b3[[0, 2]]
        ab = b2 - a2
        t_ = float(np.clip(((m - a2) @ ab) / max(1e-9, float(ab @ ab)), 0.0, 1.0))
        inner_off.append(round(float(np.linalg.norm(m - (a2 + t_ * ab))), 2))

    # ---- R3: the top course, both sides -----------------------------------------------------
    for t in ring1:
        ring1_tiles[tile_of([U[i] for i in tri_idx[t]])] += 1
    for t in ring2:
        ring2_tiles[tile_of([U[i] for i in tri_idx[t]])] += 1
    seen_wt = set()
    crest_wall = set()
    for e, wt, pt in crest_edges:
        crest_wall.add(wt)
        ek = set(e)
        fON = [frac_uv(*U[i]) for i in tri_idx[pt] if kk(V[i]) in ek]
        fOF = [frac_uv(*U[i]) for i in tri_idx[pt] if kk(V[i]) not in ek]
        if fON and fOF:
            plat_dv.append(round(float(np.mean([q[1] for q in fON]) -
                                       np.mean([q[1] for q in fOF])), 3))
            plat_du.append(round(float(np.mean([q[0] for q in fON]) -
                                       np.mean([q[0] for q in fOF])), 3))
            plat_fv_on.extend(round(q[1], 3) for q in fON)
        if wt in seen_wt:
            continue
        seen_wt.add(wt)
        wall_top_tiles[tile_of([U[i] for i in tri_idx[wt]])] += 1
        wys = [V[i][1] for i in tri_idx[wt]]
        wall_course_h.append(round(float((e[0][1] + e[1][1]) / 2.0 - min(wys)), 2))
        vr = [(V[i][1], (U[i][1] - PV) / TILE_V) for i in tri_idx[wt]]      # unwrapped v-rows
        top_span.append(round(max(q[1] for q in vr) - min(q[1] for q in vr), 3))
        my_ = np.mean([q[0] for q in vr])
        mv_ = np.mean([q[1] for q in vr])
        cov_ = float(np.mean([(q[0] - my_) * (q[1] - mv_) for q in vr]))
        if abs(cov_) > 1e-6:
            top_vy_up.append(1 if cov_ > 0 else 0)          # 1 = v grows with HEIGHT
        wON = [frac_uv(*U[i]) for i in tri_idx[wt] if kk(V[i]) in ek]
        wOF = [frac_uv(*U[i]) for i in tri_idx[wt] if kk(V[i]) not in ek]
        if wON and wOF:
            wall_fv_on.extend(round(q[1], 3) for q in wON)
            wall_dv.append(round(float(np.mean([q[1] for q in wON]) -
                                       np.mean([q[1] for q in wOF])), 3))
    foot_wall = {wt for _, wt, _ in foot_edges}
    for t in wall_tris:
        if t not in crest_wall and t not in foot_wall:
            wall_mid_tiles[tile_of([U[i] for i in tri_idx[t]])] += 1

    # ---- R4: overhang + setback vs the crest line -------------------------------------------
    OWU = []
    for e, wt, pt in crest_edges:
        mid = np.array([(e[0][0] + e[1][0]) / 2.0, (e[0][2] + e[1][2]) / 2.0])
        pc = np.mean([[V[i][0], V[i][2]] for i in tri_idx[pt]], axis=0)
        ow = mid - pc
        L = np.linalg.norm(ow)
        OWU.append(ow / L if L > 1e-9 else np.array([1.0, 0.0]))
    OWU = np.array(OWU)
    CY = np.array([(e[0][1] + e[1][1]) / 2.0 for e, _, _ in crest_edges])
    for root, ces in comp_crest.items():
        vkeys = {kk(V[i]) for t in comp_tris[root] for i in tri_idx[t]}
        for p in vkeys:
            w2 = np.array([p[0], p[2]])
            dd = np.hypot(CM[:, 0] - w2[0], CM[:, 1] - w2[1])
            j = int(np.argmin(dd))
            if float(dd[j]) > 8.0:                          # only verts NEAR their crest edge:
                continue                                    # distant along-wall geometry is not rim
            drop = float(CY[j] - p[1])
            rel = w2 - CM[j]
            perp = rel - float(rel @ CD[j]) * CD[j]
            exc = float(perp @ OWU[j])
            if drop <= 1.5:
                jut_exc.append(round(exc, 2))
            for lo, hi, name in ((0.5, 1.5, "d1"), (1.5, 2.5, "d2"), (3.0, 5.0, "d4")):
                if lo <= drop < hi:
                    setback[name].append(round(exc, 2))

    # ---- R5: the bottom course's rows + v usage ---------------------------------------------
    for t in foot_wall:
        tl = tile_of([U[i] for i in tri_idx[t]])
        bot_row_hist[tl[1]] += 1
        ys = [V[i][1] for i in tri_idx[t]]
        h = round(float(max(ys) - min(ys)), 2)
        if tl[1] == 10:
            row10_h.append(h)
            vr = [(V[i][1], (U[i][1] - PV) / TILE_V) for i in tri_idx[t]]   # unwrapped v-rows
            row10_span.append(round(max(q[1] for q in vr) - min(q[1] for q in vr), 3))
            my = np.mean([q[0] for q in vr])
            mv = np.mean([q[1] for q in vr])
            cov = float(np.mean([(q[0] - my) * (q[1] - mv) for q in vr]))
            if abs(cov) > 1e-6:
                row10_vy_up.append(1 if cov > 0 else 0)     # 1 = v grows with HEIGHT
            for i in tri_idx[t]:
                row10_fv.append(round(frac_uv(*U[i])[1], 3))
        else:
            bot_other_h.append(h)

    # ---- render capture (top-3 by crest size, data-complete) --------------------------------
    for rc in render_comps:
        if rc["block"] == (bx, by) and rc["_blockdata"] is None:
            rc["_blockdata"] = dict(
                ring1=[[(V[i][0], V[i][2]) for i in tri_idx[t]] for t in ring1],
                ring2=[[(V[i][0], V[i][2]) for i in tri_idx[t]] for t in ring2],
                inner=[((e[0][0], e[0][2]), (e[1][0], e[1][2])) for e in inner_edges])

render_comps.sort(key=lambda rc: -rc["n"])
render_comps = [rc for rc in render_comps if rc["_blockdata"]][:3]


# ---- summaries ------------------------------------------------------------------------------
def pct(a, q):
    return round(float(np.percentile(a, q)), 2) if len(a) else None


def dist(a, name, unit=""):
    return (f"{name}: n={len(a)} med {pct(a, 50)}{unit} p25 {pct(a, 25)} "
            f"p75 {pct(a, 75)} p90 {pct(a, 90)} p99 {pct(a, 99)}")


print(f"population: {n_blocks} blocks, {n_comps} components, {n_crest_edges} crest edges\n")

print("== R1 THE RIM RING (deformed course vs lattice clip) ==")
print(f"   lattice residual (plan dist to the 4u grid):")
print(f"      crest verts:  {dist(res_crest, 'res', 'u')}; on-grid (<0.3u): "
      f"{sum(1 for r in res_crest if r < 0.3) / max(1, len(res_crest)):.1%}")
print(f"      inner ring:   {dist(res_inner, 'res', 'u')}; on-grid: "
      f"{sum(1 for r in res_inner if r < 0.3) / max(1, len(res_inner)):.1%}")
print(f"      far plateau:  {dist(res_far, 'res', 'u')}; on-grid: "
      f"{sum(1 for r in res_far if r < 0.3) / max(1, len(res_far)):.1%}")
print(f"   ring-1 tris per crest edge: {n_ring1_tris / max(1, n_crest_edges):.2f} "
      f"({n_ring1_tris} tris / {n_crest_edges} edges)")
for k, lab in (("ring", "ring-1"), ("far", "far plateau")):
    ar, ma = r1_shape[k]["area"], r1_shape[k]["mina"]
    sliv = sum(1 for a_, m_ in zip(ar, ma) if a_ < 2.0 or m_ < 15.0) / max(1, len(ar))
    print(f"   {lab:11s} shape: area med {pct(ar, 50)}u2 p25 {pct(ar, 25)} p75 {pct(ar, 75)}; "
          f"min-angle med {pct(ma, 50)} p10 {pct(ma, 10)}; SLIVER frac {sliv:.1%}")
print(f"   inner boundary vs crest: align angle med {pct(inner_align, 50)} "
      f"p90 {pct(inner_align, 90)} (0 = parallel); offset med {pct(inner_off, 50)}u "
      f"p25 {pct(inner_off, 25)} p75 {pct(inner_off, 75)}")

print("\n== R2 THE CREST SILHOUETTE ==")
print(f"   {dist(seg_lens, 'segment length', 'u')}")
tb = [(0, 5), (5, 15), (15, 30), (30, 60), (60, 90), (90, 181)]
tot = max(1, len(turn_mags))
hist = {f"{lo}-{hi}": round(sum(1 for t in turn_mags if lo <= t < hi) / tot, 3)
        for lo, hi in tb}
print(f"   plan turn per interior vert: med {pct(turn_mags, 50)} p90 {pct(turn_mags, 90)} "
      f"p99 {pct(turn_mags, 99)}; hist {hist}")
print(f"   sign alternation of consecutive >15-deg turns: "
      f"{np.mean(alt_flags):.1%} (n={len(alt_flags)})" if alt_flags else "   (no big-turn pairs)")
print(f"   {dist(dy_edge, 'per-edge |dy|', 'u')}")
print(f"   {dist([abs(y) for y in y_detr], 'detrended |y| dev', 'u')}")

print("\n== R3 THE TOP COURSE ==")
print(f"   ring-1 tiles: {ring1_tiles.most_common(8)}")
print(f"   ring-2 tiles: {ring2_tiles.most_common(8)}")
print(f"   plateau side, weld-edge uv: dv(on-off) med {pct(plat_dv, 50)} "
      f"|dv| med {pct([abs(q) for q in plat_dv], 50)}; |du| med "
      f"{pct([abs(q) for q in plat_du], 50)}; fv at the weld med {pct(plat_fv_on, 50)} "
      f"p25 {pct(plat_fv_on, 25)} p75 {pct(plat_fv_on, 75)}")
print(f"   wall top course: height below crest med {pct(wall_course_h, 50)}u "
      f"p90 {pct(wall_course_h, 90)}; fv at the crest med {pct(wall_fv_on, 50)} "
      f"p25 {pct(wall_fv_on, 25)} p75 {pct(wall_fv_on, 75)}; dv(on-off) med {pct(wall_dv, 50)}")
print(f"   wall TOP tiles: {wall_top_tiles.most_common(10)}")
print(f"   wall MID tiles: {wall_mid_tiles.most_common(10)}")

print("\n== R4 OVERHANG / SETBACK vs the crest line ==")
print(f"   near-crest (drop<=1.5u) outward excursion: med {pct(jut_exc, 50)}u "
      f"p90 {pct(jut_exc, 90)} p99 {pct(jut_exc, 99)} max "
      f"{max(jut_exc) if jut_exc else None}; beyond-crest (>0.3u): "
      f"{sum(1 for e in jut_exc if e > 0.3) / max(1, len(jut_exc)):.1%}")
for name, lab in (("d1", "drop 0.5-1.5u"), ("d2", "drop 1.5-2.5u"), ("d4", "drop 3-5u")):
    a = setback[name]
    print(f"   setback at {lab}: med {pct(a, 50)}u p25 {pct(a, 25)} p75 {pct(a, 75)} "
          f"(+ve = outward of the crest)")

print("\n== R5 THE FOOT COURSE'S SHADE ==")
tot_b = max(1, sum(bot_row_hist.values()))
print(f"   bottom-course atlas ROW histogram: {bot_row_hist.most_common(8)} "
      f"(row-10 share: {bot_row_hist.get(10, 0) / tot_b:.1%})")
print(f"   row-10 tris: height med {pct(row10_h, 50)}u p90 {pct(row10_h, 90)}; "
      f"v-fraction used: p10 {pct(row10_fv, 10)} med {pct(row10_fv, 50)} p90 {pct(row10_fv, 90)}")
print(f"   row-10 unwrapped v-row SPAN per tri: med {pct(row10_span, 50)} p90 "
      f"{pct(row10_span, 90)}; v grows with HEIGHT: "
      f"{np.mean(row10_vy_up):.1%} of {len(row10_vy_up)} tris" if row10_vy_up else "")
print(f"   wall TOP course unwrapped v-row span: med {pct(top_span, 50)} p90 "
      f"{pct(top_span, 90)}; v grows with HEIGHT: "
      f"{np.mean(top_vy_up):.1%} of {len(top_vy_up)} tris" if top_vy_up else "")
print(f"   non-row-10 bottom tris: height med {pct(bot_other_h, 50)}u")

atlas_lum = {}
try:
    from ff9mapkit.world import atlas as A
    im, src = None, None
    try:
        im = A.load_atlas("terrain", source="bundle")
        if isinstance(im, tuple):
            im, src = im
    except TypeError:
        im = A.load_atlas("terrain")
    AR = np.asarray(im.convert("RGB"), dtype=float)
    H_, W_ = AR.shape[:2]
    LUM = 0.299 * AR[:, :, 0] + 0.587 * AR[:, :, 1] + 0.114 * AR[:, :, 2]

    def tile_lum(col, row, v_lo=0.0, v_hi=1.0):
        u0 = (PU + col * TILE_U) % 1.0
        v0 = (PV + row * TILE_V) % 1.0
        x0, x1 = int(u0 * W_), int((u0 + TILE_U) * W_)
        ya = int((1.0 - (v0 + v_hi * TILE_V)) * H_)
        yb = int((1.0 - (v0 + v_lo * TILE_V)) * H_)
        sub = LUM[max(0, ya):max(0, yb), max(0, x0):min(W_, x1)]
        return round(float(sub.mean()), 1) if sub.size else None

    fv_lo, fv_hi = (pct(row10_fv, 10) or 0.0), (pct(row10_fv, 90) or 1.0)
    mids = [t for t, _ in wall_mid_tiles.most_common(6)]
    r10 = [(c, 10) for c in (6, 7, 8, 9)]
    print(f"\n   atlas {W_}x{H_} loaded; per-tile mean luminance (0-255):")
    for c, r in r10:
        full = tile_lum(c, r)
        used = tile_lum(c, r, fv_lo, fv_hi)
        strips = [tile_lum(c, r, s / 8.0, (s + 1) / 8.0) for s in range(8)]
        atlas_lum[f"{c},{r}"] = dict(full=full, used=used, strips=strips)
        print(f"      row10 ({c:2d},10): full {full}  stock-subrange[{fv_lo}-{fv_hi}] {used}  "
              f"v-strips(low->high v) {strips}")
    for c, r in mids:
        full = tile_lum(c, r)
        atlas_lum[f"{c},{r}"] = dict(full=full)
        print(f"      mid   ({c:2d},{r:2d}): full {full}")
    for c, r in [(c, r) for r in (3, 4) for c in (4, 5, 6, 7)]:
        full = tile_lum(c, r)
        atlas_lum[f"{c},{r}"] = dict(full=full)
        print(f"      TOPband ({c:2d},{r:2d}): full {full}  v-strips {[tile_lum(c, r, s / 4.0, (s + 1) / 4.0) for s in range(4)]}")

    # eyeball crops of the four bands, mapped exactly as tile_lum maps them
    def band_crop(c0, c1, r0, r1):
        x0 = int(((PU + c0 * TILE_U) % 1.0) * W_)
        x1 = x0 + int((c1 - c0 + 1) * TILE_U * W_)
        ya = int((1.0 - ((PV + (r1 + 1) * TILE_V) % 1.0)) * H_)
        yb = int((1.0 - ((PV + r0 * TILE_V) % 1.0)) * H_)
        return im.convert("RGB").crop((max(0, x0), max(0, ya), min(W_, x1), max(0, yb)))

    bands = [("wall TOP band cols4-7 rows3-4", band_crop(4, 7, 3, 4)),
             ("mid-face cols0-3 rows6-7", band_crop(0, 3, 6, 7)),
             ("FOOT band cols6-9 rows9-11", band_crop(6, 9, 9, 11)),
             ("plateau grass cols0-1 rows24-25", band_crop(0, 1, 24, 25))]
    SC2 = 3
    bw = max(b.width for _, b in bands) * SC2 + 16
    bh = sum(b.height * SC2 + 26 for _, b in bands) + 8
    strip_img = Image.new("RGB", (bw, bh), (24, 26, 30))
    sd = ImageDraw.Draw(strip_img)
    yy = 4
    for lab, b in bands:
        sd.text((8, yy), lab + "  (top of crop = HIGH v)", fill=(220, 220, 220))
        yy += 18
        strip_img.paste(b.resize((b.width * SC2, b.height * SC2), Image.NEAREST), (8, yy))
        yy += b.height * SC2 + 8
    bpng = Path(__file__).with_name("out") / "rim_atlas_bands.png"
    strip_img.save(bpng)
    print(f"   atlas band crops -> {bpng}")
except Exception as ex:                                     # noqa: BLE001
    print(f"\n   !! atlas luminance skipped: {ex}")

# ---- the rim-course render ------------------------------------------------------------------
PNG.parent.mkdir(parents=True, exist_ok=True)
PW = 380
img = Image.new("RGB", (PW * max(1, len(render_comps)), 420), (24, 26, 30))
dr = ImageDraw.Draw(img)
for pi, rc in enumerate(render_comps):
    bd = rc["_blockdata"]
    pts = [p for e in rc["edges"] for p in e]
    xs = [p[0] for p in pts]
    zs = [p[2] for p in pts]
    cx, cz = (min(xs) + max(xs)) / 2.0, (min(zs) + max(zs)) / 2.0
    span = max(max(xs) - min(xs), max(zs) - min(zs), 8.0)
    sc = 340.0 / (span + 8.0)
    ox = pi * PW + PW // 2

    def M(p, ox=ox, cx=cx, cz=cz, sc=sc):
        return (ox + (p[0] - cx) * sc, 210 + (p[1 if len(p) == 2 else 2] - cz) * sc)

    for tri in bd["ring2"]:
        q = [M((x, z)) for x, z in tri]
        dr.polygon(q, outline=(70, 74, 84))
    for tri in bd["ring1"]:
        q = [M((x, z)) for x, z in tri]
        dr.polygon(q, outline=(90, 200, 120))
    for a, b in bd["inner"]:
        dr.line([M(a), M(b)], fill=(90, 170, 220), width=1)
    for e in rc["edges"]:
        dr.line([M((e[0][0], e[0][2])), M((e[1][0], e[1][2]))], fill=(245, 220, 90), width=2)
    dr.text((pi * PW + 8, 6), f"block {rc['block']}  {rc['n']} crest edges",
            fill=(220, 220, 220))
dr.text((8, 402), "yellow = crest  green = ring-1 tris  cyan = inner boundary  "
                  "gray = ring-2", fill=(170, 170, 180))
img.save(PNG)
print(f"\nrim course render -> {PNG}")

OUT.write_text(json.dumps(dict(
    population=dict(blocks=n_blocks, comps=n_comps, crest_edges=n_crest_edges),
    r1=dict(res_crest_med=pct(res_crest, 50), res_inner_med=pct(res_inner, 50),
            res_far_med=pct(res_far, 50),
            on_grid=dict(crest=round(sum(1 for r in res_crest if r < 0.3) / max(1, len(res_crest)), 3),
                         inner=round(sum(1 for r in res_inner if r < 0.3) / max(1, len(res_inner)), 3),
                         far=round(sum(1 for r in res_far if r < 0.3) / max(1, len(res_far)), 3)),
            ring1_per_edge=round(n_ring1_tris / max(1, n_crest_edges), 3),
            shape={k: dict(area_med=pct(v["area"], 50), area_p25=pct(v["area"], 25),
                           area_p75=pct(v["area"], 75), mina_med=pct(v["mina"], 50),
                           mina_p10=pct(v["mina"], 10),
                           sliver=round(sum(1 for a_, m_ in zip(v["area"], v["mina"])
                                            if a_ < 2.0 or m_ < 15.0) / max(1, len(v["area"])), 3))
                   for k, v in r1_shape.items()},
            inner_align_med=pct(inner_align, 50), inner_align_p90=pct(inner_align, 90),
            inner_off=dict(med=pct(inner_off, 50), p25=pct(inner_off, 25),
                           p75=pct(inner_off, 75))),
    r2=dict(seg_len=dict(med=pct(seg_lens, 50), p25=pct(seg_lens, 25), p75=pct(seg_lens, 75),
                         p90=pct(seg_lens, 90)),
            turn=dict(med=pct(turn_mags, 50), p90=pct(turn_mags, 90), p99=pct(turn_mags, 99),
                      hist=hist),
            alternation=round(float(np.mean(alt_flags)), 3) if alt_flags else None,
            dy_edge=dict(med=pct(dy_edge, 50), p90=pct(dy_edge, 90)),
            y_detr=dict(med=pct([abs(y) for y in y_detr], 50),
                        p90=pct([abs(y) for y in y_detr], 90))),
    r3=dict(ring1_tiles={f"{c},{r}": n for (c, r), n in ring1_tiles.most_common(16)},
            ring2_tiles={f"{c},{r}": n for (c, r), n in ring2_tiles.most_common(16)},
            plat_dv_med=pct(plat_dv, 50), plat_du_abs_med=pct([abs(q) for q in plat_du], 50),
            plat_fv_on=dict(med=pct(plat_fv_on, 50), p25=pct(plat_fv_on, 25),
                            p75=pct(plat_fv_on, 75)),
            wall_course_h=dict(med=pct(wall_course_h, 50), p90=pct(wall_course_h, 90)),
            wall_fv_on=dict(med=pct(wall_fv_on, 50), p25=pct(wall_fv_on, 25),
                            p75=pct(wall_fv_on, 75)),
            wall_dv_med=pct(wall_dv, 50),
            top_span=dict(med=pct(top_span, 50), p90=pct(top_span, 90)),
            top_v_grows_with_height=round(float(np.mean(top_vy_up)), 3) if top_vy_up else None,
            wall_top_tiles={f"{c},{r}": n for (c, r), n in wall_top_tiles.most_common(16)},
            wall_mid_tiles={f"{c},{r}": n for (c, r), n in wall_mid_tiles.most_common(16)}),
    r4=dict(jut=dict(med=pct(jut_exc, 50), p90=pct(jut_exc, 90), p99=pct(jut_exc, 99),
                     max=max(jut_exc) if jut_exc else None,
                     beyond=round(sum(1 for e in jut_exc if e > 0.3) / max(1, len(jut_exc)), 3)),
            setback={k: dict(med=pct(v, 50), p25=pct(v, 25), p75=pct(v, 75))
                     for k, v in setback.items()}),
    r5=dict(bot_rows=dict(bot_row_hist), row10_share=round(bot_row_hist.get(10, 0) / tot_b, 3),
            row10_h=dict(med=pct(row10_h, 50), p90=pct(row10_h, 90)),
            row10_fv=dict(p10=pct(row10_fv, 10), med=pct(row10_fv, 50), p90=pct(row10_fv, 90)),
            row10_span=dict(med=pct(row10_span, 50), p90=pct(row10_span, 90)),
            row10_v_grows_with_height=round(float(np.mean(row10_vy_up)), 3) if row10_vy_up else None,
            other_h_med=pct(bot_other_h, 50), atlas_lum=atlas_lum)),
    indent=0))
print(f"artifacts -> {OUT}")
