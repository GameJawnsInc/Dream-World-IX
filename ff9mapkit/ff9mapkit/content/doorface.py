"""Stock FF9's DOOR FACING GATE and region membership, engine-exact, as pure math (no game data).

A stock walk-in door does not always fire because the player stands in its region. On 102 stock gateways in 81
fields (6 of Dali's 9 on the Village Road, 350) the region's tag 2 first CALCULATES THE EXIT POSITION -- the
player projected onto the region's first edge -- and fires only when he FACES that point: his model yaw, in
256ths of a turn, within 47 of the bearing from him to it. Standing in the zone facing anywhere else re-tests
every tick and never fires. The bytes, identical at every site (field 350, entry 18, tag 2):

    A4                                   CalculateExitPosition          -> SYSVAR 10 / 11 (the exit point)
    05 d9 06 78 fa 03 7a 0a 78 fa 00 15 7a 0b 78 fa 02 15 66 15 7d ff 00 24 2c 7f
         Map.Int16[6] = (obj(250).f[3] - ANGLE2(SYSVAR[10] - obj(250).f[0], SYSVAR[11] - obj(250).f[2])) & 255
    05 d9 06 7d 30 00 18 d9 06 7d d0 00 19 28 7f        Map.Int16[6] < 48 || Map.Int16[6] > 208
    02 ..                                JMP_IFNOT -> clear Map.Bit[162,163,165,164]; RET

This module computes what those bytes compute. Engine citations are Memoria 6b8bb2d5's STOCK line numbers
(``git show 6b8bb2d5:<file>``, under Assembly-CSharp/Global/ unless said) with the function named beside each -- the
local clone carries the memoria-patches stack, whose working-tree lines differ:

  * :func:`calc_exit_position` -- CalculateExitPosition (Event/Engine/EventEngine.DoEventCode.cs:2213-2240, ``case
    MJPOS``): his float position projected onto the SEGMENT q0 -> q1 (the region's first two SetRegion points, in
    argument order: ``case QUAD``, :937-954), the parameter an integer in 256ths clamped to [0, 256], every product
    and quotient C# Int32 arithmetic (division truncates toward zero). An edge shorter than 16u makes the divisor 0
    and the exit point q0. Field 552's one hard-coded override (:2232-2236) is not modelled.
  * :func:`eb_bearing` -- B_ANGLE2 (EBin.cs:1182-1192) over angleAsm (EBin.cs:1558-1584): the direction of (dx, dz)
    in 4096ths of a turn, ``atan2(-dx, -dz)`` -- 0 = -z, 1024 = -x, +-2048 = +z, -1024 = +x -- floored to 256ths by
    the degree round trip (ConvertFixedPointAngleToDegree, EBin.cs:1586-1589, keeps ``>> 4``). In 256ths: 0 = -z,
    64 = -x, +-128 = +z, -64 (192) = +x. A zero delta is 0.
  * :func:`facing_byte` -- obj.f[3] in a field (EBin.cs:1786-1799, getvobj ``case 3``): ``Actor.rotAngle[1]``,
    degrees, through ConvertFloatAngleToFixedPoint (EBin.cs:1248-1258: the float32 of deg/360*4096, RoundToInt,
    i.e. round half to even) ``>> 4 & 255``. The yaw shares the bearing's zero and handedness: the controller turns
    it toward ``atan2(-moveVec.x, -moveVec.z)`` (Field/Map/Actor/FieldMapActorController.cs:748, in MovePC).
  * :func:`door_faced` -- the compare: ``v = (facing - bearing) & 255`` (an Int32 AND, so it wraps), and the
    door fires when ``v < lo || v > hi`` -- B_LT is ``_v0 < t3`` (EBin.cs:710-724, the compare at :722), B_GT
    ``t3 < _v0`` (:726-745, at :735): both STRICT, so with the stock (48, 208) the signed error must lie in
    [-47, +47] (+-66.1 degrees); 48 and 208 themselves fail. The bearing is taken from his ROUNDED position (f[0] /
    f[2], getvobj ``case 0`` / ``case 2`` at EBin.cs:1753 / :1779, go through CastFloatToIntWithChecking,
    :1821-1831 -- RoundToInt), the exit point from his float one.

HOW HIS YAW MOVES (:func:`turn_step`). Each MovePC call with a direction held under control turns him 40% of the
way toward the pressed direction (FieldMapActorController.cs:744-761, in MovePC: unwrap the target to within 180
degrees, ``Mathf.Lerp(rot, target, 0.4f)`` at :756, wrap into [-180, 180]) -- BEFORE the walkmesh and body
collision (:762), so a press into a wall that moves him nowhere still turns him, and a push-out revert restores
position only. Standing, or without control (the held directions are ANDed with it, :638-641; a hold on movement
returns from MovePC before any of it, :586), the yaw does not change. Walking is one MovePC call per 30 Hz field
tick; running is two, each a 30u step (FieldMapActorController.cs:197-208). A tick is WHOLE: the render loop runs
``FPSManager.MainLoopUpdateCount`` of them a frame (Global/Hono/Behavior/HonoBehaviorSystem.cs:106), paced on the
wall clock (Memoria/Application/FPSManager.cs:77-110) -- 0 or 1 a frame at 60 fps, in a phase the harness does not
see. So an n-frame hold spends a whole number of calls, ``n * per`` rounded either way, where ``per`` is the calls a
frame spends on AVERAGE: :func:`movepc_calls` of the harness's calibrated speed. A planner counts on
:func:`sure_calls` -- the whole calls ``n`` frames are sure of -- never on the average. ``player.dir`` in the
harness's state.json is NOT this yaw: it is ``PosObj.rot[1]``, which nothing writes on a field (it reads 0 there);
memoria-patch s90 publishes the yaw itself (``player.face``), but nothing here reads it yet, so the yaw is PREDICTED
from the presses that made it.

WHICH REGION ANSWERS (:func:`region_contains`). IsInQuad (Event/Engine/EventEngine.TreadQuad.cs:24-39) tests the
n triangles ``(q[i], q[i+1 mod n], q[i+2 mod n])`` for i in 0..n-1 -- every run of three consecutive vertices,
wrapping round -- NOT a fan from q0: Math3D.PointInsideTriangleTestXZ (Math3D.cs:46-59 -> :28-43), XZ only,
barycentric, border-inclusive (``u >= 0, v >= 0, u + v <= 1.000001``). So a convex 3- or 4-gon is covered whole,
but a convex 5- to 8-gon only as the ring of its "ears": the inner polygon bounded by the diagonals (i, i+2) is a
DEAD ZONE that fires nothing. A triangle with a repeated vertex divides by zero and contains nothing -- which is
why the kit's own doubled trailing vertex ``[a, b, c, d, d]`` (content.gateway.quad_zone; stock never doubles
one) is still exactly the quad: abc, bcd and dab cover it, the two triangles through the double are empty.
TreadQuad (TreadQuad.cs:6-22) answers with the FIRST armed region containing him, in activeObj order -- a region
whose gate fails, or whose tag 2 returns at once, still answers, and shadows every region after it that tick.

The atan table angleAsm reads is ``ratan_tbl.bin`` in the game's resources -- Square Enix data, never shipped
here. :data:`ATAN_TABLE` is its math approximation ``round(atan(i / 1024) * 2048 / pi)``: equal in 836 of 1025
entries, the rest off by exactly 1/4096 of a turn, which moves a 256ths bearing in about 1.3% of directions --
immaterial against a +-47 window, and the price of shipping no game bytes.

NOT MODELLED: the class-3 doors (a FIXED facing window -- 21 stock Lindblum cab / castle-lift gateways, mostly
Confirm doors), bearings to a constant point or an object (about 40 other region sites read the facing that
way), the float32 rounding of the membership test (computed here in double: a point within a hair of a border
may differ), and IsInQuadHotFix's 14 regions the engine swaps for circles (TreadQuad.cs:41-54).
"""

from __future__ import annotations

import math
import struct

#: The stock gate's compare constants: the door fires when ``(facing - bearing) & 255`` is BELOW ``lo`` or ABOVE
#: ``hi`` -- a signed error in [-47, +47]. 112 of the 114 stock sites use these; the other 2 (field 1460 and
#: 3059, regions that open a path, no warp) use (56, 200).
FACE_WINDOW = (48, 208)

#: World units one MovePC call moves him, walking or running (a run is two such calls a tick,
#: FieldMapActorController.cs:197-208) -- so a press that moved him ``d`` units FREELY spent at least
#: ``d / STEP_PER_CALL`` calls (no call steps further), and each of those turned him (:func:`turn_step`).
STEP_PER_CALL = 30.0

#: The lerp factor of one MovePC call (FieldMapActorController.cs:756: ``Mathf.Lerp(rot, target, 0.4f)``).
TURN_PER_CALL = 0.4

#: One 256th of a turn, in degrees: the unit the gate compares in.
UNIT_DEG = 360.0 / 256.0



def face_limit_deg(window=FACE_WINDOW) -> float:
    """The largest CONTINUOUS error, in degrees, a planner may count on a gate with compare constants ``window`` =
    ``(lo, hi)`` passing: the door fires for ``v < lo`` or ``v > hi`` (strict), a signed error of at most ``lo - 1``
    one way and ``255 - hi`` the other -- the nearer of the two, in units. What the bytes add on top -- the facing byte
    and the bearing byte each floored to a unit, the math table's 1/4096 -- is :func:`worst_face_error`'s one UNIT_DEG
    of quantization."""
    lo, hi = int(window[0]), int(window[1])
    return min(lo - 1, 255 - hi) * UNIT_DEG


#: :func:`face_limit_deg` of the stock window: 47 units (the strict ``< 48`` / ``> 208``), 66.09 degrees.
FACE_LIMIT_DEG = face_limit_deg()

#: angleAsm's atan table, 1025 entries in 4096ths of a turn -- the MATH approximation of the game's
#: ``ratan_tbl.bin`` (see the module docstring: the shipped table is Square Enix data and never lives here).
ATAN_TABLE = tuple(round(math.atan(i / 1024) * 2048 / math.pi) for i in range(1025))


def _cdiv(a: int, b: int) -> int:
    """C# Int32 division: the quotient truncated toward zero (Python's ``//`` floors)."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def _round_to_int(x: float) -> int:
    """Mathf.RoundToInt: Math.Round, a midpoint to EVEN -- as Python's own ``round`` does. What both
    CastFloatToIntWithChecking (EBin.cs:1821-1831) and ConvertFloatAngleToFixedPoint (:1248-1258) reduce to: their
    floor / ceil comparison always returns the rounded value."""
    return round(x)


def _float32(x: float) -> float:
    """``(Single)x`` -- the float32 the engine holds before it rounds an angle."""
    return struct.unpack("<f", struct.pack("<f", x))[0]


def calc_exit_position(px: float, pz: float, q0, q1) -> tuple[int, int]:
    """CalculateExitPosition (0xA4, DoEventCode.cs:2213-2240): (``px``, ``pz``) -- his float position -- projected
    onto the segment ``q0 -> q1``, as the ints the engine stores in SYSVAR 10 / 11 (``sMapJumpX`` / ``Z``).

    With ``e = q1 - q0``: ``d = (ex*ex + ez*ez) >> 8``; ``t = (trunc(ex * (px - q0x)) + trunc(ez * (pz - q0z)))
    / d`` in C# truncating division, clamped to [0, 256] -- onto the SEGMENT, so beyond either end he aims at that
    end; ``d == 0`` (an edge under 16u) leaves ``t = 0``, the point q0. The point is ``((t*ex) >> 8) + q0x,
    ((t*ez) >> 8) + q0z`` (an arithmetic shift, flooring)."""
    q0x, q0z = int(q0[0]), int(q0[1])
    ex, ez = int(q1[0]) - q0x, int(q1[1]) - q0z
    t = (ex * ex + ez * ez) >> 8
    if t != 0:
        t = _cdiv(int(ex * (px - q0x)) + int(ez * (pz - q0z)), t)
        t = 0 if t < 0 else (256 if t > 256 else t)
    return (t * ex >> 8) + q0x, (t * ez >> 8) + q0z


def angle_asm(dx: float, dz: float) -> int:
    """angleAsm before its degree conversion (EBin.cs:1558-1584): the direction of (dx, dz) in 4096ths of a turn,
    ``atan2(-dx, -dz)`` -- 0 = -z, 1024 = -x, +-2048 = +z, -1024 = +x -- in [-2048, 2048]. Both deltas are
    truncated to ints first, as its ``(Int32)`` casts do; a zero delta is 0. Reads :data:`ATAN_TABLE` (the math
    approximation of the game's table) with the engine's own octant arithmetic, index for index."""
    n1, n2 = int(dx), int(dz)
    if n1 == 0 and n2 == 0:
        return 0
    n3, n4 = n2 << 10, n1 << 10
    t = ATAN_TABLE
    if n2 >= 0:
        if n1 >= 0:
            return -1024 - t[_cdiv(n3, n1)] if n1 - n2 >= 0 else t[_cdiv(n4, n2)] - 2048
        return 2048 - t[-_cdiv(n4, n2)] if -n1 - n2 < 0 else 1024 + t[-_cdiv(n3, n1)]
    if n1 >= 0:
        return -t[-_cdiv(n4, n2)] if n1 + n2 < 0 else t[-_cdiv(n3, n1)] - 1024
    return 1024 - t[_cdiv(n3, n1)] if n1 - n2 < 0 else t[_cdiv(n4, n2)]


def eb_bearing(dx: float, dz: float) -> int:
    """What B_ANGLE2 pushes (EBin.cs:1182-1192): :func:`angle_asm` floored to 256ths (``>> 4``), in [-128, 128].
    0 = -z, 64 = -x, +-128 = +z, -64 = +x; a zero delta is 0."""
    return angle_asm(dx, dz) >> 4


def facing_byte(yaw_deg: float) -> int:
    """obj.f[3] on a field (EBin.cs:1786-1799): the yaw ``Actor.rotAngle[1]`` in degrees ->
    ``(RoundToInt((float)(deg / 360 * 4096)) >> 4) & 255``, 0..255 in 256ths of a turn, the bearing's convention
    (0 = -z, 64 = -x, 128 = +z, 192 = +x)."""
    return (_round_to_int(_float32(yaw_deg / 360.0 * 4096.0)) >> 4) & 255


def yaw_of_byte(b: int) -> float:
    """A yaw, in degrees in [-180, 180), whose :func:`facing_byte` is exactly ``b``: the byte's own angle,
    ``b * 360 / 256``, wrapped -- the inverse a test or a plan states a facing byte through."""
    deg = (int(b) % 256) * UNIT_DEG
    return deg - 360.0 if deg >= 180.0 else deg


def gate_value(px: float, pz: float, yaw_deg: float, q0, q1) -> int:
    """``Map.Int16[6]`` exactly as the stock let stores it: ``(facing - bearing) & 255`` -- the facing of
    ``yaw_deg`` against the bearing from his ROUNDED position (f[0], f[2]) to :func:`calc_exit_position` of his
    float one."""
    jx, jz = calc_exit_position(px, pz, q0, q1)
    return (facing_byte(yaw_deg) - eb_bearing(jx - _round_to_int(px), jz - _round_to_int(pz))) & 255


def signed_error(v: int) -> int:
    """A gate value 0..255 as a signed error in [-128, 127] (256ths): positive = he faces counter-clockwise of the
    bearing seen from above (toward -x of it when the bearing is -z)."""
    v &= 255
    return v - 256 if v >= 128 else v


def door_faced(px: float, pz: float, yaw_deg: float, q0, q1, window=FACE_WINDOW) -> tuple[bool, int]:
    """``(faced, signed_err)`` for a stock class-2 door: whether its gate lets tag 2 on to the warp for a player at
    (``px``, ``pz``) with yaw ``yaw_deg`` (degrees, ``Actor.rotAngle[1]`` -- NOT state.json ``player.dir``), and the
    gate value as a signed error in 256ths. ``q0``, ``q1`` = the region's first two SetRegion points, in engine
    order (``scan_gateways``' ``zone[0]`` / ``zone[1]`` -- or ``region[0]`` / ``region[1]``). ``window`` =
    ``(lo, hi)``, the compare constants: faced iff ``v < lo or v > hi`` (strict) -- with the stock (48, 208),
    iff ``-47 <= signed_err <= 47``."""
    lo, hi = int(window[0]), int(window[1])
    v = gate_value(px, pz, yaw_deg, q0, q1)
    return (v < lo or v > hi), signed_error(v)


def yaw_of(dx: float, dz: float) -> float:
    """The yaw, in degrees, a press converges to when it moves him along world (``dx``, ``dz``):
    ``atan2(-dx, -dz)`` (FieldMapActorController.cs:748) -- 0 faces -z, 90 faces -x, +-180 faces +z, -90 faces +x.
    A harness caller passes the world direction its calibrated basis gives for the pad it holds (the field's
    twist already in it)."""
    return math.degrees(math.atan2(-dx, -dz))


def turn_step(yaw: float, pressed_yaw, calls: float = 1.0) -> float:
    """His yaw after ``calls`` MovePC calls holding a direction that points at ``pressed_yaw`` (degrees; None =
    nothing held -> unchanged, as standing keeps the yaw exactly). One call (FieldMapActorController.cs:744-761):
    unwrap the target to within 180 of the yaw (a target exactly 180 away is left as it is), lerp 0.4 of the way,
    wrap into [-180, 180]. Toward a fixed target the unwrap never changes side, so ``k`` calls are one lerp by
    ``1 - 0.6**k`` -- the form used here. A FRACTION of a call is the AVERAGE a frame turns him (a walked harness
    frame is half a call at 15u of a 30u step, :func:`movepc_calls` -- FakeGame's model); the engine turns in whole
    calls, so a planner prices a press at :func:`sure_calls`. A press into a wall still turns him: the caller counts
    the calls a held direction spent whether or not he moved."""
    if pressed_yaw is None or calls <= 0:
        return yaw
    m = float(pressed_yaw)
    if abs(m - yaw) > 180.0:
        m = m - 360.0 if m > yaw else m + 360.0
    r = yaw + (m - yaw) * (1.0 - (1.0 - TURN_PER_CALL) ** calls)
    while r > 180.0:
        r -= 360.0
    while r < -180.0:
        r += 360.0
    return r


def movepc_calls(units_per_frame: float) -> float:
    """The MovePC calls a frame spends ON AVERAGE at ``units_per_frame`` of held movement -- its distance over the 30u
    each call steps (:data:`STEP_PER_CALL`). At the harness's calibrated 30u (run) and 15u (walk) frames that is 1 and
    0.5. It is exactly as good as the speed it is given: the harness's are constants measured once, on bench 30801,
    at that machine's 60 fps (Session.RUN_SPEED / WALK_SPEED) -- the render rate follows the monitor, a tick the wall
    clock, so on a 144 Hz monitor a walked frame is about 0.21 calls, not 0.5. A planner that counts on it checks the
    presses it made against the distance they moved (a free press never moves him further than its calls step), and
    counts only :func:`sure_calls` of it."""
    return float(units_per_frame) / STEP_PER_CALL


def sure_calls(frames: int, per: float) -> int:
    """The WHOLE MovePC calls a hold of ``frames`` frames is sure of at ``per`` calls a frame on average
    (:func:`movepc_calls`): ``floor(frames * per)``. The engine turns and steps him in whole calls, one (walking) or
    two (running) a 30 Hz tick, and a tick falls on a frame in a phase nobody sees (FPSManager.cs:77-110 paces it on
    the wall clock; HonoBehaviorSystem.cs:106 runs the ticks a frame asks) -- so at 60 fps a 9-frame walked hold is 4
    calls or 5, a 3-frame one 1 or 2: a planner counts the fewer. (A hold of an even count, at 0.5, is exactly its
    half.)"""
    return int(math.floor(frames * per + 1e-9))


def bearing_deg(px: float, pz: float, q0, q1) -> float:
    """The bearing the gate floors to a unit (:func:`gate_value`), CONTINUOUS, in degrees in the yaw's convention: from
    his rounded position to :func:`calc_exit_position` of his float one, ``yaw_of`` of the delta -- 0 for a zero delta,
    as angleAsm answers it (EBin.cs:1587-1588; ``atan2(-0.0, -0.0)`` alone would say -180). What a planner measures a
    press's offset from; the byte floor is :func:`worst_face_error`'s to allow for."""
    jx, jz = calc_exit_position(px, pz, q0, q1)
    dx, dz = jx - _round_to_int(px), jz - _round_to_int(pz)
    return 0.0 if dx == 0 and dz == 0 else yaw_of(dx, dz)


def angle_off(a_deg: float, b_deg: float) -> float:
    """How far apart two yaws are, degrees, 0..180."""
    return abs((a_deg - b_deg + 180.0) % 360.0 - 180.0)


def worst_face_error(offset_deg: float, calls: float, spread_deg: float = 0.0, off_before: float = 180.0) -> float:
    """The largest error, in degrees, a press can leave his yaw facing the door with -- PLANNED, never measured (the
    yaw is not read): after ``calls`` WHOLE MovePC calls (:func:`sure_calls` of the frames pressed: a fraction of a
    call is only an average, and the fewer whole calls the engine may deliver leave more of the turn -- with a
    fractional ``calls`` this is the average's error, not the largest) holding a direction ``offset_deg`` off the bearing
    (:func:`bearing_deg`), from a yaw at most ``off_before`` off that direction (180: unknown -- any yaw):

      * ``off_before * 0.6 ** calls`` -- what the lerp leaves of the turn (:func:`turn_step`'s closed form; the unwrap
        never changes side toward a fixed target, so the bound holds from either side);
      * ``offset_deg`` -- the direction pressed is a pad's, up to 22.5 degrees off the bearing for the nearest of the
        eight, and the yaw converges to the pad, not the bearing;
      * ``spread_deg`` -- how far that pad may truly head off the direction it was calibrated as (a measured basis);
      * one UNIT_DEG -- the facing byte and the bearing byte each floored to a unit, and the math table's 1/4096.

    The door fires for sure once this is at most :data:`FACE_LIMIT_DEG`. From any yaw the nearest pad, on a basis
    measured to 2 degrees, is sure after 4 calls (180 * 0.6**4 = 23.3, + 22.5 + 2 + 1.4 = 49.2); after 3 it is 64.8,
    1.3 to spare, and after 2, 90.7: a press that short may leave the door shut."""
    return off_before * (1.0 - TURN_PER_CALL) ** calls + offset_deg + spread_deg + UNIT_DEG


def _in_triangle_xz(x: float, z: float, a, b, c) -> bool:
    """Math3D.PointInsideTriangleTest with ``largeBorder`` (Math3D.cs:28-43), on XZ: barycentric, border-inclusive
    to ``u + v <= 1.000001``. A degenerate triangle (a repeated or collinear vertex) contains nothing: the engine's
    ``1 / 0`` makes both coordinates NaN, and every compare with NaN is false. Its divisor ``|AC|^2 |AB|^2 -
    (AC.AB)^2`` is the square of the cross product AC x AB (Lagrange's identity), whose zero is tested exactly."""
    acx, acz = float(c[0]) - a[0], float(c[1]) - a[1]
    abx, abz = float(b[0]) - a[0], float(b[1]) - a[1]
    apx, apz = x - a[0], z - a[1]
    cross = acx * abz - acz * abx
    if cross == 0:
        return False
    acsq, acab, acap = acx * acx + acz * acz, acx * abx + acz * abz, acx * apx + acz * apz
    absq, abap = abx * abx + abz * abz, abx * apx + abz * apz
    den = cross * cross
    u = (absq * acap - acab * abap) / den
    v = (acsq * abap - acab * acap) / den
    return u >= 0.0 and v >= 0.0 and u + v <= 1.000001


def region_contains(x: float, z: float, points) -> bool:
    """IsInQuad (TreadQuad.cs:24-39): is (``x``, ``z``) inside the region whose SetRegion points are ``points``
    (engine order, all of them -- ``scan_gateways``' ``region``)? True when any of the n triangles
    ``(q[i], q[i+1 mod n], q[i+2 mod n])`` holds it (:func:`_in_triangle_xz`). A convex 3- or 4-gon is covered
    whole; a convex 5- to 8-gon only as the ring of its ears, its inner polygon a dead zone; the kit's doubled
    trailing vertex changes nothing. Fewer than 3 distinct points contain nothing."""
    pts = [(float(p[0]), float(p[1])) for p in points]
    n = len(pts)
    return any(_in_triangle_xz(x, z, pts[i], pts[(i + 1) % n], pts[(i + 2) % n]) for i in range(n))
