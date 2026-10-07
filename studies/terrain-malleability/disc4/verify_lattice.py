"""VERIFIER (adversarial) -- D4-05 "new disc-4 vertices follow the stock vertex lattice".

anatomy.py's new_corner_lattice counts the corners of EVERY disc-4 triangle not exactly matched by position
(u4) -- that pool INCLUDES re-heighted triangles (same XZ footprint by definition, so their corners are on
disc-1 XZ positions trivially) and the cut-boundary corners shared with KEPT triangles (also disc-1 XZ by
construction). Neither says anything about how Square placed NEW geometry. This script splits the pool:
  RH    corners of re-heighted tris (XZ footprint identical to a disc-1 tri)
  BND   corners of pure-new tris that coincide (XZ) with a corner of a kept-exact tri (the cut boundary)
  INT   the remaining pure-new corners (interior of the cut) -- the only discriminating population
and for INT reports on-disc-1-XZ, on-4u, on-1u rates, plus the stock baseline over ALL disc-1 terrain verts.
Read-only. Run: py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/verify_lattice.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
rows = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
objs = L.mesh_objects()
T = [r for r in rows if r["lod"] == "0_1" and r["part"] == "terrain" and r["cls"] not in ("IDENTICAL", "REORDERED")]


def on(c, s):
    return abs(c[0] / s - round(c[0] / s)) < 1e-3 and abs(c[2] / s - round(c[2] / s)) < 1e-3


def xz(c):
    return (round(c[0], 3), round(c[2], 3))


tot = Counter()
per = {}
for r in T:
    x, y = r["x"], r["y"]
    b1 = L.decode(objs[(1, "0_1", x, y, "terrain")], 1, x, y, "0_1")
    b4 = L.decode(objs[(4, "0_1", x, y, "terrain")], 4, x, y, "0_1")
    r1, r4 = L.tri_records(b1), L.tri_records(b4)
    pairs, u1, u4 = L._pair([q["kfull"] for q in r1], [q["kfull"] for q in r4])
    xp, x1, x4 = L._pair([r1[i]["kxz"] for i in u1], [r4[j]["kxz"] for j in u4])
    rh4 = {u4[b] for _a, b in xp}
    pure4 = [u4[b] for b in x4]
    xz1 = {xz(v) for v in b1.verts}
    kept_xz = {xz(c) for _i, j in pairs for c in r4[j]["cs"]}
    c = Counter()
    for j in u4:
        for cc in r4[j]["cs"]:
            c["all"] += 1
            c["all_on_d1xz"] += xz(cc) in xz1
    for j in rh4:
        for cc in r4[j]["cs"]:
            c["rh"] += 1
    for j in pure4:
        for cc in r4[j]["cs"]:
            if xz(cc) in kept_xz:
                c["bnd"] += 1
                continue
            c["int"] += 1
            c["int_on_d1xz"] += xz(cc) in xz1
            c["int_on_4u"] += on(cc, 4)
            c["int_on_1u"] += on(cc, 1)
    per[f"({x},{y})"] = dict(c)
    tot.update(c)

base = Counter()
for (d, lod, x, y, p), o in objs.items():
    if d == 1 and lod == "0_1" and p == "terrain":
        for v in L.decode(o, 1, x, y, "0_1").verts:
            base["n"] += 1
            base["on_4u"] += on(v, 4)
            base["on_1u"] += on(v, 1)
pct = lambda a, b: round(100 * a / b, 1) if b else None
print(f"{len(T)} really-changed terrain blocks")
print(f"ALL u4 corners (anatomy's pool): {tot['all']}, on disc-1 XZ {tot['all_on_d1xz']} ({pct(tot['all_on_d1xz'], tot['all'])}%)")
print(f"   of which re-heighted-tri corners {tot['rh']} ({pct(tot['rh'], tot['all'])}%), "
      f"pure-new boundary corners {tot['bnd']} ({pct(tot['bnd'], tot['all'])}%), interior {tot['int']} ({pct(tot['int'], tot['all'])}%)")
print(f"INTERIOR new corners: on disc-1 XZ {tot['int_on_d1xz']} ({pct(tot['int_on_d1xz'], tot['int'])}%), "
      f"on 4u {tot['int_on_4u']} ({pct(tot['int_on_4u'], tot['int'])}%), on 1u {tot['int_on_1u']} ({pct(tot['int_on_1u'], tot['int'])}%)")
print(f"STOCK baseline (all disc-1 terrain verts, n={base['n']}): on 4u {pct(base['on_4u'], base['n'])}%, on 1u {pct(base['on_1u'], base['n'])}%")
(OUT / "verify_lattice.json").write_text(json.dumps({"total": dict(tot), "baseline": dict(base), "per_block": per},
                                                    indent=0), encoding="utf-8")
print("->", OUT / "verify_lattice.json")
