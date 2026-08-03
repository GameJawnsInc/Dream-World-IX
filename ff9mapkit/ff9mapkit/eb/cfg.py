"""Control-flow + dominator analysis over one ``.eb`` function's bytecode.

The rung-0 instrument of the narrative-state arc (``studies/narrative-state/PLAN.md``): given a
function's byte span, build its basic-block graph, compute dominators, and attribute **guard
conditions** — the comparisons that must hold for control to reach a given instruction. The
per-bit story-order model (rung 4) and the demand-driven ``story-seed`` (rung 1) both consume
this; the old census could only say "this field writes bit B", this layer says "bit B is written
under ``ScenarioCounter == 6800``".

Grounding (mirrors the engine, same reader as ``disasm``):
  * A conditional jump (``JMP_IFNOT`` 0x02 / ``JMP_IF`` 0x03) tests the value of the immediately
    preceding ``SET`` (0x05) expression statement — the compiled idiom throughout the corpus
    (``SET({... B_EQ ...})`` then ``JMP_IFNOT(L)``). A jump with no preceding ``SET`` in its own
    block keeps its edges but carries no condition.
  * A switch (0x06/0x0B/0x0D) dispatches on the value of the preceding bare-read ``SET``; each
    case edge carries ``selector == value`` (or ``in {values}`` when several cases share a target).
  * ``JMP`` (0x01) is unconditional; ``RET`` (0x04) ends the block with no successors; everything
    else falls through.

Soundness stance: guards are attributed only where they PROVABLY hold — a condition attaches to
the blocks dominated by the branch's successor, and only when that successor has a single
in-edge group (a join point kills the claim). Compound conditions joined by AND contribute every
atom; an OR/opaque compound contributes nothing (counted, never guessed). Negations are emitted
only for single atoms. Errors degrade loudly: a function that fails to decode raises
:class:`CfgError` — callers count and skip, never silently narrow.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .disasm import Instr, decode_switch, jump_target, read_code

OP_SET = 0x05
OP_JMP = 0x01
OP_JMP_IFNOT = 0x02
OP_JMP_IF = 0x03
OP_RET = 0x04
SWITCH_OPS = (0x06, 0x0B, 0x0D)

# expression-token operator families (token values, from the engine's op_binary table)
_CMP_TOKENS = {24: "<", 25: ">", 26: "<=", 27: ">=", 28: "<", 29: ">", 30: "<=", 31: ">=",
               32: "==", 33: "!=", 34: "==", 35: "!="}
_NEGATE = {"<": ">=", ">": "<=", "<=": ">", ">=": "<", "==": "!=", "!=": "=="}
_AND_TOKENS = {36, 39}          # B_AND / B_ANDAND -- both operands must hold
_NOT_TOKENS = {14, 15, 16}      # B_NOT / B_NOT_E / B_COMP
_ASSIGN_PURE = {44, 45, 46}     # B_LET / B_LET_A / B_LET_E
_ASSIGN_ALL = frozenset(range(44, 70))
_T_CONST, _T_CONST4, _T_END = 0x7D, 0x7E, 0x7F


class CfgError(ValueError):
    """A function whose bytes cannot be soundly analyzed (decode overrun, off-boundary jump,
    undecodable switch). Callers skip the function and COUNT it — never analyze a guess."""


# ---------------------------------------------------------------------------
# expression parsing (structured, RPN-aware for the shapes the compiler emits)

@dataclass(frozen=True)
class Cond:
    """One atomic guard: ``Source.Type[index] <cmp> value``.

    ``source``/``vtype`` follow the engine's VariableSource/VariableType encoding (source 0 =
    Global i.e. ``gEventGlobal``; vtype 0/1 = bit, 5 = byte, 6/7 = int16/uint16). ``cmp`` is a
    normalized operator string; ``'in'`` means ``value`` is a sorted tuple of allowed selector
    values (switch cases sharing a target). A bare flag truth-test normalizes to ``!= 0``."""

    source: int
    vtype: int
    index: int
    cmp: str
    value: object       # int, or tuple[int, ...] when cmp == 'in'

    @property
    def is_scenario(self) -> bool:
        return self.source == 0 and self.vtype in (6, 7) and self.index == 0

    @property
    def is_glob_bit(self) -> bool:
        return self.source == 0 and self.vtype in (0, 1)

    def negate(self) -> "Cond | None":
        if self.cmp in _NEGATE:
            return Cond(self.source, self.vtype, self.index, _NEGATE[self.cmp], self.value)
        return None                                  # 'in' -- no single-atom negation


_LEAF_VAR = "var"
_LEAF_CONST = "const"
_LEAF_OPAQUE = "opaque"
_LEAF_COND = "cond"
_LEAF_GROUP = "group"      # an AND-group of Conds


def _read_i16(raw: bytes, pos: int) -> int:
    v = raw[pos] | (raw[pos + 1] << 8)
    return v - 0x10000 if v >= 0x8000 else v


def parse_expr_conds(raw: bytes, pos: int, limit: int):
    """Parse the expression token stream at *pos* (ends at ``B_EXPR_END``) into
    ``(conds, kind, end_pos)``. ``kind``:

    * ``'atomic'`` — exactly one comparison/truth-test; ``conds`` = (Cond,)
    * ``'and'``    — several atoms all joined by AND; ``conds`` = every atom
    * ``'unsure'`` — a compound the parser cannot vouch for (OR/arith/opaque); ``conds`` = ()
    * ``'none'``   — no condition content (a bare non-testable expression)

    The walk is byte-exact with ``disasm.read_expr``; only the *interpretation* is added."""
    stack: list = []
    unsure = False
    while True:
        if pos >= limit:
            raise CfgError("expression ran past its statement bounds")
        o = raw[pos]; pos += 1
        if o == 0xD3:                               # flexible varfunc: u16 id + u8 argc
            pos += 3
            stack.append((_LEAF_OPAQUE,))
            continue
        if o == _T_CONST:
            stack.append((_LEAF_CONST, _read_i16(raw, pos))); pos += 2
            continue
        if o == _T_CONST4:
            v = raw[pos] | (raw[pos + 1] << 8) | (raw[pos + 2] << 16) | (raw[pos + 3] << 24)
            stack.append((_LEAF_CONST, v)); pos += 4
            continue
        if o >= 0xC0:                               # a variable token
            if o >= 0xE0:
                idx = raw[pos] | (raw[pos + 1] << 8); pos += 2
            else:
                idx = raw[pos]; pos += 1
            stack.append((_LEAF_VAR, o & 3, (o >> 2) & 7, idx))
            continue
        if o in (0x29, 0x5F, 0x79, 0x7A):           # B_MEMBER/B_PTR/B_SYSLIST/B_SYSVAR
            pos += 1
            stack.append((_LEAF_OPAQUE,))
            continue
        if o == 0x78:                               # B_OBJSPECA: uid + field
            pos += 2
            stack.append((_LEAF_OPAQUE,))
            continue
        if o == _T_END:
            break
        # a pure operator
        if o in _CMP_TOKENS:
            if len(stack) >= 2:
                b = stack.pop(); a = stack.pop()
                if a[0] == _LEAF_VAR and b[0] == _LEAF_CONST:
                    stack.append((_LEAF_COND, Cond(a[1], a[2], a[3], _CMP_TOKENS[o], b[1])))
                    continue
                if a[0] == _LEAF_CONST and b[0] == _LEAF_VAR:
                    # const <cmp> var  ==  var <mirrored-cmp> const (mirror, not negate)
                    mirror = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}
                    c = _CMP_TOKENS[o]
                    stack.append((_LEAF_COND, Cond(b[1], b[2], b[3], mirror.get(c, c), a[1])))
                    continue
            stack.append((_LEAF_OPAQUE,))
            unsure = True
            continue
        if o in _AND_TOKENS:
            if len(stack) >= 2:
                b = stack.pop(); a = stack.pop()
                atoms: list[Cond] = []
                ok = True
                for side in (a, b):
                    if side[0] == _LEAF_COND:
                        atoms.append(side[1])
                    elif side[0] == _LEAF_GROUP:
                        atoms.extend(side[1])
                    elif side[0] == _LEAF_VAR and side[2] in (0, 1):
                        atoms.append(Cond(side[1], side[2], side[3], "!=", 0))
                    else:
                        ok = False
                if ok:
                    stack.append((_LEAF_GROUP, tuple(atoms)))
                    continue
            stack.append((_LEAF_OPAQUE,))
            unsure = True
            continue
        if o in _NOT_TOKENS:
            if stack:
                a = stack.pop()
                if a[0] == _LEAF_COND:
                    neg = a[1].negate()
                    if neg is not None:
                        stack.append((_LEAF_COND, neg))
                        continue
                elif a[0] == _LEAF_VAR and a[2] in (0, 1):     # !flag
                    stack.append((_LEAF_COND, Cond(a[1], a[2], a[3], "==", 0)))
                    continue
            stack.append((_LEAF_OPAQUE,))
            unsure = True
            continue
        # any other operator (arith, OR, XOR, shifts, assignment...): opaque
        if len(stack) >= 2:
            stack.pop(); stack.pop()
            stack.append((_LEAF_OPAQUE,))
        elif stack:
            stack.pop(); stack.append((_LEAF_OPAQUE,))
        unsure = True
    # interpret the final stack
    if len(stack) == 1:
        top = stack[0]
        if top[0] == _LEAF_COND:
            return (top[1],), "atomic", pos
        if top[0] == _LEAF_GROUP:
            return tuple(top[1]), "and", pos
        if top[0] == _LEAF_VAR and top[2] in (0, 1):           # bare flag truth-test
            return (Cond(top[1], top[2], top[3], "!=", 0),), "atomic", pos
    return (), ("unsure" if unsure or stack else "none"), pos


# ---------------------------------------------------------------------------
# statement parsing (the 0x05 SET shapes)

@dataclass(frozen=True)
class SetStmt:
    """A parsed ``SET`` statement.

    ``kind``: ``'assign'`` (var <op>= value), ``'cond'`` (a condition feeding a branch),
    ``'read'`` (a bare var read — a switch selector), ``'other'`` (anything else).
    ``value`` is the literal for a simple const assignment, else None (computed).
    ``pure`` is True for plain ``B_LET`` (not compound +=/&=...)."""

    off: int
    kind: str
    source: int | None = None
    vtype: int | None = None
    index: int | None = None
    op_token: int | None = None
    value: int | None = None
    pure: bool = False
    conds: tuple = ()
    cond_kind: str = "none"


def parse_set(raw: bytes, ins: Instr) -> SetStmt:
    """Parse one 0x05 instruction. The expression begins at ``ins.off + 1`` (the opcode byte;
    SET's argFlag is implicit — mirrored from ``disasm.read_code``)."""
    pos = ins.off + 1
    limit = ins.end
    b = raw[pos] if pos < limit else 0
    if b < 0xC0:                                     # not var-led: parse as condition anyway
        conds, ck, _ = parse_expr_conds(raw, pos, limit)
        return SetStmt(ins.off, "cond" if conds else "other", conds=conds, cond_kind=ck)
    if b >= 0xE0:
        src, vt, idx = b & 3, (b >> 2) & 7, raw[pos + 1] | (raw[pos + 2] << 8)
        pos += 3
    else:
        src, vt, idx = b & 3, (b >> 2) & 7, raw[pos + 1]
        pos += 2
    # walk the remaining tokens; find the LAST operator before END and whether the value part
    # is exactly one constant
    tokens: list = []
    last_op = None
    scan = pos
    while scan < limit:
        o = raw[scan]; scan += 1
        if o == 0xD3:
            scan += 3; tokens.append((_LEAF_OPAQUE,)); continue
        if o == _T_CONST:
            tokens.append((_LEAF_CONST, _read_i16(raw, scan))); scan += 2; continue
        if o == _T_CONST4:
            v = raw[scan] | (raw[scan + 1] << 8) | (raw[scan + 2] << 16) | (raw[scan + 3] << 24)
            tokens.append((_LEAF_CONST, v)); scan += 4; continue
        if o >= 0xE0:
            scan += 2; tokens.append((_LEAF_VAR,)); continue
        if o >= 0xC0:
            scan += 1; tokens.append((_LEAF_VAR,)); continue
        if o in (0x29, 0x5F, 0x79, 0x7A):
            scan += 1; tokens.append((_LEAF_OPAQUE,)); continue
        if o == 0x78:
            scan += 2; tokens.append((_LEAF_OPAQUE,)); continue
        if o == _T_END:
            break
        last_op = o
        tokens.append(("op", o))
    if last_op in _ASSIGN_ALL:
        simple = (len(tokens) == 2 and tokens[0][0] == _LEAF_CONST and tokens[1] == ("op", last_op))
        return SetStmt(ins.off, "assign", src, vt, idx, last_op,
                       tokens[0][1] if simple else None, last_op in _ASSIGN_PURE)
    if last_op is None and not tokens:               # bare read: `SET({Var})`
        return SetStmt(ins.off, "read", src, vt, idx)
    conds, ck, _ = parse_expr_conds(raw, ins.off + 1, limit)
    return SetStmt(ins.off, "cond" if conds else "other", src, vt, idx, conds=conds, cond_kind=ck)


# ---------------------------------------------------------------------------
# the CFG

@dataclass
class Block:
    index: int
    start: int
    end: int
    instrs: list = field(default_factory=list)       # Instr list
    succs: list = field(default_factory=list)        # [(block_index, conds tuple | None)]
    preds: list = field(default_factory=list)        # [block_index] (one entry PER in-edge)


class FuncFlow:
    """The analyzed function: blocks, dominators, per-block guards.

    Build with :meth:`build`; query with :meth:`guards_at` (absolute byte offset of an
    instruction → the tuple of :class:`Cond` proven to hold there, or None for dead code)."""

    def __init__(self, blocks, entry, dom, block_of, stats):
        self.blocks = blocks
        self.entry = entry
        self._dom = dom                              # per-block bitmask of dominators
        self._block_of = block_of                    # instr offset -> block index
        self.stats = stats                           # {'negated_compound': n, 'unsure_conds': n}
        self._guard_cache: dict[int, tuple] = {}

    # -- construction -------------------------------------------------------

    @classmethod
    def build(cls, data: bytes, start: int, end: int) -> "FuncFlow":
        instrs: list[Instr] = []
        pos = start
        while pos < end:
            try:
                ins, pos = read_code(data, pos)
            except (IndexError, KeyError) as exc:    # pragma: no cover - malformed input
                raise CfgError(f"decode failed at 0x{pos:X}: {exc}") from exc
            if ins.end > end:
                raise CfgError(f"instruction at 0x{ins.off:X} overruns the function end")
            instrs.append(ins)
        offs = {i.off for i in instrs}
        by_off = {i.off: k for k, i in enumerate(instrs)}

        # leaders: entry, every jump/switch target, every instruction after a control op
        leaders = {start} if instrs else set()
        for ins in instrs:
            if ins.op in (OP_JMP, OP_JMP_IFNOT, OP_JMP_IF):
                t = jump_target(ins)
                if t is None or t == end:
                    if t is None:
                        raise CfgError(f"jump at 0x{ins.off:X} has no immediate target")
                elif t not in offs:
                    raise CfgError(f"jump at 0x{ins.off:X} targets 0x{t:X}, not an instruction boundary")
                if t is not None and t != end:
                    leaders.add(t)
                if ins.end < end:
                    leaders.add(ins.end)
            elif ins.op in SWITCH_OPS:
                si = decode_switch(ins)
                if si is None:
                    raise CfgError(f"undecodable switch at 0x{ins.off:X}")
                for e in si.edges:
                    if e.target == end:
                        continue
                    if e.target not in offs:
                        raise CfgError(f"switch at 0x{ins.off:X} targets 0x{e.target:X}, "
                                       "not an instruction boundary")
                    leaders.add(e.target)
                if ins.end < end:
                    leaders.add(ins.end)
            elif ins.op == OP_RET and ins.end < end:
                leaders.add(ins.end)

        blocks: list[Block] = []
        block_of: dict[int, int] = {}
        cur: Block | None = None
        for ins in instrs:
            if ins.off in leaders or cur is None:
                cur = Block(len(blocks), ins.off, ins.end)
                blocks.append(cur)
            cur.instrs.append(ins)
            cur.end = ins.end
            block_of[ins.off] = cur.index

        stats = {"negated_compound": 0, "unsure_conds": 0, "condless_branches": 0}

        def _branch_conds(blk: Block):
            """(true_conds, false_conds) from the SET immediately before the block's last instr."""
            if len(blk.instrs) >= 2 and blk.instrs[-2].op == OP_SET:
                st = parse_set(data, blk.instrs[-2])
                if st.kind == "cond" and st.conds:
                    true_side = st.conds
                    if st.cond_kind == "atomic":
                        neg = st.conds[0].negate()
                        false_side = (neg,) if neg is not None else None
                    else:
                        false_side = None
                        stats["negated_compound"] += 1
                    return true_side, false_side
                if st.kind == "read" and st.index is not None:
                    # bare-read truth test: `if (var) {...}` -- the common flag-gate idiom
                    return ((Cond(st.source, st.vtype, st.index, "!=", 0),),
                            (Cond(st.source, st.vtype, st.index, "==", 0),))
                if st.kind == "cond" and st.cond_kind == "unsure":
                    stats["unsure_conds"] += 1
            else:
                stats["condless_branches"] += 1
            return None, None

        def _selector(blk: Block):
            if len(blk.instrs) >= 2 and blk.instrs[-2].op == OP_SET:
                st = parse_set(data, blk.instrs[-2])
                if st.kind == "read":
                    return st.source, st.vtype, st.index
            return None

        for blk in blocks:
            last = blk.instrs[-1]
            if last.op == OP_RET:
                continue
            if last.op == OP_JMP:
                t = jump_target(last)
                if t is not None and t != end:
                    blk.succs.append((block_of[t], None))
                continue
            if last.op in (OP_JMP_IFNOT, OP_JMP_IF):
                t = jump_target(last)
                true_c, false_c = _branch_conds(blk)
                taken_c = false_c if last.op == OP_JMP_IFNOT else true_c
                fall_c = true_c if last.op == OP_JMP_IFNOT else false_c
                if last.end < end:
                    blk.succs.append((block_of[last.end], fall_c))
                if t is not None and t != end:
                    blk.succs.append((block_of[t], taken_c))
                continue
            if last.op in SWITCH_OPS:
                si = decode_switch(last)
                sel = _selector(blk)
                by_target: dict[int, list] = {}
                default_targets = set()
                for e in si.edges:
                    if e.value is None:
                        default_targets.add(e.target)
                    else:
                        by_target.setdefault(e.target, []).append(e.value)
                for t, values in by_target.items():
                    if t == end:
                        continue
                    conds = None
                    if sel is not None and t not in default_targets:
                        src, vt, idx = sel
                        if len(values) == 1:
                            conds = (Cond(src, vt, idx, "==", values[0]),)
                        else:
                            conds = (Cond(src, vt, idx, "in", tuple(sorted(values))),)
                    blk.succs.append((block_of[t], conds))
                for t in default_targets:
                    if t != end and t not in by_target:
                        blk.succs.append((block_of[t], None))
                continue
            if last.end < end:                        # plain fallthrough
                blk.succs.append((block_of[last.end], None))

        for blk in blocks:
            for (s, _c) in blk.succs:
                blocks[s].preds.append(blk.index)

        # dominators (iterative bitset dataflow over reachable blocks)
        n = len(blocks)
        entry = block_of.get(start, 0) if instrs else 0
        reach = 0
        if instrs:
            stack = [entry]
            while stack:
                b = stack.pop()
                if reach >> b & 1:
                    continue
                reach |= 1 << b
                for (s, _c) in blocks[b].succs:
                    if not (reach >> s & 1):
                        stack.append(s)
        all_mask = (1 << n) - 1
        dom = [all_mask] * n
        if instrs:
            dom[entry] = 1 << entry
            changed = True
            while changed:
                changed = False
                for b in range(n):
                    if b == entry or not (reach >> b & 1):
                        continue
                    m = all_mask
                    for p in blocks[b].preds:
                        if reach >> p & 1:
                            m &= dom[p]
                    m |= 1 << b
                    if m != dom[b]:
                        dom[b] = m
                        changed = True
        for b in range(n):
            if not (reach >> b & 1):
                dom[b] = 0                            # dead code: no dominance claims
        return cls(blocks, entry if instrs else 0, dom, block_of, stats)

    # -- queries ------------------------------------------------------------

    def block_at(self, off: int) -> int | None:
        return self._block_of.get(off)

    def guards_of_block(self, b: int) -> tuple | None:
        """Every Cond proven to hold on entry to block *b* (dead code → None)."""
        if self._dom[b] == 0:
            return None
        if b in self._guard_cache:
            return self._guard_cache[b]
        out: list[Cond] = []
        mask = self._dom[b]
        d = 0
        while mask:
            if mask & 1:
                blk = self.blocks[d]
                if d != self.entry and blk.preds and len(set(blk.preds)) == 1 \
                        and len(blk.preds) == 1:
                    p = blk.preds[0]
                    if self._dom[p]:
                        for (s, conds) in self.blocks[p].succs:
                            if s == d and conds:
                                out.extend(conds)
            mask >>= 1
            d += 1
        result = tuple(out)
        self._guard_cache[b] = result
        return result

    def guards_at(self, off: int) -> tuple | None:
        """Guards proven at the instruction starting at *off* (None = dead code / unknown off)."""
        b = self._block_of.get(off)
        if b is None:
            return None
        return self.guards_of_block(b)

    def dominated_by(self, d: int) -> list[int]:
        """Indices of every reachable block dominated by block *d* (including *d*)."""
        return [b for b in range(len(self.blocks)) if self._dom[b] and (self._dom[b] >> d) & 1]

    def iter_sets(self, data: bytes):
        """Yield ``(SetStmt, block_index)`` for every 0x05 statement in reachable blocks."""
        for blk in self.blocks:
            if self._dom[blk.index] == 0:
                continue
            for ins in blk.instrs:
                if ins.op == OP_SET:
                    yield parse_set(data, ins), blk.index

    def innermost_guard_block(self, b: int) -> int | None:
        """The nearest dominator of *b* that is entered via a conditioned single-pred edge —
        the root of *b*'s innermost guarded region (None if *b* is unguarded)."""
        if self._dom[b] == 0:
            return None
        best = None
        mask = self._dom[b]
        d = 0
        while mask:
            if mask & 1 and d != self.entry:
                blk = self.blocks[d]
                if len(blk.preds) == 1 and self._dom[blk.preds[0]]:
                    p = blk.preds[0]
                    if any(s == d and conds for (s, conds) in self.blocks[p].succs):
                        if best is None or self.blocks[d].start > self.blocks[best].start:
                            best = d
            mask >>= 1
            d += 1
        return best


# ---------------------------------------------------------------------------
# field-level context propagation (rung 0b): the arm/call graph

RUNSCRIPT_OPS = (0x10, 0x12, 0x14)      # RunScriptAsync/RunScript/RunScriptSync -- uid=imm(1), tag=imm(2)
MAIN_REINIT_TAG = 10                    # entry-0 tag 10 = after-battle re-entry (engine-invoked root)


class FieldFlow:
    """Whole-field guard propagation: per-function :class:`FuncFlow` plus the ARM/CALL graph.

    The scoping census measured that ~90% of story-bit writes live OUTSIDE Main_Init — the
    ScenarioCounter gate sits in Main_Init's arm (``SC==6800 -> InitObject(...)``) and the bits
    are written by the armed entry's own functions. This layer propagates a caller's proven
    guards into the functions it arms (``InitObject``/``InitCode``/``InitRegion`` — via
    ``eventscan.armed_slot``, the one owner of the arm semantics) and calls
    (``RunScript*`` by resolved uid+tag).

    Each propagated condition carries an ``armed`` flag: False = it held at the moment the
    callee was INVOKED (a synchronous call chain); True = it held when the handler was ARMED
    (the handler itself runs later — a tread/loop/interaction — so an SC equality is an
    arming-beat anchor, not an execution-time equality). Soundness: contexts start at TOP and
    are INTERSECTED over every in-edge (the available-expressions scheme); a function never
    reached from a root keeps NO context claims. Degraded functions (CfgError) contribute no
    edges and receive no claims."""

    def __init__(self, eb, flows, degraded, ctx, edges, stats):
        self.eb = eb
        self.flows = flows          # (entry_idx, func_idx) -> FuncFlow
        self.degraded = degraded    # {(entry_idx, func_idx): reason}
        self.ctx = ctx              # (entry_idx, func_idx) -> {Cond: armed_bool}
        self.edges = edges          # [(src_key, dst_key, guards tuple, armed_bool)]
        self.stats = stats

    @classmethod
    def build(cls, eb) -> "FieldFlow":
        from .. import eventscan                       # lazy: avoid an import cycle

        flows: dict = {}
        degraded: dict = {}
        keys_by_entry: dict[int, list] = {}
        tag_index: dict[tuple[int, int], tuple] = {}   # (entry_idx, tag) -> key
        stats = {"unresolved_calls": 0, "expr_calls": 0, "objcall_ops": 0}
        for e in eb.entries:
            if e.empty:
                continue
            for fi, f in enumerate(e.funcs):
                key = (e.index, fi)
                keys_by_entry.setdefault(e.index, []).append(key)
                if (e.index, f.tag) not in tag_index:
                    tag_index[(e.index, f.tag)] = key
                try:
                    flows[key] = FuncFlow.build(eb.data, f.abs_start, f.abs_end)
                except CfgError as exc:
                    degraded[key] = str(exc)

        pents = eventscan.resolve_player_entries(eb)
        n_entries = len(eb.entries)
        edges: list = []
        for key, fl in flows.items():
            ei, fi = key
            for blk in fl.blocks:
                if fl._dom[blk.index] == 0:
                    continue
                guards = fl.guards_of_block(blk.index) or ()
                for ins in blk.instrs:
                    slot = eventscan.armed_slot(ins)
                    if slot is not None:
                        for dst in keys_by_entry.get(slot, []):
                            edges.append((key, dst, guards, True))
                        continue
                    if ins.op in RUNSCRIPT_OPS:
                        uid, tag = ins.imm(1), ins.imm(2)
                        if uid is None or tag is None:
                            stats["expr_calls"] += 1
                            continue
                        _kind, targets = eventscan.resolve_uid(
                            uid, ei, player_entries=pents, entry_count=n_entries)
                        if not targets:
                            stats["unresolved_calls"] += 1
                            continue
                        for t in targets:
                            dst = tag_index.get((t, tag))
                            if dst is not None:
                                edges.append((key, dst, guards, False))
                    elif ins.op in (0x16, 0x18, 0x1A):    # RunScriptObject* -- not modeled yet
                        stats["objcall_ops"] += 1

        # roots: Main_Init (entry 0, first func) + entry-0 tag-10 Main_Reinit (engine-invoked)
        roots = set()
        if keys_by_entry.get(0):
            roots.add(keys_by_entry[0][0])
        r = tag_index.get((0, MAIN_REINIT_TAG))
        if r is not None:
            roots.add(r)

        TOP = None
        ctx: dict = {k: TOP for k in flows}
        for k in roots:
            ctx[k] = {}
        in_edges: dict = {}
        for (src, dst, guards, armed) in edges:
            in_edges.setdefault(dst, []).append((src, guards, armed))
        changed = True
        while changed:
            changed = False
            for dst, ins_list in in_edges.items():
                if dst in roots or dst not in ctx:
                    continue
                contribs = []
                for (src, guards, armed) in ins_list:
                    sctx = ctx.get(src, TOP)
                    if sctx is TOP:
                        continue                        # optimistic: constrain later if it lands
                    c = {cond: (a or armed) for cond, a in sctx.items()}
                    for cond in guards:
                        c[cond] = c.get(cond, armed) or armed
                    contribs.append(c)
                if len(contribs) < len(ins_list):
                    continue                            # claim only once EVERY in-edge is known
                merged = contribs[0]
                for c in contribs[1:]:
                    merged = {cond: (merged[cond] or c[cond]) for cond in merged.keys() & c.keys()}
                if ctx[dst] is TOP or merged != ctx[dst]:
                    ctx[dst] = merged
                    changed = True
        for k, v in ctx.items():
            if v is TOP:
                ctx[k] = {}                             # never reached from a root: no claims
        return cls(eb, flows, degraded, ctx, edges, stats)

    def guards_at(self, entry_idx: int, func_idx: int, off: int):
        """(direct, armed) Cond tuples at instruction *off*: ``direct`` = proven at execution
        time (intra-function + synchronous call context); ``armed`` = proven at ARMING time
        (the handler runs later). None if the function is degraded/dead there."""
        key = (entry_idx, func_idx)
        fl = self.flows.get(key)
        if fl is None:
            return None
        intra = fl.guards_at(off)
        if intra is None:
            return None
        direct = list(intra)
        armed = []
        for cond, a in self.ctx.get(key, {}).items():
            (armed if a else direct).append(cond)
        return tuple(direct), tuple(armed)
