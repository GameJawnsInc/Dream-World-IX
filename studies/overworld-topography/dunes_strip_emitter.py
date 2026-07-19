"""THE DESERT|DUNES STRIP-ROW EMITTER -- round 3 of the ecotone-strip placement arc, scoped
DELIBERATELY to desert|dunes only (the offline eye showed grass|desert reads as an ordinary
hard jigsaw boundary with no visible blend ribbon -- placement there is very likely
cosmetically free; desert|dunes shows a genuine soft halo, so THAT is the pair that needs a
trustworthy row policy before a minted dunes patch can wear an authored seam).

Round 2 (``strip_placement_policy.py``) FALSIFIED "depth alone determines the row" (0.5-3.1%
purity) and found the real structure is a locally-alternating small-step DITHER riding a soft
family-relative bias (row increases toward dunes, holds across all 4 compass directions -- so
the rule is family-relative, not world-axis-relative) -- but never built or rendered an
emitter. This script does both, THE OFFLINE EYE's way: iterate offline, only trust a render.

STEPS (see the orchestrator brief):
  1. Re-measure the desert|dunes seam map-wide (own script, own pass -- not imported from
     round 2, so this file is independently rerunnable per THE 5DP BAR's spirit and LAW 5):
     edge count (independent tri-shared-edge census, sanity-checked against the cell-level
     strip count), row marginal, adjacency same-row/delta histogram, orientation-by-touch-
     category (which settles: does the strip sit on the desert side, the dunes side, or both;
     does row order depend on which way the seam runs).
  2. A deterministic emitter: per-cell BASE row (from the measured touch-category means) +
     spatial dither (a transition kernel built from the measured |delta-row| histogram,
     conditioning on ALREADY-ASSIGNED lattice-neighbours -- generalises past a 1D "path" to an
     arbitrary 2D seam shape). Seeded RNG -> reproducible.
  3. Statistical validation: run the emitter over the SAME real strip-cell positions (with
     their real measured touch categories) and compare row marginal / |delta| histogram /
     same-row rate / lag-1..3 autocorrelation / run-length distribution against stock, next to
     two deliberately-wrong controls (all-one-row; iid uniform-random) for a floor.
  4. RENDER -- the actual deliverable: same geometry, only the strip cells' UV row swapped,
     stock vs emitter vs both controls, at two window scales (a wide seam-cluster overview and
     a close zoom), reusing offline_eye_disputed_assets.py's atlas-sampled painter's-algorithm
     technique (duplicated here, not imported, so this script stays self-contained and
     independently rerunnable) plus a flat ROW-COLOR overlay that makes the placement pattern
     legible independent of how subtle the real texture differences between rows are.
  5. The report (written by the agent that ran this, not by this script) says plainly whether
     the synthesized seam reads like the real one.

Run from the repo root:  py studies/overworld-topography/dunes_strip_emitter.py
Artifacts -> out/dunes_strip_emitter.json, out/dunes_strip_emitter_*.png
"""
import json
import math
import random
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                        # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402

BLOCK = 64.0
EPS = 0.006
TOL_V = 0.008
ROW_PITCH = 0.03125
OUTD = Path(__file__).with_name("out")
OUTD.mkdir(exist_ok=True)

PAIR = ("desert", "dunes")
FAM_A, FAM_B = PAIR          # A = desert (measured LOW base), B = dunes (measured HIGH base)

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


def mains_rect(fam):
    m = G.FAM_REGION["main"]
    g = G.GROUNDS[fam]
    return (m[0] + g["mains_du"], m[1] + g["mains_dv"], m[2] + g["mains_du"], m[3] + g["mains_dv"])


RECTS = {"desert": mains_rect("desert"), "dunes": mains_rect("dunes")}

STRIP_U0, STRIP_U1 = G.STRIP_U
ROW0_V0 = G.STRIPS_V[0][0]
S = G.STRIPS[PAIR]
DU, DV = S["du"], S["dv"]
print(f"== proven strip rect in play: STRIPS{PAIR} du={DU} dv={DV} rows={S['rows']} "
      f"(grassland.py, shipped 2026-07-19)")


def rect_contains(rect, uv3, eps=EPS):
    return all(rect[0] - eps <= u <= rect[2] + eps and rect[1] - eps <= v <= rect[3] + eps for (u, v) in uv3)


def classify_strip(uv3):
    """Snap a candidate tri's min-v corner to the nearest of the 4 STRIPS_V rows. Returns
    row index 0-3 or None. Identical method to strip_placement_policy.py's classify_strip,
    re-derived here (not imported) so this script is independently rerunnable per LAW 5."""
    u_lo, u_hi = STRIP_U0 + DU - EPS, STRIP_U1 + DU + EPS
    if not all(u_lo <= u <= u_hi for (u, _v) in uv3):
        return None
    v_min = min(v for (_u, v) in uv3)
    row0 = ROW0_V0 + DV
    k = round((v_min - row0) / ROW_PITCH)
    if k < 0 or k > 3:
        return None
    resid = abs((v_min - row0) - k * ROW_PITCH)
    if resid > TOL_V:
        return None
    return int(k)


def classify_tri(fam, uv3):
    if fam in PAIR:
        k = classify_strip(uv3)
        if k is not None:
            return ("strip", k)
    rect = RECTS.get(fam)
    if rect and rect_contains(rect, uv3):
        return ("mains", fam)
    return ("other",)


# ============================================================================================
# STEP 1 -- re-measure the desert|dunes seam map-wide, own pass
# ============================================================================================
print("\n=== STEP 1: map-wide re-measurement (own pass, all 480 (bx,by) candidates) ===")

cellinfo = {}
fams_at = defaultdict(Counter)
tags_at = defaultdict(Counter)
block_at = {}
n_blocks_read = 0

# independent edge-level census (tri-shared-edge, NOT cell-grid) -- sanity check vs the
# cell-based strip count, and the "190 edges over 9 blocks" figure the brief quotes
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
edge_count = 0
edge_blocks = Counter()

for bx in range(24):
    for by in range(20):
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            continue
        n_blocks_read += 1
        block_tris = []
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            fam = FAM_OF.get(topo)
            if fam is None:
                continue
            w = [(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1], bm.verts[j][2] - BLOCK * by) for j in tri]
            uv3 = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
            cx = sum(p[0] for p in w) / 3.0
            cz = sum(p[2] for p in w) / 3.0
            cell = (math.floor(cx / 4.0), math.floor(cz / 4.0))
            fams_at[cell][fam] += 1
            tags_at[cell][classify_tri(fam, uv3)] += 1
            block_at[cell] = (bx, by)
            if fam in PAIR:
                block_tris.append((fam, w))
        # independent edge census for this block only, restricted to A|B
        edge_owner = defaultdict(list)
        for ti, (fam, w) in enumerate(block_tris):
            ks = [kk(p) for p in w]
            for i in range(3):
                e = frozenset((ks[i], ks[(i + 1) % 3]))
                if len(e) < 2:
                    continue
                edge_owner[e].append(ti)
        for e, owners in edge_owner.items():
            fset = {block_tris[ti][0] for ti in owners}
            if fset == set(PAIR):
                edge_count += 1
                edge_blocks[(bx, by)] += 1

for cell, fc in fams_at.items():
    fam_mode, _ = fc.most_common(1)[0]
    tc = tags_at[cell]
    tag_mode, tag_n = tc.most_common(1)[0]
    cellinfo[cell] = dict(fam=fam_mode, tag=tag_mode, agree=tag_n, total=sum(tc.values()), block=block_at[cell])

print(f"blocks read: {n_blocks_read}/480; cells classified: {len(cellinfo)}")
print(f"INDEPENDENT edge census: {edge_count} desert|dunes tri-shared edges over "
      f"{len(edge_blocks)} blocks {sorted(edge_blocks)} -> {dict(sorted(edge_blocks.items(), key=lambda kv: -kv[1])[:5])} (top 5)")

strip_cells = {c: info["tag"][1] for c, info in cellinfo.items() if info["tag"][0] == "strip"}
strip_blocks = sorted({cellinfo[c]["block"] for c in strip_cells})
print(f"cell-level strip classification: {len(strip_cells)} strip cells over "
      f"{len(strip_blocks)} blocks {strip_blocks}")
print("   (edges != strip cells by construction: an edge is a single shared tri-edge between "
      "an A tri and a B tri; a strip cell is a 4u grid square whose dominant UV tag is one of "
      "the 4 translated rows. Both counted map-wide, both cited, neither substitutes the other.)")

own_fam_counts = Counter(cellinfo[c]["fam"] for c in strip_cells)
n_strip = len(strip_cells)
print(f"\nORIENTATION Q1 -- which side does the strip column sit on (own walkable topo family "
      f"of the cell wearing the strip UV): {dict(own_fam_counts)}  "
      f"({own_fam_counts['desert']/n_strip:.1%} desert-topo / {own_fam_counts['dunes']/n_strip:.1%} dunes-topo)")
print("   -> BOTH: the strip is not a one-sided edge trim -- roughly half the strip-wearing "
      "cells are walkable AS desert, half walkable AS dunes. The column straddles the seam.")

NEI4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIRNAME = {(1, 0): "i+1", (-1, 0): "i-1", (0, 1): "j+1", (0, -1): "j-1"}


def neighbors4(cell):
    (i, j) = cell
    return [(cell[0] + di, cell[1] + dj) for di, dj in NEI4]


cat_rows = defaultdict(list)
dir_rows = defaultdict(lambda: defaultdict(list))
touch_of = {}
for c, row in strip_cells.items():
    touchA = touchB = False
    for (di, dj) in NEI4:
        nb = (c[0] + di, c[1] + dj)
        info = cellinfo.get(nb)
        if info is None:
            continue
        if info["tag"] == ("mains", FAM_A):
            touchA = True
            dir_rows[DIRNAME[(di, dj)]][FAM_A].append(row)
        elif info["tag"] == ("mains", FAM_B):
            touchB = True
            dir_rows[DIRNAME[(di, dj)]][FAM_B].append(row)
    cat = "both" if touchA and touchB else ("A-only" if touchA else ("B-only" if touchB else "neither"))
    cat_rows[cat].append(row)
    touch_of[c] = cat

print(f"\nORIENTATION Q2 -- mean row by direct-touch category (settles the direction question):")
BASE_OF, SIGMA_OF, N_OF = {}, {}, {}
for cat in ("A-only", "both", "B-only", "neither"):
    rows = cat_rows.get(cat, [])
    if rows:
        m, s = float(np.mean(rows)), float(np.std(rows))
        print(f"   {cat:8s}: n={len(rows):3d} mean={m:.3f} std={s:.3f} vals={dict(sorted(Counter(rows).items()))}")
        BASE_OF[cat] = m
        SIGMA_OF[cat] = max(s, 0.4)          # floor so a thin category (n small) doesn't collapse to a delta
        N_OF[cat] = len(rows)
GLOBAL_MEAN = float(np.mean(list(strip_cells.values())))
GLOBAL_STD = float(np.std(list(strip_cells.values())))
for cat in ("A-only", "both", "B-only", "neither"):
    BASE_OF.setdefault(cat, GLOBAL_MEAN)
    SIGMA_OF.setdefault(cat, GLOBAL_STD)

# TARGET_PMF -- the emitter's per-category target distribution over rows 0-3. A first pass
# used a gaussian(mean,std) target and it FAILED validation badly (chi2 35.6 vs real 1.6,
# STEP 3 below) -- the category-conditional row distribution is not gaussian-shaped around
# its mean (e.g. "both"'s real vals {0:22,1:38,2:31,3:39} is closer to a broad, mildly-U-
# shaped spread than a bell curve centred on 1.67). Switched to the category's OWN empirical
# pmf (Laplace-smoothed, +0.5/n+2.0 so no row is ever zero-probability) as the target -- by
# construction this reproduces the real marginal almost exactly when transition modulation is
# weak, and still carries the real orientation bias (each category's pmf differs).
TARGET_PMF = {}
for cat in ("A-only", "both", "B-only", "neither"):
    n_cat = N_OF.get(cat, 0)
    counts = Counter(cat_rows.get(cat, []))
    TARGET_PMF[cat] = {r: (counts.get(r, 0) + 0.5) / (n_cat + 2.0) for r in range(4)}
    print(f"   TARGET_PMF[{cat}] = { {r: round(p,3) for r,p in TARGET_PMF[cat].items()} }")

mA, mB = BASE_OF["A-only"], BASE_OF["B-only"]
print(f"   direction: {'row increases toward ' + FAM_B if mB > mA else 'row increases toward ' + FAM_A} "
      f"(A-only mean {mA:.3f} vs B-only mean {mB:.3f})")

print(f"\nORIENTATION Q3 -- does the direction flip with which compass direction the seam runs "
      f"(world-axis-relative) or hold (family-relative)?")
flip_all_same = True
for d in ("i+1", "i-1", "j+1", "j-1"):
    rA = dir_rows[d].get(FAM_A, [])
    rB = dir_rows[d].get(FAM_B, [])
    if rA and rB:
        ma, mb = np.mean(rA), np.mean(rB)
        higher = FAM_B if mb > ma else FAM_A
        if higher != FAM_B:
            flip_all_same = False
        print(f"   {d}: {FAM_A}-touch mean={ma:.3f} (n={len(rA)})  {FAM_B}-touch mean={mb:.3f} "
              f"(n={len(rB)})  -> {higher} higher")
print(f"   -> {'FAMILY-RELATIVE (holds in all 4 compass directions -- does NOT flip)' if flip_all_same else 'WORLD-AXIS-RELATIVE (flips)'}")

row_counts = Counter(strip_cells.values())
counts4 = [row_counts.get(k, 0) for k in range(4)]
CHI2_CRIT = {0.05: 7.815, 0.01: 11.345}


def chi2_uniform(counts):
    n = sum(counts)
    exp = n / len(counts)
    return sum((c - exp) ** 2 / exp for c in counts)


chi2_real = chi2_uniform(counts4)
print(f"\nrow marginal (real, pooled): {dict(sorted(row_counts.items()))}  "
      f"chi2 vs uniform={chi2_real:.3f} (crit .05={CHI2_CRIT[0.05]}) -> "
      f"{'REJECT uniform' if chi2_real > CHI2_CRIT[0.05] else 'fail to reject uniform'}")

adj_pairs_real = []
cs = set(strip_cells)
for c in cs:
    i, j = c
    for nb in ((i + 1, j), (i, j + 1)):
        if nb in cs:
            adj_pairs_real.append((strip_cells[c], strip_cells[nb]))
n_adj_real = len(adj_pairs_real)
same_real = sum(1 for a, b in adj_pairs_real if a == b)
dr_hist_real = Counter(abs(a - b) for a, b in adj_pairs_real)
p_r_real = {k: v / n_strip for k, v in row_counts.items()}
baseline_real = sum(p * p for p in p_r_real.values())
print(f"adjacent strip-strip pairs (real): n={n_adj_real} same-row={same_real} "
      f"({same_real/n_adj_real:.1%}) vs independence baseline {baseline_real:.1%}  "
      f"|delta| hist {dict(sorted(dr_hist_real.items()))}")

DELTA_P = {d: dr_hist_real.get(d, 0) / n_adj_real for d in range(4)}
print(f"-> DELTA_P (the emitter's transition prior, straight from this measurement): "
      f"{ {k: round(v,4) for k,v in DELTA_P.items()} }")

# clean simple-path walk (identical method to strip_placement_policy.py), used for lag-k
# autocorrelation and run-length -- CELL sequences kept (not just row sequences) so any
# assignment (real/synth/control) can be replayed over the same path shape
visited = set()
path_cell_seqs = []
comp_sizes = []
for start in strip_cells:
    if start in visited:
        continue
    comp = []
    q = deque([start]); visited.add(start)
    while q:
        c = q.popleft(); comp.append(c)
        for nb in neighbors4(c):
            if nb in strip_cells and nb not in visited:
                visited.add(nb); q.append(nb)
    comp_sizes.append(len(comp))
    deg = {c: sum(1 for nb in neighbors4(c) if nb in comp) for c in comp}
    ends = [c for c in comp if deg[c] <= 1]
    if len(comp) >= 4 and max(deg.values()) <= 2 and ends:
        cur, prev = ends[0], None
        order = [cur]
        while True:
            nxts = [nb for nb in neighbors4(cur) if nb in comp and nb != prev]
            if not nxts:
                break
            nxt = nxts[0]; order.append(nxt); prev, cur = cur, nxt
        if len(order) == len(comp):
            path_cell_seqs.append(order)

print(f"\nconnected strip components: {len(comp_sizes)} (sizes {sorted(Counter(comp_sizes).items())}); "
      f"{len(path_cell_seqs)} clean simple paths length>=4 (used below for lag-k autocorrelation + run-length)")
for seq in path_cell_seqs:
    print(f"   path row sequence (real): {[strip_cells[c] for c in seq]}")


def lag_autocorr(row_seqs, lag):
    xs, ys = [], []
    for seq in row_seqs:
        if len(seq) > lag:
            xs += seq[:-lag]; ys += seq[lag:]
    if len(xs) >= 5 and np.std(xs) > 0 and np.std(ys) > 0:
        return float(np.corrcoef(xs, ys)[0, 1]), len(xs)
    return None, len(xs)


def run_lengths(seq):
    if not seq:
        return []
    runs, cur, ln = [], seq[0], 1
    for x in seq[1:]:
        if x == cur:
            ln += 1
        else:
            runs.append(ln); cur = x; ln = 1
    runs.append(ln)
    return runs


real_row_seqs = [[strip_cells[c] for c in seq] for seq in path_cell_seqs]
for lag in (1, 2, 3):
    ac, n = lag_autocorr(real_row_seqs, lag)
    print(f"   lag-{lag} autocorrelation (real, n={n}): {ac if ac is None else round(ac,4)}")
real_runs = [r for seq in real_row_seqs for r in run_lengths(seq)]
print(f"   run-length distribution (real): n={len(real_runs)} mean={np.mean(real_runs):.3f} "
      f"median={np.median(real_runs):.1f} hist={dict(sorted(Counter(real_runs).items()))}")


# ============================================================================================
# STEP 2 -- the emitter
# ============================================================================================
print("\n=== STEP 2: the emitter ===")
print("policy: per-cell TARGET_PMF = the measured touch-category's OWN empirical row "
      "distribution (A-only/both/B-only/neither -- see TARGET_PMF above) TIMES a transition "
      "prior built straight from DELTA_P against every ALREADY-ASSIGNED lattice neighbour "
      "(geometric-mean-combined so >1 neighbour doesn't over-collapse the distribution); "
      "cells are visited in a deterministic BFS order per connected component (root = "
      "lexicographically-smallest cell); sampling uses a seeded random.Random so a mint is "
      "byte-reproducible. (A first version used a gaussian(mean,std) target instead of the "
      "empirical pmf -- STEP 3 below shows why that failed and was replaced.)")


def emit_strip_rows(cells, touch_of_local, target_pmf, delta_p, seed=0):
    """cells: iterable of (i,j) grid cells forming the seam. touch_of_local: cell -> category
    ('A-only'/'both'/'B-only'/'neither'). Returns {cell: row 0-3}, deterministic given seed."""
    rng = random.Random(seed)
    cellset = set(cells)

    def nbrs(c):
        i, j = c
        return [n for n in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)) if n in cellset]

    adj = {c: nbrs(c) for c in cellset}
    order = []
    remaining = set(cellset)
    while remaining:
        root = min(remaining)
        seen = {root}
        q = deque([root])
        while q:
            c = q.popleft(); order.append(c)
            for n in sorted(adj[c]):
                if n not in seen:
                    seen.add(n); q.append(n)
        remaining -= seen
    assigned = {}
    for c in order:
        cat = touch_of_local.get(c, "neither")
        pmf = target_pmf[cat]
        nbr_rows = [assigned[n] for n in adj[c] if n in assigned]
        weights = []
        for r in range(4):
            w_target = pmf[r]
            if nbr_rows:
                w_trans = 1.0
                for nr in nbr_rows:
                    w_trans *= max(delta_p.get(abs(r - nr), 1e-6), 1e-6)
                w_trans **= (1.0 / len(nbr_rows))
            else:
                w_trans = 1.0
            weights.append(w_target * w_trans)
        tot = sum(weights)
        probs = [w / tot for w in weights]
        assigned[c] = rng.choices(range(4), weights=probs, k=1)[0]
    return assigned


# ============================================================================================
# STEP 3 -- statistical validation vs stock, next to two wrong controls
# ============================================================================================
print("\n=== STEP 3: validate the emitter (+ 2 controls) over the SAME real strip-cell positions ===")


def measure_assignment(assigned, label):
    rc = Counter(assigned.values())
    n = sum(rc.values())
    c4 = [rc.get(k, 0) for k in range(4)]
    chi2 = chi2_uniform(c4)
    adj_pairs = []
    css = set(assigned)
    for c in css:
        i, j = c
        for nb in ((i + 1, j), (i, j + 1)):
            if nb in css:
                adj_pairs.append((assigned[c], assigned[nb]))
    n_adj = len(adj_pairs)
    same = sum(1 for a, b in adj_pairs if a == b)
    dr_hist = Counter(abs(a - b) for a, b in adj_pairs)
    p_r = {k: v / n for k, v in rc.items()}
    baseline = sum(p * p for p in p_r.values())
    row_seqs = [[assigned[c] for c in seq] for seq in path_cell_seqs]
    acs = {}
    for lag in (1, 2, 3):
        ac, _ = lag_autocorr(row_seqs, lag)
        acs[lag] = ac
    runs = [r for seq in row_seqs for r in run_lengths(seq)]
    res = dict(label=label, n=n, marginal=dict(sorted(rc.items())), chi2=round(chi2, 3),
               n_adj=n_adj, same_rate=round(same / max(1, n_adj), 4), baseline=round(baseline, 4),
               dr_hist=dict(sorted(dr_hist.items())), autocorr=acs,
               run_mean=round(float(np.mean(runs)), 3) if runs else None,
               run_median=float(np.median(runs)) if runs else None)
    print(f"[{label:22s}] marginal={res['marginal']} chi2={res['chi2']:6.2f}  "
          f"same-row={res['same_rate']:.1%} (baseline {res['baseline']:.1%})  "
          f"dr_hist={res['dr_hist']}  lag1={res['autocorr'][1]}  "
          f"run mean/median={res['run_mean']}/{res['run_median']}")
    return res


results = {}
results["stock"] = measure_assignment(strip_cells, "STOCK (real)")

N_SEEDS = 20
seed_results = []
for seed in range(N_SEEDS):
    a = emit_strip_rows(strip_cells.keys(), touch_of, TARGET_PMF, DELTA_P, seed=seed)
    seed_results.append(measure_assignment(a, f"emitter seed={seed}") if seed == 0 else
                         measure_assignment(a, f"emitter seed={seed}"))
avg_chi2 = float(np.mean([r["chi2"] for r in seed_results]))
avg_same = float(np.mean([r["same_rate"] for r in seed_results]))
avg_lag1 = float(np.mean([r["autocorr"][1] for r in seed_results if r["autocorr"][1] is not None]))
print(f"\nEMITTER across {N_SEEDS} seeds: mean chi2={avg_chi2:.2f} (real {chi2_real:.2f})  "
      f"mean same-row={avg_same:.1%} (real {same_real/n_adj_real:.1%})  "
      f"mean lag1={avg_lag1:+.3f} (real {lag_autocorr(real_row_seqs,1)[0]:+.3f})")
results["emitter_seed0"] = seed_results[0]
results["emitter_seed_summary"] = dict(n_seeds=N_SEEDS, mean_chi2=round(avg_chi2, 3),
                                        mean_same_rate=round(avg_same, 4), mean_lag1=round(avg_lag1, 4))

control_all0 = {c: 0 for c in strip_cells}
results["control_all_one_row"] = measure_assignment(control_all0, "CONTROL all-row-0")

rng_ctrl = random.Random(0)
control_uniform = {c: rng_ctrl.randrange(4) for c in sorted(strip_cells)}
results["control_uniform_random"] = measure_assignment(control_uniform, "CONTROL iid-uniform")

print("\nreal path row sequences for reference:")
for seq in real_row_seqs:
    print(f"   real: {seq}")
print("emitter (seed 0) row sequences on the SAME path cells:")
emitted0 = emit_strip_rows(strip_cells.keys(), touch_of, TARGET_PMF, DELTA_P, seed=0)
for seq in path_cell_seqs:
    print(f"   emit: {[emitted0[c] for c in seq]}")


# ============================================================================================
# STEP 4 -- render: same geometry, only the strip-cell UV row swapped
# ============================================================================================
print("\n=== STEP 4: render (offline_eye_disputed_assets.py's technique, duplicated here) ===")

GP = Path(_cfg.find_game_path(None))
MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
    "textures" / "res(1_24)_terrain.png"
atlas = Image.open(MOG).convert("RGBA")
AW, AH = atlas.size
APX = atlas.load()
print(f"atlas: {MOG} ({AW}x{AH}px)")

LDIR = (-0.45, 0.72, 0.45)
_l = math.sqrt(sum(q * q for q in LDIR))
LDIR = tuple(q / _l for q in LDIR)

ROW_COLOR = {0: (230, 60, 60), 1: (240, 170, 40), 2: (70, 190, 90), 3: (70, 130, 240)}


def at_b(u_, v_):
    fx = (u_ % 1.0) * AW - 0.5
    fy = (1.0 - v_ % 1.0) * AH - 0.5
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - x0, fy - y0
    acc = [0.0, 0.0, 0.0]
    aa = 0.0
    for (dx, dy, wg) in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                         (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        px_, py_ = min(max(x0 + dx, 0), AW - 1), min(max(y0 + dy, 0), AH - 1)
        r, g, b, a = APX[px_, py_]
        acc[0] += r * wg; acc[1] += g * wg; acc[2] += b * wg; aa += a * wg
    return aa, (acc[0], acc[1], acc[2])


def world_tris_override(bm, bx, by, row_override):
    """Yields (p3, uv3, n3, topo, strip_row_or_None). If row_override is not None, a strip
    tri belonging to a cell present in row_override has its v-coordinate shifted by
    (new_row-old_row)*ROW_PITCH -- keeping u AND the internal per-vertex v-gradient intact,
    just selecting a different one of the 4 real painted rows. Non-strip tris (or strip tris
    whose cell isn't in row_override) pass through untouched."""
    V = np.asarray(bm.verts, dtype=np.float64)
    N = np.asarray(bm.normals, dtype=np.float64)
    U = np.asarray(bm.uvs, dtype=np.float64)
    TAN = np.asarray(bm.tangents, dtype=np.float64)
    for i in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        p3 = [(V[j][0] + BLOCK * bx, V[j][1], V[j][2] - BLOCK * by) for j in i]
        topo = X.decode_id(int(round(TAN[i[0]][0])))["topograph"]
        fam = FAM_OF.get(topo)
        uv3 = [tuple(U[j][:2]) for j in i]
        strip_row = None
        if fam in PAIR:
            k = classify_strip(uv3)
            if k is not None:
                strip_row = k
                if row_override is not None:
                    cx = sum(p[0] for p in p3) / 3.0
                    cz = sum(p[2] for p in p3) / 3.0
                    cell = (math.floor(cx / 4.0), math.floor(cz / 4.0))
                    if cell in row_override:
                        new_k = row_override[cell]
                        dvs = (new_k - k) * ROW_PITCH
                        uv3 = [(u, v + dvs) for (u, v) in uv3]
                        strip_row = new_k
        yield p3, uv3, [tuple(N[j][:3]) for j in i], topo, strip_row


def render_plan(blocks, cx, cz, win_x, win_z, sc=10, row_override=None, rowmap=False):
    """Top-down painter's-algorithm render. rowmap=True fills strip tris with a flat
    ROW_COLOR swatch instead of the atlas sample (non-strip tris rendered dim grey) -- the
    placement-pattern legibility view."""
    x0, x1 = cx - win_x / 2, cx + win_x / 2
    z0, z1 = cz - win_z / 2, cz + win_z / 2
    RW, RH = int(win_x * sc), int(win_z * sc)
    tex = Image.new("RGB", (RW, RH), (120, 150, 200))
    com = Image.new("RGB", (RW, RH), (120, 150, 200))
    tp, cp = tex.load(), com.load()
    tris = []
    n_read = 0
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            continue
        n_read += 1
        for p3, q3, n3, topo, srow in world_tris_override(bm, bx, by, row_override):
            if max(p[0] for p in p3) < x0 or min(p[0] for p in p3) > x1:
                continue
            if max(p[2] for p in p3) < z0 or min(p[2] for p in p3) > z1:
                continue
            tris.append((max(p[1] for p in p3), p3, q3, n3, srow))
    for _, p3, q3, n3, srow in sorted(tris, key=lambda t: t[0]):
        sx = [(p[0] - x0) * sc for p in p3]
        sy = [(z1 - p[2]) * sc for p in p3]
        bx0, bx1 = int(min(sx)), int(max(sx)) + 1
        by0, by1 = int(min(sy)), int(max(sy)) + 1
        d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
        if abs(d) < 1e-9:
            continue
        flat_rgb = ROW_COLOR.get(srow, (70, 70, 70)) if rowmap else None
        for pxx in range(max(0, bx0), min(RW, bx1)):
            for pyy in range(max(0, by0), min(RH, by1)):
                w0 = ((sy[1] - sy[2]) * (pxx - sx[2]) + (sx[2] - sx[1]) * (pyy - sy[2])) / d
                w1 = ((sy[2] - sy[0]) * (pxx - sx[2]) + (sx[0] - sx[2]) * (pyy - sy[2])) / d
                w2 = 1 - w0 - w1
                if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
                    continue
                if flat_rgb is not None:
                    rgb = flat_rgb
                    aa = 255
                else:
                    aa, rgb = at_b(w0 * q3[0][0] + w1 * q3[1][0] + w2 * q3[2][0],
                                   w0 * q3[0][1] + w1 * q3[1][1] + w2 * q3[2][1])
                    if aa < 24:
                        continue
                nx = sum(w * n3[k][0] for k, w in enumerate((w0, w1, w2)))
                ny = sum(w * n3[k][1] for k, w in enumerate((w0, w1, w2)))
                nz = sum(w * n3[k][2] for k, w in enumerate((w0, w1, w2)))
                nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
                f = 0.45 + 0.55 * max(0.0, (nx * LDIR[0] + ny * LDIR[1] + nz * LDIR[2]) / nl)
                tp[pxx, pyy] = tuple(min(255, int(c)) for c in rgb)
                cp[pxx, pyy] = tuple(min(255, int(c * f)) for c in rgb)
    return tex, com, n_read


def sheet(panels, cols, cell_w, cell_h, label_h=22, path=None, title=""):
    rows = (len(panels) + cols - 1) // cols
    pad = 10
    W = cols * (cell_w + pad) + pad
    H = rows * (cell_h + label_h + pad) + pad + (24 if title else 0)
    im = Image.new("RGB", (W, H), (16, 16, 16))
    dr = ImageDraw.Draw(im)
    if title:
        dr.text((pad, 6), title, fill=(255, 230, 140))
    for i, (label, panel) in enumerate(panels):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = pad + (24 if title else 0) + r * (cell_h + label_h + pad)
        dr.text((x, y), label, fill=(230, 230, 230))
        pw, ph = panel.size
        scale = min(cell_w / pw, cell_h / ph)
        rp = panel.resize((max(1, int(pw * scale)), max(1, int(ph * scale))), Image.NEAREST)
        im.paste(rp, (x, y + label_h))
    if path:
        im.save(path)
        print(f"-> {path}")
    return im


ASSIGNMENTS = {
    "STOCK (real)": None,                 # None = no override = render the real UVs verbatim
    "SYNTH (emitter seed0)": emitted0,
    "CONTROL all-row-0": control_all0,
    "CONTROL iid-random": control_uniform,
}

# ---- wide overview: the full desert|dunes cluster (18,3)-(20,4) + a margin of neighbours ----
WIDE_BLOCKS = [(bx, by) for bx in range(16, 22) for by in range(1, 7)]
cx_w, cz_w = (18 * 64 + 128), -(3 * 64 + 64)     # centre of the (18-20,3-4) cluster
panels_wide_tex, panels_wide_shd, panels_wide_row = [], [], []
for label, ov in ASSIGNMENTS.items():
    tex, com, nread = render_plan(WIDE_BLOCKS, cx_w, cz_w, 200, 160, sc=6, row_override=ov)
    _, rowim, _ = render_plan(WIDE_BLOCKS, cx_w, cz_w, 200, 160, sc=6, row_override=ov, rowmap=True)
    print(f"wide [{label}]: window 200x160u centred ({cx_w:.0f},{cz_w:.0f}), {nread} blocks read")
    panels_wide_tex.append((f"{label} -- TEXTURE", tex))
    panels_wide_shd.append((f"{label} -- SHADED", com))
    panels_wide_row.append((f"{label} -- ROW MAP (0=red 1=orange 2=green 3=blue, grey=non-strip)", rowim))

sheet(panels_wide_tex + panels_wide_shd, cols=4, cell_w=560, cell_h=448,
      path=OUTD / "dunes_strip_emitter_wide_texture.png",
      title="desert|dunes CLUSTER (18-20,3-4) -- stock vs emitter vs 2 wrong controls -- TEXTURE (top) / SHADED (bottom)")
sheet(panels_wide_row, cols=4, cell_w=560, cell_h=448,
      path=OUTD / "dunes_strip_emitter_wide_rowmap.png",
      title="desert|dunes CLUSTER -- ROW-COLOR overlay (the placement pattern, texture-independent)")

# ---- close zoom: the densest single block (18,3), 46 edges ----
ZBX, ZBY = 18, 3
cx_z, cz_z = ZBX * 64 + 32, -(ZBY * 64 + 32)
ZBLOCKS = [(ZBX + dx, ZBY + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
panels_zoom_shd, panels_zoom_row = [], []
for label, ov in ASSIGNMENTS.items():
    tex, com, nread = render_plan(ZBLOCKS, cx_z, cz_z, 56, 56, sc=16, row_override=ov)
    _, rowim, _ = render_plan(ZBLOCKS, cx_z, cz_z, 56, 56, sc=16, row_override=ov, rowmap=True)
    print(f"zoom [{label}]: window 56x56u centred block ({ZBX},{ZBY}), {nread}/9 neighbours read")
    panels_zoom_shd.append((f"{label} -- SHADED", com))
    panels_zoom_row.append((f"{label} -- ROW MAP", rowim))

sheet(panels_zoom_shd, cols=2, cell_w=640, cell_h=640,
      path=OUTD / "dunes_strip_emitter_zoom_shaded.png",
      title=f"CLOSE ZOOM block ({ZBX},{ZBY}) -- stock vs emitter vs 2 wrong controls -- SHADED texture")
sheet(panels_zoom_row, cols=2, cell_w=640, cell_h=640,
      path=OUTD / "dunes_strip_emitter_zoom_rowmap.png",
      title=f"CLOSE ZOOM block ({ZBX},{ZBY}) -- ROW-COLOR overlay")

# ---- SUPER-TIGHT zoom, UNSHADED texture only (the hillshade multiply can wash out subtle
# albedo differences between rows) -- centred on the densest cluster of strip cells actually
# IN block (18,3), a small enough window that individual 4u strip cells are large on screen ----
block_strip_cells = [c for c in strip_cells if cellinfo[c]["block"] == (ZBX, ZBY)]
tcx = (sum(c[0] for c in block_strip_cells) / len(block_strip_cells) + 0.5) * 4.0
tcz = (sum(c[1] for c in block_strip_cells) / len(block_strip_cells) + 0.5) * 4.0
print(f"\nsuper-tight zoom centre (centroid of block ({ZBX},{ZBY})'s {len(block_strip_cells)} "
      f"strip cells): x={tcx:.1f} z={tcz:.1f}")
panels_tight = []
for label, ov in ASSIGNMENTS.items():
    tex, com, nread = render_plan(ZBLOCKS, tcx, tcz, 24, 24, sc=32, row_override=ov)
    print(f"tight [{label}]: window 24x24u, {nread}/9 neighbours read")
    panels_tight.append((f"{label} -- UNSHADED texture", tex))
sheet(panels_tight, cols=2, cell_w=768, cell_h=768,
      path=OUTD / "dunes_strip_emitter_tight_texture.png",
      title=f"SUPER-TIGHT ZOOM ({tcx:.0f},{tcz:.0f}) 24x24u -- UNSHADED (raw atlas albedo, no hillshade)")

# ============================================================================================
# summary dump
# ============================================================================================
out = dict(
    edge_count=edge_count, edge_blocks={str(k): v for k, v in edge_blocks.items()},
    n_strip_cells=n_strip, strip_blocks=[list(b) for b in strip_blocks],
    own_fam_counts=dict(own_fam_counts),
    orientation_category_means={k: round(v, 4) for k, v in BASE_OF.items()},
    orientation_category_stds={k: round(v, 4) for k, v in SIGMA_OF.items()},
    orientation_category_n=N_OF,
    orientation_flip_family_relative=flip_all_same,
    row_marginal_real=dict(sorted(row_counts.items())),
    chi2_marginal_real=round(chi2_real, 3),
    delta_p=DELTA_P,
    real_path_row_sequences=real_row_seqs,
    results=results,
    outputs=[str(p) for p in sorted(OUTD.glob("dunes_strip_emitter_*.png"))],
)
(OUTD / "dunes_strip_emitter.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'dunes_strip_emitter.json'}")
print("\nDONE. Look at the PNGs in out/ -- this script's job is to produce them; the report")
print("describing what they SHOW is written by the agent that ran it, not by this script.")
