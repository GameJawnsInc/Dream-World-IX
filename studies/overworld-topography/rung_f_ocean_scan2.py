"""RUNG F ocean scan 2 -- the GROUND-TRUTH non-wrapping open-ocean Rmax (attempt-1 blocker check).

stage0's OPEN-OCEAN gate refuted design2_round3's PRIMARY south site (block (4,15) has stock terrain,
(3,15) has coastal sea overrides). This scan finds, over the WHOLE 24x20 block world, the largest
NON-WRAPPING open-ocean circle: center on the 4u lattice, whose disc [cx-R,cx+R] stays in [0,1536)
(no x=0 seam wrap) and [cz-R,cz]... within [0,-1280], and every covered block is TRUE PREFAB OCEAN (no
per-block Terrain/sea mesh assets AND terrain-height <=0.6 land test AND not a deployed override block).
READ-ONLY. Writes out/rung_f/ocean_scan2.json.
"""
import sys, math, io, contextlib, json
from pathlib import Path
sys.path.insert(0, '../../ff9mapkit'); sys.path.insert(0, '.')
from ff9mapkit.world import extract as X
from ff9mapkit.world import island as ISL
from ff9mapkit import config as _cfg

HERE = Path(__file__).resolve().parent
BLOCK = 64.0
game = Path(_cfg.find_game_path(None))

# a block is OCCUPIED if it has ANY per-block real parts (terrain OR coastal sea overrides) OR is a
# deployed override block. True open ocean = _real_block_parts returns {} (uses the shared SeaBlockPrefab).
deployed = {(6,18),(6,19),(7,18),(7,19),(8,19),(9,9),(10,8),(10,9),(10,10),(11,8),(11,9),(11,18),
            (11,19),(12,18),(12,19),(18,17),(18,18),(18,19),(19,17),(19,18),(19,19),(20,17),(20,18),(20,19)}
occ = set(deployed)
for by in range(20):
    for bx in range(24):
        p = ISL._real_block_parts((bx, by), disc=1, lod="0_1", game=game)
        if p:
            occ.add((bx, by))
print(f"occupied (has per-block parts or deployed): {len(occ)} / 480 blocks; open ocean = {480-len(occ)}")


def covered_blocks(cx, cz, r):
    b = set()
    steps = int(r // 4) + 2
    for i in range(-steps, steps + 1):
        for j in range(-steps, steps + 1):
            px, pz = cx + 4 * i, cz + 4 * j
            if (px - cx) ** 2 + (pz - cz) ** 2 <= r * r:
                bx = int(px // BLOCK); by = int((-pz) // BLOCK)
                b.add((bx, by))
    return b


def ok_site(cx, cz, r):
    if cx - r < 0 or cx + r > 1536:
        return False, "x-wrap"
    if cz + r > 0 or cz - r < -1280:
        return False, "z-edge"
    for blk in covered_blocks(cx, cz, r):
        if not (0 <= blk[0] <= 23 and 0 <= blk[1] <= 19):
            return False, f"offgrid{blk}"
        if blk in occ:
            return False, f"occ{blk}"
    return True, "ok"


# coarse then fine: find the max r (in 2u steps) at each 8u-lattice center, keep the best few clusters.
best = []
for gz in range(8, 1280, 8):
    cz = -float(gz)
    for gx in range(8, 1536, 8):
        cx = float(gx)
        # quick reject: block must be open
        if (int(cx // 64), int((-cz) // 64)) in occ:
            continue
        r = 40.0
        last = 0.0
        while r <= 200:
            ok, _ = ok_site(cx, cz, r)
            if ok:
                last = r; r += 4
            else:
                break
        if last >= 96:
            best.append((last, cx, cz))
best.sort(reverse=True)
clusters = []
for r, cx, cz in best:
    if any(abs(cx - sx) < 80 and abs(cz - sz) < 80 for _, sx, sz in clusters):
        continue
    clusters.append((r, cx, cz))
    if len(clusters) >= 12:
        break

print("\nTOP non-wrapping open-ocean sites (Rmax, center, block):")
rows = []
for r, cx, cz in clusters:
    blk = (int(cx // 64), int((-cz) // 64))
    print(f"  Rmax={r:.0f}u center({cx:.0f},{cz:.0f}) block{blk}")
    rows.append(dict(rmax=r, center=[cx, cz], block=list(blk)))
out = dict(n_occupied=len(occ), n_open=480 - len(occ), best_sites=rows,
           note="Rmax = largest NON-WRAPPING circle whose covered blocks are ALL true prefab ocean "
                "(no per-block parts, not deployed). The R1 need is ~121-132u (MEC 71.4 + realized 50).")
(HERE / "out" / "rung_f" / "ocean_scan2.json").write_text(json.dumps(out, indent=1))
print("wrote out/rung_f/ocean_scan2.json")
