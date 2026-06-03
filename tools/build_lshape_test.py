#!/usr/bin/env python3
"""Bounds test: an L-shaped (concave) walkmesh as field 4003/MY_ROOM.

Walkable = a 2x2 quadrant grid with the BACK-RIGHT quadrant removed (the notch). Grid-aligned
edges (no T-junctions) so the only thing under test is concave navigation + confinement + the
inner corner. character_offset=0 (this is a navigation/collision test, not a planting test).
Run:  python tools/build_lshape_test.py   then deploy the printed dist.
"""
import os, sys
KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C, guide as G
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "lshape_out"))
os.makedirs(OUT, exist_ok=True)
CW, CH, S = 384, 448, 4
PITCH, DIST, FOVX = 40.0, 4500.0, 42.2
CHAR_OFF = float(sys.argv[1]) if len(sys.argv) > 1 else 298.0   # 0 = navigation test; 298 = planted

cam = G.make_camera(PITCH, DIST, fov_x_deg=FOVX)
fr = G.frame_floor(cam, back_canvas_y=160.0, front_canvas_y=400.0, half_width=820)
fx, zb, zf = fr.half_width, fr.zb, fr.zf
zmid = (zb + zf) / 2.0
print(f"floor x +/-{fx}, z front {zf} .. back {zb}, mid {zmid:.0f}")

# 8 grid verts (FF9 x,0,z); notch = back-right quad (verts 4,5,7,8 region) removed
V = [(-fx, zf), (0, zf), (fx, zf), (-fx, zmid), (0, zmid), (fx, zmid), (-fx, zb), (0, zb)]
#     0          1        2         3            4          5         6          7
FACES = [(0, 1, 4), (0, 4, 3),     # front-left quad
         (1, 2, 5), (1, 5, 4),     # front-right quad
         (3, 4, 7), (3, 7, 6)]     # back-left quad   (back-right = NOTCH, omitted)
with open(os.path.join(OUT, "lshape.obj"), "w", newline="\n") as fh:
    fh.write("# L-shaped walkmesh (FF9 world coords, y=0)\n")
    for (x, z) in V:
        fh.write(f"v {x} 0 {z}\n")
    for (a, b, c) in FACES:
        fh.write(f"f {a+1} {b+1} {c+1}\n")

# ---------- floor.png: checker on walkable cells, blocked colour on the notch, L outline ----------
img = Image.new("RGBA", (CW * S, CH * S), (0, 0, 0, 0))
dr = ImageDraw.Draw(img, "RGBA")
def px(x, z):
    cx, cy = C.to_canvas((x, 0, z), cam); return (cx * S, cy * S)
N = 8
xs = [-fx + 2 * fx * i / N for i in range(N + 1)]
zs = [zf + (zb - zf) * j / N for j in range(N + 1)]
for j in range(N):
    for i in range(N):
        xc = (xs[i] + xs[i + 1]) / 2; zc = (zs[j] + zs[j + 1]) / 2
        notch = (xc > 0) and ((zc - zmid) * (zb - zmid) > 0)   # back-right quadrant
        q = [px(xs[i], zs[j]), px(xs[i + 1], zs[j]), px(xs[i + 1], zs[j + 1]), px(xs[i], zs[j + 1])]
        if notch:
            dr.polygon(q, fill=(150, 40, 40, 255))             # blocked (not walkable)
        else:
            dr.polygon(q, fill=((95, 140, 110, 255) if (i + j) % 2 == 0 else (55, 80, 66, 255)))
# L boundary outline
bnd = [px(-fx, zf), px(fx, zf), px(fx, zmid), px(0, zmid), px(0, zb), px(-fx, zb)]
dr.line(bnd + [bnd[0]], fill=(255, 180, 70, 255), width=3 * S // 2)
try: fnt = ImageFont.truetype("arial.ttf", 30)
except Exception: fnt = ImageFont.load_default()
nx, nz = fx / 2, (zmid + zb) / 2
dr.text(px(nx, nz), "NOTCH\n(blocked)", fill=(255, 200, 200, 255), font=fnt)
img.save(os.path.join(OUT, "floor.png"))
Image.new("RGBA", (CW * S, CH * S), (24, 26, 32, 255)).save(os.path.join(OUT, "surround.png"))
print("wrote lshape.obj + floor.png + surround.png")

# spawn in the front-centre; shift toward the camera by the char offset so it lands on the
# (camera-ward shifted) walkmesh, same as the kit does to the floor.
spawn_z = int((zf + zmid) / 2 - (CHAR_OFF if zf < zb else -CHAR_OFF))
toml = f"""# L-shaped walkmesh bounds test (pitch {PITCH})
[field]
id = 4003
name = "MY_ROOM"
area = 11
text_block = 1073

[camera]
pitch = {PITCH}
distance = {int(DIST)}
fov = {FOVX}

[walkmesh]
obj = "lshape.obj"
character_offset = {CHAR_OFF:g}

[[layers]]
image = "surround.png"
z = 4000
[[layers]]
image = "floor.png"
z = 3000

[player]
spawn = [0, {spawn_z}]
"""
tp = os.path.join(OUT, "lshape.field.toml")
open(tp, "w", newline="\n", encoding="utf-8").write(toml)
print(f"wrote {tp}\nspawn (0,{spawn_z}); notch = back-right quadrant (x>0, z toward back)")
