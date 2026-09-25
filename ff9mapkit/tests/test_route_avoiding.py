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

import warnings

import pytest

from ff9mapkit.content import pathfind as P
from ff9mapkit.scene import bgi, cam


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


def test_region_goal_is_inside_the_region_and_standable():
    door = _rect(800, -200, 1200, 200)                       # straddles the room's east edge (x = 1000)
    g = P.region_goal(ROOM, door)
    assert g is not None
    assert P.poly_gap(g[0], g[1], door) < 0                   # inside the trigger
    assert ROOM.distance_to_boundary(*g) >= cam.COLLISION_RADIUS_W - 1   # where a player centre can stand
    assert P.region_goal(ROOM, _rect(1100, -200, 1300, 200)) is None     # off the mesh entirely


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
