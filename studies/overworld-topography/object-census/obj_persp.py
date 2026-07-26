"""3/4 perspective renders of shortlisted stock Object meshes (game-like view angle)."""
import sys, math
from pathlib import Path
import numpy as np
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/gui-workspace-improvements-277c74/ff9mapkit")
from PIL import Image, ImageDraw
from ff9mapkit.world import extract as X
from ff9mapkit.world import atlas as A
SP = Path(__file__).resolve().parent
OA = np.asarray(A.load_atlas("object", source="bundle").convert("RGBA")).astype(np.float32)
AH, AW = OA.shape[0], OA.shape[1]

PLACES = {0:"Dummy",2:"Alexandria",6:"Treno",7:"SouthGate_NorthBottom",9:"SouthGate_NorthWest",
 10:"SouthGate_SouthTop",14:"Dali",15:"NorthGate_East",22:"QuMarsh_Mist",24:"LindblumDragonGate",
 27:"EarthShrine",28:"DesertPalace_Cave",32:"FossilRoo",34:"MadainSari",41:"QuMarsh_Archipelago",
 44:"WaterShrine",45:"IpsenCastle",48:"EstoGaza",49:"FireShrine",54:"Memoria",
 56:"ChocoboAirGarden_Peninsula",57:"ChocoboAirGarden_Canyon",60:"GizamalukeGrotto_Top",63:"Bridge"}

def persp(bm, size=340, yaw=35.0, pitch=28.0):
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    V = bm.verts; U = bm.uvs
    cx = (min(v[0] for v in V)+max(v[0] for v in V))/2
    cz = (min(v[2] for v in V)+max(v[2] for v in V))/2
    cyy = (min(v[1] for v in V)+max(v[1] for v in V))/2
    def cam(v):
        x, y, z = v[0]-cx, v[1]-cyy, v[2]-cz
        xr = x*cy + z*sy
        zr = -x*sy + z*cy
        yr = y*cp - zr*sp
        zd = y*sp + zr*cp
        return (xr, -yr, zd)
    P = [cam(v) for v in V]
    xs=[p[0] for p in P]; ys=[p[1] for p in P]
    span = max(max(xs)-min(xs), max(ys)-min(ys), 1e-3)
    sc = (size-20)/span
    x0, y0 = min(xs), min(ys)
    img=np.zeros((size,size,4),np.float32); zb=np.full((size,size),1e9,np.float32)
    for t in bm.tris:
        p=[((P[i][0]-x0)*sc+10,(P[i][1]-y0)*sc+10) for i in t]
        d=min(P[i][2] for i in t)
        uu=[U[i] for i in t] if U else [(0.,0.)]*3
        minx=max(int(min(q[0] for q in p)),0); maxx=min(int(max(q[0] for q in p))+1,size-1)
        miny=max(int(min(q[1] for q in p)),0); maxy=min(int(max(q[1] for q in p))+1,size-1)
        (ax,ay),(bx,by),(ccx,ccy)=p
        den=(bx-ax)*(ccy-ay)-(ccx-ax)*(by-ay)
        if abs(den)<1e-9: continue
        for yy in range(miny,maxy+1):
            for xx in range(minx,maxx+1):
                px_,py_=xx+.5,yy+.5
                w0=((bx-px_)*(ccy-py_)-(ccx-px_)*(by-py_))/den
                w1=((ccx-px_)*(ay-py_)-(ax-px_)*(ccy-py_))/den
                w2=1-w0-w1
                if w0<-.002 or w1<-.002 or w2<-.002: continue
                if zb[yy,xx]<=d: continue
                zb[yy,xx]=d
                u=w0*uu[0][0]+w1*uu[1][0]+w2*uu[2][0]
                v=w0*uu[0][1]+w1*uu[1][1]+w2*uu[2][1]
                ix=min(max(int(u*(AW-1)),0),AW-1); iy=min(max(int((1-v)*(AH-1)),0),AH-1)
                img[yy,xx]=OA[iy,ix]
    out=Image.new("RGBA",(size,size),(20,22,30,255)); out.alpha_composite(Image.fromarray(img.astype(np.uint8),"RGBA"))
    return out

CAND=[(9,17),(21,10),(22,14),(14,14),(21,14),(6,12),(2,7),(5,16),(6,16),(14,3),(18,4),(13,4),
      (7,14),(8,14),(19,10),(20,10),(17,12),(13,17),(11,4),(14,15),(16,15),(3,9)]
S=340; COLS=5
sheet=Image.new("RGBA",(COLS*S,((len(CAND)+COLS-1)//COLS)*(S+34)),(8,8,12,255))
dd=ImageDraw.Draw(sheet)
for k,(bx,by) in enumerate(CAND):
    bm=X.read_block(bx,by,disc=1,part="object")
    r,c=divmod(k,COLS); ox,oy=c*S,r*(S+34)
    sheet.alpha_composite(persp(bm,S),(ox,oy+32))
    ids=sorted(set(X.block_mapids(bm)))
    ars=sorted({X.decode_id(i)['area'] for i in ids})
    V=bm.verts
    dd.text((ox+4,oy+3), f"({bx},{by}) tri={len(bm.tris)}  {'/'.join(PLACES.get(a,str(a)) for a in ars)}", fill=(255,255,255,255))
    dd.text((ox+4,oy+18), f"{max(v[0] for v in V)-min(v[0] for v in V):.1f} x {max(v[2] for v in V)-min(v[2] for v in V):.1f} x {max(v[1] for v in V)-min(v[1] for v in V):.1f}u  topo={sorted({X.decode_id(i)['topograph'] for i in ids})}", fill=(160,220,255,255))
sheet.convert("RGB").save(SP/"obj_persp.png")
print("wrote", SP/"obj_persp.png", sheet.size)
from PIL import Image as I
im=I.open(SP/"obj_persp.png")
h=(S+34)*3
for i in range(2):
    im.crop((0,i*h,im.width,min((i+1)*h,im.height))).save(SP/f"persp_{i}.png")
print("split ok", im.size)
