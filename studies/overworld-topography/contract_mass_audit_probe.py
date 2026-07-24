"""ADVERSARIAL GATE AUDIT probes for contract_mass_gates.py (2026-07-23, READ-ONLY).

Constructs SYNTHETIC candidate views (welded-grid landmasses built from REAL stock-classified UV
triples so classify_tri is exercised for real) and runs the three gate functions on them to test for
BLINDNESS: an input that VIOLATES a gate's contract-intent while PASSING the gate as written.

Nothing here touches the game install or any deploy. It only imports the gate functions + the proven
SNR vocabulary and calls them on in-memory dicts. Output -> out/contract_mass/audit_probes/.

Probes:
  P_R2  -- a REGULAR PICKET COMB at exactly stock's saturation (0.50): the "distribution not
           aggregate" failure the calibrated eye named for Rung E, at an aggregate the gate permits.
  P_R3  -- a RIBBON + ONE token topo-17 inland cell: R3's topological law fires on n>=1 backing.
  P_SUITE -- a full welded landmass (wide grass skirt + picket-comb ecotone band + desert backing)
           run through ALL THREE gates to see whether the suite as a whole is defeated.
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

import contract_mass_gates as GT          # noqa: E402  the module under audit
import seam_null_recon as SNR             # noqa: E402

OUT = HERE / "out" / "contract_mass" / "audit_probes" / "probe_results.json"
# a real-but-empty dir so _scan_staged_sea's Path()/exists() finds no staged sea (returns []) instead
# of choking on mod_dir=None. No sea files are written here.
DUMMY_MOD = str(HERE / "out" / "contract_mass" / "audit_probes" / "_no_staged_sea")
CELL = 4.0
BLOCK = 64.0

# ---- real stock-classified UV triples (extracted live from stock ecotone; guarantees classify_tri
#      fires exactly as on real bytes) --------------------------------------------------------------
UV_GD_ROW2 = [(0.97852, 0.38477), (0.97852, 0.41602), (0.91797, 0.38477)]   # strip_grass_desert k=2
UV_GD_ROW0 = [(0.97852, 0.32227), (0.91797, 0.35254), (0.91797, 0.32227)]   # strip_grass_desert k=0
UV_DESERT_MAINS = [(0.71973, 0.70117), (0.71973, 0.73145), (0.65723, 0.73145)]  # mains_own desert
UV_GRASS_MAINS = [(0.12695, 0.7998), (0.06641, 0.7998), (0.06641, 0.76855)]     # mains_own grass


def _verify_uvs():
    """CALIBRATE THE INSTRUMENT: prove the reused UVs classify as intended before probing."""
    checks = {
        "gd_row2": SNR.classify_tri("desert", UV_GD_ROW2),
        "gd_row0": SNR.classify_tri("desert", UV_GD_ROW0),
        "desert_mains": SNR.classify_tri("desert", UV_DESERT_MAINS),
        "grass_mains": SNR.classify_tri("grass", UV_GRASS_MAINS),
    }
    ok = (checks["gd_row2"] == ("strip_grass_desert", 2)
          and checks["gd_row0"] == ("strip_grass_desert", 0)
          and checks["desert_mains"] == ("mains_own", "desert")
          and checks["grass_mains"] == ("mains_own", "grass"))
    return ok, {k: list(v) for k, v in checks.items()}


def quad_tris(col, row, x0, z0):
    """Two welded tris for cell (col,row). world x = x0 + col*4, world z = z0 - row*4 (z more negative
    inland, mirroring the real map). Adjacent cells share corner POSITIONS -> edge_index welds them."""
    x = x0 + col * CELL
    z = z0 - row * CELL
    p00 = (x, 0.0, z)
    p10 = (x + CELL, 0.0, z)
    p11 = (x + CELL, 0.0, z - CELL)
    p01 = (x, 0.0, z - CELL)
    return [(p00, p10, p11), (p00, p11, p01)]


def make_tri(w3, uv3, fam, topo):
    cx = sum(p[0] for p in w3) / 3.0
    cz = sum(p[2] for p in w3) / 3.0
    cell = (math.floor(cx / CELL), math.floor(cz / CELL))
    block = (math.floor(cx / BLOCK), math.floor(-cz / BLOCK))
    return dict(block=block, topo=topo, idall=0, fam=fam, w=[tuple(p) for p in w3],
                uv=[tuple(u) for u in uv3], cell=cell)


def build_cand(name, cellspec, x0, z0, core_pred):
    """cellspec: dict (col,row) -> list of (uv3, fam, topo) per-tri (len 2, matching quad_tris order).
    core_pred(block) -> bool decides core membership. Builds tris + derives the cand view EXACTLY as
    contract_mass_gates.load_candidate does (same boundary/straddle/body definitions)."""
    tris = []
    for (col, row), tspec in cellspec.items():
        qs = quad_tris(col, row, x0, z0)
        for (w3, (uv3, fam, topo)) in zip(qs, tspec):
            tris.append(make_tri(w3, uv3, fam, topo))
    for i, t in enumerate(tris):
        t["gid"] = i

    core_set = {t["block"] for t in tris if core_pred(t["block"])}
    region_blocks = sorted({t["block"] for t in tris})

    by_gid = {t["gid"]: t for t in tris}
    eo = SNR.edge_index(tris)
    boundary_cells = set()
    n_gd_edges = 0
    for e, owners in eo.items():
        fams = {by_gid[g]["fam"] for g in owners}
        if fams == {"grass", "desert"}:
            n_gd_edges += 1
            for g in owners:
                t = by_gid[g]
                if t["block"] in core_set:
                    boundary_cells.add(t["cell"])
    core_tris = [t for t in tris if t["block"] in core_set]
    cell_fams = defaultdict(set)
    for t in core_tris:
        if t["fam"]:
            cell_fams[t["cell"]].add(t["fam"])
    straddle_cells = {c for c, f in cell_fams.items() if f == {"grass", "desert"}}
    body_tris = [t for t in core_tris if t["topo"] == 16]

    return dict(
        name=name, is_staged=True, mod_dir=DUMMY_MOD,
        core_blocks=[list(b) for b in sorted(core_set)], core_set=core_set,
        region_blocks=region_blocks, tris=tris, core_tris=core_tris, by_gid=by_gid,
        boundary_cells=boundary_cells, straddle_cells=straddle_cells, body_tris=body_tris,
        n_gd_edges=n_gd_edges, cell_fams=cell_fams, block_source={})


# ====================================================================================================
# PROBE P_R2 -- the picket comb at 0.50 saturation (gate_r2 only; no geometry needed)
# ====================================================================================================
def probe_r2():
    """Build a core body of topo-16 tris: alternating DRESSED (gd strip row2) / PLAIN (desert mains)
    columns -> a one-cell-pitch picket comb, saturation exactly 0.50 (== stock 0.5024 ceiling), row0
    fraction ~0 (all decals in row2). The eye rejects a regular picket; the gate must PASS it."""
    # 6 boundary columns x 8 rows; even cols dressed, odd cols plain. Plus a grass margin so the
    # pooled row population also has a grass side (kept at row2 to avoid a row0 spike).
    x0, z0 = 900.0, -700.0
    spec = {}
    for row in range(8):
        for col in range(6):
            if col % 2 == 0:                       # dressed picket column
                spec[(col, row)] = [(UV_GD_ROW2, "desert", 16), (UV_GD_ROW2, "desert", 16)]
            else:                                  # plain desert column
                spec[(col, row)] = [(UV_DESERT_MAINS, "desert", 16), (UV_DESERT_MAINS, "desert", 16)]
        # a grass column at col -1 so grass|desert edges exist and a grass-side strip pop exists
        spec[(-1, row)] = [(UV_GRASS_MAINS, "grass", 3), (UV_GD_ROW2, "grass", 3)]
    cand = build_cand("probe_r2_picket_comb", spec, x0, z0, core_pred=lambda b: True)
    r2 = GT.gate_r2(cand, mode="enforce")
    return cand, r2


def probe_r2b():
    """WRONG-OBJECT evasion: R2's saturation population is `topo==16` body tris, but 'dressed' is a UV
    property set INDEPENDENTLY of the topo idall. Dress every cell (grass-decal UV) but tag the dressed
    cells topo-17 (a legal desert idall). Then body_tris(topo16) is nearly empty -> measured saturation
    ~0 while the mesh is FULLY dressed. The engine renders the decal by UV regardless of topo."""
    x0, z0 = 900.0, -700.0
    spec = {}
    for row in range(8):
        spec[(-1, row)] = [(UV_GRASS_MAINS, "grass", 3), (UV_GRASS_MAINS, "grass", 3)]
        # every desert cell carries a grass DECAL uv but is tagged topo-17 (not 16) ...
        for col in range(6):
            spec[(col, row)] = [(UV_GD_ROW2, "desert", 17), (UV_GD_ROW2, "desert", 17)]
        # ... plus one throwaway plain topo-16 cell so body_tris is non-empty (total=2, dressed=0)
    spec[(6, 0)] = [(UV_DESERT_MAINS, "desert", 16), (UV_DESERT_MAINS, "desert", 16)]
    cand = build_cand("probe_r2b_topo_mislabel", spec, x0, z0, core_pred=lambda b: True)
    r2 = GT.gate_r2(cand, mode="enforce")
    # count how many tris are UV-dressed vs how many R2 actually counts (topo16 body)
    n_uv_dressed = sum(1 for t in cand["tris"]
                       if SNR.classify_tri(t["fam"], t["uv"])[0] == "strip_grass_desert")
    return cand, r2, n_uv_dressed


# ====================================================================================================
# PROBE P_R3 -- a ribbon + one token topo-17 inland cell (gate_r3)
# ====================================================================================================
def probe_r3():
    """A thin desert ribbon (2 cols wide) inside grass -- exactly the RIBBON FALLACY shape -- but with
    ONE topo-17 desert cell placed inland at depth 1. R3's law fires on n>=1 backing, so it PASSES a
    ribbon that returns to grass on every other side."""
    x0, z0 = 900.0, -700.0
    spec = {}
    for row in range(8):
        spec[(-1, row)] = [(UV_GRASS_MAINS, "grass", 3), (UV_GRASS_MAINS, "grass", 3)]   # grass W
        spec[(0, row)] = [(UV_GD_ROW2, "desert", 16), (UV_GD_ROW2, "desert", 16)]        # ribbon col 0
        spec[(1, row)] = [(UV_DESERT_MAINS, "desert", 16), (UV_DESERT_MAINS, "desert", 16)]  # ribbon col1
        # a 3-thick desert BULGE at rows 3..5 so col1row4 becomes an INLAND (depth>=1) desert cell,
        # tagged topo-17 = the single token backing cell. Everywhere else the ribbon is 2 cols thick.
        if row in (3, 4, 5):
            spec[(2, row)] = [(UV_DESERT_MAINS, "desert", 16), (UV_DESERT_MAINS, "desert", 16)]
        else:
            spec[(2, row)] = [(UV_GRASS_MAINS, "grass", 3), (UV_GRASS_MAINS, "grass", 3)]
        spec[(3, row)] = [(UV_GRASS_MAINS, "grass", 3), (UV_GRASS_MAINS, "grass", 3)]     # grass E
    # the one inland token: col1,row4 (surrounded by desert col0/col2/row3/row5) -> topo-17
    spec[(1, 4)] = [(UV_DESERT_MAINS, "desert", 17), (UV_DESERT_MAINS, "desert", 17)]
    cand = build_cand("probe_r3_ribbon_token_backing", spec, x0, z0, core_pred=lambda b: True)
    r3 = GT.gate_r3(cand, mode="enforce")
    return cand, r3


# ====================================================================================================
# PROBE P_SUITE -- can ALL THREE gates be beaten at once by a picket-comb "two-ground" mass?
# ====================================================================================================
def probe_suite():
    """A wide grass skirt (>=48u inset on every side of the ecotone) so R1's land-perimeter standoff
    clears the floors; a picket-comb topo-16 ecotone band at 0.50 saturation (beats R2); a topo-17
    plain-desert backing behind it (beats R3). Straddle cells are seeded at the boundary (one grass +
    one desert tri in the same cell) so R1's straddle measure is defined."""
    x0, z0 = 900.0, -700.0
    spec = {}
    W, H = 44, 44                 # grass field 44x44 cells = 176u square
    # fill entire field with plain grass first
    for col in range(W):
        for row in range(H):
            spec[(col, row)] = [(UV_GRASS_MAINS, "grass", 3), (UV_GRASS_MAINS, "grass", 3)]
    # ecotone inset: rows 14..30 (>=14 cells = 56u from top/bottom edges), boundary at col 20
    r_lo, r_hi = 14, 30
    b_col = 20
    for row in range(r_lo, r_hi):
        # straddle boundary cell at b_col: one grass tri (upper) + one desert dressed tri (lower)
        spec[(b_col, row)] = [(UV_GRASS_MAINS, "grass", 16), (UV_GD_ROW2, "desert", 16)]
        # picket band cols b_col+1 .. b_col+6 : alternate dressed / plain (topo16)
        for k in range(1, 7):
            col = b_col + k
            if k % 2 == 1:
                spec[(col, row)] = [(UV_GD_ROW2, "desert", 16), (UV_GD_ROW2, "desert", 16)]
            else:
                spec[(col, row)] = [(UV_DESERT_MAINS, "desert", 16), (UV_DESERT_MAINS, "desert", 16)]
        # desert backing cols b_col+7 .. b_col+12 : plain topo-17 desert interior
        for col in range(b_col + 7, b_col + 13):
            spec[(col, row)] = [(UV_DESERT_MAINS, "desert", 17), (UV_DESERT_MAINS, "desert", 17)]

    core_blocks = None
    # core = the blocks the ecotone+desert occupy; compute from world of b_col..b_col+12, rows r_lo..r_hi
    def core_pred(block):
        return True   # whole synthetic mass is the candidate footprint

    cand = build_cand("probe_suite_picket_two_ground", spec, x0, z0, core_pred=core_pred)
    r1 = GT.gate_r1(cand, mode="enforce")
    r2 = GT.gate_r2(cand, mode="enforce")
    r3 = GT.gate_r3(cand, mode="enforce")
    overall = "PASS" if all(r["verdict"] == "PASS" for r in (r1, r2, r3)) else "FAIL"
    return cand, dict(overall=overall, R1=r1, R2=r2, R3=r3)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    uv_ok, uv_checks = _verify_uvs()
    print(f"UV calibration: {uv_ok}  {uv_checks}")

    out = dict(uv_calibration=dict(ok=uv_ok, checks=uv_checks), probes={})

    # P_R2
    cand2, r2 = probe_r2()
    print("\n== P_R2 picket comb ==")
    print(f"  body topo16 total={r2['body']['topo16_total']} dressed={r2['body']['n_dressed_grass']} "
          f"plain={r2['body']['n_plain_mains']}")
    print(f"  saturation grass={r2['saturation']['grass_decal']} (<=0.5024?) "
          f"any={r2['saturation']['any_decal']} row0={r2['row_shape']['candidate_row0_fraction']} "
          f"spike={r2['row_shape']['row0_spike_detected']}")
    print(f"  R2 verdict = {r2['verdict']}  (INTENT: reject a saturated/comb arrangement)")
    print(f"  spine (report-only): {r2['spine']['zero_spine_fraction_proxy']} "
          f"band1_plain_rate={r2['spine']['band1_plain_rate']}")
    out["probes"]["P_R2"] = dict(
        verdict=r2["verdict"], saturation=r2["saturation"], row_shape=r2["row_shape"],
        spine=r2["spine"], body=r2["body"],
        intent="catch the SATURATED COMB (distribution, not aggregate)",
        beats_gate=(r2["verdict"] == "PASS"))

    # P_R2B (topo-mislabel evasion)
    cand2b, r2b, n_uv_dressed = probe_r2b()
    print("\n== P_R2B topo-mislabel evasion ==")
    print(f"  UV-dressed tris in mesh = {n_uv_dressed}; R2 body(topo16) total={r2b['body']['topo16_total']} "
          f"counted-dressed={r2b['body']['n_dressed_grass']}")
    print(f"  saturation grass={r2b['saturation']['grass_decal']} any={r2b['saturation']['any_decal']} "
          f"-> R2 verdict = {r2b['verdict']}  (INTENT: bound how dressed the ecotone body is)")
    out["probes"]["P_R2B"] = dict(
        verdict=r2b["verdict"], n_uv_dressed_tris=n_uv_dressed,
        r2_body_total=r2b["body"]["topo16_total"], r2_counted_dressed=r2b["body"]["n_dressed_grass"],
        saturation=r2b["saturation"],
        intent="bound decal saturation of the ecotone body; population keyed on topo==16 only",
        beats_gate=(r2b["verdict"] == "PASS"))

    # P_R3
    cand3, r3 = probe_r3()
    print("\n== P_R3 ribbon + token topo17 backing ==")
    print(f"  boundary_desert_cells={r3['n_boundary_desert_cells']} "
          f"backing_depth={r3['first_desert_family_backing_depth']} "
          f"(first_dunes={r3['first_dunes_depth']} first_topo17={r3['first_topo17_depth']})")
    print(f"  R3 verdict = {r3['verdict']}  (INTENT: distinguish a 2-ground MASS from a ribbon)")
    out["probes"]["P_R3"] = dict(
        verdict=r3["verdict"], backing_depth=r3["first_desert_family_backing_depth"],
        first_dunes=r3["first_dunes_depth"], first_topo17=r3["first_topo17_depth"],
        beyond=r3["beyond_band_family_by_depth"],
        intent="distinguish a two-ground desert MASS from a ribbon that returns to grass",
        beats_gate=(r3["verdict"] == "PASS"))

    # P_SUITE
    candS, res = probe_suite()
    print("\n== P_SUITE picket-comb two-ground mass (all three gates) ==")
    r1 = res["R1"]
    print(f"  R1 boundary={r1['checks']['boundary_cell']['measured_u']}u "
          f"straddle={r1['checks']['straddle_cell']['measured_u']}u "
          f"body={r1['checks']['body_tri']['measured_u']}u (floors 39.953/44.635/42.968) -> {r1['verdict']}")
    print(f"    n_boundary_cells={r1['n_boundary_cells']} n_straddle_cells={r1['n_straddle_cells']} "
          f"n_body_tris={r1['n_body_tris']} land_perim_segs={r1['diagnostics'].get('n_land_perimeter_segments')}")
    print(f"  R2 sat_grass={res['R2']['saturation']['grass_decal']} "
          f"any={res['R2']['saturation']['any_decal']} spike={res['R2']['row_shape']['row0_spike_detected']} "
          f"-> {res['R2']['verdict']}")
    print(f"  R3 backing_depth={res['R3']['first_desert_family_backing_depth']} -> {res['R3']['verdict']}")
    print(f"  SUITE OVERALL = {res['overall']}")
    out["probes"]["P_SUITE"] = dict(
        overall=res["overall"],
        R1=dict(verdict=r1["verdict"], checks=r1["checks"], n_straddle=r1["n_straddle_cells"],
                diagnostics=r1["diagnostics"]),
        R2=dict(verdict=res["R2"]["verdict"], saturation=res["R2"]["saturation"],
                row_shape=res["R2"]["row_shape"], spine=res["R2"]["spine"]),
        R3=dict(verdict=res["R3"]["verdict"], backing_depth=res["R3"]["first_desert_family_backing_depth"]),
        intent="the contract round exists to STOP exactly this shape (picket comb / ribbon)",
        beats_suite=(res["overall"] == "PASS"))

    out["audit_summary"] = dict(
        P_R2_picket_comb_passes_R2=out["probes"]["P_R2"]["beats_gate"],
        P_R2B_topo_mislabel_passes_R2=out["probes"]["P_R2B"]["beats_gate"],
        P_R3_token_backing_passes_R3=out["probes"]["P_R3"]["beats_gate"],
        P_SUITE_picket_comb_passes_all_three=out["probes"]["P_SUITE"]["beats_suite"],
        finding=("R2 is ARRANGEMENT-INVARIANT (a one-cell-pitch picket comb at <=stock saturation "
                 "passes) and its saturation population is keyed on topo==16 while 'dressed' is a "
                 "UV/family-pair property (P_R2B: 96 UV-dressed tris tagged topo-17 -> saturation 0.0 "
                 "PASS) -- the same aggregate-blind-to-arrangement class that killed Rung E, only the "
                 "threshold moved. R3 accepts a ribbon backed by ONE token inland desert cell (no "
                 "minimum backing extent). A synthetic picket-comb two-ground mass passes ALL THREE "
                 "gates. Grounding: Round 11 census shows transition decals attach to family pairs "
                 "across topos 16/17/49, so a topo-16-only saturation population is narrower than the "
                 "study's own decoded vocabulary and violates the LABEL-BLIND CROSS-CHECK meta-law."),
        caveats=("The gates DO reproduce the pinned matrix exactly, DO correctly reject the real "
                 "rung C/D/E builds, and DO pass stock; ceilings trace to falsifier-CONFIRMED numbers. "
                 "The blindness is bounded: combs DENSER than stock (Rung E 75.7%) are caught; only "
                 "combs at/below stock density with mechanical arrangement slip. Stock couples "
                 "grass|desert decals to topo-16, so the topo-mislabel evasion is a malformed-build "
                 "hole, not a normal-pipeline one."))
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}")
    return out


if __name__ == "__main__":
    main()
