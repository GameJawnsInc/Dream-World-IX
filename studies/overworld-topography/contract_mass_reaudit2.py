"""FRESH ADVERSARIAL RE-AUDIT ROUND 2 of contract_mass_gates.py v3 (2026-07-24, READ-ONLY).

A NEW adversary. Does NOT assume the v3 fix is sound because the seven prior probes (four v1 + three
round-1 beats) now fail. Builds fresh synthetic candidate views from REAL stock-classified UV triples
(so classify_tri / classify_strip_pair fire exactly as on real bytes -- reusing contract_mass_audit_
probe's build helpers) and runs the v3 gate functions on them to hunt for surviving BLINDNESS, plus a
label-blind disagreement verification and an OVERFIT sweep (lawful-looking organic variants must PASS).

Fresh probes (>= 2 per gate; each labelled BEAT-ATTEMPT / CONFIRM / VERIFY / OVERFIT):
  SUITE/R3:
    P3_R3_TENDRIL_BACKING (BEAT) -- the headline. A grass-WRAPPED thin ecotone skin that RETURNS TO
      GRASS (no local desert interior, the ribbon fallacy) whose "backing" is a compact >=130-cell
      dune blob reachable ONLY through a 1-cell-wide topo-17 tendril. v3 R3 (BEAT #1) gates the
      ecotone-REACHABLE backing -- a thread satisfies 8-conn reachability. R1 measures only the skin
      (grass-wrapped -> far from any coast) and R2 is diluted by the plain blob/tendril, so if the
      whole suite passes, the FAKE_BACKING fix is defeated by a thread (letter of "8-conn connected to
      a >=130 mass" met, INTENT "backs onto a MASS" violated -- R3's disclaimed shape/compactness gap
      now defeats the WHOLE suite, not just R3, because grass-wrapping makes R1 pass where RIBBON_130's
      thin ribbon failed R1).
    P3_R3_TENDRIL_CONTROL (CONFIRM) -- identical but NO tendril (blob disjoint) -> R3 reachable 0 -> FAIL.
    P3_R3_ALLSKIN_NO_INTERIOR (CONFIRM) -- a fat topo-16-ONLY desert lobe (no 17/19/20/41) -> backing 0 -> FAIL.
  R1:
    P3_R1_DOUBLED_LAKE (BEAT) -- a thin desert ring around an INTERNAL ocean hole, grass-wrapped; the
      desert tris bordering the hole are DOUBLED (coincident copies -> 2-owner edges dropped from the
      single-owner silhouette) so the hole's coast VANISHES -> does the body-tri standoff inflate from
      near-hole (~FAIL) to far-outer-perimeter (PASS)? Silhouette robustness to a plausible mint artifact.
    P3_R1_DOUBLED_LAKE_CONTROL (CONFIRM) -- same ring, NOT doubled -> own hole-coast near -> FAIL.
  R2:
    P3_R2_TUNED_PENETRATION (BEAT-ATTEMPT / knife-edge) -- a DEEP_TEETH-style bimodal comb TUNED so the
      deep dressing sits just UNDER the 0.25 penetration ceiling while fringe stays >= 0.60 and floating
      == 0 (deep cells placed diagonally-adjacent to a boundary cell: 4-conn band-2 but cheby<=1 so not
      floating). Characterises whether the 0.25 ceiling is a defensible cut or an overfit knife-edge.
    P3_R2_ALONG_BOUNDARY_PICKET (CONFIRM/doc) -- a 2-cell skin, band-0 dressed as an alternating
      along-boundary picket at <=0.50 sat -> fringe 1.0 / penetration 0 -> PASS is CORRECT (round demoted
      along-boundary run-length to report-only; the disease is depth, not along-boundary structure).
  LABEL-BLIND VERIFY:
    P3_LABELBLIND_XFAM (VERIFY) -- gd-decal UV tagged topo-41(dunes) + dd-decal UV tagged topo-3(grass):
      confirm BOTH land in the body and the fam/topo disagreement is COUNTED + reported, never dropped.
  OVERFIT:
    P3_OVERFIT_5COMP / _13COMP -- stock-like fringe(~0.8)/sat(~0.48) organic variants w/ 5 or 13
      boundary-touching gd components (stock has 9) -> must PASS (fringe/floating not knife-edged).
    P3_OVERFIT_STOCKLIKE_PEN -- a lawful decaying fringe with stock-like penetration ~0.12 and a bit of
      band-1/band-2 decay -> must PASS (penetration ceiling does not reject a stock-shaped fringe).

Output -> out/contract_mass/audit_probes_v2/reaudit2_results.json. ZERO game writes, no deploy.
Run:  py contract_mass_reaudit2.py   (cwd = studies/overworld-topography)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import contract_mass_audit_probe as AP     # noqa: E402  build helpers + real UV triples
import contract_mass_gates as GT           # noqa: E402  the module under RE-audit (v3)
import contract_mass_reaudit as RA         # noqa: E402  build_cellspec / spec_to_tris helpers
import seam_null_recon as SNR              # noqa: E402

OUT = HERE / "out" / "contract_mass" / "audit_probes_v2" / "reaudit2_results.json"
UV_GD2 = AP.UV_GD_ROW2
UV_GD0 = AP.UV_GD_ROW0
UV_DM = AP.UV_DESERT_MAINS
UV_GM = AP.UV_GRASS_MAINS


def summarize_r1(r1):
    return dict(verdict=r1["verdict"], convention=r1["convention"],
                boundary=r1["checks"]["boundary_cell"]["measured_u"],
                straddle=r1["checks"]["straddle_cell"]["measured_u"],
                body=r1["checks"]["body_tri"]["measured_u"],
                standoff_pass=r1["standoff_pass"], convention_invalid=r1["convention_invalid"],
                n_land_perim=r1["diagnostics"].get("n_land_perimeter_segments"))


def summarize_r2(r2):
    a = r2["arrangement"]
    return dict(verdict=r2["verdict"], sat_grass=r2["saturation"]["grass_decal"],
                sat_grass_pass=r2["saturation"]["grass_decal_passes"],
                sat_any=r2["saturation"]["any_decal"], sat_any_pass=r2["saturation"]["any_decal_passes"],
                fringe=a["fringe_concentration"], fringe_pass=a["fringe_passes"],
                penetration=a["penetration_ge2_fraction"], penetration_pass=a["penetration_passes"],
                n_floating=a["n_floating_components"], floating_pass=a["floating_passes"],
                band_hist=a["dressed_band_hist"], n_dressed=a["n_dressed_body_tris"],
                body_total=r2["body"]["label_blind_total"], n_dressed_grass=r2["body"]["n_dressed_grass"],
                topo_disagree=r2["body"]["topo_crosscheck"]["n_topo_not16"],
                fam_disagree=r2["body"]["topo_crosscheck"]["n_fam_not_desert"],
                fam_disagree_hist=r2["body"]["topo_crosscheck"]["fam_disagreement"],
                arrangement_pass=a["arrangement_pass"], primary_pass=r2["primary_pass"])


def summarize_r3(r3):
    return dict(verdict=r3["verdict"], reachable=r3["largest_reachable_backing_cells"],
                whole_region=r3["whole_region_largest_backing_cells"], floor=r3["backing_mass_floor_cells"],
                n_boundary_desert=r3["n_boundary_desert_cells"], topo_tally=r3["backing_topo_tally"])


def run_suite(cand):
    r1 = GT.gate_r1(cand, mode="enforce")
    r2 = GT.gate_r2(cand, mode="enforce")
    r3 = GT.gate_r3(cand, mode="enforce")
    overall = "PASS" if all(r["verdict"] == "PASS" for r in (r1, r2, r3)) else "FAIL"
    return dict(overall=overall, R1=r1, R2=r2, R3=r3)


# ===================================================================================================
# helpers to fill a big grass field then override cells
# ===================================================================================================
def grass_field(spec, cols, rows):
    for col in range(cols[0], cols[1]):
        for row in range(rows[0], rows[1]):
            spec[(col, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]


# ===================================================================================================
# SUITE / R3 -- the tendril-backing headline
# ===================================================================================================
def _tendril_spec(with_tendril):
    """Grass field wrapping everything (>=14-cell margin). A thin topo-16 ecotone skin (cols 30..35,
    rows 20..36) dressed only at its band-0 straddle -> lawful R2 fringe; it RETURNS TO GRASS at col36
    (no local desert interior). A compact 13x9 topo-41 dune blob (cols 50..62, rows 24..32) wrapped in
    grass. If with_tendril: a 1-cell-wide topo-17 desert tendril at row28, cols 36..49, bridging the
    skin to the blob (so R3's 8-conn flood reaches the blob). All desert/dune cells carry UV_DM
    (desert mains) so they land in the label-blind body as PLAIN (diluting saturation)."""
    spec = {}
    grass_field(spec, (16, 78), (6, 50))          # wrap: content cols 29..62 rows 20..36 -> >=14 margin
    for row in range(20, 37):
        spec[(29, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]           # grass W of boundary
        spec[(30, row)] = [(UV_GM, "grass", 16), (UV_GD2, "desert", 16)]       # straddle, band0 dressed
        for col in range(31, 36):
            spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]  # plain topo-16 skin
        spec[(36, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]           # RETURNS TO GRASS
    # compact dune blob (topo-41), grass-wrapped, UV desert-mains
    for col in range(50, 63):
        for row in range(24, 33):
            spec[(col, row)] = [(UV_DM, "dunes", 41), (UV_DM, "dunes", 41)]
    if with_tendril:
        for col in range(36, 50):                 # 1-cell-wide topo-17 tendril at row 28, skin->blob
            spec[(col, 28)] = [(UV_DM, "desert", 17), (UV_DM, "desert", 17)]
    return spec


def p3_r3_tendril_backing():
    spec = _tendril_spec(with_tendril=True)
    cand = RA.build_cellspec("p3_r3_tendril_backing", spec, 3000.0, -3000.0)
    return cand, run_suite(cand)


def p3_r3_tendril_control():
    spec = _tendril_spec(with_tendril=False)
    cand = RA.build_cellspec("p3_r3_tendril_control", spec, 6000.0, -3000.0)
    return cand, run_suite(cand)


def p3_r3_allskin_no_interior():
    """A FAT grass-wrapped topo-16-ONLY desert lobe (a 16x16 = 256-cell topo-16 block, no 17/19/20/41).
    R1 passes (grass-wrapped, thick). R2: mostly plain topo-16 -> low sat, lawful. R3: backing grounds
    are {17,19,20,41} EXCLUDING the topo-16 skin -> reachable backing 0 -> FAIL. Confirms a desert that
    is all 'ecotone skin' and never a plain-desert/dune interior cannot satisfy R3."""
    spec = {}
    grass_field(spec, (0, 60), (0, 60))
    for row in range(22, 38):
        spec[(21, row)] = [(UV_GM, "grass", 16), (UV_GD2, "desert", 16)]       # straddle band0 dressed
        for col in range(22, 38):
            spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]  # ALL topo-16, plain
    cand = RA.build_cellspec("p3_r3_allskin_no_interior", spec, 9000.0, -3000.0)
    return cand, run_suite(cand)


# ===================================================================================================
# R1 -- doubled-lake silhouette robustness
# ===================================================================================================
def _lake_spec(double_ring):
    """Grass-wrapped desert lobe with an INTERNAL ocean hole (empty cells) at cols 30..33 rows 26..29.
    A thin (1-cell) desert ring lines the hole; the desert is 3 cells thick then grass. The desert body
    tri nearest the hole is ~2u from the hole coast -> normally R1 FAIL. If double_ring: every desert
    tri bordering the hole is DOUBLED (coincident) so its hole-facing edges get 2 owners and drop from
    the single-owner silhouette -> the hole coast vanishes -> does the standoff inflate to a PASS?"""
    spec = {}
    grass_field(spec, (0, 64), (0, 64))
    # desert block cols 24..40, rows 20..36, with a 4x4 hole at cols 30..33 rows 26..29 (empty)
    hole_cols, hole_rows = range(30, 34), range(26, 30)
    for hc in hole_cols:                          # actually EMPTY the hole cells (ocean, no tris) --
        for hr in hole_rows:                      # grass_field filled them; delete so the ring has a
            spec.pop((hc, hr), None)              # real single-owner internal coast
    ring = []
    for col in range(24, 41):
        for row in range(20, 37):
            if col in hole_cols and row in hole_rows:
                continue                          # ocean hole = no cell
            # straddle the west boundary at col24
            if col == 24:
                spec[(col, row)] = [(UV_GM, "grass", 16), (UV_GD2, "desert", 16)]
            else:
                spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
            # is this cell adjacent (8-conn) to the hole? if so it lines the hole
            adj_hole = any((col + dx) in hole_cols and (row + dy) in hole_rows
                           for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy))
            if adj_hole:
                ring.append((col, row))
    return spec, ring


def p3_r1_doubled_lake_control():
    spec, ring = _lake_spec(double_ring=False)
    cand = RA.build_cellspec("p3_r1_doubled_lake_control", spec, 12000.0, -3000.0)
    return cand, GT.gate_r1(cand, mode="enforce")


def p3_r1_doubled_lake():
    spec, ring = _lake_spec(double_ring=True)
    x0, z0 = 15000.0, -3000.0
    dup = []
    for (col, row) in ring:                       # coincident duplicate of every hole-lining desert tri
        for w3 in AP.quad_tris(col, row, x0, z0):
            dup.append(AP.make_tri(w3, UV_DM, "desert", 16))
    cand = RA.build_cellspec("p3_r1_doubled_lake", spec, x0, z0, extra_tris=dup)
    return cand, GT.gate_r1(cand, mode="enforce")


# ===================================================================================================
# R2 -- tuned penetration (knife-edge) + along-boundary picket (doc)
# ===================================================================================================
def p3_r2_tuned_penetration():
    """A bimodal comb tuned to sit just under the 0.25 penetration ceiling. Boundary at col0 (grass at
    col -1). band-0 = col0 dressed (many rows). Deep dressed cells are placed at col2 on rows where col1
    is desert but col0/col1 at the SAME row keep it band-2; they are diagonally adjacent to a band-0
    boundary cell (cheby<=1) so NOT floating. Plain desert fills the rest to keep sat <= 0.50. We tune
    the count of deep-dressed rows so penetration ~ 0.20-0.24 while fringe >= 0.60."""
    x0, z0 = 18000.0, -3000.0
    spec = {}
    rows = 40
    # body cols 0..5 (6 deep); grass margin col -1
    for row in range(rows):
        spec[(-1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
        # band0 col0: dressed on ~every row (the fringe)
        spec[(0, row)] = [(UV_GD2, "desert", 16), (UV_GD2, "desert", 16)]
        # band1 col1 plain
        spec[(1, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
        # band2 col2: dressed on a tuned subset (~1 in 3 rows) -> deep dressing, diag-adjacent to col0
        if row % 3 == 0:
            spec[(2, row)] = [(UV_GD2, "desert", 16), (UV_GD2, "desert", 16)]
        else:
            spec[(2, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
        spec[(3, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
        spec[(4, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
        spec[(5, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
    cand = RA.build_cellspec("p3_r2_tuned_penetration", spec, x0, z0)
    return cand, GT.gate_r2(cand, mode="enforce")


def p3_r2_connected_tongues():
    """BEAT-ATTEMPT (the clean knife-edge): band-0 fully dressed (fringe), PLUS connected inland
    'tongues' of dressing reaching band-2 on a tuned subset of rows. Each tongue is ONE 8-conn gd-decal
    component that INCLUDES its band-0 end -> it touches a boundary cell -> NOT floating. Tuned so
    band>=2 dressing is just UNDER the 0.25 ceiling while fringe stays >= 0.60 and sat <= 0.50. If it
    PASSES, characterises the acknowledged n=1 gray zone between a stock-shaped fringe (~0.12) and a
    penetrating comb (~0.33); the round OWNS the 0.25 cut as a deliberate wide-margin judgment."""
    x0, z0 = 37000.0, -3000.0
    spec = {}
    rows = 40
    for row in range(rows):
        spec[(-1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
        spec[(0, row)] = [(UV_GD2, "desert", 16), (UV_GD2, "desert", 16)]      # band0 dressed (fringe)
        # a connected tongue every 5th row: dress col1 (band1) + col2 (band2) so col0-col1-col2 is one
        # connected gd component that reaches the boundary at col0 (non-floating).
        tongue = (row % 5 == 0)
        spec[(1, row)] = ([(UV_GD2, "desert", 16), (UV_GD2, "desert", 16)] if tongue
                          else [(UV_DM, "desert", 16), (UV_DM, "desert", 16)])
        spec[(2, row)] = ([(UV_GD2, "desert", 16), (UV_GD2, "desert", 16)] if tongue
                          else [(UV_DM, "desert", 16), (UV_DM, "desert", 16)])
        spec[(3, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
        spec[(4, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
    cand = RA.build_cellspec("p3_r2_connected_tongues", spec, x0, z0)
    return cand, GT.gate_r2(cand, mode="enforce")


def p3_r2_along_boundary_picket():
    """A 2-cell desert skin; band-0 (col0) dressed on ALTERNATE rows (an along-boundary picket); band-1
    (col1) plain. sat <= 0.50, fringe 1.0 (all dressed at band0), penetration 0, floating 0. PASS is
    CORRECT (round: along-boundary run-length is report-only; the disease is DEPTH, not along-boundary
    structure). Documents that R2 does not gate along-boundary picketing (and the SUITE catches a 2-cell
    skin via R3 = no backing)."""
    x0, z0 = 21000.0, -3000.0
    spec = {}
    for row in range(40):
        spec[(-1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
        uv0 = UV_GD2 if (row % 2 == 0) else UV_DM
        spec[(0, row)] = [(uv0, "desert", 16), (uv0, "desert", 16)]
        spec[(1, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
    cand = RA.build_cellspec("p3_r2_along_boundary_picket", spec, x0, z0)
    return cand, run_suite(cand)


# ===================================================================================================
# LABEL-BLIND VERIFY -- fresh cross-family disagreement (topo-41 gd + topo-3 dd) must be COUNTED
# ===================================================================================================
def p3_labelblind_xfam():
    """A gd-decal UV tagged topo-41 (fam=dunes) and a dd-decal UV tagged topo-3 (fam=grass). Neither is
    the legit opposite-side half (gd-on-grass / dd-on-dunes), so both must land IN the body with the
    fam disagreement COUNTED + reported. Uses realfam=True so fam is derived from topo exactly as the
    real pipeline (fam can never disagree with topo)."""
    x0, z0 = 24000.0, -3000.0
    spec = {}
    for row in range(8):
        spec[(-1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
        spec[(0, row)] = [(UV_GD2, "desert", 16), (UV_GD2, "desert", 16)]      # legit desert body
        spec[(1, row)] = [(UV_GD2, "dunes", 41), (UV_GD2, "dunes", 41)]        # gd-decal UV, topo41
        spec[(2, row)] = [(RA.AP.UV_GD_ROW0, "grass", 3), (RA.AP.UV_GD_ROW0, "grass", 3)]  # placeholder
    # dd-decal on topo-3: need DD strip UVs. Build them from SNR strip constants.
    dd_uv = _dd_row_uv(1)
    for row in range(8):
        spec[(3, row)] = [(dd_uv, "grass", 3), (dd_uv, "grass", 3)]            # dd-decal UV, topo3=grass
    cand = RA.build_cellspec("p3_labelblind_xfam", spec, x0, z0, realfam=True)
    body, xcheck = GT.label_blind_desert_body(cand["core_tris"])
    r2 = GT.gate_r2(cand, mode="enforce")
    return cand, r2, xcheck


def _dd_row_uv(k):
    """Construct a desert|dunes strip UV triple at row k (mirrors AP.UV_GD_ROW* but for the DD strip),
    so classify_strip_pair(uv, DD_DU, DD_DV) == k. Uses SNR's own strip constants."""
    u0 = SNR.STRIP_U0 + SNR.DD_DU
    u1 = SNR.STRIP_U1 + SNR.DD_DU
    v0 = SNR.ROW0_V0 + SNR.DD_DV + k * SNR.ROW_PITCH
    # three corners inside [u0,u1] with min-v == v0 (as classify_strip_pair keys on min v)
    return [(u1, v0 + SNR.ROW_PITCH), (u1, v0), (u0, v0)]


# ===================================================================================================
# OVERFIT -- lawful organic variants must PASS
# ===================================================================================================
def _organic(name, n_comp, x0, extra_band2=0):
    """A stock-like decaying fringe: body 4 deep; band0 mostly dressed split into n_comp runs (all
    boundary-touching -> floating 0); a light band1 decay; optional band2 dressing (extra_band2 rows)
    to exercise a stock-like penetration ~0.12. sat kept < 0.50. Should PASS all R2 gates."""
    spec = {}
    rows = 40
    for row in range(rows):
        spec[(-1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
    gap_rows = set()
    if n_comp > 1:
        step = rows // n_comp
        gap_rows = {min(rows - 1, i * step) for i in range(1, n_comp)}
    for row in range(rows):
        spec[(0, row)] = ([(UV_DM, "desert", 16), (UV_DM, "desert", 16)] if row in gap_rows
                          else [(UV_GD2, "desert", 16), (UV_GD2, "desert", 16)])
        spec[(1, row)] = ([(UV_GD0, "desert", 16), (UV_GD0, "desert", 16)] if row % 4 == 0
                          else [(UV_DM, "desert", 16), (UV_DM, "desert", 16)])
        # band2: dress a few rows if requested (stock-like penetration)
        spec[(2, row)] = ([(UV_GD0, "desert", 16), (UV_GD0, "desert", 16)]
                          if (extra_band2 and row % max(1, rows // extra_band2) == 0 and row not in (0,))
                          else [(UV_DM, "desert", 16), (UV_DM, "desert", 16)])
        spec[(3, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
    cand = RA.build_cellspec(name, spec, x0, -3000.0)
    return cand, GT.gate_r2(cand, mode="enforce")


# ===================================================================================================
def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    uv_ok, uv_checks = AP._verify_uvs()
    print(f"UV calibration: {uv_ok}  {uv_checks}")
    assert uv_ok, "UV builders miscalibrated"
    # verify the DD strip UV builder classifies as intended
    dd1 = SNR.classify_strip_pair(_dd_row_uv(1), SNR.DD_DU, SNR.DD_DV)
    print(f"DD strip UV builder classify -> {dd1} (expect 1)")

    probes = {}
    findings = []

    # ---- SUITE / R3 ----
    c, res = p3_r3_tendril_backing()
    tb_beat = (res["overall"] == "PASS")
    probes["P3_R3_TENDRIL_BACKING"] = dict(kind="BEAT-ATTEMPT", gate="SUITE", expect="FAIL",
        suite_overall=res["overall"], R1=summarize_r1(res["R1"]), R2=summarize_r2(res["R2"]),
        R3=summarize_r3(res["R3"]), suite_beat=tb_beat)
    if tb_beat:
        findings.append(
            "P3_R3_TENDRIL_BACKING BEAT THE SUITE: a grass-wrapped thin topo-16 ecotone skin that RETURNS "
            "TO GRASS (no local desert interior) whose only 'backing' is a compact 130-cell dune blob "
            f"reached through a 1-cell-wide topo-17 tendril passes ALL THREE gates "
            f"(R1={res['R1']['verdict']} body={res['R1']['checks']['body_tri']['measured_u']}u, "
            f"R2={res['R2']['verdict']} sat={res['R2']['saturation']['grass_decal']} "
            f"fringe={res['R2']['arrangement']['fringe_concentration']}, "
            f"R3={res['R3']['verdict']} reachable={res['R3']['largest_reachable_backing_cells']}). "
            "R3 gates 8-conn reachability (BEAT #1 fix), which a thread satisfies; R1 measures only the "
            "grass-wrapped skin; R2 is diluted by the plain blob -- the ribbon fallacy re-opened.")

    c, res = p3_r3_tendril_control()
    probes["P3_R3_TENDRIL_CONTROL"] = dict(kind="CONFIRM", gate="SUITE", expect="FAIL",
        suite_overall=res["overall"], R3=summarize_r3(res["R3"]),
        confirm_ok=(res["overall"] == "FAIL"))

    c, res = p3_r3_allskin_no_interior()
    probes["P3_R3_ALLSKIN_NO_INTERIOR"] = dict(kind="CONFIRM", gate="SUITE", expect="FAIL",
        suite_overall=res["overall"], R1=summarize_r1(res["R1"]), R2=summarize_r2(res["R2"]),
        R3=summarize_r3(res["R3"]), confirm_ok=(res["overall"] == "FAIL"))

    # ---- R1 ----
    c, r = p3_r1_doubled_lake_control()
    dl_ctrl_fail = (r["verdict"] == "FAIL")
    probes["P3_R1_DOUBLED_LAKE_CONTROL"] = dict(kind="CONFIRM", gate="R1", expect="FAIL",
        r1=summarize_r1(r), confirm_ok=dl_ctrl_fail)

    c, r = p3_r1_doubled_lake()
    dl_pass = (r["verdict"] == "PASS")
    probes["P3_R1_DOUBLED_LAKE"] = dict(kind="BEAT-ATTEMPT", gate="R1", expect="FAIL",
        r1=summarize_r1(r), passes_gate=dl_pass, beat=dl_pass,
        note="doubled hole-lining tris drop the internal lake coast from the single-owner silhouette")
    if dl_pass:
        findings.append(
            "P3_R1_DOUBLED_LAKE BEAT R1: doubling the desert tris lining an internal ocean hole drops "
            "the hole's coast from the single-owner silhouette, inflating the body-tri standoff from "
            f"near-hole (control {probes['P3_R1_DOUBLED_LAKE_CONTROL']['r1']['body']}u -> FAIL) to "
            f"{r['checks']['body_tri']['measured_u']}u -> PASS. Silhouette is not robust to coincident "
            "tris (a plausible mint artifact); the internal-seam caveat is documented as a false-FAIL "
            "safe direction, but doubled coincident tris err the UNSAFE direction (false PASS).")

    # ---- R2 ----
    c, r = p3_r2_tuned_penetration()
    tp = summarize_r2(r)
    tp_pass = (r["verdict"] == "PASS")
    probes["P3_R2_TUNED_PENETRATION"] = dict(kind="BEAT-ATTEMPT", gate="R2", expect="FAIL",
        r2=tp, passes_gate=tp_pass, beat=tp_pass,
        note=f"bimodal comb tuned near the 0.25 penetration ceiling: penetration={tp['penetration']} "
             f"fringe={tp['fringe']} sat={tp['sat_grass']} floating={tp['n_floating']}")

    c, r = p3_r2_connected_tongues()
    ct = summarize_r2(r)
    ct_pass = (r["verdict"] == "PASS")
    # NOTE: a PASS here is NOT a hard beat -- it lands in the acknowledged n=1 gray zone (stock ~0.12,
    # comb ~0.33). Recorded as gray_zone_pass + characterised, NOT counted in hard_beats.
    probes["P3_R2_CONNECTED_TONGUES"] = dict(kind="GRAY-ZONE", gate="R2", expect="FAIL-or-gray",
        r2=ct, passes_gate=ct_pass, gray_zone_pass=ct_pass,
        note=f"connected non-floating tongues tuned near the ceiling: penetration={ct['penetration']} "
             f"fringe={ct['fringe']} sat={ct['sat_grass']} floating={ct['n_floating']}. A PASS lands in "
             f"the acknowledged n=1 gray zone (stock ~0.12, comb ~0.33), not a clean intent violation.")

    c, res = p3_r2_along_boundary_picket()
    probes["P3_R2_ALONG_BOUNDARY_PICKET"] = dict(kind="CONFIRM-DOC", gate="R2", expect="R2-PASS/suite-FAIL",
        R2=summarize_r2(res["R2"]), suite_overall=res["overall"],
        note="along-boundary picket at <=0.50 sat: R2 PASS is correct (run-length report-only); suite "
             "catches the 2-cell skin via R3",
        r2_pass=(res["R2"]["verdict"] == "PASS"), suite_fail=(res["overall"] == "FAIL"))

    # ---- LABEL-BLIND VERIFY ----
    c, r2, xcheck = p3_labelblind_xfam()
    lb = summarize_r2(r2)
    lb_counted = (lb["fam_disagree"] > 0)
    probes["P3_LABELBLIND_XFAM"] = dict(kind="VERIFY", gate="R2", expect="disagreements COUNTED",
        r2=lb, xcheck_fam_disagreement=xcheck["fam_disagreement"], xcheck_topo_hist=xcheck["topo_hist"],
        n_fam_not_desert=xcheck["n_fam_not_desert"], n_topo_not16=xcheck["n_topo_not16"],
        excluded_grass_side_gd=xcheck["excluded_grass_side_gd"],
        excluded_dunes_side_dd=xcheck["excluded_dunes_side_dd"],
        disagreements_counted_not_dropped=lb_counted, verdict=lb["verdict"])
    if not lb_counted:
        findings.append("P3_LABELBLIND_XFAM META-LAW VIOLATION: a cross-family UV-dressed tri was NOT "
                        "counted as a disagreement (silently dropped).")

    # ---- OVERFIT ----
    overfit = {}
    for nc, x0 in ((5, 27000.0), (13, 30000.0)):
        c, r = _organic(f"p3_overfit_{nc}comp", nc, x0)
        ov = summarize_r2(r)
        ov_pass = (r["verdict"] == "PASS")
        overfit[f"P3_OVERFIT_{nc}COMP"] = dict(kind="OVERFIT", gate="R2", expect="PASS",
            r2=ov, n_gd_components=r["arrangement"]["n_components"], passes_gate=ov_pass,
            overfit_fail=(not ov_pass))
        if not ov_pass:
            findings.append(f"P3_OVERFIT_{nc}COMP OVERFIT: a lawful organic variant (fringe {ov['fringe']}, "
                            f"sat {ov['sat_grass']}, pen {ov['penetration']}, {r['arrangement']['n_components']} "
                            f"comps) FAILS R2 -- ceiling knife-edged.")
    c, r = _organic("p3_overfit_stocklike_pen", 8, 33000.0, extra_band2=5)
    ov = summarize_r2(r)
    ov_pass = (r["verdict"] == "PASS")
    overfit["P3_OVERFIT_STOCKLIKE_PEN"] = dict(kind="OVERFIT", gate="R2", expect="PASS",
        r2=ov, passes_gate=ov_pass, overfit_fail=(not ov_pass),
        note="a decaying fringe with a stock-like band-2 tail (~0.12 penetration) must PASS")
    if not ov_pass:
        findings.append(f"P3_OVERFIT_STOCKLIKE_PEN OVERFIT: a stock-shaped decaying fringe (fringe "
                        f"{ov['fringe']}, pen {ov['penetration']}, sat {ov['sat_grass']}) FAILS R2 -- "
                        f"the penetration ceiling rejects a stock-like fringe.")
    probes.update(overfit)

    # ---- verdicts ----
    hard_beats = [n for n, p in probes.items() if p.get("beat") or p.get("suite_beat")]
    overfit_fails = [n for n, p in probes.items() if p.get("overfit_fail")]
    confirm_bad = [n for n, p in probes.items()
                   if p.get("kind", "").startswith("CONFIRM") and p.get("confirm_ok") is False]
    labelblind_ok = probes["P3_LABELBLIND_XFAM"]["disagreements_counted_not_dropped"]

    print("\n== RE-AUDIT ROUND-2 MATRIX ==")
    print(f"  {'probe':30s} {'kind':13s} {'gate':6s} {'verdict/overall':16s} BEAT?")
    for n, p in probes.items():
        v = (p.get("suite_overall") or p.get("r2", {}).get("verdict") or p.get("r1", {}).get("verdict")
             or p.get("r3", {}).get("verdict") or p.get("R2", {}).get("verdict") or p.get("verdict"))
        beat = p.get("beat") or p.get("suite_beat") or p.get("overfit_fail")
        print(f"  {n:30s} {p['kind']:13s} {p['gate']:6s} {str(v):16s} {beat}")
    print(f"\nhard BEATS: {hard_beats}")
    print(f"OVERFIT fails: {overfit_fails}")
    print(f"CONFIRM controls behaving wrong: {confirm_bad}")
    print(f"label-blind disagreements counted (not dropped): {labelblind_ok}")
    print("\nFINDINGS:")
    for f in findings:
        print(f"  - {f}")

    out = dict(
        meta=dict(script="contract_mass_reaudit2.py", read_only=True, zero_game_writes=True,
                  note="Fresh adversarial round-2 re-audit of contract_mass_gates.py v3. Synthetic "
                       "candidates from real stock UV triples. No deploy, no game-install writes."),
        uv_calibration=dict(ok=uv_ok, dd_strip_row1=dd1),
        probes=probes,
        hard_beats=hard_beats,
        any_hard_beat=bool(hard_beats),
        overfit_fails=overfit_fails,
        any_overfit_fail=bool(overfit_fails),
        confirm_controls_wrong=confirm_bad,
        labelblind_disagreements_counted=labelblind_ok,
        findings=findings)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}")
    return out


if __name__ == "__main__":
    main()
