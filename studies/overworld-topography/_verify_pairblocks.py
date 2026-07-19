import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from collections import defaultdict
import numpy as np
from ff9mapkit.world import extract as X

BLOCK = 64.0

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


def kk(p):
    return (round(p[0], 3), round(p[1], 3), round(p[2], 3))


pair_blocks = defaultdict(set)

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
            w = [(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1], bm.verts[j][2] - BLOCK * by) for j in tri]
            tris.append(dict(fam=fam, w=w))
        edge_owner = defaultdict(list)
        for ti, t in enumerate(tris):
            ks = [kk(p) for p in t["w"]]
            for i in range(3):
                e = frozenset((ks[i], ks[(i + 1) % 3]))
                if len(e) == 2:
                    edge_owner[e].append(ti)
        for e, owners in edge_owner.items():
            fams = {tris[ti]["fam"] for ti in owners}
            if len(fams) != 2:
                continue
            pair = tuple(sorted(fams))
            pair_blocks[pair].add((bx, by))

dg = sorted(pair_blocks[("desert", "grass")])
dd = sorted(pair_blocks[("desert", "dunes")])
print("desert|grass blocks:", dg, "n=", len(dg))
print("desert|dunes blocks:", dd, "n=", len(dd))
topo16 = {(13, 11), (13, 12), (14, 11), (14, 12), (15, 11), (15, 12)}
print("topo16 rect == desert|grass block set?", topo16 == set(dg))
print("topo16 ∩ desert|dunes:", sorted(topo16 & set(dd)), "count=", len(topo16 & set(dd)))
