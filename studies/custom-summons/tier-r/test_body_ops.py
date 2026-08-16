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
    assert set(B.body_evidence(dll)) == {B.OP_ABR, B.OP_COORD, B.OP_SCREEN, B.OP_ADDPRIM, B.OP_ANCHOR, B.OP_POS, B.OP_BLIT} | rng
    monkeypatch.setattr(B, "verify_abr", lambda d=None: (False, ["forced"]))
    assert set(B.body_evidence(dll)) == {B.OP_COORD, B.OP_SCREEN, B.OP_ADDPRIM, B.OP_ANCHOR, B.OP_POS, B.OP_BLIT} | rng
    monkeypatch.setattr(B, "verify_rng", lambda d=None: (False, ["forced"]))
    assert set(B.body_evidence(dll)) == {B.OP_COORD, B.OP_SCREEN, B.OP_ADDPRIM, B.OP_ANCHOR, B.OP_POS, B.OP_BLIT}
    monkeypatch.setattr(B, "verify_screen", lambda d=None: (False, ["forced"]))
    assert set(B.body_evidence(dll)) == {B.OP_COORD, B.OP_ADDPRIM, B.OP_ANCHOR, B.OP_POS, B.OP_BLIT}
    monkeypatch.setattr(B, "verify_addprim", lambda d=None: (False, ["forced"]))
    assert set(B.body_evidence(dll)) == {B.OP_COORD, B.OP_ANCHOR, B.OP_POS, B.OP_BLIT}
    monkeypatch.setattr(B, "verify_anchor", lambda d=None: (False, ["forced"]))
    assert set(B.body_evidence(dll)) == {B.OP_COORD, B.OP_POS, B.OP_BLIT}
    monkeypatch.setattr(B, "verify_position", lambda d=None: (False, ["forced"]))
    assert set(B.body_evidence(dll)) == {B.OP_COORD, B.OP_BLIT}
    monkeypatch.setattr(B, "verify_blit", lambda d=None: (False, ["forced"]))
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


# ---------------------------------------------------------------- op 64, the full-screen fill
@needs_dll
def test_op64_body_re_derives():
    ok, notes = B.verify_screen()
    assert ok, notes


def test_the_tile_grid_is_exactly_the_ps1_screen():
    """4*80 = 320 and 2*110 = 220 -- the constant that turns eight rectangles into a screen fill."""
    assert B.TILE_COLS * B.TILE_W == 320
    assert B.TILE_ROWS * B.TILE_H == 220
    assert B.TILE_COLS * B.TILE_ROWS == B.TILE_COUNT
    assert B.TILE_WH_WORD == (B.TILE_H << 16) | B.TILE_W


def test_the_blend_codes_are_the_ps1_rectangle_pair():
    """0x60 opaque / 0x62 semi-transparent -- bit 1 is the rectangle ABE flag."""
    assert B.CODE_RECT == 0x60
    assert B.CODE_RECT | B.CODE_ABE == 0x62


@needs_dll
def test_op64_takes_five_arguments_not_four():
    """R2 tracked the translated MIPS $sp only while it lived in rax; op 64's stub stashes it in
    rbx before another call, so arg 4 at $sp+0x10 was invisible.  M3's x86-frame table says 5."""
    sig = A.DllView().handler(B.OP_SCREEN)
    assert sig.arity == 5
    assert sig.stack_args == (4,)
    assert sig.kinds == "piiii"


@needs_dll
def test_the_stacked_arg_fix_moves_only_the_two_ops_it_should():
    """A decoder change must be bounded and measured, not trusted.  Only 64 and 70 gain an
    argument, and R2's 12-op calibration still re-derives on name AND arity."""
    dll = A.DllView()
    assert dll.handler(64).arity == 5
    assert dll.handler(70).arity == 5
    rows = A.calibration(dll)
    assert all(r.get("name_ok") and r.get("arity_ok") for r in rows), rows


@needs_dll
@needs_ops
def test_the_dictionary_carries_op64():
    ops = A.load_hle_ops()
    row = ops[B.OP_SCREEN]
    assert row["name"] == "draw_fullscreen_fill" and row["confidence"] == "medium"
    assert row["arity"] == 5 and row["arg_kinds"] == "piiii"
    assert A.check_confidence_rule(ops) == []


# ---------------------------------------------------------------- op 143, AddPrim + blend prefix
@needs_dll
def test_op143_both_halves_re_derive():
    ok, notes = B.verify_addprim()
    assert ok, notes


def test_the_dr_tpage_word_is_a_gp0_draw_mode_command():
    """0xE1 is GP0 Draw Mode; bits 5-6 are the ABR semi-transparency mode, bit 9 is dither."""
    assert B.DR_TPAGE_BASE >> 24 == 0xE1
    assert B.DR_TPAGE_BASE & (1 << 9)                      # dither
    assert B.DR_TPAGE_ABR_SHIFT == 5
    for mode in range(4):                                  # the ABR field never escapes bits 5-6
        assert (B.DR_TPAGE_BASE | (mode << B.DR_TPAGE_ABR_SHIFT)) >> 7 == B.DR_TPAGE_BASE >> 7


def test_op143_and_op64_share_the_same_native_function():
    """op 143 exposes AddPrim directly; op 64 reaches it eight times per call."""
    assert B.ADDPRIM_FN == 0x3EDB0


@needs_dll
def test_op64s_arg1_is_a_blend_mode_not_an_ot_depth():
    """The correction this rung made: op 64 hands arg1 to AddPrim's blend parameter, which masks
    it to 2 bits for a DR_TPAGE ABR mode -- an OT depth would not be masked to 0..3."""
    ev = B.body_evidence()
    assert "BLEND MODE" in ev[B.OP_SCREEN]["evidence"]
    assert "blend mode, NOT an OT depth" in ev[B.OP_ADDPRIM]["evidence"]


@needs_dll
@needs_ops
def test_the_dictionary_carries_op143():
    ops = A.load_hle_ops()
    row = ops[B.OP_ADDPRIM]
    assert row["name"] == "add_prim_blended" and row["confidence"] == "medium"
    assert row["arg_kinds"] == "ippi"
    assert A.check_confidence_rule(ops) == []


# ---------------------------------------------------------------- op 128, the actor anchor point
@needs_dll
def test_op128_all_four_commands_and_the_float_fix_re_derive():
    ok, notes = B.verify_anchor()
    assert ok, notes


def test_the_four_commands_are_one_question_not_four():
    """The refusal this rung lifted: multi-command is not the same as ambiguous.  All four are
    routes to 'where is this actor's anchor point'."""
    assert set(B.ANCHOR_COMMANDS) == {1, 14, 20, 22}
    assert B.ANCHOR_COMMANDS[1] == "GET_POSITION"
    assert B.ANCHOR_COMMANDS[22] == "GET_SLAVE"


def test_the_float_mask_is_the_float_status_bit():
    """0x200000 == 1 << 21 == BattleStatus.Float in Memoria's open-source enum."""
    assert B.FLOAT_STATUS == 1 << 21


def test_op128_shares_op136s_actor_lookup():
    """Both anchor content to an actor, through the same index space."""
    assert B.ACTOR_LOOKUP == 0x44A60


@needs_dll
@needs_ops
def test_the_dictionary_carries_op128_and_the_refusal_is_lifted():
    ops = A.load_hle_ops()
    row = ops[B.OP_ANCHOR]
    assert row["name"] == "get_actor_anchor" and row["confidence"] == "medium"
    assert row["arg_kinds"] == "iip"
    assert row["callback_command"] is None      # named by the BODY lane, not the callback lane
    assert A.check_confidence_rule(ops) == []


# ---------------------------------------------------------------- op 127, the other half
@needs_dll
def test_op127_re_derives_including_the_negative_check():
    """The negative matters: op 127 must NOT carry the Float/height correction.  If it did, the
    pair reading would collapse and both names would be wrong."""
    ok, notes = B.verify_position()
    assert ok, notes


@needs_dll
def test_op128_is_op127_plus_the_correction():
    """The structural fact that makes the pair self-confirming: op 128's body CALLS the very
    function op 127 tail-jumps to."""
    dll = A.DllView()
    body = [(i.mnemonic, i.op_str) for i in dll.body(B.ANCHOR_BODY)]
    assert ("call", hex(dll.base + B.ANCHOR_PLAIN)) in body
    fwd = [(i.mnemonic, i.op_str) for i in dll.body(B.POS_FN)]
    assert ("jmp", hex(dll.base + B.ANCHOR_PLAIN)) in fwd


@needs_dll
def test_both_halves_of_the_pair_are_guarded_independently(monkeypatch):
    dll = A.DllView()
    monkeypatch.setattr(B, "verify_position", lambda d=None: (False, ["forced"]))
    ev = B.body_evidence(dll)
    assert B.OP_POS not in ev and B.OP_ANCHOR in ev


@needs_dll
@needs_ops
def test_the_dictionary_carries_op127():
    ops = A.load_hle_ops()
    row = ops[B.OP_POS]
    assert row["name"] == "get_actor_position" and row["confidence"] == "medium"
    assert row["arg_kinds"] == "ip"
    assert row["callback_command"] is None
    assert A.check_confidence_rule(ops) == []


# ---------------------------------------------------------------- op 144, the VRAM scroll blit
@needs_dll
def test_op144_builds_two_dr_move_primitives():
    ok, notes = B.verify_blit()
    assert ok, notes


def test_the_code_word_is_the_one_the_managed_renderer_names():
    """SFXRender.cs case 231 -> DR_MOVE.  231 == 0xE7, and the code byte sits at +7 of the
    primitive, i.e. the top byte of the word the DLL stores."""
    assert B.DR_MOVE_CODE >> 24 == 231 == 0xE7
    assert B.DR_MOVE_CODE & 0x00FFFFFF == 0


def test_the_two_primitives_fill_the_allocation():
    """tag + 5 words = 0x18 bytes each; two of them are exactly the 0x30 carved off the cursor."""
    assert 2 * (4 * (B.DR_MOVE_LEN + 1)) == B.BLIT_ALLOC


def test_the_wrap_split_is_complementary():
    """The two halves must sum to the period for any phase -- that is what makes it a WRAP rather
    than a crop.  Modelled here as plain arithmetic, the way the body computes it."""
    for period in (1, 7, 16, 64, 128):
        for scroll in range(0, 3 * period + 1):
            rem = scroll % period
            assert rem + (period - rem) == period
            assert 0 <= rem < period


@needs_dll
@needs_ops
def test_the_dictionary_carries_op144():
    ops = A.load_hle_ops()
    row = ops[B.OP_BLIT]
    assert row["name"] == "vram_scroll_blit" and row["confidence"] == "medium"
    assert row["arity"] == 7 and row["arg_kinds"] == "iiiiiii"
    assert A.check_confidence_rule(ops) == []
