#!/usr/bin/env python3
"""Planting calibration room: measure the depth-dependent character-foot offset.

Deploys a DEEP floor (front->back) with character_offset=0, so the walkmesh projects EXACTLY onto
the painted floor (no planting shift). A painted ruler of labeled canvas-Y lines lets the human read
where Zidane's FEET land at a few known depths. We then fit feet_canvasY = f(walkmesh_canvasY) and
replace the constant character_offset with a depth-correct correction.

Reuses the user's scroll camera (so it applies to their rooms). Deploys to field 4003 reversibly.
Run:  python tools/build_planting_calib.py
"""
import os, sys, tempfile, shutil
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C
from PIL import Image, ImageDraw, ImageFont

CAMBGX = Path(KIT) / "blender" / "debug_proj" / "scroll_test_1" / "ff9field" / "camera.bgx"
cam = C.parse_bgx_cameras(str(CAMBGX))[0]
RW, RH = int(cam.range[0]), int(cam.range[1])
S = 4
BACK_CY, FRONT_CY = 150.0, 446.0          # deep floor: spans most of the screen vertically

zb = C.solve_z_for_canvasY(cam, BACK_CY)
zf = C.solve_z_for_canvasY(cam, FRONT_CY)
# fill the width at the front row
def solve_x(target_cx, z, lo=-30000.0, hi=30000.0):
    f0 = C.to_canvas((lo, 0, z), cam)[0] - target_cx
    for _ in range(80):
        m = 0.5 * (lo + hi); fm = C.to_canvas((m, 0, z), cam)[0] - target_cx
        if abs(fm) < 0.01: return m
        if (fm > 0) == (f0 > 0): lo, f0 = m, fm
        else: hi = m
    return 0.5 * (lo + hi)
FX = round(min(abs(solve_x(40.0, zf)), abs(solve_x(RW - 40.0, zf))))
zmid = C.solve_z_for_canvasY(cam, 0.5 * (BACK_CY + FRONT_CY))
print(f"camera pitch {C.pitch_deg(cam):.1f}, proj {cam.proj}")
print(f"floor world: x +/-{FX}, z {zf:.0f}(front,cy{FRONT_CY:.0f}) .. {zb:.0f}(back,cy{BACK_CY:.0f})")
print(f"spawn (mid) world z {zmid:.0f} -> canvas y {C.to_canvas((0,0,zmid),cam)[1]:.0f}")

# ---------- paint: floor + canvas-Y ruler ----------
img = Image.new("RGBA", (RW * S, RH * S), (0, 0, 0, 0))
dr = ImageDraw.Draw(img, "RGBA")
def cv(x, z): cx, cy = C.to_canvas((x, 0, z), cam); return (cx * S, cy * S)
# floor fill (the walkmesh quad, projected)
quad = [cv(-FX, zb), cv(FX, zb), cv(FX, zf), cv(-FX, zf)]
dr.polygon(quad, fill=(70, 74, 84, 255))
try: fnt = ImageFont.truetype("arialbd.ttf", 13 * S)
except Exception: fnt = ImageFont.load_default()
# horizontal ruler lines every 16 canvas-Y (aligned to 16 so multiples of 32 get labels)
start = ((int(BACK_CY) + 15) // 16) * 16
for cyv in range(start, int(FRONT_CY) + 1, 16):
    z = C.solve_z_for_canvasY(cam, float(cyv))
    if z is None: continue
    p0 = cv(-FX, z); p1 = cv(FX, z)
    major = (cyv % 32 == 0)
    dr.line([p0, p1], fill=(130, 205, 255, 255) if major else (80, 120, 160, 220),
            width=(2 * S if major else S))
    if major:
        for tx in (p0[0] + 8 * S, (p0[0] + p1[0]) / 2 - 18 * S, p1[0] - 44 * S):  # left, center, right
            dr.text((tx, p0[1] - 9 * S), str(cyv), fill=(210, 240, 255, 255), font=fnt,
                    stroke_width=2 * S, stroke_fill=(0, 0, 0, 255))
# spawn marker (where Zidane starts = known mid depth)
sp = cv(0, zmid)
dr.line([(sp[0] - 30 * S, sp[1]), (sp[0] + 30 * S, sp[1])], fill=(120, 255, 140, 255), width=3 * S)
dr.text((sp[0] + 34 * S, sp[1] - 8 * S), "SPAWN", fill=(120, 255, 140, 255), font=fnt,
        stroke_width=S, stroke_fill=(0, 0, 0, 255))
OUT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "scroll_out", "calib")))
OUT.mkdir(parents=True, exist_ok=True)
img.save(OUT / "floor.png")
Image.new("RGBA", (RW * S, RH * S), (16, 18, 22, 255)).save(OUT / "surround.png")

# ---------- field.toml (character_offset = 0) ----------
shutil.copyfile(CAMBGX, OUT / "camera.bgx")
SPX, SPZ = 0, round(zmid)
toml = f"""[field]
id = 4003
name = "MY_ROOM"
area = 11
text_block = 1073
[camera]
borrow = "camera.bgx"
[camera.scroll]
enabled = true
[walkmesh]
quad = [[{-FX},{zb:.0f}],[{FX},{zb:.0f}],[{FX},{zf:.0f}],[{-FX},{zf:.0f}]]
character_offset = 0
[[layers]]
image = "surround.png"
z = 4000
[[layers]]
image = "floor.png"
z = 3000
[player]
spawn = [{SPX}, {SPZ}]
"""
(OUT / "calib.field.toml").write_text(toml, encoding="utf-8", newline="\n")
print(f"wrote {OUT}")
# report the known measurement depths (walkmesh edge centers, accounting for collision radius)
rad = C.COLLISION_RADIUS_W
print("\n=== KNOWN player-CENTER depths to report feet for (collision radius %.0f accounted) ===" % rad)
print("  SPAWN  : center canvas-Y %.0f (don't move yet)" % C.to_canvas((0,0,zmid),cam)[1])
print("  FRONT  : walk DOWN to the stop; center canvas-Y ~%.0f" % C.to_canvas((0,0,zf+rad),cam)[1])
print("  BACK   : walk UP to the stop;   center canvas-Y ~%.0f" % C.to_canvas((0,0,zb-rad),cam)[1])
