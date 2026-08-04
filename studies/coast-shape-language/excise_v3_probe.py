"""EXCISE v3 -- what do the crescent's 5 interior waterline verts actually TOUCH?

The (14,0)+4x3 excise refuses: 5 waterline verts of the dropped assembly's ring are
neither on the deep sheet nor on the rect frame. Before designing anything, measure each
one against every candidate explanation:

  * NEAR-MISS      -- a sea4 vertex exists within 0.5u but off the 1e-4 key. Fix = none
                      needed conceptually; the exactness gate is too strict there.
  * ON A SEA4 EDGE -- the vert lies ON a boundary edge of the sea4 hole (collinear,
                      between endpoints). Stock itself T-junctions the ladder against the
                      sheet there; the fill inheriting the vert is stock-faithful.
  * NEAR THE KEPT assembly -- the vacated footprint abuts the crescent's own ladder;
                      filling against it authors geometry against the carried subject.
  * TRULY FREE     -- a genuine hole with nothing near: the fill must close it and the
                      ring is its only boundary source.

  py studies/coast-shape-language/excise_v3_probe.py [--donor 14,0 --size 4x3]

Read-only.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import transplant as TR                 # noqa: E402
from ff9mapkit.world import meshedit as ME                   # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--donor", default="14,0")
    ap.add_argument("--size", default="4x3")
    ap.add_argument("--disc", type=int, default=1)
    args = ap.parse_args()
    dx, dy = (int(v) for v in args.donor.split(","))
    nx, ny = (int(v) for v in args.size.lower().split("x"))

    tweaks, rep = TR.excise_plan((dx, dy), (nx, ny), disc=args.disc)
    print(f"excise report: foreign={rep['foreign']} dropped={rep.get('dropped')} "
          f"weld_missing={len(rep['weld_missing'])}")

    # everything in the rect, bucketed
    sea4, kept_water, dropped = [], [], []
    tagged = []
    for j in range(ny):
        for i in range(nx):
            for p in TR.PARTS:
                got = TR.world_tris(dx + i, dy + j, p, disc=args.disc)
                if p == "sea4":
                    sea4 += got
                else:
                    tagged += [(p, t) for t in got]
    comps = ME.vertex_components([t for _, t in tagged])
    part_of = {id(t): p for p, t in tagged}
    kept = [c for ci, c in enumerate(comps) if ci not in rep["foreign"]]
    kept_verts = [tuple(v[0]) for c in kept for t in c for v in t]
    sea4_verts = [tuple(v[0]) for t in sea4 for v in t]

    # sea4's own hole-boundary edges (edges used by exactly one sea4 tri)
    from collections import Counter
    ec = Counter()
    K = lambda v: (round(v[0], 4), round(v[1], 4), round(v[2], 4))
    for t in sea4:
        ks = [K(v[0]) for v in t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ec[frozenset((ks[a], ks[b]))] += 1
    bedges = [tuple(e) for e, n in ec.items() if n == 1 and len(e) == 2]

    def d2(a, b):
        return sum((a[k] - b[k]) ** 2 for k in range(3)) ** 0.5

    def edge_dist(p, a, b):
        ax, az, bx, bz, px, pz = a[0], a[2], b[0], b[2], p[0], p[2]
        vx, vz, wx, wz = bx - ax, bz - az, px - ax, pz - az
        L2 = vx * vx + vz * vz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, (wx * vx + wz * vz) / L2))
        cx, cz = ax + t * vx, az + t * vz
        return ((px - cx) ** 2 + (pz - cz) ** 2) ** 0.5, t

    for v in rep["weld_missing"]:
        v = tuple(v)
        ds4 = min((d2(v, s) for s in sea4_verts), default=1e9)
        dk = min((d2(v, s) for s in kept_verts), default=1e9)
        be = min(((*edge_dist(v, a, b), a, b) for a, b in bedges),
                 key=lambda r: r[0], default=None)
        print(f"\n  vert ({v[0]:.6f}, {v[1]:.6f}, {v[2]:.6f})")
        print(f"     nearest sea4 VERTEX: {ds4:.4f}u")
        print(f"     nearest KEPT-assembly vertex: {dk:.4f}u")
        if be:
            d, t, a, b = be
            print(f"     nearest sea4 hole-boundary EDGE: {d:.4f}u at t={t:.3f}  "
                  f"[{a} -> {b}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
