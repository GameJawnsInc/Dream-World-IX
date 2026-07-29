r"""W6b-2 lane V2 -- THE REFUTER for L2 (the program-VRAM WRITE scan).

WHAT THIS IS.  An INDEPENDENT re-derivation of the program-VRAM transfer-call sites, written to
falsify `w6b2_write_scan.py`'s verdict ("DELTA = NONE") rather than to restate it.  It shares no
code with L2 beyond the read-only tier-r decoder and the container parser; every predicate below --
the destination-register model, the def-use analysis, the base-chain adjudication, the switch-
dispatch refutation -- is re-derived here from the MIPS-I ISA table the decoder itself exposes.

THE THREE WAYS L2's ANSWER COULD BE WRONG, and the instrument built for each:

  F1  FALSE NEGATIVE BY WINDOW.  L2 looks BACKWARD at most 64 instructions from a call for the
      fn-pointer load.  A load hoisted further, or a call in a different basic block, is invisible.
      -> V2 scans FORWARD from every HLE-table load with NO window at all (`forward_uses`): find
         every `lw rT, 4*op(rB)` in the image, then follow rT to its consuming control transfer
         through the whole image, killing the chain only at a redefinition of rT.
  F2  FALSE NEGATIVE BY COPY.  L2 requires the call target's NEAREST DEFINITION to be the `lw`
      itself.  `lw $v0,664($t3) ; move $t9,$v0 ; ... ; jalr $t9` has an `addu`/`move` in between and
      is dropped.  -> V2 propagates through `move` / `addu rD,rS,$zero` / `or rD,rS,$zero` (W5).
  F3  FALSE POSITIVE SURVIVING ADJUDICATION.  L2 rejects 54 candidates as "the ef435 shape" using
      ONE positive test (the indexed table resolves to in-image pointers).  -> V2 adds a SECOND,
      structurally different test: the SWITCH-GUARD test (a bounds compare `sltiu`/`sltu` on the
      index, branching over the jump) and the TARGET-DECODES test (the table entries decode as
      plausible instruction streams).  Three tests must agree before a rejection is accepted.

THE HLE CALL SHAPE LAW (R1): an HLE call is ``lw rT, (4*op)(sysStruct+0x10)`` then ``jalr rT``.
THE OPS: 0 / 1 / 166 / 12 -- the four the record names as VRAM-transfer or texanim-arm ops.

PROVENANCE.  Zero Square-Enix bytes in this file.  It reads the SE-derived corpus at
``C:\gd\SCRATCH\summon-format`` and writes every decoded listing under
``C:\gd\SCRATCH\summon-format\texel-w6b\w6b2\``.  No install write, no deploy, no git.

Usage
-----
    py w6b2_v2_check.py                 # the full V2 pass -> v2_check.json + the console report
    py w6b2_v2_check.py --gates         # only the V-gates (calibration + adjudication)
    py w6b2_v2_check.py --sample 20     # the blind-sample cross-check on L2-CLEAN images
    py w6b2_v2_check.py --listing 435   # decoded listing around one effect's candidates
"""
from __future__ import annotations

import argparse
import json
import os
import random
import struct
import sys
from typing import Dict, List, Optional, Sequence, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "ff9mapkit"))
sys.path.insert(0, os.path.join(_HERE, "..", "tier-r"))

import tier_r_disasm as D                                         # noqa: E402
from ff9mapkit.summons import container as EC                     # noqa: E402
from ff9mapkit.summons import repaint as RP                       # noqa: E402

CORPUS = os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format")
OUT_DIR = os.path.join(CORPUS, "texel-w6b", "w6b2")
L2_JSON = os.path.join(OUT_DIR, "write_scan.json")

VRAM_OPS = {0: "op0", 1: "op1", 166: "op166", 12: "op12"}
#: DIRECTION under test, NOT assumed: the shipped reading is op0=LoadImage(write),
#: op1=StoreImage(read), op166=MoveImage(write), op12=TexAnimArm(write).  V2 re-checks it in
#: :func:`check_direction` from the DLL bytes + Memoria's own handler and reports BOTH predicates.
SHIPPED_NAME = {0: "LoadImage", 1: "StoreImage", 166: "MoveImage", 12: "TexAnimArm"}
WRITE_OPS = (0, 166, 12)
READ_OPS = (1,)

SHIPPED_WRITE = frozenset(RP.PROGRAM_VRAM_WRITE_IDS)
SHIPPED_READ = frozenset(RP.PROGRAM_VRAM_READ_IDS)
SHIPPED_HARD = dict(RP.MOVEIMAGE_HARD_CELLS)

R_ZERO, R_SP, R_FP, R_RA = 0, 29, 30, 31
SYS_FIELD = D.HLE_STRUCT_FIELD                                    # 0x10
HLE_MAX = D.HLE_MAX_OFFSET                                        # 0x360


# ------------------------------------------------------------------ V2's own register-write model
#: RE-DERIVED from the ISA table's extractor order rather than transcribed from L2.  Every MIPS-I
#: instruction that writes a GPR writes either its ``rd`` or its ``rt`` slot; the three link forms
#: write ``$ra`` implicitly.  Anything absent here writes no GPR (stores, branches, mult/div, the
#: COP loads/stores, the ``mtc``/``ctc`` direction).
_WRITES_RD = frozenset((
    "sll", "sra", "srl", "move", "jalr", "mfhi", "mflo", "add", "addu", "and", "xor", "srlv",
    "sub", "subu", "nor", "or", "sllv", "slt", "sltu", "srav"))
_WRITES_RT = frozenset((
    "addi", "addiu", "slti", "sltiu", "andi", "ori", "xori", "li", "lui",
    "lb", "lh", "lwl", "lw", "lbu", "lhu", "lwr",
    "mfc0", "cfc0", "mfc1", "cfc1", "mfc2", "cfc2", "mfc3", "cfc3"))
_WRITES_RA = frozenset(("jal", "bltzal", "bgezal"))


def dest_reg(ins) -> Optional[int]:
    """The GPR this instruction writes, or ``None``.  ``$zero`` is not a write.

    Uses the decoder's own ``op(Ex.RD)`` / ``op(Ex.RT)`` accessors, so it is correct regardless of
    where the operand sits in the DLL's extractor order -- L2 reads ``ops[0]`` instead, which is
    equivalent ONLY because every writing entry happens to list its destination first.  Gate V0
    asserts that equivalence over the whole ISA rather than assuming it.
    """
    if not ins.entry:
        return None
    n = ins.entry.name
    if n in _WRITES_RA:
        return R_RA
    r = ins.op(D.Ex.RD) if n in _WRITES_RD else (ins.op(D.Ex.RT) if n in _WRITES_RT else None)
    return r or None


def is_call(ins) -> Optional[Tuple[int, str]]:
    """``(target_register, via)`` for an indirect control transfer, else ``None``.

    ``jr $ra`` is a RETURN, not a call, and is excluded; every other ``jr`` is included, because a
    tail jump through a register is exactly the shape the ef435 refutation is about.
    """
    if not ins.entry:
        return None
    n = ins.entry.name
    if n == "jalr":
        rs = ins.op(D.Ex.RS)
        return (rs, "jalr") if rs else None
    if n == "jr":
        rs = ins.op(D.Ex.RS)
        return (rs, "jr") if rs and rs != R_RA else None
    return None


def hle_op_of_load(ins) -> Optional[int]:
    """If ``ins`` is ``lw rT, imm(rB)`` with ``imm`` a valid HLE table slot, the op index."""
    if not ins.entry or ins.entry.name != "lw":
        return None
    imm = ins.op(D.Ex.OFF_BASE)
    if imm is None or imm < 0 or imm % 4 or imm >= HLE_MAX:
        return None
    return imm // 4


def decode_region(img, lo: int, hi: int) -> List:
    dec = D.DEFAULT_DECODER
    hi = min(hi, len(img.payload))
    return [dec.decode(struct.unpack_from("<I", img.payload, o)[0], o, img.psx_base)
            for o in range(lo, max(lo, hi - 3), 4)]


# ------------------------------------------------------------------------- F1/F2: the FORWARD scan
#: registers a called function may clobber, so a chain crossing a call is dead.
_CALLER_SAVED = frozenset(list(range(1, 16)) + [24, 25, R_RA])     # $at,$v*,$a*,$t0-$t7,$t8,$t9,$ra


def forward_uses(ins: Sequence, k: int, reg: int, max_span: int = 100000) -> List[dict]:
    """Every control transfer that consumes the value produced at index ``k`` in ``reg``.

    THE UNBOUNDED INSTRUMENT (F1/F2).  Walks FORWARD in linear order with no lookback constant at
    all, propagating the value through ``move``/``addu rD,rS,$zero``/``or rD,rS,$zero`` copies (F2)
    and stopping a chain when its register is redefined by anything else.  This is deliberately a
    *linear* walk, not a CFG walk: a linear walk over-approximates (it may follow a value past a
    branch that would not fall through), and an over-approximation is what a false-NEGATIVE hunt
    needs.  Every extra it produces is adjudicated below, never counted.
    """
    live = {reg: [k]}                                              # reg -> the copy chain
    out: List[dict] = []
    for j in range(k + 1, min(len(ins), k + 1 + max_span)):
        i = ins[j]
        call = is_call(i)
        if call and call[0] in live:
            out.append({"use": j, "via": call[1], "chain": list(live[call[0]]), "reg": call[0]})
        d = dest_reg(i)
        if d is None:
            continue
        n = i.entry.name
        # a COPY of a live register keeps the chain alive under a new name
        src = None
        if n == "move":
            src = i.op(D.Ex.RS)
        elif n in ("addu", "add", "or") :
            a, b = i.op(D.Ex.RS), i.op(D.Ex.RT)
            if b == R_ZERO:
                src = a
            elif a == R_ZERO:
                src = b
        if src is not None and src in live and d != R_ZERO:
            live[d] = live[src] + [j]
            continue
        live.pop(d, None)
        if call and call[1] == "jalr":                             # the callee clobbers temporaries
            for r in list(live):
                if r in _CALLER_SAVED:
                    live.pop(r, None)
    return out


# ------------------------------------------------------------- the base chain, re-derived from ISA
def base_chain(ins: Sequence, defj: int, base: int) -> Tuple[str, str]:
    """Adjudicate the HLE-table BASE of the fn-pointer load at index ``defj``.

    V2's chain resolver is UNBOUNDED (it searches to the top of the image) where L2's is windowed at
    64, and it resolves a stack spill by matching the ``sw`` that filled the slot.  Verdicts:

      ``sentinel``       the base is provably ``*(rX + 0x10)`` -- the HLE system struct;
      ``sentinel-spill`` the base was spilled to the frame and reloaded, and the spilled value was
                         the sentinel load;
      ``nodef``          no definition anywhere above -- a callee-saved register or an incoming
                         parameter; the walk's own shape for a hoisted base;
      ``computed``       the base is COMPUTED from an index (``addu``) -- the ef435 shape;
      ``lw-other``       loaded from some field that is not ``+0x10``.
    """
    def prev_def(stop: int, reg: int) -> Optional[int]:
        for j in range(stop, -1, -1):
            if dest_reg(ins[j]) == reg:
                return j
        return None

    bj = prev_def(defj - 1, base)
    if bj is None:
        return ("nodef", "$%s has no definition above +%#x (hoisted / a parameter)"
                % (D.REG[base], ins[defj].off))
    q = ins[bj]
    n = q.entry.name
    if n == "lw" and q.op(D.Ex.OFF_BASE) == SYS_FIELD:
        return ("sentinel", "%s @+%#x == *(sysStruct+0x10)" % (q.text(), q.off))
    if n == "lw" and q.entry.ex and q.ops and q.op(D.Ex.OFF_BASE) is not None \
            and _load_base(q) in (R_SP, R_FP):
        slot, breg = q.op(D.Ex.OFF_BASE), _load_base(q)
        for j in range(bj - 1, -1, -1):
            r = ins[j]
            if r.entry and r.entry.name == "sw" and r.op(D.Ex.OFF_BASE) == slot \
                    and _load_base(r) == breg:
                sj = prev_def(j - 1, r.op(D.Ex.RT))
                if sj is not None and ins[sj].entry.name == "lw" \
                        and ins[sj].op(D.Ex.OFF_BASE) == SYS_FIELD:
                    return ("sentinel-spill", "%s @+%#x <- %s @+%#x <- %s @+%#x == *(sysStruct+0x10)"
                            % (q.text(), q.off, r.text(), r.off, ins[sj].text(), ins[sj].off))
                return ("spill-other", "%s @+%#x <- %s @+%#x (spilled value is not the sentinel)"
                        % (q.text(), q.off, r.text(), r.off))
        return ("spill-unresolved", "%s @+%#x -- no sw fills that frame slot above" % (q.text(),
                                                                                       q.off))
    if n == "lw":
        return ("lw-other", "%s @+%#x -- base loaded from +%#x, not +0x10"
                % (q.text(), q.off, q.op(D.Ex.OFF_BASE)))
    return ("computed", "%s @+%#x -- base COMPUTED (the ef435 pointer-table shape)"
            % (q.text(), q.off))


def _load_base(ins) -> Optional[int]:
    return ins.base_reg


REAL_CHAINS = ("sentinel", "sentinel-spill", "nodef")


# ------------------------------------------------- F3: THREE independent refutations of a candidate
def table_evidence(img, ins: Sequence, bj: int) -> Optional[dict]:
    """TEST A -- the base indexes a table of in-image code pointers (L2's test, re-implemented)."""
    q = ins[bj]
    if not q.entry or q.entry.name not in ("addu", "add"):
        return None
    for reg in (q.op(D.Ex.RS), q.op(D.Ex.RT)):
        if not reg:
            continue
        v = fold(ins, bj, reg)
        if v is None:
            continue
        rel = (v & 0x0FFFFFFF) - (img.psx_base & 0x0FFFFFFF)
        if rel % 4 or not (0 <= rel < len(img.payload) - 4):
            continue
        ptrs = 0
        for w_off in range(rel, min(rel + 256 * 4, len(img.payload) - 3), 4):
            w = struct.unpack_from("<I", img.payload, w_off)[0]
            t = (w & 0x0FFFFFFF) - (img.psx_base & 0x0FFFFFFF)
            if w and t % 4 == 0 and 0 <= t < img.header_rel:
                ptrs += 1
            else:
                break
        if ptrs >= 2:
            return {"table_rel": rel, "entries": ptrs}
    return None


def guard_evidence(ins: Sequence, k: int, span: int = 40) -> Optional[dict]:
    """TEST B -- STRUCTURALLY DIFFERENT from test A: the SWITCH GUARD.

    A compiled C ``switch`` bounds-checks its index before indexing the jump table::

        sltiu $v0, $idx, N        (or sltu against a loaded limit)
        beq   $v0, $zero, default
        ...
        jr    $vX

    An HLE call has no such guard -- the op index is a compile-time constant.  So the presence of a
    bounds compare feeding a branch that skips this jump is *independent* evidence of a dispatch,
    resting on control flow rather than on data.  Reported per site; the two tests are compared
    rather than merged (V-gate V7).
    """
    for j in range(k - 1, max(-1, k - 1 - span), -1):
        i = ins[j]
        if not i.entry:
            continue
        if i.entry.name in ("sltiu", "sltu", "slti", "slt"):
            for m in range(j, min(len(ins), j + 4)):
                b = ins[m]
                if b.entry and b.entry.name in ("beq", "bne", "blez", "bgtz", "bgez", "bltz"):
                    return {"cmp": i.text(), "cmp_off": i.off, "branch": b.text(),
                            "branch_off": b.off}
        if i.entry.name in ("bgtz", "blez", "bgez", "bltz") and i.op(D.Ex.BTARGET) is not None \
                and i.op(D.Ex.BTARGET) > ins[k].off:
            return {"cmp": "-", "cmp_off": i.off, "branch": i.text(), "branch_off": i.off}
    return None


def scaled_index_evidence(ins: Sequence, bj: int, span: int = 24) -> Optional[dict]:
    """TEST D -- the SHARPEST shape, and the one that names the idiom: the index side of the
    ``addu`` is a value SCALED BY 4 (``sll rX, rY, 2``), because a word-pointer table is indexed by
    ``4*i``.  An HLE call's table offset is a compile-time immediate and is never scaled at run
    time, so a live ``sll ...,2`` feeding the base is a dispatch and nothing else.

    Reported with its own coverage rather than merged into a single verdict: it does NOT fire when
    the scaled index was computed earlier and parked in a frame slot (ef435 ``@0x2dd8`` does exactly
    that, and is refuted by the other three tests instead).
    """
    q = ins[bj]
    if not q.entry or q.entry.name not in ("addu", "add"):
        return None
    for reg in (q.op(D.Ex.RS), q.op(D.Ex.RT)):
        if not reg:
            continue
        for j in range(bj - 1, max(-1, bj - 1 - span), -1):
            if dest_reg(ins[j]) != reg:
                continue
            i = ins[j]
            if i.entry.name == "sll" and i.op(D.Ex.SHAMT) == 2:
                return {"shift": i.text(), "off": i.off}
            break
    return None


def target_decodes(img, tbl_rel: int, entries: int, limit: int = 8) -> dict:
    """TEST C -- the table's entries POINT AT CODE: decode the first words at each target and count
    how many decode as valid instructions.  A pointer table of jump targets lands on instruction
    boundaries; a coincidence of four in-range words generally does not."""
    ok, tried = 0, 0
    for n in range(min(entries, limit)):
        w = struct.unpack_from("<I", img.payload, tbl_rel + 4 * n)[0]
        t = (w & 0x0FFFFFFF) - (img.psx_base & 0x0FFFFFFF)
        if not (0 <= t < img.header_rel - 16):
            continue
        tried += 1
        ins = decode_region(img, t, t + 16)
        if all(i.entry for i in ins):
            ok += 1
    return {"targets_tried": tried, "targets_decode": ok}


# --------------------------------------------------------------------------- V2's own const folder
def fold(ins: Sequence, k: int, reg: int, fuel: int = 8) -> Optional[int]:
    """Backward constant fold of ``reg`` at index ``k`` (searching to the top of the image).

    Independent of both the walker's lattice and L2's resolver, and unbounded rather than windowed.
    The DELAY SLOT is the caller's problem: pass ``k+2`` at a call site so the slot is in view.
    """
    if reg == R_ZERO:
        return 0
    if fuel <= 0:
        return None
    for j in range(min(k - 1, len(ins) - 1), -1, -1):
        i = ins[j]
        if dest_reg(i) != reg:
            continue
        n = i.entry.name
        if n == "lui":
            return (i.op(D.Ex.UIMM) << 16) & 0xFFFFFFFF
        if n == "li":
            v = i.op(D.Ex.SIMM)
            return ((v if v is not None else i.op(D.Ex.UIMM)) & 0xFFFFFFFF)
        if n in ("addiu", "addi", "ori", "xori", "andi"):
            src = i.op(D.Ex.RS)
            base = 0 if src == R_ZERO else fold(ins, j, src, fuel - 1)
            if base is None:
                return None
            imm = i.op(D.Ex.SIMM) if n in ("addiu", "addi") else i.op(D.Ex.UIMM)
            v = {"addiu": base + imm, "addi": base + imm, "ori": base | imm,
                 "xori": base ^ imm, "andi": base & imm}[n]
            return v & 0xFFFFFFFF
        if n == "move":
            return fold(ins, j, i.op(D.Ex.RS), fuel - 1)
        if n in ("addu", "add", "or"):
            a, b = i.op(D.Ex.RS), i.op(D.Ex.RT)
            if b == R_ZERO:
                return fold(ins, j, a, fuel - 1)
            if a == R_ZERO:
                return fold(ins, j, b, fuel - 1)
            return None
        return None
    return None


# --------------------------------------------------------------------------------- the image pass
def scan_image(img) -> dict:
    """Every VRAM-op candidate in one id-3 image, by BOTH V2 instruments, fully adjudicated."""
    ins = decode_region(img, 0, img.header_rel)
    idx_by_off = {i.off: n for n, i in enumerate(ins)}
    loads: List[Tuple[int, int]] = []                              # (index, op)
    for k, i in enumerate(ins):
        op = hle_op_of_load(i)
        if op is not None and op in VRAM_OPS:
            loads.append((k, op))

    sites: Dict[Tuple[int, int], dict] = {}                        # (call_off, op) -> record
    for k, op in loads:
        rt = ins[k].op(D.Ex.RT)
        if not rt:
            continue
        base = _load_base(ins[k])
        chain, chain_txt = base_chain(ins, k, base)
        for u in forward_uses(ins, k, rt):
            j = u["use"]
            rec = {
                "off": ins[j].off, "op": op, "via": u["via"], "load_off": ins[k].off,
                "load": ins[k].text(), "base_reg": "$" + D.REG[base],
                "chain": chain, "chain_evidence": chain_txt,
                "copies": len(u["chain"]) - 1,
                "distance": j - k,
            }
            if chain == "computed":
                bj = None
                for m in range(k - 1, -1, -1):
                    if dest_reg(ins[m]) == base:
                        bj = m
                        break
                rec["table"] = table_evidence(img, ins, bj) if bj is not None else None
                rec["scaled"] = scaled_index_evidence(ins, bj) if bj is not None else None
                if rec["table"]:
                    rec["target_decode"] = target_decodes(img, rec["table"]["table_rel"],
                                                          rec["table"]["entries"])
            rec["guard"] = guard_evidence(ins, j)
            rec["args"] = [fold(ins, j + 2, a) for a in (4, 5, 6, 7)]
            key = (rec["off"], op)
            if key not in sites or sites[key]["distance"] > rec["distance"]:
                sites[key] = rec
    return {"sites": sorted(sites.values(), key=lambda r: (r["off"], r["op"])),
            "loads": len(loads), "instrs": len(ins), "idx": idx_by_off}


def corpus_paths(corpus: str) -> List[str]:
    return sorted(os.path.join(corpus, f) for f in os.listdir(corpus)
                  if f.startswith("ef") and f.endswith(".bytes"))


def run(corpus: str = CORPUS, limit: Optional[int] = None, only: Optional[Set[int]] = None) -> dict:
    res = {"corpus": corpus, "containers": 0, "images": 0, "sites": [], "errors": [],
           "seq07": [], "tail": {"images_with_transfer": 0, "candidates": 0}}
    seq07: Set[int] = set()
    paths = corpus_paths(corpus)
    if limit:
        paths = paths[:limit]
    for path in paths:
        ef = int(os.path.basename(path)[2:5])
        if only is not None and ef not in only:
            continue
        with open(path, "rb") as fh:
            blob = fh.read()
        res["containers"] += 1
        try:                                                       # the LOADER's own VRAM write
            if any(o.code == 0x07 for o in EC.parse_op_stream(blob)):
                seq07.add(ef)
        except Exception as exc:
            res["errors"].append("ef%03d seq: %s" % (ef, exc))
        try:
            imgs = D.id3_images(blob, "ef%03d" % ef)
        except Exception as exc:
            res["errors"].append("ef%03d id3: %s" % (ef, exc))
            continue
        for img in imgs:
            res["images"] += 1
            r = scan_image(img)
            for s in r["sites"]:
                s.update(ef=ef, slot=img.chunk_slot, name=SHIPPED_NAME[s["op"]],
                         direction=("write" if s["op"] in WRITE_OPS else "read"))
                res["sites"].append(s)
            # the region beyond header_rel -- re-measured, not inherited
            tail = decode_region(img, img.header_rel, len(img.payload))
            if any(is_call(t) for t in tail):
                res["tail"]["images_with_transfer"] += 1
                for k, t in enumerate(tail):
                    op = hle_op_of_load(t)
                    if op in VRAM_OPS and t.op(D.Ex.RT) and forward_uses(tail, k, t.op(D.Ex.RT)):
                        res["tail"]["candidates"] += 1
    res["seq07"] = sorted(seq07)
    res["summary"] = summarize(res)
    return res


def _ids(sites, ops, chains=None) -> Set[int]:
    return {s["ef"] for s in sites if s["op"] in ops
            and (chains is None or s["chain"] in chains)}


def summarize(res: dict) -> dict:
    s = res["sites"]
    real = REAL_CHAINS
    out = {
        "containers": res["containers"], "images": res["images"],
        "candidates": len(s),
        "by_chain": {}, "by_op": {}, "by_via": {},
        "v2_write_real": sorted(_ids(s, WRITE_OPS, real)),
        "v2_read_real": sorted(_ids(s, READ_OPS, real)),
        "v2_write_rejected": sorted(_ids(s, WRITE_OPS) - _ids(s, WRITE_OPS, real)),
        "seq07": res["seq07"],
        "shipped_write": sorted(SHIPPED_WRITE), "shipped_read": sorted(SHIPPED_READ),
    }
    for h in s:
        for key, d in (("by_chain", h["chain"]), ("by_op", "%s(%d)" % (h["name"], h["op"])),
                       ("by_via", h["via"])):
            out[key][d] = out[key].get(d, 0) + 1
    out["derived_write"] = sorted(set(out["v2_write_real"]) | set(res["seq07"]))
    out["delta_write_new"] = sorted(set(out["derived_write"]) - SHIPPED_WRITE)
    out["delta_write_missing"] = sorted(SHIPPED_WRITE - set(out["derived_write"]))
    out["delta_read_new"] = sorted(set(out["v2_read_real"]) - SHIPPED_READ - SHIPPED_WRITE)
    out["delta_read_missing"] = sorted(SHIPPED_READ - set(out["v2_read_real"]))
    mv = [h for h in s if h["op"] == 166 and h["chain"] in real]
    out["move_sites"] = len(mv)
    out["move_dest"] = {}
    for h in mv:
        if h["args"][1] is not None and h["args"][2] is not None:
            out["move_dest"].setdefault("ef%03d" % h["ef"], []).append([h["args"][1], h["args"][2]])
    tr = [h for h in s if h["op"] in (0, 1, 166) and h["chain"] in real]
    out["rect_total"] = len(tr)
    out["rect_resolved"] = sum(1 for h in tr if h["args"][0] is not None)
    out["copies_used"] = sum(1 for h in s if h["copies"] > 0)
    out["far_sites"] = sum(1 for h in s if h["distance"] > 64)
    out["tail"] = res["tail"]
    return out


# ---------------------------------------------------------------- the DIRECTION, re-checked myself
MEMORIA_SFX = r"C:\gd\FFIX\Memoria\Assembly-CSharp\Global\SFX\SFX.cs"
_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"
DLL_CANDIDATES = [
    os.path.join(_GAME, "x64", "FF9_Data", "Plugins", "FF9SpecialEffectPlugin.dll"),
    os.path.join(_GAME, "x86", "FF9_Data", "Plugins", "FF9SpecialEffectPlugin.dll"),
]
NATIVE_FN = {0: 0x2cd0, 1: 0x2d20, 166: 0x2fe0}


def hle_table_from_dll(pe_mod, path: str) -> dict:
    """RE-DERIVE ``op index -> native fn`` FROM THE DLL, closing the last inherited link.

    Both L2's direction argument and this file's start from ``hle_ops.json``'s claim that op 0 is
    native fn ``0x2cd0``, op 1 ``0x2d20``, op 166 ``0x2fe0``.  That claim was INHERITED by both.
    Here it is re-derived from the binary: the interpreter's HLE dispatch table is an array of
    absolute 8-byte function pointers in the image, so finding the three RVAs as pointers and
    checking that their addresses are ``base + 8*op`` for ONE consistent base proves the indices
    without reading any table anyone wrote down.
    """
    pe = pe_mod.PE(path, fast_load=True)
    ib = pe.OPTIONAL_HEADER.ImageBase
    data = pe.get_memory_mapped_image()
    ptr_at: Dict[int, List[int]] = {}
    for off in range(0, len(data) - 8, 8):
        v = struct.unpack_from("<Q", data, off)[0]
        r = v - ib
        if r in (0x2cd0, 0x2d20, 0x2fe0, 0x188a0):
            ptr_at.setdefault(r, []).append(off)
    out = {"pointer_slots": {hex(k): [hex(o) for o in v] for k, v in ptr_at.items()}}
    if 0x2cd0 in ptr_at and 0x2d20 in ptr_at:
        base = ptr_at[0x2cd0][0]
        stride = ptr_at[0x2d20][0] - base
        out["table_rva"] = hex(base)
        out["stride"] = stride
        out["index_of"] = {}
        for rva, slots in ptr_at.items():
            for s in slots:
                if stride and (s - base) % stride == 0 and s >= base:
                    out["index_of"][hex(rva)] = (s - base) // stride
        out["agrees_with_hle_ops_json"] = (out["index_of"].get("0x2cd0") == 0
                                           and out["index_of"].get("0x2d20") == 1
                                           and out["index_of"].get("0x2fe0") == 166)
        # AND THE TABLE'S EXTENT, so "a table of function pointers" is not taken on faith: the
        # interpreter's op space is D.HLE_MAX_OFFSET/4 ops wide, so the array must be exactly that
        # many slots of executable pointers and no more.
        n_ops = HLE_MAX // 4
        text = next((s for s in pe.sections if s.Name.startswith(b".text")), None)
        if text is not None:
            lo, hi = text.VirtualAddress, text.VirtualAddress + text.Misc_VirtualSize
            def _in_text(k):
                off = base + 8 * k
                if not (0 <= off < len(data) - 8):
                    return False
                return lo <= struct.unpack_from("<Q", data, off)[0] - ib < hi
            out["ops"] = n_ops
            out["slots_in_text"] = sum(1 for k in range(n_ops) if _in_text(k))
            out["slots_past_end_in_text"] = sum(1 for k in range(n_ops, n_ops + 6) if _in_text(k))
            out["extent_matches_op_space"] = (out["slots_in_text"] >= n_ops - 1
                                              and out["slots_past_end_in_text"] == 0)
    return out


def check_direction() -> dict:
    """RE-CHECK op0=LoadImage / op1=StoreImage from the host side, independently of L2's path.

    L2 read the DLL through the tier-w ``refkit`` helper.  V2 does not: it maps the PE by hand with
    ``pefile`` and scans the native function's bytes for the literal ``b8|b9 xx 00 00 6x`` immediate
    that carries the callback command word, then reads Memoria's ``SFX.cs`` switch directly.  A
    second reader of the same fact is a re-derivation; a second call of the same helper is not.
    Returns ``{"instrument": "absent"}`` when the DLL or pefile is unreachable -- never a pass.
    """
    out: dict = {"dll": None, "codes": {}, "memoria": {}, "instrument": "absent"}
    try:
        import pefile                                              # noqa: F401
    except Exception:
        out["why"] = "pefile unavailable"
        pe_mod = None
    else:
        pe_mod = pefile
    path = next((p for p in DLL_CANDIDATES if os.path.isfile(p)), None)
    out["dll"] = path
    if pe_mod and path:
        pe = pe_mod.PE(path, fast_load=True)
        base = pe.OPTIONAL_HEADER.ImageBase
        data = pe.get_memory_mapped_image()
        for op, rva in NATIVE_FN.items():
            window = data[rva:rva + 0x180]
            code = None
            # the command word is a 32-bit immediate 0x6?000000 loaded into a register:
            #   b8/b9/ba/bb/bc/bd/be/bf imm32   (mov r32, imm32)
            for i in range(len(window) - 5):
                if 0xB8 <= window[i] <= 0xBF:
                    imm = struct.unpack_from("<I", window, i + 1)[0]
                    if imm & 0xFF000000 in (0x64000000, 0x65000000, 0x66000000) \
                            and imm & 0x00FFFFFF == 0:
                        code = imm
                        break
            out["codes"][op] = code
        out["instrument"] = "read"
        out["hle_table"] = hle_table_from_dll(pe_mod, path)
        del base
    # The host handler.  BOTH guard forms are recognised, because the live path is NOT a switch:
    # `BattleCallback` handles LoadImage in a bare `if (code == 100)` ABOVE its switch, and only
    # StoreImage/MoveImage arrive as `case 101:` / `case 102:`.  A parser that looked for `case`
    # alone would report LoadImage as uncased and call the direction unsettled.
    import re
    try:
        with open(MEMORIA_SFX, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        cur = None
        for n, line in enumerate(lines, 1):
            t = line.strip()
            m = re.match(r"case\s+(\d+)\s*:", t) or re.match(r"if\s*\(\s*code\s*==\s*(\d+)\s*\)", t)
            if m:
                cur = int(m.group(1))
            for k in ("LoadImage", "StoreImage", "MoveImage"):
                if "PSXTextureMgr." + k in t:
                    out["memoria"].setdefault(k, []).append({"line": n, "guard": cur,
                                                             "text": t[:110]})
    except OSError as exc:
        out["memoria_error"] = str(exc)
    # THE VERDICT, stated as a predicate rather than a name
    got = {op: (c >> 24) if c else None for op, c in out["codes"].items()}
    want = {0: 100, 1: 101, 166: 102}
    out["host_case"] = got
    out["codes_agree"] = (got == want) if out["codes"] else None
    handler = {k: sorted({e["guard"] for e in v if e["guard"] is not None})
               for k, v in out["memoria"].items()}
    out["handler_cases"] = handler
    routed = (100 in handler.get("LoadImage", ()) and 101 in handler.get("StoreImage", ())
              and 102 in handler.get("MoveImage", ()))
    out["handler_routes"] = routed
    out["verdict"] = ("op0=LoadImage(WRITE) op1=StoreImage(READ) op166=MoveImage(WRITE)"
                      if out["codes_agree"] and routed else "UNSETTLED")
    return out


# ---------------------------------------------------------------------------------- the V-gates
def load_l2() -> Optional[dict]:
    if not os.path.isfile(L2_JSON):
        return None
    with open(L2_JSON, "r", encoding="utf-8") as fh:
        return json.load(fh)


def gates(res: dict, l2: Optional[dict], sample: Optional[dict] = None) -> List[Tuple[str, bool,
                                                                                     str]]:
    g: List[Tuple[str, bool, str]] = []
    s = res["summary"]

    # V0 -- CALIBRATE THE INSTRUMENT'S OWN REGISTER MODEL against the ISA table itself.
    bad = []
    for e in D.ISA:
        kinds = [k.value for k in e.ex]
        expect = ("rd" if e.name in _WRITES_RD else "rt" if e.name in _WRITES_RT else
                  "ra" if e.name in _WRITES_RA else None)
        if expect in ("rd", "rt") and (not kinds or kinds[0] != expect):
            bad.append((e.name, kinds))
    g.append(("V0 the write model matches the ISA table (dest is always operand 0)",
              not bad, "%d mismatches %s" % (len(bad), bad[:5])))

    # V1 -- the shipped lists are re-derived by an instrument that shares no scan code with L2.
    g.append(("V1 V2 re-derives the shipped WRITE list exactly (HLE writes u seq 0x07)",
              set(s["derived_write"]) == SHIPPED_WRITE,
              "derived=%s  new=%s  missing=%s" % (s["derived_write"], s["delta_write_new"],
                                                  s["delta_write_missing"])))
    g.append(("V2 V2 re-derives the shipped READ list exactly",
              set(s["v2_read_real"]) - SHIPPED_WRITE == SHIPPED_READ,
              "derived=%s  new=%s  missing=%s" % (s["v2_read_real"], s["delta_read_new"],
                                                  s["delta_read_missing"])))
    # V3 -- the ef435 site is rejected, by V2's own chain rule, with V2's own evidence.
    e435 = [h for h in res["sites"] if h["ef"] == 435 and h["off"] == 0x2dd8]
    g.append(("V3 ef435@0x2dd8 is rejected AND carries pointer-table + guard evidence",
              bool(e435) and all(h["chain"] == "computed" and h.get("table")
                                 and h.get("guard") for h in e435),
              "%s" % [(hex(h["off"]), h["chain"], h.get("table"), bool(h.get("guard")))
                      for h in e435] or "no candidate at that offset"))
    # V4 -- F1/F2: did the unbounded/copy-propagating widening find ANY site L2's window could not?
    if l2:
        l2s = {(h["ef"], h["off"], h["op"]) for h in l2["sites"]}
        v2s = {(h["ef"], h["off"], h["op"]) for h in res["sites"]}
        extra_real = {k for k in v2s - l2s
                      if any(h["chain"] in REAL_CHAINS for h in res["sites"]
                             if (h["ef"], h["off"], h["op"]) == k)}
        g.append(("V4 the unbounded forward scan finds NO adjudicated-real site L2 missed",
                  not extra_real, "%d V2-only sites, %d of them adjudicated REAL: %s"
                  % (len(v2s - l2s), len(extra_real),
                     sorted((e, hex(o), p) for e, o, p in extra_real)[:8])))
        # V5 -- and V2 nominates everything L2 nominated (a refuter that sees less proves nothing)
        g.append(("V5 V2 nominates every L2 candidate",
                  l2s <= v2s, "%d L2 candidates, %d not nominated by V2: %s"
                  % (len(l2s), len(l2s - v2s),
                     sorted((e, hex(o), p) for e, o, p in (l2s - v2s))[:8])))
        # V6 -- the ADJUDICATIONS agree site by site, not just the summary sets
        l2chain = {(h["ef"], h["off"], h["op"]): (h["chain"] in
                                                  ("sentinel", "sentinel-spill", "sentinel-far",
                                                   "nodef"))
                   for h in l2["sites"]}
        v2chain = {(h["ef"], h["off"], h["op"]): (h["chain"] in REAL_CHAINS)
                   for h in res["sites"]}
        both = set(l2chain) & set(v2chain)
        disagree = sorted(k for k in both if l2chain[k] != v2chain[k])
        g.append(("V6 per-SITE adjudication agrees with L2 on every shared candidate",
                  not disagree, "%d shared, %d disagree: %s"
                  % (len(both), len(disagree),
                     [(e, hex(o), p, "L2real=%s V2real=%s" % (l2chain[(e, o, p)],
                                                              v2chain[(e, o, p)]))
                      for e, o, p in disagree[:6]])))
    # V7 -- FOUR refutations of the rejected class, each with its own coverage, compared rather than
    # merged.  ⚠ THE GUARD TEST IS WEAK AND IS REPORTED AS WEAK: it fires on 6 of the 23 REAL sites
    # too (a loop back-edge compare looks like a switch bounds check), so it corroborates and never
    # decides.  The deciding tests are the transfer form, the base chain, and the resolved table.
    rej = [h for h in res["sites"] if h["chain"] == "computed"]
    real = [h for h in res["sites"] if h["chain"] in REAL_CHAINS]
    tbl = [h for h in rej if h.get("table")]
    grd = [h for h in rej if h.get("guard")]
    jr = [h for h in rej if h["via"] == "jr"]
    sc = [h for h in rej if h.get("scaled")]
    dec = [h for h in tbl if h.get("target_decode", {}).get("targets_decode", 0) >= 2]
    g.append(("V7 every rejected candidate carries >=3 independent refutations (guard excluded as "
              "weak)",
              bool(rej) and all(sum((bool(h.get("table")), h["via"] == "jr",
                                     h.get("target_decode", {}).get("targets_decode", 0) >= 2))
                                >= 3 for h in rej),
              "rejected=%d  table=%d  via-jr=%d  targets-decode=%d  scaled-index=%d  | guard fires "
              "on %d of %d rejected AND on %d of %d REAL -> corroborating only"
              % (len(rej), len(tbl), len(jr), len(dec), len(sc), len(grd), len(rej),
                 sum(1 for h in real if h.get("guard")), len(real))))
    # V8 -- the two discriminators (transfer form vs base chain) must partition identically, and if
    # they ever diverge the DIVERGENCE is the finding.  Asserted, not assumed.
    byvia = {(h["ef"], h["off"], h["op"]) for h in res["sites"] if h["via"] == "jalr"}
    bych = {(h["ef"], h["off"], h["op"]) for h in res["sites"] if h["chain"] in REAL_CHAINS}
    g.append(("V8 via-jalr and sentinel-chain partition V2's candidates identically",
              byvia == bych, "jalr=%d chain-real=%d symdiff=%d %s"
              % (len(byvia), len(bych), len(byvia ^ bych),
                 sorted((e, hex(o), p) for e, o, p in (byvia ^ bych))[:6])))
    # V9 -- MOVEIMAGE_HARD_CELLS, re-derived by V2's own folder
    dest = {ef: tuple(v[0]) for ef, v in s["move_dest"].items()}
    want = {"ef%03d" % k: v for k, v in SHIPPED_HARD.items()}
    g.append(("V9 MOVEIMAGE_HARD_CELLS re-derived by V2's const folder",
              dest == want, "%s (shipped %s)" % (dest, want)))
    # V10 -- the tail region, re-measured
    g.append(("V10 no VRAM-op candidate lives beyond header_rel",
              res["tail"]["candidates"] == 0,
              "%d images carry a transfer there, %d candidates"
              % (res["tail"]["images_with_transfer"], res["tail"]["candidates"])))
    # V11 -- the DIRECTION, re-read by V2's own PE reader
    d = res.get("direction") or {}
    if d.get("instrument") != "read":
        g.append(("V11 op0=LoadImage / op1=StoreImage, re-read from the DLL + Memoria",
                  False, "INSTRUMENT ABSENT (%s) -- direction stays INHERITED"
                  % (d.get("why") or d.get("dll") or "no DLL")))
    else:
        g.append(("V11 op0=LoadImage / op1=StoreImage, re-read from the DLL + Memoria",
                  bool(d.get("codes_agree")) and d["verdict"] != "UNSETTLED",
                  "codes=%s -> cases=%s ; handler guards=%s ; %s"
                  % ({k: hex(v) if v else None for k, v in d["codes"].items()}, d["host_case"],
                     d.get("handler_cases"), d["verdict"])))
        # V11b -- the LAST INHERITED LINK, closed.  Both L2 and this file started from
        # hle_ops.json's "op 0 IS native fn 0x2cd0".  Re-derived from the DLL's own dispatch table.
        t = d.get("hle_table") or {}
        g.append(("V11b op index -> native fn re-derived from the DLL's dispatch table",
                  bool(t.get("agrees_with_hle_ops_json")) and bool(t.get("extent_matches_op_space")),
                  "table @%s stride %s: %s ; extent %s/%s slots executable, %s past the end"
                  % (t.get("table_rva"), t.get("stride"), t.get("index_of"),
                     t.get("slots_in_text"), t.get("ops"), t.get("slots_past_end_in_text"))))
    # V12 -- THE BLIND SAMPLE: 20 L2-CLEAN images + every L2-flagged image, re-scanned in isolation
    if sample:
        g.append(("V12 blind sample: V2 finds no adjudicated-real site in L2-CLEAN containers",
                  not sample["clean_real_hits"],
                  "%d clean containers sampled (%s), %d real hits; %d flagged containers re-scanned,"
                  " hit-set identical: %s"
                  % (len(sample["clean_sample"]), sample["clean_sample"][:8],
                     len(sample["clean_real_hits"]), len(sample["flagged"]),
                     sample["flagged_match"])))
    # V13 -- SET ACCOUNTING per set, the sec 1.6 item 4 discipline
    lhs_w = set(s["v2_write_real"]) | set(s["seq07"])
    ok = (lhs_w == SHIPPED_WRITE
          and (set(s["v2_read_real"]) - SHIPPED_WRITE) == SHIPPED_READ
          and not (SHIPPED_WRITE & SHIPPED_READ))
    g.append(("V13 set accounting closes per SET (write / read / disjoint / union)",
              ok, "write=%d(hle %d u seq %d) read=%d overlap=%s union=%d"
              % (len(lhs_w), len(s["v2_write_real"]), len(s["seq07"]),
                 len(set(s["v2_read_real"]) - SHIPPED_WRITE),
                 sorted(SHIPPED_WRITE & SHIPPED_READ), len(SHIPPED_WRITE | SHIPPED_READ))))
    return g


# ------------------------------------------------------------------------------- the blind sample
def blind_sample(res_all: dict, l2: dict, corpus: str, n: int = 20, seed: int = 20260728) -> dict:
    """LANE TASK 2 -- re-scan, in isolation, 20 randomly chosen containers L2 reported CLEAN plus
    EVERY container L2 flagged, and compare hit sets.  The point of re-running in isolation is that
    a corpus-wide pass can hide a per-image defect behind an aggregate."""
    flagged = sorted({h["ef"] for h in l2["sites"]})
    all_ef = sorted(int(os.path.basename(p)[2:5]) for p in corpus_paths(corpus))
    clean = [e for e in all_ef if e not in flagged]
    rng = random.Random(seed)
    sample = sorted(rng.sample(clean, min(n, len(clean))))
    r_clean = run(corpus, only=set(sample))
    r_flag = run(corpus, only=set(flagged))
    l2set = {(h["ef"], h["off"], h["op"]) for h in l2["sites"]}
    v2set = {(h["ef"], h["off"], h["op"]) for h in r_flag["sites"]}
    return {
        "clean_sample": sample,
        "clean_candidates": [(h["ef"], hex(h["off"]), h["op"], h["chain"])
                             for h in r_clean["sites"]],
        "clean_real_hits": [(h["ef"], hex(h["off"]), h["op"]) for h in r_clean["sites"]
                            if h["chain"] in REAL_CHAINS],
        "flagged": flagged,
        "flagged_match": sorted(l2set) == sorted(v2set & l2set) and not (l2set - v2set),
        "flagged_v2_only": sorted((e, hex(o), p) for e, o, p in (v2set - l2set)),
        "flagged_l2_only": sorted((e, hex(o), p) for e, o, p in (l2set - v2set)),
    }


# -------------------------------------------------------------------- the two independent closures
def residual_probe(corpus: str = CORPUS) -> dict:
    """THE RESIDUAL CLASS -- the strongest form of "no site was missed", and it is not a sweep.

    L2 defended its window by SWEEPING it (8..256, same answer).  A sweep can only show that a
    windowed instrument is insensitive to its own constant.  This asks the question with no window
    at all: enumerate EVERY ``lw rT, 4*op(rB)`` in the corpus whose base provably chains to
    ``*(x+0x10)``, then ask how many of them ever reach a control transfer.  A load that never
    reaches one is not a call site; a load that reaches one is already a candidate.  The only way a
    site could hide is a fn pointer SPILLED to the frame between load and call, so that is counted
    separately.

    Reported numbers: sentinel-class loads, of which with-a-use (== the candidate count), of which
    the residual, of which spilled.  The residual is then CHARACTERISED, not just counted -- these
    are ordinary struct dereferences whose offset happens to equal ``4*op`` (op 0's offset is 0).
    """
    out = {"chains": {}, "sentinel_loads": 0, "with_use": 0, "residual": [], "spilled": [],
           "residual_consumed_by": {}}
    for p in corpus_paths(corpus):
        ef = int(os.path.basename(p)[2:5])
        with open(p, "rb") as fh:
            blob = fh.read()
        try:
            imgs = D.id3_images(blob, "ef%03d" % ef)
        except Exception:
            continue
        for img in imgs:
            ins = decode_region(img, 0, img.header_rel)
            for k, i in enumerate(ins):
                op = hle_op_of_load(i)
                if op not in VRAM_OPS:
                    continue
                rt = i.op(D.Ex.RT)
                if not rt:
                    continue
                ch, _ = base_chain(ins, k, i.base_reg)
                out["chains"][ch] = out["chains"].get(ch, 0) + 1
                if ch not in REAL_CHAINS:
                    continue
                out["sentinel_loads"] += 1
                if forward_uses(ins, k, rt):
                    out["with_use"] += 1
                    continue
                out["residual"].append([ef, i.off, op])
                for j in range(k + 1, min(len(ins), k + 40)):
                    q = ins[j]
                    if q.entry and q.entry.name == "sw" and q.op(D.Ex.RT) == rt:
                        out["spilled"].append([ef, i.off, op, q.off])
                        break
                    if dest_reg(q) == rt:
                        nm = q.entry.name if q.entry else "?"
                        out["residual_consumed_by"][nm] = \
                            out["residual_consumed_by"].get(nm, 0) + 1
                        break
    return out


def walk_cross(corpus: str = CORPUS) -> dict:
    """CROSS-CHECK L2's C7/C8 with the walker RUN HERE, not with L2's recorded walk.

    Three facts are re-measured: every walk-confirmed VRAM site is nominated by V2; the ONLY walk
    site V2 rejects is the already-refuted ef435; and the sites the walk never reached are exactly
    the six ``StoreImage`` ids the record names.  It also counts the walker's ``hle_multi`` merges,
    which is the shape a dynamically dispatched transfer op would take -- L2 named that as an
    uncovered class; here it is MEASURED.
    """
    hle = D.load_hle_names()
    res = run(corpus)
    v2 = {(s["ef"], s["off"], s["op"]) for s in res["sites"]}
    v2real = {(s["ef"], s["off"], s["op"]) for s in res["sites"] if s["chain"] in REAL_CHAINS}
    walk, reach, multi = set(), [], []
    for p in corpus_paths(corpus):
        ef = int(os.path.basename(p)[2:5])
        with open(p, "rb") as fh:
            blob = fh.read()
        try:
            imgs = D.id3_images(blob, "ef%03d" % ef)
        except Exception:
            continue
        for img in imgs:
            r = D.walk_image(img, hle_names=hle)
            reach.append(r.coverage)
            for c in r.calls:
                if c.kind == "hle" and c.hle_op in VRAM_OPS:
                    walk.add((ef, c.off, c.hle_op))
                elif c.kind == "hle_multi":
                    multi.append([ef, c.off, str(c.hle_name)])
    return {
        "mean_reachability": sum(reach) / len(reach) if reach else None,
        "walk_sites": len(walk),
        "walk_not_nominated_by_v2": sorted(walk - v2),
        "walk_rejected_by_v2": sorted(walk - v2real),
        "v2_real_never_walked": sorted(v2real - walk),
        "hle_multi_total": len(multi),
        "hle_multi_naming_a_vram_op": [m for m in multi if any(
            k in m[2] for k in ("LoadImage", "StoreImage", "MoveImage", "TexAnim"))],
    }


# ------------------------------------------------------------------------------------ the listing
def listing(corpus: str, ef: int, span: int = 12) -> str:
    path = os.path.join(corpus, "ef%03d.bytes" % ef)
    with open(path, "rb") as fh:
        blob = fh.read()
    L = ["ef%03d -- every V2 candidate, disassembled" % ef]
    for img in D.id3_images(blob, "ef%03d" % ef):
        ins = decode_region(img, 0, img.header_rel)
        r = scan_image(img)
        for s in r["sites"]:
            k = next(n for n, i in enumerate(ins) if i.off == s["off"])
            L.append("")
            L.append("  @+%#06x  op %-3d (%s)  via %-4s  chain=%s"
                     % (s["off"], s["op"], SHIPPED_NAME[s["op"]], s["via"], s["chain"]))
            L.append("    %s" % s["chain_evidence"])
            if s.get("table"):
                L.append("    TABLE: image+%#x, %d in-image pointers, %s"
                         % (s["table"]["table_rel"], s["table"]["entries"],
                            s.get("target_decode")))
            if s.get("guard"):
                L.append("    GUARD: %s  ->  %s" % (s["guard"]["cmp"], s["guard"]["branch"]))
            L.append("    args a0..a3 = %s" % s["args"])
            for j in range(max(0, k - span), min(len(ins), k + 3)):
                L.append("      %s+%#06x  %s" % (">" if j == k else " ", ins[j].off,
                                                 ins[j].text()))
    return "\n".join(L)


def report(res: dict, l2: Optional[dict], sample: Optional[dict]) -> str:
    s = res["summary"]
    L = ["W6b-2 V2 THE REFUTER -- %d containers, %d id-3 images, %d candidates"
         % (s["containers"], s["images"], s["candidates"]), ""]
    L.append("CANDIDATES  by chain %s" % s["by_chain"])
    L.append("            by op    %s" % s["by_op"])
    L.append("            by via   %s" % s["by_via"])
    L.append("            copy-propagated chains: %d   sites >64 instructions from their load: %d"
             % (s["copies_used"], s["far_sites"]))
    L.append("")
    L.append("SET ACCOUNTING")
    L.append("  WRITE  V2 HLE real = %s" % s["v2_write_real"])
    L.append("         seq op 0x07 = %s" % s["seq07"])
    L.append("         V2 derived  = %s" % s["derived_write"])
    L.append("         SHIPPED     = %s" % s["shipped_write"])
    L.append("         delta new=%s missing=%s" % (s["delta_write_new"] or "NONE",
                                                   s["delta_write_missing"] or "NONE"))
    L.append("  READ   V2 real     = %s" % s["v2_read_real"])
    L.append("         SHIPPED     = %s" % s["shipped_read"])
    L.append("         delta new=%s missing=%s" % (s["delta_read_new"] or "NONE",
                                                   s["delta_read_missing"] or "NONE"))
    L.append("  REJECTED (computed base) = %s" % s["v2_write_rejected"])
    L.append("")
    L.append("MOVEIMAGE dest const-folded: %s   RECT* resolved %d of %d"
             % (s["move_dest"], s["rect_resolved"], s["rect_total"]))
    L.append("TAIL beyond header_rel: %d images with a transfer, %d candidates"
             % (res["tail"]["images_with_transfer"], res["tail"]["candidates"]))
    L.append("")
    L.append("V-GATES")
    for name, ok, ev in gates(res, l2, sample):
        L.append("  [%s] %s -- %s" % ("PASS" if ok else "FAIL", name, ev))
    if res["errors"]:
        L.append("ERRORS %d: %s" % (len(res["errors"]), res["errors"][:5]))
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", default=CORPUS)
    ap.add_argument("--out", default=os.path.join(OUT_DIR, "v2_check.json"))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--gates", action="store_true")
    ap.add_argument("--sample", type=int, default=20)
    ap.add_argument("--no-sample", action="store_true")
    ap.add_argument("--listing", type=int, default=None, metavar="EF")
    ap.add_argument("--residual", action="store_true",
                    help="the window-free residual probe (no site can hide)")
    ap.add_argument("--walk-cross", action="store_true",
                    help="re-run the walker here and cross-check L2's C7/C8")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.corpus):
        print("no corpus at %s" % a.corpus)
        return 2
    if a.listing is not None:
        print(listing(a.corpus, a.listing))
        return 0
    if a.residual:
        r = residual_probe(a.corpus)
        print("base-chain census over every offset-matching load: %s" % r["chains"])
        print("SENTINEL-class VRAM-op loads     %d" % r["sentinel_loads"])
        print("  ...that reach a control transfer %d   (== the candidate count)" % r["with_use"])
        print("  ...RESIDUAL (never reach one)    %d" % len(r["residual"]))
        print("  ...of the residual, fn ptr SPILLED to the frame: %d  %s"
              % (len(r["spilled"]), r["spilled"][:6]))
        print("  ...the residual's actual consumer, by instruction: %s"
              % r["residual_consumed_by"])
        with open(os.path.join(OUT_DIR, "v2_residual.json"), "w", encoding="utf-8") as fh:
            json.dump(r, fh, indent=1)
        return 0
    if a.walk_cross:
        r = walk_cross(a.corpus)
        for k, v in r.items():
            print("  %-28s %s" % (k, v))
        with open(os.path.join(OUT_DIR, "v2_walkcross.json"), "w", encoding="utf-8") as fh:
            json.dump(r, fh, indent=1)
        return 0
    res = run(a.corpus, limit=a.limit)
    res["direction"] = check_direction()
    l2 = load_l2()
    sample = None
    if l2 and not a.no_sample:
        sample = blind_sample(res, l2, a.corpus, n=a.sample)
        res["blind_sample"] = sample
    if a.gates:
        bad = 0
        for name, ok, ev in gates(res, l2, sample):
            print("[%s] %s -- %s" % ("PASS" if ok else "FAIL", name, ev))
            bad += 0 if ok else 1
        return 1 if bad else 0
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(report(res, l2, sample))
    print("\nwrote %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
