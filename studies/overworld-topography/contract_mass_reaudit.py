"""FRESH ADVERSARIAL RE-AUDIT (round 1) of contract_mass_gates.py v2 (2026-07-24, READ-ONLY).

A NEW adversary. Does NOT assume the v1-audit fix is sound because v1's four probes now fail. Builds
fresh synthetic candidate views (welded-grid landmasses from REAL stock-classified UV triples, so
classify_tri fires for real -- reusing contract_mass_audit_probe's build helpers) and runs the v2
gate functions on them to hunt for surviving BLINDNESS, plus an OVERFIT check (lawful-looking organic
variants must still PASS).

New probes (>= 2 per gate; each labelled BEAT-ATTEMPT or CONFIRM):
  R1: P2_R1_THIN_DESERT   (CONFIRM) thin desert lobe -> its own coast near the waist -> must FAIL (ALL-COASTS)
      P2_R1_THIN_GRASS    (CONFIRM) thin grass lobe -> boundary near grass coast -> must FAIL
      P2_R1_DOUBLED_COAST (BEAT)    thin desert lobe whose outer coast tris are DOUBLED so single-owner
                                    silhouette drops them -> does the standoff inflate to a false PASS?
  R2: P2_R2_XFAM_MISLABEL (BEAT)    a small LAWFUL fam=desert fringe (passes R2) PLUS a big penetrating
                                    gd-DECAL comb tagged topo-49 (fam!=desert) -> invisible to the
                                    fam-gated body. Visible mesh saturated, gate blind? wrong-object test.
      P2_R2_CLUMPED_PAIR  (CONFIRM) period-2 penetrating comb -> fringe low -> must FAIL
      P2_R2_SAWTOOTH      (BEAT)    a long jagged (interdigitated) boundary + penetrating dressing:
                                    does a space-filling boundary inflate band-0 -> fringe passes?
  R3: P2_R3_SPLIT_80_80   (CONFIRM) two 80-cell backing components -> largest 80 < 130 -> must FAIL
      P2_R3_RIBBON_130    (BEAT)    a 1-cell-wide 130-long desert ribbon backing -> 130 cells but a
                                    ribbon not a mass (R3 gates count, shape is Lane-C-out). suite check.
      P2_R3_DISCONNECTED  (BEAT)    ecotone returns to grass (no backing behind IT) + a SEPARATE 130-cell
                                    dunes blob elsewhere in the region -> R3 has no adjacency check?
  OVERFIT:
      P2_OVERFIT_7COMP / _11COMP    stock-like fringe(~0.78)+sat(~0.48) with 7/11 boundary-touching
                                    gd components (stock has 9) -> a lawful variant must still PASS.

Output -> out/contract_mass/audit_probes_v2/reaudit_results.json. ZERO game writes, no deploy.
Run:  py contract_mass_reaudit.py   (cwd = studies/overworld-topography)
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

import contract_mass_audit_probe as AP     # noqa: E402  build helpers + real UV triples
import contract_mass_gates as GT           # noqa: E402  the module under RE-audit
import seam_null_recon as SNR              # noqa: E402

OUT = HERE / "out" / "contract_mass" / "audit_probes_v2" / "reaudit_results.json"
UV_GD2 = AP.UV_GD_ROW2          # strip_grass_desert row2
UV_GD0 = AP.UV_GD_ROW0          # strip_grass_desert row0
UV_DM = AP.UV_DESERT_MAINS      # mains_own desert
UV_GM = AP.UV_GRASS_MAINS       # mains_own grass


# ---------------------------------------------------------------------------------------------------
# builders (mirror AP.build_cand but accept a raw tri list so we can inject duplicates / free geometry)
# ---------------------------------------------------------------------------------------------------
def spec_to_tris(cellspec, x0, z0):
    tris = []
    for (col, row), tspec in cellspec.items():
        qs = AP.quad_tris(col, row, x0, z0)
        for (w3, (uv3, fam, topo)) in zip(qs, tspec):
            tris.append(AP.make_tri(w3, uv3, fam, topo))
    return tris


def spec_to_tris_realfam(cellspec, x0, z0):
    """FAITHFUL builder: fam is DERIVED from topo (fam=FAM_OF[topo]) exactly as the real load pipeline
    (_tris_from_blockmesh) does -- the spec's fam field is IGNORED. Use this whenever a probe must
    reflect real bytes (where fam and topo can never disagree by construction). The straddle-building
    probes that deliberately pair a grass tri with topo-16 need the plain spec_to_tris instead."""
    tris = []
    for (col, row), tspec in cellspec.items():
        qs = AP.quad_tris(col, row, x0, z0)
        for (w3, (_uv_fam, uv3, topo)) in [(w, (t[1], t[0], t[2])) for w, t in zip(qs, tspec)]:
            fam = SNR.FAM_OF.get(topo)
            tris.append(AP.make_tri(w3, uv3, fam, topo))
    return tris


def build_view(name, tris, core_pred, is_staged=True):
    for i, t in enumerate(tris):
        t["gid"] = i
    core_set = {t["block"] for t in tris if core_pred(t["block"])}
    region_blocks = sorted({t["block"] for t in tris})
    by_gid = {t["gid"]: t for t in tris}
    eo = SNR.edge_index(tris)
    boundary_cells = set()
    n_gd = 0
    for e, owners in eo.items():
        fams = {by_gid[g]["fam"] for g in owners}
        if fams == {"grass", "desert"}:
            n_gd += 1
            for g in owners:
                t = by_gid[g]
                if t["block"] in core_set:
                    boundary_cells.add(t["cell"])
    core_tris = [t for t in tris if t["block"] in core_set]
    cell_fams = defaultdict(set)
    for t in core_tris:
        if t["fam"]:
            cell_fams[t["cell"]].add(t["fam"])
    straddle = {c for c, f in cell_fams.items() if f == {"grass", "desert"}}
    body = [t for t in core_tris if t["topo"] == 16]
    return dict(name=name, is_staged=is_staged, mod_dir=AP.DUMMY_MOD,
                core_blocks=[list(b) for b in sorted(core_set)], core_set=core_set,
                region_blocks=region_blocks, tris=tris, core_tris=core_tris, by_gid=by_gid,
                boundary_cells=boundary_cells, straddle_cells=straddle, body_tris=body,
                n_gd_edges=n_gd, cell_fams=cell_fams, block_source={})


def build_cellspec(name, cellspec, x0, z0, core_pred=lambda b: True, extra_tris=None, realfam=False):
    tris = (spec_to_tris_realfam if realfam else spec_to_tris)(cellspec, x0, z0)
    if extra_tris:
        tris.extend(extra_tris)
    return build_view(name, tris, core_pred)


def n_uv_dressed(cand):
    return sum(1 for t in cand["tris"]
               if SNR.classify_tri(t["fam"], t["uv"])[0] in ("strip_grass_desert", "strip_desert_dunes"))


# ===================================================================================================
# R1 PROBES
# ===================================================================================================
def p2_r1_thin_desert():
    """Big grass field; a 3-cell-thick desert corridor reaching the EAST ocean edge (grass N/S/W).
    The desert lobe's OWN coast is near the ecotone waist -> body-tri/boundary standoff must fall below
    the floor -> FAIL. CONFIRM the ALL-COASTS law bites in the synthetic frame."""
    x0, z0 = 2000.0, -2000.0
    spec = {}
    for col in range(-14, 4):            # grass cols -14..3
        for row in range(-8, 18):
            spec[(col, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
    for row in range(7, 10):             # 3-row corridor rows 7..9 reaching east edge (col3 = tip)
        spec[(0, row)] = [(UV_GM, "grass", 16), (UV_GD2, "desert", 16)]   # straddle at col0
        for col in range(1, 4):
            spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
    cand = build_cellspec("p2_r1_thin_desert", spec, x0, z0)
    return cand, GT.gate_r1(cand, mode="enforce")


def p2_r1_thin_grass():
    """Mirror: big desert field; a 3-cell-thick GRASS corridor reaching the WEST ocean edge. The grass
    lobe is thin so the boundary cell sits near the grass coast -> boundary_cell < floor -> FAIL."""
    x0, z0 = 5000.0, -2000.0
    spec = {}
    for col in range(0, 18):             # desert cols 0..17
        for row in range(-8, 18):
            spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
    for row in range(7, 10):             # grass corridor rows 7..9 reaching west edge (col0 = tip)
        spec[(0, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
        spec[(1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
        spec[(2, row)] = [(UV_GM, "grass", 16), (UV_GD2, "desert", 16)]   # straddle at col2
    cand = build_cellspec("p2_r1_thin_grass", spec, x0, z0)
    return cand, GT.gate_r1(cand, mode="enforce")


def p2_r1_doubled_coast():
    """BEAT-ATTEMPT: same thin desert lobe as THIN_DESERT (should FAIL) but the outer desert coast tris
    are DOUBLED (a coincident duplicate tri). single_owner_edges keeps only 1-owner edges, so a doubled
    coast tri's edges get 2 owners and DROP OUT of the silhouette -> the near coast vanishes -> does the
    body-tri standoff inflate above the floor = a FALSE PASS? Tests silhouette robustness to degenerate
    geometry (a plausible mint artifact: overlapping carries emit coincident tris)."""
    x0, z0 = 8000.0, -2000.0
    spec = {}
    for col in range(-14, 4):
        for row in range(-8, 18):
            spec[(col, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
    for row in range(7, 10):
        spec[(0, row)] = [(UV_GM, "grass", 16), (UV_GD2, "desert", 16)]
        for col in range(1, 4):
            spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
    # duplicate every desert-corridor tri (cols 1..3, and the desert tri of col0) => coincident copies
    dup = []
    for row in range(7, 10):
        for (w3, _u) in zip(AP.quad_tris(0, row, x0, z0), [None, None]):
            pass
        # col0 desert tri is the 2nd quad tri; cols1..3 both tris
        q0 = AP.quad_tris(0, row, x0, z0)
        dup.append(AP.make_tri(q0[1], UV_GD2, "desert", 16))
        for col in range(1, 4):
            for w3 in AP.quad_tris(col, row, x0, z0):
                dup.append(AP.make_tri(w3, UV_DM, "desert", 16))
    cand = build_cellspec("p2_r1_doubled_coast", spec, x0, z0, extra_tris=dup)
    return cand, GT.gate_r1(cand, mode="enforce")


# ===================================================================================================
# R2 PROBES
# ===================================================================================================
def p2_r2_xfam_mislabel():
    """BEAT-ATTEMPT (wrong-object, cross-family). Build a small LAWFUL fam=desert fringe that PASSES R2
    on its own: band0 (col0) dressed gd-decal topo-16, band1 (col1) plain desert mains topo-16 ->
    saturation 0.50, fringe 1.0, floating 0. THEN bury a big penetrating gd-DECAL comb behind it in
    cols 2..12, every tri gd-decal UV but tagged topo-49 (FAM_OF[49]=None != 'desert'), so the
    label-blind body's `fam != 'desert'` hard-filter DROPS them. The engine renders the decal by UV
    regardless of topo -> the visible mesh is ~90% ecotone-decalled (a saturated penetrating comb) but
    the gate sees only the tidy 2-cell fringe. If R2 PASSES -> the audit-hole-#2 fix is fam-gated not
    UV-gated, and the UV-vs-topo disagreement is SILENTLY DROPPED (meta-law violation)."""
    x0, z0 = 11000.0, -2000.0
    spec = {}
    for row in range(10):
        spec[(-1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]         # grass margin (fam grass)
        spec[(0, row)] = [(UV_GD2, "desert", 16), (UV_GD2, "desert", 16)]    # band0 dressed, topo16->desert
        spec[(1, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]      # band1 plain, topo16->desert
        for col in range(2, 13):                                             # HIDDEN saturated comb
            spec[(col, row)] = [(UV_GD2, "x", 49), (UV_GD2, "x", 49)]        # gd-decal UV, topo49->FAM None
    # realfam=True => fam is derived from topo EXACTLY as the real pipeline: the topo-49 cells get
    # fam=FAM_OF[49]=None (NOT 'desert'), so the label-blind body's `fam!='desert'` hard-filter drops
    # them -- faithfully reproducing what real mis-tagged bytes would do (fam can never disagree with topo).
    cand = build_cellspec("p2_r2_xfam_mislabel", spec, x0, z0, realfam=True)
    r2 = GT.gate_r2(cand, mode="enforce")
    return cand, r2


def p2_r2_clumped_pair():
    """CONFIRM: a period-2 (clumped-pair) penetrating comb. Dress cols 0,1 then plain 2,3 then dress
    4,5 ... all topo-16 fam desert, penetrating inland from the boundary. saturation ~0.50 but dressing
    spread across bands -> fringe below floor -> must FAIL. (v1 used period-1; this checks period-2.)"""
    x0, z0 = 14000.0, -2000.0
    spec = {}
    for row in range(10):
        spec[(-1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
        for col in range(12):
            dressed = (col // 2) % 2 == 0        # cols 0,1 dressed; 2,3 plain; 4,5 dressed; ...
            uv = UV_GD2 if dressed else UV_DM
            spec[(col, row)] = [(uv, "desert", 16), (uv, "desert", 16)]
    cand = build_cellspec("p2_r2_clumped_pair", spec, x0, z0)
    return cand, GT.gate_r2(cand, mode="enforce")


def p2_r2_sawtooth():
    """CONFIRM (lawful): an interdigitated (gear-tooth) boundary with dressing that hugs the boundary
    only 2 cells deep. This is a legitimate decaying fringe (low saturation, boundary-concentrated) on
    a jagged boundary, so R2 SHOULD pass it -- it is NOT the disease (deep-penetrating saturated
    dressing). Included to show the gate does not spuriously FAIL a jagged-but-lawful fringe. (my
    original 'beat' label was wrong: 2-cell-deep dressing is a fringe, not a comb.)"""
    x0, z0 = 17000.0, -2000.0
    spec = {}
    for row in range(12):
        reach = 3 if (row % 2 == 0) else 0
        for col in range(-2, reach):
            spec[(col, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
        for col in range(reach, 10):
            near = col < reach + 2
            uv = UV_GD2 if near else UV_DM
            spec[(col, row)] = [(uv, "desert", 16), (uv, "desert", 16)]
    cand = build_cellspec("p2_r2_sawtooth", spec, x0, z0)
    return cand, GT.gate_r2(cand, mode="enforce")


def p2_r2_deep_teeth():
    """BEAT-ATTEMPT (fringe-inflation, the real one): DEEP grass teeth interdigitate the desert so that
    even inland desert cells are BFS band-0 (touching a tooth). Then dress a CHECKERBOARD of those deep
    cells: saturation ~0.50 (passes) but the dressing PENETRATES far from the outer waist -- the eye's
    'saturated comb'. If the space-filling boundary keeps fringe >= 0.60 (all dressed cells count as
    band-0 because a tooth is always adjacent) AND floating stays 0, R2 PASSES a penetrating comb.
    This is the structural weakness of a depth-from-boundary metric: a builder inflates band-0 by
    making the boundary space-filling."""
    x0, z0 = 40000.0, -2000.0
    spec = {}
    # grass teeth: on even rows grass reaches deep to col 9 (a comb of teeth every other row).
    # desert occupies cols 0..9 on ODD rows, and cols 10..11 on all rows (a desert field behind).
    for row in range(20):
        if row % 2 == 0:
            for col in range(-2, 10):            # deep grass tooth
                spec[(col, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
            for col in range(10, 14):            # desert behind the tooth tip
                dressed = (col % 2 == 0)
                uv = UV_GD2 if dressed else UV_DM
                spec[(col, row)] = [(uv, "desert", 16), (uv, "desert", 16)]
        else:
            for col in range(-2, 0):
                spec[(col, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
            for col in range(0, 14):             # desert between teeth: checkerboard dressing
                dressed = ((col + row) % 2 == 0)
                uv = UV_GD2 if dressed else UV_DM
                spec[(col, row)] = [(uv, "desert", 16), (uv, "desert", 16)]
    cand = build_cellspec("p2_r2_deep_teeth", spec, x0, z0)
    return cand, GT.gate_r2(cand, mode="enforce")


# ===================================================================================================
# R3 PROBES
# ===================================================================================================
def _grass_desert_grass_ribbon(spec, rows, x0, z0):
    """helper: a thin returns-to-grass desert ribbon (grass W, 2-col desert, grass E)."""
    for row in rows:
        spec[(-1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
        spec[(0, row)] = [(UV_GD2, "desert", 16), (UV_GD2, "desert", 16)]
        spec[(1, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
        spec[(2, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]


def p2_r3_split_80_80():
    """CONFIRM: two disjoint 80-cell topo-17 desert backing blobs. Largest 8-conn component = 80 < 130
    -> must FAIL. Tests that R3's connectivity requirement can't be met by two half-size masses."""
    x0, z0 = 20000.0, -2000.0
    spec = {}
    _grass_desert_grass_ribbon(spec, range(10), x0, z0)
    # blob A: cols 10..17 x rows 0..9 = 8x10 = 80 topo-17 cells
    for col in range(10, 18):
        for row in range(10):
            spec[(col, row)] = [(UV_DM, "desert", 17), (UV_DM, "desert", 17)]
    # blob B: cols 30..37 x rows 0..9 = 80 topo-17 cells (a gap at cols 18..29 = no cells)
    for col in range(30, 38):
        for row in range(10):
            spec[(col, row)] = [(UV_DM, "desert", 17), (UV_DM, "desert", 17)]
    cand = build_cellspec("p2_r3_split_80_80", spec, x0, z0)
    return cand, GT.gate_r3(cand, mode="enforce")


def p2_r3_ribbon_130():
    """BEAT-ATTEMPT (shape): a 1-cell-WIDE, 130-cell-LONG topo-17 desert ribbon as 'backing'. 130
    connected cells -> R3 PASSES (it gates count; shape is Lane-C report-only). But a 1-wide ribbon is
    the RIBBON FALLACY, not a mass. Run the full suite to show R1 catches it (a 1-wide ribbon's own
    coast is ~2u away)."""
    x0, z0 = 24000.0, -2000.0
    spec = {}
    _grass_desert_grass_ribbon(spec, range(10), x0, z0)
    # a 1-wide backing ribbon snaking: place 130 topo-17 cells in a single 8-conn chain behind col1.
    # simplest 1-wide chain: col 3, rows 0..129 (1 cell wide, 130 long).
    for row in range(130):
        spec[(3, row)] = [(UV_DM, "desert", 17), (UV_DM, "desert", 17)]
    cand = build_cellspec("p2_r3_ribbon_130", spec, x0, z0)
    r1 = GT.gate_r1(cand, mode="enforce")
    r2 = GT.gate_r2(cand, mode="enforce")
    r3 = GT.gate_r3(cand, mode="enforce")
    overall = "PASS" if all(r["verdict"] == "PASS" for r in (r1, r2, r3)) else "FAIL"
    return cand, dict(overall=overall, R1=r1, R2=r2, R3=r3)


def p2_suite_fake_backing():
    """BEAT-ATTEMPT (suite, R3 adjacency): the harder version of DISCONNECTED. A big grass field FULLY
    surrounds a topo-16 desert patch (so the desert stands off far from every coast -> R1 passes) that
    has a lawful boundary fringe (R2 passes) but NO desert backing behind it (returns to grass on its
    far side, like Rung E's skin) -- PLUS a disjoint 130-cell topo-41 dunes blob elsewhere. If R3's
    presence-only test lets the dunes blob satisfy 'backing' while the ecotone does NOT back onto it,
    and R1/R2 pass the fat grass-wrapped patch, the WHOLE SUITE is beaten by a fake-backing build."""
    x0, z0 = 44000.0, -2000.0
    spec = {}
    for col in range(-24, 40):            # huge grass field wraps everything (coast far away)
        for row in range(-24, 40):
            spec[(col, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]
    # inland desert patch cols 10..15, rows 10..25 (wrapped by grass on all sides -> deep standoff).
    # west boundary at col10 (grass col9 vs desert col10); a lawful decaying fringe; NO dune backing.
    for row in range(10, 26):
        spec[(9, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]           # grass W of boundary
        # band0 STRADDLE cell: one grass tri + one desert dressed tri in the same cell (so R1's
        # straddle measure is defined). This is the only change from the FAIL-on-missing-straddle run.
        spec[(10, row)] = [(UV_GM, "grass", 16), (UV_GD2, "desert", 16)]      # straddle, band0 dressed
        for col in range(11, 16):
            spec[(col, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)] # plain topo-16 body
        spec[(16, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]          # grass E (returns to grass)
    # disjoint 13x10 = 130-cell dunes blob far east (cols 50..62), NOT adjacent to the ecotone
    for col in range(50, 63):
        for row in range(0, 10):
            spec[(col, row)] = [(UV_DM, "dunes", 41), (UV_DM, "dunes", 41)]
    cand = build_cellspec("p2_suite_fake_backing", spec, x0, z0)
    r1 = GT.gate_r1(cand, mode="enforce")
    r2 = GT.gate_r2(cand, mode="enforce")
    r3 = GT.gate_r3(cand, mode="enforce")
    overall = "PASS" if all(r["verdict"] == "PASS" for r in (r1, r2, r3)) else "FAIL"
    return cand, dict(overall=overall, R1=r1, R2=r2, R3=r3)


def p2_r3_disconnected():
    """BEAT-ATTEMPT (adjacency): the ecotone returns to grass (no desert mass behind IT, like Rung E)
    PLUS a SEPARATE 130-cell topo-41 dunes blob dropped elsewhere in the region, NOT touching the
    ecotone. R3's verdict uses only the largest backing component over the whole region -- no adjacency
    to the ecotone is checked -- so it PASSES though the topo-16 skin does NOT back onto the mass. Run
    the suite to see if R1/R2 catch the overall build."""
    x0, z0 = 28000.0, -2000.0
    spec = {}
    _grass_desert_grass_ribbon(spec, range(10), x0, z0)
    # a separate 13x10 = 130-cell dunes blob far to the east (cols 40..52), disjoint from the ecotone
    for col in range(40, 53):
        for row in range(10):
            spec[(col, row)] = [(UV_DM, "dunes", 41), (UV_DM, "dunes", 41)]
    cand = build_cellspec("p2_r3_disconnected", spec, x0, z0)
    r1 = GT.gate_r1(cand, mode="enforce")
    r2 = GT.gate_r2(cand, mode="enforce")
    r3 = GT.gate_r3(cand, mode="enforce")
    overall = "PASS" if all(r["verdict"] == "PASS" for r in (r1, r2, r3)) else "FAIL"
    return cand, dict(overall=overall, R1=r1, R2=r2, R3=r3, r3_verdict=r3["verdict"])


# ===================================================================================================
# OVERFIT CHECK -- lawful-looking organic variants must still PASS R2 (fringe/floating not knife-edged)
# ===================================================================================================
def _organic_variant(name, n_comp, x0, z0):
    """A stock-like fringe: a body 4 cells deep; the boundary band0 is mostly dressed (fringe ~0.8),
    dressing decays inland; split the band0 dressing into `n_comp` runs separated by a single plain
    cell so there are n_comp gd-decal components (all boundary-touching -> floating 0). saturation kept
    below 0.50 by the plain inland bands. Should PASS every R2 gate."""
    spec = {}
    rows = 40
    for row in range(rows):
        spec[(-1, row)] = [(UV_GM, "grass", 3), (UV_GM, "grass", 3)]        # grass margin
    # body cols 0..3 (4 deep). band0=col0 dressed except gaps that split it into n_comp runs.
    gap_rows = set()
    if n_comp > 1:
        step = rows // n_comp
        gap_rows = {min(rows - 1, i * step) for i in range(1, n_comp)}
    for row in range(rows):
        # col0 band0: dressed unless a splitter gap row -> plain (creates a component break)
        if row in gap_rows:
            spec[(0, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]
        else:
            spec[(0, row)] = [(UV_GD2, "desert", 16), (UV_GD2, "desert", 16)]
        # col1 band1: a light decay (dress ~1 in 4), else plain
        spec[(1, row)] = ([(UV_GD0, "desert", 16), (UV_GD0, "desert", 16)] if row % 4 == 0
                          else [(UV_DM, "desert", 16), (UV_DM, "desert", 16)])
        spec[(2, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]     # band2 plain
        spec[(3, row)] = [(UV_DM, "desert", 16), (UV_DM, "desert", 16)]     # band3 plain
    cand = build_cellspec(name, spec, x0, z0)
    return cand, GT.gate_r2(cand, mode="enforce")


# ===================================================================================================
def summarize_r2(r2):
    return dict(verdict=r2["verdict"],
               sat_grass=r2["saturation"]["grass_decal"], sat_grass_pass=r2["saturation"]["grass_decal_passes"],
               sat_any=r2["saturation"]["any_decal"], sat_any_pass=r2["saturation"]["any_decal_passes"],
               fringe=r2["arrangement"]["fringe_concentration"], fringe_pass=r2["arrangement"]["fringe_passes"],
               n_floating=r2["arrangement"]["n_floating_components"], floating_pass=r2["arrangement"]["floating_passes"],
               n_dressed_body_tris=r2["arrangement"]["n_dressed_body_tris"],
               label_blind_total=r2["body"]["label_blind_total"],
               n_dressed_grass=r2["body"]["n_dressed_grass"],
               topo_disagreement_non16=r2["body"]["topo_crosscheck"]["n_topo_not16"],
               primary_pass=r2["primary_pass"])


def summarize_r1(r1):
    return dict(verdict=r1["verdict"], convention=r1["convention"],
               boundary=r1["checks"]["boundary_cell"]["measured_u"],
               straddle=r1["checks"]["straddle_cell"]["measured_u"],
               body=r1["checks"]["body_tri"]["measured_u"],
               floors=r1["floors"], standoff_pass=r1["standoff_pass"],
               convention_invalid=r1["convention_invalid"])


def summarize_r3(r3):
    return dict(verdict=r3["verdict"], largest_backing=r3["largest_backing_component_cells"],
               floor=r3["backing_mass_floor_cells"], sizes=r3["backing_component_sizes"],
               n_backing_cells=r3["n_backing_ground_cells"], topo_tally=r3["backing_topo_tally"])


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    uv_ok, uv_checks = AP._verify_uvs()
    print(f"UV calibration: {uv_ok}  {uv_checks}")
    assert uv_ok, "UV builders miscalibrated"

    findings = []
    probes = {}

    # ---- R1 ----
    c, r = p2_r1_thin_desert()
    probes["P2_R1_THIN_DESERT"] = dict(kind="CONFIRM", gate="R1", expect="FAIL",
        r1=summarize_r1(r), passes_gate=(r["verdict"] == "PASS"),
        beat=(r["verdict"] == "PASS"))

    c, r = p2_r1_thin_grass()
    probes["P2_R1_THIN_GRASS"] = dict(kind="CONFIRM", gate="R1", expect="FAIL",
        r1=summarize_r1(r), passes_gate=(r["verdict"] == "PASS"),
        beat=(r["verdict"] == "PASS"))

    c, r = p2_r1_doubled_coast()
    ndup_pass = (r["verdict"] == "PASS")
    probes["P2_R1_DOUBLED_COAST"] = dict(kind="BEAT-ATTEMPT", gate="R1", expect="FAIL",
        r1=summarize_r1(r), n_land_perim_segs=r["diagnostics"].get("n_land_perimeter_segments"),
        passes_gate=ndup_pass, beat=ndup_pass,
        note="doubled coast tris -> 2-owner edges dropped from silhouette; PASS would be a false-standoff beat")
    if ndup_pass:
        findings.append("P2_R1_DOUBLED_COAST BEAT R1: doubling the outer desert-coast tris drops them "
                        "from the single-owner silhouette, inflating the body-tri standoff to a FALSE PASS "
                        f"(body={r['checks']['body_tri']['measured_u']}u >= 42.968).")

    # ---- R2 ----
    c, r = p2_r2_xfam_mislabel()
    xf = summarize_r2(r)
    xf_uv = n_uv_dressed(c)
    xf_pass = (r["verdict"] == "PASS")
    probes["P2_R2_XFAM_MISLABEL"] = dict(kind="BEAT-ATTEMPT", gate="R2", expect="FAIL",
        r2=xf, n_uv_dressed_tris_in_mesh=xf_uv, counted_dressed=xf["n_dressed_grass"],
        counted_body_total=xf["label_blind_total"], topo_disagreement_reported=xf["topo_disagreement_non16"],
        passes_gate=xf_pass, beat=xf_pass,
        note="gd-decal UV on topo-49 (fam None) is hard-filtered out of the fam==desert body and NOT "
             "reported as a UV/topo disagreement; visible mesh saturated, gate blind.")
    if xf_pass:
        findings.append(
            f"P2_R2_XFAM_MISLABEL BEAT R2 (WRONG-OBJECT, cross-family): {xf_uv} UV-dressed tris in the "
            f"mesh but R2 counts a {xf['label_blind_total']}-tri body with {xf['n_dressed_grass']} dressed "
            f"(sat {xf['sat_grass']}) -> PASS. The audit-hole-#2 fix is fam-gated (fam!=desert dropped), "
            f"not UV-gated; the {xf_uv - xf['n_dressed_grass']} dressed-but-non-desert-family tris are "
            f"SILENTLY DROPPED (topo cross-check reports {xf['topo_disagreement_non16']} disagreements, "
            f"missing them entirely) -- a direct label-blind meta-law violation.")

    c, r = p2_r2_clumped_pair()
    cp = summarize_r2(r)
    probes["P2_R2_CLUMPED_PAIR"] = dict(kind="CONFIRM", gate="R2", expect="FAIL",
        r2=cp, passes_gate=(r["verdict"] == "PASS"), beat=(r["verdict"] == "PASS"))

    c, r = p2_r2_sawtooth()
    sw = summarize_r2(r)
    probes["P2_R2_SAWTOOTH"] = dict(kind="CONFIRM", gate="R2", expect="PASS",
        r2=sw, passes_gate=(r["verdict"] == "PASS"),
        note="2-cell-deep boundary-hug on a jagged boundary = lawful fringe (sat low, fringe high); PASS is correct")

    c, r = p2_r2_deep_teeth()
    dt = summarize_r2(r)
    dt_pass = (r["verdict"] == "PASS")
    probes["P2_R2_DEEP_TEETH"] = dict(kind="BEAT-ATTEMPT", gate="R2", expect="FAIL",
        r2=dt, passes_gate=dt_pass, beat=dt_pass,
        note="deep grass teeth make inland cells band-0; checkerboard dressing at sat~0.5 penetrates. "
             "PASS => the depth-from-boundary fringe metric is inflatable by a space-filling boundary")
    if dt_pass:
        findings.append(
            f"P2_R2_DEEP_TEETH BEAT R2: deep interdigitated teeth inflate band-0 so a checkerboard "
            f"penetrating comb reads fringe={dt['fringe']} (>=0.60), sat {dt['sat_grass']} (<=0.5024), "
            f"floating {dt['n_floating']} -> PASS despite a saturated penetrating arrangement.")

    # ---- R3 ----
    c, r = p2_r3_split_80_80()
    sp = summarize_r3(r)
    probes["P2_R3_SPLIT_80_80"] = dict(kind="CONFIRM", gate="R3", expect="FAIL",
        r3=sp, passes_gate=(r["verdict"] == "PASS"), beat=(r["verdict"] == "PASS"))

    c, res = p2_r3_ribbon_130()
    rb_r3_pass = (res["R3"]["verdict"] == "PASS")
    probes["P2_R3_RIBBON_130"] = dict(kind="BEAT-ATTEMPT", gate="R3", expect="R3-FAIL-or-suite-FAIL",
        r3=summarize_r3(res["R3"]), r1=summarize_r1(res["R1"]), suite_overall=res["overall"],
        r3_passes_gate=rb_r3_pass, suite_beat=(res["overall"] == "PASS"),
        note="1-wide 130-long ribbon: R3 counts 130 cells -> R3 PASS; shape is Lane-C-out; suite should catch via R1")
    if res["overall"] == "PASS":
        findings.append("P2_R3_RIBBON_130 BEAT THE SUITE: a 1-wide 130-long desert ribbon passes ALL THREE gates.")
    elif rb_r3_pass:
        findings.append("P2_R3_RIBBON_130 R3-only blindness (non-blocking): R3 accepts a 1-cell-wide 130-long "
                        "ribbon as 'backing mass' (count only, no shape); the SUITE catches it via "
                        f"R1={res['R1']['verdict']} (thin-ribbon own-coast). Documented gap: R3 gates extent, not mass shape.")

    c, res = p2_r3_disconnected()
    dc_r3_pass = (res["R3"]["verdict"] == "PASS")
    probes["P2_R3_DISCONNECTED"] = dict(kind="BEAT-ATTEMPT", gate="R3", expect="R3-FAIL-or-suite-FAIL",
        r3=summarize_r3(res["R3"]), r1=summarize_r1(res["R1"]), r2_verdict=res["R2"]["verdict"],
        suite_overall=res["overall"], r3_passes_gate=dc_r3_pass, suite_beat=(res["overall"] == "PASS"),
        note="ecotone returns to grass + a SEPARATE 130-cell dunes blob; R3 has no ecotone-adjacency check")
    if res["overall"] == "PASS":
        findings.append("P2_R3_DISCONNECTED BEAT THE SUITE: a returns-to-grass ecotone + a disjoint 130-cell "
                        "dunes blob passes all three gates.")
    elif dc_r3_pass:
        findings.append("P2_R3_DISCONNECTED R3-only blindness (non-blocking): R3 PASSES on a 130-cell dunes blob "
                        "that does NOT back the ecotone (no adjacency check -- the docstring says 'back onto' but "
                        f"the code counts any region mass); the SUITE catches via R1={res['R1']['verdict']}/"
                        f"R2={res['R2']['verdict']}. Documented gap: R3 = presence, not adjacency.")

    c, res = p2_suite_fake_backing()
    fb_pass = (res["overall"] == "PASS")
    probes["P2_SUITE_FAKE_BACKING"] = dict(kind="BEAT-ATTEMPT", gate="SUITE", expect="FAIL",
        r1=summarize_r1(res["R1"]), r2=summarize_r2(res["R2"]), r3=summarize_r3(res["R3"]),
        suite_overall=res["overall"], suite_beat=fb_pass,
        note="grass-wrapped topo-16 patch (no dune backing) + disjoint 130 dunes blob; tests whether "
             "R3's presence-only backing lets a fake-backing build pass the whole suite")
    if fb_pass:
        findings.append(
            "P2_SUITE_FAKE_BACKING BEAT THE SUITE: a grass-wrapped topo-16 ecotone patch with NO dune "
            "backing behind it, plus a DISJOINT 130-cell dunes blob elsewhere, passes ALL THREE gates -- "
            "R3 checks backing PRESENCE in the region, not adjacency to the ecotone skin (the docstring "
            "says 'back onto' but the code counts any region mass).")

    # ---- OVERFIT ----
    for nc, x0 in ((7, 31000.0), (11, 34000.0)):
        c, r = _organic_variant(f"p2_overfit_{nc}comp", nc, x0, -2000.0)
        ov = summarize_r2(r)
        ov_pass = (r["verdict"] == "PASS")
        probes[f"P2_OVERFIT_{nc}COMP"] = dict(kind="OVERFIT", gate="R2", expect="PASS",
            r2=ov, n_gd_components=r["arrangement"]["n_components"],
            passes_gate=ov_pass, overfit_fail=(not ov_pass))
        if not ov_pass:
            findings.append(f"P2_OVERFIT_{nc}COMP OVERFIT: a lawful-looking organic variant (fringe {ov['fringe']}, "
                            f"sat {ov['sat_grass']}, {r['arrangement']['n_components']} components) FAILS R2 -- "
                            f"the arrangement ceiling is knife-edged.")

    # ---- verdicts ----
    any_beat = any(p.get("beat") or p.get("suite_beat") for p in probes.values())
    any_overfit = any(p.get("overfit_fail") for p in probes.values())
    confirms_ok = all((p["kind"] != "CONFIRM") or (p.get("expect") != "FAIL") or (not p.get("passes_gate"))
                      for p in probes.values())
    r3_only_blind = [n for n, p in probes.items()
                     if p.get("r3_passes_gate") and not p.get("suite_beat")]

    print("\n== RE-AUDIT MATRIX ==")
    print(f"  {'probe':24s} {'kind':13s} {'gate':5s} {'verdict/overall':16s} {'BEAT?'}")
    for n, p in probes.items():
        v = (p.get("r2", {}).get("verdict") or p.get("r1", {}).get("verdict")
             or p.get("r3", {}).get("verdict") or p.get("suite_overall"))
        beat = p.get("beat") or p.get("suite_beat") or p.get("overfit_fail")
        print(f"  {n:24s} {p['kind']:13s} {p['gate']:5s} {str(v):16s} {beat}")
    print(f"\nany hard BEAT (suite or gate-with-intent): {any_beat}")
    print(f"any OVERFIT fail: {any_overfit}")
    print(f"R3-only (per-gate) blindness, suite-caught: {r3_only_blind}")
    print("\nFINDINGS:")
    for f in findings:
        print(f"  - {f}")

    out = dict(
        meta=dict(script="contract_mass_reaudit.py", read_only=True, zero_game_writes=True,
                  note="Fresh adversarial re-audit of contract_mass_gates.py v2. Synthetic candidates "
                       "from real stock UV triples. No deploy, no game-install writes."),
        uv_calibration=dict(ok=uv_ok, checks={k: list(v) for k, v in uv_checks.items()}),
        probes=probes,
        any_hard_beat=any_beat,
        any_overfit_fail=any_overfit,
        confirms_behaved=confirms_ok,
        r3_only_blindness_suite_caught=r3_only_blind,
        findings=findings)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}")
    return out


if __name__ == "__main__":
    main()
