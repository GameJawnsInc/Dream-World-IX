"""STEP 0 -- build the decoded two-disc cache + calibrate the order-invariant matcher.

Builds lib.CACHE (outside the repo): every real Form-1 (0_1) (cell, part) on discs 1 and 4, exact container
match, with an all-channel order-invariant triangle match and a geometry-only match per pair.

CALIBRATION (asserted before anything is trusted):
  C1 self-compare of a mesh -> every tri matched, perm=True
  C2 a buffer-order shuffle of whole triangles (corner rotation kept) -> perm=True, raw_identical False
  C3 a corner ROTATION inside one tri (same winding) -> still matched (canonical rotation) iff the 3 corners
     carry the same tangent.x; a winding REVERSAL -> NOT matched
  C4 a +1/256 Y nudge of one vertex -> exactly one tri unmatched each side
  C5 a tangent.x (IDALL) change on one tri -> all-channel unmatched, geometry still matched
Writes out/s0_cache_summary.json (counts only).
Run (from C:\\gd\\Dream-World-IX\\ff9mapkit):  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_disc4_edit_reach/s0_cache.py [--rebuild]
"""
import copy
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402

objs = L.mesh_objects()
bm = L.decode(objs[(1, "0_1", 7, 7, "terrain")], 1, 7, 7)


def match(a, b):
    k1, k4 = L.tri_keys(a, L._vrec(a)), L.tri_keys(b, L._vrec(b))
    m1, m4 = L.multiset_match(k1, k4)
    g1, g4 = L.multiset_match([k[0] for k in L.tri_keys(a, L._prec(a))], [k[0] for k in L.tri_keys(b, L._prec(b))])
    return m1, m4, g1, g4


def rebuild(bm, tri_order, rot=None, flip=None):
    """Re-emit bm with whole triangles in a new order (fresh 3 verts per tri, the unindexed layout)."""
    b = copy.deepcopy(bm)
    fi = bm.flat_index
    new_ca = {ci: [] for ci in bm.chan_arrays}
    flat = []
    for n, t in enumerate(tri_order):
        cs = [fi[3 * t], fi[3 * t + 1], fi[3 * t + 2]]
        if rot and t in rot:
            cs = cs[1:] + cs[:1]
        if flip and t in flip:
            cs = [cs[0], cs[2], cs[1]]
        for k, vi in enumerate(cs):
            for ci in bm.chan_arrays:
                new_ca[ci].append(list(bm.chan_arrays[ci][vi]))
            flat.append(3 * n + k)
    b.chan_arrays = new_ca
    b.flat_index = flat
    b.tris = [flat[i:i + 3] for i in range(0, len(flat), 3)]
    b.vcount = len(flat)
    return b


n = len(bm.flat_index) // 3
res = {}
m1, m4, g1, g4 = match(bm, copy.deepcopy(bm))
assert m1.all() and m4.all(), "C1 self-compare must fully match"
res["C1"] = "ok"
order = list(range(n)); random.Random(7).shuffle(order)
sh = rebuild(bm, order)
m1, m4, _, _ = match(bm, sh)
assert m1.all() and m4.all() and not L.raw_identical(bm, sh), "C2 shuffle must be a permutation, not raw-identical"
res["C2"] = "ok"
# C3: rotation of tri 0 corners
fi = bm.flat_index
same_tan = len({bm.tangents[fi[k]][0] for k in range(3)}) == 1
rt = rebuild(bm, list(range(n)), rot={0})
m1, m4, _, _ = match(bm, rt)
assert bool(m1.all()) == same_tan, "C3 rotation must match iff corners share tangent.x"
fl = rebuild(bm, list(range(n)), flip={0})
m1, m4, g1, g4 = match(bm, fl)
assert (~m1).sum() == 1 and (~g1).sum() == 1, "C3 winding reversal must NOT match (all-channel and geometry)"
res["C3"] = f"ok (tri0 corners share tangent.x: {same_tan})"
# C4: nudge one vertex Y by 1/256
nd = copy.deepcopy(bm)
nd.chan_arrays[L.X.CH_POS][fi[0]][1] += 1 / 256
m1, m4, g1, g4 = match(bm, nd)
assert (~m1).sum() == 1 and (~m4).sum() == 1 and (~g1).sum() == 1, "C4 one nudged vertex -> one tri unmatched"
res["C4"] = "ok"
# C5: idall change on tri 0 (all 3 corners)
idc = copy.deepcopy(bm)
for k in range(3):
    idc.chan_arrays[L.X.CH_TAN][fi[k]][0] += 4.0
m1, m4, g1, g4 = match(bm, idc)
assert (~m1).sum() == 1 and g1.all(), "C5 IDALL change: all-channel unmatched, geometry matched"
res["C5"] = "ok"
print("matcher calibration:", res)

data = L.load_cache(rebuild="--rebuild" in sys.argv)
pairs = data["pairs"]
summ = {
    "calibration": res,
    "meshes": len(data["meshes"]),
    "pairs_both_discs": len(pairs),
    "cells": len(data["cells"]),
    "layout_mismatch": data["layout_mismatch"],
    "extra_channels_beyond_override_4": dict(data["extra_channels"]),
    "pairs_raw_identical": sum(1 for p in pairs.values() if p["raw_identical"]),
    "pairs_perm_not_raw": sum(1 for p in pairs.values() if p["perm"] and not p["raw_identical"]),
    "pairs_real_change": sum(1 for p in pairs.values() if not p["perm"]),
    "parts_one_disc_only": sorted([f"d{d}:{x},{y},{p}" for (d, x, y, p) in data["meshes"]
                                   if (x, y, p) not in pairs]),
}
print(json.dumps({k: v for k, v in summ.items() if k != "parts_one_disc_only"}, indent=1))
print("parts present on one disc only:", summ["parts_one_disc_only"])
(L.OUT / "s0_cache_summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
