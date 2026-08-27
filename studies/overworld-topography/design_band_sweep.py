"""ANGLE A design probe -- free-radius sweep restricted to the SOUTHERN ARCHIPELAGO BAND.

Read-only. Reuses canvas_census's forbidden set (out/world-design/_forbidden_blocks.json)
and the same nearest-forbidden metric as free_space_sweep, but sweeps at a finer step and
reports, per named GAP between the accepted clusters, the best mintable centre + r_max.
"""
import json
import math
from pathlib import Path

import numpy as np

BLOCK = 64.0
WORLD_W = 24 * BLOCK
WORLD_H = 20 * BLOCK

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "world-design"

fb_raw = json.loads((OUT / "_forbidden_blocks.json").read_text(encoding="utf-8"))
forbidden = set(map(tuple, fb_raw["stock_occ"])) | set(map(tuple, fb_raw["live"])) | set(
    map(tuple, fb_raw["named"]))
fb = sorted(forbidden)


def nearest_forbidden(cx, cz):
    best = 1e9
    for (bx, by) in fb:
        x0, x1 = BLOCK * bx, BLOCK * (bx + 1)
        z1, z0 = -BLOCK * by, -BLOCK * (by + 1)
        dx = 0.0 if x0 <= cx <= x1 else min(
            abs(cx - x0), abs(cx - x1),
            abs(cx - x0 + WORLD_W), abs(cx - x1 + WORLD_W),
            abs(cx - x0 - WORLD_W), abs(cx - x1 - WORLD_W))
        dz = 0.0 if z0 <= cz <= z1 else min(abs(cz - z0), abs(cz - z1))
        d = math.hypot(dx, dz)
        best = min(best, d)
        if best <= 0.0:
            return 0.0
    return best


def rmax(cx, cz):
    offseam = min(cx, WORLD_W - cx)
    edge = min(abs(cz), abs(-WORLD_H - cz))
    return min(nearest_forbidden(cx, cz), offseam, edge)


# named gaps: (label, bx range inclusive, by range inclusive)
GAPS = [
    ("G1 strait: junction island (bx0-4) <-> archipelago remnant (bx6-8)", 5, 5, 15, 19),
    ("G2 shoal: remnant (bx6-8) <-> retile island (bx11-12)", 9, 10, 15, 19),
    ("G3 open reach: retile island (bx11-12) <-> mountain bench (bx18-20)", 13, 17, 15, 19),
    ("G4 east flank: east of mountain bench", 21, 23, 12, 19),
    ("G5 north shelf above the band", 5, 17, 14, 16),
]

report = {}
for label, bx0, bx1, by0, by1 in GAPS:
    best = []
    for cx in np.arange(BLOCK * bx0, BLOCK * (bx1 + 1) + 0.1, 4.0):
        for cz in np.arange(-BLOCK * by0, -BLOCK * (by1 + 1) - 0.1, -4.0):
            r = rmax(float(cx), float(cz))
            if r >= 16.0:
                best.append((round(r, 1), float(cx), float(cz)))
    best.sort(reverse=True)
    picked = []
    for r, cx, cz in best:
        if all(math.hypot(cx - p[1], cz - p[2]) > 40.0 for p in picked):
            picked.append((r, cx, cz))
        if len(picked) >= 6:
            break
    report[label] = [dict(r_max=r, cx=cx, cz=cz, block=(int(cx // BLOCK), int(-cz // BLOCK)))
                     for r, cx, cz in picked]
    print(f"\n=== {label}")
    for d in report[label]:
        print(f"   r_max={d['r_max']:6.1f}  centre=({d['cx']:.0f},{d['cz']:.0f})  block={d['block']}")

(OUT / "design_band_sweep.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("\nwrote", OUT / "design_band_sweep.json")
