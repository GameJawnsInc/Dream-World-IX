import sys, io, contextlib
from collections import defaultdict, deque
sys.path.insert(0,'../../ff9mapkit'); sys.path.insert(0,'.')
import contract_mass_gates as G
core=[(x,y) for x in (13,14,15) for y in (11,12)]
with contextlib.redirect_stdout(io.StringIO()):
    cand=G.load_candidate('stock',None,core_blocks=core)
DROP={49,50,58,7,62,45,46,36,37,27,28,48,51,10,59}
# cell -> set of topos present (from core_tris)
cell_topos=defaultdict(set)
for t in cand['core_tris']:
    cell_topos[t['cell']].add(t['topo'])
# kept cells = cells that have at least one non-dropped tri
kept=set(c for c,ts in cell_topos.items() if any(tp not in DROP for tp in ts))
# 4-conn components over kept
def comps(cells):
    cs=set(cells); seen=set(); out=[]
    for c in cs:
        if c in seen: continue
        q=deque([c]); seen.add(c); comp=[]
        while q:
            cc=q.popleft(); comp.append(cc)
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                n=(cc[0]+dx,cc[1]+dy)
                if n in cs and n not in seen: seen.add(n); q.append(n)
        out.append(comp)
    return sorted(out,key=len,reverse=True)
cc=comps(kept)
print('kept cells:',len(kept),' components sizes:',[len(c) for c in cc][:12])
main=set(cc[0])
# straddle cells = grass+desert cells
straddle=cand['straddle_cells']
# split straddle by x (east vs west). ecotone spans x 866-1002 in cells (c[0]*4). find the two lobes.
sx=sorted(set(c[0] for c in straddle))
print('straddle cell x-range (cell idx):',min(sx),max(sx),' world x',min(sx)*4,max(sx)*4)
# how many straddle cells in main vs dropped?
in_main=[c for c in straddle if c in main]
not_main=[c for c in straddle if c not in main]
print('straddle in MAIN comp:',len(in_main),'  straddle NOT in main:',len(not_main))
# which components hold straddle cells?
compidx={}
for i,comp in enumerate(cc):
    for c in comp: compidx[c]=i
from collections import Counter
strad_comp=Counter(compidx.get(c,-1) for c in straddle)
print('straddle cells by component index:',dict(strad_comp))
# body(16) and backing(41) cells component membership
body_cells=set(t['cell'] for t in cand['core_tris'] if t['topo']==16)
back_cells=set(t['cell'] for t in cand['core_tris'] if t['topo']==41)
print('body(16) cells:',len(body_cells),' in main:',len([c for c in body_cells if c in main]))
print('backing(41) cells:',len(back_cells),' in main:',len([c for c in back_cells if c in main]))
# east lobe: split straddle at the internal rock band. Report per-x count
xc=Counter(c[0] for c in straddle)
print('straddle count per cell-x:',dict(sorted(xc.items())))
