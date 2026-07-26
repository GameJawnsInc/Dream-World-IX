"""Textured top-down + elevation renders of stock world Object meshes (read-only)."""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/gui-workspace-improvements-277c74/ff9mapkit")
from PIL import Image, ImageDraw
from ff9mapkit.world import extract as X
from ff9mapkit.world import atlas as A

SP = Path(__file__).resolve().parent
atl = A.load_atlas("object", source="bundle").convert("RGBA")
AT = np.asarray(atl).astype(np.float32)
AH, AW = AT.shape[0], AT.shape[1]
print("atlas", atl.size)

def raster(bm, mode, size=220, pad=8):
    """mode 'top' -> (x,z) ; 'front' -> (x,y) ; 'side' -> (z,y)"""
    V = bm.verts; U = bm.uvs
    def proj(v):
        if mode == "top":   return (v[0], -v[2])
        if mode == "front": return (v[0], -v[1])
        return (-v[2], -v[1])
    P = [proj(v) for v in V]
    xs = [p[0] for p in P]; ys = [p[1] for p in P]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    span = max(x1-x0, y1-y0, 1e-3)
    sc = (size - 2*pad) / span
    img = np.zeros((size, size, 4), np.float32)
    zbuf = np.full((size, size), -1e9, np.float32)
    def toPix(p):
        return ((p[0]-x0)*sc + pad, (p[1]-y0)*sc + pad)
    for ti, t in enumerate(bm.tris):
        p = [toPix(P[i]) for i in t]
        uu = [U[i] for i in t] if U else [(0,0)]*3
        depth = -min(V[i][2] for i in t) if mode != "top" else max(V[i][1] for i in t)
        minx = max(int(np.floor(min(q[0] for q in p))), 0); maxx = min(int(np.ceil(max(q[0] for q in p))), size-1)
        miny = max(int(np.floor(min(q[1] for q in p))), 0); maxy = min(int(np.ceil(max(q[1] for q in p))), size-1)
        if maxx < minx or maxy < miny: continue
        (ax,ay),(bx,by),(cx,cy) = p
        den = (bx-ax)*(cy-ay) - (cx-ax)*(by-ay)
        if abs(den) < 1e-9:
            # degenerate in this projection: draw a 1px line-ish fill
            for xx in range(minx, maxx+1):
                for yy in range(miny, maxy+1):
                    if zbuf[yy,xx] < depth:
                        zbuf[yy,xx] = depth
                        u,v = uu[0]
                        px = int(u*(AW-1)) % AW; py = int((1-v)*(AH-1)) % AH
                        img[yy,xx] = AT[py,px]
            continue
        for yy in range(miny, maxy+1):
            for xx in range(minx, maxx+1):
                px_, py_ = xx+0.5, yy+0.5
                w0 = ((bx-px_)*(cy-py_) - (cx-px_)*(by-py_)) / den
                w1 = ((cx-px_)*(ay-py_) - (ax-px_)*(cy-py_)) / den
                w2 = 1 - w0 - w1
                if w0 < -0.002 or w1 < -0.002 or w2 < -0.002: continue
                if zbuf[yy,xx] >= depth: continue
                zbuf[yy,xx] = depth
                u = w0*uu[0][0] + w1*uu[1][0] + w2*uu[2][0]
                v = w0*uu[0][1] + w1*uu[1][1] + w2*uu[2][1]
                ix = int(u*(AW-1)); iy = int((1-v)*(AH-1))
                img[yy,xx] = AT[min(max(iy,0),AH-1), min(max(ix,0),AW-1)]
    out = Image.new("RGBA", (size,size), (24,24,32,255))
    lay = Image.fromarray(img.astype(np.uint8), "RGBA")
    out.alpha_composite(lay)
    d = ImageDraw.Draw(out)
    # wireframe
    for t in bm.tris:
        p = [toPix(P[i]) for i in t]
        d.polygon(p, outline=(255,90,90,170))
    d.text((3,3), f"{mode} {span:.1f}u", fill=(255,255,120,255))
    return out

CAND = [(18,11),(4,4),(5,11),(6,10),(9,1),(16,1),(16,15),(17,15),(13,4),(0,0),
        (7,14),(8,14),(7,13),(8,13),(6,16),(4,3),(18,4),(18,5),(21,14),(3,9),
        (5,15),(14,3),(14,10),(9,17),(5,4),(22,14),(14,14),(17,14),(19,10),(20,11)]
COLS = 6
TILE = 220
sheet = Image.new("RGBA", (COLS*TILE, ((len(CAND)+COLS-1)//COLS)*(TILE+80)), (12,12,16,255))
dd = ImageDraw.Draw(sheet)
for k,(bx,by) in enumerate(CAND):
    bm = X.read_block(bx,by,disc=1,part="object")
    ims = [raster(bm,"top",TILE//1)]
    r,c = divmod(k, COLS)
    ox, oy = c*TILE, r*(TILE+80)
    sheet.alpha_composite(ims[0].resize((TILE,TILE), Image.NEAREST), (ox, oy+70))
    ids = sorted(set(X.block_mapids(bm)))
    dd.text((ox+4, oy+4), f"({bx},{by}) tri={len(bm.tris)}", fill=(255,255,255,255))
    dd.text((ox+4, oy+20), f"idall={ids}", fill=(180,220,255,255))
    tp = sorted({X.decode_id(i)['topograph'] for i in ids})
    dd.text((ox+4, oy+36), f"topo={tp}", fill=(180,255,180,255))
    V=bm.verts
    dd.text((ox+4, oy+52), f"dy={max(v[1] for v in V)-min(v[1] for v in V):.1f}", fill=(255,210,140,255))
sheet.convert("RGB").save(SP/"obj_top_sheet.png")
print("wrote", SP/"obj_top_sheet.png", sheet.size)

# elevation sheet for the same candidates
sheet2 = Image.new("RGBA", (COLS*TILE, ((len(CAND)+COLS-1)//COLS)*(TILE+30)), (12,12,16,255))
d2 = ImageDraw.Draw(sheet2)
for k,(bx,by) in enumerate(CAND):
    bm = X.read_block(bx,by,disc=1,part="object")
    im = raster(bm,"front",TILE)
    r,c = divmod(k, COLS)
    ox, oy = c*TILE, r*(TILE+30)
    sheet2.alpha_composite(im, (ox, oy+22))
    d2.text((ox+4, oy+4), f"({bx},{by}) tri={len(bm.tris)} FRONT(+X right,+Y up)", fill=(255,255,255,255))
sheet2.convert("RGB").save(SP/"obj_front_sheet.png")
print("wrote", SP/"obj_front_sheet.png", sheet2.size)
