"""RUNG F -- THE CARRIED-SPIKE SHAVE (round 6) -- THE FULL VERIFICATION BATTERY on
FF9CustomMap-world-FIXED6.

FIXED6 (uvf_fix6.py) is the SECOND round in the Rung-F arc to move POSITIONS (Y only), and the FIRST
round ever to move CARRIED (kept, donor) geometry rather than only synthesized fill.  Round 5's own
gate suite (uvf_gates5.py) was built to certify "every synthesized-fill vertex may move, every carried
vertex is Dirichlet-pinned" -- that is no longer the invariant.  This script re-derives the round's own
mechanism FRESH from disk (calling uvf_fix6.py's stage1..stage4 verbatim, never trusting
uvf_fix6_report.json's claims) and adds the ONE check round 5's suite structurally could not need: that
the contract change is SCOPED -- carried geometry outside the census-defined spike set is still
byte-rigid, exactly as it was under round 5's rule.

EIGHT CHECKS:
  (1) STAGE4 PLUMBING re-run fresh on FIXED6 (flat-mesh / grid bounds / weld near-miss / frame bounds /
      down-facing-tri COUNT gated against the baseline 3, not merely "0 new" / open-edge watertight),
      crosschecked for topology continuity against the whole specimen->FIXED5 chain.
  (2) A DEDICATED coincident-position WELD AUDIT, independently written (does not call uvf_fix6.py's own
      stage_verify): rebuilds every coincident-position group from disk BEFORE (FIXED5) and AFTER
      (FIXED6) across all 8 PARTS of all 20 touched blocks. A group that splits, or whose entries receive
      a non-uniform delta, is a crack -- required 0.
  (3) STANDING TEXTURE GATES, re-measured on FIXED6 and verified BYTE-UNCHANGED vs FIXED5 (round 6 writes
      no UV byte -- GATE 1a zero-uv-area, the family-aware GATE 1c one-window-coherence, family
      mains-rect membership, plus a direct UV-byte identity diff FIXED5 vs FIXED6).
  (4) GATE 2 SEA-PLAN-DISJOINT on FIXED6, plus a direct per-moved-position clearance check (every one of
      the 12 moved positions individually above the 0.5u floor and above Sea Y=0).
  (5) CONTRACT MATRIX v5 (R1+R2+R3) re-run on FIXED6 + FIXED5 crosscheck + the stock ecotone calibration
      control. R1's REALIZED standoff is XZ-only by construction and every moved position in round 6 sits
      >=12u inside the interior (12.019u is the closest spike to the crater centre, itself >>1.5u from
      any coast) -- so a Y-only, interior-only move MUST leave it byte-unchanged; measured, not assumed.
  (6) BYTE-RIGIDITY vs FIXED5, POSITION/NORMAL-SCOPED: the expected-changed vertex set is re-derived HERE
      independently by resolving uvf_fix6.py's OWN stage1-4 (re-executed fresh, not read from the JSON
      report) against FIXED5's pre-move bytes -- mirroring uvf_fix6.py's stage_apply PASS-1/PASS-3
      resolution logic but written fresh. UV/tangent/index bytes must be identical everywhere; positions
      must differ ONLY at planned vids and ONLY in Y; normals must differ ONLY at the vids of a tri that
      received a moved vertex; only the 3 expected Terrain files may differ at all vs FIXED5.
  (7) THE SCOPE GATE (new this round): every KEPT (carried, non-synthesized) triangle in the 20-block
      footprint that does NOT touch a census-defined spike position is required to be BYTE-IDENTICAL
      (position AND normal) between FIXED5 and FIXED6 -- proving the round's contract change ("carried
      positions MAY move, but ONLY the spike set") was actually honoured and not merely asserted. The
      complementary direction is checked too: every kept tri that DID change must touch a spike. A
      companion check does the same for synthesized/fill tris outside the harmonic patch (Q["Ul"]).
  (8) ONLY EXPECTED FILES CHANGED -- full-tree sha256 diff FIXED5 vs FIXED6 (3 Terrain files, 0 elsewhere,
      180 files present in both trees).

Writes only out/rung_f/uvf_gates6.json + this script. Zero git, zero install writes. specimen/FIXED../
FIXED5/FIXED6 trees read-only throughout; uvf_fix6.py's stage1-4 re-executes the same read-only donor +
fix5-report reads every prior round in this arc has used and documented.
"""
from __future__ import annotations

import json
import math
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
import contract_mass_gates as CMG     # noqa: E402
import uvf_fix2 as F2                 # noqa: E402  -- terr_path / uv_degenerate
import uvf_fix3 as F3                 # noqa: E402  -- load_blocks
import uvf_fix6 as F6                 # noqa: E402  -- stage1/2/3/4 (the round's own mechanism, re-executed)
import uvf_relief_probe as P          # noqa: E402  -- pkey / PARTS / POS_DP

OUT_DIR = HERE / "out" / "rung_f"
SPECIMEN_DIR = G.SPECIMEN_DIR
FIXED_DIR = G.FIXED_DIR
FIXED2_DIR = OUT_DIR / "FF9CustomMap-world-FIXED2"
FIXED3A_DIR = OUT_DIR / "FF9CustomMap-world-FIXED3A"
FIXED4_DIR = OUT_DIR / "FF9CustomMap-world-FIXED4"
FIXED5_DIR = OUT_DIR / "FF9CustomMap-world-FIXED5"
FIXED6_DIR = OUT_DIR / "FF9CustomMap-world-FIXED6"
OUT = OUT_DIR / "uvf_gates6.json"

FOOTPRINT = G.FOOTPRINT
DOWN_FACING_BASELINE = 3           # pre-existing, unrelated down-facing tris measured on every prior round
N_FILES = 180
N_TERRAIN_DIRTY_EXPECTED = 3       # round 6's own report: 3 files, all Terrain, all Disc1


def log(m):
    print(m, flush=True)


# ====================================================================================================
# (0) RE-DERIVE round 6's own mechanism from disk (never trust uvf_fix6_report.json's claims) -- calls
#     uvf_fix6.py's stage1..stage4 VERBATIM (the same functions the build itself runs), so this is the
#     identical solve re-executed independently of the build's own report, plus a fresh PASS-1/PASS-3
#     style resolution against FIXED5's PRE-move bytes (mirrors uvf_fix6.py's stage_apply exactly, but
#     re-derived here rather than imported).
# ====================================================================================================
def build_reference_state_r6():
    rpt = {"meta": dict(reused_by="uvf_gates6.py")}
    S = F6.stage1(rpt)
    R = F6.stage2(rpt, S)
    C = F6.stage3(rpt, S, R)
    Q = F6.stage4(rpt, S, R, C)
    moved = Q["moved"]
    spikes = set(C["spikes"])
    log(f"[ref-state-r6] spikes={len(spikes)} sites={len(C['sites'])} unknowns={len(Q['Ul'])} "
        f"moved_positions={len(moved)}")

    on_disk = json.loads((OUT_DIR / "uvf_fix6_report.json").read_text(encoding="utf-8"))
    disk_moved = {tuple(round(v, P.POS_DP) for v in row["world"]): row["dY"]
                  for row in on_disk["stage4_solve"]["result"]["spike_moves"]}
    disk_moved.update({tuple(round(v, P.POS_DP) for v in row["world"]): row["dY"]
                       for row in on_disk["stage4_solve"]["result"]["fill_moves"]})
    # the report itself rounds world keys AND dY to P.POS_DP=3 places (uvf_fix6.py stage4's `round(.., 3)`
    # in its result rows) -- so the comparison tolerance must be half that rounding step, not float noise.
    reproduced_identical = (
        len(disk_moved) == len(moved)
        and all(k in moved and abs(moved[k] - dv) < 0.5 * 10 ** (-P.POS_DP) for k, dv in disk_moved.items()))
    log(f"[ref-state-r6] re-executed solve reproduces uvf_fix6_report.json's own moved set: "
        f"{reproduced_identical} (disk n={len(disk_moved)}, re-derived n={len(moved)})")

    touched, synth_key = S["touched"], S["synth_key"]
    meshes = F3.load_blocks(FIXED5_DIR, touched)
    plan = {b: {} for b in touched}
    nrm_changed = {b: set() for b in touched}
    moved_tris = {b: set() for b in touched}
    moved_tris_kept = {b: set() for b in touched}
    for b in touched:
        bm = meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts = bm.chan_arrays[F6.CH_POS]
        for t, tri in enumerate(bm.tris):
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
                if (b, t) not in synth_key:
                    moved_tris_kept[b].add(t)

    found_positions = set()
    for b in touched:
        bm = meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts = bm.chan_arrays[F6.CH_POS]
        for j, dy in plan[b].items():
            v = verts[j]
            found_positions.add(P.pkey((v[0] + ox, v[1], v[2] + oz)))
    missing_positions = set(moved) - found_positions
    n_vert_entries = sum(len(v) for v in plan.values())
    n_moved_tris = sum(len(v) for v in moved_tris.values())
    n_nrm_vids = sum(len(v) for v in nrm_changed.values())
    log(f"[ref-state-r6] independently-resolved plan: vertex_entries={n_vert_entries} "
        f"moved_tris={n_moved_tris} (kept {sum(len(v) for v in moved_tris_kept.values())}) "
        f"nrm_changed_vids={n_nrm_vids} missing_positions={len(missing_positions)}")

    return dict(S=S, R=R, C=C, Q=Q, spikes=spikes, plan=plan, moved_tris=moved_tris,
                moved_tris_kept=moved_tris_kept, nrm_changed=nrm_changed,
                n_vert_entries=n_vert_entries, n_moved_tris=n_moved_tris, n_nrm_vids=n_nrm_vids,
                missing_positions=missing_positions, reproduced_identical=reproduced_identical,
                disk_moved_n=len(disk_moved))


# ====================================================================================================
# (1) STAGE4 PLUMBING re-run fresh -- FIXED6 must be all_ok, down-facing must stay at the BASELINE 3,
#     and must be position-CONTINUOUS with the whole specimen->FIXED5 chain wherever this round's
#     Y-move cannot have changed the measured field.
# ====================================================================================================
def run_plumbing_fresh():
    plumb_specimen = G.plumbing_criteria(SPECIMEN_DIR, "specimen")
    plumb_fixed1 = G.plumbing_criteria(FIXED_DIR, "fixed_r1")
    plumb_fixed2 = G.plumbing_criteria(FIXED2_DIR, "fixed2")
    plumb_fixed3a = G.plumbing_criteria(FIXED3A_DIR, "fixed3a")
    plumb_fixed4 = G.plumbing_criteria(FIXED4_DIR, "fixed4")
    plumb_fixed5 = G.plumbing_criteria(FIXED5_DIR, "fixed5")
    plumb_fixed6 = G.plumbing_criteria(FIXED6_DIR, "fixed6")

    topology_fields = ("flat_mesh_ok", "grid_ok", "frame_bounds_ok", "weld_near_miss_total",
                        "open_edges_above_skirt")
    identical_topology = {name: all(p[f] == plumb_fixed6[f] for f in topology_fields)
                           for name, p in (("specimen", plumb_specimen), ("fixed_r1", plumb_fixed1),
                                           ("fixed2", plumb_fixed2), ("fixed3a", plumb_fixed3a),
                                           ("fixed4", plumb_fixed4), ("fixed5", plumb_fixed5))}
    down_facing_chain = {name: p["total_down_facing_tris"]
                          for name, p in (("specimen", plumb_specimen), ("fixed_r1", plumb_fixed1),
                                          ("fixed2", plumb_fixed2), ("fixed3a", plumb_fixed3a),
                                          ("fixed4", plumb_fixed4), ("fixed5", plumb_fixed5),
                                          ("fixed6", plumb_fixed6))}
    down_facing_at_baseline = (plumb_fixed6["total_down_facing_tris"] == DOWN_FACING_BASELINE)
    down_facing_unchanged_vs_fixed5 = (plumb_fixed6["total_down_facing_tris"]
                                        == plumb_fixed5["total_down_facing_tris"])

    log(f"  fixed6: flat={plumb_fixed6['flat_mesh_ok']} grid={plumb_fixed6['grid_ok']} "
        f"frame={plumb_fixed6['frame_bounds_ok']} weld_near_miss={plumb_fixed6['weld_near_miss_total']} "
        f"down_facing={plumb_fixed6['total_down_facing_tris']} (baseline {DOWN_FACING_BASELINE}) "
        f"open_edges={plumb_fixed6['open_edges_above_skirt']} all_ok={plumb_fixed6['all_ok']}")
    log(f"  topology fields identical to fixed6 across the chain: {identical_topology}")
    log(f"  down_facing chain: {down_facing_chain}")

    return dict(
        specimen=plumb_specimen, fixed_r1=plumb_fixed1, fixed2=plumb_fixed2, fixed3a=plumb_fixed3a,
        fixed4=plumb_fixed4, fixed5=plumb_fixed5, fixed6=plumb_fixed6,
        identical_topology_vs_chain=identical_topology,
        down_facing_chain=down_facing_chain,
        down_facing_baseline=DOWN_FACING_BASELINE,
        down_facing_at_baseline=down_facing_at_baseline,
        down_facing_unchanged_vs_fixed5=down_facing_unchanged_vs_fixed5,
        fixed6_all_ok=plumb_fixed6["all_ok"],
        passed=bool(plumb_fixed6["all_ok"] and all(identical_topology.values())
                    and down_facing_at_baseline and down_facing_unchanged_vs_fixed5))


# ====================================================================================================
# (2) DEDICATED coincident-position WELD AUDIT, independently written, over ALL 8 PARTS x 20 blocks,
#     FIXED5 (pre) vs FIXED6 (post) -- 0 splits, 0 non-uniform deltas required.
# ====================================================================================================
def weld_audit_all_parts(ref):
    S, Q, plan = ref["S"], ref["Q"], ref["plan"]
    touched = S["touched"]
    moved = Q["moved"]

    pre_groups = defaultdict(list)     # pre poskey -> [(block, part, vid)]
    post_pos = {}                      # (block, part, vid) -> post poskey
    for b in touched:
        ox, oz = X.block_world_origin(*b)
        for part in P.PARTS:
            rel = M.override_relpath(1, b[0], b[1], part=part)
            p5, p6 = FIXED5_DIR / rel, FIXED6_DIR / rel
            if not p5.exists():
                continue
            d5 = M.read_ff9mesh(p5)
            d6 = M.read_ff9mesh(p6)
            if d5["vcount"] != d6["vcount"]:
                pre_groups["__VCOUNT_DRIFT__"].append((b, part, -1))
                continue
            for j in range(d5["vcount"]):
                a, c = d5["verts"][j], d6["verts"][j]
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
# (3) STANDING TEXTURE GATES, re-measured on FIXED6, verified BYTE-UNCHANGED vs FIXED5
# ====================================================================================================
def texture_gates_unchanged():
    tex_ref = G4.build_reference_state()   # re-derives family/window field from FIXED3A/FIXED4 disk bytes

    g1_fixed6 = G.gate1_uv_validity(FOOTPRINT, FIXED6_DIR, "fixed6")
    g1_fixed5 = G.gate1_uv_validity(FOOTPRINT, FIXED5_DIR, "fixed5_crosscheck")
    log(f"  GATE1a fixed6: zero_uv_frac={g1_fixed6['zero_uv_area_frac']} "
        f"bit_identical={g1_fixed6['total_bit_identical']} passed={g1_fixed6['passed']}")

    wc_fixed6 = G4.family_window_coherence_check(FIXED6_DIR, "fixed6", tex_ref)
    wc_fixed5 = G4.family_window_coherence_check(FIXED5_DIR, "fixed5_crosscheck", tex_ref)
    log(f"  GATE1c fixed6: n={wc_fixed6['n_tris']} single={wc_fixed6['single_window_reconstructed']} "
        f"multi={wc_fixed6['multi_window_or_unreconstructed']} frac={wc_fixed6['multi_window_frac']} "
        f"per_family={wc_fixed6['per_family']} passed={wc_fixed6['passed']}")
    gate1c_identical_to_fixed5 = (
        wc_fixed6["single_window_reconstructed"] == wc_fixed5["single_window_reconstructed"]
        and wc_fixed6["multi_window_or_unreconstructed"] == wc_fixed5["multi_window_or_unreconstructed"]
        and wc_fixed6["per_family"] == wc_fixed5["per_family"])

    rect_fixed6 = G4.family_rect_membership_check(FIXED6_DIR, "fixed6", tex_ref)
    rect_fixed5 = G4.family_rect_membership_check(FIXED5_DIR, "fixed5_crosscheck", tex_ref)
    log(f"  family rect membership fixed6: {rect_fixed6['out_of_region_by_family']} "
        f"zero_area={rect_fixed6['zero_area_by_family']} passed={rect_fixed6['passed']}")
    rect_identical_to_fixed5 = (rect_fixed6["out_of_region_by_family"] == rect_fixed5["out_of_region_by_family"]
                                 and rect_fixed6["zero_area_by_family"] == rect_fixed5["zero_area_by_family"]
                                 and rect_fixed6["tris_checked_by_family"] == rect_fixed5["tris_checked_by_family"])

    # direct UV-byte identity, FIXED5 vs FIXED6, over all 20 touched blocks
    uv_diffs = 0
    for (bx, by) in FOOTPRINT:
        a = M.read_ff9mesh(F2.terr_path(FIXED5_DIR, bx, by))
        f = M.read_ff9mesh(F2.terr_path(FIXED6_DIR, bx, by))
        for j in range(a["vcount"]):
            if a["uvs"][j] != f["uvs"][j]:
                uv_diffs += 1
    log(f"  direct UV-byte diff FIXED5 vs FIXED6: {uv_diffs} (must be 0 -- round 6 is Y/normal-only)")

    passed = bool(g1_fixed6["passed"] and wc_fixed6["passed"] and rect_fixed6["passed"]
                  and gate1c_identical_to_fixed5 and rect_identical_to_fixed5 and uv_diffs == 0)
    return dict(gate1a_fixed6=g1_fixed6, gate1a_fixed5_crosscheck=g1_fixed5,
                gate1c_fixed6=wc_fixed6, gate1c_fixed5_crosscheck=wc_fixed5,
                gate1c_identical_to_fixed5=gate1c_identical_to_fixed5,
                family_rect_fixed6=rect_fixed6, family_rect_fixed5_crosscheck=rect_fixed5,
                family_rect_identical_to_fixed5=rect_identical_to_fixed5,
                uv_byte_diffs_fixed5_vs_fixed6=uv_diffs,
                passed=passed)


# ====================================================================================================
# (4) GATE 2 SEA-PLAN-DISJOINT on FIXED6 + explicit per-moved-position clearance check
# ====================================================================================================
def sea_gate_and_clearance(ref):
    g2_fixed6 = G.gate2_sea_plan_disjoint(FOOTPRINT, FIXED6_DIR, "fixed6")
    g2_fixed5 = G.gate2_sea_plan_disjoint(FOOTPRINT, FIXED5_DIR, "fixed5_crosscheck")
    log(f"  GATE2 fixed6: A(y-order) viol={g2_fixed6['A_y_order']['fully_submerged_tris_GATING']} "
        f"passed={g2_fixed6['A_y_order']['passed']} | B={g2_fixed6['B_uniformity']['passed']} | "
        f"C={g2_fixed6['C_real_sea_disjoint']['passed']} | overall={g2_fixed6['passed']}")

    R, Q = ref["R"], ref["Q"]
    res = R["res"]
    moved = Q["moved"]
    moved_y_after = {k: k[1] + dv for k, dv in moved.items()}
    below_floor = {k: y for k, y in moved_y_after.items() if y <= 0.5}
    at_or_below_sea = {k: y for k, y in moved_y_after.items() if y <= 0.0}
    min_moved_y = min(moved_y_after.values()) if moved_y_after else None
    log(f"  moved-position clearance: n={len(moved_y_after)} min_Y_after={min_moved_y} "
        f"below_0.5_floor={len(below_floor)} at_or_below_sea={len(at_or_below_sea)}")

    passed = bool(g2_fixed6["passed"] and not below_floor and not at_or_below_sea)
    return dict(gate2_fixed6=g2_fixed6, gate2_fixed5_crosscheck=g2_fixed5,
                moved_position_clearance=dict(
                    n_moved=len(moved_y_after), min_Y_after=min_moved_y,
                    below_0p5_floor=len(below_floor), at_or_below_sea_y0=len(at_or_below_sea),
                    sample_below_floor=list(below_floor.items())[:5]),
                passed=passed)


# ====================================================================================================
# (5) CONTRACT MATRIX v5 -- R1+R2+R3 on FIXED6 + FIXED5 crosscheck + stock calibration control.  Round
#     6's moves are ALL interior (min r_crater 12.019u, itself far inside the mound, itself far inside
#     the 20-block footprint) -- R1's XZ-only realized metric MUST be byte-unchanged; measured.
# ====================================================================================================
def contract_matrix():
    stock_cand = CMG.load_candidate("stock_ecotone_13-15_11-12", None, core_blocks=CMG.ECOTONE_CORE)
    stock_row = CMG.run_matrix_on(stock_cand)

    contract_fixed6 = G.contract_rerun(FIXED6_DIR, "rung_f_FIXED6")
    contract_fixed5 = G.contract_rerun(FIXED5_DIR, "rung_f_FIXED5_crosscheck")
    log(f"  stock calibration control: overall={stock_row['overall']}")
    log(f"  fixed5: R1={contract_fixed5['R1']['verdict']} R2={contract_fixed5['R2']['verdict']} "
        f"R3={contract_fixed5['R3']['verdict']} overall={contract_fixed5['overall']}")
    log(f"  fixed6: R1={contract_fixed6['R1']['verdict']} R2={contract_fixed6['R2']['verdict']} "
        f"R3={contract_fixed6['R3']['verdict']} overall={contract_fixed6['overall']}")
    log(f"  fixed6 R1 measured={contract_fixed6['R1']['measured']} floors={contract_fixed6['R1']['floors']}")

    sea_vertex_flag = contract_fixed6["R1"]["sea_vertex_convention_invalid"]
    convention_invalid_flag = contract_fixed6["R1"]["convention_invalid"]
    expected_floors = dict(boundary_cell=39.953, straddle_cell=44.635, body_tri=42.968)
    floors_match = all(abs(contract_fixed6["R1"]["floors"].get(k, -1) - v) < 0.01
                        for k, v in expected_floors.items())
    r1_unchanged_vs_fixed5 = (contract_fixed6["R1"]["measured"] == contract_fixed5["R1"]["measured"])

    r2_6, r2_5 = contract_fixed6["R2"], contract_fixed5["R2"]
    r3_6, r3_5 = contract_fixed6["R3"], contract_fixed5["R3"]
    r2_keys = ("sat_grass", "sat_any", "fringe", "penetration", "floating")
    r3_keys = ("reachable_backing", "interface", "erosion")
    r2_diff = {k: dict(fixed5=r2_5[k], fixed6=r2_6[k], moved=(r2_5[k] != r2_6[k])) for k in r2_keys}
    r3_diff = {k: dict(fixed5=r3_5[k], fixed6=r3_6[k], moved=(r3_5[k] != r3_6[k])) for k in r3_keys}
    r2_any_moved = any(v["moved"] for v in r2_diff.values())
    r3_any_moved = any(v["moved"] for v in r3_diff.values())
    log(f"  R2 diff fixed5->fixed6: {r2_diff}  any_moved={r2_any_moved}")
    log(f"  R3 diff fixed5->fixed6: {r3_diff}  any_moved={r3_any_moved}")

    # -----------------------------------------------------------------------
    # R1 REALIZED, falsifier convention (rung_f_falsify.py, XZ-only by construction)
    r1_fixed6 = G.r1_realized(FIXED6_DIR, "fixed6")
    r1_fixed5 = G.r1_realized(FIXED5_DIR, "fixed5_crosscheck")
    expected_headline = dict(boundary_cell=46.826, straddle_cell=48.882, body_tri=49.547)
    r1_matches_headline = (r1_fixed6["measured"] == expected_headline)
    r1_unchanged_falsifier = (r1_fixed6["measured"] == r1_fixed5["measured"])
    log(f"  R1 REALIZED fixed6: {r1_fixed6['measured']} verdict={r1_fixed6['verdict']} "
        f"matches_headline={r1_matches_headline} unchanged_vs_fixed5={r1_unchanged_falsifier}")

    contract_matrix_green = (
        contract_fixed6["R1"]["verdict"] == "PASS"
        and contract_fixed6["R2"]["verdict"] == "PASS"
        and contract_fixed6["R3"]["verdict"] == "PASS"
        and contract_fixed6["overall"] == "PASS"
        and stock_row["overall"] == "PASS"
        and sea_vertex_flag is True
        and convention_invalid_flag is False
        and floors_match
        and r1_matches_headline
        and r1_unchanged_falsifier
        and r1_fixed6["verdict"] == "PASS")

    return dict(
        stock_calibration_overall=stock_row["overall"],
        fixed5_crosscheck=contract_fixed5, fixed6=contract_fixed6,
        fixed6_R1_sea_vertex_convention_invalid=sea_vertex_flag,
        fixed6_R1_convention_invalid=convention_invalid_flag,
        floors_match_expected=floors_match,
        R1_gate_metric_unchanged_vs_fixed5=r1_unchanged_vs_fixed5,
        R2_diff_fixed5_vs_fixed6=r2_diff, R2_any_number_moved=r2_any_moved,
        R3_diff_fixed5_vs_fixed6=r3_diff, R3_any_number_moved=r3_any_moved,
        r1_realized_fixed6=r1_fixed6, r1_realized_fixed5_crosscheck=r1_fixed5,
        r1_realized_expected_headline=expected_headline,
        r1_realized_matches_headline=r1_matches_headline,
        r1_realized_unchanged_vs_fixed5=r1_unchanged_falsifier,
        contract_matrix_green=contract_matrix_green,
        note=("all 12 moved positions are interior -- min r_crater 12.019u -- so R1's XZ-only realized "
              "standoff is expected byte-identical vs FIXED5 (round 5 established the same identity vs "
              "FIXED4 for the same reason: the metric is XZ-only by construction and Y never enters it)."),
        passed=bool(contract_matrix_green and not r2_any_moved and not r3_any_moved
                    and r1_unchanged_vs_fixed5))


# ====================================================================================================
# (6) BYTE-RIGIDITY vs FIXED5, POSITION/NORMAL-SCOPED (expected set re-derived independently, above)
# ====================================================================================================
def byte_rigidity(ref):
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
        a = M.read_ff9mesh(F2.terr_path(FIXED5_DIR, *b))
        f = M.read_ff9mesh(F2.terr_path(FIXED6_DIR, *b))
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
    return dict(counts=rig, per_block_anomalies=per_block, passed=rigidity_ok)


# ====================================================================================================
# (7) THE SCOPE GATE -- carried-core tris OUTSIDE the spike set are byte-identical to FIXED5.  This is
#     the round's own contract change ("carried MAY move, but ONLY the spike set") turned into a
#     mechanical check rather than left as prose.  Both directions are checked: every kept tri that did
#     NOT touch a spike position must be untouched, AND every kept tri that DID change must touch one.
#     A companion pass does the analogous check for synthesized/fill tris outside the harmonic patch.
# ====================================================================================================
def scope_gate(ref):
    S = ref["S"]
    touched, synth_key, spikes = S["touched"], S["synth_key"], ref["spikes"]
    patch_unknowns = set(ref["Q"]["Ul"])
    f5 = {b: M.read_ff9mesh(F2.terr_path(FIXED5_DIR, *b)) for b in touched}
    f6 = {b: M.read_ff9mesh(F2.terr_path(FIXED6_DIR, *b)) for b in touched}

    kept_touching = kept_outside = 0
    kept_outside_changed = []      # would be a HOLE in the contract
    kept_touching_unchanged = []   # informational -- a touching tri need not itself change
    fill_in_patch = fill_outside = 0
    fill_outside_changed = []

    for b in touched:
        ox, oz = X.block_world_origin(*b)
        d5, d6 = f5[b], f6[b]
        n_tris = len(d5["indices"]) // 3
        for t in range(n_tris):
            tri = d5["indices"][3 * t:3 * t + 3]
            keys = [P.pkey((d5["verts"][j][0] + ox, d5["verts"][j][1], d5["verts"][j][2] + oz))
                    for j in tri]
            touches_spike = any(k in spikes for k in keys)
            pos_changed = any(d5["verts"][j] != d6["verts"][j] for j in tri)
            nrm_changed = any(d5["normals"][j] != d6["normals"][j] for j in tri)
            changed = pos_changed or nrm_changed
            is_synth = (b, t) in synth_key
            if not is_synth:
                if touches_spike:
                    kept_touching += 1
                    if not changed:
                        kept_touching_unchanged.append(dict(block=list(b), tri=t))
                else:
                    kept_outside += 1
                    if changed:
                        kept_outside_changed.append(dict(
                            block=list(b), tri=t, pos_changed=pos_changed, nrm_changed=nrm_changed))
            else:
                in_patch = any(k in patch_unknowns for k in keys)
                if in_patch:
                    fill_in_patch += 1
                else:
                    fill_outside += 1
                    if changed:
                        fill_outside_changed.append(dict(
                            block=list(b), tri=t, pos_changed=pos_changed, nrm_changed=nrm_changed))

    result = dict(
        n_kept_tris_touching_a_spike=kept_touching,
        n_kept_tris_outside_spike_set=kept_outside,
        kept_outside_changed_count=len(kept_outside_changed),
        kept_outside_changed_examples=kept_outside_changed[:10],
        kept_touching_but_unchanged_count=len(kept_touching_unchanged),
        kept_touching_but_unchanged_examples=kept_touching_unchanged[:10],
        n_fill_tris_in_harmonic_patch=fill_in_patch,
        n_fill_tris_outside_patch=fill_outside,
        fill_outside_changed_count=len(fill_outside_changed),
        fill_outside_changed_examples=fill_outside_changed[:10],
        carried_core_frozen=(len(kept_outside_changed) == 0),
        fill_outside_patch_frozen=(len(fill_outside_changed) == 0),
        note=("kept_outside_changed_count and fill_outside_changed_count must both be 0 -- that is the "
              "literal mechanical statement of this round's ONE contract change: carried geometry MAY "
              "move only inside the census-defined spike set (plus fill graph-adjacent to it), never "
              "elsewhere. kept_touching_but_unchanged is informational only (a tri sharing a vertex with "
              "a spike need not itself change position/normal if its other two vertices absorbed the "
              "whole delta via the shared-vertex weld -- not expected to be nonzero here since every "
              "spike site drags its own 1-ring, but recorded rather than assumed)."))
    passed = bool(result["carried_core_frozen"] and result["fill_outside_patch_frozen"])
    result["passed"] = passed
    log(f"  scope gate: kept touching={kept_touching} outside={kept_outside} "
        f"outside_changed={len(kept_outside_changed)} | fill in_patch={fill_in_patch} "
        f"outside={fill_outside} outside_changed={len(fill_outside_changed)} passed={passed}")
    return result


# ====================================================================================================
# (8) ONLY EXPECTED FILES CHANGED -- full-tree sha256 diff FIXED5 vs FIXED6
# ====================================================================================================
def tree_diff(ref):
    import hashlib

    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    S = ref["S"]
    touched = S["touched"]
    changed = []
    n5 = n6 = 0
    for p in sorted(FIXED5_DIR.rglob("*")):
        if p.is_file():
            n5 += 1
            rel = p.relative_to(FIXED5_DIR)
            other = FIXED6_DIR / rel
            if not other.exists() or sha(p) != sha(other):
                changed.append(str(rel))
    for p in FIXED6_DIR.rglob("*"):
        if p.is_file():
            n6 += 1
    expected_files = {str(F2.terr_path(FIXED5_DIR, *b).relative_to(FIXED5_DIR)) for b in touched
                       if b in ref["plan"] and ref["plan"][b]}
    result = dict(
        n_files_fixed5=n5, n_files_fixed6=n6, n_changed=len(changed), changed_files=changed,
        n_terrain_changed=sum(1 for r in changed if "Terrain" in r),
        n_non_terrain_changed=sum(1 for r in changed if "Terrain" not in r),
        unexpected=[r for r in changed if r not in expected_files],
        expected_not_changed=[r for r in expected_files if r not in changed],
        matches_expected_count=(len(changed) == N_TERRAIN_DIRTY_EXPECTED == len(expected_files)),
        both_trees_180_files=(n5 == N_FILES == n6))
    log(f"  tree diff: {len(changed)} files changed (expect {N_TERRAIN_DIRTY_EXPECTED} Terrain-only); "
        f"unexpected={result['unexpected']} expected_not_changed={result['expected_not_changed']}")
    passed = bool(result["matches_expected_count"] and not result["unexpected"]
                  and not result["expected_not_changed"] and result["n_non_terrain_changed"] == 0
                  and result["both_trees_180_files"])
    result["passed"] = passed
    return result


# ====================================================================================================
def main():
    assert FIXED6_DIR.exists(), f"missing target tree: {FIXED6_DIR}"
    result = {}

    log("=" * 100)
    log("(0) RE-DERIVE round 6's mechanism from disk (uvf_fix6.py stage1-4, re-executed)")
    log("=" * 100)
    ref = build_reference_state_r6()
    result["reference_state"] = dict(
        n_touched=len(ref["S"]["touched"]), n_spikes=len(ref["spikes"]),
        n_sites=len(ref["C"]["sites"]), n_patch_unknowns=len(ref["Q"]["Ul"]),
        n_moved_positions=len(ref["Q"]["moved"]),
        n_vert_entries_resolved=ref["n_vert_entries"], n_moved_tris_resolved=ref["n_moved_tris"],
        n_moved_tris_kept_resolved=sum(len(v) for v in ref["moved_tris_kept"].values()),
        n_nrm_vids_resolved=ref["n_nrm_vids"],
        n_missing_positions=len(ref["missing_positions"]),
        resolution_matches_solver_count=(len(ref["missing_positions"]) == 0),
        independent_solve_reproduces_report_moved_set=ref["reproduced_identical"],
        report_moved_set_n=ref["disk_moved_n"])

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(1) STAGE4 PLUMBING re-run FRESH on FIXED6")
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
    log("(3) STANDING TEXTURE GATES, re-measured + verified byte-unchanged vs FIXED5")
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
    log("(6) BYTE-RIGIDITY vs FIXED5 (position/normal-scoped)")
    log("=" * 100)
    rig = byte_rigidity(ref)
    result["byte_rigidity"] = rig

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(7) THE SCOPE GATE -- carried-core tris outside the spike set are byte-identical to FIXED5")
    log("=" * 100)
    scope = scope_gate(ref)
    result["scope_gate"] = scope

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(8) ONLY-EXPECTED-FILES full-tree diff")
    log("=" * 100)
    tdiff = tree_diff(ref)
    result["tree_diff"] = tdiff

    # ====================================================================================================
    gate_summary = dict(
        reference_state_resolves_cleanly=result["reference_state"]["resolution_matches_solver_count"],
        independent_solve_matches_report=result["reference_state"]["independent_solve_reproduces_report_moved_set"],
        plumbing_fixed6_all_ok=plumbing["fixed6_all_ok"],
        plumbing_topology_identical_vs_chain=all(plumbing["identical_topology_vs_chain"].values()),
        plumbing_down_facing_at_baseline=plumbing["down_facing_at_baseline"],
        plumbing_down_facing_unchanged_vs_fixed5=plumbing["down_facing_unchanged_vs_fixed5"],
        weld_audit_zero_cracks=weld["ok"],
        texture_gates_pass_and_unchanged=tex["passed"],
        gate2_sea_passes_and_clearance_ok=sea["passed"],
        contract_matrix_green=contract["passed"],
        byte_rigidity_ok=rig["passed"],
        scope_gate_carried_core_frozen=scope["passed"],
        tree_diff_ok=tdiff["passed"])
    result["gate_summary"] = gate_summary
    log(f"GATE SUMMARY: {json.dumps(gate_summary, indent=2)}")

    overall = all(gate_summary.values())
    result["overall"] = "PASS" if overall else "FAIL"
    result["meta"] = dict(
        script="uvf_gates6.py", target=str(FIXED6_DIR), base=str(FIXED5_DIR),
        reused_functions_from=(
            "uvf_gates.py (gate1_uv_validity/gate2_sea_plan_disjoint/plumbing_criteria/contract_rerun/"
            "r1_realized, verbatim); uvf_gates4.py (build_reference_state/family_window_coherence_check/"
            "family_rect_membership_check, verbatim); uvf_fix6.py (stage1/stage2/stage3/stage4, the "
            "round's own mechanism, re-executed fresh against on-disk FIXED5 bytes + the donor/fix5-"
            "report reads -- never the fix6 report's OWN claims, though those are cross-checked for "
            "reproducibility); uvf_fix3.py (load_blocks); uvf_relief_probe.py (pkey/PARTS/POS_DP)"),
        new_this_round=("run_plumbing_fresh (down-facing baseline gate + full-chain topology continuity, "
                        "chain extended through FIXED6), weld_audit_all_parts (independent cross-part/"
                        "cross-block weld re-derivation FIXED5->FIXED6, not calling uvf_fix6.py's own "
                        "stage_verify), texture_gates_unchanged (byte-unchanged crosscheck vs FIXED5 + "
                        "direct UV-byte diff), sea_gate_and_clearance (per-moved-position clearance), "
                        "contract_matrix (R1 gate-metric + R1-realized-falsifier + R2/R3 diffs vs FIXED5, "
                        "with the interior-move R1-invariance argument stated explicitly), byte_rigidity "
                        "(position/normal-scoped rigidity vs FIXED5, expected set independently resolved "
                        "in build_reference_state_r6), scope_gate (THE NEW CHECK -- every kept tri "
                        "outside the spike set AND every fill tri outside the harmonic patch is required "
                        "byte-identical FIXED5 vs FIXED6, both directions), tree_diff (full-tree sha256, "
                        "3-Terrain-file-only)"),
        contract_gates_version="contract_mass_gates.py v5 (evolved, live)",
        note=("zero writes outside out/rung_f/uvf_gates6.json; zero git; specimen/FIXED../FIXED4/FIXED5/"
              "FIXED6 trees read-only throughout; the stock ecotone calibration read + uvf_fix6.py's "
              "stage1/stage2 donor + fix5-report reads are the same read-only install access every prior "
              "round in this arc has used and documented"))

    OUT.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    log("\n" + "=" * 100)
    log(f"OVERALL: {result['overall']}")
    log(f"-> {OUT}")
    return result


if __name__ == "__main__":
    main()
