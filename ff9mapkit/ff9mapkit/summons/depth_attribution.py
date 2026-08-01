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
    # ---- W6b-3: CHANNEL A (`so-array`).  ADDITIVE ONLY -- no constant above moves and no import-time
    # assert above changes, because channel A is NOT ADOPTED and W6b-2's arithmetic still describes
    # the shipped surface exactly.
    "ACK_ARRAY_KEY", "ORDER_UNMEASURED", "ARRAY_CAVEAT", "ARRAY_ACK_WARNING", "ARRAY_RESIDUE_LINE",
    "GAIN_ARRAY", "ARRAY_MULTIVALUED_CELLS", "ARRAY_IN_REACH_DUAL", "ARRAY_COLUMN_CONFLICT_CELLS",
    "ARRAY_CLASS_C", "ARRAY_CLEAN", "ARRAY_PROGRAM_WRITE", "ARRAY_DEFLATION_OVERLAP",
    "A2_SCOPE_NOTE",
    # ---- W6b-3 (iii): THE SECOND ARRAY, DISCLOSED.  ADDITIVE ONLY, on exactly the terms channel A
    # was: no constant above moves, no import-time assert above changes, and NOTHING here enters a
    # depth, a cover, a page or an emitted byte.  This is a DISCLOSURE about READERSHIP, which is a
    # different question from every depth channel in this module.
    "ACK_MOVER_KEY", "U_DISPLACEMENT_CAVEAT", "U_DISPLACEMENT_ACK_WARNING",
    "SECOND_ARRAY_MOVER_CELLS", "SECOND_ARRAY_MOVER_OPEN", "SECOND_ARRAY_MOVER_CONTAINERS",
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

# ================================================================ W6b-3: CHANNEL A -- `so-array`
# ★ A IS FOR **ARRAY**, NOT ARCHIVE.  W6b-3 opened on the hypothesis that an id-2 SUB-FILE ARCHIVE
# held an unread model; the recon FALSIFIED the premise (`reskin.attribution` already walks every
# sub-file id) and found the blindness in the RECORD READER instead: the `so` record is a MULTI-PART
# BINDING ARRAY and the reader hard-probed two lengths.  The 126 records it could not read split
# id-2 61 / id-6 53 / id-3 12, so "the archive channel" would be the wrong name on 65 of 126.
#
# ⚠ **CHANNEL A DISCLOSES AT CHANNEL P's TIER, AND FOR A HARSHER REASON.**  Channel P discloses
# because its one in-game trial FAILED.  Channel A has had NO trial at all that it passed: see
# :data:`ARRAY_CAVEAT`.  Nothing below is ADOPTED, which is exactly why :data:`RESIDUE_LINE`,
# :data:`GAIN_EITHER`, :data:`RESIDUE` and every import-time assert in this module are UNCHANGED.

#: THE SPEC KEY for channel A.  Literal-boolean-only, and -- like :data:`ACK_KEY` -- it admits a
#: FACT rather than arming an obligation the author already discharged, so the build path also
#: demands a matching ``expect_bpp``; on its own it is refused BY NAME.
ACK_ARRAY_KEY = "acknowledge_array_derived_depth"

#: ★ THE ORDER CLAUSE, carried as a constant because a caveat that travels separately from the
#: number is a caveat nobody reads.  Quoted by the ``so-array`` disclosure, the
#: ack-without-``expect_bpp`` refusal, :data:`ARRAY_ACK_WARNING` and the report block.
ORDER_UNMEASURED = (
    "THE ARITY IS MEASURED TWICE; THE ORDER IS NOT, AND THE KIT SHIPS ONLY THE ARITY.  The `so` "
    "record's array is 'selected by the primitive's part byte', which states an arity AND an order.  "
    "The ARITY is corroborated from outside the record's own header twice -- the part-byte range "
    "test (0 of 502 records has max(part) >= P, and a stride-8 reading over-runs on 126 of 126) and "
    "the CLUT-arity test (264/264 against a 16.2% random floor and a 53.3% ambient).  THE ORDER IS "
    "CORROBORATED BY NOTHING: the best available discriminator scores identity 63.3% / reversed "
    "56.0% / random permutations 59.4%, about 0.9 sigma above chance, and 82 of the 126 multi-part "
    "records name more than one distinct tpage.  So `parts` is a SET everywhere in this kit: a "
    "reason string may name a record offset and a slot index as IDENTIFICATION, and no verdict may "
    "assert that part k draws with entry k")

#: ★ WHAT CHANNEL A's IN-GAME STANDING ACTUALLY IS: nothing.  The rung's own ghost-layer prediction
#: was scored cell by cell and did not land once.
ARRAY_CAVEAT = (
    "NOTHING ABOUT CHANNEL A IS IN-GAME.  The ghost-layer prediction this channel was recruited to "
    "explain scored 0 HITS, 4 MISSES and 2 VACUOUS PASSES over six named cells -- so the multi-part "
    "reading has never put a texel on screen and has never been refuted there either.  "
    "BINDING-IS-NOT-A-DRAW and THE DEPTH COROLLARY apply in full: what the array states is what "
    "something BINDS at, and the draw can read the same bytes at another depth")

#: what saying :data:`ACK_ARRAY_KEY` means, printed on every build that uses it.
ARRAY_ACK_WARNING = (
    "%s = true: this cell's depth comes from CHANNEL A -- an entry of the container's own `so` "
    "record's BINDING ARRAY that no kit before W6b-3 could read -- and NOT from any `so` reader's "
    "UVs and not from the program.  %s  %s  %s  The kit checks that your `expect_bpp` matches the "
    "derivation and checks nothing else; the judgement that this depth is the depth the SCREEN reads "
    "is yours." % (ACK_ARRAY_KEY, ARRAY_CAVEAT, DEPTH_COROLLARY, ORDER_UNMEASURED))

#: CHANNEL A's disclosure surface: depth-unknown cells whose column the multi-part reading names
#: UNANIMOUSLY.  **Re-derivation-pinned** -- ``w6b3i_gates`` I9 re-rolls it from the 372 containers
#: through :func:`ff9mapkit.summons.reskin.array_depth_view` and asserts equality, the repair this
#: module's own self-consistent ``GAIN_PROGRAM + GAIN_SO_PAGE == GAIN_EITHER`` assert could never
#: have made for itself.  *A constant nobody re-checks is a claim.*
GAIN_ARRAY = 65

#: THE MULTI-VALUED HAZARD: cells whose column carries MORE THAN ONE depth across its NOVEL slots.
#: 6 columns x 2 stacked cells.  **All 12 REFUSE outright** on any path that consults ``so-array``.
#: Re-derivation-pinned (``w6b3i_gates`` I6).
ARRAY_MULTIVALUED_CELLS = 12
#: ...of which the column's INCUMBENT depth set is EMPTY -- the exact derived predicate behind the
#: 8/4 structure the refusal text prints.  ⚠ **The SPLIT is informative; the TREATMENT is UNIFORM.**
#: The other 4 sit on columns channel G already covers, and their refusal DISPLACES that service
#: rather than being stated alongside it: channel A holds VETO power (the conservative direction),
#: never emission power.  This constant survives as the split's DERIVATION count, not as a policy.
ARRAY_IN_REACH_DUAL = 8
#: THE COLUMN CONFLICT: a column with a UNANIMOUS incumbent depth AND a UNANIMOUS novel depth that
#: DIFFER -- ef184 x448, the only column in the corpus satisfying the predicate, 2 stacked cells.
#: These are the rung's ONE deliberate permissiveness regression: they are LICENSED today.
ARRAY_COLUMN_CONFLICT_CELLS = 2
#: of :data:`GAIN_ARRAY`, how many sit on a column bound with 2-4 DISTINCT CLUT words (class C).
#: Derived from the BINDERS, never from the census's ``hz_multi_palette``: that flag is
#: READER-derived and 65/65 of these cells are readerless, so its clean 0 is VACUOUS, not a clear.
ARRAY_CLASS_C = 34
#: ...and how many sit in a container whose own id-3 program WRITES VRAM at run time.  A CONSTANT
#: rather than a literal inside :data:`ARRAY_RESIDUE_LINE`, and re-derivation-pinned with the rest
#: (``w6b3i_gates`` I5/I9): a number nobody re-checks is a claim, and this module exists to repair
#: exactly that shape.
ARRAY_PROGRAM_WRITE = 7
#: ⚠ THE TWO DEFLATING CLASSES OVERLAP, so the three buckets are NOT addends.  Stated as its own
#: constant so :data:`ARRAY_RESIDUE_LINE` can say it rather than leave ``26 + 34 + 7 == 67 > 65`` for
#: a reader to trip over -- the same law :data:`~ff9mapkit.summons.repaint.W6B_REASON` states in caps
#: for the dual-depth populations.
ARRAY_DEFLATION_OVERLAP = 2
#: ...and how many clear class C and the program-VRAM verdicts both.  THE REACH's real bottom line.
ARRAY_CLEAN = 26

#: ★ A SECOND RESIDUE LINE, NEVER RECONCILED WITH THE FIRST.  :data:`RESIDUE_LINE` describes the
#: SHIPPED surface and does not move, because channel A is NOT adopted.  This one states the
#: counterfactual so the disclosure can say what the ack would buy without pretending it was bought.
#: (The two-scopes precedent is ``w6b2i_gates`` I1.)
ARRAY_RESIDUE_LINE = (
    "IF CHANNEL A WERE ADOPTED the residue would move %s -> %s (%d more cells gain a depth).  IT IS "
    "NOT ADOPTED: `so-array` is CONSULTED, it emits only behind `%s` plus a matching `expect_bpp`, "
    "and the shipped residue is still %s.  Of the %d, %d are clean, %d sit on a class-C column and "
    "%d are in a container whose own program writes VRAM at run time -- READ THE POPULATION AND DO "
    "NOT ADD THEM UP: the last two OVERLAP on %d cell(s), so the three buckets close as "
    "%d + %d + %d - %d == %d"
    % ("{:,}".format(RESIDUE), "{:,}".format(RESIDUE - GAIN_ARRAY), GAIN_ARRAY, ACK_ARRAY_KEY,
       "{:,}".format(RESIDUE), GAIN_ARRAY, ARRAY_CLEAN, ARRAY_CLASS_C, ARRAY_PROGRAM_WRITE,
       ARRAY_DEFLATION_OVERLAP, ARRAY_CLEAN, ARRAY_CLASS_C, ARRAY_PROGRAM_WRITE,
       ARRAY_DEFLATION_OVERLAP,
       ARRAY_CLEAN + ARRAY_CLASS_C + ARRAY_PROGRAM_WRITE - ARRAY_DEFLATION_OVERLAP))

#: ★★ **THE SCOPE CLAUSE THE W6b-2 COUNTS NOW OWE THE READER**, carried as a call-sited constant.
#:
#: :data:`GAIN_SO_PAGE`, :data:`CHANNEL_G_DUAL_CELLS`, :data:`REFUSED_AMBIGUOUS`,
#: :data:`RESIDUE_LINE` and :data:`~ff9mapkit.summons.repaint.W6B_REASON` all measure the surface
#: ``LICENSED_CHANNELS`` emitted at W6b-2 -- ``("so-uv", "so-page", "program")``. **None of them
#: moves**, and that is deliberate: channel A is DISCLOSED, never adopted, so nothing it discloses
#: belongs in an adopted count. But W6b-3 put ``"so-array"`` into that same channel set, and channel
#: A holds VETO power, so on the path an author actually walks a handful of cells resolve
#: differently. A number that does not say which surface it describes is a stale string waiting to
#: happen -- so the numbers stay put and **the scope is stated beside them**.
#:
#: The delta is spelled from the channel's own re-derivation-pinned constants rather than restated as
#: fresh literals, because restating it would mint exactly the un-re-derived count this module exists
#: to refuse. Whether A2's uniform refusal is permanent is an owner ratification, and the day it is
#: settled this clause is what says which numbers have to move.
A2_SCOPE_NOTE = (
    "** SCOPE OF THE COUNTS ABOVE: they measure the W6b-2 CHANNEL SET (`so-uv`, `so-page`, "
    "`program`), where they are EXACT.  The shipped `LICENSED_CHANNELS` also consults CHANNEL A, "
    "whose two hazard classes hold VETO power and never emission power, so on that path %d cell(s) "
    "resolve NO page that these counts include (%d `array-vs-column-depth` + %d `array-dual-depth` "
    "on columns another channel already served) and %d more refuse under the sharper "
    "`array-dual-depth` name instead of `depth-unknown`.  CHANNEL A IS DISCLOSED, NEVER ADOPTED, so "
    "none of the counts above moves; W6b-3 states the delta rather than restating them"
    % (ARRAY_COLUMN_CONFLICT_CELLS + (ARRAY_MULTIVALUED_CELLS - ARRAY_IN_REACH_DUAL),
       ARRAY_COLUMN_CONFLICT_CELLS, ARRAY_MULTIVALUED_CELLS - ARRAY_IN_REACH_DUAL,
       ARRAY_IN_REACH_DUAL))

#: what saying it means, printed on every build that uses it.
ACK_WARNING = (
    "%s = true: this cell's depth comes from CHANNEL P -- a constant page word folded out of the "
    "container's own id-3 program -- and NOT from any `so` reader.  %s  %s  The kit checks that your "
    "`expect_bpp` matches the derivation and checks nothing else; the judgement that this depth is "
    "the depth the SCREEN reads is yours." % (ACK_KEY, REGISTRATION_CAVEAT, DEPTH_COROLLARY))

# ======================================================= W6b-3 (iii): THE SECOND ARRAY, DISCLOSED
# ★ NOT A DEPTH CHANNEL, AND THAT IS THE WHOLE POINT.  Every constant above answers *"at what depth
# are these bytes read?"*; this one answers *"is this cell read AT ALL?"* -- so it deliberately gets
# no `DEPTH_SOURCES` token, no `expect_bpp` pairing and no place in any residue arithmetic.  The `so`
# record's SECOND array (the `P x {u16, u16}` block at `+arrayB` that `so_record` walked past and
# discarded until this rung) is, since U1's s77 byte-stream read, a MEASURED PER-SLOT TEXEL
# DISPLACEMENT -- pair position 0 onto u, pair position 1 onto v -- on ONE container.  The kit still
# models NOTHING with it: it reads the halfwords, states them, and refuses -- behind a key -- a cell
# ALL of whose readers carry one.  `SURFACE_CELLS`, `DEPTH_UNKNOWN`, `GAIN_PROGRAM`, `GAIN_SO_PAGE`,
# `GAIN_ARRAY`, `RESIDUE_LINE` and `ARRAY_RESIDUE_LINE` are all exactly as true after this rung as
# before it, and the s77 read moved none of them either.

#: THE SPEC KEY for the second-array disclosure.  Literal-boolean-only, like every other
#: acknowledgement in this lane.  It admits nothing about a DEPTH and demands no ``expect_bpp``: what
#: it acknowledges is that the cell's READERSHIP may not be what the container's own binding says.
ACK_MOVER_KEY = "acknowledge_second_array_displacement"

#: ★ THE CONDITIONALITY, CARRIED AS A CALL-SITED CONSTANT -- a caveat nothing quotes is a wish, and
#: this one has FIVE open riders that a one-line summary would collapse.  ⚠ It is spent through
#: :func:`~ff9mapkit.summons.repaint._refusal`'s ``txt % detail`` path, so it may never contain a
#: literal ``%``: that is how a measurement quietly becomes a typo.
U_DISPLACEMENT_CAVEAT = (
    "THE SECOND ARRAY DISPLACES THE SAMPLED TEXEL, AND THE MECHANISM IS MEASURED -- ON ONE "
    "CONTAINER, AT 0.97, AND THIS KIT STILL MODELS NOTHING WITH IT.  One stock log-only cast of "
    "ef038 (Shiva), read through the U1 s77 instrument -- per-mesh min/max of the primitives' OWN "
    "u,v bytes, joined one-to-one to the textured draw -- measured the `so` record's SECOND array as "
    "a PER-SLOT TEXEL DISPLACEMENT: PAIR POSITION 0 DISPLACES u, PAIR POSITION 1 DISPLACES v, a "
    "halfword of 128 moving its own axis by +128 texels, which on this container's 8bpp readers is "
    "exactly one page column, 640 to 704.  All four cells of the (position 0, position 1) square "
    "came back with ZERO residue on four disjoint reader populations, and the u-is-low-byte decode "
    "every earlier round merely ASSUMED was measured with them.  THE DISPLACEMENT IS BAKED INTO THE "
    "PRIMITIVE THE RENDERER SUBMITS AND IS ABSENT FROM THE CONTAINER'S STORED UV POOL: every span "
    "this kit holds is the UNDISPLACED coordinate, so cover, columns, spill and the whole `so`-UV "
    "attribution are computed on PRE-DISPLACEMENT numbers.  TWO RIDERS THIS CONSTANT USED TO CARRY "
    "ARE CLOSED BY THAT READ.  THE LABELLING IS SETTLED ON ef038 -- it is the one this kit calls "
    "SWAPPED -- and it is a single-record IDENTIFICATION, not a correlation: one reader carrying a "
    "non-zero position 0 with a ZERO position 1 moved in u, which the RETIRED labelling -- A onto v, "
    "B onto u, the reading this kit calls ORIGINAL -- forbids outright, and no other reader could "
    "counterfeit it.  THE v AXIS IS RESOLVED ON ef038: position 1 displaces it, read directly on two "
    "independent populations.  Both were open riders here until this cast, and both are byte-stream "
    "measurements now rather than screen inferences.  AND TREAT A DISPLACED COLUMN AS HALF AN "
    "ANSWER: every non-zero position 1 in this corpus is 128, which moves the read by half a page, "
    "into the OTHER STACKED CELL of that column.  FIVE THINGS STILL "
    "RIDE SEPARATELY AND ALL FIVE ARE OPEN.  (1) GENERALISATION: ONE CONTAINER, ONE CAST.  Nothing "
    "measured says the mechanism holds off ef038, a second container's log-only cast is what would "
    "make it a law, and every consequence this kit prints is still prefixed IF IT GENERALISES.  (2) "
    "THE OPERATION, not merely its size: ef038 carries only the halfword values 0 and 128, so adding "
    "128 to the byte and toggling the byte's top bit are THE SAME FUNCTION on every observation "
    "here.  Six containers in the corpus already carry a third value, and one log-only cast on any "
    "of them settles it.  (3) DEPTH: every population read was 8bpp, where a texel count, one "
    "64-pixel page column and half the u byte all coincide -- while this kit's own column arithmetic "
    "converts the halfword depth-dependently, and 52 of the corpus's 151 mover readers are NOT 8bpp "
    "-- 41 of them at 4bpp and 11 at 15bpp.  (4) WRAP-vs-CLAMP AT THE BYTE BOUNDARY: UNTESTED, "
    "because no observed span reaches it -- "
    "and in this kit's favour no incumbent reader in the corpus would reach it either, so the LINEAR "
    "reading printed here and a wrapping one agree on every one of them.  (5) PER-SLOT IS "
    "ESTABLISHED ONLY WHERE SLOT EQUALS RECORD: every population sits on a single-part record, so "
    "nothing here pairs array entry k with binding slot k and ORDER_UNMEASURED is untouched -- and "
    "two of the four populations are whole CLUT-key families, which establishes that NO reader "
    "drawing on that key was undisplaced rather than one identification per record.  WHAT THIS IS "
    "FOR: the kit everywhere equates a binding's BOUND cell with the cell the hardware SAMPLES, and "
    "this is the disclosure that on a reader carrying a non-zero halfword that identity is MEASURED "
    "NOT TO HOLD on ef038.  No cover, no depth, no page, no name and no emitted byte moves on it: "
    "the instrument the impact scoping made adoption conditional on -- log the primitives' own u and "
    "v instead of reading a screen -- has been BUILT, DEPLOYED, CAST AND READ, and it settled u AND "
    "v AND the labelling together on ONE container, so ADOPTING the displacement into the derivation "
    "is now an OWNER DECISION rather than a blocked one.  Until that decision is taken the kit reads "
    "the halfwords, states them, and refuses.  THE SHARPEST SINGLE STATEMENT OF WHAT IS UNMODELLED: "
    "ef038 declares both cells of column 704 and binds no `so` reader to either, so this kit refuses "
    "`cell.s0.x704_y256` AND `cell.s0.x704_y384` as `depth-unknown` and hands an author neither "
    "picture -- while the same cast measured 20 of the 27 readers this kit attributes to "
    "`cell.s0.x640_y256` -- one alone, nineteen as one CLUT-key family -- sampling column 704 "
    "instead.  BINDING-IS-NOT-A-DRAW and THE DEPTH COROLLARY "
    "are unchanged by all of it: what a record states is what something BINDS, and where the "
    "hardware reads is a second question this constant is the answer to only on one container")

#: what saying :data:`ACK_MOVER_KEY` means, printed on every build that uses it.  ⚠ THIS TEMPLATE'S
#: OWN PROSE must hold EXACTLY the two ``%s`` below and no other literal ``%``: it is formatted at
#: import, and a stray one either kills the import of this module outright or -- worse -- parses as a
#: silent conversion.  A ``%`` inside :data:`U_DISPLACEMENT_CAVEAT` is inert HERE (it is in argument
#: position) and fatal at the refusal, which is why the rule lives on the caveat as well.
U_DISPLACEMENT_ACK_WARNING = (
    "%s = true: EVERY `so` reader of this cell carries a NON-ZERO second-array halfword, and what "
    "that array does is no longer a hypothesis -- on ef038 a pair like that was MEASURED displacing "
    "the texels its reader samples, position 0 onto u and position 1 onto v, +128 texels each.  SO "
    "WHEREVER THAT MECHANISM HOLDS, THIS CELL HAS NO EFFECTIVE READER at the coordinates this kit "
    "names, and a perfectly built repaint of it is INVISIBLE IN GAME with no error anywhere.  WHAT "
    "YOU ARE ASSERTING IS NARROWER THAN IT WAS: not that the array is inert -- that is the reading "
    "ef038 refutes -- but that this container is not ef038 and you accept the generalisation risk, "
    "or that you have cast this cell yourself and seen your paint on screen.  One container, one "
    "cast is the whole distance between this warning and a certainty, and a cast is still the only "
    "thing that closes it.  %s  The kit checks nothing here and withdraws nothing: the page, its "
    "depth and its bytes are exactly what they were, the disclosure keeps printing after the "
    "acknowledgement so it stays auditable, and the judgement that this cell is still read is yours."
    % (ACK_MOVER_KEY, U_DISPLACEMENT_CAVEAT))

#: THE FIRING SET, RE-DERIVATION-PINNED (``u1_gates`` U2 re-rolls all three from the 372 containers
#: through :func:`~ff9mapkit.summons.repaint.scenery_surface` and asserts equality).  *A constant
#: nobody re-checks is a claim* -- and these three are the only numbers this rung mints.
#:
#: The predicate is UNCHANGED and stays LABELLING-INDEPENDENT BY CONSTRUCTION: a DECLARED page-cell
#: with at least one ``so`` reader, EVERY one of whose readers carries a non-zero second-array pair.
#: It never asks which halfword moves which axis and it never applies a displacement -- which is why
#: this number did not have to move on the day U1 settled the labelling, and why it will not have to
#: move on the day an adoption decision is taken either. It REFUSES; it never re-attributes.
#:
#: WHAT THE MEASUREMENT CHANGED IS THE JUSTIFICATION, NOT THE COUNT -- AND IT INVERTED IT. U1's s77
#: read settled the labelling on ef038 (pair position 0 displaces u, pair position 1 displaces v,
#: +128 texels each, 0.97, one container and one cast -- :data:`U_DISPLACEMENT_CAVEAT`), and the
#: impact scoping's two per-labelling lost-cell lists (16 SWAPPED / 19 ORIGINAL, union 35) were BOTH
#: u-ONLY models: each applied one halfword to u and modelled v not at all. So the measured labelling
#: does NOT promote the 16 to "the answer" -- it makes 16 the u-AXIS SUB-CASE of a two-axis
#: mechanism. Roll the MEASURED arithmetic over every incumbent reader in the same 372 containers and
#: the declared cells that lose EVERY effective reader are THIS SET, exactly: same count, same cells,
#: nothing added and nothing dropped. The old clause -- *"a strict SUPERSET ... by 17 cells whose
#: movers would not actually vacate the cell under either arithmetic"* -- is therefore WITHDRAWN AS
#: FALSE: those 17 DO vacate, in v, the axis neither list modelled. The set was minted conservative
#: and measures EXACT.
#:
#: WHAT STAYS CONSERVATIVE IS THE ADOPTION, NOT THE ARITHMETIC. The mechanism is ONE CONTAINER OLD,
#: so this class discloses and refuses instead of displacing anything, and a cell that keeps even ONE
#: zero-pair reader stays fully attributed here even where the measurement says most of its readers
#: sample elsewhere -- ef038 ``cell.s0.x640_y256``, 20 movers and SEVEN controls, is the worked
#: example. The reason to keep a predicate no adoption decision can move is now GENERALISATION plus
#: magnitude-vs-flag, never ignorance of which halfword moves what. Re-aiming cover, the census and
#: the licensing surface off ONE container's cast is an OWNER DECISION this rung does not take, and
#: the day it is taken this is the paragraph that says which numbers have to move.
#:
#: ⚠ THE EQUALITY ABOVE IS RE-DERIVED, NOT YET GATE-PINNED. ``u1_gates`` U2 pins the COUNT; the
#: measured-lost identity is owed its own roll beside it before anything leans on it -- on exactly
#: the law this module keeps, *a constant nobody re-checks is a claim.*
SECOND_ARRAY_MOVER_CELLS = 52
#: ...of which how many carry NO export-blocking refusal of any other class today, i.e. how many
#: ``export-art`` hands back as fully-open paintable pages. The other 5 are 4 ``program-vram-write``
#: and 1 ``same-bytes-two-depths``.
SECOND_ARRAY_MOVER_OPEN = 47
#: ...over how many of the corpus's 372 containers.
SECOND_ARRAY_MOVER_CONTAINERS = 29


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
