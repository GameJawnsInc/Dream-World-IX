"""Compose a hand-drawn multi-room FLOORPLAN into N wired FF9 fields (click-authoring Rung 6).

The author lays rooms out on a plan-view chart, declares which shared walls are doors, and this
turns that into a dungeon: one field per room, gateways both ways, an arrival position AND FACING
per side, encounters, save-point siting.

★ THE DRAWN-MESH LAW -- the human draws the walkmesh; this module never infers one. Auto-deriving a
walkmesh from a drawing is a research problem (segmentation, plane inference, semantic room
boundaries). Sequencing the composer AFTER the tracing rungs retires that problem: geometry arrives
hand-drawn and exact, and what is left is TOPOLOGY -- deterministic, testable, no inference.
:func:`shared_edges` OFFERS candidate walls; the author declares the door.

★ THE TWO-FRAME LAW -- FF9 fields have NO spatial relationship to each other; there is no global
dungeon coordinate system in the engine. The plan layout is an authoring fiction, so every room's
geometry is re-centred into its OWN field frame on emit, and EVERY derived artifact of that room
rides the SAME integer ``off_r``: door quads, arrivals, spawn, savepoint, and the background art.
Mixing frames is this rung's equivalent of the transpose bug -- it looks plausible and is wrong.
``off_r`` must be INTEGER because :func:`ff9mapkit.scene.bgi.build` rounds every vert; a fractional
offset lets the mesh, the quads and the arrival round independently and drift apart by up to 1u.

Every formula here survived an adversarial pass that derived each one independently and ran probes
against the real code. The record of what that caught -- and why several obvious-looking values are
wrong -- is ``studies/click-authoring/RUNG6.md`` §1. Read it before changing a constant. Highlights:

  * The door's inward normal is anchored to the polygon's OWN carrying edge. Deriving it from a
    point-in-polygon probe inverts on 48.5% of hand-drawn (non-coincident) walls, identically for
    both rot90 signs, because off-coincident BOTH probe points are inside or both outside.
  * ``R_WALK = 80``, matching ``cam.COLLISION_RADIUS_W`` (also fixed to 80, was wrongly 48 -- its
    stated basis, ``bgiRad*4`` off the ``.bgi``, was wrong: ``bgiRad``'s only writer is the
    battle-return backup, so it's 0 on a fresh load). IN-GAME CONFIRMED 2026-07-30: walked into a
    wall at world z=300 in a purpose-built calibration field (id 30510); the debug HUD read the
    clamped stop at exactly z=220, i.e. inset 80. See ``scene/cam.py:66-77`` for the fixed
    constant + full chain, and ``studies/click-authoring/RUNG6.md`` §6.1 for the resolved history.
  * The camera fit MUST gate on per-vertex depth. Apparent size goes as ``1/|D + cos(p)z|``, which
    has a POLE, so a box-only test accepts a camera 740u INSIDE the room.
  * The canvas-row inverse -- a painted row back to a world ``z`` -- is a Mobius function of ``z``
    with a POLE at the camera's own depth plane; past it the engine's ``|res.z|`` divide mirrors the
    SAME canvas row onto a point BEHIND the camera. ``cam.solve_z_for_canvasY`` /
    ``cam.horizon_canvas_y`` used to bisect across that pole and lose reachable low-pitch rows --
    FIXED 2026-07-29 (CHANGELOG "the painted-row inverse spanned the projection pole"): both are now
    exact closed forms on the camera's front branch, and this module calls them DIRECTLY.
    :func:`project_floor` is a thin composition of :func:`cam.to_canvas` + :func:`cam.project`, not
    an independent formula -- there is no private copy of this math left in this module to fork.
  * A ``face``-less ``[[player.arrival]]`` row is not "no facing" -- the template's unconditional
    ``D9(6)`` default is 0 = SOUTH, i.e. a silent "face the camera whichever wall you came through".
"""
from __future__ import annotations

import contextlib
import math
import threading
from bisect import bisect_left, bisect_right
from collections import OrderedDict
from dataclasses import dataclass, field as _dc_field

from . import imagefield as _if
from . import journey as _journey
from . import pack as _pack
from .scene import cam as _cam
from .scene import guide as _guide


class ComposeError(ValueError):
    """A floorplan that cannot become a legal dungeon. Carries every problem found, not the first."""

    def __init__(self, *problems):
        self.problems = [p for p in problems if p]
        super().__init__("; ".join(self.problems) if self.problems else "compose failed")


# ------------------------------------------------------------------ constants (sourced, not guessed)

# ★ THE WALL RADIUS. Chain (all four links traced AND byte/source verified): the kit's player
# Init runs CreateObject then SetObjectLogicalSize(20, 24, 40) (confirmed by disassembling the
# blank-field template, offset 731) -> Memoria EventEngine.DoEventCode.cs:1500 `size = getv1()`
# (arg1 == 20) -> :1531 `component1.radius = size * 4` == 80 -> FieldMapActorController.cs:1057
# RadiusValid -> WalkMesh.cs:1976 BGI_computeNewPoint pins the centre at EXACTLY radius off an
# inaccessible edge. IN-GAME CONFIRMED (2026-07-30, calibration field 30510): walked into a wall
# at world z=300, debug HUD read the clamped stop at exactly z=220 -- inset 80, not 48.
# cam.COLLISION_RADIUS_W (scene/cam.py:71) is now ALSO 80 (was wrongly 48 until this same pass --
# its old comment's basis, bgiRad*4, was factually wrong: bgiRad is 0 on a fresh load, its only
# writer is the battle-return backup at EventEngine.cs:1443). Kept as this module's own constant
# (not imported from cam) so a future regression in cam.py can't silently loosen these gates.
R_WALK = 80.0

R_OBJ = _cam.OBJECT_COLLISION_W          # 96.0 (scene/cam.py:82) -- correct in the repo: arg2 = 24
K_VSCALE = _cam.K_VSCALE                 # 14/15 (scene/cam.py:36)
CANVAS_W = _guide.CANVAS_W               # 384 (scene/guide.py:24) -- NOT in cam.py
CANVAS_H = _guide.CANVAS_H               # 448
FRONT_ROW = 420.0                        # guide.frame_floor's own front default (scene/guide.py:121)
FAN_TOL = 0.02                           # the repo's own gap/spill threshold (workspace/backdrop.py:576)
WORLD_LO, WORLD_HI = _journey.WORLD_ID_LO, _journey.WORLD_ID_HI      # 9000, 9012 (journey.py:62)
ID_MIN, ID_MAX = _pack.CUSTOM_ID_MIN, _pack.FIELD_ID_MAX             # 4000, 32767

NEAR_W = 200.0        # near-plane clearance. synth_r_t's Int16 quantization is 0.06px at depth 2000
                      # but blows up without bound as the projection pole is approached.
FIT_MARGIN = 8.0      # canvas px. Quantization is <=0.07px at depth>=500, so 8 is safe; 2 is not.
DEPTH_DEFAULT = 250.0     # door strip depth: 68.3% of the strip standable at R_WALK
DEPTH_WARN = 170.0        # ARRTEST's in-game-proven wall-press depth: 53.5% standable
DEPTH_MIN = 2 * R_WALK    # 160u. The player centre is clamped >= R_WALK off the wall, so a strip of
                          # depth d gives a standable WINDOW only (d - R_WALK) wide. Requiring that
                          # window to be at least the player's own radius means the player cannot
                          # step clean over it in one motion -- and it lands just under the
                          # in-game-proven 170, so every real shipped strip depth passes. The naive
                          # gate `depth > R_WALK` accepts an 81u door whose window is a ONE-UNIT
                          # sliver; the layout skill's own warning is that a bare on-mesh test
                          # "happily accepts a 1u edge sliver; a unit sent there is shoved off it".
GRID_STEP = 8.0           # world units -- the sampling step for every area/clearance test
AREA_FLOOR = 4.0 * GRID_STEP * GRID_STEP   # a polygon smaller than a few cells is a drawing slip
PITCH_SLACK = 1.0         # degrees of margin above the hard horizon-in-canvas threshold
DEFAULT_PITCH = 48.0      # pack.new_project's scaffold pitch (pack.py:150); safe by 22deg over p*
DEFAULT_FOV = 42.2        # pack.new_project's scaffold fov
STANDABLE_WARN = 0.35     # warn under this standable/total area ratio
# ★ LEGIBILITY, measured off the real game. `studies/click-authoring/camera_census.py` over all 741
# shipped FF9 cameras, restricted to the composer-comparable pitch >= 26 (n = 217): an R_OBJ-wide
# character covers p05 3.9px, p10 5.3, p25 7.4, MEDIAN 9.3, p75 12.2 canvas px. Widest range Square
# ever painted is 960x1088. These are not taste; they are the envelope the game itself shipped in.
CHAR_PX_REFUSE = 3.9      # below the 5th percentile of every real camera -- refuse, it is a sliver
CHAR_PX_WARN = 7.4        # below the 25th -- compose, but say so and name the remedy
CHAR_PX_MEDIAN = 9.3      # quoted in the messages so the number has a scale attached
# ★ THE SCROLL CAP IS FF9'S OWN WIDEST SHIPPED PAINTING (960 x 1088 across the 741-camera census).
# 768x448 is the one width proven in-game in this repo (the field-4003 spike); 960 is inside
# Square's envelope but unproven HERE, so it is a playtest item, not an offline claim. Anything
# wider is not a camera problem -- it is two rooms and a door, which is what FF9 does with a large
# space and what this composer already builds. OWNER DECISION 2026-07-31: cap at 960, split beyond.
SCROLL_RANGE_CAP = 960
_LAYER_GAP = 500          # OT-depth slack between the walkmesh's far edge, the floor layer and the
#                           backdrop. Covers the entry settle and content sited slightly past the
#                           mesh; see _placeholder_layers for why these are DERIVED, not constants.
BAND_REACH = 2 * R_WALK   # 160u -- how far "one step" reaches, for the axis-band WARN. THE PLAYER'S
                          # OWN DIAMETER: inside it, one body-length of involuntary displacement
                          # (the entry settle, a wall clamp, a single input frame) bridges the gap,
                          # which is exactly what the warning claims. Beyond it the player has to
                          # walk there on purpose, and saying "one step could fire it" is false.
                          # ★ WAS 4*R_WALK = 320, a tuned judgment, and 320 was measurably wrong:
                          # the gap is (the room's extent perpendicular to the wall)/2 minus the
                          # strip depth, so a 320 reach warns about EVERY room under ~1140u across.
                          # The first real dungeon anyone drew -- two rooms, one door, nothing wrong
                          # with it -- got two warnings, at 183u and 244u. A warning that fires on
                          # the ordinary case teaches nothing and hides the one that matters. The
                          # incident this gate exists for (a spawn 10u outside a sign zone) is still
                          # caught by a wide margin. Never widen this to silence a real finding:
                          # if a spawn is genuinely a step from a trigger, MOVE THE SPAWN.
TOUCH_EPS = 1e-6


# ------------------------------------------------------------------ C0: the closed-form projection

def project_floor(x, z, c):
    """``(canvasX, canvasY, depth)`` for a floor point on the ``y=0`` plane.

    A thin composition of the shared projection, not an independent formula: the canvas coordinate
    is :func:`cam.to_canvas`, exactly; the depth is :func:`cam.project`'s own signed ``result.z``,
    exactly. The reason to have it at all is that third value -- ``to_canvas`` folds ``abs(resz)``
    (scene/cam.py:166), which MIRRORS a behind-camera point into an ordinary-looking in-canvas
    coordinate, and the SIGNED depth is the only thing that can see that."""
    return (*_cam.to_canvas((x, 0, z), c), _cam.project((x, 0, z), c)[2])


def pitch_floor(fov_x_deg, *, range_w=CANVAS_W, range_h=CANVAS_H):
    """The pitch below which the composer refuses. ``p* = atan((h/2) / (K_VSCALE * H))``.

    ONE inequality guarding TWO hazards: under ``p*`` the horizon sits INSIDE the canvas (part of
    the frame has no floor at all) AND a behind-camera floor point can land on-canvas and fake a
    fit. Measured 25.64deg at fov 42.0, 25.73deg at fov 42.2."""
    H = _guide.proj_from_fov_x(fov_x_deg, range_w)
    return math.degrees(math.atan((range_h / 2.0) / (K_VSCALE * H)))


# ------------------------------------------------------------------ plane geometry primitives

def bbox(poly):
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    return (min(xs), min(zs), max(xs), max(zs))


def edges(poly):
    n = len(poly)
    return [(poly[i], poly[(i + 1) % n]) for i in range(n)]


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def _scale(a, k):
    return (a[0] * k, a[1] * k)


def _unit(v):
    L = math.hypot(v[0], v[1])
    return (0.0, 0.0) if L == 0 else (v[0] / L, v[1] / L)


def midpoint(seg):
    return ((seg[0][0] + seg[1][0]) / 2.0, (seg[0][1] + seg[1][1]) / 2.0)


def point_in_poly(x, z, poly):
    """Ray-cast inside test. AMBIGUOUS exactly on the boundary -- pair it with
    :func:`dist_to_boundary` whenever the answer must be STRICTLY inside."""
    inside = False
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        if (z1 > z) != (z2 > z):
            xin = x1 + (z - z1) * (x2 - x1) / ((z2 - z1) or 1e-12)
            if x < xin:
                inside = not inside
    return inside


def dist_to_boundary(x, z, poly):
    """Least distance from ``(x, z)`` to any boundary edge (0 on the boundary, positive elsewhere)."""
    best = float("inf")
    for a, b in edges(poly):
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / L2))
        best = min(best, math.hypot(x - (a[0] + t * dx), z - (a[1] + t * dz)))
    return best


def dist_point_to_poly(pt, poly):
    """0 if inside, else the distance to the nearest edge."""
    return 0.0 if point_in_poly(pt[0], pt[1], poly) else dist_to_boundary(pt[0], pt[1], poly)


def dist_point_line(pt, seg):
    """Perpendicular distance from ``pt`` to the INFINITE line through ``seg``."""
    a, b = seg
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz)
    if L == 0:
        return math.hypot(pt[0] - a[0], pt[1] - a[1])
    return abs((pt[0] - a[0]) * dz - (pt[1] - a[1]) * dx) / L


def _cross3(o, p, q):
    return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])


def segments_cross(a, b, c, d):
    """``ab`` and ``cd`` share a point: a proper crossing, OR an endpoint resting on the other.

    ⚠ THE NAME UNDERSTATES IT, DELIBERATELY, AND THE OLD DOCSTRING LIED. It used to claim
    "shared-endpoint touching returns False, which is what makes two rooms allowed to ABUT" -- it
    does not: a cross product of EXACTLY ZERO is filed with the negative side by `(d1 > 0) !=
    (d2 > 0)`, so a touch counts. That inclusiveness is CORRECT for :func:`polygon_problem`, where
    a wall ending exactly on a non-adjacent wall is a degenerate outline, and it is load-bearing in
    :func:`polys_overlap` for parallel shapes whose overlap band has every corner ON a boundary and
    so trips neither a proper crossing nor a vertex-inside test.

    It was the wrong test for ABUTMENT, and :func:`polys_overlap` is where that is now handled --
    by skipping edge pairs that share an endpoint, rather than by weakening this. Tightening it to
    strictly-proper was measured to break both: a self-touching outline was accepted, and two
    genuinely overlapping 45deg strips were called disjoint."""
    d1, d2 = _cross3(c, d, a), _cross3(c, d, b)
    d3, d4 = _cross3(a, b, c), _cross3(a, b, d)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def _shares_endpoint(ea, eb):
    """The two segments have an endpoint in common (exactly -- both are stored as ints)."""
    return any(p == q for p in ea for q in eb)


def polys_overlap(A, B, *, eps=TOUCH_EPS):
    """True when two SIMPLE polygons share interior area. Touching (a shared wall, a shared corner)
    is NOT overlap.

    ★ This is the authority, not :func:`build.region_overlap_pairs`, which is an AABB test: two
    provably disjoint 45deg bevel strips make it report a pair. Erroring on that would refuse every
    bevelled, diagonal or octagonal room -- the shapes a human actually draws. Valid for CONCAVE
    polygons too, which SAT is not, and rooms are routinely L-shaped."""
    for ea in edges(A):
        for eb in edges(B):
            # ★ SKIP EDGE PAIRS THAT SHARE AN ENDPOINT -- that is an ABUTMENT, not an overlap, and
            # it is the whole reason two rooms snapped together were refused as "sharing floor
            # area". `segments_cross` files a zero cross product with the negative side, so a wall
            # and its neighbour's next wall meeting at a welded corner read as a crossing. Latent
            # for the composer's whole life: hand-aimed corners land within `shared_edges`' 8u but
            # never on the same integer, so nothing produced exact contact until snapping did.
            # Safe to skip: if the rooms really do interpenetrate near that corner, some other edge
            # pair crosses, or a vertex of one is strictly inside the other, and both are tested.
            if _shares_endpoint(ea, eb):
                continue
            if segments_cross(ea[0], ea[1], eb[0], eb[1]):
                return True
    for p in A:
        if point_in_poly(p[0], p[1], B) and dist_to_boundary(p[0], p[1], B) > eps:
            return True
    for p in B:
        if point_in_poly(p[0], p[1], A) and dist_to_boundary(p[0], p[1], A) > eps:
            return True
    return False


# ------------------------------------------------------------------ C1: polygon health

def polygon_problem(poly, *, tol=8.0, area_floor=AREA_FLOOR):
    """None if ``poly`` is a legal room outline, else the reason it is not.

    ★ Test 3 is a REAL O(n^2) segment-intersection test, and the draft's rationale for the gate was
    wrong in a way worth recording: the suspect was ``imagefield.triangulate``'s "numerically stuck
    -> fan the remainder" fallback (imagefield.py:527). Measured, that branch never fires -- a
    self-intersecting pentagon produces a triangle-area sum of 142500 against a true |shoelace| of
    37500 (a 3.8x overcount) through the ear-clip's ORDINARY termination path, and a bowtie gives
    40000 vs 0. So "did triangulate get stuck" is not a usable proxy for self-intersection.

    ★ The area floor must be tested BEFORE any ``_as_ccw`` call anywhere downstream:
    ``imagefield._as_ccw`` branches on ``_signed_area(poly) >= 0`` (imagefield.py:456), so a
    zero-area polygon silently "keeps order" and its winding then carries no meaning.

    ★ There is deliberately NO concavity test. A valid concave L and a valid U both triangulate
    exactly (30000/30000 and 48000/48000 measured) -- the notch is not where the bug lives."""
    if len(poly) < 3:
        return f"only {len(poly)} vertices -- a room outline needs at least 3"
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        if d < tol:
            return (f"vertices {i} and {(i + 1) % n} are {d:.1f}u apart (under {tol:g}u) -- "
                    f"a duplicated corner")
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i or (j + 1) % n == i or j == (i + 1) % n:
                continue                                # adjacent edges share an endpoint
            c, d = poly[j], poly[(j + 1) % n]
            if segments_cross(a, b, c, d):
                return (f"walls {i}-{(i + 1) % n} and {j}-{(j + 1) % n} cross -- the outline "
                        f"intersects itself")
    area = abs(_if._signed_area(poly))
    if area < area_floor:
        return f"area {area:.0f} sq.u is under the {area_floor:.0f} floor -- a degenerate outline"
    if all(abs(_cross3(poly[0], poly[1], p)) < 1e-6 for p in poly[2:]):
        return "every vertex is collinear -- there is no interior"
    return None


# ------------------------------------------------------------------ C1b: where the player can stand

def standable(poly, *, R=R_WALK, step=GRID_STEP):
    """The grid cells whose centre is inside ``poly`` AND at least ``R`` from its boundary -- every
    position the player CENTRE can actually occupy. Keys are ``(floor(x/step), floor(z/step))``.

    ★ Do NOT erode with ``imagefield.outset_polygon(poly, -R)``. That is a MITER offset
    (imagefield.py:471) and it explodes on acute vertices: measured at only a 48u offset with base
    verts 100u apart -- so every one of C1's tests passes -- a 4.76deg half-angle moves the tip 244u,
    1.43deg moves it 913u, and 0.14deg moves it 9552u. A plain L-shape (90deg reflex) outsets
    cleanly, so no convex fixture can catch this. Grid sampling has no miter and cannot blow up.
    ``outset_polygon`` is still right for the ART path -- gate it there with a miter limit."""
    return set(standable_map(poly, R=R, step=step))


def _edge_data(poly):
    """``(ax, az, dx, dz, L2)`` per edge -- everything :func:`dist_to_boundary` recomputes per
    sample that does not actually depend on the sample, hoisted out of the per-cell loop."""
    n = len(poly)
    out = []
    for i in range(n):
        ax, az = poly[i]
        bx, bz = poly[(i + 1) % n]
        dx, dz = bx - ax, bz - az
        out.append((ax, az, dx, dz, dx * dx + dz * dz))
    return out


def _min_dist_to_edges(x, z, ed):
    """:func:`dist_to_boundary` against pre-built :func:`_edge_data` -- same value, bit for bit,
    without rebuilding every edge's ``dx/dz/L2`` once per sample."""
    best = float("inf")
    for (ax, az, dx, dz, L2) in ed:
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
        d = math.hypot(x - (ax + t * dx), z - (az + t * dz))
        if d < best:
            best = d
    return best


def _axis(lo, hi, step):
    """The EXACT sample sequence ``v = lo; while v <= hi + step: v += step`` walks.

    Repeated addition, deliberately -- NOT ``lo + k * step``. The two disagree in the last bits, and
    a cell key is ``floor(v / step)``, so a last-bit difference can move a sample across a cell
    boundary and change a gate's verdict for no reason anyone could ever debug."""
    out, v = [], lo
    while v <= hi + step:
        out.append(v)
        v += step
    return out


def _row_crossings(poly, z):
    """Sorted x where the horizontal line at ``z`` crosses ``poly``; inside is
    ``[xs[2k], xs[2k+1])``.

    Half-OPEN on purpose: that is exactly the set :func:`point_in_poly`'s strict ``x < xin`` test
    calls inside, so a scanline and a per-point test agree cell for cell."""
    xs = []
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        if (z1 > z) != (z2 > z):
            xs.append(x1 + (z - z1) * (x2 - x1) / ((z2 - z1) or 1e-12))
    xs.sort()
    return xs


def standable_map(poly, *, R=R_WALK, step=GRID_STEP):
    """``{(i, j): distance from the SAMPLE to the nearest wall}`` over :func:`standable`'s cells.

    ⚠ THE DISTANCE IS MEASURED AT THE SAMPLE, NOT AT THE CELL CENTRE, and the two are different
    points -- the sample is ``x0 + k*step`` walked from this polygon's own bbox, the centre is
    ``(i + 0.5) * step`` on the absolute grid. So this number is NOT a drop-in for
    :func:`interior_point`'s ranking distance, however much it looks like one. Swapping it in moved
    the spawn a whole cell on 4 of 22 random plans that composed. It is returned because it is free
    here and a caller that genuinely wants the sample's clearance should not re-measure it.

    ★ THE SCANLINE. Cells outside the polygon are skipped by row rather than rejected one at a time,
    and the distance loop exits the moment any edge is closer than ``R`` (the cell has already
    failed; the exact minimum is then nobody's business).

    ★ THE ARITHMETIC IS PINNED to :func:`dist_to_boundary`'s, term for term -- the division rather
    than a hoisted reciprocal, and ``x - (ax + t*dx)`` rather than ``(x - ax) - t*dx``. Both
    shortcuts are algebraically identical, ~1e-13 apart in floating point, and measured to move the
    distance on 60 of 240 random polygons. That is nothing to a gate and everything to "the verdict
    did not change". Differentially swept against the original double loop over 240 rect/L/U/blob
    polygons x 4 radii x 3 steps: cell sets and distances BITWISE identical, 2.4x faster.
    ``tests/test_floorplan.py`` keeps that sweep."""
    x0, z0, x1, z1 = bbox(poly)
    xs_grid = _axis(x0, x1, step)
    ed = _edge_data(poly)
    out = {}
    for z in _axis(z0, z1, step):
        xs = _row_crossings(poly, z)
        for k in range(0, len(xs) - 1, 2):
            lo, hi = xs[k], xs[k + 1]
            for gi in range(bisect_left(xs_grid, lo), len(xs_grid)):
                x = xs_grid[gi]
                if x >= hi:
                    break
                best = None
                for (ax, az, dx, dz, L2) in ed:
                    t = 0.0 if L2 == 0 else max(
                        0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
                    d = math.hypot(x - (ax + t * dx), z - (az + t * dz))
                    if d < R:
                        best = None
                        break
                    if best is None or d < best:
                        best = d
                if best is not None:
                    out[(int(math.floor(x / step)), int(math.floor(z / step)))] = best
    return out


class GeomCache:
    """The live gate's memo: every ANSWER a compose needs about a room, keyed on its coordinates.

    ★ WHY IT EXISTS. The Floorplan tab re-runs the WHOLE of :func:`compose` 140ms after every
    gesture, so nudging one corner of an eight-room plan re-derived seven untouched rooms from
    scratch. Keying on the polygon's own coordinates rather than on a room's identity is what makes
    that one mechanism: an unchanged room is a hit even though the tab rebuilds the plan dict from
    scratch every judge, a dragged room is a miss because it genuinely changed, and undo -- which
    restores a ``deepcopy``, a new object with the old coordinates -- is a hit.

    ★ IT MEMOIZES THE REDUCTIONS, NOT THE GEOMETRY, AND THAT IS THE DESIGN, NOT AN ECONOMY.
    The first version cached the fat intermediates -- the cell map, the strip's point list, the
    component sets -- and it was wrong twice over:

      * **Memory.** One tab retained **1.28 GB** after ~9 seconds of dragging a two-room plan
        (64 poses x a 58,000-cell map), and roughly half of it was never read: ``compose`` consumes
        the component list as ``len(comps)`` and ``len(comps[0])``, and the strip's point list as
        ``if not pts``. Nothing ever looked at the objects.
      * **The cliff.** ``compose`` touches each key exactly ONCE per judge, in a fixed order --
        a cyclic scan, which is the one access pattern an LRU is pathological on. Above the cap the
        hit rate is not degraded, it is EXACTLY ZERO: the entry evicted is always the one wanted
        next. Measured on a chain of rooms with one door each, at ``limit=64``: 32 doors -> 291/291
        hits, 0.04s; **33 doors -> 102/300 hits and 9.0s**. A 25-room grid dungeon put a gesture
        back at 4.3s. The playtest could not have found it -- the test plan only goes to 12 rooms.

    So the durable stores hold tuples of ints and floats, which makes ``limit`` cheap enough to sit
    far above any plan a human will draw, and the cliff unreachable rather than merely further away.

    ★ THE FULL MAPS ARE TRANSIENT, SCOPED TO ONE COMPOSE (:meth:`scope`). Within a judge the same
    room's grid is wanted twice -- once for its health, once to site its spawn -- so dropping the
    map entirely would double the COLD path. Holding it past the compose is what cost the gigabyte.
    It lives for exactly as long as it is useful.

    ⚠ Values are SHARED, not copied. They are immutable tuples, which is what makes that safe.

    ``limit`` bounds each store: a slow drag mints a new polygon every judge, and an unbounded memo
    would hold every intermediate pose of every room for the life of the session."""

    def __init__(self, limit=4096):
        self.limit = int(limit)
        self.hits = 0
        self.misses = 0
        self._lock = threading.Lock()
        self._room = OrderedDict()          # poly -> (standable cells, components, largest)
        self._strip = OrderedDict()         # (poly, quad) -> (fraction, any standable at all)
        self._fan = OrderedDict()           # quad -> (gap/spill audit, fan triangle COUNT)
        self._interior = OrderedDict()      # (poly, avoid) -> ("ok", pt) | ("refused", messages)
        self._maps = {}                     # TRANSIENT -- see scope()

    def _stores(self):
        return (self._room, self._strip, self._fan, self._interior)

    def reset(self):
        """Forget everything. The tab calls this when the document is replaced -- a closed
        drawing's poses have no claim on the next one's memory."""
        with self._lock:
            for store in self._stores():
                store.clear()
            self._maps.clear()
            self.hits = self.misses = 0

    @contextlib.contextmanager
    def scope(self):
        """Hold full cell maps for the duration of ONE compose, then drop them."""
        try:
            yield self
        finally:
            with self._lock:
                self._maps.clear()

    def _map(self, poly, R=R_WALK, step=GRID_STEP):
        """The full ``standable_map``, transient. Deliberately NOT one of the durable stores."""
        key = (self._key(poly), R, step)
        with self._lock:
            m = self._maps.get(key)
        if m is None:
            m = standable_map(poly, R=R, step=step)
            with self._lock:
                self._maps[key] = m
        return m

    @staticmethod
    def _key(poly):
        return tuple((float(x), float(z)) for x, z in poly)

    def _get(self, store, key, make):
        """★ LOCKED, because the ONE caller that matters is multi-threaded. The Floorplan tab runs
        each judge on its own daemon thread and a burst of gestures leaves several alive at once;
        they share this instance. ``OrderedDict`` is not safe across a
        ``move_to_end`` / ``__setitem__`` / ``popitem`` interleave, and ``hits``/``misses`` would
        lose updates.

        The lock is DROPPED across ``make()``. Two threads racing the same key both compute it and
        the second write wins -- the values are equal, the functions are pure, and duplicating one
        grid walk is far cheaper than serializing every judge behind a 300ms one."""
        with self._lock:
            if key in store:
                self.hits += 1
                store.move_to_end(key)
                return store[key]
            self.misses += 1
        val = make()
        with self._lock:
            store[key] = val
            store.move_to_end(key)
            while len(store) > self.limit:
                store.popitem(last=False)
        return val

    def room_stats(self, poly, R=R_WALK, step=GRID_STEP):
        """``(standable cell count, number of components, largest component's cell count)`` --
        G13's whole appetite, in three ints. The map and the component SETS behind them are
        transient; nothing downstream has ever looked at either."""
        def make():
            cells = self._map(poly, R, step)
            comps = components(cells)
            return (len(cells), len(comps), len(comps[0]) if comps else 0)

        return self._get(self._room, (self._key(poly), R, step), make)

    def strip_standable(self, poly, quad, R=R_WALK, step=None):
        """``(fraction of the strip that is standable, whether ANY of it is)`` -- G9's appetite.

        The point list itself is up to 75,000 tuples per door side and its only reader is
        ``if not pts``, so keeping it was 238 MB spent on a boolean."""
        def make():
            frac, pts = strip_standable_fraction(poly, quad, R=R, step=step)
            return (frac, bool(pts))

        return self._get(self._strip, (self._key(poly), self._key(quad), R, step), make)

    def fan(self, quad):
        """``(G7's gap/spill audit, G9's fan-triangle COUNT)`` for one quad.

        Both together because both are pure functions of the same quad, and once every grid walk
        on the plan is a hit the audit becomes ~90% of what a re-judge still costs -- 56,000
        `_in_tri` calls per judge, for quads that did not move."""
        def make():
            return (_if.zone_fan_audit(quad), len(_if.fan_triangles(quad)))

        return self._get(self._fan, self._key(quad), make)

    def interior_point(self, poly, avoid, R=R_WALK, step=GRID_STEP):
        """Memoized :func:`interior_point`, INCLUDING its refusal.

        Caching the grid walk alone left most of the cost on the table: the per-cell loop that
        ranks cells and clears the avoid zones is its own full pass over every cell of the room,
        and it re-ran for all eight rooms when the author dragged one. The key carries the avoid
        polygons, so a door edit correctly misses on the rooms that door touches and hits on the
        rest.

        The refusal is memoized too, as its MESSAGES rather than the exception object -- a raise
        is as much a verdict as a point, and re-raising one live exception would keep growing its
        traceback across judges."""
        key = (self._key(poly), tuple(self._key(a) for a in avoid), R, step)

        def make():
            try:
                return ("ok", interior_point(poly, avoid, R=R, step=step, cache=self))
            except ComposeError as e:
                return ("refused", tuple(e.problems))

        kind, payload = self._get(self._interior, key, make)
        if kind == "refused":
            raise ComposeError(*payload)
        return payload


class ComposeCancelled(Exception):
    """Raised out of :func:`compose` when its ``cancel`` callback says the verdict is already
    stale. Deliberately NOT a :class:`ComposeError` -- a cancelled judge has found no problem with
    the plan, and painting it as one would put a phantom refusal on the drawing."""


def components(cells):
    """4-connected components of a cell set, largest first."""
    todo, out = set(cells), []
    while todo:
        seed = todo.pop()
        comp, stack = {seed}, [seed]
        while stack:
            i, j = stack.pop()
            for nb in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if nb in todo:
                    todo.discard(nb)
                    comp.add(nb)
                    stack.append(nb)
        out.append(comp)
    out.sort(key=len, reverse=True)
    return out


# ------------------------------------------------------------------ C2: the inward normal

def interior_normal(poly, seg, *, eps=1.0):
    """``(n, seg_on_wall)`` -- the door's INWARD normal, bound to the polygon's own carrying edge,
    plus ``seg`` PROJECTED onto that edge and oriented along the CCW traversal.

    ★ THE INVERSION THIS AVOIDS. The obvious design -- take ``rot90(q-p)`` and flip it if
    ``mid + n*eps`` tests outside the polygon -- is decisive ONLY when the seg lies EXACTLY on the
    wall, and hand-drawn walls do not: :func:`shared_edges` has an 8u tolerance precisely to admit
    them, and it hands the SAME seg to BOTH rooms, so at most one of the two can have it
    on-boundary. Off-coincident, BOTH probe points are inside (the rooms overlap slightly) or both
    outside (they gap slightly), so the polygon contributes nothing and the answer is fixed entirely
    by the arbitrary rot90 sign and the arbitrary p->q order -- neither of which anything pins.
    Measured over room B's wall offset -8..+8u in 0.5u steps x both seg orders (n=66): the probe
    design inverted 32/66 = 48.5%, identically for BOTH rot90 signs. This one: 0/66, and
    byte-identical for the same room listed CW vs CCW.

    ★ The normal REUSES ``imagefield.py:483``'s stated convention ("right normal = outward for CCW")
    rather than re-deriving it. A second independent derivation of a sign is exactly how the
    inversion gets back in.

    ★ THE RETURNED SEG IS THE ONE TO USE. C5 and C6 must consume ``seg_on_wall``, never the raw
    candidate -- the projection is what makes every derived artifact ride the room's own wall.
    Measured on a wall drawn 4u off the candidate, the unprojected version produced a gateway quad
    with 0 of 4 corners on the mesh and an arrival off the mesh entirely; this gives 4/4.

    ``eps`` is only the assertion's probe distance, never part of the decision, so it stays small.
    """
    pts = _if._as_ccw(poly)
    m = midpoint(seg)

    def penalty(i):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        if L2 <= 0:
            return float("inf")
        t = ((m[0] - a[0]) * dx + (m[1] - a[1]) * dz) / L2
        if t < -0.05 or t > 1.05:               # this edge's SPAN does not bracket the seg
            return float("inf")
        return math.hypot(m[0] - (a[0] + t * dx), m[1] - (a[1] + t * dz))

    i = min(range(len(pts)), key=penalty)
    if penalty(i) == float("inf"):
        raise ComposeError("interior_normal: no wall of this room carries that door segment")
    a, b = pts[i], pts[(i + 1) % len(pts)]
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz)
    n = (-dz / L, dx / L)                       # inward for CCW == the negation of imagefield's
                                                # "right normal = outward for CCW" (imagefield.py:483)

    def onto_wall(pt):
        t = max(0.0, min(1.0, ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dz) / (L * L)))
        return (a[0] + t * dx, a[1] + t * dz)

    s0, s1 = onto_wall(seg[0]), onto_wall(seg[1])
    if (s1[0] - s0[0]) * dx + (s1[1] - s0[1]) * dz < 0:
        s0, s1 = s1, s0                         # CCW-oriented, so C5's front edge is determinate
    m2 = midpoint((s0, s1))
    if not point_in_poly(m2[0] + n[0] * eps, m2[1] + n[1] * eps, poly):
        raise ComposeError("interior_normal fence: the computed normal points out of the room")
    return n, (s0, s1)


# ------------------------------------------------------------------ C3: the facing byte

def face_of_dir(nx, nz):
    """The FF9 facing byte for a direction -- THE ENGINE'S OWN FORMULA, not a kit convention.

    Forward: ``TurnInstant`` (DIRE 0x36) sets ``eulerAngles.y = byte/256*360``
    (Memoria EventEngine.DoEventCode.cs:1211 + EventEngineUtils.cs:1801). Inverse: the controller
    derives that same rotation from a movement vector as ``atan2(-moveVec.x, -moveVec.z)``
    (FieldMapActorController.cs:902). Composing gives the line below. Round-trips all 256 bytes
    through ``tools/field_layout_probe.face_to_dir`` with 0 mismatches, and reproduces 3/3 of Square
    Enix's own shipped arrival facings on real field 100.

    0 = south (faces the camera) / 64 = west / 128 = north (faces away) / 192 = east.

    ★ There is NO cardinal snap, deliberately. A snap is a strict no-op on axis-aligned walls and
    fires only where it introduces error: 8 bytes is 11.25deg of yaw, so an 11deg-tilted wall would
    get a cardinal arrival while its door quad stayed tilted -- breaking THE TWO-FRAME LAW's own
    pairing -- and two near-identical drawings (11.5deg vs 12.0deg) would land 9 bytes apart.
    Non-cardinal bytes are first-class in real FF9 (the engine hardcodes 4, 22, 117, 120, 126, 228,
    240 among others) and ``build.py:6319`` accepts any 0..255 with no cardinal gate. To get straight
    walls, snap the WALL SEGMENT in the plan frame BEFORE this runs, so the quad, the arrival offset
    and the byte stay mutually consistent. Never snap one derived artifact and not the others."""
    return round(math.atan2(-nx, -nz) / (2 * math.pi) * 256) % 256


# ------------------------------------------------------------------ C4: candidate shared walls

def shared_edges(A, B, *, tol=8.0, angle_tol_deg=2.0):
    """Candidate door segments on a wall two rooms share, longest first.

    OFFERS candidates only -- the author declares the door. THE DRAWN-MESH LAW holds: this computes
    geometry, it never infers a door.

    ★ ``abs(dot)``, not ``dot``. For two consistently-wound abutting rooms the shared edges are
    ANTIPARALLEL: measured, ``_signed_area(A) == _signed_area(B) == +1000000`` (both already CCW),
    A's edge on x=0 runs ``(0,-500)->(0,+500)`` while B's runs ``(0,+500)->(0,-500)``, so
    ``dot == -1.0``. A near-parallel test written the obvious way (``dot > 1 - eps``) therefore
    returns ZERO candidates on every plan -- a silent total failure with nothing to debug, because
    every individual formula still looks right.

    ★ ``angle_tol_deg`` is explicit because a distance-to-line tolerance alone admits a
    length-dependent angle error: at ``tol=8`` a 3000u edge rejects past 0.15deg while a 200u edge
    accepts ~2.3deg.

    ★ G12 is enforced here: the two rooms' inward normals must be ANTIPARALLEL. One line that
    catches same-side adjacency, a nested room, and any residual C2 inversion.

    ★ There is no ``min_len``. The draft's 192 (= 4 x 48) followed from neither its stated reason
    nor the real radius, and an unconditional length floor refuses a legal 100u door in the middle
    of a long wall. G9's standable-area test is the real gate."""
    cos_tol = math.cos(math.radians(angle_tol_deg))
    out = []
    for ea in edges(A):
        ua = _unit(_sub(ea[1], ea[0]))
        if ua == (0.0, 0.0):
            continue
        for eb in edges(B):
            ub = _unit(_sub(eb[1], eb[0]))
            if ub == (0.0, 0.0):
                continue
            if abs(ua[0] * ub[0] + ua[1] * ub[1]) < cos_tol:
                continue
            if max(dist_point_line(p, ea) for p in eb) > tol:
                continue
            if max(dist_point_line(p, eb) for p in ea) > tol:
                continue
            def t_of(p, _ea=ea, _ua=ua):
                return (p[0] - _ea[0][0]) * _ua[0] + (p[1] - _ea[0][1]) * _ua[1]
            lo = max(min(t_of(ea[0]), t_of(ea[1])), min(t_of(eb[0]), t_of(eb[1])))
            hi = min(max(t_of(ea[0]), t_of(ea[1])), max(t_of(eb[0]), t_of(eb[1])))
            if hi - lo <= 0:
                continue
            seg = (_add(ea[0], _scale(ua, lo)), _add(ea[0], _scale(ua, hi)))
            try:
                na, _ = interior_normal(A, seg)
                nb, _ = interior_normal(B, seg)
            except ComposeError:
                continue
            if na[0] * nb[0] + na[1] * nb[1] > -1 + 1e-6:
                continue                        # G12: same-side adjacency / nested / an inversion
            out.append({"seg": seg, "length": hi - lo})
    out.sort(key=lambda r: -r["length"])
    return out


# ------------------------------------------------------------------ C5: the door trigger strip

def door_strip(poly, seg, depth):
    """The gateway zone for one side of a door: a parallelogram from the wall, ``depth`` inward.

    ★ ``quad[0] -> quad[1]`` IS the door segment, and NO GATE CAN CHECK IT -- hence the assertion.
    Verified against the engine rather than the docstring: the exit region's body runs
    ``CalculateExitPosition`` (MJPOS 0xA4, Memoria EventEngine.DoEventCode.cs:2247), which reads
    ``q[0]`` and ``q[1]`` ONLY (:2251), projects the player onto THAT segment with the parameter
    clamped to [0,256] and stores it as ``sMapJumpX``/``sMapJumpZ``; ``ExitField`` then walks the
    player there (opcode 0xA0 WalkToExit). Measured on a west-wall strip with the player at
    (-1100,-850): this order gives an exit target on the wall line -- into the door; inner-edge-first
    gives (-970,-850), i.e. 130u BACKWARD into the room during the fade; rotated by one gives
    (-1101,-300), a 550u sideways slide along the jamb. All three score ``zone_fan_audit`` 0.0/0.0,
    so the fan judge is structurally blind to it, and nothing in the package validates the
    convention (only prose at content/gateway.py:11).

    A parallelogram is convex, so ``zone_fan_audit`` is ~0 by construction -- but only 2996/3000
    measured, worst spill 7.58e-4, which is why G7 is a tolerance and not equality.

    Corners are ROUNDED, not truncated: ``content/gateway.py:57`` packs each with ``int()``."""
    n, s = interior_normal(poly, seg)
    p, q = s
    quad = [p, q, _add(q, _scale(n, depth)), _add(p, _scale(n, depth))]
    quad = [(int(round(x)), int(round(z))) for x, z in quad]
    want = [(int(round(p[0])), int(round(p[1]))), (int(round(q[0])), int(round(q[1])))]
    if quad[0] != want[0] or quad[1] != want[1]:
        raise ComposeError("door_strip: quad[0]->quad[1] must be the door segment (the walk-out "
                           "edge) -- CalculateExitPosition reads only those two corners and walks "
                           "the player onto that line")
    return quad


def strip_standable_fraction(poly, quad, *, R=R_WALK, step=None):
    """``(fraction, points)`` -- how much of the strip the player CENTRE can occupy.

    ★ Each sample is tested DIRECTLY against the room (inside it, and >= R from its boundary) rather
    than looked up in :func:`standable`'s cell set. A cell-key join looks natural and is wrong: the
    two grids have different phases, so a strip sample 79u off the wall and a room sample 80u off
    the wall land in the SAME 8u cell, and a depth-79 door -- which has no standable area at all --
    reported as standable. Sampled at a quarter of the room grid so a thin band is not missed.

    ★ That quarter-step is why this is not a minor cost: a 1200x250 strip is ~75,000 samples, which
    is the same order as a whole 2400x1800 room, and a plan pays it TWICE per door. Rows are
    scanlined against the quad and the room the same way :func:`standable_map` does, and the
    room-distance loop exits at the first edge closer than ``R``. Same arithmetic, same samples,
    same counts -- ``tot`` and the returned points are pinned by the fences. The one deliberate
    change is that ``hit`` now comes out row-major rather than column-major; no caller reads its
    order (every one of them tests emptiness or the fraction), and the sweep asserts the SET."""
    if step is None:
        step = GRID_STEP / 4.0
    x0, z0, x1, z1 = bbox(quad)
    tot, hit = 0, []
    i0, i1 = int(math.floor(x0 / step)), int(math.ceil(x1 / step))
    j0, j1 = int(math.floor(z0 / step)), int(math.ceil(z1 / step))
    xs_grid = [(i + 0.5) * step for i in range(i0, i1 + 1)]
    ed = _edge_data(poly)
    for j in range(j0, j1 + 1):
        z = (j + 0.5) * step
        xs = _row_crossings(quad, z)
        if not xs:
            continue
        # The ROOM's crossings for this row, once -- `point_in_poly(x, z, poly)` per sample was a
        # million calls on a five-room plan, all of them re-walking the same edges at the same z.
        # An odd number of crossings strictly greater than x is exactly what that test computes.
        rxs = _row_crossings(poly, z)
        for k in range(0, len(xs) - 1, 2):
            lo, hi = xs[k], xs[k + 1]
            for gi in range(bisect_left(xs_grid, lo), len(xs_grid)):
                x = xs_grid[gi]
                if x >= hi:
                    break
                tot += 1
                if (len(rxs) - bisect_right(rxs, x)) % 2 == 0:
                    continue
                for (ax, az, dx, dz, L2) in ed:
                    t = 0.0 if L2 == 0 else max(
                        0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
                    if math.hypot(x - (ax + t * dx), z - (az + t * dz)) < R:
                        break
                else:
                    hit.append((x, z))
    return ((len(hit) / tot) if tot else 0.0), hit


# ------------------------------------------------------------------ C6: the arrival

def arrival_problem(pos, poly, zones, *, R=R_WALK):
    """None if ``pos`` is a legal arrival/spawn, else the reason (an ERROR-severity reason).

    ★ THE INVISIBLE-DOOR LESSON, adjudicated into two rules. The law
    (``.claude/skills/laying-out-ff9-fields/SKILL.md``) says a spawn must be clear of every zone's
    full x/z BAND, not merely outside the quads -- and no code in the repo implements EITHER version
    (``tools/field_layout_probe.py:246`` is an exact point-in-poly test inside an offline PNG tool
    no build path spends; ``build._validate_content_placement`` never compares a spawn against a
    trigger zone at all). The split:
      * ERROR (here): distance from the arrival to every trigger-zone POLYGON >= R. Geometric and
        robust, and it directly models "the wall clamp or the entry settle displaces me into the
        zone". A literal point-in-poly test would have MISSED the real Lantern Hall incident, where
        the spawn sat 10u OUTSIDE the sign zone in a corridor whose whole lateral width was walkable.
      * WARN, never error (:func:`band_warnings`): the axis-band version. It is the rule that would
        have caught that incident directly, but as an error it refuses Square Enix's own field-100
        layout -- entrance 231 sits 23u clear of zone 114's x-band, closer than the player's radius.
        A gate on values the composer MINTS may be stricter than Square; it may not assert Square
        is wrong."""
    if not point_in_poly(pos[0], pos[1], poly):
        return "off the walkmesh"
    d = dist_to_boundary(pos[0], pos[1], poly)
    if d < R:
        return (f"{d:.0f}u from the nearest wall; the engine clamps the player centre to {R:g}u "
                f"(RadiusValid + BGI_computeNewPoint), so it would be shoved {R - d:.0f}u")
    for z in zones:
        dz = dist_point_to_poly(pos, z["zone"])
        if dz < R:
            return (f"{dz:.0f}u from {z.get('label') or 'a trigger zone'} -- under the {R:g}u the "
                    f"player centre can be displaced, so it can warp on arrival")
    return None


def band_warnings(pos, zones, *, R=R_WALK, own=None):
    """WARN-severity axis-band findings for one arrival/spawn. See :func:`arrival_problem`.

    ``own`` is the zone this point is the arrival FOR, and it is skipped: an arrival sits directly
    inward from its own door, so it necessarily shares that door's perpendicular band. That is the
    design (the player walks straight back out the way they came), not a hazard -- warning on it
    would fire on every door in every dungeon and drown the finding that matters, which is an
    arrival standing one step from a DIFFERENT zone."""
    out = []
    for z in zones:
        if own is not None and z is own:
            continue
        x0, z0, x1, z1 = bbox(z["zone"])
        label = z.get("label") or "a trigger zone"
        gap_x = max(x0 - pos[0], pos[0] - x1, 0.0)
        gap_z = max(z0 - pos[1], pos[1] - z1, 0.0)
        if z0 - R <= pos[1] <= z1 + R and gap_x <= BAND_REACH:
            out.append(f"sits in {label}'s z-band (z {z0:.0f}..{z1:.0f}) only {gap_x:.0f}u to its "
                       f"side -- one sideways step could fire it")
        elif x0 - R <= pos[0] <= x1 + R and gap_z <= BAND_REACH:
            out.append(f"sits in {label}'s x-band (x {x0:.0f}..{x1:.0f}) only {gap_z:.0f}u in front "
                       f"of or behind it -- one step could fire it")
    return out


def arrival_for(poly, seg, zones, *, depth, inset=None, R=R_WALK):
    """``(pos, face)`` for an inbound door. ``face`` is never None -- see G10.

    Starts ``depth + 2*R`` inward from the door's midpoint along the inward normal and searches back
    toward ``depth + R``, taking the first point that clears :func:`arrival_problem`. Raises naming
    the shallowness rather than minting an off-mesh arrival."""
    n, s = interior_normal(poly, seg)
    m = midpoint(s)
    face = face_of_dir(*n)
    want = depth + 2 * R if inset is None else float(inset)
    d = want
    while d >= depth + R - 1e-9:
        pos = (int(round(m[0] + n[0] * d)), int(round(m[1] + n[1] * d)))
        if arrival_problem(pos, poly, zones, R=R) is None:
            return pos, face
        d -= GRID_STEP
    raise ComposeError(
        f"no arrival point between {depth + R:g}u and {want:g}u inward from this door clears the "
        f"walls and the trigger zones -- the room is too shallow for a {depth:g}u door. Reduce the "
        f"door depth or deepen the room.")


# ------------------------------------------------------------------ C7: the play camera + off_r

def fit_play_camera(poly, *, pitch=DEFAULT_PITCH, fov=DEFAULT_FOV, margin=FIT_MARGIN,
                    front_row=FRONT_ROW, notes=None, range_wh=None, window_width=None):
    """``(cam, off_r)`` -- a camera that frames this room, and the INTEGER plan->room translation.

    ★ THE DEPTH GATE IS THE WHOLE POINT. Apparent size goes as ``1/|D + cos(p)z|``, which has a
    POLE, so size GROWS with distance below it and the fits-flag transitions TWICE. A canvas-box
    test alone returns ``D = 200`` with a minimum vertex depth of -740 for a 400x2000 corridor at
    pitch 20 -- a camera 740u INSIDE the room, passing the margin test comfortably, because
    ``cam.py:166`` folds ``abs(resz)`` and mirrors the behind-camera half into ordinary-looking
    coordinates. In-game that renders the near floor mirrored through the camera plane: walkmesh
    inverted against the art, gateways firing on the wrong side, every key press moving the wrong
    way. So every vertex must clear ``NEAR_W``.

    ★ FRONT-ALIGN, not canvas-centre. Front-align won canvas fill in 10 of 10 measured room/pitch
    pairs and always leaves exactly 28 rows under the front edge; canvas-centring left 96-201. Worst
    measured case, a 4000x1200 room at pitch 26: the entire floor inside rows 205-247 -- 8.9% fill,
    205 dead rows above and 201 below, which with placeholder art reads in-game as a strip of ground
    floating over a void. (The draft's canvas-centre step was also a TAUTOLOGY: ``to_canvas`` is
    ``range[1]/2 + centerOffset[1] - rawProj.y`` and ``rawProj.y = 0`` at ``z = 0``, so solving for
    the middle row returns 0 identically at every pitch and distance.)

    ★ THE AABB CENTRE, not the centroid. For an L-shape they differ by (-250,-200), and at the same
    distance the centroid version pushes a corner to canvas x 399.8 -- off a 384-wide canvas. The
    fit criterion is a bounding-box test, so the AABB centre is the value that balances the margins.
    Every convex or symmetric fixture gives a zero delta, so a rectangle test cannot tell them apart.

    ★ ``guide.make_camera`` VALIDATES NOTHING -- ``distance = -3000`` and ``1.0`` both return a
    plausible-looking projection of the origin, and ``0`` raises ZeroDivisionError from inside
    ``cam.project``. THE DEFAULT-VALUE LAW gets no help from that call site; the bound lives here.

    ★ ``range_wh`` paints WIDER THAN THE SCREEN, which is how a scrolling field buys back apparent
    size: the fit's canvas-box test gets more room in x, so the same polygon fits at a much shorter
    distance. ``window_width`` is then the VISIBLE screen width, and the focal length is measured at
    THAT rather than at the painting -- otherwise a 768-wide painting would simply double the FOV
    and buy nothing. This mirrors ``build._resolve_one_camera`` exactly (``build.py:3656-3658``), so
    the camera fitted here is the camera the build emits.

    ⚠ SCROLL IS A COMPOSE-TIME DECISION, NOT A TOML EDIT. The range changes the fitted distance,
    which changes ``off_r``, which is the translation every vert, door quad, arrival and spawn
    rides. Bolting a wider range onto an already-composed room re-poses the camera under a walkmesh
    that was solved for the old one. Fit and emit together, always."""
    # ★ The HARD boundary is `p*` itself -- the pitch at which the horizon reaches canvas row 0.
    # Below it part of the frame has no floor at all. PITCH_SLACK is a comfort margin above that,
    # and it is a WARNING, not a refusal, deliberately: `imagefield.DEFAULT_PITCH` is 26.0 and
    # `p*` is 25.73 at fov 42.2, so an error at `p* + 1` would refuse the trace lane's own default
    # pitch. The second hazard `p*` was meant to cover -- a behind-camera vertex faking a canvas
    # fit -- is caught directly and independently by the per-vertex depth gate below, so the pitch
    # gate does not have to be the one carrying it.
    # ★ The GATE ITSELF reads off `cam.horizon_canvas_y`, not `pitch_floor`'s own atan formula --
    # "the horizon lands inside the canvas" IS `horizon_canvas_y(cam) >= 0`, the direct statement of
    # the rule `pitch_floor` states analytically, and unlike that formula it honours a nonzero
    # centerOffset (`pitch_floor` assumes the canvas centre is `range_h/2`). Composer cameras are
    # always `guide.make_camera`-built (centerOffset [0,0]), so this is a like-for-like swap, not a
    # behaviour change; `pitch_floor` stays, to print `p*` itself in the message below. A horizon
    # does not depend on camera distance (it drops out of `cam._row_coeffs`), so any positive probe
    # distance does.
    rng = (int(CANVAS_W), int(CANVAS_H)) if range_wh is None else (int(range_wh[0]),
                                                                   int(range_wh[1]))
    win_w = int(window_width or CANVAS_W)
    proj = _guide.proj_from_fov_x(fov, win_w)   # the SCREEN's focal length, not the painting's

    pstar = pitch_floor(fov)
    row = _cam.horizon_canvas_y(_guide.make_camera(pitch, 1.0, proj=proj, range_wh=rng))
    if row >= 0:
        raise ComposeError(
            f"pitch {pitch:g} deg is at or under the horizon floor {pstar:.2f} deg for fov {fov:g}: "
            f"the horizon lands INSIDE the canvas (row {row:.0f}), so part of every frame has no "
            f"floor at all. Use more than {math.ceil(pstar)} deg (the kit scaffold's "
            f"{DEFAULT_PITCH:g} is safe by {DEFAULT_PITCH - pstar:.0f} deg).")
    if pitch < pstar + PITCH_SLACK and notes is not None:
        notes.append(f"pitch {pitch:g} deg leaves the horizon only {-row:.0f} row(s) above the "
                     f"canvas (the floor for fov {fov:g} is {pstar:.2f} deg) -- the back of the "
                     f"room will foreshorten hard")

    x0, z0, x1, z1 = bbox(poly)
    off_x = -(x0 + x1) / 2.0                    # THE AABB CENTRE

    def attempt(D):
        c = _guide.make_camera(pitch, D, proj=proj, range_wh=rng)
        zf = _cam.solve_z_for_canvasY(c, front_row, near=NEAR_W, zlo=None, zhi=None)
        if zf is None:
            return None
        off = (off_x, zf - z0)                  # FRONT-ALIGN: the room's front edge on `front_row`
        for (x, z) in poly:
            cx, cy, dep = project_floor(x + off[0], z + off[1], c)
            if dep < NEAR_W:
                return None
            if not (margin <= cx <= c.range[0] - margin and margin <= cy <= c.range[1] - margin):
                return None
        return (c, off)

    lo, hi, best = 300.0, 60000.0, None
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        r = attempt(mid)
        if r is not None:
            best, hi = (mid,) + r, mid
        else:
            lo = mid
        if hi - lo < 0.5:
            break
    if best is None:
        raise ComposeError(
            f"no camera distance in [300, 60000] frames this room at pitch {pitch:g} / fov {fov:g} "
            f"(footprint {x1 - x0:.0f} x {z1 - z0:.0f} world units). Split the room, or raise the fov.")
    D, c, off = best
    return c, (int(round(off[0])), int(round(off[1])))


# ------------------------------------------------------------------ C8: siting a point well inside

def interior_point(poly, avoid, *, R=R_WALK, step=GRID_STEP, cache=None):
    """The spawn / save-point site: the standable cell furthest from any wall that also clears every
    ``avoid`` zone by ``R``.

    ★ There is deliberately no "centroid first" fast path. For a plain L-shaped room the
    VERTEX-AVERAGE centroid -- the idiom ``build.py`` already uses for zone centres at :3734, :3742
    and :5960 -- lands exactly ON the reflex corner and tests OUTSIDE the polygon; the area
    (shoelace) centroid is inside. For a U/horseshoe room BOTH fall outside. An L is the normal case
    for a hand-drawn plan (a plain rectangle needs no composer), so the grid search is the
    load-bearing implementation, not a rare fallback.

    ★ THE RANKING DISTANCE IS MEASURED HERE, AT THE CELL CENTRE -- deliberately, and NOT reused
    from :func:`standable_map`. Those are two different points: the map's distance is measured at
    the grid SAMPLE that decided the cell was standable (``x0 + k*step`` walked from the polygon's
    own bbox), while the cell CENTRE is ``(i + 0.5) * step`` on the absolute grid. Reusing the
    map's number therefore re-ranks the search, and it is not academic -- measured over 400 random
    plans it moved the spawn one whole cell on 4 of the 22 that composed. The cheap-looking reuse
    is a behaviour change wearing an optimization's clothes.

    ``cache`` (a :class:`GeomCache`) is still worth passing: it makes the grid WALK a hit when this
    room is unchanged since the last compose, which is what the tab's live gate spends."""
    x0, z0, x1, z1 = bbox(poly)
    cx, cz = (x0 + x1) / 2.0, (z0 + z1) / 2.0
    best = None
    ed = _edge_data(poly)                    # hoisted: the per-cell loop below re-derived it ~58k
    # Each avoid zone gets its edges hoisted too, plus its own bbox GROWN BY R. A cell outside that
    # grown box is farther than R from the zone along one axis alone, so it cannot possibly be
    # within R of the polygon -- four comparisons stand in for a point-in-poly plus four hypots.
    # This is where the time was: a door strip is tiny and a room is not, so the overwhelming
    # majority of cells are nowhere near any zone and were paying full price to find that out.
    avoid_pre = []
    for a in avoid:
        bx0, bz0, bx1, bz1 = bbox(a)
        avoid_pre.append((bx0 - R, bz0 - R, bx1 + R, bz1 + R, a, _edge_data(a)))
    cells = (cache._map(poly, R, step) if cache is not None
             else standable_map(poly, R=R, step=step))
    for (i, j) in sorted(cells):
        x, z = (i + 0.5) * step, (j + 0.5) * step
        blocked = False
        for (bx0, bz0, bx1, bz1, a, aed) in avoid_pre:
            if x < bx0 or x > bx1 or z < bz0 or z > bz1:
                continue
            # literally `dist_point_to_poly(pt, a) < R`, with the edges pre-built
            if (0.0 if point_in_poly(x, z, a) else _min_dist_to_edges(x, z, aed)) < R:
                blocked = True
                break
        if blocked:
            continue
        d = _min_dist_to_edges(x, z, ed)
        # tie-break toward the AABB centre: on a rectangle hundreds of cells tie at the maximum,
        # and "whichever the scan saw first" puts the spawn visibly off-centre for no reason.
        key = (round(d, 3), -math.hypot(x - cx, z - cz))
        if best is None or key > best[0]:
            best = (key, (int(round(x)), int(round(z))))
    if best is None:
        raise ComposeError(f"no point in this room is {R:g}u clear of every wall AND every trigger "
                           f"zone -- the room is too small or too full of doors")
    return best[1]


# ------------------------------------------------------------------ id pre-flight

def preflight_ids(count, *, id_base, taken=()):
    """The first run of ``count`` CONSECUTIVE free field ids at or above ``id_base``.

    Consecutive on purpose: ``campaign.add_field``'s allocator is ``max(existing)+1``, so a
    non-contiguous set cannot be expressed through the manifest writer -- and one id block is what a
    dungeon wants anyway.

    ★ Nothing in the kit composes this, and each obvious candidate fails differently:
      * ``pack.suggest_ids(30500, 3)`` RAISES -- it caps at ``CUSTOM_ID_MAX = 9899`` (pack.py:20)
        while the scratch band, and this lane's own ``.ff9deploy.toml`` pin, is 30500.
      * ``pack.check_custom_id(9005)`` returns 9005 -- it bounds only [4000, 32767] and has NO
        carve-out for the 9000-9012 engine world-map hole, where a FieldScene clobbers a world
        script in the GLOBAL EventDB.
      * ``deploystack.check_id_collisions`` deliberately EXCLUDES the target folder (deploystack.py:558)
        so a redeploy of an id you already own is not flagged against you -- the opposite of what a
        fresh mint needs. Pass ``taken`` from ``deploylog.registrations(game)[0]`` (note: that
        returns a TUPLE) so the target folder IS included."""
    taken = set(taken)
    cand = int(id_base)
    while True:
        if not (ID_MIN <= cand <= ID_MAX):
            raise ComposeError(
                f"ran out of band at {cand}: custom field ids are {ID_MIN}-{ID_MAX} (fldMapNo is "
                f"Int16, so a higher id registers but is unreachable)")
        run = list(range(cand, cand + count))
        bad = next((i for i in run if i in taken or WORLD_LO <= i <= WORLD_HI or i > ID_MAX), None)
        if bad is None:
            return run
        cand = (WORLD_HI + 1) if WORLD_LO <= bad <= WORLD_HI else bad + 1


# ------------------------------------------------------------------ the composed result

@dataclass
class ComposedRoom:
    name: str
    field_id: int
    poly_plan: list
    poly_room: list
    off_r: tuple
    camera: object
    pitch: float
    fov: float
    distance: float
    toml: dict
    verts: list
    faces: list
    warnings: list = _dc_field(default_factory=list)


@dataclass
class Composed:
    name: str
    mod_folder: str
    rooms: list
    entry: str
    edges: list
    warnings: list = _dc_field(default_factory=list)

    def by_name(self, name):
        return next(r for r in self.rooms if r.name == name)


# ------------------------------------------------------------------ compose

def _room_defaults(r):
    return (float(r.get("pitch") or DEFAULT_PITCH), float(r.get("fov") or DEFAULT_FOV))


def _door_key(d):
    return (d["a"], d["b"], tuple(map(tuple, d["seg"])))


def _camera_toml(cam, pitch, fov, range_wh, scrolling):
    """The room's ``[camera]`` table. A static room emits exactly what it always did.

    A scrolling room adds ``range`` (the painting), ``window_width`` (the visible screen, which is
    what the focal length is measured at -- ``build.py:3656``) and ``[camera.scroll] enabled``,
    which is what makes the build auto-derive the pan Viewport from ``cam.scroll_bounds`` and inject
    the engine's ``EnableCameraServices``."""
    t = {"entry_settle": "auto", "pitch": pitch,
         "distance": int(round(-_cam.decompose(cam)["C"][2] / math.cos(math.radians(pitch)))),
         "fov": fov}
    if scrolling:
        t["range"] = [int(range_wh[0]), int(range_wh[1])]
        t["window_width"] = int(CANVAS_W)
        t["scroll"] = {"enabled": True}
    return t


def fit_room_camera(poly, *, pitch=DEFAULT_PITCH, fov=DEFAULT_FOV, notes=None,
                    cap=SCROLL_RANGE_CAP):
    """``(cam, off_r, range_wh, scrolling)`` -- the narrowest painting that renders this room
    legibly, scrolling only if the screen-sized one cannot.

    ★ STATIC FIRST, ALWAYS. A 384x448 field is what FF9 ships for most rooms and what every other
    part of this kit assumes; widening is a cost (a bigger painting for the human to paint, an
    engine path with less proof behind it) paid only when the static fit is not legible. Measured:
    a normal 2400x1500 room fits static at 10.7 char-px and never widens.

    ★ THE STEP IS THE SCREEN WIDTH and the cap is FF9's own widest shipped painting. Beyond the cap
    the answer is not a wider camera, it is TWO ROOMS -- which is what FF9 itself does with a large
    space (48 zones, median 11 fields each) and what this composer already builds, with gateways
    proven in-game. So the cap is where the legibility gate takes over and says "split".

    ⚠ Everything downstream rides ``off_r``, which the range changes -- see
    :func:`fit_play_camera`. This is the ONE place a room's range may be decided."""
    best = None
    w = int(CANVAS_W)
    while True:
        cam, off = fit_play_camera(poly, pitch=pitch, fov=fov, notes=notes,
                                   range_wh=(w, int(CANVAS_H)),
                                   window_width=int(CANVAS_W))
        best = (cam, off, (w, int(CANVAS_H)), w > int(CANVAS_W))
        if character_scale_px(cam) >= CHAR_PX_WARN or w >= cap:
            return best
        w = min(int(cap), w + int(CANVAS_W))


def character_scale_px(cam):
    """How many canvas px an :data:`R_OBJ`-wide character covers under ``cam``.

    ★ THE FORMULA IS THE CENSUS'S, DELIBERATELY. ``R_OBJ * proj * sin(pitch) / |cam_y|`` is exactly
    what ``studies/click-authoring/camera_census.py`` measured across all 741 real FF9 cameras, so
    the number this returns is directly comparable to :data:`CHAR_PX_WARN` / :data:`CHAR_PX_REFUSE`
    below. Re-deriving it a second way here would produce a number that LOOKS like the thresholds
    and is not on their scale, which is the subtlest way to build a gate that reads wrong."""
    d = _cam.decompose(cam)
    cam_y = abs(d["C"][1])
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, d.get("pitch_sin", 0.0))))) \
        if "pitch_sin" in d else None
    if pitch is None:                      # derive it the same way the census did, from the matrix
        pitch = math.degrees(math.atan2(abs(d["C"][1]), abs(d["C"][2]))) if d["C"][2] else 90.0
    return R_OBJ * cam.proj * math.sin(math.radians(pitch)) / max(cam_y, 1e-6)


def legibility_problem(name, cam, poly):
    """``(severity, message)`` when this room's fitted camera renders the character too small,
    else ``(None, None)``. ``severity`` is ``"error"`` or ``"warn"``.

    ★ THE DEFAULT-VALUE LAW ON A VALUE THE COMPOSER MINTS UNBOUNDED. ``fit_play_camera`` refuses
    only past distance 60000; below that it returns a camera that always looks plausible. A
    2200x9762 room drawn east-west fits at distance 18226 and renders the character at **3.3px** --
    below the 5th percentile of every camera Square shipped (p05 3.9 / p25 7.4 / median 9.3, n=217
    at pitch >= 26). The author built exactly that room, deployed it, and found a sliver.

    ★ AND THE REMEDY IS NAMED, because the useful thing to know is that WIDTH is the expensive axis:
    `fit_play_camera` fits the AABB, so the SAME corridor costs distance 6567 drawn north-south and
    18226 drawn east-west. Rotating the drawing is free and is the single largest lever.

    ⚠ WHAT THIS GATE DOES **NOT** JUDGE. :func:`character_scale_px` is a property of the CAMERA --
    it is the census's own per-camera measure, which is exactly what makes it comparable to the
    percentiles. It is NOT the apparent size at the worst point in the room. A very DEEP room can
    therefore pass this gate while its far edge still foreshortens hard, because apparent size goes
    as ``1/(D + cos(p)z)`` and no painting width changes that -- scroll pans a viewport across a
    FIXED camera, so it buys width and not depth. Catching the far-edge case would need a
    per-point baseline the census does not carry (its rows have no room geometry), so it is
    deliberately out of scope here rather than approximated. For a deep room the remedy the message
    already names -- split it -- is the real one."""
    px = character_scale_px(cam)
    if px >= CHAR_PX_WARN:
        return (None, None)
    x0, z0, x1, z1 = bbox(poly)
    w, h = x1 - x0, z1 - z0
    # ★ THE ROTATION REMEDY IS TESTED, NOT ASSUMED. "Width is the expensive axis" is true and it is
    # the first thing worth trying -- but on a room that is simply too big it is useless advice: a
    # 20000x2200 hall rotated is a 2200x20000 hall, equally unrenderable, and a fence caught the
    # message confidently recommending exactly that. So actually fit the rotated room and only
    # offer it if it would genuinely land legibly. Never name a remedy without checking it works.
    rot_px = None
    if w > h * 1.3:
        try:
            rcam, _o, _r, _s = fit_room_camera([(z, x) for x, z in poly])
            rot_px = character_scale_px(rcam)
        except ComposeError:
            rot_px = None
    split = (f"split it into two rooms joined by a door, which is what FF9 itself does with a large "
             f"space (48 zones, median 11 fields each) and what this composer already builds")
    if rot_px is not None and rot_px >= CHAR_PX_WARN:
        hint = (f"the room is {w:.0f}u wide by {h:.0f}u deep and WIDTH is the expensive axis -- "
                f"drawn the other way round it renders at {rot_px:.1f}px, which is fine, and "
                f"rotating the drawing costs nothing")
    elif rot_px is not None and rot_px >= CHAR_PX_REFUSE and rot_px > px * 1.5:
        # Rotating is a real improvement but does not get all the way there: say both, in order.
        hint = (f"the room is {w:.0f}u wide by {h:.0f}u deep and WIDTH is the expensive axis -- "
                f"drawn the other way round it reaches {rot_px:.1f}px, which is a big improvement "
                f"but still under {CHAR_PX_WARN:g}. To get it fully right, {split}")
    else:
        hint = (f"the room is {w:.0f}u by {h:.0f}u -- {split}"
                + (f"; rotating it would only reach {rot_px:.1f}px" if rot_px is not None else ""))
    if px < CHAR_PX_REFUSE:
        return ("error",
                f"room {name}: at the fitted camera a character is only {px:.1f} canvas px across "
                f"-- smaller than ANY of the 741 cameras FF9 ships (5th percentile is "
                f"{CHAR_PX_REFUSE:g}px, median {CHAR_PX_MEDIAN:g}). It would render as a sliver. "
                f"{hint}.")
    return ("warn",
            f"room {name}: a character is {px:.1f} canvas px across, under FF9's 25th percentile of "
            f"{CHAR_PX_WARN:g}px (median {CHAR_PX_MEDIAN:g}) -- it will read as distant. {hint}")


def _placeholder_layers(poly, cam):
    """The two placeholder layers, at depths derived from THIS room rather than assumed.

    ★ THE DEPTHS ARE NOT CONSTANTS AND CANNOT BE. FF9 sorts by OT depth with SMALLER IN FRONT, and
    the player's depth is computed from wherever they are standing -- so a floor pinned at a fixed
    z is only behind the player while the room is shallow enough to keep every standing position
    under it. The shipped literals were 3000 (floor) and 4000 (backdrop), which hold for a room a
    few thousand units deep and fail completely for a long one: measured on a 9762u room at camera
    distance 17676, the player's depth runs **3746..4125**, i.e. past BOTH -- so over the far half
    of the room the floor, and then the backdrop, drew ON TOP OF THE PLAYER. The author found it by
    building a deliberately long room and walking to the end of it.

    So: take the room's own depth range, put the floor behind its far edge and the backdrop behind
    that. ``_LAYER_GAP`` is slack for the entry settle and for content sited a little past the
    walkmesh; the values are ints because the layer table packs them as such."""
    ds = [_cam.depth((float(x), 0.0, float(z)), cam) for x, z in poly]
    floor_z = int(math.ceil(max(ds) + _LAYER_GAP))
    return [{"image": "art/back.png", "z": floor_z + _LAYER_GAP},
            {"image": "art/floor.png", "z": floor_z}]


def compose(plan, *, taken_ids=(), cache=None, cancel=None):
    """A floorplan dict -> a :class:`Composed` dungeon. Pure: no disk, no Qt, no game install.

    ``plan`` is the ``floorplan.json`` shape::

        {"name": str, "mod_folder": str, "id_base": int,
         "rooms": [{"name","poly":[[x,z],..],"pitch"?,"fov"?,"encounter"?,"savepoint"?,"id"?}],
         "doors": [{"a","b","seg":[[x,z],[x,z]],"depth"?,"two_way"?}],
         "entry"?: room name}

    Every gate is a compose-time ERROR unless the docstring says WARN. THE DEFAULT-VALUE LAW: a
    minted value is real, or loudly refused. Problems are collected per stage and raised together,
    so the author sees every fixable thing at once.

    ``cache`` is a :class:`GeomCache` to reuse across calls -- pass one from a live editor so the
    rooms a gesture did not touch are not re-walked. Omitted, a private one is still made, because
    even a single compose asks for the same room's grid more than once.

    ``cancel`` is a zero-arg predicate polled once per room and once per door; when it goes true
    this raises :class:`ComposeCancelled`. The live gate uses it so a superseded judge stops
    burning a core instead of running to completion to have its answer thrown away."""
    cache = GeomCache() if cache is None else cache
    with cache.scope():                  # full cell maps live for THIS compose and no longer
        return _compose(plan, taken_ids=taken_ids, cache=cache, cancel=cancel)


def _compose(plan, *, taken_ids, cache, cancel):
    """:func:`compose`'s body. Split out only so the transient-map scope can wrap it without
    indenting three hundred lines; everything worth knowing is in :func:`compose`'s docstring."""

    def _check():
        if cancel is not None and cancel():
            raise ComposeCancelled()

    name = str(plan.get("name") or "DUNGEON")
    mod_folder = str(plan.get("mod_folder") or "FF9CustomMap")
    rooms_in = list(plan.get("rooms") or [])
    doors_in = list(plan.get("doors") or [])
    if not rooms_in:
        raise ComposeError("the floorplan has no rooms")

    warnings = []

    # ---- stage 1: room health (G1, G11, G13) -----------------------------------------------------
    problems = []
    seen = set()
    for r in rooms_in:
        _check()
        rn = str(r.get("name") or "").strip()
        if not rn:
            problems.append("a room has no name")
            continue
        if rn in seen:
            problems.append(f"two rooms are both named {rn!r}")
        seen.add(rn)
        poly = [(float(x), float(z)) for x, z in (r.get("poly") or [])]
        why = polygon_problem(poly)
        if why:
            problems.append(f"room {rn}: {why}")                                    # G1
            continue
        n_cells, n_comps, largest = cache.room_stats(poly)                          # G13
        if not n_cells:
            problems.append(f"room {rn}: nowhere in it is {R_WALK:g}u clear of a wall -- the player "
                            f"centre could not stand anywhere. It needs to be at least "
                            f"{2 * R_WALK:g}u across.")
            continue
        if n_comps > 1:
            problems.append(f"room {rn}: its walkable area is {n_comps} disconnected pieces "
                            f"(the largest is {largest} cells of {n_cells}) -- a neck "
                            f"narrower than {2 * R_WALK:g}u splits it and the player cannot cross")
            continue
        ratio = n_cells * GRID_STEP * GRID_STEP / max(abs(_if._signed_area(poly)), 1.0)
        if ratio < STANDABLE_WARN:
            warnings.append(f"room {rn}: only {ratio * 100:.0f}% of its floor is standable (the "
                            f"player centre stops {R_WALK:g}u off every wall) -- it may feel like a "
                            f"corridor")
    for i, ra in enumerate(rooms_in):                                               # G11
        for rb in rooms_in[i + 1:]:
            pa = [(float(x), float(z)) for x, z in (ra.get("poly") or [])]
            pb = [(float(x), float(z)) for x, z in (rb.get("poly") or [])]
            if len(pa) >= 3 and len(pb) >= 3 and polys_overlap(pa, pb):
                problems.append(f"rooms {ra.get('name')} and {rb.get('name')} overlap -- they share "
                                f"floor area. Rooms may ABUT along a wall but never overlap.")
    if problems:
        raise ComposeError(*problems)

    polys = {str(r["name"]): [(float(x), float(z)) for x, z in r["poly"]] for r in rooms_in}
    order = [str(r["name"]) for r in rooms_in]
    entry = str(plan.get("entry") or order[0])
    if entry not in polys:
        raise ComposeError(f"entry room {entry!r} is not in the floorplan")

    # ---- stage 2: ids (G5) -----------------------------------------------------------------------
    fixed = {str(r["name"]): int(r["id"]) for r in rooms_in if r.get("id")}
    if len(fixed) == len(order):
        ids = dict(fixed)
        dup = [i for i in set(ids.values()) if list(ids.values()).count(i) > 1]
        if dup:
            raise ComposeError(f"two rooms share field id {dup[0]} -- EventDB and SceneData are "
                               f"GLOBAL dicts, so a collision is the classic null-.eb black screen")
        bad = [f"{n} (id {i})" for n, i in ids.items()
               if not (ID_MIN <= i <= ID_MAX) or WORLD_LO <= i <= WORLD_HI]
        if bad:
            raise ComposeError(f"field ids out of the usable band: {', '.join(bad)} -- "
                               f"{ID_MIN}-{ID_MAX} minus the reserved engine world-map hole "
                               f"{WORLD_LO}-{WORLD_HI}")
        clash = [f"{n} (id {i})" for n, i in ids.items() if i in set(taken_ids)]
        if clash:
            raise ComposeError(f"already registered in the live game: {', '.join(clash)} -- pick "
                               f"another id run or revert the existing deploy")
    else:
        run = preflight_ids(len(order), id_base=int(plan.get("id_base") or 30000),
                            taken=taken_ids)
        ids = dict(zip(order, run))
        if fixed:
            warnings.append(f"ignored {len(fixed)} hand-set room id(s): ids are allocated as one "
                            f"consecutive run, so either every room pins its id or none does")

    # ---- stage 3: doors -> strips (G9, G12 via shared_edges, G14 in door_strip) -------------------
    problems = []
    strips = {n: [] for n in order}          # room -> [{zone,label,door,role}]
    doors = []
    for k, d in enumerate(doors_in):
        _check()
        a, b = str(d.get("a") or ""), str(d.get("b") or "")
        if a not in polys or b not in polys:
            problems.append(f"door {k}: names an unknown room ({a!r} -> {b!r})")
            continue
        if a == b:
            problems.append(f"door {k}: {a} to itself -- a self-loop is not a composed door")
            continue
        seg = tuple((float(x), float(z)) for x, z in (d.get("seg") or ()))
        if len(seg) != 2:
            problems.append(f"door {k}: needs exactly 2 segment endpoints, got {len(seg)}")
            continue
        depth = float(d.get("depth") or DEPTH_DEFAULT)
        if depth < DEPTH_MIN:                                                       # G9
            problems.append(
                f"door {a}-{b}: depth {depth:g}u leaves a standable window only "
                f"{max(depth - R_WALK, 0):g}u wide -- the player centre is clamped {R_WALK:g}u off "
                f"the wall, so the strip would be drawn and (near-)never fire. Use at least "
                f"{DEPTH_MIN:g}u; {DEPTH_DEFAULT:g} is the default and {DEPTH_WARN:g} is the "
                f"in-game-proven floor.")
            continue
        if depth < DEPTH_WARN:
            warnings.append(f"door {a}-{b}: depth {depth:g}u is under the {DEPTH_WARN:g}u "
                            f"in-game-proven floor -- shallow strips are easy to skirt")
        two_way = bool(d.get("two_way", True))
        rec = {"a": a, "b": b, "seg": seg, "depth": depth, "two_way": two_way, "k": k}
        try:
            na, _ = interior_normal(polys[a], seg)
            nb, _ = interior_normal(polys[b], seg)
        except ComposeError as e:
            problems.append(f"door {a}-{b}: {e}")
            continue
        if na[0] * nb[0] + na[1] * nb[1] > -1 + 1e-6:                               # G12
            problems.append(f"door {a}-{b}: the two rooms' inward normals are not opposite, so that "
                            f"segment is not a wall BETWEEN them (same-side adjacency, or one room "
                            f"is inside the other)")
            continue
        ok = True
        for who, other in ((a, b), (b, a)):
            if who == b and not two_way:
                continue                     # a one-way door has no strip on the destination side
            try:
                quad = door_strip(polys[who], seg, depth)
            except ComposeError as e:
                problems.append(f"door {a}-{b} on {who}'s side: {e}")
                ok = False
                continue
            # G9's geometric half: the depth check above covers a straight wall analytically, but a
            # room that pinches near THIS wall (a bevel, a notch, a corner) can still leave the
            # strip unreachable. There is deliberately no "connected to the room's main component"
            # check on top: G13 already refuses any room whose standable set is disconnected, so
            # after it there is exactly one component and such a test could never fire.
            frac, any_standable = cache.strip_standable(polys[who], quad)           # G9
            if not any_standable:
                problems.append(
                    f"door {a}-{b} on {who}'s side: no part of the {depth:g}u strip is standable -- "
                    f"the room pinches to under {R_WALK:g}u of clearance at that wall, so the strip "
                    f"lies entirely inside the shell the player centre can never enter. Widen the "
                    f"room there, or move the door.")
                ok = False
                continue
            audit, n_tris = cache.fan(quad)                                         # G7
            if max(audit["gap"], audit["spill"]) > FAN_TOL:
                problems.append(
                    f"door {a}-{b} on {who}'s side: the engine's IsInQuad fan disagrees with the "
                    f"drawn outline by gap {audit['gap']:.3f} / spill {audit['spill']:.3f} "
                    f"(tolerance {FAN_TOL})")
                ok = False
                continue
            if n_tris < 2:                                                          # G9 degeneracy
                problems.append(f"door {a}-{b} on {who}'s side: the quad is degenerate "
                                f"({n_tris} triangles). Note the fan audit "
                                f"scores a perfect 0/0 on a degenerate quad, so it is not the "
                                f"backstop for this.")
                ok = False
                continue
            strips[who].append({"zone": quad, "label": f"the {other} door", "door": rec,
                                "target": other, "standable": frac})
        if ok:
            doors.append(rec)
    if problems:
        raise ComposeError(*problems)

    # ---- stage 4: entrance numbering + arrivals (G2 error / band WARN, G3, G10) -------------------
    inbound = {n: [] for n in order}
    for d in doors:
        inbound[d["b"]].append((d["a"], d))
        if d["two_way"]:
            inbound[d["a"]].append((d["b"], d))
    entrance = {}                                   # (room, door key) -> entrance int
    for n in order:
        rows = sorted(inbound[n], key=lambda t: (t[0], midpoint(t[1]["seg"])))
        for i, (_src, d) in enumerate(rows, start=1):
            entrance[(n, _door_key(d))] = i

    problems = []
    arrivals = {n: [] for n in order}
    spawns, saves = {}, {}
    for n in order:
        _check()
        zones = strips[n]
        quads = [z["zone"] for z in zones]
        try:
            spawn = cache.interior_point(polys[n], quads)
        except ComposeError as e:
            problems.append(f"room {n}: {e}")
            continue
        spawns[n] = spawn
        for w in band_warnings(spawn, zones):                                       # WARN, not error
            warnings.append(f"room {n}, the spawn {w}")
        # `savepoint` may be a dict of options, or bare true for "yes, all defaults". An EMPTY dict
        # is a legitimate "yes" -- testing it for truthiness silently drops the request, which is
        # exactly the quietly-wrong-default class THE DEFAULT-VALUE LAW exists to refuse.
        raw_sp = next((r.get("savepoint") for r in rooms_in if str(r["name"]) == n), None)
        if raw_sp is not None and raw_sp is not False:
            if isinstance(raw_sp, dict):
                sp = dict(raw_sp)
            elif raw_sp is True:
                sp = {}
            else:
                problems.append(f"room {n}: savepoint must be true or a table of options, not "
                                f"{type(raw_sp).__name__}")
                sp = None
        else:
            sp = None
        if sp is not None:
            half = float(sp.get("half") or 120.0)
            # The save point must clear the spawn too, or it lands on the exact cell the spawn took
            # (both maximize distance-to-wall against the same avoid set). The exclusion box is
            # `half` -- the press zone's own reach -- so that the resulting PRESS ZONE, not merely
            # its centre, ends up >= R_WALK from the spawn. An R_WALK-sized box is not enough: the
            # zone then extends `half` back toward the spawn and lands inside its clearance.
            spawn_box = [(spawn[0] - half, spawn[1] - half), (spawn[0] + half, spawn[1] - half),
                         (spawn[0] + half, spawn[1] + half), (spawn[0] - half, spawn[1] + half)]
            try:
                site = cache.interior_point(polys[n], quads + [spawn_box])
                press = [(site[0] - half, site[1] - half), (site[0] + half, site[1] - half),
                         (site[0] + half, site[1] + half), (site[0] - half, site[1] + half)]
                if dist_point_to_poly(spawn, press) < R_WALK:      # enforced, not assumed
                    problems.append(f"room {n}: the save point's press zone lands "
                                    f"{dist_point_to_poly(spawn, press):.0f}u from the spawn "
                                    f"(under {R_WALK:g}u) -- the player would save on arrival")
                else:
                    saves[n] = {"site": site, "half": half, "press": press}
            except ComposeError as e:
                problems.append(f"room {n}: the save point cannot be sited clear of the doors and "
                                f"the spawn -- {e}")
        for src, d in sorted(inbound[n], key=lambda t: (t[0], midpoint(t[1]["seg"]))):
            own = next((z for z in zones if z["door"] is d), None)
            try:
                pos, face = arrival_for(polys[n], d["seg"], zones, depth=d["depth"])
            except ComposeError as e:
                problems.append(f"room {n}, arriving from {src}: {e}")
                continue
            for w in band_warnings(pos, zones, own=own):                            # WARN, not error
                warnings.append(f"room {n}, the {src} arrival {w}")
            arrivals[n].append({"entrance": entrance[(n, _door_key(d))],
                                "pos": list(pos), "face": int(face), "from": src})
    if problems:
        raise ComposeError(*problems)

    # ★ [player] face is 0 = SOUTH, and that is a real choice rather than a shrug: it is the engine's
    # own unconditional template default (the player Init writes D9(6) = 0 ahead of every arrival
    # if-block), so the composer agrees with the fallback instead of fighting it, and 0 = facing the
    # camera is the layout skill's stated idiom for a standing actor. Unlike a door arrival there is
    # no wall to derive a direction from -- deriving it from "whichever inbound door sorted first"
    # would make a room's idle facing depend on room naming.
    SPAWN_FACE = 0
    spawn_face = {n: SPAWN_FACE for n in order}
    # ★ The explicit entrance-0 row goes on the ENTRY room ONLY. It is functionally redundant
    # everywhere -- an unmatched D8:2 falls through to [player] spawn / [player] face, which is
    # exactly what the row says -- and its one real job is to give `campaign.lint_campaign` (g2)
    # coverage for the campaign's own entry, which injects `<campaign entry>` into the ENTRY
    # member's inbound set alone (campaign.py:872-874). Emitting it on every room therefore buys
    # nothing and costs a spurious per-room advisory ("entrance 0 is not routed here by any
    # campaign edge") that trains the author to ignore that lint. Its face must equal
    # [player] face because both compile to the SAME D9(6) const -- a disagreement is
    # unrepresentable, not merely odd.
    arrivals[entry].insert(0, {"entrance": 0, "pos": list(spawns[entry]), "face": SPAWN_FACE,
                               "from": "<entry>"})

    # ---- stage 5: reachability (WARN) ------------------------------------------------------------
    adj = {n: set() for n in order}
    for d in doors:
        adj[d["a"]].add(d["b"])
        if d["two_way"]:
            adj[d["b"]].add(d["a"])
    seen_r, stack = {entry}, [entry]
    while stack:
        for nb in adj[stack.pop()]:
            if nb not in seen_r:
                seen_r.add(nb)
                stack.append(nb)
    lost = [n for n in order if n not in seen_r]
    if lost:
        warnings.append(f"unreachable from {entry}: {', '.join(lost)} -- no chain of doors leads "
                        f"there, so the player can only arrive by a debug warp")

    # ---- stage 6: per-room emit (G4, G6, G8, G15's inputs) ---------------------------------------
    problems = []
    out_rooms = []
    for r in rooms_in:
        n = str(r["name"])
        pitch, fov = _room_defaults(r)
        notes = []
        try:
            cam, off, rng, scrolling = fit_room_camera(polys[n], pitch=pitch, fov=fov,  # G6
                                                       notes=notes)
        except ComposeError as e:
            problems.append(f"room {n}: {e}")
            continue
        warnings.extend(f"room {n}: {t}" for t in notes)
        sev, msg = legibility_problem(n, cam, polys[n])                              # G16
        if sev == "error":
            problems.append(msg)
            continue
        if sev == "warn":
            warnings.append(msg)
        shift = lambda pts, _o=off: [(int(round(x + _o[0])), int(round(z + _o[1]))) for x, z in pts]
        poly_room = shift(polys[n])
        verts, faces = _if.triangulate(poly_room)

        gates, zone_rows = [], []
        for s in strips[n]:
            quad = shift(s["zone"])
            zone_rows.append({"zone": quad, "label": s["label"]})
            if s["target"] is not None:
                gates.append({"name": f"door_to_{s['target']}".lower(),
                              "to": ids[s["target"]],
                              "entrance": entrance[(s["target"], _door_key(s["door"]))],
                              "zone": [list(p) for p in quad]})

        save_block = None
        if n in saves:
            s = saves[n]
            pq = shift(s["press"])
            site_room = shift([s["site"]])[0]
            why = arrival_problem(site_room, poly_room, zone_rows)                    # G8
            if why is not None:
                problems.append(f"room {n}: the save point sits {why}")
            else:
                save_block = {"zone": [list(p) for p in pq], "pos": list(site_room)}
                zone_rows.append({"zone": pq, "label": "the save point"})

        for i in range(len(zone_rows)):                                              # G4
            for j in range(i + 1, len(zone_rows)):
                if polys_overlap(zone_rows[i]["zone"], zone_rows[j]["zone"]):
                    problems.append(
                        f"room {n}: {zone_rows[i]['label']} and {zone_rows[j]['label']} overlap. "
                        f"The engine delivers exactly ONE tread region per frame, so one of them "
                        f"would silently never fire.")

        enc = r.get("encounter")
        if enc:
            allowed = {"scene", "scenes", "freq", "pattern", "battle_music"}
            unknown = sorted(set(enc) - allowed)
            if unknown:                          # build.py has no closed key set for [encounter]
                problems.append(
                    f"room {n}: [encounter] has unknown key(s) {', '.join(unknown)}. The build does "
                    f"NOT check this (there is a _sp_keys gate for [[savepoint]] but no _enc_keys), "
                    f"so a typo would build clean and silently run at the default frequency.")
            if not (enc.get("scene") or enc.get("scenes")):
                problems.append(f"room {n}: [encounter] needs `scene` (or `scenes`) -- freq and "
                                f"battle_music are inert without it")
            # Resolve the scene HERE rather than deferring to the build, for TWO reasons that both
            # still hold now that the build resolves names itself (build.resolve_encounter_scenes):
            #  * a composer problem should name the ROOM, which is context the build doesn't have; and
            #  * a MODEL-BUCKET id (BSC_B3_*) crashes in-game with an InitBattleScene null-ref, which
            #    the build only WARNS about -- here it's a hard problem before a room is ever emitted.
            # Resolving to a numeric id also keeps the emitted toml in the shape every shipped example
            # uses. The author's own spelling stays in the sidecar.
            from . import catalog as _cat
            enc = dict(enc)
            for key in ("scene", "scenes"):
                if enc.get(key) is None:
                    continue
                vals = [enc[key]] if key == "scene" else list(enc[key] or [])
                sids = []                       # NOT `ids` -- that name holds the room->field-id map
                for val in vals:
                    try:
                        sid = _cat.resolve_scene(val)
                    except ValueError as e:
                        problems.append(f"room {n}: [encounter] {e}")
                        continue
                    if _cat.is_model_bucket_scene(sid):
                        problems.append(
                            f"room {n}: [encounter] scene {val!r} -> {_cat.scene_name(sid)} is a "
                            f"MODEL-BUCKET id (BSC_B3_*), not a fightable encounter -- it crashes "
                            f"in-game with an InitBattleScene null-ref")
                        continue
                    sids.append(int(sid))
                    if str(val) != str(sid):
                        warnings.append(f"room {n}: [encounter] {key} {val!r} resolved to id {sid} "
                                        f"({_cat.scene_name(sid)})")
                if sids:
                    enc[key] = sids[0] if key == "scene" else sids

        toml = {
            "field": {"id": ids[n], "name": n, "area": 11,
                      "title": str(r.get("title") or n.replace("_", " ").title())},
            "camera": _camera_toml(cam, pitch, fov, rng, scrolling),
            "walkmesh": {"obj": "walkmesh.obj"},
            "layers": _placeholder_layers(polys[n], cam),
            "player": {"spawn": list(shift([spawns[n]])[0]), "face": spawn_face[n]},
        }
        rows = []
        for row in arrivals[n]:
            pos = shift([tuple(row["pos"])])[0]
            if row["face"] is None:                                                 # G10
                problems.append(f"room {n}: an arrival row has no face -- content/npc.py:372 emits "
                                f"no D9(6) write for a face-less row and the template default is "
                                f"a hard-coded 0 = SOUTH, i.e. a silent 'face the camera'")
            rows.append({"entrance": row["entrance"], "pos": list(pos), "face": int(row["face"])})
        toml["player"]["arrival"] = rows      # raw shape is player.arrival, NOT a dotted key
                                              # (verified against studies/field-entry/ARRTEST)
        if gates:
            toml["gateway"] = gates
        if enc:
            toml["encounter"] = dict(enc)
        if save_block:
            toml["savepoint"] = [save_block]

        out_rooms.append(ComposedRoom(
            name=n, field_id=ids[n], poly_plan=polys[n], poly_room=poly_room, off_r=off,
            camera=cam, pitch=pitch, fov=fov, distance=toml["camera"]["distance"],
            toml=toml, verts=verts, faces=faces))
    if problems:
        raise ComposeError(*problems)

    edges_out = []
    for d in doors:
        edges_out.append({"from": d["a"], "to": d["b"],
                          "entrance": entrance[(d["b"], _door_key(d))]})
        if d["two_way"]:
            edges_out.append({"from": d["b"], "to": d["a"],
                              "entrance": entrance[(d["a"], _door_key(d))]})

    return Composed(name=name, mod_folder=mod_folder, rooms=out_rooms, entry=entry,
                    edges=edges_out, warnings=warnings)


# ------------------------------------------------------------------ the sidecar

SIDECAR = "floorplan.json"


def load_plan(path):
    """Read a ``floorplan.json`` session. The field.tomls are the buildable truth; this is the
    re-editable session, exactly as ``.trace.json`` is for the Trace lane. It has to be a sidecar and
    not campaign.toml metadata: every campaign mutation re-renders the manifest through
    ``campaign.render_campaign_toml``, which silently DROPS keys it does not know."""
    import json
    from pathlib import Path
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_plan(plan, path):
    import json
    from pathlib import Path
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = dict(plan)
    body.setdefault("version", 1)
    p.write_text(json.dumps(body, indent=2), encoding="utf-8", newline="\n")
    return p


# ------------------------------------------------------------------ emit to disk

def emit(composed, out_dir, *, plan=None, log=None):
    """Write a :class:`Composed` dungeon to disk as a buildable campaign. Returns a summary dict.

    Layout, one member directory per room (mandatory -- ``build.FieldProject.path()`` confines every
    asset ref to the field.toml's own directory, refusing both absolute paths and ``..``, so rooms
    cannot share an art folder or a walkmesh)::

        <out_dir>/campaign.toml
        <out_dir>/floorplan.json          the re-editable session
        <out_dir>/<ROOM>/<room>.field.toml
        <out_dir>/<ROOM>/walkmesh.obj
        <out_dir>/<ROOM>/art/back.png     art/floor.png     art/README.txt

    The manifest goes through ``campaign.new_campaign`` + ``campaign.add_field`` rather than a
    private writer (click-authoring PLAN.md §5 call site 4). ``add_field(source=None)`` scaffolds each
    member via ``pack.new_project``, whose template field.toml and rectangular placeholder art we
    then REPLACE with the composed room's own -- one wasted PNG write per room, paid to keep
    ``add_field`` the single manifest writer.
    """
    from pathlib import Path
    from . import campaign as _campaign
    from .editor import model as _model
    from .scene import placeholder as _placeholder

    say = log or (lambda *_a: None)
    out = Path(out_dir)
    ids = [r.field_id for r in composed.rooms]
    base = min(ids)
    if ids != list(range(base, base + len(ids))):
        raise ComposeError(f"emit needs one consecutive id run, got {ids} -- campaign.add_field's "
                           f"allocator is max(existing)+1 and cannot express a gap")

    cplan = _campaign.new_campaign(composed.name, composed.mod_folder, out, id_base=base)
    for room in composed.rooms:
        member = _campaign.add_field(cplan, out, name=room.name)
        if member.new_id != room.field_id:               # the allocator and the pre-flight must agree
            raise ComposeError(f"room {room.name}: composed id {room.field_id} but the campaign "
                               f"allocator assigned {member.new_id}")
        mdir = out / room.name
        (out / member.toml_rel).write_text(_model.dumps(room.toml), encoding="utf-8", newline="\n")
        _if.write_walkmesh_obj(room.verts, room.faces, mdir / "walkmesh.obj")
        tris = [(room.verts[a], room.verts[b], room.verts[c]) for a, b, c in room.faces]
        _placeholder.write_placeholders(room.camera, None, mdir / "art" / "back.png",
                                        mdir / "art" / "floor.png", floor_tris=tris)
        say(f"  {room.name:<12} id {room.field_id}  {len(room.poly_room)} verts  "
            f"pitch {room.pitch:g} dist {room.distance}  off_r {room.off_r}")

    cplan.entry_name = composed.entry
    # `CampaignPlan.edges` keys the source as "frm" -- `from` is a Python keyword, so the in-memory
    # dataclass cannot use the TOML's own spelling (campaign.py:222, :433). Translate at this one
    # boundary rather than leaking `frm` into the composer's public shape.
    cplan.edges = [{"frm": e["from"], "to": e["to"], "entrance": e["entrance"]}
                   for e in composed.edges]
    # `_save_plan` is campaign.py's own documented "single persistence point for every mutation";
    # the per-item add_edge/set_entry API it used to expose was retired in 2026-07 with no caller.
    _campaign._save_plan(cplan, out)

    if plan is not None:
        save_plan(plan, out / SIDECAR)
    return {"campaign": out / "campaign.toml", "rooms": len(composed.rooms),
            "ids": ids, "sidecar": (out / SIDECAR) if plan is not None else None}


def compose_and_emit(plan, out_dir, *, taken_ids=(), log=None):
    """The whole verb: a plan dict -> a buildable campaign on disk. Raises :class:`ComposeError`."""
    composed = compose(plan, taken_ids=taken_ids)
    return composed, emit(composed, out_dir, plan=plan, log=log)
