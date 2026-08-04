"""THE TUCK VOCABULARY (study angle 6, measurement half) — READ-ONLY.

The offset-loop curtain spec source: measure the bench's OWN coast
cross-section at sample stations — how the owner-passed shore hides its wall
from above (farcoast_nw proof) while showing rock at sea level. Per station:
the lawn-edge line, the wall crest line, their signed plan offset (the TUCK
OFFSET: + = crest seaward of the lawn edge = exposed; − = crest tucked
inland under the lawn edge = hidden from above), wall lean (seaward ny),
foot y, uv band. A fork-(i) rebuild must reproduce THIS distribution around
the corner. No build here — measurements only.
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402

# stations: far coast (owner-passed look, verified clean at close range) then
# the corner-adjacent runs (where the slivers show)
STATIONS = [
    ("far-nw", 375.1, -486.6), ("far-n", 386.8, -485.5),
    ("far-e", 448.5, -512.0), ("far-se", 448.0, -544.3),
    ("far-s", 400.1, -536.0), ("far-ne", 421.4, -487.2),
    ("run-n", 372.5, -505.5), ("run-n2", 374.5, -508.0),
    ("run-s", 377.5, -519.0), ("run-s2", 375.5, -522.5),
    ("apex", 378.4, -512.5),
]
R = 3.5                                                     # station radius


def main():
    world = W.load_world()
    lawn_edges, walls = [], []
    for bk in sorted(world):
        terr = next(m for m in world[bk] if m["name"] == "Terrain")
        edge = defaultdict(int)
        ev = {}
        for t in terr["tris"]:
            if t[4] not in W.WALK_OK:
                continue
            ks = [(round(p[0], 3), round(p[2], 3)) for p in t[:3]]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                e = tuple(sorted((ks[a], ks[b])))
                edge[e] += 1
                ev[e] = (t[a], t[b])
        for e, cnt in edge.items():
            if cnt == 1 and abs(ev[e][0][1] - 3.2) < 0.35:
                lawn_edges.append(e)
        for t in terr["tris"]:
            a, b, c = np.array(t[0]), np.array(t[1]), np.array(t[2])
            n = np.cross(b - a, c - a)
            L = np.linalg.norm(n)
            if L < 1e-12 or abs(n[1] / L) > 0.35:
                continue
            ys = [t[i][1] for i in range(3)]
            if max(ys) < 1.5:
                continue
            walls.append((t, n / L))

    print(f"{len(lawn_edges)} lawn-edge segments, {len(walls)} wall faces\n")
    print(f"{'station':8s} {'tuckoff':>8s} {'lean_ny':>8s} {'crest_y':>8s} "
          f"{'foot_y':>7s} {'#wall':>5s}  note")
    for name, sx, sz in STATIONS:
        near_e = [e for e in lawn_edges
                  if math.hypot((e[0][0] + e[1][0]) / 2 - sx,
                                (e[0][1] + e[1][1]) / 2 - sz) < R]
        near_w = [(t, n) for (t, n) in walls
                  if math.hypot(sum(t[i][0] for i in range(3)) / 3 - sx,
                                sum(t[i][2] for i in range(3)) / 3 - sz) < R]
        if not near_e or not near_w:
            print(f"{name:8s} {'—':>8s} {'—':>8s} {'—':>8s} {'—':>7s} "
                  f"{len(near_w):5d}  no lawn-edge/wall pair in radius")
            continue
        # crest verts: wall verts within 0.6 of the wall's own max y
        offs, leans, cys, fys = [], [], [], []
        for (t, n) in near_w:
            ys = [t[i][1] for i in range(3)]
            ymax, ymin = max(ys), min(ys)
            cys.append(ymax)
            fys.append(ymin)
            # seaward = away from the nearest lawn-edge midpoint
            cen = np.array([sum(t[i][0] for i in range(3)) / 3, 0,
                            sum(t[i][2] for i in range(3)) / 3])
            emid = min(near_e, key=lambda e: math.hypot(
                (e[0][0] + e[1][0]) / 2 - cen[0], (e[0][1] + e[1][1]) / 2 - cen[2]))
            (ax, az), (bx, bz) = emid
            ed = np.array([bx - ax, bz - az])
            ed /= np.linalg.norm(ed)
            for i in range(3):
                if t[i][1] > ymax - 0.6:                    # a crest vert
                    dv = np.array([t[i][0] - ax, t[i][2] - az])
                    perp = dv - (dv @ ed) * ed              # off-edge-line component
                    d = float(np.linalg.norm(perp))
                    # sign: + if crest is on the SEA side of the lawn edge —
                    # sea side = the side the wall centroid's low verts lean to
                    lowv = min(range(3), key=lambda j: t[j][1])
                    lv = np.array([t[lowv][0] - ax, t[lowv][2] - az])
                    lperp = lv - (lv @ ed) * ed
                    same = float(perp @ lperp) > 0
                    offs.append(d if same else -d)          # +: crest past foot side
            leans.append(float(n[1]))
        note = "EXPOSED (crest proud)" if np.median(offs) > 0.25 else \
               ("tucked" if np.median(offs) < -0.05 else "flush")
        print(f"{name:8s} {np.median(offs):8.2f} {np.median(leans):8.2f} "
              f"{np.median(cys):8.2f} {np.median(fys):7.2f} {len(near_w):5d}  {note}")


if __name__ == "__main__":
    main()
