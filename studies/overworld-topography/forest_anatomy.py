"""FOREST ANATOMY STUDY: (A) how real topo-37 forests sit in the terrain mesh
(boundary welds, rim heights, jitter structure, tile vocabulary, lattice), and
(B) the deployed island C block's layout (safe interior region for the build)."""
import sys
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X
from ff9mapkit.world import mesh as M

# ---- find the 3 most topo-37-rich blocks -------------------------------------
rich = []
cache = {}
for (bx, by) in X.list_blocks():
    bm = X.read_block(bx, by)
    cache[(bx, by)] = bm
    n37 = sum(1 for t in bm.tris if X.decode_id(int(bm.tangents[t[0]][0]))["topograph"] == 37)
    if n37:
        rich.append((n37, bx, by))
rich.sort(reverse=True)
print("topo-37-richest blocks:", rich[:6], flush=True)

for n37, bx, by in rich[:3]:
    bm = cache[(bx, by)]
    v = np.asarray(bm.verts, dtype=np.float64)
    uv = bm.uvs
    tan = bm.tangents
    topo_of = [X.decode_id(int(tan[t[0]][0]))["topograph"] for t in bm.tris]
    pos_key = lambda i: (round(v[i][0], 3), round(v[i][1], 3), round(v[i][2], 3))
    # positions used by forest vs non-forest tris (welded boundary = shared XYZ)
    fpos, opos = set(), set()
    for t, tri in enumerate(bm.tris):
        (fpos if topo_of[t] == 37 else opos).update(pos_key(i) for i in tri)
    shared = fpos & opos
    # rim analysis: heights of shared (boundary) verts vs interior forest verts
    inter = fpos - opos
    sh_h = [p[1] for p in shared]
    in_h = [p[1] for p in inter]
    print(f"\nblock ({bx},{by}): {n37} forest tris; boundary XYZ-shared verts {len(shared)}, "
          f"interior {len(inter)}")
    if sh_h and in_h:
        print(f"  boundary h med {np.median(sh_h):.2f}  interior h med {np.median(in_h):.2f} "
              f"(rim lift {np.median(in_h)-np.median(sh_h):+.2f})")
    # XZ lattice: fraction of forest verts on the 4u lattice
    on_lat = sum(1 for p in inter if abs(p[0] % 4) < 0.05 or abs(p[0] % 4) > 3.95)
    on_lat_z = sum(1 for p in inter if abs(p[2] % 4) < 0.05 or abs(p[2] % 4) > 3.95)
    if inter:
        print(f"  interior verts on 4u lattice: x {on_lat/len(inter):.2f} z {on_lat_z/len(inter):.2f}")
    # tile vocabulary: interior vs edge tris
    edge_tris = [t for t, tri in enumerate(bm.tris) if topo_of[t] == 37
                 and any(pos_key(i) in shared for i in tri)]
    int_tris = [t for t, tri in enumerate(bm.tris) if topo_of[t] == 37 and t not in set(edge_tris)]
    def tileset(ts):
        c = Counter()
        for t in ts:
            c[tuple(sorted((round(uv[i][0], 3), round(uv[i][1], 3)) for i in bm.tris[t]))] += 1
        return c
    ce, ci = tileset(edge_tris), tileset(int_tris)
    print(f"  edge tris {len(edge_tris)} use {len(ce)} tiles; interior tris {len(int_tris)} use {len(ci)} tiles")
    print(f"  top interior tiles: {[(k[0], n) for k, n in ci.most_common(3)]}")
    # jitter: interior vert heights relative to the local neighbourhood plane
    if in_h:
        print(f"  interior h spread p10..p90: {np.percentile(in_h,10):.2f}..{np.percentile(in_h,90):.2f}")
    # neighbouring topo of forest edges
    nb = Counter()
    for t, tri in enumerate(bm.tris):
        if topo_of[t] != 37 and any(pos_key(i) in shared for i in tri):
            nb[topo_of[t]] += 1
    print(f"  edge NEIGHBOUR topos: {dict(nb.most_common(6))}")

# ---- (B) deployed island C --------------------------------------------------
from ff9mapkit import config as _cfg
GP = str(_cfg.find_game_path(None))
p = GP + r"\FF9CustomMap-world\FF9_Data\WorldMap\Disc1\0_1\r18\Block[3][18] Terrain.ff9mesh"
bm = M.blockmesh_from_ff9mesh(p, disc=1, x=3, y=18, lod="0_1", part="terrain")
v = np.asarray(bm.verts, dtype=np.float64)
tan = bm.tangents
print(f"\nISLAND C deployed Block[3][18]: {len(bm.tris)} tris")
tc = Counter()
ev = []
for t, tri in enumerate(bm.tris):
    d = X.decode_id(int(tan[tri[0]][0]))
    tc[d["topograph"]] += 1
    if d["event"]:
        c = v[list(tri)].mean(axis=0)
        ev.append((d["event"], d["area"], round(192 + c[0], 1), round(-1152 + c[2], 1)))
print("  topo census:", dict(tc.most_common(12)))
print("  event tiles (event, area, wx, wz):", ev)
# grass interior extents (world coords) + height stats
g = [v[list(tri)].mean(axis=0) for t, tri in enumerate(bm.tris)
     if X.decode_id(int(tan[tri[0]][0]))["topograph"] == 0]
g = np.array(g)
if len(g):
    print(f"  grass tris {len(g)}: wx {192+g[:,0].min():.0f}..{192+g[:,0].max():.0f} "
          f"wz {-1152+g[:,2].max():.0f}..{-1152+g[:,2].min():.0f} h {g[:,1].min():.1f}..{g[:,1].max():.1f}")
