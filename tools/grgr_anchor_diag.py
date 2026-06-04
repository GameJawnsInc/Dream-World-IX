#!/usr/bin/env python3
"""Decisive walkmesh-frame diagnostic for GRGR.

Draws the real art + the walkmesh footprint under TWO candidate transforms, each with the
known anchors marked (player spawn = charPos; the high-Y "ladder" verts). The engine projects
curPos (raw .bgi frame) directly, so f0 should be exact -- the anchors tell us for sure.

  RAW.png        : verts as-is (f0), spawn dot at to_canvas(charPos)
  ORGPOS3D.png   : verts + full orgPos (x,y,z), spawn dot at to_canvas(charPos+orgPos)
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

path, folder, roles, env = extract.find_field(FIELD)
bgs_b = extract._raw_bytes(env.container[roles["bgs"]].read())
wm = bgi.BgiWalkmesh.from_bytes(extract._raw_bytes(env.container[roles["bgi"]].read()))
c0 = bgs.parse_cameras(bgs_b)[0]
org = (wm.orgPos.x, wm.orgPos.y, wm.orgPos.z)

# high-Y "ladder" verts (the structure that climbs in Y)
ymax = max(v.y for v in wm.verts)
ladder = {i for i, v in enumerate(wm.verts) if v.y > 0.5 * ymax}
print(f"orgPos={org}  ymax={ymax}  ladder verts={sorted(ladder)} (y>{0.5*ymax:.0f})")


def base_art():
    """The opaque BASEONLY composite (no footprint), as the backdrop."""
    p = os.path.join(OUT, "_base.png")
    extract.compose_background(FIELD, p, draw_footprint=False)
    return Image.open(p).convert("RGBA")


def render(name, off3d):
    canvas = base_art().copy()
    d = ImageDraw.Draw(canvas, "RGBA")
    ox, oy, oz = off3d
    # walkmesh tris
    for t in wm.tris:
        pts = []
        lad = False
        for vi in t.vtx:
            v = wm.verts[vi]
            cx, cy = cam.to_canvas((v.x + ox, v.y + oy, v.z + oz), c0)
            pts.append((cx * UP, cy * UP))
            if vi in ladder:
                lad = True
        col = (255, 120, 0, 90) if lad else (90, 180, 255, 45)
        out = (255, 200, 0, 220) if lad else (120, 225, 255, 160)
        d.polygon(pts, fill=col, outline=out)
    # spawn anchor (charPos + same offset) -- the exact in-game spawn under this transform
    sx, sy = cam.to_canvas((wm.charPos.x + ox, wm.charPos.y + oy, wm.charPos.z + oz), c0)
    r = 14
    d.ellipse([sx * UP - r, sy * UP - r, sx * UP + r, sy * UP + r], fill=(255, 0, 255, 255),
              outline=(255, 255, 255, 255), width=3)
    p = os.path.join(OUT, name)
    canvas.save(p)
    print(f"{name}: spawn dot at canvas ({sx:.0f},{sy:.0f}) [magenta] -> {p}")


render("RAW.png", (0, 0, 0))                 # f0: engine projects curPos directly
render("ORGPOS3D.png", org)                  # vert + full orgPos (x,y,z)
