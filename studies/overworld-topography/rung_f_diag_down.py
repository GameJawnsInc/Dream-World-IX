from __future__ import annotations
import math, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))
from ff9mapkit import config as _cfg
from ff9mapkit.world import extract as X
import rung_f_layout as RFL

CELL = 4.0


def main():
    gr = Path(_cfg.find_game_path(None))
    comp = RFL.compose(gr)
    final = comp["final_blocks"]
    placed = comp["placed_R"]
    n = 0
    for blk, bm in final.items():
        ox, oz = X.block_world_origin(blk[0], blk[1])
        for tri in bm.tris:
            p3 = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            a, b, c = p3
            ny2 = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
            if ny2 <= 0:
                cx = sum(p[0] for p in p3) / 3; cz = sum(p[2] for p in p3) / 3
                cell = (math.floor(cx / CELL), math.floor(cz / CELL))
                if cell not in placed:
                    n += 1
                    ys = [round(p[1], 2) for p in p3]
                    print(f"DOWN non-placed blk={blk} cell={cell} ny2={ny2:.4f} y={ys} "
                          f"xz={[(round(p[0],2),round(p[2],2)) for p in p3]}")
    print(f"total down non-placed: {n}")


if __name__ == "__main__":
    main()
