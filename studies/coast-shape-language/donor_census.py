"""WHICH STOCK BLOCKS CAN WE ACTUALLY CARRY? -- the donor side of the shape question.

The shape probe says what stock BUILDS. This says what we can TAKE. They are not the
same set, and the difference is what makes a design menu honest.

Found the hard way, from a `world-transplant --size 2x1` dry-run of donor (8,14):

    GATE object-anchor[8,14]: x=[512.895,516.801] z=[-908,-896] moved=True -> FAIL

A block carrying an anchored world OBJECT (a town, a landmark, a chocobo forest) refuses
the carry, because carrying it would relocate that landmark. Since stock puts objects on
exactly the interesting coasts, this prunes the donor pool hard -- and it prunes it in a
way no amount of staring at the shape census would reveal.

  py studies/coast-shape-language/donor_census.py [--disc 1]

Emits out/donors_d1.json: per candidate block, whether it is object-free, its coastal
parts, its land fraction, and which located shape instances it contains.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

G, BLOCK = 4.0, 64.0
CPB = int(BLOCK / G)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", type=int, default=1)
    args = ap.parse_args()

    d = np.load(HERE / "out" / f"landmask_d{args.disc}.npz")
    land, foot = d["land"], d["foot"]
    shapes = json.loads((HERE / "out" / f"shapes_d{args.disc}.json").read_text())

    objs = set(map(tuple, X.list_object_blocks(disc=args.disc)))
    coasts = X.list_coastal_donors(disc=args.disc, beach_only=False)
    print(f"{len(objs)} blocks carry an anchored object; {len(coasts)} are coastal")

    by_block = defaultdict(list)
    for klass, insts in shapes.items():
        if klass == "disc":
            continue
        for i in insts:
            by_block[tuple(i["block"])].append(klass)

    rows = []
    for (bx, by), parts in sorted(coasts.items()):
        z0, x0 = by * CPB, bx * CPB
        sub = land[z0:z0 + CPB, x0:x0 + CPB]
        subf = foot[z0:z0 + CPB, x0:x0 + CPB]
        n = int(sub.sum())
        if not n:
            continue
        rows.append(dict(
            block=[bx, by],
            object_free=(bx, by) not in objs,
            parts=sorted(parts),
            land_frac=round(n / sub.size, 3),
            walk_frac=round(float(subf.sum()) / n, 2),
            shapes=sorted(set(by_block.get((bx, by), []))),
        ))

    clean = [r for r in rows if r["object_free"]]
    withshape = [r for r in clean if r["shapes"]]
    print(f"{len(rows)} coastal land blocks; {len(clean)} object-free; "
          f"{len(withshape)} object-free AND carrying a located shape")

    # which shape classes still have a clean donor?
    cover = defaultdict(int)
    blocked = defaultdict(int)
    for r in rows:
        for s in r["shapes"]:
            (cover if r["object_free"] else blocked)[s] += 1
    print("\nclean donor blocks per shape class (blocked = object-anchored):")
    for k in sorted(set(cover) | set(blocked)):
        print(f"   {k:>8}: {cover.get(k, 0):>3} clean, {blocked.get(k, 0):>3} blocked")

    print("\nbest object-free donors (land 25-85%, most shapes, most walkable):")
    pick = [r for r in withshape if 0.25 <= r["land_frac"] <= 0.85]
    pick.sort(key=lambda r: (-len(r["shapes"]), -r["walk_frac"]))
    for r in pick[:14]:
        print(f"   {str(r['block']):>9}  land {r['land_frac']:.2f}  walk {r['walk_frac']:.2f}  "
              f"{','.join(r['shapes']):<28} parts={','.join(p for p in r['parts'] if p.startswith('beach') or p in ('sea1', 'sea2'))}")

    p = HERE / "out" / f"donors_d{args.disc}.json"
    p.write_text(json.dumps(dict(disc=args.disc, object_blocks=sorted(map(list, objs)),
                                 donors=rows), indent=1), encoding="utf-8")
    print(f"\n-> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
