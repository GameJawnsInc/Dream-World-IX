"""CALIBRATION PART C -- is any of the census's "change" just float noise split across a rounding boundary?

census.py keys triangles on positions rounded to 1e-3. Two floats 1e-7 apart can straddle a rounding
boundary and look like a "moved" tri. This re-matches every UNMATCHED triangle (only1 vs only4, and the
re-heighted pairs) with a TOLERANCE matcher (max corner distance over all 6 corner correspondences,
grid-hashed), at eps = 0.002 / 0.01 / 0.1 / 0.5 u, and reports how much of the change survives.
If the change were noise it would vanish at eps 0.002-0.01. Also reports the per-part distribution of the
largest true deviation, so "tiny edits" (< 0.1u) are separated from "real reshapes".

Writes out/noise_check.json. Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/noise_check.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
rows = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
objs = L.mesh_objects()
EPS = (0.002, 0.01, 0.1, 0.5)
PERMS = list(permutations(range(3)))


def corners(bm):
    V, fi = bm.verts, bm.flat_index
    return [[V[fi[3 * t + k]] for k in range(3)] for t in range(len(fi) // 3)]


def tdist(a, b):
    best = 1e9
    for p in PERMS:
        d = max(math.dist(a[k], b[p[k]]) for k in range(3))
        best = min(best, d)
    return best


def tol_match(A, B, eps):
    """Greedy tolerance match of tri lists A->B; returns # of A matched within eps."""
    cell = max(eps * 4, 1.0)
    grid = defaultdict(list)
    for j, b in enumerate(B):
        cx = sum(c[0] for c in b) / 3; cz = sum(c[2] for c in b) / 3
        grid[(math.floor(cx / cell), math.floor(cz / cell))].append(j)
    used, n = set(), 0
    for a in A:
        cx = sum(c[0] for c in a) / 3; cz = sum(c[2] for c in a) / 3
        gx, gz = math.floor(cx / cell), math.floor(cz / cell)
        best, bj = eps + 1, None
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for j in grid.get((gx + dx, gz + dz), ()):
                    if j in used:
                        continue
                    d = tdist(a, B[j])
                    if d < best:
                        best, bj = d, j
        if bj is not None and best <= eps:
            used.add(bj); n += 1
    return n


def nearest_dev(A, B):
    """For each tri in A, the distance to the nearest tri in B (centroid-gridded, 3x3 cells of 8u)."""
    cell = 8.0
    grid = defaultdict(list)
    for j, b in enumerate(B):
        cx = sum(c[0] for c in b) / 3; cz = sum(c[2] for c in b) / 3
        grid[(math.floor(cx / cell), math.floor(cz / cell))].append(j)
    out = []
    for a in A:
        cx = sum(c[0] for c in a) / 3; cz = sum(c[2] for c in a) / 3
        gx, gz = math.floor(cx / cell), math.floor(cz / cell)
        cand = [j for dx in (-1, 0, 1) for dz in (-1, 0, 1) for j in grid.get((gx + dx, gz + dz), ())]
        out.append(min((tdist(a, B[j]) for j in cand), default=99.0))
    return out


# ---- SELF-TEST (the matcher must find a 1e-6 straddle and must NOT absorb a 1.0u move) ----
_a = [[[1.0004999, 2.0, -3.0], [5.0, 2.0, -3.0], [1.0, 2.0, -7.0]]]
_b = [[[1.0005001, 2.0, -3.0], [5.0, 2.0, -3.0], [1.0, 2.0, -7.0]]]
_c = [[[1.0, 3.0, -3.0], [5.0, 3.0, -3.0], [1.0, 3.0, -7.0]]]
_rk = lambda t: tuple(sorted(tuple(round(v, 3) for v in c) for c in t))
assert _rk(_a[0]) != _rk(_b[0]), "self-test premise: the straddle must split under rounding"
assert tol_match(_a, _b, 0.002) == 1, "matcher missed a 2e-7 straddle"
assert tol_match(_a, _c, 0.5) == 0, "matcher absorbed a 1.0u move at eps 0.5"
assert tol_match(_a, [list(reversed(_b[0]))], 0.002) == 1, "matcher is corner-order sensitive"
print("self-test PASS (straddle found, 1.0u move rejected, corner order ignored)")

res = []
surv = {e: Counter() for e in EPS}
dev_hist = defaultdict(Counter)
for r in rows:
    if r["cls"] not in ("RETOPO",) and not r["cls"].startswith("RESHAPE"):
        continue
    key = (r["lod"], r["x"], r["y"], r["part"])
    bm1 = L.decode(objs[(1, *key)], 1, r["x"], r["y"], r["lod"])
    bm4 = L.decode(objs[(4, *key)], 4, r["x"], r["y"], r["lod"])
    r1, r4 = L.tri_records(bm1), L.tri_records(bm4)
    pairs, u1, u4 = L._pair([q["kfull"] for q in r1], [q["kfull"] for q in r4])
    A = [r1[i]["cs"] for i in u1]
    B = [r4[j]["cs"] for j in u4]
    rec = {"key": list(key), "unmatched1": len(A), "unmatched4": len(B)}
    for e in EPS:
        m = tol_match(A, B, e)
        rec[f"tolmatch_{e}"] = m
        left = len(A) - m + len(B) - m
        surv[e]["changed" if left else "vanished"] += 1
    devs = nearest_dev(A, B) if A and B else []
    rec["dev_max"] = round(max(devs), 4) if devs else None
    rec["dev_median"] = round(sorted(devs)[len(devs) // 2], 4) if devs else None
    b = ("none" if not devs else "<0.01" if max(devs) < 0.01 else "<0.1" if max(devs) < 0.1
         else "<1" if max(devs) < 1 else "<4" if max(devs) < 4 else ">=4")
    dev_hist[r["part"]][b] += 1
    rec["dev_bucket"] = b
    res.append(rec)

print(f"{len(res)} RETOPO/RESHAPE keys re-matched with tolerance")
for e in EPS:
    print(f"  eps {e:>5}: keys whose change survives = {surv[e]['changed']}, vanish = {surv[e]['vanished']}")
print("\n  max deviation of an unmatched disc-1 tri from its nearest disc-4 tri, per part (key counts):")
for p, c in sorted(dev_hist.items()):
    print(f"   {p:12s} {dict(c)}")
tiny = [x for x in res if x["dev_bucket"] in ("<0.01", "<0.1")]
print(f"\n  keys whose whole change is < 0.1u (sub-visual): {len(tiny)}")
for x in tiny[:40]:
    print("   ", x)
(OUT / "noise_check.json").write_text(json.dumps(res, indent=0), encoding="utf-8")
print("->", OUT / "noise_check.json")
