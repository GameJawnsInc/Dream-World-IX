"""RUNG F -- THE ROOTS RELIEF RELAX (round 5) -- THE FULL VERIFICATION BATTERY on
FF9CustomMap-world-FIXED5.

FIXED5 (uvf_fix5.py) is the FIRST round in the Rung-F UV-fix arc that moves POSITIONS (Y only) rather
than UVs -- 923 coincident positions / 5557 vertex entries on 2202 of the 2305 synthesized tris, plus a
per-tri geometric-normal recompute on those same tris. Every prior round's gate suite (uvf_gates.py /
uvf_gates2-4.py) was built to certify a UV-only or Sea4-only change; this script re-derives the
PLUMBING lane FRESH (the critical lane this round, since geometry moved) and re-verifies the standing
texture gates are BYTE-UNCHANGED, not merely re-passing by coincidence.

SEVEN CHECKS:
  (1) STAGE4 PLUMBING re-run fresh on FIXED5 (flat-mesh / grid bounds / M.weld_audit per-block
      near-miss / frame bounds / down-facing-tri COUNT, gated against the baseline 3 -- not merely
      "still 0 NEW", the raw count must stay exactly 3 -- / open-edge watertight audit), crosschecked
      against FIXED4 and specimen/FIXED/FIXED2/FIXED3A for continuity.
  (2) A DEDICATED coincident-position WELD AUDIT, independently written (not calling uvf_fix5.py's own
      stage_verify): rebuilds every coincident-position group from disk BEFORE (FIXED4) and AFTER
      (FIXED5) across all 8 PARTS (Terrain/Object/Beach1/Sea1..Sea5) of all 20 touched blocks. A group
      that splits, or whose entries receive non-uniform deltas, is a crack -- required 0.
  (3) STANDING TEXTURE GATES, verified BYTE-UNCHANGED vs FIXED4 (UV bytes untouched by this round, so
      the ONE-WINDOW-PER-TRI / zero-uv-area / family-rect-membership invariants carry over by
      definition -- re-measured from FIXED5's own bytes, not inferred): GATE 1a zero-uv-area, the
      family-aware GATE 1c one-window-coherence (uvf_gates4.py's own mechanism, re-derived from FIXED4
      -- never trusted from a JSON report), family mains-rect membership, plus a direct UV-byte
      identity diff FIXED4 vs FIXED5.
  (4) GATE 2 SEA-PLAN-DISJOINT (A: no fully-submerged land tris) on FIXED5, PLUS a direct check that
      every one of the 923 moved positions individually stays above the 0.5u clearance floor and above
      Sea Y=0.
  (5) CONTRACT MATRIX v5 (R1+R2+R3) re-run on FIXED5 + FIXED4 crosscheck + the stock ecotone
      calibration control. R1's REALIZED standoff (rung_f_falsify.py's own land-perimeter convention)
      is XZ-only by construction (body_pts/boundary_pts/segs all keyed on (x,z), never y) -- so a
      Y-only move MUST leave it byte-unchanged; measured, not assumed. R2/R3 are diffed FIXED4->FIXED5
      the same way uvf_gates4.py diffed FIXED3A->FIXED4 for round 4's UV-only change.
  (6) BYTE-RIGIDITY vs FIXED4, POSITION/NORMAL-SCOPED: the expected-changed vertex set is re-derived
      HERE independently (not read from uvf_fix5_report.json) by resolving each of the 2305
      synthesized tris' vertices against FIXED4's PRE-move position keys and uvf_fix5.py's own
      re-executed stage_scope() solve (S["moved"]) -- mirroring uvf_fix5.py's PASS-1/PASS-3 resolution
      logic but written fresh, not imported. UV/tangent/index bytes must be identical everywhere;
      positions must differ ONLY at planned vids and ONLY in Y (never X/Z); normals must differ ONLY at
      the vids of a tri that received a moved vertex; only the 15 expected Terrain files may differ at
      all vs FIXED4 (Object/Beach/Sea* untouched, tree file count == 180).
  (7) ONLY EXPECTED FILES CHANGED -- full-tree sha256 diff FIXED4 vs FIXED5.

Writes only out/rung_f/uvf_gates5.json + this script. Zero git, zero install writes. FIXED4/FIXED5/
FIXED3A/specimen trees read-only throughout; uvf_fix5.py's stage_scope() re-executes the probe's
donor read (the same read-only install access every prior round in this arc has used and documented)
to re-derive the moved-position solve independently of the fix5 build's own report.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X            # noqa: E402
from ff9mapkit.world import mesh as M                # noqa: E402

import uvf_gates as G                # noqa: E402  -- gate1a/gate2/plumbing/contract_rerun/r1_realized
import uvf_gates4 as G4               # noqa: E402  -- family_window_coherence_check / family_rect_membership_check / build_reference_state
import uvf_stock_census as USC        # noqa: E402
import contract_mass_gates as CMG     # noqa: E402
import uvf_fix2 as F2                 # noqa: E402  -- terr_path
import uvf_fix3 as F3                 # noqa: E402  -- load_blocks
import uvf_fix5 as F5                 # noqa: E402  -- stage_scope (the round's own mechanism, re-executed)
import uvf_relief_probe as P          # noqa: E402  -- pkey / PARTS / POS_DP

OUT_DIR = HERE / "out" / "rung_f"
SPECIMEN_DIR = G.SPECIMEN_DIR
FIXED_DIR = G.FIXED_DIR
FIXED2_DIR = OUT_DIR / "FF9CustomMap-world-FIXED2"
FIXED3A_DIR = OUT_DIR / "FF9CustomMap-world-FIXED3A"
FIXED4_DIR = OUT_DIR / "FF9CustomMap-world-FIXED4"
FIXED5_DIR = OUT_DIR / "FF9CustomMap-world-FIXED5"
OUT = OUT_DIR / "uvf_gates5.json"

FOOTPRINT = G.FOOTPRINT
DOWN_FACING_BASELINE = 3           # pre-existing, unrelated down-facing tris measured on every prior round
N_FILES = 180
N_TERRAIN_DIRTY_EXPECTED = 15


def log(m):
    print(m, flush=True)


# ====================================================================================================
# RE-DERIVE round 5's own mechanism from disk (never trust uvf_fix5_report.json's claims) -- calls
# uvf_fix5.py's stage_scope() VERBATIM, which itself imports uvf_relief_probe's stage1..6 verbatim, so
# this is the same dry-run solve the build applied, re-executed independently of the build's report.
# ====================================================================================================
def build_reference_state_r5():
    dummy = {"meta": dict(reused_by="uvf_gates5.py")}
    S = F5.stage_scope(dummy)
    log(f"[ref-state-r5] touched={len(S['touched'])} defective={len(S['defective'])} "
        f"movable={len(S['movable'])} pinned={len(S['pinned'])} moved={len(S['moved'])}")

    # PASS-1/PASS-3 style resolution against FIXED4's PRE-move bytes (mirrors uvf_fix5.py's
    # stage_apply exactly, but re-derived here rather than imported, as an independent crosscheck)
    touched, synth_key, moved = S["touched"], S["synth_key"], S["moved"]
    meshes = F3.load_blocks(FIXED4_DIR, touched)
    plan = {b: {} for b in touched}
    nrm_changed = {b: set() for b in touched}
    moved_tris = {b: set() for b in touched}
    for b in touched:
        bm = meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts = bm.chan_arrays[F5.CH_POS]
        for t, tri in enumerate(bm.tris):
            if (b, t) not in synth_key:
                continue
            hit = False
            for j in tri:
                v = verts[j]
                k = P.pkey((v[0] + ox, v[1], v[2] + oz))
                dy = moved.get(k)
                if dy is not None:
                    plan[b][j] = dy
                    hit = True
            if hit:
                moved_tris[b].add(t)
                nrm_changed[b].update(tri)

    found_positions = set()
    for b in touched:
        bm = meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts = bm.chan_arrays[F5.CH_POS]
        for j, dy in plan[b].items():
            v = verts[j]
            found_positions.add(P.pkey((v[0] + ox, v[1], v[2] + oz)))
    missing_positions = set(moved) - found_positions
    n_vert_entries = sum(len(v) for v in plan.values())
    n_moved_tris = sum(len(v) for v in moved_tris.values())
    n_nrm_vids = sum(len(v) for v in nrm_changed.values())
    log(f"[ref-state-r5] independently-resolved plan: vertex_entries={n_vert_entries} "
        f"moved_tris={n_moved_tris} nrm_changed_vids={n_nrm_vids} "
        f"missing_positions={len(missing_positions)}")

    return dict(S=S, plan=plan, moved_tris=moved_tris, nrm_changed=nrm_changed,
                n_vert_entries=n_vert_entries, n_moved_tris=n_moved_tris, n_nrm_vids=n_nrm_vids,
                missing_positions=missing_positions)


# ====================================================================================================
# (1) STAGE4 PLUMBING re-run fresh -- FIXED5 must be all_ok, down-facing must stay at the BASELINE 3
#     (not merely "0 new"), and must be position-CONTINUOUS with the specimen/FIXED/.../FIXED4 chain
#     wherever this round's Y-move cannot have changed the measured field (flat/grid/frame/weld/
#     open-edge -- all topology/near-miss/bounds checks unaffected by a within-block Y shift); the
#     down-facing count is explicitly NOT asserted identical to the chain here (a Y move CAN in
#     principle change it) -- it is instead independently re-measured and gated against the baseline.
# ====================================================================================================
def run_plumbing_fresh():
    plumb_specimen = G.plumbing_criteria(SPECIMEN_DIR, "specimen")
    plumb_fixed1 = G.plumbing_criteria(FIXED_DIR, "fixed_r1")
    plumb_fixed2 = G.plumbing_criteria(FIXED2_DIR, "fixed2")
    plumb_fixed3a = G.plumbing_criteria(FIXED3A_DIR, "fixed3a")
    plumb_fixed4 = G.plumbing_criteria(FIXED4_DIR, "fixed4")
    plumb_fixed5 = G.plumbing_criteria(FIXED5_DIR, "fixed5")

    topology_fields = ("flat_mesh_ok", "grid_ok", "frame_bounds_ok", "weld_near_miss_total",
                        "open_edges_above_skirt")
    identical_topology = {name: all(p[f] == plumb_fixed5[f] for f in topology_fields)
                           for name, p in (("specimen", plumb_specimen), ("fixed_r1", plumb_fixed1),
                                           ("fixed2", plumb_fixed2), ("fixed3a", plumb_fixed3a),
                                           ("fixed4", plumb_fixed4))}
    down_facing_chain = {name: p["total_down_facing_tris"]
                          for name, p in (("specimen", plumb_specimen), ("fixed_r1", plumb_fixed1),
                                          ("fixed2", plumb_fixed2), ("fixed3a", plumb_fixed3a),
                                          ("fixed4", plumb_fixed4), ("fixed5", plumb_fixed5))}
    down_facing_at_baseline = (plumb_fixed5["total_down_facing_tris"] == DOWN_FACING_BASELINE)
    down_facing_unchanged_vs_fixed4 = (plumb_fixed5["total_down_facing_tris"]
                                        == plumb_fixed4["total_down_facing_tris"])

    log(f"  fixed5: flat={plumb_fixed5['flat_mesh_ok']} grid={plumb_fixed5['grid_ok']} "
        f"frame={plumb_fixed5['frame_bounds_ok']} weld_near_miss={plumb_fixed5['weld_near_miss_total']} "
        f"down_facing={plumb_fixed5['total_down_facing_tris']} (baseline {DOWN_FACING_BASELINE}) "
        f"open_edges={plumb_fixed5['open_edges_above_skirt']} all_ok={plumb_fixed5['all_ok']}")
    log(f"  topology fields identical to fixed5 across the whole chain: {identical_topology}")
    log(f"  down_facing chain: {down_facing_chain}")

    return dict(
        specimen=plumb_specimen, fixed_r1=plumb_fixed1, fixed2=plumb_fixed2, fixed3a=plumb_fixed3a,
        fixed4=plumb_fixed4, fixed5=plumb_fixed5,
        identical_topology_vs_chain=identical_topology,
        down_facing_chain=down_facing_chain,
        down_facing_baseline=DOWN_FACING_BASELINE,
        down_facing_at_baseline=down_facing_at_baseline,
        down_facing_unchanged_vs_fixed4=down_facing_unchanged_vs_fixed4,
        fixed5_all_ok=plumb_fixed5["all_ok"],
        passed=bool(plumb_fixed5["all_ok"] and all(identical_topology.values())
                    and down_facing_at_baseline and down_facing_unchanged_vs_fixed4))


# ====================================================================================================
# (2) DEDICATED coincident-position WELD AUDIT, independently written, over ALL 8 PARTS x 20 blocks,
#     FIXED4 (pre) vs FIXED5 (post) -- 0 splits, 0 non-uniform deltas required.
# ====================================================================================================
def weld_audit_all_parts(ref):
    S = ref["S"]
    plan = ref["plan"]
    touched = S["touched"]
    moved = S["moved"]

    pre_groups = defaultdict(list)     # pre poskey -> [(block, part, vid)]
    post_pos = {}                      # (block, part, vid) -> post poskey
    for b in touched:
        ox, oz = X.block_world_origin(*b)
        for part in P.PARTS:
            rel = M.override_relpath(1, b[0], b[1], part=part)
            p4, p5 = FIXED4_DIR / rel, FIXED5_DIR / rel
            if not p4.exists():
                continue
            d4 = M.read_ff9mesh(p4)
            d5 = M.read_ff9mesh(p5)
            if d4["vcount"] != d5["vcount"]:
                pre_groups["__VCOUNT_DRIFT__"].append((b, part, -1))
                continue
            for j in range(d4["vcount"]):
                a, c = d4["verts"][j], d5["verts"][j]
                pre_groups[P.pkey((a[0] + ox, a[1], a[2] + oz))].append((b, part, j))
                post_pos[(b, part, j)] = P.pkey((c[0] + ox, c[1], c[2] + oz))

    split = []
    nonuniform = []
    groups_moved = 0
    cross_block = 0
    cross_part = 0
    for k, ents in pre_groups.items():
        if k == "__VCOUNT_DRIFT__":
            continue
        outs = {post_pos[e] for e in ents}
        if len(outs) != 1:
            split.append(dict(pre=list(k), n_entries=len(ents), post=[list(o) for o in sorted(outs)]))
            continue
        if next(iter(outs)) != k:
            groups_moved += 1
            if len({e[0] for e in ents}) > 1:
                cross_block += 1
            if len({e[1] for e in ents}) > 1:
                cross_part += 1
        deltas = set()
        for (b, part, j) in ents:
            dy = plan[b].get(j, 0.0) if part == "Terrain" else 0.0
            deltas.add(round(dy, 6))
        if len(deltas) != 1:
            nonuniform.append(dict(pre=list(k), n_entries=len(ents), deltas=sorted(deltas)))

    sub_key = [k for k, dv in moved.items() if abs(dv) < 0.5 * 10 ** (-P.POS_DP)]
    vcount_drift = len(pre_groups.get("__VCOUNT_DRIFT__", []))
    reconciled = (groups_moved + len(sub_key) == len(moved))

    result = dict(
        n_distinct_positions_all_parts=len(pre_groups) - (1 if vcount_drift else 0),
        vcount_drift_files=vcount_drift,
        groups_that_split=len(split), split_examples=split[:10],
        groups_with_nonuniform_delta=len(nonuniform), nonuniform_examples=nonuniform[:10],
        groups_that_moved_by_key=groups_moved,
        solver_moved_positions=len(moved),
        moved_below_position_key_resolution=len(sub_key),
        moved_groups_reconcile=reconciled,
        multi_entry_groups_moved=sum(1 for k in moved if len(pre_groups.get(k, ())) > 1),
        cross_block_groups_moved=cross_block,
        cross_part_groups_moved=cross_part,
        ok=bool(vcount_drift == 0 and not split and not nonuniform and reconciled))
    log(f"  weld audit: positions={result['n_distinct_positions_all_parts']} "
        f"split={result['groups_that_split']} nonuniform={result['groups_with_nonuniform_delta']} "
        f"moved_by_key={groups_moved} sub_key={len(sub_key)} reconciled={reconciled} "
        f"cross_block={cross_block} cross_part={cross_part} ok={result['ok']}")
    return result


# ====================================================================================================
# (3) STANDING TEXTURE GATES, re-measured on FIXED5, verified BYTE-UNCHANGED vs FIXED4
# ====================================================================================================
def texture_gates_unchanged():
    tex_ref = G4.build_reference_state()   # re-derives family/window field from FIXED3A/FIXED4 disk bytes

    g1_fixed5 = G.gate1_uv_validity(FOOTPRINT, FIXED5_DIR, "fixed5")
    g1_fixed4 = G.gate1_uv_validity(FOOTPRINT, FIXED4_DIR, "fixed4_crosscheck")
    log(f"  GATE1a fixed5: zero_uv_frac={g1_fixed5['zero_uv_area_frac']} "
        f"bit_identical={g1_fixed5['total_bit_identical']} passed={g1_fixed5['passed']}")

    wc_fixed5 = G4.family_window_coherence_check(FIXED5_DIR, "fixed5", tex_ref)
    wc_fixed4 = G4.family_window_coherence_check(FIXED4_DIR, "fixed4_crosscheck", tex_ref)
    log(f"  GATE1c fixed5: n={wc_fixed5['n_tris']} single={wc_fixed5['single_window_reconstructed']} "
        f"multi={wc_fixed5['multi_window_or_unreconstructed']} frac={wc_fixed5['multi_window_frac']} "
        f"per_family={wc_fixed5['per_family']} passed={wc_fixed5['passed']}")
    gate1c_identical_to_fixed4 = (
        wc_fixed5["single_window_reconstructed"] == wc_fixed4["single_window_reconstructed"]
        and wc_fixed5["multi_window_or_unreconstructed"] == wc_fixed4["multi_window_or_unreconstructed"]
        and wc_fixed5["per_family"] == wc_fixed4["per_family"])

    rect_fixed5 = G4.family_rect_membership_check(FIXED5_DIR, "fixed5", tex_ref)
    rect_fixed4 = G4.family_rect_membership_check(FIXED4_DIR, "fixed4_crosscheck", tex_ref)
    log(f"  family rect membership fixed5: {rect_fixed5['out_of_region_by_family']} "
        f"zero_area={rect_fixed5['zero_area_by_family']} passed={rect_fixed5['passed']}")
    rect_identical_to_fixed4 = (rect_fixed5["out_of_region_by_family"] == rect_fixed4["out_of_region_by_family"]
                                 and rect_fixed5["zero_area_by_family"] == rect_fixed4["zero_area_by_family"]
                                 and rect_fixed5["tris_checked_by_family"] == rect_fixed4["tris_checked_by_family"])

    # direct UV-byte identity, FIXED4 vs FIXED5, over all 20 touched blocks
    uv_diffs = 0
    for (bx, by) in FOOTPRINT:
        a = M.read_ff9mesh(F2.terr_path(FIXED4_DIR, bx, by))
        f = M.read_ff9mesh(F2.terr_path(FIXED5_DIR, bx, by))
        for j in range(a["vcount"]):
            if a["uvs"][j] != f["uvs"][j]:
                uv_diffs += 1
    log(f"  direct UV-byte diff FIXED4 vs FIXED5: {uv_diffs} (must be 0 -- round 5 is Y/normal-only)")

    passed = bool(g1_fixed5["passed"] and wc_fixed5["passed"] and rect_fixed5["passed"]
                  and gate1c_identical_to_fixed4 and rect_identical_to_fixed4 and uv_diffs == 0)
    return dict(gate1a_fixed5=g1_fixed5, gate1a_fixed4_crosscheck=g1_fixed4,
                gate1c_fixed5=wc_fixed5, gate1c_fixed4_crosscheck=wc_fixed4,
                gate1c_identical_to_fixed4=gate1c_identical_to_fixed4,
                family_rect_fixed5=rect_fixed5, family_rect_fixed4_crosscheck=rect_fixed4,
                family_rect_identical_to_fixed4=rect_identical_to_fixed4,
                uv_byte_diffs_fixed4_vs_fixed5=uv_diffs,
                passed=passed)


# ====================================================================================================
# (4) GATE 2 SEA-PLAN-DISJOINT on FIXED5 + explicit per-moved-position clearance check
# ====================================================================================================
def sea_gate_and_clearance(ref):
    g2_fixed5 = G.gate2_sea_plan_disjoint(FOOTPRINT, FIXED5_DIR, "fixed5")
    g2_fixed4 = G.gate2_sea_plan_disjoint(FOOTPRINT, FIXED4_DIR, "fixed4_crosscheck")
    log(f"  GATE2 fixed5: A(y-order) viol={g2_fixed5['A_y_order']['fully_submerged_tris_GATING']} "
        f"passed={g2_fixed5['A_y_order']['passed']} | B={g2_fixed5['B_uniformity']['passed']} | "
        f"C={g2_fixed5['C_real_sea_disjoint']['passed']} | overall={g2_fixed5['passed']}")

    S = ref["S"]
    rows = S["rows"]
    moved = S["moved"]
    by_key = {r["k"]: r for r in rows}
    moved_y_after = {k: by_key[k]["y"] + dv for k, dv in moved.items() if k in by_key}
    below_floor = {k: y for k, y in moved_y_after.items() if y <= 0.5}
    at_or_below_sea = {k: y for k, y in moved_y_after.items() if y <= 0.0}
    min_moved_y = min(moved_y_after.values()) if moved_y_after else None
    log(f"  moved-position clearance: n={len(moved_y_after)} min_Y_after={min_moved_y} "
        f"below_0.5_floor={len(below_floor)} at_or_below_sea={len(at_or_below_sea)}")

    passed = bool(g2_fixed5["passed"] and not below_floor and not at_or_below_sea)
    return dict(gate2_fixed5=g2_fixed5, gate2_fixed4_crosscheck=g2_fixed4,
                moved_position_clearance=dict(
                    n_moved=len(moved_y_after), min_Y_after=min_moved_y,
                    below_0p5_floor=len(below_floor), at_or_below_sea_y0=len(at_or_below_sea),
                    sample_below_floor=list(below_floor.items())[:5]),
                passed=passed)


# ====================================================================================================
# (5) CONTRACT MATRIX v5 -- R1+R2+R3 on FIXED5 + FIXED4 crosscheck + stock calibration control
# ====================================================================================================
def contract_matrix():
    stock_cand = CMG.load_candidate("stock_ecotone_13-15_11-12", None, core_blocks=CMG.ECOTONE_CORE)
    stock_row = CMG.run_matrix_on(stock_cand)

    contract_fixed5 = G.contract_rerun(FIXED5_DIR, "rung_f_FIXED5")
    contract_fixed4 = G.contract_rerun(FIXED4_DIR, "rung_f_FIXED4_crosscheck")
    log(f"  stock calibration control: overall={stock_row['overall']}")
    log(f"  fixed4: R1={contract_fixed4['R1']['verdict']} R2={contract_fixed4['R2']['verdict']} "
        f"R3={contract_fixed4['R3']['verdict']} overall={contract_fixed4['overall']}")
    log(f"  fixed5: R1={contract_fixed5['R1']['verdict']} R2={contract_fixed5['R2']['verdict']} "
        f"R3={contract_fixed5['R3']['verdict']} overall={contract_fixed5['overall']}")
    log(f"  fixed5 R1 measured={contract_fixed5['R1']['measured']} floors={contract_fixed5['R1']['floors']}")

    sea_vertex_flag = contract_fixed5["R1"]["sea_vertex_convention_invalid"]
    convention_invalid_flag = contract_fixed5["R1"]["convention_invalid"]
    expected_floors = dict(boundary_cell=39.953, straddle_cell=44.635, body_tri=42.968)
    floors_match = all(abs(contract_fixed5["R1"]["floors"].get(k, -1) - v) < 0.01
                        for k, v in expected_floors.items())
    r1_unchanged_vs_fixed4 = (contract_fixed5["R1"]["measured"] == contract_fixed4["R1"]["measured"])

    expected_headline = dict(boundary_cell=46.826, straddle_cell=48.882, body_tri=49.547)
    # contract_rerun's R1 "measured" is the contract gate's OWN internal metric (not necessarily
    # identical in convention to r1_realized()'s falsifier metric below) -- check both independently.

    r2_5, r2_4 = contract_fixed5["R2"], contract_fixed4["R2"]
    r3_5, r3_4 = contract_fixed5["R3"], contract_fixed4["R3"]
    r2_keys = ("sat_grass", "sat_any", "fringe", "penetration", "floating")
    r3_keys = ("reachable_backing", "interface", "erosion")
    r2_diff = {k: dict(fixed4=r2_4[k], fixed5=r2_5[k], moved=(r2_4[k] != r2_5[k])) for k in r2_keys}
    r3_diff = {k: dict(fixed4=r3_4[k], fixed5=r3_5[k], moved=(r3_4[k] != r3_5[k])) for k in r3_keys}
    r2_any_moved = any(v["moved"] for v in r2_diff.values())
    r3_any_moved = any(v["moved"] for v in r3_diff.values())
    log(f"  R2 diff fixed4->fixed5: {r2_diff}  any_moved={r2_any_moved}")
    log(f"  R3 diff fixed4->fixed5: {r3_diff}  any_moved={r3_any_moved}")

    # -----------------------------------------------------------------------
    # R1 REALIZED, falsifier convention (rung_f_falsify.py, XZ-only by construction)
    r1_fixed5 = G.r1_realized(FIXED5_DIR, "fixed5")
    r1_fixed4 = G.r1_realized(FIXED4_DIR, "fixed4_crosscheck")
    r1_matches_headline = (r1_fixed5["measured"] == expected_headline)
    r1_unchanged_falsifier = (r1_fixed5["measured"] == r1_fixed4["measured"])
    log(f"  R1 REALIZED fixed5: {r1_fixed5['measured']} verdict={r1_fixed5['verdict']} "
        f"matches_headline={r1_matches_headline} unchanged_vs_fixed4={r1_unchanged_falsifier}")

    contract_matrix_green = (
        contract_fixed5["R1"]["verdict"] == "PASS"
        and contract_fixed5["R2"]["verdict"] == "PASS"
        and contract_fixed5["R3"]["verdict"] == "PASS"
        and contract_fixed5["overall"] == "PASS"
        and stock_row["overall"] == "PASS"
        and sea_vertex_flag is True
        and convention_invalid_flag is False
        and floors_match
        and r1_matches_headline
        and r1_unchanged_falsifier
        and r1_fixed5["verdict"] == "PASS")

    return dict(
        stock_calibration_overall=stock_row["overall"],
        fixed4_crosscheck=contract_fixed4, fixed5=contract_fixed5,
        fixed5_R1_sea_vertex_convention_invalid=sea_vertex_flag,
        fixed5_R1_convention_invalid=convention_invalid_flag,
        floors_match_expected=floors_match,
        R1_gate_metric_unchanged_vs_fixed4=r1_unchanged_vs_fixed4,
        R2_diff_fixed4_vs_fixed5=r2_diff, R2_any_number_moved=r2_any_moved,
        R3_diff_fixed4_vs_fixed5=r3_diff, R3_any_number_moved=r3_any_moved,
        r1_realized_fixed5=r1_fixed5, r1_realized_fixed4_crosscheck=r1_fixed4,
        r1_realized_expected_headline=expected_headline,
        r1_realized_matches_headline=r1_matches_headline,
        r1_realized_unchanged_vs_fixed4=r1_unchanged_falsifier,
        contract_matrix_green=contract_matrix_green,
        passed=bool(contract_matrix_green and not r2_any_moved and not r3_any_moved
                    and r1_unchanged_vs_fixed4))


# ====================================================================================================
# (6) BYTE-RIGIDITY vs FIXED4, POSITION/NORMAL-SCOPED (expected set re-derived independently in
#     build_reference_state_r5, above) + (7) ONLY-EXPECTED-FILES full-tree diff
# ====================================================================================================
def byte_rigidity_and_tree_diff(ref):
    S = ref["S"]
    touched = S["touched"]
    plan = ref["plan"]
    nrm_changed = ref["nrm_changed"]

    rig = dict(uv_bad=0, tan_bad=0, idx_bad=0, vcount_bad=0,
               pos_expected_changed=0, pos_expected_missing=0, pos_unexpected=0,
               pos_xz_moved=0, pos_y_delta_bad=0,
               nrm_expected_changed=0, nrm_unexpected=0)
    per_block = {}
    for b in touched:
        a = M.read_ff9mesh(F2.terr_path(FIXED4_DIR, *b))
        f = M.read_ff9mesh(F2.terr_path(FIXED5_DIR, *b))
        rig["uv_bad"] += (a["uvs"] != f["uvs"])
        rig["tan_bad"] += (a["tangents"] != f["tangents"])
        rig["idx_bad"] += (a["indices"] != f["indices"])
        rig["vcount_bad"] += (a["vcount"] != f["vcount"])
        planned = plan[b]
        nchg = nrm_changed[b]
        blk_unexp = blk_exp = blk_bad_delta = 0
        for j in range(a["vcount"]):
            ay, fy = a["verts"][j], f["verts"][j]
            changed = (ay != fy)
            if j in planned:
                actual_dy = fy[1] - ay[1]
                if abs(actual_dy - planned[j]) > 1e-3:
                    rig["pos_y_delta_bad"] += 1
                    blk_bad_delta += 1
                if changed:
                    rig["pos_expected_changed"] += 1
                    blk_exp += 1
                else:
                    rig["pos_expected_missing"] += 1
            elif changed:
                rig["pos_unexpected"] += 1
                blk_unexp += 1
            if changed and (ay[0] != fy[0] or ay[2] != fy[2]):
                rig["pos_xz_moved"] += 1
            if a["normals"][j] != f["normals"][j]:
                if j in nchg:
                    rig["nrm_expected_changed"] += 1
                else:
                    rig["nrm_unexpected"] += 1
        if blk_unexp or blk_bad_delta:
            per_block[f"{b[0]},{b[1]}"] = dict(unexpected_pos=blk_unexp, bad_delta=blk_bad_delta,
                                                expected=blk_exp)
    rig["pos_expected_total"] = ref["n_vert_entries"]
    rig["nrm_expected_total"] = ref["n_nrm_vids"]

    rigidity_ok = bool(
        rig["uv_bad"] == 0 and rig["tan_bad"] == 0 and rig["idx_bad"] == 0 and rig["vcount_bad"] == 0
        and rig["pos_unexpected"] == 0 and rig["pos_xz_moved"] == 0 and rig["pos_y_delta_bad"] == 0
        and rig["pos_expected_missing"] == 0
        and rig["nrm_unexpected"] == 0
        and rig["pos_expected_changed"] == rig["pos_expected_total"]
        and rig["nrm_expected_changed"] == rig["nrm_expected_total"])
    log(f"  rigidity: {rig}  ok={rigidity_ok}")

    # (7) full-tree sha diff FIXED4 vs FIXED5 -- only the 15 dirty Terrain files
    import hashlib
    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()
    changed = []
    n4 = n5 = 0
    for p in sorted(FIXED4_DIR.rglob("*")):
        if p.is_file():
            n4 += 1
            rel = p.relative_to(FIXED4_DIR)
            other = FIXED5_DIR / rel
            if not other.exists() or sha(p) != sha(other):
                changed.append(str(rel))
    for p in FIXED5_DIR.rglob("*"):
        if p.is_file():
            n5 += 1
    expected_files = {str(F2.terr_path(FIXED4_DIR, *b).relative_to(FIXED4_DIR)) for b in touched
                       if b in ref["plan"] and ref["plan"][b]}
    tree_diff = dict(
        n_files_fixed4=n4, n_files_fixed5=n5, n_changed=len(changed), changed_files=changed,
        n_terrain_changed=sum(1 for r in changed if "Terrain" in r),
        n_non_terrain_changed=sum(1 for r in changed if "Terrain" not in r),
        unexpected=[r for r in changed if r not in expected_files],
        expected_not_changed=[r for r in expected_files if r not in changed],
        matches_expected_count=(len(changed) == N_TERRAIN_DIRTY_EXPECTED == len(expected_files)),
        both_trees_180_files=(n4 == N_FILES and n5 == N_FILES))
    log(f"  tree diff: {len(changed)} files changed (expect {N_TERRAIN_DIRTY_EXPECTED} Terrain-only); "
        f"unexpected={tree_diff['unexpected']} expected_not_changed={tree_diff['expected_not_changed']}")

    tree_diff_ok = bool(tree_diff["matches_expected_count"] and not tree_diff["unexpected"]
                         and not tree_diff["expected_not_changed"] and tree_diff["n_non_terrain_changed"] == 0
                         and tree_diff["both_trees_180_files"])

    return dict(byte_rigidity=dict(counts=rig, per_block_anomalies=per_block, passed=rigidity_ok),
                tree_diff=tree_diff, tree_diff_passed=tree_diff_ok,
                passed=bool(rigidity_ok and tree_diff_ok))


# ====================================================================================================
def main():
    assert FIXED5_DIR.exists(), f"missing target tree: {FIXED5_DIR}"
    result = {}

    log("=" * 100)
    log("(0) RE-DERIVE round 5's mechanism from disk (uvf_fix5.py stage_scope, re-executed)")
    log("=" * 100)
    ref = build_reference_state_r5()
    result["reference_state"] = dict(
        n_touched=len(ref["S"]["touched"]), n_defective=len(ref["S"]["defective"]),
        n_movable=len(ref["S"]["movable"]), n_pinned=len(ref["S"]["pinned"]),
        n_moved_positions=len(ref["S"]["moved"]),
        n_vert_entries_resolved=ref["n_vert_entries"], n_moved_tris_resolved=ref["n_moved_tris"],
        n_nrm_vids_resolved=ref["n_nrm_vids"],
        n_missing_positions=len(ref["missing_positions"]),
        resolution_matches_solver_count=(len(ref["missing_positions"]) == 0))

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(1) STAGE4 PLUMBING re-run FRESH on FIXED5 -- the critical lane this round (geometry moved)")
    log("=" * 100)
    plumbing = run_plumbing_fresh()
    result["plumbing_stage4_criteria"] = plumbing

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(2) DEDICATED coincident-position WELD AUDIT across parts + block borders (independent)")
    log("=" * 100)
    weld = weld_audit_all_parts(ref)
    result["weld_audit_all_parts"] = weld

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(3) STANDING TEXTURE GATES, re-measured + verified byte-unchanged vs FIXED4")
    log("=" * 100)
    tex = texture_gates_unchanged()
    result["standing_texture_gates"] = tex

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(4) GATE 2 SEA-PLAN-DISJOINT + per-moved-position clearance")
    log("=" * 100)
    sea = sea_gate_and_clearance(ref)
    result["gate2_sea_and_clearance"] = sea

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(5) CONTRACT MATRIX v5 (R1+R2+R3) + stock calibration control")
    log("=" * 100)
    contract = contract_matrix()
    result["contract_mass_gates_v5"] = contract

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(6)+(7) BYTE-RIGIDITY vs FIXED4 (position/normal-scoped) + only-expected-files tree diff")
    log("=" * 100)
    rig = byte_rigidity_and_tree_diff(ref)
    result["byte_rigidity_and_tree_diff"] = rig

    # ====================================================================================================
    gate_summary = dict(
        reference_state_resolves_cleanly=result["reference_state"]["resolution_matches_solver_count"],
        plumbing_fixed5_all_ok=plumbing["fixed5_all_ok"],
        plumbing_topology_identical_vs_chain=all(plumbing["identical_topology_vs_chain"].values()),
        plumbing_down_facing_at_baseline=plumbing["down_facing_at_baseline"],
        plumbing_down_facing_unchanged_vs_fixed4=plumbing["down_facing_unchanged_vs_fixed4"],
        weld_audit_zero_cracks=weld["ok"],
        texture_gates_pass_and_unchanged=tex["passed"],
        gate2_sea_passes_and_clearance_ok=sea["passed"],
        contract_matrix_green=contract["passed"],
        byte_rigidity_and_tree_diff_ok=rig["passed"])
    result["gate_summary"] = gate_summary
    log(f"GATE SUMMARY: {json.dumps(gate_summary, indent=2)}")

    overall = all(gate_summary.values())
    result["overall"] = "PASS" if overall else "FAIL"
    result["meta"] = dict(
        script="uvf_gates5.py", target=str(FIXED5_DIR), base=str(FIXED4_DIR),
        reused_functions_from=(
            "uvf_gates.py (gate1_uv_validity/gate2_sea_plan_disjoint/plumbing_criteria/contract_rerun/"
            "r1_realized, verbatim); uvf_gates4.py (build_reference_state/family_window_coherence_check/"
            "family_rect_membership_check, verbatim); uvf_fix5.py (stage_scope, the round's own "
            "mechanism, re-executed fresh against on-disk FIXED4 bytes + the donor -- not the JSON "
            "report); uvf_fix3.py (load_blocks); uvf_relief_probe.py (pkey/PARTS/POS_DP)"),
        new_this_round=("run_plumbing_fresh (down-facing baseline gate + full-chain topology "
                        "continuity), weld_audit_all_parts (independent cross-part/cross-block weld "
                        "re-derivation, not calling uvf_fix5.py's own stage_verify), "
                        "texture_gates_unchanged (byte-unchanged crosscheck vs FIXED4 + direct UV-byte "
                        "diff), sea_gate_and_clearance (per-moved-position clearance), contract_matrix "
                        "(R1 gate-metric + R1-realized-falsifier + R2/R3 diffs vs FIXED4), "
                        "byte_rigidity_and_tree_diff (position/normal-scoped rigidity, expected set "
                        "independently resolved in build_reference_state_r5)"),
        contract_gates_version="contract_mass_gates.py v5 (evolved, live)",
        note=("zero writes outside out/rung_f/uvf_gates5.json; zero git; FIXED4/FIXED5/FIXED3A/FIXED2/"
              "FIXED/specimen trees read-only throughout; the stock ecotone calibration read + "
              "uvf_fix5.py's stage_scope() donor read are the same read-only install access every "
              "prior round in this arc has used and documented"))

    OUT.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    log("\n" + "=" * 100)
    log(f"OVERALL: {result['overall']}")
    log(f"-> {OUT}")
    return result


if __name__ == "__main__":
    main()
