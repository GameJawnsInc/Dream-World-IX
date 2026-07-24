from __future__ import annotations
import math, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))
from ff9mapkit import config as _cfg
from ff9mapkit.world import extract as X
import rung_f_layout as RFL
import rung_f_holefill as HF

CELL = 4.0


def main():
    gr = Path(_cfg.find_game_path(None))
    # rebuild the stitch inputs to inspect the blob holes
    built = RFL.mint_grass_frame(gr)
    frame_blocks = dict(built["blocks"])
    host_bms = {blk: RFL.bm_world_soup(bm, blk[0], blk[1]) for blk, bm in frame_blocks.items()}
    donor = RFL.load_donor_window(gr)
    out, placed_R, carried_translated, diag = RFL.carry(donor, host_bms, RFL.LAND_HEIGHT)
    carried_world = [tri for tris in RFL._reparted(donor, placed_R) for tri in tris] if hasattr(RFL, "_reparted") else None

    comp = RFL.compose(gr)
    final = comp["final_blocks"]
    placed = comp["placed_R"]
    gpos = []; gtris = []
    for blk, bm in final.items():
        base = len(gpos)
        ox, oz = X.block_world_origin(blk[0], blk[1])
        for v in bm.verts:
            gpos.append((v[0] + ox, v[1], v[2] + oz))
        for tri in bm.tris:
            gtris.append((base + tri[0], base + tri[1], base + tri[2]))
    ecnt = Counter()
    for (i, j, k) in gtris:
        pts = [(round(gpos[v][0], 3), round(gpos[v][1], 3), round(gpos[v][2], 3)) for v in (i, j, k)]
        for q in range(3):
            if pts[q] == pts[(q + 1) % 3]:
                continue
            ecnt[tuple(sorted((pts[q], pts[(q + 1) % 3])))] += 1
    open_bad = [e for e, nn in ecnt.items() if nn == 1 and not (e[0][1] <= 1e-3 and e[1][1] <= 1e-3)]
    print(f"ONCE-EDGES: {len(open_bad)}")
    for e in open_bad:
        print("   ", e)


if __name__ == "__main__":
    main()
