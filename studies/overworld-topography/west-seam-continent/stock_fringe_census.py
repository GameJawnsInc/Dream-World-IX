"""How does STOCK dress a rock-grass contact? -- the census take 8's squashed foot course is judged by.

Read-only, every disc-1 block. A CONTACT tri is a rock (topo 49) tri sharing an edge with a grass
(topo 0) tri. For each: its atlas tile, its course height (ymax - ymin), and its vertical texel density
(tile-heights per unit of height: the v span in tile units / the y span). Reports:
  - what tiles stock puts on the contact (is the fringed r10 c6-9 THE contact tile, or one of several?)
  - for fringe contacts: the course height and density distribution
  - SHORT stock contacts (course < 2.5u): what tile + density stock uses when the rock rises only a
    little -- exactly take 8's situation (its window base courses are 1.6-1.9u at 0.45-0.56 density).

    py studies/overworld-topography/west-seam-continent/stock_fringe_census.py
"""
import statistics as S
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.world import extract as X                 # noqa: E402

TU, TV, PU, PV = 0.0625, 0.03125, 0.015625, 0.01953125
ROCK, GRASS = 49, 0


def tile(uvs):
    uc = sum(u for u, v in uvs) / 3
    vc = sum(v for u, v in uvs) / 3
    return int((vc - PV) / TV), int((uc - PU) / TU)


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p / 100 * len(v)))] if v else None


def main():
    contacts = []
    for bx in range(24):
        for by in range(20):
            try:
                bm = X.read_block(bx, by, disc=1)
            except Exception:
                continue
            ids = [((int(round(t[0])) >> 2) & 0x3F) for t in bm.tangents]
            edges = defaultdict(list)
            for ti, (a, b, c) in enumerate(bm.tris):
                for i, j in ((a, b), (b, c), (c, a)):
                    k = tuple(sorted((tuple(round(x, 3) for x in bm.verts[i]),
                                      tuple(round(x, 3) for x in bm.verts[j]))))
                    edges[k].append(ti)
            grass_nb = set()
            for tl in edges.values():
                tps = {ids[bm.tris[t][0]] for t in tl}
                if ROCK in tps and GRASS in tps:
                    grass_nb.update(t for t in tl if ids[bm.tris[t][0]] == ROCK)
            for ti in grass_nb:
                a, b, c = bm.tris[ti]
                ys = [bm.verts[i][1] for i in (a, b, c)]
                uvs = [bm.uvs[i] for i in (a, b, c)]
                dy = max(ys) - min(ys)
                dv = (max(v for u, v in uvs) - min(v for u, v in uvs)) / TV
                contacts.append({"blk": (bx, by), "tile": tile(uvs), "dy": dy,
                                 "dens": dv / dy if dy > 0.3 else None})
    print(f"stock rock-grass contact tris: {len(contacts)}")
    tc = Counter(f"r{c['tile'][0]}c{c['tile'][1]}" for c in contacts)
    print("contact tiles:", tc.most_common(14))
    fr = [c for c in contacts if c["tile"][0] == 10 and 6 <= c["tile"][1] <= 9]
    print(f"\nfringe r10 c6-9 contacts: {len(fr)} ({100 * len(fr) / max(1, len(contacts)):.0f}%)")
    h = [c["dy"] for c in fr]
    d = [c["dens"] for c in fr if c["dens"] is not None]
    print(f"  course height p10 {pct(h, 10):.2f} p50 {pct(h, 50):.2f} p90 {pct(h, 90):.2f}")
    print(f"  density (tile-heights / u) p10 {pct(d, 10):.2f} p50 {pct(d, 50):.2f} p90 {pct(d, 90):.2f}")
    short = [c for c in contacts if 0.3 < c["dy"] < 2.5]
    print(f"\nSHORT contacts (course < 2.5u): {len(short)}")
    print("  tiles:", Counter(f"r{c['tile'][0]}c{c['tile'][1]}" for c in short).most_common(10))
    sf = [c["dens"] for c in short if c["tile"][0] == 10 and 6 <= c["tile"][1] <= 9 and c["dens"]]
    if sf:
        print(f"  fringe-tile density on short courses: p10 {pct(sf, 10):.2f} p50 {pct(sf, 50):.2f} "
              f"p90 {pct(sf, 90):.2f} (n={len(sf)})")
    over = [x for x in d if x >= 0.45]
    print(f"\nstock fringe contacts at take 8's window density (>= 0.45): {len(over)} of {len(d)} "
          f"({100 * len(over) / max(1, len(d)):.1f}%)")


if __name__ == "__main__":
    main()
