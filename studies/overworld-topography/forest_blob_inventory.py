"""Enumerate GEOMETRIC forest blobs (position-connected topo-37 patches) across
donor blocks -- size, extent, rim height stats -- to pick one carryable blob."""
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X

for (bx, by) in ((19, 13), (17, 14), (15, 15), (16, 14), (14, 15)):
    bm = X.read_block(bx, by)
    v = np.asarray(bm.verts, dtype=np.float64)
    tan = bm.tangents
    topo = [X.decode_id(int(tan[t[0]][0]))["topograph"] for t in bm.tris]
    key = lambda i: (round(v[i][0], 3), round(v[i][1], 3), round(v[i][2], 3))
    ftris = [t for t in range(len(bm.tris)) if topo[t] == 37]
    pos_tris = defaultdict(list)
    for t in ftris:
        for i in bm.tris[t]:
            pos_tris[key(i)].append(t)
    parent = {t: t for t in ftris}
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for lst in pos_tris.values():
        for b in lst[1:]:
            parent[find(b)] = find(lst[0])
    blobs = defaultdict(list)
    for t in ftris:
        blobs[find(t)].append(t)
    print(f"\nblock ({bx},{by}): {len(ftris)} forest tris in {len(blobs)} blobs")
    for cid, tris_ in sorted(blobs.items(), key=lambda kv: -len(kv[1]))[:3]:
        pts = np.array([v[i] for t in tris_ for i in bm.tris[t]])
        # rim = positions also used by non-forest tris
        all_pos = defaultdict(set)
        for t, tri in enumerate(bm.tris):
            for i in tri:
                all_pos[key(i)].add(topo[t])
        rim_h = [v[bm.tris[t][k]][1] for t in tris_ for k in range(3)
                 if len(all_pos[key(bm.tris[t][k])] - {37}) > 0]
        nb = set()
        for t in tris_:
            for i in bm.tris[t]:
                nb |= (all_pos[key(i)] - {37})
        print(f"  blob {len(tris_)} tris: x {pts[:,0].min():.0f}..{pts[:,0].max():.0f} "
              f"z {pts[:,2].min():.0f}..{pts[:,2].max():.0f} "
              f"(extent {pts[:,0].max()-pts[:,0].min():.0f}x{pts[:,2].max()-pts[:,2].min():.0f}u) "
              f"h {pts[:,1].min():.1f}..{pts[:,1].max():.1f} rim h {min(rim_h):.1f}..{max(rim_h):.1f} "
              f"neighbours {sorted(nb)}")
