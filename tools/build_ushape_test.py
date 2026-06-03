#!/usr/bin/env python3
"""Bounds test: a U-shaped (concave) walkmesh as field 4003/MY_ROOM.

Harder than the L: the blocked bay is open at the BACK-CENTER (not at a corner), so the walkable
area WRAPS AROUND it -> TWO inner corners, and the player can walk up the left arm, across the
front, and up the right arm but never through the middle-back. Grid: 3 columns x 2 rows, with the
back-center cell removed. character_offset=298 (planting proven on the L; this also confirms it on
non-rectangular geometry).
Run:  python tools/build_ushape_test.py [char_off]   then deploy the printed dist.
"""
import os, sys
KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C, guide as G
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "ushape_out"))
os.makedirs(OUT, exist_ok=True)
CW, CH, S = 384, 448, 4
PITCH, DIST, FOVX = 40.0, 4500.0, 42.2
CHAR_OFF = float(sys.argv[1]) if len(sys.argv) > 1 else 298.0

cam = G.make_camera(PITCH, DIST, fov_x_deg=FOVX)
fr = G.frame_floor(cam, back_canvas_y=160.0, front_canvas_y=400.0, half_width=820)
fx, zb, zf = fr.half_width, fr.zb, fr.zf
zmid = (zb + zf) / 2.0
# three columns: x edges at -fx, -fx/3, fx/3, fx ; two rows: front(zf), mid, back(zb)
xs4 = [-fx, -fx / 3.0, fx / 3.0, fx]
zs3 = [zf, zmid, zb]
print(f"floor x +/-{fx}, z front {zf} .. back {zb}; cols {[round(x) for x in xs4]}")

# 12 grid verts V[idx] with idx = row*4 + col  (row 0=front,1=mid,2=back)
V = [(xs4[i], zs3[j]) for j in range(3) for i in range(4)]
def idx(i, j): return j * 4 + i
# 6 cells (3 cols x 2 rows); remove the BACK-CENTER cell (col 1, row 1) = the U opening
FACES = []
for j in range(2):          # row 0 front, row 1 back
    for i in range(3):      # col 0,1,2
        if i == 1 and j == 1:
            continue        # NOTCH: back-center cell removed
        a, b = idx(i, j), idx(i + 1, j)
        c, d = idx(i + 1, j + 1), idx(i, j + 1)
        FACES += [(a, b, c), (a, c, d)]
with open(os.path.join(OUT, "ushape.obj"), "w", newline="\n") as fh:
    fh.write("# U-shaped walkmesh (FF9 world coords, y=0)\n")
    for (x, z) in V:
        fh.write(f"v {x} 0 {z}\n")
    for (a, b, c) in FACES:
        fh.write(f"f {a+1} {b+1} {c+1}\n")

# ---------- floor.png: checker on walkable cells, blocked colour on the bay, U outline ----------
img = Image.new("RGBA", (CW * S, CH * S), (0, 0, 0, 0))
dr = ImageDraw.Draw(img, "RGBA")
def px(x, z):
    cx, cy = C.to_canvas((x, 0, z), cam); return (cx * S, cy * S)
N = 9
xs = [-fx + 2 * fx * i / N for i in range(N + 1)]
zs = [zf + (zb - zf) * j / N for j in range(N + 1)]
for j in range(N):
    for i in range(N):
        xc = (xs[i] + xs[i + 1]) / 2; zc = (zs[j] + zs[j + 1]) / 2
        # blocked bay = center column (|x|<fx/3) AND back half (z on back side of zmid)
        bay = (abs(xc) < fx / 3.0) and ((zc - zmid) * (zb - zmid) > 0)
        q = [px(xs[i], zs[j]), px(xs[i + 1], zs[j]), px(xs[i + 1], zs[j + 1]), px(xs[i], zs[j + 1])]
        if bay:
            dr.polygon(q, fill=(150, 40, 40, 255))             # blocked bay
        else:
            dr.polygon(q, fill=((95, 140, 110, 255) if (i + j) % 2 == 0 else (55, 80, 66, 255)))
# U boundary outline: front full, up the two arms, around the bay
bnd = [px(-fx, zf), px(fx, zf), px(fx, zb), px(fx / 3.0, zb),
       px(fx / 3.0, zmid), px(-fx / 3.0, zmid), px(-fx / 3.0, zb), px(-fx, zb)]
dr.line(bnd + [bnd[0]], fill=(255, 180, 70, 255), width=3 * S // 2)
try: fnt = ImageFont.truetype("arial.ttf", 30)
except Exception: fnt = ImageFont.load_default()
dr.text(px(0, (zmid + zb) / 2), "BAY\n(blocked)", fill=(255, 200, 200, 255), font=fnt)
img.save(os.path.join(OUT, "floor.png"))
Image.new("RGBA", (CW * S, CH * S), (24, 26, 32, 255)).save(os.path.join(OUT, "surround.png"))
print(f"wrote ushape.obj ({len(V)} verts, {len(FACES)} tris) + floor.png + surround.png")

# spawn in the front-centre (walkable); shift toward the camera by the char offset like the kit.
spawn_z = int((zf + zmid) / 2 - (CHAR_OFF if zf < zb else -CHAR_OFF))
toml = f"""# U-shaped walkmesh bounds test (pitch {PITCH})
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
obj = "ushape.obj"
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
tp = os.path.join(OUT, "ushape.field.toml")
open(tp, "w", newline="\n", encoding="utf-8").write(toml)
print(f"wrote {tp}\nspawn (0,{spawn_z}); bay = back-center cell (|x|<{fx/3:.0f}, back half)")
