"""THE WORKED EXAMPLE: field 559 (the behavior benches' own donut arena).

Produces every number the study needs: the decomposition, the emitted table sizes,
the per-tick executed cost, and a QUALITY comparison of roadmap next-hop routing
against the kit's own A* (the same pathfinder Path A uses at build time).
"""
from __future__ import annotations

import json
import math
import pickle
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/unruffled-moser-861897/ff9mapkit")

import emit  # noqa: E402
import roadmap  # noqa: E402
from ff9mapkit.content import pathfind  # noqa: E402
from ff9mapkit.scene.bgi import BgiWalkmesh  # noqa: E402

CACHE = HERE / "559_decomp.pkl"
_WV = [None]

# world_verts() is recomputed on EVERY point_on_walkmesh call; memoise it so the
# A* comparison finishes this decade (pure speed, identical results).
_orig_wv = BgiWalkmesh.world_verts


def _cached_wv(self):
    c = getattr(self, "_wvcache", None)
    if c is None:
        c = _orig_wv(self)
        self._wvcache = c
    return c


BgiWalkmesh.world_verts = _cached_wv


def load():
    m = BgiWalkmesh.from_bytes((HERE / "559.bgi").read_bytes())
    if CACHE.exists():
        ro, regs, portals, fo = pickle.loads(CACHE.read_bytes())
    else:
        ro, regs, portals, fo = roadmap.decompose(m)
        CACHE.write_bytes(pickle.dumps((ro, regs, portals, fo)))
    _WV[0] = m.world_verts()
    return m, ro, regs, portals, fo


def region_aabbs(m, regs):
    wv = m.world_verts()
    out = []
    for mem in regs:
        xs, zs = [], []
        for ti in mem:
            for v in m.tris[ti].vtx:
                xs.append(wv[v][0])
                zs.append(wv[v][2])
        out.append((int(min(xs)), int(max(xs)), int(min(zs)), int(max(zs))))
    return out


def roadmap_path(start, goal, m, ro, regs, portals, NEXT, cen):
    """Simulate what a compiled roadmap pursuer would actually walk: from its
    region, hop portal midpoint to portal midpoint until it shares the target's
    region, then straight at the target."""
    from ff9mapkit.scene.bgi import _pt_in_tri_xz
    wv = _WV[0]

    def region_at(p):
        for ti, t in enumerate(m.tris):
            if _pt_in_tri_xz(p[0], p[1], wv[t.vtx[0]], wv[t.vtx[1]], wv[t.vtx[2]]):
                return ro[ti]
        return None
    rs, rg = region_at(start), region_at(goal)
    if rs is None or rg is None:
        return None
    pts = [start]
    cur = rs
    guard = 0
    while cur != rg:
        guard += 1
        if guard > 80:
            return None
        nxt = NEXT[cur][rg]
        if nxt < 0:
            return None
        mid = portals[(cur, nxt)][0]
        pts.append((mid[0], mid[1]))
        cur = nxt
    pts.append(goal)
    return pts


def plen(pts):
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
               for i in range(len(pts) - 1))


def main():
    m, ro, regs, portals, fo = load()
    R = len(regs)
    NEXT = roadmap.next_hop_table(R, portals)
    cen = roadmap.centroids(m)
    cells = sum(1 for r in NEXT for v in r if v >= 0)
    print(f"field 559: {len(m.tris)} tris / {len(m.floors)} floors "
          f"-> R={R} regions, {len(portals)} directed portals, {cells} routable ordered pairs")

    # ---- emitted size
    try:
        nb = len(emit.emit_next_chain(NEXT))
    except Exception as ex:
        nb = None
        print(f"  next-hop chain: CANNOT BE ASSEMBLED -- {ex}")
    if nb:
        print(f"  next-hop chain : {nb} B")
    wb = len(emit.emit_waypoint_chain(portals))
    ab = len(emit.emit_membership_full(region_aabbs(m, regs)))
    ib = len(emit.emit_incremental_membership(set(portals), 1300))
    print(f"  waypoint chain : {wb} B ({len(portals)} portals)")
    print(f"  full rescan    : {ab} B (AABB lower bound, {R} regions)")
    print(f"  incremental    : {ib} B ({len(portals)} portal half-planes)")

    # ---- per-tick executed cost (worst-case compares walked before a hit)
    print(f"  per-tick executed compares (worst case): next-hop {R} + {R} = {2 * R}, "
          f"waypoint {len(portals)}, membership {R} (rescan) or "
          f"{max(len(v) for v in _outdeg(portals).values())} (incremental)")

    # ---- QUALITY: roadmap route vs the kit A* (the Path-A pathfinder)
    random.seed(7)
    free_pts = []
    sp = {fi: roadmap.FloorSpace(m, fi) for fi in range(len(m.floors))}
    wv = m.world_verts()
    xs = [v[0] for v in wv]
    zs = [v[2] for v in wv]
    while len(free_pts) < 400:
        x = random.uniform(min(xs), max(xs))
        z = random.uniform(min(zs), max(zs))
        if sp[0].free(x, z):
            free_pts.append((x, z))
    ratios, hops, fails = [], [], 0
    for _ in range(120):
        a, b = random.sample(free_pts, 2)
        rp = roadmap_path(a, b, m, ro, regs, portals, NEXT, cen)
        star = pathfind.route(m, a, b, ())
        if rp is None or not star:
            fails += 1
            continue
        astar = [a] + [(p[0], p[1]) for p in star]
        if plen(astar) < 1:
            continue
        ratios.append(plen(rp) / plen(astar))
        hops.append(len(rp) - 2)
    ratios.sort()
    print(f"\nQUALITY (120 random pursuit chords, roadmap vs the kit A*):")
    print(f"  unroutable by roadmap: {fails}")
    print(f"  length ratio  median {ratios[len(ratios)//2]:.2f}  "
          f"p90 {ratios[int(.9*len(ratios))]:.2f}  max {ratios[-1]:.2f}")
    print(f"  portal hops   median {sorted(hops)[len(hops)//2]}  max {max(hops)}")


def _outdeg(portals):
    d = {}
    for (a, b) in portals:
        d.setdefault(a, set()).add(b)
    return d or {0: set()}


if __name__ == "__main__":
    main()
