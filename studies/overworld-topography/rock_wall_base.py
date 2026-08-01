"""ROCK-WALL BASE-TILE GRAMMAR -- how stock PLACES the bottom transitional course
(the 6th wall study).

The whole-mesa carry passed on form; the re-minted foot fringe FAILED as mismatched
faces (studies/path-d-new-world/MESA-CARRY-PREDICTION.md playtest 2). R5 measured the
band per-tri (share/height/v-range); this instrument decodes its PLACEMENT:

  B1 U-PHASE INHERITANCE -- across the course seam (bottom course vs the course
     DIRECTLY ABOVE): shared-vertex-index fraction, |du| in column units, the
     (row_below -> row_above) relation histogram. Column continuation vs fresh band.
  B2 COLUMN QUANTIZATION -- run/gap transitions vs column boundaries (fu at the
     transition vertex), run/gap extents in COLUMN units, per-foot-edge u-extent.
  B3 THE V-SEAM -- unwrapped v-row sampled by both sides of the seam edge (is the
     band's top edge pinned, and does the course above END v-adjacent to it?).
  B4 ADJACENCY -- side (vertical) edges within the bottom course: texture
     continuity (du in cols at shared verts) inside runs / at transitions / by row
     pair; plus foot-line corner behavior (does the band avoid high-turn verts?).

Questions registered in studies/path-d-new-world/BASE-TILE-GRAMMAR.md BEFORE this
ran. Read-only vs stock disc-1. Artifacts -> out/rock_wall_base.json +
out/base_strip.png (an unwrapped two-band strip of the longest foot stretch).
Regenerate: py -X utf8 rock_wall_base.py
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
OUT = Path(__file__).with_name("out") / "rock_wall_base.json"
PNG = Path(__file__).with_name("out") / "base_strip.png"
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))   # noqa: E731

PU, PV = json.loads((Path(__file__).with_name("out") / "rock_tiles.json").read_text())["phase"]


def tile_of(uvs):
    us = [q[0] for q in uvs]
    vs = [q[1] for q in uvs]
    return (int(math.floor((min(us) - PU) / TILE_U + 0.5)),
            int(math.floor((min(vs) - PV) / TILE_V + 0.5)))


def ucol(u):
    return (u - PU) / TILE_U


def vrow(v):
    return (v - PV) / TILE_V


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
        if len(adj[a]) != 2:
            for b in adj[a]:
                if frozenset((a, b)) not in done:
                    chains.append(walk(a, b))
    for a in adj:                                           # pure cycles
        for b in adj[a]:
            if frozenset((a, b)) not in done:
                chains.append(walk(a, b))
    return [[pt3[q] for q in ch] for ch in chains if len(ch) >= 2]


# ---- accumulators ---------------------------------------------------------------------------
b1_same_idx = dict(r10=[], oth=[])                          # seam verts: same vertex index?
b1_du = dict(r10=[], oth=[])                                # seam verts: |du| in cols
b1_dv = dict(r10=[], oth=[])                                # seam verts: v_below - v_above (rows)
b1_rel = Counter()                                          # (row_below, row_above) histogram
b1_col_rel = Counter()                                      # col relation at the seam
b3_v_below = dict(r10=[], oth=[])                           # unwrapped v-row on the seam edge
b3_v_above = dict(r10=[], oth=[])
b2_fu_trans = []                                            # dist to a col boundary at transitions
b2_du_trans = []                                            # |du| cols across the transition vertex
b2_run_cols, b2_gap_cols = [], []                           # run/gap extents in column units
b2_run_frac, b2_gap_frac = [], []                           # their distance to the nearest integer
b2_edge_cols = []                                           # per-foot-edge u-extent (cols)
b4_du = dict(both10=[], neither=[], mixed=[])               # side-edge |du| cols at shared verts
b4_same_idx = dict(both10=[], neither=[], mixed=[])
b4_corner_rows = Counter()                                  # rows flanking >=45-deg foot corners
b4_corner_base = Counter()                                  # rows flanking ALL interior foot verts
n_blocks = n_comps = n_seam = n_side = 0
render_strip = None                                         # longest chain's band data for the PNG

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

    foot_edges = []                                         # (edge, wall_tri, other_tri)
    for e, ts in edge_tris.items():
        w = [t for t in ts if t in wall_tris]
        if len(w) != 1 or comp_of[w[0]] not in comp_band:
            continue
        o = [t for t in ts if t not in wall_tris]
        if o and all(topo[t] not in PLATEAU and topo[t] != 49 for t in o):
            foot_edges.append((e, w[0], o[0]))
    if not foot_edges:
        continue

    # ---- the bottom COURSE: wall tris touching the foot polyline ----------------------------
    foot_keys = {p for e, _, _ in foot_edges for p in e}
    BC = {t for t in wall_tris
          if comp_of[t] in comp_band and any(kk(V[i]) in foot_keys for i in tri_idx[t])}
    row_of = {t: tile_of([U[i] for i in tri_idx[t]])[1] for t in BC}
    col_of = {t: tile_of([U[i] for i in tri_idx[t]])[0] for t in BC}
    cy = {t: float(np.mean([V[i][1] for i in tri_idx[t]])) for t in wall_tris}

    def corners_at(t, p):
        return [i for i in tri_idx[t] if kk(V[i]) == p]

    # ---- B1/B3: the course seam -------------------------------------------------------------
    for e, ts in edge_tris.items():
        w = [t for t in ts if t in wall_tris and comp_of[t] in comp_band]
        if len(w) != 2:
            continue
        inb = [t for t in w if t in BC]
        if len(inb) != 1:
            continue
        tb, ta = inb[0], next(t for t in w if t not in BC)
        if cy[ta] <= cy[tb]:
            continue                                        # under-ledge geometry, not the course above
        dy = abs(e[0][1] - e[1][1])
        plan = math.hypot(e[0][0] - e[1][0], e[0][2] - e[1][2])
        if dy >= min(plan, 2.0):
            continue                                        # diagonal / side edge, not a course seam
        n_seam += 1
        rb = row_of[tb]
        ra = tile_of([U[i] for i in tri_idx[ta]])[1]
        ca = tile_of([U[i] for i in tri_idx[ta]])[0]
        b1_rel[(rb, ra)] += 1
        b1_col_rel["same" if ca == col_of[tb] else "diff"] += 1
        key = "r10" if rb == 10 else "oth"
        for p in e:
            ib = corners_at(tb, p)
            ia = corners_at(ta, p)
            if not ib or not ia:
                continue
            ib, ia = ib[0], ia[0]
            b1_same_idx[key].append(1 if ib == ia else 0)
            b1_du[key].append(round(abs(ucol(U[ib][0]) - ucol(U[ia][0])), 3))
            b1_dv[key].append(round(vrow(U[ib][1]) - vrow(U[ia][1]), 3))
            b3_v_below[key].append(round(vrow(U[ib][1]), 3))
            b3_v_above[key].append(round(vrow(U[ia][1]), 3))

    # ---- B4: side edges within the bottom course --------------------------------------------
    for e, ts in edge_tris.items():
        w = [t for t in ts if t in BC]
        if len(w) != 2:
            continue
        dy = abs(e[0][1] - e[1][1])
        plan = math.hypot(e[0][0] - e[1][0], e[0][2] - e[1][2])
        if dy < 2.0 or plan > dy + 2.0:
            continue                                        # keep steep side edges; skip hypotenuses
        if col_of[w[0]] == col_of[w[1]] and row_of[w[0]] == row_of[w[1]]:
            continue                                        # same-cell pair (split diagonal variants)
        n_side += 1
        r0, r1 = row_of[w[0]], row_of[w[1]]
        key = "both10" if r0 == 10 and r1 == 10 else ("neither" if 10 not in (r0, r1) else "mixed")
        for p in e:
            i0 = corners_at(w[0], p)
            i1 = corners_at(w[1], p)
            if not i0 or not i1:
                continue
            i0, i1 = i0[0], i1[0]
            b4_same_idx[key].append(1 if i0 == i1 else 0)
            b4_du[key].append(round(abs(ucol(U[i0][0]) - ucol(U[i1][0])), 3))

    # ---- B2: transitions + run/gap extents in COLUMN units along the foot chains ------------
    einfo = {}                                              # foot edge -> (row, wall tri)
    for e, wt, gt in foot_edges:
        einfo[frozenset((e[0], e[1]))] = (row_of.get(wt), wt)
    comp_foot = defaultdict(list)
    for e, wt, gt in foot_edges:
        comp_foot[comp_of[wt]].append(e)
    best_chain = None
    for root, fes in comp_foot.items():
        for ch in build_chains(fes):
            seq = []                                        # (edge key, row, wt, ucol extent)
            for i in range(len(ch) - 1):
                key = frozenset((kk(ch[i]), kk(ch[i + 1])))
                if key not in einfo or einfo[key][0] is None:
                    continue
                row, wt = einfo[key]
                ext = None
                ca = corners_at(wt, kk(ch[i]))
                cb = corners_at(wt, kk(ch[i + 1]))
                if ca and cb:
                    ext = abs(ucol(U[ca[0]][0]) - ucol(U[cb[0]][0]))
                    b2_edge_cols.append(round(ext, 3))
                seq.append((kk(ch[i]), kk(ch[i + 1]), row, wt, ext))
            if len(seq) >= 3 and (best_chain is None or len(seq) > len(best_chain)):
                best_chain = seq
            # corner census (B4) over interior chain verts
            for i in range(1, len(ch) - 1):
                a = (ch[i] - ch[i - 1])[[0, 2]]
                b = (ch[i + 1] - ch[i])[[0, 2]]
                La, Lb = np.linalg.norm(a), np.linalg.norm(b)
                if La < 1e-6 or Lb < 1e-6:
                    continue
                ang = math.degrees(math.acos(max(-1.0, min(1.0, float(a @ b) / (La * Lb)))))
                k1 = frozenset((kk(ch[i - 1]), kk(ch[i])))
                k2 = frozenset((kk(ch[i]), kk(ch[i + 1])))
                if k1 not in einfo or k2 not in einfo:
                    continue
                pair = tuple(sorted((einfo[k1][0] == 10, einfo[k2][0] == 10)))
                lab = {(True, True): "both10", (False, False): "neither",
                       (False, True): "mixed"}[pair]
                b4_corner_base[lab] += 1
                if ang >= 45.0:
                    b4_corner_rows[lab] += 1
            # transitions + run extents
            runs = []                                       # [is10, col extent]
            for i, (pa, pb, row, wt, ext) in enumerate(seq):
                is10 = row == 10
                if runs and runs[-1][0] == is10:
                    runs[-1][1] += ext or 0.0
                else:
                    if i > 0:                               # a transition at vertex pa
                        pw, pt_ = seq[i - 1][2], seq[i - 1][3]
                        cu = corners_at(wt, pa)
                        pu_ = corners_at(pt_, pa)
                        if cu and pu_:
                            fu = ucol(U[cu[0]][0]) % 1.0
                            b2_fu_trans.append(round(min(fu, 1.0 - fu), 3))
                            b2_du_trans.append(round(abs(ucol(U[cu[0]][0]) -
                                                         ucol(U[pu_[0]][0])), 3))
                    runs.append([is10, ext or 0.0])
            for is10, cols in runs[1:-1]:                   # interior runs only
                (b2_run_cols if is10 else b2_gap_cols).append(round(cols, 2))
                (b2_run_frac if is10 else b2_gap_frac).append(
                    round(abs(cols - round(cols)), 3))
    if best_chain and (render_strip is None or len(best_chain) > len(render_strip["seq"])):
        # capture uv + above-row detail for the render
        detail = []
        for pa, pb, row, wt, ext in best_chain:
            ra = None
            for e2, ts2 in edge_tris.items():               # the seam neighbor above, if any
                pass                                        # (looked up post-hoc below via b1 data)
            ua = corners_at(wt, pa)
            ub = corners_at(wt, pb)
            detail.append(dict(row=row, col=col_of.get(wt), ext=round(ext or 0.0, 3),
                               fu0=round(ucol(U[ua[0]][0]) % 1.0, 3) if ua else None,
                               fu1=round(ucol(U[ub[0]][0]) % 1.0, 3) if ub else None))
        render_strip = dict(block=(bx, by), seq=best_chain, detail=detail)


# ---- summaries ------------------------------------------------------------------------------
def pct(a, q):
    return round(float(np.percentile(a, q)), 2) if len(a) else None


def dist(a, name, unit=""):
    return (f"{name}: n={len(a)} med {pct(a, 50)}{unit} p25 {pct(a, 25)} "
            f"p75 {pct(a, 75)} p90 {pct(a, 90)} p99 {pct(a, 99)}")


def share(a, thr=0.02):
    return sum(1 for x in a if x < thr) / max(1, len(a))


print(f"population: {n_blocks} blocks, {n_comps} components, "
      f"{n_seam} course-seam edges, {n_side} bottom-course side edges\n")

print("== B1 U-PHASE INHERITANCE across the course seam ==")
for key, lab in (("r10", "row-10 below"), ("oth", "other-row below")):
    si = b1_same_idx[key]
    du = b1_du[key]
    print(f"   {lab:16s}: shared-INDEX {np.mean(si):.1%} of {len(si)} seam verts; "
          f"u-continuous (|du|<0.02 col) {share(du):.1%}; {dist(du, '|du|', ' col')}")
print(f"   (row_below -> row_above) top pairs: {b1_rel.most_common(10)}")
print(f"   seam col relation: {dict(b1_col_rel)}")

print("\n== B3 THE V-SEAM at the row boundary ==")
for key, lab in (("r10", "row-10"), ("oth", "other")):
    print(f"   {lab:7s} v_below at the seam: med {pct(b3_v_below[key], 50)} "
          f"p25 {pct(b3_v_below[key], 25)} p75 {pct(b3_v_below[key], 75)}; "
          f"v_above: med {pct(b3_v_above[key], 50)} p25 {pct(b3_v_above[key], 25)} "
          f"p75 {pct(b3_v_above[key], 75)}; dv(below-above) med {pct(b1_dv[key], 50)} "
          f"|dv|<0.02: {share([abs(q) for q in b1_dv[key]]):.1%}")

print("\n== B2 COLUMN QUANTIZATION of the intermittency ==")
print(f"   transition vertex dist to a col boundary (0 = pinned): "
      f"{dist(b2_fu_trans, 'min(fu,1-fu)', ' col')}; pinned (<0.05): "
      f"{share(b2_fu_trans, 0.05):.1%}")
print(f"   |du| across the transition vertex: {dist(b2_du_trans, '|du|', ' col')}; "
      f"continuous (<0.02): {share(b2_du_trans):.1%}")
print(f"   per-foot-edge u-extent: {dist(b2_edge_cols, 'extent', ' col')}; "
      f"exactly 1 col (+-0.1): "
      f"{sum(1 for x in b2_edge_cols if abs(x - 1.0) < 0.1) / max(1, len(b2_edge_cols)):.1%}")
print(f"   {dist(b2_run_cols, 'row-10 RUN extent', ' col')}; near-integer (+-0.1): "
      f"{share(b2_run_frac, 0.1):.1%}")
print(f"   {dist(b2_gap_cols, 'GAP extent', ' col')}; near-integer (+-0.1): "
      f"{share(b2_gap_frac, 0.1):.1%}")

print("\n== B4 ADJACENCY within the bottom course ==")
for key in ("both10", "neither", "mixed"):
    du = b4_du[key]
    si = b4_same_idx[key]
    print(f"   side edges {key:8s}: n={len(du)} verts; shared-INDEX "
          f"{np.mean(si):.1%}" if si else f"   side edges {key:8s}: n=0", end="")
    if du:
        print(f"; u-continuous {share(du):.1%}; {dist(du, '|du|', ' col')}")
    else:
        print()
print(f"   foot corners >=45 deg, flanking rows: {dict(b4_corner_rows)} "
      f"(all interior verts baseline: {dict(b4_corner_base)})")

# ---- render: the longest foot stretch, unwrapped, two bands ---------------------------------
if render_strip:
    seq = render_strip["seq"]
    det = render_strip["detail"]
    SC = 14.0                                               # px per u-col
    W = int(sum(max(0.25, d["ext"]) for d in det) * SC) + 40
    H = 130
    im = Image.new("RGB", (max(W, 400), H), (24, 24, 28))
    dr = ImageDraw.Draw(im)
    ROWCOL = {10: (150, 60, 40), 9: (110, 110, 90), 3: (100, 130, 100),
              5: (100, 100, 140), 6: (140, 120, 80)}
    x = 20.0
    for d in det:
        wpx = max(0.25, d["ext"]) * SC
        c = ROWCOL.get(d["row"], (90, 90, 90))
        dr.rectangle([x, 55, x + wpx, 105], fill=c, outline=(200, 200, 200))
        if wpx > 22:
            dr.text((x + 2, 72), f"{d['col']},{d['row']}", fill=(240, 240, 240))
        if d["fu0"] is not None and min(d["fu0"], 1 - d["fu0"]) > 0.05:
            dr.line([x, 50, x, 110], fill=(255, 80, 80), width=2)   # off-boundary start
        x += wpx
    dr.text((20, 10), f"block {render_strip['block']} longest foot stretch -- bottom course "
            f"(color=atlas row; red tick = edge start OFF a column boundary)",
            fill=(230, 230, 230))
    PNG.parent.mkdir(exist_ok=True)
    im.save(PNG)
    print(f"\nrender -> {PNG}")

OUT.write_text(json.dumps(dict(
    population=dict(blocks=n_blocks, comps=n_comps, seam_edges=n_seam, side_edges=n_side),
    b1=dict(same_idx={k: round(float(np.mean(v)), 3) if v else None
                      for k, v in b1_same_idx.items()},
            u_cont={k: round(share(v), 3) for k, v in b1_du.items()},
            du_med={k: pct(v, 50) for k, v in b1_du.items()},
            rel=[[list(k), n] for k, n in b1_rel.most_common(12)],
            col_rel=dict(b1_col_rel)),
    b3={k: dict(v_below_med=pct(b3_v_below[k], 50), v_below_p25=pct(b3_v_below[k], 25),
                v_below_p75=pct(b3_v_below[k], 75), v_above_med=pct(b3_v_above[k], 50),
                dv_med=pct(b1_dv[k], 50),
                dv_cont=round(share([abs(q) for q in b1_dv[k]]), 3))
        for k in ("r10", "oth")},
    b2=dict(fu_trans_med=pct(b2_fu_trans, 50), fu_pinned=round(share(b2_fu_trans, 0.05), 3),
            du_trans_med=pct(b2_du_trans, 50), du_trans_cont=round(share(b2_du_trans), 3),
            edge_cols_med=pct(b2_edge_cols, 50),
            edge_one_col=round(sum(1 for x in b2_edge_cols if abs(x - 1.0) < 0.1)
                               / max(1, len(b2_edge_cols)), 3),
            run_cols=dict(med=pct(b2_run_cols, 50), p25=pct(b2_run_cols, 25),
                          p75=pct(b2_run_cols, 75)),
            gap_cols=dict(med=pct(b2_gap_cols, 50), p25=pct(b2_gap_cols, 25),
                          p75=pct(b2_gap_cols, 75)),
            run_int=round(share(b2_run_frac, 0.1), 3), gap_int=round(share(b2_gap_frac, 0.1), 3)),
    b4=dict(du={k: dict(n=len(v), cont=round(share(v), 3), med=pct(v, 50))
                for k, v in b4_du.items()},
            same_idx={k: round(float(np.mean(v)), 3) if v else None
                      for k, v in b4_same_idx.items()},
            corners=dict(b4_corner_rows), corner_base=dict(b4_corner_base)),
), indent=1))
print(f"json -> {OUT}")
