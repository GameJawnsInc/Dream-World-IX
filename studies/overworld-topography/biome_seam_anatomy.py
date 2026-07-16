"""THE BIOME SEAM ANATOMY -- what texels dress a family boundary?

The adjacency census: desert is the hub (grass|desert 193, scrub|desert 958,
desert|brush 532, desert|dunes 190) and NO boundary edge of grass|desert /
desert|dunes / desert|brush is plain-mains on both sides. This decodes the seam
vocabulary per pair: for every boundary edge, classify EACH side's tri --
its own family mains / the OTHER family's mains / scrub-mains / a residual
(clustered uv rects) -- and measure which side carries the special content.

Run from the repo root:  py studies/overworld-topography/biome_seam_anatomy.py
"""
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
FAM_OF[38] = "brush"
FAM_OF[41] = "dunes"
EPS = 0.006
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

RECTS = {}
for fam in ("grass", "scrub", "desert", "brush", "dunes"):
    m = G.FAM_REGION["main"]
    g = G.GROUNDS[fam]
    RECTS[fam] = (m[0] + g["mains_du"], m[1] + g["mains_dv"],
                  m[2] + g["mains_du"], m[3] + g["mains_dv"])
d = G.FAM_REGION["D"]
RECTS["meadowD"] = d


def uv_class(uvs):
    for name, r in RECTS.items():
        if all(r[0] - EPS <= u <= r[2] + EPS and r[1] - EPS <= v <= r[3] + EPS
               for (u, v) in uvs):
            return name
    return None


PAIRS = {("desert", "dunes"): [(18, 3), (19, 3), (19, 4), (13, 12), (14, 12), (18, 4)],
         ("grass", "desert"): [(15, 11), (14, 12), (14, 11), (15, 12)],
         ("desert", "brush"): [(15, 5), (7, 11), (13, 6)],
         ("desert", "scrub"): [(18, 5), (14, 5), (17, 5)],
         ("grass", "scrub"): [(5, 7), (16, 4), (15, 4)]}

for (fa, fb), blocks in PAIRS.items():
    side_cls = {fa: Counter(), fb: Counter()}
    resid_uv = {fa: [], fb: []}
    n_edges = 0
    for (bx, by) in blocks:
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
        edge_owner = defaultdict(list)
        for ti, (fam, w, uv) in enumerate(tris):
            ks = [kk(p) for p in w]
            for i in range(3):
                e = frozenset((ks[i], ks[(i + 1) % 3]))
                if len(e) == 2:
                    edge_owner[e].append(ti)
        for e, owners in edge_owner.items():
            fams = {tris[ti][0] for ti in owners}
            if fams != {fa, fb}:
                continue
            n_edges += 1
            for ti in owners:
                fam, _, uv = tris[ti]
                c = uv_class(uv)
                side_cls[fam][c or "RESIDUAL"] += 1
                if c is None:
                    resid_uv[fam] += uv
    print(f"\n== {fa}|{fb}: {n_edges} boundary edges over {blocks}")
    for fam in (fa, fb):
        print(f"   the {fam} side: {dict(side_cls[fam].most_common())}")
        if resid_uv[fam]:
            us = [u for u, _ in resid_uv[fam]]
            vs = [v for _, v in resid_uv[fam]]
            print(f"     residual uv bbox [{min(us):.4f},{min(vs):.4f},"
                  f"{max(us):.4f},{max(vs):.4f}]")
