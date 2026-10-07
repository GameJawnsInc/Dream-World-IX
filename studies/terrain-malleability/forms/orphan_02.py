"""forms lane -- the 0_2 mesh directory vs what the baked prefabs actually reference.

WMWorldPrefabMaker (the editor-side baker; RESEARCH.md: zero runtime call sites) only ever loads Terrain/Object/
VolcanoCrater/VolcanoLava from 0_2 (as Terrain2/Object2/..), plus Sea3/4/5 for (3,9) (WMWorldPrefabMaker.cs:119-166).
So any OTHER 0_2 mesh (river/sea/beach/...) is an ORPHAN: present in the asset bundle, never instanced. Are the orphans
just copies of their 0_1 counterparts (nothing lost) or genuine per-form water variants the Unity port dropped?
Rerun:  py orphan_02.py
"""
import sys, json, re, collections
from pathlib import Path
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X

HERE = Path(__file__).parent
census = json.loads((HERE / "out" / "prefab_census.json").read_text())


def recs(d, lod, x, y, part):
    try:
        bm = X.read_block(x, y, disc=d, lod=lod, part=part)
    except ValueError:
        return None
    V, UV = bm.verts, bm.uvs or [[0, 0]] * len(bm.verts)
    TA = bm.tangents or [[0] * 4] * len(bm.verts)
    c = collections.Counter()
    for t in bm.tris:
        c[(tuple(sorted((tuple(round(q, 3) for q in V[k]), tuple(round(q, 4) for q in UV[k])) for k in t)), int(TA[t[0]][0]))] += 1
    return c


res = {}
for d in (1, 4):
    env = X._worldmap_env(d)
    conts = [(getattr(o, "container", "") or "").lower() for o in env.objects]
    all02 = sorted({c for c in conts if f"worldmap/disc{d}/0_2/" in c})
    refd = {v["mesh"] for r in census[str(d)] for v in r["slots"].values()}
    orphans = [c for c in all02 if c.replace("assets/resources/", "") not in refd]
    tally = collections.Counter()
    rows = []
    for c in orphans:
        m = re.search(r"/r(\d+)/block\[(\d+)\]\[(\d+)\] (\w+)\.asset$", c)
        y, x, part = int(m.group(1)), int(m.group(2)), m.group(4)
        a, b = recs(d, "0_1", x, y, part), recs(d, "0_2", x, y, part)
        sw = any(r["IsSwitchable"] and (r["x"], r["y"]) == (x, y) for r in census[str(d)])
        verdict = "no-0_1-twin" if a is None else ("IDENTICAL" if a == b else f"DIFFERS(-{sum((a - b).values())}/+{sum((b - a).values())})")
        tally[verdict.split("(")[0]] += 1
        rows.append([x, y, part, sw, verdict])
    print(f"disc{d}: 0_2 meshes={len(all02)} referenced-by-prefab={len(all02) - len(orphans)} orphans={len(orphans)} -> {dict(tally)}")
    print("   orphans on non-switchable cells:", [(x, y, p) for x, y, p, sw, v in rows if not sw])
    for x, y, p, sw, v in rows:
        if v != "IDENTICAL":
            print(f"   ({x},{y}) {p}: {v}  switchable={sw}")
    res[str(d)] = rows
(HERE / "out" / "orphan_02.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
