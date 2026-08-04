"""C4 SKEPTIC follow-up: arbitrate the disputed WEST edges.

For each candidate boundary edge at the west site (the instrument's W1 and my
extra E_a/E_b + the 2dp-only extras), determine -- WITHOUT rounding-based edge
identity -- whether any other Terrain tri geometrically stitches it: for probe
points along the edge, find every other tri that contains the point within tol
in plan AND matches its height within tol (a coincident surface boundary), and
every tri whose own edge overlaps it collinearly (T-junction detection by
point-on-segment distance). Also prints global owner counts at 2/3/4dp and the
full union sheet stack under each midpoint. Run: py -X utf8 skeptic_c4_debug_west.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402
from skeptic_vshore_c4 import (build_index, edge_maps, sheets,  # noqa: E402
                               face_ny, rkey)

EDGES = [
    ("W1(inst)", (382.109, 5.376, -508.0), (384.0, 4.797, -512.0)),
    ("E_a(mine4dp)", (384.0, 4.2154, -516.4492), (384.0, 4.7975, -512.0)),
    ("E_b(mine4dp)", (384.0, 4.2154, -516.4492), (385.4297, 4.1061, -520.4648)),
    ("X1(mine2dp)", (383.19, 4.92, -504.0), (384.0, 5.45, -499.46)),
    ("X2(mine2dp)", (376.0, 3.46, -500.0), (379.63, 4.06, -504.0)),
    ("W3(both)", (384.0, 3.5982, -520.3438), (385.4297, 4.1061, -520.4648)),
    ("OUTborder", (384.0, 5.4537, -499.4609), (384.0, 5.5826, -496.0)),
    ("SKIRT1.56", (384.0, 5.5826, -496.0), (387.4844, 3.9381, -491.4844)),
    ("SKIRT0.59", (384.0, 3.649, -491.4883), (387.4844, 3.9381, -491.4844)),
]


def pt_seg_d3(p, a, b):
    ax, ay, az = a
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    l2 = dx * dx + dy * dy + dz * dz
    if l2 < 1e-12:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy + (p[2] - az) * dz) / l2))
    return math.dist(p, (ax + t * dx, ay + t * dy, az + t * dz))


def main():
    live = W.load_world()
    lidx = build_index(live)
    maps = {r: edge_maps(lidx, r) for r in (2, 3, 4)}

    terrain = [(m["bk"], ti, t) for m in lidx if m["part"] == "Terrain"
               for ti, t in enumerate(m["tris"])]

    for (name, A, B) in EDGES:
        print(f"\n=== {name}: {A} -> {B} ===")
        for r in (2, 3, 4):
            glob = maps[r][0]
            k = tuple(sorted((rkey(A, r), rkey(B, r))))
            own = glob.get(k, [])
            print(f"  {r}dp key owners: {len(own)} {[(list(o[0]), o[1]) for o in own]}")
        # geometric stitch arbiter: any OTHER tri with an edge overlapping this one
        probes = [tuple(A[i] + f * (B[i] - A[i]) for i in range(3))
                  for f in (0.25, 0.5, 0.75)]
        owners_hit = set()
        for (bk, ti, t) in terrain:
            es = [(t[0], t[1]), (t[1], t[2]), (t[2], t[0])]
            for (ea, eb) in es:
                dmax = max(pt_seg_d3(p, ea, eb) for p in probes)
                if dmax < 0.05:
                    owners_hit.add((bk, ti))
        print(f"  geometric edge-overlap owners (all probes within 0.05 of a tri edge):")
        for (bk, ti) in sorted(owners_hit):
            t = dict(terrain=None)
            for m in lidx:
                if m["part"] == "Terrain" and m["bk"] == bk:
                    tri = m["tris"][ti]
            print(f"    bk={bk} ti={ti} mapid={tri[3]} topo={tri[4]} "
                  f"ny={face_ny(tri[0], tri[1], tri[2]):.3f} "
                  f"verts={[[round(c, 4) for c in v] for v in (tri[0], tri[1], tri[2])]}")
        mx, my, mz = [(A[i] + B[i]) / 2 for i in range(3)]
        st = sheets(lidx, mx, mz, render=True)
        print(f"  union render stack at mid ({mx:.2f},{mz:.2f}), edge y={my:.3f}:")
        for s in st[:6]:
            print(f"    y={s[0]:.3f} topo={s[1]} mapid={s[2]} part={s[3]}")


if __name__ == "__main__":
    main()
