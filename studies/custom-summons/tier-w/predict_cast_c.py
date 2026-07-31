r"""TIER W rung W6b-3 CAST C -- THE OFFLINE PREDICTION.  What the patched cell LOOKS LIKE at each of
the three candidate depths, rendered from THE ACTUAL PATCHED BYTES.

    py predict_cast_c.py                       # reads the built stage-c container
    py predict_cast_c.py --container <path>    # or any container to render

★ THIS IS PART OF THE INSTRUMENT, NOT DECORATION, AND THE REASON IS THE CAST-B FAILURE.  Cast B's
verdict key was a TABLE somebody wrote -- "clean bands / pin-striped bands / one solid wrong hue" --
and two of its three rows were arithmetically impossible for the ink byte it shipped.  Nobody caught
it, because a table cannot be looked at.  A RENDER can: had cast B's three hypotheses been rendered
from its own patched bytes, the 4bpp panel would have shown solid bands and the 15bpp panel white
ones, and the cast would have been redesigned before it was deployed instead of after.

So this script renders the SAME 16,384 bytes four ways and puts them side by side.  Compare the
owner's video to the SHEET; never to a memory of the table.

THE FOUR READINGS, all of the identical byte block at page offset 0x25668:

  8bpp                 128 x 128, each byte a palette index into the cell's own CLUT row.
  4bpp, CLUT base 0    256 x 128, each byte TWO texels (low nibble first -- `RP.unpack4`'s MEASURED
                       order), indexing entries 0..15.  This is what an unchanged CLUT pointer selects
                       and is therefore the natural 4bpp hypothesis.
  4bpp, base-240 win   256 x 128, the same nibbles against entries 240..255.  THE CONTRIVED RESIDUE
                       the cast-B refutation could not exclude: it is the only 16-entry window whose
                       index 15 is cast B's own ink.  Rendered because "not excluded" is not "not
                       looked at" -- and its own tell is visible here, in the CUTOUT.
  15bpp                64 x 128, byte PAIRS as direct BGR555 words.  No palette is involved.

TWO ROWS ON THE SHEET, because a texture is not a screen:

  row 1  THE TEXTURE as decoded, over a checkerboard so TRANSPARENT reads as transparent.
  row 2  THE SAME PANELS COMPOSITED ADDITIVELY over a dark backdrop of the luma the cast-B video
         measured under the bands (40-70), which is what the engine's blend actually does.  This is
         the row that answers "will the owner be able to tell these apart".

ORIENTATION.  Panels are drawn in TEXTURE order (row 0 at the top).  Cast B established the cell is
carried V-FLIPPED on the model -- the javelin is tip-down in the texture, so the authored row order
6/32/58/83/109 appeared on screen as 109/83/58/32/6.  A `--vflip` row is emitted too, so the sheet can
be held against the video without doing the flip in one's head.

PROVENANCE.  Everything is derived from the user's own container at run time.  The renders are
SE-derived and stay in SCRATCH; zero SE bytes live in this file.
"""
from __future__ import annotations

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "ff9mapkit"))
sys.path.insert(0, _HERE)

from ff9mapkit.summons import repaint as RP                       # noqa: E402
from ff9mapkit.summons import texture as KT                       # noqa: E402
from odin_band_stamp import (ACK_ARRAY_DEPTH, EFFECT, ROOT,       # noqa: E402
                             VERDICT_CELL, pin_source)

DEFAULT_CONTAINER = os.path.join(ROOT, "stage-c", "mod", "FF9_Data", "SpecialEffects",
                                 "ef%03d" % EFFECT)
DEFAULT_OUT = os.path.join(ROOT, "predict-c")
#: the backdrop the composite row blends over.  The cast-B measurement binned the ink's local backdrop
#: and found EVERY inked pixel sat on >= 40 luma, with the darkest available bin 40-70 -- so 55 is that
#: bin's centre and is the DIMMEST honest backdrop, i.e. the one most favourable to telling the panels
#: apart being hard.  A brighter backdrop only makes 8bpp clip more, which is the failure cast B hit.
BACKDROP = (55, 55, 55)
SCALE = 3


def _fail(msg):
    return SystemExit("REFUSED: " + msg)


def rgba_rows(px: bytes, words, bpp: int, w: int, h: int, clut_base: int = 0):
    """``h`` rows of ``w`` RGBA tuples -- ONE decoder, parameterised by depth, so the three panels
    cannot drift apart the way three hand-written renderers would."""
    out = []
    if bpp == 8:
        for y in range(h):
            row = px[y * w:(y + 1) * w]
            out.append([KT.bgr555_rgba(words[b]) for b in row])
    elif bpp == 4:
        idx = RP.unpack4(px)                       # measured order: out[2i] = raw[i] & 0x0F
        for y in range(h):
            row = idx[y * w:(y + 1) * w]
            out.append([KT.bgr555_rgba(words[clut_base + n]) if clut_base + n < len(words)
                        else (255, 0, 255, 255) for n in row])
    elif bpp == 15:
        for y in range(h):
            base = y * w * 2
            out.append([KT.bgr555_rgba(px[base + 2 * x] | (px[base + 2 * x + 1] << 8))
                        for x in range(w)])
    else:
        raise _fail("no decoder for %d bpp" % bpp)
    return out


def stats(rows):
    """Opacity + a coarse hue-family census -- the two axes the cast-B refutation actually judged on,
    so each panel carries its own numbers instead of an adjective."""
    n = op = 0
    fam = {"red": 0, "green": 0, "blue": 0, "grey/other": 0}
    lum = 0.0
    for row in rows:
        for r, g, b, a in row:
            n += 1
            if not a:
                continue
            op += 1
            lum += 0.299 * r + 0.587 * g + 0.114 * b
            mx = max(r, g, b)
            if mx < 24:
                fam["grey/other"] += 1
            elif r == mx and r > g and r > b:
                fam["red"] += 1
            elif g == mx and g >= r and g > b:
                fam["green"] += 1
            elif b == mx and b >= r and b >= g:
                fam["blue"] += 1
            else:
                fam["grey/other"] += 1
    return {"texels": n, "opaque": op, "opaque_pct": 100.0 * op / n if n else 0.0,
            "mean_luma": (lum / op) if op else 0.0,
            "families": {k: (100.0 * v / op if op else 0.0) for k, v in fam.items()}}


def panel(rows, w, h, scale, composite=False, vflip=False):
    """One decoded page -> an RGB image.  ``composite`` blends ADDITIVELY over :data:`BACKDROP`, which
    is what the engine does; otherwise transparency is drawn as a checkerboard so it reads AS
    transparency rather than as black (a black band and a hole are the same picture, and on cast C
    telling them apart is the entire measurement)."""
    from PIL import Image

    im = Image.new("RGB", (w, h))
    put = im.load()
    src = rows[::-1] if vflip else rows
    for y in range(h):
        for x in range(w):
            r, g, b, a = src[y][x]
            if a:
                if composite:
                    put[x, y] = (min(255, r + BACKDROP[0]), min(255, g + BACKDROP[1]),
                                 min(255, b + BACKDROP[2]))
                else:
                    put[x, y] = (r, g, b)
            elif composite:
                put[x, y] = BACKDROP
            else:
                v = 64 if ((x // 4) + (y // 4)) % 2 else 40
                put[x, y] = (v, v, v)
    # NEAREST on purpose: a smooth resample would average a 1-texel transparent comb into a uniform
    # dim wash and hide the exact structure the 4bpp hypothesis is recognised by.
    return im.resize((w * scale, h * scale), Image.NEAREST)


def label(img, lines, pad=6):
    from PIL import Image, ImageDraw

    head = 13 * len(lines) + 2 * pad
    out = Image.new("RGB", (img.width, img.height + head), (18, 18, 22))
    d = ImageDraw.Draw(out)
    for i, t in enumerate(lines):
        d.text((pad, pad + 13 * i), t, fill=(235, 235, 240) if not i else (170, 175, 190))
    out.paste(img, (0, head))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--container", default=DEFAULT_CONTAINER,
                    help="the PATCHED container to render (default: the stage-c build)")
    ap.add_argument("--stock", default=os.path.join(os.path.dirname(ROOT), "..",
                                                    "ef%03d.bytes" % EFFECT),
                    help="the STOCK corpus, used only to run the SOURCE PIN and to report the delta")
    ap.add_argument("--cell", default=VERDICT_CELL)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--scale", type=int, default=SCALE)
    a = ap.parse_args(argv)

    from PIL import Image

    stock_path = os.path.abspath(a.stock)
    with open(stock_path, "rb") as fh:
        stock = fh.read()
    # THE SOURCE PIN, on the STOCK side -- the patched container is not the thing the module constants
    # were measured on and cannot be pinned by name, but the corpus it was derived FROM can be.
    pin = pin_source(stock, stock_path)
    if not os.path.exists(a.container):
        raise _fail("no patched container at %s -- run `summon-reskin build` into stage-c first"
                    % a.container)
    with open(a.container, "rb") as fh:
        blob = fh.read()
    if len(blob) != len(stock):
        raise _fail("%s is %d B and the stock corpus is %d B -- these are not the same container"
                    % (a.container, len(blob), len(stock)))

    # THE PAGE GEOMETRY COMES FROM THE STOCK HEADERS, and the PIXELS from the patched file.  Resolving
    # the page against the patched container would let a corrupted header pick a different span and
    # then render it happily; resolving against stock and reading the same span is the honest pairing.
    page = RP.texel_page(stock, a.cell, EFFECT,
                         allow_array_depth=ACK_ARRAY_DEPTH.get(a.cell, False))
    words = RP.palette_words(stock, page)
    off, nb = page.page_offset, page.page_bytes
    px = blob[off:off + nb]
    stock_px = stock[off:off + nb]
    delta = sum(1 for x, y in zip(px, stock_px) if x != y)
    ink_hist = {}
    for i, (x, y) in enumerate(zip(px, stock_px)):
        if x != y:
            ink_hist[x] = ink_hist.get(x, 0) + 1

    os.makedirs(a.out, exist_ok=True)
    reads = [
        ("8bpp", 8, 128, 128, 0,
         "8 bpp -- CHANNEL A'S STATED DEPTH",
         "byte = palette index into %s" % page.palette_name),
        ("4bpp-clut0", 4, 256, 128, 0,
         "4 bpp, NATURAL CLUT BASE 0",
         "byte = two texels (low nibble first) into entries 0..15"),
        ("4bpp-clut240", 4, 256, 128, 240,
         "4 bpp, CONTRIVED base-240 WINDOW",
         "the residue cast B could not exclude: entries 240..255"),
        ("15bpp", 15, 64, 128, 0,
         "15 bpp -- DIRECT COLOUR",
         "byte PAIRS become BGR555 words; no palette at all"),
    ]

    panels, report = [], []
    for tag, bpp, w, h, base, title, sub in reads:
        rows = rgba_rows(px, words, bpp, w, h, base)
        st = stats(rows)
        p = os.path.join(a.out, "predict-c.%s.%s.png" % (a.cell, tag))
        panel(rows, w, h, a.scale).save(p)
        panels.append((tag, title, sub, rows, w, h, st))
        report.append((tag, p, st))

    # ---- THE SHEET: three rows -- texture, v-flipped texture, additive composite ------------------
    pad, gap = 10, 14
    cell_w = max(w for _, _, _, _, w, _, _ in panels) * a.scale
    cell_h = 128 * a.scale
    head = 68
    band = cell_h + 78
    sheet = Image.new("RGB", (pad * 2 + len(panels) * cell_w + (len(panels) - 1) * gap,
                              head + 3 * band + pad), (14, 14, 18))
    from PIL import ImageDraw

    d = ImageDraw.Draw(sheet)
    d.text((pad, 8), "CAST C -- OFFLINE PREDICTION.  ef%03d  %s  page %#x, %d bytes, rendered from "
                     "the PATCHED container." % (EFFECT, a.cell, off, nb), fill=(245, 245, 250))
    d.text((pad, 24), "%d of %d bytes differ from stock; the ink byte histogram of the delta is %s.  "
                      "Compare the VIDEO to this sheet."
           % (delta, nb, ", ".join("0x%02X x%d" % kv for kv in sorted(ink_hist.items()))),
           fill=(165, 170, 185))
    d.text((pad, 40), "ROW 1 texture as decoded (checkerboard = TRANSPARENT)   |   ROW 2 the same, "
                      "V-FLIPPED as the model carries it   |   ROW 3 composited ADDITIVELY over "
                      "rgb%s, which is what the screen does" % (BACKDROP,), fill=(165, 170, 185))
    for i, (tag, title, sub, rows, w, h, st) in enumerate(panels):
        x = pad + i * (cell_w + gap)
        for j, (vf, comp) in enumerate(((False, False), (True, False), (False, True))):
            y = head + j * band
            im = panel(rows, w, h, a.scale, composite=comp, vflip=vf)
            sheet.paste(im, (x, y + 62))
            if j == 0:
                d.text((x, y + 4), title, fill=(255, 235, 150))
                d.text((x, y + 18), sub, fill=(160, 165, 180))
                d.text((x, y + 32), "%d x %d texels   opaque %.1f%%   mean luma %.0f"
                       % (w, h, st["opaque_pct"], st["mean_luma"]), fill=(160, 165, 180))
                fam = st["families"]
                d.text((x, y + 46), "red %.0f%%  green %.0f%%  blue %.0f%%  grey %.0f%%"
                       % (fam["red"], fam["green"], fam["blue"], fam["grey/other"]),
                       fill=(160, 165, 180))
            else:
                d.text((x, y + 40), "V-FLIPPED (screen order)" if vf else
                       "ADDITIVE over rgb%s" % (BACKDROP,), fill=(200, 205, 220))
    sheet_path = os.path.join(a.out, "predict-c.%s.SHEET.png" % a.cell)
    sheet.save(sheet_path)

    print("predict_cast_c -- ef%03d %s" % (EFFECT, a.cell))
    print("  %s" % pin)
    print("  patched        %s" % a.container)
    print("  page           %#x  %d bytes  (%d differ from stock; delta ink %s)"
          % (off, nb, delta, ", ".join("0x%02X x%d" % kv for kv in sorted(ink_hist.items()))))
    print("")
    for tag, p, st in report:
        fam = st["families"]
        print("  %-13s opaque %5.1f%%  mean luma %5.1f  red %5.1f%% green %5.1f%% blue %5.1f%%"
              % (tag, st["opaque_pct"], st["mean_luma"], fam["red"], fam["green"], fam["blue"]))
        print("                %s" % p)
    print("")
    print("  SHEET          %s" % sheet_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
