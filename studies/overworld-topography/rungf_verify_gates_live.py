import sys
sys.argv = ["verify"]
import contract_mass_gates as G
LIVE = r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap-world"
RUNGF_CORE = sorted({(bx,by) for by in (16,17,18,19) for bx in (0,1,2,3,4)})
print("="*80); print("STOCK calibration (instrument check)"); print("="*80)
stock = G.load_candidate("stock", None, core_blocks=G.ECOTONE_CORE)
srow = G.run_matrix_on(stock)
print(f"  STOCK overall: {srow['overall']} (R1={srow['R1']['verdict']} R2={srow['R2']['verdict']} R3={srow['R3']['verdict']})")
print("="*80); print("RUNG F -- LIVE folder, scoped to rung_f core (cols 0-4 rows 16-19)"); print("="*80)
cand = G.load_candidate("rung_f_live", LIVE, core_blocks=RUNGF_CORE)
print(f"  boundary_cells={len(cand['boundary_cells'])} straddle_cells={len(cand['straddle_cells'])} body_tris={len(cand['body_tris'])} gd_edges={cand['n_gd_edges']}")
row = G.run_matrix_on(cand); r1,r2,r3 = row["R1"], row["R2"], row["R3"]
print(f"  RUNG F overall: {row['overall']}  R1={r1['verdict']} R2={r2['verdict']} R3={r3['verdict']}")
c = r1["checks"]
print(f"    R1 measured: boundary={c['boundary_cell']['measured_u']}u straddle={c['straddle_cell']['measured_u']}u body={c['body_tri']['measured_u']}u (floors 39.953/44.635/42.968); convention_invalid={r1['convention_invalid']}")
print(f"    R2 sat grass={r2['saturation']['grass_decal']} any={r2['saturation']['any_decal']} fringe={r2['arrangement']['fringe_concentration']} pen={r2['arrangement']['penetration_ge2_fraction']} float={r2['arrangement']['n_floating_components']}")
print(f"    R3 backing reachable={r3['largest_reachable_backing_cells']} interface={r3['skin_backing_interface_pairs']} erosion={r3['erosion_survive_backing_cells']}")
