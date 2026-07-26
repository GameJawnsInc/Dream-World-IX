"""Ranking + refined coastal metric + world coords + permutation check."""
import sys, json, math
from collections import Counter
from pathlib import Path
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/gui-workspace-improvements-277c74/ff9mapkit")
from ff9mapkit.world import extract as X
SP = Path(__file__).resolve().parent
det = json.loads((SP/"object_census.json").read_text(encoding="utf-8"))

# permutation check
perm = Counter()
for (bx,by) in X.list_object_blocks(disc=1):
    bm = X.read_block(bx,by,disc=1,part="object")
    perm[sorted(bm.flat_index) == list(range(bm.vcount))] += 1
print("flat_index is a PERMUTATION of 0..vcount-1:", dict(perm))

SEAP = ["sea1","sea2","sea3","sea4","sea5","sea6","beach1","beach2"]
AREA_PLACE = {  # area -> destination field(s) decoded from the world .eb (locate.area_to_fields)
 0:"(no .eb case)",2:"Alexandria",6:"Treno",7:"S.Gate/Treno Arch",9:"S.Gate/Dali Gate",
 10:"S.Gate/Bohden Gate",14:"Dali",15:"N.Gate/Melda Arch",22:"Qu's Marsh (Mist)",24:"Lindblum/Dragon's Gate",
 27:"Earth Shrine (airship-only)",28:"Desert Palace",32:"Fossil Roo exit",34:"Madain Sari",
 41:"Qu's Marsh (Outer)",44:"Water Shrine (airship-only)",45:"Ipsen's Castle",48:"Esto Gaza",
 49:"Fire Shrine (airship-only)",54:"(no field)",56:"(no field)",57:"(no field)",60:"Gizamaluke/Cavern(706)",
 63:"(no .eb case)"}

rows=[]
for k,d in det.items():
    s=d["summary"]; bx,by=s["bx"],s["by"]
    ob = X.read_block(bx,by,disc=1,part="object")
    OP=[(v[0],v[2]) for v in ob.verts]
    best=(1e9,"-")
    for p in SEAP:
        if p not in s["parts"]: continue
        wm = X.read_block(bx,by,disc=1,part=p)
        for v in wm.verts:
            for (ox,oz) in OP:
                dd=(v[0]-ox)**2+(v[2]-oz)**2
                if dd<best[0]**2 if best[0]<1e9 else True:
                    pass
        # cheaper: bbox-based min
        wx=[v[0] for v in wm.verts]; wz=[v[2] for v in wm.verts]
        m=min(math.hypot(v[0]-ox, v[2]-oz) for v in wm.verts for (ox,oz) in OP[::max(1,len(OP)//60)])
        if m<best[0]: best=(m,p)
    areas=sorted({X.decode_id(int(i))["area"] for i in s["idalls"]})
    rows.append(dict(block=[bx,by], tris=s["tris"], verts=s["verts"],
                     foot=round(s["dx"]*s["dz"],1), dx=s["dx"], dz=s["dz"], dy=s["dy"],
                     comps=s["n_components"], min_comp=s["smallest_comp_tris"],
                     edge_water_d=None if best[0]>=1e9 else round(best[0],2), water_part=best[1],
                     areas=areas, place="/".join(AREA_PLACE.get(a,f"area{a}") for a in areas),
                     topos=sorted(int(t) for t in s["topographs"]),
                     events=sorted(int(t) for t in s["events"]),
                     has_beach=bool({"beach1","beach2"} & set(s["parts"])),
                     worldx=s["worldx"], worldz=s["worldz"],
                     cell=[int((bx*64+(s['xmin']+s['xmax'])/2)//32), int(((by*64)+(-(s['zmin']+s['zmax'])/2))//32)]))
rows.sort(key=lambda r:(r["tris"], r["foot"]))
print("\n=== ALL 63 OBJECT BLOCKS, sorted by triangle count ===")
print(f"{'blk':>8} {'tri':>4} {'v':>5} {'dx':>6} {'dz':>6} {'dy':>6} {'foot':>7} {'cmp':>3} {'minC':>4} "
      f"{'edgeH2O':>8} {'part':>7} {'beach':>5} {'topos':>12} {'ev':>6}  place")
for r in rows:
    print(f"{str(tuple(r['block'])):>8} {r['tris']:>4} {r['verts']:>5} {r['dx']:>6.1f} {r['dz']:>6.1f} {r['dy']:>6.1f} "
          f"{r['foot']:>7.1f} {r['comps']:>3} {r['min_comp']:>4} "
          f"{('--' if r['edge_water_d'] is None else f'{r[chr(101)+chr(100)+chr(103)+chr(101)+chr(95)+chr(119)+chr(97)+chr(116)+chr(101)+chr(114)+chr(95)+chr(100)]:.1f}'):>8} "
          f"{r['water_part']:>7} {'YES' if r['has_beach'] else '.':>5} {str(r['topos']):>12} {str(r['events']):>6}  {r['place']}")
(SP/"object_rank.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
print("\nwrote", SP/"object_rank.json")
