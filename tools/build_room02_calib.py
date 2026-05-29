#!/usr/bin/env python3
# Build the in-game CALIBRATION assets for the steeper-top-down room (field 4000 reused
# via DictionaryPatch mapid swap -> FBG_N11_ROOM02_TD). Generates:
#   - grid.png  : perspective-correct checkerboard floor + edges + markers (full canvas)
#   - FBG_N11_ROOM02_TD.bgx : steeper camera + the grid overlay
# (.bgi walkmesh is built separately from room01's via bgi_set_quad4 + bgi_fix_neighbors.)
import math, os, cam_lib as C
from PIL import Image, ImageDraw, ImageFont

NAME = "FBG_N11_ROOM02_TD"
OUT = os.path.dirname(os.path.abspath(__file__)) + "/room02_out/deploy"
os.makedirs(OUT, exist_ok=True)

PITCH, H, D = 65.0, 497, 4500.0
CW, CH = 384, 448
th = math.radians(PITCH)
Cpos = (0.0, D*math.sin(th), -D*math.cos(th))
cam = C.Cam(); cam.proj = H; cam.centerOffset = [0, 0]; cam.range = [CW, CH]
cam.depthOffset = 543; cam.viewport = [160, 224, 112, 336]
cam.r, cam.t = C.synth_r_t(Cpos, C.rot_x(PITCH), H)

FX = 1500
zb = round(C.solve_z_for_canvasY(cam, 135.0))
zf = round(C.solve_z_for_canvasY(cam, 425.0))
print(f"floor: x +/-{FX}, z [{zf}..{zb}]  corners(canvas):")
for nm,(x,z) in [("BL",(-FX,zb)),("BR",(FX,zb)),("FR",(FX,zf)),("FL",(-FX,zf))]:
    print(f"  {nm} {C.to_canvas((x,0,z),cam)}")

# ---- grid.png : 4x canvas, perspective checkerboard floor ----
S = 4
img = Image.new("RGB", (CW*S, CH*S), (20, 22, 28))
dr = ImageDraw.Draw(img, "RGBA")
def px(P):
    cx, cy = C.to_canvas(P, cam); return (cx*S, cy*S)
NX, NZ = 6, 6
xs = [-FX + 2*FX*i/NX for i in range(NX+1)]
zs = [zb + (zf-zb)*j/NZ for j in range(NZ+1)]
for j in range(NZ):
    for i in range(NX):
        quad = [px((xs[i],0,zs[j])), px((xs[i+1],0,zs[j])),
                px((xs[i+1],0,zs[j+1])), px((xs[i],0,zs[j+1]))]
        light = (i + j) % 2 == 0
        col = (90,110,140,200) if light else (50,60,80,200)
        dr.polygon(quad, fill=col)
# bright floor outline
edge = [px((-FX,0,zb)), px((FX,0,zb)), px((FX,0,zf)), px((-FX,0,zf))]
dr.polygon(edge, outline=(255,180,70,255))
dr.line([edge[0],edge[1]], fill=(255,180,70,255), width=3)  # back edge bold
# markers at known world points
try: fnt = ImageFont.truetype("arial.ttf", 30)
except: fnt = ImageFont.load_default()
def mark(P, col, label):
    x,y = px(P); r=9
    dr.ellipse([x-r,y-r,x+r,y+r], fill=col)
    dr.line([x-18,y,x+18,y], fill=col, width=2); dr.line([x,y-18,x,y+18], fill=col, width=2)
    dr.text((x+14,y-34), label, fill=col, font=fnt)
mark((0,0,0),   (90,255,120), "(0,0,0)")
mark((0,0,zb),  (255,120,120), f"back z={zb}")
mark((0,0,zf),  (255,120,120), f"front z={zf}")
mark((1000,0,0),(120,200,255), "(1000,0,0)")
mark((-1000,0,0),(120,200,255), "(-1000,0,0)")
img.save(f"{OUT}/grid.png")
print(f"wrote {OUT}/grid.png  ({img.size[0]}x{img.size[1]})")

# ---- .bgx : steeper camera + one full-canvas grid overlay (behind the player) ----
bgx  = "# ROOM02_TD calibration: steeper top-down (pitch 65) + checkerboard floor grid\n"
bgx += "OVERLAY\nCameraId: 0\nViewportId: 0\nPosition: 0, 0, 4000\n"
bgx += f"Size: {CW}, {CH}\nImage: grid.png\nShader: PSX/FieldMap_Abr_None\n\n"
bgx += C.format_bgx_camera(cam)
open(f"{OUT}/{NAME}.bgx","w",newline="\n").write(bgx)
print(f"wrote {OUT}/{NAME}.bgx")
print("\nwalkmesh corners for bgi_set_quad4 (x z):")
print(f"  {-FX} {zb} {FX} {zb} {FX} {zf} {-FX} {zf}")
