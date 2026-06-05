#!/usr/bin/env python3
"""Build an OFFSET-CALIBRATION field for 4003: a flat world-frame walkmesh (org=0, NO character
offset) + a floor grid painted EXACTLY at to_canvas() of known world coords, with a 200u checker,
a RED origin cell (world 0,0), and bright CYAN x=0 / z=0 axes. The player spawns at world (0,0).

Measurement: the engine FF9PROBE logs the player's exact world P; the user reads where the feet sit
on the painted grid (cells = 200 world u). If feet land on the cell matching P -> the character is
projected by to_canvas like the floor (NO real offset; the old 298 was the org=300 artifact). Any
gap = the real character offset, read in world units.

Writes the field.toml + grid PNG to tools/scroll_out/offset_calib/ ; deploy with tools/deploy_field.py.
"""
import os, sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C, guide, placeholder

OUT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "scroll_out", "offset_calib")))
OUT.mkdir(parents=True, exist_ok=True)

# camera = the SMOKE/room camera (proj 498 -> matches the in-game PROJ=498 in the probe log).
# Optional argv[1] = pitch (default 48) to retest the offset at a different angle.
PITCH = float(sys.argv[1]) if len(sys.argv) > 1 else 48.0
cam = guide.make_camera(PITCH, 4500.0, fov_x_deg=42.2)
SCALE = 4
W, H = cam.range[0] * SCALE, cam.range[1] * SCALE

# floor extent (world): a grid the player can walk; spawn at (0,0)
X0, X1, Z0, Z1 = -1000, 1000, -1500, 300       # walkmesh quad (world)
CELL = 200                                      # grid cell, world units
GX0, GX1, GZ0, GZ1 = -1200, 1200, -1700, 500    # painted grid extent (a bit larger than walkmesh)

buf = bytearray(bytes((20, 24, 30, 255))) * (W * H)   # dark backdrop

def px(x, z):
    cx, cy = C.to_canvas((x, 0.0, z), cam)
    return (cx * SCALE, cy * SCALE)

# checkerboard cells (200u), red origin cell, via to_canvas (exact)
xs = list(range(GX0, GX1, CELL))
zs = list(range(GZ0, GZ1, CELL))
for zi, z in enumerate(zs):
    for xi, x in enumerate(xs):
        corners = [px(x, z), px(x + CELL, z), px(x + CELL, z + CELL), px(x, z + CELL)]
        if x == 0 and z == 0:
            col = (220, 60, 60, 255)            # RED origin cell (world 0,0 .. 200,200)
        elif (xi + zi) % 2 == 0:
            col = (200, 165, 95, 255)
        else:
            col = (150, 110, 60, 255)
        placeholder._fill_quad(buf, W, H, corners, col)

def line(p0, p1, col, thick=2):
    x0, y0 = p0; x1, y1 = p1
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t; y = y0 + (y1 - y0) * t
        for ox in range(-thick, thick + 1):
            for oy in range(-thick, thick + 1):
                xi, yi = int(x) + ox, int(y) + oy
                if 0 <= xi < W and 0 <= yi < H:
                    o = (yi * W + xi) * 4
                    buf[o], buf[o + 1], buf[o + 2], buf[o + 3] = col

# bright CYAN axes: x=0 (a z-running line) and z=0 (an x-running line)
CYAN = (60, 230, 230, 255)
line(px(0, GZ0), px(0, GZ1), CYAN, 2)
line(px(GX0, 0), px(GX1, 0), CYAN, 2)
# YELLOW major lines every 1000u (5 cells) so counting is easy
YEL = (240, 230, 90, 255)
for x in range(GX0, GX1 + 1, 1000):
    if x != 0:
        line(px(x, GZ0), px(x, GZ1), YEL, 1)
for z in range(GZ0, GZ1 + 1, 1000):
    if z != 0:
        line(px(GX0, z), px(GX1, z), YEL, 1)

with open(OUT / "grid.png", "wb") as fh:
    fh.write(placeholder._png_rgba(W, H, buf))

# camera.bgx + field.toml (world-frame walkmesh => org=0, no character offset)
with open(OUT / "camera.bgx", "w", encoding="utf-8", newline="\n") as fh:
    from ff9mapkit.scene import bgx
    fh.write(bgx.build(cam, [], header_comment="offset calibration camera (pitch 48)"))

quad = f"[[{X0}, {Z0}], [{X1}, {Z0}], [{X1}, {Z1}], [{X0}, {Z1}]]"
(OUT / "offset_calib.field.toml").write_text(
    "# OFFSET CALIBRATION (field 4003): world-frame walkmesh + to_canvas grid, char offset 0.\n"
    "[field]\nid = 4003\nname = \"OFFCAL\"\narea = 11\ntext_block = 1073\n\n"
    "[camera]\nborrow = \"camera.bgx\"\n\n"
    f"[walkmesh]\nquad = {quad}\nframe = \"world\"   # org=0, NO character offset -- raw world coords\n\n"
    "[[layers]]\nimage = \"grid.png\"\nz = 4000\n\n"
    "[player]\nspawn = [0, 0]   # exact world origin; the RED cell is world (0,0)..(200,200)\n",
    encoding="utf-8", newline="\n")

print(f"wrote {OUT}/offset_calib.field.toml + grid.png ({W}x{H})")
print(f"grid: 200u cells, RED origin cell=(0,0)..(200,200), CYAN axes x=0/z=0, YELLOW every 1000u")
print(f"walkmesh world x[{X0},{X1}] z[{Z0},{Z1}] (org=0); spawn (0,0)")
print(f"deploy:  py tools/deploy_field.py \"{OUT}/offset_calib.field.toml\"")
