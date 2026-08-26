"""Constant-fold reachability over one .eb function's CFG.

Hypothesis under test: the compiled chest/gift idiom emits
    SET(const 0|1) ; JMP_IFNOT/JMP_IF
so one arm of each such branch is statically dead. The kit's FuncFlow does NOT
constant-fold, so those arms are counted as live grant sites.
"""
from __future__ import annotations
import os, sys

_REPO = r"C:/gd/Dream-World-IX/.claude/worktrees/ff9-completion-journal-research-d86041"
for p in (os.path.join(_REPO, "ff9mapkit"), _REPO):
    if p not in sys.path:
        sys.path.insert(0, p)

from ff9mapkit.eb.cfg import OP_SET, OP_JMP_IFNOT, OP_JMP_IF, jump_target  # noqa


def const_value(raw: bytes, ins) -> int | None:
    """If the SET statement at *ins* is a single literal constant, return it."""
    if ins.op != OP_SET:
        return None
    pos, limit = ins.off + 1, ins.end
    if pos >= limit:
        return None
    o = raw[pos]
    if o == 0x7D and pos + 3 <= limit:
        v = raw[pos + 1] | (raw[pos + 2] << 8)
        if v >= 0x8000:
            v -= 0x10000
        return v if raw[pos + 3] == 0x7F else None
    if o == 0x7E and pos + 5 <= limit:
        v = (raw[pos + 1] | (raw[pos + 2] << 8) | (raw[pos + 3] << 16) | (raw[pos + 4] << 24))
        return v if raw[pos + 5] == 0x7F else None
    return None


def folded_reach(fl, raw: bytes) -> set[int]:
    """Block indices reachable from the entry when const-only branch conditions are folded."""
    seen = {fl.entry}
    stack = [fl.entry]
    while stack:
        b = stack.pop()
        blk = fl.blocks[b]
        term = blk.instrs[-1] if blk.instrs else None
        cv = None
        if term is not None and term.op in (OP_JMP_IFNOT, OP_JMP_IF):
            prev = blk.instrs[-2] if len(blk.instrs) >= 2 else None
            if prev is not None:
                cv = const_value(raw, prev)
        succs = [s for s, _c in blk.succs]
        if cv is not None and term is not None and len(succs) == 2:
            tgt = jump_target(term)
            tb = fl.block_at(tgt)
            fall = fl.block_at(term.end)
            if term.op == OP_JMP_IFNOT:
                take = tb if cv == 0 else fall
            else:
                take = tb if cv != 0 else fall
            succs = [take] if take is not None else succs
        for s in succs:
            if s is not None and s not in seen:
                seen.add(s)
                stack.append(s)
    return seen
