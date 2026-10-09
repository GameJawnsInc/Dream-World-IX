"""LAND -> SEA with shallows, question 7 (2026-10-09): which navigation class does stock give each tri of a sea5
transition tile?

Away from land a sea5 tri is 54 or 57 (both sailable); about half the tiles carry both. For every disc-1 sea5 lattice
tile of two tris, decoded to its deep-edge-set (transplant.strip_edge_set), all of it sea5 and 54/57: per tri, how many
of the tile's deep edges it borders (a half-tile tri borders two tile edges), and its class. Also, per tile, which
classes it carries. Writes out/sh_q7_sea5_class.json.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sh_q7_sea5_class.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))
PARTS = ("terrain", "beach1", "sea1", "sea2", "sea3", "sea5", "sea4")


def main():
    import ff9mapkit
    from ff9mapkit.world import discmirror as DM, extract as X, transplant as TR
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    real = DM._real_parts(1, "0_1")
    own, s5 = defaultdict(set), defaultdict(list)
    for b in sorted(real):
        for p in PARTS:
            if p not in real[b]:
                continue
            for t in TR.world_tris(*b, p, disc=1):
                c = TR._plan_centroid(t)
                ij = (math.floor(c[0] / 4), math.floor(c[1] / 4))
                own[ij].add(p)
                if p == "sea5":
                    s5[ij].append(t)
    per_tri, per_tile = Counter(), Counter()
    for ij, ts in s5.items():
        if own[ij] != {"sea5"} or len(ts) != 2:
            continue
        d = {TR.strip_edge_set(t) for t in ts}
        if len(d) != 1 or None in d:
            continue
        es = d.pop()
        tops = [X.decode_id(int(round(t[0][3][0])))["topograph"] for t in ts]
        if not set(tops) <= {54, 57}:
            continue
        per_tile[f"{len(es)} deep edges, classes {sorted(set(tops))}"] += 1
        x0, z0 = 4 * ij[0], 4 * ij[1]
        for t, tp in zip(ts, tops):
            corners = {(round(v[0][0] - x0), round(v[0][2] - z0)) for v in t}
            edges = {e for e, cs in (("W", {(0, 0), (0, 4)}), ("E", {(4, 0), (4, 4)}), ("S", {(0, 0), (4, 0)}),
                                     ("N", {(0, 4), (4, 4)})) if cs <= corners}
            per_tri[f"{len(es)} deep edges, the tri borders {len(edges & es)} of them: {tp}"] += 1
    res = {"per_tri": dict(sorted(per_tri.items())), "per_tile": dict(sorted(per_tile.items()))}
    (HERE / "out" / "sh_q7_sea5_class.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, v in res["per_tri"].items():
        print(f"{v:5d}  {k}")
    for k, v in res["per_tile"].items():
        print(f"{v:5d}  tiles: {k}")


if __name__ == "__main__":
    main()
