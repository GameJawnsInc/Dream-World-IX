"""SECOND INDEPENDENT re-derivation of Lane A's gate-bound numbers -- a from-scratch cross-check of
contract_mass_falsify_a.py that shares NO code with it (own family table, own edge index, own coast
scan; only the byte readers X.*/M.* are reused). Guards against a subtly-agreeing bug in the first
falsifier. Read-only. -> out/contract_mass/falsify_a_indep_crosscheck.json
"""
import json, math, sys, time
from collections import defaultdict, Counter
from pathlib import Path

HERE = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/ff9-special-effect-plugin-dll-2fdd97/studies/overworld-topography")
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
from ff9mapkit.world import extract as X   # noqa
from ff9mapkit.world import mesh as M      # noqa

t0 = time.time()
C = 4.0
GR = {0,1,2,3,10,11,12,13,42}; DE = {16,17,19,20}
SEA = ("sea1","sea2","sea3","sea4","sea5","beach1","beach2")
CAP = {"sea1":"Sea1","sea2":"Sea2","sea3":"Sea3","sea4":"Sea4","sea5":"Sea5","beach1":"Beach1","beach2":"Beach2"}
STAGE = HERE/"out"/"rung_e"/"FF9CustomMap-world"


def famof(topo):
    if topo in GR: return "grass"
    if topo in DE: return "desert"
    return None


def read_terrain(blocks, staged=False):
    tris = []
    for (bx,by) in blocks:
        try:
            if staged:
                p = STAGE/M.override_relpath(1,bx,by,part="Terrain")
                if not p.exists(): continue
                bm = M.blockmesh_from_ff9mesh(p,disc=1,x=bx,y=by,part="terrain")
            else:
                bm = X.read_block(bx,by,disc=1,part="terrain")
        except (ValueError,FileNotFoundError): continue
        ox,oz = X.block_world_origin(bx,by)
        for tri in bm.tris:
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            w = [(bm.verts[j][0]+ox, bm.verts[j][2]+oz) for j in tri]   # (x,z) only
            cx = sum(p[0] for p in w)/3.0; cz = sum(p[1] for p in w)/3.0
            tris.append((topo, famof(topo), w, (math.floor(cx/C),math.floor(cz/C)), (cx,cz)))
    return tris


def read_sea(blocks, staged=False):
    pts = []
    for (bx,by) in blocks:
        ox,oz = X.block_world_origin(bx,by)
        for part in SEA:
            try:
                if staged:
                    p = STAGE/M.override_relpath(1,bx,by,part=CAP[part])
                    if not p.exists(): continue
                    bm = M.blockmesh_from_ff9mesh(p,disc=1,x=bx,y=by,part=part)
                else:
                    bm = X.read_block(bx,by,disc=1,part=part)
            except (ValueError,FileNotFoundError,KeyError): continue
            for v in bm.verts:
                pts.append((v[0]+ox, v[2]+oz))
    return pts


def mind(px,pz,pts):
    best = None
    for (sx,sz) in pts:
        d = (px-sx)**2 + (pz-sz)**2
        if best is None or d < best: best = d
    return math.sqrt(best) if best is not None else None


def edge_own(tris):
    eo = defaultdict(list)
    for i,t in enumerate(tris):
        w = t[2]
        k = [(round(p[0],3),round(p[1],3)) for p in w]
        for a in range(3):
            e = frozenset((k[a],k[(a+1)%3]))
            if len(e)==2: eo[e].append(i)
    return eo


def analyze(tris, sea):
    eo = edge_own(tris)
    bcell = set(); ngd = 0
    for e,ow in eo.items():
        fams = {tris[i][1] for i in ow}
        if fams=={"grass","desert"}:
            ngd += 1
            for i in ow: bcell.add(tris[i][3])
    cf = defaultdict(set)
    for t in tris:
        if t[1]: cf[t[3]].add(t[1])
    straddle = {c for c,f in cf.items() if f=={"grass","desert"}}
    body16 = [t for t in tris if t[0]==16]
    res = dict(n_boundary=len(bcell), n_straddle=len(straddle), n_topo16=len(body16), n_gd_edges=ngd)
    if sea:
        res["boundary_floor"] = round(min(mind(c[0]*C+2, c[1]*C+2, sea) for c in bcell),3) if bcell else None
        res["straddle_floor"] = round(min(mind(c[0]*C+2, c[1]*C+2, sea) for c in straddle),3) if straddle else None
        res["body_floor"] = round(min(mind(t[4][0], t[4][1], sea) for t in body16),3) if body16 else None
    # perimeter (1-owner) edges for the mesh-edge convention
    segs = [tuple(e) for e,ow in eo.items() if len(ow)==1]
    return res, bcell, straddle, body16, segs


def pt_seg(px,pz,segs):
    best = None
    for (a,b) in segs:
        ax,az=a; bx,bz=b; dx=bx-ax; dz=bz-az; L2=dx*dx+dz*dz
        if L2<1e-12: d=math.hypot(px-ax,pz-az)
        else:
            tt=max(0.0,min(1.0,((px-ax)*dx+(pz-az)*dz)/L2))
            d=math.hypot(px-(ax+tt*dx),pz-(az+tt*dz))
        if best is None or d<best: best=d
    return best


# STOCK
CORE = [(bx,by) for bx in (13,14,15) for by in (11,12)]
RING = sorted({(bx+dx,by+dy) for (bx,by) in CORE for dx in(-1,0,1) for dy in(-1,0,1)})
st = read_terrain(RING); ss = read_sea(RING)
res, bc, sc, b16, segs = analyze(st, ss)
print("STOCK", res, "sea_verts", len(ss))

# RUNG E
sb = set()
for p in STAGE.rglob("*Terrain.ff9mesh"):
    n=p.name.split("Block[")[1]; bx=int(n.split("]")[0]); by=int(n.split("[")[1].split("]")[0]); sb.add((bx,by))
sb=sorted(sb)
rt = read_terrain(sb, staged=True); rsea = read_sea(sb, staged=True)
rres, rbc, rsc, rb16, rsegs = analyze(rt, rsea)
# valid convention = coastal-filtered perimeter edges (near a sea vertex within 5u)
sset = rsea
def near_sea(x,z):
    for (sx,sz) in sset:
        if abs(x-sx)<=5 and abs(z-sz)<=5 and math.hypot(x-sx,z-sz)<=5: return True
    return False
coastal = [(a,b) for (a,b) in rsegs if near_sea(*a) or near_sea(*b)]
re_body_pe = round(min(pt_seg(t[4][0],t[4][1],coastal) for t in rb16),3)
re_str_pe = round(min(pt_seg(c[0]*C+2,c[1]*C+2,coastal) for c in rsc),3)
re_bnd_pe = round(min(pt_seg(c[0]*C+2,c[1]*C+2,coastal) for c in rbc),3)
print("RUNG_E counts", {k:rres[k] for k in ('n_boundary','n_straddle','n_topo16')})
print("RUNG_E sea-vertex (should be near-zero, invalid):", {k:rres.get(k) for k in ('boundary_floor','straddle_floor','body_floor')})
print("RUNG_E coastal-filtered perimeter-edge (valid):", dict(body=re_body_pe, straddle=re_str_pe, boundary=re_bnd_pe), "coastal_segs", len(coastal))

out = dict(
    stock=res, stock_sea_verts=len(ss),
    rung_e_counts={k:rres[k] for k in ('n_boundary','n_straddle','n_topo16','n_gd_edges')},
    rung_e_seavtx_invalid={k:rres.get(k) for k in ('boundary_floor','straddle_floor','body_floor')},
    rung_e_coastal_edge_valid=dict(body=re_body_pe, straddle=re_str_pe, boundary=re_bnd_pe, n_coastal_segs=len(coastal)),
    elapsed_s=round(time.time()-t0,1),
)
(HERE/"out"/"contract_mass"/"falsify_a_indep_crosscheck.json").write_text(json.dumps(out,indent=1))
print("elapsed", out["elapsed_s"])
