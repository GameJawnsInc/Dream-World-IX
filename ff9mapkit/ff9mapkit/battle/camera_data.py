"""In-place tweaks to a minted battle's OPENING camera (raw17 SFXDataCamera) -- yaw / pitch / zoom.

The native FF9SpecialEffectPlugin.dll reads the raw17 camera keyframes directly (it's a data consumer, not
a wall -- see project_ff9_battle_backgrounds). The opening shot is ``cameraList[CameraNo]`` where CameraNo =
the raw16 pattern ``Camera`` byte (0-2; random if >=3). This rotates/tilts/zooms that opening sweep by
adding a constant offset to every ``cameraPosition`` spherical coord IN PLACE -- no byte-count change, so no
camera offset-table repack (full keyframe authoring, which CAN change lengths, is a separate tier). Only
``cameraPosition`` (the camera's own position) is changed, not the target, so the battle stays framed.

raw17 camera format: header ``int16 seqBlockOffset; int16 camOffset``; at ``camOffset`` a UInt16 set-offset
table (one per camera); each camera = ``Flags u16`` + per-flag sequence-offset table + a Code stream
(``frame u16`` [0=end], ``CodeFlags u16``, then ``cameraPosition``[code,flags,PITCH,ORIENTATION,roll,DIST]
6B, ``cameraMovement`` 4B, target 6B+4B, ...). pitch/roll 0-0x80 = 360deg; orientation 0-0x40 = 360deg.
"""
from __future__ import annotations

import struct

_PITCH_FULL = 0x80     # pitch/roll: 0..0x80 = 360 degrees
_YAW_FULL = 0x40       # orientation: 0..0x40 = 360 degrees


class CameraEditError(ValueError):
    pass


def _u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def camera_count(raw17) -> int:
    cam_off = struct.unpack_from("<h", raw17, 2)[0]
    return _u16(raw17, cam_off) // 2


def _campos_fields(raw17, cam_index):
    """Yield (pitch_off, orientation_off, distance_off) for every cameraPosition in cameraList[cam_index]."""
    cam_off = struct.unpack_from("<h", raw17, 2)[0]
    n = _u16(raw17, cam_off) // 2
    if not 0 <= cam_index < n:
        return
    base = cam_off + _u16(raw17, cam_off + 2 * cam_index)
    flags = _u16(raw17, base)
    seqs, oo = [], 2
    for bit in (1, 2, 4):                              # HAS_SEQUENCE_0/1/2
        if flags & bit:
            seqs.append(base + _u16(raw17, base + oo)); oo += 2
    for so in seqs:
        off = so
        while True:
            frame = _u16(raw17, off); off += 2
            if frame == 0:
                break
            fl = _u16(raw17, off); off += 2
            if fl & 3:                                 # HAS_CAMERA_POSITION (6B): code,flags,pitch,ori,roll,dist
                yield (off + 2, off + 3, off + 5); off += 6
            if fl & 2:
                off += 4                               # cameraMovement
            if fl & 4:
                break                                  # HAS_UNKNOWN_1 aborts
            if fl & 0x18:
                off += 6                               # targetPosition
            if fl & 0x10:
                off += 4                               # targetMovement
            if fl & 0x20:
                break
            if fl & 0x40:
                off += 2                               # signing
            if fl & 0x200:
                off += 2
            if fl & 0x400:
                off += 2
            if fl & 0x800:
                off += 4                               # focal
            if fl & 0x1000:
                off += 4
            if fl & 0x4000:
                off += 2                               # setting
            if fl & 0x8000:
                off += 4


def tweak_opening(raw17, cam_indices, *, yaw_deg=0.0, pitch_deg=0.0, zoom=1.0) -> bytes:
    """Rotate (yaw_deg around the target), tilt (pitch_deg), and/or zoom (distance x ``zoom``) the opening
    camera(s) ``cam_indices`` in place. Returns new raw17 bytes (same length). Pure byte edit, no repack."""
    if zoom <= 0:
        raise CameraEditError(f"camera_zoom {zoom} must be > 0")
    b = bytearray(raw17)
    dyaw = round(yaw_deg / 360.0 * _YAW_FULL)
    dpitch = round(pitch_deg / 360.0 * _PITCH_FULL)
    touched = 0
    for idx in cam_indices:
        for p_off, o_off, d_off in _campos_fields(b, idx):
            if dpitch:
                b[p_off] = (b[p_off] + dpitch) % _PITCH_FULL
            if dyaw:
                b[o_off] = (b[o_off] + dyaw) % _YAW_FULL
            if zoom != 1.0:
                b[d_off] = max(0, min(255, round(b[d_off] * zoom)))
            touched += 1
    if touched == 0:
        raise CameraEditError(f"no cameraPosition keyframes found in cameras {list(cam_indices)} "
                              f"(this raw17 has {camera_count(raw17)} cameras)")
    return bytes(b)


def opening_indices(camera_selector) -> list:
    """Which cameraList indices a tweak targets. A pinned ``[scene] camera`` 0-2 -> just that one; otherwise
    (unset / >=3 random) -> all three possible openings [0,1,2] so whichever the engine rolls is tweaked."""
    if isinstance(camera_selector, int) and 0 <= camera_selector < 3:
        return [camera_selector]
    return [0, 1, 2]
