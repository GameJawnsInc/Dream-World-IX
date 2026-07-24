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

CELL = 4.0
# region of interest
X0, X1, Z0, Z1 = 232, 238, -1143, -1136


def main():
    gr = Path(_cfg.find_game_path(None))
    comp = RFL.compose(gr)
    final = comp["final_blocks"]
    placed = comp["placed_R"]
    tris = []
    for blk, bm in final.items():
        ox, oz = X.block_world_origin(blk[0], blk[1])
        for tri in bm.tris:
            p3 = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            cx = sum(p[0] for p in p3) / 3; cz = sum(p[2] for p in p3) / 3
            if X0 <= cx <= X1 and Z0 <= cz <= Z1:
                idall = int(round(bm.tangents[tri[0]][0]))
                topo = X.decode_id(idall)["topograph"]
                cell = (math.floor(cx / CELL), math.floor(cz / CELL))
                tris.append((p3, topo, cell in placed))
    print(f"tris in ROI: {len(tris)}")
    for (p3, topo, isplaced) in sorted(tris, key=lambda t: (t[0][0][0], t[0][0][2])):
        ys = [round(p[1], 2) for p in p3]
        pts = [(round(p[0], 2), round(p[2], 2)) for p in p3]
        print(f"   topo={topo} placed={isplaced} y={ys} xz={pts}")


if __name__ == "__main__":
    main()
