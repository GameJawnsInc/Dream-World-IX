"""RUNG F UV-FIX round 2 -- THE R1 GATE-EVOLUTION MATRIX HARNESS (read-only, no game writes).

Runs the full verdict matrix through contract_mass_gates' LIVE gate functions so it can be executed
BEFORE and AFTER the _staged_sea_underlap semantics evolution and diffed. Candidates:
  stock          -- the map's ONE grass|desert ecotone (must PASS)
  lawful_control -- p4_suite_lawful_ctrl, the synthetic two-ground satisfiability proof (must PASS)
  rung_e / rung_d / rung_c -- the staged negative controls (must REJECT overall)
  rung_f_specimen -- out/rung_f/FF9CustomMap-world (round-0 build; Sea4 replaced with stubs)
  rung_f_FIXED    -- out/rung_f/FF9CustomMap-world-FIXED (round-1: full Sea4 restored -> full-underlay)

Usage:  py -X utf8 uvf_gate_evolution.py <phase-label> <out.json>
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import contract_mass_gates as GT          # noqa: E402  the module under evolution
import contract_mass_reaudit3 as R3       # noqa: E402  the synthetic lawful two-ground control

RUNG_C_FOREIGN = Path(
    r"C:/gd/Dream-World-IX/.claude/worktrees/overworld-tools-performance-a36df4/"
    r"studies/overworld-topography/out/mixed_biome_mint/FF9CustomMap-world")


def r1_detail(r1):
    ch = r1["checks"]
    diag = r1.get("diagnostics", {})
    ul = diag.get("staged_sea_underlap", {})
    return dict(
        verdict=r1["verdict"],
        convention=r1["convention"],
        convention_invalid=r1.get("convention_invalid"),
        sea_vertex_convention_invalid=r1.get("sea_vertex_convention_invalid",
                                             ch.get("sea_vertex_convention_invalid")),
        standoff_pass=r1["standoff_pass"],
        boundary_u=ch.get("boundary_cell", {}).get("measured_u"),
        straddle_u=ch.get("straddle_cell", {}).get("measured_u"),
        body_u=ch.get("body_tri", {}).get("measured_u"),
        floors=r1.get("floors"),
        underlap_fired=ul.get("convention_invalid"),
        n_full_block_planes=ul.get("n_full_block_planes"),
        invalid_sea_vertex_body_u=diag.get("invalid_sea_vertex_convention_body_u"),
        n_land_perimeter_segments=diag.get("n_land_perimeter_segments"),
    )


def matrix_row_from_cand(name, cand):
    row = GT.run_matrix_on(cand)
    return dict(name=name, overall=row["overall"],
                R1=row["R1"]["verdict"], R2=row["R2"]["verdict"], R3=row["R3"]["verdict"],
                r1_detail=r1_detail(row["R1"]))


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "phase"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "out" / "rung_f" / f"uvf_matrix_{phase}.json"
    rows = []
    notes = {}

    # 1. stock ecotone
    stock = GT.load_candidate("stock_ecotone_13-15_11-12", None, core_blocks=GT.ECOTONE_CORE)
    rows.append(matrix_row_from_cand("stock_ecotone_13-15_11-12", stock))

    # 2. lawful two-ground control (synthetic satisfiability proof)
    lc = R3.p4_suite_lawful_ctrl()
    rows.append(dict(name="lawful_two_ground_control", overall=lc["suite_overall"],
                     R1=lc["R1"]["verdict"], R2=lc["r2"]["verdict"], R3=lc["R3"]["verdict"],
                     r1_detail=dict(verdict=lc["R1"]["verdict"],
                                    convention=lc["R1"]["convention"],
                                    convention_invalid=lc["R1"]["convention_invalid"],
                                    standoff_pass=lc["R1"]["standoff_pass"],
                                    boundary_u=lc["R1"]["boundary"], straddle_u=lc["R1"]["straddle"],
                                    body_u=lc["R1"]["body"])))

    # 3. staged negative controls
    for name, mod_dir in (("rung_e", HERE / "out" / "rung_e" / "FF9CustomMap-world"),
                          ("rung_d", HERE / "out" / "rung_d" / "FF9CustomMap-world"),
                          ("rung_c_foreign_mixed_biome_mint", RUNG_C_FOREIGN)):
        if not Path(mod_dir).is_dir() or not GT.detect_footprint(mod_dir):
            notes[name] = f"SKIPPED -- not re-runnable ({mod_dir} missing or no Terrain overrides)"
            continue
        cand = GT.load_candidate(name, str(mod_dir))
        rows.append(matrix_row_from_cand(name, cand))

    # 4. Rung-F specimen (stubs) + FIXED (full sea = full-underlay)
    for name, mod_dir in (("rung_f_specimen", HERE / "out" / "rung_f" / "FF9CustomMap-world"),
                          ("rung_f_FIXED", HERE / "out" / "rung_f" / "FF9CustomMap-world-FIXED")):
        if not Path(mod_dir).is_dir() or not GT.detect_footprint(mod_dir):
            notes[name] = f"SKIPPED -- {mod_dir} missing"
            continue
        cand = GT.load_candidate(name, str(mod_dir))
        rows.append(matrix_row_from_cand(name, cand))

    snap = dict(phase=phase, gate_module_version=_module_version(),
                matrix=rows, skipped_notes=notes)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, indent=1), encoding="utf-8")
    print(f"[{phase}] wrote {out}")
    for r in rows:
        d = r["r1_detail"]
        print(f"  {r['name']:36s} overall={r['overall']:5s} R1={r['R1']:18s} R2={r['R2']:5s} "
              f"R3={r['R3']:5s}  ci={d.get('convention_invalid')} "
              f"sea_ci={d.get('sea_vertex_convention_invalid')} "
              f"body_u={d.get('body_u')} underlap={d.get('underlap_fired')}")
    return snap


def _module_version():
    import re
    txt = (HERE / "contract_mass_gates.py").read_text(encoding="utf-8")
    m = re.search(r'version="(v\d+)"', txt)
    return m.group(1) if m else "?"


if __name__ == "__main__":
    main()
