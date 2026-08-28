"""FINE footprint verification for the continent candidates.

The block-granular 9x9 sweep in continent_site_scan.py is a PRE-FILTER, not a gate: it missed a
0.6u sliver of the seed-30 outline poking into stock block (4,3), which island.landmass()'s
OPEN-OCEAN TARGET LAW would have refused at deploy. This re-tests every shape-gate survivor with
1280 interpolated rays x 1u marching (sub-unit accurate on a star-convex outline) and keeps only
candidates whose ENTIRE filled footprint plus a safety margin lands on free ocean.
Read-only."""
from __future__ import annotations
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "ff9mapkit")))
import continent_site_scan as C  # noqa: E402
from ff9mapkit.world import mesh as M  # noqa: E402

OUT = C.OUT
BLOCK = 64.0
NRAY = 1280
MARGIN = 1.5          # push the outline out this far before testing (deploy-refusal safety)


def fine_blocks(cx, cz, R, lobes, seed, margin=MARGIN):
    radii, _, _ = C.PROF[(lobes, seed)]
    n = len(radii)
    blocks = set()
    for k in range(NRAY):
        th = 2 * math.pi * k / NRAY
        f = th / (2 * math.pi) * n
        i = int(f) % n
        t = f - int(f)
        r = R * (radii[i] * (1 - t) + radii[(i + 1) % n] * t) + margin
        d = 0.0
        ct, st = math.cos(th), math.sin(th)
        while d <= r:
            x, z = cx + d * ct, cz + d * st
            blocks.add((int(math.floor(x / BLOCK)) % 24, int(math.floor(-z / BLOCK))))
            d += 1.0
        x, z = cx + r * ct, cz + r * st
        # bx wraps mod 24 (the seam-wrap fix, playtest-proven 2026-08-27); by stays raw so the
        # z-range check below still refuses genuine off-grid rows.
        blocks.add((int(math.floor(x / BLOCK)) % 24, int(math.floor(-z / BLOCK))))
    return blocks


rank = json.load(open(os.path.join(OUT, "continent_ranked.json")))
print(f"{rank['n']} shape-gate survivors; fine-verifying the ranked list\n")
ok = []
for h in rank["top"]:
    cx, cz = h["center"]
    blks = fine_blocks(cx, cz, h["radius"], h["lobes"], h["seed"])
    bad = sorted(b for b in blks if b in C.FORBIDDEN or not (0 <= b[1] < 20))
    status = "CLEAN" if not bad else f"REFUSED {bad}"
    print(f"area={h['area_u2']:6d} R={int(h['radius']):3d} lobes={h['lobes']} seed={h['seed']:3d} "
          f"c={h['center']} blocks={len(blks):3d} medturn={h['shape']['med_turn']:5.2f}  {status}")
    if not bad:
        h["fine_blocks"] = sorted(blks)
        h["n_fine_blocks"] = len(blks)
        ok.append(h)

print(f"\n{len(ok)} of {len(rank['top'])} ranked candidates survive the fine footprint test")
if ok:
    b = ok[0]
    print(f"\nWINNER: --center {b['center'][0]:.0f},{b['center'][1]:.0f} --radius {int(b['radius'])} "
          f"--lobes {b['lobes']} --seed {b['seed']}")
    print(f"  area {b['area_u2']}u2 | {b['n_fine_blocks']} blocks | span {b['span_x']}x{b['span_z']} "
          f"| rmin/rmax {b['rmin_u']}/{b['rmax_u']} | med_turn {b['shape']['med_turn']:.2f}")
    print(f"  blocks: {b['fine_blocks']}")
with open(os.path.join(OUT, "continent_verified.json"), "w", encoding="utf-8") as f:
    json.dump({"n_clean": len(ok), "clean": ok}, f, indent=1)
print("wrote", os.path.join(OUT, "continent_verified.json"))
