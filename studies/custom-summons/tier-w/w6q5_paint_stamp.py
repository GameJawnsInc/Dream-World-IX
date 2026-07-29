r"""TIER W rung W6q-5 cast A -- THE BULLSEYE, authored in COLOUR through the quantize lane.

`bahamut_quantize.toml` needs an RGBA painting; this script writes it.  It is the quantize-lane
counterpart of `emblem_stamp.py` (W6a), and the same provenance shape: THE ART CANNOT BE IN THE
REPO (it is painted over a decoded stock render), so what ships is this GENERATOR, which re-derives
every parameter from the user's own container and writes exactly that PNG into SCRATCH.

WHAT CAST A MUST ISOLATE (FINAL-DESIGN.md section 9.4 item 6): a shape edit *in colours the row
already carries*, so the exact-hit count is high, the census is quiet, and the QUANTIZE STEP is the
only variable between this cast and W6a's index-space brand.  Therefore:

  * both inks are SAMPLED from the exported paint render itself -- any pixel colour in that file is
    by construction the rendered colour of a live row entry, so every painted texel is an EXACT-class
    hit and the build's error census must read 0 moved-by-approximation;
  * the glyph (two concentric rings + a centre dot -- deliberately NOT W6a's ring-and-three-bars, so
    the screen names which lane drew) is placed inside the largest fully-sampled disc of part 0's
    UV island, re-derived here via the kit's own `coverage()` -- nothing touches the cutout, nothing
    lands on a never-sampled pad texel, `acknowledge_cutout_reshape` stays false;
  * the paint file's ALPHA is carried through UNTOUCHED (alpha is the cutout and it is authoritative).

CAST B (`--foreign`) is the SAME glyph at the SAME coordinates painted in colours the row CANNOT
carry -- an authored saturated magenta and orange, constants of this script and of nobody's palette.
The quantizer must therefore approximate every painted texel (nearest row entry, squared Euclidean
over the 5-bit triple), the build's census must be LOUD instead of quiet, and the screen shows what
the approximation looks like at speed.  A-vs-B isolates exactly one variable: whether the painting's
colours are representable.  (FINAL-DESIGN.md section 9.4 item 6's second cast.)

REFUSALS, not conveniences: the staged composition base must hash to the W4 cast-proven artifact
(else the sampled inks belong to some other palette and the whole "colours the row already carries"
premise is false), the paint render must be 128x128 RGBA, and both cast-A inks must clear a minimum
census count so a one-off dither colour cannot become the ink.

Run AFTER `summon-reskin build bahamut_reskin.toml` (stages the base) and
`summon-reskin export-art --ef 227 --art-lane paint --from <staged ef227>` (renders against it):

    py w6q5_paint_stamp.py

Zero Square-Enix bytes live in this file: every colour, coordinate and count is derived at run time
from the user's own install artifacts under SCRATCH.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
sys.path.insert(0, os.path.join(_REPO, "ff9mapkit"))

from ff9mapkit.summons import repaint as RP                      # noqa: E402

SCRATCH = os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format")
STAGED_BASE = r"C:\gd\SCRATCH\summon-transplant\reskin\ef227\mod\FF9_Data\SpecialEffects\ef227"
ART_DIR = os.path.join(SCRATCH, "quantize-w6q", "cast5", "art")

#: The W4 cast-proven composition base.  A HASH PREFIX, not data.
BASE_SHA8 = "7fef205f"
#: An ink must appear at least this many times inside the disc before it may be an ink.
MIN_INK_COUNT = 16
PAGE_W = PAGE_H = 128

#: CAST B's foreign inks -- AUTHORED constants, deliberately far off the spectral-mist row (which
#: lives in greens, silver-blues and near-blacks): a saturated magenta and a saturated orange.
#: Their whole job is to be unrepresentable, so the nearest-entry approximation is the cast.
FOREIGN_BRIGHT = (255, 0, 255)
FOREIGN_DARK = (255, 96, 0)


def _fail(msg: str) -> "SystemExit":
    return SystemExit("REFUSED: " + msg)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--staged", default=STAGED_BASE,
                    help="the staged W4 composition base (default: the summon-transplant staging root)")
    ap.add_argument("--art", default=ART_DIR,
                    help="the export-art --art-lane paint output dir (default: quantize-w6q/cast5/art)")
    ap.add_argument("--out", default=None,
                    help="output PNG (default: <art>/tex.part0.cast5a.png, or .cast5b.png with --foreign)")
    ap.add_argument("--foreign", action="store_true",
                    help="CAST B: paint the same glyph in the authored FOREIGN inks (magenta/orange) "
                         "so every texel must be approximated; without it, CAST A samples the row")
    a = ap.parse_args(argv)

    try:
        from PIL import Image
    except ImportError:
        raise _fail("Pillow is required (py -m pip install pillow)")

    # ---- the composition base, refused on drift --------------------------------------------------
    if not os.path.exists(a.staged):
        raise _fail("no staged base at %s -- run `summon-reskin build bahamut_reskin.toml` first" % a.staged)
    blob = open(a.staged, "rb").read()
    sha8 = hashlib.sha256(blob).hexdigest()[:8]
    if sha8 != BASE_SHA8:
        raise _fail("the staged base hashes %s, not the W4 cast-proven %s -- the sampled inks would "
                    "belong to some other palette" % (sha8, BASE_SHA8))

    paint_path = os.path.join(a.art, "tex.part0.paint.png")
    if not os.path.exists(paint_path):
        raise _fail("no paint render at %s -- run export-art --art-lane paint --from <staged>" % paint_path)
    img = Image.open(paint_path)
    if img.mode != "RGBA" or img.size != (PAGE_W, PAGE_H):
        raise _fail("paint render is %s %r, expected RGBA (128, 128)" % (img.mode, img.size))
    px = img.load()

    # ---- the island, re-derived through the kit's own instrument ---------------------------------
    cov = RP.coverage(blob, 0)
    if not cov.available:
        raise _fail("coverage unavailable on part 0: %s" % cov.reason)
    mask = cov.mask
    samp = [(x, y) for y in range(PAGE_H) for x in range(PAGE_W) if mask[y * PAGE_W + x]]
    cx = sum(p[0] for p in samp) / len(samp)
    cy = sum(p[1] for p in samp) / len(samp)
    icx, icy = int(round(cx)), int(round(cy))

    def disc_ok(r: int) -> bool:
        r2 = r * r
        for y in range(max(0, icy - r), min(PAGE_H, icy + r + 1)):
            for x in range(max(0, icx - r), min(PAGE_W, icx + r + 1)):
                if (x - icx) ** 2 + (y - icy) ** 2 <= r2:
                    if not mask[y * PAGE_W + x] or px[x, y][3] != 255:
                        return False
        return True

    r = 0
    while r < 64 and disc_ok(r + 1):
        r += 1
    if r < 12:
        raise _fail("largest fully-sampled disc is r=%d -- too small to carry a legible bullseye" % r)

    # ---- the inks: the row's own colours, by census ---------------------------------------------
    census = Counter()
    for y in range(icy - r, icy + r + 1):
        for x in range(icx - r, icx + r + 1):
            if (x - icx) ** 2 + (y - icy) ** 2 <= r * r:
                pr, pg, pb, pa = px[x, y]
                census[(pr, pg, pb)] += 1
    if a.foreign:
        # CAST B: the inks are authored constants and must NOT be colours the render carries --
        # if either one appears in the page at all, it is representable and the cast tests nothing.
        page_colours = {px[x, y][:3] for y in range(PAGE_H) for x in range(PAGE_W) if px[x, y][3] == 255}
        for ink in (FOREIGN_BRIGHT, FOREIGN_DARK):
            if ink in page_colours:
                raise _fail("foreign ink rgb%r is a colour this render already carries -- "
                            "it would quantize exactly and cast B would be cast A" % (ink,))
        ink_bright, ink_dark = FOREIGN_BRIGHT, FOREIGN_DARK
    else:
        frequent = [(c, n) for c, n in census.items() if n >= MIN_INK_COUNT]
        if len(frequent) < 2:
            raise _fail("fewer than two colours clear the %d-count census inside the disc" % MIN_INK_COUNT)

        def luma(c) -> int:
            return 2 * c[0] + 5 * c[1] + c[2]

        ink_bright = max(frequent, key=lambda cn: luma(cn[0]))[0]
        ink_dark = min(frequent, key=lambda cn: luma(cn[0]))[0]
        if ink_bright == ink_dark:
            raise _fail("bright and dark ink resolved to the same colour -- no contrast to draw with")

    # ---- the glyph: outer ring BRIGHT, middle ring DARK, centre dot BRIGHT ----------------------
    bands = (
        ("outer ring", (0.82 * r) ** 2, float(r * r), ink_bright),
        ("middle ring", (0.45 * r) ** 2, (0.58 * r) ** 2, ink_dark),
        ("centre dot", 0.0, (0.18 * r) ** 2, ink_bright),
    )
    painted = Counter()
    differ = 0
    for y in range(icy - r, icy + r + 1):
        for x in range(icx - r, icx + r + 1):
            d2 = float((x - icx) ** 2 + (y - icy) ** 2)
            for name, lo, hi, ink in bands:
                if lo <= d2 <= hi:
                    pr, pg, pb, pa = px[x, y]
                    if (pr, pg, pb) != ink:
                        differ += 1
                    px[x, y] = (ink[0], ink[1], ink[2], pa)     # alpha carried, never written
                    painted[name] += 1
                    break

    cast = "B" if a.foreign else "A"
    out = a.out or os.path.join(a.art, "tex.part0.cast5%s.png" % cast.lower())
    img.save(out)

    print("w6q5_paint_stamp -- CAST %s art written: %s" % (cast, out))
    print("  base            %s (the W4 cast-proven composition base)" % sha8)
    print("  island          %d/%d sampled; centroid (%.1f, %.1f); fully-sampled disc r=%d"
          % (len(samp), PAGE_W * PAGE_H, cx, cy, r))
    print("  ink bright      rgb%r  (census %d inside the disc)" % (ink_bright, census[ink_bright]))
    print("  ink dark        rgb%r  (census %d inside the disc)" % (ink_dark, census[ink_dark]))
    for name, lo, hi, ink in bands:
        print("  %-12s %5d texels" % (name, painted[name]))
    print("  total painted   %d texels (%d differ from what the render already showed;"
          % (sum(painted.values()), differ))
    print("                  the rest hit THE INCUMBENT LOCK and must move 0 bytes)")
    if a.foreign:
        print("  EXPECTED CENSUS neither ink exists anywhere in the render == EVERY painted texel")
        print("                  is APPROXIMATED (nearest row entry); the census must be LOUD and")
        print("                  the previews show what the magenta and orange became.")
    else:
        print("  EXPECTED CENSUS both inks are sampled render colours == EXACT-class hits;")
        print("                  the build's moved-by-approximation count must be 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
