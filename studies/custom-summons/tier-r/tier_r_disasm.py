"""TIER R rung 1 -- the reachability-driven MIPS R3000A + GTE disassembler for resource id-3 images.

WHAT THIS IS.  FF9's ``FF9SpecialEffectPlugin.dll`` carries a small **table-driven MIPS R3000A
interpreter**.  Every summon / special-effect container (``ef###.bytes``) can ship a *resource id 3*
payload: a PlayStation main-RAM image holding the effect's **program** -- the machine code that drives
the creature's bones, emits primitives, moves the native camera and calls back into the host through
an HLE trap.  This module turns that image into a readable listing.

THE GROUND TRUTH IS THE DLL'S OWN ISA TABLE, NOT A SPEC.  The plugin pre-decodes each word by walking
a 99-entry ``{u32 mask, u32 match, <name?>, extractor[], u8 flag}`` table at x64 RVA ``0x66c70``
(stride ``0x38``) and taking the **first** entry whose ``(word & mask) == match``; the matched index
*is* the interpreter's opcode id (``fn 0xd1a0`` @``0xd24e``-``0xd285``).  Operands are produced by the
per-entry extractor thunks at ``0xd0d0..0xd180`` -- eleven six-byte functions whose bodies are
transcribed verbatim into :class:`Ex` below.  ``flag == 1`` marks a **delay-slot-carrying control
transfer**: the interpreter checks that very flag (``0xebfb``: ``cmp word [rbx+2],0 / jne 0xecdf``) to
decide whether to *defer* a pending branch by one instruction.  So the delay-slot set is not our
opinion either -- it is a column of the shipping decode table.

:data:`ISA` is a committed mirror of that table (masks/matches are the public R3000A + PS1 GTE
encoding; no game bytes).  :func:`load_isa_from_dll` re-reads the real thing so a gate can prove the
mirror still matches the shipping interpreter, 99/99.

WHY REACHABILITY AND NEVER A LINEAR SWEEP.  ``[0, headerRel)`` is code **and embedded data**
(``V-C8`` measured 50.3 % / 62.0 % linear-decode rates on two images -- those are data blobs, not
broken code).  The 16-entry program table at ``headerRel+8`` gives real entry points, so the walk is
seeded from those and follows fall-through, both branch arms, and in-image ``J``/``JAL``; everything
it never reaches is reported as data, not decoded.

PROVENANCE.  Pure analysis code.  It reads the user's own installed DLL (read-only, never modified)
and caller-supplied blobs, and emits offsets, mnemonics and statistics.  **Disassembly listings of
stock images are derived stock content -- write them under the scratch tree, never into the repo.**

CLI::

    py tier_r_disasm.py --isa-check                      # mirror vs the live DLL, 99/99
    py tier_r_disasm.py <ef227.bytes>                    # per-image walk summary
    py tier_r_disasm.py <ef227.bytes> --listing OUTDIR   # full annotated listings (SCRATCH ONLY)
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------- sibling study modules
_HERE = os.path.dirname(os.path.abspath(__file__))
_DISASM_DIR = os.path.normpath(os.path.join(_HERE, "..", "thomas-swap", "disasm"))
if _DISASM_DIR not in sys.path:
    sys.path.insert(0, _DISASM_DIR)

#: Where the extracted stock ``ef###.bytes`` live.  LOCAL-ONLY, never committed; override for a
#: different extraction root.
SCRATCH_CORPUS = os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format")
OPCODE_TABLE_JSON = os.path.join(_DISASM_DIR, "M3-opcode-table.json")

DLL_ISA_TABLE_RVA = 0x66C70          # fn 0xd1a0 @0xd259: lea rsi,[rip+0x59a10]
DLL_ISA_STRIDE = 0x38
DLL_HLE_SENTINEL_TABLE_RVA = 0x68250  # .data: 216 dwords 0xFF000000|i
HLE_SENTINEL_MASK = 0xFF000000
HLE_OP_MASK = 0x3FFFFF                # 0xec38: and edx,0x3fffff
HLE_OP_COUNT = 216                    # 0xee98: cmp edx,0xd7 / ja

REG = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
       "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
       "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
       "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"]
R_RA = 31
ARG_REGS = (4, 5, 6, 7)               # $a0..$a3  (O32)
# O32 caller-saved: $v0,$v1,$a0-$a3,$t0-$t9,$at,$ra -- clobbered across a call.
CALLER_SAVED = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 24, 25, 31)


# --------------------------------------------------------------------------- operand extractors
class Ex(Enum):
    """The DLL's own operand thunks, transcribed from their (6-byte) bodies.

    Called as ``f(ecx = imageRelativePC, edx = word, r8 = &scratch) -> eax``.
    """
    RS = "rs"              # 0xd0d0  shr edx,0x15 ; and 0x1f
    RT = "rt"              # 0xd0e0  shr edx,0x10 ; and 0x1f
    RD = "rd"              # 0xd0f0  shr edx,0x0b ; and 0x1f
    SHAMT = "shamt"        # 0xd100  shr edx,6    ; and 0x1f
    CODE20 = "code20"      # 0xd110  shr edx,6    ; and 0xfffff
    SIMM = "simm"          # 0xd120  movzx dx ; sign-extend bit 15
    UIMM = "uimm"          # 0xd130  movzx dx
    JTARGET = "jtarget"    # 0xd140  (edx & 0x3ffffff) << 2   [then -= psxBaseLow @0xd2d0]
    COFUN = "cofun"        # 0xd150  edx & 0x1ffffff
    BTARGET = "btarget"    # 0xd160  pc + 4*(simm16 + 1)
    OFF_BASE = "off_base"  # 0xd180  eax = simm16 ; *r8 = (edx >> 0x15) & 0x1f   -> TWO operands


_EX_RVA = {                # for the DLL cross-check
    0xD0D0: Ex.RS, 0xD0E0: Ex.RT, 0xD0F0: Ex.RD, 0xD100: Ex.SHAMT, 0xD110: Ex.CODE20,
    0xD120: Ex.SIMM, 0xD130: Ex.UIMM, 0xD140: Ex.JTARGET, 0xD150: Ex.COFUN,
    0xD160: Ex.BTARGET, 0xD180: Ex.OFF_BASE,
}

_R, _T, _D, _S, _C20 = Ex.RS, Ex.RT, Ex.RD, Ex.SHAMT, Ex.CODE20
_SI, _UI, _JT, _CF, _BT, _OB = Ex.SIMM, Ex.UIMM, Ex.JTARGET, Ex.COFUN, Ex.BTARGET, Ex.OFF_BASE


@dataclass(frozen=True)
class IsaEntry:
    idx: int
    mask: int
    match: int
    ex: Tuple[Ex, ...]
    flag: int              # 1 == control transfer WITH a delay slot (the DLL's own column)
    name: str

    @property
    def is_transfer(self) -> bool:
        return self.flag == 1


def _e(idx, mask, match, ex, flag, name) -> IsaEntry:
    return IsaEntry(idx, mask, match, tuple(ex), flag, name)


#: The committed mirror of the DLL's 99-entry decode table @0x66c70, IN TABLE ORDER.
#: Order is load-bearing -- the decoder takes the FIRST match, which is why e.g. entry 4 ``move``
#: shadows entry 16 ``addu`` when rs==0, and why entries 35/36 (``li``) and 60 (``b``) can never be
#: reached at all (``addiu``/``ori``/``beq`` match first).  Masks/matches are the public MIPS R3000A +
#: PS1 GTE encoding; nothing here is game content.
ISA: Tuple[IsaEntry, ...] = (
    _e(0,  0xFFFFFFFF, 0x00000000, (),                 0, "nop"),
    _e(1,  0xFFE0003F, 0x00000000, (_D, _T, _S),       0, "sll"),
    _e(2,  0xFFE0003F, 0x00000003, (_D, _T, _S),       0, "sra"),
    _e(3,  0xFFE0003F, 0x00000002, (_D, _T, _S),       0, "srl"),
    _e(4,  0xFFE007FF, 0x00000021, (_D, _R),           0, "move"),
    _e(5,  0xFC1F07FF, 0x00000009, (_D, _R),           1, "jalr"),
    _e(6,  0xFC1FFFFF, 0x00000008, (_R,),              1, "jr"),
    _e(7,  0xFFFF07FF, 0x00000010, (_D,),              0, "mfhi"),
    _e(8,  0xFFFF07FF, 0x00000011, (_R,),              0, "mthi"),
    _e(9,  0xFFFF07FF, 0x00000012, (_D,),              0, "mflo"),
    _e(10, 0xFFFF07FF, 0x00000013, (_R,),              0, "mtlo"),
    _e(11, 0xFC00FFFF, 0x00000018, (_R, _T),           0, "mult"),
    _e(12, 0xFC00FFFF, 0x00000019, (_R, _T),           0, "multu"),
    _e(13, 0xFC00FFFF, 0x0000001A, (_R, _T),           0, "div"),
    _e(14, 0xFC00FFFF, 0x0000001B, (_R, _T),           0, "divu"),
    _e(15, 0xFC0007FF, 0x00000020, (_D, _R, _T),       0, "add"),
    _e(16, 0xFC0007FF, 0x00000021, (_D, _R, _T),       0, "addu"),
    _e(17, 0xFC0007FF, 0x00000024, (_D, _R, _T),       0, "and"),
    _e(18, 0xFC0007FF, 0x00000026, (_D, _R, _T),       0, "xor"),
    _e(19, 0xFC0007FF, 0x00000006, (_D, _T, _R),       0, "srlv"),
    _e(20, 0xFC0007FF, 0x00000022, (_D, _R, _T),       0, "sub"),
    _e(21, 0xFC0007FF, 0x00000023, (_D, _R, _T),       0, "subu"),
    _e(22, 0xFC0007FF, 0x00000027, (_D, _R, _T),       0, "nor"),
    _e(23, 0xFC0007FF, 0x00000025, (_D, _R, _T),       0, "or"),
    _e(24, 0xFC0007FF, 0x00000004, (_D, _T, _R),       0, "sllv"),
    _e(25, 0xFC0007FF, 0x0000002A, (_D, _R, _T),       0, "slt"),
    _e(26, 0xFC0007FF, 0x0000002B, (_D, _R, _T),       0, "sltu"),
    _e(27, 0xFC0007FF, 0x00000007, (_D, _T, _R),       0, "srav"),
    _e(28, 0xFC000000, 0x20000000, (_T, _R, _SI),      0, "addi"),
    _e(29, 0xFC000000, 0x24000000, (_T, _R, _SI),      0, "addiu"),
    _e(30, 0xFC000000, 0x28000000, (_T, _R, _SI),      0, "slti"),
    _e(31, 0xFC000000, 0x2C000000, (_T, _R, _UI),      0, "sltiu"),
    _e(32, 0xFC000000, 0x30000000, (_T, _R, _UI),      0, "andi"),
    _e(33, 0xFC000000, 0x34000000, (_T, _R, _UI),      0, "ori"),
    _e(34, 0xFC000000, 0x38000000, (_T, _R, _UI),      0, "xori"),
    _e(35, 0xFFE00000, 0x24000000, (_T, _SI),          0, "li"),       # shadowed by 29
    _e(36, 0xFFE00000, 0x34000000, (_T, _UI),          0, "li"),       # shadowed by 33
    _e(37, 0xFFE00000, 0x3C000000, (_T, _UI),          0, "lui"),
    _e(38, 0xFC000000, 0x80000000, (_T, _OB),          0, "lb"),
    _e(39, 0xFC000000, 0x84000000, (_T, _OB),          0, "lh"),
    _e(40, 0xFC000000, 0x88000000, (_T, _OB),          0, "lwl"),
    _e(41, 0xFC000000, 0x8C000000, (_T, _OB),          0, "lw"),
    _e(42, 0xFC000000, 0x90000000, (_T, _OB),          0, "lbu"),
    _e(43, 0xFC000000, 0x94000000, (_T, _OB),          0, "lhu"),
    _e(44, 0xFC000000, 0x98000000, (_T, _OB),          0, "lwr"),
    _e(45, 0xFC000000, 0xA0000000, (_T, _OB),          0, "sb"),
    _e(46, 0xFC000000, 0xA4000000, (_T, _OB),          0, "sh"),
    _e(47, 0xFC000000, 0xA8000000, (_T, _OB),          0, "swl"),
    _e(48, 0xFC000000, 0xAC000000, (_T, _OB),          0, "sw"),
    _e(49, 0xFC000000, 0xB8000000, (_T, _OB),          0, "swr"),
    _e(50, 0xFC000000, 0x08000000, (_JT,),             1, "j"),
    _e(51, 0xFC000000, 0x0C000000, (_JT,),             1, "jal"),
    _e(52, 0xFC000000, 0x10000000, (_R, _T, _BT),      1, "beq"),
    _e(53, 0xFC000000, 0x14000000, (_R, _T, _BT),      1, "bne"),
    _e(54, 0xFC1F0000, 0x04010000, (_R, _BT),          1, "bgez"),
    _e(55, 0xFC1F0000, 0x04000000, (_R, _BT),          1, "bltz"),
    _e(56, 0xFC1F0000, 0x04100000, (_R, _BT),          1, "bltzal"),
    _e(57, 0xFC1F0000, 0x04110000, (_R, _BT),          1, "bgezal"),
    _e(58, 0xFC1F0000, 0x18000000, (_R, _BT),          1, "blez"),
    _e(59, 0xFC1F0000, 0x1C000000, (_R, _BT),          1, "bgtz"),
    _e(60, 0xFFFF0000, 0x10000000, (_BT,),             1, "b"),        # shadowed by 52
    _e(61, 0xFC000000, 0xE8000000, (_T, _OB),          0, "swc2"),
    _e(62, 0xFC000000, 0xC8000000, (_T, _OB),          0, "lwc2"),
    _e(63, 0xFFE007FF, 0x48400000, (_T, _D),           0, "cfc2"),
    _e(64, 0xFFE007FF, 0x48C00000, (_T, _D),           0, "ctc2"),
    _e(65, 0xFE000000, 0x4A000000, (_CF,),             0, "cop2"),
    _e(66, 0xFC00003F, 0x0000000D, (_C20,),            0, "break"),
    _e(67, 0xFC000000, 0xE0000000, (_T, _OB),          0, "swc0"),
    _e(68, 0xFC000000, 0xE4000000, (_T, _OB),          0, "swc1"),
    _e(69, 0xFC000000, 0xEC000000, (_T, _OB),          0, "swc3"),
    _e(70, 0xFC000000, 0xC0000000, (_T, _OB),          0, "lwc0"),
    _e(71, 0xFC000000, 0xC4000000, (_T, _OB),          0, "lwc1"),
    _e(72, 0xFC000000, 0xCC000000, (_T, _OB),          0, "lwc3"),
    _e(73, 0xFFFF0000, 0x41000000, (_BT,),             1, "bc0f"),
    _e(74, 0xFFFF0000, 0x45000000, (_BT,),             1, "bc1f"),
    _e(75, 0xFFFF0000, 0x49000000, (_BT,),             1, "bc2f"),
    _e(76, 0xFFFF0000, 0x4D000000, (_BT,),             1, "bc3f"),
    _e(77, 0xFFFF0000, 0x41010000, (_BT,),             1, "bc0t"),
    _e(78, 0xFFFF0000, 0x45010000, (_BT,),             1, "bc1t"),
    _e(79, 0xFFFF0000, 0x49010000, (_BT,),             1, "bc2t"),
    _e(80, 0xFFFF0000, 0x4D010000, (_BT,),             1, "bc3t"),
    _e(81, 0xFFE007FF, 0x40000000, (_T, _D),           0, "mfc0"),
    _e(82, 0xFFE007FF, 0x40400000, (_T, _D),           0, "cfc0"),
    _e(83, 0xFFE007FF, 0x40800000, (_T, _D),           0, "mtc0"),
    _e(84, 0xFFE007FF, 0x40C00000, (_T, _D),           0, "ctc0"),
    _e(85, 0xFFE007FF, 0x44000000, (_T, _D),           0, "mfc1"),
    _e(86, 0xFFE007FF, 0x44400000, (_T, _D),           0, "cfc1"),
    _e(87, 0xFFE007FF, 0x44800000, (_T, _D),           0, "mtc1"),
    _e(88, 0xFFE007FF, 0x44C00000, (_T, _D),           0, "ctc1"),
    _e(89, 0xFFE007FF, 0x48000000, (_T, _D),           0, "mfc2"),
    _e(90, 0xFFE007FF, 0x48800000, (_T, _D),           0, "mtc2"),
    _e(91, 0xFFE007FF, 0x4C000000, (_T, _D),           0, "mfc3"),
    _e(92, 0xFFE007FF, 0x4C400000, (_T, _D),           0, "cfc3"),
    _e(93, 0xFFE007FF, 0x4C800000, (_T, _D),           0, "mtc3"),
    _e(94, 0xFFE007FF, 0x4CC00000, (_T, _D),           0, "ctc3"),
    _e(95, 0xFE000000, 0x42000000, (_CF,),             0, "cop0"),
    _e(96, 0xFE000000, 0x46000000, (_CF,),             0, "cop1"),
    _e(97, 0xFE000000, 0x4E000000, (_CF,),             0, "cop3"),
    _e(98, 0xFFFFFFFF, 0x0000000C, (),                 0, "syscall"),
)

#: Interpreter reality: ``fn 0xe210`` @0xe273-0xe288 does ``dec eax ; cmp eax,0x59 ; ja`` before the
#: 90-entry jump table @0xed18 -- so decode indices > 90 are silently skipped, and table slots
#: 0x42..0x57 point at the "next instruction" stub.  Only 0..90 can ever execute.
IMPLEMENTED_MAX_INDEX = 90

# Opcode ids the interpreter deliberately drops (jump-table entries pointing at the 0xebfb stub).
UNIMPLEMENTED_INDICES = frozenset(range(67, 89))


# --------------------------------------------------------------------------- GTE (COP2) cofun
# The 25-bit cofun immediate of a ``cop2`` instruction, per the PS1 GTE encoding:
#     [24:20] "fake" command number (naming only)   [19] sf     [18:17] mx
#     [16:15] v          [14:13] cv                 [10] lm     [5:0]  real command number
GTE_OPS = {
    0x01: "RTPS",  0x06: "NCLIP", 0x0C: "OP",    0x10: "DPCS",  0x11: "INTPL", 0x12: "MVMVA",
    0x13: "NCDS",  0x14: "CDP",   0x16: "NCDT",  0x1B: "NCCS",  0x1C: "CC",    0x1E: "NCS",
    0x20: "NCT",   0x28: "SQR",   0x29: "DCPL",  0x2A: "DPCT",  0x2D: "AVSZ3", 0x2E: "AVSZ4",
    0x30: "RTPT",  0x3D: "GPF",   0x3E: "GPL",   0x3F: "NCCT",
}
GTE_MX = ("Rot", "Light", "Color", "Rsvd")
GTE_V = ("V0", "V1", "V2", "IR")
GTE_CV = ("TR", "BK", "FC", "None")

#: The COP2-cofun words the shipping interpreter actually implements.  ``fn 0xeacd`` (dispatch table
#: @0xed18 slot 64 = decode index 65) does NOT field-decode: it compares the whole 25-bit cofun
#: against exactly these six constants and ``_wassert``s (0xeb3c -> 0x4a170, line 0x4e7) on anything
#: else.  So this set IS FF9's entire GTE surface.
DLL_GTE_COFUNS = {
    0x0180001: ("RTPS",  "fn 0x3e80 (vertex 0)"),
    0x0280030: ("RTPT",  "fn 0x3e80 x3 (vertices 0,1,2)"),
    0x0480012: ("MVMVA", "fn 0x3d60  sf=1 mx=Rot v=V0 cv=TR lm=0"),
    0x0780010: ("DPCS",  "fn 0x4b50"),
    0x1400006: ("NCLIP", "inlined cross product over SXY0/1/2 -> MAC0"),
    0x158002D: ("AVSZ3", "fn 0x48d0"),
}


def gte_fields(cofun: int) -> dict:
    """Decode a 25-bit COP2 cofun immediate into its named GTE fields."""
    op = cofun & 0x3F
    return {
        "cofun": cofun,
        "op": op,
        "name": GTE_OPS.get(op, "GTE_%02X" % op),
        "fake": (cofun >> 20) & 0x1F,
        "sf": (cofun >> 19) & 1,
        "mx": (cofun >> 17) & 3,
        "v": (cofun >> 15) & 3,
        "cv": (cofun >> 13) & 3,
        "lm": (cofun >> 10) & 1,
        "implemented": cofun in DLL_GTE_COFUNS,
    }


def gte_text(cofun: int) -> str:
    f = gte_fields(cofun)
    if f["name"] == "MVMVA":
        return "MVMVA sf=%d mx=%s v=%s cv=%s lm=%d" % (
            f["sf"], GTE_MX[f["mx"]], GTE_V[f["v"]], GTE_CV[f["cv"]], f["lm"])
    return "%s sf=%d lm=%d" % (f["name"], f["sf"], f["lm"])


# --------------------------------------------------------------------------- the decoder
@dataclass
class Instr:
    off: int                 # image-relative byte offset (== the interpreter's PC)
    word: int
    entry: Optional[IsaEntry]
    ops: Tuple[int, ...]     # operand values in the DLL's own extractor order
    psx_base: int

    @property
    def valid(self) -> bool:
        return self.entry is not None

    @property
    def name(self) -> str:
        return self.entry.name if self.entry else "<invalid>"

    @property
    def psx(self) -> int:
        """The PSX main-RAM address this instruction is mapped at."""
        return ((self.psx_base & 0x0FFFFFFF) + self.off) | (self.psx_base & 0xF0000000)

    def op(self, kind: Ex) -> Optional[int]:
        """The value of the first operand produced by extractor ``kind`` (None if absent)."""
        if not self.entry:
            return None
        i = 0
        for k in self.entry.ex:
            if k is kind:
                return self.ops[i]
            i += 2 if k is Ex.OFF_BASE else 1
        return None

    @property
    def base_reg(self) -> Optional[int]:
        """The base register of a load/store (the second value the OFF_BASE thunk writes)."""
        if not self.entry:
            return None
        i = 0
        for k in self.entry.ex:
            if k is Ex.OFF_BASE:
                return self.ops[i + 1]
            i += 1
        return None

    def text(self) -> str:
        """`mnemonic operands` in the DLL's operand order."""
        if not self.entry:
            return "<invalid %08x>" % self.word
        e = self.entry
        parts: List[str] = []
        i = 0
        for k in e.ex:
            v = self.ops[i]
            if k in (Ex.RS, Ex.RT, Ex.RD):
                parts.append("$" + REG[v])
            elif k is Ex.SHAMT:
                parts.append(str(v))
            elif k is Ex.SIMM:
                parts.append(str(v))
            elif k is Ex.UIMM:
                parts.append("0x%x" % v)
            elif k is Ex.CODE20:
                parts.append("0x%x" % v)
            elif k in (Ex.JTARGET, Ex.BTARGET):
                parts.append("0x%x" % (v & 0xFFFFFFFF))
            elif k is Ex.COFUN:
                parts.append("0x%07x" % v)
            elif k is Ex.OFF_BASE:
                parts.append("%d($%s)" % (v, REG[self.ops[i + 1]]))
                i += 1
            i += 1
        return "%-7s %s" % (e.name, ", ".join(parts))


def _sx16(v: int) -> int:
    return v - 0x10000 if v & 0x8000 else v


def _s32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v & 0x80000000 else v


class Decoder:
    """Greedy first-match decode against the ISA table, with the DLL's operand extraction."""

    def __init__(self, isa: Sequence[IsaEntry] = ISA):
        self.isa = tuple(isa)

    def classify(self, word: int) -> Optional[IsaEntry]:
        for e in self.isa:
            if (word & e.mask) == e.match:
                return e
        return None

    def decode(self, word: int, off: int, psx_base: int) -> Instr:
        e = self.classify(word)
        if e is None:
            return Instr(off, word, None, (), psx_base)
        ops: List[int] = []
        for k in e.ex:
            if k is Ex.RS:
                ops.append((word >> 21) & 0x1F)
            elif k is Ex.RT:
                ops.append((word >> 16) & 0x1F)
            elif k is Ex.RD:
                ops.append((word >> 11) & 0x1F)
            elif k is Ex.SHAMT:
                ops.append((word >> 6) & 0x1F)
            elif k is Ex.CODE20:
                ops.append((word >> 6) & 0xFFFFF)
            elif k is Ex.SIMM:
                ops.append(_sx16(word & 0xFFFF))
            elif k is Ex.UIMM:
                ops.append(word & 0xFFFF)
            elif k is Ex.JTARGET:
                # 0xd140 then the pre-decoder's `sub eax,[rdi]` @0xd2d0 -> image relative
                ops.append(_s32(((word & 0x3FFFFFF) << 2) - (psx_base & 0x0FFFFFFF)))
            elif k is Ex.COFUN:
                ops.append(word & 0x1FFFFFF)
            elif k is Ex.BTARGET:
                ops.append(_s32(off + 4 * (_sx16(word & 0xFFFF) + 1)))
            elif k is Ex.OFF_BASE:
                ops.append(_sx16(word & 0xFFFF))
                ops.append((word >> 21) & 0x1F)
        return Instr(off, word, e, tuple(ops), psx_base)


DEFAULT_DECODER = Decoder()


# --------------------------------------------------------------------------- the DLL cross-check
def load_isa_from_dll(pe=None) -> List[IsaEntry]:
    """Re-read the live 99-entry decode table out of ``FF9SpecialEffectPlugin.dll``.

    Names come from the committed mirror (the table itself carries no strings); everything else --
    mask, match, extractor list, flag -- is read from the file.  Raises if the DLL is unreachable.
    """
    import refkit  # local import: the DLL is optional for everything except this check
    pe = pe or refkit.load()
    ib = refkit.image_base(pe)
    out: List[IsaEntry] = []
    i = 0
    while True:
        d = pe.get_data(DLL_ISA_TABLE_RVA + i * DLL_ISA_STRIDE, DLL_ISA_STRIDE)
        mask, match = struct.unpack_from("<II", d, 0)
        if mask == 0:
            break
        ex: List[Ex] = []
        for k in range(4):
            q = struct.unpack_from("<Q", d, 0x10 + 8 * k)[0]
            if q == 0:
                break
            rva = q - ib
            if rva not in _EX_RVA:
                raise RuntimeError("unknown operand extractor at RVA %#x (entry %d)" % (rva, i))
            ex.append(_EX_RVA[rva])
        name = ISA[i].name if i < len(ISA) else "?"
        out.append(IsaEntry(i, mask, match, tuple(ex), d[0x30], name))
        i += 1
    return out


def isa_diff(live: Sequence[IsaEntry], mirror: Sequence[IsaEntry] = ISA) -> List[str]:
    """[] when the committed mirror reproduces the live table exactly."""
    problems: List[str] = []
    if len(live) != len(mirror):
        problems.append("entry count %d != %d" % (len(live), len(mirror)))
    for a, b in zip(live, mirror):
        if (a.mask, a.match, a.ex, a.flag) != (b.mask, b.match, b.ex, b.flag):
            problems.append(
                "entry %d: dll(mask=%08x match=%08x ex=%s flag=%d) != mirror(mask=%08x match=%08x "
                "ex=%s flag=%d)" % (a.idx, a.mask, a.match, [e.value for e in a.ex], a.flag,
                                    b.mask, b.match, [e.value for e in b.ex], b.flag))
    return problems


def load_hle_names(path: str = OPCODE_TABLE_JSON) -> Dict[int, str]:
    """{op -> name} for the 216 HLE ops (only 12 are named in M3-opcode-table.json)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            rows = json.load(fh)
    except OSError:
        return {}
    return {int(r["op"]): r["name"] for r in rows if r.get("name")}


def load_hle_arity(path: str = OPCODE_TABLE_JSON) -> Dict[int, int]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            rows = json.load(fh)
    except OSError:
        return {}
    return {int(r["op"]): int(r["arity"]) for r in rows if r.get("arity") is not None}


# --------------------------------------------------------------------------- abstract values
class Val:
    """Tiny lattice for the constant tracker.

    ``const(v)``  a statically known 32-bit value.
    ``load(a)``   loaded from the statically known address ``a``.
    ``slot(off)`` loaded at ``off`` from a base we cannot see -- the shape an **HLE call** has
                  (``lw $vX, 4*op($tableBase)``); ``src`` carries the base's own value so a chain
                  like ``sysStruct+0x10 -> +4*op`` stays visible in the listing.
    ``idx(base)`` a known constant plus an unknown -- an index into the table at ``base``.
    ``jtab(a)``   loaded from ``idx``: the shape a **switch jump table** has
                  (``sltiu / sll 2 / addu / lw / jr``), with ``a`` the table's PSX address.
    ``unk``       everything else.
    """
    __slots__ = ("kind", "v", "src")

    def __init__(self, kind: str, v: int = 0, src: Optional["Val"] = None):
        self.kind = kind      # "const" | "load" | "slot" | "idx" | "jtab" | "unk"
        self.v = v
        self.src = src

    def __eq__(self, o):
        return (isinstance(o, Val) and o.kind == self.kind and o.v == self.v
                and (self.src == o.src))

    def __hash__(self):
        return hash((self.kind, self.v))

    def __repr__(self):
        if self.kind == "unk":
            return "UNK"
        if self.kind == "slot":
            return "slot(+%#x of %r)" % (self.v, self.src)
        return "%s(%#x)" % (self.kind, self.v & 0xFFFFFFFF)


UNK = Val("unk")

#: The effect program reaches a host routine through a **function-pointer table**, not through an
#: immediate: ``lw $vX, (4*op)(tableBase)`` then ``jalr $vX``.  The loaded word is the DLL-synthesised
#: sentinel ``0xFF000000|op`` and the interpreter traps it at ``fn 0xec31``.  So the op index is
#: statically recoverable from the LOAD OFFSET alone -- no runtime probe needed.
#: ``tableBase`` itself is ``*(sysStruct + 0x10)``, and the DLL publishes the sentinel table's PSX
#: address to host RVA ``0x21FF78`` = ``0x21FF68 + 0x10`` (see R1-DISASSEMBLER.md G7).
HLE_STRUCT_FIELD = 0x10
HLE_MAX_OFFSET = 4 * HLE_OP_COUNT     # 0x360


def _const(v: int) -> Val:
    return Val("const", v & 0xFFFFFFFF)


# --------------------------------------------------------------------------- the walk
@dataclass
class CallSite:
    off: int
    kind: str                    # "in_image" | "hle" | "unresolved"
    via: str                     # "jal" | "jalr" | "j" | "jr"
    target: Optional[int] = None      # image offset for in_image
    hle_op: Optional[int] = None
    hle_name: Optional[str] = None
    args: Tuple[Optional[int], ...] = (None, None, None, None)
    detail: str = ""


@dataclass
class JumpTable:
    site: int                    # the `jr` that dispatches through it
    addr: int                    # the table's PSX address
    off: int                     # ... as an image offset
    targets: Tuple[int, ...]     # image offsets, in slot order
    bound: Optional[int]         # the `sltiu` case count, when one was found


@dataclass
class WalkResult:
    name: str                    # e.g. "ef227:c0"
    psx_base: int
    header_rel: int
    nbytes: int
    entries: Tuple[int, ...]     # the live program offsets that seeded the walk
    instrs: Dict[int, Instr] = field(default_factory=dict)
    jump_tables: List[JumpTable] = field(default_factory=list)
    delay_slots: set = field(default_factory=set)
    labels: Dict[int, str] = field(default_factory=dict)
    calls: List[CallSite] = field(default_factory=list)
    invalid: List[int] = field(default_factory=list)      # reachable words the ISA table rejects
    out_of_image: List[Tuple[int, int]] = field(default_factory=list)  # (site, target)
    anomalies: List[str] = field(default_factory=list)
    cofun_hist: Dict[int, int] = field(default_factory=dict)
    block_starts: set = field(default_factory=set)

    @property
    def reached_bytes(self) -> int:
        return 4 * len(self.instrs)

    @property
    def coverage(self) -> float:
        return self.reached_bytes / self.header_rel if self.header_rel else 0.0


class ImageWalker:
    """Reachability walk of one id-3 image, seeded from its 16-entry program table."""

    def __init__(self, payload: bytes, psx_base: int, header_rel: int,
                 program_offsets: Sequence[int], name: str = "?",
                 decoder: Decoder = DEFAULT_DECODER, hle_names: Optional[Dict[int, str]] = None):
        self.pay = payload
        self.psx_base = psx_base
        self.header_rel = header_rel
        self.progs = tuple(o for o in program_offsets if o)
        self.name = name
        self.dec = decoder
        self.hle_names = hle_names if hle_names is not None else load_hle_names()

    # -- helpers ----------------------------------------------------------
    def word(self, off: int) -> int:
        return struct.unpack_from("<I", self.pay, off)[0]

    def in_code(self, off: int) -> bool:
        return 0 <= off < self.header_rel and off + 4 <= len(self.pay)

    # -- the driver: reachability and the constant tracker feed each other ----
    def run(self, max_rounds: int = 8) -> WalkResult:
        """Walk, annotate, fold any recovered switch-table targets back in, repeat to a fixpoint."""
        seeds: Tuple[int, ...] = self.progs
        r = self.annotate(self.walk(seeds))
        for _ in range(max_rounds):
            found = tuple(t for jt in r.jump_tables for t in jt.targets)
            new = tuple(t for t in found if t not in r.instrs)
            if not new:
                break
            seeds = seeds + new
            r = self.annotate(self.walk(seeds))
        return r

    # -- pass 1: reachability --------------------------------------------
    def walk(self, seeds: Optional[Sequence[int]] = None) -> WalkResult:
        seeds = tuple(self.progs if seeds is None else seeds)
        r = WalkResult(self.name, self.psx_base, self.header_rel, len(self.pay), self.progs)
        for i, p in enumerate(self.progs):
            r.labels[p] = "prog%d" % i
            r.block_starts.add(p)
        for s in seeds:
            if s not in r.labels:
                r.labels[s] = "case_%04x" % s
            r.block_starts.add(s)
        stack = list(seeds)
        seen = set()
        while stack:
            off = stack.pop()
            if off in seen or not self.in_code(off):
                continue
            seen.add(off)
            ins = self._get(r, off)
            if ins.entry is None:
                r.invalid.append(off)
                continue
            if not ins.entry.is_transfer:
                nxt = off + 4
                if self.in_code(nxt):
                    stack.append(nxt)
                elif nxt < len(self.pay):
                    r.anomalies.append("fallthrough past headerRel at %#x" % off)
                continue

            # -- a control transfer: its DELAY SLOT always executes (DLL fn 0xe210 @0xebfb)
            slot = off + 4
            if self.in_code(slot):
                r.delay_slots.add(slot)
                sins = self._get(r, slot)
                seen.add(slot)
                if sins.entry is None:
                    r.invalid.append(slot)
                elif sins.entry.is_transfer:
                    r.anomalies.append("branch in delay slot at %#x" % slot)
            else:
                r.anomalies.append("delay slot outside code at %#x" % slot)

            for succ, why in self._successors(r, ins):
                if succ is None:
                    continue
                if self.in_code(succ):
                    r.block_starts.add(succ)
                    r.labels.setdefault(succ, "L_%04x" % succ)
                    stack.append(succ)
                else:
                    r.out_of_image.append((off, succ))
        # cofun histogram over reachable code only
        for ins in r.instrs.values():
            if ins.entry is not None and ins.entry.name == "cop2":
                c = ins.ops[0]
                r.cofun_hist[c] = r.cofun_hist.get(c, 0) + 1
        return r

    def _get(self, r: WalkResult, off: int) -> Instr:
        ins = r.instrs.get(off)
        if ins is None:
            ins = self.dec.decode(self.word(off), off, self.psx_base)
            r.instrs[off] = ins
        return ins

    def _successors(self, r: WalkResult, ins: Instr,
                    dataflow: bool = False) -> List[Tuple[Optional[int], str]]:
        """Successor offsets, applied AFTER the delay slot has executed.

        ``dataflow=True`` drops call edges (a callee gets a fresh, all-unknown entry state -- the
        register tracker is deliberately intra-procedural).
        """
        n = ins.entry.name
        off = ins.off
        if n == "j":
            return [(ins.ops[0], "j")]
        if n == "jal":
            return [(off + 8, "return")] if dataflow else [(ins.ops[0], "call"), (off + 8, "return")]
        if n == "jr":
            # $ra = a return (terminal after its slot); any other register is an indirect
            # transfer whose target pass 2 classifies -- the path stops here either way.
            return []
        if n == "jalr":
            return [(off + 8, "return")]        # indirect callee resolved in pass 2
        if n in ("bltzal", "bgezal"):
            t = ins.op(Ex.BTARGET)
            return [(off + 8, "fallthrough")] if dataflow else [(t, "call"), (off + 8, "fallthrough")]
        if n == "b":
            return [(ins.ops[0], "b")]
        # conditional branches (incl. BCzF/T)
        t = ins.op(Ex.BTARGET)
        return [(t, "taken"), (off + 8, "fallthrough")]

    # -- pass 2: constants + call classification --------------------------
    def annotate(self, r: WalkResult) -> WalkResult:
        blocks = self.blocks(r)
        preds: Dict[int, set] = {b: set() for b in blocks}
        for b, (_body, succs) in blocks.items():
            for s in succs:
                if s in preds:
                    preds[s].add(b)
        # BOTTOM (None, "not yet reached") must not be confused with TOP ({}, "everything unknown"):
        # running a block from BOTTOM poisons its successors with spurious UNKs.  Only blocks with no
        # dataflow predecessor -- function entries, since call edges are cut -- start at TOP.
        state_in: Dict[int, Optional[Dict[int, Val]]] = {b: None for b in blocks}
        work: List[int] = []
        for b in blocks:
            if not preds[b]:
                state_in[b] = {}
                work.append(b)
        rounds = 0
        limit = 60 * max(1, len(blocks)) + 1000
        while rounds < limit:
            while work and rounds < limit:
                rounds += 1
                b = work.pop()
                body, succs = blocks[b]
                out = self._run_block(r, body, dict(state_in[b] or {}))
                for s in succs:
                    if s not in state_in:
                        continue
                    merged = out if state_in[s] is None else _merge(state_in[s], out)
                    if state_in[s] is None or merged != state_in[s]:
                        state_in[s] = merged
                        work.append(s)
            left = [b for b in blocks if state_in[b] is None]
            if not left:
                break
            b = min(left)                     # an entry only a call/loop can reach
            state_in[b] = {}
            work.append(b)
        if work:
            r.anomalies.append("constant tracker hit its iteration cap (%d blocks)" % len(blocks))
        # final pass: record call sites against the settled entry states
        for b in sorted(blocks):
            body, _ = blocks[b]
            self._run_block(r, body, dict(state_in[b] or {}), record=True)
        r.calls.sort(key=lambda c: c.off)
        return r

    def blocks(self, r: WalkResult) -> Dict[int, Tuple[List[int], List[int]]]:
        """{blockStart: ([offsets in order, delay slot included], [dataflow successors])}.

        A control transfer and its delay slot END a block together -- the slot executes before the
        transfer takes effect, so it belongs to the block that owns the branch.
        """
        starts = set(p for p in self.progs if p in r.instrs)
        for off, ins in r.instrs.items():
            if off - 4 not in r.instrs:
                starts.add(off)
            if ins.entry is not None and ins.entry.is_transfer:
                starts.add(off + 8)
                for s, _why in self._successors(r, ins):
                    if s is not None:
                        starts.add(s)
        starts = {s for s in starts if s in r.instrs}

        blocks: Dict[int, Tuple[List[int], List[int]]] = {}
        for b in sorted(starts):
            body: List[int] = []
            succs: List[int] = []
            o = b
            while o in r.instrs:
                ins = r.instrs[o]
                body.append(o)
                if ins.entry is not None and ins.entry.is_transfer:
                    if o + 4 in r.instrs:
                        body.append(o + 4)       # the delay slot
                    for s, _why in self._successors(r, ins, dataflow=True):
                        if s is not None and s in r.instrs:
                            succs.append(s)
                    break
                o += 4
                if o in starts:
                    if o in r.instrs:
                        succs.append(o)
                    break
            else:
                pass
            blocks[b] = (body, succs)
        return blocks

    def _run_block(self, r: WalkResult, body: List[int], st: Dict[int, Val],
                   record: bool = False) -> Dict[int, Val]:
        st[0] = _const(0)
        transfer: Optional[Instr] = None
        for off in body:
            ins = r.instrs[off]
            if ins.entry is None:
                continue
            if ins.entry.is_transfer:
                transfer = ins            # deferred: its delay slot runs first
                continue
            self._step(r, ins, st)
            st[0] = _const(0)
        if transfer is not None:
            n = transfer.entry.name
            if n in ("jal", "jalr", "bltzal", "bgezal"):
                if record:
                    self._record_call(r, transfer, st)
                for reg in CALLER_SAVED:
                    st[reg] = UNK
                st[0] = _const(0)
            elif record and n == "jr" and transfer.ops[0] != R_RA:
                if not self._record_jump_table(r, transfer, st):
                    self._record_call(r, transfer, st)
        return st

    def _record_jump_table(self, r: WalkResult, ins: Instr, st: Dict[int, Val]) -> bool:
        """Recover a compiled ``switch``: ``sltiu N / sll 2 / addu base / lw / jr``.

        The table lives in the image, so its entries are readable statically.  Every entry is
        validated as a 4-aligned PSX pointer inside this image's own code window -- the read stops at
        the first word that is not one, which keeps an unbounded table from running into code.
        """
        v = st.get(ins.ops[0], UNK)
        if v.kind != "jtab":
            return False
        toff = (v.v & 0x0FFFFFFF) - (self.psx_base & 0x0FFFFFFF)
        if not (0 <= toff < len(self.pay)) or toff % 4:
            return False
        if any(jt.site == ins.off for jt in r.jump_tables):
            return True
        bound = self._switch_bound(r, ins.off)
        cap = bound if bound is not None else 64
        targets: List[int] = []
        for k in range(min(cap, (len(self.pay) - toff) // 4)):
            w = struct.unpack_from("<I", self.pay, toff + 4 * k)[0]
            if (w >> 28) != 8:
                break
            rel = (w & 0x0FFFFFFF) - (self.psx_base & 0x0FFFFFFF)
            if rel % 4 or not self.in_code(rel):
                break
            targets.append(rel)
        if not targets:
            return False
        r.jump_tables.append(JumpTable(ins.off, v.v, toff, tuple(targets), bound))
        return True

    def _switch_bound(self, r: WalkResult, site: int, window: int = 24) -> Optional[int]:
        """The ``sltiu $x, $idx, N`` case count guarding a switch dispatch, if it is in range."""
        for k in range(1, window + 1):
            o = site - 4 * k
            ins = r.instrs.get(o)
            if ins is None or ins.entry is None:
                break
            if ins.entry.name == "sltiu":
                n = ins.ops[2]
                return n if 0 < n <= 256 else None
        return None

    def _step(self, r: WalkResult, ins: Instr, st: Dict[int, Val]) -> None:
        if ins.entry is None:
            return
        n = ins.entry.name
        g = lambda reg: st.get(reg, UNK) if reg else _const(0)   # noqa: E731

        def put(reg: int, v: Val):
            if reg:
                st[reg] = v

        if n == "lui":
            put(ins.ops[0], _const(ins.ops[1] << 16))
        elif n in ("addiu", "addi"):
            a = g(ins.ops[1])
            put(ins.ops[0], _const(a.v + ins.ops[2]) if a.kind == "const" else UNK)
        elif n == "ori":
            a = g(ins.ops[1])
            put(ins.ops[0], _const(a.v | ins.ops[2]) if a.kind == "const" else UNK)
        elif n == "li":
            put(ins.ops[0], _const(ins.ops[1]))
        elif n == "andi":
            a = g(ins.ops[1])
            put(ins.ops[0], _const(a.v & ins.ops[2]) if a.kind == "const" else UNK)
        elif n == "xori":
            a = g(ins.ops[1])
            put(ins.ops[0], _const(a.v ^ ins.ops[2]) if a.kind == "const" else UNK)
        elif n == "move":
            put(ins.ops[0], g(ins.ops[1]))
        elif n in ("addu", "add", "or"):
            a, b = g(ins.ops[1]), g(ins.ops[2])
            if a.kind == "const" and b.kind == "const":
                put(ins.ops[0], _const(a.v + b.v if n != "or" else a.v | b.v))
            elif a.kind == "const" and a.v == 0:
                put(ins.ops[0], b)
            elif b.kind == "const" and b.v == 0:
                put(ins.ops[0], a)
            elif n != "or" and a.kind == "const" and b.kind == "unk":
                put(ins.ops[0], Val("idx", a.v))       # base + <unknown index>
            elif n != "or" and b.kind == "const" and a.kind == "unk":
                put(ins.ops[0], Val("idx", b.v))
            else:
                put(ins.ops[0], UNK)
        elif n == "sll":
            a = g(ins.ops[1])
            put(ins.ops[0], _const(a.v << ins.ops[2]) if a.kind == "const" else UNK)
        elif n == "lw":
            base = g(ins.base_reg)
            if base.kind == "const":
                put(ins.ops[0], Val("load", (base.v + ins.ops[1]) & 0xFFFFFFFF))
            elif base.kind == "idx":
                put(ins.ops[0], Val("jtab", (base.v + ins.ops[1]) & 0xFFFFFFFF))
            else:
                # the shape an HLE call has: lw $vX, (4*op)($tableBase)
                put(ins.ops[0], Val("slot", ins.ops[1], base))
        elif n in ("lb", "lh", "lbu", "lhu", "lwl", "lwr", "lwc0", "lwc1", "lwc2", "lwc3",
                   "mfhi", "mflo", "mfc0", "mfc1", "mfc2", "mfc3", "cfc0", "cfc1", "cfc2", "cfc3"):
            put(ins.ops[0], UNK)
        elif n in ("sb", "sh", "sw", "swl", "swr", "swc0", "swc1", "swc2", "swc3",
                   "mtc0", "mtc1", "mtc2", "mtc3", "ctc0", "ctc1", "ctc2", "ctc3",
                   "mthi", "mtlo", "mult", "multu", "div", "divu", "break", "syscall", "nop",
                   "cop0", "cop1", "cop2", "cop3"):
            pass
        else:
            # every remaining ALU form writes its first operand
            if ins.entry.ex and ins.entry.ex[0] in (Ex.RD, Ex.RT):
                put(ins.ops[0], UNK)

    def _record_call(self, r: WalkResult, ins: Instr, st: Dict[int, Val]) -> None:
        n = ins.entry.name
        args = tuple((st.get(a, UNK).v if st.get(a, UNK).kind == "const" else None)
                     for a in ARG_REGS)
        if n == "jal":
            tgt = ins.ops[0]
            kind = "in_image" if self.in_code(tgt) else "unresolved"
            r.calls.append(CallSite(ins.off, kind, "jal", target=tgt, args=args,
                                    detail="" if kind == "in_image" else "jal target outside code"))
            return
        rs = ins.ops[1] if n == "jalr" else ins.ops[0]
        v = st.get(rs, UNK)
        via = "jalr" if n == "jalr" else "jr"
        if v.kind == "const":
            k = v.v
            if (k & HLE_SENTINEL_MASK) == HLE_SENTINEL_MASK:
                op = k & HLE_OP_MASK
                r.calls.append(CallSite(ins.off, "hle", via, hle_op=op,
                                        hle_name=self.hle_names.get(op), args=args,
                                        detail="immediate sentinel %#010x" % k))
                return
            rel = (k & 0x0FFFFFFF) - (self.psx_base & 0x0FFFFFFF)
            if self.in_code(rel):
                r.calls.append(CallSite(ins.off, "in_image", via, target=rel, args=args,
                                        detail="psx %#010x" % k))
                return
            r.calls.append(CallSite(ins.off, "unresolved", via, args=args,
                                    detail="const %#010x (outside this image)" % k))
            return
        if v.kind == "slots":
            offs = sorted(v.src or ())
            if offs and all(0 <= o < HLE_MAX_OFFSET and o % 4 == 0 for o in offs):
                ops = [o // 4 for o in offs]
                r.calls.append(CallSite(
                    ins.off, "hle_multi", via, hle_op=None, args=args,
                    hle_name="|".join(self.hle_names.get(o, "HLE_%d" % o) for o in ops),
                    detail="merge of %d paths: table[%s]" % (
                        len(ops), ",".join(str(o) for o in ops))))
                return
            r.calls.append(CallSite(ins.off, "unresolved", via, args=args,
                                    detail="fn-ptr merge over offsets %s" % offs))
            return
        if v.kind == "slot":
            off, src = v.v, v.src
            if off >= 0 and off % 4 == 0 and off < HLE_MAX_OFFSET:
                op = off // 4
                chain = "table[%d] (+%#x)" % (op, off)
                if src is not None and src.kind == "slot":
                    chain += " base=*(+%#x)" % src.v
                    if src.v == HLE_STRUCT_FIELD:
                        chain += " = sysStruct+0x10 (the sentinel table)"
                r.calls.append(CallSite(ins.off, "hle", via, hle_op=op,
                                        hle_name=self.hle_names.get(op), args=args, detail=chain))
                return
            r.calls.append(CallSite(ins.off, "unresolved", via, args=args,
                                    detail="fn-ptr load at +%#x (not an HLE table slot)" % off))
            return
        if v.kind == "load":
            rel = (v.v & 0x0FFFFFFF) - (self.psx_base & 0x0FFFFFFF)
            where = " (image+%#x)" % rel if 0 <= rel < len(self.pay) else ""
            r.calls.append(CallSite(ins.off, "unresolved", via, args=args,
                                    detail="fn ptr loaded from %#010x%s" % (v.v, where)))
            return
        r.calls.append(CallSite(ins.off, "unresolved", via, args=args,
                                detail="dynamic $%s" % REG[rs]))


def _slot_offsets(v: Val) -> Optional[frozenset]:
    if v.kind == "slot":
        return frozenset((v.v,))
    if v.kind == "slots":
        return v.src
    return None


def _join(va: Val, vb: Val) -> Val:
    """Lattice join.  Two *different* table slots surviving a merge is not noise: it is a call site
    two paths reach with two different ops (polymorphic dispatch), and both ops stay nameable."""
    if va == vb:
        return va
    sa, sb = _slot_offsets(va), _slot_offsets(vb)
    if sa is not None and sb is not None:
        return Val("slots", 0, sa | sb)
    return UNK


def _merge(a: Dict[int, Val], b: Dict[int, Val]) -> Dict[int, Val]:
    if not a:
        return dict(b)
    out: Dict[int, Val] = {}
    for k in set(a) | set(b):
        out[k] = _join(a.get(k, UNK), b.get(k, UNK))
    return out


# --------------------------------------------------------------------------- container glue
@dataclass
class Id3Image:
    source: str
    chunk_slot: int
    psx_base: int
    header_rel: int
    payload: bytes
    program_offsets: Tuple[int, ...]

    @property
    def label(self) -> str:
        return "%s:c%d" % (self.source, self.chunk_slot)

    @property
    def live_programs(self) -> Tuple[int, ...]:
        return tuple(o for o in self.program_offsets if o)


def id3_images(blob: bytes, source: str = "?") -> List[Id3Image]:
    """Every resource-id-3 image in one container, via ef_container (the sanctioned parser)."""
    import ef_container as ec
    c = ec.parse_header(blob)
    out: List[Id3Image] = []
    for ch in c.chunks:
        for res in ch.resources:
            if res.id != 3:
                continue
            img = ec.parse_chunk_image(blob, res, ch.psx_base)
            out.append(Id3Image(source, ch.slot, ch.psx_base, img.header_rel,
                                blob[res.offset:res.offset + res.nbytes],
                                tuple(img.program_offsets)))
    return out


def walk_image(img: Id3Image, decoder: Decoder = DEFAULT_DECODER,
               hle_names: Optional[Dict[int, str]] = None) -> WalkResult:
    w = ImageWalker(img.payload, img.psx_base, img.header_rel, img.live_programs,
                    name=img.label, decoder=decoder, hle_names=hle_names)
    return w.run()


def corpus_images(root: str = SCRATCH_CORPUS) -> Iterable[Id3Image]:
    """Every id-3 image in the extracted corpus, in file order."""
    import glob
    for p in sorted(glob.glob(os.path.join(root, "ef*.bytes"))):
        blob = open(p, "rb").read()
        for img in id3_images(blob, os.path.splitext(os.path.basename(p))[0]):
            yield img


def region_runs(img: Id3Image, r: WalkResult, decoder: Decoder = DEFAULT_DECODER,
                code_cut: float = 0.95) -> List[Tuple[int, int, str]]:
    """Split ``[0, headerRel)`` into runs: reached | unreached-code-shaped | data-shaped.

    A run the walk never entered is called "data-shaped" when the ISA table rejects more than
    ``1 - code_cut`` of its words -- the same measurement V-C8 used to spot the embedded blobs in
    ef508/ef210.  This is a *description* of what the walk left behind, never a decode strategy.
    """
    out: List[Tuple[int, int, str]] = []
    cur_start, cur_kind = 0, None
    for o in range(0, img.header_rel - 3, 4):
        kind = "reached" if o in r.instrs else "unreached"
        if cur_kind is None:
            cur_start, cur_kind = o, kind
        elif kind != cur_kind:
            out.append((cur_start, o, cur_kind))
            cur_start, cur_kind = o, kind
    if cur_kind is not None:
        out.append((cur_start, ((img.header_rel - 3) // 4) * 4 + 4, cur_kind))
    final: List[Tuple[int, int, str]] = []
    for a, b, kind in out:
        if kind == "reached":
            final.append((a, b, kind))
            continue
        words = [struct.unpack_from("<I", img.payload, o)[0] for o in range(a, b, 4)]
        ok = sum(1 for w in words if decoder.classify(w) is not None) / max(1, len(words))
        final.append((a, b, "unreached_code" if ok >= code_cut else "data"))
    return final


def linear_score(img: Id3Image, decoder: Decoder = DEFAULT_DECODER) -> float:
    """The ANTI-pattern's score: fraction of `[4, headerRel)` words a linear sweep accepts.

    Kept as a measurement, never as a decode strategy -- the gap between this and the reachable
    coverage is exactly the embedded-data mass the walker must refuse to swallow.
    """
    ok = tot = 0
    for o in range(4, img.header_rel - 3, 4):
        tot += 1
        if decoder.classify(struct.unpack_from("<I", img.payload, o)[0]) is not None:
            ok += 1
    return ok / tot if tot else 0.0


# --------------------------------------------------------------------------- listing writer
def write_listing(r: WalkResult, fh, hle_names: Optional[Dict[int, str]] = None) -> None:
    """addr | raw word | mnemonic+operands | annotation.  SCRATCH-ONLY for stock images."""
    hle_names = hle_names if hle_names is not None else load_hle_names()
    calls = {c.off: c for c in r.calls}
    fh.write("; %s  psxBase=%#010x headerRel=%#x  entries=%s\n"
             % (r.name, r.psx_base, r.header_rel,
                ", ".join("%#x" % e for e in r.entries)))
    fh.write("; reachable %d instr (%d B) = %.2f%% of the code region; %d delay slots; "
             "%d calls; %d invalid\n"
             % (len(r.instrs), r.reached_bytes, 100 * r.coverage, len(r.delay_slots),
                len(r.calls), len(r.invalid)))
    prev = None
    for off in sorted(r.instrs):
        if prev is not None and off != prev + 4:
            fh.write("        ---- %#x bytes of data / unreached code ----\n" % (off - prev - 4))
        ins = r.instrs[off]
        lab = r.labels.get(off)
        if lab:
            fh.write("%s:\n" % lab)
        ann: List[str] = []
        if off in r.delay_slots:
            ann.append("[delay slot]")
        if ins.entry is not None:
            if ins.entry.name == "cop2":
                ann.append("GTE " + gte_text(ins.ops[0]))
                if ins.ops[0] not in DLL_GTE_COFUNS:
                    ann.append("!! not implemented by the DLL")
            tgt = ins.op(Ex.BTARGET)
            if tgt is None and ins.entry.name in ("j", "jal"):
                tgt = ins.ops[0]
            if tgt is not None and tgt in r.labels:
                ann.append("-> %s" % r.labels[tgt])
        c = calls.get(off)
        if c is not None:
            if c.kind == "hle":
                nm = c.hle_name or "HLE_%d" % c.hle_op
                ann.append("HLE %s (op %d)" % (nm, c.hle_op))
            elif c.kind == "in_image":
                ann.append("call %#x" % c.target)
            else:
                ann.append("call UNRESOLVED (%s)" % c.detail)
            shown = [("$a%d=%#x" % (i, v)) for i, v in enumerate(c.args) if v is not None]
            if shown:
                ann.append(" ".join(shown))
        fh.write("  %04x  %08x  %-34s %s\n"
                 % (off, ins.word, ins.text(), ("; " + "  ".join(ann)) if ann else ""))
        prev = off


# --------------------------------------------------------------------------- CLI
def _iter_corpus(root: str = SCRATCH_CORPUS):
    import glob
    for p in sorted(glob.glob(os.path.join(root, "ef*.bytes"))):
        yield p


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("blobs", nargs="*", help="ef###.bytes containers (SCRATCH)")
    ap.add_argument("--isa-check", action="store_true",
                    help="verify the committed ISA mirror against the live DLL and exit")
    ap.add_argument("--listing", metavar="DIR",
                    help="write full annotated listings here (SCRATCH ONLY -- derived stock content)")
    ap.add_argument("--corpus", action="store_true", help="run over the whole SCRATCH corpus")
    args = ap.parse_args(argv)

    if args.isa_check:
        live = load_isa_from_dll()
        problems = isa_diff(live)
        print("live ISA entries: %d   mirror: %d" % (len(live), len(ISA)))
        for p in problems:
            print("  MISMATCH", p)
        print("ISA mirror %s" % ("MATCHES the shipping table" if not problems else "DIVERGES"))
        return 0 if not problems else 1

    paths = list(args.blobs)
    if args.corpus:
        paths += list(_iter_corpus())
    if not paths:
        ap.error("give a blob path or --corpus / --isa-check")

    if args.listing:
        os.makedirs(args.listing, exist_ok=True)
    hle = load_hle_names()
    for p in paths:
        blob = open(p, "rb").read()
        src = os.path.splitext(os.path.basename(p))[0]
        for img in id3_images(blob, src):
            r = walk_image(img, hle_names=hle)
            print("%-12s headerRel=%#-8x progs=%-2d reach=%5d instr %6.2f%%  linear=%5.1f%%  "
                  "calls(in=%d hle=%d unres=%d) invalid=%d"
                  % (img.label, img.header_rel, len(img.live_programs), len(r.instrs),
                     100 * r.coverage, 100 * linear_score(img),
                     sum(1 for c in r.calls if c.kind == "in_image"),
                     sum(1 for c in r.calls if c.kind == "hle"),
                     sum(1 for c in r.calls if c.kind == "unresolved"), len(r.invalid)))
            if args.listing:
                out = os.path.join(args.listing, "%s.asm" % img.label.replace(":", "_"))
                with open(out, "w", encoding="utf-8") as fh:
                    write_listing(r, fh, hle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
