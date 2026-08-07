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
def test_each_name_is_emitted_only_behind_its_own_verify(monkeypatch):
    """A different DLL build must yield no name rather than a stale constant -- and each claim is
    guarded INDEPENDENTLY, so a change that breaks one must not silently drop the others."""
    dll = A.DllView()
    rng = {B.OP_RAND, B.OP_RAND_RANGE, B.OP_RAND_CENTERED}
    monkeypatch.setattr(B, "verify", lambda d=None: (False, ["forced"]))
    assert set(B.body_evidence(dll)) == {B.OP_ABR, B.OP_COORD} | rng
    monkeypatch.setattr(B, "verify_abr", lambda d=None: (False, ["forced"]))
    assert set(B.body_evidence(dll)) == {B.OP_COORD} | rng
    monkeypatch.setattr(B, "verify_rng", lambda d=None: (False, ["forced"]))
    assert set(B.body_evidence(dll)) == {B.OP_COORD}
    monkeypatch.setattr(B, "verify_coord", lambda d=None: (False, ["forced"]))
    assert B.body_evidence(dll) == {}


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


# ---------------------------------------------------------------- op 206, the ABR/registrar
def so_blob(variant, entries, magic=B.SO_MAGIC, pad=0x200):
    buf = bytearray(pad)
    struct.pack_into("<H", buf, 0, magic)
    struct.pack_into("<H", buf, B.SO_VARIANT_OFF, variant)
    struct.pack_into("<H", buf, B.SO_LEN_OFF, B.SO_TABLE_OFF + 8 * entries)
    return bytes(buf)


def test_the_so_reading_accepts_a_well_formed_table():
    assert B.so_reading(so_blob(1, 3), 0, 0x200) == (1, 3)
    assert B.so_reading(so_blob(0, 1), 0, 0x200) == (0, 1)


def test_a_wrong_magic_rejects():
    """This is the op's OWN assert -- a blob failing it cannot be a real operand."""
    assert B.so_reading(so_blob(1, 2, magic=0x1234), 0, 0x200) is None


def test_a_record_length_past_the_bound_rejects():
    assert B.so_reading(so_blob(1, 60), 0, 0x40) is None


def test_the_so_reading_never_raises_on_garbage():
    for n in (0, 1, 5, 9):
        assert B.so_reading(b"so" + b"\x00" * n, 0, n + 2) is None


@needs_dll
def test_op206_body_and_both_tail_call_names_re_derive():
    ok, notes = B.verify_abr()
    assert ok, notes


@needs_dll
def test_op206_ships_high_because_the_dll_supplies_the_name():
    """Contrast with op 117, which has no symbol anywhere in its chain and ships medium."""
    ev = B.body_evidence()
    assert ev[B.OP_ABR]["confidence"] == "high"
    assert ev[B.OP_OPEN]["confidence"] == "medium"
    assert "Hi_RegisterTexListModel" in ev[B.OP_ABR]["name"]
    assert "Hi_RegisterGouEffModel" in ev[B.OP_ABR]["name"]


@needs_dll
def test_the_wassert_sources_are_utf16_and_reachable():
    """A string class R2's ASCII scan could not see; op 206's is psx_compatibility.cpp."""
    src = B.wassert_sources()
    assert B.ABR_FN in src
    assert any("psx_compatibility.cpp" in s for s in src[B.ABR_FN])
    assert all(".cpp" in s for v in src.values() for s in v)


@needs_dll
@needs_ops
def test_the_dictionary_carries_op206_at_high():
    ops = A.load_hle_ops()
    row = ops[B.OP_ABR]
    assert row["confidence"] == "high" and "Hi_Register" in row["name"]
    assert A.check_confidence_rule(ops) == []


# ---------------------------------------------------------------- op 136, the actor-relative coord
@needs_dll
def test_op136_body_re_derives():
    ok, notes = B.verify_coord()
    assert ok, notes


@needs_dll
def test_op136_ships_medium_because_the_field_it_divides_is_unidentified():
    """The arithmetic and the destination are pinned; actor[+0x38] itself is not -- every
    BTL_DATA_INIT field maps to a different offset, so it is a DLL runtime field."""
    ev = B.body_evidence()
    assert ev[B.OP_COORD]["confidence"] == "medium"
    assert B.NAME_COORD == "actor_relative_coord"
    assert "coordinate component" in ev[B.OP_COORD]["evidence"]


@needs_dll
@needs_ops
def test_the_dictionary_carries_op136():
    ops = A.load_hle_ops()
    row = ops[B.OP_COORD]
    assert row["name"] == B.NAME_COORD and row["confidence"] == "medium"
    assert row["callback_command"] is None
    assert A.check_confidence_rule(ops) == []


# ---------------------------------------------------------------- ops 48/49/50, the RNG family
@needs_dll
def test_the_rng_family_shares_one_lcg():
    ok, notes = B.verify_rng()
    assert ok, notes


@needs_dll
def test_the_lcg_constants_are_the_ansi_c_ones():
    """1103515245 / 12345 -- the multiplier/increment pair from the C standard's rand()."""
    assert B.LCG_MUL == 1103515245
    assert B.LCG_ADD == 12345


@needs_dll
def test_the_rng_ops_ship_medium_not_high():
    """R2 rates a thin CRT wrapper high (rsin/rcos). These are the same library function INLINED,
    but no source in the binary states a name, so they stay medium rather than inflating."""
    ev = B.body_evidence()
    for op in (B.OP_RAND, B.OP_RAND_RANGE, B.OP_RAND_CENTERED):
        assert ev[op]["confidence"] == "medium"
    assert ev[B.OP_RAND]["name"] == "rand"
    assert ev[B.OP_RAND_RANGE]["name"] == "rand_range"
    assert ev[B.OP_RAND_CENTERED]["name"] == "rand_centered"


@needs_dll
def test_r12d_is_recognised_from_any_source_register():
    """R2 matched only `mov r12d, eax`, so three ops that plainly return a value read as VOID --
    op 50 (378 sites) ends `mov r12d, edx`, op 43 `ecx`, op 16 a constant."""
    dll = A.DllView()
    for op in (50, 43, 16):
        assert dll.handler(op).ret == "int", op


@needs_dll
@needs_ops
def test_the_dictionary_carries_the_rng_family():
    ops = A.load_hle_ops()
    assert ops[B.OP_RAND]["name"] == "rand"
    assert ops[B.OP_RAND_CENTERED]["name"] == "rand_centered"
    assert ops[B.OP_RAND_CENTERED]["returns"] == "int"     # was VOID before the decoder fix
    assert A.check_confidence_rule(ops) == []
