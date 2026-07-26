"""Pass 2: decode object IDALLs, per-component detail, coast distance, place-name cross-ref."""
import json, math, re, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/gui-workspace-improvements-277c74/ff9mapkit")
from ff9mapkit.world import extract as X
from ff9mapkit.world import navimap as NM

SP = Path(__file__).resolve().parent
det = json.loads((SP/"object_census.json").read_text(encoding="utf-8"))

# --- 1. distinct object IDALLs decoded --------------------------------------------------
allids = Counter()
for k, d in det.items():
    for i, n in d["summary"]["idalls"].items():
        allids[int(i)] += n
print("1. DISTINCT OBJECT-MESH IDALL VALUES (disc1, all 63 blocks):")
print(f"   {len(allids)} distinct; total tris {sum(allids.values())}")
for i in sorted(allids):
    dd = X.decode_id(i)
    print(f"   idall {i:6d} 0x{i:04X}  event={dd['event']} area={dd['area']:2d} topo={dd['topograph']:2d} "
          f"flags={dd['flags']}  tris={allids[i]}")
topo_tot = Counter()
for i, n in allids.items():
    topo_tot[X.decode_id(i)["topograph"]] += n
print("   topograph totals:", dict(sorted(topo_tot.items())))
ev_tot = Counter()
for i, n in allids.items():
    ev_tot[X.decode_id(i)["event"]] += n
print("   event totals:", dict(sorted(ev_tot.items())))

# --- 2. entrance areas of the block + neighbours -> place names ------------------------
blocks_all = set(X.list_blocks(disc=1))
area_cache = {}
def areas_of(bx, by):
    if (bx,by) in area_cache: return area_cache[(bx,by)]
    if (bx,by) not in blocks_all:
        area_cache[(bx,by)] = set(); return set()
    bm = X.read_block(bx, by, disc=1, part="terrain")
    s = set()
    for i in set(X.block_mapids(bm)):
        d = X.decode_id(i)
        if d["event"]:
            s.add(d["area"])
    area_cache[(bx,by)] = s
    return s

# --- 3. coast distance from the same block's water sub-meshes -------------------------
WATERP = ["beach1","beach2","sea1","sea2","sea3","sea4","sea5","sea6"]
def water_pts(bx, by, parts):
    pts = []
    for p in parts:
        if p not in WATERP: continue
        try:
            wm = X.read_block(bx, by, disc=1, part=p)
        except Exception:
            continue
        for v in wm.verts:
            pts.append((v[0], v[2], p))
    return pts

print("\n2. PER-BLOCK: place names (own+neighbour entrance areas) + coast distance + components")
rows = []
for k in sorted(det, key=lambda s: tuple(int(t) for t in s.split(","))):
    d = det[k]; s = d["summary"]; bx, by = s["bx"], s["by"]
    own = areas_of(bx, by)
    nb = set()
    for dx in (-1,0,1):
        for dy in (-1,0,1):
            if dx or dy: nb |= areas_of(bx+dx, by+dy)
    names_own = sorted({NM.MARKER_NAMES.get(a, f"area{a}") for a in own})
    names_nb  = sorted({NM.MARKER_NAMES.get(a, f"area{a}") for a in nb - own})
    wp = water_pts(bx, by, s["parts"])
    ocx = (s["xmin"]+s["xmax"])/2; ocz = (s["zmin"]+s["zmax"])/2
    if wp:
        bestd, bestp = min(((math.hypot(px-ocx, pz-ocz), pp) for px, pz, pp in wp), key=lambda t: t[0])
    else:
        bestd, bestp = float("inf"), "-"
    # also: is there an ocean-only block (no terrain) adjacent?
    sea_nb = [(bx+dx, by+dy) for dx in (-1,0,1) for dy in (-1,0,1)
              if (dx or dy) and (bx+dx, by+dy) not in blocks_all and 0 <= bx+dx < 24 and 0 <= by+dy < 20]
    rows.append(dict(block=[bx,by], tris=s["tris"], comps=s["n_components"], min_comp=s["smallest_comp_tris"],
                     dx=s["dx"], dz=s["dz"], dy=s["dy"], coast_d=None if bestd==float('inf') else round(bestd,1),
                     coast_part=bestp, names_own=names_own, names_nb=names_nb,
                     n_open_ocean_nb=len(sea_nb), idalls=s["idalls"], topos=sorted(int(t) for t in s["topographs"])))
    print(f"   ({bx:2d},{by:2d}) tri={s['tris']:5d} comps={s['comps'] if 'comps' in s else s['n_components']:3d} "
          f"minC={s['smallest_comp_tris']:4d} size {s['dx']:5.1f}x{s['dz']:5.1f}x{s['dy']:5.1f} "
          f"coast={'--' if bestd==float('inf') else f'{bestd:6.1f}u({bestp})':>16} oceanNb={len(sea_nb)} "
          f"| own={names_own} nb={names_nb}")

(SP/"object_coast.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
print("\nwrote", SP/"object_coast.json")
