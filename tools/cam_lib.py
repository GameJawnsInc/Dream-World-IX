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

# Global canvas scale: painted-canvas-px per field-screen-px. Derived map is scale-1 on
# both axes (canvasX = projectedPos.x + HalfW; canvasY = -projectedPos.y + HalfH), but the
# field's ortho camera applies a single uniform scale s that static source can't reveal.
# Pinned by the room02 checkerboard calibration (Session 10). The field ortho camera scales the
# two axes DIFFERENTLY (non-square): vertical 0.889 (top/bottom edges), horizontal 0.926 (left/right
# edges). Supersedes the Session-8 back-fit 0.929 (fit to a freehand painting, never a clean grid).
S_CANVAS_X = 0.926
S_CANVAS_Y = 0.889
S_CANVAS = S_CANVAS_Y   # back-compat alias

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

def to_canvas(P, cam, sx=S_CANVAS_X, sy=S_CANVAS_Y, half_w=HALF_FIELD_W, half_h=HALF_FIELD_H):
    """Painted-canvas pixel (top-left origin, Y down) where a world point appears.
    Calibrated (room02 grid, Session 10):
      canvasX = w/2 + sx*(projectedPos.x - offsetX)   # centered on canvas mid; offsetX = projX at x=0
      canvasY =       sy*(-projectedPos.y + HalfFieldHeight)  # scales about the top
    Horizontal centers at the canvas midpoint (world x=0 -> canvasX = w/2) and uses sx=0.926;
    vertical scales about the top with sy=0.889 (the field ortho camera is non-square)."""
    px, py, _ = project_screen(P, cam, half_w, half_h)
    offx, _ = compute_offset(cam, half_w, half_h)
    return (cam.range[0]/2.0 + sx*(px - offx), sy*(-py + half_h))

def solve_z_for_canvasY(cam, canvasY, x=0.0, y=0.0, sy=S_CANVAS_Y, half_h=HALF_FIELD_H,
                        zlo=-6000.0, zhi=6000.0):
    """Inverse: find the world z (at given x,y) whose foot projects to a painted-canvas row.
    Bisection on the monotonic canvasY(z). Returns z or None."""
    def cy(z): return to_canvas((x, y, z), cam, sy=sy, half_h=half_h)[1]
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
    cams, cur = [], None
    for line in open(path, encoding="utf-8", errors="replace"):
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
