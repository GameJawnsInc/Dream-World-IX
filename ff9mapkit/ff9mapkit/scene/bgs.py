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
