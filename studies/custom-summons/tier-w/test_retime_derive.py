r"""Tests for TIER W rung 5's E1 AUTO-DERIVATION (``retime_derive.py``).

Two layers, deliberately:

* **corpus-free unit tests** (sections 1-4) build their own MIPS words and hand-assemble a
  ``WalkResult`` from them, so the reaching-definition pass, the peer-``lui`` refusals, the linear
  dividend reader and the magic search are exercised on bytes this file wrote.  Every refusal the
  module can raise has a test here or in section 6;
* **corpus-gated integration tests** (sections 5-7) run the whole derivation against real
  containers, and the headline one is ``test_derived_edit_set_reproduces_the_frozen_ef227_table``:
  the auto-derivation must reproduce ``w3_program_edits.PROGRAM_EDITS`` -- B0's hand-recovered,
  cast-proven, in-game-verified E1 set -- site for site and byte for byte, including the delay-slot
  peer ``lui`` that is the rung's named half-patch trap.  Nothing else available offline comes
  close to that as a check on a derivation.

    py -m pytest studies/custom-summons/tier-w/test_retime_derive.py -q
"""
from __future__ import annotations

import glob
import os
import struct
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_TIER_R = os.path.join(os.path.dirname(_HERE), "tier-r")
sys.path.insert(0, _HERE)
sys.path.insert(0, _TIER_R)

import retime_derive as RD                                    # noqa: E402
import tier_r_disasm as T                                     # noqa: E402
import w3_program_edits as PE                                 # noqa: E402
import summon_camera as W                                     # noqa: E402

CORPUS = W.SCRATCH_CORPUS
have_corpus = bool(glob.glob(os.path.join(CORPUS, "ef*.bytes")))
needs_corpus = pytest.mark.skipif(not have_corpus, reason="no extracted corpus at %s" % CORPUS)

ZERO, V0, V1, A3, T0_, S5 = 0, 2, 3, 7, 8, 21


def _blob(ef: int) -> bytes:
    with open(os.path.join(CORPUS, "ef%03d.bytes" % ef), "rb") as fh:
        return fh.read()


# ============================================================ tiny MIPS assembler for the fixtures
def lui(rt, imm):            return 0x3C000000 | rt << 16 | (imm & 0xFFFF)
def ori(rt, rs, imm):        return 0x34000000 | rs << 21 | rt << 16 | (imm & 0xFFFF)
def mult(rs, rt):            return 0x00000018 | rs << 21 | rt << 16
def mfhi(rd):                return 0x00000010 | rd << 11
def addu(rd, rs, rt):        return 0x00000021 | rs << 21 | rt << 16 | rd << 11
def subu(rd, rs, rt):        return 0x00000023 | rs << 21 | rt << 16 | rd << 11
def sra(rd, rt, sh):         return 0x00000003 | rt << 16 | rd << 11 | (sh & 0x1F) << 6
def sll(rd, rt, sh):         return 0x00000000 | rt << 16 | rd << 11 | (sh & 0x1F) << 6
def addiu(rt, rs, imm):      return 0x24000000 | rs << 21 | rt << 16 | (imm & 0xFFFF)
def slti(rt, rs, imm):       return 0x28000000 | rs << 21 | rt << 16 | (imm & 0xFFFF)
def bne(rs, rt, simm):       return 0x14000000 | rs << 21 | rt << 16 | (simm & 0xFFFF)
def lw(rt, off, base):       return 0x8C000000 | base << 21 | rt << 16 | (off & 0xFFFF)
NOP = 0


def walk(words, base=0):
    """A ``WalkResult`` holding exactly these words, at consecutive offsets from ``base``."""
    r = T.WalkResult("synth:c0", 0x80010000, 4 * len(words) + base, 4 * len(words) + base, (base,))
    for i, w in enumerate(words):
        off = base + 4 * i
        r.instrs[off] = T.DEFAULT_DECODER.decode(w, off, r.psx_base)
    return r, set(r.instrs)


# ============================================================ (1) the register model
def test_dest_reg_names_the_destination_for_each_operand_form():
    r, _b = walk([addiu(V0, S5, -24), sll(V0, V0, 12), addu(V1, V0, S5), lui(V1, 0xB60B),
                  mult(V0, V1), NOP])
    assert RD.dest_reg(r.instrs[0x00]) == (V0, True)         # I-type writes RT
    assert RD.dest_reg(r.instrs[0x04]) == (V0, True)         # shift writes RD
    assert RD.dest_reg(r.instrs[0x08]) == (V1, True)
    assert RD.dest_reg(r.instrs[0x0C]) == (V1, True)
    assert RD.dest_reg(r.instrs[0x10]) == (None, True)       # mult writes HI/LO, no GPR
    assert RD.dest_reg(r.instrs[0x14]) == (None, True)       # nop


def test_dest_reg_reports_an_unmodelled_instruction_rather_than_guessing():
    """The soundness precondition.  A name outside the four sets means the kill sets in the
    reaching-definition pass would be wrong, so the model says so instead of returning None."""
    r, _b = walk([0x00000018])
    ins = r.instrs[0]
    saved = RD.W_NONE
    try:
        RD.W_NONE = frozenset()
        assert RD.dest_reg(ins) == (None, False)
    finally:
        RD.W_NONE = saved


def test_source_regs_keeps_a_read_that_is_also_the_write_target():
    """``sll $v0, $v0, 12`` reads $v0 AND writes it.  A naive ``x != dest`` filter drops the read,
    and the first draft of this analysis did exactly that -- which made ef227's arrival dividend
    look like it was not derived from the clock at all, and the whole phase unreadable."""
    r, _b = walk([sll(V0, V0, 12)])
    assert RD.source_regs(r.instrs[0], V0) == [V0]


# ============================================================ (2) reaching definitions / peers
def test_reaching_defs_follows_the_delay_slot_out_of_a_branch():
    """A transfer does not branch until its delay slot has run, so control leaves FROM the slot.
    Model it the other way and a delay-slot ``lui`` -- ef227's 0x0C04 -- looks unreachable."""
    r, body = walk([bne(T0_, ZERO, 3),          # 0x00 -> 0x10
                    lui(V1, 0xB60B),            # 0x04  delay slot, the PEER copy
                    NOP,                        # 0x08
                    lui(V1, 0xB60B),            # 0x0C  the equal-path copy
                    ori(V1, V1, 0x60B7),        # 0x10  the consumer
                    mult(V0, V1)])              # 0x14
    got = RD.reaching_defs(r, body, {}, V1, 0x10)
    assert got == {0x04, 0x0C}


def test_the_reaching_defs_memo_cannot_serve_another_walks_answer():
    """THE ``id()``-REUSE TRAP (W5 reconcile).

    ``_REACH_CACHE`` was keyed on ``(id(walk), reg)`` alone.  ``id()`` is an ADDRESS and CPython
    recycles it as soon as the object dies, so a short-lived ``WalkResult`` could land on a dead
    one's address and inherit its reaching-definition map.  The symptom was measured, not imagined:
    ``test_retime_derive.py`` passed 55/55 alone and failed 2-3 of these tests when run after
    ``test_retime.py`` in the same process, with a DIFFERENT failing set each run.

    Poisoning the memo under this walk's own key is a deterministic stand-in for that collision:
    with the identity check a poisoned entry is a MISS (recompute), without it the poison is
    returned.  A wrong reaching set here means the peer-``lui`` search misses a twin -- the
    HALF-PATCH TRAP the whole pass exists to prevent."""
    r, body = walk([bne(T0_, ZERO, 3), lui(V1, 0xB60B), NOP, lui(V1, 0xB60B),
                    ori(V1, V1, 0x60B7), mult(V0, V1)])
    other, _ob = walk([lui(V1, 0x1111), ori(V1, V1, 0x2222), mult(V0, V1)])
    RD._REACH_CACHE[(id(r), V1)] = (other, {0x10: frozenset({0xDEAD})})
    try:
        assert RD.reaching_defs(r, body, {}, V1, 0x10) == {0x04, 0x0C}
        # ...and the poisoned entry has been REPLACED by this walk's own, not merely bypassed
        assert RD._REACH_CACHE[(id(r), V1)][0] is r
    finally:
        RD._REACH_CACHE.clear()


def test_resolve_peers_returns_both_copies_of_a_duplicated_lui():
    r, body = walk([bne(T0_, ZERO, 3), lui(V1, 0xB60B), NOP, lui(V1, 0xB60B),
                    ori(V1, V1, 0x60B7), mult(V0, V1)])
    assert RD._resolve_peers(r, body, {}, 0x10, V1, 0xB60B, "lui") == (0x04, 0x0C)


def test_resolve_peers_refuses_a_same_value_lui_that_cannot_be_shown_to_reach():
    """THE HALF-PATCH TRAP as a refusal: a twin the pass cannot place is not silently ignored."""
    r, body = walk([lui(V1, 0xB60B), ori(V1, V1, 0x60B7), mult(V0, V1), lui(V1, 0xB60B)])
    with pytest.raises(RD.DeriveRefusal, match="HALF-PATCH TRAP"):
        RD._resolve_peers(r, body, {}, 0x04, V1, 0xB60B, "lui")


def test_resolve_peers_refuses_two_different_immediates_on_two_paths():
    r, body = walk([bne(T0_, ZERO, 3), lui(V1, 0x1111), NOP, lui(V1, 0xB60B),
                    ori(V1, V1, 0x60B7), mult(V0, V1)])
    with pytest.raises(RD.DeriveRefusal, match="TWO different lui immediates"):
        RD._resolve_peers(r, body, {}, 0x10, V1, 0xB60B, "lui")


def test_resolve_peers_refuses_a_constant_set_outside_the_case_body():
    r, body = walk([ori(V1, V1, 0x60B7), mult(V0, V1)])
    with pytest.raises(RD.DeriveRefusal, match="NO definition inside the case body"):
        RD._resolve_peers(r, body, {}, 0x00, V1, 0xB60B, "lui")


def test_resolve_peers_refuses_a_reaching_def_of_the_wrong_kind():
    r, body = walk([addiu(V1, ZERO, 0x4242), ori(V1, V1, 0x60B7), mult(V0, V1)])
    with pytest.raises(RD.DeriveRefusal, match="is not a `lui`"):
        RD._resolve_peers(r, body, {}, 0x04, V1, 0xB60B, "lui")


# ============================================================ (3) the dividend form
def _cregs(body, reg):
    return {o: frozenset({reg}) for o in body}


def test_dividend_form_reads_the_shifted_offset_ramp():
    """ef227's arrival dividend, in miniature: ``(clock - 24) << 12`` must come back as
    ``A = 4096, B = -98304`` so the origin is 24 and NOT 98304 -- the constant is applied before
    the shift, and scaling it by the shift is the mistake this pins."""
    r, body = walk([addiu(V0, S5, -24), sll(V0, V0, 12), mult(V0, V1)])
    got = RD.dividend_form(r, body, {}, V0, 0x08, _cregs(body, S5), {})
    assert got == ("linear", 4096, -24 * 4096)


def test_dividend_form_reads_a_shift_add_multiply_chain():
    """``clock * 5`` written as ``(clock << 2) + clock`` -- the strength-reduced form the compiler
    emits for the beam phase's ``clock * 245``.  A walker that only knew ``sll`` would call this
    unreadable and refuse a phase that is perfectly legible."""
    r, body = walk([sll(V0, S5, 2), addu(V0, V0, S5), mult(V0, V1)])
    assert RD.dividend_form(r, body, {}, V0, 0x08, _cregs(body, S5), {}) == ("linear", 5, 0)


def test_dividend_form_names_the_parent_reciprocal_it_is_a_function_of():
    r, body = walk([subu(V0, V1, V1), mult(V0, V1)])
    got = RD.dividend_form(r, body, {}, V0, 0x04, {}, {0x00: (V0, 0xABC)})
    assert got == ("parent", 0xABC)


def test_dividend_form_reports_a_pure_constant():
    r, body = walk([addiu(V0, ZERO, 7), mult(V0, V1)])
    assert RD.dividend_form(r, body, {}, V0, 0x04, {}, {}) == ("const", 7)


def test_dividend_form_gives_up_on_a_value_it_cannot_read():
    r, body = walk([mfhi(V0), mult(V0, V1)])
    assert RD.dividend_form(r, body, {}, V0, 0x04, {}, {}) is None


# ============================================================ (4) the magic search
@pytest.mark.parametrize("d, magic, shift, addback", [
    (3, 0x55555556, 0, False),        # ef227's Q-domain ramp -- the shift-0 form
    (6, 0x2AAAAAAB, 0, False),
    (12, 0x2AAAAAAB, 1, False),       # ef227's intro fade
    (24, 0x2AAAAAAB, 2, False),
    (45, 0xB60B60B7, 5, True),        # ef227's arrival ramp
    (66, 0x3E0F83E1, 4, False),       # ef211's entrance progress ramp
    (69, 0x76B981DB, 5, False),       # ef227's progress ramp
    (42, 0x30C30C31, 3, False),       # ef211's arrival ramp
    (23, 0xB21642C9, 4, True),
    (14, 0x92492493, 3, True),
])
def test_canonical_magic_reproduces_the_shipping_constants(d, magic, shift, addback):
    """The compiler's own signed-magic search, checked against constants read out of real images.

    This is the rule the identity gate stands on: it is not tuned to ef227, and it decides the
    add-back bit as an OUTPUT rather than taking it as a preference."""
    assert RD.canonical_magic(d) == (magic, shift, addback)


def test_canonical_magic_refuses_a_divisor_below_two():
    with pytest.raises(RD.DeriveRefusal, match="no signed reciprocal"):
        RD.canonical_magic(1)


def test_pick_reciprocal_uses_the_compilers_own_answer_when_the_skeleton_matches():
    assert RD.pick_reciprocal(69, False, 1 << 20) == (5, 0x76B981DB)
    assert RD.pick_reciprocal(45, True, 1 << 20) == (5, 0xB60B60B7)


def test_pick_reciprocal_keeps_the_skeleton_when_the_canonical_magic_wants_the_other_one():
    """ef227's own N=+48 move.  ``/117``'s canonical magic needs an add-back the ``/69`` site does
    not have, and ``/93``'s does not need the add-back the ``/45`` site does -- so both fall back to
    a shift that keeps the instruction sequence intact, and land on B0's shipping constants."""
    assert RD.canonical_magic(117)[2] is True and RD.canonical_magic(93)[2] is False
    assert RD.pick_reciprocal(117, False, (2 * 117) << 12) == (5, 0x46046047)
    assert RD.pick_reciprocal(93, True, (2 * 93) << 12) == (6, 0xB02C0B03)


def test_canonical_check_refuses_a_reused_magic_that_is_not_the_compilers_own():
    """A shared magic re-shifted for a second divisor -- ef227's c0 s10 divides by 24 with the /3
    magic shifted three further.  Exact, legitimate, and NOT what the rule emits, so a site like it
    is refused rather than rewritten on a rule it disproves."""
    x = RD.Reciprocal(mult_off=0x100, lui_offs=(0x0F8,), ori_offs=(0x0FC,), sra_off=0x110,
                      out_off=None, out_reg=None, magic=0x55555556, shift=3, addback=False,
                      divisor=24, scale=4096, origin=0, tainted=True, parent=None)
    why = RD.canonical_check(x)
    assert why and "not a canonical emitted reciprocal" in why
    x.magic, x.shift = 0x2AAAAAAB, 2
    assert RD.canonical_check(x) is None


# ============================================================ (5) THE HEADLINE: ef227 reproduced
@needs_corpus
def test_derived_edit_set_reproduces_the_frozen_ef227_table():
    """The auto-derivation, run on ef227's own c0 state 0 at N = +48, must reproduce
    :data:`w3_program_edits.PROGRAM_EDITS` -- B0's hand-recovered, cast-proven E1 set -- at every
    site, with every byte, including the shamt rewrite and the delay-slot peer ``lui``."""
    blob = _blob(227)
    d = RD.derive(blob, 227, "ef227:c0", 0, 48)
    mine = sorted((off, ln, nb) for off, ln, nb, _w in d.edits)
    frozen = sorted((off, ln, nb) for off, ln, nb, _w in PE.PROGRAM_EDITS)
    assert mine == frozen
    # and the whole-container splice agrees too, byte for byte
    assert RD.apply_edits(blob, d.edits) == PE.apply_edits(blob)


@needs_corpus
def test_ef227_peer_lui_is_found_by_reaching_definitions_not_by_a_table():
    """The half-patch trap, resolved mechanically: the arrival magic's high half is emitted twice
    (image 0x0C04 in a ``bne``'s delay slot, 0x0C54 on the equal path) and BOTH must be rewritten."""
    t = RD.analyse_target(_blob(227), 227, "ef227:c0", 0)
    arrival = next(x for x in t.reciprocals if x.divisor == 45)
    assert arrival.lui_offs == (0x0C04, 0x0C54) and arrival.peers == 1
    assert t.peer_count == 1


@needs_corpus
def test_ef227_dispositions_match_b0s_own_reading():
    """RETUNE the two phase-normalised ramps, KEEP the other three -- the policy B0 argued from what
    each value drives, here reached from the dividend's dataflow instead."""
    t = RD.analyse_target(_blob(227), 227, "ef227:c0", 0)
    got = {x.divisor: x.disposition for x in t.reciprocals}
    assert got == {69: "RETUNE", 45: "RETUNE", 12: "KEEP", 46: "KEEP", 3: "KEEP"}
    assert next(x for x in t.reciprocals if x.divisor == 45).origin == 24
    assert next(x for x in t.reciprocals if x.divisor == 3).parent is not None


@needs_corpus
def test_ef227_gate_census_matches_the_frozen_untouched_gate_table():
    """The intra-case clock gates recovered from the bytes are exactly the eight immediates
    :data:`w3_program_edits.UNTOUCHED_GATES` names, found without any of its offsets."""
    t = RD.analyse_target(_blob(227), 227, "ef227:c0", 0)
    assert sorted({g.imm for g in t.gates}) == sorted({v for v, _w in
                                                       PE.UNTOUCHED_GATES.values()})


@needs_corpus
def test_the_image_base_is_read_not_assumed():
    """``IMAGE_BASE = 0x2D000`` is ef227 chunk 0's number and nobody else's."""
    assert RD.analyse_target(_blob(227), 227, "ef227:c0", 0).image_base == PE.IMAGE_BASE
    assert RD.analyse_target(_blob(211), 211, "ef211:c0", 3).image_base == 0x35000


# ============================================================ (6) ef211 -- the second effect
@needs_corpus
@pytest.mark.parametrize("state", [0, 4])
def test_ef211_c0_derives_and_passes_its_own_identity_gate(state):
    blob = _blob(211)
    d = RD.derive(blob, 211, "ef211:c0", state, 48)
    assert d.ok and d.edits
    assert all(e.ok for e in d.endpoints)


@needs_corpus
@pytest.mark.parametrize("state", [0, 3, 4])
def test_ef211_c0_build_edits_at_zero_is_the_identity_on_the_whole_container(state):
    if state == 3:
        pytest.skip("s3 is refused (a reciprocal only reaching definitions can see) -- see below")
    """THE MANDATORY SELF-GATE, at container scale: N = 0 changes not one byte."""
    blob = _blob(211)
    t = RD.analyse_target(blob, 211, "ef211:c0", state)
    assert RD.apply_edits(blob, RD.build_edits(t, blob, 0)) == blob


@needs_corpus
def test_ef211_c0_s0_reads_the_same_shape_ef227_has():
    """Phoenix's entrance phase is ef227's entrance phase structurally: one ramp over the whole
    phase and one over ``clock - <gate>``, plus a self-contained sub-ramp under its own gate."""
    t = RD.analyse_target(_blob(211), 211, "ef211:c0", 0)
    assert t.threshold == 66
    got = {x.divisor: (x.disposition, x.origin) for x in t.reciprocals}
    assert got[66] == ("RETUNE", 0)
    assert got[42] == ("RETUNE", 24)
    assert got[35][0] == "KEEP"


# ============================================================ (7) every refusal, by name
@needs_corpus
def test_refuses_a_state_with_no_clock_guarded_transition():
    with pytest.raises(RD.DeriveRefusal, match="no CLOCK-GUARDED transition"):
        RD.analyse_target(_blob(211), 211, "ef211:c0", 6)


@needs_corpus
def test_refuses_a_state_the_machine_does_not_have():
    with pytest.raises(RD.DeriveRefusal, match="has no phase for state"):
        RD.analyse_target(_blob(211), 211, "ef211:c0", 99)


@needs_corpus
def test_refuses_an_image_that_is_not_in_the_container():
    with pytest.raises(RD.DeriveRefusal, match="no id-3 image named"):
        RD.analyse_target(_blob(211), 211, "ef211:c9", 0)


@needs_corpus
def test_refuses_an_image_outside_the_clean_switch_class():
    """ef001:c0 is frame-dispatch: it switches on the host's frame counter, so there is no
    threshold immediate to move."""
    with pytest.raises(RD.DeriveRefusal, match="needs the CLEAN-SWITCH class"):
        RD.analyse_target(_blob(1), 1, "ef001:c0", 0)


@needs_corpus
def test_refuses_a_gate_at_or_past_the_phase_threshold():
    t = RD.analyse_target(_blob(211), 211, "ef211:c0", 1)
    assert not t.derivable
    assert any("at or past the phase threshold" in x for x in t.refusals)


@needs_corpus
def test_refuses_a_divisor_that_is_neither_the_phase_span_nor_a_gate():
    t = RD.analyse_target(_blob(211), 211, "ef211:c0", 2)
    assert not t.derivable
    assert any("which is neither the phase span" in x for x in t.refusals)


@needs_corpus
def test_the_magic_operand_is_found_by_dataflow_not_by_a_backward_window():
    """ef211:c0 s3 loads a ``/3`` magic well outside any fixed backward window from its ``mult``.

    A window scan reports "no reciprocal here" and the phase looks clean -- which is the exact shape
    of the failure this rung exists to prevent, because a reciprocal nobody saw is a reciprocal left
    dividing by the old phase length.  Reaching definitions have no window, so the site is found and
    the phase is refused on it."""
    t = RD.analyse_target(_blob(211), 211, "ef211:c0", 3)
    assert any(x.divisor == 3 and x.mult_off == 0x2A1C for x in t.reciprocals)
    assert not t.derivable


@needs_corpus
def test_refuses_a_clock_derived_dividend_it_cannot_read():
    t = RD.analyse_target(_blob(211), 211, "ef211:c0", 5)
    assert not t.derivable
    assert any("not a readable linear form" in x for x in t.refusals)


@needs_corpus
def test_refuses_an_unresolved_peer_copy_on_a_real_container():
    """ef227's own c0 state 1 carries a second ``lui $v1, 0x5555`` the pass cannot place."""
    with pytest.raises(RD.DeriveRefusal, match="HALF-PATCH TRAP"):
        RD.analyse_target(_blob(227), 227, "ef227:c0", 1)


@needs_corpus
def test_refuses_a_body_it_cannot_model(monkeypatch):
    """The soundness precondition at the call site: strip the write model and the analysis refuses
    rather than computing kill sets it cannot justify."""
    monkeypatch.setattr(RD, "W_NONE", frozenset())
    with pytest.raises(RD.DeriveRefusal, match="no modelled destination register"):
        RD.analyse_target(_blob(227), 227, "ef227:c0", 0)


@needs_corpus
def test_refuses_a_stretch_that_shrinks_the_phase_past_its_own_gates():
    """B0's floor, generalised: ef227's largest intra-case gate is ``clock < 46``, so a threshold at
    or below 46 would put a sub-phase boundary outside the phase that contains it."""
    blob = _blob(227)
    t = RD.analyse_target(blob, 227, "ef227:c0", 0)
    with pytest.raises(RD.DeriveRefusal, match="at or below the largest intra-case clock gate"):
        RD.build_edits(t, blob, -30)
    assert RD.build_edits(t, blob, -22)                       # 69 - 22 = 47, one above the floor


@needs_corpus
def test_refuses_a_shift_change_the_skeleton_cannot_carry():
    """A shift-0 reciprocal has no shift instruction at all; moving its shamt would mean growing an
    instruction, which this rung does not do."""
    blob = _blob(251)
    t = RD.analyse_target(blob, 251, "ef251:c0", 4)
    with pytest.raises(RD.DeriveRefusal, match="NO shift instruction"):
        RD.build_edits(t, blob, 48)


@needs_corpus
def test_build_refuses_a_target_that_was_refused():
    blob = _blob(211)
    t = RD.analyse_target(blob, 211, "ef211:c0", 2)
    with pytest.raises(RD.DeriveRefusal, match="this target is refused"):
        RD.build_edits(t, blob, 10)


@needs_corpus
def test_the_identity_gate_fires_when_the_derivation_disagrees_with_stock():
    """Falsifiability of the self-gate itself: hand the target a container whose stock magic has
    been mangled and ``assert_identity`` must catch it."""
    blob = _blob(227)
    t = RD.analyse_target(blob, 227, "ef227:c0", 0)
    bad = bytearray(blob)
    off = t.image_base + 0x0B6C
    struct.pack_into("<H", bad, off, 0x1234)
    with pytest.raises(RD.DeriveRefusal, match="THE N=0 IDENTITY GATE FAILED"):
        RD.assert_identity(t, bytes(bad))


def test_apply_edits_refuses_overlapping_or_out_of_range_writes():
    with pytest.raises(RD.DeriveRefusal, match="two edits write byte"):
        RD.apply_edits(bytes(16), [RD.Edit(4, 2, b"\x01\x02", "a"), RD.Edit(5, 2, b"\x03\x04", "b")])
    with pytest.raises(RD.DeriveRefusal, match="outside the container"):
        RD.apply_edits(bytes(8), [RD.Edit(7, 2, b"\x01\x02", "over the end")])


# ============================================================ (8) the corpus sweep
@needs_corpus
def test_the_corpus_sweep_never_crashes_and_every_refusal_is_named():
    """Every clock-guarded phase in the clean-switch class either derives (and passes its own N=0
    identity gate) or refuses with a reason a human can act on.  No exception escapes."""
    targets = RD.corpus_targets()
    assert len(targets) >= 80
    blobs = {}
    derivable, refused = 0, 0
    for ef, image, state in targets:
        blobs.setdefault(ef, _blob(ef))
        try:
            t = RD.analyse_target(blobs[ef], ef, image, state)
            if t.derivable:
                RD.assert_identity(t, blobs[ef])
                derivable += 1
            else:
                refused += 1
                assert all(x.strip() for x in t.refusals)
        except RD.DeriveRefusal as exc:
            refused += 1
            assert str(exc).strip()
    assert derivable + refused == len(targets)
    assert derivable >= 40, "the derivable set collapsed: %d of %d" % (derivable, len(targets))


@needs_corpus
def test_corpus_targets_includes_the_two_effects_this_rung_names():
    targets = set(RD.corpus_targets())
    assert (227, "ef227:c0", 0) in targets
    assert (211, "ef211:c0", 0) in targets
