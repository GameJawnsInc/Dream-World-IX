"""ISLAND CLUSTERS, question 3 (2026-10-09): THE CELL FILL -- fill the hole a sink leaves, cell by cell, from the dropped
tris themselves.

sh_c2_hole.py filled the hole's outline with `lattice_patch`, which clips one polygon against each 4u cell. Two sites
broke it: Shimmering's hole ENCLOSES a kept islet (an inner loop, filled over), and an irregular outline clipped to a cell
left a degenerate piece the ear-clipper could not take. Here every dropped tri is cut against every cell it covers -- a
triangle and a square meet in one convex polygon, its crossing points computed from the ORIGINAL edge and the grid line
in one canonical order, so two tris sharing an edge cut it at the same floats -- and the pieces in a cell merge by edge
cancellation into the cell's outline: a whole cell (its square), or one or more loops to ear-clip. An islet inside the
hole needs no special case: each cell sees only its part of the islet's coast.
For each site: whole and partial cells, partial cells' loop counts, failures, plan area against the dropped tris' (land
and water), and samples: inside the hole one fill tri, outside none.
Writes out/sh_c3_cellfill.json. Run (from C:\\gd\\Dream-World-IX):
  py studies/terrain-malleability/land2sea/sh_c3_cellfill.py X Z [X Z ...]
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))

LAND = ("terrain", "beach1")
BAND = ("sea3", "sea5", "sea4")
PARTS = ("terrain", "beach1", "sea1", "sea2", "sea3", "sea5", "sea4", "object")
R = 5                                       # key decimals


def kp(p):
    return (round(p[0], R), round(p[1], R))


def cross_line(a, b, axis, val):
    """Where the segment a-b crosses the grid line coordinate[axis] == val, computed from the canonical order of its
    ends (so both tris sharing the edge get the same floats), or None."""
    if (a[0], a[1]) > (b[0], b[1]):
        a, b = b, a
    da, db = a[axis] - val, b[axis] - val
    if (da < 0) == (db < 0) or da == db:
        return None
    t = da / (da - db)
    p = [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]
    p[axis] = val                                    # exactly on the line
    return tuple(p)


def tri_cell_piece(tri, i, j):
    """The convex polygon (plan, CCW) where triangle ``tri`` [(x, z)]*3 meets cell (i, j); [] when they barely touch."""
    x0, x1, z0, z1 = 4.0 * i, 4.0 * i + 4.0, 4.0 * j, 4.0 * j + 4.0
    eps = 1e-9
    pts = []
    for p in tri:
        if x0 - eps <= p[0] <= x1 + eps and z0 - eps <= p[1] <= z1 + eps:
            pts.append(p)
    a, b, c = tri
    d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(d) < 1e-12:
        return []
    for q in ((x0, z0), (x1, z0), (x1, z1), (x0, z1)):
        w0 = ((b[1] - c[1]) * (q[0] - c[0]) + (c[0] - b[0]) * (q[1] - c[1])) / d
        w1 = ((c[1] - a[1]) * (q[0] - c[0]) + (a[0] - c[0]) * (q[1] - c[1])) / d
        if w0 >= -eps and w1 >= -eps and 1 - w0 - w1 >= -eps:
            pts.append(q)
    for k in range(3):
        e0, e1 = tri[k], tri[(k + 1) % 3]
        for axis, val, lo, hi in ((0, x0, z0, z1), (0, x1, z0, z1), (1, z0, x0, x1), (1, z1, x0, x1)):
            q = cross_line(e0, e1, axis, val)
            if q is not None and lo - eps <= q[1 - axis] <= hi + eps:
                pts.append(q)
    uniq = {}
    for p in pts:
        uniq.setdefault(kp(p), p)
    pts = list(uniq.values())
    if len(pts) < 3:
        return []
    cx = sum(p[0] for p in pts) / len(pts)
    cz = sum(p[1] for p in pts) / len(pts)
    pts.sort(key=lambda p: math.atan2(p[1] - cz, p[0] - cx))
    area = 0.5 * sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, pts[1:] + pts[:1]))
    return pts if area > 1e-7 else []


def cell_loops(pieces):
    """Merge convex pieces by edge cancellation: the outline loops of their union (vertex lists), or None when the
    edges do not chain into simple loops."""
    ec = Counter()
    first = {}
    for pc in pieces:
        for p, q in zip(pc, pc[1:] + pc[:1]):
            a, b = kp(p), kp(q)
            if a == b:
                continue
            ec[(a, b)] += 1
            first.setdefault(a, p)
            first.setdefault(b, q)
    # an edge cancels against its reverse
    out = {}
    for (a, b), n in ec.items():
        m = ec.get((b, a), 0)
        if n > m:
            out.setdefault(a, []).append(b)
    if any(len(v) != 1 for v in out.values()):
        return None
    loops, seen = [], set()
    for s in out:
        if s in seen:
            continue
        lp, cur = [], s
        while cur not in seen:
            seen.add(cur)
            lp.append(first[cur])
            nxt = out.get(cur)
            if not nxt:
                return None
            cur = nxt[0]
        if cur != s:
            return None
        loops.append(lp)
    return loops


def collinear_drop(lp):
    """Remove outline vertices that sit in a straight run ON THE CELL BORDER only? No: keep every vertex (welds)."""
    return lp


def site(at, res_all):
    from ff9mapkit.world import discmirror as DM, meshedit as ME, transplant as TR
    real = DM._real_parts(1, "0_1")
    home = (int(math.floor(at[0] / 64.0)), int(math.floor(-at[1] / 64.0)))
    blocks = sorted({(home[0] + dx, home[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)} & set(real))
    tris = {(b, p): TR.world_tris(*b, p, disc=1) if p in real[b] else [] for b in blocks for p in PARTS}
    land_all = [t for b in blocks for p in LAND for t in tris[(b, p)]]
    island = next(c for c in ME.vertex_components(land_all) if any(TR._tri_has(t, at) for t in c))
    region = set()
    for t in island:
        region |= TR._tiles_touched(t)
    drop = list(island) + [t for b in blocks for p in BAND for t in tris[(b, p)] if TR._tiles_touched(t) & region]
    did = {id(t) for t in drop}
    by_cell = defaultdict(list)
    for t in drop:
        P = [(v[0][0], v[0][2]) for v in t]
        for ij in TR._tiles_touched(t):
            pc = tri_cell_piece(P, *ij)
            if pc:
                by_cell[ij].append(pc)
    whole = partial = fail = multi = 0
    fill = []
    for ij, pcs in sorted(by_cell.items()):
        loops = cell_loops(pcs)
        if loops is None:
            fail += 1
            continue
        sq = {kp((4.0 * ij[0] + dx, 4.0 * ij[1] + dz)) for dx in (0, 4) for dz in (0, 4)}
        if len(loops) == 1 and {kp(p) for p in loops[0]} == sq:
            whole += 1
            fill += ME.lattice_patch([(4.0 * ij[0], 0, 4.0 * ij[1]), (4.0 * ij[0] + 4, 0, 4.0 * ij[1]),
                                      (4.0 * ij[0] + 4, 0, 4.0 * ij[1] + 4), (4.0 * ij[0], 0, 4.0 * ij[1] + 4)],
                                     y=0.0, uv_quads=((0, 0, 1, 1),), idall=0)
            continue
        partial += 1
        multi += len(loops) > 1
        for lp in loops:
            area = 0.5 * sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(lp, lp[1:] + lp[:1]))
            if area < 0:
                fail += 1                              # a hole in the cell (kept land wholly inside it)
                continue
            try:
                for t in ME.earclip(lp, quality=True):
                    fill.append([((p[0], 0.0, p[1]), (0, 1, 0), (0, 0), (0, 0, 0, 1)) for p in t])
            except ValueError:
                fail += 1
    fill_area = sum(TR._plan_clip_area([(v[0][0], v[0][2]) for v in t], -1e9, 1e9, -1e9, 1e9) for t in fill)
    piece_area = sum(0.5 * abs(sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pc, pc[1:] + pc[:1])))
                     for pcs in by_cell.values() for pc in pcs)
    # samples: a 0.5u lattice offset off the diagonals over the dropped footprint's bbox
    xs = [v[0][0] for t in drop for v in t]
    zs = [v[0][2] for t in drop for v in t]
    kept = [t for b in blocks for p in PARTS for t in tris[(b, p)] if id(t) not in did]
    miss = over = n = 0
    x = min(xs) + 0.13
    while x < max(xs):
        z = min(zs) + 0.29
        while z < max(zs):
            q = (x, z)
            inside = any(TR._tri_has(t, q) for t in drop if all(abs(v[0][1]) < 50 for v in t))
            k = sum(1 for t in fill if TR._tri_has(t, q))
            if inside:
                n += 1
                miss += k == 0
                over += k > 1
            elif k:
                over += 1
            z += 0.5
        x += 0.5
    out = {"at": at, "dropped": len(drop), "cells": len(by_cell), "whole": whole, "partial": partial,
           "multi_loop_cells": multi, "failed": fail, "piece_area": round(piece_area, 1),
           "fill_area": round(fill_area, 1), "fill_tris": len(fill), "samples": n, "miss": miss, "over": over}
    res_all[f"{at[0]},{at[1]}"] = out
    print(json.dumps(out))


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    a = [float(v) for v in sys.argv[1:]]
    res = {}
    for k in range(0, len(a), 2):
        site((a[k], a[k + 1]), res)
    (HERE / "out" / "sh_c3_cellfill.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
