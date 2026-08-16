"""body_ops -- THE HANDLER-BODY EVIDENCE CLASS.  Six ops: 117, 206, 136 and the RNG family 48/49/50.

**ops 48 / 49 / 50** are one algorithm wearing three hats, and the algorithm names itself: each
drives ``seed = seed*0x41C64E6D + 0x3039 ; value = seed >> 16`` on the shared state ``0x3231dc``, and
that multiplier/increment pair is the **ANSI C ``rand()`` LCG**.  See :func:`verify_rng`.

**op 136** (510 sites) is four instructions -- look an actor up, divide one of its fields by 6, add
the caller's base -- and the body alone would not name it.  WHERE THE RESULT GOES does: the corpus
stores it into an op-117 instance's ``+0x22``, and the per-tick function loads ``+0x20``/``+0x22``
TOGETHER into GTE input slots and projects them.  So it is a COORDINATE component placed relative to
an actor, not the sort key it first looks like.  See :func:`verify_coord`.

**op 206** is the cheap half and it ships at ``high``: ``fn 0x47290`` asserts the ``'so'`` magic,
branches on ``u16[operand+2]``, ORs the PSX TPAGE **ABR** field into every binding on the non-zero
arm, and TAIL-CALLS one of two functions the DLL names itself -- ``Hi_RegisterTexListModel`` or
``Hi_RegisterGouEffModel``.  R2 missed it only because it resolves names on an op's OWN function and
a tail call hides the callee.  The name is their disjunction because that is what the op IS, and the
ABR half independently reproduces ``A1-TEXTURES.md`` §3.5 -- a claim derived months earlier by a
different method.  See :func:`verify_abr`, :func:`so_reading` and §ADDENDUM 2 of the report.

**op 117** is the expensive half, below.

R2's four static sources and R4's managed-ABI source between them name 107 of 216 ops.  Neither
reaches **op 117**, which at **1,709 call sites is the single most-called op in the corpus** (12% of
all HLE traffic) and does not touch the callback slot at all.  Naming it needs the expensive lane:
read the handler body.

WHAT THE BODY SAYS.  ``op 117``'s native function ``0x306f0`` is a THIN FORWARDER -- it shuffles the
two arguments into ``r8``/``r9`` and TAIL-JUMPS to ``0x34380`` with a pool descriptor and a context
object.  (That tail jump also hides the callee from R2's name resolver, which only looks at names
owned by an op's own function -- see :func:`tailjump_name_gap`.)  ``0x34380`` then:

  1. scans a pool of **0x6C-byte records** (descriptor ``0x3210d0``: count at +0, high-water at +8,
     array at +0x10) for one whose ``+0x30`` is zero, and **returns 0 when the pool is full**;
  2. zeroes the record, marks ``+0x30 = 1``, and binds it a **0x1FE0-byte work buffer** carved from
     the static array at ``0x587520`` by slot index;
  3. converts the caller's blob pointer to a PSX address (``fn 0x12940`` against ``psxBankTable``)
     and stores it at ``+0x00``;
  4. **RELOCATES the blob**: header ``0x10`` if ``blob[0] == 0xff`` else ``0x28``; ``u16`` count at
     ``+0x04``; a ``0x28``-stride entry array at ``+0x14``; per entry, ``byte+0x00 != 9`` promotes
     ``u32 +0x1c`` and ``byte+0x01 != 0xff`` promotes ``u32 +0x20`` from a blob-relative offset
     (bounded ``<= 0x27ff``) to an absolute PSX address;
  5. records the table's start/end at ``+0x18``/``+0x24``, the second argument at ``+0x28`` AND
     ``+0x2c`` (a cursor and its base), and returns the record.

THE FAMILY.  ``0x3210d0`` and the context object ``0x211e68`` are referenced by exactly the same six
functions, four of which are consecutive ops on consecutive addresses -- **116 (``()->void``, a pool
reset), 117 (open), 118 (``(pp)->void``), 119 (``(p)->void``, which marks ``+0x30 = -1`` and walks a
second table restoring a saved byte on every slot bound to the handle)**.  Open / operate / close.

THE CORPUS AGREES, and the tests below are the ones that could have refuted it:

  * **1,680 of 1,709 call sites (98.3%)** are immediately preceded by ``op 102 get_subfile_ptr``
    with a constant index -- the first argument is a sub-file pointer, essentially always.
  * the relocator's structural reading validates on **62.2%** of the sub-files the corpus actually
    feeds to op 117, against **6.4%** for every other sub-file in the same chunks -- a ~10x
    separation, the same shape of evidence that named op 102.
  * **0 of 759 camera sub-files** across 356 containers are ever fed to op 117: this is not the
    camera lane.

WHAT IS DELIBERATELY NOT CLAIMED.  38% of the fed sub-files do NOT satisfy the reading, and relaxing
the sub-file bound does not recover them (62.2% either way), so there is real structure here that
this pass does not model -- more header variants than the one ``blob[0] == 0xff`` discriminator.
The name therefore describes the MECHANISM (open a pooled instance of a sub-file, relocating its
internal offsets) and **not the content domain**, and it ships at ``medium``: no symbol anywhere in
the chain supplies it.  R2's contract reserves ``high`` for a name a source actually states.

    py studies/custom-summons/tier-r/body_ops.py            # verify + report
    py studies/custom-summons/tier-r/body_ops.py --gates    # + the corpus A/B (needs SCRATCH)
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import struct
import sys
from typing import Dict, List, Optional, Sequence, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import tier_r_annot as A

#: The marker that makes a body-derived evidence line greppable in ``hle_ops.json``.
BODY_MARKER = "handler-body:"

# --- the structural facts this module VERIFIES before it will name anything -------------------
OP_OPEN = 117
FORWARDER = 0x306F0          # op 117's native function
RELOCATOR = 0x34380          # its tail-jump target -- where the work is
POOL_DESC = 0x3210D0         # count +0, high-water +8, record array +0x10
CTX_OBJECT = 0x211E68        # the family's context object (count +0, array +0x10)
WORK_ARRAY = 0x587520        # 0x1FE0 bytes per slot
RECORD_STRIDE = 0x6C
WORK_SIZE = 0x1FE0
FAMILY_OPS = (116, 117, 118, 119)

#: The relocator's own reading of a blob, as constants (mirrored by :func:`relocator_reading`).
HDR_FLAG_BYTE = 0xFF
HDR_SMALL, HDR_LARGE = 0x10, 0x28
COUNT_OFF = 0x04
TABLE_OFF = 0x14
ENTRY_STRIDE = 0x28
PTR_FIELDS = ((0x00, 0x09, 0x1C), (0x01, 0xFF, 0x20))   # (kind byte, sentinel, pointer field)
OFFSET_MAX = 0x27FF

NAME = "subfile_instance_open"
DESCRIPTION = ("open a pooled runtime instance of a sub-file, relocating the sub-file's internal "
               "offset table to absolute PSX addresses; returns the record, or NULL when the pool "
               "is full")

# --- op 206: the ABR setter + model registrar (a VARIANT DISPATCHER) ---------------------------
#: Unlike op 117, this one's identity is stated by the DLL -- twice.  ``fn 0x47290`` asserts the
#: ``'so'`` magic, optionally ORs the PSX TPAGE **ABR** (semi-transparency) field into every binding,
#: and then TAIL-CALLS one of two functions that each own a debug-string name.  R2 never saw either,
#: because it resolves names on an op's OWN function and a tail call hides the callee.
OP_ABR = 206
ABR_FN = 0x47290
SO_MAGIC = 0x6F73                 # 'so', asserted at u16[arg0+0]
SO_VARIANT_OFF = 0x02             # u16: non-zero -> tex-list, zero -> gouraud
SO_LEN_OFF = 0x04                 # u16: record length; entries = (len - 8) / 8
SO_TABLE_OFF = 0x08               # {u16 tpage, u16 clut} pairs; the ABR ORs into the tpage
ABR_MASK, ABR_SHIFT = 0x3, 5      # (arg1 & 3) << 5 -- the PSX TPAGE ABR field
TEXLIST_FN = 0x15D30              # owns Hi_RegisterTexListModel
GOURAUD_FN = 0x15B70              # owns Hi_RegisterGouEffModel
NAME_ABR = "Hi_RegisterTexListModel|Hi_RegisterGouEffModel"
DESCRIPTION_ABR = ("OR the PSX TPAGE ABR (semi-transparency) field into every binding of an 'so' "
                   "table, then register the model -- tex-list variant when u16[+2] is non-zero, "
                   "gouraud variant when it is zero")


# --- op 136: a coordinate placed relative to an actor -----------------------------------------
#: ``fn 0x45a80`` is four instructions of work: look the actor up, divide one of its fields by 6
#: (the classic ``0xAAAAAAAB`` / ``shr 2`` unsigned magic), add the caller's base.  What names it is
#: not the body but WHERE THE RESULT GOES -- the corpus stores it into an op-117 instance's ``+0x22``,
#: and the per-tick function loads ``+0x20``/``+0x22`` TOGETHER into GTE input slots and projects
#: them.  So ``+0x22`` is a coordinate component, and op 136 places it relative to an actor.
OP_COORD = 136
COORD_FN = 0x45A80
ACTOR_LOOKUP = 0x44A60         # idx<8 party (count ctx+0x24) / 8..15 enemies (ctx+0x27) / 0x10,0x11
ACTOR_FIELD = 0x38             # the u32 this op divides
COORD_DIVISOR = 6
DIV_MAGIC = 0xAAAAAAAB         # unsigned /6: mul then shr edx, 2
INSTANCE_COORD_OFF = 0x22      # where the corpus stores the result, on an op-117 record
NAME_COORD = "actor_relative_coord"
DESCRIPTION_COORD = ("a coordinate component placed relative to an actor: base + "
                     "actor[+0x38] / 6")


# --- op 143: AddPrim, with an optional blend-mode prefix ----------------------------------------
#: ``fn 0x3edb0`` is libgpu's **``addPrim``** and op 143 exposes it directly (op 64 reaches the same
#: function eight times per call).  Two halves:
#:
#:   1. **the splice** -- length into the tag's top byte (``shr ecx, 0x18`` ; ``mov [r8+3], cl``),
#:      then the standard PS1 ordering-table insert, XOR-swapping only the low **24 bits** of
#:      ``*ot`` and ``prim->tag`` so each word keeps its own top byte;
#:   2. **the blend prefix** -- unless ``arg3 == 0xFF``, it carves **8 more bytes** off the arena
#:      cursor, builds a 2-word primitive (length 1) whose payload is
#:      ``0xE1000200 | ((arg3 & 3) << 5)``, and splices THAT in too.
#:
#: ``0xE1`` is the PS1 GPU **GP0 Draw Mode** command: bits 5-6 are the semi-transparency (**ABR**)
#: mode and bit 9 is dither -- i.e. a ``DR_TPAGE``, the state primitive the s76 probe already logs.
#: Because ``addPrim`` inserts at the HEAD, the prefix is drawn FIRST: set the blend, then draw.
#:
#: ** THIS CORRECTS THE OP 64 READING.**  op 64 passes its ``arg1`` straight into this parameter, so
#: ``arg1`` is a **BLEND MODE, not an OT depth** -- and its corpus profile fits that far better:
#: ``1(x254)`` is ABR 1, PS1 **additive** blending, exactly what a VFX flash wants; ``0`` is 50/50,
#: ``2`` subtractive, and ``255`` means "opaque, emit no draw-mode primitive at all".  There is no
#: depth argument anywhere: the OT POINTER is the depth, as PS1 code always does it (``&ot[z]``).
OP_ADDPRIM = 143
ADDPRIM_LINK_MASK = 0xFFFFFF      # the OT link is 24 bits; the top byte is the length
ADDPRIM_TAG_SHIFT = 0x18
DR_TPAGE_BASE = 0xE1000200        # GP0(E1h) Draw Mode + dither (bit 9)
DR_TPAGE_ABR_SHIFT = 5            # bits 5-6 = semi-transparency mode
DR_TPAGE_BYTES = 8                # a 2-word primitive: tag + one payload word
BLEND_NONE = 0xFF                 # arg3 == 0xff -> opaque, no draw-mode primitive
NAME_ADDPRIM = "add_prim_blended"
DESCRIPTION_ADDPRIM = ("link a primitive into the ordering table (libgpu addPrim: length into the "
                       "tag's top byte, 24-bit XOR splice) and, unless arg3 == 0xff, prepend an "
                       "8-byte DR_TPAGE draw-mode primitive setting the PS1 semi-transparency mode "
                       "to arg3 & 3")


def verify_addprim(dll: Optional[A.DllView] = None) -> Tuple[bool, List[str]]:
    """Re-derive both halves of op 143 -- the OT splice and the DR_TPAGE blend prefix."""
    dll = dll or A.DllView()
    notes: List[str] = []
    ok = True

    fn = dll.function_of(dll.native_fn[OP_ADDPRIM]) or dll.native_fn[OP_ADDPRIM]
    good = fn == ADDPRIM_FN
    ok &= good
    notes.append("op %d native fn = %#x (the same function op 64 calls) %s"
                 % (OP_ADDPRIM, fn, "OK" if good else "FAIL"))

    text = [(i.mnemonic, i.op_str) for i in dll.body(fn)]
    checks = (
        ("takes the length from the tag's top byte",
         ("shr", "ecx, 0x%x" % ADDPRIM_TAG_SHIFT) in text and ("mov", "byte ptr [r8 + 3], cl") in text),
        ("splices through a %d-bit OT link" % ADDPRIM_LINK_MASK.bit_length(),
         ("and", "eax, 0x%x" % ADDPRIM_LINK_MASK) in text),
        ("skips the blend prefix when arg3 == %#x" % BLEND_NONE,
         ("cmp", "ebx, 0x%x" % BLEND_NONE) in text),
        ("carves %d more bytes off the arena cursor" % DR_TPAGE_BYTES,
         ("lea", "eax, [rcx + %d]" % DR_TPAGE_BYTES) in text),
        ("builds a DR_TPAGE %#x | ((arg3 & 3) << %d)" % (DR_TPAGE_BASE, DR_TPAGE_ABR_SHIFT),
         ("or", "ebx, 0x%x" % DR_TPAGE_BASE) in text and ("and", "ebx, 3") in text
         and ("shl", "ebx, %d" % DR_TPAGE_ABR_SHIFT) in text),
        ("gives the prefix length 1", ("mov", "byte ptr [rdx + 3], 1") in text),
    )
    for label, good2 in checks:
        ok &= good2
        notes.append("%s %s" % (label, "OK" if good2 else "FAIL"))

    sig = dll.handler(OP_ADDPRIM)
    good = sig.kinds == "ippi"
    ok &= good
    notes.append("signature (tag, ot, prim, blend) = %r %s" % (sig.kinds, "OK" if good else "FAIL"))

    # op 64 hands its arg1 to THIS parameter -- which is what makes it a blend mode, not a depth.
    s64 = [(i.mnemonic, i.op_str) for i in dll.body(SCREEN_FN)]
    good = ("mov", "r9d, esi") in s64
    ok &= good
    notes.append("op 64 passes its arg1 into this blend parameter %s" % ("OK" if good else "FAIL"))
    return ok, notes


# --- op 64: the full-screen colour fill ---------------------------------------------------------
#: ``fn 0x3f180`` carves a 0x80-byte block off the arena cursor at ``sysCtx+0x24`` and fills it with
#: **eight 0x10-byte PS1 ``TILE`` primitives** -- ``{u32 tag; u8 r,g,b,code; u16 x,y; u16 w,h}`` --
#: then hands each to ``fn 0x3edb0``, which is libgpu's **``AddPrim``**: it puts the length in the
#: tag's top byte and XOR-splices the primitive into the ordering table through a 24-bit link
#: (``and 0xffffff``), the standard PS1 OT insert.  ``op 143`` exposes that function directly.
#:
#: The eight tiles are a **4x2 grid of 80x110** -- and ``4*80 = 320``, ``2*110 = 220``, the PS1
#: screen (this project already pins ``FieldMap.PsxScreenHeightNative = 220``).  So the op paints
#: the WHOLE SCREEN one flat colour.
#:
#: ``arg1`` is the **BLEND MODE** (corrected in the op 143 rung -- it was first read here as an OT
#: depth).  It does double duty: ``== 0xFF`` selects the opaque rectangle code ``0x60`` while
#: anything else selects ``0x62``, the semi-transparent twin (bit 1 is the PS1 rectangle ABE flag);
#: and it is handed to :data:`ADDPRIM_FN`'s fourth parameter, which turns ``arg1 & 3`` into a
#: ``DR_TPAGE`` semi-transparency mode (or emits nothing at ``0xFF``).  The corpus fits a blend mode
#: far better than a depth: ``1(x254)`` is ABR 1, PS1 **additive** blending -- what a VFX flash
#: wants -- with ``0`` 50/50, ``2`` subtractive and ``255`` opaque.  There is no depth argument at
#: all; the OT POINTER is the depth, as PS1 code always does it (``&ot[z]``).
OP_SCREEN = 64
SCREEN_FN = 0x3F180
ADDPRIM_FN = 0x3EDB0          # libgpu AddPrim; op 143's own native function
ADDPRIM_TAG = 0x3000000       # tag length 3 -> a 4-word TILE
TILE_COUNT = 8
TILE_W, TILE_H = 0x50, 0x6E   # 80 x 110
TILE_COLS, TILE_ROWS = 4, 2   # 4*80 = 320, 2*110 = 220 -- the PS1 screen
TILE_WH_WORD = 0x6E0050       # the single dword store that sets both
CODE_RECT = 0x60              # PS1 monochrome variable-size rectangle
CODE_ABE = 0x02               # + semi-transparency
OPAQUE_SENTINEL = 0xFF        # arg1 == 0xff -> opaque, and AddPrim special-cases it too
ARENA_BUMP = 0x80             # bytes carved off sysCtx+0x24 per call
NAME_SCREEN = "draw_fullscreen_fill"
DESCRIPTION_SCREEN = ("fill the whole 320x220 screen with a flat RGB colour -- eight TILE "
                      "primitives in a 4x2 grid of 80x110, added to the ordering table arg0; "
                      "opaque when the blend mode arg1 == 0xff, else semi-transparent at ABR "
                      "arg1 & 3")


def verify_screen(dll: Optional[A.DllView] = None) -> Tuple[bool, List[str]]:
    """Re-derive op 64's tile geometry, blend discriminator and AddPrim hand-off."""
    dll = dll or A.DllView()
    notes: List[str] = []
    ok = True

    fn = dll.function_of(dll.native_fn[OP_SCREEN]) or dll.native_fn[OP_SCREEN]
    good = fn == SCREEN_FN
    ok &= good
    notes.append("op %d native fn = %#x %s" % (OP_SCREEN, fn, "OK" if good else "FAIL"))

    text = [(i.mnemonic, i.op_str) for i in dll.body(fn)]
    checks = (
        ("carves %#x bytes off the arena cursor" % ARENA_BUMP,
         ("lea", "eax, [r10 + 0x%x]" % ARENA_BUMP) in text),
        ("writes w/h as one dword %#x (%d x %d)" % (TILE_WH_WORD, TILE_W, TILE_H),
         ("mov", "dword ptr [rbx + 8], 0x%x" % TILE_WH_WORD) in text),
        ("x stride %d: (i & 3) * 5 << 4" % TILE_W,
         ("and", "cx, 3") in text and ("shl", "cx, 4") in text),
        ("y stride %d: (i >> 2) * 0x%x" % (TILE_H, TILE_H),
         ("imul", "ax, ax, 0x%x" % TILE_H) in text),
        ("builds the rectangle code %#x | %#x" % (CODE_RECT, CODE_ABE),
         ("or", "r14b, 0x%x" % CODE_RECT) in text and ("mov", "r14d, %d" % CODE_ABE) in text),
        ("blend discriminator arg1 == %#x" % OPAQUE_SENTINEL,
         ("cmp", "esi, 0x%x" % OPAQUE_SENTINEL) in text),
        ("loops exactly %d times" % TILE_COUNT, ("cmp", "edi, %d" % TILE_COUNT) in text),
        ("hands each tile to AddPrim %#x with tag %#x" % (ADDPRIM_FN, ADDPRIM_TAG),
         ("call", hex(dll.base + ADDPRIM_FN)) in text
         and ("mov", "ecx, 0x%x" % ADDPRIM_TAG) in text),
    )
    for label, good2 in checks:
        ok &= good2
        notes.append("%s %s" % (label, "OK" if good2 else "FAIL"))

    good = TILE_COLS * TILE_W == 320 and TILE_ROWS * TILE_H == 220
    ok &= good
    notes.append("the grid tiles the PS1 screen: %d*%d = %d wide, %d*%d = %d high %s"
                 % (TILE_COLS, TILE_W, TILE_COLS * TILE_W, TILE_ROWS, TILE_H,
                    TILE_ROWS * TILE_H, "OK" if good else "FAIL"))

    # AddPrim really is one: the 24-bit XOR splice into the ordering table.
    ap = [(i.mnemonic, i.op_str) for i in dll.body(ADDPRIM_FN)]
    good = ("and", "eax, 0xffffff") in ap and ("shr", "ecx, 0x18") in ap
    ok &= good
    notes.append("%#x splices a 24-bit OT link and puts the length in the tag %s"
                 % (ADDPRIM_FN, "OK" if good else "FAIL"))

    sig = dll.handler(OP_SCREEN)
    good = sig.arity == 5 and sig.stack_args == (4,)
    ok &= good
    notes.append("the stub reads FIVE arguments, the last off the MIPS stack (arity=%d stacked=%s) %s"
                 % (sig.arity, sig.stack_args, "OK" if good else "FAIL"))
    return ok, notes


# --- ops 48 / 49 / 50: the RNG family -----------------------------------------------------------
#: Three ops, one algorithm, and the algorithm names itself.  Each computes
#:     seed = seed * 0x41C64E6D + 0x3039 ; value = seed >> 16
#: on the shared state at ``0x3231dc``.  ``0x41C64E6D`` = 1103515245 and ``0x3039`` = 12345 are the
#: **ANSI C ``rand()`` LCG constants** -- the multiplier/increment pair from the C standard's own
#: example implementation.  That is an external, published prior, not an inference about purpose:
#: the numbers identify the algorithm the way an import name would.
#:
#: Note the asymmetry this exposes in R2's contract.  R2 rates a *thin CRT wrapper* ``high`` -- it is
#: how ``rsin``/``rcos`` got their names, because the DLL imports ``sin``/``cos``.  These ops are the
#: C library's ``rand()`` too, just INLINED rather than imported, and inlining is a compiler choice.
#: They still ship ``medium``, because no source in the binary states a name, and inflating that
#: would be exactly the confident-wrong-name defect the contract exists to prevent.
RNG_STATE = 0x3231DC
LCG_MUL = 0x41C64E6D           # 1103515245
LCG_ADD = 0x3039               # 12345
LCG_SHIFT = 16
OP_RAND, OP_RAND_RANGE, OP_RAND_CENTERED = 48, 49, 50
RNG_FNS = {OP_RAND: 0x20930, OP_RAND_RANGE: 0x20950, OP_RAND_CENTERED: 0x20980}
RNG_NAMES = {
    OP_RAND: ("rand", "the raw LCG draw: seed = seed*0x41C64E6D + 0x3039; return seed >> 16"),
    OP_RAND_RANGE: ("rand_range",
                    "lo + rand() % (hi - lo); returns lo unchanged when lo == hi, without "
                    "advancing the seed"),
    OP_RAND_CENTERED: ("rand_centered",
                       "rand() % n - n/2, a jitter centred on zero; n == 0 is guarded to 1"),
}


def verify_rng(dll: Optional[A.DllView] = None) -> Tuple[bool, List[str]]:
    """Re-derive the shared LCG in all three RNG ops."""
    dll = dll or A.DllView()
    notes: List[str] = []
    ok = True
    mul_op = "eax, dword ptr [rip + 0x%x], 0x%x"          # matched by target, not by text
    for op in (OP_RAND, OP_RAND_RANGE, OP_RAND_CENTERED):
        fn = dll.function_of(dll.native_fn[op]) or dll.native_fn[op]
        good = fn == RNG_FNS[op]
        ok &= good
        body = list(dll.body(fn))
        text = [(i.mnemonic, i.op_str) for i in body]
        # the imul against the shared state, resolved by rip target rather than by displacement text
        hit = any(i.mnemonic == "imul" and dll.rip_target(i) == RNG_STATE
                  and hex(LCG_MUL) in i.op_str for i in body)
        add = ("add", "eax, 0x%x" % LCG_ADD) in text
        shr = ("shr", "eax, 0x%x" % LCG_SHIFT) in text
        store = any(i.mnemonic == "mov" and dll.rip_target(i) == RNG_STATE
                    and i.op_str.startswith("dword ptr [rip") for i in body)
        good2 = hit and add and shr and store
        ok &= good2
        notes.append("op %d fn %#x: imul*%#x %s, add %#x %s, shr %d %s, stores seed %s"
                     % (op, fn, LCG_MUL, "OK" if hit else "FAIL", LCG_ADD, "OK" if add else "FAIL",
                        LCG_SHIFT, "OK" if shr else "FAIL", "OK" if store else "FAIL"))
    # the shape that separates the three
    r49 = [(i.mnemonic, i.op_str) for i in dll.body(RNG_FNS[OP_RAND_RANGE])]
    good = ("idiv", "r8d") in r49 and ("lea", "eax, [rdx + rcx]") in r49
    ok &= good
    notes.append("op %d: %% (hi-lo) then + lo %s" % (OP_RAND_RANGE, "OK" if good else "FAIL"))
    r50 = [(i.mnemonic, i.op_str) for i in dll.body(RNG_FNS[OP_RAND_CENTERED])]
    good = ("sar", "ecx, 1") in r50 and ("sub", "edx, ecx") in r50
    ok &= good
    notes.append("op %d: %% n then - n/2 %s" % (OP_RAND_CENTERED, "OK" if good else "FAIL"))
    return ok, notes


def _u16(b: bytes, o: int) -> int:
    return struct.unpack_from("<H", b, o)[0]


def _u32(b: bytes, o: int) -> int:
    return struct.unpack_from("<I", b, o)[0]


def relocator_reading(blob: bytes, base: int, limit: int) -> Optional[Tuple[int, int, int]]:
    """``(count, relocations, header)`` if the relocator's reading holds at ``base``, else None.

    A pure predicate over bytes -- this is what the corpus A/B test scores, so it must be the same
    code in both arms and must not know which arm it is in.
    """
    try:
        hdr = HDR_SMALL if blob[base] == HDR_FLAG_BYTE else HDR_LARGE
        top = base + hdr
        if top + TABLE_OFF > limit:
            return None
        count = _u16(blob, top + COUNT_OFF)
        if count == 0 or count > 512:
            return None
        if top + TABLE_OFF + ENTRY_STRIDE * count > limit:
            return None
        relocs = 0
        for i in range(count):
            e = top + TABLE_OFF + ENTRY_STRIDE * i
            for kind_off, sentinel, ptr_off in PTR_FIELDS:
                if blob[e + kind_off] != sentinel:
                    v = _u32(blob, e + ptr_off)
                    if v > OFFSET_MAX or base + v >= limit:
                        return None
                    relocs += 1
        return count, relocs, hdr
    except Exception:
        return None


# --- verification against the live DLL ---------------------------------------------------------
def verify(dll: Optional[A.DllView] = None) -> Tuple[bool, List[str]]:
    """Re-derive every structural claim from the installed DLL.

    The name is emitted ONLY if this passes, so a different build cannot inherit a stale constant.
    """
    dll = dll or A.DllView()
    notes: List[str] = []
    ok = True

    fn = dll.function_of(dll.native_fn[OP_OPEN]) or dll.native_fn[OP_OPEN]
    good = fn == FORWARDER
    ok &= good
    notes.append("op %d native fn = %#x (expect %#x) %s"
                 % (OP_OPEN, fn, FORWARDER, "OK" if good else "FAIL"))

    # the forwarder tail-jumps to the relocator, passing the pool descriptor and the context object
    jmp: Set[int] = set()
    leas: Set[int] = set()
    for ins in dll.body(fn):
        if ins.mnemonic == "jmp" and ins.op_str.startswith("0x"):
            jmp.add(int(ins.op_str, 16) - dll.base)
        t = dll.rip_target(ins)
        if t is not None:
            leas.add(t)
    good = RELOCATOR in jmp
    ok &= good
    notes.append("forwarder tail-jumps to %#x %s" % (RELOCATOR, "OK" if good else "FAIL got %s"
                                                     % [hex(x) for x in sorted(jmp)]))
    good = {POOL_DESC, CTX_OBJECT} <= leas
    ok &= good
    notes.append("forwarder passes pool %#x + context %#x %s"
                 % (POOL_DESC, CTX_OBJECT, "OK" if good else "FAIL"))

    # the relocator uses the per-slot work array and the PSX address translator
    rel_refs: Set[int] = set()
    calls: Set[int] = set()
    for ins in dll.body(RELOCATOR):
        t = dll.rip_target(ins)
        if t is not None:
            rel_refs.add(t)
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            calls.add(int(ins.op_str, 16) - dll.base)
    good = WORK_ARRAY in rel_refs and 0x576A10 in rel_refs
    ok &= good
    notes.append("relocator references the work array %#x and psxBankTable %s"
                 % (WORK_ARRAY, "OK" if good else "FAIL"))
    good = A.HOST_TO_PSX_RVA in calls
    ok &= good
    notes.append("relocator calls host->PSX %#x %s"
                 % (A.HOST_TO_PSX_RVA, "OK" if good else "FAIL"))

    # the family shares the pool: ops 116..119 sit on consecutive functions that all reference it
    fam: Dict[int, int] = {}
    for op in FAMILY_OPS:
        fam[op] = dll.function_of(dll.native_fn[op]) or dll.native_fn[op]
    shares = []
    for op, f in fam.items():
        refs = {dll.rip_target(i) for i in dll.body(f)}
        refs |= {t for j in _tail_targets(dll, f) for t in {dll.rip_target(i) for i in dll.body(j)}}
        shares.append(CTX_OBJECT in refs or POOL_DESC in refs)
    good = all(shares)
    ok &= good
    notes.append("ops %s all reach the shared pool/context %s"
                 % (list(FAMILY_OPS), "OK" if good else "FAIL %s" % shares))
    good = sorted(fam.values()) == list(fam.values()) and len(set(fam.values())) == 4
    ok &= good
    notes.append("the family's functions are 4 distinct, ascending: %s %s"
                 % ([hex(v) for v in fam.values()], "OK" if good else "FAIL"))
    return ok, notes


def so_reading(blob: bytes, base: int, limit: int) -> Optional[Tuple[int, int]]:
    """``(variant, entry_count)`` if an ``'so'`` binding table starts at ``base``, else None.

    This is the op's OWN assert (``u16[base] == 0x6f73``) plus the two fields its ABR loop reads,
    so a sub-file that fails it cannot be a real operand -- the DLL would have tripped ``_wassert``.
    """
    try:
        if base + SO_TABLE_OFF > limit or _u16(blob, base) != SO_MAGIC:
            return None
        rec_len = _u16(blob, base + SO_LEN_OFF)
        if rec_len < SO_TABLE_OFF or base + rec_len > limit:
            return None
        return _u16(blob, base + SO_VARIANT_OFF), (rec_len - SO_TABLE_OFF) // 8
    except Exception:
        return None


def verify_abr(dll: Optional[A.DllView] = None) -> Tuple[bool, List[str]]:
    """Re-derive op 206's body from the installed DLL, including BOTH tail-call names."""
    dll = dll or A.DllView()
    notes: List[str] = []
    ok = True

    fn = dll.function_of(dll.native_fn[OP_ABR]) or dll.native_fn[OP_ABR]
    good = fn == ABR_FN
    ok &= good
    notes.append("op %d native fn = %#x (expect %#x) %s"
                 % (OP_ABR, fn, ABR_FN, "OK" if good else "FAIL"))

    body = list(dll.body(fn))
    text = [(i.mnemonic, i.op_str) for i in body]
    good = ("mov", "eax, 0x6f73") in text
    ok &= good
    notes.append("asserts the 'so' magic %#x %s" % (SO_MAGIC, "OK" if good else "FAIL"))
    good = ("and", "di, 3") in text and ("shl", "di, 5") in text
    ok &= good
    notes.append("builds the ABR field as (arg1 & %#x) << %d %s"
                 % (ABR_MASK, ABR_SHIFT, "OK" if good else "FAIL"))
    good = any(m == "or" and o.startswith("word ptr [rdx +") for m, o in text)
    ok &= good
    notes.append("ORs it into the binding table (never assigns) %s" % ("OK" if good else "FAIL"))

    jmps = {int(o, 16) - dll.base for m, o in text if m == "jmp" and o.startswith("0x")}
    good = {TEXLIST_FN, GOURAUD_FN} <= jmps
    ok &= good
    notes.append("tail-calls %#x and %#x %s" % (TEXLIST_FN, GOURAUD_FN, "OK" if good else "FAIL"))
    for f2, want in ((TEXLIST_FN, "Hi_RegisterTexListModel"), (GOURAUD_FN, "Hi_RegisterGouEffModel")):
        owns = sorted(dll._name_of_fn.get(f2, ()))
        good = dll.function_of(f2) == f2 and owns == [want]
        ok &= good
        notes.append("  %#x is a .pdata primary owning exactly %r %s"
                     % (f2, want, "OK" if good else "FAIL got %s" % owns))
    return ok, notes


def verify_coord(dll: Optional[A.DllView] = None) -> Tuple[bool, List[str]]:
    """Re-derive op 136's body: lookup, divide-by-6, add."""
    dll = dll or A.DllView()
    notes: List[str] = []
    ok = True

    fn = dll.function_of(dll.native_fn[OP_COORD]) or dll.native_fn[OP_COORD]
    good = fn == COORD_FN
    ok &= good
    notes.append("op %d native fn = %#x (expect %#x) %s"
                 % (OP_COORD, fn, COORD_FN, "OK" if good else "FAIL"))

    text = [(i.mnemonic, i.op_str) for i in dll.body(fn)]
    calls = {int(o, 16) - dll.base for m, o in text if m == "call" and o.startswith("0x")}
    good = ACTOR_LOOKUP in calls
    ok &= good
    notes.append("calls the actor lookup %#x %s" % (ACTOR_LOOKUP, "OK" if good else "FAIL"))
    good = ("mov", "eax, 0x%x" % DIV_MAGIC) in text and ("shr", "edx, 2") in text
    ok &= good
    notes.append("divides by %d via the %#x magic %s"
                 % (COORD_DIVISOR, DIV_MAGIC, "OK" if good else "FAIL"))
    good = ("mul", "dword ptr [rcx + 0x%x]" % ACTOR_FIELD) in text
    ok &= good
    notes.append("the dividend is actor[+%#x] %s" % (ACTOR_FIELD, "OK" if good else "FAIL"))
    good = any(m == "lea" and o.startswith("eax, [rbx +") for m, o in text)
    ok &= good
    notes.append("adds the caller's base to the quotient %s" % ("OK" if good else "FAIL"))

    # +0x38 is NOT one of BTL_DATA_INIT's 17 fields: SFX_InitBattle copies every one of them, in
    # order, to a DIFFERENT set of offsets.  Recorded so nobody re-derives it from the open-source
    # struct and lands on the wrong field.
    notes.append("NOTE actor[+%#x] is a DLL-computed runtime field, not a copied BTL_DATA_INIT one"
                 % ACTOR_FIELD)
    return ok, notes


def wassert_sources(dll: Optional[A.DllView] = None) -> Dict[int, Set[str]]:
    """{function: {source file}} from every ``_wassert`` call site.

    A string class R2 never saw: ``_wassert`` takes WIDE (UTF-16) strings, and R2's name resolver
    scans ASCII runs only.  Reach is modest -- 6 files over 20 functions, 9 of them an op's own
    native function -- so this is an attribution aid, not a naming lane; op 206's is
    ``psx_compatibility.cpp`` line 786.
    """
    dll = dll or A.DllView()
    wassert = next((rva for rva, nm in dll.imports.items() if nm == "_wassert"), None)
    out: Dict[int, Set[str]] = {}
    if wassert is None:
        return out
    for fn in sorted({dll.function_of(b) or b for b, _e, _u in dll._raw}):
        rdx = None
        try:
            body = list(dll.body(fn))
        except Exception:
            continue
        for ins in body:
            t = dll.rip_target(ins)
            if ins.mnemonic == "lea" and ins.op_str.startswith("rdx,") and t:
                rdx = t
            elif ins.mnemonic == "call" and "rip" in ins.op_str and t == wassert and rdx:
                try:
                    s = dll.pe.get_data(rdx, 400).decode("utf-16le", "replace").split("\x00")[0]
                except Exception:
                    continue
                if ".cpp" in s:
                    out.setdefault(fn, set()).add(s)
    return out


def _tail_targets(dll: A.DllView, fn: int) -> List[int]:
    out = []
    for ins in dll.body(fn):
        if ins.mnemonic == "jmp" and ins.op_str.startswith("0x"):
            t = int(ins.op_str, 16) - dll.base
            f2 = dll.function_of(t) or t
            if f2 != fn:
                out.append(f2)
    return out


def tailjump_name_gap(dll: Optional[A.DllView] = None) -> List[Tuple[int, int, List[str]]]:
    """Ops whose own function owns no debug string but which TAIL-JUMP to one that does.

    R2 resolves a name on the op's own function only, so a forwarder hides its callee's symbol.
    Found while naming op 117 (whose chain has no symbol at all, so it does not benefit).
    """
    dll = dll or A.DllView()
    out = []
    for op in range(A.T.HLE_OP_COUNT):
        fn = dll.function_of(dll.native_fn[op]) or dll.native_fn[op]
        if not fn or dll._name_of_fn.get(fn):
            continue
        for f2 in _tail_targets(dll, fn):
            names = sorted(dll._name_of_fn.get(f2, ()))
            if names:
                out.append((op, f2, names))
    return out


def body_evidence(dll: Optional[A.DllView] = None) -> Dict[int, dict]:
    """The injectable source for ``tier_r_annot.build_hle_ops(body=...)``.

    Emits nothing at all unless :func:`verify` passes against the installed DLL.
    """
    dll = dll or A.DllView()
    out: Dict[int, dict] = {}

    ok_abr, _n = verify_abr(dll)
    if ok_abr:
        src = sorted(wassert_sources(dll).get(ABR_FN, ()))
        out[OP_ABR] = {
            "name": NAME_ABR,
            # HIGH: the DLL supplies the name -- twice, from two .pdata primaries each owning
            # exactly one debug string -- and the op is precisely their disjunction, with the
            # selector decoded.  R2 missed it only because a tail call hides the callee's symbol.
            "confidence": "high",
            "evidence": ("%s %s; fn %#x asserts u16[arg0] == %#x ('so'), branches on u16[+%#x], "
                         "ORs (arg1 & %#x) << %d into u16[+%#x + 4*i] for i < (u16[+%#x] - %d)/8, "
                         "then TAIL-CALLS %#x Hi_RegisterTexListModel (variant != 0) or %#x "
                         "Hi_RegisterGouEffModel (variant == 0), both .pdata primaries owning "
                         "exactly that one name%s; corpus: 339/339 $a1 values lie in {0,1,2,3,255} "
                         "-- every one a valid ABR selector under &3, mode 1 (additive) dominant "
                         "at 222/339; the 'so' magic holds on 67.2%% of heuristically-paired "
                         "operands vs 3.7%% control (18x), and the shortfall is PAIRING, not "
                         "operands: the magic is absent at every offset in the misses and the DLL "
                         "would have tripped _wassert on a real one. Independently reproduces "
                         "A1-TEXTURES.md 3.5, derived months earlier by a different method."
                         % (BODY_MARKER, DESCRIPTION_ABR, ABR_FN, SO_MAGIC, SO_VARIANT_OFF,
                            ABR_MASK, ABR_SHIFT, SO_TABLE_OFF, SO_LEN_OFF, SO_TABLE_OFF,
                            TEXLIST_FN, GOURAUD_FN,
                            " (%s)" % src[0] if src else "")),
        }

    ok_ap, _n5 = verify_addprim(dll)
    if ok_ap:
        out[OP_ADDPRIM] = {
            "name": NAME_ADDPRIM,
            "confidence": "medium",
            "evidence": ("%s %s; fn %#x is libgpu addPrim -- length from the tag's top byte into "
                         "prim->tag[3], then the standard PS1 ordering-table insert XOR-swapping "
                         "only the low 24 bits so each word keeps its own top byte -- and unless "
                         "arg3 == %#x it carves %d more bytes off the arena cursor for a 2-word "
                         "primitive whose payload is %#x | ((arg3 & 3) << %d): GP0(E1h) Draw Mode, "
                         "bits 5-6 the ABR semi-transparency mode, bit 9 dither, i.e. a DR_TPAGE. "
                         "addPrim inserts at the HEAD, so the prefix draws FIRST -- set the blend, "
                         "then draw. Corpus: all 9 $a0 constants are primitive TAGS (low 24 bits "
                         "zero, length 4 or 8) against 0.9%% of every other int-arg0 op -- a ~90x "
                         "separation. THIS RUNG CORRECTED OP 64: it passes its arg1 into this "
                         "blend parameter, so that argument is a blend mode, NOT an OT depth."
                         % (BODY_MARKER, DESCRIPTION_ADDPRIM, ADDPRIM_FN, BLEND_NONE,
                            DR_TPAGE_BYTES, DR_TPAGE_BASE, DR_TPAGE_ABR_SHIFT)),
        }

    ok_screen, _n4 = verify_screen(dll)
    if ok_screen:
        out[OP_SCREEN] = {
            "name": NAME_SCREEN,
            "confidence": "medium",
            "evidence": ("%s %s; fn %#x carves %#x bytes off the arena cursor and builds %d PS1 "
                         "TILE primitives {u32 tag; u8 r,g,b,code; u16 x,y; u16 w,h} in a %dx%d "
                         "grid of %dx%d -- %d x %d, the PS1 screen -- colouring each (arg2,arg3,"
                         "arg4) and coding it %#x opaque when arg1 == %#x else %#x (the rectangle "
                         "ABE bit), then handing it to %#x, libgpu AddPrim (24-bit OT XOR-splice, "
                         "length in the tag's top byte; op 143's own native fn). THE STUB READS "
                         "FIVE ARGUMENTS -- the fifth off the MIPS stack at $sp+0x10 -- which R2 "
                         "undercounted at 4; M3-opcode-table.json, derived independently from the "
                         "x86 build's [ebp+N] frame, says 5. Corpus: $a1 is only ever "
                         "{0,1,2,255} (a BLEND MODE -- ABR 1, additive, dominates at 254/366 -- "
                         "plus the 0xff opaque case AddPrim itself "
                         "special-cases as 'no draw-mode primitive') and every $a2/$a3 constant is "
                         "a colour byte <= 255; a "
                         "real call site builds the three channels as three SHIFTS of one animated "
                         "scalar (r=v>>4, g=v>>3, b=v>>2), which coordinates could not be."
                         % (BODY_MARKER, DESCRIPTION_SCREEN, SCREEN_FN, ARENA_BUMP, TILE_COUNT,
                            TILE_COLS, TILE_ROWS, TILE_W, TILE_H, TILE_COLS * TILE_W,
                            TILE_ROWS * TILE_H, CODE_RECT, OPAQUE_SENTINEL, CODE_RECT | CODE_ABE,
                            ADDPRIM_FN)),
        }

    ok_rng, _n3 = verify_rng(dll)
    if ok_rng:
        for op, (nm, how) in RNG_NAMES.items():
            out[op] = {
                "name": nm,
                "confidence": "medium",
                "evidence": ("%s %s; fn %#x drives the shared LCG at %#x -- "
                             "seed = seed*%#x + %#x, value = seed >> %d -- whose multiplier/"
                             "increment pair (%d, %d) is the ANSI C rand() LCG, a published "
                             "external prior. MEDIUM not high: no source in the binary states a "
                             "name; R2 rates a thin CRT wrapper high (rsin/rcos) and these are the "
                             "same library function INLINED rather than imported, but inlining is "
                             "a codegen choice and the contract asks for a stated name."
                             % (BODY_MARKER, how, RNG_FNS[op], RNG_STATE, LCG_MUL, LCG_ADD,
                                LCG_SHIFT, LCG_MUL, LCG_ADD)),
            }

    ok_coord, _n2 = verify_coord(dll)
    if ok_coord:
        out[OP_COORD] = {
            "name": NAME_COORD,
            # MEDIUM: no symbol names it, and actor[+0x38]'s own identity is unresolved -- every
            # BTL_DATA_INIT field maps elsewhere, so it is a DLL runtime field.  What IS pinned is
            # the arithmetic and the destination.
            "confidence": "medium",
            "evidence": ("%s %s; fn %#x looks the actor up via %#x (idx<8 party, 8..15 enemies, "
                         "0x10/0x11 singleton slots), divides actor[+%#x] by %d (%#x magic + "
                         "shr 2) and adds arg1; the corpus stores the result into an op-117 "
                         "instance's +%#x, which the per-tick fn 0x34860 loads TOGETHER with +0x20 "
                         "into GTE input slots and projects -- so +%#x is a coordinate component, "
                         "not a sort key; 510/510 sites pass arity 2, $a0 in {0,16} (party member 0 "
                         "and the +0x50 singleton), $a1 all powers of two 16..512, and 436 of the "
                         "510 sites sit beside op 117. actor[+%#x] is NOT a BTL_DATA_INIT field: "
                         "SFX_InitBattle copies all 17 of them, in order, to other offsets."
                         % (BODY_MARKER, DESCRIPTION_COORD, COORD_FN, ACTOR_LOOKUP, ACTOR_FIELD,
                            COORD_DIVISOR, DIV_MAGIC, INSTANCE_COORD_OFF, INSTANCE_COORD_OFF,
                            ACTOR_FIELD)),
        }

    ok, _notes = verify(dll)
    if not ok:
        return out
    out[OP_OPEN] = {
        "name": NAME,
        "confidence": "medium",
        "evidence": ("%s %s; native fn %#x tail-jumps to the pooled allocator %#x (record stride "
                     "%#x, work buffer %#x/slot, pool %#x shared with ops %s); relocates the blob's "
                     "%#x-stride entry table (count u16 at +%#x, pointers +%#x/+%#x gated by kind "
                     "bytes, offsets <= %#x) to absolute PSX addresses via psxBankTable; corpus: "
                     "1680/1709 sites (98.3%%) take a sub-file pointer from op 102, the reading "
                     "validates 62.2%% on fed sub-files vs 6.4%% on the rest, and 0/759 camera "
                     "sub-files are ever fed. NOT high: no symbol in the chain supplies a name, and "
                     "38%% of fed sub-files carry structure this pass does not model."
                     % (BODY_MARKER, DESCRIPTION, FORWARDER, RELOCATOR, RECORD_STRIDE, WORK_SIZE,
                        POOL_DESC, list(FAMILY_OPS), ENTRY_STRIDE, COUNT_OFF,
                        PTR_FIELDS[0][2], PTR_FIELDS[1][2], OFFSET_MAX)),
    }
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gates", action="store_true", help="also run the corpus A/B test")
    args = ap.parse_args(argv)

    dll = A.DllView()
    ok, notes = verify(dll)
    print("VERIFY op %d against the installed DLL" % OP_OPEN)
    for n in notes:
        print("  " + n)
    print("  =>", "PASS" if ok else "FAIL")

    ok2, notes2 = verify_abr(dll)
    print("\nVERIFY op %d against the installed DLL" % OP_ABR)
    for n in notes2:
        print("  " + n)
    print("  =>", "PASS" if ok2 else "FAIL")

    ok3, notes3 = verify_coord(dll)
    print("\nVERIFY op %d against the installed DLL" % OP_COORD)
    for n in notes3:
        print("  " + n)
    print("  =>", "PASS" if ok3 else "FAIL")

    ok4, notes4 = verify_rng(dll)
    print("\nVERIFY the RNG family (ops %d / %d / %d)"
          % (OP_RAND, OP_RAND_RANGE, OP_RAND_CENTERED))
    for n in notes4:
        print("  " + n)
    print("  =>", "PASS" if ok4 else "FAIL")
    ok = ok and ok2 and ok3 and ok4

    src = wassert_sources(dll)
    files = sorted({f for v in src.values() for f in v})
    print("\n_wassert SOURCE FILES (UTF-16 -- invisible to an ASCII string scan): %d files over "
          "%d functions" % (len(files), len(src)))
    for f in files:
        print("   " + f)

    gap = tailjump_name_gap(dll)
    print("\nTAIL-JUMP NAME GAP (R2 resolves names on the op's own function only): %d op(s)"
          % len(gap))
    for op, f2, names in gap:
        print("   op %3d --jmp--> %#x owns %s" % (op, f2, names))

    ev = body_evidence(dll)
    print("\nBODY EVIDENCE: %s" % ({op: e["name"] for op, e in ev.items()} or "none"))

    if args.gates:
        from body_gates import main as gmain
        return gmain()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
