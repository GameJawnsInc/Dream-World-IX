"""Tests for the TIER R rung-3 inspector.

Runs WITHOUT the extracted corpus, WITHOUT the game install and WITHOUT any capture log: the unit
tests synthesise complete little state machines with R1's MIPS encoder (imported from
``test_tier_r_disasm``) and write throw-away probe logs into ``tmp_path``.  Corpus tests skip on
absence, exactly as R1's and R2's do.

    py -m pytest studies/custom-summons/tier-r/test_summon_inspect.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tier_r_disasm as T                      # noqa: E402
import summon_inspect as S                     # noqa: E402
from test_tier_r_disasm import (                # noqa: E402
    ORIGIN, PSX, image, addiu, addu, beq, bne, j, jalr, jr, lui, lw, nop, sll, sltiu, sw,
    ZERO, V0, V1, A0, A1, A2, A3, S0, S1, SP, RA, needs_corpus, have_corpus)

T9 = 25          # $t9 -- a scratch register the synthetic programs use for the clock
S3 = 19          # the state pointer, as in ef227
CORPUS = T.SCRATCH_CORPUS


def slti(rt, rs, imm):
    return 0x28000000 | rs << 21 | rt << 16 | (imm & 0xFFFF)


# --------------------------------------------------------------------------- a synthetic machine
def machine(cases, psx=PSX):
    """Assemble a whole per-tick program: describe / init / tick(switch) + N clock-guarded cases.

    ``cases`` is ``[(nextState, threshold, extraWords)]`` in state order; ``extraWords`` may be a
    callable taking the case's own word index.  The layout mirrors the shipping idiom exactly: the
    state variable is ``0($a1)``, the clock is ``*($a3)``, and a case ends on
    ``slti clock,N / bne -> STAY / addiu next / sw 0($a1) / sw -1,0($a3)``.  The jump table sits
    below ``headerRel`` after the code, which is where R1 found every real one.
    """
    n = len(cases)
    cases = [tuple(c) + ((),) * (4 - len(c)) for c in cases]
    cases = [(a, b, list(c), list(d)) for a, b, c, d in cases]
    # ---- lay the code out so branch targets can be computed before emitting
    words = []

    def at(i):
        return ORIGIN + 4 * i

    # entry: bne $a0,$zero,INIT_CHECK ; move $s3,$a1  (delay slot)
    # describe arm; init arm; tick arm; cases...; stay/tail; exit
    # sizes
    entry_n = 4                      # bne, addu(ds), <describe: sw, j>  -- see below
    describe_n = 4
    initchk_n = 4
    init_n = 4
    tick_n = 11              # ... including the `nop` every real dispatch puts in the delay slot
    case_n = [10 + len(c[2]) + len(c[3]) for c in cases]
    tail_n = 3
    exit_n = 2
    i_entry = 0
    i_describe = i_entry + entry_n
    i_initchk = i_describe + describe_n
    i_init = i_initchk + initchk_n
    i_tick = i_init + init_n
    i_case = []
    p = i_tick + tick_n
    for k in range(n):
        i_case.append(p)
        p += case_n[k]
    i_tail = p
    i_exit = i_tail + tail_n
    total = i_exit + exit_n
    table_at = ORIGIN + 4 * total          # the table sits after the code, still below headerRel

    # entry
    words += [bne(A0, ZERO, at(i_entry), at(i_initchk)),
              addu(S3, A1, ZERO),                            # delay slot: the state pointer
              nop(), nop()]
    # describe: *(arg4) = blockSize ; j exit
    words += [lw(V1, 16 + 4 * 4 - 16 + (0), SP), addiu(V0, ZERO, 168),
              j(at(i_exit)), sw(V0, 0, V1)]
    # init check: addiu $v0,1 ; bne $a0,$v0 -> tick
    words += [addiu(V0, ZERO, 1), bne(A0, V0, at(i_initchk + 1), at(i_tick)), nop(), nop()]
    # init: sw $zero,0($s3) ; j exit
    words += [sw(ZERO, 0, S3), nop(), j(at(i_exit)), nop()]
    # tick: load state, bound-check, dispatch through the table at image+`table_at`
    words += [lw(V1, 0, S3),                                  # the STATE variable
              lw(T9, 0, A3),                                  # the CLOCK
              sltiu(V0, V1, n),
              beq(V0, ZERO, at(i_tick + 3), at(i_tail)),
              lui(V0, (psx + table_at) >> 16),
              addiu(V0, V0, (psx + table_at) & 0xFFFF),
              sll(V1, V1, 2), addu(V1, V1, V0), lw(V0, 0, V1), jr(V0), nop()]
    # the cases
    for k, (nxt, thr, extra, post) in enumerate(cases):
        base = i_case[k]
        words += [x(base) if callable(x) else x for x in extra]
        words += [slti(V0, T9, thr),
                  bne(V0, ZERO, at(base + len(extra) + 1), at(i_tail)),
                  addiu(V0, ZERO, nxt),                       # delay slot: the next state
                  sw(V0, 0, S3),                              # the TRANSITION
                  addiu(V0, ZERO, -1),
                  sw(V0, 0, A3)]                              # the CLOCK RESET
        words += [x(base) if callable(x) else x for x in post]   # the transition's own tail
        words += [j(at(i_exit)), nop(), nop(), nop()]
    words += [nop(), j(at(i_exit)), nop()]                    # the tail
    words += [jr(RA), nop()]                                  # the exit
    assert len(words) == total, (len(words), total)
    import struct
    table = b"".join(struct.pack("<I", psx + at(i_case[k])) for k in range(n))
    return image(words, progs=(at(i_entry),), tail=table, psx=psx)


def rec(img):
    return S.recover(img, {})


# =========================================================================== the symbolic tracker
def test_incoming_stack_args_are_named():
    assert S._incoming_arg(0) == S.Sym("arg", 0)
    assert S._incoming_arg(12) == S.Sym("arg", 3)
    assert S._incoming_arg(16) == S.Sym("arg", 4)
    assert S._incoming_arg(20) == S.Sym("arg", 5)
    assert S._incoming_arg(-8) == S.UNK


def test_sym_renders_readably():
    assert str(S.Sym("arg", 1)) == "arg1"
    assert str(S.Sym("deref", 0, S.Sym("arg", 3))) == "*(arg3)"
    assert str(S.Sym("deref", 4, S.Sym("arg", 1))) == "*(arg1+0x4)"
    assert str(S._sym_const(0xFFFFFFFF)) == "-1"


def test_trace_follows_a_callee_saved_copy_of_an_argument():
    img = machine([(1, 5, ()), (0, 7, ())])
    w, r = T.ImageWalker(img.payload, img.psx_base, img.header_rel, img.live_programs), None
    r = w.run()
    import tier_r_annot as A
    seg = A.segment_functions(img, w, r, {})
    fn = [f for f in seg.functions if f.entry][0]
    tr = S.trace_function(w, r, fn.offsets)
    # the state pointer is $a1 copied into $s3 in a DELAY SLOT, and it must survive into the cases
    store = [o for o in fn.offsets
             if r.instrs[o].entry and r.instrs[o].entry.name == "sw"
             and r.instrs[o].ops[1] == 0 and tr.reg(o, r.instrs[o].base_reg) == S.Sym("arg", 1)]
    assert store, "no store resolved through the callee-saved copy of arg1"


def test_switch_edges_are_modelled_or_the_cases_start_blind():
    """The regression this guards: ``blocks()`` stops at ``jr``, so without the jump-table edges
    every case body starts from a blank state and the state pointer is lost inside every case."""
    img = machine([(1, 3, ()), (0, 4, ())])
    w = T.ImageWalker(img.payload, img.psx_base, img.header_rel, img.live_programs)
    r = w.run()
    assert r.jump_tables, "the synthetic switch was not recovered by R1"
    jt = r.jump_tables[0]
    raw = w.blocks(r)
    assert all(t not in [s for _b, (_bd, sc) in raw.items() for s in sc] for t in jt.targets), \
        "R1's block graph is expected NOT to carry switch edges -- this test is about adding them"
    # ... and with them added, the state pointer survives into every case body
    import tier_r_annot as A
    seg = A.segment_functions(img, w, r, {})
    fn = [f for f in seg.functions if f.entry][0]
    tr = S.trace_function(w, r, fn.offsets)
    for t in jt.targets:
        store = [o for o in fn.offsets if o > t and S._is_state_store(r, o, tr, 1, 0)]
        assert store, "case %#x lost the state pointer" % t


# =========================================================================== the recovery
def test_recovers_a_synthetic_state_machine():
    got = rec(machine([(1, 9, ()), (2, 4, ()), (0, 6, ())]))
    assert got.verdict == "clean", got.reason
    sm = got.machine
    assert sm.state_base == S.Sym("arg", 1) and sm.state_offset == 0
    assert sm.clock == S.Sym("deref", 0, S.Sym("arg", 3))
    assert sm.bound == 3 and len(sm.cases) == 3
    assert [c.transitions[0].to_state for c in sm.cases] == [1, 2, 0]
    assert [c.transitions[0].threshold for c in sm.cases] == [9, 4, 6]


def test_mode_arms_are_named_from_what_they_do_not_from_the_number():
    sm = rec(machine([(1, 3, ()), (0, 3, ())])).machine
    roles = {a.role for a in sm.arms}
    assert roles == {"describe", "init", "tick"}
    assert [a.mode for a in sm.arms] == [0, 1, None]
    assert sm.state_block_bytes == 168        # read off the describe arm's own store


def test_the_frame_model_is_threshold_plus_one():
    sm = rec(machine([(1, 9, ()), (0, 0, ())])).machine
    assert sm.cases[0].transitions[0].ticks == 10        # clock runs 0..9 inclusive
    assert sm.cases[1].transitions[0].ticks == 1
    assert [p.start_tick for p in sm.phases[:2]] == [0, 10]


def test_phase_chain_stops_on_a_cycle():
    sm = rec(machine([(1, 2, ()), (0, 2, ())])).machine
    assert [p.state for p in sm.phases] == [0, 1]        # 0 -> 1 -> 0 stops at the repeat
    assert sm.phases[-1].next_state == 0


def test_terminal_case_has_no_duration():
    sm = rec(machine([(1, 4, ()), (1, 4, ())])).machine
    # state 1 transitions to itself, so the chain is 0 -> 1 and stops
    assert sm.phases[-1].state == 1


def test_dead_states_are_reported_not_hidden():
    sm = rec(machine([(1, 4, ()), (0, 4, ()), (0, 4, ())])).machine
    assert 2 in sm.dead_states           # slot 2 exists but nothing ever assigns state 2
    assert not sm.bad_targets


def test_a_transition_to_a_state_the_table_cannot_dispatch_is_a_finding():
    sm = rec(machine([(7, 4, ()), (0, 4, ())])).machine
    assert sm.bad_targets == (7,)


def test_a_program_with_no_switch_is_trivial_not_defeated():
    img = image([addiu(SP, SP, -16), jr(RA), addiu(SP, SP, 16)])
    got = rec(img)
    assert got.verdict == "trivial" and "no switch" in got.reason


def test_recovery_never_raises_on_a_degenerate_image():
    img = image([nop(), jr(RA), nop()])
    assert rec(img).verdict in ("trivial", "defeated")


# =========================================================================== the gates
def hle_call(op):
    """The shipping HLE idiom: ``lw $vX, 4*op($table) ; jalr $vX`` (R1 §5)."""
    return [lw(V0, 4 * op, S1), jalr(V0), nop()]


def gated_call(op, threshold):
    """``if (clock >= threshold) hle(op);`` -- six words, laid out from the case's own base."""
    def f(base):
        return [slti(V0, T9, threshold),
                bne(V0, ZERO, ORIGIN + 4 * (base + 1), ORIGIN + 4 * (base + 6)),
                nop()] + hle_call(op)
    return [(lambda b, i=i: f(b)[i]) for i in range(6)]


def test_a_dominating_clock_compare_becomes_a_sub_phase_gate():
    """A call reachable only when ``clock >= N`` must come back carrying that gate."""
    got = rec(machine([(1, 20, gated_call(16, 6)), (0, 4, ())]))
    assert got.verdict == "clean"
    case0 = got.machine.cases[0]
    calls = [h for h in case0.hle if h.op == 16]
    assert calls, "the synthetic HLE call was not recognised"
    gates = case0.gates.get(calls[0].off, ())
    assert any(g.sense == ">=" and g.threshold == 6 for g in gates), gates
    assert case0.first_gate(16).threshold == 6


def test_an_ungated_call_carries_no_gate():
    got = rec(machine([(1, 20, hle_call(16)), (0, 4, ())]))
    case0 = got.machine.cases[0]
    calls = [h for h in case0.hle if h.op == 16]
    assert calls and not case0.gates.get(calls[0].off)
    assert case0.first_gate(16).threshold == 0


# =========================================================================== the capture parser
LOG_HEAD = "# ff9mapkit s47+s48 sfx probe\n"


def write_log(tmp_path, rows, effect=227):
    p = tmp_path / "probe.log"
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(LOG_HEAD)
        for row in rows:
            fh.write(row + "\n")
    return str(p)


def model_row(frame, motion, drawn=True, effect=227, kind="S"):
    bones = "E2EA1B28" if drawn else "00000000"
    return ("MODEL,%d,%d,%s,0,1,1,0,%d,0,0,0,0,0,0,0,0,"
            "0,0,0,0,0,0,0,0,0,%s" % (effect, frame, kind, motion, bones))


def bones_row(frame, ok=True, effect=227):
    v = "100" if ok else "71277478"
    return "BONES,%d,%d,93,%s,%s,%s,%s,%s,%s,%s,%s,%s" % ((effect, frame) + (v,) * 9)


def test_capture_parser_reads_the_rows_it_needs(tmp_path):
    rows = [model_row(10, 0, drawn=False), bones_row(10, ok=False),
            model_row(11, 1), bones_row(11),
            "PSXCAM,227,11,0,0,0,0,0,0,0,0,0,0,0,0,160,120,300,01C25ED0",
            model_row(12, 2, kind="E")]
    cap = S.parse_capture(write_log(tmp_path, rows), 227)
    assert cap.span == (10, 12)
    assert cap.frames[11].motion == 1 and cap.frames[11].drawn
    assert cap.frames[11].proj_h == 300
    assert cap.frames[12].eff_slots == 1
    assert cap.first(lambda c: c.drawn) == 11


def test_capture_ignores_other_effects(tmp_path):
    rows = [model_row(5, 3, effect=329), bones_row(5, effect=329), model_row(6, 4)]
    cap = S.parse_capture(write_log(tmp_path, rows), 227)
    assert list(cap.frames) == [6]


def test_repeated_rows_within_a_frame_are_collapsed(tmp_path):
    rows = []
    for f in (3, 4):
        for _ in range(4):
            rows.append(model_row(f, f))
            rows.append(model_row(f, f, kind="E"))
    cap = S.parse_capture(write_log(tmp_path, rows), 227)
    assert cap.frames[3].eff_slots == 1        # 4 identical passes, one logical model


def test_bone_garbage_is_detected_as_freed_memory(tmp_path):
    rows = [bones_row(f) for f in range(5, 9)] + [bones_row(f, ok=False) for f in range(9, 12)]
    cap = S.parse_capture(write_log(tmp_path, rows), 227)
    assert cap.last_bones_ok() == 8 and cap.first_bones_bad() == 9


def test_motion_resets_are_the_restarts_not_the_advances(tmp_path):
    rows = [model_row(f, m) for f, m in
            [(1, 1), (2, 2), (3, 3), (4, 0), (5, 1), (6, 2), (7, 10), (8, 11)]]
    cap = S.parse_capture(write_log(tmp_path, rows), 227)
    assert cap.motion_resets() == [(4, 0)]


# =========================================================================== the fit
def timed_machine():
    """0 -(10 ticks)-> 1 -(5 ticks)-> 2, each transition scrubbing the motion clip to 0 then 7."""
    return machine([(1, 9, (), hle_call(100)),
                    (2, 4, (), hle_call(26)),
                    (0, 9, ())])


def synth_capture(tmp_path, origin, motion_at, span=60):
    """A probe log where the motion counter restarts at exactly ``motion_at`` = {frame: value}."""
    rows, m = [], 3
    for f in range(origin - 5, origin + span):
        m = motion_at.get(f, m + 1)
        rows.append(model_row(f, m))
        rows.append(bones_row(f))
    return S.parse_capture(write_log(tmp_path, rows), 227)


def test_the_fit_recovers_the_origin_from_the_observed_restarts(tmp_path):
    sm = rec(timed_machine()).machine
    assert [(p.state, p.ticks) for p in sm.phases] == [(0, 10), (1, 5), (2, 10)]
    cap = synth_capture(tmp_path, 40, {50: 0, 55: 0})       # origin 40: 0..49, 50..54, 55..
    fit = S.fit_origin(sm, cap)
    assert fit.origin == 40 and (fit.hits, fit.total) == (2, 2)
    checks = {c.what: c.verdict for c in S.validate(sm, cap, fit)}
    assert checks["enters state 1"] == "AGREE" and checks["enters state 2"] == "AGREE"


def test_a_restart_at_the_right_frame_with_the_wrong_value_is_not_a_match(tmp_path):
    """The value the transition's own SetMotFrame writes is part of the prediction."""
    sm = rec(machine([(1, 9, (), hle_call(100)), (0, 9, ())])).machine
    b = S.boundaries(sm)[0]
    assert b.observable and b.expect_motion == 0
    cap = synth_capture(tmp_path, 40, {50: 4})              # restarts at 50, but to 4, not 0
    fit = S.fit_origin(sm, cap)
    assert fit.hits == 0


def test_fit_uses_only_boundaries_that_predict_an_observable(tmp_path):
    """A machine whose transitions emit no motion call has nothing to fit against, and says so."""
    sm = rec(machine([(1, 9, ()), (0, 9, ())])).machine
    rows = [model_row(f, f % 7) for f in range(0, 60)]
    cap = S.parse_capture(write_log(tmp_path, rows), 227)
    fit = S.fit_origin(sm, cap)
    assert fit.total == 0 and fit.origin is None
    checks = S.validate(sm, cap, fit)
    assert checks[0].verdict == "N/A"


def test_boundaries_flag_observability_from_the_transition_tail():
    sm = rec(machine([(1, 9, ()), (0, 9, ())])).machine
    bs = S.boundaries(sm)
    assert bs and all(not b.observable for b in bs)
    assert "no motion call" in bs[0].detail


# =========================================================================== the report
def test_report_enforces_the_quote_budget(tmp_path):
    sm = rec(machine([(1, 3, ()), (0, 3, ())])).machine
    out = tmp_path / "r.md"
    over = [("too many", ["x"] * (S.QUOTE_BUDGET + 1))]
    with open(out, "w", encoding="utf-8") as fh:
        with pytest.raises(ValueError):
            S.write_report(fh, 999, [sm], {}, quotes=over)


def test_report_writes_the_phase_and_state_tables(tmp_path):
    sm = rec(machine([(1, 3, ()), (2, 3, ()), (0, 3, ())])).machine
    out = tmp_path / "r.md"
    with open(out, "w", encoding="utf-8") as fh:
        n = S.write_report(fh, 999, [sm], {})
    text = out.read_text(encoding="utf-8")
    assert n == 0
    assert "## 1. The entry model" in text and "## 2. The state graph" in text
    assert "state variable" in text and "clock" in text
    for section in ("## 3. What each phase actually calls", "## 7. Every HLE name"):
        assert section in text


def test_report_marks_unnamed_ops_as_unnamed(tmp_path):
    sm = rec(machine([(1, 3, ()), (0, 3, ())])).machine
    out = tmp_path / "r.md"
    with open(out, "w", encoding="utf-8") as fh:
        S.write_report(fh, 999, [sm], {})
    assert "unnamed" in out.read_text(encoding="utf-8")


# =========================================================================== the census
def test_census_summary_counts_every_verdict():
    rows = [S.CensusRow("a", "clean", ""), S.CensusRow("b", "trivial", "no switch"),
            S.CensusRow("c", "defeated", "why"), S.CensusRow("d", "defeated", "why")]
    s = S.census_summary(rows)
    assert (s["total"], s["clean"], s["trivial"], s["defeated"]) == (4, 1, 1, 2)
    assert s["causes"]["why"] == 2


# =========================================================================== the corpus (skipped)
@needs_corpus
def test_ef227_recovers_eleven_and_six_cases():
    blob = open(os.path.join(CORPUS, "ef227.bytes"), "rb").read()
    recs = S.recover_container(blob, "ef227", {})
    assert [r.verdict for r in recs] == ["clean", "clean"]
    c0, c1 = (r.machine for r in recs)
    assert c0.bound == 11 and c1.bound == 6
    assert c0.n_slots == 11 and c1.n_slots == 6
    assert c0.state_base == S.Sym("arg", 1) and c0.clock == S.Sym("deref", 0, S.Sym("arg", 3))
    assert c0.state_block_bytes == 168 and c1.state_block_bytes == 228
    assert [p.state for p in c0.phases] == [0, 10, 1, 2, 4, 5]
    assert [p.ticks for p in c0.phases] == [70, 25, 25, 27, 31, None]
    assert [p.state for p in c1.phases] == [0, 1, 2, 3, 4, 5]
    assert [p.ticks for p in c1.phases] == [36, 49, 29, 3, 15, None]
    assert c0.dead_states == (3, 6, 7, 8, 9) and not c0.bad_targets
    assert not c1.dead_states and not c1.bad_targets


@needs_corpus
def test_ef227_the_default_case_is_the_per_tick_tail():
    blob = open(os.path.join(CORPUS, "ef227.bytes"), "rb").read()
    c0 = S.recover_container(blob, "ef227", {})[0].machine
    tail = [c for c in c0.cases if c.is_tail]
    assert len(tail) == 1 and tail[0].slots == (3, 6, 7, 8, 9)


@needs_corpus
def test_ef227_draw_gate_is_derived_not_guessed():
    import tier_r_annot as A
    ops = A.load_hle_ops()
    blob = open(os.path.join(CORPUS, "ef227.bytes"), "rb").read()
    c0 = S.recover_container(blob, "ef227", ops)[0].machine
    g = c0.cases[0].first_gate(S.DRAW_SUMMON_OP)
    assert g is not None and g.sense == ">=" and g.threshold == 24
