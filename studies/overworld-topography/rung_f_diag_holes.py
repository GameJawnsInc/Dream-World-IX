"""Confirm: the residual grass once-edges come from missing cells ENCLOSED by the carried blob
(stranded grass patches), and the blob has interior hole loops that need ear-clip fill."""
from __future__ import annotations
import math, sys
from collections import Counter, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg
import rung_f_layout as RFL

CELL = 4.0
NEI4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def main():
    gr = Path(_cfg.find_game_path(None))
    comp = RFL.compose(gr)
    placed = set(comp["placed_R"])
    cxs = [c[0] for c in placed]; czs = [c[1] for c in placed]
    x0, x1, z0, z1 = min(cxs), max(cxs), min(czs), max(czs)
    # missing cells in bbox
    missing = {(cx, cz) for cx in range(x0, x1 + 1) for cz in range(z0, z1 + 1)
               if (cx, cz) not in placed}
    print(f"placed {len(placed)}, bbox {(x1-x0+1)*(z1-z0+1)}, missing {len(missing)}")

    # flood the "outside" from the bbox border through missing/non-placed cells -> which missing are enclosed?
    # outside = cells reachable from outside the bbox through non-placed cells.
    # Build a padded grid; BFS from padding ring through non-placed cells.
    lo = (x0 - 1, z0 - 1); hi = (x1 + 1, z1 + 1)
    outside = set()
    dq = deque()
    for cx in range(lo[0], hi[0] + 1):
        for cz in (lo[1], hi[1]):
            outside.add((cx, cz)); dq.append((cx, cz))
    for cz in range(lo[1], hi[1] + 1):
        for cx in (lo[0], hi[0]):
            if (cx, cz) not in outside:
                outside.add((cx, cz)); dq.append((cx, cz))
    while dq:
        c = dq.popleft()
        for di, dj in NEI4:
            n = (c[0] + di, c[1] + dj)
            if lo[0] <= n[0] <= hi[0] and lo[1] <= n[1] <= hi[1] and n not in outside and n not in placed:
                outside.add(n); dq.append(n)
    enclosed = {c for c in missing if c not in outside}
    perim = missing - enclosed
    print(f"ENCLOSED missing cells (stranded grass): {len(enclosed)} -> {sorted(enclosed)}")
    print(f"perimeter-indent missing cells: {len(perim)} -> {sorted(perim)}")
    # rim edge count for enclosed cells (edges to placed neighbors)
    rim = 0
    for c in enclosed:
        for di, dj in NEI4:
            if (c[0] + di, c[1] + dj) in placed:
                rim += 1
    print(f"enclosed-cell rim edges (to placed): {rim}")


if __name__ == "__main__":
    main()
