"""VERIFIER for V9 and V10 (read-only).

V9 says the off-zero sea1/sea2/sea3 verts are "coastal rims, ramps toward land ... under the land rim". The lane's
own probe only looked for Terrain in the SAME block within 0.5u (192 of 232 raised sea2 verts found none). Here every
raised sea vertex (|y| > 0.05) is placed in WORLD coordinates and checked against Terrain of the 3x3 block
neighbourhood: the nearest terrain vertex (plan distance) and the max terrain sheet within 2u / 4u.

V10 scans only blocks whose TERRAIN dips below 0. Here: every block whose ANY registered part has a vertex < -0.05,
and the engine ground (calibrated kit simulator, registration order) over a 0.5u grid -- is there sub-zero,
foot-legal ground in a block the lane did not scan?

Writes out/verify_sea_rim_and_subzero.json.
Run: py studies/terrain-malleability/vertical/verify_sea_rim_and_subzero.py
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
import numpy as np                                   # noqa: E402
from ff9mapkit.world import extract as X             # noqa: E402
from ff9mapkit.world import placement as P           # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
res = {}


def block_parts(disc):
    env = X._worldmap_env(disc)
    pat = re.compile(rf"worldmap/disc{disc}/0_1/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
    per = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            per[(int(m.group(1)), int(m.group(2)))].add(m.group(3))
    return per


for disc in (1, 4):
    bp = block_parts(disc)
    terr_cache = {}

    def terrain_world(bx, by):
        if (bx, by) in terr_cache:
            return terr_cache[(bx, by)]
        out = None
        if "terrain" in bp.get((bx, by), ()):
            tb = X.read_block(bx, by, disc=disc, part="terrain")
            ox, oz = X.block_world_origin(bx, by)
            V = np.asarray(tb.verts, dtype=float).copy()
            V[:, 0] += ox; V[:, 2] += oz
            out = (V, np.asarray(tb.flat_index, dtype=np.int64).reshape(-1, 3))
        terr_cache[(bx, by)] = out
        return out

    # ---- V9: raised sea verts vs neighbourhood terrain -------------------------------------------------
    rows = Counter()
    dists = defaultdict(list)
    examples = []
    for (bx, by), parts in sorted(bp.items()):
        for part in ("sea1", "sea2", "sea3"):
            if part not in parts:
                continue
            sb = X.read_block(bx, by, disc=disc, part=part)
            V = np.asarray(sb.verts, dtype=float)
            off = np.abs(V[:, 1]) > 0.05
            if not off.any():
                continue
            ox, oz = X.block_world_origin(bx, by)
            W = V[off].copy(); W[:, 0] += ox; W[:, 2] += oz
            neigh = [terrain_world(bx + i, by + j) for i in (-1, 0, 1) for j in (-1, 0, 1)]
            TV = [n[0] for n in neigh if n is not None]
            if not TV:
                for w in W:
                    rows[(part, "no_terrain_in_3x3")] += 1
                continue
            TV = np.concatenate(TV)
            for w in W:
                d = np.hypot(TV[:, 0] - w[0], TV[:, 2] - w[2])
                dmin = float(d.min())
                dists[part].append(dmin)
                near2 = TV[d <= 2.0, 1]
                cls = "terrain_vert_within_2u" if dmin <= 2.0 else ("within_4u" if dmin <= 4.0 else "farther_than_4u")
                rows[(part, cls)] += 1
                if cls == "farther_than_4u" and len(examples) < 10:
                    examples.append({"part": part, "block": [bx, by], "world": [round(w[0], 2), round(w[1], 3), round(w[2], 2)],
                                     "nearest_terrain_vert_u": round(dmin, 2)})
    res[f"disc{disc}_sea_raised_vs_terrain"] = {f"{p}|{c}": n for (p, c), n in sorted(rows.items())}
    res[f"disc{disc}_sea_raised_nearest_terrain_pcts"] = {
        p: {q: round(float(np.percentile(v, q)), 2) for q in (50, 90, 100)} for p, v in dists.items()}
    res[f"disc{disc}_sea_raised_far_examples"] = examples

    # ---- V10: any part below zero, blocks the lane did not scan ---------------------------------------
    lane_blocks = set()
    other = []
    for (bx, by), parts in sorted(bp.items()):
        mins = {}
        for p in parts:
            if P.canonical_part(p) is None:
                continue
            bm = X.read_block(bx, by, disc=disc, part=p)
            if len(bm.verts):
                mins[p] = min(v[1] for v in bm.verts)
        if mins.get("terrain", 0) < 0:
            lane_blocks.add((bx, by))
            continue
        neg = {p: round(m, 3) for p, m in mins.items() if m < -0.05}
        if not neg:
            continue
        if any("volcano" in p for p in parts) or by * 24 + bx == 219:
            other.append({"block": [bx, by], "neg_parts": neg, "skipped": "volcano/water-shrine order"})
            continue
        by_name = {p: X.read_block(bx, by, disc=disc, part=p) for p in parts if P.canonical_part(p) is not None}
        ml = P.build_meshlist(by_name)
        idx = P.build_meshlist_index(ml)
        sub = Counter()
        mn = 0.0
        for i in range(128):
            for j in range(128):
                x, z = (i + 0.5) * 0.5, -(j + 0.5) * 0.5
                g, mesh, idall, topo = P.place(ml, x, z, 0.0, sky=True, index=idx)
                if mesh != "MISS" and g < -1e-6:
                    sub[(mesh, topo, topo in P.WALK_OK)] += 1
                    mn = min(mn, g)
        other.append({"block": [bx, by], "neg_parts": neg, "engine_subzero_samples": sum(sub.values()),
                      "min_ground": round(mn, 3),
                      "winners": {f"{m}/{t}/{'foot' if f else 'nofoot'}": c for (m, t, f), c in sub.items()}})
    res[f"disc{disc}_lane_terrain_subzero_blocks"] = sorted(lane_blocks)
    res[f"disc{disc}_other_subzero_part_blocks"] = other
    print(f"disc {disc}: sea raised vs terrain {res[f'disc{disc}_sea_raised_vs_terrain']}")
    print(f"   nearest-terrain pcts {res[f'disc{disc}_sea_raised_nearest_terrain_pcts']}")
    print(f"   far examples {examples[:4]}")
    print(f"   other sub-zero part blocks: {other}")

(OUT / "verify_sea_rim_and_subzero.json").write_text(json.dumps(res, indent=1, default=str))
print("wrote", OUT / "verify_sea_rim_and_subzero.json")
