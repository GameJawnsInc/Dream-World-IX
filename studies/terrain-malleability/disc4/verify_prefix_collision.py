"""VERIFIER (adversarial) -- D4-17 / P4: sweep EVERY (disc, lod, block, part) and check which container
extract.read_block's lookup resolves to versus the exact container (d4lib.mesh_objects regex, anchored).

read_block (extract.py) resolves `target = "worldmap/disc{d}/{lod}/r{y}/block[{x}][{y}] {part}"` by the
FIRST container in _mesh_index order with `c.endswith(target) or (target in c)`. Any part name that is a
prefix of another part name on the same block can collide: sea4 / sea4f, and river / riverjoint.

This script replicates the lookup on the index (cheap, no decode) and then CONFIRMS each mismatch by
calling the real X.read_block and comparing vcount against the exact decode. Read-only.

FIXED since: read_block now matches the part EXACTLY (extract._find_block_part). The replicated OLD rule
below still reports its 3 mismatches by construction; the LIVE line and `read_block_wrong` are the verdict
on the current code (0 and False once the fix is in). Regression test: tests/test_world_block_part_lookup.py.
Run: py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/verify_prefix_collision.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402
from d4lib import X                                  # noqa: E402

env = X._worldmap_env(1)
idx = X._mesh_index(env)
objs = L.mesh_objects()
inv = {id(o): k for k, o in objs.items()}

# which part names are prefixes of another part name on the same (disc, lod, block)?
parts_at = {}
for (d, lod, x, y, p) in objs:
    parts_at.setdefault((d, lod, x, y), set()).add(p)
prefix_pairs = Counter()
for key, ps in parts_at.items():
    for a in ps:
        for b in ps:
            if a != b and b.startswith(a):
                prefix_pairs[(a, b)] += 1
print("prefix-colliding part pairs present on a block (a is a prefix of b):", dict(prefix_pairs))

mism = []
for (d, lod, x, y, p), o in sorted(objs.items()):
    target = f"worldmap/disc{d}/{lod}/r{y}/block[{x}][{y}] {p}"
    hit = None
    for c, oo in idx.items():
        if c.endswith(target) or (target in c):
            hit = (c, oo)
            break
    if hit is None or hit[1] is not o:
        mism.append({"disc": d, "lod": lod, "x": x, "y": y, "part": p, "resolved": hit[0] if hit else None})
print(f"{len(objs)} exact meshes swept; OLD substring rule (replicated) mismatches: {len(mism)}")
if hasattr(X, "_find_block_part"):                   # the live lookup; absent on pre-fix code
    from ff9mapkit.extract import env_lock           # noqa: E402
    with env_lock:
        live = [k for k, o in sorted(objs.items()) if X._find_block_part(env, *k) is not o]
    print(f"LIVE read_block lookup mismatches: {len(live)} {live}")
conf = []
for m in mism:
    bm = X.read_block(m["x"], m["y"], disc=m["disc"], lod=m["lod"], part=m["part"])
    ex = L.decode(objs[(m["disc"], m["lod"], m["x"], m["y"], m["part"])], m["disc"], m["x"], m["y"], m["lod"])
    m["read_block_vcount"] = bm.vcount
    m["exact_vcount"] = ex.vcount
    m["read_block_wrong"] = (bm.vcount != ex.vcount) or (bm.verts != ex.verts)
    print("  ", m)
    conf.append(m)
# what does the discmirror gate do at mismatched cells? (both discs' reads, as _parts_identical does)
from ff9mapkit.world import discmirror as DM        # noqa: E402
gate_cells = sorted({(m["x"], m["y"], m["part"]) for m in mism if m["lod"] == "0_1"})
for (x, y, p) in gate_cells:
    a1 = objs.get((1, "0_1", x, y, p)); a4 = objs.get((4, "0_1", x, y, p))
    true_same = None
    if a1 is not None and a4 is not None:
        s1, s4 = L.raw_sig(a1), L.raw_sig(a4)
        true_same = L.sig_identical(s1, s4)
    print(f"  gate cell ({x},{y}) part {p}: _parts_identical={DM._parts_identical((x, y), p, 1, 4)}  "
          f"exact bytes identical across discs={true_same}")
out = Path(__file__).resolve().parent / "out" / "verify_prefix_collision.json"
out.write_text(json.dumps({"prefix_pairs": {f"{a}<{b}": v for (a, b), v in prefix_pairs.items()},
                           "mismatches": conf}, indent=1), encoding="utf-8")
print("->", out)
