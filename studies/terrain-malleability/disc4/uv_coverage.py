"""STEP 6 -- ATLAS COVERAGE: did disc 4's new terrain triangles sample atlas art that disc 1 NEVER uses?

The two discs share ONE terrain material/texture (prefab_census.py: identical material PathIDs), so any new
art disc 4 shows must already sit in the shared 1024^2 atlas. Test: rasterize every disc-1 terrain triangle in
UV space (1024^2), per block; then
  * CALIBRATION 1: disc-4 tris of byte-IDENTICAL blocks -> virgin (never-used-by-disc-1) texel fraction must be 0.
  * BASELINE (held-out): for each disc-1 block, the fraction of its texels no OTHER disc-1 block uses
    ("exclusive art") -- what an ordinary block looks like under this instrument.
  * TEST: disc-4-only triangles (per topograph; and the raised-rock ridge tris) -> virgin texel fraction, and
    whether those virgin texels are PAINTED (atlas alpha > 0).
Writes out/uv_coverage.json + out/uv_coverage.png (a DERIVED mask render: grey = disc-1 coverage, orange =
texels only disc-4 new tris use; no atlas pixels). The atlas crop of the virgin region is written ONLY to the
OS temp dir for a by-eye check (never into the repo -- provenance gate).
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/uv_coverage.py
"""
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402
from d4lib import X                                  # noqa: E402
from ff9mapkit.world import atlas as A               # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
N = 1024
rows = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
objs = L.mesh_objects()
cls = {(r["x"], r["y"]): r["cls"] for r in rows if r["lod"] == "0_1" and r["part"] == "terrain"}


def mask_of(uvtris):
    im = Image.new("1", (N, N), 0)
    d = ImageDraw.Draw(im)
    for tri in uvtris:
        pts = [(u * (N - 1), (1.0 - v) * (N - 1)) for u, v in tri]
        d.polygon(pts, fill=1, outline=1)
    return np.array(im, bool)


def uvtris(bm, tri_idx=None):
    U, fi = bm.uvs, bm.flat_index
    ts = range(len(fi) // 3) if tri_idx is None else tri_idx
    return [[U[fi[3 * t + k]][:2] for k in range(3)] for t in ts]


blocks = sorted({(x, y) for (d, lod, x, y, p) in objs if d == 1 and lod == "0_1" and p == "terrain"})
bm1 = {b: L.decode(objs[(1, "0_1", b[0], b[1], "terrain")], 1, b[0], b[1], "0_1") for b in blocks}
own = {}
count = np.zeros((N, N), np.int16)
for b in blocks:
    own[b] = mask_of(uvtris(bm1[b]))
    count += own[b]
cov1 = count > 0
print(f"disc-1 terrain atlas coverage: {cov1.mean()*100:.1f}% of texels used by >=1 block")

# BASELINE: exclusive-art fraction per held-out block
excl = []
for b in blocks:
    m = own[b]
    if m.sum():
        excl.append(float(((count == 1) & m).sum() / m.sum()))
excl.sort()
print(f"BASELINE exclusive-art fraction per disc-1 block: median {excl[len(excl)//2]:.3f}, "
      f"p90 {excl[int(len(excl)*0.9)]:.3f}, max {excl[-1]:.3f}")

# CALIBRATION + TEST
cal_tex = cal_virgin = 0
new_by_topo = defaultdict(list)
for b in blocks:
    k4 = (4, "0_1", b[0], b[1], "terrain")
    if k4 not in objs:
        continue
    bm4 = L.decode(objs[k4], 4, b[0], b[1], "0_1")
    if cls.get(b) == "IDENTICAL":
        m = mask_of(uvtris(bm4))
        cal_tex += int(m.sum()); cal_virgin += int((m & ~cov1).sum())
        continue
    r1, r4 = L.tri_records(bm1[b]), L.tri_records(bm4)
    _p, _u1, u4 = L._pair([q["kfull"] for q in r1], [q["kfull"] for q in r4])
    for j in u4:
        new_by_topo[X.decode_id(r4[j]["id"])["topograph"]].append([list(c) for c in uvtris(bm4, [j])[0]])
print(f"CALIBRATION 1: identical-block disc-4 texels {cal_tex}, virgin {cal_virgin} (must be 0)")

atlas = np.array(A.load_atlas("terrain", source="bundle", cache=False))
alpha = atlas[..., 3] > 8 if atlas.shape[0] == N else None
res = {"disc1_coverage_frac": float(cov1.mean()), "baseline_exclusive": {"median": excl[len(excl)//2],
       "p90": excl[int(len(excl)*0.9)], "max": excl[-1]}, "calibration": [cal_tex, cal_virgin], "by_topo": {}}
virgin_all = np.zeros((N, N), bool)
for t, tris in sorted(new_by_topo.items(), key=lambda kv: -len(kv[1])):
    m = mask_of(tris)
    v = m & ~cov1
    virgin_all |= v
    painted = int((v & alpha).sum()) if alpha is not None else None
    res["by_topo"][str(t)] = {"tris": len(tris), "texels": int(m.sum()), "virgin": int(v.sum()),
                              "virgin_frac": round(float(v.sum() / max(m.sum(), 1)), 4), "virgin_painted": painted}
    if len(tris) >= 50:
        print(f"  topo {t:2d}: {len(tris):5d} new tris, {int(m.sum()):6d} texels, virgin {int(v.sum()):6d} "
              f"({100*v.sum()/max(m.sum(),1):.1f}%), painted virgin {painted}")
ys, xs = np.nonzero(virgin_all)
if len(xs):
    res["virgin_bbox_px"] = [int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())]
    res["virgin_total"] = int(virgin_all.sum())
print("virgin texels used only by disc-4 new tris:", res.get("virgin_total"), "bbox px", res.get("virgin_bbox_px"))

# derived mask render (no atlas pixels)
img = np.full((N, N, 3), 252, np.uint8)
img[cov1] = (195, 194, 183)
img[virgin_all] = (235, 104, 52)
Image.fromarray(img).save(OUT / "uv_coverage.png")
# by-eye crop of the real atlas -> OS temp ONLY
if len(xs):
    x0, x1, y0, y1 = res["virgin_bbox_px"]
    tmp = Path(tempfile.gettempdir()) / "ff9_disc4_virgin_atlas_crop.png"
    crop = Image.fromarray(atlas[max(0, y0 - 8):y1 + 8, max(0, x0 - 8):x1 + 8])
    over = Image.fromarray(np.where(virgin_all[max(0, y0 - 8):y1 + 8, max(0, x0 - 8):x1 + 8, None],
                                    np.array([255, 0, 255, 255], np.uint8), 0).astype(np.uint8))
    sc = max(1, 600 // max(crop.size))
    crop.resize((crop.size[0] * sc, crop.size[1] * sc), Image.NEAREST).save(tmp)
    over.resize((over.size[0] * sc, over.size[1] * sc), Image.NEAREST).save(tmp.with_name("ff9_disc4_virgin_mask.png"))
    print("by-eye crop (temp, not repo):", tmp)
(OUT / "uv_coverage.json").write_text(json.dumps(res, indent=0), encoding="utf-8")
print("->", OUT / "uv_coverage.json")
