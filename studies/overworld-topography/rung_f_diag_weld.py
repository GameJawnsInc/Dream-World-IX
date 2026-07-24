from __future__ import annotations
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))
from ff9mapkit import config as _cfg
from ff9mapkit.world import mesh as M
import rung_f_layout as RFL


def main():
    gr = Path(_cfg.find_game_path(None))
    # grass frame alone
    built = RFL.mint_grass_frame(gr)
    fb = dict(built["blocks"])
    gtot = 0
    for blk, bm in fb.items():
        w = M.weld_audit([bm])
        if w:
            print(f"GRASS FRAME near-miss block {blk}: {len(w)}")
            for p in w[:4]:
                print("    ", p)
            gtot += len(w)
    print(f"grass frame total near-miss: {gtot}")
    # full composite
    comp = RFL.compose(gr)
    final = comp["final_blocks"]
    placed = comp["placed_R"]
    ctot = 0
    for blk, bm in final.items():
        w = M.weld_audit([bm])
        if w:
            print(f"COMPOSITE near-miss block {blk}: {len(w)}")
            import math
            for p in w:
                # classify each vert: in placed cell?
                def cell(pt):
                    return (math.floor(pt[0] / 4.0), math.floor(pt[2] / 4.0))
                print("    ", p, "cells", cell(p[0]) in placed, cell(p[1]) in placed)
            ctot += len(w)
    print(f"composite total near-miss: {ctot}")


if __name__ == "__main__":
    main()
