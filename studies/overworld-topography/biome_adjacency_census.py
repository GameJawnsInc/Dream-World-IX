"""THE BIOME-ADJACENCY CENSUS -- which ground families touch in stock, and how?

The mixed-biome landmass rung (2026-07-15): dunes/scrub/brush are interior/seam/slope
vocabularies meant to live INSIDE a landmass behind a lawful coast. Before composing
one, measure the composition grammar the game itself uses:

  A. map-wide shared-edge counts for every walkable-family pair (which families are
     EVER adjacent; a pair with zero edges is off-language by construction);
  B. per-pair boundary anatomy on the top blocks: the uv class on each side of the
     shared edge (family mains vs other), the y-step across it (flat weld vs slope),
     and whether the boundary follows lattice lines;
  C. the patch form for the interior families (dunes): patch sizes (connected
     components), what surrounds them, block examples to eyeball in-game.

Run from the repo root:  py studies/overworld-topography/biome_adjacency_census.py
"""
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402

FAM_OF = {}
for t in (0, 1, 2, 3, 10, 11, 12, 13, 42):
    FAM_OF[t] = "grass"
for t in (4, 5, 6):
    FAM_OF[t] = "scrub"
for t in (17, 16, 19, 20):
    FAM_OF[t] = "desert"
for t in (27, 28):
    FAM_OF[t] = "snow"
FAM_OF[38] = "brush"
FAM_OF[41] = "dunes"
FAM_OF[45] = FAM_OF[46] = "canyon"
EPS = 0.006


def mains_rect(fam):
    m = G.FAM_REGION["main"]
    g = G.GROUNDS[fam]
    return (m[0] + g["mains_du"], m[1] + g["mains_dv"],
            m[2] + g["mains_du"], m[3] + g["mains_dv"])


def in_rect(uv, r):
    return r[0] - EPS <= uv[0] <= r[2] + EPS and r[1] - EPS <= uv[1] <= r[3] + EPS


kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

pair_edges = Counter()
pair_blocks = defaultdict(Counter)
pair_detail = defaultdict(lambda: dict(mains_both=0, lattice=0, n=0, ystep=[]))
dunes_patches = []

for bx in range(24):
    for by in range(20):
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            continue
        tris = []
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            fam = FAM_OF.get(topo)
            if fam is None:
                continue
            w = [(bm.verts[j][0] + 64.0 * bx, bm.verts[j][1], bm.verts[j][2] - 64.0 * by)
                 for j in tri]
            uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
            tris.append((fam, w, uv))
        edge_owner = {}
        for ti, (fam, w, uv) in enumerate(tris):
            ks = [kk(p) for p in w]
            for i in range(3):
                e = frozenset((ks[i], ks[(i + 1) % 3]))
                if len(e) < 2:
                    continue
                edge_owner.setdefault(e, []).append(ti)
        for e, owners in edge_owner.items():
            fams = {tris[ti][0] for ti in owners}
            if len(fams) != 2:
                continue
            pair = tuple(sorted(fams))
            pair_edges[pair] += 1
            pair_blocks[pair][(bx, by)] += 1
            d = pair_detail[pair]
            d["n"] += 1
            both_mains = all(
                all(in_rect(u, mains_rect(tris[ti][0])) for u in tris[ti][2])
                for ti in owners)
            d["mains_both"] += both_mains
            (a, b) = sorted(e)
            if (abs(a[0] - b[0]) < 1e-6 and abs(a[0] / 4 - round(a[0] / 4)) < 1e-3) or \
               (abs(a[2] - b[2]) < 1e-6 and abs(a[2] / 4 - round(a[2] / 4)) < 1e-3):
                d["lattice"] += 1
            d["ystep"].append(abs(a[1] - b[1]))
        # dunes patch inventory (connected dunes components + their neighbours)
        dun = [ti for ti, t in enumerate(tris) if t[0] == "dunes"]
        if dun:
            parent = {}

            def find(x):
                while parent.setdefault(x, x) != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x

            vert_of = defaultdict(list)
            for ti in dun:
                for p in tris[ti][1]:
                    vert_of[kk(p)].append(ti)
            for tl in vert_of.values():
                for t2 in tl[1:]:
                    parent[find(tl[0])] = find(t2)
            comps = defaultdict(list)
            for ti in dun:
                comps[find(ti)].append(ti)
            for tl in comps.values():
                xs = [p[0] for ti in tl for p in tris[ti][1]]
                zs = [p[2] for ti in tl for p in tris[ti][1]]
                nb = Counter()
                keys = {kk(p) for ti in tl for p in tris[ti][1]}
                for ti, (fam, w, uv) in enumerate(tris):
                    if fam != "dunes" and any(kk(p) in keys for p in w):
                        nb[fam] += 1
                dunes_patches.append(dict(block=(bx, by), tris=len(tl),
                                          w=round(max(xs) - min(xs), 1),
                                          h=round(max(zs) - min(zs), 1),
                                          neighbours=dict(nb)))

print("== A. family-pair shared edges (map-wide; zero = the pair NEVER touches)")
fams = ["grass", "scrub", "desert", "snow", "brush", "dunes", "canyon"]
for i, f1 in enumerate(fams):
    for f2 in fams[i + 1:]:
        n = pair_edges.get((f1, f2), 0) + pair_edges.get((f2, f1), 0)
        if n:
            top = pair_blocks[tuple(sorted((f1, f2)))].most_common(3)
            d = pair_detail[tuple(sorted((f1, f2)))]
            ys = sorted(d["ystep"])
            print(f"   {f1:7s}|{f2:7s} {n:5d} edges  blocks {top}  "
                  f"mains-both {d['mains_both']}/{d['n']}  lattice {d['lattice']}/{d['n']}  "
                  f"ystep p50 {ys[len(ys)//2]:.2f} max {ys[-1]:.2f}")
        else:
            print(f"   {f1:7s}|{f2:7s}     0 edges  -- NEVER touch")

print("\n== C. dunes patch inventory (per-block connected components)")
for p in sorted(dunes_patches, key=lambda q: -q["tris"])[:12]:
    print(f"   {p['block']}: {p['tris']:3d} tris  {p['w']}x{p['h']}u  "
          f"neighbours {p['neighbours']}")
