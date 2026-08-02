"""C1 SKEPTIC addendum: the cross-tabs the first pass did not aggregate.

  * ROCK/COAST sloped-vs-degenerate cross-tab (claimed: rock sloped 199/212, coast 536/564);
  * ROCK/COAST tile histograms (claimed: rock cols 0-3 rows 10/11/18; coast rows 27-28);
  * curtain (OTHER, degf>=0.9) components vert-adjacent to coastal/sea topo (claimed: exactly 2);
  * sloped OTHER comps in the 62 family: full non-NV neighbor topo histogram (claimed x62|x62);
  * curtain above=49 under a per-plan-key-max-only top attribution (claimed rock-49 above 10).

Writes out/curtain_skeptic_recheck2.json.
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

KIT = r"C:\gd\Dream-World-IX\.claude\worktrees\angry-williamson-08e8bb\ff9mapkit"
sys.path.insert(0, KIT)
from ff9mapkit.world import extract as X  # noqa: E402

TILE_U, TILE_V = 0.0625, 0.03125
COASTAL = {53, 54, 55, 56, 57, 58}


def q2(v):
    return int(round(v * 100))


class UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        p = self.p
        while p.setdefault(a, a) != a:
            p[a] = p[p[a]]
            a = p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def main():
    rock_degf, coast_degf = [], []
    rock_tiles, coast_tiles = Counter(), Counter()
    curtain_coastal = []
    sloped62 = []
    curtain_top49 = []
    for (bx, by) in X.list_blocks(disc=1):
        bm = X.read_block(bx, by, disc=1, part="terrain")
        verts, fi, tans, uvs = bm.verts, bm.flat_index, bm.tangents, bm.uvs
        ntri = len(fi) // 3
        topo, absny, deg, tile, corners = [0] * ntri, [1.0] * ntri, [False] * ntri, [None] * ntri, [None] * ntri
        for t in range(ntri):
            i0, i1, i2 = fi[3 * t], fi[3 * t + 1], fi[3 * t + 2]
            v0, v1, v2 = verts[i0], verts[i1], verts[i2]
            e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
            e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
            nx = e1[1] * e2[2] - e1[2] * e2[1]
            ny = e1[2] * e2[0] - e1[0] * e2[2]
            nz = e1[0] * e2[1] - e1[1] * e2[0]
            ln = math.sqrt(nx * nx + ny * ny + nz * nz)
            absny[t] = abs(ny) / ln if ln > 1e-12 else 1.0
            pa = 0.5 * abs(e1[0] * e2[2] - e1[2] * e2[0])
            deg[t] = (absny[t] <= 0.05) or (pa < 0.01)
            topo[t] = X.decode_id(int(round(tans[i0][0])))["topograph"]
            umin = min(uvs[i0][0], uvs[i1][0], uvs[i2][0])
            vmin = min(uvs[i0][1], uvs[i1][1], uvs[i2][1])
            tile[t] = (math.floor(umin / TILE_U + 1e-9), math.floor(vmin / TILE_V + 1e-9))
            corners[t] = (i0, i1, i2)
        nv = [t for t in range(ntri) if absny[t] <= 0.2]
        if not nv:
            continue
        pos_key = {}
        for t in range(ntri):
            for i in corners[t]:
                if i not in pos_key:
                    v = verts[i]
                    pos_key[i] = (q2(v[0]), q2(v[1]), q2(v[2]))
        nv_set = set(nv)
        vert_nonnv = defaultdict(list)
        for t in range(ntri):
            if t in nv_set:
                continue
            for i in corners[t]:
                vert_nonnv[pos_key[i]].append(t)
        edge_map = defaultdict(list)
        for t in nv:
            i0, i1, i2 = corners[t]
            for a, b in ((i0, i1), (i1, i2), (i2, i0)):
                ka, kb = pos_key[a], pos_key[b]
                edge_map[(min(ka, kb), max(ka, kb))].append(t)
        uf = UF()
        for ts in edge_map.values():
            for t in ts[1:]:
                uf.union(ts[0], t)
        groups = defaultdict(list)
        for t in nv:
            groups[uf.find(t)].append(t)
        for ts in groups.values():
            ys = [verts[i][1] for t in ts for i in corners[t]]
            if max(ys) - min(ys) < 1.0:
                continue
            th = Counter(topo[t] for t in ts)
            n = len(ts)
            rock_share = (th.get(49, 0) + th.get(50, 0)) / n
            coast_share = th.get(58, 0) / n
            degf = sum(1 for t in ts if deg[t]) / n
            vset = {pos_key[i] for t in ts for i in corners[t]}
            if rock_share >= 0.5:
                rock_degf.append(degf)
                rock_tiles.update(tile[t] for t in ts)
                continue
            if coast_share >= 0.5:
                coast_degf.append(degf)
                coast_tiles.update(tile[t] for t in ts)
                continue
            # OTHER
            cx = sum(verts[i][0] for t in ts for i in corners[t]) / (3 * n) + bx * 64
            cy = sum(ys) / len(ys)
            cz = sum(verts[i][2] for t in ts for i in corners[t]) / (3 * n) - by * 64
            nb_hist = Counter()
            for vk in vset:
                for t2 in vert_nonnv.get(vk, ()):
                    nb_hist[topo[t2]] += 1
            if degf >= 0.9:
                if any(k in COASTAL for k in nb_hist):
                    curtain_coastal.append({
                        "block": (bx, by), "ntri": n, "drop": round(max(ys) - min(ys), 2),
                        "at": [round(cx, 1), round(cy, 1), round(cz, 1)],
                        "coastal_nb": {str(k): v for k, v in nb_hist.items() if k in COASTAL},
                    })
                # alternative top attribution: per-plan-key max only (no comp-mid fallback)
                by_plan = defaultdict(list)
                for (kx, ky, kz) in vset:
                    by_plan[(kx, kz)].append(ky)
                topc = Counter()
                for (kx, kz), kys in by_plan.items():
                    kmax = max(kys)
                    if kmax - min(kys) >= 30:
                        for t2 in vert_nonnv.get((kx, kmax, kz), ()):
                            topc[topo[t2]] += 1
                if topc and topc.most_common(1)[0][0] == 49:
                    curtain_top49.append({"block": (bx, by), "ntri": n,
                                          "at": [round(cx, 1), round(cy, 1), round(cz, 1)],
                                          "top_nb": dict(topc)})
                if 49 in topc and topc.most_common(1)[0][0] != 49:
                    curtain_top49.append({"block": (bx, by), "ntri": n, "weak": True,
                                          "at": [round(cx, 1), round(cy, 1), round(cz, 1)],
                                          "top_nb": dict(topc)})
            elif degf <= 0.1 and 62 in nb_hist:
                sloped62.append({"block": (bx, by), "ntri": n,
                                 "at": [round(cx, 1), round(cy, 1), round(cz, 1)],
                                 "nb_hist": {str(k): v for k, v in nb_hist.most_common()},
                                 "own_hist": {str(k): v for k, v in th.items()}})

    out = {
        "rock": {"comps": len(rock_degf),
                 "sloped_le0.1": sum(1 for d in rock_degf if d <= 0.1),
                 "not_fully_deg": sum(1 for d in rock_degf if d < 0.9),
                 "tiles_top10": [(str(k), v) for k, v in rock_tiles.most_common(10)]},
        "coast": {"comps": len(coast_degf),
                  "sloped_le0.1": sum(1 for d in coast_degf if d <= 0.1),
                  "not_fully_deg": sum(1 for d in coast_degf if d < 0.9),
                  "tiles_top10": [(str(k), v) for k, v in coast_tiles.most_common(10)]},
        "curtain_coastal_adjacent": curtain_coastal,
        "curtain_top49": curtain_top49,
        "sloped_62_family": sloped62,
    }
    od = Path(__file__).resolve().parent / "out"
    (od / "curtain_skeptic_recheck2.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
