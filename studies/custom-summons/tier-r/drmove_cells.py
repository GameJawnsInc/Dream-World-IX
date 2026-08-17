"""drmove_cells -- do op 144's VRAM scroll blits land on cells the texel lane lets you repaint?

WHY THIS CAN BE ASKED AT ALL.  The W6b program-VRAM census is built from ``LoadImage`` /
``StoreImage`` / ``MoveImage`` / loader-op ``0x07``, and its own note records the ceiling:

    "0 of 18 RECT* arguments const-fold, so the only PER-CELL verdict in the corpus is
     MOVEIMAGE_HARD_CELLS"

-- three hard-coded cells.  Those ops take the rectangle as a **pointer**, and pointers do not fold.
**op 144 takes its rectangle as seven loose integers**, and `arg1` (dst x), `arg2` (dst y) and
`arg3` (width) fold in the ordinary census; `arg4` (the period, i.e. the height) rides the MIPS stack
at ``$sp+0x10`` and folds here.  So this op yields **per-cell destination verdicts that the existing
census structurally could not produce** -- and op 144 was never in its writer union at all.

WHAT A HIT MEANS.  op 144 rewrites its destination band every frame it runs (that is the point -- it
is a scroll).  A repaint of a cell inside that band is therefore **overwritten at runtime**, silently:
the artifact is byte-correct on disk, the deploy verifies, and the picture never appears.  That is
precisely the failure mode W6b-3(iv) flagged as the arc's open risk -- the GAIN half "fails SILENTLY
... with no way to decline".

A SOURCE hit is different and much milder: the repaint is READ and propagated into the destination,
so it shows up, just also somewhere else.  The two are reported separately and never merged.

    py studies/custom-summons/tier-r/drmove_cells.py            # the corpus verdict
    py studies/custom-summons/tier-r/drmove_cells.py --ef 407   # one container, verbose
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import body_ops as B
import tier_r_annot as A

ANNOT = os.path.join(A.SCRATCH_CORPUS, "annot-r2")
KIT = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "ff9mapkit"))

#: O32: the first stacked argument sits at ``$sp+0x10``, one word each.
STACK_SLOTS = {0x10: 4, 0x14: 5, 0x18: 6}
_CONST = re.compile(r"addiu\s+\$(\w+), \$zero, (-?\d+)")
_MOVE = re.compile(r"addu\s+\$(\w+), \$(\w+), \$zero")
_STORE = re.compile(r"sw\s+\$(\w+), (\d+)\(\$sp\)")
_SITE = re.compile(r"HLE op 144 ")
_ARG = re.compile(r"\$a(\d)=0x([0-9a-f]+)")
_CELL = re.compile(r"x(\d+)_y(\d+)")


def _kit():
    if KIT not in sys.path:
        sys.path.insert(0, KIT)
    from ff9mapkit.summons import repaint, reskin
    return repaint, reskin


def blit_rects(path: str) -> List[Dict[str, object]]:
    """Every op-144 site in one annotated listing, as dst/src rectangles.

    Constant folding is deliberately shallow -- ``addiu $r, $zero, N`` and ``addu $r, $s, $zero``
    only.  A site whose period (arg4) does not fold is reported with ``h=None`` and EXCLUDED from
    the verdict rather than guessed at; the count of those is published so the coverage is honest.
    """
    const: Dict[str, int] = {}
    stack: Dict[int, Optional[int]] = {}
    out: List[Dict[str, object]] = []
    for ln in open(path, encoding="utf-8", errors="replace"):
        m = _CONST.search(ln)
        if m:
            const[m.group(1)] = int(m.group(2))
        m = _MOVE.search(ln)
        if m:
            const[m.group(1)] = const.get(m.group(2))
        m = _STORE.search(ln)
        if m and int(m.group(2)) in STACK_SLOTS:
            stack[STACK_SLOTS[int(m.group(2))]] = const.get(m.group(1))
        if _SITE.search(ln):
            args = {int(i): int(v, 16) for i, v in _ARG.findall(ln)}
            x, y, w = args.get(1), args.get(2), args.get(3)
            h, sx, sy = stack.get(4), stack.get(5), stack.get(6)
            out.append({"x": x, "y": y, "w": w, "h": h, "sx": sx, "sy": sy})
            stack.clear()
    return out


def overlaps(ax, ay, aw, ah, bx, by, bw, bh) -> bool:
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def cell_xy(name: str) -> Optional[Tuple[int, int]]:
    m = _CELL.search(name or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def analyse(effects: Optional[Sequence[int]] = None, verbose: bool = False):
    repaint, reskin = _kit()
    cw, ch = reskin.PAGE_CELL_W, reskin.PAGE_CELL_LINES
    dst_hits: Dict[int, List[str]] = {}
    src_hits: Dict[int, List[str]] = {}
    scanned = sites = unfolded = 0
    surfaced = 0

    seen: Dict[int, List[Dict[str, object]]] = {}
    for f in sorted(glob.glob(os.path.join(ANNOT, "ef*.asm"))):
        m = re.match(r"ef(\d+)_c\d\.asm", os.path.basename(f))
        if not m:
            continue
        ef = int(m.group(1))
        if effects and ef not in effects:
            continue
        rects = blit_rects(f)
        if rects:
            seen.setdefault(ef, []).extend(rects)

    for ef, rects in sorted(seen.items()):
        path = os.path.join(A.SCRATCH_CORPUS, "ef%03d.bytes" % ef)
        if not os.path.isfile(path):
            continue
        scanned += 1
        blob = open(path, "rb").read()
        try:
            pages = repaint.scenery_texel_pages(blob, effect=ef)
        except Exception:
            continue
        cells = [(p, cell_xy(getattr(p, "name", ""))) for p in pages]
        cells = [(p, xy) for p, xy in cells if xy]
        surfaced += len(cells)
        for r in rects:
            sites += 1
            if r["h"] is None or r["x"] is None or r["w"] is None:
                unfolded += 1
                continue
            for p, (cx, cy) in cells:
                if overlaps(r["x"], r["y"], r["w"], r["h"], cx, cy, cw, ch):
                    dst_hits.setdefault(ef, []).append(p.name)
                if (r["sx"] is not None and r["sy"] is not None
                        and overlaps(r["sx"], r["sy"], r["w"], r["h"], cx, cy, cw, ch)):
                    src_hits.setdefault(ef, []).append(p.name)
        if verbose:
            print("ef%03d  edit surface: %s" % (ef, [p.name for p, _ in cells]))
            for r in rects:
                print("   blit dst=(%s,%s) %sx%s  src=(%s,%s)"
                      % (r["x"], r["y"], r["w"], r["h"], r["sx"], r["sy"]))
    return dst_hits, src_hits, scanned, sites, unfolded, surfaced


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ef", type=int, action="append", help="restrict to these effect ids")
    args = ap.parse_args(argv)

    dst, src, scanned, sites, unfolded, surfaced = analyse(args.ef, verbose=bool(args.ef))
    print()
    print("=" * 78)
    print("DR_MOVE (op 144) x THE TEXEL EDIT SURFACE")
    print("=" * 78)
    print("containers scanned            : %d" % scanned)
    print("op-144 sites                  : %d  (%d excluded, period did not fold)"
          % (sites, unfolded))
    print("editable scenery cells seen   : %d" % surfaced)
    print()
    print("DESTINATION hits -- a repaint here is OVERWRITTEN at runtime, silently:")
    if not dst:
        print("   none")
    for ef, names in sorted(dst.items()):
        print("   ef%03d  %s" % (ef, sorted(set(names))))
    print()
    print("SOURCE hits -- the repaint is READ and propagated (milder, reported separately):")
    if not src:
        print("   none")
    for ef, names in sorted(src.items()):
        print("   ef%03d  %s" % (ef, sorted(set(names))))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
