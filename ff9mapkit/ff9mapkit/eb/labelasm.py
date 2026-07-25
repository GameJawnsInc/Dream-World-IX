"""The `.eb` LABEL ASSEMBLER — two-pass jump resolution for authored function bodies.

Promoted verbatim from the fort-condor study's `asm()` (studies/fort-condor/swarm_bench.py,
where it assembled every referee/duty/fight body of the proven skirmish bench) so the
behavior-tree compiler (:mod:`ff9mapkit.content.behavior`) and future authored-logic
generators share ONE jump encoder.

A body is a list of items:
  * ``bytes`` — literal instructions (from :mod:`ff9mapkit.eb.opcodes` /
    :func:`ff9mapkit.eb.exprasm.assemble`);
  * ``("label", name)`` — a zero-width position marker;
  * ``(JMP | JMP_IF | JMP_IFNOT, name)`` — a 3-byte relative jump to that label.

Engine truth (Memoria ``EBin.jumpToCommand``): all three jumps carry a 16-bit offset
measured from the INSTRUCTION'S END; ``0x01`` JMP (``bra()``) and ``0x03`` JMP_IF
(``bne()``) are SIGNED, ``0x02`` JMP_IFNOT (``beq()`` via ``getUShortIP``) is UNSIGNED —
forward-only, and this assembler refuses a backward JMP_IFNOT rather than emit a wild
positive offset. The conditional jumps consume the value pushed by a preceding ``0x05``
expression statement (see the CalcStack desync law in [[project-ff9-fort-condor-rts]]).

LONG-JUMP RELAXATION (the fort-condor rung-5 capacity finding): a signed span is
±32767, so any body past ~32KB used to die in ``struct.pack`` — a hard ceiling on how
much behavior one ticker can hold. ``asm()`` now RELAXES: an out-of-range jump is
re-routed through an inserted ISLAND (``JMP skip; island: JMP target; skip:`` — 6
bytes, jumped over by fall-through so it is safe at ANY block boundary), iterated to a
fixpoint since each insertion shifts later offsets; a span beyond two hops chains
islands naturally (an island's own jump is scanned like any other). Two invariants:
a body with NO out-of-range jump assembles BYTE-IDENTICAL to the pre-relaxation
encoder (golden stability), and an island is never inserted between an expression
statement and the conditional jump that consumes it (the belt-and-braces stance on
the engine's condition register — an unconditional hop between push and test is not
a pattern any shipped field exercises).
"""
from __future__ import annotations

import struct

JMP, JMP_IFNOT, JMP_IF = 0x01, 0x02, 0x03

# stay clear of the true limits so the 6-byte shifts of LATER insertions rarely
# push an already-routed hop back out of range (the fixpoint loop still catches
# any that do)
_SIGNED_REACH = 30000
_UNSIGNED_REACH = 63000
_ISLAND_PREFIX = "__isl"


def label(name: str) -> tuple:
    """A zero-width position marker (sugar for ``("label", name)``)."""
    return ("label", name)


def _measure(blocks) -> tuple:
    """(label -> position, item index -> position, total size)."""
    labels, at, pos = {}, [], 0
    for it in blocks:
        at.append(pos)
        if isinstance(it, tuple) and it[0] == "label":
            labels[it[1]] = pos
        elif isinstance(it, tuple):
            pos += 3
        else:
            pos += len(it)
    return labels, at, pos


def _first_long_jump(blocks, labels, at):
    """Index of the first jump whose span exceeds its op's SAFE reach, or None.
    JMP_IFNOT is unsigned forward (huge reach); backward JMP_IFNOT stays a hard
    error at emit time — no island can make a backward hop unsigned."""
    for i, it in enumerate(blocks):
        if not (isinstance(it, tuple) and it[0] != "label"):
            continue
        op, target = it
        off = labels[target] - (at[i] + 3)
        if op == JMP_IFNOT:
            if off > _UNSIGNED_REACH:
                return i
        elif not -_SIGNED_REACH <= off <= _SIGNED_REACH:
            return i
    return None


def _insert_island(blocks, ji, labels, at, total: int, ctr: int):
    """Route blocks[ji]'s jump through a fresh island: pick the legal block
    boundary nearest to one-SAFE-reach toward the target, STRICTLY BETWEEN the
    jump and its target (that is the progress guarantee — every hop shortens
    the remaining span, so chains terminate)."""
    op, target = blocks[ji]
    src_end = at[ji] + 3
    tgt = labels[target]
    lo, hi = (src_end, tgt) if tgt > src_end else (tgt, src_end)
    goal = src_end + (_SIGNED_REACH - 200) * (1 if tgt > src_end else -1)

    def boundary_pos(k: int) -> int:
        return at[k] if k < len(blocks) else total

    def legal(k: int) -> bool:
        # never split an expression statement from the conditional that consumes
        # its value: no island directly before a conditional-jump tuple
        return not (k < len(blocks) and isinstance(blocks[k], tuple)
                    and blocks[k][0] in (JMP_IF, JMP_IFNOT))

    best, best_d = None, None
    for k in range(len(blocks) + 1):
        p = boundary_pos(k)
        if not lo < p < hi:                  # strictly between = guaranteed progress
            continue
        if not legal(k):
            continue
        d = abs(p - goal)
        if best_d is None or d < best_d:
            best, best_d = k, d
    if best is None:
        raise ValueError(f"no legal island site between a long jump and {target!r}")
    isl = f"{_ISLAND_PREFIX}{ctr}"
    skip = f"{_ISLAND_PREFIX}{ctr}s"
    blocks[ji] = (op, isl)                   # the original jump now hops to the island
    blocks[best:best] = [(JMP, skip), ("label", isl), (JMP, target), ("label", skip)]
    return blocks


def asm(blocks) -> bytes:
    """Assemble a block list into body bytes, resolving every label — with
    long-jump relaxation. Raises ``KeyError`` on an undefined label,
    ``ValueError`` on a backward JMP_IFNOT or a non-converging relaxation."""
    blocks = list(blocks)
    ctr = 0
    for _round in range(400):
        labels, at, total = _measure(blocks)
        ji = _first_long_jump(blocks, labels, at)
        if ji is None:
            break
        blocks = _insert_island(blocks, ji, labels, at, total, ctr)
        ctr += 1
    else:
        raise ValueError("long-jump relaxation did not converge (400 islands?)")

    out, pos = bytearray(), 0
    for it in blocks:
        if isinstance(it, tuple) and it[0] == "label":
            continue
        if isinstance(it, tuple):
            op, target = it
            off = labels[target] - (pos + 3)
            if op == JMP_IFNOT:
                if off < 0:
                    raise ValueError(f"JMP_IFNOT is forward-only (to {target!r})")
                out += bytes([op]) + struct.pack("<H", off)
            else:
                out += bytes([op]) + struct.pack("<h", off)
            pos += 3
        else:
            out += it
            pos += len(it)
    return bytes(out)
