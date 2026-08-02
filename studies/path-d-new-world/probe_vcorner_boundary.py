"""Boundary-polyline extraction for THE CORNER FILLET — the chamfer targets.

From live Terrain (5,7): walkable tris' boundary edges (used by exactly one walkable
tri) in the catch zone, chained into polylines; per-vertex turn angles; per-vertex
seaward room (distance from the crest vertex to the wall FOOT line / water). READ-ONLY.
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402

ZONE = (368.0, 392.0, -522.0, -500.0)                       # x0, x1, z0, z1


def main():
    world = W.load_world()
    walk_tris = []
    for bk in sorted(world):
        terr = next(m for m in world[bk] if m["name"] == "Terrain")
        for ti, t in enumerate(terr["tris"]):
            if t[4] in W.WALK_OK:
                walk_tris.append((f"{bk}#{ti}", t))

    def key(p):
        return (round(p[0], 3), round(p[2], 3))

    edge_use = defaultdict(list)
    for ti, t in walk_tris:
        ps = [key(t[0]), key(t[1]), key(t[2])]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_use[tuple(sorted((ps[a], ps[b])))].append((ti, ps[a], ps[b]))

    x0, x1, z0, z1 = ZONE
    bnd = []
    for e, uses in edge_use.items():
        if len(uses) != 1:
            continue
        (ti, pa, pb) = uses[0]
        cx = (pa[0] + pb[0]) / 2
        cz = (pa[1] + pb[1]) / 2
        if x0 <= cx <= x1 and z0 <= cz <= z1:
            bnd.append((pa, pb, ti))
    print(f"{len(bnd)} boundary edges in the zone")

    nxt = defaultdict(list)
    for (pa, pb, ti) in bnd:
        nxt[pa].append(pb)
        nxt[pb].append(pa)
    seen = set()
    chains = []
    for start in [p for p, ns in nxt.items() if len(ns) == 1] + list(nxt):
        if start in seen:
            continue
        chain = [start]
        seen.add(start)
        cur = start
        while True:
            cand = [q for q in nxt[cur] if q not in seen]
            if not cand:
                break
            cur = cand[0]
            seen.add(cur)
            chain.append(cur)
        if len(chain) > 2:
            chains.append(chain)
    chains.sort(key=len, reverse=True)
    for ci, chain in enumerate(chains[:3]):
        print(f"\nchain {ci}: {len(chain)} verts")
        for i, p in enumerate(chain):
            seg = ""
            if i + 1 < len(chain):
                d = (chain[i + 1][0] - p[0], chain[i + 1][1] - p[1])
                L = math.hypot(*d)
                hdg = math.degrees(math.atan2(d[0], d[1])) % 360
                seg = f"  -> seg {L:5.2f}u @ {hdg:6.1f}deg"
            turn = ""
            if 0 < i < len(chain) - 1:
                d0 = (p[0] - chain[i - 1][0], p[1] - chain[i - 1][1])
                d1 = (chain[i + 1][0] - p[0], chain[i + 1][1] - p[1])
                a0 = math.atan2(d0[0], d0[1])
                a1 = math.atan2(d1[0], d1[1])
                dt = math.degrees((a1 - a0 + math.pi) % (2 * math.pi) - math.pi)
                mark = "  <== TURN" if abs(dt) > 35 else ""
                turn = f"  turn {dt:+6.1f}deg{mark}"
            print(f"   v{i:2d} ({p[0]:7.2f},{p[1]:8.2f}){seg}{turn}")


if __name__ == "__main__":
    main()
