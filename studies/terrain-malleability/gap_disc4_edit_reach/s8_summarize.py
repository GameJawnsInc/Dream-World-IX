"""STEP 8 -- headline numbers for NOTES.md, derived ONLY from out/*.json written by s1-s7 (no new measurement).

Prints: the recovery table (189 refused land cells x strategy), hazard fractions of replay by edit class, the
refused cells that had no walkable lattice point, the order-invariant / per-part gate cell lists, and the morph
(cliff-bump) three-way counts.
Run (from C:\\gd\\Dream-World-IX\\ff9mapkit):  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_disc4_edit_reach/s8_summarize.py
"""
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
s1 = json.loads((OUT / "s1_gate.json").read_text(encoding="utf-8"))
reach = json.loads((OUT / "reach.json").read_text(encoding="utf-8"))["cells"]
summ = json.loads((OUT / "reach_summary.json").read_text(encoding="utf-8"))
s6 = json.loads((OUT / "s6_semantic.json").read_text(encoding="utf-8"))
s7 = json.loads((OUT / "s7_morph_replay.json").read_text(encoding="utf-8"))

refused = [tuple(c) for c in s1["refused_land_shipped"]]
in_pop = {tuple(map(int, k.split(","))) for k in reach}
print("refused land cells:", len(refused), "| in the edit population:", len(in_pop & set(refused)),
      "| no walkable 4u lattice point:", sorted(set(refused) - in_pop))
print("\nSINGLE-CELL gate recovery (a gate verdict is per cell):")
print("  order-invariant gate (all parts exact permutations):", len(s1["orderinv_flips_land"]), s1["orderinv_flips_land"])
print("  per-part gate (Terrain identical or permuted):", len(s6["A"]["terrain_ok_cells"]), "refusing parts:", s6["A"]["refusing_parts"])

print("\nEDIT-LEVEL lawful fraction over the population (atomic over every touched cell):")
classes = list(summ["n_by_class"])
print("  n per class:", summ["n_by_class"])
print(f"  {'strategy':13s} overall  " + " ".join(f"{c:>9s}" for c in classes))
for s, v in summ["overall"].items():
    print(f"  {s:13s} {v:7.3f}  " + " ".join(f"{summ['by_class'][s].get(c, 0):9.3f}" for c in classes))
print("\nCELLS RECOVERED (population cells; any / >=50% / all edits lawful):")
for s, v in summ["cells_recovered"].items():
    print(f"  {s:13s} any {v['any']:3d}  ge50 {v['ge50']:3d}  all {v['all']:3d}  of {v['of']}")
print("\nREPLAY hazard incidence (share of the class's edits whose support touches each disc-4 hazard layer):")
for c in classes:
    n = summ["n_by_class"][c]
    h = summ["hazards_by_class"].get(c, {})
    print(f"  {c:11s} " + "  ".join(f"{k} {h[k] / n:.3f}" for k in sorted(h)))
print("\nCRACK under per-cell gating (edits on refused cells that ALSO touch an eligible cell, moving a shared border vertex):")
for g, rows in summ["crack_current_design"].items():
    tot = sum(r["crack"] for r in rows.values()); n = sum(r["n"] for r in rows.values())
    big = sum(r["step_ge_1u"] for r in rows.values())
    print(f"  {g:9s} {tot} of {n} reshape edits ({tot / n:.3f}); step >= 1u: {big}")
pb = s7["partB"]
print(f"\nMORPH (cliff-bump, certified on disc 1) on refused coastal cells: tested {pb['tested']}, "
      f"replay passes its own gates on disc 4 {pb['replay_clean']}, delta lawful {pb['delta_ok']}, "
      f"delta == replay {pb['delta_eq_replay']}/{pb['both']}, lawful-delta min XZ clearance {min(pb['delta_ok_min_xz_dist'])}u")
C = s6["C"]
print(f"\nCLOSED entrance cells: {C['lost_cells']} disc-1 event-tile cells lost on disc 4; WORLD08 trigger for "
      f"{C['lost_cells_with_w08_trigger']}, WORLD09 trigger for {C['lost_cells_with_w09_trigger']}")
print("E pin bug: RiverJoint pinned", s6["E"]["riverjoint_pins"], "x, River pinned", s6["E"]["river_pins"], "x")
sys.exit(0)
