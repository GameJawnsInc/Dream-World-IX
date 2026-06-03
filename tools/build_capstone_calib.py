#!/usr/bin/env python3
"""Capstone: a clean field 4003/BLENDERROOM built end-to-end by ff9mapkit with the NEW exact
scale-1 canvas map. Checkerboard floor + bright edge outline drawn via to_canvas; walkmesh
EXTENDED outward by the collision radius so the player's feet reach the painted edges. Proves
the corrected map in real gameplay (back edge now symmetric with front/sides).

Run:  python tools/build_capstone_calib.py
Then deploy with the printed dist path. (Offline only; human playtests.)
"""
import os, sys, math
KIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ff9mapkit")
sys.path.insert(0, os.path.abspath(KIT))
from ff9mapkit.scene import cam as C, guide as G
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "capstone_out"))
os.makedirs(OUT, exist_ok=True)
CW, CH = 384, 448
PITCH, DIST, FOVX = 40.0, 4500.0, 42.2   # FOVX must match build.py's [camera] fov default (proj 498)
RAD = int(C.COLLISION_RADIUS_W)          # ~48 world units the player centre can't cross

cam = G.make_camera(PITCH, DIST, fov_x_deg=FOVX)
print(f"camera: pitch {PITCH}  proj {cam.proj}  FOVx {C.decompose(cam)['fov_x_deg']:.1f}")

# frame the painted floor between two canvas rows (the NEW scale-1 map).
# explicit half-width so all four edges stay on-screen (the floor is wide at the near edge).
frame = G.frame_floor(cam, back_canvas_y=160.0, front_canvas_y=400.0, half_width=820)
fx, zb, zf = frame.half_width, frame.zb, frame.zf
print(f"painted floor: x +/-{fx}, z [{zf}(front)..{zb}(back)]   canvas corners {frame.corners_canvas}")

# walkmesh = floor extended OUTWARD by the collision radius so feet reach the painted edge
cz = (zb + zf) / 2.0
zb_w = zb + (RAD if zb > cz else -RAD)
zf_w = zf + (RAD if zf > cz else -RAD)
wm = [(-fx - RAD, zb_w), (fx + RAD, zb_w), (fx + RAD, zf_w), (-fx - RAD, zf_w)]
print(f"walkmesh (extended {RAD}u): {wm}")

# ---------- draw the painted layers via the NEW to_canvas ----------
S = 4
def px(P):
    x, y = C.to_canvas(P, cam); return (x * S, y * S)

# surround (full canvas, opaque dark teal so the floor region reads clearly)
sur = Image.new("RGBA", (CW * S, CH * S), (26, 32, 40, 255))
sur.save(os.path.join(OUT, "csurround.png"))

# floor: transparent except the floor region -> checkerboard + bright edge outline
flo = Image.new("RGBA", (CW * S, CH * S), (0, 0, 0, 0))
dr = ImageDraw.Draw(flo, "RGBA")
NX, NZ = 6, 6
xs = [-fx + 2 * fx * i / NX for i in range(NX + 1)]
zs = [zb + (zf - zb) * j / NZ for j in range(NZ + 1)]
for j in range(NZ):
    for i in range(NX):
        q = [px((xs[i], 0, zs[j])), px((xs[i + 1], 0, zs[j])),
             px((xs[i + 1], 0, zs[j + 1])), px((xs[i], 0, zs[j + 1]))]
        dr.polygon(q, fill=((95, 120, 150, 255) if (i + j) % 2 == 0 else (55, 68, 86, 255)))
# bright outline at the PAINTED floor edge (this is the line the feet should land on)
edge = [px((-fx, 0, zb)), px((fx, 0, zb)), px((fx, 0, zf)), px((-fx, 0, zf))]
dr.line(edge + [edge[0]], fill=(255, 180, 70, 255), width=4)
# label each edge
try: fnt = ImageFont.truetype("arial.ttf", 34)
except Exception: fnt = ImageFont.load_default()
def lab(P, t, col=(255, 230, 120, 255)):
    x, y = px(P); dr.text((x - 30, y - 18), t, fill=col, font=fnt)
lab((0, 0, zb), "BACK"); lab((0, 0, zf), "FRONT")
lab((-fx, 0, (zb + zf) / 2), "L"); lab((fx, 0, (zb + zf) / 2), "R")
flo.save(os.path.join(OUT, "cfloor.png"))
print(f"wrote {OUT}/csurround.png + cfloor.png")

# ---------- field.toml ----------
toml = f"""# Capstone calibration room — exact scale-1 canvas map (ff9mapkit)
[field]
id = 4003
name = "BLENDERROOM"
area = 11
text_block = 1073

[camera]
pitch = {PITCH}
distance = {int(DIST)}
fov = {FOVX}

[walkmesh]
quad = [[{wm[0][0]},{wm[0][1]}],[{wm[1][0]},{wm[1][1]}],[{wm[2][0]},{wm[2][1]}],[{wm[3][0]},{wm[3][1]}]]

[[layers]]
image = "csurround.png"
z = 4000
[[layers]]
image = "cfloor.png"
z = 3000

[player]
spawn = [0, {int((zb + zf) / 2)}]
"""
tp = os.path.join(OUT, "capstone.field.toml")
open(tp, "w", newline="\n", encoding="utf-8").write(toml)
print(f"wrote {tp}")
print("\nNext: ff9mapkit build " + tp + " --out <dist>")
