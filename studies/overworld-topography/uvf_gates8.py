"""RUNG F -- THE ORPHAN-DECAL REDRESS (round 8) -- THE FULL VERIFICATION BATTERY on
FF9CustomMap-world-FIXED8.

FIXED8 (uvf_fix8.py) is the FIRST round in the Rung-F arc to touch CARRIED geometry's TEXTURE rather
than its position: the five knobs' 10 uncatalogued-rect tris (orphaned by rounds 6-7's shaves -- see
uvf_fix8.py's own docstring) are re-clothed with plain dunes mains UVs, through the standing
uvf_fix3/uvf_fix4 one-window path. NO position/normal/tangent/index byte moves anywhere; the round
writes exactly 30 UV vertex entries across 10 tris in 4 Terrain files.

This script follows the uvf_gates5.py / uvf_gates6.py / uvf_gates7.py SHAPE: it re-derives round 8's
own mechanism FRESH from disk (calling uvf_fix8.py's stage1/load_donor/census/census_mapwide/
stage3_cellfield/stage3b_prove_reuse/stage3c_method_a_dunes/stage4_family/stage5_preview verbatim --
the same functions the build itself runs -- never trusting uvf_fix8_report.json's claims except as a
reproduction cross-check), then runs the standing battery plus the checks this round's own contract
change specifically demands: since round 8 is UV-only, the parts of the standing battery that measure
POSITION/TOPOLOGY must come back BYTE-IDENTICAL to FIXED7 (not merely "interior" or "unaffected" as
weaker prior rounds argued) -- everything here is measured, nothing assumed.

EIGHT SECTIONS:
  (0) REFERENCE-STATE re-derivation: uvf_fix8.py's own stage functions re-executed against on-disk
      FIXED7 (round 8's declared INPUT) bytes; the census's act set (10 tris / 5 knobs), the rebuilt
      (quad,ori) field's bit-exact reuse proof, the per-cell window resolution, and the per-target
      family are all reproduced from scratch and cross-checked against uvf_fix8_report.json's own
      numbers (never trusted directly). A fresh independent UV-write PLAN (block -> {vid: target UV})
      is resolved here, mirroring uvf_gates7.py's PASS-1-style discipline applied to a UV-only round.
  (1) STAGE-CHAIN PLUMBING re-run fresh through FIXED8 -- flat-mesh/grid/frame-bounds/weld-near-miss/
      open-edge/down-facing topology must be BYTE-IDENTICAL to FIXED7 (a UV-only round changes zero
      geometry) and consistent with the whole specimen->FIXED7 chain wherever those rounds already
      established it.
  (2) A DEDICATED coincident-position WELD AUDIT, independently written, across ALL 8 PARTS of all 20
      touched blocks, FIXED7 (pre) -> FIXED8 (post) -- this round's OWN contract is "0 moved positions"
      (unlike every prior geometry round in this arc), verified rather than assumed.
  (3) TEXTURE GATES -- GATE 1a zero-uv-area; GATE 1c one-window-coherence over the STANDING synthesized-
      fill population (byte-unchanged vs FIXED7, since round 8 never touches a synthesized tri); a NEW
      one-window-coherence + mains-region-membership check over the 10 RE-CLOTHED CARRIED tris,
      independently reconstructed from this script's own re-derived cell field (not uvf_fix8.py's own
      stage7) -- run on BOTH trees to show FIXED7 fails it (10/10 still wear the rock rect) and FIXED8
      passes it (10/10 now single-window dunes mains); family mains-rect membership (standing, byte-
      unchanged crosscheck); an independent map-wide carried-uncatalogued-in-mound SWEEP proving the
      count drops from 10 (FIXED7) to 0 (FIXED8); a direct UV-byte identity diff FIXED7 vs FIXED8
      confirming exactly 30 vertex entries differ and nothing else.
  (4) GATE 2 SEA-PLAN-DISJOINT on FIXED8 + FIXED7 crosscheck (both purely position-based, so expected
      byte-identical results).
  (5) CONTRACT MATRIX v5 (R1+R2+R3) re-run on FIXED8 + FIXED7 crosscheck + the stock ecotone calibration
      control. Since round 8 moves ZERO position/normal bytes anywhere in the 20-block footprint, R1's
      XZ-only realized standoff (both the contract_mass_gates reading and the falsifier-convention
      REALIZED reading) MUST be byte-identical to FIXED7 -- measured, not assumed, and stricter than
      round 7's "interior" argument since there the geometric predicate had exactly 3 positions to
      leave alone; here it has ALL of them. R2/R3 (texture-derived) are diffed and reported, not
      required unchanged, since the redress deliberately reclassifies 10 tris' UV membership.
  (6) BYTE-RIGIDITY vs FIXED7, UV-SCOPED and CONFINED TO THE BUILD'S DECLARED CHANGE SET: the expected-
      changed vertex-id set is re-derived HERE independently (from this script's own PLAN in section 0,
      never from uvf_fix8_report.json) and the round's own declared totals (30 UV vertex entries / 10
      tris / 4 files) are asserted as upper AND lower bounds -- not just "0 unexpected".
  (7) THE BASIN sacred-disc byte-freeze (trivially true here -- no target lies within 10.78u of the
      basin's 7.92u radius -- audited, not assumed) + declared-totals crosscheck against
      uvf_fix8_report.json's own stage2_census/stage5_reclothe/stage6_apply numbers.
  (8) ONLY EXPECTED FILES CHANGED -- full-tree sha256 diff FIXED7 vs FIXED8 (4 Terrain files, 0
      elsewhere, 180 files present in both trees).

Writes only out/rung_f/uvf_gates8.json + this script. Zero git, zero install writes. specimen/FIXED../
FIXED7/FIXED8 trees read-only throughout; uvf_fix8.py's stage1/load_donor donor read (stock disc-1
Cleyra, READ-ONLY) and the stock ecotone calibration control are the same read-only install access
every prior round in this arc has used and documented.
"""
from __future__ import annotations

import hashlib
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
from ff9mapkit.world import grassland as GR          # noqa: E402

import seam_null_recon as SNR         # noqa: E402  -- FAM_OF
import uvf_stock_census as SC         # noqa: E402  -- classify_tri_plus
import uvf_gates as G                 # noqa: E402  -- gate1a/gate2/plumbing/contract_rerun/r1_realized
import uvf_gates4 as G4                # noqa: E402  -- family_window_coherence_check / family_rect_membership_check / build_reference_state
import contract_mass_gates as CMG     # noqa: E402
import uvf_fix2 as F2                 # noqa: E402  -- terr_path / uv_degenerate
import uvf_fix3 as F3                 # noqa: E402  -- load_blocks / max_pairwise_uv / QUAD_DIAG
import uvf_fix8 as F8                 # noqa: E402  -- stage1/load_donor/census/.../stage5_preview (the round's own mechanism, re-executed)
import uvf_relief_probe as P          # noqa: E402  -- pkey / PARTS / POS_DP / stats

OUT_DIR = HERE / "out" / "rung_f"
SPECIMEN_DIR = G.SPECIMEN_DIR
FIXED_DIR = G.FIXED_DIR
FIXED2_DIR = OUT_DIR / "FF9CustomMap-world-FIXED2"
FIXED3A_DIR = OUT_DIR / "FF9CustomMap-world-FIXED3A"
FIXED4_DIR = OUT_DIR / "FF9CustomMap-world-FIXED4"
FIXED5_DIR = OUT_DIR / "FF9CustomMap-world-FIXED5"
FIXED6_DIR = OUT_DIR / "FF9CustomMap-world-FIXED6"
FIXED7_DIR = OUT_DIR / "FF9CustomMap-world-FIXED7"          # round 8's declared INPUT (== F8.BASE)
FIXED8_DIR = OUT_DIR / "FF9CustomMap-world-FIXED8"          # round 8's declared OUTPUT (== F8.OUT)
FIX8_REPORT = OUT_DIR / "uvf_fix8_report.json"
OUT = OUT_DIR / "uvf_gates8.json"

FOOTPRINT = G.FOOTPRINT
DOWN_FACING_BASELINE = 3          # pre-existing, unrelated down-facing tris measured on every prior round
N_FILES = 180
N_TERRAIN_DIRTY_EXPECTED = 4      # Block[1][17], Block[1][18], Block[2][17], Block[2][18] Terrain
N_ACT_TRIS_EXPECTED = 10
N_KNOBS_EXPECTED = 5
N_UV_VERTEX_ENTRIES_EXPECTED = 30 # 10 tris x 3 verts, no shared vertices across tris

REGION_TOL = 1e-6

assert FIXED7_DIR == F8.BASE, "this script's FIXED7_DIR must be round 8's declared BASE"
assert FIXED8_DIR == F8.OUT, "this script's FIXED8_DIR must be round 8's declared OUT"


def log(m):
    print(m, flush=True)


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ====================================================================================================
# (0) RE-DERIVE round 8's own mechanism from disk (never trust uvf_fix8_report.json's claims) -- calls
#     uvf_fix8.py's stage functions VERBATIM (the same functions the build itself runs), reproduces the
#     act set + rebuilt cell field + resolved windows + family assignment, then resolves an
#     INDEPENDENT UV-write plan from those values (never from the report's own stage5/stage6 numbers).
# ====================================================================================================
def build_reference_state_r8():
    rpt = {"meta": dict(reused_by="uvf_gates8.py")}
    S = F8.stage1(rpt)
    donor, sh, dy = F8.load_donor(rpt)
    act_raw, rejected, orphan = F8.census(rpt, S, donor)
    F8.census_mapwide(rpt, rejected, orphan)

    # normalise the act records EXACTLY as uvf_fix8.py's own main() does (verts/old-uv/cell)
    act = []
    for r in act_raw:
        b = tuple(r["block"])
        bm = S["base"][b]
        ox, oz = X.block_world_origin(*b)
        tri = bm.tris[r["tri"]]
        Pv, U = bm.chan_arrays[F8.CH_POS], bm.chan_arrays[F8.CH_UV]
        w = [(float(Pv[j][0]) + ox, float(Pv[j][1]), float(Pv[j][2]) + oz) for j in tri]
        uv = [(float(U[j][0]), float(U[j][1])) for j in tri]
        act.append(dict(block=b, tri=r["tri"], name=f"({b[0]}, {b[1]})#{r['tri']}",
                        verts_f=w, uv_old=uv, cell=list(F8.own_cell(*F8.centroid_xz(w))),
                        topo=r["topo"], r_crater=r["r_crater"],
                        sigma_max_before=F8.sigma_max(w, uv), emit_family=F8.TARGET_FAMILY))

    field = F8.stage3_cellfield(rpt, S)
    F8.stage3b_prove_reuse(rpt, S, field)                       # asserts misses<=1, refuses otherwise
    resolved = F8.stage3c_method_a_dunes(rpt, S, act, field)
    non_dunes = F8.stage4_family(rpt, S, act)
    for r in act:
        if non_dunes:
            r["emit_family"] = r.get("surround_family", F8.TARGET_FAMILY)
    preview_rows = F8.stage5_preview(rpt, act, resolved)        # asserts in-region/non-degenerate/one-window

    log(f"[ref-state-r8] act={len(act)} knobs={len(rpt['stage2_census']['knobs'])} "
        f"non_dunes={len(non_dunes)} field_cells={len(field)}")

    # --- cross-check vs the on-disk report (never trusted directly, only reproduced) -----------------
    on_disk = json.loads(FIX8_REPORT.read_text(encoding="utf-8"))
    disk_act = on_disk["stage2_census"]["act_set"]
    disk_names = {f"({r['block'][0]}, {r['block'][1]})#{r['tri']}" for r in disk_act}
    our_names = {r["name"] for r in act}
    disk_knob_sets = {frozenset(k["tris"]) for k in on_disk["stage2_census"]["knobs"]}
    our_knob_sets = {frozenset(k["tris"]) for k in rpt["stage2_census"]["knobs"]}
    census_reproduces_report = (disk_names == our_names and disk_knob_sets == our_knob_sets
                                and len(disk_names) == N_ACT_TRIS_EXPECTED
                                and len(disk_knob_sets) == N_KNOBS_EXPECTED)
    log(f"[ref-state-r8] re-executed census reproduces uvf_fix8_report.json's own act set: "
        f"{census_reproduces_report} (disk n={len(disk_names)}, re-derived n={len(our_names)})")

    disk_reclothe = {r["tri"]: r for r in on_disk["stage5_reclothe"]["per_tri"]}
    preview_matches_disk = True
    max_uv_delta = 0.0
    for r in preview_rows:
        d = disk_reclothe.get(r["tri"])
        if d is None:
            preview_matches_disk = False
            continue
        for (u1, v1), (u2, v2) in zip(r["uv_new"], d["uv_new"]):
            max_uv_delta = max(max_uv_delta, abs(u1 - u2), abs(v1 - v2))
    preview_matches_disk = preview_matches_disk and max_uv_delta < 1e-4
    log(f"[ref-state-r8] re-derived emission matches uvf_fix8_report.json's stage5_reclothe: "
        f"{preview_matches_disk} (max |delta| {max_uv_delta:.6g})")

    # --- independent UV-write PLAN: block -> {vid: target (u,v)}, resolved from THIS script's own
    #     act/resolved/field values, never from the report's stage6_apply bookkeeping ----------------
    plan_uv = defaultdict(dict)
    tri_vids = defaultdict(dict)
    for r in act:
        b = tuple(r["block"])
        bm = S["base"][b]
        tri = bm.tris[r["tri"]]
        Pv = bm.chan_arrays[F8.CH_POS]
        ox, oz = X.block_world_origin(*b)
        cell = tuple(r["cell"])
        q, o, _src = resolved[cell]
        fam = r["emit_family"]
        for j in tri:
            vx = float(Pv[j][0]) + ox
            vz = float(Pv[j][2]) + oz
            u, v = GR.ground_uv(vx, vz, cell, q, o, fam)
            plan_uv[b][j] = (float(u), float(v))
        tri_vids[b][r["tri"]] = list(tri)
    n_vid_entries = sum(len(v) for v in plan_uv.values())
    n_files_planned = len(plan_uv)
    log(f"[ref-state-r8] independent UV plan: {n_vid_entries} vertex entries across {n_files_planned} "
        f"files (expected {N_UV_VERTEX_ENTRIES_EXPECTED} / {N_TERRAIN_DIRTY_EXPECTED})")

    return dict(S=S, donor=donor, act=act, rejected=rejected, orphan=orphan, field=field,
                resolved=resolved, non_dunes=non_dunes, preview_rows=preview_rows,
                plan_uv=plan_uv, tri_vids=tri_vids, n_vid_entries=n_vid_entries,
                n_files_planned=n_files_planned,
                census_reproduces_report=census_reproduces_report,
                preview_matches_disk_report=preview_matches_disk,
                max_uv_delta_vs_report=round(max_uv_delta, 6),
                classifier_carries_over=rpt["stage1_mesh"]["classifier_carries_over"],
                rpt=rpt)


# ====================================================================================================
# (1) STAGE-CHAIN PLUMBING re-run fresh -- FIXED8 must be all_ok and BYTE-IDENTICAL (every topology
#     field, including down-facing) to FIXED7, since round 8 moves zero position/normal bytes.
# ====================================================================================================
def run_plumbing_fresh():
    plumb = dict(
        specimen=G.plumbing_criteria(SPECIMEN_DIR, "specimen"),
        fixed_r1=G.plumbing_criteria(FIXED_DIR, "fixed_r1"),
        fixed2=G.plumbing_criteria(FIXED2_DIR, "fixed2"),
        fixed3a=G.plumbing_criteria(FIXED3A_DIR, "fixed3a"),
        fixed4=G.plumbing_criteria(FIXED4_DIR, "fixed4"),
        fixed5=G.plumbing_criteria(FIXED5_DIR, "fixed5"),
        fixed6=G.plumbing_criteria(FIXED6_DIR, "fixed6"),
        fixed7=G.plumbing_criteria(FIXED7_DIR, "fixed7"),
        fixed8=G.plumbing_criteria(FIXED8_DIR, "fixed8"))

    topology_fields = ("flat_mesh_ok", "grid_ok", "frame_bounds_ok", "weld_near_miss_total",
                        "open_edges_above_skirt", "total_down_facing_tris")
    identical_topology_vs_chain = {name: all(plumb[name][f] == plumb["fixed8"][f] for f in topology_fields)
                                   for name in ("specimen", "fixed_r1", "fixed2", "fixed3a", "fixed4",
                                               "fixed5", "fixed6")}
    fixed7_vs_fixed8_all_fields_identical = all(plumb["fixed7"][f] == plumb["fixed8"][f]
                                                for f in topology_fields)
    down_facing_at_baseline = (plumb["fixed8"]["total_down_facing_tris"] == DOWN_FACING_BASELINE)

    log(f"  fixed8: flat={plumb['fixed8']['flat_mesh_ok']} grid={plumb['fixed8']['grid_ok']} "
        f"frame={plumb['fixed8']['frame_bounds_ok']} weld_near_miss={plumb['fixed8']['weld_near_miss_total']} "
        f"down_facing={plumb['fixed8']['total_down_facing_tris']} (baseline {DOWN_FACING_BASELINE}) "
        f"open_edges={plumb['fixed8']['open_edges_above_skirt']} all_ok={plumb['fixed8']['all_ok']}")
    log(f"  fixed7 vs fixed8, ALL topology fields identical (expected true, UV-only round): "
        f"{fixed7_vs_fixed8_all_fields_identical}")
    log(f"  topology fields identical to fixed8 across the rest of the chain: {identical_topology_vs_chain}")

    return dict(
        by_tree={k: v for k, v in plumb.items()},
        identical_topology_vs_chain=identical_topology_vs_chain,
        fixed7_vs_fixed8_all_fields_identical=fixed7_vs_fixed8_all_fields_identical,
        down_facing_baseline=DOWN_FACING_BASELINE,
        down_facing_at_baseline=down_facing_at_baseline,
        fixed8_all_ok=plumb["fixed8"]["all_ok"],
        passed=bool(plumb["fixed8"]["all_ok"] and all(identical_topology_vs_chain.values())
                    and fixed7_vs_fixed8_all_fields_identical and down_facing_at_baseline))


# ====================================================================================================
# (2) DEDICATED coincident-position WELD AUDIT, independently written, over ALL 8 PARTS x 20 blocks,
#     FIXED7 (pre) vs FIXED8 (post) -- round 8's OWN contract is 0 MOVED POSITIONS (a UV-only round);
#     verified directly against the bytes rather than inferred from the plumbing chain.
# ====================================================================================================
def weld_audit_zero_moves():
    touched = FOOTPRINT
    n_positions = 0
    moved_entries = 0
    vcount_drift = []
    parts_seen = Counter()
    uv_moved_entries = 0
    for (bx, by) in touched:
        ox, oz = X.block_world_origin(bx, by)
        for part in P.PARTS:
            rel = M.override_relpath(1, bx, by, part=part)
            p7, p8 = FIXED7_DIR / rel, FIXED8_DIR / rel
            if not p7.exists():
                continue
            parts_seen[part] += 1
            d7 = M.read_ff9mesh(p7)
            d8 = M.read_ff9mesh(p8)
            if d7["vcount"] != d8["vcount"]:
                vcount_drift.append(str(rel))
                continue
            for j in range(d7["vcount"]):
                n_positions += 1
                if d7["verts"][j] != d8["verts"][j]:
                    moved_entries += 1
                if part == "Terrain" and d7["uvs"][j] != d8["uvs"][j]:
                    uv_moved_entries += 1

    result = dict(
        n_vertex_entries_all_parts=n_positions, parts_present=dict(parts_seen),
        vcount_drift_files=vcount_drift, position_entries_moved=moved_entries,
        terrain_uv_entries_moved=uv_moved_entries,
        zero_position_moves=(moved_entries == 0 and not vcount_drift),
        note=("round 8's own contract, unlike every prior geometry round in this arc: 0 moved "
              "positions anywhere, in any of the 8 parts, across all 20 blocks -- audited directly, "
              "not inferred from the plumbing chain's topology invariants."),
        ok=bool(moved_entries == 0 and not vcount_drift))
    log(f"  weld audit (zero-move contract): entries={n_positions} moved={moved_entries} "
        f"vcount_drift={len(vcount_drift)} terrain_uv_moved={uv_moved_entries} ok={result['ok']}")
    return result


# ====================================================================================================
# (3) TEXTURE GATES -- GATE1a, GATE1c standing (unchanged) crosscheck, the NEW carried-orphan window
#     +region check (FIXED7 fails it / FIXED8 passes it), family rect membership standing crosscheck,
#     the map-wide carried-uncatalogued-in-mound sweep (10 -> 0), and a direct UV-byte diff.
# ====================================================================================================
def carried_window_and_rect_check(tree_dir, label, ref):
    """Independently reconstructs the 10 act tris' CURRENT on-disk UVs through this script's own
    re-derived (cell,quad,ori) window in the dunes-mains family -- NOT uvf_fix8.py's own stage7, a
    fresh implementation of the same one-window-per-tri discipline. Run on FIXED7 (expected to FAIL --
    the old UVs are the rock/lichen rect) and FIXED8 (expected to PASS 10/10)."""
    act, resolved = ref["act"], ref["resolved"]
    lo_u, lo_v, hi_u, hi_v = GR.ground_main_region(F8.TARGET_FAMILY)
    rows = []
    single = in_region = 0
    for r in act:
        b = tuple(r["block"])
        p = F2.terr_path(tree_dir, *b)
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=b[0], y=b[1], part="terrain")
        tri = bm.tris[r["tri"]]
        U = bm.chan_arrays[F8.CH_UV]
        uv3 = [(float(U[j][0]), float(U[j][1])) for j in tri]
        cell = tuple(r["cell"])
        q, o, _src = resolved[cell]
        pred = [GR.ground_uv(p3[0], p3[2], cell, q, o, r["emit_family"]) for p3 in r["verts_f"]]
        ok = all(F8.f32(pred[k][c]) == F8.f32(uv3[k][c]) for k in range(3) for c in range(2))
        reg_ok = all(lo_u - REGION_TOL <= u <= hi_u + REGION_TOL
                     and lo_v - REGION_TOL <= v <= hi_v + REGION_TOL for (u, v) in uv3)
        single += ok
        in_region += reg_ok
        rows.append(dict(tri=r["name"], single_window_bit_exact=bool(ok),
                         in_dunes_mains_region=bool(reg_ok),
                         uv_spread=round(F3.max_pairwise_uv(uv3), 6)))
    return dict(label=label, n_tris=len(act), single_window_reconstructed=single,
                in_dunes_mains_region=in_region, spread_ceiling=round(F3.QUAD_DIAG, 6),
                all_single_window=(single == len(act)), all_in_dunes_mains_region=(in_region == len(act)),
                rows=rows, passed=(single == len(act) and in_region == len(act)))


def sweep_uncatalogued_in_mound(tree_dir, S):
    """Independent map-wide sweep -- every CARRIED (non-synthesized) GROUND tri whose UVs classify
    other_uncatalogued (uvf_stock_census.classify_tri_plus, imported not reimplemented), reported
    with its crater distance. A fresh reimplementation of uvf_fix8.py's own stage2/stage7 recensus
    logic, run here against arbitrary trees rather than only FIXED8."""
    touched, synth_key = S["touched"], S["synth_key"]
    n_total = n_in_mound = 0
    rows = []
    for b in touched:
        p = F2.terr_path(tree_dir, *b)
        if not p.exists():
            continue
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=b[0], y=b[1], part="terrain")
        ox, oz = X.block_world_origin(*b)
        Pv, U, T = bm.chan_arrays[F8.CH_POS], bm.chan_arrays[F8.CH_UV], bm.chan_arrays[F8.CH_TAN]
        for t, tri in enumerate(bm.tris):
            if (b, t) in synth_key:
                continue
            topo = X.decode_id(int(round(T[tri[0]][0])))["topograph"]
            fam = SNR.FAM_OF.get(topo)
            if fam is None or GR.TOPO_FAMILY.get(topo) is None:
                continue
            uv = [(float(U[j][0]), float(U[j][1])) for j in tri]
            if SC.classify_tri_plus(fam, uv)[0] != "other_uncatalogued":
                continue
            w = [(float(Pv[j][0]) + ox, float(Pv[j][1]), float(Pv[j][2]) + oz) for j in tri]
            cx, cz = F8.centroid_xz(w)
            r = F8.rc(cx, cz)
            n_total += 1
            im = r <= F8.MOUND_R
            if im:
                n_in_mound += 1
            rows.append(dict(tri=f"({b[0]}, {b[1]})#{t}", r_crater=round(r, 2), in_mound=im))
    return dict(n_carried_uncatalogued_total=n_total, n_carried_uncatalogued_in_mound=n_in_mound,
                rows=rows)


def texture_gates(ref):
    S = ref["S"]
    tex_ref = G4.build_reference_state()   # re-derives the STANDING synthesized-fill family/window field

    # -- GATE1a -----------------------------------------------------------------------------------
    g1_fixed8 = G.gate1_uv_validity(FOOTPRINT, FIXED8_DIR, "fixed8")
    g1_fixed7 = G.gate1_uv_validity(FOOTPRINT, FIXED7_DIR, "fixed7_crosscheck")
    log(f"  GATE1a fixed8: zero_uv_frac={g1_fixed8['zero_uv_area_frac']} "
        f"bit_identical={g1_fixed8['total_bit_identical']} passed={g1_fixed8['passed']}")

    # -- GATE1c, STANDING (synthesized-fill population -- untouched by round 8, must be byte-unchanged)
    wc_fixed8 = G4.family_window_coherence_check(FIXED8_DIR, "fixed8", tex_ref)
    wc_fixed7 = G4.family_window_coherence_check(FIXED7_DIR, "fixed7_crosscheck", tex_ref)
    gate1c_standing_unchanged = (
        wc_fixed8["single_window_reconstructed"] == wc_fixed7["single_window_reconstructed"]
        and wc_fixed8["multi_window_or_unreconstructed"] == wc_fixed7["multi_window_or_unreconstructed"]
        and wc_fixed8["per_family"] == wc_fixed7["per_family"])
    log(f"  GATE1c (standing synthesized-fill pop) fixed8: single={wc_fixed8['single_window_reconstructed']} "
        f"multi={wc_fixed8['multi_window_or_unreconstructed']} passed={wc_fixed8['passed']} "
        f"unchanged_vs_fixed7={gate1c_standing_unchanged}")

    # -- GATE1c, NEW -- the 10 re-clothed CARRIED tris, on both trees ----------------------------
    carried_fixed7 = carried_window_and_rect_check(FIXED7_DIR, "fixed7 (expect FAIL)", ref)
    carried_fixed8 = carried_window_and_rect_check(FIXED8_DIR, "fixed8 (expect PASS)", ref)
    log(f"  GATE1c (10 re-clothed carried tris) fixed7: single_window={carried_fixed7['single_window_reconstructed']}/10 "
        f"in_region={carried_fixed7['in_dunes_mains_region']}/10 (expect 0/10, still the rock rect)")
    log(f"  GATE1c (10 re-clothed carried tris) fixed8: single_window={carried_fixed8['single_window_reconstructed']}/10 "
        f"in_region={carried_fixed8['in_dunes_mains_region']}/10 (expect 10/10)")
    carried_gate_correct = (
        carried_fixed7["single_window_reconstructed"] == 0 and carried_fixed7["in_dunes_mains_region"] == 0
        and carried_fixed8["single_window_reconstructed"] == N_ACT_TRIS_EXPECTED
        and carried_fixed8["in_dunes_mains_region"] == N_ACT_TRIS_EXPECTED)

    # -- family rect membership, STANDING (synthesized-fill population, byte-unchanged crosscheck) --
    rect_fixed8 = G4.family_rect_membership_check(FIXED8_DIR, "fixed8", tex_ref)
    rect_fixed7 = G4.family_rect_membership_check(FIXED7_DIR, "fixed7_crosscheck", tex_ref)
    rect_standing_unchanged = (rect_fixed8["out_of_region_by_family"] == rect_fixed7["out_of_region_by_family"]
                               and rect_fixed8["zero_area_by_family"] == rect_fixed7["zero_area_by_family"]
                               and rect_fixed8["tris_checked_by_family"] == rect_fixed7["tris_checked_by_family"])
    log(f"  family rect membership (standing) fixed8: {rect_fixed8['out_of_region_by_family']} "
        f"passed={rect_fixed8['passed']} unchanged_vs_fixed7={rect_standing_unchanged}")

    # -- the map-wide carried-uncatalogued-in-mound SWEEP: 10 (fixed7) -> 0 (fixed8) ---------------
    sweep_fixed7 = sweep_uncatalogued_in_mound(FIXED7_DIR, S)
    sweep_fixed8 = sweep_uncatalogued_in_mound(FIXED8_DIR, S)
    drop_by_ten = (sweep_fixed7["n_carried_uncatalogued_in_mound"] == N_ACT_TRIS_EXPECTED
                  and sweep_fixed8["n_carried_uncatalogued_in_mound"] == 0)
    log(f"  carried-uncatalogued-in-mound sweep: fixed7={sweep_fixed7['n_carried_uncatalogued_in_mound']} "
        f"-> fixed8={sweep_fixed8['n_carried_uncatalogued_in_mound']} (expect 10 -> 0) "
        f"drop_by_ten={drop_by_ten}  "
        f"total_tree_wide fixed7={sweep_fixed7['n_carried_uncatalogued_total']} "
        f"fixed8={sweep_fixed8['n_carried_uncatalogued_total']}")

    # -- direct UV-byte identity diff, FIXED7 vs FIXED8 --------------------------------------------
    uv_diffs = 0
    uv_degen_fixed8 = 0
    for (bx, by) in FOOTPRINT:
        a = M.read_ff9mesh(F2.terr_path(FIXED7_DIR, bx, by))
        f = M.read_ff9mesh(F2.terr_path(FIXED8_DIR, bx, by))
        for j in range(a["vcount"]):
            if a["uvs"][j] != f["uvs"][j]:
                uv_diffs += 1
        for t in range(len(f["indices"]) // 3):
            tri = f["indices"][3 * t:3 * t + 3]
            if F2.uv_degenerate([(f["uvs"][j][0], f["uvs"][j][1]) for j in tri]):
                uv_degen_fixed8 += 1
    log(f"  direct UV-byte diff FIXED7 vs FIXED8: {uv_diffs} (expect exactly "
        f"{N_UV_VERTEX_ENTRIES_EXPECTED}); degenerate UV tris on FIXED8 = {uv_degen_fixed8}")

    classifier_carries_over = ref["classifier_carries_over"]
    passed = bool(g1_fixed8["passed"] and wc_fixed8["passed"] and gate1c_standing_unchanged
                 and carried_gate_correct and rect_fixed8["passed"] and rect_standing_unchanged
                 and drop_by_ten and uv_diffs == N_UV_VERTEX_ENTRIES_EXPECTED and uv_degen_fixed8 == 0
                 and classifier_carries_over)
    return dict(gate1a_fixed8=g1_fixed8, gate1a_fixed7_crosscheck=g1_fixed7,
                gate1c_standing_fixed8=wc_fixed8, gate1c_standing_fixed7_crosscheck=wc_fixed7,
                gate1c_standing_unchanged=gate1c_standing_unchanged,
                gate1c_carried_orphans_fixed7=carried_fixed7, gate1c_carried_orphans_fixed8=carried_fixed8,
                carried_gate_correct=carried_gate_correct,
                family_rect_standing_fixed8=rect_fixed8, family_rect_standing_fixed7_crosscheck=rect_fixed7,
                family_rect_standing_unchanged=rect_standing_unchanged,
                uncatalogued_in_mound_sweep=dict(fixed7=sweep_fixed7, fixed8=sweep_fixed8,
                                                 drop_by_ten=drop_by_ten),
                uv_byte_diffs_fixed7_vs_fixed8=uv_diffs,
                degenerate_uv_tris_fixed8=uv_degen_fixed8,
                classifier_carries_over=classifier_carries_over,
                passed=passed)


# ====================================================================================================
# (4) GATE 2 SEA-PLAN-DISJOINT on FIXED8 + FIXED7 crosscheck (both purely position-based)
# ====================================================================================================
def sea_gate():
    g2_fixed8 = G.gate2_sea_plan_disjoint(FOOTPRINT, FIXED8_DIR, "fixed8")
    g2_fixed7 = G.gate2_sea_plan_disjoint(FOOTPRINT, FIXED7_DIR, "fixed7_crosscheck")
    log(f"  GATE2 fixed8: A(y-order) viol={g2_fixed8['A_y_order']['fully_submerged_tris_GATING']} "
        f"passed={g2_fixed8['A_y_order']['passed']} | B={g2_fixed8['B_uniformity']['passed']} | "
        f"C={g2_fixed8['C_real_sea_disjoint']['passed']} | overall={g2_fixed8['passed']}")
    unchanged_vs_fixed7 = (g2_fixed8["A_y_order"]["fully_submerged_tris_GATING"]
                           == g2_fixed7["A_y_order"]["fully_submerged_tris_GATING"]
                           and g2_fixed8["passed"] == g2_fixed7["passed"])
    log(f"  GATE2 unchanged vs fixed7 (expected true, purely position-based): {unchanged_vs_fixed7}")
    passed = bool(g2_fixed8["passed"] and unchanged_vs_fixed7)
    return dict(gate2_fixed8=g2_fixed8, gate2_fixed7_crosscheck=g2_fixed7,
                unchanged_vs_fixed7=unchanged_vs_fixed7, passed=passed)


# ====================================================================================================
# (5) CONTRACT MATRIX v5 -- R1+R2+R3 on FIXED8 + FIXED7 crosscheck + stock calibration control.  Round
#     8 moves ZERO position/normal bytes anywhere -- R1's XZ-only realized standoff (both readings)
#     MUST be byte-identical to FIXED7. R2/R3 (texture-derived) are diffed and reported, not required
#     unchanged, since the redress deliberately reclassifies 10 tris' UV membership.
# ====================================================================================================
def contract_matrix():
    stock_cand = CMG.load_candidate("stock_ecotone_13-15_11-12", None, core_blocks=CMG.ECOTONE_CORE)
    stock_row = CMG.run_matrix_on(stock_cand)

    contract_fixed8 = G.contract_rerun(FIXED8_DIR, "rung_f_FIXED8")
    contract_fixed7 = G.contract_rerun(FIXED7_DIR, "rung_f_FIXED7_crosscheck")
    log(f"  stock calibration control: overall={stock_row['overall']}")
    log(f"  fixed7: R1={contract_fixed7['R1']['verdict']} R2={contract_fixed7['R2']['verdict']} "
        f"R3={contract_fixed7['R3']['verdict']} overall={contract_fixed7['overall']}")
    log(f"  fixed8: R1={contract_fixed8['R1']['verdict']} R2={contract_fixed8['R2']['verdict']} "
        f"R3={contract_fixed8['R3']['verdict']} overall={contract_fixed8['overall']}")
    log(f"  fixed8 R1 measured={contract_fixed8['R1']['measured']} floors={contract_fixed8['R1']['floors']}")

    sea_vertex_flag = contract_fixed8["R1"]["sea_vertex_convention_invalid"]
    convention_invalid_flag = contract_fixed8["R1"]["convention_invalid"]
    expected_floors = dict(boundary_cell=39.953, straddle_cell=44.635, body_tri=42.968)
    floors_match = all(abs(contract_fixed8["R1"]["floors"].get(k, -1) - v) < 0.01
                        for k, v in expected_floors.items())
    r1_byte_identical_vs_fixed7 = (contract_fixed8["R1"]["measured"] == contract_fixed7["R1"]["measured"])

    r2_8, r2_7 = contract_fixed8["R2"], contract_fixed7["R2"]
    r3_8, r3_7 = contract_fixed8["R3"], contract_fixed7["R3"]
    r2_keys = ("sat_grass", "sat_any", "fringe", "penetration", "floating")
    r3_keys = ("reachable_backing", "interface", "erosion")
    r2_diff = {k: dict(fixed7=r2_7[k], fixed8=r2_8[k], moved=(r2_7[k] != r2_8[k])) for k in r2_keys}
    r3_diff = {k: dict(fixed7=r3_7[k], fixed8=r3_8[k], moved=(r3_7[k] != r3_8[k])) for k in r3_keys}
    r2_any_moved = any(v["moved"] for v in r2_diff.values())
    r3_any_moved = any(v["moved"] for v in r3_diff.values())
    log(f"  R2 diff fixed7->fixed8 (texture-derived, may move): {r2_diff}  any_moved={r2_any_moved}")
    log(f"  R3 diff fixed7->fixed8: {r3_diff}  any_moved={r3_any_moved}")

    # R1 REALIZED, falsifier convention (rung_f_falsify.py, XZ-only by construction)
    r1_fixed8 = G.r1_realized(FIXED8_DIR, "fixed8")
    r1_fixed7 = G.r1_realized(FIXED7_DIR, "fixed7_crosscheck")
    expected_headline = dict(boundary_cell=46.826, straddle_cell=48.882, body_tri=49.547)
    r1_matches_headline = (r1_fixed8["measured"] == expected_headline)
    r1_realized_byte_identical_vs_fixed7 = (r1_fixed8["measured"] == r1_fixed7["measured"])
    log(f"  R1 REALIZED fixed8: {r1_fixed8['measured']} verdict={r1_fixed8['verdict']} "
        f"matches_headline={r1_matches_headline} byte_identical_vs_fixed7={r1_realized_byte_identical_vs_fixed7}")

    contract_matrix_green = (
        contract_fixed8["R1"]["verdict"] == "PASS"
        and contract_fixed8["R2"]["verdict"] == "PASS"
        and contract_fixed8["R3"]["verdict"] == "PASS"
        and contract_fixed8["overall"] == "PASS"
        and stock_row["overall"] == "PASS"
        and sea_vertex_flag is True
        and convention_invalid_flag is False
        and floors_match
        and r1_matches_headline
        and r1_realized_byte_identical_vs_fixed7
        and r1_fixed8["verdict"] == "PASS")

    return dict(
        stock_calibration_overall=stock_row["overall"],
        fixed7_crosscheck=contract_fixed7, fixed8=contract_fixed8,
        fixed8_R1_sea_vertex_convention_invalid=sea_vertex_flag,
        fixed8_R1_convention_invalid=convention_invalid_flag,
        floors_match_expected=floors_match,
        R1_gate_metric_byte_identical_vs_fixed7=r1_byte_identical_vs_fixed7,
        R2_diff_fixed7_vs_fixed8=r2_diff, R2_any_number_moved=r2_any_moved,
        R3_diff_fixed7_vs_fixed8=r3_diff, R3_any_number_moved=r3_any_moved,
        r1_realized_fixed8=r1_fixed8, r1_realized_fixed7_crosscheck=r1_fixed7,
        r1_realized_expected_headline=expected_headline,
        r1_realized_matches_headline=r1_matches_headline,
        r1_realized_byte_identical_vs_fixed7=r1_realized_byte_identical_vs_fixed7,
        contract_matrix_green=contract_matrix_green,
        note=("round 8 moves ZERO position/normal bytes anywhere in the 20-block footprint (unlike "
              "every prior geometry round in this arc, which could only argue R1 unchanged for an "
              "interior subset) -- so BOTH R1 readings (contract_mass_gates' own + the falsifier's "
              "REALIZED convention) are required BYTE-IDENTICAL to FIXED7, not merely unaffected; "
              "R2/R3 are texture-derived and may legitimately move since 10 tris are deliberately "
              "reclassified from other_uncatalogued to mains_own dunes -- diffed and reported, not "
              "gated on staying fixed."),
        passed=bool(contract_matrix_green and r1_byte_identical_vs_fixed7
                    and r1_realized_byte_identical_vs_fixed7))


# ====================================================================================================
# (6) BYTE-RIGIDITY vs FIXED7, UV-SCOPED, CONFINED TO THE BUILD'S DECLARED CHANGE SET -- the expected-
#     changed vertex-id set comes from THIS script's own independent plan_uv (section 0), and the
#     round's own declared totals (30 UV entries / 10 tris / 4 files) are asserted exactly.
# ====================================================================================================
def byte_rigidity(ref):
    S = ref["S"]
    touched = S["touched"]
    plan_uv = ref["plan_uv"]

    rig = dict(pos_bad=0, nrm_bad=0, tan_bad=0, idx_bad=0, vcount_bad=0,
               uv_expected_changed=0, uv_expected_missing=0, uv_expected_value_bad=0, uv_unexpected=0)
    per_block = {}
    n_files_with_a_planned_vertex = 0
    for b in touched:
        a = M.read_ff9mesh(F2.terr_path(FIXED7_DIR, *b))
        f = M.read_ff9mesh(F2.terr_path(FIXED8_DIR, *b))
        rig["pos_bad"] += (a["verts"] != f["verts"])
        rig["nrm_bad"] += (a["normals"] != f["normals"])
        rig["tan_bad"] += (a["tangents"] != f["tangents"])
        rig["idx_bad"] += (a["indices"] != f["indices"])
        rig["vcount_bad"] += (a["vcount"] != f["vcount"])
        planned = plan_uv.get(b, {})
        if planned:
            n_files_with_a_planned_vertex += 1
        blk_unexp = blk_exp = blk_bad_val = 0
        for j in range(a["vcount"]):
            au, fu = a["uvs"][j], f["uvs"][j]
            changed = (au != fu)
            if j in planned:
                tu, tv = planned[j]
                value_ok = (F8.f32(fu[0]) == F8.f32(tu) and F8.f32(fu[1]) == F8.f32(tv))
                if not value_ok:
                    rig["uv_expected_value_bad"] += 1
                    blk_bad_val += 1
                if changed:
                    rig["uv_expected_changed"] += 1
                    blk_exp += 1
                else:
                    rig["uv_expected_missing"] += 1
            elif changed:
                rig["uv_unexpected"] += 1
                blk_unexp += 1
        if blk_unexp or blk_bad_val:
            per_block[f"{b[0]},{b[1]}"] = dict(unexpected_uv=blk_unexp, bad_value=blk_bad_val,
                                                expected=blk_exp)
    rig["uv_expected_total"] = ref["n_vid_entries"]
    rig["n_files_with_a_planned_vertex"] = n_files_with_a_planned_vertex

    declared_matches = dict(
        uv_vertex_entries=(ref["n_vid_entries"] == N_UV_VERTEX_ENTRIES_EXPECTED),
        act_tris=(len(ref["act"]) == N_ACT_TRIS_EXPECTED),
        knobs=(len(ref["rpt"]["stage2_census"]["knobs"]) == N_KNOBS_EXPECTED),
        files_touched=(n_files_with_a_planned_vertex == N_TERRAIN_DIRTY_EXPECTED))

    rigidity_ok = bool(
        rig["pos_bad"] == 0 and rig["nrm_bad"] == 0 and rig["tan_bad"] == 0
        and rig["idx_bad"] == 0 and rig["vcount_bad"] == 0
        and rig["uv_unexpected"] == 0 and rig["uv_expected_missing"] == 0
        and rig["uv_expected_value_bad"] == 0
        and rig["uv_expected_changed"] == rig["uv_expected_total"]
        and all(declared_matches.values()))
    log(f"  rigidity: {rig}  declared_matches={declared_matches}  ok={rigidity_ok}")
    return dict(counts=rig, per_block_anomalies=per_block, declared_change_set_matches=declared_matches,
                passed=rigidity_ok,
                note=("declared_change_set_matches confines this round's rigidity check to its OWN "
                      "declared totals (30 UV vertex entries / 10 tris / 5 knobs / 4 files) -- not "
                      "merely 'nothing unexpected changed' but 'exactly and only the build's own "
                      "declared set changed, to the exact predicted float32 value'."))


# ====================================================================================================
# (7) THE BASIN sacred-disc byte-freeze + declared-totals crosscheck against uvf_fix8_report.json's
#     own stage2_census/stage5_reclothe/stage6_apply numbers (never trusted, only cross-checked).
# ====================================================================================================
def basin_and_declared_totals(ref):
    touched = ref["S"]["touched"]
    basin_entries = basin_changed = 0
    for b in touched:
        ox, oz = X.block_world_origin(*b)
        d7 = M.read_ff9mesh(F2.terr_path(FIXED7_DIR, *b))
        d8 = M.read_ff9mesh(F2.terr_path(FIXED8_DIR, *b))
        for t in range(len(d8["indices"]) // 3):
            tri = d8["indices"][3 * t:3 * t + 3]
            w = [(d8["verts"][j][0] + ox, d8["verts"][j][1], d8["verts"][j][2] + oz) for j in tri]
            if F8.rc(*F8.centroid_xz(w)) > F8.BASIN_R:
                continue
            for j in tri:
                basin_entries += 1
                if d7["verts"][j] != d8["verts"][j] or d7["uvs"][j] != d8["uvs"][j]:
                    basin_changed += 1
    basin = dict(center=list(F8.BASIN_C), radius_u=F8.BASIN_R, vertex_entries_inside=basin_entries,
                pos_or_uv_bytes_changed=basin_changed, byte_frozen=(basin_changed == 0))
    log(f"  basin: {basin_entries} entries inside, bytes changed={basin_changed} frozen={basin['byte_frozen']}")

    on_disk = json.loads(FIX8_REPORT.read_text(encoding="utf-8"))
    declared = dict(
        n_orphaned_in_mound=on_disk["stage2_census"]["n_orphaned_in_mound"],
        n_knobs=on_disk["stage2_census"]["n_knobs"],
        tris_rewritten=on_disk["stage6_apply"]["tris_rewritten"],
        uv_vertex_entries_rewritten=on_disk["stage6_apply"]["uv_vertex_entries_rewritten"],
        blocks_written=on_disk["stage6_apply"]["blocks_written"],
        report_ok=on_disk.get("ok"))
    declared_matches_constants = dict(
        n_orphaned_in_mound=(declared["n_orphaned_in_mound"] == N_ACT_TRIS_EXPECTED),
        n_knobs=(declared["n_knobs"] == N_KNOBS_EXPECTED),
        tris_rewritten=(declared["tris_rewritten"] == N_ACT_TRIS_EXPECTED),
        uv_vertex_entries_rewritten=(declared["uv_vertex_entries_rewritten"] == N_UV_VERTEX_ENTRIES_EXPECTED),
        n_blocks_written=(len(declared["blocks_written"]) == N_TERRAIN_DIRTY_EXPECTED),
        report_ok_true=(declared["report_ok"] is True))
    log(f"  declared totals (uvf_fix8_report.json, cross-checked not trusted): {declared} "
        f"matches_constants={declared_matches_constants}")
    return dict(basin_sacred=basin, fix8_report_declared=declared,
                declared_matches_constants=declared_matches_constants,
                passed=bool(basin["byte_frozen"] and all(declared_matches_constants.values())))


# ====================================================================================================
# (8) ONLY EXPECTED FILES CHANGED -- full-tree sha256 diff FIXED7 vs FIXED8
# ====================================================================================================
def tree_diff(ref):
    plan_uv = ref["plan_uv"]
    touched = ref["S"]["touched"]
    changed = []
    n7 = n8 = 0
    for p in sorted(FIXED7_DIR.rglob("*")):
        if p.is_file():
            n7 += 1
            rel = p.relative_to(FIXED7_DIR)
            other = FIXED8_DIR / rel
            if not other.exists() or sha256_file(p) != sha256_file(other):
                changed.append(str(rel))
    for p in FIXED8_DIR.rglob("*"):
        if p.is_file():
            n8 += 1
    expected_files = {str(F2.terr_path(FIXED7_DIR, *b).relative_to(FIXED7_DIR)) for b in touched
                      if b in plan_uv and plan_uv[b]}
    result = dict(
        n_files_fixed7=n7, n_files_fixed8=n8, n_changed=len(changed), changed_files=changed,
        n_terrain_changed=sum(1 for r in changed if "Terrain" in r),
        n_non_terrain_changed=sum(1 for r in changed if "Terrain" not in r),
        unexpected=[r for r in changed if r not in expected_files],
        expected_not_changed=[r for r in expected_files if r not in changed],
        matches_expected_count=(len(changed) == N_TERRAIN_DIRTY_EXPECTED == len(expected_files)),
        both_trees_180_files=(n7 == N_FILES == n8))
    log(f"  tree diff: {len(changed)} files changed (expect {N_TERRAIN_DIRTY_EXPECTED} Terrain-only); "
        f"unexpected={result['unexpected']} expected_not_changed={result['expected_not_changed']}")
    passed = bool(result["matches_expected_count"] and not result["unexpected"]
                 and not result["expected_not_changed"] and result["n_non_terrain_changed"] == 0
                 and result["both_trees_180_files"])
    result["passed"] = passed
    return result


# ====================================================================================================
def main():
    assert FIXED8_DIR.exists(), f"missing target tree: {FIXED8_DIR}"
    result = {}

    log("=" * 100)
    log("(0) RE-DERIVE round 8's mechanism from disk (uvf_fix8.py stage1/load_donor/census/.../"
        "stage5_preview, re-executed)")
    log("=" * 100)
    ref = build_reference_state_r8()
    result["reference_state"] = dict(
        n_touched=len(ref["S"]["touched"]), n_act_tris=len(ref["act"]),
        n_knobs=len(ref["rpt"]["stage2_census"]["knobs"]), n_non_dunes=len(ref["non_dunes"]),
        n_vid_entries_resolved=ref["n_vid_entries"], n_files_planned=ref["n_files_planned"],
        census_reproduces_report=ref["census_reproduces_report"],
        preview_matches_disk_report=ref["preview_matches_disk_report"],
        max_uv_delta_vs_report=ref["max_uv_delta_vs_report"],
        classifier_carries_over=ref["classifier_carries_over"])

    log("=" * 100)
    log("(1) STAGE-CHAIN PLUMBING re-run FRESH on FIXED8")
    log("=" * 100)
    plumbing = run_plumbing_fresh()
    result["plumbing_criteria"] = plumbing

    log("=" * 100)
    log("(2) DEDICATED weld audit -- round 8's own contract is ZERO moved positions")
    log("=" * 100)
    weld = weld_audit_zero_moves()
    result["weld_audit_zero_moves"] = weld

    log("=" * 100)
    log("(3) TEXTURE GATES -- GATE1a / GATE1c standing + NEW carried-orphan check / family rect / "
        "uncatalogued-in-mound sweep / UV-byte diff")
    log("=" * 100)
    tex = texture_gates(ref)
    result["texture_gates"] = tex

    log("=" * 100)
    log("(4) GATE 2 SEA-PLAN-DISJOINT + crosscheck")
    log("=" * 100)
    sea = sea_gate()
    result["gate2_sea"] = sea

    log("=" * 100)
    log("(5) CONTRACT MATRIX v5 (R1+R2+R3) + stock calibration control")
    log("=" * 100)
    contract = contract_matrix()
    result["contract_mass_gates_v5"] = contract

    log("=" * 100)
    log("(6) BYTE-RIGIDITY vs FIXED7 (UV-scoped, confined to the declared change set)")
    log("=" * 100)
    rig = byte_rigidity(ref)
    result["byte_rigidity"] = rig

    log("=" * 100)
    log("(7) THE BASIN sacred-disc + declared-totals crosscheck")
    log("=" * 100)
    basin = basin_and_declared_totals(ref)
    result["basin_and_declared_totals"] = basin

    log("=" * 100)
    log("(8) ONLY-EXPECTED-FILES full-tree diff")
    log("=" * 100)
    tdiff = tree_diff(ref)
    result["tree_diff"] = tdiff

    # ====================================================================================================
    gate_summary = dict(
        reference_state_reproduces_report=(ref["census_reproduces_report"]
                                           and ref["preview_matches_disk_report"]),
        plumbing_fixed8_all_ok=plumbing["fixed8_all_ok"],
        plumbing_topology_identical_vs_chain=all(plumbing["identical_topology_vs_chain"].values()),
        plumbing_fixed7_vs_fixed8_byte_identical=plumbing["fixed7_vs_fixed8_all_fields_identical"],
        plumbing_down_facing_at_baseline=plumbing["down_facing_at_baseline"],
        weld_audit_zero_moves=weld["ok"],
        texture_gates_pass=tex["passed"],
        gate2_sea_passes_and_unchanged=sea["passed"],
        contract_matrix_green=contract["passed"],
        byte_rigidity_confined_to_declared_change_set=rig["passed"],
        basin_frozen_and_declared_totals_match=basin["passed"],
        tree_diff_ok=tdiff["passed"])
    result["gate_summary"] = gate_summary
    log(f"GATE SUMMARY: {json.dumps(gate_summary, indent=2)}")

    overall = all(gate_summary.values())
    result["overall"] = "PASS" if overall else "FAIL"
    result["meta"] = dict(
        script="uvf_gates8.py", target=str(FIXED8_DIR), base=str(FIXED7_DIR),
        reused_functions_from=(
            "uvf_gates.py (gate1_uv_validity/gate2_sea_plan_disjoint/plumbing_criteria/contract_rerun/"
            "r1_realized, verbatim); uvf_gates4.py (build_reference_state/family_window_coherence_check/"
            "family_rect_membership_check, verbatim -- STANDING synthesized-fill population only, "
            "correctly byte-unchanged vs FIXED7 since round 8 never touches a synthesized tri); "
            "uvf_fix8.py (stage1/load_donor/census/census_mapwide/stage3_cellfield/stage3b_prove_reuse/"
            "stage3c_method_a_dunes/stage4_family/stage5_preview, the round's own mechanism, re-executed "
            "fresh against on-disk FIXED7 bytes + the donor/fix7-report reads -- never the fix8 report's "
            "OWN claims, though those are cross-checked for reproducibility); uvf_fix3.py (load_blocks/"
            "max_pairwise_uv/QUAD_DIAG, indirectly via S['base']); uvf_stock_census.py (classify_tri_plus, "
            "imported not reimplemented); seam_null_recon.py (FAM_OF); uvf_relief_probe.py (pkey/PARTS/"
            "POS_DP/stats)"),
        new_this_round=("plumbing chain extended through FIXED8 with a STRICT byte-identity requirement "
                        "vs FIXED7 (not merely 'unaffected', since this round moves zero position bytes "
                        "anywhere); weld_audit_zero_moves (NEW -- round 8's own contract is 0 moved "
                        "positions, unlike every prior geometry round, verified across all 8 parts x 20 "
                        "blocks); carried_window_and_rect_check (NEW -- independently reconstructs the 10 "
                        "re-clothed carried tris' UVs through this script's own re-derived cell field, run "
                        "on both FIXED7 [expect FAIL] and FIXED8 [expect PASS] to demonstrate the redress "
                        "mechanically); sweep_uncatalogued_in_mound (NEW -- independent map-wide "
                        "reimplementation of the orphan-census's predicates 1-3, proving the in-mound count "
                        "drops from 10 to 0); contract matrix's R1 requirement upgraded from round 7's "
                        "'interior positions unchanged' to full byte-identity (both the contract_mass_gates "
                        "reading and the falsifier REALIZED reading), since round 8 has no moved positions "
                        "at all; byte_rigidity re-scoped from position/normal-tracking to UV-tracking "
                        "against an independently-resolved plan_uv (never the fix8 report's stage6_apply); "
                        "basin_and_declared_totals (NEW -- cross-checks uvf_fix8_report.json's own numbers "
                        "against the hard-coded round constants, never trusting them directly); tree_diff "
                        "re-targeted to the round's 4-file totals"),
        contract_gates_version="contract_mass_gates.py v5 (evolved, live)",
        note=("zero writes outside out/rung_f/uvf_gates8.json; zero git; specimen/FIXED../FIXED6/FIXED7/"
              "FIXED8 trees read-only throughout; the stock ecotone calibration read + uvf_fix8.py's "
              "stage1/load_donor donor reads (stock disc-1 Cleyra, READ-ONLY) are the same read-only "
              "install access every prior round in this arc has used and documented"))

    OUT.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    log("\n" + "=" * 100)
    log(f"OVERALL: {result['overall']}")
    log(f"-> {OUT}")
    return result


if __name__ == "__main__":
    main()
