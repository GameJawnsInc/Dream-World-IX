"""Take 8's SW window from ABOVE, textured with the real atlas, with the three suspects outlined.

Read-only. Rasterizes every terrain tri in the ROI top-down (north up, east right), the TOP surface
winning, uv -> atlas pixel as (u, 1 - v) (calibrated: lawn samples green, rock grey). Outlines:
  red     -- THE SLIVER suspects: minted ROCK lying near-flat at the lawn (ny >= 0.68, top < lawn + 0.5)
  yellow  -- THE TRANSITION BAND: minted rock wearing the r10 c6-9 fringed tiles
  cyan    -- THE WEDGE suspects: minted GRASS take 8's rule (b) emitted inside the rock outline
Writes take8_defect_view.png into the (gitignored) take-8 harness run dir -- it carries atlas pixels.

    py studies/overworld-topography/west-seam-continent/take8_defect_view.py
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from take8_defect_census import LAWN, geom, load, tile            # noqa: E402
from profile_base_measure import donor_data, fit_transform, uvkey   # noqa: E402

ROI = (1404.0, -500.0, 1452.0, -452.0)
S = 18
W, H = int((ROI[2] - ROI[0]) * S), int((ROI[3] - ROI[1]) * S)
REPO_RUNS = HERE.parents[2] / ".harness-runs" / "20261006-105632-rimwalk-take8"     # gitignored
MOG = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\MoguriMain\StreamingAssets"
           r"\assets\resources\worldmap\textures\res(1_24)_terrain.png")


def px(x, z):
    return ((x - ROI[0]) * S, (ROI[3] - z) * S)


def main():
    atlas = np.asarray(Image.open(MOG).convert("RGB"))
    AH, AW = atlas.shape[:2]
    dn_tris, dn_keys = donor_data()
    rows = load()
    st = [(r["w"][0], r["w"][1], r["w"][2], r["topo"]) for r in rows]
    xf = fit_transform(st, [uvkey(r["uv"]) for r in rows], dn_tris, dn_keys)
    vset = set()
    for t in dn_tris:
        for v in t[:3]:
            w = xf(v)
            vset.add((round(w[0], 1), round(w[1], 1), round(w[2], 1)))
    img = np.zeros((H, W, 3), np.uint8)
    depth = np.full((H, W), -1e9)
    gx, gz = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
    wx, wz = ROI[0] + gx / S, ROI[3] - gz / S
    marks = []
    for r in rows:
        g = geom(r["w"])
        cx, _, cz = g["c"]
        if not (ROI[0] - 8 <= cx <= ROI[2] + 8 and ROI[1] - 8 <= cz <= ROI[3] + 8):
            continue
        (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = r["w"]
        d = (z1 - z2) * (x0 - x2) + (x2 - x1) * (z0 - z2)
        if abs(d) < 1e-9:
            continue
        xs, zs = (x0, x1, x2), (z0, z1, z2)
        i0 = max(0, int((ROI[3] - max(zs)) * S)); i1 = min(H, int((ROI[3] - min(zs)) * S) + 2)
        j0 = max(0, int((min(xs) - ROI[0]) * S)); j1 = min(W, int((max(xs) - ROI[0]) * S) + 2)
        if i0 >= i1 or j0 >= j1:
            continue
        X, Z = wx[i0:i1, j0:j1], wz[i0:i1, j0:j1]
        a = ((z1 - z2) * (X - x2) + (x2 - x1) * (Z - z2)) / d
        b = ((z2 - z0) * (X - x2) + (x0 - x2) * (Z - z2)) / d
        c = 1 - a - b
        inside = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6)
        y = a * y0 + b * y1 + c * y2
        win = inside & (y > depth[i0:i1, j0:j1])
        if not win.any():
            continue
        (u0, v0), (u1, v1), (u2, v2) = r["uv"]
        u = a * u0 + b * u1 + c * u2
        v = a * v0 + b * v1 + c * v2
        ax = np.clip((u * AW).astype(int), 0, AW - 1)
        ay = np.clip(((1 - v) * AH).astype(int), 0, AH - 1)
        sub = img[i0:i1, j0:j1]
        sub[win] = atlas[ay[win], ax[win]]
        depth[i0:i1, j0:j1][win] = y[win]
        minted = not all((round(p[0], 1), round(p[1], 1), round(p[2], 1)) in vset for p in r["w"])
        if not (ROI[0] <= cx <= ROI[2] and ROI[1] <= cz <= ROI[3]) or not minted:
            continue
        tr, tc = tile(r["uv"])
        r = dict(r, **g)
        if r["topo"] == 49 and g["ny"] >= 0.68 and g["ymax"] < LAWN + 0.5:
            marks.append(("sliver", r))
        elif r["topo"] == 49 and tr == 10 and 6 <= tc <= 9:
            marks.append(("band", r))
        elif r["topo"] == 0 and g["ymax"] - g["ymin"] > 0.2 and cz < -482:
            marks.append(("wedge", r))
    out = Image.fromarray(img)
    dr = ImageDraw.Draw(out)
    colors = {"sliver": (255, 40, 40), "band": (255, 230, 0), "wedge": (0, 255, 255)}
    import os as _os
    for kind, r in (marks if _os.environ.get("FF9MK_VIEW_MARKS", "1") != "0" else []):
        poly = [px(p[0], p[2]) for p in r["w"]]
        dr.polygon(poly, outline=colors[kind])
    for gxu in range(int(ROI[0]), int(ROI[2]) + 1, 8):
        dr.text(px(gxu, ROI[3]), str(gxu), fill=(255, 255, 255))
    for gzu in range(int(ROI[1]), int(ROI[3]) + 1, 8):
        dr.text(px(ROI[0], gzu), str(gzu), fill=(255, 255, 255))
    import os
    dest = Path(os.environ.get("FF9MK_VIEW_OUT", str(REPO_RUNS / "take8_defect_view.png")))   # atlas pixels: never committed
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    from collections import Counter
    print("marked:", Counter(k for k, _ in marks), "->", "take8_defect_view.png", out.size)
    for kind, r in marks:
        if kind == "sliver":
            print(f"  sliver t{r['tri']} blk{tuple(r['block'])} c=({r['c'][0]:.1f},{r['c'][2]:.1f}) "
                  f"y {r['ymin']:.2f}..{r['ymax']:.2f} ny {r['ny']:.2f} r{tile(r['uv'])[0]}c{tile(r['uv'])[1]}")


if __name__ == "__main__":
    main()
