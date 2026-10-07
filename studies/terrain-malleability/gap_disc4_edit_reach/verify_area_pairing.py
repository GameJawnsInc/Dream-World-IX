"""VERIFY (adversarial) -- G9/G13: are the order-invariant area/topograph/event re-zone counts robust to the
arbitrary pop() pairing of DUPLICATE geometry keys?

s2/s6 pair disc-1 and disc-4 terrain tris by position-only key and pop() the first free disc-4 match. If a block
holds several tris with the SAME position triple (stacked/coplanar duplicates) and those carry different IDALL,
an arbitrary pairing could manufacture transitions (0->7 and 7->0) that a multiset compare would not see.

Here: per block, per geometry key, compare the MULTISET of each IDALL field on disc 1 vs disc 4. The minimal
number of tris whose field must differ = sum over keys of (n - |multiset intersection|). Blocks with any.
Also: duplicate-key census, and the F18 overlap for area (lane says 17 of 44 shared).
Read-only; uses the lane cache (GAP_DISC4_CACHE honoured).
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402

data = L.load_cache()
meshes, pairs = data["meshes"], data["pairs"]
objs = L.mesh_objects()
FN = {"event": L.event, "area": L.area, "topograph": L.topo}

blocks = Counter(); tris = Counter(); dup_keys = 0; dup_blocks = set(); dup_mixed = 0
blk_list = defaultdict(list)
for (x, y, p), pr in sorted(pairs.items()):
    if p != "terrain" or pr["perm"]:
        continue
    a = L.decode(objs[(1, "0_1", x, y, p)], 1, x, y)
    b = L.decode(objs[(4, "0_1", x, y, p)], 4, x, y)
    k1 = [k[0] for k in L.tri_keys(a, L._prec(a))]
    k4 = [k[0] for k in L.tri_keys(b, L._prec(b))]
    I1, I4 = meshes[(1, x, y, p)]["idall"], meshes[(4, x, y, p)]["idall"]
    g1, g4 = defaultdict(list), defaultdict(list)
    for i, k in enumerate(k1):
        g1[k].append(int(I1[i]))
    for j, k in enumerate(k4):
        g4[k].append(int(I4[j]))
    for k, v in g1.items():
        if len(v) > 1:
            dup_keys += 1; dup_blocks.add((x, y))
            if len({FN["area"](i) for i in v}) > 1:
                dup_mixed += 1
    hit = Counter()
    for k in set(g1) & set(g4):
        n = min(len(g1[k]), len(g4[k]))          # matched geometry count for this key
        for nm, fn in FN.items():
            c1 = Counter(fn(i) for i in g1[k]); c4 = Counter(fn(i) for i in g4[k])
            inter = sum((c1 & c4).values())
            d = n - min(inter, n)
            if d:
                hit[nm] += d
    for nm, n in hit.items():
        blocks[nm] += 1; tris[nm] += n; blk_list[nm].append((x, y))

op = json.loads((L.LANE.parent / "operators" / "out" / "disc_tree_channels.json").read_text(encoding="utf-8"))["rows"]
f18_area = {tuple(int(a) for a in k.split(",")) for k, v in op.items() if "area" in (v.get("tangent") or {})}
res = {"multiset_blocks": dict(blocks), "multiset_tris": dict(tris),
       "dup_geometry_keys": dup_keys, "dup_key_blocks": len(dup_blocks), "dup_keys_with_mixed_area": dup_mixed,
       "area_blocks_shared_with_F18": len(set(blk_list["area"]) & f18_area), "f18_area_blocks": len(f18_area)}
print(json.dumps(res, indent=1))
(L.OUT / "verify_area_pairing.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
