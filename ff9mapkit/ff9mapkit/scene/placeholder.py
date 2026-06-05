"""Pure-stdlib PLACEHOLDER background art for a scaffolded field -- NO PIL, NO painting.

`ff9mapkit new` writes these so a fresh project BUILDS and is walkable immediately (a perspective
checkerboard floor + a solid backdrop), giving an end-to-end smoke test before any art exists. They
are obvious placeholders in-game (flat colours); the human REPLACES back.png/floor.png with real
painted art (Hard Constraint S2 -- the kit only tells you where the floor lands). Not art authoring,
just scaffolding (like the calibration grids).
"""

from __future__ import annotations

import struct
import zlib

from . import cam as _cam

BACKDROP = (45, 57, 71, 255)            # #2d3947 muted slate
CHECKER_LIGHT = (210, 170, 90, 255)     # warm tan
CHECKER_DARK = (150, 110, 55, 255)


def _png_rgba(w: int, h: int, buf: bytearray) -> bytes:
    """Encode a w*h RGBA buffer (row-major, top-down) as PNG bytes (filter 0, zlib level 6)."""
    stride = w * 4
    rows = bytearray()
    for y in range(h):
        rows.append(0)
        rows += buf[y * stride:(y + 1) * stride]

    def chunk(typ, data):
        body = typ + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 6))
            + chunk(b"IEND", b""))


def _fill_quad(buf: bytearray, W: int, H: int, pts, rgba) -> None:
    """Scanline-fill a convex quad (4 (x,y) float pixel corners) into the RGBA buffer."""
    r, g, b, a = rgba
    ys = [p[1] for p in pts]
    y0, y1 = max(0, int(min(ys))), min(H - 1, int(max(ys)))
    for y in range(y0, y1 + 1):
        yc = y + 0.5
        xs = []
        for i in range(4):
            (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % 4]
            if (ya <= yc < yb) or (yb <= yc < ya):
                xs.append(xa + (yc - ya) * (xb - xa) / (yb - ya))
        if len(xs) < 2:
            continue
        xlo, xhi = max(0, int(min(xs))), min(W - 1, int(max(xs)))
        o = (y * W + xlo) * 4
        for _ in range(xlo, xhi + 1):
            buf[o], buf[o + 1], buf[o + 2], buf[o + 3] = r, g, b, a
            o += 4


def write_placeholders(camera: _cam.Cam, frame, back_path, floor_path, *,
                       scale: int = 4, nx: int = 12, nz: int = 12):
    """Write a solid backdrop (`back_path`, z behind) + a perspective checkerboard floor
    (`floor_path`, transparent off the floor) matched to the camera/frame. Returns (W, H) in px.

    The floor cells are projected through ``cam.to_canvas`` (exact), so the checkerboard sits where
    the painted floor should -- the placeholder doubles as an alignment sanity check in-game.
    """
    W, H = int(camera.range[0] * scale), int(camera.range[1] * scale)
    back = bytearray(bytes(BACKDROP)) * (W * H)            # opaque slate, full canvas
    with open(back_path, "wb") as fh:
        fh.write(_png_rgba(W, H, back))

    floor = bytearray(W * H * 4)                           # transparent
    fx, zb, zf = frame.half_width, frame.zb, frame.zf
    for iz in range(nz):
        for ix in range(nx):
            x0, x1 = -fx + 2 * fx * ix / nx, -fx + 2 * fx * (ix + 1) / nx
            z0, z1 = zb + (zf - zb) * iz / nz, zb + (zf - zb) * (iz + 1) / nz
            pts = [tuple(c * scale for c in _cam.to_canvas((x, 0.0, z), camera))
                   for (x, z) in ((x0, z0), (x1, z0), (x1, z1), (x0, z1))]
            _fill_quad(floor, W, H, pts, CHECKER_LIGHT if (ix + iz) % 2 == 0 else CHECKER_DARK)
    with open(floor_path, "wb") as fh:
        fh.write(_png_rgba(W, H, floor))
    return W, H
