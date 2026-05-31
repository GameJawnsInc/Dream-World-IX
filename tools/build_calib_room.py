#!/usr/bin/env python3
# Generic calibration-room builder: author a pure-pitch camera at ANY angle/FOV, frame a flat
# floor with the CALIBRATED canvas map (sx/sy from cam_lib, NO re-tuning), and emit grid.png +
# .bgx. Used to validate that the canvas scales are GLOBAL (same on a different camera).
# Usage: build_calib_room.py <NAME> <pitch_deg> <H> <D> [FX]
import math, os, sys, cam_lib as C
from PIL import Image, ImageDraw, ImageFont

NAME  = sys.argv[1] if len(sys.argv) > 1 else "FBG_N11_ROOM03_TD"
PITCH = float(sys.argv[2]) if len(sys.argv) > 2 else 75.0
H     = int(sys.argv[3]) if len(sys.argv) > 3 else 650
D     = float(sys.argv[4]) if len(sys.argv) > 4 else 5000.0
CW, CH = 384, 448
OUT = os.path.dirname(os.path.abspath(__file__)) + "/room03_out/deploy"
os.makedirs(OUT, exist_ok=True)

th = math.radians(PITCH)
Cpos = (0.0, D*math.sin(th), -D*math.cos(th))
cam = C.Cam(); cam.proj = H; cam.centerOffset = [0, 0]; cam.range = [CW, CH]
cam.depthOffset = 543; cam.viewport = [160, 224, 112, 336]
cam.r, cam.t = C.synth_r_t(Cpos, C.rot_x(PITCH), H)

# frame floor: canvasY 130(back)..420(front) via the CALIBRATED map
zb = round(C.solve_z_for_canvasY(cam, 130.0))
zf = round(C.solve_z_for_canvasY(cam, 420.0))
# auto half-width so back edge spans ~130px from center
nb = abs(C.project((0,0,zb), cam)[2])              # depth at back center
FX = int(sys.argv[5]) if len(sys.argv) > 5 else int(round(130*nb/(C.S_CANVAS_X*H)))

print(f"=== {NAME}: pitch {PITCH} (room01=49.6, room02=65), H={H}, FOV_x~{C.decompose(cam)['fov_x_deg']:.1f} ===")
print(f"camera C={tuple(round(x) for x in Cpos)}  floor x+/-{FX}, z [{zf}..{zb}]")
def cv(P): return C.to_canvas(P, cam)
for nm,(x,z) in [("BL",(-FX,zb)),("BR",(FX,zb)),("FR",(FX,zf)),("FL",(-FX,zf))]:
    print(f"  {nm} {(x,0,z)} -> canvas {tuple(round(v,1) for v in cv((x,0,z)))}  depth {C.depth((x,0,z),cam):.0f}")

# ---- grid.png ----
S = 4; img = Image.new("RGB", (CW*S, CH*S), (20,22,28)); dr = ImageDraw.Draw(img, "RGBA")
def px(P): cx,cy = cv(P); return (cx*S, cy*S)
NX, NZ = 6, 6
xs = [-FX + 2*FX*i/NX for i in range(NX+1)]; zs = [zb + (zf-zb)*j/NZ for j in range(NZ+1)]
for j in range(NZ):
    for i in range(NX):
        q = [px((xs[i],0,zs[j])),px((xs[i+1],0,zs[j])),px((xs[i+1],0,zs[j+1])),px((xs[i],0,zs[j+1]))]
        dr.polygon(q, fill=((90,110,140,200) if (i+j)%2==0 else (50,60,80,200)))
edge = [px((-FX,0,zb)),px((FX,0,zb)),px((FX,0,zf)),px((-FX,0,zf))]
dr.polygon(edge, outline=(255,180,70,255)); dr.line([edge[0],edge[1]], fill=(255,180,70,255), width=3)
try: fnt = ImageFont.truetype("arial.ttf", 30)
except: fnt = ImageFont.load_default()
def mark(P,col,lab):
    x,y=px(P); r=9; dr.ellipse([x-r,y-r,x+r,y+r],fill=col)
    dr.line([x-18,y,x+18,y],fill=col,width=2); dr.line([x,y-18,x,y+18],fill=col,width=2)
    dr.text((x+14,y-34),lab,fill=col,font=fnt)
mark((0,0,0),(90,255,120),"(0,0,0)"); mark((1000,0,0),(120,200,255),"(1000,0,0)")
mark((-1000,0,0),(120,200,255),"(-1000,0,0)")
mark((0,0,zb),(255,120,120),f"back z={zb}"); mark((0,0,zf),(255,120,120),f"front z={zf}")
img.save(f"{OUT}/grid.png")

# ---- .bgx ----
bgx = f"# {NAME} calibration: pitch {PITCH} top-down + checkerboard grid (GLOBAL sx/sy test)\n"
bgx += f"OVERLAY\nCameraId: 0\nViewportId: 0\nPosition: 0, 0, 4000\nSize: {CW}, {CH}\nImage: grid.png\nShader: PSX/FieldMap_Abr_None\n\n"
bgx += C.format_bgx_camera(cam)
open(f"{OUT}/{NAME}.bgx","w",newline="\n").write(bgx)
print(f"\nwrote {OUT}/grid.png + {NAME}.bgx")
print(f"walkmesh corners (x z): {-FX} {zb} {FX} {zb} {FX} {zf} {-FX} {zf}")
