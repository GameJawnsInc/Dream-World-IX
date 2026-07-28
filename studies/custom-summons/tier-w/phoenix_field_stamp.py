r"""TIER W rung W6b-1 -- THE SCENERY WHEEL GENERATOR.  The committed half of the scenery texel proof.

    py phoenix_field_stamp.py                      # export ef211's art, stamp the wheel, report
    py phoenix_field_stamp.py --root DIR           # stage somewhere else (still local-only guarded)
    py phoenix_field_stamp.py --from ef211.bytes   # read a corpus container instead of the install

WHAT THIS FILE IS, AND WHY IT IS THE THING THAT SHIPS
------------------------------------------------------
The artifact this rung proves with is a repainted VRAM page-cell -- 0x4000 bytes of **decoded
Square-Enix content**, not committable at any resolution under any name.  So the proof ships as a
GENERATOR, exactly as W6a's ``emblem_stamp.py`` did: this script reads the user's own container,
re-derives every parameter of the figure from the bytes in front of it, stamps the glyph in INDEX
space, and writes the edited PNG into SCRATCH.  ``phoenix_field.toml`` then points at that PNG.
Nothing between here and the cast carries a stock byte; re-running this on a fresh machine
reproduces the same art from that machine's own bytes.

THE CELL, AND WHY IT IS THIS ONE
--------------------------------
``cell.s0.x704_y256`` on ef211 (Phoenix) -- the full-screen roiling FIRE FIELD.  Every field below
is the container's own derivation, re-measured at run time and printed by :func:`report`:

    writer     s0 id-0 page rect @0x11678, 16,384 B          SINGLE writer  (no co-transform)
    reader     GEOM 0x2b668, 8bpp, CLUT cell (0,247)         SINGLE reader  (no shared read)
               = pal.s0.x0_y247.e256
    coverage   8,128 of 8,192 halfwords -- 99.2% of the cell is live art
    hazards    co-transform NO / two-depths NO / multi-palette NO / shared-read NO
               spill-in NO / spill-out NO / lower-half NO / texanim NO
    program    ef211's id-3 program touches VRAM only through StoreImage -- VRAM -> main RAM, a
               **READ**, which cannot clobber a repaint.  A DISCLOSURE in the plan, not a refusal.

and the decisive argument is not the hazard arithmetic: **this exact upload path is already
cast-proven**.  W5's magenta probe recoloured the five bound palettes of ef211 and the owner
reported the magenta showing up in the flames, so the id-0 scenery path is known to reach the
screen on this container, on this palette, in this cell.

WHY A WHEEL, AND WHY NOTHING DARKER THAN THE BRIGHTEST INK
----------------------------------------------------------
Two laws this tier paid for in playtests, applied together:

* **the CLUT lever cannot make a shape.**  ``[[reskin.target]]`` is a per-index colour FUNCTION: it
  can rotate a hue, it can never move a texel from one index to another.  A softer flame is
  therefore a weak discriminator -- a sceptic attributes it to a palette shift.  A hard-edged
  geometric figure that stock fire never forms cannot be produced by any colour map at all, and
  *"a wheel, not a disc"* is a phrase that survives a moving texture.  W6a branded a stroked ring
  with three radial bars onto Bahamut's wing and the owner has already learned to read it; the same
  figure here is a deliberate continuity choice, not a lack of imagination.
* **THE ADDITIVE-COMPOSITING COROLLARY** (W5 cast A, the miss that cost this tier the most): for VFX
  textures the in-game read keeps the channel the blend favours -- under additive blending a
  *darker* stamp subtracts nothing, it merely fails to add.  So the ink is the LIVE entry of this
  cell's own palette with the **highest measured luminance**, and there is deliberately **no dark
  outline**: W6a's edge index earned its place on an opaque, non-additive hide, and the same
  construct here would be a stroke that the blend renders as no stroke at all.

EVERY PARAMETER IS DERIVED, NOT TYPED
--------------------------------------
* **the ink** is the maximum-luminance entry of the entries the geometry actually SAMPLES, minus
  every transparent one (an ink drawn from the whole row could be a colour that appears nowhere on
  this page; an ink that is the cutout entry would punch a hole instead of painting a figure).
  Ties break to the LOWEST index -- stated, so "deterministic" is a property and not a coincidence.
  Because the ink is an already-live entry of the row, the figure costs **zero CLUT bytes**.
* **the placement** is the centroid of the model's UV cover, and the size is the largest disc whose
  whole perimeter lies inside that cover.  The cover comes from the container's own ``so`` binding
  and uv pools (:func:`ff9mapkit.summons.repaint.bound_models`) in HALFWORD space, expanded to
  texels at the cell's own derived depth -- which is why "dead bytes moved" comes out at zero by
  construction instead of being asserted.
* **the proportions are W6a's, verbatim**; only the SCALE is re-derived.  The stroke half-width is
  ``2.2 / (0.80 * 26)`` of the ring radius -- the ratio the branded wing actually carried -- so the
  figure the owner learned to read is the figure this cell gets, at this cell's own size.

WHY THERE IS NO SIBLING CLUT SPEC HERE (AND ``emblem_stamp.py`` HAD ONE)
------------------------------------------------------------------------
W6a composed onto W4's recolour, so its ink had to read under the palette the cast would actually
run, and the generator rebuilt that palette from the sibling spec.  **This artifact is CLEAN.**
W5's ef211 override was wiped from the mod folder by another session's campaign deploy, and W5's
recolour targets ``pal.s0.x0_y247.e256`` -- *exactly this cell's palette* -- so composing would put
both levers on the same 8,128 halfwords and make a stock-vs-new read ambiguous.  One lever, one
container, one verdict.  The palette at cast time is therefore the STOCK row, which is the row the
ink is chosen under here; there is no second palette to read under and no sibling to rebuild.

PROVENANCE
----------
No stock byte run appears in this file.  The container is read at run time under the kit's sha256
drift guard; every destination goes through :func:`ff9mapkit.summons.export.assert_local_only`,
which refuses a git checkout, a ``StreamingAssets`` tree and the resolved install with no
``--force``.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                              # noqa: E402  (sets up sys.path)
from ff9mapkit.summons import export as EX                       # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402
from ff9mapkit.summons import texture as KT                      # noqa: E402

#: THE PROOF'S OWN STAGING ROOT.  ``phoenix_field.toml``'s ``source`` is an absolute path into
#: ``<root>/art``; re-point one and re-point the other, or the build refuses with "no such source
#: image" rather than silently packing yesterday's art.
DEFAULT_ROOT = os.environ.get("FF9_REPAINT_W6B_ROOT",
                              r"C:\gd\SCRATCH\summon-format\repaint-w6b\ef211")

#: which effect, which VRAM page-cell.  The name is the SCENERY namespace's own spelling
#: (``cell.<writer tag>.x<vram x>_y<vram y>``) and NOT ``page.s0.x704_y256.h256`` -- an ``h == 256``
#: rect is not an addressable unit; the engine uploads it as two stacked cells and the kit refuses
#: the rect spelling by name.
EFFECT = 211
CELL = "cell.s0.x704_y256"

#: THE FIGURE, in units of the derived disc radius -- **W6a's numbers, unchanged**.  A stroked ring
#: at 0.80 R with three radial spokes inside it.  :data:`STROKE_OF_RING` is the stroke half-width as
#: a FRACTION of the ring radius, back-derived from the branded wing (half-width 2.2 at ring radius
#: 0.80 * 26 = 20.8), so the figure scales with the cell instead of thinning out on a larger one --
#: a constant 2.2 here would draw a hairline on a ring two and a half times the size.
RING_R = 0.80
STROKE_OF_RING = 2.2 / (0.80 * 26.0)
SPOKES = 3
SPOKE_DUTY = 0.90

#: THE BOLD PROFILE (``--bold``) -- cast 2's in-game lesson.  The thin wheel (7% of the page) did
#: not read on the emergence vortex, while the probe's stripes (28%) read instantly: the surface's
#: sheared, mirrored UV shreds small figures.  Bold scales the SAME wheel toward stripe-class
#: coverage -- stroke ~0.30 of the ring radius, spokes ~3x wider -- without changing what it is
#: (a ring with three spokes, which smoke never forms).  The default profile stays untouched, so
#: the pinned W6a/cast-2 artifacts regenerate byte-identically.
BOLD_STROKE_OF_RING = 0.30
BOLD_SPOKE_DUTY = 0.72


def _luma(word: int) -> float:
    """Rec.601 luma of one BGR555 palette word, through the kit's own decoder."""
    r, g, b, _a = KT.bgr555_rgba(word)
    return 0.299 * r + 0.587 * g + 0.114 * b


def cell_page(blob: bytes, effect: int = EFFECT, cell: str = CELL) -> RP.TexelPage:
    """Resolve the scenery cell through the kit's own namespace, or REFUSE with its reason.

    :func:`ff9mapkit.summons.repaint.texel_page` answers a REFUSED cell with the refusal rather than
    with "unknown", so a generator pointed at a depth-unknown or same-bytes-two-depths cell stops
    with the measurement instead of drawing a figure into bytes nobody can say the shape of.
    """
    page = RP.texel_page(blob, cell, effect)
    if not page.scenery:                                         # pragma: no cover - name-shaped
        raise SystemExit("%s resolves to a CREATURE page -- this generator is the SCENERY lane's, "
                         "and a creature part is uploaded by index rather than by VRAM cell" % cell)
    return page


def cover_mask(blob: bytes, page: RP.TexelPage) -> Tuple[bytearray, Set[int], int]:
    """``(texel mask, the halfword cover, the number of models that sample this cell)``.

    The scenery lane's coverage unit is the **HALFWORD** -- the only unit that survives three depths
    -- so the mask has to be expanded into texel space at THIS cell's derived depth before a glyph
    can be placed on it.  Doing that expansion here rather than trusting a texel-shaped field is the
    difference between a figure that lands on geometry and one that lands next to it: at 4bpp one
    covered halfword is four texels, at 8bpp two, at 15bpp one.
    """
    per = KT.TEXELS_PER_HW[page.bpp]
    models = [m for m in RP.bound_models(blob) if page.cell in m.cover]
    cover: Set[int] = {hw for m in models for hw in m.cover[page.cell]}
    mask = bytearray(page.w * page.h)
    for hw in cover:
        line, hx = divmod(hw, RS.PAGE_CELL_W)
        for k in range(per):
            mask[line * page.w + hx * per + k] = 1
    if not any(mask):                                            # pragma: no cover - emitted cells
        raise SystemExit("%s has an EMPTY UV cover -- the placement constraint is the cover, so "
                         "there is nothing to derive a figure from" % page.name)
    return mask, cover, len(models)


def choose_ink(px: Sequence[int], mask: Sequence[int], words: Sequence[int],
               zeros: Sequence[int]) -> Tuple[int, List[int]]:
    """``(ink index, the sampled index set)`` -- **the brightest live entry, measured not chosen.**

    THE ADDITIVE-COMPOSITING COROLLARY is the whole of it: a darker ink subtracts nothing under
    additive blending, so the only ink guaranteed to READ is the maximum-luminance one.  The
    candidate set is the entries the geometry SAMPLES minus every transparent one -- an ink from the
    whole 256-entry row could be a colour that appears nowhere on this page, and the cutout entry
    would punch a hole instead of painting a figure.  The tie-break to the LOWEST index is stated
    rather than inherited from ``max``: this cell's two brightest entries are the same BGR555 word,
    and "deterministic across re-runs" must be a property of the rule, not of an implementation.
    """
    zs = set(zeros)
    live = sorted({px[i] for i in range(len(mask)) if mask[i]} - zs)
    if not live:                                                 # pragma: no cover - stock has 255
        raise SystemExit("no sampled, non-transparent index on this cell -- nothing to ink with")
    ink = max(live, key=lambda i: (_luma(words[i]), -i))
    return ink, live


def island_centre(mask: Sequence[int], w: int, h: int) -> Tuple[float, float, int, bool]:
    """``(cx, cy, r, coverage_bound)`` -- the cover's centroid, the largest disc inside it, and
    WHICH constraint stopped the search.

    The radius walks OUTWARD and stops at the first perimeter that leaves the cover, so the disc is
    contiguous rather than the largest radius that happens to work.  ``coverage_bound`` is the honest
    disclosure this cell forces: at 99.2% cover the binding constraint is the CELL EDGE, not the art,
    and a report that said "largest fully-sampled disc" without saying which limit bit would be
    quoting a coverage measurement that measured the page.
    """
    xs = [i % w for i in range(len(mask)) if mask[i]]
    ys = [i // w for i in range(len(mask)) if mask[i]]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    r, bound = 0, False
    for rad in range(4, min(w, h) // 2):
        ok = True
        for a in range(80):
            th = a / 40.0 * math.pi
            px_, py_ = int(cx + rad * math.cos(th)), int(cy + rad * math.sin(th))
            if not (0 <= px_ < w and 0 <= py_ < h):
                ok = False
                break
            if not mask[py_ * w + px_]:
                ok, bound = False, True
                break
        if not ok:
            break
        r = rad
    return cx, cy, r, bound


def stamp(px: Sequence[int], mask: Sequence[int], w: int, h: int, cx: float, cy: float, r: int,
          ink: int, stroke_frac: float = STROKE_OF_RING,
          spoke_duty: float = SPOKE_DUTY) -> Tuple[bytearray, int]:
    """The wheel, written ONLY where the UV cover says a face samples the texel.

    That single guard is what makes "dead bytes moved" come out at zero rather than being asserted.
    ONE ink and no outline: see the module docstring's additive corollary -- a dark edge under
    additive blending is a stroke the blend renders as no stroke.
    """
    out = bytearray(px)
    ring = RING_R * r
    half = stroke_frac * ring
    n = 0
    for y in range(h):
        for x in range(w):
            i = y * w + x
            if not mask[i]:
                continue
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy)
            th = math.atan2(dy, dx)
            on_ring = abs(d - ring) <= half
            on_spoke = d <= ring and abs(((th * SPOKES / math.pi) % 2.0) - 1.0) > spoke_duty
            if on_ring or on_spoke:
                out[i] = ink
                n += 1
    return out, n


def generate(effect: int = EFFECT, cell: str = CELL, root: Optional[str] = None,
             from_path: Optional[str] = None, game=None, export: bool = True,
             mode: str = "ink", bold: bool = False) -> Dict[str, object]:
    """Export the effect's art, stamp the cell, and return every number the spec and the report quote.

    ``mode="ink"`` (the default, and the pinned artifact) paints the wheel in the max-luminance live
    entry.  ``mode="punch"`` writes the TRANSPARENT index instead -- THE CAST-1 DISCRIMINATOR,
    pre-registered as sec 6 Q6's fallback: the ink wheel did not read under additive stacking
    (brighter-on-bright adds almost nothing a moving fire does not already add), and a PUNCHED texel
    contributes NOTHING to an additive blend, so the wheel reads as persistent dark gaps -- the one
    negative signal additive compositing cannot wash out.  It also separates the two remaining
    hypotheses: gaps visible = the edit reaches the screen and cast 1 was a legibility miss; gaps
    absent = these bytes are not what the fire on screen samples, a different diagnosis entirely.
    """
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

    page = cell_page(stock, effect, cell)
    w, h = page.wh
    raw = stock[page.page_offset:page.page_offset + page.page_bytes]
    # ONE BYTE PER TEXEL at every depth: 8bpp raw IS texels; 4bpp unpacks two per byte (the kit's
    # own nibble codec -- `write_indexed_png` on unpacked texels is exactly `write_indexed4_png`,
    # and the import re-packs through `read_indexed4_png` keyed by `expect_bpp`).  15bpp has no
    # index space to stamp in and no cell of this rung's cast ladder is 15bpp.
    if page.bpp == 4:
        px = RP.unpack4(raw)
    elif page.bpp == 8:
        px = raw
    else:
        raise SystemExit("this generator stamps INDEX space; %s is %dbpp" % (page.name, page.bpp))
    words = RP.palette_words(stock, page)
    zeros = RP.transparent_indices(words)
    mask, cover, n_models = cover_mask(stock, page)

    ink, live_set = choose_ink(px, mask, words, zeros)
    if mode == "ink":
        write_value = ink
    elif mode == "punch":
        if not zeros:
            raise SystemExit("no transparent index on this row -- nothing to punch with")
        write_value = zeros[0]
    else:
        raise SystemExit("unknown mode %r -- this generator ships `ink` and `punch`" % mode)
    cx, cy, r, cov_bound = island_centre(mask, w, h)
    edited, stamped = stamp(px, mask, w, h, cx, cy, r, write_value,
                            stroke_frac=BOLD_STROKE_OF_RING if bold else STROKE_OF_RING,
                            spoke_duty=BOLD_SPOKE_DUTY if bold else SPOKE_DUTY)

    zs = set(zeros)
    changed = [i for i in range(len(px)) if px[i] != edited[i]]
    dead_moved = sum(1 for i in changed if not mask[i])
    punch = sum(1 for i in changed if px[i] not in zs and edited[i] in zs)
    fill = sum(1 for i in changed if px[i] in zs and edited[i] not in zs)

    out_png = art / ("%s.png" % page.name)
    art.mkdir(parents=True, exist_ok=True)
    RP.write_indexed_png(bytes(edited), words, w, h, out_png)

    hz = page.hazards
    return {
        "mode": mode, "write_value": write_value,
        "effect": effect, "cell": page.name, "source": source,
        "root": str(root), "art": str(art), "png": str(out_png),
        "page_offset": page.page_offset, "page_bytes": page.page_bytes, "wh": [w, h],
        "bpp": page.bpp, "vram": list(page.cell), "palette_name": page.palette_name,
        "clut_offset": page.clut_offset, "clut_entries": page.clut_entries,
        "writers": ["%s %s @%#x %dB" % (x.tag, x.kind, x.off, x.nbytes) for x in hz.writers],
        "readers": ["GEOM %#x %dbpp CLUT %s" % (x.geom, x.bpp, x.clut_cell) for x in hz.readers],
        "hazards": list(hz.names), "program": hz.program, "program_evidence": hz.program_evidence,
        "covered_halfwords": hz.covered_halfwords, "covered_texels": sum(mask),
        "models_here": n_models, "sampled_indices": len(live_set),
        "ink": ink, "ink_word": words[ink], "ink_luma": _luma(words[ink]),
        "transparent_indices": list(zeros),
        "transparent_texels": sum(1 for v in px if v in zs),
        "centroid": [round(cx, 1), round(cy, 1)], "radius": r, "coverage_bound": cov_bound,
        "ring_radius": RING_R * r, "stroke": 2.0 * STROKE_OF_RING * RING_R * r,
        "stamped": stamped, "changed": len(changed),
        "dead_bytes_moved": dead_moved, "cutout_punch": punch, "cutout_fill": fill,
    }


def report(d: Dict[str, object]) -> List[str]:
    tot = d["wh"][0] * d["wh"][1]
    return [
        "ef%03d %s  <- %s" % (d["effect"], d["cell"], d["source"]),
        "  cell           %#08x .. %#08x   VRAM %s   %dx%d @ %dbpp"
        % (d["page_offset"], d["page_offset"] + d["page_bytes"], d["vram"], d["wh"][0], d["wh"][1],
           d["bpp"]),
        "  writer(s)      %s" % "; ".join(d["writers"]),
        "  reader(s)      %s  -> %s @%#x, %d entries"
        % ("; ".join(d["readers"]), d["palette_name"], d["clut_offset"], d["clut_entries"]),
        "  hazards        %s" % (", ".join(d["hazards"]) or "NONE -- single writer, single reader, "
                                                            "single depth, single palette, no spill"),
        "  program        %s  (%s)" % (d["program"], d["program_evidence"]),
        "  coverage       %d/8192 halfwords = %d/%d texels sampled (%.1f%%) by %d model(s)"
        % (d["covered_halfwords"], d["covered_texels"], tot,
           100.0 * d["covered_texels"] / tot, d["models_here"]),
        "  ink   idx %3d  %#06x  L=%.1f  -- the MAX-LUMINANCE live entry of %d sampled (additive "
        "compositing: a darker ink subtracts nothing, it merely fails to add)"
        % (d["ink"], d["ink_word"], d["ink_luma"], d["sampled_indices"]),
        "  figure         centroid (%s,%s), largest contiguous disc r=%d (%s), ring at %.2f R = "
        "%.1f texels, stroke %.1f texels, %d spokes"
        % (d["centroid"][0], d["centroid"][1], d["radius"],
           "bounded by the COVER" if d["coverage_bound"] else
           "bounded by the CELL EDGE -- the cover is not the binding constraint at %.1f%%"
           % (100.0 * d["covered_texels"] / tot),
           RING_R, d["ring_radius"], d["stroke"], SPOKES),
        "  stamped        %d texels (%.1f%% of the sampled cell, %.1f%% of the page)"
        % (d["stamped"], 100.0 * d["stamped"] / max(1, d["covered_texels"]),
           100.0 * d["stamped"] / max(1, tot)),
        "  MEASURED       %d changed texels | dead bytes moved %d | cutout flips %d "
        "(punch %d / fill %d, of %d transparent texels on the page)"
        % (d["changed"], d["dead_bytes_moved"], d["cutout_punch"] + d["cutout_fill"],
           d["cutout_punch"], d["cutout_fill"], d["transparent_texels"]),
        "  wrote          %s" % d["png"],
        "  CLUT bytes this figure needs: 0 -- the ink is already a live entry of the row.",
    ]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ef", type=int, default=EFFECT, help="the stock effect id (default 211)")
    ap.add_argument("--cell", default=CELL,
                    help="the SCENERY page-cell name (default %s)" % CELL)
    ap.add_argument("--root", default=None,
                    help="staging root (default %s); the repo, a StreamingAssets tree and the "
                         "install are refused" % DEFAULT_ROOT)
    ap.add_argument("--from", dest="from_path", default=None,
                    help="read this container file instead of the install")
    ap.add_argument("--no-export", action="store_true",
                    help="skip `export-art` and stamp into an art directory that already exists "
                         "(the manifest and the per-cell previews are then whatever is there)")
    ap.add_argument("--bold", action="store_true",
                    help="the stripe-class figure profile (stroke 0.30R, spokes 3x wider) -- for "
                         "surfaces whose sheared UV shreds the thin wheel; the default profile and "
                         "its pinned artifacts are untouched")
    ap.add_argument("--mode", choices=("ink", "punch"), default="ink",
                    help="ink = paint the wheel in the max-luminance live entry (the pinned "
                         "artifact); punch = write the TRANSPARENT index instead -- the cast-1 "
                         "discriminator (a hole adds nothing under additive blending)")
    ap.add_argument("--game", default=None)
    a = ap.parse_args(argv)
    d = generate(a.ef, a.cell, a.root, a.from_path, a.game, export=not a.no_export, mode=a.mode, bold=a.bold)
    print("\n".join(report(d)))
    # THE TWO NUMBERS THE CLAIM RESTS ON, per mode -- `dead_bytes_moved` must be 0 either way (paint
    # outside the UV cover is inert).  In `ink` mode `cutout_punch` must be 0 (nothing is removed;
    # `cutout_fill` is the deliberate, disclosed count).  In `punch` mode the polarity flips exactly:
    # `cutout_fill` must be 0 (a punch that FILLS a hole would be writing art, not removing it) and
    # `cutout_punch` IS the figure, disclosed above rather than waved through.
    clean = (d["cutout_punch"] == 0) if a.mode == "ink" else (d["cutout_fill"] == 0)
    return 0 if (d["dead_bytes_moved"] == 0 and clean) else 1


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
