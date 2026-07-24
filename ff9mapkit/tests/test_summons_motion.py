"""``summons.motion`` -- the motion-clip decoder + the PSX Euler rotation math.

Two lanes:
  * PURE-MATH (always runs, never game-gated) -- build_rotation / decompose round-trip incl. gimbal lock
    and the +-90/180 literals, the closed-form expansion, and the coarse/fine split. These are the
    exporter's load-bearing math and must pass on any machine.
  * GAME-GATED -- the full-clip decode + self-validation on the user's own locally-extracted Bahamut
    (ef227) and Odin (ef261). Skips cleanly when the local C:/gd/SCRATCH/summon-format/ blobs are absent.
"""
from __future__ import annotations

import math
import os

import pytest

from ff9mapkit.summons import motion as M

_SCRATCH = r"C:/gd/SCRATCH/summon-format"


def _ef(effid: int) -> str:
    return os.path.join(_SCRATCH, f"ef{effid:03d}.bytes")


def _have(effid: int) -> bool:
    return os.path.exists(_ef(effid))


# ------------------------------------------------------------------ pure-math helpers
def _mul(A, B):
    return [[sum(A[r][k] * B[k][c] for k in range(3)) for c in range(3)] for r in range(3)]


def _transpose(A):
    return [[A[c][r] for c in range(3)] for r in range(3)]


def _maxabs(A, B):
    return max(abs(A[r][c] - B[r][c]) for r in range(3) for c in range(3))


def _det(A):
    return (A[0][0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1])
            - A[0][1] * (A[1][0] * A[2][2] - A[1][2] * A[2][0])
            + A[0][2] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]))


# grid of triples exercising every discrimination axis: identity, single-axis literals (+-90/+-180),
# gimbal lock (ay = +-1024 = +-90 deg), the real clip multi-axis frames, and a coprime-step sweep.
_LITERALS = [(-1024, 0, 0), (2047, 0, 0), (-2047, 0, 0), (2048, 0, 0), (1024, 0, 0), (3072, 0, 0)]
_MULTI = [(2143, 209, 0), (0, 933, 2049), (500, 700, 900), (-300, 1500, -800), (100, 200, 300)]
_GIMBAL = [(a, 1024, b) for a in (0, 512, 2000) for b in (0, 777, 3000)] + \
          [(a, 3072, b) for a in (0, 1234) for b in (0, 2222)]
_SWEEP = [(x, y, z) for x in range(0, 4096, 911) for y in range(0, 4096, 733) for z in range(0, 4096, 577)]


# ------------------------------------------------------------------ PURE-MATH (always run)
def test_build_rotation_identity_and_concrete_axis():
    I = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    assert _maxabs(M.build_rotation(0, 0, 0), I) < 1e-12
    # Rx(90 deg): cx=0, sx=1 -> [[1,0,0],[0,0,-1],[0,1,0]] (standard, -S above the diagonal)
    rx90 = M.build_rotation(1024, 0, 0)
    assert _maxabs(rx90, [[1, 0, 0], [0, 0, -1], [0, 1, 0]]) < 1e-9


def test_build_rotation_orthonormal_proper():
    for a in _LITERALS + _MULTI + _GIMBAL + _SWEEP[:40]:
        R = [list(row) for row in M.build_rotation(*a)]
        assert _maxabs(_mul(R, _transpose(R)), [[1, 0, 0], [0, 1, 0], [0, 0, 1]]) < 1e-9
        assert abs(_det(R) - 1.0) < 1e-9


def test_build_rotation_matches_closed_form_ZYX():
    # EULER.md section 1.2: R = Rz*Ry*Rx expands to this exact table -- an independent check of the
    # composition order + every sign.
    def cs(a):
        r = a * M.TWO_PI_OVER_4096
        return math.cos(r), math.sin(r)
    for ax, ay, az in _MULTI + _SWEEP[::7]:
        cx, sx = cs(ax)
        cy, sy = cs(ay)
        cz, sz = cs(az)
        expect = [
            [cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
            [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
            [-sy,     cy * sx,                cy * cx],
        ]
        assert _maxabs(M.build_rotation(ax, ay, az), expect) < 1e-12


def test_decompose_roundtrips_to_float_precision():
    # The robust invariant (holds through gimbal): build_rotation(decompose(M)) reproduces M exactly,
    # even where decompose returns a DIFFERENT-but-equivalent angle triple.
    for a in _LITERALS + _MULTI + _GIMBAL + _SWEEP:
        Mm = M.build_rotation(*a)
        assert _maxabs(M.build_rotation(*M.decompose(Mm)), Mm) < 1e-9


def test_decompose_recovers_exact_integers_when_pitch_in_range():
    # When the pitch ay is inside the principal range (-90, 90) deg (exclusive of the +-90 gimbal), the
    # decode is unique: decompose returns each input angle reduced mod 4096.
    for ax in (0, 300, 2143, 4000, -300):
        for ay in (0, 209, 933, -1000, 1000):
            for az in (0, 900, 2049, -800, 3072):
                got = M.decompose(M.build_rotation(ax, ay, az))
                assert got == (ax % 4096, ay % 4096, az % 4096), (ax, ay, az, got)


def test_gimbal_branch_is_exercised_and_valid():
    # ay = +90 deg drives the hypot(R00,R10) -> 0 branch; the result must still rebuild the matrix.
    Mm = M.build_rotation(500, 1024, 700)
    ax, ay, az = M.decompose(Mm)
    assert az == 0                                   # gimbal fold zeroes Z
    assert _maxabs(M.build_rotation(ax, ay, az), Mm) < 1e-9


def test_coarse_fine_split_roundtrips_full_range():
    for v in range(4096):
        coarse, fine = M.split_angle(v)
        assert 0 <= coarse <= 0xFF and 0 <= fine <= 0xF
        assert M.combine_angle(coarse, fine) == v
    # a literal like the on-disk -90 deg (0xffc0 stored, folded to 0xfc00 -> 12-bit 3072 = -1024 units)
    assert M.split_angle(3072) == (0xC0, 0x0)
    assert M.combine_angle(0xC0, 0x0) == 3072


def test_signed12():
    assert M.signed12(0) == 0
    assert M.signed12(1024) == 1024
    assert M.signed12(3072) == -1024                 # 270 deg == -90 deg
    assert M.signed12(64512) == -1024                # periodic mod 4096 (the raw stored form)
    assert M.signed12(2047) == 2047 and M.signed12(2048) == -2048


def test_validate_rejects_non_creature_blob():
    import struct
    from ff9mapkit.summons import container as C
    header = struct.pack("<H", 1) + struct.pack("<HH", 0, 1) + struct.pack("<bbH", 3, 0, 1)
    blob = header + b"\x00" * (0x1000 - len(header))
    with pytest.raises(C.ContainerError):
        M.validate(blob)


# ------------------------------------------------------------------ GAME-GATED (local stock blobs)
@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_all_clips_tile_and_roundtrip():
    ok, reports = M.validate_file(_ef(227))
    assert ok
    assert [r.frame_count for r in reports] == [24, 30, 26, 48, 40, 68, 82, 28]
    assert all(r.tiles for r in reports)                          # 0 gaps/overlaps within alignment
    assert all(r.max_roundtrip_err < 1e-6 for r in reports)
    assert all(r.triples_total > 0 for r in reports)


@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_node0_signature_matches_study():
    # EULER.md section 3: clip 0 node 0 is the literal -90 deg (-1024 units) on the X axis, every frame.
    from ff9mapkit.summons import container as C
    blob = open(_ef(227), "rb").read()
    mp = C.creature_package(blob)
    node_count = C.creature_geom(blob, mp).bone_count
    cl = M.read_clip_header(blob, 0, mp.motion_file_offsets[0])
    assert cl.frame_count == 24
    for fr in range(cl.frame_count):
        angles, _is_track, _t = M.decode_rotation(blob, cl, fr, node_count)
        ax, ay, az = angles[0]
        assert (M.signed12(ax), M.signed12(ay), M.signed12(az)) == (-1024, 0, 0)


@pytest.mark.skipif(not _have(261), reason="needs local C:/gd/SCRATCH/summon-format/ef261.bytes")
def test_ef261_odin_validates():
    ok, reports = M.validate_file(_ef(261))
    assert ok                                                    # 97-node creature, 7 clips
    assert len(reports) == 7
    assert all(r.tiles and r.max_roundtrip_err < 1e-6 for r in reports)
