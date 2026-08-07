"""TIER R rung 2 -- THE ANNOTATOR: names the boundary a rung-1 disassembly leaves anonymous.

R1 made resource id-3 *decodable*: 385 images / 599 program entries walk with zero invalid reachable
instructions and zero unresolved call targets.  What it could not say is what any of it MEANS -- 204
of the 216 HLE ops were bare numbers, every absolute address was a bare number, and the reachable
code was one undifferentiated mass.  This module supplies the three missing name-spaces:

  (A) THE HLE OP DICTIONARY  -- ``hle_ops.json``.  Two independent evidence streams, combined:
      * STATIC, from the DLL.  Each op ``i`` is a slot in the dispatcher's own jump table
        (``fn 0xee80``, table @``0x12358``).  The stub at ``jt[i]`` pulls its arguments either
        through ``getArgInt``@``0x126c0`` / ``getArgPtr``@``0x12740`` (``edx`` = the argument index)
        or INLINE off the interpreter context (``[ctx + 0xca8/0xcac/0xcb0/0xcb4]`` = ``$a0..$a3``,
        ``[ctx + 0xd0c]`` = the MIPS ``$sp`` for arguments 4+), then tail-jumps to one of exactly two
        epilogues: ``0x122f1`` (return ``r12d`` -- and ``r12d`` is zeroed at ``0xee92``, so "no
        ``mov r12d,eax``" means *void*) or ``0x11e7a`` (convert a host pointer back to a PSX address
        and return THAT).  So arity, per-argument int-vs-pointer kind, and the return kind all fall
        out statically.  **The inline form is the one a naive reading misses; without it the
        calibration set scores 4/12 (see ``--calibrate``).**
      * CORPUS-STATISTICAL.  Per-op call-site census over all 385 images: how many argument
        registers each site actually sets, the constant-argument value distribution, which effects
        use the op (creature-bearing or not), which ops it sits next to, and where in the program it
        is called.

      Names come only from evidence the DLL itself carries: the leftover ``Hi_Foo()`` debug strings
      (located by RIP-relative xref, resolved to a function through the **UNWIND_INFO chain**, not
      by nearest-.pdata-entry), the CRT imports a stub reaches, and the "stub IS the return tail"
      no-op shape.  Everything weaker is named descriptively and marked ``medium``/``low``.

  (B) THE GLOBALS + DATA-REF MAP -- every absolute address the program builds, classified against
      the id-3 image's own PSX address space (``0x801E7700 + (slot&1)*0x5000``, ``ef_container``)
      and against the FORMAT round's host memory map (:data:`NAMED_GLOBALS`).

  (C) THE FUNCTION ROLE TABLE -- the reachable code segmented into functions by flood-fill from the
      program entries and the in-image call targets, each tagged by the HLE ops and coprocessor
      instructions it actually contains.

PROVENANCE.  Pure analysis code.  Reads the user's own installed DLL (READ-ONLY, never modified) and
caller-supplied blobs; emits names, RVAs, offsets and counts.  **Annotated listings of stock images
are derived stock content -- scratch tree only, never the repo.**

CLI::

    py tier_r_annot.py --calibrate                 # the 12 known ops, re-derived statically
    py tier_r_annot.py --hle-ops hle_ops.json      # build the dictionary (DLL + corpus)
    py tier_r_annot.py --image ef227.bytes         # data-ref map + function table for one container
    py tier_r_annot.py --image ef227.bytes --listing OUTDIR    # SCRATCH ONLY
"""
from __future__ import annotations

import argparse
import bisect
import collections
import json
import os
import re
import struct
import sys
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_DISASM_DIR = os.path.normpath(os.path.join(_HERE, "..", "thomas-swap", "disasm"))
if _DISASM_DIR not in sys.path:
    sys.path.insert(0, _DISASM_DIR)

import tier_r_disasm as T   # noqa: E402

SCRATCH_CORPUS = T.SCRATCH_CORPUS
HLE_OPS_JSON = os.path.join(_HERE, "hle_ops.json")


# ===========================================================================  (B) the memory map
#: The FORMAT round's host-side memory map, as x64 DLL RVAs.  Every row carries the report that
#: established it, so a disagreement found here is attributable rather than anonymous.
#: These are HOST addresses -- the MIPS program cannot name them directly (it sees emulated PSX
#: RAM); they are reached through the HLE boundary, which is why they are attributed to *ops*.
NAMED_GLOBALS: Dict[int, Tuple[str, str]] = {
    0x1C1DC8: ("viewMatrix", "FORMAT 81: SFX_Update copies the installed camera here"),
    0x1C1DE8: ("vramUploadCallback", "ef_container RESOURCE_IDS[0]: LoadImage callback slot"),
    0x211DF0: ("cam13Floats", "A5 3: the 13-float camera SFX_UpdateCamera returns"),
    0x211E24: ("cameraKeyframeFlag", "A5 4: kf_flag gate"),
    0x211E28: ("cameraKeyframeSrc", "A5 4: the keyframe source installed into curCam"),
    0x211F40: ("gteRotationMatrix", "B3 279: GTE current rotation 3x3 i16 (R)"),
    0x211F54: ("gteTranslation", "B3 280: GTE translation TRX/TRY/TRZ"),
    0x211FA0: ("gteOFX", "B3 281 / FORMAT 145: projection X offset (160)"),
    0x211FA4: ("gteOFY", "B3 281 / FORMAT 145: projection Y offset (120)"),
    0x211FA8: ("gteH", "B3 281 / FORMAT 145: projection distance H"),
    0x211FC0: ("gteVertexBank", "B3 282: GTE input vertex bank V0/V1/V2, stride 8"),
    0x212440: ("otzArray", "B3 285: per-vertex ordering-table depth"),
    0x2191A0: ("screenXYArray", "B3 284: per-vertex projected screen XY"),
    0x220830: ("summonModels", "A5 141: the summon model slot array"),
    0x21FF68: ("sysStruct", "R1 G7: the MIPS-visible host struct, 5 fields"),
    0x21FF78: ("sysStruct.hleTable", "R1 G7: +0x10 = the 216-entry sentinel table's PSX base"),
    0x21FF7C: ("sysStruct.camera", "R1 G7: +0x14 = the camera struct's PSX base"),
    0x68250: ("hleSentinelTable", "R1 G7: 216 dwords 0xFF000000|i"),
    0x69730: ("curCam", "A5 39: the installed camera, PSX int16 form"),
    0x323170: ("seqState", "R1 G7: psx(0x323170) -> sysStruct+0x00"),
    0x323178: ("curChunkSlot", "ef_container: LOAD_CHUNK stores the slot here"),
    0x323180: ("channelFlags", "FORMAT 443: byte[0x323180 + arg1] = arg2"),
    0x323198: ("seqPtr", "ef_container: the sequence stream cursor"),
    0x323218: ("arenaCursor", "FORMAT 260: the running PSX-RAM load cursor"),
    0x576A10: ("psxBankTable", "R1 G7: the host<->PSX address bank table"),
}

#: Globals whose meaning is broad enough that attributing an op to them proves little.  Kept out of
#: the discriminating evidence, reported separately.
DIFFUSE_GLOBALS = frozenset((0x576A10, 0x1C1DE8))


# ===========================================================================  (B) PSX address space
#: ``ef_container.Chunk.psx_base`` -- fn 0xd390@0xd431.  Both chunks of a container sit adjacent.
CHUNK_STRIDE = 0x5000
PSX_MAIN_RAM = 0x200000
SCRATCHPAD_BASE = 0x1F800000
SCRATCHPAD_SIZE = 0x400

#: The id-3 image header, relative to ``headerRel`` (``ef_container.parse_chunk_image`` + R1 11).
HEADER_FIELDS = (
    (0x00, 0x08, "header.words"),
    (0x08, 0x48, "header.programTable"),      # 16 dwords -- the walk's own seeds
    (0x48, 0x4C, "header.sysStructPtr"),      # the program's window onto the host
)


def classify_psx(addr: int, psx_base: int, header_rel: int, nbytes: int) -> Tuple[str, int, str]:
    """(kind, offset, detail) for one absolute PSX address seen in an id-3 program.

    ``kind`` is one of ``image_code`` / ``image_data`` / ``sibling_image`` / ``psx_ram`` /
    ``scratchpad`` / ``host_bank`` / ``not_an_address``.  The arms mirror the DLL's own PSX->host
    translator ``fn 0x10e0``: segment ``0x80`` under 2 MB is main RAM, ``(addr & 0xC00000) ==
    0xC00000`` is a bank-mapped HOST object, and ``0x1F800000..0x1F8003FF`` is the scratchpad.
    """
    addr &= 0xFFFFFFFF
    seg = addr >> 24
    base = psx_base & 0x0FFFFFFF
    if seg in (0x80, 0xA0, 0x00) and (addr & 0x0FFFFFFF) < PSX_MAIN_RAM:
        rel = (addr & 0x0FFFFFFF) - base
        if 0 <= rel < header_rel:
            return "image_code", rel, ""
        if header_rel <= rel < nbytes:
            d = rel - header_rel
            for lo, hi, nm in HEADER_FIELDS:
                if lo <= d < hi:
                    return "image_data", rel, nm
            return "image_data", rel, "image.bss"
        for sign in (+1, -1):
            rel2 = rel - sign * CHUNK_STRIDE
            if 0 <= rel2 < nbytes:
                return "sibling_image", rel2, "the container's other chunk image"
        return "psx_ram", addr & 0x1FFFFF, ""
    if SCRATCHPAD_BASE <= addr < SCRATCHPAD_BASE + SCRATCHPAD_SIZE:
        return "scratchpad", addr - SCRATCHPAD_BASE, "fn 0x10e0 third arm"
    if seg and (addr & 0xC00000) == 0xC00000:
        return "host_bank", addr & 0x3FFFFF, "bank %d (fn 0x10e0 second arm)" % seg
    return "not_an_address", addr, ""


def looks_like_psx_pointer(v: int) -> bool:
    """True for a constant a PS1 LINKER could have emitted as an address.

    Deliberately NARROWER than :func:`classify_psx`.  The bank arm of the DLL's translator maps
    ``(addr & 0xC00000) == 0xC00000`` to a HOST object, but a bank base is assigned at runtime, so
    no ``lui``/``addiu`` pair can ever name one -- the program only ever obtains those by loading
    a ``sysStruct`` field.  Admitting the bank arm here instead re-labels ordinary NEGATIVE integer
    constants (``lui 0xffff`` + ``addiu``, whose ``0xFFFF####`` form satisfies the mask) as
    "host bank 255" pointers.  Main RAM and the scratchpad are the only link-time-nameable spaces.
    """
    v &= 0xFFFFFFFF
    seg = v >> 24
    if seg in (0x80, 0xA0) and (v & 0x0FFFFFFF) < PSX_MAIN_RAM:
        return True
    return SCRATCHPAD_BASE <= v < SCRATCHPAD_BASE + SCRATCHPAD_SIZE


# ===========================================================================  (A) the DLL side
DISPATCH_FN_RVA = 0xEE80              # int nativeCall(PsxCtx*, int op)
DISPATCH_JT_RVA = 0x12358             # 216 x u32 image-relative stub targets
NATIVE_FN_TABLE_RVA = 0x68780         # 216 x u64 -- the .data hypothesis, NOT the authority
GET_ARG_INT_RVA = 0x126C0
GET_ARG_PTR_RVA = 0x12740
PSX_TO_HOST_RVA = 0x10E0
HOST_TO_PSX_RVA = 0x12940
TAIL_RETURN_INT_RVA = 0x122F1         # returns r12d (zeroed @0xee92 -> void when never set)
TAIL_RETURN_PTR_RVA = 0x11E7A         # host pointer -> PSX address -> r12d
#: ``[ctx + N]`` displacements that ARE the MIPS argument registers (getArgInt's own arms).
CTX_ARG_SLOTS = {0xCA8: 0, 0xCAC: 1, 0xCB0: 2, 0xCB4: 3}
CTX_STACK_PTR = 0xD0C                 # the MIPS $sp -- arguments 4+ live at sp + 4*i
STACK_ARG_MIN = 0x10                  # O32: the first stacked argument is arg 4 at sp+0x10

_MEM_CTX = re.compile(r"\[(?=[^\]]*r13)[^\]]*\+ (0x[0-9a-f]+)\]")
_DST = re.compile(r"^(\w+),")
_RIP = re.compile(r"\[rip ([+-]) 0x([0-9a-f]+)\]")
_FN_NAME_STRING = re.compile(r"^([A-Za-z_][A-Za-z0-9_]{3,})\s*\(")


@dataclass
class HandlerSig:
    """What the dispatcher's own stub for one op says about that op's signature."""
    op: int
    stub: int
    args: Dict[int, str] = field(default_factory=dict)     # index -> "int" | "ptr"
    ret: Optional[str] = None                              # "void" | "int" | "ptr" | "none" | ...
    calls: Tuple[int, ...] = ()
    native_fn: int = 0                                     # the .data table's claim
    fn_confirmed: bool = False                             # ... and the stub really calls it
    noop: bool = False                                     # the jump table points AT the return tail
    stack_args: Tuple[int, ...] = ()

    @property
    def arity(self) -> int:
        return (max(self.args) + 1) if self.args else 0

    @property
    def kinds(self) -> str:
        return "".join("i" if self.args.get(k) == "int" else
                       "p" if self.args.get(k) == "ptr" else "?" for k in range(self.arity))


@dataclass
class NativeProfile:
    """What the op's native function touches."""
    fn: int
    names: Tuple[str, ...] = ()          # debug-string names owned by this function
    direct: Tuple[int, ...] = ()         # NAMED_GLOBALS RVAs referenced in the function itself
    deep: Tuple[int, ...] = ()           # ... or anywhere within two call levels
    crt: Tuple[str, ...] = ()            # CRT / import names reached at ANY depth
    crt_direct: Tuple[str, ...] = ()     # ... reached by the function ITSELF (thunks transparent)
    span: int = 0                        # functions visited while profiling


class DllView:
    """One parse of the plugin DLL, with the pieces R2 needs cached.

    The function model is UNWIND_INFO-exact: MSVC splits a function into several ``.pdata``
    RUNTIME_FUNCTION chunks, and a chunk whose unwind info carries ``UNW_FLAG_CHAININFO`` (0x4)
    names its primary.  Resolving a string xref by "nearest preceding ``.pdata`` begin" instead
    mis-attributes names across function boundaries -- it puts two different ``Hi_`` names on the
    same op.  Everything here follows the chain to the primary.
    """

    UNW_FLAG_CHAININFO = 0x4

    def __init__(self, pe=None):
        import refkit
        self.refkit = refkit
        self.pe = pe or refkit.load()
        self.base = refkit.image_base(self.pe)
        self._raw = []
        for e in self.pe.DIRECTORY_ENTRY_EXCEPTION:
            s = e.struct
            self._raw.append((s.BeginAddress, s.EndAddress, s.UnwindData))
        self._raw.sort()
        self._begins = [b for b, _, _ in self._raw]
        self._chunks: Dict[int, List[Tuple[int, int]]] = collections.defaultdict(list)
        for b, e, u in self._raw:
            self._chunks[self._primary(b, u)].append((b, e))
        self.imports: Dict[int, str] = {}
        for entry in getattr(self.pe, "DIRECTORY_ENTRY_IMPORT", []) or []:
            for imp in entry.imports:
                if imp.name:
                    self.imports[imp.address - self.base] = imp.name.decode()
        self.jt: List[int] = list(struct.unpack(
            "<%dI" % T.HLE_OP_COUNT, self.pe.get_data(DISPATCH_JT_RVA, 4 * T.HLE_OP_COUNT)))
        self.native_fn: List[int] = [
            (v - self.base) if v else 0 for v in struct.unpack(
                "<%dQ" % T.HLE_OP_COUNT, self.pe.get_data(NATIVE_FN_TABLE_RVA, 8 * T.HLE_OP_COUNT))]
        self._stub_starts = sorted(set(self.jt))
        self._prof_cache: Dict[int, Tuple[Set[int], Set[int], Set[str]]] = {}
        self._thunk_cache: Dict[int, Optional[str]] = {}
        self._name_of_fn = self._build_name_map()

    # -- function model -------------------------------------------------
    def _primary(self, begin: int, unwind: int) -> int:
        for _ in range(8):
            d = self.pe.get_data(unwind, 4)
            if not ((d[0] >> 3) & self.UNW_FLAG_CHAININFO):
                return begin
            count = d[2]
            off = unwind + 4 + 2 * ((count + 1) & ~1)
            begin, _end, unwind = struct.unpack("<III", self.pe.get_data(off, 12))
        return begin

    def function_of(self, rva: int) -> Optional[int]:
        """The primary start of the function containing ``rva`` (None outside every chunk)."""
        i = bisect.bisect_right(self._begins, rva) - 1
        if i < 0:
            return None
        b, e, u = self._raw[i]
        return self._primary(b, u) if b <= rva < e else None

    def body(self, fn: int, fallback_bytes: int = 0x400):
        """Every instruction of a function, chunk by chunk.

        A leaf with no unwind data has no ``.pdata`` row at all; for those we disassemble linearly
        from the entry and stop at the first ``ret`` -- stated, because it is a weaker read.
        """
        chunks = sorted(self._chunks.get(fn, ()))
        if not chunks:
            for ins in self.refkit.disasm(self.pe, fn, fn + fallback_bytes):
                yield ins
                if ins.mnemonic == "ret":
                    return
            return
        for b, e in chunks:
            for ins in self.refkit.disasm(self.pe, b, e):
                yield ins

    def rip_target(self, ins) -> Optional[int]:
        m = _RIP.search(ins.op_str)
        if not m:
            return None
        disp = int(m.group(2), 16) * (1 if m.group(1) == "+" else -1)
        return (ins.address - self.base) + ins.size + disp

    # -- the debug-string name map ---------------------------------------
    def _build_name_map(self) -> Dict[int, Set[str]]:
        strings = self.refkit.string_rvas(self.pe, 4)
        cand = {}
        for rva, txt in strings.items():
            m = _FN_NAME_STRING.match(txt)
            if m:
                cand[rva] = m.group(1)
        if not cand:
            return {}
        xi = self.refkit.xref_index(self.pe, min(cand), max(cand) + 64,
                                    self.refkit.functions(self.pe))
        out: Dict[int, Set[str]] = collections.defaultdict(set)
        for srva, name in cand.items():
            for from_rva, _m, _o in xi.get(srva, ()):
                fn = self.function_of(from_rva)
                if fn is not None:
                    out[fn].add(name)
        return out

    # -- the handler stub -------------------------------------------------
    def handler(self, op: int) -> HandlerSig:
        """Decode one dispatcher stub into a signature.

        Two argument idioms, both real and both required (see the module docstring):
          * ``mov edx, <i> ; call getArgInt/getArgPtr``
          * ``mov <reg>, [ctxIndex + r13 + 0xca8|0xcac|0xcb0|0xcb4]`` -- the same four fields
            ``getArgInt`` itself reads, inlined.  A dword read into ``edx`` and then handed to
            ``fn 0x10e0`` is a POINTER argument; otherwise an int.
        """
        stub = self.jt[op]
        sig = HandlerSig(op=op, stub=stub, native_fn=self.native_fn[op])
        if stub in (TAIL_RETURN_INT_RVA, TAIL_RETURN_PTR_RVA):
            sig.noop = True
            sig.ret = "none"
            return sig
        i = bisect.bisect_right(self._stub_starts, stub)
        end = self._stub_starts[i] if i < len(self._stub_starts) else DISPATCH_JT_RVA
        end = min(end, stub + 0x400)
        calls: List[int] = []
        stack: List[int] = []
        edx_const: Optional[int] = None
        edx_src = None                       # an arg index, or "SP", or None
        r12_set = False
        sp_live = False
        for ins in self.refkit.disasm(self.pe, stub, end):
            mn, ops = ins.mnemonic, ins.op_str
            mm = _MEM_CTX.search(ops)
            if mm:
                disp = int(mm.group(1), 16)
                dst = _DST.match(ops)
                if disp in CTX_ARG_SLOTS:
                    idx = CTX_ARG_SLOTS[disp]
                    sig.args.setdefault(idx, "int")
                    if dst and dst.group(1) == "edx":
                        edx_src = idx
                elif disp == CTX_STACK_PTR and dst and dst.group(1) == "edx":
                    edx_src = "SP"
            if mn == "mov" and re.match(r"^edx, (0x[0-9a-f]+|\d+)$", ops):
                edx_const, edx_src = int(ops[5:], 0), None
            elif mn == "xor" and ops == "edx, edx":
                edx_const, edx_src = 0, None
            elif mn == "call":
                tgt = int(ops, 16) - self.base if ops.startswith("0x") else None
                if tgt == GET_ARG_INT_RVA and edx_const is not None:
                    sig.args[edx_const] = "int"
                elif tgt == GET_ARG_PTR_RVA and edx_const is not None:
                    sig.args[edx_const] = "ptr"
                elif tgt == PSX_TO_HOST_RVA:
                    if isinstance(edx_src, int):
                        sig.args[edx_src] = "ptr"
                    elif edx_src == "SP":
                        sp_live = True
                elif tgt is not None:
                    calls.append(tgt)
            elif mn == "mov" and ops == "r12d, eax":
                r12_set = True
            elif mn == "jmp":
                tgt = int(ops, 16) - self.base if ops.startswith("0x") else None
                if tgt == TAIL_RETURN_INT_RVA:
                    sig.ret = "int" if r12_set else "void"
                    break
                if tgt == TAIL_RETURN_PTR_RVA:
                    sig.ret = "ptr"
                    break
                if tgt is not None and not (stub <= tgt < end):
                    sig.ret = "jmp:%#x" % tgt
                    break
            elif mn == "ret":
                sig.ret = "ret"
                break
            if sp_live and mn in ("mov", "movsxd") and "[rax" in ops:
                m2 = re.search(r"\[rax(?: \+ (0x[0-9a-f]+))?\]", ops)
                if m2:
                    d = int(m2.group(1), 16) if m2.group(1) else 0
                    if d % 4 == 0 and STACK_ARG_MIN <= d < 0x100:
                        stack.append(d // 4)
        for a in stack:
            sig.args.setdefault(a, "int")
        sig.calls = tuple(calls)
        sig.stack_args = tuple(sorted(set(stack)))
        sig.fn_confirmed = bool(sig.native_fn) and sig.native_fn in sig.calls
        return sig

    def handlers(self) -> Dict[int, HandlerSig]:
        return {op: self.handler(op) for op in range(T.HLE_OP_COUNT)}

    # -- the native function ----------------------------------------------
    def _thunk_import(self, rva: int) -> Optional[str]:
        """The import a 6-byte ``jmp qword ptr [rip+X]`` thunk forwards to, else None."""
        if rva in self._thunk_cache:
            return self._thunk_cache[rva]
        name = None
        try:
            for ins in self.refkit.disasm(self.pe, rva, rva + 8):
                if ins.mnemonic == "jmp" and "rip" in ins.op_str:
                    name = self.imports.get(self.rip_target(ins))
                break
        except Exception:
            pass
        self._thunk_cache[rva] = name
        return name

    def _shallow(self, fn: int) -> Tuple[Set[int], Set[int], Set[str]]:
        if fn in self._prof_cache:
            return self._prof_cache[fn]
        calls: Set[int] = set()
        globs: Set[int] = set()
        crt: Set[str] = set()
        try:
            for ins in self.body(fn):
                if ins.mnemonic in ("call", "jmp"):
                    if ins.op_str.startswith("0x"):
                        tgt = int(ins.op_str, 16) - self.base
                        # MSVC routes every CRT call through a 6-byte import thunk
                        # (`jmp qword [rip+X]`).  Treat the thunk as TRANSPARENT so "this function
                        # itself calls `cos`" stays a depth-0 fact -- without that, either the two
                        # trig ops stay anonymous, or (worse) the name leaks down a call chain onto
                        # every op that transitively reaches `cos`.
                        name = self._thunk_import(tgt)
                        if name is not None:
                            crt.add(name)
                        elif ins.mnemonic == "call" or not (fn <= tgt < fn + 0x1000):
                            calls.add(tgt)
                    else:
                        t = self.rip_target(ins)
                        if t in self.imports:
                            crt.add(self.imports[t])
                else:
                    t = self.rip_target(ins)
                    if t is not None and t in NAMED_GLOBALS:
                        globs.add(t)
        except Exception:                                  # unreadable range -- report nothing
            pass
        self._prof_cache[fn] = (calls, globs, crt)
        return self._prof_cache[fn]

    def profile(self, fn: int, depth: int = 2) -> NativeProfile:
        if not fn:
            return NativeProfile(fn=0)
        direct_calls, direct, crt = self._shallow(fn)
        deep: Set[int] = set(direct)
        allcrt: Set[str] = set(crt)
        seen: Set[int] = {fn}
        frontier = [(t, 1) for t in direct_calls]
        while frontier:
            tgt, d = frontier.pop()
            f2 = self.function_of(tgt) or tgt
            if f2 in seen or d > depth:
                continue
            seen.add(f2)
            c2, g2, r2 = self._shallow(f2)
            deep |= g2
            allcrt |= r2
            if d < depth:
                frontier.extend((t, d + 1) for t in c2)
        return NativeProfile(fn=fn, names=tuple(sorted(self._name_of_fn.get(fn, ()))),
                             direct=tuple(sorted(direct)), deep=tuple(sorted(deep)),
                             crt=tuple(sorted(allcrt)), crt_direct=tuple(sorted(crt)),
                             span=len(seen))

    def profile_op(self, op: int, sig: Optional[HandlerSig] = None) -> NativeProfile:
        """Profile the op's native function -- and, when the stub INLINES the work instead of
        calling the table's function, fold in the stub's own immediate callees as depth-0."""
        sig = sig or self.handler(op)
        fn = self.function_of(self.native_fn[op]) or self.native_fn[op]
        prof = self.profile(fn)
        if not sig.fn_confirmed and not sig.noop and sig.calls:
            crt_d, direct = set(prof.crt_direct), set(prof.direct)
            allcrt = set(prof.crt)
            for tgt in sig.calls:
                name = self._thunk_import(tgt)
                if name is not None:
                    crt_d.add(name)
                    allcrt.add(name)
                    continue
                f2 = self.function_of(tgt) or tgt
                p2 = self.profile(f2, depth=1)
                crt_d |= set(p2.crt_direct)
                allcrt |= set(p2.crt)
                direct |= set(p2.direct)
            prof = NativeProfile(fn=prof.fn, names=prof.names, direct=tuple(sorted(direct)),
                                 deep=tuple(sorted(set(prof.deep) | direct)),
                                 crt=tuple(sorted(allcrt)), crt_direct=tuple(sorted(crt_d)),
                                 span=prof.span)
        return prof


# ===========================================================================  (A) the corpus census
@dataclass
class OpCensus:
    op: int
    call_sites: int = 0
    images: int = 0
    effects: Set[str] = field(default_factory=set)
    creature_effects: Set[str] = field(default_factory=set)
    observed_arity: collections.Counter = field(default_factory=collections.Counter)
    const_args: Tuple[collections.Counter, ...] = field(
        default_factory=lambda: tuple(collections.Counter() for _ in range(4)))
    neighbours: collections.Counter = field(default_factory=collections.Counter)
    depth_bins: collections.Counter = field(default_factory=collections.Counter)
    #: THE FALSIFIABLE INDEX TEST.  For an op whose $a1 is claimed to be a sub-file index, every
    #: statically-known value must address a sub-file that the chunk's id-2 directory really has.
    index_in_range: int = 0
    index_out_of_range: int = 0
    index_out_examples: List[str] = field(default_factory=list)

    @property
    def index_hit_rate(self) -> float:
        n = self.index_in_range + self.index_out_of_range
        return self.index_in_range / n if n else 0.0

    @property
    def max_observed_arity(self) -> int:
        return max(self.observed_arity) if self.observed_arity else 0


ARG_REG_SET = frozenset(T.ARG_REGS)
CALL_NAMES = ("jal", "jalr", "bltzal", "bgezal")


def walk(img: T.Id3Image, hle_names: Optional[Dict[int, str]] = None
         ) -> Tuple[T.ImageWalker, T.WalkResult]:
    """R1's walk, keeping the walker so its block decomposition can be reused."""
    w = T.ImageWalker(img.payload, img.psx_base, img.header_rel, img.live_programs,
                      name=img.label, hle_names=hle_names)
    return w, w.run()


def observed_arities(w: T.ImageWalker, r: T.WalkResult) -> Dict[int, int]:
    """{callSiteOffset: how many of $a0..$a3 were written since the previous call in this block}.

    A lower bound on the real arity, and deliberately so: argument registers are caller-saved, so
    the window between two calls is exactly where a site's own arguments are set up.  Anything
    forwarded from the caller's own $a0..$a3, or reloaded from the frame, is invisible here -- which
    is why this is used to CHECK the static arity, never to replace it.
    """
    out: Dict[int, int] = {}
    for _b, (body, _succ) in w.blocks(r).items():
        written: Set[int] = set()
        transfer: Optional[T.Instr] = None
        for off in body:
            ins = r.instrs.get(off)
            if ins is None or ins.entry is None:
                continue
            if ins.entry.is_transfer:
                transfer = ins
                continue
            dst = _written_reg(ins)
            if dst in ARG_REG_SET:
                written.add(dst)
        if transfer is not None and transfer.entry.name in CALL_NAMES:
            out[transfer.off] = (max(written) - T.ARG_REGS[0] + 1) if written else 0
        # a block that ends in a call resets the window for the next block; blocks are re-entered
        # from their own start, so no carry is needed.
    return out


_WRITES_FIRST_OPERAND = frozenset((
    "lui", "addiu", "addi", "ori", "li", "andi", "xori", "move", "addu", "add", "or", "sll", "sra",
    "srl", "sllv", "srlv", "srav", "and", "xor", "nor", "sub", "subu", "slt", "sltu", "slti",
    "sltiu", "lw", "lb", "lh", "lbu", "lhu", "lwl", "lwr", "mfhi", "mflo", "mfc0", "mfc1", "mfc2",
    "mfc3", "cfc0", "cfc1", "cfc2", "cfc3",
))


def _written_reg(ins: T.Instr) -> Optional[int]:
    if ins.entry is None or ins.entry.name not in _WRITES_FIRST_OPERAND:
        return None
    if not ins.entry.ex or ins.entry.ex[0] not in (T.Ex.RD, T.Ex.RT):
        return None
    return ins.ops[0] or None


def census_corpus(root: str = SCRATCH_CORPUS, hle_names: Optional[Dict[int, str]] = None,
                  progress: bool = False) -> Tuple[Dict[int, OpCensus], List[dict]]:
    """One pass over the corpus: per-op call census + the per-image summary R3 will want."""
    import ef_container as ec
    import glob as _glob
    hle_names = hle_names if hle_names is not None else T.load_hle_names()
    census: Dict[int, OpCensus] = {op: OpCensus(op) for op in range(T.HLE_OP_COUNT)}
    images: List[dict] = []
    for path in sorted(_glob.glob(os.path.join(root, "ef*.bytes"))):
        blob = open(path, "rb").read()
        src = os.path.splitext(os.path.basename(path))[0]
        has_creature = False
        subfiles: Dict[int, int] = {}
        try:
            container = ec.parse_header(blob)
            for ch in container.chunks:
                try:
                    if ec.parse_model_package(blob, ch) is not None:
                        has_creature = True
                except Exception:
                    pass
                for res in ch.resources:
                    if res.id == 2:
                        try:
                            subfiles[ch.slot] = len(ec.parse_directory(blob, res.offset))
                        except Exception:
                            pass
        except Exception:
            pass
        for img in T.id3_images(blob, src):
            w, r = walk(img, hle_names)
            obs = observed_arities(w, r)
            ops_here: Set[int] = set()
            seq = [c for c in r.calls if c.kind in ("hle", "hle_multi")]
            for i, c in enumerate(seq):
                for op in _ops_of(c):
                    st = census[op]
                    st.call_sites += 1
                    st.effects.add(src)
                    if has_creature:
                        st.creature_effects.add(src)
                    ops_here.add(op)
                    st.observed_arity[obs.get(c.off, 0)] += 1
                    for k, v in enumerate(c.args):
                        if v is not None:
                            st.const_args[k][v] += 1
                    for j in (i - 1, i + 1):
                        if 0 <= j < len(seq):
                            for nb in _ops_of(seq[j]):
                                if nb != op:
                                    st.neighbours[nb] += 1
                    st.depth_bins[_phase_bin(c.off, img.header_rel)] += 1
                    nsub = subfiles.get(img.chunk_slot)
                    if nsub is not None and c.args[1] is not None:
                        if (c.args[1] & SUBFILE_INDEX_MASK) < nsub:
                            st.index_in_range += 1
                        else:
                            st.index_out_of_range += 1
                            if len(st.index_out_examples) < 6:
                                st.index_out_examples.append(
                                    "%s+%#x idx=%d of %d" % (img.label, c.off, c.args[1], nsub))
            for op in ops_here:
                census[op].images += 1
            images.append({"label": img.label, "source": src, "chunk": img.chunk_slot,
                           "header_rel": img.header_rel, "instrs": len(r.instrs),
                           "coverage": r.coverage, "creature": has_creature,
                           "subfiles": subfiles.get(img.chunk_slot),
                           "hle_calls": len(seq)})
        if progress and len(images) % 100 == 0:
            print("  ... %d images" % len(images), file=sys.stderr)
    return census, images


def _ops_of(c: T.CallSite) -> List[int]:
    if c.kind == "hle":
        return [c.hle_op]
    if c.kind == "hle_multi" and "table[" in c.detail:
        return [int(t) for t in c.detail.split("table[")[1].rstrip("]").split(",")]
    return []


def _phase_bin(off: int, header_rel: int) -> str:
    """Where in the code region a call sits.  A coarse proxy for init-vs-body, and labelled as one."""
    if not header_rel:
        return "?"
    f = off / header_rel
    return "first-third" if f < 1 / 3 else "middle-third" if f < 2 / 3 else "last-third"


# ===========================================================================  (A) the dictionary
#: A CRT name only pins an op's semantics when the op IS a thin wrapper around it.  Allowing the
#: match at any call depth is how ``rcos`` leaks onto every op that transitively reaches ``cos``
#: -- a wrong confident name, which this rung treats as a defect.
CRT_MAX_SPAN = 2

#: Ops whose stub reaches a CRT import that pins the semantics outright.
CRT_SEMANTICS = {
    "cos": ("rcos_fixed_point", "the stub converts $a0 to double, calls the CRT `cos` import, and "
                                "scales back to 12-bit fixed point"),
    "sin": ("rsin_fixed_point", "the stub converts $a0 to double, calls the CRT `sin` import, and "
                                "scales back to 12-bit fixed point"),
}

#: Descriptive names for a native function by the discriminating globals it DIRECTLY touches.
#: Ordered most-specific first; the first rule whose required set is satisfied wins.  These are
#: shaped as DESCRIPTIONS of an observed effect, never as guessed PS1-library symbols -- a wrong
#: confident symbol is a defect, a hedged description is not.
GLOBAL_RULES: Tuple[Tuple[frozenset, str, str], ...] = (
    (frozenset(("otzArray", "screenXYArray")), "emit_primitive_to_ordering_table", "medium"),
    (frozenset(("gteH", "gteOFX", "gteOFY", "gteRotationMatrix", "gteTranslation",
                "gteVertexBank")), "gte_project_vertices", "medium"),
    (frozenset(("gteH", "gteOFX", "gteOFY")), "set_projection_h_ofx_ofy", "medium"),
    (frozenset(("gteRotationMatrix", "gteTranslation", "gteVertexBank")),
     "gte_transform_vertices", "medium"),
    (frozenset(("gteRotationMatrix", "gteTranslation")), "set_gte_rot_and_trans", "medium"),
    (frozenset(("gteRotationMatrix",)), "set_gte_rotation_matrix", "medium"),
    (frozenset(("gteTranslation",)), "set_gte_translation", "medium"),
    (frozenset(("gteVertexBank",)), "load_gte_vertex_bank", "medium"),
    (frozenset(("seqPtr",)), "sequence_stream_access", "medium"),
    (frozenset(("channelFlags",)), "channel_flag_access", "medium"),
    (frozenset(("arenaCursor",)), "psx_ram_arena_access", "medium"),
    (frozenset(("cameraKeyframeFlag",)), "camera_keyframe_gate_access", "medium"),
    (frozenset(("curCam",)), "camera_struct_access", "medium"),
    (frozenset(("viewMatrix",)), "view_matrix_access", "medium"),
    (frozenset(("gteH",)), "set_projection_distance?", "low"),
    (frozenset(("summonModels",)), "summon_model_slot_access", "low"),
)


def global_semantics(direct: Sequence[str]) -> Optional[Tuple[str, str]]:
    """First matching rule, most specific first.

    A rule naming a SINGLE global must match the touch set exactly -- otherwise a function that
    writes the GTE translation *and* loads the vertex bank would be labelled a bare
    ``set_gte_translation``, which is a wrong confident name rather than a hedged one.  Two or more
    globals co-occurring are already a signature, so those rules may match as a subset.
    """
    have = set(direct)
    for need, name, conf in GLOBAL_RULES:
        if need <= have and (len(need) >= 2 or have <= need):
            return name, conf
    return None

#: The 12 ops ``M3-opcode-table.json`` already names -- R2's CALIBRATION SET.  The static method
#: must re-derive their signatures before any unknown op's signature is believed.
CALIBRATION_OPS = (11, 12, 23, 25, 26, 65, 100, 147, 149, 157, 158, 164)

#: Op 102's native function is the sub-file directory walker ``fn 0x3d800`` that ``ef_container``
#: documents (``entry = base + (Int32)base[idx]``), and the stub returns a POINTER.  The corpus test
#: that makes the reading falsifiable: every statically-known index must address a real sub-file.
SUBFILE_OP = 102
SUBFILE_INDEX_MASK = 0x7F


def build_hle_ops(dll: DllView, census: Dict[int, OpCensus],
                  known_names: Optional[Dict[int, str]] = None,
                  callback: Optional[Dict[int, dict]] = None,
                  body: Optional[Dict[int, dict]] = None) -> Dict[int, dict]:
    """The op dictionary: a name, a confidence and the evidence behind both, per op.

    CONFIDENCE CONTRACT (enforced, not merely documented -- see :func:`check_confidence_rule`):
      ``high``    the DLL itself supplies the name (a debug string owned by the op's function, a
                  CRT import that pins the semantics, or a stub that IS the return tail), OR the
                  MANAGED side of the ABI does (a resolved callback command code, see below) --
                  AND the handler stub decoded AND the corpus census is consistent.
      ``medium``  no symbol, but a discriminating static signature (a named global touched directly
                  by the native function, or a documented native function) plus corpus support.
      ``low``     one weak signal only; the name is descriptive and carries a trailing ``?``.
      unnamed     arity and return kind only.

    ``callback`` is the MANAGED-ABI evidence source (``callback_ops.callback_evidence``), injected
    rather than imported so this module keeps no dependency on it and a build without Memoria's
    source behaves exactly as it did before -- a stated skip, never a silent partial answer.
    Injection is also what keeps the dictionary SINGLE-WRITER: the fields land here, inside the
    builder, so ``--hle-ops`` regenerates them instead of a second tool bolting them on afterwards
    (the two-writers trap this project has already paid for once).

    THE TWO LANES ARE DISJOINT, MEASURED: no op named from a DLL debug string reaches the callback,
    and none of the 12 independently-known calibration ops do either (``cb_gates`` D1).  The
    ``Hi_*`` summon-model family is the DLL's own work and never crosses to managed; the ops that do
    cross are the battle-unit and VRAM family.  That is why R2's sources ran dry exactly where this
    one begins -- and it is why a callback name can never overwrite a debug-string name.
    """
    known_names = known_names if known_names is not None else T.load_hle_names()
    handlers = dll.handlers()
    fn_of_op = {op: (dll.function_of(dll.native_fn[op]) or dll.native_fn[op])
                for op in range(T.HLE_OP_COUNT)}
    owned = _exclusive_names(dll, fn_of_op)
    out: Dict[int, dict] = {}
    for op in range(T.HLE_OP_COUNT):
        sig = handlers[op]
        prof = dll.profile_op(op, sig)
        st = census[op]
        name: Optional[str] = None
        conf: Optional[str] = None
        evidence: List[str] = []
        static_ok = sig.noop or sig.ret is not None
        evidence.append("stub %#x: arity %d kinds=%s returns %s"
                        % (sig.stub, sig.arity, sig.kinds or "-", sig.ret))
        mine, borrowed = _split_names(prof, fn_of_op[op], owned)
        if borrowed:
            evidence.append("fn %#x also references %s, but another function owns that string "
                            "exclusively -- an inlined callee's assert text, not this op's name"
                            % (prof.fn, ", ".join(borrowed)))
        if sig.noop:
            name, conf = "nop_returns_zero", "high"
            evidence.append("the dispatcher's jump-table slot IS the return tail %#x: the op "
                            "executes nothing and returns r12d, zeroed at 0xee92"
                            % TAIL_RETURN_INT_RVA)
        elif len(mine) == 1:
            name, conf = mine[0], "high"
            evidence.append("the DLL's own debug string %r is owned by fn %#x (UNWIND_INFO-exact "
                            "function boundaries)" % (mine[0], prof.fn))
        elif any(c in CRT_SEMANTICS for c in prof.crt_direct) and prof.span <= CRT_MAX_SPAN:
            hit = next(c for c in prof.crt_direct if c in CRT_SEMANTICS)
            name, conf = CRT_SEMANTICS[hit][0], "high"
            evidence.append(CRT_SEMANTICS[hit][1] + " (a %d-function thin wrapper, so the import "
                            "IS the op rather than something it reaches)" % prof.span)
        elif mine:
            name, conf = "|".join(mine) + "?", "low"
            evidence.append("fn %#x carries %d unclaimed debug strings, so the symbol is AMBIGUOUS"
                            % (prof.fn, len(mine)))
        elif op == SUBFILE_OP:
            name, conf = "get_subfile_ptr", "medium"
            evidence.append("native fn %#x is the sub-file directory walker ef_container documents "
                            "(entry = base + (Int32)base[idx]); the stub returns a POINTER" % prof.fn)
            evidence.append("FALSIFIABLE INDEX TEST: %d/%d statically-known $a1 values address a "
                            "sub-file the chunk's id-2 directory really has (%.2f%%); misses %s"
                            % (st.index_in_range, st.index_in_range + st.index_out_of_range,
                               100 * st.index_hit_rate, st.index_out_examples[:3] or "none"))
        else:
            direct = tuple(sorted(NAMED_GLOBALS[g][0] for g in prof.direct
                                  if g not in DIFFUSE_GLOBALS))
            hit = global_semantics(direct)
            if hit:
                name, conf = hit
                evidence.append("fn %#x directly references %s" % (prof.fn, ", ".join(direct)))
            elif direct:
                name, conf = "touches_" + "_and_".join(direct) + "?", "low"
                evidence.append("fn %#x directly references %s" % (prof.fn, ", ".join(direct)))
        # an op with no name of its own inherits a twin's, one confidence step down
        if name is None and fn_of_op[op]:
            for other in range(T.HLE_OP_COUNT):
                if other == op or fn_of_op[other] != fn_of_op[op]:
                    continue
                tn, _ = _split_names(dll.profile(fn_of_op[other]), fn_of_op[other], owned)
                if len(tn) == 1:
                    name, conf = tn[0], "medium"
                    evidence.append("shares native fn %#x with op %d, which the DLL names"
                                    % (fn_of_op[op], other))
                    break
        # -- corpus evidence, always recorded ------------------------------
        # The consistency test is the MODE, not the maximum.  Argument registers are caller-saved,
        # so a block can leave one dirty from earlier work; a single high outlier is noise.  What
        # cannot be noise is where the distribution PILES UP -- and it piles up on exactly the
        # number of REGISTER-passed arguments the stub predicts (args 4+ ride the MIPS stack and
        # are invisible to this measure, which is why the prediction is min(arity, 4)).
        reg_arity = min(sig.arity, len(T.ARG_REGS))
        corpus_kind = "never-called"
        corpus_ok = True
        if sig.noop and st.call_sites:
            # a no-op has no arity to agree with; what the corpus says instead is a finding
            corpus_kind = "noop-called-anyway"
            evidence.append(
                "corpus: %d call sites in %d effects, and they still set up arguments for an op "
                "that executes nothing -- a retired entry point whose callers were never "
                "re-emitted (observed arg-setup %s)"
                % (st.call_sites, len(st.effects), dict(st.observed_arity)))
        elif st.call_sites:
            mode, mode_n = st.observed_arity.most_common(1)[0]
            corpus_kind = "arity-mode"
            corpus_ok = (mode == reg_arity)
            evidence.append(
                "corpus: %d call sites in %d images / %d effects (%d creature-bearing); modal "
                "arg-setup %d/%d sites = %d vs the stub's %d register args%s; full histogram %s"
                % (st.call_sites, st.images, len(st.effects), len(st.creature_effects), mode_n,
                   st.call_sites, mode, reg_arity,
                   " AGREES" if corpus_ok else " DISAGREES", dict(st.observed_arity)))
            top = st.neighbours.most_common(3)
            if top:
                evidence.append("called next to ops %s"
                                % ", ".join("%d(x%d)" % (o, n) for o, n in top))
            for k, c in enumerate(st.const_args):
                if c:
                    # a slot at or above the stub's arity is NOT an argument -- it is whatever the
                    # block left in that caller-saved register.  Labelled, never silently dropped:
                    # a constant piling up beyond the arity would be evidence the arity is wrong.
                    tag = "$a%d constants" % k if k < reg_arity else (
                        "$a%d (BEYOND the arity -- leftovers, not arguments)" % k)
                    evidence.append("%s: %s"
                                    % (tag, ", ".join("%d(x%d)" % (v, n)
                                                      for v, n in c.most_common(6))))
            evidence.append("position: %s" % dict(st.depth_bins))
        else:
            evidence.append("corpus: NEVER called by any of the 385 programs -- itself a checked "
                            "fact, and the expected one for a host-side registration entry point")
        # The managed-ABI source is folded in BEFORE the corpus demotion, not after: a callback name
        # is subject to exactly the same corpus consistency rule as every other high row.  Assigning
        # it afterwards let ops 1 and 203 keep `high` while the census disagreed with their stub
        # arity -- the confidence gate caught it, which is the whole reason that gate exists.
        cb = (callback or {}).get(op)
        if cb:
            evidence.append(cb["evidence"])
            if name is None:
                name, conf = cb["command"], cb["confidence"]
            elif name != cb["command"]:
                # NOT a contradiction, and not resolved by overwriting.  A callback code names the
                # BOUNDARY CROSSING an op performs, which is a lower bound on the op's semantics --
                # op 174 both reads a bone matrix across the ABI (COMMAND_GET_MATRIX) and transforms
                # vertices with it inside the DLL (R2's `gte_transform_vertices`).  Both are true;
                # the existing name is the more specific one, so it stands.
                evidence.append("the callback code is the op's boundary crossing, not its whole "
                                "semantics -- the existing name is retained as the more specific")
        # The HANDLER-BODY source (``body_ops``) is the expensive lane: a read of the op's native
        # function, corroborated by a corpus test with a control.  It ships at whatever confidence
        # it declares -- never ``high``, because no source states the name -- and it never displaces
        # an existing one, for the same reason the callback source does not (a body read describes
        # the mechanism; a symbol names the thing).
        bd = (body or {}).get(op)
        if bd:
            evidence.append(bd["evidence"])
            if name is None:
                name, conf = bd["name"], bd["confidence"]
        if conf == "high" and not (static_ok and corpus_ok):
            conf = "medium"
            evidence.append("demoted from high: the corpus census disagrees with the static arity")
        if op in known_names and name != known_names[op]:
            evidence.append("M3-opcode-table.json names this op %r" % known_names[op])
        out[op] = {
            "op": op,
            "name": name,
            "confidence": conf,
            "callback_command": cb["command"] if cb else None,
            "callback_code": cb["code"] if cb else None,
            "callback_submode": cb["submode"] if cb else None,
            "corpus_support": corpus_kind,
            "arity": sig.arity,
            "arg_kinds": sig.kinds,
            "returns": sig.ret,
            "native_fn": "%#x" % prof.fn if prof.fn else None,
            "native_fn_confirmed_by_stub": sig.fn_confirmed,
            "touches": [NAMED_GLOBALS[g][0] for g in prof.direct],
            "touches_deep": [NAMED_GLOBALS[g][0] for g in prof.deep],
            "evidence": "; ".join(evidence),
            "call_sites": st.call_sites,
            "effects": len(st.effects),
            "creature_effects": len(st.creature_effects),
        }
    return out


def _exclusive_names(dll: DllView, fn_of_op: Dict[int, int]) -> Dict[str, int]:
    """{name: fn} for every debug string exactly ONE op-function references.

    The DLL prints an assert message through the *callee's* name string, and MSVC inlines those
    callees; so ``Hi_DrawEffModelByBone``'s body also carries the ``Hi_GetSummonBoneMatrix`` text.
    A name another function owns exclusively is therefore borrowed, and dropping it turns an
    "ambiguous, two candidate symbols" row into a clean one.
    """
    holders: Dict[str, Set[int]] = collections.defaultdict(set)
    for fn in set(fn_of_op.values()):
        if not fn:
            continue
        for nm in dll.profile(fn).names:
            holders[nm].add(fn)
    out: Dict[str, int] = {}
    for nm, fns in holders.items():
        singles = [f for f in fns if len(dll.profile(f).names) == 1]
        if len(singles) == 1:
            out[nm] = singles[0]
    return out


def _split_names(prof: NativeProfile, fn: int, owned: Dict[str, int]) -> Tuple[List[str], List[str]]:
    """(names this function may claim, names it merely borrows from an inlined callee)."""
    mine, borrowed = [], []
    for nm in prof.names:
        if nm in owned and owned[nm] != fn:
            borrowed.append(nm)
        else:
            mine.append(nm)
    return mine, borrowed


def check_confidence_rule(ops: Dict[int, dict]) -> List[str]:
    """[] when every ``high`` row really carries BOTH evidence streams -- the H2 contract.

    static:  a decoded handler stub with a recognised terminator, and a name the DLL itself supplies.
    corpus:  a recorded census outcome that does not contradict the static signature -- either the
             modal argument-setup matches the stub's register-argument count, or the op is never
             called at all (a checked corpus fact in its own right), or it is a no-op whose callers
             pass arguments anyway (recorded as a finding).
    """
    ok_support = {"arity-mode", "never-called", "noop-called-anyway"}
    bad: List[str] = []
    for op, row in sorted(ops.items()):
        if row["confidence"] != "high":
            continue
        ev = row["evidence"]
        if "stub " not in ev:
            bad.append("op %d high without a decoded handler stub" % op)
        if "corpus:" not in ev:
            bad.append("op %d high without a corpus census line" % op)
        if row["returns"] is None:
            bad.append("op %d high but the stub has no recognised terminator" % op)
        if row.get("corpus_support") not in ok_support:
            bad.append("op %d high with unrecognised corpus support %r"
                       % (op, row.get("corpus_support")))
        if "DISAGREES" in ev:
            bad.append("op %d high although the corpus disagrees with the static arity" % op)
    return bad


def confidence_histogram(ops: Dict[int, dict]) -> collections.Counter:
    return collections.Counter(row["confidence"] or "unnamed" for row in ops.values())


def rebuild_hle_ops(dll: "DllView", census: Dict[int, OpCensus],
                    verbose: bool = True) -> Dict[int, dict]:
    """THE canonical dictionary build -- every writer of ``hle_ops.json`` must come through here.

    ``r2_gates.py`` rebuilds and rewrites the dictionary as part of its H-board.  When the
    managed-ABI source was wired into the CLI alone, running that board silently reverted 28 names
    to null -- the artifact had two writers that disagreed, which is the exact failure this project
    has a law about.  One function, both call sites, no way to build a partial dictionary by
    accident.

    The managed-ABI source stays OPTIONAL and loud: Memoria's clone is gitignored and shared between
    worktrees, so a machine without it must produce the pre-callback dictionary and SAY so.
    """
    cb_ev = None
    try:
        import callback_ops
        cb_ev = callback_ops.callback_evidence(
            callback_ops.OpNamer(callback_ops.CallbackMap(dll)))
        if verbose:
            print("managed-ABI evidence: %d ops named from callback command codes" % len(cb_ev))
    except Exception as exc:                                       # noqa: BLE001 -- reported
        if verbose:
            print("managed-ABI evidence SKIPPED (%s: %s) -- rebuilding without it"
                  % (type(exc).__name__, exc))
    body_ev = None
    try:
        import body_ops
        body_ev = body_ops.body_evidence(dll)
        if verbose:
            print("handler-body evidence: %d op(s) named from a read of the native function"
                  % len(body_ev))
    except Exception as exc:                                       # noqa: BLE001 -- reported
        if verbose:
            print("handler-body evidence SKIPPED (%s: %s) -- rebuilding without it"
                  % (type(exc).__name__, exc))
    return build_hle_ops(dll, census, callback=cb_ev, body=body_ev)


def write_hle_ops(ops: Dict[int, dict], path: str = HLE_OPS_JSON) -> str:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump([ops[o] for o in sorted(ops)], fh, indent=1)
        fh.write("\n")
    return path


def load_hle_ops(path: str = HLE_OPS_JSON) -> Dict[int, dict]:
    with open(path, "r", encoding="utf-8") as fh:
        return {int(r["op"]): r for r in json.load(fh)}


def calibration(dll: DllView, known_names: Optional[Dict[int, str]] = None) -> List[dict]:
    """Re-derive the 12 KNOWN ops' signatures from the DLL alone and score the method."""
    known_names = known_names if known_names is not None else T.load_hle_names()
    arity_ref = T.load_hle_arity()
    rows = []
    for op in CALIBRATION_OPS:
        sig = dll.handler(op)
        prof = dll.profile_op(op, sig)
        want = arity_ref.get(op)
        rows.append({
            "op": op, "expect_name": known_names.get(op), "derived_name":
                prof.names[0] if len(prof.names) == 1 else ("|".join(prof.names) or None),
            "arity": sig.arity, "expect_arity": want, "arity_ok": want is not None and want == sig.arity,
            "kinds": sig.kinds, "returns": sig.ret, "fn": sig.native_fn,
            "fn_confirmed": sig.fn_confirmed,
            "name_ok": len(prof.names) == 1 and prof.names[0] == known_names.get(op),
        })
    return rows


# ===========================================================================  (B) the data-ref map
@dataclass
class DataRef:
    off: int                 # the instruction that makes the reference
    addr: int                # the absolute PSX address
    kind: str                # classify_psx kind
    rel: int                 # offset inside whatever it names
    how: str                 # "pointer" | "load" | "store"
    detail: str = ""

    @property
    def resource(self) -> str:
        return self.detail or self.kind


_LOAD_NAMES = frozenset(("lw", "lb", "lh", "lbu", "lhu", "lwl", "lwr", "lwc0", "lwc1", "lwc2",
                         "lwc3"))
_STORE_NAMES = frozenset(("sw", "sb", "sh", "swl", "swr", "swc0", "swc1", "swc2", "swc3"))


def _const_step(r: T.WalkResult, body: Sequence[int], const: Dict[int, int],
                record=None) -> Dict[int, int]:
    """Fold one block's constants.  ``record(off, addr, how)`` fires on each address formed."""
    for off in body:
        ins = r.instrs.get(off)
        if ins is None or ins.entry is None:
            continue
        n = ins.entry.name
        if n == "lui":
            const[ins.ops[0]] = (ins.ops[1] << 16) & 0xFFFFFFFF
        elif n in ("addiu", "addi", "ori", "andi", "xori"):
            src = const.get(ins.ops[1])
            if src is None:
                const.pop(ins.ops[0], None)
            else:
                v = (src + ins.ops[2]) if n in ("addiu", "addi") else (
                    src | ins.ops[2]) if n == "ori" else (
                    src & ins.ops[2]) if n == "andi" else (src ^ ins.ops[2])
                const[ins.ops[0]] = v & 0xFFFFFFFF
                if record and looks_like_psx_pointer(const[ins.ops[0]]):
                    record(off, const[ins.ops[0]], "pointer")
        elif n == "move":
            if ins.ops[1] in const:
                const[ins.ops[0]] = const[ins.ops[1]]
            else:
                const.pop(ins.ops[0], None)
        elif n == "li":
            const[ins.ops[0]] = ins.ops[1] & 0xFFFFFFFF
        elif n in _LOAD_NAMES or n in _STORE_NAMES:
            base = const.get(ins.base_reg)
            if base is not None:
                addr = (base + ins.ops[1]) & 0xFFFFFFFF
                if record and looks_like_psx_pointer(addr):
                    record(off, addr, "load" if n in _LOAD_NAMES else "store")
            if n in _LOAD_NAMES:
                const.pop(ins.ops[0], None)
        else:
            dst = _written_reg(ins)
            if dst is not None:
                const.pop(dst, None)
        const[0] = 0
    return const


def _meet(a: Optional[Dict[int, int]], b: Dict[int, int]) -> Dict[int, int]:
    """Intersection on equal values -- a register keeps a constant only if EVERY path agrees."""
    if a is None:
        return dict(b)
    return {k: v for k, v in a.items() if b.get(k) == v}


DATAFLOW_ROUND_CAP = 80


def image_data_refs(img: T.Id3Image, w: T.ImageWalker, r: T.WalkResult) -> List[DataRef]:
    """Every absolute PSX address the reachable code builds or dereferences.

    A constant fold over ``lui`` / ``addiu`` / ``ori`` / ``move`` -- where PS1 code forms an
    address -- run to a FIXPOINT over the block graph rather than block-locally.  Block-local is
    not merely weaker, it systematically misses the switch-table idiom: the ``lui`` lands in the
    DELAY SLOT of the guarding ``beq``, which ends its block, so its companion ``addiu`` starts the
    next one and the pair never meets.

    The merge is an intersection on equal values, so a register keeps a constant only when every
    path into the block agrees on it.  Calls are barriers (caller-saved registers are dropped), and
    a block no path reaches with a settled state starts empty.  Under-counting, never inventing.
    """
    out: List[DataRef] = []
    seen: Set[Tuple[int, int]] = set()

    def record(off: int, addr: int, how: str):
        key = (off, addr & 0xFFFFFFFF)
        if key in seen:
            return
        seen.add(key)
        kind, rel, detail = classify_psx(addr, img.psx_base, img.header_rel, len(img.payload))
        if kind == "image_code":
            detail = "code" if rel in r.instrs else "in-code data (switch table / constant pool)"
        out.append(DataRef(off, addr & 0xFFFFFFFF, kind, rel, how, detail))

    blocks = w.blocks(r)
    preds: Dict[int, Set[int]] = {b: set() for b in blocks}
    for b, (_body, succs) in blocks.items():
        for s in succs:
            if s in preds:
                preds[s].add(b)
    state: Dict[int, Optional[Dict[int, int]]] = {b: None for b in blocks}
    work: List[int] = []
    for b in blocks:
        if not preds[b]:
            state[b] = {0: 0}
            work.append(b)
    rounds = 0
    cap = DATAFLOW_ROUND_CAP * max(1, len(blocks))
    while rounds < cap:
        while work and rounds < cap:
            rounds += 1
            b = work.pop()
            body, succs = blocks[b]
            exit_state = _const_step(r, body, dict(state[b] or {}))
            if _block_ends_in_a_call(r, body):
                for reg in T.CALLER_SAVED:
                    exit_state.pop(reg, None)
            for s in succs:
                if s not in state:
                    continue
                merged = _meet(state[s], exit_state)
                if state[s] is None or merged != state[s]:
                    state[s] = merged
                    work.append(s)
        left = [b for b in blocks if state[b] is None]
        if not left:
            break
        state[min(left)] = {0: 0}          # a block only a loop back-edge reaches
        work.append(min(left))
    for b in sorted(blocks):
        _const_step(r, blocks[b][0], dict(state[b] or {0: 0}), record=record)
    out.sort(key=lambda d: (d.off, d.addr))
    return out


def _block_ends_in_a_call(r: T.WalkResult, body: Sequence[int]) -> bool:
    for off in body:
        ins = r.instrs.get(off)
        if ins is not None and ins.entry is not None and ins.entry.name in CALL_NAMES:
            return True
    return False


def data_ref_summary(refs: Sequence[DataRef]) -> collections.Counter:
    return collections.Counter("%s/%s" % (d.kind, d.detail) if d.detail else d.kind for d in refs)


# ===========================================================================  (C) function roles
#: Which HLE ops make a function a member of each behavioural class.  Membership is a FACT (the
#: function literally contains that call); the class LABEL is the inference, and is named as one.
def role_tag_map(ops: Dict[int, dict]) -> Dict[str, Set[int]]:
    """{tag: ops}.  Global-derived tags use only DIRECT touches.

    Going two call levels deep instead makes every ``Hi_Register*`` op a "primitive emitter",
    because registration shares the geometry parser with the draw path -- a tag that broad labels
    everything and therefore distinguishes nothing.
    """
    tags: Dict[str, Set[int]] = collections.defaultdict(set)
    for op, row in ops.items():
        name = (row.get("name") or "").lower()
        direct = set(row.get("touches") or [])
        if "bonematrix" in name or "bonepos" in name:
            tags["bone"].add(op)
        if "draw" in name:
            tags["draw"].add(op)
        if "motion" in name or "motframe" in name:
            tags["motion"].add(op)
        if "register" in name or "subfile" in name or "arena" in name:
            tags["load"].add(op)
        if name.startswith(("rsin", "rcos")):
            tags["trig"].add(op)
        if "texanim" in name:
            tags["texanim"].add(op)
        if direct & {"gteH", "gteOFX", "gteOFY"}:
            tags["projection"].add(op)
        if direct & {"curCam", "viewMatrix", "cam13Floats", "cameraKeyframeFlag"}:
            tags["camera-struct"].add(op)
        if direct & {"otzArray", "screenXYArray"}:
            tags["primitive"].add(op)
        if direct & {"gteRotationMatrix", "gteTranslation", "gteVertexBank"}:
            tags["gte-globals"].add(op)
        if direct & {"summonModels"}:
            tags["summon-slot"].add(op)
        if direct & {"seqPtr", "channelFlags", "curChunkSlot"}:
            tags["sequence"].add(op)
    return dict(tags)


GTE_INSTRS = frozenset(("cop2", "mfc2", "mtc2", "cfc2", "ctc2", "lwc2", "swc2"))


@dataclass
class Function:
    start: int
    label: str
    offsets: Tuple[int, ...] = ()
    entry: bool = False
    calls: Tuple[int, ...] = ()          # in-image callees
    hle_ops: Tuple[int, ...] = ()
    tags: Tuple[str, ...] = ()
    gte: int = 0
    leaf: bool = False
    switches: int = 0        # compiled `switch` dispatches this function owns
    cases: int = 0           # ... and how many case targets they reach
    hle_calls: int = 0

    @property
    def size(self) -> int:
        return 4 * len(self.offsets)

    @property
    def role(self) -> str:
        if self.entry:
            return "program-entry"
        if self.leaf and not self.hle_ops:
            return "leaf-helper"
        if self.leaf:
            return "leaf-hle-wrapper"
        return "internal"


@dataclass
class Segmentation:
    functions: List[Function]
    owners: Dict[int, Tuple[int, ...]]
    orphans: Tuple[int, ...]
    shared: Tuple[int, ...]
    midbody_targets: Tuple[Tuple[int, int], ...]   # (callSite target, the function it lands inside)

    @property
    def clean(self) -> bool:
        return not self.orphans and not self.shared


def segment_functions(img: T.Id3Image, w: T.ImageWalker, r: T.WalkResult,
                      ops: Optional[Dict[int, dict]] = None) -> Segmentation:
    """Split the reachable code into functions and label each by what it demonstrably does.

    Starts = the program entries plus every in-image call target.  From each start we flood along
    intra-procedural edges only (fall-through, both branch arms, ``j``, and the ``switch`` targets
    of a jump table dispatched inside this function), stopping at any OTHER start.  An instruction
    reached from two starts, or from none, is reported rather than silently assigned -- that is the
    H5 consistency check, and a shared instruction is a real finding about the code (a tail-call
    landing pad, or a call into the middle of another function).
    """
    tagmap = role_tag_map(ops) if ops else {}
    calls_by_site = {c.off: c for c in r.calls}
    starts: Set[int] = set(o for o in r.entries if o in r.instrs)
    for c in r.calls:
        if c.kind == "in_image" and c.target in r.instrs:
            starts.add(c.target)
    jt_by_site = {jt.site: jt for jt in r.jump_tables}
    owners: Dict[int, Set[int]] = collections.defaultdict(set)
    reach: Dict[int, List[int]] = {}
    for s in sorted(starts):
        seen: Set[int] = set()
        stack = [s]
        while stack:
            off = stack.pop()
            if off in seen or off not in r.instrs:
                continue
            if off != s and off in starts:
                continue
            seen.add(off)
            ins = r.instrs[off]
            if ins.entry is None:
                continue
            if not ins.entry.is_transfer:
                stack.append(off + 4)
                continue
            if off + 4 in r.instrs:                       # the delay slot belongs to this function
                seen.add(off + 4)
            name = ins.entry.name
            if name == "jr":
                jt = jt_by_site.get(off)
                if jt:
                    stack.extend(jt.targets)
                continue
            if name in ("jal", "bltzal", "bgezal"):
                stack.append(off + 8)
                continue
            if name == "jalr":
                stack.append(off + 8)
                continue
            if name in ("j", "b"):
                stack.append(ins.ops[0])
                continue
            tgt = ins.op(T.Ex.BTARGET)
            if tgt is not None:
                stack.append(tgt)
            stack.append(off + 8)
        reach[s] = sorted(seen)
        for o in seen:
            owners[o].add(s)
    functions: List[Function] = []
    for s in sorted(starts):
        offs = tuple(reach[s])
        cs = tuple(sorted({calls_by_site[o].target for o in offs
                           if o in calls_by_site and calls_by_site[o].kind == "in_image"
                           and calls_by_site[o].target is not None}))
        hle = tuple(sorted({op for o in offs if o in calls_by_site
                            for op in _ops_of(calls_by_site[o])}))
        gte = sum(1 for o in offs
                  if r.instrs[o].entry is not None and r.instrs[o].entry.name in GTE_INSTRS)
        tags = sorted({t for t, members in tagmap.items() if members & set(hle)})
        if gte:
            tags.append("gte-code")
        mine = [jt for jt in r.jump_tables if jt.site in set(offs)]
        nhle = sum(1 for o in offs if o in calls_by_site
                   and calls_by_site[o].kind in ("hle", "hle_multi"))
        if len(offs) > 1 and mine:
            tags.append("state-machine")
        functions.append(Function(start=s, label=r.labels.get(s, "fn_%04x" % s), offsets=offs,
                                  entry=s in r.entries, calls=cs, hle_ops=hle,
                                  tags=tuple(tags), gte=gte, leaf=not cs,
                                  switches=len(mine), cases=sum(len(jt.targets) for jt in mine),
                                  hle_calls=nhle))
    orphans = tuple(sorted(o for o in r.instrs if o not in owners))
    shared = tuple(sorted(o for o, ow in owners.items() if len(ow) > 1))
    mid = tuple(sorted((t, s) for t in starts for s in starts
                       if s != t and t in owners and s in owners[t]))
    return Segmentation(functions=functions,
                        owners={o: tuple(sorted(v)) for o, v in owners.items()},
                        orphans=orphans, shared=shared, midbody_targets=mid)


# ===========================================================================  reporting helpers
def annotate_listing(img: T.Id3Image, w: T.ImageWalker, r: T.WalkResult, seg: Segmentation,
                     refs: Sequence[DataRef], ops: Dict[int, dict], fh) -> None:
    """R1's listing plus R2's names.  SCRATCH-ONLY for stock images -- derived stock content."""
    by_off = collections.defaultdict(list)
    for d in refs:
        by_off[d.off].append(d)
    fn_of = {}
    for f in seg.functions:
        for o in f.offsets:
            fn_of.setdefault(o, f)
    calls = {c.off: c for c in r.calls}
    fh.write("; %s  psxBase=%#010x headerRel=%#x  %d functions, %d data refs\n"
             % (r.name, r.psx_base, r.header_rel, len(seg.functions), len(refs)))
    for f in seg.functions:
        fh.write(";   %-10s %#06x %5d B  role=%-16s tags=%-28s hle=%s\n"
                 % (f.label, f.start, f.size, f.role, ",".join(f.tags) or "-",
                    ",".join(str(o) for o in f.hle_ops) or "-"))
    prev = None
    for off in sorted(r.instrs):
        if prev is not None and off != prev + 4:
            fh.write("        ---- %#x bytes unreached ----\n" % (off - prev - 4))
        ins = r.instrs[off]
        f = fn_of.get(off)
        if f is not None and f.start == off:
            fh.write("\n%s:            ; role=%s tags=%s\n"
                     % (f.label, f.role, ",".join(f.tags) or "-"))
        ann: List[str] = []
        if off in r.delay_slots:
            ann.append("[delay slot]")
        if ins.entry is not None and ins.entry.name == "cop2":
            ann.append("GTE " + T.gte_text(ins.ops[0]))
        c = calls.get(off)
        if c is not None and c.kind in ("hle", "hle_multi"):
            for op in _ops_of(c):
                row = ops.get(op, {})
                ann.append("HLE op %d %s [%s]" % (op, row.get("name") or "?",
                                                  row.get("confidence") or "unnamed"))
                if row.get("arg_kinds"):
                    ann.append("sig(%s)->%s" % (row["arg_kinds"], row.get("returns")))
        elif c is not None and c.kind == "in_image":
            ann.append("call %#x" % c.target)
        if c is not None:
            known = ["$a%d=%#x" % (i, v) for i, v in enumerate(c.args) if v is not None]
            if known:
                ann.append(" ".join(known))
        for d in by_off.get(off, ()):
            ann.append("%s %#010x -> image+%#x (%s)" % (d.how, d.addr, d.rel, d.resource))
        fh.write("  %04x  %08x  %-34s %s\n"
                 % (off, ins.word, ins.text(), ("; " + "  ".join(ann)) if ann else ""))
        prev = off


# ===========================================================================  CLI
def _print_calibration(rows: Sequence[dict]) -> int:
    ok = sum(1 for r in rows if r["arity_ok"] and r["name_ok"])
    print("CALIBRATION -- the 12 ops M3-opcode-table.json names, re-derived from the DLL alone")
    print("%3s %-26s %-26s %5s %5s %-7s %-5s %s"
          % ("op", "expected", "derived", "arity", "want", "kinds", "ret", "fn"))
    for r in rows:
        print("%3d %-26s %-26s %5d %5s %-7s %-5s %#07x %s"
              % (r["op"], r["expect_name"], r["derived_name"] or "-", r["arity"],
                 r["expect_arity"], r["kinds"] or "-", r["returns"], r["fn"],
                 "OK" if (r["arity_ok"] and r["name_ok"]) else "MISS"))
    print("re-derived %d/%d (name AND arity)" % (ok, len(rows)))
    return ok


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--calibrate", action="store_true",
                    help="re-derive the 12 known ops from the DLL and score the method")
    ap.add_argument("--hle-ops", metavar="OUT", nargs="?", const=HLE_OPS_JSON,
                    help="build the op dictionary (DLL + corpus) and write it here")
    ap.add_argument("--image", metavar="BLOB", help="data-ref map + function table for a container")
    ap.add_argument("--listing", metavar="DIR",
                    help="write annotated listings here (SCRATCH ONLY -- derived stock content)")
    args = ap.parse_args(argv)

    if args.calibrate:
        return 0 if _print_calibration(calibration(DllView())) == len(CALIBRATION_OPS) else 1

    if args.hle_ops:
        dll = DllView()
        cen, images = census_corpus()
        ops = rebuild_hle_ops(dll, cen)
        path = write_hle_ops(ops, args.hle_ops)
        hist = confidence_histogram(ops)
        print("wrote %s -- %d ops" % (path, len(ops)))
        print("confidence: high %d / medium %d / low %d / unnamed %d"
              % (hist["high"], hist["medium"], hist["low"], hist["unnamed"]))
        bad = check_confidence_rule(ops)
        print("confidence-rule violations: %d" % len(bad))
        for b in bad[:8]:
            print("   " + b)
        print("corpus: %d images, %d HLE call sites"
              % (len(images), sum(r["hle_calls"] for r in images)))
        return 0

    if args.image:
        ops = load_hle_ops() if os.path.isfile(HLE_OPS_JSON) else {}
        blob = open(args.image, "rb").read()
        src = os.path.splitext(os.path.basename(args.image))[0]
        if args.listing:
            os.makedirs(args.listing, exist_ok=True)
        for img in T.id3_images(blob, src):
            w, r = walk(img)
            refs = image_data_refs(img, w, r)
            seg = segment_functions(img, w, r, ops)
            print("\n%s  headerRel=%#x  %d instr  %d functions  %d data refs"
                  % (img.label, img.header_rel, len(r.instrs), len(seg.functions), len(refs)))
            for k, n in data_ref_summary(refs).most_common():
                print("   ref %-46s %d" % (k, n))
            print("   orphan instructions %d | shared %d | mid-function call targets %d"
                  % (len(seg.orphans), len(seg.shared), len(seg.midbody_targets)))
            for f in seg.functions[:40]:
                print("   %-10s %#06x %5d B %-16s sw=%d/%-4d hle=%-4d %-34s ops=%s"
                      % (f.label, f.start, f.size, f.role, f.switches, f.cases, f.hle_calls,
                         ",".join(f.tags) or "-",
                         ",".join(str(o) for o in f.hle_ops[:10]) or "-"))
            if args.listing:
                out = os.path.join(args.listing, "%s.asm" % img.label.replace(":", "_"))
                with open(out, "w", encoding="utf-8") as fh:
                    annotate_listing(img, w, r, seg, refs, ops, fh)
        return 0

    ap.error("give --calibrate, --hle-ops or --image")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
