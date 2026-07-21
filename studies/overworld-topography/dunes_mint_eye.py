"""THE CALIBRATED EYE for the ≥130-cell WHOLE-STAMP dunes mint (rung 5 of the dunes arc).

THE DUNES SIZE-CLASS LAW (`GROUND-FAMILY-DECODE-2026-07-19.md` §Round 4) closed the
small-patch mint as FALSIFIED: even a TRANSPLANT of genuine stock arrangement quilts on a
~31-cell blob, because the ecotone dressing is a real minimum-size-class vocabulary painted
for stock's only two dunes components (273 and 130 cells, boundary populations 164/171, ZERO
freckles map-wide). The lawful path that remains is a **≥~130-cell multi-block dunes field
that STAMPS A REAL COMPONENT'S FOOTPRINT WHOLE** — comp[1] (130 cells + its ecotone ring
needs ~185 regular cells) on a DESERT host.

This script is the INSTRUMENT that will judge that build's renders. It is calibrated ONCE,
here, against 100% stock, BEFORE any synthesis exists — then FROZEN for the round. Per the
arc's hardest-won law, CALIBRATE THE INSTRUMENT BEFORE YOU JUDGE WITH IT: every band below is
the spread stock shows against ITSELF, and every metric ships with a resolving-power proof
(it separates a known-wrong control from stock AND does NOT separate stock from stock).

WHAT IT DOES
  1. Render harness at the three frozen zooms of this arc, through the REAL Moguri atlas:
        WIDE   200x160u sc=6   (frames a whole component + margin; texture + shaded)
        MEDIUM  56x56u  sc=16  (frames a boundary region; shaded — the play-scale read)
        TIGHT   24x24u  sc=32  (unshaded raw albedo — the row/Rorschach zoom the arc
                                 calibrated on; the ONLY zoom where row choice is legible)
  2. Establish the NULLS from stock, rendered side by side so the builder drops its mint
     panel beside them:
        - BOTH real dunes components in situ (comp[0] 273-cell, comp[1] 130-cell — comp[1]
          is THE reference twin for the mint)
        - >=3 desert|dunes seam windows spanning the known stock variance
          (smooth-organic (18,3) .. boxy (13,12))
        - a pure-desert control block
        - a pure-dunes-interior control (eroded interior of comp[0])
  3. Compute + VALIDATE the metrics:
        M1  transplant-null luminance jumpiness   (row axis; the v2 metric, band re-frozen)
        M2  same-row adjacency %                   (row axis)
        M3  silhouette convexity + max boundary run (shape axis; where v2/v4 died)
        M4  interior-strip-coverage                (interior-quilt axis; where v3 died)
        (diagnostic, NON-gating) lag-1 row autocorrelation — documents the BFS emitter's
        known structural miss; NOT a pass/fail line, by the arc's own ruling.
  4. Freeze the pass/fail CRITERIA and expose judge() — the entry point the builder calls on
     its mint's ring-rows + footprint to get a verdict against these frozen bands.

The instrument reuses round 3's render primitives + measured constants verbatim (exec-and-cut,
the same technique dunes_strip_emitter_v2.py uses) so it is bit-consistent with the frozen
calibration; the shape/component machinery is re-derived inline (LAW 5 — independently
rerunnable, a drift shows as a self-check failure, not a silent shared assumption).

Run from the repo root:  py studies/overworld-topography/dunes_mint_eye.py
Artifacts -> out/dunes_mint_eye.json + out/dunes_mint_eye_*.png
"""
from __future__ import annotations

import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))

BLOCK = 64.0
CELL_U = 4.0
NEI4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
OUTD = HERE / "out"
OUTD.mkdir(exist_ok=True)

# ============================================================================================
# STEP 0 -- pull round 3's machinery (render primitives + measured constants + the census)
# ============================================================================================
SRC_P = HERE / "dunes_strip_emitter.py"
_lines = SRC_P.read_text(encoding="utf-8").split("\n")
_cut = next(i for i, ln in enumerate(_lines) if ln.startswith("# ---- wide overview"))
NS = {"__file__": str(SRC_P), "__name__": "_r3_for_mint_eye"}
print("=" * 96)
print("STEP 0: exec round 3's census + render primitives (map-wide, ~260 blocks) ...")
print("=" * 96)
exec(compile("\n".join(_lines[:_cut]), str(SRC_P), "exec"), NS)  # noqa: S102

render_plan = NS["render_plan"]
sheet = NS["sheet"]
at_b = NS["at_b"]
strip_cells = NS["strip_cells"]          # {cell: real stock strip row 0-3}  (map-wide)
cellinfo = NS["cellinfo"]                 # {cell: {"fam","tag","block",...}}  tag = ("strip",k)/("mains",f)/("other",)
fams_at = NS["fams_at"]                   # {cell: Counter(family -> tri count)}  ALL walkable families
touch_of = NS["touch_of"]                 # {strip cell: "A-only"/"both"/"B-only"/"neither"}
emit_strip_rows = NS["emit_strip_rows"]
TARGET_PMF = NS["TARGET_PMF"]
DELTA_P = NS["DELTA_P"]
neighbors4 = NS["neighbors4"]
path_cell_seqs = NS["path_cell_seqs"]     # clean simple boundary chains (for autocorrelation)
ROW_PITCH = NS["ROW_PITCH"]
DU, DV = NS["DU"], NS["DV"]
U_LO, U_HI = NS["STRIP_U0"] + DU, NS["STRIP_U1"] + DU
ROW_V0 = NS["ROW0_V0"] + DV               # v of strip row 0 in the desert|dunes frame

print(f"\n   pulled: {len(strip_cells)} map-wide strip cells, {len(cellinfo)} classified cells, "
      f"{len(fams_at)} family-census cells")


# ============================================================================================
# STEP 1 -- re-derive the two real dunes components (LAW 5: independent, self-checked)
# ============================================================================================
print("\n" + "=" * 96)
print("STEP 1: re-derive stock's dunes components from the family census (self-check vs 273/130)")
print("=" * 96)

dunes_cells = {c for c, fc in fams_at.items() if fc.most_common(1)[0][0] == "dunes"}


def connected_components(cellset):
    seen, comps = set(), []
    for s in cellset:
        if s in seen:
            continue
        comp, q = set(), deque([s])
        seen.add(s)
        while q:
            c = q.popleft()
            comp.add(c)
            for di, dj in NEI4:
                n = (c[0] + di, c[1] + dj)
                if n in cellset and n not in seen:
                    seen.add(n)
                    q.append(n)
        comps.append(comp)
    return comps


def bbox(cells):
    xs = [c[0] for c in cells]
    zs = [c[1] for c in cells]
    return (min(xs), min(zs), max(xs), max(zs))


COMPS = sorted(connected_components(dunes_cells), key=len, reverse=True)
assert len(COMPS) == 2, f"expected 2 dunes components, got {len(COMPS)} (calibration integrity)"
assert len(COMPS[0]) == 273 and len(COMPS[1]) == 130, \
    f"component sizes drifted: {[len(c) for c in COMPS]} != [273, 130] -- instrument NOT calibrated"
COMP0, COMP1 = COMPS
print(f"   comp[0] {len(COMP0)} cells bbox {bbox(COMP0)}   comp[1] {len(COMP1)} cells bbox {bbox(COMP1)}")
print("   self-check PASSED: 273 + 130, matches the committed dunes_blob_shapes.json")


# ---- shape helpers (cell-grid boundary trace + convexity + run-length) --------------------
def erode(cellset):
    return {c for c in cellset if all((c[0] + di, c[1] + dj) in cellset for di, dj in NEI4)}


def boundary_cells_of(cellset):
    return {c for c in cellset if any((c[0] + di, c[1] + dj) not in cellset for di, dj in NEI4)}


def _boundary_loops(cellset):
    directed = {}
    for (i, j) in cellset:
        bl, br, tr, tl = (i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)
        for (a, b, nb) in [(bl, br, (i, j - 1)), (br, tr, (i + 1, j)),
                           (tr, tl, (i, j + 1)), (tl, bl, (i - 1, j))]:
            if nb not in cellset:
                directed[(a, b)] = (i, j)
    out_from = defaultdict(list)
    for (a, b), cell in directed.items():
        out_from[a].append((b, cell))

    def pri(pd, cd):
        cross = pd[0] * cd[1] - pd[1] * cd[0]
        dot = pd[0] * cd[0] + pd[1] * cd[1]
        return -math.atan2(cross, dot)

    remaining = dict(directed)
    loops = []
    while remaining:
        (a0, b0) = next(iter(remaining))
        remaining.pop((a0, b0))
        loop = [(a0, b0)]
        cur, prev_dir = b0, (b0[0] - a0[0], b0[1] - a0[1])
        guard = 0
        while cur != a0 and guard < 100000:
            guard += 1
            cands = [(end, cell) for (end, cell) in out_from[cur] if (cur, end) in remaining]
            if not cands:
                break
            end, _cell = cands[0] if len(cands) == 1 else \
                min(cands, key=lambda ec: pri(prev_dir, (ec[0][0] - cur[0], ec[0][1] - cur[1])))
            remaining.pop((cur, end))
            loop.append((cur, end))
            prev_dir = (end[0] - cur[0], end[1] - cur[1])
            cur = end
        loops.append(loop)
    return loops


def _loop_area(loop):
    return sum(p[0] * q[1] - q[0] * p[1] for (p, q) in loop) / 2.0


def _runs(loop):
    dirs = [(q[0] - p[0], q[1] - p[1]) for (p, q) in loop]
    if not dirs:
        return []
    runs, cur, ln = [], dirs[0], 1
    for d in dirs[1:]:
        if d == cur:
            ln += 1
        else:
            runs.append(ln)
            cur, ln = d, 1
    runs.append(ln)
    if len(runs) > 1 and dirs[-1] == dirs[0]:
        runs[0] += runs[-1]
        runs.pop()
    return runs


def _hull_area(points):
    pts = sorted(set(points))
    if len(pts) < 3:
        return 0.0

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lo = []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    up = []
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    hull = lo[:-1] + up[:-1]
    a = sum(hull[i][0] * hull[(i + 1) % len(hull)][1] - hull[(i + 1) % len(hull)][0] * hull[i][1]
            for i in range(len(hull)))
    return abs(a) / 2.0


def shape_stats(cellset):
    loops = _boundary_loops(cellset)
    outer = max((lp for lp in loops if _loop_area(lp) > 0),
                key=lambda lp: abs(_loop_area(lp)), default=(max(loops, key=len) if loops else []))
    runs = _runs(outer)
    corners = {p for (p, q) in outer} | {q for (p, q) in outer}
    hull = _hull_area(list(corners))
    conv = (len(cellset) / hull) if hull > 0 else None
    holes = sum(1 for lp in loops if _loop_area(lp) < 0)
    return dict(size=len(cellset), convexity=round(conv, 4) if conv else None,
                max_run=max(runs) if runs else 0,
                mean_run=round(float(np.mean(runs)), 3) if runs else 0.0,
                n_boundary_cells=len(boundary_cells_of(cellset)), n_holes=holes)


S0 = shape_stats(COMP0)
S1 = shape_stats(COMP1)
print(f"   comp[0] shape {S0}")
print(f"   comp[1] shape {S1}")


# ============================================================================================
# STEP 2 -- the scorers (row + shape + coverage), all over a {cell: row} or cell-set
# ============================================================================================
print("\n" + "=" * 96)
print("STEP 2: the metric scorers")
print("=" * 96)

# ---- M1 pre-req: per-row painted brightness (v2's block A, verbatim) ----------------------
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
STEP_LUM = statistics.mean(abs(row_lum[i + 1] - row_lum[i]) for i in range(3))
print(f"   row luminances {[round(row_lum[r], 2) for r in range(4)]}  "
      f"(a 1-row step changes brightness by {STEP_LUM:.2f}/255; the whole 0->3 span is "
      f"{abs(row_lum[3] - row_lum[0]):.2f}) -- THE ROOT CAUSE: rows are ~the same tile")


def _adj_pairs(rowmap):
    cs = set(rowmap)
    out = []
    for c in cs:
        for nb in ((c[0] + 1, c[1]), (c[0], c[1] + 1)):
            if nb in cs:
                out.append((rowmap[c], rowmap[nb]))
    return out


def jumpiness(rowmap):
    """M1: mean |delta mean-luminance| between lattice-adjacent strip cells."""
    ap = _adj_pairs(rowmap)
    return statistics.mean(abs(row_lum[a] - row_lum[b]) for a, b in ap) if ap else 0.0


def same_row_pct(rowmap):
    """M2: fraction of lattice-adjacent strip-cell pairs that share a row."""
    ap = _adj_pairs(rowmap)
    return (sum(1 for a, b in ap if a == b) / len(ap)) if ap else None


def lag1_autocorr(rowmap, chains):
    """diagnostic: lag-1 autocorrelation of the row sequence along boundary chains."""
    xs, ys = [], []
    for seq in chains:
        rows = [rowmap[c] for c in seq if c in rowmap]
        if len(rows) > 1:
            xs += rows[:-1]
            ys += rows[1:]
    if len(xs) >= 5 and np.std(xs) > 0 and np.std(ys) > 0:
        return float(np.corrcoef(xs, ys)[0, 1])
    return None


# ---- extract each stock reference region's OWN strip-cell rows + interior coverage --------
def region_rows(cellset):
    return {c: strip_cells[c] for c in cellset if c in strip_cells}


def interior_strip_coverage(cellset):
    """M4: fraction of INTERIOR (depth>=2, doubly-eroded) component cells that wear the strip
    UV rather than plain dune mains. Stock interiors are ~all plain mains (the quilt failure
    pushes this up)."""
    inner = erode(erode(cellset))
    if not inner:
        return None
    strip_inner = sum(1 for c in inner if cellinfo.get(c, {}).get("tag", ("",))[0] == "strip")
    return strip_inner / len(inner)


def boundary_strip_coverage(cellset):
    """diagnostic target for the builder's ring: fraction of BOUNDARY cells wearing strip."""
    bc = boundary_cells_of(cellset)
    if not bc:
        return None
    return sum(1 for c in bc if cellinfo.get(c, {}).get("tag", ("",))[0] == "strip") / len(bc)


# ============================================================================================
# STEP 3 -- M1/M2 THE TRANSPLANT NULL (v2's blocks C/D, re-frozen) + resolving-power proof
# ============================================================================================
print("\n" + "=" * 96)
print("STEP 3: M1 transplant-null jumpiness + M2 same-row -- the frozen band + validation")
print("=" * 96)

targets = sorted(strip_cells)
WEST = sorted(c for c in strip_cells if cellinfo[c]["block"][0] < 16)   # comp[1] cluster
EAST = sorted(c for c in strip_cells if cellinfo[c]["block"][0] >= 16)  # comp[0] cluster


def transplant(donor_cells, off):
    dr = [strip_cells[c] for c in donor_cells]
    return {c: dr[(i + off) % len(dr)] for i, c in enumerate(targets)}


NULL = {}
for off in range(0, len(WEST), max(1, len(WEST) // 14)):
    NULL[f"WEST+{off}"] = transplant(WEST, off)
for off in range(0, len(EAST), max(1, len(EAST) // 14)):
    NULL[f"EAST+{off}"] = transplant(EAST, off)

STOCK_J = jumpiness(strip_cells)
null_j = sorted(jumpiness(v) for v in NULL.values())
MAPWIDE_LO, MAPWIDE_HI = null_j[0], null_j[-1]
print(f"   (context) map-wide STOCK jumpiness = {STOCK_J:.2f}; map-wide transplant band "
      f"{MAPWIDE_LO:.2f}..{MAPWIDE_HI:.2f} (n={len(null_j)}) -- the v2 figure, kept for continuity")

# ---- CALIBRATE AT THE MINT'S OWN SCALE (the self-test bug's lesson) --------------------------
# The judge() measures jumpiness/same-row over the MINT's ring -- which is comp[1]'s ~30-cell
# strip ring, NOT the pooled 195-cell map. A 30-cell ring has materially higher variance and a
# HIGHER same-row rate (small clustered ring) than the map-wide pool -- comp[1]'s own is 0.36,
# comp[0]'s 0.15, both far above the map-wide 9.8%. Gating on the map-wide band would FALSE-REJECT
# a verbatim comp[1] stamp (the self-test proved it). So the null band is built at RING SCALE:
# lay GENUINE stock row-sequences (comp[0]'s and comp[1]'s own, cycled at every offset) over
# comp[1]'s real ring geometry. Offset 0 of comp[1]'s own pool == the verbatim stamp, IN by
# construction; the spread over all offsets + the cross-component transplant is the band.
RING1 = region_rows(COMP1)                       # {cell: real row}, comp[1]'s 30-cell strip ring
RING0 = region_rows(COMP0)                       # comp[0]'s 69-cell ring (a second stock reference)
ring1_cells = sorted(RING1)
pool0 = [RING0[c] for c in sorted(RING0)]
pool1 = [RING1[c] for c in sorted(RING1)]


def lay(cells, pool, off):
    return {c: pool[(i + off) % len(pool)] for i, c in enumerate(cells)}


# v2's cross-cluster method: lay the OTHER component's genuine rows over comp[1]'s ring at every
# phase (a real transplant), + comp[1]'s own verbatim assignment as the anchor. (Self-cycling
# comp[1]'s own rows at nonzero offsets is a SHUFFLE, not a transplant -- it inflates the band with
# arrangements FF9 never painted, so it is excluded.)
ring_null = [lay(ring1_cells, pool0, off) for off in range(len(pool0))] + [dict(RING1)]
ring_j = sorted(jumpiness(a) for a in ring_null)
ring_sr = sorted(same_row_pct(a) for a in ring_null)
BAND_LO, BAND_HI = ring_j[0], ring_j[-1]
SR_LO, SR_HI = ring_sr[0], ring_sr[-1]
VERB_J = jumpiness(RING1)          # the verbatim comp[1] stamp -- must be inside by construction
VERB_SR = same_row_pct(RING1)
print(f"\n   RING-SCALE null (comp[0]+comp[1] genuine rows over comp[1]'s ring geometry, "
      f"n={len(ring_null)}):")
print(f"      M1 jumpiness band = {BAND_LO:.2f} .. {BAND_HI:.2f}   (verbatim comp[1] stamp = {VERB_J:.2f}, IN)")
print(f"      M2 same-row band  = {SR_LO:.1%} .. {SR_HI:.1%}   (verbatim comp[1] stamp = {VERB_SR:.1%}, IN)")

# controls for the resolving-power proof, ALL over comp[1]'s ring geometry (the judged scale)
CTRL_ALL0 = {c: 0 for c in ring1_cells}
_rng = random.Random(0)
CTRL_IID = {c: _rng.randrange(4) for c in ring1_cells}
j_all0, j_iid = jumpiness(CTRL_ALL0), jumpiness(CTRL_IID)
sr_all0, sr_iid = same_row_pct(CTRL_ALL0), same_row_pct(CTRL_IID)
# the round-3 BFS emitter over comp[1]'s ring, across seeds (the shippable fallback if not verbatim)
emit_j, emit_sr = [], []
for s in range(20):
    a = emit_strip_rows(ring1_cells, touch_of, TARGET_PMF, DELTA_P, seed=s)
    emit_j.append(jumpiness(a))
    emit_sr.append(same_row_pct(a))
emit_in = sum(1 for j in emit_j if BAND_LO <= j <= BAND_HI)

print("\n   -- M1 resolving-power proof (separates a wrong control; does NOT separate stock-stock) --")
print(f"      all-row-0 (wrong ctrl): j={j_all0:.2f}  {'OUTSIDE' if not (BAND_LO <= j_all0 <= BAND_HI) else 'INSIDE (BAD)'}")
print(f"      iid-random            : j={j_iid:.2f}  {'inside' if BAND_LO <= j_iid <= BAND_HI else 'outside'}")
print(f"      emitter 20 seeds      : {min(emit_j):.2f}..{max(emit_j):.2f}  {emit_in}/20 inside")
print("      -> stock-vs-stock: every genuine transplant (incl. verbatim comp[1]) is the band by "
      "construction; comp[0]'s rows laid on comp[1]'s ring stay inside too. No over-rejection. VALID.")
print("\n   -- M2 resolving-power proof --")
print(f"      all-row-0 (wrong ctrl): same-row={sr_all0:.1%}  {'OUTSIDE' if not (SR_LO <= sr_all0 <= SR_HI) else 'INSIDE (BAD)'}")
print(f"      iid-random            : same-row={sr_iid:.1%}")
print(f"      comp[0] own ring same-row={same_row_pct(RING0):.1%}  comp[1] own ring same-row={VERB_SR:.1%} "
      "(both real, both define the stock spread)")
sr_stock = VERB_SR   # the mint's twin is comp[1]; its same-row is the headline stock value


# ============================================================================================
# STEP 4 -- M3 shape + M4 interior-coverage: resolving-power proofs
# ============================================================================================
print("\n" + "=" * 96)
print("STEP 4: M3 silhouette (convexity/max-run) + M4 interior-strip-coverage -- proofs")
print("=" * 96)

# real envelope (the two stock components)
CONV_LO = min(S0["convexity"], S1["convexity"])
CONV_HI = max(S0["convexity"], S1["convexity"])
MAXRUN_LO = min(S0["max_run"], S1["max_run"])
MAXRUN_HI = max(S0["max_run"], S1["max_run"])

# the known-wrong shape control: v2's 3x3-core + 2 concentric shells = a rectilinear SQUARE
CORE = {(di, dj) for di in range(3) for dj in range(3)}


def _dilate(seed, exclude):
    nxt = set()
    for c in seed:
        for di, dj in NEI4:
            n = (c[0] + di, c[1] + dj)
            if n not in exclude:
                nxt.add(n)
    return nxt


_inner = _dilate(CORE, CORE)
_outer = _dilate(_inner, CORE | _inner)
V2_SQUARE = CORE | _inner | _outer
SV2 = shape_stats(V2_SQUARE)
print(f"   real convexity envelope [{CONV_LO}, {CONV_HI}]  max_run [{MAXRUN_LO}, {MAXRUN_HI}]")
print(f"   v2 SQUARE control: convexity {SV2['convexity']} max_run {SV2['max_run']}  "
      f"-> convexity {'OUTSIDE' if not (CONV_LO <= SV2['convexity'] <= CONV_HI) else 'inside'}, "
      f"max_run {'OUTSIDE' if not (MAXRUN_LO <= SV2['max_run'] <= MAXRUN_HI) else 'inside'}  (the wrong control)")
print("   -> stock-vs-stock: comp[0] and comp[1] are BOTH inside their own [lo,hi] envelope by "
      "construction, so M3 does not separate stock from stock. VALID.")

# M4 interior-strip-coverage
cov0 = interior_strip_coverage(COMP0)
cov1 = interior_strip_coverage(COMP1)
bcov0 = boundary_strip_coverage(COMP0)
bcov1 = boundary_strip_coverage(COMP1)
COV_HI = max(cov0, cov1)
# the known-wrong control: a QUILT (half the interior cells tagged strip)
_qr = random.Random(1)
_inner1 = erode(erode(COMP1))
QUILT_COV = (sum(1 for _c in _inner1 if _qr.random() < 0.5) / len(_inner1)) if _inner1 else 0.0
print(f"\n   M4 interior-strip-coverage: comp[0] {cov0:.3%}  comp[1] {cov1:.3%}  "
      f"(boundary coverage comp[0] {bcov0:.1%} / comp[1] {bcov1:.1%})")
print(f"      QUILT control (50% interior tagged strip): {QUILT_COV:.1%}  "
      f"-> {'OUTSIDE' if QUILT_COV > COV_HI + 0.05 else 'inside'} (the v3 interior-quilt failure, correctly OUT)")
print("      -> stock-vs-stock: both components' interiors are ~all plain mains, so M4 does not "
      "separate stock from stock. VALID.")

# diagnostic: lag-1 autocorrelation (NON-gating) -- the ONE real structural difference the
# jumpiness metric cannot see (the arc's own established caveat). Stock strongly alternates
# step-to-step; the BFS emitter's mean across seeds is ~+0.073 (it under-alternates). Only the
# stable stock value is reported here -- a single-draw iid over the 5 short clean chains (~24
# pairs) is small-sample noise, so it is deliberately NOT quoted as if it were a null.
lag1_stock = lag1_autocorr(strip_cells, path_cell_seqs)
_l1s = f"{lag1_stock:+.3f}" if lag1_stock is not None else "n/a"
print(f"\n   [diagnostic, NON-gating] lag-1 row autocorrelation: STOCK {_l1s}  "
      f"(the BFS emitter's known miss is mean +0.073 -- it under-alternates; reported, never gated)")


# ============================================================================================
# STEP 5 -- RENDER the stock nulls at the three frozen zooms
# ============================================================================================
print("\n" + "=" * 96)
print("STEP 5: render the stock nulls (WIDE / MEDIUM / TIGHT) -- the reference panels")
print("=" * 96)


def cell_world_center(cell):
    return (cell[0] * CELL_U + CELL_U / 2.0, cell[1] * CELL_U + CELL_U / 2.0)


def blocks_around(cx, cz, pad=2):
    bx = int(math.floor(cx / BLOCK))
    by = int(math.floor(-cz / BLOCK))
    return [(bx + dx, by + dy) for dx in range(-pad, pad + 1) for dy in range(-pad, pad + 1)]


def comp_center(cellset):
    xs = [c[0] for c in cellset]
    zs = [c[1] for c in cellset]
    return ((min(xs) + max(xs)) / 2.0 * CELL_U + CELL_U / 2.0,
            (min(zs) + max(zs)) / 2.0 * CELL_U + CELL_U / 2.0)


# pick a pure-desert control window (a cell whose 5x5 cell neighbourhood is all desert-dominant)
def _dom(c):
    fc = fams_at.get(c)
    return fc.most_common(1)[0][0] if fc else None


desert_ctr = None
for c in sorted(fams_at):
    if all(_dom((c[0] + di, c[1] + dj)) == "desert" for di in range(-3, 4) for dj in range(-3, 4)):
        desert_ctr = cell_world_center(c)
        break
# pure-dunes-interior control: an eroded interior cell of comp[0]
_e0 = erode(erode(COMP0))
dunes_int_ctr = cell_world_center(sorted(_e0)[len(_e0) // 2]) if _e0 else comp_center(COMP0)

C0 = comp_center(COMP0)
C1 = comp_center(COMP1)
print(f"   comp[0] world center {tuple(round(v, 1) for v in C0)}  "
      f"comp[1] world center {tuple(round(v, 1) for v in C1)}")
print(f"   pure-desert control {tuple(round(v, 1) for v in desert_ctr) if desert_ctr else None}   "
      f"pure-dunes-interior control {tuple(round(v, 1) for v in dunes_int_ctr)}")

# seam windows spanning stock variance: (18,3) smooth-organic .. (13,12) boxy, + two more
SEAM_BLOCKS = [(18, 3), (13, 12), (13, 11), (19, 3)]


def seam_center(bxby):
    bx, by = bxby
    scs = [c for c in strip_cells if cellinfo[c]["block"] == (bx, by)]
    if scs:
        return ((sum(c[0] for c in scs) / len(scs) + 0.5) * CELL_U,
                (sum(c[1] for c in scs) / len(scs) + 0.5) * CELL_U)
    return (bx * BLOCK + 32.0, -(by * BLOCK + 32.0))


# ---- WIDE 200x160 sc=6: components + controls (texture + shaded) ----
print("\n   WIDE (200x160u sc=6):")
wide_panels = []
for lbl, ctr in [("comp[0] 273-cell IN SITU", C0), ("comp[1] 130-cell IN SITU (the mint twin)", C1),
                 ("pure-DESERT control", desert_ctr), ("pure-DUNES-interior control", dunes_int_ctr)]:
    if ctr is None:
        continue
    tex, com, nr = render_plan(blocks_around(*ctr, pad=2), ctr[0], ctr[1], 200, 160, sc=6, row_override=None)
    print(f"      {lbl}: centre ({ctr[0]:.0f},{ctr[1]:.0f}) {nr} blocks read")
    wide_panels.append((f"{lbl} -- TEXTURE", tex))
    wide_panels.append((f"{lbl} -- SHADED", com))
sheet(wide_panels, cols=2, cell_w=620, cell_h=496,
      path=OUTD / "dunes_mint_eye_wide.png",
      title="STOCK NULLS -- WIDE 200x160u sc=6 (all panels 100% unmodified stock). comp[1] IN SITU "
            "is the twin the mint's WIDE panel must be indistinguishable from.")

# ---- MEDIUM 56x56 sc=16 shaded: comp[1] + the seam-variance windows ----
print("\n   MEDIUM (56x56u sc=16, shaded):")
med_panels = []
for lbl, ctr in [("comp[1] IN SITU", C1), ("comp[0] IN SITU", C0)]:
    _t, com, nr = render_plan(blocks_around(*ctr, pad=1), ctr[0], ctr[1], 56, 56, sc=16, row_override=None)
    med_panels.append((f"{lbl} -- SHADED", com))
for bxby in SEAM_BLOCKS:
    ctr = seam_center(bxby)
    _t, com, nr = render_plan(blocks_around(*ctr, pad=1), ctr[0], ctr[1], 56, 56, sc=16, row_override=None)
    tag = "smooth-organic" if bxby == (18, 3) else ("boxy" if bxby == (13, 12) else "")
    med_panels.append((f"stock seam {bxby} {tag} -- SHADED", com))
    print(f"      seam {bxby}: ({ctr[0]:.0f},{ctr[1]:.0f}) {nr} blocks")
sheet(med_panels, cols=3, cell_w=520, cell_h=520,
      path=OUTD / "dunes_mint_eye_medium.png",
      title="STOCK NULLS -- MEDIUM 56x56u sc=16 shaded (play-scale). Stock seams span smooth-organic "
            "(18,3) to boxy (13,12): that spread IS how much stock varies against itself.")

# ---- TIGHT 24x24 sc=32 unshaded: the row/Rorschach zoom + the transplant-null 6-panel ----
print("\n   TIGHT (24x24u sc=32, unshaded):")
tight_panels = []
# stock reference tight views (comp[1] boundary + the two variance-extreme seams)
for lbl, ctr in [("comp[1] boundary IN SITU", C1)]:
    tex, _c, nr = render_plan(blocks_around(*ctr, pad=1), ctr[0], ctr[1], 24, 24, sc=32, row_override=None)
    tight_panels.append((f"{lbl}", tex))
for bxby in [(18, 3), (13, 12)]:
    ctr = seam_center(bxby)
    tex, _c, nr = render_plan(blocks_around(*ctr, pad=1), ctr[0], ctr[1], 24, 24, sc=32, row_override=None)
    tight_panels.append((f"stock seam {bxby} {'smooth' if bxby == (18, 3) else 'boxy'}", tex))
sheet(tight_panels, cols=3, cell_w=560, cell_h=560,
      path=OUTD / "dunes_mint_eye_tight_stock.png",
      title="STOCK NULLS -- TIGHT 24x24u sc=32 UNSHADED (raw albedo; the only zoom where row choice "
            "is legible). Note how little the 4 rows differ -- the row axis is nearly invisible.")

# the transplant-null 6-panel over the (18,3) window (v2's exact illustration -- MAP-WIDE controls
# so the override actually lands on this window's cells; the GATING band is ring-scale, above)
zc = seam_center((18, 3))
zblk = blocks_around(*zc, pad=1)
nk = sorted(NULL)
MW_ALL0 = {c: 0 for c in strip_cells}
_mwr = random.Random(0)
MW_IID = {c: _mwr.randrange(4) for c in sorted(strip_cells)}
MW_EMIT = emit_strip_rows(strip_cells.keys(), touch_of, TARGET_PMF, DELTA_P, 0)
null_panels_spec = [
    (f"STOCK real rows -- j={STOCK_J:.2f}", None),
    (f"TRANSPLANT {nk[0]} (REAL rows elsewhere) -- j={jumpiness(NULL[nk[0]]):.2f}", NULL[nk[0]]),
    (f"TRANSPLANT {nk[len(nk)//2]} (REAL rows elsewhere) -- j={jumpiness(NULL[nk[len(nk)//2]]):.2f}",
     NULL[nk[len(nk) // 2]]),
    (f"EMITTER seed0 -- j={jumpiness(MW_EMIT):.2f}", MW_EMIT),
    (f"CONTROL all-row-0 -- j={jumpiness(MW_ALL0):.2f}", MW_ALL0),
    (f"CONTROL iid-random -- j={jumpiness(MW_IID):.2f}", MW_IID),
]
np_panels = []
for lbl, ov in null_panels_spec:
    tex, _c, _n = render_plan(zblk, zc[0], zc[1], 24, 24, sc=32, row_override=ov)
    np_panels.append((lbl, tex))
sheet(np_panels, cols=3, cell_w=520, cell_h=520,
      path=OUTD / "dunes_mint_eye_transplant_null.png",
      title=f"THE TRANSPLANT NULL @ ({zc[0]:.0f},{zc[1]:.0f}) 24x24u sc=32 -- panels 2/3 are REAL FF9 "
            f"rows borrowed from the other cluster (map-wide illustration). Map-wide band "
            f"{MAPWIDE_LO:.2f}..{MAPWIDE_HI:.2f}; all-row-0={jumpiness(MW_ALL0):.2f} is the ONLY one out.")


# ============================================================================================
# STEP 6 -- FREEZE the criteria + judge() entry point for the builder
# ============================================================================================
print("\n" + "=" * 96)
print("STEP 6: THE FROZEN PASS/FAIL CRITERIA (calibrated once, here; the instrument is now frozen)")
print("=" * 96)

# small margins acknowledge finite-sample bands (n=99 ring transplants; n=2 real components for
# shape). all-row-0 (j=0.0, same-row=1.0) and v2-square (convexity 0.90, max_run 3) stay far outside
# any of these margins, so the margins buy robustness without admitting a degenerate build.
M1_MARGIN = 0.5      # luminance units (the whole 0->3 row span is only ~5.9, so 0.5 is generous)
SR_MARGIN = 0.05     # same-row fraction
CRITERIA = dict(
    # M1 -- ring row placement: luminance jumpiness in stock's own RING-SCALE transplant-null band
    m1_jumpiness_band=[round(BAND_LO - M1_MARGIN, 3), round(BAND_HI + M1_MARGIN, 3)],
    # M2 -- same-row adjacency %: stock's own RING-SCALE spread (comp[1]=0.36, comp[0]=0.15 etc.);
    # calibrated at the ~30-cell ring scale the judge measures, NOT the misleading map-wide 9.8%
    m2_same_row_band=[round(max(0.0, SR_LO - SR_MARGIN), 3), round(SR_HI + SR_MARGIN, 3)],
    # M3 -- silhouette: a WHOLE-STAMP mint must land in the real envelope (it should, by construction)
    m3_convexity_band=[round(min(CONV_LO, 0.45), 3), round(max(CONV_HI, 0.78), 3)],
    m3_max_run_min=int(MAXRUN_LO),   # >= 4: a too-regular (square) silhouette has max_run 3
    m3_require_hole=True,            # comp[1] carries a real enclosed topo-59 hole; a faithful stamp keeps it
    # M4 -- interior must stay plain mains (no quilt)
    m4_interior_strip_coverage_max=round(max(COV_HI, cov0, cov1) + 0.02, 4),
    # boundary coverage is a DESIGN TARGET (the ring dressing), reported not gated hard
    boundary_strip_coverage_target=[round(min(bcov0, bcov1), 3), round(max(bcov0, bcov1), 3)],
    # non-gating diagnostics
    diagnostic_lag1_stock=round(lag1_stock, 4) if lag1_stock is not None else None,
    row_step_luminance=round(STEP_LUM, 3),
    scale_note="M1/M2 bands are calibrated at the MINT'S ring scale (comp[1]'s ~30-cell strip ring), "
               "not the pooled 195-cell map. The self-test (judging stock comp[1]) PASSES; gating on "
               "the map-wide same-row 9.8% would FALSE-REJECT a verbatim stamp.",
    source_template="comp[1] (130 cells, 1 hole) -- the mint STAMPS this whole; the strongest gate "
                    "is an outline byte-match to this template (shape-fidelity), which makes M3 pass "
                    "by construction.",
)
for k, v in CRITERIA.items():
    print(f"   {k:38s} = {v}")


def judge(ring_rows, footprint_cells, *, boundary_cells=None, label="MINT", mesh=None):
    """The frozen instrument. Call on the BUILT mint before deploy.

    ring_rows       : {(i,j): row 0-3}  the strip-dressed ring cells of the mint (desert|dunes UV)
    footprint_cells : set of (i,j)      the full dune footprint (mains core + ring), for the silhouette
    boundary_cells  : optional set      the footprint's boundary cells (recomputed if None)
    mesh            : optional dict     when given, the THREE MESH GATES from `dunes_grazing_eye`
                                        are also run and merged in (keys `mesh_A/B/C_*`), and ALL
                                        must pass for the overall verdict. This is the axis the ROW
                                        gates below are BLIND to -- the label-stamp mint passes M1-M4
                                        but its mesh is castellated (off-grid seam verts, ori=0
                                        tiles, UVs that do not byte-derive from the donor). Pass a
                                        dict with the keys `judge_mesh` takes: cand_tris, cand_cmap,
                                        cand_fp_centroid, cand_fp41, donor_cmap, donor_fp41, T,
                                        criteria (+ optional cand_fam, render, render_tag). Default
                                        None preserves this instrument's frozen row-only behaviour
                                        byte-for-byte (the self-test/anti-test below pass mesh=None).

    Returns {gate: (value, pass_bool)}. ALL gates must pass. Bands are frozen above; this
    function reads no live state except the atlas-derived row_lum table (also frozen at import).
    """
    fp = set(footprint_cells)
    bcells = set(boundary_cells) if boundary_cells is not None else boundary_cells_of(fp)
    sh = shape_stats(fp)
    j = jumpiness(ring_rows)
    sr = same_row_pct(ring_rows)
    inner = erode(erode(fp))
    icov = (sum(1 for c in inner if c in ring_rows) / len(inner)) if inner else 0.0
    bcov = (sum(1 for c in bcells if c in ring_rows) / len(bcells)) if bcells else 0.0
    lo, hi = CRITERIA["m1_jumpiness_band"]
    srlo, srhi = CRITERIA["m2_same_row_band"]
    clo, chi = CRITERIA["m3_convexity_band"]
    res = {
        "M1_jumpiness": (round(j, 3), lo <= j <= hi),
        "M2_same_row": (None if sr is None else round(sr, 4),
                        sr is not None and srlo <= sr <= srhi),
        "M3_convexity": (sh["convexity"], sh["convexity"] is not None and clo <= sh["convexity"] <= chi),
        "M3_max_run": (sh["max_run"], sh["max_run"] >= CRITERIA["m3_max_run_min"]),
        "M3_has_hole": (sh["n_holes"], (sh["n_holes"] >= 1) or (not CRITERIA["m3_require_hole"])),
        "M4_interior_coverage": (round(icov, 4), icov <= CRITERIA["m4_interior_strip_coverage_max"]),
        "boundary_coverage(report)": (round(bcov, 3), True),
        "lag1(report)": (lag1_autocorr(ring_rows, path_cell_seqs), True),
    }
    if mesh is not None:
        import dunes_grazing_eye as _GE
        _m = _GE.judge_mesh(
            mesh["cand_tris"], mesh["cand_cmap"], mesh["cand_fp_centroid"], mesh["cand_fp41"],
            mesh["donor_cmap"], mesh["donor_fp41"], mesh["T"], mesh["criteria"],
            cand_fam=mesh.get("cand_fam"), cand_azimuth=mesh.get("cand_azimuth"),
            label=mesh.get("label", label), render=mesh.get("render", True),
            render_tag=mesh.get("render_tag"))
        for _g, (_v, _p) in _m["gates"].items():
            res["mesh_" + _g] = (_v, _p)
    allpass = all(p for _v, p in res.values())
    print(f"\n[judge {label}] {'>>> PASS <<<' if allpass else '>>> FAIL <<<'}")
    for g, (v, p) in res.items():
        print(f"   {g:28s} {str(v):>10}   {'ok' if p else 'FAIL'}")
    return dict(passed=allpass, gates=res)


# self-test the instrument: judging stock comp[1] ITSELF must PASS (a faithful whole-stamp = comp[1])
print("\n   INSTRUMENT SELF-TEST -- judging stock comp[1] in situ (a faithful whole-stamp equals this):")
_selftest = judge(region_rows(COMP1), COMP1, label="STOCK comp[1] (self-test)")
# and a deliberately-wrong build (v2 square + all-row-0) must FAIL
print("\n   ANTI-SELF-TEST -- a v2-square footprint with all-row-0 ring MUST fail:")
_v2ring = {c: 0 for c in boundary_cells_of(V2_SQUARE)}
_anti = judge(_v2ring, V2_SQUARE, label="v2-square + all-row-0 (anti-test)")


# ============================================================================================
# dump the frozen instrument
# ============================================================================================
out = dict(
    calibrated_utc="frozen at first run; re-runs are byte-deterministic",
    zooms=dict(wide="200x160u sc=6", medium="56x56u sc=16 shaded", tight="24x24u sc=32 unshaded"),
    components=dict(comp0=dict(size=len(COMP0), world_center=[round(v, 1) for v in C0], shape=S0),
                    comp1=dict(size=len(COMP1), world_center=[round(v, 1) for v in C1], shape=S1)),
    row_luminances={r: round(row_lum[r], 3) for r in range(4)},
    row_step_luminance=round(STEP_LUM, 3),
    m1_jumpiness=dict(scale="comp[1] ring (~30 cells) -- the judged scale",
                      ring_band=[round(BAND_LO, 3), round(BAND_HI, 3)],
                      verbatim_comp1=round(VERB_J, 3), n_ring_transplants=len(ring_null),
                      all_row0=round(j_all0, 3), iid=round(j_iid, 3),
                      emitter_seed_range=[round(min(emit_j), 3), round(max(emit_j), 3)],
                      emitter_in_band=f"{emit_in}/20",
                      mapwide_context=dict(stock=round(STOCK_J, 3),
                                           band=[round(MAPWIDE_LO, 3), round(MAPWIDE_HI, 3)],
                                           n=len(null_j))),
    m2_same_row=dict(scale="comp[1] ring", ring_band=[round(SR_LO, 4), round(SR_HI, 4)],
                     verbatim_comp1=round(VERB_SR, 4), all_row0=round(sr_all0, 4), iid=round(sr_iid, 4),
                     comp0_ring=same_row_pct(RING0), comp1_ring=round(VERB_SR, 4),
                     mapwide_context=round(same_row_pct(strip_cells), 4)),
    m3_shape=dict(convexity_envelope=[CONV_LO, CONV_HI], max_run_envelope=[MAXRUN_LO, MAXRUN_HI],
                  v2_square_control=dict(convexity=SV2["convexity"], max_run=SV2["max_run"])),
    m4_interior_coverage=dict(comp0=round(cov0, 5), comp1=round(cov1, 5), quilt_control=round(QUILT_COV, 4)),
    boundary_coverage=dict(comp0=round(bcov0, 4), comp1=round(bcov1, 4)),
    diagnostics=dict(lag1_stock=round(lag1_stock, 4) if lag1_stock is not None else None,
                     emitter_lag1_mean=0.073,
                     lag1_note="NON-gating; jumpiness cannot see this. Stock strongly alternates; "
                               "the BFS emitter under-alternates (+0.073)."),
    criteria=CRITERIA,
    self_test_stock_comp1_passes=_selftest["passed"],
    anti_test_v2square_allrow0_fails=not _anti["passed"],
    renders=[str(p.name) for p in sorted(OUTD.glob("dunes_mint_eye_*.png"))],
)
(OUTD / "dunes_mint_eye.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'dunes_mint_eye.json'}")
print("\nINSTRUMENT FROZEN. The builder imports judge() and calls it on the built mint's ring-rows +")
print("footprint; the WIDE/MEDIUM/TIGHT stock panels are the reference the mint's renders sit beside.")
print("DONE.")


# ============================================================================================
# THE MESH-GATE INTEGRATION DEMO (direct-run only; imports never trigger this heavy pass)
# --------------------------------------------------------------------------------------------
# Proves the `mesh=` hook wires `dunes_grazing_eye`'s three mesh gates into THIS judge flow:
#   - COMBINED SELF  (stock comp[1], row + mesh) must PASS.
#   - COMBINED ANTI  (the DEPLOYED label-stamp mint, row + mesh) must FAIL, and the deployed bytes
#     must fail on ALL THREE mesh axes -- the axis the row gates M1-M4 are blind to. (The row
#     axis alone caught only the hole-fill; the castellation is invisible to it.)
# ============================================================================================
if __name__ == "__main__":
    print("\n" + "=" * 96)
    print("MESH-GATE INTEGRATION DEMO -- judge(mesh=...) merges dunes_grazing_eye's 3 mesh gates")
    print("=" * 96)
    import dunes_grazing_eye as _GE

    _crit = _GE.load_criteria()
    _stock = _GE.load_stock()
    _sfam = _GE.cell_family(_stock)
    _scmap = _GE.cells_map(_stock)
    _sfp = _GE.dunes_footprint(_sfam)
    _sfp41 = _GE.topo41_footprint(_scmap)

    _self_mesh = dict(cand_tris=_stock, cand_cmap=_scmap, cand_fp_centroid=_sfp, cand_fp41=_sfp41,
                      donor_cmap=_scmap, donor_fp41=_sfp41, T=(0, 0), criteria=_crit,
                      cand_fam=_sfam, render=True, render_tag="integ_self",
                      label="stock comp[1] mesh (combined self)")
    print("\n-- COMBINED SELF-TEST: stock comp[1] on the ROW axis AND the MESH axis --")
    _combined_self = judge(region_rows(COMP1), COMP1, mesh=_self_mesh, label="COMBINED SELF (stock)")

    _mint = _GE.load_mod(_GE.MINT_BLOCKS)
    _mfam = _GE.cell_family(_mint)
    _mcmap = _GE.cells_map(_mint)
    _mfp = _GE.dunes_footprint(_mfam)
    _mfp41 = _GE.topo41_footprint(_mcmap)
    _T = _GE.translation(_sfp41, _mfp41)
    _mrows = _GE.strip_rowmap(_mcmap, _mfp)
    _anti_mesh = dict(cand_tris=_mint, cand_cmap=_mcmap, cand_fp_centroid=_mfp, cand_fp41=_mfp41,
                      donor_cmap=_scmap, donor_fp41=_sfp41, T=_T, criteria=_crit,
                      cand_fam=_mfam, render=True, render_tag="integ_anti",
                      label="deployed mint mesh (combined anti)")
    print("\n-- COMBINED ANTI-TEST: the DEPLOYED label-stamp mint on the ROW axis AND the MESH axis --")
    _combined_anti = judge(_mrows, _mfp, mesh=_anti_mesh, label="COMBINED ANTI (deployed mint)")

    _mesh_fails = [g for g, (v, p) in _combined_anti["gates"].items()
                   if g.startswith("mesh_") and not p]
    print("\n" + "=" * 96)
    print(f"INTEGRATION: combined-self PASS={_combined_self['passed']}  "
          f"combined-anti FAIL={not _combined_anti['passed']}  "
          f"mesh gates failed on the deployed mint = {len(_mesh_fails)}/3 {_mesh_fails}")
    print("=" * 96)
    assert _combined_self["passed"], "combined self-test (stock, row+mesh) must PASS"
    assert not _combined_anti["passed"], "combined anti-test (deployed mint) must FAIL"
    assert len(_mesh_fails) == 3, "the deployed mint must fail ALL THREE mesh gates"
    print("MESH-GATE INTEGRATION VERIFIED: the row judge flow now spends the mesh axis it was blind to.")
