"""``content.doorface`` -- stock FF9's door facing gate and region membership, engine-exact, pinned by hand-computed
cases (no install needed: the atan table is the math approximation, and every case here holds with it).

THE WORKED CHECK is stock 350's door to 351 (entry 18: q0 = (569, 195), q1 = (662, -63)) at the tour's goal in its
zone, (289, -74): the exit point (622, 46), the bearing -79 (177 as a byte), and the five pads of 350's 1.40625-degree
twist -- up -48 (not faced: 208 fails), up+right -16, right +16, down+right +48 (not faced: 48 fails), left -112. And
the arrival from 351 at yaw 69 (error -128), which three walked MovePC calls pressing right turn to +40 (faced).
"""

from __future__ import annotations

import math

import pytest

from ff9mapkit.content import doorface as D
from ff9mapkit.content import gateway as _gw

Q0, Q1 = (569, 195), (662, -63)           # stock 350 entry 18 (-> 351): the region's first edge
AT = (289, -74)                            # the tour's goal in that zone
TWIST = 1.40625                            # 350's SetControlDirection(0, 0): (0 + 1) / 256 * 360 degrees
PAD_YAW = {"up": 180 + TWIST - 360, "up+right": -135 + TWIST, "right": -90 + TWIST,
           "down+right": -45 + TWIST, "left": 90 + TWIST}


def test_the_worked_check_at_350s_door_to_351():
    assert D.calc_exit_position(*AT, Q0, Q1) == (622, 46)
    assert D.eb_bearing(622 - 289, 46 - -74) == -79 and D.eb_bearing(333, 120) & 255 == 177
    got = {pad: D.door_faced(*AT, yaw, Q0, Q1) for pad, yaw in PAD_YAW.items()}
    assert got == {"up": (False, -48), "up+right": (True, -16), "right": (True, 16),
                   "down+right": (False, 48), "left": (False, -112)}
    assert D.gate_value(*AT, PAD_YAW["up"], Q0, Q1) == 208 and D.gate_value(*AT, PAD_YAW["down+right"], Q0, Q1) == 48


def test_a_measured_facing_byte_is_judged_by_the_same_gate():
    """``gate_value_from_face`` takes the facing BYTE itself -- s90's published ``player.face`` / ``turn_end``'s
    ``face``, the gate's own operand -- against the same bearing: equal to ``gate_value`` of any yaw with that byte,
    so a measured byte and a predicted yaw are judged alike (and a byte a script left at, say, 250 -- a yaw of 351.6,
    outside MovePC's range -- is judged as that byte)."""
    for pad, yaw in PAD_YAW.items():
        assert D.gate_value_from_face(*AT, D.facing_byte(yaw), Q0, Q1) == D.gate_value(*AT, yaw, Q0, Q1), pad
    assert D.gate_value_from_face(*AT, 177, Q0, Q1) == 0                    # facing the bearing's own byte
    assert D.gate_value_from_face(0, 0, 250, _W0, _W1) == D.gate_value(0, 0, 351.6, _W0, _W1) == 245


def test_the_gates_compare_is_strict_at_both_edges_and_the_one_rule_door_faced_uses():
    """``gate_faced`` is THE compare (B_LT / B_GT, both strict): with the stock (48, 208) the values 48 and 208 are
    shut and 47 / 209 open -- signed errors -47..+47 faced, +-48 not -- and a site's own constants (the (56, 200) of
    fields 1460 and 3059) the same way. ``door_faced`` answers with it for every yaw."""
    assert [v for v in range(256) if D.gate_faced(v)] == list(range(0, 48)) + list(range(209, 256))
    assert [D.gate_faced(v) for v in (47, 48, 208, 209)] == [True, False, False, True]
    assert [D.gate_faced(v, (56, 200)) for v in (55, 56, 200, 201)] == [True, False, False, True]
    assert all(D.gate_faced(D.signed_error(v) & 255) == (abs(D.signed_error(v)) <= 47) for v in range(256))
    for yaw in range(-180, 181, 3):
        faced, err = D.door_faced(*AT, float(yaw), Q0, Q1)
        assert faced == D.gate_faced(D.gate_value(*AT, float(yaw), Q0, Q1)) == (abs(err) <= 47), yaw


def test_the_arrival_from_351_turns_to_face_the_door_on_the_third_walked_call():
    """He walked out of 351 away from this door (yaw 69): error -128. Pressing right, one MovePC call a walked tick,
    the lerp reaches 6.0, -31.9, -54.6 degrees -- errors +83, +56, +40: faced only at the third call."""
    assert D.door_faced(*AT, 69.0, Q0, Q1) == (False, -128)
    yaw, seen = 69.0, []
    for _ in range(3):
        yaw = D.turn_step(yaw, PAD_YAW["right"])
        seen.append((round(yaw, 1), D.door_faced(*AT, yaw, Q0, Q1)))
    assert seen == [(6.0, (False, 83)), (-31.9, (False, 56)), (-54.6, (True, 40))]


# --- the compare: an Int32 AND that wraps, and strict bounds ----------------------------------------------------------
#: An exit point clamped to q0 = (-130, -991) from the origin: bearing atan2(130, 991) = 7.47 degrees, 85/4096 -> 5.
_W0, _W1 = (-130, -991), (-1130, -991)


def test_the_gate_wraps_through_zero():
    assert D.calc_exit_position(0, 0, _W0, _W1) == _W0                      # t < 0: clamped to q0
    assert D.eb_bearing(-130, -991) == 5
    assert D.facing_byte(D.yaw_of_byte(250)) == 250
    assert D.gate_value(0, 0, D.yaw_of_byte(250), _W0, _W1) == 245           # (250 - 5) & 255
    assert D.door_faced(0, 0, D.yaw_of_byte(250), _W0, _W1) == (True, -11)


@pytest.mark.parametrize("err,faced", [(47, True), (48, False), (-47, True), (-48, False), (0, True), (-128, False)])
def test_the_stock_bounds_are_strict(err, faced):
    """B_LT / B_GT are strict (EBin.cs:722 / :735 at stock 6b8bb2d5): ``v < 48 || v > 208`` -- 47 and -47 fire, 48 and
    -48 (208) do not."""
    assert D.door_faced(0, 0, D.yaw_of_byte(5 + err), _W0, _W1) == (faced, err)


def test_an_explicit_window_is_the_compare_constants():
    """1460's and 3059's (56, 200): an error of 50 passes there, not under the stock (48, 208)."""
    yaw = D.yaw_of_byte(5 + 50)
    assert D.door_faced(0, 0, yaw, _W0, _W1) == (False, 50)
    assert D.door_faced(0, 0, yaw, _W0, _W1, window=(56, 200)) == (True, 50)


# --- CalculateExitPosition: onto the SEGMENT, in Int32 arithmetic ------------------------------------------------------
def test_the_exit_point_is_clamped_to_the_segment():
    q0, q1 = (0, 0), (1024, 0)
    assert D.calc_exit_position(400, 300, q0, q1) == (400, 0)                 # the foot of the perpendicular
    assert D.calc_exit_position(-250, 300, q0, q1) == (0, 0)                  # before q0: q0
    assert D.calc_exit_position(1700, -20, q0, q1) == (1024, 0)               # past q1: q1


def test_the_exit_point_moves_in_256ths_of_the_edge():
    """The parameter is an integer in 256ths: on a 1000u edge the foot at 400 is t = 400000 // 3906 = 102, the point
    102 * 1000 >> 8 = 398."""
    assert D.calc_exit_position(400, 300, (0, 0), (1000, 0)) == (398, 0)


def test_an_edge_under_16u_exits_at_q0():
    """``(ex*ex + ez*ez) >> 8`` is 0 for an edge shorter than 16u: no division, the parameter stays 0."""
    assert D.calc_exit_position(500, 500, (10, 20), (25, 20)) == (10, 20)
    assert D.calc_exit_position(500, 500, (10, 20), (26, 20)) != (10, 20)


def test_the_exit_point_shifts_arithmetically_and_divides_toward_zero():
    """``(t * ex) >> 8`` floors a negative product (-13000 / 256 = -50.78 -> -51; truncation would say -50), and the
    quotient truncates toward zero (C#), as ``_cdiv`` does for either sign."""
    assert D.calc_exit_position(-51, 0, (0, 0), (-100, 0)) == (-51, 0)
    assert (D._cdiv(7, 2), D._cdiv(-7, 2), D._cdiv(7, -2), D._cdiv(-7, -2)) == (3, -3, -3, 3)


def test_the_bearing_is_taken_from_his_rounded_position():
    """f[0] / f[2] are RoundToInt: 0.5 rounds to even (0), 1.5 to 2 -- one step from the exit point that moves the
    bearing from straight -z to 45-odd degrees off it."""
    q0, q1 = (0, -100), (5, -100)                    # a 5u edge: the exit point is q0
    assert D.gate_value(0.5, -99, 0.0, q0, q1) == 0                          # (0, -99) -> (0, -1): bearing 0
    assert D.gate_value(1.5, -99, 0.0, q0, q1) == (0 - D.eb_bearing(-2, -1)) & 255
    assert D.eb_bearing(-2, -1) > 40


# --- the conventions --------------------------------------------------------------------------------------------------
def test_the_bearing_and_the_facing_share_one_convention():
    """0 = -z, 64 = -x, +-128 = +z, -64 (192) = +x -- clockwise seen from above with +x right and +z up. Straight +z
    is -128 from one side of the octant arithmetic and +128 from the other: the same byte."""
    assert [D.eb_bearing(dx, dz) for dx, dz in ((0, -10), (-10, 0), (0, 10), (10, 0), (0, 0))] == [0, 64, -128, -64, 0]
    assert D.eb_bearing(-1, 2000) == 128 and D.eb_bearing(-1, 2000) & 255 == D.eb_bearing(0, 10) & 255
    assert [D.facing_byte(y) for y in (0.0, 90.0, 180.0, -180.0, -90.0)] == [0, 64, 128, 128, 192]
    assert [round(D.yaw_of(dx, dz)) for dx, dz in ((0, -1), (-1, 0), (1, 0))] == [0, 90, -90]
    assert abs(D.yaw_of(0, 1)) == 180
    for dx, dz in ((3, -7), (-5, 2), (8, 8)):                                 # a press's yaw faces its own bearing
        assert abs(D.signed_error(D.facing_byte(D.yaw_of(dx, dz)) - D.eb_bearing(dx * 100, dz * 100))) <= 1


def test_the_facing_byte_rounds_half_to_even():
    """RoundToInt is Math.Round: -0.5/4096 of a turn rounds to 0 (byte 0), not away from zero to -1 (byte 255);
    31.5/4096 rounds to 32 (byte 2)."""
    assert D.facing_byte(-0.5 * 360 / 4096) == 0
    assert D.facing_byte(31.5 * 360 / 4096) == 2


def test_the_atan_table_is_the_math_approximation_not_game_data():
    assert len(D.ATAN_TABLE) == 1025 and D.ATAN_TABLE[0] == 0 and D.ATAN_TABLE[1024] == 512
    assert D.angle_asm(-1, -1) == 512 and D.angle_asm(1, 1) == -1536


# --- the turn: 40% a MovePC call ---------------------------------------------------------------------------------------
def test_the_turn_is_40_percent_a_call_and_k_calls_are_one_lerp():
    assert D.turn_step(0.0, 180.0) == pytest.approx(72.0)                   # from 180 away: 108 left
    assert D.turn_step(0.0, 180.0, 2) == pytest.approx(115.2)               # 64.8 left
    assert D.turn_step(0.0, 180.0, 3) == pytest.approx(D.turn_step(D.turn_step(D.turn_step(0.0, 180.0), 180.0), 180.0))
    assert D.turn_step(10.0, 90.0, 0.5) == pytest.approx(10.0 + 80.0 * (1 - math.sqrt(0.6)))   # a walked frame


def test_the_turn_takes_the_short_way_round_and_wraps():
    """170 pressing -170: the target unwraps to 190 -- 178 after one call, 182.8 -> -177.2 after two."""
    assert D.turn_step(170.0, -170.0) == pytest.approx(178.0)
    assert D.turn_step(170.0, -170.0, 2) == pytest.approx(-177.2)
    assert D.turn_step(D.turn_step(170.0, -170.0), -170.0) == pytest.approx(-177.2)


def test_no_press_and_no_calls_keep_the_yaw():
    assert D.turn_step(33.0, None) == 33.0 and D.turn_step(33.0, -90.0, 0) == 33.0


def test_calls_come_from_the_calibrated_speed():
    assert (D.movepc_calls(30.0), D.movepc_calls(15.0)) == (1.0, 0.5)


def test_a_press_is_sure_only_of_its_whole_calls():
    """The engine turns in WHOLE calls, a walked one a tick, in a phase nobody sees: at half a call a frame, 8 frames are
    4 calls, 9 are 4 or 5 -- sure of 4 -- and 3 are sure of 1; one frame is sure of none. A run frame is a whole call."""
    assert [D.sure_calls(n, 0.5) for n in (1, 2, 3, 8, 9, 10)] == [0, 1, 1, 4, 4, 5]
    assert [D.sure_calls(n, 1.0) for n in (1, 4)] == [1, 4]


def test_the_window_sets_the_error_a_planner_may_count_on():
    """Strict bounds: the stock (48, 208) passes 47 units either way, 66.09 degrees; 1460's (56, 200) 55."""
    assert D.face_limit_deg() == D.FACE_LIMIT_DEG == pytest.approx(47 * 360 / 256)
    assert D.face_limit_deg((56, 200)) == pytest.approx(55 * 360 / 256)
    assert D.face_limit_deg((48, 200)) == pytest.approx(47 * 360 / 256)      # the nearer bound


def test_a_yaw_of_every_byte_has_that_byte():
    assert all(D.facing_byte(D.yaw_of_byte(b)) == b for b in range(256))
    assert D.yaw_of_byte(0) == 0.0 and D.yaw_of_byte(64) == 90.0 and D.yaw_of_byte(192) == -90.0


# --- planning a press (the harness's facing step): the bearing before its floor, the worst error a press leaves ------
def test_the_planners_bearing_is_the_gates_before_its_floor():
    """bearing_deg is the bearing the gate floors to a unit: at the worked spot the byte is -79 and the continuous
    bearing lies in that unit; standing on the edge itself (a zero delta) it is 0, angleAsm's own answer -- never the
    -180 atan2 gives for (-0.0, -0.0)."""
    b = D.bearing_deg(*AT, Q0, Q1)
    assert -79 * D.UNIT_DEG <= b < -78 * D.UNIT_DEG
    assert D.bearing_deg(600, 0, (600, -100), (600, 100)) == 0.0
    assert D.angle_off(170, -170) == pytest.approx(20.0) and D.angle_off(-90, 90) == pytest.approx(180.0)


def test_the_worst_error_a_press_leaves_is_the_turns_rest_the_pads_offset_the_spread_and_a_unit():
    """From any yaw, the nearest pad (22.5 degrees off at most) on a basis good to 2 degrees: after 4 MovePC calls at
    most 49.2 degrees -- inside the 47-unit window (66.09) -- after 3, 64.8 (1.3 to spare), after 2, 90.7: not sure at
    all. From a yaw known to within 30 degrees of the pad, one call leaves 18 of it."""
    assert D.FACE_LIMIT_DEG == pytest.approx(66.09375)
    assert D.worst_face_error(22.5, 4, 2.0) == pytest.approx(180 * 0.6 ** 4 + 22.5 + 2.0 + 1.40625)
    assert D.worst_face_error(22.5, 4, 2.0) < D.worst_face_error(22.5, 3, 2.0) < D.FACE_LIMIT_DEG
    assert D.worst_face_error(22.5, 2, 2.0) > D.FACE_LIMIT_DEG
    assert D.worst_face_error(22.5, 1, 2.0, off_before=30.0) == pytest.approx(18.0 + 22.5 + 2.0 + 1.40625)


# --- IsInQuad: the triangles of consecutive triplets --------------------------------------------------------------------
def test_a_triangle_is_covered_whole_border_included():
    tri = [(0, 0), (100, 0), (0, 100)]
    assert D.region_contains(10, 10, tri) and D.region_contains(50, 50, tri) and D.region_contains(100, 0, tri)
    assert not D.region_contains(60, 60, tri) and not D.region_contains(-1, 10, tri)


def test_a_quad_is_covered_whole():
    quad = [(0, 0), (200, 0), (200, 100), (0, 100)]
    assert all(D.region_contains(x, z, quad) for x in range(0, 201, 20) for z in range(0, 101, 20))
    assert not D.region_contains(201, 50, quad) and not D.region_contains(100, -1, quad)


def test_the_kits_doubled_trailing_vertex_is_still_exactly_the_quad():
    """quad_zone's ``[a, b, c, d, d]``: triangles abc, bcd and dab cover the quad, the two through the double are
    empty (a repeated vertex divides by zero in the engine and contains nothing)."""
    corners = [(-200, 200), (200, 200), (260, 420), (-180, 400)]
    five = _gw.quad_zone(corners)
    assert len(five) == 5 and five[-1] == five[-2]
    for x in range(-260, 300, 10):
        for z in range(160, 460, 10):
            assert D.region_contains(x, z, five) == D.region_contains(x, z, corners), (x, z)
    assert D.region_contains(0, 300, five) and not D.region_contains(0, 150, five)


def test_a_pentagons_middle_is_a_dead_zone():
    """Five points: the five ears (q[i], q[i+1], q[i+2]) -- the inner pentagon bounded by the diagonals is in none."""
    penta = [(round(1000 * math.sin(2 * math.pi * k / 5)), round(1000 * math.cos(2 * math.pi * k / 5)))
             for k in range(5)]
    assert not D.region_contains(0, 0, penta)                                 # the middle: dead
    assert D.region_contains(0, 900, penta)                                   # by a vertex: an ear
    mid_edge = ((penta[0][0] + penta[1][0]) / 2 * 0.98, (penta[0][1] + penta[1][1]) / 2 * 0.98)
    assert D.region_contains(*mid_edge, penta)                                # along an edge: an ear
    assert not D.region_contains(0, 1100, penta)                              # outside


def test_degenerate_regions_contain_nothing():
    assert not D.region_contains(0, 0, [(0, 0), (0, 0), (0, 0)])
    assert not D.region_contains(50, 0, [(0, 0), (50, 0), (100, 0)])         # collinear
    assert not D.region_contains(0, 0, [(0, 0), (10, 10)])
    assert not D.region_contains(0, 0, [])
