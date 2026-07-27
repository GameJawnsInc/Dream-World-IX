r"""TIER W rung 5 -- E1 AUTO-DERIVATION: find a phase's clock constants in ANY summon's program.

    py retime_derive.py ef211:c0 5              # analyse one (effect, machine, state)
    py retime_derive.py ef211:c0 5 --ticks 48   # ... and print the edit set it would emit
    py retime_derive.py --corpus                # every clock-guarded phase in the clean-switch class

WHAT THIS IS, AND WHAT IT IS NOT
--------------------------------
:mod:`w3_program_edits` is **N-generic but ef227-LOCATED**: swap the stretch freely, swap the effect
never.  Its eight image offsets, its eight stock halfword guards and its eight untouched-gate values
were hand-recovered by the B0 audit.  This module is the other half: given ``(effect, machine,
state)`` it *finds* those sites in the target's own bytes, decides which of them a retime may touch,
and **refuses by name** the moment a decision stops being mechanical.

It is deliberately NOT a port of :mod:`w3_clock_emu`.  That module's ``tick()`` is a hand
transcription of one case body and has no route to generalisation (recon agent2 section 2.1).  What
travels is the *arithmetic*: the magic-reciprocal idiom, the selection rule, and the endpoint
identity.  A target derived here therefore gets a strictly WEAKER proof than ef227 got -- the
arithmetic endpoints, not the per-tick discrete-signal identity -- and that gap is stated in the
derivation's own report rather than papered over.

THE FIVE THINGS IT DERIVES
--------------------------
1. **the image file base** -- the chunk's id-3 resource offset, from ``ef_container`` (never 0x2D000);
2. **the threshold** -- ``summon_inspect``'s recovered ``Transition.guard_off`` for the phase, which
   names the ``slti`` deciding it;
3. **the reciprocals** -- a whole-case-body scan for the ``lui/ori/mult/mfhi/[addu]/sra/subu``
   skeleton, with both of the prototype scanner's blind spots closed: the **shift-0 form** (there is
   no ``sra`` at all -- ``/3`` at image 0x0CD4 in ef227's own s0 is exactly that class) and the
   **out-of-window magic** (ef211's ``c0`` s3 loads its magic far enough back that a fixed backward
   window reports "no reciprocal here", so the magic operand is found by dataflow instead).  A
   multiply this walker still cannot read is REPORTED, not dropped: if its operands are clock-derived
   and one of them is a 32-bit literal, the target is refused;
4. **every peer copy of each reciprocal's ``lui``/``ori``** -- by reaching definitions over the case
   body's CFG, which is what makes THE HALF-PATCH TRAP mechanical instead of lucky.  ef227's
   ``lui @0x0C04`` sits in a ``bne``'s delay slot and its twin at ``0x0C54`` on the equal path; a
   linear scan finds one and silently leaves the creature's arrival ramp wrong on half the ticks.
   Corpus-wide ~11.5% of reciprocals carry such a peer;
5. **the disposition** -- RETUNE vs KEEP, per reciprocal, from the DIVIDEND's own dataflow.

THE DISPOSITION RULE (B0's policy, made mechanical)
---------------------------------------------------
B0's policy is *the phase's discrete beats keep their stock ticks; the phase-normalised PROGRESS
ramps are retuned so they still land on their stock terminal value on the new last tick.*  The
question "is this reciprocal phase-normalised?" is answered here by **the dividend, not the
divisor**.  A divisor that merely happens to equal ``threshold - <some gate immediate>`` is
numerology; a dividend the program itself computes as ``4096 * (clock - 24)`` is a fact:

* dividend not clock-derived at all              -> **KEEP** (nothing to rebase);
* dividend is another recovered reciprocal's OUTPUT -> **KEEP** (it rebases with its parent for
  free -- ef227's Q-domain ``/3`` on the arrival ramp is exactly this class);
* dividend is linear in the clock, ``A * (clock - k)``, and ``divisor == threshold - k``
  -> **RETUNE** to ``new_threshold - k``;
* dividend is linear, ``divisor != threshold - k``, and the divisor equals a clock gate immediate
  found in the same case body -> **KEEP** (a self-contained sub-ramp bounded by its own gate);
* anything else -> **REFUSED BY NAME.**

``A`` is the ramp's own unit (4096 for the Q12 ramps, 150 for ef227's light column) and is recovered
through shift-add chains, so ``clock * 245`` written as four shifts and three adds reads as linear
rather than as noise.

THE GATE POLICY, and where it stops being mechanical.  Every intra-case clock gate BELOW the
threshold is KEPT -- that is B0's policy verbatim, not a decision this module makes: a discrete beat
keeps its stock tick.  A gate at or PAST the threshold is a different animal: in stock it can never
fire, and after a stretch it can, so its KEEP-vs-RETUNE disposition is a reading of what it drives
and the target is refused.  The floor falls out of the same policy -- a new threshold at or below
the largest gate would put a sub-phase boundary outside the phase containing it.

THE TWO SELF-GATES
------------------
1. **the canonical-magic check**: a site this rung will rewrite must be a reciprocal the compiler
   itself would have emitted (:func:`canonical_magic`).  ef227's own ``c0`` s10 divides by 24 using
   the ``/3`` magic shifted three further -- exact, legitimate, and not canonical -- and a site like
   that is refused rather than rewritten on a rule it disproves.
2. **the N = 0 identity gate**: :func:`build_edits` at ``n = 0`` MUST reproduce the target's stock
   bytes exactly, at every site it would touch.  That is not a nicety: it is the proof that the
   selection rule reads the original compiler's idiom rather than fitting a plausible answer, and
   :func:`derive` runs it before returning ANY edit set.

Run against ef227's own ``c0`` state 0 at N = +48 the whole pipeline reproduces
:data:`w3_program_edits.PROGRAM_EDITS` site for site and byte for byte -- the strongest check
available offline, and ``test_retime_derive.py`` asserts it.

MEASURED, over the corpus's 85 clock-guarded phases in the clean-switch class: **45 derive** and 40
refuse, every refusal naming its reason.

PROVENANCE
----------
Reads containers from the corpus or the install at run time.  Emits offsets, counts and small scalar
guards -- no stock byte run is embedded here and none is committed.
"""
from __future__ import annotations

import argparse
import collections
import os
import struct
import sys
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Sequence, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)
for _p in (_HERE, os.path.join(_STUDY, "tier-r"), os.path.join(_STUDY, "thomas-swap", "disasm")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tier_r_disasm as T                                     # noqa: E402
import summon_inspect as S                                    # noqa: E402
import ef_container as EC                                     # noqa: E402
import w3_program_edits as PE                                 # noqa: E402
import w3_clock_emu as EMU                                    # noqa: E402


class DeriveRefusal(RuntimeError):
    """Raised for every case the derivation declines to decide.  The message names the reason."""


# ============================================================ (0) the register-write model
#: An instruction's DESTINATION register, by name.  A name outside these four sets is UNMODELLED,
#: and an unmodelled instruction anywhere in a case body makes the reaching-definition pass unsound
#: -- so the derivation refuses rather than analysing a body it cannot read.  (``$zero`` targets are
#: architectural no-ops and are reported as "writes nothing".)
W_RD = frozenset(("add", "addu", "and", "jalr", "mfhi", "mflo", "nor", "or", "sll", "sllv", "slt",
                  "sltu", "sra", "srav", "srl", "srlv", "sub", "subu", "xor", "move"))
W_RT = frozenset(("addi", "addiu", "andi", "cfc0", "cfc1", "cfc2", "cfc3", "lb", "lbu", "lh", "lhu",
                  "li", "lui", "lw", "lwl", "lwr", "mfc0", "mfc1", "mfc2", "mfc3", "ori", "slti",
                  "sltiu", "xori"))
W_RA = frozenset(("jal", "bgezal", "bltzal"))
W_NONE = frozenset((
    "b", "bc0f", "bc0t", "bc1f", "bc1t", "bc2f", "bc2t", "bc3f", "bc3t", "beq", "bgez", "bgtz",
    "blez", "bltz", "bne", "break", "cop0", "cop1", "cop2", "cop3", "ctc0", "ctc1", "ctc2", "ctc3",
    "div", "divu", "j", "jr", "lwc0", "lwc1", "lwc2", "lwc3", "mtc0", "mtc1", "mtc2", "mtc3",
    "mthi", "mtlo", "mult", "multu", "nop", "sb", "sh", "sw", "swc0", "swc1", "swc2", "swc3",
    "swl", "swr", "syscall"))

#: MIPS ``$ra``
RA = 31


def dest_reg(ins: T.Instr) -> Tuple[Optional[int], bool]:
    """``(destination register or None, modelled?)`` for one decoded instruction."""
    if ins.entry is None:
        return None, False
    n = ins.entry.name
    if n in W_NONE:
        return None, True
    if n in W_RA:
        return RA, True
    if n in W_RD:
        r = ins.op(T.Ex.RD)
        return (r or None), True
    if n in W_RT:
        r = ins.op(T.Ex.RT)
        return (r or None), True
    return None, False


def source_regs(ins: T.Instr, dest: Optional[int]) -> List[int]:
    """The registers this instruction READS: its declared RS/RT/RD operands minus the destination.

    Written as "operands present, minus the destination KIND" rather than a per-name table on
    purpose: ``sll $v0, $v0, 12`` reads and writes the same register, and a naive ``x != dest``
    filter silently drops the read -- which is exactly the bug that made the first draft of this
    analysis report ef227's arrival dividend as not clock-derived.
    """
    if ins.entry is None:
        return []
    kinds = list(ins.entry.ex)
    out: List[int] = []
    for k in (T.Ex.RS, T.Ex.RT, T.Ex.RD):
        if k not in kinds:
            continue
        if k is T.Ex.RD and dest is not None and ins.op(T.Ex.RD) == dest:
            continue                                   # RD is the destination, not a source
        v = ins.op(k)
        if v:
            out.append(v)
    return out


# ============================================================ (1) the case-body CFG
def succ_offs(r: T.WalkResult, off: int, body: Set[int],
              jt_by_site: Dict[int, object]) -> List[int]:
    """Instruction-level successors inside one case body, with MIPS delay slots modelled.

    A transfer at ``off`` does not branch until its delay slot at ``off + 4`` has executed, so
    control leaves from the DELAY SLOT.  Getting this backwards would make a delay-slot ``lui`` --
    precisely ef227's ``0x0C04`` -- look unreachable from the ``ori`` it feeds.
    """
    prev = r.instrs.get(off - 4)
    if prev is not None and prev.entry is not None and prev.entry.is_transfer:
        n = prev.entry.name
        if n == "jr":
            jt = jt_by_site.get(off - 4)
            outs = list(getattr(jt, "targets", ()) or ())
        elif n in ("j", "b"):
            outs = [prev.ops[0]]
        elif n in ("jal", "jalr", "bltzal", "bgezal"):
            outs = [off + 4]
        else:
            bt = prev.op(T.Ex.BTARGET)
            outs = ([bt] if bt is not None else []) + [off + 4]
        return [o for o in outs if o in body]
    return [off + 4] if (off + 4) in body else []


def _preds(r, body, jt_by_site) -> Dict[int, List[int]]:
    p: Dict[int, List[int]] = collections.defaultdict(list)
    for o in body:
        for s in succ_offs(r, o, body, jt_by_site):
            p[s].append(o)
    return p


#: ``{(id(walk), register): (walk, {offset: reaching definitions})}`` -- the pass is per-register and
#: yields an answer for every offset at once, so recomputing it per query is pure waste.  Emptied at
#: the top of :func:`analyse_target`.
#:
#: THE ``id()``-REUSE TRAP, and why the value carries the walk it was computed for.
#: ``id()`` is an ADDRESS, and CPython recycles an address the moment its object is collected.  The
#: original key was ``(id(walk), reg)`` alone, and the comment claimed safety because
#: "``analyse_target`` is the only place a new case body enters" -- but :func:`reaching_defs` is
#: reachable from :func:`_resolve_peers` and :func:`dividend_form` WITHOUT going through
#: ``analyse_target``, which is exactly how every unit test calls it.  Short-lived ``WalkResult``
#: objects then land on each other's freed addresses and one test silently reads another's
#: reaching-definition map.  MEASURED: ``test_retime_derive.py`` passes 55/55 alone and FAILS 2-3
#: tests when run after ``test_retime.py`` in the same process, with the failing set varying between
#: runs -- non-determinism, in a module whose whole job is to refuse when it cannot be sure.
#: The fix is one identity comparison: a hit must prove it was computed for THIS object, and an
#: address collision degrades to a cache miss (recompute), never to a wrong answer.
_REACH_CACHE: Dict[Tuple[int, int], Tuple["T.WalkResult", Dict[int, FrozenSet[int]]]] = {}


def reaching_defs(r: T.WalkResult, body: Set[int], jt_by_site, reg: int, at: int) -> Set[int]:
    """Every definition of ``reg`` that can reach ``at`` on some path through the case body.

    THE PEER-``lui`` PASS.  An over-approximation on purpose: a definition that *might* reach is
    reported, because the failure this exists to prevent is patching one copy of a duplicated
    constant and leaving its twin.  An unmodelled instruction anywhere in the body would make the
    kill sets wrong, so :func:`analyse_target` refuses such a body before this ever runs.
    """
    key = (id(r), reg)
    cached = _REACH_CACHE.get(key)
    if cached is not None and cached[0] is r:                # identity, not just address
        return set(cached[1].get(at, frozenset()))
    computed = _reaching_map(r, body, jt_by_site, reg)
    _REACH_CACHE[key] = (r, computed)                        # the strong ref also pins the address
    return set(computed.get(at, frozenset()))


def _reaching_map(r: T.WalkResult, body: Set[int], jt_by_site, reg: int) -> Dict[int, FrozenSet[int]]:
    body = set(body)
    preds = _preds(r, body, jt_by_site)
    IN: Dict[int, FrozenSet[int]] = {o: frozenset() for o in body}
    OUT: Dict[int, FrozenSet[int]] = {o: frozenset() for o in body}
    order = sorted(body)
    for _ in range(1000):
        changed = False
        for o in order:
            s: Set[int] = set()
            for p in preds[o]:
                s |= OUT[p]
            nin = frozenset(s)
            ins = r.instrs.get(o)
            nout = nin
            if ins is not None:
                d, _ok = dest_reg(ins)
                if d == reg:
                    nout = frozenset({o})
            if nin != IN[o] or nout != OUT[o]:
                IN[o], OUT[o] = nin, nout
                changed = True
        if not changed:
            break
    else:                                                     # pragma: no cover - 1000 rounds
        raise DeriveRefusal("the reaching-definition pass did not converge on this case body")
    return IN


def _dataflow(r, body, jt_by_site, step, seed: FrozenSet):
    body = set(body)
    preds = _preds(r, body, jt_by_site)
    IN = {o: frozenset() for o in body}
    OUT = {o: frozenset() for o in body}
    entries = {o for o in body if not preds[o]}
    for _ in range(1000):
        changed = False
        for o in sorted(body):
            s = set()
            for p in preds[o]:
                s |= OUT[p]
            if o in entries:
                s |= seed
            nin = frozenset(s)
            ins = r.instrs.get(o)
            nout = frozenset(step(o, ins, set(s))) if ins is not None else nin
            if nin != IN[o] or nout != OUT[o]:
                IN[o], OUT[o] = nin, nout
                changed = True
        if not changed:
            break
    else:                                                     # pragma: no cover
        raise DeriveRefusal("a dataflow pass did not converge on this case body")
    return IN


# ============================================================ (2) the clock
@dataclass(frozen=True)
class ClockGate:
    """A clock comparison inside the case body that is NOT the phase transition's own guard."""
    off: int
    kind: str                # slti | sltiu | beq | bne
    imm: int


def clock_source(r, body, jt_by_site, guard_off: int) -> Tuple[Optional[Tuple[int, int]],
                                                                Optional[int]]:
    """``(clock memory cell, live-in clock register)`` -- exactly one of the two is not None.

    The transition guard's own compared register IS the clock (``summon_inspect`` proved that
    symbolically when it set ``guard_reg_is_clock``).  Either it is loaded inside the case body --
    then the ``(offset, base)`` pair it is loaded from is the clock cell, and every other load of
    that pair is another clock register -- or it has no definition in the body at all, in which case
    it is live-in and carries the clock by itself.  A2 warns the register DIFFERS per program
    (``$s5`` in ef227's c0, a reloaded cell in its c1), so neither form may be assumed.
    """
    ins = r.instrs.get(guard_off)
    if ins is None or ins.entry is None:
        raise DeriveRefusal("the phase guard at image %#06x did not decode" % guard_off)
    reg = ins.op(T.Ex.RS)
    if not reg:
        raise DeriveRefusal("the phase guard at image %#06x compares no register" % guard_off)
    defs = reaching_defs(r, body, jt_by_site, reg, guard_off)
    if not defs:
        return None, reg
    cells = set()
    for d in defs:
        di = r.instrs.get(d)
        if di is None or di.entry is None or di.entry.name != "lw":
            raise DeriveRefusal(
                "the phase guard's clock register is defined at image %#06x by `%s`, not by a load "
                "-- the clock cell cannot be named, so no other clock register in the body can be "
                "recognised" % (d, di.entry.name if di and di.entry else "<invalid>"))
        cells.add((di.op(T.Ex.OFF_BASE), di.base_reg))
    if len(cells) != 1:
        raise DeriveRefusal("the phase guard's clock register is loaded from %d different cells"
                            % len(cells))
    return cells.pop(), None


def clock_registers(r, body, jt_by_site, cell, live_in) -> Dict[int, FrozenSet[int]]:
    """NARROW: ``{offset: registers holding the clock ITSELF}`` -- loads of the cell and plain copies.

    Deliberately narrower than the taint below.  A gate is ``clock < N``; a comparison against
    something merely *derived* from the clock is not a gate and must not be mined for an immediate.
    """
    def step(off, ins, cur):
        if ins.entry is None:
            return cur
        n = ins.entry.name
        if n == "lw":
            rt = ins.op(T.Ex.RT)
            if rt:
                if cell is not None and (ins.op(T.Ex.OFF_BASE), ins.base_reg) == cell:
                    cur.add(rt)
                else:
                    cur.discard(rt)
            return cur
        d, _ok = dest_reg(ins)
        if d:
            src = None
            if n == "move":
                src = ins.op(T.Ex.RS)
            elif n in ("addu", "or") and 0 in (ins.op(T.Ex.RS), ins.op(T.Ex.RT)):
                src = ins.op(T.Ex.RS) or ins.op(T.Ex.RT)
            elif n in ("addiu", "addi", "ori") and ins.op(T.Ex.SIMM) == 0:
                src = ins.op(T.Ex.RS)
            if src and src in cur:
                cur.add(d)
            else:
                cur.discard(d)
        return cur
    return _dataflow(r, body, jt_by_site, step, frozenset({live_in} if live_in else ()))


def clock_taint(r, body, jt_by_site, cell, live_in, kill_at: Dict[int, int] = None
                ) -> Dict[int, FrozenSet]:
    """BROAD may-taint: anything arithmetically derived from the clock, through registers, ``HI/LO``
    and stack slots.  Over-approximating on purpose -- an over-tainted dividend costs a REFUSAL, an
    under-tainted one costs a silently unretimed ramp.

    ``kill_at`` maps ``{definition offset: register}``; those definitions are treated as CLEAN.  That
    is how "derived only through another reciprocal's output" is decided: re-run with the parent
    reciprocals' outputs killed and see whether any independent clock path remains.
    """
    kill_at = kill_at or {}

    def step(off, ins, cur):
        if ins.entry is None:
            return cur
        n = ins.entry.name
        if n == "lw":
            rt = ins.op(T.Ex.RT)
            key = ("M", ins.op(T.Ex.OFF_BASE), ins.base_reg)
            if rt:
                if kill_at.get(off) == rt:
                    cur.discard(rt)
                elif (cell is not None and (ins.op(T.Ex.OFF_BASE), ins.base_reg) == cell) \
                        or key in cur:
                    cur.add(rt)
                else:
                    cur.discard(rt)
            return cur
        if n == "sw":
            key = ("M", ins.op(T.Ex.OFF_BASE), ins.base_reg)
            if ins.op(T.Ex.RT) in cur:
                cur.add(key)
            else:
                cur.discard(key)
            return cur
        if n in ("mult", "multu", "div", "divu"):
            if any(x in cur for x in (ins.op(T.Ex.RS), ins.op(T.Ex.RT))):
                cur.add(("HL",))
            else:
                cur.discard(("HL",))
            return cur
        d, _ok = dest_reg(ins)
        if d:
            if kill_at.get(off) == d:
                cur.discard(d)
            elif n in ("mfhi", "mflo"):
                if ("HL",) in cur:
                    cur.add(d)
                else:
                    cur.discard(d)
            elif any(x in cur for x in source_regs(ins, d)):
                cur.add(d)
            else:
                cur.discard(d)
        return cur
    return _dataflow(r, body, jt_by_site, step, frozenset({live_in} if live_in else ()))


def _const_reaching(r, body, jt_by_site, reg: int, at: int) -> Optional[int]:
    """The single literal value reaching ``reg`` at ``at``, or None if it is not a unique constant."""
    ds = reaching_defs(r, body, jt_by_site, reg, at)
    if not ds:
        return None
    vals = set()
    for d in ds:
        di = r.instrs.get(d)
        if di is None or di.entry is None:
            return None
        if di.entry.name in ("addiu", "addi") and di.op(T.Ex.RS) == 0:
            vals.add(di.op(T.Ex.SIMM))
        elif di.entry.name == "ori" and di.op(T.Ex.RS) == 0:
            vals.add(di.op(T.Ex.UIMM))
        else:
            return None
    return vals.pop() if len(vals) == 1 else None


def find_gates(r, body, jt_by_site, cregs, skip: Sequence[int] = ()) -> List[ClockGate]:
    """Every intra-case clock comparison except the phase transition's own guard.

    Two forms, both attested in ef227's s0: ``slti clock, N`` (a sub-phase window) and
    ``beq/bne clock, <li N>`` (an equality one-shot -- the ``clock == 24`` motion start and the
    ``clock == 44`` trail latch).
    """
    skip = set(skip)
    out: List[ClockGate] = []
    for o in sorted(body):
        if o in skip:
            continue
        ins = r.instrs.get(o)
        if ins is None or ins.entry is None:
            continue
        n = ins.entry.name
        cur = cregs.get(o, frozenset())
        if n in ("slti", "sltiu"):
            if ins.op(T.Ex.RS) in cur:
                v = ins.op(T.Ex.SIMM)
                if v is not None:
                    out.append(ClockGate(o, n, v))
        elif n in ("beq", "bne"):
            a, b = ins.op(T.Ex.RS), ins.op(T.Ex.RT)
            for x, y in ((a, b), (b, a)):
                if x in cur and y and y not in cur:
                    v = _const_reaching(r, body, jt_by_site, y, o)
                    if v is not None and v > 0:
                        out.append(ClockGate(o, n, v))
                    break
    return out


# ============================================================ (3) the reciprocal scan
@dataclass
class Reciprocal:
    """One magic-division site, located down to every byte a retime would have to write."""
    mult_off: int
    lui_offs: Tuple[int, ...]        # EVERY peer copy, from reaching definitions
    ori_offs: Tuple[int, ...]
    sra_off: Optional[int]           # None for the shift-0 form
    out_off: Optional[int]           # the closing ``subu`` -- the ramp's own output
    out_reg: Optional[int]
    magic: int
    shift: int
    addback: bool
    divisor: int
    scale: Optional[int]             # the ``A`` in ``dividend = A * clock + B`` (the ramp's unit)
    origin: Optional[int]            # the ``k`` in ``A * (clock - k)``; None when not affine
    tainted: bool
    parent: Optional[int]            # the mult_off of the reciprocal whose output feeds this one
    disposition: str = "?"           # RETUNE | KEEP | REFUSE
    reason: str = ""

    @property
    def peers(self) -> int:
        return max(0, len(self.lui_offs) - 1)

    @property
    def form(self) -> str:
        if self.parent is not None:
            return "the output of the reciprocal at image %#06x" % self.parent
        if self.origin is not None:
            return "%d * (clock - %d)" % (self.scale, self.origin)
        return "clock-derived, unreadable" if self.tainted else "not clock-derived"


def _magic_operand(r, body, jt_by_site, mult_off: int) -> Optional[dict]:
    """Which operand of this multiply carries a 32-bit ``lui``+``ori`` literal, found by DATAFLOW.

    An earlier draft searched a fixed 24-instruction window backwards from the ``mult``.  That is
    how a real reciprocal hides: ef211's ``c0`` s3 loads its ``/3`` magic well outside any such
    window, so the window scan reported "no skeleton" and the phase looked clean when it was not.
    Reaching definitions have no window.
    """
    ins = r.instrs[mult_off]
    for reg, other in ((ins.op(T.Ex.RS), ins.op(T.Ex.RT)), (ins.op(T.Ex.RT), ins.op(T.Ex.RS))):
        if not reg:
            continue
        lo = _uniform_defs(r, reaching_defs(r, body, jt_by_site, reg, mult_off), "ori",
                           lambda i: i.ops[2])
        if lo is None:
            continue
        ori_off, lo_imm = lo
        hi = _uniform_defs(r, reaching_defs(r, body, jt_by_site,
                                            r.instrs[ori_off].op(T.Ex.RS), ori_off),
                           "lui", lambda i: i.ops[1])
        if hi is None:
            continue
        lui_off, hi_imm = hi
        return {"magic": (hi_imm << 16) | lo_imm, "lui": lui_off, "ori": ori_off,
                "dividend": other}
    return None


def _uniform_defs(r, offs, kind: str, imm_of):
    """``(representative offset, immediate)`` when every reaching def is a ``kind`` with one value.

    MORE THAN ONE DEF IS THE NORMAL CASE, not the failure case: ef227's arrival magic is loaded by
    two ``lui`` on two paths, and requiring a single definition here would make the whole reciprocal
    invisible -- silently leaving the ramp dividing by the old phase length.  Disagreeing
    immediates are left for :func:`_resolve_peers` to refuse by name.
    """
    if not offs:
        return None
    ins = [r.instrs.get(o) for o in offs]
    if any(i is None or i.entry is None or i.entry.name != kind for i in ins):
        return None
    vals = {imm_of(i) for i in ins}
    return (min(offs), vals.pop()) if len(vals) == 1 else None


def _literal32_operand(r, body, jt_by_site, mult_off: int) -> Optional[int]:
    """The 32-bit ``lui``+``ori`` literal one of this multiply's operands carries, or ``None``.

    A magic reciprocal's divisor is a compile-time constant, so its magic is ALWAYS a literal pair.
    A multiply by a value loaded at run time cannot be a reciprocal however unreadable the
    surrounding code is, and refusing on it would be refusing on ordinary arithmetic.
    """
    m = _magic_operand(r, body, jt_by_site, mult_off)
    return m["magic"] if m else None


def _skeleton(r, body, jt_by_site, mult_off) -> Optional[dict]:
    """The magic operand (by dataflow) plus the forward ``mfhi``/``addu``/``sra``/``subu`` chain."""
    m = _magic_operand(r, body, jt_by_site, mult_off)
    if m is None:
        return None
    magic, lui_off, ori_off, dividend = m["magic"], m["lui"], m["ori"], m["dividend"]
    hi = cur = shift = sra_off = None
    addback = False
    for k in range(1, 20):
        n = r.instrs.get(mult_off + 4 * k)
        if n is None or n.entry is None:
            continue
        if n.entry.name == "mfhi" and hi is None:
            hi = n.ops[0]
            cur = hi
            continue
        if cur is None:
            continue
        if n.entry.name == "addu" and cur in (n.ops[1], n.ops[2]):
            addback = True
            cur = n.op(T.Ex.RD)
            continue
        if n.entry.name in ("sra", "srl") and n.ops[1] == cur:
            shift = n.ops[2]
            sra_off = n.off
            cur = n.op(T.Ex.RD)
            break
    # the closing ``subu q, shifted, (x >> 31)`` -- the ramp's OUTPUT register
    out_off = out_reg = None
    start = (sra_off if sra_off is not None else mult_off)
    for k in range(1, 8):
        n = r.instrs.get(start + 4 * k)
        if n is None or n.entry is None:
            continue
        if n.entry.name == "subu" and cur is not None and n.op(T.Ex.RS) == cur:
            out_off, out_reg = n.off, n.op(T.Ex.RD)
            break
    return dict(magic=magic, lui=lui_off, ori=ori_off, sra=sra_off, shift=shift,
                addback=addback, dividend=dividend, out_off=out_off, out_reg=out_reg)


#: how deep the dividend walk will chase a shift-add chain before giving up.  ``clock * 245`` in
#: ef227's beam block is five instructions; 40 is generous and bounds the recursion.
_FORM_DEPTH = 40


def dividend_form(r, body, jt_by_site, reg: int, at: int, cregs,
                  recip_out: Dict[int, Tuple[int, int]], depth: int = 0):
    """What the value in ``reg`` at ``at`` IS, as one of four verdicts.

    ``("linear", A, B)``   the value is ``A * clock + B`` -- the only form a phase-normalised ramp
                           can take.  Shift-add chains count: ef227's beam phase is
                           ``clock * 245`` written as four shifts and three adds, and a walker that
                           only understood ``sll`` would call it non-affine and refuse a phase that
                           is perfectly readable.
    ``("parent", off)``    the value is a reciprocal's OUTPUT -- this ramp is a function of that one
                           and rebases with it for free (ef227's Q-domain ``/3`` on ``arrival``).
    ``("const", B)``       a literal; nothing to do with the clock.
    ``None``               undecidable.  Combined with the clock taint this becomes either a KEEP
                           (not clock-derived at all) or a REFUSAL (clock-derived, unreadable).

    THE DISCRIMINATOR THIS EXISTS FOR: ef227's arrival ramp divides by 45 and its case body also
    happens to carry a ``clock < 45`` gate, so the divisor alone cannot tell "normalised over the
    phase from tick 24" from "self-contained under its own 45-tick gate".  The dividend can -- the
    program itself computes ``(clock - 24) << 12``.
    """
    if depth > _FORM_DEPTH:
        return None
    if reg == 0:
        return ("const", 0)
    if reg in cregs.get(at, frozenset()):
        return ("linear", 1, 0)
    ds = reaching_defs(r, body, jt_by_site, reg, at)
    if len(ds) != 1:
        return None
    d = ds.pop()
    di = r.instrs.get(d)
    if di is None or di.entry is None:
        return None
    if recip_out.get(d, (None, None))[0] == reg:
        return ("parent", recip_out[d][1])
    n = di.entry.name

    def sub(rg):
        return dividend_form(r, body, jt_by_site, rg, d, cregs, recip_out, depth + 1)

    if n in ("move",):
        return sub(di.op(T.Ex.RS))
    if n == "lui":
        return ("const", di.ops[1] << 16)
    if n in ("addiu", "addi"):
        a = sub(di.op(T.Ex.RS))
        if a and a[0] == "linear":
            return ("linear", a[1], a[2] + di.op(T.Ex.SIMM))
        if a and a[0] == "const":
            return ("const", a[1] + di.op(T.Ex.SIMM))
        return None
    if n == "ori":
        a = sub(di.op(T.Ex.RS))
        if a and a[0] == "const":
            return ("const", a[1] | di.ops[2])
        return None
    if n in ("sll",):
        a = sub(di.op(T.Ex.RT))
        k = 1 << di.ops[2]
        if a and a[0] == "linear":
            return ("linear", a[1] * k, a[2] * k)
        if a and a[0] == "const":
            return ("const", a[1] * k)
        return None
    if n in ("addu", "subu", "add", "sub", "or"):
        x, y = sub(di.op(T.Ex.RS)), sub(di.op(T.Ex.RT))
        if n == "or":                                   # only the ``or rd, rs, $zero`` copy idiom
            if di.op(T.Ex.RT) == 0 and x:
                return x
            if di.op(T.Ex.RS) == 0 and y:
                return y
            return None
        if not x or not y or "parent" in (x[0], y[0]):
            return None
        sign = -1 if n in ("subu", "sub") else 1
        ax, bx = (x[1], x[2]) if x[0] == "linear" else (0, x[1])
        ay, by = (y[1], y[2]) if y[0] == "linear" else (0, y[1])
        A, B = ax + sign * ay, bx + sign * by
        return ("linear", A, B) if A else ("const", B)
    return None


def scan_reciprocals(r, body, jt_by_site, cregs, taint
                     ) -> Tuple[List[Reciprocal], List[int]]:
    """``(reciprocals, unreadable multiply sites)`` for one case body.

    Two passes: the skeletons first (so every reciprocal's OUTPUT register is known), then the
    dividend forms (so a ramp fed by another ramp's output can say so instead of looking unreadable).

    THE SCANNER'S OWN BLIND SPOT, closed rather than documented.  The prototype this grew from could
    not see a **shift-0** reciprocal at all -- there is no ``sra`` after the ``mfhi``, which is
    exactly how ef227's own Q-domain ``/3`` at image 0x0CD4 is emitted -- so it silently reported
    four of that phase's five.  Here shift 0 is tried whenever no shift instruction is found, and
    ``_recover_divisor`` validates the guess against real division rather than accepting it.  What is
    still unreadable is returned as the second element instead of being dropped: a ``mult`` this
    walker cannot resolve into a reciprocal might BE one, and :func:`analyse_target` refuses if its
    operands are clock-derived.
    """
    skels: List[Tuple[int, dict, int, Optional[int], int]] = []
    unreadable: List[int] = []
    for off in sorted(body):
        ins = r.instrs.get(off)
        if ins is None or ins.entry is None or ins.entry.name not in ("mult", "multu"):
            continue
        sk = _skeleton(r, body, jt_by_site, off)
        if sk is None:
            unreadable.append(off)
            continue
        # the shift-0 form has no ``sra`` at all (ef227's Q-domain /3 at image 0x0CD4).  Try the
        # recovered shift first, then 0; ``_recover_divisor`` self-validates against real division,
        # so a wrong guess is rejected rather than accepted.
        cands = ([(sk["shift"], sk["sra"])] if sk["shift"] is not None else []) + [(0, None)]
        found = None
        for sh, so in cands:
            try:
                d = EMU._recover_divisor(sk["magic"], sh, sk["addback"])
            except Exception:
                continue
            found = (sh, so, d)
            break
        if found is None:
            unreadable.append(off)
            continue
        sh, so, div = found
        skels.append((off, sk, sh, so, div))

    recip_out = {sk["out_off"]: (sk["out_reg"], off)
                 for off, sk, _sh, _so, _d in skels if sk["out_off"] is not None and sk["out_reg"]}
    out: List[Reciprocal] = []
    for off, sk, sh, so, div in skels:
        ins = r.instrs[off]
        lui = r.instrs[sk["lui"]]
        lui_peers = _resolve_peers(r, body, jt_by_site, sk["ori"], lui.ops[0], lui.ops[1], "lui")
        ori = r.instrs[sk["ori"]]
        ori_peers = _resolve_peers(r, body, jt_by_site, off, ori.ops[0], ori.ops[2], "ori")
        tset = taint.get(off, frozenset())
        tainted = any(x in tset for x in (ins.op(T.Ex.RS), ins.op(T.Ex.RT)))
        form = dividend_form(r, body, jt_by_site, sk["dividend"], off, cregs, recip_out)
        scale = origin = parent = None
        if form and form[0] == "linear":
            A, B = form[1], form[2]
            if A > 0 and B % A == 0:
                scale, origin = A, -(B // A)
        elif form and form[0] == "parent":
            parent = form[1]
        elif form and form[0] == "const":
            tainted = False
        out.append(Reciprocal(
            mult_off=off, lui_offs=lui_peers, ori_offs=ori_peers,
            sra_off=(so if sh == sk["shift"] else None), out_off=sk["out_off"],
            out_reg=sk["out_reg"], magic=sk["magic"], shift=sh, addback=sk["addback"],
            divisor=div, scale=scale, origin=origin, tainted=tainted, parent=parent))
    return out, unreadable


def _product_half(r, mult_off: int, window: int = 20) -> Optional[str]:
    """``"hi"``, ``"lo"`` or ``None`` -- which half of the 64-bit product this multiply is read for.

    The whole magic-division idiom hangs on ``mfhi``: the quotient is the HIGH word of
    ``x * magic``.  A multiply whose result is taken with ``mflo`` is an ordinary product (ef227's
    s0 alone has four -- the creature's radius scaling and the beam maths) and can never be a
    reciprocal, so it does not have to be readable for the phase to be derivable.
    """
    for k in range(1, window):
        n = r.instrs.get(mult_off + 4 * k)
        if n is None or n.entry is None:
            continue
        if n.entry.name in ("mult", "multu", "div", "divu"):
            return None                                       # a second product intervenes
        if n.entry.name == "mfhi":
            return "hi"
        if n.entry.name == "mflo":
            return "lo"
    return None


def _resolve_peers(r, body, jt_by_site, consumer_off: int, reg: int, imm: int,
                   what: str) -> Tuple[int, ...]:
    """Every copy of the ``lui``/``ori`` that feeds ``consumer_off``.  ANY unresolved copy refuses.

    Three ways this refuses, all of them the half-patch trap wearing a different hat:

    * a definition reaching the consumer that is not this instruction kind, or carries a DIFFERENT
      immediate -- the consumer is fed two different constants on two paths;
    * a same-register/same-immediate instruction sitting in the case body that reaching definitions
      says cannot reach the consumer -- it may be a copy this analysis is simply not seeing;
    * no reaching definition at all -- the constant comes from outside the body.
    """
    ds = reaching_defs(r, body, jt_by_site, reg, consumer_off)
    if not ds:
        raise DeriveRefusal(
            "the %s feeding the reciprocal at image %#06x has NO definition inside the case body -- "
            "its constant is set upstream and this pass cannot enumerate its copies"
            % (what, consumer_off))
    kind = "lui" if what == "lui" else "ori"
    imm_of = (lambda i: i.ops[1]) if what == "lui" else (lambda i: i.ops[2])
    resolved = []
    for d in sorted(ds):
        di = r.instrs.get(d)
        if di is None or di.entry is None or di.entry.name != kind:
            raise DeriveRefusal(
                "the reciprocal consumed at image %#06x is reached by a `%s` definition at %#06x "
                "that is not a `%s` -- the magic is not a pair of literal halves on every path"
                % (consumer_off, di.entry.name if di and di.entry else "<invalid>", d, kind))
        if imm_of(di) != imm:
            raise DeriveRefusal(
                "the reciprocal consumed at image %#06x is fed TWO different %s immediates "
                "(%#06x at %#06x vs %#06x) -- retuning it would be right on one path and wrong on "
                "the other" % (consumer_off, kind, imm, d, imm_of(di)))
        resolved.append(d)
    same = [o for o in sorted(body)
            if (lambda i: i is not None and i.entry is not None and i.entry.name == kind
                and i.ops[0] == reg and imm_of(i) == imm)(r.instrs.get(o))]
    stray = [o for o in same if o not in resolved]
    if stray:
        raise DeriveRefusal(
            "THE HALF-PATCH TRAP: the case body carries %d more `%s $%d, %#06x` at %s that reaching "
            "definitions cannot show reaching the consumer at image %#06x. Patch the ones we can see "
            "and the ramp is right on some paths and wrong on others -- ef227's own arrival magic is "
            "emitted twice for exactly this reason (B0 section 2.1), so this refuses instead of "
            "guessing" % (len(stray), kind, reg, imm, ", ".join("%#06x" % o for o in stray),
                          consumer_off))
    return tuple(resolved)


# ============================================================ (4) the target
@dataclass
class Target:
    """One ``(effect, machine, state)`` phase, analysed."""
    effect: int
    image: str                       # "ef211:c0"
    chunk_slot: int
    state: int
    image_base: int                  # FILE offset of the chunk's id-3 payload
    threshold: int
    guard_off: int                   # image offset of the deciding ``slti``
    start_tick: int
    ticks: int
    gates: Tuple[ClockGate, ...]
    reciprocals: Tuple[Reciprocal, ...]
    refusals: Tuple[str, ...] = ()

    @property
    def guard_file_off(self) -> int:
        return self.image_base + self.guard_off

    @property
    def derivable(self) -> bool:
        return not self.refusals

    @property
    def retuned(self) -> Tuple[Reciprocal, ...]:
        return tuple(x for x in self.reciprocals if x.disposition == "RETUNE")

    @property
    def peer_count(self) -> int:
        return sum(x.peers for x in self.reciprocals)

    @property
    def max_gate(self) -> int:
        return max((g.imm for g in self.gates), default=0)


def id3_images_with_base(blob: bytes, source: str) -> List[Tuple[T.Id3Image, int]]:
    """``tier_r_disasm.id3_images`` plus each image's own FILE offset.

    ``IMAGE_BASE = 0x2D000`` is ef227 chunk 0's number and nothing else's -- ef211's c0 sits at
    0x35000, ef251's at 0x2F000.  The base is a resource offset, so it is read, never assumed.
    """
    c = EC.parse_header(blob)
    bases: List[int] = []
    for ch in c.chunks:
        for res in ch.resources:
            if res.id == 3:
                bases.append(res.offset)
    imgs = T.id3_images(blob, source)
    if len(imgs) != len(bases):                               # pragma: no cover - parser drift
        raise DeriveRefusal("id-3 image count %d != resource count %d" % (len(imgs), len(bases)))
    return list(zip(imgs, bases))


def recover_machine(blob: bytes, source: str, image: str):
    """``(StateMachine, image file base)`` for ``ef###:cN``, or a named refusal."""
    ops = S._load_ops()
    for img, base in id3_images_with_base(blob, source):
        if img.label != image:
            continue
        rec = S.recover(img, ops)
        if rec.verdict != "clean":
            raise DeriveRefusal(
                "%s is a %s image (%s) -- E1 derivation needs the CLEAN-SWITCH class, where the "
                "phase spine is a state the program stores and a threshold decides"
                % (image, rec.verdict, rec.reason or "no reason given"))
        return rec.machine, base
    raise DeriveRefusal("no id-3 image named %s in this container" % image)


def analyse_target(blob: bytes, effect: int, image: str, state: int) -> Target:
    """Locate and classify every clock constant of one phase.  Refusals accumulate, never silently."""
    source = "ef%03d" % effect
    sm, base = recover_machine(blob, source, image)
    ph = next((p for p in sm.phases if p.state == state), None)
    if ph is None:
        raise DeriveRefusal("%s has no phase for state %d (its states are %s)"
                            % (image, state, [p.state for p in sm.phases]))
    case = ph.case
    trs = [t for t in case.transitions if t.threshold is not None and t.guard_reg_is_clock
           and t.guard_off is not None]
    if not trs:
        raise DeriveRefusal(
            "%s s%d has no CLOCK-GUARDED transition -- its length is not an immediate this rung can "
            "move (it is terminal, or it leaves on a signal rather than a tick count)"
            % (image, state))
    if len({t.threshold for t in trs}) != 1:
        raise DeriveRefusal("%s s%d has %d clock-guarded transitions with different thresholds %s"
                            % (image, state, len(trs), sorted({t.threshold for t in trs})))
    thr, guard_off = trs[0].threshold, trs[0].guard_off

    r = sm.walk
    jt_by_site = {jt.site: jt for jt in r.jump_tables}
    body = set(case.body)
    # the reaching-definition memo is per (walk, register) and this is the only place a new case
    # body enters, so it is emptied here rather than keyed on the body itself
    _REACH_CACHE.clear()

    # THE SOUNDNESS PRECONDITION: every instruction in the body must have a modelled destination,
    # or the kill sets in the reaching-definition pass are wrong and the peer search is worthless.
    unmodelled = sorted({r.instrs[o].entry.name for o in body
                         if r.instrs.get(o) is not None and not dest_reg(r.instrs[o])[1]})
    if unmodelled:
        raise DeriveRefusal(
            "the case body contains instruction(s) with no modelled destination register: %s. The "
            "reaching-definition pass cannot compute kill sets for them, so every peer-copy answer "
            "it gives would be unsound" % ", ".join(unmodelled))

    cell, live_in = clock_source(r, body, jt_by_site, guard_off)
    cregs = clock_registers(r, body, jt_by_site, cell, live_in)
    taint = clock_taint(r, body, jt_by_site, cell, live_in)
    gates = tuple(find_gates(r, body, jt_by_site, cregs,
                             skip=[t.guard_off for t in case.transitions
                                   if t.guard_off is not None]))
    recips, unreadable = scan_reciprocals(r, body, jt_by_site, cregs, taint)

    refusals: List[str] = []
    for off in unreadable:
        mi = r.instrs[off]
        tset = taint.get(off, frozenset())
        if not any(x in tset for x in (mi.op(T.Ex.RS), mi.op(T.Ex.RT))):
            continue
        if _product_half(r, off) == "lo":
            continue          # a plain product: `mflo` is the low word, never a division result
        lit = _literal32_operand(r, body, jt_by_site, off)
        if lit is None:
            continue          # both operands are runtime values -- a magic is always a lui/ori pair
        refusals.append(
            "a CLOCK-DERIVED multiply at image %#06x is by the 32-bit literal %#010x and does not "
            "resolve into a magic-reciprocal skeleton this walker can read. A literal that wide, "
            "multiplied into the HIGH word, is the divide idiom -- so this may be a phase-normalised "
            "ramp the scan cannot see, and a ramp missed here is a ramp left dividing by the OLD "
            "phase length, which is the silent failure this rung exists to avoid" % (off, lit))
    gvals = {g.imm for g in gates}
    for x in recips:
        _classify(x, thr, gvals)
        if x.disposition == "REFUSE":
            refusals.append("reciprocal /%d at image %#06x: %s" % (x.divisor, x.mult_off, x.reason))
            continue
        if x.disposition != "RETUNE":
            continue
        why = canonical_check(x)
        if why:
            refusals.append(why)

    # ---- the gate dispositions the tool cannot decide
    for g in gates:
        if g.imm >= thr:
            refusals.append(
                "intra-case clock gate `%s %d` at image %#06x is at or past the phase threshold %d: "
                "in stock it can never fire, after a stretch it can. KEEP-vs-RETUNE is a reading of "
                "what it drives, not a computation" % (g.kind, g.imm, g.off, thr))
    return Target(effect=effect, image=image, chunk_slot=sm and int(image.rsplit(":c", 1)[-1]),
                  state=state, image_base=base, threshold=thr, guard_off=guard_off,
                  start_tick=ph.start_tick, ticks=ph.ticks or 0, gates=gates,
                  reciprocals=tuple(recips), refusals=tuple(refusals))


def canonical_check(x: Reciprocal) -> Optional[str]:
    """A site this rung will REWRITE must be a reciprocal the compiler itself would have emitted.

    Where it is not, the site is a common-subexpression reuse -- ef227's own ``c0`` s10 divides by
    24 using the ``/3`` magic shifted three places further, which is exact and completely legitimate
    and *not* what :func:`canonical_magic` produces -- or it is hand-written.  Either way the rule
    that would pick its replacement has nothing here to be validated against, so the target is
    refused rather than rewritten on a rule this site disproves.
    """
    try:
        canon = canonical_magic(x.divisor)
    except DeriveRefusal as exc:                              # pragma: no cover - divisor < 2
        return "reciprocal /%d at image %#06x: %s" % (x.divisor, x.mult_off, exc)
    if canon == (x.magic, x.shift, x.addback):
        return None
    return ("reciprocal /%d at image %#06x holds magic %#010x shift %d %s, but the compiler's own "
            "signed-magic search for /%d gives %#010x shift %d %s. This site is not a canonical "
            "emitted reciprocal (a shared magic re-shifted for a second divisor is the usual "
            "cause), so the rule that would pick its replacement cannot be validated here"
            % (x.divisor, x.mult_off, x.magic, x.shift, "add-back" if x.addback else "plain",
               x.divisor, canon[0], canon[1], "add-back" if canon[2] else "plain"))


def _classify(x: Reciprocal, threshold: int, gvals: Set[int]) -> None:
    """B0's policy, applied to one reciprocal.  Sets ``disposition`` and ``reason`` in place."""
    if not x.tainted:
        x.disposition, x.reason = "KEEP", "its dividend is not derived from the phase clock"
        return
    if x.parent is not None:
        x.disposition = "KEEP"
        x.reason = ("its dividend is a pure function of the reciprocal at image %#06x, so it "
                    "rebases with that ramp for free (ef227's Q-domain /3 is this class)"
                    % x.parent)
        return
    if x.origin is None:
        x.disposition = "REFUSE"
        x.reason = ("its dividend is clock-derived but is not a readable linear form A*clock + B "
                    "(or its A does not divide its B), so whether its divisor is the phase length "
                    "cannot be decided from the dataflow")
        return
    if x.divisor == threshold - x.origin:
        x.disposition = "RETUNE"
        x.reason = ("its dividend is %d * (clock - %d) and it divides by %d == threshold - %d, so "
                    "it is normalised over the phase and must re-divide by the new one"
                    % (x.scale, x.origin, x.divisor, x.origin))
        return
    if x.divisor in gvals:
        x.disposition = "KEEP"
        x.reason = ("it normalises over %d ticks from origin %d, which is not the phase "
                    "(threshold - origin = %d), and %d is a clock gate immediate in the same case "
                    "body -- a self-contained sub-ramp"
                    % (x.divisor, x.origin, threshold - x.origin, x.divisor))
        return
    x.disposition = "REFUSE"
    x.reason = ("its dividend is %d * (clock - %d) but it divides by %d, which is neither the "
                "phase span %d nor any clock gate immediate in this case body %s -- the tool cannot "
                "decide whether it is a progress ramp or a rate"
                % (x.scale, x.origin, x.divisor, threshold - x.origin, sorted(gvals)))


# ============================================================ (5) the edit set
class Edit(PE.ProgramEdit):
    """Same 4-tuple contract ``retime.py`` already unpacks from :mod:`w3_program_edits`."""


def _u16(v: int) -> bytes:
    if not 0 <= v <= 0xFFFF:
        raise DeriveRefusal("value %r does not fit a u16 immediate" % (v,))
    return struct.pack("<H", v)


def canonical_magic(d: int) -> Tuple[int, int, bool]:
    """The compiler's OWN signed-division magic for ``d``: ``(stored magic, shift, needs add-back)``.

    This is the standard signed ``magic()`` search (Granlund-Montgomery; Hacker's Delight fig 10-1),
    and it is not a guess: run over every reciprocal in the clean-switch corpus it reproduces the
    shipping ``(magic, shift, add-back)`` triple at site after site -- ``/3 -> 0x55555556 s0``,
    ``/12 -> 0x2AAAAAAB s1``, ``/45 -> 0xB60B60B7 s5 add-back``, ``/66 -> 0x3E0F83E1 s4``,
    ``/69 -> 0x76B981DB s5`` -- including ef227's own two.

    The add-back bit is an OUTPUT here, not a choice: a magic that needs 33 bits is stored as
    ``M - 2**32`` and the compiler emits the ``addu`` that recovers the high half.  That is why
    :func:`pick_reciprocal` cannot simply use this value for a *new* divisor: the skeleton in the
    image is fixed, and a new divisor whose canonical magic wants the other skeleton would need an
    instruction inserted or removed.
    """
    if d < 2:
        raise DeriveRefusal("no signed reciprocal exists for /%d" % d)
    two31 = 1 << 31
    ad = d
    anc = two31 - 1 - two31 % ad
    p = 31
    q1, r1 = two31 // anc, two31 - (two31 // anc) * anc
    q2, r2 = two31 // ad, two31 - (two31 // ad) * ad
    while True:
        p += 1
        q1, r1 = q1 * 2, r1 * 2
        if r1 >= anc:
            q1, r1 = q1 + 1, r1 - anc
        q2, r2 = q2 * 2, r2 * 2
        if r2 >= ad:
            q2, r2 = q2 + 1, r2 - ad
        delta = ad - r2
        if not (q1 < delta or (q1 == delta and r1 == 0)):
            break
        if p > 96:                                            # pragma: no cover - safety
            raise DeriveRefusal("the magic search did not terminate for /%d" % d)
    m = q2 + 1
    return m & 0xFFFFFFFF, p - 32, m >= two31


def pick_reciprocal(divisor: int, addback: bool, xmax: int) -> Tuple[int, int]:
    """``(shift, stored magic)`` for a divisor UNDER A SKELETON THAT CANNOT CHANGE.

    First choice is the compiler's own answer (:func:`canonical_magic`) whenever its add-back bit
    matches the skeleton already in the image -- which is always true at ``n = 0``, and is what makes
    the identity gate pass rather than being made to pass.

    When the new divisor's canonical magic wants the *other* skeleton, fall back to
    :func:`w3_program_edits.pick_reciprocal`, which searches for a different shift that is exact
    under the skeleton we have.  That is exactly B0's move on ef227: ``/117``'s canonical magic needs
    the add-back that ``/69``'s site does not have, and ``/93``'s does not need the add-back that
    ``/45``'s site does -- so both are re-derived at a shift that keeps the instruction sequence
    intact, and the result is the shipping, cast-proven E1 set.
    """
    m, s, needs_ab = canonical_magic(divisor)
    if needs_ab == addback:
        return s, m
    return PE.pick_reciprocal(divisor, addback, xmax)


def _xmax(scale: int, span: int) -> int:
    """A dividend ceiling for the magic search: twice the ramp's own end, on its own scale.

    ``2 * A * span``.  On ef227's two phase ramps that is ``(2*117)<<12`` and ``(2*93)<<12`` -- the
    exact ceilings :mod:`w3_program_edits` uses, which is why the two agree site for site.
    """
    return max(1, 2 * abs(scale) * abs(span))


def build_edits(t: Target, blob: bytes, n: int) -> List[Edit]:
    """The E1 splice set for this target at stretch ``n`` -- every value computed, none tabulated.

    ``n = 0`` must reproduce the stock bytes; :func:`assert_identity` is what enforces that, and
    :func:`derive` calls it before returning anything.
    """
    if not t.derivable:
        raise DeriveRefusal("this target is refused:\n  - " + "\n  - ".join(t.refusals))
    new_thr = t.threshold + n
    if new_thr <= t.max_gate:
        raise DeriveRefusal(
            "N = %+d puts the threshold at %d, at or below the largest intra-case clock gate %d. "
            "B0's floor, generalised: a phase cannot shrink past its own sub-phase boundaries"
            % (n, new_thr, t.max_gate))
    if new_thr < 1:
        raise DeriveRefusal("N = %+d puts the threshold at %d" % (n, new_thr))

    out: List[Edit] = []
    out.append(Edit(t.guard_file_off, 2, _u16(new_thr),
                    "E1a THRESHOLD: the phase guard's slti immediate %d -> %d at image %#06x -- "
                    "s%d now lasts %d ticks (clock 0..%d)"
                    % (t.threshold, new_thr, t.guard_off, t.state, new_thr + 1, new_thr)))
    for x in t.retuned:
        span = new_thr - x.origin
        if span < 1:
            raise DeriveRefusal("the ramp at image %#06x would span %d ticks" % (x.mult_off, span))
        try:
            sh, magic = pick_reciprocal(span, x.addback, _xmax(x.scale, span))
        except ValueError as exc:
            raise DeriveRefusal("no %s magic exists for /%d under the skeleton at image %#06x: %s"
                                % ("add-back" if x.addback else "plain", span, x.mult_off, exc))
        for off in x.lui_offs:
            out.append(Edit(t.image_base + off, 2, _u16(magic >> 16),
                            "E1 RAMP hi: lui at image %#06x -> /%d magic 0x%08X (shift %d, %s)%s"
                            % (off, span, magic, sh,
                               "add-back" if x.addback else "no add-back",
                               "" if len(x.lui_offs) == 1 else
                               "  [PEER COPY %d of %d -- both must agree]"
                               % (x.lui_offs.index(off) + 1, len(x.lui_offs)))))
        for off in x.ori_offs:
            out.append(Edit(t.image_base + off, 2, _u16(magic & 0xFFFF),
                            "E1 RAMP lo: ori at image %#06x -> /%d magic low half" % (off, span)))
        if sh != x.shift:
            if x.sra_off is None:
                raise DeriveRefusal(
                    "the reciprocal at image %#06x needs shift %d -> %d but has NO shift "
                    "instruction (it is the shift-0 form); the skeleton would have to grow an "
                    "instruction, which this rung does not do" % (x.mult_off, x.shift, sh))
            word = struct.unpack_from("<I", blob, t.image_base + x.sra_off)[0]
            new_word = (word & ~(0x1F << 6)) | ((sh & 0x1F) << 6)
            out.append(Edit(t.image_base + x.sra_off, 2, _u16(new_word & 0xFFFF),
                            "E1 RAMP shift: the shift instruction at image %#06x, shamt %d -> %d "
                            "(read from the LIVE word; rt/rd/funct untouched)"
                            % (x.sra_off, x.shift, sh)))
    seen: Dict[int, str] = {}
    for off, ln, nb, why in out:
        for i in range(ln):
            if off + i in seen:
                raise DeriveRefusal(
                    "TWO retuned ramps want to rewrite the same byte at file %#x (image %#06x): "
                    "%s and %s. A `lui`/`ori` shared by two reciprocals cannot carry two different "
                    "new magics, and choosing one would silently leave the other dividing by the "
                    "old phase length -- so this refuses rather than picking"
                    % (off + i, off + i - t.image_base, seen[off + i], why.split(":")[0]))
            seen[off + i] = why.split(":")[0]
    return out


def assert_identity(t: Target, blob: bytes) -> List[Edit]:
    """THE MANDATORY SELF-GATE: ``build_edits(0)`` must be byte-identical to what is already there.

    If the selection rule cannot reproduce this target's own shipping constants it is fitting, not
    reading, and nothing it computes for a non-zero N can be trusted.
    """
    edits = build_edits(t, blob, 0)
    bad = []
    for off, ln, nb, why in edits:
        got = bytes(blob[off:off + ln])
        if got != nb:
            bad.append("file %#x (image %#06x): stock %s, derived %s  [%s]"
                       % (off, off - t.image_base, got[::-1].hex().upper(),
                          nb[::-1].hex().upper(), why.split(":")[0]))
    if bad:
        raise DeriveRefusal(
            "THE N=0 IDENTITY GATE FAILED for %s s%d -- the derivation does not reproduce this "
            "target's own stock constants at %d of %d sites:\n  - %s"
            % (t.image, t.state, len(bad), len(edits), "\n  - ".join(bad)))
    return edits


# ============================================================ (6) the endpoint proof
@dataclass(frozen=True)
class Endpoint:
    ok: bool
    what: str
    detail: str

    def __str__(self) -> str:
        return "[%s] %-46s %s" % ("PASS" if self.ok else "FAIL", self.what, self.detail)


def endpoint_checks(t: Target, n: int) -> List[Endpoint]:
    """The portable substitute for ``w3_clock_emu``: arithmetic endpoints, monotonicity, sign.

    What this proves: each retuned ramp still lands on its stock terminal value on the phase's NEW
    last tick, rises without going backwards, and never goes negative.  What it does NOT prove, and
    what ef227 got from a per-tick emulator instead: one-shot re-fires, saturation steps, gate-local
    ramps and beam completion.  A target derived here is retimed on a strictly thinner proof.
    """
    out: List[Endpoint] = []
    new_thr = t.threshold + n
    for x in t.retuned:
        stock_span, new_span = t.threshold - x.origin, new_thr - x.origin
        unit = x.scale
        s_sh, s_m = x.shift, x.magic
        n_sh, n_m = pick_reciprocal(new_span, x.addback, _xmax(x.scale, new_span))
        got_stock = PE.magic_div(x.scale * stock_span, s_m, s_sh, x.addback)
        out.append(Endpoint(got_stock == unit,
                            "/%d STOCK lands on %d at clock %d" % (x.divisor, unit, t.threshold),
                            "magic_div(%d * (%d - %d)) = %d"
                            % (x.scale, t.threshold, x.origin, got_stock)))
        got_new = PE.magic_div(x.scale * new_span, n_m, n_sh, x.addback)
        out.append(Endpoint(got_new == unit,
                            "/%d RETUNED lands on %d at clock %d" % (new_span, unit, new_thr),
                            "magic_div(%d * (%d - %d)) = %d"
                            % (x.scale, new_thr, x.origin, got_new)))
        vals = [PE.magic_div(x.scale * max(0, k - x.origin), n_m, n_sh, x.addback)
                for k in range(0, new_thr + 1)]
        out.append(Endpoint(all(b >= a for a, b in zip(vals, vals[1:])),
                            "/%d RETUNED is monotone over the phase" % new_span,
                            "%d ticks, %d -> %d" % (len(vals), vals[0], vals[-1])))
        out.append(Endpoint(all(v >= 0 for v in vals),
                            "/%d RETUNED never goes negative" % new_span,
                            "min %d" % min(vals)))
    if not t.retuned:
        out.append(Endpoint(True, "no phase-coupled ramp in this phase",
                            "the threshold moves alone; nothing normalises over the phase length"))
    return out


# ============================================================ (7) the whole derivation
@dataclass
class Derivation:
    target: Target
    n: int
    edits: List[Edit]
    identity: List[Edit]
    endpoints: List[Endpoint]

    @property
    def ok(self) -> bool:
        return all(e.ok for e in self.endpoints)

    @property
    def changed_bytes(self) -> int:
        return len(self.edits) * 2


def derive(blob: bytes, effect: int, image: str, state: int, n: int) -> Derivation:
    """Analyse, self-gate at N=0, build at N, and prove the endpoints -- or refuse, by name."""
    t = analyse_target(blob, effect, image, state)
    if not t.derivable:
        raise DeriveRefusal("%s s%d is NOT auto-derivable:\n  - %s"
                            % (image, state, "\n  - ".join(t.refusals)))
    identity = assert_identity(t, blob)
    edits = build_edits(t, blob, n)
    eps = endpoint_checks(t, n)
    bad = [e for e in eps if not e.ok]
    if bad:
        raise DeriveRefusal("the arithmetic endpoint proof failed for %s s%d:\n  - %s"
                            % (image, state, "\n  - ".join(str(e) for e in bad)))
    return Derivation(t, n, edits, identity, eps)


def apply_edits(blob: bytes, edits: Sequence[Edit]) -> bytes:
    """Splice a derived edit set into a COPY.  Same length in, same length out, or it raises."""
    out = bytearray(blob)
    seen: Set[int] = set()
    for off, ln, nb, why in edits:
        if len(nb) != ln:
            raise DeriveRefusal("edit at %#x is not same-length" % off)
        if off < 0 or off + ln > len(out):
            raise DeriveRefusal("edit at %#x is outside the container" % off)
        for i in range(ln):
            if off + i in seen:
                raise DeriveRefusal("two edits write byte %#x" % (off + i))
            seen.add(off + i)
        out[off:off + ln] = nb
    if len(out) != len(blob):                                 # pragma: no cover
        raise DeriveRefusal("length changed")
    return bytes(out)


# ============================================================ (8) reporting / CLI
def describe(t: Target) -> List[str]:
    L = ["%s s%d   threshold %d (clock 0..%d, %d ticks)  starts at program tick %d"
         % (t.image, t.state, t.threshold, t.threshold, t.ticks, t.start_tick),
         "  image file base : %#08x   guard slti at image %#06x = file %#08x"
         % (t.image_base, t.guard_off, t.guard_file_off),
         "  intra-case clock gates: %s"
         % (", ".join("%s %d @%#06x" % (g.kind, g.imm, g.off) for g in t.gates) or "(none)"),
         "  reciprocals: %d (%d with a peer copy)" % (len(t.reciprocals), t.peer_count)]
    for x in t.reciprocals:
        L.append("    /%-5d sh=%-2d %-11s dividend=%s  %-7s %s"
                 % (x.divisor, x.shift, "add-back" if x.addback else "plain", x.form,
                    x.disposition, x.reason))
        L.append("        lui %s   ori %s   %s"
                 % (", ".join("%#06x" % o for o in x.lui_offs),
                    ", ".join("%#06x" % o for o in x.ori_offs),
                    ("sra %#06x" % x.sra_off) if x.sra_off is not None else "shift-0 form"))
    if t.refusals:
        L.append("  REFUSED:")
        L += ["    - " + x for x in t.refusals]
    else:
        L.append("  DERIVABLE: threshold + %d retuned ramp(s), %d kept"
                 % (len(t.retuned), len(t.reciprocals) - len(t.retuned)))
    return L


def corpus_targets(root: str = None) -> List[Tuple[int, str, int]]:
    """Every clock-guarded phase of every clean-switch image in the corpus."""
    import glob
    root = root or getattr(__import__("summon_camera"), "SCRATCH_CORPUS")
    ops = S._load_ops()
    out = []
    for p in sorted(glob.glob(os.path.join(root, "ef*.bytes"))):
        src = os.path.splitext(os.path.basename(p))[0]
        try:
            ef = int(src[2:])
        except ValueError:                                    # pragma: no cover
            continue
        with open(p, "rb") as fh:
            blob = fh.read()
        try:
            imgs = T.id3_images(blob, src)
        except Exception:                                     # pragma: no cover
            continue
        for img in imgs:
            try:
                rec = S.recover(img, ops)
            except Exception:                                 # pragma: no cover
                continue
            if rec.verdict != "clean" or rec.machine is None:
                continue
            for ph in rec.machine.phases:
                if any(t.threshold is not None and t.guard_reg_is_clock
                       for t in ph.case.transitions):
                    out.append((ef, img.label, ph.state))
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:                # pragma: no cover
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("image", nargs="?", help="e.g. ef211:c0")
    ap.add_argument("state", nargs="?", type=int)
    ap.add_argument("--ticks", type=int, default=None)
    ap.add_argument("--corpus", action="store_true")
    ap.add_argument("--root", default=None)
    a = ap.parse_args(argv)
    import summon_camera as W
    root = a.root or W.SCRATCH_CORPUS

    def read(ef: int) -> bytes:
        p = os.path.join(root, "ef%03d.bytes" % ef)
        with open(p, "rb") as fh:
            return fh.read()

    if a.corpus:
        rows = corpus_targets(root)
        ok = ref = 0
        blobs: Dict[int, bytes] = {}
        for ef, image, state in rows:
            blobs.setdefault(ef, read(ef))
            try:
                t = analyse_target(blobs[ef], ef, image, state)
                if t.derivable:
                    assert_identity(t, blobs[ef])
                    ok += 1
                    print("DERIVABLE  %-12s s%-3d thr=%-4d retune=%d keep=%d peers=%d"
                          % (image, state, t.threshold, len(t.retuned),
                             len(t.reciprocals) - len(t.retuned), t.peer_count))
                else:
                    ref += 1
                    print("refused    %-12s s%-3d %s" % (image, state, t.refusals[0][:110]))
            except DeriveRefusal as exc:
                ref += 1
                print("refused    %-12s s%-3d %s" % (image, state, str(exc).splitlines()[0][:110]))
        print("\n%d clock-guarded phases: %d DERIVABLE, %d refused" % (len(rows), ok, ref))
        return 0
    if not a.image or a.state is None:
        ap.error("give an image and a state, or --corpus")
    ef = int(a.image.split(":")[0][2:])
    blob = read(ef)
    t = analyse_target(blob, ef, a.image, a.state)
    print("\n".join(describe(t)))
    if a.ticks is not None and t.derivable:
        d = derive(blob, ef, a.image, a.state, a.ticks)
        print("\n  N = %+d -> %d sites, %d bytes" % (a.ticks, len(d.edits), d.changed_bytes))
        for off, ln, nb, why in d.edits:
            print("    file %#08x (image %#06x)  %s" % (off, off - t.image_base, why))
        print("\n  THE N=0 IDENTITY GATE: %d sites reproduce stock byte-for-byte" % len(d.identity))
        print("  ENDPOINTS")
        for e in d.endpoints:
            print("    %s" % e)
    return 0


if __name__ == "__main__":                                     # pragma: no cover
    raise SystemExit(main())
