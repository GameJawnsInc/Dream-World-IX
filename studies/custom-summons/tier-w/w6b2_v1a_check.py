r"""W6b-2 lane V1a -- THE DISASSEMBLY REFUTER for L1's tpage sweep.

INDEPENDENT RE-DERIVATION, by construction.  Nothing here imports or transcribes L1's folding
logic.  This module carries:

  * its OWN MIPS R3000A decoder, written from the raw bit fields (no ``tier_r_disasm.Decoder``,
    no ``Instr``, no opcode table);
  * its OWN call-site finder -- a LINEAR scan of every word in ``[0, header_rel)``, seeded from
    nothing, so it sees code the reachability walk never enters;
  * its OWN constant folder -- a depth-capped backward window walk that records, per hit, how many
    control transfers it had to cross to believe its answer (the honest weakness of a linear scan,
    reported instead of hidden).

It shares exactly two things with L1, both of them upstream authorities rather than method:
``ef_container`` (the sanctioned container parser -- there is only one) and
``ff9mapkit.summons.reskin`` (the in-repo authority for the tpage bit layout and the page-cell map,
which the census itself is built on).  Everything between those two ends is re-derived.

THE FIVE ATTACK LENSES, each with a measured result:

  A  AGREEMENT     my hits vs L1's raw hits, per op/arg, per idiom class.
  B  DEAD CODE     which of my linear hits the reachability walk never reaches, and vice versa.
  C  MASQUERADE    for a sample, is the folded constant really the LAST writer before the call
                   (delay slot included), or did either instrument read a stale register?
  D  COINCIDENCE   the base rate of a tpage-SHAPED constant in NON-tpage argument positions, plus a
                   PERMUTATION null for the "declared column" predicate -- if a random constant from
                   another container passes the test as often, constant-ness proves nothing.
  E  RECALIBRATE   the so-vs-program agreement recomputed here from L1's raw json + pages.json.

PROVENANCE: pure analysis code, zero Square-Enix bytes; committable.  Its OUTPUT quotes decoded
stock constants and therefore goes to SCRATCH.

CLI::

    py w6b2_v1a_check.py scan        # my linear scan -> v1a_scan.json
    py w6b2_v1a_check.py compare     # lens A + B against L1's tpage_sweep.json
    py w6b2_v1a_check.py baserate    # lens D
    py w6b2_v1a_check.py recal       # lens E
    py w6b2_v1a_check.py all
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import struct
import sys
import time
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_TIER_R = os.path.normpath(os.path.join(_HERE, "..", "tier-r"))
_EFC = os.path.normpath(os.path.join(_HERE, "..", "thomas-swap", "disasm"))
_KIT = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "ff9mapkit"))
for _p in (_TIER_R, _EFC, _KIT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ef_container as EC                                       # noqa: E402
from ff9mapkit.summons import reskin as RS                      # noqa: E402

SCRATCH = os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format")
OUT_DIR = os.path.join(SCRATCH, "texel-w6b", "w6b2")
CENSUS_PAGES = os.path.join(SCRATCH, "texel-w6b", "census", "pages.json")
L1_SWEEP = os.path.join(OUT_DIR, "tpage_sweep.json")
HLE_OPS_JSON = os.path.join(_TIER_R, "hle_ops.json")

HLE_MAX_OFF = 0x360        # 216 ops * 4
SYSSTRUCT_FIELD = 0x10
PAGE_HW, PAGE_LINES, CELL_LINES = 64, 256, 128
BACK_WINDOW = 24           # instructions searched backward for a register's producer
FOLD_DEPTH = 4


# ===================================================================== my own MIPS decoder
def _f(w: int):
    """Raw R3000A bit fields -- (op, rs, rt, rd, shamt, funct, uimm, simm, target)."""
    uimm = w & 0xFFFF
    return (w >> 26, (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31, (w >> 6) & 31, w & 63,
            uimm, uimm - 0x10000 if uimm & 0x8000 else uimm, (w & 0x03FFFFFF) << 2)


#: SPECIAL functs that write no GPR at all.
_SPECIAL_NO_GPR = {0x08, 0x0C, 0x0D, 0x10, 0x11, 0x12, 0x13, 0x18, 0x19, 0x1A, 0x1B}


def writes_reg(w: int) -> Optional[int]:
    """Which GPR this word writes, or None.  Conservative: unknown encodings write nothing."""
    op, rs, rt, rd, _sh, fn, _u, _s, _t = _f(w)
    if op == 0:
        if fn == 0x09:                       # jalr -> rd (default $ra)
            return rd or 31
        if fn in _SPECIAL_NO_GPR:
            return None
        if fn in (0x10, 0x12):               # mfhi/mflo (also covered above; explicit)
            return rd
        if fn <= 0x2B:
            return rd
        return None
    if op == 1:                              # REGIMM: bltzal/bgezal write $ra
        return 31 if rt in (0x10, 0x11) else None
    if op == 3:                              # jal
        return 31
    if op in (2, 4, 5, 6, 7):                # j / beq / bne / blez / bgtz
        return None
    if 8 <= op <= 0x0F:                      # addi..lui -> rt
        return rt
    if 0x10 <= op <= 0x13:                   # COPz: mfc/cfc write rt, mtc/ctc do not
        return rt if rs in (0, 2) else None
    if 0x20 <= op <= 0x26:                   # loads -> rt
        return rt
    return None                              # stores, lwc/swc, everything else


def is_call(w: int) -> bool:
    op, _rs, _rt, _rd, _sh, fn, _u, _s, _t = _f(w)
    return op == 3 or (op == 0 and fn == 0x09)


def is_transfer(w: int) -> bool:
    op, _rs, rt, _rd, _sh, fn, _u, _s, _t = _f(w)
    if op == 0:
        return fn in (0x08, 0x09)
    if op == 1:
        return rt in (0x00, 0x01, 0x10, 0x11)
    return op in (2, 3, 4, 5, 6, 7)


def is_jalr(w: int) -> Tuple[bool, int]:
    op, rs, _rt, _rd, _sh, fn, _u, _s, _t = _f(w)
    return (op == 0 and fn == 0x09), rs


def is_lw(w: int) -> Tuple[bool, int, int, int]:
    """(is lw, dest rt, offset, base rs)."""
    op, rs, rt, _rd, _sh, _fn, _u, s, _t = _f(w)
    return op == 0x23, rt, s, rs


MN = {0: "special", 1: "regimm", 2: "j", 3: "jal", 4: "beq", 5: "bne", 8: "addi", 9: "addiu",
      0x0A: "slti", 0x0B: "sltiu", 0x0C: "andi", 0x0D: "ori", 0x0E: "xori", 0x0F: "lui",
      0x23: "lw", 0x2B: "sw", 0x29: "sh", 0x28: "sb"}


def text(w: int) -> str:
    """A minimal mnemonic for the handful of forms this lane quotes in evidence."""
    op, rs, rt, rd, sh, fn, u, s, t = _f(w)
    if op == 0:
        if fn == 0x09:
            return "jalr $%d" % rs
        if fn == 0x08:
            return "jr $%d" % rs
        if fn == 0x21:
            return "addu $%d, $%d, $%d" % (rd, rs, rt)
        if fn == 0x25:
            return "or $%d, $%d, $%d" % (rd, rs, rt)
        if fn == 0x00:
            return "sll $%d, $%d, %d" % (rd, rt, sh)
        return "special.%#x $%d" % (fn, rd)
    if op == 9:
        return "addiu $%d, $%d, %d" % (rt, rs, s)
    if op == 0x0D:
        return "ori $%d, $%d, %#x" % (rt, rs, u)
    if op == 0x0F:
        return "lui $%d, %#x" % (rt, u)
    if op == 0x23:
        return "lw $%d, %#x($%d)" % (rt, s, rs)
    if op == 3:
        return "jal %#x" % t
    return "%s(op=%#x) w=%08x" % (MN.get(op, "?"), op, w)


# ===================================================================== my own folder
class Fold:
    """A depth-capped backward window folder over a flat word array.  Deliberately DUMBER than a
    block lattice: it walks program order backwards, stops at the first producer, and REPORTS how
    many control transfers it crossed rather than pretending the path is straight."""

    def __init__(self, words: Sequence[int], window: int = BACK_WINDOW):
        self.w = words
        #: the backward reach, applied RECURSIVELY.  Widening only the top-level lookup and not the
        #: source-register recursion is exactly the bug that made this lane's first window probe
        #: report 0/12 against L1 -- an instrument artefact that looked like a disagreement.
        self.win = window

    def producer(self, i: int, reg: int, window: Optional[int] = None
                 ) -> Tuple[Optional[int], str, int]:
        """Index of the last instruction before ``i`` that writes ``reg`` -- with the delay slot of
        a call at ``i`` handled by the CALLER (see :meth:`arg`).  Returns (idx, why, n_transfers)."""
        window = self.win if window is None else window
        crossed = 0
        for k in range(1, window + 1):
            p = i - k
            if p < 0:
                return None, "start-of-image", crossed
            w = self.w[p]
            if writes_reg(w) == reg:
                return p, "found", crossed
            if is_call(w) and reg in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 24, 25):
                return None, "clobbered-by-call", crossed
            if is_transfer(w):
                crossed += 1
        return None, "window", crossed

    def value(self, i: int, reg: int, depth: int = FOLD_DEPTH) -> Tuple[Optional[int], str, int]:
        """Fold ``reg``'s value as of just before index ``i``.  (value | None, why, transfers)."""
        if reg == 0:
            return 0, "zero", 0
        if depth < 0:
            return None, "depth", 0
        p, why, crossed = self.producer(i, reg)
        if p is None:
            return None, why, crossed
        return self.resolve(p, reg, depth, crossed)

    def resolve(self, p: int, reg: int, depth: int = FOLD_DEPTH,
                crossed: int = 0) -> Tuple[Optional[int], str, int]:
        """Fold the value the instruction AT index ``p`` puts in ``reg``."""
        if depth < 0:
            return None, "depth", crossed
        w = self.w[p]
        op, rs, rt, rd, _sh, fn, u, s, _t = _f(w)
        if op == 0x0F:                                    # lui
            return (u << 16) & 0xFFFFFFFF, "lui", crossed
        if op in (8, 9):                                  # addi/addiu
            if rs == 0:
                return s & 0xFFFFFFFF, "imm", crossed
            base, why2, c2 = self.value(p, rs, depth - 1)
            if base is None:
                return None, "addiu(" + why2 + ")", crossed + c2
            return (base + s) & 0xFFFFFFFF, "addiu", crossed + c2
        if op == 0x0D:                                    # ori
            if rs == 0:
                return u, "imm", crossed
            base, why2, c2 = self.value(p, rs, depth - 1)
            if base is None:
                return None, "ori(" + why2 + ")", crossed + c2
            return (base | u), "ori", crossed + c2
        if op == 0 and fn in (0x21, 0x20, 0x25):          # addu/add/or
            a, b = rs, rt
            if b == 0:
                return self.value(p, a, depth - 1)
            if a == 0:
                return self.value(p, b, depth - 1)
            va, _w1, c1 = self.value(p, a, depth - 1)
            vb, _w2, c2 = self.value(p, b, depth - 1)
            if va is None or vb is None:
                return None, "reg+reg", crossed + c1 + c2
            return ((va + vb) if fn != 0x25 else (va | vb)) & 0xFFFFFFFF, "regreg", crossed
        if op == 0x23:
            return None, "load", crossed
        return None, "op%#x" % op, crossed

    def arg(self, call_i: int, areg: int) -> Tuple[Optional[int], str, int]:
        """An argument register's value AS THE CALL SEES IT -- the DELAY SLOT executes first.

        MIPS R3000A has no interlock on the branch delay: the word at ``call+4`` runs before the
        callee.  If it writes the argument register, IT is the producer and every earlier writer is
        dead.  Any instrument that reads the register state *at* the ``jalr`` and not *after* its
        delay slot reports a stale value; lens C measures how often that would matter.
        """
        if call_i + 1 < len(self.w) and writes_reg(self.w[call_i + 1]) == areg:
            v, why, c = self.resolve(call_i + 1, areg)
            return v, "delay:" + why, c
        return self.value(call_i, areg)


# ===================================================================== the linear scan
def decode_tpage(tp: int) -> Dict[str, object]:
    """Re-derived from ``reskin.attribution``'s decoder, checked word-for-word by :func:`c0`."""
    return {"tpage": tp, "page_x": (tp & 0x0F) * PAGE_HW, "page_y": ((tp >> 4) & 1) * PAGE_LINES,
            "semi": (tp >> 5) & 3, "bpp": RS.SO_BPP[(tp >> 7) & 3]}


def c0(n: int = 512) -> str:
    """CALIBRATION 0 (mine, not L1's): my decoder vs reskin's own bit layout, every 9-bit word."""
    import inspect
    src = inspect.getsource(RS.attribution)
    bad = [tp for tp in range(n)
           if decode_tpage(tp)["bpp"] != RS.SO_BPP[(tp >> 7) & 3]
           or decode_tpage(tp)["page_x"] != (tp & 0x0F) * 64
           or decode_tpage(tp)["page_y"] != ((tp >> 4) & 1) * 256]
    if bad:
        raise AssertionError("decoder diverges on %d words" % len(bad))
    has = all(k in src for k in ("& 0x0F", ">> 4", ">> 7"))
    return ("V1a decoder == reskin over %d/%d words; reskin.attribution source carries the same "
            "three field extractions: %s" % (n, n, has))


def corpus_paths() -> List[str]:
    return sorted(glob.glob(os.path.join(SCRATCH, "ef*.bytes")))


def ef_of(p: str) -> int:
    return int(os.path.splitext(os.path.basename(p))[0][2:])


def images_of(blob: bytes, src: str):
    """(chunk_slot, psx_base, header_rel, payload) per id-3 image -- via the sanctioned parser."""
    c = EC.parse_header(blob)
    out = []
    for ch in c.chunks:
        for res in ch.resources:
            if res.id != 3:
                continue
            img = EC.parse_chunk_image(blob, res, ch.psx_base)
            out.append((ch.slot, ch.psx_base, img.header_rel,
                        blob[res.offset:res.offset + res.nbytes],
                        tuple(o for o in img.program_offsets if o)))
    return out


def scan_image(payload: bytes, header_rel: int) -> List[Dict[str, object]]:
    """EVERY jalr in [0, header_rel) whose target register came from an in-window ``lw``.

    No seeds, no reachability, no blocks -- a flat pass over the words.  The op index falls out of
    the load offset (R1's HLE CALL SHAPE LAW); the sysStruct parent is tested SEPARATELY so a hit
    can be graded rather than silently dropped.
    """
    n = min(header_rel, len(payload)) // 4
    if n < 4:
        return []
    words = struct.unpack_from("<%dI" % n, payload, 0)
    fold = Fold(words)
    out: List[Dict[str, object]] = []
    for i in range(n):
        ok, rs = is_jalr(words[i])
        if not ok:
            continue
        p, why, crossed = fold.producer(i, rs)
        if p is None:
            out.append({"off": 4 * i, "op": None, "why": "target:" + why})
            continue
        islw, rt, loff, base = is_lw(words[p])
        if not islw:
            out.append({"off": 4 * i, "op": None, "why": "target-not-lw"})
            continue
        if loff < 0 or loff % 4 or loff >= HLE_MAX_OFF:
            out.append({"off": 4 * i, "op": None, "why": "offset-not-a-table-slot"})
            continue
        # THE ef435 GUARD, my own version.  The dispatch table's base is usually parked in a
        # CALLEE-SAVED register at function entry, thousands of instructions back, so the window
        # for THIS lookup is the whole image -- the caller-saved clobber rule still applies and is
        # what makes the search sound for $v/$a/$t bases.
        bp, _w2, _c2 = fold.producer(p, base, window=len(words))
        parent = "none"
        if bp is not None:
            islw2, _rt2, loff2, _b2 = is_lw(words[bp])
            if islw2:
                parent = "sysStruct" if loff2 == SYSSTRUCT_FIELD else "slot(+%#x)" % loff2
            else:
                parent = "nonload:%s" % text(words[bp]).split()[0]
        rec: Dict[str, object] = {"off": 4 * i, "op": loff // 4, "parent": parent,
                                  "target_crossed": crossed, "lw_off": 4 * p}
        for ai, areg in enumerate((4, 5, 6, 7)):
            v, why_a, c_a = fold.arg(i, areg)
            rec["a%d" % ai] = v
            rec["a%d_why" % ai] = why_a
            rec["a%d_crossed" % ai] = c_a
        out.append(rec)
    return out


def scan(paths: Optional[Sequence[str]] = None, progress: bool = True) -> Dict[str, object]:
    paths = list(paths or corpus_paths())
    t0 = time.time()
    per_image: List[Dict[str, object]] = []
    imm_pool: List[Tuple[int, int]] = []          # (ef, immediate)  -- lens D input
    for k, p in enumerate(paths):
        ef = ef_of(p)
        blob = open(p, "rb").read()
        try:
            imgs = images_of(blob, os.path.basename(p))
        except Exception as e:
            per_image.append({"ef": ef, "error": "%s: %s" % (type(e).__name__, e)})
            continue
        for slot, psx, hrel, pay, progs in imgs:
            sites = scan_image(pay, hrel)
            per_image.append({"ef": ef, "slot": slot, "header_rel": hrel,
                              "n_words": min(hrel, len(pay)) // 4, "programs": list(progs),
                              "sites": sites})
            nn = min(hrel, len(pay)) // 4
            if nn:
                for w in struct.unpack_from("<%dI" % nn, pay, 0):
                    op, rs, _rt, _rd, _sh, _fn, u, s, _t = _f(w)
                    if op == 9 and rs == 0 and 0 <= s < 0x10000:
                        imm_pool.append((ef, s))
                    elif op == 0x0D and rs == 0:
                        imm_pool.append((ef, u))
        if progress and (k + 1) % 100 == 0:
            print("  ... %d/%d  %.1fs" % (k + 1, len(paths), time.time() - t0))
    return {"per_image": per_image, "imm_pool": imm_pool, "containers": len(paths),
            "seconds": round(time.time() - t0, 1)}


# ===================================================================== container facts
def container_columns(blob: bytes) -> set:
    try:
        return set(pc.x for pc in RS.page_cells(blob).values())
    except Exception:
        return set()


def container_so(blob: bytes) -> List[Dict[str, object]]:
    try:
        # ★ W6b-3 NARROWING, DECLARED: every consumer of this helper compares L1's hits against the
        # CENSUS's own `so` bindings, i.e. against channel G's input.  `attribution`'s default became
        # the TRUE (multi-part) population at W6b-3, so the scope is stated rather than inherited.
        a = RS.attribution(blob, include_direct=True, witness=RS.WITNESS_INCUMBENT)
    except Exception:
        return []
    return [{"geom": b.geom, "tpage": int(b.tpage), "bpp": int(b.bpp),
             "page_x": int(b.page[0]), "page_y": int(b.page[1])} for b in a.bindings]


def container_geom_total(blob: bytes) -> Optional[int]:
    try:
        return RS.attribution(blob).geom_total
    except Exception:
        return None


# ===================================================================== LENS A + B
def compare(sc: Dict[str, object]) -> Dict[str, object]:
    """Lens A (agreement) and lens B (dead code) against L1's raw hits."""
    l1 = json.load(open(L1_SWEEP, encoding="utf-8"))
    l1_hits = {(h["ef"], h["image"], h["off"]): h for h in l1["sweep"]["hits"]}
    l1_rt = {(h["ef"], h["image"], h["off"]): h for h in l1["sweep"]["runtime"]}
    l1_weak = {(h["ef"], h["image"], h["off"]): h for h in l1["sweep"]["weak_dispatch"]}

    mine_all: Dict[Tuple[int, str, int], Dict[str, object]] = {}
    op_hist_all: Counter = Counter()
    for im in sc["per_image"]:
        if "sites" not in im:
            continue
        label = "ef%03d:c%d" % (im["ef"], im["slot"])
        for s in im["sites"]:
            if s.get("op") is None:
                continue
            op_hist_all[s["op"]] += 1
            mine_all[(im["ef"], label, s["off"])] = s

    mine22 = {k: v for k, v in mine_all.items() if v["op"] == 22}
    both = set(mine22) & set(l1_hits)
    only_l1 = set(l1_hits) - set(mine22)
    only_me = set(mine22) - set(l1_hits)

    val_agree, val_disagree = 0, []
    for k in sorted(both):
        mv, lv = mine22[k]["a1"], l1_hits[k]["value"]
        if mv == lv:
            val_agree += 1
        else:
            val_disagree.append({"key": "%s+%#x" % (k[1], k[2]), "mine": mv, "l1": lv,
                                 "why": mine22[k]["a1_why"]})

    # only_l1: did I see the site at all (as a non-op-22 or as an unresolved jalr)?
    only_l1_detail = Counter()
    for k in only_l1:
        s = mine_all.get(k)
        only_l1_detail["i-called-it-op-%s" % (s["op"] if s else "MISSED")] += 1

    # only_me: what does L1 say about them?
    only_me_detail = Counter()
    for k in only_me:
        if k in l1_rt:
            only_me_detail["l1-runtime"] += 1
        elif k in l1_weak:
            only_me_detail["l1-weak-dispatch"] += 1
        else:
            only_me_detail["l1-never-reached"] += 1

    # ---- lens B: reachability.  L1's hits live in the walked set BY CONSTRUCTION; the question
    # is what a seed-free linear scan finds OUTSIDE it, and whether those sites look alive.
    dead = [{"key": "%s+%#x" % (k[1], k[2]), "parent": mine22[k]["parent"],
             "a1": mine22[k]["a1"], "a1_why": mine22[k]["a1_why"],
             "a2": mine22[k]["a2"], "crossed": mine22[k]["a1_crossed"]}
            for k in sorted(only_me) if k not in l1_rt and k not in l1_weak]

    parent_hist = Counter(v["parent"] for v in mine22.values())
    return {
        "my_op22_sites": len(mine22),
        "my_op22_const_a1": sum(1 for v in mine22.values() if v["a1"] is not None),
        "my_parent_hist": dict(parent_hist),
        "l1_hits": len(l1_hits), "l1_runtime": len(l1_rt), "l1_weak": len(l1_weak),
        "intersection": len(both), "value_agree": val_agree,
        "value_disagreements": val_disagree,
        "only_l1": len(only_l1), "only_l1_detail": dict(only_l1_detail),
        "only_me": len(only_me), "only_me_detail": dict(only_me_detail),
        "linear_only_unreached_sites": len(dead), "linear_only_examples": dead[:12],
        "my_op_histogram_top": op_hist_all.most_common(15),
    }


# ===================================================================== LENS C
def masquerade(sc: Dict[str, object], sample: int = 40, seed: int = 11) -> Dict[str, object]:
    """Is the folded constant really the LAST writer before the call takes effect?

    Two failure modes are counted separately:
      * DELAY-SLOT producer -- the argument is set in the call's delay slot.  Both instruments must
        honour it; a lattice recorded AT the jalr would be stale.
      * CROSSED TRANSFERS -- my linear window had to step over N branches to reach the producer, so
        the value is only correct on the fall-through path.  This is MY weakness, reported.
    """
    rnd = random.Random(seed)
    rows = []
    for im in sc["per_image"]:
        if "sites" not in im:
            continue
        label = "ef%03d:c%d" % (im["ef"], im["slot"])
        for s in im["sites"]:
            if s.get("op") == 22:
                rows.append((im["ef"], label, s))
    delay = [r for r in rows if str(r[2].get("a1_why", "")).startswith("delay")]
    crossed = [r for r in rows if (r[2].get("a1_crossed") or 0) > 0 and r[2]["a1"] is not None]
    clean = [r for r in rows if (r[2].get("a1_crossed") or 0) == 0 and r[2]["a1"] is not None]
    pick = rnd.sample(rows, min(sample, len(rows)))
    return {
        "op22_sites_seen": len(rows),
        "arg1_set_in_delay_slot": len(delay),
        "delay_slot_examples": [{"site": "%s+%#x" % (r[1], r[2]["off"]), "a1": r[2]["a1"],
                                 "why": r[2]["a1_why"]} for r in delay[:8]],
        "arg1_folded_across_a_branch": len(crossed),
        "arg1_folded_straight_line": len(clean),
        "arg1_runtime": sum(1 for r in rows if r[2]["a1"] is None),
        "sampled": [{"site": "%s+%#x" % (r[1], r[2]["off"]), "a1": r[2]["a1"],
                     "why": r[2]["a1_why"], "crossed": r[2]["a1_crossed"],
                     "parent": r[2]["parent"]} for r in pick[:12]],
    }


# ===================================================================== LENS D
def baserate(sc: Dict[str, object], seed: int = 7, trials: int = 200) -> Dict[str, object]:
    """How special is a tpage-SHAPED constant?  Three independent nulls.

    NULL 1  every ``addiu/ori $rD, $zero, imm`` immediate in the corpus's id-3 code -- the ambient
            population of small constants -- scored on the same three predicates.
    NULL 2  the OTHER argument slots of the SAME op-22 calls ($a0/$a2/$a3), which are the tightest
            possible control: same call, same container, same compiler.
    NULL 3  a PERMUTATION of the winning values ACROSS containers: keep the value multiset, break
            the value<->container pairing, recompute the declared-column rate.  If a value from a
            different container lands on a declared column just as often, "declared column" is a
            property of how many columns a container uploads, not of the value.
    """
    rnd = random.Random(seed)
    cols: Dict[int, set] = {}
    for p in corpus_paths():
        cols[ef_of(p)] = container_columns(open(p, "rb").read())

    def shaped(v: Optional[int]) -> bool:
        return v is not None and 0 <= v < 512 and bool((v >> 4) & 1)

    def declared(ef: int, v: Optional[int]) -> bool:
        return shaped(v) and ((v & 0x0F) * PAGE_HW) in cols.get(ef, set())

    # ---- the observed population (op 22 arg 1)
    obs: List[Tuple[int, int]] = []
    others: Dict[int, List[Tuple[int, int]]] = {0: [], 2: [], 3: []}
    for im in sc["per_image"]:
        if "sites" not in im:
            continue
        for s in im["sites"]:
            if s.get("op") != 22:
                continue
            if s["a1"] is not None:
                obs.append((im["ef"], s["a1"]))
            for ai in (0, 2, 3):
                if s["a%d" % ai] is not None:
                    others[ai].append((im["ef"], s["a%d" % ai]))

    def score(pop):
        n = len(pop)
        if not n:
            return {"n": 0}
        return {"n": n,
                "narrow_lt512": round(sum(1 for e, v in pop if v < 512) / n, 4),
                "shaped": round(sum(1 for e, v in pop if shaped(v)) / n, 4),
                "declared_of_all": round(sum(1 for e, v in pop if declared(e, v)) / n, 4),
                "declared_given_shaped": (
                    round(sum(1 for e, v in pop if declared(e, v))
                          / max(1, sum(1 for e, v in pop if shaped(v))), 4))}

    imm_pool = [tuple(x) for x in sc["imm_pool"]]
    # restrict the ambient pool to the 77-ish containers that actually make the call, so the null
    # sees the same column-declaring population as the observation
    obs_efs = set(e for e, _v in obs)
    imm_same_efs = [(e, v) for e, v in imm_pool if e in obs_efs]

    # ---- NULL 3: permutation
    vals = [v for _e, v in obs]
    efs = [e for e, _v in obs]
    obs_decl = sum(1 for e, v in obs if declared(e, v))
    perm = []
    for _ in range(trials):
        sh = vals[:]
        rnd.shuffle(sh)
        perm.append(sum(1 for e, v in zip(efs, sh) if declared(e, v)))
    perm_mean = sum(perm) / len(perm)
    ge = sum(1 for x in perm if x >= obs_decl)

    # ---- a fourth, harsher null: a UNIFORM random 9-bit value with the y bit forced
    uni = []
    for _ in range(trials):
        uni.append(sum(1 for e in efs
                       if ((rnd.randrange(512) | 0x10) & 0x0F) * PAGE_HW in cols.get(e, set())))
    return {
        "observed_op22_arg1": dict(score(obs), declared_count=obs_decl),
        "null1_ambient_immediates_same_containers": score(imm_same_efs),
        "null1_ambient_immediates_corpus": score(imm_pool),
        "null2_same_call_other_args": {("a%d" % ai): score(v) for ai, v in others.items()},
        "null3_permutation_across_containers": {
            "observed_declared": obs_decl, "n": len(obs),
            "perm_mean_declared": round(perm_mean, 1),
            "perm_rate": round(perm_mean / max(1, len(obs)), 4),
            "trials_ge_observed": ge, "trials": trials,
            "p_value": round((ge + 1) / (trials + 1), 4)},
        "null4_uniform_9bit_with_ybit": {
            "mean_declared": round(sum(uni) / len(uni), 1),
            "rate": round(sum(uni) / len(uni) / max(1, len(efs)), 4)},
        "distinct_values": Counter(vals).most_common(10),
        "distinct_value_count": len(set(vals)),
        "distinct_container_value_pairs": len(set(obs)),
        "containers": len(obs_efs),
    }


# ===================================================================== LENS D-bis: draw-env
def drawenv(sc: Dict[str, object]) -> Dict[str, object]:
    """Is there a DRAW-MODE path L1's single-idiom set misses?

    On the PSX a textured POLY carries its own tpage word, but a SPRT/ TILE takes the page from the
    *current draw mode* (``DR_TPAGE`` / ``SetDrawMode``).  If the effect programs set pages that way
    the constant would show up in some OTHER op's argument -- so this scores EVERY op/arg pair in my
    own scan on the same predicates and reports the field, not just the winner.
    """
    cols: Dict[int, set] = {}
    sos: Dict[int, set] = {}
    for p in corpus_paths():
        blob = open(p, "rb").read()
        cols[ef_of(p)] = container_columns(blob)
        sos[ef_of(p)] = set(s["tpage"] for s in container_so(blob))
    stat: Dict[Tuple[int, int], Counter] = defaultdict(Counter)
    vals: Dict[Tuple[int, int], Counter] = defaultdict(Counter)
    for im in sc["per_image"]:
        if "sites" not in im:
            continue
        ef = im["ef"]
        for s in im["sites"]:
            op = s.get("op")
            if op is None or s.get("parent") != "sysStruct":
                continue
            for ai in range(4):
                v = s["a%d" % ai]
                k = (op, ai)
                stat[k]["sites"] += 1
                if v is None:
                    stat[k]["runtime"] += 1
                    continue
                stat[k]["const"] += 1
                vals[k][v] += 1
                if v < 512:
                    stat[k]["narrow"] += 1
                    if (v >> 4) & 1:
                        stat[k]["ybase"] += 1
                        if ((v & 0x0F) * PAGE_HW) in cols.get(ef, set()):
                            stat[k]["declared"] += 1
                if v in sos.get(ef, set()):
                    stat[k]["so_match"] += 1
    names = {int(o["op"]): o.get("name") for o in json.load(open(HLE_OPS_JSON, encoding="utf-8"))}
    rows = []
    for (op, ai), s in stat.items():
        n = s["const"]
        if n < 8:
            continue
        rows.append({"op": op, "arg": ai, "name": names.get(op), "sites": s["sites"],
                     "const": n, "runtime": s["runtime"],
                     "narrow": s["narrow"], "ybase": s["ybase"], "declared": s["declared"],
                     "so_match": s["so_match"],
                     "score": round((s["narrow"] + s["ybase"] + s["declared"] + s["so_match"])
                                    / (4.0 * n), 4),
                     "top": vals[(op, ai)].most_common(4)})
    rows.sort(key=lambda r: (-r["score"], -r["const"]))
    return {"ranked": rows[:20], "pairs_scored": len(rows)}


# ===================================================================== LENS E
def recal() -> Dict[str, object]:
    """Recompute L1's headline numbers HERE, from its raw hits + pages.json + the kit's so records.

    Nothing is taken from L1's ``join``/``calibration`` blocks -- only ``sweep.hits``, which is raw
    evidence.  A number that does not reproduce is a finding.
    """
    l1 = json.load(open(L1_SWEEP, encoding="utf-8"))
    cen = json.load(open(CENSUS_PAGES, encoding="utf-8"))
    by_cell = {(r["ef"], r["vram_x"], r["vram_y"]): r for r in cen}

    # ---- channel P, rebuilt from raw hits
    prog: Dict[Tuple[int, int, int], Counter] = defaultdict(Counter)
    ptp: Dict[Tuple[int, int, int], set] = defaultdict(set)
    undeclared = 0
    for h in l1["sweep"]["hits"]:
        v = h.get("value")
        if v is None or v >= 512:
            continue
        d = decode_tpage(v)
        px, py = d["page_x"], d["page_y"]
        hit_any = False
        for y in (py, py + CELL_LINES):
            k = (h["ef"], px, y)
            if k in by_cell:
                prog[k][d["bpp"]] += 1
                ptp[k].add(v)
                hit_any = True
        if not hit_any:
            undeclared += 1

    # ---- channel G, rebuilt from the kit's own so records
    sog: Dict[Tuple[int, int, int], Counter] = defaultdict(Counter)
    geom_blind: Dict[int, bool] = {}
    for p in corpus_paths():
        ef = ef_of(p)
        blob = open(p, "rb").read()
        gt = container_geom_total(blob)
        geom_blind[ef] = (gt == 0) if gt is not None else True
        for s in container_so(blob):
            for y in (s["page_y"], s["page_y"] + CELL_LINES):
                k = (ef, s["page_x"], y)
                if k in by_cell:
                    sog[k][s["bpp"]] += 1

    def one(c: Counter) -> Optional[int]:
        return list(c)[0] if len(c) == 1 else None

    ncell = 0
    gt_p = gt_p_agree = 0
    gt_g = gt_g_agree = 0
    dis_p, dis_g = [], []
    unk_p = unk_g = unk_either = 0
    unk_total = 0
    bppnone_either = bppnone_total = 0
    blind_unk = blind_gain = 0
    multi_prog = 0
    xchan_n = xchan_agree = 0
    for k, r in by_cell.items():
        ncell += 1
        pv = one(prog[k]) if k in prog else None
        gv = one(sog[k]) if k in sog else None
        if k in prog and pv is None:
            multi_prog += 1
        cb = r["bpp"]
        if cb is not None and pv is not None:
            gt_p += 1
            if cb == pv:
                gt_p_agree += 1
            else:
                dis_p.append({"id": r["id"], "census": cb, "prog": pv,
                              "tpages": sorted(ptp[k])})
        if cb is not None and gv is not None:
            gt_g += 1
            if cb == gv:
                gt_g_agree += 1
            else:
                dis_g.append({"id": r["id"], "census": cb, "so_page": gv,
                              "spill_in": r["hz_spill_in"],
                              "all_readers_spilled": (bool(r["readers"]) and not any(
                                  x["own_column"] for x in r["readers"]))})
        if pv is not None and gv is not None:
            xchan_n += 1
            xchan_agree += 1 if pv == gv else 0
        if "creature" in r["classes"]:
            continue
        if r["hz_depth_unknown"]:
            unk_total += 1
            if pv is not None:
                unk_p += 1
            if gv is not None:
                unk_g += 1
            if pv is not None or gv is not None:
                unk_either += 1
            if geom_blind.get(r["ef"]):
                blind_unk += 1
                if pv is not None:
                    blind_gain += 1
        if r["bpp"] is None:
            bppnone_total += 1
            if pv is not None or gv is not None:
                bppnone_either += 1

    return {
        "cells": ncell,
        "program": {"ground_truth_n": gt_p, "agree": gt_p_agree,
                    "rate": round(gt_p_agree / gt_p, 4) if gt_p else None,
                    "disagreements": dis_p},
        "so_page": {"ground_truth_n": gt_g, "agree": gt_g_agree,
                    "rate": round(gt_g_agree / gt_g, 4) if gt_g else None,
                    "disagreements": dis_g},
        "cross_channel": {"n": xchan_n, "agree": xchan_agree},
        "gain": {"hz_unknown": unk_total, "program": unk_p, "so_page": unk_g,
                 "either": unk_either,
                 "pct_either": round(100.0 * unk_either / max(1, unk_total), 2),
                 "bpp_none_total": bppnone_total, "bpp_none_either": bppnone_either},
        "structural": {"hz_unknown_in_geom_blind": blind_unk,
                       "geom_blind_gaining_program_depth": blind_gain,
                       "geom_blind_containers": sum(1 for v in geom_blind.values() if v)},
        "program_multi_depth_cells": multi_prog,
        "undeclared_hits": undeclared,
    }


# ===================================================================== follow-ups
def window_probe(sc: Dict[str, object], big: int = 400) -> Dict[str, object]:
    """The 12 sites where my 24-instruction window gave up and L1's block lattice did not.

    A DISAGREEMENT ONLY IN CAPABILITY is still a disagreement until it is closed, so it is closed
    here: the same sites are re-folded with a window long enough to reach the producer, and the
    recovered constant is compared to L1's.  Crossed-transfer counts are reported so the reader can
    see how much straight-line faith each answer needs.
    """
    l1 = json.load(open(L1_SWEEP, encoding="utf-8"))
    l1_hits = {(h["ef"], h["image"], h["off"]): h for h in l1["sweep"]["hits"]}
    want: Dict[int, List[Tuple[str, int, int]]] = defaultdict(list)
    for im in sc["per_image"]:
        if "sites" not in im:
            continue
        label = "ef%03d:c%d" % (im["ef"], im["slot"])
        for s in im["sites"]:
            if s.get("op") != 22 or s["a1"] is not None:
                continue
            k = (im["ef"], label, s["off"])
            if k in l1_hits:
                want[im["ef"]].append((label, im["slot"], s["off"]))
    rows = []
    for p in corpus_paths():
        ef = ef_of(p)
        if ef not in want:
            continue
        blob = open(p, "rb").read()
        for slot, _psx, hrel, pay, _pr in images_of(blob, ""):
            n = min(hrel, len(pay)) // 4
            words = struct.unpack_from("<%dI" % n, pay, 0)
            fold = Fold(words, window=big)          # widened RECURSIVELY, sources included
            for label, sl, off in want[ef]:
                if sl != slot:
                    continue
                i = off // 4
                v, why, crossed = fold.arg(i, 5)
                why = "big-window:" + str(why)
                l1v = l1_hits[(ef, label, off)]["value"]
                rows.append({"site": "%s+%#x" % (label, off), "mine_big_window": v,
                             "l1": l1v, "why": why, "crossed": crossed, "agree": v == l1v})
    return {"n": len(rows), "agree": sum(1 for r in rows if r["agree"]),
            "rows": rows}


#: Every HLE entry point that can bind a TEXTURE to a model, from the DLL's own debug strings.
TEX_REG_OPS = {22: "Hi_RegisterTexEffModel", 19: "Hi_RegisterTexListModel",
               171: "Hi_RegisterTexPtrModel"}
#: ...and the untextured / creature-only registration + draw ops, for contrast.
OTHER_REG_OPS = {6: "Hi_RegisterGouEffModel", 21: "Hi_RegisterSolidEffModel",
                 23: "Hi_RegisterSummonModel"}
DRAW_OPS = {24: "Hi_DrawEffModel", 25: "Hi_DrawSummonModel", 163: "Hi_DrawMorphEffModel",
            199: "Hi_DrawSliceEffModel", 145: "Hi_DrawMorphModelByBone",
            162: "Hi_DrawEffModelByBone"}


def regops(sc: Dict[str, object]) -> Dict[str, object]:
    """DOES THE API EVEN HAVE A DRAW-MODE PATH? -- lens (iv), answered by naming the whole surface.

    On a real PSX a ``SPRT``/``TILE`` takes its page from the *draw mode* word, not from the prim,
    so an idiom set built only on prim-level tpages would miss it.  This effect VM is not a
    primitive API: of 216 HLE ops, 79 carry a DLL debug-string name and not one of them is a
    ``DR_TPAGE`` / ``SetDrawMode`` / ``AddPrim`` / sprite entry point.  Every textured thing goes
    through ``Hi_Register*Model`` -> ``Hi_Draw*Model``.  So the coverage question is not "prim vs
    draw-env", it is "which of the THREE texture-registration ops does L1 read" -- measured here,
    split by the geom-blind population that bounds the whole lane.
    """
    blind: Dict[int, bool] = {}
    for p in corpus_paths():
        gt = container_geom_total(open(p, "rb").read())
        blind[ef_of(p)] = (gt == 0) if gt is not None else True
    per_op_sites: Counter = Counter()
    per_op_efs: Dict[int, set] = defaultdict(set)
    blind_op_sites: Counter = Counter()
    blind_op_efs: Dict[int, set] = defaultdict(set)
    for im in sc["per_image"]:
        if "sites" not in im:
            continue
        ef = im["ef"]
        for s in im["sites"]:
            op = s.get("op")
            if op is None:
                continue
            per_op_sites[op] += 1
            per_op_efs[op].add(ef)
            if blind.get(ef):
                blind_op_sites[op] += 1
                blind_op_efs[op].add(ef)
    names = dict(TEX_REG_OPS)
    names.update(OTHER_REG_OPS)
    names.update(DRAW_OPS)
    rows = []
    for op, nm in sorted(names.items()):
        rows.append({"op": op, "name": nm, "sites": per_op_sites[op],
                     "containers": len(per_op_efs[op]),
                     "blind_sites": blind_op_sites[op],
                     "blind_containers": len(blind_op_efs[op])})
    tex_sites = sum(per_op_sites[o] for o in TEX_REG_OPS)
    return {
        "geom_blind_containers": sum(1 for v in blind.values() if v),
        "geom_bearing_containers": sum(1 for v in blind.values() if not v),
        "rows": rows,
        "texture_registration_sites_total": tex_sites,
        "covered_by_L1_op22": per_op_sites[22],
        "L1_coverage_of_textured_registration": round(per_op_sites[22] / max(1, tex_sites), 4),
        "blind_containers_making_ANY_texture_registration": len(
            set().union(*[blind_op_efs[o] for o in TEX_REG_OPS]) or set()),
        "no_drawmode_op_exists": True,
    }


def reach(paths: Optional[Sequence[str]] = None) -> Dict[str, object]:
    """LENS B, the real question: are the hits inside the reachability closure at all?

    My linear scan is seed-free, so it is the instrument that CAN see dead code.  The reference
    walk is seeded from the image's own 16-entry program table.  Containment in both directions is
    the measurement; the walk's coverage fraction is reported beside it so "reached" is not
    mistaken for "the whole image".
    """
    import tier_r_disasm as D
    paths = list(paths or corpus_paths())
    hle = D.load_hle_names()
    total = inside = 0
    cov: List[float] = []
    for p in paths:
        blob = open(p, "rb").read()
        src = os.path.splitext(os.path.basename(p))[0]
        try:
            imgs = D.id3_images(blob, src)
        except Exception:
            continue
        for img in imgs:
            mine = [s for s in scan_image(img.payload, img.header_rel) if s.get("op") == 22]
            if not mine:
                continue
            w = D.ImageWalker(img.payload, img.psx_base, img.header_rel, img.live_programs,
                              name=img.label, hle_names=hle)
            r = w.run()
            cov.append(r.coverage)
            for s in mine:
                total += 1
                inside += 1 if s["off"] in r.instrs else 0
    return {"op22_sites": total, "inside_reachability_closure": inside,
            "outside": total - inside,
            "mean_walk_coverage_of_op22_images": round(sum(cov) / max(1, len(cov)), 4),
            "images_measured": len(cov)}


def audit(sc: Dict[str, object]) -> Dict[str, object]:
    """Three questions L1's own numbers do not answer, plus an internal audit of its json.

    1  HOW THIN IS THE GROUND TRUTH, REALLY?  L1 reports P's ``N = 10`` at CELL level and argues the
       scarcity is inherent.  Test it by dropping the census-cell requirement entirely and comparing
       P and G at PAGE level -- the largest sample the two channels can possibly share.
    2  IS DEPTH THE ONLY GATE?  The gained cells are re-scored against every OTHER hazard the census
       already carries, because "gains a depth" and "the texel lane can edit it" are different
       claims and only the first was measured.
    3  IS THE BLIND POPULATION'S SILENCE AN ARTEFACT OF THE SCANNER?  If my instrument simply fails
       on those images their op-22 silence proves nothing; count their RESOLVED calls first.
    4  DOES L1'S PROSE MATCH L1'S JSON?  Restatement is not evidence; the tier compositions quoted
       in the dossier are checked against the raw hits.
    """
    l1 = json.load(open(L1_SWEEP, encoding="utf-8"))
    cen = json.load(open(CENSUS_PAGES, encoding="utf-8"))
    by = {(r["ef"], r["vram_x"], r["vram_y"]): r for r in cen}

    # ---- 1: page-level widening
    prog_pg: Dict[Tuple[int, int, int], set] = defaultdict(set)
    prog_cell: Dict[Tuple[int, int, int], Counter] = defaultdict(Counter)
    for h in l1["sweep"]["hits"]:
        v = h.get("value")
        if v is None or v >= 512:
            continue
        d = decode_tpage(v)
        prog_pg[(h["ef"], d["page_x"], d["page_y"])].add(d["bpp"])
        for y in (d["page_y"], d["page_y"] + CELL_LINES):
            k = (h["ef"], d["page_x"], y)
            if k in by:
                prog_cell[k][d["bpp"]] += 1
    so_pg: Dict[Tuple[int, int, int], set] = defaultdict(set)
    so_cell: Dict[Tuple[int, int, int], Counter] = defaultdict(Counter)
    blind: Dict[int, bool] = {}
    for p in corpus_paths():
        ef = ef_of(p)
        blob = open(p, "rb").read()
        gt = container_geom_total(blob)
        blind[ef] = (gt == 0) if gt is not None else True
        for s in container_so(blob):
            so_pg[(ef, s["page_x"], s["page_y"])].add(s["bpp"])
            for y in (s["page_y"], s["page_y"] + CELL_LINES):
                k = (ef, s["page_x"], y)
                if k in by:
                    so_cell[k][s["bpp"]] += 1
    shared = set(prog_pg) & set(so_pg)
    pg_ag = sum(1 for k in shared if len(prog_pg[k]) == 1 and len(so_pg[k]) == 1
                and prog_pg[k] == so_pg[k])

    # ---- 2: hazards on the gained cells
    HZ = ("hz_multi_palette", "hz_shared_read", "hz_program_write", "hz_program_write_here",
          "hz_co_transform", "hz_unaddressable_lower_half", "hz_attribution_blind")
    hz = Counter()
    gained = 0
    clean = 0
    for k, r in by.items():
        if "creature" in r["classes"] or not r["hz_depth_unknown"]:
            continue
        pv = list(prog_cell[k])[0] if len(prog_cell[k]) == 1 else None
        gv = list(so_cell[k])[0] if len(so_cell[k]) == 1 else None
        if pv is None and gv is None:
            continue
        gained += 1
        for f in HZ:
            if r.get(f):
                hz[f] += 1
        if r["hz_spill_in"]:
            hz["hz_spill_in"] += 1
        blockers = ("hz_multi_palette", "hz_shared_read", "hz_program_write", "hz_co_transform",
                    "hz_unaddressable_lower_half")
        if not any(r.get(f) for f in blockers) and not r["hz_spill_in"] and r["w_is_64"]:
            clean += 1

    # ---- 3: the blind population's own call profile
    resolved = Counter()
    blind_efs_with_calls = set()
    blind_ops = Counter()
    for im in sc["per_image"]:
        if "sites" not in im:
            continue
        b = blind.get(im["ef"])
        for s in im["sites"]:
            if s.get("op") is None:
                resolved["unresolved_jalr_%s" % ("blind" if b else "geom")] += 1
                continue
            resolved["resolved_%s" % ("blind" if b else "geom")] += 1
            if b:
                blind_efs_with_calls.add(im["ef"])
                blind_ops[s["op"]] += 1

    # ---- 4: L1's prose vs L1's json
    promoted = l1["sweep"]["promoted"]
    return {
        "page_level_widening": {
            "program_named_pages": len(prog_pg), "so_named_pages": len(so_pg),
            "pages_named_by_BOTH": len(shared), "agree": pg_ag,
            "program_pages_with_no_so_record": len(set(prog_pg) - set(so_pg)),
            "pct_of_program_pages_uncorroborated":
                round(100.0 * len(set(prog_pg) - set(so_pg)) / max(1, len(prog_pg)), 1)},
        "gained_cell_hazards": {
            "gained": gained, "hazards": dict(hz),
            "clean_of_every_other_listed_hazard": clean,
            "pct_of_2385_actually_clean": round(100.0 * clean / 2385, 2)},
        "blind_population": {
            "geom_blind_containers": sum(1 for v in blind.values() if v),
            "blind_containers_with_at_least_one_resolved_hle_call": len(blind_efs_with_calls),
            "resolved_call_sites": dict(resolved),
            "blind_top_ops": blind_ops.most_common(10)},
        "L1_json_vs_prose": {
            "promoted_by_ef": dict(Counter(x["ef"] for x in promoted)),
            "promoted_images": sorted(set(x["image"] for x in promoted)),
            "weak_by_ef": dict(Counter(x["ef"] for x in l1["sweep"]["weak_dispatch"])),
            "runtime_by_ef": dict(Counter(x["ef"] for x in l1["sweep"]["runtime"])),
            "dossier_says": "corroborated 8 = ef122 x1, ef125 x3, ef251 x4; 'in all four images'",
            "json_says": "corroborated 8 = ef125 x3 + ef251 x5, across TWO images; ef122's single "
                         "site is the REFUSED one",
            "strong_declared_column": "%d/%d" % (
                sum(1 for x in l1["sweep"]["hits"]
                    if x["tier"] == "strong" and x["declared_column"]),
                sum(1 for x in l1["sweep"]["hits"] if x["tier"] == "strong")),
            "all_hits_declared_column": "%d/%d" % (
                sum(1 for x in l1["sweep"]["hits"] if x["declared_column"]),
                len(l1["sweep"]["hits"]))},
    }


# ===================================================================== CLI
def _dump(name: str, obj) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    p = os.path.join(OUT_DIR, name)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["scan", "compare", "baserate", "drawenv", "recal",
                                    "window", "regops", "reach", "audit", "all"])
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    print(c0())
    paths = corpus_paths()
    if a.limit:
        paths = paths[:a.limit]

    sc = None
    cache = os.path.join(OUT_DIR, "v1a_scan.json")
    if a.cmd in ("scan", "all") or not os.path.exists(cache):
        sc = scan(paths)
        _dump("v1a_scan.json", sc)
        print("linear scan: %d images, %.1fs" % (len(sc["per_image"]), sc["seconds"]))
        if a.cmd == "scan":
            return 0
    if sc is None:
        sc = json.load(open(cache, encoding="utf-8"))

    out: Dict[str, object] = {}
    vp = os.path.join(OUT_DIR, "v1a_verify.json")
    if os.path.exists(vp):                       # accumulate: one subcommand must not erase another
        out = json.load(open(vp, encoding="utf-8"))
    out["decoder_check"] = c0()
    if a.cmd in ("compare", "all"):
        out["lensA_B_compare"] = compare(sc)
        out["lensC_masquerade"] = masquerade(sc)
    if a.cmd in ("baserate", "all"):
        out["lensD_baserate"] = baserate(sc)
    if a.cmd in ("drawenv", "all"):
        out["lensD_drawenv"] = drawenv(sc)
    if a.cmd in ("recal", "all"):
        out["lensE_recal"] = recal()
    if a.cmd in ("window", "all"):
        out["window_probe"] = window_probe(sc)
    if a.cmd in ("regops", "all"):
        out["lensIV_regops"] = regops(sc)
    if a.cmd in ("reach", "all"):
        out["lensB_reach"] = reach(paths)
    if a.cmd in ("audit", "all"):
        out["audit"] = audit(sc)
    p = _dump("v1a_verify.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "decoder_check"},
                     indent=1, default=str)[:9000])
    print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
