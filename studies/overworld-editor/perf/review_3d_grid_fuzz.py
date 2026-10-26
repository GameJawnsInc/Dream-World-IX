"""Review probe (3D-view slice): is ground_y with the ground grid (26b7eb7a) exactly the whole-scan ground_y?

Random float32 scenes (tris across 16u cell lines, negative coordinates, vertices ON cell lines, tiny and slanted
tris, down-facing lids, an empty part), seam copies included, probed at random points, at every vertex, on the
cell lines and at their crossings. Pure numpy: no Qt view, no install.
Run: py studies/overworld-editor/perf/review_3d_grid_fuzz.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(WT / "ff9mapkit"), ff9mapkit.__file__

import numpy as np  # noqa: E402
from ff9mapkit.workspace import worldview3d as V  # noqa: E402

rng = np.random.default_rng(7)
bad = total = 0
for trial in range(40):
    batches = []
    for part in ("Terrain", "Object", "Sea4", "Beach1"):
        n = int(rng.integers(0, 120))
        if trial % 7 == 0 and part == "Beach1":
            n = 0
        base = rng.uniform(-200, 1700, size=(n, 1, 3))
        base[:, :, 0] = np.round(base[:, :, 0] / 16.0) * 16.0 * (rng.random((n, 1)) < 0.4) + \
            base[:, :, 0] * (rng.random((n, 1)) >= 0.4)            # many vertices exactly on a cell line
        span = rng.choice([0.01, 3.0, 16.0, 40.0], size=(n, 1, 1))
        v = (base + rng.uniform(-1, 1, size=(n, 3, 3)) * span).astype(np.float32).reshape(-1, 3)
        v[:, 1] = rng.uniform(-5, 30, size=len(v)).astype(np.float32)
        t = np.arange(len(v)).reshape(-1, 3)
        flip = rng.random(len(t)) < 0.5
        t[flip] = t[flip][:, [0, 2, 1]]                                # half face down, half up
        batches.append((part, v.astype(np.float64), np.zeros((len(v), 2)), t))
    scene = V.seam_copies(batches)
    plain, gridded = V.pack(scene), V.pack(scene)
    gridded.build_ground_grid()
    pts = [tuple(p) for p in rng.uniform(-300, 1850, size=(300, 2))]
    for part in gridded.arrays:                                        # every vertex
        a = gridded.arrays[part][:, :3].astype(np.float64)
        pts += [(float(x), float(z)) for x, _y, z in a[:: max(1, len(a) // 200)]]
    pts += [(16.0 * i, 16.0 * j) for i in range(-14, 110, 3) for j in range(-14, 110, 3)]
    pts += [(16.0 * i, float(z)) for i in range(-14, 110, 5) for z in rng.uniform(-300, 1850, 4)]
    pts += [(-0.0, -0.0), (0.0, -16.0), (-16.0, 0.0), (1536.0, -0.0)]
    for x, z in pts:
        total += 1
        g, p = V.ground_y(gridded, x, z), V.ground_y(plain, x, z)
        if g != p:
            bad += 1
            if bad <= 5:
                print("DIFF", trial, x, z, g, p)
print(f"{total} probes, {bad} differ")
