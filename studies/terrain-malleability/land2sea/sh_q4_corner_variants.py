"""LAND -> SEA with shallows, question 4 (2026-10-09): a corner transition tile has two stock variants; what picks one?

The sink re-bands the water where an island stood with the open-ocean marching band (water.py, in-game proven): a tile
with 0 deep edges is sea3, 4 is sea4, 1-3 is a sea5 transition tile keyed by WHICH edges are deep (transplant.py's
learned table). A two-adjacent-edge (corner) set maps to two byte-observed tiles, v-strip 1 and v-strip 3. If the
diagonal tile between the two deep edges decides between them, the sink must follow it rather than pick at random.
For every disc-1 sea5 lattice tile with a corner set: its strip, and the band of that diagonal tile (and of the
opposite diagonal). Writes out/sh_q4_corner_variants.json.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sh_q4_corner_variants.py
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
    from ff9mapkit.world import discmirror as DM, transplant as TR
    from ff9mapkit.world.water import UFULL, VSTRIP
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    real = DM._real_parts(1, "0_1")
    own = defaultdict(set)
    s5 = defaultdict(list)
    for b in sorted(real):
        for p in PARTS:
            if p not in real[b]:
                continue
            for t in TR.world_tris(*b, p, disc=1):
                c = TR._plan_centroid(t)
                ij = (math.floor(c[0] / 4.0), math.floor(c[1] / 4.0))
                own[ij].add(p)
                if p == "sea5":
                    s5[ij].append(t)
    maps = TR._dih_maps()
    tab = Counter()
    for ij, ts in s5.items():
        if own[ij] != {"sea5"} or len(ts) != 2:
            continue
        if not all(abs(v[0][0] / 4 - round(v[0][0] / 4)) < 1e-3 and abs(v[0][2] / 4 - round(v[0][2] / 4)) < 1e-3
                   for t in ts for v in t):
            continue
        uvf = TR._affine_uv(ts[0])
        best = None
        for k in range(4):
            (u0, u1), (v0, v1) = UFULL, VSTRIP[k]
            for on, om in maps.items():
                err = 0.0
                for fx in (0, 1):
                    for fz in (0, 1):
                        u, v = uvf(4.0 * ij[0] + 4.0 * fx, 4.0 * ij[1] + 4.0 * fz)
                        a, b2 = om(fx, fz)
                        err = max(err, abs(u0 + a * (u1 - u0) - u), abs(v0 + b2 * (v1 - v0) - v))
                if best is None or err < best[2]:
                    best = (k, on, err)
        if best[2] > 0.04:
            continue
        es = TR.STRIP_EDGESET.get(best[:2])
        if es is None or len(es) != 2:
            continue
        d = [TR._DIRS[c] for c in sorted(es)]
        diag = (ij[0] + d[0][0] + d[1][0], ij[1] + d[0][1] + d[1][1])
        anti = (ij[0] - d[0][0] - d[1][0], ij[1] - d[0][1] - d[1][1])

        def band(c):
            w = own.get(c, set()) - {"terrain", "beach1"}
            return "+".join(sorted(w)) + ("+L" if own.get(c, set()) & {"terrain", "beach1"} else "") or "none"
        tab[(best[0], band(diag), band(anti))] += 1
    res = {f"strip{k} diag={a} anti={b}": n for (k, a, b), n in sorted(tab.items(), key=lambda kv: -kv[1])}
    (HERE / "out" / "sh_q4_corner_variants.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, n in res.items():
        print(f"{n:5d}  {k}")


if __name__ == "__main__":
    main()
