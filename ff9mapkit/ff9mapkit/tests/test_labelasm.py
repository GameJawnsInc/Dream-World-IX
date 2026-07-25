"""The label assembler + LONG-JUMP RELAXATION (the rung-5 capacity fix).

A signed `.eb` jump reaches ±32767; bodies past ~32KB used to die in struct.pack.
asm() now routes out-of-range jumps through inserted islands. The battery pins:
byte-identity when nothing overflows (golden stability), semantic reachability
through island chains (a decoder-walk FOLLOWS the hops), fall-through safety
(islands are jumped over), multi-hop spans, the statement/conditional adjacency
rule, and the behavior compiler surviving a ticker far past the old ceiling.
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.eb import disasm as D
from ff9mapkit.eb.labelasm import JMP, JMP_IF, JMP_IFNOT, asm, label

NOP8 = bytes([0x00] * 8)                       # 8 one-byte NOTHING ops


def _follow(body: bytes, off: int) -> int:
    """Follow unconditional-jump hops from the instruction at ``off`` until a
    non-jump instruction is reached; returns its offset. Walks the raw bytes —
    op 0x01 + i16 (measured from the instruction's END, engine truth)."""
    for _hop in range(50):
        if body[off] != JMP:
            return off
        (rel,) = struct.unpack_from("<h", body, off + 1)
        off = off + 3 + rel
    raise AssertionError("jump chain did not terminate")


def _first_target(body: bytes, op: int) -> int:
    """Resolve the FIRST jump of ``op`` in the body through any island chain."""
    for ins in D.iter_code(body, 0, len(body)):
        if ins.op == op:
            if op == JMP_IFNOT:
                (rel,) = struct.unpack_from("<H", body, ins.off + 1)
            else:
                (rel,) = struct.unpack_from("<h", body, ins.off + 1)
            return _follow(body, ins.off + 3 + rel)
    raise AssertionError(f"no op {op:#x} in body")


def test_small_bodies_are_byte_identical():
    """No overflow -> the exact pre-relaxation encoding (golden stability)."""
    body = asm([label("top"), NOP8, (JMP_IFNOT, "out"), NOP8, (JMP, "top"),
                label("out"), bytes([0x04])])
    # hand-computed: 8 NOPs, IFNOT +11 (to out), 8 NOPs, JMP -22 (to top), 0x04
    assert body == (NOP8 + bytes([JMP_IFNOT]) + struct.pack("<H", 11)
                    + NOP8 + bytes([JMP]) + struct.pack("<h", -22) + bytes([0x04]))
    assert len(body) == 23                     # no islands appeared


def test_forward_long_jump_relaxes_and_reaches():
    filler = [NOP8] * 5000                     # 40KB of one-byte ops
    body = asm([(JMP, "far"), *filler, label("far"), bytes([0x04])])
    assert len(body) > 40000
    # the first instruction is still a jump; following its chain lands on 0x04
    assert body[_follow(body, 0)] == 0x04
    # and the walk stays structurally sound
    for ins in D.iter_code(body, 0, len(body)):
        assert ins.end <= len(body)


def test_backward_long_jump_relaxes_and_reaches():
    """The loop-closure shape that actually broke rung 5: end -> top."""
    filler = [NOP8] * 5000
    body = asm([label("top"), bytes([0x04]), *filler, (JMP, "top")])
    off = len(body) - 3
    # the tail jump's chain must land exactly on the 0x04 at offset 0
    (rel,) = struct.unpack_from("<h", body, off + 1)
    assert _follow(body, off + 3 + rel) == 0
    assert struct.unpack_from("<h", body, off + 1)[0] >= -32767


def test_two_hop_chain_past_64k():
    filler = [NOP8] * 9000                     # 72KB — needs a chained island
    body = asm([(JMP, "far"), *filler, label("far"), bytes([0x04])])
    assert body[_follow(body, 0)] == 0x04


def test_conditional_long_jump_relaxes():
    filler = [NOP8] * 5000
    body = asm([bytes([0x05, 0x7D, 0x01, 0x00, 0x7F]),       # SET const(1)
                (JMP_IF, "far"), *filler, label("far"), bytes([0x04])])
    assert body[_first_target(body, JMP_IF)] == 0x04


def test_every_signed_offset_in_range_after_relaxation():
    filler = [NOP8] * 5000
    body = asm([label("top"), NOP8, (JMP, "mid"), *filler, label("mid"),
                NOP8, *filler, (JMP, "top"), bytes([0x04])])
    for ins in D.iter_code(body, 0, len(body)):
        if ins.op in (JMP, JMP_IF):
            (rel,) = struct.unpack_from("<h", body, ins.off + 1)
            assert -32768 <= rel <= 32767      # struct would have raised anyway
        elif ins.op == JMP_IFNOT:
            (rel,) = struct.unpack_from("<H", body, ins.off + 1)
            assert rel <= 65535


def test_islands_never_split_stmt_from_conditional():
    """The adjacency rule: no island lands between a 0x05 statement and the
    conditional that consumes its value — every conditional's PREDECESSOR
    instruction must never be an unconditional island hop we inserted."""
    stmt = bytes([0x05, 0x7D, 0x01, 0x00, 0x7F])
    pairs = [x for _ in range(4000) for x in (stmt, (JMP_IFNOT, "out"))]
    body = asm([label("top"), *pairs, (JMP, "top"), label("out"), bytes([0x04])])
    prev_end = {}
    starts = {}
    for ins in D.iter_code(body, 0, len(body)):
        starts[ins.off] = ins.op
        prev_end[ins.end] = ins.op
    for off, op in starts.items():
        if op == JMP_IFNOT:
            assert prev_end.get(off) == 0x05   # its consumer sits right behind it


def test_backward_ifnot_still_refused():
    with pytest.raises(ValueError, match="forward-only"):
        asm([label("top"), NOP8, (JMP_IFNOT, "top")])


def test_behavior_compiles_far_past_the_old_ceiling():
    """The e2e: a roster whose ticker would have died in struct.pack now
    compiles, and every jump the walker sees is in range and on-boundary."""
    from ff9mapkit.content import behavior as B

    units = [B.UnitSpec(f"u{i}", entry=2 + i, spawn=(i * 50, 0), hp=5)
             for i in range(30)]
    fb = B.FieldBehavior(units)
    for i, u in enumerate(units):
        others = [f"u{j}" for j in range(30) if j != i][:12]
        branches = [B.Sequence(fb.hp_le(u.name, 0), B.Do(B.Die()))]
        for o in others:
            branches.append(B.Sequence(fb.active(o), fb.near(u.name, o, 250),
                                       B.Do(B.SwingAt(o))))
        branches.append(B.Do(B.Hold((i * 50, 0))))
        fb.units[u.name].tree = B.Selector(*branches)
    cb = fb.compile()
    assert len(cb.ticker_body) > 40000         # far past the old ~32.7KB wall
    starts = set()
    for ins in D.iter_code(cb.ticker_body, 0, len(cb.ticker_body)):
        starts.add(ins.off)
        assert ins.end <= len(cb.ticker_body)
    for ins in D.iter_code(cb.ticker_body, 0, len(cb.ticker_body)):
        if ins.op in (0x01, 0x02, 0x03):
            t = D.jump_target(ins)
            assert t is None or t in starts | {len(cb.ticker_body)}
    # determinism holds through relaxation
    fb2 = B.FieldBehavior(list(units))
    for i, u in enumerate(units):
        others = [f"u{j}" for j in range(30) if j != i][:12]
        branches = [B.Sequence(fb2.hp_le(u.name, 0), B.Do(B.Die()))]
        for o in others:
            branches.append(B.Sequence(fb2.active(o), fb2.near(u.name, o, 250),
                                       B.Do(B.SwingAt(o))))
        branches.append(B.Do(B.Hold((i * 50, 0))))
        fb2.units[u.name].tree = B.Selector(*branches)
    assert fb2.compile().stable_hash() == cb.stable_hash()


def test_dense_same_target_long_jumps_reuse_one_island():
    """The stress case a future generator could emit: thousands of long jumps
    bailing to ONE far label. Without island reuse each would mint its own
    island (6 bytes + a fixpoint round apiece) and blow the convergence cap;
    with reuse the whole field shares a hop chain."""
    stmt = bytes([0x05, 0x7D, 0x01, 0x00, 0x7F])
    pairs = [x for _ in range(3000) for x in (stmt, (JMP_IF, "far"))]
    filler = [NOP8] * 5000                     # 40KB between the field and the label
    body = asm([*pairs, *filler, label("far"), bytes([0x04])])
    content = 3000 * 8 + 5000 * 8 + 1
    assert len(body) - content <= 10 * 6       # a handful of islands, not thousands
    # first and last conditional both land on the terminator through the chain
    assert body[_first_target(body, JMP_IF)] == 0x04
    for ins in D.iter_code(body, 0, len(body)):
        if ins.op == JMP_IF:
            last = ins
    (rel,) = struct.unpack_from("<h", body, last.off + 1)
    assert body[_follow(body, last.off + 3 + rel)] == 0x04


def test_many_distinct_far_targets_all_reach():
    """300 long jumps to 300 DISTINCT far labels — no reuse possible, every one
    needs its own island, and the fixpoint must converge with every target
    reached. The tail labels sit exactly 8 bytes apart (islands cluster in the
    filler, never in the tail), so landing offsets must be an exact 8-stride."""
    n = 300
    head = [(JMP, f"far{i}") for i in range(n)]
    filler = [NOP8] * 5000
    tail = []
    for i in range(n - 1):
        tail += [label(f"far{i}"), NOP8]
    tail += [label(f"far{n - 1}"), bytes([0x04])]
    body = asm([*head, *filler, *tail])
    offs = [_follow(body, i * 3) for i in range(n)]
    assert offs == [offs[0] + 8 * i for i in range(n)]
    assert offs[-1] == len(body) - 1 and body[offs[-1]] == 0x04
    for ins in D.iter_code(body, 0, len(body)):
        assert ins.end <= len(body)


def test_append_entry_boundary_at_255():
    """The OTHER file wall: entry_count is a single header byte. The chunked
    growth must not overshoot the 255 ceiling while slots still fit — and slot
    255 itself must be refused loudly, never wrapped."""
    from ff9mapkit.eb import edit as E

    base = bytearray(128 + 80)
    base[3] = 10
    eb = bytes(base)
    entry = bytes([2, 1]) + struct.pack("<HH", 0, 4) + bytes([0x04])
    for slot in range(0, 255, 7):              # stride keeps the loop cheap; the
        eb = E.append_entry(eb, slot, entry)   # grow path exercises every chunk
    eb = E.append_entry(eb, 254, entry)        # the last slot still fits
    assert eb[3] == 255                        # clamped exactly at the ceiling
    with pytest.raises(ValueError, match="at most 255"):
        E.append_entry(eb, 255, entry)


def test_append_entry_refuses_u16_overflow():
    """The next wall after relaxation: entry-table offsets are u16 and set_u16
    MASKS — an oversized file must fail LOUDLY, never register a wrapped offset."""
    from ff9mapkit.eb import edit as E
    from ff9mapkit.eb.model import EbScript

    base = bytearray(128 + 80)                 # header + a 10-slot table
    base[3] = 10
    eb = bytes(base)
    entry = bytes([2, 1]) + struct.pack("<HH", 0, 4) + bytes([0x04])
    eb = E.append_entry(eb, 0, entry + bytes(40000))     # two entries push the
    eb = E.append_entry(eb, 1, entry + bytes(30000))     # FILE past the u16 reach
    with pytest.raises(ValueError, match="too large"):
        E.append_entry(eb, 2, entry)
    with pytest.raises(ValueError, match="entry size"):
        E.append_entry(bytes(base), 1, bytes(70000))
