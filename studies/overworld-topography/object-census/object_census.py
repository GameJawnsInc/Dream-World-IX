"""READ-ONLY census of stock world-map Object sub-meshes, disc 1."""
import csv, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(r"C:/gd/Dream-World-IX/.claude/worktrees/gui-workspace-improvements-277c74/ff9mapkit")))
from ff9mapkit.world import extract as X

OUT = Path(__file__).resolve().parent

def part_blocks(disc=1, lod="0_1"):
    env = X._worldmap_env(disc)
    pat = re.compile(rf"worldmap/disc{disc}/{lod}/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
    per = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            per[m.group(3)].add((int(m.group(1)), int(m.group(2))))
    return {p: sorted(b) for p, b in per.items()}

PARTS = part_blocks(1)
by_block = defaultdict(set)
for p, bs in PARTS.items():
    for b in bs:
        by_block[b].add(p)

WATER = {"beach1","beach2","sea1","sea2","sea3","sea4","sea5","sea6","sea4f"}

def components(bm):
    """Connected components over shared XYZ positions (mesh is flat/unindexed -> weld by rounded pos)."""
    V = bm.verts
    key = {}
    rep = {}
    def find(a):
        while rep[a] != a:
            rep[a] = rep[rep[a]]; a = rep[a]
        return a
    def union(a,b):
        ra, rb = find(a), find(b)
        if ra != rb: rep[ra] = rb
    ids = []
    for i,v in enumerate(V):
        k = (round(v[0],3), round(v[1],3), round(v[2],3))
        if k not in key:
            key[k] = i
            rep[i] = i
        ids.append(key[k])
    for t in bm.tris:
        a,b,c = (ids[t[0]], ids[t[1]], ids[t[2]])
        union(a,b); union(b,c)
    groups = defaultdict(list)
    for ti,t in enumerate(bm.tris):
        groups[find(ids[t[0]])].append(ti)
    comps = []
    tan = bm.tangents
    for root, tl in groups.items():
        vs = []
        for ti in tl:
            for vi in bm.tris[ti]:
                vs.append(V[vi])
        xs=[v[0] for v in vs]; ys=[v[1] for v in vs]; zs=[v[2] for v in vs]
        idalls = Counter(int(round(tan[bm.flat_index[ti*3]][0])) for ti in tl) if tan else Counter()
        comps.append(dict(tris=len(tl), verts=len(set((round(v[0],3),round(v[1],3),round(v[2],3)) for v in vs)),
                          x=[min(xs),max(xs)], y=[min(ys),max(ys)], z=[min(zs),max(zs)],
                          dx=max(xs)-min(xs), dz=max(zs)-min(zs), dy=max(ys)-min(ys),
                          cx=(min(xs)+max(xs))/2, cz=(min(zs)+max(zs))/2,
                          idalls={str(k):v for k,v in sorted(idalls.items())}))
    comps.sort(key=lambda c: c["tris"])
    return comps

rows = []
detail = {}
for (bx, by) in X.list_object_blocks(disc=1):
    bm = X.read_block(bx, by, disc=1, part="object")
    V = bm.verts
    xs=[v[0] for v in V]; ys=[v[1] for v in V]; zs=[v[2] for v in V]
    ids = X.block_mapids(bm)
    cnt = Counter(ids)
    topo = Counter(X.decode_id(i)["topograph"] for i in ids)
    ev = Counter(X.decode_id(i)["event"] for i in ids)
    ar = Counter(X.decode_id(i)["area"] for i in ids)
    U = bm.uvs
    us=[u[0] for u in U] if U else [0.0]; vv=[u[1] for u in U] if U else [0.0]
    comps = components(bm)
    parts_here = sorted(by_block[(bx,by)])
    coastal = sorted(set(parts_here) & WATER)
    # terrain topos under the block, for reference
    try:
        tbm = X.read_block(bx,by,disc=1,part="terrain")
        ttopo = Counter(X.decode_id(i)["topograph"] for i in X.block_mapids(tbm))
        tt = {str(k):v for k,v in sorted(ttopo.items())}
    except Exception as e:
        tt = {"err": str(e)}
    r = dict(bx=bx, by=by, tris=len(bm.tris), verts=bm.vcount, stride=bm.stride,
             channels=sorted(bm.channels), submeshes=len(bm.submeshes), use32=bm.use32,
             xmin=round(min(xs),3), xmax=round(max(xs),3), zmin=round(min(zs),3), zmax=round(max(zs),3),
             ymin=round(min(ys),3), ymax=round(max(ys),3),
             dx=round(max(xs)-min(xs),2), dz=round(max(zs)-min(zs),2), dy=round(max(ys)-min(ys),2),
             umin=round(min(us),4), umax=round(max(us),4), vmin=round(min(vv),4), vmax=round(max(vv),4),
             n_components=len(comps), smallest_comp_tris=comps[0]["tris"] if comps else 0,
             idalls={str(k):v for k,v in sorted(cnt.items())},
             topographs={str(k):v for k,v in sorted(topo.items())},
             events={str(k):v for k,v in sorted(ev.items())},
             areas={str(k):v for k,v in sorted(ar.items())},
             parts=parts_here, coastal_parts=coastal, is_coastal=bool(coastal),
             terrain_topographs=tt,
             worldx=[bx*64+round(min(xs),1), bx*64+round(max(xs),1)],
             worldz=[-by*64+round(min(zs),1), -by*64+round(max(zs),1)])
    rows.append(r)
    detail[f"{bx},{by}"] = dict(summary=r, components=comps)
    print(f"({bx:2d},{by:2d}) tri={len(bm.tris):5d} v={bm.vcount:5d} "
          f"x[{min(xs):7.2f},{max(xs):7.2f}] z[{min(zs):7.2f},{max(zs):7.2f}] y[{min(ys):7.2f},{max(ys):7.2f}] "
          f"comps={len(comps):3d} minComp={comps[0]['tris'] if comps else 0:4d} "
          f"idall={sorted(cnt)} topo={sorted(topo)} coastal={coastal}")

(OUT/"object_census.json").write_text(json.dumps(detail, indent=1), encoding="utf-8")
cols = ["bx","by","tris","verts","dx","dz","dy","xmin","xmax","zmin","zmax","ymin","ymax",
        "n_components","smallest_comp_tris","is_coastal","coastal_parts","idalls","topographs","events","areas",
        "umin","umax","vmin","vmax","stride","channels","submeshes","parts","terrain_topographs","worldx","worldz"]
with open(OUT/"object_census.csv","w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k:(json.dumps(v) if isinstance(v,(dict,list)) else v) for k,v in r.items() if k in cols})
print("\nwrote", OUT/"object_census.json", OUT/"object_census.csv")
print("\nPART UNIVERSE counts:", {p:len(b) for p,b in sorted(PARTS.items(), key=lambda kv:-len(kv[1]))})
