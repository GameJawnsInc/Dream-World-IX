"""Author a camera from a simple spec, frame a flat floor, and emit a paint guide.

This is the human-facing half of the scene pipeline. The kit can't paint the background
(Hard Constraint), but it CAN tell the artist *exactly* where the floor and its edges land
on the painted canvas for a chosen camera angle, and hand back the matching walkmesh corners.

  make_camera(pitch, distance, fov_x | proj, yaw)  -> a Cam (via the camera math)
  frame_floor(cam, back/front canvas rows)         -> the floor quad (world + canvas coords)
  render_paint_guide(cam, frame, png)              -> a checkerboard guide image to paint over
  walkmesh_corners(frame)                          -> 4 (x, z) corners for scene.bgi.quad()

Canvas is the painted logical 384x448 (top-left origin, Y down) with an EXACT scale-1 map
(canvasX = rawProj.x + w/2, canvasY = h/2 - rawProj.y; see :mod:`ff9mapkit.scene.cam`). The old
per-pitch sx/sy fudge (0.926/0.889) is gone -- the projection is exact at every pitch.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import cam as _cam

CANVAS_W, CANVAS_H = 384, 448
# GRGR-derived defaults that work across the real FF9 pitch range (Sessions 6-10)
DEFAULT_DEPTH_OFFSET = 543
DEFAULT_VIEWPORT = (160, 224, 112, 336)


def proj_from_fov_x(fov_x_deg: float, range_w: int = CANVAS_W) -> int:
    """Projection distance H for a horizontal FOV: H = (w/2) / tan(fov/2)."""
    return int(round((range_w / 2.0) / math.tan(math.radians(fov_x_deg) / 2.0)))


def _canvas_wh(cam: _cam.Cam) -> tuple:
    """The painted-canvas size (px) for this camera = its Range, else the 384x448 default.
    A larger-than-screen (scrolling) field has Range > screen, so the paint guide/template must be
    that full size, not the 384x448 single screen."""
    w = int(cam.range[0]) if cam.range and cam.range[0] else CANVAS_W
    h = int(cam.range[1]) if cam.range and cam.range[1] else CANVAS_H
    return (w, h)


def _height_ticks(wall_h: float) -> list:
    """Sensible labeled heights up to wall_h (quarters)."""
    return [round(wall_h * k / 4) for k in range(1, 5)]


def _height_segments(cam: _cam.Cam, frame: "FloorFrame", S: int, wall_h: float) -> list:
    """Vertical perspective guides (as colored line segments) so the artist can paint WALLS at the
    right height. A flat floor grid can't show how "up" foreshortens. World-accurate projection:
      * vertical POLES at the floor's 4 corners + back/front mid-edges (y=0 -> wall_h),
      * back-wall horizontal RINGS at each quarter-height tick,
      * the room-box TOP outline (the ceiling rectangle).
    Returns [(p0_px, p1_px, rgba), ...]; heights share the floor's world units so the scales match.
    (Height tick *labels* are omitted in the stdlib renderer -- the CLI prints the coordinates.)"""
    def pc(x, y, z):
        cx, cy = _cam.to_canvas((x, y, z), cam)
        return (cx * S, cy * S)

    (blx, _, blz), (brx, _, brz), (frx, _, frz), (flx, _, flz) = frame.corners_world
    bl, br, fr, fl = (blx, blz), (brx, brz), (frx, frz), (flx, flz)
    bm = ((blx + brx) / 2.0, blz)
    fm = ((flx + frx) / 2.0, flz)
    POLE, RING, BOX = (90, 220, 235, 255), (90, 215, 230, 200), (130, 240, 255, 255)
    segs = [(pc(x, 0, z), pc(x, wall_h, z), POLE) for (x, z) in (bl, br, fr, fl, bm, fm)]
    segs += [(pc(bl[0], h, bl[1]), pc(br[0], h, br[1]), RING) for h in _height_ticks(wall_h)]
    tops = [pc(x, wall_h, z) for (x, z) in (bl, br, fr, fl)]
    segs += [(tops[k], tops[(k + 1) % 4], BOX) for k in range(4)]
    return segs


def make_camera(pitch_deg: float, distance: float, *, fov_x_deg: float | None = None,
                proj: int | None = None, yaw_deg: float = 0.0,
                range_wh: tuple = (CANVAS_W, CANVAS_H),
                depth_offset: int = DEFAULT_DEPTH_OFFSET,
                viewport: tuple = DEFAULT_VIEWPORT,
                center_offset: tuple = (0, 0)) -> _cam.Cam:
    """Synthesize a Cam looking down at *pitch_deg* from *distance*, optional *yaw_deg*.

    Provide either ``fov_x_deg`` or ``proj`` (H). The camera ORBITS the scene centre: position at
    rot_y(yaw)·(0, D·sinθ, −D·cosθ), view rotation R = rot_x(pitch)·rot_y(−yaw), then synth_r_t.
    The post-multiply (−yaw) is required: because the projection applies R AFTER the y-flip F,
    pre-multiplying rot_y(yaw) would NOT keep the origin centred (the floor flies off-screen). This
    form keeps (0,0,0) projecting to the canvas centre at every yaw (verified).
    """
    if proj is None:
        if fov_x_deg is None:
            raise ValueError("provide either fov_x_deg or proj")
        proj = proj_from_fov_x(fov_x_deg, range_wh[0])
    th = math.radians(pitch_deg)
    Cpos = (0.0, distance * math.sin(th), -distance * math.cos(th))
    R = _cam.rot_x(pitch_deg)
    if yaw_deg:
        R = _cam.mm(R, _cam.rot_y(-yaw_deg))
        # orbit the camera position by yaw about the origin too, so it keeps looking at center
        cy, sy = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
        x, y, z = Cpos
        Cpos = (cy * x + sy * z, y, -sy * x + cy * z)
    cam = _cam.Cam()
    cam.proj = proj
    cam.centerOffset = list(center_offset)
    cam.range = list(range_wh)
    cam.depthOffset = depth_offset
    cam.viewport = list(viewport)
    cam.r, cam.t = _cam.synth_r_t(Cpos, R, proj)
    return cam


@dataclass
class FloorFrame:
    """A flat floor quad, in both world and painted-canvas coordinates."""

    zb: int           # world z of the back edge
    zf: int           # world z of the front edge
    half_width: int   # world x half-extent
    corners_world: list   # [BL, BR, FR, FL] as (x, 0, z)
    corners_canvas: list  # parallel [(cx, cy), ...]


def frame_floor(cam: _cam.Cam, *, back_canvas_y: float = 130.0, front_canvas_y: float = 420.0,
                half_width: int | None = None, back_span_px: float = 130.0) -> FloorFrame:
    """Frame a flat floor between two painted-canvas rows; auto half-width if not given.

    Raises ValueError if a requested row is above the camera's horizon (unreachable) — typically a
    too-shallow pitch. The message reports the horizon row so you can steepen the pitch or move the
    floor rows below it."""
    zb_f = _cam.solve_z_for_canvasY(cam, back_canvas_y)
    zf_f = _cam.solve_z_for_canvasY(cam, front_canvas_y)
    if zb_f is None or zf_f is None:
        hy = _cam.horizon_canvas_y(cam)
        bad = "back" if zb_f is None else "front"
        val = back_canvas_y if zb_f is None else front_canvas_y
        raise ValueError(
            f"floor {bad} edge (canvas Y={val:g}) is above the horizon for this camera "
            f"(pitch {_cam.pitch_deg(cam):.1f} deg, horizon at canvas Y~{hy:.0f}): no floor projects "
            f"there. Use a steeper pitch, or keep the floor rows below Y~{hy:.0f} (larger values).")
    zb, zf = round(zb_f), round(zf_f)
    if half_width is None:
        nb = abs(_cam.project((0, 0, zb), cam)[2])           # depth at back center
        # scale-1 map: canvas half-span = half_width * proj / depth  ->  invert for half_width
        half_width = int(round(back_span_px * nb / cam.proj))
    fx = half_width
    world = [(-fx, 0, zb), (fx, 0, zb), (fx, 0, zf), (-fx, 0, zf)]   # BL, BR, FR, FL
    canvas = [tuple(round(v, 1) for v in _cam.to_canvas(P, cam)) for P in world]
    return FloorFrame(zb, zf, fx, world, canvas)


def walkmesh_corners(frame: FloorFrame) -> list:
    """The 4 (x, z) corners for scene.bgi.quad(), ordered front-edge-first for a forward exit."""
    # bgi.quad order v0,v1,v2,v3 with diagonal v0-v2; use back-left, back-right, front-right, front-left
    return [(frame.corners_world[0][0], frame.corners_world[0][2]),
            (frame.corners_world[1][0], frame.corners_world[1][2]),
            (frame.corners_world[2][0], frame.corners_world[2][2]),
            (frame.corners_world[3][0], frame.corners_world[3][2])]


def render_paint_guide(cam: _cam.Cam, frame: FloorFrame, png_path, *, scale: int = 4,
                       nx: int = 6, nz: int = 6, wall_height: float | None = None) -> tuple:
    """Render an opaque checkerboard floor + reference cross-markers as a paint underlay (pure
    stdlib, no PIL). ``wall_height`` adds vertical height guides (poles/rings/ceiling); ``None`` =
    auto (the floor's depth), ``0`` = floor only. Coordinate values are PRINTED by the CLI, not
    drawn (stdlib has no font), so the markers are crosses without text. Returns (W, H) px."""
    from . import placeholder as _ph

    S = scale
    cw, ch = _canvas_wh(cam)
    W, H = cw * S, ch * S
    buf = bytearray(bytes((20, 22, 28, 255))) * (W * H)        # opaque dark

    def px(P):
        cx, cy = _cam.to_canvas(P, cam)
        return (cx * S, cy * S)

    fx, zb, zf = frame.half_width, frame.zb, frame.zf
    xs = [-fx + 2 * fx * i / nx for i in range(nx + 1)]
    zs = [zb + (zf - zb) * j / nz for j in range(nz + 1)]
    for j in range(nz):
        for i in range(nx):
            q = [px((xs[i], 0, zs[j])), px((xs[i + 1], 0, zs[j])),
                 px((xs[i + 1], 0, zs[j + 1])), px((xs[i], 0, zs[j + 1]))]
            _ph._fill_quad(buf, W, H, q, (90, 110, 140, 255) if (i + j) % 2 == 0 else (50, 60, 80, 255))
    edge = [px(P) for P in frame.corners_world]
    for k in range(4):
        _ph.draw_line(buf, W, H, edge[k], edge[(k + 1) % 4], (255, 180, 70, 255), 2)
    _ph.draw_line(buf, W, H, edge[0], edge[1], (255, 180, 70, 255), 3)     # back edge highlighted

    def mark(P, col):
        x, y = px(P)
        _ph.draw_line(buf, W, H, (x - 18, y), (x + 18, y), col, 2)
        _ph.draw_line(buf, W, H, (x, y - 18), (x, y + 18), col, 2)

    mark((0, 0, 0), (90, 255, 120, 255))                                   # origin
    mark((1000, 0, 0), (120, 200, 255, 255))
    mark((-1000, 0, 0), (120, 200, 255, 255))
    mark((0, 0, zb), (255, 120, 120, 255))                                 # floor back
    mark((0, 0, zf), (255, 120, 120, 255))                                 # floor front
    wall_h = abs(zb - zf) if wall_height is None else wall_height
    if wall_h > 0:
        for p0, p1, col in _height_segments(cam, frame, S, wall_h):
            _ph.draw_line(buf, W, H, p0, p1, col, max(1, S // 2))
    with open(png_path, "wb") as fh:
        fh.write(_ph._png_rgba(W, H, buf))
    return (W, H)


# --- transparent trace-over paint template (single-PNG default + opt-in per-layer PNGs) ----
_GRID_RGBA = (210, 215, 230, 90)        # faint perspective grid
_OUTLINE_RGBA = (255, 170, 60, 255)     # bright floor outline
_BORDER_RGBA = (120, 200, 255, 200)     # canvas safe-frame
# Ordered bottom -> top (the paint-app layer order), each with the manifest opacity + blurb:
PAINT_TEMPLATE_LAYERS = (
    ("grid", 0.35, "Perspective floor grid (alignment only)"),
    ("outline", 1.0, "Floor outline + canvas safe-frame (where the floor lands)"),
    ("height", 0.7, "Vertical height guides (corner poles / back rings / ceiling box)"),
)


def _draw_template_layer(buf: bytearray, W: int, H: int, layer: str, cam: _cam.Cam,
                         frame: "FloorFrame", S: int, nx: int, nz: int, wall_h: float) -> None:
    """Draw ONE named paint-template layer into ``buf`` ('grid' | 'outline' | 'height'). Shared by the
    single-PNG ``render_paint_template`` and the per-layer ``render_paint_template_layers`` so the two
    can never drift. 'outline' carries the canvas border; 'height' is the colored vertical guides."""
    from . import placeholder as _ph

    def px(P):
        cx, cy = _cam.to_canvas(P, cam)
        return (cx * S, cy * S)

    fx, zb, zf = frame.half_width, frame.zb, frame.zf
    if layer == "grid":
        xs = [-fx + 2 * fx * i / nx for i in range(nx + 1)]
        zs = [zb + (zf - zb) * j / nz for j in range(nz + 1)]
        for x in xs:
            _ph.draw_line(buf, W, H, px((x, 0, zb)), px((x, 0, zf)), _GRID_RGBA, 1)
        for z in zs:
            _ph.draw_line(buf, W, H, px((-fx, 0, z)), px((fx, 0, z)), _GRID_RGBA, 1)
    elif layer == "outline":
        edge = [px(P) for P in frame.corners_world]            # bright floor outline (back thicker)
        for k in range(4):
            _ph.draw_line(buf, W, H, edge[k], edge[(k + 1) % 4], _OUTLINE_RGBA, 2 * S)
        _ph.draw_line(buf, W, H, edge[0], edge[1], _OUTLINE_RGBA, 3 * S)
        for a, b in (((1, 1), (W - 2, 1)), ((W - 2, 1), (W - 2, H - 2)),    # canvas border
                     ((W - 2, H - 2), (1, H - 2)), ((1, H - 2), (1, 1))):
            _ph.draw_line(buf, W, H, a, b, _BORDER_RGBA, 2)
    elif layer == "height":
        if wall_h > 0:
            for p0, p1, col in _height_segments(cam, frame, S, wall_h):
                _ph.draw_line(buf, W, H, p0, p1, col, max(1, S // 2))


def render_paint_template(cam: _cam.Cam, frame: FloorFrame, png_path, *, scale: int = 4,
                          nx: int = 8, nz: int = 8, wall_height: float | None = None) -> tuple:
    """Render a TRANSPARENT trace-over paint template (canvas_w*scale x canvas_h*scale), pure stdlib.

    A transparent overlay: open it in your paint app, paint your room on layers BELOW it, then
    hide/delete this layer. Draws a faint perspective floor grid + a bright floor outline + the
    canvas border + vertical height guides. Coordinate labels are PRINTED by the CLI (no font in
    stdlib). ``render_paint_template_layers`` writes the same content as separate per-layer PNGs.
    Returns the image (w, h) in pixels.
    """
    from . import placeholder as _ph

    S = scale
    cw, ch = _canvas_wh(cam)
    W, H = cw * S, ch * S
    buf = bytearray(W * H * 4)                                  # transparent
    wall_h = abs(frame.zb - frame.zf) if wall_height is None else wall_height
    for layer, _opacity, _desc in PAINT_TEMPLATE_LAYERS:
        _draw_template_layer(buf, W, H, layer, cam, frame, S, nx, nz, wall_h)
    with open(png_path, "wb") as fh:
        fh.write(_ph._png_rgba(W, H, buf))
    return (W, H)


def render_paint_template_layers(cam: _cam.Cam, frame: FloorFrame, out_dir, *, scale: int = 4,
                                 nx: int = 8, nz: int = 8, wall_height: float | None = None,
                                 basename: str = "paint_template") -> list:
    """Write the paint template as SEPARATE transparent PNGs -- one per layer (grid / outline /
    height) -- plus a ``<basename>.manifest.json`` listing them in bottom-to-top paint order with a
    suggested opacity. Lets the artist toggle each guide independently in a paint app. The single-PNG
    ``render_paint_template`` stays the default; this is the opt-in per-layer form. Returns the list
    of written paths (the manifest last)."""
    import json
    import os

    from . import placeholder as _ph

    S = scale
    cw, ch = _canvas_wh(cam)
    W, H = cw * S, ch * S
    wall_h = abs(frame.zb - frame.zf) if wall_height is None else wall_height
    os.makedirs(out_dir, exist_ok=True)
    written, entries = [], []
    for layer, opacity, desc in PAINT_TEMPLATE_LAYERS:
        buf = bytearray(W * H * 4)
        _draw_template_layer(buf, W, H, layer, cam, frame, S, nx, nz, wall_h)
        fn = f"{basename}_{layer}.png"
        path = os.path.join(out_dir, fn)
        with open(path, "wb") as fh:
            fh.write(_ph._png_rgba(W, H, buf))
        written.append(path)
        entries.append({"file": fn, "type": layer, "opacity": opacity, "blend": "normal",
                        "description": desc})
    man = {"version": 1, "canvas_size": [W, H], "scale": S, "layers": entries}
    man_path = os.path.join(out_dir, f"{basename}.manifest.json")
    with open(man_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(man, fh, indent=2)
        fh.write("\n")
    written.append(man_path)
    return written
