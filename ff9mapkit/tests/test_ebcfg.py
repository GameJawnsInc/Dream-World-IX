"""Tests for eb/cfg.py — the narrative-state arc's rung-0 dominance instrument.

Synthetic functions are assembled from labeled cmdasm source (the same authoring layer the
`.ebs` round-trip uses), so every test states its control-flow shape in readable text and the
assertions pin the GUARD semantics: a condition attaches to an instruction iff it provably
holds on every path there.
"""

from __future__ import annotations

import pytest

from ff9mapkit.eb import cmdasm
from ff9mapkit.eb.cfg import Cond, CfgError, FuncFlow, parse_set
from ff9mapkit.eb.disasm import read_code


def _flow(src: str) -> tuple[FuncFlow, bytes]:
    body = cmdasm.assemble_block(src)
    return FuncFlow.build(body, 0, len(body)), body


def _off_of(data: bytes, op: int, skip: int = 0) -> int:
    """Absolute offset of the (skip+1)-th instruction with opcode *op*."""
    pos = 0
    seen = 0
    while pos < len(data):
        ins, pos = read_code(data, pos)
        if ins.op == op:
            if seen == skip:
                return ins.off
            seen += 1
    raise AssertionError(f"no op 0x{op:02X} #{skip} in body")


SC = "Global.UInt16[0]"


# ---------------------------------------------------------------------------
# guard attribution

def test_straight_line_has_no_guards():
    fl, body = _flow(f"""
        SET({{{SC} const(2600) B_LET B_EXPR_END}})
        RET()
    """)
    assert fl.guards_at(_off_of(body, 0x05)) == ()


def test_if_guard_attaches_inside_and_not_after():
    fl, body = _flow(f"""
        SET({{{SC} const(6800) B_EQ B_EXPR_END}})
        JMP_IFNOT(after)
        SET({{Global.Bit[300] const(1) B_LET B_EXPR_END}})
    after:
        SET({{Global.Bit[301] const(1) B_LET B_EXPR_END}})
        RET()
    """)
    inside = fl.guards_at(_off_of(body, 0x05, 1))
    assert inside == (Cond(0, 7, 0, "==", 6800),)
    # the join block (reachable both ways) carries no guard
    assert fl.guards_at(_off_of(body, 0x05, 2)) == ()


def test_else_branch_gets_the_negation():
    fl, body = _flow(f"""
        SET({{{SC} const(6800) B_EQ B_EXPR_END}})
        JMP_IFNOT(elseb)
        SET({{Global.Bit[300] const(1) B_LET B_EXPR_END}})
        JMP(after)
    elseb:
        SET({{Global.Bit[301] const(1) B_LET B_EXPR_END}})
    after:
        RET()
    """)
    assert fl.guards_at(_off_of(body, 0x05, 1)) == (Cond(0, 7, 0, "==", 6800),)
    assert fl.guards_at(_off_of(body, 0x05, 2)) == (Cond(0, 7, 0, "!=", 6800),)


def test_jmp_if_polarity_is_reversed():
    fl, body = _flow(f"""
        SET({{{SC} const(3000) B_GE B_EXPR_END}})
        JMP_IF(taken)
        RET()
    taken:
        SET({{Global.Bit[302] const(1) B_LET B_EXPR_END}})
        RET()
    """)
    assert fl.guards_at(_off_of(body, 0x05, 1)) == (Cond(0, 7, 0, ">=", 3000),)


def test_bare_flag_truth_test_guard():
    fl, body = _flow("""
        SET({Global.Bit[2447] B_EXPR_END})
        JMP_IFNOT(after)
        SET({Global.Bit[900] const(1) B_LET B_EXPR_END})
    after:
        RET()
    """)
    assert fl.guards_at(_off_of(body, 0x05, 1)) == (Cond(0, 1, 2447, "!=", 0),)


def test_nested_guards_accumulate():
    fl, body = _flow(f"""
        SET({{{SC} const(2000) B_GE B_EXPR_END}})
        JMP_IFNOT(end)
        SET({{Global.Bit[10] B_EXPR_END}})
        JMP_IFNOT(end)
        SET({{Global.Bit[11] const(1) B_LET B_EXPR_END}})
    end:
        RET()
    """)
    g = fl.guards_at(_off_of(body, 0x05, 2))
    assert set(g) == {Cond(0, 7, 0, ">=", 2000), Cond(0, 1, 10, "!=", 0)}


def test_compound_and_emits_both_atoms():
    fl, body = _flow(f"""
        SET({{{SC} const(2000) B_GE {SC} const(3000) B_LT B_ANDAND B_EXPR_END}})
        JMP_IFNOT(after)
        SET({{Global.Bit[12] const(1) B_LET B_EXPR_END}})
    after:
        RET()
    """)
    g = fl.guards_at(_off_of(body, 0x05, 1))
    assert set(g) == {Cond(0, 7, 0, ">=", 2000), Cond(0, 7, 0, "<", 3000)}
    # and the FALSE side of a compound must claim nothing
    assert fl.guards_at(_off_of(body, 0x04)) == ()
    assert fl.stats["negated_compound"] == 1


def test_compound_or_claims_nothing():
    fl, body = _flow(f"""
        SET({{{SC} const(2000) B_EQ {SC} const(3000) B_EQ B_OROR B_EXPR_END}})
        JMP_IFNOT(after)
        SET({{Global.Bit[13] const(1) B_LET B_EXPR_END}})
    after:
        RET()
    """)
    assert fl.guards_at(_off_of(body, 0x05, 1)) == ()
    assert fl.stats["unsure_conds"] >= 0


def test_join_point_kills_the_guard():
    # two guarded paths converge on the write -> the write carries neither guard
    fl, body = _flow(f"""
        SET({{{SC} const(1000) B_EQ B_EXPR_END}})
        JMP_IFNOT(other)
        JMP(write)
    other:
        NOTHING()
    write:
        SET({{Global.Bit[14] const(1) B_LET B_EXPR_END}})
        RET()
    """)
    assert fl.guards_at(_off_of(body, 0x05, 1)) == ()


def test_switch_case_guards():
    fl, body = _flow(f"""
        SET({{{SC} B_EXPR_END}})
        SWITCHEX(dflt, 1900, c1, 2005, c2)
    c1:
        SET({{Global.Bit[20] const(1) B_LET B_EXPR_END}})
        RET()
    c2:
        SET({{Global.Bit[21] const(1) B_LET B_EXPR_END}})
        RET()
    dflt:
        SET({{Global.Bit[22] const(1) B_LET B_EXPR_END}})
        RET()
    """)
    assert fl.guards_at(_off_of(body, 0x05, 1)) == (Cond(0, 7, 0, "==", 1900),)
    assert fl.guards_at(_off_of(body, 0x05, 2)) == (Cond(0, 7, 0, "==", 2005),)
    assert fl.guards_at(_off_of(body, 0x05, 3)) == ()      # default arm: no claim


def test_switch_shared_target_becomes_in():
    fl, body = _flow(f"""
        SET({{{SC} B_EXPR_END}})
        SWITCHEX(dflt, 5, shared, 7, shared)
    shared:
        SET({{Global.Bit[23] const(1) B_LET B_EXPR_END}})
        RET()
    dflt:
        RET()
    """)
    assert fl.guards_at(_off_of(body, 0x05, 1)) == (Cond(0, 7, 0, "in", (5, 7)),)


def test_loop_body_and_exit_guards():
    # while (flag) { write } -- the body is guarded flag!=0; the exit block is provably
    # reached only via the false edge, so it carries flag==0 (the loop's exit condition)
    fl, body = _flow("""
    top:
        SET({Global.Bit[30] B_EXPR_END})
        JMP_IFNOT(done)
        SET({Global.Bit[31] const(1) B_LET B_EXPR_END})
        JMP(top)
    done:
        SET({Global.Bit[32] const(1) B_LET B_EXPR_END})
        RET()
    """)
    assert fl.guards_at(_off_of(body, 0x05, 1)) == (Cond(0, 1, 30, "!=", 0),)
    assert fl.guards_at(_off_of(body, 0x05, 2)) == (Cond(0, 1, 30, "==", 0),)


def test_code_after_ret_is_dead():
    fl, body = _flow("""
        RET()
        SET({Global.Bit[40] const(1) B_LET B_EXPR_END})
    """)
    assert fl.guards_at(_off_of(body, 0x05)) is None


def test_malformed_stream_raises_not_guesses():
    body = cmdasm.assemble_block("SET({Global.Bit[1] const(1) B_LET B_EXPR_END})\nRET()")
    with pytest.raises(CfgError):
        FuncFlow.build(body[:-2], 0, len(body) - 2)   # truncated mid-instruction


# ---------------------------------------------------------------------------
# statement parsing

def _first_set(src: str):
    body = cmdasm.assemble_block(src)
    ins, _ = read_code(body, 0)
    return parse_set(body, ins)


def test_parse_set_literal_assign():
    st = _first_set("SET({Global.Bit[8712] const(1) B_LET B_EXPR_END})")
    assert (st.kind, st.source, st.vtype, st.index, st.value, st.pure) == ("assign", 0, 1, 8712, 1, True)


def test_parse_set_clear_and_word():
    st = _first_set(f"SET({{{SC} const(6800) B_LET B_EXPR_END}})")
    assert (st.kind, st.vtype, st.index, st.value) == ("assign", 7, 0, 6800)
    st2 = _first_set("SET({Global.Bit[3536] const(0) B_LET B_EXPR_END})")
    assert (st2.kind, st2.value) == ("assign", 0)


def test_parse_set_computed_value_is_none():
    st = _first_set("SET({Global.Byte[290] Global.Byte[291] const(1) B_PLUS B_LET B_EXPR_END})")
    assert st.kind == "assign" and st.value is None


def test_parse_set_bare_read_is_selector():
    st = _first_set(f"SET({{{SC} B_EXPR_END}})")
    assert (st.kind, st.vtype, st.index) == ("read", 7, 0)


def test_parse_set_condition_statement():
    st = _first_set(f"SET({{{SC} const(2600) B_EQ B_EXPR_END}})")
    assert st.kind == "cond" and st.conds == (Cond(0, 7, 0, "==", 2600),)


def test_guards_deterministic_across_rebuild():
    src = f"""
        SET({{{SC} const(2000) B_GE B_EXPR_END}})
        JMP_IFNOT(end)
        SET({{Global.Bit[11] const(1) B_LET B_EXPR_END}})
    end:
        RET()
    """
    fl1, b1 = _flow(src)
    fl2, b2 = _flow(src)
    assert b1 == b2
    off = _off_of(b1, 0x05, 1)
    assert fl1.guards_at(off) == fl2.guards_at(off)


# ---------------------------------------------------------------------------
# corpus smoke (install-gated)

def _install_eb(fid: int):
    from ff9mapkit.extract import EventBundle
    try:
        return EventBundle().eb_for_id(fid)
    except Exception:
        pytest.skip("game install not available")


def test_field_206_story_dispatch_guards():
    """Field 206's Main_Init dispatches on the ScenarioCounter (the known 1900/2005/2010 story
    switch) — the CFG must surface SC equality guards on real bytes."""
    data = _install_eb(206)
    if data is None:
        pytest.skip("field 206 unavailable")
    from ff9mapkit.eb import EbScript
    eb = EbScript.from_bytes(data)
    f = eb.entries[0].funcs[0]
    fl = FuncFlow.build(eb.data, f.abs_start, f.abs_end)
    sc_values = set()
    for st, blk in fl.iter_sets(eb.data):
        g = fl.guards_of_block(blk)
        if not g:
            continue
        for c in g:
            if c.is_scenario and c.cmp == "==":
                sc_values.add(c.value)
            elif c.is_scenario and c.cmp == "in":
                sc_values.update(c.value)
    assert {1900, 2005}.issubset(sc_values), sc_values


def test_corpus_sample_builds_without_error():
    """Every entry/func of three story-heavy fields must analyze cleanly (or raise CfgError,
    never a raw exception) — and the vast majority must succeed."""
    from ff9mapkit.eb import EbScript
    ok = bad = 0
    for fid in (206, 302, 553):
        data = _install_eb(fid)
        if data is None:
            continue
        eb = EbScript.from_bytes(data)
        for e in eb.entries:
            if e.empty:
                continue
            for f in e.funcs:
                try:
                    FuncFlow.build(eb.data, f.abs_start, f.abs_end)
                    ok += 1
                except CfgError:
                    bad += 1
    assert ok > 0
    assert bad <= ok // 10, (ok, bad)


# ---------------------------------------------------------------------------
# FieldFlow: arm/call-graph context propagation

import struct

from ff9mapkit.eb import EbScript
from ff9mapkit.eb.cfg import FieldFlow


def _eb_field(entries):
    """Minimal synthetic multi-entry .eb (mirrors test_ebsrc's builder): ``entries`` = per slot
    None (EMPTY) or (etype, [(tag, body_src)]) with cmdasm source bodies."""
    blobs = []
    for e in entries:
        if e is None:
            blobs.append(None)
            continue
        etype, funcs = e
        fc = len(funcs)
        table, bodies, fpos = b"", b"", fc * 4
        for tag, src in funcs:
            body = cmdasm.assemble_block(src)
            table += struct.pack("<HH", tag, fpos)
            bodies += body
            fpos += len(body)
        blobs.append(bytes([etype, fc]) + table + bodies)
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[2] = 2
    head[3] = len(blobs)
    offs, pos = [], 8 * len(blobs)
    for b in blobs:
        if b is None:
            offs.append(None)
        else:
            offs.append(pos)
            pos += len(b)
    nonempty = [o for o in offs if o is not None]
    for i, o in enumerate(offs):
        if o is None:
            nxt = next((x for x in offs[i + 1:] if x is not None), None)
            offs[i] = nxt if nxt is not None else nonempty[-1]
    slots, out = b"", b""
    for i, b in enumerate(blobs):
        slots += struct.pack("<HHBBH", offs[i], len(b) if b else 0, 0, 0, 0)
        if b is not None:
            out += b
    return bytes(head) + slots + out


def _sc_ctx(ff, key):
    return sorted((c.cmp, c.value, a) for c, a in ff.ctx.get(key, {}).items() if c.is_scenario)


def test_fieldflow_armed_entry_inherits_beat_guard():
    eb = EbScript.from_bytes(_eb_field([
        (0, [(0, f"""
            SET({{{SC} const(6800) B_EQ B_EXPR_END}})
            JMP_IFNOT(skip)
            InitObject(1, 0)
        skip:
            RET()
        """)]),
        (5, [(0, "SET({Global.Bit[500] const(1) B_LET B_EXPR_END})\nRET()"),
             (1, "SET({Global.Bit[501] const(1) B_LET B_EXPR_END})\nRET()")]),
    ]))
    ff = FieldFlow.build(eb)
    assert _sc_ctx(ff, (1, 0)) == [("==", 6800, True)]
    assert _sc_ctx(ff, (1, 1)) == [("==", 6800, True)]


def test_fieldflow_multi_beat_arm_drops_equality():
    eb = EbScript.from_bytes(_eb_field([
        (0, [(0, f"""
            SET({{{SC} const(6800) B_EQ B_EXPR_END}})
            JMP_IFNOT(second)
            InitObject(1, 0)
        second:
            SET({{{SC} const(6900) B_EQ B_EXPR_END}})
            JMP_IFNOT(skip)
            InitObject(1, 0)
        skip:
            RET()
        """)]),
        (5, [(0, "SET({Global.Bit[500] const(1) B_LET B_EXPR_END})\nRET()")]),
    ]))
    ff = FieldFlow.build(eb)
    # armed at BOTH beats -> the intersection keeps no equality claim
    assert _sc_ctx(ff, (1, 0)) == []


def test_fieldflow_unarmed_entry_gets_no_claims():
    eb = EbScript.from_bytes(_eb_field([
        (0, [(0, "RET()")]),
        (5, [(0, "SET({Global.Bit[500] const(1) B_LET B_EXPR_END})\nRET()")]),
    ]))
    ff = FieldFlow.build(eb)
    assert ff.ctx.get((1, 0)) == {}


def test_fieldflow_unconditional_arm_propagates_empty():
    eb = EbScript.from_bytes(_eb_field([
        (0, [(0, "InitObject(1, 0)\nRET()")]),
        (5, [(0, "SET({Global.Bit[500] const(1) B_LET B_EXPR_END})\nRET()")]),
    ]))
    ff = FieldFlow.build(eb)
    assert ff.ctx.get((1, 0)) == {}          # armed, but under no condition


def test_fieldflow_guards_at_splits_direct_and_armed():
    eb = EbScript.from_bytes(_eb_field([
        (0, [(0, f"""
            SET({{{SC} const(3110) B_EQ B_EXPR_END}})
            JMP_IFNOT(skip)
            InitObject(1, 0)
        skip:
            RET()
        """)]),
        (5, [(0, """
            SET({Global.Bit[600] B_EXPR_END})
            JMP_IFNOT(out)
            SET({Global.Bit[601] const(1) B_LET B_EXPR_END})
        out:
            RET()
        """)]),
    ]))
    ff = FieldFlow.build(eb)
    f = eb.entries[1].funcs[0]
    # the guarded write inside entry 1: intra flag guard is DIRECT, the arm beat is ARMED
    fl = ff.flows[(1, 0)]
    write_off = None
    for st, blk in fl.iter_sets(eb.data):
        if st.kind == "assign" and st.index == 601:
            write_off = st.off
    direct, armed = ff.guards_at(1, 0, write_off)
    assert Cond(0, 1, 600, "!=", 0) in direct
    assert Cond(0, 7, 0, "==", 3110) in armed
