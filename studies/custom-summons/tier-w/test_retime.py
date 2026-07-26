r"""Tests for TIER W rung 3 -- THE TIMING RESCORE (``retime.py`` + ``w3_clock_emu.py`` +
``w3_program_edits.py``).

Runs WITHOUT the install and WITHOUT the corpus: every unit test synthesises its own container /
image / ``Consts``, following ``test_rescore.py``'s posture -- so the frame-word transform, the
WAIT-bounds refusal, the misretime-minus-E1 set property, the alignment checker (and its
falsifiability), the emulator's MIPS primitives and the ledger/revert round-trip are all exercised
on bytes this file wrote.  Install- and corpus-dependent tests use the same skip guards
``test_rescore.py`` uses.

    py -m pytest studies/custom-summons/tier-w/test_retime.py -q

THE ALIGNMENT-CHECKER FIXTURE (section 4) is the one genuinely hard synthetic build: it assembles a
whole ``ef###.bytes``-shaped container carrying TWO real, R3-recoverable state machines (via
``test_summon_inspect.machine()``, TIER R's own MIPS encoder) plus two SFX camera archives, and
hand-derives its own E1/E2/E3 edits (never importing ``w3_program_edits`` -- that module's offsets
are ef227-specific and have no meaning against a synthetic image).  One quirk earned the hard way is
recorded at the call site: ``Chunk.psx_base`` is ``PSX + (slot & 1) * 0x5000`` but ``machine()``'s
``j``/``jal`` encoding hard-codes the DEFAULT psx rather than threading its own ``psx=`` parameter
through jump-target encoding, so an id-3 image built for an ODD chunk slot decodes its own jumps
against the wrong base and R3 never recovers a switch.  The fixture dodges this by giving the second
machine an EVEN slot (2, with an empty padding chunk at slot 1) rather than patching either tool.
"""
from __future__ import annotations

import glob
import hashlib
import os
import struct
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_TIER_R = os.path.join(os.path.dirname(_HERE), "tier-r")
sys.path.insert(0, _HERE)
sys.path.insert(0, _TIER_R)

import retime as T                                              # noqa: E402
import w3_clock_emu as EMU                                      # noqa: E402
import w3_program_edits as PE                                   # noqa: E402
import summon_camera as W                                       # noqa: E402
from test_summon_camera import (CAMPOS, FOCAL, TGTPOS, camera_block, code,  # noqa: E402
                                synth)
from test_summon_inspect import machine                         # noqa: E402
from test_tier_r_disasm import V0                               # noqa: E402

#: this module has no corpus-only test (its install-gated tests already exercise real ef227 data,
#: read the SAME way the corpus was originally extracted) -- kept for parity with test_rescore.py's
#: posture, in case a future addition here needs it.
CORPUS = W.SCRATCH_CORPUS
have_corpus = bool(glob.glob(os.path.join(CORPUS, "ef*.bytes")))
needs_corpus = pytest.mark.skipif(not have_corpus, reason="no extracted corpus at %s" % CORPUS)


def _has_install() -> bool:
    try:
        from ff9mapkit import config
        return bool(config.find_game_path(None))
    except Exception:
        return False


needs_install = pytest.mark.skipif(not _has_install(), reason="no FF9 install resolvable")

SPEC = os.path.join(_HERE, "bahamut_retime.toml")
#: TIER R's own MIPS state-machine encoder marks its clock register $t9 == 25 (T9); the emulator's
#: synthetic threshold ``slti`` sites are located by SEARCHING for this exact word, never by offset.
T9 = 25


def _slti(rt: int, rs: int, imm: int) -> int:
    return 0x28000000 | rs << 21 | rt << 16 | (imm & 0xFFFF)


# ============================================================ small synthetic-container helpers
def _one_shot(codes, wait_before: int = 10, wait_after: int = 20):
    """A one-camera container + its resolved ``Shot`` -- the fixture ``rescore``/``summon_camera``
    tests already use, reused here for the frame-word and WAIT-anchor unit tests."""
    blk = camera_block([codes])
    subs = [b"\xaa" * 8, blk, b"\xbb" * 8]
    ops = [(W.OP_WAIT, 0, wait_before), (W.OP_PLAY_CAMERA, 1, 0), (W.OP_WAIT, 0, wait_after)]
    blob = synth(subs, ops)
    return blob, W.extract_shots(blob, "synth").shots[0]


ESTABLISH_LIKE = code(1, 0x0809, CAMPOS + TGTPOS + FOCAL)         # a focal duration=7 sub-block


def _plain(frame: int, marks: int = 0) -> bytes:
    """A minimal Code carrying no duration field at all (flags 0x8000 = ``unk6``, 4 opaque bytes) --
    the shape this file uses whenever a test cares about the FRAME word and nothing else."""
    return code(frame | marks, 0x8000, b"\x11\x22\x33\x44")


# ============================================================ (1) the frame-word transform
def test_frame_num_and_flags_are_the_10_bit_write_mask():
    assert T.frame_num(0x4001) == 1 and T.frame_flags(0x4001) == 0x4000
    assert T.frame_num(0x0103) == 0x103 and T.frame_flags(0x0103) == 0
    # the write mask is 0x3FF/0xFC00, NOT summon_camera's looser 0x1FFF/0xE000 read-side mask
    assert T.FRAME_NUM_MASK == 0x3FF and T.FRAME_FLAG_MASK == 0xFC00


def test_find_frame_edits_shifts_post_cut_only_and_preserves_flag_bits():
    blob, shot = _one_shot([_plain(1), _plain(11)])
    edits = T.find_frame_edits(shot, cut_local=11, n=5)
    assert [(e.site.local, e.new_local) for e in edits] == [(11, 16)]
    e = edits[0]
    assert T.frame_flags(e.new_word) == T.frame_flags(e.site.word) == 0
    # the pre-cut Code (local 1) is untouched: not in the edit set at all
    assert not any(x.site.local == 1 for x in edits)


def test_find_frame_edits_preserves_a_mark_through_the_shift():
    blob, shot = _one_shot([_plain(1), _plain(11, marks=0x2000)])
    (e,) = T.find_frame_edits(shot, cut_local=11, n=3)
    assert e.site.word == 0x200B and e.new_word == 0x200E           # local 11->14, mark 0x2000 kept
    assert T.frame_flags(e.new_word) == 0x2000


def test_find_frame_edits_crosses_a_256_boundary_moving_both_bytes():
    """A3's own discovery: local 218->266 crosses a 256 boundary so its HIGH byte moves too. This
    reproduces that shape on synthetic data (254 -> 259, 0x00FE -> 0x0103): both bytes of the u16
    change, and the round-trip through ``struct`` is exact."""
    blob, shot = _one_shot([_plain(1), _plain(254)])
    (e,) = T.find_frame_edits(shot, cut_local=254, n=5)
    assert (e.site.local, e.new_local) == (254, 259)
    old_bytes = struct.pack("<H", 254)
    new_bytes = e.write[1]
    assert old_bytes == b"\xfe\x00" and new_bytes == b"\x03\x01"
    assert old_bytes[0] != new_bytes[0] and old_bytes[1] != new_bytes[1]     # BOTH bytes moved
    assert struct.unpack("<H", new_bytes)[0] == 259


def test_find_frame_edits_refuses_a_would_be_zero_frame():
    blob, shot = _one_shot([_plain(5)])
    with pytest.raises(T.RetimeError, match=r"outside 1\.\.1023"):
        T.find_frame_edits(shot, cut_local=5, n=-5)                # 5 + -5 = 0


def test_find_frame_edits_refuses_a_frame_past_1023():
    blob, shot = _one_shot([_plain(1000)])
    with pytest.raises(T.RetimeError, match=r"outside 1\.\.1023"):
        T.find_frame_edits(shot, cut_local=1000, n=100)


def test_find_frame_edits_refuses_a_frozen_pause_bit_before_the_cut():
    blob, shot = _one_shot([_plain(1, marks=0x4000), _plain(11)])
    with pytest.raises(T.RetimeError, match="FREEZE bit"):
        T.find_frame_edits(shot, cut_local=11, n=5)


def test_find_frame_edits_refuses_a_straddling_pre_cut_duration():
    """``ESTABLISH_LIKE`` carries a focal duration of 7 starting at local frame 1; a cut at local
    frame 5 falls INSIDE that countdown (1 + 7 = 8 > 5) and must be refused before any byte moves."""
    blob, shot = _one_shot([ESTABLISH_LIKE, _plain(20)])
    with pytest.raises(T.RetimeError, match="STRADDLE TEST FAILED"):
        T.find_frame_edits(shot, cut_local=5, n=5)


def test_find_frame_edits_refuses_non_monotonic_output():
    """An (adversarial, not corpus-shaped) track where a PRE-cut Code's local frame is numerically
    smaller than a POST-cut Code declared earlier in the list: shifting only the post-cut one would
    make the track's own frame order go backwards, which the block's own frame counter cannot play."""
    blob, shot = _one_shot([_plain(20), _plain(5)])
    with pytest.raises(T.RetimeError, match="non-decreasing"):
        T.find_frame_edits(shot, cut_local=10, n=5)


def test_find_frame_edits_refuses_when_nothing_is_at_or_after_the_cut():
    blob, shot = _one_shot([_plain(1)])
    with pytest.raises(T.RetimeError, match="nothing to retime"):
        T.find_frame_edits(shot, cut_local=50, n=5)


# ============================================================ (2) the WAIT-anchor / bounds refusal
def _bare_sequence(ops):
    return synth([b"\xaa" * 8], ops)


def test_find_seq_anchor_locates_the_unique_span_ending_wait():
    blob = _bare_sequence([(W.OP_WAIT, 0, 10), (W.OP_SETUP_CAMERA, 0xFF, 0), (W.OP_WAIT, 0, 20)])
    a = T.find_seq_anchor(blob, cut_tick=10, n=5)
    assert (a.old, a.new, a.from_tick, a.to_tick) == (10, 15, 0, 10)


def test_find_seq_anchor_refuses_above_the_corpus_envelope():
    blob = _bare_sequence([(W.OP_WAIT, 0, 10), (W.OP_SETUP_CAMERA, 0xFF, 0)])
    with pytest.raises(T.RetimeError, match=r"WAIT arg2 would become 1010"):
        T.find_seq_anchor(blob, cut_tick=10, n=1000)


def test_find_seq_anchor_refuses_a_negative_result():
    blob = _bare_sequence([(W.OP_WAIT, 0, 10), (W.OP_SETUP_CAMERA, 0xFF, 0)])
    with pytest.raises(T.RetimeError, match=r"WAIT arg2 would become -5"):
        T.find_seq_anchor(blob, cut_tick=10, n=-15)


def test_find_seq_anchor_refuses_an_ambiguous_span():
    """Two non-blocking WAITs whose spans BOTH end on the cut tick (here: 10, then a zero-length
    WAIT immediately after it) -- the derivation is refused rather than guessing which one."""
    blob = _bare_sequence([(W.OP_WAIT, 0, 10), (W.OP_WAIT, 0, 0), (W.OP_SETUP_CAMERA, 0xFF, 0)])
    with pytest.raises(T.RetimeError, match="found 2"):
        T.find_seq_anchor(blob, cut_tick=10, n=5)


def test_find_seq_anchor_write_targets_exactly_the_arg2_byte():
    blob = _bare_sequence([(W.OP_WAIT, 0, 10), (W.OP_SETUP_CAMERA, 0xFF, 0)])
    a = T.find_seq_anchor(blob, cut_tick=10, n=5)
    off, raw, _why = a.write
    assert off == a.arg_at == a.op_at + 2
    assert raw == bytes([15])


# ============================================================ (3) misretime == aligned - E1 (set property)
def test_apply_writes_composes_disjoint_domains_and_the_difference_is_exactly_the_third_domain():
    """The mechanism ``build_containers`` relies on, isolated: splice E2+E3 to get MIS-RETIME, splice
    E1 on top to get ALIGNED, and the two artifacts must differ from each other in EXACTLY the bytes
    E1 touches -- nothing more, nothing less -- with every byte the two artifacts DO share identical.
    """
    orig = bytes(64)
    d_seq = T.Domain("E2", "seq", [(0, b"\x01", "seq byte")])
    d_cam = T.Domain("E3", "cam", [(10, b"\x02\x03", "cam word")])
    d_prog = T.Domain("E1", "prog", [(40, b"\x04", "prog byte"), (41, b"\x05", "prog byte 2")])

    misretime = T.apply_writes(orig, d_seq.writes + d_cam.writes)
    aligned = T.apply_writes(misretime, d_prog.writes)

    sa = {i for i in range(len(orig)) if orig[i] != aligned[i]}
    sm = {i for i in range(len(orig)) if orig[i] != misretime[i]}
    assert sm == {0, 10, 11}
    assert sa == sm | {40, 41}
    diff = {i for i in range(len(orig)) if aligned[i] != misretime[i]}
    assert diff == set(d_prog.offsets) == {40, 41}
    # every byte the two artifacts SHARE (everything outside the diff) is bit-for-bit identical
    assert all(aligned[i] == misretime[i] for i in range(len(orig)) if i not in diff)


def test_apply_writes_refuses_two_edits_on_the_same_byte():
    with pytest.raises(T.RetimeError, match="two edits write byte"):
        T.apply_writes(bytes(8), [(2, b"\x01\x02", "a"), (3, b"\x03", "b")])


def test_apply_writes_refuses_a_write_outside_the_container():
    with pytest.raises(T.RetimeError, match="outside the container"):
        T.apply_writes(bytes(8), [(6, b"\x01\x02\x03", "over the end")])


def test_apply_writes_never_changes_length():
    out = T.apply_writes(bytes(16), [(0, b"\xff", "x"), (15, b"\xee", "y")])
    assert len(out) == 16 and out[0] == 0xFF and out[15] == 0xEE


# ============================================================ (4) the alignment checker, on a
#     from-scratch two-clock fixture (NOT ef227 -- w3_program_edits' offsets have no meaning here)
def _build_two_clock_fixture(n: int = 5):
    """A full ``ef###.bytes``-shaped container carrying:

      * chunk 0 ("c0"): a 2-state R3-recoverable machine (state0 -T0-> state1, self-loop) plus one
        SFX camera archive with three Codes -- one pre-cut, two post-cut (one of them past a 256
        Code-word boundary is NOT needed here; that shape is covered in section 1).
      * chunk 1: EMPTY (0 resources) -- pure padding so chunk 2 lands on an EVEN table slot.
      * chunk 2 ("c1" in the checker's own vocabulary: any slot != 0): a 2-state machine whose own
        RUN_PROGRAM and PLAY_CAMERA both sit AFTER the WAIT anchor, so its own beat/cam pair rides
        the E2 shift uniformly and its LEAD must stay exactly what it was in stock.

    Returns ``(stock, T0, N, cut_tick, cut_local, shot0, e1_site, anchor, frame_edits)``.
    """
    T0 = 10                                    # c0 state0's threshold == the cut tick
    img0 = machine([(1, T0, ()), (1, 4, ())])                  # state0 -T0-> state1 -4-> state1
    img1 = machine([(1, 3, ()), (1, 3, ())])                   # state0 -3-> state1 -3-> state1

    blk0 = camera_block([[ESTABLISH_LIKE, _plain(11), _plain(15)]])
    cam0 = _id2_payload([blk0, b"\x00" * 8])
    blk1 = camera_block([[_plain(1)]])
    cam1 = _id2_payload([blk1, b"\x00" * 8])

    ops = [
        (W.OP_RUN_PROGRAM, 0, 0),               # tick 0: origin_c0 = 0
        (W.OP_PLAY_CAMERA, 0, 0),               # tick 0: install chunk0's shot
        (W.OP_WAIT, 0, T0),                     # spans tick 0 -> T0 (== cut_tick)
        (W.OP_LOAD_CHUNK, 2, 0),                # tick T0
        (W.OP_RUN_PROGRAM, 0, 0),               # tick T0: origin_c1 = T0 (post-cut: rides E2)
        (W.OP_PLAY_CAMERA, 0, 0),               # tick T0: install chunk2's shot (post-cut too)
    ]
    stock = _build_two_chunk_container(ops, img0, cam0, img1, cam1)

    import ef_container as EC
    ex = W.extract_shots(stock, "synth")
    shot0 = next(s for s in ex.shots if s.slot == 0)
    cut_tick = T0
    cut_local = cut_tick - shot0.op.seq_tick + 1               # == 11, per retime.build_containers

    anchor = T.find_seq_anchor(stock, cut_tick, n)
    frame_edits = T.find_frame_edits(shot0, cut_local, n)

    c = EC.parse_header(stock, strict=True)
    res0 = next(r for r in c.chunks[0].resources if r.id == 3)
    needle = struct.pack("<I", _slti(V0, T9, T0))
    local_off = img0.payload.find(needle)
    assert img0.payload.find(needle, local_off + 1) == -1, "the E1 site must be unique"
    e1_site = res0.offset + local_off

    return stock, T0, n, cut_tick, cut_local, shot0, e1_site, anchor, frame_edits


def _id2_payload(subs):
    n = len(subs)
    table, body, cur, offs = bytearray(), bytearray(), 4 * n, []
    for s in subs:
        offs.append(cur)
        body += s
        cur += len(s)
    for o in offs:
        table += struct.pack("<i", o)
    payload = bytes(table) + bytes(body)
    sectors = max(1, (len(payload) + W.SECTOR - 1) // W.SECTOR)
    return payload.ljust(sectors * W.SECTOR, b"\x00")


def _build_two_chunk_container(seq_ops, chunk0_img, chunk0_cam, chunk2_img, chunk2_cam):
    resources = {0: [(3, chunk0_img.payload), (2, chunk0_cam)], 1: [],
                2: [(3, chunk2_img.payload), (2, chunk2_cam)]}
    head = bytearray(struct.pack("<h", len(resources)))
    for slot in sorted(resources):
        ress = resources[slot]
        head += struct.pack("<hh", slot, len(ress))
        for rid, payload in ress:
            assert len(payload) % W.SECTOR == 0
            head += struct.pack("<bbh", rid, 0, len(payload) // W.SECTOR)
    assert len(head) <= W.SECTOR
    blob = bytearray(head.ljust(W.SECTOR, b"\x00"))
    seq = bytearray()
    for c_, a1, a2 in seq_ops:
        seq += bytes((c_, a1, a2))
    seq += bytes((W.OP_END, 0, 0))
    assert 0x400 + len(seq) <= W.SECTOR
    blob[0x400:0x400 + len(seq)] = seq
    for slot in sorted(resources):
        for _rid, payload in resources[slot]:
            blob += payload
    return bytes(blob)


def _split_fixture_edits(n: int = 5):
    """Splice the fixture's own E2+E3(->MIS-RETIME) and +E1(->ALIGNED), by hand -- exactly the
    ``build_containers`` recipe, without importing ``w3_program_edits`` (whose offsets are ef227's,
    not this synthetic image's)."""
    (stock, T0, n, cut_tick, cut_local, shot0, e1_site, anchor,
     frame_edits) = _build_two_clock_fixture(n)
    e1_write = (e1_site, struct.pack("<I", _slti(V0, T9, T0 + n)), "synthetic E1")
    misretime = T.apply_writes(stock, [anchor.write] + [e.write for e in frame_edits])
    aligned = T.apply_writes(misretime, [e1_write])
    return stock, aligned, misretime, n, cut_tick, cut_local, shot0, frame_edits


def test_alignment_checker_passes_a_correctly_built_two_clock_retime():
    stock, aligned, misretime, n, cut_tick, cut_local, shot0, _fe = _split_fixture_edits()
    al = T.check_alignment(stock, aligned, misretime, n, cut_tick, cut_local,
                           (shot0.slot, shot0.index), "synth", stretched=("synth:c0", 0))
    assert al.ok, "\n".join("%s %s -- %s" % (ok, tag, d) for ok, tag, d in al.findings if not ok)
    # the two structural facts B1 reported for the REAL retime, reproduced here on synthetic data:
    assert len(al.stock) >= 4                                   # at least one pair per state, x2 machines
    c0_post = [r for r in al.stock if r.ident.slot == 0 and r.cam >= cut_tick]
    c1_rows = [r for r in al.stock if r.ident.slot != 0]
    assert c0_post and c1_rows
    for r in c0_post:
        assert al.misretime[r.ident].lead - r.lead == n           # c0 drifts by exactly N
    for r in c1_rows:
        assert al.misretime[r.ident].lead == r.lead                # c1 is untouched


def test_alignment_checker_is_falsifiable_a_deliberate_1_tick_error_fails_it():
    """The checker must be SHOWN falsifiable, not just shown to pass: mangle one already-shifted
    frame word in ALIGNED by one extra tick (N+1 instead of N) and the checker must catch it."""
    (stock, aligned, misretime, n, cut_tick, cut_local, shot0,
     frame_edits) = _split_fixture_edits()
    bad_edit = frame_edits[0]
    bad_word = struct.pack("<H", bad_edit.new_word + 1)
    bad_aligned = T.apply_writes(aligned, [(bad_edit.site.file_off, bad_word, "1-tick error")])

    al_good = T.check_alignment(stock, aligned, misretime, n, cut_tick, cut_local,
                                (shot0.slot, shot0.index), "synth", stretched=("synth:c0", 0))
    al_bad = T.check_alignment(stock, bad_aligned, misretime, n, cut_tick, cut_local,
                               (shot0.slot, shot0.index), "synth", stretched=("synth:c0", 0))
    assert al_good.ok
    assert not al_bad.ok
    failed_tags = {tag for ok, tag, _d in al_bad.findings if not ok}
    assert any("keeps its lead" in t for t in failed_tags)


# ============================================================ (5) the emulator: MIPS semantics
def test_s32_reinterprets_the_low_32_bits_signed():
    assert EMU.s32(0xFFFFFFFF) == -1
    assert EMU.s32(0x80000000) == -(1 << 31)
    assert EMU.s32(0x7FFFFFFF) == 0x7FFFFFFF
    assert EMU.s32(0x100000000 + 5) == 5                        # bits above 32 are discarded


def test_sra_is_arithmetic_srl_is_logical():
    assert EMU.sra(-8, 1) == -4                                  # sign-extends
    assert EMU.sra(8, 1) == 4
    assert EMU.srl(0xFFFFFFFF, 1) == 0x7FFFFFFF                  # zero-fills


def test_sll_wraps_into_the_sign_bit():
    assert EMU.sll(0x40000000, 1) == -(1 << 31)


def test_addu_subu_wrap_mod_2_32():
    assert EMU.addu(0xFFFFFFFF, 1) == 0
    assert EMU.subu(0, 1) == -1


def test_mult_hi_is_the_high_word_of_a_signed_64_bit_product():
    """Hand-computed: MIPS ``mult``+``mfhi`` on a SIGNED 32x32 product."""
    assert EMU.mult_hi(-1, -1) == 0                              # (-1)*(-1)=1 -> hi word 0
    assert EMU.mult_hi(0x40000000, 4) == 1                       # 0x40000000*4 = 0x1_00000000
    assert EMU.mult_hi(-2, 0x7FFFFFFF) == -1                     # -0xFFFFFFFE -> hi word sign-ext -1
    assert EMU.mult_hi(0, 12345) == 0


def test_magic_div_no_addback_matches_floor_division_on_a_synthetic_divisor():
    """/10 with a divisor we choose ourselves (no stock data at all) -- ``pick_reciprocal`` is a
    pure, generic function, so this is a legitimate from-scratch reciprocal, hand-verified against
    real floor division over a spread of inputs including the divisor's own multiples."""
    sh, m = PE.pick_reciprocal(10, False, 4096)
    for x in list(range(0, 500, 7)) + [0, 10, 20, 4090]:
        assert EMU.magic_div(x, m, sh, False) == x // 10, x


def test_magic_div_addback_matches_floor_division_on_a_synthetic_divisor():
    sh, m = PE.pick_reciprocal(7, True, 4096)
    for x in list(range(0, 500, 5)) + [0, 7, 4088]:
        assert EMU.magic_div(x, m, sh, True) == x // 7, x


def _synthetic_consts(threshold: int, g_creature: int = 4, g_beam: int = 10) -> EMU.Consts:
    """A ``Consts`` built ENTIRELY from arithmetic of our own choosing (own threshold, own gates) --
    not one byte of this is ef227 data.  Exercises ``tick()``'s full dataflow end to end.

    ``threshold`` must be large enough that the 9-element beam-wrap phase (``clock*245 + i*455``,
    reduced modulo 4096 by a loop that can subtract AT MOST TWICE) has permanently exceeded
    ``3*4096`` for every element by the phase's own end -- exactly the corpus-scale geometry real
    ef227 has (threshold 69 against gate 46); a threshold much smaller than ~45 leaves an element
    still reachable and ``check_retime``'s "beams stay retracted" finding fails, which is a fact
    about the beam-wrap arithmetic's scale, not a defect in the retime math this section tests.
    """
    span = threshold - g_creature
    prog_sh, prog_m = PE.pick_reciprocal(threshold, False, (2 * threshold) << 12)
    arr_sh, arr_m = PE.pick_reciprocal(span, True, (2 * span) << 12)
    intro_sh, intro_m = PE.pick_reciprocal(3, False, 3 * 2 * 4096)
    beam_sh, beam_m = PE.pick_reciprocal(g_beam, True, g_beam * 150 * 2)
    ycurve_sh, ycurve_m = PE.pick_reciprocal(3, False, 4096)
    return EMU.Consts(
        threshold=threshold, prog_magic=prog_m, prog_shift=prog_sh,
        arr_magic=arr_m, arr_shift=arr_sh, arr_magic_delay=arr_m, arr_origin=-g_creature,
        intro_magic=intro_m, intro_shift=intro_sh, beam_magic=beam_m, beam_shift=beam_sh,
        ycurve_magic=ycurve_m, g_intro=3, g_creature=g_creature, g_motion=g_creature,
        g_latch=g_creature + 4, g_trail=g_creature + 5, g_parity_odd=g_creature + 1,
        g_parity_even=g_creature + 1, g_beam=g_beam, trail_value=4096)


def test_tick_reproduces_the_ramp_endpoints_on_a_synthetic_consts():
    c = _synthetic_consts(50)
    ts = {k: EMU.tick(c, k) for k in range(c.threshold + 1)}
    assert ts[0].progress == 0 and ts[c.threshold].progress == 4096
    assert ts[c.g_creature].arrival == 0 and ts[c.threshold].arrival == 4096
    assert c.prog_divisor == c.threshold
    assert c.arr_divisor == c.threshold - c.g_creature


def test_check_retime_terminal_identity_on_a_synthetic_stretch():
    """``check_retime`` itself (not just ``tick``), on a from-scratch stock/patched Consts pair."""
    stock = _synthetic_consts(50)
    patched = _synthetic_consts(56)                             # N = +6, same recipe
    findings = EMU.check_retime(stock, patched, 6)
    bad = [f for f in findings if not f.ok]
    assert not bad, "\n".join(str(f) for f in bad)


# ============================================================ (6) w3_program_edits, synthetic image
def _stock_shaped_image() -> bytes:
    """A minimal blob satisfying ``PE.verify_stock``: every guarded u16 in place, everything else
    zero.  ``verify_stock``/``apply_edits`` never decode surrounding bytes as MIPS, so this is
    sufficient without reproducing a real instruction stream."""
    b = bytearray(PE.IMAGE_BASE + 0x2000)
    for off, val in PE.EXPECT_OLD.items():
        struct.pack_into("<H", b, off, val)
    for off, (val, _why) in PE.UNTOUCHED_GATES.items():
        struct.pack_into("<H", b, off, val)
    return bytes(b)


def test_verify_stock_passes_on_a_conforming_synthetic_image():
    PE.verify_stock(_stock_shaped_image())            # must not raise


def test_verify_stock_refuses_a_drifted_guard_byte():
    bad = bytearray(_stock_shaped_image())
    struct.pack_into("<H", bad, PE.IMAGE_BASE + 0x1278, 70)          # stock guard is 69
    with pytest.raises(PE.ProgramEditError, match="E1a"):
        PE.verify_stock(bytes(bad))


def test_verify_stock_refuses_a_drifted_untouched_gate():
    bad = bytearray(_stock_shaped_image())
    struct.pack_into("<H", bad, PE.IMAGE_BASE + 0x0BF0, 25)           # stock gate is 24
    with pytest.raises(PE.ProgramEditError, match="untouched gate"):
        PE.verify_stock(bytes(bad))


def test_apply_edits_changes_exactly_12_bytes_at_n48():
    blob = _stock_shaped_image()
    patched = PE.apply_edits(blob)
    assert len(patched) == len(blob)
    assert PE.changed_byte_count(blob) == 12
    diff = {i for i in range(len(blob)) if blob[i] != patched[i]}
    assert diff <= {off + i for off, ln, _nb, _why in PE.PROGRAM_EDITS for i in range(ln)}


def test_apply_edits_at_n0_is_the_identity():
    blob = _stock_shaped_image()
    zeroed = PE.apply_edits(blob, PE.build_edits(0))
    assert zeroed == blob


def test_build_edits_refuses_below_the_intra_phase_gate_floor():
    with pytest.raises(ValueError, match="floor"):
        PE.build_edits(-25)                             # threshold would drop to 44 < 47


def test_build_edits_accepts_the_floor_boundary():
    edits = PE.build_edits(-22)                          # threshold -> exactly 47
    assert edits                                          # does not raise


def test_recompute_reproduces_the_locked_n48_table():
    d = PE.recompute(PE.N_TICKS)
    assert d["threshold"] == PE.NEW_THRESHOLD
    assert d["progress_magic"] == PE.PROGRESS_MAGIC and d["progress_shift"] == PE.PROGRESS_SHIFT
    assert d["arrival_magic"] == PE.ARRIVAL_MAGIC and d["arrival_shift"] == PE.ARRIVAL_SHIFT


# ============================================================ (7) the ledger / revert round-trip
def _minimal_synth_build(effect: int = 999, n: int = 5) -> T.Build:
    """A ``Build`` assembled BY HAND from a tiny synthetic container -- enough for ``stage()``,
    which only touches ``b.aligned``/``b.misretime``/``b.text``/``b.effect`` and the small scalar
    fields, never ``b.domains``/``b.check``."""
    blob, shot = _one_shot([_plain(1), _plain(10)])
    cut_tick = 10
    cut_local = cut_tick - shot.op.seq_tick + 1
    anchor = T.find_seq_anchor(blob, cut_tick, n)
    frame_edits = T.find_frame_edits(shot, cut_local, n)
    misretime = T.apply_writes(blob, [anchor.write] + [e.write for e in frame_edits])
    # a fake "E1" write elsewhere in the file, same-length, standing in for a program edit
    aligned = T.apply_writes(misretime, [(0x900, bytes([0x42]), "fake E1")])
    return T.Build(spec_path="synthtest.toml", effect=effect, label="t", n=n, source="(synthetic)",
                   sha_in="0" * 64, cut_tick=cut_tick, cut_local=cut_local, anchor=anchor,
                   frame_edits=frame_edits, shot_letter="A", shot=shot, orig=blob, aligned=aligned,
                   misretime=misretime)


def _manifest(root) -> dict:
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            p = os.path.join(dirpath, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def test_stage_writes_both_artifacts_extensionless(tmp_path):
    b = _minimal_synth_build()
    out = T.stage(b, root=tmp_path / "stage")
    container = tmp_path / "stage" / "mod" / "FF9_Data" / "SpecialEffects" / "ef999"
    misfile = tmp_path / "stage" / "misretime" / "ef999"
    assert container.suffix == "" and container.read_bytes() == b.aligned
    assert misfile.read_bytes() == b.misretime
    assert out["aligned_sha256"] == hashlib.sha256(b.aligned).hexdigest()
    assert out["misretime_sha256"] == hashlib.sha256(b.misretime).hexdigest()


@pytest.mark.parametrize("seed_existing", [False, True])
def test_deploy_and_revert_round_trip_on_a_fake_mod_folder(tmp_path, seed_existing):
    """Proven against a MOCK live tree, exactly as the brief requires -- never the install.  Covers
    BOTH the fresh-folder case and the already-carrying-an-override case in one parametrised test."""
    b = _minimal_synth_build()
    game_root = tmp_path / "FAKE_GAME"
    mod = game_root / "FF9CustomMap"
    dest_dir = mod / "FF9_Data" / "SpecialEffects"
    dest_dir.mkdir(parents=True)
    prior = b"a pre-existing override that must come back byte-for-byte" if seed_existing else None
    if prior is not None:
        (dest_dir / "ef999").write_bytes(prior)
    before = _manifest(mod)

    out = T.stage(b, root=tmp_path / "stage", game_root=str(game_root))
    p = subprocess.run([sys.executable, out["scripts"]["deploy_aligned"]],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    assert (dest_dir / "ef999").read_bytes() == b.aligned

    # re-deploy is idempotent
    p2 = subprocess.run([sys.executable, out["scripts"]["deploy_aligned"]],
                        capture_output=True, text=True)
    assert p2.returncode == 0

    # deploying the OTHER variant on top does not disturb the first-deploy snapshot
    p3 = subprocess.run([sys.executable, out["scripts"]["deploy_misretime"]],
                        capture_output=True, text=True)
    assert p3.returncode == 0
    assert (dest_dir / "ef999").read_bytes() == b.misretime

    p4 = subprocess.run([sys.executable, out["scripts"]["revert"]], capture_output=True, text=True)
    assert p4.returncode == 0, p4.stdout + p4.stderr
    after = _manifest(mod)
    assert after == before
    if seed_existing:
        assert (dest_dir / "ef999").read_bytes() == prior
    else:
        assert not (dest_dir / "ef999").exists()

    # a second revert is idempotent
    p5 = subprocess.run([sys.executable, out["scripts"]["revert"]], capture_output=True, text=True)
    assert p5.returncode == 0
    assert _manifest(mod) == before


def test_deploy_refuses_a_mod_folder_carrying_a_modfilelist(tmp_path):
    b = _minimal_synth_build()
    game_root = tmp_path / "FAKE_GAME"
    mod = game_root / "FF9CustomMap"
    mod.mkdir(parents=True)
    (mod / "ModFileList.txt").write_text("something/else\n", encoding="utf-8")
    out = T.stage(b, root=tmp_path / "stage", game_root=str(game_root))
    p = subprocess.run([sys.executable, out["scripts"]["deploy_aligned"]],
                       capture_output=True, text=True)
    assert p.returncode != 0
    assert "ModFileList.txt" in p.stdout


# ============================================================ (8) staging refusals (provenance)
def test_staging_refuses_the_repo():
    with pytest.raises(T.R.RescoreError, match="repo"):
        T.R._refuse_repo_path(os.path.join(T._REPO, "studies", "x"))


def test_staging_refuses_the_install_unless_allow_install(tmp_path):
    game = tmp_path / "FINAL FANTASY IX"
    (game / "FF9CustomMap").mkdir(parents=True)
    b = _minimal_synth_build()
    with pytest.raises(T.R.RescoreError, match="game install"):
        T.stage(b, root=game / "FF9CustomMap", game_root=str(game))


# ============================================================ (9) the real install + corpus (skipped)
@needs_install
def test_the_shipped_spec_builds_and_self_checks_against_this_install():
    spec = T.load_spec(SPEC)
    b = T.build_containers(spec, SPEC)
    b.check = T.self_check(b)
    assert len(b.aligned) == len(b.orig) == len(b.misretime)
    assert b.check.ok, "\n".join(T.check_lines(b))


@needs_install
def test_the_install_still_matches_the_registered_drift_hash():
    import rescore as R
    blob, src = R.read_stock_effect(227)
    assert R.drift_guard(227, blob) == EMU.EXPECTED_STOCK_SHA256
    assert "resources.assets" in src
