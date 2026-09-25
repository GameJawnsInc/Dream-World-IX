"""Auto-pathing: route a blocked cutscene walk AROUND obstacles into clear straight legs.

A FF9 field walk is straight-line + synchronous, so it can't round a corner (off the walkmesh) or pass
a standing character (its collision box) on its own -- it presses into the obstacle and stalls. This
finds a route over the walkmesh that avoids both, then string-pulls it down to a few waypoints (which
the builder emits as a ``path``).

Grid A* over the walkmesh bounds: a cell is FREE if its centre is on the walkmesh, at least
``clearance`` from any wall (the player's controller radius), and at least ``obstacle_r`` from every
other character's centre (= the collision distance, so the actor never enters a box). Pure stdlib;
operates on a :class:`ff9mapkit.scene.bgi.BgiWalkmesh`.

KEEP-OUT POLYGONS (:func:`route_avoiding`): the same router can also refuse whole regions -- a field's
OTHER gateway zones, so a walk to one exit cannot step through another. A walker that crosses a gateway
region leaves the field; "the route grazed a door" is not a near miss, it is a different room.

THE PLAYER'S FLOOR (:class:`PlayerWalkmesh`): the triangles the engine refuses the controlled player (stock
door strips) are walls to a route planned for him -- opt-in, because an NPC's bar is a different bit.
"""

from __future__ import annotations

import heapq

from ..scene import cam, routes as _routes

_NEIGHBORS = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]


def _in_poly(x, z, poly) -> bool:
    """(x, z) inside the simple polygon ``poly`` ([(x, z), ...]), even-odd rule, top-down."""
    inside = False
    n = len(poly)
    for i in range(n):
        ax, az = poly[i]
        bx, bz = poly[(i + 1) % n]
        if (az > z) != (bz > z) and x < ax + (z - az) * (bx - ax) / (bz - az):
            inside = not inside
    return inside


def _crosses(a, b, c, d) -> bool:
    """Do segments a-b and c-d intersect (touching counts)? XZ, (x, z) tuples."""
    def orient(p, q, r):
        v = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return (v > 0) - (v < 0)

    def within(p, q, r):          # r on the line p-q: is it inside the p-q box?
        return min(p[0], q[0]) <= r[0] <= max(p[0], q[0]) and min(p[1], q[1]) <= r[1] <= max(p[1], q[1])

    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    if o1 != o2 and o3 != o4:
        return True
    return ((o1 == 0 and within(a, b, c)) or (o2 == 0 and within(a, b, d))
            or (o3 == 0 and within(c, d, a)) or (o4 == 0 and within(c, d, b)))


def poly_gap(x, z, poly) -> float:
    """Distance from (x, z) to polygon ``poly``; ``-1.0`` when the point is INSIDE it.

    Negative-inside rather than 0 so that ``gap < margin`` blocks the interior even at ``margin = 0``."""
    if _in_poly(x, z, poly):
        return -1.0
    n = len(poly)
    return min(_routes.seg_dist_xz(x, z, poly[i], poly[(i + 1) % n]) for i in range(n))


def seg_poly_gap(a, b, poly) -> float:
    """Closest approach of the straight leg a->b to polygon ``poly``; ``-1.0`` when the leg ENTERS it.

    Exact, not sampled (the lesson :func:`_clear` records for discs holds for polygons: a sampled test has
    no safe step against a leg that clips a corner)."""
    n = len(poly)
    if _in_poly(a[0], a[1], poly) or _in_poly(b[0], b[1], poly):
        return -1.0
    if any(_crosses(a, b, poly[i], poly[(i + 1) % n]) for i in range(n)):
        return -1.0
    # disjoint segments: the closest pair always has an endpoint of one of them in it -- BOTH ends of the
    # leg against every edge, every corner against the leg. (Leaving out the leg's END overstated the gap
    # whenever the leg stopped just short of an edge's middle: a probe judged 37.7u clear ended 10.6u off.)
    best = min(_routes.seg_dist_xz(p[0], p[1], poly[i], poly[(i + 1) % n]) for p in (a, b) for i in range(n))
    best = min(best, min(_routes.seg_dist_xz(p[0], p[1], a, b) for p in poly))
    return best


class Keepout:
    """A polygon the walker must not enter nor come within ``margin`` of (a gateway region, typically).

    ``leave=True`` is the region the walker STARTS IN (it arrived through that door): it may walk out of
    it -- once. Along the route the region's :meth:`level` (0 inside, 1 within ``margin``, 2 clear) never
    goes DOWN, so the route leaves the interior at most once and, once clear, never comes back within the
    margin. Dropping such a region instead let a route walk out of the door and later straight back in
    (stock 350 from inside its 353 zone to the 351 exit did). Monotone is a property of a step's
    DIRECTION, so a leaving region blocks no point, and :meth:`blocks_leg` reads a->b as walked from a.
    Checked at the leg's ends plus "no entry" / "one boundary cut" -- exact for a CONVEX region, where the
    distance along a straight leg is convex (all 1477 stock gateway zones are convex 3- or 4-gons).

    Built by :func:`route_avoiding`; the router tests cells with :meth:`blocks_point` and legs with
    :meth:`blocks_leg` (exact)."""

    __slots__ = ("poly", "margin", "box", "leave")

    def __init__(self, poly, margin: float, *, leave: bool = False):
        self.poly = tuple((float(p[0]), float(p[1])) for p in poly)
        if len(self.poly) < 3:
            raise ValueError(f"a keep-out region needs >= 3 corners, got {len(self.poly)}")
        self.margin = float(margin)
        self.leave = bool(leave)
        xs = [p[0] for p in self.poly]
        zs = [p[1] for p in self.poly]
        m = self.margin
        self.box = (min(xs) - m, min(zs) - m, max(xs) + m, max(zs) + m)

    def level(self, x, z) -> int:
        """0 inside the polygon, 1 outside but within ``margin`` of it, 2 clear."""
        gap = poly_gap(x, z, self.poly)
        return 0 if gap < 0 else (1 if gap < self.margin else 2)

    def blocks_point(self, x, z) -> bool:
        if self.leave:
            return False
        x0, z0, x1, z1 = self.box
        if not (x0 <= x <= x1 and z0 <= z <= z1):
            return False
        return poly_gap(x, z, self.poly) < self.margin

    def blocks_leg(self, a, b) -> bool:
        x0, z0, x1, z1 = self.box
        if max(a[0], b[0]) < x0 or min(a[0], b[0]) > x1 or max(a[1], b[1]) < z0 or min(a[1], b[1]) > z1:
            return False                                # wholly outside the margin box: clear either way
        if not self.leave:
            return seg_poly_gap(a, b, self.poly) < self.margin
        la, lb = self.level(*a), self.level(*b)
        if lb < la:
            return True                                 # back towards the door it already left
        if la == 2:
            return seg_poly_gap(a, b, self.poly) < self.margin
        if la == 1:
            return seg_poly_gap(a, b, self.poly) < 0     # outside already: never back in
        # from inside: stay inside (no boundary cut) or leave through exactly one -- a leg that cuts two
        # has left and come back (a vertex touch counts twice, so it is refused too: conservative)
        n = len(self.poly)
        cuts = sum(_crosses(a, b, self.poly[i], self.poly[(i + 1) % n]) for i in range(n))
        return cuts != (0 if lb == 0 else 1)

    def __repr__(self) -> str:
        return (f"Keepout({[(round(x), round(z)) for x, z in self.poly]}, margin={self.margin:.0f}"
                f"{', leave' if self.leave else ''})")

# How finely a leg is sampled against the MESH. Deliberately a constant, NOT derived from
# ``clearance``: tying the step to the wall radius means a bigger radius samples SPARSER, so the
# 2026-07-30 COLLISION_RADIUS_W correction (48 -> 80) silently coarsened this check from 48u to 80u
# and ``_simplify`` began string-pulling legs across features it no longer resolved. Matches
# ``routes.sweep_polyline``'s own step, so the router never checks coarser than the sweep that judges
# its output (:func:`route_polyline` re-sweeps every routed line through exactly that oracle).
_MESH_STEP_W = 40.0


def _free(wmesh, x, z, obstacles, clearance, obstacle_r, avoid=()) -> bool:
    if wmesh.point_on_walkmesh(int(round(x)), int(round(z))) is None:
        return False
    for k in avoid:
        if k.blocks_point(x, z):
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


def _clear(wmesh, a, b, obstacles, clearance, obstacle_r, avoid=()) -> bool:
    """Is the straight leg a->b fully free?

    Obstacles are discs, so they are tested EXACTLY (point-to-segment distance) rather than
    sampled -- the same oracle ``build._segment_hits_object`` uses to judge the emitted path. A
    sampled disc test has no safe step: a leg that clips the rim carries a chord ~``2*sqrt(2*R*d)``
    long, which vanishes as the penetration ``d`` does, so ANY step straddles some grazing leg.
    Measured: the demo-room route pulled a leg passing 188.6u from a character centre (192 required)
    and the 80u-stepped sample walked straight over the 72u chord -- the router emitted a path its
    own validator then rejected. The mesh/wall half still samples, at the radius-independent
    :data:`_MESH_STEP_W`. Keep-out polygons (``avoid``) are tested exactly too."""
    for ox, oz in obstacles:
        if _routes.seg_dist_xz(ox, oz, a, b) < obstacle_r:
            return False
    for k in avoid:
        if k.blocks_leg(a, b):
            return False
    dx, dz = b[0] - a[0], b[1] - a[1]
    dist = (dx * dx + dz * dz) ** 0.5
    n = max(1, int(dist / _MESH_STEP_W))
    for k in range(n + 1):
        t = k / n
        if not _free(wmesh, a[0] + dx * t, a[1] + dz * t, (), clearance, obstacle_r):
            return False
    return True


def _simplify(wmesh, pts, obstacles, clearance, obstacle_r, avoid=()) -> list:
    """String-pull a dense point list to a few waypoints (drop a point when you can see past it).
    Returns the waypoints AFTER the start, always ending at the exact goal (pts[-1])."""
    out, i = [], 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and not _clear(wmesh, pts[i], pts[j], obstacles, clearance, obstacle_r, avoid):
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
        if not leg["spans"] and not leg.get("jumps"):
            continue                                    # a floor break jams like a gap
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
            if leg.get("jumps"):
                jj = leg["jumps"][0]
                raise RouteLegError(
                    j, leg["a"], leg["b"],
                    f"the routed line still crosses floor "
                    f"{'+'.join(map(str, jj['from']))} -> {'+'.join(map(str, jj['to']))} "
                    f"away from any seam around ({jj['x']:.0f},{jj['z']:.0f}) -- the "
                    f"A* is floor-blind, so route this leg by hand THROUGH a real seam "
                    f"edge (add a waypoint on the seam)")
    return [(int(round(x)), int(round(z))) for (x, z) in out], inserted


#: The walker<->character collision distance, world units: two characters' OBJECT_COLLISION_W, centre to
#: centre. :func:`route`'s default ``obstacle_r``, and where the harness puts an unseen blocker it walked
#: into (``Session.route_to(unstick=True)``: this far ahead of where he stopped).
OBSTACLE_R_W = 2 * cam.OBJECT_COLLISION_W


def route(wmesh, start, goal, obstacles=(), *, cell=64.0, clearance=None, obstacle_r=None,
          max_expand=20000, avoid=()):
    """Waypoints routing ``start``->``goal`` around walls + obstacles, or ``None`` if unreachable.

    Returns the interior waypoints + the exact goal (EXCLUDING start), suitable as a ``path``. Stays on
    the walkmesh, >= ``clearance`` from walls, >= ``obstacle_r`` from each obstacle centre. ``obstacles``
    is a list of (x, z) character centres. ``avoid`` is a list of :class:`Keepout` -- use
    :func:`route_avoiding`, which builds them (and exempts the region the walker starts in)."""
    clearance = cam.COLLISION_RADIUS_W if clearance is None else clearance
    obstacle_r = OBSTACLE_R_W if obstacle_r is None else obstacle_r
    sx, sz = float(start[0]), float(start[1])
    gx, gz = float(goal[0]), float(goal[1])

    def cell_xz(i, j):
        return (sx + i * cell, sz + j * cell)

    # A* asks about a cell once per neighbour that reaches it; the answer is fixed for this call, and the
    # wall-distance query behind it is the router's whole cost (a full sweep of stock 350 at cell 8:
    # 47s unmemoised, 9s memoised) -- which is what makes route_avoiding's finer retries affordable.
    known: dict = {}

    def free_cell(i, j):
        v = known.get((i, j))
        if v is None:
            x, z = cell_xz(i, j)
            v = known[(i, j)] = _free(wmesh, x, z, obstacles, clearance, obstacle_r, avoid)
        return v

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
            # two free cells can still have a keep-out CORNER between them (a diagonal step cuts it),
            # and the string-pull keeps adjacent steps unchecked -- so the step itself is tested
            if avoid and any(k.blocks_leg(cell_xz(*c), cell_xz(*n)) for k in avoid):
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
    wps = _simplify(wmesh, pts, obstacles, clearance, obstacle_r, avoid)
    return [(int(round(x)), int(round(z))) for (x, z) in wps]


#: Default keep-out margin around an avoided region, world units. Wider than one run frame (30u) so the
#: walker's own overshoot cannot carry it in; narrower than the controller radius (80u), because a
#: margin wider than a doorway's approach corridor would seal off exits that share a wall.
KEEPOUT_MARGIN_W = 56.0

#: How many times :func:`route_avoiding` halves the grid before calling a goal unreachable (64 -> 32 ->
#: 16 -> 8). Measured on stock 352, the tour's first room: its only way out is a corner-to-corner pinch
#: whose widest standable spot is 82.3u from both walls against the 80u controller radius, and from 40 of
#: 47 starts in the inn room no cell centre of a start-aligned 64 or 32 grid lands in that band; 8 routed
#: all 106 sampled starts. The price is paid only by a goal no grain reaches: a whole-field sweep at every
#: grain, ~12s on 350, the largest Dali field.
ROUTE_REFINES = 3


def route_avoiding(wmesh, start, goal, avoid_polygons, margin: float = KEEPOUT_MARGIN_W, *,
                   obstacles=(), cell=64.0, clearance=None, obstacle_r=None, max_expand=20000):
    """:func:`route` that also keeps out of every polygon in ``avoid_polygons`` (and ``margin`` around it).

    Returns the waypoints after ``start`` ending at the exact ``goal``, or ``None`` when no such route
    exists -- including when the goal itself lies in (or within the margin of) an avoided region.
    ``obstacles`` (character centres, kept ``obstacle_r`` clear) are an ADDITIONAL constraint: they never
    relax a keep-out -- a route that goes round one still stays out of every avoided region.

    THE START IS EXEMPT, because the walker is where it is -- but only as far as it has to be. A polygon
    CONTAINING the start becomes a leaving :class:`Keepout`: the route may walk out of it once and never
    back in (it stands in the arrival door and must be able to leave it); a polygon the start sits within
    ``margin`` of keeps its interior but its margin shrinks to the start's own distance, so the route may
    leave the door's side without ever getting closer to it. Every leg -- the string-pulled ones and the two
    the grid does not choose (start -> first cell, last cell -> exact goal) -- is re-checked exactly.

    THE GRID IS ALIGNED ON THE START, so a passage barely wider than twice the clearance can fall between
    cell centres. A miss is retried at half the cell, :data:`ROUTE_REFINES` times, before it is called
    unreachable.

    On a :class:`PlayerWalkmesh` the start is exempt from the closed triangles too: the strip he stands in is
    open to him (:meth:`PlayerWalkmesh.standing_at`)."""
    sx, sz = float(start[0]), float(start[1])
    gx, gz = float(goal[0]), float(goal[1])
    if isinstance(wmesh, PlayerWalkmesh):
        wmesh = wmesh.standing_at(sx, sz)
    keep = []
    for poly in avoid_polygons:
        gap = poly_gap(sx, sz, [(float(p[0]), float(p[1])) for p in poly])
        if gap < 0:
            keep.append(Keepout(poly, float(margin), leave=True))     # standing in it: walk out, once
            continue
        # half a unit under the start's own gap, so the float error of a leg measured FROM the start
        # cannot read as the start approaching its own door
        keep.append(Keepout(poly, min(float(margin), max(0.0, gap - 0.5))))
    if any(k.blocks_point(gx, gz) for k in keep):
        return None
    for k in range(ROUTE_REFINES + 1):
        wps = route(wmesh, (sx, sz), (gx, gz), obstacles, cell=cell / 2 ** k, clearance=clearance,
                    obstacle_r=obstacle_r, max_expand=max_expand * 4 ** k, avoid=keep)
        if wps is None:
            continue
        legs = [(sx, sz)] + [(float(x), float(z)) for (x, z) in wps]
        if not any(kp.blocks_leg(legs[i], legs[i + 1]) for i in range(len(legs) - 1) for kp in keep):
            return wps
    return None


def region_goal(wmesh, polygon, *, clearance=None, step: float = 24.0):
    """A point to WALK TO in order to enter trigger ``polygon``: inside it, on the walkmesh, and standable.

    A gateway zone usually straddles the walkmesh edge (its corners are off-mesh) and its corner-average
    can be off-mesh too, while the player's CENTRE never gets within ``clearance`` (the controller radius)
    of a wall. So: sample the polygon, keep the points on the mesh, prefer the ones >= ``clearance`` from
    every wall, and among those take the one DEEPEST inside the polygon (steering error then still lands
    inside). With no standable sample, the on-mesh sample nearest to standable. ``None`` = the polygon
    does not touch the walkmesh at all (no walk can fire it). Returns ``(x, z)`` ints."""
    clearance = cam.COLLISION_RADIUS_W if clearance is None else clearance
    poly = [(float(p[0]), float(p[1])) for p in polygon]
    n = len(poly)
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    best = None
    x = min(xs) + step / 2
    while x < max(xs):
        z = min(zs) + step / 2
        while z < max(zs):
            if _in_poly(x, z, poly) and wmesh.point_on_walkmesh(int(round(x)), int(round(z))) is not None:
                wall = wmesh.distance_to_boundary(int(round(x)), int(round(z)))
                wall = 0.0 if wall is None else wall
                depth = min(_routes.seg_dist_xz(x, z, poly[i], poly[(i + 1) % n]) for i in range(n))
                key = (1, depth) if wall >= clearance else (0, wall)
                if best is None or key > best[0]:
                    best = (key, (int(round(x)), int(round(z))))
            z += step
        x += step
    return None if best is None else best[1]


#: The triFlags high-byte bit the engine refuses to the CONTROLLED player: WalkMesh.BGI_findAccessibleTriangle
#: (and RadiusValid, which walls such an edge at his radius like any other) tests ``(triFlags >> 8) &
#: attributeMask & 0x80``, and ``attributeMask`` is 255 in play -- a script lowers it to 127
#: (SetTriangleFlagMask) only for its own scripted walk through a door. 0x40 is the same bar for everyone
#: else, and a triangle whose low bit is clear is closed to all.
TRI_PLAYER_CLOSED = 0x80


class PlayerWalkmesh:
    """A walkmesh as the CONTROLLED PLAYER may walk it: its triangles minus the ones the engine refuses him.

    Stock door strips are such triangles (``triFlags`` 0xA001 across Dali's doorways: 350, 351, 352, 353,
    356, 357), and :class:`BgiWalkmesh` knows nothing of the rule -- to it they are floor. A route or a
    :func:`region_goal` over the raw mesh can therefore aim at a point he can never stand on: stock 356's
    exit to 358 stalled four times exactly COLLISION_RADIUS_W off triangle 50's edge, pressing into a wall
    the router did not have. Here a closed triangle is not floor (:meth:`point_on_walkmesh` skips it) and
    every edge an open triangle shares with one is a WALL (:meth:`distance_to_boundary`), which is all
    :func:`route`, :func:`route_avoiding` and :func:`region_goal` ask of a walkmesh.

    An explicit wrapper, not a change to the router: an NPC is not the controlled player (its bar is 0x40),
    so the kit's build-time routing keeps the raw mesh. ``mask`` is the attributeMask to assume; ``opened``
    triangles count as open whatever their flags (:meth:`standing_at`)."""

    def __init__(self, wmesh, mask: int = 0xFF, opened=()):
        from ..scene import bgi
        self.mesh = wmesh
        self.mask = mask
        tris = wmesh.tris
        self.closed = frozenset(i for i, t in enumerate(tris) if i not in opened
                                and (not t.tri_flags & 1 or (t.tri_flags >> 8) & mask & TRI_PLAYER_CLOSED))
        wv = wmesh.world_verts()
        self._floor = wmesh._tri_floor()
        walls: dict = {}
        for ti, t in enumerate(tris):
            if ti in self.closed:
                continue
            segs = walls.setdefault(self._floor.get(ti, t.floor_ndx), [])
            for k, (i, j) in enumerate(bgi.SLOT_PAIRS):
                if 0 <= t.nbr[k] < len(tris) and t.nbr[k] not in self.closed:
                    continue                            # an open neighbour across this edge: not a wall
                a, b = wv[t.vtx[i]], wv[t.vtx[j]]
                segs.append(((a[0], a[2]), (b[0], b[2])))
        self._walls = walls

    def point_on_walkmesh(self, x, z):
        """Floor index of the first OPEN triangle containing (x, z), else None (off-mesh, or closed to him)."""
        for ti in self.mesh.tris_at(x, z):
            if ti not in self.closed:
                return self._floor.get(ti, self.mesh.tris[ti].floor_ndx)
        return None

    def distance_to_boundary(self, x, z):
        """Min XZ distance from (x, z) to a wall of its floor -- a mesh boundary or the edge of a closed
        triangle. None off the open floor."""
        floor = self.point_on_walkmesh(x, z)
        if floor is None:
            return None
        return min((_routes.seg_dist_xz(x, z, a, b) for a, b in self._walls.get(floor, ())), default=None)

    def standing_at(self, x, z) -> "PlayerWalkmesh":
        """This view with the closed STRIP he stands in opened -- every closed triangle linked to the one
        under (x, z) through other closed ones. Only a script puts him there: its walk through a door ran at
        mask 127, a mask the router cannot see, and the strip is the way out that walk was taking. (At 255
        the engine bars only ENTERING a closed triangle -- BGI_findAccessibleTriangle judges the neighbour
        across an edge -- so a route out through the strip may still stall; it cannot be worse than the
        raw mesh, which ignores every strip.) :func:`route_avoiding` asks for this at its start."""
        todo = list(self.closed.intersection(self.mesh.tris_at(x, z)))
        strip = set(todo)
        while todo:
            for n in self.mesh.tris[todo.pop()].nbr:
                if n in self.closed and n not in strip:
                    strip.add(n)
                    todo.append(n)
        return PlayerWalkmesh(self.mesh, self.mask, opened=strip) if strip else self
