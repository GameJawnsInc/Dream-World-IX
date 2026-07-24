"""Row-distribution reconciliation: reproduce the lane's BOTH-SIDES row binning independently and
compare per-family-side, to decide whether the lane's row-distribution numbers are a bug or a
population-definition choice. READ-ONLY. Writes out/contract_mass/falsify_b_rows.json."""
from __future__ import annotations
import json, math, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/ff9-special-effect-plugin-dll-2fdd97/studies/overworld-topography")
sys.path.insert(0, str(HERE.parent.parent / "ff9mapkit")); sys.path.insert(0, str(HERE))
from ff9mapkit.world import extract as X
from ff9mapkit.world import grassland as G
from ff9mapkit.world import mesh as M

CELL = 4.0
FAM_OF = {}
for _t in (0,1,2,3,10,11,12,13,42): FAM_OF[_t]="grass"
for _t in (16,17,19,20): FAM_OF[_t]="desert"
FAM_OF[41]="dunes"
EPS=0.006; TOL_V=0.008; ROW_PITCH=0.03125
STRIP_U0,STRIP_U1=G.STRIP_U; ROW0_V0=G.STRIPS_V[0][0]
GD_DU,GD_DV=G.STRIPS[("grass","desert")]["du"],G.STRIPS[("grass","desert")]["dv"]

def gd_row(uv3):
    u_lo,u_hi=STRIP_U0+GD_DU-EPS,STRIP_U1+GD_DU+EPS
    if not all(u_lo<=u<=u_hi for (u,_v) in uv3): return None
    v_min=min(v for (_u,v) in uv3); base=ROW0_V0+GD_DV
    k=round((v_min-base)/ROW_PITCH)
    if k<0 or k>3 or abs((v_min-base)-k*ROW_PITCH)>TOL_V: return None
    return int(k)

def load(bx,by,staged=None):
    if staged is not None:
        rel=M.override_relpath(1,bx,by,part="Terrain"); p=staged/rel
        if not p.exists(): return None
        bm=M.blockmesh_from_ff9mesh(p,disc=1,x=bx,y=by,part="terrain")
    else:
        try: bm=X.read_block(bx,by,disc=1,part="terrain")
        except (ValueError,FileNotFoundError): return None
    out=[]
    for tri in bm.tris:
        topo=X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
        uv=[(float(bm.uvs[j][0]),float(bm.uvs[j][1])) for j in tri]
        out.append(dict(topo=topo,fam=FAM_OF.get(topo),uv=uv))
    return out

def rows_bothsides(tris, label):
    both=Counter(); byside=defaultdict(Counter)
    for t in tris:
        if t["fam"] not in ("grass","desert"): continue
        k=gd_row(t["uv"])
        if k is None: continue
        both[k]+=1; byside[t["fam"]][k]+=1
    tot=sum(both.values())
    frac={k: round(both.get(k,0)/tot,4) for k in range(4)} if tot else {}
    print(f"\n{label}: total strip_grass_desert (BOTH sides) = {tot}")
    print(f"  both-sides counts : {dict(sorted(both.items()))}")
    print(f"  both-sides fracs  : " + ",".join(f"r{k}={frac.get(k,0):.4f}" for k in range(4)))
    for side in ("grass","desert"):
        c=byside[side]; st=sum(c.values()) or 1
        print(f"  {side}-side counts  : {dict(sorted(c.items()))}  frac=" +
              ",".join(f"{c.get(k,0)/st:.3f}" for k in range(4)))
    return dict(total=tot, both=dict(both), fracs=frac,
                grass_side=dict(byside["grass"]), desert_side=dict(byside["desert"]))

def main():
    RE=HERE/"out"/"rung_e"/"FF9CustomMap-world"
    stock=[]
    for bx in (13,14,15):
        for by in (11,12):
            t=load(bx,by)
            if t: stock+=t
    s=rows_bothsides(stock,"STOCK (13-15,11-12) all terrain tris")
    e_blocks=[]
    import re
    for p in RE.rglob("*Terrain.ff9mesh"):
        m=re.search(r"Block\[(\d+)\]\[(\d+)\]",p.name)
        if m: e_blocks.append((int(m.group(1)),int(m.group(2))))
    e=[]
    for bx,by in sorted(set(e_blocks)):
        t=load(bx,by,staged=RE)
        if t: e+=t
    r=rows_bothsides(e,"RUNG E staged all terrain tris")
    (HERE/"out"/"contract_mass"/"falsify_b_rows.json").write_text(
        json.dumps(dict(stock=s,rung_e=r),indent=1),encoding="utf-8")

if __name__=="__main__": main()
