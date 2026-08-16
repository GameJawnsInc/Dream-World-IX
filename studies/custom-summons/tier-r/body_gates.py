"""body_gates -- the gate board for the HANDLER-BODY evidence class (117, 206, 136, 48/49/50).

B1/B2/B6 are DLL-side and always run.  B3-B5 (op 117) and B7-B8 (op 206) score the claims against
the corpus.  Two of them could have killed their claim outright:

* **B4** -- if the relocator's reading validated equally on sub-files op 117 never touches, the
  structure would be a coincidence and the name would not ship.
* **B8** -- op 206's operand must carry the ``'so'`` magic BECAUSE THE DLL ASSERTS IT.  If the
  unpaired misses carried the magic at some nonzero offset, the operand would be ``base + k`` and
  the reading would be wrong.  They carry it at none, so the shortfall measures the pairing
  heuristic instead of the claim -- the assert is what makes that inference available.

    py studies/custom-summons/tier-r/body_gates.py
"""
from __future__ import annotations

import collections
import glob
import os
import re
import struct
import sys
from typing import Dict, List, Optional, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import body_ops as B
import tier_r_annot as A

ANNOT = os.path.join(A.SCRATCH_CORPUS, "annot-r2")

#: The published numbers this board pins.  A drift here means the corpus or the reading moved, and
#: the report's claims are stale -- which is the point of pinning them.
EXPECT_FED_RATE = (0.55, 0.70)      # set A validation rate
EXPECT_CTRL_MAX = 0.12              # set B must stay far below it
EXPECT_SUBFILE_IDIOM = 0.95         # share of op-117 sites fed by a constant-index op 102


def _kit():
    sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..", "..", "..", "ff9mapkit")))
    from ff9mapkit.summons import container as K, camera as CAM
    return K, CAM


def feeders(target_op: int = B.OP_OPEN) -> Dict[Tuple[int, int], Set[int]]:
    """{(ef, chunk): {sub-file index}} that the corpus feeds to ``target_op`` via op 102."""
    out: Dict[Tuple[int, int], Set[int]] = collections.defaultdict(set)
    for f in sorted(glob.glob(os.path.join(ANNOT, "ef*.asm"))):
        m = re.match(r"ef(\d+)_c(\d)\.asm", os.path.basename(f))
        if not m:
            continue
        key = (int(m.group(1)), int(m.group(2)))
        last: Optional[int] = None
        for ln in open(f, encoding="utf-8", errors="replace"):
            mm = re.search(r"HLE op (\d+)", ln)
            if not mm:
                continue
            op = int(mm.group(1))
            if op == A.SUBFILE_OP:
                a1 = re.search(r"\$a1=0x([0-9a-f]+)", ln)
                last = (int(a1.group(1), 16) & A.SUBFILE_INDEX_MASK) if a1 else None
            elif op == target_op:
                if last is not None:
                    out[key].add(last)
                last = None
            else:
                last = None
    return out


def site_idiom() -> Tuple[int, int]:
    """(sites preceded by a constant-index op 102, total op-117 sites)."""
    hit = tot = 0
    for f in sorted(glob.glob(os.path.join(ANNOT, "ef*.asm"))):
        last = None
        for ln in open(f, encoding="utf-8", errors="replace"):
            mm = re.search(r"HLE op (\d+)", ln)
            if not mm:
                continue
            op = int(mm.group(1))
            if op == A.SUBFILE_OP:
                last = re.search(r"\$a1=0x([0-9a-f]+)", ln)
            elif op == B.OP_OPEN:
                tot += 1
                hit += last is not None
                last = None
            else:
                last = None
    return hit, tot


def ab_test() -> Tuple[int, int, int, int, int, int]:
    """(A, Aok, Bctrl, Bok, camera sub-files, overlap with op-117 sub-files)."""
    K, CAM = _kit()
    feed = feeders()
    a = aok = b = bok = ncam = overlap = 0
    seen_ef: Set[int] = set()
    for (ef, ck), idxs in sorted(feed.items()):
        path = os.path.join(A.SCRATCH_CORPUS, "ef%03d.bytes" % ef)
        if not os.path.isfile(path):
            continue
        blob = open(path, "rb").read()
        try:
            cont = K.parse_header(blob, strict=False)
        except Exception:
            continue
        slots = [c.slot for c in cont.chunks]
        if ck >= len(slots):
            continue
        arc = CAM.id2_directory(blob, cont, slots[ck])
        if not arc:
            continue
        for i in range(len(arc.entries)):
            try:
                lo, hi = arc.bounds(i)
            except Exception:
                continue
            if hi <= lo:
                continue
            ok = B.relocator_reading(blob, lo, hi) is not None
            if i in idxs:
                a += 1
                aok += ok
            else:
                b += 1
                bok += ok
        if ef not in seen_ef:
            seen_ef.add(ef)
            try:
                ex = CAM.extract_shots(blob, source="ef%03d" % ef)
            except Exception:
                continue
            cam = set()
            for s in ex.shots:
                idx = getattr(s, "subfile", getattr(s, "index", None))
                slot = getattr(s, "chunk", getattr(s, "slot", None))
                if idx is not None:
                    cam.add((slot, idx))
            ncam += len(cam)
            allfed = {(c, j) for (e, c), js in feed.items() if e == ef for j in js}
            overlap += len(cam & allfed)
    return a, aok, b, bok, ncam, overlap


def so_ab() -> Tuple[int, int, int, int, int, int, int]:
    """(A, Aok, B, Bok, texlist, gouraud, misses-with-the-magic-at-a-nonzero-offset).

    ``off`` is the load-bearing one: the DLL ASSERTS the magic, so a real operand cannot lack it.
    If the misses carried it at some offset, the operand would be ``base + k`` and the reading would
    be wrong; they do not, so the shortfall measures the pairing heuristic instead.
    """
    K, CAM = _kit()
    feed = feeders(B.OP_ABR)
    a = aok = b = bok = tex = gou = off = 0
    for (ef, ck), idxs in sorted(feed.items()):
        path = os.path.join(A.SCRATCH_CORPUS, "ef%03d.bytes" % ef)
        if not os.path.isfile(path):
            continue
        blob = open(path, "rb").read()
        try:
            cont = K.parse_header(blob, strict=False)
        except Exception:
            continue
        slots = [c.slot for c in cont.chunks]
        if ck >= len(slots):
            continue
        arc = CAM.id2_directory(blob, cont, slots[ck])
        if not arc:
            continue
        for i in range(len(arc.entries)):
            try:
                lo, hi = arc.bounds(i)
            except Exception:
                continue
            if hi <= lo:
                continue
            r = B.so_reading(blob, lo, hi)
            if i in idxs:
                a += 1
                if r:
                    aok += 1
                    if r[0]:
                        tex += 1
                    else:
                        gou += 1
                else:
                    for k in range(2, min(hi - lo - 8, 0x400), 2):
                        if B.so_reading(blob, lo + k, hi):
                            off += 1
                            break
            else:
                b += 1
                bok += bool(r)
    return a, aok, b, bok, tex, gou, off


def screen_args() -> Tuple[int, int, int, int, set]:
    """(op-64 colour constants, how many are <= 255, control constants, control <= 255, $a1 set).

    If arg2/arg3 were coordinates or ids they would routinely exceed a colour byte.  The control is
    every OTHER op with at least three integer arguments, scored by the same rule.
    """
    ops = A.load_hle_ops()
    hit = tot = chit = ctot = 0
    a1: set = set()
    pat = re.compile(r"\$a(\d)=0x([0-9a-f]+)")
    for f in sorted(glob.glob(os.path.join(ANNOT, "ef*.asm"))):
        for ln in open(f, encoding="utf-8", errors="replace"):
            mm = re.search(r"HLE op (\d+) ", ln)
            if not mm:
                continue
            op = int(mm.group(1))
            row = ops.get(op)
            if not row:
                continue
            for idx, val in ((int(a), int(v, 16)) for a, v in pat.findall(ln)):
                if op == B.OP_SCREEN:
                    if idx == 1:
                        a1.add(val)
                    elif idx in (2, 3):
                        tot += 1
                        hit += val <= 0xFF
                elif (row.get("arg_kinds") or "").count("i") >= 3 and idx in (2, 3):
                    ctot += 1
                    chit += val <= 0xFF
    return hit, tot, chit, ctot, a1


def addprim_args():
    """(op-143 $a0 count, how many are primitive TAGS, control count, control tags).

    A tag has its length in the top byte and a zeroed 24-bit link field.  If arg0 were an id, a
    count or a pointer it would not look like that -- which is what the control measures.
    """
    ops = A.load_hle_ops()
    pat = re.compile(r"\$a0=0x([0-9a-f]+)")
    is_tag = lambda v: (v & B.ADDPRIM_LINK_MASK) == 0 and 1 <= (v >> B.ADDPRIM_TAG_SHIFT) <= 16
    hit = tot = chit = ctot = 0
    for f in sorted(glob.glob(os.path.join(ANNOT, "ef*.asm"))):
        for ln in open(f, encoding="utf-8", errors="replace"):
            mm = re.search(r"HLE op (\d+) ", ln)
            if not mm:
                continue
            op = int(mm.group(1))
            row = ops.get(op)
            if not row:
                continue
            for v in (int(x, 16) for x in pat.findall(ln)):
                if op == B.OP_ADDPRIM:
                    tot += 1
                    hit += is_tag(v)
                elif (row.get("arg_kinds") or "").startswith("i"):
                    ctot += 1
                    chit += is_tag(v)
    return hit, tot, chit, ctot


def main() -> int:
    results: List[Tuple[str, str, bool]] = []
    dll = A.DllView()

    ok, notes = B.verify(dll)
    for n in notes:
        print("  " + n)
    results.append(("B1", "every structural claim re-derives from the installed DLL", ok))

    ok6, notes6 = B.verify_abr(dll)
    print()
    for n in notes6:
        print("  " + n)
    results.append(("B6", "op 206's body + BOTH tail-call names re-derive from the DLL", ok6))

    ok9, notes9 = B.verify_coord(dll)
    print()
    for n in notes9:
        print("  " + n)
    results.append(("B9", "op 136's lookup + divide-by-6 + add re-derive from the DLL", ok9))

    ok13, notes13 = B.verify_addprim(dll)
    print()
    for n in notes13:
        print("  " + n)
    results.append(("B13", "op 143's OT splice and DR_TPAGE blend prefix re-derive", ok13))

    ok11, notes11 = B.verify_screen(dll)
    print()
    for n in notes11:
        print("  " + n)
    results.append(("B11", "op 64's tile grid, blend code and AddPrim hand-off re-derive", ok11))

    ok10, notes10 = B.verify_rng(dll)
    print()
    for n in notes10:
        print("  " + n)
    results.append(("B10", "the RNG family's shared ANSI-C LCG re-derives from the DLL", ok10))

    ev = B.body_evidence(dll)
    good = (set(ev) == {B.OP_OPEN, B.OP_ABR, B.OP_COORD,
                        B.OP_RAND, B.OP_RAND_RANGE, B.OP_RAND_CENTERED, B.OP_SCREEN,
                        B.OP_ADDPRIM}
            and ev[B.OP_OPEN]["confidence"] == "medium"      # no symbol names it
            and ev[B.OP_COORD]["confidence"] == "medium"     # no symbol; +0x38 unresolved
            and ev[B.OP_RAND]["confidence"] == "medium"      # algorithm known, name not stated
            and ev[B.OP_SCREEN]["confidence"] == "medium"    # no symbol on the chain
            and ev[B.OP_ADDPRIM]["confidence"] == "medium"   # libgpu shape, no stated name
            and ev[B.OP_ABR]["confidence"] == "high")        # the DLL names it, twice
    print("\nB2 body evidence: %s" % {o: (e["name"], e["confidence"]) for o, e in ev.items()})
    results.append(("B2", "each name ships at the confidence its evidence supports", good))

    have_corpus = os.path.isdir(ANNOT) and os.path.isdir(A.SCRATCH_CORPUS)
    if not have_corpus:
        print("\nB3-B5 SKIPPED -- no annotated corpus at %s" % ANNOT)
        # A skip is not a pass: report it as such rather than counting it green.
        for k, d in (("B3", "the sub-file idiom"), ("B4", "the A/B separation"),
                     ("B5", "camera disjointness"), ("B7", "the 'so' magic"),
                     ("B8", "the pairing attribution"), ("B12", "op 64's colour args"),
                     ("B14", "op 143's tag argument")):
            print("  %s %s -- SKIP" % (k, d))
    else:
        hit, tot = site_idiom()
        rate = hit / max(tot, 1)
        print("\nB3 op-117 sites fed by a constant-index op 102: %d/%d (%.1f%%)"
              % (hit, tot, 100 * rate))
        results.append(("B3", "op 117's first argument is a sub-file pointer",
                        rate >= EXPECT_SUBFILE_IDIOM))

        a, aok, b, bok, ncam, overlap = ab_test()
        ra, rb = aok / max(a, 1), bok / max(b, 1)
        print("B4 relocator reading: fed %d/%d (%.1f%%) vs control %d/%d (%.1f%%)"
              % (aok, a, 100 * ra, bok, b, 100 * rb))
        results.append(("B4", "the reading discriminates fed sub-files from the control",
                        EXPECT_FED_RATE[0] <= ra <= EXPECT_FED_RATE[1] and rb <= EXPECT_CTRL_MAX
                        and ra > 5 * rb))
        print("B5 camera sub-files %d, overlap with op-117 sub-files %d" % (ncam, overlap))
        results.append(("B5", "op 117 is not the camera lane", ncam > 500 and overlap == 0))

        a, aok, b, bok, tex, gou, off = so_ab()
        ra, rb = aok / max(a, 1), bok / max(b, 1)
        print("B7 'so' magic: fed %d/%d (%.1f%%) vs control %d/%d (%.1f%%); variants tex=%d gou=%d"
              % (aok, a, 100 * ra, bok, b, 100 * rb, tex, gou))
        results.append(("B7", "op 206's operand carries the magic the DLL asserts",
                        ra > 0.6 and rb < 0.10 and ra > 10 * rb and tex > gou > 0))
        chit, ctot, cc, cct, a1 = screen_args()
        r, cr = chit / max(ctot, 1), cc / max(cct, 1)
        print("B12 op-64 colour args <= 255: %d/%d (%.1f%%) vs control %d/%d (%.1f%%); blend modes seen = %s"
              % (chit, ctot, 100 * r, cc, cct, 100 * cr, sorted(a1)))
        results.append(("B12", "op 64's arg2/arg3 are colour bytes and arg1 is a small blend-mode set",
                        ctot > 50 and r == 1.0 and r > cr and a1 <= {0, 1, 2, 255}))

        ah, at, ach, act = addprim_args()
        ar, acr = ah / max(at, 1), ach / max(act, 1)
        print("B14 op-143 $a0 that are primitive TAGS: %d/%d (%.1f%%) vs control %d/%d (%.1f%%)"
              % (ah, at, 100 * ar, ach, act, 100 * acr))
        results.append(("B14", "op 143's arg0 is a primitive tag, not an id or a pointer",
                        at >= 9 and ar == 1.0 and acr < 0.05))

        print("B8 misses carrying 'so' at ANY nonzero offset: %d" % off)
        results.append(("B8", "the shortfall is pairing, not an operand the assert would reject",
                        off == 0))

    print("=" * 72)
    print("BODY GATES")
    print("=" * 72)
    for k, d, r in results:
        print("%-4s %-62s %s" % (k, d, "PASS" if r else "FAIL"))
    npass = sum(1 for _, _, r in results if r)
    print("=" * 72)
    print("%d/%d gates pass%s" % (npass, len(results),
                                  "" if have_corpus else "  (3 skipped -- no corpus)"))
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
