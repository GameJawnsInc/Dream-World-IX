"""Author a camera from a simple spec, frame a flat floor, and emit a paint guide.

This is the human-facing half of the scene pipeline. The kit can't paint the background
(Hard Constraint), but it CAN tell the artist *exactly* where the floor and its edges land
on the painted canvas for a chosen camera angle, and hand back the matching walkmesh corners.

  make_camera(pitch, distance, fov_x | proj, yaw)  -> a Cam (via the camera math)
  frame_floor(cam, back/front canvas rows)         -> the floor quad (world + canvas coords)
  render_paint_guide(cam, frame, png)              -> a checkerboard guide image to paint over
  walkmesh_corners(frame)                          -> 4 (x, z) corners for scene.bgi.quad()

Canvas is the painted logical 384x448 (top-left origin, Y down); the calibrated map lives in
:mod:`ff9mapkit.scene.cam` (sx=0.926, sy=0.889).
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


def _draw_height_guides(dr, cam: _cam.Cam, frame: "FloorFrame", S: int, wall_h: float, fnt) -> None:
    """Vertical perspective guides so the artist can paint WALLS/objects at the right height.

    A flat floor grid can't show how "up" foreshortens. This draws, in world-accurate projection:
      * vertical POLES at the floor's 4 corners + back/front mid-edges (y=0 -> wall_h),
      * back-wall horizontal RINGS at each tick height (the grid for painting the backdrop),
      * the room-box TOP outline (the ceiling rectangle),
      * height LABELS (world units) up the back-left pole.
    Heights are in the SAME world units as the floor grid, so vertical and horizontal scale match.
    """
    def pc(x, y, z):
        cx, cy = _cam.to_canvas((x, y, z), cam)
        return (cx * S, cy * S)

    (blx, _, blz), (brx, _, brz), (frx, _, frz), (flx, _, flz) = frame.corners_world
    bl, br, fr, fl = (blx, blz), (brx, brz), (frx, frz), (flx, flz)
    bm = ((blx + brx) / 2.0, blz)        # back-mid
    fm = ((flx + frx) / 2.0, flz)        # front-mid
    ticks = _height_ticks(wall_h)
    POLE = (90, 220, 235, 235)
    RING = (90, 215, 230, 130)
    BOX = (130, 240, 255, 240)
    LAB = (160, 235, 248, 255)
    w = max(1, S // 2)

    for (x, z) in (bl, br, fr, fl, bm, fm):           # vertical poles
        dr.line([pc(x, 0, z), pc(x, wall_h, z)], fill=POLE, width=w)
    for h in ticks:                                   # back-wall horizontal rings
        dr.line([pc(bl[0], h, bl[1]), pc(br[0], h, br[1])], fill=RING, width=w)
    tops = [pc(x, wall_h, z) for (x, z) in (bl, br, fr, fl)]   # ceiling rectangle
    dr.line(tops + [tops[0]], fill=BOX, width=w)
    for h in ticks:                                   # height labels up the back-left pole
        x, y = pc(bl[0], h, bl[1])
        dr.text((x - 11 * S, y - 7), f"{int(h)}", fill=LAB, font=fnt,
                stroke_width=max(1, S // 3), stroke_fill=(0, 0, 0, 210))


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
                       nx: int = 6, nz: int = 6, wall_height: float | None = None) -> None:
    """Render a checkerboard floor + reference markers onto the canvas, as a paint underlay.

    ``wall_height`` adds vertical height guides (poles/rings/ceiling) so walls can be painted in
    correct perspective; ``None`` = auto (the floor's depth), ``0`` = floor only."""
    from PIL import Image, ImageDraw, ImageFont

    S = scale
    cw, ch = _canvas_wh(cam)
    img = Image.new("RGB", (cw * S, ch * S), (20, 22, 28))
    dr = ImageDraw.Draw(img, "RGBA")

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
            dr.polygon(q, fill=((90, 110, 140, 200) if (i + j) % 2 == 0 else (50, 60, 80, 200)))
    edge = [px(P) for P in frame.corners_world]
    dr.polygon(edge, outline=(255, 180, 70, 255))
    dr.line([edge[0], edge[1]], fill=(255, 180, 70, 255), width=3)   # back edge highlighted
    try:
        fnt = ImageFont.truetype("arial.ttf", 30)
    except OSError:
        fnt = ImageFont.load_default()

    def mark(P, col, lab):
        x, y = px(P)
        r = 9
        dr.ellipse([x - r, y - r, x + r, y + r], fill=col)
        dr.line([x - 18, y, x + 18, y], fill=col, width=2)
        dr.line([x, y - 18, x, y + 18], fill=col, width=2)
        dr.text((x + 14, y - 34), lab, fill=col, font=fnt)

    mark((0, 0, 0), (90, 255, 120), "(0,0,0)")
    mark((1000, 0, 0), (120, 200, 255), "(1000,0,0)")
    mark((-1000, 0, 0), (120, 200, 255), "(-1000,0,0)")
    mark((0, 0, zb), (255, 120, 120), f"back z={zb}")
    mark((0, 0, zf), (255, 120, 120), f"front z={zf}")
    wall_h = abs(zb - zf) if wall_height is None else wall_height
    if wall_h > 0:
        _draw_height_guides(dr, cam, frame, S, wall_h, fnt)
    img.save(png_path)


def render_paint_template(cam: _cam.Cam, frame: FloorFrame, png_path, *, scale: int = 4,
                          nx: int = 8, nz: int = 8, wall_height: float | None = None) -> tuple:
    """Render a TRANSPARENT trace-over paint template (canvas_w*scale x canvas_h*scale).

    Unlike render_paint_guide (an opaque calibration checkerboard), this is a transparent overlay:
    open it in your paint app, paint your room on layers BELOW it, then hide/delete this guide layer.
    Draws a faint perspective floor grid + a bright floor outline + the canvas border + labels.
    Returns the image (w, h) in pixels.
    """
    from PIL import Image, ImageDraw, ImageFont

    S = scale
    cw, ch = _canvas_wh(cam)
    W, H = cw * S, ch * S
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img, "RGBA")

    def px(P):
        cx, cy = _cam.to_canvas(P, cam)
        return (cx * S, cy * S)

    fx, zb, zf = frame.half_width, frame.zb, frame.zf
    xs = [-fx + 2 * fx * i / nx for i in range(nx + 1)]
    zs = [zb + (zf - zb) * j / nz for j in range(nz + 1)]
    GRID = (210, 215, 230, 70)                              # faint perspective grid
    for x in xs:
        dr.line([px((x, 0, zb)), px((x, 0, zf))], fill=GRID, width=1)
    for z in zs:
        dr.line([px((-fx, 0, z)), px((fx, 0, z))], fill=GRID, width=1)
    # bright floor outline (back edge thicker)
    edge = [px(P) for P in frame.corners_world]
    dr.line(edge + [edge[0]], fill=(255, 170, 60, 220), width=2 * S)
    dr.line([edge[0], edge[1]], fill=(255, 170, 60, 255), width=3 * S)
    # canvas border (the full paint area)
    dr.rectangle([1, 1, W - 2, H - 2], outline=(120, 200, 255, 160), width=2)
    try:
        fnt = ImageFont.truetype("arial.ttf", 12 * S)
    except OSError:
        fnt = ImageFont.load_default()

    def label(P, txt, col):
        x, y = px(P)
        dr.text((x + 6, y - 8 * S), txt, fill=col, font=fnt,
                stroke_width=max(1, S // 2), stroke_fill=(0, 0, 0, 200))

    wall_h = abs(zb - zf) if wall_height is None else wall_height
    if wall_h > 0:
        _draw_height_guides(dr, cam, frame, S, wall_h, fnt)
    label((0, 0, zb), "FLOOR BACK", (255, 170, 60, 255))
    label((0, 0, zf), "FLOOR FRONT", (255, 170, 60, 255))
    label((0, 0, (zb + zf) / 2), "floor center", (90, 255, 120, 255))
    dr.text((10, 10), f"paint canvas {W}x{H} (logical {cw}x{ch})  -  trace UNDER this layer",
            fill=(120, 200, 255, 230), font=fnt, stroke_width=max(1, S // 2), stroke_fill=(0, 0, 0, 220))
    img.save(png_path)
    return (W, H)
