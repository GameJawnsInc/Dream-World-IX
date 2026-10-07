"""Prediction numbers for the two proposed in-game probes (NOT run in-game -- offline only).

P1 beach seam (7,17), centre (480,-1120), r16, +3 (and the +1 control): every Terrain|Beach1 probe crossing
   before/after with heights -- which steps become one-way walls and where (world x,z).
P2 object origin-shift (19,14), centre (1274.219,-954.016), r8, +1: the terrain->Object crossings that turn
   illegal because the raised start height lets an earlier-in-buffer topo-59 Object tri win the walk ray.
Writes out/probe_detail.json.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/probe_detail.py
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402
import tear_sweep as T                                 # noqa: E402
from ff9mapkit.world import placement as P             # noqa: E402
from ff9mapkit.world.mesh import _falloff              # noqa: E402

M = S.load_disc(1)
blocks = T.build_world(M)


def run(blk, centre, R, A, partner):
    ter = blocks[blk]["terrain"]
    ox, oz = blk[0] * 64, -blk[1] * 64
    tv = [(v[0], v[1] + A * _falloff(math.hypot(v[0] + ox - centre[0], v[2] + oz - centre[1]) / R), v[2])
          for v in ter.lv]
    ml0 = T.meshlist_for(blocks, blk)
    ml1 = T.meshlist_for(blocks, blk, tv)
    idx = P.build_meshlist_index(ml0)
    tri_at = defaultdict(list)
    for p in ("terrain", partner):
        m = blocks[blk][p]
        for t in range(m.ntri):
            for k in range(3):
                tri_at[m.lv[m.fi[3 * t + k]]].append((p, t))
    out = []
    for lp, lst in tri_at.items():
        ps = {p for p, _ in lst}
        if ps != {"terrain", partner}:
            continue
        f = A * _falloff(math.hypot(lp[0] + ox - centre[0], lp[2] + oz - centre[1]) / R)
        if abs(f) <= S.TOL:
            continue
        pr = []
        for (p, t) in lst:
            m = blocks[blk][p]
            cs = [m.lv[m.fi[3 * t + k]] for k in range(3)]
            gx, gz = sum(q[0] for q in cs) / 3 - lp[0], sum(q[2] for q in cs) / 3 - lp[2]
            L = math.hypot(gx, gz)
            if L > 1e-6:
                pr.append((p, (lp[0] + T.PROBE * gx / L, lp[2] + T.PROBE * gz / L)))
        for (pa, a) in pr:
            for (pb, b) in pr:
                if pa == pb:
                    continue
                before = T.crossing(ml0, idx, a, ml0, idx, b)
                after = T.crossing(ml1, idx, a, ml1, idx, b)
                if before[0] and after[0] is False:
                    ga = T.hit_tri(ml1, idx, a[0], a[1], 0.0, sky=True)
                    gb = T.hit_tri(ml1, idx, b[0], b[1], 0.0, sky=True)
                    out.append({"from": pa, "to": pb, "world_from": [round(a[0] + ox, 2), round(a[1] + oz, 2)],
                                "world_to": [round(b[0] + ox, 2), round(b[1] + oz, 2)],
                                "seam_dy": round(f, 3), "ground_from_after": round(ga[1], 3),
                                "ground_to_after_sky": round(gb[1], 3), "topo_to_after_sky": S.topo(gb[2]),
                                "reason": after[1]})
    return out


res = {}
for A in (1.0, 3.0):
    r = run((7, 17), (480.0, -1120.0), 16.0, A, "beach1")
    res[f"P1_A{A:g}"] = r
    print(f"P1 (7,17) +{A:g} r16: {len(r)} introduced walls; e.g. {r[:2]}")
r = run((19, 14), (1274.219, -954.016), 8.0, 1.0, "object")
res["P2"] = r
print(f"P2 (19,14) +1 r8: {len(r)} introduced walls; e.g. {r[:3]}")
p = S.save_json("probe_detail.json", res)
print("->", p)
