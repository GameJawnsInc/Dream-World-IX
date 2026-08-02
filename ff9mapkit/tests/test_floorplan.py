"""Fences for the floorplan composer (click-authoring Rung 6) -- the pure topology layer.

Every test here pins a law an adversarial pass BROKE in the first draft of the spec
(``studies/click-authoring/RUNG6.md`` §1). Several assert the SHAPE OF A BUG rather than just the
fix, so that a future "simplification" back toward the obvious-looking version goes red instead of
silently reintroducing an inversion nobody can see.

A law in a docstring is a wish in this codebase. These are the laws.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from ff9mapkit import floorplan as F
from ff9mapkit import imagefield as IF
from ff9mapkit import pack
from ff9mapkit.scene import cam as CAM
from ff9mapkit.scene import guide

# two rooms abutting on the x=0 wall; A to the west, B to the east
ROOM_A = [(-2400, -900), (0, -900), (0, 900), (-2400, 900)]
ROOM_B = [(0, -900), (2400, -900), (2400, 900), (0, 900)]
DOOR = ((0.0, -300.0), (0.0, 300.0))
L_SHAPE = [(0, 0), (2400, 0), (2400, 1000), (1000, 1000), (1000, 2400), (0, 2400)]
U_SHAPE = [(0, 0), (3000, 0), (3000, 2400), (2000, 2400), (2000, 900),
           (1000, 900), (1000, 2400), (0, 2400)]


KIT = Path(__file__).resolve().parents[2]      # the repo root, for the census


def _plan(**kw):
    base = {"name": "T", "id_base": 30500,
            "rooms": [{"name": "HALL", "poly": ROOM_A}, {"name": "CELL", "poly": ROOM_B}],
            "doors": [{"a": "HALL", "b": "CELL", "seg": [list(DOOR[0]), list(DOOR[1])]}]}
    base.update(kw)
    return base


# ------------------------------------------------------------------ the wall radius, and its split

def test_R_WALK_agrees_with_the_shared_collision_radius():
    """★ THE TRIPWIRE. `floorplan.R_WALK` is deliberately its OWN literal, not an alias of
    `cam.COLLISION_RADIUS_W` -- the composer derived 80 independently from the opcode chain
    (SetObjectLogicalSize(20,..) x4) back when the shared constant still said 48, and the two agreed
    only after the value was measured in-game on 2026-07-30 (calibration field 30510: the clamped
    stop read exactly 80u off the wall).

    A duplicate with no fence is just a second owner of one number. THIS is what makes it a
    tripwire instead: if either side drifts, this goes red and names both. Do NOT "simplify" it to
    `R_WALK = cam.COLLISION_RADIUS_W` -- an alias cannot detect the drift it exists to catch."""
    assert F.R_WALK == CAM.COLLISION_RADIUS_W, (
        f"floorplan.R_WALK={F.R_WALK} vs cam.COLLISION_RADIUS_W={CAM.COLLISION_RADIUS_W} -- the "
        f"composer's gates (DEPTH_MIN = 2*R_WALK, arrival insets, `standable`) and the rest of the "
        f"kit now disagree about where the player can stand")


def test_the_walk_radius_is_reconciled_everywhere_but_the_trace_outset():
    """★ THE SPLIT, HALF CLOSED. Pins what is reconciled AND what deliberately is not.

    The 2026-07-30 measurement corrected `cam.COLLISION_RADIUS_W` 48 -> 80 and left two standalone
    literals behind. `routes.WALL_CLEARANCE_W` was reconciled to 80 on owner sign-off, because it
    was never an independently-derived number -- just a stale copy of the value that got measured
    wrong -- and it erred OPTIMISTIC: a 130u corridor measures 1820 standable cells at 48 and ZERO
    at 80, so every sweep in `routes` certified patrols the engine physically cannot walk. That flip
    also settled `content/pathfind.py` disagreeing with itself (`route_polyline` defaults to routes',
    `route` to cam's); both now resolve to 80.

    Re-measured rather than relaxed, as the reconciliation required: exactly ONE behavior test moved
    (`test_behavior_pursuit.test_concave_notch_is_caught_with_an_exemplar_pair`, whose exemplar bound
    had to go wall-INCLUSIVE -- an 80u step lands exactly on the notch wall where a 48u step never
    did). RUNG6.md §6.1's estimate of five was high.

    `imagefield.COLLISION_OUTSET` stays 48 ON PURPOSE. Offline it looks equally wrong (it
    under-outsets every traced field by 32u -- the "back edge is a bit short" symptom) and flipping
    it breaks ZERO tests, but it changes the shipped walkmesh geometry of every traced field, and
    that is an in-game judgment nobody has made yet. It needs a traced-field playtest, not a green
    suite. The day it flips, this test goes red -- the reminder to update the layout skill's outset
    prose and RUNG6.md §6.1 in the same breath, so the docs never describe a value the code dropped."""
    from ff9mapkit.scene import routes as _routes
    assert _routes.WALL_CLEARANCE_W == CAM.COLLISION_RADIUS_W == F.R_WALK == 80.0, (
        f"the walk radius drifted apart again: routes={_routes.WALL_CLEARANCE_W} "
        f"cam={CAM.COLLISION_RADIUS_W} floorplan={F.R_WALK} -- all three are the SAME measured "
        f"engine constant (calibration field 30510), kept as separate literals so drift goes red here")
    assert IF.COLLISION_OUTSET == 48.0, (
        "imagefield.COLLISION_OUTSET changed -- if it is now 80, a traced field's back edge should "
        "finally reach the painted floor. Confirm that IN-GAME, then update the outset note in "
        ".claude/skills/laying-out-ff9-fields/SKILL.md and RUNG6.md §6.1 and delete this assert")
    # the hazard the REMAINING half creates, measured rather than asserted from memory
    corridor = [(0, 0), (3000, 0), (3000, 130), (0, 130)]
    assert F.standable(corridor, R=IF.COLLISION_OUTSET), "the trace outset thinks this is walkable"
    assert F.standable(corridor, R=F.R_WALK) == set(), "and the engine says it is not"


# ------------------------------------------------------------------ C2 + C3: the inversion class
# The highest-value fixtures in the file. The draft's design inverted on 48.5% of these inputs.

@pytest.mark.parametrize("offset", [-8.0, -4.0, -0.5, 0.0, 0.5, 4.0, 8.0])
@pytest.mark.parametrize("order", [0, 1])
def test_the_door_facings_survive_a_wall_drawn_off_the_candidate(offset, order):
    """THE INVERSION FENCE. Room B's wall is drawn `offset` off the shared segment -- which is the
    normal case for a hand-traced plan, and exactly where a point-in-polygon disambiguation stops
    being decisive (off-coincident, BOTH probe points are inside or both outside). Arriving through
    A's EAST door you face WEST (64); through B's WEST door you face EAST (192). Order-invariant."""
    b = [(0 + offset, -900), (2400, -900), (2400, 900), (0 + offset, 900)]
    seg = DOOR if order == 0 else (DOOR[1], DOOR[0])
    na, _ = F.interior_normal(ROOM_A, seg)
    nb, _ = F.interior_normal(b, seg)
    assert F.face_of_dir(*na) == 64, f"A's east door should face west; offset={offset} order={order}"
    assert F.face_of_dir(*nb) == 192, f"B's west door should face east; offset={offset} order={order}"


def test_the_same_room_listed_clockwise_gives_the_identical_normal():
    """Winding must not reach the answer. `imagefield._as_ccw` normalizes it, but only because C2
    goes through it -- a version that used the caller's order would flip here."""
    n1, s1 = F.interior_normal(ROOM_A, DOOR)
    n2, s2 = F.interior_normal(list(reversed(ROOM_A)), DOOR)
    assert list(n1) == pytest.approx(list(n2))
    assert [c for p in s1 for c in p] == pytest.approx([c for p in s2 for c in p])
    assert F.face_of_dir(*n1) == F.face_of_dir(*n2) == 64


def test_the_normal_does_not_depend_on_the_probe_distance():
    """A 120u-wide corridor with the door on its long south wall: truth is 128 (north). The draft's
    design was correct only for eps < the local room width, so a plausible author pick of 48 or 80
    broke it. This one has no eps in the decision path at all."""
    corridor = [(0, 0), (3000, 0), (3000, 120), (0, 120)]
    seg = ((1000.0, 0.0), (1400.0, 0.0))
    for eps in (1e-3, 1.0, 48.0, 80.0, 119.0):
        n, _ = F.interior_normal(corridor, seg, eps=eps)
        assert F.face_of_dir(*n) == 128, f"eps={eps}"


def test_interior_normal_returns_the_seg_projected_onto_the_rooms_own_wall():
    """★ C5 and C6 must consume the RETURNED seg. Unprojected, a wall drawn 4u off the candidate
    produced a gateway quad with 0 of 4 corners on the mesh."""
    b = [(-4, -900), (2400, -900), (2400, 900), (-4, 900)]
    n, seg = F.interior_normal(b, DOOR)
    for p in seg:
        assert p[0] == pytest.approx(-4.0), "both endpoints must land on the room's own wall"
    quad = F.door_strip(b, DOOR, 250.0)
    on_mesh = sum(1 for c in quad if F.point_in_poly(c[0], c[1], b)
                  or F.dist_to_boundary(c[0], c[1], b) < 1e-6)
    assert on_mesh == 4, f"every corner should sit on B's mesh, got {on_mesh}: {quad}"


def test_face_of_dir_round_trips_every_byte_through_the_probes_own_formula():
    """`tools/field_layout_probe.face_to_dir` is the forward direction the repo already ships."""
    bad = []
    for byte in range(256):
        th = byte / 256.0 * 2 * math.pi
        dx, dz = -math.sin(th), -math.cos(th)
        if F.face_of_dir(dx, dz) != byte:
            bad.append(byte)
    assert bad == [], f"round-trip mismatches: {bad}"


def test_the_four_cardinals_match_the_documented_table():
    assert F.face_of_dir(0, -1) == 0          # south -- faces the camera
    assert F.face_of_dir(-1, 0) == 64         # west
    assert F.face_of_dir(0, 1) == 128         # north -- faces away
    assert F.face_of_dir(1, 0) == 192         # east


def test_there_is_no_cardinal_snap():
    """8 bytes of snap is 11.25deg of yaw, so two near-identical drawings would land 9 apart while
    their door quads stayed tilted. Non-cardinal bytes are first-class in real FF9."""
    a = F.face_of_dir(*F._unit((math.sin(math.radians(11.5)), math.cos(math.radians(11.5)))))
    b = F.face_of_dir(*F._unit((math.sin(math.radians(12.0)), math.cos(math.radians(12.0)))))
    assert abs(a - b) <= 1, f"{a} vs {b} -- a snap would separate these by ~9"
    assert a % 64 != 0, "an 11.5deg wall must NOT be forced to a cardinal"


# ------------------------------------------------------------------ C1: polygon health

def test_a_self_intersecting_room_is_refused_and_triangulate_would_not_have_told_us():
    """★ The draft blamed `triangulate`'s 'numerically stuck -> fan' fallback. It never fires: the
    overcount comes out of the ORDINARY ear-clip path, so 'did triangulate get stuck' is not a
    usable proxy. This asserts both halves so nobody swaps the real test for the cheap one."""
    bad = [(0, 0), (900, 0), (900, 900), (450, -300), (0, 900)]
    assert F.polygon_problem(bad) is not None
    assert "cross" in F.polygon_problem(bad)
    pts, faces = IF.triangulate(bad)
    area = sum(abs(F._cross3(pts[a], pts[b], pts[c])) / 2.0 for a, b, c in faces)
    shoe = abs(IF._signed_area(bad))
    assert area > shoe * 3, (f"triangulate overcounts a self-intersecting room's area "
                             f"({area:.0f} vs {shoe:.0f}) WITHOUT raising -- that is why C1 exists")


def test_a_bowtie_is_refused():
    assert F.polygon_problem([(0, 0), (1000, 1000), (1000, 0), (0, 1000)]) is not None


@pytest.mark.parametrize("poly", [L_SHAPE, U_SHAPE, ROOM_A])
def test_valid_concave_rooms_are_accepted_and_triangulate_exactly(poly):
    """There is deliberately no concavity gate -- the notch is not where the bug lives."""
    assert F.polygon_problem(poly) is None
    pts, faces = IF.triangulate(poly)
    area = sum(abs(F._cross3(pts[a], pts[b], pts[c])) / 2.0 for a, b, c in faces)
    assert area == pytest.approx(abs(IF._signed_area(poly)), rel=1e-9)


def test_a_zero_area_room_is_refused_by_the_area_floor():
    """Must be caught BEFORE any `_as_ccw` call: `_as_ccw` branches on `signed_area >= 0`, so a
    zero-area polygon silently 'keeps order' and its winding then means nothing."""
    why = F.polygon_problem([(0, 0), (1000, 0), (2000, 0), (1000, 0)])
    assert why is not None


def test_a_duplicated_corner_is_refused():
    assert "duplicated" in (F.polygon_problem([(0, 0), (1200, 0), (1200, 2), (1200, 900), (0, 900)])
                            or "")


# ------------------------------------------------------------------ C1b: standable

def test_a_room_narrower_than_two_wall_radii_has_nowhere_to_stand():
    assert F.standable([(0, 0), (3000, 0), (3000, 120), (0, 120)]) == set()
    assert F.standable([(0, 0), (3000, 0), (3000, 400), (0, 400)]) != set()


def test_a_dumbbell_with_a_narrow_neck_is_disconnected():
    """G13's real payload: two halves the player cannot walk between, which every point test passes."""
    neck = 100
    poly = [(0, 0), (1200, 0), (1200, (1000 - neck) / 2), (2000, (1000 - neck) / 2),
            (2000, 0), (3200, 0), (3200, 1000), (2000, 1000), (2000, (1000 + neck) / 2),
            (1200, (1000 + neck) / 2), (1200, 1000), (0, 1000)]
    assert F.polygon_problem(poly) is None, "the outline itself is legal -- that is the point"
    assert len(F.components(F.standable(poly))) > 1


def test_the_miter_erosion_that_standable_exists_to_avoid():
    """Pins WHY `standable` grid-samples instead of calling `outset_polygon(poly, -R)`. A 100u base
    passes every C1 test, and the miter still throws the tip hundreds of units."""
    half = math.radians(4.76)
    spike = [(0, 0), (100, 0), (100 * math.tan(half) + 50 * 0, 4000)]
    spike = [(0.0, 0.0), (100.0, 0.0), (50.0 + 4000 * math.tan(half), 4000.0)]
    assert F.polygon_problem(spike) is None
    tip_before = spike[2]
    tip_after = IF.outset_polygon(spike, 48.0)[2]
    moved = math.hypot(tip_after[0] - tip_before[0], tip_after[1] - tip_before[1])
    assert moved > 200, f"the miter should blow the tip out; moved {moved:.0f}u"


# ------------------------------------------------------------------ C4: shared walls

def test_two_abutting_rooms_share_a_wall_despite_their_edges_being_antiparallel():
    """★ The `abs(dot)` fence. Both rooms are already CCW, so the shared edges run OPPOSITE ways and
    `dot == -1`. A `dot > 1 - eps` implementation finds zero doors on every plan -- silently."""
    ua = F._unit(F._sub((0, 900), (0, -900)))
    ub = F._unit(F._sub((0, -900), (0, 900)))
    assert ua[0] * ub[0] + ua[1] * ub[1] == pytest.approx(-1.0), "the premise"
    cands = F.shared_edges(ROOM_A, ROOM_B)
    assert cands, "the shared x=0 wall must be offered"
    assert cands[0]["length"] == pytest.approx(1800.0)


def test_a_nested_room_is_not_a_door_candidate():
    """G12 for free: a room wholly inside another has its wall normals pointing the SAME way."""
    inner = [(-2000, -500), (-400, -500), (-400, 500), (-2000, 500)]
    outer_wall = [(-2400.0, -400.0), (-2400.0, 400.0)]
    nested = [(-2400, -500), (-800, -500), (-800, 500), (-2400, 500)]
    assert F.shared_edges(ROOM_A, nested) == [] or all(
        F.interior_normal(ROOM_A, tuple(c["seg"]))[0][0]
        * F.interior_normal(nested, tuple(c["seg"]))[0][0] < 0
        for c in F.shared_edges(ROOM_A, nested))


def test_a_short_door_in_the_middle_of_a_long_wall_is_legal():
    """The deleted `min_len = 192` would have refused this, and it is perfectly playable."""
    c = F.compose(_plan(doors=[{"a": "HALL", "b": "CELL", "seg": [[0, -50], [0, 50]]}]))
    assert len(c.by_name("HALL").toml["gateway"]) == 1


# ------------------------------------------------------------------ C5: the door strip

def test_the_strip_starts_with_the_door_segment_because_nothing_else_can_check_it():
    """G14. `CalculateExitPosition` reads q[0] and q[1] ONLY and walks the player onto that line;
    all four rotations of a legal quad score `zone_fan_audit` 0.0/0.0, so no gate can see a wrong
    q0. This fence and the assertion inside `door_strip` are the only defence."""
    quad = F.door_strip(ROOM_A, DOOR, 250.0)
    assert quad[0] == (0, -300) and quad[1] == (0, 300)
    assert quad[2][0] == quad[3][0] == -250, "the far edge is `depth` INWARD"


def test_the_fan_audit_is_blind_to_a_rotated_or_degenerate_quad():
    """Pins that G7 is NOT the backstop for either G14 or G9's degeneracy check."""
    quad = F.door_strip(ROOM_A, DOOR, 250.0)
    for k in range(4):
        rot = quad[k:] + quad[:k]
        a = IF.zone_fan_audit(rot)
        assert max(a["gap"], a["spill"]) <= F.FAN_TOL, f"rotation {k} looks clean to the fan judge"
    for degen in ([(0, 0), (0, 0), (0, 0), (0, 0)],
                  [(0, 0), (100, 0), (200, 0), (300, 0)]):
        a = IF.zone_fan_audit(degen)
        assert (a["gap"], a["spill"]) == (0.0, 0.0), "a degenerate quad scores a PERFECT 0/0"


@pytest.mark.parametrize("depth", [48, 60, 79, 80])
def test_a_door_no_deeper_than_the_wall_radius_has_no_standable_area_at_all(depth):
    """★ The draft refused only `depth <= 48` and therefore ACCEPTED a depth-60 or depth-79 door
    with 0% standable area -- the exact drawn-but-never-fires failure the gate exists to prevent."""
    quad = F.door_strip(ROOM_A, DOOR, float(depth))
    frac, pts = F.strip_standable_fraction(ROOM_A, quad)
    assert pts == [], f"depth {depth} -> {frac:.1%} standable"


def test_the_standable_measure_does_not_join_two_differently_phased_grids():
    """★ A cell-key join between the strip's grid and the room's grid looks natural and is wrong:
    a strip sample 79u off the wall and a room sample 80u off it land in the SAME 8u cell, so a
    depth-79 door -- which has no standable area whatsoever -- measured as standable."""
    for depth in (79, 80):
        _, pts = F.strip_standable_fraction(ROOM_A, F.door_strip(ROOM_A, DOOR, float(depth)))
        assert pts == []
    _, deep = F.strip_standable_fraction(ROOM_A, F.door_strip(ROOM_A, DOOR, 250.0))
    assert deep and all(F.dist_to_boundary(x, z, ROOM_A) >= F.R_WALK for x, z in deep)


@pytest.mark.parametrize("depth,ok", [(81, False), (159, False), (160, True), (170, True),
                                      (250, True)])
def test_the_depth_gate_demands_a_standable_window_not_merely_a_positive_one(depth, ok):
    """★ `depth > R_WALK` accepts an 81u door whose standable window is a ONE-UNIT sliver. The
    layout skill's own warning is that a bare on-mesh test "happily accepts a 1u edge sliver; a unit
    sent there is shoved off it". `DEPTH_MIN = 2 * R_WALK` makes the window at least the player's
    own radius -- and lands just under the in-game-proven 170, so every real strip depth passes."""
    assert F.DEPTH_MIN == 2 * F.R_WALK
    plan = _plan(doors=[{"a": "HALL", "b": "CELL",
                         "seg": [list(DOOR[0]), list(DOOR[1])], "depth": depth}])
    if ok:
        assert F.compose(plan).by_name("HALL").toml["gateway"]
    else:
        with pytest.raises(F.ComposeError) as e:
            F.compose(plan)
        assert "standable window" in str(e.value)


def test_a_door_on_a_wall_where_the_room_pinches_is_refused_even_at_a_legal_depth():
    """G9's geometric half -- the case the analytic depth check cannot see."""
    # a 120u neck running the strip's full 250u depth before the room flares out behind it
    pinched = [(-2400, -900), (-400, -60), (0, -60), (0, 60), (-400, 60), (-2400, 900)]
    assert F.polygon_problem(pinched) is None, "the outline is legal -- that is the point"
    quad = F.door_strip(pinched, ((0.0, -60.0), (0.0, 60.0)), 250.0)
    assert float(250) >= F.DEPTH_MIN, "the depth gate alone would pass this door"
    assert F.strip_standable_fraction(pinched, quad)[1] == []


def test_a_too_shallow_door_is_refused_by_compose_with_the_reason():
    with pytest.raises(F.ComposeError) as e:
        F.compose(_plan(doors=[{"a": "HALL", "b": "CELL",
                                "seg": [list(DOOR[0]), list(DOOR[1])], "depth": 60}]))
    assert "never fire" in str(e.value)


def test_a_door_spanning_a_narrow_full_wall_has_no_standable_window():
    """The measured zero-crossing of the standable window is 2 * R_WALK (160u): a wall exactly that
    wide leaves a zero-WIDTH line, and anything narrower leaves nothing. This is what makes the
    deleted `min_len = 192` both wrong and unnecessary -- 192 matched neither the stated reason
    (96u) nor the real radius, and G9's area test is the property that actually matters."""
    narrow = [(0, -75), (1600, -75), (1600, 75), (0, 75)]        # 150u < 2 * R_WALK
    quad = F.door_strip(narrow, ((0.0, -75.0), (0.0, 75.0)), 250.0)
    assert F.strip_standable_fraction(narrow, quad)[1] == []
    wide = [(0, -250), (1600, -250), (1600, 250), (0, 250)]      # 500u -- comfortably standable
    quad2 = F.door_strip(wide, ((0.0, -250.0), (0.0, 250.0)), 250.0)
    assert F.strip_standable_fraction(wide, quad2)[1] != []


# ------------------------------------------------------------------ C6: arrivals + the band split

def test_an_arrival_too_close_to_a_wall_is_refused_with_the_shove_distance():
    why = F.arrival_problem((-2400 + 50, 0), ROOM_A, [])
    assert why is not None and "shoved" in why
    assert F.arrival_problem((-2400 + 80, 0), ROOM_A, []) is None


def test_an_arrival_inside_its_rooms_own_door_band_does_not_warn():
    """★ The band test WITHOUT a lateral cap fires on every door in every dungeon: an arrival sits
    directly inward from its own door, so it shares that door's perpendicular band by construction.
    Noise drowns the finding that matters."""
    c = F.compose(_plan())
    assert not any("band" in w for w in c.warnings), c.warnings


def test_an_arrival_one_step_beside_a_DIFFERENT_zone_does_warn():
    """...and this is the finding that matters -- the Lantern Hall class."""
    zone = [{"zone": [(0, -300), (0, 300), (-250, 300), (-250, -300)], "label": "the door"}]
    assert F.band_warnings((-350, 0), zone), "100u to the side, in-band -> must warn"
    assert not F.band_warnings((-1250, 0), zone), "1000u away is a deliberate walk, not a step"


def test_the_band_rule_is_a_warning_because_an_error_would_refuse_shipping_ff9():
    """Square's own field-100 entrance 231 sits 23u clear of zone 114's x-band. A gate on values the
    composer MINTS may be stricter than Square; it may not assert Square is wrong."""
    zone = [{"zone": [(0, -300), (0, 300), (-250, 300), (-250, -300)], "label": "the door"}]
    pos = (-273, 0)                                     # 23u clear of the zone polygon
    assert F.band_warnings(pos, zone), "the band rule notices it"
    assert F.arrival_problem(pos, ROOM_A, zone) is not None, "and at 23u the ERROR does fire"
    far = (-600, 0)                                     # 350u clear -- band-aligned, error-free
    assert F.arrival_problem(far, ROOM_A, zone) is None


def test_a_room_too_shallow_for_its_door_raises_naming_the_shallowness():
    """Shallow PERPENDICULAR to the door: the arrival walks inward along the wall's normal, so what
    matters is the room's depth in that direction, not its span along the wall."""
    shallow = [(-300, -900), (0, -900), (0, 900), (-300, 900)]   # only 300u deep away from the door
    with pytest.raises(F.ComposeError) as e:
        F.arrival_for(shallow, ((0.0, -300.0), (0.0, 300.0)), [], depth=250.0)
    assert "too shallow" in str(e.value)


# ------------------------------------------------------------------ C7: the camera fit

def test_a_pitch_below_the_horizon_floor_is_refused():
    """★ The draft's fit returned distance 200 with a minimum vertex depth of -740 for a corridor at
    pitch 20 -- a camera INSIDE the room, passing a canvas-box test comfortably."""
    assert F.pitch_floor(42.0) == pytest.approx(25.64, abs=0.05)
    assert F.pitch_floor(42.2) == pytest.approx(25.73, abs=0.05)
    with pytest.raises(F.ComposeError) as e:
        F.fit_play_camera(ROOM_A, pitch=20.0, fov=42.0)
    assert "horizon" in str(e.value)


@pytest.mark.parametrize("poly", [ROOM_A, L_SHAPE, [(0, 0), (4000, 0), (4000, 1200), (0, 1200)],
                                  [(0, 0), (1200, 0), (1200, 4000), (0, 4000)]])
def test_every_fitted_vertex_clears_the_near_plane(poly):
    """THE DEPTH GATE. `cam.to_canvas` folds `abs(resz)`, so a behind-camera vertex looks like an
    ordinary in-canvas coordinate -- the depth is the only thing that can see it."""
    cam, off = F.fit_play_camera(poly, pitch=48.0, fov=42.2)
    deps = [F.project_floor(x + off[0], z + off[1], cam)[2] for x, z in poly]
    assert min(deps) >= F.NEAR_W, f"min depth {min(deps):.0f} < {F.NEAR_W}"


def test_the_fit_front_aligns_rather_than_centring():
    """Front-align won canvas fill 10/10 and always leaves ~28 rows under the front edge;
    canvas-centring left 96-201 dead rows (8.9% fill in the worst measured case)."""
    wide = [(0, 0), (4000, 0), (4000, 1200), (0, 1200)]
    cam, off = F.fit_play_camera(wide, pitch=30.0, fov=42.2)
    rows = [F.project_floor(x + off[0], z + off[1], cam)[1] for x, z in wide]
    assert max(rows) == pytest.approx(F.FRONT_ROW, abs=1.0)
    assert F.CANVAS_H - max(rows) <= 30, "front-align leaves ~28 dead rows; centring left 96-201"


def test_the_pitch_gate_refuses_a_horizon_inside_the_canvas_but_only_warns_above_it():
    """★ The hard boundary is `p*` (horizon at canvas row 0). The comfort margin above it is a
    WARNING, not a refusal, because `imagefield.DEFAULT_PITCH` is 26.0 while `p*` is 25.73 at
    fov 42.2 -- an error at `p* + 1` would refuse the trace lane's own default pitch."""
    pstar = F.pitch_floor(42.2)
    assert pstar == pytest.approx(25.73, abs=0.05)
    with pytest.raises(F.ComposeError) as e:
        F.fit_play_camera(ROOM_A, pitch=25.0, fov=42.2)
    assert "INSIDE the canvas" in str(e.value)
    notes = []
    F.fit_play_camera(ROOM_A, pitch=26.0, fov=42.2, notes=notes)   # accepted...
    assert notes and "foreshorten" in notes[0]                     # ...with the warning
    notes2 = []
    F.fit_play_camera(ROOM_A, pitch=48.0, fov=42.2, notes=notes2)
    assert notes2 == []


def test_the_offset_uses_the_aabb_centre_not_the_centroid():
    """★ They differ by (-250, -200) on an L, which pushes a corner to canvas x 399.8 -- off a
    384-wide canvas. Every convex or symmetric fixture gives a zero delta, so only an asymmetric
    room can tell them apart."""
    x0, z0, x1, z1 = F.bbox(L_SHAPE)
    aabb_cx = -(x0 + x1) / 2.0
    n = len(L_SHAPE)
    vert_cx = -sum(p[0] for p in L_SHAPE) / n
    assert abs(aabb_cx - vert_cx) > 50, "the fixture must actually be asymmetric"
    cam, off = F.fit_play_camera(L_SHAPE, pitch=48.0, fov=42.2)
    assert off[0] == int(round(aabb_cx))


def test_off_r_is_an_integer_on_every_room():
    """`bgi.build` rounds every vert; a fractional offset lets the mesh, the quads and the arrival
    round independently and drift apart by up to 1u."""
    c = F.compose(_plan())
    for r in c.rooms:
        assert all(isinstance(v, int) for v in r.off_r)
        assert all(isinstance(v, int) for p in r.poly_room for v in p)


def test_the_private_camera_math_fork_is_retired():
    """★ THE TRIPWIRE, RESOLVED. This module used to carry its own `cam_params`/`z_for_row`/
    `horizon_row` because `cam.solve_z_for_canvasY` bisected across the projection pole and lost
    reachable low-pitch rows (measured at pitch 15 / distance 3000: rows 365/420/440 all came back
    None). cam.py's 2026-07-29 fix (closed-form on the camera's front branch) discharged that
    reason, so the fork is retired -- the composer now calls the shared solver directly. Pinned here
    so a future 'simplification' does not silently recreate the private copy."""
    assert not hasattr(F, "cam_params")
    assert not hasattr(F, "z_for_row")
    assert not hasattr(F, "horizon_row")


def test_project_floor_agrees_exactly_with_the_shared_projection():
    """`project_floor` is now a thin composition of `cam.to_canvas` + `cam.project`'s signed depth,
    not an independent formula -- so it must agree with them to machine precision, not the private
    form's former ~0.07 canvas px / up to 1.28e4-unit-off depth on a real (non-yaw-0) camera."""
    cams = [guide.make_camera(15.0, 3000.0, fov_x_deg=42.0),
            guide.make_camera(48.0, 5000.0, fov_x_deg=42.2, yaw_deg=17.0)]
    for cam in cams:
        for (x, z) in [(0.0, 0.0), (500.0, -800.0), (-1200.0, 400.0)]:
            cx, cy, dep = F.project_floor(x, z, cam)
            want_x, want_y = CAM.to_canvas((x, 0.0, z), cam)
            want_dep = CAM.project((x, 0.0, z), cam)[2]
            assert cx == pytest.approx(want_x, abs=1e-9)
            assert cy == pytest.approx(want_y, abs=1e-9)
            assert dep == pytest.approx(want_dep, abs=1e-9)


def test_frame_floor_no_longer_raises_at_this_pitch():
    """★ THE OTHER HALF OF THE TRIPWIRE. `guide.frame_floor` used to raise at pitch 15 / distance
    3000 for EVERY distance -- not because the floor was actually unreachable, but because it
    inherited solve_z_for_canvasY's pole-spanning bisection (see cam.py's 2026-07-29 fix; fenced in
    ff9mapkit/tests/test_cameras.py::test_frame_floor_low_pitch_frames_on_the_requested_rows). It now
    succeeds and lands on the requested rows, matching floorplan's own private frame at the same
    camera."""
    cam = guide.make_camera(15.0, 3000.0, fov_x_deg=42.0)
    fr = guide.frame_floor(cam)          # defaults: back=130, front=420
    assert CAM.to_canvas((0, 0, fr.zb), cam)[1] == pytest.approx(130.0, abs=1.0)
    assert CAM.to_canvas((0, 0, fr.zf), cam)[1] == pytest.approx(420.0, abs=1.0)


def test_a_room_laid_out_far_from_the_plan_origin_still_emits_in_range():
    """THE TWO-FRAME LAW's payoff: plan coordinates are an authoring fiction, so a dungeon drawn at
    (30000, 30000) must still ship Int16-legal room-frame verts."""
    far_a = [(x + 30000, z + 30000) for x, z in ROOM_A]
    far_b = [(x + 30000, z + 30000) for x, z in ROOM_B]
    c = F.compose(_plan(rooms=[{"name": "HALL", "poly": far_a}, {"name": "CELL", "poly": far_b}],
                        doors=[{"a": "HALL", "b": "CELL",
                                "seg": [[30000, 29700], [30000, 30300]]}]))
    for r in c.rooms:
        assert max(abs(v) for p in r.poly_room for v in p) < 32767


# ------------------------------------------------------------------ C8 + siting

def test_the_centroid_idiom_the_grid_search_replaces():
    """★ For an L the VERTEX-AVERAGE centroid -- the idiom `build.py` already uses for zone centres
    -- lands exactly ON the reflex corner and tests OUTSIDE. For a U, both centroids fall outside.
    So the grid search is load-bearing, not a fallback, and an L is the NORMAL hand-drawn room."""
    n = len(L_SHAPE)
    va = (sum(p[0] for p in L_SHAPE) / n, sum(p[1] for p in L_SHAPE) / n)
    assert not F.point_in_poly(va[0], va[1], L_SHAPE) or F.dist_to_boundary(*va, L_SHAPE) < 1e-9
    m = len(U_SHAPE)
    uva = (sum(p[0] for p in U_SHAPE) / m, sum(p[1] for p in U_SHAPE) / m)
    assert not F.point_in_poly(uva[0], uva[1], U_SHAPE)
    pt = F.interior_point(L_SHAPE, [])
    assert F.point_in_poly(pt[0], pt[1], L_SHAPE)
    assert F.dist_to_boundary(pt[0], pt[1], L_SHAPE) >= F.R_WALK


def test_the_save_points_press_zone_clears_the_spawn():
    """Both maximize distance-to-wall against the same avoid set, so without an exclusion the save
    point lands on the spawn's own cell -- and an R_WALK-sized exclusion is not enough, because the
    press zone then extends `half` back toward the spawn."""
    c = F.compose(_plan(rooms=[{"name": "HALL", "poly": ROOM_A, "savepoint": {}},
                               {"name": "CELL", "poly": ROOM_B}]))
    h = c.by_name("HALL")
    press = [tuple(p) for p in h.toml["savepoint"][0]["zone"]]
    spawn = tuple(h.toml["player"]["spawn"])
    assert F.dist_point_to_poly(spawn, press) >= F.R_WALK


def test_an_empty_savepoint_table_still_requests_a_savepoint():
    """A bare `savepoint = {}` means 'yes, defaults'. Testing it for truthiness drops the request
    silently -- the quietly-wrong-default class THE DEFAULT-VALUE LAW refuses."""
    for value in ({}, True):
        c = F.compose(_plan(rooms=[{"name": "HALL", "poly": ROOM_A, "savepoint": value},
                                   {"name": "CELL", "poly": ROOM_B}]))
        assert "savepoint" in c.by_name("HALL").toml, f"savepoint={value!r} was dropped"


# ------------------------------------------------------------------ G4 / G11: overlap

def test_two_overlapping_rooms_are_refused_naming_both():
    with pytest.raises(F.ComposeError) as e:
        F.compose(_plan(rooms=[{"name": "HALL", "poly": ROOM_A},
                               {"name": "CELL", "poly": [(-1200, -900), (1200, -900),
                                                         (1200, 900), (-1200, 900)]}],
                        doors=[]))
    assert "HALL" in str(e.value) and "CELL" in str(e.value) and "overlap" in str(e.value)


def test_two_rooms_may_abut_along_a_shared_wall():
    assert not F.polys_overlap(ROOM_A, ROOM_B)


def test_two_bevelled_strips_that_only_the_aabb_judge_thinks_overlap():
    """★ `build.region_overlap_pairs` is an AABB test: two provably disjoint 45deg bevel strips make
    it report a pair. Erroring on that would refuse every bevelled or diagonal room."""
    # two parallel 45deg strips ~141u wide, offset 300u along their shared PERPENDICULAR -- so they
    # cannot touch, while their axis-aligned bounding boxes interleave heavily.
    s1 = [(0, 0), (400, 400), (300, 500), (-100, 100)]
    s2 = [(x + 212, z - 212) for x, z in s1]
    assert not F.polys_overlap(s1, s2), "the exact judge sees them apart"
    b1, b2 = F.bbox(s1), F.bbox(s2)
    assert not (b1[2] <= b2[0] or b2[2] <= b1[0] or b1[3] <= b2[1] or b2[3] <= b1[1]), (
        "their AABBs DO intersect -- which is exactly why an AABB judge false-positives here, and "
        "why G4 confirms every candidate pair with the exact test instead of erroring on the box")
    near = [(x + 60, z - 60) for x, z in s1]         # ~85u perpendicular: a genuine overlap
    assert F.polys_overlap(s1, near)


# ------------------------------------------------------------------ ids

def test_preflight_skips_taken_ids_and_the_engine_world_hole():
    assert F.preflight_ids(3, id_base=30500, taken={30501}) == [30502, 30503, 30504]
    assert F.preflight_ids(3, id_base=8999, taken=set()) == [9013, 9014, 9015]
    assert F.preflight_ids(2, id_base=30500, taken=set()) == [30500, 30501]


def test_the_kit_id_helpers_this_replaces():
    """★ Each obvious candidate fails differently, and the failures are silent-ish. Pinned so nobody
    'simplifies' the pre-flight back onto them."""
    with pytest.raises(ValueError):
        pack.suggest_ids(30500, 3)                    # caps at CUSTOM_ID_MAX = 9899
    assert pack.check_custom_id(9005) == 9005         # no carve-out for the 9000-9012 world hole


def test_a_hand_pinned_id_inside_the_world_hole_is_refused():
    with pytest.raises(F.ComposeError) as e:
        F.compose(_plan(rooms=[{"name": "HALL", "poly": ROOM_A, "id": 9005},
                               {"name": "CELL", "poly": ROOM_B, "id": 9006}]))
    assert "9000" in str(e.value)


def test_a_live_registration_collision_is_refused():
    with pytest.raises(F.ComposeError) as e:
        F.compose(_plan(rooms=[{"name": "HALL", "poly": ROOM_A, "id": 30500},
                               {"name": "CELL", "poly": ROOM_B, "id": 30501}]),
                  taken_ids={30501})
    assert "already registered" in str(e.value)


# ------------------------------------------------------------------ the emit

def test_every_arrival_row_carries_an_explicit_face():
    """★ G10. `content/npc.py:372` emits NO D9(6) write for a face-less row, and the template's
    unconditional default is a hard-coded 0 = SOUTH -- so a missing face is a silent 'face the
    camera whichever wall you walked through', and no other gate fires."""
    c = F.compose(_plan(entry="HALL"))
    for r in c.rooms:
        rows = r.toml["player"]["arrival"]
        assert rows, "every room needs at least one arrival row"
        for row in rows:
            assert isinstance(row["face"], int)
        assert isinstance(r.toml["player"]["face"], int), "[player] face is mandatory too"
        zero = [x for x in rows if x["entrance"] == 0]
        assert len(zero) == (1 if r.name == c.entry else 0), (
            "the explicit entrance-0 row goes on the ENTRY room only -- elsewhere it is redundant "
            "(an unmatched D8:2 falls through to [player] spawn/face, which is what the row says) "
            "and it draws a spurious lint_campaign g2 advisory")
        for z in zero:
            assert z["face"] == r.toml["player"]["face"], (
                "the entrance-0 row and [player] face compile to the SAME D9(6) const, so a "
                "disagreement is unrepresentable, not merely odd")
            assert z["pos"] == r.toml["player"]["spawn"]


def test_arrival_rows_live_under_player_not_a_dotted_key():
    c = F.compose(_plan())
    raw = c.by_name("HALL").toml
    assert "arrival" in raw["player"]
    assert "player.arrival" not in raw


def test_entrance_numbers_are_namespaced_per_destination():
    """Both rooms independently number their inbound door `entrance = 1`. D8:2 is read by the
    destination's own if-chain, so reuse across rooms is correct."""
    c = F.compose(_plan(entry="HALL"))
    for r in c.rooms:
        assert r.toml["gateway"][0]["entrance"] == 1, "both rooms number their inbound door 1"
        want = {0, 1} if r.name == c.entry else {1}
        assert {x["entrance"] for x in r.toml["player"]["arrival"]} == want


def test_gateway_zones_have_four_corners():
    """The build calls `content.gateway.quad_zone` for us at three sites; four keeps
    `region_overlap_pairs`' `zone[:4]` truncation harmless."""
    c = F.compose(_plan())
    for r in c.rooms:
        for g in r.toml["gateway"]:
            assert len(g["zone"]) == 4


def test_a_gateway_never_targets_field_zero():
    """The Field(0) black-screen softlock, playtest-confirmed 2026-07-29."""
    c = F.compose(_plan())
    for r in c.rooms:
        for g in r.toml["gateway"]:
            assert isinstance(g["to"], int) and g["to"] > 0


def test_a_one_way_door_emits_no_return_gateway_but_still_an_arrival():
    c = F.compose(_plan(doors=[{"a": "HALL", "b": "CELL",
                                "seg": [list(DOOR[0]), list(DOOR[1])], "two_way": False}]))
    assert len(c.by_name("HALL").toml.get("gateway", [])) == 1
    assert "gateway" not in c.by_name("CELL").toml
    assert {x["entrance"] for x in c.by_name("CELL").toml["player"]["arrival"]} == {1}


def test_an_encounter_typo_is_refused_because_the_build_will_not_catch_it():
    """★ `build.py` hard-errors on an unknown `[[savepoint]]` key (`_sp_keys`) but there is no
    `_enc_keys` anywhere, so `feq` for `freq` builds clean and silently runs at the default."""
    with pytest.raises(F.ComposeError) as e:
        F.compose(_plan(rooms=[{"name": "HALL", "poly": ROOM_A,
                                "encounter": {"scene": 5, "feq": 220}},
                               {"name": "CELL", "poly": ROOM_B}]))
    assert "feq" in str(e.value)


def test_an_encounter_without_a_scene_is_refused():
    with pytest.raises(F.ComposeError) as e:
        F.compose(_plan(rooms=[{"name": "HALL", "poly": ROOM_A, "encounter": {"freq": 200}},
                               {"name": "CELL", "poly": ROOM_B}]))
    assert "scene" in str(e.value)


def test_an_unreachable_room_warns_rather_than_blocking():
    """The composer is an iterative authoring tool -- a not-yet-connected room is normal mid-session."""
    c = F.compose(_plan(rooms=[{"name": "HALL", "poly": ROOM_A}, {"name": "CELL", "poly": ROOM_B},
                               {"name": "VAULT", "poly": [(0, 1200), (1200, 1200),
                                                          (1200, 2400), (0, 2400)]}]))
    assert any("VAULT" in w and "unreachable" in w for w in c.warnings)


# ------------------------------------------------------------------ 6b: the emit to disk

def _canvas_aabb(pts, cam):
    p = [F.project_floor(x, z, cam)[:2] for x, z in pts]
    return (min(q[0] for q in p), min(q[1] for q in p),
            max(q[0] for q in p), max(q[1] for q in p))


def _opaque_aabb(png_path, scale=4):
    """The AABB of a PNG's non-transparent pixels, in CANVAS units (the layers ship at 4x)."""
    import struct
    import zlib
    raw = png_path.read_bytes()
    i, idat, W, H = 8, b"", 0, 0
    while i < len(raw):
        n = struct.unpack(">I", raw[i:i + 4])[0]
        typ, body = raw[i + 4:i + 8], raw[i + 8:i + 8 + n]
        if typ == b"IHDR":
            W, H = struct.unpack(">II", body[:8])
        if typ == b"IDAT":
            idat += body
        i += 12 + n
    buf = zlib.decompress(idat)
    stride = W * 4
    x0 = y0 = 10 ** 9
    x1 = y1 = -10 ** 9
    for y in range(H):
        row = buf[y * (stride + 1) + 1:(y + 1) * (stride + 1)]
        for x in range(W):
            if row[x * 4 + 3]:
                x0, x1 = min(x0, x), max(x1, x)
                y0, y1 = min(y0, y), max(y1, y)
    return (x0 / scale, y0 / scale, (x1 + 1) / scale, (y1 + 1) / scale)


def test_emit_writes_a_buildable_campaign_tree(tmp_path):
    c = F.compose(_plan())
    wrote = F.emit(c, tmp_path, plan=_plan())
    assert (tmp_path / "campaign.toml").is_file()
    assert (tmp_path / F.SIDECAR).is_file()
    for room in ("HALL", "CELL"):
        d = tmp_path / room
        assert (d / f"{room.lower()}.field.toml").is_file()
        assert (d / "walkmesh.obj").is_file()
        assert (d / "art" / "back.png").is_file()
        assert (d / "art" / "floor.png").is_file()
    assert wrote["ids"] == [30500, 30501]


def test_the_emitted_campaign_lints_clean(tmp_path):
    """Including g2: the entrance-0 row goes on the ENTRY room only, so no room draws a spurious
    'entrance 0 is not routed here by any campaign edge' advisory."""
    from ff9mapkit import campaign as C
    F.emit(F.compose(_plan()), tmp_path, plan=_plan())
    plan = C.load_campaign(tmp_path / "campaign.toml")
    errors, warns = C.lint_campaign(plan, tmp_path)
    assert errors == [], errors
    assert warns == [], warns


def test_the_entrance_zero_row_is_on_the_entry_room_only():
    c = F.compose(_plan(entry="HALL"))
    assert 0 in {r["entrance"] for r in c.by_name("HALL").toml["player"]["arrival"]}
    assert 0 not in {r["entrance"] for r in c.by_name("CELL").toml["player"]["arrival"]}


def test_the_walkmesh_obj_is_the_drawn_polygon_in_true_world_coords(tmp_path):
    F.emit(F.compose(_plan()), tmp_path, plan=_plan())
    lines = (tmp_path / "HALL" / "walkmesh.obj").read_text().splitlines()
    verts = [tuple(float(v) for v in ln.split()[1:]) for ln in lines if ln.startswith("v ")]
    assert all(v[1] == 0.0 for v in verts), "the floor plane is y=0"
    got = {(round(v[0]), round(v[2])) for v in verts}
    assert got == set(F.compose(_plan()).by_name("HALL").poly_room)


@pytest.mark.parametrize("poly", [ROOM_A, L_SHAPE])
def test_the_painted_floor_matches_the_walkmesh(poly, tmp_path):
    """★ G15. `write_placeholders` takes a rectangular FloorFrame, so without `floor_tris` the
    checkerboard covers ground the player cannot reach -- measured 68% unwalkable on a composed room,
    which inverts the placeholder's own stated purpose as an in-game alignment check and makes the
    human report a walkmesh bug that does not exist."""
    from ff9mapkit.scene import placeholder
    cam, off = F.fit_play_camera(poly, pitch=48.0, fov=42.2)
    room = [(x + off[0], z + off[1]) for x, z in poly]
    verts, faces = IF.triangulate(room)
    tris = [(verts[a], verts[b], verts[c]) for a, b, c in faces]
    back, floor = tmp_path / "back.png", tmp_path / "floor.png"
    placeholder.write_placeholders(cam, None, back, floor, floor_tris=tris)
    wx0, wy0, wx1, wy1 = _canvas_aabb(room, cam)
    px0, py0, px1, py1 = _opaque_aabb(floor)
    for got, want, axis in ((px0, wx0, "x0"), (px1, wx1, "x1"), (py0, wy0, "y0"), (py1, wy1, "y1")):
        assert abs(got - want) <= F.FIT_MARGIN, f"{axis}: painted {got:.1f} vs walkmesh {want:.1f}"


def test_the_notch_of_an_l_shaped_room_is_left_unpainted(tmp_path):
    """The clip has to be by the real footprint, not its bounding box."""
    from ff9mapkit.scene import placeholder
    cam, off = F.fit_play_camera(L_SHAPE, pitch=48.0, fov=42.2)
    room = [(x + off[0], z + off[1]) for x, z in L_SHAPE]
    verts, faces = IF.triangulate(room)
    tris = [(verts[a], verts[b], verts[c]) for a, b, c in faces]
    placeholder.write_placeholders(cam, None, tmp_path / "b.png", tmp_path / "f.png",
                                   floor_tris=tris)
    # the notch corner of the L, well inside the AABB but outside the footprint
    x0, z0, x1, z1 = F.bbox(room)
    notch = (x1 - (x1 - x0) * 0.15, z1 - (z1 - z0) * 0.15)
    assert not F.point_in_poly(notch[0], notch[1], room), "the probe point must be in the notch"
    import struct
    import zlib
    raw = (tmp_path / "f.png").read_bytes()
    i, idat, W, H = 8, b"", 0, 0
    while i < len(raw):
        n = struct.unpack(">I", raw[i:i + 4])[0]
        typ, body = raw[i + 4:i + 8], raw[i + 8:i + 8 + n]
        if typ == b"IHDR":
            W, H = struct.unpack(">II", body[:8])
        if typ == b"IDAT":
            idat += body
        i += 12 + n
    buf = zlib.decompress(idat)
    cx, cy = F.project_floor(notch[0], notch[1], cam)[:2]
    px, py = int(cx * 4), int(cy * 4)
    assert 0 <= px < W and 0 <= py < H
    assert buf[py * (W * 4 + 1) + 1 + px * 4 + 3] == 0, "the notch must be TRANSPARENT"


def test_an_encounter_scene_name_is_resolved_to_an_id_in_the_emitted_toml():
    """★ `build.py:6379` compiles the encounter with a bare `int(e["scene"])`, so a catalog NAME --
    which the LINT resolves and reports on happily -- dies at build time as `invalid literal for
    int()`. The author's spelling stays in the sidecar; the toml carries the id."""
    c = F.compose(_plan(rooms=[{"name": "HALL", "poly": ROOM_A},
                               {"name": "CELL", "poly": ROOM_B,
                                "encounter": {"scene": "BSC_CA_E013", "freq": 180}}]))
    assert c.by_name("CELL").toml["encounter"]["scene"] == 296
    assert any("resolved to id 296" in w for w in c.warnings)


def test_emit_refuses_a_non_consecutive_id_run(tmp_path):
    c = F.compose(_plan())
    c.rooms[1].field_id = 30599
    with pytest.raises(F.ComposeError) as e:
        F.emit(c, tmp_path)
    assert "consecutive" in str(e.value)


def test_the_sidecar_round_trips(tmp_path):
    p = _plan()
    F.save_plan(p, tmp_path / F.SIDECAR)
    back = F.load_plan(tmp_path / F.SIDECAR)
    assert back["version"] == 1
    assert F.compose(back).by_name("HALL").field_id == 30500


def test_the_cli_verb_is_registered():
    from ff9mapkit import cli
    parser = cli.build_parser()
    args = parser.parse_args(["floorplan", "plan.json", "--out", "d", "--no-preflight"])
    assert args.func is cli._cmd_floorplan
    assert args.plan == "plan.json" and args.out == "d" and args.no_preflight is True


def test_compose_collects_every_problem_not_just_the_first():
    with pytest.raises(F.ComposeError) as e:
        F.compose(_plan(rooms=[{"name": "A", "poly": [(0, 0), (900, 0), (900, 900),
                                                      (450, -300), (0, 900)]},
                               {"name": "B", "poly": [(0, 0), (100, 0), (100, 5)]}],
                        doors=[]))
    assert len(e.value.problems) >= 2, e.value.problems


# ================================================================== the live gate's speed work
# The Floorplan tab re-runs the WHOLE of `compose` after every gesture, so `compose`'s cost IS the
# tab's responsiveness. Every gesture cost what DRAWING the plan cost -- ~17s on eight rooms --
# because nothing survived a judge. A stall, not a live gate. It is now ~0.6s and FLAT in room
# count. Everything in this
# block exists because that work is a byte-level rewrite of the gate's core, and the one invariant
# it must never move is THE VERDICT.
#
# Reproduce the numbers with `py studies/click-authoring/gate_bench.py` (and `--drag 8`).


def _reference_standable_map(poly, *, R=F.R_WALK, step=F.GRID_STEP):
    """The ORIGINAL double loop, pinned here verbatim, as the oracle for the scanline rewrite.

    Do not tidy it, do not share helpers with the implementation, and do not "keep it in sync" --
    its whole value is that it is the code that shipped BEFORE the optimization, so the fast path
    has something independent to be caught against."""
    x0, z0, x1, z1 = F.bbox(poly)
    out = {}
    x = x0
    while x <= x1 + step:
        z = z0
        while z <= z1 + step:
            if F.point_in_poly(x, z, poly):
                d = F.dist_to_boundary(x, z, poly)
                if d >= R:
                    out[(int(math.floor(x / step)), int(math.floor(z / step)))] = d
            z += step
        x += step
    return out


def _sweep_polys():
    """rect / L / U / trapezoid / corridor / jittered n-gons -- plus deliberately awkward offsets.
    The cell grid is ABSOLUTE (`floor(x/step)`) while the sample walk starts at the polygon's own
    bbox, so where a room sits relative to the origin decides which samples land in which cell, and
    a fractional offset is what makes the two samplers able to disagree at all.

    ★ Deliberately SMALL rooms. What this sweep tests -- the scanline's half-open spans against
    `point_in_poly`'s strict `x < xin`, and the arithmetic pinning -- is sensitive to SHAPE and
    OFFSET, not to size, and the oracle is the slow double loop the rewrite replaced. At real room
    sizes the sweep cost 165s and would simply have been deleted by the first person in a hurry."""
    out = [[(-600, -225), (0, -225), (0, 225), (-600, 225)],
           [(0, -225), (600, -225), (600, 225), (0, 225)],
           [(0, 0), (700, 0), (700, 300), (300, 300), (300, 700), (0, 700)],          # an L
           [(0, 0), (900, 0), (900, 700), (600, 700), (600, 280),
            (300, 280), (300, 700), (0, 700)],                                        # a U
           [(-334.5, 177.25), (365.5, 177.25), (365.5, 702.25), (-334.5, 702.25)],    # off-grid
           [(300, 300), (900, 300), (900, 460), (300, 460)],           # a corridor, mostly empty
           [(0, 0), (800, 0), (650, 560), (150, 560)],                 # trapezoid: no axis edge
           [(0, 0), (640, 0), (640, 200), (360, 200), (360, 640), (0, 640)]]
    for i in range(8):                                   # bevels and diagonals
        n = 3 + i % 6
        cx, cz, rad = 130.0 * i - 300.0, 90.0 * i, 260.0 + 47.0 * i
        out.append([(cx + rad * math.cos(2 * math.pi * k / n + 0.21 * i),
                     cz + rad * math.sin(2 * math.pi * k / n + 0.21 * i)) for k in range(n)])
    return [p for p in out if F.polygon_problem(p) is None]


def test_the_scanline_sampler_is_bitwise_the_original_double_loop():
    """★ THE SWEEP `standable_map`'s docstring PROMISES. Without it the composer's core sampler is
    a rewrite with nothing watching it -- and this suite was measured staying green against a
    materially different cell set, so "everything passed" is not the fence.

    BITWISE, not approximately: the cell SET and every distance. The rewrite deliberately keeps the
    division rather than a hoisted reciprocal, and `x - (ax + t*dx)` rather than `(x - ax) - t*dx`,
    precisely so this can be an equality -- both "identical" shortcuts were measured moving the
    distance on 60 of 240 polygons, and `interior_point` ranks on `round(d, 3)`."""
    checked = nonempty = 0
    for poly in _sweep_polys():
        for R in (F.R_WALK, 48.0, 96.0, 20.0):
            for step in (F.GRID_STEP, 4.0, 16.0):
                ref = _reference_standable_map(poly, R=R, step=step)
                got = F.standable_map(poly, R=R, step=step)
                assert set(got) == set(ref), (
                    f"cell set moved at R={R} step={step}: "
                    f"{len(set(ref) - set(got))} missing, {len(set(got) - set(ref))} extra")
                assert got == ref, f"distances drifted at R={R} step={step}"
                checked += 1
                nonempty += bool(ref)
    assert checked >= 150, f"the sweep only ran {checked} cases"
    # a sweep that compared empty against empty would pass while asserting nothing at all
    assert nonempty >= checked // 2, f"only {nonempty}/{checked} cases had any standable cell"


def test_standable_is_still_exactly_the_maps_key_set():
    for poly in (ROOM_A, L_SHAPE, U_SHAPE):
        assert F.standable(poly) == set(F.standable_map(poly))


def test_the_sample_distance_is_not_the_cell_centre_distance():
    """★ THE TRAP THAT LOOKS LIKE A FREE OPTIMIZATION. `standable_map` returns the distance at the
    grid SAMPLE (walked from the polygon's own bbox); `interior_point` ranks on the distance at the
    absolute CELL CENTRE, `(i + 0.5) * step`. Reusing the map's number instead of re-measuring is
    the obvious win, and it MOVED THE SPAWN a whole cell on 4 of 22 random plans that composed.

    This fence exists so the next reader who spots that "redundant" second measurement learns why
    it is there from a red test rather than from a playtest."""
    poly = [(-1234.5, 777.25), (1165.5, 777.25), (1165.5, 2577.25), (-1234.5, 2577.25)]
    m = F.standable_map(poly)
    step = F.GRID_STEP
    differ = [c for c in m
              if m[c] != F.dist_to_boundary((c[0] + 0.5) * step, (c[1] + 0.5) * step, poly)]
    assert differ, ("the two measurements happened to agree on this fixture -- pick a polygon whose "
                    "bbox is off the sample grid, or this fence is asserting nothing")


# ------------------------------------------------------------------ GeomCache: a memo, not a verdict

def _verdict(plan, **kw):
    """Everything a caller of `compose` can observe, flattened."""
    try:
        c = F.compose(plan, **kw)
    except F.ComposeError as e:
        return ("refused", tuple(e.problems))
    return ("ok", c.name, c.entry, tuple(c.warnings),
            tuple((r.name, r.field_id, r.off_r, r.pitch, r.distance, repr(r.toml), repr(r.verts))
                  for r in c.rooms))


def _corpus():
    """One of each verdict shape the cache has to survive -- clean, self-intersecting, no standable
    interior, overlapping, a door too shallow, an unreachable room, an L and a U."""
    return [
        _plan(),
        _plan(doors=[{"a": "HALL", "b": "CELL", "seg": [list(DOOR[0]), list(DOOR[1])],
                      "depth": 100.0}]),
        _plan(doors=[]),                                          # unreachable CELL -> a warning
        _plan(rooms=[{"name": "A", "poly": [(0, 0), (900, 0), (900, 900), (450, -300), (0, 900)]}],
              doors=[]),                                          # self-intersecting
        _plan(rooms=[{"name": "A", "poly": [(0, 0), (3000, 0), (3000, 120), (0, 120)]}],
              doors=[]),                                          # nowhere to stand
        _plan(rooms=[{"name": "A", "poly": [(0, 0), (2400, 0), (2400, 1800), (0, 1800)]},
                     {"name": "B", "poly": [(1200, 0), (3600, 0), (3600, 1800), (1200, 1800)]}],
              doors=[]),                                          # overlapping
        _plan(rooms=[{"name": "L", "poly": L_SHAPE}], doors=[]),
        _plan(rooms=[{"name": "U", "poly": U_SHAPE, "savepoint": True}], doors=[]),
    ]


def test_a_warm_cache_never_changes_a_verdict():
    """★ THE ONE INVARIANT THE WHOLE OPTIMIZATION RIDES ON. A `GeomCache` carried across judges is
    the difference between ~17s and ~0.6s per gesture, and it is worth exactly nothing if a hit can
    say something a miss would not.

    Every plan is judged three ways -- cold, through a cache that has never seen it, and through a
    cache warmed on the WHOLE corpus first, so a refusal is memoized before a success asks about the
    same room and vice versa. `GeomCache.interior_point` memoizes its `ComposeError` as messages,
    and that path has both directions to get wrong."""
    corpus = _corpus()
    cold = [_verdict(p) for p in corpus]

    fresh = F.GeomCache()
    assert [_verdict(p, cache=fresh) for p in corpus] == cold, "a cold cache changed a verdict"

    warm = F.GeomCache()
    for p in corpus:
        _verdict(p, cache=warm)
    assert [_verdict(p, cache=warm) for p in corpus] == cold, "a warm cache changed a verdict"
    assert warm.hits > 0, "the corpus never exercised a hit -- this fence is asserting nothing"

    twice = F.GeomCache()                     # the same plan judged again, which is what typing does
    for p, want in zip(corpus, cold):
        assert _verdict(p, cache=twice) == want
        assert _verdict(p, cache=twice) == want


def test_the_cache_evicts_and_a_re_judge_after_eviction_is_still_right():
    """A slow drag mints a new polygon every judge, so an unbounded memo would grow for the whole
    session. The LRU cap is the guard -- and a plan judged again after its entries were evicted must
    give the same answer. Eviction may cost time; it may never cost truth."""
    plan = _plan()
    want = _verdict(plan)
    tiny = F.GeomCache(limit=1)
    for k in range(6):                        # six distinct plans, evicting each other out
        _verdict(_plan(rooms=[{"name": "A", "poly": [(0, 0), (2400 + k, 0),
                                                     (2400 + k, 1800), (0, 1800)]}], doors=[]),
                 cache=tiny)
    assert _verdict(plan, cache=tiny) == want
    for store in tiny._stores():
        assert len(store) <= 1, f"the LRU cap did not hold: {len(store)} entries"
    assert not tiny._maps, "the transient cell maps outlived their compose"


def test_the_cache_still_hits_on_a_plan_bigger_than_its_cap():
    """★ THE CLIFF. `compose` touches each key exactly ONCE per judge, in a fixed order — a cyclic
    scan, which is the one access pattern an LRU is pathological on. Above the cap the hit rate is
    not degraded, it is EXACTLY ZERO: the entry evicted is always the one wanted next.

    Measured on the first version of this cache, chained rooms with one door each at `limit=64`:
    32 doors -> 291/291 hits in 0.04s; **33 doors -> 102/300 hits and 9.0 seconds**. A 25-room grid
    dungeon put one gesture back at 4.3s, and the tab's own test plan only goes to 12 rooms, so no
    playtest could have found it. The fix was to memoize the REDUCTIONS rather than the geometry,
    which made entries small enough for a cap no real plan can reach.

    This judges a plan with more doors than the OLD cap through one cache twice and demands the
    second judge be almost entirely hits. It fails on any design that stores fat values."""
    n = 40
    w, h, span = 900.0, 1100.0, 700.0
    rooms = [{"name": f"R{i + 1}", "poly": [[i * w, 0.0], [i * w + w, 0.0],
                                            [i * w + w, h], [i * w, h]]} for i in range(n)]
    doors = [{"a": f"R{i}", "b": f"R{i + 1}",
              "seg": [[i * w, (h - span) / 2], [i * w, (h + span) / 2]]} for i in range(1, n)]
    plan = _plan(rooms=rooms, doors=doors, entry="R1")

    cache = F.GeomCache()
    first = _verdict(plan, cache=cache)
    hits, misses = cache.hits, cache.misses
    second = _verdict(plan, cache=cache)
    gained_h, gained_m = cache.hits - hits, cache.misses - misses

    assert second == first
    assert gained_h + gained_m > 200, "the plan is too small to exercise the cap"
    assert gained_m == 0, (
        f"re-judging an unchanged {n}-room plan missed {gained_m} of {gained_h + gained_m} — the "
        f"LRU is evicting what the next judge asks for next (cap {cache.limit})")


def test_the_cache_does_not_retain_the_grid_maps_between_judges():
    """★ THE GIGABYTE. Holding full cell maps across judges retained **1.28 GB** in one tab after
    about nine seconds of dragging a two-room plan — 64 poses x a 58,000-cell map — and roughly
    half of it was never read at all: `compose` consumes the component list as `len()` and the
    strip's point list as `if not pts`.

    The durable stores now hold tuples of ints and floats; the full maps are scoped to one compose.
    This pins BOTH halves: nothing map-shaped survives a compose, and the durable entries stay
    small no matter how long the drag."""
    import sys

    cache = F.GeomCache()
    poly = [[0, 0], [2400, 0], [2400, 1800], [0, 1800]]
    for k in range(12):                       # twelve drag poses of one full-size room
        p = [[x, z] for x, z in poly]
        p[2][0] += k
        _verdict(_plan(rooms=[{"name": "A", "poly": p}], doors=[]), cache=cache)

    assert not cache._maps, "a full cell map outlived its compose"
    for store in cache._stores():
        for value in store.values():
            assert sys.getsizeof(value) < 1024, f"a durable entry is {sys.getsizeof(value)} bytes"
            for part in (value if isinstance(value, tuple) else ()):
                assert not isinstance(part, (dict, set, list)), (
                    f"a durable entry holds a {type(part).__name__} — that is the container whose "
                    f"retention cost 1.28 GB")


def test_the_geom_cache_survives_concurrent_judges():
    """★ The tab hands ONE cache to N daemon worker threads -- `judge_now` starts one per gesture
    and a burst leaves several alive at once. `OrderedDict` is not safe across an interleaved
    `move_to_end` / `__setitem__` / `popitem`, so `GeomCache._get` locks. Unlocked, this is the kind
    of defect that surfaces once a week on somebody else's machine."""
    import threading

    corpus = _corpus()
    want = [_verdict(p) for p in corpus]
    shared = F.GeomCache()
    got = [None] * (len(corpus) * 4)
    errors = []

    def run(slot, plan):
        try:
            got[slot] = _verdict(plan, cache=shared)
        except Exception as e:                             # noqa: BLE001
            errors.append(f"{type(e).__name__}: {e}")

    threads = [threading.Thread(target=run, args=(i * len(corpus) + j, p))
               for i in range(4) for j, p in enumerate(corpus)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(120)
    assert not errors, errors
    assert got == want * 4


# ------------------------------------------------------------------ cancellation

def test_a_cancelled_compose_is_not_a_refusal():
    """`ComposeCancelled` is deliberately NOT a `ComposeError`: a superseded judge has found no
    problem with the plan, and anything treating it as one paints a refusal the author never
    earned. The tab's `_judge_work` catches it explicitly, ahead of its catch-all, for this."""
    with pytest.raises(F.ComposeCancelled):
        F.compose(_plan(), cancel=lambda: True)
    assert not isinstance(F.ComposeCancelled(), F.ComposeError)


def test_cancel_is_polled_often_enough_to_matter():
    """A hook nobody polls is a wish. This pins that the poll happens per ROOM (and per door), not
    once at the top: worst-case cancel latency is one room's work, not a whole plan's."""
    calls = []
    plan = _plan(rooms=[{"name": f"R{i}", "poly": [(3000 * i, 0), (3000 * i + 2400, 0),
                                                   (3000 * i + 2400, 1800), (3000 * i, 1800)]}
                        for i in range(4)], doors=[])
    with pytest.raises(F.ComposeCancelled):
        F.compose(plan, cancel=lambda: (calls.append(1), len(calls) > 3)[1])
    assert len(calls) == 4, f"cancel was polled {len(calls)} times over a 4-room plan"


def test_compose_without_a_cancel_hook_is_unchanged():
    assert _verdict(_plan(), cancel=None) == _verdict(_plan())


# ============================================ the abutment that "overlapped" (first contact, step 4)
# "that welding broke it i think. i assembled 2 rooms and now it says they overlap"
#
# Welding did not break it. `segments_cross` had filed a cross product of EXACTLY ZERO -- an
# endpoint resting on the other segment -- on the negative side, so a TOUCH read as a CROSSING.
# It was latent for the composer's whole life because nothing could produce exact contact: hand
# aimed corners land within `shared_edges`' 8u but never on the same integer. Snapping made
# abutments exact and the first author to use it was told their rooms shared floor area.


def test_the_shared_corner_that_read_as_a_crossing():
    """★ THE ZERO. Two walls meeting at a shared corner give cross products of EXACTLY 0, and
    `(d1 > 0) != (d2 > 0)` files 0 with the negative side -- so both halves of `segments_cross`
    come out True and a touch reads as a crossing. THAT IS STILL TRUE and deliberately so (the
    primitive is inclusive on purpose); this pins the pair that exposed it, so the next reader can
    see why `polys_overlap` skips shared endpoints instead of trusting this."""
    wall = ((0.0, 0.0), (1600.0, -60.0))
    nextwall = ((1600.0, -60.0), (1700.0, 1200.0))     # shares the corner (1600, -60)
    assert F.segments_cross(*wall, *nextwall), "the inclusive primitive is the documented one"
    assert F._shares_endpoint(wall, nextwall), "...and THIS is what tells an abutment from a cross"


def test_two_rooms_sharing_a_wall_exactly_do_not_overlap():
    """The gate as the author meets it: snap ROOM2's corners onto ROOM1's, and the two must be an
    abutment, not an overlap. This is the exact pair the first session hit."""
    A = [(0.0, 0.0), (1600.0, -60.0), (1900.0, -1500.0), (-300.0, -1400.0)]
    B = [(0.0, 0.0), (1600.0, -60.0), (1700.0, 1200.0), (-500.0, 1000.0)]
    assert not F.polys_overlap(A, B), "an exactly-shared wall was read as shared floor area"
    assert F.shared_edges(A, B), "...and the shared wall must still be offered as a door"


def test_a_real_overlap_is_still_refused():
    """The tightening must not blunt the gate: rooms that genuinely interpenetrate still fail."""
    A = [(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0), (0.0, 1000.0)]
    B = [(500.0, 500.0), (1500.0, 500.0), (1500.0, 1500.0), (500.0, 1500.0)]
    assert F.polys_overlap(A, B)
    C = [(200.0, 200.0), (800.0, 200.0), (800.0, 800.0), (200.0, 800.0)]      # fully contained
    assert F.polys_overlap(A, C)


def test_an_outline_that_merely_touches_itself_is_still_refused():
    """★ HALF OF WHY THE PRIMITIVE STAYS INCLUSIVE. A wall that ENDS exactly on a non-adjacent wall
    is a degenerate outline even though nothing properly crosses -- and snapping makes that shape
    reachable by hand for the first time. Tightening `segments_cross` to strictly-proper accepted
    it, which is one of the two measured regressions that sent the fix to the caller instead."""
    poly = [(0, 0), (1000, 0), (1000, 1000), (500, 0), (0, 1000)]   # vertex 3 lands ON wall 0
    assert F.polygon_problem(poly) is not None, "a self-touching outline was accepted"
    bowtie = [(0, 0), (1000, 1000), (1000, 0), (0, 1000)]
    assert F.polygon_problem(bowtie) is not None, "a bowtie was accepted"


def test_the_overlap_judge_skips_shared_endpoints_rather_than_weakening_the_primitive():
    """★ WHERE THE FIX HAD TO GO. `segments_cross` counts a touch as a crossing, and that
    inclusiveness is LOAD-BEARING twice over: `polygon_problem` needs it (a wall ending on a
    non-adjacent wall is a degenerate outline) and `polys_overlap` needs it for PARALLEL shapes,
    whose overlap band can have every corner sitting on a boundary so that nothing properly crosses
    and no vertex is strictly inside. Tightening the primitive was MEASURED to break both -- a
    self-touching outline was accepted, and two genuinely overlapping 45deg strips were called
    disjoint. That is why the abutment fix is here and not there.

    So the abutment case is fixed at the CALLER: edge pairs that share an endpoint are skipped,
    because that is what an abutment IS."""
    a, b = (0.0, 0.0), (100.0, 0.0)
    c, d = (50.0, 0.0), (50.0, 100.0)                 # a T-junction: touches, does not cross
    assert F.segments_cross(a, b, c, d), "the primitive stays inclusive -- see the docstring"
    assert F._shares_endpoint(((0.0, 0.0), (100.0, 0.0)), ((100.0, 0.0), (100.0, 50.0)))
    assert not F._shares_endpoint(((0.0, 0.0), (100.0, 0.0)), ((50.0, 1.0), (50.0, 50.0)))


def _opaque_mask(png_path):
    """``(W, H, bytearray)`` -- 1 per non-transparent pixel. Our writer emits filter-0 rows."""
    import struct
    import zlib
    raw = png_path.read_bytes()
    i, idat, W, H = 8, b"", 0, 0
    while i < len(raw):
        n = struct.unpack(">I", raw[i:i + 4])[0]
        typ, body = raw[i + 4:i + 8], raw[i + 8:i + 8 + n]
        if typ == b"IHDR":
            W, H = struct.unpack(">II", body[:8])
        if typ == b"IDAT":
            idat += body
        i += 12 + n
    buf = zlib.decompress(idat)
    stride = W * 4
    out = bytearray(W * H)
    for y in range(H):
        row = buf[y * (stride + 1) + 1:(y + 1) * (stride + 1)]
        base = y * W
        for x in range(W):
            if row[x * 4 + 3]:
                out[base + x] = 1
    return W, H, out


def _footprint_mask(tris, cam, W, H, scale=4):
    """The exact footprint, rasterised HERE. A truth image borrowed from the code under test
    proves nothing -- this is a separate scanline, deliberately."""
    def px(x, z):
        return tuple(c * scale for c in CAM.to_canvas((x, 0.0, z), cam))

    out = bytearray(W * H)
    for tri in tris:
        p = [px(*v) for v in tri]
        ys = [q[1] for q in p]
        for y in range(max(0, int(min(ys))), min(H - 1, int(max(ys))) + 1):
            yc = y + 0.5
            xs = []
            for i in range(3):
                (xa, ya), (xb, yb) = p[i], p[(i + 1) % 3]
                if (ya <= yc < yb) or (yb <= yc < ya):
                    xs.append(xa + (yc - ya) * (xb - xa) / (yb - ya))
            if len(xs) < 2:
                continue
            for x in range(max(0, int(min(xs))), min(W - 1, int(max(xs))) + 1):
                out[y * W + x] = 1
    return out


@pytest.mark.parametrize("poly,name", [(ROOM_A, "rect"), (L_SHAPE, "L"), (U_SHAPE, "U"),
                                       ([(0, 0), (2400, -90), (2900, 1500), (1200, 2100),
                                         (-400, 1400)], "5-gon")])
def test_no_floor_paint_falls_outside_the_walkable_footprint(poly, name, tmp_path):
    """★ THE PLACEHOLDER'S SILHOUETTE IS THE ROOM'S, TO THE PIXEL.

    The dark base is filled from the triangles and was always exact. The LIGHT cells were not: each
    was drawn WHOLE if its CENTRE tested inside the footprint and dropped whole otherwise. On a
    rectangle that is invisible -- every cell is fully in or fully out -- which is why every fence
    here passed. On the freeform polygons the Floorplan tab exists to draw, it is the entire look:
    light squares hang off the edges and notches appear where a straddling cell was dropped, so the
    floor reads as a ragged chessboard rather than as the room's own footprint.

    The author's in-game screenshots of a composed 5-gon are what caught it, and the earlier
    AABB fence could not: the spill is a fraction of a cell and hides inside its FIT_MARGIN.
    Measured on that real dungeon: 2.57% and 2.87% of all painted pixels lay outside the walkable
    area -- floor the author is told they can walk on and cannot -- and 0.00% after.

    The placeholder's ONE job is to let a human see whether the walkable area matches the art. Paint
    outside the mesh does not merely look wrong; it actively lies to that check."""
    from ff9mapkit.scene import placeholder
    cam, off = F.fit_play_camera(poly, pitch=48.0, fov=42.2)
    room = [(x + off[0], z + off[1]) for x, z in poly]
    verts, faces = IF.triangulate(room)
    tris = [(verts[a], verts[b], verts[c]) for a, b, c in faces]
    floor = tmp_path / "floor.png"
    placeholder.write_placeholders(cam, None, tmp_path / "back.png", floor, floor_tris=tris)

    W, H, painted = _opaque_mask(floor)
    truth = _footprint_mask(tris, cam, W, H)
    spill = sum(1 for i in range(W * H) if painted[i] and not truth[i])
    total = sum(painted)
    assert total > 10000, f"{name}: only {total} px painted -- the fixture painted nothing"
    assert spill == 0, (
        f"{name}: {spill} of {total} painted px ({spill / total * 100:.2f}%) fall OUTSIDE the "
        f"walkable footprint -- the checkerboard is not clipped to the mesh")


@pytest.mark.parametrize("length,name", [(2400, "short"), (9800, "long"), (20000, "very long")])
def test_the_floor_layer_stays_behind_the_player_however_deep_the_room(length, name):
    """★ THE PLACEHOLDER LAYERS' DEPTHS ARE DERIVED, NOT CONSTANTS.

    FF9 sorts by OT depth with SMALLER IN FRONT, and the player's depth comes from wherever they
    are standing -- so a floor pinned at a fixed z is only behind the player while the room is
    shallow enough to keep every standing position under it. The shipped literals were 3000 (floor)
    and 4000 (backdrop). Measured on a 9762u room at camera distance 17676, the player's depth runs
    3746..4125 -- past BOTH -- so over the far half of the room the floor, and then the backdrop,
    drew ON TOP OF THE PLAYER. Found by building a deliberately long room and walking to the end.

    Every walkable position must sort in FRONT of both layers, at every room length."""
    poly = [(0, 0), (2000, 0), (2000, length), (0, length)]
    cam, off = F.fit_play_camera(poly, pitch=48.0, fov=42.2)
    room = [(x + off[0], z + off[1]) for x, z in poly]
    layers = F._placeholder_layers(room, cam)
    z = {l["image"].split("/")[-1]: l["z"] for l in layers}
    deepest = max(CAM.depth((float(x), 0.0, float(zz)), cam) for x, zz in room)
    assert z["floor.png"] > deepest, (
        f"{name} room: the floor layer sits at z={z['floor.png']} but the player reaches depth "
        f"{deepest:.0f} -- the floor draws OVER them past that point")
    assert z["back.png"] > z["floor.png"], "the backdrop must sit behind the floor"
    assert all(isinstance(l["z"], int) for l in layers), "the layer table packs z as an int"


def test_a_composed_long_room_does_not_bury_its_own_player():
    """The same law through the real composer, on the shape that found it."""
    poly = [(0, 0), (2000, 0), (2000, 9800), (0, 9800)]
    c = F.compose(_plan(rooms=[{"name": "LONG", "poly": poly}], doors=[]))
    r = c.by_name("LONG")
    z = min(l["z"] for l in r.toml["layers"])
    deepest = max(CAM.depth((float(x), 0.0, float(zz)), r.camera) for x, zz in r.poly_room)
    assert z > deepest, f"floor z {z} vs deepest standing depth {deepest:.0f}"


# ---------------------------------------------------------------- Rung 7a: the round trip and G16

def test_the_legibility_gate_is_on_the_real_games_scale():
    """★ G16's thresholds are MEASURED, not chosen. Re-derive them from the census the same way
    `character_scale_px` computes a room's, so a drift in either goes red."""
    import json
    rows = json.loads((KIT / "studies" / "click-authoring" / "camera_census.json").read_text(
        encoding="utf-8"))["rows"] if (KIT / "studies").exists() else None
    if rows is None:
        pytest.skip("census not in this checkout")
    vals = sorted(F.R_OBJ * r["proj"] * math.sin(math.radians(r["pitch"])) / abs(r["cam_y"])
                  for r in rows if r.get("pitch", 0) >= 26 and r.get("cam_y") and r.get("proj"))
    p = lambda q: vals[max(0, min(len(vals) - 1, int(q * len(vals))))]
    assert F.CHAR_PX_REFUSE == pytest.approx(p(.05), abs=0.2), "the refuse floor left FF9's p05"
    assert F.CHAR_PX_WARN == pytest.approx(p(.25), abs=0.2), "the warn floor left FF9's p25"
    assert F.CHAR_PX_MEDIAN == pytest.approx(p(.50), abs=0.2)


@pytest.mark.parametrize("w,h,want", [(2400, 1500, None), (2200, 9762, "warn"), (9762, 2200, "error"),
                                      (5000, 2000, "warn")])
def test_a_room_too_wide_for_its_camera_is_named_and_refused(w, h, want):
    """★ THE ROOM THE OWNER ACTUALLY BUILT. A 9762x2200 room fits at distance 18226 and renders the
    character at ~2.6 canvas px -- below the 5th percentile of all 741 cameras FF9 ships. It
    composed, built, deployed and walked as a sliver, and nothing in the pipeline said a word:
    `fit_play_camera` refuses only past distance 60000.

    ★ AND WIDTH IS THE EXPENSIVE AXIS -- the SAME room drawn the other way round only warns. The
    message has to say so, because rotating the drawing is free and is the largest single lever."""
    poly = [(0, 0), (w, 0), (w, h), (0, h)]
    cam, _off = F.fit_play_camera(poly, pitch=48.0, fov=42.2)
    sev, msg = F.legibility_problem("R", cam, poly)
    assert sev == want, f"{w}x{h}: got {sev} ({msg})"
    if want:
        assert "canvas px" in msg and str(int(w)) in msg
        if w > h:
            # ★ THE REMEDY IS TESTED, NOT ASSUMED. An earlier version of this message told EVERY
            # wide room to rotate -- including a 20000x2200 hall, whose rotation is a 2200x20000
            # hall and equally unrenderable. `legibility_problem` now actually fits the rotated
            # room and says what it would reach. So the fence checks that the advice is grounded,
            # not that it contains a particular phrase.
            assert "other way round" in msg or "split" in msg
            assert "px" in msg


def test_the_normal_composed_room_sits_in_the_real_games_band():
    """The gate must not fire on the shape the composer is FOR. A 2400x1500 room lands at ~10.7px,
    between FF9's median and p75 -- if this ever warns, the thresholds are wrong, not the room."""
    poly = [(0, 0), (2400, 0), (2400, 1500), (0, 1500)]
    cam, _ = F.fit_play_camera(poly, pitch=48.0, fov=42.2)
    px = F.character_scale_px(cam)
    assert F.CHAR_PX_MEDIAN <= px <= 15.0, f"a normal room renders at {px:.1f}px"
    assert F.legibility_problem("R", cam, poly) == (None, None)


# ------------------------------------------------------------------ 7b: the scrolling camera

def test_a_normal_room_does_not_scroll():
    """★ STATIC FIRST, ALWAYS. A 384x448 field is what FF9 ships for most rooms and what the rest
    of the kit assumes; widening costs a bigger painting for a human to paint and an engine path
    with less proof behind it. It is paid only when the static fit is not legible."""
    cam, off, rng, scrolling = F.fit_room_camera([(0, 0), (2400, 0), (2400, 1500), (0, 1500)])
    assert rng == (F.CANVAS_W, F.CANVAS_H) and not scrolling
    assert F.character_scale_px(cam) >= F.CHAR_PX_WARN
    c = F.compose(_plan(rooms=[{"name": "R", "poly": [(0, 0), (2400, 0), (2400, 1500), (0, 1500)]}],
                        doors=[])).by_name("R")
    assert "scroll" not in c.toml["camera"], "a normal room emitted scroll keys"
    assert "range" not in c.toml["camera"]


def test_a_wide_room_scrolls_and_is_capped_at_ff9s_own_widest():
    """The owner's stress room: 9762u wide, which a 384-wide painting renders at 2.6 char-px --
    below the 5th percentile of every camera Square shipped. Scrolling buys the apparent size back
    by letting the fit use more canvas in x, so the same polygon frames at a much shorter distance.

    The cap is FF9's own widest shipped painting (960x1088 over the 741-camera census). Beyond it
    the answer is not a wider camera, it is two rooms and a door."""
    poly = [(0, 0), (9762, 0), (9762, 2200), (0, 2200)]
    static, _o = F.fit_play_camera(poly)
    cam, off, rng, scrolling = F.fit_room_camera(poly)
    assert scrolling and rng[0] <= F.SCROLL_RANGE_CAP
    assert F.character_scale_px(cam) > F.character_scale_px(static) * 2, (
        f"scrolling bought only {F.character_scale_px(cam):.1f} vs {F.character_scale_px(static):.1f}")
    assert F.legibility_problem("R", static, poly)[0] == "error", "the static fit should be refused"
    assert F.legibility_problem("R", cam, poly)[0] != "error", "the scrolling fit should not be"


def test_the_scroll_camera_emits_what_the_build_actually_honours():
    """★ THE FOCAL LENGTH IS MEASURED AT THE SCREEN, NOT THE PAINTING. Without `window_width` a
    768-wide painting would simply double the FOV and buy nothing at all. This pins that the toml
    the composer writes resolves, through the REAL build path, to the camera it fitted."""
    from ff9mapkit import build
    from ff9mapkit.scene import guide
    poly = [(0, 0), (9762, 0), (9762, 2200), (0, 2200)]
    cam, off, rng, scrolling = F.fit_room_camera(poly)
    t = F._camera_toml(cam, F.DEFAULT_PITCH, F.DEFAULT_FOV, rng, scrolling)
    assert t["range"] == [rng[0], rng[1]]
    assert t["window_width"] == F.CANVAS_W
    assert t["scroll"] == {"enabled": True}

    class _P:                                   # the shape _resolve_one_camera reads
        def path(self, p):
            raise AssertionError("no borrow expected")

    got = build._resolve_one_camera(_P(), t, True)
    assert tuple(got.range) == tuple(rng)
    assert got.proj == guide.proj_from_fov_x(F.DEFAULT_FOV, F.CANVAS_W), (
        "the focal length followed the painting instead of the screen")
    assert tuple(got.viewport) == tuple(CAM.scroll_bounds(rng)), (
        "the pan viewport does not span the painting")


def test_the_range_moves_off_r_which_is_why_scroll_is_a_compose_time_decision():
    """⚠ THE TRAP. `off_r` is the translation every vert, door quad, arrival and spawn rides, and
    it falls out of the fitted DISTANCE, which the range changes. Bolting a wider range onto an
    already-composed room re-poses the camera under a walkmesh solved for the old one. This pins
    that the two really do move together, so nobody 'optimises' the range into a post-hoc toml
    edit."""
    poly = [(0, 0), (9762, 0), (9762, 2200), (0, 2200)]
    _c1, off_static = F.fit_play_camera(poly)
    _c2, off_wide = F.fit_play_camera(poly, range_wh=(960, F.CANVAS_H), window_width=F.CANVAS_W)
    assert off_static != off_wide, "the range did not move off_r -- the trap is not being modelled"


def test_a_room_too_wide_even_to_scroll_is_refused_and_told_to_split():
    """At the cap the gate takes over. FF9's own answer to a space this size is many fields joined
    by gateways -- 48 zones, median 11 fields each -- which this composer already builds."""
    poly = [(0, 0), (20000, 0), (20000, 2200), (0, 2200)]
    cam, _off, rng, scrolling = F.fit_room_camera(poly)
    assert rng[0] == F.SCROLL_RANGE_CAP and scrolling
    sev, msg = F.legibility_problem("HUGE", cam, poly)
    assert sev == "error" and "split" in msg.lower()


# ------------------------------------------------------------------ 7c: recompose is not a bulldozer

# What the Place tab / the Editor forms write into a room -- i.e. the content a recompose must not
# silently eat. Kept as module constants so no shell/heredoc escaping layer can mangle them.
_NPC_BLOCK = '\n[[npc]]\nname = "GUARD"\nmodel = "guard"\npos = [0, 0]\nface = 0\n'
_CHEST_BLOCK = '\n[[chest]]\nitem = "potion"\n'

def _room_toml(tmp_path, name="HALL"):
    return next(p for p in (tmp_path / name).glob("*.field.toml"))


def _read(tmp_path, name="HALL"):
    import tomllib
    return tomllib.loads(_room_toml(tmp_path, name).read_text(encoding="utf-8"))


def test_recompose_preserves_hand_authored_content_instead_of_destroying_it(tmp_path):
    """★ THE BUG THAT MADE "INTEROPERABLE" MEANINGLESS. `emit` was an unconditional write per room,
    so composing a dungeon, adding an `[[npc]]` -- exactly what the Place tab and the Editor forms
    write -- and recomposing the UNCHANGED plan left no npc, no error, no warning, exit 0.

    Any click surface built over a composed room was writing into a file the next Compose deleted.
    Rung 7c made that a hard refusal; this is the merge that replaced it (owner, 2026-07-31:
    "Recompose REFUSES on drift this rung, MERGES next")."""
    plan = _plan()
    c, _w = F.compose_and_emit(plan, tmp_path, log=None)
    spawn = _read(tmp_path)["player"]["spawn"]          # a point the composer itself certified
    room = _room_toml(tmp_path)
    room.write_text(room.read_text(encoding="utf-8")
                    + _NPC_BLOCK.replace("[0, 0]", f"[{spawn[0]}, {spawn[1] - 200}]")
                    + _CHEST_BLOCK, encoding="utf-8")

    _c, wrote = F.compose_and_emit(plan, tmp_path, log=None)
    got = _read(tmp_path)
    assert [n["name"] for n in got["npc"]] == ["GUARD"]
    assert got["npc"][0]["pos"] == [spawn[0], spawn[1] - 200], \
        "the row must survive VALUE-for-value, not just by name"
    assert got["chest"] == [{"item": "potion"}]
    assert wrote["preserved"]["HALL"]["kept"] == ["chest", "npc"]
    assert not wrote["warnings"], f"an unchanged recompose should be quiet, got {wrote['warnings']}"

    F.compose_and_emit(plan, tmp_path, log=None, force=True)          # force still discards
    assert "npc" not in _read(tmp_path) and "chest" not in _read(tmp_path)


def test_the_merge_reads_the_room_before_anything_is_written(tmp_path):
    """`new_campaign` rebuilds the manifest and `add_field` scaffolds each member OVER the room
    directory -- so by the time the room tomls are rewritten, both the old toml and the old art are
    already gone. Everything the merge needs has to be read before any of that.

    Fenced through the one refusal that survived the merge: a room that will not PARSE cannot be
    merged into, and a refusal that fires halfway through is not a refusal, it is a worse outcome
    than either finishing or stopping."""
    plan = _plan()
    F.compose_and_emit(plan, tmp_path, log=None)
    _room_toml(tmp_path).write_text("[[npc]\nname = ", encoding="utf-8")   # unparseable
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(F.ComposeError) as e:
        F.compose_and_emit(plan, tmp_path, log=None)
    assert "HALL" in str(e.value) and "--force" in str(e.value)
    after = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after, "the refusal still touched the tree"


def test_the_merge_keeps_a_hand_drawn_door_and_still_deletes_one_taken_out_of_the_plan(tmp_path):
    """★ WHY THE COMPOSER'S GATEWAYS ARE IDENTIFIED BY PREFIX AND NOT MERGED BY NAME. `[[gateway]]`
    is composer-OWNED, and the Place tab (Rung 4) draws doors into exactly that table -- so a
    wholesale rewrite eats a hand-drawn door. But a merge-by-name cannot express DELETION: take a
    door out of the plan and the old `door_to_*` row would stay live, pointing at a room the
    dungeon no longer wires."""
    from ff9mapkit.editor import model as M
    plan = _plan()
    F.compose_and_emit(plan, tmp_path, log=None)
    data = _read(tmp_path)
    assert [g["name"] for g in data["gateway"]] == ["door_to_cell"]
    data["gateway"].append({"name": "door0", "to": 4005,
                            "zone": [[-100, -100], [100, -100], [100, 100], [-100, 100]]})
    _room_toml(tmp_path).write_text(M.dumps(data), encoding="utf-8", newline="\n")

    F.compose_and_emit(plan, tmp_path, log=None)                       # door still declared
    assert [g["name"] for g in _read(tmp_path)["gateway"]] == ["door_to_cell", "door0"]

    F.compose_and_emit(_plan(doors=[]), tmp_path, log=None)            # door taken OUT of the plan
    assert [g["name"] for g in _read(tmp_path)["gateway"]] == ["door0"], \
        "the composer's own door must go when the plan drops it; the hand-drawn one must not"


def test_the_merge_keeps_an_extra_painted_layer_and_re_derives_its_own_two(tmp_path):
    """`[[layers]]` is the other owned table whose rows are independently meaningful -- adding a
    painted occluder layer beside the placeholder pair is exactly what the art README tells the
    author to do, and the composer's own two rows carry depths it must keep re-deriving."""
    from ff9mapkit.editor import model as M
    plan = _plan()
    F.compose_and_emit(plan, tmp_path, log=None)
    data = _read(tmp_path)
    data["layers"] = list(data["layers"]) + [{"image": "art/pillar.png", "z": 1500}]
    _room_toml(tmp_path).write_text(M.dumps(data), encoding="utf-8", newline="\n")

    F.compose_and_emit(plan, tmp_path, log=None)
    got = _read(tmp_path)["layers"]
    assert [row["image"] for row in got] == list(F.COMPOSER_ART) + ["art/pillar.png"]
    assert got[-1]["z"] == 1500, "the human's depth is the human's"


def test_the_composer_owns_exactly_the_gateway_names_it_claims_to():
    """★ THE PREFIX IS FENCED AGAINST THE COMPOSER'S OWN OUTPUT, exactly like
    COMPOSER_OWNED_TABLES. If the composer ever names a door something else, the merge would treat
    it as hand-drawn: it would stop regenerating it AND stop deleting it, and the room would collect
    a stale duplicate door every recompose. Invisible without this."""
    c = F.compose(_plan())
    for room in c.rooms:
        for g in room.toml.get("gateway") or []:
            assert g["name"].startswith(F.COMPOSER_GATEWAY_PREFIX), \
                f"{room.name} emits a gateway named {g['name']!r}, which the merge would read as " \
                f"hand-drawn and never touch again"


def test_the_composer_paints_exactly_the_layer_images_it_claims_to():
    """The COMPOSER_ART half of the same fence -- a `[[layers]]` row the composer emits under some
    other filename would be preserved as the human's forever, its depth frozen at whatever the
    room's shape was on the day it was first composed."""
    c = F.compose(_plan())
    for room in c.rooms:
        for row in room.toml.get("layers") or []:
            assert row["image"] in F.COMPOSER_ART, \
                f"{room.name} paints {row['image']!r}, which the merge would read as the human's"


def test_a_reshape_that_strands_preserved_content_says_so_and_a_reshape_that_does_not_is_quiet(tmp_path):
    """★ THE GATE THE MERGE IS CONDITIONED ON (owner, 2026-07-31). Preserved content keeps its
    ROOM-frame coordinate verbatim -- see `emit` for why that and not the plan frame -- so a reshape
    can leave an NPC outside the new outline. In-game that is SILENT: an off-mesh NPC still renders,
    standing in the air, and the player simply cannot reach it.

    The second half is the one that makes the gate worth having: a fence that only ever fires is
    indistinguishable from `warn always`."""
    from ff9mapkit.editor import model as M
    deep = [(0, 0), (3000, 0), (3000, 2400), (0, 2400)]
    shallow = [(0, 0), (3000, 0), (3000, 1200), (0, 1200)]        # the back half removed
    plan = {"name": "T", "id_base": 30500, "doors": [],
            "rooms": [{"name": "R", "poly": deep}]}
    c, _w = F.compose_and_emit(plan, tmp_path, log=None)
    z0 = min(z for _x, z in c.by_name("R").poly_room)             # the room frame, measured not guessed

    data = _read(tmp_path, "R")
    data["npc"] = [{"name": "DOOMED", "preset": "vivi", "pos": [0, int(z0 + 2100)]},
                   {"name": "SAFE", "preset": "vivi", "pos": [0, int(z0 + 800)]}]
    _room_toml(tmp_path, "R").write_text(M.dumps(data), encoding="utf-8", newline="\n")

    plan["rooms"][0]["poly"] = shallow
    _c2, wrote = F.compose_and_emit(plan, tmp_path, log=None)
    said = " | ".join(wrote["warnings"])
    assert "DOOMED" in said and "OUTSIDE the room outline" in said
    assert "SAFE" not in said, f"the gate fired on content that is still standable: {said}"
    assert [n["name"] for n in _read(tmp_path, "R")["npc"]] == ["DOOMED", "SAFE"], \
        "the warning must not be a deletion -- the author decides what to do about it"


def test_the_gate_also_catches_the_wall_clamp_and_a_door_moved_on_top_of_content():
    """The other two ways a reshape strands content, both silent in-game. `unstandable_preserved`
    is exercised directly here: driving them through a whole compose would mean hand-solving a plan
    that puts a regenerated door exactly over an old NPC, which tests the fixture, not the rule."""
    poly = [(0.0, 0.0), (2000.0, 0.0), (2000.0, 2000.0), (0.0, 2000.0)]
    door = [(900.0, 0.0), (1100.0, 0.0), (1100.0, 250.0), (900.0, 250.0)]
    tables = {"npc": [{"name": "HUGGER", "pos": [30, 1000]},        # 30u off the wall, clamp is 80
                      {"name": "BLOCKER", "pos": [1000, 120]},      # inside the new door strip
                      {"name": "FINE", "pos": [1000, 1000]}]}
    found = {label: why for _t, label, _xz, why in
             F.unstandable_preserved(poly, tables, [(door, "the door_to_x door strip")])}
    assert "FINE" not in found
    assert "30u from the nearest wall" in found["HUGGER"]
    assert "door_to_x" in found["BLOCKER"] and "blocks it" in found["BLOCKER"]


def test_a_trigger_quad_is_never_judged_by_the_standable_gate():
    """Rung 4 established that a region's corners legitimately hang OFF the mesh -- donor door quads
    do it. Reading `zone` here would fire on every correctly drawn door, which is how a gate gets
    trained out of an author's attention."""
    poly = [(0.0, 0.0), (2000.0, 0.0), (2000.0, 2000.0), (0.0, 2000.0)]
    far = {"event": [{"name": "sign", "zone": [[-500, -500], [-400, -500], [-400, -400],
                                               [-500, -400]]}]}
    assert F.unstandable_preserved(poly, far) == []
    assert F.preserved_positions(far) == [], "a zone is not a pos"


def test_painted_art_survives_a_recompose_and_the_one_after_it(tmp_path):
    """★ THE FINGERPRINT IS OF WHAT THE COMPOSER PAINTED, NOT OF WHAT ENDS UP ON DISK. Recording the
    final state would hash the author's PAINTING, so the NEXT compose would see a match, call the
    file its own and repaint over it -- the same silent loss, one compose later, which is exactly
    the shape of bug a single-recompose fence cannot see."""
    plan = _plan()
    F.compose_and_emit(plan, tmp_path, log=None)
    back = tmp_path / "HALL" / "art" / "back.png"
    placeholder = back.read_bytes()
    painting = placeholder[:-1] + bytes([placeholder[-1] ^ 0xFF])
    back.write_bytes(painting)

    for run in (1, 2):
        side = F.load_plan(tmp_path / F.SIDECAR)
        _c, wrote = F.compose_and_emit(side, tmp_path, log=None)
        assert back.read_bytes() == painting, f"recompose {run} repainted over the author's art"
        assert wrote["preserved"]["HALL"]["art"] == ["art/back.png"]
        # the room it did NOT paint is still the composer's, and is still regenerated
        assert (tmp_path / "HALL" / "art" / "floor.png").read_bytes() != painting

    F.compose_and_emit(F.load_plan(tmp_path / F.SIDECAR), tmp_path, log=None, force=True)
    assert back.read_bytes() == placeholder, "--force must repaint"


def test_a_reshape_under_painted_art_says_the_painting_no_longer_matches(tmp_path):
    """Keeping the painting is right, and it is not enough: the floor moved under it. The signal is
    EXACT rather than a proxy -- the placeholder pair is a pure function of (camera, floor_tris), so
    a fingerprint that moved between two composes means the art FRAME changed.

    It is deliberately judged PER ROOM. `back.png` is a solid fill at canvas size and so is
    byte-identical across any reshape that does not change the range -- and a painted backdrop whose
    horizon was drawn against the old floor is exactly the thing that just stopped lining up. This
    test paints THAT file on purpose; a per-file check passes it and is wrong."""
    plan = {"name": "T", "id_base": 30500, "doors": [],
            "rooms": [{"name": "R", "poly": [(0, 0), (3000, 0), (3000, 2400), (0, 2400)]}]}
    F.compose_and_emit(plan, tmp_path, log=None)
    back = tmp_path / "R" / "art" / "back.png"
    back.write_bytes(back.read_bytes()[:-1] + b"\x00")

    side = F.load_plan(tmp_path / F.SIDECAR)
    _c, quiet = F.compose_and_emit(side, tmp_path, log=None)          # same shape: nothing to say
    assert not any("no longer lines up" in w for w in quiet["warnings"]), quiet["warnings"]

    side = F.load_plan(tmp_path / F.SIDECAR)
    side["rooms"][0]["poly"] = [[0, 0], [3000, 0], [3000, 1200], [0, 1200]]
    _c, loud = F.compose_and_emit(side, tmp_path, log=None)
    assert any("no longer lines up" in w and "art/back.png" in w for w in loud["warnings"]), \
        loud["warnings"]
    assert back.read_bytes()[-1:] == b"\x00", "it warns, it does not repaint"


def test_the_art_fingerprint_rides_the_plan_so_the_tab_round_trip_carries_it(tmp_path):
    """The record lives in the sidecar's own room entries, which is what makes it work in both
    lanes: the CLI's plan file is usually the sidecar itself (so a separate disk read would see the
    author's edit, not the record), and the Floorplan tab holds the plan in memory. Rung 7a made
    `plan()` / `load_plan` carry unknown room keys through unchanged -- this is the first thing
    that spends that carry, so it is fenced here rather than assumed."""
    F.compose_and_emit(_plan(), tmp_path, log=None)
    side = F.load_plan(tmp_path / F.SIDECAR)
    art = side["rooms"][0]["art"]
    assert sorted(art) == sorted(F.COMPOSER_ART)
    assert all(len(v) == 64 for v in art.values()), "sha256 hex, not a size or an mtime"
    assert art == F.art_fingerprints(tmp_path / side["rooms"][0]["name"])


def test_the_composer_owns_exactly_the_tables_it_emits():
    """★ THE LIST IS FENCED AGAINST THE COMPOSER'S OWN OUTPUT. `COMPOSER_OWNED_TABLES` decides what
    counts as "the human's"; if the composer learns to emit a new table and the list is not updated,
    every recompose would start refusing on its OWN output -- and if a table is wrongly listed as
    owned, hand-authored content in it gets silently destroyed. Either way the failure is invisible
    without this."""
    c = F.compose(_plan(rooms=[{"name": "R", "poly": ROOM_A, "savepoint": True,
                                "encounter": {"scene": 1}}], doors=[]))
    emitted = set(c.by_name("R").toml)
    assert emitted <= F.COMPOSER_OWNED_TABLES, (
        f"the composer emits {sorted(emitted - F.COMPOSER_OWNED_TABLES)}, which it does not claim "
        f"to own -- a recompose would refuse on its own output")


def test_a_freshly_composed_room_shows_no_drift(tmp_path):
    """The complement, and the one that would catch an over-broad owned-list turning every second
    compose into a refusal."""
    F.compose_and_emit(_plan(), tmp_path, log=None)
    c = F.compose(_plan())
    assert F.emit_drift(c, tmp_path) == {}


def test_the_ids_are_pinned_so_a_recompose_cannot_renumber_deployed_rooms(tmp_path):
    """★ `cli`'s pre-flight seeds `taken` from the LIVE DictionaryPatch registrations -- which
    include this dungeon's own already-deployed rooms -- so a plain recompose could shuffle the run
    onto the next free block, invalidating every `deploy_field.py --id N` the author wrote down,
    every external gateway aimed at these rooms, and the New Game wiring."""
    import json
    F.compose_and_emit(_plan(), tmp_path, log=None)
    side = json.loads((tmp_path / F.SIDECAR).read_text(encoding="utf-8"))
    pinned = [r.get("id") for r in side["rooms"]]
    assert all(isinstance(i, int) for i in pinned), f"ids not pinned: {pinned}"

    # ★ AND A DUNGEON DOES NOT COLLIDE WITH ITSELF. The live pre-flight reports our own deployed
    # rooms as taken; `own_pinned_ids` is what lets the caller subtract them. Without that step the
    # pin turns the old silent renumbering into a hard refusal -- which this fence caught.
    own = F.own_pinned_ids(tmp_path)
    assert own == set(pinned)
    live = set(pinned) | {31234}                     # our rooms, plus somebody else's field
    again = F.compose(side, taken_ids=tuple(live - own))
    assert [r.field_id for r in again.rooms] == pinned, "a recompose renumbered its own rooms"

    with pytest.raises(F.ComposeError):              # a REAL collision must still be refused
        F.compose(side, taken_ids=tuple(live))
    assert F.own_pinned_ids(tmp_path / "nope") == set(), "no sidecar must claim nothing"
