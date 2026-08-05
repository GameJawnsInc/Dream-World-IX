"""Revert the Path D Disc9 carries: the FRAYING TAIL anchor, THE ISTHMUS, THE CORNER ISLE.

The five target cells were EMPTY before this deploy (`mod-overwrite: existing=0`), so the
revert is a clean delete -- nothing is being restored over, and nothing else in the
shared install is touched. Lists what it would remove unless --apply is passed.

  py studies/coast-shape-language/revert_fraying_tail.py [--apply]
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

GAME = Path(os.environ.get(
    "FF9_GAME",
    r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"))
ROOT = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc9" / "0_1"

ANCHOR = [(11, 12), (10, 13), (11, 13), (10, 14), (11, 14)]   # comma, (10,12)+2x3
ISTHMUS = [(14, 12), (15, 12), (14, 13), (15, 13)]            # waisted, (14,12)+2x2
CORNER = [(13, 15)]                                           # (0,0) 1x1, a pure carry
SETS = {"anchor": ANCHOR, "isthmus": ISTHMUS, "corner": CORNER}
PARTS = ("Terrain.ff9mesh", "Sea3.ff9mesh", "Sea5.ff9mesh", "Sea4.ff9mesh",
         "Donor.txt")

# Cells that belong to OTHER work in this shared world -- never touch them.
PROTECTED = {(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)}      # the Path D bench


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", choices=sorted(SETS), help="revert just one carry")
    args = ap.parse_args()

    cells = SETS[args.only] if args.only else [c for v in SETS.values() for c in v]
    assert not (set(cells) & PROTECTED), "refusing: overlaps the owner-accepted bench"
    todo = []
    for bx, by in cells:
        for part in PARTS:
            p = ROOT / f"r{by}" / f"Block[{bx}][{by}] {part}"
            if p.exists():
                todo.append(p)
    if not todo:
        print("nothing to revert -- nothing is deployed")
        return 0
    for p in todo:
        print(("removing " if args.apply else "would remove ") + str(p))
        if args.apply:
            p.unlink()
    if args.apply:
        for by in {c[1] for c in cells}:                # tidy empty row dirs
            d = ROOT / f"r{by}"
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
                print(f"removed empty {d}")
        print("\nreverted. RELAUNCH (or exit+re-enter the overworld) to apply.")
    else:
        print(f"\n{len(todo)} file(s); re-run with --apply to delete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
