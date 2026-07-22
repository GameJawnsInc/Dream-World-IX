"""Round 2: dense scan of block (7,17) -- map the sand (topo 31) and pick the boat spot."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit.world.extract import read_block, block_world_origin      # noqa: E402
from ff9mapkit.world.placement import place                             # noqa: E402

bm = read_block(7, 17, part="terrain")
ox, oz = block_world_origin(7, 17)

sand, land = [], []
STEP = 2
for xi in range(0, 65, STEP):
    for zi in range(-64, 1, STEP):
        gy, name, idall, topo = place([("T", bm)], float(xi), float(zi))
        if name == "MISS":
            continue
        wx, wz = xi + ox, zi + oz
        if topo == 31:
            sand.append((wx, wz, gy))
        elif gy > 0.3:
            land.append((wx, wz, gy, topo))

print(f"sand(topo31): {len(sand)}   other land: {len(land)}")
if sand:
    xs = sorted(p[0] for p in sand)
    zs = sorted(p[1] for p in sand)
    print(f"sand x range {xs[0]}..{xs[-1]}   z range {zs[0]}..{zs[-1]}")
    south = min(sand, key=lambda p: p[1])
    north = max(sand, key=lambda p: p[1])
    east = max(sand, key=lambda p: p[0])
    west = min(sand, key=lambda p: p[0])
    for tagp, p in (("south", south), ("north", north), ("east", east), ("west", west)):
        print(f"  {tagp}most sand: ({p[0]}, {p[1]}) y={p[2]:.2f}")
if land:
    cx = sum(p[0] for p in land) / len(land)
    cz = sum(p[1] for p in land) / len(land)
    print(f"land centroid: ({cx:.0f}, {cz:.0f})   land z range "
          f"{min(p[1] for p in land)}..{max(p[1] for p in land)}")
