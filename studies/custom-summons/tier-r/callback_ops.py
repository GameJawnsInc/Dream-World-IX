"""callback_ops -- THE CALLBACK-CODE EVIDENCE CLASS for naming HLE ops.

R2 named 79 of the 216 HLE ops and stopped, because its four static evidence sources ran dry:
a debug string the DLL owns (32 ops), a thin CRT wrapper (2), a return-tail no-op (8), and a
discriminating global touch-set (37).  Two globals were explicitly excluded from that last source
as too broad to prove anything -- ``tier_r_annot.DIFFUSE_GLOBALS`` --

    0x1C1DE8  vramUploadCallback   the host callback slot
    0x576A10  psxBankTable         the host<->PSX address bank table

**and that exclusion is what left 39 VRAM-cluster ops anonymous.**  The exclusion is right about the
TOUCH and wrong about what rides it.  Reaching the callback slot proves nothing -- 166 xref sites
across the DLL reach it.  But every call through it passes a *command code* in ``ecx``, and that code
is fully discriminating, because the managed side of the boundary is OPEN SOURCE and carries Square's
own symbol for each one:

    SFX.BattleCallback(Int32 fullCode, arg0..arg3, void* p)      Memoria SFX.cs:833
    code = fullCode >> 24 ; btlid = fullCode & 255               SFX.cs:839, :958
    enum SFX.COMMAND { COMMAND_LOAD_IMAGE = 100, ... }           SFX.cs:2330-2384

So an op whose native function issues ``mov ecx, 0x64000000 ; call [vramUploadCallback]`` **is**
``COMMAND_LOAD_IMAGE``, named by the shipping game's own enumerator rather than by our inference.
That is a stronger source than the DLL's leftover assert strings, not a weaker one -- it is the other
side of the same ABI, with names, in source we can read.

THE FUNCTION MODEL IS THE TRAP, AND IT ALREADY BIT ONCE.  MSVC splits one function across several
``.pdata`` RUNTIME_FUNCTION chunks; a chunk carrying ``UNW_FLAG_CHAININFO`` names its primary.
``A1-TEXTURES.md`` §5.2 published the LoadImage issuer set as ``{0x2cd0, 0x31060, 0x312d0, 0x315f1,
0x3dc85, 0x3de37}`` -- but ``0x3dc85`` is a *chained chunk* of primary ``0x3dc50`` (the page streamer
A1 itself names two sections earlier).  Attribute by chunk begin and the same function answers to two
addresses; attribute by nearest preceding row and neighbours merge.  This module reuses
``tier_r_annot.DllView``, whose function model is UNWIND-exact and already gated, and the calibration
below asserts the reconciliation rather than quietly accepting a near-miss.

Provenance: pure parser.  Reads the user's own installed DLL and Memoria's open source at runtime,
emits names/RVAs/statistics.  Zero stock bytes.  Never writes to the install.

    py studies/custom-summons/tier-r/callback_ops.py --calibrate   # the A1 reproduction gate
    py studies/custom-summons/tier-r/callback_ops.py --sweep       # op -> command code
    py studies/custom-summons/tier-r/callback_ops.py --cluster     # the VRAM/bank cluster report
"""
from __future__ import annotations

import argparse
import bisect
import collections
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import tier_r_annot as A


# ===========================================================================  the managed authority
#: Memoria ``Assembly-CSharp/Global/SFX/SFX.cs``.  The clone is gitignored and shared between
#: worktrees (CLAUDE.md §3), so the path is overridable and its absence is a stated skip, never a
#: silent fallback to a hardcoded copy of the enum.
MEMORIA_SRC = os.environ.get("FF9_MEMORIA_SRC", r"C:\gd\FFIX\Memoria")
SFX_CS = os.path.join(MEMORIA_SRC, "Assembly-CSharp", "Global", "SFX", "SFX.cs")

CALLBACK_GLOBAL = 0x1C1DE8

_ENUM_HEAD = re.compile(r"\benum\s+COMMAND\b")
_ENUM_ROW = re.compile(r"^\s*COMMAND_([A-Z0-9_]+)\s*=\s*(\d+)\s*,?\s*$")


def load_commands(path: str = SFX_CS) -> Dict[int, str]:
    """Parse ``SFX.COMMAND`` out of Memoria's source.

    Parsed, never transcribed: a hardcoded copy of an enum in another repo is a fact with no owner,
    and this one is the whole naming authority.  Raises if the source is unavailable -- the caller
    decides whether that is a skip, so no code path can silently name an op from a stale copy.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    out: Dict[int, str] = {}
    inside = False
    for ln in lines:
        if not inside:
            if _ENUM_HEAD.search(ln):
                inside = True
            continue
        if "}" in ln:
            break
        m = _ENUM_ROW.match(ln)
        if m:
            out[int(m.group(2))] = m.group(1)
    if not out:
        raise RuntimeError("SFX.COMMAND parsed to zero rows at %s" % path)
    return out


#: A ``case N:`` at the switch's own indentation inside ``BattleCallback`` /
#: ``BattleCallbackWithBtl``.  Nested selector switches (``switch (arg0)``) sit deeper and must NOT
#: be read as command codes -- ``case 0:`` under ``case 1: // Get Position`` is a sub-mode, not
#: ``COMMAND`` zero.  Anchoring on the exact 12-space indent is what separates them.
_CASE_TOP = re.compile(r"^ {12}case (\d+):")
_CASE_ANY = re.compile(r"^ *case (\d+):")
_ARGN = re.compile(r"\barg([0-3])\b")
_RET_VAL = re.compile(r"^\s*return\s+(?!0\s*;)(.+);")


@dataclass
class ManagedSig:
    """What Memoria's own handler for a command code consumes and produces."""
    code: int
    args: Set[int] = field(default_factory=set)   # which of arg0..arg3 the case body reads
    uses_p: bool = False                          # writes/reads through the void* out-parameter
    returns_value: bool = False                   # `return <expr>` other than the shared 0
    submodes: Dict[int, str] = field(default_factory=dict)   # nested `switch (arg0)` -> its comment


def managed_signatures(path: str = SFX_CS) -> Dict[int, ManagedSig]:
    """Parse each ``COMMAND`` case body out of Memoria's two callback switches.

    This is the round's CROSS-CHECK, and it is independent of the DLL by construction: it reads the
    other side of the ABI, in a different language, written by different people.  A name that the
    disassembly asserts and this contradicts is a name that does not ship.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    # Bound the parse to the two BATTLE callback bodies.  Other switches in this file sit at the
    # same indentation (they parsed as bogus "commands" 0/73/83 before this bound existed), and
    # `DebugRoomCallback` is a separate debug-room dispatcher for the same codes -- folding it in
    # would attribute debug-only behaviour to the battle path a summon actually runs.
    spans: List[Tuple[int, int]] = []
    for i, ln in enumerate(lines):
        if re.search(r"Int32 BattleCallback(WithBtl)?\(", ln):
            j = i + 1
            while j < len(lines) and not re.match(r"^    (public|private|internal) ", lines[j]):
                j += 1
            spans.append((i, j))
    if not spans:
        raise RuntimeError("neither battle callback body found at %s" % path)
    body = [ln for a, b in spans for ln in lines[a:b]]

    out: Dict[int, ManagedSig] = {}
    cur: Optional[ManagedSig] = None
    sub: Optional[int] = None
    for ln in body:
        # `case 100` is not a case at all -- LOAD_IMAGE is an `if (code == 100)` FAST PATH ahead of
        # the switch (SFX.cs:840).  Missing it reported "no managed case parsed" against the single
        # best-attested name in the round, which is how this branch got found.
        mf = re.match(r"^\s*if \(code == (\d+)\)", ln)
        if mf:
            cur, sub = out.setdefault(int(mf.group(1)),
                                      ManagedSig(code=int(mf.group(1)))), None
            continue
        m = _CASE_TOP.match(ln)
        if m:
            code = int(m.group(1))
            cur, sub = out.setdefault(code, ManagedSig(code=code)), None
            continue
        if cur is None:
            continue
        # The switch's own closing brace sits at 8 spaces; anything shallower ends the body.  A
        # prefix test on "    }" does NOT match "        }", so the old terminator ran past the end
        # of the switch and swallowed the trailing `return BattleCallbackWithBtl(... p ...)` into
        # whichever case happened to be last -- inventing both a `p` use and a return for SET_FPS.
        stripped = ln.strip()
        if stripped and (len(ln) - len(ln.lstrip())) <= 8 and stripped.startswith("}"):
            cur = None
            continue
        ms = _CASE_ANY.match(ln)
        if ms and not _CASE_TOP.match(ln):
            sub = int(ms.group(1))
            note = ln.split("//", 1)[1].strip() if "//" in ln else ""
            cur.submodes.setdefault(sub, note)
            continue
        for a in _ARGN.findall(ln):
            cur.args.add(int(a))
        if re.search(r"(?<![A-Za-z_])p(?![A-Za-z_0-9])", ln):
            cur.uses_p = True
        if _RET_VAL.match(ln):
            cur.returns_value = True
    return out


# ===========================================================================  the code extractor
@dataclass
class CallSite:
    fn: int                     # UNWIND-exact primary
    chunk: int                  # the .pdata RUNTIME_FUNCTION row containing the call
    at: int                     # the `call` itself
    code: Optional[int]         # the COMMAND code, or None when the code byte never resolved
    raw: Optional[int]          # the code byte as staged (may be a non-COMMAND value)
    form: Optional[str] = None  # which encoding installed it: mov / or / bts / xor / movzx
    arg0: Optional[int] = None  # the sub-mode, when edx is staged as a constant at the site


#: ``ecx`` is the Win64 ABI's first argument -- the callback's ``fullCode``.
_ECX_IMM = re.compile(r"^(?:e|r)cx, (0x[0-9a-f]+|\d+)$")
#: ``movzx ecx, word|byte ptr [...]`` -- a zero-extending load, so bits 16..31 are PROVABLY 0.
_ECX_MOVZX = re.compile(r"^(?:e|r)cx, (?:word|byte) ptr ")
#: ``bts ecx, N`` -- MSVC's one-byte way to set a single high bit.
_ECX_BTS = re.compile(r"^(?:e|r)cx, (0x[0-9a-f]+|\d+)$")
#: ``edx`` is the callback's ``arg0`` -- several commands multiplex on it (code 14 GET_MATRIX has
#: three sub-modes), so two ops can share a code and differ only here.
_EDX_IMM = re.compile(r"^(?:e|r)dx, (0x[0-9a-f]+|\d+)$")
_CLOBBER_DX = re.compile(r"^(?:e|r)dx")
_LOAD_RIP = re.compile(r"^(\w+), qword ptr \[rip ([+-]) 0x([0-9a-f]+)\]")
_CLOBBER = re.compile(r"^(?:e|r)cx\b")


class CallbackMap:
    """Every function that calls through the host callback slot, with the codes it passes.

    THE COMMAND WORD HAS THREE ENCODINGS, and a scan that models one is not conservative, it is
    WRONG -- it silently drops sites rather than reporting them (measured: ``mov`` 144, ``or`` 53,
    ``bts`` 7 of 204, so a mov-only scan sees 70% and loses the very ``LoadImage`` site
    ``A1-TEXTURES`` published).  MSVC picks whichever is cheapest:

        mov  ecx, 0x64000000                    the code alone, btlid 0
        movzx ecx, word ptr [rbx + 0x18]        the btlid ...
        or   ecx, 0x16000000                    ... then the code OR'd over it
        bts  ecx, 0x19                          ... or a single bit set (1 << 25 == code 2)

    The ``or``/``bts`` forms are EXACT rather than inferred because of the instruction in front of
    them: ``movzx`` from a word zero-extends, so bits 16..31 are provably clear and the OR/BTS *is*
    the whole code.  That is why the tracker follows the code byte specifically, not the register.

    Everything else stays conservative, because a wrong code here becomes a wrong NAME downstream
    and this project's record says a hedged description is cheap while a confident wrong name is a
    defect (R2 §4):

    * any write to ``ecx`` that is not one of the four modelled forms leaves the site ``code=None``
      (UNRESOLVED) rather than inheriting whatever value happened to precede it;
    * a nested ``call`` CLEARS the tracked value.  ``ecx`` is caller-saved on Win64, so an immediate
      staged before an intervening call is not evidence about the one after it;
    * only values that are real ``SFX.COMMAND`` members count.  The page streamer's own
      ``mov ecx, 0x40`` (a loop bound at ``0x3dc63``) is exactly the accident this rejects.
    """

    def __init__(self, dll: Optional[A.DllView] = None, commands: Optional[Dict[int, str]] = None):
        self.dll = dll or A.DllView()
        self.commands = commands if commands is not None else load_commands()
        self.sites: List[CallSite] = []
        self._by_fn: Dict[int, Set[Optional[int]]] = collections.defaultdict(set)
        self._scan()

    # -- the scan ---------------------------------------------------------
    def _holder_functions(self) -> List[int]:
        rk = self.dll.refkit
        xi = rk.xref_index(self.dll.pe, CALLBACK_GLOBAL, CALLBACK_GLOBAL + 8,
                           rk.functions(self.dll.pe))
        out: Set[int] = set()
        for lst in xi.values():
            for frm, _mn, _ops in lst:
                fn = self.dll.function_of(frm)
                if fn is not None:
                    out.add(fn)
        return sorted(out)

    def _scan(self) -> None:
        base = self.dll.base
        for fn in self._holder_functions():
            ecx: Optional[int] = None      # the CODE byte (bits 24..31), not the whole word
            form: Optional[str] = None
            edx: Optional[int] = None      # the callback's arg0
            cbregs: Set[str] = set()
            prev_end: Optional[int] = None
            chunks = sorted(self.dll._chunks.get(fn, ())) or [(fn, fn + 0x400)]
            for chunk, cend in chunks:
                # MSVC chunks of one function need not be adjacent.  An ADJACENT chunk is
                # straight-line continuation -- the page streamer `0x3dc50` loads the callback
                # pointer into r10 at `0x3dc7e` and calls it inside the next chunk, and resetting
                # there loses the LoadImage site A1 published.  A non-adjacent chunk is reached by a
                # branch from somewhere unmodelled, so its inherited state is not evidence.
                if prev_end != chunk:
                    ecx, form, edx, cbregs = None, None, None, set()
                prev_end = cend
                for ins in self.dll.refkit.disasm(self.dll.pe, chunk, cend):
                    mn, ops = ins.mnemonic, ins.op_str
                    if mn == "mov":
                        m = _LOAD_RIP.match(ops)
                        if m:
                            disp = int(m.group(3), 16) * (1 if m.group(2) == "+" else -1)
                            tgt = (ins.address - base) + ins.size + disp
                            if tgt == CALLBACK_GLOBAL:
                                cbregs.add(m.group(1))
                            else:
                                cbregs.discard(m.group(1))
                            continue
                        m = _ECX_IMM.match(ops)
                        if m:
                            hi = (int(m.group(1), 0) >> 24) & 0xFF
                            ecx, form = hi, "mov"
                            continue
                        m = _EDX_IMM.match(ops)
                        if m:
                            edx = int(m.group(1), 0)
                            continue
                        if _CLOBBER.match(ops):    # ecx written from anything but an immediate
                            ecx, form = None, None
                            continue
                        if _CLOBBER_DX.match(ops):
                            edx = None
                            continue
                    elif mn == "movzx":
                        # A zero-extending load of a word/byte leaves bits 16..31 CLEAR.  That is
                        # what makes the `or`/`bts` forms below exact rather than inferred: the code
                        # bits are known to start at zero, so the OR/BTS *is* the whole code.
                        if _ECX_MOVZX.match(ops):
                            ecx, form = 0, "movzx"
                        elif _CLOBBER.match(ops):
                            ecx, form = None, None
                        continue
                    elif mn == "or":
                        m = _ECX_IMM.match(ops)
                        if m and ecx is not None:
                            ecx |= (int(m.group(1), 0) >> 24) & 0xFF
                            form = "or"
                            continue
                        if _CLOBBER.match(ops):
                            ecx, form = None, None
                            continue
                    elif mn == "bts":
                        m = _ECX_BTS.match(ops)
                        if m and ecx is not None:
                            bit = int(m.group(1), 0)
                            if bit >= 24:
                                ecx |= 1 << (bit - 24)
                                form = "bts"
                                continue
                        if _CLOBBER.match(ops):
                            ecx, form = None, None
                            continue
                    elif mn in ("xor", "and", "add", "sub", "lea", "movsx", "movsxd",
                                "shl", "shr", "sar", "imul", "inc", "dec"):
                        if mn == "xor" and ops in ("ecx, ecx", "rcx, rcx"):
                            ecx, form = 0, "xor"
                        elif _CLOBBER.match(ops):
                            ecx, form = None, None
                        if mn == "xor" and ops in ("edx, edx", "rdx, rdx"):
                            edx = 0
                        elif _CLOBBER_DX.match(ops):
                            edx = None
                        continue
                    elif mn == "call":
                        if ops in cbregs:
                            code = ecx if (ecx is not None and ecx in self.commands) else None
                            self.sites.append(CallSite(fn=fn, chunk=chunk, at=ins.address - base,
                                                       code=code, raw=ecx, form=form, arg0=edx))
                            self._by_fn[fn].add(code)
                        ecx, form, edx = None, None, None   # caller-saved across every call
                        continue
        return

    # -- queries -----------------------------------------------------------
    def codes_of(self, fn: int) -> Set[Optional[int]]:
        return set(self._by_fn.get(fn, ()))

    @property
    def holders(self) -> List[int]:
        return sorted(self._by_fn)

    def issuers(self, code: int) -> Set[int]:
        return {fn for fn, cs in self._by_fn.items() if code in cs}


# ===========================================================================  op -> code
@dataclass
class OpVerdict:
    op: int
    codes: Set[int] = field(default_factory=set)
    unresolved: bool = False
    via: Tuple[int, ...] = ()          # the callback-holding functions reached
    depth: Optional[int] = None        # hops from the op's own native function
    name: Optional[str] = None
    confidence: Optional[str] = None
    reason: str = ""


#: How far to chase callees from an op's native function.  ``DllView.profile`` uses 2 for globals;
#: the same bound is kept here so the two evidence lanes see the same neighbourhood, and the depth
#: that produced each verdict is REPORTED so a deep hit can be discounted by a reader.
REACH_DEPTH = 2


class OpNamer:
    def __init__(self, cbmap: Optional[CallbackMap] = None):
        self.cb = cbmap or CallbackMap()
        self.dll = self.cb.dll
        self.commands = self.cb.commands

    def _reach(self, fn: int, depth: int) -> Dict[int, int]:
        """{callback-holding fn: hops} within ``depth`` call levels of ``fn``."""
        hits: Dict[int, int] = {}
        seen: Set[int] = set()
        frontier = [(fn, 0)]
        while frontier:
            cur, d = frontier.pop()
            if cur in seen or d > depth:
                continue
            seen.add(cur)
            if cur in self.cb._by_fn:
                hits[cur] = min(hits.get(cur, 99), d)
            calls, _globs, _crt = self.dll._shallow(cur)
            if d < depth:
                for t in calls:
                    frontier.append((self.dll.function_of(t) or t, d + 1))
        return hits

    def verdict(self, op: int) -> OpVerdict:
        sig = self.dll.handler(op)
        v = OpVerdict(op=op)
        if sig.noop:
            v.reason = "the jump-table slot is the return tail -- the op executes nothing"
            return v
        roots = []
        fn = self.dll.function_of(self.dll.native_fn[op]) or self.dll.native_fn[op]
        if fn:
            roots.append(fn)
        if not sig.fn_confirmed:
            # the stub inlines its work instead of calling the table's function (R2 finding 5)
            roots.extend(self.dll.function_of(t) or t for t in sig.calls)
        hits: Dict[int, int] = {}
        for r in roots:
            for h, d in self._reach(r, REACH_DEPTH).items():
                hits[h] = min(hits.get(h, 99), d)
        if not hits:
            v.reason = "does not reach the callback slot"
            return v
        v.via = tuple(sorted(hits))
        v.depth = min(hits.values())
        codes: Set[int] = set()
        for h in hits:
            for c in self.cb.codes_of(h):
                if c is None:
                    v.unresolved = True
                else:
                    codes.add(c)
        v.codes = codes
        if len(codes) == 1 and not v.unresolved:
            code = next(iter(codes))
            v.name = "COMMAND_" + self.commands[code]
            v.confidence = "high" if v.depth == 0 else "medium"
            v.reason = ("issues exactly one callback command, code %d, at depth %d"
                        % (code, v.depth))
        elif len(codes) > 1:
            v.reason = ("reaches %d distinct callback commands (%s) -- a dispatcher, not one op"
                        % (len(codes), ", ".join(str(c) for c in sorted(codes))))
        elif v.unresolved:
            v.reason = "reaches the callback with a computed code -- UNRESOLVED"
        return v

    def sweep(self) -> Dict[int, OpVerdict]:
        return {op: self.verdict(op) for op in range(A.T.HLE_OP_COUNT)}


# ===========================================================================  the calibration gate
#: ``A1-TEXTURES.md`` §5.2's published issuer table, verbatim, as CHUNK addresses.  It was derived
#: independently (a direct-call graph over all 646 functions, before this module existed), which is
#: what makes it a control rather than a restatement.
A1_ISSUERS = {
    100: {0x2CD0, 0x31060, 0x312D0, 0x315F1, 0x3DC85, 0x3DE37},
    101: {0x2D20, 0x31D31, 0x31F03},
    102: {0x2FE0},
}

#: A1's addresses are ``.pdata`` CHUNK begins, and four of the ten chain into a larger primary.
#: The map is DERIVED from the DLL, never transcribed -- and the direction of the loss is the point:
#: at primary granularity ``0x31520`` issues LOAD_IMAGE *and* STORE_IMAGE, so the primary is COARSER
#: than A1's model, not finer.  Calibrating on primaries would therefore hide a real disagreement.
#: The gate runs on CHUNKS, which is the unit that actually locates a call site.


def chunk_reconciliation(cb: CallbackMap) -> Dict[int, int]:
    """{A1 chunk address: its UNWIND primary} for every address A1 published."""
    return {a: (cb.dll.function_of(a) or a)
            for s in A1_ISSUERS.values() for a in s}


def calibrate(namer: Optional[OpNamer] = None) -> Tuple[bool, List[str]]:
    """Reproduce A1's independently-derived issuer table, site by site.

    A1 built its table from a direct-call graph over all 646 functions, months before this module
    existed and by a different method.  Reproducing it exactly is what licenses the sweep; anything
    less is this project's "a gate can be green and wrong in the same number" failure.
    """
    namer = namer or OpNamer()
    cb = namer.cb
    lines: List[str] = []
    ok = True

    recon = chunk_reconciliation(cb)
    chained = {a: p for a, p in recon.items() if a != p}
    lines.append("  chunk -> primary reconciliation: %d of %d A1 addresses are chained chunks"
                 % (len(chained), len(recon)))
    for a, p in sorted(chained.items()):
        lines.append("      %#x -> %#x" % (a, p))

    by_code: Dict[int, Set[int]] = collections.defaultdict(set)
    for s in cb.sites:
        if s.code is not None:
            by_code[s.code].add(s.chunk)

    for code in sorted(A1_ISSUERS):
        expect = A1_ISSUERS[code]
        got = by_code.get(code, set())
        good = got == expect
        ok &= good
        lines.append("  code %3d %-12s expect %s" % (code, namer.commands.get(code, "?"),
                                                     " ".join("%#x" % x for x in sorted(expect))))
        lines.append("      %-21s got    %s   %s"
                     % ("", " ".join("%#x" % x for x in sorted(got)), "OK" if good else "FAIL"))
    return ok, lines


# ===========================================================================  the cross-check
@dataclass
class CrossCheck:
    op: int
    verdict: str                 # "AGREE" | "FLAG"
    note: str = ""


def crosscheck(op: int, v: OpVerdict, sig: A.HandlerSig,
               msigs: Dict[int, ManagedSig]) -> CrossCheck:
    """Test a callback-derived name against the managed handler's own shape.

    The two sides are independent: the name comes from the DLL's ``ecx`` immediate, the shape from
    C# in another repository.  Three contradictions are checked, and each is a real disagreement
    rather than a style note:

    * the handler returns a value by RETURN, and the op declares neither an int return nor a
      pointer argument to receive it -- the op could not deliver the result it asked for;
    * the handler delivers through the ``void* p`` out-parameter and the op passes no pointer;
    * the handler reads a selector ``arg0`` and the op has arity 0 -- nothing to select with.
    """
    code = next(iter(v.codes))
    ms = msigs.get(code)
    if ms is None:
        return CrossCheck(op, "FLAG", "no managed case parsed for code %d" % code)
    kinds = sig.kinds
    has_ptr = "p" in kinds
    notes: List[str] = []
    if ms.returns_value and not ms.uses_p and sig.ret == "void" and not has_ptr:
        notes.append("managed returns a value; op is void with no out-pointer")
    if ms.uses_p and not has_ptr:
        notes.append("managed delivers through p; op passes no pointer")
    if ms.args and sig.arity == 0:
        notes.append("managed reads arg%s; op has arity 0" % sorted(ms.args))
    return CrossCheck(op, "FLAG" if notes else "AGREE", "; ".join(notes))


#: The marker that makes a managed-ABI evidence line greppable in ``hle_ops.json``.
MANAGED_ABI_MARKER = "managed-ABI:"


def callback_evidence(namer: Optional[OpNamer] = None) -> Dict[int, dict]:
    """The injectable evidence source ``tier_r_annot.build_hle_ops(callback=...)`` consumes.

    Only ops that resolve to EXACTLY ONE command appear.  An op that reaches several is left out
    entirely rather than described with a guess -- ``cluster_report`` publishes those as named
    refusals, which is where they belong.
    """
    namer = namer or OpNamer()
    msigs = managed_signatures()
    out: Dict[int, dict] = {}
    for op, v in namer.sweep().items():
        if not v.name:
            continue
        code = next(iter(v.codes))
        sub = _submode_of(namer, v, code)
        ms = msigs.get(code)
        note = ""
        if sub is not None and ms and sub in ms.submodes and ms.submodes[sub]:
            note = " sub-mode %d (%s)" % (sub, ms.submodes[sub])
        elif sub is not None:
            note = " sub-mode %d" % sub
        out[op] = {
            "command": v.name,
            "code": code,
            "submode": sub,
            "confidence": v.confidence,
            "evidence": ("%s the native function issues callback command %d = SFX.COMMAND.%s%s "
                         "at depth %d (Memoria SFX.cs enum COMMAND; code = fullCode >> 24)"
                         % (MANAGED_ABI_MARKER, code, v.name, note, v.depth)),
        }
    return out


def _submode_of(namer: OpNamer, v: OpVerdict, code: int) -> Optional[int]:
    """The constant ``arg0`` staged at the op's callback sites, when every site agrees.

    Several commands multiplex on ``arg0`` -- ``COMMAND_GET_MATRIX`` alone covers Get Bone
    Position / Height / Orientation.  Where the DLL pins it, the sub-mode is part of the name; where
    the op forwards its own caller's value, there is nothing constant to report and this returns
    None rather than picking one.
    """
    seen = {s.arg0 for f in v.via for s in namer.cb.sites if s.fn == f and s.code == code}
    seen.discard(None)
    return next(iter(seen)) if len(seen) == 1 else None


def cluster_report(namer: Optional[OpNamer] = None) -> Dict[str, object]:
    """The round's deliverable: names, refusals, conflicts and the cross-check, in one pass."""
    namer = namer or OpNamer()
    ops = A.load_hle_ops()
    msigs = managed_signatures()
    sweep = namer.sweep()

    named, refused, conflicts, checks = {}, {}, {}, {}
    for op, v in sweep.items():
        if v.name:
            sig = namer.dll.handler(op)
            checks[op] = crosscheck(op, v, sig, msigs)
            if ops[op].get("name"):
                conflicts[op] = (ops[op]["name"], ops[op].get("confidence"), v.name)
            named[op] = v
        elif v.via:
            refused[op] = v
    return {"sweep": sweep, "named": named, "refused": refused,
            "conflicts": conflicts, "checks": checks, "ops": ops, "managed": msigs}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--cluster", action="store_true")
    ap.add_argument("--op", type=int, default=None)
    args = ap.parse_args(argv)

    namer = OpNamer()

    if args.calibrate or not (args.sweep or args.cluster or args.op is not None):
        ok, lines = calibrate(namer)
        print("CALIBRATION -- A1-TEXTURES §5.2 reproduced under the UNWIND-exact model")
        for ln in lines:
            print(ln)
        print("  =>", "PASS" if ok else "FAIL")
        if not ok:
            return 1

    if args.op is not None:
        v = namer.verdict(args.op)
        print("op %d: name=%s confidence=%s depth=%s codes=%s via=%s\n  %s"
              % (v.op, v.name, v.confidence, v.depth, sorted(v.codes),
                 [hex(x) for x in v.via], v.reason))

    if args.sweep or args.cluster:
        rep = cluster_report(namer)
        sweep, named, refused = rep["sweep"], rep["named"], rep["refused"]
        ops, checks, conflicts = rep["ops"], rep["checks"], rep["conflicts"]
        print("\nSWEEP: %d of %d ops reach the callback; %d resolve to exactly one command"
              % (sum(1 for v in sweep.values() if v.via), len(sweep), len(named)))

        traffic = sum(ops[op]["call_sites"] for op in named if not ops[op].get("name"))
        print("\nNAMED (%d ops, %d corpus call sites)" % (len(named), traffic))
        for op in sorted(named, key=lambda o: -ops[o]["call_sites"]):
            v, c = named[op], checks[op]
            print("  op %3d  %-28s [%-6s] calls=%5d  sig(%s)->%-4s  %s%s"
                  % (op, v.name, v.confidence, ops[op]["call_sites"],
                     ops[op]["arg_kinds"], ops[op]["returns"], c.verdict,
                     "  -- " + c.note if c.note else ""))

        agree = sum(1 for c in checks.values() if c.verdict == "AGREE")
        print("\nCROSS-CHECK vs the managed handler: %d/%d agree" % (agree, len(checks)))

        if conflicts:
            print("\nCONFLICTS with hle_ops.json")
            for op, (old, conf, new) in sorted(conflicts.items()):
                print("  op %3d  R2 said %-24s [%s]   callback says %s" % (op, old, conf, new))

        print("\nREFUSED -- reaches the callback, more than one command (%d ops, %d call sites)"
              % (len(refused), sum(ops[op]["call_sites"] for op in refused)))
        for op in sorted(refused, key=lambda o: -ops[o]["call_sites"]):
            v = refused[op]
            print("  op %3d  calls=%5d  codes=%s"
                  % (op, ops[op]["call_sites"],
                     ",".join(namer.commands.get(c, str(c)) for c in sorted(v.codes))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
