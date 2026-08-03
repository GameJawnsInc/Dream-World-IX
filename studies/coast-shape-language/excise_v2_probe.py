"""EXCISE v2 -- what do the non-deep waterline vertices actually ABUT?

v1 refuses when the excised assembly's waterline does not lie wholly on the deep sheet
("the mass owns a shallow-water ladder, which excise v1 does not re-zip"). Before
designing the re-zip, measure what those vertices touch, because the fix is different
per case:

  * ON THE RECT FRAME   -- the mass is cropped by the frame anyway; the fill simply runs
                           out to the frame and the "missing" sea4 is the neighbouring
                           cell's problem, not ours. Cheapest possible fix.
  * ON A KEPT ASSEMBLY  -- the excised ladder is WELDED to the island we are carrying.
                           Filling would have to cut a shared boundary: expensive, and it
                           authors geometry against a surface we care about.
  * FREE / INTERIOR     -- a genuine hole in the sheet that the fill must close.

  py studies/coast-shape-language/excise_v2_probe.py --donor 5,15 --size 3x2

Read-only.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import transplant as TR                 # noqa: E402
from ff9mapkit.world import meshedit as ME                   # noqa: E402

BLOCK = 64.0
KD = 4


def key(v):
    return (round(v[0], KD), round(v[1], KD), round(v[2], KD))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--donor", default="5,15")
    ap.add_argument("--size", default="3x2")
    ap.add_argument("--disc", type=int, default=1)
    args = ap.parse_args()
    dx, dy = (int(v) for v in args.donor.split(","))
    nx, ny = (int(v) for v in args.size.lower().split("x"))
    x0, x1 = BLOCK * dx, BLOCK * (dx + nx)
    z1, z0 = -BLOCK * dy, -BLOCK * (dy + ny)

    parts = [p for p in TR.PARTS]
    tagged, sea4 = [], []
    for j in range(ny):
        for i in range(nx):
            for p in parts:
                got = TR.world_tris(dx + i, dy + j, p, disc=args.disc)
                if p == "sea4":
                    sea4 += got
                else:
                    tagged += [(p, t) for t in got]

    comps = ME.vertex_components([t for _, t in tagged])
    print(f"donor ({dx},{dy})+{nx}x{ny}: {len(tagged)} non-sea4 tris, "
          f"{len(sea4)} sea4 tris, {len(comps)} assemblies")

    part_of = {}
    for p, t in tagged:
        for v in t:
            part_of.setdefault(key(v[0]), set()).add(p)

    sea4_keys = {key(v[0]) for t in sea4 for v in t}
    frame_eps = 1e-3

    def on_frame(k):
        return (abs(k[0] - x0) < frame_eps or abs(k[0] - x1) < frame_eps
                or abs(k[2] - z0) < frame_eps or abs(k[2] - z1) < frame_eps)

    # which assemblies cross the frame (= foreign, would be excised)
    foreign = []
    for ci, c in enumerate(comps):
        ks = [key(v[0]) for t in c for v in t]
        if any(on_frame(k) for k in ks):
            foreign.append(ci)
    print(f"   frame-crossing (foreign) assemblies: {foreign}")

    kept_keys = {key(v[0]) for ci, c in enumerate(comps) if ci not in foreign
                 for t in c for v in t}

    for ci in foreign:
        ks = {key(v[0]) for t in comps[ci] for v in t}
        # the waterline = this assembly's boundary vertices
        bnd = set()
        for cyc in ME.boundary_cycles(comps[ci]):
            bnd |= set(cyc)
        bad = [k for k in bnd if k not in sea4_keys]
        cls = Counter()
        for k in bad:
            if on_frame(k):
                cls["ON THE RECT FRAME"] += 1
            elif k in kept_keys:
                cls["welded to a KEPT assembly"] += 1
            else:
                cls["free (a genuine sheet hole)"] += 1
        print(f"\n   assembly #{ci}: {len(comps[ci])} tris, {len(bnd)} boundary verts, "
              f"{len(bad)} NOT on the deep sheet")
        for k2, n in cls.most_common():
            print(f"      {n:>4}  {k2}")
        pc = Counter()
        for k in bad:
            pc[tuple(sorted(part_of.get(k, ())))] += 1
        for k2, n in pc.most_common(4):
            print(f"      parts at those verts: {n:>4} x {k2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
