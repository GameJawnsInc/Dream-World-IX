"""LAND -> SEA with shallows, question 2 (2026-10-09): what water does each small island stand in? A plan plot per
island (terrain, beach1 and every sea band coloured by part, the 4u lattice drawn), and per island the parts its LAND
shares a vertex with (the band it meets) plus the parts on the ring of tiles round its footprint.
Reads stock only. Writes out/sh_q2_<bx>_<by>.png and out/sh_q2_touch_d<disc>.json.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sh_q2_plot.py [disc]
"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))
COL = {"terrain": "#6b8e23", "beach1": "#e8d28a", "sea1": "#7fe0d0", "sea2": "#b8f0ff", "sea3": "#3fa0c8",
       "sea5": "#2060a0", "sea4": "#0a2a60", "object": "#c03030"}
PARTS = ("sea4", "sea5", "sea3", "sea1", "sea2", "beach1", "terrain", "object")


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    import ff9mapkit
    from ff9mapkit.world import discmirror as DM, transplant as TR
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    disc = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    real = DM._real_parts(disc, "0_1")
    q1 = json.loads((HERE / "out" / f"sh_q1_halos_d{disc}.json").read_text(encoding="utf-8"))
    cache = {}

    def tris(b, p):
        if (b, p) not in cache:
            cache[(b, p)] = TR.world_tris(*b, p, disc=disc) if p in real.get(tuple(b), ()) else []
        return cache[(b, p)]

    out = {}
    for r in q1["rows"]:
        if r.get("continent") or len(r["blocks"]) > 9:
            continue
        blocks = [tuple(b) for b in r["blocks"]]
        near = sorted({(b[0] + dx, b[1] + dy) for b in blocks for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                       if (b[0] + dx, b[1] + dy) in real})
        # this component's land: re-find it by vertex keys of its blocks' land joined to the q1 component's at-point
        from ff9mapkit.world import meshedit as ME
        land_all = [t for b in near for p in ("terrain", "beach1") for t in tris(b, p)]
        comps = ME.vertex_components(land_all)
        want = r["land_tris"]
        cands = [c for c in comps if len(c) == want and {(math.floor(v[0][0] / 64), math.floor(-v[0][2] / 64))
                                                          for t in c for v in t} <= set(near)]
        if not cands:
            continue
        land = cands[0]
        lk = {(round(v[0][0], 4), round(v[0][2], 4)) for t in land for v in t}
        touch = Counter()
        for b in near:
            for p in PARTS[:5]:
                for t in tris(b, p):
                    if any((round(v[0][0], 4), round(v[0][2], 4)) in lk for v in t):
                        touch[p] += 1
        foot = set()
        for t in land:
            foot |= TR._tiles_touched(t)
        ring = {(i + di, j + dj) for (i, j) in foot for di in (-1, 0, 1) for dj in (-1, 0, 1)} - foot
        ringp = Counter()
        for ij in ring:
            c = (ij[0] * 4 + 2.0, ij[1] * 4 + 2.0)
            b = (int(math.floor(c[0] / 64)), int(math.floor(-c[1] / 64)))
            hit = [p for p in PARTS if any(TR._tri_has(t, c) for t in tris(b, p))]
            ringp["+".join(hit) or "none"] += 1
        key = f"{blocks[0][0]},{blocks[0][1]}"
        out[f"c{r['comp']} {key}"] = {"land_u2": r["land_u2"], "land_touches": dict(touch),
                                      "ring_tiles": dict(ringp), "foot_tiles": len(foot)}
        print(f"c{r['comp']:3d} {key:7s} {r['land_u2']:8.1f}u2 land meets {dict(touch)}  ring {dict(ringp)}")
        xs = [v[0][0] for t in land for v in t]
        zs = [v[0][2] for t in land for v in t]
        pad = 40
        x0, x1, z0, z1 = min(xs) - pad, max(xs) + pad, min(zs) - pad, max(zs) + pad
        fig, ax = plt.subplots(figsize=(8, 8 * (z1 - z0) / max(x1 - x0, 1)))
        for p in PARTS:
            polys = [[(v[0][0], v[0][2]) for v in t] for b in near for t in tris(b, p)
                     if any(x0 <= v[0][0] <= x1 and z0 <= v[0][2] <= z1 for v in t)]
            if polys:
                ax.add_collection(PolyCollection(polys, facecolors=COL[p], edgecolors="k", linewidths=0.15,
                                                 alpha=0.9, label=p))
        for gx in range(int(x0 // 4) * 4, int(x1) + 4, 4):
            ax.axvline(gx, color="w", lw=0.2, alpha=0.4)
        for gz in range(int(z0 // 4) * 4, int(z1) + 4, 4):
            ax.axhline(gz, color="w", lw=0.2, alpha=0.4)
        ax.set_xlim(x0, x1)
        ax.set_ylim(z0, z1)
        ax.set_aspect("equal")
        ax.set_title(f"c{r['comp']} block {key}  {r['land_u2']}u2  meets {dict(touch)}", fontsize=8)
        ax.legend(fontsize=6, loc="upper right")
        fig.savefig(HERE / "out" / f"sh_q2_{blocks[0][0]}_{blocks[0][1]}_c{r['comp']}.png", dpi=110)
        plt.close(fig)
    (HERE / "out" / f"sh_q2_touch_d{disc}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
