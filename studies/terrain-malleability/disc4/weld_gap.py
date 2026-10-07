"""STEP 10 -- WELD GAPS: when disc 4 changed a block border, did the seam stay closed?

anatomy.py classifies every adjacent terrain pair's shared edge as EXACT (identical border vertex sets on both
sides) or OPEN. OPEN is not necessarily a crack: a T-junction (a vertex on one side only, lying ON the other
side's edge) is gap-free. This measures the real gap: each side's border becomes a height polyline along the
edge (the TOP sheet: max y per along-coordinate), both are linearly interpolated at the union of along-coords,
gap = max |hA - hB|. Calibration: every EXACT edge must measure 0.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/weld_gap.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
objs = L.mesh_objects()
terr = {(d, x, y): o for (d, lod, x, y, p), o in objs.items() if lod == "0_1" and p == "terrain"}
prof = {}


def ep(d, x, y, s):
    k = (d, x, y)
    if k not in prof:
        bm = L.decode(terr[k], d, x, y, "0_1")
        prof[k] = {side: L.edge_profile(bm, side) for side in "EWNS"}
    return prof[k][s]


def top_poly(pts):
    best = {}
    for a, y in pts:
        best[a] = max(y, best.get(a, -1e9))
    return sorted(best.items())


def interp(poly, a):
    if not poly:
        return None
    if a <= poly[0][0]:
        return poly[0][1] if abs(a - poly[0][0]) < 1e-3 else None
    if a >= poly[-1][0]:
        return poly[-1][1] if abs(a - poly[-1][0]) < 1e-3 else None
    for (a0, y0), (a1, y1) in zip(poly, poly[1:]):
        if a0 <= a <= a1:
            return y0 + (y1 - y0) * ((a - a0) / (a1 - a0) if a1 > a0 else 0)
    return None


def gap(A, B):
    pa, pb = top_poly(A), top_poly(B)
    g, uncovered = 0.0, 0
    for a in sorted({p[0] for p in pa} | {p[0] for p in pb}):
        ha, hb = interp(pa, a), interp(pb, a)
        if ha is None or hb is None:
            uncovered += 1
            continue
        g = max(g, abs(ha - hb))
    return round(g, 4), uncovered


rows, cal = [], Counter()
for (d, x, y) in sorted(terr):
    if d != 1:
        continue
    for (dx, dy, sa, sb) in ((1, 0, "E", "W"), (0, 1, "S", "N")):
        nb = (x + dx, y + dy)
        if (1, *nb) not in terr or (4, x, y) not in terr or (4, *nb) not in terr:
            continue
        rec = {"a": [x, y, sa], "b": [nb[0], nb[1], sb]}
        for disc in (1, 4):
            A, B = ep(disc, x, y, sa), ep(disc, nb[0], nb[1], sb)
            g, unc = gap(A, B)
            rec[f"d{disc}_exact"] = A == B
            rec[f"d{disc}_gap"] = g
            rec[f"d{disc}_uncovered"] = unc
            if A == B:
                cal["exact_edges"] += 1
                cal["exact_edges_gap0"] += g == 0.0
        rec["changed"] = (ep(1, x, y, sa) != ep(4, x, y, sa)) or (ep(1, *nb, sb) != ep(4, *nb, sb))
        rows.append(rec)
print(f"CALIBRATION: exact edges measuring gap 0: {cal['exact_edges_gap0']}/{cal['exact_edges']}")


def bucket(g):
    return "0" if g == 0 else "<0.01" if g < 0.01 else "<0.1" if g < 0.1 else "<1" if g < 1 else ">=1"


for disc in (1, 4):
    c = Counter(bucket(r[f"d{disc}_gap"]) for r in rows if not r[f"d{disc}_exact"])
    print(f"disc {disc}: open edges {sum(c.values())}/{len(rows)}, gap buckets {dict(c)}")
ch = [r for r in rows if r["changed"]]
print(f"\nedges whose profile changed across discs: {len(ch)}")
print("   disc-4 gap buckets on changed edges:", dict(Counter(bucket(r['d4_gap']) for r in ch)))
print("   changed edges that got WORSE (d4 gap > d1 gap + 0.01):")
for r in ch:
    if r["d4_gap"] > r["d1_gap"] + 0.01:
        print("     ", r)
(OUT / "weld_gap.json").write_text(json.dumps(rows, indent=0), encoding="utf-8")
print("->", OUT / "weld_gap.json")
