"""LAND -> SEA with shallows, question 3 (2026-10-09): which navigation class (topograph) does stock give each water
band, by distance from land?

A sunk island's water has to carry the class of water that has no island in it. Topograph is the engine's navigation
key, not the band: 57 open sea, 53 landable beach-front, 54 cliff-front (both sailable), 55 the standoff belt and 56 the
keel (neither sailable; coastnav.py). For every disc-1 water tri (sea1, sea2, sea3, sea5, sea4): its band, topograph and
the plan distance from its centroid to the nearest land tri (terrain or beach1, the 3x3 blocks round it), binned.
Writes out/sh_q3_topo_reach.json.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sh_q3_topo_reach.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(HERE))
from keel_reach import seg_dist  # noqa: E402

PARTS = ("sea1", "sea2", "sea3", "sea5", "sea4")
BINS = (0, 2, 4, 6, 8, 12, 16, 24, 32, 48, 64, float("inf"), float("nan"))


def main():
    import ff9mapkit
    from ff9mapkit.world import discmirror as DM, extract as X, transplant as TR
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    real = DM._real_parts(1, "0_1")
    land = {b: TR.world_tris(*b, "terrain", disc=1) + TR.world_tris(*b, "beach1", disc=1) for b in real}
    tab = defaultdict(Counter)
    for b in sorted(real):
        segs = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for t in land.get((b[0] + dx, b[1] + dy), ()):
                    pts = [(v[0][0], v[0][2]) for v in t]
                    segs += [(pts[i], pts[(i + 1) % 3]) for i in range(3)]
        s = np.array(segs) if segs else None
        for p in PARTS:
            if p not in real[b]:
                continue
            ts = TR.world_tris(*b, p, disc=1)
            if not ts:
                continue
            cents = np.array([TR._plan_centroid(t) for t in ts])
            if s is None:
                d = np.full(len(ts), np.inf)
            else:
                d = np.empty(len(ts))
                for k in range(0, len(ts), 256):
                    d[k:k + 256] = seg_dist(cents[k:k + 256], s[:, 0], s[:, 1]).min(1)
            for t, dd in zip(ts, d):
                topo = X.decode_id(int(round(t[0][3][0])))["topograph"]
                bi = next((i for i in range(len(BINS) - 2) if BINS[i] <= dd < BINS[i + 1]), len(BINS) - 3)
                tab[(p, f"{BINS[bi]}-{BINS[bi + 1]:g}")][topo] += 1
    res = {f"{p} {r}": dict(c) for (p, r), c in sorted(tab.items(), key=lambda kv: (kv[0][0], float(kv[0][1].split('-')[0])))}
    (HERE / "out" / "sh_q3_topo_reach.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, v in res.items():
        print(f"{k:16s} {dict(sorted(v.items()))}")


if __name__ == "__main__":
    main()
