"""V4 DONOR DETAIL -- everything the transplant plan needs to know about (5-7, 15-16).

Per block: full part list + tri counts; event ids on terrain tris (de-quest scope);
the object part's anchor + bounds; the falls/river/riverjoint mesh stats; the two
N-neck crossings' exact tris. Run from the repo root.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                   # noqa: E402

BLOCKS = [(5, 15), (6, 15), (7, 15), (5, 16), (6, 16), (7, 16)]
import re
env = X._worldmap_env(1)
pat = re.compile(r"worldmap/disc1/0_1/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9]+)(?:\.asset)?$")
parts = defaultdict(set)
for k in env.container:
    m = pat.search((k or "").lower())
    if m:
        parts[(int(m.group(1)), int(m.group(2)))].add(m.group(3))

for b in BLOCKS:
    print(f"\n== block {b}: parts {sorted(parts.get(b, ()))}")
    for part in sorted(parts.get(b, ())):
        try:
            pm = X.read_block(b[0], b[1], disc=1, part=part)
        except Exception as e:
            print(f"   {part}: READ FAIL {e}")
            continue
        V = np.asarray(pm.verts, dtype=np.float64)
        ntri = len(pm.flat_index) // 3
        print(f"   {part:10} {ntri:4} tris  x[{V[:,0].min():6.1f},{V[:,0].max():6.1f}] "
              f"y[{V[:,1].min():6.1f},{V[:,1].max():6.1f}] z[{V[:,2].min():7.1f},{V[:,2].max():6.1f}]")
        if part == "terrain":
            T = np.asarray(pm.tangents, dtype=np.float64)
            idx = np.asarray(pm.flat_index, dtype=np.int64).reshape(-1, 3)
            evs = Counter()
            for i in idx[:, 0]:
                d = X.decode_id(int(round(T[i][0])))
                key = tuple(sorted(d.items()))
                evs[key] += 1
            # show the decode fields once, then any tri whose decode has a nonzero
            # field OTHER than topograph/shade-ish keys
            sample = X.decode_id(int(round(T[idx[0][0]][0])))
            print(f"      decode fields: {sorted(sample.keys())}")
            interesting = Counter()
            for key, n in evs.items():
                d = dict(key)
                extra = {k: v for k, v in d.items() if k != "topograph" and v}
                if extra:
                    interesting[(d.get('topograph'), tuple(sorted(extra.items())))] += n
            for (topo, extra), n in sorted(interesting.items()):
                print(f"      topo {topo} + {dict(extra)}: {n} tris")
