"""FOREST UV LANGUAGE STUDY -- how real canopy UVs actually work:
(1) UV continuity at weld positions (continuous field vs per-tri tiles),
(2) plan-affine fit (u,v) ~ A.(x,z)+b -- residuals + scale,
(3) the atlas region + whether WALL faces share the same field,
(4) rim behavior (canopy vs grass UVs at shared positions)."""
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X

for (bx, by) in ((19, 13), (17, 14), (15, 15)):
    bm = X.read_block(bx, by)
    v = np.asarray(bm.verts, dtype=np.float64)
    uv = np.asarray(bm.uvs, dtype=np.float64)
    tan = bm.tangents
    topo = [X.decode_id(int(tan[t[0]][0]))["topograph"] for t in bm.tris]
    key = lambda i: (round(v[i][0], 3), round(v[i][1], 3), round(v[i][2], 3))

    # collect forest verts (tri-slot copies) per weld position
    per_pos = defaultdict(list)          # pos -> [(vert index, tri)]
    for t, tri in enumerate(bm.tris):
        if topo[t] == 37:
            for i in tri:
                per_pos[key(i)].append((i, t))
    # (1) UV continuity: distinct UVs per position among forest copies
    multi = [len({(round(uv[i][0], 4), round(uv[i][1], 4)) for i, _ in lst}) for lst in per_pos.values()]
    cont = sum(1 for m in multi if m == 1) / len(multi)
    print(f"\nblock ({bx},{by}): forest weld positions {len(per_pos)}, "
          f"single-UV fraction {cont:.2f} (1.0 = fully continuous field)")

    # (2) plan-affine fit on ALL forest verts
    P = np.array([[v[i][0], v[i][2], 1.0] for lst in per_pos.values() for i, _ in lst])
    Q = np.array([[uv[i][0], uv[i][1]] for lst in per_pos.values() for i, _ in lst])
    coef, res, *_ = np.linalg.lstsq(P, Q, rcond=None)
    pred = P @ coef
    err = np.abs(pred - Q)
    print(f"  plan-affine fit: max err ({err[:,0].max():.4f},{err[:,1].max():.4f}) "
          f"med ({np.median(err[:,0]):.4f},{np.median(err[:,1]):.4f})  "
          f"du/dx {coef[0,0]:.5f} du/dz {coef[1,0]:.5f} dv/dx {coef[0,1]:.5f} dv/dz {coef[1,1]:.5f}")
    wpt_u = 1.0 / (abs(coef[0, 0]) + 1e-9)                # world units per full atlas U
    print(f"  scale: {abs(coef[0,0])*1024:.1f} texels/u in U, {abs(coef[1,1])*1024:.1f} texels/u in V "
          f"(if axis-aligned)")

    # (3) atlas region + wall-vs-top continuity
    print(f"  UV bbox: u {Q[:,0].min():.3f}..{Q[:,0].max():.3f}  v {Q[:,1].min():.3f}..{Q[:,1].max():.3f}")
    # wall faces = steep tris; are their verts' UVs the same field? (they're included above --
    # check their residuals separately)
    steep_idx, flat_idx = [], []
    row = 0
    for lst in per_pos.values():
        for i, t in lst:
            tri = bm.tris[t]
            a, b, c = v[tri[0]], v[tri[1]], v[tri[2]]
            n = np.cross(b - a, c - a)
            up = n[1] / (np.linalg.norm(n) + 1e-12)
            (steep_idx if up < 0.5 else flat_idx).append(row)
            row += 1
    if steep_idx and flat_idx:
        print(f"  fit err on STEEP wall verts: med u {np.median(err[steep_idx,0]):.4f} "
              f"v {np.median(err[steep_idx,1]):.4f}   on TOP verts: u {np.median(err[flat_idx,0]):.4f} "
              f"v {np.median(err[flat_idx,1]):.4f}")

    # (4) rim: at positions shared with grass, canopy copy UV vs grass copy UV
    gpos = defaultdict(list)
    for t, tri in enumerate(bm.tris):
        if topo[t] in (0, 1, 2):
            for i in tri:
                gpos[key(i)].append(i)
    shared = [p for p in per_pos if p in gpos]
    if shared:
        same = 0
        for p in shared[:60]:
            fu = {(round(uv[i][0], 3), round(uv[i][1], 3)) for i, _ in per_pos[p]}
            gu = {(round(uv[i][0], 3), round(uv[i][1], 3)) for i in gpos[p]}
            if fu & gu:
                same += 1
        print(f"  rim: {len(shared)} shared positions; canopy-UV==grass-UV at {same}/{min(len(shared),60)}")
