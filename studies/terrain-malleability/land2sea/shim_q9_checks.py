"""Q3/Q2 closing checks on an edge-avoiding 0.25u lattice: Sea4 x Terrain plan overlap per disc (z-fight risk), the
sea-topo Terrain tris x Sea4 overlap, where the NEW disc-4 topo-59 Terrain tris sit (which disc-1 ground was under
them), and the area of disc-4 Terrain above y=0.05 over the old main-island footprint.
Run: cd C:\\gd\\Dream-World-IX\\ff9mapkit ; py <this>   -> out/q9_checks.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np                                         # noqa: E402
import shim_lib as S                                       # noqa: E402

PITCH = 0.25
px, pz = S.grid(PITCH, 0.37, 0.61)
SA = PITCH * PITCH
res = {}
tot = Counter()
for (bx, by) in S.SHIM:
    part1, ids1, y1, _ = S.ground_raster(1, bx, by, px, pz)
    land1 = np.isin(part1, list(S.LAND_PARTS))
    for d in (1, 4):
        tr = S.tri_arrays(S.read(bx, by, d, "terrain"))
        s4 = S.tri_arrays(S.read(bx, by, d, "sea4"))
        ct, tymin, tymax, tf = S.cover(tr["V"], px, pz)
        cs, *_ = S.cover(s4["V"], px, pz)
        both = (ct > 0) & (cs > 0)
        tot[f"d{d}_sea4&terrain_u2"] += both.sum() * SA
        tot[f"d{d}_sea4_multi_u2"] += (cs > 1).sum() * SA
        tot[f"d{d}_terrain_multi_u2"] += (ct > 1).sum() * SA
        if d == 4:
            seaT = np.isin(S.topo(tr["ids"]), [53, 54, 55, 56, 57])
            hit_seaT = (tf >= 0) & seaT[np.maximum(tf, 0)]
            tot["d4_seaTopoTerrain&sea4_u2"] += (hit_seaT & (cs > 0)).sum() * SA
            tot["d4_seaTopoTerrain_u2"] += hit_seaT.sum() * SA
            tot["d4_terrain_above0.05_over_d1land_u2"] += ((ct > 0) & (tymax > 0.05) & land1).sum() * SA
            # new topo-59 terrain tris: what was the disc-1 ground under them
            t1 = S.tri_arrays(S.read(bx, by, 1, "terrain"))
            k1 = Counter(S.tri_key(v) for v in t1["V"])
            new = np.array([k1[S.tri_key(v)] == 0 for v in tr["V"]]) & ~seaT
            hit_new = (tf >= 0) & new[np.maximum(tf, 0)]
            tot["d4_new_topo59_terrain_u2"] += hit_new.sum() * SA
            for k, v in Counter(part1[hit_new].tolist()).items():
                tot[f"...d1_ground_under_new_topo59:{k}_u2"] += v * SA
            tot["...their_ymax>0.05_u2"] += (hit_new & (tymax > 0.05)).sum() * SA
res = {k: round(float(v), 3) for k, v in sorted(tot.items())}
(S.OUT / "q9_checks.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
