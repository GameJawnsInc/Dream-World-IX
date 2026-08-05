"""RUNG 6 -- an ASCII map of the V-shore bench island, from the deployed Disc9 bytes.

  .  sea / no land        #  non-walkable (cliff, wall)
  g  clean GRASS lawn (topo 0, walkable, unstacked, y>0.6)
  w  walkable non-grass (shore shelf / relief classes 10/37/42)
  ^  walkable but high (y > 6)  --  the hill
Cell boundaries every 32u are marked with '|' / '-'.
"""
from __future__ import annotations

import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY)); sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDY.parent.parent / "ff9mapkit"))
import walk_sim as W                                          # noqa: E402
import probe_site as PS                                       # noqa: E402

STEP = 2                                                      # sample stride for the map


def main():
    W.CELLS = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]
    world = W.load_world()
    clean, ground, topo_of, stacked, (x0, z0, nx, nz) = PS.build_map(world)

    # margin to the nearest NON-WALKABLE sample (water/cliff) -- the safety number
    walkable = {k for k, t in topo_of.items() if t in W.WALK_OK and ground[k] > PS.SEA_Y}
    from collections import deque
    dist = {}
    q = deque()
    for k in walkable:
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if (k[0] + di, k[1] + dj) not in walkable:
                    dist[k] = 1
                    q.append(k)
                    break
            else:
                continue
            break
    while q:
        k = q.popleft()
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                n = (k[0] + di, k[1] + dj)
                if n in walkable and n not in dist:
                    dist[n] = dist[k] + 1
                    q.append(n)

    print("x ->  372 .. 462   (cols every 2u);  z rows every 2u from -462 down")
    hdr = "        " + "".join(str((x0 + i) // 32 % 10) if (x0 + i) % 32 < STEP else " "
                              for i in range(52, 146, STEP))
    print("cellx:  " + "".join(f"{int((x0 + i)//32)%10}" for i in range(52, 146, STEP)))
    for j in range(6, 118, STEP):
        z = z0 + j
        row = []
        for i in range(52, 146, STEP):
            k = (i, j)
            if k not in ground or ground[k] <= PS.SEA_Y:
                row.append(".")
            elif topo_of[k] not in W.WALK_OK:
                row.append("#")
            elif ground[k] > 6.0:
                row.append("^")
            elif k in clean:
                row.append("g")
            else:
                row.append("w")
        print(f"z{z:6.0f} c{int(-z//32)} " + "".join(row))

    print("\nDEEPEST INTERIOR (distance to nearest non-walkable sample):")
    best = sorted(((d, k) for k, d in dist.items() if k in clean), reverse=True)[:200]
    seen = set()
    for d, k in best:
        x, z = x0 + k[0] * PS.GRID, z0 + k[1] * PS.GRID
        cell = (int(x // 32), int(-z // 32))
        if cell in seen:
            continue
        seen.add(cell)
        print(f"   cell {cell}: best clean point ({x:.0f},{z:.0f}) y={ground[k]:.3f} "
              f"safety={d}u")
    # explicit report for the two chosen points
    for (px, pz, tag) in [(420.0, -475.0, "LANDING cand N"), (425.0, -550.0, "cand S"),
                          (432.0, -560.0, "cell(13,17) centre"), (418.0, -477.0, "LANDING alt")]:
        k = (int(round((px - x0) / PS.GRID)), int(round((pz - z0) / PS.GRID)))
        print(f"   {tag:22s} ({px},{pz}): y={ground.get(k)} topo={topo_of.get(k)} "
              f"clean={k in clean} safety={dist.get(k)}u")


if __name__ == "__main__":
    main()
