#!/usr/bin/env python3
# FF9 field CAMERA math library — the "novel camera" toolkit.
#
# Goal: faithfully read / decompose / re-synthesize an FF9 .bgx CAMERA block,
# so we can author a brand-new camera (any angle) instead of borrowing one.
#
# Ground truth (verified against Memoria source):
#   * Player/walkmesh screen position = PSX.CalculateGTE_RTPT_POS(worldPos,
#       localRTS=identity, globalRT=GetMatrixRT(), viewDist=proj, offset=centerOffset, useAbsZ=true)
#       (FieldMapActor.cs:121). localRTS is identity for field actors.
#   * GetMatrixRT() row i = (r[i,0]/4096, r[i,1]/4096, r[i,2]/4096 | t[i]); row3=(0,0,0,1).
#   * .bgx OrientationMatrix entries == r[i,j]/4096 (BGSCENE_DEF.ProcessMemoriaCamera / ExportMemoriaBGX).
#
# The projection (from PSX.CalculateGTE_RTPT_POS), with F = diag(1,-1,1):
#   v       = vertex                      # localRTS = I
#   v.y     = -v.y                        # flip 1   -> v' = F*vertex
#   result  = R_ff9 * v' + t              # globalRT = GetMatrixRT
#   result.y= -result.y                   # flip 2   -> result'' = F*result
#   num     = |result.z|
#   screen.x= result''.x * H/num + off.x
#   screen.y= result''.y * H/num + off.y
#   (screen.z = result.z  -> used for depth sort)
#
# Equivalent clean pinhole form (derived + validated here):
#   R_view  = F * R_ff9 * F
#   cs      = R_view * (P - C)            # camera-space; cs.z > 0 in front
#   screen  = (cs.x, cs.y) * H/|cs.z| + offset
#   with    t = -R_ff9 * (F*C)   <=>   C = -F * R_ff9^{-1} * t
#
# Key invariant (measured across 6 real cameras): R_ff9 = diag(1, k, 1) * R_ortho
#   where R_ortho is a proper orthonormal rotation and k = 14/15 = 0.933333...
#
# Pure stdlib (no numpy) so it runs anywhere the other tools do.
import math

K_VSCALE = 14.0 / 15.0            # 0.93333..  vertical-focal scale baked into row 1
ROT = 4096.0                      # fixed-point factor (BGCAM_DEF.ROTATTION_FACTOR)

# Field-screen half-extents (PSX native 4:3). HalfFieldWidth is aspect-dependent under
# widescreen (PsxFieldWidth/2); HalfFieldHeight is fixed (PsxFieldHeightNative/2 = 112).
HALF_FIELD_W = 160.0
HALF_FIELD_H = 112.0

# ---------- painted-canvas map (EXACT, scale-1) ----------
# A painted-canvas pixel (cx, cy) is placed by the engine's overlay system at FieldMap-world
# (cx - HalfFieldWidth, HalfFieldHeight - cy) (BGSCENE_DEF.CreateScene_OverlayGo, scale 1); the field
# actor/walkmesh is placed at its GTE-projected (px, py). Both render through the same ortho FieldMap
# camera, so a world point appears under canvas pixel (cx, cy) exactly when (px, py) == (cx - HFW,
# HFH - cy). Writing px,py as the RAW GTE projection plus the engine offset (range/2 - HFW in x,
# -range/2 + HFH in y), the HalfField terms cancel and the map is EXACTLY scale-1, no fudge:
#       canvasX = rawProj.x + range.w/2 ;  canvasY = range.h/2 - rawProj.y
# Verified noise-free against an in-engine projection probe (overlay corners + actor grid, 2026-06-02).
# The earlier S_CANVAS_X/Y = 0.926/0.889 were an eyeball fit that silently absorbed the player
# COLLISION_RADIUS_W (below) -- removed; kept here as 1.0 for any external caller.
S_CANVAS_X = 1.0
S_CANVAS_Y = 1.0
S_CANVAS = 1.0

# Walking-character collision radius, world units. FieldMap.cs sets the controller radius to
# bgiRad*4 (bgiRad from the .bgi; flat quads use the default ~12 -> ~48). The player CENTRE cannot
# reach the painted floor edge -- it stops ~this far inside (most visible at the foreshortened back
# edge; THIS was the old "back edge a bit short"). Physics, not a map error: extend the walkmesh
# past the painted floor by ~this much if the player should be able to stand at the visual edge.
COLLISION_RADIUS_W = 48.0

# Object<->object collision radius, world units (DISTINCT from the controller radius above).
# WalkMesh.Collision blocks one actor against another when their centres are within
# 4*collRadA + 4*collRadB; the default field character collRad is 16 (WalkMesh.cs:2363) -> 4*16 = 64
# per character. So two default characters collide at ~2*64 = 128u apart. A cutscene walk TO another
# object (e.g. @player) must therefore stop SHORT of this, or the actor presses into the box and the
# synchronous walk stalls. Used to auto-approach @object targets and to warn on too-close targets.
OBJECT_COLLISION_W = 64.0

# Character GROUND offset, world units. MEASURED IN-GAME = ~0 (Session 18 engine probe + grid, 3
# spots x 2 pitches): the character MODEL is projected by its vertex shader's GTE (FieldMapActor.txt:
# _MatrixRT/_ViewDistance/_OffsetX/Y) EXACTLY like the floor/walkmesh, so the feet render at the
# true world position -- there is NO real character-vs-floor offset. The earlier "3D-perspective-
# camera, feet sit behind" story (and the per-pitch sx/sy scale) was WRONG; both were fitting an
# artifact. The artifact: the legacy flat builder (bgi.quad/build_flat) injects orgPos=(0,0,300), so
# its walkmesh sits +300z off a to_canvas-painted floor; this 298 is the near-cancel that undoes it.
# So it is NOT a real offset -- it's the partner of the +300 org (the Session-17 double-count). The
# HONEST model is `[walkmesh] frame = "world"` => org=0 + NO offset (walkmesh in true world coords =
# the painted floor; exact at any angle). New scaffolds use that. This constant is kept ONLY so the
# legacy org=300 quad/auto path still cancels (head-on); prefer frame="world" for new work.
CHARACTER_GROUND_OFFSET_Z = 298.0

# ---------- scroll bounds (larger-than-screen fields) ----------
def scroll_bounds(range_wh, half_w=HALF_FIELD_W, half_h=HALF_FIELD_H):
    """Camera Viewport (vrpMinX, vrpMaxX, vrpMinY, vrpMaxY) that lets the native view window pan
    across the WHOLE painting, so a larger-than-screen field scrolls edge to edge.

    From Memoria's clamp (FieldMap.cs:1111-1114): vrpMin = HalfNative, vrpMax = size - HalfNative
    (HalfNative = PSX 160 x 112, == HALF_FIELD_W/H here). For a screen-sized painting (w,h == 384,448)
    this is (160, 224, 112, 336) = the kit's DEFAULT_VIEWPORT (min<->max gap is tiny, so no real
    scroll). For a wider painting the gap opens and the engine pans. In-game-proven on the 768x448
    spike (field 4003): Viewport (160, 608, 112, 336) scrolls + clamps cleanly with no over-scroll."""
    w, h = int(range_wh[0]), int(range_wh[1])
    return (int(half_w), int(w - half_w), int(half_h), int(h - half_h))


# ---------- tiny 3x3 / vec3 linear algebra ----------
def mv(M, v):
    return [M[i][0]*v[0] + M[i][1]*v[1] + M[i][2]*v[2] for i in range(3)]
def mm(A, B):
    return [[sum(A[i][k]*B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def transpose(M):
    return [[M[j][i] for j in range(3)] for i in range(3)]
def dot(a, b):
    return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def norm(a):
    return math.sqrt(dot(a, a))
def sub(a, b):
    return [a[0]-b[0], a[1]-b[1], a[2]-b[2]]
def scale_rows(M, s):
    return [[M[i][j]*s[i] for j in range(3)] for i in range(3)]
def det3(M):
    return (M[0][0]*(M[1][1]*M[2][2]-M[1][2]*M[2][1])
          - M[0][1]*(M[1][0]*M[2][2]-M[1][2]*M[2][0])
          + M[0][2]*(M[1][0]*M[2][1]-M[1][1]*M[2][0]))
def inv3(M):
    d = det3(M)
    c = [[ (M[1][1]*M[2][2]-M[1][2]*M[2][1]), -(M[0][1]*M[2][2]-M[0][2]*M[2][1]),  (M[0][1]*M[1][2]-M[0][2]*M[1][1])],
         [-(M[1][0]*M[2][2]-M[1][2]*M[2][0]),  (M[0][0]*M[2][2]-M[0][2]*M[2][0]), -(M[0][0]*M[1][2]-M[0][2]*M[1][0])],
         [ (M[1][0]*M[2][1]-M[1][1]*M[2][0]), -(M[0][0]*M[2][1]-M[0][1]*M[2][0]),  (M[0][0]*M[1][1]-M[0][1]*M[1][0])]]
    return [[c[i][j]/d for j in range(3)] for i in range(3)]

F = [[1,0,0],[0,-1,0],[0,0,1]]    # the y-flip diag(1,-1,1)
def Fapply(v): return [v[0], -v[1], v[2]]

# ---------- camera container ----------
class Cam:
    def __init__(self):
        self.proj = 0            # H = ViewDistance
        self.centerOffset = [0, 0]
        self.t = [0, 0, 0]       # RT translation
        self.range = [0, 0]      # w, h  (canvas size)
        self.depthOffset = 0
        self.viewport = [0, 0, 0, 0]  # minX,maxX,minY,maxY
        self.r = [[0,0,0],[0,0,0],[0,0,0]]   # r[i][j] = OrientationMatrix * 4096 (Int16)
    def Rf(self):
        "R_ff9 = r/4096 (float 3x3)"
        return [[self.r[i][j]/ROT for j in range(3)] for i in range(3)]

# ---------- the exact engine projection ----------
def project(P, cam, offset=(0.0, 0.0)):
    """Replicates PSX.CalculateGTE_RTPT_POS. Returns (screenX, screenY, depthZ).
    `offset` is the 2D projection offset ADDED after the perspective divide.
    NOTE: the engine does NOT pass raw centerOffset here — it passes `compute_offset(cam)`
    (FieldMap.cs builds projectionOffset = centerOffset +/- range/2 +/- HalfField).
    Use project_screen() for the engine-accurate actor position."""
    Rf = cam.Rf()
    v = Fapply(P)                       # flip 1
    res = [mv(Rf, v)[i] + cam.t[i] for i in range(3)]   # R*v + t
    resz = res[2]
    res = Fapply(res)                   # flip 2 (y)
    num = abs(resz)
    sx = res[0]*cam.proj/num + offset[0]
    sy = res[1]*cam.proj/num + offset[1]
    return (sx, sy, resz)

def compute_offset(cam, half_w=HALF_FIELD_W, half_h=HALF_FIELD_H):
    """The projectionOffset the engine actually passes to the GTE (FieldMap.cs:393-406).
    offset.x = centerOffset.x + w/2 - HalfFieldWidth ; offset.y = -centerOffset.y - h/2 + HalfFieldHeight"""
    return (cam.centerOffset[0] + cam.range[0]/2.0 - half_w,
            -cam.centerOffset[1] - cam.range[1]/2.0 + half_h)

def project_screen(P, cam, half_w=HALF_FIELD_W, half_h=HALF_FIELD_H):
    "Engine-accurate actor screen position (FieldMapActor.cs:121): GTE with the real offset."
    return project(P, cam, compute_offset(cam, half_w, half_h))

def depth(P, cam):
    "Actor depth for OT sorting (FieldMapActor.cs:122 / shader): result.z/4 + depthOffset."
    _, _, resz = project(P, cam)
    return resz/4.0 + cam.depthOffset

def to_canvas(P, cam):
    """Painted-canvas pixel (top-left origin, Y down) where a world point appears.
    EXACT, scale-1 (no calibration fudge):
      canvasX = rawProj.x + range.w/2 ;  canvasY = range.h/2 - rawProj.y
    Derived from the engine overlay placement (BGSCENE_DEF) + the GTE actor projection (FieldMap),
    and verified noise-free against an in-engine projection probe.
    NB: this is pure geometry -- the player's COLLISION_RADIUS_W keeps the player CENTRE a constant
    ~48 world units inside any painted edge; account for it in the walkmesh, not here."""
    px, py, _ = project(P, cam)                 # RAW GTE projection (offset 0,0)
    return (px + cam.range[0]/2.0, cam.range[1]/2.0 - py)


def solve_z_for_canvasY(cam, canvasY, x=0.0, y=0.0, zlo=-30000.0, zhi=30000.0):
    """Inverse: find the world z (at given x,y) whose foot projects to a painted-canvas row.
    Bisection on the monotonic canvasY(z). Returns z, or None if the row is unreachable (the
    floor never projects there at this camera — i.e. above the horizon, or beyond the z search)."""
    def cy(z): return to_canvas((x, y, z), cam)[1]
    a, b = zlo, zhi
    fa, fb = cy(a)-canvasY, cy(b)-canvasY
    if fa == 0: return a
    if fb == 0: return b
    if (fa > 0) == (fb > 0): return None
    for _ in range(80):
        m = 0.5*(a+b); fm = cy(m)-canvasY
        if abs(fm) < 1e-4: return m
        if (fm > 0) == (fa > 0): a, fa = m, fm
        else: b, fb = m, fm
    return 0.5*(a+b)

def horizon_canvas_y(cam, x=0.0):
    """The painted-canvas Y the floor (y=0 plane) approaches as z -> +inf: the camera's horizon.
    Floor rows ABOVE this (smaller canvasY) are unreachable — there's no floor point there."""
    return to_canvas((x, 0.0, 1.0e7), cam)[1]

# ---------- decomposition: R_ff9 -> (k-per-row, R_ortho, camera pos C, R_view) ----------
def decompose(cam):
    Rf = cam.Rf()
    row_norms = [norm(Rf[i]) for i in range(3)]
    # divide each row by its norm to recover the orthonormal rotation
    R_ortho = [[Rf[i][j]/row_norms[i] for j in range(3)] for i in range(3)]
    # orthonormality residual: ||R_ortho * R_ortho^T - I||_max
    RRt = mm(R_ortho, transpose(R_ortho))
    ortho_err = max(abs(RRt[i][j] - (1.0 if i == j else 0.0)) for i in range(3) for j in range(3))
    det = det3(R_ortho)
    # camera world position: C = -F * R_ff9^{-1} * t
    Rinv = inv3(Rf)
    C = Fapply([-x for x in mv(Rinv, cam.t)])
    R_view = mm(mm(F, Rf), F)
    return {
        "row_norms": row_norms,
        "k": row_norms[1],
        "R_ortho": R_ortho,
        "ortho_err": ortho_err,
        "det": det,
        "C": C,
        "R_view": R_view,
        "fov_x_deg": 2*math.degrees(math.atan((cam.range[0]/2.0)/cam.proj)) if cam.range[0] else None,
    }

# ---------- synthesis: (camera pos C, R_ortho, H) -> r[][], t[] ----------
def synth_r_t(C, R_ortho, H, k=K_VSCALE):
    "Build FF9 r[][] (Int16) and t[] from a clean camera. Inverse of decompose()."
    Rf = scale_rows(R_ortho, [1.0, k, 1.0])         # R_ff9 = diag(1,k,1)*R_ortho
    r = [[int(round(Rf[i][j]*ROT)) for j in range(3)] for i in range(3)]
    t = [int(round(x)) for x in [-v for v in mv(Rf, Fapply(C))]]   # t = -R_ff9*(F*C)
    return r, t

# ---------- rotation builders (proper orthonormal, right-handed) ----------
def rot_x(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return [[1,0,0],[0,c,-s],[0,s,c]]
def rot_y(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return [[c,0,s],[0,1,0],[-s,0,c]]
def rot_z(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return [[c,-s,0],[s,c,0],[0,0,1]]

# ---------- .bgx CAMERA block I/O ----------
def parse_bgx_cameras(path):
    "Return list[Cam] parsed from a .bgx file."
    with open(path, encoding="utf-8", errors="replace") as fh:
        return parse_bgx_cameras_text(fh.read())


def parse_bgx_cameras_text(text):
    "Return list[Cam] parsed from .bgx text."
    cams, cur = [], None
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("//"):
            continue
        if s == "CAMERA":
            cur = Cam(); cams.append(cur); continue
        if cur is None or ":" not in s:
            continue
        key, _, val = s.partition(":")
        key = key.strip(); args = [a.strip() for a in val.split(",")]
        try:
            if key == "ViewDistance": cur.proj = int(args[0])
            elif key == "CenterOffset": cur.centerOffset = [int(args[0]), int(args[1])]
            elif key == "Position": cur.t = [int(args[0]), int(args[1]), int(args[2])]
            elif key == "Range": cur.range = [int(args[0]), int(args[1])]
            elif key == "DepthOffset": cur.depthOffset = int(args[0])
            elif key == "Viewport": cur.viewport = [int(a) for a in args[:4]]
            elif key == "OrientationMatrix":
                f = [float(a) for a in args[:9]]
                cur.r = [[int(round(f[i*3+j]*ROT)) for j in range(3)] for i in range(3)]
        except (ValueError, IndexError):
            pass
    return cams

def format_bgx_camera(cam):
    Rf = cam.Rf()
    om = ", ".join(_fmt(Rf[i][j]) for i in range(3) for j in range(3))
    return ("CAMERA\n"
            f"ViewDistance: {cam.proj}\n"
            f"CenterOffset: {cam.centerOffset[0]}, {cam.centerOffset[1]}\n"
            f"Position: {cam.t[0]}, {cam.t[1]}, {cam.t[2]}\n"
            f"Range: {cam.range[0]}, {cam.range[1]}\n"
            f"DepthOffset: {cam.depthOffset}\n"
            f"Viewport: {cam.viewport[0]}, {cam.viewport[1]}, {cam.viewport[2]}, {cam.viewport[3]}\n"
            f"OrientationMatrix: {om}\n")

def _fmt(x):
    # match Unity's float formatting closely enough for readability
    return f"{x:.7g}"


# ---------- supported camera-pitch range (advisory) ----------
# Both the camera SYNTHESIS (synth_r_t) and the painted-canvas map (to_canvas) are EXACT at any
# pitch (the map is pure projection, verified noise-free in-engine 2026-06-02). This range is now
# only an AUTHENTICITY advisory: the shipped FF9 cameras span ~0-50 deg downward pitch (GRGR steepest
# ~49.6; most 15-30). Steeper angles render correctly but look non-vanilla, and the constant
# COLLISION_RADIUS_W inset is more visible at a steep/foreshortened back edge. ADVISORY only.
SUPPORTED_PITCH_DEG = (0.0, 50.0)


def pitch_deg(cam):
    """Approximate downward pitch (degrees) of a camera, from its orthonormal orientation.

    Exact for pure-pitch cameras (R_ortho = rot_x(pitch)); a reasonable tilt estimate otherwise.
    """
    R = decompose(cam)["R_ortho"]
    return math.degrees(math.atan2(R[2][1], R[1][1]))


def yaw_deg(cam):
    """Camera yaw (orbit about world-Y), degrees, recovered from R_ortho row 0. 0 = front-facing.

    Exact for the make_camera form R_ortho = rot_x(pitch)·rot_y(-yaw), whose row 0 is
    (cos yaw, 0, -sin yaw); a reasonable estimate for arbitrary real cameras. Drives the player
    movement control-direction (TWIST): the WASD vector must rotate by the camera yaw so "up"
    stays "up the screen". See content.movement.control_value_for_angle."""
    R = decompose(cam)["R_ortho"]
    return math.degrees(math.atan2(-R[0][2], R[0][0]))


def pitch_warning(pitch, lo_hi=SUPPORTED_PITCH_DEG):
    """Return an advisory message if `pitch` (deg) is outside the supported range, else None."""
    lo, hi = lo_hi
    if lo <= pitch <= hi:
        return None
    return (f"camera pitch {pitch:.1f} deg is outside the typical FF9 range "
            f"[{lo:.0f}-{hi:.0f} deg]: the render and paint guide are still exact, but the angle "
            f"looks non-vanilla and the player's collision-radius inset is more visible at a steep "
            f"back edge. Advisory only.")
