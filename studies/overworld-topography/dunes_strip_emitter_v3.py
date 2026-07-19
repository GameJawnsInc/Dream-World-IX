"""THE CONTINUOUS COVERAGE-FIELD STRIP-ROW EMITTER (v3) -- round 3's NAMED NEXT DESIGN,
attempted here for the first time.

Round 3 (`dunes_strip_emitter.py`) built a PER-CELL stochastic emitter (category empirical PMF
x a pairwise transition prior, BFS-sampled). It measurably misses stock's lag-1 autocorrelation
(+0.073 vs real -0.423) -- round 3's own diagnosis was that per-cell sampling can never fix this
because the 4 rows are a hand-painted CONTINUOUS coverage-density gradient, and independent
per-cell draws jitter locally even when long-run statistics look right. The round-3 doc named,
but explicitly did not attempt, the fix: sample one continuous scalar field with real spatial
structure, THEN quantize it -- never draw each cell's row independently.

HARD CONSTRAINT this script honours throughout: the emitter must work at a NOVEL minted seam.
It may CALIBRATE hyperparameters against stock (touch-category base means, field variance,
diffusion/correlation length, quantizer choice) -- all aggregate statistics -- but at EMISSION
time (`gen_field`, `quantize_snap`, `quantize_dither`) it is only ever given seam GEOMETRY: the
strip-cell lattice, its 4-neighbour adjacency, and each cell's touch category (which side(s) of
the seam it borders). It never reads the stock row actually painted at the cell being emitted.

DESIGN:
  1. field[cell] = BASE_OF[touch_category(cell)]  (the measured family-relative bias, same
     figures round 3 already measured)  +  a ZERO-MEAN smooth stochastic term: iid seeded
     Gaussian noise on the strip lattice, then graph-Laplacian-smoothed (`iters` diffusion
     passes at rate `alpha`) to induce spatial correlation length -- this is what round 3's
     per-cell draw never had.
  2. TWO quantizers of the SAME field, both tested honestly:
       A. nearest-row snap        -- the literally-named design.
       B. error-diffusion dither  -- 1-D-style residual carry along the same deterministic BFS
          order used elsewhere in this arc, propagated to not-yet-visited lattice neighbours
          (a graph generalisation of Floyd-Steinberg). Hypothesis under test: stock's negative
          lag-1 (locally alternating) + smooth density gradient is what dithered quantization of
          a smooth field naturally produces, while pure snap over-produces same-row runs
          (positive lag-1). If A fails and B passes, that is reported plainly as a finding about
          the named design, not smoothed over.
  3. Calibration is a small grid search over (sigma0, iters) per quantizer, scored ONLY against
     stock's AGGREGATE statistics (chi2 marginal, same-row rate, lag-1) -- never per-cell truth.
  4. Validation reuses v2's exact harness: the same 195 real strip-cell positions/categories,
     the recomputed (never hardcoded) TRANSPLANT NULL luminance-jumpiness band, lag-1..3
     autocorrelation, same-row rate, |drow| histogram, row marginals, run-length distribution,
     all against stock -- for 20 seeds per variant.
  5. Renders the full 8-panel sheet at the exact round-3 settings (24x24u, UNSHADED, sc=32):
     STOCK / 2 TRANSPLANTS / v3-A / v3-B / v2-BFS (round 3's emitter) / iid-random / all-row-0,
     plus the flat ROW-COLOR overlay twin.
  6. Prints an honest per-variant decision table against the stated success criteria.

Run from the repo root:  py studies/overworld-topography/dunes_strip_emitter_v3.py
Artifacts -> out/dunes_strip_emitter_v3.json, out/dunes_strip_emitter_v3_*.png
"""
import json
import statistics
import sys
from collections import deque
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))

SRC_P = Path(__file__).with_name("dunes_strip_emitter.py")
SRC = SRC_P.read_text(encoding="utf-8")
_lines = SRC.split("\n")
# exec round 3's analysis + render primitives verbatim, same exec-reuse pattern as v2 -- stop
# before round 3's OWN rendering section (we build our own panel set below).
_cut = next(i for i, ln in enumerate(_lines) if ln.startswith("# ---- wide overview"))
NS = {"__file__": str(SRC_P), "__name__": "_r3"}
print("=" * 92)
print("re-running round 3's analysis (cell classification, category means, atlas, emitter) ...")
print("=" * 92)
exec(compile("\n".join(_lines[:_cut]), str(SRC_P), "exec"), NS)

strip_cells = NS["strip_cells"]              # {cell: real stock row} -- used ONLY for scoring/render, never fed to the emitter
cellinfo = NS["cellinfo"]
touch_of = NS["touch_of"]                    # cell -> 'A-only'/'both'/'B-only'/'neither' -- SEAM GEOMETRY, legitimate emitter input
BASE_OF = NS["BASE_OF"]                      # measured touch-category row means -- a calibrated hyperparameter
neighbors4 = NS["neighbors4"]
render_plan, sheet, at_b = NS["render_plan"], NS["sheet"], NS["at_b"]
measure_assignment = NS["measure_assignment"]
chi2_uniform = NS["chi2_uniform"]
lag_autocorr = NS["lag_autocorr"]
run_lengths = NS["run_lengths"]
path_cell_seqs = NS["path_cell_seqs"]
real_row_seqs = NS["real_row_seqs"]
chi2_real, same_real, n_adj_real, n_strip = NS["chi2_real"], NS["same_real"], NS["n_adj_real"], NS["n_strip"]
CHI2_CRIT = NS["CHI2_CRIT"]
ASSIGN = dict(NS["ASSIGNMENTS"])             # STOCK(None)/SYNTH(v2-BFS seed0)/2 controls
emit_bfs = NS["emit_strip_rows"]             # round-3's category-PMF + transition-prior BFS emitter ("v2-BFS" below)
TARGET_PMF, DELTA_P = NS["TARGET_PMF"], NS["DELTA_P"]
ROW_PITCH, DU, DV = NS["ROW_PITCH"], NS["DU"], NS["DV"]
U_LO, U_HI = NS["STRIP_U0"] + DU, NS["STRIP_U1"] + DU
ROW_V0 = NS["ROW0_V0"] + DV
OUTD = NS["OUTD"]
control_all0, control_uniform, emitted0 = NS["control_all0"], NS["control_uniform"], NS["emitted0"]
ZBX, ZBY = 18, 3
ZBLOCKS = [(ZBX + dx, ZBY + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]

REAL_LAG1, _ = lag_autocorr(real_row_seqs, 1)
REAL_SAME_RATE = same_real / n_adj_real
V2BFS_LAG1_MISS = +0.073          # the arc-record figure this script must honestly compare against
print(f"\nREAL (stock) targets: lag1={REAL_LAG1:+.4f}  same-row-rate={REAL_SAME_RATE:.1%}  "
      f"chi2(marginal)={chi2_real:.3f}")
print(f"the arc's standing miss (round-3/v2-BFS per-cell emitter): lag1={V2BFS_LAG1_MISS:+.3f} "
      f"(WRONG SIGN vs real {REAL_LAG1:+.3f})")

# ============================================================================================
# the strip-cell lattice graph + a deterministic visiting order -- SEAM GEOMETRY ONLY
# ============================================================================================
cellset = set(strip_cells)
adj = {c: [n for n in neighbors4(c) if n in cellset] for c in cellset}


def bfs_order(cellset_, adj_):
    order, remaining = [], set(cellset_)
    while remaining:
        root = min(remaining)
        seen = {root}
        q = deque([root])
        while q:
            c = q.popleft(); order.append(c)
            for n in sorted(adj_[c]):
                if n not in seen:
                    seen.add(n); q.append(n)
        remaining -= seen
    return order


ORDER = bfs_order(cellset, adj)
ORDER_IDX = {c: i for i, c in enumerate(ORDER)}
print(f"strip lattice: {len(ORDER)} cells, deterministic BFS visiting order built "
      f"(root = lexicographically-smallest cell per connected component, matches round 3's own convention)")


# ============================================================================================
# STEP 1 -- the continuous coverage field (mean structure + smooth zero-mean noise)
# ============================================================================================
def gen_field(seed, sigma0, iters, alpha=0.5):
    """SEAM-GEOMETRY-ONLY generator: base = the measured touch-category mean (a calibrated
    constant, not a per-cell stock lookup) + zero-mean Gaussian noise smoothed by `iters`
    graph-Laplacian diffusion passes at rate `alpha` over the REAL lattice adjacency (also seam
    geometry). Deterministic given seed."""
    rng = np.random.RandomState((seed * 97 + 13) % (2**31 - 1))
    z0 = rng.normal(0.0, sigma0, size=len(ORDER))
    z = {c: float(z0[ORDER_IDX[c]]) for c in ORDER}
    for _ in range(iters):
        newz = {}
        for c in ORDER:
            nb = adj[c]
            newz[c] = z[c] if not nb else (1 - alpha) * z[c] + alpha * (sum(z[n] for n in nb) / len(nb))
        z = newz
    return {c: BASE_OF[touch_of.get(c, "neither")] + z[c] for c in ORDER}


# ============================================================================================
# STEP 2 -- two quantizers of the SAME field
# ============================================================================================
def quantize_snap(field):
    """A -- nearest-row snap, the literally-named design."""
    return {c: int(min(3, max(0, round(v)))) for c, v in field.items()}


def quantize_dither(field):
    """B -- error-diffusion quantization: visit cells in the same deterministic BFS order,
    round, and carry the residual forward onto not-yet-visited lattice neighbours (equal split)
    -- a graph generalisation of 1-D Floyd-Steinberg dithering."""
    val = dict(field)
    out = {}
    for c in ORDER:
        v = val[c]
        q = int(min(3, max(0, round(v))))
        out[c] = q
        err = v - q
        later = [n for n in adj[c] if ORDER_IDX[n] > ORDER_IDX[c]]
        if later:
            share = err / len(later)
            for n in later:
                val[n] += share
    return out


# ============================================================================================
# STEP 3 -- calibration: small grid search, scored ONLY against stock's AGGREGATE stats
# ============================================================================================
print("\n=== STEP 3: calibrate (sigma0, iters) per quantizer against stock's AGGREGATE stats only ===")
print("(chi2-marginal, same-row-rate, lag-1 -- never a per-cell stock row; alpha fixed at 0.5)")

SIGMA_GRID = [0.4, 0.6, 0.8, 1.0, 1.3, 1.6, 2.0]
ITERS_GRID = [0, 1, 2, 3, 5, 8]
ALPHA_GRID = [0.0, 0.3, 0.5, 0.8]      # 0.0 = no smoothing (control point); iters ignored when alpha=0
CAL_SEEDS = range(6)          # calibration uses a handful of seeds for speed; final validation uses 20


def score_variant(assigned):
    r = measure_assignment(assigned, "cal")
    lag1 = r["autocorr"][1]
    if lag1 is None:
        lag1 = 0.0
    # lag1 weighted heaviest -- it is the primary criterion under test; chi2/same-rate secondary
    return (abs(r["chi2"] - chi2_real) * 0.2
            + abs(r["same_rate"] - REAL_SAME_RATE) * 40.0
            + abs(lag1 - REAL_LAG1) * 15.0), r["chi2"], r["same_rate"], lag1


def calibrate(quantizer):
    rows = []
    for sigma0 in SIGMA_GRID:
        for alpha in ALPHA_GRID:
            for iters in ITERS_GRID:
                if alpha == 0.0 and iters > 0:
                    continue           # alpha=0 diffusion step is a no-op, don't waste evals
                scores, chi2s, sames, lag1s = [], [], [], []
                for s in CAL_SEEDS:
                    a = quantizer(gen_field(s, sigma0, iters, alpha=alpha or 0.5))
                    sc, c2, sr, l1 = score_variant(a)
                    scores.append(sc); chi2s.append(c2); sames.append(sr); lag1s.append(l1)
                rows.append(dict(sigma0=sigma0, iters=iters, alpha=alpha, score=float(np.mean(scores)),
                                  chi2=float(np.mean(chi2s)), same_rate=float(np.mean(sames)),
                                  lag1=float(np.mean(lag1s))))
    rows.sort(key=lambda r: r["score"])
    return rows


cal_A = calibrate(quantize_snap)
cal_B = calibrate(quantize_dither)
bestA, bestB = cal_A[0], cal_B[0]
mostneg_A = min(cal_A, key=lambda r: r["lag1"])
mostneg_B = min(cal_B, key=lambda r: r["lag1"])
print(f"\nA (snap)   top 5 by score:")
for r in cal_A[:5]:
    print(f"   sigma0={r['sigma0']:.2f} alpha={r['alpha']:.2f} iters={r['iters']}  score={r['score']:.3f}  "
          f"chi2={r['chi2']:.2f} same-rate={r['same_rate']:.1%} lag1={r['lag1']:+.3f}")
print(f"   MOST-NEGATIVE lag1 found anywhere in A's grid ({len(cal_A)} configs): "
      f"sigma0={mostneg_A['sigma0']:.2f} alpha={mostneg_A['alpha']:.2f} iters={mostneg_A['iters']} "
      f"-> lag1={mostneg_A['lag1']:+.3f} (score {mostneg_A['score']:.2f}, same-rate {mostneg_A['same_rate']:.1%})")
print(f"B (dither) top 5 by score:")
for r in cal_B[:5]:
    print(f"   sigma0={r['sigma0']:.2f} alpha={r['alpha']:.2f} iters={r['iters']}  score={r['score']:.3f}  "
          f"chi2={r['chi2']:.2f} same-rate={r['same_rate']:.1%} lag1={r['lag1']:+.3f}")
print(f"   MOST-NEGATIVE lag1 found anywhere in B's grid ({len(cal_B)} configs): "
      f"sigma0={mostneg_B['sigma0']:.2f} alpha={mostneg_B['alpha']:.2f} iters={mostneg_B['iters']} "
      f"-> lag1={mostneg_B['lag1']:+.3f} (score {mostneg_B['score']:.2f}, same-rate {mostneg_B['same_rate']:.1%})")
print(f"\n-> A chosen (by composite score): sigma0={bestA['sigma0']}, alpha={bestA['alpha']}, iters={bestA['iters']}")
print(f"-> B chosen (by composite score): sigma0={bestB['sigma0']}, alpha={bestB['alpha']}, iters={bestB['iters']}")


def variant_A(seed):
    return quantize_snap(gen_field(seed, bestA["sigma0"], bestA["iters"], alpha=bestA["alpha"] or 0.5))


def variant_B(seed):
    return quantize_dither(gen_field(seed, bestB["sigma0"], bestB["iters"], alpha=bestB["alpha"] or 0.5))


# ============================================================================================
# STEP 4 -- validation: v2's exact harness (transplant null band, recomputed, never hardcoded)
# ============================================================================================
print("\n=== STEP 4: validation on the v2 harness (transplant null recomputed, luminance jumpiness) ===")

WEST = sorted(c for c in strip_cells if cellinfo[c]["block"][0] < 16)
EAST = sorted(c for c in strip_cells if cellinfo[c]["block"][0] >= 16)
targets = sorted(strip_cells)


def transplant(donor_cells, off):
    dr = [strip_cells[c] for c in donor_cells]
    return {c: dr[(i + off) % len(dr)] for i, c in enumerate(targets)}


NULL = {}
for off in range(0, len(WEST), max(1, len(WEST) // 14)):
    NULL[f"WEST+{off}"] = transplant(WEST, off)
for off in range(0, len(EAST), max(1, len(EAST) // 14)):
    NULL[f"EAST+{off}"] = transplant(EAST, off)
print(f"transplant null: {len(NULL)} samples from 2 real clusters "
      f"(west n={len(WEST)}, east n={len(EAST)}) -- RECOMPUTED here, not hardcoded")

# per-row painted brightness (own pass, same method as v2)
row_lum = {}
for r in range(4):
    v0 = ROW_V0 + r * ROW_PITCH
    acc, n = 0.0, 0
    for iu in range(32):
        for iv in range(16):
            u = U_LO + (U_HI - U_LO) * (iu + 0.5) / 32.0
            v = v0 + ROW_PITCH * (iv + 0.5) / 16.0
            _a, (rr, gg, bb) = at_b(u, v)
            acc += 0.299 * rr + 0.587 * gg + 0.114 * bb
            n += 1
    row_lum[r] = acc / n
print(f"row luminance: {[round(row_lum[r],2) for r in range(4)]} "
      f"(span {abs(row_lum[3]-row_lum[0]):.2f}/255 -- the ~2.3% near-identical-tile fact)")

ADJ = [(a, b) for a in sorted(strip_cells) for b in neighbors4(a) if b in strip_cells and a < b]


def jumpiness(assign):
    asn = strip_cells if assign is None else assign
    return statistics.mean(abs(row_lum[asn[a]] - row_lum[asn[b]]) for a, b in ADJ)


stock_j = jumpiness(None)
null_j = {k: jumpiness(v) for k, v in NULL.items()}
nvals = sorted(null_j.values())
lo, hi = nvals[0], nvals[-1]
print(f"STOCK jumpiness = {stock_j:.3f}   TRANSPLANT null band = [{lo:.3f}, {hi:.3f}] "
      f"(n={len(nvals)}, median {statistics.median(nvals):.3f})  <- recomputed this run")


def full_report(label, assign_fn_or_dict, n_seeds=20):
    """assign_fn_or_dict: either a callable(seed)->assignment for a seeded variant, or a fixed
    dict for a deterministic one (n_seeds forced to 1)."""
    if callable(assign_fn_or_dict):
        seeds = list(range(n_seeds))
        assigns = [assign_fn_or_dict(s) for s in seeds]
    else:
        assigns = [assign_fn_or_dict]
    reports = [measure_assignment(a, f"{label} seed") for a in assigns]
    jvals = [jumpiness(a) for a in assigns]
    lag1s = [r["autocorr"][1] for r in reports if r["autocorr"][1] is not None]
    same_rates = [r["same_rate"] for r in reports]
    chi2s = [r["chi2"] for r in reports]
    in_band = sum(1 for j in jvals if lo <= j <= hi)
    return dict(
        label=label, n=len(assigns),
        in_band=in_band, in_band_total=len(assigns),
        jumpiness_range=[round(min(jvals), 3), round(max(jvals), 3)],
        jumpiness_mean=round(float(np.mean(jvals)), 3),
        lag1_mean=round(float(np.mean(lag1s)), 4) if lag1s else None,
        lag1_std=round(float(np.std(lag1s)), 4) if lag1s else None,
        same_rate_mean=round(float(np.mean(same_rates)), 4),
        chi2_mean=round(float(np.mean(chi2s)), 3),
        seed0_assignment=assigns[0],
    )


REPORTS = {}
REPORTS["STOCK (reference)"] = full_report("STOCK", strip_cells, n_seeds=1)
REPORTS["v3-A (snap)"] = full_report("v3-A", variant_A)
REPORTS["v3-B (dither)"] = full_report("v3-B", variant_B)
REPORTS["v2-BFS (round-3 emitter)"] = full_report(
    "v2-BFS", lambda s: emit_bfs(strip_cells.keys(), touch_of, TARGET_PMF, DELTA_P, seed=s))
REPORTS["CONTROL iid-random"] = full_report(
    "iid-random", lambda s: {c: __import__("random").Random(s * 7919 + hash(c) % 9973).randrange(4)
                              for c in sorted(strip_cells)})
REPORTS["CONTROL all-row-0"] = full_report("all-row-0", control_all0, n_seeds=1)

print("\n" + "=" * 100)
print("DECISION TABLE  (targets: real lag1=%.3f  real same-rate=%.1f%%  null band=[%.2f,%.2f]  "
      "criteria: >=18/20 in-band, lag1 negative & closer to real than +0.073, same-rate near 9.8%%, "
      "marginals non-degenerate)" % (REAL_LAG1, REAL_SAME_RATE * 100, lo, hi))
print("=" * 100)
for label, r in REPORTS.items():
    tot = r["in_band_total"]
    crit_band = f"{r['in_band']}/{tot}" + (" [PASS >=18/20]" if tot == 20 and r["in_band"] >= 18 else
                                            " [n/a]" if tot != 20 else " [FAIL <18/20]")
    lag1_str = "n/a" if r["lag1_mean"] is None else f"{r['lag1_mean']:+.3f}"
    closer = ""
    if r["lag1_mean"] is not None and label not in ("STOCK (reference)",):
        closer = " [closer to real than +0.073]" if r["lag1_mean"] < 0 and abs(r["lag1_mean"] - REAL_LAG1) < abs(V2BFS_LAG1_MISS - REAL_LAG1) else \
                 (" [negative but not closer]" if r["lag1_mean"] < 0 else " [WRONG SIGN, positive]")
    same_str = f"{r['same_rate_mean']:.1%}"
    marg_ok = "non-degenerate" if 0 < r["chi2_mean"] < CHI2_CRIT[0.01] * 3 else "DEGENERATE"
    verdict = []
    if tot == 20:
        verdict.append("in-band PASS" if r["in_band"] >= 18 else "in-band FAIL")
    if r["lag1_mean"] is not None and label != "STOCK (reference)":
        verdict.append("lag1 PASS" if (r["lag1_mean"] < 0 and abs(r["lag1_mean"] - REAL_LAG1) < abs(V2BFS_LAG1_MISS - REAL_LAG1)) else "lag1 FAIL")
    print(f"[{label:26s}] jumpiness={r['jumpiness_mean']:6.2f} range={r['jumpiness_range']}  "
          f"in-band={crit_band:16s}  lag1={lag1_str}{closer:26s}  same-rate={same_str:6s}  "
          f"chi2={r['chi2_mean']:6.2f} ({marg_ok})  -> {', '.join(verdict) if verdict else '(reference / n=1)'}")
print("=" * 100)

# ============================================================================================
# STEP 5 -- render the 8-panel sheet at the EXACT round-3 settings (24x24u, UNSHADED, sc=32)
# ============================================================================================
print("\n=== STEP 5: render the 8-panel comparison sheet (tight zoom, exact round-3 settings) ===")
bsc = [c for c in strip_cells if cellinfo[c]["block"] == (ZBX, ZBY)]
tcx = (sum(c[0] for c in bsc) / len(bsc) + 0.5) * 4.0
tcz = (sum(c[1] for c in bsc) / len(bsc) + 0.5) * 4.0
print(f"window centre (centroid of block ({ZBX},{ZBY})'s {len(bsc)} strip cells): x={tcx:.1f} z={tcz:.1f}")

nk = sorted(NULL)
v3a0, v3b0 = REPORTS["v3-A (snap)"]["seed0_assignment"], REPORTS["v3-B (dither)"]["seed0_assignment"]
v2bfs0 = REPORTS["v2-BFS (round-3 emitter)"]["seed0_assignment"]
iidr0 = REPORTS["CONTROL iid-random"]["seed0_assignment"]

PANEL_DEFS = [
    ("STOCK (real)", None, jumpiness(None)),
    (f"TRANSPLANT {nk[0]}", NULL[nk[0]], null_j[nk[0]]),
    (f"TRANSPLANT {nk[len(nk)//2]}", NULL[nk[len(nk)//2]], null_j[nk[len(nk)//2]]),
    ("v3-A (snap, seed0)", v3a0, jumpiness(v3a0)),
    ("v3-B (dither, seed0)", v3b0, jumpiness(v3b0)),
    ("v2-BFS (round-3, seed0)", v2bfs0, jumpiness(v2bfs0)),
    ("CONTROL iid-random", iidr0, jumpiness(iidr0)),
    ("CONTROL all-row-0", control_all0, jumpiness(control_all0)),
]

panels_tex, panels_row = [], []
for label, ov, j in PANEL_DEFS:
    tex, _com, nread = render_plan(ZBLOCKS, tcx, tcz, 24, 24, sc=32, row_override=ov)
    _, rowim, _ = render_plan(ZBLOCKS, tcx, tcz, 24, 24, sc=32, row_override=ov, rowmap=True)
    print(f"   {label:26s} j={j:5.2f}  ({nread}/9 neighbours read)")
    panels_tex.append((f"{label} -- j={j:.2f}", tex))
    panels_row.append((f"{label} -- ROW MAP", rowim))

sheet(panels_tex, cols=4, cell_w=480, cell_h=480,
      path=OUTD / "dunes_strip_emitter_v3_tight_texture.png",
      title=f"v3 EMITTER SHEET ({tcx:.0f},{tcz:.0f}) 24x24u UNSHADED sc=32 -- "
            f"STOCK / 2 TRANSPLANTS(real, elsewhere) / v3-A / v3-B / v2-BFS / iid-random / all-row-0")
sheet(panels_row, cols=4, cell_w=480, cell_h=480,
      path=OUTD / "dunes_strip_emitter_v3_tight_rowmap.png",
      title="v3 EMITTER SHEET -- flat ROW-COLOR overlay (0=red 1=orange 2=green 3=blue, grey=non-strip)")

# ============================================================================================
# pick + summary dump
# ============================================================================================
a_pass_band = REPORTS["v3-A (snap)"]["in_band"] >= 18
b_pass_band = REPORTS["v3-B (dither)"]["in_band"] >= 18
a_lag1 = REPORTS["v3-A (snap)"]["lag1_mean"]
b_lag1 = REPORTS["v3-B (dither)"]["lag1_mean"]
a_pass_lag1 = a_lag1 is not None and a_lag1 < 0 and abs(a_lag1 - REAL_LAG1) < abs(V2BFS_LAG1_MISS - REAL_LAG1)
b_pass_lag1 = b_lag1 is not None and b_lag1 < 0 and abs(b_lag1 - REAL_LAG1) < abs(V2BFS_LAG1_MISS - REAL_LAG1)

print("\n" + "=" * 100)
print("HYPOTHESIS CHECK: 'pure snap over-produces same-row runs (positive lag1); dithered "
      "quantization reproduces the negative lag1' --")
print(f"   v3-A (snap)   lag1={a_lag1}   {'CONFIRMS the failure mode (positive/near-zero)' if not a_pass_lag1 else 'does NOT show the predicted failure'}")
print(f"   v3-B (dither) lag1={b_lag1}   {'CONFIRMS the fix (negative, closer to real)' if b_pass_lag1 else 'does NOT confirm the fix'}")
print("=" * 100)

out = dict(
    real_targets=dict(lag1=REAL_LAG1, same_rate=REAL_SAME_RATE, chi2=chi2_real, n_strip=n_strip),
    v2bfs_arc_record_lag1_miss=V2BFS_LAG1_MISS,
    calibration=dict(
        grid_sigma0=SIGMA_GRID, grid_iters=ITERS_GRID, grid_alpha=ALPHA_GRID, cal_seeds=list(CAL_SEEDS),
        chosen_A=dict(sigma0=bestA["sigma0"], iters=bestA["iters"], alpha=bestA["alpha"]),
        chosen_B=dict(sigma0=bestB["sigma0"], iters=bestB["iters"], alpha=bestB["alpha"]),
        top5_A=cal_A[:5], top5_B=cal_B[:5],
        most_negative_lag1_A=mostneg_A, most_negative_lag1_B=mostneg_B,
    ),
    transplant_null_band=dict(lo=lo, hi=hi, n=len(nvals), stock_jumpiness=stock_j,
                               samples={k: round(v, 3) for k, v in null_j.items()}),
    row_luminance=row_lum,
    reports={k: {kk: vv for kk, vv in v.items() if kk != "seed0_assignment"} for k, v in REPORTS.items()},
    seed0_assignments={k: {f"{c[0]},{c[1]}": r for c, r in v["seed0_assignment"].items()}
                        for k, v in REPORTS.items()},
    hypothesis_check=dict(
        v3_A_lag1=a_lag1, v3_A_confirms_snap_failure=(not a_pass_lag1),
        v3_B_lag1=b_lag1, v3_B_confirms_dither_fix=b_pass_lag1,
    ),
    pick=None,   # filled by the reporting agent's narrative; the raw numbers above are authoritative
    outputs=[str(p) for p in sorted(OUTD.glob("dunes_strip_emitter_v3_*.png"))],
)
(OUTD / "dunes_strip_emitter_v3.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'dunes_strip_emitter_v3.json'}")
print("\nDONE.")
