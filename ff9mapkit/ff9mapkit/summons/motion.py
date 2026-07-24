"""Offline decoder for a summon creature's motion clips + the PSX Euler rotation math.

Committable, pure decode/logic code (no game bytes embedded, nothing written). It reads a caller-supplied
stock ``ef###.bytes`` blob (via ``summons.container``) and turns each motion clip into per-frame, per-node
12-bit Euler angles + a root translation, and builds/decomposes the 3x3 rotation exactly as the plugin
does -- the forward math for an offline pose and the closed-form inverse the DCC->clip exporter needs.

Two halves:

  * THE CLIP DECODE (M5 / FORMAT.md §2.4). A clip is a 0x14-byte header + a coarse rotation-key table
    (1 byte/frame per animated axis) + an optional fine nibble table (2 frames/byte) + a root-translation
    track. Rotation angle = ``(coarse << 4) | fine``, 4096 units per turn -- one sample per rendered
    frame, no interpolation. The decode logic is the proven ``transplant_spike.py`` decode.

  * THE ROTATION MATH (EULER.md §1, CONFIRMED two independent ways). ``build_rotation`` is the exact psyq
    RotMatrix chain ``R = Rz(az) @ Ry(ay) @ Rx(ax)`` with STANDARD cos/sin (cos on the diagonal), angles
    scaled ``2*pi/4096``, PRE-multiplied, no transpose. ``decompose`` is the closed-form inverse (with the
    gimbal-lock fold) that round-trips ``build_rotation`` to float precision.

Angles are periodic mod 4096, so ``build_rotation`` accepts any integer; every 12-bit value splits into the
on-disk two-stream form via ``split_angle`` (``coarse = (v>>4)&0xFF``, ``fine = v & 0xF``).

Self-validation: ``validate(blob)`` (and the CLI ``py -m ff9mapkit.summons.motion <ef.bytes>``) decodes
every clip, checks each tiles its region exactly (0 gaps/overlaps within 4-byte alignment) and that every
decoded ``(ax,ay,az)`` triple round-trips ``build_rotation ∘ decompose`` to float precision.
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from typing import List, Optional, Tuple

from . import container as _container

# 4096 == one turn (PSX fixed-point angle; RotMatrix scales a movsx'd s16 by exactly this, fn 0x37a0).
UNITS_PER_TURN = 4096
TWO_PI_OVER_4096 = 2.0 * math.pi / UNITS_PER_TURN

Mat3 = Tuple[Tuple[float, float, float], ...]

__all__ = [
    "UNITS_PER_TURN", "TWO_PI_OVER_4096",
    "Clip", "read_clip_header", "decode_root_translation", "decode_rotation",
    "build_rotation", "decompose", "split_angle", "combine_angle", "signed12",
    "ClipValidation", "validate", "validate_file",
]


# ======================================================================= rotation math (EULER.md §1)
def _axis_cos_sin(a: float) -> Tuple[float, float]:
    r = a * TWO_PI_OVER_4096
    return math.cos(r), math.sin(r)                     # COS on the diagonal, SIN off-diagonal (verified)


def _mat3_mul(A: Mat3, B: Mat3) -> Mat3:
    return tuple(tuple(sum(A[r][k] * B[k][c] for k in range(3)) for c in range(3)) for r in range(3))


def build_rotation(ax: int, ay: int, az: int) -> Mat3:
    """Build the node's 3x3 from its three 12-bit Euler angles, EXACTLY as the DLL does (EULER.md §1.1):
    ``R = Rz(az) @ Ry(ay) @ Rx(ax)``, standard per-axis matrices (cos on the diagonal), angles scaled
    ``2*pi/4096``, PRE-multiplied (each new axis on the left), no transpose. Angles are periodic mod 4096,
    so any integer is accepted."""
    cx, sx = _axis_cos_sin(ax)
    cy, sy = _axis_cos_sin(ay)
    cz, sz = _axis_cos_sin(az)
    rx = ((1.0, 0.0, 0.0), (0.0, cx, -sx), (0.0, sx, cx))    # fn 0x37a0
    ry = ((cy, 0.0, sy), (0.0, 1.0, 0.0), (-sy, 0.0, cy))    # fn 0x3850
    rz = ((cz, -sz, 0.0), (sz, cz, 0.0), (0.0, 0.0, 1.0))    # fn 0x3910
    return _mat3_mul(_mat3_mul(rz, ry), rx)                  # seed I; Rx; Ry*(Rx); Rz*(Ry*Rx)


def decompose(R) -> Tuple[int, int, int]:
    """Inverse of ``build_rotation``: a proper 3x3 rotation -> the three 12-bit Euler angles (0..4095),
    the closed form for ``R = Rz*Ry*Rx`` (EULER.md §1.2). Folds Z into X at gimbal lock (|pitch| ~ 90).
    ``R`` is any object supporting ``R[i][j]``; it is assumed proper (the det<0 guard belongs to the
    managed reprojection path, not this offline decode)."""
    y = math.atan2(-R[2][0], math.hypot(R[0][0], R[1][0]))   # sy = -R20 ; cy = hypot(R00,R10) >= 0
    if math.cos(y) > 1e-6:
        x = math.atan2(R[2][1], R[2][2])                     # cy*sx , cy*cx
        z = math.atan2(R[1][0], R[0][0])                     # sz*cy , cz*cy
    else:                                                    # gimbal lock: fold z into x
        x = math.atan2(-R[1][2], R[1][1])
        z = 0.0
    to_units = UNITS_PER_TURN / (2.0 * math.pi)
    return tuple(int(round(v * to_units)) % UNITS_PER_TURN for v in (x, y, z))


def split_angle(v: int) -> Tuple[int, int]:
    """A 12-bit angle -> the on-disk two-stream form (M5 §2.3): ``coarse`` = the 1-byte/frame track sample
    (u8), ``fine`` = the nibble (2 frames/byte)."""
    v &= 0xFFF
    return (v >> 4) & 0xFF, v & 0xF


def combine_angle(coarse: int, fine: int) -> int:
    """Inverse of ``split_angle``: reassemble the 12-bit angle from its coarse byte + fine nibble."""
    return ((coarse << 4) | (fine & 0xF)) & 0xFFF


def signed12(raw: int) -> int:
    """Reduce a raw ``(coarse<<4)|fine`` result to a signed 12-bit angle in [-2048, 2047] (4096 == one
    turn; high bits are periodic) -- the canonical human-readable angle."""
    v = raw & 0xFFF
    return v - UNITS_PER_TURN if v >= 2048 else v


# ======================================================================= clip decode (M5 / FORMAT.md §2.4)
def _u16(b, o): return struct.unpack_from("<H", b, o)[0]
def _s16(b, o): return struct.unpack_from("<h", b, o)[0]
def _u32(b, o): return struct.unpack_from("<I", b, o)[0]


@dataclass
class Clip:
    """One decoded motion-clip header (FORMAT.md §2.4). Every offset is motion-relative, as on disk
    (pre-relocation)."""
    index: int
    file_off: int              # absolute file offset of the clip payload
    frame_count: int
    flags: int                 # bits 0..2 = "root translation axis i is a CONSTANT"
    t_raw: Tuple[int, int, int]  # per axis: constant s16 (flag set) OR track byte-offset (clear)
    rot_key_off: int           # -> RotKey[nodeCount]  (coarse)
    fine_key_off: int          # -> RotKey[nodeCount]  (fine nibble), or 0


def read_clip_header(blob: bytes, index: int, file_off: int) -> Clip:
    return Clip(index, file_off, _u16(blob, file_off + 2), blob[file_off + 0x0A],
                (_u16(blob, file_off + 4), _u16(blob, file_off + 6), _u16(blob, file_off + 8)),
                _u32(blob, file_off + 0x0C), _u32(blob, file_off + 0x10))


def decode_root_translation(blob: bytes, clip: Clip, frame: int) -> Tuple[int, int, int, int]:
    """Root translation for one frame (FORMAT.md §2.4). Returns ``(tx, ty, tz, max_touched)`` where
    ``max_touched`` is the highest motion-relative byte offset read (for the tiling check)."""
    out = []
    touched = 0
    for i in range(3):
        v = clip.t_raw[i]
        if clip.flags & (1 << i):
            out.append(struct.unpack("<h", struct.pack("<H", v))[0])         # constant s16
        else:
            rel = v + frame * 2
            out.append(_s16(blob, clip.file_off + rel))                       # per-frame s16 track
            touched = max(touched, rel + 2)
    return out[0], out[1], out[2], touched


def decode_rotation(blob: bytes, clip: Clip, frame: int, node_count: int
                    ) -> Tuple[List[Tuple[int, int, int]], List[Tuple[bool, bool, bool]], int]:
    """Decode the 12-bit Euler angles for EVERY node at ``frame`` (FORMAT.md §2.4). Angles are RAW u16
    ``((coarse<<4)|fine)`` (periodic mod 4096; apply ``signed12`` for a canonical angle). Also returns,
    per node, a ``(isTrackX, isTrackY, isTrackZ)`` tuple and the max motion-relative byte offset touched.

    Per node k, per axis i: a track channel reads a u8 coarse sample (1 byte/frame) plus, if a fine table
    is present, a nibble (2 frames/byte); a literal channel stores the u16 value in the RotKey directly."""
    base = clip.file_off
    touched = 0
    angles: List[Tuple[int, int, int]] = []
    is_track: List[Tuple[bool, bool, bool]] = []
    for k in range(node_count):
        ckey = base + clip.rot_key_off + 8 * k
        cflags = _s16(blob, ckey + 6)
        fkey = base + clip.fine_key_off + 8 * k if clip.fine_key_off else 0
        fflags = _s16(blob, fkey + 6) if fkey else 0
        axis = []
        trk = []
        for i in range(3):
            tracked = not (cflags & (1 << i))
            coarse = _u16(blob, ckey + 2 * i)          # field i (u16): literal coarse OR track offset
            if tracked:
                rel = coarse + frame
                coarse = blob[base + rel]              # u8 coarse track, 1 byte/frame
                touched = max(touched, rel + 1)
            fine = 0
            if clip.fine_key_off:
                f = _u16(blob, fkey + 2 * i)
                if not (fflags & (1 << i)):
                    rel = f + (frame >> 1)
                    bval = blob[base + rel]            # nibble track, 2 frames/byte
                    f = (bval >> 4) if (frame & 1) else bval
                    touched = max(touched, rel + 1)
                fine = f & 0xF
            axis.append(((coarse << 4) | fine) & 0xFFFF)
            trk.append(tracked)
        angles.append((axis[0], axis[1], axis[2]))
        is_track.append((trk[0], trk[1], trk[2]))
    # account for the key tables themselves in the tiling bound
    touched = max(touched, clip.rot_key_off + 8 * node_count)
    if clip.fine_key_off:
        touched = max(touched, clip.fine_key_off + 8 * node_count)
    return angles, is_track, touched


# ======================================================================= self-validation
@dataclass
class ClipValidation:
    index: int
    frame_count: int
    flags: int
    has_fine: bool
    file_off: int
    span_bytes: int
    max_touched: int
    tiles: bool                 # touched <= span AND (span - touched) < 4  (only alignment slack)
    triples_checked: int        # distinct (ax,ay,az) round-tripped
    triples_total: int          # all decoded (frames * nodes)
    max_roundtrip_err: float

    @property
    def ok(self) -> bool:
        return self.tiles and self.max_roundtrip_err <= _ROUNDTRIP_TOL


_ROUNDTRIP_TOL = 1e-6


def _mat_max_abs_diff(A: Mat3, B: Mat3) -> float:
    return max(abs(A[r][c] - B[r][c]) for r in range(3) for c in range(3))


def _roundtrip_err(ax: int, ay: int, az: int) -> float:
    """||build_rotation(decompose(M)) - M|| (max abs element), M = build_rotation(ax,ay,az)."""
    M = build_rotation(ax, ay, az)
    return _mat_max_abs_diff(build_rotation(*decompose(M)), M)


def validate(blob: bytes, tol: float = _ROUNDTRIP_TOL) -> Tuple[bool, List[ClipValidation]]:
    """Decode + self-check every motion clip in a creature ``ef###.bytes`` blob. For each clip:
      * TILING -- decoding all ``frame_count`` frames touches bytes up to ``max_touched``, which must fall
        inside the clip's region (``<= span``) with no gap beyond 4-byte alignment (``span - touched < 4``).
      * ROUND-TRIP -- every decoded ``(ax,ay,az)`` triple satisfies
        ``||build_rotation(decompose(build_rotation(a))) - build_rotation(a)|| <= tol``.
    Returns ``(all_ok, [ClipValidation])``. Raises ``ContainerError`` if the effect carries no creature."""
    mp = _container.creature_package(blob)
    if mp is None:
        raise _container.ContainerError("no creature package (id-4 + id-5) in this effect")
    node_count = _container.creature_geom(blob, mp).bone_count
    starts = mp.motion_file_offsets
    sorted_starts = sorted(starts)
    end_of_last = mp.model_image_end
    reports: List[ClipValidation] = []
    for i, off in enumerate(starts):
        cl = read_clip_header(blob, i, off)
        nxt = min((s for s in sorted_starts if s > off), default=end_of_last)
        span = nxt - off
        max_touched = 0
        total = 0
        distinct = set()
        for fr in range(cl.frame_count):
            angles, _is_track, tch = decode_rotation(blob, cl, fr, node_count)
            _tx, _ty, _tz, tch2 = decode_root_translation(blob, cl, fr)
            max_touched = max(max_touched, tch, tch2)
            total += len(angles)
            distinct.update(angles)                     # a triple that round-trips once round-trips always
        max_err = max((_roundtrip_err(*a) for a in distinct), default=0.0)
        tiles = (max_touched <= span) and (span - max_touched) < 4
        reports.append(ClipValidation(
            index=i, frame_count=cl.frame_count, flags=cl.flags, has_fine=cl.fine_key_off != 0,
            file_off=off, span_bytes=span, max_touched=max_touched, tiles=tiles,
            triples_checked=len(distinct), triples_total=total, max_roundtrip_err=max_err))
    ok = all(r.tiles and r.max_roundtrip_err <= tol for r in reports)
    return ok, reports


def validate_file(path: str, tol: float = _ROUNDTRIP_TOL) -> Tuple[bool, List[ClipValidation]]:
    """``validate`` given a local ``ef###.bytes`` path (the file is read, never copied or written)."""
    with open(path, "rb") as fh:
        return validate(fh.read(), tol=tol)


def _format(path: str, ok: bool, reports: List[ClipValidation]) -> str:
    lines = [f"{path}: {len(reports)} clips  frame_counts={[r.frame_count for r in reports]}  "
             f"{'OK' if ok else 'FAIL'}"]
    for r in reports:
        lines.append(
            f"  clip{r.index} @{r.file_off:#x} frames={r.frame_count} flags={r.flags} "
            f"fine={r.has_fine}  tiles={r.tiles} (touched {r.max_touched:#x} <= span {r.span_bytes:#x})  "
            f"roundtrip<= {r.max_roundtrip_err:.2e} on {r.triples_checked} distinct / {r.triples_total}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: py -m ff9mapkit.summons.motion <ef###.bytes> [...]", file=sys.stderr)
        return 2
    all_ok = True
    for p in args:
        try:
            ok, reports = validate_file(p)
        except (_container.ContainerError, OSError, struct.error) as e:
            print(f"{p}: {e}")
            all_ok = False
            continue
        print(_format(p, ok, reports))
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
