#!/usr/bin/env python3
# Vivi's hut: shared 48-deg camera + floor walkmesh, and TWO annotated paint guides
# (exterior "Vivi's Return" / interior "Vivi's House"). Same geometry for both rooms; the
# human paints two backgrounds to the same floor. Floor is framed low so the upper ~40% of
# the canvas is free for the hut / walls. Uses the validated calibrated canvas map.
import math, os, cam_lib as C
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__)) + "/hut_out"
os.makedirs(OUT, exist_ok=True)
CW, CH = 384, 448

# ---- shared camera: 48 deg (steepest real FF9 angle, = GRGR), validated ----
PITCH, H, D = 48.0, 497, 4500.0
th = math.radians(PITCH)
Cpos = (0.0, D*math.sin(th), -D*math.cos(th))
cam = C.Cam(); cam.proj = H; cam.centerOffset = [0, 0]; cam.range = [CW, CH]
cam.depthOffset = 543; cam.viewport = [160, 224, 112, 336]
cam.r, cam.t = C.synth_r_t(Cpos, C.rot_x(PITCH), H)

# ---- floor: framed low (back canvasY 205, front 432); FX so the wide front fits on canvas ----
zb = round(C.solve_z_for_canvasY(cam, 205.0))
zf = round(C.solve_z_for_canvasY(cam, 432.0))
nf = abs(C.project((0,0,zf), cam)[2])               # depth at front center
FX = int(round(165 * nf / (C.S_CANVAS_X * H)))      # front half-width ~165 canvas px
verts = [(-FX,0,zb),(FX,0,zb),(FX,0,zf),(-FX,0,zf)]
def cv(P): return C.to_canvas(P, cam)

print(f"=== Vivi's hut shared geometry: 48 deg, H={H} ===")
print(f"floor x+/-{FX}, z [{zf}..{zb}]   corners(canvas):")
for nm,P in zip(["back-L","back-R","front-R","front-L"], verts):
    print(f"  {nm:8} {tuple(round(x) for x in P)} -> {tuple(round(v,1) for v in cv(P))}")

# door (exterior entrance) at back-center; exit (interior) at front-center; Vivi mid-floor
door_world  = (0, 0, zb)                  # back-center of floor (player walks up to hut door)
exit_world  = (0, 0, zf)                  # front-center (walk down/out to leave)
vivi_world  = (0, 0, round(zb*0.45 + zf*0.55))   # standing a bit toward the front

# ---- .bgx camera + walkmesh corners (shared) ----
open(f"{OUT}/hut_camera.bgx.txt","w",newline="\n").write(C.format_bgx_camera(cam))
flat = " ".join(f"{x} {z}" for (x,_,z) in verts)
open(f"{OUT}/hut_walkmesh_corners.txt","w",newline="\n").write(flat+"\n")

# ---- paint guide renderer ----
S = 4
try: F1=ImageFont.truetype("arialbd.ttf",26); F2=ImageFont.truetype("arial.ttf",18)
except: F1=ImageFont.load_default(); F2=F1
def px(P): cx,cy=cv(P); return (cx*S, cy*S)

def make_guide(fname, title, region_label, marks):
    img = Image.new("RGB", (CW*S, CH*S), (32,30,38)); dr = ImageDraw.Draw(img,"RGBA")
    # floor quad
    poly=[px(v) for v in verts]
    dr.polygon(poly, fill=(170,120,70,80), outline=(255,170,70,255))
    dr.line([poly[0],poly[1]], fill=(255,170,70,255), width=3)
    # depth gridlines
    for j in range(1,6):
        z=zb+(zf-zb)*j/6; a=px((-FX,0,z)); b=px((FX,0,z))
        dr.line([a,b], fill=(255,255,255,45), width=1)
    # center line
    dr.line([px((0,0,zb)),px((0,0,zf))], fill=(120,200,255,90), width=1)
    # background region label (upper area, above floor)
    by=px((0,0,zb))[1]
    dr.rectangle([0,0,CW*S,by], outline=(120,160,220,120))
    dr.text((CW*S*0.10, by*0.42), region_label, fill=(170,200,255), font=F1)
    # marks (door / exit / vivi)
    for (P,col,lab) in marks:
        x,y=px(P); r=14
        dr.ellipse([x-r,y-r,x+r,y+r], outline=col, width=3)
        dr.line([x-22,y,x+22,y],fill=col,width=2); dr.line([x,y-22,x,y+22],fill=col,width=2)
        dr.text((x+18,y-12), lab, fill=col, font=F2)
    # floor corner coords
    for (x,_,z),nm in zip(verts,["BL","BR","FR","FL"]):
        p=px((x,0,z)); dr.text((p[0]+4,p[1]+4), f"{nm}(x={x},z={z})", fill=(255,225,170), font=F2)
    dr.text((12,CH*S-90), f"{title}\ncanvas {CW}x{CH} (png is {S}x). Paint the FLOOR inside the orange quad\n"
            f"(walkmesh sits exactly there). Floor recedes with depth (faint lines).",
            fill=(235,235,245), font=F2)
    img.save(f"{OUT}/{fname}")
    print(f"wrote {OUT}/{fname}")

make_guide("guide_exterior.png", "VIVI'S RETURN (outside the hut) - 48deg",
    "THE HUT  (paint the building up here, with a door at the orange DOOR mark)",
    [(door_world,(120,255,140),"DOOR -> enter (gateway is the back-center floor strip)")])
make_guide("guide_interior.png", "VIVI'S HOUSE (inside the hut) - 48deg",
    "BACK WALL / interior walls  (paint the room's back + side walls up here)",
    [(exit_world,(255,200,90),"EXIT -> leave (front-center floor strip)"),
     (vivi_world,(150,210,255),"VIVI stands here")])
print(f"\nVivi world pos: {vivi_world}  | door(enter): {door_world} | exit: {exit_world}")
