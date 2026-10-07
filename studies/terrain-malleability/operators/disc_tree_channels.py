"""Operator inventory, step 4b: WHAT differs between Disc1 and Disc4 terrain on the 179 blocks disc_tree_inventory.py
flagged -- geometry, UV, topograph/area/event (tangent.x IDALL), or just normals/index order?

Why: 'differs' is a coarse predicate (discmirror._parts_identical). The malleability question is finer:
  * if only IDALL area/event differ, a Disc1 geometry edit COULD be mirrored by patching geometry alone
    (but discmirror refuses the whole cell, by design);
  * if verts differ, the two trees are genuinely different terrain and an edit must be authored per tree.
READ-ONLY; writes out/disc_tree_channels.json (counts/coordinates only).
CALIBRATION: a block vs itself must classify as {} (no channel differs); a vs a deliberately perturbed copy must
classify verts-differ -- both asserted before the census is trusted.

Rerun:  py studies/terrain-malleability/operators/disc_tree_channels.py
"""
import json, os, sys
from collections import Counter

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
inv = json.load(open(os.path.join(OUT, "disc_tree_inventory.json"), encoding="utf-8"))
differs = [tuple(b) for b in inv["terrain_differs"]]
both_all = None


def classify(a, b):
    ch = {}
    if a.vcount != b.vcount:
        ch["vcount"] = (a.vcount, b.vcount)
        return ch
    if a.verts != b.verts:
        mx = max(max(abs(p - q) for p, q in zip(u, v)) for u, v in zip(a.verts, b.verts))
        ch["verts"] = round(mx, 4)
    if a.uvs != b.uvs:
        ch["uv"] = True
    if a.flat_index != b.flat_index:
        ch["index"] = True
    if a.normals != b.normals:
        ch["normals"] = True
    if a.tangents != b.tangents:
        dec = Counter()
        for ta, tb in zip(a.tangents, b.tangents):
            if ta != tb:
                da, db = X.decode_id(int(round(ta[0]))), X.decode_id(int(round(tb[0])))
                for k in ("event", "area", "topograph", "flags"):
                    if da[k] != db[k]:
                        dec[k] += 1
                if ta[1:] != tb[1:]:
                    dec["tangent_yzw"] += 1
        ch["tangent"] = dict(dec)
    return ch


# calibration
b = X.read_block(7, 7, disc=1, part="terrain")
assert classify(b, X.read_block(7, 7, disc=1, part="terrain")) == {}, "self-compare must be empty"
import copy
p = copy.deepcopy(b)
p.verts[0][1] += 0.5
assert "verts" in classify(b, p), "perturbation must register"
print("calibration OK (self=={}, +0.5 Y perturbation -> verts)")

rows, kinds = {}, Counter()
for blk in differs:
    a = X.read_block(blk[0], blk[1], disc=1, part="terrain")
    d = X.read_block(blk[0], blk[1], disc=4, part="terrain")
    c = classify(a, d)
    rows[f"{blk[0]},{blk[1]}"] = c
    kinds[tuple(sorted(c))] += 1

print(f"{len(differs)} differing blocks; channel-signature histogram:")
for k, n in kinds.most_common():
    print(f"  {n:4d}  {k}")
geom = [k for k, c in rows.items() if "vcount" in c or "verts" in c]
idonly = [k for k, c in rows.items() if not ("vcount" in c or "verts" in c) and "tangent" in c]
print(f"\nblocks whose GEOMETRY (vcount/verts) differs: {len(geom)}; blocks identical in geometry but different IDALL/uv/normals: {len(rows) - len(geom)}")
tang = Counter()
for c in rows.values():
    for k in (c.get("tangent") or {}):
        tang[k] += 1
print("tangent sub-field difference (block counts):", dict(tang))
json.dump({"signature_hist": {"|".join(k): n for k, n in kinds.items()}, "rows": rows}, open(os.path.join(OUT, "disc_tree_channels.json"), "w"), indent=1)
