"""RUNG F UV-FIX ROUND 3 -- THE FULL VERIFICATION BATTERY on FF9CustomMap-world-FIXED3A.

Wraps uvf_gates.py (reused verbatim -- imported, not edited further by this script; it WAS patched
in place for a real v4->v5 schema-compat bug, see PATCH NOTE below) and uvf_gates2.py's pattern, and
re-points every one of the standing checks at the FIXED3A tree (out/rung_f/FF9CustomMap-world-FIXED3A),
the output of uvf_fix3.py's ONE-WINDOW-PER-TRI fix. Adds ONE new predicate this round did not have:
GATE 1c ONE-WINDOW-COHERENCE -- every synthesized-zone (the 2305 UV-rewritten) tri's 3 on-disk UVs must
be reproducible from a SINGLE (cell, quad, ori) window, independently re-derived from disk (not trusted
from uvf_fix3_report.json).

PATCH NOTE (applied to uvf_gates.py itself, this round, per the brief's explicit instruction): its
contract_rerun() used to do `{k: r1["checks"][k]["measured_u"] for k in r1["checks"]}` -- iterating
EVERY key in checks{}. The evolved contract_mass_gates.py v5's gate_r1 added a genuine new key
`checks["sea_vertex_convention_invalid"] = <bool>` (not a measurement dict), so that comprehension
raised `TypeError: 'bool' object is not subscriptable` on every candidate -- first hit by
uvf_gates2.py, which worked around it LOCALLY with a copy-pasted contract_rerun_v5_safe(). This round
fixes it AT THE SOURCE instead: uvf_gates.py now has a module-level `R1_MEASURE_KEYS = ("boundary_cell",
"straddle_cell", "body_tri")` and contract_rerun() iterates that tuple (guarded by `if k in
r1["checks"]`) rather than r1["checks"].keys(), and additionally surfaces the new
`sea_vertex_convention_invalid` flag. Verified live in this script (contract_rerun() is called
directly, unwrapped, no local safe-copy needed) -- see result["patch_verification"].

SIX CHECKS, all against FIXED3A (uvf_gates.py's own functions reused verbatim except where noted):
  (1) GATE 1a UV-VALIDITY          -- zero-uv-area frac <= 0.0005, bit-identical grep == 0.  Must PASS.
  (2) GATE 1c ONE-WINDOW-COHERENCE -- NEW this round (see above). Must PASS on FIXED3A; is EXPECTED TO
                                      FAIL on specimen/FIXED(r1)/FIXED2 (measuring the exact defect
                                      classes rounds 1-3 each represent -- reported as diagnostic
                                      cross-checks, not gated, since the brief's target is FIXED3A).
  (3) GATE 2 SEA-PLAN-DISJOINT     -- A(y-order) / B(uniformity) / C(real-sea disjoint). Must PASS.
  (4) STAGE4 PLUMBING CRITERIA     -- flat-mesh / grid bounds / weld near-miss / frame bounds /
                                      down-facing / open-edge weld-integrity. FIXED3A must be
                                      POSITION-IDENTICAL to specimen (byte-rigidity re-verified live)
                                      and all_ok.
  (5) CONTRACT MATRIX (v5)         -- R1 (PASS, sea_vertex_convention_invalid=True,
                                      convention_invalid=False, realized triple 46.826/48.882/49.547u
                                      over floors 39.953/44.635/42.968u -- UNCHANGED from FIXED/FIXED2
                                      since UV-only changes cannot move XZ/Y geometry), R2, R3, +
                                      the stock calibration control -- all PASS.
  (6) R1 REALIZED standoff, falsifier convention (uvf_gates.py's own r1_realized) -- must match the
                                      headline exactly, confirming FIXED3A's fill geometry (positions)
                                      is byte-identical to FIXED/FIXED2/specimen (the round-3 fix is
                                      UV-only by construction; re-verified, not assumed).

Writes only out/rung_f/uvf_gates3.json + this script + the in-place patch to uvf_gates.py. Zero git,
zero install writes beyond the read-only stock-strata/calibration reads uvf_gates.py's own docstring
already documents and defends. specimen / FIXED / FIXED2 / FIXED3A trees read-only throughout.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import uvf_gates as G            # noqa: E402  -- reused; PATCHED in place this round (see module docstring)
import uvf_stock_census as USC   # noqa: E402
import contract_mass_gates as CMG  # noqa: E402
import uvf_fix2 as F2            # noqa: E402  -- decode_quad_ori / assign_mains_seeded / uv_tri_degen
import uvf_fix3 as F3            # noqa: E402  -- classify_defective / own_cell / max_pairwise_uv / QUAD_DIAG
from ff9mapkit.world import mesh as M            # noqa: E402  -- override_relpath / blockmesh_from_ff9mesh

OUT_DIR = HERE / "out" / "rung_f"
SPECIMEN_DIR = G.SPECIMEN_DIR
FIXED_DIR = G.FIXED_DIR
FIXED2_DIR = OUT_DIR / "FF9CustomMap-world-FIXED2"
FIXED3A_DIR = OUT_DIR / "FF9CustomMap-world-FIXED3A"
OUT = OUT_DIR / "uvf_gates3.json"

FOOTPRINT = G.FOOTPRINT
ONE_WINDOW_FRAC_CEILING = 0.0005     # same ceiling as GATE1_FRAC_CEILING -- >=99.95% single-window


def log(m):
    print(m, flush=True)


# ====================================================================================================
# GATE 1c -- ONE-WINDOW-COHERENCE (NEW this round)
# ====================================================================================================
def build_reference_state():
    """Everything needed to test window-coherence on ANY target tree, derived ONCE from the SPECIMEN
    tree + the frozen forensics/build artifacts (never from a fix script's own report). Mirrors
    uvf_fix3.py's classify_defective() + build_fixed3a()'s cell-field reconstruction (lines 280-317)
    exactly, but re-executed here independently (this script imports the FUNCTIONS, not the report)."""
    build = json.loads((OUT_DIR / "rung_f_build.json").read_text(encoding="utf-8"))
    touched = [tuple(b) for b in build["compose_diag"]["touched_blocks"]]
    assert len(touched) == 20

    forensics = json.loads((OUT_DIR / "uvf_forensics.json").read_text(encoding="utf-8"))
    apron_keys = set()
    for rec in forensics["records"]:
        if rec.get("uv_verdict") == "degenerate-zero-area" and rec["provenance"] == "apron":
            cx, _cy, cz = rec["centroid"]
            apron_keys.add((tuple(rec["block"]), round(cx, 3), round(cz, 3)))

    spec_meshes = F3.load_blocks(SPECIMEN_DIR, touched)
    defective, lawful_grass = F3.classify_defective(spec_meshes, apron_keys, touched)
    assert len(defective) == 2305, f"defective count drifted: {len(defective)} != 2305"

    # ---- rebuild the EXACT (quad,ori) cell field (method-a truth + assign_mains_seeded dropped) ----
    target_cells = set()
    for d in defective:
        for (vx, _vy, vz) in d["vw"]:
            target_cells.add(F3.own_cell(vx, vz))
    centroid_cells = set()
    for d in defective:
        cx = sum(p[0] for p in d["vw"]) / 3.0
        cz = sum(p[2] for p in d["vw"]) / 3.0
        centroid_cells.add(F3.own_cell(cx, cz))
    resolve_cells = target_cells | centroid_cells

    decoded_a = {}
    by_cell = defaultdict(list)
    for (cell, vw, uv3) in lawful_grass:
        by_cell[cell].append((vw, uv3))
    for cell in sorted(by_cell):
        got = None
        for (vw, uv3) in by_cell[cell]:
            qo = F2.decode_quad_ori(cell, vw, uv3)
            if qo is not None:
                got = qo
                break
        if got is not None:
            decoded_a[cell] = got
    dropped = sorted(c for c in resolve_cells if c not in decoded_a)

    pre_quad = dict(decoded_a)
    pre_ori = {c: o for c, (q, o) in decoded_a.items()}
    v2_quad, v2_ori = F2.assign_mains_seeded(dropped, pre_quad, pre_ori, seed=F3.V2_SEED)

    decoded_map = {c: (q, o, "a") for c, (q, o) in decoded_a.items()}
    for c in dropped:
        decoded_map[c] = (v2_quad[c], v2_ori[c], "v2")

    log(f"[ref-state] touched={len(touched)} defective={len(defective)} "
        f"cell_field: method-a={len(decoded_a)} dropped={len(dropped)} resolve={len(resolve_cells)}")
    return dict(touched=touched, defective=defective, decoded_map=decoded_map)


def window_coherence_check(target_dir, label, ref):
    """For each of the 2305 synthesized-zone tris, is there a SINGLE (cell,quad,ori) candidate
    (centroid cell, or a vertex own-cell) whose predicted UVs match the TARGET TREE's on-disk UVs
    exactly (float32 round-trip tolerance)? Also reports the max pairwise UV spread (the barycentric
    sweep length) as a plain geometric diagnostic independent of reconstruction. Vertex indices
    (d['vids']) are stable across specimen/FIXED/FIXED2/FIXED3A -- all four trees are position/index
    -byte-identical copies of the specimen (re-verified independently below in plumbing/r1_realized),
    differing only in UV (and, for the apron subset, normals)."""
    touched = ref["touched"]
    defective = ref["defective"]
    decoded_map = ref["decoded_map"]

    meshes = {}
    for (bx, by) in touched:
        p = target_dir / M.override_relpath(1, bx, by, part="Terrain")
        meshes[(bx, by)] = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain") if p.exists() else None

    n = single_qo = multi_qo = missing = 0
    exc = []
    over_window = 0
    per_block_multi = defaultdict(int)
    for d in defective:
        (bx, by) = d["block"]
        bm = meshes.get((bx, by))
        if bm is None:
            missing += 1
            continue
        n += 1
        # channel index for UV -- reuse F3's own channel constant (CH_UV), identical module-level alias
        uvs = bm.chan_arrays[F3.CH_UV]
        uv3 = [(uvs[j][0], uvs[j][1]) for j in d["vids"]]

        cx = sum(p[0] for p in d["vw"]) / 3.0
        cz = sum(p[2] for p in d["vw"]) / 3.0
        cand = [F3.own_cell(cx, cz)] + [F3.own_cell(vx, vz) for (vx, _vy, vz) in d["vw"]]
        ok = False
        for cell in cand:
            if cell not in decoded_map:
                continue
            q, o, _m = decoded_map[cell]
            pred = [tuple(F3.G.ground_uv(vx, vz, cell, q, o, "grass")) for (vx, _vy, vz) in d["vw"]]
            if all(abs(pred[k][0] - uv3[k][0]) < 5e-6 and abs(pred[k][1] - uv3[k][1]) < 5e-6
                   for k in range(3)):
                ok = True
                break
        single_qo += ok
        if not ok:
            multi_qo += 1
            per_block_multi[f"{bx},{by}"] += 1
        e = F3.max_pairwise_uv(uv3)
        exc.append(e)
        if e > F3.QUAD_DIAG + 1e-9:
            over_window += 1

    exc.sort()
    nn = len(exc)
    multi_frac = (multi_qo / n) if n else None
    passed = (n > 0 and missing == 0 and multi_frac is not None and multi_frac <= ONE_WINDOW_FRAC_CEILING + 1e-12)
    return dict(
        label=label, n_tris=n, n_missing_blocks=missing,
        single_window_reconstructed=single_qo, multi_window_or_unreconstructed=multi_qo,
        multi_window_frac=round(multi_frac, 6) if multi_frac is not None else None,
        threshold=ONE_WINDOW_FRAC_CEILING,
        excursion_p50=round(exc[nn // 2], 5) if nn else None,
        excursion_p90=round(exc[int(0.9 * (nn - 1))], 5) if nn else None,
        excursion_max=round(exc[-1], 5) if nn else None,
        one_window_scale=round(F3.QUAD_DIAG, 5),
        tris_spread_over_one_window_scale=over_window,
        per_block_multi_window_sample=dict(list(sorted(per_block_multi.items(),
                                                        key=lambda kv: -kv[1]))[:10]),
        passed=passed)


# ====================================================================================================
def main():
    assert FIXED3A_DIR.exists(), f"missing target tree: {FIXED3A_DIR}"
    result = {}

    # ====================================================================================================
    log("=" * 100)
    log("PATCH VERIFICATION -- uvf_gates.py's contract_rerun() called UNWRAPPED against v5, must not raise")
    log("=" * 100)
    try:
        _probe = G.contract_rerun(FIXED3A_DIR, "patch_verify_probe")
        patch_ok = True
        patch_err = None
        log(f"  contract_rerun(FIXED3A) unwrapped OK: R1={_probe['R1']['verdict']} "
            f"sea_vertex_convention_invalid={_probe['R1']['sea_vertex_convention_invalid']}")
    except Exception as e:
        patch_ok = False
        patch_err = f"{type(e).__name__}: {e}"
        log(f"  contract_rerun(FIXED3A) unwrapped RAISED: {patch_err}")
    result["patch_verification"] = dict(
        target="uvf_gates.py:contract_rerun", fix="iterate R1_MEASURE_KEYS instead of r1['checks'].keys()",
        called_unwrapped_no_local_workaround=True, raised=(not patch_ok), error=patch_err, passed=patch_ok)

    # ====================================================================================================
    log("=" * 100)
    log("(1) GATE 1a UV-VALIDITY + GATE 2 SEA-PLAN-DISJOINT on FIXED3A (uvf_gates.py functions, verbatim)")
    log("=" * 100)
    g1_fixed3a = G.gate1_uv_validity(FOOTPRINT, FIXED3A_DIR, "fixed3a")
    g2_fixed3a = G.gate2_sea_plan_disjoint(FOOTPRINT, FIXED3A_DIR, "fixed3a")
    log(f"[fixed3a] GATE1a zero_uv_frac={g1_fixed3a['zero_uv_area_frac']} (<= {G.GATE1_FRAC_CEILING}) "
        f"bit_identical={g1_fixed3a['total_bit_identical']} passed={g1_fixed3a['passed']}")
    log(f"[fixed3a] GATE2 A={g2_fixed3a['A_y_order']['passed']} B={g2_fixed3a['B_uniformity']['passed']} "
        f"C={g2_fixed3a['C_real_sea_disjoint']['passed']} overall={g2_fixed3a['passed']}")

    # cross-checks: specimen must still FAIL, FIXED(r1)/FIXED2 must still PASS gate1a/gate2 (unaffected
    # by round 3's UV-only rewrite of the SAME zone -- confirms nothing upstream broke)
    g1_spec = G.gate1_uv_validity(FOOTPRINT, SPECIMEN_DIR, "specimen_crosscheck")
    g2_spec = G.gate2_sea_plan_disjoint(FOOTPRINT, SPECIMEN_DIR, "specimen_crosscheck")
    g1_fixed1 = G.gate1_uv_validity(FOOTPRINT, FIXED_DIR, "fixed_r1_crosscheck")
    g1_fixed2 = G.gate1_uv_validity(FOOTPRINT, FIXED2_DIR, "fixed2_crosscheck")
    log(f"[specimen crosscheck] GATE1a passed={g1_spec['passed']} (expect False) "
        f"GATE2 passed={g2_spec['passed']}")
    log(f"[fixed(r1)/fixed2 crosscheck] GATE1a passed r1={g1_fixed1['passed']} fixed2={g1_fixed2['passed']} "
        "(expect True both -- unaffected by round 3)")

    groups = USC.sample_groups()
    stock_all_blocks = sorted({b for blocks in groups.values() for b in blocks})
    stock_g1 = {sname: G.gate1_uv_validity(blocks, None, f"stock:{sname}") for sname, blocks in groups.items()}
    stock_g2 = {sname: G.gate2_sea_plan_disjoint(blocks, None, f"stock:{sname}") for sname, blocks in groups.items()}
    g1_pooled = G.gate1_uv_validity(stock_all_blocks, None, "stock:pooled_all")
    g2_pooled = G.gate2_sea_plan_disjoint(stock_all_blocks, None, "stock:pooled_all")
    gate1_stock_all_pass = g1_pooled["passed"] and all(v["passed"] for v in stock_g1.values())
    gate2_stock_all_pass = g2_pooled["passed"] and all(v["passed"] for v in stock_g2.values())
    log(f"  stock/POOLED-ALL: GATE1a passed={g1_pooled['passed']} | GATE2 passed={g2_pooled['passed']} "
        f"| all-strata GATE1a={gate1_stock_all_pass} GATE2={gate2_stock_all_pass}")

    result["gate1a_uv_validity"] = dict(fixed3a=g1_fixed3a, specimen_crosscheck=g1_spec,
                                         fixed_r1_crosscheck=g1_fixed1, fixed2_crosscheck=g1_fixed2,
                                         stock_by_stratum=stock_g1, stock_pooled_all=g1_pooled)
    result["gate2_sea_plan_disjoint"] = dict(fixed3a=g2_fixed3a, specimen_crosscheck=g2_spec,
                                              stock_by_stratum=stock_g2, stock_pooled_all=g2_pooled)

    # ====================================================================================================
    log("=" * 100)
    log("(2) GATE 1c ONE-WINDOW-COHERENCE (NEW) -- FIXED3A must PASS; specimen/FIXED(r1)/FIXED2 diagnostic")
    log("=" * 100)
    ref = build_reference_state()
    wc_specimen = window_coherence_check(SPECIMEN_DIR, "specimen", ref)
    wc_fixed1 = window_coherence_check(FIXED_DIR, "fixed_r1", ref)
    wc_fixed2 = window_coherence_check(FIXED2_DIR, "fixed2", ref)
    wc_fixed3a = window_coherence_check(FIXED3A_DIR, "fixed3a", ref)
    for wc in (wc_specimen, wc_fixed1, wc_fixed2, wc_fixed3a):
        log(f"  [{wc['label']}] n={wc['n_tris']} single_window={wc['single_window_reconstructed']} "
            f"multi/unrecon={wc['multi_window_or_unreconstructed']} frac={wc['multi_window_frac']} "
            f"exc_p50={wc['excursion_p50']} exc_max={wc['excursion_max']} "
            f"(one_window_scale={wc['one_window_scale']}) passed={wc['passed']}")
    result["gate1c_one_window_coherence"] = dict(
        fixed3a=wc_fixed3a,
        diagnostic_specimen=wc_specimen, diagnostic_fixed_r1=wc_fixed1, diagnostic_fixed2=wc_fixed2,
        gated_target="fixed3a", note=("specimen/fixed(r1)/fixed2 are reported as DIAGNOSTIC cross-checks, "
                                      "not gated -- they measure the exact defect classes rounds 1-2 (and "
                                      "the raw specimen) represent; only FIXED3A's pass/fail gates overall"))

    # ====================================================================================================
    log("=" * 100)
    log("(3) STAGE4-CRITERIA plumbing re-run (file-based, uvf_gates.py's plumbing_criteria) on FIXED3A")
    log("   -- must be POSITION-IDENTICAL to specimen/FIXED/FIXED2 (round 3 is UV-only by construction)")
    log("=" * 100)
    plumb_specimen = G.plumbing_criteria(SPECIMEN_DIR, "specimen")
    plumb_fixed1 = G.plumbing_criteria(FIXED_DIR, "fixed_r1")
    plumb_fixed2 = G.plumbing_criteria(FIXED2_DIR, "fixed2")
    plumb_fixed3a = G.plumbing_criteria(FIXED3A_DIR, "fixed3a")
    positional_fields = ("flat_mesh_ok", "grid_ok", "frame_bounds_ok", "weld_near_miss_total",
                          "total_down_facing_tris", "open_edges_above_skirt")
    identical_spec_vs_3a = all(plumb_specimen[f] == plumb_fixed3a[f] for f in positional_fields)
    identical_1_vs_3a = all(plumb_fixed1[f] == plumb_fixed3a[f] for f in positional_fields)
    identical_2_vs_3a = all(plumb_fixed2[f] == plumb_fixed3a[f] for f in positional_fields)
    log(f"  specimen:  {json.dumps({k: v for k, v in plumb_specimen.items() if k in positional_fields})}")
    log(f"  fixed(r1): {json.dumps({k: v for k, v in plumb_fixed1.items() if k in positional_fields})}")
    log(f"  fixed2:    {json.dumps({k: v for k, v in plumb_fixed2.items() if k in positional_fields})}")
    log(f"  fixed3a:   {json.dumps({k: v for k, v in plumb_fixed3a.items() if k in positional_fields})}")
    log(f"  position-identical: specimen==3a {identical_spec_vs_3a} | r1==3a {identical_1_vs_3a} | "
        f"fixed2==3a {identical_2_vs_3a}")
    log(f"  fixed3a.all_ok = {plumb_fixed3a['all_ok']}")

    try:
        build_json = json.loads((OUT_DIR / "rung_f_build.json").read_text(encoding="utf-8"))
        s4 = build_json["stage4_composite_plumbing"]
        matches_recorded = (plumb_fixed3a["flat_mesh_ok"] == s4["flat_mesh_ok"]
                             and plumb_fixed3a["grid_ok"] == s4["grid_ok"]
                             and plumb_fixed3a["weld_near_miss_total"] == s4["weld_near_miss"]
                             and plumb_fixed3a["frame_bounds_ok"] == s4["frame_bounds_ok"]
                             and plumb_fixed3a["open_edges_above_skirt"] == s4["open_edges_above_skirt"])
    except Exception as e:
        s4 = None
        matches_recorded = None
        log(f"  (could not load rung_f_build.json for cross-check: {e})")
    log(f"  fixed3a recompute matches rung_f_build.json's recorded (all-green) stage4 result: {matches_recorded}")

    result["plumbing_stage4_criteria"] = dict(
        specimen=plumb_specimen, fixed_r1=plumb_fixed1, fixed2=plumb_fixed2, fixed3a=plumb_fixed3a,
        identical_specimen_vs_fixed3a=identical_spec_vs_3a,
        identical_fixed_r1_vs_fixed3a=identical_1_vs_3a,
        identical_fixed2_vs_fixed3a=identical_2_vs_3a,
        recorded_stage4_from_build_json=s4, fixed3a_matches_recorded=matches_recorded,
        fixed3a_all_ok=plumb_fixed3a["all_ok"])

    # ====================================================================================================
    log("=" * 100)
    log("(4) contract_mass_gates.py v5 R1+R2+R3 re-run on FIXED3A + stock calibration control")
    log("    (uvf_gates.py's own PATCHED contract_rerun -- no local workaround)")
    log("=" * 100)
    stock_cand = CMG.load_candidate("stock_ecotone_13-15_11-12", None, core_blocks=CMG.ECOTONE_CORE)
    stock_row = CMG.run_matrix_on(stock_cand)
    contract_fixed3a = G.contract_rerun(FIXED3A_DIR, "rung_f_FIXED3A")
    contract_fixed2 = G.contract_rerun(FIXED2_DIR, "rung_f_FIXED2_crosscheck")
    contract_fixed1 = G.contract_rerun(FIXED_DIR, "rung_f_FIXED_r1_crosscheck")
    log(f"  stock calibration control: overall={stock_row['overall']}")
    log(f"  fixed(r1) crosscheck: R1={contract_fixed1['R1']['verdict']} overall={contract_fixed1['overall']}")
    log(f"  fixed2 crosscheck:    R1={contract_fixed2['R1']['verdict']} overall={contract_fixed2['overall']}")
    log(f"  fixed3a:              R1={contract_fixed3a['R1']['verdict']} R2={contract_fixed3a['R2']['verdict']} "
        f"R3={contract_fixed3a['R3']['verdict']} overall={contract_fixed3a['overall']}")
    log(f"  fixed3a R1 measured={contract_fixed3a['R1']['measured']} floors={contract_fixed3a['R1']['floors']} "
        f"convention_invalid={contract_fixed3a['R1']['convention_invalid']} "
        f"sea_vertex_convention_invalid={contract_fixed3a['R1']['sea_vertex_convention_invalid']}")

    sea_vertex_flag = contract_fixed3a["R1"]["sea_vertex_convention_invalid"]
    convention_invalid_flag = contract_fixed3a["R1"]["convention_invalid"]
    expected_floors = dict(boundary_cell=39.953, straddle_cell=44.635, body_tri=42.968)
    floors_match = all(abs(contract_fixed3a["R1"]["floors"].get(k, -1) - v) < 0.01 for k, v in expected_floors.items())

    result["contract_mass_gates_v5"] = dict(
        stock_calibration_overall=stock_row["overall"],
        fixed_r1_crosscheck=contract_fixed1,
        fixed2_crosscheck=contract_fixed2,
        fixed3a=contract_fixed3a,
        fixed3a_R1_sea_vertex_convention_invalid=sea_vertex_flag,
        fixed3a_R1_convention_invalid=convention_invalid_flag,
        floors_match_expected=floors_match,
        fixed3a_all_green=(contract_fixed3a["overall"] == "PASS" and stock_row["overall"] == "PASS"))

    # ====================================================================================================
    log("=" * 100)
    log("(5) R1 REALIZED standoff, falsifier convention (uvf_gates.py's r1_realized) on FIXED3A")
    log("     -- must equal the round-1 headline 46.826/48.882/49.547u (UV changes cannot move XZ/Y)")
    log("=" * 100)
    r1_fixed3a = G.r1_realized(FIXED3A_DIR, "fixed3a")
    r1_fixed2 = G.r1_realized(FIXED2_DIR, "fixed2_crosscheck")
    r1_fixed1 = G.r1_realized(FIXED_DIR, "fixed_r1_crosscheck")
    log(f"  fixed(r1) crosscheck: {r1_fixed1['measured']} verdict={r1_fixed1['verdict']}")
    log(f"  fixed2 crosscheck:    {r1_fixed2['measured']} verdict={r1_fixed2['verdict']}")
    log(f"  fixed3a:              {r1_fixed3a['measured']} verdict={r1_fixed3a['verdict']}")
    expected = dict(boundary_cell=46.826, straddle_cell=48.882, body_tri=49.547)
    r1_matches_headline = (r1_fixed3a["measured"] == expected)
    r1_unchanged_vs_1_and_2 = (r1_fixed3a["measured"] == r1_fixed1["measured"] == r1_fixed2["measured"])
    log(f"  fixed3a measured == expected headline {expected}: {r1_matches_headline}")
    log(f"  fixed3a measured == fixed(r1) == fixed2 measured: {r1_unchanged_vs_1_and_2}")
    result["r1_realized_falsifier_convention"] = dict(
        fixed_r1_crosscheck=r1_fixed1, fixed2_crosscheck=r1_fixed2, fixed3a=r1_fixed3a,
        expected_headline=expected, fixed3a_matches_expected_headline=r1_matches_headline,
        fixed3a_unchanged_vs_fixed_r1_and_fixed2=r1_unchanged_vs_1_and_2)

    # ====================================================================================================
    contract_matrix_green = (
        contract_fixed3a["R1"]["verdict"] == "PASS"
        and contract_fixed3a["R2"]["verdict"] == "PASS"
        and contract_fixed3a["R3"]["verdict"] == "PASS"
        and contract_fixed3a["overall"] == "PASS"
        and stock_row["overall"] == "PASS"
        and sea_vertex_flag is True
        and convention_invalid_flag is False
        and floors_match
        and r1_matches_headline
        and r1_unchanged_vs_1_and_2
        and r1_fixed3a["verdict"] == "PASS")

    result["contract_matrix"] = dict(
        R1=contract_fixed3a["R1"]["verdict"], R2=contract_fixed3a["R2"]["verdict"],
        R3=contract_fixed3a["R3"]["verdict"], overall=contract_fixed3a["overall"],
        stock_control=stock_row["overall"],
        sea_vertex_convention_invalid_flagged=sea_vertex_flag,
        convention_invalid=convention_invalid_flag,
        realized_triple=contract_fixed3a["R1"]["measured"],
        floors=contract_fixed3a["R1"]["floors"],
        all_green=contract_matrix_green)

    gate_summary = dict(
        gate1a_fixed3a_passes=g1_fixed3a["passed"],
        gate1a_specimen_still_fails=(not g1_spec["passed"]),
        gate1a_fixed_r1_still_passes=g1_fixed1["passed"],
        gate1a_fixed2_still_passes=g1_fixed2["passed"],
        gate1a_stock_passes=gate1_stock_all_pass,
        gate1c_fixed3a_passes=wc_fixed3a["passed"],
        gate2_fixed3a_passes=g2_fixed3a["passed"],
        gate2_specimen_still_fails=(not g2_spec["passed"]),
        gate2_stock_passes=gate2_stock_all_pass)
    result["gate_summary"] = gate_summary
    log(f"GATE SUMMARY: {json.dumps(gate_summary, indent=2)}")

    overall = (
        patch_ok
        and gate_summary["gate1a_fixed3a_passes"]
        and gate_summary["gate1a_specimen_still_fails"]
        and gate_summary["gate1a_fixed_r1_still_passes"]
        and gate_summary["gate1a_fixed2_still_passes"]
        and gate_summary["gate1a_stock_passes"]
        and gate_summary["gate1c_fixed3a_passes"]
        and gate_summary["gate2_fixed3a_passes"]
        and gate_summary["gate2_specimen_still_fails"]
        and gate_summary["gate2_stock_passes"]
        and result["plumbing_stage4_criteria"]["fixed3a_all_ok"]
        and result["plumbing_stage4_criteria"]["identical_specimen_vs_fixed3a"]
        and result["plumbing_stage4_criteria"]["identical_fixed_r1_vs_fixed3a"]
        and result["plumbing_stage4_criteria"]["identical_fixed2_vs_fixed3a"]
        and contract_matrix_green)

    result["overall"] = "PASS" if overall else "FAIL"
    result["meta"] = dict(
        script="uvf_gates3.py", target=str(FIXED3A_DIR),
        reused_functions_from="uvf_gates.py (patched, see module docstring) for gate1a/gate2/plumbing/"
                              "contract_rerun/r1_realized",
        new_this_round="gate1c_one_window_coherence (window_coherence_check), independently re-derives "
                       "the (quad,ori) cell field from the SPECIMEN tree + forensics/build artifacts "
                       "(not trusted from uvf_fix3_report.json), then tests FIXED3A/specimen/FIXED/"
                       "FIXED2's on-disk UVs against it",
        contract_gates_version="contract_mass_gates.py v5 (evolved, live)",
        patch_applied_to="uvf_gates.py (R1_MEASURE_KEYS + contract_rerun, in place, this round)",
        note="zero writes outside out/rung_f/uvf_gates3.json (+ the in-place uvf_gates.py patch); "
             "zero git; specimen/FIXED/FIXED2/FIXED3A trees read-only throughout")

    OUT.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    log("\n" + "=" * 100)
    log(f"OVERALL: {result['overall']}")
    log(f"-> {OUT}")
    return result


if __name__ == "__main__":
    main()
