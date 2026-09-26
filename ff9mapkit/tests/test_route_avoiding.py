"""Routing that keeps out of gateway regions (``content.pathfind.route_avoiding``) -- and the FRAME it rests on.

The harness's blind exit tour (studies/story-trace/rung3_step1.py) arrived in stock Dali 350 from 351 standing
18u from 351's own gateway, and every walk toward the next exit stepped straight back through it: 80 field
visits of 350 <-> 351. The fix routes over the field's REAL walkmesh and keeps out of every gateway zone it was
not sent to. Two things must hold for that to mean anything, and both are pinned here against real bytes:

  * THE FRAME. The harness publishes ``po.pos`` (``state.player_x/z``); the router runs on
    ``BgiWalkmesh.world_verts`` (``vert + orgPos + floor.org``); the zones are ``SetRegion`` literals. Recorded
    in-game positions (``.harness-runs/*`` states-final.jsonl, the stuck run's state.json) must stand ON the
    install's walkmesh; arrivals must equal the script's own D9 x/z literals exactly; a wall slide must sit at
    the controller radius from the boundary -- and a shifted frame must FAIL the same check (a check that
    cannot fail proves nothing).
  * THE ROUTES. On stock 350 from the 351-door arrival, 351 from its stuck landing and 450 from beside its
    350 door: a route to every other exit exists, and no waypoint or string-pulled leg enters an avoided zone.

Install-gated (THE WORKTREE SKIP TRAP): without a readable game install the real-bytes tests WARN and skip.
The synthetic tests run everywhere.
"""
from __future__ import annotations

import math
import warnings

import pytest

from ff9mapkit.content import pathfind as P
from ff9mapkit.scene import bgi, cam, routes


def _floor(x0, z0, x1, z1):
    """A flat rectangular walkmesh in WORLD coords (bgi.build: orgPos = 0, so world = authored)."""
    c = [(x0, 0, z1), (x1, 0, z1), (x1, 0, z0), (x0, 0, z0)]
    return bgi.BgiWalkmesh.from_bytes(bgi.build(c, [(0, 1, 2), (0, 2, 3)]).to_bytes())


def _rect(x0, z0, x1, z1):
    return [[x0, z0], [x1, z0], [x1, z1], [x0, z1]]


def _legs_clear(start, wps, polys, margin=0.0):
    """Every leg of start->wps keeps >= margin from every polygon (exact: P.seg_poly_gap, -1 = enters)."""
    pts = [tuple(map(float, start))] + [tuple(map(float, w)) for w in wps]
    return all(P.seg_poly_gap(pts[i], pts[i + 1], p) >= margin
               for i in range(len(pts) - 1) for p in polys)


# ======================================================================= synthetic (runs everywhere)
ROOM = _floor(-1000, -1000, 1000, 1000)


def test_a_route_goes_round_a_region_the_straight_line_crosses():
    door = _rect(-150, -150, 150, 150)                       # dead centre, between start and goal
    start, goal = (-700, 0), (700, 0)
    assert P.seg_poly_gap(start, goal, door) < 0              # the straight walk would take the door
    wps = P.route_avoiding(ROOM, start, goal, [door], 56)
    assert wps and tuple(wps[-1]) == goal
    assert _legs_clear(start, wps, [door], 56 - 1e-6)
    assert all(not P.Keepout(door, 56).blocks_point(*w) for w in wps)


def test_the_region_the_walker_stands_in_is_exempt():
    """The arrival door: standing IN it, the walker must be able to walk out through it."""
    door = _rect(-900, -100, -600, 100)
    start = (-750, 0)                                         # inside the door region
    wps = P.route_avoiding(ROOM, start, (500, 0), [door], 56)
    assert wps and tuple(wps[-1]) == (500, 0)


def _band(a, b, half):
    """A thin convex quad of half-width ``half`` along a->b."""
    dx, dz = b[0] - a[0], b[1] - a[1]
    n = (dx * dx + dz * dz) ** 0.5
    nx, nz = -dz / n * half, dx / n * half
    return [[a[0] + nx, a[1] + nz], [b[0] + nx, b[1] + nz], [b[0] - nx, b[1] - nz], [a[0] - nx, a[1] - nz]]


def test_the_region_the_walker_stands_in_may_be_left_once_and_never_re_entered():
    """Exempting the start's region by DROPPING it let the route walk out of the door and later straight
    back in (stock 350: from inside its 353 zone, the route to the 351 exit re-crossed it). Here a wall
    forces a bend over its top, and the start's door is a thin band reaching across the wall to the bend's
    far leg: the route that forgets the door re-enters it; the route that leaves it may not."""
    wall = _rect(-100, -1000, 100, 500)
    door = _band((-340, -20), (240, 290), 40)
    start, goal = (-300, 0), (300, 0)
    assert P.poly_gap(*start, door) < 0                       # standing in it
    forgot = [start] + P.route_avoiding(ROOM, start, goal, [wall], 56)
    assert any(P.seg_poly_gap(a, b, door) < 0 for a, b in zip(forgot[1:], forgot[2:])), \
        "premise: a later leg of the door-blind route walks back into the door"
    wps = P.route_avoiding(ROOM, start, goal, [wall, door], 56)
    assert wps and tuple(wps[-1]) == goal
    legs = list(zip([start] + wps[:-1], wps))
    assert P.poly_gap(*legs[0][1], door) >= 56                # the first leg walks out, clear
    assert all(P.seg_poly_gap(a, b, door) >= 56 - 1e-6 for a, b in legs[1:])


def test_a_leaving_region_blocks_by_direction():
    """``Keepout(leave=True)``: its level (0 inside, 1 within the margin, 2 clear) may only rise along a leg."""
    k = P.Keepout(_rect(-100, -100, 100, 100), 50, leave=True)
    assert not k.blocks_point(0, 0) and not k.blocks_point(130, 0)   # no POINT is refused
    assert not k.blocks_leg((0, 0), (50, 0))                  # inside -> inside
    assert not k.blocks_leg((0, 0), (300, 0))                 # out through one edge, clear
    assert k.blocks_leg((130, 0), (50, 0))                    # back in from the margin
    assert k.blocks_leg((300, 0), (130, 0))                   # back within the margin once clear
    assert k.blocks_leg((300, 0), (-300, 0))                  # straight through from outside
    assert not k.blocks_leg((130, 0), (130, 300))             # along the margin, not closer in level


def test_beside_a_region_the_route_never_gets_closer_to_it():
    """18u from the door (stock 350's arrival): the margin shrinks to 18, not to zero -- the route may leave
    the door's side but never approach it -- and a goal PAST the door is refused rather than walked through."""
    door = _rect(0, -200, 300, 200)
    start = (-18, 0)
    wps = P.route_avoiding(ROOM, start, (-700, 0), [door], 56)
    assert wps and _legs_clear(start, wps, [door], 17.0)
    around = P.route_avoiding(ROOM, start, (700, 0), [door], 56)
    assert around is not None, "the room is open above and below the door: there IS a way round"
    assert _legs_clear(start, around, [door], 17.0)
    assert len(around) > 1                                    # not the straight line through the door


def test_a_goal_inside_an_avoided_region_has_no_route():
    door = _rect(400, -100, 600, 100)
    assert P.route_avoiding(ROOM, (-500, 0), (500, 0), [door], 56) is None
    assert P.route_avoiding(ROOM, (-500, 0), (500 - 100 - 30, 0), [door], 56) is None   # inside the margin


def test_a_leg_that_clips_a_corner_is_caught_exactly():
    """A sampled leg test has no safe step against a corner clip; the keep-out test is exact."""
    square = _rect(0, 0, 100, 100)
    assert P.seg_poly_gap((-10, 95), (95, -10), square) < 0   # clips the (0, 0) corner by a few units
    assert P.seg_poly_gap((-10, 50), (-10, 150), square) == pytest.approx(10.0)
    assert P.Keepout(square, 11).blocks_leg((-10, 50), (-10, 150))
    assert not P.Keepout(square, 9).blocks_leg((-10, 50), (-10, 150))


def test_a_leg_that_ENDS_closest_to_an_edge_is_measured_from_its_end():
    """The closest approach can be the leg's END against the middle of an edge. Measured from the start and
    the corners only, this leg read 27.9u clear of the square it stops 10u short of -- the shape of a
    calibration probe judged 37.7u clear of stock 356's 350 door that ended 10.6u from it."""
    square = _rect(0, 0, 100, 100)
    assert P.seg_poly_gap((-50, 150), (50, 110), square) == pytest.approx(10.0)
    assert P.seg_poly_gap((50, 110), (-50, 150), square) == pytest.approx(10.0)    # either direction
    assert P.Keepout(square, 20).blocks_leg((-50, 150), (50, 110))


def test_route_without_avoid_is_unchanged():
    """``route`` and the two helpers it shares with the whole kit keep their positional contract."""
    wps = P.route(ROOM, (-700, 0), (700, 0))
    assert wps == [(700, 0)]
    assert P._clear(ROOM, (-700, 0), (700, 0), [], cam.COLLISION_RADIUS_W, 192.0)
    assert P._free(ROOM, 0, 0, [], cam.COLLISION_RADIUS_W, 192.0)


def test_an_obstacle_may_carry_its_own_radius():
    """``(x, z, r)`` is kept its own ``r`` clear, a bare ``(x, z)`` still ``obstacle_r`` -- the harness plans the
    engine's published objects, whose collision radii differ, in the same call as its unseen blockers
    (``Session.route_to(npcs=True)``)."""
    from ff9mapkit.scene import routes
    start, goal = (-700, 0), (700, 0)
    assert P.route(ROOM, start, goal, [(0, 300)]) == [(700, 0)]          # 300 > obstacle_r 192: straight on
    assert P.route(ROOM, start, goal, [(0, 300, 280)]) == [(700, 0)]
    for obstacles in ([(0, 300, 320)], [(0, 300, 320), (0, -700)]):
        wps = P.route_avoiding(ROOM, start, goal, [], obstacles=obstacles)
        pts = [start] + [tuple(w) for w in wps]
        assert len(wps) > 1 and all(routes.seg_dist_xz(0, 300, a, b) >= 320 - 1e-6 for a, b in zip(pts, pts[1:]))
    assert not P._free(ROOM, 0, 0, [(0, 300, 320)], cam.COLLISION_RADIUS_W, 192.0)
    assert P._free(ROOM, 0, 0, [(0, 300)], cam.COLLISION_RADIUS_W, 192.0)



def test_a_memo_answers_the_floor_once_for_every_route_from_one_start():
    """``memo`` (route_avoiding): several routes planned from ONE start -- other obstacle sets, as the harness plans a
    field's published objects tier by tier -- share the grid's cell centres, so each point's floor and wall answer is
    asked of the walkmesh once. The routes are the same with it as without; a second plan from that start asks the
    walkmesh nothing new; and a plan from another start keeps its own answers (on a PlayerWalkmesh the view differs by
    start)."""
    asked = []

    class Counted:
        def point_on_walkmesh(self, x, z):
            asked.append(("on", x, z))
            return ROOM.point_on_walkmesh(x, z)

        def distance_to_boundary(self, x, z):
            asked.append(("wall", x, z))
            return ROOM.distance_to_boundary(x, z)
    door = _rect(-150, -150, 150, 150)
    start, goal = (-700, 0), (700, 0)
    memo: dict = {}
    for obstacles in ([], [(0, 400, 300)], [(0, -400, 300), (0, 400, 300)]):
        assert P.route_avoiding(Counted(), start, goal, [door], 56, obstacles=obstacles, memo=memo) ==             P.route_avoiding(ROOM, start, goal, [door], 56, obstacles=obstacles)
    asked.clear()
    P.route_avoiding(Counted(), start, goal, [door], 56, obstacles=[(0, 400, 300)], memo=memo)
    assert asked == [], asked[:5]
    P.route_avoiding(Counted(), (-700, 100), goal, [door], 56, memo=memo)
    assert asked and set(memo) == {(-700.0, 0.0), (-700.0, 100.0)}

def test_region_goal_is_inside_the_region_and_standable():
    door = _rect(800, -200, 1200, 200)                       # straddles the room's east edge (x = 1000)
    g = P.region_goal(ROOM, door)
    assert g is not None
    assert P.poly_gap(g[0], g[1], door) < 0                   # inside the trigger
    assert ROOM.distance_to_boundary(*g) >= cam.COLLISION_RADIUS_W - 1   # where a player centre can stand
    assert P.region_goal(ROOM, _rect(1100, -200, 1300, 200)) is None     # off the mesh entirely


def _strip():
    """A room in three columns; the middle one (x -100..100, triangles 2 and 3) is a door strip with stock Dali's
    triFlags 0xA001 -- closed to the controlled player at attributeMask 255."""
    v = [(-1000, 0, 1000), (-100, 0, 1000), (100, 0, 1000), (1000, 0, 1000),
         (-1000, 0, -1000), (-100, 0, -1000), (100, 0, -1000), (1000, 0, -1000)]
    f = [(0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6)]
    wm = bgi.BgiWalkmesh.from_bytes(bgi.build(v, f).to_bytes())
    for ti in (2, 3):
        wm.tris[ti].tri_flags = 0xA001
    return wm


def test_the_players_walkmesh_walls_off_a_triangle_closed_to_him():
    """THE 356 -> 358 STALL, synthetic: the raw mesh routes straight through a door strip the engine refuses
    the player; his view has no floor there, walls its edges at his radius, and aims a region goal off it."""
    wm = _strip()
    view = P.PlayerWalkmesh(wm)
    assert view.closed == {2, 3}
    assert wm.point_on_walkmesh(0, 0) is not None and view.point_on_walkmesh(0, 0) is None
    assert view.point_on_walkmesh(-500, 0) == wm.point_on_walkmesh(-500, 0)
    assert wm.distance_to_boundary(-180, 0) == pytest.approx(820)
    assert view.distance_to_boundary(-180, 0) == pytest.approx(80)       # the strip's edge is a wall now
    assert P.route_avoiding(wm, (-700, 0), (700, 0), []) is not None
    assert P.route_avoiding(view, (-700, 0), (700, 0), []) is None
    door = _rect(-300, -200, 300, 200)                                  # a zone straddling the strip
    assert abs(P.region_goal(wm, door)[0]) < 100                        # the raw goal: in the strip
    g = P.region_goal(view, door)
    assert view.point_on_walkmesh(*g) is not None and view.distance_to_boundary(*g) >= cam.COLLISION_RADIUS_W - 1
    assert P.PlayerWalkmesh(wm, mask=127).closed == frozenset()         # a script's door walk opens it
    for ti in (2, 3):
        wm.tris[ti].tri_flags = 0x4001                                  # 0x40 bars everyone ELSE
    assert P.PlayerWalkmesh(wm).closed == frozenset()


def test_the_players_walkmesh_opens_the_strip_he_stands_in():
    """A script can leave him inside a strip (its walk ran at mask 127, which the router cannot see): the route
    starts there and leaves it. The exemption is the start's alone -- walking up to the strip, it is still shut."""
    wm = _strip()
    view = P.PlayerWalkmesh(wm)
    assert view.standing_at(-500, 0) is view
    assert view.standing_at(0, 0).closed == frozenset()
    wps = P.route_avoiding(view, (0, 0), (700, 0), [])
    assert wps is not None and tuple(wps[-1]) == (700, 0)
    assert P.route_avoiding(view, (-700, 0), (700, 0), []) is None


def _along(start, wps, step=2.0):
    """Points every ``step`` units along the walk start -> wps, the corners included."""
    pts = [tuple(map(float, start))] + [tuple(map(float, w)) for w in wps]
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(math.dist(a, b) // step))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(1, n + 1)]
    return out


def _band_exit(wm, start, wps, clearance=cam.COLLISION_RADIUS_W):
    """Walk start -> wps as ``leave_wall`` promises it, from a start ``d0`` < ``clearance`` off the walls. EITHER its
    first leg is one step of the coarsest grid (64 * sqrt 2 at most) straight onto a spot ``clearance`` clear -- the
    start is taken as given, as it always was (:func:`_walked_on_the_floor` holds that step to no wall) -- OR it walks
    never nearer a wall than it has been, out of the band -- ``clearance`` off every wall -- within
    ``(clearance - d0) / WALL_LEAVE_GAIN`` of walking. Measured every 2u at the exact point, as the rule is judged;
    the slack is what the rule's own sampling may leave: 1u deeper between two of its samples 4u apart (the wall
    distance moves at most a unit per unit walked, so a quarter of the spacing), and 4u of walking (this walk's 2u
    sampling, twice). A fixed 1u, not pathfind's _BAND_STEP_W / 4: a slack read off the code under test widens with
    it. Returns (how far it walked in the band, the samples after it)."""
    d0 = wm.distance_to_boundary(*start)
    assert d0 is not None and d0 < clearance, "premise: the start stands inside the band"
    first = tuple(map(float, wps[0]))
    if math.dist(start, first) <= 64 * 2 ** 0.5 + 1 and wm.distance_to_boundary(*first) >= clearance:
        return math.dist(start, first), _along(first, wps[1:])
    pts = _along(start, wps)
    level, walked = d0, 0.0
    for i in range(1, len(pts)):
        d = wm.distance_to_boundary(*pts[i])
        assert d is not None and d >= level - 1.0, (pts[i], d, level)            # never deeper
        walked += math.dist(pts[i - 1], pts[i])
        level = max(level, d)
        if d >= clearance:
            assert walked <= (clearance - d0) / P.WALL_LEAVE_GAIN + 4.0, (walked, d0)    # out, not along
            return walked, pts[i:]
    raise AssertionError("the walk never left the band")


def _walked_on_the_floor(wm, start, wps):
    """Every point of the walk start -> wps, 1u apart, stands on ``wm``'s floor (a PlayerWalkmesh's: its closed
    triangles are no floor), and each steps to the next within one triangle or across an edge the two LINK -- the
    engine walks triangle to triangle. Never through a wall, however thin: past an unlinked edge the far side is floor
    too, and only the link tells the step from a crossing. A step whose ends do not link is halved until the
    triangles between them show (a sliver, a fan round a corner the walk passes close to) or the crossing is pinned
    to a point, which must be a corner both sides touch. Which triangles he is on narrows to those the walk reaches:
    a point ON an unlinked edge lies in both triangles, and must not carry him across."""
    mesh = getattr(wm, "mesh", wm)
    closed = getattr(wm, "closed", frozenset())
    wv = mesh.world_verts()

    def under(p):
        return {t for t in mesh.tris_at(p[0], p[1]) if t not in closed}

    def corners(tris):
        return {(wv[i][0], wv[i][2]) for t in tris for i in mesh.tris[t].vtx}

    def walk(a, here, b, depth=0):
        """The triangles at b that the walk a -> b reaches from ``here`` (empty: it cannot)."""
        there = under(b)
        reach = there & (here | {n for t in here for n in mesh.tris[t].nbr})
        if reach or not there:
            return reach
        if depth == 12:
            shared = corners(here) & corners(there)
            return there if any(routes.seg_dist_xz(c[0], c[1], a, b) < 0.01 for c in shared) else set()
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        mid = walk(a, here, m, depth + 1)
        return walk(m, mid, b, depth + 1) if mid else set()

    pts = _along(start, wps, 1.0)
    here = under(pts[0])
    assert here, f"the start {start} is off the floor"
    for a, b in zip(pts, pts[1:]):
        assert under(b), f"off the floor at {b}"
        reached = walk(a, here, b)
        assert reached, f"through a wall between {a} and {b}: {sorted(here)} -> {sorted(under(b))}"
        here = reached


@pytest.mark.parametrize("start, goal", [((-990, -500), (-900, 500)),     # 10u off a wall, the goal up along it
                                         ((-990, -990), (0, 0))])         # 10u off both walls of a corner
def test_a_start_inside_the_wall_band_walks_out_of_it_never_deeper_nor_along_it(start, goal):
    """THE 352 WAKE, synthetic. A scene can hand control back with his centre nearer a wall than the controller
    radius (stock 352: 22.8u off a closed strip's edge); the engine pushes him straight back out to it when he
    moves. Every cell within 64u of a start 10u off the wall is itself inside the band, so the planner that treats
    the start like any other cell -- the build's -- has nowhere to step, at every grain. ``leave_wall`` plans out:
    never nearer a wall, out within (80 - 10) / WALL_LEAVE_GAIN of walking, and clear from there on. The walk
    straight up the wall never gets deeper either -- and never gets out: refused."""
    assert P.route(ROOM, start, goal) is None                            # the build's rule, unchanged
    assert P.route_avoiding(ROOM, start, goal, []) is None
    wps = P.route_avoiding(ROOM, start, goal, [], leave_wall=True)
    assert wps and tuple(wps[-1]) == goal
    _walked, after = _band_exit(ROOM, start, wps)
    assert all(ROOM.distance_to_boundary(round(x), round(z)) >= cam.COLLISION_RADIUS_W - 1.0 for x, z in after)
    assert not P._clear(ROOM, (-990, -500), (-990, 500), (), cam.COLLISION_RADIUS_W, 192.0, leave_wall=True)
    assert not P._clear(ROOM, (-990, -500), (-900, 500), (), cam.COLLISION_RADIUS_W, 192.0, leave_wall=True)
    assert P._clear(ROOM, (-990, -500), (-800, -500), (), cam.COLLISION_RADIUS_W, 192.0, leave_wall=True)


def test_leaving_the_wall_band_keeps_the_zones_and_the_bodies():
    """The way straight out of the band is a gateway (kept 56 clear) and someone stands beside it: the route
    leaves the band round both, enters neither -- and from a start already clear of the walls ``leave_wall``
    changes nothing."""
    from ff9mapkit.scene import routes
    start, goal = (-990, 0), (500, 0)
    door, body = _rect(-850, -60, -650, 60), (-880, 260, 150)
    wps = P.route_avoiding(ROOM, start, goal, [door], 56, obstacles=[body], leave_wall=True)
    assert wps and tuple(wps[-1]) == goal
    assert _legs_clear(start, wps, [door], 56 - 1e-6)
    pts = [start] + [tuple(w) for w in wps]
    assert all(routes.seg_dist_xz(body[0], body[1], a, b) >= body[2] - 1e-6 for a, b in zip(pts, pts[1:]))
    _band_exit(ROOM, start, wps)
    for s in ((-700, 0), (-700, 400)):
        assert (P.route_avoiding(ROOM, s, goal, [door], 56, obstacles=[body], leave_wall=True)
                == P.route_avoiding(ROOM, s, goal, [door], 56, obstacles=[body]))


def test_leaving_the_wall_band_on_the_players_floor_keeps_the_closed_strip_shut():
    """His floor (PlayerWalkmesh): he stands 10u off a door strip closed to him -- its edge is a wall -- and the goal
    lies up along it, so the shortest walk would hug the strip. The way out of the band is AWAY from the strip,
    never into it nor along it; every point of the route is on the floor open to him."""
    view = P.PlayerWalkmesh(_strip())
    start, goal = (-110, -500), (-200, 600)
    assert view.distance_to_boundary(*start) == pytest.approx(10)
    assert P.route_avoiding(view, start, goal, []) is None
    wps = P.route_avoiding(view, start, goal, [], leave_wall=True)
    assert wps and tuple(wps[-1]) == goal
    _walked_on_the_floor(view, start, wps)
    _band_exit(view, start, wps)


def _two_rooms():
    """Two rooms meeting along x = 0 with no link between them (each its own vertices -- bgi.build links only
    shared ones): a zero-width wall, floor on both sides of it."""
    v = [(-1000, 0, 1000), (0, 0, 1000), (0, 0, -1000), (-1000, 0, -1000),
         (0, 0, 1000), (1000, 0, 1000), (1000, 0, -1000), (0, 0, -1000)]
    return bgi.BgiWalkmesh.from_bytes(bgi.build(v, [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)]).to_bytes())


def _thin_strip():
    """_strip()'s room with its door strip 10u wide (x -5..5): closed to him, a wall two edges thick."""
    v = [(-1000, 0, 1000), (-5, 0, 1000), (5, 0, 1000), (1000, 0, 1000),
         (-1000, 0, -1000), (-5, 0, -1000), (5, 0, -1000), (1000, 0, -1000)]
    f = [(0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6)]
    wm = bgi.BgiWalkmesh.from_bytes(bgi.build(v, f).to_bytes())
    for ti in (2, 3):
        wm.tris[ti].tri_flags = 0xA001
    return P.PlayerWalkmesh(wm)


@pytest.mark.parametrize("floor, start", [(_two_rooms, (-5, 0)), (_two_rooms, (-1, 0)), (_thin_strip, (-12, 0))])
def test_leaving_the_wall_band_never_steps_through_the_wall_it_stands_beside(floor, start):
    """A wall with floor on its far side -- a zero-width divider, a thin strip closed to him: the far side measures
    its OWN walls, so judged at two points a grid step apart the step across reads as ground gained (5u off the
    divider, 400u past it), and a route out of the band walked straight through (review: [(600, 0)] from (-5, 0)).
    The way out is walked in samples no further apart than he stands off the walls, which no wall can hide between:
    across, no route; on his own side, a route that stays there."""
    wm = floor()
    assert wm.distance_to_boundary(*start) < 10 and wm.point_on_walkmesh(600, 0) is not None
    assert P.route_avoiding(wm, start, (600, 0), []) is None                  # the build's rule: none either
    assert P.route_avoiding(wm, start, (600, 0), [], leave_wall=True) is None
    assert P.route(wm, start, (600, 0), leave_wall=True) is None
    assert not P._clear(wm, start, (600, 0), (), cam.COLLISION_RADIUS_W, 192.0, leave_wall=True)
    wps = P.route_avoiding(wm, start, (-600, 300), [], leave_wall=True)
    assert wps and tuple(wps[-1]) == (-600, 300)
    _walked_on_the_floor(wm, start, wps)
    _band_exit(wm, start, wps)


def test_the_starts_first_step_onto_a_free_cell_never_crosses_a_wall():
    """The start is taken as given, as it always was: its first step may go straight onto any free cell. A wall at 45
    degrees to the grid puts a free cell ACROSS it one diagonal step (90.5u) from a start 5.7u off it -- the one move
    the planner never checked, and the build still does not. Under ``leave_wall`` that step is walked no further
    apart than he stands off the walls: across, no route; on his side, one."""
    v = [(-1000, 0, -1000), (1000, 0, -1000), (-1000, 0, 1000),
         (1000, 0, 1000), (-1000, 0, 1000), (1000, 0, -1000)]           # split along x + z = 0, nothing linked
    wm = bgi.BgiWalkmesh.from_bytes(bgi.build(v, [(0, 1, 2), (3, 4, 5)]).to_bytes())
    start = (-4, -4)
    assert wm.distance_to_boundary(*start) == pytest.approx(8 / 2 ** 0.5)
    assert P._free(wm, start[0] + 64, start[1] + 64, (), cam.COLLISION_RADIUS_W, 192.0), \
        "premise: a free cell across the wall, one diagonal step from the start"
    assert P.route_avoiding(wm, start, (600, 0), [], leave_wall=True) is None
    wps = P.route_avoiding(wm, start, (-600, -300), [], leave_wall=True)
    assert wps and tuple(wps[-1]) == (-600, -300)
    _walked_on_the_floor(wm, start, wps)
    _band_exit(wm, start, wps)


def test_the_starts_first_step_is_walked_by_the_triangles_it_links():
    """``_steps_linked``, the start's first step: every unit of it on the floor, every change of triangle across a
    linked edge. Its samples from (-5, 0) land ON the zero-width wall at x = 0, where both rooms' triangles contain
    the point -- which triangles he stands on narrows to those he reached, so that sample does not carry him over.
    A strip closed to him is no floor; opened (he stands in it) it is."""
    rooms = _two_rooms()
    assert P._steps_linked(rooms, (-5, 0), (-59, 64)) and not P._steps_linked(rooms, (-5, 0), (59, 0))
    assert len(rooms.tris_at(0, 0)) == 2, "premise: a sample on the wall lies in both rooms"
    view = P.PlayerWalkmesh(_strip())
    assert not P._steps_linked(view, (-150, 0), (150, 0)) and P._steps_linked(view, (-150, 0), (-150, 90))
    assert P._steps_linked(view.standing_at(0, 0), (0, 0), (150, 0))



def test_key_move_basis_is_the_engines_rotation():
    """``FieldMapActorController``: a digital press rotated by Euler(0, (v+1)/256*360, 0). The kit's blank TWIST
    (-1 / 255) is 0 deg; stock 351/352's TWIST 0 is 1.4 deg -- the harness MEASURED up (+0.02, +1.00), right
    (+1.00, -0.02) there; 63 is a quarter turn. Up and right stay perpendicular with one handedness."""
    from ff9mapkit.content import movement
    for v in (-1, 255, None):
        b = movement.key_move_basis(v)
        assert b["v"] == pytest.approx((0.0, 1.0), abs=1e-9) and b["h"] == pytest.approx((1.0, 0.0), abs=1e-9)
    b = movement.key_move_basis(0)
    assert (round(b["v"][0], 2), round(b["v"][1], 2)) == (0.02, 1.0)
    assert (round(b["h"][0], 2), round(b["h"][1], 2)) == (1.0, -0.02)
    b = movement.key_move_basis(63)
    assert b["v"] == pytest.approx((1.0, 0.0), abs=1e-9) and b["h"] == pytest.approx((0.0, -1.0), abs=1e-9)
    for v in range(-128, 256, 7):
        b = movement.key_move_basis(v)
        assert b["v"] == pytest.approx((-b["h"][1], b["h"][0]), abs=1e-12)     # up = (-right.z, right.x)


# ======================================================================= real bytes (install-gated)
@pytest.fixture(scope="module")
def stock():
    """``(walkmesh(fid), script(fid))`` from the install, or a warned skip (THE WORKTREE SKIP TRAP)."""
    try:
        from ff9mapkit import extract, storytrace
        src = storytrace.stock_script_source()
        extract.stock_walkmesh(350)
        assert src(350) is not None
    except Exception as err:                                   # noqa: BLE001 -- no install here
        warnings.warn(
            f"the route/frame checks went UNVERIFIED against real bytes in this run: the game install is not "
            f"readable here ({type(err).__name__}). Run on the machine with the install.", UserWarning)
        pytest.skip("game install unavailable")
    return extract.stock_walkmesh, (lambda fid: src(fid).data)


# Recorded in-game (the harness's published player.x/z). Source runs: .harness-runs/*story-rung{0,1,2}
# (552 and its verbatim fork 30830 -- same walkmesh), *movepc-field70 (105), *mcf-rung1-explore (1606),
# *editable-2507-* (2507; its two OFF-walkway points are the DETACHED player that study hunted, not frame
# error), and the rung-3 stuck run's state.json (351, taken the moment the 350 gateway had fired).
RECORDED = {
    552: [(337, 1046), (-1632, 55)],
    105: [(-51, 2986)],
    351: [(-1891, 218)],
    1606: [(-691, -150), (-650, -162), (-591, -170), (-548, -210), (-506, -251), (-462, -292), (-419, -334),
           (-377, -290), (-336, -247), (-310, -232), (-303, -231), (-300, -231), (-299, -231)],
    2507: [(2019, -1077), (2075, -1055), (2099, -1021), (2114, -983), (2128, -946), (2142, -907), (2157, -870)],
}
#: (field, entrance or None = the default) -> the recorded arrival, which must equal the script's D9 literal
ARRIVALS = {(552, 3): (337, 1046), (552, 5): (-1632, 55), (105, None): (-51, 2986), (1606, 11): (-691, -150),
            (2507, 128): (2019, -1077)}
#: 2507's walk along the walkway's edge: the controller pins the centre EXACTLY its radius off a wall
WALL_SLIDE_2507 = [(2099, -1021), (2114, -983), (2128, -946), (2142, -907), (2157, -870)]


def test_frame_recorded_positions_stand_on_the_stock_walkmesh(stock):
    walkmesh, _script = stock
    for fid, pts in RECORDED.items():
        wm = walkmesh(fid)
        off = [p for p in pts if not wm.floors_at(*p)]
        assert not off, f"field {fid}: recorded positions OFF the walkmesh {off}"


def test_frame_each_dropped_term_fails_the_same_check(stock):
    """The falsifier, one per term of ``vert + orgPos + floor.org``: rebuild the mesh WITHOUT that term and the
    same recorded positions no longer all stand on it -- so the check above tells the frames apart.

    Without ``orgPos`` every field fails. Without ``floor.org`` only fields whose recorded points sit on a
    floor with a non-zero org can fail (552's (-1632, 55), 2507's walkway): 105, 351 and 1606 stand on
    org-0 floors, where the two frames coincide -- so that term is pinned by 552 and 2507 alone."""
    from ff9mapkit.scene.bgi import Vec3
    walkmesh, _script = stock

    def without(fid, term):
        wm = walkmesh(fid)                                   # a fresh parse: safe to edit
        if term == "orgPos":
            wm.orgPos = Vec3(0, 0, 0)
        else:
            for fl in wm.floors:
                fl.org = Vec3(0, 0, 0)
        wm.invalidate_cache()
        return wm

    for fid, pts in RECORDED.items():
        wm = without(fid, "orgPos")
        assert any(not wm.floors_at(*p) for p in pts), f"field {fid}: the frame without orgPos also fits"
    for fid in (552, 2507):
        wm = without(fid, "floor.org")
        assert any(not wm.floors_at(*p) for p in RECORDED[fid]), f"field {fid}: the frame without floor.org fits"


def test_frame_arrivals_are_the_scripts_own_literals(stock):
    """The published position IS the field script's coordinate space: an arrival lands on the D9 x/z literal
    the Init wrote, to the unit. SetRegion corners are literals of that same script -- one frame, no transform."""
    from ff9mapkit import eventscan
    walkmesh, script = stock
    for (fid, ent), pos in ARRIVALS.items():
        t = eventscan.scan_arrival_table(script(fid))
        want = (t["default"]["pos"] if ent is None
                else next(r["pos"] for r in t["table"] if r["entrance"] == ent))
        assert tuple(want) == pos, f"field {fid} entrance {ent}: script {want} vs recorded {pos}"


def test_frame_a_wall_slide_sits_at_the_controller_radius(stock):
    """A boundary off by more than a unit or two would not put five consecutive samples at 80-81u."""
    walkmesh, _script = stock
    wm = walkmesh(2507)
    d = [wm.distance_to_boundary(*p) for p in WALL_SLIDE_2507]
    assert all(cam.COLLISION_RADIUS_W - 1 <= x <= cam.COLLISION_RADIUS_W + 2 for x in d), d


def test_frame_the_stuck_position_is_inside_the_gateway_that_fired(stock):
    """351's state.json was written with control already gone -- the 350 gateway's ExitField had fired -- and
    that position lies INSIDE 351's 350 zone as scan_gateways decodes it: player frame == region frame."""
    from ff9mapkit import eventscan
    _walkmesh, script = stock
    zone = next(g["zone"] for g in eventscan.scan_gateways(script(351)) if g["to"] == 350)
    assert P.poly_gap(-1891, 218, zone) < 0


def test_scan_control_twist_reads_both_operands(stock):
    """The keys read arg2 (stock Memoria.ini UseAbsoluteOrientation = 3); stock Dali has fields where the two
    differ, so a reader of arg1 alone would predict the wrong direction there."""
    from ff9mapkit import eventscan
    _walkmesh, script = stock
    assert eventscan.scan_control_twist(script(351)) == (0, 0)
    assert eventscan.scan_control_twist(script(354)) == (242, 0)
    assert eventscan.scan_control_twist(script(450)) == (0, 18)
    assert eventscan.scan_control_direction(script(354)) == 242          # the old reader: arg1 only


def _zones(script, fid):
    """(to, zone) per DISTINCT gateway zone (350 lists its 353 exit twice with one zone)."""
    from ff9mapkit import eventscan
    out = []
    for g in eventscan.scan_gateways(script(fid)):
        if all(g["zone"] != z for _t, z in out):
            out.append((g["to"], g["zone"]))
    return out


def _every_exit_routes_clear(wm, start, zones):
    for i, (to, zone) in enumerate(zones):
        goal = P.region_goal(wm, zone)
        assert goal is not None, f"exit to {to}: its zone does not touch the walkmesh"
        others = [z for j, (_t, z) in enumerate(zones) if j != i]
        wps = P.route_avoiding(wm, start, goal, others, P.KEEPOUT_MARGIN_W)
        assert wps is not None, f"no route from {start} to the exit to {to}"
        # the regions the start is NOT inside must never be entered -- by a waypoint or by any leg between
        live = [z for z in others if P.poly_gap(start[0], start[1], z) >= 0]
        assert all(P.poly_gap(w[0], w[1], z) >= 0 for w in wps for z in live), (to, wps)
        assert _legs_clear(start, wps, live), (to, wps)
        assert all(wm.floors_at(*w) for w in wps), (to, wps)


def test_350_from_the_351_door_reaches_every_other_exit(stock):
    """THE STUCK FIELD. The arrival from 351 (entrance 2, the script's (258, -58)) stands 18u outside 351's
    own gateway; every other exit must route without touching it (or any other exit)."""
    from ff9mapkit import eventscan
    walkmesh, script = stock
    wm = walkmesh(350)
    start = tuple(next(r["pos"] for r in eventscan.scan_arrival_table(script(350))["table"] if r["entrance"] == 2))
    zones = _zones(script, 350)
    door = next(z for t, z in zones if t == 351)
    assert 0 <= P.poly_gap(*start, door) < P.KEEPOUT_MARGIN_W          # the premise: beside the door
    _every_exit_routes_clear(wm, start, zones)


def test_352_the_inn_room_routes_out_from_anywhere_in_it(stock):
    """THE TOUR'S FIRST CROSSING. 352's inn room leaves through a corner-to-corner pinch whose widest standable
    spot is ~82u from both walls (controller radius 80), and the grid is aligned on the start: from most of
    the room no cell centre of a 64 or 32 grid lands in that band, and a tour that read 'no route' there
    ended after one crossing. The finer retries (ROUTE_REFINES) must route every standable start."""
    walkmesh, script = stock
    wm = walkmesh(352)
    (to, zone), = _zones(script, 352)
    assert to == 351
    goal = P.region_goal(wm, zone)
    # a prime step, so the starts -- and with them the start-aligned grids -- take every offset mod 8 and 16
    # (an 80-step grid of starts would test ONE alignment of the finer grains, over and over)
    starts = [(x, z) for x in range(-560, 561, 73) for z in range(320, 881, 73)
              if wm.floors_at(x, z) and (wm.distance_to_boundary(x, z) or 0) >= cam.COLLISION_RADIUS_W]
    assert len(starts) >= 20
    coarse = [s for s in starts if P.route(wm, s, goal, cell=64) is None and P.route(wm, s, goal, cell=32) is None]
    assert coarse, "premise: some inn-room starts need a grid finer than 32"
    missed = [s for s in starts if P.route_avoiding(wm, s, goal, []) is None]
    assert not missed, f"no route out of the inn room from {missed}"


DALI = (350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 450)


def test_the_one_dali_door_a_router_cannot_walk_back_out_of_is_350_to_358(stock):
    """THE TOUR'S TRAP (studies/story-trace/rung3_step1.py, its ONE-WAY rule). 350's gateway to 358 (entrance
    22) stands the player at 358's (160, 4519), on a walkmesh piece that 358's only gateway zone (to 356) is not
    on -- the way back to 350 is a scripted position check, not a region -- so from that arrival no exit of 358
    routes. It sits before 450 in 350's scan order, and an offline dry run of the tour stranded there one exit
    short of 450. Every other Dali door whose arrival spot decodes leads somewhere with a routable exit."""
    from ff9mapkit import eventscan
    walkmesh, script = stock
    one_way = set()
    for f in DALI:
        for g in eventscan.scan_gateways(script(f)):
            to = g["to"]
            if to not in DALI:
                continue
            t = eventscan.scan_arrival_table(script(to))
            row = next((r for r in t["table"] if r["entrance"] == g["entrance"]), None) or t["default"]
            if row is None:
                continue                                          # undecoded arrival: the tour calls it two-way
            wm, zones = walkmesh(to), _zones(script, to)
            back = False
            for i, (_t, zone) in enumerate(zones):
                goal = P.region_goal(wm, zone)
                others = [z for j, (_t2, z) in enumerate(zones) if j != i]
                if goal is not None and P.route_avoiding(wm, tuple(row["pos"]), goal, others) is not None:
                    back = True
                    break
            if not back:
                one_way.add((f, to, g["entrance"]))
    assert one_way == {(350, 358, 22)}, one_way


#: rung-3 s1b, crossings 20 and 22: where 356 -> 358 stalled, pressing a wall the raw mesh does not have
STALLS_356_TO_358 = [(831, 1234), (836, 1224), (795, 1301), (864, 1175)]


def test_on_the_players_floor_356_to_358_has_no_route_and_every_other_dali_exit_still_routes(stock):
    """THE 356 -> 358 STALLS: all four stood the controller radius off a wall only the player's floor has --
    the edge of triangle 50, a door strip (triFlags 0xA001) the raw mesh treats as floor. On his floor that exit
    has no route from anywhere the tour stood in 356; from every decoded Dali arrival, every other Dali exit
    still routes -- the strips close nothing else."""
    from ff9mapkit import eventscan
    walkmesh, script = stock
    raw = walkmesh(356)
    view = P.PlayerWalkmesh(raw)
    assert 50 in view.closed
    for s in STALLS_356_TO_358:
        assert raw.distance_to_boundary(*s) > cam.COLLISION_RADIUS_W, s             # raw: open floor
        assert abs(view.distance_to_boundary(*s) - cam.COLLISION_RADIUS_W) <= 3, s  # his: against a wall
    starts: dict = {}
    for f in DALI:
        for g in eventscan.scan_gateways(script(f)):
            if g["to"] in DALI:
                t = eventscan.scan_arrival_table(script(g["to"]))
                row = next((r for r in t["table"] if r["entrance"] == g["entrance"]), None) or t["default"]
                if row is not None:
                    starts.setdefault(g["to"], set()).add(tuple(row["pos"]))
    starts[356] |= set(STALLS_356_TO_358)
    routed, sealed = 0, []
    for f, pts in sorted(starts.items()):
        wm, zones = P.PlayerWalkmesh(walkmesh(f)), _zones(script, f)
        for i, (to, zone) in enumerate(zones):
            if to not in DALI:
                continue
            goal = P.region_goal(wm, zone)
            others = [z for j, (_t, z) in enumerate(zones) if j != i]
            for s in sorted(pts):
                if P.route_avoiding(wm.mesh, s, P.region_goal(wm.mesh, zone), others) is None:
                    continue                    # no route on the raw mesh either (358's one-way arrival)
                if P.route_avoiding(wm, s, goal, others) is None:
                    sealed.append((f, to, s))
                else:
                    routed += 1
    assert {(f, to) for f, to, _s in sealed} == {(356, 358)}, sealed
    assert len(sealed) == len(starts[356]) and routed >= 60, (routed, sealed)


#: rung-3 runs 4 and 5: where 352's wake scene handed control back -- in stock 352 and in its verbatim fork 30834,
#: which runs 352's .bgi byte for byte -- and route_to answered "no route" twice, ending the tour
WAKE_352 = (-133, 847)


def test_from_352s_wake_spot_the_route_walks_out_of_the_wall_band_to_the_351_door(stock):
    """THE 352 WAKE. On his floor the wake spot stands 22.8u off the edge of a strip closed to him (triangles 64/66/67,
    triFlags 0xA001) and 59u off the back wall -- inside the 80u band -- so no cell of any grain near it was free
    and the plan never left the start. ``leave_wall`` plans out of the band -- never nearer a wall, out within
    (80 - 22.8) / WALL_LEAVE_GAIN of walking -- to the one door, 351's, with every point of the route on the floor
    open to him and every waypoint after the band clear of the walls."""
    walkmesh, script = stock
    view = P.PlayerWalkmesh(walkmesh(352))
    zones = _zones(script, 352)
    assert [t for t, _z in zones] == [351]
    zone = zones[0][1]
    goal = P.region_goal(view, zone)
    assert view.distance_to_boundary(*WAKE_352) == pytest.approx(22.8, abs=0.1)
    assert walkmesh(352).distance_to_boundary(*WAKE_352) == pytest.approx(59.0)          # the raw mesh: the back wall
    assert P.route_avoiding(view, WAKE_352, goal, []) is None                          # the failure, pinned
    wps = P.route_avoiding(view, WAKE_352, goal, [], leave_wall=True)
    assert wps and tuple(wps[-1]) == tuple(goal) and P.poly_gap(goal[0], goal[1], zone) < 0
    _walked_on_the_floor(view, WAKE_352, wps)
    walked, _after = _band_exit(view, WAKE_352, wps)
    assert walked < 120
    assert all(view.distance_to_boundary(*w) >= cam.COLLISION_RADIUS_W for w in wps)


#: Stock band starts a few units off an UNLINKED edge with floor past it (review of the 352 fix): 2216's (-333, 3160)
#: stands 11.5u off the edge of triangle 26, past which triangles 54/55 lie 1136u lower, and the goal is on them;
#: 1863's (-236, 1071) stands 5.2u off a wall. Judged at cell centres, the way out stepped straight across (2216:
#: [(-333, 3096), (-317, 2999)]) or off the mesh for 8u (1863's first leg).
UNLINKED_EDGE_STARTS = [(2216, (-333, 3160), (-317, 2999)), (1863, (-236, 1071), (-1764, -258))]


@pytest.mark.parametrize("fid, start, goal", UNLINKED_EDGE_STARTS)
def test_the_way_out_of_the_wall_band_never_crosses_an_unlinked_edge(stock, fid, start, goal):
    """The route that walks out of the band takes the linked way round -- on the raw mesh and on his floor."""
    walkmesh, _script = stock
    for wm in (walkmesh(fid), P.PlayerWalkmesh(walkmesh(fid))):
        here = wm.standing_at(*start) if isinstance(wm, P.PlayerWalkmesh) else wm
        assert here.distance_to_boundary(*start) < 12
        wps = P.route_avoiding(wm, start, goal, [], leave_wall=True)
        assert wps and tuple(wps[-1]) == goal
        _walked_on_the_floor(here, start, wps)
        _band_exit(here, start, wps)


#: Band starts ON a seam between two floors (the start's point lies in a triangle of each): the floor found first
#: measures its own walls, and the planner's way onto the other floor passes the corner where that wall begins --
#: 0.1u off it, by distance a touch. Every one routed before ``leave_wall`` existed; a first step judged by distance
#: refused all three (13 of 51 such starts in stock 1000-1009).
SEAM_STARTS = [(57, (-1511, -582), (-1364, -632)), (1006, (-637, -1544), (-746, -1433)),
               (1008, (-919, 4322), (-829, 4449))]


@pytest.mark.parametrize("fid, start, goal", SEAM_STARTS)
def test_a_band_start_on_a_seam_still_routes_onto_the_other_floor(stock, fid, start, goal):
    walkmesh, _script = stock
    wm = walkmesh(fid)
    assert len(wm.tris_at(*start)) == 2 and wm.distance_to_boundary(*start) < 6
    plain = P.route_avoiding(wm, start, goal, [])
    assert plain is not None, "premise: the planner without leave_wall routes it"
    wps = P.route_avoiding(wm, start, goal, [], leave_wall=True)
    assert wps and tuple(wps[-1]) == goal
    _walked_on_the_floor(wm, start, wps)


#: The Dali fields with an exit to walk to (357 and 359 have no gateway zone)
DALI_EXITS = (350, 351, 352, 353, 354, 355, 356, 358, 450)

#: Band starts the quantiles miss. 350's (-581, 810) stands 64u off the walls of triangle 314's floor, beside its seam
#: onto triangle 48's: the straight way out crosses it within 13u, and on 314's floor it first comes 7.6u NEARER the
#: walls -- which band samples 32u apart (no further than he stands off them, nor past the band's edge) step over.
EXTRA_BAND_STARTS = {350: [(-581, 810)]}


@pytest.mark.parametrize("fid", DALI_EXITS)
def test_from_the_wall_band_anywhere_on_a_dali_floor_the_route_walks_out_on_his_floor(stock, fid):
    """``leave_wall`` beyond the hand-picked starts: on his floor in every Dali field with an exit, four starts in the
    band -- from ON a wall to the band's edge (quantiles of a 37u grid's band points; and EXTRA_BAND_STARTS) -- routed
    to the field's first two exits as the tour routes them (the other zones kept out). Every route walks on his floor,
    never through a wall, and out of the band as promised (:func:`_band_exit`); no start the build's rule routes goes
    unrouted."""
    walkmesh, script = stock
    view = P.PlayerWalkmesh(walkmesh(fid))
    zones = _zones(script, fid)
    goals = [(P.region_goal(view, z), [o for j, (_t, o) in enumerate(zones) if j != i])
             for i, (_t, z) in enumerate(zones)]
    goals = [(g, others) for g, others in goals if g is not None][:2]
    wv = view.mesh.world_verts()
    xs, zs = [v[0] for v in wv], [v[2] for v in wv]
    band = sorted((view.distance_to_boundary(x, z), (x, z))
                  for x in range(int(min(xs)), int(max(xs)), 37) for z in range(int(min(zs)), int(max(zs)), 37)
                  if view.point_on_walkmesh(x, z) is not None
                  and (view.distance_to_boundary(x, z) or cam.COLLISION_RADIUS_W) < cam.COLLISION_RADIUS_W)
    starts = [band[k * (len(band) - 1) // 3][1] for k in range(4)] + EXTRA_BAND_STARTS.get(fid, [])
    assert goals and band[0][0] < 1.0, "premise: an exit, and a band start (nearly) on a wall"
    routed = 0
    for s in starts:
        here = view.standing_at(*s)
        for goal, others in goals:
            wps = P.route_avoiding(view, s, goal, others, leave_wall=True)
            if wps is None:
                assert P.route_avoiding(view, s, goal, others) is None, (s, goal)
                continue
            routed += 1
            _walked_on_the_floor(here, s, wps)
            if here.distance_to_boundary(*s) < cam.COLLISION_RADIUS_W:
                _band_exit(here, s, wps)
    assert routed, "premise: some band start routes"


def test_351_from_the_stuck_landing_reaches_every_exit(stock):
    walkmesh, script = stock
    _every_exit_routes_clear(walkmesh(351), (-1891, 218), _zones(script, 351))


def test_450_from_beside_its_350_door_reaches_its_other_regions(stock):
    """450 has ONE gateway (to 350); its other two trigger regions stand in for 'the other exits'. The start
    is a standable spot just outside the 350 door -- where an arrival from 350 stands."""
    from ff9mapkit import eventscan
    walkmesh, script = stock
    wm = walkmesh(450)
    door = next(g["zone"] for g in eventscan.scan_gateways(script(450)) if g["to"] == 350)
    regions = [z for z in eventscan.scan_region_zones(script(450)) if z != door]
    assert len(regions) >= 2
    near = [(x, z) for x in range(-800, 800, 16) for z in range(-2400, -1200, 16)
            if 20 <= P.poly_gap(x, z, door) <= 40 and (wm.distance_to_boundary(x, z) or 0) >= cam.COLLISION_RADIUS_W]
    assert near, "no standable spot beside 450's 350 door"
    start = min(near, key=lambda p: (p[0] - 30) ** 2 + (p[1] + 1770) ** 2)
    _every_exit_routes_clear(wm, start, [(350, door)] + [(None, z) for z in regions])
