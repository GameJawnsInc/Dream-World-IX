"""CAPACITY lane, step 11 -- THE ADDED-TRIS CPU COST MODEL, simulated offline: how the controlled walker's
ground-query work per tick scales when a block's terrain is uniformly refined.

Model = the stock query path (WMBlock.cs:137-183 cache ring + full scan; WMPhysics.cs:13-46), reduced to plan:
  * per tick the walker probes its next (x,z) (on foot 0.4375 u/tick, walk-decode-claims.md step 1);
  * CACHE: 10-slot ring, probe newest slot first then oldest->second-newest (WALK-QUERY-DECODE.md CACHE LAW);
    a slot answers iff its triangle still contains the plan point (no filters on this path);
  * else FULL SCAN in registration order (scan_cost.block_soup), first eligible containing tri wins, cost =
    tris iterated; the hit is written to slot (Number+1)%10.
The 2-probe snap and the deflection fan multiply both arms equally and are left out (ratios are what matter).

Refinement: every tri -> 4 by edge midpoints, applied r times (tris x4^r, edge /2^r), children emitted in place
(emit-order locality preserved -- a real builder's emit order can only be worse or equal for scan depth).

Calibration: at r=0 the per-probe first hit must agree with scan_cost.first_hits on the same points (asserted).

Writes out/walk_cost_sim.json.  Run:  py studies/terrain-malleability/capacity/walk_cost_sim.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ff9mapkit.world import extract as X  # noqa: E402
from census import PAT  # noqa: E402
from scan_cost import block_soup, first_hits  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
BLOCKS = [(15, 14), (18, 13), (12, 16)]          # a median-ish, the densest terrain, a mid block
STEP = 0.4375
RNG = np.random.default_rng(9)


def refine(A, B, C, ex):
    ab, bc, ca = (A + B) / 2, (B + C) / 2, (C + A) / 2
    nA = np.stack([A, ab, ca, ab], 1).reshape(-1, 3)
    nB = np.stack([ab, B, bc, bc], 1).reshape(-1, 3)
    nC = np.stack([ca, bc, C, ca], 1).reshape(-1, 3)
    return nA, nB, nC, np.repeat(ex, 4)


def contains(A, B, C, i, p):
    a, b, c = A[i], B[i], C[i]
    v0, v1, v2 = c[[0, 2]] - a[[0, 2]], b[[0, 2]] - a[[0, 2]], p - a[[0, 2]]
    d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01
    if abs(den) < 1e-12:
        return False
    u = (d11 * d20 - d01 * d21) / den
    v = (d00 * d21 - d01 * d20) / den
    return u >= -1e-9 and v >= -1e-9 and u + v <= 1 + 1e-9


def walk(A, B, C, ex, paths):
    ring = [-1] * 10
    num = 0
    scans = tests = probes = 0
    for pts in paths:
        parts = [first_hits(A, B, C, ex, pts[j:j + 16]) for j in range(0, len(pts), 16)]   # chunked (memory)
        idx = np.concatenate([q[0] for q in parts])
        hit = np.concatenate([q[1] for q in parts])
        for k, p in enumerate(pts):
            probes += 1
            order = [(num + i) % 10 for i in range(10)]
            cached = False
            for s in order:
                t = ring[s]
                if t >= 0 and contains(A, B, C, t, p):
                    cached = True
                    tests += 1
                    break
                if t >= 0:
                    tests += 1
            if cached:
                continue
            scans += 1
            tests += int(min(idx[k] + 1, len(A)))
            if hit[k]:
                num = (num + 1) % 10
                ring[num] = int(idx[k])
    return {"probes": probes, "full_scans": scans, "scan_rate": round(scans / probes, 4),
            "tri_tests_per_probe": round(tests / probes, 1)}


def main():
    env = X._worldmap_env(1)
    meshes = {}
    for c, o in X._mesh_index(env).items():
        m = PAT.search(c)
        if m and int(m.group(1)) == 1 and m.group(2) == "0_1":
            meshes[(int(m.group(4)), int(m.group(3)), m.group(6))] = o
    res = {}
    for (bx, by) in BLOCKS:
        A, B, C, ex, part = block_soup(meshes, bx, by)
        # 60 straight walks of 120 ticks across the land part of the block (start on a hit point)
        paths = []
        while len(paths) < 60:
            s = RNG.uniform([4, -60], [60, -4])
            ang = RNG.uniform(0, 2 * np.pi)
            d = np.array([np.cos(ang), np.sin(ang)]) * STEP
            pts = s + np.outer(np.arange(120), d)
            pts = pts[(pts[:, 0] > 0.5) & (pts[:, 0] < 63.5) & (pts[:, 1] < -0.5) & (pts[:, 1] > -63.5)]
            if len(pts) >= 40:
                paths.append(pts)
        rows = []
        for r in range(4):
            if r:
                A, B, C, ex = refine(A, B, C, ex)
            if r == 0:   # calibration: reuse of first_hits is the instrument; spot-check vs brute force
                i0, h0 = first_hits(A, B, C, ex, paths[0][:5])
                for k in range(5):
                    bf = next((t for t in range(len(A)) if ex[t] and contains(A, B, C, t, paths[0][k])), len(A))
                    assert (bf == i0[k]) or (not h0[k] and bf == len(A)), "first_hits disagrees with brute force"
            out = walk(A, B, C, ex, paths)
            out.update({"refine": r, "tris": int(len(A)), "edge_scale": 1 / 2 ** r})
            rows.append(out)
            print((bx, by), out)
        base = rows[0]["tri_tests_per_probe"]
        for row in rows:
            row["cost_x_vs_stock"] = round(row["tri_tests_per_probe"] / base, 1)
        res[f"{bx},{by}"] = rows
    (OUT / "walk_cost_sim.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, rows in res.items():
        print(k, [(r["tris"], r["scan_rate"], r["tri_tests_per_probe"], r["cost_x_vs_stock"]) for r in rows])


if __name__ == "__main__":
    main()
