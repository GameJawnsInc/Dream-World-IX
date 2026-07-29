r"""TIER W rung W6b-3 INTEGRATION -- THE GATE RUNNER FOR THE KIT SIDE.  `py w6b3i_gates.py` -> I0..I11.

`w6b3_gates.py` is the RECON's gate runner: it re-measures the DELTA between what the kit could read
and what the container states, and W6b-3i is the rung that closes that delta.  **This file is the
other half**: the integration design's build list turned into shipped kit behaviour, one gate per
row, **every gate driven through THE CODE THAT SHIPS** rather than through a private re-derivation,
and nothing imported from a sibling gate's ``PIN`` -- two files measuring the same thing
independently is the point, and a shared constant would make the agreement a tautology.

    design sec 2    `so_record` -- THE READER FIX, and the P = 0 invariant                    I0 I1
    design sec 4    THE SAFETY FIX: the verdict census, the dedupe law, coverage's scope      I2 I3
    design sec 5    THE CONTAINMENT -- the census and CHANNEL G narrowed, A/B                 I4
    design sec 6    CHANNEL A (`so-array`) DISCLOSES: its reach, its keys, its ack ladder     I5 I7
    design sec 7    the two refusals, DERIVED not enumerated, and their addressability        I6
    design sec 8    CLASS C for the 34, at the DEPTH's own granularity                        I5
    design sec 9    the census artifact FROZEN -- and the freeze VERIFIED                     I10
    addendum A5     every new count constant RE-DERIVATION-PINNED                             I9
    design sec 2.4  THE ORDER CLAUSE IS NOT SHIPPED -- structurally, and by permutation       I8 I8b
                    provenance: no stock byte in anything this round commits                  I11

★ THE LINE THIS RUNG IMPLEMENTS, and every gate below is a form of it:

    THE READER FIX IS UNCONDITIONAL.  THE DEPTH DISCLOSES AT CHANNEL P's TIER.

★ AND THE MECHANISM THAT MAKES IT SAFE, which is why I0 runs FIRST and I4 is the longest gate here:

    ★ THE WITNESS PARTITION.  A record with P <= 1 is an INCUMBENT witness; a record with P >= 2 is
    NOVEL, and ALL of its slots are novel together (the old reader returned None for the whole
    record).  Filtering the FIXED reader to the incumbent class reproduces the pre-W6b-3 binding
    population EXACTLY -- so "the census and CHANNEL G do not move" is a statement about the INPUT,
    not a claim about the output, and I0 proves it before any other gate spends it.

★ AND THE TWO OWNER-RATIFIED POSTURE CALLS THIS BOARD PINS (addendum A1 / A2), because a gate that
did not name them would read green about a kit that shipped something else:

    A1  THE 122-PALETTE RELEASE DOES NOT SHIP.  `complete` is HONEST (the denominator is the bytes'),
        but where completeness DEPENDS on novel records the verdict is
        `UNBOUND at COMPLETE so-coverage (NOVEL-DEPENDENT)` with `shared = True`: the guard stays
        ARMED.  I2 pins the guarded split 301 / 122 with 0 released BY THE COVERAGE FLIP -- and,
        beside it, the WHOLE `_gate_shared` obligation delta (46 released / 5 armed), because the
        unconditional safety fix moves palettes off `shared` too and an unqualified zero would have
        read as a claim about the gate.
    A2  ALL 12 ARRAY-DUAL CELLS REFUSE OUTRIGHT on any path that consults `so-array`, including the
        4 whose columns another channel already serves -- CHANNEL A holds VETO power, never emission
        power.  I6 pins the licensed-path addressability at -6 and prints the refused -2 alternative.

Reads the extracted corpus at C:\gd\SCRATCH\summon-format and the lane artifacts under texel-w6b\
ONLY.  No install read, NO deploy, no install write, no git commit, and it writes nothing but its own
stdout.  Budget: ~3 rasterising passes over the corpus (the same order as `w6b2i_gates`), plus three
SCOPED partial passes over the containers CHANNEL A / the multi-part records live in -- never a
fourth full walk.  ~7 min end to end on this machine.
"""
from __future__ import annotations

import ast
import glob
import hashlib
import json
import os
import random
import re
import struct
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                              # noqa: E402  (sets up sys.path)
import summon_camera as W                                        # noqa: E402
from ff9mapkit.summons import container as EC                    # noqa: E402
from ff9mapkit.summons import depth_attribution as DA            # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402

CORPUS = W.SCRATCH_CORPUS
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
SCRATCH = os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format")
W6B = os.path.join(SCRATCH, "texel-w6b")

#: THE GRANULARITY STATEMENT, in this file's own arithmetic rather than by import: a VRAM tpage names
#: a 64 x 256 PAGE, a census page-cell is 64 x 128, so one page word covers a COLUMN of two cells.
PAGE_HW, PAGE_LINES, CELL_LINES = 64, 256, 128

#: the W6b-2 CHANNEL SCOPE -- `LICENSED_CHANNELS` as it stood before CHANNEL A joined it.  Used as a
#: SECOND SCOPE (never as a replacement) wherever a W6b-2 constant describes a surface that A2's
#: uniform refusal has since moved: two scopes, both printed, neither reconciled.  The precedent is
#: `w6b2i_gates` I1.
W6B2_CHANNELS = tuple(c for c in RP.LICENSED_CHANNELS if c != "so-array")

# --------------------------------------------------------------------------- THE PINS
#: Every number this rung's kit side is allowed to assert.  Each is RE-MEASURED below and compared
#: here.  Where a number also lives in `w6b3_gates.PIN` or `w6b2i_gates.PIN` it is deliberately NOT
#: imported.
PIN = {
    "containers": 372,
    # -- I0 THE WITNESS PARTITION (the pre-W6b-3 population, reproduced by the FIXED reader)
    "legacy_records": 376,
    "legacy_tpage_bearing": 340,
    "incumbent_bindings_direct": 340,
    "incumbent_bindings_nodirect": 316,
    "containers_differing": 0,
    "ef211_p2_records": 0,
    # -- I1 THE READER
    "records": 502,
    "slots": 649,
    "novel_records": 126,
    "novel_slots": 309,
    "p_hist": {0: 36, 1: 340, 2: 98, 3: 12, 4: 6, 5: 8, 6: 1, 7: 1},
    "p0_records": 36,
    "max_p": 7,
    "arrayb_informative": 126,
    "tpage_bearing": 466,
    "textured": 465,
    "compat_view_agrees": 340,
    # -- I2 THE SAFETY FIX (A1's guarded split)
    "before_private": 107, "before_shared": 87, "before_unknown": 2600, "before_unbound": 301,
    "n_private": 148, "n_shared": 129, "n_unknown": 2395,
    "n_unbound_complete": 301,
    "n_unbound_complete_novel_guarded": 122,
    "n_released": 0,
    "palettes_total": 3095,
    "false_private_now": 0, "false_private_before": 5,
    "unknown_gains": 83,
    "gain_split_geom": (46, 37),
    "gain_split_slot": (43, 40),
    "complete_flips": 19,
    #: ★ THE `_gate_shared` OBLIGATION DELTA -- measured on `Palette.shared`, the field that gate
    #: reads, in BOTH directions.  `n_released` above is A1's COMPLETENESS branch alone and is 0;
    #: this is the whole obligation surface, and the release here is the SAFETY FIX's own direction
    #: (a palette that gains a NAMED single binder is PRIVATE, which is the repair, not a loosening
    #: by omission).  Named because "0 palettes are released" is true of one branch and would read as
    #: a claim about the gate.  ★ AND THE ARMED DIRECTION IS THE STRONGEST FORM THE NUMBER COULD
    #: TAKE: it is EXACTLY the five historical FALSE PRIVATE palettes, so the fix arms the guard on
    #: precisely the palettes that were being edited against a verdict the container contradicts.
    "guard_released": 46, "guard_armed": 5,
    "self_shared_verdict": 3, "self_shared_count_only": 2,
    "one_geom_two_depths": 0,
    #: A7.m3.  MEASURED HERE THROUGH THE SHIPPED `preview_source`, not carried: the design's
    #: handoff quoted 30 / 4.  The VANISHING set turns out to be EXACTLY the five historical FALSE
    #: PRIVATE palettes -- which is the strongest form the number could take, so it is asserted as an
    #: identity rather than as a count.
    #:
    #: ⚠ **TWO SCOPES, BOTH PINNED, THE DIFFERENCE DERIVED.**  The first pair is every non-creature
    #: palette whose `preview_source` answer moved; the second is the subset `render_previews`
    #: actually DRAWS (it filters `pal.entries != 256`).  `ff9mapkit/tests/test_summon_reskin.py`
    #: pins the DRAWN pair, and a board and a test quoting different numbers under one noun is the
    #: thing this split exists to stop.
    "previews_appearing": 43, "previews_vanishing": 5,
    "previews_appearing_drawn": 30, "previews_vanishing_drawn": 4,
    "previews_not_drawn": (13, 1),
    # -- I3 THE FLAGSHIP
    "ef381_binders": 7, "ef381_models": 7, "ef381_novel": 6,
    # -- I4 THE CONTAINMENT
    "so_uv_cells": 187,
    "depth_unknown_census": 2385,
    "scenery_cells": 2572,
    "gain_so_page": 57,
    "g_dual": 8,
    "pdv_legacy_mismatch": 0,
    "bound_models_mismatch": 0,
    # ...and the COUNTERFACTUAL: what the NAIVE widening would have done.  BOTH GRANULARITIES ARE
    # PINNED and neither is reconciled: the design measured the PAGE-ORIGIN form (122 -> 162 etc.)
    # and left the CELL form as an [M] for this board.  A page word governs a COLUMN of two cells,
    # so an origin count and a cell count are not the same predicate -- printing one under the
    # other's name is exactly how a granularity error becomes a pin.
    # AND THE ORIGIN FORM HAS TWO SCOPES, for the same reason `w6b2i_gates` I1 does: the design's
    # [V] figures are the RECORD's scope (every CENSUS cell, creature pages included) while the
    # SHIPPED `page_depth_view` names only cells `page_cells` declares.  Both are pinned and the
    # difference is asserted to be exactly the creature-class rows this rung excludes BY RULE.
    "cf_origins_incumbent": 122, "cf_origins_all": 162,
    "cf_origin_single_incumbent": 108, "cf_origin_single_all": 141,
    "cf_origin_dual_incumbent": 14, "cf_origin_dual_all": 21,
    "cf_kit_origins_incumbent": 121, "cf_kit_origins_all": 159,
    "cf_kit_origin_single_incumbent": 107, "cf_kit_origin_single_all": 138,
    "cf_cells_incumbent": 226, "cf_cells_all": 299,
    "cf_single_incumbent": 198, "cf_single_all": 257,
    "cf_dual_incumbent": 28, "cf_dual_all": 42,
    "cf_flip_single_to_dual": 6,
    "cf_flip_origins": 3,
    # -- I5 CHANNEL A's REACH
    "gain_array": 65,
    "array_in_reach_dual": 8,
    "reach_strict": 73,
    "array_class_c": 34,
    "array_clean": 26,
    "array_program_write": 7,
    "array_deflation_overlap": 2,
    "array_readerless": 65,
    "census_multi_palette_vacuous": 0,
    "class_c_keyset_equal": 65,
    # -- I6 THE REFUSALS
    "array_dual_cells": 12,
    "array_dual_columns": 6,
    "array_vs_column_cells": 2,
    "array_vs_column_columns": 1,
    "hazard_pairs_checked": 6,
    "hazard_pairwise_overlap": 0,
    "addressability_delta_licensed": -6,
    "addressability_delta_census": 0,
    "addressability_delta_refused_alternative": -2,
    "program_dual_cells": 22,
    "spill_cells": 2,
    # -- I8 the order clause
    "order_subscripts": 0,
    # -- I8b permutation invariance
    "perm_display_pick_differs": 0,
    "perm_verdict_differs": 0,
    "perm_depth_differs": 0,
    "perm_class_differs": 0,
    # -- I9 the re-derivation pins, under BOTH scopes
    "w6b2_scope_so_page": 57,
    "w6b2_scope_g_dual": 8,
    "w6b2_scope_depth_unknown": 2298,
    "w6b2_scope_gained": 246,
    "shipped_so_page": 55,
    "shipped_so_uv": 183,
    "shipped_depth_unknown": 2290,
    "shipped_gained": 244,
    "stale_string_delta": 8,
    # -- I10 the census freeze
    "census_rows": 2665,
    "census_reader_rows": 187,
    "census_n_readers": 449,
    "census_so_binding_rows": 187,
    "census_freeze_mismatch": 0,
    # -- I11 provenance
    "stockish_files": 0,
    "unadjudicated_leaks": 0,
}

_FAILS: List[str] = []


def chk(name: str, got, want) -> None:
    """Compare a re-measured value against its pin; COLLECT rather than raise, so the whole board
    prints and one red gate cannot hide the state of the others."""
    ok = (abs(got - want) < 5e-3) if isinstance(want, float) else (got == want)
    if not ok:
        _FAILS.append("%s: measured %r, pinned %r" % (name, got, want))


# --------------------------------------------------------------------------- shared derivations
def u16(b: bytes, o: int) -> int:
    return struct.unpack_from("<H", b, o)[0] if 0 <= o <= len(b) - 2 else -1


def dec(tp: int) -> Tuple[int, int, int]:
    """(page_x, page_y, bpp) from a nine-bit PSX tpage word -- written from the bit layout HERE, so
    the re-derivation pins do not lean on the same decoder the kit does."""
    return (tp & 0x0F) * PAGE_HW, ((tp >> 4) & 1) * PAGE_LINES, RS.SO_BPP[(tp >> 7) & 3]


def cover(px: int, py: int) -> List[Tuple[int, int]]:
    """THE GRANULARITY STATEMENT, in code: a page covers both stacked 128-line cells of its column."""
    return [(px, py), (px, py + CELL_LINES)]


SO_MAGIC = 0x6F73


def _LEGACY_SO_RECORD(blob: bytes, geom_base: int) -> Optional[dict]:
    """★ **THE HISTORICAL INSTRUMENT, FROZEN IN THIS FILE.**

    A byte-for-byte copy of ``reskin.so_record``'s PRE-W6b-3 body -- the kit's own retired code,
    ~8 lines, no Square-Enix bytes.  W6b-3i's whole subject is that the SHIPPED reader is now RIGHT,
    which makes every "and it did not move" claim a comparison against a population that no longer
    exists anywhere in the kit.  Re-deriving that population from the CURRENT reader would be a
    self-comparison wearing a calibration's clothes, so the retired decoder is kept here and I0
    compares the two.

    (`w6b3_gates.py` freezes the same body for its own reasons.  It is NOT imported: two files
    holding the historical instrument independently is what makes their agreement evidence.)
    """
    for rec_len in (0x10, 0x08):
        o = geom_base - rec_len
        if o >= 0 and u16(blob, o) == SO_MAGIC and u16(blob, o + 4) == rec_len:
            rec = {"at": o, "len": rec_len, "textured": u16(blob, o + 2)}
            if rec_len == 0x10:
                rec["tpage"] = u16(blob, o + 8)
                rec["clut"] = u16(blob, o + 0x0A)
            return rec
    return None


def _geom_bases(blob: bytes) -> List:
    """Every NON-CREATURE GEOM block, the population :func:`reskin.attribution` walks."""
    mp = EC.creature_package(blob)
    cg = mp.geom_offset if mp is not None else None
    return [g for g in EC.scan_geom(blob) if cg is None or g.base != cg]


def _owner_slots(blob: bytes):
    """The chunk-slot join, re-implemented HERE so I0's tuple comparison is genuinely independent of
    `attribution`'s own copy of it."""
    c = EC.parse_header(blob, strict=False)
    owners = []
    for ch in c.chunks:
        for r in ch.resources:
            n = r.nbytes + ((r.extra_sectors or 0) << 11)
            owners.append((r.offset, r.offset + n, ch.slot))

    def slot_of(off: int) -> int:
        for lo, hi, s in owners:
            if lo <= off < hi:
                return s
        return -1
    return slot_of


def _legacy_bindings(blob: bytes, include_direct: bool) -> List[tuple]:
    """★ THE PRE-W6b-3 BINDING POPULATION, rolled INDEPENDENTLY in this file.

    `attribution`'s slot logic re-written against `_LEGACY_SO_RECORD`: one pair per record, 15bpp
    direct binders admitted only under ``include_direct``, an indexed slot naming no CLUT word
    dropped.  Returns the tuple I0 compares against the SHIPPED reader narrowed to INCUMBENT --
    ``(geom, tpage, clut_word, bpp, entries, cell, chunk_slot)``, the full identity the design's
    partition claim is stated over.
    """
    slot_of = _owner_slots(blob)
    out: List[tuple] = []
    for g in _geom_bases(blob):
        rec = _LEGACY_SO_RECORD(blob, g.base)
        if rec is None or "tpage" not in rec:
            continue
        tp, cw = rec["tpage"], rec["clut"]
        bpp = RS.SO_BPP[(tp >> 7) & 3]
        if bpp == 15:
            if not include_direct:
                continue
            out.append((g.base, tp, cw or 0, 15, 0, RS.NO_CLUT_CELL, slot_of(g.base)))
            continue
        if not cw:
            continue
        out.append((g.base, tp, cw, bpp, 16 if bpp == 4 else 256, RS.clut_word_xy(cw),
                    slot_of(g.base)))
    return out


def _tuples(bindings) -> List[tuple]:
    """The SHIPPED `Binding` rendered into the same identity tuple, so the comparison is over values
    rather than over object identity."""
    return [(b.geom, b.tpage, b.clut_word, b.bpp, b.entries, b.cell, b.chunk_slot)
            for b in bindings]


def _load(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _blob(ef: int) -> bytes:
    with open(os.path.join(SCRATCH, "ef%03d.bytes" % ef), "rb") as fh:
        return fh.read()


# --------------------------------------------------------------------------- ONE CORPUS WALK
class Data:
    """ONE corpus pass, driven through the SHIPPED derivations.

    THE BUDGET, stated because the design set one: three RASTERISING passes over the 372 containers
    (`scenery_surface` at CENSUS scope, `scenery_surface` at the SHIPPED LICENSED scope, and one
    `bound_models` whose result is handed to `cell_readers` rather than recomputed), plus two SCOPED
    partial passes over ONLY the containers CHANNEL A names a cell in -- the W6b-2 channel scope and
    the ACK surface.  Elsewhere those two are identical to the licensed pass BY CONSTRUCTION, because
    `scenery_surface` gates `array_depth_view` on ``"so-array" in channels`` (design A3), and that
    identity is asserted rather than assumed (I4).
    """

    def __init__(self) -> None:
        self.census = _load(os.path.join(W6B, "census", "pages.json"))
        self.C = {(r["ef"], r["vram_x"], r["vram_y"]): r for r in self.census}
        self.paths = sorted(p for p in glob.glob(os.path.join(SCRATCH, "ef*.bytes"))
                            if len(os.path.basename(p)) == 11)
        # ---- the RECORD population (I0/I1)
        self.recs: List[dict] = []                 # one row per ACCEPTED shipped record
        self.legacy_rec_n = 0
        self.legacy_tpage_n = 0
        self.compat_ok = 0
        self.compat_bad: List[tuple] = []
        self.p2_efs: set = set()                   # containers holding >= 1 P >= 2 record
        self.geom_with_so: Dict[int, Tuple[int, int, int]] = {}   # ef -> (total, with_so, novel)
        # ---- the BINDING population (I0)
        self.part_bad: List[int] = []
        self.off_n = self.on_n = self.direct_n = 0
        self.inc_on = self.inc_off = 0
        self.effects_with_direct: set = set()
        # ---- CHANNEL G / CHANNEL A views (I4/I5/I9)
        self.gview: Dict[Tuple[int, int, int], Tuple[int, ...]] = {}
        self.gbind: Dict[Tuple[int, int, int], tuple] = {}
        self.gview_legacy: Dict[Tuple[int, int, int], Tuple[int, ...]] = {}
        self.aview: Dict[Tuple[int, int, int], Tuple[int, ...]] = {}
        self.abind: Dict[Tuple[int, int, int], tuple] = {}
        self.cf_all: Dict[Tuple[int, int, int], Tuple[int, ...]] = {}   # the NAIVE widening
        #: the SAME two rolls at PAGE-ORIGIN granularity with **NO declared-cell filter** -- every
        #: origin any `so` binding names.  This is the scope the design's page-origin [V] figures
        #: were taken at, kept BESIDE the shipped view's rather than instead of it: the shipped
        #: `page_depth_view` drops an origin the container never uploads, on the rule it states in
        #: its own docstring (*a recovered column the container never uploads is evidence about
        #: somebody else's page and attributes NOTHING here*).  Reconciling the two would hide that
        #: rule; printing both is what makes it visible.
        self.graw: Dict[Tuple[int, int, int], set] = defaultdict(set)
        self.cf_raw: Dict[Tuple[int, int, int], set] = defaultdict(set)
        #: the origins in `graw`/`cf_raw` the container declares NO cell for -- the difference.
        self.undeclared_origins: set = set()
        # ---- the SURFACES
        self.cells: set = set()
        self.census_pages: set = set()
        self.census_dark: set = set()
        self.census_klasses: set = set()
        self.census_hz_multi: set = set()
        self.pages: Dict[Tuple[int, int, int], RP.TexelPage] = {}
        self.refusals: Dict[Tuple[int, int, int], set] = defaultdict(set)
        self.reasons: Dict[Tuple[int, int, int], Dict[str, str]] = defaultdict(dict)
        #: the page-cell NAME a refusal carries -- the string a spec row has to write, so I7's
        #: vehicles are named by the shipped derivation rather than by this file guessing a slot.
        self.ref_names: Dict[Tuple[int, int, int], str] = {}
        #: the W6b-2 CHANNEL SCOPE, on the CHANNEL-A containers only (see the class docstring)
        self.w2_pages: Dict[Tuple[int, int, int], RP.TexelPage] = {}
        self.w2_refusals: Dict[Tuple[int, int, int], set] = defaultdict(set)
        self.w2_efs: set = set()
        self.w2_gained = self.w2_dark = self.w2_sopage = self.w2_souv = self.w2_gdual = 0
        #: the ACK surface -- `array_depth=True`, i.e. what an author who said the key actually gets
        self.ack_pages: Dict[Tuple[int, int, int], RP.TexelPage] = {}
        self.ack_refusals: Dict[Tuple[int, int, int], set] = defaultdict(set)
        self.ack_disclosures: Dict[Tuple[int, int, int], str] = {}
        # ---- the READER population, for the census freeze (I10)
        self.readers: Dict[Tuple[int, int, int], List[int]] = {}
        self.model_fields: Dict[int, Dict[int, tuple]] = {}
        # ---- the PALETTE verdicts (I2/I3)
        self.verdicts: Counter = Counter()
        self.false_priv_now: List[str] = []
        self.false_priv_before: List[str] = []
        self.gains = 0
        self.split_geom = {"priv": 0, "shared": 0}
        self.split_slot = {"priv": 0, "shared": 0}
        self.flips: List[int] = []
        self.self_shared: List[str] = []
        self.count_only: List[str] = []
        self.one_geom_two_depths: List[str] = []
        self.guarded_shared_ok = 0
        self.guarded_n = 0
        #: ★ THE `_gate_shared` OBLIGATION DELTA, measured on the flag that gate actually reads.
        #: "0 palettes are released" is true of A1's COMPLETENESS branch and of nothing else -- the
        #: unconditional SAFETY FIX also moves palettes off `shared = True` by giving them a NAMED
        #: PRIVATE binder, which is design-sanctioned (A1: "the 83 still gain named binders") but was
        #: measured by no pin.  A count that does not match its own noun is the defect this rung
        #: exists to repair, so both directions are counted here and named separately.
        self.guard_released: List[str] = []
        self.guard_armed: List[str] = []
        self.prev_appear: List[str] = []
        self.prev_vanish: List[str] = []
        #: ...and the SAME two populations at the scope `render_previews` actually DRAWS at.  It
        #: filters `pal.entries != 256`, so a 16-entry palette can change binder count without any
        #: picture appearing or disappearing anywhere.  TWO SCOPES, BOTH PINNED, the difference
        #: derived -- the `w6b2i_gates` I1 precedent, and the reason the kit test and this board
        #: quote different numbers for the same-sounding noun.
        self.prev_appear_drawn: List[str] = []
        self.prev_vanish_drawn: List[str] = []
        self.prev_reasons: Dict[str, str] = {}
        self.flagship: Optional[tuple] = None
        self._walk()

    # -- the walk ------------------------------------------------------------
    def _walk(self) -> None:
        for p in self.paths:
            ef = int(os.path.basename(p)[2:5])
            with open(p, "rb") as fh:
                blob = fh.read()
            self._records(ef, blob)
            self._bindings(ef, blob)
            self._views(ef, blob)
            self._surfaces(ef, blob)
            self._palettes(ef, blob)

    def _records(self, ef: int, blob: bytes) -> None:
        for g in _geom_bases(blob):
            rec = RS.so_record(blob, g.base)
            old = _LEGACY_SO_RECORD(blob, g.base)
            if old is not None:
                self.legacy_rec_n += 1
                if "tpage" in old:
                    self.legacy_tpage_n += 1
            if rec is None:
                continue
            self.recs.append({"ef": ef, "geom": g.base, "at": rec["at"], "len": rec["len"],
                              "nparts": rec["nparts"], "witness": rec["witness"],
                              "textured": rec["textured"], "parts": tuple(rec["parts"]),
                              "arrayB": u16(blob, rec["at"] + 6)})
            if rec["nparts"] >= 2:
                self.p2_efs.add(ef)
            # ★ THE COMPATIBILITY VIEW: entry 0 must still be the LEGACY answer, on all 340.
            if old is not None and "tpage" in old:
                if rec.get("tpage") == old["tpage"] and rec.get("clut") == old["clut"] \
                        and rec["at"] == old["at"]:
                    self.compat_ok += 1
                else:
                    self.compat_bad.append((ef, g.base))

    def _bindings(self, ef: int, blob: bytes) -> None:
        a_off = RS.attribution(blob)
        a_on = RS.attribution(blob, include_direct=True)
        a_inc_on = RS.attribution(blob, include_direct=True, witness=RS.WITNESS_INCUMBENT)
        a_inc_off = RS.attribution(blob, witness=RS.WITNESS_INCUMBENT)
        self.off_n += len(a_off.bindings)
        self.on_n += len(a_on.bindings)
        self.direct_n += len(a_on.direct)
        self.inc_on += len(a_inc_on.bindings)
        self.inc_off += len(a_inc_off.bindings)
        if a_on.direct:
            self.effects_with_direct.add(ef)
        self.geom_with_so[ef] = (a_on.geom_total, a_on.geom_with_so, a_on.geom_with_so_novel)
        # ★ THE PARTITION, tuple for tuple, against THIS FILE's frozen legacy roll.
        if sorted(_tuples(a_inc_on.bindings)) != sorted(_legacy_bindings(blob, True)) \
                or sorted(_tuples(a_inc_off.bindings)) != sorted(_legacy_bindings(blob, False)):
            self.part_bad.append(ef)

    def _views(self, ef: int, blob: bytes) -> None:
        for cell, pd in RS.page_depth_view(blob).items():
            self.gview[(ef, cell[0], cell[1])] = pd.depths
            b = pd.binding
            self.gbind[(ef, cell[0], cell[1])] = (b.geom, b.tpage, b.clut_word) if b else ()
        for cell, pd in RS.array_depth_view(blob).items():
            self.aview[(ef, cell[0], cell[1])] = pd.depths
            b = pd.binding
            self.abind[(ef, cell[0], cell[1])] = (b.geom, b.tpage, b.clut_word) if b else ()
        # THE COUNTERFACTUAL: the NAIVE widening -- channel G asked for the TRUE population.
        for cell, pd in RS.page_depth_view(blob, witness=RS.WITNESS_ALL).items():
            self.cf_all[(ef, cell[0], cell[1])] = pd.depths
        # ...and an INDEPENDENT incumbent roll off the FROZEN legacy reader, for I4's identity.
        declared = {pc.cell for pc in RS.page_cells(blob).values()}
        rolled: Dict[Tuple[int, int], set] = defaultdict(set)
        for (_g, tp, _cw, bpp, _e, _c, _s) in _legacy_bindings(blob, True):
            px, py, _b = dec(tp)
            for c in cover(px, py):
                if c in declared:
                    rolled[c].add(bpp)
        for c, ds in rolled.items():
            self.gview_legacy[(ef, c[0], c[1])] = tuple(sorted(ds))
        # ...and the SAME rolls at PAGE-ORIGIN granularity with NO declared-cell filter.
        for witness, sink in ((RS.WITNESS_INCUMBENT, self.graw), (RS.WITNESS_ALL, self.cf_raw)):
            for b in RS.attribution(blob, include_direct=True, witness=witness).bindings:
                px, py, _bpp = dec(b.tpage)
                sink[(ef, px, py)].add(b.bpp)
                if not any(c in declared for c in cover(px, py)):
                    self.undeclared_origins.add((ef, px, py))

    def _surfaces(self, ef: int, blob: bytes) -> None:
        for pc in RS.page_cells(blob).values():
            self.cells.add((ef, pc.cell[0], pc.cell[1]))
        cp, cr = RP.scenery_surface(blob, ef)                       # CENSUS scope
        self.census_pages |= {(ef, p.cell[0], p.cell[1]) for p in cp}
        self.census_dark |= {(ef, r.cell[0], r.cell[1]) for r in cr if r.klass == "depth-unknown"}
        self.census_klasses.update(r.klass for r in cr)
        for pg in cp:
            if pg.hazards is not None and pg.hazards.multi_palette:
                self.census_hz_multi.add((ef, pg.cell[0], pg.cell[1]))
        pages, refused = RP.scenery_surface(blob, ef, channels=RP.LICENSED_CHANNELS)
        for pg in pages:
            self.pages[(ef, pg.cell[0], pg.cell[1])] = pg
        for r in refused:
            k = (ef, r.cell[0], r.cell[1])
            self.refusals[k].add(r.klass)
            self.reasons[k][r.klass] = r.reason
            self.ref_names[k] = r.name
        # THE TWO SCOPED PARTIAL PASSES -- only where CHANNEL A names a cell.
        if any(k[0] == ef for k in self.aview):
            self.w2_efs.add(ef)
            w2p, w2r = RP.scenery_surface(blob, ef, channels=W6B2_CHANNELS)
            for pg in w2p:
                self.w2_pages[(ef, pg.cell[0], pg.cell[1])] = pg
            for r in w2r:
                self.w2_refusals[(ef, r.cell[0], r.cell[1])].add(r.klass)
            ap, ar = RP.scenery_surface(blob, ef, channels=RP.LICENSED_CHANNELS, array_depth=True)
            for pg in ap:
                k = (ef, pg.cell[0], pg.cell[1])
                self.ack_pages[k] = pg
                if pg.depth_source == "so-array":
                    t = RP.TexelTarget(name=pg.name, enabled=False, source="", page=pg,
                                       ack_array_depth=True)
                    self.ack_disclosures[k] = "  ".join(RP._scenery_disclosures(t))
            for r in ar:
                self.ack_refusals[(ef, r.cell[0], r.cell[1])].add(r.klass)
        # THE READER POPULATION -- ONE `bound_models`, handed to `cell_readers` rather than recomputed
        models = RP.bound_models(blob)
        self.model_fields[ef] = {m.geom: (m.tpage, m.bpp, m.clut_word, m.clut_cell,
                                          m.clut_entries, m.page) for m in models}
        for cell, ms in RP.cell_readers(blob, models).items():
            self.readers[(ef, cell[0], cell[1])] = sorted(m.geom for m in ms)

    def _palettes(self, ef: int, blob: bytes) -> None:
        a_all = RS.attribution(blob)
        a_inc = RS.attribution(blob, witness=RS.WITNESS_INCUMBENT)
        try:
            pm = RS.palette_map(blob, effect=ef, attrib=a_all)
            pm_inc = RS.palette_map(blob, effect=ef, attrib=a_inc)
        except Exception:                                                      # noqa: BLE001
            return
        if a_all.complete and not a_inc.complete:
            self.flips.append(ef)
        old = {q.name: q for q in pm_inc.palettes}
        for pal in pm.palettes:
            if pal.slot < 0:
                continue
            r = pal.shared_reason
            o = old.get(pal.name)
            b_all = a_all.binders(pal.vram, pal.entries)
            b_inc = a_inc.binders(pal.vram, pal.entries)
            models = {b.geom for b in b_all}
            if r.startswith("DERIVED PRIVATE"):
                self.verdicts["private"] += 1
                if len(models) > 1:
                    self.false_priv_now.append("ef%03d %s" % (ef, pal.name))
            elif r.startswith("DERIVED SHARED"):
                self.verdicts["shared"] += 1
            elif r.startswith("SHARED-UNKNOWN"):
                self.verdicts["unknown"] += 1
            elif r.startswith("UNBOUND at COMPLETE so-coverage (NOVEL-DEPENDENT)"):
                self.verdicts["guarded"] += 1
                self.guarded_n += 1
                if pal.shared is True:
                    self.guarded_shared_ok += 1
            elif r.startswith("UNBOUND at COMPLETE"):
                self.verdicts["unbound"] += 1
            else:
                self.verdicts["OTHER"] += 1
            # -- the PRE-FIX census, and the five FALSE PRIVATE it shipped
            if o is not None:
                # ★ the OBLIGATION delta, on `Palette.shared` -- the exact field `_gate_shared` reads.
                if o.shared and not pal.shared:
                    self.guard_released.append("ef%03d %s" % (ef, pal.name))
                elif pal.shared and not o.shared:
                    self.guard_armed.append("ef%03d %s" % (ef, pal.name))
                ro = o.shared_reason
                if ro.startswith("DERIVED PRIVATE"):
                    self.verdicts["before_private"] += 1
                    if models - {b.geom for b in b_inc}:
                        self.false_priv_before.append("ef%03d %s" % (ef, pal.name))
                elif ro.startswith("DERIVED SHARED"):
                    self.verdicts["before_shared"] += 1
                elif ro.startswith("SHARED-UNKNOWN"):
                    self.verdicts["before_unknown"] += 1
                    if b_all:
                        self.gains += 1
                        self.split_geom["shared" if len(models) > 1 else "priv"] += 1
                        self.split_slot["shared" if len(b_all) > 1 else "priv"] += 1
                elif ro.startswith("UNBOUND at COMPLETE"):
                    self.verdicts["before_unbound"] += 1
            # -- THE DEDUPE LAW's two populations
            if len(b_all) > 1 and len(models) == 1:
                self.self_shared.append("ef%03d %s" % (ef, pal.name))
            elif len(models) > 1 and len(b_all) != len(models):
                self.count_only.append("ef%03d %s (%d slots -> %d models)"
                                       % (ef, pal.name, len(b_all), len(models)))
            by_geom: Dict[int, set] = defaultdict(set)
            for b in b_all:
                by_geom[b.geom].add(b.bpp)
            if any(len(v) > 1 for v in by_geom.values()):
                self.one_geom_two_depths.append("ef%03d %s" % (ef, pal.name))
            if ef == 381 and pal.name == "pal.s0.x0_y248.e256":
                self.flagship = (len(b_all), len(models), sum(1 for b in b_all if b.novel), r,
                                 tuple(sorted((b.geom, b.record_at, b.slot) for b in b_all)))
            # -- A7.m3: the PREVIEWS that appear and vanish.  Pre-filtered on a CHANGED binder count,
            #    because `preview_source` re-derives the page map per call and 3,095 x 2 would be a
            #    corpus pass of its own for a population of 34.
            if len(b_inc) != len(b_all):
                was = RS.preview_source(blob, pal, a_inc)
                rr: List[str] = []
                now = RS.preview_source(blob, pal, a_all, rr)
                if was is None and now is not None:
                    self.prev_appear.append("ef%03d %s" % (ef, pal.name))
                    if pal.entries == 256:
                        self.prev_appear_drawn.append("ef%03d %s" % (ef, pal.name))
                elif was is not None and now is None:
                    self.prev_vanish.append("ef%03d %s" % (ef, pal.name))
                    self.prev_reasons["ef%03d %s" % (ef, pal.name)] = rr[0] if rr else ""
                    if pal.entries == 256:
                        self.prev_vanish_drawn.append("ef%03d %s" % (ef, pal.name))

    # -- derived views -------------------------------------------------------
    def by_source(self, src: str, where=None) -> List[Tuple[int, int, int]]:
        d = self.pages if where is None else where
        return sorted(k for k, p in d.items() if p.depth_source == src)

    def refused_of(self, klass: str, where=None) -> List[Tuple[int, int, int]]:
        d = self.refusals if where is None else where
        return sorted(k for k, v in d.items() if klass in v)

    def cid(self, k) -> str:
        r = self.C.get(k)
        return r["id"] if r else "ef%03d.x%d_y%d" % k


# --------------------------------------------------------------------------- I0
def i0_partition(D: Data) -> None:
    """★ **CALIBRATE FIRST -- THE WITNESS PARTITION.**

    Everything below rests on one claim: the SHIPPED fixed reader, filtered to INCUMBENT, reproduces
    the pre-W6b-3 population **tuple for tuple**.  That claim is what makes *"the census and channel
    G do not move"* a statement about the INPUT rather than a hope about the output, so it is proved
    against `_LEGACY_SO_RECORD` -- the retired decoder, frozen in this file -- and against a binding
    roll written here from scratch, over all 372 containers, before any other gate spends it.

    Then two KNOWN ANSWERS re-found through the shipped code, and **the calibration's own limit
    printed**: ef211 holds ZERO multi-part records, so THE DOME rung evaluates no ``P >= 2`` byte.
    """
    print("[I0] CALIBRATE -- THE WITNESS PARTITION: the FIXED reader, narrowed, IS the old one")
    chk("containers", len(D.paths), PIN["containers"])
    chk("records the RETIRED reader accepts", D.legacy_rec_n, PIN["legacy_records"])
    chk("...of which carry a tpage/clut pair", D.legacy_tpage_n, PIN["legacy_tpage_bearing"])
    chk("INCUMBENT bindings (include_direct=True)", D.inc_on, PIN["incumbent_bindings_direct"])
    chk("INCUMBENT bindings (the CLUT lane's default)", D.inc_off,
        PIN["incumbent_bindings_nodirect"])
    chk("★ containers where the narrowed reader DIFFERS, tuple for tuple", len(D.part_bad),
        PIN["containers_differing"])
    chk("...and the compatibility view reproduces entry 0 on every legacy record", D.compat_ok,
        PIN["compat_view_agrees"])
    chk("...with no disagreement", len(D.compat_bad), 0)
    print("   %d containers . the RETIRED `so_record` accepts %d records / %d tpage-bearing"
          % (len(D.paths), D.legacy_rec_n, D.legacy_tpage_n))
    print("   the SHIPPED reader narrowed to INCUMBENT: %d bindings (direct admitted) / %d (the CLUT"
          " lane's default) -- IDENTICAL tuple for tuple on (geom, tpage, clut_word, bpp, entries,"
          " cell, chunk_slot) in %d/%d containers, %d differing"
          % (D.inc_on, D.inc_off, len(D.paths) - len(D.part_bad), len(D.paths), len(D.part_bad)))
    print("   -> THE CONTAINMENT IS A PROPERTY OF THE INPUT.  Every consumer narrowed to this class"
          " is byte-identical BY CONSTRUCTION, which is a different and stronger thing than every"
          " consumer having been inspected.")

    # KNOWN ANSWER 1 -- THE DOME.  ef211 (704,384): the readerless lower half the W6b-1 cast ladder
    # banded on screen, and channel G's flagship.  It must still be channel G's, at 8bpp.
    dome = (211, 704, 384)
    chk("THE DOME is named by the page view", D.gview.get(dome), (8,))
    pg = D.pages.get(dome)
    chk("...and the kit still emits it", (pg.bpp, pg.depth_source, pg.depth_inherited) if pg else (),
        (8, "so-page", True))
    chk("...with ZERO readers", len(pg.hazards.readers) if pg else -1, 0)
    chk("...and CHANNEL A is SILENT there", D.aview.get(dome), None)
    # ...AND THE LIMIT, PRINTED: this known answer evaluates no P >= 2 byte at all.
    ef211_p2 = sum(1 for r in D.recs if r["ef"] == 211 and r["nparts"] >= 2)
    chk("ef211 multi-part records (the calibration's own LIMIT)", ef211_p2, PIN["ef211_p2_records"])
    print("   KNOWN ANSWER 1  ef211 (704,384) THE DOME: channel G, 8bpp, inherited, 0 readers --"
          " UNMOVED.  ** AND THE LIMIT: ef211 holds %d multi-part records, so this rung re-finds a"
          " known answer WITHOUT evaluating a single P>=2 byte.  It calibrates the containment, not"
          " the new reading." % ef211_p2)

    # KNOWN ANSWER 2 -- the ef226 outlier, BY OFFSET AND VALUE.  A textured==0 record with a
    # live-looking binding: the one record between "tpage-bearing" and "textured", named rather than
    # renumbered away.
    odd = [r for r in D.recs if r["nparts"] >= 1 and not r["textured"]]
    chk("records with a pair but textured == 0", len(odd), 1)
    r = odd[0]
    chk("...it is ef226 GEOM 0x9c804", (r["ef"], r["geom"]), (226, 0x9C804))
    chk("...at record 0x9c7f4", r["at"], 0x9C7F4)
    chk("...binding tpage 0x97 / clut 0x3e00", r["parts"][0], (0x97, 0x3E00))
    chk("...and the SHIPPED docstring still names it by offset AND value",
        all(t in RS.so_record.__doc__ for t in ("0x9c804", "0x9c7f4", "0x97", "0x3e00", "ef226")),
        True)
    print("   KNOWN ANSWER 2  the ef226 outlier, BY OFFSET AND VALUE: GEOM %#x, record %#x, tpage"
          " %#x, clut %#x, textured %d -- the ONE record between `tpage-bearing` and `textured`,"
          " still named in the shipped docstring rather than renumbered away."
          % (r["geom"], r["at"], r["parts"][0][0], r["parts"][0][1], r["textured"]))


# --------------------------------------------------------------------------- I1
def i1_reader(D: Data) -> None:
    """design sec 2 -- **THE READER**, and the invariant that runs the OPPOSITE way.

    The obvious risk in a length fix is reading too little.  The one this gate exists for is reading
    too little in the other direction: **a record with ZERO pairs is still a RECORD**, and the
    natural new shape (*"no pairs, return None"*) would silently shrink ``geom_with_so``'s
    DENOMINATOR, flip ``complete`` on containers that read UNBOUND today and dissolve
    ``acknowledge_shared`` on palettes that never needed it.  Unsafe-by-omission is still unsafe, so
    the 36 P=0 records are counted here AND the counterfactual is run.

    And ``arrayB`` at +0x06 is what the acceptance test actually rests on: ``recLen == 8 + 8P`` is
    near-tautological given ``P := (recLen-8)//8``, while ``arrayB == 8 + 4P`` takes a value OUTSIDE
    the two a ``P <= 1`` corpus could ever supply on every one of the 126 novel records.
    """
    print("[I1] THE READER -- 502 records, 649 slots, and the P = 0 invariant")
    hist = Counter(r["nparts"] for r in D.recs)
    slots = sum(r["nparts"] for r in D.recs)
    novel = [r for r in D.recs if r["witness"] == RS.WITNESS_NOVEL]
    chk("accepted records", len(D.recs), PIN["records"])
    chk("binding SLOTS", slots, PIN["slots"])
    chk("NOVEL records (P >= 2)", len(novel), PIN["novel_records"])
    chk("...and their slots", sum(r["nparts"] for r in novel), PIN["novel_slots"])
    chk("the P histogram", dict(hist), PIN["p_hist"])
    chk("corpus max P", max(hist), PIN["max_p"])
    chk("...strictly below the loop BOUND", max(hist) < RS.MAX_SO_PARTS, True)
    chk("tpage-bearing records", sum(1 for r in D.recs if r["nparts"] >= 1), PIN["tpage_bearing"])
    chk("records declaring textured == 1", sum(1 for r in D.recs if r["textured"] == 1),
        PIN["textured"])
    # ★ arrayB: the INDEPENDENT halfword, and where its evidence actually lives.
    chk("recordBase + recLen == geomBase on every accepted record",
        sum(1 for r in D.recs if r["at"] + r["len"] == r["geom"]), len(D.recs))
    chk("arrayB == 8 + 4P on every accepted record",
        sum(1 for r in D.recs if r["arrayB"] == 8 + 4 * r["nparts"]), len(D.recs))
    informative = [r for r in D.recs if r["arrayB"] not in (8, 12)]
    chk("★ records whose arrayB is OUTSIDE the {8,12} a P<=1 corpus could supply", len(informative),
        PIN["arrayb_informative"])
    chk("...and they are EXACTLY the novel ones", sorted((r["ef"], r["geom"]) for r in informative),
        sorted((r["ef"], r["geom"]) for r in novel))
    print("   %d records / %d slots ; P histogram %s ; max P = %d < MAX_SO_PARTS = %d"
          % (len(D.recs), slots, dict(sorted(hist.items())), max(hist), RS.MAX_SO_PARTS))
    print("   %d NOVEL records carrying %d slots -- record, slot 0 AND every slot >= 1 alike, because"
          " the retired reader returned None for the WHOLE record"
          % (len(novel), sum(r["nparts"] for r in novel)))
    print("   the ACCEPTANCE TEST: recLen is near-tautological (it asserts only recLen %% 8 == 0);"
          " arrayB at +0x06 agrees %d/%d and takes a value OUTSIDE {8,12} on %d/%d NOVEL records --"
          " so the informative population is EXACTLY the novel one, and +0x06 stops being OPAQUE"
          % (len(D.recs), len(D.recs), len(informative), len(novel)))
    chk("tpage-bearing minus textured is the ef226 outlier, and nothing else",
        sum(1 for r in D.recs if r["nparts"] >= 1) - sum(1 for r in D.recs if r["textured"] == 1), 1)

    # ★ THE P = 0 INVARIANT, and its COUNTERFACTUAL.
    p0 = [r for r in D.recs if r["nparts"] == 0]
    chk("P = 0 records", len(p0), PIN["p0_records"])
    chk("...and every one of them counts in `geom_with_so`",
        sum(v[1] for v in D.geom_with_so.values()), len(D.recs))
    would_flip = 0
    p0_by_ef = Counter(r["ef"] for r in p0)
    for ef, (total, with_so, _nov) in D.geom_with_so.items():
        was = total > 0 and with_so == total
        now = total > 0 and (with_so - p0_by_ef.get(ef, 0)) == total
        if was != now:
            would_flip += 1
    chk("...and dropping them would NOT be free (the counterfactual is non-empty)", would_flip > 0,
        True)
    print("   ★ THE P = 0 INVARIANT: %d records carry ZERO pairs and are STILL records -- counted in"
          " `geom_with_so` BEFORE any tpage check, exactly where the pre-W6b-3 `with_so += 1` sat."
          "  COUNTERFACTUAL: returning None on them would flip `complete` on %d containers and"
          " dissolve `acknowledge_shared` on palettes that never needed it.  Unsafe-by-omission is"
          " still unsafe." % (len(p0), would_flip))


# --------------------------------------------------------------------------- I2
def i2_safety_fix(D: Data) -> None:
    """design sec 4 + addendum **A1** -- **THE SAFETY FIX**, through the SHIPPED `palette_map`.

    The reader was not merely missing an answer; it was publishing a WRONG one.  Five palettes
    shipped ``DERIVED PRIVATE`` that a dropped record contradicts.  This gate re-measures the whole
    3,095-palette census through the shipped path, in BOTH readings -- the pre-fix one is reproduced
    by handing `palette_map` an INCUMBENT attribution, which is exactly the population the retired
    reader could see -- and pins the move.

    ★ **AND IT PINS ADDENDUM A1'S GUARDED SPLIT.**  ``complete`` flips INCOMPLETE -> COMPLETE on 19
    containers, and left as a bare boolean that would have DISSOLVED ``acknowledge_shared`` on 122
    palettes -- 24x the population of the 5 verdicts the fix exists to repair, moving in the
    PERMISSIVE direction, as a side effect of a SAFETY fix.  So the release is **measured and NOT
    taken**: those palettes take the ``NOVEL-DEPENDENT`` verdict variant with ``shared = True``.
    **0 palettes are released BY THE COVERAGE FLIP**, and the counterfactual is printed rather than
    banked.

    ⚠ **AND THAT ZERO IS SCOPED TO A1's BRANCH, DELIBERATELY.**  The unconditional safety fix moves
    palettes off ``shared`` too -- a SHARED-UNKNOWN palette that gains a NAMED single binder is
    ``DERIVED PRIVATE``, which IS the repair and is design-sanctioned by A1's ``46 + 37`` -- so the
    whole ``_gate_shared`` obligation delta is measured here in **both directions** on the flag that
    gate reads, beside the branch figure. A zero under an unqualified noun would have read as a
    claim about the gate.
    """
    print("[I2] THE SAFETY FIX -- the verdict census, the dedupe law, and A1's GUARDED release")
    v = D.verdicts
    chk("(before) DERIVED PRIVATE", v["before_private"], PIN["before_private"])
    chk("(before) DERIVED SHARED", v["before_shared"], PIN["before_shared"])
    chk("(before) SHARED-UNKNOWN", v["before_unknown"], PIN["before_unknown"])
    chk("(before) UNBOUND at COMPLETE", v["before_unbound"], PIN["before_unbound"])
    chk("DERIVED PRIVATE", v["private"], PIN["n_private"])
    chk("DERIVED SHARED", v["shared"], PIN["n_shared"])
    chk("SHARED-UNKNOWN", v["unknown"], PIN["n_unknown"])
    chk("UNBOUND at COMPLETE (incumbent completeness)", v["unbound"], PIN["n_unbound_complete"])
    chk("★ UNBOUND at COMPLETE (NOVEL-DEPENDENT) -- the guard still ARMED", v["guarded"],
        PIN["n_unbound_complete_novel_guarded"])
    chk("...no other verdict string exists", v["OTHER"], 0)
    total = sum(v[k] for k in ("private", "shared", "unknown", "unbound", "guarded"))
    chk("the identity: every palette lands in exactly one bucket", total, PIN["palettes_total"])
    chk("★ palettes RELEASED from `acknowledge_shared` by the COVERAGE FLIP (A1's branch)",
        PIN["n_unbound_complete_novel_guarded"] - D.guarded_shared_ok, PIN["n_released"])
    chk("...i.e. every NOVEL-DEPENDENT palette really carries shared = True", D.guarded_shared_ok,
        D.guarded_n)
    # ★ AND THE WHOLE OBLIGATION SURFACE, not just A1's branch -- measured on the flag `_gate_shared`
    # reads.  "0 released" is a statement about the COMPLETENESS branch; the SAFETY FIX moves
    # palettes off `shared` too, by giving them a NAMED single binder, and that number is design-
    # sanctioned (A1) but was measured by nothing.  A count that does not match its own noun is the
    # defect this rung repairs, so the noun is narrowed and the other direction gets its own pin.
    chk("★ `_gate_shared` obligation RELEASED corpus-wide (shared True -> False)",
        len(D.guard_released), PIN["guard_released"])
    chk("★ ...and ARMED where it was not (shared False -> True)", len(D.guard_armed),
        PIN["guard_armed"])
    chk("...and the release is EXACTLY the SHARED-UNKNOWN palettes that gained a PRIVATE binder",
        len(D.guard_released), D.split_geom["priv"])
    chk("★★ ...and the ARMED set IS the five historical FALSE PRIVATE palettes, name for name",
        sorted(D.guard_armed), sorted(D.false_priv_before))
    print("   BEFORE (the retired reader's population, reproduced through the shipped path):"
          " %d PRIVATE / %d SHARED / %d SHARED-UNKNOWN / %d UNBOUND-at-COMPLETE"
          % (v["before_private"], v["before_shared"], v["before_unknown"], v["before_unbound"]))
    print("   AFTER : %d PRIVATE / %d SHARED / %d SHARED-UNKNOWN / %d UNBOUND-at-COMPLETE"
          " / %d UNBOUND-at-COMPLETE-(NOVEL-DEPENDENT).  Total %d, identity holds."
          % (v["private"], v["shared"], v["unknown"], v["unbound"], v["guarded"], total))

    chk("★ FALSE PRIVATE, after the fix", len(D.false_priv_now), PIN["false_private_now"])
    chk("★ FALSE PRIVATE, before it -- and the count is what makes the 0 above evidence",
        len(D.false_priv_before), PIN["false_private_before"])
    chk("...by name", sorted(D.false_priv_before),
        ["ef179 pal.s0.x0_y248.e256", "ef179 pal.s0.x16_y244.e16", "ef381 pal.s0.x0_y248.e256",
         "ef438 pal.s0.x0_y242.e256", "ef438 pal.s0.x0_y248.e256"])
    print("   ★ FALSE PRIVATE %d -> %d.  The five, by name, kept as the historical set: %s"
          % (len(D.false_priv_before), len(D.false_priv_now), ", ".join(sorted(D.false_priv_before))))

    chk("SHARED-UNKNOWN palettes gaining a NAMED binder", D.gains, PIN["unknown_gains"])
    chk("...split by GEOM MODEL (the dedupe law, and what SHIPS)",
        (D.split_geom["priv"], D.split_geom["shared"]), PIN["gain_split_geom"])
    chk("...and by BINDING SLOT (the un-deduped counterfactual)",
        (D.split_slot["priv"], D.split_slot["shared"]), PIN["gain_split_slot"])
    chk("containers whose `complete` flips on the multi-part reader", len(D.flips),
        PIN["complete_flips"])
    chk("...by name", sorted(D.flips),
        [58, 94, 154, 155, 179, 186, 237, 261, 290, 300, 382, 390, 415, 424, 431, 432, 438, 439,
         490])
    chk("THE 205-PALETTE MOVE CLOSES: 83 gain a binder + 122 are guarded by the flip",
        D.gains + v["guarded"], v["before_unknown"] - v["unknown"])
    print("   the %d SHARED-UNKNOWN palettes that gain a named binder split %d PRIVATE + %d SHARED"
          " counting distinct GEOM MODELS -- the noun the reason string uses, and what ships;"
          " %d + %d counting binding SLOTS.  The two differ, which is why the dedupe is a LAW."
          % (D.gains, D.split_geom["priv"], D.split_geom["shared"], D.split_slot["priv"],
             D.split_slot["shared"]))
    print("   THE 205 CLOSES: %d - %d = %d = %d gaining a named binder + %d moved to the GUARDED"
          " NOVEL-DEPENDENT verdict by the coverage flip (guarded, NOT released)"
          % (v["before_unknown"], v["unknown"], v["before_unknown"] - v["unknown"], D.gains,
             v["guarded"]))
    print("   ★★ A1, PINNED: `complete` flips on %d containers (%s) and %d palettes hang on it."
          "  The completeness is HONEST -- the denominator is the container's own bytes -- but the"
          " OBLIGATION is not dissolved by it: all %d take the NOVEL-DEPENDENT verdict with"
          " shared = True, so **%d palettes are released BY THE COVERAGE FLIP**.  The release is"
          " MEASURED and NOT TAKEN, pending owner ratification: loosening later is cheap, tightening"
          " after shipping is not."
          % (len(D.flips), ", ".join("ef%03d" % e for e in sorted(D.flips)), v["guarded"],
             D.guarded_shared_ok, PIN["n_unbound_complete_novel_guarded"] - D.guarded_shared_ok))
    print("   ...AND THE NOUN IS NARROWED ON PURPOSE.  Corpus-wide the `_gate_shared` obligation is"
          " RELEASED on %d palettes and ARMED on %d -- the release is the SAFETY FIX's OWN direction"
          " (a SHARED-UNKNOWN palette that gains a NAMED single binder is PRIVATE, which is the"
          " repair), it is design-sanctioned by A1's `46 + 37`, and it is the same %d.  'Zero"
          " released' is a statement about the COMPLETENESS branch and about nothing else; both"
          " numbers are pinned so neither can stand in for the other."
          % (len(D.guard_released), len(D.guard_armed), D.split_geom["priv"]))
    print("   ★★ AND THE ARMED SET IS THE FIVE FALSE PRIVATE PALETTES, NAME FOR NAME (%s) -- the"
          " guard is armed on exactly the palettes that were being recoloured against a verdict the"
          " container's own bytes contradict.  That is the safety fix, stated as an obligation"
          " rather than as a verdict count." % ", ".join(sorted(D.guard_armed)))

    # ★ THE DEDUPE LAW's two populations, and the check that keeps it from hiding a hazard.
    chk("SELF-SHARED palettes (one model, > 1 entry) -- the dedupe FLIPS the verdict",
        len(D.self_shared), PIN["self_shared_verdict"])
    chk("...by name", sorted(D.self_shared),
        ["ef179 pal.s0.x0_y249.e256", "ef186 pal.s0.x0_y248.e256", "ef415 pal.s0.x0_y248.e256"])
    chk("COUNT-ONLY palettes -- the verdict holds, the printed COUNT would not",
        len(D.count_only), PIN["self_shared_count_only"])
    chk("★ one GEOM binding one palette at TWO DIFFERENT DEPTHS", len(D.one_geom_two_depths),
        PIN["one_geom_two_depths"])
    print("   THE DEDUPE's TWO POPULATIONS: %d SELF-SHARED (%s) -- slot-counting publishes 'DERIVED"
          " SHARED: 2 GEOM models' about ONE model; and %d COUNT-ONLY (%s) -- the verdict stays"
          " SHARED and the printed count is wrong by one."
          % (len(D.self_shared), ", ".join(sorted(D.self_shared)), len(D.count_only),
             " ; ".join(sorted(D.count_only))))
    print("   ...and the check that stops the dedupe HIDING something: %d cases corpus-wide of one"
          " GEOM binding one palette at two different DEPTHS.  The dedupe can never collapse a depth"
          " conflict." % len(D.one_geom_two_depths))

    # ★ A7.m3 -- the PREVIEW population moves in BOTH directions, and both are measured.
    chk("previews APPEARING (0 -> 1 binder, the new binder novel)", len(D.prev_appear),
        PIN["previews_appearing"])
    chk("previews VANISHING (a SECOND binder became visible)", len(D.prev_vanish),
        PIN["previews_vanishing"])
    chk("★ ...and the VANISHING set IS the historical FALSE PRIVATE set, palette for palette",
        sorted(D.prev_vanish), sorted(D.false_priv_before))
    miss = [k for k, r in D.prev_reasons.items()
            if "ORDER inside a record's binding array is UNMEASURED" not in r
            or "NO column is picked" not in r]
    chk("...and every vanished preview carries a REASON naming the unmeasured order", len(miss), 0)
    print("   PREVIEWS: %d APPEAR (a palette that had no single binder now has one) and %d VANISH."
          "  ★ THE VANISHING SET IS EXACTLY THE FIVE HISTORICAL FALSE PRIVATE PALETTES -- which is"
          " the strongest form this number could take: the previews the fix withdraws are precisely"
          " the five pictures that were being drawn against a verdict the container contradicts."
          % (len(D.prev_appear), len(D.prev_vanish)))
    print("      the %d, by name: %s" % (len(D.prev_vanish), ", ".join(sorted(D.prev_vanish))))
    print("      the refusal is NOT widened and NOT de-duplicated -- on 2 of the 3 self-shared"
          " palettes the model's two entries name DIFFERENT columns, so no order-free column pick"
          " exists.  It carries a REASON instead, and every one of the %d names the unmeasured"
          " order." % len(D.prev_vanish))
    # ★ AND THE SCOPE IS STATED, because the same noun has two populations.
    chk("previews APPEARING at the scope `render_previews` DRAWS (entries == 256)",
        len(D.prev_appear_drawn), PIN["previews_appearing_drawn"])
    chk("previews VANISHING at the scope `render_previews` DRAWS", len(D.prev_vanish_drawn),
        PIN["previews_vanishing_drawn"])
    chk("...and the difference is exactly the palettes the preview loop never draws",
        (len(D.prev_appear) - len(D.prev_appear_drawn),
         len(D.prev_vanish) - len(D.prev_vanish_drawn)), PIN["previews_not_drawn"])
    chk("...every one of which is a non-256-entry palette, by construction of the filter",
        sorted(set(D.prev_vanish) - set(D.prev_vanish_drawn)), ["ef179 pal.s0.x16_y244.e16"])
    print("   ⚠ [M] MEASURED HERE, NOT CARRIED: the implementation handoff quoted 30 APPEARING and"
          " 4 VANISHING.  Both are re-measured through the SHIPPED `preview_source` over the whole"
          " corpus -- and the handoff's pair is the RIGHT number for a DIFFERENT scope, which is why"
          " both are pinned here rather than one being called wrong.")
    print("   TWO SCOPES: `preview_source` moves on %d/%d palettes; `render_previews` filters"
          " `entries != 256`, so only %d/%d are pictures that appear or disappear for an author."
          "  The %d + %d that do not draw are 16-entry rows (%s) -- `test_summon_reskin.py` pins the"
          " DRAWN pair, this board pins both, and neither number is the other's under one name."
          % (len(D.prev_appear), len(D.prev_vanish), len(D.prev_appear_drawn),
             len(D.prev_vanish_drawn), len(D.prev_appear) - len(D.prev_appear_drawn),
             len(D.prev_vanish) - len(D.prev_vanish_drawn),
             ", ".join(sorted(set(D.prev_vanish) - set(D.prev_vanish_drawn))) or "none vanishing"))


# --------------------------------------------------------------------------- I3
def i3_flagship(D: Data) -> None:
    """★ **THE FLAGSHIP**: ``ef381 pal.s0.x0_y248.e256``.

    It is the right vehicle for one reason that has to be STATED rather than enjoyed: here the SLOT
    count and the MODEL count **agree at 7** -- seven slots on seven DISTINCT GEOM models, one of
    them the INCUMBENT record's entry 0.  So the archive's "seven" survives the dedupe law rather
    than accidentally surviving it, and the number is robust to the very correction that moved three
    other palettes' verdicts.
    """
    print("[I3] THE FLAGSHIP -- ef381 pal.s0.x0_y248.e256, where slot-count and model-count AGREE")
    chk("the flagship palette resolves", D.flagship is not None, True)
    if D.flagship is None:
        return
    n_slots, n_models, n_novel, reason, ident = D.flagship
    chk("binding SLOTS", n_slots, PIN["ef381_binders"])
    chk("distinct GEOM MODELS", n_models, PIN["ef381_models"])
    chk("...of which NOVEL", n_novel, PIN["ef381_novel"])
    chk("...so the two predicates AGREE, and the 7 is robust to the dedupe", n_slots, n_models)
    chk("the shipped verdict says SEVEN GEOM MODELS",
        reason.startswith("DERIVED SHARED: 7 GEOM models"), True)
    chk("...and names the multi-part evidence as IDENTIFICATION ONLY",
        "MULTI-PART record the kit did not read before W6b-3" in reason
        and "identification only" in reason and "ORDER" in reason, True)
    chk("...and the INCUMBENT one is entry 0 of a record", sum(1 for t in ident if t[2] == 0), 1)
    print("   %d slots on %d DISTINCT GEOM models (%d of them novel).  slot-count == model-count == %d"
          " -- the flagship number is TRUE under both predicates, so it is evidence about the format"
          " rather than an artefact of which one was used." % (n_slots, n_models, n_novel, n_slots))
    print("   binders (geom / record / slot): %s"
          % ", ".join("%#x / %#x / %d" % t for t in ident))
    print("   the shipped reason: %s" % reason[:230])


# --------------------------------------------------------------------------- I4
def i4_containment(D: Data) -> None:
    """★★ **THE CONTAINMENT, A/B -- and one of these halves moving is the whole rung failing.**

    Half A: the SHIPPED defaults.  `scenery_surface`'s CENSUS scope still reads W6b-1's 187/2,385;
    `page_depth_view` is cell-for-cell identical to a roll off the FROZEN legacy reader;
    `bound_models` produces the same binding fields per GEOM block it always did.

    Half B: the **COUNTERFACTUAL**.  A containment never measured against the thing it contains is an
    assertion, so the NAIVE widening -- `page_depth_view` asked for the TRUE population -- is run and
    the leak is shown to be real and non-empty.  It is not a hypothetical: fold the novel slots into
    channel G and ef184's column goes dual, so the ef184 pair would refuse as `channel-g-dual-depth`,
    a TRUE but WRONG-SHAPED verdict blaming channel G's own record set for a contradiction the second
    half of which comes from a channel the kit does not license.

    And the three deliberately UN-narrowed sites are printed with the measurement that licenses
    leaving them alone, rather than with a promise.
    """
    print("[I4] THE CONTAINMENT, A/B -- the shipped defaults, then the leak that was declined")
    # ---- HALF A ----------------------------------------------------------------
    chk("the CENSUS default still reads W6b-1's readable set", len(D.census_pages),
        PIN["so_uv_cells"])
    chk("...and W6b-1's dark set", len(D.census_dark), PIN["depth_unknown_census"])
    chk("...and states NONE of the channel-A classes",
        sorted(D.census_klasses & {"array-dual-depth", "array-vs-column-depth"}), [])
    chk("the scenery page-cell population", len(D.cells), PIN["scenery_cells"])
    bad = [k for k in D.gview if D.gview[k] != D.gview_legacy.get(k)]
    chk("`page_depth_view` cells the FROZEN legacy roll does not reproduce", len(bad),
        PIN["pdv_legacy_mismatch"])
    chk("...and the two name the SAME cells", sorted(D.gview) == sorted(D.gview_legacy), True)
    mm = 0
    for path in D.paths:
        ef = int(os.path.basename(path)[2:5])
        want = {}
        with open(path, "rb") as fh:
            blob = fh.read()
        for (g, tp, cw, bpp, ent, cell, _s) in _legacy_bindings(blob, True):
            want[g] = (tp, bpp, cw if bpp != 15 else cw, None if bpp == 15 else cell, ent,
                       (dec(tp)[0], dec(tp)[1]))
        got = D.model_fields[ef]
        if sorted(got) != sorted(want):
            mm += 1
            continue
        for g, t in got.items():
            if (t[0], t[1], t[3], t[4], t[5]) != (want[g][0], want[g][1], want[g][3], want[g][4],
                                                  want[g][5]):
                mm += 1
                break
    chk("★ `bound_models` GEOM blocks whose binding the legacy roll does not reproduce", mm,
        PIN["bound_models_mismatch"])
    print("   HALF A -- THE SHIPPED DEFAULTS: census %d read + %d dark (W6b-1, byte for byte) ;"
          " `page_depth_view` == the FROZEN legacy roll on %d/%d cells ; `bound_models` reproduces"
          " the legacy binding on every GEOM block in %d/%d containers"
          % (len(D.census_pages), len(D.census_dark), len(D.gview) - len(bad), len(D.gview),
             len(D.paths) - mm, len(D.paths)))
    print("   ...and the 1:1 assertion lives AT THE CALL SITE, not in a docstring: `bound_models`"
          " RAISES if the incumbent bindings are ever not 1:1 with GEOM blocks, which is the only"
          " thing that makes `by_geom`'s last-wins collapse impossible rather than unlikely.")

    # ---- HALF B: THE COUNTERFACTUAL ---------------------------------------------
    inc_cells = set(D.gview)
    all_cells = set(D.cf_all)
    inc_single = [k for k in inc_cells if len(D.gview[k]) == 1]
    all_single = [k for k in all_cells if len(D.cf_all[k]) == 1]
    inc_dual = [k for k in inc_cells if len(D.gview[k]) > 1]
    all_dual = [k for k in all_cells if len(D.cf_all[k]) > 1]
    flipped = sorted(set(all_dual) & set(inc_single))
    # ...and the SAME roll at PAGE-ORIGIN granularity, because a page word governs a COLUMN of two
    # cells and the design's [V] figures are origins.  Both are pinned; neither is reconciled into
    # the other, which is the only way a granularity slip stays visible instead of becoming a pin.
    def _origins(view) -> Dict[Tuple[int, int, int], set]:
        out: Dict[Tuple[int, int, int], set] = defaultdict(set)
        for (ef, x, y), ds in view.items():
            out[(ef, x, y - (y % PAGE_LINES))] |= set(ds)
        return out
    o_inc, o_all = _origins(D.gview), _origins(D.cf_all)
    c_inc, c_all = D.graw, D.cf_raw
    o_flip = sorted(k for k in o_all if len(o_all[k]) > 1 and len(o_inc.get(k, ())) == 1)
    # (a) THE UNFILTERED SCOPE -- every page ORIGIN any `so` binding names, whether or not the
    #     container uploads a cell there.  This is the scope the design's page-origin [V] figures
    #     were taken at, reproduced rather than re-scoped.
    chk("(unfiltered) channel G, bound page-ORIGINS", len(c_inc), PIN["cf_origins_incumbent"])
    chk("(unfiltered) ...and under the NAIVE widening", len(c_all), PIN["cf_origins_all"])
    chk("(unfiltered) single-depth ORIGINS", len([k for k in c_inc if len(c_inc[k]) == 1]),
        PIN["cf_origin_single_incumbent"])
    chk("(unfiltered) ...and under the NAIVE widening",
        len([k for k in c_all if len(c_all[k]) == 1]), PIN["cf_origin_single_all"])
    chk("(unfiltered) DUAL ORIGINS", len([k for k in c_inc if len(c_inc[k]) > 1]),
        PIN["cf_origin_dual_incumbent"])
    chk("(unfiltered) ...and under the NAIVE widening",
        len([k for k in c_all if len(c_all[k]) > 1]), PIN["cf_origin_dual_all"])
    # (b) THE SHIPPED VIEW's SCOPE -- SCENERY only, which is one row smaller and deliberately so.
    chk("(kit scope) channel G, bound page-ORIGINS", len(o_inc), PIN["cf_kit_origins_incumbent"])
    chk("(kit scope) ...and under the NAIVE widening", len(o_all), PIN["cf_kit_origins_all"])
    chk("(kit scope) single-depth ORIGINS", len([k for k in o_inc if len(o_inc[k]) == 1]),
        PIN["cf_kit_origin_single_incumbent"])
    chk("(kit scope) ...and under the NAIVE widening",
        len([k for k in o_all if len(o_all[k]) == 1]), PIN["cf_kit_origin_single_all"])
    chk("(kit scope) DUAL ORIGINS -- and the DUAL count is the SAME in both scopes",
        len([k for k in o_inc if len(o_inc[k]) > 1]), PIN["cf_origin_dual_incumbent"])
    chk("(kit scope) ...and under the NAIVE widening",
        len([k for k in o_all if len(o_all[k]) > 1]), PIN["cf_origin_dual_all"])
    chk("ORIGINS that flip SINGLE -> DUAL under the widening", len(o_flip), PIN["cf_flip_origins"])
    # ★ ...AND THE DIFFERENCE BETWEEN THE TWO SCOPES IS EXACTLY THE UNDECLARED COLUMNS.
    dropped_inc = sorted(set(c_inc) - set(o_inc))
    dropped_all = sorted(set(c_all) - set(o_all))
    chk("★ every origin the SHIPPED view drops is a column the container never UPLOADS",
        len([k for k in dropped_inc + dropped_all if k in D.undeclared_origins]),
        len(dropped_inc + dropped_all))
    chk("...(incumbent) how many that is", len(dropped_inc), 1)
    chk("...(under the widening) how many that is", len(dropped_all), 3)
    print("   ...THE TWO SCOPES, BOTH PRINTED, NEITHER RECONCILED: UNFILTERED (every origin a"
          " binding names) gives %d -> %d ; the SHIPPED view gives %d -> %d.  The %d origin(s)"
          " between them are columns the container NEVER UPLOADS -- %s -- and `page_depth_view`"
          " drops them on its own stated rule: *a recovered column the container never uploads is"
          " evidence about somebody else's page and attributes NOTHING here*.  The smaller number is"
          " that rule ENFORCED, not a shortfall."
          % (len(c_inc), len(c_all), len(o_inc), len(o_all),
             len(set(dropped_inc + dropped_all)),
             ", ".join(sorted({"ef%03d x%d_y%d" % k for k in dropped_inc + dropped_all}))))
    chk("channel G, bound CELLS (SHIPPED, incumbent)", len(inc_cells), PIN["cf_cells_incumbent"])
    chk("...and under the NAIVE widening", len(all_cells), PIN["cf_cells_all"])
    chk("channel G, single-depth CELLS (SHIPPED)", len(inc_single), PIN["cf_single_incumbent"])
    chk("...and under the NAIVE widening", len(all_single), PIN["cf_single_all"])
    chk("channel G, DUAL CELLS (SHIPPED)", len(inc_dual), PIN["cf_dual_incumbent"])
    chk("...and under the NAIVE widening", len(all_dual), PIN["cf_dual_all"])
    chk("cells that flip SINGLE -> DUAL under the widening", len(flipped),
        PIN["cf_flip_single_to_dual"])
    chk("...and the LEAK IS NON-EMPTY (a vacuous counterfactual proves nothing)",
        len(all_cells) > len(inc_cells), True)
    chk("★ the ef184 pair is among them -- i.e. the WRONG-SHAPED verdict is real",
        len([k for k in flipped if k[0] == 184]), 2)
    print("   HALF B -- THE COUNTERFACTUAL (`page_depth_view` asked for the TRUE population), AT BOTH"
          " GRANULARITIES, NEITHER RECONCILED INTO THE OTHER:")
    print("      page-ORIGINS (unfiltered): bound %d -> %d, single-depth %d -> %d, dual %d -> %d"
          % (len(c_inc), len(c_all), len([k for k in c_inc if len(c_inc[k]) == 1]),
             len([k for k in c_all if len(c_all[k]) == 1]),
             len([k for k in c_inc if len(c_inc[k]) > 1]),
             len([k for k in c_all if len(c_all[k]) > 1])))
    print("      page-ORIGINS (shipped)   : bound %d -> %d, single-depth %d -> %d, dual %d -> %d,"
          " %d origins flip"
          % (len(o_inc), len(o_all), len([k for k in o_inc if len(o_inc[k]) == 1]),
             len([k for k in o_all if len(o_all[k]) == 1]),
             len([k for k in o_inc if len(o_inc[k]) > 1]),
             len([k for k in o_all if len(o_all[k]) > 1]), len(o_flip)))
    print("      page-CELLS  : bound %d -> %d, single-depth %d -> %d, dual %d -> %d, %d cells flip"
          % (len(inc_cells), len(all_cells), len(inc_single), len(all_single), len(inc_dual),
             len(all_dual), len(flipped)))
    print("      the %d flips, by column: %s"
          % (len(flipped), ", ".join(sorted({"ef%03d x%d" % (k[0], k[1]) for k in flipped}))))
    print("   -> the naive fix would LICENSE the archive's own gains with no acknowledgement"
          " anywhere on the path, and would refuse the ef184 pair as `channel-g-dual-depth` -- TRUE,"
          " and WRONG-SHAPED: it blames CHANNEL G's own record set for a contradiction whose second"
          " half comes from a channel this kit does not license.  A refusal must never drift from"
          " the predicate that produced it.")

    # ---- the three deliberately UN-narrowed sites, with the measurement that licenses each -------
    ef211_p2 = sum(1 for r in D.recs if r["ef"] == 211 and r["nparts"] >= 2)
    chk("un-narrowed site 1 (`w6b2_gates.py` KNOWN ANSWER 1, ef211): 0 multi-part records",
        ef211_p2, 0)
    chk("un-narrowed site 3 (`w6b3_gates.py` G7): the DEFAULT is WITNESS_ALL by design",
        RS.attribution.__defaults__[-1], RS.WITNESS_ALL)
    print("   THREE SITES LEFT UN-NARROWED, EACH WITH ITS MEASUREMENT rather than a promise:")
    print("      1. ef211's calibration roll -- ef211 holds %d multi-part records, so the roll is"
          " IDENTICAL under every witness and leaving it alone keeps the calibration a genuine"
          " re-read of the container." % ef211_p2)
    print("      2. the class-C `colclut` union -- it unions a walker that already enumerates EVERY"
          " part of every record with the attribution binders, so the novel words are in the set"
          " either way.  The invariance is ASSERTED in I5, not assumed here.")
    print("      3. the safety-finding roll -- deliberately at `attribution`'s DEFAULT (%r).  Narrowed"
          " to INCUMBENT it would keep measuring the OLD delta and never notice the fix."
          % RS.WITNESS_ALL)
    print("   ...and the leak sites that ARE narrowed are auditable by grep, not by trust:"
          " `grep -rn \"witness=\" ff9mapkit/ studies/` returns the narrowing sites and nothing else.")


# --------------------------------------------------------------------------- I5
def i5_channel_a(D: Data) -> None:
    """design sec 6 + sec 8 -- **CHANNEL A's REACH, re-derived from the CONTAINERS after the reader
    change** and never carried across the fix on trust.

    The recon measured a 73-cell reach -- 65 unanimous + 8 dual -- and a deflation of the 65 into
    26 clean / 34 class-C / 7 program-write, all on the PRE-FIX instrument.  It is *expected* to
    hold, because the shipped census stays incumbent-narrowed so all 65 stay readerless; **expected
    is not measured**, so every one of those numbers is rolled again here through the shipped code.

    ★ **AND THE CLASS-C EVIDENCE IS TAKEN AT THE DEPTH's OWN GRANULARITY** (addendum A7.m1).  The
    census's ``hz_multi_palette`` is READER-derived and 65/65 of these cells are readerless, so its
    clean 0 is **VACUOUS, not a clear** -- it is printed beside the derived 34 so nobody mistakes the
    flag's silence for a verdict.  And the key SET is asserted EQUAL under the novel-only and the
    all-slot derivations, which is true exactly when the incumbent binder set is empty on all 65
    columns: that predicate is asserted and printed, not assumed.
    """
    print("[I5] CHANNEL A's REACH -- re-derived from the containers AFTER the reader change")
    gain = D.by_source("so-array", D.ack_pages)
    chk("cells CHANNEL A discloses (under the ack)", len(gain), PIN["gain_array"])
    chk("...and it is SHUT without it", len(D.by_source("so-array")), 0)
    dual_all = D.refused_of("array-dual-depth")
    dual_reach = [k for k in dual_all if not D.gview.get(k)]
    chk("ARRAY-DUAL cells in CHANNEL A's OWN reach (incumbent depth set EMPTY)", len(dual_reach),
        PIN["array_in_reach_dual"])
    chk("★ the strict reach: 65 unanimous + 8 dual", len(gain) + len(dual_reach), PIN["reach_strict"])
    depths = Counter(D.ack_pages[k].bpp for k in gain)
    print("   %d cells gain a depth under `%s` + %d multi-valued cells in channel A's own reach"
          " = %d new vs EVERY incumbent channel.  Depths %s."
          % (len(gain), DA.ACK_ARRAY_KEY, len(dual_reach), len(gain) + len(dual_reach),
             dict(sorted(depths.items()))))

    # ★ ALL 65 READERLESS -- which is what makes the census's own flag vacuous here.
    readerless = [k for k in gain if not D.readers.get(k)]
    chk("...and every one of them is READERLESS", len(readerless), PIN["array_readerless"])
    census_mp = len([k for k in gain if k in D.census_hz_multi])
    chk("the census's `hz_multi_palette` over the same 65 -- VACUOUS, not a clear", census_mp,
        PIN["census_multi_palette_vacuous"])

    # ★ CLASS C, DERIVED FROM BINDERS at the DEPTH's own granularity (design sec 8).
    class_c = [k for k in gain if len(D.ack_pages[k].hazards.column_clut_cells) > 1]
    chk("★ class C, derived from the COLUMN's own binders", len(class_c), PIN["array_class_c"])
    chk("...and the shipped `multi_palette` predicate agrees on every one",
        len([k for k in class_c if D.ack_pages[k].hazards.multi_palette]), len(class_c))
    prog_w = sorted(k for k in gain
                    if D.C.get(k) and (D.C[k]["hz_program_write"] or D.C[k]["hz_program_write_here"]))
    clean = [k for k in gain if k not in set(class_c) and k not in set(prog_w)]
    chk("cells refusing on a PROGRAM WRITE", len(prog_w), PIN["array_program_write"])
    chk("...all in ONE container", len({k[0] for k in prog_w}), 1)
    chk("genuinely CLEAN", len(clean), PIN["array_clean"])
    print("   ** THE REACH's REAL BOTTOM LINE IS %d, NOT %d.  %d/%d of the gained cells are"
          " READERLESS, so the census's reader-derived `hz_multi_palette` reads %d -- VACUOUS rather"
          " than a clear.  Re-derived from the BINDERS at COLUMN granularity: %d sit on a column"
          " bound with 2-4 distinct CLUT words."
          % (len(clean), len(gain), len(readerless), len(gain), census_mp, len(class_c)))
    overlap = len(set(class_c) & set(prog_w))
    chk("...and the two deflating classes OVERLAP on this many cells", overlap,
        PIN["array_deflation_overlap"])
    chk("...which is the module constant `ARRAY_RESIDUE_LINE` quotes rather than a bare literal",
        overlap, DA.ARRAY_DEFLATION_OVERLAP)
    print("   honest split: %d clean + %d class-C + %d program-write (in %s), the %d-cell overlap"
          " counted ONCE = %d.  The three do not sum to the total and saying so is the point."
          % (len(clean), len(class_c), len(prog_w),
             ", ".join("ef%03d" % e for e in sorted({k[0] for k in prog_w})) or "-", overlap,
             len(clean) + len(class_c) + len(prog_w) - overlap))

    # ★ A7.m1 -- the key SET is EQUAL under both derivations, and the predicate that makes it so.
    incumbent_empty = [k for k in gain if not D.gview.get(k)]
    chk("★ the predicate: the INCUMBENT binder set is EMPTY on every channel-A column",
        len(incumbent_empty), len(gain))
    keyset_equal = 0
    for k in gain:
        novel_keys = set(D.ack_pages[k].hazards.array_clut_cells)
        all_keys = set(D.ack_pages[k].hazards.column_clut_cells)
        if novel_keys == all_keys:
            keyset_equal += 1
    chk("★ class-C key SET equal under the novel-only and the all-slot derivations", keyset_equal,
        PIN["class_c_keyset_equal"])
    print("   ★ A7.m1: the class-C key SET is IDENTICAL under the novel-only and the all-slot"
          " derivations on %d/%d columns -- and it is identical for a REASON, not by luck: the"
          " incumbent binder set is EMPTY on all %d of them, so the two derivations have the same"
          " input.  The predicate is asserted, not assumed."
          % (keyset_equal, len(gain), len(incumbent_empty)))

    # the channel intersections, re-measured and printed
    p_cells = {k for k in gain if DA.program_depth(k[0], (k[1], k[2])) is not None}
    g_cells = {k for k in gain if k in D.gview}
    known = {k for k in gain if D.C.get(k) and D.C[k]["bpp"] is not None}
    chk("P intersect A", len(p_cells), 0)
    chk("G intersect A", len(g_cells), 0)
    chk("A intersect the census's KNOWN set", len(known), 0)
    print("   P n A = %d . G n A = %d . A n (census-known) = %d -- CHANNEL A's 65 are new against"
          " every incumbent channel, which is what makes it a channel rather than a re-reading"
          % (len(p_cells), len(g_cells), len(known)))
    print("   ⚠ AND ITS IN-GAME STANDING IS NOTHING: %s" % DA.ARRAY_CAVEAT[:190])


# --------------------------------------------------------------------------- I6
def i6_refusals(D: Data) -> None:
    """design sec 7 + addendum **A2 / A8** -- **THE REFUSALS, DERIVED AND NOT ENUMERATED**, and the
    one non-zero addressability decision in the rung, gated by a COUNTERFACTUAL.

    Both classes are derived live from the container.  The precedent that says why is
    ``channel-g-dual-depth``'s own text: *a kit building its refusal list from the attribution sweep
    alone would ship all 8 unlisted.*

    ★ **A2: ALL 12 ARRAY-DUAL CELLS REFUSE OUTRIGHT.**  The ``incumbent == EMPTY`` predicate SURVIVES
    as the split's DERIVATION -- 8 in channel A's own reach, 4 on columns another channel already
    serves -- and the gate prints it because it is informative.  But the TREATMENT is uniform: a
    hazard bites hardest exactly where another channel already covers the cell, and CHANNEL A holds
    VETO power, never emission power.  So the 4 lose their page too, and the addressability delta on
    the licensed path is **-6**, not the -2 a softer reading would have given.  Both numbers are
    measured; the -2 is printed as the considered-and-refused alternative so the CHOICE is stated.
    """
    print("[I6] THE REFUSALS -- derived, not enumerated; A2's uniform refusal, counterfactualled")
    dual = D.refused_of("array-dual-depth")
    conflict = D.refused_of("array-vs-column-depth")
    pdual = D.refused_of("program-dual-depth")
    gdual = D.refused_of("channel-g-dual-depth")
    spill = D.refused_of("spill-vs-own-page")
    chk("ARRAY-DUAL cells", len(dual), PIN["array_dual_cells"])
    chk("...over this many COLUMNS", len({(k[0], k[1]) for k in dual}), PIN["array_dual_columns"])
    chk("ARRAY-vs-COLUMN cells", len(conflict), PIN["array_vs_column_cells"])
    chk("...over this many COLUMNS", len({(k[0], k[1]) for k in conflict}),
        PIN["array_vs_column_columns"])
    chk("...and it is the ef184 x448 column", sorted({(k[0], k[1]) for k in conflict}), [(184, 448)])
    chk("PROGRAM-DUAL cells (unmoved)", len(pdual), PIN["program_dual_cells"])
    chk("CHANNEL-G-DUAL cells (unmoved)", len(gdual), PIN["g_dual"])
    chk("SPILL cells (unmoved)", len(spill), PIN["spill_cells"])

    # ★ THE 8/4 SPLIT, AS A DERIVED PREDICATE -- `the column's INCUMBENT depth set is EMPTY`.
    cols: Dict[tuple, dict] = {}
    for k in dual:
        c = (k[0], k[1])
        cols.setdefault(c, {"inc": set(), "nov": set(), "cells": []})
        cols[c]["cells"].append(k)
        cols[c]["inc"] |= set(D.gview.get(k, ()))
        cols[c]["nov"] |= set(D.aview.get(k, ()))
    in_reach = [c for c, v in cols.items() if not v["inc"]]
    covered = [c for c, v in cols.items() if v["inc"]]
    chk("★ columns where the INCUMBENT depth set is EMPTY (channel A's own reach)", len(in_reach), 4)
    chk("...and columns another channel already serves", len(covered), 2)
    chk("...cells: 8 in reach + 4 covered", (sum(len(cols[c]["cells"]) for c in in_reach),
                                             sum(len(cols[c]["cells"]) for c in covered)), (8, 4))
    print("   THE 12, BY COLUMN, WITH BOTH DEPTH SETS -- the 8/4 split is `incumbent == EMPTY`, an"
          " EXACT predicate, not the prose 'cells another channel already covers':")
    for c in sorted(cols):
        v = cols[c]
        print("      ef%03d x%-4d  incumbent %-8s novel %-8s -> %s"
              % (c[0], c[1], sorted(v["inc"]) or "EMPTY", sorted(v["nov"]),
                 "IN CHANNEL A's REACH (was already depth-unknown)" if not v["inc"]
                 else "COVERED by so-uv/so-page -- and A2 REFUSES IT ANYWAY"))
    chk("...and the refusal text states BOTH predicates and picks neither",
        all("STATED PLAINLY" in D.reasons[k]["array-dual-depth"]
            and "TAKES THAT PAGE AWAY" in D.reasons[k]["array-dual-depth"] for k in dual), True)

    # ef184, by name, with both records
    for k in conflict:
        why = D.reasons[k]["array-vs-column-depth"]
        chk("%s states BOTH readings" % D.cid(k),
            "the records this kit has always read bind its column" in why
            and "an entry of a MULTI-PART record binds the same column" in why, True)
        chk("%s names its evidence as identification only" % D.cid(k), "identification only" in why,
            True)
        chk("%s: incumbent {4} vs novel {8}" % D.cid(k),
            (sorted(D.gview.get(k, ())), sorted(D.aview.get(k, ()))), ([4], [8]))
    print("   THE 2 THAT WITHDRAW A PAGE -- ef184 x448 at y256 and y384, the ONLY column in the"
          " corpus satisfying the predicate.  incumbent {4} (a record the kit has ALWAYS read) vs"
          " novel {8} (an entry of a multi-part record).  Both true of the same bytes; the kit states"
          " both and picks neither.")
    for k in conflict:
        print("      %s  %s" % (D.cid(k),
                                D.reasons[k]["array-vs-column-depth"].split(".  ")[0][:220]))
    print("   ⚠ SUBSTITUTION DECLARED: the design quotes a UV-OVERLAP for this column (hx 448..479"
          " vs 448..511).  It is NOT re-derived here and MUST NOT BE: `bound_models` is"
          " incumbent-only BY DESIGN, so the novel model's cover is unreachable through the shipped"
          " code, and rolling a private rasteriser would consume the ORDER clause this rung refuses"
          " to consume.  The UV figure stays a STUDY artifact; what the kit asserts is the two"
          " depths on the same column, which is what the refusal says.")

    # ★ THE FOUR DUAL CLASSES ARE PAIRWISE DISJOINT -> the ladder order is a STATEMENT
    klasses = {"program-dual-depth": set(pdual), "channel-g-dual-depth": set(gdual),
               "array-dual-depth": set(dual), "array-vs-column-depth": set(conflict)}
    names = sorted(klasses)
    pairs = 0
    overlap = 0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            pairs += 1
            overlap += len(klasses[names[i]] & klasses[names[j]])
    chk("hazard-class pairs checked", pairs, PIN["hazard_pairs_checked"])
    chk("★ pairwise overlap across the FOUR dual classes", overlap, PIN["hazard_pairwise_overlap"])
    print("   THE FOUR DUAL CLASSES, PAIRWISE: %d pairs, total overlap %d.  So the ladder's ORDER is"
          " a STATEMENT about which instrument names the cell, never a tie-break: %d program-dual +"
          " %d channel-G-dual + %d array-dual + %d array-vs-column, all disjoint."
          % (pairs, overlap, len(pdual), len(gdual), len(dual), len(conflict)))

    # ★★ THE ADDRESSABILITY COUNTERFACTUAL -- through the SHIPPED code, at the CHANNEL SCOPE.
    # `scenery_surface` gates channel A's whole derivation on `"so-array" in channels` (design A3),
    # so dropping the token from the scope is the exact counterfactual "what if these two classes
    # could not fire?" -- driven through the shipping ladder rather than around it.
    touched = sorted({k[0] for k in dual} | {k[0] for k in conflict})
    # BOTH SIDES RESTRICTED TO THE CONTAINERS THE SCOPED PASS COVERS.  `w2_pages` is walked only
    # where CHANNEL A names a cell (elsewhere the two scopes are identical BY CONSTRUCTION -- A3
    # gates channel A's whole derivation on the token), so comparing it against the whole corpus
    # would count every page in an unwalked container as "gained".
    shipped_in_scope = {k for k in D.pages if k[0] in D.w2_efs}
    lost = sorted(set(D.w2_pages) - shipped_in_scope)
    gained = sorted(shipped_in_scope - set(D.w2_pages))
    lost_in_touched = [k for k in lost if k[0] in touched]
    chk("★ addressability delta on the LICENSED path", -len(lost),
        PIN["addressability_delta_licensed"])
    chk("...and 0 cells gained (a refusal may never ADD a page)", len(gained), 0)
    chk("...every lost cell is one of the two new classes' own",
        len([k for k in lost if D.refusals[k] & {"array-dual-depth", "array-vs-column-depth"}]),
        len(lost))
    chk("...on a NON-EMPTY surface (a vacuous counterfactual proves nothing)",
        len(D.w2_pages) > 0, True)
    # ★ AND THE CENSUS PATH, MEASURED AGAINST THE FROZEN SNAPSHOT rather than against itself.  The
    # census scope can never state a channel-A class (A3), so comparing the census surface with and
    # without the token would be vacuous by construction.  What IS evidence: over the very
    # containers the two new classes touch, the SHIPPED census surface still names exactly the cells
    # the frozen `pages.json` recorded as reader-bearing -- an independent snapshot, taken before
    # this rung existed.
    census_now = {k for k in D.census_pages if k[0] in set(touched)}
    census_frozen = {(r["ef"], r["vram_x"], r["vram_y"]) for r in D.census
                     if r["ef"] in set(touched) and r["n_readers"]}
    chk("...and the CENSUS path loses NOTHING (vs the FROZEN snapshot, on the touched containers)",
        len(census_now ^ census_frozen), PIN["addressability_delta_census"])
    chk("...on a NON-EMPTY census surface there too", len(census_now) > 0, True)
    refused_alt = [k for k in lost if "array-vs-column-depth" in D.refusals[k]]
    chk("the REFUSED softer alternative would have been", -len(refused_alt),
        PIN["addressability_delta_refused_alternative"])
    print("   ★★ THE ADDRESSABILITY COUNTERFACTUAL, run through `scenery_surface` at two CHANNEL"
          " SCOPES (the shipped `LICENSED_CHANNELS` vs the same set with `so-array` removed, which"
          " is exactly 'what if channel A could not speak'):")
    print("      LICENSED path: %d cells lose a page, %d gain one -> delta %d.  By name: %s"
          % (len(lost), len(gained), -len(lost), ", ".join(D.cid(k) for k in lost)))
    print("      CENSUS path  : delta %d -- `CENSUS_CHANNELS` never consults A, so neither class can"
          " fire there (A3's channel-scope gate is the line that makes this true).  Measured against"
          " the FROZEN `pages.json` rather than against the census surface itself, because comparing"
          " a scope with a channel it cannot hold would be vacuous: over the %d touched containers"
          " the shipped census names %d reader-bearing cells and the snapshot names the same %d."
          % (len(census_now ^ census_frozen), len(touched), len(census_now), len(census_frozen)))
    chk("...and the 6 lost cells, BY NAME (so a softened A2 goes red here rather than quietly)",
        sorted(D.cid(k) for k in lost),
        ["ef179.x448_y256", "ef179.x448_y384", "ef184.x448_y256", "ef184.x448_y384",
         "ef186.x576_y256", "ef186.x576_y384"])
    # ★ AND THE COST IS NAMED WHERE IT IS ACTUALLY PAID, not left as an abstraction.  `w6q_gates`
    # selects `ef179 cell.s0.x448_y256` from the CENSUS surface as a class-C PAINT VEHICLE and used
    # to re-resolve it through the LICENSED `texel_page`.  A2's veto withdraws exactly that page.
    # W6b-3i's answer is NOT to re-pin that board and NOT to swallow the refusal: `w6q_gates` now
    # RE-DERIVES the withdrawn set from `scenery_surface(LICENSED_CHANNELS)` and pins it BY NAME, so
    # its census numbers stay measured where W6q measured them (the census scope is byte-identical --
    # `addressability_delta_census` above) while the one cell an author can no longer reach is
    # STATED there.  This assertion is what keeps the two boards' facts attached to each other.
    chk("★ ...and `w6q_gates`' own paint vehicle ef179.x448_y256 is one of them",
        "ef179.x448_y256" in {D.cid(k) for k in lost}, True)
    print("      ** AND THE COST IS NAMED WHERE IT IS PAID: `ef179.x448_y256` is `w6q_gates`' g6b"
          " PAINT VEHICLE -- selected from the CENSUS surface, then re-resolved through the LICENSED"
          " `texel_page`.  A2 withdraws that page.  `w6q_gates` G6b now re-derives the withdrawn set"
          " from the shipped predicate and pins it BY NAME (its census pins are unmoved -- the census"
          " scope is byte-identical), so a DIFFERENT withdrawal turns that board red instead of"
          " aborting it.  The permissiveness regression is NOT confined to the 2 ef184 cells: it"
          " takes a W6q paint vehicle away, and both boards now say so.")
    print("      ** THE REFUSED ALTERNATIVE, PRINTED SO THE CHOICE IS STATED: the softer treatment"
          " -- state the hazard ALONGSIDE on the 4 covered cells and keep their page -- measures"
          " delta %d.  A2 refuses it: a hazard bites hardest exactly where another channel already"
          " covers the cell, and loosening later is cheap while tightening after shipping is not."
          % -len(refused_alt))
    chk("...and lost cells sit only in the containers the two classes name",
        len(lost_in_touched), len(lost))

    # A6: the caveat rides BOTH texts, and both classes are UNADDRESSABLE
    for klass in ("array-dual-depth", "array-vs-column-depth"):
        chk("%r is in the refusal matrix" % klass, klass in RP._REFUSAL_TEXT, True)
        chk("%r is UNADDRESSABLE" % klass, klass in RP._UNADDRESSABLE, True)
        chk("%r blocks EXPORT" % klass, klass in RP._EXPORT_BLOCKING, True)
        chk("★ A6: %r quotes ARRAY_CAVEAT" % klass, DA.ARRAY_CAVEAT in RP._REFUSAL_TEXT[klass], True)
        chk("★ A6: %r quotes THE DEPTH COROLLARY" % klass,
            DA.DEPTH_COROLLARY in RP._REFUSAL_TEXT[klass], True)
    chk("...and neither refused cell has a page",
        len([k for k in dual + conflict if k in D.pages]), 0)


# --------------------------------------------------------------------------- I7
def _spec(blob: bytes, effect: int, row: dict) -> dict:
    """A minimal one-row texel spec against a REAL container, guarded by its own sha.  The row is
    ``enabled = false`` throughout: every rung of the ladder below is decided BEFORE a single PNG is
    opened, which is itself part of the claim -- an author must not have to produce art to be told
    the depth channel refuses."""
    r = dict(row)
    r.setdefault("enabled", False)
    return {"reskin": {"effect": effect, "label": "w6b3i",
                       "expect_sha256": hashlib.sha256(blob).hexdigest(), "texel": [r]}}


def i7_ack_ladder(D: Data) -> None:
    """design sec 6.6 -- **THE ACK LADDER**, driven through `repaint.build` on REAL containers.

    Channel A sits at exactly channel P's tier and its reason to be there is HARSHER: channel P's one
    in-game trial FAILED, channel A has had none it passed.  So the same two-part gate applies -- the
    acknowledgement is the author's judgement, ``expect_bpp`` is the number the kit checks it against,
    and one without the other is a wish.

    ★ **THE VEHICLES ARE CHOSEN FROM THE MEASUREMENT, NOT HARD-CODED**, and printed, so the ladder
    cannot silently end up on a cell where something ELSE supplies the refusal.  And rung (8) runs on
    a **class-C** cell -- 34 of the 65, the MAJORITY population a clean vehicle cannot exercise.
    """
    print("[I7] THE ACK LADDER -- every rung failing BY NAME, on the real build path")
    _ACK = DA.ACK_ARRAY_KEY
    gain = D.by_source("so-array", D.ack_pages)
    clean = sorted(k for k in gain
                   if not D.ack_refusals[k]
                   and not D.ack_pages[k].hazards.multi_palette
                   and D.ack_pages[k].clut_offset is not None)
    classc = sorted(k for k in gain if D.ack_pages[k].hazards.multi_palette)
    dual = D.refused_of("array-dual-depth")
    conflict = D.refused_of("array-vs-column-depth")
    chk("a CLEAN channel-A vehicle exists", len(clean) > 0, True)
    chk("a CLASS-C channel-A vehicle exists", len(classc) > 0, True)
    chk("an ARRAY-DUAL vehicle exists", len(dual) > 0, True)
    chk("an ARRAY-vs-COLUMN vehicle exists", len(conflict) > 0, True)
    if not (clean and classc and dual and conflict):
        return
    V, VC, VD, VX = clean[0], classc[0], dual[0], conflict[0]
    BL = {ef: _blob(ef) for ef in {V[0], VC[0], VD[0], VX[0]}}
    vname = D.ack_pages[V].name
    vbpp = D.ack_pages[V].bpp
    cname = D.ack_pages[VC].name
    cbpp = D.ack_pages[VC].bpp
    dname = D.ref_names[VD]
    print("   VEHICLES, CHOSEN FROM THE MEASUREMENT: clean %s (%s, %dbpp) . class-C %s (%s, %dbpp) ."
          " array-dual %s . array-vs-column %s"
          % (D.cid(V), vname, vbpp, D.cid(VC), cname, cbpp, D.cid(VD), D.cid(VX)))

    def refuses(spec, *tokens):
        try:
            RP.build(spec, "w6b3i", blob=BL[spec["reskin"]["effect"]])
        except RP.RepaintError as e:
            missing = [t for t in tokens if t not in str(e)]
            return (True, missing, str(e).splitlines()[0][:120])
        return (False, list(tokens), "BUILT -- no refusal at all")

    # (1) NO ACK -- DISCLOSE means the reason is richer, not that the cell resolves.
    ok, missing, first = refuses(_spec(BL[V[0]], V[0], {"name": vname}),
                                 "CHANNEL A, DISCLOSE", _ACK, "expect_bpp")
    chk("(1) no ack -> refused, and the reason names the key", (ok, missing), (True, []))
    print("   (1) no ack                    REFUSED, and the reason names `%s`" % _ACK)

    # (2) THE ACK ALONE -- a judgement with nothing to check it against.
    ok, missing, first = refuses(_spec(BL[V[0]], V[0], {"name": vname, _ACK: True}),
                                 "states NO `expect_bpp`", "channel-A derivation",
                                 "identification only")
    chk("(2) ack without expect_bpp -> FAILS BY NAME", (ok, missing), (True, []))
    print("   (2) ack, no expect_bpp        FAILS BY NAME: %r" % first)

    # (3) A MISMATCHING expect_bpp -- and the message must name the DERIVATION as channel A's.
    ok, missing, first = refuses(
        _spec(BL[V[0]], V[0], {"name": vname, _ACK: True,
                               "expect_bpp": 4 if vbpp != 4 else 8}),
        "the spec guards", "BINDING ARRAY", "CHANNEL A")
    chk("(3) mismatching expect_bpp -> FAILS BY NAME, naming CHANNEL A", (ok, missing), (True, []))
    print("   (3) ack + WRONG expect_bpp    FAILS BY NAME: %r" % first)

    # (4) THE LITERAL-BOOLEAN LAW (W5's, re-stated at this call site).
    ok, missing, first = refuses(
        _spec(BL[V[0]], V[0], {"name": vname, _ACK: "true", "expect_bpp": vbpp}),
        "must be a BOOLEAN", "never inferred from a truthy string")
    chk("(4) a string 'true' -> REFUSES", (ok, missing), (True, []))
    print("   (4) ack = \"true\" (a string)    REFUSES on the literal-boolean law")

    # (5) A HAZARD OUTRANKS AN ACKNOWLEDGEMENT -- on an ARRAY-DUAL cell.
    ok, missing, first = refuses(
        _spec(BL[VD[0]], VD[0], {"name": dname, _ACK: True, "expect_bpp": 8}),
        "ARRAY-DUAL-DEPTH", "TWO VALUES IS A HAZARD, NOT A VOTE", "no acknowledgement")
    chk("(5) ack on an ARRAY-DUAL cell -> still refuses", (ok, missing), (True, []))
    print("   (5) ack on an ARRAY-DUAL cell STILL REFUSES -- the hazard outranks the ack")

    # (6) ...and on the page-WITHDRAWING class, which is the one that used to resolve.
    xname = D.ref_names[VX]
    ok, missing, first = refuses(
        _spec(BL[VX[0]], VX[0], {"name": xname, _ACK: True, "expect_bpp": 8}),
        "ARRAY-vs-COLUMN-DEPTH", "LICENCE CONTRADICTED BY ITS OWN INSTRUMENT IS VOID",
        "permissiveness regression")
    chk("(6) ack on an ARRAY-vs-COLUMN cell -> still refuses", (ok, missing), (True, []))
    print("   (6) ack on the ef184 pair     STILL REFUSES -- and it says out loud that it is the"
          " rung's ONE deliberate permissiveness regression")

    # (7) THE PAIR resolves, and the page records where the depth came from.
    b = RP.build(_spec(BL[V[0]], V[0], {"name": vname, _ACK: True, "expect_bpp": vbpp}),
                 "w6b3i", blob=BL[V[0]])
    t = b.targets[0]
    chk("(7) the PAIR resolves the page",
        (t.ack_array_depth, t.page.depth_source, t.page.bpp), (True, "so-array", vbpp))
    dis = "  ".join(RP._scenery_disclosures(t))
    chk("(7) ...and the disclosure names the RECORD and SLOT", "record 0x" in dis and "slot " in dis,
        True)
    chk("(7) ...and carries the ORDER clause", DA.ORDER_UNMEASURED[:60] in dis, True)
    chk("(7) ...and the in-game standing, which is NOTHING", DA.ARRAY_CAVEAT[:60] in dis, True)
    chk("(7) ...and, on a lower half, the INHERITANCE clause",
        (DA.INHERITED_LINE in dis) if V[2] % PAGE_LINES else True, True)
    chk("the key is in the FAIL-CLOSED table", _ACK in RP._TEXEL_KEYS, True)
    print("   (7) ack + MATCHING expect_bpp RESOLVES, depth_source=%r bpp=%d -- the author carries"
          " the judgement, the kit carries the check" % (t.page.depth_source, t.page.bpp))

    # (8) ★ THE MAJORITY RUNG -- a CLASS-C cell, 34 of the 65.
    b2 = RP.build(_spec(BL[VC[0]], VC[0], {"name": cname, _ACK: True, "expect_bpp": cbpp}),
                  "w6b3i", blob=BL[VC[0]])
    t2 = b2.targets[0]
    dis2 = "  ".join(RP._scenery_disclosures(t2))
    chk("(8) the CLASS-C rung resolves too", t2.page.depth_source, "so-array")
    chk("(8) ...and DISCLOSES the other renderings", "MULTI-PALETTE (class C)" in dis2, True)
    chk("(8) ...naming each alternate by its own `.as-` file",
        all(("`.as-x%d_y%d.png`" % c) in dis2
            for c in t2.page.hazards.column_clut_cells[1:]), True)
    pmap = RS.palette_map(BL[VC[0]], effect=VC[0])
    rows = RP.alternate_palette_rows(BL[VC[0]], t2.page, pmap)
    chk("(8) ...and an alternate ROW really exists per other key", len(rows),
        len(t2.page.hazards.palette_cells) - 1)
    print("   (8) a CLASS-C cell (%d of the %d) -- resolves AND discloses %d rendering(s), each with"
          " its own read-only `.as-x{X}_y{Y}.png`.  A ladder run only on clean cells cannot see the"
          " MAJORITY of its own channel."
          % (len(classc), len(gain), len(t2.page.hazards.palette_cells)))


# --------------------------------------------------------------------------- I8
#: ★ BENIGN BY NAME, NOT BY A NARROWER GREP.  Two subscripts in the `summons` package really are
#: taken by a value called `part` or `slot`, and NEITHER is the `so` binding array.  Loosening the
#: scan until they stop matching would have made the gate agree with itself; adjudicating them keeps
#: the scan blunt (so a NEW one shows up) and the judgement explicit.  Keyed on the unparsed
#: expression rather than a line number, so a re-indent cannot silently retire an exemption -- and
#: the gate asserts every key still MATCHES, so a stale exemption is red too.
_ORDER_ADJUDICATED: Dict[str, str] = {
    "camera.py :: cont.chunks[slot]":
        "the CONTAINER's chunk slot -- an index into the container header's chunk list, not into "
        "any binding array.  `Binding.chunk_slot` is this same number and W6b-3 did not touch it.",
    "build.py :: v_offsets[part]":
        "the id-4 CREATURE model package's PARALLEL ARRAYS (container.py's `+0x18 u16[partCount] "
        "TPAGE / +0x24 CLUT / +0x30 V-offset`), indexed by the primitive's part byte.  A DIFFERENT "
        "structure from the `so` record, on the creature lane, whose index mapping predates this "
        "rung -- and it is exactly the structure whose SPLIT layout w6b3 scored as the control and "
        "rejected for the `so` record.  Naming it here is what keeps the two from being confused.",
}


def i8_order_not_shipped(D: Data) -> None:
    """★ **THE ORDER CLAUSE IS NOT SHIPPED -- a STRUCTURAL assertion, not a statistic.**

    The record's array has a measured ARITY and an UNMEASURED ORDER.  Every claim in this rung is a
    SET claim, and the way to prove that is not to grep for a caveat but to prove no module can
    consume the order: **no kit module indexes a UV box, a cover or a cell by a part/slot value.**
    An AST scan over the whole ``summons`` package is the instrument.

    The withheld refinement is named too, because the honest form of "we do not ship this" is a
    sentence, not an absence: the recon's *5 DIRECT READS* and its 4-cell cast shortlist are both
    computed by indexing a part's UV box with that slot's own index, so both stay STUDY-only.
    """
    print("[I8] THE ORDER CLAUSE IS NOT SHIPPED -- proved structurally over the summons package")
    pkg = os.path.join(_REPO, "ff9mapkit", "ff9mapkit", "summons")
    files = sorted(glob.glob(os.path.join(pkg, "*.py")))
    chk("summons modules scanned", len(files) > 5, True)
    hits: List[str] = []

    def _names(node) -> List[str]:
        out = []
        for n in ast.walk(node):
            if isinstance(n, ast.Name):
                out.append(n.id)
            elif isinstance(n, ast.Attribute):
                out.append(n.attr)
        return out

    adjudicated: List[str] = []
    for p in files:
        base = os.path.basename(p)
        with open(p, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Subscript):
                continue
            if not any(nm in ("part", "slot", "nparts") or nm.endswith("_part")
                       for nm in _names(node.slice)):
                continue
            src = ast.unparse(node)
            key = "%s :: %s" % (base, src)
            if key in _ORDER_ADJUDICATED:
                adjudicated.append(key)
            else:
                hits.append("%s:%d  %s" % (base, node.lineno, src))
    chk("★ kit subscripts taken by a part/slot INDEX, UNADJUDICATED", len(hits),
        PIN["order_subscripts"])
    chk("...and every adjudication in the list is still LIVE (a dead entry is a stale exemption)",
        sorted(set(adjudicated)), sorted(_ORDER_ADJUDICATED))
    if hits:
        for h in hits[:8]:
            print("      !! %s" % h)
    print("   %d modules scanned by AST: %d UNADJUDICATED subscripts indexed by a `part`/`slot`"
          " value.  The `so` binding array is consumed as a SET everywhere, so no verdict can depend"
          " on which entry came first." % (len(files), len(hits)))
    for key in sorted(adjudicated):
        print("      ADJUDICATED, NOT SILENT -- %s : %s" % (key, _ORDER_ADJUDICATED[key]))
    chk("...and `so_record`'s ONE positional read is documented as a COMPATIBILITY VIEW",
        "COMPATIBILITY VIEW" in RS.so_record.__doc__ and "entry 0" in RS.so_record.__doc__, True)
    print("   ...and the one positional read that DOES exist -- `so_record`'s `tpage`/`clut`"
          " compatibility view of entry 0 -- is documented as such and PROVEN un-consumed by I8b:"
          " permuting the array moves those two keys and moves NO verdict.")

    # ...and no channel-A string may assert a part -> entry mapping.
    strings = [RP._REFUSAL_TEXT["array-dual-depth"], RP._REFUSAL_TEXT["array-vs-column-depth"],
               RP._DEPTH_DERIVED_BY["so-array"], DA.ORDER_UNMEASURED, DA.ARRAY_CAVEAT,
               DA.ARRAY_ACK_WARNING]
    chk("no channel-A string asserts that part k draws with entry k",
        len([s for s in strings if re.search(r"part \d+ .{0,20}entry \d+", s)]), 0)
    chk("`_DEPTH_DERIVED_BY['so-array']` states the ORDER is unmeasured",
        "UNMEASURED" in RP._DEPTH_DERIVED_BY["so-array"], True)
    chk("★ A7.m2: ...and ends on the registration clause's parity line",
        "a BINDING is not a DRAW" in RP._DEPTH_DERIVED_BY["so-array"], True)
    chk("every reason that names a slot calls it identification",
        len([s for s in strings if "slot" in s and "identification" not in s.lower()]), 0)
    chk("`_DEPTH_DERIVED_BY` covers every source (else `assert_expect_bpp` raises KeyError)",
        set(RP._DEPTH_DERIVED_BY) == set(RP.DEPTH_SOURCES), True)
    print("   ...and the strings agree with the structure: `_DEPTH_DERIVED_BY['so-array']` states the"
          " order is UNMEASURED and closes on '…and a BINDING is not a DRAW'; every reason that"
          " names a `record 0x… slot N` calls it IDENTIFICATION ONLY.")
    print("   ⚠ THE OPEN QUESTION, RE-PRINTED RATHER THAN RESOLVED (W6b-3's own statistic, inherited"
          " and NOT re-measured here): the best available order discriminator scores identity 63.3 %"
          " / reversed 56.0 % / random permutations 59.4 %, ~0.9 sigma above chance.  82 of the 126"
          " novel records name more than one distinct tpage, so an arbitrary pick would"
          " mis-attribute the majority of them.")
    print("   ⚠ AND WHAT IS DELIBERATELY WITHHELD: the recon's 5 DIRECT READS and its 4-cell cast"
          " shortlist are computed by indexing a part's UV box with that slot's own index -- they"
          " CONSUME the unmeasured clause, so they stay STUDY-only.  An error running into false"
          " modesty is a defect; shipping a correction on unmeasured evidence is a worse one.")


# --------------------------------------------------------------------------- I8b
def i8b_permutation(D: Data) -> None:
    """★★ **PERMUTATION INVARIANCE -- the order clause proven UN-CONSUMED, not merely un-grepped.**

    I8 proves no module *indexes* by a part value.  This proves the stronger thing: with
    `so_record` monkeypatched **in memory** to hand back each record's ``parts`` in a seeded random
    PERMUTATION, every verdict-bearing output of the shipped path is **bit-identical**.

    ★ **AND THERE IS NO DISPLAY-BINDER CARVE-OUT** (addendum A4).  The design's first form allowed
    the *display* pick to vary and merely counted how often; A4 replaced the sort key with one taken
    on VALUES -- ``(geom, tpage, clut_word)`` -- which ties only between IDENTICAL values, where the
    pick is immaterial by construction.  So the display pick is asserted invariant too, and a
    non-zero count here is a red gate rather than a footnote.

    SCOPE, STATED: the re-run covers the containers holding at least one ``P >= 2`` record.  Everywhere
    else a permutation of a 0- or 1-element list is the IDENTITY, so those containers cannot differ --
    that is a proof, not a sample, and the population is printed.

    Read-only throughout: no bytes are written, nothing is committed, and the patch is reverted in a
    ``finally``.
    """
    print("[I8b] PERMUTATION INVARIANCE -- every verdict-bearing output, display pick INCLUDED")
    efs = sorted(D.p2_efs)
    chk("containers holding at least one multi-part record", len(efs) > 0, True)
    ident_re = re.compile(r"record 0x[0-9a-f]+ slot \d+")
    real = RS.so_record

    def permuted(seed: int):
        rng = random.Random(seed)

        def _wrapped(blob, geom_base):
            rec = real(blob, geom_base)
            if rec is None or len(rec.get("parts", ())) < 2:
                return rec
            parts = list(rec["parts"])
            rng.shuffle(parts)
            rec = dict(rec)
            rec["parts"] = parts
            rec["tpage"], rec["clut"] = parts[0]        # the COMPAT VIEW moves with the array
            return rec
        return _wrapped

    verdict_bad: List[str] = []
    depth_bad: List[str] = []
    class_bad: List[str] = []
    pick_bad: List[str] = []
    key_bad: List[str] = []
    moved = 0
    try:
        for seed in (1, 2):
            RS.so_record = permuted(seed)
            for ef in efs:
                blob = _blob(ef)
                # (a) the PALETTE verdicts -- modulo the identification clause, which is by
                #     definition identification and not a verdict.
                pm = RS.palette_map(blob, effect=ef)
                for pal in pm.palettes:
                    if pal.slot < 0:
                        continue
                    k = (ef, pal.name)
                    got = (pal.shared, ident_re.sub("<ident>", pal.shared_reason),
                           tuple(pal.binders or ()))
                    if k not in _PERM_BASE["verdict"]:
                        continue
                    if got != _PERM_BASE["verdict"][k]:
                        verdict_bad.append("ef%03d %s" % (ef, pal.name))
                # (b) CHANNEL G and CHANNEL A, depth AND display pick
                for cell, pd in RS.page_depth_view(blob).items():
                    k = (ef, cell[0], cell[1])
                    b = pd.binding
                    if (pd.depths, (b.geom, b.tpage, b.clut_word) if b else ()) != \
                            (D.gview.get(k), D.gbind.get(k)):
                        depth_bad.append("G " + D.cid(k))
                for cell, pd in RS.array_depth_view(blob).items():
                    k = (ef, cell[0], cell[1])
                    b = pd.binding
                    if pd.depths != D.aview.get(k):
                        depth_bad.append("A " + D.cid(k))
                    if ((b.geom, b.tpage, b.clut_word) if b else ()) != D.abind.get(k):
                        pick_bad.append(D.cid(k))
                # (c) the SURFACE: refusal class per cell, and the page's own verdict fields
                pages, refused = RP.scenery_surface(blob, ef, channels=RP.LICENSED_CHANNELS,
                                                    array_depth=True)
                got_pg = {(ef, p.cell[0], p.cell[1]): (p.depth_source, p.bpp, p.tpage, p.clut,
                                                       p.clut_offset, p.clut_entries,
                                                       p.palette_name)
                          for p in pages}
                got_kl = defaultdict(set)
                for r in refused:
                    got_kl[(ef, r.cell[0], r.cell[1])].add(r.klass)
                got_keys = {(ef, p.cell[0], p.cell[1]):
                            frozenset(p.hazards.column_clut_cells) for p in pages}
                # compared as WHOLE dicts restricted to this container, so a cell that LOSES a page
                # or a refusal is caught as loudly as one whose values move.
                base_pg = {k: v for k, v in _PERM_BASE["page"].items() if k[0] == ef}
                base_kl = {k: set(v) for k, v in _PERM_BASE["klass"].items() if k[0] == ef}
                base_keys = {k: v for k, v in _PERM_BASE["keys"].items() if k[0] == ef}
                for k in set(base_pg) | set(got_pg):
                    if base_pg.get(k) != got_pg.get(k):
                        class_bad.append(D.cid(k))
                for k in set(base_kl) | set(got_kl):
                    if base_kl.get(k, set()) != set(got_kl.get(k, set())):
                        class_bad.append(D.cid(k))
                for k in set(base_keys) | set(got_keys):
                    if base_keys.get(k) != got_keys.get(k):
                        key_bad.append(D.cid(k))
                moved += 1
    finally:
        RS.so_record = real

    chk("★ palette verdicts differing under permutation", len(set(verdict_bad)),
        PIN["perm_verdict_differs"])
    chk("★ channel G / channel A depths differing", len(set(depth_bad)), PIN["perm_depth_differs"])
    chk("★ refusal class or emitted page differing", len(set(class_bad)), PIN["perm_class_differs"])
    chk("★ class-C key SETS differing", len(set(key_bad)), 0)
    chk("★★ A4: the DISPLAY BINDER pick differing -- NO CARVE-OUT", len(set(pick_bad)),
        PIN["perm_display_pick_differs"])
    print("   %d container-runs (%d containers x 2 seeds) with every multi-part record's binding"
          " array SHUFFLED in memory:" % (moved, len(efs)))
    print("      palette verdicts       %d differ   (modulo the `record 0x… slot N` identification"
          " clause, which is identification and not a verdict)" % len(set(verdict_bad)))
    print("      channel G / A depths   %d differ" % len(set(depth_bad)))
    print("      emitted page + refusal %d differ" % len(set(class_bad)))
    print("      class-C key SETS       %d differ" % len(set(key_bad)))
    print("      ★★ DISPLAY BINDER pick %d differ -- A4 removed the design's carve-out here: the"
          " sort key is taken on VALUES (geom, tpage, clut_word), so it ties only between IDENTICAL"
          " values and the pick cannot depend on storage order.  A non-zero count is RED."
          % len(set(pick_bad)))
    print("   SCOPE, STATED: %d of %d containers hold a multi-part record.  A permutation of a 0- or"
          " 1-element list is the IDENTITY, so the other %d cannot differ -- that is a proof about"
          " the input, not a sample." % (len(efs), len(D.paths), len(D.paths) - len(efs)))


#: I8b's baseline, captured from the UNPATCHED shipped path -- filled by `_perm_baseline` before the
#: permutation runs so the comparison is against a real run rather than against `Data`'s summaries.
_PERM_BASE: Dict[str, dict] = {"verdict": {}, "page": {}, "klass": defaultdict(set), "keys": {}}


def _perm_baseline(D: Data) -> None:
    ident_re = re.compile(r"record 0x[0-9a-f]+ slot \d+")
    for ef in sorted(D.p2_efs):
        blob = _blob(ef)
        pm = RS.palette_map(blob, effect=ef)
        for pal in pm.palettes:
            if pal.slot < 0:
                continue
            _PERM_BASE["verdict"][(ef, pal.name)] = (
                pal.shared, ident_re.sub("<ident>", pal.shared_reason),
                tuple(pal.binders or ()))
        pages, refused = RP.scenery_surface(blob, ef, channels=RP.LICENSED_CHANNELS,
                                            array_depth=True)
        for p in pages:
            k = (ef, p.cell[0], p.cell[1])
            _PERM_BASE["page"][k] = (p.depth_source, p.bpp, p.tpage, p.clut, p.clut_offset,
                                     p.clut_entries, p.palette_name)
            _PERM_BASE["keys"][k] = frozenset(p.hazards.column_clut_cells)
        for r in refused:
            _PERM_BASE["klass"][(ef, r.cell[0], r.cell[1])].add(r.klass)


# --------------------------------------------------------------------------- I9
def _channel_g_disclosure(D: Data) -> List[str]:
    """The lines an author is shown on a real CHANNEL-G build -- rendered through the SHIPPED
    ``_scenery_disclosures`` on a real corpus cell, never asserted against the source string."""
    for k in sorted(D.by_source("so-page")):
        pg = D.pages[k]
        t = RP.TexelTarget(name=pg.name, enabled=False, source="", page=pg)
        return list(RP._scenery_disclosures(t))
    return []                                                    # pragma: no cover - fixture drift


def i9_rederivation_pin(D: Data) -> None:
    """★ **THE RE-DERIVATION PIN THE HOUSE LAW DEMANDS** (addendum A5).

    ``depth_attribution.py``'s ``assert GAIN_PROGRAM + GAIN_SO_PAGE == GAIN_EITHER == 246`` is
    **self-consistent, and therefore structurally incapable of noticing that 57 had gone wrong**.  So
    are ``CHANNEL_G_DUAL_CELLS`` and ``REFUSED_AMBIGUOUS``.  Those are hand-authored fact tables
    defeating their own guard-rail by construction -- exactly what this codebase forbids, sitting in
    the module this rung edits.  Under this design none of them MOVES, which is precisely why the
    repair lands now, while they are still correct and the fix is cheap.

    ★ **AND ALL FIVE NEW CONSTANTS SHIP RE-DERIVED** -- ``GAIN_ARRAY``, ``ARRAY_MULTIVALUED_CELLS``,
    ``ARRAY_IN_REACH_DUAL``, ``ARRAY_COLUMN_CONFLICT_CELLS``, ``ARRAY_CLASS_C``, ``ARRAY_CLEAN``.
    *A constant nobody re-checks is a claim.*

    ⚠ **TWO SCOPES, BOTH PRINTED, NEITHER RECONCILED** -- the `w6b2i_gates` I1 precedent.  The W6b-2
    constants describe the surface `LICENSED_CHANNELS` emitted BEFORE channel A joined it, and A2's
    uniform refusal MOVED that surface by exactly the -6 cells I6 measures plus the cells the two new
    classes rename.  So they are re-derived at the **W6b-2 channel scope**, where they are exact, and
    the SHIPPED default's own figures are pinned beside them with the delta DERIVED rather than
    excused.  A number that no longer describes the surface it is printed on is a STALE STRING, and
    this gate is where that gets said out loud instead of noticed three rungs later.
    """
    print("[I9] THE RE-DERIVATION PIN -- every count constant rolled again from the containers")
    # ---- SCOPE 1: the W6b-2 channel scope, where the W6b-2 constants are exact ----------------
    # `w2_*` covers only the CHANNEL-A containers; everywhere else the two scopes are identical by
    # construction (A3 gates channel A's whole derivation on the token), so the shipped totals carry
    # the rest.  That identity is asserted rather than assumed.
    untouched_pages = {k: p for k, p in D.pages.items() if k[0] not in D.w2_efs}
    untouched_ref = {k: v for k, v in D.refusals.items() if k[0] not in D.w2_efs}
    w2_souv = len([k for k, p in untouched_pages.items() if p.depth_source == "so-uv"]) \
        + len([k for k, p in D.w2_pages.items() if p.depth_source == "so-uv"])
    w2_sopage = len([k for k, p in untouched_pages.items() if p.depth_source == "so-page"]) \
        + len([k for k, p in D.w2_pages.items() if p.depth_source == "so-page"])
    w2_dark = len([k for k, v in untouched_ref.items() if "depth-unknown" in v]) \
        + len([k for k, v in D.w2_refusals.items() if "depth-unknown" in v])
    w2_gdual = len([k for k, v in untouched_ref.items() if "channel-g-dual-depth" in v]) \
        + len([k for k, v in D.w2_refusals.items() if "channel-g-dual-depth" in v])
    w2_pdual = len([k for k, v in untouched_ref.items() if "program-dual-depth" in v]) \
        + len([k for k, v in D.w2_refusals.items() if "program-dual-depth" in v])
    w2_spill = len([k for k, v in untouched_ref.items() if "spill-vs-own-page" in v]) \
        + len([k for k, v in D.w2_refusals.items() if "spill-vs-own-page" in v])
    chk("(W6b-2 scope) `so-uv`", w2_souv, PIN["so_uv_cells"])
    chk("(W6b-2 scope) GAIN_SO_PAGE, re-rolled", w2_sopage, DA.GAIN_SO_PAGE)
    chk("(W6b-2 scope) CHANNEL_G_DUAL_CELLS, re-rolled", w2_gdual, DA.CHANNEL_G_DUAL_CELLS)
    chk("(W6b-2 scope) REFUSED_AMBIGUOUS, re-rolled", w2_pdual + w2_gdual + w2_spill,
        DA.REFUSED_AMBIGUOUS)
    chk("(W6b-2 scope) depth-unknown", w2_dark, PIN["w6b2_scope_depth_unknown"])
    chk("(W6b-2 scope) GAIN_EITHER closes", w2_sopage + DA.GAIN_PROGRAM, DA.GAIN_EITHER)
    chk("(W6b-2 scope) ...and so does 2,385 - 246 == 2,139", DA.DEPTH_UNKNOWN - DA.GAIN_EITHER,
        DA.RESIDUE)
    print("   SCOPE 1 -- the W6b-2 CHANNEL SCOPE %s: so-uv %d . GAIN_SO_PAGE %d . CHANNEL_G_DUAL %d"
          " . REFUSED_AMBIGUOUS %d . depth-unknown %d.  Every W6b-2 constant re-rolled FROM THE"
          " CONTAINERS and equal to the module's own -- the self-consistent `%d + %d == %d` assert"
          " could never have caught its own drift, and now something else can."
          % (str(W6B2_CHANNELS), w2_souv, w2_sopage, w2_gdual,
             w2_pdual + w2_gdual + w2_spill, w2_dark, DA.GAIN_PROGRAM, DA.GAIN_SO_PAGE,
             DA.GAIN_EITHER))

    # ---- SCOPE 2: the SHIPPED default, which A2 moved -----------------------------------------
    s_souv = len(D.by_source("so-uv"))
    s_sopage = len(D.by_source("so-page"))
    s_dark = len(D.refused_of("depth-unknown"))
    chk("(SHIPPED default) `so-uv`", s_souv, PIN["shipped_so_uv"])
    chk("(SHIPPED default) `so-page`", s_sopage, PIN["shipped_so_page"])
    chk("(SHIPPED default) depth-unknown", s_dark, PIN["shipped_depth_unknown"])
    chk("★ THE DELTA IS DERIVED, NOT EXCUSED: the two scopes differ by exactly A2's withdrawal",
        (w2_souv - s_souv) + (w2_sopage - s_sopage), -PIN["addressability_delta_licensed"])
    chk("...and every cell the shipped scope no longer calls depth-unknown is one of the 12 + 2",
        w2_dark - s_dark, PIN["stale_string_delta"])
    stated = re.search(r"DEPTH-UNKNOWN \(([\d,]+) cells", RP.W6B_REASON)
    stated_n = int(stated.group(1).replace(",", "")) if stated else -1
    chk("`W6B_REASON`'s stated depth-unknown == the W6b-2 SCOPE's derivation", stated_n, w2_dark)
    print("   SCOPE 2 -- the SHIPPED `LICENSED_CHANNELS`: so-uv %d . so-page %d . depth-unknown %d."
          "  The two scopes differ by exactly A2's uniform refusal: %d cells lose a page (%d so-uv +"
          " %d so-page) and %d cells that WERE depth-unknown now refuse under the sharper name."
          % (s_souv, s_sopage, s_dark, (w2_souv - s_souv) + (w2_sopage - s_sopage),
             w2_souv - s_souv, w2_sopage - s_sopage, w2_dark - s_dark))
    # ★ AND THE STALE-STRING FINDING IS DISCHARGED, NOT MERELY NAMED.  The counts do not move --
    # channel A is DISCLOSED, never adopted, so an adopted count may not absorb it, and whether A2's
    # uniform refusal is permanent is an owner ratification.  What they owed the reader was their
    # SCOPE, and `DA.A2_SCOPE_NOTE` is that clause: derived from the channel's own re-derivation-
    # pinned constants (never fresh literals) and quoted at both sites an author actually reads.
    chk("★ the scope clause exists and is spelled from the pinned constants",
        (str(DA.ARRAY_COLUMN_CONFLICT_CELLS + (DA.ARRAY_MULTIVALUED_CELLS - DA.ARRAY_IN_REACH_DUAL))
         in DA.A2_SCOPE_NOTE and "DISCLOSED, NEVER ADOPTED" in DA.A2_SCOPE_NOTE), True)
    chk("...and its withdrawal figure IS the measured addressability delta",
        DA.ARRAY_COLUMN_CONFLICT_CELLS + (DA.ARRAY_MULTIVALUED_CELLS - DA.ARRAY_IN_REACH_DUAL),
        -PIN["addressability_delta_licensed"])
    chk("★ `W6B_REASON` carries it -- the string `texel_page` hands an author on every unknown name",
        DA.A2_SCOPE_NOTE in RP.W6B_REASON, True)
    chk("★ ...and so does the CHANNEL-G build disclosure, which prints on every so-page build",
        any(DA.A2_SCOPE_NOTE in ln for ln in _channel_g_disclosure(D)), True)
    print("   ★ THE SCOPE CLAUSE, NOT A RESTATEMENT: `repaint.W6B_REASON` still quotes %d"
          " depth-unknown cells and `depth_attribution.RESIDUE_LINE` / `GAIN_EITHER` still describe"
          " %d gained -- EXACT at the W6b-2 scope above -- and both now carry `A2_SCOPE_NOTE`, which"
          " states the -%d/+%d delta on the path an author walks and says in the same breath that"
          " channel A is DISCLOSED, NEVER ADOPTED.  Moving the numbers would bank a ratification"
          " nobody has made; leaving them unscoped was the stale string."
          % (stated_n, DA.GAIN_EITHER, -PIN["addressability_delta_licensed"],
             PIN["stale_string_delta"]))

    # ---- ★ A5: all five NEW constants, re-derived -------------------------------------------
    chk("★ GAIN_ARRAY, re-rolled", len(D.by_source("so-array", D.ack_pages)), DA.GAIN_ARRAY)
    dual = D.refused_of("array-dual-depth")
    chk("★ ARRAY_MULTIVALUED_CELLS, re-rolled", len(dual), DA.ARRAY_MULTIVALUED_CELLS)
    chk("★ ARRAY_IN_REACH_DUAL, re-rolled", len([k for k in dual if not D.gview.get(k)]),
        DA.ARRAY_IN_REACH_DUAL)
    chk("★ ARRAY_COLUMN_CONFLICT_CELLS, re-rolled", len(D.refused_of("array-vs-column-depth")),
        DA.ARRAY_COLUMN_CONFLICT_CELLS)
    gain = D.by_source("so-array", D.ack_pages)
    cc = [k for k in gain if len(D.ack_pages[k].hazards.column_clut_cells) > 1]
    pw = [k for k in gain
          if D.C.get(k) and (D.C[k]["hz_program_write"] or D.C[k]["hz_program_write_here"])]
    chk("★ ARRAY_CLASS_C, re-rolled", len(cc), DA.ARRAY_CLASS_C)
    chk("★ ARRAY_PROGRAM_WRITE, re-rolled", len(pw), DA.ARRAY_PROGRAM_WRITE)
    chk("★ ARRAY_DEFLATION_OVERLAP, re-rolled", len(set(cc) & set(pw)), DA.ARRAY_DEFLATION_OVERLAP)
    chk("★ ARRAY_CLEAN, re-rolled", len([k for k in gain if k not in set(cc) and k not in set(pw)]),
        DA.ARRAY_CLEAN)
    chk("...and `ARRAY_RESIDUE_LINE`'s own three buckets close against the same derivation",
        DA.ARRAY_CLEAN + DA.ARRAY_CLASS_C + DA.ARRAY_PROGRAM_WRITE - DA.ARRAY_DEFLATION_OVERLAP,
        DA.GAIN_ARRAY)
    chk("...and the module's own import-time arithmetic still closes",
        DA.GAIN_EITHER + DA.RESIDUE_BLIND + DA.RESIDUE_COVERED, DA.DEPTH_UNKNOWN)
    print("   ★ A5 -- ALL FIVE NEW COUNT CONSTANTS RE-DERIVED FROM THE CONTAINERS: GAIN_ARRAY %d ."
          " ARRAY_MULTIVALUED_CELLS %d . ARRAY_IN_REACH_DUAL %d . ARRAY_COLUMN_CONFLICT_CELLS %d ."
          " ARRAY_CLASS_C %d . ARRAY_CLEAN %d.  No new constant ships un-re-derived."
          % (DA.GAIN_ARRAY, DA.ARRAY_MULTIVALUED_CELLS, DA.ARRAY_IN_REACH_DUAL,
             DA.ARRAY_COLUMN_CONFLICT_CELLS, DA.ARRAY_CLASS_C, DA.ARRAY_CLEAN))
    print("   ...and `ARRAY_IN_REACH_DUAL` keeps its name under A2 ON PURPOSE: the 8/4 split is the"
          " DERIVATION of the class, printed because it is informative, while the TREATMENT is"
          " uniform.  A constant named after a policy that changed would be a lie in a docstring.")
    chk("★ RESIDUE_LINE is UNCHANGED (channel A is DISCLOSED, never ADOPTED)",
        DA.RESIDUE_LINE.count("{:,}".format(DA.RESIDUE)) >= 1, True)
    chk("...and ARRAY_RESIDUE_LINE is a SECOND line, never reconciled with it",
        "{:,}".format(DA.RESIDUE - DA.GAIN_ARRAY) in DA.ARRAY_RESIDUE_LINE, True)


# --------------------------------------------------------------------------- I10
def i10_census_freeze(D: Data) -> None:
    """design sec 9 -- **THE CENSUS ARTIFACT IS FROZEN, AND THE FREEZE IS VERIFIED.**

    ``texel-w6b/census/pages.json`` is NOT re-stamped.  Three reasons, all stated in the record:
    the kit's census channel (``so-uv``) is deliberately unmoved, so the artifact still describes the
    shipped census EXACTLY; the recon's reach numbers are statements about what the PRE-FIX kit could
    not see, measured against this snapshot, and re-stamping would move the baseline the reach was
    measured against and collapse `w6b3_gates`'s own subject to zero by construction; and the record
    already flags the census delta as only as fresh as this file.

    ⚠ **But a freeze must be CHECKED, or it is just a stale file nobody noticed.**  So the census's
    own reader population is compared against what the SHIPPED, incumbent-narrowed
    ``bound_models`` / ``cell_readers`` produce right now.  If the freeze ever stops describing the
    kit, this says so in that session rather than three rungs later.
    """
    print("[I10] THE CENSUS FREEZE -- not re-stamped, and therefore CHECKED")
    chk("census rows", len(D.census), PIN["census_rows"])
    reader_rows = [r for r in D.census if r["n_readers"]]
    chk("census rows carrying readers", len(reader_rows), PIN["census_reader_rows"])
    chk("...and their total reader count", sum(r["n_readers"] for r in D.census),
        PIN["census_n_readers"])
    chk("rows whose bpp evidence is an `so`-record binding",
        sum(1 for r in D.census if r["bpp_evidence"] == "so-record binding"),
        PIN["census_so_binding_rows"])
    bad: List[str] = []
    for r in reader_rows:
        k = (r["ef"], r["vram_x"], r["vram_y"])
        want = sorted(int(x["geom"]) for x in r["readers"])
        got = D.readers.get(k, [])
        if want != got:
            bad.append(r["id"])
    chk("★ census reader rows the SHIPPED incumbent `cell_readers` does not reproduce", len(bad),
        PIN["census_freeze_mismatch"])
    extra = sorted(k for k, v in D.readers.items() if v and k not in
                   {(r["ef"], r["vram_x"], r["vram_y"]) for r in reader_rows}
                   and k in D.C)
    chk("...and the shipped code names no census cell a reader the snapshot does not", len(extra), 0)
    print("   %d census rows . %d carry readers . %d reader entries in total . %d rows whose depth"
          " evidence is an `so`-record binding" % (len(D.census), len(reader_rows),
                                                   sum(r["n_readers"] for r in D.census),
                                                   PIN["census_so_binding_rows"]))
    print("   THE FREEZE STILL DESCRIBES THE KIT: the SHIPPED `bound_models` -> `cell_readers`"
          " reproduces the snapshot's reader GEOM list on %d/%d rows, and names no extra cell."
          % (len(reader_rows) - len(bad), len(reader_rows)))
    if bad:
        print("   !! rows the shipped code no longer reproduces: %s" % ", ".join(bad[:8]))
    print("   THE DECISION, RECORDED: FREEZE.  `so-uv` is deliberately unmoved (design sec 5.2), so"
          " the artifact is not stale; the reach numbers are measured AGAINST this snapshot, so"
          " re-stamping would move the baseline and make the delta collapse by construction; and"
          " `w6b2_census_restamp.py` is itself narrowed to INCUMBENT so a future re-stamp cannot"
          " silently re-aim it.  A freeze with a stated reason is evidence; one with none is a stale"
          " pin.")


# --------------------------------------------------------------------------- I11
#: BENIGN BY NAME, not by silence.  Nothing this round commits is EXPECTED to match corpus bytes;
#: anything that does is printed with its file and adjudicated here, or the gate is red.
#:
#: ⚠ **THIS DICT IS NOT EMPTY, AND THE DESIGN EXPECTED IT TO BE.**  The two entries are pre-existing
#: benign literals in files this rung's one-line narrowings put inside `git status --porcelain` --
#: they were already adjudicated in `w6b2_gates`/`w6b3_gates` and are inherited verbatim rather than
#: re-argued.  Naming them is the point: an adjudication list that is empty because nothing was
#: scanned is indistinguishable from one that is empty because nothing leaked.
_ADJUDICATED: Dict[bytes, str] = {
    b"\x02\x03\x04\x05\x06\x07": "MIPS load/store opcode tuple in a decoder's is_transfer "
                                 "(w6b2_gates.py's own adjudication, inherited verbatim)",
    b"\x00\x00\x01\x01\x02\x03\x04\x05": "reskin.ID9_SLOT_BIT, the kit's own slot->bit table, "
                                         "asserted in test_reskin.py (same inheritance)",
}


def _changed_files() -> List[str]:
    """ASK GIT, never a hand-written list -- the provenance surface MOVES while a round is judged and
    a concurrent lane's new file must not be silently unscanned."""
    import subprocess
    try:
        out = subprocess.run(["git", "-C", _REPO, "status", "--porcelain"],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception:                                                          # noqa: BLE001
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
    except Exception:                                                          # noqa: BLE001
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
        except Exception:                                                      # noqa: BLE001
            pass
    return out


def i11_provenance(D: Data) -> None:
    """PROVENANCE.  What this rung commits is a DERIVATION -- cell coordinates, depths, record
    offsets, effect ids and counts -- and **never a stock byte, a hex run or a byte-sequence
    literal.**

    The file that could have gone wrong here is a TEST FIXTURE: a multi-part `so` record is easy to
    produce by copying one out of a container.  The house rule is to SYNTHESISE instead --
    ``struct.pack("<HHHH", 0x6F73, 1, 8+8*P, 8+4*P)`` plus invented pairs -- and this gate is what
    makes that rule enforced rather than remembered.  The file list comes from
    ``git status --porcelain`` so a concurrent lane's new file cannot be silently unscanned.
    """
    print("[I11] PROVENANCE -- a derivation, never a stock byte")
    files = [p for p in _changed_files()
             if os.path.splitext(p)[1].lower() in (".py", ".md", ".toml")]
    stockish = [p for p in _changed_files()
                if os.path.splitext(p)[1].lower() in (".bytes", ".png", ".tga", ".bmp", ".dds")]
    chk("stock-shaped assets added to the checkout", len(stockish), PIN["stockish_files"])
    lits: List[Tuple[bytes, str]] = []
    for p in files:
        for lit in _byte_constants(p):
            if len(lit) < 6 or len(set(lit)) < 2:
                continue
            lits.append((lit, os.path.basename(p)))
    hits: Dict[bytes, int] = defaultdict(int)
    for path in D.paths:                       # streamed, so the whole corpus is never resident
        with open(path, "rb") as fh:
            blob = fh.read()
        for lit, _f in lits:
            if lit in blob:
                hits[lit] += 1
    leaks = adj = 0
    for lit, fname in lits:
        n = hits.get(lit, 0)
        if not n:
            continue
        if lit in _ADJUDICATED:
            adj += 1
            print("      %r in %s: in %d containers -- ADJUDICATED BENIGN: %s"
                  % (lit, fname, n, _ADJUDICATED[lit]))
            continue
        leaks += 1
        print("      !! byte literal %r in %s appears in %d corpus containers" % (lit, fname, n))
    chk("unadjudicated byte literals matching corpus data", leaks, PIN["unadjudicated_leaks"])
    print("   %d changed text file(s) scanned, from `git status --porcelain` rather than a list: %s"
          % (len(files), ", ".join(sorted({os.path.basename(f) for f in files}))))
    print("   %d byte-constant candidate(s) of >= 6 non-uniform bytes . %d adjudicated benign BY"
          " NAME . %d unadjudicated leaks . %d stock-shaped files added"
          % (len(lits), adj, leaks, len(stockish)))
    print("   ⚠ THE DESIGN EXPECTED `_ADJUDICATED` TO BE EMPTY AND IT IS NOT -- both entries are"
          " PRE-EXISTING benign literals in files this rung's one-line witness narrowings pulled"
          " into `git status`, inherited verbatim from the boards that already argued them.  Stated"
          " rather than silently filtered.")
    # ...and the lane's own dossiers must resolve OUTSIDE the checkout.
    outside = [os.path.join(W6B, "census", "pages.json"), SCRATCH]
    chk("the corpus and the lane artifacts resolve OUTSIDE the repo",
        all(not os.path.abspath(p).startswith(os.path.abspath(_REPO)) for p in outside), True)
    print("   the corpus (%s) and the census artifact resolve OUTSIDE the checkout; the round"
          " commits coordinates and counts, and the bytes stay where the user's own install put"
          " them." % SCRATCH)


# --------------------------------------------------------------------------- runner
GATES = [
    ("I0", "CALIBRATE -- THE WITNESS PARTITION, tuple for tuple against the frozen reader",
     i0_partition),
    ("I1", "THE READER -- 502/649, arrayB informative on the 126, and the P=0 invariant", i1_reader),
    ("I2", "THE SAFETY FIX -- 148/129/2,395 + A1's GUARDED 301/122, 0 released by the flip "
           "(guard: 46 released / 5 armed)", i2_safety_fix),
    ("I3", "THE FLAGSHIP -- ef381: slot-count and model-count AGREE at 7", i3_flagship),
    ("I4", "THE CONTAINMENT, A/B -- the shipped defaults, then the leak declined", i4_containment),
    ("I5", "CHANNEL A's REACH -- 65 + 8, class C at the DEPTH's granularity", i5_channel_a),
    ("I6", "THE REFUSALS -- A2's uniform 12 + 2, addressability -6 (refused -2 printed)",
     i6_refusals),
    ("I7", "THE ACK LADDER -- 8 rungs, each failing BY NAME, on the real build path", i7_ack_ladder),
    ("I8", "THE ORDER CLAUSE IS NOT SHIPPED -- AST-structural, over the whole package",
     i8_order_not_shipped),
    ("I8b", "PERMUTATION INVARIANCE -- display pick INCLUDED (A4, no carve-out)", i8b_permutation),
    ("I9", "THE RE-DERIVATION PIN -- every constant re-rolled, two scopes printed",
     i9_rederivation_pin),
    ("I10", "THE CENSUS FREEZE -- not re-stamped, and therefore CHECKED", i10_census_freeze),
    ("I11", "PROVENANCE -- a derivation, never a stock byte", i11_provenance),
]


def main(argv=None) -> int:
    # This board's gate NAMES carry the house's own ★ / ⚠ markers, so a cp1252 stdout (which is what
    # a redirect to a file gets on this machine) would raise UnicodeEncodeError INSIDE a gate and
    # report it as a measurement failure.  A gate must fail for what it measured, never for how its
    # output was piped.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                          # noqa: BLE001
        pass
    only = set(a.upper() for a in (argv or sys.argv[1:]) if a.upper().startswith("I"))
    print("W6b-3 INTEGRATION GATES -- the multi-part `so` record, as SHIPPED KIT BEHAVIOUR")
    print("corpus: %s" % SCRATCH)
    print("THE LINE: THE READER FIX IS UNCONDITIONAL.  THE DEPTH DISCLOSES AT CHANNEL P's TIER.")
    print("A1: the 122-palette release is MEASURED and NOT TAKEN.  A2: all 12 array-dual cells "
          "REFUSE.")
    print("=" * 78)
    D = Data()
    _perm_baseline(D)
    board = []
    for tag, title, fn in GATES:
        if only and tag.upper() not in only:
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
    print("=" * 78)
    for tag, title, ok in board:
        print("%-4s %-4s %s" % ("PASS" if ok else "FAIL", tag, title))
    if _FAILS:
        print("-" * 78)
        for f in _FAILS:
            print("  FAIL  %s" % f)
    print("=" * 78)
    print("%d/%d gates pass" % (sum(1 for _, _, ok in board if ok), len(board)))
    return 1 if _FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
