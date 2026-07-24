"""RUNG F -- DESIGN probe (2026-07-24). READ-ONLY vs the install.

Three load-bearing measurements the design needs that the S1/S2 scouts did not pin:
  (A) The realized STANDOFF budget: the tight bbox of the R1-MEASURED features (grass|desert
      boundary cells, straddle cells, label-blind desert body-tris = the skin) -- NOT the whole
      ensemble (the dunes backing + grass fringe are not R1-measured). This bbox is what must clear
      >=64u guide from every coast, so it fixes the minimum landmass extent.
  (B) The site question: is block (3,15) real land (the lone violator of a 5x4 margin=1 rect at
      (0,16))? If it is trivial/absent, the 5x4 site is available and the 4x3 tightness dissolves.
      Re-verify (0,17) 4x3 + (0,16) 5x4 open-ocean + margin via island._real_block_parts (the same
      gate landmass() uses).
  (C) Where the 164 topo-49 rock tris + the dunes sit relative to the ensemble EDGE (do they reach
      the weld seam -> apron/rock-carry, or are they interior -> trivial grass weld?).

Reuses seam_null_recon load/FAM_OF + island._real_block_parts (the OPEN-OCEAN gate). ZERO writes to
the install; artifact -> out/rung_f/design_probe.json.
"""
from __future__ import annotations
import json, math, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR
from ff9mapkit.world import extract as X
from ff9mapkit.world import island as ISL

CELL = 4.0
OUT = HERE / "out" / "rung_f" / "design_probe.json"
CORE = [(bx, by) for bx in (13, 14, 15) for by in (11, 12)]
# include the ring blocks so grass|desert edges that span a block boundary are seen
REGION = sorted({(bx + dx, by + dy) for (bx, by) in CORE for dx in (-1, 0, 1) for dy in (-1, 0, 1)})


def main():
    out = {}
    tris, bms, src = SNR.load_tris(REGION, source="stock")
    by_gid = {t["gid"]: t for t in tris}
    core_set = set(CORE)

    # ---- (A) R1-measured feature bbox ------------------------------------------------------------
    eo = SNR.edge_index(tris)
    boundary_cells = set()
    for e, owners in eo.items():
        fams = {by_gid[g]["fam"] for g in owners}
        if fams == {"grass", "desert"}:
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
    body16 = [t for t in core_tris if t["topo"] == 16]

    def bbox_cells(cells):
        xs = [c[0] for c in cells]; ys = [c[1] for c in cells]
        return dict(x_lo=min(xs), x_hi=max(xs), y_lo=min(ys), y_hi=max(ys),
                    w_cells=max(xs) - min(xs) + 1, h_cells=max(ys) - min(ys) + 1,
                    w_u=(max(xs) - min(xs) + 1) * CELL, h_u=(max(ys) - min(ys) + 1) * CELL, n=len(cells))

    body16_cells = {t["cell"] for t in body16}
    measured_cells = boundary_cells | straddle_cells | body16_cells
    out["A_standoff_features"] = dict(
        boundary_bbox=bbox_cells(boundary_cells),
        straddle_bbox=bbox_cells(straddle_cells),
        body16_bbox=bbox_cells(body16_cells),
        measured_union_bbox=bbox_cells(measured_cells),
        note="measured_union_bbox is the R1 critical footprint: it must clear the standoff floors "
             "to EVERY coast. Min landmass land-extent = this bbox + 2*guide(64u) each axis.")
    mb = out["A_standoff_features"]["measured_union_bbox"]
    out["A_standoff_features"]["min_landmass_land_extent_u"] = dict(
        w=mb["w_u"] + 128.0, h=mb["h_u"] + 128.0,
        w_blocks=round((mb["w_u"] + 128.0) / 64.0, 2), h_blocks=round((mb["h_u"] + 128.0) / 64.0, 2))

    # ---- (C) rock + dunes vs the ensemble EDGE ---------------------------------------------------
    # ensemble bbox from scout
    sw = json.loads((HERE / "out" / "rung_f" / "scout_window.json").read_text())
    ens_rect = sw["ensemble"]["cell_rect"]  # [x_lo,y_lo,x_hi,y_hi]
    ex0, ey0, ex1, ey1 = ens_rect
    backing = {tuple(c) for c in sw["backing_dunes"]["cells"]}
    rock_cells = {t["cell"] for t in core_tris if t["topo"] == 49}
    dunes_cells = {t["cell"] for t in core_tris if t["topo"] == 41}

    def on_edge(c, ring=1):
        return (c[0] <= ex0 + ring - 1 or c[0] >= ex1 - ring + 1
                or c[1] <= ey0 + ring - 1 or c[1] >= ey1 - ring + 1)

    rock_on_edge = sorted(c for c in rock_cells if on_edge(c, 2))
    dunes_on_edge = sorted(c for c in dunes_cells if on_edge(c, 2))
    out["C_edge"] = dict(
        ensemble_cell_rect=ens_rect,
        n_rock_cells_core=len(rock_cells), n_rock_cells_within_2_of_edge=len(rock_on_edge),
        rock_edge_sample=rock_on_edge[:30],
        n_dunes_cells_core=len(dunes_cells), n_dunes_within_2_of_edge=len(dunes_on_edge),
        dunes_edge_sample=dunes_on_edge[:20],
        backing_bbox=bbox_cells(backing),
        note="dunes_within_2_of_edge>0 means the byte-rigid rect weld would put dunes against minted "
             "grass (no decal vocab) -> must grow the carry so grass/rock fringe wraps the dunes.")

    # a compact ASCII of the ensemble region (skin=S, dunes=n, rock=#, grass=',', boundary=B)
    x0, y0, x1, y1 = ex0 - 2, ey0 - 2, ex1 + 2, ey1 + 2
    cell_topo = defaultdict(Counter)
    for t in core_tris:
        cell_topo[t["cell"]][t["topo"]] += 1
    rows = []
    for y in range(y1, y0 - 1, -1):
        line = f"{y:5d} "
        for x in range(x0, x1 + 1):
            c = (x, y)
            if c in boundary_cells: ch = "B"
            elif c in backing: ch = "n"
            elif c in dunes_cells: ch = "u"
            elif (x, y) in rock_cells: ch = "#"
            elif c in body16_cells: ch = "S"
            elif c in cell_topo:
                dom = cell_topo[c].most_common(1)[0][0]
                ch = "," if dom in (0, 1, 2, 10, 11, 12) else ("d" if dom in (16, 17, 19, 20) else "?")
            else: ch = "."
            line += ch
        rows.append(line)
    out["C_edge"]["ascii"] = rows
    out["C_edge"]["ascii_legend"] = "B grass|desert boundary cell | S topo16 skin | n backing-dunes | u other dunes | # rock49 | d desert | , grass | . no-tri"

    # ---- (B) the site question -------------------------------------------------------------------
    def occ(bx, by):
        try:
            return ISL._real_block_parts((bx, by), disc=1)
        except Exception as e:
            return {"_error": str(e)}
    # (3,15) the lone 5x4(0,16) violator; plus the whole 5x4 rect + its 1-block margin ring
    site54 = [(x, y) for x in range(0, 5) for y in range(16, 20)]      # cols0-4 rows16-19
    ring54 = sorted({(x + dx, y + dy) for (x, y) in site54 for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                     if 0 <= x + dx < 24 and 0 <= y + dy < 20} - set(site54))
    site43 = [(x, y) for x in range(0, 4) for y in range(17, 20)]     # cols0-3 rows17-19 (recommended)
    ring43 = sorted({(x + dx, y + dy) for (x, y) in site43 for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                     if 0 <= x + dx < 24 and 0 <= y + dy < 20} - set(site43))
    def scan(blocks):
        return {f"{b[0]},{b[1]}": occ(*b) for b in blocks}
    b315 = occ(3, 15)
    out["B_site"] = dict(
        block_3_15=b315, block_3_15_is_land=bool(b315) and "_error" not in b315,
        site_5x4_0_16=dict(rect_occ=scan(site54),
                           rect_all_open=all(not v for v in scan(site54).values()),
                           margin_occ=scan(ring54),
                           margin_violators=sorted(k for k, v in scan(ring54).items() if v)),
        site_4x3_0_17=dict(rect_occ=scan(site43),
                           rect_all_open=all(not v for v in scan(site43).values()),
                           margin_occ=scan(ring43),
                           margin_violators=sorted(k for k, v in scan(ring43).items() if v)),
    )

    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    # console summary
    print("=== (A) STANDOFF FEATURES ===")
    for k in ("boundary_bbox", "straddle_bbox", "body16_bbox", "measured_union_bbox"):
        b = out["A_standoff_features"][k]
        print(f"  {k}: {b['w_u']}x{b['h_u']}u ({b['n']} cells) x[{b['x_lo']},{b['x_hi']}] y[{b['y_lo']},{b['y_hi']}]")
    print("  MIN LANDMASS extent:", out["A_standoff_features"]["min_landmass_land_extent_u"])
    print("\n=== (C) EDGE ===")
    print(f"  rock cells core={out['C_edge']['n_rock_cells_core']} within2edge={out['C_edge']['n_rock_cells_within_2_of_edge']}")
    print(f"  dunes within2edge={out['C_edge']['n_dunes_within_2_of_edge']}  backing bbox={out['C_edge']['backing_bbox']['w_u']}x{out['C_edge']['backing_bbox']['h_u']}u")
    for r in rows: print(r)
    print("\n=== (B) SITE ===")
    print(f"  block (3,15): land={out['B_site']['block_3_15_is_land']}  parts={b315}")
    print(f"  5x4 (0,16): all_open={out['B_site']['site_5x4_0_16']['rect_all_open']}  margin_violators={out['B_site']['site_5x4_0_16']['margin_violators']}")
    print(f"  4x3 (0,17): all_open={out['B_site']['site_4x3_0_17']['rect_all_open']}  margin_violators={out['B_site']['site_4x3_0_17']['margin_violators']}")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
