#!/usr/bin/env python3
"""Bounds test: a YAWED camera (rotated off front-facing) as field 4003/MY_ROOM.

Tests the last unverified bound. A yawed camera RENDERS fine (floor + walkmesh both project through
the same yawed matrix, so they stay aligned) but the kit hardcodes the movement control-direction
(TWIST) to 0deg, so WASD is expected to be ROTATED wrong relative to the screen. This build
ISOLATES that: character_offset=0 (no planting shift), default twist, and world-axis ARROWS painted
on the floor (+Z green = world-forward, +X blue = world-right) so the playtester can report exactly
which way each key sends the player -> that pins the exact rotation for the fix.

Run:  python tools/build_yaw_test.py [yaw_deg] [twist_value]
  twist_value: optional raw SetControlDirection value to bake in (default = leave kit default -1=0deg).
"""
import os, sys, math
KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C, guide as G
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "yaw_out"))
os.makedirs(OUT, exist_ok=True)
CW, CH, S = 384, 448, 4
PITCH, DIST, FOVX = 40.0, 4500.0, 42.2
YAW = float(sys.argv[1]) if len(sys.argv) > 1 else 45.0
TWIST = int(sys.argv[2]) if len(sys.argv) > 2 else None   # None = kit default (-1 = 0deg)
CHAR_OFF = 0.0

cam = G.make_camera(PITCH, DIST, fov_x_deg=FOVX, yaw_deg=YAW)
# explicit world floor rectangle (axis-aligned in world; yaw shows up only in the projection)
X0, X1, ZF, ZB = -700, 700, -1400, 900
world = [(X0, ZB), (X1, ZB), (X1, ZF), (X0, ZF)]    # BL, BR, FR, FL (world x,z)
def cv(x, z):
    cx, cy = C.to_canvas((x, 0, z), cam); return (cx, cy)
print(f"yaw {YAW}  pitch {PITCH}  fov {FOVX}")
print("floor canvas corners:", [tuple(round(v, 1) for v in cv(x, z)) for (x, z) in world])
print("center (0,0,0) ->", tuple(round(v, 1) for v in cv(0, 0)))

# ---------- floor.png: checker + world-axis arrows ----------
img = Image.new("RGBA", (CW * S, CH * S), (0, 0, 0, 0))
dr = ImageDraw.Draw(img, "RGBA")
def px(x, z):
    cx, cy = cv(x, z); return (cx * S, cy * S)
N = 8
xs = [X0 + (X1 - X0) * i / N for i in range(N + 1)]
zs = [ZF + (ZB - ZF) * j / N for j in range(N + 1)]
for j in range(N):
    for i in range(N):
        q = [px(xs[i], zs[j]), px(xs[i + 1], zs[j]), px(xs[i + 1], zs[j + 1]), px(xs[i], zs[j + 1])]
        dr.polygon(q, fill=((95, 140, 110, 255) if (i + j) % 2 == 0 else (55, 80, 66, 255)))
# outline
out = [px(x, z) for (x, z) in world]
dr.line(out + [out[0]], fill=(255, 180, 70, 255), width=3 * S // 2)
try: fnt = ImageFont.truetype("arial.ttf", 32)
except Exception: fnt = ImageFont.load_default()
def arrow(x0, z0, x1, z1, col, lab):
    p0, p1 = px(x0, z0), px(x1, z1)
    dr.line([p0, p1], fill=col, width=4 * S)
    # arrowhead
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0]); h = 22 * S / 2
    for da in (2.6, -2.6):
        dr.line([p1, (p1[0] + h * math.cos(ang + da), p1[1] + h * math.sin(ang + da))], fill=col, width=4 * S)
    dr.text((p1[0] + 8, p1[1] - 18), lab, fill=col, font=fnt)
arrow(0, 0, 0, 600, (90, 255, 120, 255), "+Z (world fwd)")
arrow(0, 0, 600, 0, (120, 200, 255, 255), "+X (world right)")
dr.ellipse([px(0, 0)[0] - 10, px(0, 0)[1] - 10, px(0, 0)[0] + 10, px(0, 0)[1] + 10], fill=(255, 255, 255, 255))
img.save(os.path.join(OUT, "floor.png"))
Image.new("RGBA", (CW * S, CH * S), (24, 26, 32, 255)).save(os.path.join(OUT, "surround.png"))
print("wrote floor.png (checker + axis arrows) + surround.png")

twist_line = f"\ncontrol_direction = {TWIST}" if TWIST is not None else ""
toml = f"""# Yawed-camera bounds test (yaw {YAW})
[field]
id = 4003
name = "MY_ROOM"
area = 11
text_block = 1073

[camera]
pitch = {PITCH}
distance = {int(DIST)}
fov = {FOVX}
yaw = {YAW}

[walkmesh]
quad = [[{X0},{ZB}],[{X1},{ZB}],[{X1},{ZF}],[{X0},{ZF}]]
character_offset = {CHAR_OFF:g}

[[layers]]
image = "surround.png"
z = 4000
[[layers]]
image = "floor.png"
z = 3000

[player]
spawn = [0, -300]
"""
tp = os.path.join(OUT, "yaw.field.toml")
open(tp, "w", newline="\n", encoding="utf-8").write(toml)
print(f"wrote {tp}\nTWIST baked: {TWIST if TWIST is not None else 'kit default (-1 = 0 deg)'}")
