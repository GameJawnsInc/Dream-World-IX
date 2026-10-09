"""LAND -> SEA, the coastal-water reach (2026-10-09): how far from land does stock put its coastal sea ids?

Stock deep sea (sea4) carries topograph 57 in open water and 53-56 near coasts (coastnav's names: 53 BEACH landing,
54 CLIFF, 55 BELT, 56 KEEL; the Blue Narciss sails only on 53/54/57). Disc 4's Shimmering Island sink re-id'd its
topo-56 ring to 57 along with the fill, or a boat could not cross where the island was. The sink re-ids a coastal tri
only when no remaining land is within the reach stock gives these ids; this measures that reach: for every disc-1
sea4 tri, the plan distance from its centroid to the nearest land tri (terrain or beach1, the 3x3 blocks round it).
Writes out/keel_reach.json.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/keel_reach.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))


def seg_dist(p, a, b):
    """Distances from points p (N,2) to segments a-b (M,2): (N, M)."""
    ab = b - a
    L = (ab ** 2).sum(1)
    L[L == 0] = 1e-12
    t = ((p[:, None, :] - a[None]) * ab[None]).sum(2) / L[None]
    t = np.clip(t, 0, 1)
    q = a[None] + t[..., None] * ab[None]
    return np.sqrt(((p[:, None, :] - q) ** 2).sum(2))


def main():
    import ff9mapkit
    from ff9mapkit.world import extract as X, transplant as TR
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    blocks = sorted(X.list_blocks(disc=1))
    land, sea = {}, {}
    for b in blocks:
        land[b] = TR.world_tris(*b, "terrain", disc=1) + TR.world_tris(*b, "beach1", disc=1)
        sea[b] = TR.world_tris(*b, "sea4", disc=1)
    by_topo = defaultdict(list)
    for (bx, by) in blocks:
        if not sea[(bx, by)]:
            continue
        segs = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for t in land.get((bx + dx, by + dy), ()):
                    pts = [(v[0][0], v[0][2]) for v in t]
                    segs += [(pts[i], pts[(i + 1) % 3]) for i in range(3)]
        cents = np.array([TR._plan_centroid(t) for t in sea[(bx, by)]])
        topo = [X.decode_id(int(round(t[0][3][0])))["topograph"] for t in sea[(bx, by)]]
        if segs:
            s = np.array(segs)
            d = np.empty(len(cents))
            for k in range(0, len(cents), 256):
                d[k:k + 256] = seg_dist(cents[k:k + 256], s[:, 0], s[:, 1]).min(1)
        else:
            d = np.full(len(cents), np.inf)
        for tp, dd in zip(topo, d):
            by_topo[tp].append(float(dd))
    res = {}
    for tp, ds in sorted(by_topo.items()):
        a = np.array(ds)
        f = a[np.isfinite(a)]
        res[tp] = {"n": len(a), "far": int((~np.isfinite(a)).sum()),
                   "p50": round(float(np.percentile(f, 50)), 2) if len(f) else None,
                   "p99": round(float(np.percentile(f, 99)), 2) if len(f) else None,
                   "max": round(float(f.max()), 2) if len(f) else None,
                   "min": round(float(f.min()), 2) if len(f) else None}
        print(tp, res[tp])
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "keel_reach.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
