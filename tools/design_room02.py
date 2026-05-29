#!/usr/bin/env python3
# Phase 3b: design a NOVEL steeper-top-down room (camera + flat floor walkmesh) and emit:
#   1) the .bgx CAMERA block (synthesized via cam_lib),
#   2) the walkmesh corner coords (for bgi_set_quad4.py),
#   3) a visual PAINT GUIDE png (canvas-res) the human paints over,
#   4) a text summary.
# All offline. Floor depth uses the Session-8-proven vertical canvas map; this room's
# playtest also serves to pin the global scale s on both axes.
import math, os, cam_lib as C
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__)) + "/room02_out"
os.makedirs(OUT, exist_ok=True)

# ---------------- camera: pure pitch about X, steeper than GRGR (49.6 deg) ----------------
PITCH, H, D = 65.0, 497, 4500.0
CANVAS_W, CANVAS_H = 384, 448
th = math.radians(PITCH)
Cpos = (0.0, D*math.sin(th), -D*math.cos(th))     # look at origin from up-and-back
cam = C.Cam(); cam.proj = H; cam.centerOffset = [0, 0]
cam.range = [CANVAS_W, CANVAS_H]; cam.depthOffset = 543; cam.viewport = [160, 224, 112, 336]
cam.r, cam.t = C.synth_r_t(Cpos, C.rot_x(PITCH), H)

# ---------------- floor: world rectangle on y=0, framed to fill the canvas ----------------
CANVASY_BACK, CANVASY_FRONT = 135.0, 425.0        # where floor back/front edges land
FX = 1500                                          # floor half-width in world units
zb = C.solve_z_for_canvasY(cam, CANVASY_BACK)      # back edge (far, +z)
zf = C.solve_z_for_canvasY(cam, CANVASY_FRONT)     # front edge (near, -z)
# walkmesh corners (bgi vert order v0,v1 back; v2,v3 front)
verts = [(-FX,0,zb),(FX,0,zb),(FX,0,zf),(-FX,0,zf)]

def cv(P): return C.to_canvas(P, cam)              # world -> canvas px

print(f"=== steeper top-down (pitch {PITCH} deg, was 49.6) ===")
print(f"camera C={tuple(round(x) for x in Cpos)}  H={H}  FOV_x~{C.decompose(cam)['fov_x_deg']:.1f}deg")
print(f"floor world z: back={zb:.0f} front={zf:.0f}  x=+/-{FX}")
print("corners (world -> canvas):")
for nm,P in zip(["back-L","back-R","front-R","front-L"], verts):
    cx,cy = cv(P); print(f"  {nm:8} {tuple(round(x) for x in P)} -> canvas ({cx:6.1f},{cy:6.1f})  depth {C.depth(P,cam):.0f}")

# ---------------- 1) .bgx camera block ----------------
open(f"{OUT}/camera.bgx.txt","w").write(C.format_bgx_camera(cam))

# ---------------- 2) walkmesh corner command ----------------
flat = " ".join(f"{x} {z}" for (x,_,z) in verts)
open(f"{OUT}/walkmesh_corners.txt","w").write(
    f"# bgi_set_quad4.py <file.bgi> {flat}\n# corners v0..v3 (x z), y=0\n{flat}\n")

# ---------------- 3) paint-guide PNG (4x canvas) ----------------
SCALE = 4
W, Hpx = CANVAS_W*SCALE, CANVAS_H*SCALE
img = Image.new("RGB", (W, Hpx), (28, 28, 34))
dr = ImageDraw.Draw(img, "RGBA")
def P2px(cx, cy): return (cx*SCALE, cy*SCALE)
try: font = ImageFont.truetype("arial.ttf", 22); fontS = ImageFont.truetype("arial.ttf", 16)
except: font = ImageFont.load_default(); fontS = font

# floor polygon
poly = [P2px(*cv(v)) for v in verts]
dr.polygon(poly, fill=(180,120,60,90), outline=(255,170,70,255))
for (x,_,z),nm in zip(verts,["back-L","back-R","front-R","front-L"]):
    px,py = P2px(*cv((x,0,z))); dr.ellipse([px-5,py-5,px+5,py+5], fill=(255,200,90))
    dr.text((px+8,py-8), f"{nm}\n(x={x}, z={z})", fill=(255,220,150), font=fontS)
# depth gridlines (constant z), labelled
for z in range(int(round(zb/200)*200), int(zf)-1, -200):
    a = P2px(*cv((-FX,0,z))); b = P2px(*cv((FX,0,z)))
    dr.line([a,b], fill=(255,255,255,60), width=1)
    dr.text((b[0]+6, b[1]-9), f"z={z}", fill=(200,220,255), font=fontS)
# center vertical (x=0)
ct = P2px(*cv((0,0,zb))); cb = P2px(*cv((0,0,zf)))
dr.line([ct,cb], fill=(120,200,255,120), width=1)
# region labels
dr.text((W*0.30, P2px(0,CANVASY_BACK)[1]-90), "BACK WALL / BACKGROUND  (paint above the floor)",
        fill=(180,200,255), font=font)
dr.text((W*0.32, P2px(0,CANVASY_FRONT)[1]+18), "front lip / under-wall (optional occlusion overlay)",
        fill=(180,200,255), font=font)
dr.text((10,10), f"PAINT GUIDE — steeper top-down (pitch {int(PITCH)}deg)\n"
        f"canvas {CANVAS_W}x{CANVAS_H} (this png is {SCALE}x).  Paint the FLOOR inside the orange quad;\n"
        f"the walkmesh sits exactly there. Floor recedes with depth (z labels).",
        fill=(230,230,240), font=fontS)
img.save(f"{OUT}/paint_guide.png")

# ---------------- 4) summary ----------------
open(f"{OUT}/SUMMARY.txt","w").write(
f"""STEEPER TOP-DOWN ROOM (room02) — design output
camera: pure pitch {PITCH} deg about X (GRGR was 49.6), H={H}, C={tuple(round(x) for x in Cpos)}
canvas: {CANVAS_W}x{CANVAS_H} logical (paint at 4x = {W}x{Hpx})
floor world rect: x in [-{FX},{FX}], z in [{zf:.0f}(front), {zb:.0f}(back)]
walkmesh corners (x z): {flat}

NEXT:
 - paint_guide.png shows where the floor lands. Paint a top-down floor filling the orange quad,
   and a back wall / background above it (and optionally a thin front lip for occlusion).
 - then I wire camera.bgx + the walkmesh + your art into a new field and we test in-game
   (this playtest also pins the global canvas scale s on both axes).
""")
print(f"\nwrote: {OUT}/  (camera.bgx.txt, walkmesh_corners.txt, paint_guide.png, SUMMARY.txt)")
