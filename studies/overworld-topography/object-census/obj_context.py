"""Per-candidate context render: block terrain+water top-down with the Object mesh highlighted, plus 3 object views."""
import sys, math
from pathlib import Path
import numpy as np
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/gui-workspace-improvements-277c74/ff9mapkit")
from PIL import Image, ImageDraw
from ff9mapkit.world import extract as X
from ff9mapkit.world import atlas as A

SP = Path(__file__).resolve().parent
TA = np.asarray(A.load_atlas("terrain", source="bundle").convert("RGBA")).astype(np.float32)
OA = np.asarray(A.load_atlas("object",  source="bundle").convert("RGBA")).astype(np.float32)

def rast(img, zb, tris, V, U, AT, proj, box, size, tint=1.0):
    AH, AW = AT.shape[0], AT.shape[1]
    x0, y0, sc, pad = box
    for t in tris:
        p = []
        for i in t:
            q = proj(V[i]); p.append(((q[0]-x0)*sc+pad, (q[1]-y0)*sc+pad))
        depth = max(V[i][1] for i in t)
        uu = [U[i] for i in t] if U else [(0.,0.)]*3
        minx = max(int(min(q[0] for q in p)), 0); maxx = min(int(max(q[0] for q in p))+1, size-1)
        miny = max(int(min(q[1] for q in p)), 0); maxy = min(int(max(q[1] for q in p))+1, size-1)
        (ax,ay),(bx,by),(cx,cy) = p
        den = (bx-ax)*(cy-ay)-(cx-ax)*(by-ay)
        if abs(den) < 1e-9: continue
        for yy in range(miny, maxy+1):
            for xx in range(minx, maxx+1):
                px_, py_ = xx+.5, yy+.5
                w0 = ((bx-px_)*(cy-py_)-(cx-px_)*(by-py_))/den
                w1 = ((cx-px_)*(ay-py_)-(ax-px_)*(cy-py_))/den
                w2 = 1-w0-w1
                if w0<-.002 or w1<-.002 or w2<-.002: continue
                if zb[yy,xx] >= depth: continue
                zb[yy,xx] = depth
                u = w0*uu[0][0]+w1*uu[1][0]+w2*uu[2][0]
                v = w0*uu[0][1]+w1*uu[1][1]+w2*uu[2][1]
                ix = min(max(int(u*(AW-1)),0),AW-1); iy = min(max(int((1-v)*(AH-1)),0),AH-1)
                img[yy,xx] = AT[iy,ix]*tint

WPARTS = ["sea1","sea2","sea3","sea4","sea5","sea6","beach1","beach2","river","stream","falls","riverjoint"]

def block_panel(bx, by, size=300):
    img = np.zeros((size,size,4), np.float32); zb = np.full((size,size), -1e9, np.float32)
    box = (0.0, -64.0, (size-8)/64.0, 4)      # local x[0,64], -z in [0,64] -> y0=-64
    proj = lambda v: (v[0], -v[2]-64.0+64.0) if False else (v[0], -v[2])
    box = (0.0, 0.0, (size-8)/64.0, 4)
    tb = X.read_block(bx,by,disc=1,part="terrain")
    rast(img, zb, tb.tris, tb.verts, tb.uvs, TA, proj, box, size, 0.75)
    for p in WPARTS:
        try: wm = X.read_block(bx,by,disc=1,part=p)
        except Exception: continue
        rast(img, zb, wm.tris, wm.verts, wm.uvs, TA, proj, box, size, 0.9)
    out = Image.new("RGBA",(size,size),(10,12,20,255)); out.alpha_composite(Image.fromarray(img.astype(np.uint8),"RGBA"))
    d = ImageDraw.Draw(out)
    ob = X.read_block(bx,by,disc=1,part="object")
    for t in ob.tris:
        p=[]
        for i in t:
            q = proj(ob.verts[i]); p.append(((q[0]-box[0])*box[2]+box[3], (q[1]-box[1])*box[2]+box[3]))
        d.polygon(p, outline=(255,40,40,255), fill=(255,120,0,110))
    d.text((4,4), f"Block[{bx}][{by}] TOP  local x->right, -z->down (64u)", fill=(255,255,140,255))
    d.text((4,size-14), "orange = Object mesh", fill=(255,160,60,255))
    return out

def obj_views(bx, by, size=300):
    ob = X.read_block(bx,by,disc=1,part="object")
    outs=[]
    for mode in ("top","front","side"):
        proj = {"top": lambda v:(v[0],-v[2]), "front": lambda v:(v[0],-v[1]), "side": lambda v:(-v[2],-v[1])}[mode]
        P=[proj(v) for v in ob.verts]
        x0=min(p[0] for p in P); x1=max(p[0] for p in P); y0=min(p[1] for p in P); y1=max(p[1] for p in P)
        span=max(x1-x0,y1-y0,1e-3); sc=(size-16)/span
        img=np.zeros((size,size,4),np.float32); zb=np.full((size,size),-1e9,np.float32)
        rast(img, zb, ob.tris, ob.verts, ob.uvs, OA, proj, (x0,y0,sc,8), size)
        o=Image.new("RGBA",(size,size),(18,18,24,255)); o.alpha_composite(Image.fromarray(img.astype(np.uint8),"RGBA"))
        d=ImageDraw.Draw(o)
        for t in ob.tris:
            p=[((proj(ob.verts[i])[0]-x0)*sc+8,(proj(ob.verts[i])[1]-y0)*sc+8) for i in t]
            d.polygon(p, outline=(255,80,80,110))
        d.text((4,4), f"{mode} {span:.1f}u", fill=(255,255,140,255))
        outs.append(o)
    return outs

CAND = [(9,17),(21,10),(22,14),(14,14),(3,9),(0,0),(13,4),(16,1),(18,4),(21,14),(16,15),(13,17)]
S=300
sheet = Image.new("RGBA",(4*S, len(CAND)*(S+22)),(8,8,12,255))
dd=ImageDraw.Draw(sheet)
for k,(bx,by) in enumerate(CAND):
    oy=k*(S+22)
    sheet.alpha_composite(block_panel(bx,by,S),(0,oy+20))
    for j,im in enumerate(obj_views(bx,by,S)):
        sheet.alpha_composite(im,((j+1)*S,oy+20))
    ob = X.read_block(bx,by,disc=1,part="object")
    ids=sorted(set(X.block_mapids(ob)))
    dd.text((4,oy+4), f"({bx},{by})  tri={len(ob.tris)}  idall={ids}  areas={sorted({X.decode_id(i)['area'] for i in ids})}  topos={sorted({X.decode_id(i)['topograph'] for i in ids})}  events={sorted({X.decode_id(i)['event'] for i in ids})}", fill=(255,255,255,255))
sheet.convert("RGB").save(SP/"obj_context_sheet.png")
print("wrote", SP/"obj_context_sheet.png", sheet.size)
