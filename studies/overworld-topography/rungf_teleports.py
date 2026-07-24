import sys, math
from collections import defaultdict
sys.argv=["tp"]
import contract_mass_gates as G
LIVE = r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap-world"
CORE = sorted({(bx,by) for by in (16,17,18,19) for bx in (0,1,2,3,4)})
CELL=G.CELL
region = G.moore_ring(CORE,2)
tris,_ = G.load_region(region, mod_dir=LIVE)
core=set(CORE)
fam_by_cell=defaultdict(set); topo_by_cell=defaultdict(set); yy_by_cell=defaultdict(list); pts=[]
for t in tris:
    if t["block"] not in core: continue
    fam_by_cell[t["cell"]].add(t["fam"]); topo_by_cell[t["cell"]].add(t["topo"])
    yy_by_cell[t["cell"]].append(sum(p[1] for p in t["w"])/3.0)
    pts.append(t)
def midcell(c): return (c[0]*CELL+CELL/2.0, c[1]*CELL+CELL/2.0)
def ymed(c):
    v=sorted(yy_by_cell[c]); return v[len(v)//2] if v else None
def centroid(cs): return (sum(c[0] for c in cs)/len(cs), sum(c[1] for c in cs)/len(cs))
straddles=[c for c in fam_by_cell if {"grass","desert"}<=fam_by_cell[c]]
grass=[c for c in fam_by_cell if fam_by_cell[c]=={"grass"}]
dunes=[c for c in topo_by_cell if 41 in topo_by_cell[c]]
sc=centroid(straddles); dc=centroid(dunes)
straddle_pick=min(straddles,key=lambda c:(c[0]-sc[0])**2+(c[1]-sc[1])**2)
dunes_pick=min(dunes,key=lambda c:(c[0]-dc[0])**2+(c[1]-dc[1])**2)
# grass: pick a solidly-grass cell whose 4 orthogonal neighbours are all grass-only (interior grass, walkable, mid-cell safe), farthest from straddle centroid
gset=set(grass)
def grass_interior(c):
    return all((c[0]+dx,c[1]+dy) in gset for dx,dy in[(1,0),(-1,0),(0,1),(0,-1)])
gi=[c for c in grass if grass_interior(c)]
grass_pick=max(gi,key=lambda c:(c[0]-sc[0])**2+(c[1]-sc[1])**2) if gi else max(grass,key=lambda c:(c[0]-sc[0])**2+(c[1]-sc[1])**2)
print("counts: straddle=%d grass=%d grass_interior=%d dunes=%d"%(len(straddles),len(grass),len(gi),len(dunes)))
for label,cell in [("GRASS LOBE",grass_pick),("ECOTONE STRADDLE",straddle_pick),("DUNES BACKING",dunes_pick)]:
    mx,mz=midcell(cell); y=ymed(cell)
    print(f"  {label:16s} cell={cell} -> X={mx:.1f} Z={mz:.1f} (y~{y:.2f}) fam={sorted(str(x) for x in fam_by_cell[cell])} topo={sorted(topo_by_cell[cell])}")
xs=[sum(q[0] for q in t['w'])/3 for t in pts]; zs=[sum(q[2] for q in t['w'])/3 for t in pts]
print(f"  island land centroid X={sum(xs)/len(xs):.1f} Z={sum(zs)/len(zs):.1f}  bbox X[{min(xs):.1f},{max(xs):.1f}] Z[{min(zs):.1f},{max(zs):.1f}]")
