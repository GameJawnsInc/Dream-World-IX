"""LAND -> SEA with shallows, the look (2026-10-09): a top-down textured render of an island before and after the
re-banding sink, from the plan alone (nothing deployed).

Each pixel samples the game's own textures (render.tex_for: the engine atlas for land, the frame-0 water PNGs per band)
at the uv of the tri over it, NEAREST, unlit -- the in-game look minus wave animation, fog and the camera's angle
(render.py's blind-spot ledger). Left: stock. Middle: after the sink. Right: the bands after (sea3 light, sea5 mid,
sea4 dark), the re-tiled region outlined. Writes out/sh_q6_<x>_<z>.png.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sh_q6_render.py X Z [X Z ...]
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))
ORDER = ("sea4", "sea5", "sea3", "sea1", "sea2", "beach1", "terrain", "object")
BAND_RGB = {"sea4": (20, 40, 110), "sea5": (40, 100, 170), "sea3": (90, 170, 210), "sea1": (130, 220, 200),
            "sea2": (190, 240, 250), "beach1": (230, 210, 140), "terrain": (110, 140, 50), "object": (190, 60, 60)}
PX = 6                                    # pixels per world unit


def raster(soups, box, tex):
    x0, x1, z0, z1 = box
    W, H = int((x1 - x0) * PX), int((z1 - z0) * PX)
    img = np.zeros((H, W, 3), np.float32)
    img[:] = (152, 178, 208)
    band = np.zeros((H, W, 3), np.float32)
    band[:] = (0, 0, 0)
    gx = x0 + (np.arange(W) + 0.5) / PX
    gz = z1 - (np.arange(H) + 0.5) / PX
    for part in ORDER:
        for t in soups.get(part, ()):
            P = np.array([[v[0][0], v[0][2]] for v in t])
            UV = np.array([v[2] for v in t])
            bx0, bx1 = P[:, 0].min(), P[:, 0].max()
            bz0, bz1 = P[:, 1].min(), P[:, 1].max()
            i0, i1 = max(0, int((bx0 - x0) * PX)), min(W, int(math.ceil((bx1 - x0) * PX)) + 1)
            j0, j1 = max(0, int((z1 - bz1) * PX)), min(H, int(math.ceil((z1 - bz0) * PX)) + 1)
            if i0 >= i1 or j0 >= j1:
                continue
            X, Z = np.meshgrid(gx[i0:i1], gz[j0:j1])
            (ax, az), (bx, bz), (cx, cz) = P
            d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
            if abs(d) < 1e-12:
                continue
            w0 = ((bz - cz) * (X - cx) + (cx - bx) * (Z - cz)) / d
            w1 = ((cz - az) * (X - cx) + (ax - cx) * (Z - cz)) / d
            w2 = 1 - w0 - w1
            m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not m.any():
                continue
            u = w0 * UV[0, 0] + w1 * UV[1, 0] + w2 * UV[2, 0]
            v = w0 * UV[0, 1] + w1 * UV[1, 1] + w2 * UV[2, 1]
            sub = img[j0:j1, i0:i1]
            tx = tex.get(part)
            if tx is not None:
                from ff9mapkit.world import render as R
                rgb = R.sample(tx, u[m], v[m])
                sub[m] = rgb
            else:
                sub[m] = BAND_RGB[part]
            band[j0:j1, i0:i1][m] = BAND_RGB[part]
    return img.astype(np.uint8), band.astype(np.uint8)


def main():
    import ff9mapkit
    from ff9mapkit.world import discmirror as DM, render as R, transplant as TR
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    site = R.RenderSite(cells=((0, 0),), disc=1)
    names = {"sea4": "Sea4", "sea5": "Sea5", "sea3": "Sea3", "sea1": "Sea1", "sea2": "Sea2", "beach1": "Beach1",
             "terrain": "Terrain", "object": "Object"}
    tex = {p: R.tex_for(n, site) for p, n in names.items()}
    real = DM._real_parts(1, "0_1")
    a = [float(v) for v in sys.argv[1:]]
    for k in range(0, len(a), 2):
        at = (a[k], a[k + 1])
        plan, rep = TR.sink_plan(at)
        blocks = sorted({tuple(b) for b in rep["blocks"]} | set(plan))
        near = sorted({(b[0] + dx, b[1] + dy) for b in blocks for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                       if (b[0] + dx, b[1] + dy) in real})
        before = {p: [t for b in near for t in TR.world_tris(*b, p)] for p in ORDER}
        after = {p: list(ts) for p, ts in before.items()}
        region = set()
        for b, tws in plan.items():
            for tw in tws:
                if isinstance(tw, TR.DropTris):
                    after[tw.part] = [t for t in after[tw.part] if tw._key_set(t) not in tw.keys]
                elif isinstance(tw, TR.EmitTris):
                    em = tw.emit()
                    after[tw.part] += em
                    for t in em:
                        c = TR._plan_centroid(t)
                        region.add((math.floor(c[0] / 4), math.floor(c[1] / 4)))
        xs = [i * 4 for i, _ in region]
        zs = [j * 4 for _, j in region]
        pad = 24
        box = (min(xs) - pad, max(xs) + 4 + pad, min(zs) - pad, max(zs) + 4 + pad)
        img0, _b0 = raster(before, box, tex)
        img1, band1 = raster(after, box, tex)
        H, W = img0.shape[:2]
        canvas = Image.new("RGB", (3 * W + 20, H), (255, 255, 255))
        canvas.paste(Image.fromarray(img0), (0, 0))
        canvas.paste(Image.fromarray(img1), (W + 10, 0))
        bimg = Image.fromarray(band1)
        dr = ImageDraw.Draw(bimg)
        for (i, j) in region:
            for d, (di, dj) in TR._DIRS.items():
                if (i + di, j + dj) in region:
                    continue
                if d in ("E", "W"):
                    x = ((i + (1 if d == "E" else 0)) * 4 - box[0]) * PX
                    dr.line([(x, (box[3] - (j + 1) * 4) * PX), (x, (box[3] - j * 4) * PX)], fill=(255, 220, 0))
                else:
                    zz = ((j + (1 if d == "N" else 0)) * 4)
                    y = (box[3] - zz) * PX
                    dr.line([((i * 4 - box[0]) * PX, y), (((i + 1) * 4 - box[0]) * PX, y)], fill=(255, 220, 0))
        canvas.paste(bimg, (2 * W + 20, 0))
        out = HERE / "out" / f"sh_q6_{int(at[0])}_{int(-at[1])}.png"
        canvas.save(out)
        print(out, rep["bands"], "shore", rep["shore_tris"], "keel", rep["keel_to_open"])


if __name__ == "__main__":
    main()
