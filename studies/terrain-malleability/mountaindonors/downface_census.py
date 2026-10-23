"""THE STOCK DOWN-FACE CENSUS: how many shipping disc-1 Terrain tris face down, by how much, and of what.

carve_mountain's geometry gate refuses ANY new tri whose geometric normal points down (cross.y < 0), verbatim donor rock
included. comp10 trips it on two STOCK tris that lean past vertical by a hair (ny -0.007 canopy wall, -0.003 rock;
STEP.md). Before the gate can exempt a verbatim stock tri "near vertical", this measures what stock holds: every
disc-1 Terrain tri, its unit normal's y (the geometric winding the engine's ground query uses), bucketed, per
topograph, with the steepest examples. A threshold is lawful only if it sits inside a quiet band of this histogram:
it must admit the near-vertical walls and still refuse a genuinely flipped tri (ny near -1).
Writes out/downface_census.json.  RUN:  py studies/terrain-malleability/mountaindonors/downface_census.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sweep as S  # noqa: E402  (the worktree-pinned kit import)

EDGES = (-1.0, -0.5, -0.2, -0.1, -0.05, -0.02, -0.01, -0.005, -0.002, -0.001, 0.0)


def main():
    S._kit()
    from ff9mapkit.world import extract as X
    total, down = 0, []
    for bx in range(24):
        for by in range(20):
            try:
                bm = X.read_block(bx, by, disc=1)
            except Exception:                                          # noqa: BLE001
                continue
            V = np.asarray(bm.verts, float)
            fi = np.asarray(bm.flat_index).reshape(-1, 3)
            P = V[fi]
            n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
            L = np.linalg.norm(n, axis=1)
            ok = L > 1e-12
            ny = np.where(ok, n[:, 1] / np.where(ok, L, 1.0), 0.0)
            total += int(ok.sum())
            for t in np.where(ok & (ny < 0))[0]:
                topo = X.decode_id(int(round(bm.tangents[fi[t][0]][0])))["topograph"]
                down.append({"block": [bx, by], "tri": int(t), "ny": round(float(ny[t]), 6), "topo": topo,
                             "area": round(float(L[t]) / 2, 4),
                             "centre": [round(float(v), 2) for v in P[t].mean(0) + (64 * bx, 0, -64 * by)]})
    hist = Counter()
    for d in down:
        for lo, hi in zip(EDGES[:-1], EDGES[1:]):
            if lo <= d["ny"] < hi:
                hist[f"[{lo}, {hi})"] += 1
                break
    by_topo = defaultdict(list)
    for d in down:
        by_topo[d["topo"]].append(d["ny"])
    out = {"terrain_tris": total, "down_tris": len(down),
           "histogram": {f"[{lo}, {hi})": hist.get(f"[{lo}, {hi})", 0) for lo, hi in zip(EDGES[:-1], EDGES[1:])},
           "by_topo": {str(k): {"n": len(v), "min_ny": min(v)} for k, v in sorted(by_topo.items())},
           "steepest": sorted(down, key=lambda d: d["ny"])[:15], "all": down}
    print(f"disc 1: {total} Terrain tris, {len(down)} face down")
    for k, v in out["histogram"].items():
        print(f"   ny in {k:18s} {v}")
    print("   by topograph:", {k: v for k, v in out["by_topo"].items()})
    print("   steepest:", [(d["ny"], d["topo"], d["block"], d["area"]) for d in out["steepest"][:8]])
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "downface_census.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
