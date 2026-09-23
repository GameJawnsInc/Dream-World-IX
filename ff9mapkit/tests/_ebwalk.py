"""Walk the ops a ``.eb`` function can actually EXECUTE (shared test helper).

A linear disassembly also lists bytes a ``JMP`` skips, so it cannot tell a live ``0x00`` -- a one-tick yield in
the engine (``DoEventCode`` ``case NOP`` returns 1) -- from dead filler. This follows control flow instead.
"""
from __future__ import annotations

import struct

from ff9mapkit.eb import EbScript


def executed_ops(ebb, entry_index: int, tag: int) -> list:
    """The ops of ``entry_index``'s function ``tag`` reachable from its start: follows JMP (0x01), both arms of
    JMP_IFNOT/JMP_IF (0x02/0x03), and stops at RET (0x04). Returned in address order."""
    eb = EbScript.from_bytes(ebb)
    f = eb.entry(entry_index).func_by_tag(tag)
    by_off = {i.off: i for i in eb.instrs(f)}
    order = sorted(by_off)
    after = dict(zip(order, order[1:]))
    seen, todo = {}, [f.abs_start]
    while todo:
        off = todo.pop()
        if off in seen or off not in by_off:
            continue
        ins = seen[off] = by_off[off]
        nxt = [after[off]] if off in after else []
        if ins.op in (0x01, 0x02, 0x03):
            todo.append(off + 3 + struct.unpack_from("<h", eb.data, off + 1)[0])
            if ins.op != 0x01:
                todo += nxt
        elif ins.op != 0x04:
            todo += nxt
    return [seen[k].op for k in sorted(seen)]
