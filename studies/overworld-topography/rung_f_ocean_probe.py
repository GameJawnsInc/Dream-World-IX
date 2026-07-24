import sys, io, contextlib, math
sys.path.insert(0,'../../ff9mapkit'); sys.path.insert(0,'.')
from ff9mapkit.world import extract as X
# gather stock LAND verts (terrain, y>0.6) over the northern band rows 0-8, all cols
land=[]
for by in range(0,9):
    for bx in range(0,24):
        try: bm=X.read_block(bx,by,disc=1,part='terrain')
        except Exception: continue
        ox,oz=X.block_world_origin(bx,by)
        for v in bm.verts:
            if v[1]>0.6:
                land.append((v[0]+ox, v[2]+oz))
print("northern land verts (rows0-8):",len(land))
def wrapdx(ax,bx):
    d=ax-bx
    while d>768: d-=1536
    while d<-768: d+=1536
    return d
def clearance(cx,cz):
    best=1e9
    for (lx,lz) in land:
        dx=wrapdx(cx,lx); dz=cz-lz
        d=math.hypot(dx,dz)
        if d<best: best=d
    return best
# candidate centers from the design
for (cx,cz,lbl) in [(110,-192,"configB (110,-192)"),(100,-192,"configB (100,-192)"),
                    (120,-200,"configB (120,-200)"),(64,-232,"headroom (64,-232)"),
                    (-8,-248,"configA seam (-8,-248)"),(103.8,-191.3,"MEC shift (-13,+9)"),
                    (103.8,-255.3,"MEC shift (-13,+8)")]:
    z0=cz  # north edge is z=0
    north_edge=abs(0-cz)  # distance to z=0 top
    r=clearance(cx,cz)
    print(f"  {lbl:28} land_clearance={r:6.1f}u  north_z_edge={north_edge:5.0f}u  Rmax(min of two)={min(r,north_edge):6.1f}u")

print("\n=== OFF-SEAM sweep: need cx-132>=0 (west edge off seam) AND clearance>=132 ===")
for cx in range(132,320,8):
    for cz in (-176,-192,-208,-224,-240):
        r=clearance(cx,cz); ne=abs(cz)
        rmax=min(r,ne)
        west_edge=cx-132
        if rmax>=132 and west_edge>=0:
            print(f"  OFFSEAM FIT cx={cx} cz={cz}  clearance={r:.0f} north={ne} Rmax={rmax:.0f} westEdge={west_edge}")
print("  (any line above = an off-seam R132 site exists; none = wrap is mandatory)")

print("\n=== whole-block-shift achievable centers (64u lattice from MEC 935.8,-767.3) ===")
mecx,mecz=935.8,-767.3
for k in (11,12,13,14):
    for j in (8,9,10):
        cx=mecx-64*k; cz=mecz+64*j
        if cx< -60 or cz< -400: continue
        r=clearance(cx,cz); ne=abs(cz); rmax=min(r,ne); we=cx-132
        seam = "OFF-SEAM" if we>=0 else "WRAPS"
        fit = "FIT-R132" if rmax>=132 else "     "
        print(f"  shift(-{k},+{j}) center=({cx:.1f},{cz:.1f})  clearance={r:6.1f} north={ne:4.0f} Rmax={rmax:6.1f} westEdge={we:6.1f} {seam} {fit}")
