"""Render the outline census to a readable map -- the eye's half of the shape study.

  py studies/coast-shape-language/outline_render.py [--disc 1] [--px 3]
  py studies/coast-shape-language/outline_render.py --mass 4 --px 8    # one mass, zoomed

Sea is flat, land is split into standable (green) and scenery (grey) so the
walkable-vs-visible distinction the census measured is visible at a glance. Block
lines every 16 cells (64u) because the block grid is the unit every builder verb
(transplant / fuse / island) actually works in.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
G, BLOCK = 4.0, 64.0
CPB = int(BLOCK / G)                       # 16 cells per block

SEA = (24, 44, 78)
FOOT_C = (104, 158, 84)
SCENERY = (122, 116, 104)
GRID = (44, 66, 100)
HOT = (232, 168, 64)


def load(disc: int):
    d = np.load(HERE / "out" / f"landmask_d{disc}.npz")
    return d["land"], d["foot"], d["hgt"], d["topo"]


def render(land, foot, px: int, *, box=None, label=None):
    gh, gw = land.shape
    if box:
        x0, z0, x1, z1 = box
        land, foot = land[z0:z1, x0:x1], foot[z0:z1, x0:x1]
        gh, gw = land.shape
    else:
        x0, z0 = 0, 0
    img = np.zeros((gh, gw, 3), dtype=np.uint8)
    img[:] = SEA
    img[land] = SCENERY
    img[foot] = FOOT_C
    im = Image.fromarray(img).resize((gw * px, gh * px), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    for gx in range(gw + 1):
        if (x0 + gx) % CPB == 0:
            dr.line([(gx * px, 0), (gx * px, gh * px)], fill=GRID)
    for gz in range(gh + 1):
        if (z0 + gz) % CPB == 0:
            dr.line([(0, gz * px), (gw * px, gz * px)], fill=GRID)
    for m in label or []:
        cx, cz = m["centroid_cell"]
        dr.text(((cx - x0) * px + 2, (cz - z0) * px + 2), f"#{m['id']}", fill=HOT)
    return im


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", type=int, default=1)
    ap.add_argument("--px", type=int, default=3)
    ap.add_argument("--mass", type=int, default=None,
                    help="crop to this LAND mass id (from outline_dN.json)")
    ap.add_argument("--pad", type=int, default=6, help="cells of margin when cropping")
    args = ap.parse_args()

    land, foot, _, _ = load(args.disc)
    meta = json.loads((HERE / "out" / f"outline_d{args.disc}.json").read_text())
    masses = [m for m in meta["land"] if m["cells"] >= 16]

    if args.mass is None:
        im = render(land, foot, args.px, label=masses[:12])
        p = HERE / "out" / f"outline_d{args.disc}.png"
    else:
        m = next(x for x in meta["land"] if x["id"] == args.mass)
        cx, cz = m["centroid_cell"]
        w, h = [int(v / G) for v in m["bbox_u"]]
        x0 = max(0, cx - w // 2 - args.pad)
        z0 = max(0, cz - h // 2 - args.pad)
        box = (x0, z0, min(land.shape[1], x0 + w + 2 * args.pad),
               min(land.shape[0], z0 + h + 2 * args.pad))
        im = render(land, foot, args.px, box=box)
        p = HERE / "out" / f"mass{args.mass}_d{args.disc}.png"
    im.save(p)
    print(f"-> {p}  ({im.size[0]}x{im.size[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
