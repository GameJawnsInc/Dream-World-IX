"""DUNES BOUNDARY COMPOSITION -- round 4 of the ecotone-strip placement arc. dunes_strip_emitter.py
(round 3) measured the ROW a strip cell wears; it never measured WHICH cells wear a strip at all --
that emitter is only ever called on a cellset the CALLER already decided was "the ring". v3 of
dunes_patch_mint.py assumed 100% ring coverage (every footprint-boundary cell + every outward-dilation
cell gets a strip), which the offline eye reads as a desert/dunes CHECKER QUILT at gameplay scale (a
12-cell solid core inside a 43-cell transition band, 61% boundary vs stock's measured 32-45% -- see
GROUND-FAMILY-DECODE-2026-07-19.md). This script measures the piece v3 skipped: stock's actual
COVERAGE + SIDE-CONDITIONAL ROW BIAS + CONTIGUITY + INTERIOR SOLIDITY along the two real dunes|desert
boundaries, so a next mint round can dress a stamped footprint with the MEASURED rule instead of a
uniform-coverage assumption.

Cell-classification machinery (FAM_OF topo->family map, the tri-level classify_tri/classify_strip UV
classifier, connected_components, boundary_trace) is a verbatim re-derivation of dunes_blob_shapes.py's
/ dunes_strip_emitter.py's own copies -- not imported (LAW 5: every script independently rerunnable).
Both source scripts' 480-block census is folded into ONE pass here (family census AND tri-level
strip/mains tag census together), so this script costs one map scan, not two.

MEASURES (orchestrator brief, Part 1):
  1. STRIP COVERAGE -- of each component's own dune-side boundary cells (the outer-loop walk, matching
     dunes_blob_shapes.py's n_outer_boundary_cells: 122 for comp[0], 42 for comp[1]), what fraction
     actually classify as ("strip", row) rather than ("mains", "dunes")? Same question for the
     desert-family cells in each component's 1-cell outward ring (the "desert-side outer cells").
  2. SIDE-CONDITIONAL ROWS -- the row histogram of dune-side strip cells vs desert-side strip cells
     (does dunes-side skew high/rows 2-3, desert-side skew low/rows 0-1, and how hard).
  3. CONTIGUITY -- walking each component's real boundary in geometric order (the same directed-edge
     chain-walk dunes_blob_shapes.py's boundary_trace already extracts), are strip cells contiguous
     RUNS or scattered singletons? Run-length histogram of strip-vs-plain along the walk, both sides.
  4. INTERIOR SOLIDITY -- multi-source BFS erosion-depth from each component's own boundary: does ANY
     cell at depth>=2 (i.e. NOT on the boundary walk) ever carry a strip tag? If so, how far inland.

Run from the repo root:  py studies/overworld-topography/dunes_boundary_composition.py
Artifacts -> out/dunes_boundary_composition.json
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                      # noqa: E402
from ff9mapkit.world import grassland as G                    # noqa: E402

HERE = Path(__file__).parent
OUTD = HERE / "out"
OUTD.mkdir(exist_ok=True)

BLOCK = 64.0
CELL_U = 4.0
EPS = 0.006
TOL_V = 0.008
ROW_PITCH = 0.03125
NEI4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
BIG_THRESH = 6           # a component >= this size is "a real component" (dunes_blob_shapes.py's own cut)

# ---- FAM_OF -- verbatim re-derivation of dunes_strip_emitter.py's/dunes_blob_shapes.py's topo->family
# map (LAW 5) -----------------------------------------------------------------------------------------
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

PAIR = ("desert", "dunes")
FAM_A, FAM_B = PAIR          # A = desert (measured LOW base row), B = dunes (measured HIGH base row)

STRIP_U0, STRIP_U1 = G.STRIP_U
ROW0_V0 = G.STRIPS_V[0][0]
_S = G.STRIPS[PAIR]
_DU, _DV = _S["du"], _S["dv"]


def mains_rect(fam):
    m = G.FAM_REGION["main"]
    g = G.GROUNDS[fam]
    return (m[0] + g["mains_du"], m[1] + g["mains_dv"], m[2] + g["mains_du"], m[3] + g["mains_dv"])


RECTS = {"desert": mains_rect("desert"), "dunes": mains_rect("dunes")}


def rect_contains(rect, uv3, eps=EPS):
    return all(rect[0] - eps <= u <= rect[2] + eps and rect[1] - eps <= v <= rect[3] + eps for (u, v) in uv3)


def classify_strip(uv3):
    """Snap a candidate tri's min-v corner to the nearest of the 4 STRIPS_V rows. Returns row 0-3 or
    None. Verbatim re-derivation of dunes_strip_emitter.py's classify_strip (LAW 5)."""
    u_lo, u_hi = STRIP_U0 + _DU - EPS, STRIP_U1 + _DU + EPS
    if not all(u_lo <= u <= u_hi for (u, _v) in uv3):
        return None
    v_min = min(v for (_u, v) in uv3)
    row0 = ROW0_V0 + _DV
    k = round((v_min - row0) / ROW_PITCH)
    if k < 0 or k > 3:
        return None
    if abs((v_min - row0) - k * ROW_PITCH) > TOL_V:
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
# STEP 1 -- ONE map-wide pass: per-cell dominant FAMILY (for component membership, dunes_blob_
# shapes.py's own method) AND per-cell dominant TAG (strip/mains/other, dunes_strip_emitter.py's
# own method) together -- folds both source scripts' separate 480-block scans into one.
# ============================================================================================
print("=== STEP 1: map-wide per-cell family + tag census (one pass, all 24x20 disc-1 blocks) ===")

fams_at: dict = defaultdict(Counter)
tags_at: dict = defaultdict(Counter)
block_at = {}
n_blocks_read = 0
for bx in range(24):
    for by in range(20):
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            continue
        n_blocks_read += 1
        V, TAN = bm.verts, bm.tangents
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            topo = X.decode_id(int(round(TAN[tri[0]][0])))["topograph"]
            fam = FAM_OF.get(topo)
            if fam is None:
                continue
            uv3 = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
            cx = sum(V[j][0] for j in tri) / 3.0 + BLOCK * bx
            cz = sum(V[j][2] for j in tri) / 3.0 - BLOCK * by
            cell = (math.floor(cx / CELL_U), math.floor(cz / CELL_U))
            fams_at[cell][fam] += 1
            tags_at[cell][classify_tri(fam, uv3)] += 1
            block_at[cell] = (bx, by)

print(f"blocks read: {n_blocks_read}/480; cells classified: {len(fams_at)}")

cellinfo = {}
for cell, fc in fams_at.items():
    fam_mode, _ = fc.most_common(1)[0]
    tc = tags_at[cell]
    tag_mode, tag_n = tc.most_common(1)[0]
    cellinfo[cell] = dict(fam=fam_mode, tag=tag_mode, block=block_at[cell])

cell_fam = {c: info["fam"] for c, info in cellinfo.items()}
dunes_cells = {c for c, f in cell_fam.items() if f == "dunes"}
n_dunes_topo_strip = sum(1 for c in dunes_cells if cellinfo[c]["tag"][0] == "strip")
n_desert_topo_strip = sum(1 for c, f in cell_fam.items() if f == "desert" and cellinfo[c]["tag"][0] == "strip")
print(f"dunes-family cells: {len(dunes_cells)}; dunes-topo strip cells: {n_dunes_topo_strip}; "
      f"desert-topo strip cells (map-wide, sanity xref vs dunes_strip_emitter.json's 99/96): "
      f"{n_dunes_topo_strip}/{n_desert_topo_strip}")


# ============================================================================================
# STEP 2 -- connected components (verbatim re-derivation of dunes_blob_shapes.py's own method)
# ============================================================================================
def connected_components(cellset):
    visited, comps = set(), []
    for start in cellset:
        if start in visited:
            continue
        comp = set()
        q = deque([start]); visited.add(start)
        while q:
            c = q.popleft(); comp.add(c)
            for di, dj in NEI4:
                n = (c[0] + di, c[1] + dj)
                if n in cellset and n not in visited:
                    visited.add(n); q.append(n)
        comps.append(comp)
    return comps


components = connected_components(dunes_cells)
components.sort(key=len, reverse=True)
big_components = [c for c in components if len(c) >= BIG_THRESH]
print(f"\n=== STEP 2: {len(components)} components ({len(big_components)} size>={BIG_THRESH}): "
      f"sizes {sorted((len(c) for c in components), reverse=True)} ===")


# ============================================================================================
# STEP 3 -- boundary trace, EXTENDED to also carry the exterior (non-cellset) neighbour per edge
# so the geometric walk yields BOTH an owning-cell (dune-side) sequence and an aligned exterior-
# cell (desert-side) sequence. Verbatim re-derivation of dunes_blob_shapes.py's boundary_trace()
# + turn_priority(), extended (LAW 5).
# ============================================================================================
def boundary_trace_ext(cellset):
    directed = {}      # (a,b) -> (owning_cell, exterior_cell)
    for (i, j) in cellset:
        bl, br, tr, tl = (i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)
        sides = [(bl, br, (i, j - 1)), (br, tr, (i + 1, j)),
                 (tr, tl, (i, j + 1)), (tl, bl, (i - 1, j))]
        for (a, b, nb) in sides:
            if nb in cellset:
                continue
            directed[(a, b)] = ((i, j), nb)
    out_from = defaultdict(list)
    for (a, b), (cell, nb) in directed.items():
        out_from[a].append((b, cell, nb))

    def turn_priority(prev_dir, cand_dir):
        cross = prev_dir[0] * cand_dir[1] - prev_dir[1] * cand_dir[0]
        dot = prev_dir[0] * cand_dir[0] + prev_dir[1] * cand_dir[1]
        return -math.atan2(cross, dot)

    remaining = dict(directed)
    loops = []
    while remaining:
        (a0, b0) = next(iter(remaining))
        loop = []
        a, b = a0, b0
        cell0, nb0 = remaining.pop((a0, b0))
        loop.append((a, b, cell0, nb0))
        cur = b
        prev_dir = (b[0] - a[0], b[1] - a[1])
        guard = 0
        while cur != a0 and guard < 100000:
            guard += 1
            cands = [(end, cell, nb) for (end, cell, nb) in out_from[cur] if (cur, end) in remaining]
            if not cands:
                break
            if len(cands) == 1:
                end, cell, nb = cands[0]
            else:
                end, cell, nb = min(cands, key=lambda ecn: turn_priority(prev_dir, (ecn[0][0] - cur[0], ecn[0][1] - cur[1])))
            remaining.pop((cur, end))
            loop.append((cur, end, cell, nb))
            prev_dir = (end[0] - cur[0], end[1] - cur[1])
            cur = end
        loops.append(loop)
    return loops


def loop_area(loop):
    a = 0.0
    for (p, q, _c, _n) in loop:
        a += p[0] * q[1] - q[0] * p[1]
    return a / 2.0


def outer_loop_of(cellset):
    loops = boundary_trace_ext(cellset)
    outer_loops = [lp for lp in loops if loop_area(lp) > 0]
    return max(outer_loops, key=lambda lp: abs(loop_area(lp))) if outer_loops else (max(loops, key=len) if loops else [])


def dedup_walk(seq):
    out = []
    for x in seq:
        if not out or out[-1] != x:
            out.append(x)
    return out


def run_lengths(bool_seq):
    """Circular run-length of a boolean sequence (the walk is a closed loop)."""
    if not bool_seq:
        return []
    if len(set(bool_seq)) == 1:
        return [len(bool_seq)]
    # rotate to start at a boundary between False/True so runs don't wrap-split
    start = next(i for i in range(len(bool_seq)) if bool_seq[i] != bool_seq[i - 1])
    seq = bool_seq[start:] + bool_seq[:start]
    runs, cur, ln = [], seq[0], 1
    for x in seq[1:]:
        if x == cur:
            ln += 1
        else:
            runs.append((cur, ln)); cur, ln = x, 1
    runs.append((cur, ln))
    return runs


# ============================================================================================
# PER-COMPONENT MEASUREMENT
# ============================================================================================
print("\n=== STEP 3+4: per-component coverage / side-conditional rows / contiguity / interior solidity ===")

component_reports = []
all_dune_side_rows, all_desert_side_rows = [], []
all_dune_runs, all_desert_runs = [], []

for ci_idx, comp in enumerate(big_components):
    outer = outer_loop_of(comp)
    dune_walk = dedup_walk([cell for (_p, _q, cell, _nb) in outer])
    ext_walk_raw = [nb for (_p, _q, _cell, nb) in outer]
    ext_walk = dedup_walk(ext_walk_raw)

    # ---- 1. STRIP COVERAGE, dune-side boundary walk ----
    dune_tags = [cellinfo.get(c, {}).get("tag", ("other",)) for c in dune_walk]
    dune_is_strip = [t[0] == "strip" for t in dune_tags]
    n_dune_strip = sum(dune_is_strip)
    dune_coverage = n_dune_strip / len(dune_walk) if dune_walk else 0.0

    # ---- 1. STRIP COVERAGE, desert-side outer walk (restrict the FRACTION stat to cells whose
    # own family is actually 'desert' -- a handful of exterior neighbours are off-census/other
    # family (comp[0] touches 1 'brush' cell, comp[1] touches 1 'grass' cell + 18 off-census per
    # dunes_blob_shapes.json's boundary_neighbour_family_by_component -- reported, not silently
    # dropped) ----
    ext_fam = [cell_fam.get(c) for c in ext_walk]
    ext_desert_mask = [f == "desert" for f in ext_fam]
    ext_desert_cells = [c for c, m in zip(ext_walk, ext_desert_mask) if m]
    ext_desert_tags = [cellinfo[c]["tag"] for c in ext_desert_cells]
    ext_is_strip_desert_only = [t[0] == "strip" for t in ext_desert_tags]
    n_ext_strip = sum(ext_is_strip_desert_only)
    ext_coverage = n_ext_strip / len(ext_desert_cells) if ext_desert_cells else 0.0
    n_ext_off_census = sum(1 for f in ext_fam if f not in ("desert",))

    # ---- 2. SIDE-CONDITIONAL ROWS ----
    dune_rows = [t[1] for t in dune_tags if t[0] == "strip"]
    desert_rows = [t[1] for t in ext_desert_tags if t[0] == "strip"]
    all_dune_side_rows += dune_rows
    all_desert_side_rows += desert_rows

    # ---- 3. CONTIGUITY -- run-length of strip-vs-plain along the ordered walk, both sides ----
    dune_runs = run_lengths(dune_is_strip)
    # for the desert-side walk, run-length over the FULL ext_walk (True=strip, False=plain-or-
    # other) so the walk stays geometrically ordered/contiguous; off-census cells count as "plain"
    # here (they are not strip by construction -- classify_tri only ever tags desert/dunes fam)
    ext_is_strip_full = [cell_fam.get(c) == "desert" and cellinfo[c]["tag"][0] == "strip" for c in ext_walk]
    ext_runs = run_lengths(ext_is_strip_full)
    dune_strip_run_lens = [ln for (val, ln) in dune_runs if val]
    dune_plain_run_lens = [ln for (val, ln) in dune_runs if not val]
    ext_strip_run_lens = [ln for (val, ln) in ext_runs if val]
    ext_plain_run_lens = [ln for (val, ln) in ext_runs if not val]
    all_dune_runs += dune_strip_run_lens
    all_desert_runs += ext_strip_run_lens

    # ---- 4. INTERIOR SOLIDITY -- multi-source BFS erosion-depth from the boundary walk cells ----
    boundary_set = set(dune_walk)
    depth = {c: 1 for c in boundary_set}
    q = deque(boundary_set)
    while q:
        c = q.popleft()
        for di, dj in NEI4:
            n = (c[0] + di, c[1] + dj)
            if n in comp and n not in depth:
                depth[n] = depth[c] + 1
                q.append(n)
    interior_cells = [c for c in comp if depth.get(c, 1) >= 2]
    interior_strip_cells = [c for c in interior_cells if cellinfo.get(c, {}).get("tag", ("other",))[0] == "strip"]
    max_strip_depth = max((depth[c] for c in interior_strip_cells), default=1)
    max_depth_reached = max(depth.values()) if depth else 0

    # ---- v4 NEW: the RAW ordered walk sequences (position-aligned, NOT sorted) -- the transplant
    # dressing variant needs a genuine contiguous stretch of stock's own arrangement, not just the
    # aggregated run-length/row statistics above. Each entry is [is_strip, row_or_-1] for the dune
    # walk, and [is_strip, row_or_-1_or_-2] for the ext walk (-2 = off-census/non-desert-family
    # exterior cell -- geometrically real but not part of the desert-side strip vocabulary).
    dune_walk_strip_row = [[bool(s), (cellinfo[c]["tag"][1] if s else -1)] for c, s in zip(dune_walk, dune_is_strip)]
    ext_walk_strip_row = []
    for c in ext_walk:
        f = cell_fam.get(c)
        if f != "desert":
            ext_walk_strip_row.append([False, -2])
        else:
            t = cellinfo[c]["tag"]
            ext_walk_strip_row.append([bool(t[0] == "strip"), (t[1] if t[0] == "strip" else -1)])

    rep = dict(
        component_idx=ci_idx, size=len(comp),
        dune_walk_cells=[list(c) for c in dune_walk], dune_walk_strip_row=dune_walk_strip_row,
        ext_walk_cells=[list(c) for c in ext_walk], ext_walk_strip_row=ext_walk_strip_row,
        dune_side=dict(n_boundary_walk_cells=len(dune_walk), n_strip=n_dune_strip,
                        coverage=round(dune_coverage, 4), row_hist=dict(sorted(Counter(dune_rows).items())),
                        strip_run_lengths=sorted(dune_strip_run_lens, reverse=True),
                        plain_run_lengths=sorted(dune_plain_run_lens, reverse=True)),
        desert_side=dict(n_outer_walk_cells_total=len(ext_walk), n_outer_desert_family_cells=len(ext_desert_cells),
                          n_off_census_or_other_family=n_ext_off_census, n_strip=n_ext_strip,
                          coverage=round(ext_coverage, 4), row_hist=dict(sorted(Counter(desert_rows).items())),
                          strip_run_lengths=sorted(ext_strip_run_lens, reverse=True),
                          plain_run_lengths=sorted(ext_plain_run_lens, reverse=True)),
        interior_solidity=dict(n_interior_cells_depth_ge2=len(interior_cells),
                                n_interior_strip_cells=len(interior_strip_cells),
                                interior_strip_fraction=round(len(interior_strip_cells) / len(interior_cells), 4) if interior_cells else None,
                                max_depth_reached_by_any_cell=max_depth_reached,
                                max_depth_reached_by_a_strip_cell=max_strip_depth,
                                interior_is_100pct_plain_mains=(len(interior_strip_cells) == 0)),
    )
    component_reports.append(rep)
    print(f"\ncomp[{ci_idx}] size={len(comp)}")
    print(f"  DUNE-SIDE : boundary_walk_cells={len(dune_walk)} strip={n_dune_strip} "
          f"coverage={dune_coverage:.1%}  row_hist={rep['dune_side']['row_hist']}")
    print(f"    strip run-lengths (walk order): {rep['dune_side']['strip_run_lengths']}  "
          f"plain run-lengths: {rep['dune_side']['plain_run_lengths']}")
    print(f"  DESERT-SIDE: outer_walk_cells={len(ext_walk)} (desert-family={len(ext_desert_cells)}, "
          f"off-census/other-family={n_ext_off_census}) strip={n_ext_strip} "
          f"coverage(of desert-family only)={ext_coverage:.1%}  row_hist={rep['desert_side']['row_hist']}")
    print(f"    strip run-lengths (walk order): {rep['desert_side']['strip_run_lengths']}  "
          f"plain run-lengths: {rep['desert_side']['plain_run_lengths']}")
    print(f"  INTERIOR SOLIDITY: {len(interior_cells)} cells at depth>=2, "
          f"{len(interior_strip_cells)} of them strip-tagged "
          f"({'100% plain mains -- CONFIRMED' if not interior_strip_cells else f'max strip depth={max_strip_depth}'}), "
          f"max depth reached by ANY cell (component thickness) = {max_depth_reached}")


# ============================================================================================
# POOLED SUMMARY (both real components combined)
# ============================================================================================
print("\n=== POOLED (both components combined) ===")
pooled_dune_cov = sum(r["dune_side"]["n_strip"] for r in component_reports) / \
    sum(r["dune_side"]["n_boundary_walk_cells"] for r in component_reports)
pooled_desert_cov = sum(r["desert_side"]["n_strip"] for r in component_reports) / \
    sum(r["desert_side"]["n_outer_desert_family_cells"] for r in component_reports)
print(f"DUNE-SIDE coverage (pooled): {pooled_dune_cov:.1%} "
      f"({sum(r['dune_side']['n_strip'] for r in component_reports)}/"
      f"{sum(r['dune_side']['n_boundary_walk_cells'] for r in component_reports)})")
print(f"DESERT-SIDE coverage (pooled, desert-family cells only): {pooled_desert_cov:.1%} "
      f"({sum(r['desert_side']['n_strip'] for r in component_reports)}/"
      f"{sum(r['desert_side']['n_outer_desert_family_cells'] for r in component_reports)})")

dune_row_hist = dict(sorted(Counter(all_dune_side_rows).items()))
desert_row_hist = dict(sorted(Counter(all_desert_side_rows).items()))
dune_row_mean = float(np.mean(all_dune_side_rows)) if all_dune_side_rows else None
desert_row_mean = float(np.mean(all_desert_side_rows)) if all_desert_side_rows else None
print(f"\nSIDE-CONDITIONAL ROW HISTOGRAM (pooled):")
print(f"  dunes-side   strip cells: n={len(all_dune_side_rows):3d} hist={dune_row_hist}  "
      f"mean={dune_row_mean:.3f}" if dune_row_mean is not None else "  dunes-side: n=0")
print(f"  desert-side  strip cells: n={len(all_desert_side_rows):3d} hist={desert_row_hist}  "
      f"mean={desert_row_mean:.3f}" if desert_row_mean is not None else "  desert-side: n=0")
skew_note = (f"dunes-side mean {dune_row_mean:.3f} {'>' if dune_row_mean > desert_row_mean else '<='} "
             f"desert-side mean {desert_row_mean:.3f} -- "
             f"{'CONFIRMS' if dune_row_mean > desert_row_mean else 'DOES NOT CONFIRM'} the "
             "dunes-side-skews-high/desert-side-skews-low hypothesis") \
    if (dune_row_mean is not None and desert_row_mean is not None) else "insufficient data"
print(f"  -> {skew_note}")

dune_run_hist = dict(sorted(Counter(all_dune_runs).items()))
desert_run_hist = dict(sorted(Counter(all_desert_runs).items()))
print(f"\nCONTIGUITY (pooled strip-run-length histogram, walk order):")
print(f"  dunes-side  strip runs: {dune_run_hist}  (mean={float(np.mean(all_dune_runs)):.2f})" if all_dune_runs else "  dunes-side: no strip runs")
print(f"  desert-side strip runs: {desert_run_hist}  (mean={float(np.mean(all_desert_runs)):.2f})" if all_desert_runs else "  desert-side: no strip runs")

all_dune_plain_runs = [ln for r in component_reports for ln in r["dune_side"]["plain_run_lengths"]]
all_desert_plain_runs = [ln for r in component_reports for ln in r["desert_side"]["plain_run_lengths"]]
dune_plain_run_hist = dict(sorted(Counter(all_dune_plain_runs).items()))
desert_plain_run_hist = dict(sorted(Counter(all_desert_plain_runs).items()))
print(f"  dunes-side  plain runs: {dune_plain_run_hist}  (mean={float(np.mean(all_dune_plain_runs)):.2f})" if all_dune_plain_runs else "  dunes-side: no plain runs")
print(f"  desert-side plain runs: {desert_plain_run_hist}  (mean={float(np.mean(all_desert_plain_runs)):.2f})" if all_desert_plain_runs else "  desert-side: no plain runs")

n_interior_total = sum(r["interior_solidity"]["n_interior_cells_depth_ge2"] for r in component_reports)
n_interior_strip_total = sum(r["interior_solidity"]["n_interior_strip_cells"] for r in component_reports)
print(f"\nINTERIOR SOLIDITY (pooled): {n_interior_strip_total}/{n_interior_total} depth>=2 cells are "
      f"strip-tagged ({'0.0% -- INTERIOR IS 100% PLAIN MAINS, CONFIRMED map-wide' if n_interior_strip_total == 0 else f'{n_interior_strip_total/n_interior_total:.1%}'})")

# cross-check vs the known global totals (dunes_strip_emitter.json: 99 dunes-topo / 96 desert-topo
# strip cells map-wide, over the SAME two components since dunes_blob_shapes.json found 0 freckles)
xcheck_dune = sum(r["dune_side"]["n_strip"] for r in component_reports)
xcheck_desert_all = sum(r["desert_side"]["n_strip"] for r in component_reports)  # desert-family only
print(f"\nXCHECK vs known global totals: dune-side strip cells found here = {xcheck_dune} "
      f"(dunes_strip_emitter.json's own-family dunes-topo-strip count = {n_dunes_topo_strip}); "
      f"desert-side (desert-family only) strip cells found here = {xcheck_desert_all} "
      f"(dunes_strip_emitter.json's desert-topo-strip count = {n_desert_topo_strip} -- may exceed "
      f"this script's count if some desert-topo strip cells sit outside any big dunes component's "
      f"1-cell outer ring, e.g. between the two components' own separate seams)")

# ============================================================================================
# summary dump
# ============================================================================================
out = dict(
    n_blocks_read=n_blocks_read, n_cells_classified=len(fams_at),
    n_dunes_cells=len(dunes_cells), n_components=len(components),
    component_sizes=sorted((len(c) for c in components), reverse=True),
    n_big_components=len(big_components), big_thresh=BIG_THRESH,
    n_dunes_topo_strip_cells_global=n_dunes_topo_strip, n_desert_topo_strip_cells_global=n_desert_topo_strip,
    components=component_reports,
    pooled=dict(
        dune_side_coverage=round(pooled_dune_cov, 4), desert_side_coverage=round(pooled_desert_cov, 4),
        dune_side_row_hist=dune_row_hist, desert_side_row_hist=desert_row_hist,
        dune_side_row_mean=round(dune_row_mean, 4) if dune_row_mean is not None else None,
        desert_side_row_mean=round(desert_row_mean, 4) if desert_row_mean is not None else None,
        dune_side_strip_run_hist=dune_run_hist, desert_side_strip_run_hist=desert_run_hist,
        dune_side_plain_run_hist=dune_plain_run_hist, desert_side_plain_run_hist=desert_plain_run_hist,
        interior_strip_cells_total=n_interior_strip_total, interior_cells_total=n_interior_total,
        interior_is_100pct_plain_mains=(n_interior_strip_total == 0),
        skew_note=skew_note,
    ),
)
(OUTD / "dunes_boundary_composition.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'dunes_boundary_composition.json'}")
print("\nDONE.")
