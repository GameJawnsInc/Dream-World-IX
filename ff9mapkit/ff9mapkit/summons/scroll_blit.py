r"""THE SCROLL-BLIT TABLE -- the VRAM an effect's own program REWRITES EVERY FRAME (HLE op 144).

WHAT OP 144 IS (tier-r ``CALLBACK-OPS.md`` ADDENDUM 9). ``fn 0x47b40`` queues two primitives whose code
word is ``0xE7000000``, and ``SFXRender.cs`` dispatches ``case 231`` to ``DR_MOVE`` -- libgpu's
VRAM-to-VRAM block move. Its seven arguments are ``(scroll, dstX, dstY, width, period, srcX, srcY)``:
one source band, split at ``scroll % period`` and written back with the halves swapped, i.e. **a
vertical scroll with wraparound done as a VRAM blit**, the PS1 way to animate a texture without moving
a UV. Over one period every row of the source band reaches every row of the destination band.

WHY THE TEXEL LANE HAS TO KNOW
------------------------------
**A DESTINATION band is rewritten from its source every frame the op runs.** A repaint of texels
inside it is byte-correct on disk, deploys, verifies -- and never reaches the screen. That is this
lane's worst failure class because it is SILENT, and the null it produces gets charged to whatever
mechanism the author was testing. A **SOURCE** hit is milder and is never merged with it: the repaint
is READ and propagated, so it shows -- in the destination band too, scrolling.

The W6b-1 program-VRAM census could not see this. Its writer union is ``LoadImage`` / ``MoveImage`` /
loader op ``0x07``, which take their rectangle as a POINTER (0 of 18 fold); op 144 takes its rectangle
as seven loose integers, so it yields PER-CELL verdicts -- and it was never in that union at all.

THE MEASUREMENT (tier-r ADDENDUM 10, ``drmove_cells.py``): **59 containers, 167 sites, 0 excluded**
(every period folded -- a complete static picture), against 198 editable scenery cells: **20 containers
/ 88 cells are DESTINATIONS** and 19 / 82 are SOURCES. Independently, running the plugin headless on
ef407 executed **252 DR_MOVE blits into (704,384) from (704,256) over native frames 85-211** -- the
static site is the one that runs (``studies/custom-summons/headless/``, its census row for ef407).

WHAT IT DOES NOT ESTABLISH -- and why the refusal has a key: **reachability per cast.** A blit rewrites
its band only while it runs, and these are static sites: the table does not know when a cast draws a
cell. ef211's own cast ladder, read against this table after the fact, sides with the refusal wherever
it was checked (:data:`REACHABILITY`): two wheels on a FULL destination were invisible, and the band
under cast 2b's bold wheel, once quoted here as a counter-witness, is blitted on every frame its page
is drawn, per the game's own capture. So :data:`ACK_KEY` lifts the refusal, literal-boolean only, and
the build says what was lifted.

THE JOIN, AND ITS TWO DELIBERATE COARSENESSES
---------------------------------------------
* **VRAM is one address space**, so a site in ANY program chunk is tested against EVERY editable cell,
  whichever section declared it -- the instrument's own join, kept rather than narrowed;
* **the SOURCE fields are less certain than the destination.** ``dstX/dstY/width`` fold in the ordinary
  census and the hardware's fit predicate (``x + w <= 1024``, ``y + h <= 512``, ``w > 0``) holds on
  167/167; ``srcX/srcY`` ride the stack beside the period and four sites fold to a source that does not
  fit VRAM at all (ef022, ef095, ef222, ef418). Those name no source cell, and a remedy says so rather
  than naming one (:attr:`ScrollBlit.src_in_vram`).

WHY THIS IS A CACHED CONSTANT, AND WHAT PINS IT
-----------------------------------------------
The derivation needs tier-r's disassembler and annotator over the container's id-3 program images --
derived stock content that lives under ``C:\gd\SCRATCH`` and never in a build. So, exactly like
:data:`ff9mapkit.summons.depth_attribution.PROGRAM_DEPTH` and
:data:`ff9mapkit.summons.repaint.PROGRAM_VRAM_WRITE_IDS`, this table is a CACHE OF A MEASUREMENT and is
**RE-DERIVATION-PINNED**: ``studies/custom-summons/tier-w/scroll_blit_gates.py`` re-parses every
annotated listing through ``drmove_cells.blit_rects`` and asserts equality site for site, then re-runs
the instrument's corpus verdict against the kit's own per-cell join. *A constant nobody re-checks is a
claim.* The counts below are asserted AT IMPORT so a truncated table fails loudly.

PROVENANCE
----------
VRAM coordinates, sizes, program-chunk indices, effect ids and counts. No stock byte, no hex run.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple

__all__ = [
    "SITES", "CONTAINERS", "EDIT_SURFACE_CELLS", "DEST_CONTAINERS", "DEST_CELLS",
    "SOURCE_CONTAINERS", "SOURCE_CELLS", "VRAM_W", "VRAM_H", "CELL_W", "CELL_LINES",
    "ScrollBlit", "SCROLL_BLITS", "blits", "cell_hits", "cell_of", "cells_under",
    "rewritten_halfwords",
    "ACK_KEY", "MECHANISM", "MEASUREMENT", "EF407_EXECUTED", "REACHABILITY", "ACK_WARNING",
]

#: every op-144 call site in the corpus, and the containers they sit in -- asserted below.
SITES = 167
CONTAINERS = 59
#: THE CORPUS VERDICT against the texel EDIT surface (``scenery_texel_pages`` at its default channels).
#: Not checkable here -- it needs the containers -- so ``scroll_blit_gates.py`` re-derives all five
#: through the kit's own join AND through ``drmove_cells.analyse`` and asserts both equal these.
EDIT_SURFACE_CELLS = 198
DEST_CONTAINERS, DEST_CELLS = 20, 88
SOURCE_CONTAINERS, SOURCE_CELLS = 19, 82
#: the PSX VRAM, in halfwords x lines -- what the hardware's fit predicate is stated against.
VRAM_W, VRAM_H = 1024, 512
#: one census page-cell: 64 halfwords x 128 lines (``reskin.PAGE_CELL_W`` / ``PAGE_CELL_LINES``; the
#: equality is asserted by :mod:`ff9mapkit.summons.repaint` at import, which imports both).
CELL_W, CELL_LINES = 64, 128

# ``(effect, program chunk, dst x, dst y, width, period, src x, src y)`` -- one row per op-144 CALL
# SITE, in listing order, duplicates kept: two sites queueing the same rect are two sites.  Width and
# x are VRAM HALFWORDS; y and the period are VRAM LINES.
_SITE_ROWS = (
    (4, 0, 640, 384, 64, 128, 640, 256), (6, 0, 576, 384, 64, 128, 576, 256),
    (7, 0, 480, 384, 32, 128, 480, 256), (22, 0, 576, 384, 16, 64, 6144, 64),
    (38, 0, 704, 384, 64, 128, 704, 256), (38, 0, 640, 256, 64, 128, 640, 384),
    (52, 0, 640, 384, 64, 128, 640, 256), (62, 0, 576, 384, 64, 128, 576, 256),
    (72, 0, 480, 384, 32, 128, 480, 256), (77, 0, 640, 384, 64, 128, 640, 256),
    (95, 0, 576, 384, 16, 64, 4096, 64), (125, 0, 512, 256, 32, 128, 544, 256),
    (125, 0, 512, 256, 32, 128, 544, 256), (131, 0, 704, 384, 64, 64, 64, 64),
    (131, 0, 704, 384, 64, 64, 64, 64), (131, 0, 608, 256, 32, 240, 576, 256),
    (134, 0, 448, 256, 64, 128, 512, 256), (134, 0, 576, 256, 64, 128, 768, 256),
    (143, 0, 448, 256, 64, 128, 512, 256), (151, 0, 640, 384, 64, 128, 640, 256),
    (151, 0, 640, 384, 64, 128, 640, 256), (151, 0, 640, 384, 64, 128, 640, 256),
    (152, 0, 640, 384, 64, 128, 640, 256), (152, 0, 640, 384, 64, 128, 640, 256),
    (152, 0, 640, 384, 64, 128, 640, 256), (178, 0, 448, 368, 28, 112, 476, 368),
    (178, 0, 640, 256, 28, 112, 668, 256), (179, 0, 448, 256, 32, 128, 480, 256),
    (179, 0, 448, 384, 32, 128, 480, 384), (179, 0, 448, 256, 32, 128, 480, 256),
    (179, 0, 448, 256, 32, 128, 480, 256), (179, 0, 448, 384, 32, 128, 480, 384),
    (179, 0, 448, 256, 32, 128, 480, 256), (179, 0, 448, 384, 32, 128, 480, 384),
    (184, 0, 384, 256, 64, 128, 384, 384), (184, 0, 448, 256, 32, 128, 480, 256),
    (184, 0, 448, 256, 32, 128, 480, 256), (184, 0, 640, 256, 32, 128, 672, 256),
    (184, 0, 704, 256, 56, 112, 704, 368), (184, 0, 448, 256, 24, 96, 448, 384),
    (186, 0, 576, 368, 56, 112, 576, 256), (186, 0, 640, 368, 56, 112, 640, 256),
    (186, 0, 576, 368, 56, 112, 576, 256), (186, 0, 576, 368, 56, 112, 576, 256),
    (186, 0, 640, 368, 56, 112, 640, 256), (186, 0, 352, 256, 32, 128, 320, 256),
    (186, 0, 576, 368, 56, 112, 576, 256), (186, 0, 576, 368, 56, 112, 576, 256),
    (186, 0, 352, 256, 32, 128, 320, 256), (203, 0, 576, 256, 56, 112, 632, 256),
    (211, 0, 576, 256, 28, 112, 604, 256), (211, 0, 576, 368, 28, 112, 604, 368),
    (211, 0, 576, 256, 28, 112, 604, 256), (211, 0, 576, 368, 28, 112, 604, 368),
    (211, 0, 704, 256, 64, 128, 704, 384), (211, 0, 640, 256, 32, 128, 672, 256),
    (211, 0, 704, 256, 64, 128, 704, 384), (211, 0, 640, 256, 32, 128, 672, 256),
    (211, 0, 768, 384, 16, 128, 784, 384), (214, 0, 480, 384, 32, 128, 480, 256),
    (218, 0, 576, 384, 64, 128, 576, 256), (219, 0, 640, 384, 64, 128, 640, 256),
    (220, 0, 640, 384, 64, 128, 640, 256), (222, 0, 576, 384, 16, 64, 6144, 64),
    (223, 0, 512, 256, 32, 128, 544, 256), (223, 0, 512, 256, 32, 128, 544, 256),
    (224, 0, 480, 256, 32, 128, 768, 256), (225, 0, 640, 256, 32, 128, 672, 256),
    (225, 0, 752, 256, 16, 128, 736, 256), (225, 0, 672, 384, 16, 64, 688, 384),
    (225, 0, 752, 256, 16, 128, 736, 256), (227, 1, 832, 256, 32, 192, 864, 256),
    (245, 0, 448, 256, 64, 128, 512, 256), (245, 0, 448, 384, 32, 128, 480, 384),
    (245, 0, 640, 256, 32, 128, 672, 256), (250, 0, 704, 384, 64, 64, 64, 64),
    (250, 0, 704, 384, 64, 64, 64, 64), (251, 1, 704, 256, 32, 128, 864, 256),
    (251, 1, 864, 384, 16, 64, 880, 384), (251, 1, 672, 384, 16, 64, 688, 384),
    (257, 0, 448, 288, 32, 64, 480, 288), (276, 0, 640, 256, 64, 128, 576, 256),
    (276, 0, 640, 256, 64, 128, 576, 256), (308, 0, 448, 384, 24, 96, 800, 256),
    (308, 0, 480, 256, 32, 128, 768, 256), (378, 0, 448, 256, 32, 128, 672, 256),
    (378, 0, 672, 384, 16, 64, 688, 384), (381, 1, 832, 256, 64, 128, 832, 384),
    (381, 1, 832, 256, 64, 128, 832, 384), (381, 2, 384, 256, 64, 128, 384, 384),
    (381, 2, 576, 256, 64, 128, 640, 256), (381, 3, 768, 320, 32, 128, 800, 320),
    (381, 3, 704, 256, 64, 128, 704, 384), (381, 3, 768, 320, 32, 128, 800, 320),
    (381, 3, 704, 256, 64, 128, 704, 384), (381, 3, 704, 256, 64, 128, 704, 384),
    (381, 3, 832, 256, 32, 128, 864, 256), (381, 3, 704, 256, 64, 128, 704, 384),
    (381, 3, 832, 256, 32, 128, 864, 256), (381, 3, 704, 256, 64, 128, 704, 384),
    (381, 3, 832, 256, 32, 128, 864, 256), (381, 3, 704, 256, 64, 128, 704, 384),
    (381, 3, 832, 256, 32, 128, 864, 256), (381, 3, 704, 256, 64, 128, 704, 384),
    (381, 3, 832, 256, 32, 128, 864, 256), (381, 3, 704, 256, 64, 128, 704, 384),
    (381, 3, 832, 256, 32, 128, 864, 256), (381, 4, 384, 256, 64, 128, 384, 384),
    (381, 4, 384, 256, 64, 128, 384, 384), (381, 4, 384, 256, 64, 128, 384, 384),
    (381, 4, 384, 256, 64, 128, 384, 384), (381, 5, 512, 256, 64, 128, 512, 384),
    (381, 6, 640, 256, 32, 128, 672, 256), (381, 6, 640, 256, 32, 128, 672, 256),
    (381, 7, 832, 256, 16, 64, 848, 256), (381, 7, 832, 256, 16, 64, 848, 256),
    (381, 7, 864, 256, 32, 128, 864, 384), (381, 7, 512, 384, 32, 128, 544, 384),
    (381, 7, 512, 256, 32, 128, 544, 256), (381, 8, 704, 256, 32, 128, 736, 256),
    (381, 8, 768, 256, 32, 128, 800, 256), (390, 0, 704, 384, 32, 128, 736, 384),
    (394, 0, 448, 288, 32, 64, 480, 288), (405, 0, 512, 256, 32, 192, 544, 256),
    (407, 0, 704, 384, 64, 128, 704, 256), (407, 0, 640, 256, 64, 128, 640, 384),
    (415, 0, 608, 256, 32, 128, 576, 256), (418, 0, 640, 480, 64, 32, 704, 704),
    (418, 0, 576, 256, 48, 128, 576, 384), (420, 0, 480, 384, 32, 128, 480, 256),
    (420, 0, 512, 384, 32, 128, 512, 256), (424, 0, 448, 256, 56, 112, 448, 368),
    (424, 0, 576, 320, 32, 128, 608, 320), (424, 0, 576, 256, 32, 64, 608, 256),
    (429, 0, 512, 256, 32, 64, 1, 1), (435, 0, 896, 0, 40, 80, 936, 80),
    (445, 0, 640, 256, 64, 128, 576, 256), (446, 0, 704, 256, 56, 112, 704, 368),
    (446, 0, 640, 256, 32, 128, 672, 256), (446, 0, 576, 320, 24, 96, 576, 416),
    (447, 1, 832, 256, 16, 64, 848, 256), (447, 1, 832, 256, 16, 64, 848, 256),
    (447, 1, 864, 256, 32, 128, 864, 384), (447, 1, 512, 384, 32, 128, 544, 384),
    (447, 1, 512, 256, 32, 128, 544, 256), (447, 2, 704, 256, 32, 128, 736, 256),
    (447, 2, 768, 256, 32, 128, 800, 256), (460, 0, 640, 384, 64, 128, 640, 256),
    (460, 0, 640, 384, 64, 128, 640, 256), (460, 0, 640, 384, 64, 128, 640, 256),
    (489, 0, 448, 288, 32, 64, 480, 288), (496, 0, 512, 256, 64, 128, 512, 384),
    (496, 0, 448, 288, 56, 112, 448, 400), (497, 0, 448, 256, 32, 128, 480, 256),
    (497, 0, 448, 384, 32, 128, 480, 384), (498, 0, 832, 384, 16, 128, 848, 384),
    (498, 0, 448, 256, 16, 128, 464, 256), (498, 0, 768, 256, 32, 128, 800, 256),
    (498, 0, 800, 384, 32, 128, 864, 384), (498, 0, 448, 256, 16, 128, 464, 256),
    (498, 0, 448, 256, 16, 128, 464, 256), (499, 0, 576, 256, 64, 128, 576, 384),
    (499, 0, 576, 256, 64, 128, 576, 384), (499, 0, 512, 256, 64, 128, 512, 384),
    (499, 0, 704, 256, 32, 128, 736, 256), (510, 0, 704, 256, 64, 128, 704, 384),
    (510, 0, 640, 256, 32, 128, 672, 256),
)

Rect = Tuple[int, int, int, int]                     # (x, y, w, h) -- halfwords x lines


def _overlap(a: Rect, b: Rect) -> Optional[Rect]:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    return (x0, y0, x1 - x0, y1 - y0) if x0 < x1 and y0 < y1 else None


def cell_of(x: int, y: int) -> Tuple[int, int]:
    """The census page-cell a VRAM coordinate lies in."""
    return (x - x % CELL_W, y - y % CELL_LINES)


def cells_under(rect: Rect) -> Tuple[Tuple[int, int], ...]:
    """Every census page-cell a VRAM rect touches, in (x, y) order."""
    x, y, w, h = rect
    x0, y0 = cell_of(x, y)
    return tuple((cx, cy) for cx in range(x0, x + w, CELL_W) for cy in range(y0, y + h, CELL_LINES))


@dataclass(frozen=True)
class ScrollBlit:
    """One op-144 destination/source rectangle pair, with every site that queues it.

    The site count is kept because a rect queued from five sites is not five times as certain to run
    -- it is five places a phase question has to be asked -- and the chunks are kept because they are
    the only IDENTIFICATION the listing offers.
    """
    effect: int
    dst: Tuple[int, int]
    size: Tuple[int, int]                            # (width halfwords, period lines)
    src: Tuple[int, int]
    chunks: Tuple[int, ...]
    sites: int

    @property
    def dst_rect(self) -> Rect:
        return (self.dst[0], self.dst[1], self.size[0], self.size[1])

    @property
    def src_rect(self) -> Rect:
        return (self.src[0], self.src[1], self.size[0], self.size[1])

    @property
    def src_in_vram(self) -> bool:
        """Whether the folded SOURCE fits the 1024x512 VRAM -- the predicate the destination passes
        167/167. False on 4 corpus sites, which therefore name no source cell."""
        sx, sy, w, h = self.src_rect
        return sx >= 0 and sy >= 0 and sx + w <= VRAM_W and sy + h <= VRAM_H

    def dest_overlap(self, cell: Tuple[int, int]) -> Optional[Rect]:
        """The part of ``cell`` this blit REWRITES, in VRAM coordinates, or None."""
        return _overlap(self.dst_rect, (cell[0], cell[1], CELL_W, CELL_LINES))

    def source_overlap(self, cell: Tuple[int, int]) -> Optional[Rect]:
        """The part of ``cell`` this blit READS, in VRAM coordinates, or None."""
        if not self.src_in_vram:
            return None
        return _overlap(self.src_rect, (cell[0], cell[1], CELL_W, CELL_LINES))

    def feeds(self, band: Rect) -> Optional[Rect]:
        """The SOURCE band written into ``band`` (a part of the destination).

        Columns map one to one at the source's offset; ROWS do not -- the scroll rotates the band, so
        over one period every source row lands on every destination row. So the source of a
        destination column range is that column range over the WHOLE period. None when the source
        does not fit VRAM.
        """
        if not self.src_in_vram:
            return None
        x0 = self.src[0] + (band[0] - self.dst[0])
        return (x0, self.src[1], band[2], self.size[1])

    def describe(self) -> str:
        return ("op 144 dst (%d,%d) %dx%d <- src (%d,%d)%s, %d site(s) in chunk %s"
                % (self.dst[0], self.dst[1], self.size[0], self.size[1], self.src[0], self.src[1],
                   "" if self.src_in_vram else " [source does not fit VRAM as folded]",
                   self.sites, "/".join(str(c) for c in self.chunks)))


def _build() -> Dict[int, Tuple[ScrollBlit, ...]]:
    grouped: Dict[int, Dict[Tuple[int, ...], List[int]]] = {}
    for ef, chunk, dx, dy, w, h, sx, sy in _SITE_ROWS:
        grouped.setdefault(ef, {}).setdefault((dx, dy, w, h, sx, sy), []).append(chunk)
    return {ef: tuple(ScrollBlit(effect=ef, dst=(k[0], k[1]), size=(k[2], k[3]), src=(k[4], k[5]),
                                 chunks=tuple(sorted(set(cs))), sites=len(cs))
                      for k, cs in rects.items())
            for ef, rects in grouped.items()}


#: ``{effect: (ScrollBlit, ...)}`` -- every distinct op-144 rect pair per container.
SCROLL_BLITS: Dict[int, Tuple[ScrollBlit, ...]] = _build()


def blits(effect: Optional[int]) -> Tuple[ScrollBlit, ...]:
    """Every scroll blit one container's program queues. ``effect is None`` answers ``()`` and that
    is ignorance, not safety -- the same law :func:`ff9mapkit.summons.repaint.program_class` states,
    which is why the program-VRAM gate already refuses an id-less derivation outright."""
    if effect is None:
        return ()
    return SCROLL_BLITS.get(int(effect), ())


def cell_hits(effect: Optional[int], cell: Tuple[int, int]
              ) -> Tuple[Tuple[ScrollBlit, ...], Tuple[ScrollBlit, ...]]:
    """``(destination hits, source hits)`` for one page-cell -- two lists, never merged."""
    bs = blits(effect)
    return (tuple(b for b in bs if b.dest_overlap(cell)),
            tuple(b for b in bs if b.source_overlap(cell)))


def rewritten_halfwords(dst: Tuple[ScrollBlit, ...], cell: Tuple[int, int]) -> FrozenSet[int]:
    """Cell-local halfword indices (``row * CELL_W + col``) the destination hits rewrite."""
    out = set()
    for b in dst:
        o = b.dest_overlap(cell)
        if o:
            for y in range(o[1], o[1] + o[3]):
                row = (y - cell[1]) * CELL_W
                out.update(row + x - cell[0] for x in range(o[0], o[0] + o[2]))
    return frozenset(out)


#: THE SPEC KEY.  Literal-boolean-only, like every other acknowledgement in this lane.
ACK_KEY = "acknowledge_scroll_blit_destination"

#: the mechanism, in the one sentence every refusal and disclosure quotes.
MECHANISM = (
    "HLE op 144 is a VRAM SCROLL BLIT: it queues two DR_MOVE primitives (SFXRender case 231, "
    "libgpu's VRAM-to-VRAM block move) that copy a source band into a destination band split at the "
    "animated phase and swapped -- a vertical scroll with wraparound -- every frame it runs")

#: the corpus measurement, asserted against the table below.
MEASUREMENT = (
    "%d op-144 sites over %d containers, every period folded; against the %d editable scenery "
    "cells, %d containers / %d cells are DESTINATIONS and %d / %d are SOURCES -- a class the W6b "
    "program-VRAM census structurally could not see, because op 144 was never in its writer union"
    % (SITES, CONTAINERS, EDIT_SURFACE_CELLS, DEST_CONTAINERS, DEST_CELLS, SOURCE_CONTAINERS,
       SOURCE_CELLS))

#: the one container on which a static site has been seen to EXECUTE.
EF407_EXECUTED = (
    "ON ef407 THE STATIC SITE IS THE ONE THAT RUNS: the plugin, run headless, executed 252 DR_MOVE "
    "blits into (704,384) from (704,256) over native frames 85-211")

#: what the table does not establish -- the reason the refusal has a key at all -- and what the
#: in-game record says about it.  The ef211 cast ladder (W6b-SCENERY.md sec 5) read against this
#: table, after the fact: the ink and punch wheels on (704,256) -- a FULL destination fed from
#: (704,384) -- were both invisible, while stripes on (704,384) banded the on-screen dome.
#: CORRECTED: this caveat used to cite cast 2b's bold wheel (every changed halfword inside the
#: (576,368) band) as the other side, a wheel that "still eroded the vortex smoke at burst peak".  It
#: is not.  The ladder's own capture (`sfxmeshprobe.w6b-cast-ladder.2026-07-28.log`) has DR_MOVE as
#: the first prims of every frame f47-157, and the 4bpp page at (576,256) that holds the wheel's cell
#: is drawn on exactly those frames and no others -- the headless census puts the column-576 blits on
#: the same window -- so the wheel was stock bytes at every draw.  The headless raster renders 2b
#: identical to stock on every frame, and the recorded erosion compared 2b with the thin-wheel cast
#: (both edited), never with stock.  No cast on record has drawn a destination edit; the key stands
#: because the table is static and does not know a cast's draw window.
REACHABILITY = (
    "REACHABILITY IS NOT ESTABLISHED PER CAST: these are static call sites and a blit rewrites its "
    "band only while it runs.  Every in-game check so far sides with the refusal -- on ef211 the "
    "ink and punch wheels on (704,256), a FULL destination fed from (704,384), were both INVISIBLE "
    "while stripes on (704,384) banded the dome on screen (headless, that blit runs over frames "
    "235-284, exactly the frames the 8bpp page sampling (704,256) draws), and the game's own capture "
    "shows the (576,368) band's blit running on every frame its page is drawn (f47-157), ahead of "
    "the first draw, so cast 2b's bold wheel inside it never reached the screen either")

#: what saying :data:`ACK_KEY` means, printed on every build that uses it.
ACK_WARNING = (
    "%s = true: the texels this edit changes inside an op-144 DESTINATION band are rewritten from "
    "the source every frame the blit runs, so while it runs they never reach the screen.  %s.  The "
    "kit counts the changed texels in the band and checks nothing else; the judgement that this "
    "blit is not running when your cell is drawn is yours." % (ACK_KEY, REACHABILITY))

# ---------------------------------------------------------------- THE COUNT PINS (asserted at import)
assert len(_SITE_ROWS) == SITES, len(_SITE_ROWS)
assert len(SCROLL_BLITS) == CONTAINERS, len(SCROLL_BLITS)
assert sum(b.sites for bs in SCROLL_BLITS.values() for b in bs) == SITES
#: the hardware's own fit predicate, which every DESTINATION satisfies -- the evidence ADDENDUM 9
#: shipped the op's naming on (167/167 against 46.0% on the control population).
assert all(b.size[0] > 0 and b.dst[0] + b.size[0] <= VRAM_W and b.dst[1] + b.size[1] <= VRAM_H
           for bs in SCROLL_BLITS.values() for b in bs)
#: ...and the four sites whose folded SOURCE does not fit, named so a fifth cannot appear silently.
assert sorted({b.effect for bs in SCROLL_BLITS.values() for b in bs
               if not b.src_in_vram}) == [22, 95, 222, 418]
