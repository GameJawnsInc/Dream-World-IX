"""Auto-pathing: route a blocked cutscene walk AROUND obstacles into clear straight legs.

A FF9 field walk is straight-line + synchronous, so it can't round a corner (off the walkmesh) or pass
a standing character (its collision box) on its own -- it presses into the obstacle and stalls. This
finds a route over the walkmesh that avoids both, then string-pulls it down to a few waypoints (which
the builder emits as a ``path``).

Grid A* over the walkmesh bounds: a cell is FREE if its centre is on the walkmesh, at least
``clearance`` from any wall (the player's controller radius), and at least ``obstacle_r`` from every
other character's centre (= the collision distance, so the actor never enters a box). Pure stdlib;
operates on a :class:`ff9mapkit.scene.bgi.BgiWalkmesh`.
"""

from __future__ import annotations

import heapq

from ..scene import cam

_NEIGHBORS = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]


def _free(wmesh, x, z, obstacles, clearance, obstacle_r) -> bool:
    if wmesh.point_on_walkmesh(int(round(x)), int(round(z))) is None:
        return False
    if clearance > 0:
        d = wmesh.distance_to_boundary(int(round(x)), int(round(z)))
        if d is not None and d < clearance:
            return False
    r2 = obstacle_r * obstacle_r
    for ox, oz in obstacles:
        if (x - ox) ** 2 + (z - oz) ** 2 < r2:
            return False
    return True


def _clear(wmesh, a, b, obstacles, clearance, obstacle_r) -> bool:
    """Is the straight leg a->b fully free (sampled ~every clearance)?"""
    dx, dz = b[0] - a[0], b[1] - a[1]
    dist = (dx * dx + dz * dz) ** 0.5
    n = max(1, int(dist / max(8.0, clearance)))
    for k in range(n + 1):
        t = k / n
        if not _free(wmesh, a[0] + dx * t, a[1] + dz * t, obstacles, clearance, obstacle_r):
            return False
    return True


def _simplify(wmesh, pts, obstacles, clearance, obstacle_r) -> list:
    """String-pull a dense point list to a few waypoints (drop a point when you can see past it).
    Returns the waypoints AFTER the start, always ending at the exact goal (pts[-1])."""
    out, i = [], 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and not _clear(wmesh, pts[i], pts[j], obstacles, clearance, obstacle_r):
            j -= 1
        out.append(pts[j])
        i = j
    return out


def _nearest_free_cell(free_cell, gi, gj, span=6):
    """A free grid cell near (gi, gj) (the exact goal may sit within a margin of a wall/obstacle)."""
    if free_cell(gi, gj):
        return (gi, gj)
    for ring in range(1, span + 1):
        best = None
        for di in range(-ring, ring + 1):
            for dj in range(-ring, ring + 1):
                if max(abs(di), abs(dj)) != ring:
                    continue
                if free_cell(gi + di, gj + dj):
                    d = di * di + dj * dj
                    if best is None or d < best[0]:
                        best = (d, (gi + di, gj + dj))
        if best:
            return best[1]
    return None


class RouteLegError(ValueError):
    """A polyline leg that jams and cannot be auto-routed (or an endpoint is off-mesh).
    ``leg`` is the 0-based leg index; ``a``/``b`` its endpoints."""

    def __init__(self, leg: int, a, b, reason: str):
        self.leg, self.a, self.b, self.reason = leg, tuple(a), tuple(b), reason
        super().__init__(f"leg {leg + 1} ({a[0]:.0f},{a[1]:.0f})->({b[0]:.0f},{b[1]:.0f}): {reason}")


def route_polyline(wmesh, points, *, closed=False, obstacles=(), clearance=None):
    """Insert detour waypoints wherever a straight leg of ``points`` leaves the walkmesh.

    The jam oracle is the SAME sweep ``behavior lint`` and the layout probe run
    (:func:`ff9mapkit.scene.routes.sweep_polyline`), so what's routed == what's reported.
    Clear legs are left untouched (the authored points survive byte-for-byte); a jammed
    leg gets :func:`route`'s interior waypoints spliced in and the result is re-swept as
    a safety net. ``obstacles`` defaults to EMPTY: this is the static-feed router --
    walls are the only build-time truth (characters move), so it routes around geometry
    only. Returns ``(new_points, inserted)`` where ``inserted`` is
    ``[(leg_index, [detour waypoints])]``. Raises :class:`RouteLegError` when an input
    waypoint itself is off-mesh, a jammed leg has no route, or the routed polyline
    still fails the sweep."""
    from ..scene import routes as _routes
    clearance = _routes.WALL_CLEARANCE_W if clearance is None else clearance
    pts = [(float(p[0]), float(p[1])) for p in points]
    for i, (x, z) in enumerate(pts):
        if wmesh.point_on_walkmesh(int(round(x)), int(round(z))) is None:
            raise RouteLegError(max(0, i - 1), pts[i - 1] if i else pts[0], pts[i],
                                f"waypoint {i + 1} ({x:.0f},{z:.0f}) is itself OFF the "
                                f"walkmesh -- no route can fix an off-mesh target; move "
                                f"the point onto the floor")
    legs = _routes.sweep_polyline(pts, wmesh, [], closed=closed)   # spans only ([] skips
    # the boundary-distance pass -- OFF-MESH detection is bedges-independent)
    seq = pts + [pts[0]] if closed else pts             # seq[i]->seq[i+1] == legs[i]
    out, inserted = [], []
    for i, leg in enumerate(legs):
        out.append(seq[i])
        if not leg["spans"]:
            continue
        wps = route(wmesh, leg["a"], leg["b"], obstacles, clearance=clearance)
        if not wps:
            raise RouteLegError(i, leg["a"], leg["b"],
                                "OFF-MESH and NO route exists around the gap (the two "
                                "ends may be on disconnected floors)")
        detour = [(float(x), float(z)) for (x, z) in wps[:-1]]   # interior only; the
        out.extend(detour)                                       # authored goal stays
        inserted.append((i, [(int(x), int(z)) for (x, z) in detour]))
    if not closed:
        out.append(seq[-1])
    if inserted:                                        # verify: the routed line sweeps clean
        for j, leg in enumerate(_routes.sweep_polyline(out, wmesh, [], closed=closed)):
            if leg["spans"]:
                raise RouteLegError(j, leg["a"], leg["b"],
                                    "still OFF-MESH after routing (sweep/route sampling "
                                    "disagree) -- reroute this leg by hand")
    return [(int(round(x)), int(round(z))) for (x, z) in out], inserted


def route(wmesh, start, goal, obstacles=(), *, cell=64.0, clearance=None, obstacle_r=None,
          max_expand=20000):
    """Waypoints routing ``start``->``goal`` around walls + obstacles, or ``None`` if unreachable.

    Returns the interior waypoints + the exact goal (EXCLUDING start), suitable as a ``path``. Stays on
    the walkmesh, >= ``clearance`` from walls, >= ``obstacle_r`` from each obstacle centre. ``obstacles``
    is a list of (x, z) character centres."""
    clearance = cam.COLLISION_RADIUS_W if clearance is None else clearance
    obstacle_r = 2 * cam.OBJECT_COLLISION_W if obstacle_r is None else obstacle_r
    sx, sz = float(start[0]), float(start[1])
    gx, gz = float(goal[0]), float(goal[1])

    def cell_xz(i, j):
        return (sx + i * cell, sz + j * cell)

    def free_cell(i, j):
        x, z = cell_xz(i, j)
        return _free(wmesh, x, z, obstacles, clearance, obstacle_r)

    start_c = (0, 0)
    goal_c = _nearest_free_cell(free_cell, round((gx - sx) / cell), round((gz - sz) / cell))
    if goal_c is None:
        return None
    if start_c == goal_c:
        return [(int(round(gx)), int(round(gz)))]

    open_h = [(0.0, start_c)]
    came = {}
    g = {start_c: 0.0}
    expand = 0
    while open_h:
        _, c = heapq.heappop(open_h)
        if c == goal_c:
            break
        expand += 1
        if expand > max_expand:
            return None
        for di, dj in _NEIGHBORS:
            n = (c[0] + di, c[1] + dj)
            if n != goal_c and not free_cell(*n):       # start/goal cells are taken as given
                continue
            step = cell * (1.41421356 if di and dj else 1.0)
            ng = g[c] + step
            if ng < g.get(n, 1e18):
                g[n] = ng
                came[n] = c
                h = ((n[0] - goal_c[0]) ** 2 + (n[1] - goal_c[1]) ** 2) ** 0.5 * cell
                heapq.heappush(open_h, (ng + h, n))
    if goal_c not in came:
        return None

    chain = [goal_c]
    while chain[-1] in came:
        chain.append(came[chain[-1]])
    chain.reverse()                                     # start_c .. goal_c
    pts = [(sx, sz)] + [cell_xz(i, j) for (i, j) in chain[1:-1]] + [(gx, gz)]   # exact start..exact goal
    wps = _simplify(wmesh, pts, obstacles, clearance, obstacle_r)
    return [(int(round(x)), int(round(z))) for (x, z) in wps]
