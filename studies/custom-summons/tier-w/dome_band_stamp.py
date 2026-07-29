r"""TIER W rung W6b-2 CAST B -- THE DOME BANDS: the first depth-BEARING edit on a channel-G cell.

`phoenix_dome.toml` needs an indexed PNG; this script writes it.  The vehicle is THE DOME --
ef211 `cell.s0.x704_y384`, the rolling-fire dome's cell: **readerless** (0 of 8,192 halfwords
sampled by any model, which is exactly why W6b-1's census refused it), **proven drawn** (the cast
ladder's zero-write stripes banded the fire through it), and **8 bpp only by CHANNEL G** -- the
container's own `so` binding on the column's page, re-read at page granularity by the W6b-2 kit
integration.  No zero-write can test a depth (zeroing is depth-invariant); THESE bands carry INK,
so what the screen shows judges the depth claim itself:

  * clean bright bands banding the rolling fire  ->  the channel-G 8 bpp IS the draw depth
    (REGISTRATION-IS-A-DRAW-ENOUGH holds where the surface is already proven live);
  * bands present but pin-striped / textured     ->  the draw reads these bytes at 4 bpp
    (each ink byte splits into two nibble texels -- the ef446 "jittery" signature one level down);
  * bands in one solid WRONG colour              ->  a 15 bpp read (byte pairs become direct words
    -- the cast-15 "bumper strip" family's mirror image).

THE FIGURE IS TRANSLATION-INVARIANT ON PURPOSE (bands, never a shape): this cell has no declared
UVs, so the offline flatness screen that licenses a SHAPE cannot clear it -- the record forbids
attempting one here (`W6b2-ATTRIBUTION.md` section 8.2).  Four 12-row bands, spacing 32, are also
deliberately NOT the census probe's thin 6-row stripes, so the screen names which instrument drew.

The ink is DERIVED, never chosen: the brightest entry of the display palette the export rendered
under (`pal.s0.x0_y247.e256`, the same CLUT the upper half's cast-proven wheel used), taken from
the exported PNG's own embedded palette.  Zero Square-Enix bytes live in this file; the art stays
in SCRATCH.

Run AFTER `summon-reskin export-art --ef 211 --out <art dir>`:

    py dome_band_stamp.py
"""
from __future__ import annotations

import argparse
import os
import sys

SCRATCH = os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format")
ART_DIR = os.path.join(SCRATCH, "repaint-w6b", "ef211-dome", "art")
CELL = "cell.s0.x704_y384"

#: Four bands x 12 rows at spacing 32 -- bold (2x the census probe's 6-row duty) and periodic.
BAND_ROWS = 12
BAND_SPACING = 32
BAND_STARTS = (16, 48, 80, 112)
PAGE_W = PAGE_H = 128


def _fail(msg: str) -> "SystemExit":
    return SystemExit("REFUSED: " + msg)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--art", default=ART_DIR)
    ap.add_argument("--out", default=None, help="default: <art>/%s.domebands.png" % CELL)
    a = ap.parse_args(argv)

    try:
        from PIL import Image
    except ImportError:
        raise _fail("Pillow is required (py -m pip install pillow)")

    src = os.path.join(a.art, CELL + ".png")
    if not os.path.exists(src):
        raise _fail("no exported cell at %s -- run summon-reskin export-art --ef 211 first" % src)
    img = Image.open(src)
    if img.mode != "P" or img.size != (PAGE_W, PAGE_H):
        raise _fail("exported cell is %s %r, expected an indexed P-mode (128, 128) PNG "
                    "(the EXACT lane is the format of record for a depth experiment -- "
                    "no quantizer between the ink and the bytes)" % (img.mode, img.size))

    pal = img.getpalette()
    if not pal:
        raise _fail("the exported PNG carries no palette to derive an ink from")
    lumas = [(2 * pal[3 * i] + 5 * pal[3 * i + 1] + pal[3 * i + 2], i) for i in range(256)]
    ink_luma, ink = max(lumas)
    if ink == 0:
        raise _fail("the brightest entry is index 0 (the transparent entry) -- refusing to ink "
                    "with the cutout")

    px = img.load()
    stamped = holes = 0
    for y0 in BAND_STARTS:
        for y in range(y0, min(y0 + BAND_ROWS, PAGE_H)):
            for x in range(PAGE_W):
                # THE CUTOUT STAYS THE CUTOUT: an index-0 texel is the model's silhouette, and
                # inking it would trip THE CUTOUT LAW (rightly).  A few pinholes in a 12-row band
                # are invisible at speed; a reshaped silhouette is a second variable.
                if px[x, y] == 0:
                    holes += 1
                    continue
                if px[x, y] != ink:
                    stamped += 1
                px[x, y] = ink

    out = a.out or os.path.join(a.art, CELL + ".domebands.png")
    img.save(out)

    print("dome_band_stamp -- CAST art written: %s" % out)
    print("  cell            %s (THE DOME -- readerless, drawn, 8bpp by CHANNEL G alone)" % CELL)
    print("  ink             index %d (the display palette's max-luminance entry, luma %d)"
          % (ink, ink_luma))
    print("  ink colour      rgb(%d, %d, %d) as rendered by the export"
          % (pal[3 * ink], pal[3 * ink + 1], pal[3 * ink + 2]))
    print("  bands           %d x %d rows at spacing %d (starts %r)"
          % (len(BAND_STARTS), BAND_ROWS, BAND_SPACING, list(BAND_STARTS)))
    print("  texels inked    %d changed of %d band texels (%d cutout holes SKIPPED -- the "
          "silhouette is not this cast's variable)"
          % (stamped, len(BAND_STARTS) * BAND_ROWS * PAGE_W, holes))
    print("  VERDICT KEY     clean bright bands = 8bpp CONFIRMED (registration-is-a-draw-enough);")
    print("                  pin-striped bands = a 4bpp read; solid wrong colour = a 15bpp read.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
