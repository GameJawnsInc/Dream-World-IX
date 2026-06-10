#!/usr/bin/env python3
# FF9 field .bgs (BGSCENE_DEF) binary reader -- the BASE-GAME scene container.
#
# A real field's background scene ships as <fbg>.bgs.bytes inside StreamingAssets/p0data*.bin.
# It holds the field's CAMERAS (BGCAM_DEF) + overlays + animations + lights. The kit normally
# AUTHORS pure-Memoria .bgx scenes; but to IMPORT a real field as an editable base we must READ
# its native binary .bgs. This module parses the header + the camera list (what camera import
# needs); overlay/anim parsing can be layered on later for art extraction.
#
# Layout -- verified against Memoria source AND byte-exact vs the engine's own .bgx export
# (offline p0data spike, 2026-06-04: every GRGR camera field matched the FieldCreatorScene .bgx):
#
#   BGSCENE_DEF.ExtractHeaderData (BGSCENE_DEF.cs:655), little-endian:
#     u16 sceneLength, depthBitShift, animCount, overlayCount, lightCount, cameraCount
#     u32 animOffset, overlayOffset, lightOffset, cameraOffset      # cameraOffset is ABSOLUTE
#     i16 orgZ,curZ, orgX,orgY, curX,curY, minX,maxX, minY,maxY, scrX,scrY
#   then cameraCount BGCAM_DEF blocks at cameraOffset, 52 bytes each (BGCAM_DEF.ReadData, cs:17):
#     u16 proj; i16 r[3][3]; i32 t[3]; i16 centerOffset[2]; i16 w,h;
#     i16 vrpMinX,vrpMaxX,vrpMinY,vrpMaxY; i32 depthOffset
#
# The kit's Cam stores exactly these fields (cam.Cam: proj, r[3][3], t[3], centerOffset, range=[w,h],
# viewport=[vrpMinX,vrpMaxX,vrpMinY,vrpMaxY], depthOffset), so a parsed camera drops straight into
# cam.decompose / cam.to_canvas / bgx.format_bgx_camera.
from collections import namedtuple
import struct

from .cam import Cam

_HEADER = struct.Struct("<6H4I12h")        # 6 counts (u16) + 4 offsets (u32) + 12 scene bounds (i16) = 52 B
_CAMERA = struct.Struct("<H9h3i2h2h4hi")   # one BGCAM_DEF block
HEADER_SIZE = _HEADER.size                  # 52
CAMERA_SIZE = _CAMERA.size                  # 52

BgsHeader = namedtuple(
    "BgsHeader",
    "sceneLength depthBitShift animCount overlayCount lightCount cameraCount "
    "animOffset overlayOffset lightOffset cameraOffset bounds",
)


def parse_header(data: bytes) -> BgsHeader:
    f = _HEADER.unpack_from(data, 0)
    return BgsHeader(*f[:10], bounds=tuple(f[10:22]))


def camera_from_block(buf: bytes, off: int = 0) -> Cam:
    """Decode one 52-byte BGCAM_DEF block into a kit Cam."""
    f = _CAMERA.unpack_from(buf, off)
    c = Cam()
    c.proj = f[0]
    r = f[1:10]
    c.r = [[r[0], r[1], r[2]], [r[3], r[4], r[5]], [r[6], r[7], r[8]]]
    c.t = list(f[10:13])
    c.centerOffset = list(f[13:15])
    c.range = [f[15], f[16]]
    c.viewport = list(f[17:21])            # vrpMinX, vrpMaxX, vrpMinY, vrpMaxY
    c.depthOffset = f[21]
    return c


def camera_to_block(cam: Cam) -> bytes:
    """Encode a kit Cam back into a 52-byte BGCAM_DEF block (round-trip of camera_from_block)."""
    r = cam.r
    return _CAMERA.pack(
        cam.proj,
        r[0][0], r[0][1], r[0][2], r[1][0], r[1][1], r[1][2], r[2][0], r[2][1], r[2][2],
        cam.t[0], cam.t[1], cam.t[2],
        cam.centerOffset[0], cam.centerOffset[1],
        cam.range[0], cam.range[1],
        cam.viewport[0], cam.viewport[1], cam.viewport[2], cam.viewport[3],
        cam.depthOffset,
    )


def parse_cameras(data: bytes) -> list:
    """All cameras from a .bgs byte blob, as kit Cam objects."""
    h = parse_header(data)
    return [camera_from_block(data, h.cameraOffset + i * CAMERA_SIZE) for i in range(h.cameraCount)]


# --------------------------------------------------------------------------- overlays + sprites (art)
# A field's background is a stack of OVERLAYS (depth layers); each overlay is a grid of 16-px TILES,
# each tile sampling a cell of the upscaled atlas.png. Porting BGSCENE_DEF.ExtractOverlayData/
# ExtractSpriteData + ExtractHeaderData lets us re-composite the real art offline (see scene.bgart).
_OVERLAY = struct.Struct("<I HH hhhh hhhh hh hh hh I I I I I")   # BGOVERLAY_DEF.ReadData, 56 B
HEADER12 = struct.Struct("<12h")


def _bits(v, start, n):
    return (v >> start) & ((1 << n) - 1)


class Sprite:
    __slots__ = ("offX", "offY", "depth", "trans", "alpha", "atlasX", "atlasY")

    def __init__(self, offX, offY, depth, trans, alpha, atlasX=0, atlasY=0):
        self.offX, self.offY, self.depth = offX, offY, depth
        self.trans, self.alpha = trans, alpha
        self.atlasX, self.atlasY = atlasX, atlasY


class Overlay:
    __slots__ = ("curZ", "orgZ", "orgX", "orgY", "w", "h", "spriteCount", "locOffset", "prmOffset", "sprites")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
        self.sprites = []


def parse_overlays(data: bytes):
    """(header, [Overlay]) — overlays with their tile sprites resolved to atlas grid cells.

    Sprite atlas cells follow BGSCENE_DEF's upscale layout: a global tile index laid out
    `countPerRow = atlasW // (tile_size+4)`, `atlasX = 2 + i%cpr*(tile_size+4)`, y analogous.
    `tile_size` defaults to 64 (the Steam 4x atlas); pass the real value if it differs."""
    h = parse_header(data)
    overlays = []
    off = h.overlayOffset
    for _ in range(h.overlayCount):
        f = _OVERLAY.unpack_from(data, off)
        off += _OVERLAY.size
        buf, buf2 = f[0], f[17]
        overlays.append(Overlay(
            curZ=_bits(buf, 8, 12), orgZ=_bits(buf, 20, 12),
            orgX=f[3], orgY=f[4], w=f[1], h=f[2],
            spriteCount=_bits(buf2, 16, 16), locOffset=f[18], prmOffset=f[19]))
    return h, overlays


TILE = 16     # one background tile is 16x16 logical (pre-upscale) px (BGSCENE_DEF sprite quad)


def tile_box(sprite, mnX, mnY, upscale: int = 4, tile: int = TILE):
    """The crop rectangle ``(left, top, right, bottom)`` of one tile-sprite inside its overlay's
    engine-exported ``Overlay{i}.png``.

    The ``[Export] Field=1`` dump writes each overlay as a tight composite whose pixel (0,0) is the
    overlay's MIN-offset tile (BGSCENE_DEF.cs:570-588), which is exactly where
    ``extract.compose_background`` places the whole PNG (``(sOrg+org+min(off))*upscale``, no flip), so
    a tile at ``(offX, offY)`` sits ``(offX-mnX, offY-mnY)`` tiles in -- each ``tile`` px, upscaled.
    Pure arithmetic so the per-tile occlusion split is unit-testable without art."""
    x0 = (sprite.offX - mnX) * upscale
    y0 = (sprite.offY - mnY) * upscale
    return (x0, y0, x0 + tile * upscale, y0 + tile * upscale)


def resolve_sprites(data: bytes, overlays, atlas_w: int, tile_size: int = 64):
    """Fill each overlay's .sprites (offX/offY/depth + atlas cell). Mutates in place."""
    cpr = atlas_w // (tile_size + 4)
    idx = 0
    for ov in overlays:
        alpha_trans = []
        po = ov.prmOffset
        for _ in range(ov.spriteCount):
            p1, p2 = struct.unpack_from("<II", data, po)
            po += 8
            alpha_trans.append((_bits(p1, 22, 2), _bits(p2, 28, 1)))   # alpha, trans (shader)
        lo = ov.locOffset
        for j in range(ov.spriteCount):
            (L,) = struct.unpack_from("<I", data, lo)
            lo += 4
            depth, offY, offX = _bits(L, 0, 12), _bits(L, 12, 10), _bits(L, 22, 10)
            alpha, trans = alpha_trans[j]
            ov.sprites.append(Sprite(
                offX, offY, depth, trans, alpha,
                atlasX=2 + idx % cpr * (tile_size + 4),
                atlasY=2 + idx // cpr * (tile_size + 4)))
            idx += 1
    return overlays
