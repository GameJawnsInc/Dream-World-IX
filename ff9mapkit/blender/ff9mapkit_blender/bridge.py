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
                       center_offset=(0, 0), k=cam.K_VSCALE, window_width=None):
    """Convert a Blender camera (world location + 3x3 world rotation + lens) to an FF9 `Cam`.

    This is the EXPORT direction. loc_bl is the camera world position (Blender coords); R_bl is
    its world rotation matrix (columns = local axes). Returns a fully-populated cam.Cam.

    ``window_width`` (default = ``range_wh[0]``) is the canvas width the camera's FOV/focal is
    measured against. For a SCROLLING field the painting (``range_wh[0]``) is wider than the
    visible screen, so pass ``window_width=384`` to keep the focal length normal.
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
    H = lens_to_H(lens, sensor_width, range_wh[0] if window_width is None else window_width)

    c = cam.Cam()
    c.proj = int(round(H))
    c.centerOffset = list(center_offset)
    c.range = list(range_wh)
    c.depthOffset = depth_offset
    c.viewport = list(viewport)
    c.r, c.t = cam.synth_r_t(C, R_ortho, c.proj, k=k)
    return c


def ff9_cam_to_blender(c, *, sensor_width=DEFAULT_SENSOR, window_width=None):
    """Convert an FF9 `Cam` to Blender camera params. Returns dict(location, rotation, lens, sensor_width).

    The IMPORT direction — used to drop a correctly-posed Blender camera into the scene.
    ``window_width`` (default = ``c.range[0]``) is the canvas width the FOV is measured against;
    pass ``384`` for a scrolling camera so the Blender lens encodes the visible-screen FOV.
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
    lens = H_to_lens(c.proj, sensor_width, c.range[0] if window_width is None else window_width)
    return {"location": loc_bl, "rotation": R_bl, "lens": lens, "sensor_width": sensor_width}


# --- walkmesh ----------------------------------------------------------------------------
def blender_verts_to_ff9(world_verts):
    """Map Blender world-space vertices to FF9 world coords (list of (x, y, z))."""
    return [tuple(cam.mv(M_FB, list(v))) for v in world_verts]


def ff9_verts_to_blender(ff9_verts):
    """Inverse of blender_verts_to_ff9: FF9 world coords -> Blender world coords."""
    return [tuple(cam.mv(M_BF, list(v))) for v in ff9_verts]


def walkmesh_frame_offset(bgi_bytes):
    """(dx,dy,dz) to put an IMPORTED real walkmesh into the world (camera/art/engine) frame =
    its orgPos (verts are corner-origin; world_vert = vert + orgPos). Content placed on the shifted
    walkmesh is already in the engine's frame, so it exports with no undo."""
    wm = bgi.BgiWalkmesh.from_bytes(bgi_bytes)
    return cam.walkmesh_world_offset((wm.orgPos.x, wm.orgPos.y, wm.orgPos.z))


def _blender_pixel(P_bl, b, res, off=(0.0, 0.0, 0.0)):
    """Blender's pinhole projection (sensor_fit=HORIZONTAL) of a Blender-world point -> (px,py)."""
    L, R, f, sw = b["location"], b["rotation"], b["lens"], b["sensor_width"]
    rx, ry = res
    rel = [P_bl[i] + off[i] - L[i] for i in range(3)]
    xc = sum(rel[i] * R[i][0] for i in range(3))     # camera basis = COLUMNS of R (right/up/+Z=back)
    yc = sum(rel[i] * R[i][1] for i in range(3))
    zc = sum(rel[i] * R[i][2] for i in range(3))
    if -zc <= 1e-6:
        return None
    tan_x = (sw / 2.0) / f
    tan_y = tan_x * (ry / rx)
    return (((xc / -zc) / tan_x * 0.5 + 0.5) * rx, (0.5 - (yc / -zc) / tan_y * 0.5) * ry)


def walkmesh_view_offset(bgi_bytes, c):
    """Per-camera 3D Blender nudge (the 3D-char-vs-2D-BG residual): Blender's pinhole projection of
    the imported walkmesh vs FF9's EXACT 2D-BG projection (cam.to_canvas, which the footprint nails).
    Returned as a Blender offset D; the import applies it as `camera.location -= D` so the walkmesh +
    content stay in the raw engine frame (content unaffected -- only the VIEW shifts). Fit on the
    floor verts by coordinate descent. (GLGV head-on -> ~+42 height; tilted cams -> height+depth.)"""
    import statistics
    wm = bgi.BgiWalkmesh.from_bytes(bgi_bytes)
    ox, oy, oz = cam.walkmesh_world_offset((wm.orgPos.x, wm.orgPos.y, wm.orgPos.z))
    med = statistics.median([v.y for v in wm.verts])         # main walkable surface
    floor = [(v.x + ox, v.y + oy, v.z + oz) for v in wm.verts if abs(v.y - med) < 60]
    if not floor:
        return (0.0, 0.0, 0.0)
    scrolling = c.range[0] > 384 or c.range[1] > 448
    b = ff9_cam_to_blender(c, sensor_width=float(c.range[0])) if scrolling else ff9_cam_to_blender(c)
    res = (c.range[0], c.range[1])
    floor_bl = [ff9_verts_to_blender([P])[0] for P in floor]
    gte = [cam.to_canvas(P, c) for P in floor]

    def cost(D):
        s = 0.0
        for Pbl, (gx, gy) in zip(floor_bl, gte):
            bp = _blender_pixel(Pbl, b, res, D)
            if bp is None:
                return 1e18
            s += (gx - bp[0]) ** 2 + (gy - bp[1]) ** 2
        return s

    D = [0.0, 0.0, 0.0]
    step = 64.0
    for _ in range(60):
        improved = False
        for i in range(3):
            for s in (step, -step):
                cand = D[:]
                cand[i] += s
                if cost(cand) < cost(D):
                    D = cand
                    improved = True
        if not improved:
            step /= 2.0
            if step < 0.05:
                break
    return tuple(D)


def bgi_walkmesh_to_blender(bgi_bytes, offset=(0, 0, 0)):
    """Parse a .bgi walkmesh -> (blender_verts, faces) for an editable Blender mesh.

    Verts map FF9 (x, y~0, z) -> Blender via ff9_verts_to_blender; faces are each triangle's 3
    vertex indices. Round-trips with blender_verts_to_ff9 (tested). `offset=(dx,dy,dz)` shifts verts
    in FF9 coords before conversion: for an IMPORTED real field pass walkmesh_frame_offset(bgi_bytes)
    (= orgPos) so the corner-origin walkmesh lands in world (where the camera + art live); kit-built
    walkmeshes are already world, so the default 0 leaves them untouched. The walkmesh may extend
    past the screen edges (tunnels) -- that's correct."""
    wm = bgi.BgiWalkmesh.from_bytes(bgi_bytes)
    ox, oy, oz = offset
    ff9 = [(v.x + ox, v.y + oy, v.z + oz) for v in wm.verts]
    faces = [tuple(t.vtx) for t in wm.tris]
    return ff9_verts_to_blender(ff9), faces


# --- floor framing + vertical height guides (scrolling-aware) -----------------------------
SCREEN_W = 384                              # visible field width; a wider painting scrolls


def scroll_floor_frame(c, back_canvas_y, front_canvas_y, margin_px=24):
    """frame_floor whose half-width is solved so the FRONT row spans the (wide) canvas edge to edge."""
    zf = cam.solve_z_for_canvasY(c, front_canvas_y)
    target = c.range[0] - margin_px
    lo, hi = 0.0, 40000.0
    flo = cam.to_canvas((lo, 0, zf), c)[0] - target
    for _ in range(80):
        m = 0.5 * (lo + hi)
        fm = cam.to_canvas((m, 0, zf), c)[0] - target
        if abs(fm) < 0.01:
            break
        if (fm > 0) == (flo > 0):
            lo, flo = m, fm
        else:
            hi = m
    hw = max(1, round(0.5 * (lo + hi)))
    return guide.frame_floor(c, back_canvas_y=back_canvas_y, front_canvas_y=front_canvas_y,
                             half_width=hw)


def _floor_frame(c, back_canvas_y, front_canvas_y):
    """Frame the floor; for a wider-than-screen (scrolling) camera, FILL the wide canvas width."""
    if c.range and c.range[0] > SCREEN_W:
        return scroll_floor_frame(c, back_canvas_y, front_canvas_y)
    return guide.frame_floor(c, back_canvas_y=back_canvas_y, front_canvas_y=front_canvas_y)


def _grid_nx(c, nx):
    rw = c.range[0] if c.range and c.range[0] else SCREEN_W
    return max(nx, round(nx * rw / SCREEN_W))


def _height_segments(c, frame, S, wall_h):
    """Line segments (PNG px) for vertical perspective guides: poles at the floor corners/mid-edges,
    back-wall rings at quarter heights, and the room-box (ceiling) outline. World-accurate."""
    def px(x, y, z):
        cx, cy = cam.to_canvas((x, y, z), c)
        return (cx * S, cy * S)
    (blx, _a, blz), (brx, _b, brz), (frx, _cc, frz), (flx, _d, flz) = frame.corners_world
    bl, br, fr, fl = (blx, blz), (brx, brz), (frx, frz), (flx, flz)
    bm = ((blx + brx) / 2.0, blz)
    fm = ((flx + frx) / 2.0, flz)
    ticks = [wall_h * k / 4.0 for k in range(1, 5)]
    segs = [(px(x, 0, z), px(x, wall_h, z)) for (x, z) in (bl, br, fr, fl, bm, fm)]   # poles
    segs += [(px(bl[0], h, bl[1]), px(br[0], h, br[1])) for h in ticks]               # back rings
    tops = [px(x, wall_h, z) for (x, z) in (bl, br, fr, fl)]                           # ceiling box
    segs += [(tops[i], tops[(i + 1) % 4]) for i in range(4)]
    return segs


def _height_wireframe_blender(frame, wall_h):
    """Vertical-guide wireframe in BLENDER coords: poles at floor corners/mid-edges + ceiling box.
    Returns (verts, edges) for a viewport wireframe object so walls can be modelled/painted in 3D."""
    (blx, _a, blz), (brx, _b, brz), (frx, _cc, frz), (flx, _d, flz) = frame.corners_world
    posts = [(blx, blz), (brx, brz), (frx, frz), (flx, flz),
             ((blx + brx) / 2.0, blz), ((flx + frx) / 2.0, flz)]
    ff9 = []
    for (x, z) in posts:                       # base + top of each pole
        ff9 += [(x, 0.0, z), (x, wall_h, z)]
    verts = ff9_verts_to_blender(ff9)
    edges = [(2 * i, 2 * i + 1) for i in range(len(posts))]      # the poles
    tops = [1, 3, 5, 7]                                          # bl/br/fr/fl tops
    edges += [(tops[i], tops[(i + 1) % 4]) for i in range(4)]    # ceiling box
    return verts, edges


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
    frame = _floor_frame(c, back_canvas_y, front_canvas_y)
    nx = _grid_nx(c, nx)
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
    wall_verts, wall_edges = _height_wireframe_blender(frame, abs(zb - zf))   # vertical height guides
    return {"grid_verts": grid_verts, "grid_faces": grid_faces, "markers": markers,
            "wall_verts": wall_verts, "wall_edges": wall_edges,
            "half_width": fx, "zb": zb, "zf": zf}


def floor_quad_blender(c, back_canvas_y, front_canvas_y):
    """The 4 floor-frame corners (a flat quad) in Blender world coords (BL, BR, FR, FL).

    Use this to start the walkmesh ON the painted floor so it lines up with the guide grid; the
    artist then reshapes it. Same frame as `floor_guide_geometry` (scale-1 `to_canvas`).
    """
    fr = _floor_frame(c, back_canvas_y, front_canvas_y)
    fx, zb, zf = fr.half_width, fr.zb, fr.zf
    return ff9_verts_to_blender([(-fx, 0, zb), (fx, 0, zb), (fx, 0, zf), (-fx, 0, zf)])


def paint_template_lines(c, back_canvas_y, front_canvas_y, scale=4, nx=8, nz=8):
    """Line segments (in PNG pixels) for a trace-over paint template, bpy-free + testable.

    Returns {"size": (W, H), "grid": [...], "outline": [...], "height": [...]} where the canvas is
    the camera's Range * scale (the FULL painting for a scrolling field) and (x,y) are top-left-origin
    PNG pixels. ``height`` is the vertical perspective guides (poles/rings/ceiling). The bpy operator
    rasterizes these. The floor fills the wide canvas for a scrolling camera.
    """
    fr = _floor_frame(c, back_canvas_y, front_canvas_y)
    fx, zb, zf = fr.half_width, fr.zb, fr.zf
    S = scale
    nx = _grid_nx(c, nx)
    rw = c.range[0] if c.range and c.range[0] else SCREEN_W
    rh = c.range[1] if c.range and c.range[1] else 448

    def px(x, z):
        cx, cy = cam.to_canvas((x, 0, z), c)
        return (cx * S, cy * S)

    xs = [-fx + 2.0 * fx * i / nx for i in range(nx + 1)]
    zs = [zb + (zf - zb) * j / nz for j in range(nz + 1)]
    grid = [(px(x, zb), px(x, zf)) for x in xs] + [(px(-fx, z), px(fx, z)) for z in zs]
    co = [px(*p) for p in ((-fx, zb), (fx, zb), (fx, zf), (-fx, zf))]
    outline = [(co[i], co[(i + 1) % 4]) for i in range(4)]
    height = _height_segments(c, fr, S, abs(zb - zf))
    return {"size": (rw * S, rh * S), "grid": grid, "outline": outline, "height": height}


def layers_to_toml(layers):
    """Emit the `[[layers]]` TOML block from an ordered list of {image, z} (dict or (image, z))."""
    blocks = []
    for L in layers:
        img = L["image"] if isinstance(L, dict) else L[0]
        z = L["z"] if isinstance(L, dict) else L[1]
        blocks.append(f'[[layers]]\nimage = "{img}"\nz = {int(z)}')
    return "\n".join(blocks)


# --- Phase 2: content markers (NPC / gateway / player spawn) -> TOML ----------------------
def _toml_str(s):
    """A TOML basic-string literal with the special characters escaped."""
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
    return f'"{s}"'


def marker_floor_pos(world_loc):
    """Blender world location of a floor marker -> FF9 (x, z) ints (FF9 y, the height, is dropped)."""
    fx, _fy, fz = blender_verts_to_ff9([list(world_loc)])[0]
    return (int(round(fx)), int(round(fz)))


def npcs_to_toml(npcs):
    """`[[npc]]` blocks from dicts: {pos:(x,z), name?, preset?, model?, animset?, anims?,
    dialogue?, text_id?}. ``pos`` is required; ``preset`` (e.g. "vivi") OR model/animset/anims."""
    blocks = []
    for n in npcs:
        L = ["[[npc]]"]
        if n.get("name"):
            L.append(f"name = {_toml_str(n['name'])}")
        if n.get("preset"):
            L.append(f"preset = {_toml_str(n['preset'])}")
        else:
            if n.get("model") is not None:
                L.append(f"model = {int(n['model'])}")
            if n.get("animset") is not None:
                L.append(f"animset = {int(n['animset'])}")
            if n.get("anims"):
                L.append("anims = [" + ", ".join(str(int(a)) for a in n["anims"]) + "]")
        L.append(f"pos = [{int(n['pos'][0])}, {int(n['pos'][1])}]")
        if n.get("dialogue"):
            L.append(f"dialogue = {_toml_str(n['dialogue'])}")
        if n.get("text_id") is not None:
            L.append(f"text_id = {int(n['text_id'])}")
        blocks.append("\n".join(L))
    return "\n\n".join(blocks)


def gateways_to_toml(gateways):
    """`[[gateway]]` blocks from dicts: {to, entrance?, zone:[(x,z) x4]}. ``zone`` is the 4 floor
    corners; point ORDER sets the walk-out direction (the q0->q1 edge is walked across on exit)."""
    blocks = []
    for g in gateways:
        zone = ", ".join(f"[{int(x)}, {int(z)}]" for (x, z) in g["zone"])
        L = ["[[gateway]]", f"to = {int(g['to'])}", f"entrance = {int(g.get('entrance', 0))}",
             f"zone = [{zone}]"]
        blocks.append("\n".join(L))
    return "\n\n".join(blocks)


def player_to_toml(spawn):
    """`[player]` block. ``spawn`` is (x, z)."""
    return f"[player]\nspawn = [{int(spawn[0])}, {int(spawn[1])}]"


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
