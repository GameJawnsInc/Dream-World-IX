r"""W6b-2 lane L2 -- THE WRITE SCAN.  `py w6b2_write_scan.py` re-derives the program-VRAM **WRITE**
set from the corpus bytes with an instrument that does not depend on reachability.

THE QUESTION (recon Q2, `W6b-SCENERY.md` sec 7.2 row 2): *is the program-VRAM WRITE list missing
writes?*  `repaint.PROGRAM_VRAM_WRITE_IDS` was derived by a const-folding reachability walk whose
mean reachability is 0.905 -- a LOWER bound, and six real ``StoreImage`` sites were found only by an
independent linear call-shape scan.  Only the READ op's extras were ever adopted.

THE INSTRUMENT.  Three scans over the same 385 id-3 program images, reported side by side, because a
number with one instrument behind it is a restatement:

  WALK      tier-r's const-folding :class:`ImageWalker` -- reachability-bounded, the shipped lists'
            own derivation.  Read-only import; this file never edits tier-r.
  LINEAR-G6 a FAITHFUL reproduction of ``w6b_gates._walk_program_vram``'s linear scan (lookback 12
            instructions, first ``lw`` of the target register wins, region ``[0, header_rel)``).
            It exists to CALIBRATE: if this file cannot re-find G6's own answer, its own answer is
            not evidence.
  LINEAR-L2 this lane's scan.  Four widenings over LINEAR-G6, each named so the delta is
            attributable rather than atmospheric:
              W1  the nearest DEFINITION of the target register, not the nearest ``lw`` -- an
                  intervening ``addu``/``move`` means the ``lw`` behind it defines something else.
              W2  lookback 64 instead of 12 (a fn-pointer load hoisted out of a loop would be
                  >12 instructions from its ``jalr``).  MEASURED NULL: swept 8..256, the candidate
                  count never moves -- reported as null rather than quietly kept.
              W3  ``jr $rX`` (rX != $ra) as well as ``jalr`` -- the walker already treats it as a
                  call; the linear scan did not.  It adds 54 candidates and ALL 54 are the ef435
                  switch-dispatch shape, which is exactly why W4 exists.
              W4  the BASE-CHAIN adjudication the walker lacks -- ``base = *(sysStruct + 0x10)``.
                  This is the ef435 discriminator, applied to every hit rather than to one.

THE HLE CALL SHAPE LAW (R1): an HLE call is ``lw $vX, (4*op)($sysStruct+0x10)`` followed by
``jalr $vX`` -- the op index falls out of the load offset.

THE OP IDENTITIES are VERIFIED, not assumed: sec 7.2 names "op 0 and op 166" as the writes, and this
file re-derives the arity/kind signature of ops 0/1/166 from ``hle_ops.json`` before using them
(:func:`verify_op_identities`) -- and REPORTS the one thing the corpus cannot settle, which of the
two arity-2 ``pp`` ops is Load and which is Store.

PROVENANCE.  Zero Square-Enix bytes.  It reads the SE-derived corpus at ``C:\gd\SCRATCH\summon-format``
and writes its listings and dossier under ``C:\gd\SCRATCH\summon-format\texel-w6b\w6b2\``; nothing
decoded ever lands in the checkout.  No install read, no deploy, no git.

Usage
-----
    py w6b2_write_scan.py                 # full run -> write_scan.json + the console report
    py w6b2_write_scan.py --calibrate     # ONLY the calibration gates (C1..C13)
    py w6b2_write_scan.py --sweep         # lookback sensitivity (walk-free)
    py w6b2_write_scan.py --explain 435   # the adjudicated listing around one effect's hits
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from typing import Dict, List, Optional, Sequence, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "tier-r"))

import reskin as RS                                              # noqa: E402,F401  (sets sys.path)
import summon_camera as W                                        # noqa: E402
import tier_r_disasm as D                                        # noqa: E402
from ff9mapkit.summons import container as EC                    # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402

CORPUS = W.SCRATCH_CORPUS
OUT_DIR = os.path.join(CORPUS, "texel-w6b", "w6b2")

# --------------------------------------------------------------------------- THE OPS UNDER TEST
#: The four VRAM-transfer HLE ops, in `w6b_gates`' own naming so the two files can be diffed.
#: DIRECTION (W6b-SCENERY sec 1.6 item 1): Load/Move are WRITES, Store is a READ.
VRAM_OPS = {0: "LoadImage", 1: "StoreImage", 166: "MoveImage", 12: "TexAnimArm"}
WRITE_OPS = (0, 166, 12)
READ_OPS = (1,)

#: What the SHIPPED lists say, quoted here ONLY to be compared against a fresh derivation.
SHIPPED_WRITE = frozenset(RP.PROGRAM_VRAM_WRITE_IDS)
SHIPPED_READ = frozenset(RP.PROGRAM_VRAM_READ_IDS)
SHIPPED_HARD_CELLS = dict(RP.MOVEIMAGE_HARD_CELLS)

#: `w6b_gates`' own re-derivation constants -- the calibration targets.  If this file's WALK and
#: LINEAR-G6 instruments do not reproduce these, nothing else it prints is evidence.
CAL_WALK_LOADIMAGE = frozenset((149, 435))
CAL_WALK_MOVEIMAGE = frozenset((1, 142, 144, 149, 274))
CAL_WALK_STOREIMAGE = frozenset((7, 72, 149, 211, 214, 276, 390))
CAL_WALK_TEXANIM = frozenset((38,))
CAL_LINEAR_G6_WRITE = frozenset((1, 142, 144, 149, 274))
CAL_LINEAR_ONLY_STORE = frozenset((151, 152, 225, 445, 460, 510))
CAL_MOVE_DEST = (704, 256)
CAL_EF435_SITE = 0x2dd8

LOOKBACK_G6 = 12
LOOKBACK_L2 = 64
ARG_REGS = (4, 5, 6, 7)                    # $a0..$a3
R_RA = 31

#: instructions whose FIRST operand is the GPR they write.  Everything else in the ISA either writes
#: no GPR (stores, branches, cop-register moves, mult/div) or writes $ra implicitly (jal, *al).
_DEST_OPS0 = frozenset((
    "sll", "sra", "srl", "move", "mfhi", "mflo", "add", "addu", "and", "xor", "srlv", "sub", "subu",
    "nor", "or", "sllv", "slt", "sltu", "srav", "addi", "addiu", "slti", "sltiu", "andi", "ori",
    "xori", "li", "lui", "lb", "lh", "lwl", "lw", "lbu", "lhu", "lwr",
    "cfc0", "cfc1", "cfc2", "cfc3", "mfc0", "mfc1", "mfc2", "mfc3", "jalr"))
_WRITES_RA = frozenset(("jal", "bltzal", "bgezal"))


def dest_reg(ins) -> Optional[int]:
    """The GPR this instruction writes, or ``None``.  ``$zero`` counts as no write."""
    if not ins.entry:
        return None
    n = ins.entry.name
    if n in _WRITES_RA:
        return R_RA
    if n in _DEST_OPS0 and ins.ops:
        r = ins.ops[0]
        return r if r else None
    return None


# --------------------------------------------------------------------------- op-identity check
def verify_op_identities(path: str = None) -> dict:
    """RE-DERIVE what ``hle_ops.json`` actually says about ops 0 / 1 / 166 before trusting sec 7.2.

    The claim under test is *"the WRITE ops are op 0 (LoadImage) and op 166 (MoveImage)"*.  What the
    table can support is stated separately from what it cannot: the PSX prototypes are
    ``LoadImage(RECT*, u_long*)`` / ``StoreImage(RECT*, u_long*)`` / ``MoveImage(RECT*, int, int)``,
    so op 166's ``pii`` arity-3 signature identifies MoveImage UNIQUELY, while ops 0 and 1 are BOTH
    arity-2 ``pp`` and the corpus alone cannot say which is which.
    """
    path = path or os.path.join(_HERE, "..", "tier-r", "hle_ops.json")
    with open(path, "r", encoding="utf-8") as fh:
        rows = {int(r["op"]): r for r in json.load(fh)}
    out = {"table": path, "ops": {}}
    for op in (0, 1, 166, 12):
        r = rows.get(op, {})
        out["ops"][op] = {
            "arity": r.get("arity"), "arg_kinds": r.get("arg_kinds"), "returns": r.get("returns"),
            "native_fn": r.get("native_fn"), "touches": r.get("touches"),
            "name": r.get("name"), "call_sites": r.get("call_sites"), "effects": r.get("effects"),
        }
    a, b, m = out["ops"][0], out["ops"][1], out["ops"][166]
    out["moveimage_unique"] = (m["arity"] == 3 and m["arg_kinds"] == "pii")
    out["load_store_ambiguous"] = (a["arity"] == b["arity"] == 2
                                   and a["arg_kinds"] == b["arg_kinds"] == "pp")
    out["both_touch_vram"] = ("vramUploadCallback" in (a["touches"] or ())
                              and "vramUploadCallback" in (b["touches"] or ()))
    #: THE DISCRIMINATOR THE CORPUS DOES CARRY -- direction is a per-op population fact, not a name:
    #: whichever of {0, 1} is the WRITE is the one the shipped lists treat as a write, and BOTH are
    #: reported so a reader can see the swap risk instead of inheriting it.
    out["op0_effects"], out["op1_effects"] = a["effects"], b["effects"]
    return out


#: DLL function RVAs for the three transfer ops, as `hle_ops.json` records them.
NATIVE_FN = {0: 0x2cd0, 1: 0x2d20, 166: 0x2fe0}
#: what each native fn passes as the host callback command word, and what Memoria's own handler does
#: with it (`SFX.cs` dispatches on `code >> 24`).
HOST_CASE = {0: 100, 1: 101, 166: 102}
MEMORIA_SFX = os.path.join("C:", os.sep, "gd", "FFIX", "Memoria", "Assembly-CSharp",
                           "Global", "SFX", "SFX.cs")


def verify_op_direction_from_dll(arch: str = "x64") -> Optional[dict]:
    """SETTLE Load-vs-Store from the ENGINE, because the corpus cannot.

    ops 0 and 1 are both arity-2 ``pp`` and both touch ``vramUploadCallback``, so nothing in
    `hle_ops.json` distinguishes an upload from a readback -- and the whole DIRECTION LAW (and with
    it the 113 cells W6b-1 moved from REFUSE to DISCLOSE, and the ef211 cast's licence) hangs on
    which is which.  The evidence that does settle it is one layer down and read-only:

      * each native fn loads ONE callback pointer (all three: the same one) and passes a command
        word -- ``0x64000000`` (fn 0x2cd0, op 0), ``0x65000000`` (fn 0x2d20, op 1),
        ``0x66000000`` (fn 0x2fe0, op 166);
      * Memoria's ``SFX.HonoluluCallback``/``DebugRoomCallback`` switch on ``code >> 24`` and route
        **100 -> PSXTextureMgr.LoadImage, 101 -> StoreImage, 102 -> MoveImage**.

    So op 0 IS LoadImage and op 1 IS StoreImage, by the host's own handler names.  Returns ``None``
    when the DLL or capstone/pefile is unreachable -- an ABSENT instrument, never a passing one.
    """
    sys.path.insert(0, os.path.join(_HERE, "..", "thomas-swap", "disasm"))
    try:
        import refkit
        pe = refkit.load(arch)
        fns = refkit.functions(pe)
    except Exception:                                            # pragma: no cover - env dependent
        return None
    out = {"arch": arch, "codes": {}, "host_case": {}, "memoria_lines": {}}
    for op, rva in NATIVE_FN.items():
        rng = refkit.func_of(fns, rva) or (rva, rva + 0x140)
        code = None
        for ins in refkit.disasm(pe, rng[0], rng[1]):
            if ins.mnemonic == "mov" and ins.op_str.startswith("ecx, 0x6"):
                code = int(ins.op_str.split(", ")[1], 16)
                break
        out["codes"][op] = code
        out["host_case"][op] = (code >> 24) if code else None
    out["agrees"] = out["host_case"] == HOST_CASE
    try:                                                         # the host handler, quoted by line
        with open(MEMORIA_SFX, "r", encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                t = line.strip()
                if t.startswith("PSXTextureMgr.") and any(
                        k in t for k in ("LoadImage", "StoreImage", "MoveImage")):
                    out["memoria_lines"]["%s:%d" % (os.path.basename(MEMORIA_SFX), n)] = t
    except OSError:
        pass
    return out


# --------------------------------------------------------------------------- the three scans
def _decode_region(img, lo: int, hi: int) -> List:
    dec = D.DEFAULT_DECODER
    pay = img.payload
    hi = min(hi, len(pay))
    return [dec.decode(struct.unpack_from("<I", pay, o)[0], o, img.psx_base)
            for o in range(lo, max(lo, hi - 3), 4)]


def scan_linear_g6(ins: Sequence) -> List[dict]:
    """LINEAR-G6: `w6b_gates._walk_program_vram`'s scan, transcribed operationally.

    Deliberately NOT imported: a reproduction that shares the code proves the code runs, not that the
    number is re-derivable.  This one is a re-implementation from the documented shape.
    """
    hits: List[dict] = []
    for k, i in enumerate(ins):
        if not i.entry or i.entry.name != "jalr" or len(i.ops) < 2:
            continue
        treg = i.ops[1]
        for j in range(k - 1, max(-1, k - 1 - LOOKBACK_G6), -1):
            p = ins[j]
            if not p.entry or p.entry.name != "lw" or p.ops[0] != treg:
                continue
            imm = p.ops[1]
            op = imm // 4 if imm % 4 == 0 else -1
            if not (0 <= imm < D.HLE_MAX_OFFSET) or op not in VRAM_OPS:
                break
            hits.append({"off": i.off, "op": op, "load_off": j})
            break
    return hits


def _resolve_const(ins: Sequence, k: int, reg: int, depth: int = 64,
                   _fuel: int = 6) -> Tuple[Optional[int], str]:
    """Backward const-fold of one GPR at instruction index ``k``.  ``(value, evidence)``.

    Independent of the walker's forward lattice ON PURPOSE: a site the walk never reached has no
    lattice state, so a new hit's arguments need an instrument that does not require reachability.
    Calibrated against the walk's own answer on the five MoveImage sites (gate C3).
    """
    if reg == 0:
        return 0, "$zero"
    if _fuel <= 0:
        return None, "chain too deep"
    start = min(k - 1, len(ins) - 1)                    # callers pass k+2 to include the delay slot
    for j in range(start, max(-1, k - 1 - depth), -1):
        i = ins[j]
        if dest_reg(i) != reg:
            continue
        n = i.entry.name
        if n in ("addiu", "addi", "ori", "xori", "li"):
            if n == "li":
                return i.ops[1] & 0xFFFFFFFF, "%s @+%#x" % (i.text(), i.off)
            base, ev = (0, "$zero") if i.ops[1] == 0 else _resolve_const(ins, j, i.ops[1], depth,
                                                                        _fuel - 1)
            if base is None:
                return None, "%s @+%#x (base $%s unresolved)" % (i.text(), i.off, D.REG[i.ops[1]])
            v = (base + i.ops[2]) if n in ("addiu", "addi") else (
                base | i.ops[2] if n == "ori" else base ^ i.ops[2])
            return v & 0xFFFFFFFF, "%s @+%#x <- %s" % (i.text(), i.off, ev)
        if n == "lui":
            return (i.ops[1] << 16) & 0xFFFFFFFF, "%s @+%#x" % (i.text(), i.off)
        if n == "move":
            return _resolve_const(ins, j, i.ops[1], depth, _fuel - 1)
        if n in ("addu", "add") and (i.ops[1] == 0 or i.ops[2] == 0):
            src = i.ops[2] if i.ops[1] == 0 else i.ops[1]
            return _resolve_const(ins, j, i.ops[1 if i.ops[2] == 0 else 2], depth, _fuel - 1) \
                if src else (0, "$zero")
        return None, "defined by %s @+%#x" % (i.text(), i.off)
    return None, "no definition within %d instructions" % depth


#: chains that ADJUDICATE REAL.  ``sentinel``/``sentinel-spill``/``sentinel-far`` see the
#: ``*(sysStruct+0x10)`` load itself; ``nodef`` is a callee-saved register loaded in a prologue this
#: window cannot see, which is what every walk-CONFIRMED site with a hoisted base looks like.
REAL_CHAINS = ("sentinel", "sentinel-spill", "sentinel-far", "nodef")


def classify_base_chain(ins: Sequence, defj: int, base: int,
                        lookback: int = LOOKBACK_L2) -> Tuple[str, str]:
    """W4 -- adjudicate the HLE table BASE of the fn-pointer load at index ``defj``.

    THE DISCRIMINATOR (the ef435 refutation, generalised from one site to every site): a real HLE
    call loads its function pointer out of ``*(sysStruct + 0x10)``; the false positive loads it out
    of the image's OWN pointer table, whose base is COMPUTED (``addu``) from an index.  Three shapes
    resolve to the sentinel and they all had to be handled, because a classifier that rejects real
    calls hardens a list by losing evidence:

    * ``lw base, 0x10($rX)``                       -- the sentinel load, in view;
    * ``lw base, N($sp)`` after ``sw rY, N($sp)``  -- the base SPILLED in the prologue and reloaded
      (this is the shared ``StoreImage`` boilerplate of ef007/072/151/211/214/225/276: ef211 does
      ``lw $t3, 16($s0)`` @+0x80, ``sw $t3, 160($sp)`` @+0x8c, then ``lw $t3, 160($sp)`` @+0x560);
    * no definition in the window at all -- a callee-saved register set in a prologue further back
      than any sane window, which is what ef038/ef149/ef390/ef001's walk-confirmed sites look like.
    """
    def _near(stop: int, reg: int, span: int) -> Optional[int]:
        for j in range(stop, max(-1, stop - span), -1):
            if dest_reg(ins[j]) == reg:
                return j
        return None

    basej = _near(defj - 1, base, lookback)
    if basej is None:
        far = _near(defj - 1, base, defj + 1)
        if far is not None and ins[far].entry.name == "lw" \
                and ins[far].ops[1] == D.HLE_STRUCT_FIELD:
            return ("sentinel-far", "%s @+%#x = *(sysStruct+0x10), %d instructions back"
                    % (ins[far].text(), ins[far].off, defj - far))
        return ("nodef", "$%s not defined within %d instructions (hoisted or a parameter)"
                % (D.REG[base], lookback))
    q = ins[basej]
    if q.entry.name == "lw" and q.ops[1] == D.HLE_STRUCT_FIELD:
        return ("sentinel", "%s @+%#x = *(sysStruct+0x10)" % (q.text(), q.off))
    if q.entry.name == "lw" and q.ops[2] in (29, 30):            # $sp / $fp -- a spill reload
        off = q.ops[1]
        for j in range(basej - 1, -1, -1):
            r = ins[j]
            if r.entry and r.entry.name == "sw" and r.ops[1] == off and r.ops[2] == q.ops[2]:
                src = _near(j - 1, r.ops[0], lookback)
                if src is not None and ins[src].entry.name == "lw" \
                        and ins[src].ops[1] == D.HLE_STRUCT_FIELD:
                    return ("sentinel-spill",
                            "%s @+%#x <- %s @+%#x <- %s @+%#x = *(sysStruct+0x10)"
                            % (q.text(), q.off, r.text(), r.off, ins[src].text(), ins[src].off))
                return ("spill-other", "%s @+%#x <- %s @+%#x (source not the sentinel load)"
                        % (q.text(), q.off, r.text(), r.off))
        return ("spill-unresolved", "%s @+%#x -- no matching sw into that frame slot"
                % (q.text(), q.off))
    if q.entry.name == "lw":
        return ("lw-other", "%s @+%#x -- base loaded at +%#x, NOT +0x10"
                % (q.text(), q.off, q.ops[1]))
    return ("computed", "%s @+%#x -- base COMPUTED, the ef435 pointer-table shape" % (q.text(),
                                                                                      q.off))


def pointer_table_evidence(img, ins: Sequence, basej: int,
                           lookback: int = LOOKBACK_L2) -> Optional[dict]:
    """POSITIVE evidence for a rejected ``computed`` hit: the base is the image's OWN pointer table.

    "Not the sentinel" is an absence; the ef435 refutation rested on a PRESENCE -- *the image's words
    0x00..0x38 are 15 PSX addresses inside itself*.  So this re-derives that presence for every
    computed hit: const-fold the ``addu``'s non-index operand to a PSX address, map it into the
    image, and count how many consecutive words there are 4-aligned PSX pointers into this image's
    own code window.  Two or more and the "call" is a switch dispatch, adjudicated, not asserted.
    """
    q = ins[basej]
    if not q.entry or q.entry.name not in ("addu", "add"):
        return None
    for reg in (q.ops[1], q.ops[2]):
        v, ev = _resolve_const(ins, basej, reg, lookback)
        if v is None:
            continue
        rel = (v & 0x0FFFFFFF) - (img.psx_base & 0x0FFFFFFF)
        if not (0 <= rel < len(img.payload) - 4) or rel % 4:
            continue
        ptrs, n = 0, 0
        for w_off in range(rel, min(rel + 64 * 4, len(img.payload) - 3), 4):
            w = struct.unpack_from("<I", img.payload, w_off)[0]
            t = (w & 0x0FFFFFFF) - (img.psx_base & 0x0FFFFFFF)
            n += 1
            if w and t % 4 == 0 and 0 <= t < img.header_rel:
                ptrs += 1
            else:
                break
        if ptrs >= 2:
            return {"table_psx": v, "table_rel": rel, "entries_in_image": ptrs,
                    "words_examined": n, "evidence": ev}
    return None


def scan_linear_l2(ins: Sequence, lookback: int = LOOKBACK_L2, img=None) -> List[dict]:
    """LINEAR-L2: widenings W1..W4.  Every candidate is returned, adjudicated, never pre-filtered --
    a scan that drops its own false positives cannot be audited."""
    hits: List[dict] = []
    for k, i in enumerate(ins):
        if not i.entry:
            continue
        n = i.entry.name
        if n == "jalr" and len(i.ops) >= 2:
            treg, via = i.ops[1], "jalr"
        elif n == "jr" and i.ops and i.ops[0] != R_RA:          # W3
            treg, via = i.ops[0], "jr"
        else:
            continue
        if treg == 0:
            continue
        # W1 + W2: the nearest DEFINITION of $treg, within a 64-instruction window.
        defj = None
        for j in range(k - 1, max(-1, k - 1 - lookback), -1):
            if dest_reg(ins[j]) == treg:
                defj = j
                break
        if defj is None:
            continue
        p = ins[defj]
        if p.entry.name != "lw":
            continue
        imm, base = p.ops[1], p.ops[2]
        if imm < 0 or imm % 4 or imm >= D.HLE_MAX_OFFSET:
            continue
        op = imm // 4
        if op not in VRAM_OPS:
            continue
        # W4: the base chain -- see classify_base_chain.
        chain, chain_txt = classify_base_chain(ins, defj, base, lookback)
        tbl = None
        if img is not None and chain == "computed":
            bj = next((j for j in range(defj - 1, max(-1, defj - 1 - lookback), -1)
                       if dest_reg(ins[j]) == base), None)
            tbl = pointer_table_evidence(img, ins, bj, lookback) if bj is not None else None
        # THE DELAY-SLOT LAW, and it is not cosmetic: on ef001@0x5b0 the MoveImage destination's
        # `addiu $a2, $zero, 256` sits in the jalr's DELAY SLOT (k+1), which executes BEFORE the
        # target does.  A resolver that starts at k-1 loses the argument and reports "unresolved" --
        # exactly the shape of a false negative that would look like a hardened list.  The target
        # register and its base chain are NOT read from the delay slot: `jalr` reads $rs at the jump
        # itself, so a delay-slot write to it cannot redirect the call.
        args = []
        for a in ARG_REGS:
            v, ev = _resolve_const(ins, k + 2, a, lookback + 1)
            args.append({"reg": "$" + D.REG[a], "value": v, "evidence": ev})
        hits.append({"off": i.off, "op": op, "via": via, "load": p.text(), "load_off": p.off,
                     "base_reg": "$" + D.REG[base], "chain": chain, "chain_evidence": chain_txt,
                     "pointer_table": tbl, "args": args})
    return hits


# --------------------------------------------------------------------------- the corpus pass
def run(corpus: str = CORPUS, want_walk: bool = True, limit: Optional[int] = None) -> dict:
    hle = D.load_hle_names()
    res = {
        "corpus": corpus, "containers": 0, "images": 0, "errors": [],
        "walk": {v: sorted(()) for v in VRAM_OPS.values()},
        "reach": [],
        "sites": [],                     # every LINEAR-L2 candidate, adjudicated
        "g6_sites": [],                  # every LINEAR-G6 candidate
        "walk_sites": [],
        "tail_region_code": [],
    }
    walk_sets: Dict[str, Set[int]] = {v: set() for v in VRAM_OPS.values()}
    seq07: Set[int] = set()
    walk_dest: Dict[int, Set[Tuple[int, int]]] = {}
    paths = W.corpus_paths(corpus)
    if limit:
        paths = paths[:limit]
    for path in paths:
        ef = int(os.path.basename(path)[2:5])
        with open(path, "rb") as fh:
            blob = fh.read()
        res["containers"] += 1
        # --- the LOADER's own VRAM write: seq op 0x07.  Not an HLE call at all, so no call-shape
        #     scan could ever reach it -- measured here so the SET ACCOUNTING below CLOSES against
        #     the shipped 15 instead of leaving 9 ids looking like a shortfall.
        try:
            if any(op.code == 0x07 for op in EC.parse_op_stream(blob)):
                seq07.add(ef)
        except Exception as exc:                                 # pragma: no cover - corpus health
            res["errors"].append("ef%03d: parse_op_stream: %s" % (ef, exc))
        try:
            imgs = D.id3_images(blob, "ef%03d" % ef)
        except Exception as exc:                                 # pragma: no cover - corpus health
            res["errors"].append("ef%03d: id3_images: %s" % (ef, exc))
            continue
        for img in imgs:
            res["images"] += 1
            ins = _decode_region(img, 0, img.header_rel)
            # --- LINEAR-G6 (calibration)
            for h in scan_linear_g6(ins):
                res["g6_sites"].append({"ef": ef, "slot": img.chunk_slot, "off": h["off"],
                                        "op": h["op"], "name": VRAM_OPS[h["op"]]})
            # --- LINEAR-L2
            for h in scan_linear_l2(ins, img=img):
                h.update(ef=ef, slot=img.chunk_slot, name=VRAM_OPS[h["op"]],
                         direction=("write" if h["op"] in WRITE_OPS else "read"))
                res["sites"].append(h)
            # --- the region BEYOND header_rel: is there code there at all? (a miss class the
            #     linear scans would never see, so it is measured rather than assumed away)
            tail = _decode_region(img, img.header_rel, len(img.payload))
            if tail:
                jl = sum(1 for t in tail if t.entry and t.entry.name in ("jalr", "jr"))
                dec = sum(1 for t in tail if t.entry)
                res["tail_region_code"].append({"ef": ef, "slot": img.chunk_slot, "words": len(tail),
                                                "decoded": dec, "jalr_or_jr": jl,
                                                "hits": len(scan_linear_l2(tail))})
            # --- WALK
            if want_walk:
                try:
                    r = D.walk_image(img, hle_names=hle)
                except Exception as exc:                         # pragma: no cover
                    res["errors"].append("ef%03d slot %s: walk: %s" % (ef, img.chunk_slot, exc))
                    continue
                res["reach"].append(r.coverage)
                for c in r.calls:
                    if c.kind == "hle" and c.hle_op in VRAM_OPS:
                        walk_sets[VRAM_OPS[c.hle_op]].add(ef)
                        res["walk_sites"].append({"ef": ef, "slot": img.chunk_slot, "off": c.off,
                                                  "op": c.hle_op, "name": VRAM_OPS[c.hle_op],
                                                  "detail": c.detail, "args": list(c.args)})
                        if c.hle_op == 166 and len(c.args) >= 3 and c.args[1] is not None \
                                and c.args[2] is not None:
                            walk_dest.setdefault(ef, set()).add((c.args[1], c.args[2]))
    res["walk"] = {k: sorted(v) for k, v in walk_sets.items()}
    res["seq07"] = sorted(seq07)
    res["walk_move_dest"] = {str(k): sorted(map(list, v)) for k, v in walk_dest.items()}
    res["ops"] = verify_op_identities()
    res["direction"] = verify_op_direction_from_dll()
    res["summary"] = summarize(res)
    return res


def _ids(sites, ops, chains=None) -> Set[int]:
    return {s["ef"] for s in sites if s["op"] in ops
            and (chains is None or s.get("chain") in chains)}


def summarize(res: dict) -> dict:
    s, g6 = res["sites"], res["g6_sites"]
    real = REAL_CHAINS
    out = {
        "images": res["images"], "containers": res["containers"],
        "mean_reachability": (sum(res["reach"]) / len(res["reach"])) if res["reach"] else None,
        "seq07": sorted(res.get("seq07", ())),
        "walk_write": sorted(set(res["walk"]["LoadImage"]) | set(res["walk"]["MoveImage"])
                             | set(res["walk"]["TexAnimArm"])),
        "walk_read": sorted(res["walk"]["StoreImage"]),
        "g6_write": sorted({h["ef"] for h in g6 if h["op"] in WRITE_OPS}),
        "g6_read": sorted({h["ef"] for h in g6 if h["op"] in READ_OPS}),
        "l2_write_all": sorted(_ids(s, WRITE_OPS)),
        "l2_read_all": sorted(_ids(s, READ_OPS)),
        "l2_write_real": sorted(_ids(s, WRITE_OPS, real)),
        "l2_read_real": sorted(_ids(s, READ_OPS, real)),
        "l2_write_rejected": sorted(_ids(s, WRITE_OPS) - _ids(s, WRITE_OPS, real)),
        "sites_by_chain": {},
        "sites_by_op": {},
        "tail_hits": sum(t["hits"] for t in res["tail_region_code"]),
        "tail_images_with_jumps": sum(1 for t in res["tail_region_code"] if t["jalr_or_jr"]),
    }
    for h in s:
        out["sites_by_chain"][h["chain"]] = out["sites_by_chain"].get(h["chain"], 0) + 1
        key = "%s(%d)" % (h["name"], h["op"])
        out["sites_by_op"][key] = out["sites_by_op"].get(key, 0) + 1
    # the RECT* accounting -- $a0 is the RECT pointer on all three transfer ops
    tr = [h for h in s if h["op"] in (0, 1, 166) and h["chain"] in real]
    out["rect_args_total"] = len(tr)
    out["rect_args_resolved"] = sum(1 for h in tr if h["args"][0]["value"] is not None)
    mv = [h for h in s if h["op"] == 166 and h["chain"] in real]
    out["move_sites"] = len(mv)
    out["move_dest_resolved"] = {}
    for h in mv:
        x, y = h["args"][1]["value"], h["args"][2]["value"]
        if x is not None and y is not None:
            out["move_dest_resolved"].setdefault("ef%03d" % h["ef"], []).append([x, y])
    # THE DELTA against the shipped lists
    out["shipped_write"] = sorted(SHIPPED_WRITE)
    out["shipped_read"] = sorted(SHIPPED_READ)
    out["delta_write_new"] = sorted(set(out["l2_write_real"]) - SHIPPED_WRITE)
    out["delta_read_new"] = sorted(set(out["l2_read_real"]) - SHIPPED_READ - SHIPPED_WRITE)
    out["shipped_write_not_found"] = sorted(SHIPPED_WRITE - set(out["l2_write_real"]))
    out["union"] = sorted(set(out["l2_write_real"]) | set(out["l2_read_real"])
                          | SHIPPED_WRITE | SHIPPED_READ)
    return out


# --------------------------------------------------------------------------- calibration gates
def calibrate(res: dict) -> List[Tuple[str, bool, str]]:
    """C1..C6 -- RE-FIND THE KNOWN ANSWER BEFORE JUDGING WITH THE INSTRUMENT.

    Every gate compares a set this run measured against a set another instrument already published.
    A red gate here invalidates the delta below it, and says so.
    """
    g: List[Tuple[str, bool, str]] = []
    w = res["walk"]
    g.append(("C1 WALK reproduces w6b_gates' four op families",
              set(w["LoadImage"]) == CAL_WALK_LOADIMAGE
              and set(w["MoveImage"]) == CAL_WALK_MOVEIMAGE
              and set(w["StoreImage"]) == CAL_WALK_STOREIMAGE
              and set(w["TexAnimArm"]) == CAL_WALK_TEXANIM,
              "Load=%s Move=%s Store=%s TexAnim=%s" % (w["LoadImage"], w["MoveImage"],
                                                       w["StoreImage"], w["TexAnimArm"])))
    s = res["summary"]
    # ⚠ ON G6'S OWN PREDICATE, WHICH IS NOT THIS FILE'S.  `w6b_gates` builds its linear write set as
    # `linear["LoadImage"] | linear["MoveImage"]` -- the TEXANIM ARM is left out, although the walk
    # counts ef038's arm as a program VRAM write and `PROGRAM_VRAM_WRITE_IDS` ships ef038.  So the
    # two numbers differ by ef038 for a DEFINITIONAL reason, and both predicates are stated rather
    # than reconciled: on Load u Move the sets are identical; add the arm and ef038 joins.
    g6_lm = sorted({h["ef"] for h in res["g6_sites"] if h["op"] in (0, 166)})
    g.append(("C2 LINEAR-G6 reproduces G6's linear write set (its own predicate: Load u Move)",
              set(g6_lm) == CAL_LINEAR_G6_WRITE,
              "%s (want %s); adding the texanim arm gives %s" % (g6_lm, sorted(CAL_LINEAR_G6_WRITE),
                                                                 s["g6_write"])))
    extra = set(s["g6_read"]) - CAL_WALK_STOREIMAGE
    g.append(("C3 LINEAR-G6 re-finds the six linear-only StoreImage ids",
              extra == set(CAL_LINEAR_ONLY_STORE), "%s" % sorted(extra)))
    dest = {tuple(v) for vs in s["move_dest_resolved"].values() for v in vs}
    g.append(("C4 the L2 const-folder re-finds MoveImage's (704,256) on 3 of 5 sites",
              dest == {CAL_MOVE_DEST}
              and sum(len(v) for v in s["move_dest_resolved"].values()) == 3
              and s["move_sites"] == 5,
              "dests=%s over %d of %d sites" % (sorted(dest),
                                                sum(len(v) for v in s["move_dest_resolved"].values()),
                                                s["move_sites"])))
    ef435 = [h for h in res["sites"] if h["ef"] == 435 and h["off"] == CAL_EF435_SITE]
    g.append(("C5 ef435@0x2dd8 is REJECTED by the base-chain rule",
              bool(ef435) and all(h["chain"] not in ("sentinel", "nodef") for h in ef435),
              "%s" % ([(hex(h["off"]), h["chain"], h["chain_evidence"]) for h in ef435] or
                      "no L2 candidate at that offset")))
    g.append(("C6 0 of the RECT* pointers const-fold (sec 1.6's own prediction)",
              s["rect_args_resolved"] == 0,
              "%d of %d resolved" % (s["rect_args_resolved"], s["rect_args_total"])))
    # C7/C8 -- THE FALSE-NEGATIVE GATES.  A scan is judged by what it LOSES as much as what it adds:
    # a classifier that rejected real calls would report "no new writes" for the wrong reason.
    wsites = {(h["ef"], h["off"]) for h in res["walk_sites"]}
    lsites = {(h["ef"], h["off"]) for h in res["sites"]}
    g.append(("C7 LINEAR-L2 NOMINATES every walk-confirmed HLE VRAM site",
              wsites <= lsites, "%d walk sites, %d missed by L2: %s"
              % (len(wsites), len(wsites - lsites), sorted(wsites - lsites)[:8])))
    by = {(h["ef"], h["off"]): h["chain"] for h in res["sites"]}
    badly = sorted(k for k in wsites & lsites if by[k] not in REAL_CHAINS)
    # THE ONLY walk-confirmed site the base-chain rule may reject is the one the record already
    # REFUTED -- and rejecting it here is an INDEPENDENT re-derivation of that refutation, from a
    # different rule than G6 used (G6: the linear scan never reproduces it; L2: its base is
    # computed, and the table it indexes is the image's own).  Any OTHER rejection is a defect.
    g.append(("C8 the ONLY walk site L2 rejects is the refuted ef435@0x2dd8",
              badly == [(435, CAL_EF435_SITE)],
              "%d rejected: %s" % (len(badly), [(e, hex(o), by[(e, o)]) for e, o in badly[:8]])))
    ptab = [h for h in res["sites"] if h["chain"] == "computed" and h.get("pointer_table")]
    g.append(("C10 the rejected class carries POSITIVE evidence: an in-image pointer table",
              len(ptab) >= 1 and any(h["ef"] == 435 for h in ptab),
              "%d of %d computed hits resolve their table (%d entries median), ef435 among them: %s"
              % (len(ptab), sum(1 for h in res["sites"] if h["chain"] == "computed"),
                 sorted(h["pointer_table"]["entries_in_image"] for h in ptab)[len(ptab) // 2]
                 if ptab else 0, any(h["ef"] == 435 for h in ptab))))
    # C11 -- a THIRD instrument.  The annotator's own $a1 histogram for op 1 (recorded in
    # hle_ops.json from a different derivation) must equal the addresses this file's const-folder
    # recovers.  Agreement across annotator / walker / L2 is what makes an argument non-circular.
    a1 = {h["args"][1]["value"] for h in res["sites"]
          if h["op"] == 1 and h["chain"] in REAL_CHAINS and h["args"][1]["value"] is not None}
    want_a1 = {2149489540, 2149489604, 2149489732}
    g.append(("C11 the L2 const-folder reproduces the annotator's op-1 $a1 constants",
              a1 == want_a1, "%s (annotator: %s)" % (sorted(a1), sorted(want_a1))))
    # C12 -- TWO INDEPENDENT DISCRIMINATORS, stated rather than reconciled.  `via` (a jalr CALLS, a
    # jr TAIL-JUMPS: a switch dispatch jumps) and `chain` (the sentinel base) are different facts
    # about a site.  On this corpus they partition the candidates IDENTICALLY; if they ever diverge
    # the divergence is the finding, so the gate asserts the agreement instead of assuming it.
    byvia = {(h["ef"], h["off"]) for h in res["sites"] if h["via"] == "jalr"}
    bychain = {(h["ef"], h["off"]) for h in res["sites"] if h["chain"] in REAL_CHAINS}
    g.append(("C12 via-jalr and sentinel-chain partition the candidates identically",
              byvia == bychain, "jalr=%d chain-real=%d symmetric difference=%d"
              % (len(byvia), len(bychain), len(byvia ^ bychain))))
    # C13 -- THE DIRECTION, settled one layer down.  OPTIONAL: reports an ABSENT instrument rather
    # than a pass when the DLL is unreachable, because a green gate nobody ran is a comment.
    d = res.get("direction")
    if d is None:
        g.append(("C13 op 0 = LoadImage / op 1 = StoreImage, from the DLL + Memoria's handler",
                  False, "INSTRUMENT ABSENT -- FF9SpecialEffectPlugin.dll or pefile/capstone "
                         "unreachable; the assignment stays INHERITED, not verified"))
    else:
        g.append(("C13 op 0 = LoadImage / op 1 = StoreImage, from the DLL + Memoria's handler",
                  bool(d.get("agrees")),
                  "callback codes %s -> host cases %s (want %s); handler: %s"
                  % ({k: hex(v) if v else None for k, v in d["codes"].items()}, d["host_case"],
                     HOST_CASE, list(d.get("memoria_lines", {}).items())[:3])))
    # C9 -- the accounting identity the shipped WRITE list must satisfy, re-derived end to end.
    lhs = set(s["l2_write_real"]) | set(s["seq07"])
    g.append(("C9 shipped WRITE == (L2 HLE writes) u (seq op 0x07) exactly",
              lhs == SHIPPED_WRITE, "derived %s  missing %s  extra %s"
              % (sorted(lhs), sorted(SHIPPED_WRITE - lhs), sorted(lhs - SHIPPED_WRITE))))
    return g


# --------------------------------------------------------------------------- report
def report(res: dict) -> str:
    s, o = res["summary"], res["ops"]
    L = []
    L.append("W6b-2 L2 THE WRITE SCAN -- %d containers, %d id-3 images, mean reachability %.3f"
             % (s["containers"], s["images"], s["mean_reachability"] or 0.0))
    L.append("")
    L.append("OP IDENTITIES (verified against hle_ops.json, not inherited from the record)")
    for op in (0, 1, 166, 12):
        r = o["ops"][op]
        L.append("  op %-3d arity %s kinds %-5s returns %-4s native %-8s touches %s  "
                 "sites=%s effects=%s" % (op, r["arity"], r["arg_kinds"], r["returns"],
                                          r["native_fn"], ",".join(r["touches"] or []) or "-",
                                          r["call_sites"], r["effects"]))
    L.append("  MoveImage(op 166) uniquely identified by arity-3 'pii' : %s" % o["moveimage_unique"])
    L.append("  ops 0/1 are BOTH arity-2 'pp' -- Load-vs-Store is NOT settled by the table: %s"
             % o["load_store_ambiguous"])
    d = res.get("direction")
    L.append("  ... so DIRECTION is settled one layer down: %s"
             % ("DLL callback codes %s -> Memoria SFX.cs cases %s (LoadImage/StoreImage/MoveImage)"
                % ({k: hex(v) for k, v in d["codes"].items() if v}, d["host_case"])
                if d else "INSTRUMENT ABSENT (no DLL) -- assignment INHERITED, not verified"))
    L.append("")
    L.append("CALIBRATION")
    for name, ok, ev in calibrate(res):
        L.append("  [%s] %s -- %s" % ("PASS" if ok else "FAIL", name, ev))
    L.append("")
    L.append("SITES  (LINEAR-L2 candidates by adjudication)")
    for k, v in sorted(s["sites_by_chain"].items()):
        L.append("  chain=%-9s %d" % (k, v))
    for k, v in sorted(s["sites_by_op"].items()):
        L.append("  %-16s %d" % (k, v))
    L.append("")
    L.append("SET ACCOUNTING (sec 1.6 item 4's form: per SET, not one headline)")
    L.append("  WRITE  walk=%s" % s["walk_write"])
    L.append("         G6-linear=%s" % s["g6_write"])
    L.append("         L2-linear(adjudicated real)=%s" % s["l2_write_real"])
    L.append("         L2 candidates REJECTED by the base chain=%s" % s["l2_write_rejected"])
    L.append("         SHIPPED=%s" % s["shipped_write"])
    L.append("         DELTA new writes = %s" % (s["delta_write_new"] or "NONE"))
    L.append("         shipped writes this scan does NOT reach = %s"
             % (s["shipped_write_not_found"] or "none"))
    L.append("  READ   walk=%s" % s["walk_read"])
    L.append("         L2-linear(adjudicated real)=%s" % s["l2_read_real"])
    L.append("         SHIPPED=%s" % s["shipped_read"])
    L.append("         DELTA new reads = %s" % (s["delta_read_new"] or "NONE"))
    L.append("  SEQ    loader op 0x07 (not an HLE call -- no call-shape scan can reach it) = %s"
             % s["seq07"])
    L.append("  UNION  %d ids  (write u read, shipped u derived)" % len(s["union"]))
    L.append("")
    L.append("MOVEIMAGE destinations const-folded: %s   (RECT* resolved %d of %d)"
             % (s["move_dest_resolved"], s["rect_args_resolved"], s["rect_args_total"]))
    L.append("TAIL REGION (beyond header_rel): %d images carry a jalr/jr there, %d L2 hits"
             % (s["tail_images_with_jumps"], s["tail_hits"]))
    if res["errors"]:
        L.append("ERRORS: %d  %s" % (len(res["errors"]), res["errors"][:5]))
    return "\n".join(L)


def explain(res: dict, ef: int) -> str:
    L = ["ef%03d -- every L2 candidate, adjudicated" % ef]
    for h in res["sites"]:
        if h["ef"] != ef:
            continue
        L.append("  @+%#06x  %-12s via %-4s  chain=%-9s  %s" % (h["off"], h["name"], h["via"],
                                                                h["chain"], h["load"]))
        L.append("            base %s: %s" % (h["base_reg"], h["chain_evidence"]))
        for a in h["args"]:
            L.append("            %s = %s   (%s)" % (a["reg"],
                                                     "?" if a["value"] is None else a["value"],
                                                     a["evidence"]))
    for h in res["walk_sites"]:
        if h["ef"] == ef:
            L.append("  WALK @+%#06x %s args=%s  %s" % (h["off"], h["name"], h["args"],
                                                        h["detail"]))
    return "\n".join(L)


def sweep(corpus: str = CORPUS, windows=(8, 12, 24, 64, 128, 256)) -> dict:
    """THE WINDOW SENSITIVITY.  A linear scan's answer is a function of its lookback, so the lookback
    is swept rather than defended: if the adjudicated WRITE set is the same at 8 and at 256, the
    verdict is not an artifact of one constant.  Walk-free, so it is cheap enough to run every time.
    """
    out = {}
    for lb in windows:
        wr, rd, cand = set(), set(), 0
        for path in W.corpus_paths(corpus):
            ef = int(os.path.basename(path)[2:5])
            with open(path, "rb") as fh:
                blob = fh.read()
            try:
                imgs = D.id3_images(blob, "ef%03d" % ef)
            except Exception:                                    # pragma: no cover
                continue
            for img in imgs:
                ins = _decode_region(img, 0, img.header_rel)
                for h in scan_linear_l2(ins, lookback=lb, img=img):
                    cand += 1
                    if h["chain"] in REAL_CHAINS:
                        (wr if h["op"] in WRITE_OPS else rd).add(ef)
        out[lb] = {"write": sorted(wr), "read": sorted(rd), "candidates": cand}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", default=CORPUS)
    ap.add_argument("--out", default=os.path.join(OUT_DIR, "write_scan.json"))
    ap.add_argument("--limit", type=int, default=None, help="first N containers (a smoke run)")
    ap.add_argument("--no-walk", action="store_true", help="skip the slow reachability walk")
    ap.add_argument("--calibrate", action="store_true", help="print only the calibration gates")
    ap.add_argument("--explain", type=int, default=None, metavar="EF")
    ap.add_argument("--sweep", action="store_true", help="lookback-window sensitivity, walk-free")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.corpus):
        print("no corpus at %s" % a.corpus)
        return 2
    if a.sweep:
        for lb, v in sweep(a.corpus).items():
            print("lookback %3d  candidates %4d  WRITE %s  READ %s"
                  % (lb, v["candidates"], v["write"], v["read"]))
        return 0
    res = run(a.corpus, want_walk=not a.no_walk, limit=a.limit)
    if a.calibrate:
        bad = 0
        for name, ok, ev in calibrate(res):
            print("[%s] %s -- %s" % ("PASS" if ok else "FAIL", name, ev))
            bad += 0 if ok else 1
        return 1 if bad else 0
    if a.explain is not None:
        print(explain(res, a.explain))
        return 0
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(report(res))
    print("\nwrote %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
