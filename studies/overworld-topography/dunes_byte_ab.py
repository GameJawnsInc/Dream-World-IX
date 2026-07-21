"""DEFINITIVE byte-level test: does the DEPLOYED dunes mint paint each ecotone tile the SAME
as stock comp[1], or does it deviate in per-tile ORIENTATION? Reads deployed .ff9mesh + stock
p0data directly. NO writes."""
import sys, math, json
from collections import Counter, defaultdict, deque
from pathlib import Path

REPO = Path("C:/gd/Dream-World-IX/.claude/worktrees/overworld-work-continue-0d139c")
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.world import extract as X
from ff9mapkit.world import grassland as G
from ff9mapkit.world import mesh as M

GAME = Path("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX")
MOD = "FF9CustomMap-world"
BLOCK=64.0; CELL=4.0; NEI4=((1,0),(-1,0),(0,1),(0,-1)); ORIS=(0,90,180,270)
EPS=0.004
TOPO_FAM={17:"desert",41:"dunes",58:"rock",59:"hole"}

_S=G.STRIPS[("desert","dunes")]; _DU,_DV=_S["du"],_S["dv"]
def clamp01(v): return max(0.0,min(1.0,v))
def strip_uv(x,z,cell,row,ori):
    i,j=cell; fx=(x-CELL*i)/CELL; fz=(z-CELL*j)/CELL
    a,b=G.rot_ab(fx,fz,ori); a,b=clamp01(a),clamp01(b)
    u0,u1=G.STRIP_U; v0,v1=G.STRIPS_V[row]
    return [u0+a*(u1-u0)+_DU, v0+b*(v1-v0)+_DV]

def classify_tri(topo, world_pts, uvs, cell):
    """Recover (class, params, ori) by brute force over the generative parameter space."""
    fam=TOPO_FAM.get(topo)
    def match(fn):
        return all(abs(fn(p)[0]-uv[0])<EPS and abs(fn(p)[1]-uv[1])<EPS for p,uv in zip(world_pts,uvs))
    # try strip (desert|dunes column)
    for ori in ORIS:
        for row in range(4):
            if match(lambda p,r=row,o=ori: strip_uv(p[0],p[2],cell,r,o)):
                return ("strip",row,ori)
    # try mains for both grounds
    for ground in ("dunes","desert"):
        for uh in (0,1):
            for vh in (0,1):
                for ori in ORIS:
                    if match(lambda p,q=(uh,vh),o=ori,g=ground: G.ground_uv(p[0],p[2],cell,q,o,g)):
                        return ("mains",ground,(uh,vh),ori)
    return ("other",None,None)

def cell_of(x,z): return (math.floor(x/CELL), math.floor(z/CELL))

def gather(bm, bx, by):
    """{cell: list of (topo, ('strip',row,ori)|('mains',g,quad,ori)|('other',))}"""
    import numpy as np
    V=bm.verts; U=bm.uvs; TAN=bm.tangents
    tris=np.asarray(bm.flat_index,dtype=np.int64).reshape(-1,3)
    out=defaultdict(list)
    for tri in tris:
        wp=[(V[j][0]+BLOCK*bx, V[j][1], V[j][2]-BLOCK*by) for j in tri]
        topo=X.decode_id(int(round(TAN[tri[0]][0])))["topograph"]
        cx=sum(p[0] for p in wp)/3; cz=sum(p[2] for p in wp)/3
        cell=cell_of(cx,cz)
        uvs=[tuple(U[j]) for j in tri]
        cls=classify_tri(topo,wp,uvs,cell)
        out[cell].append((topo,cls))
    return out

# ---- STOCK comp[1]: blocks around (13-14,11-12) ----
print("reading stock comp[1] blocks (12-15, 10-13) ...")
stock={}
for bx in range(12,16):
    for by in range(10,14):
        try:
            bm=X.read_block(bx,by,disc=1,part="terrain")
            g=gather(bm,bx,by)
            for c,v in g.items(): stock[c]=v
        except Exception as e:
            pass
# dunes footprint = topo41 cells, largest connected comp
dunes_cells={c for c,tl in stock.items() if any(t==41 for t,_ in tl)}
def comps(cs):
    seen=set(); res=[]
    for s in cs:
        if s in seen: continue
        comp=set(); q=deque([s]); seen.add(s)
        while q:
            c=q.popleft(); comp.add(c)
            for di,dj in NEI4:
                n=(c[0]+di,c[1]+dj)
                if n in cs and n not in seen: seen.add(n); q.append(n)
        res.append(comp)
    return res
sc=sorted(comps(dunes_cells),key=len,reverse=True)
print("stock dunes comps sizes:", [len(x) for x in sc][:4])
STOCK_C1=sc[0] if sc and len(sc[0])>=100 else None
if STOCK_C1 is None:
    print("!! could not isolate stock comp1 130-cell footprint"); sys.exit(1)
print(f"stock comp1 = {len(STOCK_C1)} cells, bbox {min(c[0] for c in STOCK_C1)},{min(c[1] for c in STOCK_C1)} .. {max(c[0] for c in STOCK_C1)},{max(c[1] for c in STOCK_C1)}")

# ---- DEPLOYED MINT: blocks (18-20,17-19) ----
print("\nreading deployed mint blocks (18-20,17-19) ...")
mint={}
for bx in range(18,21):
    for by in range(17,20):
        p=GAME/MOD/M.override_relpath(1,bx,by,part="Terrain")
        if not p.exists():
            print("  MISSING",p.name); continue
        bm=M.blockmesh_from_ff9mesh(p,disc=1,x=bx,y=by,part="terrain")
        g=gather(bm,bx,by)
        for c,v in g.items(): mint[c]=v
mint_dunes={c for c,tl in mint.items() if any(t==41 for t,_ in tl)}
mc=sorted(comps(mint_dunes),key=len,reverse=True)
print("mint dunes comps sizes:", [len(x) for x in mc][:4])
MINT_C1=mc[0]
print(f"mint dunes footprint = {len(MINT_C1)} cells (comp1 130 + filled hole 14 = 144 expected), bbox {min(c[0] for c in MINT_C1)},{min(c[1] for c in MINT_C1)} .. {max(c[0] for c in MINT_C1)},{max(c[1] for c in MINT_C1)}")

# ---- translation: align dunes footprints by bbox-min ----
sminx=min(c[0] for c in STOCK_C1); sminz=min(c[1] for c in STOCK_C1)
mminx=min(c[0] for c in MINT_C1); mminz=min(c[1] for c in MINT_C1)
Tx,Tz=mminx-sminx, mminz-sminz
print(f"\ntranslation stock->mint = ({Tx},{Tz})")
# verify shapes match on comp1 cells
stock_norm={(c[0]-sminx,c[1]-sminz) for c in STOCK_C1}
# mint comp1 = mint footprint minus the hole (hole = enclosed). Just take stock cells + T and check they're dunes in mint.
def cell_class(tl):
    # collapse a cell's tris to a descriptor: dominant class + set of oris + rows/grounds
    strips=[(r,o) for t,c in tl if c[0]=="strip" for r,o in [(c[1],c[2])]]
    mains=[(g,o) for t,c in tl if c[0]=="mains" for g,o in [(c[1],c[3])]]
    others=[1 for t,c in tl if c[0]=="other"]
    if strips:
        rows=set(r for r,o in strips); oris=set(o for r,o in strips)
        return ("strip", tuple(sorted(rows)), tuple(sorted(oris)))
    if mains:
        gs=set(g for g,o in mains); oris=set(o for g,o in mains)
        return ("mains", tuple(sorted(gs)), tuple(sorted(oris)))
    return ("other",(),())

matched=0; missing=0
cls_match=strip_row_match=strip_ori_match=strip_total=0
mains_ori_match=mains_total=0
detail=[]
strip_ori_hist=Counter()   # (stock_ori_set, mint_ori_set) for strip cells
mains_ori_hist=Counter()
for c in STOCK_C1:
    mc_cell=(c[0]+Tx, c[1]+Tz)
    if c not in stock or mc_cell not in mint:
        missing+=1; continue
    sd=cell_class(stock[c]); md=cell_class(mint[mc_cell])
    matched+=1
    if sd[0]==md[0]: cls_match+=1
    if sd[0]=="strip":
        strip_total+=1
        if md[0]=="strip":
            if sd[1]==md[1]: strip_row_match+=1
            if sd[2]==md[2]: strip_ori_match+=1
            strip_ori_hist[(sd[2],md[2])]+=1
    elif sd[0]=="mains":
        mains_total+=1
        if md[0]=="mains":
            if sd[2]==md[2]: mains_ori_match+=1
            mains_ori_hist[(sd[2],md[2])]+=1

print(f"\n=== COMP1 (dunes-side) cell-by-cell: matched {matched}/{len(STOCK_C1)} (missing {missing}) ===")
print(f"class agree (strip-vs-mains): {cls_match}/{matched}")
print(f"STRIP cells (stock): {strip_total}  row-match {strip_row_match}  ORI-match {strip_ori_match}")
print(f"MAINS cells (stock): {mains_total}  ORI-match {mains_ori_match}")
print(f"\nstrip ori (stock_oris -> mint_oris) histogram:")
for k,v in sorted(strip_ori_hist.items(), key=lambda x:-x[1]): print(f"   {k[0]} -> {k[1]}  x{v}")
print(f"mains ori (stock_oris -> mint_oris) histogram (top 12):")
for k,v in sorted(mains_ori_hist.items(), key=lambda x:-x[1])[:12]: print(f"   {k[0]} -> {k[1]}  x{v}")

# ---- desert-SIDE outer ring (topo17 strip + generic mains) ----
def dilate(cells,exclude):
    nxt=set()
    for c in cells:
        for di,dj in NEI4:
            n=(c[0]+di,c[1]+dj)
            if n not in exclude: nxt.add(n)
    return nxt
def enclosed_hole(cs):
    xs=[c[0] for c in cs]; zs=[c[1] for c in cs]
    x0,x1,z0,z1=min(xs)-1,max(xs)+1,min(zs)-1,max(zs)+1
    outside,q=set(),deque()
    for s in [(i,z0) for i in range(x0,x1+1)]+[(i,z1) for i in range(x0,x1+1)]+[(x0,j) for j in range(z0,z1+1)]+[(x1,j) for j in range(z0,z1+1)]:
        if s not in cs and s not in outside: outside.add(s); q.append(s)
    while q:
        cc=q.popleft()
        for di,dj in NEI4:
            n=(cc[0]+di,cc[1]+dj)
            if x0<=n[0]<=x1 and z0<=n[1]<=z1 and n not in cs and n not in outside: outside.add(n); q.append(n)
    return {(i,j) for i in range(x0,x1+1) for j in range(z0,z1+1) if (i,j) not in cs and (i,j) not in outside}
FOOT=STOCK_C1|enclosed_hole(STOCK_C1)
OUTER=dilate(FOOT,FOOT)
o_matched=o_strip_total=o_strip_ori_match=o_mains_total=o_mains_ori_match=0
o_strip_hist=Counter()
for c in OUTER:
    mc_cell=(c[0]+Tx,c[1]+Tz)
    if c not in stock or mc_cell not in mint: continue
    sd=cell_class(stock[c]); md=cell_class(mint[mc_cell])
    o_matched+=1
    if sd[0]=="strip":
        o_strip_total+=1
        if md[0]=="strip":
            if sd[2]==md[2]: o_strip_ori_match+=1
            o_strip_hist[(sd[2],md[2])]+=1
    elif sd[0]=="mains":
        o_mains_total+=1
        if md[0]=="mains" and sd[2]==md[2]: o_mains_ori_match+=1
print(f"\n=== OUTER RING (desert-side) matched {o_matched} ===")
print(f"desert-STRIP cells (stock): {o_strip_total}  ORI-match {o_strip_ori_match}")
print(f"desert-MAINS cells (stock): {o_mains_total}  ORI-match {o_mains_ori_match}")
print("desert-strip ori (stock->mint):")
for k,v in sorted(o_strip_hist.items(),key=lambda x:-x[1]): print(f"   {k[0]} -> {k[1]}  x{v}")

summ=dict(matched=matched, strip_total=strip_total, strip_row_match=strip_row_match, strip_ori_match=strip_ori_match,
          mains_total=mains_total, mains_ori_match=mains_ori_match,
          o_strip_total=o_strip_total, o_strip_ori_match=o_strip_ori_match,
          o_mains_total=o_mains_total, o_mains_ori_match=o_mains_ori_match)
print("\nJSON:", json.dumps(summ))
