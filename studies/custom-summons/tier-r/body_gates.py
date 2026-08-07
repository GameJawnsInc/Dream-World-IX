"""body_gates -- the gate board for the HANDLER-BODY evidence class (op 117).

B1/B2 are DLL-side and always run.  B3-B5 score the claim against the corpus, and B4 is the one
that could have killed it: if the relocator's reading validated equally on sub-files op 117 never
touches, the structure would be a coincidence and the name would not ship.

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


def feeders() -> Dict[Tuple[int, int], Set[int]]:
    """{(ef, chunk): {sub-file index}} that the corpus feeds to op 117 via op 102."""
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
            elif op == B.OP_OPEN:
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


def main() -> int:
    results: List[Tuple[str, str, bool]] = []
    dll = A.DllView()

    ok, notes = B.verify(dll)
    for n in notes:
        print("  " + n)
    results.append(("B1", "every structural claim re-derives from the installed DLL", ok))

    ev = B.body_evidence(dll)
    good = set(ev) == {B.OP_OPEN} and ev[B.OP_OPEN]["confidence"] == "medium"
    print("\nB2 body evidence: %s" % {o: (e["name"], e["confidence"]) for o, e in ev.items()})
    results.append(("B2", "the name ships at medium -- no symbol supplies it", good))

    have_corpus = os.path.isdir(ANNOT) and os.path.isdir(A.SCRATCH_CORPUS)
    if not have_corpus:
        print("\nB3-B5 SKIPPED -- no annotated corpus at %s" % ANNOT)
        # A skip is not a pass: report it as such rather than counting it green.
        for k, d in (("B3", "the sub-file idiom"), ("B4", "the A/B separation"),
                     ("B5", "camera disjointness")):
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
