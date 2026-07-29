r"""CHANNEL P (W6b-2) -- THE PROGRAM-DERIVED DEPTH TABLE, and why it DISCLOSES rather than licenses.

W6b-1 closed the scenery texel lane attribution-limited: **2,385 of 2,572 scenery page-cells (92.7%)
have no ``so`` reader**, so the container states no bit depth for them and
:func:`ff9mapkit.summons.repaint.scenery_surface` refuses them by name. W6b-2 asked whether the
container states the depth SOMEWHERE ELSE and found two channels:

* **CHANNEL P** -- the id-3 effect program's own texture-registration call folds a CONSTANT PSX tpage
  word, and a tpage's colour-mode bits ARE the GPU draw mode. **189** of the 2,385 gain a depth this
  way; **22 more, in 10 containers, are named TWICE at two different depths** and are a HAZARD, not a
  vote (:data:`PROGRAM_DUAL_CELLS`). This module is that table;
* **CHANNEL G** -- the container's own ``so`` records re-read at PAGE rather than UV granularity
  (:func:`ff9mapkit.summons.reskin.page_depth_view`). **57** more. It is DERIVED LIVE from the
  container on every call and is deliberately NOT cached here: it needs no disassembly.

  ``189 + 57 = 246``; ``2,385 - 246 = 2,139`` keep refusing by name.

> **THE LINE (W6b2-ATTRIBUTION.md sec 5).**
> **CHANNEL G LICENSES. CHANNEL P DISCLOSES, and edits only behind an explicit acknowledgement.**

THE GRANULARITY STATEMENT, AND ALL THREE OF ITS LINES
-----------------------------------------------------
::

    one texture-page word  =  a 64-halfword x 256-line PAGE
    one census page-cell   =  a 64-halfword x 128-line CELL
                           => one page word names a COLUMN of TWO STACKED CELLS

1. **DEPTH is a property of the PAGE. READERSHIP is a property of the UVs.** Collapsing these two is
   what produced W6b-1's ``y = 384`` blind spot -- the census attributed a record's depth only to the
   cells its stored UVs physically touched, which is the right instrument for readership and the
   wrong one for depth.
2. **A page's draw mode governs all 256 lines FOR A GIVEN DRAW**, so this table attributes a
   recovered page word to BOTH stacked cells of its column -- and the lower half's depth is therefore
   **INHERITED FROM THE COLUMN, never direct** (:attr:`ProgramDepth.inherited`). No instrument has
   seen a model sample those bytes; what is established is the mode under which the page is read.
3. **On this hardware a page can be bound at one depth by one primitive and another by the next**, so
   a page named twice at two depths is the 22-cell hazard class, NOT a contradiction to average away.
   Dropping this third line would license an unsound generalisation the first time someone quotes the
   law without the hazard.

WHY THIS IS A CACHED CONSTANT, AND WHAT PINS IT
------------------------------------------------
The derivation is a MIPS const-folding reachability walk over 385 id-3 program images. A build cannot
afford to re-run it, so -- exactly like :data:`ff9mapkit.summons.repaint.PROGRAM_VRAM_WRITE_IDS` --
the table is a CACHE OF A MEASUREMENT and is **RE-DERIVATION-PINNED**: ``studies/custom-summons/
tier-w/w6b2i_gates.py`` re-rolls it from the sweep artifact plus the corpus and asserts EQUALITY with
this dict, cell for cell. *A constant nobody re-checks is a claim.* The counts below are asserted AT
IMPORT so a truncated table fails loudly instead of quietly attributing fewer cells.

★ AND THE ONE THING THAT MAKES THIS A DISCLOSURE RATHER THAN A LICENCE -- IT WAS TESTED IN-GAME
------------------------------------------------------------------------------------------------
Channel P's own written upgrade path was *"channel P earns LICENSE when a cast proves a
program-derived depth on screen"*. **That trigger fired once and FAILED.** W6b-SCENERY.md sec 5's
cast ladder, on ef251 (Madeen) column x512, tpage 312, program-registered 15bpp, verbatim:

    "REGISTRATION-IS-NOT-A-DRAW, CONFIRMED WITH TEETH: tpage 312's depth bits say 15bpp and the
    surface that draws reads INDEXED -- channel P's LICENSE upgrade path FAILED its first trigger
    cast, and the record's DISCLOSE posture is vindicated by its own test."

The self-diagnosing artifact was three solid ``0x7FFF`` white bands (flat white would mean a 15bpp
read); it came back as a **"BUMPER STRIP"** of fine ridged micro-stripes -- the 4-cycle signature of a
**4bpp** read -- "decisively NOT flat white".

And the same ladder minted the law that generalises it, on ef446 (Atomos), verbatim:

    "THE DEPTH COROLLARY (new law): a census depth is a BINDING fact, not a DRAW fact -- the `so`
    record's 15bpp binds its own (evidently undrawn) model, while the surface that draws the nucleus
    reads the same bytes at 8bpp under the warm CLUT; the fine two-tone checker is the corollary's
    diagnostic signature."

    "THE GHOST-LAYER OBSERVATION (3 vehicles, 6 verdict casts): every 15bpp-attributed scenery cell
    probed so far is either bound-never-drawn (ef429 x2 covers) or drawn at another depth (ef446 at
    8bpp, ef251 indexed) -- 15bpp attributions may systematically name a processed-not-drawn layer."

So a stated depth -- from a binding OR from a registration -- is a fact about the BINDING side, and
the draw can read the same bytes at another depth. That is why an edit on a P-attributed cell unlocks
only behind :data:`ACK_KEY` **plus** an author-stated ``expect_bpp`` that MATCHES this table.
**The author carries the judgement; the kit carries the check.**

PROVENANCE
----------
Cell coordinates, depths, call-site counts, effect ids and counts. **No stock byte, no hex run, no
byte-sequence literal** -- the decoded listings and every recovered constant's provenance stay
outside the checkout, under ``C:\gd\SCRATCH\summon-format\texel-w6b\w6b2\``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

__all__ = [
    "SURFACE_CELLS", "DEPTH_UNKNOWN", "GAIN_PROGRAM", "GAIN_SO_PAGE", "GAIN_EITHER",
    "RESIDUE", "RESIDUE_BLIND", "RESIDUE_COVERED", "PROGRAM_DUAL_CELLS",
    "PROGRAM_DUAL_CONTAINERS", "CHANNEL_G_DUAL_CELLS", "SPILL_CONFLICT_CELLS",
    "REFUSED_AMBIGUOUS", "BLIND_CONTAINERS", "PAGE_LINES", "CELL_LINES",
    "ProgramDepth", "PROGRAM_DEPTH", "program_depth", "clut_arity_hint",
    "ACK_KEY", "REGISTRATION_CAVEAT", "DEPTH_COROLLARY", "ACK_WARNING", "RESIDUE_LINE",
    "GRANULARITY_LAW", "INHERITED_LINE",
]

# ---------------------------------------------------------------- THE COUNT PINS (asserted at import)
#: the non-creature scenery page-cell population W6b-1 measured.
SURFACE_CELLS = 2572
#: ...of which no ``so`` record samples, so W6b-1 refused them by name (92.7%).
DEPTH_UNKNOWN = 2385
#: CHANNEL P's gain: depth-unknown cells a recovered program tpage names UNANIMOUSLY.
GAIN_PROGRAM = 189
#: CHANNEL G's gain: depth-unknown cells whose COLUMN carries exactly one ``so``-stated depth.
GAIN_SO_PAGE = 57
GAIN_EITHER = GAIN_PROGRAM + GAIN_SO_PAGE
#: the cells that keep refusing by name after both channels have spoken.
RESIDUE = DEPTH_UNKNOWN - GAIN_EITHER
#: THE STRUCTURAL CEILING: 222 containers declare ZERO non-creature GEOM blocks, have no model to
#: register a texture onto, and make ZERO such calls -- they hold this many of the unknown cells and
#: gain 0.  The lever is silent exactly where the census is blind, which is why the 10.31% MUST NOT be
#: projected forward onto the 92.7% surface.
RESIDUE_BLIND = 1278
#: how many containers that is -- named, because the ceiling is a property of THEM, not of the scan.
BLIND_CONTAINERS = 222
#: ...and the rest: cells in 135 model-BEARING containers that no recovered page word and no ``so``
#: page covers.  The sharpest warning in the corpus lives here -- one container has 73 GEOM blocks,
#: 750 resolved engine calls and 34 page-word-shaped immediates while making ZERO registration calls,
#: which is why :data:`GAIN_PROGRAM` is a FLOOR and not a ceiling.
RESIDUE_COVERED = 861
#: THE THREE REFUSAL CLASSES THIS RUNG MINTS -- three different populations, never added up.
PROGRAM_DUAL_CELLS = 22           # INSIDE the 2,385 (a subset of the 861), in 10 containers
PROGRAM_DUAL_CONTAINERS = 10
CHANNEL_G_DUAL_CELLS = 8          # INSIDE the 2,385, disjoint from the 22; named in NO lane dossier
SPILL_CONFLICT_CELLS = 2          # OUTSIDE the 2,385 entirely: they HAD a depth and now have two
REFUSED_AMBIGUOUS = PROGRAM_DUAL_CELLS + CHANNEL_G_DUAL_CELLS + SPILL_CONFLICT_CELLS

#: a VRAM texture PAGE is 256 lines; a census page-cell is 128.  One page word names TWO stacked cells.
PAGE_LINES, CELL_LINES = 256, 128


@dataclass(frozen=True)
class ProgramDepth:
    """What the container's OWN id-3 program registers for one VRAM page-cell.

    ``bpp is None`` is NOT "no evidence" -- it is the PROGRAM-DUAL-DEPTH HAZARD: the program names
    this column at two different depths, and **unanimity is the verdict rule; two values is a hazard,
    not a vote**. The kit refuses such a cell by name and no acknowledgement lifts it, because the
    hazard is about the EVIDENCE and the ack is about the AUTHOR's judgement of a single-valued one.
    """
    effect: int
    cell: Tuple[int, int]
    #: the UNANIMOUS depth, or ``None`` when the program names two -> a REFUSAL, never a majority.
    bpp: Optional[int]
    #: every depth the program's own recovered constants name for this cell's COLUMN.
    depths: Tuple[int, ...]
    #: how many op-22 call sites fold to a page word covering this cell.
    call_sites: int

    @property
    def dual(self) -> bool:
        return self.bpp is None

    @property
    def inherited(self) -> bool:
        """THE SECOND LINE OF THE GRANULARITY LAW, per cell: this is the LOWER half of the column, so
        its depth crossed a cell boundary to get here -- inherited from the page word, never read off
        anything that names this cell. (The THIRD line is the dual-depth hazard, :attr:`dual`.)"""
        return bool(self.cell[1] % PAGE_LINES)

    @property
    def evidence(self) -> str:
        """The DISCLOSURE sentence a refusal quotes -- what the container states, in one line."""
        if self.dual:
            return ("ef%03d's own id-3 program registers this page at %s bpp at %d call site(s) -- "
                    "TWO different depths for one column"
                    % (self.effect, "/".join(str(d) for d in self.depths), self.call_sites))
        return ("the container's own program registers this page at %d bpp at %d call site(s)%s"
                % (self.bpp, self.call_sites,
                   "; this cell is the LOWER half of that column, so the depth is INHERITED FROM THE "
                   "COLUMN, never direct" if self.inherited else ""))


#: THE GRANULARITY LAW, in one quotable line -- carried as a constant because every refusal that
#: attributes a depth to a stacked cell has to be able to say WHY it may.
GRANULARITY_LAW = (
    "DEPTH is a property of the PAGE; READERSHIP is a property of the UVs.  One 64x256 page word "
    "names a COLUMN of two stacked 64x128 cells, and a page drawn twice at two depths is a HAZARD "
    "class, not a contradiction")

#: what a cell whose depth came off the column rather than off itself must always say out loud.
INHERITED_LINE = ("this cell is the LOWER half of its column, so its depth is INHERITED FROM THE "
                  "COLUMN, never direct -- no instrument has seen a model sample these bytes; what "
                  "is established is the mode under which the page they live in is read")

#: ★ THE IN-GAME REFUTATION, carried at every call site that discloses a program-derived depth.
#: W6b-1 minted BINDING-IS-NOT-A-DRAW at the cost of two negative playtests; W6b-2's own upgrade
#: trigger then fired ONCE and FAILED.  A constant, not a docstring, because a caveat nothing quotes
#: is a wish.
REGISTRATION_CAVEAT = (
    "REGISTRATION-IS-NOT-A-DRAW, CONFIRMED IN-GAME: the FIRST cast to put a program-derived depth on "
    "screen refuted it.  ef251 (Madeen) column x512, program-registered tpage 312 = 15bpp, was cast "
    "with solid 0x7FFF words -- flat white would have meant a 15bpp read -- and drew a 4-cycle "
    "'BUMPER STRIP' of fine ridged micro-stripes, i.e. a 4bpp read.  Channel P's own LICENSE upgrade "
    "path FAILED its first trigger cast, which is why this DISCLOSES and does not license")

#: ★ THE DEPTH COROLLARY (W6b-SCENERY sec 5, the ef446 ladder), quoted because it is the general form
#: of the same finding and it applies to the ``so`` census too, not only to the program channel.
DEPTH_COROLLARY = (
    "THE DEPTH COROLLARY: a stated depth is a BINDING-side fact, not a DRAW fact -- on ef446 the "
    "`so` record's 15bpp bound its own (evidently undrawn) model while the surface that draws the "
    "nucleus read the SAME BYTES at 8bpp under the warm CLUT, and the fine two-tone checker is the "
    "corollary's diagnostic signature.  A depth the container states is the depth something BINDS "
    "at; the draw can read the same bytes at another")

#: the residue split, in the words every depth refusal ends with.  The arithmetic is asserted below.
RESIDUE_LINE = (
    "THE RESIDUE, SPLIT: %s of %s scenery cells were depth-unknown; %d gain a depth in W6b-2 "
    "(%d program + %d `so`-at-page) and %s keep refusing -- %s inside the %d containers that declare "
    "no model at all (their programs register nothing: a STRUCTURAL ceiling, not a scanner "
    "shortfall) and %d in 135 model-BEARING containers the lever does not cover"
    % ("{:,}".format(DEPTH_UNKNOWN), "{:,}".format(SURFACE_CELLS), GAIN_EITHER, GAIN_PROGRAM,
       GAIN_SO_PAGE, "{:,}".format(RESIDUE), "{:,}".format(RESIDUE_BLIND), BLIND_CONTAINERS,
       RESIDUE_COVERED))

#: THE SPEC KEY.  Literal-boolean-only, like every other acknowledgement in this lane.
ACK_KEY = "acknowledge_program_derived_depth"

#: what saying it means, printed on every build that uses it.
ACK_WARNING = (
    "%s = true: this cell's depth comes from CHANNEL P -- a constant page word folded out of the "
    "container's own id-3 program -- and NOT from any `so` reader.  %s  %s  The kit checks that your "
    "`expect_bpp` matches the derivation and checks nothing else; the judgement that this depth is "
    "the depth the SCREEN reads is yours." % (ACK_KEY, REGISTRATION_CAVEAT, DEPTH_COROLLARY))


# ---------------------------------------------------------------- THE TABLE
# ``(effect, cell x, cell y, bpp, call sites)`` -- one row per CENSUS-DECLARED cell a recovered page
# word covers, UNANIMOUS tier.  Both stacked cells of a column appear whenever the container declares
# both; a column whose lower half it never uploads contributes only its upper cell.
_SINGLE_ROWS = (
    (1, 704, 256, 4, 2),
    (1, 704, 384, 4, 2),
    (4, 640, 256, 8, 5),
    (4, 640, 384, 8, 5),
    (6, 512, 256, 8, 1),
    (6, 512, 384, 8, 1),
    (6, 640, 256, 8, 3),
    (6, 640, 384, 8, 3),
    (7, 448, 256, 4, 2),
    (7, 448, 384, 4, 2),
    (14, 512, 256, 15, 1),
    (14, 512, 384, 15, 1),
    (22, 576, 256, 4, 6),
    (22, 576, 384, 4, 6),
    (22, 704, 256, 4, 2),
    (22, 704, 384, 4, 2),
    (24, 512, 256, 8, 1),
    (24, 512, 384, 8, 1),
    (24, 576, 256, 15, 1),
    (24, 576, 384, 15, 1),
    (52, 576, 256, 8, 1),
    (52, 576, 384, 8, 1),
    (52, 640, 256, 8, 1),
    (62, 512, 256, 8, 1),
    (62, 512, 384, 8, 1),
    (62, 640, 256, 8, 3),
    (62, 640, 384, 8, 3),
    (72, 448, 256, 4, 2),
    (72, 448, 384, 4, 2),
    (77, 640, 256, 8, 5),
    (77, 640, 384, 8, 5),
    (79, 448, 256, 15, 2),
    (79, 448, 384, 15, 2),
    (87, 448, 256, 15, 1),
    (87, 448, 384, 15, 1),
    (87, 576, 256, 8, 1),
    (87, 576, 384, 8, 1),
    (90, 448, 256, 15, 1),
    (90, 448, 384, 15, 1),
    (93, 448, 256, 8, 1),
    (93, 448, 384, 8, 1),
    (95, 576, 256, 4, 6),
    (95, 576, 384, 4, 6),
    (95, 704, 256, 4, 2),
    (95, 704, 384, 4, 2),
    (98, 448, 256, 15, 1),
    (98, 448, 384, 15, 1),
    (99, 448, 256, 15, 1),
    (99, 448, 384, 15, 1),
    (120, 448, 256, 8, 1),
    (120, 448, 384, 8, 1),
    (125, 512, 256, 4, 1),
    (125, 512, 384, 4, 1),
    (125, 576, 256, 15, 1),
    (125, 576, 384, 15, 1),
    (125, 768, 256, 15, 1),
    (125, 768, 384, 15, 1),
    (126, 704, 256, 8, 1),
    (126, 704, 384, 8, 1),
    (127, 448, 256, 8, 1),
    (127, 448, 384, 8, 1),
    (127, 576, 256, 15, 1),
    (127, 576, 384, 15, 1),
    (129, 448, 256, 15, 1),
    (129, 448, 384, 15, 1),
    (129, 576, 256, 8, 1),
    (129, 576, 384, 8, 1),
    (131, 512, 256, 8, 1),
    (131, 512, 384, 8, 1),
    (131, 640, 256, 8, 1),
    (131, 640, 384, 8, 1),
    (133, 512, 256, 8, 1),
    (133, 512, 384, 8, 1),
    (133, 576, 256, 15, 1),
    (133, 576, 384, 15, 1),
    (134, 448, 256, 8, 1),
    (134, 448, 384, 8, 1),
    (134, 640, 256, 8, 1),
    (134, 640, 384, 8, 1),
    (134, 768, 256, 4, 1),
    (134, 768, 384, 4, 1),
    (140, 512, 256, 15, 1),
    (140, 512, 384, 15, 1),
    (142, 704, 256, 4, 2),
    (142, 704, 384, 4, 2),
    (143, 448, 256, 8, 1),
    (143, 448, 384, 8, 1),
    (143, 640, 256, 8, 1),
    (143, 640, 384, 8, 1),
    (143, 768, 256, 4, 1),
    (143, 768, 384, 4, 1),
    (144, 704, 256, 4, 2),
    (144, 704, 384, 4, 2),
    (151, 640, 256, 8, 7),
    (151, 640, 384, 8, 7),
    (152, 640, 256, 8, 7),
    (152, 640, 384, 8, 7),
    (177, 448, 256, 15, 1),
    (177, 448, 384, 15, 1),
    (184, 384, 256, 8, 2),
    (184, 384, 384, 8, 2),
    (184, 640, 256, 4, 2),
    (184, 640, 384, 4, 2),
    (184, 704, 256, 8, 1),
    (184, 704, 384, 8, 1),
    (184, 768, 256, 15, 5),
    (184, 768, 384, 15, 5),
    (201, 448, 256, 15, 1),
    (201, 448, 384, 15, 1),
    (214, 448, 256, 4, 2),
    (214, 448, 384, 4, 2),
    (217, 512, 256, 8, 1),
    (217, 512, 384, 8, 1),
    (217, 576, 256, 15, 1),
    (217, 576, 384, 15, 1),
    (218, 512, 256, 8, 1),
    (218, 512, 384, 8, 1),
    (218, 640, 256, 8, 3),
    (218, 640, 384, 8, 3),
    (219, 640, 256, 8, 5),
    (219, 640, 384, 8, 5),
    (220, 640, 256, 8, 7),
    (220, 640, 384, 8, 7),
    (221, 448, 256, 8, 1),
    (221, 448, 384, 8, 1),
    (222, 576, 256, 4, 6),
    (222, 576, 384, 4, 6),
    (222, 704, 256, 4, 2),
    (222, 704, 384, 4, 2),
    (223, 512, 256, 4, 1),
    (223, 512, 384, 4, 1),
    (223, 576, 256, 15, 1),
    (223, 576, 384, 15, 1),
    (223, 768, 256, 15, 1),
    (223, 768, 384, 15, 1),
    (224, 448, 256, 4, 2),
    (224, 448, 384, 4, 2),
    (224, 768, 256, 8, 1),
    (224, 768, 384, 8, 1),
    (230, 448, 256, 8, 1),
    (236, 448, 256, 8, 4),
    (236, 448, 384, 8, 4),
    (242, 640, 256, 15, 1),
    (244, 640, 256, 15, 2),
    (244, 640, 384, 15, 2),
    (250, 640, 256, 8, 1),
    (250, 640, 384, 8, 1),
    (251, 384, 256, 8, 2),
    (251, 384, 384, 8, 2),
    (251, 512, 256, 15, 1),
    (251, 512, 384, 15, 1),
    (251, 768, 256, 4, 1),
    (251, 768, 384, 4, 1),
    (257, 448, 256, 8, 1),
    (257, 448, 384, 8, 1),
    (265, 448, 256, 8, 1),
    (266, 448, 256, 8, 1),
    (267, 448, 256, 8, 1),
    (268, 448, 256, 8, 1),
    (269, 448, 256, 8, 1),
    (270, 448, 256, 8, 1),
    (271, 448, 256, 8, 1),
    (272, 448, 256, 8, 1),
    (274, 448, 256, 15, 1),
    (274, 448, 384, 15, 1),
    (276, 640, 256, 8, 3),
    (276, 640, 384, 8, 3),
    (291, 448, 256, 8, 2),
    (291, 448, 384, 8, 2),
    (308, 448, 256, 4, 2),
    (308, 448, 384, 4, 2),
    (308, 768, 256, 8, 1),
    (308, 768, 384, 8, 1),
    (312, 576, 256, 8, 1),
    (312, 576, 384, 8, 1),
    (377, 640, 256, 8, 1),
    (377, 640, 384, 8, 1),
    (378, 512, 256, 15, 1),
    (378, 512, 384, 15, 1),
    (394, 448, 256, 8, 1),
    (394, 448, 384, 8, 1),
    (408, 448, 256, 15, 1),
    (408, 448, 384, 15, 1),
    (418, 512, 256, 8, 5),
    (418, 512, 384, 8, 5),
    (418, 640, 256, 8, 3),
    (418, 640, 384, 8, 3),
    (434, 448, 256, 15, 1),
    (434, 448, 384, 15, 1),
    (434, 576, 256, 15, 1),
    (434, 576, 384, 15, 1),
    (445, 640, 256, 8, 2),
    (445, 640, 384, 8, 2),
    (460, 640, 256, 8, 7),
    (460, 640, 384, 8, 7),
    (489, 448, 256, 8, 1),
    (489, 448, 384, 8, 1),
    (504, 448, 256, 15, 1),
    (504, 448, 384, 15, 1),
)

# ``(effect, cell x, cell y, call sites, depth, depth)`` -- the PROGRAM-DUAL-DEPTH hazard class: 22
# cells in 10 containers the program names at TWO depths.  Carried in the SAME table as the unanimous
# rows on purpose: a refusal that lives in a different structure from the attribution it refuses is a
# refusal that can be forgotten by a caller that only reads one of them.
_DUAL_ROWS = (
    (56, 448, 256, 2, 8, 15),
    (56, 448, 384, 2, 8, 15),
    (134, 576, 256, 2, 8, 15),
    (134, 576, 384, 2, 8, 15),
    (143, 576, 256, 2, 8, 15),
    (143, 576, 384, 2, 8, 15),
    (224, 512, 256, 3, 8, 15),
    (224, 512, 384, 3, 8, 15),
    (236, 576, 256, 2, 4, 15),
    (236, 576, 384, 2, 4, 15),
    (251, 640, 256, 5, 4, 8),
    (251, 640, 384, 5, 4, 8),
    (251, 832, 256, 6, 4, 8),
    (251, 832, 384, 6, 4, 8),
    (276, 448, 256, 3, 4, 15),
    (276, 448, 384, 3, 4, 15),
    (308, 512, 256, 3, 8, 15),
    (308, 512, 384, 3, 8, 15),
    (378, 640, 256, 3, 4, 8),
    (378, 640, 384, 3, 4, 8),
    (445, 448, 256, 2, 4, 15),
    (445, 448, 384, 2, 4, 15),
)


def _build() -> Dict[Tuple[int, int, int], ProgramDepth]:
    out: Dict[Tuple[int, int, int], ProgramDepth] = {}
    for ef, x, y, bpp, sites in _SINGLE_ROWS:
        out[(ef, x, y)] = ProgramDepth(effect=ef, cell=(x, y), bpp=bpp, depths=(bpp,),
                                       call_sites=sites)
    for ef, x, y, sites, d0, d1 in _DUAL_ROWS:
        if (ef, x, y) in out:                                    # pragma: no cover - by construction
            raise AssertionError("a cell cannot be both unanimous and dual: %r" % ((ef, x, y),))
        out[(ef, x, y)] = ProgramDepth(effect=ef, cell=(x, y), bpp=None,
                                       depths=(d0, d1), call_sites=sites)
    return out


#: ``{(effect, cell x, cell y): ProgramDepth}`` -- every census-declared cell channel P speaks for.
PROGRAM_DEPTH: Dict[Tuple[int, int, int], ProgramDepth] = _build()


def program_depth(effect: Optional[int], cell: Tuple[int, int]) -> Optional[ProgramDepth]:
    """Channel P's record for one cell, or ``None`` when the program is SILENT there.

    ``effect is None`` answers ``None`` and that is not a synonym for "clean": the table is keyed by
    effect id, so a derivation handed bare bytes with no id genuinely does not know -- the same law
    :func:`ff9mapkit.summons.repaint.program_class` states for the VRAM-write lists.
    """
    if effect is None:
        return None
    return PROGRAM_DEPTH.get((int(effect), int(cell[0]), int(cell[1])))


def clut_arity_hint(n_clut4: int, n_clut8: int) -> Optional[int]:
    """CHANNEL H -- the container's OWN id-0 ``nClut4`` / ``nClut8`` arity, as a **NARROWING**.

    ``hint == 4`` means *"this container ships no 8-entry-per-byte CLUT, so this page is 4 bpp **or**
    15 bpp"*. It is not a depth and it licenses no decode: measured over the corpus it speaks for 351
    of the 2,385 unknown cells, corroborates 17 of the 246 attributed ones at 0 conflicts, and breaks
    **0 of the 30** dual-depth ties -- a clean negative, recorded so nobody tries.

    What it IS good for is the refusal's own honesty: *"the container states nothing about this cell"*
    is FALSE for 334 of the residue's cells, and the reason string should say which of the two it
    means. Derived live from the container, never cached.
    """
    if n_clut4 == 0 and n_clut8:
        return 8
    if n_clut8 == 0 and n_clut4:
        return 4
    return None


# ---------------------------------------------------------------- THE PINS, ASSERTED AT IMPORT
# A truncated or half-pasted table must fail LOUDLY here rather than quietly attributing fewer cells
# than the record claims -- the failure mode a cached measurement actually has.
_UNANIMOUS = tuple(v for v in PROGRAM_DEPTH.values() if not v.dual)
_DUAL = tuple(v for v in PROGRAM_DEPTH.values() if v.dual)
assert len(_DUAL) == PROGRAM_DUAL_CELLS, len(_DUAL)
assert len({v.effect for v in _DUAL}) == PROGRAM_DUAL_CONTAINERS
assert all(len(v.depths) == 2 and v.depths[0] != v.depths[1] for v in _DUAL)
assert all(v.bpp in (4, 8, 15) for v in _UNANIMOUS)
assert all(d in (4, 8, 15) for v in _DUAL for d in v.depths)
assert all(v.call_sites >= 1 for v in PROGRAM_DEPTH.values())
assert all(v.cell[1] % CELL_LINES == 0 for v in PROGRAM_DEPTH.values())
#: the 199 unanimous rows are the 189 depth-unknown GAINS plus the 10 cells the ``so`` census already
#: had a depth for -- P's whole ground truth, which is scarce BY CONSTRUCTION because the program
#: speaks precisely where the census is quiet (112 of the 121 pages it names carry no ``so`` record).
assert len(_UNANIMOUS) == GAIN_PROGRAM + 10, len(_UNANIMOUS)
assert GAIN_PROGRAM + GAIN_SO_PAGE == GAIN_EITHER == 246
assert GAIN_EITHER + RESIDUE_BLIND + RESIDUE_COVERED == DEPTH_UNKNOWN
assert DEPTH_UNKNOWN - GAIN_EITHER == RESIDUE == 2139
assert REFUSED_AMBIGUOUS == 32
