r"""TIER R rung 3 -- THE INSPECTOR: an effect program's choreography, recovered and time-bound.

R1 made resource id-3 *decodable*, R2 made it *readable*.  Neither could say **when** anything
happens.  This module binds the code to the clock:

  (A) THE STATE-MACHINE RECOVERY.  An effect's entry-point program is not a script that runs once --
      it is a per-tick callback around a ``switch``.  :func:`recover` finds, generically:
        * the ENTRY MODEL -- the program's first branch is a dispatch on ``$a0``: mode 0 = *describe*
          (report the state block's byte size to a caller-supplied pointer), mode 1 = *init* (zero
          the state), anything else = *tick*.  R1's G4 census already saw the frameless half of this
          shape (the 10 non-prologue entries are all ``bne $a0,$zero``); here it is named.
        * the STATE VARIABLE -- the ``lw $idx, K(base)`` feeding the ``sltiu`` / jump-table dispatch,
          with ``base`` resolved to a call argument by a small symbolic tracker (:class:`Sym`).
        * the CASES -- one exclusive body per jump-table target, plus the shared per-tick TAIL every
          case falls into (a case that "stays" branches there too, which is how the tail is found).
        * the TRANSITIONS -- a store of a constant to the state variable, the compare that guards it,
          and whether the same block resets the clock.
  (B) THE FRAME MODEL.  The clock is a caller-owned cell (``*arg3``) the program *reads* at the top
      of the tick and *writes -1 to* at a transition.  Writing -1 is only coherent if the host
      increments before the next read, so a case guarded by ``clock < N`` occupies **N+1 ticks** --
      the whole frame model falls out of that one store.  Chaining the graph from the init state
      turns each case into a frame WINDOW.
  (C) VALIDATION.  :func:`parse_capture` reads the s53 probe rows (MODEL / BONES / PSXCAM) for one
      effect and derives observable beats -- first draw, motion-counter resets, the frame the bone
      matrices stop being valid.  :func:`validate` fits ONE free parameter per program (the frame the
      sequence starts that chunk) and scores the derived boundaries against the observed ones.
  (D) THE REPORT -- :func:`write_report` emits the whole CHOREOGRAPHY document.

PROVENANCE.  Pure analysis code: it reads caller-supplied blobs and emits names, offsets, counts and
frame numbers.  Full listings and capture excerpts belong in the scratch tree, never the repo; the
report's instruction quotes are capped at :data:`QUOTE_BUDGET` and the cap is enforced in code.

CLI::

    py summon_inspect.py 227                       # the recovery, to stdout
    py summon_inspect.py 227 --report OUT.md       # the CHOREOGRAPHY report
    py summon_inspect.py 227 --capture LOG         # + validate against an s53 probe log
    py summon_inspect.py --corpus                  # the recovery census over all 385 images
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_DISASM_DIR = os.path.normpath(os.path.join(_HERE, "..", "thomas-swap", "disasm"))
if _DISASM_DIR not in sys.path:
    sys.path.insert(0, _DISASM_DIR)

import tier_r_disasm as T    # noqa: E402
import tier_r_annot as A     # noqa: E402

SCRATCH_CORPUS = T.SCRATCH_CORPUS
SCRATCH_OUT = r"C:\gd\SCRATCH\summon-format\inspect-r3"

#: The report may quote at most this many stock instructions (the FORMAT round's posture; R1 and R2
#: each spent ten).  Enforced by :func:`write_report`, not merely documented.
QUOTE_BUDGET = 10

#: ``$a0`` values the entry dispatches on.  Names are OURS; the numbers are the program's.
MODE_DESCRIBE, MODE_INIT = 0, 1

#: A clock reset writes one of these.  ``-1`` is the interesting one: it only makes sense if the
#: host increments the cell BEFORE the next read, which is what pins the frame model (see §B).
CLOCK_RESET_VALUES = frozenset((0xFFFFFFFF, 0))

#: How far back from a state-variable store to look for the compare that guards it.
GUARD_WINDOW = 8

#: Ops whose presence in a case body is choreographically load-bearing, and what they mean for the
#: phase label.  The MEMBERSHIP is a fact (the call is in the body); the LABEL is the inference.
ROLE_OPS = {
    25: "draws the creature",
    26: "starts a motion clip",
    100: "scrubs the motion clip to a fixed frame",
    65: "recolours the creature",
    24: "draws effect models",
    155: "recolours effect models",
    149: "reads creature bone positions",
    164: "reads creature bone matrices",
    146: "projects vertices",
}

#: The human-observed beats on record for an effect, from the playtest notes the s53 probe round
#: produced.  These are OBSERVATIONS supplied by the user, never derived by this module -- they are
#: carried here so the report can put the derived phases next to the beats they have to explain.
OBSERVED_BEATS: Dict[int, Tuple[str, ...]] = {
    227: ("float", "charge", "beam", "fire-column"),
}


# ===========================================================================  the symbolic tracker
@dataclass(frozen=True)
class Sym:
    """A tiny symbolic value: enough to name an argument, a dereference and a stack slot.

    ``kind``  ``const`` (``v`` = the value) | ``arg`` (``v`` = the argument index) |
              ``deref`` (``base`` + ``v`` = the byte offset) | ``sp`` (``v`` = delta from entry
              ``$sp``) | ``unk``.
    """
    kind: str
    v: int = 0
    base: Optional["Sym"] = None

    def __str__(self) -> str:
        if self.kind == "const":
            return "%d" % T._s32(self.v)
        if self.kind == "arg":
            return "arg%d" % self.v
        if self.kind == "sp":
            return "sp%+d" % self.v
        if self.kind == "deref":
            return "*(%s%+#x)" % (self.base, self.v) if self.v else "*(%s)" % self.base
        return "?"


UNK = Sym("unk")
_ARG_REGS = (4, 5, 6, 7)         # $a0..$a3
_SP = 29


def _sym_const(v: int) -> Sym:
    return Sym("const", v & 0xFFFFFFFF)


def _incoming_arg(key: int) -> Sym:
    """A load from at-or-above the entry ``$sp`` reads the caller's argument area (MIPS o32).

    ``$a0..$a3`` have reserved shadow slots at ``+0..+12``; arguments 4 and up are passed on the
    stack from ``+16``.  A callee that spills ``$a3`` into its own shadow slot and reloads it later
    is the idiom this exists to follow -- it is how the clock pointer stays nameable across a call.
    """
    if key < 0:
        return UNK
    return Sym("arg", key // 4) if key < 16 else Sym("arg", 4 + (key - 16) // 4)


@dataclass
class Trace:
    """The symbolic register/stack state before every instruction of one function."""
    at: Dict[int, Dict[int, Sym]] = field(default_factory=dict)
    stack_at: Dict[int, Dict[int, Sym]] = field(default_factory=dict)

    def reg(self, off: int, r: int) -> Sym:
        return self.at.get(off, {}).get(r, UNK)


_ALU_KEEP = frozenset(("addiu", "addi", "ori", "andi", "xori", "move", "li", "lui", "addu", "add"))


def _step(ins: T.Instr, regs: Dict[int, Sym], stack: Dict[int, Sym]) -> None:
    n = ins.entry.name
    o = ins.ops

    def put(reg: int, val: Sym) -> None:
        if reg:
            regs[reg] = val

    def get(reg: int) -> Sym:
        return _sym_const(0) if reg == 0 else regs.get(reg, UNK)

    if n == "lui":
        put(o[0], _sym_const(o[1] << 16))
    elif n == "li":
        put(o[0], _sym_const(o[1]))
    elif n in ("addiu", "addi"):
        a = get(o[1])
        if a.kind == "const":
            put(o[0], _sym_const(a.v + o[2]))
        elif a.kind == "sp":
            put(o[0], Sym("sp", a.v + o[2]))
        else:
            put(o[0], UNK)
    elif n in ("ori", "andi", "xori"):
        a = get(o[1])
        if a.kind == "const":
            put(o[0], _sym_const(a.v | o[2] if n == "ori" else
                                 a.v & o[2] if n == "andi" else a.v ^ o[2]))
        else:
            put(o[0], UNK)
    elif n == "move":
        put(o[0], get(o[1]))
    elif n in ("addu", "add"):
        a, b = get(o[1]), get(o[2])
        if a.kind == "const" and b.kind == "const":
            put(o[0], _sym_const(a.v + b.v))
        elif a.kind == "const" and a.v == 0:
            put(o[0], b)
        elif b.kind == "const" and b.v == 0:
            put(o[0], a)
        else:
            put(o[0], UNK)
    elif n in A._LOAD_NAMES:
        base = get(ins.base_reg)
        if base.kind == "sp":
            put(o[0], stack.get(base.v + o[1]) or _incoming_arg(base.v + o[1]))
        elif base.kind in ("arg", "deref"):
            put(o[0], Sym("deref", o[1], base))
        else:
            put(o[0], UNK)
    elif n in A._STORE_NAMES:
        base = get(ins.base_reg)
        if base.kind == "sp":
            stack[base.v + o[1]] = get(o[0])
    else:
        dst = A._written_reg(ins)
        if dst is not None:
            put(dst, UNK)
    regs[0] = _sym_const(0)


def _meet_sym(a: Optional[Dict[int, Sym]], b: Dict[int, Sym]) -> Dict[int, Sym]:
    if a is None:
        return dict(b)
    return {k: v for k, v in a.items() if b.get(k) == v}


TRACE_ROUND_CAP = 80


def trace_function(w: T.ImageWalker, r: T.WalkResult, body: Sequence[int]) -> Trace:
    """Fixpoint symbolic trace over the blocks of ONE function.

    Arguments arrive in ``$a0..$a3`` and ``$sp`` is the entry frame pointer; everything else starts
    unknown.  The merge is an intersection on identical values, so a register keeps a meaning only
    when every path into a block agrees -- under-naming, never inventing.  A call clobbers the
    caller-saved registers, exactly as the interpreter's ABI does.

    **The switch edge is modelled here and nowhere else.**  ``ImageWalker.blocks`` stops at ``jr``,
    so a compiled ``switch``'s case bodies have no dataflow predecessor at all -- every case would
    start from a blank state and the state pointer (a callee-saved register set once in the
    prologue) would be lost exactly where the state machine needs it.  The recovered jump tables
    supply those edges.
    """
    own = set(body)
    raw = w.blocks(r)
    blocks = {b: (bd, list(sc)) for b, (bd, sc) in raw.items()
              if b in own and all(o in own for o in bd)}
    jt_by_site = {jt.site: jt for jt in r.jump_tables}
    for b, (bd, succs) in blocks.items():
        for o in bd:
            jt = jt_by_site.get(o)
            if jt:
                succs.extend(t for t in jt.targets if t in blocks and t not in succs)
    preds: Dict[int, Set[int]] = {b: set() for b in blocks}
    for b, (_bd, succs) in blocks.items():
        for s in succs:
            if s in preds:
                preds[s].add(b)
    entry = min(blocks) if blocks else None
    start = {reg: Sym("arg", i) for i, reg in enumerate(_ARG_REGS)}
    start[_SP] = Sym("sp", 0)
    start[0] = _sym_const(0)
    state: Dict[int, Optional[Tuple[Dict[int, Sym], Dict[int, Sym]]]] = {b: None for b in blocks}
    work: List[int] = []
    for b in blocks:
        if not preds[b] or b == entry:
            state[b] = (dict(start), {})
            work.append(b)
    rounds, cap = 0, TRACE_ROUND_CAP * max(1, len(blocks))
    while rounds < cap:
        while work and rounds < cap:
            rounds += 1
            b = work.pop()
            regs, stack = state[b]
            regs, stack = dict(regs), dict(stack)
            call = False
            for off in blocks[b][0]:
                ins = r.instrs.get(off)
                if ins is None or ins.entry is None:
                    continue
                if ins.entry.name in A.CALL_NAMES:
                    call = True
                    continue
                if ins.entry.is_transfer:
                    continue
                _step(ins, regs, stack)
            if call:
                for reg in T.CALLER_SAVED:
                    regs.pop(reg, None)
            for s in blocks[b][1]:
                if s not in state:
                    continue
                if state[s] is None:
                    state[s] = (dict(regs), dict(stack))
                    work.append(s)
                else:
                    m = (_meet_sym(state[s][0], regs), _meet_sym(state[s][1], stack))
                    if m != state[s]:
                        state[s] = m
                        work.append(s)
        left = [b for b in blocks if state[b] is None]
        if not left:
            break
        state[min(left)] = (dict(start), {})
        work.append(min(left))
    tr = Trace()
    for b in sorted(blocks):
        regs, stack = state[b] if state[b] else (dict(start), {})
        regs, stack = dict(regs), dict(stack)
        for off in blocks[b][0]:
            tr.at[off] = dict(regs)
            tr.stack_at[off] = dict(stack)
            ins = r.instrs.get(off)
            if ins is None or ins.entry is None:
                continue
            if ins.entry.name in A.CALL_NAMES:
                for reg in T.CALLER_SAVED:
                    regs.pop(reg, None)
                continue
            if ins.entry.is_transfer:
                continue
            _step(ins, regs, stack)
    return tr


# ===========================================================================  (A) the recovery
@dataclass
class ModeArm:
    mode: Optional[int]          # the ``$a0`` value that reaches this arm (None = the fall-through)
    target: int
    role: str = "?"              # "describe" | "init" | "tick" | "?"
    detail: str = ""


@dataclass
class Transition:
    off: int                     # the store that writes the state variable
    to_state: Optional[int]
    guard_off: Optional[int]     # the ``slti`` that decides it
    threshold: Optional[int]     # ``clock < N`` stays; ``clock >= N`` transitions
    guard_reg_is_clock: bool
    stay_target: Optional[int]   # where the "not yet" branch goes -- this is how the TAIL is found
    clock_reset: bool = False

    @property
    def ticks(self) -> Optional[int]:
        """How many ticks the owning case occupies: clock runs 0..N inclusive -> N+1."""
        return None if self.threshold is None else self.threshold + 1


@dataclass
class HleCall:
    off: int
    op: int
    name: Optional[str]
    confidence: Optional[str]
    args: Tuple[Optional[int], ...]


@dataclass
class Gate:
    """A clock condition that DOMINATES a call site inside a case -- a sub-phase boundary."""
    threshold: int
    sense: str                   # ">=" (the call needs clock >= N) | "<"
    guard_off: int

    def __str__(self) -> str:
        return "clock %s %d" % (self.sense, self.threshold)


@dataclass
class Case:
    slots: Tuple[int, ...]       # the jump-table indices that reach it == the STATE values
    target: int
    label: str
    body: Tuple[int, ...]        # exclusive instructions
    hle: Tuple[HleCall, ...]
    transitions: Tuple[Transition, ...]
    reachable_states: Tuple[int, ...] = ()
    is_tail: bool = False
    gates: Dict[int, Tuple[Gate, ...]] = field(default_factory=dict)   # {callOff: gates}

    @property
    def terminal(self) -> bool:
        return not self.transitions

    def first_gate(self, op: int) -> Optional[Gate]:
        """The earliest tick a call to ``op`` can run in this case, as a gate.

        Every ``clock >=`` gate dominating a site must hold, so a site's own earliest tick is the
        MAXIMUM of its thresholds; across sites the earliest is the MINIMUM of those.
        """
        best: Optional[Gate] = None
        for h in self.hle:
            if h.op != op:
                continue
            ge = [g for g in self.gates.get(h.off, ()) if g.sense == ">="]
            site = max(ge, key=lambda g: g.threshold) if ge else Gate(0, ">=", h.off)
            if best is None or site.threshold < best.threshold:
                best = site
        return best

    def emits_after(self, off: int, opset: Sequence[int]) -> List[HleCall]:
        """Calls to ``opset`` that run AFTER ``off`` -- i.e. in a transition's own tail."""
        return [h for h in self.hle if h.off > off and h.op in opset]

    def ops(self) -> collections.Counter:
        return collections.Counter(c.op for c in self.hle)

    def roles(self) -> List[str]:
        seen = self.ops()
        return [ROLE_OPS[o] for o in sorted(ROLE_OPS) if o in seen]


@dataclass
class Phase:
    state: int
    case: Case
    start_tick: int
    ticks: Optional[int]
    next_state: Optional[int]

    @property
    def end_tick(self) -> Optional[int]:
        return None if self.ticks is None else self.start_tick + self.ticks - 1


@dataclass
class StateMachine:
    image: str
    entry: int
    dispatch_off: int
    table_off: int
    bound: Optional[int]
    state_base: Sym
    state_offset: int
    state_bias: int
    state_block_bytes: Optional[int]
    init_state: Optional[int]
    clock: Optional[Sym]
    clock_reset_sites: Tuple[int, ...]
    arms: Tuple[ModeArm, ...]
    cases: Tuple[Case, ...]
    tail: Optional[Case]
    phases: Tuple[Phase, ...]
    dead_states: Tuple[int, ...]
    bad_targets: Tuple[int, ...]
    notes: Tuple[str, ...] = ()
    #: the walk this machine came out of -- kept only so the report can quote a line verbatim
    walk: Optional[T.WalkResult] = field(default=None, repr=False)

    @property
    def n_slots(self) -> int:
        return sum(len(c.slots) for c in self.cases)

    @property
    def total_ticks(self) -> Optional[int]:
        last = self.phases[-1] if self.phases else None
        return None if last is None else last.start_tick

    def case_of_state(self, state: int) -> Optional[Case]:
        for c in self.cases:
            if state in c.slots:
                return c
        return None


#: Recovery outcomes.  ``frame-dispatch`` is NOT a failure: the program switches directly on the
#: host's frame counter instead of on a state it stores, so its timeline is even more direct -- slot
#: k IS frame k.  It is counted separately precisely so it cannot be mistaken for either success at
#: recovering a state machine or a defeat.
VERDICTS = ("clean", "frame-dispatch", "trivial", "defeated")


@dataclass
class Recovery:
    image: str
    verdict: str
    reason: str = ""
    machine: Optional[StateMachine] = None


def _runs(slots: Sequence[int]) -> List[List[int]]:
    """Split a sorted slot list into runs of consecutive indices."""
    out: List[List[int]] = []
    for s in sorted(slots):
        if out and s == out[-1][-1] + 1:
            out[-1].append(s)
        else:
            out.append([s])
    return out


def _flood(r: T.WalkResult, start: int, stops: Set[int],
           jt_by_site: Dict[int, T.JumpTable]) -> Set[int]:
    """Intra-procedural flood from ``start``, halting at any offset in ``stops``."""
    seen: Set[int] = set()
    stack = [start]
    while stack:
        off = stack.pop()
        if off in seen or off not in r.instrs:
            continue
        if off != start and off in stops:
            continue
        seen.add(off)
        ins = r.instrs[off]
        if ins.entry is None:
            continue
        if not ins.entry.is_transfer:
            stack.append(off + 4)
            continue
        if off + 4 in r.instrs:
            seen.add(off + 4)
        n = ins.entry.name
        if n == "jr":
            jt = jt_by_site.get(off)
            if jt:
                stack.extend(jt.targets)
            continue
        if n in ("jal", "jalr", "bltzal", "bgezal"):
            stack.append(off + 8)
            continue
        if n in ("j", "b"):
            stack.append(ins.ops[0])
            continue
        tgt = ins.op(T.Ex.BTARGET)
        if tgt is not None:
            stack.append(tgt)
        stack.append(off + 8)
    return seen


def _sub_cfg(r: T.WalkResult, w: T.ImageWalker, body: Set[int],
             jt_by_site: Dict[int, T.JumpTable]) -> Tuple[Dict[int, List[int]], Dict[int, int]]:
    """({blockStart: successors}, {instrOff: blockStart}) restricted to one case body."""
    blocks = {b: bd for b, (bd, _sc) in w.blocks(r).items() if b in body}
    where: Dict[int, int] = {}
    for b, bd in blocks.items():
        for o in bd:
            if o in body:
                where[o] = b
    succ: Dict[int, List[int]] = {}
    for b, bd in blocks.items():
        xfer = None
        for o in bd:
            ins = r.instrs.get(o)
            if ins is not None and ins.entry is not None and ins.entry.is_transfer:
                xfer = ins
                break
        outs: List[int] = []
        if xfer is None:
            nxt = bd[-1] + 4
            if nxt in blocks:
                outs.append(nxt)
        else:
            n = xfer.entry.name
            if n == "jr":
                jt = jt_by_site.get(xfer.off)
                outs.extend(t for t in (jt.targets if jt else ()) if t in blocks)
            elif n in ("j", "b"):
                outs.append(xfer.ops[0])
            elif n in ("jal", "jalr", "bltzal", "bgezal"):
                outs.append(xfer.off + 8)
            else:
                t = xfer.op(T.Ex.BTARGET)
                if t is not None:
                    outs.append(t)
                outs.append(xfer.off + 8)
        succ[b] = [o for o in outs if o in blocks]
    return succ, where


def _dominators(succ: Dict[int, List[int]], entry: int) -> Dict[int, Set[int]]:
    """Classic iterative dominator sets over a small block graph."""
    nodes = set(succ)
    dom = {n: set(nodes) for n in nodes}
    dom[entry] = {entry}
    preds: Dict[int, Set[int]] = {n: set() for n in nodes}
    for b, ss in succ.items():
        for s in ss:
            preds[s].add(b)
    changed = True
    rounds = 0
    while changed and rounds < 200:
        changed = False
        rounds += 1
        for n in sorted(nodes):
            if n == entry:
                continue
            ps = [dom[p] for p in preds[n] if p in dom]
            new = ({n} | set.intersection(*ps)) if ps else {n}
            if new != dom[n]:
                dom[n] = new
                changed = True
    return dom


def _reaches(succ: Dict[int, List[int]], start: int, target: int, avoid: int) -> bool:
    seen, stack = set(), [start]
    while stack:
        n = stack.pop()
        if n in seen or n == avoid:
            continue
        seen.add(n)
        if n == target:
            return True
        stack.extend(succ.get(n, ()))
    return False


def _gates_for(r: T.WalkResult, w: T.ImageWalker, body: Set[int], entry: int,
               sites: Sequence[int], tr: Trace, clock: Optional[Sym],
               jt_by_site: Dict[int, T.JumpTable]) -> Dict[int, Tuple[Gate, ...]]:
    """For each call site, the clock conditions that DOMINATE it inside its case.

    A guard block dominating the site decides the site only if exactly one of its two successors can
    still reach the site; that is what turns "there is a compare in this case" into "this call needs
    ``clock >= 24``".  Anything ambiguous is dropped rather than guessed.
    """
    if clock is None or not sites:
        return {}
    succ, where = _sub_cfg(r, w, body, jt_by_site)
    if entry not in succ:
        return {}
    dom = _dominators(succ, entry)
    out: Dict[int, Tuple[Gate, ...]] = {}
    for site in sites:
        blk = where.get(site)
        if blk is None or blk not in dom:
            continue
        gates: List[Gate] = []
        for d in sorted(dom[blk] - {blk}):
            bd = [o for o in sorted(where) if where[o] == d]
            cmp_ins = brn = None
            for o in bd:
                ins = r.instrs.get(o)
                if ins is None or ins.entry is None:
                    continue
                if ins.entry.name in ("slti", "sltiu") and tr.reg(o, ins.ops[1]) == clock:
                    cmp_ins = ins
                elif ins.entry.is_transfer and ins.entry.name in ("beq", "bne") and cmp_ins is not None \
                        and ins.ops[0] == cmp_ins.ops[0]:
                    brn = ins
            if cmp_ins is None or brn is None:
                continue
            taken = brn.op(T.Ex.BTARGET)
            fall = brn.off + 8
            if taken not in succ or fall not in succ:
                continue
            via_taken = _reaches(succ, taken, blk, fall)
            via_fall = _reaches(succ, fall, blk, taken)
            if via_taken == via_fall:
                continue
            # `slti $x,$clock,N` sets $x=1 when clock < N.  `bne $x,$zero` takes that arm.
            lt_arm = taken if brn.entry.name == "bne" else fall
            needs_lt = (lt_arm == taken) == via_taken
            gates.append(Gate(cmp_ins.ops[2], "<" if needs_lt else ">=", cmp_ins.off))
        if gates:
            out[site] = tuple(gates)
    return out


def _dispatch_index(r: T.WalkResult, site: int) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """``(indexReg, sltiuBound, lwOffset)`` for the ``switch`` dispatched by the ``jr`` at ``site``."""
    idx_reg = bound = None
    for k in range(1, 25):
        ins = r.instrs.get(site - 4 * k)
        if ins is None or ins.entry is None:
            break
        if ins.entry.name == "sltiu":
            idx_reg, bound = ins.ops[1], ins.ops[2]
            break
    return idx_reg, bound, None


def _state_var(r: T.WalkResult, site: int, idx_reg: int,
               depth: int = 3) -> Optional[Tuple[int, int, int, int]]:
    """The ``lw $idx, K(base)`` that feeds the dispatch -> ``(loadOff, baseReg, K, bias)``.

    A dispatch is often biased -- ``lw $s4,0($s3) ; addiu $v1,$s4,-6 ; sltiu ; ...`` is a switch on
    ``counter - 6``, i.e. a table whose slot 0 is frame 6.  The bias is followed and returned rather
    than treated as an unrecoverable computed dispatch.
    """
    reg, bias = idx_reg, 0
    for _ in range(depth):
        found = None
        for k in range(1, 40):
            ins = r.instrs.get(site - 4 * k)
            if ins is None or ins.entry is None:
                continue
            if ins.entry.name in A._LOAD_NAMES and ins.ops[0] == reg:
                return ins.off, ins.base_reg, ins.ops[1], bias
            if ins.entry.name in ("addiu", "addi", "move") and ins.ops[0] == reg:
                found = ins
                break
        if found is None:
            return None
        reg = found.ops[1]
        bias += found.ops[2] if found.entry.name != "move" else 0
    return None


def _mode_arms(w: T.ImageWalker, r: T.WalkResult, entry: int, tr: Trace,
               limit: int = 8) -> List[ModeArm]:
    """The ``$a0`` compare chain at a program entry: ``bne $a0,$zero`` / ``bne $a0,1`` / ...

    Walked block by block: while the block's terminating branch compares ``$a0`` against a constant,
    the arm it selects is recorded and the walk continues down the other side.  The first block that
    ends on anything else IS the last arm -- the mode the program falls through to.
    """
    arms: List[ModeArm] = []
    blocks = w.blocks(r)
    cur = entry
    for _ in range(limit):
        blk = blocks.get(cur)
        if blk is None:
            break
        xfer = None
        for o in blk[0]:
            ins = r.instrs.get(o)
            if ins is not None and ins.entry is not None and ins.entry.is_transfer:
                xfer = ins
                break
        if xfer is None or xfer.entry.name not in ("bne", "beq"):
            break
        a, b = tr.reg(xfer.off, xfer.ops[0]), tr.reg(xfer.off, xfer.ops[1])
        mode = None
        if a.kind == "arg" and a.v == 0 and b.kind == "const":
            mode = T._s32(b.v)
        elif b.kind == "arg" and b.v == 0 and a.kind == "const":
            mode = T._s32(a.v)
        if mode is None:
            break
        tgt = xfer.op(T.Ex.BTARGET)
        if xfer.entry.name == "bne":
            arms.append(ModeArm(mode, xfer.off + 8))          # equal -> the fall-through
            cur = tgt
        else:
            arms.append(ModeArm(mode, tgt))
            cur = xfer.off + 8
    arms.append(ModeArm(None, cur))
    return arms


def _classify_arms(r: T.WalkResult, arms: List[ModeArm], dispatch_off: int,
                   state_arg: int, state_off: int, tr: Trace,
                   jt_by_site: Dict[int, T.JumpTable]
                   ) -> Tuple[List[ModeArm], Optional[int], Optional[int]]:
    """Name each ``$a0`` arm, and read the state block's size and the initial state off them.

    Nothing here is assumed from the mode NUMBER: an arm is *tick* because the dispatch is inside
    it, *describe* because it writes constants through a caller pointer that is **not** the state
    block and calls nothing, and *init* by elimination.  An init arm that never writes the state
    variable is not a failure -- the host hands out a zero-filled block of the size the describe arm
    reported, so the initial state is 0.
    """
    block_bytes = None
    init_state: Optional[int] = None
    stops = {a.target for a in arms}
    call_offs = {c.off for c in r.calls}
    unclaimed: List[ModeArm] = []
    for arm in arms:
        body = _flood(r, arm.target, stops - {arm.target}, jt_by_site)
        if dispatch_off in body:
            arm.role = "tick"
            arm.detail = "runs the state machine"
            continue
        seeded: Optional[int] = None
        out: Dict[Tuple[int, int], int] = {}
        for o in sorted(body):
            ins = r.instrs.get(o)
            if ins is None or ins.entry is None or ins.entry.name not in A._STORE_NAMES:
                continue
            base = tr.reg(o, ins.base_reg)
            val = tr.reg(o, ins.ops[0])
            if base.kind != "arg" or val.kind != "const":
                continue
            if base.v == state_arg and ins.ops[1] == state_off:
                seeded = T._s32(val.v)
            elif base.v != state_arg:
                out[(base.v, ins.ops[1])] = T._s32(val.v)
        if out and not (body & call_offs):
            arm.role = "describe"
            arm.detail = ("writes %d constant%s through a caller pointer, calls nothing"
                          % (len(out), "" if len(out) == 1 else "s"))
            at_zero = [v for (_a, off), v in out.items() if off == 0]
            block_bytes = at_zero[0] if at_zero else None
        else:
            arm.role = "init"
            arm.detail = ("seeds the state variable to %d" % seeded) if seeded is not None else \
                "sets the state block up; leaves the state variable at the host's zero fill"
            init_state = seeded if seeded is not None else 0
            unclaimed.append(arm)
    if len(unclaimed) > 1:                     # more arms than the two-mode idiom explains
        for arm in unclaimed[1:]:
            arm.role = "?"
    return arms, block_bytes, init_state


def _guard_for(r: T.WalkResult, store_off: int, tr: Trace,
               clock: Optional[Sym]) -> Tuple[Optional[int], Optional[int], bool, Optional[int]]:
    """The ``slti $x, clock, N`` + ``bne $x,$zero,STAY`` pair guarding a state-variable store."""
    for k in range(1, GUARD_WINDOW + 1):
        o = store_off - 4 * k
        ins = r.instrs.get(o)
        if ins is None or ins.entry is None:
            continue
        if ins.entry.name in ("slti", "sltiu"):
            reg_sym = tr.reg(o, ins.ops[1])
            is_clock = clock is not None and reg_sym == clock
            stay = None
            for j in range(1, 4):
                b = r.instrs.get(o + 4 * j)
                if b is not None and b.entry is not None and b.entry.name in ("bne", "beq"):
                    stay = b.op(T.Ex.BTARGET)
                    break
            return o, ins.ops[2], is_clock, stay
    return None, None, False, None


def _clock_candidates(r: T.WalkResult, body: Set[int], tr: Trace,
                      state_arg: int, state_off: int) -> Tuple[Optional[Sym], List[int]]:
    """The clock is the cell a transition RESETS.  Find the reset stores, then name the cell.

    A store of ``-1`` (or ``0``) through a pointer argument, sitting within a few instructions of a
    state-variable store, is the signature.  The same cell read at the top of the tick is the value
    the guards compare -- which the caller cross-checks.
    """
    resets: List[int] = []
    cells: collections.Counter = collections.Counter()
    state_stores = [o for o in sorted(body) if _is_state_store(r, o, tr, state_arg, state_off)]
    for so in state_stores:
        for k in range(0, 8):
            o = so + 4 * k
            ins = r.instrs.get(o)
            if ins is None or ins.entry is None or ins.entry.name not in A._STORE_NAMES:
                continue
            base = tr.reg(o, ins.base_reg)
            val = tr.reg(o, ins.ops[0])
            if base.kind in ("arg", "deref") and val.kind == "const" \
                    and val.v in CLOCK_RESET_VALUES                     and not (base.kind == "arg" and base.v == state_arg):
                cell = Sym("deref", ins.ops[1], base)
                cells[cell] += 1
                resets.append(o)
    if not cells:
        return None, []
    return cells.most_common(1)[0][0], sorted(set(resets))


def _is_state_store(r: T.WalkResult, off: int, tr: Trace, state_arg: int, state_off: int) -> bool:
    ins = r.instrs.get(off)
    if ins is None or ins.entry is None or ins.entry.name not in A._STORE_NAMES:
        return False
    if ins.ops[1] != state_off:
        return False
    base = tr.reg(off, ins.base_reg)
    return base.kind == "arg" and base.v == state_arg


def recover(img: T.Id3Image, ops: Optional[Dict[int, dict]] = None,
            w: Optional[T.ImageWalker] = None,
            r: Optional[T.WalkResult] = None) -> Recovery:
    """Recover the state machine of ``img``'s first switch-driven program entry."""
    ops = ops if ops is not None else {}
    if w is None or r is None:
        w, r = A.walk(img)
    seg = A.segment_functions(img, w, r, ops)
    jt_by_site = {jt.site: jt for jt in r.jump_tables}
    entries = [f for f in seg.functions if f.entry]
    if not entries:
        return Recovery(img.label, "defeated", "no program entry function")
    owner = None
    for f in sorted(entries, key=lambda x: -x.cases):
        if f.switches:
            owner = f
            break
    if owner is None:
        return Recovery(img.label, "trivial", "no switch in any program entry (linear program)")
    body = set(owner.offsets)
    mine = sorted([jt for jt in r.jump_tables if jt.site in body],
                  key=lambda x: -len(x.targets))
    tr = trace_function(w, r, owner.offsets)
    # A program may compile more than one `switch`; the STATE machine's is the one whose index
    # comes out of the caller's own state block.  Try them all, biggest first, and keep the reason
    # the best candidate failed rather than the reason the last one did.
    jt = None
    fail = "switch dispatch has no sltiu bound"
    for cand in mine:
        idx_reg, bound, _ = _dispatch_index(r, cand.site)
        if idx_reg is None:
            continue
        sv = _state_var(r, cand.site, idx_reg)
        if sv is None:
            fail = ("switch index is not loaded from memory "
                    "(computed dispatch, not a state variable)")
            continue
        load_off, base_reg, state_off, bias = sv
        base_sym = tr.reg(load_off, base_reg)
        if base_sym.kind != "arg":
            fail = ("state variable is a stack local, not a field of the caller's state "
                    "block -- an inner switch, not the phase spine")
            continue
        jt = cand
        break
    if jt is None:
        return Recovery(img.label, "defeated", fail)

    clock, reset_sites = _clock_candidates(r, body, tr, base_sym.v, state_off)
    writes_state = [o for o in sorted(body) if _is_state_store(r, o, tr, base_sym.v, state_off)]

    # ---- case bodies: flood, find the shared per-tick TAIL, re-flood exclusively
    targets = list(dict.fromkeys(jt.targets))
    first = {t: _flood(r, t, set(targets) - {t}, jt_by_site) for t in targets}
    counts: collections.Counter = collections.Counter()
    for t, s in first.items():
        counts.update(s)
    shared = {o for o, n in counts.items() if n > 1}
    tail_starts = {o for o in shared if (o - 4) not in shared}
    stops = set(targets) | tail_starts
    bodies = {t: _flood(r, t, stops - {t}, jt_by_site) for t in targets}

    calls = {c.off: c for c in r.calls}

    def hle_of(offs: Iterable[int]) -> Tuple[HleCall, ...]:
        out = []
        for o in sorted(offs):
            c = calls.get(o)
            if c is None or c.kind != "hle" or c.hle_op is None:
                continue
            row = ops.get(c.hle_op, {})
            out.append(HleCall(o, c.hle_op, row.get("name"), row.get("confidence"), c.args))
        return tuple(out)

    slots_of: Dict[int, List[int]] = collections.defaultdict(list)
    for i, t in enumerate(jt.targets):
        slots_of[t].append(i)

    cases: List[Case] = []
    for t in targets:
        offs = sorted(bodies[t])
        trans: List[Transition] = []
        for o in offs:
            if not _is_state_store(r, o, tr, base_sym.v, state_off):
                continue
            val = tr.reg(o, r.instrs[o].ops[0])
            g_off, thr, is_clock, stay = _guard_for(r, o, tr, clock)
            reset = any(abs(x - o) <= 4 * 8 for x in reset_sites)
            trans.append(Transition(o, T._s32(val.v) if val.kind == "const" else None,
                                    g_off, thr, is_clock, stay, reset))
        hl = hle_of(offs)
        gates = _gates_for(r, w, set(offs), t, [h.off for h in hl], tr, clock, jt_by_site)
        cases.append(Case(tuple(slots_of[t]), t, r.labels.get(t, "case_%04x" % t),
                          tuple(offs), hl, tuple(trans),
                          tuple(sorted({x.to_state for x in trans if x.to_state is not None})),
                          gates=gates))

    # A case every transition's "not yet" branch lands on IS the per-tick tail, even when the
    # dispatch table also points at it (ef227:c0 does exactly that with five slots).
    stays = collections.Counter(x.stay_target for c in cases for x in c.transitions
                                if x.stay_target is not None)
    stay_tail = stays.most_common(1)[0][0] if stays else None
    for c in cases:
        if stay_tail is not None and c.target == stay_tail:
            c.is_tail = True

    tail_case = None
    if tail_starts:
        tail_offs = sorted(shared)
        tail_case = Case((), min(tail_starts), "TAIL", tuple(tail_offs), hle_of(tail_offs), (),
                         is_tail=True)

    # ---- the arms, the state block's size, and the initial state
    arms, block_bytes, init_state = _classify_arms(r, _mode_arms(w, r, owner.start, tr), jt.site,
                                                   base_sym.v, state_off, tr, jt_by_site)

    # ---- the phase chain.  With no store to the dispatch index anywhere in the program, the index
    # is not a state the program keeps -- it is the caller's own frame counter, and slot k IS tick k.
    phases: List[Phase] = []
    frame_dispatch = not writes_state
    if frame_dispatch:
        for c in cases:
            for run in _runs(c.slots):
                phases.append(Phase(run[0], c, run[0], len(run), None))
        phases.sort(key=lambda p: p.start_tick)
    seen_states: Set[int] = set()
    state = None if frame_dispatch else init_state
    tick = 0
    while state is not None and state not in seen_states:
        c = None
        for cc in cases:
            if state in cc.slots:
                c = cc
                break
        if c is None:
            break
        seen_states.add(state)
        prim = next((x for x in c.transitions if x.guard_reg_is_clock and x.to_state is not None),
                    c.transitions[0] if c.transitions else None)
        ticks = prim.ticks if prim else None
        phases.append(Phase(state, c, tick, ticks, prim.to_state if prim else None))
        if ticks is None or prim is None or prim.to_state is None:
            break
        tick += ticks
        state = prim.to_state

    live = {p.state for p in phases} if not frame_dispatch else \
        {s for c in cases for s in c.slots}
    dead = tuple(sorted(s for c in cases for s in c.slots if s not in live))
    bad = tuple(sorted({x.to_state for c in cases for x in c.transitions
                        if x.to_state is not None and all(x.to_state not in cc.slots
                                                          for cc in cases)}))
    notes: List[str] = []
    if tail_case is not None:
        notes.append("%d instructions are shared by every case: the per-tick TAIL at %#x"
                     % (len(tail_case.body), tail_case.target))
    if dead:
        notes.append("states %s are table slots no transition ever assigns"
                     % ", ".join(str(s) for s in dead))
    sm = StateMachine(image=img.label, entry=owner.start, dispatch_off=jt.site, table_off=jt.off,
                      bound=bound, state_base=base_sym, state_offset=state_off, state_bias=bias,
                      state_block_bytes=block_bytes, init_state=init_state, clock=clock,
                      clock_reset_sites=tuple(reset_sites), arms=tuple(arms), cases=tuple(cases),
                      tail=tail_case, phases=tuple(phases), dead_states=dead, bad_targets=bad,
                      notes=tuple(notes), walk=r)
    if frame_dispatch:
        return Recovery(img.label, "frame-dispatch",
                        "nothing in the program writes the dispatch index -- it switches on the "
                        "caller's frame counter (%s), so slot k IS frame k" % base_sym, sm)
    if clock is None:
        return Recovery(img.label, "defeated", "no clock cell found (no transition resets one)", sm)
    if not sm.phases:
        return Recovery(img.label, "defeated",
                        "the initial state %s has no case in the dispatch table" % init_state, sm)
    if len(sm.phases) < 2:
        return Recovery(img.label, "defeated",
                        "the chain stops at the first state (its transition is unguarded or "
                        "self-directed) -- no timeline comes out", sm)
    return Recovery(img.label, "clean", "", sm)


def recover_container(blob: bytes, source: str, ops: Optional[Dict[int, dict]] = None
                      ) -> List[Recovery]:
    return [recover(img, ops) for img in T.id3_images(blob, source)]


# ===========================================================================  (C) the capture
@dataclass
class CaptureFrame:
    frame: int
    active: Optional[int] = None
    motion: Optional[int] = None       # aux0 == the summon slot's motion frame counter
    drawn: bool = False                # bones32 != 0
    anchor: Tuple[int, int, int] = (0, 0, 0)
    eff_slots: int = 0
    bones_ok: Optional[bool] = None
    proj_h: Optional[int] = None


#: A bone AABB coordinate larger than this is not a pose, it is freed memory read as integers.
BONES_SANE = 1_000_000


@dataclass
class Capture:
    source: str
    effect: int
    frames: Dict[int, CaptureFrame]

    @property
    def span(self) -> Tuple[int, int]:
        ks = sorted(self.frames)
        return (ks[0], ks[-1]) if ks else (0, 0)

    def first(self, pred) -> Optional[int]:
        for f in sorted(self.frames):
            if pred(self.frames[f]):
                return f
        return None

    def motion_resets(self) -> List[Tuple[int, int]]:
        """Frames where the motion counter restarts -- a ``SetMotion``/``SetMotFrame`` fingerprint.

        A wrap at the end of a looping clip also restarts it, so this is a *candidate* list; the
        validator scores derived boundaries against it and reports the ones that do not land.
        """
        out: List[Tuple[int, int]] = []
        prev = None
        for f in sorted(self.frames):
            m = self.frames[f].motion
            if m is None:
                continue
            if prev is not None and m < prev:
                out.append((f, m))
            prev = m
        return out

    def last_bones_ok(self) -> Optional[int]:
        best = None
        for f in sorted(self.frames):
            if self.frames[f].bones_ok:
                best = f
        return best

    def first_bones_bad(self) -> Optional[int]:
        started = False
        for f in sorted(self.frames):
            b = self.frames[f].bones_ok
            if b:
                started = True
            elif b is False and started:
                return f
        return None

    def proj_changes(self) -> List[Tuple[int, int]]:
        out, prev = [], None
        for f in sorted(self.frames):
            h = self.frames[f].proj_h
            if h is None:
                continue
            if prev is not None and h != prev:
                out.append((f, h))
            prev = h
        return out

    def eff_changes(self) -> List[Tuple[int, int]]:
        out, prev = [], None
        for f in sorted(self.frames):
            n = self.frames[f].eff_slots
            if prev is not None and n != prev:
                out.append((f, n))
            prev = n
        return out


def parse_capture(path: str, effect: int) -> Capture:
    """Read one s53 probe log's MODEL / BONES / PSXCAM rows for ``effect``.

    The probe emits each row once per draw pass, so identical rows repeat within a frame; they are
    collapsed.  Only the fields the validator uses are kept -- this never copies the log.
    """
    frames: Dict[int, CaptureFrame] = {}
    pre = "%d," % effect
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line or line[0] == "#":
                continue
            head, _, rest = line.partition(",")
            if head not in ("MODEL", "BONES", "PSXCAM") or not rest.startswith(pre):
                continue
            f = rest.split(",")
            try:
                fr = int(f[1])
            except ValueError:
                continue
            cf = frames.get(fr)
            if cf is None:
                cf = frames[fr] = CaptureFrame(fr)
            if head == "MODEL":
                kind = f[2]
                if kind == "S":
                    cf.active = int(f[4])
                    cf.motion = int(f[7])
                    cf.drawn = f[-1].strip() not in ("0", "00000000")
                    cf.anchor = (int(f[10]), int(f[11]), int(f[12]))
                else:
                    cf.eff_slots += 1
            elif head == "BONES":
                vals = [int(x) for x in f[3:12]]
                cf.bones_ok = all(abs(v) < BONES_SANE for v in vals)
            elif head == "PSXCAM":
                cf.proj_h = int(f[16])
    # the eff-slot count is inflated by the per-pass repetition; normalise by the S multiplicity
    mult = collections.Counter()
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("MODEL," + pre):
                g = line.split(",")
                if g[3] == "S":
                    mult[int(g[2])] += 1
    m = collections.Counter(mult.values()).most_common(1)
    k = m[0][0] if m else 1
    if k > 1:
        for cf in frames.values():
            cf.eff_slots //= k
    return Capture(os.path.basename(path), effect, frames)


@dataclass
class Check:
    what: str
    predicted: Optional[int]
    observed: Optional[int]
    verdict: str
    note: str = ""


#: ``Hi_SetSummonMotion`` restarts the clip; ``Hi_SetSummonMotFrame`` scrubs it to a fixed frame.
#: Either one shows up in the capture as the motion counter RESTARTING, which is the only per-frame
#: observable a transition can produce.
MOTION_OPS = (26, 100)
DRAW_SUMMON_OP = 25


@dataclass
class Boundary:
    """One derived phase boundary and what -- if anything -- it should be visible as."""
    state: int
    tick: int
    frame: Optional[int] = None
    observable: bool = False
    expect_motion: Optional[int] = None    # the motion frame the transition's tail scrubs to
    detail: str = ""


def boundaries(sm: StateMachine) -> List[Boundary]:
    out: List[Boundary] = []
    for prev, p in zip(sm.phases, sm.phases[1:]):
        trans = next((x for x in prev.case.transitions if x.guard_reg_is_clock), None)
        emits = prev.case.emits_after(trans.off, MOTION_OPS) if trans else []
        setf = [h for h in emits if h.op == 100 and h.args[1] is not None]
        b = Boundary(p.state, p.start_tick, observable=bool(emits),
                     expect_motion=(setf[-1].args[1] if setf else (0 if emits else None)))
        b.detail = ("the transition's own tail calls %s"
                    % ", ".join("op %d" % h.op for h in emits)) if emits else \
                   "the transition emits no motion call -- nothing to see in the capture"
        out.append(b)
    return out


@dataclass
class Fit:
    machine: StateMachine
    origin: Optional[int]
    hits: int
    total: int                 # boundaries that PREDICT an observable
    anchors: Tuple[int, ...] = ()


def fit_origin(sm: StateMachine, cap: Capture) -> Fit:
    """Fit the ONE free parameter: the frame the sequence starts this chunk.

    The phase DURATIONS are derived from the code and are not fitted.  Three kinds of constraint
    score a candidate origin, and all three are things the CODE predicts:

    * a boundary whose transition tail issues a motion call must land on an observed motion-counter
      restart **whose value equals the constant that transition writes** -- a restart at the right
      frame with the wrong value is a coincidence, not a match;
    * the last phase that draws the creature must end where the bone matrices stop being a pose;
    * a boundary that predicts no observable scores nothing either way.

    Scoring only the boundaries that predict something is what stops a single coincidence from
    carrying the alignment on a program with one observable transition.
    """
    bs = [b for b in boundaries(sm) if b.observable]
    resets = dict(cap.motion_resets())
    draw = [p for p in sm.phases if any(h.op == DRAW_SUMMON_OP for h in p.case.hle)]
    last_tick = draw[-1].end_tick if draw else None
    last_obs = cap.last_bones_ok()
    if not bs and last_tick is None:
        return Fit(sm, None, 0, 0)

    def score(origin: int) -> Tuple[int, int]:
        hit = res = 0
        for b in bs:
            f = origin + b.tick
            if f in resets and (b.expect_motion is None or resets[f] == b.expect_motion):
                hit += 1
            else:
                res += min((abs(f - y) for y in resets), default=999)
        if last_tick is not None and last_obs is not None:
            d = abs(origin + last_tick - last_obs)
            if d <= 3:
                hit += 1
            res += d
        return hit, -res

    cands: Set[int] = set()
    for f in resets:
        for b in bs:
            cands.add(f - b.tick)
    if last_tick is not None and last_obs is not None:
        cands.add(last_obs - last_tick)
    if not cands:
        return Fit(sm, None, 0, len(bs))
    origin = max(cands, key=lambda o: score(o) + (-abs(o),))
    hits = sum(1 for b in bs
               if (origin + b.tick) in resets
               and (b.expect_motion is None or resets[origin + b.tick] == b.expect_motion))
    return Fit(sm, origin, hits, len(bs), tuple(b.tick for b in bs))


def validate_all(sms: Sequence[StateMachine], cap: Capture,
                 fits: Sequence[Fit]) -> List[List[Check]]:
    """Validate every program of one container, so cross-program facts are stated once.

    The creature is ONE slot shared by both chunks (R1 finding 1 -- the summon slot survives across
    containers), so "first drawn" is a property of the container, not of a program: only the program
    that draws it first is scored on it.
    """
    firsts: List[Optional[int]] = []
    for sm, fit in zip(sms, fits):
        draw = [p for p in sm.phases if any(h.op == DRAW_SUMMON_OP for h in p.case.hle)]
        if not draw or fit.origin is None:
            firsts.append(None)
            continue
        g = draw[0].case.first_gate(DRAW_SUMMON_OP)
        firsts.append(fit.origin + draw[0].start_tick + (g.threshold if g else 0))
    live = [f for f in firsts if f is not None]
    earliest = min(live) if live else None
    return [validate(sm, cap, fit, owns_first_draw=(firsts[i] is not None
                                                    and firsts[i] == earliest))
            for i, (sm, fit) in enumerate(zip(sms, fits))]


def validate(sm: StateMachine, cap: Capture, fit: Fit,
             owns_first_draw: bool = True) -> List[Check]:
    """Score the recovered machine against one capture.  Disagreements are findings, not noise."""
    out: List[Check] = []
    if fit.origin is None:
        out.append(Check("origin fit", None, None, "N/A",
                         "no boundary predicts an observable in this capture"))
        return out
    resets = dict(cap.motion_resets())
    for b in boundaries(sm):
        b.frame = fit.origin + b.tick
        if not b.observable:
            out.append(Check("enters state %d" % b.state, b.frame, None, "NOT OBSERVABLE", b.detail))
            continue
        got = b.frame in resets and (b.expect_motion is None
                                     or resets[b.frame] == b.expect_motion)
        out.append(Check("enters state %d" % b.state, b.frame, b.frame if b.frame in resets else
                         min(resets, key=lambda f: abs(f - b.frame)) if resets else None,
                         "AGREE" if got else "DISAGREE", b.detail))
        if b.frame in resets and b.expect_motion is not None:
            out.append(Check("  ... motion counter reads %d" % b.expect_motion, b.expect_motion,
                             resets[b.frame],
                             "AGREE" if resets[b.frame] == b.expect_motion else "DISAGREE",
                             "the constant the transition's own SetMotFrame writes"))
    # --- the creature's draw window: a different observable, so an independent test of the fit
    draw = [p for p in sm.phases if any(h.op == DRAW_SUMMON_OP for h in p.case.hle)]
    if draw:
        first = draw[0]
        gate = first.case.first_gate(DRAW_SUMMON_OP)
        pred_first = fit.origin + first.start_tick + (gate.threshold if gate else 0)
        obs_first = cap.first(lambda c: c.drawn)
        out.append(Check("creature first drawn", pred_first,
                         obs_first if owns_first_draw else None,
                         _near(pred_first, obs_first, 2) if owns_first_draw else "N/A",
                         (("state %d's draw is gated on %s" % (first.state, gate)) if gate
                          else "state %d, ungated" % first.state) if owns_first_draw else
                         "another program in this container draws the creature first"))
        last = draw[-1]
        pred_last = None if last.end_tick is None else fit.origin + last.end_tick
        nxt = sm.phases.index(last) + 1
        out.append(Check("creature last drawn", pred_last, cap.last_bones_ok(),
                         _near(pred_last, cap.last_bones_ok(), 3),
                         "last frame the bone AABB is a pose and not freed memory"
                         if pred_last is not None else
                         "TERMINAL phase -- the program never stops itself; the sequence does"))
        out.append(Check("bone matrices freed", None if pred_last is None else pred_last + 1,
                         cap.first_bones_bad(),
                         _near(None if pred_last is None else pred_last + 1,
                               cap.first_bones_bad(), 3),
                         "state %d is the first phase with no draw call" % sm.phases[nxt].state
                         if nxt < len(sm.phases) else "no phase after the last drawing one"))
    return out


def _near(pred: Optional[int], obs: Optional[int], tol: int) -> str:
    if pred is None or obs is None:
        return "N/A"
    d = abs(pred - obs)
    return "AGREE" if d == 0 else ("AGREE (%+d)" % (obs - pred) if d <= tol else
                                   "DISAGREE (%+d)" % (obs - pred))


# ===========================================================================  the corpus census
@dataclass
class CensusRow:
    image: str
    verdict: str
    reason: str
    cases: int = 0
    phases: int = 0
    ticks: Optional[int] = None


def corpus_census(root: str = SCRATCH_CORPUS, ops: Optional[Dict[int, dict]] = None,
                  limit: Optional[int] = None, progress=None) -> List[CensusRow]:
    rows: List[CensusRow] = []
    for n, path in enumerate(sorted(glob.glob(os.path.join(root, "ef*.bytes")))):
        if limit is not None and n >= limit:
            break
        blob = open(path, "rb").read()
        src = os.path.splitext(os.path.basename(path))[0]
        for img in T.id3_images(blob, src):
            try:
                rec = recover(img, ops)
            except Exception as exc:                       # a crash is a census outcome, not a stop
                rows.append(CensusRow(img.label, "defeated", "recovery raised %s" % type(exc).__name__))
                continue
            sm = rec.machine
            rows.append(CensusRow(img.label, rec.verdict, rec.reason,
                                  len(sm.cases) if sm else 0, len(sm.phases) if sm else 0,
                                  sm.total_ticks if sm else None))
        if progress:
            progress(n, path)
    return rows


def census_summary(rows: Sequence[CensusRow]) -> Dict[str, object]:
    by = collections.Counter(r.verdict for r in rows)
    causes = collections.Counter(r.reason for r in rows if r.verdict == "defeated")
    out: Dict[str, object] = {"total": len(rows), "causes": causes}
    for v in VERDICTS:
        out[v] = by[v]
    return out


# ===========================================================================  (D) the report
def _fmt_op(c: HleCall) -> str:
    args = " ".join("$a%d=%#x" % (i, v) for i, v in enumerate(c.args) if v is not None)
    conf = c.confidence or "unnamed"
    return "op %d %s [%s]%s" % (c.op, c.name or "?", conf, (" " + args) if args else "")


def _phase_label(case: Case) -> str:
    roles = case.roles()
    if not roles:
        return "bookkeeping only"
    return "; ".join(roles)


def _quote(sm: StateMachine, offs: Sequence[int], notes: Dict[int, str]) -> List[str]:
    out: List[str] = []
    if sm.walk is None:
        return out
    for o in offs:
        ins = sm.walk.instrs.get(o)
        if ins is None:
            continue
        out.append("  %04x  %08x  %-30s %s"
                   % (o, ins.word, ins.text(), ("; " + notes[o]) if o in notes else ""))
    return out


def report_quotes(sms: Sequence[StateMachine]) -> List[Tuple[str, List[str]]]:
    """The report's structural evidence, capped at :data:`QUOTE_BUDGET` instructions in total.

    Two idioms carry the whole rung, so those are the two that get quoted: the ``$a0`` mode dispatch
    (the program is a callback, not a script) and the transition (the clock compare, the state
    store, and the ``-1`` that pins the frame model).
    """
    if not sms:
        return []
    sm = sms[0]
    out: List[Tuple[str, List[str]]] = []
    ent: List[int] = []
    if sm.walk is not None and sm.arms:
        # the first mode arm is the fall-through of its own `bne`, so the branch sits at -8
        cand = sm.arms[0].target - 8
        ins = sm.walk.instrs.get(cand)
        if ins is not None and ins.entry is not None and ins.entry.name in ("bne", "beq"):
            ent = [cand, cand + 4]
    if ent:
        out.append(("**The per-tick contract.** The program's very first branch is a dispatch on "
                    "`$a0`: report / initialise / tick. The state pointer arrives as `arg1` and is "
                    "parked in a callee-saved register in the branch's delay slot.",
                    _quote(sm, ent, {ent[0]: "$a0 == 0 -> the DESCRIBE arm (block size %s B)"
                                     % sm.state_block_bytes,
                                     ent[1]: "[delay slot] the state block pointer, kept for the "
                                             "whole tick"})))
    prim = None
    for c in sm.cases:
        for t in c.transitions:
            if t.guard_reg_is_clock and t.threshold is not None:
                prim = t
                break
        if prim:
            break
    if prim and prim.guard_off is not None:
        offs = [prim.guard_off, prim.guard_off + 4, prim.guard_off + 8, prim.off, prim.off + 4,
                prim.off + 8, prim.off + 12]
        reset = next((o for o in sm.clock_reset_sites if 0 < o - prim.off <= 32), None)
        offs = [o for o in offs if o <= (reset or prim.off + 12)]
        notes = {prim.guard_off: "the CLOCK compare: stay while clock < %d" % prim.threshold,
                 prim.off: "the TRANSITION: state = %s" % prim.to_state}
        if reset is not None:
            notes[reset] = ("the CLOCK RESET -- writing -1 only works if the host increments "
                            "BEFORE the next read, which is what makes the case N+1 ticks long")
            if reset not in offs:
                offs.append(reset)
        out.append(("**The transition, and the one store the whole frame model rests on.** Every "
                    "phase change in this program has this exact shape.",
                    _quote(sm, offs, notes)))
    # trim to the budget, keeping whole groups
    total = 0
    kept: List[Tuple[str, List[str]]] = []
    for title, lines in out:
        if total + len(lines) > QUOTE_BUDGET:
            lines = lines[:QUOTE_BUDGET - total]
        if lines:
            kept.append((title, lines))
            total += len(lines)
    return kept


def cited_ops(sms: Sequence[StateMachine]) -> Dict[int, dict]:
    out: Dict[int, dict] = {}
    for sm in sms:
        for c in list(sm.cases) + ([sm.tail] if sm.tail else []):
            for h in c.hle:
                out[h.op] = {"name": h.name, "confidence": h.confidence}
    return out


def replicate(sms: Sequence[StateMachine], paths: Sequence[str],
              effect: int) -> List[Tuple[str, List[Optional[int]], List[Tuple[int, int]]]]:
    """Re-fit every program against every archived capture.

    One capture agreeing with a model it was fitted to is weak; the same origins and the same hit
    counts falling out of independently recorded casts is not.
    """
    out = []
    for p in paths:
        cap = parse_capture(p, effect)
        fits = [fit_origin(sm, cap) for sm in sms]
        out.append((os.path.basename(p), [f.origin for f in fits],
                    [(f.hits, f.total) for f in fits]))
    return out


def write_report(fh, effect: int, sms: Sequence[StateMachine], ops: Dict[int, dict],
                 cap: Optional[Capture] = None, fits: Sequence[Fit] = (),
                 checks: Sequence[Sequence[Check]] = (), census: Optional[Dict] = None,
                 quotes: Sequence[Tuple[str, Sequence[str]]] = (),
                 replicas: Sequence[Tuple[str, List, List]] = ()) -> int:
    """Write the CHOREOGRAPHY report.  Returns the number of stock instructions quoted."""
    nq = sum(len(q[1]) for q in quotes)
    if nq > QUOTE_BUDGET:
        raise ValueError("quote budget exceeded: %d > %d" % (nq, QUOTE_BUDGET))
    W = fh.write
    beats = OBSERVED_BEATS.get(effect, ())
    W("# ef%03d — CHOREOGRAPHY (TIER R rung 3)\n\n" % effect)
    W("> Generated by `summon_inspect.py` from the effect's own bytes")
    if cap is not None:
        W(" and validated against the archived s53 capture `%s`" % cap.source)
    W(".\n> Structure, names and frame numbers only — no payload. "
      "Quoted stock instructions: **%d** (budget %d).\n\n" % (nq, QUOTE_BUDGET))

    # ---- the executive answer
    W("## 0. What happens at frame N\n\n")
    if cap is not None and fits:
        resets = dict(cap.motion_resets())
        rows = []
        for fit in fits:
            if fit.origin is None:
                continue
            obs = {fit.origin + b.tick for b in boundaries(fit.machine)
                   if b.observable and (fit.origin + b.tick) in resets}
            for p in fit.machine.phases:
                a = fit.origin + p.start_tick
                b = None if p.end_tick is None else fit.origin + p.end_tick
                if a in obs:
                    conf = "**measured** — the capture shows this phase starting here"
                elif p.ticks is None:
                    conf = "*inferred* — terminal; only the sequence ends it"
                else:
                    conf = "derived — duration from the code, origin fitted"
                rows.append((a, b, fit.machine.image, p, conf))
        rows.sort(key=lambda x: (x[0], x[2]))
        W("| frames | program | state | what the code does | ticks | confidence |\n")
        W("|---|---|---|---|---|---|\n")
        for a, b, img, p, conf in rows:
            W("| %s | `%s` | %d | %s | %s | %s |\n"
              % ("%d–%d" % (a, b) if b is not None else "%d–end" % a, img, p.state,
                 _phase_label(p.case), p.ticks if p.ticks else "terminal", conf))
        W("\nThe **durations** are read off the code (§2); only the **origin** of each program — the "
          "frame the sequence starts that chunk — is fitted to the capture, one free parameter per "
          "program (§4).\n\n")
        W("Read the confidence column literally. *measured* means the capture shows the event at "
          "that exact frame. *derived* means the code says how long the phase lasts and the frame "
          "number follows from the fitted origin — no capture row confirms that particular "
          "boundary. *inferred* means the program itself never ends the phase.\n\n")
        if beats:
            W("The beats on record for this effect (%s) are the human observation this table has to "
              "explain; the code says nothing about their names.\n\n"
              % ", ".join("*%s*" % b for b in beats))
    else:
        W("_No capture supplied — the table below is in program ticks, not frames._\n\n")

    # ---- the machine
    W("## 1. The entry model — a per-tick callback, not a script\n\n")
    for sm in sms:
        W("### `%s` entry `%#x`\n\n" % (sm.image, sm.entry))
        W("| `$a0` | arm | role | evidence |\n|---|---|---|---|\n")
        for arm in sm.arms:
            W("| %s | `%#x` | **%s** | %s |\n"
              % ("(else)" if arm.mode is None else str(arm.mode), arm.target, arm.role,
                 arm.detail or "—"))
        W("\n- state variable: **`%s + %#x`**%s\n"
          % (sm.state_base, sm.state_offset,
             " (block size **%d B**, from the describe arm)" % sm.state_block_bytes
             if sm.state_block_bytes else ""))
        W("- dispatch: `jr` at `%#x` through a %s-slot table at image `+%#x`\n"
          % (sm.dispatch_off, sm.bound, sm.table_off))
        W("- clock: **`%s`** — read at the top of the tick, reset at %d transition site%s\n"
          % (sm.clock, len(sm.clock_reset_sites), "" if len(sm.clock_reset_sites) == 1 else "s"))
        for n in sm.notes:
            W("- %s\n" % n)
        W("\n")

    W("## 2. The state graph\n\n")
    for sm in sms:
        W("**`%s`** — %d table slots → %d distinct case bodies%s\n\n"
          % (sm.image, sm.n_slots, len(sm.cases),
             " + a shared per-tick tail" if sm.tail else ""))
        W("| state(s) | body | instr | HLE calls | guard | → state | ticks |\n")
        W("|---|---|---|---|---|---|---|\n")
        for c in sm.cases:
            prim = next((x for x in c.transitions if x.guard_reg_is_clock), None)
            guard = ("`clock >= %d`" % prim.threshold) if prim and prim.threshold is not None \
                else ("`%d transition(s)`" % len(c.transitions) if c.transitions else "—")
            W("| %s | `%#x` | %d | %d | %s | %s | %s |\n"
              % (", ".join(str(s) for s in c.slots) or "—", c.target, len(c.body), len(c.hle),
                 guard, prim.to_state if prim and prim.to_state is not None else
                 ("terminal" if not c.transitions else "?"),
                 prim.ticks if prim and prim.ticks else "—"))
        if sm.tail:
            W("| (tail) | `%#x` | %d | %d | runs every tick after the case | — | — |\n"
              % (sm.tail.target, len(sm.tail.body), len(sm.tail.hle)))
        W("\n")
        if sm.dead_states:
            W("**Dead slots:** states %s are reachable from the dispatch but no transition ever "
              "assigns them — they land on the shared tail, i.e. a tick that does the common work "
              "and nothing else.\n\n" % ", ".join(str(s) for s in sm.dead_states))
        if sm.bad_targets:
            W("**Unreachable transition targets:** %s — a transition writes a state the table "
              "cannot dispatch. **This is a defect in the model or in the program; do not sand it "
              "off.**\n\n" % ", ".join(str(s) for s in sm.bad_targets))
        else:
            W("Every transition target is a real case, and every case is reachable from the "
              "dispatch.\n\n")

    W("## 3. What each phase actually calls\n\n")
    for sm in sms:
        W("### `%s`\n\n" % sm.image)
        for p in sm.phases:
            W("**state %d** (ticks %s) — %s\n\n"
              % (p.state, "%d–%s" % (p.start_tick, p.end_tick if p.end_tick is not None else "end"),
                 _phase_label(p.case)))
            seq = collections.Counter((h.op, h.name, h.confidence) for h in p.case.hle)
            if not seq:
                W("  (no HLE calls of its own)\n\n")
                continue
            W("| HLE | name | confidence | calls | earliest | constant args seen |\n"
              "|---|---|---|---|---|---|\n")
            for (op, name, conf), n in sorted(seq.items()):
                args = sorted({tuple(h.args) for h in p.case.hle if h.op == op},
                              key=lambda a: tuple(-1 if v is None else v for v in a))
                shown = []
                for a in args[:3]:
                    s = " ".join("$a%d=%#x" % (i, v) for i, v in enumerate(a) if v is not None)
                    if s:
                        shown.append(s)
                g = p.case.first_gate(op)
                when = "tick %d" % p.start_tick if not g or not g.threshold else \
                    "tick %d (`%s`)" % (p.start_tick + g.threshold, g)
                W("| op %d | %s | %s | %d | %s | %s |\n"
                  % (op, name or "—", conf or "unnamed", n, when, "; ".join(shown) or "—"))
            W("\nThe *earliest* column is the first tick the call can run: the phase's own start "
              "plus every `clock >=` condition that **dominates** the call site inside the case. "
              "A call with no gate runs on the phase's first tick.\n\n")
        for t in [c for c in sm.cases if c.is_tail] + ([sm.tail] if sm.tail else []):
            W("**the per-tick tail** (`%#x`, %d instructions, reached by every case's \"not yet\" "
              "branch) — %s\n\n" % (t.target, len(t.body), _phase_label(t)))

    if cap is not None and fits:
        W("## 4. Validation against the archived s53 capture\n\n")
        lo, hi = cap.span
        W("Capture `%s`, effect %d, frames %d–%d. The probe emits a row per draw pass; identical "
          "rows within a frame are collapsed.\n\n" % (cap.source, cap.effect, lo, hi))
        for fit, ck in zip(fits, checks):
            W("### `%s` — origin fitted to frame **%s**, %d/%d boundaries land exactly\n\n"
              % (fit.machine.image, fit.origin, fit.hits, fit.total))
            W("| check | predicted frame | observed | verdict | note |\n|---|---|---|---|---|\n")
            for c in ck:
                W("| %s | %s | %s | %s | %s |\n"
                  % (c.what, c.predicted if c.predicted is not None else "—",
                     c.observed if c.observed is not None else "—", c.verdict, c.note))
            W("\n")
        W("### Observed beats the capture supplies independently\n\n")
        W("| observable | frame(s) |\n|---|---|\n")
        W("| summon slot goes active | %s |\n" % cap.first(lambda c: bool(c.active)))
        W("| creature first drawn | %s |\n" % cap.first(lambda c: c.drawn))
        W("| bone pose last valid | %s |\n" % cap.last_bones_ok())
        W("| bone matrices become freed memory | %s |\n" % cap.first_bones_bad())
        W("| projection distance H changes | %s |\n"
          % ", ".join("f%d→%d" % (f, h) for f, h in cap.proj_changes()[:8]))
        W("\n")

        if replicas:
            W("### Replication across every archived capture\n\n")
            W("| capture | fitted origins | boundaries hit |\n|---|---|---|\n")
            for name, origins, hits in replicas:
                W("| `%s` | %s | %s |\n"
                  % (name, ", ".join("f%s" % o for o in origins),
                     ", ".join("%d/%d" % h for h in hits)))
            same = len({tuple(o) for _n, o, _h in replicas}) == 1
            W("\n%s\n\n" % ("**The same origins and the same hit counts fall out of every "
                            "independently recorded cast.** The alignment is a property of the "
                            "effect, not of the log it was fitted to." if same else
                            "**The captures do NOT agree on the origins.** That is a finding: "
                            "either the sequence starts the chunk at a variable frame, or the "
                            "fit is under-determined."))

        # ---- the camera
        W("## 4a. The camera story — sequence, not program\n\n")
        cam_ops = sorted(op for op in cited_ops(sms)
                         if set((ops.get(op) or {}).get("touches") or ())
                         & {"gteOFX", "gteOFY", "gteH", "curCam", "viewMatrix"})
        W("R2 established from the data side that the camera sub-file is not reachable from the "
          "program at all — the shots are played by the SEQUENCE, opcode `0x29`. From the code "
          "side: of the **%d** distinct HLE ops these phases call, **%d** touch "
          "`gteOFX`/`gteOFY`/`gteH`/`curCam`/`viewMatrix` directly%s.\n\n"
          % (len(cited_ops(sms)), len(cam_ops),
             "" if not cam_ops else ": %s" % ", ".join(
                 "`op %d %s` [%s] → %s" % (o, (ops.get(o) or {}).get("name") or "?",
                                           (ops.get(o) or {}).get("confidence") or "unnamed",
                                           ", ".join(sorted(set((ops.get(o) or {}).get("touches")
                                                                or ()) &
                                                            {"gteOFX", "gteOFY", "gteH", "curCam",
                                                             "viewMatrix"})))
                 for o in cam_ops)))
        if cam_ops:
            W("**Do not read that as the program moving the camera.** `hle_ops.json`'s `touches` "
              "column does not distinguish a read from a write, and a vertex projector must READ "
              "the projection registers to do its job. Nothing here shows a phase *setting* them, "
              "and R2's data-side result says it cannot reach the camera data to do so. What would "
              "settle it: a probe row logging `gteOFX/OFY/H` immediately before and after each "
              "call to that op — if the values are unchanged across the call, the read-only "
              "reading is confirmed outright.\n\n")
        starts = sorted({fit.origin + p.start_tick for fit in fits if fit.origin is not None
                         for p in fit.machine.phases})
        last = max(starts) if starts else 0
        W("What the capture shows is a camera cut in **lockstep** with the program anyway:\n\n")
        W("| frame | projection distance H | nearest phase boundary | offset |\n|---|---|---|---|\n")
        for f, h in cap.proj_changes():
            near = min(starts, key=lambda s: abs(s - f)) if starts else None
            d = None if near is None else f - near
            W("| %d | → %d | %s | %s |\n"
              % (f, h, near if near is not None else "—",
                 "—  *(after the last phase begins; the camera returning to its battle default)*"
                 if d is not None and f > last and abs(d) > 8 else
                 ("%+d" % d if d is not None else "—")))
        W("\nSo the shots and the phases are two clocks the author kept aligned by construction. "
          "**The consequence for anyone re-scoring a stock summon is R2's, unchanged: edit the "
          "sequence, not the program — but retime the program's phase thresholds to match, or the "
          "cut and the beat drift apart.**\n\n")

        # ---- the motion
        W("## 4b. The creature's motion story — clips by index, scrubbed by frame\n\n")
        W("The creature's animation is never addressed by pointer. A phase starts a clip with "
          "`op 26` (an INDEX into the id-5 model package) and pins or scrubs it with `op 100` "
          "(a frame NUMBER). Both are visible in the capture as the summon slot's motion counter.\n\n")
        W("| frame | program | phase entered | code issues | counter observed |\n|---|---|---|---|---|\n")
        for fit in fits:
            if fit.origin is None:
                continue
            for b in boundaries(fit.machine):
                if not b.observable:
                    continue
                f = fit.origin + b.tick
                W("| %d | `%s` | state %d | %s | %s |\n"
                  % (f, fit.machine.image, b.state,
                     "`op 100` frame %d" % b.expect_motion if b.expect_motion else "`op 26` restart",
                     resets.get(f, "—")))
        W("\nA counter that *holds* a value for a whole phase is `op 100` called every tick rather "
          "than once — the pose is being pinned, not played.\n\n")

    if census:
        W("## 5. Corpus census — does the recovery generalise?\n\n")
        W("| outcome | images | what it means |\n|---|---|---|\n")
        W("| clean state-machine recovery | %d | a stored phase variable, clock-guarded "
          "transitions, a timeline |\n" % census["clean"])
        W("| frame-dispatch | %d | the switch index is the caller's frame counter and nothing in "
          "the program writes it — slot k **is** frame k |\n" % census["frame-dispatch"])
        W("| trivial | %d | no compiled switch in any program entry: one per-tick body, no stored "
          "phase |\n" % census["trivial"])
        W("| defeated | %d | a switch is there and the recovery could not turn it into a timeline "
          "|\n" % census["defeated"])
        W("| **total** | **%d** | |\n\n" % census["total"])
        if census["causes"]:
            W("Defeated, by cause:\n\n")
            for cause, n in census["causes"].most_common():
                W("- %d × %s\n" % (n, cause))
            W("\n")
        W("So **%d of 385** id-3 images have a switch-driven program entry at all. The multi-phase "
          "choreography this report describes is the exception in FF9's effect corpus, not the "
          "rule — most effects are a single beat played every tick.\n\n"
          % (census["clean"] + census["frame-dispatch"] + census["defeated"]))

    if quotes:
        W("## 6. Evidence — %d annotated instructions\n\n" % nq)
        for title, lines in quotes:
            W("%s\n\n```\n%s\n```\n\n" % (title, "\n".join(lines)))

    W("## 7. Every HLE name this report cites\n\n")
    cited = cited_ops(sms)
    W("| op | name | confidence | source |\n|---|---|---|---|\n")
    for op in sorted(cited):
        row = ops.get(op, {})
        W("| %d | %s | %s | `hle_ops.json` |\n"
          % (op, row.get("name") or "—", row.get("confidence") or "unnamed"))
    W("\nA `medium` or `low` name is a *description*, not a fact; the prose above never promotes "
      "one. %d of the %d ops cited here are unnamed and appear as bare numbers.\n\n"
      % (sum(1 for op in cited if not (ops.get(op) or {}).get("name")), len(cited)))

    # ---- what this report cannot tell you
    W("## 8. What this report still cannot tell you\n\n")
    W("- **Where each program's clock starts is fitted, not read.** The program has no say in it; "
      "the sequence starts the chunk. One number per program, and the report shows the residuals "
      "so the fit can be judged rather than trusted.\n")
    W("- **A terminal phase has no end in the code.** Both of ef227's programs finish in a state "
      "that never transitions, so the frame the cast *stops* is a sequence event this rung cannot "
      "derive — only observe.\n")
    if cap is not None:
        W("- **The capture cannot say which program drew the creature on a given frame.** The "
          "summon slot is one shared slot (R1 finding 1), and the probe logs the slot, not the "
          "caller. Where two programs both draw, the attribution here is the model's, not the "
          "capture's. A probe row carrying the calling chunk's slot would settle it.\n")
        W("- **A motion-counter restart is not proof of a `SetMotion` call.** A looping clip wraps "
          "on its own; that is why only boundaries whose transition tail actually issues a motion "
          "call are scored, and why the value written is checked as well as the frame.\n")
    W("- **Within a phase, only *gated* calls carry a tick.** A call with no dominating clock "
      "condition is placed at the phase's first tick, which is a lower bound, not a schedule.\n")
    W("- **`medium` and `low` names are descriptions.** %d of the %d ops cited are unnamed "
      "entirely; a phase's label inherits every bit of that uncertainty.\n"
      % (sum(1 for op in cited if not (ops.get(op) or {}).get("name")), len(cited)))
    return nq


# ===========================================================================  CLI
def _load_ops() -> Dict[int, dict]:
    try:
        return A.load_hle_ops()
    except Exception:
        return {}


def _print_recovery(rec: Recovery) -> None:
    print("\n%s  verdict=%s %s" % (rec.image, rec.verdict, rec.reason))
    sm = rec.machine
    if sm is None:
        return
    print("  entry %#x  dispatch %#x  table +%#x  bound=%s" %
          (sm.entry, sm.dispatch_off, sm.table_off, sm.bound))
    print("  state = %s + %#x   block=%s B   clock = %s   resets at %s"
          % (sm.state_base, sm.state_offset, sm.state_block_bytes, sm.clock,
             ", ".join("%#x" % o for o in sm.clock_reset_sites)))
    print("  arms: " + ", ".join("$a0=%s->%#x:%s" % ("else" if a.mode is None else a.mode,
                                                     a.target, a.role) for a in sm.arms))
    for c in sm.cases:
        prim = next((x for x in c.transitions if x.guard_reg_is_clock), None)
        print("   case %-12s %#06x %4d instr %3d HLE  %s"
              % (",".join(str(s) for s in c.slots) or "-", c.target, len(c.body), len(c.hle),
                 ("clock>=%d -> %s" % (prim.threshold, prim.to_state)) if prim else
                 ("terminal" if not c.transitions else "%d transitions" % len(c.transitions))))
    if sm.tail:
        print("   TAIL         %#06x %4d instr %3d HLE" %
              (sm.tail.target, len(sm.tail.body), len(sm.tail.hle)))
    print("   phases: " + " -> ".join("s%d[%s ticks]" % (p.state, p.ticks if p.ticks else "term")
                                      for p in sm.phases))
    if sm.dead_states:
        print("   dead states: %s" % ", ".join(str(s) for s in sm.dead_states))
    if sm.bad_targets:
        print("   UNREACHABLE transition targets: %s" % sm.bad_targets)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("effect", nargs="?", help="an effect id (227) or an ef###.bytes path")
    ap.add_argument("--corpus", action="store_true", help="run the recovery census over the corpus")
    ap.add_argument("--corpus-root", default=SCRATCH_CORPUS)
    ap.add_argument("--capture", help="an s53 probe log to validate against")
    ap.add_argument("--report", metavar="OUT.md", help="write the CHOREOGRAPHY report here")
    ap.add_argument("--limit", type=int, help="census: stop after N containers")
    args = ap.parse_args(argv)
    ops = _load_ops()

    if args.corpus:
        rows = corpus_census(args.corpus_root, ops, limit=args.limit)
        s = census_summary(rows)
        print("corpus recovery census over %d id-3 images" % s["total"])
        for v in VERDICTS:
            print("  %-15s %4d" % (v, s[v]))
        for cause, n in s["causes"].most_common():
            print("      %4d  %s" % (n, cause))
        return 0

    if not args.effect:
        ap.error("give an effect id, a path, or --corpus")
    path = args.effect
    if not os.path.exists(path):
        path = os.path.join(args.corpus_root, "ef%03d.bytes" % int(args.effect))
    if not os.path.exists(path):
        print("no such image: %s" % path)
        return 2
    eff = int(os.path.basename(path)[2:5])
    blob = open(path, "rb").read()
    recs = recover_container(blob, "ef%03d" % eff, ops)
    for rec in recs:
        _print_recovery(rec)
    sms = [r.machine for r in recs if r.machine is not None]

    cap = fits = checks = None
    if args.capture:
        cap = parse_capture(args.capture, eff)
        fits = [fit_origin(sm, cap) for sm in sms]
        checks = validate_all(sms, cap, fits)
        for f, ck in zip(fits, checks):
            print("\n%s  origin=f%s  %d/%d boundaries exact" %
                  (f.machine.image, f.origin, f.hits, f.total))
            for c in ck:
                print("   %-28s pred=%-6s obs=%-6s %s"
                      % (c.what, c.predicted, c.observed, c.verdict))

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            n = write_report(fh, eff, sms, ops, cap, fits or (), checks or (),
                             quotes=report_quotes(sms))
        print("\nwrote %s (%d quoted instructions)" % (args.report, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
