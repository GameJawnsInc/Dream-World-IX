"""Blender <-> FF9 camera + coordinate bridge (bpy-FREE, offline-validated).

This is the heart of the add-on and the one genuinely tricky piece: mapping a Blender camera
(Z-up world, looks down local -Z) to/from an FF9 field camera (the `cam.Cam` the rest of the
kit understands). It deliberately imports NO `bpy`, so it can be unit-tested without Blender;
the `bpy` operators are thin wrappers that read/write Blender objects and call into here.

FF9 camera math (see vendor/cam.py): the engine projects with
    R_view = F * R_ff9 * F = diag(1, k, 1) * R_o'      where R_o' = F * R_ortho * F (orthonormal)
    cs = R_view * (P - C)                               cs.z > 0 in front
The orthonormal frame R_o' has the camera basis vectors as its ROWS (in FF9 world coords):
    row0 = camera right (screen +x),  row1 = camera vertical,  row2 = camera forward (depth).

Blender camera basis vectors are the COLUMNS of its world rotation matrix:
    col0 = local +X (right),  col1 = local +Y (up),  col2 = local +Z  (camera looks down -Z).

We relate the two worlds by a fixed basis map M (FF9_dir = M * Blender_dir) plus a sign for the
vertical axis; the exact constants are pinned by the offline round-trip + semantic tests.
"""

from __future__ import annotations

import math

from .vendor import bgi, cam, guide

# --- coordinate convention (pinned by tests) ---------------------------------------------
# Blender world is Z-up; FF9 world is +y up with the floor at y=0 and +z = depth toward the
# back of the screen. Map Blender (x,y,z) -> FF9 (x, z, y): Blender-up(z) -> FF9-up(y),
# Blender-forward(y) -> FF9-depth(z). M is its own inverse (a y<->z swap).
M_FB = [[1, 0, 0], [0, 0, 1], [0, 1, 0]]   # FF9_vec = M_FB * Blender_vec
M_BF = M_FB                                # inverse of a swap is itself
S_UP = 1.0                                 # sign of the camera-vertical axis (resolved by tests)

F = cam.F                                  # diag(1,-1,1)
DEFAULT_SENSOR = 384.0                     # sensor width == default FF9 range width


# --- small matrix helpers (reuse cam's) --------------------------------------------------
def _col(R, j):
    return [R[0][j], R[1][j], R[2][j]]


def _neg(v):
    return [-v[0], -v[1], -v[2]]


def _rows_to_matrix(r0, r1, r2):
    return [list(r0), list(r1), list(r2)]


def look_at_blender(eye, target, up=(0.0, 0.0, 1.0)):
    """Blender camera world-rotation (3x3, columns = local axes) looking from eye to target.

    Pure Blender convention: camera looks down local -Z, local +Y is up. Used by tests to
    construct a camera pose from first principles (no FF9 math involved).
    """
    fwd = cam.sub(target, eye)
    n = cam.norm(fwd)
    fwd = [c / n for c in fwd]                 # forward = -localZ
    right = _cross(fwd, list(up))
    rn = cam.norm(right)
    right = [c / rn for c in right]
    true_up = _cross(right, fwd)
    # columns: +X=right, +Y=up, +Z=-forward
    z = _neg(fwd)
    return [[right[0], true_up[0], z[0]],
            [right[1], true_up[1], z[1]],
            [right[2], true_up[2], z[2]]]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


# --- FOV / lens <-> H ---------------------------------------------------------------------
def lens_to_H(lens, sensor_width, range_w):
    fov_x = 2.0 * math.atan((sensor_width / 2.0) / lens)
    return (range_w / 2.0) / math.tan(fov_x / 2.0)


def H_to_lens(H, sensor_width, range_w):
    fov_x = 2.0 * math.atan((range_w / 2.0) / H)
    return (sensor_width / 2.0) / math.tan(fov_x / 2.0)


# --- the two conversions ------------------------------------------------------------------
def blender_cam_to_ff9(loc_bl, R_bl, lens, *, sensor_width=DEFAULT_SENSOR,
                       range_wh=(384, 448), depth_offset=543, viewport=(160, 224, 112, 336),
                       center_offset=(0, 0), k=cam.K_VSCALE):
    """Convert a Blender camera (world location + 3x3 world rotation + lens) to an FF9 `Cam`.

    This is the EXPORT direction. loc_bl is the camera world position (Blender coords); R_bl is
    its world rotation matrix (columns = local axes). Returns a fully-populated cam.Cam.
    """
    C = cam.mv(M_FB, list(loc_bl))
    right_bl = _col(R_bl, 0)
    up_bl = _col(R_bl, 1)
    fwd_bl = _neg(_col(R_bl, 2))                     # camera looks down -Z
    ff9_right = cam.mv(M_FB, right_bl)
    ff9_camY = [S_UP * c for c in cam.mv(M_FB, up_bl)]
    ff9_fwd = cam.mv(M_FB, fwd_bl)
    R_o = _rows_to_matrix(ff9_right, ff9_camY, ff9_fwd)   # camera basis as rows = R_o'
    R_ortho = cam.mm(F, cam.mm(R_o, F))                   # R_ortho = F * R_o' * F
    H = lens_to_H(lens, sensor_width, range_wh[0])

    c = cam.Cam()
    c.proj = int(round(H))
    c.centerOffset = list(center_offset)
    c.range = list(range_wh)
    c.depthOffset = depth_offset
    c.viewport = list(viewport)
    c.r, c.t = cam.synth_r_t(C, R_ortho, c.proj, k=k)
    return c


def ff9_cam_to_blender(c, *, sensor_width=DEFAULT_SENSOR):
    """Convert an FF9 `Cam` to Blender camera params. Returns dict(location, rotation, lens, sensor_width).

    The IMPORT direction — used to drop a correctly-posed Blender camera into the scene.
    """
    d = cam.decompose(c)
    R_ortho = d["R_ortho"]
    Cpos = d["C"]
    R_o = cam.mm(F, cam.mm(R_ortho, F))              # rows = camera basis in FF9 world
    ff9_right, ff9_camY, ff9_fwd = R_o[0], R_o[1], R_o[2]
    right_bl = cam.mv(M_BF, ff9_right)
    up_bl = cam.mv(M_BF, [S_UP * x for x in ff9_camY])
    fwd_bl = cam.mv(M_BF, ff9_fwd)
    z_bl = _neg(fwd_bl)                              # local +Z = -forward
    R_bl = [[right_bl[0], up_bl[0], z_bl[0]],
            [right_bl[1], up_bl[1], z_bl[1]],
            [right_bl[2], up_bl[2], z_bl[2]]]
    loc_bl = cam.mv(M_BF, Cpos)
    lens = H_to_lens(c.proj, sensor_width, c.range[0])
    return {"location": loc_bl, "rotation": R_bl, "lens": lens, "sensor_width": sensor_width}


# --- walkmesh ----------------------------------------------------------------------------
def blender_verts_to_ff9(world_verts):
    """Map Blender world-space vertices to FF9 world coords (list of (x, y, z))."""
    return [tuple(cam.mv(M_FB, list(v))) for v in world_verts]


def ff9_verts_to_blender(ff9_verts):
    """Inverse of blender_verts_to_ff9: FF9 world coords -> Blender world coords."""
    return [tuple(cam.mv(M_BF, list(v))) for v in ff9_verts]


# --- Phase 1: viewport guide geometry + background-layer TOML (bpy-free) ------------------
def floor_guide_geometry(c, back_canvas_y, front_canvas_y, nx=6, nz=6):
    """Reference floor grid + key markers for the PAINTED floor, in BLENDER world coords.

    The grid spans the painted-floor frame (scale-1 `to_canvas`, no character offset) so it shows
    where to paint AND where to model the walkmesh. Returns a dict:
      grid_verts : [(x,y,z)...] Blender coords, (nx+1)*(nz+1) points on the floor plane (z=0)
      grid_faces : [(i,j,k,l)...] row-major quad faces
      markers    : [(label, (x,y,z))...] Blender coords (origin / back / front / right / left)
      half_width, zb, zf : the FF9-world frame, for reference
    """
    frame = guide.frame_floor(c, back_canvas_y=back_canvas_y, front_canvas_y=front_canvas_y)
    fx, zb, zf = frame.half_width, frame.zb, frame.zf
    xs = [-fx + 2.0 * fx * i / nx for i in range(nx + 1)]
    zs = [zb + (zf - zb) * j / nz for j in range(nz + 1)]
    ff9_grid = [(x, 0.0, z) for z in zs for x in xs]            # row-major by z
    grid_verts = ff9_verts_to_blender(ff9_grid)
    w = nx + 1
    grid_faces = [(j * w + i, j * w + i + 1, j * w + i + 1 + w, j * w + i + w)
                  for j in range(nz) for i in range(nx)]
    czc = (zb + zf) / 2.0
    mk = [("origin", (0.0, 0.0, 0.0)), ("back", (0.0, 0.0, zb)), ("front", (0.0, 0.0, zf)),
          ("right", (fx, 0.0, czc)), ("left", (-fx, 0.0, czc))]
    markers = [(lab, ff9_verts_to_blender([p])[0]) for lab, p in mk]
    return {"grid_verts": grid_verts, "grid_faces": grid_faces, "markers": markers,
            "half_width": fx, "zb": zb, "zf": zf}


def floor_quad_blender(c, back_canvas_y, front_canvas_y):
    """The 4 floor-frame corners (a flat quad) in Blender world coords (BL, BR, FR, FL).

    Use this to start the walkmesh ON the painted floor so it lines up with the guide grid; the
    artist then reshapes it. Same frame as `floor_guide_geometry` (scale-1 `to_canvas`).
    """
    fr = guide.frame_floor(c, back_canvas_y=back_canvas_y, front_canvas_y=front_canvas_y)
    fx, zb, zf = fr.half_width, fr.zb, fr.zf
    return ff9_verts_to_blender([(-fx, 0, zb), (fx, 0, zb), (fx, 0, zf), (-fx, 0, zf)])


def paint_template_lines(c, back_canvas_y, front_canvas_y, scale=4, nx=8, nz=8):
    """Line segments (in PNG pixels) for a trace-over paint template, bpy-free + testable.

    Returns {"size": (W, H), "grid": [((x0,y0),(x1,y1))...], "outline": [...]} where the canvas is
    384x448 * scale and (x,y) are top-left-origin PNG pixels. The bpy operator rasterizes these.
    """
    fr = guide.frame_floor(c, back_canvas_y=back_canvas_y, front_canvas_y=front_canvas_y)
    fx, zb, zf = fr.half_width, fr.zb, fr.zf
    S = scale

    def px(x, z):
        cx, cy = cam.to_canvas((x, 0, z), c)
        return (cx * S, cy * S)

    xs = [-fx + 2.0 * fx * i / nx for i in range(nx + 1)]
    zs = [zb + (zf - zb) * j / nz for j in range(nz + 1)]
    grid = [(px(x, zb), px(x, zf)) for x in xs] + [(px(-fx, z), px(fx, z)) for z in zs]
    co = [px(*p) for p in ((-fx, zb), (fx, zb), (fx, zf), (-fx, zf))]
    outline = [(co[i], co[(i + 1) % 4]) for i in range(4)]
    return {"size": (384 * S, 448 * S), "grid": grid, "outline": outline}


def layers_to_toml(layers):
    """Emit the `[[layers]]` TOML block from an ordered list of {image, z} (dict or (image, z))."""
    blocks = []
    for L in layers:
        img = L["image"] if isinstance(L, dict) else L[0]
        z = L["z"] if isinstance(L, dict) else L[1]
        blocks.append(f'[[layers]]\nimage = "{img}"\nz = {int(z)}')
    return "\n".join(blocks)


def mesh_to_ff9_obj(world_verts, tri_faces):
    """Wavefront .obj text for a Blender mesh (world verts + triangle faces), in FF9 coords."""
    fv = blender_verts_to_ff9(world_verts)
    lines = ["# ff9mapkit walkmesh (FF9 world coords; y=0 floor)"]
    for (x, y, z) in fv:
        lines.append(f"v {x:.4f} {y:.4f} {z:.4f}")
    for (a, b, cc) in tri_faces:
        lines.append(f"f {a + 1} {b + 1} {cc + 1}")     # .obj is 1-based
    return "\n".join(lines) + "\n"


def mesh_to_bgi_bytes(world_verts, tri_faces):
    """.bgi.bytes for a Blender mesh (world verts + triangle faces)."""
    return bgi.build_flat(blender_verts_to_ff9(world_verts), list(tri_faces)).to_bytes()
