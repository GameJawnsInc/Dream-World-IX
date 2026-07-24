import sys, math, io, contextlib
sys.path.insert(0,'../../ff9mapkit'); sys.path.insert(0,'.')
from ff9mapkit.world import extract as X
LAND_Y=0.6
land=set()
for by in range(20):
    for bx in range(24):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                bm=X.read_block(bx,by,disc=1,part='terrain')
        except Exception: continue
        if any(bm.verts[i][1]>LAND_Y for t in bm.tris for i in t[:3]): land.add((bx,by))
deployed=[(6,18),(6,19),(7,18),(7,19),(8,19),(9,9),(10,8),(10,9),(10,10),(11,8),(11,9),(11,18),(11,19),(12,18),(12,19),(18,17),(18,18),(18,19),(19,17),(19,18),(19,19),(20,17),(20,18),(20,19)]
occ=land|set(deployed)
def clear(cx,cz,r):
    # min dist center->occupied block rect (x-wrap) and to z-edges
    def axd(px,a,b):
        if a<=px<=b: return 0
        return min(min((px-a)%1536,(a-px)%1536),min((px-b)%1536,(b-px)%1536))
    mind=1e9; who=None
    for (bx,by) in occ:
        x0=64*bx;x1=x0+64;z1=-64*by;z0=z1-64
        dx=axd(cx,x0,x1); dz=0 if z0<=cz<=z1 else min(abs(cz-z0),abs(cz-z1))
        d=math.hypot(dx,dz)
        if d<mind: mind=d;who=(bx,by)
    zedge=min(-cz, cz+1280)  # north(0) / south(-1280)
    return mind,who,zedge
for cx,cz,r in [(120,-160,132),(110,-180,132),(128,-176,130),(120,-160,150),(100,-192,128)]:
    m,who,ze=clear(cx,cz,r)
    verdict='OK' if (m>=r and ze>=r) else 'TIGHT/FAIL'
    print(f'center({cx},{cz}) r{r}: land_clear={m:.0f}u(nearest {who}) zedge_clear={ze:.0f}u  -> {verdict} (need >= r={r}; wrap west={cx-r:.0f})')

print('--- NW-bay scan for max clean radius (center x -80..300 wrap, z -120..-420) ---')
best=[]
for gz in range(120,440,8):
    cz=-gz
    for gx in range(-120,320,8):
        cx=gx%1536
        bcx=int(cx//64)%24; bcz=int(gz//64)
        if (bcx,bcz) in occ: continue
        m,who,ze=clear(cx,cz,999)
        r=min(m,ze)
        best.append((r,cx,cz,who))
best.sort(reverse=True)
seen=[]
for r,cx,cz,who in best:
    if any(math.hypot(((cx-sx+768)%1536)-768,cz-sz)<70 for sx,sz in seen): continue
    seen.append((cx,cz)); print(f'  Rmax={r:.0f}u center({cx},{cz}) block({cx//64},{-cz//64}) nearest_land{who} westEdge={cx-r if cx-r>-1536 else cx-r:.0f}')
    if len(seen)>=6: break
