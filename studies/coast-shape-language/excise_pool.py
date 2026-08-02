"""Does EXCISE actually widen the carryable pool? (prediction E-3)

Without excise a donor rect is carryable only if EVERY mass it touches is contained
whole, clear of the frame. With excise, a rect qualifies if it contains at least one
whole mass worth carrying -- the frame-crossing neighbours are dropped and the deep
sheet re-zipped over them.

Mask-based enumeration (fast) over every rect up to 4x4; a sample is then gate-verified
with the real transplant, because a mask says what SHOULD qualify and only the gate
suite says what does.

  py studies/coast-shape-language/excise_pool.py [--max 4] [--verify 3]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "ff9mapkit"))

CELL, CPB = 4.0, 16                       # 4u cells; 16 cells per 64u block
NXB, NYB = 24, 20
MIN_KEEP = 60                             # cells: below this a "kept" mass is a pebble


def label_wrap(land):
    lab, n = ndi.label(land)
    for z in range(land.shape[0]):
        a, b = lab[z, 0], lab[z, -1]
        if a and b and a != b:
            lab[lab == b] = a
    return lab


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=4)
    ap.add_argument("--verify", type=int, default=3)
    ap.add_argument("--disc", type=int, default=1)
    args = ap.parse_args()

    d = np.load(HERE / "out" / f"landmask_d{args.disc}.npz")
    land = d["land"]
    lab = label_wrap(land)
    sizes = {int(i): int((lab == i).sum()) for i in np.unique(lab) if i}

    plain, with_ex = [], []
    for ny in range(1, args.max + 1):
        for nx in range(1, args.max + 1):
            for by in range(0, NYB - ny + 1):
                for bx in range(0, NXB - nx + 1):
                    z0, z1 = by * CPB, (by + ny) * CPB
                    x0, x1 = bx * CPB, (bx + nx) * CPB
                    sub = lab[z0:z1, x0:x1]
                    ids = {int(i) for i in np.unique(sub) if i}
                    if not ids:
                        continue
                    # a mass CROSSES if any of its cells lie outside the rect
                    crossing = {i for i in ids if (lab == i).sum() != int((sub == i).sum())}
                    whole = {i for i in ids - crossing if sizes[i] >= MIN_KEEP}
                    if not whole:
                        continue
                    rec = (bx, by, nx, ny, sorted(whole), sorted(crossing))
                    if not crossing:
                        plain.append(rec)
                    else:
                        with_ex.append(rec)

    def masses(recs):
        out = set()
        for r in recs:
            out |= set(r[4])
        return out

    print(f"rects up to {args.max}x{args.max}, keeping masses >= {MIN_KEEP} cells:")
    print(f"   carryable WITHOUT excise : {len(plain):>5} rects, "
          f"{len(masses(plain)):>3} distinct masses")
    print(f"   unlocked BY excise       : {len(with_ex):>5} rects, "
          f"{len(masses(with_ex)):>3} distinct masses")
    both = masses(plain) | masses(with_ex)
    print(f"   TOTAL reachable masses   : {len(both):>3} "
          f"(of {sum(1 for s in sizes.values() if s >= MIN_KEEP)} masses >= {MIN_KEEP} cells)")
    newly = masses(with_ex) - masses(plain)
    print(f"   masses ONLY excise reaches: {len(newly)} -> {sorted(newly)[:16]}")

    if args.verify:
        print(f"\ngate-verifying {args.verify} unlocked rect(s) with the real transplant:")
        from ff9mapkit.world import transplant as TR
        seen, done = set(), 0
        for bx, by, nx, ny, whole, crossing in sorted(
                with_ex, key=lambda r: -max(sizes[i] for i in r[4])):
            key = tuple(sorted(whole))
            if key in seen:
                continue
            seen.add(key)
            try:
                tw, rep = TR.excise_plan((bx, by), (nx, ny), disc=args.disc)
                r = TR.transplant_region(
                    "FF9CustomMap-world", cell=(14, 12), donor=(bx, by), size=(nx, ny),
                    shift=(0, 0), tweaks=tw, disc=args.disc, target_disc=9,
                    all_sea_target=True, dry_run=True, skip_mirror=True)
                bad = [g["gate"] for g in r["gates"] if not g.get("ok")]
                print(f"   ({bx},{by})+{nx}x{ny}: drop={rep.get('dropped')} "
                      f"fill={rep['fill_tris']} weld_exact={rep['weld_exact']} -> "
                      f"{'CLEAN' if not bad else 'FAIL ' + ','.join(bad)}")
            except Exception as e:                      # noqa: BLE001
                print(f"   ({bx},{by})+{nx}x{ny}: refused -- {type(e).__name__}: {e}")
            done += 1
            if done >= args.verify:
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
