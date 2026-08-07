"""body_ops -- THE HANDLER-BODY EVIDENCE CLASS.  Currently: op 117, the corpus's busiest HLE op.

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
    ok, _notes = verify(dll)
    if not ok:
        return {}
    return {OP_OPEN: {
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
    }}


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
