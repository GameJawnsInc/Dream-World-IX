"""Fences for the floorplan composer (click-authoring Rung 6) -- the pure topology layer.

Every test here pins a law an adversarial pass BROKE in the first draft of the spec
(``studies/click-authoring/RUNG6.md`` §1). Several assert the SHAPE OF A BUG rather than just the
fix, so that a future "simplification" back toward the obvious-looking version goes red instead of
silently reintroducing an inversion nobody can see.

A law in a docstring is a wish in this codebase. These are the laws.
"""
from __future__ import annotations

import math

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


def _plan(**kw):
    base = {"name": "T", "id_base": 30500,
            "rooms": [{"name": "HALL", "poly": ROOM_A}, {"name": "CELL", "poly": ROOM_B}],
            "doors": [{"a": "HALL", "b": "CELL", "seg": [list(DOOR[0]), list(DOOR[1])]}]}
    base.update(kw)
    return base


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
