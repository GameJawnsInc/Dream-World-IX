#!/usr/bin/env python3
"""Color-code GRGR's walkmesh by FLOOR on the art, + analyze the Y (height) structure.

Tells us whether the "stacked shapes" the user sees are a real positioning bug or just a
genuinely multi-level 3D walkmesh (ground/platforms/ramps/ladder/tunnels) projected to one
flat wireframe (overlap is then expected + correct).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
from ff9mapkit import extract
from ff9mapkit.scene import bgs, bgi, cam
from PIL import Image, ImageDraw

FIELD = "grgr_map420_gr_cen"
OUT = os.path.join(os.path.dirname(__file__), "scroll_out", "p0spike")
UP = 4
COLORS = [(255, 80, 80), (80, 200, 255), (120, 255, 120), (255, 220, 60),
          (255, 130, 255), (120, 160, 255), (255, 170, 70)]

path, folder, roles, env = extract.find_field(FIELD)
bgs_b = extract._raw_bytes(env.container[roles["bgs"]].read())
wm = bgi.BgiWalkmesh.from_bytes(extract._raw_bytes(env.container[roles["bgi"]].read()))
c0 = bgs.parse_cameras(bgs_b)[0]

# tri -> floor index (each Floor lists its tri indices)
tri_floor = {}
for fi, fl in enumerate(wm.floors):
    for ti in fl.tri_ndx_list:
        tri_floor[ti] = fi

print("floor   ntris  vert-Y range (of its tris)   sample tri canvas extent")
for fi, fl in enumerate(wm.floors):
    ys, cxs, cys = [], [], []
    for ti in fl.tri_ndx_list:
        for vi in wm.tris[ti].vtx:
            v = wm.verts[vi]
            ys.append(v.y)
            cx, cy = cam.to_canvas((v.x, v.y, v.z), c0)
            cxs.append(cx); cys.append(cy)
    print(f"  {fi}    {len(fl.tri_ndx_list):3d}   Y[{min(ys):5d},{max(ys):5d}]   "
          f"canvas x[{min(cxs):6.0f},{max(cxs):6.0f}] y[{min(cys):6.0f},{max(cys):6.0f}]")

# overall Y histogram (how flat is it really?)
yvals = [v.y for v in wm.verts]
flat = sum(1 for y in yvals if y == 0)
print(f"\nverts: {len(yvals)} total, {flat} at Y=0 ({100*flat//len(yvals)}%), "
      f"Y distinct = {sorted(set(yvals))[:12]}{'...' if len(set(yvals))>12 else ''}")

# base art
base = os.path.join(OUT, "_base.png")
extract.compose_background(FIELD, base, draw_footprint=False)

# one image per-floor-colored, real Y
canvas = Image.open(base).convert("RGBA")
d = ImageDraw.Draw(canvas, "RGBA")
for ti, t in enumerate(wm.tris):
    fi = tri_floor.get(ti, 0)
    r, g, b = COLORS[fi % len(COLORS)]
    pts = []
    for vi in t.vtx:
        v = wm.verts[vi]
        cx, cy = cam.to_canvas((v.x, v.y, v.z), c0)
        pts.append((cx * UP, cy * UP))
    d.polygon(pts, fill=(r, g, b, 70), outline=(r, g, b, 230))
p = os.path.join(OUT, "FLOORS_realY.png")
canvas.save(p)
print(f"\nwrote {p}  (each floor a distinct color, real-Y GTE projection)")
