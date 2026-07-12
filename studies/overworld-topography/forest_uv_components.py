"""FOREST LOBE HYPOTHESIS: cluster forest tris into UV-CONTINUITY components
(adjacent tris connected iff their shared weld positions carry matching UVs).
Measure: component count/size, per-component affine UV fit + scale, and whether
component BOUNDARIES sit in height creases (local minima)."""
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X

for (bx, by) in ((19, 13), (17, 14)):
    bm = X.read_block(bx, by)
    v = np.asarray(bm.verts, dtype=np.float64)
    uv = np.asarray(bm.uvs, dtype=np.float64)
    tan = bm.tangents
    topo = [X.decode_id(int(tan[t[0]][0]))["topograph"] for t in bm.tris]
    key = lambda i: (round(v[i][0], 3), round(v[i][1], 3), round(v[i][2], 3))
    ftris = [t for t in range(len(bm.tris)) if topo[t] == 37]
    fset = set(ftris)

    # adjacency via shared weld positions, with UV-match test
    pos_tris = defaultdict(list)
    for t in ftris:
        for i in bm.tris[t]:
            pos_tris[key(i)].append((t, i))
    parent = {t: t for t in ftris}
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    def union(a, b):
        parent[find(a)] = find(b)
    n_match_links = n_links = 0
    for p, lst in pos_tris.items():
        for ai in range(len(lst)):
            for bi in range(ai + 1, len(lst)):
                (t1, i1), (t2, i2) = lst[ai], lst[bi]
                if t1 == t2:
                    continue
                n_links += 1
                if abs(uv[i1][0] - uv[i2][0]) < 5e-4 and abs(uv[i1][1] - uv[i2][1]) < 5e-4:
                    union(t1, t2)
                    n_match_links += 1
    comps = defaultdict(list)
    for t in ftris:
        comps[find(t)].append(t)
    sizes = sorted((len(c) for c in comps.values()), reverse=True)
    print(f"\nblock ({bx},{by}): {len(ftris)} forest tris -> {len(comps)} UV-continuity components; "
          f"sizes {sizes[:12]}...  (links matched {n_match_links}/{n_links})")

    # per-component affine fit + scale (components with >= 6 tris)
    for cid, tris_ in sorted(comps.items(), key=lambda kv: -len(kv[1]))[:5]:
        if len(tris_) < 6:
            break
        rowsP, rowsQ = [], []
        for t in tris_:
            for i in bm.tris[t]:
                rowsP.append([v[i][0], v[i][2], 1.0])
                rowsQ.append([uv[i][0], uv[i][1]])
        P, Q = np.array(rowsP), np.array(rowsQ)
        coef, *_ = np.linalg.lstsq(P, Q, rcond=None)
        err = np.abs(P @ coef - Q)
        # singular values of the 2x2 jacobian = texel scale range
        J = coef[:2, :] * 1024.0
        sv = np.linalg.svd(J, compute_uv=False)
        print(f"  comp {len(tris_)} tris: affine max err ({err[:,0].max():.4f},{err[:,1].max():.4f}) "
              f"texels/u sv {sv[0]:.1f}/{sv[1]:.1f}")

    # crease correlation: multi-UV positions vs local height rank
    heights = {p: v[lst[0][1]][1] for p, lst in pos_tris.items()}
    nbr = defaultdict(set)
    for t in ftris:
        ks = [key(i) for i in bm.tris[t]]
        for a in ks:
            nbr[a].update(k for k in ks if k != a)
    lo_multi = lo_single = hi_multi = hi_single = 0
    for p, lst in pos_tris.items():
        uvs = {(round(uv[i][0], 4), round(uv[i][1], 4)) for _, i in lst}
        ns = [heights[q] for q in nbr[p] if q in heights]
        if len(ns) < 2:
            continue
        is_low = heights[p] <= np.percentile(ns, 30)
        if len(uvs) > 1:
            lo_multi += is_low; hi_multi += (not is_low)
        else:
            lo_single += is_low; hi_single += (not is_low)
    print(f"  seam positions: {lo_multi} in creases vs {hi_multi} on highs; "
          f"continuous positions: {lo_single} creases vs {hi_single} highs")
