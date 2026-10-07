"""VERIFIER (adversarial) -- D4-06 "the 5 edges that went exact->open are T-junctions with gap 0".
weld_gap.gap() SKIPS any along-coordinate where either side's top polyline does not reach it ("uncovered"),
so a stretch of border that one side no longer covers at all measures gap 0. A T-junction is fully covered.
For every changed edge whose uncovered count rose on disc 4, print both sides' border extents per disc and
the uncovered along-coordinates. Read-only.
Run: py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/verify_weld_uncovered.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
rows = json.loads((OUT / "weld_gap.json").read_text(encoding="utf-8"))
objs = L.mesh_objects()
sel = [r for r in rows if r["changed"] and r["d4_uncovered"] > r["d1_uncovered"]]
res = []
for r in sel:
    (ax, ay, sa), (bx, by, sb) = r["a"], r["b"]
    rec = {"a": r["a"], "b": r["b"]}
    for d in (1, 4):
        A = L.edge_profile(L.decode(objs[(d, "0_1", ax, ay, "terrain")], d, ax, ay, "0_1"), sa)
        B = L.edge_profile(L.decode(objs[(d, "0_1", bx, by, "terrain")], d, bx, by, "0_1"), sb)
        aa, bb = sorted({p[0] for p in A}), sorted({p[0] for p in B})
        ra = (aa[0], aa[-1]) if aa else None
        rb = (bb[0], bb[-1]) if bb else None
        unc = sorted([a for a in set(aa) | set(bb)
                      if not (ra and ra[0] - 1e-3 <= a <= ra[1] + 1e-3) or not (rb and rb[0] - 1e-3 <= a <= rb[1] + 1e-3)])
        only_a = sorted(set(aa) - set(bb)); only_b = sorted(set(bb) - set(aa))
        rec[f"d{d}"] = {"A_extent": ra, "B_extent": rb, "A_n": len(A), "B_n": len(B),
                        "uncovered_along": unc, "along_only_A": only_a[:8], "along_only_B": only_b[:8]}
    res.append(rec)
    print(json.dumps(rec))
(OUT / "verify_weld_uncovered.json").write_text(json.dumps(res, indent=1), encoding="utf-8")

# What does each side ground on (all Form-1 parts, engine order) just inside the border along the uncovered stretch?
print("\nground probe 0.25u inside each side along the uncovered stretch (disc 4 vs disc 1):")
SIDE = {"E": lambda a: (63.75, a), "W": lambda a: (0.25, a), "N": lambda a: (a, -0.25), "S": lambda a: (a, -63.75)}
for rec in res:
    (ax, ay, sa), (bx, by, sb) = rec["a"], rec["b"]
    unc = rec["d4"]["uncovered_along"]
    lo, hi = min(unc), max(unc)
    for d in (1, 4):
        line = []
        for (x, y, s) in ((ax, ay, sa), (bx, by, sb)):
            parts = {p: L.decode(o, d, xx, yy, lod) for (dd, lod, xx, yy, p), o in objs.items()
                     if dd == d and lod == "0_1" and (xx, yy) == (x, y)}
            ml, _ = L.meshlist_for(parts)
            idx = [L.P.build_index(bm) for _, bm in ml]
            hits = []
            for a in sorted({lo, (lo + hi) / 2, hi} | ({lo - 2} if lo - 2 > (0 if s in "NS" else -64) else set())):
                px, pz = SIDE[s](a)
                g = L.P.place(ml, px, pz, 0.0, sky=True, index=idx)
                hits.append((round(a, 2), g[1], round(g[0], 2) if g[1] != "MISS" else None))
            line.append(((x, y, s), hits))
        print(f"  d{d} {line}")
