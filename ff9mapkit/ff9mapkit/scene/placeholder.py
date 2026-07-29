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


def draw_line(buf: bytearray, W: int, H: int, p0, p1, rgba, thick: int = 1) -> None:
    """Draw a thick straight line into the RGBA buffer (square brush, overwrite -- no blend)."""
    x0, y0 = p0
    x1, y1 = p1
    n = int(max(abs(x1 - x0), abs(y1 - y0)))
    r, g, b, a = rgba
    half = max(0, thick - 1)
    for i in range(n + 1):
        t = i / n if n else 0.0
        cx, cy = int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t))
        for oy in range(-half, half + 1):
            yi = cy + oy
            if not (0 <= yi < H):
                continue
            row = yi * W
            for ox in range(-half, half + 1):
                xi = cx + ox
                if 0 <= xi < W:
                    o = (row + xi) * 4
                    buf[o], buf[o + 1], buf[o + 2], buf[o + 3] = r, g, b, a


def _pt_in_tri(p, a, b, c) -> bool:
    def cr(o, u, v):
        return (u[0] - o[0]) * (v[1] - o[1]) - (u[1] - o[1]) * (v[0] - o[0])
    d1, d2, d3 = cr(p, a, b), cr(p, b, c), cr(p, c, a)
    return not (((d1 < 0) or (d2 < 0) or (d3 < 0)) and ((d1 > 0) or (d2 > 0) or (d3 > 0)))


def write_placeholders(camera: _cam.Cam, frame, back_path, floor_path, *,
                       scale: int = 4, nx: int = 12, nz: int = 12, floor_tris=None):
    """Write a solid backdrop (`back_path`, z behind) + a perspective checkerboard floor
    (`floor_path`, transparent off the floor) matched to the camera. Returns (W, H) in px.

    The floor cells are projected through ``cam.to_canvas`` (exact), so the checkerboard sits where
    the painted floor should -- the placeholder doubles as an alignment sanity check in-game.

    ``frame`` is a :class:`guide.FloorFrame`, i.e. a RECTANGLE (``zb``/``zf``/``half_width``).
    ``floor_tris`` overrides it with the real walkable footprint: a list of world-space
    ``((x,z),(x,z),(x,z))`` triangles (the same fan the walkmesh ships). Pass it whenever the floor
    is not a rectangle -- otherwise the checkerboard covers ground the player cannot reach, which
    inverts the placeholder's whole purpose. Measured on a composed room: the walkmesh occupied
    canvas rows 328-420 inside a floor painted 130-420, i.e. **68% of the checkerboard was
    unwalkable**, and the human walks into an invisible wall two thirds across it and reports a
    walkmesh bug that does not exist. With ``floor_tris`` the SILHOUETTE is exact (the triangles are
    filled first) and the checker texture rides inside it. ``frame`` may be None in that case.
    """
    W, H = int(camera.range[0] * scale), int(camera.range[1] * scale)
    back = bytearray(bytes(BACKDROP)) * (W * H)            # opaque slate, full canvas
    with open(back_path, "wb") as fh:
        fh.write(_png_rgba(W, H, back))

    def px(x, z):
        return tuple(c * scale for c in _cam.to_canvas((x, 0.0, z), camera))

    floor = bytearray(W * H * 4)                           # transparent
    if floor_tris:
        tris = [tuple(map(tuple, t)) for t in floor_tris]
        for a, b, c in tris:                               # exact silhouette first
            _fill_quad(floor, W, H, [px(*a), px(*b), px(*c), px(*c)], CHECKER_DARK)
        xs = [p[0] for t in tris for p in t]
        zs = [p[1] for t in tris for p in t]
        x0a, x1a, z0a, z1a = min(xs), max(xs), min(zs), max(zs)
        for iz in range(nz):
            for ix in range(nx):
                if (ix + iz) % 2:
                    continue                               # the dark cells are already the base fill
                cx0, cx1 = x0a + (x1a - x0a) * ix / nx, x0a + (x1a - x0a) * (ix + 1) / nx
                cz0, cz1 = z0a + (z1a - z0a) * iz / nz, z0a + (z1a - z0a) * (iz + 1) / nz
                mid = ((cx0 + cx1) / 2.0, (cz0 + cz1) / 2.0)
                if not any(_pt_in_tri(mid, *t) for t in tris):
                    continue                               # keep the checker inside the footprint
                _fill_quad(floor, W, H,
                           [px(cx0, cz0), px(cx1, cz0), px(cx1, cz1), px(cx0, cz1)], CHECKER_LIGHT)
    else:
        fx, zb, zf = frame.half_width, frame.zb, frame.zf
        for iz in range(nz):
            for ix in range(nx):
                x0, x1 = -fx + 2 * fx * ix / nx, -fx + 2 * fx * (ix + 1) / nx
                z0, z1 = zb + (zf - zb) * iz / nz, zb + (zf - zb) * (iz + 1) / nz
                _fill_quad(floor, W, H, [px(x0, z0), px(x1, z0), px(x1, z1), px(x0, z1)],
                           CHECKER_LIGHT if (ix + iz) % 2 == 0 else CHECKER_DARK)
    with open(floor_path, "wb") as fh:
        fh.write(_png_rgba(W, H, floor))
    return W, H
