from __future__ import annotations
import math, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))
from ff9mapkit import config as _cfg
import rung_f_layout as RFL
import rung_f_holefill as HF

CELL = 4.0


def main():
    gr = Path(_cfg.find_game_path(None))
    # replicate the stitch inputs
    built = RFL.mint_grass_frame(gr)
    frame_blocks = dict(built["blocks"])
    host_bms = {blk: RFL.bm_world_soup(bm, blk[0], blk[1]) for blk, bm in frame_blocks.items()}
    donor = RFL.load_donor_window(gr)
    out, placed_R, carried_translated, diag = RFL.carry(donor, host_bms, RFL.LAND_HEIGHT)
    grass_remove = HF.dilate(placed_R, 1)

    def tri_cell(tri):
        cx = sum(v[0][0] for v in tri) / 3.0
        cz = sum(v[0][2] for v in tri) / 3.0
        return (math.floor(cx / CELL), math.floor(cz / CELL))

    grass_world = []
    for blk, soup in host_bms.items():
        for tri in soup:
            if tri_cell(tri) not in grass_remove:
                grass_world.append(tri)
    loops = HF.boundary_loops(grass_world)
    print(f"grass_world tris={len(grass_world)}; boundary loops={len(loops)}")
    for i, lp in enumerate(sorted(loops, key=lambda l: -abs(HF._signed_area_xz([v[0] for v in l])))[:12]):
        ys = [v[0][1] for v in lp]
        area = HF._signed_area_xz([v[0] for v in lp])
        print(f"  loop {i}: len={len(lp)} area={area:.0f} y[{min(ys):.2f},{max(ys):.2f}] "
              f"n_below_skirt={sum(1 for y in ys if y <= 1e-3)}")
    # also directed half-edge stats
    og, vo = HF.directed_boundary_halfedges(grass_world)
    degs = [len(v) for v in og.values()]
    from collections import Counter
    print(f"outgoing degree hist: {Counter(degs)}")
    # count above-skirt boundary edges
    be = HF.boundary_edges(grass_world)
    above = [e for e in be if e[0][0][1] > 1e-3 and e[1][0][1] > 1e-3]
    print(f"boundary edges={len(be)}, above-skirt={len(above)}")


if __name__ == "__main__":
    main()
