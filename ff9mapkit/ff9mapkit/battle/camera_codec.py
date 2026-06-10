"""Lossless codec for a battle raw17 SFXDataCamera block -- parse -> edit -> RE-SERIALIZE (with the
offset-table repack), so a minted battle can author a FROM-SCRATCH opening camera (tier ii), not just
offset the donor's keyframes in place (tier i, ``camera_data.py``).

The native plugin reads the camera block at ``camOffset`` (raw17 header's 2nd int16); ``UpdateBSC``
(SFXDataCamera.cs:131-203) is Memoria's re-serializer of that block and the exact spec this mirrors. The
block is self-contained from ``camOffset`` to end-of-file, so editing = parse the block, replace one
camera's sequence, re-serialize, splice ``raw17[:camOffset] + new_block``.

Block layout: a UInt16 set-offset table (one per camera; the first entry == table size, so cameraCount =
table[0]/2), then each camera at its set-offset = ``Flags u16`` + a UInt16 offset entry per present flag
(HAS_SEQUENCE_0/1/2=0x01/02/04, HAS_UNKNOWN=0x08, HAS_CUSTOM_POSITION=0xF0) + the pointed-at blocks. A
sequence block is a Code stream: ``frame u16`` (0=end), ``CodeFlags u16``, then conditional sub-blocks
(cameraPosition 6B, cameraMovement 4B, target 6B+4B, signing 2B, focal 4B, unknown 2/2/4/4 B).
"""
from __future__ import annotations

import struct

HAS_SEQ = (0x01, 0x02, 0x04)
HAS_UNKNOWN = 0x08
HAS_CUSTOM_POSITION = 0xF0


class CameraCodecError(ValueError):
    pass


def _u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


# ----------------------------------------------------------------- Code stream (one sequence)
def parse_sequence(b, off, end):
    """Parse a Code stream [off, end) -> list of Codes. Each Code = dict(frame, flags, block:bytes); the
    terminator is dict(frame=0). ``block`` is the raw conditional sub-block bytes (kept verbatim)."""
    codes = []
    while off < end:
        frame = _u16(b, off); off += 2
        if frame == 0:
            codes.append({"frame": 0})
            return codes, off
        flags = _u16(b, off); off += 2
        blk = off
        size = 0
        if flags & 0x03:
            size += 6                      # cameraPosition
        if flags & 0x02:
            size += 4                      # cameraMovement
        if flags & 0x04:                   # HAS_UNKNOWN_1 aborts the reader
            codes.append({"frame": frame, "flags": flags, "block": bytes(b[blk:off]), "abort": True})
            return codes, off
        if flags & 0x18:
            size += 6                      # targetPosition
        if flags & 0x10:
            size += 4                      # targetMovement
        if flags & 0x20:                   # HAS_UNKNOWN_2 aborts
            codes.append({"frame": frame, "flags": flags, "block": bytes(b[blk:off]), "abort": True})
            return codes, off
        if flags & 0x40:
            size += 2                      # signing
        if flags & 0x200:
            size += 2
        if flags & 0x400:
            size += 2
        if flags & 0x800:
            size += 4                      # focal
        if flags & 0x1000:
            size += 4
        if flags & 0x4000:
            size += 2                      # setting
        if flags & 0x8000:
            size += 4
        codes.append({"frame": frame, "flags": flags, "block": bytes(b[off:off + size])})
        off += size
    return codes, off


def serialize_sequence(codes) -> bytes:
    out = bytearray()
    for c in codes:
        out += struct.pack("<H", c["frame"])
        if c["frame"] == 0:
            break
        out += struct.pack("<H", c["flags"]) + c.get("block", b"")
        if c.get("abort"):
            break
    return bytes(out)


# ----------------------------------------------------------------- one camera + the whole block
def _parse_camera(b, base, end):
    """Parse a camera at [base, end). Returns dict(flags, sequences:[[Code]], unknown:bytes|None,
    position:bytes|None). Blocks are delimited by the offset entries + the camera end -> lossless."""
    flags = _u16(b, base)
    present = [("seq", bit) for bit in HAS_SEQ if flags & bit]
    if flags & HAS_UNKNOWN:
        present.append(("unknown", HAS_UNKNOWN))
    if flags & HAS_CUSTOM_POSITION:
        present.append(("position", HAS_CUSTOM_POSITION))
    offs = [base + _u16(b, base + 2 + i * 2) for i in range(len(present))]
    bounds = offs + [end]                  # each block runs to the next offset (or camera end)
    cam = {"flags": flags, "sequences": [], "unknown": None, "position": None}
    for i, (kind, _bit) in enumerate(present):
        lo, hi = bounds[i], bounds[i + 1]
        if kind == "seq":
            codes, _ = parse_sequence(b, lo, hi)
            cam["sequences"].append(codes)
        elif kind == "unknown":
            cam["unknown"] = bytes(b[lo:hi])
        else:
            cam["position"] = bytes(b[lo:hi])
    return cam


def parse_block(raw17):
    """(camOffset, [camera dicts]) from a raw17. Cameras keep their full structure for lossless re-serialize."""
    cam_off = struct.unpack_from("<h", raw17, 2)[0]
    if cam_off <= 0 or cam_off >= len(raw17):
        raise CameraCodecError(f"bad camOffset {cam_off}")
    table0 = _u16(raw17, cam_off)
    n = table0 // 2
    set_offs = [_u16(raw17, cam_off + 2 * i) for i in range(n)]
    cams = []
    for i in range(n):
        base = cam_off + set_offs[i]
        end = cam_off + (set_offs[i + 1] if i + 1 < n else (len(raw17) - cam_off))
        cams.append(_parse_camera(raw17, base, end))
    return cam_off, cams


def _serialize_camera(cam) -> bytes:
    flags = cam["flags"]
    blocks = []
    for bit in HAS_SEQ:
        if flags & bit:
            blocks.append(serialize_sequence(cam["sequences"][len(blocks)]))
    if flags & HAS_UNKNOWN:
        blocks.append(cam["unknown"] or b"")
    if flags & HAS_CUSTOM_POSITION:
        blocks.append(cam["position"] or b"")
    data_start = 2 + len(blocks) * 2       # flags + one UInt16 offset entry per block
    table = bytearray(len(blocks) * 2)
    body = bytearray()
    cur = data_start
    for i, blk in enumerate(blocks):
        struct.pack_into("<H", table, i * 2, cur)
        body += blk
        cur += len(blk)
    return struct.pack("<H", flags) + bytes(table) + bytes(body)


def serialize_block(cams) -> bytes:
    """Re-serialize the camera list -> block bytes (set-offset table + cameras), mirroring UpdateBSC."""
    n = len(cams)
    table = bytearray(n * 2)
    body = bytearray()
    cur = n * 2                            # cameras start right after the set-offset table
    for i, cam in enumerate(cams):
        struct.pack_into("<H", table, i * 2, cur)
        cb = _serialize_camera(cam)
        body += cb
        cur += len(cb)
    return bytes(table) + bytes(body)


def splice_block(raw17, cams) -> bytes:
    """raw17 with its camera block replaced by ``serialize_block(cams)`` (camOffset unchanged)."""
    cam_off = struct.unpack_from("<h", raw17, 2)[0]
    return bytes(raw17[:cam_off]) + serialize_block(cams)


# ----------------------------------------------------------------- from-scratch keyframe authoring (tier ii)
# Grounded in the REAL opening-camera grammar shared by every shipping battle (surveyed across EF_R007,
# BU_R002, CM_R000, BB_R000, CA_E013, AC_E031 -- see tools/dump_battle_camera.py). A real opening is:
#   1. an ESTABLISHING code @ frame 1: cameraPosition + targetPosition [+ focal], no movement -> the camera
#      is placed instantly at a start pose, looking at a fixed target.
#   2. a CHAIN of 2-4 MOVEMENT segments: each is cameraPosition + cameraMovement(duration, easing), firing
#      at prev_frame + prev_duration, so the swoop is continuous (durations seen: 15-70 frames).
#   3. a HANDOFF code (SAVE_FOR_FIXED|SETTING type=1 = SetCameraPhase(1)) a few frames after the last move
#      settles -- THIS is what flips GetCameraPhase()==1 (SFX.cs:1606) and ends the intro; without it the
#      battle hangs (root-caused via an ultracode workflow). + a trailing UNK6(0x21) marker, then END.
# We reproduce that grammar, ANCHORED on the donor's proven FIXED-CAMERA pose -- its SETTLE pose, i.e. the
# LAST cameraPosition code's pose + the LAST targetPosition (the on-fight look-at). That settle pose is what
# the battle saves via SAVE_FOR_FIXED and uses as its normal camera, so it is GUARANTEED to frame the fight.
#
# THE ORIGIN MATTERS AS MUCH AS THE MOTION. The battle centre is the world origin (0,0,0), ground at y=0;
# the default cameras (BattleMapCameraController) sit ~4500-5900 world units out -> a settle distance byte
# ~0x0a-0x17 = ~4500-5900w, so 1 distance unit ~= 450-500 world units, NOT the 63 the SFXDataCamera comment
# guesses. Crucially, the camera distance is measured FROM THE TARGET, so the target's own offset is part of
# the framing -- zeroing it (or freezing the far establishing target) mis-origins the shot. Rather than
# reverse-engineer the closed plugin's absolute scale, keyframes are expressed RELATIVE to the proven settle
# pose: yaw/pitch/roll are degree OFFSETS and `zoom` is a distance MULTIPLIER (consistent with tier i's
# camera_yaw/pitch/zoom). So offset 0 / zoom 1 == the game's normal framing -- a sweep can't be mis-origined
# or super-zoomed; it orbits/cranes around the exact shot the battle settles into.
_EASE = {"linear": 0, "in": 1, "out": 2, "sinusin": 1, "sinusout": 2}


def _split_code(flags, block):
    """Slice a donor Code's ``block`` (the bytes after frame+flags) into named sub-blocks, per the exact
    field order of SFXDataCamera.Sequence.Read. Returns {campos, cammove, tgtpos, tgtmove, focal, ...}
    with each value the verbatim bytes (or None). Lossless for the fields a normal opening uses."""
    o, p = 0, {}
    if flags & 0x03:
        p["campos"] = bytes(block[o:o + 6]); o += 6
    if flags & 0x02:
        p["cammove"] = bytes(block[o:o + 4]); o += 4
    if flags & 0x04:
        return p                                        # HAS_UNKNOWN_1 aborts the reader
    if flags & 0x18:
        p["tgtpos"] = bytes(block[o:o + 6]); o += 6
    if flags & 0x10:
        p["tgtmove"] = bytes(block[o:o + 4]); o += 4
    if flags & 0x20:
        return p
    if flags & 0x40:
        p["sign"] = bytes(block[o:o + 2]); o += 2
    if flags & 0x200:
        p["unk3"] = bytes(block[o:o + 2]); o += 2
    if flags & 0x400:
        p["unk4"] = bytes(block[o:o + 2]); o += 2
    if flags & 0x800:
        p["focal"] = bytes(block[o:o + 4]); o += 4
    if flags & 0x1000:
        p["unk5"] = bytes(block[o:o + 4]); o += 4
    if flags & 0x4000:
        p["setting"] = bytes(block[o:o + 2]); o += 2
    if flags & 0x8000:
        p["unk6"] = bytes(block[o:o + 4]); o += 4
    return p


def _pose_bytes(base6, kf):
    """A new 6-byte cameraPosition by ADJUSTING the proven settle pose ``base6`` (code,flags,pitch,ori,roll,
    dist): ``yaw``/``pitch``/``roll`` are degree OFFSETS (pitch/roll 0x80=360, orientation 0x40=360) and
    ``zoom`` is a distance MULTIPLIER. Offset 0 / zoom 1 reproduces ``base6`` byte-for-byte. The pitch/roll
    HIGH BIT (the plugin's signed-rotation convention) is preserved."""
    out = bytearray(base6)
    p_off = round(float(kf.get("pitch", 0)) / 360.0 * 0x80)
    y_off = round(float(kf.get("yaw", 0)) / 360.0 * 0x40)
    r_off = round(float(kf.get("roll", 0)) / 360.0 * 0x80)
    out[2] = (base6[2] & 0x80) | ((base6[2] + p_off) & 0x7F)
    out[3] = (base6[3] + y_off) % 0x40
    out[4] = (base6[4] & 0x80) | ((base6[4] + r_off) & 0x7F)
    out[5] = max(0, min(255, round(base6[5] * float(kf.get("zoom", 1.0)))))
    return bytes(out)


def _settle_pose(donor_codes, pos_idxs):
    """The donor's proven fixed-camera pose: the LAST cameraPosition code's campos (where the swoop ends ==
    the SAVE_FOR_FIXED snapshot the battle uses) + the LAST targetPosition in the opening (the on-fight
    look-at) + a focal. Returns (base6, target_bytes, focal_bytes)."""
    settle = _split_code(donor_codes[pos_idxs[-1]]["flags"], donor_codes[pos_idxs[-1]]["block"])
    base6 = settle.get("campos", b"\x15\x80\xfb\x19\x80\x0a")
    tgts = [_split_code(c["flags"], c["block"]).get("tgtpos") for c in donor_codes if c.get("frame")]
    tgts = [t for t in tgts if t]
    tgt = tgts[-1] if tgts else b""
    if not settle.get("focal"):                          # focal may live on the establishing code instead
        est = _split_code(donor_codes[pos_idxs[0]]["flags"], donor_codes[pos_idxs[0]]["block"])
        return base6, tgt, est.get("focal", b"")
    return base6, tgt, settle["focal"]


def build_sequence(donor_codes, keyframes, *, start_delay=1, handoff_gap=5, default_move=30):
    """Build a real-grammar opening Code list from ``keyframes`` (ordered), ANCHORED on the donor's proven
    settle pose: the FIRST keyframe is the instant START pose, each later one is a swoop segment that MOVES
    the camera there over ``move`` frames (default ``default_move``), easing ``ease`` (in|out|linear).
    Frames chain automatically. The donor's on-fight target, focal and handoff/terminator codes are kept, so
    the battle starts AND stays framed around the exact shot it settles into.

    Each keyframe ADJUSTS the settle pose: {yaw?, pitch?, roll? (degree offsets), zoom? (distance multiplier,
    default 1.0), move?, ease?}. The natural last keyframe is {} (offset 0 / zoom 1) == the game's normal
    framing. Needs >= 2 keyframes (a start + at least one move); fewer is static and belongs to tier i."""
    if len(keyframes) < 2:
        raise CameraCodecError("[[scene.camera_keyframes]] needs >= 2 keyframes (a start pose + at least one "
                               "move); for a static nudge use [scene] camera_yaw/pitch/zoom instead")
    pos_idxs = [i for i, c in enumerate(donor_codes) if c.get("frame") and (c["flags"] & 0x03)]
    if not pos_idxs:
        raise CameraCodecError("donor opening camera has no cameraPosition code to template from")
    base6, tgt, focal = _settle_pose(donor_codes, pos_idxs)
    # the donor's control/handoff codes = everything after its LAST cameraPosition code (SAVE_FIXED|SETTING
    # SetCameraPhase(1) + the UNK6 marker). Re-framed after the authored sweep settles -> battle starts.
    trailing = [c for c in donor_codes[pos_idxs[-1] + 1:] if c.get("frame")]

    out = []
    # 1) establishing code @ frame `start_delay` (== 1, like every donor): instant pose + on-fight target + focal
    f0 = 0x01 | (0x08 if tgt else 0) | (0x800 if focal else 0)
    out.append({"frame": start_delay, "flags": f0, "block": _pose_bytes(base6, keyframes[0]) + tgt + focal})
    # 2) chained movement segments (each starts where the previous ended; first starts at the establish frame)
    t = start_delay
    for kf in keyframes[1:]:
        dur = max(1, int(kf.get("move", default_move)))
        ease = _EASE.get(str(kf.get("ease", "out")).lower(), 2)
        fl = 0x03 | (0x08 if tgt else 0)               # CAMPOS+CAMMOVE (+ static on-fight TGTPOS)
        blk = _pose_bytes(base6, kf) + struct.pack("<H", dur) + bytes([ease, 0]) + tgt
        out.append({"frame": t, "flags": fl, "block": blk})
        t += dur
    # 3) handoff, re-framed just after the sweep settles (keep the donor's relative spacing)
    if trailing:
        base = trailing[0]["frame"]
        for c in trailing:
            out.append({"frame": t + handoff_gap + (c["frame"] - base), "flags": c["flags"],
                        "block": c["block"]})
    else:                                              # synthesize a minimal handoff if the donor had none
        out.append({"frame": t + handoff_gap, "flags": 0x4080, "block": b"\x01\x00"})
        out.append({"frame": t + handoff_gap + 1, "flags": 0x8000, "block": b"\x21\x00\x00\x00"})
    out.append({"frame": 0})                           # terminator
    return out


def author_opening(raw17, cam_indices, keyframes) -> bytes:
    """Replace the opening camera(s) ``cam_indices`` with a from-scratch sweep from ``keyframes`` (keeping
    each donor camera's static target, focal and handoff). Re-serializes the whole block (offset repack).
    Cameras without a usable cameraPosition opening sequence are skipped (cam[1]/[2] are often empty)."""
    if not keyframes:
        return bytes(raw17)
    cam_off, cams = parse_block(raw17)
    n = len(cams)
    authored = 0
    for idx in cam_indices:
        if not 0 <= idx < n or not cams[idx]["sequences"]:
            continue
        donor = cams[idx]["sequences"][0]
        if not any(c.get("frame") and (c["flags"] & 0x03) for c in donor):
            continue                                   # no cameraPosition to anchor on -> skip (e.g. empty default cam)
        seq = build_sequence(donor, keyframes)
        cams[idx]["sequences"] = [list(seq) for _ in cams[idx]["sequences"]]
        authored += 1
    if authored == 0:
        raise CameraCodecError(f"no opening camera among {list(cam_indices)} had a cameraPosition sequence to "
                               f"author from (this raw17 has {n} cameras); pin [scene] camera = 0")
    return splice_block(raw17, cams)
