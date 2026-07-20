"""THE FIRST MINTED DUNES ECOTONE PATCH -- v3 (this round replaces v2's rectilinear 3x3-core +
concentric-shells design, which ``dunes_blob_shapes.py`` proved renders as a SQUARE FRAME -- straight
cell-column seams, 90-degree corners -- while every real stock dunes closure is an organic blob:
v2's convexity 0.9024 sits *above* the measured real max 0.754, and its run-length histogram is a
clean bimodal {1,3} vs real's broad decaying {1,2,3,4}/{1,2,3,5} spread.

**v3's fix: STAMP a real stock footprint (cell-set SHAPE ONLY, zero texture/UV bytes carried) instead
of generating a synthetic core+shells.** The template is ``lobe_of_comp_0_cut_at_saddle`` from
``out/dunes_blob_templates.json`` (``dunes_blob_shapes.py``'s census): a 31-cell, bbox-9x6 closed lobe
cut from the 273-cell real dunes component at blocks (18,3)/(18,4)/(19,3)/(19,4)/(20,3) -- the only
template that (a) is a genuine piece of real stock geometry and (b) fits an ~80-regular-cell host
budget with its ring (both whole stock components, 130 and 273 cells, do not). 19 of its 31 cells are
its own boundary (16 real stock component edge, 3 on the erosion-Voronoi SYNTHETIC cut where this
lobe was severed from its 6 sibling lobes) -- see ``_template_provenance()`` for the live-reverified
breakdown.

**Everything the census called out as ALREADY CORRECT survives unchanged**: the desert host build
(``island.build_landmass``), the dunes-mains retile rule (``grassland.ground_uv(..., "dunes")``), the
frozen-constant BFS row emitter (``dunes_strip_emitter.py``'s measured TARGET_PMF/DELTA_P, re-verified
live every run -- LAW 5) with its cross-boundary ``|drow|<=1`` hard constraint generalized from "inner
shell vs outer shell" to "the footprint's own boundary cells vs the 1-cell ring outside it" (the BFS
emitter's cellset/shell_of machinery was already an arbitrary 2D-seam abstraction; only the SHAPE
feeding it changes), and zero vertex motion (uv/tangent.x only).

**What "core/inner/outer" now mean, generalized from v1/v2's concentric-square language to an
arbitrary stamped footprint:**
- CORE = the footprint's own INTERIOR cells (footprint minus its own boundary cells) -- plain dunes
  MAINS UV, no strip, topo 41.
- INNER = the footprint's own BOUNDARY cells (``template["boundary_cell_offsets"]``, transformed +
  translated onto the host) -- dunes-side strip UV, topo 41, touch-category ``B-only`` (fixed, same
  convention v1/v2 used for their inner ring).
- OUTER = the 1-cell 4-neighbour dilation of the WHOLE footprint (not just the core) -- desert-side
  strip UV, topo 17, touch-category ``A-only``/``neither`` exactly as v2 computed it, just keyed off
  the footprint's outward dilation instead of a 3x3 core's.

**Placement**: an exhaustive search over all 8 dihedral transforms (4 rotations x mirror) and every
translation across the host's REGULAR-cell region (the same 4u-grid-square classifier v1/v2 already
used to exclude the irregular rim-blend cells -- the CLEAN-BOUNDARY precedent, generalized from
"does a fixed 3x3+shells window fit" to "does ANY dihedral placement of the template+ring fit"), for
one candidate: footprint AND its outward ring must land entirely on regular cells. The primary design
site (seed=2, radius=26, block (10,19), ``dunes_mint_design.md`` Sec.4) has exactly ONE such placement
(dihedral=rot270, verified this round -- see ``resolve_site_and_placement()``'s printed search log) --
no fallback tier (seed scan 1-39 / radius scan 27-30 / block (11,19)) was needed, though all three are
implemented and would run in that order if it had been.

**Freckles**: ``dunes_blob_shapes.py`` found ZERO 1-2-cell satellite dunes components anywhere on the
map (falsifying the task brief's "freckle satellite" premise) -- so v3 mints none, rather than
inventing an unmeasured strip treatment for them.

Gate list = v2's (this round renames "CROSS-SHELL SMOOTHNESS" -> "CROSS-BOUNDARY SMOOTHNESS", same
logic) + two NEW structural gates: RING COMPLETENESS is now checked against the template's own
boundary/dilation counts (not a fixed shell theory), and a new SHAPE-FIDELITY gate asserts the placed
footprint's straight-run-length histogram + corner count are IDENTICAL to the template's own (a rigid
dihedral transform + translation cannot change either metric; any diff would mean a cell was
silently dropped during placement -- "it is a stamp, any deviation is a bug").

NO --deploy is ever invoked by the harness that runs this (the --deploy CODE PATH is implemented per
the brief but must not be executed).

Run from the repo root:  py studies/overworld-topography/dunes_patch_mint.py [--deploy]
Artifacts -> out/dunes_patch_mint.json, out/dunes_patch_mint_*.png
"""
from __future__ import annotations

import copy
import dataclasses
import json
import math
import random
import subprocess
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                          # noqa: E402
from ff9mapkit.world import discmirror as DM                  # noqa: E402
from ff9mapkit.world import extract as X                      # noqa: E402
from ff9mapkit.world import grassland as G                    # noqa: E402
from ff9mapkit.world import island as I                       # noqa: E402
from ff9mapkit.world import mesh as M                          # noqa: E402
from ff9mapkit.world import placement as P                    # noqa: E402

DEPLOY = "--deploy" in sys.argv
if DEPLOY:
    sys.exit("this harness run refuses --deploy per the lane's HARD RULES -- the code path exists "
             "(see deploy_patch() below) but must be invoked by a human, out of band")

HERE = Path(__file__).parent
OUTD = HERE / "out"
OUTD.mkdir(exist_ok=True)

MOD = "FF9CustomMap-world"
CENTER = (672.0, -1248.0)                                      # PRIMARY design site (v1/v2's own pick)
RADIUS = 26.0
SEED = 2.0
GROUND = "desert"
TEMPLATE_NAME = "lobe_of_comp_0_cut_at_saddle"                 # from out/dunes_blob_templates.json
MAINS_SEED = 0xF91                                             # build_landmass's own default mains_seed
MINT_SEED = 0                                                  # the row emitter's seed (recorded)
BLOCK = 64.0
CELL_U = 4.0
NEI4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
EPS = 0.006
TOL_V = 0.008
ROW_PITCH = 0.03125
# comp20 massif carry (6-7,18-19) + the scrub recreate islet (8,19) + (9,19) explicitly reserved
# untouched by the lane's CONTEXT -- a fallback tier must never land on any of these.
EXCLUDED_BLOCKS = {(6, 18), (6, 19), (7, 18), (7, 19), (8, 19), (9, 19)}

GATES: list = []                                               # (name, ok, detail)


def gate(name: str, ok: bool, detail: str = ""):
    GATES.append((name, bool(ok), detail))
    print(f"GATE [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    return ok


# ============================================================================================
# THE FROZEN ROW-EMITTER CONSTANTS (dunes_strip_emitter.py round 3, re-derived this session --
# see _live_reverify() below, which re-runs the SAME script's Step 1+2 via the exec-and-cut
# technique already used by dunes_mint_design.md's own reproduction log, and asserts these
# literals still match it byte-for-byte. DELTA_P also matches out/dunes_strip_emitter.json's
# "delta_p" key exactly; TARGET_PMF is NOT persisted in that JSON (the emitter script only dumps
# it to stdout), so it is verified against the live re-derivation only.)
# ============================================================================================
FROZEN_TARGET_PMF = {
    "A-only": {0: 0.5303030303030303, 1: 0.25757575757575757, 2: 0.015151515151515152, 3: 0.19696969696969696},
    "both": {0: 0.17045454545454544, 1: 0.2916666666666667, 2: 0.23863636363636365, 3: 0.29924242424242425},
    "B-only": {0: 0.05172413793103448, 1: 0.29310344827586204, 2: 0.5689655172413793, 3: 0.08620689655172414},
    "neither": {0: 0.5, 1: 0.2777777777777778, 2: 0.16666666666666666, 3: 0.05555555555555555},
}
FROZEN_DELTA_P = {0: 0.09774436090225563, 1: 0.5263157894736842, 2: 0.2932330827067669, 3: 0.08270676691729323}


def emit_strip_rows_v1_unconstrained(cells, touch_of_local, target_pmf, delta_p, seed=0):
    """VERBATIM copy of dunes_strip_emitter.py's emitter (round 3) -- pure deterministic code, not
    a measured number, so it is reused as code (not re-derived); its INPUT DATA (target_pmf/
    delta_p) is what gets frozen+reverified above. Kept unmodified (not called by apply_retile
    any more) as the regression reference emit_strip_rows() is measured against -- LAW 5."""
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


def emit_strip_rows(cells, touch_of_local, target_pmf, delta_p, seed=0, shell_of=None):
    """v2 -- emit_strip_rows_v1_unconstrained() PLUS a hard cross-BOUNDARY constraint (v2's fix,
    cause 2/DENSITY CLIFFS): on every RING adjacency where the two cells sit on DIFFERENT sides of
    the footprint boundary (``shell_of[a] != shell_of[b]`` -- inner|outer touching, generalized in
    v3 from "concentric shell" to "inside vs outside the stamped footprint's own boundary" -- this
    BFS machinery never cared which SHAPE it was walking, only the cellset + adjacency, so the v2
    generalization needed zero code changes here), the candidate row for the later-assigned cell is
    restricted to rows that are (a) within 1 of the already-assigned neighbour's row (|dr|<=1,
    closing the |drow|=2 density cliffs a calibrated eye caught) and (b) still rising toward dunes
    (inner's row >= outer's row on that pair, consistent with the measured family-relative direction
    law, Sec.2). LATERAL adjacencies (same side touching same side) are left exactly as v1's own
    delta_p-weighted transition -- that is the measured, real, in-band dither. If ``shell_of`` is
    None this degenerates to the v1 behaviour exactly (used nowhere in this script, kept for API
    symmetry/testability).

    Conflict fallback (should not occur for one ring cell wide on each side, and did not occur this
    run -- printed if it ever does): if every row is hard-vetoed by two already-assigned cross-
    boundary neighbours pulling in opposite directions, relax to the row minimising total violation
    (ties broken by target_pmf weight) rather than crash or silently violate the gate."""
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

    n_conflict_fallbacks = 0
    assigned = {}
    for c in order:
        cat = touch_of_local.get(c, "neither")
        pmf = target_pmf[cat]
        lateral_rows, cross_rows = [], []
        for n in adj[c]:
            if n not in assigned:
                continue
            same_shell = shell_of is None or shell_of.get(n) == shell_of.get(c)
            (lateral_rows if same_shell else cross_rows).append(assigned[n])

        def veto(r):
            for nr in cross_rows:
                if abs(r - nr) > 1:
                    return True
                if shell_of.get(c) == "inner" and r < nr:
                    return True
                if shell_of.get(c) == "outer" and r > nr:
                    return True
            return False

        weights = []
        for r in range(4):
            if cross_rows and veto(r):
                weights.append(0.0)
                continue
            w_target = pmf[r]
            if lateral_rows:
                w_trans = 1.0
                for nr in lateral_rows:
                    w_trans *= max(delta_p.get(abs(r - nr), 1e-6), 1e-6)
                w_trans **= (1.0 / len(lateral_rows))
            else:
                w_trans = 1.0
            weights.append(w_target * w_trans)
        tot = sum(weights)
        if tot <= 0.0:                                          # hard-veto conflict -- min-violation fallback
            n_conflict_fallbacks += 1

            def violation(r):
                v = 0
                for nr in cross_rows:
                    v += max(0, abs(r - nr) - 1)
                    if shell_of.get(c) == "inner" and r < nr:
                        v += 2
                    if shell_of.get(c) == "outer" and r > nr:
                        v += 2
                return v
            best_v = min(violation(r) for r in range(4))
            fallback_rows = [r for r in range(4) if violation(r) == best_v]
            fweights = [pmf[r] for r in fallback_rows]
            ftot = sum(fweights) or 1.0
            assigned[c] = rng.choices(fallback_rows, weights=[w / ftot for w in fweights], k=1)[0]
            print(f"  [emit_strip_rows conflict fallback] cell {c}: no row satisfies all cross-boundary "
                  f"constraints from {cross_rows} -- chose row {assigned[c]} (min violation {best_v})")
            continue
        probs = [w / tot for w in weights]
        assigned[c] = rng.choices(range(4), weights=probs, k=1)[0]
    if n_conflict_fallbacks:
        print(f"  emit_strip_rows: {n_conflict_fallbacks} conflict fallback(s) hit (see above)")
    return assigned


def _live_reverify():
    """Re-run dunes_strip_emitter.py's Step 1 (map-wide census) + Step 2 (emitter def) via the
    exec-and-cut technique the design doc's own reproduction log already used, and assert the
    FROZEN constants above still match byte-for-byte. Returns the live namespace (also reused
    below for the offline-eye's stock calibration windows -- no second 480-block scan)."""
    src_path = HERE / "dunes_strip_emitter.py"
    src = src_path.read_text(encoding="utf-8")
    marker = "# ============================================================================================\n# STEP 3"
    idx = src.index(marker)
    truncated = src[:idx]
    ns = {"__name__": "_dunes_strip_emitter_trunc_S1S2", "__file__": str(src_path)}
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(truncated, "dunes_strip_emitter.py(trunc@STEP3)", "exec"), ns)
    live_target = {cat: {int(k): float(v) for k, v in d.items()} for cat, d in ns["TARGET_PMF"].items()}
    live_delta = {int(k): float(v) for k, v in ns["DELTA_P"].items()}
    tp_ok = live_target == FROZEN_TARGET_PMF
    dp_ok = live_delta == FROZEN_DELTA_P
    max_tp_diff = max((abs(live_target[c][r] - FROZEN_TARGET_PMF[c][r]) for c in FROZEN_TARGET_PMF for r in range(4)), default=0.0)
    max_dp_diff = max((abs(live_delta[r] - FROZEN_DELTA_P[r]) for r in range(4)), default=0.0)
    gate("frozen TARGET_PMF matches live re-derivation (dunes_strip_emitter.py Step1+2, exec-and-cut)",
         tp_ok, f"max|diff|={max_tp_diff:.2e}")
    gate("frozen DELTA_P matches live re-derivation", dp_ok, f"max|diff|={max_dp_diff:.2e}")
    json_path = OUTD / "dunes_strip_emitter.json"
    if json_path.is_file():
        rec = json.loads(json_path.read_text(encoding="utf-8"))
        json_delta = {int(k): float(v) for k, v in rec["delta_p"].items()}
        gate("frozen DELTA_P matches out/dunes_strip_emitter.json byte-for-byte",
             json_delta == FROZEN_DELTA_P, f"json={json_delta}")
    else:
        gate("out/dunes_strip_emitter.json present for cross-check", False, "missing -- run dunes_strip_emitter.py first")
    return ns


def _live_reverify_template():
    """v3 NEW: re-run dunes_blob_shapes.py IN FULL (its own map-wide 480-block census is ~4-5s, not
    the 1-2min UnityPy-cold-start figure -- timed this session) via the same exec-and-cut technique,
    and assert the chosen template's cell-set matches out/dunes_blob_templates.json's committed copy
    byte-for-byte (LAW 5: this script's own template choice is independently reproducible, not just
    trusted from a stale file). Returns (the live template dict, the full live namespace -- reused
    by _template_provenance() below for the source-component/block breakdown without a second scan)."""
    src_path = HERE / "dunes_blob_shapes.py"
    src = src_path.read_text(encoding="utf-8")
    ns = {"__name__": "_dunes_blob_shapes_trunc", "__file__": str(src_path)}
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(src, "dunes_blob_shapes.py(full)", "exec"), ns)
    live_templates = {t["name"]: t for t in ns["templates"]}
    disk_path = OUTD / "dunes_blob_templates.json"
    if not disk_path.is_file():
        gate("out/dunes_blob_templates.json present for cross-check", False, "missing -- run dunes_blob_shapes.py first")
        return live_templates[TEMPLATE_NAME], ns
    disk = json.loads(disk_path.read_text(encoding="utf-8"))
    disk_templates = {t["name"]: t for t in disk["templates"]}
    live_t = live_templates.get(TEMPLATE_NAME)
    disk_t = disk_templates.get(TEMPLATE_NAME)
    # round-trip the live dict through JSON (tuples -> lists, matching the on-disk shape) before
    # comparing -- dunes_blob_shapes.py's in-memory templates carry (i,j) TUPLES (from its own
    # normalize()/sorted() calls), json.loads() always yields lists; without this the equality
    # check would report a false mismatch on every run despite identical content.
    live_t_json = json.loads(json.dumps(live_t, default=str)) if live_t is not None else None
    match = live_t_json == disk_t
    gate(f"chosen template '{TEMPLATE_NAME}' matches a live full re-derivation of dunes_blob_shapes.py "
         "(map-wide 480-block census, LAW 5)", match,
         f"live size={len(live_t.get('cell_offsets', [])) if live_t else None} "
         f"disk size={len(disk_t.get('cell_offsets', [])) if disk_t else None}")
    return (live_t if live_t is not None else disk_t), ns


def _template_provenance(ns):
    """Which real stock dunes component this round's template was cut from, and which real blocks
    it spans -- read off the live namespace _live_reverify_template() already produced (zero extra
    scan)."""
    lobe_report = ns["lobe_report"]
    src_idx = lobe_report["source_comp"]
    comp = next(c for c in ns["comp_info"] if c["idx"] == src_idx)
    blocks = sorted({ns["to_block"](c) for c in comp["cells"]})
    n_cut = len(lobe_report["cut_cells_in_chosen_lobe"])
    print(f"TEMPLATE PROVENANCE: '{TEMPLATE_NAME}' = one lobe (size {lobe_report['chosen_lobe_size']}) of "
          f"real stock dunes component[{src_idx}] (whole-component size {comp['size']}, bbox "
          f"{comp['bbox']}, {lobe_report['n_lobes']} lobes total, sizes {lobe_report['lobe_sizes']}) "
          f"spanning real blocks {blocks}. {n_cut} of the lobe's 19 boundary cells sit on the "
          f"erosion-Voronoi SYNTHETIC cut (the saddle line between this lobe and its 6 sibling lobes "
          f"of the same real component); the remaining {19 - n_cut} boundary cells are verbatim-real "
          f"stock component edge.")
    return dict(source_component_idx=src_idx, source_component_size=comp["size"],
                source_component_bbox=list(comp["bbox"]), source_component_blocks=[list(b) for b in blocks],
                n_lobes=lobe_report["n_lobes"], lobe_sizes=lobe_report["lobe_sizes"],
                n_cut_boundary_cells=n_cut, n_real_boundary_cells=19 - n_cut)


# ============================================================================================
# strip_uv() -- design doc Sec.2, authored to mirror mains_uv() exactly (ori fixed at 0, the
# conservative/measured-safe choice -- round 2/3 never varied tile rotation within a strip cell)
# ============================================================================================

def strip_uv(x: float, z: float, cell, row: int, ori: int = 0, *, pair=("desert", "dunes")):
    (i, j) = cell
    fx, fz = (x - CELL_U * i) / CELL_U, (z - CELL_U * j) / CELL_U
    a, b = G.rot_ab(fx, fz, ori)
    a, b = max(0.0, min(1.0, a)), max(0.0, min(1.0, b))
    S = G.STRIPS[pair]
    u0, u1 = G.STRIP_U
    v0, v1 = G.STRIPS_V[row]
    return [u0 + a * (u1 - u0) + S["du"], v0 + b * (v1 - v0) + S["dv"]]


PAIR = ("desert", "dunes")

# ---- the zero-residual classification oracle (reimplemented, not imported -- LAW 5) --------------

STRIP_U0, STRIP_U1 = G.STRIP_U
ROW0_V0 = G.STRIPS_V[0][0]
_S = G.STRIPS[PAIR]
_DU, _DV = _S["du"], _S["dv"]
TOPO_FAM = {17: "desert", 41: "dunes", 58: "rock"}


def _mains_rect(fam):
    m = G.FAM_REGION["main"]
    g = G.GROUNDS[fam]
    return (m[0] + g["mains_du"], m[1] + g["mains_dv"], m[2] + g["mains_du"], m[3] + g["mains_dv"])


RECTS = {"desert": _mains_rect("desert"), "dunes": _mains_rect("dunes")}


def _rect_contains(rect, uv3, eps=EPS):
    return all(rect[0] - eps <= u <= rect[2] + eps and rect[1] - eps <= v <= rect[3] + eps for (u, v) in uv3)


def classify_strip(uv3):
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


def classify_tri(topo, uv3):
    fam = TOPO_FAM.get(topo)
    if fam in PAIR:
        k = classify_strip(uv3)
        if k is not None:
            return ("strip", k)
    rect = RECTS.get(fam)
    if rect and _rect_contains(rect, uv3):
        return ("mains", fam)
    if fam == "rock":
        lo_u, lo_v = I.ROCK_U[0] + G.GROUNDS["desert"]["wall_du"], min(I.ROCK_V) + G.GROUNDS["desert"]["wall_dv"]
        hi_u, hi_v = I.ROCK_U[1] + G.GROUNDS["desert"]["wall_du"], max(I.ROCK_V) + G.GROUNDS["desert"]["wall_dv"]
        if _rect_contains((lo_u, lo_v, hi_u, hi_v), uv3, eps=1e-3):
            return ("rock",)
    return ("other",)


# ============================================================================================
# DIHEDRAL TRANSFORMS -- v3 NEW: 4 rotations x optional mirror, applied to a normalized cell-
# offset set (re-normalized to its own bbox-min-corner origin after transform, matching
# dunes_blob_shapes.py's normalize() convention -- LAW 5, reimplemented not imported)
# ============================================================================================

def dihedral_point(i: int, j: int, k: int):
    """k in 0..7: k>=4 mirrors the i axis first, then rotates (k%4)*90deg CCW about the origin."""
    if k >= 4:
        i = -i
    r = k % 4
    if r == 0:
        return (i, j)
    if r == 1:
        return (-j, i)
    if r == 2:
        return (-i, -j)
    return (j, -i)


def dihedral_cellset(cells, k):
    """Transform + renormalize an (i,j) offset iterable under dihedral element k. Returns
    (normalized_set, (ti0, tj0)) -- the origin subtracted, so a caller can push a SIBLING subset
    (e.g. the template's own boundary cells) through dihedral_point() + the SAME (ti0, tj0) for an
    identical transform."""
    pts = [dihedral_point(i, j, k) for (i, j) in cells]
    ti0 = min(p[0] for p in pts)
    tj0 = min(p[1] for p in pts)
    return {(p[0] - ti0, p[1] - tj0) for p in pts}, (ti0, tj0)


def apply_placement(cells, placement):
    """Push an arbitrary auxiliary cell subset (e.g. the template's cut-boundary cells, kept only
    for provenance printing) through the SAME dihedral+translation a winning placement used."""
    k = placement["k"]
    ti0, tj0 = placement["dihedral_origin"]
    oi, oj = placement["oi"], placement["oj"]
    out = set()
    for (i, j) in cells:
        pi, pj = dihedral_point(i, j, k)
        out.add((pi - ti0 + oi, pj - tj0 + oj))
    return out


# ============================================================================================
# once_edges / weld / frame / census gates (reused technique, dunes_patch_carry.py) -- moved up
# here since dilate()/_cell_is_regular() below are shared by the geometry + placement passes
# ============================================================================================

def to_world(bm, cell):
    bx, by = cell
    return [(v[0] + BLOCK * bx, v[1], v[2] - BLOCK * by) for v in bm.verts]


def dilate(seed_cells, exclude):
    nxt = set()
    for c in seed_cells:
        for (di, dj) in NEI4:
            n = (c[0] + di, c[1] + dj)
            if n not in exclude:
                nxt.add(n)
    return nxt


def _cell_is_regular(cell, tri_list, tris_idx, world_pos, *, tol=0.02):
    """A cell is a clean axis-aligned 4u-square (2 tris, every corner exactly on the cell's own
    4 corners) iff every vertex's cell-local (fx, fz) snaps to {0, 1} within ``tol``. The rim
    curve blends into the interior grid via irregular (non-grid) Delaunay triangles at the
    OUTERMOST 1-2 cells of the mains footprint (verts straddling into a neighbour cell, fz
    outside [0,1]) -- those triangles' UV do not fit the discrete-row classifier (built for
    stock geometry) and must not be forced into the strip vocabulary; the retile simply leaves
    them untouched plain desert."""
    (ci, cj) = cell
    for ti in tri_list:
        for j in tris_idx[ti]:
            fx = (world_pos[j][0] - CELL_U * ci) / CELL_U
            fz = (world_pos[j][2] - CELL_U * cj) / CELL_U
            if min(abs(fx - 0.0), abs(fx - 1.0)) > tol or min(abs(fz - 0.0), abs(fz - 1.0)) > tol:
                return False
    return True


def once_edges_from_bm(bm, cell):
    world_pos = to_world(bm, cell)
    tris_idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
    c = Counter()
    for tri in tris_idx:
        ks = [tuple(round(v, 3) for v in world_pos[j]) for j in tri]
        for i in range(3):
            e = frozenset((ks[i], ks[(i + 1) % 3]))
            if len(e) == 2:
                c[e] += 1
    return {e for e, n in c.items() if n == 1}


# ============================================================================================
# STEP A -- the plain desert host build (site-parametrized -- the fallback ladder tries several)
# ============================================================================================

def probe_site(center, radius, seed, label):
    """Cheap-first probe: build the landmass, reject on single-block/excluded-block/open-ocean
    grounds WITHOUT running the (more expensive) verify_landmass engine census -- that only runs
    once, on the tier that actually wins (finalize_site_gates(), below). No gate() calls here:
    a rejected candidate is not a defect, it's the ladder working as designed."""
    try:
        built = I.build_landmass(center=center, base_radius=radius, seed=seed, ground=GROUND,
                                 stamps=None, disc=1)
    except Exception as e:                                     # noqa: BLE001
        print(f"  [{label}] build_landmass raised: {e}")
        return None
    cells = sorted(built["blocks"])
    if len(cells) != 1:
        print(f"  [{label}] rejected: not single-block ({cells})")
        return None
    CELL = cells[0]
    if CELL in EXCLUDED_BLOCKS:
        print(f"  [{label}] rejected: touches an excluded block {CELL}")
        return None
    occupied = {blk: occ for blk in cells if (occ := I._real_block_parts(blk, disc=1, game=None))}
    if occupied:
        print(f"  [{label}] rejected: not open ocean {occupied}")
        return None
    return dict(built=built, cell=CELL, center=center, radius=radius, seed=seed, label=label)


def compute_mains_geometry(bm, cell):
    world_pos = to_world(bm, cell)
    tris_idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
    mains_cells = defaultdict(list)
    for ti, tri in enumerate(tris_idx):
        topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
        if topo != 17:
            continue
        cx = sum(world_pos[j][0] for j in tri) / 3.0
        cz = sum(world_pos[j][2] for j in tri) / 3.0
        mains_cells[(math.floor(cx / CELL_U), math.floor(cz / CELL_U))].append(ti)
    regular_cells = {c for c, tl in mains_cells.items() if _cell_is_regular(c, tl, tris_idx, world_pos)}
    return dict(world_pos=world_pos, tris_idx=tris_idx, mains_cells=mains_cells, regular_cells=regular_cells)


# ============================================================================================
# STEP B -- template placement search (v3 NEW): 8 dihedral transforms x every translation over
# the host's regular-cell region; a candidate must land the footprint AND its 1-cell outward
# ring entirely on regular cells.
# ============================================================================================

def search_placement(regular_cells, template_cells, template_boundary, host_center, *, label=""):
    if not regular_cells:
        print(f"  [{label}] no placement found (host has zero regular cells)")
        return None
    xs = sorted({c[0] for c in regular_cells})
    zs = sorted({c[1] for c in regular_cells})
    candidates = []
    for k in range(8):
        footprint_norm, origin = dihedral_cellset(template_cells, k)
        ti0, tj0 = origin
        boundary_norm = {(dihedral_point(i, j, k)[0] - ti0, dihedral_point(i, j, k)[1] - tj0)
                          for (i, j) in template_boundary}
        w = max(p[0] for p in footprint_norm) + 1
        h = max(p[1] for p in footprint_norm) + 1
        for oi in range(xs[0] - 1, xs[-1] - w + 2):
            for oj in range(zs[0] - 1, zs[-1] - h + 2):
                footprint = {(oi + a, oj + b) for (a, b) in footprint_norm}
                if not footprint <= regular_cells:
                    continue
                ring = dilate(footprint, footprint)
                if not ring <= regular_cells:
                    continue
                boundary_placed = {(oi + a, oj + b) for (a, b) in boundary_norm}
                wx = CELL_U * (oi + w / 2.0)
                wz = CELL_U * (oj + h / 2.0)
                d = math.hypot(wx - host_center[0], wz - host_center[1])
                candidates.append((d, k, oi, oj, footprint, boundary_placed, ring, (ti0, tj0)))
    if not candidates:
        print(f"  [{label}] no placement found ({len(regular_cells)} regular cells in this host, "
              f"8 dihedral orientations scanned)")
        return None
    candidates.sort(key=lambda c: (round(c[0], 6), c[1], c[2], c[3]))
    d, k, oi, oj, footprint, boundary_placed, ring, dihedral_origin = candidates[0]
    print(f"  [{label}] placement FOUND: {len(candidates)} candidate(s) over 8 dihedral orientations, "
          f"winner dihedral={k} origin=({oi},{oj}) distance={d:.2f}u from host centre")
    return dict(k=k, oi=oi, oj=oj, footprint=footprint, boundary=boundary_placed, ring=ring,
                dihedral_origin=dihedral_origin, n_candidates=len(candidates), distance=d)


def resolve_site_and_placement(template_cells, template_boundary):
    """The fallback ladder (brief requirement 1, in order): primary design site -> seed-scan
    1-39 -> radius-scan 27-30 -> fallback block (11,19). Stops at the first site+placement that
    both build cleanly (single block, not excluded, open ocean) AND admit a valid template
    placement. Returns (site, geom, placement, tier_info)."""
    tiers = [("primary design site (seed=2.0, radius=26.0)", CENTER, RADIUS, SEED)]
    for s in range(1, 40):
        if s == int(SEED):
            continue
        tiers.append((f"seed-scan seed={s} (radius=26.0, same centre)", CENTER, RADIUS, float(s)))
    for r in range(27, 31):
        tiers.append((f"radius-scan radius={r} (seed=2.0, same centre)", CENTER, float(r), SEED))
    fb_center = (BLOCK * 11 + BLOCK / 2.0, -(BLOCK * 19 + BLOCK / 2.0))
    tiers.append((f"fallback block (11,19) centre={fb_center}", fb_center, RADIUS, SEED))

    print(f"placement search: {len(tiers)} tiers queued (1 primary + 38 seed-scan + 4 radius-scan + "
          f"1 block-fallback; stops at first success) -----------------------------------------")
    for label, center, radius, seed in tiers:
        site = probe_site(center, radius, seed, label)
        if site is None:
            continue
        geom = compute_mains_geometry(site["built"]["blocks"][site["cell"]], site["cell"])
        print(f"  [{label}] host accepted: block {site['cell']}, {len(geom['mains_cells'])} mains "
              f"cells ({len(geom['regular_cells'])} regular)")
        placement = search_placement(geom["regular_cells"], template_cells, template_boundary,
                                      center, label=label)
        if placement is not None:
            print(f"\n=== WINNER: {label} -- centre={center} radius={radius} seed={seed} "
                  f"block={site['cell']} ===\n")
            return site, geom, placement, dict(label=label, center=list(center), radius=radius,
                                               seed=seed, block=list(site["cell"]))
    raise SystemExit("no placement found across every fallback tier (primary + seed 1-39 + radius "
                      "27-30 + block (11,19)) -- would need a larger host radius or a smaller "
                      "template; neither implemented since not needed this run")


def finalize_site_gates(site, tier_info):
    """The official named gates for the WINNING site only (rejected tiers are not defects, so they
    get plain prints in probe_site()/search_placement(), not gate() calls)."""
    built = site["built"]
    CELL = site["cell"]
    cells = sorted(built["blocks"])
    gate(f"host is a single block ({tier_info['label']})", cells == [CELL], f"blocks={cells}")
    gate("chosen block is not excluded (comp20 (6-7,18-19) / the scrub islet (8,19) / (9,19) "
         "explicitly reserved-untouched)", CELL not in EXCLUDED_BLOCKS,
         f"block={CELL} excluded={sorted(EXCLUDED_BLOCKS)}")
    occupied = {blk: occ for blk in cells if (occ := I._real_block_parts(blk, disc=1, game=None))}
    gate("OPEN-OCEAN TARGET (every touched block is true open ocean)", not occupied, f"occupied={occupied}")
    gate("THE WALL-CONTEXT LAW (ground=desert -> wall_coastal=True)", G.GROUNDS[GROUND]["wall_coastal"] is True,
         "enforced by build_landmass at call time; would have raised otherwise")
    plane = I._sea_plane(disc=1, game=None)
    report = I.verify_landmass(built, sea_plane=plane, land_height=3.2)
    gate("mint acceptance -- verify_landmass on the plain host (baseline, pre-retile)", report["clean"],
         f"{ {k: v for k, v in report.items() if k not in ('placement', 'shape')} }")
    n_tris = len(built["blocks"][CELL].tris)
    print(f"host: block {CELL}, {n_tris} tris, seed {tier_info['seed']}, centre {tier_info['center']}, "
          f"radius {tier_info['radius']}, tier '{tier_info['label']}'")
    return plane, report


# ============================================================================================
# SHAPE-FIDELITY oracle -- v3 NEW: a slimmed, independent re-derivation (LAW 5) of
# dunes_blob_shapes.py's boundary_trace()/loop_area()/run_lengths_and_corners(), used to assert
# the PLACED footprint's straight-run histogram + corner count are IDENTICAL to the template's
# own (a rigid dihedral transform + translation preserves both exactly -- any diff means a cell
# was dropped/added during placement, i.e. a real bug, not measurement noise).
# ============================================================================================

def _boundary_trace(cellset):
    directed = {}
    for (i, j) in cellset:
        bl, br, tr, tl = (i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)
        sides = [(bl, br, (i, j - 1)), (br, tr, (i + 1, j)),
                 (tr, tl, (i, j + 1)), (tl, bl, (i - 1, j))]
        for (a, b, nb) in sides:
            if nb in cellset:
                continue
            directed[(a, b)] = (i, j)
    out_from = defaultdict(list)
    for (a, b), cell in directed.items():
        out_from[a].append((b, cell))

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
        cell0 = remaining.pop((a0, b0))
        loop.append((a, b, cell0))
        cur = b
        prev_dir = (b[0] - a[0], b[1] - a[1])
        guard = 0
        while cur != a0 and guard < 100000:
            guard += 1
            cands = [(end, cell) for (end, cell) in out_from[cur] if (cur, end) in remaining]
            if not cands:
                break
            if len(cands) == 1:
                end, cell = cands[0]
            else:
                end, cell = min(cands, key=lambda ec: turn_priority(prev_dir, (ec[0][0] - cur[0], ec[0][1] - cur[1])))
            remaining.pop((cur, end))
            loop.append((cur, end, cell))
            prev_dir = (end[0] - cur[0], end[1] - cur[1])
            cur = end
        loops.append(loop)
    return loops


def _loop_area(loop):
    a = 0.0
    for (p, q, _c) in loop:
        a += p[0] * q[1] - q[0] * p[1]
    return a / 2.0


def _run_lengths_and_corners(loop):
    dirs = [(q[0] - p[0], q[1] - p[1]) for (p, q, _c) in loop]
    if not dirs:
        return [], 0
    runs = []
    cur_dir = dirs[0]
    run_len = 1
    for d in dirs[1:]:
        if d == cur_dir:
            run_len += 1
        else:
            runs.append(run_len)
            cur_dir = d
            run_len = 1
    runs.append(run_len)
    if len(runs) > 1 and dirs[-1] == dirs[0]:
        runs[0] += runs[-1]
        runs.pop()
    return runs, len(runs)


def analyze_shape_local(cellset):
    loops = _boundary_trace(cellset)
    outer_loops = [lp for lp in loops if _loop_area(lp) > 0]
    outer = max(outer_loops, key=lambda lp: abs(_loop_area(lp))) if outer_loops else (max(loops, key=len) if loops else [])
    runs, n_corners = _run_lengths_and_corners(outer)
    return dict(run_hist=dict(sorted(Counter(runs).items())), max_run=(max(runs) if runs else 0),
                n_corners=n_corners, n_loops=len(loops))


# ============================================================================================
# STEP C -- the retile plan (CORE/INNER/OUTER generalized from v1/v2's concentric squares to an
# arbitrary stamped footprint's own interior/boundary/outward-ring split)
# ============================================================================================

def plan_cells(geom, placement, template_cells_original, template_boundary_original):
    mains_cells, regular_cells = geom["mains_cells"], geom["regular_cells"]
    footprint, boundary_placed, ring = placement["footprint"], placement["boundary"], placement["ring"]

    gate("dunes footprint is fully within the built island's desert-mains footprint",
         footprint <= set(mains_cells), f"missing={sorted(footprint - set(mains_cells))}")
    gate("dunes footprint cells (footprint + 1-cell ring) are all geometrically regular (clean 4u "
         "grid squares)", (footprint | ring) <= regular_cells,
         f"irregular cells={sorted((footprint | ring) - regular_cells)}")

    CORE = footprint - boundary_placed                          # interior -- pure mains dunes, no strip
    INNER = boundary_placed                                     # the footprint's own boundary -- strip, dunes-side
    OUTER = ring                                                 # 1-cell outward dilation -- strip, desert-side

    gate("RING COMPLETENESS -- footprint-boundary (inner strip) shell has zero dropped cells "
         "(== the template's own boundary cell count, transform-invariant)",
         len(INNER) == len(template_boundary_original),
         f"inner={len(INNER)} template_boundary={len(template_boundary_original)}")
    outer_theory = dilate(footprint, footprint)
    gate("RING COMPLETENESS -- outer shell (1-cell dilation beyond the whole footprint) has zero "
         "dropped cells (== theoretical dilation size)", OUTER == outer_theory,
         f"outer={len(OUTER)} theory={len(outer_theory)} dropped={sorted(outer_theory - OUTER)}")

    remaining_mains = set(mains_cells) - footprint - OUTER
    touch_of = {}
    for c in INNER:
        touch_of[c] = "B-only"
    for c in OUTER:
        touches_desert = any((c[0] + di, c[1] + dj) in remaining_mains for (di, dj) in NEI4)
        touch_of[c] = "A-only" if touches_desert else "neither"
    tally = Counter(touch_of.values())
    print(f"cells: footprint={len(footprint)} (core={len(CORE)} inner={len(INNER)}) outer={len(OUTER)} "
          f"template size={len(template_cells_original)}; touch tally {dict(tally)}")

    # -- SHAPE-FIDELITY gate (v3 NEW): the placed footprint's straight-run histogram + corner
    # count must be IDENTICAL to the template's own (rotation/mirror/translation-invariant) --------
    tmpl_shape = analyze_shape_local(set(template_cells_original))
    placed_shape = analyze_shape_local(footprint)
    shape_ok = (tmpl_shape["run_hist"] == placed_shape["run_hist"]
                and tmpl_shape["max_run"] == placed_shape["max_run"]
                and tmpl_shape["n_corners"] == placed_shape["n_corners"])
    gate("SHAPE-FIDELITY -- the stamped footprint's straight-run distribution + corner count are "
         "IDENTICAL to the template's own (a rigid dihedral transform + translation cannot change "
         "either metric; any deviation means a cell was silently dropped/added -- it is a stamp, "
         "any deviation is a bug)", shape_ok,
         f"template run_hist={tmpl_shape['run_hist']} max_run={tmpl_shape['max_run']} "
         f"corners={tmpl_shape['n_corners']} | placed run_hist={placed_shape['run_hist']} "
         f"max_run={placed_shape['max_run']} corners={placed_shape['n_corners']}")

    fx0, fx1 = min(c[0] for c in footprint), max(c[0] for c in footprint)
    fz0, fz1 = min(c[1] for c in footprint), max(c[1] for c in footprint)
    footprint_center_world = (CELL_U * (fx0 + fx1 + 1) / 2.0, CELL_U * (fz0 + fz1 + 1) / 2.0)

    return dict(CORE=CORE, INNER=INNER, OUTER=OUTER, touch_of=touch_of, footprint=footprint,
                footprint_center_world=footprint_center_world, dihedral=placement["k"],
                origin=(placement["oi"], placement["oj"]), n_candidates=placement["n_candidates"],
                template_shape=tmpl_shape, placed_shape=placed_shape,
                world_pos=geom["world_pos"], tris_idx=geom["tris_idx"], mains_cells=mains_cells)


def cross_shell_pairs(INNER, OUTER):
    """Every RING adjacency where the two cells sit on different sides of the footprint boundary
    (inner touching outer)."""
    pairs = []
    for c in INNER:
        for (di, dj) in NEI4:
            n = (c[0] + di, c[1] + dj)
            if n in OUTER:
                pairs.append((c, n))
    return pairs


def apply_retile(bm, plan):
    world_pos, tris_idx, mains_cells = plan["world_pos"], plan["tris_idx"], plan["mains_cells"]
    CORE, INNER, OUTER, touch_of = plan["CORE"], plan["INNER"], plan["OUTER"], plan["touch_of"]
    RING = INNER | OUTER
    shell_of = {c: "inner" for c in INNER}
    shell_of.update({c: "outer" for c in OUTER})
    rows = emit_strip_rows(sorted(RING), touch_of, FROZEN_TARGET_PMF, FROZEN_DELTA_P, seed=MINT_SEED,
                            shell_of=shell_of)

    # -- CROSS-BOUNDARY SMOOTHNESS gate (v2's cause 2/DENSITY CLIFFS fix, generalized) ------------
    xpairs = cross_shell_pairs(INNER, OUTER)
    offenders = []
    for (inr, outr) in xpairs:
        dr = rows[inr] - rows[outr]
        if abs(dr) > 1 or dr < 0:                                  # |drow|<=1 AND inner>=outer (rising to dunes)
            offenders.append((inr, outr, rows[inr], rows[outr], dr))
    max_abs_dr = max((abs(rows[i] - rows[o]) for i, o in xpairs), default=0)
    gate("CROSS-BOUNDARY SMOOTHNESS -- every inner|outer-adjacent pair (footprint boundary vs the "
         "1-cell ring outside it) has |drow|<=1 and inner>=outer (dunes-ward rise, zero density "
         "cliffs)", not offenders,
         f"max|drow|={max_abs_dr} n_pairs={len(xpairs)} offenders={offenders}" if offenders else
         f"max|drow|={max_abs_dr} n_pairs={len(xpairs)}")

    core_quad, core_ori = G.assign_mains(CORE, seed=MAINS_SEED)
    idall_dunes = float(X.encode_id(topograph=41))
    idall_desert = float(X.encode_id(topograph=17))
    n_core = n_inner = n_outer = 0
    for cell, tri_list in mains_cells.items():
        if cell in CORE:
            quad, ori = core_quad[cell], core_ori[cell]
            for ti in tri_list:
                for j in tris_idx[ti]:
                    wx, wz = world_pos[j][0], world_pos[j][2]
                    u, v = G.ground_uv(wx, wz, cell, quad, ori, "dunes")
                    bm.uvs[j][0], bm.uvs[j][1] = u, v
                    bm.tangents[j][0] = idall_dunes
                n_core += 1
        elif cell in INNER:
            row = rows[cell]
            for ti in tri_list:
                for j in tris_idx[ti]:
                    wx, wz = world_pos[j][0], world_pos[j][2]
                    u, v = strip_uv(wx, wz, cell, row)
                    bm.uvs[j][0], bm.uvs[j][1] = u, v
                    bm.tangents[j][0] = idall_dunes
                n_inner += 1
        elif cell in OUTER:
            row = rows[cell]
            for ti in tri_list:
                for j in tris_idx[ti]:
                    wx, wz = world_pos[j][0], world_pos[j][2]
                    u, v = strip_uv(wx, wz, cell, row)
                    bm.uvs[j][0], bm.uvs[j][1] = u, v
                    bm.tangents[j][0] = idall_desert
                n_outer += 1
    print(f"retiled: {n_core} core tris (dunes mains), {n_inner} inner-ring tris (topo41+strip), "
          f"{n_outer} outer-ring tris (topo17+strip)")
    return rows


# ============================================================================================
# STEP D -- run_gates(): everything below is v2's regression/census/save-brick gate list,
# unchanged in mechanism -- only plan["core_origin"] (a fixed 3x3-square centre) is replaced by
# plan["footprint_center_world"] + an actual CORE/INNER cell probe point (the footprint is no
# longer a rectangle, so a bbox-centre point is not guaranteed to land inside it)
# ============================================================================================

def run_gates(built, CELL, plane, plan, before_snapshot):
    bm = built["blocks"][CELL]
    bx, by = CELL

    # -- zero vertex motion: verts/normals byte-identical to the pre-retile snapshot -----------
    verts_ok = bm.verts == before_snapshot["verts"]
    norms_ok = bm.normals == before_snapshot["normals"]
    gate("zero vertex motion (verts byte-identical to the plain host)", verts_ok)
    gate("zero vertex motion (normals byte-identical to the plain host)", norms_ok)

    # -- retile strict zero-residual classification over the touched footprint -----------------
    touched = plan["CORE"] | plan["INNER"] | plan["OUTER"]
    tris_idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
    world_pos = to_world(bm, CELL)
    tally = Counter()
    n_other = 0
    for cell, tri_list in plan["mains_cells"].items():
        if cell not in touched:
            continue
        for ti in tri_list:
            tri = tris_idx[ti]
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            uv3 = [tuple(bm.uvs[j]) for j in tri]
            tag = classify_tri(topo, uv3)
            tally[tag[0]] += 1
            if tag[0] == "other":
                n_other += 1
    gate("retile zero-residual classification (touched footprint: only mains-dunes/strip)", n_other == 0,
         f"tally={dict(tally)}")

    # -- boundary invariance + weld audit + frame bounds ----------------------------------------
    before_edges = before_snapshot["once_edges"]
    after_edges = once_edges_from_bm(bm, CELL)
    gate("boundary invariance (block once-edge set unchanged by the retile)", before_edges == after_edges,
         f"before={len(before_edges)} after={len(after_edges)}")
    pairs = M.weld_audit([bm])
    gate("weld audit (0 near-miss vertex pairs)", not pairs, f"{len(pairs)} pairs")
    lx = [v[0] for v in bm.verts]
    lz = [v[2] for v in bm.verts]
    frame_ok = -0.06 <= min(lx) and max(lx) <= 64.06 and -64.06 <= min(lz) and max(lz) <= 0.06
    gate("frame-bounds (local verts sit inside the block frame)", frame_ok,
         f"x[{min(lx):.2f},{max(lx):.2f}] z[{min(lz):.2f},{max(lz):.2f}]")

    # -- IDALL_SKIP: structurally unreachable (area always 0) -----------------------------------
    skip_hit = any(int(round(bm.tangents[j][0])) in P.IDALL_SKIP for j in range(bm.vcount))
    gate("IDALL_SKIP collision (structurally impossible, area always 0)", not skip_hit)

    # -- engine placement census: MISS regression + MISS==0 --------------------------------------
    hid = lambda nm: M.hidden_block_mesh(name=nm, disc=1, x=bx, y=by)  # noqa: E731
    meshlist_after = [("Object", hid("Object")), ("Terrain", bm), ("Sea1", hid("Sea1")), ("Sea2", hid("Sea2")),
                       ("Sea3", hid("Sea3")), ("Sea4", plane), ("Sea5", hid("Sea5"))]
    meshlist_before = [("Object", hid("Object")), ("Terrain", before_snapshot["bm_plain"]),
                        ("Sea1", hid("Sea1")), ("Sea2", hid("Sea2")), ("Sea3", hid("Sea3")),
                        ("Sea4", plane), ("Sea5", hid("Sea5"))]
    cen_before = P.census(meshlist_before, samples=24)
    cen_after = P.census(meshlist_after, samples=24)
    miss_regression = set(map(tuple, cen_after["miss"])) == set(map(tuple, cen_before["miss"]))
    gate("placement census MISS regression (identical to the plain host)", miss_regression,
         f"after={len(cen_after['miss'])} before={len(cen_before['miss'])}")
    gate("placement census MISS==0 (post-retile)", len(cen_after["miss"]) == 0, f"miss={cen_after['miss'][:5]}")

    # -- THE SAVE-BRICK PROBE: actually ground-query candidate spawn points, don't just assert --
    cx, cz = plan["footprint_center_world"]
    lx0, lz0 = cx - BLOCK * bx, cz + BLOCK * (by + 1) - BLOCK
    gy0, nm0, idall0, topo0 = P.place(meshlist_after, lx0, lz0, sky=True)
    block_centre_ok = nm0 == "Terrain" and topo0 in (17, 41)
    gate(f"save-brick probe: footprint centre ({cx:.0f},{cz:.0f}) grounds walkable", block_centre_ok,
         f"y={gy0:.2f} mesh={nm0} topo={topo0}")

    # a probe point GUARANTEED inside a dunes cell (the footprint is no longer a rectangle, so the
    # bbox-centre point above may or may not itself be a dunes cell -- pick the CORE (or, if the
    # footprint has no pure-interior cell, INNER) cell nearest the bbox centre)
    def cell_world_centre(c):
        return (CELL_U * (c[0] + 0.5), CELL_U * (c[1] + 0.5))
    dunes_pool = plan["CORE"] if plan["CORE"] else plan["INNER"]
    probe_cell = min(dunes_pool, key=lambda c: (lambda w: (w[0] - cx) ** 2 + (w[1] - cz) ** 2)(cell_world_centre(c)))
    px, pz = cell_world_centre(probe_cell)
    plx, plz = px - BLOCK * bx, pz + BLOCK * (by + 1) - BLOCK
    gy1, nm1, idall1, topo1 = P.place(meshlist_after, plx, plz, sky=True)
    core_centre_ok = nm1 == "Terrain" and topo1 == 41
    gate(f"save-brick probe: a dunes cell ({px:.0f},{pz:.0f}, {'CORE' if probe_cell in plan['CORE'] else 'INNER'}) "
         "grounds on walkable dunes (topo 41)", core_centre_ok, f"y={gy1:.2f} mesh={nm1} topo={topo1}")
    # a handful of ring-cell centres too (inner + outer), not just the two named points
    ring_ok = True
    ring_samples = []
    for cell in sorted(list(plan["INNER"])[:2] + list(plan["OUTER"])[:2]):
        rx, rz = CELL_U * cell[0] + CELL_U / 2, CELL_U * cell[1] + CELL_U / 2
        rlx, rlz = rx - BLOCK * bx, rz + BLOCK * (by + 1) - BLOCK
        gy, nm, idall, topo = P.place(meshlist_after, rlx, rlz, sky=True)
        ok = nm == "Terrain" and topo in (17, 41)
        ring_ok = ring_ok and ok
        ring_samples.append((cell, nm, topo, ok))
    gate("save-brick probe: sampled ring-cell centres ground walkable", ring_ok, f"{ring_samples}")

    return dict(tally=dict(tally), cen_after=len(cen_after["miss"]), cen_before=len(cen_before["miss"]))


# ============================================================================================
# THE OFFLINE EYE -- calibrated (stock-vs-stock controls in the same sheet, LAW: CALIBRATE THE
# INSTRUMENT BEFORE YOU JUDGE WITH IT)
# ============================================================================================

LDIR = (-0.45, 0.72, 0.45)
_l = math.sqrt(sum(q * q for q in LDIR))
LDIR = tuple(q / _l for q in LDIR)
ROW_COLOR = {0: (230, 60, 60), 1: (240, 170, 40), 2: (70, 190, 90), 3: (70, 130, 240)}


def _atlas():
    GP = Path(_cfg.find_game_path(None))
    MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / "textures" / "res(1_24)_terrain.png"
    atlas = Image.open(MOG).convert("RGBA")
    return atlas, atlas.size, atlas.load()


def synth_tris(bm, cell):
    bx, by = cell
    V, N, U, TAN = bm.verts, bm.normals, bm.uvs, bm.tangents
    out = []
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        p3 = [(V[j][0] + BLOCK * bx, V[j][1], V[j][2] - BLOCK * by) for j in tri]
        uv3 = [tuple(U[j][:2]) for j in tri]
        n3 = [tuple(N[j][:3]) for j in tri]
        topo = X.decode_id(int(round(TAN[tri[0]][0])))["topograph"]
        out.append((p3, uv3, n3, topo))
    return out


def stock_tris(bx, by):
    bm = X.read_block(bx, by, disc=1, part="terrain")
    return synth_tris(bm, (bx, by))


def paint(tris, cx, cz, win_x, win_z, sc, *, atlas_wh, atlas_px, rowmap=False):
    AW, AH = atlas_wh

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
            r, g, b, a = atlas_px[px_, py_]
            acc[0] += r * wg; acc[1] += g * wg; acc[2] += b * wg; aa += a * wg
        return aa, (acc[0], acc[1], acc[2])

    x0, x1 = cx - win_x / 2, cx + win_x / 2
    z0, z1 = cz - win_z / 2, cz + win_z / 2
    RW, RH = int(win_x * sc), int(win_z * sc)
    tex = Image.new("RGB", (RW, RH), (120, 150, 200))
    com = Image.new("RGB", (RW, RH), (120, 150, 200))
    tp, cp = tex.load(), com.load()
    plotted = []
    for (p3, uv3, n3, topo) in tris:
        if max(p[0] for p in p3) < x0 or min(p[0] for p in p3) > x1:
            continue
        if max(p[2] for p in p3) < z0 or min(p[2] for p in p3) > z1:
            continue
        srow = classify_strip(uv3) if topo in (17, 41) else None
        plotted.append((max(p[1] for p in p3), p3, uv3, n3, srow))
    for _, p3, q3, n3, srow in sorted(plotted, key=lambda t: t[0]):
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
                    rgb, aa = flat_rgb, 255
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
    return tex, com


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


def row_mean_luminance(atlas_wh, atlas_px):
    """A row's mean atlas luminance -- the jumpiness metric's per-row value, reused from the
    v2 calibration technique (mean |delta mean-luminance| between lattice-adjacent strip cells)."""
    AW, AH = atlas_wh
    out = {}
    for row in range(4):
        u0, u1 = G.STRIP_U[0] + _DU, G.STRIP_U[1] + _DU
        v0, v1 = G.STRIPS_V[row][0] + _DV, G.STRIPS_V[row][1] + _DV
        acc = n = 0.0
        for i in range(8):
            for j in range(8):
                u = u0 + (u1 - u0) * (i + 0.5) / 8
                v = v0 + (v1 - v0) * (j + 0.5) / 8
                px = min(max(int((u % 1.0) * AW), 0), AW - 1)
                py = min(max(int((1.0 - v % 1.0) * AH), 0), AH - 1)
                r, g, b, a = atlas_px[px, py]
                acc += 0.2126 * r + 0.7152 * g + 0.0722 * b
                n += 1
        out[row] = acc / n
    return out


def offline_eye(built, CELL, plan, rows, live_ns):
    atlas, atlas_wh, atlas_px = _atlas()
    bm = built["blocks"][CELL]
    synth = synth_tris(bm, CELL)

    # ---- jumpiness, calibrated against the transplant-null band (3.83-5.85) ------------------
    lum = row_mean_luminance(atlas_wh, atlas_px)
    INNER, OUTER = plan["INNER"], plan["OUTER"]
    RING = INNER | OUTER
    diffs, lateral_diffs, cross_diffs = [], [], []
    for c in RING:
        for (di, dj) in ((1, 0), (0, 1)):
            nb = (c[0] + di, c[1] + dj)
            if nb in RING:
                d = abs(lum[rows[c]] - lum[rows[nb]])
                diffs.append(d)
                same_shell = (c in INNER) == (nb in INNER)
                (lateral_diffs if same_shell else cross_diffs).append(d)
    jump = (sum(diffs) / len(diffs)) if diffs else 0.0
    lat_jump = (sum(lateral_diffs) / len(lateral_diffs)) if lateral_diffs else 0.0
    band_ok = 3.83 <= jump <= 5.85
    lat_band_ok = 3.83 <= lat_jump <= 5.85
    gate("offline-eye jumpiness, AGGREGATE all-ring-pairs (informational, STALE calibration post-fix "
         "-- see lateral-only split below; expected to read low, not a defect)", band_ok,
         f"jumpiness={jump:.3f} n_pairs={len(diffs)} row_luminance={ {k: round(v,1) for k,v in lum.items()} }")
    gate("offline-eye jumpiness, LATERAL-ONLY pairs (the like-for-like comparison to the "
         "transplant-null band -- same-boundary-side dither is deliberately left unconstrained)", lat_band_ok,
         f"jumpiness={lat_jump:.3f} n_pairs={len(lateral_diffs)} "
         f"(cross-boundary n_pairs={len(cross_diffs)}, mean={((sum(cross_diffs)/len(cross_diffs)) if cross_diffs else 0.0):.3f}, capped by construction)")

    # ---- render: fixed-window (24x24u tight / 48x48u medium -- v2's own calibrated windows, kept
    # unchanged for apples-to-apples with the stock reference panels, which also only ever show a
    # LOCAL window of a much bigger real component) zoom on the minted seam + 2 real stock windows --
    px, pz = plan["footprint_center_world"]
    STOCK_A, STOCK_B = (18, 3), (13, 12)
    cellinfo = live_ns["cellinfo"]
    strip_cells = live_ns["strip_cells"]

    def stock_centre(bxby):
        cs = [c for c in strip_cells if cellinfo[c]["block"] == bxby]
        if not cs:
            return (bxby[0] * 64 + 32, -(bxby[1] * 64 + 32))
        return ((sum(c[0] for c in cs) / len(cs) + 0.5) * 4.0, (sum(c[1] for c in cs) / len(cs) + 0.5) * 4.0)

    acx, acz = stock_centre(STOCK_A)
    bcx, bcz = stock_centre(STOCK_B)
    a_tris = stock_tris(*STOCK_A) + stock_tris(STOCK_A[0] - 1, STOCK_A[1]) + stock_tris(STOCK_A[0] + 1, STOCK_A[1]) \
        + stock_tris(STOCK_A[0], STOCK_A[1] - 1) + stock_tris(STOCK_A[0], STOCK_A[1] + 1)
    b_tris = stock_tris(*STOCK_B) + stock_tris(STOCK_B[0] - 1, STOCK_B[1]) + stock_tris(STOCK_B[0] + 1, STOCK_B[1]) \
        + stock_tris(STOCK_B[0], STOCK_B[1] - 1) + stock_tris(STOCK_B[0], STOCK_B[1] + 1)

    tight_panels = []
    for label, tris, cx, cz in (("SYNTH minted seam (v3 stamped footprint)", synth, px, pz),
                                 (f"STOCK {STOCK_A} (smooth-organic ref)", a_tris, acx, acz),
                                 (f"STOCK {STOCK_B} (boxy ref)", b_tris, bcx, bcz)):
        tex, com = paint(tris, cx, cz, 24, 24, 32, atlas_wh=atlas_wh, atlas_px=atlas_px)
        _, rowim = paint(tris, cx, cz, 24, 24, 32, atlas_wh=atlas_wh, atlas_px=atlas_px, rowmap=True)
        tight_panels.append((f"{label} -- UNSHADED", tex))
        tight_panels.append((f"{label} -- ROW MAP", rowim))
    sheet(tight_panels, cols=2, cell_w=640, cell_h=640, path=OUTD / "dunes_patch_mint_tight.png",
          title="TIGHT ZOOM (24x24u, sc=32) -- SYNTH minted seam vs 2 REAL stock desert|dunes windows (calibration)")

    medium_panels = []
    for label, tris, cx, cz, win in (("SYNTH whole patch", synth, px, pz, 48),
                                      (f"STOCK {STOCK_A}", a_tris, acx, acz, 48),
                                      (f"STOCK {STOCK_B}", b_tris, bcx, bcz, 48)):
        tex, com = paint(tris, cx, cz, win, win, 10, atlas_wh=atlas_wh, atlas_px=atlas_px)
        medium_panels.append((f"{label} -- TEXTURE", tex))
        medium_panels.append((f"{label} -- SHADED (gameplay-scale)", com))
    sheet(medium_panels, cols=2, cell_w=560, cell_h=560, path=OUTD / "dunes_patch_mint_medium.png",
          title="MEDIUM/GAMEPLAY-SCALE (48x48u, sc=10) -- SYNTH whole patch vs 2 REAL stock windows")

    return dict(jumpiness=jump, jumpiness_in_band=band_ok, row_luminance=lum,
                lateral_jumpiness=lat_jump, lateral_jumpiness_in_band=lat_band_ok,
                cross_jumpiness=((sum(cross_diffs) / len(cross_diffs)) if cross_diffs else 0.0),
                n_lateral_pairs=len(lateral_diffs), n_cross_pairs=len(cross_diffs))


# ============================================================================================
# THE --deploy PATH -- implemented per the brief, NEVER invoked by this harness run
# ============================================================================================

def would_write_list(cell):
    """The exact Disc1 + auto-mirrored Disc4 file list a --deploy would write (design Sec.6.5-6.6),
    printed in dry mode without touching the filesystem (path construction only). ``cell`` is the
    WINNING site's block (may differ from (10,19) if a fallback tier won)."""
    game_root = _cfg.find_game_path(None)
    (bx, by) = cell
    parts = ("Terrain", "Sea4", "Object", "Sea1", "Sea2", "Sea3", "Sea5", "Beach1")
    disc1 = [str(game_root / MOD / M.override_relpath(1, bx, by, part=p)) for p in parts]
    disc1.append(str(game_root / MOD / M.donor_sidecar_relpath(1, bx, by)))
    disc4 = [p.replace("Disc1", "Disc4") for p in disc1]
    return disc1, disc4


def deploy_patch(built, CELL, plane):                          # pragma: no cover -- never invoked this run
    """The real deploy: build_landmass's own per-block write loop (island.landmass, Sec 802-881),
    reused by hand since landmass() itself would deploy the UN-retiled mesh -- our retile happens
    on built["blocks"][CELL] BEFORE any write. Calls discmirror.auto_mirror itself on every path
    it wrote (closing the auto-mirror bypass gap the scrub carry script has)."""
    bx, by = CELL
    bm = built["blocks"][CELL]
    written = []
    written.append(M.deploy_override(bm, mod_folder=MOD, part="Terrain"))
    sea = dataclasses.replace(plane, x=bx, y=by, name=f"Block[{bx}][{by}] Sea4")
    written.append(M.deploy_override(sea, mod_folder=MOD, part="Sea4"))
    for part in I.HIDDEN_PARTS:
        written.append(M.deploy_override(M.hidden_block_mesh(name=f"Block[{bx}][{by}] {part}", disc=1, x=bx, y=by),
                                         mod_folder=MOD, part=part))
    written.append(M.deploy_donor_sidecar(I.DEFAULT_DONOR[0], I.DEFAULT_DONOR[1], mod_folder=MOD, disc=1, x=bx, y=by))
    DM.auto_mirror(written, mod_folder=MOD)
    return written


# ============================================================================================
# CLI smoke test -- the design doc's own recommended CLI line, --dry-run (writes nothing),
# parametrized to the WINNING site (v3: may not be seed=2/radius=26 if a fallback tier won)
# ============================================================================================

def cli_smoke_test(center, radius, seed):
    kit_root = HERE.resolve().parents[1] / "ff9mapkit"
    cmd = [sys.executable, "-m", "ff9mapkit", "world-island", "--ground", "desert",
           "--mod-folder", MOD, "--center", f"{center[0]:g},{center[1]:g}", "--radius", f"{radius:g}",
           "--seed", f"{seed:g}", "--dry-run"]
    print(f"CLI smoke test (from {kit_root}): {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, cwd=str(kit_root), capture_output=True, text=True, timeout=180)
        ok = r.returncode == 0 and "all gates CLEAN" in r.stdout
        gate("CLI smoke test (world-island --dry-run, the winning site's own reproduction command, "
             "writes nothing)", ok, f"returncode={r.returncode} stdout_tail={r.stdout[-300:]!r} "
             f"stderr_tail={r.stderr[-300:]!r}")
        return dict(returncode=r.returncode, stdout=r.stdout, stderr=r.stderr)
    except Exception as e:                                     # noqa: BLE001
        gate("CLI smoke test (world-island --dry-run)", False, f"exception: {e}")
        return dict(error=str(e))


# ============================================================================================
# main
# ============================================================================================

def main():
    print(f"=== dunes_patch_mint.py v3 -- MOD={MOD} PRIMARY_CENTER={CENTER} PRIMARY_RADIUS={RADIUS} "
          f"PRIMARY_SEED={SEED} GROUND={GROUND} TEMPLATE={TEMPLATE_NAME} MINT_SEED(row emitter)={MINT_SEED} ===\n")

    print("--- frozen-constant live re-verification (row emitter) ---")
    live_ns = _live_reverify()

    print("\n--- template live re-verification (dunes_blob_shapes.py, full re-run) ---")
    template, blob_ns = _live_reverify_template()
    template_cells = [tuple(c) for c in template["cell_offsets"]]
    template_boundary = [tuple(c) for c in template["boundary_cell_offsets"]]
    template_cut_boundary = [tuple(c) for c in template.get("cut_boundary_cell_offsets", [])]
    provenance = _template_provenance(blob_ns)
    print(f"template: '{TEMPLATE_NAME}' size={template['size']} bbox_wh={template['bbox_wh']} "
          f"boundary_cells={len(template_boundary)} fits_80_cell_host_with_ring="
          f"{template['fits_80_cell_host_with_ring']}")
    print("NOTE: dunes_blob_shapes.py's own census found ZERO 1-2-cell freckle components anywhere "
          "on the map (falsifying the brief's 'freckle satellite' premise) -- v3 mints none.")

    print("\n--- STEP B: resolve site + placement (fallback ladder) ---")
    site, geom, placement, tier_info = resolve_site_and_placement(template_cells, template_boundary)
    plane, base_report = finalize_site_gates(site, tier_info)
    gate(f"template placement found ({tier_info['label']}): footprint({len(placement['footprint'])} "
         f"cells) + 1-cell ring({len(placement['ring'])} cells) entirely regular, dihedral="
         f"{placement['k']} origin=({placement['oi']},{placement['oj']})", True,
         f"{placement['n_candidates']} candidate placement(s) found across 8 dihedral orientations "
         "at the winning site")

    CELL = site["cell"]
    built = site["built"]

    print("\n--- STEP C: plan the footprint/core/inner/outer cell-set ---")
    plan = plan_cells(geom, placement, template_cells, template_boundary)
    cut_boundary_placed = apply_placement(template_cut_boundary, placement) if template_cut_boundary else set()
    plan["cut_boundary_placed"] = cut_boundary_placed

    # snapshot BEFORE the retile (position-only + a plain copy for the census/edge regressions)
    bm = built["blocks"][CELL]
    before_snapshot = dict(
        verts=copy.deepcopy(bm.verts), normals=copy.deepcopy(bm.normals),
        once_edges=once_edges_from_bm(bm, CELL),
        bm_plain=dataclasses.replace(bm, chan_arrays={k: copy.deepcopy(v) for k, v in bm.chan_arrays.items()}),
    )

    print("\n--- STEP D: apply the retile (uv + tangent.x only) ---")
    rows = apply_retile(bm, plan)

    print("\n--- STEP E: the gate list ---")
    gate_summary = run_gates(built, CELL, plane, plan, before_snapshot)

    print("\n--- STEP F: the offline eye (calibrated) ---")
    eye = offline_eye(built, CELL, plan, rows, live_ns)

    print("\n--- STEP G: the --deploy path (dry mode only -- would-write list) ---")
    disc1, disc4 = would_write_list(CELL)
    print("would write (Disc1):")
    for p in disc1:
        print(f"   {p}")
    print("would write (Disc4, auto-mirrored):")
    for p in disc4:
        print(f"   {p}")

    print("\n--- STEP H: CLI smoke test (winning site's own reproduction command) ---")
    cli_result = cli_smoke_test(tier_info["center"], tier_info["radius"], tier_info["seed"])

    n_fail = sum(1 for _, ok, _ in GATES if not ok)
    print(f"\n=== {len(GATES)} gates run, {n_fail} FAILED ===")

    out = dict(
        mod_folder=MOD, template_name=TEMPLATE_NAME, template_provenance=provenance,
        tier_info=tier_info, primary_center=list(CENTER), primary_radius=RADIUS, primary_seed=SEED,
        ground=GROUND, mint_seed=MINT_SEED, mains_seed=MAINS_SEED, cell=list(CELL),
        dihedral=plan["dihedral"], placement_origin=list(plan["origin"]),
        n_placement_candidates=plan["n_candidates"],
        core_cells=[list(c) for c in sorted(plan["CORE"])],
        inner_ring_cells=[list(c) for c in sorted(plan["INNER"])],
        outer_ring_cells=[list(c) for c in sorted(plan["OUTER"])],
        cut_boundary_cells_placed=[list(c) for c in sorted(plan["cut_boundary_placed"])],
        touch_of={f"{c[0]},{c[1]}": v for c, v in plan["touch_of"].items()},
        row_assignment={f"{c[0]},{c[1]}": r for c, r in rows.items()},
        template_shape=plan["template_shape"], placed_shape=plan["placed_shape"],
        gates=[{"name": n, "ok": ok, "detail": d} for n, ok, d in GATES],
        n_gates=len(GATES), n_failed=n_fail,
        gate_summary=gate_summary, offline_eye=eye,
        would_write_disc1=disc1, would_write_disc4=disc4,
        cli_smoke=dict(returncode=cli_result.get("returncode"), ok="all gates CLEAN" in cli_result.get("stdout", "")),
        outputs=[str(p) for p in sorted(OUTD.glob("dunes_patch_mint_*.png"))],
    )
    (OUTD / "dunes_patch_mint.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"\n-> {OUTD / 'dunes_patch_mint.json'}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
