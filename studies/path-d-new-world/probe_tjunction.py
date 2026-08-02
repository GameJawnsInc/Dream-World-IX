"""THE T-JUNCTION GATE — a vertex lying in the INTERIOR of another face's edge.

A T-junction is watertight in exact arithmetic and cracks under float32
rasterisation, so it is invisible to the render gate at most cameras and to
the weld audit (which only looks for near-MISS duplicate vertices) — but the
player sees a hairline of whatever is behind: for a lawn, the hollow interior,
which reads as pale specks along a seam. This finds them by construction.

  py probe_tjunction.py [staged|live|baseline]
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402
import vcorner_transplant as VT                             # noqa: E402
from vcorner_crest import BASELINE_T                        # noqa: E402

EPS = 2e-3                      # off-segment distance that still cracks
ZONE = (368.0, 392.0, -534.0, -500.0)


def scan(tag):
    found = {}
    for (bx, by) in VT.BLOCKS:
        if tag == "staged":
            p = VT.OUTD2 / f"Block[{bx}][{by}] Terrain.ff9mesh"
        elif tag == "baseline":
            p = BASELINE_T[(bx, by)]
        else:
            p = VT.live_path(bx, by, "Terrain")
        d = W.M.read_ff9mesh(p)
        ox, oz = 64.0 * bx, -64.0 * by
        idx, vs = d["indices"], d["verts"]
        pts, edges = {}, set()
        for t0 in range(0, len(idx), 3):
            t = idx[t0:t0 + 3]
            k3 = []
            for j in t:
                q = (round(vs[j][0] + ox, 5), round(vs[j][1], 5), round(vs[j][2] + oz, 5))
                pts[q] = True
                k3.append(q)
            for a, b in ((0, 1), (1, 2), (2, 0)):
                edges.add(tuple(sorted((k3[a], k3[b]))))
        x0, x1, z0, z1 = ZONE
        verts = [q for q in pts if x0 <= q[0] <= x1 and z0 <= q[2] <= z1]
        for (a, b) in edges:
            if not (x0 <= (a[0] + b[0]) / 2 <= x1 and z0 <= (a[2] + b[2]) / 2 <= z1):
                continue
            ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            L2 = ab[0] ** 2 + ab[1] ** 2 + ab[2] ** 2
            if L2 < 1e-12:
                continue
            for q in verts:
                if q == a or q == b:
                    continue
                aq = (q[0] - a[0], q[1] - a[1], q[2] - a[2])
                t = (aq[0] * ab[0] + aq[1] * ab[1] + aq[2] * ab[2]) / L2
                if not (1e-4 < t < 1 - 1e-4):
                    continue
                px = (a[0] + t * ab[0], a[1] + t * ab[1], a[2] + t * ab[2])
                dd = math.dist(px, q)
                if dd < EPS:
                    found[(q, a, b)] = dd
    return found


def diff():
    s, b = scan("staged"), scan("baseline")
    new = {k: v for k, v in s.items() if k not in b}
    gone = {k: v for k, v in b.items() if k not in s}
    print(f"staged {len(s)}  baseline {len(b)}  NEW {len(new)}  removed {len(gone)}")
    for (q, a, bb), dd in sorted(new.items(), key=lambda kv: -kv[1]):
        print(f"   NEW vert ({q[0]:8.3f},{q[1]:5.2f},{q[2]:9.3f}) on "
              f"({a[0]:.3f},{a[2]:.3f})-({bb[0]:.3f},{bb[2]:.3f}) off {dd:.5f}")
    return len(new)


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "staged"
    if tag == "diff":
        n = diff()
        print(f"\nT-JUNCTION DIFF: {n} NEW -> {'PASS' if n == 0 else 'FAIL'}")
        return
    total = 0
    for (bx, by) in VT.BLOCKS:
        if tag == "staged":
            p = VT.OUTD2 / f"Block[{bx}][{by}] Terrain.ff9mesh"
        elif tag == "baseline":
            p = BASELINE_T[(bx, by)]
        else:
            p = VT.live_path(bx, by, "Terrain")
        d = W.M.read_ff9mesh(p)
        ox, oz = 64.0 * bx, -64.0 * by
        idx, vs = d["indices"], d["verts"]
        pts = {}
        edges = set()
        for t0 in range(0, len(idx), 3):
            t = idx[t0:t0 + 3]
            k3 = []
            for j in t:
                q = (round(vs[j][0] + ox, 5), round(vs[j][1], 5), round(vs[j][2] + oz, 5))
                pts[q] = True
                k3.append(q)
            for a, b in ((0, 1), (1, 2), (2, 0)):
                edges.add(tuple(sorted((k3[a], k3[b]))))
        x0, x1, z0, z1 = ZONE
        verts = [q for q in pts if x0 <= q[0] <= x1 and z0 <= q[2] <= z1]
        hits = []
        for (a, b) in edges:
            if not (x0 <= (a[0] + b[0]) / 2 <= x1 and z0 <= (a[2] + b[2]) / 2 <= z1):
                continue
            ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            L2 = ab[0] ** 2 + ab[1] ** 2 + ab[2] ** 2
            if L2 < 1e-12:
                continue
            for q in verts:
                if q == a or q == b:
                    continue
                aq = (q[0] - a[0], q[1] - a[1], q[2] - a[2])
                t = (aq[0] * ab[0] + aq[1] * ab[1] + aq[2] * ab[2]) / L2
                if not (1e-4 < t < 1 - 1e-4):
                    continue
                px = (a[0] + t * ab[0], a[1] + t * ab[1], a[2] + t * ab[2])
                if math.dist(px, q) < EPS:
                    hits.append((q, a, b, math.dist(px, q)))
        total += len(hits)
        print(f"   [{bx}][{by}]: {len(hits)} T-junctions in the corner zone")
        for (q, a, b, dd) in hits[:8]:
            print(f"      vert ({q[0]:8.3f},{q[1]:6.2f},{q[2]:9.3f}) sits on edge "
                  f"({a[0]:.2f},{a[1]:.2f},{a[2]:.2f})-({b[0]:.2f},{b[1]:.2f},{b[2]:.2f}) "
                  f"off {dd:.5f}")
    print(f"\nT-JUNCTION GATE [{tag}]: {total} -> {'PASS' if total == 0 else 'FAIL'}")


if __name__ == "__main__":
    main()
