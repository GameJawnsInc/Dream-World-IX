"""Offline eye: map the coastline around the bench island (block (7,17)) from the STOCK terrain
mesh and print a proper boat spot -- a sea point just off the sand nearest the teleport dock.

Classification per sample (terrain sky-cast, world frame): land = ground_y > 0.3; sand = the
beach topographs; sea = ground_y <= 0 (the underwater shelf).
"""
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit.world.extract import read_block, block_world_origin      # noqa: E402
from ff9mapkit.world.placement import place                             # noqa: E402

BEACH_TOPOS = {30, 32, 34, 35}
DOCK_HINT = (480.0, -1120.0)

_blocks = {}
for bx, by in [(7, 16), (7, 17), (7, 18), (6, 17), (8, 17), (6, 16), (8, 16), (6, 18), (8, 18)]:
    try:
        _blocks[(bx, by)] = read_block(bx, by, part="terrain")
    except Exception as ex:
        print(f"block ({bx},{by}): {ex}")


def place_world(wx: float, wz: float):
    """place() in the owning block's LOCAL frame (BlockMesh verts are block-local, read-only)."""
    bx, by = int(wx // 64), int(-wz // 64)
    bm = _blocks.get((bx, by))
    if bm is None:
        return 0.0, "MISS", 0, None
    ox, oz = block_world_origin(bx, by)
    return place([(f"T{bx}_{by}", bm)], wx - ox, wz - oz)

sand, sea = [], []
STEP = 4
for xi in range(int(6 * 64), int(9 * 64) + 1, STEP):
    for zi in range(int(-18 * 64) - 64, int(-16 * 64) + 1, STEP):
        gy, name, idall, topo = place_world(float(xi), float(zi))
        if name == "MISS":
            continue
        if topo in BEACH_TOPOS and gy > 0.05:
            sand.append((xi, zi, gy, topo))
        elif gy <= 0.0:
            sea.append((xi, zi, gy))

print(f"sand samples: {len(sand)}   sea samples: {len(sea)}")
if not sand:
    print("no sand found -- dumping topo census near the hint instead:")
    from collections import Counter
    c = Counter()
    for xi in range(440, 521, STEP):
        for zi in range(-1160, -1079, STEP):
            gy, name, idall, topo = place_world(float(xi), float(zi))
            c[(name, topo, round(gy) if gy else 0)] += 1
    for k, n in sorted(c.items(), key=lambda kv: -kv[1])[:20]:
        print("  ", k, n)
    sys.exit(0)

# the sand point nearest the dock hint
sx, sz, sgy, stopo = min(sand, key=lambda p: (p[0] - DOCK_HINT[0]) ** 2 + (p[1] - DOCK_HINT[1]) ** 2)
print(f"nearest sand to {DOCK_HINT}: ({sx}, {sz})  y={sgy:.2f} topo={stopo}")

# the sea point nearest that sand with depth (a boat wants real water, not the swash film)
cands = [(x, z, gy) for x, z, gy in sea if gy < -0.5]
bx_, bz_, bgy = min(cands, key=lambda p: (p[0] - sx) ** 2 + (p[1] - sz) ** 2)
d = math.dist((bx_, bz_), (sx, sz))
print(f"nearest deep-ish sea to that sand: ({bx_}, {bz_})  y={bgy:.2f}  ({d:.0f}u off the sand)")

# push ~14u further out along the sand->sea direction so the hull isn't beached
vx, vz = bx_ - sx, bz_ - sz
L = math.hypot(vx, vz) or 1.0
ox_, oz_ = bx_ + vx / L * 14, bz_ + vz / L * 14
gy2, name2, idall2, topo2 = place_world(ox_, oz_)
print(f"BOAT_SPAWN suggestion: ({ox_:.0f}, {oz_:.0f})  ground there: {name2} y={gy2:.2f} topo={topo2}")
print(f"DOCK suggestion (the sand itself): ({sx}, {sz})")
