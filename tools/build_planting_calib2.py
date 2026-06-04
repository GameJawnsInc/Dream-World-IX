#!/usr/bin/env python3
"""Planting calibration v2 — CLEAN: static Zidane figures at EXACT known depths.

The v1 room used walk-to-the-edge stops, whose true depth is fuzzy (collision radius). This places
5 static Zidane NPCs (same model as the player) at depths I control exactly, each labeled with its
standing-point canvas-Y. character_offset=0, so each figure's standing point sits on its painted
ruler line; you read where its SOLES land. No collision slop -> a clean float-vs-depth curve.

Deploys to field 4003 reversibly. Run:  python tools/build_planting_calib2.py
"""
import os, sys, shutil
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C
from PIL import Image, ImageDraw, ImageFont

CAMBGX = Path(KIT) / "blender" / "debug_proj" / "scroll_test_1" / "ff9field" / "camera.bgx"
cam = C.parse_bgx_cameras(str(CAMBGX))[0]
RW, RH, S = int(cam.range[0]), int(cam.range[1]), 4
BACK_CY, FRONT_CY = 150.0, 446.0
zb = C.solve_z_for_canvasY(cam, BACK_CY); zf = C.solve_z_for_canvasY(cam, FRONT_CY)
def solve_x(tcx, z, lo=-30000., hi=30000.):
    f0 = C.to_canvas((lo, 0, z), cam)[0] - tcx
    for _ in range(80):
        m = .5 * (lo + hi); fm = C.to_canvas((m, 0, z), cam)[0] - tcx
        if abs(fm) < .01: return m
        if (fm > 0) == (f0 > 0): lo, f0 = m, fm
        else: hi = m
    return .5 * (lo + hi)
FX = round(min(abs(solve_x(40., zf)), abs(solve_x(RW - 40., zf))))

# back+mid already measured float 0; now map the FRONT rise. The player spawn is reliable (the 2nd
# injected NPC mis-positions), so put the PLAYER at the very front + one NPC just behind him.
NPC_CY = [402]                            # front-mid (single NPC -> avoids the 2nd-NPC bug)
NPC_X = [650]
PLAYER_CY = 438                           # the very front (player spawn)
npcs = []
for cy, x in zip(NPC_CY, NPC_X):
    z = round(C.solve_z_for_canvasY(cam, float(cy)))
    npcs.append((cy, x, z))
PLAYER_Z = round(C.solve_z_for_canvasY(cam, float(PLAYER_CY)))
print("figures (standing canvasY, world x, world z):")
for cy, x, z in npcs: print(f"   NPC  cy {cy}: ({x}, {z})")
print(f"   PLAYER cy {PLAYER_CY}: (0, {PLAYER_Z})  (spawn; read soles before moving)")

# ---------- paint: floor + ruler + figure labels ----------
img = Image.new("RGBA", (RW * S, RH * S), (0, 0, 0, 0)); dr = ImageDraw.Draw(img, "RGBA")
def cv(x, z): cx, cy = C.to_canvas((x, 0, z), cam); return (cx * S, cy * S)
dr.polygon([cv(-FX, zb), cv(FX, zb), cv(FX, zf), cv(-FX, zf)], fill=(70, 74, 84, 255))
try: fnt = ImageFont.truetype("arialbd.ttf", 13 * S)
except Exception: fnt = ImageFont.load_default()
for cyv in range(((int(BACK_CY) + 15) // 16) * 16, int(FRONT_CY) + 1, 16):
    z = C.solve_z_for_canvasY(cam, float(cyv));  p0 = cv(-FX, z); p1 = cv(FX, z)
    major = (cyv % 32 == 0)
    dr.line([p0, p1], fill=(130, 205, 255, 255) if major else (80, 120, 160, 220), width=(2 * S if major else S))
    if major:
        for tx in (p0[0] + 8 * S, (p0[0] + p1[0]) / 2 - 18 * S, p1[0] - 44 * S):
            dr.text((tx, p0[1] - 9 * S), str(cyv), fill=(210, 240, 255, 255), font=fnt, stroke_width=2 * S, stroke_fill=(0, 0, 0, 255))
# a bright tick + label at each figure's standing point (where its SOLES should be if planted)
for cy, x, z in npcs:
    p = cv(x, z)
    dr.line([(p[0] - 26 * S, p[1]), (p[0] + 26 * S, p[1])], fill=(120, 255, 140, 255), width=3 * S)
    dr.text((p[0] - 16 * S, p[1] + 4 * S), f"#{cy}", fill=(150, 255, 170, 255), font=fnt, stroke_width=2 * S, stroke_fill=(0, 0, 0, 255))
pp = cv(0, PLAYER_Z)                      # the player spawn (middle)
dr.line([(pp[0] - 26 * S, pp[1]), (pp[0] + 26 * S, pp[1])], fill=(255, 230, 120, 255), width=3 * S)
dr.text((pp[0] - 22 * S, pp[1] + 4 * S), f"PLAYER #{PLAYER_CY}", fill=(255, 230, 120, 255), font=fnt, stroke_width=2 * S, stroke_fill=(0, 0, 0, 255))
OUT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "scroll_out", "calib2"))); OUT.mkdir(parents=True, exist_ok=True)
img.save(OUT / "floor.png"); Image.new("RGBA", (RW * S, RH * S), (16, 18, 22, 255)).save(OUT / "surround.png")
shutil.copyfile(CAMBGX, OUT / "camera.bgx")

# ---------- field.toml: 5 zidane NPCs at the exact positions ----------
npc_blocks = "".join(f'[[npc]]\nname = "{cy}"\npreset = "zidane"\npos = [{x}, {z}]\n' for cy, x, z in npcs)
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
spawn = [0, {PLAYER_Z}]
{npc_blocks}"""
(OUT / "calib2.field.toml").write_text(toml, encoding="utf-8", newline="\n")
print(f"\nwrote {OUT}/calib2.field.toml")
print("Each Zidane stands on its labeled green line (#<canvasY>). Read where its SOLES land on the ruler.")
