"""VERIFIER (adversarial) -- fairness check before judging D4-07. uv_coverage.py's "virgin" baseline rasterises
only disc-1 FORM-1 (0_1) terrain UVs. The terrain material is also used by the FORM-2 (0_2) Terrain2 meshes
(WMWorldPrefabMaker binds Terrain2 with TerrainMaterial). Disc 4 promotes Form-2 content into Form 1 (D4-13),
so texels "virgin" to disc-1 Form 1 may be disc-1 Form-2 art. Re-measure the virgin texels of disc-4 new tris
against disc-1 Form-1 + Form-2 terrain coverage (and, separately, the full disc-1+disc-4 0_2 trees).
Read-only. Run: py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/verify_virgin_form2.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402
from d4lib import X                                  # noqa: E402

N = 1024
OUT = Path(__file__).resolve().parent / "out"
rows = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
objs = L.mesh_objects()


def mask_of(uvtris):
    im = Image.new("1", (N, N), 0)
    d = ImageDraw.Draw(im)
    for tri in uvtris:
        d.polygon([(u * (N - 1), (1.0 - v) * (N - 1)) for u, v in tri], fill=1, outline=1)
    return np.array(im, bool)


def uvtris(bm, ts=None):
    U, fi = bm.uvs, bm.flat_index
    ts = range(len(fi) // 3) if ts is None else ts
    return [[U[fi[3 * t + k]][:2] for k in range(3)] for t in ts]


def cover(disc, lod):
    m = np.zeros((N, N), bool)
    for (d, l, x, y, p), o in objs.items():
        if d == disc and l == lod and p == "terrain":
            m |= mask_of(uvtris(L.decode(o, d, x, y, l)))
    return m


c11 = cover(1, "0_1"); c12 = cover(1, "0_2")
new_by_topo = defaultdict(list)
for r in rows:
    if r["lod"] != "0_1" or r["part"] != "terrain" or r["cls"] in ("IDENTICAL", "REORDERED"):
        continue
    x, y = r["x"], r["y"]
    b1 = L.decode(objs[(1, "0_1", x, y, "terrain")], 1, x, y, "0_1")
    b4 = L.decode(objs[(4, "0_1", x, y, "terrain")], 4, x, y, "0_1")
    r1, r4 = L.tri_records(b1), L.tri_records(b4)
    _p, _u, u4 = L._pair([q["kfull"] for q in r1], [q["kfull"] for q in r4])
    for j in u4:
        new_by_topo[X.decode_id(r4[j]["id"])["topograph"]].append(uvtris(b4, [j])[0])
res = {}
allv_f1 = np.zeros((N, N), bool); allv_f12 = np.zeros((N, N), bool)
for t, tris in sorted(new_by_topo.items()):
    m = mask_of(tris)
    v1 = m & ~c11
    v12 = m & ~(c11 | c12)
    allv_f1 |= v1; allv_f12 |= v12
    if v1.sum():
        res[t] = {"tris": len(tris), "texels": int(m.sum()), "virgin_vs_F1": int(v1.sum()), "virgin_vs_F1F2": int(v12.sum())}
        print(f"  topo {t:2d}: {len(tris):5d} new tris, virgin vs disc-1 F1 {int(v1.sum()):6d}, vs disc-1 F1+F2 {int(v12.sum()):6d}")
print(f"UNION virgin texels: vs disc-1 Form-1 terrain {int(allv_f1.sum())}; vs disc-1 Form-1+Form-2 terrain {int(allv_f12.sum())}")
print(f"disc-1 coverage: F1 {c11.mean()*100:.1f}%, F1+F2 {(c11 | c12).mean()*100:.1f}%")
(OUT / "verify_virgin_form2.json").write_text(json.dumps({"by_topo": {str(k): v for k, v in res.items()},
                                                          "union_vs_f1": int(allv_f1.sum()),
                                                          "union_vs_f1f2": int(allv_f12.sum())}, indent=1),
                                               encoding="utf-8")
