"""RUNG F -- THE SLIVER-STEP SHAVE (round 7) -- THE FULL VERIFICATION BATTERY on
FF9CustomMap-world-FIXED7.

FIXED7 (uvf_fix7.py) is the THIRD round in the Rung-F arc to move CARRIED (kept, donor) geometry -- and
the first whose contract change lives entirely inside ONE predicate's ARM SET (predicate (3) of round 6's
five-predicate census gains a STEP arm: prominence >= 0.4u (CONE) OR prominence >= 0.0u AND drop >= 1.5u
(STEP)). Nothing else in the rule, the solve, the guards or the weld law changed. This script follows the
uvf_gates5.py / uvf_gates6.py SHAPE: it re-derives round 7's own mechanism FRESH from disk (calling
uvf_fix7.py's stage1..stage4 verbatim -- the same functions the build itself runs -- never trusting
uvf_fix7_report.json's claims except as a reproduction cross-check), then runs the standing battery plus
the checks this round's own contract change specifically demands.

TEN SECTIONS:
  (0) REFERENCE-STATE re-derivation: uvf_fix7.py stage1-4 re-executed against on-disk FIXED6 (round 7's
      declared INPUT) bytes; the solved moved-set is cross-checked for reproducibility against
      uvf_fix7_report.json's own numbers (never trusted directly).
  (1) STAGE4 PLUMBING re-run fresh, chain now extended through FIXED7 -- flat-mesh/grid/frame-bounds/
      weld-near-miss/open-edges topology-identical back to specimen, and down-facing-tri COUNT gated
      against the baseline 3 (must also equal FIXED6's own count -- a Y-only move cannot change winding).
  (2) A DEDICATED coincident-position WELD AUDIT, independently written (its own re-derivation of every
      coincident-position group, not uvf_fix7.py's own stage_verify), across ALL 8 PARTS of all 20
      touched blocks, FIXED6 (pre) -> FIXED7 (post).
  (3) STANDING TEXTURE GATES, re-measured on FIXED7 and verified BYTE-UNCHANGED vs FIXED6 -- GATE 1a
      zero-uv-area, the family-aware GATE 1c one-window-coherence (uvf_gates4.family_window_coherence_
      check, itself seeded from the stock census / grassland.ground_uv -- NOT a hardcoded per-round
      exception, so it "accounts for any new band/row language" the SAME way it always has: by
      reconstructing every synthesized tri from its own assigned family's mains, whatever that family
      is), family mains-rect membership, plus a direct UV-byte identity diff FIXED6 vs FIXED7. Round 7
      writes ZERO UV bytes (a Y/normal-only round), so every one of these must come back IDENTICAL to
      FIXED6's own measurement -- verified, not assumed, and nothing here is special-cased for round 7's
      particular geometry.
  (4) GATE 2 SEA-PLAN-DISJOINT on FIXED7, plus a direct per-moved-position clearance check.
  (5) CONTRACT MATRIX v5 (R1+R2+R3) re-run on FIXED7 + FIXED6 crosscheck + the stock ecotone calibration
      control. All 3 of round 7's moved positions are interior (min r_crater 11.435u, itself far inside
      the mound) -- R1's XZ-only realized standoff MUST be byte-unchanged; measured, not assumed.
  (6) BYTE-RIGIDITY vs FIXED6, POSITION/NORMAL-SCOPED and CONFINED TO THE BUILD'S DECLARED CHANGE SET:
      the expected-changed vertex/normal sets are re-derived HERE independently (mirroring uvf_fix7.py's
      own PASS-1/PASS-3 resolution, written fresh) and the round's own declared totals (16 vertex
      entries / 3 positions / 12 tris / 36 normal entries / 1 file) are asserted as upper AND lower
      bounds -- not just "0 unexpected".
  (7) THE SCOPE GATE (round 6's own contract check, still load-bearing): every KEPT (carried) triangle
      in the 20-block footprint that does NOT touch the census-defined spike position is required
      BYTE-IDENTICAL (position AND normal) FIXED6 vs FIXED7; every kept tri that DID change must touch
      the spike. A companion pass does the same for synthesized/fill tris outside the harmonic patch.
  (8) THE CRATER + ROUND 7's OWN NEW GUARDS, re-derived independently: the sacred basin disc byte-frozen,
      the carried rim-base multiset identical outside the (single) spike site, THE BASIN REFERENCE TRAP
      re-measured (rim-crest clearance under the residual gate, now a hard stop given predicate (3)'s
      widening), round 6's four apexes re-verified byte-frozen and NOT re-selected by the wider rule
      (uvf_fix7.py's own _round6_apexes/_prior_fixes_intact/_recensus helpers called directly, on values
      derived fresh in THIS script -- not read from the JSON report), and the widened census's
      self-termination (FIXED6 -> 1 qualifier, FIXED7 -> 0).
  (9) ONLY EXPECTED FILES CHANGED -- full-tree sha256 diff FIXED6 vs FIXED7 (1 Terrain file, 0 elsewhere,
      180 files present in both trees -- the smallest tree diff of the arc).

Writes only out/rung_f/uvf_gates7.json + this script. Zero git, zero install writes. specimen/FIXED../
FIXED6/FIXED7 trees read-only throughout; uvf_fix7.py's stage1-4 re-executes the same read-only donor +
fix5/fix6-report reads every prior round in this arc has used and documented.
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
import uvf_fix7 as F7                 # noqa: E402  -- stage1/2/3/4/stage_guards + _round6_apexes/_prior_fixes_intact/_recensus (the round's own mechanism, re-executed)
import uvf_relief_probe as P          # noqa: E402  -- pkey / PARTS / POS_DP

OUT_DIR = HERE / "out" / "rung_f"
SPECIMEN_DIR = G.SPECIMEN_DIR
FIXED_DIR = G.FIXED_DIR
FIXED2_DIR = OUT_DIR / "FF9CustomMap-world-FIXED2"
FIXED3A_DIR = OUT_DIR / "FF9CustomMap-world-FIXED3A"
FIXED4_DIR = OUT_DIR / "FF9CustomMap-world-FIXED4"
FIXED5_DIR = OUT_DIR / "FF9CustomMap-world-FIXED5"
FIXED6_DIR = OUT_DIR / "FF9CustomMap-world-FIXED6"          # round 7's declared INPUT (== F7.BASE)
FIXED7_DIR = OUT_DIR / "FF9CustomMap-world-FIXED7"          # round 7's declared OUTPUT (== F7.OUT)
OUT = OUT_DIR / "uvf_gates7.json"

FOOTPRINT = G.FOOTPRINT
DOWN_FACING_BASELINE = 3          # pre-existing, unrelated down-facing tris measured on every prior round
N_FILES = 180
N_TERRAIN_DIRTY_EXPECTED = 1      # round 7's own report: exactly 1 file, Terrain, Disc1 -- the smallest yet
N_VERT_ENTRIES_EXPECTED = 16      # 3 moved positions x (4+5+7) vertex entries
N_NRM_VIDS_EXPECTED = 36          # 12 moved tris x 3 verts
N_MOVED_POSITIONS_EXPECTED = 3    # 1 spike + 2 fill (hop1, hop2)
N_MOVED_TRIS_EXPECTED = 12
N_MOVED_TRIS_KEPT_EXPECTED = 2    # the rock-decal pair, (1,18)#1 and (1,18)#8

assert FIXED6_DIR == F7.BASE, "this script's FIXED6_DIR must be round 7's declared BASE"
assert FIXED7_DIR == F7.OUT, "this script's FIXED7_DIR must be round 7's declared OUT"


def log(m):
    print(m, flush=True)


# ====================================================================================================
# (0) RE-DERIVE round 7's own mechanism from disk (never trust uvf_fix7_report.json's claims) -- calls
#     uvf_fix7.py's stage1..stage4 VERBATIM (the same functions the build itself runs), so this is the
#     identical solve re-executed independently of the build's own report, plus a fresh PASS-1/PASS-3
#     style resolution against FIXED6's PRE-move bytes (mirrors uvf_fix7.py's stage_apply exactly, but
#     re-derived here rather than imported).
# ====================================================================================================
def build_reference_state_r7():
    rpt = {"meta": dict(reused_by="uvf_gates7.py")}
    S = F7.stage1(rpt)
    R = F7.stage2(rpt, S)
    C = F7.stage3(rpt, S, R)
    Q = F7.stage4(rpt, S, R, C)
    moved = Q["moved"]
    spikes = set(C["spikes"])
    log(f"[ref-state-r7] spikes={len(spikes)} sites={len(C['sites'])} unknowns={len(Q['Ul'])} "
        f"moved_positions={len(moved)}")

    on_disk = json.loads((OUT_DIR / "uvf_fix7_report.json").read_text(encoding="utf-8"))
    disk_moved = {tuple(round(v, P.POS_DP) for v in row["world"]): row["dY"]
                  for row in on_disk["stage4_solve"]["result"]["spike_moves"]}
    disk_moved.update({tuple(round(v, P.POS_DP) for v in row["world"]): row["dY"]
                       for row in on_disk["stage4_solve"]["result"]["fill_moves"]})
    # the report itself rounds world keys AND dY to P.POS_DP=3 places (uvf_fix7.py stage4's `round(.., 3)`
    # in its result rows) -- so the comparison tolerance must be half that rounding step, not float noise.
    reproduced_identical = (
        len(disk_moved) == len(moved)
        and all(k in moved and abs(moved[k] - dv) < 0.5 * 10 ** (-P.POS_DP) for k, dv in disk_moved.items()))
    log(f"[ref-state-r7] re-executed solve reproduces uvf_fix7_report.json's own moved set: "
        f"{reproduced_identical} (disk n={len(disk_moved)}, re-derived n={len(moved)})")

    touched, synth_key = S["touched"], S["synth_key"]
    # S["f5"] is uvf_fix7.py's OWN name for the meshes loaded from BASE (FIXED6, round 7's input) during
    # stage1 -- reused here rather than reloading, so this is literally the same bytes the solve saw.
    meshes = S["f5"]
    plan = {b: {} for b in touched}
    nrm_changed = {b: set() for b in touched}
    moved_tris = {b: set() for b in touched}
    moved_tris_kept = {b: set() for b in touched}
    for b in touched:
        bm = meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts = bm.chan_arrays[F7.CH_POS]
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
        verts = bm.chan_arrays[F7.CH_POS]
        for j, dy in plan[b].items():
            v = verts[j]
            found_positions.add(P.pkey((v[0] + ox, v[1], v[2] + oz)))
    missing_positions = set(moved) - found_positions
    n_vert_entries = sum(len(v) for v in plan.values())
    n_moved_tris = sum(len(v) for v in moved_tris.values())
    n_nrm_vids = sum(len(v) for v in nrm_changed.values())
    log(f"[ref-state-r7] independently-resolved plan: vertex_entries={n_vert_entries} "
        f"moved_tris={n_moved_tris} (kept {sum(len(v) for v in moved_tris_kept.values())}) "
        f"nrm_changed_vids={n_nrm_vids} missing_positions={len(missing_positions)}")

    return dict(S=S, R=R, C=C, Q=Q, spikes=spikes, plan=plan, moved_tris=moved_tris,
                moved_tris_kept=moved_tris_kept, nrm_changed=nrm_changed,
                n_vert_entries=n_vert_entries, n_moved_tris=n_moved_tris, n_nrm_vids=n_nrm_vids,
                missing_positions=missing_positions, reproduced_identical=reproduced_identical,
                disk_moved_n=len(disk_moved),
                classifier_carries_over=rpt["stage1_mesh"]["classifier_carries_over"],
                rpt=rpt)


# ====================================================================================================
# (1) STAGE4 PLUMBING re-run fresh -- FIXED7 must be all_ok, down-facing must stay at the BASELINE 3,
#     and must be position-CONTINUOUS with the whole specimen->FIXED6 chain wherever this round's
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
    plumb_fixed7 = G.plumbing_criteria(FIXED7_DIR, "fixed7")

    topology_fields = ("flat_mesh_ok", "grid_ok", "frame_bounds_ok", "weld_near_miss_total",
                        "open_edges_above_skirt")
    identical_topology = {name: all(p[f] == plumb_fixed7[f] for f in topology_fields)
                           for name, p in (("specimen", plumb_specimen), ("fixed_r1", plumb_fixed1),
                                           ("fixed2", plumb_fixed2), ("fixed3a", plumb_fixed3a),
                                           ("fixed4", plumb_fixed4), ("fixed5", plumb_fixed5),
                                           ("fixed6", plumb_fixed6))}
    down_facing_chain = {name: p["total_down_facing_tris"]
                          for name, p in (("specimen", plumb_specimen), ("fixed_r1", plumb_fixed1),
                                          ("fixed2", plumb_fixed2), ("fixed3a", plumb_fixed3a),
                                          ("fixed4", plumb_fixed4), ("fixed5", plumb_fixed5),
                                          ("fixed6", plumb_fixed6), ("fixed7", plumb_fixed7))}
    down_facing_at_baseline = (plumb_fixed7["total_down_facing_tris"] == DOWN_FACING_BASELINE)
    down_facing_unchanged_vs_fixed6 = (plumb_fixed7["total_down_facing_tris"]
                                        == plumb_fixed6["total_down_facing_tris"])

    log(f"  fixed7: flat={plumb_fixed7['flat_mesh_ok']} grid={plumb_fixed7['grid_ok']} "
        f"frame={plumb_fixed7['frame_bounds_ok']} weld_near_miss={plumb_fixed7['weld_near_miss_total']} "
        f"down_facing={plumb_fixed7['total_down_facing_tris']} (baseline {DOWN_FACING_BASELINE}) "
        f"open_edges={plumb_fixed7['open_edges_above_skirt']} all_ok={plumb_fixed7['all_ok']}")
    log(f"  topology fields identical to fixed7 across the chain: {identical_topology}")
    log(f"  down_facing chain: {down_facing_chain}")

    return dict(
        specimen=plumb_specimen, fixed_r1=plumb_fixed1, fixed2=plumb_fixed2, fixed3a=plumb_fixed3a,
        fixed4=plumb_fixed4, fixed5=plumb_fixed5, fixed6=plumb_fixed6, fixed7=plumb_fixed7,
        identical_topology_vs_chain=identical_topology,
        down_facing_chain=down_facing_chain,
        down_facing_baseline=DOWN_FACING_BASELINE,
        down_facing_at_baseline=down_facing_at_baseline,
        down_facing_unchanged_vs_fixed6=down_facing_unchanged_vs_fixed6,
        fixed7_all_ok=plumb_fixed7["all_ok"],
        passed=bool(plumb_fixed7["all_ok"] and all(identical_topology.values())
                    and down_facing_at_baseline and down_facing_unchanged_vs_fixed6))


# ====================================================================================================
# (2) DEDICATED coincident-position WELD AUDIT, independently written, over ALL 8 PARTS x 20 blocks,
#     FIXED6 (pre) vs FIXED7 (post) -- 0 splits, 0 non-uniform deltas required.
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
            p6, p7 = FIXED6_DIR / rel, FIXED7_DIR / rel
            if not p6.exists():
                continue
            d6 = M.read_ff9mesh(p6)
            d7 = M.read_ff9mesh(p7)
            if d6["vcount"] != d7["vcount"]:
                pre_groups["__VCOUNT_DRIFT__"].append((b, part, -1))
                continue
            for j in range(d6["vcount"]):
                a, c = d6["verts"][j], d7["verts"][j]
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
# (3) STANDING TEXTURE GATES, re-measured on FIXED7, verified BYTE-UNCHANGED vs FIXED6.
#     family_window_coherence_check / family_rect_membership_check reconstruct every SYNTHESIZED tri
#     through its OWN assigned family's grassland.ground_uv mains -- that assignment is seeded from the
#     cell field (uvf_fix4.py stage2/stage3_cellfield), itself derived from the stock census, and is
#     entirely a function of (block, tri) identity + cell membership, NEVER of Y. A round that writes
#     zero UV bytes and zero index/XZ bytes (asserted in stage1_mesh.classifier_carries_over, re-checked
#     below) cannot introduce any new band/row language into these checks BY CONSTRUCTION -- there is
#     nothing here to special-case; the generic mechanism is what already "accounts for" whatever family
#     vocabulary is present, this round or any other.
# ====================================================================================================
def texture_gates_unchanged(ref):
    tex_ref = G4.build_reference_state()   # re-derives family/window field from FIXED3A/FIXED4 disk bytes

    g1_fixed7 = G.gate1_uv_validity(FOOTPRINT, FIXED7_DIR, "fixed7")
    g1_fixed6 = G.gate1_uv_validity(FOOTPRINT, FIXED6_DIR, "fixed6_crosscheck")
    log(f"  GATE1a fixed7: zero_uv_frac={g1_fixed7['zero_uv_area_frac']} "
        f"bit_identical={g1_fixed7['total_bit_identical']} passed={g1_fixed7['passed']}")

    wc_fixed7 = G4.family_window_coherence_check(FIXED7_DIR, "fixed7", tex_ref)
    wc_fixed6 = G4.family_window_coherence_check(FIXED6_DIR, "fixed6_crosscheck", tex_ref)
    log(f"  GATE1c fixed7: n={wc_fixed7['n_tris']} single={wc_fixed7['single_window_reconstructed']} "
        f"multi={wc_fixed7['multi_window_or_unreconstructed']} frac={wc_fixed7['multi_window_frac']} "
        f"per_family={wc_fixed7['per_family']} passed={wc_fixed7['passed']}")
    gate1c_identical_to_fixed6 = (
        wc_fixed7["single_window_reconstructed"] == wc_fixed6["single_window_reconstructed"]
        and wc_fixed7["multi_window_or_unreconstructed"] == wc_fixed6["multi_window_or_unreconstructed"]
        and wc_fixed7["per_family"] == wc_fixed6["per_family"])

    rect_fixed7 = G4.family_rect_membership_check(FIXED7_DIR, "fixed7", tex_ref)
    rect_fixed6 = G4.family_rect_membership_check(FIXED6_DIR, "fixed6_crosscheck", tex_ref)
    log(f"  family rect membership fixed7: {rect_fixed7['out_of_region_by_family']} "
        f"zero_area={rect_fixed7['zero_area_by_family']} passed={rect_fixed7['passed']}")
    rect_identical_to_fixed6 = (rect_fixed7["out_of_region_by_family"] == rect_fixed6["out_of_region_by_family"]
                                 and rect_fixed7["zero_area_by_family"] == rect_fixed6["zero_area_by_family"]
                                 and rect_fixed7["tris_checked_by_family"] == rect_fixed6["tris_checked_by_family"])

    # direct UV-byte identity, FIXED6 vs FIXED7, over all 20 touched blocks
    uv_diffs = 0
    uv_degen_fixed7 = 0
    for (bx, by) in FOOTPRINT:
        a = M.read_ff9mesh(F2.terr_path(FIXED6_DIR, bx, by))
        f = M.read_ff9mesh(F2.terr_path(FIXED7_DIR, bx, by))
        for j in range(a["vcount"]):
            if a["uvs"][j] != f["uvs"][j]:
                uv_diffs += 1
        for t in range(len(f["indices"]) // 3):
            tri = f["indices"][3 * t:3 * t + 3]
            if F2.uv_degenerate([(f["uvs"][j][0], f["uvs"][j][1]) for j in tri]):
                uv_degen_fixed7 += 1
    log(f"  direct UV-byte diff FIXED6 vs FIXED7: {uv_diffs} (must be 0 -- round 7 is Y/normal-only); "
        f"degenerate UV tris on FIXED7 = {uv_degen_fixed7}")

    classifier_carries_over = ref["classifier_carries_over"]  # re-asserted, not re-derived twice
    passed = bool(g1_fixed7["passed"] and wc_fixed7["passed"] and rect_fixed7["passed"]
                  and gate1c_identical_to_fixed6 and rect_identical_to_fixed6 and uv_diffs == 0
                  and uv_degen_fixed7 == 0 and classifier_carries_over)
    return dict(gate1a_fixed7=g1_fixed7, gate1a_fixed6_crosscheck=g1_fixed6,
                gate1c_fixed7=wc_fixed7, gate1c_fixed6_crosscheck=wc_fixed6,
                gate1c_identical_to_fixed6=gate1c_identical_to_fixed6,
                family_rect_fixed7=rect_fixed7, family_rect_fixed6_crosscheck=rect_fixed6,
                family_rect_identical_to_fixed6=rect_identical_to_fixed6,
                uv_byte_diffs_fixed6_vs_fixed7=uv_diffs,
                degenerate_uv_tris_fixed7=uv_degen_fixed7,
                classifier_carries_over=classifier_carries_over,
                note=("family_window_coherence_check/family_rect_membership_check operate over "
                      "SYNTHESIZED (fill) tris keyed by (block,tri) identity + cell membership -- both "
                      "invariant under a Y-only move -- so byte-identity here is the direct consequence "
                      "of stage1_mesh.classifier_carries_over (0 index / 0 X-Z diffs), not a separate "
                      "coincidence; no per-round special-casing is needed or present."),
                passed=passed)


# ====================================================================================================
# (4) GATE 2 SEA-PLAN-DISJOINT on FIXED7 + explicit per-moved-position clearance check
# ====================================================================================================
def sea_gate_and_clearance(ref):
    g2_fixed7 = G.gate2_sea_plan_disjoint(FOOTPRINT, FIXED7_DIR, "fixed7")
    g2_fixed6 = G.gate2_sea_plan_disjoint(FOOTPRINT, FIXED6_DIR, "fixed6_crosscheck")
    log(f"  GATE2 fixed7: A(y-order) viol={g2_fixed7['A_y_order']['fully_submerged_tris_GATING']} "
        f"passed={g2_fixed7['A_y_order']['passed']} | B={g2_fixed7['B_uniformity']['passed']} | "
        f"C={g2_fixed7['C_real_sea_disjoint']['passed']} | overall={g2_fixed7['passed']}")

    R, Q = ref["R"], ref["Q"]
    res = R["res"]
    moved = Q["moved"]
    moved_y_after = {k: k[1] + dv for k, dv in moved.items()}
    below_floor = {k: y for k, y in moved_y_after.items() if y <= 0.5}
    at_or_below_sea = {k: y for k, y in moved_y_after.items() if y <= 0.0}
    min_moved_y = min(moved_y_after.values()) if moved_y_after else None
    log(f"  moved-position clearance: n={len(moved_y_after)} min_Y_after={min_moved_y} "
        f"below_0.5_floor={len(below_floor)} at_or_below_sea={len(at_or_below_sea)}")

    passed = bool(g2_fixed7["passed"] and not below_floor and not at_or_below_sea)
    return dict(gate2_fixed7=g2_fixed7, gate2_fixed6_crosscheck=g2_fixed6,
                moved_position_clearance=dict(
                    n_moved=len(moved_y_after), min_Y_after=min_moved_y,
                    below_0p5_floor=len(below_floor), at_or_below_sea_y0=len(at_or_below_sea),
                    sample_below_floor=list(below_floor.items())[:5]),
                passed=passed)


# ====================================================================================================
# (5) CONTRACT MATRIX v5 -- R1+R2+R3 on FIXED7 + FIXED6 crosscheck + stock calibration control.  Round
#     7's moves are ALL interior (min r_crater 11.435u, itself far inside the mound, itself far inside
#     the 20-block footprint) -- R1's XZ-only realized metric MUST be byte-unchanged; measured, not
#     assumed.
# ====================================================================================================
def contract_matrix():
    stock_cand = CMG.load_candidate("stock_ecotone_13-15_11-12", None, core_blocks=CMG.ECOTONE_CORE)
    stock_row = CMG.run_matrix_on(stock_cand)

    contract_fixed7 = G.contract_rerun(FIXED7_DIR, "rung_f_FIXED7")
    contract_fixed6 = G.contract_rerun(FIXED6_DIR, "rung_f_FIXED6_crosscheck")
    log(f"  stock calibration control: overall={stock_row['overall']}")
    log(f"  fixed6: R1={contract_fixed6['R1']['verdict']} R2={contract_fixed6['R2']['verdict']} "
        f"R3={contract_fixed6['R3']['verdict']} overall={contract_fixed6['overall']}")
    log(f"  fixed7: R1={contract_fixed7['R1']['verdict']} R2={contract_fixed7['R2']['verdict']} "
        f"R3={contract_fixed7['R3']['verdict']} overall={contract_fixed7['overall']}")
    log(f"  fixed7 R1 measured={contract_fixed7['R1']['measured']} floors={contract_fixed7['R1']['floors']}")

    sea_vertex_flag = contract_fixed7["R1"]["sea_vertex_convention_invalid"]
    convention_invalid_flag = contract_fixed7["R1"]["convention_invalid"]
    expected_floors = dict(boundary_cell=39.953, straddle_cell=44.635, body_tri=42.968)
    floors_match = all(abs(contract_fixed7["R1"]["floors"].get(k, -1) - v) < 0.01
                        for k, v in expected_floors.items())
    r1_unchanged_vs_fixed6 = (contract_fixed7["R1"]["measured"] == contract_fixed6["R1"]["measured"])

    r2_7, r2_6 = contract_fixed7["R2"], contract_fixed6["R2"]
    r3_7, r3_6 = contract_fixed7["R3"], contract_fixed6["R3"]
    r2_keys = ("sat_grass", "sat_any", "fringe", "penetration", "floating")
    r3_keys = ("reachable_backing", "interface", "erosion")
    r2_diff = {k: dict(fixed6=r2_6[k], fixed7=r2_7[k], moved=(r2_6[k] != r2_7[k])) for k in r2_keys}
    r3_diff = {k: dict(fixed6=r3_6[k], fixed7=r3_7[k], moved=(r3_6[k] != r3_7[k])) for k in r3_keys}
    r2_any_moved = any(v["moved"] for v in r2_diff.values())
    r3_any_moved = any(v["moved"] for v in r3_diff.values())
    log(f"  R2 diff fixed6->fixed7: {r2_diff}  any_moved={r2_any_moved}")
    log(f"  R3 diff fixed6->fixed7: {r3_diff}  any_moved={r3_any_moved}")

    # -----------------------------------------------------------------------
    # R1 REALIZED, falsifier convention (rung_f_falsify.py, XZ-only by construction)
    r1_fixed7 = G.r1_realized(FIXED7_DIR, "fixed7")
    r1_fixed6 = G.r1_realized(FIXED6_DIR, "fixed6_crosscheck")
    expected_headline = dict(boundary_cell=46.826, straddle_cell=48.882, body_tri=49.547)
    r1_matches_headline = (r1_fixed7["measured"] == expected_headline)
    r1_unchanged_falsifier = (r1_fixed7["measured"] == r1_fixed6["measured"])
    log(f"  R1 REALIZED fixed7: {r1_fixed7['measured']} verdict={r1_fixed7['verdict']} "
        f"matches_headline={r1_matches_headline} unchanged_vs_fixed6={r1_unchanged_falsifier}")

    contract_matrix_green = (
        contract_fixed7["R1"]["verdict"] == "PASS"
        and contract_fixed7["R2"]["verdict"] == "PASS"
        and contract_fixed7["R3"]["verdict"] == "PASS"
        and contract_fixed7["overall"] == "PASS"
        and stock_row["overall"] == "PASS"
        and sea_vertex_flag is True
        and convention_invalid_flag is False
        and floors_match
        and r1_matches_headline
        and r1_unchanged_falsifier
        and r1_fixed7["verdict"] == "PASS")

    return dict(
        stock_calibration_overall=stock_row["overall"],
        fixed6_crosscheck=contract_fixed6, fixed7=contract_fixed7,
        fixed7_R1_sea_vertex_convention_invalid=sea_vertex_flag,
        fixed7_R1_convention_invalid=convention_invalid_flag,
        floors_match_expected=floors_match,
        R1_gate_metric_unchanged_vs_fixed6=r1_unchanged_vs_fixed6,
        R2_diff_fixed6_vs_fixed7=r2_diff, R2_any_number_moved=r2_any_moved,
        R3_diff_fixed6_vs_fixed7=r3_diff, R3_any_number_moved=r3_any_moved,
        r1_realized_fixed7=r1_fixed7, r1_realized_fixed6_crosscheck=r1_fixed6,
        r1_realized_expected_headline=expected_headline,
        r1_realized_matches_headline=r1_matches_headline,
        r1_realized_unchanged_vs_fixed6=r1_unchanged_falsifier,
        contract_matrix_green=contract_matrix_green,
        note=("all 3 moved positions are interior -- min r_crater 11.435u -- so R1's XZ-only realized "
              "standoff is expected byte-identical vs FIXED6 (rounds 5 and 6 established the same "
              "identity for the same reason: the metric is XZ-only by construction and Y never enters "
              "it)."),
        passed=bool(contract_matrix_green and not r2_any_moved and not r3_any_moved
                    and r1_unchanged_vs_fixed6))


# ====================================================================================================
# (6) BYTE-RIGIDITY vs FIXED6, POSITION/NORMAL-SCOPED (expected set re-derived independently, above),
#     CONFINED TO THE BUILD'S DECLARED CHANGE SET -- the round's own declared totals (16/3/12/36/1) are
#     asserted as exact figures, not just "0 unexpected".
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
    n_files_with_a_planned_vertex = 0
    for b in touched:
        a = M.read_ff9mesh(F2.terr_path(FIXED6_DIR, *b))
        f = M.read_ff9mesh(F2.terr_path(FIXED7_DIR, *b))
        rig["uv_bad"] += (a["uvs"] != f["uvs"])
        rig["tan_bad"] += (a["tangents"] != f["tangents"])
        rig["idx_bad"] += (a["indices"] != f["indices"])
        rig["vcount_bad"] += (a["vcount"] != f["vcount"])
        planned = plan[b]
        if planned:
            n_files_with_a_planned_vertex += 1
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
    rig["n_files_with_a_planned_vertex"] = n_files_with_a_planned_vertex

    declared_matches = dict(
        vertex_entries=(ref["n_vert_entries"] == N_VERT_ENTRIES_EXPECTED),
        normal_entries=(ref["n_nrm_vids"] == N_NRM_VIDS_EXPECTED),
        moved_positions=(len(ref["Q"]["moved"]) == N_MOVED_POSITIONS_EXPECTED),
        moved_tris=(ref["n_moved_tris"] == N_MOVED_TRIS_EXPECTED),
        moved_tris_kept=(sum(len(v) for v in ref["moved_tris_kept"].values()) == N_MOVED_TRIS_KEPT_EXPECTED),
        files_touched=(n_files_with_a_planned_vertex == N_TERRAIN_DIRTY_EXPECTED))

    rigidity_ok = bool(
        rig["uv_bad"] == 0 and rig["tan_bad"] == 0 and rig["idx_bad"] == 0 and rig["vcount_bad"] == 0
        and rig["pos_unexpected"] == 0 and rig["pos_xz_moved"] == 0 and rig["pos_y_delta_bad"] == 0
        and rig["pos_expected_missing"] == 0
        and rig["nrm_unexpected"] == 0
        and rig["pos_expected_changed"] == rig["pos_expected_total"]
        and rig["nrm_expected_changed"] == rig["nrm_expected_total"]
        and all(declared_matches.values()))
    log(f"  rigidity: {rig}  declared_matches={declared_matches}  ok={rigidity_ok}")
    return dict(counts=rig, per_block_anomalies=per_block, declared_change_set_matches=declared_matches,
                passed=rigidity_ok,
                note=("declared_change_set_matches confines this round's rigidity check to its OWN "
                      "declared totals (16 vertex entries / 3 positions / 12 tris, 2 of them kept / 36 "
                      "normal entries / 1 file) -- not merely 'nothing unexpected changed' but 'exactly "
                      "and only the build's own declared set changed'."))


# ====================================================================================================
# (7) THE SCOPE GATE -- carried-core tris OUTSIDE the spike set are byte-identical to FIXED6.  Round 6
#     minted this check as the mechanical statement of "carried MAY move, but ONLY the census-defined
#     set"; round 7 re-derives it fresh against its own (much smaller) spike/patch set.
# ====================================================================================================
def scope_gate(ref):
    S = ref["S"]
    touched, synth_key, spikes = S["touched"], S["synth_key"], ref["spikes"]
    patch_unknowns = set(ref["Q"]["Ul"])
    f6 = {b: M.read_ff9mesh(F2.terr_path(FIXED6_DIR, *b)) for b in touched}
    f7 = {b: M.read_ff9mesh(F2.terr_path(FIXED7_DIR, *b)) for b in touched}

    kept_touching = kept_outside = 0
    kept_outside_changed = []      # would be a HOLE in the contract
    kept_touching_unchanged = []   # informational -- a touching tri need not itself change
    fill_in_patch = fill_outside = 0
    fill_outside_changed = []

    for b in touched:
        ox, oz = X.block_world_origin(*b)
        d6, d7 = f6[b], f7[b]
        n_tris = len(d6["indices"]) // 3
        for t in range(n_tris):
            tri = d6["indices"][3 * t:3 * t + 3]
            keys = [P.pkey((d6["verts"][j][0] + ox, d6["verts"][j][1], d6["verts"][j][2] + oz))
                    for j in tri]
            touches_spike = any(k in spikes for k in keys)
            pos_changed = any(d6["verts"][j] != d7["verts"][j] for j in tri)
            nrm_changed = any(d6["normals"][j] != d7["normals"][j] for j in tri)
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
        note=("kept_outside_changed_count and fill_outside_changed_count must both be 0 -- the "
              "mechanical statement of round 6's contract change, still load-bearing this round: "
              "carried geometry MAY move only inside the census-defined spike set (plus fill "
              "graph-adjacent to it), never elsewhere. kept_touching_but_unchanged is informational "
              "only."))
    passed = bool(result["carried_core_frozen"] and result["fill_outside_patch_frozen"])
    result["passed"] = passed
    log(f"  scope gate: kept touching={kept_touching} outside={kept_outside} "
        f"outside_changed={len(kept_outside_changed)} | fill in_patch={fill_in_patch} "
        f"outside={fill_outside} outside_changed={len(fill_outside_changed)} passed={passed}")
    return result


# ====================================================================================================
# (8) THE CRATER + ROUND 7's OWN NEW GUARDS, re-derived independently.
#     (a) basin disc byte-frozen; (b) carried rim-base multiset identical outside the spike site;
#     (c) THE BASIN REFERENCE TRAP margin, re-measured; (d) round 6's four apexes byte-frozen and NOT
#     re-selected by the wider rule; (e) the widened census's self-termination (FIXED6 -> 1, FIXED7 -> 0).
#     (d) and (e) call uvf_fix7.py's OWN helper functions (_round6_apexes / _prior_fixes_intact /
#     _recensus) directly -- these are the exact functions the build's own stage_verify calls, so this is
#     the "re-execute the mechanism" discipline applied to the round's bespoke checks, not merely its
#     stage1-4 solve.
# ====================================================================================================
def crater_and_round7_guards(ref):
    S, R, C, Q = ref["S"], ref["R"], ref["C"], ref["Q"]
    touched = S["touched"]
    spikes = ref["spikes"]
    res = R["res"]

    f6 = {b: M.read_ff9mesh(F2.terr_path(FIXED6_DIR, *b)) for b in touched}
    f7 = {b: M.read_ff9mesh(F2.terr_path(FIXED7_DIR, *b)) for b in touched}

    # --- (a)+(b) the crater, measured directly from bytes ------------------------------------------
    basin_bytes_changed = 0
    rim_before, rim_after = [], []
    basin_before, basin_after = [], []
    for b in touched:
        ox, oz = X.block_world_origin(*b)
        d6, d7 = f6[b], f7[b]
        for j in range(d6["vcount"]):
            x6, y6, z6 = d6["verts"][j][0] + ox, d6["verts"][j][1], d6["verts"][j][2] + oz
            k = P.pkey((x6, y6, z6))
            r = F7.rc(k)
            if r <= F7.BASIN_R:
                basin_before.append(y6)
                basin_after.append(d7["verts"][j][1])
                if d6["verts"][j] != d7["verts"][j]:
                    basin_bytes_changed += 1
            if r <= F7.MOUND_R and k not in spikes:
                is_kept = any(not sy for (_bb, _tt, sy) in S["tri_index"].get(k, ()))
                if is_kept:
                    rim_before.append(round(y6, 6))
                    rim_after.append(round(d7["verts"][j][1], 6))
    crater_sacred = dict(
        basin=dict(center=list(F7.BASIN_C), radius_u=F7.BASIN_R,
                   n_vertex_entries_inside=len(basin_before),
                   n_position_groups_inside=len(R["basin_keys"]),
                   vertex_bytes_changed=basin_bytes_changed,
                   y_before=P.stats(basin_before), y_after=P.stats(basin_after),
                   byte_frozen=(basin_bytes_changed == 0)),
        rim_base=dict(
            scope=f"every CARRIED vertex entry within {F7.MOUND_R}u of the crater centre, spike excluded",
            n_entries=len(rim_before),
            distribution_before=P.stats(rim_before), distribution_after=P.stats(rim_after),
            multiset_identical=(sorted(rim_before) == sorted(rim_after)),
            entries_differing=sum(1 for a, b2 in zip(rim_before, rim_after) if a != b2)),
        ok=bool(basin_bytes_changed == 0 and sorted(rim_before) == sorted(rim_after)))
    log(f"  crater: basin bytes changed={basin_bytes_changed}; rim-base multiset identical="
        f"{crater_sacred['rim_base']['multiset_identical']} over {len(rim_before)} carried entries")

    # --- (c) THE BASIN REFERENCE TRAP margin, re-measured (already computed in stage2/stage3, re-read
    #     here rather than recomputed, since R/C were derived fresh in THIS script's own call to
    #     uvf_fix7.stage1-4 above -- not read from the JSON report) --------------------------------
    rim_ring = C["rim_ring"]
    rim_max_res = R["rim_max_res"]
    rim_crest_clear_of_gate = bool(rim_max_res is not None and rim_max_res < F7.RIM_CREST_MAX_RES_T)
    rim_crest_vertices_in_spike_set = sum(1 for k in rim_ring if k in spikes)
    basin_trap_margin = dict(
        rim_crest_n=len(rim_ring),
        rim_crest_max_residual=(None if rim_max_res is None else round(rim_max_res, 4)),
        residual_gate=F7.SPIKE_RES_T,
        clearance=(None if rim_max_res is None else round(F7.SPIKE_RES_T - rim_max_res, 4)),
        rim_crest_max_residual_lt_gate=rim_crest_clear_of_gate,
        rim_crest_vertices_in_spike_set=rim_crest_vertices_in_spike_set,
        rim_crest_excluded=(rim_crest_vertices_in_spike_set == 0),
        rim_crest_vertices_passing_an_arm=sum(1 for k in rim_ring if C["arm_of"](k) is not None))
    log(f"  BASIN TRAP margin: rim-crest max residual {rim_max_res:.4f} vs gate {F7.SPIKE_RES_T} "
        f"(clearance {F7.SPIKE_RES_T - rim_max_res:.4f}); crest vertices in spike set "
        f"{rim_crest_vertices_in_spike_set}; passing an arm "
        f"{basin_trap_margin['rim_crest_vertices_passing_an_arm']}")

    # --- census-shape guards, re-derived directly from C/Q (fresh in this script) -------------------
    census_selects_expected_count = (len(spikes) == F7.N_EXPECTED_SPIKES)
    arm_hist = dict(sorted(Counter(C["arm_of"](k) or "none" for k in spikes).items()))
    every_spike_passes_an_arm = all(C["arm_of"](k) is not None for k in spikes)
    log(f"  census shape: n_spikes={len(spikes)} (expected {F7.N_EXPECTED_SPIKES}) arm_hist={arm_hist} "
        f"every_spike_passes_an_arm={every_spike_passes_an_arm}")

    # --- (d) round 6's four apexes, re-verified via uvf_fix7.py's OWN helper -------------------------
    round6_keys = set(F7._round6_apexes(S))
    round6_apexes_not_reselected = (len(round6_keys & spikes) == 0)
    prior = F7._prior_fixes_intact(S, R, C, Q, None, f6, f7, res)
    log(f"  round6 apexes: reselected_by_wider_rule={len(round6_keys & spikes)} "
        f"all_four_intact={prior['round6']['all_four_intact']}")
    log(f"  round5 seal intact={prior['round5']['seal_intact']}  the_one dip {prior['the_one']['dip_before']}"
        f" -> {prior['the_one']['dip_after']}")

    # --- (e) the widened census's self-termination, via uvf_fix7.py's OWN _recensus helper ----------
    recensus_fixed7 = F7._recensus(FIXED7_DIR, touched, S["synth_key"])
    recensus_fixed6 = F7._recensus(FIXED6_DIR, touched, S["synth_key"])
    census_now_empty = (recensus_fixed7["n_qualifying"] == 0)
    census_was_exactly_one_on_fixed6 = (recensus_fixed6["n_qualifying"] == F7.N_EXPECTED_SPIKES)
    log(f"  re-census from disk: FIXED6 -> {recensus_fixed6['n_qualifying']} qualifiers, "
        f"FIXED7 -> {recensus_fixed7['n_qualifying']} qualifiers (must be 0)")

    round7_new_guards = dict(
        n_expected_spikes=F7.N_EXPECTED_SPIKES,
        census_selects_expected_count=census_selects_expected_count,
        arm_hist=arm_hist,
        every_spike_passes_an_arm=every_spike_passes_an_arm,
        THE_BASIN_REFERENCE_TRAP=basin_trap_margin,
        round6_apexes_reselected=len(round6_keys & spikes),
        round6_apexes_not_reselected=round6_apexes_not_reselected,
        round6_apexes_byte_frozen=prior["round6"]["all_four_intact"],
        round5_seal_intact=prior["round5"]["seal_intact"],
        the_one_dip_before=prior["the_one"]["dip_before"],
        the_one_dip_after=prior["the_one"]["dip_after"],
        recensus_from_disk=dict(fixed6_n_qualifying=recensus_fixed6["n_qualifying"],
                                fixed7_n_qualifying=recensus_fixed7["n_qualifying"],
                                census_was_exactly_one_on_fixed6=census_was_exactly_one_on_fixed6,
                                census_now_empty=census_now_empty),
        passed=bool(census_selects_expected_count and every_spike_passes_an_arm
                    and basin_trap_margin["rim_crest_max_residual_lt_gate"]
                    and basin_trap_margin["rim_crest_excluded"]
                    and round6_apexes_not_reselected and prior["round6"]["all_four_intact"]
                    and prior["round5"]["seal_intact"] and census_now_empty
                    and census_was_exactly_one_on_fixed6))

    # --- also invoke uvf_fix7.py's OWN stage_guards on these SAME fresh S/R/C/Q, as a second, official
    #     cross-check (this is the exact code path the build itself gates on, re-executed here rather
    #     than trusted from the report).  stage_guards reads back report["stage1_mesh"] (populated by
    #     the SAME stage1 call that produced S), so the ORIGINAL rpt from build_reference_state_r7 is
    #     reused here rather than a fresh dict -----------------------------------------------------------
    stage_guards_all_pass = F7.stage_guards(ref["rpt"], S, R, C, Q)

    result = dict(crater_sacred=crater_sacred, round7_new_guards=round7_new_guards,
                  fix7_own_stage_guards=ref["rpt"]["stop_guards"],
                  fix7_own_stage_guards_all_pass=stage_guards_all_pass,
                  passed=bool(crater_sacred["ok"] and round7_new_guards["passed"] and stage_guards_all_pass))
    log(f"  crater_and_round7_guards passed={result['passed']} "
        f"(fix7's own stage_guards all_pass={stage_guards_all_pass})")
    return result


# ====================================================================================================
# (9) ONLY EXPECTED FILES CHANGED -- full-tree sha256 diff FIXED6 vs FIXED7
# ====================================================================================================
def tree_diff(ref):
    import hashlib

    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    S = ref["S"]
    touched = S["touched"]
    changed = []
    n6 = n7 = 0
    for p in sorted(FIXED6_DIR.rglob("*")):
        if p.is_file():
            n6 += 1
            rel = p.relative_to(FIXED6_DIR)
            other = FIXED7_DIR / rel
            if not other.exists() or sha(p) != sha(other):
                changed.append(str(rel))
    for p in FIXED7_DIR.rglob("*"):
        if p.is_file():
            n7 += 1
    expected_files = {str(F2.terr_path(FIXED6_DIR, *b).relative_to(FIXED6_DIR)) for b in touched
                       if b in ref["plan"] and ref["plan"][b]}
    result = dict(
        n_files_fixed6=n6, n_files_fixed7=n7, n_changed=len(changed), changed_files=changed,
        n_terrain_changed=sum(1 for r in changed if "Terrain" in r),
        n_non_terrain_changed=sum(1 for r in changed if "Terrain" not in r),
        unexpected=[r for r in changed if r not in expected_files],
        expected_not_changed=[r for r in expected_files if r not in changed],
        matches_expected_count=(len(changed) == N_TERRAIN_DIRTY_EXPECTED == len(expected_files)),
        both_trees_180_files=(n6 == N_FILES == n7))
    log(f"  tree diff: {len(changed)} files changed (expect {N_TERRAIN_DIRTY_EXPECTED} Terrain-only); "
        f"unexpected={result['unexpected']} expected_not_changed={result['expected_not_changed']}")
    passed = bool(result["matches_expected_count"] and not result["unexpected"]
                  and not result["expected_not_changed"] and result["n_non_terrain_changed"] == 0
                  and result["both_trees_180_files"])
    result["passed"] = passed
    return result


# ====================================================================================================
def main():
    assert FIXED7_DIR.exists(), f"missing target tree: {FIXED7_DIR}"
    result = {}

    log("=" * 100)
    log("(0) RE-DERIVE round 7's mechanism from disk (uvf_fix7.py stage1-4, re-executed)")
    log("=" * 100)
    ref = build_reference_state_r7()
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
    log("(1) STAGE4 PLUMBING re-run FRESH on FIXED7")
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
    log("(3) STANDING TEXTURE GATES, re-measured + verified byte-unchanged vs FIXED6")
    log("=" * 100)
    tex = texture_gates_unchanged(ref)
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
    log("(6) BYTE-RIGIDITY vs FIXED6 (position/normal-scoped, confined to the declared change set)")
    log("=" * 100)
    rig = byte_rigidity(ref)
    result["byte_rigidity"] = rig

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(7) THE SCOPE GATE -- carried-core tris outside the spike set are byte-identical to FIXED6")
    log("=" * 100)
    scope = scope_gate(ref)
    result["scope_gate"] = scope

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(8) THE CRATER + round 7's own new guards (basin trap margin, round6/round5 intactness, "
        "self-termination)")
    log("=" * 100)
    crater = crater_and_round7_guards(ref)
    result["crater_and_round7_guards"] = crater

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(9) ONLY-EXPECTED-FILES full-tree diff")
    log("=" * 100)
    tdiff = tree_diff(ref)
    result["tree_diff"] = tdiff

    # ====================================================================================================
    gate_summary = dict(
        reference_state_resolves_cleanly=result["reference_state"]["resolution_matches_solver_count"],
        independent_solve_matches_report=result["reference_state"]["independent_solve_reproduces_report_moved_set"],
        plumbing_fixed7_all_ok=plumbing["fixed7_all_ok"],
        plumbing_topology_identical_vs_chain=all(plumbing["identical_topology_vs_chain"].values()),
        plumbing_down_facing_at_baseline=plumbing["down_facing_at_baseline"],
        plumbing_down_facing_unchanged_vs_fixed6=plumbing["down_facing_unchanged_vs_fixed6"],
        weld_audit_zero_cracks=weld["ok"],
        texture_gates_pass_and_unchanged=tex["passed"],
        gate2_sea_passes_and_clearance_ok=sea["passed"],
        contract_matrix_green=contract["passed"],
        byte_rigidity_confined_to_declared_change_set=rig["passed"],
        scope_gate_carried_core_frozen=scope["passed"],
        crater_and_round7_guards_pass=crater["passed"],
        tree_diff_ok=tdiff["passed"])
    result["gate_summary"] = gate_summary
    log(f"GATE SUMMARY: {json.dumps(gate_summary, indent=2)}")

    overall = all(gate_summary.values())
    result["overall"] = "PASS" if overall else "FAIL"
    result["meta"] = dict(
        script="uvf_gates7.py", target=str(FIXED7_DIR), base=str(FIXED6_DIR),
        reused_functions_from=(
            "uvf_gates.py (gate1_uv_validity/gate2_sea_plan_disjoint/plumbing_criteria/contract_rerun/"
            "r1_realized, verbatim); uvf_gates4.py (build_reference_state/family_window_coherence_check/"
            "family_rect_membership_check, verbatim); uvf_fix7.py (stage1/stage2/stage3/stage4/"
            "stage_guards, the round's own mechanism, re-executed fresh against on-disk FIXED6 bytes + "
            "the donor/fix5/fix6-report reads -- never the fix7 report's OWN claims, though those are "
            "cross-checked for reproducibility; also _round6_apexes/_prior_fixes_intact/_recensus, the "
            "round's own bespoke helpers, called directly on values derived fresh in this script); "
            "uvf_fix3.py (load_blocks, indirectly via S['f5']); uvf_relief_probe.py (pkey/PARTS/POS_DP)"),
        new_this_round=("plumbing chain extended through FIXED7; weld_audit_all_parts re-targeted "
                        "FIXED6->FIXED7; texture_gates_unchanged re-targeted FIXED6->FIXED7 with an "
                        "explicit note on why the family-aware checks need no per-round special-casing; "
                        "byte_rigidity gains declared_change_set_matches (exact 16/3/12/36/1 totals, not "
                        "just '0 unexpected'); scope_gate re-targeted to round 7's 1-spike/3-unknown "
                        "patch; crater_and_round7_guards (NEW -- the basin reference trap margin as a "
                        "hard stop now that predicate (3) is widened, round 6's four-apex byte-freeze + "
                        "non-reselection via uvf_fix7.py's own _round6_apexes/_prior_fixes_intact "
                        "helpers, the widened census's self-termination via _recensus, and a direct "
                        "cross-check against uvf_fix7.py's own stage_guards() re-run on this script's "
                        "freshly-derived S/R/C/Q); tree_diff re-targeted to the round's 1-file totals"),
        contract_gates_version="contract_mass_gates.py v5 (evolved, live)",
        note=("zero writes outside out/rung_f/uvf_gates7.json; zero git; specimen/FIXED../FIXED5/FIXED6/"
              "FIXED7 trees read-only throughout; the stock ecotone calibration read + uvf_fix7.py's "
              "stage1/stage2 donor + fix5/fix6-report reads are the same read-only install access every "
              "prior round in this arc has used and documented"))

    OUT.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    log("\n" + "=" * 100)
    log(f"OVERALL: {result['overall']}")
    log(f"-> {OUT}")
    return result


if __name__ == "__main__":
    main()
