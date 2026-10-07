"""VERIFIER (adversarial) -- D4-07 "disc 4 painted no new art; every new topograph except 59 has 0% virgin
texels". uv_coverage.py prints only topographs with >= 50 new tris; its own JSON shows topographs 30/48/53-57
at 100% virgin. Locate those triangles (block, topograph, area, UV bbox). Read-only.
Run: py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/verify_virgin_art.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402
from d4lib import X                                  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
uv = json.loads((OUT / "uv_coverage.json").read_text(encoding="utf-8"))
virgin_topos = {int(t) for t, v in uv["by_topo"].items() if v["virgin"] and v["virgin_frac"] > 0.5}
print("topographs whose new tris are >50% virgin texels:", sorted(virgin_topos),
      "texels:", {t: uv["by_topo"][str(t)]["virgin"] for t in sorted(virgin_topos)})
rows = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
objs = L.mesh_objects()
hits = defaultdict(Counter)
uvb = {}
for r in rows:
    if r["lod"] != "0_1" or r["part"] != "terrain" or r["cls"] in ("IDENTICAL", "REORDERED"):
        continue
    x, y = r["x"], r["y"]
    b1 = L.decode(objs[(1, "0_1", x, y, "terrain")], 1, x, y, "0_1")
    b4 = L.decode(objs[(4, "0_1", x, y, "terrain")], 4, x, y, "0_1")
    r1, r4 = L.tri_records(b1), L.tri_records(b4)
    _p, _u1, u4 = L._pair([q["kfull"] for q in r1], [q["kfull"] for q in r4])
    for j in u4:
        t = X.decode_id(r4[j]["id"])["topograph"]
        if t in virgin_topos:
            hits[(x, y)][t] += 1
            us = [c[0] for c in r4[j]["uv"]]; vs = [c[1] for c in r4[j]["uv"]]
            k = (x, y, t)
            b = uvb.get(k, [9, -9, 9, -9])
            uvb[k] = [min(b[0], min(us)), max(b[1], max(us)), min(b[2], min(vs)), max(b[3], max(vs))]
# does disc 1's terrain use these topographs anywhere at all?
d1t = Counter()
for (d, lod, x, y, p), o in objs.items():
    if d == 1 and lod == "0_1" and p == "terrain":
        for q in L.tri_records(L.decode(o, 1, x, y, "0_1")):
            t = X.decode_id(q["id"])["topograph"]
            if t in virgin_topos:
                d1t[t] += 1
print("disc-1 terrain tris carrying those topographs anywhere:", dict(d1t))
for b, c in sorted(hits.items()):
    print(f"   block {b}: {dict(c)}  uv bbox " + str({t: [round(v, 3) for v in uvb[(b[0], b[1], t)]] for t in c}))
(OUT / "verify_virgin_art.json").write_text(json.dumps({"virgin_topos": sorted(virgin_topos),
                                                        "disc1_use": {str(k): v for k, v in d1t.items()},
                                                        "blocks": {str(b): dict(c) for b, c in hits.items()}},
                                                       indent=1), encoding="utf-8")
