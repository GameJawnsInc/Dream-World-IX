"""ISLAND CLUSTERS, question 2 (2026-10-09): can a sink take one island of a cluster and keep the rest, the way disc 4
took Shimmering's main island and kept its islets?

The whole-tile sink re-tiles every 4u tile the island touches, closed over the coast-conforming water round it; where
that water also conforms to another coast, the closure runs into it and the sink refuses. THE HOLE FILL instead drops the
island, its beach water and every water tri that covers one of its tiles (whole, even where it reaches past them), and
fills the exact hole those leave: its outline runs along kept edges only (kept water, the kept islets' coastlines), and
`meshedit.lattice_patch` fills it clipped to each 4u cell, reusing every outline vertex.
For each site: the hole's outline loops, their vertex heights (water welds only at y 0), what the outline runs along
(kept water, kept land, the map edge), the hole's cells (whole or partial, and the kept band in a partial one), and the
fill's coverage (plan area and samples). Renders stock, the fill (bands coloured) and, for Shimmering, disc 4.
Writes out/sh_c2_hole.json and out/sh_c2_<x>_<z>.png.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sh_c2_hole.py X Z [X Z ...]
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(HERE))
import sh_q6_render as Q6  # noqa: E402

LAND = ("terrain", "beach1")
BAND = ("sea3", "sea5", "sea4")
PARTS = ("terrain", "beach1", "sea1", "sea2", "sea3", "sea5", "sea4", "object")


def k3(v):
    return (round(v[0][0], 4), round(v[0][1], 4), round(v[0][2], 4))


def site(at, res_all):
    from ff9mapkit.world import discmirror as DM, meshedit as ME, transplant as TR
    real = DM._real_parts(1, "0_1")
    home = (int(math.floor(at[0] / 64.0)), int(math.floor(-at[1] / 64.0)))
    blocks = sorted({(home[0] + dx, home[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)} & set(real))
    tris = {(b, p): TR.world_tris(*b, p, disc=1) if p in real[b] else [] for b in blocks for p in PARTS}
    land_all = [t for b in blocks for p in LAND for t in tris[(b, p)]]
    island = next(c for c in ME.vertex_components(land_all) if any(TR._tri_has(t, at) for t in c))
    iid = {id(t) for t in island}
    region = set()
    for t in island:
        region |= TR._tiles_touched(t)
    drop = list(island)
    for b in blocks:
        for p in BAND:
            for t in tris[(b, p)]:
                if TR._tiles_touched(t) & region:
                    drop.append(t)
    did = {id(t) for t in drop}
    # the outline: D's edges used once (3D keys)
    ec = Counter()
    for t in drop:
        ks = [k3(v) for v in t]
        for i in range(3):
            a, b = ks[i], ks[(i + 1) % 3]
            if a != b:
                ec[tuple(sorted((a, b)))] += 1
    bnd = [e for e, n in ec.items() if n == 1]
    # what each outline edge runs along: an edge of a kept tri of which part
    kept_edges = defaultdict(set)
    for b in blocks:
        for p in PARTS:
            for t in tris[(b, p)]:
                if id(t) in did:
                    continue
                ks = [k3(v) for v in t]
                for i in range(3):
                    kept_edges[tuple(sorted((ks[i], ks[(i + 1) % 3])))].add(p)
    along = Counter("+".join(sorted(kept_edges.get(e, {"NOTHING"}))) for e in bnd)
    ys = Counter(round(v[1], 3) for e in bnd for v in e)
    # loops
    adj = defaultdict(list)
    for a, b in bnd:
        adj[a].append(b)
        adj[b].append(a)
    odd = sum(1 for v, n in adj.items() if len(n) != 2)
    loops, used = [], set()
    for start in list(adj):
        if start in used or len(adj[start]) != 2:
            continue
        loop, prev, cur = [start], None, start
        used.add(start)
        while True:
            nxt = [w for w in adj[cur] if w != prev]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            if cur == start:
                break
            if cur in used:
                break
            used.add(cur)
            loop.append(cur)
        loops.append(loop)
    area = [0.5 * (sum(a[0] * b[2] - b[0] * a[2] for a, b in zip(lp, lp[1:] + lp[:1]))) for lp in loops]
    drop_area = sum(TR._plan_clip_area([(v[0][0], v[0][2]) for v in t], -1e9, 1e9, -1e9, 1e9) for t in drop
                    if all(abs(v[0][1]) < 1e-6 for v in t))
    # fill each loop
    fill, fail = [], []
    for li, lp in enumerate(loops):
        ring = [(v[0], 0.0, v[2]) for v in lp]
        try:
            fill += ME.lattice_patch(ring, y=0.0, uv_quads=((0.0, 0.0, 1.0, 1.0),), idall=0)
        except ValueError as e:
            fail.append((li, len(lp), round(area[li], 1), str(e)[:60]))
    fill_area = sum(TR._plan_clip_area([(v[0][0], v[0][2]) for v in t], -1e9, 1e9, -1e9, 1e9) for t in fill)
    cells = Counter()
    for t in fill:
        c = TR._plan_centroid(t)
        cells[(math.floor(c[0] / 4), math.floor(c[1] / 4))] += 1
    kept_in = defaultdict(set)
    for b in blocks:
        for p in PARTS:
            for t in tris[(b, p)]:
                if id(t) in did:
                    continue
                for ij in TR._tiles_touched(t):
                    if ij in cells:
                        kept_in[ij].add(p)
    partial = Counter("+".join(sorted(kept_in[ij])) for ij in cells if kept_in.get(ij))
    out = {"at": at, "island_tris": len(island), "dropped": len(drop), "outline_edges": len(bnd),
           "outline_runs_along": dict(along), "outline_y": dict(ys.most_common(6)), "branch_vertices": odd,
           "loops": [len(lp) for lp in loops], "loop_areas": [round(a, 1) for a in area],
           "dropped_water_plan_area": round(drop_area, 1), "fill_tris": len(fill), "fill_area": round(fill_area, 1),
           "cells": len(cells), "partial_cells_kept": dict(partial), "fill_failed_loops": fail}
    res_all[f"{at[0]},{at[1]}"] = out
    print(json.dumps(out))
    # render: stock | fill (bands coloured; kept tris textured)
    from ff9mapkit.world import render as R
    rs = R.RenderSite(cells=((0, 0),), disc=1)
    names = {"sea4": "Sea4", "sea5": "Sea5", "sea3": "Sea3", "sea1": "Sea1", "sea2": "Sea2", "beach1": "Beach1",
             "terrain": "Terrain", "object": "Object"}
    tex = {p: R.tex_for(n, rs) for p, n in names.items()}
    stock = {p: [t for b in blocks for t in tris[(b, p)]] for p in PARTS}
    after = {p: [t for t in ts if id(t) not in did] for p, ts in stock.items()}
    xs = [v[0] for lp in loops for v in lp]
    zs = [v[2] for lp in loops for v in lp]
    box = (min(xs) - 16, max(xs) + 16, min(zs) - 16, max(zs) + 16)
    i0, _ = Q6.raster(stock, box, tex)
    i1, _ = Q6.raster(after, box, tex)
    _, fb = Q6.raster({"sea3": fill}, box, {})
    i1[fb.sum(2) > 0] = (230, 120, 40)
    panels = [i0, i1]
    if at == (441.992, -311.975):
        d4 = {p: [t for b in blocks for t in (TR.world_tris(*b, p, disc=4) if p in DM._real_parts(4, "0_1").get(b, ())
                                              else [])] for p in PARTS}
        panels.append(Q6.raster(d4, box, tex)[0])
    H, W = i0.shape[:2]
    canvas = Image.new("RGB", (len(panels) * (W + 10), H), (255, 255, 255))
    for k, im in enumerate(panels):
        canvas.paste(Image.fromarray(im), (k * (W + 10), 0))
    canvas.save(HERE / "out" / f"sh_c2_{int(at[0])}_{int(-at[1])}.png")


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    a = [float(v) for v in sys.argv[1:]]
    res = {}
    for k in range(0, len(a), 2):
        site((a[k], a[k + 1]), res)
    (HERE / "out" / "sh_c2_hole.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
