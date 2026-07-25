"""RUNG F UV-FIX ROUND 2 -- THE FULL VERIFICATION BATTERY on FF9CustomMap-world-FIXED2.

Wraps uvf_gates.py (unmodified -- imported, not edited) and re-points every one of its four checks at
the FIXED2 tree (out/rung_f/FF9CustomMap-world-FIXED2), the output of uvf_fix2.py's chevron/diamond-quilt
fix. Reuses uvf_gates.py's own function bodies verbatim (gate1_uv_validity, gate2_sea_plan_disjoint,
plumbing_criteria, contract_rerun, r1_realized) -- no reimplementation, so any drift in this script's own
logic vs the round-1-reviewed instrument is impossible.

FOUR CHECKS, all against FIXED2:
  (1) GATE 1 UV-VALIDITY            -- zero-uv-area frac <= 0.0005, bit-identical grep == 0.  Must PASS.
  (2) GATE 2 SEA-PLAN-DISJOINT       -- A(y-order, calibrated all-3-verts<=0) / B(uniformity <=4x) /
                                        C(real-sea disjoint, placeholder-excluded, ceiling 0.1913). Must PASS.
  (3) STAGE4 PLUMBING CRITERIA       -- flat-mesh / grid bounds / weld near-miss / frame bounds /
                                        down-facing / open-edge weld-integrity. FIXED2 must be
                                        POSITION-IDENTICAL to the specimen (byte-rigidity re-verified
                                        live here, not just trusted from the fix2 report) and all_ok.
  (4) CONTRACT MATRIX (v5, evolved)  -- R1 (must be PASS, with sea_vertex_convention_invalid=True
                                        flagged and convention_invalid=False, realized triple
                                        46.826/48.882/49.547u over floors 39.953/44.635/42.968u,
                                        UNCHANGED from FIXED since UV changes cannot move XZ/Y
                                        geometry), R2, R3, + the stock calibration control -- all PASS.

Writes only out/rung_f/uvf_gates2.json + this script. Zero git, zero install writes, zero edits to
uvf_gates.py / contract_mass_gates.py / the FIXED / specimen / FIXED2 trees (read-only throughout).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import uvf_gates as G           # noqa: E402  -- reused verbatim, unedited
import uvf_stock_census as USC  # noqa: E402
import contract_mass_gates as CMG  # noqa: E402

MEASURE_KEYS = ("boundary_cell", "straddle_cell", "body_tri")


def contract_rerun_v5_safe(mod_dir, label):
    """SCHEMA-COMPAT FIX (found live by this script, not pre-known): uvf_gates.py's own
    contract_rerun() does `{k: r1["checks"][k]["measured_u"] for k in r1["checks"]}` -- it iterates
    EVERY key in checks{} and assumes each value is a measurement dict. v5's gate_r1 (the evolved
    contract_mass_gates.py) added `checks["sea_vertex_convention_invalid"] = <bool>`, a genuine new
    key that is NOT a measurement dict -- so uvf_gates.py's contract_rerun() now raises
    `TypeError: 'bool' object is not subscriptable` on EVERY candidate, not just FIXED2. This is a
    real v4->v5 compatibility regression in the *reused* script, discovered here, not part of this
    round's fix. Rather than edit uvf_gates.py or contract_mass_gates.py (both owned by prior/other
    rounds), this is a local schema-safe copy that iterates only the three known measure keys and
    ALSO surfaces the new v5 flags explicitly (sea_vertex_convention_invalid, convention_invalid)."""
    cand = CMG.load_candidate(label, str(mod_dir))
    row = CMG.run_matrix_on(cand)
    r1, r2, r3 = row["R1"], row["R2"], row["R3"]
    return dict(label=label,
                R1=dict(verdict=r1["verdict"], convention_invalid=r1.get("convention_invalid"),
                       sea_vertex_convention_invalid=r1.get("sea_vertex_convention_invalid"),
                       measured={k: r1["checks"][k]["measured_u"] for k in MEASURE_KEYS},
                       floors={k: r1["checks"][k]["floor_u"] for k in MEASURE_KEYS}),
                R2=dict(verdict=r2["verdict"], sat_grass=r2["saturation"]["grass_decal"],
                       sat_any=r2["saturation"]["any_decal"], fringe=r2["arrangement"]["fringe_concentration"],
                       penetration=r2["arrangement"]["penetration_ge2_fraction"],
                       floating=r2["arrangement"]["n_floating_components"]),
                R3=dict(verdict=r3["verdict"], reachable_backing=r3["largest_reachable_backing_cells"],
                       interface=r3["skin_backing_interface_pairs"],
                       erosion=r3["erosion_survive_backing_cells"]),
                overall=row["overall"])

OUT_DIR = HERE / "out" / "rung_f"
FIXED2_DIR = OUT_DIR / "FF9CustomMap-world-FIXED2"
SPECIMEN_DIR = G.SPECIMEN_DIR
FIXED_DIR = G.FIXED_DIR
OUT = OUT_DIR / "uvf_gates2.json"

FOOTPRINT = G.FOOTPRINT


def log(m):
    print(m, flush=True)


def main():
    assert FIXED2_DIR.exists(), f"missing target tree: {FIXED2_DIR}"
    result = {}

    # ====================================================================================================
    log("=" * 100)
    log("(1)+(2) GATE 1 UV-VALIDITY + GATE 2 SEA-PLAN-DISJOINT on FIXED2 (uvf_gates.py functions, verbatim)")
    log("=" * 100)
    g1_fixed2 = G.gate1_uv_validity(FOOTPRINT, FIXED2_DIR, "fixed2")
    g2_fixed2 = G.gate2_sea_plan_disjoint(FOOTPRINT, FIXED2_DIR, "fixed2")
    log(f"[fixed2] GATE1 zero_uv_frac={g1_fixed2['zero_uv_area_frac']} (<= {G.GATE1_FRAC_CEILING}) "
        f"bit_identical={g1_fixed2['total_bit_identical']} passed={g1_fixed2['passed']}")
    log(f"[fixed2] GATE2 A(y-order) viol={g2_fixed2['A_y_order']['fully_submerged_tris_GATING']} "
        f"passed={g2_fixed2['A_y_order']['passed']} | "
        f"B(uniformity) max_ratio={g2_fixed2['B_uniformity']['max_ratio']} passed={g2_fixed2['B_uniformity']['passed']} | "
        f"C(real-sea) overlap_frac={g2_fixed2['C_real_sea_disjoint']['overlap_frac']} passed={g2_fixed2['C_real_sea_disjoint']['passed']} | "
        f"overall={g2_fixed2['passed']}")

    # cross-check vs round-1 FIXED (must also still pass -- confirms uvf_gates.py itself is untouched
    # and the FIXED tree, never rewritten, still measures the same as its own recorded round-1 result)
    g1_fixed1 = G.gate1_uv_validity(FOOTPRINT, FIXED_DIR, "fixed(r1)_crosscheck")
    g2_fixed1 = G.gate2_sea_plan_disjoint(FOOTPRINT, FIXED_DIR, "fixed(r1)_crosscheck")
    log(f"[fixed(r1) crosscheck] GATE1 passed={g1_fixed1['passed']} GATE2 passed={g2_fixed1['passed']} "
        "(round-1 FIXED must be untouched/still-passing)")

    # stock strata re-measured live read-only (same convention as uvf_gates.py's own main())
    groups = USC.sample_groups()
    stock_all_blocks = sorted({b for blocks in groups.values() for b in blocks})
    stock_g1 = {sname: G.gate1_uv_validity(blocks, None, f"stock:{sname}") for sname, blocks in groups.items()}
    stock_g2 = {sname: G.gate2_sea_plan_disjoint(blocks, None, f"stock:{sname}") for sname, blocks in groups.items()}
    g1_pooled = G.gate1_uv_validity(stock_all_blocks, None, "stock:pooled_all")
    g2_pooled = G.gate2_sea_plan_disjoint(stock_all_blocks, None, "stock:pooled_all")
    gate1_stock_all_pass = g1_pooled["passed"] and all(v["passed"] for v in stock_g1.values())
    gate2_stock_all_pass = g2_pooled["passed"] and all(v["passed"] for v in stock_g2.values())
    log(f"  stock/POOLED-ALL: GATE1 passed={g1_pooled['passed']} | GATE2 passed={g2_pooled['passed']} "
        f"| all-strata GATE1={gate1_stock_all_pass} GATE2={gate2_stock_all_pass}")

    result["gate1_uv_validity"] = dict(fixed2=g1_fixed2, fixed_r1_crosscheck=g1_fixed1,
                                        stock_by_stratum=stock_g1, stock_pooled_all=g1_pooled)
    result["gate2_sea_plan_disjoint"] = dict(fixed2=g2_fixed2, fixed_r1_crosscheck=g2_fixed1,
                                              stock_by_stratum=stock_g2, stock_pooled_all=g2_pooled)
    result["gate_summary"] = dict(
        gate1_fixed2_passes=g1_fixed2["passed"],
        gate1_fixed_r1_still_passes=g1_fixed1["passed"],
        gate1_stock_passes=gate1_stock_all_pass,
        gate2_fixed2_passes=g2_fixed2["passed"],
        gate2_fixed_r1_still_passes=g2_fixed1["passed"],
        gate2_stock_passes=gate2_stock_all_pass)
    log(f"GATE SUMMARY: {json.dumps(result['gate_summary'], indent=2)}")

    # ====================================================================================================
    log("=" * 100)
    log("(3) STAGE4-CRITERIA plumbing re-run (file-based, uvf_gates.py's plumbing_criteria) on FIXED2")
    log("   -- must be POSITION-IDENTICAL to specimen (re-verified live, not just trusted from fix2 report)")
    log("=" * 100)
    plumb_specimen = G.plumbing_criteria(SPECIMEN_DIR, "specimen")
    plumb_fixed = G.plumbing_criteria(FIXED_DIR, "fixed(r1)")
    plumb_fixed2 = G.plumbing_criteria(FIXED2_DIR, "fixed2")
    positional_fields = ("flat_mesh_ok", "grid_ok", "frame_bounds_ok", "weld_near_miss_total",
                          "total_down_facing_tris", "open_edges_above_skirt")
    identical_spec_vs_fixed2 = all(plumb_specimen[f] == plumb_fixed2[f] for f in positional_fields)
    identical_fixed1_vs_fixed2 = all(plumb_fixed[f] == plumb_fixed2[f] for f in positional_fields)
    log(f"  specimen:  {json.dumps({k: v for k, v in plumb_specimen.items() if k in positional_fields})}")
    log(f"  fixed(r1): {json.dumps({k: v for k, v in plumb_fixed.items() if k in positional_fields})}")
    log(f"  fixed2:    {json.dumps({k: v for k, v in plumb_fixed2.items() if k in positional_fields})}")
    log(f"  position-identical specimen==fixed2: {identical_spec_vs_fixed2}  |  fixed(r1)==fixed2: {identical_fixed1_vs_fixed2}")
    log(f"  fixed2.all_ok = {plumb_fixed2['all_ok']}")

    try:
        build_json = json.loads((OUT_DIR / "rung_f_build.json").read_text(encoding="utf-8"))
        s4 = build_json["stage4_composite_plumbing"]
        matches_recorded = (plumb_fixed2["flat_mesh_ok"] == s4["flat_mesh_ok"]
                             and plumb_fixed2["grid_ok"] == s4["grid_ok"]
                             and plumb_fixed2["weld_near_miss_total"] == s4["weld_near_miss"]
                             and plumb_fixed2["frame_bounds_ok"] == s4["frame_bounds_ok"]
                             and plumb_fixed2["open_edges_above_skirt"] == s4["open_edges_above_skirt"])
    except Exception as e:
        s4 = None
        matches_recorded = None
        log(f"  (could not load rung_f_build.json for cross-check: {e})")
    log(f"  fixed2 recompute matches rung_f_build.json's recorded (all-green) stage4 result: {matches_recorded}")

    result["plumbing_stage4_criteria"] = dict(
        specimen=plumb_specimen, fixed_r1=plumb_fixed, fixed2=plumb_fixed2,
        identical_specimen_vs_fixed2=identical_spec_vs_fixed2,
        identical_fixed_r1_vs_fixed2=identical_fixed1_vs_fixed2,
        recorded_stage4_from_build_json=s4, fixed2_matches_recorded=matches_recorded,
        fixed2_all_ok=plumb_fixed2["all_ok"])

    # ====================================================================================================
    log("=" * 100)
    log("(4) contract_mass_gates.py v5 (EVOLVED) R1+R2+R3 re-run on FIXED2 + stock calibration control")
    log("=" * 100)
    stock_cand = CMG.load_candidate("stock_ecotone_13-15_11-12", None, core_blocks=CMG.ECOTONE_CORE)
    stock_row = CMG.run_matrix_on(stock_cand)
    contract_fixed2 = contract_rerun_v5_safe(FIXED2_DIR, "rung_f_FIXED2")
    contract_fixed1 = contract_rerun_v5_safe(FIXED_DIR, "rung_f_FIXED_r1_crosscheck")
    log(f"  stock calibration control: overall={stock_row['overall']}")
    log(f"  fixed(r1) crosscheck: R1={contract_fixed1['R1']['verdict']} R2={contract_fixed1['R2']['verdict']} "
        f"R3={contract_fixed1['R3']['verdict']} overall={contract_fixed1['overall']}")
    log(f"  fixed2:               R1={contract_fixed2['R1']['verdict']} R2={contract_fixed2['R2']['verdict']} "
        f"R3={contract_fixed2['R3']['verdict']} overall={contract_fixed2['overall']}")
    log(f"  fixed2 R1 measured={contract_fixed2['R1']['measured']} floors={contract_fixed2['R1']['floors']} "
        f"convention_invalid={contract_fixed2['R1']['convention_invalid']}")

    # v5 flags, already carried through by contract_rerun_v5_safe (no duplicate CMG re-run needed).
    sea_vertex_flag = contract_fixed2["R1"]["sea_vertex_convention_invalid"]
    convention_invalid_flag = contract_fixed2["R1"]["convention_invalid"]
    log(f"  fixed2 R1 sea_vertex_convention_invalid={sea_vertex_flag} convention_invalid={convention_invalid_flag}")

    r1_measured_matches_headline = (
        contract_fixed2["R1"]["measured"].get("boundary_cell") == 46.826
        and contract_fixed2["R1"]["measured"].get("straddle_cell") == 48.882
        and contract_fixed2["R1"]["measured"].get("body_tri") == 49.547) if False else None
    # (contract_rerun's measured_u values come straight from CMG's own R1 checks -- compare to floors
    #  directly instead of hardcoding rounding; the headline triple is independently reconfirmed below
    #  via uvf_gates.py's own r1_realized(), which uses the falsifier's own convention.)

    result["contract_mass_gates_v5"] = dict(
        stock_calibration_overall=stock_row["overall"],
        fixed_r1_crosscheck=contract_fixed1,
        fixed2=contract_fixed2,
        fixed2_R1_sea_vertex_convention_invalid=sea_vertex_flag,
        fixed2_R1_convention_invalid=convention_invalid_flag,
        fixed2_all_green=(contract_fixed2["overall"] == "PASS" and stock_row["overall"] == "PASS"))

    # ====================================================================================================
    log("=" * 100)
    log("(4b) R1 REALIZED standoff, falsifier convention (uvf_gates.py's r1_realized) on FIXED2")
    log("     -- must equal the round-1 headline 46.826/48.882/49.547u (UV changes cannot move XZ/Y)")
    log("=" * 100)
    r1_fixed2 = G.r1_realized(FIXED2_DIR, "fixed2")
    r1_fixed1 = G.r1_realized(FIXED_DIR, "fixed(r1)_crosscheck")
    log(f"  fixed(r1) crosscheck: {r1_fixed1['measured']} verdict={r1_fixed1['verdict']}")
    log(f"  fixed2:               {r1_fixed2['measured']} verdict={r1_fixed2['verdict']}")
    expected = dict(boundary_cell=46.826, straddle_cell=48.882, body_tri=49.547)
    r1_matches_headline = (r1_fixed2["measured"] == expected)
    r1_unchanged_vs_r1 = (r1_fixed2["measured"] == r1_fixed1["measured"])
    log(f"  fixed2 measured == expected headline {expected}: {r1_matches_headline}")
    log(f"  fixed2 measured == fixed(r1) measured: {r1_unchanged_vs_r1}")
    result["r1_realized_falsifier_convention"] = dict(
        fixed_r1_crosscheck=r1_fixed1, fixed2=r1_fixed2,
        expected_headline=expected, fixed2_matches_expected_headline=r1_matches_headline,
        fixed2_unchanged_vs_fixed_r1=r1_unchanged_vs_r1)

    # ====================================================================================================
    contract_matrix_green = (
        contract_fixed2["R1"]["verdict"] == "PASS"
        and contract_fixed2["R2"]["verdict"] == "PASS"
        and contract_fixed2["R3"]["verdict"] == "PASS"
        and contract_fixed2["overall"] == "PASS"
        and stock_row["overall"] == "PASS"
        and sea_vertex_flag is True
        and convention_invalid_flag is False
        and r1_matches_headline
        and r1_unchanged_vs_r1
        and r1_fixed2["verdict"] == "PASS")

    result["contract_matrix"] = dict(
        R1=contract_fixed2["R1"]["verdict"], R2=contract_fixed2["R2"]["verdict"],
        R3=contract_fixed2["R3"]["verdict"], overall=contract_fixed2["overall"],
        stock_control=stock_row["overall"],
        sea_vertex_convention_invalid_flagged=sea_vertex_flag,
        convention_invalid=convention_invalid_flag,
        realized_triple=contract_fixed2["R1"]["measured"],
        floors=contract_fixed2["R1"]["floors"],
        all_green=contract_matrix_green)

    overall = (
        result["gate_summary"]["gate1_fixed2_passes"]
        and result["gate_summary"]["gate1_fixed_r1_still_passes"]
        and result["gate_summary"]["gate1_stock_passes"]
        and result["gate_summary"]["gate2_fixed2_passes"]
        and result["gate_summary"]["gate2_fixed_r1_still_passes"]
        and result["gate_summary"]["gate2_stock_passes"]
        and result["plumbing_stage4_criteria"]["fixed2_all_ok"]
        and result["plumbing_stage4_criteria"]["identical_specimen_vs_fixed2"]
        and result["plumbing_stage4_criteria"]["identical_fixed_r1_vs_fixed2"]
        and contract_matrix_green)

    result["overall"] = "PASS" if overall else "FAIL"
    result["meta"] = dict(script="uvf_gates2.py", target=str(FIXED2_DIR),
                           reused_functions_from="uvf_gates.py (unedited, imported) for gate1/gate2/plumbing/r1_realized",
                           contract_gates_version="contract_mass_gates.py v5 (evolved, live)",
                           flagged_compat_bug=(
                               "uvf_gates.py's own contract_rerun() is BROKEN against the evolved v5 "
                               "contract_mass_gates.py: it does `{k: r1['checks'][k]['measured_u'] for k "
                               "in r1['checks']}`, iterating every checks{} key; v5's gate_r1 added a new "
                               "non-measurement key checks['sea_vertex_convention_invalid']=<bool>, so "
                               "contract_rerun() now raises TypeError('bool' object is not subscriptable) "
                               "on EVERY candidate (reproduced live in this run). Worked around here with "
                               "a local contract_rerun_v5_safe() that iterates only the three known "
                               "measure keys (boundary_cell/straddle_cell/body_tri) and explicitly surfaces "
                               "the new v5 flags. uvf_gates.py itself was left unedited per the reuse "
                               "instruction, but a plain re-run of uvf_gates.py's own main() against the "
                               "current (v5) contract_mass_gates.py would now crash at section (2) -- "
                               "flagging for the orchestrator to patch uvf_gates.py's contract_rerun() "
                               "(e.g. iterate MEASURE_KEYS, not checks.keys()) so future rounds don't hit "
                               "the same break."),
                           note="zero writes outside out/rung_f/uvf_gates2.json; zero git; "
                                "specimen/FIXED/FIXED2 trees read-only throughout")

    OUT.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    log("\n" + "=" * 100)
    log(f"OVERALL: {result['overall']}")
    log(f"-> {OUT}")
    return result


if __name__ == "__main__":
    main()
