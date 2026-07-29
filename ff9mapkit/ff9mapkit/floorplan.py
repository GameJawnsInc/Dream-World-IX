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
  * ``R_WALK = 80``, not ``cam.COLLISION_RADIUS_W`` (48). The kit's player Init runs
    ``SetObjectLogicalSize(20, 24, 40)`` and Memoria's ``DoEventCode.cs:1531`` does
    ``radius = size * 4``. ``cam.py:66-70``'s stated basis (``bgiRad*4`` off the ``.bgi``) is wrong:
    ``bgiRad``'s only writer is the battle-return backup, so it is 0 on a fresh load.
  * The camera fit MUST gate on per-vertex depth. Apparent size goes as ``1/|D + cos(p)z|``, which
    has a POLE, so a box-only test accepts a camera 740u INSIDE the room.
  * ``cam.solve_z_for_canvasY`` and ``guide.frame_floor`` are unsound at low pitch and are NOT in
    this module's call path (:func:`z_for_row` replaces them).
  * A ``face``-less ``[[player.arrival]]`` row is not "no facing" -- the template's unconditional
    ``D9(6)`` default is 0 = SOUTH, i.e. a silent "face the camera whichever wall you came through".
"""
from __future__ import annotations

import math
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

# ★ THE WALL RADIUS -- the composer's OWN constant. DO NOT substitute cam.COLLISION_RADIUS_W.
# Chain (all four links traced): the kit's player Init runs CreateObject then
# SetObjectLogicalSize(20, 24, 40) -> Memoria EventEngine.DoEventCode.cs:1500 `size = getv1()`
# (arg1 == 20) -> :1531 `component1.radius = size * 4` == 80 -> FieldMapActorController.cs:1057
# RadiusValid -> WalkMesh.cs:1976 BGI_computeNewPoint pins the centre at EXACTLY radius off an
# inaccessible edge. cam.COLLISION_RADIUS_W = 48 (scene/cam.py:71) is 64% small AND its comment's
# basis is factually wrong (bgiRad is 0 on a fresh load; its only writer is the battle-return
# backup at EventEngine.cs:1443). ⚠ This is a CODE derivation, not an in-game measurement -- see
# RUNG6.md §6.1. Adopting 80 is safe either way: if 48 is right these gates are merely stricter.
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
BAND_REACH = 4 * R_WALK   # 320u -- how far "one sideways step" reaches, for the axis-band WARN.
                          # A TUNED JUDGMENT, not a derivation: the law it serves says "a spawn at
                          # the same depth as a zone row is one sideways step from firing it", and a
                          # band test with no lateral cap fires on EVERY door in EVERY dungeon
                          # (a spawn is in its own room's door band by construction -- that is how
                          # the player reaches the door). For scale, actors jam under 192u and the
                          # skill's standing spacing is >=300u, so 320u is a few steps, not a room.
TOUCH_EPS = 1e-6


# ------------------------------------------------------------------ C0: the closed-form projection

def cam_params(c):
    """``(pitch_rad, D, H, cx0, cy0)`` for a yaw-0 :func:`guide.make_camera` camera over ``y=0``."""
    p = math.radians(_cam.pitch_deg(c))
    D = -_cam.decompose(c)["C"][2] / math.cos(p)
    return (p, D, float(c.proj),
            c.centerOffset[0] + c.range[0] / 2.0,
            c.range[1] / 2.0 + c.centerOffset[1])


def project_floor(x, z, c):
    """``(canvasX, canvasY, depth)`` for a floor point. ``depth = D + cos(p)*z``.

    Exact: max 0.07 canvas px against :func:`cam.to_canvas` at depth >= 500 over 8 pitches x 4
    distances. The reason to have it at all is the third return value -- ``cam.to_canvas`` folds
    ``abs(resz)`` (scene/cam.py:166), which MIRRORS a behind-camera point into an ordinary-looking
    in-canvas coordinate. The depth is the only thing that can see that."""
    p, D, H, cx0, cy0 = cam_params(c)
    dep = D + math.cos(p) * z
    return (cx0 + x * H / abs(dep),
            cy0 - K_VSCALE * math.sin(p) * H * z / abs(dep),
            dep)


def horizon_row(c):
    """The painted-canvas row the horizon sits on (may be off-canvas, which is the healthy case)."""
    p, D, H, cx0, cy0 = cam_params(c)
    return cy0 - K_VSCALE * math.tan(p) * H


def z_for_row(c, row, *, near=NEAR_W):
    """Front-branch world ``z`` whose floor projects to painted-canvas ``row``; None if unreachable.

    ★ REPLACES :func:`cam.solve_z_for_canvasY` for the composer, and the reason is a defect in that
    function, not a preference: it brackets ``[-30000, +30000]``, which SPANS the projection pole at
    ``z = -D/cos(pitch)``. Past the pole ``cam.py:166``'s ``num = abs(resz)`` mirrors the branch, so
    its sign test bails and it returns None for rows that DO have a root. Measured at pitch 15 /
    distance 3000: rows 365, 420 and 440 all return None while the true roots (z = -1646, -1896,
    -1967) re-project to 364.97, 419.96 and 439.95. ``guide.frame_floor`` inherits the same fault
    and RAISES at every distance for pitch 15. Both are spawned as their own fix."""
    p, D, H, cx0, cy0 = cam_params(c)
    s, co = math.sin(p), math.cos(p)
    a = cy0 - row
    den = K_VSCALE * s * H - a * co
    if abs(den) < 1e-9:
        return None                                    # the row IS the horizon
    z = a * D / den
    return None if D + co * z <= near else z


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
    """PROPER crossing of ``ab`` and ``cd``. Collinear-overlapping and shared-endpoint touching both
    return False, which is what makes two rooms allowed to ABUT along a shared wall."""
    d1, d2 = _cross3(c, d, a), _cross3(c, d, b)
    d3, d4 = _cross3(a, b, c), _cross3(a, b, d)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def polys_overlap(A, B, *, eps=TOUCH_EPS):
    """True when two SIMPLE polygons share interior area. Touching (a shared wall, a shared corner)
    is NOT overlap.

    ★ This is the authority, not :func:`build.region_overlap_pairs`, which is an AABB test: two
    provably disjoint 45deg bevel strips make it report a pair. Erroring on that would refuse every
    bevelled, diagonal or octagonal room -- the shapes a human actually draws. Valid for CONCAVE
    polygons too, which SAT is not, and rooms are routinely L-shaped."""
    for ea in edges(A):
        for eb in edges(B):
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
    x0, z0, x1, z1 = bbox(poly)
    out = set()
    x = x0
    while x <= x1 + step:
        z = z0
        while z <= z1 + step:
            if point_in_poly(x, z, poly) and dist_to_boundary(x, z, poly) >= R:
                out.add((int(math.floor(x / step)), int(math.floor(z / step))))
            z += step
        x += step
    return out


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
    reported as standable. Sampled at a quarter of the room grid so a thin band is not missed."""
    if step is None:
        step = GRID_STEP / 4.0
    x0, z0, x1, z1 = bbox(quad)
    tot, hit = 0, []
    i0, i1 = int(math.floor(x0 / step)), int(math.ceil(x1 / step))
    j0, j1 = int(math.floor(z0 / step)), int(math.ceil(z1 / step))
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            x, z = (i + 0.5) * step, (j + 0.5) * step
            if not point_in_poly(x, z, quad):
                continue
            tot += 1
            if point_in_poly(x, z, poly) and dist_to_boundary(x, z, poly) >= R:
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
                    front_row=FRONT_ROW, notes=None):
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
    ``cam.project``. THE DEFAULT-VALUE LAW gets no help from that call site; the bound lives here."""
    # ★ The HARD boundary is `p*` itself -- the pitch at which the horizon reaches canvas row 0.
    # Below it part of the frame has no floor at all. PITCH_SLACK is a comfort margin above that,
    # and it is a WARNING, not a refusal, deliberately: `imagefield.DEFAULT_PITCH` is 26.0 and
    # `p*` is 25.73 at fov 42.2, so an error at `p* + 1` would refuse the trace lane's own default
    # pitch. The second hazard `p*` was meant to cover -- a behind-camera vertex faking a canvas
    # fit -- is caught directly and independently by the per-vertex depth gate below, so the pitch
    # gate does not have to be the one carrying it.
    pstar = pitch_floor(fov)
    H = _guide.proj_from_fov_x(fov, CANVAS_W)
    row = CANVAS_H / 2.0 - K_VSCALE * math.tan(math.radians(pitch)) * H
    if pitch <= pstar:
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
        c = _guide.make_camera(pitch, D, fov_x_deg=fov)
        zf = z_for_row(c, front_row)
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

def interior_point(poly, avoid, *, R=R_WALK, step=GRID_STEP):
    """The spawn / save-point site: the standable cell furthest from any wall that also clears every
    ``avoid`` zone by ``R``.

    ★ There is deliberately no "centroid first" fast path. For a plain L-shaped room the
    VERTEX-AVERAGE centroid -- the idiom ``build.py`` already uses for zone centres at :3734, :3742
    and :5960 -- lands exactly ON the reflex corner and tests OUTSIDE the polygon; the area
    (shoelace) centroid is inside. For a U/horseshoe room BOTH fall outside. An L is the normal case
    for a hand-drawn plan (a plain rectangle needs no composer), so the grid search is the
    load-bearing implementation, not a rare fallback."""
    x0, z0, x1, z1 = bbox(poly)
    cx, cz = (x0 + x1) / 2.0, (z0 + z1) / 2.0
    best = None
    for (i, j) in sorted(standable(poly, R=R, step=step)):
        x, z = (i + 0.5) * step, (j + 0.5) * step
        if any(dist_point_to_poly((x, z), a) < R for a in avoid):
            continue
        d = dist_to_boundary(x, z, poly)
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


def compose(plan, *, taken_ids=()):
    """A floorplan dict -> a :class:`Composed` dungeon. Pure: no disk, no Qt, no game install.

    ``plan`` is the ``floorplan.json`` shape::

        {"name": str, "mod_folder": str, "id_base": int,
         "rooms": [{"name","poly":[[x,z],..],"pitch"?,"fov"?,"encounter"?,"savepoint"?,"id"?}],
         "doors": [{"a","b","seg":[[x,z],[x,z]],"depth"?,"two_way"?}],
         "entry"?: room name}

    Every gate is a compose-time ERROR unless the docstring says WARN. THE DEFAULT-VALUE LAW: a
    minted value is real, or loudly refused. Problems are collected per stage and raised together,
    so the author sees every fixable thing at once."""
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
        cells = standable(poly)                                                     # G13
        if not cells:
            problems.append(f"room {rn}: nowhere in it is {R_WALK:g}u clear of a wall -- the player "
                            f"centre could not stand anywhere. It needs to be at least "
                            f"{2 * R_WALK:g}u across.")
            continue
        comps = components(cells)
        if len(comps) > 1:
            problems.append(f"room {rn}: its walkable area is {len(comps)} disconnected pieces "
                            f"(the largest is {len(comps[0])} cells of {len(cells)}) -- a neck "
                            f"narrower than {2 * R_WALK:g}u splits it and the player cannot cross")
            continue
        ratio = len(cells) * GRID_STEP * GRID_STEP / max(abs(_if._signed_area(poly)), 1.0)
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
            frac, pts = strip_standable_fraction(polys[who], quad)                  # G9
            if not pts:
                problems.append(
                    f"door {a}-{b} on {who}'s side: no part of the {depth:g}u strip is standable -- "
                    f"the room pinches to under {R_WALK:g}u of clearance at that wall, so the strip "
                    f"lies entirely inside the shell the player centre can never enter. Widen the "
                    f"room there, or move the door.")
                ok = False
                continue
            audit = _if.zone_fan_audit(quad)                                        # G7
            if max(audit["gap"], audit["spill"]) > FAN_TOL:
                problems.append(
                    f"door {a}-{b} on {who}'s side: the engine's IsInQuad fan disagrees with the "
                    f"drawn outline by gap {audit['gap']:.3f} / spill {audit['spill']:.3f} "
                    f"(tolerance {FAN_TOL})")
                ok = False
                continue
            if len(_if.fan_triangles(quad)) < 2:                                    # G9 degeneracy
                problems.append(f"door {a}-{b} on {who}'s side: the quad is degenerate "
                                f"({len(_if.fan_triangles(quad))} triangles). Note the fan audit "
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
        zones = strips[n]
        quads = [z["zone"] for z in zones]
        try:
            spawn = interior_point(polys[n], quads)
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
                site = interior_point(polys[n], quads + [spawn_box])
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

    # ★ The entrance-0 row is the campaign entry / a debug warp, and its face MUST equal
    # [player] face -- both compile to the SAME D9(6) const, so a disagreement is unrepresentable
    # rather than merely odd. The value is 0 = SOUTH, and that is a real choice, not a shrug: it is
    # the engine's own unconditional template default (so the row agrees with the fallback instead
    # of fighting it), and 0 = facing the camera is the layout skill's stated idiom for a standing
    # actor. Unlike a door arrival there is no wall to derive a direction from -- deriving it from
    # "whichever inbound door sorted first" would make the value depend on room naming.
    SPAWN_FACE = 0
    spawn_face = {n: SPAWN_FACE for n in order}
    for n in order:
        arrivals[n].insert(0, {"entrance": 0, "pos": list(spawns[n]), "face": SPAWN_FACE,
                               "from": "<entry>"})

    # ---- stage 5: reachability (WARN) ------------------------------------------------------------
    entry = str(plan.get("entry") or order[0])
    if entry not in polys:
        raise ComposeError(f"entry room {entry!r} is not in the floorplan")
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
            cam, off = fit_play_camera(polys[n], pitch=pitch, fov=fov, notes=notes)  # G6
        except ComposeError as e:
            problems.append(f"room {n}: {e}")
            continue
        warnings.extend(f"room {n}: {t}" for t in notes)
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

        toml = {
            "field": {"id": ids[n], "name": n, "area": 11,
                      "title": str(r.get("title") or n.replace("_", " ").title())},
            "camera": {"entry_settle": "auto", "pitch": pitch,
                       "distance": int(round(-_cam.decompose(cam)["C"][2] / math.cos(math.radians(pitch)))),
                       "fov": fov},
            "walkmesh": {"obj": "walkmesh.obj"},
            "layers": [{"image": "art/back.png", "z": 4000},
                       {"image": "art/floor.png", "z": 3000}],
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
