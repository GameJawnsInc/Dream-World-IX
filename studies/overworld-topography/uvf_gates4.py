"""RUNG F UV-FIX ROUND 4 -- THE ROOTS RE-CLOTHE -- THE FULL VERIFICATION BATTERY on
FF9CustomMap-world-FIXED4.

FIXED4 (uvf_fix4.py) re-clothes 102 of the 2305 synthesized tris (the ones whose nearest kept ground
family is dunes/desert -- the root-wedge hole-fill through the donut) with the kit's own
grassland.ground_uv(x,z,cell,quad,ori,family) mains translation, leaving the other 2203 byte-identical
grass. Positions/normals/tangents(IDALL topo)/indices are untouched everywhere; only 306 UV verts on
102 tris in 4 files move.

SIX CHECKS, all family-aware where the round's own change requires it (reusing uvf_gates.py's
functions verbatim for the parts round 4 does NOT touch):
  (1) GATE 1a UV-VALIDITY on FIXED4          -- zero-uv-area frac <= 0.0005, bit-identical grep == 0.
  (2) GATE 1c ONE-WINDOW-COHERENCE, FAMILY-AWARE -- NEW this round: generalizes uvf_gates3.py's
      window_coherence_check so each of the 2305 synthesized tris is reconstructed from ONE
      (cell,quad,ori) window THROUGH ITS OWN ASSIGNED FAMILY's mains (grass/desert/dunes), not
      hardcoded grass. The family field (fam_of_cell / fill_tri_cell) and the (quad,ori) cell field
      (decoded) are RE-DERIVED here by calling uvf_fix4.py's own stage1/stage2/stage3/stage3b
      functions against the on-disk FIXED3A/FIXED4 bytes (not trusted from uvf_fix4_report.json) --
      the same "read the mechanism, not the report" discipline uvf_gates3.py used for round 3.
  (3) FAMILY MAINS-RECT MEMBERSHIP -- every rewritten UV lies inside ITS family's catalogued
      grassland.ground_main_region(family) rect (REGION_EPS slack); untouched grass tris still land in
      the grass region.
  (4) STAGE4 PLUMBING (position-only) -- uvf_gates.py's plumbing_criteria() on FIXED4 must be
      POSITION-IDENTICAL to FIXED3A/specimen/FIXED/FIXED2 (round 4 is UV-only by construction) and
      all_ok.
  (5) CONTRACT MATRIX v5 -- uvf_gates.py's contract_rerun() on FIXED4 + FIXED3A crosscheck + the stock
      ecotone calibration control. R1's realized triple must be UNCHANGED byte-for-byte vs FIXED3A (a
      UV-only change cannot move XZ/Y geometry). R2's saturation/arrangement numbers ARE re-derived
      from UV-classified decal/mains-rect membership (contract_mass_gates.label_blind_desert_body), so
      this round explicitly diffs FIXED4's R2 against FIXED3A's and reports whether any number moved
      and whether it stays inside the stock-calibrated band (GATE_CEILINGS).
  (6) BYTE-RIGIDITY vs FIXED3A, FAMILY-SCOPED -- positions/normals/tangents/indices identical
      everywhere; UVs differ ONLY at the vertices of the 102 tris whose assigned family != grass (the
      expected-changed set is computed HERE from the re-derived family field, not read from the fix4
      build's own bookkeeping).

Writes only out/rung_f/uvf_gates4.json + this script. Zero git, zero install writes. FIXED3A/FIXED4/
specimen trees read-only throughout; the stock ecotone calibration read (contract_mass_gates.py's own
control) is the same read-only install access every prior round in this arc has used and documented.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict, Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import mesh as M              # noqa: E402

import uvf_gates as G              # noqa: E402  -- gate1a/gate2/plumbing/contract_rerun/r1_realized, reused verbatim
import uvf_stock_census as USC     # noqa: E402
import contract_mass_gates as CMG  # noqa: E402
import uvf_fix2 as F2              # noqa: E402  -- decode_quad_ori / uv_tri_degen / assign_mains_seeded
import uvf_fix3 as F3              # noqa: E402  -- classify_defective / own_cell / max_pairwise_uv / QUAD_DIAG / CH_UV
import uvf_fix4 as F4              # noqa: E402  -- stage1/stage2/stage3_cellfield/stage3b (the round's own mechanism)

OUT_DIR = HERE / "out" / "rung_f"
SPECIMEN_DIR = G.SPECIMEN_DIR
FIXED_DIR = G.FIXED_DIR
FIXED2_DIR = OUT_DIR / "FF9CustomMap-world-FIXED2"
FIXED3A_DIR = OUT_DIR / "FF9CustomMap-world-FIXED3A"
FIXED4_DIR = OUT_DIR / "FF9CustomMap-world-FIXED4"
OUT = OUT_DIR / "uvf_gates4.json"

FOOTPRINT = G.FOOTPRINT
FAMILIES = ("grass", "desert", "dunes")
ONE_WINDOW_FRAC_CEILING = 0.0005          # same ceiling family used by gate1a/gate1c throughout the arc
REGION_EPS = 0.006                        # transplant.GroundRetile._EPS (uv membership slack), fix4's own


def log(m):
    print(m, flush=True)


# ====================================================================================================
# RE-DERIVE the round's own mechanism from disk (never trust uvf_fix4_report.json's claims)
# ====================================================================================================
def build_reference_state():
    build = json.loads((OUT_DIR / "rung_f_build.json").read_text(encoding="utf-8"))
    touched = [tuple(b) for b in build["compose_diag"]["touched_blocks"]]
    assert len(touched) == 20

    forensics = json.loads((OUT_DIR / "uvf_forensics.json").read_text(encoding="utf-8"))
    apron_keys = set()
    for rec in forensics["records"]:
        if rec.get("uv_verdict") == "degenerate-zero-area" and rec["provenance"] == "apron":
            cx, _cy, cz = rec["centroid"]
            apron_keys.add((tuple(rec["block"]), round(cx, 3), round(cz, 3)))

    scratch = {}
    _spec, a3_meshes, defective, lawful_grass = F4.stage1(scratch, touched, apron_keys)
    fam_of_cell, fill_tri_cell, cell_detail = F4.stage2(scratch, touched, a3_meshes, defective)
    decoded = F4.stage3_cellfield(scratch, defective, lawful_grass)
    windows = F4.stage3b_prove_reuse(scratch, touched, defective, decoded)   # asserts bit-exact reuse

    fam_per_tri = {}
    for d in defective:
        key = (d["block"], d["tri"])
        fam_per_tri[key] = fam_of_cell[fill_tri_cell[key]]
    non_grass_keys = {k for k, f in fam_per_tri.items() if f != "grass"}
    expected_changed_vids = defaultdict(set)
    for d in defective:
        key = (d["block"], d["tri"])
        if key in non_grass_keys:
            for j in d["vids"]:
                expected_changed_vids[d["block"]].add(j)

    log(f"[ref-state] touched={len(touched)} defective={len(defective)} "
        f"fam counts={dict(Counter(fam_per_tri.values()))} non_grass_tris={len(non_grass_keys)}")
    return dict(touched=touched, defective=defective, decoded=decoded, windows=windows,
                fam_per_tri=fam_per_tri, non_grass_keys=non_grass_keys,
                expected_changed_vids=expected_changed_vids, scratch_report=scratch)


# ====================================================================================================
# (2) GATE 1c ONE-WINDOW-COHERENCE, FAMILY-AWARE
# ====================================================================================================
def family_window_coherence_check(target_dir, label, ref):
    touched = ref["touched"]
    defective = ref["defective"]
    decoded = ref["decoded"]
    fam_per_tri = ref["fam_per_tri"]

    meshes = {}
    for (bx, by) in touched:
        p = target_dir / M.override_relpath(1, bx, by, part="Terrain")
        meshes[(bx, by)] = (M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
                             if p.exists() else None)

    n = single = multi = missing = 0
    exc = []
    over_window = 0
    per_family = defaultdict(Counter)
    per_block_multi = defaultdict(int)
    for d in defective:
        key = (d["block"], d["tri"])
        fam = fam_per_tri[key]
        (bx, by) = d["block"]
        bm = meshes.get((bx, by))
        if bm is None:
            missing += 1
            continue
        n += 1
        uvs = bm.chan_arrays[F3.CH_UV]
        uv3 = [(uvs[j][0], uvs[j][1]) for j in d["vids"]]

        cx = sum(p[0] for p in d["vw"]) / 3.0
        cz = sum(p[2] for p in d["vw"]) / 3.0
        cand = [F3.own_cell(cx, cz)] + [F3.own_cell(vx, vz) for (vx, _vy, vz) in d["vw"]]
        ok = False
        for cell in cand:
            if cell not in decoded:
                continue
            q, o, _m = decoded[cell]
            pred = [tuple(F3.G.ground_uv(vx, vz, cell, q, o, fam)) for (vx, _vy, vz) in d["vw"]]
            if all(abs(pred[k][0] - uv3[k][0]) < 5e-6 and abs(pred[k][1] - uv3[k][1]) < 5e-6
                   for k in range(3)):
                ok = True
                break
        single += ok
        per_family[fam]["single" if ok else "multi"] += 1
        if not ok:
            multi += 1
            per_block_multi[f"{bx},{by}"] += 1
        e = F3.max_pairwise_uv(uv3)
        exc.append(e)
        if e > F3.QUAD_DIAG + 1e-9:
            over_window += 1

    exc.sort()
    nn = len(exc)
    multi_frac = (multi / n) if n else None
    passed = (n > 0 and missing == 0 and multi_frac is not None
              and multi_frac <= ONE_WINDOW_FRAC_CEILING + 1e-12)
    return dict(
        label=label, n_tris=n, n_missing_blocks=missing,
        single_window_reconstructed=single, multi_window_or_unreconstructed=multi,
        multi_window_frac=round(multi_frac, 6) if multi_frac is not None else None,
        threshold=ONE_WINDOW_FRAC_CEILING,
        per_family={f: dict(per_family[f]) for f in FAMILIES},
        excursion_p50=round(exc[nn // 2], 5) if nn else None,
        excursion_p90=round(exc[int(0.9 * (nn - 1))], 5) if nn else None,
        excursion_max=round(exc[-1], 5) if nn else None,
        one_window_scale=round(F3.QUAD_DIAG, 5),
        tris_spread_over_one_window_scale=over_window,
        per_block_multi_window_sample=dict(list(sorted(per_block_multi.items(),
                                                        key=lambda kv: -kv[1]))[:10]),
        passed=passed,
        note=("generalizes uvf_gates3.py's window_coherence_check to reconstruct each tri through ITS "
              "OWN assigned family's ground_uv space, not hardcoded grass"))


def grass_only_window_coherence_check(target_dir, label, ref):
    """uvf_gates3.py's ORIGINAL check, hardcoded to grass -- the correct crosscheck for FIXED3A (which
    predates the family re-clothe: all 2305 tris are still grass-space UVs there). Used to confirm
    FIXED3A's own known-good coherence (2304/2305 single-window), NOT gated by this script -- FIXED3A
    is expected to FAIL the family-aware check on the 102 not-yet-reclothed tris (see diagnostic)."""
    touched = ref["touched"]
    defective = ref["defective"]
    decoded = ref["decoded"]

    meshes = {}
    for (bx, by) in touched:
        p = target_dir / M.override_relpath(1, bx, by, part="Terrain")
        meshes[(bx, by)] = (M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
                             if p.exists() else None)

    n = single = multi = 0
    exc = []
    for d in defective:
        (bx, by) = d["block"]
        bm = meshes.get((bx, by))
        if bm is None:
            continue
        n += 1
        uvs = bm.chan_arrays[F3.CH_UV]
        uv3 = [(uvs[j][0], uvs[j][1]) for j in d["vids"]]
        cx = sum(p[0] for p in d["vw"]) / 3.0
        cz = sum(p[2] for p in d["vw"]) / 3.0
        cand = [F3.own_cell(cx, cz)] + [F3.own_cell(vx, vz) for (vx, _vy, vz) in d["vw"]]
        ok = False
        for cell in cand:
            if cell not in decoded:
                continue
            q, o, _m = decoded[cell]
            pred = [tuple(F3.G.ground_uv(vx, vz, cell, q, o, "grass")) for (vx, _vy, vz) in d["vw"]]
            if all(abs(pred[k][0] - uv3[k][0]) < 5e-6 and abs(pred[k][1] - uv3[k][1]) < 5e-6
                   for k in range(3)):
                ok = True
                break
        single += ok
        multi += (not ok)
        exc.append(F3.max_pairwise_uv(uv3))
    exc.sort()
    frac = (multi / n) if n else None
    passed = (n > 0 and frac is not None and frac <= ONE_WINDOW_FRAC_CEILING + 1e-12)
    return dict(label=label, n_tris=n, single_window_reconstructed=single, multi_window=multi,
                multi_window_frac=round(frac, 6) if frac is not None else None, passed=passed)


# ====================================================================================================
# (3) FAMILY MAINS-RECT MEMBERSHIP -- every rewritten UV inside its family's catalogued mains rect
# ====================================================================================================
def family_rect_membership_check(target_dir, label, ref):
    touched = ref["touched"]
    defective = ref["defective"]
    fam_per_tri = ref["fam_per_tri"]
    regions = {f: F3.G.ground_main_region(f) for f in FAMILIES}

    meshes = {}
    for (bx, by) in touched:
        p = target_dir / M.override_relpath(1, bx, by, part="Terrain")
        meshes[(bx, by)] = (M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
                             if p.exists() else None)

    out_of_region = Counter()
    zero_area = Counter()
    n_checked = Counter()
    for d in defective:
        key = (d["block"], d["tri"])
        fam = fam_per_tri[key]
        (bx, by) = d["block"]
        bm = meshes.get((bx, by))
        if bm is None:
            continue
        uvs = bm.chan_arrays[F3.CH_UV]
        uv3 = [(uvs[j][0], uvs[j][1]) for j in d["vids"]]
        lo_u, lo_v, hi_u, hi_v = regions[fam]
        n_checked[fam] += 1
        for (u, v) in uv3:
            if not (lo_u - REGION_EPS <= u <= hi_u + REGION_EPS
                    and lo_v - REGION_EPS <= v <= hi_v + REGION_EPS):
                out_of_region[fam] += 1
        if F2.uv_tri_degen(uv3):
            zero_area[fam] += 1

    passed = (not out_of_region) and (not zero_area)
    return dict(label=label, tris_checked_by_family=dict(n_checked),
                out_of_region_by_family=dict(out_of_region), zero_area_by_family=dict(zero_area),
                regions={f: [round(x, 6) for x in regions[f]] for f in FAMILIES},
                region_eps=REGION_EPS, passed=passed)


# ====================================================================================================
# (6) BYTE-RIGIDITY vs FIXED3A, FAMILY-SCOPED
# ====================================================================================================
def family_scoped_rigidity(ref):
    touched = ref["touched"]
    expected = ref["expected_changed_vids"]
    rig = dict(pos_bad=0, nrm_bad=0, tan_bad=0, idx_bad=0, uv_unexpected=0, uv_expected_found=0,
               uv_expected_total=sum(len(s) for s in expected.values()))
    per_block = {}
    for b in touched:
        a = M.read_ff9mesh(F2.terr_path(FIXED3A_DIR, *b))
        f = M.read_ff9mesh(F2.terr_path(FIXED4_DIR, *b))
        rig["pos_bad"] += (a["verts"] != f["verts"])
        rig["nrm_bad"] += (a["normals"] != f["normals"])
        rig["tan_bad"] += (a["tangents"] != f["tangents"])
        rig["idx_bad"] += (a["indices"] != f["indices"])
        exp = expected.get(b, set())
        blk_unexp = blk_exp = 0
        for j in range(a["vcount"]):
            if a["uvs"][j] != f["uvs"][j]:
                if j in exp:
                    rig["uv_expected_found"] += 1
                    blk_exp += 1
                else:
                    rig["uv_unexpected"] += 1
                    blk_unexp += 1
        if blk_unexp or blk_exp:
            per_block[f"{b[0]},{b[1]}"] = dict(uv_changed_expected=blk_exp, uv_changed_unexpected=blk_unexp,
                                               expected_total=len(exp))
    rig["uv_expected_missing"] = rig["uv_expected_total"] - rig["uv_expected_found"]
    passed = (rig["pos_bad"] == 0 and rig["nrm_bad"] == 0 and rig["tan_bad"] == 0 and rig["idx_bad"] == 0
              and rig["uv_unexpected"] == 0 and rig["uv_expected_missing"] == 0)
    return dict(rigidity=rig, per_block_changed=per_block, passed=passed,
                note=("expected-changed vertex set is the union of d['vids'] over defective tris whose "
                      "RE-DERIVED family != grass (102 tris) -- computed here independently, not read "
                      "from uvf_fix4_report.json's own bookkeeping"))


# ====================================================================================================
def main():
    assert FIXED4_DIR.exists(), f"missing target tree: {FIXED4_DIR}"
    result = {}

    ref = build_reference_state()

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(1) GATE 1a UV-VALIDITY + GATE 2 SEA-PLAN-DISJOINT on FIXED4")
    log("=" * 100)
    g1_fixed4 = G.gate1_uv_validity(FOOTPRINT, FIXED4_DIR, "fixed4")
    g2_fixed4 = G.gate2_sea_plan_disjoint(FOOTPRINT, FIXED4_DIR, "fixed4")
    g1_fixed3a = G.gate1_uv_validity(FOOTPRINT, FIXED3A_DIR, "fixed3a_crosscheck")
    g2_fixed3a = G.gate2_sea_plan_disjoint(FOOTPRINT, FIXED3A_DIR, "fixed3a_crosscheck")
    g1_spec = G.gate1_uv_validity(FOOTPRINT, SPECIMEN_DIR, "specimen_crosscheck")
    log(f"[fixed4]  GATE1a zero_uv_frac={g1_fixed4['zero_uv_area_frac']} "
        f"(<= {G.GATE1_FRAC_CEILING}) bit_identical={g1_fixed4['total_bit_identical']} "
        f"passed={g1_fixed4['passed']}")
    log(f"[fixed4]  GATE2 A={g2_fixed4['A_y_order']['passed']} B={g2_fixed4['B_uniformity']['passed']} "
        f"C={g2_fixed4['C_real_sea_disjoint']['passed']} overall={g2_fixed4['passed']}")
    log(f"[fixed3a crosscheck] GATE1a={g1_fixed3a['passed']} GATE2={g2_fixed3a['passed']}")
    log(f"[specimen crosscheck] GATE1a={g1_spec['passed']} (expect False)")

    groups = USC.sample_groups()
    stock_all_blocks = sorted({b for blocks in groups.values() for b in blocks})
    g1_pooled = G.gate1_uv_validity(stock_all_blocks, None, "stock:pooled_all")
    g2_pooled = G.gate2_sea_plan_disjoint(stock_all_blocks, None, "stock:pooled_all")
    log(f"  stock/POOLED-ALL: GATE1a passed={g1_pooled['passed']} | GATE2 passed={g2_pooled['passed']}")

    result["gate1a_uv_validity"] = dict(fixed4=g1_fixed4, fixed3a_crosscheck=g1_fixed3a,
                                         specimen_crosscheck=g1_spec, stock_pooled_all=g1_pooled)
    result["gate2_sea_plan_disjoint"] = dict(fixed4=g2_fixed4, fixed3a_crosscheck=g2_fixed3a,
                                              stock_pooled_all=g2_pooled)

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(2) GATE 1c ONE-WINDOW-COHERENCE, FAMILY-AWARE -- must PASS on FIXED4")
    log("=" * 100)
    wc_fixed4 = family_window_coherence_check(FIXED4_DIR, "fixed4", ref)
    # FIXED3A crosscheck against the FAMILY-AWARE predicate is DIAGNOSTIC ONLY (not gated): FIXED3A
    # predates the re-clothe, so its 102 not-yet-recoloured tris are STILL grass-space UVs and are
    # EXPECTED to fail a dunes/desert-space prediction -- that failure is the round's own before/after
    # proof, not a regression. The correctly-scoped crosscheck (does FIXED3A hold its OWN documented
    # grass-only coherence) is the grass-hardcoded check below, gated as it was in uvf_gates3.py.
    wc_fixed3a_family_aware_diag = family_window_coherence_check(FIXED3A_DIR, "fixed3a_diagnostic", ref)
    wc_fixed3a_grass = grass_only_window_coherence_check(FIXED3A_DIR, "fixed3a_grass_crosscheck", ref)
    log(f"  [fixed4]  n={wc_fixed4['n_tris']} single={wc_fixed4['single_window_reconstructed']} "
        f"multi={wc_fixed4['multi_window_or_unreconstructed']} frac={wc_fixed4['multi_window_frac']} "
        f"per_family={wc_fixed4['per_family']} passed={wc_fixed4['passed']}")
    log(f"  [fixed3a family-aware, DIAGNOSTIC] single={wc_fixed3a_family_aware_diag['single_window_reconstructed']} "
        f"multi={wc_fixed3a_family_aware_diag['multi_window_or_unreconstructed']} "
        f"per_family={wc_fixed3a_family_aware_diag['per_family']} "
        f"(EXPECTED to fail on the 102 not-yet-reclothed tris -- proves the round's change is real)")
    log(f"  [fixed3a grass-hardcoded crosscheck] n={wc_fixed3a_grass['n_tris']} "
        f"single={wc_fixed3a_grass['single_window_reconstructed']} multi={wc_fixed3a_grass['multi_window']} "
        f"passed={wc_fixed3a_grass['passed']} (must PASS -- FIXED3A's own documented coherence, unaffected)")
    result["gate1c_family_aware_window_coherence"] = dict(
        fixed4=wc_fixed4, fixed3a_family_aware_diagnostic=wc_fixed3a_family_aware_diag,
        fixed3a_grass_hardcoded_crosscheck=wc_fixed3a_grass,
        note=("fixed3a_family_aware_diagnostic is NOT gated -- FIXED3A predates the re-clothe so its "
              "102 tris are still grass-space UVs and correctly read as multi/non-matching against a "
              "dunes/desert-space prediction; that mismatch count (102) exactly equals the round's own "
              "non-grass tri count, which is itself a cross-check that the mechanism is real. The gated "
              "crosscheck is fixed3a_grass_hardcoded_crosscheck (FIXED3A's own known-good coherence, "
              "reproducing uvf_gates3.py's 2304/2305 result unaffected by round 4)."))

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(3) FAMILY MAINS-RECT MEMBERSHIP on FIXED4")
    log("=" * 100)
    rect_fixed4 = family_rect_membership_check(FIXED4_DIR, "fixed4", ref)
    log(f"  [fixed4] checked={rect_fixed4['tris_checked_by_family']} "
        f"out_of_region={rect_fixed4['out_of_region_by_family']} "
        f"zero_area={rect_fixed4['zero_area_by_family']} passed={rect_fixed4['passed']}")
    result["family_rect_membership"] = rect_fixed4

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(4) STAGE4 PLUMBING (position-only) -- FIXED4 must be POSITION-IDENTICAL to specimen/FIXED/"
        "FIXED2/FIXED3A (round 4 is UV-only by construction)")
    log("=" * 100)
    plumb_specimen = G.plumbing_criteria(SPECIMEN_DIR, "specimen")
    plumb_fixed1 = G.plumbing_criteria(FIXED_DIR, "fixed_r1")
    plumb_fixed2 = G.plumbing_criteria(FIXED2_DIR, "fixed2")
    plumb_fixed3a = G.plumbing_criteria(FIXED3A_DIR, "fixed3a")
    plumb_fixed4 = G.plumbing_criteria(FIXED4_DIR, "fixed4")
    positional_fields = ("flat_mesh_ok", "grid_ok", "frame_bounds_ok", "weld_near_miss_total",
                          "total_down_facing_tris", "open_edges_above_skirt")
    identical = {name: all(p[f] == plumb_fixed4[f] for f in positional_fields)
                 for name, p in (("specimen", plumb_specimen), ("fixed_r1", plumb_fixed1),
                                 ("fixed2", plumb_fixed2), ("fixed3a", plumb_fixed3a))}
    log(f"  fixed4: {json.dumps({k: v for k, v in plumb_fixed4.items() if k in positional_fields})}")
    log(f"  position-identical to fixed4: {identical}  fixed4.all_ok={plumb_fixed4['all_ok']}")
    result["plumbing_stage4_criteria"] = dict(
        specimen=plumb_specimen, fixed_r1=plumb_fixed1, fixed2=plumb_fixed2,
        fixed3a=plumb_fixed3a, fixed4=plumb_fixed4,
        identical_vs_fixed4=identical, fixed4_all_ok=plumb_fixed4["all_ok"])

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(5) contract_mass_gates.py v5 R1+R2+R3 on FIXED4 + FIXED3A crosscheck + stock control")
    log("=" * 100)
    stock_cand = CMG.load_candidate("stock_ecotone_13-15_11-12", None, core_blocks=CMG.ECOTONE_CORE)
    stock_row = CMG.run_matrix_on(stock_cand)
    contract_fixed4 = G.contract_rerun(FIXED4_DIR, "rung_f_FIXED4")
    contract_fixed3a = G.contract_rerun(FIXED3A_DIR, "rung_f_FIXED3A_crosscheck")
    log(f"  stock calibration control: overall={stock_row['overall']}")
    log(f"  fixed3a crosscheck: R1={contract_fixed3a['R1']['verdict']} R2={contract_fixed3a['R2']['verdict']} "
        f"R3={contract_fixed3a['R3']['verdict']} overall={contract_fixed3a['overall']}")
    log(f"  fixed4:             R1={contract_fixed4['R1']['verdict']} R2={contract_fixed4['R2']['verdict']} "
        f"R3={contract_fixed4['R3']['verdict']} overall={contract_fixed4['overall']}")
    log(f"  fixed4 R1 measured={contract_fixed4['R1']['measured']} floors={contract_fixed4['R1']['floors']}")

    sea_vertex_flag = contract_fixed4["R1"]["sea_vertex_convention_invalid"]
    convention_invalid_flag = contract_fixed4["R1"]["convention_invalid"]
    expected_floors = dict(boundary_cell=39.953, straddle_cell=44.635, body_tri=42.968)
    floors_match = all(abs(contract_fixed4["R1"]["floors"].get(k, -1) - v) < 0.01
                       for k, v in expected_floors.items())
    r1_unchanged_vs_fixed3a = (contract_fixed4["R1"]["measured"] == contract_fixed3a["R1"]["measured"])

    # R2 DIFF: did the family re-clothe move any R2 number, and does it stay inside the stock band?
    r2_4, r2_3a = contract_fixed4["R2"], contract_fixed3a["R2"]
    r2_keys = ("sat_grass", "sat_any", "fringe", "penetration", "floating")
    r2_diff = {k: dict(fixed3a=r2_3a[k], fixed4=r2_4[k], moved=(r2_3a[k] != r2_4[k])) for k in r2_keys}
    r2_any_moved = any(v["moved"] for v in r2_diff.values())
    r2_in_band = (contract_fixed4["R2"]["verdict"] == "PASS")
    log(f"  R2 diff fixed3a->fixed4: {r2_diff}  any_moved={r2_any_moved}  in_band(PASS)={r2_in_band}")

    r3_unchanged_vs_fixed3a = (contract_fixed4["R3"] == contract_fixed3a["R3"])

    result["contract_mass_gates_v5"] = dict(
        stock_calibration_overall=stock_row["overall"],
        fixed3a_crosscheck=contract_fixed3a, fixed4=contract_fixed4,
        fixed4_R1_sea_vertex_convention_invalid=sea_vertex_flag,
        fixed4_R1_convention_invalid=convention_invalid_flag,
        floors_match_expected=floors_match,
        R1_unchanged_vs_fixed3a=r1_unchanged_vs_fixed3a,
        R2_diff_fixed3a_vs_fixed4=r2_diff, R2_any_number_moved=r2_any_moved,
        R2_stays_inside_stock_band=r2_in_band,
        R3_unchanged_vs_fixed3a=r3_unchanged_vs_fixed3a,
        fixed4_all_green=(contract_fixed4["overall"] == "PASS" and stock_row["overall"] == "PASS"))

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(5b) R1 REALIZED standoff, falsifier convention -- FIXED4 must equal the round-1 headline "
        "46.826/48.882/49.547u (UV changes cannot move XZ/Y)")
    log("=" * 100)
    r1_fixed4 = G.r1_realized(FIXED4_DIR, "fixed4")
    r1_fixed3a = G.r1_realized(FIXED3A_DIR, "fixed3a_crosscheck")
    expected = dict(boundary_cell=46.826, straddle_cell=48.882, body_tri=49.547)
    r1_matches_headline = (r1_fixed4["measured"] == expected)
    r1_unchanged_falsifier = (r1_fixed4["measured"] == r1_fixed3a["measured"])
    log(f"  fixed4: {r1_fixed4['measured']} verdict={r1_fixed4['verdict']} "
        f"matches_headline={r1_matches_headline} unchanged_vs_fixed3a={r1_unchanged_falsifier}")
    result["r1_realized_falsifier_convention"] = dict(
        fixed4=r1_fixed4, fixed3a_crosscheck=r1_fixed3a, expected_headline=expected,
        fixed4_matches_expected_headline=r1_matches_headline,
        fixed4_unchanged_vs_fixed3a=r1_unchanged_falsifier)

    # ----------------------------------------------------------------------------------------------
    log("=" * 100)
    log("(6) BYTE-RIGIDITY vs FIXED3A, FAMILY-SCOPED (expected-changed set re-derived independently)")
    log("=" * 100)
    rig = family_scoped_rigidity(ref)
    log(f"  rigidity={rig['rigidity']}  passed={rig['passed']}")
    result["byte_rigidity_family_scoped"] = rig

    # ====================================================================================================
    contract_matrix_green = (
        contract_fixed4["R1"]["verdict"] == "PASS"
        and contract_fixed4["R2"]["verdict"] == "PASS"
        and contract_fixed4["R3"]["verdict"] == "PASS"
        and contract_fixed4["overall"] == "PASS"
        and stock_row["overall"] == "PASS"
        and sea_vertex_flag is True
        and convention_invalid_flag is False
        and floors_match
        and r1_unchanged_vs_fixed3a
        and r3_unchanged_vs_fixed3a
        and r1_matches_headline
        and r1_unchanged_falsifier
        and r1_fixed4["verdict"] == "PASS")

    gate_summary = dict(
        gate1a_fixed4_passes=g1_fixed4["passed"],
        gate1a_fixed3a_still_passes=g1_fixed3a["passed"],
        gate1a_specimen_still_fails=(not g1_spec["passed"]),
        gate1a_stock_passes=(g1_pooled["passed"] and all(v["passed"] for v in
                             (G.gate1_uv_validity(b, None, f"stock:{n}") for n, b in groups.items()))),
        gate2_fixed4_passes=g2_fixed4["passed"],
        gate2_fixed3a_still_passes=g2_fixed3a["passed"],
        gate2_stock_passes=(g2_pooled["passed"] and all(v["passed"] for v in
                            (G.gate2_sea_plan_disjoint(b, None, f"stock:{n}") for n, b in groups.items()))),
        gate1c_fixed4_passes=wc_fixed4["passed"],
        gate1c_fixed3a_grass_crosscheck_passes=wc_fixed3a_grass["passed"],
        # FIXED3A diagnostic: predates the re-clothe, so the family-aware predicate must mismatch on
        # EXACTLY dunes:101 + desert:1 (the 102 not-yet-recoloured tris) PLUS the ONE pre-existing
        # per-vertex-lastresort grass sliver FIXED3A has always carried (unrelated to round 4) -- i.e.
        # per_family multi == {dunes:101, desert:1, grass:1}, total 103. Any OTHER count would mean the
        # re-derived family/window field disagrees with the round's own build, not an expected artifact.
        gate1c_fixed3a_family_aware_diag_matches_expected_before_state=(
            wc_fixed3a_family_aware_diag["per_family"].get("dunes", {}).get("multi") == 101
            and wc_fixed3a_family_aware_diag["per_family"].get("desert", {}).get("multi") == 1
            and wc_fixed3a_family_aware_diag["per_family"].get("grass", {}).get("multi") == 1
            and wc_fixed3a_family_aware_diag["per_family"].get("grass", {}).get("single") == 2202),
        family_rect_membership_passes=rect_fixed4["passed"],
        plumbing_fixed4_all_ok=plumb_fixed4["all_ok"],
        plumbing_identical_vs_fixed4=all(identical.values()),
        contract_matrix_green=contract_matrix_green,
        r2_stays_inside_stock_band=r2_in_band,
        byte_rigidity_family_scoped_passes=rig["passed"])
    result["gate_summary"] = gate_summary
    log(f"GATE SUMMARY: {json.dumps(gate_summary, indent=2)}")

    overall = all(gate_summary.values())
    result["overall"] = "PASS" if overall else "FAIL"
    result["meta"] = dict(
        script="uvf_gates4.py", target=str(FIXED4_DIR), base=str(FIXED3A_DIR),
        reused_functions_from="uvf_gates.py (gate1a/gate2/plumbing/contract_rerun/r1_realized, verbatim); "
                              "uvf_fix4.py (stage1/stage2/stage3_cellfield/stage3b, the round's own "
                              "mechanism, re-executed against on-disk bytes -- not the JSON report)",
        new_this_round="family-aware GATE 1c (family_window_coherence_check), family mains-rect "
                       "membership (family_rect_membership_check), R2 diff fixed3a->fixed4, "
                       "family-scoped byte-rigidity (family_scoped_rigidity)",
        contract_gates_version="contract_mass_gates.py v5 (evolved, live)",
        note="zero writes outside out/rung_f/uvf_gates4.json; zero git; specimen/FIXED/FIXED2/FIXED3A/"
             "FIXED4 trees read-only throughout; the stock ecotone calibration read is the same "
             "read-only install access every prior round in this arc has used and documented")

    OUT.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    log("\n" + "=" * 100)
    log(f"OVERALL: {result['overall']}")
    log(f"-> {OUT}")
    return result


if __name__ == "__main__":
    main()
