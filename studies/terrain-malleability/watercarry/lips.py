"""Do the bay's two rocky lips and the kit island's lip share a profile a lip-to-lip join could meet?

R1's remaining problem (RECON.md R1): the mouth's smallest closed assembly is the ~157u bay, beach arcs lip to lip, so
seating it on a kit island means joining a stock cliff to the kit's minted cliff at each lip. THE LAW (coast-mosaic):
independently authored cliffs never meet cleanly. Before building anything, measure each side's wall in the terms
the coast laws name, per wall (topo 58) tri near each lip and round the kit island's ring:
  CREST / BASE  heights of the wall's top verts (welded to land) and its foot verts (welded to water, or the lowest)
  RUN / SLOPE   the crest-to-base plan distance per tri, and the tri's angle from horizontal
  V             the wall's v at crest and at base (THE WALL V CORNER-ROLE LAW: grass crest 0.8926, base 0.9229)
  U DENSITY     |du| per unit of along-shore crest length (the kit mints 0.0125/u; THE COLUMN QUANTIZATION LAW)
  LAND / WATER  the topographs on top of the crest; the water parts welded to the foot (THE RING LADDER)
Stock lips: the far ends of the two beach arcs (mouth.py): E (1133, -1010), W (1035, -1055), wall tris within 30u.
Kit: the r90 grass bench (seat_dryrun.py's), every wall tri; its live water is the cut Sea4 sheet (island.py
HIDDEN_PARTS hides Sea1/2/3/5 and Beach1).
RUN:  py studies/terrain-malleability/watercarry/lips.py   (writes out/lips.json)
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import extract as X  # noqa: E402
from ff9mapkit.world.interior import kk3  # noqa: E402
from ff9mapkit.world.island import build_landmass  # noqa: E402
import seat_dryrun as S  # noqa: E402

LIPS = {"E": (1133.0, -1010.0), "W": (1035.0, -1055.0)}
NEAR = 30.0
WATER_PARTS = ("sea1", "sea2", "sea3", "sea4", "sea5", "beach1")


def stats(v):
    v = np.asarray(v, dtype=float)
    if not len(v):
        return None
    return {"n": int(len(v)), "p10": round(float(np.percentile(v, 10)), 3), "p50": round(float(np.median(v)), 3),
            "p90": round(float(np.percentile(v, 90)), 3)}


def profile(walls, others):
    """walls: wall tris (dicts: P, uv, topo, part); others: every other tri in reach (land + water)."""
    land_keys, water_keys = defaultdict(set), defaultdict(set)
    for t in others:
        for p in t["P"]:
            k = kk3(p)
            if t["part"] in WATER_PARTS:
                water_keys[k].add(t["part"])
            elif t["topo"] != 58:
                land_keys[k].add(t["topo"])
    crest_y, base_y, crest_v, base_v, runs, slopes, udens = [], [], [], [], [], [], []
    land_top, water_foot = Counter(), Counter()
    for t in walls:
        P, UV = t["P"], t["uv"]
        crest = [i for i in range(3) if kk3(P[i]) in land_keys]
        base = [i for i in range(3) if kk3(P[i]) in water_keys] or ([int(np.argmin(P[:, 1]))] if not crest else [])
        for i in crest:
            crest_y.append(P[i][1])
            crest_v.append(UV[i][1])
            land_top.update(land_keys[kk3(P[i])])
        for i in base:
            base_y.append(P[i][1])
            base_v.append(UV[i][1])
            water_foot.update(water_keys.get(kk3(P[i]), {"(none)"}))
        if crest and base:
            runs.append(min(math.hypot(P[a][0] - P[b][0], P[a][2] - P[b][2]) for a in crest for b in base))
        n = np.cross(P[1] - P[0], P[2] - P[0])
        ln = float(np.linalg.norm(n))
        if ln > 1e-9:
            slopes.append(math.degrees(math.acos(min(1.0, abs(float(n[1])) / ln))))
        if len(crest) == 2:
            a, b = crest
            L = math.hypot(P[a][0] - P[b][0], P[a][2] - P[b][2])
            if L > 0.05:
                udens.append(abs(UV[a][0] - UV[b][0]) / L)
    return {"wall_tris": len(walls), "crest_y": stats(crest_y), "base_y": stats(base_y), "run": stats(runs),
            "slope_deg": stats(slopes), "crest_v": stats(crest_v), "base_v": stats(base_v), "u_per_unit": stats(udens),
            "land_on_top": dict(land_top.most_common(5)), "water_at_foot": dict(water_foot.most_common(6))}


def main():
    bp = X.block_parts(disc=1)
    stock = []
    for bx in range(14, 19):
        for by in range(14, 18):
            for part in ("terrain",) + WATER_PARTS:
                if part in bp.get((bx, by), ()):
                    stock += S.tris_uv(bx, by, part)
    out = {"stock": {}, "kit": {}}
    for name, (lx, lz) in LIPS.items():
        near = [t for t in stock if math.hypot(t["P"][:, 0].mean() - lx, t["P"][:, 2].mean() - lz) <= NEAR]
        walls = [t for t in near if t["part"] == "terrain" and t["topo"] == 58]
        wid = {id(t) for t in walls}
        out["stock"][name] = profile(walls, [t for t in near if id(t) not in wid])
    built = build_landmass(center=S.BENCH_C, base_radius=S.BENCH_R, seed=S.SEED, lobes=1, n_patches=0, ground="grass")
    kit = []
    for (bx, by), bm in built["blocks"].items():
        V = np.asarray(bm.chan_arrays[X.CH_POS], dtype=float) + np.array([64.0 * bx, 0.0, -64.0 * by])
        U = np.asarray(bm.chan_arrays[X.CH_UV], dtype=float)
        tan = bm.chan_arrays[X.CH_TAN]
        for t in bm.tris:
            idall = int(round(tan[t[0]][0]))
            kit.append({"P": V[t], "uv": U[t], "part": "terrain", "topo": X.decode_id(idall)["topograph"]})
    walls = [t for t in kit if t["topo"] == 58]
    out["kit"]["ring"] = profile(walls, [t for t in kit if t["topo"] != 58])
    print(json.dumps(out, indent=1))
    (HERE / "out" / "lips.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
