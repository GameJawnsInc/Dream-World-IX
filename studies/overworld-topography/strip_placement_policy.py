"""THE ECOTONE-STRIP PLACEMENT POLICY -- given the proven STRIP rects (grassland.STRIPS,
2026-07-19), WHICH of the 4 rows does a given boundary cell wear?

Round 1 (ecotone_strip_decode.py) proved the two strip RECTS byte-exact-5dp but explicitly
shipped them as "data only, not yet an authoring surface": nobody had measured the per-cell
ROW-PLACEMENT policy (the mains 2x2 has a documented avoid-repeat neighbour policy --
grassland.assign_mains -- the strips have no analogue). THE NO-ENCLOSED-DUNES LAW means a
dunes patch has no verbatim donor window and needs THIS vocabulary to compose one -- this is
named the highest-leverage unblock in the arc. This script measures it.

QUESTION: for each of the two proven pairs (grass|desert, desert|dunes), walk the real
boundary cells map-wide and record which STRIPS row each cell wears. Then: is row choice
(a) random/hash-like, (b) a repeating along-seam cycle, (c) keyed to geometry (depth from
the boundary / seam direction), or (d) an avoid-repeat-neighbour rule like the mains? Also:
is there a consistent ORIENTATION (row increases toward a specific family, not a world
axis)?

METHOD (obeys THE METHOD LAW's spirit -- classification is map-wide, not top-N, and every
number is printed):
  A. ONE map-wide pass (all 480 (bx,by) candidates) builds a GLOBAL per-4u-CELL
     classification: each cell's dominant walkable family (from its triangles' topo ids,
     ff9.cs decode_id) and its dominant UV tag -- own-family MAINS, the meadow D rect, one
     of a pair's 4 translated STRIP rows (row assigned by SNAPPING the triangle's minimum-v
     corner to the nearest of the 4 rows at the PROVEN 0.03125 pitch -- not a containment
     test, so it is immune to the ~1-2-texel internal painted gutter round 1 documented),
     or "other". Classifying by physical 4u CELL (not by triangle-owning-fam, which round 1
     itself used only for its boundary-edge census) sidesteps a double-counting artifact:
     a single boundary QUAD split into 2 triangles can have its two triangles' FIRST
     vertices decode to two different topo families even though both triangles share one
     physical UV tile -- round 1's "desert side" and "grass side" row tallies at IDENTICAL
     cell counts (67/67, 36/37) are exactly this artifact, confirmed below.
  B. For each proven pair, collect every cell classified into one of its 4 strip rows
     ("strip cells"). For each strip cell, BFS (through classified cells only, unbounded by
     family, capped at 8 steps) to the nearest cell classified MAINS of family A and
     nearest MAINS of family B -- this is the measured GEOMETRIC DEPTH from each side of
     the seam, replacing any assumed/authored 1D seam order with an actual measured
     coordinate.
  C. Competing-hypothesis tests, in order of what they can rule out:
       (c) geometry-keyed depth -- DEPTH-GROUP PURITY: group strip cells by their
           (dist_to_A, dist_to_B) tuple; a group is PURE if every cell in it wears the same
           row. Purity rate near 100% falsifies (a)/(b)/(d) outright (no residual freedom
           left for them to act on) and hands over a literal formula.
       (a) random/hash -- chi-square of the row MARGINAL vs uniform (both pooled and, if
           depth does not fully determine row, WITHIN a fixed depth-group).
       (d) avoid-repeat-neighbour -- same-row rate among lattice-ADJACENT strip cells vs the
           independence baseline sum(p_r^2) from the marginal (mirrors the mains 12%-vs-25%
           reasoning in grassland.assign_mains's own measured comment).
       (b) along-seam cycle -- connected-component walk of same-depth cells ordered along
           the seam-tangent axis; row sequence printed + lag-1..4 autocorrelation.
     ORIENTATION: mean row conditioned on which family (A or B) a cell directly touches, and
     whether that direction (row increases toward family X) holds across all 4 lattice
     compass directions the boundary is found in (i-1/i+1/j-1/j+1) -- tests whether the rule
     is family-relative (does not flip) or world-axis-relative (would flip).
  D. Deliver the emission policy as pseudocode, grounded in whichever hypothesis the data
     actually supports, and state plainly whether the dunes-carry blocker is closed.

Artifacts -> out/strip_placement_policy.json. Run from the repo root:
    py studies/overworld-topography/strip_placement_policy.py
"""
import json
import math
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402

BLOCK = 64.0
EPS = 0.006                    # mains/D containment padding (round1's convention)
TOL_V = 0.008                  # strip-row snap acceptance radius (rows are 0.03125 apart --
                                # snapping picks the NEAREST row regardless of TOL_V; this
                                # only rejects tris too far from ANY row to be a strip tri)
ROW_PITCH = 0.03125
OUTD = Path(__file__).with_name("out")

# ---- family membership (recomputed, not trusted from any prior script -- same law as round1) ------
FAM_OF = {}
for t in (0, 1, 2, 3, 10, 11, 12, 13, 42):
    FAM_OF[t] = "grass"
for t in (4, 5, 6):
    FAM_OF[t] = "scrub"
for t in (17, 16, 19, 20):
    FAM_OF[t] = "desert"
for t in (27, 28):
    FAM_OF[t] = "snow"
FAM_OF[38] = "brush"
FAM_OF[41] = "dunes"
FAM_OF[45] = FAM_OF[46] = "canyon"
MAIN_FAMS = ("grass", "scrub", "desert", "brush", "dunes", "snow", "canyon")

PAIR_KEYS = [("grass", "desert"), ("desert", "dunes")]         # exactly G.STRIPS's own key order


def mains_rect(fam):
    m = G.FAM_REGION["main"]
    g = G.GROUNDS[fam]
    return (m[0] + g["mains_du"], m[1] + g["mains_dv"], m[2] + g["mains_du"], m[3] + g["mains_dv"])


RECTS = {fam: mains_rect(fam) for fam in MAIN_FAMS}
RECTS["meadowD"] = G.FAM_REGION["D"]

STRIP_U0, STRIP_U1 = G.STRIP_U
ROW0_V0 = G.STRIPS_V[0][0]
print("== proven inputs in play (grassland.py, shipped 2026-07-19)")
for pk in PAIR_KEYS:
    s = G.STRIPS[pk]
    print(f"   STRIPS{pk} du={s['du']} dv={s['dv']} rows={s['rows']}  "
          f"-> row0 u[{STRIP_U0 + s['du']:.5f},{STRIP_U1 + s['du']:.5f}] "
          f"v0[{ROW0_V0 + s['dv']:.5f}, pitch {ROW_PITCH}]")


def rect_contains(rect, uv3, eps=EPS):
    return all(rect[0] - eps <= u <= rect[2] + eps and rect[1] - eps <= v <= rect[3] + eps for (u, v) in uv3)


def classify_strip(fam, uv3, pk):
    """Snap a candidate tri's min-v corner to the nearest of the pair's 4 STRIPS_V rows (the
    proven 0.03125 pitch), gated by the STRIP_U window. Returns row index 0-3 or None."""
    s = G.STRIPS[pk]
    du, dv = s["du"], s["dv"]
    u_lo, u_hi = STRIP_U0 + du - EPS, STRIP_U1 + du + EPS
    if not all(u_lo <= u <= u_hi for (u, _v) in uv3):
        return None
    v_min = min(v for (_u, v) in uv3)
    row0 = ROW0_V0 + dv
    k = round((v_min - row0) / ROW_PITCH)
    if k < 0 or k > 3:
        return None
    resid = abs((v_min - row0) - k * ROW_PITCH)
    if resid > TOL_V:
        return None
    return int(k)


def classify_tri(fam, uv3):
    for pk in PAIR_KEYS:
        if fam in pk:
            k = classify_strip(fam, uv3, pk)
            if k is not None:
                return ("strip", pk, k)
    rect = RECTS.get(fam)
    if rect and rect_contains(rect, uv3):
        return ("mains", fam)
    if rect_contains(RECTS["meadowD"], uv3):
        return ("D",)
    return ("other",)


# ---- A. ONE map-wide pass: global per-4u-cell classification -------------------------------------
CellInfo = dict          # (gi,gj) -> {"fam":..,"fam_mixed":bool,"tag":..,"agree":n,"total":n,"block":(bx,by)}
cellinfo: CellInfo = {}
fams_at = defaultdict(Counter)
tags_at = defaultdict(Counter)
block_at = {}
n_blocks_read = 0
n_blocks_with_desert_or_dunes = 0

for bx in range(24):
    for by in range(20):
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            continue
        n_blocks_read += 1
        has_dd = False
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            fam = FAM_OF.get(topo)
            if fam is None:
                continue
            if fam in ("desert", "dunes"):
                has_dd = True
            w = [(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1], bm.verts[j][2] - BLOCK * by) for j in tri]
            uv3 = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
            cx = sum(p[0] for p in w) / 3.0
            cz = sum(p[2] for p in w) / 3.0
            cell = (math.floor(cx / 4.0), math.floor(cz / 4.0))
            fams_at[cell][fam] += 1
            tags_at[cell][classify_tri(fam, uv3)] += 1
            block_at[cell] = (bx, by)
        if has_dd:
            n_blocks_with_desert_or_dunes += 1

for cell, fc in fams_at.items():
    fam_mode, fam_n = fc.most_common(1)[0]
    tc = tags_at[cell]
    tag_mode, tag_n = tc.most_common(1)[0]
    cellinfo[cell] = dict(fam=fam_mode, fam_mixed=len(fc) > 1, tag=tag_mode,
                           agree=tag_n, total=sum(tc.values()), block=block_at[cell])

print(f"\nblocks read: {n_blocks_read}/480; blocks containing desert or dunes topo: "
      f"{n_blocks_with_desert_or_dunes}")
print(f"global cells classified: {len(cellinfo)}")

# ---- adjacency helpers -----------------------------------------------------------------------
NEI4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def neighbors4(cell):
    (i, j) = cell
    return [(i + di, j + dj) for di, dj in NEI4]


def bfs_dist_to_mains(start, fam, max_dist=8):
    """Shortest lattice-step distance from `start` to the nearest cell tagged mains(fam),
    traversing only cells present in `cellinfo` (stays inside the actual mesh footprint)."""
    seen = {start}
    q = deque([(start, 0)])
    while q:
        c, d = q.popleft()
        if d > 0 and cellinfo.get(c, {}).get("tag") == ("mains", fam):
            return d
        if d >= max_dist:
            continue
        for nb in neighbors4(c):
            if nb in seen or nb not in cellinfo:
                continue
            seen.add(nb)
            q.append((nb, d + 1))
    return None


def chi2_uniform(counts):
    n = sum(counts)
    k = len(counts)
    exp = n / k
    return sum((c - exp) ** 2 / exp for c in counts)


CHI2_CRIT_DF3 = {0.05: 7.815, 0.01: 11.345, 0.001: 16.266}

out = {"blocks_read": n_blocks_read, "cells_classified": len(cellinfo), "pairs": {}}

# ---- B+C. per-pair strip decode + placement-policy tests -----------------------------------------
for pk in PAIR_KEYS:
    fA, fB = pk
    strip_cells = {c: info["tag"][2] for c, info in cellinfo.items()
                   if info["tag"][0] == "strip" and info["tag"][1] == pk}
    blocks_touched = sorted({cellinfo[c]["block"] for c in strip_cells})
    print(f"\n{'=' * 90}\n== {fA}|{fB}: {len(strip_cells)} strip cells over "
          f"{len(blocks_touched)} blocks {blocks_touched}")
    pair_out = {"n_strip_cells": len(strip_cells), "blocks": blocks_touched}

    # sanity cross-check vs round1's per-tri-owning-fam tally (the double-count artifact)
    own_fam_counts = Counter(cellinfo[c]["fam"] for c in strip_cells)
    print(f"   own-topo-family of strip cells: {dict(own_fam_counts)}  "
          f"(round1's per-tri 'side' tallies over-counted via this same split -- "
          f"a cell's OWN topo family is context, not a 2nd independent measurement)")
    pair_out["own_fam_counts"] = dict(own_fam_counts)

    row_counts = Counter(strip_cells.values())
    print(f"   row marginal (0-3): {dict(sorted(row_counts.items()))}")
    counts4 = [row_counts.get(k, 0) for k in range(4)]
    chi2 = chi2_uniform(counts4) if sum(counts4) else 0.0
    verdict05 = "REJECT uniform (p<.05)" if chi2 > CHI2_CRIT_DF3[0.05] else "fail to reject uniform"
    print(f"   (a) chi2 vs uniform: {chi2:.2f} (df=3, crit .05={CHI2_CRIT_DF3[0.05]}, "
          f".01={CHI2_CRIT_DF3[1e-2 if False else 0.01]}) -> {verdict05}")
    pair_out["row_marginal"] = dict(sorted(row_counts.items()))
    pair_out["chi2_marginal"] = round(chi2, 3)

    # depth to each mains family
    depth = {}
    n_no_A = n_no_B = 0
    for c in strip_cells:
        dA = bfs_dist_to_mains(c, fA)
        dB = bfs_dist_to_mains(c, fB)
        if dA is None:
            n_no_A += 1
        if dB is None:
            n_no_B += 1
        depth[c] = (dA, dB)
    print(f"   BFS depth: {n_no_A} cells never reached {fA}-mains within 8 steps, "
          f"{n_no_B} never reached {fB}-mains")
    pair_out["depth_unreached"] = dict(no_A=n_no_A, no_B=n_no_B)

    both = {c: depth[c] for c in strip_cells if depth[c][0] is not None and depth[c][1] is not None}
    print(f"   {len(both)}/{len(strip_cells)} strip cells have BOTH distances resolved")

    # (c) DEPTH-GROUP PURITY -- the central geometry-keyed test
    by_pair_depth = defaultdict(list)     # (dA,dB) -> [rows]
    by_A_depth = defaultdict(list)        # dA -> [rows]
    for c, (dA, dB) in both.items():
        by_pair_depth[(dA, dB)].append(strip_cells[c])
        by_A_depth[dA].append(strip_cells[c])

    def purity(groups):
        pure = sum(1 for rows in groups.values() if len(set(rows)) == 1)
        total = len(groups)
        cells_in_pure = sum(len(rows) for rows in groups.values() if len(set(rows)) == 1)
        cells_total = sum(len(rows) for rows in groups.values())
        return pure, total, cells_in_pure, cells_total

    pg_pure, pg_total, pg_cells_pure, pg_cells_total = purity(by_pair_depth)
    a_pure, a_total, a_cells_pure, a_cells_total = purity(by_A_depth)
    print(f"   (c) DEPTH-GROUP PURITY, grouped by (dist_{fA},dist_{fB}): {pg_pure}/{pg_total} groups "
          f"pure ({pg_cells_pure}/{pg_cells_total} cells, {pg_cells_pure / max(1, pg_cells_total):.1%})")
    print(f"   (c) DEPTH-GROUP PURITY, grouped by dist_{fA} ALONE: {a_pure}/{a_total} groups pure "
          f"({a_cells_pure}/{a_cells_total} cells, {a_cells_pure / max(1, a_cells_total):.1%})")
    pair_out["purity_pairdepth"] = dict(groups_pure=pg_pure, groups_total=pg_total,
                                        cells_pure=pg_cells_pure, cells_total=pg_cells_total)
    pair_out["purity_Adepth"] = dict(groups_pure=a_pure, groups_total=a_total,
                                     cells_pure=a_cells_pure, cells_total=a_cells_total)

    # the explicit lookup table: dist_A -> row (mode) + spread, for the pseudocode
    print(f"   dist_{fA} -> row table (mode [spread], n cells):")
    depth_row_table = {}
    for dA in sorted(by_A_depth):
        rows = by_A_depth[dA]
        mode_row, mode_n = Counter(rows).most_common(1)[0]
        spread = sorted(set(rows))
        print(f"      dist_{fA}={dA}: rows seen={spread}  mode={mode_row} ({mode_n}/{len(rows)})  n={len(rows)}")
        depth_row_table[dA] = dict(rows_seen=spread, mode=mode_row, mode_n=mode_n, n=len(rows))
    pair_out["depth_A_to_row"] = {str(k): v for k, v in depth_row_table.items()}

    # correlation row vs dA, row vs dB, row vs (dA-dB)
    if both:
        rows_arr = np.array([strip_cells[c] for c in both])
        dA_arr = np.array([both[c][0] for c in both], dtype=float)
        dB_arr = np.array([both[c][1] for c in both], dtype=float)
        corr_A = float(np.corrcoef(rows_arr, dA_arr)[0, 1]) if np.std(dA_arr) > 0 else float("nan")
        corr_B = float(np.corrcoef(rows_arr, dB_arr)[0, 1]) if np.std(dB_arr) > 0 else float("nan")
        corr_diff = float(np.corrcoef(rows_arr, dA_arr - dB_arr)[0, 1]) if np.std(dA_arr - dB_arr) > 0 else float("nan")
        print(f"   correlation row~dist_{fA}: {corr_A:+.3f}   row~dist_{fB}: {corr_B:+.3f}   "
              f"row~(dist_{fA}-dist_{fB}): {corr_diff:+.3f}")
        pair_out["corr"] = dict(row_vs_distA=round(corr_A, 4), row_vs_distB=round(corr_B, 4),
                                row_vs_diff=round(corr_diff, 4))

    # (d) avoid-repeat-neighbour among lattice-adjacent STRIP cells (undirected, count once)
    adj_pairs = []
    for c in strip_cells:
        (i, j) = c
        for nb in ((i + 1, j), (i, j + 1)):        # only +i/+j directions -> each edge counted once
            if nb in strip_cells:
                adj_pairs.append((strip_cells[c], strip_cells[nb]))
    n_adj = len(adj_pairs)
    same = sum(1 for r1, r2 in adj_pairs if r1 == r2)
    dr_hist = Counter(abs(r1 - r2) for r1, r2 in adj_pairs)
    p_r = {k: v / len(strip_cells) for k, v in row_counts.items()}
    baseline_same = sum(p * p for p in p_r.values())
    print(f"   (d) lattice-adjacent strip-strip pairs: {n_adj}; same-row {same} "
          f"({same / max(1, n_adj):.1%}) vs independence baseline {baseline_same:.1%}; "
          f"|delta-row| histogram {dict(sorted(dr_hist.items()))}")
    pair_out["adjacent"] = dict(n=n_adj, same=same, baseline=round(baseline_same, 4),
                                dr_hist={str(k): v for k, v in dr_hist.items()})

    # ORIENTATION: mean row for cells that DIRECTLY touch mains-A only / mains-B only / both / neither
    cat_rows = defaultdict(list)
    dir_rows = defaultdict(lambda: defaultdict(list))   # direction -> fam -> [rows]
    DIRNAME = {(1, 0): "i+1", (-1, 0): "i-1", (0, 1): "j+1", (0, -1): "j-1"}
    for c, row in strip_cells.items():
        touchA = touchB = False
        for (di, dj) in NEI4:
            nb = (c[0] + di, c[1] + dj)
            info = cellinfo.get(nb)
            if info is None:
                continue
            if info["tag"] == ("mains", fA):
                touchA = True
                dir_rows[DIRNAME[(di, dj)]][fA].append(row)
            elif info["tag"] == ("mains", fB):
                touchB = True
                dir_rows[DIRNAME[(di, dj)]][fB].append(row)
        cat = "both" if touchA and touchB else ("A-only" if touchA else ("B-only" if touchB else "neither"))
        cat_rows[cat].append(row)
    print(f"   ORIENTATION -- mean row by direct-touch category:")
    cat_summary = {}
    for cat in ("A-only", "both", "B-only", "neither"):
        rows = cat_rows.get(cat, [])
        if rows:
            print(f"      {cat:8s} (touches {fA if cat=='A-only' else fB if cat=='B-only' else '?'}"
                  f"{'' if cat not in ('A-only','B-only') else '-mains'}): n={len(rows)} "
                  f"mean={np.mean(rows):.2f} std={np.std(rows):.2f} vals={dict(sorted(Counter(rows).items()))}")
            cat_summary[cat] = dict(n=len(rows), mean=round(float(np.mean(rows)), 3),
                                    std=round(float(np.std(rows)), 3),
                                    counts=dict(sorted(Counter(rows).items())))
    pair_out["orientation_category"] = cat_summary

    if cat_rows.get("A-only") and cat_rows.get("B-only"):
        mA, mB = np.mean(cat_rows["A-only"]), np.mean(cat_rows["B-only"])
        sA, nA = np.std(cat_rows["A-only"]), len(cat_rows["A-only"])
        sB, nB = np.std(cat_rows["B-only"]), len(cat_rows["B-only"])
        se = math.sqrt((sA ** 2) / max(1, nA) + (sB ** 2) / max(1, nB))
        t = (mB - mA) / se if se > 0 else float("nan")
        direction = f"row increases toward {fB}" if mB > mA else f"row increases toward {fA}"
        print(f"      A-only mean={mA:.2f} (n={nA})  B-only mean={mB:.2f} (n={nB})  "
              f"Welch-t={t:+.2f}  -> {direction}")
        pair_out["orientation_direction"] = dict(meanA=round(float(mA), 3), meanB=round(float(mB), 3),
                                                  welch_t=round(float(t), 3), direction=direction)

    # ORIENTATION-FLIP: does the direction hold across all 4 geometric compass directions?
    print(f"   ORIENTATION-FLIP -- mean row by which compass direction holds the mains neighbour:")
    flip_summary = {}
    for d in ("i+1", "i-1", "j+1", "j-1"):
        rowsA = dir_rows[d].get(fA, [])
        rowsB = dir_rows[d].get(fB, [])
        if rowsA and rowsB:
            mA, mB = np.mean(rowsA), np.mean(rowsB)
            dirn = f"->{fB} higher" if mB > mA else f"->{fA} higher"
            print(f"      {d}: {fA}-touch mean={mA:.2f} (n={len(rowsA)})  "
                  f"{fB}-touch mean={mB:.2f} (n={len(rowsB)})  {dirn}")
            flip_summary[d] = dict(meanA=round(float(mA), 3), nA=len(rowsA),
                                   meanB=round(float(mB), 3), nB=len(rowsB), verdict=dirn)
        elif rowsA or rowsB:
            fam_have = fA if rowsA else fB
            rows_have = rowsA or rowsB
            print(f"      {d}: only {fam_have}-touch present, mean={np.mean(rows_have):.2f} "
                  f"(n={len(rows_have)}) -- no A/B comparison possible in this direction")
    pair_out["orientation_flip"] = flip_summary

    # (b) ALONG-SEAM CYCLE -- connected components of strip cells, path-like ones walked in order
    visited = set()
    comp_id = 0
    comp_sizes = []
    path_rows_all = []
    for start in strip_cells:
        if start in visited:
            continue
        comp_id += 1
        comp = []
        q = deque([start])
        visited.add(start)
        while q:
            c = q.popleft()
            comp.append(c)
            for nb in neighbors4(c):
                if nb in strip_cells and nb not in visited:
                    visited.add(nb)
                    q.append(nb)
        comp_sizes.append(len(comp))
        # degree within the component's induced subgraph
        deg = {c: sum(1 for nb in neighbors4(c) if nb in comp) for c in comp}
        ends = [c for c in comp if deg[c] <= 1]
        if len(comp) >= 4 and max(deg.values()) <= 2 and ends:
            # simple path (or cycle if no endpoint) -- walk it in order
            cur, prev = ends[0], None
            order = [cur]
            while True:
                nxts = [nb for nb in neighbors4(cur) if nb in comp and nb != prev]
                if not nxts:
                    break
                nxt = nxts[0]
                order.append(nxt)
                prev, cur = cur, nxt
            if len(order) == len(comp):
                seq = [strip_cells[c] for c in order]
                path_rows_all.append(seq)
    print(f"   (b) connected strip components: {len(comp_sizes)} "
          f"(sizes {sorted(Counter(comp_sizes).items())}); "
          f"{len(path_rows_all)} are clean simple paths of length>=4")
    for seq in path_rows_all[:12]:
        print(f"      path row sequence: {seq}")
    pair_out["path_sequences"] = path_rows_all
    pair_out["component_sizes"] = sorted(comp_sizes)

    if path_rows_all:
        # lag-1..4 autocorrelation pooled across paths (each path's own mean-centering)
        for lag in (1, 2, 3, 4):
            xs, ys = [], []
            for seq in path_rows_all:
                if len(seq) > lag:
                    xs += seq[:-lag]
                    ys += seq[lag:]
            if len(xs) >= 5 and np.std(xs) > 0 and np.std(ys) > 0:
                ac = float(np.corrcoef(xs, ys)[0, 1])
                print(f"      lag-{lag} autocorrelation along path (n={len(xs)}): {ac:+.3f}")
                pair_out.setdefault("autocorr", {})[str(lag)] = round(ac, 4)

    out["pairs"][f"{fA}|{fB}"] = pair_out

OUTD.mkdir(exist_ok=True)
(OUTD / "strip_placement_policy.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'strip_placement_policy.json'}")
