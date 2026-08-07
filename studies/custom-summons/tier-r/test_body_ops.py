"""Tests for the HANDLER-BODY evidence class (op 117).

The predicate tests build synthetic blobs, so they run with no DLL and no corpus -- the predicate is
what the corpus A/B scores, and a predicate that cannot be tested offline cannot be trusted to have
scored anything.

    py -m pytest studies/custom-summons/tier-r/test_body_ops.py -q
"""
from __future__ import annotations

import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import body_ops as B         # noqa: E402
import tier_r_annot as A     # noqa: E402

try:
    import refkit                                     # noqa: F401
    have_dll = os.path.isfile(refkit.DLL_X64)
except Exception:                                     # pragma: no cover
    have_dll = False
have_ops = os.path.isfile(A.HLE_OPS_JSON)

needs_dll = pytest.mark.skipif(not have_dll, reason="needs the installed FF9SpecialEffectPlugin.dll")
needs_ops = pytest.mark.skipif(not have_ops, reason="needs a built hle_ops.json")


def blob_with(count, entries, flag_byte=0x00, pad=0x400):
    """A synthetic sub-file shaped the way the relocator reads one."""
    hdr = B.HDR_SMALL if flag_byte == B.HDR_FLAG_BYTE else B.HDR_LARGE
    buf = bytearray(pad)
    buf[0] = flag_byte
    top = hdr
    struct.pack_into("<H", buf, top + B.COUNT_OFF, count)
    for i, (k0, k1, p0, p1) in enumerate(entries):
        e = top + B.TABLE_OFF + B.ENTRY_STRIDE * i
        buf[e + 0x00] = k0
        buf[e + 0x01] = k1
        struct.pack_into("<I", buf, e + 0x1C, p0)
        struct.pack_into("<I", buf, e + 0x20, p1)
    return bytes(buf)


def test_a_well_formed_blob_reads():
    b = blob_with(2, [(0, 0, 0x100, 0x200), (0, 0, 0x110, 0x210)])
    got = B.relocator_reading(b, 0, len(b))
    assert got == (2, 4, B.HDR_LARGE)


def test_the_header_discriminator_selects_the_small_header():
    b = blob_with(1, [(0, 0, 0x40, 0x50)], flag_byte=B.HDR_FLAG_BYTE)
    got = B.relocator_reading(b, 0, len(b))
    assert got is not None and got[2] == B.HDR_SMALL


def test_sentinel_kind_bytes_suppress_their_pointer():
    """byte+0x00 == 9 and byte+0x01 == 0xff mean 'no pointer here' -- the field is not relocated,
    so a value past the bound must NOT fail the read."""
    b = blob_with(1, [(9, 0xFF, 0xFFFFFFFF, 0xFFFFFFFF)])
    got = B.relocator_reading(b, 0, len(b))
    assert got == (1, 0, B.HDR_LARGE)


def test_an_out_of_range_offset_rejects():
    b = blob_with(1, [(0, 0, B.OFFSET_MAX + 1, 0x10)])
    assert B.relocator_reading(b, 0, len(b)) is None


def test_an_offset_past_the_subfile_rejects():
    b = blob_with(1, [(0, 0, 0x300, 0x10)])
    assert B.relocator_reading(b, 0, 0x200) is None


def test_a_zero_or_absurd_count_rejects():
    assert B.relocator_reading(blob_with(0, []), 0, 0x400) is None
    b = bytearray(blob_with(1, [(0, 0, 0x40, 0x50)]))
    struct.pack_into("<H", b, B.HDR_LARGE + B.COUNT_OFF, 513)
    assert B.relocator_reading(bytes(b), 0, len(b)) is None


def test_a_table_running_past_the_bound_rejects():
    b = blob_with(4, [(0, 0, 0x40, 0x50)] * 4)
    assert B.relocator_reading(b, 0, B.HDR_LARGE + B.TABLE_OFF + 8) is None


def test_the_predicate_never_raises_on_garbage():
    for n in (0, 1, 7, 0x40):
        assert B.relocator_reading(b"\xff" * n, 0, n) is None


@needs_dll
def test_every_structural_claim_re_derives_from_the_dll():
    ok, notes = B.verify()
    assert ok, notes


@needs_dll
def test_the_name_is_emitted_only_behind_verify(monkeypatch):
    """A different DLL build must yield no name at all rather than a stale constant."""
    monkeypatch.setattr(B, "verify", lambda dll=None: (False, ["forced"]))
    assert B.body_evidence(A.DllView()) == {}


@needs_dll
def test_the_name_never_ships_as_high():
    ev = B.body_evidence()
    assert ev[B.OP_OPEN]["confidence"] == "medium"
    assert B.BODY_MARKER in ev[B.OP_OPEN]["evidence"]


@needs_dll
def test_the_tail_jump_gap_is_real_and_bounded():
    """R2 resolves names on an op's own function, so a forwarder hides its callee's symbol.
    op 117's own chain has NO symbol, so it does not benefit -- but op 206's does."""
    gap = {op for op, _f, _n in B.tailjump_name_gap()}
    assert 206 in gap
    assert B.OP_OPEN not in gap


@needs_dll
@needs_ops
def test_the_dictionary_carries_the_body_name_and_it_displaced_nothing():
    ops = A.load_hle_ops()
    row = ops[B.OP_OPEN]
    assert row["name"] == B.NAME and row["confidence"] == "medium"
    assert row["callback_command"] is None      # the two lanes do not both claim it
    assert A.check_confidence_rule(ops) == []
