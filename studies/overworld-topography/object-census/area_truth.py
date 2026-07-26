"""Empirical AREA -> place: world centroid of each area's entrance tiles vs the engine navipos markers."""
import sys, io, re, math, json
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/gui-workspace-improvements-277c74/ff9mapkit")
from ff9mapkit.world import extract as X
from ff9mapkit.world import locate as L

# --- navipos markers (engine table) ---
src = io.open(r"C:/gd/FFIX/Memoria/Assembly-CSharp/Global/ff9/ff9.cs", encoding="utf-8", errors="replace").read()
i = src.index("array3[0, 0] = new ff9.navipos")
ent = re.findall(r"array3\[(\d+), (\d+)\] = new ff9\.navipos\s*\{(.*?)\}", src[i:i+200000], re.S)
NAMES = {0:'Alexandria Harbor',1:'Alexandria',2:'Evil Forest',3:'Ice Cavern',4:"Quan's Dwelling",5:'Treno',
 6:'South Gate',7:'South Gate',8:'South Gate',9:'South Gate',10:'South Gate',11:'Ice Cavern',12:'Observatory Mtn',
 13:'Dali',14:'North Gate',15:'North Gate',16:'Gizamaluke',17:'Burmecia',18:'Cleyra',19:'Chocobo Forest',
 20:'Gizamaluke',21:"Qu's Marsh",22:'Pinnacle Rocks',23:'Lindblum Dragon Gate',24:'Lindblum',25:'Lindblum Harbor',
 26:'Earth Shrine',27:'Desert Palace',28:'Mognet Central',29:"Qu's Marsh",30:'Black Mage Village',31:'Fossil Roo',
 32:'Conde Petie',33:'Madain Sari',34:'CP Mountain Path',35:'CP Mountain Path',36:'Iifa Tree',37:'Chocobo Lagoon',
 38:'Wind Shrine',39:'Daguerreo',40:"Qu's Marsh",41:'Oeilvert',42:'Landing Site',43:'Water Shrine',44:"Ipsen's Castle",
 45:"Qu's Marsh",46:'Shimmering Island',47:'Esto Gaza',48:'Fire Shrine',49:'Chocobo Paradise',53:'Memoria',
 54:'Air Garden',55:'Air Garden',56:'Air Garden',57:'Air Garden',58:'Air Garden',59:'Gizamaluke'}
MARK = []
for dim, loc, body in ent:
    if dim != "1": continue
    tx = re.search(r"tx = ([-\d]+)", body); ty = re.search(r"ty = ([-\d]+)", body)
    if not tx or not ty: continue
    TX, TY = int(tx.group(1)), int(ty.group(1))
    if TX == 0 and TY == 0: continue
    MARK.append((int(loc), NAMES.get(int(loc),'?'), TX/256.0, TY/256.0))
print("live markers:", len(MARK))

# --- terrain entrance tiles per area, world centroid ---
tiles = defaultdict(list)
for (bx, by) in X.list_blocks(disc=1):
    bm = X.read_block(bx, by, disc=1, part="terrain")
    tan = bm.tangents
    for t in range(len(bm.tris)):
        idall = int(round(tan[bm.flat_index[t*3]][0]))
        d = X.decode_id(idall)
        if not d["event"]: continue
        tri = bm.tris[t]
        cx = sum(bm.verts[k][0] for k in tri)/3.0 + bx*64
        cz = sum(bm.verts[k][2] for k in tri)/3.0 - by*64
        tiles[d["area"]].append((cx, cz, bx, by, idall, d["event"]))
a2f = L.area_to_fields()
names = L.field_names()
print("\narea | ntiles | world centroid | nearest navipos marker (dist) | locate's .eb field for this area")
for a in sorted(tiles):
    pts = tiles[a]
    cx = sum(p[0] for p in pts)/len(pts); cz = sum(p[1] for p in pts)/len(pts)
    best = min(MARK, key=lambda m: math.hypot(m[2]-cx, m[3]-cz))
    d = math.hypot(best[2]-cx, best[3]-cz)
    f = "; ".join(f"{ff}({names.get(ff,'?')})" for _c, ff in a2f.get(a, [("-",None)]))
    blocks = sorted({(p[2],p[3]) for p in pts})
    print(f"{a:4d} | {len(pts):6d} | ({cx:7.1f},{cz:8.1f}) | loc{best[0]:2d} {best[1]:22s} d={d:6.1f} | {f}")
    print(f"       blocks={blocks}")
