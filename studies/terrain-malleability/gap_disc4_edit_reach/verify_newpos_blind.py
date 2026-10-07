"""VERIFY (adversarial) -- G7: what fraction of disc-4-only terrain tris is truly INVISIBLE to a vertex-position
closure test?

s6 B reports 8,616 / 13,746 (63%) disc-4-only terrain tris with AT LEAST ONE corner at a position no disc-1 vertex
of the cell has. But a vertex-closure delta (lib.delta_transfer ring 0/1) refuses an edit as soon as ANY moved
disc-1 position coincides with ANY corner of an unmatched tri -- so a disc-4-only tri with even one corner on an
old (disc-1) position is still visible whenever that corner moves. The tris that can be missed regardless of
the edit are those with ALL THREE corners at new positions. Count both, plus the per-corner breakdown.
Read-only on the lane cache. Writes out/verify_newpos_blind.json.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402
import numpy as np                                    # noqa: E402

data = L.load_cache()
meshes, pairs = data["meshes"], data["pairs"]
hist = Counter()
topo_all_new = Counter()
for (x, y, p), pr in pairs.items():
    if p != "terrain" or pr["perm"]:
        continue
    m4, m1 = meshes[(4, x, y, p)], meshes[(1, x, y, p)]
    V, T, I = m4["V"], m4["T"], m4["idall"]
    d1pos = {m1["V"][vi].tobytes() for vi in range(len(m1["V"]))}
    for t in np.nonzero(~pr["m4"])[0]:
        n_new = sum(1 for vi in T[t] if V[vi].tobytes() not in d1pos)
        hist[n_new] += 1
        if n_new == 3:
            topo_all_new[L.topo(int(I[t]))] += 1
tot = sum(hist.values())
res = {"d4only_tris": tot, "by_new_corner_count": {str(k): v for k, v in sorted(hist.items())},
       "any_new": tot - hist[0], "all_three_new": hist[3], "all_three_new_share": round(hist[3] / tot, 4),
       "all_three_new_topographs": dict(topo_all_new.most_common(8))}
print(json.dumps(res, indent=1))
(L.OUT / "verify_newpos_blind.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
