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
"""
from __future__ import annotations

import struct

JMP, JMP_IFNOT, JMP_IF = 0x01, 0x02, 0x03


def label(name: str) -> tuple:
    """A zero-width position marker (sugar for ``("label", name)``)."""
    return ("label", name)


def asm(blocks) -> bytes:
    """Assemble a block list into body bytes, resolving every label. Raises
    ``KeyError`` on an undefined label and ``ValueError`` on a backward JMP_IFNOT."""
    pos, labels = 0, {}
    for it in blocks:
        if isinstance(it, tuple) and it[0] == "label":
            labels[it[1]] = pos
        elif isinstance(it, tuple):
            pos += 3
        else:
            pos += len(it)
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
