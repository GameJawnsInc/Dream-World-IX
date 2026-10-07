"""CALIBRATION of the walk-crossing instrument in tear_sweep.py before its verdicts are trusted.

W1 stock baseline: at every Terrain|Beach1 weld on (7,17) (the proven beach donor), the probe crossings
   beach1->terrain and terrain->beach1 must be LEGAL on pristine stock (an instrument that refuses stock is broken).
W2 the climb ceiling: a UNIFORM +dy lift of (7,17)'s Terrain (flat field, so no falloff slope) must turn
   beach1->terrain crossings from legal to refused at dy = 2.34375 minus the probe's own terrain rise over the
   0.8u probe gap (the engine constant, ff9.cs rayStartOffsetY), and terrain->beach1 (a DROP) must stay legal for
   every dy (no reach limit: WMBlock.Raycast never reads `distance`).
W3 the canopy sink: on a stock block with topo 36/37/38 Terrain beside non-canopy walkable Terrain, a uniform lift
   of the NON-canopy side must refuse canopy->lawn climbs at ~1.171875 (2.34375 - 1.171875), not 2.34375.
W4 the 10-slot cache: count how many crossings the cache decides vs the scan (Y-only edits keep XZ footprints, so
   a seam crossing leaves the cached start tri and the cache should decide none).
Writes out/calibrate_walk.json.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/calibrate_walk.py
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402
import tear_sweep as T                                 # noqa: E402
from ff9mapkit.world import placement as P             # noqa: E402

M = S.load_disc(1)
blocks = T.build_world(M)
res = {}


def probes_between(blk, part_a, part_b, pred_a=None, pred_b=None, limit=400):
    """(A, B) probe pairs 0.4u into a part_a tri and a part_b tri sharing a vertex."""
    tri_at = defaultdict(list)
    for p in (part_a, part_b):
        m = blocks[blk][p]
        for t in range(m.ntri):
            for k in range(3):
                tri_at[m.lv[m.fi[3 * t + k]]].append((p, t))
    out = []
    for lp, lst in tri_at.items():
        A = [(p, t) for p, t in lst if p == part_a and (pred_a is None or pred_a(blocks[blk][p], t))]
        Bs = [(p, t) for p, t in lst if p == part_b and (pred_b is None or pred_b(blocks[blk][p], t))]
        if not A or not Bs or (part_a == part_b and not set(A) - set(Bs)):
            continue
        for (pa, ta) in A:
            for (pb, tb) in Bs:
                if (pa, ta) == (pb, tb):
                    continue
                pts = []
                for (p, t) in ((pa, ta), (pb, tb)):
                    m = blocks[blk][p]
                    cs = [m.lv[m.fi[3 * t + k]] for k in range(3)]
                    gx, gz = sum(q[0] for q in cs) / 3 - lp[0], sum(q[2] for q in cs) / 3 - lp[2]
                    L = math.hypot(gx, gz)
                    pts.append((lp[0] + T.PROBE * gx / L, lp[2] + T.PROBE * gz / L))
                out.append((lp, pts[0], pts[1]))
        if len(out) >= limit:
            break
    return out


# ---- W1 + W2 on (7,17) -----------------------------------------------------------------------
blk = (7, 17)
ml0 = T.meshlist_for(blocks, blk)
idx = P.build_meshlist_index(ml0)
pairs = probes_between(blk, "beach1", "terrain")
w1 = Counter()
for lp, A, B in pairs:
    w1["b->t " + str(T.crossing(ml0, idx, A, ml0, idx, B)[0])] += 1
    w1["t->b " + str(T.crossing(ml0, idx, B, ml0, idx, A)[0])] += 1
print(f"W1 stock (7,17) beach1|terrain crossings ({len(pairs)} probe pairs): {dict(w1)}")
res["W1_stock"] = dict(w1)
ter = blocks[blk]["terrain"]
w2 = {}
for dy in (1.0, 2.0, 2.2, 2.3, 2.34, 2.35, 2.4, 2.6, 3.0, 6.0):
    tv = [(v[0], v[1] + dy, v[2]) for v in ter.lv]
    ml1 = T.meshlist_for(blocks, blk, tv)
    c = Counter()
    for lp, A, B in pairs:
        c["b->t legal" if T.crossing(ml1, idx, A, ml1, idx, B)[0] else "b->t refused"] += 1
        c["t->b legal" if T.crossing(ml1, idx, B, ml1, idx, A)[0] else "t->b refused"] += 1
    w2[str(dy)] = dict(c)
    print(f"W2 uniform terrain lift +{dy}: {dict(c)}")
res["W2_lift"] = w2

# ---- W3 canopy sink: find a block with canopy (36-38) terrain tris welded to non-canopy walkable terrain -----
canopy = lambda m, t: S.topo(m.tri_idall(t)) in T.CANOPY            # noqa: E731
lawn = lambda m, t: S.topo(m.tri_idall(t)) in P.WALK_OK and S.topo(m.tri_idall(t)) not in T.CANOPY  # noqa: E731
best = None
for b in sorted(blocks):
    if "terrain" not in blocks[b]:
        continue
    pp = probes_between(b, "terrain", "terrain", pred_a=canopy, pred_b=lawn, limit=400)
    if not pp:
        continue
    _ml = T.meshlist_for(blocks, b)
    _ix = P.build_meshlist_index(_ml)
    # keep only pairs whose stock SKY cast grounds A on canopy and B on non-canopy walkable terrain (a probe
    # 0.4u toward a steep wall tri's centroid can land in a neighbour's footprint -- the first W3 run's bug)
    keep = []
    for lp, A, B in pp:
        ta = T.hit_tri(_ml, _ix, A[0], A[1], 0.0, sky=True)
        tb = T.hit_tri(_ml, _ix, B[0], B[1], 0.0, sky=True)
        if ta[0] is None or tb[0] is None:
            continue
        if S.topo(ta[2]) in T.CANOPY and S.topo(tb[2]) in P.WALK_OK and S.topo(tb[2]) not in T.CANOPY                 and _ml[tb[0][0]][0] == "Terrain" and abs(ta[1] - tb[1]) < 0.3:
            keep.append((lp, A, B))
    pp = keep
    if len(pp) >= 20:
        best = (b, pp)
        break
b, pp = best
mlc = T.meshlist_for(blocks, b)
idc = P.build_meshlist_index(mlc)
terc = blocks[b]["terrain"]
lawn_v = set()
for t in range(terc.ntri):
    if lawn(terc, t):
        lawn_v |= {terc.lv[terc.fi[3 * t + k]] for k in range(3)}
canopy_v = set()
for t in range(terc.ntri):
    if canopy(terc, t):
        canopy_v |= {terc.lv[terc.fi[3 * t + k]] for k in range(3)}
only_lawn = lawn_v - canopy_v
w3 = {}
for dy in (0.8, 1.0, 1.1, 1.15, 1.2, 1.3, 1.6, 2.0, 2.3, 2.4):
    # lift the lawn TRIS' own vertex INSTANCES (the mesh is unindexed: a canopy tri keeps its own copy of a
    # shared corner), so the seam gets a vertical step of exactly dy -- a clean canopy->lawn climb of dy
    lift_i = {terc.fi[3 * t + k] for t in range(terc.ntri) if lawn(terc, t) for k in range(3)}
    tv = [(v[0], v[1] + (dy if i in lift_i else 0.0), v[2]) for i, v in enumerate(terc.lv)]
    ml1 = T.meshlist_for(blocks, b, tv)
    c = Counter()
    for lp, A, B in pp:                                  # A on canopy, B on lawn
        c["canopy->lawn legal" if T.crossing(ml1, idc, A, ml1, idc, B)[0] else "canopy->lawn refused"] += 1
    w3[str(dy)] = dict(c)
    print(f"W3 block {b}: lawn tris lifted +{dy}: {dict(c)}")
res["W3_canopy"] = {"block": list(b), "pairs": len(pp), "by_dy": w3}

# ---- W4 cache vs scan accounting over the W2 +3 case ---------------------------------------------
tv = [(v[0], v[1] + 3.0, v[2]) for v in ter.lv]
ml1 = T.meshlist_for(blocks, blk, tv)
how = Counter()
for lp, A, B in pairs:
    for (S0, S1) in ((A, B), (B, A)):
        st, gy, ida = T.hit_tri(ml1, idx, S0[0], S0[1], 0.0, sky=True)
        if st is None:
            continue
        tp = S.topo(ida)
        y = gy - (T.SINK if tp in T.CANOPY else 0.0)
        r = T.walk_step(ml1, idx, S1[0], S1[1], y, [st], use_cache=tp not in (49, 52))
        how[r[4]] += 1
print(f"W4 cache-vs-scan deciders over {sum(how.values())} crossings: {dict(how)}")
res["W4_cache"] = dict(how)
p = S.save_json("calibrate_walk.json", res)
print("->", p)
