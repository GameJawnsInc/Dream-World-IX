import sys, math, io, contextlib, random
sys.path.insert(0,'../../ff9mapkit'); sys.path.insert(0,'.')
import contract_mass_gates as G
core = [(x,y) for x in (13,14,15) for y in (11,12)]
with contextlib.redirect_stdout(io.StringIO()):
    cand = G.load_candidate('stock', None, core_blocks=core)
def centers(cells): return [G.cell_center(c) for c in cells]
bpts=centers(cand['boundary_cells']); spts=centers(cand['straddle_cells']); tpts=[G.tri_centroid_xz(t) for t in cand['body_tris']]

def welzl(points):
    P=[(float(a),float(b)) for a,b in {(round(p[0],3),round(p[1],3)) for p in points}]
    random.seed(1); random.shuffle(P)
    def cc2(a,b): return ((a[0]+b[0])/2,(a[1]+b[1])/2,math.hypot(a[0]-b[0],a[1]-b[1])/2)
    def cc3(a,b,c):
        ax,ay=a;bx,by=b;cx,cy=c
        d=2*(ax*(by-cy)+bx*(cy-ay)+cx*(ay-by))
        if abs(d)<1e-12: 
            # collinear: use farthest pair
            pr=[(a,b),(a,c),(b,c)]; best=max(pr,key=lambda pq:math.hypot(pq[0][0]-pq[1][0],pq[0][1]-pq[1][1]))
            return cc2(*best)
        ux=((ax*ax+ay*ay)*(by-cy)+(bx*bx+by*by)*(cy-ay)+(cx*cx+cy*cy)*(ay-by))/d
        uy=((ax*ax+ay*ay)*(cx-bx)+(bx*bx+by*by)*(ax-cx)+(cx*cx+cy*cy)*(bx-ax))/d
        return (ux,uy,math.hypot(ax-ux,ay-uy))
    def inside(p,c): return math.hypot(p[0]-c[0],p[1]-c[1])<=c[2]+1e-7
    c=None
    for i,p in enumerate(P):
        if c and inside(p,c): continue
        c=(p[0],p[1],0)
        for j in range(i):
            q=P[j]
            if inside(q,c): continue
            c=cc2(p,q)
            for k in range(j):
                r=P[k]
                if inside(r,c): continue
                c=cc3(p,q,r)
    return c
for name,pts in [('boundary',bpts),('straddle',spts),('body',tpts)]:
    xs=[p[0] for p in pts]; zs=[p[1] for p in pts]
    cx=sum(xs)/len(xs); cz=sum(zs)/len(zs)
    maxc=max(math.hypot(p[0]-cx,p[1]-cz) for p in pts)
    m=welzl(pts)
    print(f'{name}: n={len(pts)} span {max(xs)-min(xs):.0f}x{max(zs)-min(zs):.0f} centroid=({cx:.1f},{cz:.1f}) maxFromCentroid={maxc:.1f}  MEC=({m[0]:.1f},{m[1]:.1f}) R={m[2]:.1f}')
allp=bpts+spts+tpts; m=welzl(allp)
print(f'UNION MEC=({m[0]:.1f},{m[1]:.1f}) R={m[2]:.1f}  (n={len(allp)})')
# also straddle+boundary only (the two binding cell classes)
m2=welzl(bpts+spts); print(f'boundary+straddle MEC=({m2[0]:.1f},{m2[1]:.1f}) R={m2[2]:.1f}')
