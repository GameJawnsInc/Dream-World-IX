"""VERIFIER (adversarial) -- what ARE the Object-seam "walls" of tear_sweep.py (S6) and the origin-shift class (S7)?

tear_sweep.py probes a crossing 0.4u into every tri incident on a torn weld vertex, along the tri's centroid
direction in XZ. For a VERTICAL tri (zero XZ area -- a wall/curtain face) that probe sits ON the face's base
line, not inside any part of that tri, so the "to Object" step may in fact ground on Terrain (or on an
overhanging sheet). This re-runs the sweep's object branch (same plan, same instrument functions imported from
tear_sweep.py) and, for every introduced wall, records:
  * the target probe's tri: XZ area and |normal.y| (vertical <=> XZ area < 1e-6);
  * which mesh/topograph the STOCK step grounded on (the "legal" before state);
  * the after-edit reason.
Writes out/verify_object_walls.json.   Run: py <this file>   (~1 min)
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402
import tear_sweep as T                                 # noqa: E402
from ff9mapkit.world import placement as P             # noqa: E402
from ff9mapkit.world.mesh import _falloff              # noqa: E402

AMOUNTS = (1.0, 3.0, -3.0)
RADII = (8.0, 16.0, 24.0)


def xz_area(cs):
    return abs((cs[1][0] - cs[0][0]) * (cs[2][2] - cs[0][2]) - (cs[2][0] - cs[0][0]) * (cs[1][2] - cs[0][2])) / 2


def main():
    M = S.load_disc(1)
    blocks = T.build_world(M)
    owners = defaultdict(set)
    for k, m in M.items():
        for p in m.wv:
            owners[S.wrap_key(p)].add(k)
    welds = {}
    tri_at = defaultdict(lambda: defaultdict(list))
    for (x, y), parts in blocks.items():
        for p, m in parts.items():
            for t in range(m.ntri):
                for k in range(3):
                    tri_at[(x, y)][m.lv[m.fi[3 * t + k]]].append((p, t))
    for (x, y), parts in blocks.items():
        if "terrain" not in parts:
            continue
        w = {}
        for lp, wp in zip(parts["terrain"].lv, parts["terrain"].wv):
            if lp in w:
                continue
            o = owners[S.wrap_key(wp)] - {(x, y, "terrain")}
            if o:
                w[lp] = sorted(o)
        welds[(x, y)] = w
    obj_blocks = sorted({(x, y) for (x, y, p) in M if p == "object"})
    plan = []
    for b in obj_blocks:
        cells = defaultdict(list)
        for lp, others in welds[b].items():
            if any(o[2] == "object" for o in others):
                wx, wz = lp[0] + b[0] * 64, lp[2] - b[1] * 64
                cells[(math.floor(wx / 16), math.floor(wz / 16))].append((wx, wz))
        for c, pts in sorted(cells.items()):
            mx = sum(p[0] for p in pts) / len(pts)
            mz = sum(p[1] for p in pts) / len(pts)
            plan.append((b, min(pts, key=lambda p: (p[0] - mx) ** 2 + (p[1] - mz) ** 2)))
    base_ml, base_idx = {}, {}
    stats = Counter()
    examples = []
    for (b0, (cx, cz)) in plan:
        for R in RADII:
            bx0, bx1 = math.floor((cx - R) / 64), math.floor((cx + R) / 64)
            by0, by1 = math.floor(-(cz + R) / 64), math.floor(-(cz - R) / 64)
            touched = [(bx, by) for bx in range(bx0, bx1 + 1) for by in range(by0, by1 + 1)
                       if 0 <= bx < 24 and 0 <= by < 20 and (bx, by) in welds]
            for A in AMOUNTS:
                for blk in touched:
                    ox, oz = blk[0] * 64, -blk[1] * 64
                    ter = blocks[blk]["terrain"]
                    wt = {lp: _falloff(math.hypot(lp[0] + ox - cx, lp[2] + oz - cz) / R, "smooth") for lp in set(ter.lv)}
                    mla = None
                    for lp, others in welds[blk].items():
                        f = A * wt.get(lp, 0.0)
                        if abs(f) <= S.TOL or not any(o[2] in T.WALKABLE_PARTNERS for o in others):
                            continue
                        if blk not in base_ml:
                            base_ml[blk] = T.meshlist_for(blocks, blk)
                            base_idx[blk] = P.build_meshlist_index(base_ml[blk])
                        if mla is None:
                            mla = T.meshlist_for(blocks, blk, [(v[0], v[1] + A * wt.get(v, 0.0), v[2]) for v in ter.lv])
                        mlb, idx = base_ml[blk], base_idx[blk]
                        probes = []
                        for (p, t) in tri_at[blk][lp]:
                            m = blocks[blk][p]
                            cs = [m.lv[m.fi[3 * t + k]] for k in range(3)]
                            gx, gz = sum(q[0] for q in cs) / 3 - lp[0], sum(q[2] for q in cs) / 3 - lp[2]
                            L = math.hypot(gx, gz)
                            if L < 1e-6:
                                continue
                            probes.append((p, t, cs, (lp[0] + T.PROBE * gx / L, lp[2] + T.PROBE * gz / L)))
                        for (pa, ta, csa, Ap) in probes:
                            for (pb, tb, csb, Bp) in probes:
                                if pa == pb or "terrain" not in (pa, pb):
                                    continue
                                if pa not in T.WALKABLE_PARTNERS | {"terrain"} or pb not in T.WALKABLE_PARTNERS | {"terrain"}:
                                    continue
                                before, db = T.crossing(mlb, idx, Ap, mlb, idx, Bp)
                                after, da = T.crossing(mla, idx, Ap, mla, idx, Bp)
                                if not (before and after is False):
                                    continue
                                vert_to = xz_area(csb) < 1e-6
                                vert_from = xz_area(csa) < 1e-6
                                grounded = db.split(":")[0]           # mesh the stock step grounded on
                                key = (f"A{A:+g}", f"{pa}->{pb}", "to-tri VERTICAL" if vert_to else "to-tri has XZ area",
                                       "from-tri VERTICAL" if vert_from else "from-tri has XZ area",
                                       f"stock step grounded on {grounded}", da.split("(")[0])
                                stats[key] += 1
                                if len(examples) < 12 and da.startswith("unwalkable topo 59"):
                                    examples.append({"blk": blk, "lp": lp, "A": A, "R": R, "from": pa, "to": pb,
                                                     "to_tri": [tuple(round(q, 4) for q in c) for c in csb],
                                                     "stock": db, "after": da})
    tot = Counter()
    for k, v in stats.items():
        tot[(k[0], k[1], k[2], k[4], k[5])] += v
    print("introduced walls on Object-centre edits, by (amount, direction, target-tri geometry, stock ground, reason):")
    for k, v in sorted(tot.items()):
        print(f"   {v:6d}  {k}")
    t59 = sum(v for k, v in stats.items() if k[5].startswith("unwalkable topo 59"))
    t59v = sum(v for k, v in stats.items() if k[5].startswith("unwalkable topo 59") and k[2] == "to-tri VERTICAL")
    t59g = sum(v for k, v in stats.items() if k[5].startswith("unwalkable topo 59") and k[4] == "stock step grounded on Terrain")
    print(f"topo-59 walls (A +1/+3 only here): {t59}; target probe on a VERTICAL Object tri: {t59v}; stock step grounded on "
          f"TERRAIN (not on an Object sheet): {t59g}")
    out = {"by_class": [[list(k), v] for k, v in sorted(tot.items())],
           "topo59_total": t59, "topo59_target_vertical": t59v, "topo59_stock_on_terrain": t59g, "examples": examples}
    p = S.OUT / "verify_object_walls.json"
    p.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("->", p)


if __name__ == "__main__":
    main()
