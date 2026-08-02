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
    "THE SECOND ARRAY DISPLACES THE SAMPLED TEXEL, THE MECHANISM IS MEASURED, AND SINCE W6b-3 (iv) "
    "THIS KIT MODELS IT.  THE MODEL, IN ONE LINE: effective = stored + halfword, on each axis "
    "independently, LINEAR ADDITION -- PAIR POSITION 0 DISPLACES u (in TEXELS, converted to "
    "halfwords at the page's own depth) and pair position 1 displaces v (in VRAM LINES, "
    "depth-free).  It is named `linear-add-v1` wherever this kit stamps a derivation, and the "
    "reader join an author walks is taken on the cell the hardware SAMPLES instead of the cell the "
    "record BINDS.  THE MEASUREMENT.  A stock log-only cast of ef038 (Shiva), read through the U1 "
    "s77 instrument -- per-mesh min/max of the primitives' OWN u,v bytes, joined one-to-one to the "
    "textured draw -- read the array as a PER-SLOT TEXEL DISPLACEMENT at 0.97, all four cells of "
    "the (position 0, position 1) square, four disjoint reader populations, ZERO residue; a "
    "halfword of 128 moved its own axis by +128 texels, which on that container's 8bpp readers is "
    "exactly one page column, 640 to 704.  THE GENERALISATION IS CLOSED: the same mechanism read on "
    "ef227 (key ISOLATED, triangle ratio 1.00, control gate PASS) and on ef446 (control gate PASS), "
    "two containers never measured before, with ef038 reproducing in the same log.  THE OPERATION "
    "IS CLOSED, AND THE TEST WAS DECISIVE RATHER THAN SUGGESTIVE: ef227's answer slot carries the "
    "raw pool 0, 25, 55, 85, 111 and the observed per-frame extremes were 16, 41, 101, 127 -- 41 "
    "and 101 are pool values 25 and 85 PLUS 16.  Under OR they would read 25 and 85, under XOR 9 "
    "and 69, and a FLAG reading predicts u in 128..239 against an observed 16..127, DISJOINT.  ADD "
    "is the only surviving operation and it is refuted independently on both ef227 and ef446.  THE "
    "LABELLING IS SETTLED and it is a single-record IDENTIFICATION rather than a correlation: one "
    "ef038 reader carrying a non-zero position 0 with a ZERO position 1 moved in u, which the "
    "REFUTED labelling -- position 1 onto u, the reading this kit used to call ORIGINAL -- forbids "
    "outright.  THE v AXIS IS RESOLVED: position 1 displaces it, read directly on two independent "
    "populations, and 129 of this kit's 151 mover readers carry a non-zero v -- 68 of them carry "
    "ONLY a v -- so a u-only adoption would have addressed the wrong stacked cell on the largest "
    "class in the corpus.  THE DISPLACEMENT IS BAKED INTO THE PRIMITIVE THE RENDERER SUBMITS AND IS "
    "ABSENT FROM THE CONTAINER'S STORED UV POOL, so the file's own spans are the UNDISPLACED "
    "coordinate and the kit keeps BOTH: the BOUND cover is what the record states and the EFFECTIVE "
    "cover is what the hardware reads.  THE INTRA-PAGE LAW, WHICH IS WHAT MAKES THE MODEL SAFE "
    "RATHER THAN MERELY LIKELY: a tpage origin is cell-aligned and stored u and v are BYTES, so one "
    "tpage spans one, two or four 64-halfword cells at 4, 8 or 15 bpp by exactly two stacked cells "
    "tall -- and across all 372 containers max(u) + du and max(v) + dv stay within 255 on 340 of "
    "340 incumbent readers, every effective cell landing inside the reader's OWN page.  Three "
    "things follow.  A displaced reader can never leave its page, so no read lands off VRAM.  An "
    "arriving reader's DEPTH is its own tpage's depth applied to an address inside that tpage, so "
    "nothing is extrapolated.  And LINEAR versus mod-256 WRAPPING is DEGENERATE -- nothing in the "
    "corpus reaches the byte boundary, the two readings agree on every reader this kit can reach, "
    "and the kit implements linear addition without having to choose.  FOUR THINGS STILL RIDE, AND "
    "ALL FOUR ARE NARROWER THAN THEY WERE.  (1) THE REACH IS THE INCUMBENT RECORDS ONLY: "
    "`Binding.mover` refuses to answer on a record with two or more parts, so nothing here pairs "
    "array entry k with binding slot k, ORDER_UNMEASURED is untouched, and 142 of the corpus's 309 "
    "novel slots carry a non-zero pair that NOTHING in this kit models.  The effective cover is "
    "therefore a LOWER BOUND on readership and no string in this lane may say that nothing reads a "
    "cell -- only that no reader this kit can attribute samples it.  (2) DEPTH: the axis-by-depth "
    "coverage is now u at 8bpp (ef038) and u at 15bpp (ef227's answer slot and ef446, both at "
    "displacement 16) and v at 8bpp, and the v axis is depth-free by construction.  What remains "
    "extrapolated is u at displacement 32 and 64 at 15bpp -- six readers, same axis and same depth "
    "class as the measured 16, magnitude only -- and ONE 4bpp u reader, which cannot change a cell "
    "verdict at all: a 4bpp cell is 256 texels wide and u is a byte, so every 4bpp u lands in one "
    "cell and the term moves halfwords inside it and nothing else.  (3) ARRAY-versus-BINDING: no "
    "cast separates the array VALUE displacing from the BINDING selecting a displaced source window "
    "that the array merely labels.  Both readings predict the SAME effective cell for every "
    "incumbent reader in the corpus, so the arithmetic is unaffected -- and every string here says "
    "that a reader CARRYING this pair samples at the displaced address, never that the halfword "
    "CAUSES it.  (4) BINDING-IS-NOT-A-DRAW and THE DEPTH COROLLARY are unchanged: deriving that a "
    "reader samples a cell makes that cell DERIVABLE, never PROVEN VISIBLE, and a stated depth is "
    "still what something BINDS at.  THE SHARPEST SINGLE STATEMENT OF WHAT THIS BUYS: ef038 "
    "declares both cells of column 704 and binds no `so` reader to either, so every kit before this "
    "one refused `cell.s0.x704_y256` AND `cell.s0.x704_y384` as `depth-unknown` and handed an "
    "author neither picture -- while the same cast measured 20 of the 27 readers those kits "
    "attributed to `cell.s0.x640_y256`, one alone and nineteen as one CLUT-key family, sampling "
    "column 704 instead.  This kit hands both back: the single reader lands on `cell.s0.x704_y256` "
    "and THE NINETEEN-PLUS-ONE LAND ON `cell.s0.x704_y384`, the LOWER stacked cell, because the v "
    "term puts them there.  ** BUT DERIVABLE IS NOT DELIVERABLE, AND ON ef038 ITSELF IT IS NOT: "
    "`export-art` writes no PNG for ANY of that container's four column-640 and column-704 pages, "
    "before this rung or after it -- but for TWO DIFFERENT REASONS, and this lane will not credit "
    "the older one for a page the new arithmetic withdrew.  ef038 is a program-VRAM WRITER, so "
    "THREE of the four (`cell.s0.x640_y256`, `cell.s0.x704_y256`, `cell.s0.x704_y384`) carry the "
    "pre-existing `program-vram-write` refusal; the FOURTH, `cell.s0.x640_y384`, is withdrawn by "
    "THIS RUNG'S OWN `displaced-readerless` -- every reader it bound samples column 704 instead.  "
    "THE DELIVERABLE CASE IS ef407, ef038's structural twin, which "
    "reproduces the derivation cell for cell -- 27 bound readers on `cell.s0.x640_y256` down to 7, "
    "ONE arriving on `cell.s0.x704_y256` and TWENTY on `cell.s0.x704_y384` -- and carries no "
    "program-VRAM refusal, so on ef407 both gained pages really do export")

#: what saying :data:`ACK_MOVER_KEY` means, printed on every build that uses it.  ⚠ THIS TEMPLATE'S
#: OWN PROSE must hold EXACTLY the two ``%s`` below and no other literal ``%``: it is formatted at
#: import, and a stray one either kills the import of this module outright or -- worse -- parses as a
#: silent conversion.  A ``%`` inside :data:`U_DISPLACEMENT_CAVEAT` is inert HERE (it is in argument
#: position) and fatal at the refusal, which is why the rule lives on the caveat as well.
U_DISPLACEMENT_ACK_WARNING = (
    "%s = true: THIS KIT DERIVES THAT NO READER IT CAN ATTRIBUTE SAMPLES THIS CELL, AND YOU ARE "
    "PAINTING IT ANYWAY.  Every `so` reader the container binds to this cell carries a NON-ZERO "
    "second-array halfword, and the displacement those halfwords encode is MODELLED -- linear "
    "addition, position 0 onto u and position 1 onto v -- so under the adopted derivation each of "
    "them samples somewhere else.  WITHOUT THIS KEY the cell refuses as `displaced-readerless` or "
    "`displaced-readership-substituted`; WITH IT the kit falls back to whatever channel still "
    "speaks for the cell -- usually its COLUMN's own depth (CHANNEL G), at the same bit depth, "
    "because a displacement moves where a reader looks and never what mode a page is read in.  "
    "** THE KEY LIFTS THE REFUSAL, NOT THE GUARANTEE, AND THE LEDGER IS MEASURED RATHER THAN "
    "PROMISED.  Over the 55 corpus names the two classes cover, WITH the key: 39 come back as the "
    "IDENTICAL PICTURE (34 of them with nothing moving but `depth_source`, `so-uv` to `so-page`); 6 "
    "COME BACK AS A DIFFERENT PICTURE, four of those read back at 8 bpp where they were 4 bpp -- the "
    "same 16,384 bytes, half the texel width, through a 256-entry key instead of a 16-entry one -- "
    "and two through a different CLUT at the same depth; and 10 COME BACK WITH NOTHING AT ALL, "
    "falling straight through to `depth-unknown` or `channel-g-dual-depth` because the channel that "
    "has to speak next does not always have an answer either.  Saying the key is not the same as "
    "being handed back what you had.  WHAT "
    "YOU ARE ASSERTING is that this cell is read despite the derivation: either because you have "
    "cast it yourself and seen your paint on screen, or because you judge that a reader this kit "
    "cannot attribute -- one on a multi-part record, whose array entry order nothing has measured "
    "-- samples it.  That second case is real and the kit says so rather than implying safety: the "
    "effective cover is a LOWER BOUND on readership.  A CAST IS STILL THE ONLY THING THAT CLOSES "
    "IT.  %s  The disclosure keeps printing after the acknowledgement so it stays auditable, and "
    "the judgement that this cell is still read is yours."
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
#: ⚠ **THAT DAY CAME: THE PARAGRAPH ABOVE IS W6b-3 (iii)'s AND IS KEPT AS THE RECORD OF WHY THE
#: DECISION WAS OWED, NOT AS A STATEMENT OF WHERE THE KIT STANDS.** Two of its clauses are RETIRED.
#: *"The mechanism is ONE CONTAINER OLD"* -- it is three (ef038 measured, ef227 and ef446
#: generalised, operation settled by a value test on ef227). *"an OWNER DECISION this rung does not
#: take"* -- W6b-3 (iv) TAKES it, and re-aimed cover, readership and the EDIT surface accordingly.
#: What did NOT move is this constant and the two beside it: the predicate is still taken on
#: :data:`~ff9mapkit.summons.repaint.LICENSED_CHANNELS`, still refuses rather than re-attributes
#: there, and still re-rolls 52 / 47 / 29. The adoption's own counts live below, under EDIT scope.
#:
#: ⚠ **THE EQUALITY ABOVE WAS OWED A ROLL, W6b-3 (iv) RAN IT, AND IT NEEDED A SCOPE WORD.** The
#: sentence *"the declared cells that lose EVERY effective reader are THIS SET, exactly"* is TRUE
#: under the **VACATE** reading -- every reader OF THIS CELL leaves it: 52 of 52, zero added, zero
#: dropped, and the roll says why it is not luck (over 182 mover-times-cell incidences corpus-wide,
#: **0** are cases where a displaced reader still covers a cell it reads today, so *"every reader
#: carries a pair"* and *"every reader leaves"* are the same set here -- a corpus fact, not a
#: theorem: a 4bpp reader with a small ``u`` term confined to mid-column would stay). It is FALSE
#: under the plain reading of its own words: the cells that end with NO effective reader are
#: **45**, because 7 of the 52 are RE-POPULATED by an arriving FOREIGN displaced reader. The 45 and
#: the 7 are :data:`DISPLACED_READERLESS_CELLS` and :data:`DISPLACED_SUBSTITUTED_CELLS`, minted
#: BESIDE this constant rather than moved into it, because the 7 do not stop being displaced -- they
#: stop being UNREAD, and they move from REFUSE to RE-ATTRIBUTE.
SECOND_ARRAY_MOVER_CELLS = 52
#: ...of which how many carry NO export-blocking refusal of any other class today, i.e. how many
#: ``export-art`` hands back as fully-open paintable pages. The other 5 are 4 ``program-vram-write``
#: and 1 ``same-bytes-two-depths``.
SECOND_ARRAY_MOVER_OPEN = 47
#: ...over how many of the corpus's 372 containers.
SECOND_ARRAY_MOVER_CONTAINERS = 29

# ================================================= W6b-3 (iv): THE SECOND ARRAY, **ADOPTED**
# ★ THE FIRST RUNG IN THIS LANE THAT DELIBERATELY CHANGES BEHAVIOUR.  Every rung before it read the
# second array and refused; this one applies it -- `effective = stored + halfword`, per axis, linear
# -- so the reader join an author walks is taken on the cell the hardware SAMPLES.
#
# ⚠ **SCOPE, STATED BEFORE THE NUMBERS.**  Every count below measures
# :data:`ff9mapkit.summons.repaint.EDIT_CHANNELS`, the set that consults `"so-displaced"`.  Nothing
# above it moves: :data:`SECOND_ARRAY_MOVER_CELLS` / `_OPEN` / `_CONTAINERS` describe
# :data:`~ff9mapkit.summons.repaint.LICENSED_CHANNELS`, where they re-roll to 52 / 47 / 29 exactly as
# before, and :data:`GAIN_SO_PAGE`, :data:`CHANNEL_G_DUAL_CELLS`, :data:`DEPTH_UNKNOWN`,
# :data:`REFUSED_AMBIGUOUS` and every depth VALUE are unmoved on their own scopes too.  That is the
# same two-scope device :data:`A2_SCOPE_NOTE` is; the delta is a diff between two NAMED sets rather
# than a number that moved under a constant's old name.

#: the ADOPTED model's name, so a manifest, a scaffold or a ledger row can say WHICH arithmetic it
#: was written under. Mirrored by :data:`ff9mapkit.summons.repaint.DISPLACEMENT_MODEL`.
DISPLACEMENT_MODEL = "linear-add-v1"

#: incumbent (``P <= 1``) ``so`` readers corpus-wide -- the whole reach of the adoption.
#: Re-derivation-pinned; ``u1_gates`` U2 already rolls this number independently.
INCUMBENT_READERS = 340
#: ...of which carry a NON-ZERO second-array pair, i.e. are DISPLACED. 41 at 4bpp, 99 at 8bpp, 11 at
#: 15bpp; by pair, ``(0,128)`` x68, ``(128,128)`` x55, ``(128,0)`` x22, ``(16,128)`` x3,
#: ``(32,128)`` x2, ``(64,128)`` x1 -- **v-ONLY is the largest single class**, which is why a u-only
#: adoption would have landed the arc's own worked example on the wrong stacked cell.
INCUMBENT_MOVERS = 151
#: NOVEL (``P >= 2``) slots carrying a non-zero pair -- **WHAT THE ADOPTION CANNOT REACH.**
#: ``Binding.mover`` refuses to answer there (``ORDER_UNMEASURED``), so the effective cover is a
#: LOWER BOUND on readership. Carried as a constant so the disclosures can say it with a number.
NOVEL_MOVER_SLOTS = 142

#: **THE VACATED HALF.** Declared page-cells that had at least one ``so`` reader and end with NONE
#: under the adopted derivation. ⚠ These were NOT silently paintable before this rung: W6b-3 (iii)'s
#: second-array gate already refused the BUILD on every one of them (measured, 0 of 45 build clean
#: without the ack). What this rung adds is the DESTINATION -- and it moves the refusal from the
#: build to resolution and export. **Re-derivation-pinned** through
#: :func:`ff9mapkit.summons.repaint.scenery_surface` at ``EDIT_CHANNELS`` scope.
DISPLACED_READERLESS_CELLS = 45
#: ...of which carried NO export-blocking refusal on the **PRE-ADOPTION** surface, i.e. how many were
#: fully open paintable pages that this rung takes away. Measured at the W6b-3 scope on purpose: what
#: an addressability delta costs is what the author could reach BEFORE, and after the refusal fires
#: every one of them reads as open (the later classes are appended only to an EMITTED page).
DISPLACED_READERLESS_OPEN = 41
#: ...over how many of the 372 containers.
DISPLACED_READERLESS_CONTAINERS = 26
#: **THE SHARPER HALF OF THE SAME LOSS**: every bound reader leaves AND a DISJOINT foreign displaced
#: set arrives. *"Paint here and a DIFFERENT model shows it"* is not *"nothing reads here"*, so it is
#: its own class rather than a footnote on one.
DISPLACED_SUBSTITUTED_CELLS = 7
#: ...of which were open on the pre-adoption surface, by the same reading as
#: :data:`DISPLACED_READERLESS_OPEN`.
DISPLACED_SUBSTITUTED_OPEN = 6

#: ⚠ **45 AND 52 ARE NOT ADDENDS, AND THIS IS THE SENTENCE THAT SAYS SO.** They are two readings of
#: ONE population. ``45 readerless + 7 substituted == 52 vacating``, and ``41 + 6 == 47`` open, over
#: the same 29 containers -- so :data:`SECOND_ARRAY_MOVER_CELLS` is the VACATE count and
#: :data:`DISPLACED_READERLESS_CELLS` is the READERLESS one. Anyone adding them is double-counting
#: the same cells, which is the likeliest misreading in this whole rung and is pre-empted in prose
#: for the same reason :data:`ARRAY_DEFLATION_OVERLAP` exists.
assert (DISPLACED_READERLESS_CELLS + DISPLACED_SUBSTITUTED_CELLS
        == SECOND_ARRAY_MOVER_CELLS), "45 + 7 must close on the 52 VACATE cells"
assert (DISPLACED_READERLESS_OPEN + DISPLACED_SUBSTITUTED_OPEN
        == SECOND_ARRAY_MOVER_OPEN), "41 + 6 must close on the 47 open"

#: **THE GAIN HALF.** Declared page-cells that bind no ``so`` reader and that a DISPLACED reader
#: SAMPLES. They are licensed by DEFAULT and behind no new key: the arriving reader's depth comes
#: from its own ``so`` record, at the same tier as every one of the 187 incumbent ``so-uv`` cells,
#: and by THE INTRA-PAGE LAW that record's tpage CONTAINS the effective address -- so nothing is
#: extrapolated and there is no weaker channel to acknowledge.
DISPLACED_GAINED_CELLS = 70
#: ...of which were refused ``depth-unknown`` before this rung -- **THE PRIZE**: cells the kit handed
#: an author nothing for, now derivable from evidence the licensed path already consults.
DISPLACED_GAINED_FROM_UNKNOWN = 29
#: UNDECLARED cells a displaced reader lands on -- bytes nothing in the container uploads. There is
#: no page to hand back; they join the u-spill UNWRITTEN class on the EFFECTIVE obligation set only.
DISPLACED_GAINED_UNDECLARED = 2

#: cells that keep a reader but not the SAME readers -- **the class nobody had named**, bigger than
#: either half above. Nothing refuses and no page moves; what moves is which models the shared-read
#: and multi-palette disclosures NAME.
DISPLACED_CHANGED_CELLS = 36
#: ...of which the LOWEST-ADDRESSED reader changes, i.e. the class-C DISPLAY BINDING changes hands
#: and the exported PNG comes back in a different palette key. A picture that changes key with no
#: line saying so is exactly the silent change this lane refuses to ship.
DISPLACED_DISPLAY_BINDING_MOVED = 14

#: **THE ONE VETO THIS RUNG MINTS**: a GAINED cell whose arriving reader's depth contradicts the
#: CHANNEL G page depth that was serving it. Two overlapping tpages naming the same VRAM at two
#: depths -- and UNANIMITY IS THE VERDICT RULE, TWO VALUES IS A HAZARD NOT A VOTE, so the kit states
#: both and picks neither rather than re-sourcing to the reader.
DISPLACED_VS_PAGE_DEPTH_CELLS = 1

#: spilling bindings on the **EFFECTIVE** cover -- what THE NAME-EVERY-COLUMN gate's obligation set
#: is now taken on. :attr:`~ff9mapkit.summons.repaint.BoundModel.spills` (the BOUND reading, 58) is
#: what ``w6b_gates`` G6's u-spill census is written about and **does not move**; this is the second
#: number beside it, never a replacement for it. The change is PURELY ADDITIVE -- 0 bindings stop
#: spilling -- and the two that start are **ef381 GEOM 0x20727c** and **ef447 GEOM 0xa2f74**, both
#: 15bpp with the pair ``(32, 128)``: at one texel per halfword a ``+32`` u term carries a span that
#: sat inside column 704 across the boundary into 768. (⚠ The scoping survey predicted a different
#: pair -- two ef082 bindings -- and the roll refutes it; this is the measured answer.)
DISPLACED_SPILL_BINDINGS = 60

#: the ``so-uv`` cell count on the three named surfaces, with the arithmetic between them spelled
#: out. **187** is W6b-1's census (:data:`~ff9mapkit.summons.repaint.CENSUS_CHANNELS`) and **183** is
#: the W6b-3 shipped one (:data:`~ff9mapkit.summons.repaint.LICENSED_CHANNELS`, where CHANNEL A's
#: veto withdraws 4). Neither moves. The edit surface
#: (:data:`~ff9mapkit.summons.repaint.EDIT_CHANNELS`) is the ONE number this rung is allowed to move,
#: and it moves BY ARITHMETIC: ``183 - 45 readerless - 7 substituted + 70 gained - 1 displaced-vs-
#: page-depth - 1 whose column keeps CHANNEL A's array-dual veto == 199``.
CENSUS_SO_UV_CELLS = 187
SHIPPED_SO_UV_CELLS = 183
EDIT_SO_UV_CELLS = 199
assert (SHIPPED_SO_UV_CELLS - DISPLACED_READERLESS_CELLS - DISPLACED_SUBSTITUTED_CELLS
        + DISPLACED_GAINED_CELLS - DISPLACED_VS_PAGE_DEPTH_CELLS - 1
        == EDIT_SO_UV_CELLS), "the edit surface's so-uv count must close on its own terms"

#: ★ THE DERIVATION, CARRIED AS A CALL-SITED CONSTANT so a manifest row, a ledger line or a refusal
#: can say what the model rests on without re-stating :data:`U_DISPLACEMENT_CAVEAT` in full.
DISPLACEMENT_DERIVATION = (
    "MODEL " + DISPLACEMENT_MODEL + ": effective = stored + halfword, per axis, LINEAR ADDITION; "
    "pair position 0 onto u (TEXELS, depth-converted), pair position 1 onto v (VRAM LINES).  "
    "MEASURED on ef038 at 0.97 (four disjoint reader populations, zero residue), GENERALISED on "
    "ef227 and ef446 with control gates PASS, and the OPERATION settled by a value test on ef227 "
    "that excludes OR, XOR, FLAG and NONE.  REACH: the INCUMBENT records only -- 340 readers, 151 "
    "of them displaced; a multi-part record's array entry order is UNMEASURED and 142 novel slots "
    "carry a pair nothing here models, so the effective cover is a LOWER BOUND on readership.  "
    "DEGENERACIES: linear versus mod-256 wrapping (nothing in the corpus reaches the byte "
    "boundary, so they agree on every reader in reach) and array-versus-binding (both readings "
    "predict the same effective cell for every reader in reach).  ** THE TWO HALVES OF THIS "
    "DERIVATION FAIL DIFFERENTLY AND ONLY ONE OF THEM FAILS LOUDLY, WHICH IS THE HONEST LIMIT OF "
    "THE ADOPTION.  Where it takes readership AWAY the kit REFUSES and a stated key is the only "
    "way past, so a wrong model costs you a refusal you can argue with.  Where it HANDS readership "
    "to a cell nothing binds -- the gain half, 70 declared cells, 29 of them refused "
    "`depth-unknown` before this rung -- the page is licensed on the derivation ALONE, behind no "
    "key, because there is no reader to contradict.  So if `linear-add-v1` does not hold on YOUR "
    "container, a perfect repaint of a gained cell is INVISIBLE IN GAME with no error anywhere: "
    "the same silent failure the loss half exists to refuse, pointing the other way.  A CAST IS "
    "THE ONLY THING THAT CLOSES IT")


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
