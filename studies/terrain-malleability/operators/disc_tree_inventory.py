"""Operator inventory, step 4 (the DISC-4 MIRRORING axis, measured): how different are the two shipped overworld
asset trees (Disc1 serves discs 1-3, Disc4 is its own), and therefore how many REAL blocks can the auto-mirror
NOT carry a terrain edit onto?

Why it matters: discmirror.mirror gates per cell -- "the destination's REAL cell must be open ocean (no real
assets) or byte-identical to the source disc's; an --in-place edit of a real block that DIFFERS across discs must
not be transplanted between them -- those cells skip with a warning" (world/discmirror.py:12-16).  world-terrain,
world-retarget, world-deploy and every --in-place morph edit REAL blocks, so on a block whose Disc1 and Disc4
terrain differ, the edit exists on one tree only.

READ-ONLY (reads the user's own install via the kit reader; writes only out/disc_tree_inventory.json, which is
derived statistics -- counts and coordinates, no mesh bytes).

Part 1 (cheap): per-disc part inventory from the asset CONTAINER names (no mesh decode).
Part 2 (decodes): for every block that has a Terrain mesh on BOTH discs, are the two byte-identical (the same
        predicate discmirror._parts_identical uses: vcount, verts, flat_index, uvs, tangents, normals)?
CALIBRATION: (a) a block compared with ITSELF must report identical; (b) a block compared with a DIFFERENT block
must report different -- the predicate must be able to answer both ways before its disc verdict means anything.

Rerun:  py studies/terrain-malleability/operators/disc_tree_inventory.py
"""
import json, os, re, sys, time
from collections import Counter, defaultdict

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X
from ff9mapkit.world import discmirror as DM

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
t0 = time.time()

inv = {}
for disc in (1, 4):
    env = X._worldmap_env(disc)
    pat = re.compile(rf"worldmap/disc{disc}/(0_\d)/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
    parts = defaultdict(set)
    lods = Counter()
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            lods[m.group(1)] += 1
            if m.group(1) == "0_1":
                parts[(int(m.group(2)), int(m.group(3)))].add(m.group(4))
    inv[disc] = {"parts": parts, "lods": dict(lods)}
    freq = Counter(p for s in parts.values() for p in s)
    print(f"disc{disc}: lod mesh counts {dict(lods)}; blocks with any 0_1 part: {len(parts)}; "
          f"part frequency {dict(sorted(freq.items(), key=lambda kv: -kv[1]))}")

t1 = {b for b, s in inv[1]["parts"].items() if "terrain" in s}
t4 = {b for b, s in inv[4]["parts"].items() if "terrain" in s}
both = sorted(t1 & t4)
print(f"terrain blocks: disc1={len(t1)} disc4={len(t4)} both={len(both)} only1={len(t1 - t4)} only4={len(t4 - t1)}")

# part-set differences on shared blocks (cheap)
pset_diff = [b for b in sorted(set(inv[1]['parts']) & set(inv[4]['parts'])) if inv[1]['parts'][b] != inv[4]['parts'][b]]
print(f"blocks present on both discs whose 0_1 PART SET differs: {len(pset_diff)}")

# ---- calibration ----------------------------------------------------------------------------------
b0 = both[0]
b1 = both[len(both) // 2]
same = DM._parts_identical(b0, "terrain", 1, 1)
diff = DM._parts_identical(b0, "terrain", 1, 1) if False else None
a = X.read_block(b0[0], b0[1], disc=1, part="terrain")
c = X.read_block(b1[0], b1[1], disc=1, part="terrain")
cross = (a.vcount == c.vcount and a.verts == c.verts)
print(f"CALIBRATION self-vs-self (disc1 vs disc1) identical={same}  | different blocks {b0} vs {b1} identical={cross}")
assert same is True and cross is False, "predicate cannot answer both ways -- stop"

# ---- the decode comparison -------------------------------------------------------------------------
ident, differs, errs = [], [], []
for i, b in enumerate(both):
    try:
        (ident if DM._parts_identical(b, "terrain", 1, 4) else differs).append(b)
    except Exception as e:                                    # noqa: BLE001
        errs.append((b, repr(e)[:80]))
    if i % 40 == 0:
        print(f"  {i}/{len(both)} identical={len(ident)} differ={len(differs)} errs={len(errs)} t={time.time() - t0:.0f}s", flush=True)

res = {
    "terrain_blocks": {"disc1": len(t1), "disc4": len(t4), "both": len(both), "only_disc1": sorted(t1 - t4), "only_disc4": sorted(t4 - t1)},
    "terrain_identical_both_discs": len(ident), "terrain_differs": sorted(differs), "errors": errs,
    "part_set_differs_blocks": pset_diff,
    "part_freq": {d: dict(Counter(p for s in inv[d]['parts'].values() for p in s)) for d in (1, 4)},
    "lod_mesh_counts": {d: inv[d]["lods"] for d in (1, 4)},
    "seconds": round(time.time() - t0),
}
json.dump(res, open(os.path.join(OUT, "disc_tree_inventory.json"), "w", encoding="utf-8"), indent=1)
print(f"\nRESULT: of {len(both)} terrain blocks on BOTH discs: identical={len(ident)} DIFFER={len(differs)} errors={len(errs)}; "
      f"only-on-disc1={len(t1 - t4)} only-on-disc4={len(t4 - t1)}; {time.time() - t0:.0f}s")
if differs:
    print("DIFFERING blocks:", differs[:60])
