import sys, math
sys.path.insert(0,'../../ff9mapkit'); sys.path.insert(0,'.')
from ff9mapkit.world import extract as X
from pathlib import Path
from ff9mapkit.world import mesh as M
# stock land verts, rows 0-12 (cover bay + north archipelago fringe)
land=[]
for by in range(0,13):
    for bx in range(0,24):
        try: bm=X.read_block(bx,by,disc=1,part='terrain')
        except Exception: continue
        ox,oz=X.block_world_origin(bx,by)
        for v in bm.verts:
            if v[1]>0.6: land.append((v[0]+ox,v[2]+oz))
# deployed land (live game folder), rows 0-12
LIVE=Path("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap-world")
import glob,re
dep=0
for f in glob.glob(str(LIVE/"**"/"*Terrain.ff9mesh"),recursive=True):
    mm=re.search(r"Block\[(\d+)\]\[(\d+)\]",f)
    if not mm: continue
    bx,by=int(mm.group(1)),int(mm.group(2))
    if by>12: continue
    try: bm=M.blockmesh_from_ff9mesh(f,disc=1,x=bx,y=by,part="terrain")
    except Exception: continue
    ox,oz=X.block_world_origin(bx,by)
    for v in bm.verts:
        if v[1]>0.6: land.append((v[0]+ox,v[2]+oz)); dep+=1
print("stock+deployed land verts rows0-12:",len(land),"(deployed",dep,")")
def wrapdx(a,b):
    d=a-b
    while d>768:d-=1536
    while d<-768:d+=1536
    return d
def clr(cx,cz):
    b=1e9
    for lx,lz in land:
        d=math.hypot(wrapdx(cx,lx),cz-lz)
        if d<b:b=d
    return b
mecx,mecz=935.8,-767.3
print("\nFULL whole-block-shift lattice (off-seam needs westEdge>=0 for R=132):")
best_off=None
for k in range(10,15):
    for j in range(6,13):
        cx=mecx-64*k; cz=mecz+64*j
        if not(-1279<cz<0): continue
        r=clr(cx,cz); ne=abs(cz); rmax=min(r,ne); we=cx-132
        seam="OFF" if we>=0 else "WRAP"
        tag=""
        if we>=0 and rmax>=132: tag="  <-- OFF-SEAM R132 FIT"
        if we>=0 and (best_off is None or rmax>best_off[2]): best_off=(cx,cz,rmax)
        if rmax>=100:
            print(f"  ({cx:6.1f},{cz:7.1f}) clr={r:6.1f} north={ne:4.0f} Rmax={rmax:6.1f} we={we:6.1f} {seam}{tag}")
print("\nbest OFF-SEAM lattice Rmax:",best_off,"(need >=132; +fill-overshoot margin)")
