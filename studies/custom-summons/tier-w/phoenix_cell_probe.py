r"""TIER W rung W6b-1 -- CAST 1c: THE STRIPED CELL CENSUS.  Which cells does the on-screen fire read?

WHY THIS PROBE EXISTS.  Casts 1a (ink wheel) and 1b (punch wheel) both reached the FILE -- the live
container's sha was verified after each deploy -- and neither figure appears anywhere in the cast
(owner + full-resolution frame sweeps agree, both videos).  A punched annulus covering ~25% of the
texture cannot hide, so the conclusion is not legibility: **cell (704,256) is not what the visible
fire samples.**  That falsifies an attribution the census could not test offline, and names a law:

    AN `so` READER IS A BINDING, NOT A DRAW.  The so-record proves a model CAN sample a cell; it
    does not prove the model is ever drawn, or visible.  W5's magenta proof went through the
    PALETTE -- shared by every binding on CLUT (0,247) -- so it proved the palette path, never any
    one cell's.  The on-screen fire is very plausibly drawn by the id-3 program's own primitives
    sampling the DEPTH-UNKNOWN cells (448/512 columns), which is recon open question Q1 exactly.

THE INSTRUMENT.  Zero-writing is DEPTH-INVARIANT: a 0x00 byte is index 0 twice at 4bpp, index 0 at
8bpp, and half of the cutout word 0x0000 at 15bpp -- at every depth a zeroed texel is the
transparent/black-cutout value.  So a probe may lawfully mark EVERY cell, including the ten the
edit lane refuses as depth-unknown -- this is a diagnostic instrument outside the edit lane, and
what it writes is the one value whose meaning does not depend on the answer it is measuring.

THE ENCODING.  Cell #k (1-based, sorted by (x, y) then writer tag) gets **k evenly-spaced
horizontal zero stripes**, each STRIPE_ROWS byte-rows of 128 bytes.  A surface sampling cell #k
shows k dark bands per texture repeat -- scrolling moves the bands, never their count.  Count the
bands in whatever fire goes gappy and read off the cell.

THE LEDGER.  This probe snapshots whatever the mod folder holds (cast 1b's punch container) into
its own root before writing, and emits `revert_probe.py` restoring it byte-for-byte.  One file
written, one file restored; nothing else is touched.

Provenance: everything is derived from the user's own container at run time; the probe container
is SE-derived and stays in SCRATCH / the install.  Zero SE bytes here.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "ff9mapkit"))

from ff9mapkit.summons import reskin as RS                       # noqa: E402
from ff9mapkit.summons import container as EC                    # noqa: E402

EFFECT = 211
DEFAULT_ROOT = r"C:\gd\SCRATCH\summon-format\repaint-w6b\ef211-cellprobe"
DEFAULT_CORPUS = r"C:\gd\SCRATCH\summon-format\ef211.bytes"
GAME_OVERRIDE = (r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"
                 r"\FF9CustomMap\FF9_Data\SpecialEffects\ef211")
STRIPE_ROWS = 6                     # byte-rows per stripe (128 B each); bold enough to read on video
ROW_BYTES = 128
CELL_ROWS = 128


def striped(cell_bytes: bytes, k: int) -> bytes:
    """``k`` evenly-spaced zero stripes of ``STRIPE_ROWS`` byte-rows across a 0x4000-byte cell."""
    out = bytearray(cell_bytes)
    for s in range(k):
        centre = int((s + 0.5) * CELL_ROWS / k)
        top = max(0, min(CELL_ROWS - STRIPE_ROWS, centre - STRIPE_ROWS // 2))
        for r in range(top, top + STRIPE_ROWS):
            out[r * ROW_BYTES:(r + 1) * ROW_BYTES] = b"\x00" * ROW_BYTES
    return bytes(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from", dest="from_path", default=DEFAULT_CORPUS,
                    help="the STOCK container to stripe (default the corpus ef211)")
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--deploy", action="store_true",
                    help="snapshot the live override and write the probe container over it")
    ap.add_argument("--only", default=None, metavar="CELL",
                    help="stripe ONLY this cell (e.g. cell.s0.x576_y384), keeping its canonical "
                         "stripe count from the full-census legend -- the surgical confirm: exactly "
                         "the surfaces reading this cell band, everything else is its own control")
    a = ap.parse_args(argv)

    stock = Path(a.from_path).read_bytes()
    cells = RS.page_cells(stock)
    order = sorted(cells.values(), key=lambda pc: (pc.x, pc.y, pc.tag))
    blob = bytearray(stock)
    legend = []
    for i, pc in enumerate(order):
        k = i + 1
        if a.only is not None and pc.name != a.only:
            legend.append("  %2d           -> %-22s  UNTOUCHED (control)" % (k, pc.name))
            continue
        blob[pc.off:pc.off + pc.nbytes] = striped(bytes(stock[pc.off:pc.off + pc.nbytes]), k)
        legend.append("  %2d stripe(s) -> %-22s  (%s @%#x)" % (k, pc.name, pc.kind, pc.off))
    if a.only is not None and not any("stripe(s)" in l for l in legend):
        raise SystemExit("--only %r matches no cell; the census names are:\n%s"
                         % (a.only, "\n".join("  " + pc.name for pc in order)))
    probe = bytes(blob)
    EC.parse_header(probe, strict=True)                          # the probe must still parse

    root = Path(a.root)
    root.mkdir(parents=True, exist_ok=True)
    out = root / "ef211.cellprobe"
    out.write_bytes(probe)
    sha = hashlib.sha256(probe).hexdigest()
    print("THE STRIPED CELL CENSUS -- ef%03d, %d cells marked" % (EFFECT, len(order)))
    print("\n".join(legend))
    print("probe container  %d B  sha256 %s" % (len(probe), sha))
    print("staged           %s" % out)

    if a.deploy:
        live = Path(GAME_OVERRIDE)
        pre = root / "pre.ef211"
        if live.exists():
            pre.write_bytes(live.read_bytes())
            print("snapshot         %s (the pre-probe override, %d B)" % (pre, pre.stat().st_size))
        else:
            pre_note = root / "pre.ABSENT"
            pre_note.write_text("no override existed before the probe; revert = delete\n")
            print("snapshot         (no prior override -- revert deletes)")
        live.parent.mkdir(parents=True, exist_ok=True)
        live.write_bytes(probe)
        rb = hashlib.sha256(live.read_bytes()).hexdigest()
        print("DEPLOYED         %s  (readback sha %s: %s)"
              % (live, rb[:16], "OK" if rb == sha else "*** MISMATCH ***"))
        rv = root / "revert_probe.py"
        rv.write_text(
            "import pathlib\n"
            "live = pathlib.Path(%r)\n"
            "pre = pathlib.Path(%r)\n"
            "if pre.exists():\n"
            "    live.write_bytes(pre.read_bytes()); print('restored', live)\n"
            "else:\n"
            "    live.unlink(missing_ok=True); print('deleted', live)\n" % (str(live), str(pre)))
        print("revert with      py %s" % rv)
    return 0


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
