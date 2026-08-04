"""What does a STOCK shore look like at the playtest-8 vantage class? READ-ONLY.

Renders the donor block (5,14)'s own coast (disc 1, stock bytes) at a graze
and an owner_close-class camera, auto-aimed at the donor window's chord.
The lawful reference for the waterline band: if stock's own wall-meets-water
shows the same bright rocky band, the band class is lawful and the residual
defect is elsewhere (joints/smears); if stock reads fine-textured, the class
itself is the defect. Output: out/render_gate/stock_graze.png / stock_close.png.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_gate as RG                                    # noqa: E402
import vcorner_transplant as VT                             # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402

BLK = (5, 14)
NEIGH = [(4, 14), (6, 14), (5, 13), (5, 15), (4, 13), (6, 13), (4, 15), (6, 15)]


def stock_batches(cells):
    batches = []
    for (bx, by) in cells:
        ox, oz = X.block_world_origin(bx, by)
        for part in RG.PARTS:
            try:
                bm = X.read_block(bx, by, disc=1, part=part.lower())
            except Exception:
                continue
            if bm is None:
                continue
            pos = np.asarray(bm.chan_arrays[X.CH_POS], dtype=np.float64)
            uvc = bm.chan_arrays.get(X.CH_UV)
            uv = np.asarray(uvc, dtype=np.float64)[:, :2] if uvc is not None \
                else np.zeros((len(pos), 2))
            w = pos.copy()
            w[:, 0] += ox
            w[:, 2] += oz
            batches.append((part, w, uv, np.asarray(bm.tris, dtype=np.int64)))
    return batches


def main():
    tris = VT.block_tris(*BLK)
    chains, _landcen, _yof = VT.boundary_chains(tris)
    chain = chains[VT.PICK["chain"]]
    i0, i1 = VT.PICK["i0"], VT.PICK["i1"]
    a, b = chain[i0], chain[i1]                             # (x,z) keys
    mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
    # land = average walkable centroid; eye goes the OPPOSITE side (the sea)
    wc = np.mean([np.mean([p for p in t[0]], axis=0)
                  for t in tris if t[3] in VT.W.WALK_OK], axis=0)
    away = np.array([mid[0] - wc[0], mid[1] - wc[2]])
    away /= np.linalg.norm(away)
    print(f"window chord mid=({mid[0]:.1f},{mid[1]:.1f})  seaward=({away[0]:+.2f},{away[1]:+.2f})")

    views = {
        "stock_graze": dict(kind="persp",
                            eye=(mid[0] + 18 * away[0], 3.0, mid[1] + 18 * away[1]),
                            at=(mid[0], 1.0, mid[1]), fov=45.0, reach=60.0),
        "stock_close": dict(kind="persp",
                            eye=(mid[0] - 8 * away[0] + 6 * away[1], 21.0,
                                 mid[1] - 8 * away[1] - 6 * away[0]),
                            at=(mid[0], 0.5, mid[1]), fov=50.0, reach=45.0),
    }
    batches = stock_batches([BLK] + NEIGH)
    print(f"{len(batches)} stock part batches")
    for name, v in views.items():
        RG.raster(v, batches, name)


if __name__ == "__main__":
    main()
