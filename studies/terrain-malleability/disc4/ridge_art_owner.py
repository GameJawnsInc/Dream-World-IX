"""STEP 7 -- WHOSE ART do disc 4's scattered rock ridges borrow?  (the "Iifa roots" discriminator)

The ridges (new topo-49 tris away from the two big sites) sample atlas texels disc 1 already uses
(uv_coverage.py: 0.2% virgin). If those texels are OWNED on disc 1 mainly by the Iifa Tree blocks (whose
disc-1 terrain already carries the tree's roots), the ridges are Iifa-root art transplanted map-wide. If the
owners are ordinary rock blocks everywhere, they are generic rock.
  * ridge tris = disc-4-only terrain tris with topo 49, outside the Iifa (10-12,4-6) / Shimmering (5-7,2-5)
    site windows, whose centroid sits >0.3u ABOVE disc-1 ground that was WALKABLE (the crescents proper --
    excludes ordinary re-cut mountain rock).
  * owner share(b) = |ridge texels covered by disc-1 block b| / |ridge texels|  (a texel can have many owners).
  * CONTROL: the same statistic for the disc-1 topo-49 tris of 12 random ordinary rock blocks, so a "high
    share" has a reference (owners of ordinary rock are diffuse).
  * the ridge texels' atlas footprint on a 32px tile grid (concentrated strip vs diffuse).
Crops of the top atlas cells go to the OS temp dir only (provenance gate).
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/ridge_art_owner.py
"""
import json
import random
import sys
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402
from d4lib import X, P                               # noqa: E402
from ff9mapkit.world import atlas as A               # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
N = 1024
objs = L.mesh_objects()
IIFA = {(x, y) for x in (10, 11, 12) for y in (4, 5, 6)}
SHIM = {(x, y) for x in (5, 6, 7) for y in (2, 3, 4, 5)}


def mask_of(uvtris):
    im = Image.new("1", (N, N), 0)
    d = ImageDraw.Draw(im)
    for tri in uvtris:
        d.polygon([(u * (N - 1), (1.0 - v) * (N - 1)) for u, v in tri], fill=1, outline=1)
    return np.array(im, bool)


blocks = sorted({(x, y) for (d, lod, x, y, p) in objs if d == 1 and lod == "0_1" and p == "terrain"})
bm1 = {b: L.decode(objs[(1, "0_1", b[0], b[1], "terrain")], 1, b[0], b[1], "0_1") for b in blocks}
own = {}
for b in blocks:
    U, fi = bm1[b].uvs, bm1[b].flat_index
    own[b] = mask_of([[U[fi[3 * t + k]][:2] for k in range(3)] for t in range(len(fi) // 3)])

ridge = []
ridge_blocks = Counter()
for b in blocks:
    if b in IIFA or b in SHIM or (4, "0_1", b[0], b[1], "terrain") not in objs:
        continue
    bm4 = L.decode(objs[(4, "0_1", b[0], b[1], "terrain")], 4, b[0], b[1], "0_1")
    r1, r4 = L.tri_records(bm1[b]), L.tri_records(bm4)
    _p, _u1, u4 = L._pair([q["kfull"] for q in r1], [q["kfull"] for q in r4])
    parts1 = {pp: L.decode(o, 1, x, y, lod) for (d, lod, x, y, pp), o in objs.items()
              if d == 1 and lod == "0_1" and (x, y) == b}
    ml1, _ = L.meshlist_for(parts1)
    idx1 = [P.build_index(m) for _, m in ml1]
    for j in u4:
        if X.decode_id(r4[j]["id"])["topograph"] != 49:
            continue
        cs = r4[j]["cs"]
        cx, cz = sum(c[0] for c in cs) / 3, sum(c[2] for c in cs) / 3
        g = P.place(ml1, cx, cz, 0.0, sky=True, index=idx1)
        # a CRESCENT tri: disc 1 was WALKABLE ground here and disc 4's new rock sits ABOVE it
        if g[1] != "MISS" and g[3] in P.WALK_OK and sum(c[1] for c in cs) / 3 > g[0] + 0.3:
            ridge.append([list(c) for c in r4[j]["uv"]])
            ridge_blocks[b] += 1
rm = mask_of(ridge)
print(f"ridge tris {len(ridge)} on {len(ridge_blocks)} blocks; ridge texels {int(rm.sum())}")


def owner_share(m):
    tot = m.sum()
    sh = {b: float((own[b] & m).sum() / tot) for b in blocks}
    return sorted(sh.items(), key=lambda kv: -kv[1])


top = owner_share(rm)[:10]
print("ridge texel owners (disc-1 block, share of ridge texels it also uses):")
for b, s in top:
    tag = " <- IIFA window" if b in IIFA else (" <- SHIMMERING window" if b in SHIM else "")
    print(f"   {b}: {s:.3f}{tag}")
iifa_union = np.zeros((N, N), bool)
for b in IIFA:
    if b in own:
        iifa_union |= own[b]
iifa_share = float((iifa_union & rm).sum() / rm.sum())
print(f"share of ridge texels covered by ANY Iifa-window block: {iifa_share:.3f}")

# CONTROL: ordinary disc-1 rock (topo-49 tris) of random non-Iifa blocks
random.seed(7)
ctrl_rows = []
cands = [b for b in blocks if b not in IIFA and b not in SHIM]
for b in random.sample(cands, 12):
    recs = [r for r in L.tri_records(bm1[b]) if r["id"] is not None and X.decode_id(r["id"])["topograph"] == 49]
    if len(recs) < 20:
        continue
    m = mask_of([[list(c) for c in r["uv"]] for r in recs])
    others = np.zeros((N, N), bool)
    for bb in blocks:
        if bb != b:
            others |= own[bb]
    sh = owner_share(m)
    sh = [(bb, s) for bb, s in sh if bb != b]
    ctrl_rows.append({"block": list(b), "tris": len(recs), "iifa_share": round(float((iifa_union & m).sum() / m.sum()), 3),
                      "top_other_owner": [list(sh[0][0]), round(sh[0][1], 3)],
                      "shared_with_any_other": round(float((others & m).sum() / m.sum()), 3)})
print("CONTROL (ordinary disc-1 topo-49 rock of random blocks):")
for c in ctrl_rows:
    print("  ", c)

# atlas footprint of ridge texels on a 32px grid
g = Counter()
ys, xs = np.nonzero(rm)
for x, y in zip(xs, ys):
    g[(x // 32, y // 32)] += 1
tot = int(rm.sum())
cells = g.most_common(12)
cum = sum(v for _, v in cells)
print(f"ridge texels in the top-12 of {len(g)} 32px atlas cells: {cum/tot:.3f}")
print("   top cells (cx,cy,share):", [(c[0], c[1], round(v / tot, 3)) for c, v in cells[:8]])
atlas = np.array(A.load_atlas("terrain", source="bundle", cache=False))
tmpd = Path(tempfile.gettempdir())
x0 = min(c[0] for c, _ in cells[:8]) * 32; x1 = (max(c[0] for c, _ in cells[:8]) + 1) * 32
y0 = min(c[1] for c, _ in cells[:8]) * 32; y1 = (max(c[1] for c, _ in cells[:8]) + 1) * 32
crop = atlas[y0:y1, x0:x1].copy()
crop[rm[y0:y1, x0:x1] & (np.indices(crop.shape[:2]).sum(0) % 6 == 0)] = (255, 0, 255, 255)
sc = max(1, 700 // max(crop.shape[:2]))
Image.fromarray(crop).resize((crop.shape[1] * sc, crop.shape[0] * sc), Image.NEAREST).save(tmpd / "ff9_disc4_ridge_art.png")
print("by-eye crop (temp, not repo):", tmpd / "ff9_disc4_ridge_art.png", "px window", [x0, x1, y0, y1])
(OUT / "ridge_art_owner.json").write_text(json.dumps({
    "ridge_tris": len(ridge), "ridge_blocks": len(ridge_blocks), "ridge_texels": tot,
    "top_owners": [[list(b), s] for b, s in top], "iifa_window_share": iifa_share, "control": ctrl_rows,
    "top_cells": [[int(c[0]), int(c[1]), v / tot] for c, v in cells]}, indent=0), encoding="utf-8")
print("->", OUT / "ridge_art_owner.json")
