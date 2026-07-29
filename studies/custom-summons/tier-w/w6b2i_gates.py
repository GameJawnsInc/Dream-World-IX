r"""TIER W rung W6b-2 INTEGRATION -- THE GATE RUNNER FOR THE KIT SIDE.  `py w6b2i_gates.py` -> I0..I10.

`w6b2_gates.py` is the RECON's gate runner: it re-measures every number `W6b2-ATTRIBUTION.md` states,
from the corpus and the lane artifacts, and it is READ-ONLY to this round.  **This file is the other
half**: the recon's build list (that record's sec 7) turned into shipped kit behaviour, with one gate
per row and every gate driven through THE CODE THAT SHIPS rather than through a private re-derivation.

    sec 7 row 1   a PAGE-granular depth view in `reskin`, beside the UV reader view, NEVER merged   I0 I1
    sec 7 row 2   the SPILL-vs-OWN-PAGE hazard -- and it must protect EXACTLY ZERO new cells        I4
    sec 7 row 3   the PROGRAM-DUAL-DEPTH hazard: 22 cells in 10 containers, re-derived per run      I3
    sec 7 row 4   the CHANNEL-G-DUAL-DEPTH hazard: 8 cells, named nowhere in any lane dossier       I3
    sec 7 row 5   the program-derived depth table as a CONSTANT, WITH A RE-DERIVATION PIN           I2
    sec 7 row 6   the depth-unknown refusal reason gains the derived evidence (DISCLOSE)            I6
    sec 7 row 7   `acknowledge_program_derived_depth` + a MANDATORY matching `expect_bpp`           I7
    sec 7 row 8   channel G adopted as a depth SOURCE: 57 gain, 56 build, 1 refuses                 I5
    sec 7 row 9   re-stamp the census's `addressable_via` field   (a PARALLEL lane's; verified)     I8
    sec 7 row 10  2,139 cells keep refusing BY NAME, with the residue split in the reason string    I9
                  provenance: no stock byte in anything this round commits                          I10

★ THE LINE THIS RUNG IMPLEMENTS, and every gate below is a form of it:

    CHANNEL G LICENSES.  CHANNEL P DISCLOSES, and edits only behind an explicit acknowledgement.

★ AND THE FACT THAT DECIDED IT, which is why I7 is the longest gate here.  Channel P's own written
upgrade path was *"P earns LICENSE when a cast proves a program-derived depth on screen"*.  **That
trigger fired ONCE and FAILED**: `W6b-SCENERY.md` sec 5's ef251 ladder cast a program-registered
15bpp page and got a 4bpp read back.  So the kit ships the DISCLOSURE, ships the ack, and makes the
ack meaningless without a matching `expect_bpp` -- the author carries the judgement, the kit carries
the check.

Reads the extracted corpus at C:\gd\SCRATCH\summon-format and the lane artifacts under
texel-w6b\ ONLY.  No install read, NO deploy, no install write, no git commit, and it writes nothing
but its own stdout.  ONE corpus pass, ~4 min.
"""
from __future__ import annotations

import ast
import glob
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                              # noqa: E402  (sets up sys.path)
import summon_camera as W                                        # noqa: E402
from ff9mapkit.summons import depth_attribution as DA            # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402

CORPUS = W.SCRATCH_CORPUS
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
SCRATCH = os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format")
W6B = os.path.join(SCRATCH, "texel-w6b")
LANE = os.path.join(W6B, "w6b2")

#: THE GRANULARITY STATEMENT, in this file's own arithmetic rather than by import: a VRAM tpage names
#: a 64 x 256 PAGE, a census page-cell is 64 x 128, so one page word covers a COLUMN of two cells.
PAGE_HW, PAGE_LINES, CELL_LINES = 64, 256, 128

#: ★ W6b-3 NARROWING, DECLARED -- THE EDIT SURFACE THIS FILE IS WRITTEN ABOUT IS **W6b-2's**.
#:
#: Every pin below (`gain_so_page 57`, `so_uv_cells 187`, `depth_unknown_after 2298`, the whole
#: `hz_*` block, `scenery_cells 2572`) measures the surface `LICENSED_CHANNELS` emitted when this
#: file was written -- ``("so-uv", "so-page", "program")``.  W6b-3 added ``"so-array"`` to that
#: constant, and CHANNEL A holds **VETO** power: on the shipped licensed path 6 cells lose a page
#: and 8 more refuse under a sharper name (`w6b3i_gates` I6/I9 measure and pin exactly that).
#: Taking `RP.LICENSED_CHANNELS` here would therefore have re-aimed every number in this file at a
#: different population while the pins still read as W6b-2's -- the same defect
#: :data:`~ff9mapkit.summons.repaint.CENSUS_CHANNELS` was minted to prevent one channel earlier, and
#: the same defect `w6b3_gates`' three freezes prevent one witness earlier.
#:
#: So the scope is **STATED**, not inherited: derived from the shipped tuple so a future channel
#: cannot be silently absorbed either, and any W6b-2-era number that moves under it is a real leak
#: rather than a re-aim.  The SHIPPED default's own figures live in `w6b3i_gates` I9, beside these,
#: with the delta derived -- two scopes, both printed, neither reconciled (the I1 precedent).
W6B2_CHANNELS = tuple(c for c in RP.LICENSED_CHANNELS if c != "so-array")

# --------------------------------------------------------------------------- THE PINS
#: Every number this rung's kit side is allowed to assert.  Each is RE-MEASURED below and compared
#: here.  Where a number is also in `w6b2_gates.PIN` it is deliberately NOT imported: two files
#: measuring the same thing independently is the point, and a shared constant would make the
#: agreement a tautology.
PIN = {
    # -- I0/I1 the two views
    "containers": 372,
    "scenery_cells": 2572,
    "cal_g_rows": 140, "cal_g_agree": 138,
    "cal_g_informative": 18, "cal_g_informative_agree": 16,
    "cal_g_flagged": 2,
    #: ...and the SHIPPED view's own scope, which is ONE ROW SMALLER and deliberately so -- see I1.
    "kit_rows": 139, "kit_agree": 137,
    "kit_informative": 17, "kit_informative_agree": 15,
    # -- I2 the re-derivation pin
    "p_table_rows": 221,
    "p_single": 199,
    "p_dual": 22,
    "p_dual_containers": 10,
    # -- I3 the refused set
    "g_dual": 8,
    "ambiguous_overlap": 0,
    "refused_ambiguous": 32,
    # -- I4 the spill class
    "spill_cells": 2,
    "spill_newly_unaddressable": 0,
    "spill_newly_export_blocked": 0,
    # -- I5 channel G
    "gain_so_page": 57,
    "g_clean": 56,
    "g_refusing": 1,
    "g_lower_halves": 55,
    #: ★ THE THIRD BUCKET.  56 clear every REFUSAL, and 7 of those 56 carry the class-C multi-palette
    #: DISCLOSURE -- their COLUMN is bound with 2-3 CLUT keys.  Invisible while class-C evidence was
    #: read off READERS a readerless cell does not have, which is why "56 clean" read green.
    "g_multi_palette": 7,
    "g_hazard_clean": 49,
    #: the read-only `.as-<clut>.png` renderings those 7 name -- 6 columns with 2 keys + 1 with 3.
    "g_alternate_rows": 8,
    # ...and the W6b-1 hazard populations that must NOT move when 57 cells gain a depth.  BOTH
    # SURFACES ARE PINNED: the census one is the W6b-1 identity three sibling gate files rest on, the
    # edit one is what an author meets, and exactly one of the six differs between them.
    "hz_two_depths": 17, "hz_multi_palette": 25, "hz_shared_read": 93,
    "hz_spill_in": 36, "hz_spill_touched": 70, "hz_co_transform": 24,
    "hz_multi_palette_edit": 32,
    # -- I7 CHANNEL P's own three-way split, measured rather than scoped around
    #: 189 cells gain a program-derived depth; the acknowledgement's reach is NOT all of them.
    "p_direct_cells": 55,           # 15bpp -- direct colour, which indexes no palette by definition
    "p_indexed_cells": 134,         # 4 or 8bpp -- an index array channel P states NO key for
    "p_no_palette": 102,            # ...of which this many reach `program-depth-no-palette`
    "p_indexed_other": 32,          # ...and this many refuse EARLIER on a program-VRAM verdict
    "p_resolvable": 87,             # cells `texel_page` hands back under the ack
    "p_buildable": 43,              # ...with no refusal of any kind: all 15bpp
    #: channel-P cells at y = 384 that are id-9 ALTERNATE BLOCKS -- `hazards.lower_half` is False on
    #: every one of them and their depth still crossed a cell boundary.  The disclosure's inheritance
    #: clause is gated on the COLUMN, and these 10 are the population that proves which predicate.
    "p_id9_lower": 10,
    # -- I5/I9 the population
    "so_uv_cells": 187,
    "gain_program": 189,
    "gain_either": 246,
    "depth_unknown_after": 2298,
    "residue": 2139,
    "residue_blind": 1278,
    "residue_covered": 861,
    "depth_unknown_before": 2385,
    # -- I8 the census re-stamp
    "stale_addressable_rows": 0,
    "prog_lower_halves": 93,
    #: 83 carry the census's own `hz_unaddressable_lower_half` flag and are stamped through the
    #: per-cell map; the other 10 are id-9 alternate blocks -- one whole upload each, never a rect's
    #: lower half, addressable through the id-9 rect key and always were.  83 + 10 = 93.
    "prog_lower_halves_via_map": 83,
    "prog_lower_halves_via_id9": 10,
    #: CHANNEL H over W6b-1's WHOLE 2,385 -- the record's own figure, so the kit's smaller in-residue
    #: count can be shown to be the same measurement on a smaller population rather than a drift.
    "hint_in_2385": 351, "hint_4bpp": 286, "hint_8bpp": 65,
}

_FAILS: List[str] = []


def chk(name: str, got, want) -> None:
    """Compare a re-measured value against its pin; COLLECT rather than raise, so the whole board
    prints and one red gate cannot hide the state of the others."""
    ok = (abs(got - want) < 5e-3) if isinstance(want, float) else (got == want)
    if not ok:
        _FAILS.append("%s: measured %r, pinned %r" % (name, got, want))


# --------------------------------------------------------------------------- shared derivations
def dec(tp: int) -> Tuple[int, int, int]:
    """(page_x, page_y, bpp) from a nine-bit PSX tpage word -- written from the bit layout HERE, so
    the re-derivation pin does not lean on the same decoder the kit does."""
    return (tp & 0x0F) * PAGE_HW, ((tp >> 4) & 1) * PAGE_LINES, RS.SO_BPP[(tp >> 7) & 3]


def cover(px: int, py: int) -> List[Tuple[int, int]]:
    """THE GRANULARITY STATEMENT, in code: a page covers both stacked 128-line cells of its column."""
    return [(px, py), (px, py + CELL_LINES)]


def _load(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class Data:
    """ONE corpus pass, driven through the SHIPPED derivations, plus the census and the sweep."""

    def __init__(self) -> None:
        self.census = _load(os.path.join(W6B, "census", "pages.json"))
        self.C = {(r["ef"], r["vram_x"], r["vram_y"]): r for r in self.census}
        self.sweep = _load(os.path.join(LANE, "tpage_sweep.json"))
        self.paths = sorted(p for p in glob.glob(os.path.join(SCRATCH, "ef*.bytes"))
                            if len(os.path.basename(p)) == 11)
        #: the SHIPPED page-granular view, per cell -- `reskin.page_depth_view`
        self.gview: Dict[Tuple[int, int, int], Tuple[int, ...]] = {}
        self.gbinders: Dict[Tuple[int, int, int], set] = {}
        #: THIS FILE's independent roll of the same thing, for I0
        self.gmine: Dict[Tuple[int, int, int], Tuple[int, ...]] = {}
        #: ...and the RECON's scope for the same roll: every CENSUS cell, id-4 creature pages
        #: INCLUDED.  Kept separately because the one-row difference between the two is the whole
        #: content of I1's second half.
        self.gcensus: Dict[Tuple[int, int, int], Tuple[int, ...]] = {}
        self.gcensus_binders: Dict[Tuple[int, int, int], set] = {}
        #: the SHIPPED surface, per cell
        self.pages: Dict[Tuple[int, int, int], RP.TexelPage] = {}
        self.refusals: Dict[Tuple[int, int, int], set] = defaultdict(set)
        self.reasons: Dict[Tuple[int, int, int], Dict[str, str]] = defaultdict(dict)
        self.cells: set = set()
        self.arity: Dict[int, Tuple[int, int]] = {}
        #: the CENSUS view -- `scenery_surface`'s default, which three sibling gate files pin.
        self.census_pages: set = set()
        self.census_dark: set = set()
        self.census_klasses: set = set()
        #: the census view's own HAZARD populations -- the six W6b-1 numbers, measured where W6b-1
        #: measured them.  Kept beside the edit surface's rather than instead of it: one of the six
        #: MOVES on the edit surface by design (class-C evidence at the depth's own granularity), and
        #: pinning only one of the two would hide either the fix or the W6b-1 identity.
        self.census_hz: Dict[str, set] = defaultdict(set)
        self.edit_hz: Dict[str, set] = defaultdict(set)
        #: ★ THE ACK SURFACE -- `program_depth=True`, i.e. what an author who said the acknowledgement
        #: actually gets.  Run ONLY on the containers channel P speaks for (76 of 372), because
        #: everywhere else it is the edit surface by construction and a third full pass would buy
        #: nothing but runtime.
        self.ack_pages: Dict[Tuple[int, int, int], RP.TexelPage] = {}
        self.ack_refusals: Dict[Tuple[int, int, int], set] = defaultdict(set)
        self.ack_reasons: Dict[Tuple[int, int, int], Dict[str, str]] = defaultdict(dict)
        self.ack_disclosures: Dict[Tuple[int, int, int], str] = {}
        self._walk()

    _HZ = ("two_depths", "multi_palette", "shared_read", "spill_in", "spill_out", "co_transform")

    @staticmethod
    def _hz_of(page: RP.TexelPage) -> List[str]:
        h = page.hazards
        return [n for n, v in (("two_depths", h.two_depths), ("multi_palette", h.multi_palette),
                               ("shared_read", h.shared_read), ("spill_in", bool(h.spill_in)),
                               ("spill_out", bool(h.spill_out)),
                               ("co_transform", h.co_transform)) if v]

    def _walk(self) -> None:
        p_effects = {k[0] for k in DA.PROGRAM_DEPTH}
        for p in self.paths:
            ef = int(os.path.basename(p)[2:5])
            with open(p, "rb") as fh:
                blob = fh.read()
            for pc in RS.page_cells(blob).values():
                self.cells.add((ef, pc.cell[0], pc.cell[1]))
            for cell, pd in RS.page_depth_view(blob).items():
                self.gview[(ef, cell[0], cell[1])] = pd.depths
                self.gbinders[(ef, cell[0], cell[1])] = {b.geom for b in pd.binders}
            # THIS FILE's own roll, from `attribution` alone -- the instrument check for I0, and the
            # RECON's wider scope (every census cell, creature pages included) for I1.
            declared = {pc.cell for pc in RS.page_cells(blob).values()}
            mine: Dict[Tuple[int, int], set] = defaultdict(set)
            wide: Dict[Tuple[int, int], set] = defaultdict(set)
            wide_g: Dict[Tuple[int, int], set] = defaultdict(set)
            # ★ W6b-3 NARROWING, DECLARED: `mine` / `wide` / `wide_g` are this file's private CHANNEL
            # G roll and feed I0/I1.  `attribution`'s default became the TRUE (multi-part) population
            # at W6b-3 and channel G is its INCUMBENT half, so the scope is stated here rather than
            # inherited from a default that no longer means what this code was written to mean.
            for b in RS.attribution(blob, include_direct=True,
                                    witness=RS.WITNESS_INCUMBENT).bindings:
                px, py, bpp = dec(b.tpage)
                for c in cover(px, py):
                    if c in declared:
                        mine[c].add(bpp)
                    if (ef, c[0], c[1]) in self.C:
                        wide[c].add(bpp)
                        wide_g[c].add(b.geom)
            for c, ds in mine.items():
                self.gmine[(ef, c[0], c[1])] = tuple(sorted(ds))
            for c, ds in wide.items():
                self.gcensus[(ef, c[0], c[1])] = tuple(sorted(ds))
                self.gcensus_binders[(ef, c[0], c[1])] = set(wide_g[c])
            self.arity[ef] = RP.clut_arity(blob)
            # THE CENSUS VIEW -- `scenery_surface`'s own default, which MUST still be W6b-1's.
            cp, cr = RP.scenery_surface(blob, ef)
            self.census_pages |= {(ef, p.cell[0], p.cell[1]) for p in cp}
            self.census_dark |= {(ef, r.cell[0], r.cell[1]) for r in cr
                                 if r.klass == "depth-unknown"}
            self.census_klasses.update(r.klass for r in cr)
            for pg in cp:
                for n in self._hz_of(pg):
                    self.census_hz[n].add((ef, pg.cell[0], pg.cell[1]))
            # THE EDIT SURFACE -- what an author got at W6b-2, and what every gate below judges.
            # ★ SCOPED, NOT INHERITED: see `W6B2_CHANNELS`.  `RP.LICENSED_CHANNELS` now consults
            # CHANNEL A, whose hazards can WITHDRAW a page, so reading the constant here would move
            # this file's whole subject while its pins still claimed to be W6b-2's.
            pages, refused = RP.scenery_surface(blob, ef, channels=W6B2_CHANNELS)
            for pg in pages:
                self.pages[(ef, pg.cell[0], pg.cell[1])] = pg
                for n in self._hz_of(pg):
                    self.edit_hz[n].add((ef, pg.cell[0], pg.cell[1]))
            for r in refused:
                k = (ef, r.cell[0], r.cell[1])
                self.refusals[k].add(r.klass)
                self.reasons[k][r.klass] = r.reason
            # THE ACK SURFACE, only where channel P has anything to say.
            if ef in p_effects:
                apages, arefused = RP.scenery_surface(blob, ef, channels=W6B2_CHANNELS,
                                                      program_depth=True)
                for pg in apages:
                    k = (ef, pg.cell[0], pg.cell[1])
                    self.ack_pages[k] = pg
                    if pg.depth_source == "program":
                        t = RP.TexelTarget(name=pg.name, enabled=False, source="", page=pg,
                                           ack_program_depth=True)
                        self.ack_disclosures[k] = "  ".join(RP._scenery_disclosures(t))
                for r in arefused:
                    k = (ef, r.cell[0], r.cell[1])
                    self.ack_refusals[k].add(r.klass)
                    self.ack_reasons[k][r.klass] = r.reason

    # -- derived views
    def by_source(self, src: str) -> List[Tuple[int, int, int]]:
        return [k for k, p in self.pages.items() if p.depth_source == src]

    def refused_of(self, klass: str) -> List[Tuple[int, int, int]]:
        return sorted(k for k, v in self.refusals.items() if klass in v)


# --------------------------------------------------------------------------- I0
def i0_calibrate(D: Data) -> None:
    """CALIBRATE THE INSTRUMENT BEFORE JUDGING WITH IT.  Everything below rests on
    `reskin.page_depth_view` being the page-granular roll it claims to be, so it is checked against a
    roll written independently in this file, cell for cell, over all 372 containers -- and then
    pointed at the DOME, the one cell in the corpus that is depth-attributed by this rung, PROVEN
    DRAWN in-game, and free of every other hazard."""
    print("[I0] CALIBRATE -- the SHIPPED page view against an independent roll of the same records")
    chk("containers", len(D.paths), PIN["containers"])
    chk("the shipped view and this file's roll name the SAME cells",
        sorted(D.gview) == sorted(D.gmine), True)
    bad = [k for k in D.gview if D.gview[k] != D.gmine.get(k)]
    chk("... and state the same depths for every one of them", len(bad), 0)
    print("   %d containers . %d page-cells the container's own `so` records name a COLUMN depth for"
          % (len(D.paths), len(D.gview)))
    print("   the shipped `reskin.page_depth_view` == an independently written roll on %d/%d cells"
          % (len(D.gview) - len(bad), len(D.gview)))

    # KNOWN ANSWER: THE DOME.  ef211 (704,384) -- the readerless lower half the W6b-1 cast ladder
    # banded on screen (cast 1c's stripes attributed the rolling-fire dome to exactly this cell).
    dome = (211, 704, 384)
    chk("THE DOME is named by the page view", D.gview.get(dome), (8,))
    chk("... and the census could not name it", D.C[dome]["bpp"], None)
    chk("... its stacked partner the census DID know", D.C[(211, 704, 256)]["bpp"], 8)
    pg = D.pages[dome]
    chk("... and the kit now emits it", (pg.bpp, pg.depth_source, pg.depth_inherited),
        (8, "so-page", True))
    chk("... with ZERO readers, which is exactly why the census refused it", len(pg.hazards.readers), 0)
    chk("... and the PROGRAM is silent there -- not wrong, silent", pg.hazards.program_depths, ())
    print("   KNOWN ANSWER  ef211 (704,384) THE DOME: census UNKNOWN -> channel G 8bpp, inherited "
          "from the column its stacked partner is bound at; 0 readers, program READ only")


# --------------------------------------------------------------------------- I1
def i1_two_views(D: Data) -> None:
    """sec 7 ROW 1.  The two views agree on **138/140** overall and **16/18 on the informative rows**,
    and THE TWO EXCEPTIONS ARE FLAGGED, NOT RECONCILED.

    ⚠ BOTH PREDICATES ARE PRINTED, because they are not the same claim.  122 of the 140 ground-truth
    rows compare an `so` record AGAINST ITSELF -- an identity, not a test -- so the flat 138/140 is
    87 % tautological and the number that carries evidence is 16/18.  And the two rows that disagree
    are exactly the two GENUINELY DISJOINT ones: **every row that could have falsified the page
    predicate did**, and both are the spill-vs-own-page class this rung ships as a refusal.
    """
    print("[I1] ROW 1 -- the PAGE view vs the UV view: two views, kept apart, calibrated")

    def calibrate(view, binders):
        taut = partial = disjoint = independent = 0
        rows = agree = informative = informative_agree = 0
        flagged, ind_ids = [], []
        for k, r in D.C.items():
            depths = view.get(k)
            if r["bpp"] is None or depths is None or len(depths) != 1:
                continue
            rows += 1
            ok = int(depths[0] == r["bpp"])
            agree += ok
            readers = {int(x["geom"]) for x in r["readers"]}
            owners = binders.get(k, set())
            if not readers:
                # a NON-`so` witness -- the census read this cell's depth out of the id-4
                # model-package header, a source channel G never consults.
                independent += 1
                ind_ids.append(r["id"])
                informative += 1
                informative_agree += ok
            elif readers == owners:
                taut += 1                          # the same record on both sides: an IDENTITY
            else:
                if readers & owners:
                    partial += 1
                else:
                    disjoint += 1
                    if not ok:
                        flagged.append(r["id"])
                informative += 1
                informative_agree += ok
        return (rows, agree, taut, informative, informative_agree, disjoint, sorted(flagged),
                independent, sorted(ind_ids))

    # (a) THE RECORD'S OWN SCOPE: every CENSUS cell, id-4 creature pages included.  Reproduced here so
    # the shipped view can be compared against the number the record states rather than against a
    # re-scoped one nobody published.
    rows, agree, taut, inf, inf_ok, disjoint, flagged, ind, ind_ids = calibrate(
        D.gcensus, D.gcensus_binders)
    chk("ground-truth rows (the RECORD's scope)", rows, PIN["cal_g_rows"])
    chk("... agreeing overall", agree, PIN["cal_g_agree"])
    chk("... INFORMATIVE rows (the tautological ones removed)", inf, PIN["cal_g_informative"])
    chk("... agreeing on those", inf_ok, PIN["cal_g_informative_agree"])
    chk("the exceptions are FLAGGED, not reconciled", len(flagged), PIN["cal_g_flagged"])
    chk("... and by name", flagged, ["ef381.x640_y384", "ef447.x640_y384"])
    print("   'the two views agree %d/%d = %.4f'          -- TRUE, and %d of those rows compare an "
          "`so` record against ITSELF (%.0f %% tautological)"
          % (agree, rows, agree / float(rows), taut, 100.0 * taut / rows))
    print("   'and %d/%d = %.3f on the INFORMATIVE rows'   -- ALSO TRUE, and it is the number that "
          "carries evidence" % (inf_ok, inf, inf_ok / float(inf)))
    print("   the %d disagreements are FLAGGED by name and stay refused: %s"
          % (len(flagged), ", ".join(flagged)))

    # (b) ★ THE SHIPPED VIEW'S SCOPE IS ONE ROW SMALLER, AND THAT ROW IS THE RECORD'S OWN CAVEAT.
    # `page_depth_view` names only cells `page_cells` declares -- the SCENERY surface.  The single row
    # it drops is `ef179.x320_y384`, which sec 5 of the record calls the calibration's strongest
    # independent row AND then names as creature-class: *"Creature cells are precisely the population
    # this rung's attribution excludes BY RULE ... It is NOT a scenery datum."*  So the kit measuring
    # 139/137 rather than 140/138 is the record's own scoping applied, not a shortfall -- and BOTH
    # pairs are printed, because reconciling them would hide exactly the fact the record insists on.
    krows, kagree, ktaut, kinf, kinf_ok, _kd, kflag, kind, _ki = calibrate(D.gview, D.gbinders)
    chk("the SHIPPED view's rows (scenery only)", krows, PIN["kit_rows"])
    chk("... agreeing overall", kagree, PIN["kit_agree"])
    chk("... INFORMATIVE", kinf, PIN["kit_informative"])
    chk("... agreeing on those", kinf_ok, PIN["kit_informative_agree"])
    chk("the SHIPPED view flags the SAME two exceptions", kflag, flagged)
    dropped = sorted(set(D.gcensus) - set(D.gview))
    chk("the ONE ground-truth row the kit's scope drops", len(
        [k for k in dropped if D.C[k]["bpp"] is not None and len(D.gcensus[k]) == 1]), 1)
    row = [k for k in dropped if D.C[k]["bpp"] is not None and len(D.gcensus[k]) == 1][0]
    chk("...is ef179.x320_y384", D.C[row]["id"], "ef179.x320_y384")
    chk("...and it is CREATURE-class, which this rung excludes BY RULE",
        "creature" in D.C[row]["classes"], True)
    chk("...and the record counts it as the INDEPENDENT witness", ind_ids, ["ef179.x320_y384"])
    chk("...so the kit's informative set has none", kind, 0)
    print("   ** TWO SCOPES, BOTH PRINTED, NEITHER RECONCILED:")
    print("      the RECORD's scope (every census cell): %d/%d overall, %d/%d informative"
          % (agree, rows, inf_ok, inf))
    print("      the SHIPPED view's scope (SCENERY only): %d/%d overall, %d/%d informative"
          % (kagree, krows, kinf_ok, kinf))
    print("      the ONE row between them is %s -- %s.  The record itself says it is creature-class "
          "and 'NOT a scenery datum', so the kit dropping it is that caveat ENFORCED, not a loss."
          % (D.C[row]["id"], D.C[row]["classes"]))
    print("   -> DEPTH is a property of the PAGE; READERSHIP is a property of the UVs.  The kit keeps "
          "BOTH views; merging them is what produced the y=384 blind spot in the first place.")

    # THE NON-MERGER, as a structural fact rather than as a comment.
    with open(D.paths[0], "rb") as fh:
        blob = fh.read()
    a = RS.attribution(blob, include_direct=True)
    chk("the UV view grew no page-depth field", hasattr(a, "page_depths"), False)
    chk("`page_depth_view` is a SEPARATE entry point", callable(RS.page_depth_view), True)
    chk("...and it is exported as one", "page_depth_view" in RS.__all__, True)


# --------------------------------------------------------------------------- I2
def i2_rederivation_pin(D: Data) -> None:
    """sec 7 ROW 5 -- **THE RE-DERIVATION PIN**, on the `w6b_gates` G6 precedent.

    `depth_attribution.PROGRAM_DEPTH` is the one thing this rung CACHES: recovering it is a MIPS
    const-folding walk over 385 program images and a build cannot afford to re-run it.  So the cache
    is compared against the measurement's own output -- rolled here from the raw sweep hits and the
    census, at PAGE granularity, with this file's own decoder.  **A constant nobody re-checks is a
    claim.**
    """
    print("[I2] ROW 5 -- THE RE-DERIVATION PIN: the cached P table vs a fresh roll of the sweep")
    rolled: Dict[Tuple[int, int, int], Counter] = defaultdict(Counter)
    undeclared = 0
    for h in D.sweep["sweep"]["hits"]:
        px, py, bpp = dec(h["value"])
        cells = [c for c in cover(px, py) if (h["ef"], c[0], c[1]) in D.C]
        if not cells:
            undeclared += 1
            continue
        for c in cells:
            rolled[(h["ef"], c[0], c[1])][bpp] += 1
    chk("rolled cells", len(rolled), PIN["p_table_rows"])
    chk("the SHIPPED table names the same cells", sorted(rolled) == sorted(DA.PROGRAM_DEPTH), True)
    bad = []
    for k, cnt in rolled.items():
        rec = DA.PROGRAM_DEPTH.get(k)
        if rec is None:
            bad.append((k, "missing"))
            continue
        want_bpp = list(cnt)[0] if len(cnt) == 1 else None
        if (rec.bpp, rec.depths, rec.call_sites) != (want_bpp, tuple(sorted(cnt)), sum(cnt.values())):
            bad.append((k, (rec.bpp, rec.depths, rec.call_sites)))
    chk("EQUALITY, cell for cell: depth, depth set and call-site count", len(bad), 0)
    single = [v for v in DA.PROGRAM_DEPTH.values() if not v.dual]
    dual = [v for v in DA.PROGRAM_DEPTH.values() if v.dual]
    chk("unanimous rows", len(single), PIN["p_single"])
    chk("MULTI-VALUED rows", len(dual), PIN["p_dual"])
    chk("...in this many containers", len({v.effect for v in dual}), PIN["p_dual_containers"])
    print("   %d cells re-rolled from %d raw sweep hits (%d hits name a column their container never "
          "uploads and attribute NOTHING)"
          % (len(rolled), len(D.sweep["sweep"]["hits"]), undeclared))
    print("   the shipped constant matches on %d/%d cells -- depth, depth SET and call-site count"
          % (len(rolled) - len(bad), len(rolled)))
    print("   %d unanimous . %d MULTI-VALUED in %d containers (a refusal, never a majority)"
          % (len(single), len(dual), len({v.effect for v in dual})))
    # the import-time pins the module asserts about ITSELF, re-stated here from the outside
    chk("the module's own arithmetic closes",
        DA.GAIN_EITHER + DA.RESIDUE_BLIND + DA.RESIDUE_COVERED, DA.DEPTH_UNKNOWN)
    chk("189 + 57 == 246", DA.GAIN_PROGRAM + DA.GAIN_SO_PAGE, PIN["gain_either"])
    chk("2,385 - 246 == 2,139", DA.DEPTH_UNKNOWN - DA.GAIN_EITHER, PIN["residue"])
    print("   COUNT PINS, asserted at IMPORT so a truncated table fails loudly: %d + %d + %d = %d ; "
          "%d - %d = %d" % (DA.GAIN_EITHER, DA.RESIDUE_BLIND, DA.RESIDUE_COVERED, DA.DEPTH_UNKNOWN,
                            DA.DEPTH_UNKNOWN, DA.GAIN_EITHER, DA.RESIDUE))


# --------------------------------------------------------------------------- I3
def i3_dual_classes(D: Data) -> None:
    """sec 7 ROWS 3 + 4 -- the two DUAL-DEPTH refusals, RE-DERIVED PER RUN from the shipping code.

    22 program cells in 10 containers, 8 channel-G cells, overlap 0 -- so the refused-ambiguous set is
    **32, not the 24 the lane dossiers hand off**.  The 8 are named in NO dossier: a lane that built
    its refusal list from the attribution sweep alone would ship every one of them UNLISTED, which is
    exactly why the kit derives that class LIVE from the container instead of caching it.
    """
    print("[I3] ROWS 3+4 -- the two DUAL-DEPTH refusals, re-derived from the shipped derivation")
    pdual = D.refused_of("program-dual-depth")
    gdual = D.refused_of("channel-g-dual-depth")
    spill = D.refused_of("spill-vs-own-page")
    chk("PROGRAM-DUAL-DEPTH cells", len(pdual), PIN["p_dual"])
    chk("...in this many containers", len({k[0] for k in pdual}), PIN["p_dual_containers"])
    chk("CHANNEL-G-DUAL-DEPTH cells", len(gdual), PIN["g_dual"])
    chk("the two sets are DISJOINT", len(set(pdual) & set(gdual)), PIN["ambiguous_overlap"])
    chk("the refused-ambiguous set", len(pdual) + len(gdual) + len(spill), PIN["refused_ambiguous"])
    chk("every program-dual cell is UNADDRESSABLE", "program-dual-depth" in RP._UNADDRESSABLE, True)
    chk("every channel-G-dual cell is UNADDRESSABLE", "channel-g-dual-depth" in RP._UNADDRESSABLE,
        True)
    chk("...and neither has a page", len([k for k in pdual + gdual if k in D.pages]), 0)
    print("   PROGRAM-DUAL %d cells in %d containers . CHANNEL-G-DUAL %d cells . SPILL %d cells "
          "-> the refused set is %d, NOT the dossiers' 24"
          % (len(pdual), len({k[0] for k in pdual}), len(gdual), len(spill),
             len(pdual) + len(gdual) + len(spill)))
    print("   the %d channel-G ambiguities, BY NAME (no lane dossier lists them): %s"
          % (len(gdual), ", ".join(D.C[k]["id"] for k in gdual)))
    print("   THREE POPULATIONS, ANNOTATED SO NOBODY ADDS THEM UP: the %d program-dual and %d "
          "channel-G-dual cells are INSIDE W6b-1's 2,385; the %d spill cells are OUTSIDE it entirely "
          "-- they HAD a depth and now have two." % (len(pdual), len(gdual), len(spill)))
    # UNANIMITY IS THE VERDICT RULE, at the call site rather than in a docstring.
    for k in pdual[:3] + gdual[:3]:
        klass = "program-dual-depth" if k in set(pdual) else "channel-g-dual-depth"
        chk("%s says why" % D.C[k]["id"],
            "HAZARD, NOT A VOTE" in D.reasons[k][klass] or "TWO different depths"
            in D.reasons[k][klass], True)


# --------------------------------------------------------------------------- I4
def i4_spill_class(D: Data) -> None:
    """sec 7 ROW 2 -- and the gate the record wrote in its own words:

        ⚠ state it plainly: it adds 0 cells to the refused set as PROTECTION (both already refuse on
        other hazards).  It is non-vacuous as a PREDICATE and exists to carry the REASON.
        **A gate asserting it protects >= 1 new cell would fail.**

    So this asserts **== 0**, and it asserts it on the two things "protection" can mean in the kit:
    a cell that stops RESOLVING (`texel_page` refuses by name) and a cell that stops being EXPORTED.

    ⚠ **AND THE SECOND ONE IS A COUNTERFACTUAL, NOT AN IDENTITY** -- the first draft of this gate
    asked *"which spill cells carry an export-blocking class and NOTHING ELSE?"*, which is empty for
    every possible corpus because ``spill-vs-own-page`` is asserted three lines above NOT to be in
    that set.  It could not have returned anything but 0 whether or not the class protected something,
    i.e. it was not evidence.  What is measured instead is `export_art`'s own predicate run TWICE --
    once with the shipped `_EXPORT_BLOCKING` and once with the class ADDED -- and the two exported-cell
    sets asserted identical.  The 0 is then a fact about the corpus (both cells already carry an
    export-blocking class of their own), and a later round that moved the class into the blocking set
    would turn this red instead of silently keeping a green board.
    """
    print("[I4] ROW 2 -- SPILL-vs-OWN-PAGE: non-vacuous as a PREDICATE, zero as PROTECTION")
    spill = D.refused_of("spill-vs-own-page")
    chk("spill-conflict cells", len(spill), PIN["spill_cells"])
    chk("...by name", sorted(D.C[k]["id"] for k in spill),
        ["ef381.x640_y384", "ef447.x640_y384"])
    chk("the class is NOT unaddressable", "spill-vs-own-page" in RP._UNADDRESSABLE, False)
    chk("the class does NOT block export", "spill-vs-own-page" in RP._EXPORT_BLOCKING, False)
    newly_unaddr = [k for k in spill if k not in D.pages]
    chk("cells this class newly makes UNADDRESSABLE", len(newly_unaddr),
        PIN["spill_newly_unaddressable"])
    # THE COUNTERFACTUAL: `export_art`'s filter, re-run over the two containers with the class in the
    # blocking set, against the same filter as shipped.  `export_art` writes PNGs, so the PREDICATE is
    # what is driven here (`{r.name for r in refusals if r.klass in BLOCKING}` filtered by bpp lane) --
    # the same expression the shipped function evaluates, read off the shipped constant.
    counterfactual = RP._EXPORT_BLOCKING | frozenset(("spill-vs-own-page",))
    shipped_cells, blocked_cells = set(), set()
    for ef in sorted({k[0] for k in spill}):
        with open(os.path.join(SCRATCH, "ef%03d.bytes" % ef), "rb") as fh:
            blob = fh.read()
        pages, refusals = RP.scenery_surface(blob, ef, channels=RP.LICENSED_CHANNELS)
        for blocking, sink in ((RP._EXPORT_BLOCKING, shipped_cells),
                               (counterfactual, blocked_cells)):
            names = {r.name for r in refusals if r.klass in blocking}
            sink |= {(ef, p.name) for p in pages if p.bpp in (4, 8, 15) and p.name not in names}
    chk("cells this class newly blocks from EXPORT", len(shipped_cells - blocked_cells),
        PIN["spill_newly_export_blocked"])
    chk("...and the two exported-cell sets are IDENTICAL", shipped_cells == blocked_cells, True)
    chk("...on a NON-EMPTY export surface (a vacuous set would prove nothing)",
        len(shipped_cells) > 0, True)
    print("   COUNTERFACTUAL: `_EXPORT_BLOCKING` re-run WITH the class added -- %d exported cells "
          "either way, delta %d.  Both spill cells already carry an export-blocking class of their "
          "own (%s), so the class protects nothing NEW -- which is the row's claim, measured."
          % (len(shipped_cells), len(shipped_cells - blocked_cells),
             " . ".join("%s: %s" % (D.C[k]["id"],
                                    ",".join(sorted(D.refusals[k] & RP._EXPORT_BLOCKING)))
                        for k in spill)))
    for k in spill:
        pg = D.pages[k]
        chk("%s still resolves" % D.C[k]["id"], pg.bpp, D.C[k]["bpp"])
        chk("%s already refuses through the u-spill remedy" % D.C[k]["id"],
            bool(pg.hazards.spill_in), True)
        chk("%s carries the hazard slug" % D.C[k]["id"], "spill-vs-own-page" in pg.hazards.names,
            True)
        chk("%s prints BOTH predicates" % D.C[k]["id"],
            "BOTH PREDICATES ARE TRUE OF THE SAME BYTES" in D.reasons[k]["spill-vs-own-page"], True)
        print("   %s  readers bind the NEIGHBOURING page at %dbpp . this cell's own page is named at "
              "%dbpp -> both true, FLAGGED, neither picked"
              % (D.C[k]["id"], pg.hazards.depths[0], pg.hazards.page_depths[0]))
    print("   PROTECTION DELTA: %d cells newly unaddressable, %d newly export-blocked -- the second "
          "measured as a COUNTERFACTUAL rather than as an identity.  The class is a REASON, not a "
          "gate, and saying so is the point of the row."
          % (len(newly_unaddr), len(shipped_cells - blocked_cells)))


# --------------------------------------------------------------------------- I5
def i5_channel_g(D: Data) -> None:
    """sec 7 ROW 8 -- **CORRECTED BEFORE IT WAS PROPOSED**: *"the 57 cells build"* is FALSE.

    57 gain a depth; **56 clear every REFUSAL; 1 refuses on a program write** (ef038, whose id-3
    program is a VRAM writer).  55 of the 57 are lower halves, buildable ONLY through the per-cell map
    W6b-1 shipped -- which is why this row depends on row 9's census re-stamp landing too.

    ⚠ **AND THE SPLIT IS THREE-WAY, NOT TWO-WAY.**  Of the 56, **49 are hazard-clean and 7 carry the
    class-C multi-palette DISCLOSURE**: their COLUMN is bound with two or three different CLUT keys,
    so one index array has two or three renderings exactly as a multi-reader cell does.  That was
    invisible while class-C evidence was read off READERS -- which a readerless cell has none of --
    and 56 + 1 read clean only because the predicate could not fire.

    And the other half of the row, which is the part that could have gone wrong silently: **the 57
    flow through EVERY OTHER hazard gate unchanged.**  Six W6b-1 hazard populations are re-measured
    here ON BOTH SURFACES: all six are their W6b-1 numbers on the CENSUS surface, and five of the six
    are unmoved on the EDIT surface too.  The sixth is the class-C one above, and both numbers are
    printed rather than reconciled.
    """
    print("[I5] ROW 8 -- CHANNEL G adopted as a depth SOURCE: 57 gain / 56 clear every REFUSAL / "
          "49 of those are hazard-clean and 7 disclose class C / 1 refuses")
    # ★ FIRST, THE THING THAT MAKES THE OTHER SIBLING GATES MEAN ANYTHING.  `scenery_surface`'s own
    # DEFAULT is `CENSUS_CHANNELS`, so its output is W6b-1's byte for byte -- 187 read, 2,385 dark,
    # and NONE of the three new refusal classes stated.  `w6b_gates` G6 and `w6q_gates` G1/G16 pin
    # that population; a rung that re-aimed the function under them would have left three green
    # boards measuring something else.  The precedent is `attribution(include_direct=)`: a PARAMETER,
    # never a second derivation, with the default chosen so no published count moves.
    chk("the CENSUS default still reads W6b-1's readable set", len(D.census_pages),
        PIN["so_uv_cells"])
    chk("...and W6b-1's dark set", len(D.census_dark), PIN["depth_unknown_before"])
    chk("...and states NONE of the three new classes",
        sorted(D.census_klasses & {"program-dual-depth", "channel-g-dual-depth",
                                   "spill-vs-own-page"}), [])
    print("   CENSUS_CHANNELS (the default): %d readable + %d dark -- W6b-1, byte for byte, and NOT "
          "ONE of the three new refusal classes is stated through it.  A channel a caller declines "
          "to consult cannot deliver a verdict it declined to check."
          % (len(D.census_pages), len(D.census_dark)))
    uv = D.by_source("so-uv")
    gp = D.by_source("so-page")
    chk("cells with an `so` READER (W6b-1's own number)", len(uv), PIN["so_uv_cells"])
    chk("cells CHANNEL G licenses", len(gp), PIN["gain_so_page"])
    chk("CHANNEL P is SHUT without the acknowledgement", len(D.by_source("program")), 0)
    chk("all of channel G's cells are y=384 lower halves of their COLUMN",
        sum(1 for k in gp if k[2] % PAGE_LINES), len(gp))
    # every class that denies an editable picture.  `program-depth-no-palette` is listed for
    # completeness and can never fire here BY CONSTRUCTION -- it is channel P's, and a channel-G cell
    # inherits its KEY from the same record as its depth.  Listing it is how that stays checked rather
    # than assumed: if it ever appeared on a so-page cell, `g_clean` would move and this would go red.
    blocking = {"program-vram-write", "program-moveimage-cell", "program-vram-unknown",
                "same-bytes-two-depths", "no-declared-clut", "program-depth-no-palette"}
    refusing = [k for k in gp if D.refusals[k] & blocking]
    chk("...that clear every REFUSAL", len(gp) - len(refusing), PIN["g_clean"])
    chk("...and the ones that do not", len(refusing), PIN["g_refusing"])
    chk("...by name", sorted(D.C[k]["id"] for k in refusing), ["ef038.x512_y384"])
    chk("...on a PROGRAM WRITE", sorted(D.refusals[refusing[0]]) if refusing else [],
        ["program-vram-write"])
    chk("channel-G cells that are a tall rect's LOWER HALF (per WRITER)",
        sum(1 for k in gp if D.pages[k].hazards.lower_half), PIN["g_lower_halves"])
    print("   57 gain / %d clear every REFUSAL / %d refuses -- %s, on %s"
          % (len(gp) - len(refusing), len(refusing),
             ", ".join(D.C[k]["id"] for k in refusing),
             ", ".join(sorted(D.refusals[refusing[0]])) if refusing else "-"))
    print("   %d of the %d are a tall rect's LOWER HALF: addressable ONLY through the per-cell map "
          "W6b-1 shipped (the other %d are id-9 alternate blocks, one whole upload each)"
          % (PIN["g_lower_halves"], len(gp), len(gp) - PIN["g_lower_halves"]))
    print("   ...and EVERY one of them declares a palette: %d/%d resolve a CLUT or are 15bpp direct"
          % (sum(1 for k in gp if D.pages[k].bpp == 15 or D.pages[k].clut_offset is not None),
             len(gp)))

    # ★ THE SIX POPULATIONS, ON BOTH SURFACES -- five unmoved, ONE moved ON PURPOSE.
    #
    # The claim "the 57 flow through every other hazard gate unchanged" is about the CENSUS
    # populations, and that is where they are measured.  On the EDIT surface one of the six is larger,
    # and it has to be: `multi_palette` reads `palette_cells`, and class-C evidence is taken at the
    # SAME GRANULARITY AS THE DEPTH.  Fed from READERS -- which a readerless cell has none of -- the
    # predicate is False BY CONSTRUCTION over the whole channel-G surface, so 7 cells whose COLUMN is
    # bound with 2-3 different CLUT keys would ship ONE of those renderings with no class-C line and
    # no alternate PNG: LESS honest on the newly licensed path than W6b-1 was on the old one, on
    # evidence the kit already held.  A predicate that cannot fire on a surface is not a measurement
    # of that surface, so the 25-vs-32 delta is a fix and both numbers are printed.
    for name, pin in (("two_depths", PIN["hz_two_depths"]),
                      ("multi_palette", PIN["hz_multi_palette"]),
                      ("shared_read", PIN["hz_shared_read"]), ("spill_in", PIN["hz_spill_in"]),
                      ("co_transform", PIN["hz_co_transform"])):
        chk("hz %s (CENSUS surface -- W6b-1's own)" % name, len(D.census_hz[name]), pin)
    chk("hz spill-touched (CENSUS surface)",
        len(D.census_hz["spill_in"] | D.census_hz["spill_out"]), PIN["hz_spill_touched"])
    for name, pin in (("two_depths", PIN["hz_two_depths"]),
                      ("shared_read", PIN["hz_shared_read"]), ("spill_in", PIN["hz_spill_in"]),
                      ("co_transform", PIN["hz_co_transform"])):
        chk("hz %s (EDIT surface -- unmoved)" % name, len(D.edit_hz[name]), pin)
    chk("hz spill-touched (EDIT surface -- unmoved)",
        len(D.edit_hz["spill_in"] | D.edit_hz["spill_out"]), PIN["hz_spill_touched"])
    gmulti = sorted(D.edit_hz["multi_palette"] - D.census_hz["multi_palette"])
    chk("hz multi-palette (EDIT surface)", len(D.edit_hz["multi_palette"]),
        PIN["hz_multi_palette_edit"])
    chk("...the delta is exactly the channel-G class-C cells", len(gmulti), PIN["g_multi_palette"])
    chk("...and every one of them IS a channel-G cell", len([k for k in gmulti if k in set(gp)]),
        len(gmulti))
    print("   FIVE POPULATIONS UNMOVED ON BOTH SURFACES: two-depths %d . shared-read %d . spill-in "
          "%d . spill-touched %d . co-transform %d"
          % (len(D.edit_hz["two_depths"]), len(D.edit_hz["shared_read"]), len(D.edit_hz["spill_in"]),
             len(D.edit_hz["spill_in"] | D.edit_hz["spill_out"]), len(D.edit_hz["co_transform"])))
    print("   ...AND THE SIXTH MOVES, ON PURPOSE: multi-palette %d on the CENSUS surface (W6b-1, "
          "unmoved) and %d on the EDIT surface.  The %d new ones are channel-G cells whose COLUMN is "
          "bound with more than one CLUT key -- class-C evidence read at the granularity the DEPTH "
          "was read at.  A predicate fed from readers is False by construction on a readerless cell."
          % (len(D.census_hz["multi_palette"]), len(D.edit_hz["multi_palette"]), len(gmulti)))
    print("      by name: %s" % ", ".join(
        "%s (%d keys)" % (D.C[k]["id"], len(D.pages[k].hazards.palette_cells)) for k in gmulti))
    # ...and the class-C machinery really RUNS on them: the alternate rows are the read-only `.as-`
    # views `export_art` writes, and they were EMPTY on every readerless cell before this round.
    alts = 0
    for ef in sorted({k[0] for k in gmulti}):
        with open(os.path.join(SCRATCH, "ef%03d.bytes" % ef), "rb") as fh:
            blob = fh.read()
        pmap = RS.palette_map(blob, effect=ef)
        for k in [k for k in gmulti if k[0] == ef]:
            pg = D.pages[k]
            rows = RP.alternate_palette_rows(blob, pg, pmap)
            chk("%s names its alternate key(s)" % D.C[k]["id"], len(rows),
                len(pg.hazards.palette_cells) - 1)
            # ...and the DISCLOSURE names them too.  Built from `readers` the class-C line printed its
            # headline and then an EMPTY list -- a disclosure that says a second rendering exists and
            # declines to say which is not a disclosure.
            dis = "  ".join(RP._scenery_disclosures(
                RP.TexelTarget(name=pg.name, enabled=False, source="", page=pg)))
            chk("%s's class-C line NAMES the other key(s)" % D.C[k]["id"],
                all("CLUT %s" % (c,) in dis for c in pg.hazards.page_clut_cells[1:])
                and "MULTI-PALETTE (class C)" in dis, True)
            alts += len(rows)
    chk("alternate renderings now NAMED that were structurally invisible", alts,
        PIN["g_alternate_rows"])
    print("   ...and %d alternate rendering(s) are named across those %d cells -- the `.as-` PNGs "
          "`export_art` writes.  Before this round `alternate_palette_rows` read `hazards.readers` "
          "and returned () on every one of them." % (alts, len(gmulti)))
    # THE THREE-WAY SPLIT OF THE 57, so no single number reads as the whole story.
    clean = [k for k in gp if not (D.refusals[k] & blocking) and not D.pages[k].hazards.multi_palette]
    chk("channel-G cells that are HAZARD-clean", len(clean), PIN["g_hazard_clean"])
    chk("49 + 7 + 1 == 57", len(clean) + len(gmulti) + len(refusing), PIN["gain_so_page"])
    print("   THE 57, SPLIT THREE WAYS AND NOT TWO: %d hazard-clean + %d class-C disclosures + %d "
          "refused on a program write = %d"
          % (len(clean), len(gmulti), len(refusing), len(gp)))


# --------------------------------------------------------------------------- I6
def i6_refusal_matrix(D: Data) -> None:
    """sec 7 ROW 6 -- the refusal matrix NAMES the new strings, and the depth-unknown reason DISCLOSES.

    W6b-1's reason said *"the container states no depth for this cell"*.  W6b-2 measured that this is
    false for a large minority, so the reason now names WHICH: the program's own registered depth and
    its call-site count, or the container's CLUT-arity NARROWING (and which of the two narrowings it
    is), or neither.  **And when it names a program depth it carries the in-game refutation in the
    same breath** -- a caveat that travels separately from the number is a caveat nobody reads.
    """
    print("[I6] ROW 6 -- the refusal matrix names the new strings; depth-unknown DISCLOSES")
    for k in ("program-dual-depth", "channel-g-dual-depth", "spill-vs-own-page"):
        chk("the matrix names %r" % k, k in RP._REFUSAL_TEXT, True)
    dark = D.refused_of("depth-unknown")
    chk("cells still refused as depth-unknown", len(dark), PIN["depth_unknown_after"])

    # (a) the cells where CHANNEL P speaks: the reason must name the depth, the sites and the cast.
    p_disclosed = [k for k in dark if DA.program_depth(k[0], (k[1], k[2])) is not None]
    chk("depth-unknown cells channel P speaks for", len(p_disclosed), PIN["gain_program"])
    miss = []
    promised = wrongly_promised = 0
    for k in p_disclosed:
        why = D.reasons[k]["depth-unknown"]
        rec = DA.program_depth(k[0], (k[1], k[2]))
        for token in ("no `so` reader samples this cell",
                      "registers this page at %d bpp at %d call site(s)"
                      % (rec.bpp, rec.call_sites),
                      "REGISTRATION-IS-NOT-A-DRAW, CONFIRMED IN-GAME", "ef251", "tpage 312",
                      "BUMPER STRIP", "THE DEPTH COROLLARY", "ef446", DA.ACK_KEY):
            if token not in why:
                miss.append((D.C[k]["id"], token))
        # ★ AND THE REMEDY SENTENCE IS CHECKED AGAINST WHAT THE KIT CAN ACTUALLY DELIVER.  Channel P
        # states a DEPTH and names no CLUT, so on an INDEXED cell the ack + a matching `expect_bpp`
        # are necessary conditions that are not sufficient ones -- the cell refuses for want of a KEY
        # whatever is acknowledged.  A disclosure that offers a remedy it does not have is the same
        # defect as one that says nothing; both leave the author with a false model of the gate.
        if rec.bpp == 15:
            promised += 1
            for token in ("To edit it anyway say", "expect_bpp = 15"):
                if token not in why:
                    miss.append((D.C[k]["id"], token))
        else:
            if "THE ACKNOWLEDGEMENT CANNOT REACH THIS CELL" not in why:
                miss.append((D.C[k]["id"], "the ack-cannot-reach clause"))
            if "To edit it anyway say" in why:
                wrongly_promised += 1
    chk("every P-disclosed reason carries the derivation AND the refutation", len(miss), 0)
    chk("...and only the DIRECT cells are offered the ack path", promised, PIN["p_direct_cells"])
    chk("...with the indexed ones promised NOTHING the kit cannot deliver", wrongly_promised, 0)
    print("   %d of the %d still-refused cells carry a PROGRAM-DERIVED depth in their reason string, "
          "each naming its bpp, its call-site count and `%s`" % (len(p_disclosed), len(dark),
                                                                 DA.ACK_KEY))
    print("   ...and the REMEDY is offered to %d of them (the 15bpp DIRECT ones) and withheld from "
          "the other %d BY NAME: channel P states a depth and no CLUT, so an indexed cell has no key "
          "and the ack cannot reach it." % (promised, len(p_disclosed) - promised))
    print("   ...and each of them carries the IN-GAME REFUTATION with the number: ef251's x512 family,"
          " program-registered tpage 312 = 15bpp, drew a 4-cycle 'BUMPER STRIP' -- a 4bpp read.")

    # (b) CHANNEL H: the reason says WHICH narrowing, and only where the container declares one.
    hint_cells = [k for k in dark if DA.clut_arity_hint(*D.arity[k[0]]) is not None]
    said = [k for k in hint_cells if "CHANNEL H" in D.reasons[k]["depth-unknown"]]
    silent_wrong = [k for k in dark
                    if DA.clut_arity_hint(*D.arity[k[0]]) is None
                    and "CHANNEL H" in D.reasons[k]["depth-unknown"]]
    chk("every hint-carrying cell SAYS which narrowing", len(said), len(hint_cells))
    chk("...and no cell invents one", len(silent_wrong), 0)
    kinds = Counter(DA.clut_arity_hint(*D.arity[k[0]]) for k in hint_cells)
    # ...and the SAME rule over W6b-1's WHOLE 2,385, so the smaller in-residue count above is visibly
    # the same measurement on a smaller population rather than a quiet drift.
    was = [k for k, r in D.C.items()
           if "creature" not in r["classes"] and r["hz_depth_unknown"]
           and DA.clut_arity_hint(*D.arity[k[0]]) is not None]
    wkinds = Counter(DA.clut_arity_hint(*D.arity[k[0]]) for k in was)
    chk("CHANNEL H over W6b-1's whole 2,385", len(was), PIN["hint_in_2385"])
    chk("... narrowed toward 4bpp-or-15bpp", wkinds[4], PIN["hint_4bpp"])
    chk("... narrowed toward the 8bpp family", wkinds[8], PIN["hint_8bpp"])
    print("   CHANNEL H (a NARROWING, not a depth): %d of the %d refused cells carry one -- %d toward "
          "'4bpp or 15bpp', %d toward '8bpp or 15bpp'.  'the container states nothing about this "
          "cell' is FALSE for all of them, and the reason says so."
          % (len(hint_cells), len(dark), kinds[4], kinds[8]))
    print("   ...over W6b-1's WHOLE 2,385 the same rule speaks for %d (%d / %d) -- the record's own "
          "figure; the %d above is that measurement on the %d cells still refused, not a drift."
          % (len(was), wkinds[4], wkinds[8], len(hint_cells), len(dark)))
    # CALIBRATE the kit's own arity derivation against the census's independently recorded one.
    arity_bad = [k for k in D.C
                 if D.C[k]["container_nclut4"] is not None
                 and (D.C[k]["container_nclut4"], D.C[k]["container_nclut8"]) != D.arity[k[0]]]
    chk("the kit's `clut_arity` == the census's own nClut4/nClut8", len(arity_bad), 0)
    print("   ...and `repaint.clut_arity` reproduces the census's own nClut4/nClut8 on %d/%d cells"
          % (len(D.C) - len(arity_bad), len(D.C)))


# --------------------------------------------------------------------------- I7
_ACK = DA.ACK_KEY


def _spec(blob: bytes, effect: int, row: dict) -> dict:
    """A minimal one-row texel spec against a REAL container, guarded by its own sha.  The row is
    ``enabled = false`` throughout: every rung of the ladder below is decided BEFORE a single PNG is
    opened, which is itself part of the claim -- an author must not have to produce art to be told
    the depth channel refuses."""
    import hashlib
    r = dict(row)
    r.setdefault("enabled", False)
    return {"reskin": {"effect": effect, "label": "w6b2i",
                       "expect_sha256": hashlib.sha256(blob).hexdigest(), "texel": [r]}}


def i7_ack_ladder(D: Data) -> None:
    """sec 7 ROW 7 -- **an ack without a matching `expect_bpp` must FAIL BY NAME; a mismatching one
    must FAIL BY NAME.**  Driven through `repaint.build` on REAL corpus containers, so the ladder is
    tested on the path an author actually walks rather than on a helper.

    The vehicles are chosen so nothing else can supply the refusal: **ef090** registers `(448,256)` at
    ONE depth, 15bpp (a direct cell indexes no palette, so channel P's silence about CLUTs is not a
    second variable) and its program is neither a VRAM writer nor a reader; **ef056** registers the
    SAME cell at TWO depths and is the hazard-outranks-the-ack case.

    ★ **AND THE POPULATION THE 15bpp VEHICLE SCOPES AROUND IS MEASURED FIRST, not left implicit.**
    "15bpp on purpose, so channel P's silence about CLUTs is not a second variable" is a sound choice
    of vehicle and an unsound choice of COVERAGE: that silence is exactly what stops **134 of the 189
    cells** -- every 4bpp and 8bpp one -- from ever rendering, ack or no ack.  So the ack's reach is
    re-measured over the whole channel before the ladder runs, and the ladder gains an INDEXED rung.
    """
    print("[I7] ROW 7 -- the acknowledgement ladder, on the real build path, failing BY NAME")
    ef_ok, cell, bpp = 90, "cell.s0.x448_y256", 15
    ef_dual = 56
    #: ★ THE INDEXED VEHICLE, the one the 15bpp ladder cannot exercise: ef093 registers the SAME cell
    #: at ONE depth, 8bpp, and its program is CLEAN -- so nothing but the missing KEY can refuse it.
    ef_idx, idx_bpp = 93, 8
    BLOBS = {}
    for _ef in (ef_ok, ef_dual, ef_idx):
        with open(os.path.join(SCRATCH, "ef%03d.bytes" % _ef), "rb") as fh:
            BLOBS[_ef] = fh.read()
    good, bad = BLOBS[ef_ok], BLOBS[ef_dual]
    chk("the vehicle's cell is depth-unknown without the ack",
        "depth-unknown" in D.refusals[(ef_ok, 448, 256)], True)
    chk("the vehicle's channel-P derivation", DA.program_depth(ef_ok, (448, 256)).bpp, bpp)
    chk("the dual vehicle's derivation is MULTI-VALUED",
        DA.program_depth(ef_dual, (448, 256)).dual, True)

    # ---- (0) ★ THE ACK'S REACH, OVER THE WHOLE CHANNEL, from the ACK surface the shipped code emits.
    pcells = {k: pg for k, pg in D.ack_pages.items() if pg.depth_source == "program"}
    chk("channel-P cells emitted under the ack", len(pcells), PIN["gain_program"])
    direct = [k for k in pcells if pcells[k].bpp == 15]
    indexed = [k for k in pcells if pcells[k].bpp != 15]
    nokey = [k for k in indexed if "program-depth-no-palette" in D.ack_refusals[k]]
    other = [k for k in indexed if k not in set(nokey)]
    resolvable = [k for k in pcells if not (D.ack_refusals[k] & RP._UNADDRESSABLE)]
    buildable = [k for k in pcells if not D.ack_refusals[k]]
    chk("...15bpp DIRECT (the ack's live surface)", len(direct), PIN["p_direct_cells"])
    chk("...INDEXED, which channel P states no key for", len(indexed), PIN["p_indexed_cells"])
    chk("...refusing `program-depth-no-palette`", len(nokey), PIN["p_no_palette"])
    chk("...refusing EARLIER on a program-VRAM verdict", len(other), PIN["p_indexed_other"])
    chk("...and NOT ONE indexed cell renders", len([k for k in indexed if not D.ack_refusals[k]]), 0)
    chk("cells `texel_page` hands back under the ack", len(resolvable), PIN["p_resolvable"])
    chk("...with no refusal of any kind (all 15bpp)", len(buildable), PIN["p_buildable"])
    chk("...and every one of those is DIRECT", len([k for k in buildable if pcells[k].bpp != 15]), 0)
    chk("the no-palette class is UNADDRESSABLE", "program-depth-no-palette" in RP._UNADDRESSABLE,
        True)
    # THE REASON MUST NOT QUOTE A READER THAT DOES NOT EXIST.  This is what the class was minted for:
    # `no-declared-clut`'s text is written about an `so` record, and channel P applies exactly where
    # there is none -- it printed `None` at `0` entries as if they were measurements.
    liar = [k for k in nokey if "the reader's `so` record" in D.ack_reasons[k].get(
        "program-depth-no-palette", "")]
    chk("...and no reason quotes an `so` reader on a cell that has none", len(liar), 0)
    chk("...nor prints a None/0 as if it were a measurement",
        len([k for k in nokey if "CLUT cell None at 0 entries"
             in D.ack_reasons[k]["program-depth-no-palette"]]), 0)
    chk("no channel-P cell refuses under the READER-shaped class at all",
        len([k for k in pcells if "no-declared-clut" in D.ack_refusals[k]]), 0)
    print("   THE ACK'S REACH, MEASURED BEFORE THE LADDER: %d cells / %d DIRECT + %d INDEXED; of the "
          "indexed, %d refuse for want of a KEY and %d refuse earlier on a program-VRAM verdict -- "
          "NONE render.  %d resolve through `texel_page` and %d carry no refusal at all, every one of "
          "them 15bpp."
          % (len(pcells), len(direct), len(indexed), len(nokey), len(other), len(resolvable),
             len(buildable)))

    # ---- (0b) ★ THE INHERITANCE CLAUSE IS GATED ON THE COLUMN, NOT ON THE WRITER'S RECT.  10 corpus
    # channel-P cells sit at y = 384 as id-9 ALTERNATE BLOCKS: one whole 0x4000 upload each, so
    # `hazards.lower_half` is False on all 10 while `ProgramDepth.inherited` is True.  Gated on the
    # writer, those 10 were told their depth was direct -- a disclosure saying LESS than it measured.
    id9_low = [k for k in pcells if k[2] % PAGE_LINES and not pcells[k].hazards.lower_half]
    chk("channel-P cells at y=384 that are NOT a rect's lower half", len(id9_low), PIN["p_id9_lower"])
    chk("...and the kit's own per-cell predicate calls every one of them INHERITED",
        len([k for k in id9_low if DA.program_depth(k[0], (k[1], k[2])).inherited]), len(id9_low))
    said = [k for k in id9_low if "LOWER half of its column" in D.ack_disclosures[k]]
    chk("...and the DISCLOSURE says so on every one", len(said), len(id9_low))
    upper = [k for k in pcells if not k[2] % PAGE_LINES]
    chk("...while no UPPER half claims a crossing it did not make",
        len([k for k in upper if "LOWER half of its column" in D.ack_disclosures[k]]), 0)
    print("   THE INHERITANCE CLAUSE: %d channel-P cells are id-9 alternate blocks at y = 384 -- "
          "`lower_half` False, column-inherited TRUE -- and all %d now carry the clause; %d upper "
          "halves carry none.  A page word names a PAGE; the crossing is a property of the COLUMN."
          % (len(id9_low), len(said), len(upper)))

    def refuses(spec, *tokens):
        try:
            RP.build(spec, "w6b2i", blob=BLOBS[spec["reskin"]["effect"]])
        except RP.RepaintError as e:
            missing = [t for t in tokens if t not in str(e)]
            return (True, missing, str(e).splitlines()[0][:110])
        return (False, list(tokens), "BUILT -- no refusal at all")

    # (1) NO ACK AT ALL -- the default posture.  DISCLOSE means the reason is richer, not that the
    #     cell resolves.
    ok, missing, first = refuses(_spec(good, ef_ok, {"name": cell}),
                                 "is REFUSED, not unknown", "REGISTRATION-IS-NOT-A-DRAW", _ACK)
    chk("(1) no ack -> refused, and the reason names the ack", (ok, missing), (True, []))
    print("   (1) no ack                    REFUSED, and the reason names `%s`" % _ACK)

    # (2) THE ACK ALONE -- a judgement with nothing to check it against.
    ok, missing, first = refuses(_spec(good, ef_ok, {"name": cell, _ACK: True}),
                                 "states NO `expect_bpp`", _ACK, "REGISTRATION-IS-NOT-A-DRAW")
    chk("(2) ack without expect_bpp -> FAILS BY NAME", (ok, missing), (True, []))
    print("   (2) ack, no expect_bpp        FAILS BY NAME: %r" % first)

    # (3) A MISMATCHING expect_bpp.
    ok, missing, first = refuses(
        _spec(good, ef_ok, {"name": cell, _ACK: True, "expect_bpp": 8}),
        "the spec guards 8bpp", "CHANNEL P", "registration is not a draw")
    chk("(3) mismatching expect_bpp -> FAILS BY NAME", (ok, missing), (True, []))
    print("   (3) ack + WRONG expect_bpp    FAILS BY NAME: %r" % first)

    # (4) THE LITERAL-BOOLEAN LAW (W5's, re-stated at this call site): a truthy string must REFUSE.
    ok, missing, first = refuses(
        _spec(good, ef_ok, {"name": cell, _ACK: "true", "expect_bpp": bpp}),
        "must be a BOOLEAN", "never inferred from a truthy string")
    chk("(4) a string 'true' -> REFUSES", (ok, missing), (True, []))
    print("   (4) ack = \"true\" (a string)    REFUSES on the literal-boolean law")

    # (5) THE HAZARD OUTRANKS THE ACK.
    ok, missing, first = refuses(
        _spec(bad, ef_dual, {"name": cell, _ACK: True, "expect_bpp": 8}),
        "PROGRAM-DUAL-DEPTH", "UNANIMITY IS THE VERDICT RULE", "no acknowledgement lifts it")
    chk("(5) ack on a PROGRAM-DUAL cell -> still refuses", (ok, missing), (True, []))
    print("   (5) ack on a DUAL-depth cell  STILL REFUSES -- the hazard outranks the ack")

    # (6) THE PAIR.  Ack + a MATCHING expect_bpp resolves the page, and the page says where the depth
    #     came from -- which is what makes a channel-P cast readable back as evidence about channel P.
    b = RP.build(_spec(good, ef_ok, {"name": cell, _ACK: True, "expect_bpp": bpp}),
                 "w6b2i", blob=good)
    t = b.targets[0]
    chk("(6) the PAIR resolves the page", (t.ack_program_depth, t.page.depth_source, t.page.bpp),
        (True, "program", bpp))
    chk("(6) ...and the page records the inheritance", t.page.depth_inherited, True)
    print("   (6) ack + MATCHING expect_bpp RESOLVES, depth_source=%r bpp=%d -- the author carries "
          "the judgement, the kit carries the check" % (t.page.depth_source, t.page.bpp))
    chk("the key is in the fail-closed table", _ACK in RP._TEXEL_KEYS, True)

    # (7) ★ THE MAJORITY RUNG, on an INDEXED vehicle -- the 134 cells rungs (1)-(6) cannot reach.
    #     The correct ack AND the correct `expect_bpp` are both in hand and the cell STILL refuses,
    #     because what is missing is a KEY and neither key-word supplies one.  It refuses in its OWN
    #     class: `no-declared-clut` is written about "the reader's `so` record" and there is no reader.
    ok, missing, first = refuses(
        _spec(BLOBS[ef_idx], ef_idx, {"name": cell, _ACK: True, "expect_bpp": idx_bpp}),
        "CHANNEL P STATES A DEPTH AND NOTHING ELSE", "no key to index into",
        "134 of channel P's 189 cells are indexed")
    chk("(7) ack + MATCHING expect_bpp on an INDEXED cell -> STILL REFUSES, by its own name",
        (ok, missing), (True, []))
    chk("(7) ...and the refusal does not quote a reader that does not exist",
        "the reader's `so` record" in first, False)
    chk("(7) ...and the cell is REFUSED, not merely un-emitted",
        "program-depth-no-palette" in D.ack_refusals[(ef_idx, 448, 256)], True)
    print("   (7) ack + RIGHT expect_bpp,   INDEXED cell: STILL REFUSES -- `program-depth-no-palette`."
          "  %r" % first)
    print("       the ack admits a DEPTH; what is missing here is a KEY, and 134 of the 189 are in "
          "this shape.  A ladder run only on 15bpp cannot see the majority of its own channel.")


# --------------------------------------------------------------------------- I8
def i8_census_restamp(D: Data) -> None:
    """sec 7 ROW 9 -- **a PARALLEL lane's deliverable, verified here rather than assumed.**

    The census's `addressable_via` field asserted "UNADDRESSABLE (lower half of an h=256 rect)" for
    cells the shipped per-cell map names, which is how the 79-vs-199 dispute regenerates: two
    instruments read the same cells and one of them believed a stale flag.  This gate reads
    `pages.json` and asserts ZERO map-named cells still carry it -- and, because the re-stamp is
    landing from another session while this runs, it RE-CHECKS ONCE after a short wait before failing.
    **Then it fails honestly**: a stale field reported as clean is exactly the failure this row exists
    to end.
    """
    print("[I8] ROW 9 -- the census `addressable_via` re-stamp (a parallel lane's), VERIFIED")
    path = os.path.join(W6B, "census", "pages.json")

    def stale_rows():
        recs = _load(path)
        return [r for r in recs
                if any("UNADDRESSABLE" in str(v) for v in (r.get("addressable_via") or []))]

    stale = stale_rows()
    if stale:
        print("   %d row(s) still carry the stale flag -- the re-stamp may be mid-flight in another "
              "session; RE-CHECKING ONCE in 20s rather than failing on a race." % len(stale))
        time.sleep(20)
        stale = stale_rows()
    chk("census rows still asserting UNADDRESSABLE", len(stale), PIN["stale_addressable_rows"])
    if stale:
        print("   !! STILL STALE after the re-check: %s" % ", ".join(r["id"] for r in stale[:8]))

    # ...and the POSITIVE half: what it was re-stamped TO must be a key the shipped map really names.
    lower = [k for k, r in D.C.items()
             if "creature" not in r["classes"] and r["hz_depth_unknown"]
             and DA.program_depth(k[0], (k[1], k[2])) is not None
             and DA.program_depth(k[0], (k[1], k[2])).bpp is not None and k[2] % PAGE_LINES]
    chk("program-gained LOWER HALVES", len(lower), PIN["prog_lower_halves"])
    named = id9 = 0
    bad = []
    for k in sorted(lower):
        via = " ".join(str(v) for v in (D.C[k].get("addressable_via") or [])).replace(" ", "")
        if "page_cells" in via and ("%d,%d" % (k[1], k[2])) in via:
            named += 1
        elif "id9_pages" in via:
            # ⚠ TWO LAWFUL ROUTES, AND ONLY ONE OF THEM IS THE PER-CELL MAP.  An id-9 alternate block
            # is ONE WHOLE 0x4000 upload that happens to sit at y = 384; it is not the lower half of
            # any rect, so its own writer record is addressable through the id-9 rect key and always
            # was.  Counting those as "not re-stamped" would manufacture a defect out of a cell that
            # never had the problem row 9 exists to fix.
            id9 += 1
        else:
            bad.append((D.C[k]["id"], via))
    chk("...stamped through the PER-CELL map at their own (x, y)", named,
        PIN["prog_lower_halves_via_map"])
    chk("...stamped through the id-9 rect key (never a rect's lower half in the first place)",
        id9, PIN["prog_lower_halves_via_id9"])
    chk("...and nothing else", len(bad), 0)
    chk("83 + 10 == 93", named + id9, PIN["prog_lower_halves"])
    # THE ASSUMPTION NOBODY HAD PUT TO `reskin` ITSELF: can the SHIPPED map actually NAME these cells?
    chk("the shipped `reskin.page_cells` names every one of them",
        len([k for k in lower if k in D.cells]), PIN["prog_lower_halves"])
    print("   %d rows assert UNADDRESSABLE (was: the pre-W6b-1 rect key, for cells the shipped map "
          "NAMES)" % len(stale))
    print("   TWO PREDICATES ON THE SAME CELLS, BOTH PRINTED: %d of the %d program-gained lower "
          "halves are stamped `reskin.page_cells[(tag, x, y)]` -- the census's own "
          "hz_unaddressable_lower_half subset -- and the other %d are id-9 ALTERNATE BLOCKS, one "
          "whole upload each, addressable through the id-9 rect key and never a rect's lower half."
          % (named, len(lower), id9))
    print("   ...and the assumption underneath the 79-vs-199 dispute, put to `reskin` at last: the "
          "shipped per-cell map names %d/%d of them." % (len([k for k in lower if k in D.cells]),
                                                         len(lower)))
    if bad:
        print("   !! not re-stamped: %s" % ", ".join("%s -> %s" % b for b in bad[:6]))
    # THE DOME, the one cell the whole hand-off argument turned on
    chk("THE DOME is stamped through the per-cell map",
        "page_cells" in " ".join(str(v) for v in D.C[(211, 704, 384)]["addressable_via"]), True)


# --------------------------------------------------------------------------- I9
def i9_residue(D: Data) -> None:
    """sec 7 ROW 10 -- **2,139 cells keep refusing BY NAME, with the residue split in the reason.**

    The split is what stops the number reading like a shortfall: **1,278** of them sit in the 222
    containers that declare no model at all, so their programs register nothing and never could --
    a STRUCTURAL ceiling, not a scanner that gave up.  The other **861** are in model-BEARING
    containers the lever simply does not cover.  ``246 + 1,278 + 861 = 2,385`` and the closure is
    asserted, not quoted.
    """
    print("[I9] ROW 10 -- the residue, its split, and its arithmetic closure")
    chk("the scenery page-cell population", len(D.cells), PIN["scenery_cells"])
    uv, gp = len(D.by_source("so-uv")), len(D.by_source("so-page"))
    dark = len(D.refused_of("depth-unknown"))
    pdual, gdual = len(D.refused_of("program-dual-depth")), len(D.refused_of("channel-g-dual-depth"))
    chk("W6b-1's own readable count", uv, PIN["so_uv_cells"])
    chk("depth-unknown AFTER both channels", dark, PIN["depth_unknown_after"])
    chk("the walk still visits every cell exactly once", uv + gp + dark + pdual + gdual, len(D.cells))
    chk("W6b-1's 2,385, split by the two channels", dark + gp + pdual + gdual,
        PIN["depth_unknown_before"])
    print("   %d cells = %d so-uv + %d so-page + %d depth-unknown + %d program-dual + %d "
          "channel-G-dual  (the closure, not any single count, is what proves nothing fell out)"
          % (len(D.cells), uv, gp, dark, pdual, gdual))

    # THE SPLIT ITSELF, re-measured: a container with ZERO non-creature GEOM blocks has no model to
    # register a texture onto, so the lever is silent there BY CONSTRUCTION.
    blind = set()
    for p in D.paths:
        ef = int(os.path.basename(p)[2:5])
        with open(p, "rb") as fh:
            if RS.attribution(fh.read(), include_direct=True).geom_total == 0:
                blind.add(ef)
    unk = [k for k, r in D.C.items() if "creature" not in r["classes"] and r["hz_depth_unknown"]]
    gained = set(D.by_source("so-page")) | {
        k for k in unk if (DA.program_depth(k[0], (k[1], k[2])) is not None
                           and DA.program_depth(k[0], (k[1], k[2])).bpp is not None)}
    bu = [k for k in unk if k[0] in blind]
    rest = [k for k in unk if k[0] not in blind and k not in gained]
    chk("W6b-1's depth-unknown population", len(unk), PIN["depth_unknown_before"])
    chk("246 gained", len(gained), PIN["gain_either"])
    chk("1,278 in the `so`-blind containers", len(bu), PIN["residue_blind"])
    chk("861 in model-BEARING containers the lever does not cover", len(rest), PIN["residue_covered"])
    chk("THE ARITHMETIC CLOSES", len(gained) + len(bu) + len(rest), len(unk))
    chk("...and the blind containers gain ZERO",
        len([k for k in bu if k in gained]), 0)
    print("   %d = %d gained + %d inside the %d containers that declare NO model + %d in "
          "model-BEARING containers the lever does not cover"
          % (len(unk), len(gained), len(bu), len(blind), len(rest)))
    print("   THE CEILING IS STRUCTURAL, NOT STATISTICAL: a container with no model has nothing to "
          "register a texture ONTO, so those %d cells gain %d.  Do not project 10.31 %% forward."
          % (len(bu), len([k for k in bu if k in gained])))

    # ...and the SPLIT IS IN THE REASON STRING, on every one of the refused cells.
    miss = [k for k in D.refused_of("depth-unknown")
            if not all(t in D.reasons[k]["depth-unknown"]
                       for t in ("THE RESIDUE, SPLIT", "2,139 keep refusing", "1,278", "861"))]
    chk("every depth-unknown reason carries the split", len(miss), 0)

    # ★ `W6B_REASON` IS RE-MEASURED, NOT SUBSTRING-MATCHED.  It is author-facing -- `texel_page`
    # appends it to every unresolved name, and three build gates quote it -- and the previous pin
    # (`"2,139 cells" in W6B_REASON`) PROTECTED a number rather than CHECKING it: the string named the
    # record's ATTRIBUTION RESIDUE where a reader would read the class's own population, which this
    # very gate measures ten lines above as 2,298.  Both numbers are now in the string, and both are
    # checked against the derivation -- including the arithmetic BETWEEN them, since the 30 dual-depth
    # cells are a SUBSET of the residue and the flat form double-counts them.
    def _stated(pattern: str) -> int:
        m = re.search(pattern, RP.W6B_REASON)
        return int(m.group(1).replace(",", "")) if m else -1

    chk("W6B_REASON's depth-unknown population == the re-measured count",
        _stated(r"DEPTH-UNKNOWN \(([\d,]+) cells"), dark)
    chk("...and the residue it also names == the module's own pin",
        _stated(r"no depth on ANY channel is ([\d,]+)"), DA.RESIDUE)
    chk("THE ARITHMETIC BETWEEN THE TWO CLOSES: 2,298 - 189 + 30 == 2,139",
        dark - PIN["gain_program"] + pdual + gdual, DA.RESIDUE)
    chk("...and the string says the 30 are a SUBSET, never an addend",
        "SUBSET of this population, never an addend" in RP.W6B_REASON, True)
    print("   and the split is IN THE REASON STRING on all %d of them, plus in `repaint.W6B_REASON` "
          "-- which names BOTH populations: %d refuse under the class's own name and %d is the "
          "residue with no depth on any channel (%d - %d disclosed + %d dual = %d)"
          % (dark, dark, DA.RESIDUE, dark, PIN["gain_program"], pdual + gdual, DA.RESIDUE))


# --------------------------------------------------------------------------- I10
#: BENIGN BY NAME, not by silence.  Nothing in this round's committable surface is expected to match
#: corpus bytes; anything that does is printed with its file and adjudicated here or the gate is red.
#:
#: ⚠ THE SCAN'S SURFACE IS `git status`, SO IT GROWS WHEN A NEIGHBOURING ROUND EDITS A FILE.  W6b-3i
#: pulled `test_reskin.py`, `w6b2_gates.py` and four more into it, and the two literals below are the
#: ones the other three boards carrying this table (`w6b2_gates.py`, `w6b3_gates.py`,
#: `w6b3i_gates.py`) already clear BY NAME.  Both are short runs of small ints that match binary data
#: by construction, and both are the KIT's or a DECODER's own published tables -- adjudicated here so
#: this board clears them for the same stated reason instead of going red on a false alarm.
_ADJUDICATED: Dict[bytes, str] = {
    b"\x02\x03\x04\x05\x06\x07": "MIPS load/store opcode tuple in a decoder's is_transfer",
    b"\x00\x00\x01\x01\x02\x03\x04\x05": "reskin.ID9_SLOT_BIT, the kit's own slot->bit table, "
                                         "asserted in test_reskin.py",
}


def _new_files() -> List[str]:
    """ASK GIT, never a hand-written list -- the provenance surface MOVES while a round is judged and
    a concurrent lane's new file must not be silently unscanned.  (The same method `w6b2_gates.py` H8
    uses; run here too so this file does not depend on another one being run.)"""
    import subprocess
    try:
        out = subprocess.run(["git", "-C", _REPO, "status", "--porcelain"],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return []
    names = []
    for line in out.splitlines():
        rel = line[3:].strip().strip('"')
        p = os.path.join(_REPO, rel.replace("/", os.sep))
        if os.path.isfile(p):
            names.append(p)
        elif os.path.isdir(p):
            for root, _d, fs in os.walk(p):
                names.extend(os.path.join(root, f) for f in fs)
    return sorted(names)


def _byte_constants(path: str) -> List[bytes]:
    out: List[bytes] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except Exception:
        return out
    if path.lower().endswith(".py"):
        try:
            tree = ast.parse(src)
        except SyntaxError:
            return out
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, bytes):
                out.append(node.value)
            elif isinstance(node, (ast.Tuple, ast.List)):
                vals = [e.value for e in node.elts
                        if isinstance(e, ast.Constant) and isinstance(e.value, int)
                        and 0 <= e.value < 256]
                if len(vals) == len(node.elts) and len(vals) >= 6:
                    out.append(bytes(vals))
    for m in re.finditer(r"(?:\\x[0-9a-fA-F]{2}){6,}", src):
        try:
            out.append(bytes.fromhex(m.group(0).replace("\\x", "")))
        except Exception:
            pass
    return out


def i10_provenance(D: Data) -> None:
    """PROVENANCE.  What this rung commits is a DERIVATION -- cell coordinates, depths, call-site
    counts, effect ids and counts -- and **never a stock byte, a hex run or a byte-sequence literal.**

    The cached channel-P table is the file that could have gone wrong: it is 221 rows of integers
    recovered from Square-Enix program images.  What is recovered is the ARGUMENT VALUE and the
    coordinates it decodes to; the decoded listings, the provenance strings and every instruction the
    walker read stay outside the checkout, under `C:\\gd\\SCRATCH\\summon-format\\texel-w6b\\w6b2\\`.
    """
    print("[I10] PROVENANCE -- a derivation, never a stock byte")
    blobs = []
    for p in D.paths:
        with open(p, "rb") as fh:
            blobs.append(fh.read())
    files = [p for p in _new_files()
             if os.path.splitext(p)[1].lower() in (".py", ".md", ".toml")]
    stockish = [p for p in _new_files()
                if os.path.splitext(p)[1].lower() in (".bytes", ".png", ".tga", ".bmp", ".dds")]
    chk("no stock-shaped asset added to the checkout", len(stockish), 0)
    found = leaks = 0
    for p in files:
        for lit in _byte_constants(p):
            if len(lit) < 6 or len(set(lit)) < 2:
                continue
            found += 1
            hits = sum(1 for b in blobs if lit in b)
            if hits and lit not in _ADJUDICATED:
                leaks += 1
                print("      !! byte literal %r in %s appears in %d corpus containers"
                      % (lit, os.path.basename(p), hits))
    chk("unadjudicated byte literals matching corpus data", leaks, 0)
    print("   %d new text file(s) scanned, from `git status --porcelain` rather than a list: %s"
          % (len(files), ", ".join(sorted(os.path.basename(f) for f in files))[:200]))
    print("   %d byte-constant candidate(s) of >= 6 non-uniform bytes . %d leaks . %d stock-shaped "
          "files added" % (found, leaks, len(stockish)))
    # the SHAPE of the cached table, stated: integers only, and every row carries a y >= 256 so it can
    # never be read as a byte sequence in the first place.
    ys = {v.cell[1] for v in DA.PROGRAM_DEPTH.values()}
    chk("every cached row's y is >= 256 (never a byte-shaped tuple)", min(ys) >= 256, True)
    print("   the cached channel-P table is %d rows of (effect, x, y, depth, call sites); every y is "
          ">= 256, so no row can even be mistaken for a byte sequence" % len(DA.PROGRAM_DEPTH))


# --------------------------------------------------------------------------- runner
GATES = [
    ("I0", "CALIBRATE (the shipped page view == an independent roll; the DOME re-found)", i0_calibrate),
    ("I1", "ROW 1 -- two views, 138/140 and 16/18 informative, 2 FLAGGED", i1_two_views),
    ("I2", "ROW 5 -- THE RE-DERIVATION PIN on the cached channel-P table", i2_rederivation_pin),
    ("I3", "ROWS 3+4 -- the dual-depth refusals: 22 in 10 containers + 8 unnamed", i3_dual_classes),
    ("I4", "ROW 2 -- SPILL-vs-OWN-PAGE protects EXACTLY ZERO new cells", i4_spill_class),
    ("I5", "ROW 8 -- channel G: 57 = 49 clean + 7 class-C + 1 refused; 5 populations unmoved",
     i5_channel_g),
    ("I6", "ROW 6 -- the refusal matrix names the new strings and DISCLOSES", i6_refusal_matrix),
    ("I7", "ROW 7 -- the ack ladder, every rung failing BY NAME", i7_ack_ladder),
    ("I8", "ROW 9 -- the census re-stamp landed (a parallel lane's, verified)", i8_census_restamp),
    ("I9", "ROW 10 -- 2,139 refuse by name, split and closed", i9_residue),
    ("I10", "PROVENANCE -- a derivation, never a stock byte", i10_provenance),
]


def main(argv=None) -> int:
    only = set(a.upper() for a in (argv or sys.argv[1:]) if a.upper().startswith("I"))
    print("W6b-2 INTEGRATION GATES -- the attribution rung, as SHIPPED KIT BEHAVIOUR")
    print("corpus: %s" % SCRATCH)
    print("THE LINE: CHANNEL G LICENSES.  CHANNEL P DISCLOSES, and edits only behind an ack.")
    print("=" * 72)
    D = Data()
    board = []
    for tag, title, fn in GATES:
        if only and tag not in only:
            continue
        before = len(_FAILS)
        try:
            fn(D)
            ok = len(_FAILS) == before
        except Exception as exc:                                   # a crashed gate is a red gate
            _FAILS.append("%s raised %s: %s" % (tag, type(exc).__name__, exc))
            ok = False
        board.append((tag, title, ok))
        print("   [%s] %s\n" % ("PASS" if ok else "FAIL", tag))
    print("=" * 72)
    for tag, title, ok in board:
        print("%-4s %s %s" % ("PASS" if ok else "FAIL", tag, title))
    if _FAILS:
        print("-" * 72)
        for f in _FAILS:
            print("  FAIL  %s" % f)
    print("=" * 72)
    print("%d/%d gates pass" % (sum(1 for _, _, ok in board if ok), len(board)))
    return 1 if _FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
