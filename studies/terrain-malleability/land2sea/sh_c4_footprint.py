"""ISLAND CLUSTERS, question 4 (2026-10-09): THE FOOTPRINT FILL -- sink one island of a cluster by replacing only its
LAND with water, keeping every water tri round it.

The whole-tile sink re-tiles every tile the island touches, so it must take the coast-conforming water round it, and
where that water also conforms to another coast it runs into it. Here nothing but the island's land goes: its plan
footprint, cut cell by cell (sh_c3's convex tri-cell pieces, merged by edge cancellation), becomes water. The water
round it stays, so a neighbouring islet's coast is never touched. Where a 4u lattice line crosses the old coastline,
the kept water tri on it is split at the crossing (same plane, same affine uv), so the fill meets it vertex to vertex.
Per site: the coastline (the land's boundary edges: their heights, what is on their other side), whole and partial
cells, failures, kept water overlapping the footprint, the kept water tris to split, and coverage samples. Renders
stock, the footprint fill (orange) over the kept tris, and disc 4 for Shimmering.
Writes out/sh_c4_footprint.json and out/sh_c4_<x>_<z>.png.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sh_c4_footprint.py X Z [X Z ...]
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
import sh_c3_cellfill as C3  # noqa: E402
import sh_q6_render as Q6  # noqa: E402

LAND = ("terrain", "beach1")
WATER = ("sea1", "sea2", "sea3", "sea5", "sea4")
PARTS = ("terrain", "beach1", "sea1", "sea2", "sea3", "sea5", "sea4", "object")


def k3(v):
    return (round(v[0][0], 4), round(v[0][1], 4), round(v[0][2], 4))


def site(at, res_all):
    from ff9mapkit.world import discmirror as DM, meshedit as ME, render as R, transplant as TR
    real = DM._real_parts(1, "0_1")
    home = (int(math.floor(at[0] / 64.0)), int(math.floor(-at[1] / 64.0)))
    blocks = sorted({(home[0] + dx, home[1] + dy) for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)}
                    & set(real))
    tris = {(b, p): TR.world_tris(*b, p, disc=1) if p in real[b] else [] for b in blocks for p in PARTS}
    land_all = [t for b in blocks for p in LAND for t in tris[(b, p)]]
    island = next(c for c in ME.vertex_components(land_all) if any(TR._tri_has(t, at) for t in c))
    iid = {id(t) for t in island}
    # the coastline: the island's boundary edges
    ec = Counter()
    for t in island:
        ks = [k3(v) for v in t]
        for i in range(3):
            a, b = ks[i], ks[(i + 1) % 3]
            if a != b:
                ec[tuple(sorted((a, b)))] += 1
    coast = [e for e, n in ec.items() if n == 1]
    cy = Counter(round(v[1], 3) for e in coast for v in e)
    other = defaultdict(set)
    for b in blocks:
        for p in PARTS:
            for t in tris[(b, p)]:
                if id(t) in iid:
                    continue
                ks = [k3(v) for v in t]
                for i in range(3):
                    other[tuple(sorted((ks[i], ks[(i + 1) % 3])))].add(p)
    across = Counter("+".join(sorted(other.get(e, {"NOTHING"}))) for e in coast)
    # the footprint, cell by cell
    by_cell = defaultdict(list)
    for t in island:
        P = [(v[0][0], v[0][2]) for v in t]
        for ij in TR._tiles_touched(t):
            pc = C3.tri_cell_piece(P, *ij)
            if pc:
                by_cell[ij].append(pc)
    whole = partial = fail = 0
    fill = []
    for ij, pcs in sorted(by_cell.items()):
        loops = C3.cell_loops(pcs)
        if loops is None:
            fail += 1
            continue
        sq = {C3.kp((4.0 * ij[0] + dx, 4.0 * ij[1] + dz)) for dx in (0, 4) for dz in (0, 4)}
        if len(loops) == 1 and {C3.kp(p) for p in loops[0]} <= sq | {C3.kp(p) for p in loops[0]
                                                                       if _on_border(p, ij)} and _full(loops[0], ij):
            whole += 1
        else:
            partial += 1
        for lp in loops:
            area = 0.5 * sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(lp, lp[1:] + lp[:1]))
            if area < 0:
                fail += 1
                continue
            try:
                for t in ME.earclip(lp, quality=True):
                    fill.append([((p[0], 0.0, p[1]), (0, 1, 0), (0, 0), (0, 0, 0, 1)) for p in t])
            except ValueError:
                fail += 1
    # kept water over the footprint (sea under land: stock has none), and the kept water tris on the coastline that a
    # lattice line crosses (to split)
    kept_w = [(p, t) for b in blocks for p in WATER for t in tris[(b, p)]]
    over_area = 0.0
    for p, t in kept_w:
        P = [(v[0][0], v[0][2]) for v in t]
        for ij in TR._tiles_touched(t):
            for pc in by_cell.get(ij, ()):
                over_area += _convex_overlap(P, pc)
    cset = set(coast)
    to_split = 0
    for p, t in kept_w:
        ks = [k3(v) for v in t]
        for i in range(3):
            e = tuple(sorted((ks[i], ks[(i + 1) % 3])))
            if e in cset and _crosses_lattice(e):
                to_split += 1
                break
    fill_area = sum(TR._plan_clip_area([(v[0][0], v[0][2]) for v in t], -1e9, 1e9, -1e9, 1e9) for t in fill)
    piece_area = sum(0.5 * abs(sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pc, pc[1:] + pc[:1])))
                     for pcs in by_cell.values() for pc in pcs)
    out = {"at": at, "island_tris": len(island), "coast_edges": len(coast), "coast_y": dict(cy.most_common(5)),
           "coast_across": dict(across), "cells": len(by_cell), "whole": whole, "partial": partial, "failed": fail,
           "piece_area": round(piece_area, 1), "fill_area": round(fill_area, 1), "fill_tris": len(fill),
           "kept_water_over_footprint_u2": round(over_area, 3), "kept_water_tris_to_split": to_split}
    res_all[f"{at[0]},{at[1]}"] = out
    print(json.dumps(out))
    rs = R.RenderSite(cells=((0, 0),), disc=1)
    names = {"sea4": "Sea4", "sea5": "Sea5", "sea3": "Sea3", "sea1": "Sea1", "sea2": "Sea2", "beach1": "Beach1",
             "terrain": "Terrain", "object": "Object"}
    tex = {p: R.tex_for(n, rs) for p, n in names.items()}
    stock = {p: [t for b in blocks for t in tris[(b, p)]] for p in PARTS}
    after = {p: [t for t in ts if id(t) not in iid] for p, ts in stock.items()}
    xs = [v[0][0] for t in island for v in t]
    zs = [v[0][2] for t in island for v in t]
    box = (min(xs) - 24, max(xs) + 24, min(zs) - 24, max(zs) + 24)
    i0, _ = Q6.raster(stock, box, tex)
    i1, _ = Q6.raster(after, box, tex)
    _, fb = Q6.raster({"sea3": fill}, box, {})
    i1[fb.sum(2) > 0] = (230, 120, 40)
    panels = [i0, i1]
    if at == (441.992, -311.975):
        r4 = DM._real_parts(4, "0_1")
        d4 = {p: [t for b in blocks for t in (TR.world_tris(*b, p, disc=4) if p in r4.get(b, ()) else [])]
              for p in PARTS}
        panels.append(Q6.raster(d4, box, tex)[0])
    H, W = i0.shape[:2]
    canvas = Image.new("RGB", (len(panels) * (W + 10), H), (255, 255, 255))
    for k, im in enumerate(panels):
        canvas.paste(Image.fromarray(im), (k * (W + 10), 0))
    canvas.save(HERE / "out" / f"sh_c4_{int(at[0])}_{int(-at[1])}.png")


def _on_border(p, ij):
    x0, z0 = 4.0 * ij[0], 4.0 * ij[1]
    return (abs(p[0] - x0) < 1e-6 or abs(p[0] - x0 - 4) < 1e-6) or (abs(p[1] - z0) < 1e-6 or abs(p[1] - z0 - 4) < 1e-6)


def _full(lp, ij):
    area = 0.5 * sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(lp, lp[1:] + lp[:1]))
    return abs(area - 16.0) < 1e-6 and all(_on_border(p, ij) for p in lp)


def _crosses_lattice(e):
    (ax, _ay, az), (bx, _by, bz) = e
    return math.floor(ax / 4) != math.floor(bx / 4 - 1e-9 * (bx < ax)) or math.floor(az / 4) != math.floor(bz / 4)


def _convex_overlap(tri, poly):
    """Plan area of triangle ``tri`` clipped to the convex polygon ``poly`` (CCW)."""
    out = list(tri)
    n = len(poly)
    for k in range(n):
        a, b = poly[k], poly[(k + 1) % n]
        inp, out = out, []
        if not inp:
            break
        for m in range(len(inp)):
            p, q = inp[m], inp[(m + 1) % len(inp)]
            sp = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
            sq = (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0])
            if sp >= 0:
                out.append(p)
            if (sp >= 0) != (sq >= 0):
                t = sp / (sp - sq)
                out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    if len(out) < 3:
        return 0.0
    return max(0.0, 0.5 * sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(out, out[1:] + out[:1])) - 1e-6)


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    a = [float(v) for v in sys.argv[1:]]
    res = {}
    for k in range(0, len(a), 2):
        site((a[k], a[k + 1]), res)
    (HERE / "out" / "sh_c4_footprint.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
