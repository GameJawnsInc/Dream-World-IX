r"""TIER W rung W6a -- THE EMBLEM GENERATOR.  The committed half of the texel proof.

    py emblem_stamp.py                      # export ef227's art, stamp the brand, report the numbers
    py emblem_stamp.py --root DIR           # stage somewhere else (still local-only guarded)
    py emblem_stamp.py --from ef227.bytes   # read a corpus container instead of the install

WHAT THIS FILE IS, AND WHY IT IS THE THING THAT SHIPS
------------------------------------------------------
The artifact this rung proves with is a repainted 128x128 texture page.  That page is **decoded
Square-Enix content** -- it is not committable, at any resolution, under any name.  So the proof
ships as a GENERATOR: this script reads the user's own install, re-derives every parameter of the
brand from the container in front of it, stamps the glyph in INDEX space, and writes the edited PNG
into SCRATCH.  ``bahamut_emblem.toml`` then points at that PNG.  Nothing between here and the cast
carries a stock byte; re-running this on a fresh machine reproduces the same art from that machine's
own bytes.

That is the same posture the tier has used since W1 (offsets, counts and hashes are committable;
decoded dumps are not) -- applied to the one lane where the AUTHORED artifact is itself derived from
stock pixels.

WHY AN EMBLEM AND NOT "A DIFFERENT FLAME PATTERN"
-------------------------------------------------
``summon-reskin``'s CLUT lever (lever #1) is structurally a per-index colour FUNCTION: it can rotate
a hue, it can never move a texel from one index to another, so it cannot change a shape, an edge or
a silhouette.  A soft pattern change on additively-composited flame is therefore a weak
discriminator -- a sceptical observer can attribute it to a palette shift, and W5's own ADDITIVE-
COMPOSITING COROLLARY says the blend washes flame cores toward white anyway.  **A hard-edged
geometric brand on an opaque hide cannot be produced by any colour map at all.**  So the glyph is a
stroked ring with three radial bars, on ef227 part 0 -- the violet wing membrane, 468 faces and the
largest sampled island of the six pages.

EVERY PARAMETER IS DERIVED, NOT TYPED
--------------------------------------
* **the ink and the edge indices** are chosen from the indices the geometry actually SAMPLES, by
  maximising ``min(luma_stock, luma_composed)`` (and minimising ``max(...)`` for the outline).  Both
  therefore read under the stock violet palette AND under the W4 spectral-mist palette the cast will
  actually run -- and because both are already-live entries of the row, the emblem needs **zero CLUT
  bytes**.  The "composed" palette is REBUILT from ``bahamut_reskin.toml`` rather than read out of
  the live install: a generator that reads a mod folder would reproduce whatever happened to be
  deployed that day instead of what its own sibling spec says.
* **the placement** is the centroid of the sampled island, and the radius is the largest disc whose
  whole perimeter is inside that island.  The coverage mask comes from the container's own uv pools
  (:func:`ff9mapkit.summons.repaint.coverage`), so the glyph is guaranteed to land on geometry --
  which is also what makes ``dead-pad bytes moved`` and ``index-0 cutout flips`` come out at zero
  instead of being asserted.

PROVENANCE
----------
No stock byte run appears in this file (the tier's byte-literal scan covers it).  The install is read
at run time under the kit's sha256 drift guard; every destination goes through
:func:`ff9mapkit.summons.export.assert_local_only`, which refuses a git checkout, a
``StreamingAssets`` tree and the resolved install with no ``--force``.
"""
from __future__ import annotations

import argparse
import math
import os
import struct
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                              # noqa: E402  (sets up sys.path)
from ff9mapkit.summons import export as EX                       # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402
from ff9mapkit.summons import texture as KT                      # noqa: E402

#: THE PROOF'S OWN STAGING ROOT.  ``bahamut_emblem.toml``'s ``source`` is an absolute path into
#: ``<root>/art``; re-point one and re-point the other, or the build refuses with "no such source
#: image" rather than silently packing yesterday's art.
DEFAULT_ROOT = os.environ.get("FF9_REPAINT_W6_ROOT",
                              r"C:\gd\SCRATCH\summon-format\repaint-w6\ef227")

#: the sibling CLUT spec whose patched palette the ink/edge choice has to read under.  ABSOLUTE for
#: the same reason ``reskin.DEFAULT_ORTH_SPECS`` is: a relative name resolves against the SPEC's own
#: directory, and this one must resolve to the study's reference toml from wherever it was invoked.
RESKIN_SPEC = os.path.join(_HERE, "bahamut_reskin.toml")

#: which effect, which part.  ef227 part 0 is the wing membrane: the largest sampled island in the
#: package (11,563 of 16,384 texels) and the surface the owner has already judged twice.
EFFECT = 227
PART = 0

#: THE GLYPH, in units of the derived radius.  A stroked ring at 0.80 R, three radial bars inside it,
#: and a dark outline 1.4 texels wide outside the stroke so the brand reads against BOTH palettes
#: without depending on either one's local contrast.
RING_R = 0.80
RING_HALF_WIDTH = 2.2
EDGE_HALF_WIDTH = 3.6
BARS = 3
BAR_DUTY = 0.90


def _luma(word: int) -> float:
    """Rec.601 luma of one BGR555 palette word, through the kit's own decoder."""
    r, g, b, _a = KT.bgr555_rgba(word)
    return 0.299 * r + 0.587 * g + 0.114 * b


def composed_palette(stock: bytes, page, reskin_spec: str = RESKIN_SPEC) -> Tuple[int, ...]:
    """The CLUT row this page will index into ONCE THE CAST RUNS -- rebuilt from the sibling spec.

    Deliberately NO fallback to the stock row: an unreadable sibling RAISES.  A generator that
    quietly substituted the stock palette would pick an ink chosen for high contrast under a palette
    the cast never shows, and the resulting glyph could be invisible in game with nothing anywhere
    saying why -- the exact silent failure this rung's whole gate stack is shaped against.
    """
    b = RS.build(RS.load_spec(reskin_spec), reskin_spec, blob=stock)
    return struct.unpack_from("<%dH" % page.clut_entries, b.patched, page.clut_offset)


def choose_ink(px: Sequence[int], mask: Sequence[int], stock_words: Sequence[int],
               live_words: Sequence[int], zeros: Sequence[int]) -> Tuple[int, int, List[int]]:
    """``(ink index, edge index, the sampled index set)``.

    The candidate set is the indices the GEOMETRY SAMPLES, minus every transparent entry: an ink
    drawn from the whole 256-entry row could be a colour that appears nowhere on this page, and an
    ink that is the cutout entry would punch a hole instead of painting a brand.
    """
    zs = set(zeros)
    live = sorted({px[i] for i in range(len(mask)) if mask[i]} - zs)
    if not live:                                                 # pragma: no cover - stock has 255
        raise SystemExit("no sampled, non-transparent index on this page -- nothing to ink with")
    ink = max(live, key=lambda i: min(_luma(stock_words[i]), _luma(live_words[i])))
    edge = min(live, key=lambda i: max(_luma(stock_words[i]), _luma(live_words[i])))
    return ink, edge, live


def island_centre(mask: Sequence[int], w: int, h: int) -> Tuple[float, float, int]:
    """``(cx, cy, r)`` -- the sampled island's centroid and the largest disc fully inside it.

    The radius search walks OUTWARD and stops at the first perimeter that leaves the island, so the
    disc is contiguous rather than the largest radius that happens to work; a glyph drawn on a
    non-contiguous "island" would be split across two pieces of geometry.
    """
    xs = [i % w for i in range(len(mask)) if mask[i]]
    ys = [i // w for i in range(len(mask)) if mask[i]]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    r = 0
    for rad in range(4, min(w, h) // 2):
        ok = True
        for a in range(80):
            th = a / 40.0 * math.pi
            px_, py_ = int(cx + rad * math.cos(th)), int(cy + rad * math.sin(th))
            if not (0 <= px_ < w and 0 <= py_ < h) or not mask[py_ * w + px_]:
                ok = False
                break
        if not ok:
            break
        r = rad
    return cx, cy, r


def stamp(px: Sequence[int], mask: Sequence[int], w: int, h: int, cx: float, cy: float, r: int,
          ink: int, edge: int) -> Tuple[bytearray, int]:
    """The brand, written ONLY where the coverage mask says a face samples the texel.

    That single guard is what makes the two hard numbers come out at zero: nothing lands in the dead
    pad (so no byte of the edit is inert), and nothing lands on a transparent texel (so the
    silhouette cannot move).  Both are MEASURED afterwards by the caller rather than trusted here.
    """
    out = bytearray(px)
    n = 0
    for y in range(h):
        for x in range(w):
            i = y * w + x
            if not mask[i]:
                continue
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy)
            th = math.atan2(dy, dx)
            on_ring = abs(d - r * RING_R) <= RING_HALF_WIDTH
            on_bar = d <= r * RING_R and abs(((th * BARS / math.pi) % 2.0) - 1.0) > BAR_DUTY
            on_edge = abs(d - r * RING_R) <= EDGE_HALF_WIDTH and not on_ring
            if on_ring or on_bar:
                out[i] = ink
                n += 1
            elif on_edge:
                out[i] = edge
                n += 1
    return out, n


def generate(effect: int = EFFECT, part: int = PART, root: Optional[str] = None,
             from_path: Optional[str] = None, game=None, reskin_spec: str = RESKIN_SPEC,
             export: bool = True) -> Dict[str, object]:
    """Export the effect's art, stamp part ``part``, and return every number the spec quotes."""
    if from_path:
        stock = Path(from_path).read_bytes()
        source = str(from_path)
    else:
        stock, source = RS.R.read_stock_effect(effect, game)

    root = Path(EX.assert_local_only(root or DEFAULT_ROOT))
    art = root / "art"
    if export:
        man = RP.export_art(stock, effect, art, source=source, lane="indexed")
        art = Path(man["out_dir"])

    pages = RP.creature_texel_pages(stock)
    page = next(p for p in pages if p.index == part)
    w, h = page.wh
    px = stock[page.page_offset:page.page_offset + page.page_bytes]
    stock_words = RP.palette_words(stock, page)
    zeros = RP.transparent_indices(stock_words)

    cov = RP.coverage(stock, part)
    if not cov.available:                                        # pragma: no cover - geom drift
        raise SystemExit("coverage UNAVAILABLE on ef%03d part %d (%s) -- the placement constraint "
                         "is the coverage mask, so there is nothing to derive from" % (effect, part,
                                                                                       cov.reason))
    live_words = composed_palette(stock, page, reskin_spec)
    ink, edge, live_set = choose_ink(px, cov.mask, stock_words, live_words, zeros)
    cx, cy, r = island_centre(cov.mask, w, h)
    edited, stamped = stamp(px, cov.mask, w, h, cx, cy, r, ink, edge)

    zs = set(zeros)
    changed = [i for i in range(len(px)) if px[i] != edited[i]]
    dead_moved = sum(1 for i in changed if not cov.mask[i])
    punch = sum(1 for i in changed if px[i] not in zs and edited[i] in zs)
    fill = sum(1 for i in changed if px[i] in zs and edited[i] not in zs)

    out_png = art / ("%s.png" % page.name)
    art.mkdir(parents=True, exist_ok=True)
    RP.write_indexed_png(bytes(edited), stock_words, w, h, out_png)

    return {
        "effect": effect, "part": part, "page": page.name, "source": source,
        "root": str(root), "art": str(art), "png": str(out_png),
        "page_offset": page.page_offset, "page_bytes": page.page_bytes, "wh": [w, h],
        "clut_offset": page.clut_offset,
        "covered": cov.covered, "dead": cov.dead, "interior_holes": cov.interior_holes,
        "faces": cov.faces, "sampled_indices": len(live_set),
        "ink": ink, "ink_stock": stock_words[ink], "ink_live": live_words[ink],
        "edge": edge, "edge_stock": stock_words[edge], "edge_live": live_words[edge],
        "centroid": [round(cx, 1), round(cy, 1)], "radius": r,
        "stamped": stamped, "changed": len(changed),
        "dead_pad_moved": dead_moved, "cutout_punch": punch, "cutout_fill": fill,
        "transparent_indices": list(zeros),
    }


def report(d: Dict[str, object]) -> List[str]:
    return [
        "ef%03d %s  <- %s" % (d["effect"], d["page"], d["source"]),
        "  page           %#08x .. %#08x   %dx%d 8bpp   CLUT row @%#08x"
        % (d["page_offset"], d["page_offset"] + d["page_bytes"], d["wh"][0], d["wh"][1],
           d["clut_offset"]),
        "  coverage       %d/%d texels sampled (%.1f%%), %d dead, %d interior hole(s), %d faces"
        % (d["covered"], d["wh"][0] * d["wh"][1],
           100.0 * d["covered"] / (d["wh"][0] * d["wh"][1]), d["dead"], d["interior_holes"],
           d["faces"]),
        "  ink   idx %3d  stock %#06x L=%.0f   composed %#06x L=%.0f"
        % (d["ink"], d["ink_stock"], _luma(d["ink_stock"]), d["ink_live"], _luma(d["ink_live"])),
        "  edge  idx %3d  stock %#06x L=%.0f   composed %#06x L=%.0f"
        % (d["edge"], d["edge_stock"], _luma(d["edge_stock"]), d["edge_live"],
           _luma(d["edge_live"])),
        "  glyph          centroid (%s,%s), largest fully-sampled disc r=%d, ring at %.2f R"
        % (d["centroid"][0], d["centroid"][1], d["radius"], RING_R),
        "  stamped        %d texels (%.1f%% of the sampled island, %.1f%% of the page)"
        % (d["stamped"], 100.0 * d["stamped"] / max(1, d["covered"]),
           100.0 * d["stamped"] / max(1, d["wh"][0] * d["wh"][1])),
        "  MEASURED       %d changed texels | dead-pad bytes moved %d | index-0 cutout flips %d "
        "(punch %d / fill %d)"
        % (d["changed"], d["dead_pad_moved"], d["cutout_punch"] + d["cutout_fill"],
           d["cutout_punch"], d["cutout_fill"]),
        "  wrote          %s" % d["png"],
        "  CLUT bytes this glyph needs: 0 -- both indices are already live entries of the row.",
    ]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ef", type=int, default=EFFECT, help="the stock effect id (default 227)")
    ap.add_argument("--part", type=int, default=PART, help="which creature part (default 0)")
    ap.add_argument("--root", default=None,
                    help="staging root (default %s); the repo, a StreamingAssets tree and the "
                         "install are refused" % DEFAULT_ROOT)
    ap.add_argument("--from", dest="from_path", default=None,
                    help="read this container file instead of the install")
    ap.add_argument("--reskin", default=RESKIN_SPEC,
                    help="the sibling CLUT spec whose patched palette the ink must also read under")
    ap.add_argument("--no-export", action="store_true",
                    help="skip `export-art` and stamp into an art directory that already exists "
                         "(the manifest and the coverage overlays are then whatever is there)")
    ap.add_argument("--game", default=None)
    a = ap.parse_args(argv)
    d = generate(a.ef, a.part, a.root, a.from_path, a.game, a.reskin, export=not a.no_export)
    print("\n".join(report(d)))
    # The two numbers the rung's claim rests on.  Non-zero is not a warning here: it means the glyph
    # left the geometry, and the spec's `acknowledge_cutout_reshape = false` would refuse the build.
    return 0 if (d["dead_pad_moved"] == 0 and d["cutout_punch"] + d["cutout_fill"] == 0) else 1


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
