"""How does a stock water part sit in its ground? Per water part (Stream / River / RiverJoint / Falls), on its own block
plus the 8 around it:
  HOLE   -- of the part's own plan footprint, how much has NO Terrain under it (down-ray on Terrain alone)?
            A part that plugs a hole (as every stock building plugs one: forms/object2_census.py) reads ~100%.
  WELD   -- of the part's boundary vertices, how many coincide (kk3) with a Terrain vertex, or with another water part?
  BELOW  -- where Terrain IS under the part, how far below the water surface it sits (a channel bed) or above (overlay).
  BANK   -- the topographs of the Terrain tris that share a vertex with the part (what ground a stream meets).
RUN:  py studies/terrain-malleability/watercarry/anatomy.py   (writes out/anatomy.json)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import extract as X  # noqa: E402
from ff9mapkit.world.interior import kk3  # noqa: E402

WATER = ("stream", "river", "riverjoint", "falls")


def world_tris(bx, by, part):
    try:
        bm = X.read_block(bx, by, disc=1, part=part)
    except Exception:                                                           # noqa: BLE001
        return None
    V = np.asarray(bm.verts, dtype=float) + np.array([64.0 * bx, 0.0, -64.0 * by])
    T = np.asarray(bm.tris, dtype=int)
    tan = bm.chan_arrays[X.CH_TAN]
    topo = np.array([X.decode_id(int(round(tan[t[0]][0])))["topograph"] for t in T])
    return V[T], topo


def down_hits(TRI, x, z):
    a, b, c = TRI[:, 0], TRI[:, 1], TRI[:, 2]
    den = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])
    ok = np.abs(den) > 1e-12
    with np.errstate(divide="ignore", invalid="ignore"):
        l1 = ((b[:, 2] - c[:, 2]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (z - c[:, 2])) / den
        l2 = ((c[:, 2] - a[:, 2]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (z - c[:, 2])) / den
    l3 = 1 - l1 - l2
    hit = ok & (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
    y = l1 * a[:, 1] + l2 * b[:, 1] + l3 * c[:, 1]
    return y[hit]


def samples(TRI, n=4):
    pts = []
    for t in TRI:
        for i in range(1, n):
            for j in range(1, n - i):
                k = n - i - j
                p = (t[0] * i + t[1] * j + t[2] * k) / n
                pts.append(p)
    return np.array(pts)


def main():
    census = json.loads((HERE / "out" / "census.json").read_text(encoding="utf-8"))
    out = {}
    for key in census["water_parts"]:
        bx, by, part = key.split(",")
        bx, by = int(bx), int(by)
        if part not in WATER:
            continue
        own = world_tris(bx, by, part)
        if own is None:
            continue
        TRI, _ = own
        terr, ttopo, other = [], [], []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                t = world_tris(bx + dx, by + dy, "terrain")
                if t is not None:
                    terr.append(t[0])
                    ttopo.append(t[1])
                for p2 in WATER:
                    if (dx, dy, p2) != (0, 0, part):
                        w = world_tris(bx + dx, by + dy, p2)
                        if w is not None:
                            other.append(w[0])
        TT = np.concatenate(terr)
        TP = np.concatenate(ttopo)
        S = samples(TRI)
        none, below = 0, []
        for p in S:
            ys = down_hits(TT, p[0], p[2])
            if len(ys) == 0:
                none += 1
            else:
                below.append(float(p[1] - ys.max()))
        # boundary verts of the part, and what they weld to
        edges = Counter()
        for t in TRI:
            for a, b in ((0, 1), (1, 2), (2, 0)):
                edges[tuple(sorted((kk3(t[a]), kk3(t[b]))))] += 1
        bnd = {k for e, n in edges.items() if n == 1 for k in e}
        tkeys = {kk3(v) for t in TT for v in t}
        okeys = {kk3(v) for o in other for t in o for v in t} if other else set()
        bank = Counter()
        for ti, t in enumerate(TT):
            if any(kk3(v) in bnd for v in t):
                bank[int(TP[ti])] += 1
        below_a = np.array(below) if below else np.array([np.nan])
        rec = {"tris": int(len(TRI)), "samples": int(len(S)), "no_terrain_pct": round(100.0 * none / len(S), 1),
               "water_minus_terrain": {"p05": round(float(np.nanpercentile(below_a, 5)), 2),
                                       "p50": round(float(np.nanpercentile(below_a, 50)), 2),
                                       "p95": round(float(np.nanpercentile(below_a, 95)), 2)},
               "boundary_verts": len(bnd), "weld_terrain": len(bnd & tkeys), "weld_other_water": len(bnd & okeys),
               "bank_topos": dict(bank.most_common(6))}
        out[key] = rec
        print(f"({bx:2d},{by:2d}) {part:10s} {rec['tris']:3d} tris: no Terrain under {rec['no_terrain_pct']:5.1f}% | "
              f"water - terrain p05/50/95 {rec['water_minus_terrain']['p05']}/{rec['water_minus_terrain']['p50']}/"
              f"{rec['water_minus_terrain']['p95']} | boundary {rec['boundary_verts']} -> Terrain {rec['weld_terrain']}, "
              f"water {rec['weld_other_water']} | bank {rec['bank_topos']}")
    (HERE / "out" / "anatomy.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
