"""THE FRESH-SITE PROOF -- finalizer.  Assembles the definitive site record (with its calibration
and controls) and the round report from the run JSONs.  READ-ONLY vs the install.

    py -X utf8 freshmint_finalize.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import freshmint_site_scan as S      # noqa: E402

OUT = HERE / "out" / "foldback"
BLOCK = 64.0
WORLD_W, WORLD_H = 1536.0, 1280.0
# the donor blob: the 3x2-block ecotone core 13-15,11-12, pre-shift centre (928,-768)
BLOB_HALF = (96.0, 64.0)


def rect_d(cx, cz, bx, by):
    x0, x1 = BLOCK * bx, BLOCK * (bx + 1)
    z1, z0 = -BLOCK * by, -BLOCK * (by + 1)
    dx = 0.0 if x0 <= cx <= x1 else min(abs(cx - x0), abs(cx - x1),
                                        abs(cx - x0 + WORLD_W), abs(cx - x1 + WORLD_W),
                                        abs(cx - x0 - WORLD_W), abs(cx - x1 - WORLD_W))
    dz = 0.0 if z0 <= cz <= z1 else min(abs(cz - z0), abs(cz - z1))
    return math.hypot(dx, dz)


def enumerate_lattice(forb):
    """THE ACHIEVABLE-CENTRE LATTICE: cx == 32 (mod 64), cz == 0 (mod 64) -- forced by THE WHOLE-BLOCK
    SHIFT LAW (rung_f_layout:113) applied to the blob's own pre-shift centre (928,-768)."""
    rows = []
    for bx0 in range(24):
        cx = BLOCK * bx0 + 96.0
        if cx >= WORLD_W:
            continue
        for by0 in range(19):
            cz = -BLOCK * (by0 + 1)
            cap = min(cx, WORLD_W - cx, abs(cz), abs(-WORLD_H - cz))
            dmin = min(rect_d(cx, cz, b[0], b[1]) for b in forb)
            rows.append(dict(cx=cx, cz=cz, off_seam_and_edge_cap=cap,
                             nearest_forbidden_block=round(dmin, 2), R_max=round(min(cap, dmin), 2),
                             blockers=[list(b) for b in sorted(forb)
                                       if rect_d(cx, cz, b[0], b[1]) <= dmin + 0.01][:4]))
    rows.sort(key=lambda r: -r["R_max"])
    return rows


def main():
    grid = json.loads((OUT / "stock_grid.json").read_text())
    stock_occ = {tuple(map(int, k.split(","))) for k in grid["occ"]}
    live = S.live_blocks()
    rungf = {(bx, by) for bx in range(0, 5) for by in range(15, 20)}
    forb = stock_occ | live | S.NAMED_BENCH_BLOCKS

    cur = enumerate_lattice(forb)
    ctlA = enumerate_lattice(stock_occ)                       # the pre-any-deploy world
    ctlC = enumerate_lattice(stock_occ | (live - rungf))       # every deploy EXCEPT rung F

    free_map = ["".join("." if (bx, by) not in forb else "#" for bx in range(24)) for by in range(20)]

    site = dict(
        method=(
            "THE ACHIEVABLE-CENTRE LATTICE is forced, not chosen.  rung_f_layout:113 -- a WHOLE-BLOCK "
            "shift on BOTH axes maps the 6 donor blocks (13-15,11-12) onto 6 target blocks with ZERO "
            "re-partition; a PHASE shift re-partitions every donor border tri into un-weldable "
            "T-junctions.  The blob's pre-shift centre is (928,-768) and the island centre must sit ON "
            "the blob centre (an offset of 7.8u already broke the clean annulus in rung-F's rebuild "
            "attempt 1), so a legal centre satisfies cx == 32 (mod 64) AND cz == 0 (mod 64).  Legal "
            "radius = min(off-seam cap, grid-edge cap, distance to the nearest FORBIDDEN block), where "
            "FORBIDDEN = every stock prefab-occupied block (THE OPEN-OCEAN TARGET LAW, block-granular) "
            "+ every live-deployed block in FF9CustomMap-world + every bench named in the study."),
        instrument_calibration=dict(
            claim="the free-block map + disc kernel reproduce the value rung_f_layout:74-76 recorded",
            recorded="the largest NON-WRAPPING TRUE-OCEAN circle in the world is Rmax=132 @ (144,-1144)",
            measured_stock_only_4u_sweep="R=132.3 @ (136,-1144); R=130.7 @ (140,-1144)",
            verdict="CALIBRATED"),
        counts=dict(grid_blocks=480, stock_prefab_occupied=len(stock_occ),
                    live_deployed=len(live), named_benches_adding_beyond=len(
                        S.NAMED_BENCH_BLOCKS - stock_occ - live),
                    forbidden_total=len(forb), free=480 - len(forb)),
        free_block_map=dict(legend="'.' = mintable (true open ocean, undeployed); '#' = forbidden",
                            columns="bx 0..23 left to right", rows=free_map),
        capacity_floor=dict(
            donor_rect_half_extent_u=list(BLOB_HALF),
            donor_rect_half_diagonal_u=round(math.hypot(*BLOB_HALF), 2),
            kept_cells_max_radius_u=107.70,
            R_cells_incl_dropped_and_enclosed_max_radius_u=115.38,
            dilated_grass_remove_ring_max_radius_u=118.73,
            rung_f_proven_floor_u=125.38,
            rung_f_proven_floor_derivation=("dilated grass rim 118.73u + rung-F's own measured >=6u "
                                            "clean-annulus margin (rung_f_layout:81-88) -> ~125u; "
                                            "rung-F shipped R=125.0"),
            pipeline_measured_floor_u="between 118 and 121 (bisected by the gate battery itself)",
            pipeline_floor_evidence=dict(
                r112="3 reds -- WELD-INTEGRITY open_edges=317, WELD AUDIT 4, CONTRACT R1 0.137/2.0/0.943",
                r118="3 reds (same set) -- open_edges=325, WELD AUDIT 5, CONTRACT R1 0.137/2.0/0.943",
                r121="0 reds besides S0 -- open_edges=0, WELD AUDIT 0, CONTRACT R1 42.815/44.887/45.552 "
                     "(straddle floor 44.635 -> only 0.252u of headroom)")),
        current_world=dict(
            top=cur[:6],
            verdict=("NO FRESH SITE EXISTS.  The best remaining legal centre is (160,-128) at "
                     "R_max=115.38u -- below the pipeline's own measured floor (121u) and far below "
                     "rung-F's proven 125.38u.")),
        control_A_stock_only=dict(
            top=ctlA[:4],
            verdict=("Even in the PRE-ANY-DEPLOY world the whole-block lattice admits exactly ONE "
                     "centre at R>=125: (160,-1152) at R=128.0 -- the rung-F site itself.  The world "
                     "has capacity for exactly ONE two-ground landmass of this donor's size.")),
        control_C_all_deploys_except_rung_f=dict(
            top=ctlC[:4],
            verdict=("(160,-1152) is free again at R=128 -- so the DEPLOYED rung-F island is the sole "
                     "blocker; no other bench costs a site.")),
        impossibility_proof=(
            "At (160,-128) the two blocking blocks are (0,0) and (4,3).  Their nearest corners lie at "
            "offsets (-96,+64) and (+96,-64) from the centre -- EXACTLY ANTIPODAL, each 115.38u away.  "
            "Those are precisely the two directions in which the donor blob's own corners point "
            "(atan2(+-64,+-96)).  Any shape (disc, perturbed circle, multi-lobe) that contains the blob "
            "plus its 4u grass dilation and a non-zero annulus margin must reach past 118.73u in those "
            "directions, so no centre offset and no outline shape can rescue the site: 2 x 115.38 = "
            "230.76u of available span against 2 x 118.73 = 237.46u required at ZERO margin."),
        chosen_site=dict(
            cx=160.0, cz=-128.0, island_radius_run=125.0, shift_cells=[-192, 160],
            shift_world=[-768.0, 640.0], shift_blocks=[-12, 10],
            whole_block_shift_law="SATISFIED (-192 % 16 == 0, 160 % 16 == 0)",
            distance_from_rung_f_centre_u=1024.0,
            distance_to_nearest_deployed_or_bench_block_u=357.8,
            stock_LAND_vertex_clearance_u=130.60,
            note=("the site fails on PREFAB OCCUPANCY, not on land collision: the nearest stock LAND "
                  "vertex is 130.60u away (outside R=125), but blocks (0,0) and (4,3) load their own "
                  "prefabs and an r125 disc penetrates their corners by 9.62u")),
    )
    (OUT / "freshmint_site.json").write_text(json.dumps(site, indent=1))
    print("wrote out/foldback/freshmint_site.json")
    print(json.dumps(site["current_world"]["top"][:3], indent=1))
    print(site["current_world"]["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
