"""FRESH ADVERSARIAL RE-AUDIT ROUND 3 of contract_mass_gates.py v4 (2026-07-24, READ-ONLY).

A NEW adversary. Does NOT assume the v4 fix is sound because the nine prior probes now fail. Builds
fresh synthetic candidate views from REAL stock-classified UV triples (so classify_tri /
classify_strip_pair fire exactly as on real bytes -- reusing contract_mass_audit_probe +
contract_mass_reaudit build helpers) and runs the v4 gate functions on them.

Every attack is built with the FAITHFUL builder (realfam=True: fam=FAM_OF[topo], as the real load
pipeline does) UNLESS the attack itself is a topo/UV disagreement that real bytes CAN carry (a
gd-decal UV with a grass topograph id -- the "orphan decal" the study decoded), in which case
realfam is exactly what reproduces it. The plain (free-fam) builder is used ONLY to construct a
straddle tri (grass tri + desert topo in one cell) the way stock straddle cells are built.

Fresh probes (>= 2 per gate; labelled BEAT-ATTEMPT / CONFIRM / OVERFIT / VERIFY):
  R1:
    P4_R1_THIN_LOBE_2CELL (BEAT-ATTEMPT/confirm) -- a 2-cell-thick desert lobe reaching the ocean, grass
      N/S/W. Its OWN coast sits near the ecotone waist -> ALL-COASTS law must drop body-tri standoff
      below 42.968 -> FAIL. Directly exercises critic gap (iv).
    P4_R1_THICK_LOBE_CTRL (CONTROL) -- a FAT desert lobe (own coast far from the waist) -> R1 PASS.
      Proves R1 is not always-FAIL on a staged mint (a real broad two-lobe mass clears it).
  R2:
    P4_R2_VERTICAL_STRIPES (BEAT-ATTEMPT) -- depth-uniform vertical decal stripes at cols 0/2/4 (a
      DIFFERENT mechanical arrangement than v1's checkerboard). fringe ~0.33, penetration ~0.67,
      floating>0 -> FAIL on all three arrangement stats.
    P4_R2_TOPO_RELABEL_HIDE (BEAT-ATTEMPT, the label-blind stressor) -- a depth-uniform SATURATED comb
      that fails R2 on its face, then every DEEP (band>=1) gd-decal tooth is relabelled to a GRASS
      topograph (topo 3 -> fam=grass via realfam). The gate excludes gd-on-grass tris as the "legit
      grass-side"; an adversary abuses that to DELETE inconvenient teeth from BOTH the saturation
      denominator AND the arrangement graph, while the tris still RENDER the gd decal (an orphan-decal
      defect). Does R2 -- and the whole suite -- then pass? The exclusion count is reported, so the
      question is whether the GATE (not just the report) is fooled.
    P4_R2_DILUTE_BIGBODY (CONFIRM) -- a thin organic band-0 fringe on a HUGE plain-desert body: sat
      ~0.1, fringe 1.0. PASS is CORRECT (that IS the stock shape -- a fringe on a big body).
  R3:
    P4_R3_TWO_80 (BEAT-ATTEMPT) -- backing split into TWO 80-cell components, both ecotone-reachable
      across a broad interface. Largest reachable component 80 < 130 -> FAIL. Confirms the floor is on
      one connected MASS, not summed fragments.
    P4_R3_WAIST_3CELL (BEAT-ATTEMPT) -- a real >=130 dune blob bridged to the skin by a 3-cell-wide
      waist (not a 1-cell thread). interface pairs ~3 < 20 -> FAIL. Probes whether a MODERATELY narrow
      neck is caught (and whether the floor of 20 could reject a lawful thin-but-real waist).
    P4_R3_BROAD_WAIST_CTRL (CONTROL) -- the same blob across a >=20-pair broad front -> R3 PASS. Proves
      R3 accepts a genuine broad-waist two-lobe mass (not always-FAIL).
  OVERFIT:
    P4_OVERFIT_7COMP (OVERFIT) -- stock-shaped organic fringe, sat ~0.47, fringe ~0.80, penetration
      ~0.12, 7 boundary-touching gd components (stock 9) -> must PASS.
    P4_OVERFIT_SAWTOOTH (OVERFIT) -- an organic 2-cell-hug sawtooth fringe, sat ~0.40, penetration ~0.0
      -> must PASS (the fringe/penetration cut does not reject a lawful decaying margin).
  LABEL-BLIND VERIFY:
    P4_LABELBLIND_SCRUB (VERIFY) -- a gd-decal UV tagged topo-4 (fam=scrub) and a dd-decal UV tagged
      topo-20 (fam=desert): both must land IN the body (neither is the legit gd-on-grass/dd-on-dunes
      half) with the fam/topo disagreement COUNTED + reported, never silently dropped.

Output -> out/contract_mass/audit_probes_v2/reaudit3_results.json. ZERO game writes, no deploy.
Run:  py contract_mass_reaudit3.py   (cwd = studies/overworld-topography)
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
import contract_mass_gates as GT           # noqa: E402  the module under RE-audit (v4)
import contract_mass_reaudit as RA         # noqa: E402  build_cellspec / realfam helpers
import seam_null_recon as SNR              # noqa: E402

OUT = HERE / "out" / "contract_mass" / "audit_probes_v2" / "reaudit3_results.json"
UV_GD2 = AP.UV_GD_ROW2
UV_GD0 = AP.UV_GD_ROW0
UV_DM = AP.UV_DESERT_MAINS
UV_GM = AP.UV_GRASS_MAINS


def _dd_row_uv(k):
    """Build a desert|dunes strip decal UV at row k from SNR's DD strip constants (mirrors reaudit2)."""
    u0 = SNR.STRIP_U0 + SNR.DD_DU
    u1 = SNR.STRIP_U1 + SNR.DD_DU
    v0 = SNR.ROW0_V0 + SNR.DD_DV + k * SNR.ROW_PITCH
    tri = [(u1, v0 + SNR.ROW_PITCH), (u1, v0), (u0, v0)]
    assert SNR.classify_strip_pair(tri, SNR.DD_DU, SNR.DD_DV) == k, "dd uv did not classify"
    return tri


def grass_field(spec, cols, rows):
    for col in range(cols[0], cols[1]):
        for row in range(rows[0], rows[1]):
            spec[(col, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]


def summarize_r1(r1):
    return dict(verdict=r1["verdict"], convention=r1["convention"],
                boundary=r1["checks"]["boundary_cell"]["measured_u"],
                straddle=r1["checks"]["straddle_cell"]["measured_u"],
                body=r1["checks"]["body_tri"]["measured_u"],
                standoff_pass=r1["standoff_pass"], convention_invalid=r1["convention_invalid"])


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
                excluded_grass_side_gd=r2["body"]["topo_crosscheck"]["excluded_grass_side_gd"],
                arrangement_pass=a["arrangement_pass"], primary_pass=r2["primary_pass"])


def summarize_r3(r3):
    return dict(verdict=r3["verdict"], reachable=r3["largest_reachable_backing_cells"],
                whole_region=r3["whole_region_largest_backing_cells"], floor=r3["backing_mass_floor_cells"],
                interface=r3["skin_backing_interface_pairs"], interface_floor=r3["skin_backing_interface_floor_pairs"],
                erosion=r3["erosion_survive_backing_cells"],
                has_extent=r3["has_extent"], has_interface=r3["has_broad_interface"],
                erosion_survives=r3["erosion_survives"])


def run_suite(cand):
    r1 = GT.gate_r1(cand, mode="enforce")
    r2 = GT.gate_r2(cand, mode="enforce")
    r3 = GT.gate_r3(cand, mode="enforce")
    overall = "PASS" if all(r["verdict"] == "PASS" for r in (r1, r2, r3)) else "FAIL"
    return overall, r1, r2, r3


# ===================================================================================================
# R1
# ===================================================================================================
def p4_r1_thin_lobe_2cell():
    x0, z0 = 30000.0, -3000.0
    spec = {}
    # grass wrap W of col 0, N/S of the corridor
    for col in range(-16, 0):
        for row in range(-10, 20):
            spec[(col, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
    for row in range(-10, 20):
        for col in range(0, 24):
            if 8 <= row <= 9:            # 2-cell-thick desert corridor reaching the EAST tip (col 23)
                if col == 0:
                    spec[(col, row)] = [(UV_GM, "grass", 16), (UV_GD2, "desert", 16)]   # straddle
                else:
                    spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
            else:
                spec[(col, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
    # the desert corridor's own N/S coast is only 1 cell (4u) from its body -> nearest coast is the
    # grass|land silhouette edge at row 7/10 boundary of the corridor... but grass fills there so no
    # ocean. To force the OWN-coast pathology we must expose the corridor's N/S sides to OCEAN, not
    # grass. Rebuild: remove grass adjacent to the corridor tip so the desert tip meets open sea.
    for row in list(range(6, 8)) + list(range(10, 12)):   # ocean band framing the corridor's flanks
        for col in range(18, 26):
            spec.pop((col, row), None)                     # open sea (no tris) beside the desert tip
    # also open sea east of the tip
    for row in range(8, 10):
        for col in range(24, 27):
            spec.pop((col, row), None)
    cand = RA.build_cellspec("p4_r1_thin_lobe_2cell", spec, x0, z0, realfam=True)
    overall, r1, r2, r3 = run_suite(cand)
    return dict(kind="BEAT-ATTEMPT", gate="R1", expect="FAIL", suite_overall=overall,
                R1=summarize_r1(r1), R3=summarize_r3(r3),
                passes_gate=(r1["verdict"] == "PASS"),
                beat=(r1["verdict"] == "PASS"),
                note="2-cell desert lobe with open sea on its flanks -> own coast near the waist "
                     "(ALL-COASTS mass-thickness). R1 must FAIL on body-tri standoff.")


def _straddle(col, row, spec):
    # a proper straddle cell: a grass tri (topo 3, fam grass) + a desert tri (topo 16, fam desert), both
    # realfam-CONSISTENT (FAM_OF[3]=grass, FAM_OF[16]=desert). Mirrors a real stock straddle tile.
    spec[(col, row)] = [(UV_GM, "grass", 3), (UV_GD2, "desert", 16)]


def p4_r1_thick_lobe_ctrl():
    x0, z0 = 33000.0, -3000.0
    spec = {}
    # BIG grass wrap (>=14 cells on every side) so the ecotone waist is >=56u from the outer land-
    # perimeter silhouette. Straddle column at col 16 (16 grass cells to its west).
    grass_field(spec, (0, 60), (0, 56))
    for row in range(14, 42):                        # 28-row desert lobe, well inside the wrap
        _straddle(16, row, spec)
        for col in range(17, 44):                    # fat desert body cols 17..43 (27 cells)
            spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
    cand = RA.build_cellspec("p4_r1_thick_lobe_ctrl", spec, x0, z0)   # plain builder (straddle forms)
    r1 = GT.gate_r1(cand, mode="enforce")
    return dict(kind="CONTROL", gate="R1", expect="PASS(standoff)", R1=summarize_r1(r1),
                standoff_pass=r1["standoff_pass"],
                note="big-grass-wrapped fat lobe with a real straddle column: the ecotone waist is "
                     ">=56u from every coast -> standoff clears the floor (R1 not always-FAIL).")


# ===================================================================================================
# R2
# ===================================================================================================
def p4_r2_vertical_stripes():
    x0, z0 = 36000.0, -3000.0
    spec = {}
    rows = 40
    for row in range(rows):
        spec[(-1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
        for col in range(0, 6):
            dressed = (col % 2 == 0)     # cols 0,2,4 fully dressed (depth-uniform stripes)
            uv = UV_GD2 if dressed else UV_DM
            spec[(col, row)] = [(uv, "desert", 16), (uv, "desert", 16)]
    cand = RA.build_cellspec("p4_r2_vertical_stripes", spec, x0, z0, realfam=True)
    r2 = GT.gate_r2(cand, mode="enforce")
    return dict(kind="BEAT-ATTEMPT", gate="R2", expect="FAIL", r2=summarize_r2(r2),
                passes_gate=(r2["verdict"] == "PASS"), beat=(r2["verdict"] == "PASS"),
                note="depth-uniform vertical stripes cols 0/2/4 -> fringe low, penetration high, "
                     "floating stripes; a distinct mechanical arrangement vs v1 checkerboard.")


def p4_r2_topo_relabel_hide():
    """THE label-blind stressor. A depth-uniform SATURATED comb (fails R2 on saturation + arrangement).
    Then every DEEP (band>=1, i.e. col>=1) gd-decal tooth is relabelled topo-3 (fam=grass). Under
    realfam these render the gd decal but classify fam=grass -> the gate EXCLUDES them as the legit
    grass-side, deleting them from the saturation denominator AND the arrangement graph. Measure whether
    R2 (and the suite) is fooled, and whether the exclusion count betrays the trick."""
    x0, z0 = 39000.0, -3000.0
    spec = {}
    rows = 40
    # baseline SATURATED depth-uniform comb: dress ~2/3 of every band0..4 body cell -> sat > 0.5024
    for row in range(rows):
        spec[(-1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
        for col in range(0, 6):
            dressed = ((col + row) % 3 != 0)        # ~2/3 dressed across all depths
            if col == 0:
                # boundary column: keep dressed teeth as topo-16 desert (they must stay in the body)
                uv = UV_GD2 if dressed else UV_DM
                spec[(col, row)] = [(uv, "desert", 16), (uv, "desert", 16)]
            else:
                if dressed:
                    # DEEP dressed tooth -> relabel to grass topo (the exclusion abuse); still gd UV
                    spec[(col, row)] = [(UV_GD2, "grass", 3), (UV_GD2, "grass", 3)]
                else:
                    spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
    cand = RA.build_cellspec("p4_r2_topo_relabel_hide", spec, x0, z0, realfam=True)
    overall, r1, r2, r3 = run_suite(cand)
    # also measure what saturation WOULD be if the relabelled teeth were counted (the true dressing)
    return dict(kind="BEAT-ATTEMPT", gate="R2", expect="FAIL", suite_overall=overall,
                r2=summarize_r2(r2), R3=summarize_r3(r3), R1=summarize_r1(r1),
                r2_passes=(r2["verdict"] == "PASS"),
                suite_beat=(overall == "PASS"),
                note="deep gd teeth relabelled topo-3(grass); the gate excludes gd-on-grass. The "
                     "reported excluded_grass_side_gd count is the tell (a Rung-F reader sees it spike).")


def p4_r2_dilute_bigbody():
    x0, z0 = 42000.0, -3000.0
    spec = {}
    # thin organic band-0 fringe on a HUGE plain-desert body -> low saturation, lawful shape
    for row in range(40):
        spec[(-1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
        spec[(0, row)] = [(UV_GD2, "desert", 16), (UV_GD2, "desert", 16)]       # band0 fringe
        for col in range(1, 20):
            spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]   # big plain body
    cand = RA.build_cellspec("p4_r2_dilute_bigbody", spec, x0, z0, realfam=True)
    r2 = GT.gate_r2(cand, mode="enforce")
    return dict(kind="CONFIRM", gate="R2", expect="PASS(correct)", r2=summarize_r2(r2),
                r2_pass=(r2["verdict"] == "PASS"),
                note="a fringe on a big plain body IS the stock shape -> R2 PASS is correct; the SUITE "
                     "would still require R1 thickness + R3 backing.")


# ===================================================================================================
# R3
# ===================================================================================================
def _r3_lobe_with_backing(backing_builder, name, x0, z0):
    """A grass-wrapped desert lobe: straddle col at 0, a topo-16 skin cols 0..5 (16 rows), then a
    desert-family backing region shaped by backing_builder(spec). Everything grass-wrapped so R1 is not
    the discriminator (this isolates R3)."""
    spec = {}
    grass_field(spec, (-4, 90), (-4, 60))
    for row in range(20, 36):
        spec[(0, row)] = [(UV_GM, "grass", 16), (UV_GD2, "desert", 16)]        # straddle band0
        for col in range(1, 6):
            spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]  # topo-16 skin
    backing_builder(spec)
    return RA.build_cellspec(name, spec, x0, z0, realfam=True)


def p4_r3_two_80():
    def backing(spec):
        # component A: cols 6..15 rows 20..27 = 10x8 = 80 cells (topo-41 dunes), adjacent to the skin
        for col in range(6, 16):
            for row in range(20, 28):
                spec[(col, row)] = [(UV_DM, "dunes", 41), (UV_DM, "dunes", 41)]
        # component B: cols 6..15 rows 29..36 = 10x8 = 80 cells, SEPARATED from A by row 28 grass gap,
        # but still reachable from the skin (col 5 skin touches col 6 rows 29..35).
        for col in range(6, 16):
            for row in range(29, 37):
                spec[(col, row)] = [(UV_DM, "dunes", 41), (UV_DM, "dunes", 41)]
        # row 28 across cols 6..15 stays grass (the separating gap) -> two 8-conn components
    cand = _r3_lobe_with_backing(backing, "p4_r3_two_80", 45000.0, -3000.0)
    overall, r1, r2, r3 = run_suite(cand)
    return dict(kind="BEAT-ATTEMPT", gate="R3", expect="FAIL", suite_overall=overall,
                R3=summarize_r3(r3), passes_gate=(r3["verdict"] == "PASS"),
                beat=(r3["verdict"] == "PASS"),
                note="backing = two ~80-cell dune components; largest reachable < 130 -> FAIL "
                     "(floor is on one MASS, not summed fragments).")


def p4_r3_waist_3cell():
    def backing(spec):
        # a real 13x11 = 143-cell dune blob far inland (cols 20..32 rows 22..32)
        for col in range(20, 33):
            for row in range(22, 33):
                spec[(col, row)] = [(UV_DM, "dunes", 41), (UV_DM, "dunes", 41)]
        # a 3-cell-wide topo-17 waist bridging skin (col5) to the blob (col20) at rows 26..28
        for col in range(6, 20):
            for row in range(26, 29):
                spec[(col, row)] = [(UV_DM, "desert", 17), (UV_DM, "desert", 17)]
    cand = _r3_lobe_with_backing(backing, "p4_r3_waist_3cell", 48000.0, -3000.0)
    overall, r1, r2, r3 = run_suite(cand)
    return dict(kind="BEAT-ATTEMPT", gate="R3", expect="FAIL", suite_overall=overall,
                R3=summarize_r3(r3), passes_gate=(r3["verdict"] == "PASS"),
                beat=(r3["verdict"] == "PASS"),
                note="143-cell blob reached via a 3-cell waist; interface pairs << 20 -> FAIL "
                     "(anti-thread waist gate catches a moderately narrow neck too).")


def p4_r3_broad_waist_ctrl():
    # widen the skin so its front against backing is >= 24 cells (floor 20). Rebuild a dedicated spec:
    # a taller skin band (rows 16..40 = 24 rows) directly against a fat 143+ dune blob.
    spec = {}
    grass_field(spec, (-4, 90), (-4, 60))
    for row in range(16, 40):                       # 24-row skin front
        spec[(0, row)] = [(UV_GM, "grass", 16), (UV_GD2, "desert", 16)]
        for col in range(1, 6):
            spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
    for col in range(6, 20):                         # fat dune blob directly behind (broad front)
        for row in range(16, 40):
            spec[(col, row)] = [(UV_DM, "dunes", 41), (UV_DM, "dunes", 41)]
    cand = RA.build_cellspec("p4_r3_broad_waist_ctrl", spec, 51000.0, -3000.0, realfam=True)
    r3 = GT.gate_r3(cand, mode="enforce")
    return dict(kind="CONTROL", gate="R3", expect="PASS", R3=summarize_r3(r3),
                r3_pass=(r3["verdict"] == "PASS"),
                note="broad-front backing (24-row interface >= 20) -> R3 PASS: the gate accepts a "
                     "genuine two-lobe mass (not always-FAIL).")


def p4_suite_lawful_ctrl():
    """THE PASSABILITY PROOF. A lawful-looking two-ground landmass that must pass ALL THREE gates:
    fully grass-wrapped (R1 thickness), organic band-0 fringe at sat < 0.50 with fringe >= 0.60 (R2),
    and a fat >=130-cell dune backing directly behind a >=20-cell skin front (R3). If the whole suite
    is UNPASSABLE by any synthetic lawful mass, the contract is vacuous/overfit-to-stock-bytes."""
    spec = {}
    grass_field(spec, (0, 70), (0, 64))
    # straddle column at col 16 (16-cell grass wrap west); skin cols 17..21; fat dune backing cols 22..44;
    # >=14 grass cells N/S/E of the lobe. Rows 16..46 (30-row skin front).
    for row in range(16, 46):
        # band-0 organic fringe: the straddle's desert tri dressed on ~3/4 of rows (fringe high, sat<0.5)
        dressed = (row % 4 != 3)
        desert_uv = UV_GD2 if dressed else UV_DM
        spec[(16, row)] = [(UV_GM, "grass", 3), (desert_uv, "desert", 16)]        # straddle, dressed
        for col in range(17, 22):
            spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]     # plain topo-16 skin
        for col in range(22, 45):
            spec[(col, row)] = [(UV_DM, "dunes", 41), (UV_DM, "dunes", 41)]       # fat dune backing
    cand = RA.build_cellspec("p4_suite_lawful_ctrl", spec, 63000.0, -3000.0)      # plain builder
    overall, r1, r2, r3 = run_suite(cand)
    return dict(kind="CONTROL", gate="SUITE", expect="PASS", suite_overall=overall,
                R1=summarize_r1(r1), r2=summarize_r2(r2), R3=summarize_r3(r3),
                suite_pass=(overall == "PASS"),
                note="a lawful two-ground landmass MUST pass all three gates -> proves the contract is "
                     "satisfiable (not vacuous / not overfit to stock's exact bytes).")


def p4_r2_relabel_smart():
    """THE SMARTER label-blind attack: a lawful two-lobe mass (grass-wrapped, fat >=130 dune backing,
    thick) whose topo-16 skin is SATURATED with gd-decals (>50%), then ~half the skin gd-teeth are
    relabelled to grass topo (topo 3) -- scattered so they neither sever the skin->backing flood nor
    create near coasts. Goal: pass R1 (thick) + R3 (backing intact) while R2 saturation is dodged below
    0.50 by the exclusion. If the SUITE passes, the label-blind exclusion is a SUITE beat (still a
    degenerate orphan-decal build); if R3/R1 catch it, the suite-catch is robust."""
    spec = {}
    grass_field(spec, (0, 70), (0, 64))
    for row in range(16, 46):
        spec[(16, row)] = [(UV_GM, "grass", 3), (UV_GD2, "desert", 16)]           # straddle (counted)
        for col in range(17, 22):
            # skin cols 17..21 SATURATED with gd-decals; relabel ~half (odd col+row) to grass topo
            # (orphan decals) to dodge saturation, keep topo-16 connectivity through the even ones.
            hide = ((col + row) % 2 == 1)
            if hide:
                spec[(col, row)] = [(UV_GD2, "grass", 3), (UV_GD2, "grass", 3)]   # hidden orphan decal
            else:
                spec[(col, row)] = [(UV_GD2, "desert", 16), (UV_GD2, "desert", 16)]  # counted decal
        for col in range(22, 45):
            spec[(col, row)] = [(UV_DM, "dunes", 41), (UV_DM, "dunes", 41)]       # fat dune backing
    cand = RA.build_cellspec("p4_r2_relabel_smart", spec, 66000.0, -3000.0)       # plain builder
    overall, r1, r2, r3 = run_suite(cand)
    return dict(kind="BEAT-ATTEMPT", gate="SUITE", expect="FAIL", suite_overall=overall,
                R1=summarize_r1(r1), r2=summarize_r2(r2), R3=summarize_r3(r3),
                r2_passes=(r2["verdict"] == "PASS"),
                suite_beat=(overall == "PASS"),
                note="saturated skin with ~half gd-teeth relabelled grass topo (orphan decals) to dodge "
                     "R2 saturation, on a lawful thick + backed lobe. Does the suite catch it?")


# ===================================================================================================
# OVERFIT
# ===================================================================================================
def p4_overfit_7comp():
    """Stock-shaped organic fringe: band0 dressed in 7 separated runs (7 boundary-touching components,
    stock has 9), a bit of band-1 decay, sat ~0.47, penetration ~0.12. Must PASS."""
    x0, z0 = 54000.0, -3000.0
    spec = {}
    rows = 48
    for row in range(rows):
        spec[(-1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
        # 7 runs along the boundary: dress band0 except every 7th row (creates ~7 runs / gaps)
        band0_dressed = (row % 7 != 6)
        spec[(0, row)] = [((UV_GD2 if band0_dressed else UV_DM), "desert", 16),
                          ((UV_GD2 if band0_dressed else UV_DM), "desert", 16)]
        # gentle band-1 decay on ~1/4 of rows (connected to band0), tiny band-2 tail on ~1/12
        b1 = (row % 4 == 0) and band0_dressed
        spec[(1, row)] = [((UV_GD2 if b1 else UV_DM), "desert", 16),
                          ((UV_GD2 if b1 else UV_DM), "desert", 16)]
        b2 = (row % 12 == 0) and b1
        spec[(2, row)] = [((UV_GD2 if b2 else UV_DM), "desert", 16),
                          ((UV_GD2 if b2 else UV_DM), "desert", 16)]
        for col in range(3, 8):
            spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
    cand = RA.build_cellspec("p4_overfit_7comp", spec, x0, z0, realfam=True)
    r2 = GT.gate_r2(cand, mode="enforce")
    # count boundary-touching gd components for the record
    return dict(kind="OVERFIT", gate="R2", expect="PASS", r2=summarize_r2(r2),
                n_components=r2["arrangement"]["n_components"],
                n_floating=r2["arrangement"]["n_floating_components"],
                passes_gate=(r2["verdict"] == "PASS"), overfit_fail=(r2["verdict"] != "PASS"),
                note="stock-shaped organic fringe (sat~0.47, fringe~0.8, penetration~0.12, several "
                     "boundary-touching components) MUST pass -- not knife-edged on stock's exact stats.")


def p4_overfit_sawtooth():
    """An organic 2-cell-hug sawtooth: band0 fully dressed, band1 dressed on alternate rows (connected),
    no deeper. sat ~0.40, fringe ~0.67, penetration 0. A lawful decaying margin -> must PASS."""
    x0, z0 = 57000.0, -3000.0
    spec = {}
    for row in range(48):
        spec[(-1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
        spec[(0, row)] = [(UV_GD2, "desert", 16), (UV_GD2, "desert", 16)]
        b1 = (row % 2 == 0)
        spec[(1, row)] = [((UV_GD2 if b1 else UV_DM), "desert", 16),
                          ((UV_GD2 if b1 else UV_DM), "desert", 16)]
        for col in range(2, 6):
            spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
    cand = RA.build_cellspec("p4_overfit_sawtooth", spec, x0, z0, realfam=True)
    r2 = GT.gate_r2(cand, mode="enforce")
    return dict(kind="OVERFIT", gate="R2", expect="PASS", r2=summarize_r2(r2),
                passes_gate=(r2["verdict"] == "PASS"), overfit_fail=(r2["verdict"] != "PASS"),
                note="2-cell-hug decaying margin -> penetration 0, fringe ~0.67 -> must PASS.")


# ===================================================================================================
# LABEL-BLIND VERIFY
# ===================================================================================================
def p4_labelblind_scrub():
    """gd-decal UV tagged topo-4 (fam=scrub) + dd-decal UV tagged topo-20 (fam=desert). Neither is the
    legit opposite-side half (gd-on-grass / dd-on-dunes), so BOTH must land IN the body and the fam
    disagreement be COUNTED + reported. realfam=True (fam derived from topo, as real bytes)."""
    x0, z0 = 60000.0, -3000.0
    spec = {}
    dd_uv = _dd_row_uv(1)
    for row in range(10):
        spec[(-1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
        spec[(0, row)] = [(UV_GD2, "desert", 16), (UV_GD2, "desert", 16)]      # legit desert body
        spec[(1, row)] = [(UV_GD2, "scrub", 4), (UV_GD2, "scrub", 4)]          # gd UV, topo4=scrub
        spec[(2, row)] = [(dd_uv, "desert", 20), (dd_uv, "desert", 20)]        # dd UV, topo20=desert
    cand = RA.build_cellspec("p4_labelblind_scrub", spec, x0, z0, realfam=True)
    r2 = GT.gate_r2(cand, mode="enforce")
    xc = r2["body"]["topo_crosscheck"]
    # confirm the scrub gd tris landed in the body and were counted as a disagreement
    counted_scrub = xc["fam_disagreement"].get("scrub", 0)
    topo_hist = xc.get("topo_hist", {})
    return dict(kind="VERIFY", gate="R2", expect="disagreements COUNTED",
                r2=summarize_r2(r2), topo_crosscheck=xc,
                scrub_counted_in_body=counted_scrub,
                topo_hist=topo_hist,
                disagreements_counted_not_dropped=(counted_scrub == 20 and xc["n_fam_not_desert"] >= 20),
                note="gd-on-scrub (topo4) + dd-on-desert(topo20) must be COUNTED in the body; the "
                     "topo-20 dd tri is a desert-side dd decal (NOT excluded).")


def main():
    ok_uv, uv = AP._verify_uvs()
    results = {}
    results["P4_R1_THIN_LOBE_2CELL"] = p4_r1_thin_lobe_2cell()
    results["P4_R1_THICK_LOBE_CTRL"] = p4_r1_thick_lobe_ctrl()
    results["P4_R2_VERTICAL_STRIPES"] = p4_r2_vertical_stripes()
    results["P4_R2_TOPO_RELABEL_HIDE"] = p4_r2_topo_relabel_hide()
    results["P4_R2_DILUTE_BIGBODY"] = p4_r2_dilute_bigbody()
    results["P4_R3_TWO_80"] = p4_r3_two_80()
    results["P4_R3_WAIST_3CELL"] = p4_r3_waist_3cell()
    results["P4_R3_BROAD_WAIST_CTRL"] = p4_r3_broad_waist_ctrl()
    results["P4_SUITE_LAWFUL_CTRL"] = p4_suite_lawful_ctrl()
    results["P4_R2_RELABEL_SMART"] = p4_r2_relabel_smart()
    results["P4_OVERFIT_7COMP"] = p4_overfit_7comp()
    results["P4_OVERFIT_SAWTOOTH"] = p4_overfit_sawtooth()
    results["P4_LABELBLIND_SCRUB"] = p4_labelblind_scrub()

    hard_beats = []
    plausible_gray = []
    overfit_fails = []
    controls_wrong = []
    for name, r in results.items():
        if r.get("beat") or r.get("suite_beat"):
            hard_beats.append(name)
        if r.get("overfit_fail"):
            overfit_fails.append(name)
        if r["kind"] == "CONTROL":
            exp_pass = "PASS" in r["expect"]
            got = r.get("r3_pass") or r.get("standoff_pass") or r.get("suite_pass")
            if exp_pass and not got:
                controls_wrong.append(name)

    out = dict(
        meta=dict(script="contract_mass_reaudit3.py", read_only=True, zero_game_writes=True,
                  note="Fresh adversarial round-3 re-audit of contract_mass_gates.py v4. New adversary; "
                       "does not assume soundness from the nine prior probes failing. Faithful builder "
                       "(realfam) except where a topo/UV disagreement is itself the real-byte attack."),
        uv_calibration=dict(ok=ok_uv, checks=uv),
        probes=results,
        hard_beats=hard_beats,
        any_hard_beat=bool(hard_beats),
        overfit_fails=overfit_fails,
        any_overfit_fail=bool(overfit_fails),
        controls_wrong=controls_wrong,
        labelblind_disagreements_counted=results["P4_LABELBLIND_SCRUB"]["disagreements_counted_not_dropped"],
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print(f"uv_ok={ok_uv}  hard_beats={hard_beats}  overfit_fails={overfit_fails}  "
          f"controls_wrong={controls_wrong}")
    for name, r in results.items():
        line = f"  {name:28s} kind={r['kind']:12s}"
        if "suite_overall" in r:
            line += f" suite={r['suite_overall']}"
        if "R1" in r and isinstance(r["R1"], dict):
            line += f" R1={r['R1']['verdict']}"
        if "r2" in r:
            line += f" R2={r['r2']['verdict']}"
        if "R3" in r and isinstance(r["R3"], dict):
            line += f" R3={r['R3']['verdict']}"
        print(line)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
