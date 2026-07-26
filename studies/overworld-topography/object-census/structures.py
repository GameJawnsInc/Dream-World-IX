"""WHOLE-STRUCTURE census: weld all 63 disc-1 Object meshes in WORLD space -> named landmarks."""
import sys, io, re, math, json, csv
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/gui-workspace-improvements-277c74/ff9mapkit")
from ff9mapkit.world import extract as X
SP = Path(__file__).resolve().parent

src = io.open(r"C:/gd/FFIX/Memoria/Assembly-CSharp/Global/ff9/ff9.cs", encoding="utf-8", errors="replace").read()
i = src.index("array3[0, 0] = new ff9.navipos")
ent = re.findall(r"array3\[(\d+), (\d+)\] = new ff9\.navipos\s*\{(.*?)\}", src[i:i+200000], re.S)
NAMES = {0:"Alexandria Harbour",1:"Alexandria",2:"Evil Forest",3:"Ice Cavern",4:"Quan Dwelling",5:"Treno",
 6:"South Gate",7:"South Gate",8:"South Gate",9:"South Gate",10:"South Gate",11:"Ice Cavern",12:"Observatory Mtn",
 13:"Dali",14:"North Gate",15:"North Gate",16:"Gizamaluke Grotto",17:"Burmecia",18:"Cleyra",19:"Chocobo Forest",
 20:"Gizamaluke Grotto",21:"Qu Marsh (Mist)",22:"Pinnacle Rocks",23:"Lindblum Dragon Gate",24:"Lindblum",
 25:"Lindblum Harbour",26:"Earth Shrine",27:"Desert Palace",28:"Mognet Central",29:"Qu Marsh (Outer)",
 30:"Black Mage Village",31:"Fossil Roo",32:"Conde Petie",33:"Madain Sari",34:"CP Mountain Path",
 35:"CP Mountain Path",36:"Iifa Tree",37:"Chocobo Lagoon",38:"Wind Shrine",39:"Daguerreo",40:"Qu Marsh (Forgotten)",
 41:"Oeilvert",42:"Landing Site",43:"Water Shrine",44:"Ipsen Castle",45:"Qu Marsh (Archipelago)",
 46:"Shimmering Island",47:"Esto Gaza",48:"Fire Shrine",49:"Chocobo Paradise",53:"Memoria",
 54:"Air Garden (Alex)",55:"Air Garden (Peninsula)",56:"Air Garden (Canyon)",57:"Air Garden (Archipelago)",
 58:"Air Garden (Ocean)",59:"Gizamaluke Grotto"}
MARK=[]
for dim, loc, body in ent:
    if dim != "1": continue
    tx = re.search(r"tx = ([-\d]+)", body); ty = re.search(r"ty = ([-\d]+)", body)
    if not tx or not ty: continue
    TX,TY=int(tx.group(1)),int(ty.group(1))
    if TX==0 and TY==0: continue
    MARK.append((int(loc), NAMES.get(int(loc),"?"), TX/256.0, TY/256.0))

WATERP=["sea1","sea2","sea3","sea4","sea5","sea6","beach1","beach2"]
partmap=defaultdict(set)
env=X._worldmap_env(1)
pat=re.compile(r"worldmap/disc1/0_1/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
for k in env.container:
    m=pat.search((k or "").lower())
    if m: partmap[(int(m.group(1)),int(m.group(2)))].add(m.group(3))
waterpts=[]
for (bx,by),parts in partmap.items():
    for p in sorted(parts & set(WATERP)):
        wm=X.read_block(bx,by,disc=1,part=p)
        for v in wm.verts:
            waterpts.append((v[0]+bx*64, v[2]-by*64, p))
print("water sample points:", len(waterpts))

tri_world=[]
for (bx,by) in X.list_object_blocks(disc=1):
    bm=X.read_block(bx,by,disc=1,part="object")
    tan=bm.tangents
    for t in range(len(bm.tris)):
        idall=int(round(tan[bm.flat_index[t*3]][0]))
        vs=[(bm.verts[k][0]+bx*64, bm.verts[k][1], bm.verts[k][2]-by*64) for k in bm.tris[t]]
        tri_world.append(((bx,by), idall, vs))
print("total object triangles (disc1):", len(tri_world))

key={}; rep={}
def find(a):
    while rep[a]!=a: rep[a]=rep[rep[a]]; a=rep[a]
    return a
def union(a,b):
    ra,rb=find(a),find(b)
    if ra!=rb: rep[ra]=rb
tri_ids=[]
for _,_,vs in tri_world:
    ids=[]
    for v in vs:
        k=(round(v[0],2),round(v[1],2),round(v[2],2))
        if k not in key:
            key[k]=len(key); rep[key[k]]=key[k]
        ids.append(key[k])
    tri_ids.append(ids)
for ids in tri_ids:
    union(ids[0],ids[1]); union(ids[1],ids[2])
groups=defaultdict(list)
for ti,ids in enumerate(tri_ids):
    groups[find(ids[0])].append(ti)
print("welded structures:", len(groups))

rows=[]
for root,tl in groups.items():
    vs=[v for ti in tl for v in tri_world[ti][2]]
    xs=[v[0] for v in vs]; ys=[v[1] for v in vs]; zs=[v[2] for v in vs]
    cx=(min(xs)+max(xs))/2; cz=(min(zs)+max(zs))/2
    blks=sorted({tri_world[ti][0] for ti in tl})
    idc=Counter(tri_world[ti][1] for ti in tl)
    nm=min(MARK,key=lambda m: math.hypot(m[2]-cx,m[3]-cz))
    nd=math.hypot(nm[2]-cx,nm[3]-cz)
    inside=[m[1] for m in MARK if min(xs)-6<=m[2]<=max(xs)+6 and min(zs)-6<=m[3]<=max(zs)+6]
    step=max(1,len(vs)//160)
    cd=min((math.hypot(w[0]-v[0], w[1]-v[2]), w[2]) for v in vs[::step] for w in waterpts[::7])
    rows.append(dict(tris=len(tl), verts=len(set((round(v[0],2),round(v[1],2),round(v[2],2)) for v in vs)),
                     blocks=[list(b) for b in blks], nblocks=len(blks),
                     wx=[round(min(xs),1),round(max(xs),1)], wz=[round(min(zs),1),round(max(zs),1)],
                     y=[round(min(ys),2),round(max(ys),2)],
                     dx=round(max(xs)-min(xs),1), dz=round(max(zs)-min(zs),1), dy=round(max(ys)-min(ys),1),
                     cx=round(cx,1), cz=round(cz,1),
                     nearest=nm[1], nearest_loc=nm[0], nearest_d=round(nd,1),
                     markers_in_bbox=inside, coast_d=round(cd[0],1), coast_part=cd[1],
                     idalls={str(k):v for k,v in sorted(idc.items())},
                     topos=sorted({X.decode_id(k)["topograph"] for k in idc}),
                     areas=sorted({X.decode_id(k)["area"] for k in idc}),
                     events=sorted({X.decode_id(k)["event"] for k in idc})))
rows.sort(key=lambda r:(r["tris"], r["dx"]*r["dz"]))
hdr = "%5s %5s %6s %6s %6s %7s %7s %26s %12s %7s  landmark" % ("tri","v","dx","dz","dy","coastD","part","blocks","topos","ev")
print("")
print(hdr)
for r in rows:
    print("%5d %5d %6.1f %6.1f %6.1f %7.1f %7s %26s %12s %7s  %s (d=%.1f)%s" % (
        r["tris"], r["verts"], r["dx"], r["dz"], r["dy"], r["coast_d"], r["coast_part"],
        str([tuple(b) for b in r["blocks"]]), str(r["topos"]), str(r["events"]),
        r["nearest"], r["nearest_d"], ("  bbox:" + str(r["markers_in_bbox"])) if r["markers_in_bbox"] else ""))
(SP/"structures.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
cols=["tris","verts","nblocks","blocks","dx","dz","dy","wx","wz","y","cx","cz","coast_d","coast_part",
      "nearest","nearest_loc","nearest_d","markers_in_bbox","topos","areas","events","idalls"]
with open(SP/"structures.csv","w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore"); w.writeheader()
    for r in rows: w.writerow({k:(json.dumps(v) if isinstance(v,(dict,list)) else v) for k,v in r.items() if k in cols})
print("")
print("wrote structures.json / structures.csv")
