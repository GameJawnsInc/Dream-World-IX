"""Disassemble a raw17 (.bytes) battle camera block into human-readable terms.

Faithful to SFXDataCamera.cs (Load/Sequence.Read). Decodes every camera in cameraList:
each code's frame, flags, cameraPosition (pitch/orientation/roll deg + distance world), cameraMovement
(duration/easing), targetPosition/Movement, signing, focal, setting (SetCameraPhase). This is the
"understand the base game first" tool -- run it on real donor cameras to learn the opening grammar.

Usage: py tools/dump_battle_camera.py <file.raw17.bytes> [cam_index]
"""
import struct
import sys

CF = [  # (bit, name, fixed payload size or None for special)
    (0x0001, "CAMPOS", 6),
    (0x0002, "CAMMOVE", 4),
    (0x0004, "UNK1_ABORT", 0),
    (0x0008, "TGTPOS", 6),
    (0x0010, "TGTMOVE", 4),
    (0x0020, "UNK2_ABORT", 0),
    (0x0040, "SIGN", 2),
    (0x0080, "SAVE_FIXED", 0),
    (0x0100, "UNKFLAG1", 0),
    (0x0200, "UNK3", 2),
    (0x0400, "UNK4", 2),
    (0x0800, "FOCAL", 4),
    (0x1000, "UNK5", 4),
    (0x2000, "UNKFLAG2", 0),
    (0x4000, "SETTING", 2),
    (0x8000, "UNK6", 4),
]


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def deg_pitch(v):  # 0..0x80 = 360
    return round(v / 0x80 * 360, 1)


def deg_yaw(v):    # 0..0x40 = 360
    return round(v / 0x40 * 360, 1)


def fmt_pos(b, o, label):
    code, fl, pitch, ori, roll, dist = b[o], b[o + 1], b[o + 2], b[o + 3], b[o + 4], b[o + 5]
    return (f"{label}(code={code:#04x} fl={fl:#04x} "
            f"pitch={pitch:#04x}={deg_pitch(pitch):.0f}deg ori={ori:#04x}={deg_yaw(ori):.0f}deg "
            f"roll={roll:#04x}={deg_pitch(roll):.0f}deg dist={dist:#04x}={dist*63}w)")


def fmt_move(b, o, label):
    dur = u16(b, o)
    typ = b[o + 2]
    ease = {0: "Linear", 1: "SinusIn", 2: "SinusOut"}.get(typ, f"type{typ}")
    return f"{label}(dur={dur}f {ease} unk={b[o+3]:#04x})"


def parse_codes(b, off, end):
    """Yield decoded code dicts until a 0-frame terminator or end."""
    codes = []
    while off < end:
        frame = u16(b, off); off += 2
        if frame == 0:
            codes.append({"frame": 0, "desc": "<END>"}); break
        flags = u16(b, off); off += 2
        parts = []
        aborted = False
        # order matters -- exactly as SFXDataCamera.Sequence.Read
        if flags & 0x03:
            parts.append(fmt_pos(b, off, "CAMPOS")); off += 6
        if flags & 0x02:
            parts.append(fmt_move(b, off, "CAMMOVE")); off += 4
        if flags & 0x04:
            parts.append("UNK1_ABORT"); aborted = True
        if not aborted and flags & 0x18:
            parts.append(fmt_pos(b, off, "TGTPOS")); off += 6
        if not aborted and flags & 0x10:
            parts.append(fmt_move(b, off, "TGTMOVE")); off += 4
        if not aborted and flags & 0x20:
            parts.append("UNK2_ABORT"); aborted = True
        if not aborted:
            if flags & 0x40:
                parts.append(f"SIGN({b[off]:#04x},{b[off+1]:#04x})"); off += 2
            if flags & 0x80:
                parts.append("SAVE_FIXED")
            if flags & 0x200:
                parts.append(f"UNK3({u16(b,off):#06x})"); off += 2
            if flags & 0x400:
                parts.append(f"UNK4({u16(b,off):#06x})"); off += 2
            if flags & 0x800:
                parts.append(f"FOCAL(dur={b[off]} fl={b[off+1]} dist={u16(b,off+2)})"); off += 4
            if flags & 0x1000:
                parts.append(f"UNK5({struct.unpack_from('<I',b,off)[0]:#010x})"); off += 4
            if flags & 0x4000:
                vt = b[off]
                note = "=SetCameraPhase(1)" if vt == 1 else ("=btlseq++" if vt == 2 else "")
                parts.append(f"SETTING(type={vt}{note} unk={b[off+1]:#04x})"); off += 2
            if flags & 0x8000:
                parts.append(f"UNK6({struct.unpack_from('<I',b,off)[0]:#010x})"); off += 4
        codes.append({"frame": frame, "flags": flags, "desc": "  ".join(parts), "abort": aborted})
        if aborted:
            break
    return codes, off


def dump(path, only_cam=None):
    b = open(path, "rb").read()
    seq_block_off = struct.unpack_from("<h", b, 0)[0]
    cam_off = struct.unpack_from("<h", b, 2)[0]
    print(f"== {path}")
    print(f"   len={len(b)}  seqBlockOffset={seq_block_off}  camOffset={cam_off}")
    n = u16(b, cam_off) // 2
    set_offs = [u16(b, cam_off + 2 * i) for i in range(n)]
    print(f"   cameraCount={n}  setOffsets={set_offs}")
    for i in range(n):
        if only_cam is not None and i != only_cam:
            continue
        base = cam_off + set_offs[i]
        end = cam_off + (set_offs[i + 1] if i + 1 < n else (len(b) - cam_off))
        flags = u16(b, base)
        present = []
        oo = 2
        seqs = []
        for bit, label in ((1, "SEQ0"), (2, "SEQ1"), (4, "SEQ2")):
            if flags & bit:
                seqs.append((label, base + u16(b, base + oo))); oo += 2
        has_unknown = flags & 0x08
        has_pos = flags & 0xF0
        if has_unknown:
            present.append("UNKNOWN"); oo += 2
        if has_pos:
            present.append("CUSTOM_POSITION")
        role = {0: "OPENING", 1: "DEFAULT/fixed", 2: "VICTORY"}.get(i, f"attack/cutscene[{i}]")
        print(f"\n  -- cameraList[{i}] ({role})  flags={flags:#06x}  seqs={[s[0] for s in seqs]} {present}")
        for label, so in seqs:
            codes, _ = parse_codes(b, so, end)
            print(f"     {label} @ {so} ({len(codes)} codes):")
            for c in codes:
                if c["frame"] == 0:
                    print(f"        frame={c['frame']:<4} <END>")
                else:
                    print(f"        frame={c['frame']:<4} flags={c['flags']:#06x}  {c['desc']}")


if __name__ == "__main__":
    p = sys.argv[1]
    cam = int(sys.argv[2]) if len(sys.argv) > 2 else None
    dump(p, cam)
