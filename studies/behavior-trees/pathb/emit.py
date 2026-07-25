"""Emit the compiled-roadmap lookup as REAL .eb bytes and measure it.

Uses the shipped emitters (behavior._stmt / eb.labelasm.asm), so every byte count
here is what the compiler would actually produce -- not an estimate.
"""
from __future__ import annotations

import sys

sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/unruffled-moser-861897/ff9mapkit")

from ff9mapkit.content.behavior import _set_byte, _set_int16, _stmt  # noqa: E402
from ff9mapkit.eb.labelasm import JMP, JMP_IFNOT, asm, label  # noqa: E402

SREG, TREG, NR = 1300, 1301, 1302          # blackboard bytes (illustrative indices)
TX, TZ = 1304, 1306                        # the unit's target Int16s


def emit_next_chain(NEXT):
    """NEXT[r][s] -> next region. The unrolled all-pairs table."""
    R = len(NEXT)
    out = []
    for r in range(R):
        out += [_stmt(f"Global.Byte[{SREG}] const({r}) B_EQ"), (JMP_IFNOT, f"r{r}")]
        for s in range(R):
            n = NEXT[r][s]
            if n < 0:
                continue
            out += [_stmt(f"Global.Byte[{TREG}] const({s}) B_EQ"), (JMP_IFNOT, f"r{r}s{s}"),
                    _set_byte(NR, n), (JMP, "done"), label(f"r{r}s{s}")]
        out += [label(f"r{r}")]
    out += [label("done")]
    return asm(out)


def emit_waypoint_chain(portals):
    """(sreg, nr) -> the portal midpoint written into the unit's target GLOBs."""
    out = []
    for i, ((a, b), (mid, _len, _t1, _t2)) in enumerate(sorted(portals.items())):
        out += [_stmt(f"Global.Byte[{SREG}] const({a}) B_EQ "
                      f"Global.Byte[{NR}] const({b}) B_EQ B_ANDAND"),
                (JMP_IFNOT, f"w{i}"),
                _set_int16(TX, int(mid[0])), _set_int16(TZ, int(mid[1])),
                (JMP, "wdone"), label(f"w{i}")]
    out += [label("wdone")]
    return asm(out)


def emit_membership_full(regions_aabb):
    """Worst case: a FULL region rescan from (x,z) by axis-aligned box chain.
    (Unsound in general -- regions are not boxes -- but this is the cheapest
    possible full-scan shape, so its size is a LOWER BOUND on the real thing.)"""
    out = []
    for r, (x0, x1, z0, z1) in enumerate(regions_aabb):
        out += [_stmt(f"Global.Int16[{TX}] const({x0}) B_GT Global.Int16[{TX}] const({x1}) B_LT "
                      f"B_ANDAND Global.Int16[{TZ}] const({z0}) B_GT B_ANDAND "
                      f"Global.Int16[{TZ}] const({z1}) B_LT B_ANDAND"),
                (JMP_IFNOT, f"m{r}"), _set_byte(SREG, r), (JMP, "mdone"), label(f"m{r}")]
    out += [label("mdone")]
    return asm(out)


def emit_incremental_membership(portals, reg_byte):
    """The cheap alternative: a tracked region byte that only ever steps to a
    NEIGHBOUR. Per portal, a half-plane crossing test  a*x + b*z > c  (Int24-safe
    with a,b scaled to +-64) plus the region write."""
    out = []
    for i, (a, b) in enumerate(sorted(portals)):
        out += [_stmt(f"Global.Byte[{reg_byte}] const({a}) B_EQ"), (JMP_IFNOT, f"p{i}"),
                # half-plane: 64*nx*(x-px) + 64*nz*(z-pz) > 0   (constants folded)
                _stmt(f"Global.Int16[{TX}] const(37) B_MULT Global.Int16[{TZ}] const(52) B_MULT "
                      f"B_PLUS const(12345) B_GT"),
                (JMP_IFNOT, f"p{i}"), _set_byte(reg_byte, b), (JMP, "idone"), label(f"p{i}")]
    out += [label("idone")]
    return asm(out)
