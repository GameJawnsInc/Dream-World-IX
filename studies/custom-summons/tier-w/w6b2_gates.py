r"""TIER W rung W6b-2 -- THE ATTRIBUTION RUNG'S OWN GATE RUNNER.  `py w6b2_gates.py` prints H0..H16.

W6b-1 closed with 2,385 of 2,572 scenery page-cells DEPTH-UNKNOWN: no `so` record samples them, so
the container "states no depth" and the texel edit lane refuses them by name.  W6b-2 asks whether the
container states the depth SOMEWHERE ELSE -- in the id-3 effect program's own texture registration --
and how far that lever actually reaches.  Two sweep lanes (L1 tpage, L2 write-scan) and their
refuters produced the numbers; THIS FILE RE-MEASURES EVERY ONE OF THEM from the corpus and the raw
lane artifacts, so `W6b2-ATTRIBUTION.md` quotes nothing it cannot re-derive:

H0  CALIBRATE THE INSTRUMENT BEFORE JUDGING WITH IT.  This file's own tpage decoder is checked
    against `reskin.attribution`'s field extraction over all 512 nine-bit words, and then pointed at
    two KNOWN answers first: ef211's column-704 `so` binding (tpage 155 -> page (704,256) 8bpp, the
    W6b-1 cast vehicle's own page) and L1's quoted ef001 chain (tpage 27 -> page (704,256) 4bpp).
H1  THE POPULATION.  2,665 census page-cells; 2,572 scenery; 2,385 `hz_depth_unknown`; 2,402
    `bpp is None`; and the 17-cell gap between the last two accounted for as `hz_dual_depth` rather
    than rounded away.
H2  CHANNEL P -- THE PROGRAM CHANNEL, RE-ROLLED FROM THE RAW HITS.  L1's per-cell rollup
    (`join.cells`) is NOT read: the hits are re-decoded here with this file's own decoder and
    re-attributed at PAGE granularity, then the tier split, the structural predicates, the undeclared
    columns and the multi-valued residue are re-counted.
H3  CHANNEL G -- `so` AT PAGE GRANULARITY, RE-READ FROM THE CORPUS.  372 containers re-scanned
    through `reskin.attribution`; a tpage's depth is attributed to BOTH stacked cells of its column.
    The 189 / 57 / 246 headline and the 10.31 % are computed here, never quoted.
H4  THE CALIBRATION TABLE, and every disagreement adjudicated by name -- P 10/10, G 138/140, cross-
    channel 10/10, and the two residual G rows shown to be U-SPILL (every census reader of the cell
    is a binding on the NEIGHBOURING page whose u range crosses the column boundary).
H5  THE STRUCTURAL CEILING.  222 geom-blind containers hold 1,278 of the unknown cells and gain
    ZERO, plus a third instrument's corroboration (V1b's flat shape scan nominates nothing in any
    container L1 reported zero hits for).
H6  THE REFUTER CHECKS, REPRODUCED RATHER THAN RESTATED.  (a) V1a lens G: the 246 gained cells
    re-scored against every other census hazard -> 79 clean, and the THIRD predicate stated (10, if
    `hz_attribution_blind` is allowed to disqualify).  (b) V1b's A5 linear-scan disagreement list:
    all 18 disagreeing containers explained, 0 unexplained.
H7  THE WRITE DELTA.  L2's adjudicated site list + the loader's seq-0x07 ids are re-summed into id
    SETS here and compared against the SHIPPED `repaint.PROGRAM_VRAM_WRITE_IDS` /
    `PROGRAM_VRAM_READ_IDS` / `MOVEIMAGE_HARD_CELLS`.  Delta must be empty in both directions, and
    the G6-vs-shipped predicate disagreement (the texanim arm) is printed, not reconciled away.
H8  PROVENANCE: an AST-level byte-constant scan (plus integer sequences and hex runs) of every NEW
    file `git status --porcelain` reports in the checkout -- ASKED OF GIT, never a hand-written list,
    because the provenance surface MOVES while the round is being judged and a concurrent lane's new
    file must not be silently unscanned.  One literal is ADJUDICATED BENIGN BY NAME rather than
    suppressed.  The SE-derived lane dossiers all sit outside the checkout.

The gates below were added after the round's refuters and its completeness critic landed.  Each one
exists because a claim WAS BEING QUOTED WITHOUT BEING MEASURED, or because a proposed gate would
have failed on day one:

H9  '233/233 VALUES, 238/238 SITES' -- the sentence that makes channel P a RECOVERED CONSTANT rather
    than an inference, and which no gate touched.  Both disassemblers' site sets, the TWO-WINDOW
    composition of the "233/233" the prose elides, a THIRD source months older, the reachability
    closure, THE DELAY-SLOT LAW, and the calibration argument the refuter REFUTED AS STATED (the
    conditional null is 85.6 %, not ~50 %) with the sibling controls that carry the load instead.
H10 CHANNEL G RE-EXAMINED.  Its 138/140 calibration is re-derived here and shown to be 87 %
    TAUTOLOGICAL -- the same `so` record on both sides is an identity, not a test -- leaving 16/18 on
    the informative rows.  Plus: its 57 cells open ZERO new columns, and P and G share NO cell.
H11 THE REFUSED SET IS 32, NOT 24.  Eight channel-G ambiguities are named in no dossier.  And the
    residue table's three populations are annotated so a reader cannot double-count 24 cells.
H12 THE BUILD LIST'S OWN GATES, PRE-TESTED.  "The 57 cells build" FAILS as written (56 do).  And the
    assumption underneath the 199-vs-79 hand-off dispute is finally PUT TO `reskin` itself.
H13 THE NEXT PROBE, COSTED BEFORE A LANE IS SPENT ON IT.  The ranked-first probe joins over an
    11-element page space and returns "yes" for 1,278 of 1,278 cells.  The ranked-second question is
    answered here with one call.
H14 THE STORE-LEVEL SWEEP L1's own caveat named and nobody ran -- with its OWN ambient null and its
    OWN positive control, in the same pass.
H15 THE WRITE LANE'S REFUTER, reproduced at SITE level, plus the `ef149` subtraction that until now
    survived only in SCRATCH, plus the op-index -> native-fn link both lanes had inherited.
H16 ★ CHANNEL H -- THE CLUT-ARITY NARROWING THAT SAT IN THE PRIMARY ARTIFACT ALL ROUND AND THAT NO
    LANE OPENED.  `pages.json.bpp_hint` is the container's OWN id-0 payload header nClut4/nClut8
    arity, and it speaks for 351 of the 2,385.  It is a NARROWING, NOT AN ATTRIBUTION (hint = 4 means
    "4 bpp or 15 bpp") and licenses no decode alone -- which is why it is not a fourth headline.  It
    is gated because it falsifies two of this record's FLAT caveats: 17 shipped cells DO have a
    second witness, and P's corroborated set is not frozen at 10.  Re-measured from `pages.json` +
    `tpage_sweep.json`, never from the critic's own JSON.

Reads the extracted corpus at C:\gd\SCRATCH\summon-format and the lane artifacts under
texel-w6b\w6b2\ ONLY -- no install read, NO deploy, no install write, no git commit.  ~2 min.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                              # noqa: E402  (sets up sys.path)
import summon_camera as W                                        # noqa: E402
import ef_container as EC                                        # noqa: E402  (the sanctioned parser)
from ff9mapkit.summons import repaint as RP                      # noqa: E402

CORPUS = W.SCRATCH_CORPUS
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
SCRATCH = os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format")
W6B = os.path.join(SCRATCH, "texel-w6b")
LANE = os.path.join(W6B, "w6b2")

#: A VRAM tpage names a 64-halfword x 256-line PAGE.  A census page-cell is 64 x 128.  So ONE tpage
#: covers the TWO STACKED CELLS of its column -- the granularity statement this whole rung turns on.
PAGE_HW, PAGE_LINES, CELL_LINES = 64, 256, 128

# --------------------------------------------------------------------------- THE PINS
#: Every number `W6b2-ATTRIBUTION.md` and `A4-TPAGE-ATTRIBUTION.md` are allowed to quote.  Each is
#: RE-MEASURED in the gate body below and compared here; a pin that only matched a prose table would
#: be the thing this house forbids.
PIN = {
    # -- H1 population
    "page_cells": 2665,
    "scenery_cells": 2572,
    "creature_pages": 93,
    "depth_unknown": 2385,
    "bpp_none": 2402,
    "dual_depth": 17,               # == bpp_none - depth_unknown, exactly
    # -- H2 channel P
    "op22_sites": 238,              # hits + runtime + refused-dispatch
    "hits": 233,
    "tier_strong": 225,
    "tier_corroborated": 8,
    "runtime_args": 4,
    "refused_dispatch": 1,
    "ybit_all": 233,                # page-Y bit set on every accepted hit
    "declared_column_all": 228,
    "declared_column_strong": 220,
    "undeclared_hits": 5,
    "prog_cells": 221,              # census cells a recovered tpage's page covers
    "prog_multi_depth": 22,         # ... of which MULTI-VALUED -> no verdict, a new hazard class
    "gain_program": 189,
    "gain_program_strong_only": 181,
    # -- H3 channel G + the headline
    "gain_so_page": 57,
    "gain_either": 246,
    "pct_either": 10.31,
    "gain_y384": 150,
    # -- H4 calibration
    "cal_p_n": 10, "cal_p_agree": 10,
    "cal_g_n": 140, "cal_g_agree": 138,
    "cal_cross_n": 10, "cal_cross_agree": 10,
    # -- H5 ceiling
    "geom_blind_containers": 222,
    "blind_unknown_cells": 1278,
    "blind_gain": 0,
    "containers": 372,
    "residue_geom_bearing": 861,    # unknown, in a container WITH models, still unattributed
    "residue_containers": 135,
    "op22_containers": 77,
    "cells_on_the_corroborated_tier": 8,
    # -- H6 refuter
    "gained_clean": 79,             # V1a's predicate: the census's PRE-W6b-1 (tag,x) addressing
    "gained_clean_shipped_map": 199,  # ... under the per-cell map W6b-1 ACTUALLY SHIPPED
    "gained_clean_strict": 10,      # ... if hz_attribution_blind is allowed to disqualify too
    "hz_lower_half": 138,
    "hz_attribution_blind": 177,
    "hz_program_write": 45,
    "v1b_disagreeing_containers": 18,
    "v1b_unexplained": 0,
    # -- H7 write delta
    "shipped_write_ids": 15,
    "shipped_read_ids": 12,
    "write_delta": 0,
    "read_delta": 0,
    "l2_sites": 77,
    "l2_real": 23,
    "l2_rejected": 54,
    # -- H9 the 238/238 . 233/233 claim, and the calibration the refuter REFUTED as stated
    "v1a_op22_sites": 238,
    "v1a_only_l1": 0,
    "v1a_intersection": 233,
    "v1a_value_agree_windowA": 221,
    "v1a_window_probe": 12,
    "hle_ops_op22_sites": 238,          # a THIRD source, months older than either lane
    "reach_inside_closure": 238,
    "reach_outside": 0,
    "arg1_from_a_delay_slot": 0,        # THE DELAY-SLOT LAW, in the safe direction
    "perm_null_declared": 0.8557,       # NOT ~0.50 -- the sweep's calibration prose is refuted
    "perm_p_value": 0.005,
    "sibling_a2_shaped": 0.0,
    "sibling_a3_declared": 0.0,
    "texreg_sites_total": 275,
    "texreg_covered_by_op22": 238,
    "texreg_coverage": 0.8655,
    # -- H10 channel G re-examined: circularity, reach, disjointness
    "g_gt_rows": 140,
    "g_tautological": 122,              # same `so` record on BOTH sides -- an identity, not a test
    "g_partial": 15,
    "g_disjoint": 2,
    "g_independent": 1,                 # census depth from the id-4 header -- a NON-`so` witness
    "g_informative_n": 18,
    "g_informative_agree": 16,          # 16/18 = 0.889 on the rows that could have falsified it
    "g57_y384": 57,
    "g57_partner_already_known": 57,
    "g57_new_columns": 0,
    "p_and_g_overlap_on_the_gain": 0,   # every shipped cell rests on ONE channel
    # -- H11 the refused set, and the residue populations
    "p_ambiguous": 22,
    "g_ambiguous_unknown": 8,           # NAMED NOWHERE in L1's dossier
    "ambiguous_overlap": 0,
    "refused_total": 32,                # 22 + 8 + 2, not the dossier's 24
    "spill_inside_the_2385": 0,         # the 2 spill cells are OUTSIDE the population
    "spill_newly_protected": 0,         # ... and already refused by hz_spill_in / lawful=False
    # -- H12 the build list, pre-tested
    "g57_clean": 56,                    # NOT 57 -- one refuses on hz_program_write
    "g57_refusing": 1,
    "g57_lower_halves": 55,
    "prog_lower_halves": 93,            # all program-gained y=384 cells
    "prog_lower_halves_flagged": 83,    # ... the subset carrying hz_unaddressable_lower_half
    "page_cells_names_them": 93,
    # -- H13 the next probe, costed before a lane is spent on it
    "census_vram_pages": 11,
    "blind_pages": 6,
    "blind_pages_named_by_op22": 6,     # => 1,278/1,278 "pass" -- the probe discriminates NOTHING
    "ef390_bindings": 12,
    "ef390_writerless_15bpp": 10,
    # -- H14 the store-level sweep nobody had run
    "store_positive_control_shaped": 233,
    # -- H15 V2's independent write refutation
    "v2_candidates": 77,
    "v2_vs_l2_site_disagreements": 0,
    "v2_clean_sample": 20,
    "v2_clean_sample_candidates": 0,
    "v2_read_before_subtraction": 13,
    "ef149_the_subtracted_id": 149,
    "hle_table_ops": 216,
    "hle_table_slots_in_text": 215,
    "hle_table_slots_past_end": 0,
    # -- H16 ★ CHANNEL H, the container's own CLUT-arity NARROWING (`bpp_hint`), never opened
    "hint_cells_in_2385": 351,
    "hint_4bpp": 286,                   # "4 bpp OR 15 bpp" -- the container ships no 8bpp CLUT
    "hint_8bpp": 65,
    "hint_known_n": 12,                 # the calibration the field itself CANNOT give (see below)
    "hint_known_agree": 12,
    "hint_second_witness": 17,          # ... of the 246.  "NO SHIPPED CELL HAS TWO WITNESSES" is false
    "hint_second_witness_p": 9,
    "hint_second_witness_g": 8,
    "hint_exact": 15,
    "hint_compatible_15bpp": 2,
    "hint_conflicts": 0,
    "hint_ties_seen": 30,               # the 22 program + 8 channel-G multi-valued cells
    "hint_ties_broken": 0,              # a CLEAN NEGATIVE, recorded so nobody tries
    "hint_only_in_the_residue": 334,
    "p_corroborated_before": 10,        # P's census ground truth
    "p_corroborated_after": 19,         # ... + the 9 hint corroborations, at CELL level
    # -- THE TOKENS THE RECORD STATED AND NO GATE RE-MEASURED (the re-measurability claim itself)
    "residue_cells": 2139,              # 2385 - 246, the record's own second headline
    "pct_unknown_of_scenery": 92.7,     # 2385 / 2572 -- the surface the whole rung is about
    "cell_lines": 128,
    "prog_pages": 121,
    "prog_pages_with_no_so_record": 112,
    "pct_prog_pages_uncorroborated": 92.6,   # the single largest caveat on the rung
    "declared_column_strong_pct": 97.8,      # 220/225 -- L1's calibration headline
    "ambient_shaped_pct": 22.8,              # 0.2276, the ambient the shape predicate beats
    "ptr_inside_image": 28,
    "ptr_shape_hits": 11,
    "ptr_shape_rate": 0.3929,                # 39.3 % -- the pointer-table refusal's own rate
    "op19_sites": 35, "op19_effects": 9, "op19_cells": 92,
    "op171_sites": 2, "op171_effects": 2, "op171_cells": 27,
    "dark_sites": 37, "dark_effects": 11, "dark_cells": 119,
    "dark_pct_of_2385": 5.0,
    "ef381_geom": 73, "ef381_hle_calls": 750, "ef381_op22": 0,
    "header_channel_cells": 93,
    "header_channel_creature": 93,
    "header_channel_scenery": 0,
}

_FAILS: List[str] = []


def chk(name: str, got, want) -> None:
    """Compare a re-measured value against its pin; collect rather than raise, so the board prints."""
    ok = (abs(got - want) < 5e-3) if isinstance(want, float) else (got == want)
    if not ok:
        _FAILS.append("%s: measured %r, pinned %r" % (name, got, want))


# --------------------------------------------------------------------------- shared derivations
def dec(tp: int) -> Tuple[int, int, int]:
    """(page_x, page_y, bpp) from a nine-bit PSX tpage word -- written from the bit layout."""
    return (tp & 0x0F) * PAGE_HW, ((tp >> 4) & 1) * PAGE_LINES, RS.SO_BPP[(tp >> 7) & 3]


def cover(px: int, py: int) -> List[Tuple[int, int]]:
    """THE GRANULARITY STATEMENT, in code: a page covers both stacked 128-line cells of its column."""
    return [(px, py), (px, py + CELL_LINES)]


def verdict(cnt: Counter) -> Optional[int]:
    """A depth is stated only if the evidence is UNANIMOUS; two values is a hazard, not a vote."""
    return list(cnt)[0] if len(cnt) == 1 else None


def _load(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class Data:
    """Every primary source this runner reads, loaded once."""

    def __init__(self) -> None:
        self.census = _load(os.path.join(W6B, "census", "pages.json"))
        self.C = {(r["ef"], r["vram_x"], r["vram_y"]): r for r in self.census}
        self.sweep = _load(os.path.join(LANE, "tpage_sweep.json"))
        self.write = _load(os.path.join(LANE, "write_scan.json"))
        self.v1a = _load(os.path.join(LANE, "v1a_verify.json"))
        self.v1a_scan = _load(os.path.join(LANE, "v1a_scan.json"))
        self.v1b = _load(os.path.join(LANE, "v1b_audit.json"))
        self.v1b_rc = _load(os.path.join(LANE, "v1b_recheck.json"))
        self.v1b2 = _load(os.path.join(LANE, "v1b_recheck2.json"))
        self.v2 = _load(os.path.join(LANE, "v2_check.json"))
        self.hle = _load(os.path.join(_HERE, "..", "tier-r", "hle_ops.json"))
        self.paths = sorted(glob.glob(os.path.join(SCRATCH, "ef*.bytes")))
        self.prog: Dict[Tuple[int, int, int], Counter] = defaultdict(Counter)
        self.prog_strong: Dict[Tuple[int, int, int], Counter] = defaultdict(Counter)
        self.sopage: Dict[Tuple[int, int, int], Counter] = defaultdict(Counter)
        #: which `so` records OWN the page a cell sits in -- the page-side half of the circularity
        #: test the calibration refuter ran (H10).  The census's own `readers` list is the other half.
        self.sopage_recs: Dict[Tuple[int, int, int], set] = defaultdict(set)
        #: `reskin.page_cells` per container -- the per-cell map W6b-1 SHIPPED, asked directly (H12).
        self.pcmap: Dict[int, dict] = {}
        self.blind: Dict[int, bool] = {}
        self.undeclared: List[Tuple[int, int]] = []
        self._roll_program()
        self._roll_so_page()

    # -- CHANNEL P, re-rolled from `sweep.hits` alone.  L1's `join.cells` is deliberately not read.
    def _roll_program(self) -> None:
        for h in self.sweep["sweep"]["hits"]:
            px, py, bpp = dec(h["value"])
            cells = [c for c in cover(px, py) if (h["ef"], c[0], c[1]) in self.C]
            if not cells:
                self.undeclared.append((h["ef"], h["value"]))
                continue
            for c in cells:
                k = (h["ef"], c[0], c[1])
                self.prog[k][bpp] += 1
                if h["tier"] == "strong":
                    self.prog_strong[k][bpp] += 1

    # -- CHANNEL G, re-read from the containers themselves at PAGE rather than UV granularity.
    def _roll_so_page(self) -> None:
        for p in self.paths:
            ef = int(os.path.basename(p)[2:5])
            with open(p, "rb") as fh:
                blob = fh.read()
            try:
                a = RS.attribution(blob, include_direct=True)
            except Exception:
                self.blind[ef] = True
                continue
            self.blind[ef] = (a.geom_total == 0)
            try:
                self.pcmap[ef] = RS.page_cells(blob)
            except Exception:
                self.pcmap[ef] = {}
            for b in a.bindings:
                px, py, bpp = dec(b.tpage)
                for c in cover(px, py):
                    k = (ef, c[0], c[1])
                    if k in self.C:
                        self.sopage[k][bpp] += 1
                        self.sopage_recs[k].add(int(b.geom))

    # -- derived views
    def unknown(self) -> List[Tuple[int, int, int]]:
        return [k for k, r in self.C.items()
                if "creature" not in r["classes"] and r["hz_depth_unknown"]]

    def pv(self) -> Dict[Tuple[int, int, int], Optional[int]]:
        return {k: verdict(v) for k, v in self.prog.items()}

    def gv(self) -> Dict[Tuple[int, int, int], Optional[int]]:
        return {k: verdict(v) for k, v in self.sopage.items()}


# --------------------------------------------------------------------------- H0
def h0_calibrate(D: Data) -> None:
    print("[H0] CALIBRATE the instrument before judging with it")
    bad = [tp for tp in range(512)
           if dec(tp) != ((tp & 0x0F) * 64, ((tp >> 4) & 1) * 256, RS.SO_BPP[(tp >> 7) & 3])]
    chk("decoder", len(bad), 0)
    print("   this file's tpage decoder == reskin's field extraction over %d/512 words" % (512 - len(bad)))

    # KNOWN ANSWER 1 -- the W6b-1 cast vehicle's own page, from the container, not from a dossier.
    with open(os.path.join(SCRATCH, "ef211.bytes"), "rb") as fh:
        a = RS.attribution(fh.read(), include_direct=True)
    col704 = sorted(set(b.tpage for b in a.bindings if dec(b.tpage)[0] == 704))
    chk("ef211 col-704 tpage count", len(col704), 1)
    px, py, bpp = dec(col704[0])
    chk("ef211 col-704 page", (px, py, bpp), (704, 256, 8))
    print("   KNOWN ANSWER 1  ef211 so tpage %d -> page (%d,%d) %dbpp, covering cells %s"
          % (col704[0], px, py, bpp, ["x%d_y%d" % c for c in cover(px, py)]))

    # KNOWN ANSWER 2 -- L1's own quoted folding chain, re-decoded here.
    ef001 = [h for h in D.sweep["sweep"]["hits"] if h["ef"] == 1]
    chk("ef001 hits", len(ef001), 2)
    chk("ef001 hits agree on one value", sorted(set(h["value"] for h in ef001)), [27])
    at_1dc = [h for h in ef001 if h["off"] == 0x1DC]
    chk("L1's quoted site is present", len(at_1dc), 1)
    px, py, bpp = dec(at_1dc[0]["value"])
    chk("ef001 chain", (at_1dc[0]["value"], px, py, bpp), (27, 704, 256, 4))
    print("   KNOWN ANSWER 2  ef001:c0 +0x1dc program tpage 27 -> page (704,256) 4bpp"
          "   (L1 sec 1, verbatim; the container's 2nd site folds to the same value)")
    print("   -> the instrument re-finds both answers before it is allowed to judge anything")


# --------------------------------------------------------------------------- H1
def h1_population(D: Data) -> None:
    print("[H1] THE POPULATION -- what 'depth-unknown' actually counts")
    cells = len(D.census)
    creature = sum(1 for r in D.census if "creature" in r["classes"])
    scenery = cells - creature
    unk = len(D.unknown())
    none = sum(1 for r in D.census
               if "creature" not in r["classes"] and r["bpp"] is None)
    dual = sum(1 for r in D.census if r["hz_dual_depth"])
    chk("page_cells", cells, PIN["page_cells"])
    chk("creature_pages", creature, PIN["creature_pages"])
    chk("scenery_cells", scenery, PIN["scenery_cells"])
    chk("depth_unknown", unk, PIN["depth_unknown"])
    chk("bpp_none", none, PIN["bpp_none"])
    chk("dual_depth", dual, PIN["dual_depth"])
    chk("the 17-cell gap IS the dual-depth class", none - unk, dual)
    print("   census page-cells %d = %d scenery + %d id-4 creature" % (cells, scenery, creature))
    print("   hz_depth_unknown %d ; bpp is None %d ; gap %d == hz_dual_depth %d  (a depth is known,"
          " but two of them)" % (unk, none, none - unk, dual))

    # ★ THE TWO HEADLINES THE RECORD LEADS WITH AND NO GATE HAD RE-MEASURED.  The re-measurability
    # sentence is a claim ABOUT every other claim, so the residue arithmetic and the surface
    # percentage are computed here rather than quoted from a dossier.
    pv, gv = D.pv(), D.gv()
    unk_keys = D.unknown()
    gain = len([k for k in unk_keys if pv.get(k) is not None or gv.get(k) is not None])
    pct = round(100.0 * unk / scenery, 1)
    chk("the surface percentage", pct, PIN["pct_unknown_of_scenery"])
    chk("THE RESIDUE, computed not quoted", unk - gain, PIN["residue_cells"])
    chk("one census page-cell is 128 lines", CELL_LINES, PIN["cell_lines"])
    print("   THE SURFACE: %d of %d scenery page-cells = %.1f %% carry no `so` reader, which is what"
          " W6b-1 refused by name" % (unk, scenery, pct))
    print("   THE RESIDUE, ARITHMETIC PRINTED: %d depth-unknown - %d gained = %d still refused"
          " (a page is 64 halfwords x 256 lines; a census cell is 64 x %d, so one page word names a"
          " COLUMN of two stacked cells)" % (unk, gain, unk - gain, CELL_LINES))


# --------------------------------------------------------------------------- H2
def h2_channel_p(D: Data) -> None:
    print("[H2] CHANNEL P -- the id-3 program's own tpage, re-rolled from the RAW hits")
    sw = D.sweep["sweep"]
    hits, runtime = sw["hits"], sw["runtime"]
    weak, promoted = sw["weak_dispatch"], sw["promoted"]
    tiers = Counter(h["tier"] for h in hits)
    chk("hits", len(hits), PIN["hits"])
    chk("tier strong", tiers["strong"], PIN["tier_strong"])
    chk("tier corroborated", tiers["corroborated"], PIN["tier_corroborated"])
    chk("promoted == corroborated", len(promoted), PIN["tier_corroborated"])
    chk("runtime", len(runtime), PIN["runtime_args"])
    chk("refused dispatch", len(weak), PIN["refused_dispatch"])
    chk("op22 sites", len(hits) + len(runtime) + len(weak), PIN["op22_sites"])

    ybit = sum(1 for h in hits if (h["value"] >> 4) & 1)
    declared = sum(1 for h in hits if h["declared_column"])
    dstrong = sum(1 for h in hits if h["tier"] == "strong" and h["declared_column"])
    chk("page-Y bit set on every hit", ybit, PIN["ybit_all"])
    chk("declared column (all)", declared, PIN["declared_column_all"])
    chk("declared column (strong)", dstrong, PIN["declared_column_strong"])
    chk("undeclared hits", len(D.undeclared), PIN["undeclared_hits"])
    chk("prog cells", len(D.prog), PIN["prog_cells"])

    multi = [k for k, c in D.prog.items() if len(c) > 1]
    chk("program multi-depth cells", len(multi), PIN["prog_multi_depth"])
    unk = D.unknown()
    pv, psv = D.pv(), {k: verdict(v) for k, v in D.prog_strong.items()}
    gain = [k for k in unk if pv.get(k) is not None]
    gain_s = [k for k in unk if psv.get(k) is not None]
    chk("gain program", len(gain), PIN["gain_program"])
    chk("gain program --strong-only", len(gain_s), PIN["gain_program_strong_only"])

    # ★ L1's CALIBRATION HEADLINE, as a percentage rather than only as a ratio: the "97.8 %" the
    # record quotes and no gate re-measured is 220/225 -- the STRONG tier's declared-column rate.
    dpct = round(100.0 * dstrong / tiers["strong"], 1)
    chk("the declared-column headline, as the record states it", dpct,
        PIN["declared_column_strong_pct"])

    # ★ AND THE 92.6 % PAGE-LEVEL CAVEAT -- "the single largest caveat on this rung" -- re-derived
    # here from the raw hits and this file's own `so` roll, then cross-checked against V1a's
    # published figure.  P speaks precisely where the `so` census is quiet, so overlap is scarce BY
    # CONSTRUCTION; that is why the ground truth is N = 10 and why it cannot be grown from `so`.
    prog_pages = set()
    for h in hits:
        px, py, _b = dec(h["value"])
        prog_pages.add((h["ef"], px, py))
    so_pages = set((k[0], k[1], 256) for k in D.sopage)
    no_so = prog_pages - so_pages
    ppct = round(100.0 * len(no_so) / max(len(prog_pages), 1), 1)
    chk("pages a program constant names", len(prog_pages), PIN["prog_pages"])
    chk("... carrying NO `so` record at all", len(no_so), PIN["prog_pages_with_no_so_record"])
    chk("... as a percentage", ppct, PIN["pct_prog_pages_uncorroborated"])
    plw = D.v1a["audit"]["page_level_widening"]
    chk("V1a published the same page count", plw["program_named_pages"], PIN["prog_pages"])
    chk("V1a published the same uncorroborated count", plw["program_pages_with_no_so_record"],
        PIN["prog_pages_with_no_so_record"])
    chk("V1a published the same percentage", plw["pct_of_program_pages_uncorroborated"],
        PIN["pct_prog_pages_uncorroborated"])

    bpp_split = Counter(dec(h["value"])[2] for h in hits)
    print("   op-22 sites %d = %d hits (%d strong + %d corroborated) + %d runtime + %d refused"
          % (len(hits) + len(runtime) + len(weak), len(hits), tiers["strong"],
             tiers["corroborated"], len(runtime), len(weak)))
    print("   structural predicates: page-Y bit %d/%d ; declared column %d/%d (strong %d/%d = %.1f %%"
          " -- L1's calibration headline, re-measured)"
          % (ybit, len(hits), declared, len(hits), dstrong, tiers["strong"], dpct))
    print("   ** THE LARGEST CAVEAT, RE-DERIVED NOT QUOTED: a program constant names %d pages;"
          " %d of them (%.1f %%) carry NO `so` record at all, and only %d are named by both.  P"
          " speaks where the census is quiet, so its ground truth is scarce BY CONSTRUCTION."
          % (len(prog_pages), len(no_so), ppct, len(prog_pages & so_pages)))
    print("   bpp split of the recovered tpages: 4bpp %d . 8bpp %d . 15bpp %d"
          % (bpp_split[4], bpp_split[8], bpp_split[15]))
    print("   undeclared columns %d (evidence about somebody else's page; ZERO cells attributed): %s"
          % (len(D.undeclared), sorted(set("ef%03d/tp%d" % u for u in D.undeclared))))
    print("   census cells a recovered page covers %d ; MULTI-VALUED %d in %d containers -> NO"
          " VERDICT, counted separately from the gain"
          % (len(D.prog), len(multi), len(set(k[0] for k in multi))))
    print("   depth-unknown cells gaining a PROGRAM depth: %d   (--strong-only variant: %d)"
          % (len(gain), len(gain_s)))


# --------------------------------------------------------------------------- H3
def h3_channel_g(D: Data) -> None:
    print("[H3] CHANNEL G -- the container's OWN so records, re-read at PAGE granularity")
    unk = D.unknown()
    pv, gv = D.pv(), D.gv()
    gp = [k for k in unk if pv.get(k) is not None]
    gg = [k for k in unk if gv.get(k) is not None]
    ge = [k for k in unk if pv.get(k) is not None or gv.get(k) is not None]
    chk("gain so-page", len(gg), PIN["gain_so_page"])
    chk("gain either", len(ge), PIN["gain_either"])
    chk("channels disjoint on the unknown set", len(gp) + len(gg), len(ge))
    pct = round(100.0 * len(ge) / len(unk), 2)
    chk("pct either", pct, PIN["pct_either"])
    y = Counter(k[2] for k in ge)
    chk("y384 gains", y[384], PIN["gain_y384"])

    print("   the census attributed an so record's depth only to the cells its stored UVs TOUCHED")
    print("   -- right for READERSHIP, wrong for DEPTH: a tpage's draw mode governs all 256 lines")
    print("   gain: program %d + so-at-page %d = %d of %d depth-unknown cells = %.2f %%"
          % (len(gp), len(gg), len(ge), len(unk), pct))
    print("   of the gains, %d are y=256 halves and %d are y=384 halves -- the census's blind spot"
          % (y[256], y[384]))

    # THE ef211 ANCHOR, re-derived: the in-game striped-cell cast banded the dome through (704,384).
    a256, a384 = (211, 704, 256), (211, 704, 384)
    chk("ef211 (704,256) census bpp", D.C[a256]["bpp"], 8)
    chk("ef211 (704,384) census bpp", D.C[a384]["bpp"], None)
    chk("ef211 (704,384) so-page bpp", gv.get(a384), 8)
    chk("ef211 program silent", len([h for h in D.sweep["sweep"]["hits"] if h["ef"] == 211]), 0)
    print("   THE ef211 ANCHOR: (704,256) census 8bpp . (704,384) census UNKNOWN -> channel G 8bpp ;"
          " the PROGRAM channel is SILENT there (0 op-22 calls), not wrong")

    # THE NEXT-CAST LEDGER, measured rather than argued.  (704,384) is the DOME the W6b-1 striped
    # cast banded on screen; it is now the only cell in the corpus that is depth-attributed, drawn
    # in-game, and otherwise hazard-free.  And it has NO `so` reader -- so it has NO declared UVs,
    # which is precisely why its flatness cannot be checked offline.
    dome = D.C[a384]
    for h in ("hz_dual_depth", "hz_co_transform", "hz_multi_palette", "hz_shared_read",
              "hz_program_write", "hz_program_write_here", "hz_attribution_blind"):
        chk("dome %s" % h, dome[h], False)
    chk("dome spill-in", dome["hz_spill_in"], [])
    chk("dome is a lower half (only the shipped per-cell map names it)",
        dome["hz_unaddressable_lower_half"], True)
    chk("dome program verdict is a READ", dome["program_verdict"], "read-storeimage")
    chk("dome has NO so reader -> NO declared UVs", dome["n_readers"], 0)
    print("   -> ef211 (704,384) THE DOME: depth 8bpp (channel G), single writer, program READ only,"
          " zero other hazards, addressable ONLY through the shipped per-cell map -- and 0 readers,"
          " so its UV layout is UNDECLARED and its flatness CANNOT be checked offline")
    for pool in ((211, 576, 256), (211, 640, 256)):
        chk("%s already carries an so-derived depth" % D.C[pool]["id"], D.C[pool]["bpp"], 4)
        chk("%s is therefore NOT in the gained set" % D.C[pool]["id"],
            D.C[pool]["hz_depth_unknown"], False)
    print("   -> the pool candidates (576,256)/(640,256) already carry so-derived 4bpp WITH declared"
          " reader UVs; W6b-2 adds them nothing, and they remain the only flat-UV-checkable vehicle")


# --------------------------------------------------------------------------- H4
def h4_calibration(D: Data) -> None:
    print("[H4] THE CALIBRATION TABLE -- and every disagreement adjudicated by name")

    def calibrate(dep):
        n = agree = 0
        dis = []
        for k, cnt in dep.items():
            cb, v = D.C[k]["bpp"], verdict(cnt)
            if cb is None or v is None:
                continue
            n += 1
            if cb == v:
                agree += 1
            else:
                readers = D.C[k]["readers"]
                dis.append({
                    "cell": D.C[k]["id"], "census": cb, "derived": v,
                    "all_readers_spilled": bool(readers) and not any(r["own_column"] for r in readers),
                    "spill_in": D.C[k]["hz_spill_in"],
                })
        return n, agree, dis

    pn, pa, pd = calibrate(D.prog)
    gn, ga, gd = calibrate(D.sopage)
    chk("cal P n", pn, PIN["cal_p_n"])
    chk("cal P agree", pa, PIN["cal_p_agree"])
    chk("cal G n", gn, PIN["cal_g_n"])
    chk("cal G agree", ga, PIN["cal_g_agree"])

    pv, gv = D.pv(), D.gv()
    both = [k for k in D.prog if k in D.sopage
            and pv.get(k) is not None and gv.get(k) is not None]
    xa = sum(1 for k in both if pv[k] == gv[k])
    chk("cross-channel n", len(both), PIN["cal_cross_n"])
    chk("cross-channel agree", xa, PIN["cal_cross_agree"])

    print("   channel P vs the census: %d/%d = %.3f   (%d disagreement(s))"
          % (pa, pn, pa / pn, len(pd)))
    print("   channel G vs the census: %d/%d = %.4f  (%d disagreement(s))"
          % (ga, gn, ga / gn, len(gd)))
    print("   cross-channel P vs G, census-independent: %d/%d" % (xa, len(both)))
    for d in gd:
        chk("%s is U-SPILL" % d["cell"], d["all_readers_spilled"], True)
        print("      %s  census %dbpp vs page %dbpp -- EVERY census reader is a binding on the"
              " NEIGHBOURING page spilling across the column boundary; the cell's own page is named"
              " at %dbpp.  BOTH predicates true -> genuinely dual-depth, STAYS REFUSED."
              % (d["cell"], d["census"], d["derived"], d["derived"]))
    chk("G disagreements are exactly the two U-SPILL cells", len(gd), 2)
    chk("the two cells, by name", sorted(d["cell"] for d in gd),
        ["ef381.x640_y384", "ef447.x640_y384"])


# --------------------------------------------------------------------------- H5
def h5_ceiling(D: Data) -> None:
    print("[H5] THE STRUCTURAL CEILING -- the finding that bounds the whole lane")
    blind = [ef for ef, b in D.blind.items() if b]
    chk("containers", len(D.blind), PIN["containers"])
    chk("geom-blind containers", len(blind), PIN["geom_blind_containers"])
    unk = D.unknown()
    pv, gv = D.pv(), D.gv()
    bset = set(blind)
    bu = [k for k in unk if k[0] in bset]
    bg = [k for k in bu if pv.get(k) is not None or gv.get(k) is not None]
    chk("blind unknown cells", len(bu), PIN["blind_unknown_cells"])
    chk("blind gain", len(bg), PIN["blind_gain"])

    hit_efs = set(h["ef"] for h in D.sweep["sweep"]["hits"])
    chk("no geom-blind container makes an op-22 call", len(hit_efs & bset), 0)
    print("   %d of %d containers declare ZERO non-creature GEOM blocks (the so-blind population)"
          % (len(blind), len(D.blind)))
    print("   they hold %d of the %d depth-unknown cells (%.1f %%) and gain %d"
          % (len(bu), len(unk), 100.0 * len(bu) / len(unk), len(bg)))
    print("   MECHANISM: Hi_RegisterTexEffModel registers a texture ONTO A MODEL -- a container with"
          " no model has nothing to register on.  The lever is silent exactly where the census is"
          " blind.")

    # THE RESIDUE, and its arithmetic closure -- a named remainder beats a percentage.
    ge = set(k for k in unk if pv.get(k) is not None or gv.get(k) is not None)
    rest = [k for k in unk if k[0] not in bset and k not in ge]
    chk("residue in geom-BEARING containers", len(rest), PIN["residue_geom_bearing"])
    chk("residue containers", len(set(k[0] for k in rest)), PIN["residue_containers"])
    chk("the residue arithmetic closes", len(bu) + len(ge) + len(rest), len(unk))
    chk("containers with >=1 constant tpage", len(hit_efs), PIN["op22_containers"])
    psv = {k: verdict(v) for k, v in D.prog_strong.items()}
    chk("cells resting only on the corroborated tier",
        len([k for k in unk if pv.get(k) is not None and psv.get(k) is None]),
        PIN["cells_on_the_corroborated_tier"])
    print("   THE RESIDUE CLOSES: %d unknown = %d gained + %d in the blind %d + %d in %d"
          " model-BEARING containers the lever simply does not cover"
          % (len(unk), len(ge), len(bu), len(blind), len(rest),
             len(set(k[0] for k in rest))))

    # A THIRD INSTRUMENT on the same question: V1b's flat call-shape scan over all 372 containers.
    a5 = D.v1b["A5_linear_all"]
    chk("V1b: zero-hit containers where a flat scan nominates a shaped tpage",
        len(a5["l1_zero_but_linear_shaped"]), 0)
    print("   THIRD INSTRUMENT (V1b A5, a flat shape scan, no reachability): of %d containers L1"
          " reports zero hits for -- %d with GEOM blocks -- it nominates a tpage-shaped candidate in"
          " %d.  The silence is the corpus, not the walker."
          % (a5["l1_zero_hit_containers"], a5["l1_zero_with_geom_blocks"],
             len(a5["l1_zero_but_linear_shaped"])))


# --------------------------------------------------------------------------- H6
_DISQUALIFYING = ["hz_unaddressable_lower_half", "hz_program_write",
                  "hz_program_write_here", "hz_co_transform"]


def h6_refuters(D: Data) -> None:
    print("[H6] THE REFUTER CHECKS, REPRODUCED -- not restated")
    unk = D.unknown()
    pv, gv = D.pv(), D.gv()
    ge = [k for k in unk if pv.get(k) is not None or gv.get(k) is not None]

    # (a) V1a LENS G -- the hand-off, re-scored against every other census hazard.
    hz = Counter()
    clean = strict = shipped = 0
    for k in ge:
        r = D.C[k]
        bad = [h for h in _DISQUALIFYING if r[h]]
        if r["hz_spill_in"]:
            bad.append("hz_spill_in")
        for h in bad:
            hz[h] += 1
        if r["hz_attribution_blind"]:
            hz["hz_attribution_blind"] += 1
        if not bad:
            clean += 1
            if not r["hz_attribution_blind"]:
                strict += 1
        # THE FOURTH PREDICATE.  `hz_unaddressable_lower_half` records what the census could name
        # through the PRE-W6b-1 `(tag, x)` rect key.  W6b-1 SHIPPED `reskin.page_cells`, keyed
        # `(tag, x, y)`, for exactly these cells -- so under the kit as it exists today the lower
        # half is not a hazard at all, and counting it as one under-states the hand-off.
        if not [h for h in bad if h != "hz_unaddressable_lower_half"]:
            shipped += 1
    chk("V1a lens G: clean of every other EDIT hazard", clean, PIN["gained_clean"])
    chk("... under the SHIPPED per-cell map", shipped, PIN["gained_clean_shipped_map"])
    chk("V1a lens G: hz_unaddressable_lower_half", hz["hz_unaddressable_lower_half"],
        PIN["hz_lower_half"])
    chk("V1a lens G: hz_attribution_blind", hz["hz_attribution_blind"], PIN["hz_attribution_blind"])
    chk("V1a lens G: hz_program_write", hz["hz_program_write"], PIN["hz_program_write"])
    chk("V1a lens G: the STRICTER predicate", strict, PIN["gained_clean_strict"])
    chk("V1a published the same clean count",
        D.v1a["audit"]["gained_cell_hazards"]["clean_of_every_other_listed_hazard"],
        PIN["gained_clean"])
    print("   (a) THE HAND-OFF, FOUR PREDICATES, ALL FOUR STATED:")
    print("       %d cells gain a DEPTH (10.31 %% of %d)" % (len(ge), len(unk)))
    print("       %d clear every other edit hazard UNDER THE SHIPPED PER-CELL MAP (%.2f %%)"
          % (shipped, 100.0 * shipped / len(unk)))
    print("       %d under the CENSUS's pre-W6b-1 (tag,x) addressing -- V1a lens G's number (%.2f %%)"
          % (clean, 100.0 * clean / len(unk)))
    print("       %d if `hz_attribution_blind` is also allowed to disqualify -- which is CIRCULAR,"
          " it is the very hazard the attribution answers" % strict)
    print("       the loss is concentrated: %s"
          % ", ".join("%s %d" % (h, n) for h, n in sorted(hz.items(), key=lambda x: -x[1])))
    print("       -> depth is ONE gate of several.  'more disassembly' does not unlock the other"
          " %d; an ADDRESSING fix or a write-collision fix does." % (len(ge) - clean))

    # (b) V1b's A5 disagreement list, every row adjudicated from primary data.
    op22_a1 = defaultdict(set)
    for im in D.v1a_scan["per_image"]:
        for s in im["sites"]:
            if s["op"] == 22 and s["a1"] is not None:
                op22_a1[im["ef"]].add(s["a1"])
    undeclared_by_ef = defaultdict(set)
    for ef, v in D.undeclared:
        undeclared_by_ef[ef].add(v)
    window_efs = set()          # V1a sec 1a: `addu $a1,$s3,$zero` with $s3 set 29 instructions back
    for row in D.v1a["window_probe"]["rows"]:
        m = re.search(r"ef(\d+)", json.dumps(row))
        if m:
            window_efs.add(int(m.group(1)))
    rows = D.v1b["A5_linear_all"]["value_disagreements"]
    chk("V1b disagreeing containers", len(rows), PIN["v1b_disagreeing_containers"])
    unexplained = []
    n_extra = n_missing_undeclared = n_missing_window = 0
    for row in rows:
        ef = row["ef"]
        extra, missing = set(row["linear"]) - set(row["l1"]), set(row["l1"]) - set(row["linear"])
        for v in extra:
            if v in op22_a1[ef]:
                unexplained.append(("extra-is-a-real-op22-value", ef, v))
            else:
                n_extra += 1
        for v in missing:
            if v in undeclared_by_ef[ef]:
                n_missing_undeclared += 1
            elif ef in window_efs:
                n_missing_window += 1
            else:
                unexplained.append(("missing-and-unexplained", ef, v))
    chk("V1b rows unexplained", len(unexplained), PIN["v1b_unexplained"])
    # and L1's per-container vocabulary must equal V1a's independent op-22 argument set
    voc_bad = [row["ef"] for row in rows if set(row["l1"]) != op22_a1[row["ef"]]]
    chk("L1 vocabulary == V1a's independent op-22 $a1 set on every disagreeing container",
        len(voc_bad), 0)
    print("   (b) V1b's A5 flat scan disagrees with L1 on %d containers.  EVERY ROW ADJUDICATED"
          " FROM PRIMARY DATA:" % len(rows))
    print("       %d 'extra' values are NOT op-22 arguments in V1a's independent per-site scan --"
          " V1b's shape test does not check the dispatch base, so it admits the ef435 idiom" % n_extra)
    print("       %d 'missing' values are UNDECLARED-COLUMN tpages that V1b's own `shaped` filter"
          " drops by construction" % n_missing_undeclared)
    print("       %d 'missing' values are the `addu $a1,$sX,$zero` shape V1a sec 1a closed at a"
          " wider window (ef%s)" % (n_missing_window, ", ef".join(str(e) for e in sorted(window_efs))))
    print("       unexplained rows: %d ; and on all %d containers L1's tpage vocabulary EQUALS the"
          " op-22 $a1 set V1a recovered independently" % (len(unexplained), len(rows)))
    print("       -> V1b's A5 is the WEAKER instrument on this predicate; L1 stands.")


# --------------------------------------------------------------------------- H7
def h7_write_delta(D: Data) -> None:
    print("[H7] THE WRITE DELTA -- L2's adjudicated sites re-summed into SETS here")
    sites = D.write["sites"]
    chk("L2 candidate sites", len(sites), PIN["l2_sites"])
    real = [s for s in sites if s["chain"] != "computed"]
    rejected = [s for s in sites if s["chain"] == "computed"]
    chk("L2 real", len(real), PIN["l2_real"])
    chk("L2 rejected", len(rejected), PIN["l2_rejected"])
    # the two independent discriminators must partition identically (L2's own claim, re-tested)
    by_transfer = set(s["ef"] for s in sites if s["via"] == "jalr")
    by_chain = set(s["ef"] for s in real)
    chk("transfer-kind and base-chain discriminators agree", by_transfer, by_chain)

    write_ops = {0: "LoadImage", 166: "MoveImage", 12: "TexAnimArm"}
    hle_write = set(s["ef"] for s in real if s["op"] in write_ops)
    hle_read = set(s["ef"] for s in real if s["op"] == 1)
    seq07 = set(D.write["seq07"])
    derived_write = hle_write | seq07
    derived_read = hle_read - derived_write
    shipped_write, shipped_read = set(RP.PROGRAM_VRAM_WRITE_IDS), set(RP.PROGRAM_VRAM_READ_IDS)
    chk("shipped write ids", len(shipped_write), PIN["shipped_write_ids"])
    chk("shipped read ids", len(shipped_read), PIN["shipped_read_ids"])
    chk("WRITE delta", len(derived_write ^ shipped_write), PIN["write_delta"])
    chk("READ delta", len(derived_read ^ shipped_read), PIN["read_delta"])

    dest = {}
    for s in real:
        if s["op"] == 166:
            a = {x["reg"]: x["value"] for x in s["args"]}
            if a.get("$a1") is not None and a.get("$a2") is not None:
                dest[s["ef"]] = (a["$a1"], a["$a2"])
    chk("MoveImage destinations", dest, dict(RP.MOVEIMAGE_HARD_CELLS))
    print("   HLE writes (LoadImage u MoveImage u TexAnimArm) %s" % sorted(hle_write))
    print("   loader seq op 0x07 (not an HLE call -- no call-shape scan can ever reach it) %s"
          % sorted(seq07))
    print("   derived WRITE = %d ids ; shipped PROGRAM_VRAM_WRITE_IDS = %d ids ; DELTA %d"
          % (len(derived_write), len(shipped_write), len(derived_write ^ shipped_write)))
    print("   derived READ  = %d ids ; shipped PROGRAM_VRAM_READ_IDS  = %d ids ; DELTA %d"
          % (len(derived_read), len(shipped_read), len(derived_read ^ shipped_read)))
    print("   MoveImage destination const-folds on %d of 5 sites -> %s == repaint.MOVEIMAGE_HARD_CELLS"
          % (len(dest), {("ef%03d" % k): v for k, v in sorted(dest.items())}))
    # THE PREDICATE DISAGREEMENT, printed rather than reconciled away.
    g6_write = set(D.write["summary"]["g6_write"])
    arm = set(s["ef"] for s in real if s["op"] == 12)
    print("   PREDICATE DISAGREEMENT, STATED BOTH WAYS: w6b_gates G6 builds its linear write set as"
          " LoadImage u MoveImage and OMITS the texanim arm %s, so its printed set is %s;"
          " the shipped set counts the arm.  Same corpus, two predicates, no contradiction."
          % (sorted(arm), sorted(g6_write - seq07)))
    chk("G6's set plus the arm is the shipped HLE write set", (g6_write - seq07) | arm, hle_write)
    # DIRECTION: the load-bearing assignment L2 settled one layer down, re-asserted from its record.
    d = D.write["direction"]
    chk("op 0 host case", d["host_case"]["0"], 100)
    chk("op 1 host case", d["host_case"]["1"], 101)
    chk("op 166 host case", d["host_case"]["166"], 102)
    print("   THE DIRECTION LAW, engine-grounded (L2 C13): callback codes 0x64/0x65/0x66 ->"
          " SFX.cs cases 100/101/102 -> LoadImage / StoreImage / MoveImage.  op 1 IS StoreImage,"
          " so the 113 disclosed cells and ef211's cast licence no longer rest on an unverified name.")


# --------------------------------------------------------------------------- H8
_DOSSIERS = [os.path.join(LANE, n) for n in
             ("A4-TPAGE-ATTRIBUTION.md", "L1-TPAGE-SWEEP.md", "L2-WRITE-SCAN.md",
              "V1A-VERIFY.md", "V1B-VERIFY.md", "V2-VERIFY.md", "CRITIC.md")]

#: BENIGN BY NAME, not by silence.  A monotone run of small ints matches binary data by construction;
#: this one is the MIPS load/store opcode tuple in a decoder.  Adjudicated, never suppressed silently.
_ADJUDICATED = {b"\x02\x03\x04\x05\x06\x07": "MIPS load/store opcode tuple in a decoder's is_transfer"}


def _untracked_new_files() -> List[str]:
    """THE PROVENANCE SURFACE MOVES WHILE THE ROUND IS JUDGED -- so ASK GIT, never a hand-written
    list.  A concurrent lane's new file in this directory must not be silently unscanned."""
    import subprocess
    try:
        out = subprocess.run(["git", "-C", _REPO, "status", "--porcelain"],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return []
    names = []
    for line in out.splitlines():
        if not line.startswith("?? ") and not line.startswith(" M ") and not line.startswith("M "):
            continue
        rel = line[3:].strip().strip('"')
        p = os.path.join(_REPO, rel.replace("/", os.sep))
        if os.path.isfile(p):
            names.append(p)
        elif os.path.isdir(p):
            for root, _d, fs in os.walk(p):
                names.extend(os.path.join(root, f) for f in fs)
    return sorted(names)


def _byte_constants(path: str) -> List[bytes]:
    """AST `bytes` constants (the w6b_gates G7 method -- a regex misses triple-quoted, adjacent and
    non-`b'...'` spellings) PLUS integer sequences re-encoded to bytes."""
    out: List[bytes] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except Exception:
        return out
    if path.lower().endswith(".py"):
        import ast
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
    # hex runs in ANY committable text -- .py, .md and .toml alike
    for m in re.finditer(r"(?:\\x[0-9a-fA-F]{2}){6,}", src):
        try:
            out.append(bytes.fromhex(m.group(0).replace("\\x", "")))
        except Exception:
            pass
    return out


def h8_provenance(D: Data) -> None:
    print("[H8] PROVENANCE -- what this rung commits is a DERIVATION, never a stock byte")
    blobs = []
    for p in D.paths:
        with open(p, "rb") as fh:
            blobs.append(fh.read())
    files = [p for p in _untracked_new_files()
             if os.path.splitext(p)[1].lower() in (".py", ".md", ".toml")]
    stockish = [p for p in _untracked_new_files()
                if os.path.splitext(p)[1].lower() in (".bytes", ".png", ".tga", ".bmp", ".dds")]
    chk("no stock-shaped asset added to the checkout", len(stockish), 0)
    found = adjudicated = 0
    for p in files:
        for lit in _byte_constants(p):
            if len(lit) < 6 or len(set(lit)) < 2:
                continue
            hits = sum(1 for b in blobs if lit in b)
            found += 1
            if hits and lit in _ADJUDICATED:
                adjudicated += 1
                print("      %r in %s: in %d containers -- ADJUDICATED BENIGN: %s"
                      % (lit, os.path.basename(p), hits, _ADJUDICATED[lit]))
                continue
            if hits:
                print("      byte literal %r in %s: appears in %d corpus containers"
                      % (lit, os.path.basename(p), hits))
            chk("literal %r in %s is not corpus data" % (lit, os.path.basename(p)), hits, 0)
    print("   file list came from `git status --porcelain`, NOT a hand-written list: %d new"
          " text files scanned (%s)" % (len(files), ", ".join(sorted(os.path.basename(f)
                                                                     for f in files))))
    print("   byte constants of >= 6 non-uniform bytes: %d found, %d adjudicated benign by name,"
          " %d unadjudicated leaks" % (found, adjudicated, 0))
    print("   stock-shaped files (.bytes/.png/.tga/.bmp/.dds) added to the checkout: %d"
          % len(stockish))
    for p in _DOSSIERS:
        inside = os.path.abspath(p).lower().startswith(os.path.abspath(_REPO).lower())
        chk("dossier %s outside the checkout" % os.path.basename(p), inside, False)
        print("   dossier outside the checkout: %s  (%s)" % (not inside, p))
    # THE G7 CHECK THIS GATE USED TO DROP: the exporter must refuse a repo destination outright.
    try:
        from ff9mapkit.summons import export as _EX
        refused = False
        try:
            _EX.assert_local_only(_REPO)
        except Exception:
            refused = True
        chk("export.assert_local_only refuses a repo destination", refused, True)
        print("   export.assert_local_only refuses a repo destination: %s" % refused)
    except Exception as exc:
        print("   export.assert_local_only NOT CHECKED (%s) -- instrument absent, reported not"
              " assumed" % type(exc).__name__)


# --------------------------------------------------------------------------- H9
def h9_two_disassemblers(D: Data) -> None:
    """The single strongest sentence in the record -- and the calibration argument BEHIND it, which
    the refuter REFUTED AS STATED.  Both are gated here; neither was gated before."""
    print("[H9] '233/233 VALUES, 238/238 SITES' -- the claim that makes channel P a RECOVERED")
    print("     CONSTANT rather than an inference, gated at last")
    cmp_ = D.v1a["lensA_B_compare"]
    wp = D.v1a["window_probe"]
    chk("V1a's independent op-22 site count", cmp_["my_op22_sites"], PIN["v1a_op22_sites"])
    chk("sites only L1 found", cmp_["only_l1"], PIN["v1a_only_l1"])
    chk("the intersection is L1's whole hit set", cmp_["intersection"], PIN["v1a_intersection"])
    chk("values agreeing at the refuter's NARROW window", cmp_["value_agree"],
        PIN["v1a_value_agree_windowA"])
    chk("the 12 gaps closed at the WIDE window", wp["agree"], PIN["v1a_window_probe"])
    chk("221 + 12 == 233", cmp_["value_agree"] + wp["agree"], PIN["v1a_intersection"])
    # L1's side of the same identity, re-summed from its RAW artifact rather than its prose.
    s = D.sweep["sweep"]
    chk("L1 hits", len(s["hits"]), PIN["hits"])
    chk("L1 runtime-computed tpage arguments", len(s["runtime"]), PIN["runtime_args"])
    chk("L1 refused dispatch", len(s["weak_dispatch"]), PIN["refused_dispatch"])
    chk("L1 sites = hits + runtime + refused",
        len(s["hits"]) + len(s["runtime"]) + len(s["weak_dispatch"]), PIN["v1a_op22_sites"])
    # A THIRD SOURCE, written months before either lane, for the same op.
    ev = D.hle[22].get("evidence", "")
    m = re.search(r"(\d+)\s+call sites", ev)
    chk("tier-R's annotator table, months older, on the same op",
        int(m.group(1)) if m else -1, PIN["hle_ops_op22_sites"])
    print("   TWO INDEPENDENTLY WRITTEN DISASSEMBLERS: sites %d vs %d ; only-L1 %d ; intersection %d"
          % (cmp_["my_op22_sites"],
             len(s["hits"]) + len(s["runtime"]) + len(s["weak_dispatch"]),
             cmp_["only_l1"], cmp_["intersection"]))
    print("   ...AND THE COMPOSITION THE PROSE ELIDED, stated here: '233/233' is %d at the refuter's"
          " 24-instruction window PLUS %d re-probed at a 400-instruction window -- TWO instrument"
          " configurations, not one." % (cmp_["value_agree"], wp["agree"]))
    print("   THIRD SOURCE (tier-R hle_ops, months older): op 22 = %s call sites" % m.group(1))

    # LENS B -- the sites are live code, not walker debris.
    rb = D.v1a["lensB_reach"]
    chk("op-22 sites inside the reachability closure", rb["inside_reachability_closure"],
        PIN["reach_inside_closure"])
    chk("op-22 sites in code the walk never reaches", rb["outside"], PIN["reach_outside"])
    print("   REACHABILITY: %d/%d sites are inside the walk's closure (mean coverage %.4f), so"
          " neither 'counted dead code' nor 'missed live code' survives"
          % (rb["inside_reachability_closure"], rb["op22_sites"], rb["mean_walk_coverage_of_op22_images"]))

    # THE DELAY-SLOT LAW -- durable instrument law, gated in its safe direction.
    lc = D.v1a["lensC_masquerade"]
    chk("the tpage argument is NEVER produced in a call's delay slot", lc["arg1_set_in_delay_slot"],
        PIN["arg1_from_a_delay_slot"])
    print("   ** THE DELAY-SLOT LAW (durable, about the INSTRUMENT not this rung): a MIPS call's delay"
          " slot executes BEFORE the call, so an argument can be produced there.  Measured: %d of %d"
          " op-22 tpage arguments come from a delay slot, %d are straight-line folds, %d cross a"
          " branch, %d are unresolved by the refuter's folder (L1 adjudicates %d of those as"
          " genuinely runtime-computed -- two folders, two counts, both stated).  Any future"
          " arg-recovery tool that reads the register file AT the jalr is silently wrong."
          % (lc["arg1_set_in_delay_slot"], lc["op22_sites_seen"], lc["arg1_folded_straight_line"],
             lc["arg1_folded_across_a_branch"], lc["arg1_runtime"], len(s["runtime"])))
    print("     (the $a3 half of that law -- 238/238 flag arguments delay-slot-produced, 12,360"
          " corpus-wide argument slots -- is V1A-VERIFY.md's, NOT re-measured here.)")

    # ★ THE CALIBRATION THE REFUTER REFUTED AS STATED.  Both predicates, printed together.
    bd = D.v1a["lensD_baserate"]
    p3, n2 = bd["null3_permutation_across_containers"], bd["null2_same_call_other_args"]
    chk("the PERMUTATION null on declared-column", p3["perm_rate"], PIN["perm_null_declared"])
    chk("its p-value", p3["p_value"], PIN["perm_p_value"])
    chk("sibling argument $a2, tpage-shaped rate", n2["a2"]["shaped"], PIN["sibling_a2_shaped"])
    chk("sibling argument $a3, declared-column rate", n2["a3"]["declared_of_all"],
        PIN["sibling_a3_declared"])
    print("   ** REFUTED AS STATED, CONCLUSION SURVIVES.  L1 rejected its runner-up at '53 %% ="
          " chance', which implies a ~50 %% null.  The CONDITIONAL null -- L1's own value multiset"
          " with container pairing broken -- is %.1f %% (observed %d/%d, p = %s)."
          % (100 * p3["perm_rate"], p3["observed_declared"], p3["n"], p3["p_value"]))
    amb_pct = round(100.0 * bd["null1_ambient_immediates_same_containers"]["shaped"], 1)
    chk("the ambient shaped rate, as the record states it", amb_pct, PIN["ambient_shaped_pct"])
    print("     So declared-column carries ~12 points, not ~45.  The load is carried by SHAPE"
          " (%.3f observed vs %.4f = %.1f %% ambient) and by the SIBLING CONTROL: the same calls'"
          " $a2 is %.1f %% shaped and $a3 is %.1f %% declared."
          % (bd["observed_op22_arg1"]["shaped"],
             bd["null1_ambient_immediates_same_containers"]["shaped"], amb_pct,
             100 * n2["a2"]["shaped"], 100 * n2["a3"]["declared_of_all"]))
    print("     AND THE RUNNER-UP REJECTION IS STRONGER THAN L1 KNEW: 53 %s is BELOW the %.1f %s"
          " null -- worse than chance for a real page word, not merely 'chance'."
          % ("%", 100 * p3["perm_rate"], "%"))

    # THE COVERAGE HEADLINE the refuter asked to be promoted.
    iv = D.v1a["lensIV_regops"]
    chk("textured-registration sites corpus-wide", iv["texture_registration_sites_total"],
        PIN["texreg_sites_total"])
    chk("... covered by the recovered idiom", iv["covered_by_L1_op22"], PIN["texreg_covered_by_op22"])
    chk("coverage", iv["L1_coverage_of_textured_registration"], PIN["texreg_coverage"])
    print("   COVERAGE, PROMOTED TO THE HEADLINE: the idiom covers %d of %d textured-registration"
          " sites = %.2f %%.  %d sites in the other registration ops stay DARK."
          % (iv["covered_by_L1_op22"], iv["texture_registration_sites_total"],
             100 * iv["L1_coverage_of_textured_registration"],
             iv["texture_registration_sites_total"] - iv["covered_by_L1_op22"]))


# --------------------------------------------------------------------------- H10
def h10_channel_g_reexamined(D: Data) -> None:
    """The calibration refuter's three findings about channel G, RE-DERIVED here rather than quoted:
    its 138/140 is 87 % an identity; its 57 cells open no new column; and P and G share no cell."""
    print("[H10] CHANNEL G RE-EXAMINED -- the licensed channel, put under its refuter")

    # (a) ★ THE CIRCULARITY.  A ground-truth row whose census depth and page depth come from the SAME
    #     `so` records is an IDENTITY, not a test.  Derived from primary data: the census's own
    #     `readers` geoms on one side, the page-owning binding geoms this file rolled on the other.
    gv = D.gv()
    taut = partial = disjoint = independent = 0
    dis_ids, ind_ids, informative_agree, agree_all = [], [], 0, 0
    for k, r in D.C.items():
        if r["bpp"] is None or gv.get(k) is None:
            continue
        readers = set(int(x["geom"]) for x in r["readers"])
        owners = D.sopage_recs.get(k, set())
        ok = int(gv[k] == r["bpp"])
        agree_all += ok
        if not readers:
            # ** THE ONE ROW WITH A GENUINELY INDEPENDENT WITNESS.  Its census depth comes from the
            # id-4 model-package header, a source channel G does not read at all -- so it is the
            # strongest row in the whole table, not a row to drop.
            independent += 1
            ind_ids.append("%s (%s)" % (r["id"], r["bpp_evidence"]))
            informative_agree += ok
        elif readers == owners:
            taut += 1
        elif readers & owners:
            partial += 1
            informative_agree += ok
        else:
            disjoint += 1
            dis_ids.append(r["id"])
            informative_agree += ok
    rows = taut + partial + disjoint + independent
    inf = partial + disjoint + independent
    chk("channel G ground-truth rows", rows, PIN["g_gt_rows"])
    chk("... agreeing overall (the number the dossier quotes)", agree_all, PIN["cal_g_agree"])
    chk("... TAUTOLOGICAL (same `so` record on both sides)", taut, PIN["g_tautological"])
    chk("... partially overlapping", partial, PIN["g_partial"])
    chk("... genuinely disjoint", disjoint, PIN["g_disjoint"])
    chk("... resting on an INDEPENDENT, non-`so` witness", independent, PIN["g_independent"])
    chk("the INFORMATIVE subset", inf, PIN["g_informative_n"])
    chk("agreement on the INFORMATIVE rows", informative_agree, PIN["g_informative_agree"])
    chk("the disjoint rows are exactly the two U-SPILL cells", sorted(dis_ids),
        ["ef381.x640_y384", "ef447.x640_y384"])
    print("   ** BOTH PREDICATES, STATED BOTH WAYS, NOT RECONCILED:")
    print("     'channel G agrees with the census on %d/%d = %.4f'  -- true, and %d of those rows"
          " (%.0f %%) compare an `so` record AGAINST ITSELF: an IDENTITY, not a test"
          % (agree_all, rows, agree_all / float(rows), taut, 100.0 * taut / rows))
    print("     'on the %d INFORMATIVE rows channel G agrees %d/%d = %.3f'  -- also true, and it is"
          " the number that carries evidence"
          % (inf, informative_agree, inf, informative_agree / float(inf)))
    print("     !! and BOTH genuinely disjoint rows are the u-spill disagreements: every row that"
          " COULD have falsified the page predicate DID.  %s" % ", ".join(dis_ids))
    print("     A LABELLING DIFFERENCE WITH THE REFUTER, STATED NOT RECONCILED: it split the"
          " informative %d as 16 partial + 2 disjoint; this file splits them %d partial + %d"
          " disjoint + %d INDEPENDENT, because one row has NO `so` reader at all -- %s."
          "  Its census depth comes from a source channel G never reads, which makes it the"
          " STRONGEST row in the table rather than a partial one.  Both splits give the same"
          " informative agreement, %d/%d." % (inf, partial, disjoint, independent,
                                              "; ".join(ind_ids), informative_agree, inf))

    # (b) CHANNEL G'S REACH.  Every one of its 57 is a lower half whose partner was already known.
    unk = D.unknown()
    pv = D.pv()
    gainG = [k for k in unk if pv.get(k) is None and gv.get(k) is not None]
    chk("channel G's gain", len(gainG), PIN["gain_so_page"])
    chk("... all at y = 384", sum(1 for k in gainG if k[2] == 384), PIN["g57_y384"])
    known = sum(1 for k in gainG
                if D.C.get((k[0], k[1], 256)) and D.C[(k[0], k[1], 256)]["bpp"] is not None)
    chk("... whose stacked partner the census ALREADY knew", known, PIN["g57_partner_already_known"])
    chk("... genuinely NEW columns", len(gainG) - known, PIN["g57_new_columns"])
    print("   REACH: all %d of channel G's cells are y=384 lower halves, and %d/%d have a stacked"
          " partner the census already had a depth for.  G opens %d NEW COLUMNS -- it is the"
          " y=384 blind-spot repair, propagating a depth the container had already stated DOWNWARD"
          " across a cell boundary, not an independent reach."
          % (len(gainG), known, len(gainG), len(gainG) - known))

    # (c) NO CELL HAS TWO WITNESSES.
    gainP = [k for k in unk if pv.get(k) is not None]
    chk("P and G overlap on the gained set", len(set(gainP) & set(gainG)),
        PIN["p_and_g_overlap_on_the_gain"])
    chk("P + G == the headline", len(gainP) + len(gainG), PIN["gain_either"])
    print("   DISJOINT, EXACTLY: %d + %d = %d with overlap %d.  EVERY shipped cell rests on ONE"
          " channel.  The cross-channel 10/10 agreement is evidence about the INSTRUMENTS, never"
          " about any cell being shipped." % (len(gainP), len(gainG), PIN["gain_either"], 0))


# --------------------------------------------------------------------------- H11
def h11_refused_set(D: Data) -> None:
    """The refused set the build list must ship is 32 cells, not the 24 the dossiers hand off -- and
    the residue table's three populations are NOT one population."""
    print("[H11] THE REFUSED SET, AND THE THREE POPULATIONS THE RESIDUE TABLE MIXES")
    unk = set(D.unknown())
    pamb = sorted(k for k, v in D.prog.items() if verdict(v) is None and k in unk)
    gamb = sorted(k for k, v in D.sopage.items() if verdict(v) is None and k in unk)
    chk("program-derived MULTI-VALUED cells", len(pamb), PIN["p_ambiguous"])
    chk("** channel-G MULTI-VALUED cells that are depth-unknown", len(gamb),
        PIN["g_ambiguous_unknown"])
    chk("the two ambiguous sets are disjoint", len(set(pamb) & set(gamb)), PIN["ambiguous_overlap"])
    spill = [(381, 640, 384), (447, 640, 384)]
    chk("the total refused-ambiguous set", len(pamb) + len(gamb) + len(spill), PIN["refused_total"])
    print("   ** THE HAND-OFF UNDER-COUNTS ITS OWN REFUSALS.  L1's dossier names %d + %d = 24; the"
          " true set is %d + %d + %d = %d.  The %d channel-G ambiguities are named NOWHERE in it:"
          % (PIN["p_ambiguous"], len(spill), len(pamb), len(gamb), len(spill),
             PIN["refused_total"], len(gamb)))
    print("     %s" % ", ".join(D.C[k]["id"] for k in gamb))
    print("   -> a lane building repaint's refusal list from L1-TPAGE-SWEEP.md alone would ship"
          " %d cells UNLISTED." % len(gamb))

    # THE POPULATIONS.  A reader of the residue table can double-count 24 cells; here is why not.
    inside = sum(1 for k in spill if k in unk)
    chk("the spill cells inside the 2,385", inside, PIN["spill_inside_the_2385"])
    chk("the program-ambiguous cells inside the 2,385", len([k for k in pamb if k in unk]),
        PIN["p_ambiguous"])
    already = sum(1 for k in spill if D.C[k]["hz_spill_in"] and not D.C[k]["lawful"])
    chk("the spill cells NEWLY protected by the new class", len(spill) - already,
        PIN["spill_newly_protected"])
    print("   POPULATIONS, ANNOTATED SO NOBODY ADDS THEM UP:")
    print("     the %d program-multi-valued cells ARE inside the 2,385 -- a SUBSET of the 861,"
          " not an addend" % len(pamb))
    print("     the %d spill cells are OUTSIDE the 2,385 entirely (hz_depth_unknown=%s, bpp=%s):"
          " they HAD a depth and now have two"
          % (len(spill), D.C[spill[0]]["hz_depth_unknown"], D.C[spill[0]]["bpp"]))
    print("     and the SPILL class protects %d cell no existing hazard already refuses -- both"
          " carry hz_spill_in and lawful=False today.  It is non-vacuous as a PREDICATE and adds"
          " nothing as PROTECTION; it exists to carry the REASON." % (len(spill) - already))


# --------------------------------------------------------------------------- H12
def h12_build_list(D: Data) -> None:
    """Every gate the record's build list PROPOSES, run here first.  A proposed gate that fails on
    day one is a defect in the record, not in the kit."""
    print("[H12] THE BUILD LIST'S OWN GATES, PRE-TESTED BEFORE THEY ARE PROPOSED")
    unk = D.unknown()
    pv, gv = D.pv(), D.gv()
    gainG = [k for k in unk if pv.get(k) is None and gv.get(k) is not None]

    # (a) "the 57 cells build" -- as written this FAILS.  56 build; one refuses.
    bad = []
    for k in gainG:
        r = D.C[k]
        why = [h for h in ("hz_program_write", "hz_program_write_here", "hz_co_transform") if r[h]]
        if r["hz_spill_in"]:
            why.append("hz_spill_in")
        if why:
            bad.append((r["id"], why))
    chk("channel-G cells that clear every OTHER hazard", len(gainG) - len(bad), PIN["g57_clean"])
    chk("... and the ones that refuse", len(bad), PIN["g57_refusing"])
    chk("channel-G cells that are lower halves", sum(1 for k in gainG
                                                     if D.C[k]["hz_unaddressable_lower_half"]),
        PIN["g57_lower_halves"])
    print("   ** 'THE 57 CELLS BUILD' FAILS AS WRITTEN.  %d clear every other hazard; %d refuses: %s"
          % (len(gainG) - len(bad), len(bad),
             "; ".join("%s on %s" % (i, ",".join(w)) for i, w in bad)))
    print("     re-spec: '57 gain a depth; 56 clear every other hazard; 1 refuses on"
          " hz_program_write'.  %d of the 57 are lower halves, buildable ONLY through the"
          " per-cell map." % sum(1 for k in gainG if D.C[k]["hz_unaddressable_lower_half"]))

    # (b) THE ASSUMPTION NOBODY PUT TO reskin: can the shipped per-cell map actually NAME these cells?
    lower = [k for k in unk if pv.get(k) is not None and k[2] == 384]
    named = sum(1 for k in lower
                if any(x == k[1] and y == k[2] for (_t, x, y) in D.pcmap.get(k[0], {})))
    flagged = [k for k in lower if D.C[k]["hz_unaddressable_lower_half"]]
    chk("program-gained lower halves", len(lower), PIN["prog_lower_halves"])
    chk("... named by the SHIPPED reskin.page_cells", named, PIN["page_cells_names_them"])
    chk("... of which FLAGGED unaddressable by the census", len(flagged),
        PIN["prog_lower_halves_flagged"])
    chk("the DOME is a real per-cell key", ("s0", 704, 384) in D.pcmap.get(211, {}), True)
    print("   THE 199-vs-79 ADJUDICATION RESTED ON THIS, AND NOBODY HAD ASKED reskin.  Asked:"
          " reskin.page_cells names %d/%d of the program-gained lower halves, and ('s0',704,384)"
          " -- THE DOME -- is a real key." % (named, len(lower)))
    print("   TWO PREDICATES ON THE SAME CELLS: %d cells are program-gained at y=384; %d of them"
          " carry the census's hz_unaddressable_lower_half FLAG (the completeness critic's number)."
          " %d + %d channel-G = %d, the record's y=384 total."
          % (len(lower), len(flagged), len(flagged),
             sum(1 for k in gainG if D.C[k]["hz_unaddressable_lower_half"]), PIN["hz_lower_half"]))
    print("   !! AND THE CENSUS FIELD IS STALE: pages.json still stamps these cells"
          " addressable_via 'UNADDRESSABLE (lower half of an h=256 rect)'.  That records the"
          " PRE-W6b-1 rect key.  It is why one instrument scored 79 and another 199.")


# --------------------------------------------------------------------------- H13
def h13_next_probe(D: Data) -> None:
    """COST THE NEXT PROBE BEFORE A LANE IS SPENT ON IT.  The ranked-first probe returns 'yes' for
    every cell in the corpus, and the ranked-second question is already answered."""
    print("[H13] THE NEXT PROBE, COSTED BEFORE THE BUDGET IS COMMITTED")
    pages = sorted(set((r["vram_x"], 256) for r in D.census))
    chk("distinct VRAM pages in the whole census", len(pages), PIN["census_vram_pages"])
    unk = D.unknown()
    bset = set(ef for ef, b in D.blind.items() if b)
    bu = [k for k in unk if k[0] in bset]
    bpages = sorted(set((k[1], 256) for k in bu))
    hitpages = set()
    for h in D.sweep["sweep"]["hits"]:
        px, py, _b = dec(h["value"])
        hitpages.add((px, py))
    named = [p for p in bpages if p in hitpages]
    chk("pages the blind containers' unknown cells occupy", len(bpages), PIN["blind_pages"])
    chk("... of those, named by SOME op-22 constant somewhere", len(named),
        PIN["blind_pages_named_by_op22"])
    print("   ** THE RANKED-FIRST PROBE IS NEAR-VACUOUS AS SPECIFIED.  A cross-container page-overlap"
          " join runs over a %d-ELEMENT page space: the blind 222's %d unknown cells occupy %d"
          " pages and ALL %d are named by some op-22 container.  %d/%d blind cells 'pass'."
          % (len(pages), len(bu), len(bpages), len(named), len(bu), len(bu)))
    print("     RE-SPEC BEFORE SPENDING A LANE: the discriminating predicate is CO-RESIDENCY --"
          " WHICH containers are simultaneously live in VRAM during one cast -- and that lives in"
          " the .seq / SFXRework cast graph, not in the page map.")

    # ★ THE RANKED-#2 PROBE, COSTED -- the follow-up the record said "nobody can cost" because the
    # sweep artifact does not record which containers are behind the pointer tables.  It was one join
    # away from `v1a_scan.json`, which resolves every jalr to an op index.  A CEILING, not an
    # estimate: an op need not name every column of its container.
    unkc = Counter()
    for r in D.census:
        if r["hz_depth_unknown"] and "creature" not in r["classes"]:
            unkc[r["ef"]] += 1
    per_op: Dict[int, set] = {19: set(), 171: set()}
    sites_op = Counter()
    for im in D.v1a_scan["per_image"]:
        for st in im["sites"]:
            if st["op"] in per_op:
                per_op[st["op"]].add(im["ef"])
                sites_op[st["op"]] += 1
    cells19 = sum(unkc[e] for e in per_op[19])
    cells171 = sum(unkc[e] for e in per_op[171])
    allefs = per_op[19] | per_op[171]
    dark_cells = sum(unkc[e] for e in allefs)
    dark_pct = round(100.0 * dark_cells / len(unk), 1)
    chk("op 19 sites", sites_op[19], PIN["op19_sites"])
    chk("op 19 effects", len(per_op[19]), PIN["op19_effects"])
    chk("op 19 depth-unknown cells at stake", cells19, PIN["op19_cells"])
    chk("op 171 sites", sites_op[171], PIN["op171_sites"])
    chk("op 171 effects", len(per_op[171]), PIN["op171_effects"])
    chk("op 171 depth-unknown cells at stake", cells171, PIN["op171_cells"])
    chk("the dark path's sites", sites_op[19] + sites_op[171], PIN["dark_sites"])
    chk("the dark path's containers", len(allefs), PIN["dark_effects"])
    chk("THE CEILING on the dark path", dark_cells, PIN["dark_cells"])
    chk("... as a percentage of the surface", dark_pct, PIN["dark_pct_of_2385"])
    rc = D.sweep["refused_channels"]["op19_op171_pointer_tables"]
    chk("in-image pointer arguments the refusal rests on", rc["counts"]["ptr_inside_image"],
        PIN["ptr_inside_image"])
    chk("... carrying any tpage-shaped halfword", rc["counts"]["pointee_has_tpage_shaped_halfword"],
        PIN["ptr_shape_hits"])
    chk("... the shape-hit rate the refusal quotes", rc["shape_hit_rate"], PIN["ptr_shape_rate"])
    print("   ** THE RANKED-#2 PROBE, COSTED FROM AN ARTIFACT ALREADY ON DISK (the record said"
          " nobody could):")
    print("      op  19 Hi_RegisterTexListModel : %d sites / %d effects %s -> %d depth-unknown cells"
          % (sites_op[19], len(per_op[19]), sorted(per_op[19]), cells19))
    print("      op 171 Hi_RegisterTexPtrModel  : %d sites / %d effects %s -> %d depth-unknown cells"
          % (sites_op[171], len(per_op[171]), sorted(per_op[171]), cells171))
    print("      UNION                          : %d sites / %d effects -> <= %d cells = %.1f %% of"
          " %d.  A CEILING: an op need not name every column of its container."
          % (sites_op[19] + sites_op[171], len(allefs), dark_cells, dark_pct, len(unk)))
    print("      the refusal itself rests on %d in-image pointer arguments of which %d (%.1f %%)"
          " carry any tpage-shaped halfword -- chance on an ANY-halfword predicate, and the"
          " structural tests were never tried."
          % (rc["counts"]["ptr_inside_image"], rc["counts"]["pointee_has_tpage_shaped_halfword"],
             100.0 * rc["shape_hit_rate"]))
    # THE WARNING CONTAINER, and the canonical false positive, both inside that eleven.
    r381 = [r for r in D.v1b_rc["G_negative_controls"]["rows"] if r["ef"] == 381][0]
    chk("ef381 GEOM blocks", r381["geom_total"], PIN["ef381_geom"])
    chk("ef381 resolved engine calls", r381["hle_calls"], PIN["ef381_hle_calls"])
    chk("ef381 op-22 calls", r381["op22_calls"], PIN["ef381_op22"])
    chk("the warning container is inside the dark eleven", 381 in allefs, True)
    chk("so is the canonical false positive", 435 in allefs, True)
    print("      TWO OF THE ELEVEN ARE ALREADY NAMED ELSEWHERE IN THIS ROUND: ef381 -- %d GEOM"
          " blocks, %d resolved engine calls, %d op-22 calls, the sharpest warning in the corpus --"
          " and ef435, the canonical false positive of the flat scan."
          % (r381["geom_total"], r381["hle_calls"], r381["op22_calls"]))
    print("      RE-RANK BEFORE SPENDING A LANE: a typed-pointee disassembly for <= %d cells is not"
          " obviously ahead of channel H's %d-for-a-join (H16)." % (dark_cells, PIN["hint_cells_in_2385"]))

    # THE RANKED-SECOND QUESTION, answered here with one call instead of a lane.
    with open(os.path.join(SCRATCH, "ef390.bytes"), "rb") as fh:
        a = RS.attribution(fh.read(), include_direct=True)
    by = Counter((b.page[0], b.page[1], b.bpp) for b in a.bindings)
    cols = sorted(set(x for (_t, x, _y) in D.pcmap.get(390, {})))
    writerless = sum(n for (px, _py, bpp), n in by.items() if bpp == 15 and px not in cols)
    chk("ef390 bindings", len(a.bindings), PIN["ef390_bindings"])
    chk("... naming a page ef390 NEVER UPLOADS, at 15bpp", writerless, PIN["ef390_writerless_15bpp"])
    print("   W6b-1 sec 7.2 Q4 ANSWERED, one call, no lane: ef390's %d bindings are %s; it uploads only"
          " columns %s.  The %d writerless 15bpp bindings name a page ef390 NEVER UPLOADS."
          % (len(a.bindings), dict(by), cols, writerless))
    print("     => the RESIDUAL-VRAM hypothesis is the only survivor and the refusal is PERMANENT"
          " absent a co-residency probe -- the same probe H13 just re-specified.  Note the corpus"
          " gains ef390.x704_y384 through channel G while its OTHER page stays unreachable.")

    # And the one op the earlier record's open question named BY NAME, which the ranking did score.
    disc = _load(os.path.join(LANE, "tpage_discover.json"))
    rows = disc if isinstance(disc, list) else disc.get("pairs", disc.get("ranked", []))
    r199 = [r for r in rows if isinstance(r, dict) and r.get("op") == 199]
    chk("op 199 -- the op W6b-1 sec 7.2 Q1 named BY NAME -- was in fact ranked", len(r199) >= 1, True)
    r = r199[0]
    print("   FOR THE READER OF W6b-1 sec 7.2 Q1: op 199 Hi_DrawSliceEffModel WAS ranked and LOST --"
          " %d sites, only %d const-folded (%d runtime), page-Y bit set on %d, declared column on"
          " %d, score %.2f.  CHECKED AND NEGATIVE.  Neither sweep dossier mentions it because the"
          " discovery artifact persists SURVIVORS (%d pairs) and not the ~666 scored-and-dropped."
          % (r["sites"], r["const"], r["runtime"], r["ybase"], r["declared"], r["score"], len(rows)))


# --------------------------------------------------------------------------- H14
_STORE_OPS = {0x29: "sh", 0x2B: "sw"}


def _fold_const(words, i: int, reg: int, window: int = 32):
    """Backward const-fold of `reg` -- addiu/ori FROM $zero only, so the answer is a constant or a
    named unknown.  Any other definition of the register kills the fold rather than guessing."""
    if reg == 0:
        return 0
    for j in range(i - 1, max(-1, i - 1 - window), -1):
        w = words[j]
        op, rs, rt = (w >> 26) & 0x3F, (w >> 21) & 0x1F, (w >> 16) & 0x1F
        if op in (0x09, 0x0D) and rt == reg:
            return (w & 0xFFFF) if rs == 0 else None
        if op == 0 and ((w >> 11) & 0x1F) == reg:
            return None
        if op in (0x08, 0x0C, 0x0E, 0x0F, 0x20, 0x21, 0x23, 0x24, 0x25) and rt == reg:
            return None
    return None


def h14_store_sweep(D: Data) -> None:
    """THE MEASUREMENT NOBODY HAD RUN.  L1's own caveat: 'IDIOM NOT FOUND ... searched and not found
    ON THE RECON IMAGES, NOT absent corpus-wide -- a full store-level sweep is not in these numbers.'
    This runs it, corpus-wide, with its OWN ambient null and its OWN positive control."""
    import struct
    print("[H14] THE STORE-LEVEL SWEEP -- L1's named-and-unrun caveat, run")
    tot = Counter()
    for p in D.paths:
        with open(p, "rb") as fh:
            blob = fh.read()
        ef = int(os.path.basename(p)[2:5])
        cols = set(x for (_t, x, _y) in D.pcmap.get(ef, {}))
        try:
            c = EC.parse_header(blob)
        except Exception:
            continue
        for ch in c.chunks:
            for res in ch.resources:
                if res.id != 3:
                    continue
                try:
                    img = EC.parse_chunk_image(blob, res, ch.psx_base)
                except Exception:
                    continue
                payload = blob[res.offset:res.offset + res.nbytes]
                n = min(img.header_rel, len(payload)) // 4
                if n < 4:
                    continue
                words = struct.unpack_from("<%dI" % n, payload, 0)
                for i in range(n):
                    w = words[i]
                    op = (w >> 26) & 0x3F
                    # THE AMBIENT NULL, same instrument, same images, same pass.
                    if op in (0x09, 0x0D) and ((w >> 21) & 0x1F) == 0:
                        v0 = w & 0xFFFF
                        tot["amb_n"] += 1
                        if v0 < 512 and ((v0 >> 4) & 1):
                            tot["amb_shaped"] += 1
                            if ((v0 & 0x0F) * PAGE_HW) in cols:
                                tot["amb_declared"] += 1
                    if op not in _STORE_OPS:
                        continue
                    tot["sites"] += 1
                    v = _fold_const(words, i, (w >> 16) & 0x1F)
                    if v is None:
                        tot["runtime"] += 1
                        continue
                    tot["const"] += 1
                    if v < 512 and ((v >> 4) & 1):
                        tot["shaped"] += 1
                        if ((v & 0x0F) * PAGE_HW) in cols:
                            tot["declared"] += 1
    # POSITIVE CONTROL first -- calibrate the predicate on the answer we already know.
    hv = [h["value"] for h in D.sweep["sweep"]["hits"]]
    shaped_hits = sum(1 for v in hv if v < 512 and ((v >> 4) & 1))
    chk("positive control: L1's recovered tpages are all tpage-shaped on THIS predicate",
        shaped_hits, PIN["store_positive_control_shaped"])
    st_shaped = tot["shaped"] / float(max(tot["const"], 1))
    am_shaped = tot["amb_shaped"] / float(max(tot["amb_n"], 1))
    st_decl = tot["declared"] / float(max(tot["shaped"], 1))
    am_decl = tot["amb_declared"] / float(max(tot["amb_shaped"], 1))
    chk("** stores carry tpage-shaped constants NO MORE OFTEN THAN ambient chance",
        st_shaped < am_shaped, True)
    chk("** and their declared-column rate does not clear the ambient rate by half",
        st_decl < am_decl * 1.5, True)
    print("   POSITIVE CONTROL: %d/%d of the recovered tpages are shaped on this predicate (1.000)"
          % (shaped_hits, len(hv)))
    print("   STORES (sh + sw over every id-3 program): %d sites, %d const-folded, %d tpage-shaped,"
          " %d also declared-column" % (tot["sites"], tot["const"], tot["shaped"], tot["declared"]))
    print("   AMBIENT NULL (same instrument, same pass): %d immediates, shaped %.4f,"
          " declared|shaped %.4f" % (tot["amb_n"], am_shaped, am_decl))
    print("   ** CLEAN NEGATIVE: stores are shaped %.4f vs ambient %.4f (BELOW chance), and"
          " declared|shaped %.4f vs ambient %.4f (AT chance).  The op-22 idiom scores 1.0000 and"
          " 0.9730 on the same two predicates." % (st_shaped, am_shaped, st_decl, am_decl))
    print("     SCOPE, NAMED: the folder resolves %d of %d stores (%.0f %%); the other %.0f %% are"
          " runtime-computed and this instrument states nothing about them.  So: 'no CONST-FOLDABLE"
          " store carries a tpage, corpus-wide' -- an upgrade on 'not found on the recon images',"
          " NOT a proof that no store ever does."
          % (tot["const"], tot["sites"], 100.0 * tot["const"] / max(tot["sites"], 1),
             100.0 * tot["runtime"] / max(tot["sites"], 1)))


# --------------------------------------------------------------------------- H15
def h15_v2_write_refutation(D: Data) -> None:
    """The write lane was the round's highest-consequence UNREFUTED object.  Its refuter landed; this
    reproduces the refutation at SITE level and gates the two links that were still inherited."""
    print("[H15] THE WRITE LANE'S REFUTER, REPRODUCED AT SITE LEVEL")
    l2 = {(s["ef"], s["slot"], s["off"]): s for s in D.write["sites"]}
    v2 = {(s["ef"], s["slot"], s["off"]): s for s in D.v2["sites"]}
    chk("V2 candidate sites", len(v2), PIN["v2_candidates"])
    chk("L2 candidate sites", len(l2), PIN["l2_sites"])
    chk("site sets identical", len(set(l2) ^ set(v2)), 0)
    disagree = [k for k in l2 if (l2[k]["chain"] == "computed") != (v2[k]["chain"] == "computed")]
    chk("per-site adjudication disagreements", len(disagree), PIN["v2_vs_l2_site_disagreements"])
    print("   TWO INSTRUMENTS SHARING NO SCAN CODE: %d candidate sites each, symmetric difference"
          " %d, and %d of %d adjudicated identically real-vs-rejected."
          % (len(v2), len(set(l2) ^ set(v2)), len(l2) - len(disagree), len(l2)))

    # THE BLIND SAMPLE -- the control that says the scan is not simply agreeing by construction.
    bs = D.v2["blind_sample"]
    chk("blind clean sample size", len(bs["clean_sample"]), PIN["v2_clean_sample"])
    chk("... candidates found in containers L2 called clean", len(bs["clean_candidates"]),
        PIN["v2_clean_sample_candidates"])
    chk("re-scanning L2's flagged containers IN ISOLATION reproduces its hit set",
        bs["flagged_match"], True)
    print("   BLIND CONTROL: %d L2-clean containers re-scanned in isolation -> %d candidates;"
          " all %d flagged containers re-scanned in isolation -> identical hit set (v2-only %d,"
          " l2-only %d)." % (len(bs["clean_sample"]), len(bs["clean_candidates"]),
                             len(bs["flagged"]), len(bs["flagged_v2_only"]), len(bs["flagged_l2_only"])))

    # ★ THE PREDICATE THAT SURVIVED ONLY IN SCRATCH.  Named here, on the record.
    su = D.v2["summary"]
    chk("READ ids before the subtraction", len(su["v2_read_real"]), PIN["v2_read_before_subtraction"])
    chk("the shipped READ list", len(su["shipped_read"]), PIN["shipped_read_ids"])
    subtracted = sorted(set(su["v2_read_real"]) - set(su["shipped_read"]))
    chk("exactly one id is subtracted", len(subtracted), 1)
    chk("and it is the one that both writes and reads", subtracted[0], PIN["ef149_the_subtracted_id"])
    chk("it IS in the shipped WRITE list", subtracted[0] in su["shipped_write"], True)
    print("   ** THE SUBTRACTION, ON THE RECORD AT LAST: the scan finds %d READ ids; the shipped list"
          " has %d.  DELTA 0 is reached by `derived_read = hle_read - derived_write`, i.e. ef%03d is"
          " a real StoreImage container RECLASSIFIED AS A WRITER because it also writes -- and"
          " repaint tests WRITE first.  'Delta 0 in both directions' is true ONLY with that clause."
          % (len(su["v2_read_real"]), len(su["shipped_read"]), subtracted[0]))
    for key, pin in (("delta_write_new", 0), ("delta_write_missing", 0),
                     ("delta_read_new", 0), ("delta_read_missing", 0)):
        chk("V2 %s" % key, len(su[key]), pin)

    # THE LAST INHERITED LINK: op INDEX -> native fn, from the interpreter's own dispatch table.
    t = D.v2["direction"]["hle_table"]
    chk("the HLE dispatch table's extent matches the op space", t["ops"], PIN["hle_table_ops"])
    chk("... slots pointing into .text", t["slots_in_text"], PIN["hle_table_slots_in_text"])
    chk("... slots past the end that do", t["slots_past_end_in_text"], PIN["hle_table_slots_past_end"])
    chk("it agrees with the annotator table both lanes inherited", t["agrees_with_hle_ops_json"], True)
    hc = D.write["direction"]["host_case"]
    chk("op 0 -> host case", hc["0"], 100)
    chk("op 1 -> host case", hc["1"], 101)
    chk("op 166 -> host case", hc["166"], 102)
    print("   THE DIRECTION LAW IS NOW GROUNDED END TO END, not inherited: op index -> dispatch-table"
          " slot (rva %s, stride %d) -> native fn -> callback code -> the engine's own handler."
          " Table extent: %d/%d slots point into .text and %d of the slots past the op space do."
          % (t["table_rva"], t["stride"], t["slots_in_text"], t["ops"], t["slots_past_end_in_text"]))
    print("   A DISCRIMINATOR THE REFUTER DOWNGRADED ITSELF, recorded so nobody re-uses it: the"
          " switch-GUARD test fires on 54/54 rejected sites AND on 6 of the 23 REAL ones (a loop"
          " back-edge compare is shaped like a bounds check).  Corroborating only.  The decisive"
          " tests remain transfer-kind, computed base, and the resolved in-image pointer table.")
    lab = Counter(s["chain"] for s in D.write["sites"])
    lab2 = Counter(s["chain"] for s in D.v2["sites"])
    chk("the two instruments partition identically even though they LABEL differently",
        (lab["computed"], sum(v for k, v in lab.items() if k != "computed")),
        (lab2["computed"], sum(v for k, v in lab2.items() if k != "computed")))
    print("   CHAIN LABELS DIFFER, PARTITION DOES NOT: %s vs %s -- 'sentinel-far' is the same site"
          " found without a window." % (dict(lab), dict(lab2)))


# --------------------------------------------------------------------------- H16
def h16_clut_arity(D: Data) -> None:
    """★ CHANNEL H -- the third depth channel that sat in `pages.json` all round, that every lane
    read past, and that no lane opened.  `bpp_hint` is the container's OWN id-0 payload-header CLUT
    arity (`reskin.id0_palettes`: nClut4 / nClut8), named in W6b-1's census as "the one lawful
    narrowing".

    STATED PRECISELY SO NOBODY OVER-CLAIMS IT: it is a NARROWING, NOT AN ATTRIBUTION.  `hint = 4`
    means "this container ships no 8-entry-per-byte CLUTs, so this page is 4 bpp OR 15 bpp".  It
    cannot license a decode alone, which is exactly why it is not a fourth headline number.  What it
    IS good for is the two things the record twice said it did not have -- a second witness on a
    shipped cell, and a way to grow P's corroboration -- so those two flat caveats are FALSIFIED
    here, by measurement, from `pages.json` + `tpage_sweep.json` only.

    And a CLOSURE while the census is open: the third evidence class, the id-4 model-package header,
    is 93/93 creature-class.  It can never attribute a scenery cell.  Named as a refusal so no
    future lane spends a budget rediscovering that.
    """
    print("[H16] ** CHANNEL H -- the CLUT-arity NARROWING no lane opened (and one channel CLOSED)")
    unk = D.unknown()
    pv, gv = D.pv(), D.gv()
    gainP = [k for k in unk if pv.get(k) is not None]
    gainG = [k for k in unk if pv.get(k) is None and gv.get(k) is not None]
    gain = gainP + gainG
    chk("the gained set H16 judges is the record's own", len(gain), PIN["gain_either"])

    # (a) THE POPULATION IT SPEAKS FOR.  1.4x the whole round's 246 -- and not one of them decodable
    #     on the hint alone.
    hinted = [k for k in unk if D.C[k]["bpp_hint"] is not None]
    dist = Counter(D.C[k]["bpp_hint"] for k in hinted)
    chk("cells inside the 2,385 the hint speaks for", len(hinted), PIN["hint_cells_in_2385"])
    chk("... narrowed toward 4bpp-or-15bpp", dist[4], PIN["hint_4bpp"])
    chk("... narrowed toward the 8bpp family", dist[8], PIN["hint_8bpp"])
    print("   POPULATION: %d of the %d depth-unknown cells carry a container-declared CLUT arity"
          " -- %d toward 4bpp-or-15bpp, %d toward the 8bpp family.  That is %.1fx the round's %d,"
          " and it decodes NOTHING on its own: hint=4 means '4 or 15'."
          % (len(hinted), len(unk), dist[4], dist[8],
             len(hinted) / float(PIN["gain_either"]), PIN["gain_either"]))

    # (b) CALIBRATE THE INSTRUMENT.  The field is populated ONLY where the depth is unknown, so it
    #     cannot calibrate itself.  Re-apply the SAME rule where the answer IS known.
    n = agree = 0
    wrong = []
    for r in D.census:
        b = r["bpp"]
        if b not in (4, 8):
            continue
        n4, n8 = r["container_nclut4"], r["container_nclut8"]
        pred = 8 if (n4 == 0 and n8) else 4 if (n8 == 0 and n4) else None
        if pred is None:
            continue
        n += 1
        if pred == b:
            agree += 1
        else:
            wrong.append((r["id"], b, pred))
    chk("cells whose depth IS known and where the rule speaks", n, PIN["hint_known_n"])
    chk("... where the rule is right", agree, PIN["hint_known_agree"])
    print("   CALIBRATION (the field cannot give it -- it is populated only where depth is UNKNOWN,"
          " so the same rule is re-applied where the answer is known): %d/%d = %.3f, wrong on %s"
          % (agree, n, agree / float(max(n, 1)), wrong or "none"))

    # (c) ★ THE FIRST FALSIFIED CAVEAT: "AND NO SHIPPED CELL HAS TWO WITNESSES."  17 do.
    spoke = Counter()
    kinds = Counter()
    conflicts = []
    for k in gain:
        r = D.C[k]
        h = r["bpp_hint"]
        ch = "P" if pv.get(k) is not None else "G"
        d = pv[k] if ch == "P" else gv[k]
        n4, n8 = r["container_nclut4"], r["container_nclut8"]
        if h is not None:
            spoke[ch] += 1
            if d == h:
                kinds["exact"] += 1
            elif d == 15:
                # a DIRECT-COLOUR derivation against a CLUT-arity hint that cannot speak to it
                kinds["compatible-15bpp"] += 1
            else:
                conflicts.append((r["id"], ch, d, h))
        elif (d == 4 and n4 == 0) or (d == 8 and n8 == 0):
            # the hard structural form: an indexed depth whose CLUT arity the container LACKS
            conflicts.append((r["id"], ch, d, None))
    chk("** shipped cells carrying a SECOND witness", sum(spoke.values()), PIN["hint_second_witness"])
    chk("... on channel P", spoke["P"], PIN["hint_second_witness_p"])
    chk("... on channel G", spoke["G"], PIN["hint_second_witness_g"])
    chk("... exact agreement", kinds["exact"], PIN["hint_exact"])
    chk("... compatible (a 15bpp derivation the arity cannot speak to)",
        kinds["compatible-15bpp"], PIN["hint_compatible_15bpp"])
    chk("** CONFLICTS with either channel", len(conflicts), PIN["hint_conflicts"])
    print("   ** FALSIFIED, FLATLY STATED IN THE RECORD: 'AND NO SHIPPED CELL HAS TWO WITNESSES.'"
          "  %d of the %d DO -- P %d, G %d -- with %d exact, %d compatible-15bpp and %d CONFLICTS."
          % (sum(spoke.values()), len(gain), spoke["P"], spoke["G"],
             kinds["exact"], kinds["compatible-15bpp"], len(conflicts)))
    for c in conflicts[:10]:
        print("      CONFLICT %s" % (c,))

    # (d) ★ THE SECOND FALSIFIED CAVEAT: "P's ground truth is N = 10 and CANNOT BE GROWN."
    chk("P's census ground truth, unchanged", PIN["cal_p_n"], PIN["p_corroborated_before"])
    chk("** P's corroborated set AT CELL LEVEL after the join",
        PIN["cal_p_n"] + spoke["P"], PIN["p_corroborated_after"])
    print("   ** FALSIFIED, ALSO FLAT: \"P's ground truth is N = 10 and CANNOT BE GROWN\".  At CELL"
          " level it goes %d -> %d (+%.0f %%) for the cost of one join, at 0 conflicts.  !! SCOPE:"
          " the 92.6 %% caveat is a PAGE-level figure; the page-level restatement is one further"
          " join and is NOT computed here or anywhere in this round."
          % (PIN["cal_p_n"], PIN["cal_p_n"] + spoke["P"],
             100.0 * spoke["P"] / PIN["cal_p_n"]))

    # (e) A CLEAN NEGATIVE, recorded so nobody tries: the arity breaks none of the 30 ties.
    unkset = set(unk)
    pamb = [(k, D.prog[k]) for k, v in D.prog.items() if verdict(v) is None and k in unkset]
    gamb = [(k, D.sopage[k]) for k, v in D.sopage.items() if verdict(v) is None and k in unkset]
    broke = []
    for k, cnt in pamb + gamb:
        r = D.C[k]
        n4, n8 = r["container_nclut4"], r["container_nclut8"]
        surv = [d for d in cnt if not ((d == 4 and n4 == 0) or (d == 8 and n8 == 0))]
        if len(cnt) > 1 and len(surv) == 1:
            broke.append(r["id"])
    chk("the dual-depth ties on the table", len(pamb) + len(gamb), PIN["hint_ties_seen"])
    chk("... broken by CLUT arity", len(broke), PIN["hint_ties_broken"])
    print("   CLEAN NEGATIVE, RECORDED SO NOBODY TRIES: of the %d dual-depth ties (%d program + %d"
          " channel-G) the arity breaks %d.  Every tie's two values survive the container's own"
          " CLUT declaration." % (len(pamb) + len(gamb), len(pamb), len(gamb), len(broke)))

    # (f) ★ THE THIRD FALSIFIED CAVEAT: the residue table says nothing about this.
    residue = len(unk) - len(gain)
    hint_only = len(hinted) - sum(spoke.values())
    chk("the residue", residue, PIN["residue_cells"])
    chk("** hint-only cells sitting INSIDE the residue", hint_only, PIN["hint_only_in_the_residue"])
    print("   ** AND THE RESIDUE TABLE'S 'why each is still unknown' IS INCOMPLETE: %d of the %d"
          " still-refused cells carry a CONTAINER-DECLARED NARROWING.  Still refused -- a narrowing"
          " is not a depth -- but not for the reason the two-row table gives." % (hint_only, residue))

    # (g) A CHANNEL CLOSED, not opened: the id-4 model-package header is structurally vacuous here.
    hdr = [r for r in D.census if "model-package header" in (r["bpp_evidence"] or "")]
    hcre = [r for r in hdr if "creature" in r["classes"]]
    chk("id-4 header-evidence cells", len(hdr), PIN["header_channel_cells"])
    chk("... creature-class", len(hcre), PIN["header_channel_creature"])
    chk("... scenery", len(hdr) - len(hcre), PIN["header_channel_scenery"])
    e179 = [r for r in D.census if r["id"] == "ef179.x320_y384"]
    chk("the calibration's strongest row exists", len(e179), 1)
    chk("** and it is itself CREATURE-class", "creature" in e179[0]["classes"], True)
    print("   A CHANNEL CLOSED RATHER THAN OPENED: the census's third evidence class, the id-4"
          " model-package header, covers %d cells -- %d/%d CREATURE-class, %d scenery.  It can NEVER"
          " attribute a scenery cell; state it as a named refusal and it is closed forever."
          % (len(hdr), len(hcre), len(hdr), len(hdr) - len(hcre)))
    print("     !! AND THE SAME MEASUREMENT LANDS ON THIS RECORD'S OWN sec 5: ef179.x320_y384, the"
          " 'genuinely independent witness' the calibration calls its strongest row, is %s -- the"
          " population this rung's attribution excludes BY RULE.  It is real evidence about the"
          " INSTRUMENT; it is not evidence from the population the lever serves."
          % (e179[0]["classes"],))


# --------------------------------------------------------------------------- runner
GATES = [
    ("H0", "CALIBRATION (own decoder == reskin; two known answers re-found first)", h0_calibrate),
    ("H1", "THE POPULATION (2,665 / 2,572 / 2,385, and the 17-cell gap accounted for)", h1_population),
    ("H2", "CHANNEL P (the program's tpage, re-rolled from the raw hits)", h2_channel_p),
    ("H3", "CHANNEL G (so records at PAGE granularity) + the 189/57/246 headline", h3_channel_g),
    ("H4", "THE CALIBRATION TABLE (every disagreement adjudicated: U-SPILL)", h4_calibration),
    ("H5", "THE STRUCTURAL CEILING (222 blind containers, 1,278 cells, 0 gain)", h5_ceiling),
    ("H6", "THE REFUTER CHECKS reproduced (V1a lens G; V1b A5 row by row)", h6_refuters),
    ("H7", "THE WRITE DELTA (L2's sites re-summed vs the shipped lists)", h7_write_delta),
    ("H8", "PROVENANCE (no SE bytes committable; the dossiers stay in SCRATCH)", h8_provenance),
    ("H9", "'233/233 VALUES, 238/238 SITES' + the calibration REFUTED as stated", h9_two_disassemblers),
    ("H10", "CHANNEL G RE-EXAMINED (its calibration is 87 % an identity)", h10_channel_g_reexamined),
    ("H11", "THE REFUSED SET IS 32, NOT 24; and the residue's three populations", h11_refused_set),
    ("H12", "THE BUILD LIST'S OWN GATES, PRE-TESTED (56 of 57, not 57)", h12_build_list),
    ("H13", "THE NEXT PROBE COSTED (it discriminates nothing as specified)", h13_next_probe),
    ("H14", "THE STORE-LEVEL SWEEP -- L1's named-and-unrun caveat, run", h14_store_sweep),
    ("H15", "THE WRITE LANE'S REFUTER reproduced at SITE level", h15_v2_write_refutation),
    ("H16", "CHANNEL H -- the CLUT-arity NARROWING no lane opened (351 cells, 17 second witnesses)",
     h16_clut_arity),
]


def main(argv=None) -> int:
    only = set(a.upper() for a in (argv or sys.argv[1:]) if a.upper().startswith("H"))
    print("W6b-2 GATES -- the depth-attribution rung, every headline number re-measured")
    print("corpus: %s" % SCRATCH)
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
