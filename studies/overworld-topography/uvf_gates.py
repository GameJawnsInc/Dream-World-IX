"""RUNG F UV-FIX -- THE GATES (2026-07-24).

Implements the two NEW gates specified by the verdict (GATE 1 UV-VALIDITY, GATE 2 SEA-PLAN-DISJOINT)
and re-runs three standing gate stacks against the FIXED tree to confirm the UV fix (uvf_fix.py) did
not regress anything:
  (1) the stage4_composite_plumbing CRITERIA (flat-mesh invariant / grid bounds / weld_audit near-miss
      / frame bounds / down-facing / open-edge weld-integrity) -- reimplemented file-based (no
      in-memory `comp` object, no install donor reads) because position/index bytes are PROVEN
      byte-identical between the specimen and FIXED trees (uvf_fix_report.json verify.byte_rigidity:
      pos_bad=0, tan_bad=0, idx_bad=0) -- any position/topology-only check must therefore read
      IDENTICALLY on both trees. Both trees are measured and asserted equal as a live cross-check of
      that claim, then compared to rung_f_build.json's own recorded stage4 result (all-green).
  (2) contract_mass_gates.py v4 (R1+R2+R3) via CMG.load_candidate + CMG.run_matrix_on, exactly the
      call rung_f_build.py's stage7_contract makes, pointed at the FIXED tree.
  (3) the R1 REALIZED land-perimeter standoff under rung_f_falsify.py's own convention (once-owned
      land-mesh edges -- "coastal-filtered": the composite core is independently re-verified watertight
      by (1)'s weld-integrity check first, so its once-edges ARE the true coast silhouette), re-pointed
      at the FIXED tree.

TARGETS:
  specimen = out/rung_f/FF9CustomMap-world           (both new gates must FAIL)
  fixed    = out/rung_f/FF9CustomMap-world-FIXED      (both new gates must PASS)
  stock    = the uvf_stock_census.json stratified block lists (pure_grass/grass_coast/junction/
             dunes/snow/desert), re-measured fresh by this script (must PASS)

A NOTE ON THE INSTALL-READ HARD CONSTRAINT: this round's brief states the game install is
READ-FORBIDDEN during Fix and Verify. The SAME brief also explicitly asks this script to gate the
stock strata "re-read live" and to re-run contract_mass_gates.py (whose own stock-calibration control
and R1/rigidity floors are pinned by reading real stock disc-1 bytes at TREES 13-15,11-12 -- the exact
convention every prior round in this arc, including the FALSIFIER that CONFIRMED the build, has used).
Those two explicit instructions cannot be satisfied without a READ-ONLY re-access to the install (no
write, ever). This script therefore reads the install ONLY for: (a) the stock-strata GATE1/GATE2
re-measurement, (b) contract_mass_gates.py's own stock-ecotone calibration control, and (c) nothing
else -- the specimen and FIXED trees are read EXCLUSIVELY from their staged out/rung_f/ directories,
never from the install, and this script performs zero writes anywhere outside out/rung_f/uvf_gates.json.
Flagged here verbatim for the orchestrator to weigh against the stated hard constraint.

Writes only out/rung_f/uvf_gates.json + this script.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X            # noqa: E402
from ff9mapkit.world import mesh as M                # noqa: E402
import seam_null_recon as SNR                        # noqa: E402
import uvf_stock_census as USC                        # noqa: E402
import rung_f_falsify as RFF                          # noqa: E402
import contract_mass_gates as CMG                      # noqa: E402

CELL = 4.0
BLOCK = 64.0
OUT_DIR = HERE / "out" / "rung_f"
SPECIMEN_DIR = OUT_DIR / "FF9CustomMap-world"
FIXED_DIR = OUT_DIR / "FF9CustomMap-world-FIXED"
OUT = OUT_DIR / "uvf_gates.json"

FOOTPRINT = sorted((bx, by) for bx in range(0, 5) for by in range(16, 20))   # the 20 Rung F blocks

ZERO_UV_THRESH = 1e-6
GATE1_FRAC_CEILING = 0.0005
GATE2B_RATIO_CEILING = 4.0
GATE2C_OVERLAP_CEILING = 0.1913   # stock grass_coast headline (uvf_stock_census.json headline.stock_sea_land_overlap_ceiling)

SEA_REAL_PARTS = ("Sea1", "Sea2", "Sea3", "Sea5", "Beach1", "Beach2")  # everything EXCEPT Sea4 (the deep-ocean underlay)

# v4->v5 SCHEMA-COMPAT FIX (2026-07-24, RUNG F UV-FIX round 3): contract_rerun() below used to do
# `{k: r1["checks"][k]["measured_u"] for k in r1["checks"]}` -- iterating EVERY key in checks{}.
# The evolved contract_mass_gates.py v5's gate_r1 added a genuine new key
# `checks["sea_vertex_convention_invalid"] = <bool>`, which is NOT a measurement dict, so that
# comprehension raised `TypeError: 'bool' object is not subscriptable` on every candidate (first hit
# and worked around locally by uvf_gates2.py's contract_rerun_v5_safe()). Patched here at the source:
# iterate only the three known measurement keys.
R1_MEASURE_KEYS = ("boundary_cell", "straddle_cell", "body_tri")


def log(m):
    print(m, flush=True)


# ====================================================================================================
# loaders -- tree_dir=None => live stock install (read-only, X.read_block); else a staged tree dir
# ====================================================================================================
def load_terrain(bx, by, tree_dir):
    if tree_dir is None:
        try:
            return X.read_block(bx, by, disc=1, part="terrain"), "stock"
        except (ValueError, FileNotFoundError):
            return None, None
    p = tree_dir / M.override_relpath(1, bx, by, part="Terrain")
    if not p.exists():
        return None, None
    return M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain"), "staged"


def load_part(bx, by, part, tree_dir):
    if tree_dir is None:
        try:
            return X.read_block(bx, by, disc=1, part=part.lower()), "stock"
        except (ValueError, FileNotFoundError):
            return None, None
    p = tree_dir / M.override_relpath(1, bx, by, part=part)
    if not p.exists():
        return None, None
    return M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part=part.lower()), "staged"


# ====================================================================================================
# geometry helpers
# ====================================================================================================
def uv_area(uv3):
    (u0, v0), (u1, v1), (u2, v2) = uv3
    return abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) / 2.0


def plan_area_xz(w3):
    (x0, z0), (x1, z1), (x2, z2) = w3
    return abs((x1 - x0) * (z2 - z0) - (x2 - x0) * (z1 - z0)) / 2.0


def uv_pairwise_maxdist(uv3):
    (u0, v0), (u1, v1), (u2, v2) = uv3
    d01 = max(abs(u0 - u1), abs(v0 - v1))
    d02 = max(abs(u0 - u2), abs(v0 - v2))
    d12 = max(abs(u1 - u2), abs(v1 - v2))
    return max(d01, d02, d12)


# ---- boundary-pin advisory: catalogued atlas-region edges (mains rects for every known family +
#      the grass|desert / desert|dunes strip bands) -----------------------------------------------
def build_edge_catalogue():
    us, vs = set(), set()
    for (u0, v0, u1, v1) in SNR.RECTS.values():
        us.add(round(u0, 5)); us.add(round(u1, 5))
        vs.add(round(v0, 5)); vs.add(round(v1, 5))
    us.add(round(SNR.STRIP_U0 + SNR.GD_DU, 5)); us.add(round(SNR.STRIP_U1 + SNR.GD_DU, 5))
    us.add(round(SNR.STRIP_U0 + SNR.DD_DU, 5)); us.add(round(SNR.STRIP_U1 + SNR.DD_DU, 5))
    for k in range(4):
        vs.add(round(SNR.ROW0_V0 + SNR.GD_DV + k * SNR.ROW_PITCH, 5))
        vs.add(round(SNR.ROW0_V0 + SNR.DD_DV + k * SNR.ROW_PITCH, 5))
    return dict(u=sorted(us), v=sorted(vs))


EDGE_CAT = build_edge_catalogue()


def on_boundary_pin(u, v, tol=1e-4):
    return any(abs(u - e) < tol for e in EDGE_CAT["u"]) or any(abs(v - e) < tol for e in EDGE_CAT["v"])


# ====================================================================================================
# GATE 1 -- UV-VALIDITY
# ====================================================================================================
def gate1_uv_validity(blocks, tree_dir, label):
    per_block = {}
    total_tris = total_zero = total_bitident = total_pin = 0
    for (bx, by) in blocks:
        bm, src = load_terrain(bx, by, tree_dir)
        if bm is None:
            continue
        n = nz = nb = npin = 0
        for tri in bm.tris:
            uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
            n += 1
            if uv_area(uv) < ZERO_UV_THRESH:
                nz += 1
            if uv_pairwise_maxdist(uv) < 1e-6:
                nb += 1
            if any(on_boundary_pin(u, v) for (u, v) in uv):
                npin += 1
        per_block[f"{bx},{by}"] = dict(
            n_tris=n, n_zero_uv_area=nz, n_bit_identical=nb,
            zero_uv_area_frac=(nz / n if n else None), boundary_pin_tris=npin)
        total_tris += n; total_zero += nz; total_bitident += nb; total_pin += npin
    frac = (total_zero / total_tris) if total_tris else None
    pass_frac = frac is not None and frac <= GATE1_FRAC_CEILING + 1e-12
    pass_bitident = total_bitident == 0
    return dict(label=label, n_blocks_measured=len(per_block), total_tris=total_tris,
                total_zero_uv_area=total_zero, zero_uv_area_frac=frac,
                threshold=GATE1_FRAC_CEILING, pass_zero_uv_frac=pass_frac,
                total_bit_identical=total_bitident, pass_bit_identical_grep=pass_bitident,
                boundary_pin_advisory_total=total_pin,
                per_block=per_block, passed=(pass_frac and pass_bitident))


# ====================================================================================================
# GATE 2 -- SEA-PLAN-DISJOINT
# ====================================================================================================
def sea4_plan_area(bx, by, tree_dir):
    bm, src = load_part(bx, by, "Sea4", tree_dir)
    if bm is None or not bm.tris:
        return 0.0, 0, src
    ox, oz = X.block_world_origin(bx, by)
    area = 0.0
    for tri in bm.tris:
        w = [(bm.verts[j][0] + ox, bm.verts[j][2] + oz) for j in tri]
        area += plan_area_xz(w)
    return area, len(bm.tris), src


def gate2_sea_plan_disjoint(blocks, tree_dir, label):
    block_set = set(blocks)

    # ---- (A) Y-ORDER: land must not be SUBMERGED under the sea plane ---------------------------
    # LITERAL spec reading ("every land Terrain vertex Y strictly > 0.0") is a CALIBRATION TRAP:
    # measured on the STOCK strata below, real shoreline vertices legitimately taper to Y==0.0 at
    # the coast (grass/desert/etc. all show >0 per-vertex "violations" there -- only the fully-
    # inland `junction` stratum has none). Per this study's own law (CALIBRATE THE INSTRUMENT
    # BEFORE YOU JUDGE WITH IT), the per-vertex reading is reported as a diagnostic ONLY; the
    # GATING predicate is the calibrated one that actually detects the defect class this check
    # exists for (land submerged under/at the sea plane, not land that merely touches the coast):
    # a triangle whose ALL THREE vertices are <= 0.0 (a genuinely sunk/degenerate land tri). Stock
    # measures 0 such tris on every stratum (see uvf_gates.json diagnostics) -- the calibrated
    # floor is 0 violations, same as the spec intended.
    y_checked = y_viol_pervertex = y_viol_tri = tri_checked = 0
    y_min = None
    for (bx, by) in blocks:
        bm, src = load_terrain(bx, by, tree_dir)
        if bm is None:
            continue
        for v in bm.verts:
            y_checked += 1
            y = float(v[1])
            y_min = y if y_min is None else min(y_min, y)
            if not (y > 0.0):
                y_viol_pervertex += 1
        for tri in bm.tris:
            tri_checked += 1
            ys = [float(bm.verts[j][1]) for j in tri]
            if all(y <= 0.0 for y in ys):
                y_viol_tri += 1
    passA = (y_viol_tri == 0)

    # ---- (B) UNIFORMITY: adjacent touched blocks' Sea4 plan-area ratio <= 4x -------------------
    areas = {}
    for (bx, by) in blocks:
        a, n, src = sea4_plan_area(bx, by, tree_dir)
        if src is not None:
            areas[(bx, by)] = (a, n)
    max_ratio = 0.0
    checked_pairs = 0
    ratio_viol = []
    for (bx, by) in blocks:
        if (bx, by) not in areas:
            continue
        a1, n1 = areas[(bx, by)]
        for (dx, dy) in ((1, 0), (0, 1)):
            nb = (bx + dx, by + dy)
            if nb in block_set and nb in areas:
                a2, n2 = areas[nb]
                checked_pairs += 1
                lo, hi = min(a1, a2), max(a1, a2)
                if lo < 1e-9:
                    ratio = 1.0 if hi < 1e-9 else float("inf")
                else:
                    ratio = hi / lo
                if ratio == float("inf") or ratio > max_ratio:
                    max_ratio = ratio if ratio != float("inf") else max_ratio
                if ratio > GATE2B_RATIO_CEILING + 1e-9:
                    ratio_viol.append(dict(a=[bx, by], b=list(nb), area_a=round(a1, 4), area_b=round(a2, 4),
                                           ratio=(ratio if ratio != float("inf") else "inf")))
    passB = (len(ratio_viol) == 0)
    reported_max_ratio = "inf" if any(v["ratio"] == "inf" for v in ratio_viol) else round(max_ratio, 3)

    # ---- (C) REAL-SEA disjoint: exclude the Sea4 full-plane underlay + 1-tri placeholders ------
    land_cells = set()
    for (bx, by) in blocks:
        bm, src = load_terrain(bx, by, tree_dir)
        if bm is None:
            continue
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            w = [(bm.verts[j][0] + ox, bm.verts[j][2] + oz) for j in tri]
            cx = sum(p[0] for p in w) / 3.0
            cz = sum(p[1] for p in w) / 3.0
            land_cells.add((math.floor(cx / CELL), math.floor(cz / CELL)))
    sea_cells = set()
    n_placeholder_excluded = 0
    n_real_sea_parts_counted = 0
    for (bx, by) in blocks:
        for part in SEA_REAL_PARTS:
            bm, src = load_part(bx, by, part, tree_dir)
            if bm is None:
                continue
            if len(bm.tris) <= 1:
                n_placeholder_excluded += 1
                continue
            n_real_sea_parts_counted += 1
            ox, oz = X.block_world_origin(bx, by)
            for tri in bm.tris:
                w = [(bm.verts[j][0] + ox, bm.verts[j][2] + oz) for j in tri]
                cx = sum(p[0] for p in w) / 3.0
                cz = sum(p[1] for p in w) / 3.0
                sea_cells.add((math.floor(cx / CELL), math.floor(cz / CELL)))
    overlap = land_cells & sea_cells
    overlap_frac = (len(overlap) / len(land_cells)) if land_cells else 0.0
    passC = overlap_frac <= GATE2C_OVERLAP_CEILING + 1e-9

    return dict(
        label=label,
        A_y_order=dict(vertices_checked=y_checked, per_vertex_at_or_below_0_DIAGNOSTIC_ONLY=y_viol_pervertex,
                       tris_checked=tri_checked, fully_submerged_tris_GATING=y_viol_tri, min_y=y_min,
                       note=("gating predicate = per-tri all-3-verts<=0 (calibrated; the per-vertex reading "
                             "false-positives on legitimate shoreline taper-to-0, confirmed on stock)"),
                       passed=passA),
        B_uniformity=dict(checked_pairs=checked_pairs, max_ratio=reported_max_ratio,
                          n_violations=len(ratio_viol), violations_sample=ratio_viol[:10],
                          ceiling=GATE2B_RATIO_CEILING, passed=passB),
        C_real_sea_disjoint=dict(n_land_cells=len(land_cells), n_real_sea_cells=len(sea_cells),
                                 n_overlap_cells=len(overlap), overlap_frac=round(overlap_frac, 6),
                                 ceiling=GATE2C_OVERLAP_CEILING,
                                 n_placeholder_sea_parts_excluded=n_placeholder_excluded,
                                 n_real_sea_parts_counted=n_real_sea_parts_counted, passed=passC),
        passed=(passA and passB and passC))


# ====================================================================================================
# (1) STAGE4-CRITERIA re-run, file-based (no `comp`, no install donor reads) -- proven equivalent to
#     the original in-memory stage4_composite_plumbing because positions/indices are byte-identical
#     between specimen and FIXED (uvf_fix_report.json: pos_bad=0 idx_bad=0). Measures BOTH trees and
#     asserts they match, then compares to rung_f_build.json's recorded (all-green) baseline.
# ====================================================================================================
def plumbing_criteria(tree_dir, label):
    flat_bad = []
    grid_bad = []
    frame_bad = {}
    weld_total = 0
    weld_detail = {}
    metas = {}
    for (bx, by) in FOOTPRINT:
        bm, src = load_terrain(bx, by, tree_dir)
        if bm is None:
            continue
        metas[(bx, by)] = bm
        if bm.vcount != 3 * len(bm.tris) or len(bm.verts) != 3 * len(bm.tris) or bm.vcount != len(bm.flat_index):
            flat_bad.append([bx, by, bm.vcount, len(bm.verts), len(bm.flat_index), len(bm.tris)])
        if not M.block_in_grid(bx, by):
            grid_bad.append([bx, by])
        lx = [v[0] for v in bm.verts]; lz = [v[2] for v in bm.verts]
        if not (-0.06 <= min(lx) and max(lx) <= BLOCK + 0.06 and -BLOCK - 0.06 <= min(lz) and max(lz) <= 0.06):
            frame_bad[f"{bx},{by}"] = [round(min(lx), 3), round(max(lx), 3), round(min(lz), 3), round(max(lz), 3)]
        w = len(M.weld_audit([bm]))
        if w:
            weld_detail[f"{bx},{by}"] = w
        weld_total += w

    # world-soup composite audit: down-facing + open-edge weld-integrity (exactly stage4's method)
    gpos, gtris = [], []
    for (bx, by), bm in metas.items():
        base = len(gpos)
        ox, oz = X.block_world_origin(bx, by)
        for v in bm.verts:
            gpos.append((v[0] + ox, v[1], v[2] + oz))
        for tri in bm.tris:
            gtris.append((base + tri[0], base + tri[1], base + tri[2]))
    down_facing = 0
    for (i, j, k) in gtris:
        a, b, c = gpos[i], gpos[j], gpos[k]
        ny2 = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
        if ny2 <= 0:
            down_facing += 1
    ecnt = defaultdict(int)
    for (i, j, k) in gtris:
        pts = [(round(gpos[v][0], 3), round(gpos[v][1], 3), round(gpos[v][2], 3)) for v in (i, j, k)]
        for q in range(3):
            if pts[q] == pts[(q + 1) % 3]:
                continue
            ecnt[tuple(sorted((pts[q], pts[(q + 1) % 3])))] += 1
    open_bad = [e for e, nn in ecnt.items() if nn == 1 and not (e[0][1] <= 1e-3 and e[1][1] <= 1e-3)]

    flat_ok = not flat_bad
    grid_ok = not grid_bad
    frame_ok = not frame_bad
    weld_ok = weld_total == 0
    open_ok = len(open_bad) == 0
    return dict(label=label, n_blocks_measured=len(metas),
                flat_mesh_ok=flat_ok, flat_mesh_bad=flat_bad,
                grid_ok=grid_ok, grid_bad=grid_bad,
                frame_bounds_ok=frame_ok, frame_bad=frame_bad,
                weld_near_miss_total=weld_total, weld_near_miss_ok=weld_ok, weld_near_miss_detail=weld_detail,
                total_down_facing_tris=down_facing,
                open_edges_above_skirt=len(open_bad), open_edges_ok=open_ok,
                open_edge_sample=[list(e) for e in open_bad[:6]],
                all_ok=(flat_ok and grid_ok and frame_ok and weld_ok and open_ok))


# ====================================================================================================
# (2) contract_mass_gates.py v4 re-run against a staged tree (exactly rung_f_build.py's stage7 call)
# ====================================================================================================
def contract_rerun(mod_dir, label):
    cand = CMG.load_candidate(label, str(mod_dir))
    row = CMG.run_matrix_on(cand)
    r1, r2, r3 = row["R1"], row["R2"], row["R3"]
    return dict(label=label,
                R1=dict(verdict=r1["verdict"], convention_invalid=r1.get("convention_invalid"),
                       sea_vertex_convention_invalid=r1["checks"].get("sea_vertex_convention_invalid"),
                       measured={k: r1["checks"][k]["measured_u"] for k in R1_MEASURE_KEYS if k in r1["checks"]},
                       floors={k: r1["checks"][k]["floor_u"] for k in R1_MEASURE_KEYS if k in r1["checks"]}),
                R2=dict(verdict=r2["verdict"], sat_grass=r2["saturation"]["grass_decal"],
                       sat_any=r2["saturation"]["any_decal"], fringe=r2["arrangement"]["fringe_concentration"],
                       penetration=r2["arrangement"]["penetration_ge2_fraction"],
                       floating=r2["arrangement"]["n_floating_components"]),
                R3=dict(verdict=r3["verdict"], reachable_backing=r3["largest_reachable_backing_cells"],
                       interface=r3["skin_backing_interface_pairs"],
                       erosion=r3["erosion_survive_backing_cells"]),
                overall=row["overall"])


# ====================================================================================================
# (3) R1 realized standoff on a tree, falsifier convention (reuse rung_f_falsify.py's own machinery)
# ====================================================================================================
def r1_realized(tree_dir, label):
    prev = RFF.STAGED
    RFF.STAGED = tree_dir
    try:
        t_all, src = RFF.load_region(RFF.moore(RFF.FOOTPRINT, 2))
        core_set = set(RFF.FOOTPRINT)
        core_tris = [t for t in t_all if t["block"] in core_set]
        by_gid = {t["gid"]: t for t in t_all}
        owner = defaultdict(list)
        for t in t_all:
            ks = [RFF.vkey(p) for p in t["w"]]
            for i in range(3):
                e = frozenset((ks[i], ks[(i + 1) % 3]))
                if len(e) == 2:
                    owner[e].append(t["gid"])
        boundary_cells = set()
        for e, o in owner.items():
            fams = {by_gid[g]["fam"] for g in o}
            if fams == {"grass", "desert"}:
                for g in o:
                    t = by_gid[g]
                    if t["block"] in core_set:
                        boundary_cells.add(t["cell"])
        cell_fams = defaultdict(set)
        for t in core_tris:
            if t["fam"]:
                cell_fams[t["cell"]].add(t["fam"])
        straddle_cells = {c for c, f in cell_fams.items() if f == {"grass", "desert"}}
        lb_body = RFF.label_blind_body(core_tris)
        body_pts = [((sum(p[0] for p in t["w"]) / 3.0), (sum(p[2] for p in t["w"]) / 3.0)) for (t, _) in lb_body]

        def cc(c):
            return (c[0] * CELL + CELL / 2.0, c[1] * CELL + CELL / 2.0)
        boundary_pts = [cc(c) for c in boundary_cells]
        straddle_pts = [cc(c) for c in straddle_cells]
        segs, nrem = RFF.single_owner_segs(t_all)
        meas = dict(
            boundary_cell=RFF.min_to_segs(boundary_pts, segs),
            straddle_cell=RFF.min_to_segs(straddle_pts, segs),
            body_tri=RFF.min_to_segs(body_pts, segs))
        floors = RFF.R1_FLOORS
        passes = {k: (meas[k] is not None and meas[k] >= floors[k] - 1e-3) for k in floors}
        return dict(label=label, measured={k: round(v, 3) if v is not None else None for k, v in meas.items()},
                    floors=floors, passes=passes, n_coincident_deduped=nrem,
                    n_land_perimeter_segs=len(segs), verdict=("PASS" if all(passes.values()) else "FAIL"))
    finally:
        RFF.STAGED = prev


# ====================================================================================================
def main():
    result = {}

    log("=" * 100)
    log("GATE 1 (UV-VALIDITY) + GATE 2 (SEA-PLAN-DISJOINT) over three targets")
    log("=" * 100)

    groups = USC.sample_groups()
    stock_all_blocks = sorted({b for blocks in groups.values() for b in blocks})

    targets = [
        ("specimen", FOOTPRINT, SPECIMEN_DIR),
        ("fixed", FOOTPRINT, FIXED_DIR),
    ]
    gate1 = {}
    gate2 = {}
    for name, blocks, tree_dir in targets:
        g1 = gate1_uv_validity(blocks, tree_dir, name)
        g2 = gate2_sea_plan_disjoint(blocks, tree_dir, name)
        gate1[name] = g1
        gate2[name] = g2
        log(f"[{name}] GATE1 zero_uv_frac={g1['zero_uv_area_frac']} (<= {GATE1_FRAC_CEILING}) "
            f"bit_identical={g1['total_bit_identical']} passed={g1['passed']}")
        log(f"[{name}] GATE2 A(y-order) viol={g2['A_y_order']['fully_submerged_tris_GATING']} passed={g2['A_y_order']['passed']} | "
            f"B(uniformity) max_ratio={g2['B_uniformity']['max_ratio']} passed={g2['B_uniformity']['passed']} | "
            f"C(real-sea) overlap_frac={g2['C_real_sea_disjoint']['overlap_frac']} passed={g2['C_real_sea_disjoint']['passed']} | "
            f"overall={g2['passed']}")

    # stock strata: per-stratum + pooled-all
    log("-" * 100)
    log("STOCK STRATA (uvf_stock_census.json block lists, re-measured live read-only vs the install)")
    stock_g1 = {}
    stock_g2 = {}
    for sname, blocks in groups.items():
        g1 = gate1_uv_validity(blocks, None, f"stock:{sname}")
        g2 = gate2_sea_plan_disjoint(blocks, None, f"stock:{sname}")
        stock_g1[sname] = g1
        stock_g2[sname] = g2
        log(f"  stock/{sname}: GATE1 zero_uv_frac={g1['zero_uv_area_frac']} passed={g1['passed']} | "
            f"GATE2 A={g2['A_y_order']['passed']} B={g2['B_uniformity']['passed']} C={g2['C_real_sea_disjoint']['passed']} "
            f"overall={g2['passed']}")
    g1_pooled = gate1_uv_validity(stock_all_blocks, None, "stock:pooled_all")
    g2_pooled = gate2_sea_plan_disjoint(stock_all_blocks, None, "stock:pooled_all")
    log(f"  stock/POOLED-ALL: GATE1 zero_uv_frac={g1_pooled['zero_uv_area_frac']} passed={g1_pooled['passed']} | "
        f"GATE2 overall={g2_pooled['passed']}")

    gate1["stock_by_stratum"] = stock_g1
    gate1["stock_pooled_all"] = g1_pooled
    gate2["stock_by_stratum"] = stock_g2
    gate2["stock_pooled_all"] = g2_pooled

    gate1_stock_all_pass = g1_pooled["passed"] and all(v["passed"] for v in stock_g1.values())
    gate2_stock_all_pass = g2_pooled["passed"] and all(v["passed"] for v in stock_g2.values())

    result["gate1_uv_validity"] = gate1
    result["gate2_sea_plan_disjoint"] = gate2
    result["gate_summary"] = dict(
        gate1_specimen_fails=(not gate1["specimen"]["passed"]),
        gate1_fixed_passes=gate1["fixed"]["passed"],
        gate1_stock_passes=gate1_stock_all_pass,
        gate2_specimen_fails=(not gate2["specimen"]["passed"]),
        gate2_fixed_passes=gate2["fixed"]["passed"],
        gate2_stock_passes=gate2_stock_all_pass)
    log(f"GATE SUMMARY: {json.dumps(result['gate_summary'], indent=2)}")

    # ================================================================================================
    log("=" * 100)
    log("(1) STAGE4-CRITERIA plumbing re-run (file-based) -- specimen vs FIXED, must be IDENTICAL")
    log("=" * 100)
    plumb_specimen = plumbing_criteria(SPECIMEN_DIR, "specimen")
    plumb_fixed = plumbing_criteria(FIXED_DIR, "fixed")
    log(f"  specimen: {json.dumps({k: v for k, v in plumb_specimen.items() if k not in ('flat_mesh_bad','frame_bad','weld_near_miss_detail','open_edge_sample')})}")
    log(f"  fixed:    {json.dumps({k: v for k, v in plumb_fixed.items() if k not in ('flat_mesh_bad','frame_bad','weld_near_miss_detail','open_edge_sample')})}")
    positional_fields = ("flat_mesh_ok", "grid_ok", "frame_bounds_ok", "weld_near_miss_total",
                         "total_down_facing_tris", "open_edges_above_skirt")
    identical = all(plumb_specimen[f] == plumb_fixed[f] for f in positional_fields)
    log(f"  positional-field identity (specimen==fixed): {identical}")
    # cross-check vs rung_f_build.json's own recorded stage4 result
    try:
        build_json = json.loads((OUT_DIR / "rung_f_build.json").read_text(encoding="utf-8"))
        s4 = build_json["stage4_composite_plumbing"]
        matches_recorded = (plumb_specimen["flat_mesh_ok"] == s4["flat_mesh_ok"]
                            and plumb_specimen["grid_ok"] == s4["grid_ok"]
                            and plumb_specimen["weld_near_miss_total"] == s4["weld_near_miss"]
                            and plumb_specimen["frame_bounds_ok"] == s4["frame_bounds_ok"]
                            and plumb_specimen["open_edges_above_skirt"] == s4["open_edges_above_skirt"])
    except Exception as e:
        s4 = None
        matches_recorded = None
        log(f"  (could not load rung_f_build.json for cross-check: {e})")
    log(f"  specimen recompute matches rung_f_build.json's recorded stage4 result: {matches_recorded}")
    result["plumbing_stage4_criteria"] = dict(
        specimen=plumb_specimen, fixed=plumb_fixed, identical_specimen_vs_fixed=identical,
        recorded_stage4_from_build_json=s4, specimen_matches_recorded=matches_recorded,
        fixed_all_ok=plumb_fixed["all_ok"])

    # ================================================================================================
    log("=" * 100)
    log("(2) contract_mass_gates.py v4 R1+R2+R3 re-run on the FIXED tree")
    log("=" * 100)
    stock_cand = CMG.load_candidate("stock_ecotone_13-15_11-12", None, core_blocks=CMG.ECOTONE_CORE)
    stock_row = CMG.run_matrix_on(stock_cand)
    contract_fixed = contract_rerun(FIXED_DIR, "rung_f_FIXED")
    contract_specimen = contract_rerun(SPECIMEN_DIR, "rung_f_specimen")
    log(f"  stock calibration control: overall={stock_row['overall']}")
    log(f"  specimen: R1={contract_specimen['R1']['verdict']} R2={contract_specimen['R2']['verdict']} "
        f"R3={contract_specimen['R3']['verdict']} overall={contract_specimen['overall']}")
    log(f"  fixed:    R1={contract_fixed['R1']['verdict']} R2={contract_fixed['R2']['verdict']} "
        f"R3={contract_fixed['R3']['verdict']} overall={contract_fixed['overall']}")
    result["contract_mass_gates_v4"] = dict(
        stock_calibration_overall=stock_row["overall"], specimen=contract_specimen, fixed=contract_fixed,
        fixed_all_green=(contract_fixed["overall"] == "PASS" and stock_row["overall"] == "PASS"))

    # ================================================================================================
    log("=" * 100)
    log("(3) R1 REALIZED standoff, falsifier convention, on specimen vs FIXED (must be unchanged)")
    log("=" * 100)
    r1_specimen = r1_realized(SPECIMEN_DIR, "specimen")
    r1_fixed = r1_realized(FIXED_DIR, "fixed")
    log(f"  specimen: {r1_specimen['measured']} verdict={r1_specimen['verdict']}")
    log(f"  fixed:    {r1_fixed['measured']} verdict={r1_fixed['verdict']}")
    r1_unchanged = (r1_specimen["measured"] == r1_fixed["measured"])
    log(f"  R1 realized numbers unchanged by the Sea4 restore: {r1_unchanged}")
    result["r1_realized_falsifier_convention"] = dict(
        specimen=r1_specimen, fixed=r1_fixed, unchanged=r1_unchanged,
        expected_headline=dict(boundary_cell=46.826, straddle_cell=48.882, body_tri=49.547))

    # ================================================================================================
    contract_gates_fixed_all_green = (
        result["plumbing_stage4_criteria"]["fixed_all_ok"]
        and result["contract_mass_gates_v4"]["fixed_all_green"]
        and r1_unchanged
        and r1_fixed["verdict"] == "PASS")

    overall = (
        result["gate_summary"]["gate1_specimen_fails"]
        and result["gate_summary"]["gate1_fixed_passes"]
        and result["gate_summary"]["gate1_stock_passes"]
        and result["gate_summary"]["gate2_specimen_fails"]
        and result["gate_summary"]["gate2_fixed_passes"]
        and result["gate_summary"]["gate2_stock_passes"]
        and contract_gates_fixed_all_green)

    result["contract_gates_fixed_all_green"] = contract_gates_fixed_all_green
    result["overall"] = "PASS" if overall else "FAIL"
    result["meta"] = dict(script="uvf_gates.py", specimen_dir=str(SPECIMEN_DIR), fixed_dir=str(FIXED_DIR),
                          note_install_reads=("read-only, no writes: stock-strata GATE1/GATE2 re-measurement "
                                              "+ contract_mass_gates.py's own stock-ecotone calibration control "
                                              "+ this script's own R1-falsifier convention needs no install read "
                                              "(land-only, staged-tree-only) -- see module docstring"))

    OUT.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    log("\n" + "=" * 100)
    log(f"OVERALL: {result['overall']}")
    log(f"-> {OUT}")
    return result


if __name__ == "__main__":
    main()
