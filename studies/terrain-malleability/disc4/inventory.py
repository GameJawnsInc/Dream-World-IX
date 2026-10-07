"""STEP 0 -- the WORLDMAP ASSET INVENTORY, both discs, every container kind.

What lives under `worldmap/disc1/` vs `worldmap/disc4/` (and the prefab trees
`worldmap/prefabs/worlddisc1|4/`) in the user's own p0data bundles: per asset TYPE, per LOD,
per sub-mesh PART. This is the denominator every later count is taken against.

Read-only on the install (the bundle hint `.ff9mapkit-worldmap-bundle.json` already carries
both discs, so `_worldmap_env` takes its hit path and writes nothing).

Writes out/inventory.json (container -> type, grouped). Run from anywhere:
    py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/inventory.py
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X          # noqa: E402
from ff9mapkit import extract as FX               # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

env1 = X._worldmap_env(1)
env4 = X._worldmap_env(4)
print("disc1 env is disc4 env:", env1 is env4)

# every container mentioning worldmap, across ALL bundles (not just the terrain-mesh bundle), so
# disc-4-only prefabs/textures elsewhere are not missed
rows = []
for path in sorted(FX._bundles(None)):
    try:
        env = FX._load_env(path)
    except Exception:  # noqa: BLE001
        continue
    for k, o in env.container.items():
        kl = (k or "").lower()
        if "worldmap" in kl or "worlddisc" in kl:
            rows.append((Path(path).name, kl, o.type.name))
print("worldmap containers:", len(rows))

kind = Counter()
by = defaultdict(Counter)
mesh_re = re.compile(r"worldmap/disc(\d)/([0-9_]+)/r(\d+)/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
pref_re = re.compile(r"worldmap/prefabs/worlddisc(\d)/r(\d+)/block\[(\d+)\]\[(\d+)\](f?)(?:\.prefab)?$")
meshes = defaultdict(lambda: defaultdict(set))       # disc -> lod -> {(x,y,part)}
prefabs = defaultdict(set)                            # disc -> {(x,y,suffix)}
other = Counter()
for bundle, k, t in rows:
    m = mesh_re.search(k)
    if m:
        d, lod, _r, x, y, part = m.groups()
        meshes[int(d)][lod].add((int(x), int(y), part))
        kind[("mesh-block", t)] += 1
        continue
    m = pref_re.search(k)
    if m:
        d, _r, x, y, f = m.groups()
        prefabs[int(d)].add((int(x), int(y), f))
        kind[("prefab-block", t)] += 1
        continue
    # generalize the rest: strip digits/brackets to a pattern
    g = re.sub(r"\d+", "#", k)
    other[(bundle, g, t)] += 1

print("\n== kinds ==")
for k, v in sorted(kind.items()):
    print(f"  {k}: {v}")
summary = {"meshes": {}, "prefabs": {}, "other": []}
print("\n== block meshes per disc/lod: blocks, parts ==")
for d in sorted(meshes):
    for lod in sorted(meshes[d]):
        s = meshes[d][lod]
        blocks = {(x, y) for x, y, _ in s}
        parts = Counter(p for _, _, p in s)
        print(f"  disc{d} lod {lod}: {len(s)} meshes on {len(blocks)} blocks; parts {dict(sorted(parts.items()))}")
        summary["meshes"][f"disc{d}/{lod}"] = {
            "n_meshes": len(s), "n_blocks": len(blocks), "parts": dict(sorted(parts.items())),
            "items": sorted([list(t) for t in s])}
print("\n== block prefabs per disc ==")
for d in sorted(prefabs):
    s = prefabs[d]
    print(f"  WorldDisc{d}: {len(s)} prefabs ({sum(1 for *_, f in s if f)} with 'f' suffix)")
    summary["prefabs"][f"WorldDisc{d}"] = sorted([list(t) for t in s])
pb1 = {(x, y, f) for x, y, f in prefabs.get(1, ())}
pb4 = {(x, y, f) for x, y, f in prefabs.get(4, ())}
print("  prefab only in disc1:", sorted(pb1 - pb4)[:40], len(pb1 - pb4))
print("  prefab only in disc4:", sorted(pb4 - pb1)[:40], len(pb4 - pb1))
print("\n== other worldmap containers (generalized) ==")
for (b, g, t), v in sorted(other.items(), key=lambda kv: kv[0][1]):
    if "disc" in g or "worlddisc" in g:
        print(f"  {b:14s} {t:14s} x{v:4d}  {g}")
    summary["other"].append([b, g, t, v])
(OUT / "inventory.json").write_text(json.dumps(summary, indent=0), encoding="utf-8")
print("\n->", OUT / "inventory.json")
