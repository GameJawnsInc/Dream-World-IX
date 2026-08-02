r"""TIER W rungs W6b-3 (iii) DISCLOSED and (iv) ADOPTED -- THE SECOND ARRAY.  `py u1_gates.py` -> U1..U7.

★ A **NEW FILE**, and that is the point.  `w6b_gates` G6, `w6q_gates` G1/G16, `w6b2i_gates` I5 and
`w6b3i_gates` I6/I9 are RE-DERIVATION PINS over populations this rung must not move, so not one line
of them is edited: this board proves the new behaviour beside them, and the acceptance test for the
rung is **green BEFORE == green AFTER** on all four, plus green here.

⚠ AND AT W6b-3 (iv) THAT CLAIM NEEDED AN AMENDMENT, MADE HERE RATHER THAN LEFT TO ROT.  The named
GATES are still untouched -- `w6b_gates` G6's census block is byte-identical before and after the
adoption, which is why the pre-announced `spill_bindings 58 -> 60` was RETRACTED rather than applied
(the two-cover architecture keeps `BoundModel.columns`/`.spills` on the BOUND cover; the EFFECTIVE
count ships as a separate constant).  What DID move in those files is their FIXTURES: `w6b_gates` G4
lost a same-bytes-two-depths cell to the displacement and needed `effective_cover` on a synthetic
ghost, and `w6q_gates` had to roll its withdrawal set at the scope `texel_page` now resolves at.  A
fixture is not a pin, and repairing one is not moving a population -- but "not one line" now means
"not one line OF THOSE GATES", not "not one line of those files".

    U1  THE READER -- `so_record["second"]` against an INDEPENDENT raw walker, 502/649/293
    U2  THE POPULATION -- 52 cells / 29 containers / 47 fully open, re-derivation-pinned
    U3  THE SUPERSET LAW -- the scoping's 16 SWAPPED + 19 ORIGINAL contained, zero missed
    U4  THE CENSUS DEFAULT IS UNMOVED -- the class silent, the field empty, the page set identical
    U5  THE SHIPPED CASTS -- the cast cells clean, the ONE that fires named out loud, and the two
        W6b-3 (ii) ODIN RECORDS proved FROZEN (they hard-fail twice; the ack does not rescue them)
    U6  THE ACK AND THE CONSTANT -- literal boolean, registered key, and NO BYTE MOVES
    U7  THE EFFECTIVE COVER -- the W6b-3 (iv) ADOPTION, re-rolled at `EDIT_CHANNELS` scope

★ AND U7 IS THE ONLY INSTRUMENT IN THE ARC AIMED AT THE SURFACE AN AUTHOR ACTUALLY GETS.  U1..U6 and
every board beside them measure :data:`RP.LICENSED_CHANNELS` -- two of them DERIVE their scope as
`tuple(c for c in RP.LICENSED_CHANNELS if c != "so-array")`, so they will follow the frozen set
forever -- while `texel_page`, `export_art`, `build` and `scenery_lines` all default to
`EDIT_CHANNELS`.  Without U7 the edit surface has exactly ONE re-derivation and it lives in the same
file family as the code it checks.  U7 rolls its own numbers from the 372 containers and compares
them against LITERALS WRITTEN IN THIS FILE: it imports no other board's `PIN`, and it takes no
expectation from `depth_attribution` (it PINS those constants against its own roll, which is the
opposite direction).

★ THE LINE W6b-3 (iii) IMPLEMENTED, AND THE LINE THAT SUPERSEDED IT.  Both are kept: U6's token
ledger pins the retired wording ABSENT, so restoring the old sentence here without restoring it in
the kit would go red -- which is the whole device.

    (iii)  THE SECOND ARRAY IS READ AND DISCLOSED.  NOTHING IS MODELLED WITH IT, AND NO EMITTED
           BYTE MOVES.                                                          -- ★ RETIRED at (iv)
    (iv)   THE SECOND ARRAY IS APPLIED.  THE READER JOIN IS TAKEN ON THE CELL THE HARDWARE SAMPLES,
           EMITTED BYTES MOVE ON THE **EDIT** SURFACE ONLY, AND THE CENSUS AND LICENSED SURFACES
           STAY BYTE-IDENTICAL.

The evidence was MEASURED on ONE container at **0.97** -- U1's s77 byte-stream read of
ef038: the second array is a per-slot texel displacement, **pair position 0 onto `u`, pair position 1
onto `v`**, +128 texels each.  That settled two riders this board was written under (the labelling,
which is the one the kit calls SWAPPED, and the `v` axis), and left five open -- generalisation, the
operation-vs-magnitude, depth, wrap-vs-clamp, and per-slot-only-where-slot-equals-record.  ★ U2's
owner cast then CLOSED generalisation (ef227 + ef446) and the operation (ADD, by a decisive value
test on ef227), and wrap-vs-clamp closed as degenerate; **FOUR riders now ride**, all narrower, and
the one that gates the reach is per-slot-only-where-slot-equals-record -- see
`depth_attribution.U_DISPLACEMENT_CAVEAT`, which is spent at the
refusal, the build gate, the disclosure and the report block -- *a caveat nothing quotes is a wish.*

★ U2's NUMBERS DID NOT MOVE, AND THAT IS THE POINT: the predicate never asked which halfword moves
which axis, so U2's 52 / 29 / 47 are exactly what they were the day before the read -- and they are
still LICENSED-scope numbers after the adoption.  The adoption's own counts are U7's, at EDIT scope.

Reads the extracted corpus at C:\gd\SCRATCH\summon-format ONLY.  No install read, NO deploy, no
install write, no git commit; it writes nothing but its own stdout.  Budget: FOUR rasterising passes
over the 372 containers -- three for `Data` (U1..U6) and one for `Effective` (U7, which memoises
`bound_models` per container so its five channel-scope walks share ONE rasterisation, plus 40 extra
on the ten control containers; see `Effective.CONTROL`).  MEASURED: 586s end to end on this machine,
188s of it U7.  `py u1_gates.py U7` pays for U7's walk only.
"""
from __future__ import annotations

import dataclasses
import glob
import os
import struct
import sys
import time
from typing import Dict, List, Optional, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS_STUDY                                        # noqa: E402  (sets up sys.path)
import summon_camera as W                                        # noqa: E402
from ff9mapkit.summons import container as EC                    # noqa: E402
from ff9mapkit.summons import depth_attribution as DA            # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402
from ff9mapkit.summons import reskin as RS                       # noqa: E402
from ff9mapkit.summons import texture as KT                      # noqa: E402

assert RS_STUDY is not None                                      # the sys.path side effect is the use
SCRATCH = os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format")
CORPUS = W.SCRATCH_CORPUS

#: a VRAM tpage names a 64 x 256 PAGE and a census page-cell is 64 x 128 -- written HERE, from the
#: bit layout, so the pins below do not lean on the same arithmetic the kit uses.
PAGE_HW, CELL_LINES = 64, 128

# --------------------------------------------------------------------------- THE PINS
PIN = {
    "containers": 372,
    # -- U1 THE READER (deliberately NOT imported from `w6b3i_gates.PIN`: two files measuring the
    #    same population independently is the point, and a shared constant makes agreement a tautology)
    "records": 502,
    "slots": 649,
    "p0_records": 36,
    "arrayb_agrees": 502,
    "record_end_is_geom": 502,
    "second_len_equals_p": 502,
    "second_nonzero_slots": 293,
    "independent_agreement": 649,
    # -- U2 THE POPULATION
    "fire_cells": 52,
    "fire_containers": 29,
    "fire_open": 47,
    "fire_program_vram_write": 4,
    "fire_same_bytes_two_depths": 1,
    "incumbent_readers": 340,
    "incumbent_movers": 151,
    "census_so_uv_cells": 187,
    # -- U3 THE SUPERSET LAW
    "lost_swapped": 16,
    "lost_original": 19,
    "lost_union": 35,
    "conservative_extras": 17,
    "rederived_swapped": 16,
    #: ⚠ THE ONE PLACE THE SPAN AND THE SCOPING'S RASTER DIFFER, PINNED RATHER THAN RECONCILED.  The
    #: kit's disclosure derives its effective columns from the reader's `u` SPAN (a displacement term
    #: in `_cover_mark` is Option 3 and is NOT taken), and under the ORIGINAL labelling that names
    #: TWO more cells than the scoping's fully rasterised cover does -- `ef226 (576, 256)` and
    #: `ef227 (512, 256)`.  A SPAN is a WIDER claim, never a wrong one, and both cells are in the
    #: firing set anyway, so the disclosure's reach is unaffected.  Under SWAPPED the two agree
    #: exactly (16 == 16), which is why this delta is a labelled property and not a defect.
    "rederived_original": 21,
    "span_vs_raster_extra": 2,
    # -- U4 THE CENSUS DEFAULT
    "census_class_stated": 0,
    "census_field_nonempty": 0,
    "census_page_diff": 0,
    # -- U5 THE SHIPPED CASTS
    "shipped_clean": 7,
    "shipped_firing": 1,
    #: ⚠ THE OBLIGATION ON THE ARC'S OWN COMMITTED SPECS, SWEPT RATHER THAN TYPED.  Both ef424 cast
    #: specs -- `odin_channel_a.toml` ROW 2 and its cast-C sibling `odin_channel_a_c.toml` ROW 2 --
    #: target the one firing cast cell with `enabled = true`.  Naming only one of them would have been
    #: the same class of omission this whole rung exists to prevent.  ⚠ SWEPT AT LICENSED_CHANNELS:
    #: see `specs_on_firing_cells`, and see the freeze pins below for what the SHIPPED default says.
    "specs_on_the_firing_cell": 2,
    #: ★ THE FREEZE.  Under the adoption NEITHER record builds, and the pin is on WHICH refusal each
    #: hits at each stage -- `displaced-readerless` with no ack, and the palette-is-a-header-fact
    #: refusal once the ack lifts it, because the cell re-sources `so-uv` -> `so-page` and the COLUMN's
    #: own CLUT word is 243 where the departed reader's key was 242.
    "frozen_specs": 2,
    "frozen_specs_that_build": 0,
}

# ------------------------------------------------------------------- U7's PINS, AND ONLY U7's
#: ★ **A SECOND DICT, DELIBERATELY, AND NOTHING READS BOTH.**  U7 measures a DIFFERENT SURFACE from
#: U1..U6 -- :data:`RP.EDIT_CHANNELS`, the one every author-facing entry point defaults to -- through
#: a walk of its own (:class:`Effective`), and the point of the exercise is two independent
#: measurements, not one measurement quoted twice.  So U7 reads no key of :data:`PIN`, no other
#: board's pin dict, and **no constant of `depth_attribution` as an expectation**: every number below
#: is a literal a human can check, and the shipped constants are pinned AGAINST it (U7f), which is the
#: opposite direction of dependency from importing them.
#:
#: ⚠ `incumbent_readers` / `incumbent_movers` appear here AND in :data:`PIN`.  That is not a
#: duplication to be tidied away -- U2 reaches them through `Data`'s walk and U7 through
#: `Effective`'s, and two walks agreeing is evidence where one walk quoted twice is not.
U7_PIN = {
    "containers": 372,
    "skipped": 0,
    # -- U7a THE REACH
    "incumbent_readers": 340,
    "incumbent_movers": 151,
    "novel_records": 126,
    "novel_mover_slots": 142,
    "intra_page_ok": 340,
    "assert_intra_page_raised": 0,
    # -- U7b THE LOSS HALF, and the closure that says 45 and 52 are not addends
    "readerless_cells": 45,
    "readerless_open": 41,
    "readerless_containers": 26,
    "substituted_cells": 7,
    "substituted_open": 6,
    "substituted_containers": 6,
    "vacate_cells": 52,
    "vacate_open": 47,
    "vacate_containers": 29,
    # -- U7c THE GAIN HALF
    "gained_cells": 70,
    "gained_from_unknown": 29,
    "gained_undeclared": 2,
    "gained_containers": 36,
    "vs_page_depth_cells": 1,
    # -- U7d THE CLASS NOBODY HAD NAMED
    "changed_cells": 36,
    #: ⚠ **TWO NUMBERS, AND THE GAP BETWEEN THEM IS THE FINDING** -- see :func:`u7d_changed`.
    #: `DA.DISPLACED_DISPLAY_BINDING_MOVED` is 14 and is documented *"...of which"* under
    #: :data:`DA.DISPLACED_CHANGED_CELLS`, i.e. its population is the 36 CHANGED cells.  The SHIPPED
    #: predicate `CellHazards.display_binding_moved` is NOT scoped to `displaced_changed`, so a roll
    #: of the predicate itself answers **21** -- the 14, plus all 7 SUBSTITUTED cells, whose reader
    #: sets are disjoint and whose display binding therefore always changes hands.  Both are pinned so
    #: neither can drift into the other's name.
    "display_binding_moved_in_changed": 14,
    "display_binding_moved_predicate": 21,
    # -- U7e THE OBLIGATION SET, and the surface totals
    "spill_bound": 58,
    "spill_effective": 60,
    "census_so_uv": 187,
    "licensed_so_uv": 183,
    "edit_so_uv": 199,
    "so_uv_lost": 52,
    "so_uv_gained": 68,
    "so_uv_lost_residual": 0,
    "gained_not_emitted": 2,
    "census_pages": 249,
    "census_refusals": 2487,
    "licensed_pages": 300,
    "licensed_refusals": 2499,
    "edit_pages": 289,
    "edit_refusals": 2453,
    # -- U7g THE CONTAINMENT
    "census_identical": 372,
    "licensed_identical": 372,
    "poison_reads": 0,
    "control_containers": 10,
    "control_models_agree": 10,
    "control_dumps_agree": 30,
}

#: THE SCOPING'S OWN LISTS, transcribed from `REPORT-IMPACT.md` sec 3.1 -- **coordinates, never
#: bytes**.  Written out rather than read from the JSON so this board fails if the artifact moves,
#: and so the reconciliation is against a number a human can check against the report.
LOST_SWAPPED = {
    ("ef038", (640, 384)), ("ef061", (640, 256)), ("ef082", (512, 256)), ("ef082", (512, 384)),
    ("ef179", (704, 256)), ("ef226", (576, 256)), ("ef381", (384, 384)), ("ef384", (448, 256)),
    ("ef384", (448, 384)), ("ef387", (640, 256)), ("ef407", (640, 384)), ("ef424", (448, 384)),
    ("ef447", (384, 384)), ("ef492", (448, 256)), ("ef492", (448, 384)), ("ef499", (448, 256))}
LOST_ORIGINAL = {
    ("ef038", (512, 256)), ("ef082", (640, 256)), ("ef082", (704, 256)), ("ef203", (640, 256)),
    ("ef205", (576, 256)), ("ef206", (512, 256)), ("ef225", (640, 256)), ("ef296", (512, 256)),
    ("ef387", (512, 256)), ("ef405", (448, 256)), ("ef405", (576, 256)), ("ef405", (640, 256)),
    ("ef427", (640, 256)), ("ef438", (576, 256)), ("ef446", (448, 256)), ("ef446", (512, 256)),
    ("ef490", (512, 256)), ("ef502", (576, 256)), ("ef509", (448, 256))}
#: ★ THE DECLARED BLIND SPOT.  These four are readers ONLY through MULTI-PART records, and
#: `bound_models` is incumbent-only, so no predicate in this lane can reach them.  Named here rather
#: than quietly omitted: a kit that listed 52 as "the exposure" would be overstating its own reach.
ALL_SCOPE_ONLY = {("ef155", (448, 384)), ("ef179", (832, 256)),
                  ("ef226", (768, 256)), ("ef226", (832, 256))}
#: ★ THE OWNER'S DECISION, ASSERTED HERE: the two W6b-3 (ii) Odin cast records are FROZEN AS HISTORY.
#: They reproduce only against the PRE-adoption kit and are NOT repaired -- a dated cast record is
#: history in this arc, a superseding note goes at the top of the file, and the record stands.  U5
#: proves the freeze instead of asserting reproduction: both must still PARSE, both must carry the
#: superseding note, and both must HARD-FAIL through the real build path on the cell below.
FROZEN_ODIN_SPECS = ("odin_channel_a.toml", "odin_channel_a_c.toml")
FROZEN_ODIN_CELL = "cell.s0.x448_y384"
#: a token from the superseding note.  Pinned so that DELETING the note is as red as breaking a build.
FREEZE_TOKEN = "FROZEN AS-CAST RECORD"

#: the arc's own cast cells (impact report sec 3.2) -- seven clean, one firing.
SHIPPED_CASTS = {
    ("ef211", (704, 384)), ("ef211", (704, 256)), ("ef211", (576, 384)), ("ef211", (640, 256)),
    ("ef429", (448, 256)), ("ef130", (448, 384)), ("ef424", (704, 384)),
    ("ef424", (448, 384))}

_FAILS: List[str] = []


def chk(name: str, got, want) -> None:
    """Compare a re-measured value against its pin; COLLECT rather than raise, so the whole board
    prints and one red gate cannot hide the state of the others."""
    if got != want:
        _FAILS.append("%s: measured %r, pinned %r" % (name, got, want))


def u16(b: bytes, o: int) -> int:
    return struct.unpack_from("<H", b, o)[0] if 0 <= o <= len(b) - 2 else -1


def specs_on_firing_cells(firing: Set[Tuple[str, Tuple[int, int]]]) -> List[str]:
    """Every COMMITTED `[reskin]` spec in this directory with an ENABLED row on a firing cell.

    ★ SWEPT, NEVER TYPED.  A build gate that fires on the arc's own committed cast records is a
    permissiveness change the OWNER has to decide about -- so the list of specs it touches is DERIVED
    at gate time from the specs themselves rather than transcribed.  A hand-written list is exactly
    how the cast-C sibling gets missed.

    ⚠ RESOLVED AT :data:`RP.LICENSED_CHANNELS`, DELIBERATELY, AND THE REASON IS THE FREEZE.  The
    firing set this identifies specs against is the `second-array-mover` population, which is a
    LICENSED-scope verdict; and the specs being identified are the W6b-3 (ii) Odin cast records, which
    were cast against the pre-adoption kit and are now FROZEN AS HISTORY by owner decision.  At the
    shipped EDIT default those specs' `cell.s0.x448_y384` is `displaced-readerless` and emits no page
    at all, so a sweep there names ZERO specs -- which would read as "the adoption touches none of the
    arc's casts", the exact opposite of the truth.  Resolving at the scope the casts were MADE at is
    what lets this function keep answering the question it was written to answer.  ``u5`` then states
    the freeze separately, and proves it against the SHIPPED default through the real build path.
    """
    import tomllib
    out: List[str] = []
    for path in sorted(glob.glob(os.path.join(_HERE, "*.toml"))):
        with open(path, "rb") as fh:
            try:
                spec = tomllib.load(fh)
            except Exception:                                              # noqa: BLE001
                continue
        rk = spec.get("reskin") or {}
        rows = [t for t in (rk.get("texel") or []) if t.get("enabled")]
        ef = rk.get("effect")
        if not rows or not isinstance(ef, int):
            continue
        blob_path = os.path.join(CORPUS, "ef%03d.bytes" % ef)
        if not os.path.exists(blob_path):
            continue
        with open(blob_path, "rb") as fh:
            blob = fh.read()
        cells = {p.name: p.cell
                 for p in RP.scenery_texel_pages(blob, ef, channels=RP.LICENSED_CHANNELS)}
        for t in rows:
            cell = cells.get(t.get("name"))
            if cell is not None and ("ef%03d" % ef, tuple(cell)) in firing:
                out.append(os.path.basename(path))
                break
    return out


def frozen_spec_verdicts() -> List[Tuple[str, str, str]]:
    """``[(spec, what the SHIPPED kit says with no ack, what it says WITH the ack)]``.

    ★ THE FREEZE, ASSERTED RATHER THAN ANNOUNCED.  The owner froze both Odin cast records as HISTORY:
    they reproduce only against the pre-adoption kit.  A board that merely stopped checking them would
    be silently dropping a check, so this RUNS them -- through the real ``RP.build`` path, at the
    shipped default, against the stock container -- and U5 pins that they refuse TWICE and by which
    names.  If someone ever "repairs" a frozen record, this goes red the same day.
    """
    import tomllib
    out: List[Tuple[str, str, str]] = []
    for name in FROZEN_ODIN_SPECS:
        path = os.path.join(_HERE, name)
        with open(path, "rb") as fh:
            spec = tomllib.load(fh)
        ef = spec["reskin"]["effect"]
        with open(os.path.join(CORPUS, "ef%03d.bytes" % ef), "rb") as fh:
            blob = fh.read()
        verdicts = []
        for ack in (False, True):
            probe = {"reskin": dict(spec["reskin"], texel=[
                dict(t, **({DA.ACK_MOVER_KEY: True} if ack and t.get("name") == FROZEN_ODIN_CELL
                           else {})) for t in spec["reskin"]["texel"]])}
            try:
                RP.build(probe, path, blob=blob)
                verdicts.append("BUILT")
            except RP.RepaintError as e:
                msg = str(e)
                verdicts.append("DISPLACED-READERLESS" if "DISPLACED-READERLESS" in msg
                                else ("PALETTE-IS-A-HEADER-FACT" if "indexes into" in msg
                                      else "OTHER: %s" % msg[:60]))
        out.append((name, verdicts[0], verdicts[1]))
    return out


def eff_cols(page_x: int, u: Tuple[int, int], bpp: int, disp: int) -> Set[int]:
    """The displaced column SPAN, written from the geometry HERE rather than through
    `repaint._effective_columns` -- U1's whole job is to be a second instrument."""
    per = {4: 4, 8: 2, 15: 1}[bpp]
    lo = page_x + (u[0] + disp) // per
    hi = page_x + (u[1] + disp) // per
    return {(x // PAGE_HW) * PAGE_HW for x in range(lo, hi + 1)}


class Data:
    """ONE corpus pass, driven through the SHIPPED derivations plus one INDEPENDENT raw walker."""

    def __init__(self) -> None:
        self.paths = sorted(p for p in glob.glob(os.path.join(CORPUS, "ef*.bytes"))
                            if len(os.path.basename(p)) == 11)
        # ---- U1 the reader
        self.records = self.slots = self.p0 = 0
        self.arrayb_ok = self.rec_end_ok = self.second_len_ok = 0
        self.second_nonzero = 0
        self.agree = 0
        self.disagree: List[str] = []
        self.p0_shape_ok = True
        # ---- U2 the population
        self.fire: Dict[str, Dict[Tuple[int, int], dict]] = {}
        self.fire_open = 0
        self.fire_block: Dict[str, int] = {}
        self.readers = self.movers = 0
        self.census_cells = 0
        # ---- U3 the independent per-labelling derivation
        self.lost: Dict[str, Set[Tuple[str, Tuple[int, int]]]] = {"swapped": set(),
                                                                  "original": set()}
        # ---- U4 the census default
        self.census_class = 0
        self.census_field = 0
        self.page_diff: List[str] = []

        for path in self.paths:
            name = os.path.basename(path)[:-6]
            ef = int(name[2:5])
            with open(path, "rb") as fh:
                blob = fh.read()
            self._records(name, blob)
            try:
                models = RP.bound_models(blob)
                readers = RP.cell_readers(blob, models)
                cells = RS.page_cells(blob)
                pages, refused = RP.scenery_surface(blob, ef, channels=RP.LICENSED_CHANNELS)
                cpages, crefused = RP.scenery_surface(blob, ef)
            except (RS.ReskinError, EC.ContainerError, RP.RepaintError):
                continue                        # a container the kit itself refuses: not this rung's
            self._population(name, models, readers, cells, pages, refused)
            self._census(name, cpages, crefused, pages)

    # ---- U1 -------------------------------------------------------------------------------------
    def _records(self, name: str, blob: bytes) -> None:
        mp = EC.creature_package(blob)
        creature = mp.geom_offset if mp is not None else None
        for g in EC.scan_geom(blob):
            if creature is not None and g.base == creature:
                continue
            rec = RS.so_record(blob, g.base)
            if rec is None:
                continue
            P = rec["nparts"]
            self.records += 1
            self.slots += P
            if P == 0:
                self.p0 += 1
                if rec["second"] != [] or "tpage" in rec or "clut" in rec:
                    self.p0_shape_ok = False
            self.arrayb_ok += int(u16(blob, rec["at"] + 6) == 8 + 4 * P)
            self.rec_end_ok += int(rec["at"] + rec["len"] == g.base)
            self.second_len_ok += int(len(rec["second"]) == P)
            # ★ THE INDEPENDENT WALKER: raw halfwords at `at + 8 + 4P + 4k`, never `rec["second"]`
            for k in range(P):
                base = rec["at"] + 8 + 4 * P + 4 * k
                mine = (u16(blob, base), u16(blob, base + 2))
                if mine == rec["second"][k]:
                    self.agree += 1
                else:
                    self.disagree.append("%s %#x slot %d: %r vs %r"
                                         % (name, rec["at"], k, mine, rec["second"][k]))
                if mine[0] or mine[1]:
                    self.second_nonzero += 1

    # ---- U2 / U3 --------------------------------------------------------------------------------
    def _population(self, name, models, readers, cells, pages, refused) -> None:
        for m in models:
            self.readers += 1
            if m.mover and (m.mover[0] or m.mover[1]):
                self.movers += 1
        declared = {pc.cell for pc in cells.values()}
        by_cell: Dict[Tuple[int, int], Set[str]] = {}
        for r in refused:
            by_cell.setdefault(r.cell, set()).add(r.klass)
        src = {p.cell: p.depth_source for p in pages}
        hits = {c for c, ks in by_cell.items() if "second-array-mover" in ks}
        if hits:
            self.fire[name] = {}
            for c in sorted(hits):
                others = by_cell[c] - {"second-array-mover"}
                block = sorted(others & RP._EXPORT_BLOCKING)
                self.fire[name][c] = {"source": src.get(c), "block": block}
                if not block:
                    self.fire_open += 1
                for b in (block or ["OPEN"]):
                    self.fire_block[b] = self.fire_block.get(b, 0) + 1
        # ---- U3's INDEPENDENT per-labelling roll, from the reader's own u span and v rows
        for cell, ms in readers.items():
            if cell not in declared:
                continue
            for tag, idx in (("swapped", 0), ("original", 1)):
                alive = 0
                for m in ms:
                    mv = m.mover or (0, 0)
                    rows = {cy for (_cx, cy) in m.cover}
                    if cell[0] in eff_cols(m.page[0], m.u, m.bpp, mv[idx]) and cell[1] in rows:
                        alive += 1
                if alive == 0:
                    self.lost[tag].add((name, cell))

    # ---- U4 -------------------------------------------------------------------------------------
    def _census(self, name, cpages, crefused, pages) -> None:
        self.census_cells += len({p.cell for p in cpages if p.depth_source == "so-uv"})
        self.census_class += sum(1 for r in crefused if r.klass == "second-array-mover")
        self.census_field += sum(1 for p in cpages if p.hazards.second_array)
        # every CENSUS page must be a LICENSED page with the SAME name, depth and source -- the
        # licensed run may carry MORE (channel G/A/P) and may WITHDRAW on channel A's veto, so the
        # comparison is over the census page's own identity, not over set equality.
        lic = {(p.name, p.cell): (p.bpp, p.depth_source, p.page_offset) for p in pages}
        for p in cpages:
            got = lic.get((p.name, p.cell))
            if got is not None and got != (p.bpp, p.depth_source, p.page_offset):
                self.page_diff.append("%s %s" % (name, p.name))


# ================================================================= U7: THE EDIT SURFACE'S OWN WALK
class _Poison(dict):
    """An :attr:`RP.BoundModel.effective_cover` that SCREAMS instead of answering.

    ★ **THE CONTAINMENT GATE'S INSTRUMENT, AND IT IS SHARPER THAN A DIFF.**  The rung's claim is that
    :data:`RP.CENSUS_CHANNELS` and :data:`RP.LICENSED_CHANNELS` are byte-identical before and after the
    adoption.  Compared as OUTPUTS on the stock 372 that is a CORPUS FACT: the two surfaces could be
    reading the effective cover and merely agreeing with the bound one everywhere.  Substituting this
    for `effective_cover` turns the claim into a STRUCTURAL one -- *the frozen scopes never so much as
    look* -- because any access at all raises, and the run then also yields a dump to diff against the
    real one.  Both readings are taken (U7g), and the instrument is CALIBRATED before it is believed:
    the same substitution under :data:`RP.EDIT_CHANNELS` must RAISE, or a silent pass here would mean
    only that the probe is broken.
    """
    TOKEN = "A FROZEN SCOPE READ effective_cover"

    def _boom(self, *a, **k):
        raise AssertionError(_Poison.TOKEN)

    __getitem__ = __iter__ = __len__ = __contains__ = _boom
    keys = items = values = get = pop = copy = _boom

    def __bool__(self):                                                    # len() is already poisoned
        raise AssertionError(_Poison.TOKEN)


def _dump(pages, refused) -> Tuple:
    """A container's surface as a CANONICAL, order-free tuple -- every field a consumer can read.

    Not a hash: a hash tells you two runs differ and nothing else, and the first question after a
    containment failure is always WHICH FIELD MOVED.
    """
    return (tuple(sorted((p.name, p.cell, p.bpp, p.depth_source, p.readership, p.page_offset,
                          p.page_bytes, p.w, p.h, p.tpage, p.clut, p.clut_offset, p.clut_entries,
                          p.palette_name, p.vram, p.v_offset, p.index, p.kind) for p in pages)),
            tuple(sorted((r.name, r.cell, r.klass, r.reason) for r in refused)))


def names(cells) -> List[str]:
    """``{(container, (x, y))}`` -> sorted ``["ef038 x640_y256", ...]`` -- what a human can check."""
    return sorted("%s x%d_y%d" % (n, c[0], c[1]) for n, c in cells)


def intra_page(m) -> bool:
    """THE INTRA-PAGE LAW, re-derived HERE from the bit layout -- U7's second instrument.

    `max(u) + du <= 255`, `max(v) + dv <= 255`, and every effective cell inside the reader's OWN
    tpage span, which is `256 // (64 * per)` cells wide by 2 stacked cells tall.  Written out rather
    than called through :func:`RP.assert_intra_page` for the same reason :func:`eff_cols` is: a gate
    that checks a law by calling the law's own implementation checks nothing.  U7a runs BOTH and
    requires them to agree.
    """
    if not m.displaced:
        return True
    du, dv = m.mover
    wide = 256 // (PAGE_HW * KT.TEXELS_PER_HW[m.bpp])
    span = {(m.page[0] + PAGE_HW * i, m.page[1] + CELL_LINES * j)
            for i in range(wide) for j in range(2)}
    if m.u[1] + du > 255 or m.v[1] + dv > 255:
        return False
    return all(c in span for c in m.effective_cover)


class Effective:
    """U7's OWN corpus walk -- **THE EDIT SURFACE**, :data:`RP.EDIT_CHANNELS`, 372 containers.

    ★ **WHY IT IS A SECOND WALK AND NOT A PARAMETER ON `Data`.**  `Data` is written about
    :data:`RP.LICENSED_CHANNELS`, the FROZEN scope; this one is written about the scope
    `texel_page` / `export_art` / `build` / `scenery_lines` actually default to.  Folding them would
    have given the edit surface one derivation shared with the file that is supposed to be checking
    it independently.

    ⚠ **THE MEMO, AND ITS CONTROL.**  :func:`RP.scenery_surface` re-derives `bound_models` internally
    on every call, and this walk needs FIVE channel-scope surfaces per container -- five full UV
    rasterisations, ~10 minutes.  So the models are rasterised ONCE per container through the shipped
    :func:`RP.bound_models` and the module global is bound to a closure returning THAT LIST for the
    duration of the container's walk.  The objects are the shipped function's own output, so nothing
    downstream is re-implemented here -- but *purity is exactly the kind of claim that should be
    checked rather than assumed*, so on :data:`CONTROL` (16 containers chosen to own every interesting
    class) the walk ALSO runs all three scopes UNPATCHED and re-derives the models from scratch, and
    U7g requires the dumps and the model tuples to agree.  The same seam is what makes the
    :class:`_Poison` containment probe possible at all.
    """

    #: the containers U7g re-runs UNPATCHED.  Each one costs FOUR extra rasterisations (a fresh
    #: `bound_models` plus one per scope), so the set is chosen for CLASS COVERAGE AT LOW COST rather
    #: than for size: the displacement's own worked example (ef038), two display-binding flips (ef072,
    #: ef203), a container with ZERO incumbent models -- the degenerate case (ef130), four clean
    #: shipped cast cells (ef211), both same-bytes-two-depths corroborations and both cheap
    #: SUBSTITUTED cells (ef226, ef227 -- ef227 also owns the ANSWER SLOT that settled ADD), the
    #: deliverable twin of ef038 (ef407), the frozen Odin records' container (ef424) and the
    #: generalisation cast's second container (ef446).
    #:
    #: ⚠ **ef381 / ef447 / ef498 / ef082 / ef179 / ef390 ARE DELIBERATELY OUT, AND THE REASON IS NOT
    #: THRIFT ALONE.**  What this control tests -- that :func:`RP.bound_models` is pure and that no
    #: surface MUTATES the models between walks -- is a property of the CODE, not of a container, so a
    #: control is CALIBRATION and not coverage.  Including the six biggest cost 440 of U7's 636
    #: seconds (ef381 alone rasterises in 36s, x4) and bought no new proposition.  Every one of them
    #: is still walked, measured and counted by the main pass; it is only the redundant re-derivation
    #: that is skipped.
    CONTROL = ("ef038", "ef072", "ef130", "ef203", "ef211", "ef226", "ef227", "ef407",
               "ef424", "ef446")

    def __init__(self) -> None:
        self.paths = sorted(p for p in glob.glob(os.path.join(CORPUS, "ef*.bytes"))
                            if len(os.path.basename(p)) == 11)
        self.containers = self.skipped = 0
        # ---- U7a THE REACH
        self.readers = self.movers = 0
        self.novel_records = self.novel_slots = 0
        self.novel_records_witness = self.novel_slots_witness = 0
        self.intra_ok = 0
        self.assert_raised = 0
        self.spill_bound = self.spill_eff = 0
        # ---- U7b/c/d the cell populations, as SETS of (container, cell) so the closures are SET
        #      identities and not merely count identities
        self.readerless: Set[Tuple[str, Tuple[int, int]]] = set()
        self.substituted: Set[Tuple[str, Tuple[int, int]]] = set()
        self.vacate: Set[Tuple[str, Tuple[int, int]]] = set()
        self.vs_page: Set[Tuple[str, Tuple[int, int]]] = set()
        self.gained: Set[Tuple[str, Tuple[int, int]]] = set()
        #: every EDIT-scope refusal class standing on a GAINED cell -- what says WHY the two that
        #: never come back as a page do not, by name rather than as a bare `- 1`.
        self.gained_classes: Dict[Tuple[str, Tuple[int, int]], Tuple[str, ...]] = {}
        self.gained_unknown: Set[Tuple[str, Tuple[int, int]]] = set()
        self.gained_undeclared: Set[Tuple[str, Tuple[int, int]]] = set()
        self.changed: Set[Tuple[str, Tuple[int, int]]] = set()
        self.flips: Set[Tuple[str, Tuple[int, int]]] = set()
        self.dbm_predicate: Set[Tuple[str, Tuple[int, int]]] = set()
        self.readerless_open = self.substituted_open = self.vacate_open = 0
        # ---- U7e the surface totals
        self.uv = {"census": 0, "licensed": 0, "edit": 0}
        self.pages = {"census": 0, "licensed": 0, "edit": 0}
        self.refusals = {"census": 0, "licensed": 0, "edit": 0}
        self.uv_lost: Set[Tuple[str, Tuple[int, int]]] = set()
        self.uv_gained: Set[Tuple[str, Tuple[int, int]]] = set()
        # ---- U7g the containment
        self.census_same = self.licensed_same = 0
        self.poison_reads: List[str] = []
        self.poison_calibrated = False
        self.control_models = self.control_dumps = 0
        self.control_seen: List[str] = []
        self.diffs: List[str] = []
        self.elapsed = 0.0

        t0 = time.time()
        real = RP.bound_models
        for path in self.paths:
            name = os.path.basename(path)[:-6]
            ef = int(name[2:5])
            with open(path, "rb") as fh:
                blob = fh.read()
            self.containers += 1
            self._novel(blob)
            try:
                models = real(blob)
                bound = RP.cell_readers(blob, models)
                eff = RP.effective_cell_readers(blob, models)
                cells = RS.page_cells(blob)
            except (RS.ReskinError, EC.ContainerError, RP.RepaintError):
                self.skipped += 1
                continue
            self._reach(models)
            RP.bound_models = lambda _b, _m=models: _m
            try:
                surf = {"edit": RP.scenery_surface(blob, ef, channels=RP.EDIT_CHANNELS),
                        "licensed": RP.scenery_surface(blob, ef, channels=RP.LICENSED_CHANNELS),
                        "census": RP.scenery_surface(blob, ef)}
            except (RS.ReskinError, EC.ContainerError, RP.RepaintError):
                RP.bound_models = real
                self.skipped += 1
                continue
            try:
                self._contain(name, ef, blob, models, surf)
                if name in self.CONTROL:
                    self._control(name, ef, blob, models, surf, real)
            finally:
                RP.bound_models = real
            self._surface(name, surf)
            self._cells(name, surf, cells, bound, eff)
        self.elapsed = time.time() - t0

    # ---- U7a ------------------------------------------------------------------------------------
    def _novel(self, blob: bytes) -> None:
        """The NOVEL (`P >= 2`) records and their non-zero pairs, off the RAW halfwords.

        Read at `at + 8 + 4P + 4k` by this file's own walker rather than through
        :func:`RP.novel_displacement_reach`, and the ARITY is the discriminant (`P >= 2`) rather than
        `rec["witness"]` -- the two are cross-checked below, which is the point of rolling both.
        """
        mp = EC.creature_package(blob)
        creature = mp.geom_offset if mp is not None else None
        for g in EC.scan_geom(blob):
            if creature is not None and g.base == creature:
                continue
            rec = RS.so_record(blob, g.base)
            if rec is None:
                continue
            P = rec["nparts"]
            nz = sum(1 for k in range(P)
                     if u16(blob, rec["at"] + 8 + 4 * P + 4 * k)
                     or u16(blob, rec["at"] + 8 + 4 * P + 4 * k + 2))
            if P >= 2:
                self.novel_records += 1
                self.novel_slots += nz
            if rec.get("witness") == RS.WITNESS_NOVEL:
                self.novel_records_witness += 1
                self.novel_slots_witness += nz

    def _reach(self, models) -> None:
        for m in models:
            self.readers += 1
            self.movers += int(m.displaced)
            self.spill_bound += int(m.spills)
            self.spill_eff += int(m.effective_spills)
            self.intra_ok += int(intra_page(m))
            try:
                RP.assert_intra_page(m)
            except RP.RepaintError:
                self.assert_raised += 1

    # ---- U7e ------------------------------------------------------------------------------------
    def _surface(self, name: str, surf) -> None:
        uv = {}
        for tag, (pg, rf) in surf.items():
            self.pages[tag] += len(pg)
            self.refusals[tag] += len(rf)
            uv[tag] = {p.cell for p in pg if p.depth_source == "so-uv"}
            self.uv[tag] += len(uv[tag])
        for c in uv["licensed"] - uv["edit"]:
            self.uv_lost.add((name, c))
        for c in uv["edit"] - uv["licensed"]:
            self.uv_gained.add((name, c))

    # ---- U7b / U7c / U7d -------------------------------------------------------------------------
    def _cells(self, name, surf, cells, bound, eff) -> None:
        ekl: Dict[Tuple[int, int], Set[str]] = {}
        for r in surf["edit"][1]:
            ekl.setdefault(r.cell, set()).add(r.klass)
        lkl: Dict[Tuple[int, int], Set[str]] = {}
        for r in surf["licensed"][1]:
            lkl.setdefault(r.cell, set()).add(r.klass)

        def open_before(c) -> bool:
            """OPEN on the PRE-ADOPTION surface -- no export-blocking refusal of any OTHER class.

            Taken at LICENSED on purpose: what an addressability change COSTS is what the author could
            reach BEFORE it, and after the new refusal fires every one of these cells reads as open.
            """
            return not ((lkl.get(c, set()) - {"second-array-mover"}) & RP._EXPORT_BLOCKING)

        for c, ks in ekl.items():
            if "displaced-readerless" in ks:
                self.readerless.add((name, c))
                self.readerless_open += int(open_before(c))
            if "displaced-readership-substituted" in ks:
                self.substituted.add((name, c))
                self.substituted_open += int(open_before(c))
            if "displaced-vs-page-depth" in ks:
                self.vs_page.add((name, c))
        for c, ks in lkl.items():
            if "second-array-mover" in ks:
                self.vacate.add((name, c))
                self.vacate_open += int(open_before(c))

        unknown = {c for c, ks in lkl.items() if "depth-unknown" in ks}
        declared = {pc.cell for pc in cells.values()}
        for c in set(bound) | set(eff):
            b = sorted(m.geom for m in bound.get(c, ()))
            e = sorted(m.geom for m in eff.get(c, ()))
            if not b and e:
                if c in declared:
                    self.gained.add((name, c))
                    self.gained_classes[(name, c)] = tuple(sorted(ekl.get(c, ())))
                    if c in unknown:
                        self.gained_unknown.add((name, c))
                else:
                    # bytes nothing in the container uploads: there is no page to hand back, so these
                    # join the u-spill UNWRITTEN class on the EFFECTIVE obligation set only.
                    self.gained_undeclared.add((name, c))
            elif b and e and b != e and set(b) & set(e):
                self.changed.add((name, c))
                if b[0] != e[0]:
                    self.flips.add((name, c))
            if b and e and b[0] != e[0]:
                # ⚠ the SHIPPED predicate's own population -- NOT scoped to `changed`, so it also
                # holds on all 7 SUBSTITUTED cells.  See `U7_PIN["display_binding_moved_predicate"]`.
                self.dbm_predicate.add((name, c))

    # ---- U7g ------------------------------------------------------------------------------------
    def _contain(self, name, ef, blob, models, surf) -> None:
        """The two FROZEN scopes, re-run with :class:`_Poison` in place of every effective cover."""
        poisoned = [dataclasses.replace(m, effective_cover=_Poison()) for m in models]
        RP.bound_models = lambda _b, _m=poisoned: _m
        try:
            lic = RP.scenery_surface(blob, ef, channels=RP.LICENSED_CHANNELS)
            cen = RP.scenery_surface(blob, ef)
        except AssertionError as exc:
            self.poison_reads.append("%s: %s" % (name, exc))
            return
        self.licensed_same += int(_dump(*lic) == _dump(*surf["licensed"]))
        self.census_same += int(_dump(*cen) == _dump(*surf["census"]))
        if _dump(*lic) != _dump(*surf["licensed"]):
            self.diffs.append("%s LICENSED" % name)
        if _dump(*cen) != _dump(*surf["census"]):
            self.diffs.append("%s CENSUS" % name)
        # ★ THE CALIBRATION, taken ONCE: the same substitution under the EDIT scope MUST raise, or
        # the two passes above prove nothing about the frozen scopes and everything about a probe
        # that cannot fire.  An uncalibrated instrument has produced confident wrong verdicts in this
        # arc before.
        if not self.poison_calibrated and models:
            try:
                RP.scenery_surface(blob, ef, channels=RP.EDIT_CHANNELS)
            except AssertionError as exc:
                self.poison_calibrated = _Poison.TOKEN in str(exc)

    def _control(self, name, ef, blob, models, surf, real) -> None:
        """The memo's own control: the three scopes UNPATCHED, and the models re-derived."""
        RP.bound_models = real
        self.control_seen.append(name)
        fresh = real(blob)
        mine = [(m.geom, m.record_at, m.mover, m.bpp, m.page, m.u, m.v,
                 tuple(sorted(m.cover)), tuple(sorted(m.effective_cover))) for m in models]
        theirs = [(m.geom, m.record_at, m.mover, m.bpp, m.page, m.u, m.v,
                   tuple(sorted(m.cover)), tuple(sorted(m.effective_cover))) for m in fresh]
        self.control_models += int(mine == theirs)
        for tag, chan in (("edit", RP.EDIT_CHANNELS), ("licensed", RP.LICENSED_CHANNELS),
                          ("census", RP.CENSUS_CHANNELS)):
            got = RP.scenery_surface(blob, ef, channels=chan)
            same = _dump(*got) == _dump(*surf[tag])
            self.control_dumps += int(same)
            if not same:
                self.diffs.append("%s MEMO %s" % (name, tag))


_EFF: Optional[Effective] = None


def effective() -> Effective:
    """U7's walk, built once and reused if the board is re-run in the same process."""
    global _EFF
    if _EFF is None:
        _EFF = Effective()
    return _EFF


def row(label: str, got, want) -> None:
    """:func:`chk`, with the measurement PRINTED whether it passes or not.

    U7 prints a per-check ledger rather than only a PASS/FAIL line, because the numbers ARE the
    deliverable here: a green gate that shows nobody the 45 / 7 / 70 / 36 it rolled cannot be read
    against the constants file by a human.
    """
    chk(label, got, want)
    print("   %-4s %-52s %s" % ("ok" if got == want else "****", label,
                                got if got == want else "%r  PINNED %r" % (got, want)))


# --------------------------------------------------------------------------- THE GATES
def u1_reader(D: Data) -> None:
    print("U1  THE READER -- `so_record` returns the SECOND array, and an INDEPENDENT walker agrees")
    chk("accepted records", D.records, PIN["records"])
    chk("binding slots", D.slots, PIN["slots"])
    chk("P == 0 records", D.p0, PIN["p0_records"])
    chk("arrayB == 8 + 4P", D.arrayb_ok, PIN["arrayb_agrees"])
    chk("recordBase + recLen == geomBase", D.rec_end_ok, PIN["record_end_is_geom"])
    chk("len(second) == P", D.second_len_ok, PIN["second_len_equals_p"])
    chk("independent walker agrees, slot for slot", D.agree, PIN["independent_agreement"])
    chk("slots carrying a NON-ZERO pair", D.second_nonzero, PIN["second_nonzero_slots"])
    chk("the P = 0 shape is unchanged (second == [], no tpage/clut)", D.p0_shape_ok, True)
    print("   %d records / %d slots; arrayB agrees %d/%d and the record still ends at geomBase %d/%d"
          % (D.records, D.slots, D.arrayb_ok, D.records, D.rec_end_ok, D.records))
    print("   the SECOND array read at `at + 8 + 4P + 4k` agrees with an independent raw walker on "
          "%d/%d slots (%d disagreements)" % (D.agree, D.slots, len(D.disagree)))
    print("   %d of %d slots carry a NON-ZERO pair -- the raw material, UNINTERPRETED"
          % (D.second_nonzero, D.slots))
    if D.disagree:                                                     # pragma: no cover
        for line in D.disagree[:5]:
            print("   *** %s" % line)


def u2_population(D: Data) -> None:
    print("U2  THE POPULATION -- the firing set, RE-DERIVED from the container at call time")
    n = sum(len(v) for v in D.fire.values())
    chk("firing cells", n, PIN["fire_cells"])
    chk("firing containers", len(D.fire), PIN["fire_containers"])
    chk("fully open (no export-blocking refusal of any other class)", D.fire_open, PIN["fire_open"])
    chk("blocked: program-vram-write", D.fire_block.get("program-vram-write", 0),
        PIN["fire_program_vram_write"])
    chk("blocked: same-bytes-two-depths", D.fire_block.get("same-bytes-two-depths", 0),
        PIN["fire_same_bytes_two_depths"])
    chk("incumbent readers corpus-wide", D.readers, PIN["incumbent_readers"])
    chk("...of which carry a mover", D.movers, PIN["incumbent_movers"])
    chk("every firing cell is an EMITTED so-uv page",
        sorted({v["source"] for h in D.fire.values() for v in h.values()}), ["so-uv"])
    # ★ THE RE-DERIVATION PIN: the three shipped constants, re-rolled here.
    chk("DA.SECOND_ARRAY_MOVER_CELLS", DA.SECOND_ARRAY_MOVER_CELLS, n)
    chk("DA.SECOND_ARRAY_MOVER_CONTAINERS", DA.SECOND_ARRAY_MOVER_CONTAINERS, len(D.fire))
    chk("DA.SECOND_ARRAY_MOVER_OPEN", DA.SECOND_ARRAY_MOVER_OPEN, D.fire_open)
    print("   %d cell(s) in %d container(s); %d fully OPEN today, %s"
          % (n, len(D.fire), D.fire_open,
             ", ".join("%d %s" % (v, k) for k, v in sorted(D.fire_block.items()) if k != "OPEN")))
    print("   %d incumbent readers corpus-wide, %d carrying a NON-ZERO pair"
          % (D.readers, D.movers))
    print("   THE %d, BY NAME:" % n)
    for c in sorted(D.fire):
        print("      %-6s %s" % (c, "  ".join("x%d_y%d%s" % (k[0], k[1],
                                                             "" if not v["block"] else
                                                             "[%s]" % "+".join(v["block"]))
                                              for k, v in sorted(D.fire[c].items()))))


def u3_superset(D: Data) -> None:
    print("U3  THE SUPERSET LAW -- both per-labelling lost-cell lists CONTAINED, zero missed")
    mine = {(c, k) for c, h in D.fire.items() for k in h}
    chk("the scoping's SWAPPED list", len(LOST_SWAPPED), PIN["lost_swapped"])
    chk("the scoping's ORIGINAL list", len(LOST_ORIGINAL), PIN["lost_original"])
    chk("their union", len(LOST_SWAPPED | LOST_ORIGINAL), PIN["lost_union"])
    chk("SWAPPED cells missing from the firing set", sorted(LOST_SWAPPED - mine), [])
    chk("ORIGINAL cells missing from the firing set", sorted(LOST_ORIGINAL - mine), [])
    chk("conservative extras beyond the union",
        len(mine - (LOST_SWAPPED | LOST_ORIGINAL)), PIN["conservative_extras"])
    # ...and the independent re-derivation of the two lists, from the kit's own movers
    chk("re-derived SWAPPED", len(D.lost["swapped"]), PIN["rederived_swapped"])
    chk("re-derived ORIGINAL", len(D.lost["original"]), PIN["rederived_original"])
    chk("re-derived SWAPPED == the scoping's", sorted(D.lost["swapped"]), sorted(LOST_SWAPPED))
    chk("the scoping's ORIGINAL is contained in the re-derivation",
        sorted(LOST_ORIGINAL - D.lost["original"]), [])
    chk("the SPAN's ORIGINAL over-count", len(D.lost["original"] - LOST_ORIGINAL),
        PIN["span_vs_raster_extra"])
    chk("...and both over-counted cells are in the firing set anyway",
        sorted((D.lost["original"] - LOST_ORIGINAL) - mine), [])
    chk("the ALL-scope four are OUT OF REACH by construction", sorted(ALL_SCOPE_ONLY & mine), [])
    print("   SWAPPED 16/16 contained . ORIGINAL 19/19 contained . union 35/35, ZERO missed")
    print("   %d extras beyond the union -- and since U1's s77 read they are NOT cells that stay "
          "put: both lists are u-ONLY models, and these vacate in v, the axis neither modelled"
          % len(mine - (LOST_SWAPPED | LOST_ORIGINAL)))
    print("   the independent roll reproduces SWAPPED EXACTLY (16 == 16) and over-names ORIGINAL by "
          "%d (%s) -- the kit's columns are a `u` SPAN, and a SPAN is a WIDER claim, never a wrong "
          "one" % (len(D.lost["original"] - LOST_ORIGINAL),
                   ", ".join("%s %s" % t for t in sorted(D.lost["original"] - LOST_ORIGINAL))))
    print("   THE DECLARED BLIND SPOT (multi-part readers only, unreachable by an incumbent-only "
          "lane): %s" % ", ".join("%s x%d_y%d" % (c, k[0], k[1])
                                  for c, k in sorted(ALL_SCOPE_ONLY)))


def u4_census(D: Data) -> None:
    print("U4  THE CENSUS DEFAULT IS UNMOVED -- the class silent, the field EMPTY, the pages equal")
    chk("`second-array-mover` stated under CENSUS_CHANNELS", D.census_class,
        PIN["census_class_stated"])
    chk("non-empty `second_array` under CENSUS_CHANNELS", D.census_field,
        PIN["census_field_nonempty"])
    chk("census so-uv cells", D.census_cells, PIN["census_so_uv_cells"])
    chk("census pages whose name/depth/source/offset differ on the licensed path",
        len(D.page_diff), PIN["census_page_diff"])
    print("   %d census so-uv cell(s) -- W6b-1's own 187, byte for byte, which is the population "
          "`w6b_gates` G6 / `w6q_gates` G1+G16 / `w6b2i_gates` I5 are written ABOUT"
          % D.census_cells)
    print("   the class is stated %d time(s) and the field is non-empty on %d page(s) under the "
          "census default: an instrument nobody asked for says NOTHING"
          % (D.census_class, D.census_field))


def u5_shipped_casts(D: Data) -> None:
    print("U5  THE SHIPPED CASTS -- what this class says about the artifacts this arc already cast")
    mine = {(c, k) for c, h in D.fire.items() for k in h}
    firing = sorted(SHIPPED_CASTS & mine)
    clean = sorted(SHIPPED_CASTS - mine)
    chk("shipped cast cells that stay CLEAN", len(clean), PIN["shipped_clean"])
    chk("shipped cast cells that FIRE", len(firing), PIN["shipped_firing"])
    chk("...and it is ef424 cell.s0.x448_y384", firing, [("ef424", (448, 384))])
    chk("ef038 x640_y256 is NOT in the class (20 movers, SEVEN zero-pair controls)",
        ("ef038", (640, 256)) in mine, False)
    specs = specs_on_firing_cells(mine)
    chk("committed cast specs with an ENABLED row on the firing cell", len(specs),
        PIN["specs_on_the_firing_cell"])
    chk("...and they are BOTH ef424 casts", specs, list(FROZEN_ODIN_SPECS))
    for c, k in clean:
        print("      CLEAN  %-6s x%d_y%d" % (c, k[0], k[1]))
    for c, k in firing:
        note = D.fire[c][k]
        print("      FIRES  %-6s x%d_y%d  (%s)" % (c, k[0], k[1], note["source"]))
    print("   ★ ef424 `cell.s0.x448_y384` was the W6b-3ii ORDER RIDER -- and under the adoption it is "
          "no longer a lead but a DERIVATION: its only incumbent reader, GEOM 0x2ec34 (record "
          "0x2ec24, 8bpp, pair (128, 0)), samples column 512 instead, so the cell is "
          "`displaced-readerless`.")

    # ---- ★ THE FREEZE.  The owner's decision, ASSERTED rather than announced.
    # These two are the W6b-3 (ii) cast records.  This board used to say "re-running either cast now
    # needs the ack" -- which was WRONG the moment the adoption landed: the ack does NOT rescue them,
    # it only moves the refusal one stage on.  A board that quietly dropped the check would be hiding
    # that.  So the check is REPLACED, not removed: the specs must still PARSE, must still carry their
    # superseding note, must NOT have been silently repaired with an ack, and must HARD-FAIL through
    # the real build path -- twice, by name, at the shipped default.
    import tomllib
    parsed, noted, acked = 0, 0, 0
    for name in FROZEN_ODIN_SPECS:
        path = os.path.join(_HERE, name)
        with open(path, "rb") as fh:
            spec = tomllib.load(fh)
        parsed += 1
        with open(path, encoding="utf-8") as fh:
            noted += int(FREEZE_TOKEN in fh.read())
        acked += sum(1 for t in spec["reskin"]["texel"] if DA.ACK_MOVER_KEY in t)
    chk("both frozen records still PARSE", parsed, PIN["frozen_specs"])
    chk("both carry the superseding note (%r)" % FREEZE_TOKEN, noted, PIN["frozen_specs"])
    chk("neither has been silently REPAIRED with an ack", acked, 0)
    verdicts = frozen_spec_verdicts()
    chk("frozen records that BUILD under the shipped kit",
        sum(1 for _, a, b in verdicts if "BUILT" in (a, b)), PIN["frozen_specs_that_build"])
    chk("...with no ack, every one refuses as DISPLACED-READERLESS",
        sorted({a for _, a, _ in verdicts}), ["DISPLACED-READERLESS"])
    chk("...and WITH the ack the palette is a HEADER FACT and refuses again",
        sorted({b for _, _, b in verdicts}), ["PALETTE-IS-A-HEADER-FACT"])
    print("   ★ THE OWNER'S DECISION: BOTH ef424 CAST RECORDS ARE FROZEN AS HISTORY.  They reproduce "
          "only against the PRE-adoption kit; their bodies are NOT retro-edited and a superseding "
          "note stands at the top of each.")
    for name, no_ack, with_ack in verdicts:
        print("      FROZEN  %-22s no ack -> %-22s with the ack -> %s"
              % (name, no_ack, with_ack))
    print("   ⚠ `%s` DOES NOT RESCUE THEM -- it lifts the readerless refusal and the row then fails "
          "on `palette_from`, because the cell re-sources so-uv -> so-page and the COLUMN's own CLUT "
          "word is 243 where the departed reader 0x2ec34's key was 242.  A bare re-point would also "
          "change what the recorded mark LOOKS LIKE (ink index 99 was the max-luminance entry under "
          "242).  Re-cast = a FRESH spec, never a repair of these." % DA.ACK_MOVER_KEY)
    print("   ★ AND NOTHING RESTS ON REBUILDING THEM: the finding they carry -- BLADE (part 1) -> "
          "slot 1 -> column 704, IDENTITY ordering -- was scored on video and rests on a BAND COUNT, "
          "which is DEPTH-INVARIANT by construction.  ROW 1 (`cell.s0.x704_y384`, record 0x2f9a4, "
          "P = 2) is out of the adoption's reach under ORDER_UNMEASURED and is unmoved.")
    print("   ⚠ the %d spec(s) above are identified at LICENSED_CHANNELS -- the scope they were CAST "
          "at.  At the shipped EDIT default their cell emits no page at all, so a sweep there names "
          "ZERO, which would read as 'the adoption touches none of the arc's casts'." % len(specs))


def u6_ack_and_constant(D: Data) -> None:
    print("U6  THE ACK AND THE CONSTANT -- literal boolean, registered key, and NO BYTE MOVES")
    import hashlib
    import tempfile
    chk("the key is registered in _TEXEL_KEYS", DA.ACK_MOVER_KEY in RP._TEXEL_KEYS, True)
    chk("the class is NOT unaddressable", "second-array-mover" in RP._UNADDRESSABLE, False)
    chk("the class is NOT export-blocking", "second-array-mover" in RP._EXPORT_BLOCKING, False)
    # the `%` hazard is a property of EVERY `%`-formatted class text this lane owns, and since the
    # adoption the class that actually fires on an author is one of the two below -- so all three are
    # swept rather than the one this board was originally written about.
    for klass in ("second-array-mover", "displaced-readerless",
                  "displaced-readership-substituted"):
        chk("no literal `%%` in the `%s` class text" % klass,
            "%" in RP._REFUSAL_TEXT[klass].replace("%s", ""), False)
    # ★ THE LOAD-BEARING CLAIMS -- the altitude, the settled labelling, the resolved v axis, the
    # OPERATION, the two containers the owner's generalisation cast added, the law that makes the
    # model safe, and the surviving reach rider.  THE STALE-TEXT LEDGER'S OWN DEVICE: a token is never
    # DELETED from this loop, it is MOVED to the absent loop below, so a silent revert to the old text
    # fails LOUD instead of passing quietly.  "0.84" / "0.68" / "UNRESOLVED" were retired that way by
    # the s77 read; "ONE CONTAINER, ONE CAST" was retired by the owner's four-cast session, which read
    # the same mechanism on ef227 and ef446 and made the one-container claim FALSE.
    for piece in ("0.97", "PAIR POSITION 0 DISPLACES u", "THE v AXIS IS RESOLVED",
                  "LINEAR ADDITION", "ef227", "ef446", "THE INTRA-PAGE LAW",
                  "THE REACH IS THE INCUMBENT RECORDS ONLY"):
        chk("the caveat carries %r" % piece, piece in DA.U_DISPLACEMENT_CAVEAT, True)
    for gone in ("0.84", "0.68", "UNRESOLVED", "NEITHER is preferred",
                 "ONE CONTAINER, ONE CAST"):
        chk("the caveat has RETIRED %r" % gone, gone in DA.U_DISPLACEMENT_CAVEAT, False)
    for piece in ("cell.s0.x704_y256", "cell.s0.x704_y384"):
        chk("the sharpest-unmodelled statement names %r" % piece,
            piece in DA.U_DISPLACEMENT_CAVEAT, True)
    chk("the refusal quotes the caveat", DA.U_DISPLACEMENT_CAVEAT
        in RP._REFUSAL_TEXT["second-array-mover"], True)
    chk("the ack warning quotes the caveat",
        DA.U_DISPLACEMENT_CAVEAT in DA.U_DISPLACEMENT_ACK_WARNING, True)

    # THE REAL BUILD PATH, on a real corpus firing cell.
    # ⚠ SINCE THE ADOPTION THE EXPORT ITSELF NEEDS THE ACK.  `cell.s0.x448_y384` is
    # `displaced-readerless` at the shipped EDIT default, so `export_art` writes NO png for it and a
    # bare export leaves this block with nothing to build against (it used to die on ART DRIFT, which
    # reads like a manifest bug and is really the refusal arriving one stage earlier).  Threading
    # `displacement_ack=True` here is the same judgement the spec row below states, made once.
    ef, cell = 424, "cell.s0.x448_y384"
    with open(os.path.join(CORPUS, "ef%03d.bytes" % ef), "rb") as fh:
        blob = fh.read()
    td = tempfile.mkdtemp(prefix="u1gates-")
    RP.export_art(blob, ef, out_dir=td, scaffold=True, overlays=False, displacement_ack=True)
    row = {"name": cell, "enabled": True, "source": os.path.join(td, "%s.png" % cell),
           "expect_bpp": 8}
    spec = {"reskin": {"effect": ef, "label": "u1gates",
                       "expect_sha256": hashlib.sha256(blob).hexdigest(), "texel": [dict(row)]}}
    refused_by_name = False
    try:
        RP.build(spec, os.path.join(td, "s.toml"), blob=blob)
    except RP.RepaintError as e:
        # the refusal MOVED, and the name moved with it: the disclosure-era `THE SECOND-ARRAY GATE`
        # fired at BUILD, the adopted `DISPLACED-READERLESS` fires at RESOLUTION -- earlier, and on
        # the export lane as well as the build lane.
        refused_by_name = "DISPLACED-READERLESS" in str(e)
    chk("an enabled row on a firing cell REFUSES by name without the ack", refused_by_name, True)
    # ...and `"true"` is not `true`
    bad = dict(spec)
    bad["reskin"] = dict(spec["reskin"], texel=[dict(row, **{DA.ACK_MOVER_KEY: "true"})])
    literal = False
    try:
        RP.build(bad, os.path.join(td, "s.toml"), blob=blob)
    except RP.RepaintError as e:
        literal = "must be a BOOLEAN" in str(e)
    chk("the ack is a LITERAL BOOLEAN (`\"true\"` refuses)", literal, True)
    # ...and with it, the build succeeds and NO BYTE MOVES.  ⚠ THE CONTROL HAD TO CHANGE SHAPE.  It
    # used to build the UNACKNOWLEDGED row with the gate stubbed out and compare; under the adoption
    # that row cannot be built at all, because the refusal is now in the PAGE RESOLUTION and not in
    # the gate.  So the control is taken on the acknowledged row instead -- gate stubbed vs gate live,
    # same row -- which is the property that was ever load-bearing: the gate REFUSES, it never emits.
    good = {"reskin": dict(spec["reskin"], texel=[dict(row, **{DA.ACK_MOVER_KEY: True})])}
    with_ack = RP.build(good, os.path.join(td, "s.toml"), blob=blob)
    was = RP._gate_second_array
    try:
        RP._gate_second_array = lambda targets: {}
        stubbed = RP.build(good, os.path.join(td, "s.toml"), blob=blob)
    finally:
        RP._gate_second_array = was
    chk("EMISSION UNCHANGED: the gate stubbed out emits the same bytes",
        with_ack.patched == stubbed.patched, True)
    chk("...and this row is a NO-OP repaint, so it is also the stock container",
        with_ack.patched == blob, True)
    notes = " ".join(with_ack.targets[0].hazard_notes)
    chk("the acknowledged case STILL discloses", DA.U_DISPLACEMENT_ACK_WARNING in notes, True)
    with open(os.path.join(td, RP.SCAFFOLD_NAME), encoding="utf-8") as fh:
        scaffold = fh.read()
    chk("the scaffold emits the ack line on the firing row",
        "%s = false" % DA.ACK_MOVER_KEY in scaffold, True)
    chk("...exactly once", scaffold.count("%s = false" % DA.ACK_MOVER_KEY), 1)
    # ★ THE SCAFFOLD PINS MOVED WITH THE KIT.  A disclosure-era scaffold printed BOTH candidate
    # labellings side by side ("SWAPPED  reading" / "ORIGINAL reading") because the kit had not
    # chosen.  The adopted scaffold prints ONE arithmetic per reader -- what the record BINDS and what
    # the hardware SAMPLES -- so the pin is on that line's own shape, and the retired pair is checked
    # ABSENT so a revert to the two-reading text goes RED.
    chk("the scaffold prints the ADOPTED per-reader arithmetic",
        "binds " in scaffold and " -> samples " in scaffold, True)
    chk("...on the reader that vacates this very cell",
        "GEOM 0x2ec34  record 0x2ec24  du=128 dv=0  binds x448_y256 x448_y384 -> samples "
        "x512_y256 x512_y384" in scaffold, True)
    chk("the TWO-READING text is RETIRED from the scaffold",
        "SWAPPED  reading" in scaffold or "ORIGINAL reading" in scaffold, False)
    chk("the refuted claim `pair position 1 moves u` is GONE from the scaffold",
        "pair position 1 moves u" in scaffold, False)
    print("   the build path on ef424 %s: refused as DISPLACED-READERLESS without the ack, built "
          "with it, and the patched bytes are IDENTICAL to the same row built with the gate stubbed "
          "out -- and identical to the stock container, because the row is a no-op repaint" % cell)
    print("   the caveat carries 0.97 / the settled labelling / the resolved v axis / LINEAR "
          "ADDITION / ef227 + ef446 / THE INTRA-PAGE LAW / the surviving REACH rider, and is quoted "
          "at the refusal, the gate, the disclosure and the report block")
    print("   ...and `ONE CONTAINER, ONE CAST` has MOVED to the retired list -- the owner's cast "
          "read the same mechanism on two more containers, so the one-container claim is now FALSE "
          "and a revert to it fails LOUD here rather than passing quietly")


def u7_effective_cover(_D=None) -> None:
    """★ **U7 -- THE EFFECTIVE COVER.**  The W6b-3 (iv) adoption, re-rolled at the EDIT scope.

    THE GAP THIS CLOSES: every other gate in this arc is aimed at :data:`RP.LICENSED_CHANNELS`, and
    two of them derive their scope from it by construction, so the surface an author is actually
    handed -- `texel_page` / `export_art` / `build` / `scenery_lines`, all defaulting to
    :data:`RP.EDIT_CHANNELS` -- had exactly ONE re-derivation, in the kit's own test file.
    """
    E = effective()
    print("U7  THE EFFECTIVE COVER -- the EDIT surface, re-rolled from the 372 containers")
    row("containers walked", E.containers, U7_PIN["containers"])
    row("containers the kit itself refuses", E.skipped, U7_PIN["skipped"])

    print("  U7a  THE REACH -- what the adoption can touch, and what it provably cannot")
    row("incumbent (P <= 1) so readers", E.readers, U7_PIN["incumbent_readers"])
    row("...carrying a NON-ZERO pair, i.e. DISPLACED", E.movers, U7_PIN["incumbent_movers"])
    row("NOVEL (P >= 2) records", E.novel_records, U7_PIN["novel_records"])
    row("NOVEL slots carrying a pair -- OUT OF REACH", E.novel_slots,
        U7_PIN["novel_mover_slots"])
    row("...and the `witness` reading agrees with the ARITY one",
        (E.novel_records_witness, E.novel_slots_witness), (E.novel_records, E.novel_slots))
    row("THE INTRA-PAGE LAW, re-derived in this file", E.intra_ok, U7_PIN["intra_page_ok"])
    row("...and `RP.assert_intra_page` agrees, 0 refusals", E.assert_raised,
        U7_PIN["assert_intra_page_raised"])
    print("     the reach is the INCUMBENT records only: %d readers, %d displaced -- and %d novel "
          "slots in %d records carry a pair NOTHING here models, so the effective cover is a LOWER "
          "BOUND on readership" % (E.readers, E.movers, E.novel_slots, E.novel_records))

    print("  U7b  THE LOSS HALF -- and the closure that says 45 and 52 are NOT addends")
    row("displaced-readerless cells", len(E.readerless), U7_PIN["readerless_cells"])
    row("...OPEN on the pre-adoption surface", E.readerless_open, U7_PIN["readerless_open"])
    row("...over how many containers", len({n for n, _ in E.readerless}),
        U7_PIN["readerless_containers"])
    row("displaced-readership-substituted cells", len(E.substituted),
        U7_PIN["substituted_cells"])
    row("...OPEN on the pre-adoption surface", E.substituted_open, U7_PIN["substituted_open"])
    row("...over how many containers", len({n for n, _ in E.substituted}),
        U7_PIN["substituted_containers"])
    row("second-array-mover cells at LICENSED (the VACATE reading)", len(E.vacate),
        U7_PIN["vacate_cells"])
    row("...OPEN", E.vacate_open, U7_PIN["vacate_open"])
    row("...over how many containers", len({n for n, _ in E.vacate}), U7_PIN["vacate_containers"])
    # ★ THE CLOSURES, AS SET IDENTITIES.  Counts closing is weaker than sets closing: 45 + 7 == 52
    # would still hold if the two halves named cells the 52 does not.
    row("CLOSURE 45 + 7 == 52", len(E.readerless) + len(E.substituted), len(E.vacate))
    row("...and they are the SAME CELLS, not merely the same count",
        names((E.readerless | E.substituted) ^ E.vacate), [])
    row("CLOSURE 41 + 6 == 47", E.readerless_open + E.substituted_open, E.vacate_open)
    row("...over the same containers", sorted({n for n, _ in E.readerless | E.substituted}
                                              ^ {n for n, _ in E.vacate}), [])
    row("the two halves are DISJOINT", names(E.readerless & E.substituted), [])

    print("  U7c  THE GAIN HALF -- what the adoption hands back")
    row("declared cells that GAIN a displaced reader", len(E.gained), U7_PIN["gained_cells"])
    row("...refused depth-unknown before this rung (THE PRIZE)", len(E.gained_unknown),
        U7_PIN["gained_from_unknown"])
    row("...over how many containers", len({n for n, _ in E.gained}), U7_PIN["gained_containers"])
    row("UNDECLARED cells a displaced reader lands on", len(E.gained_undeclared),
        U7_PIN["gained_undeclared"])
    row("displaced-vs-page-depth (the one VETO this rung mints)", len(E.vs_page),
        U7_PIN["vs_page_depth_cells"])
    row("...and the gain half never overlaps the loss half",
        names(E.gained & (E.readerless | E.substituted)), [])
    print("     UNDECLARED: %s -- bytes nothing in the container uploads, so there is no page to "
          "hand back and they join the u-spill UNWRITTEN class on the EFFECTIVE obligation only"
          % ", ".join(names(E.gained_undeclared)))
    print("     THE VETO: %s" % ", ".join(names(E.vs_page)))

    print("  U7d  THE CLASS NOBODY HAD NAMED -- and a two-number finding inside it")
    row("cells that keep a reader but not the SAME readers", len(E.changed),
        U7_PIN["changed_cells"])
    row("...of which the DISPLAY BINDING changes hands", len(E.flips),
        U7_PIN["display_binding_moved_in_changed"])
    row("`CellHazards.display_binding_moved`'s OWN population", len(E.dbm_predicate),
        U7_PIN["display_binding_moved_predicate"])
    # ★ THE FINDING, PINNED RATHER THAN NARRATED: the predicate's population is the constant's PLUS
    # the 7 substituted cells, exactly, and nothing else.  Both readings are defensible -- on a
    # substituted cell the display binding HAS changed hands, so `_scenery_disclosures` is right to
    # print its line there -- but `DISPLACED_DISPLAY_BINDING_MOVED = 14` is documented "...of which"
    # under `DISPLACED_CHANGED_CELLS`, and the predicate's own docstring says "and of those", which
    # reads as a subset claim the predicate does not satisfy.  Pinning the DECOMPOSITION is what stops
    # either number from quietly becoming the other.
    row("...and the gap is EXACTLY the 7 substituted cells",
        names(E.dbm_predicate - E.flips), names(E.substituted))
    row("...with nothing outside those two classes",
        names(E.dbm_predicate - E.flips - E.substituted), [])
    print("     ⚠ TWO POPULATIONS, ONE NAME: `DA.DISPLACED_DISPLAY_BINDING_MOVED` is %d and is "
          "scoped to the %d CHANGED cells; the SHIPPED predicate answers True on %d, because it is "
          "not scoped to `displaced_changed` and every SUBSTITUTED cell's reader set is disjoint.  "
          "14 + 7 == 21, measured, with 0 elsewhere."
          % (len(E.flips), len(E.changed), len(E.dbm_predicate)))

    print("  U7e  THE OBLIGATION SET, AND THE so-uv ARITHMETIC, DERIVED AS SETS")
    row("spilling bindings on the BOUND cover (w6b_gates G6's)", E.spill_bound,
        U7_PIN["spill_bound"])
    row("...on the EFFECTIVE cover (THE NAME-EVERY-COLUMN obligation)", E.spill_eff,
        U7_PIN["spill_effective"])
    row("the change is PURELY ADDITIVE (0 bindings stop spilling)",
        E.spill_eff >= E.spill_bound, True)
    row("so-uv cells, CENSUS", E.uv["census"], U7_PIN["census_so_uv"])
    row("so-uv cells, LICENSED", E.uv["licensed"], U7_PIN["licensed_so_uv"])
    row("so-uv cells, EDIT", E.uv["edit"], U7_PIN["edit_so_uv"])
    row("so-uv cells LOST between LICENSED and EDIT", len(E.uv_lost), U7_PIN["so_uv_lost"])
    row("so-uv cells GAINED between LICENSED and EDIT", len(E.uv_gained), U7_PIN["so_uv_gained"])
    # ★ THE ARITHMETIC, RE-DERIVED AS A SET DIFFERENCE RATHER THAN COPIED.  The kit's own closure is
    # written `183 - 45 - 7 + 70 - 1 - 1 == 199`, with two bare `- 1` terms.  Rolled as sets the
    # residual on the LOSS side is ZERO -- the 52 lost cells are exactly the readerless plus the
    # substituted -- so BOTH subtractions belong on the GAIN side: of the 70 gained cells, 68 come
    # back as so-uv pages and 2 do not (the displaced-vs-page-depth VETO, and one cell whose column
    # keeps CHANNEL A's array-dual veto).  Same total, and now every term is named.
    row("...the LOST set is exactly readerless + substituted",
        names(E.uv_lost ^ (E.readerless | E.substituted)), [])
    row("...so the loss-side residual is", len(E.uv_lost - E.readerless - E.substituted),
        U7_PIN["so_uv_lost_residual"])
    row("gained cells that do NOT come back as a so-uv page", len(E.gained - E.uv_gained),
        U7_PIN["gained_not_emitted"])
    # ...and WHICH refusal each of the two is standing under, by name.  A `- 1` with no class behind
    # it is a fudge factor; a `- 1` whose refusal class the board reads back off the surface is a term.
    row("...and their refusal classes, read back off the EDIT surface",
        sorted(E.gained_classes[k] for k in E.gained - E.uv_gained),
        [("array-dual-depth",), ("displaced-vs-page-depth",)])
    row("CLOSURE 183 - 52 + 68 == 199",
        E.uv["licensed"] - len(E.uv_lost) + len(E.uv_gained), E.uv["edit"])
    row("census pages / refusals", (E.pages["census"], E.refusals["census"]),
        (U7_PIN["census_pages"], U7_PIN["census_refusals"]))
    row("licensed pages / refusals", (E.pages["licensed"], E.refusals["licensed"]),
        (U7_PIN["licensed_pages"], U7_PIN["licensed_refusals"]))
    row("edit pages / refusals", (E.pages["edit"], E.refusals["edit"]),
        (U7_PIN["edit_pages"], U7_PIN["edit_refusals"]))
    print("     the 2 gained cells that emit NOTHING -- displaced-vs-page-depth VETO: %s . CHANNEL "
          "A's array-dual veto: %s.  NAMING them is what turns the kit's two bare `- 1` terms into "
          "a derivation" % (", ".join(names((E.gained - E.uv_gained) & E.vs_page)),
                            ", ".join(names((E.gained - E.uv_gained) - E.vs_page))))

    print("  U7f  THE SHIPPED CONSTANTS, PINNED AGAINST THIS FILE'S OWN ROLL")
    row("DA.INCUMBENT_READERS", DA.INCUMBENT_READERS, E.readers)
    row("DA.INCUMBENT_MOVERS", DA.INCUMBENT_MOVERS, E.movers)
    row("DA.NOVEL_MOVER_SLOTS", DA.NOVEL_MOVER_SLOTS, E.novel_slots)
    row("DA.DISPLACED_READERLESS_CELLS", DA.DISPLACED_READERLESS_CELLS, len(E.readerless))
    row("DA.DISPLACED_READERLESS_OPEN", DA.DISPLACED_READERLESS_OPEN, E.readerless_open)
    row("DA.DISPLACED_READERLESS_CONTAINERS", DA.DISPLACED_READERLESS_CONTAINERS,
        len({n for n, _ in E.readerless}))
    row("DA.DISPLACED_SUBSTITUTED_CELLS", DA.DISPLACED_SUBSTITUTED_CELLS, len(E.substituted))
    row("DA.DISPLACED_SUBSTITUTED_OPEN", DA.DISPLACED_SUBSTITUTED_OPEN, E.substituted_open)
    row("DA.SECOND_ARRAY_MOVER_CELLS", DA.SECOND_ARRAY_MOVER_CELLS, len(E.vacate))
    row("DA.SECOND_ARRAY_MOVER_OPEN", DA.SECOND_ARRAY_MOVER_OPEN, E.vacate_open)
    row("DA.SECOND_ARRAY_MOVER_CONTAINERS", DA.SECOND_ARRAY_MOVER_CONTAINERS,
        len({n for n, _ in E.vacate}))
    row("DA.DISPLACED_GAINED_CELLS", DA.DISPLACED_GAINED_CELLS, len(E.gained))
    row("DA.DISPLACED_GAINED_FROM_UNKNOWN", DA.DISPLACED_GAINED_FROM_UNKNOWN,
        len(E.gained_unknown))
    row("DA.DISPLACED_GAINED_UNDECLARED", DA.DISPLACED_GAINED_UNDECLARED,
        len(E.gained_undeclared))
    row("DA.DISPLACED_CHANGED_CELLS", DA.DISPLACED_CHANGED_CELLS, len(E.changed))
    row("DA.DISPLACED_DISPLAY_BINDING_MOVED (the CHANGED-scoped 14)",
        DA.DISPLACED_DISPLAY_BINDING_MOVED, len(E.flips))
    row("DA.DISPLACED_VS_PAGE_DEPTH_CELLS", DA.DISPLACED_VS_PAGE_DEPTH_CELLS, len(E.vs_page))
    row("DA.DISPLACED_SPILL_BINDINGS", DA.DISPLACED_SPILL_BINDINGS, E.spill_eff)
    row("DA.CENSUS_SO_UV_CELLS", DA.CENSUS_SO_UV_CELLS, E.uv["census"])
    row("DA.SHIPPED_SO_UV_CELLS", DA.SHIPPED_SO_UV_CELLS, E.uv["licensed"])
    row("DA.EDIT_SO_UV_CELLS", DA.EDIT_SO_UV_CELLS, E.uv["edit"])
    row("the MODEL NAME is one string in two modules", DA.DISPLACEMENT_MODEL,
        RP.DISPLACEMENT_MODEL)

    print("  U7g  THE CONTAINMENT -- the frozen scopes never so much as LOOK at the effective cover")
    row("the POISON probe is CALIBRATED (it fires under EDIT)", E.poison_calibrated, True)
    row("frozen scopes that READ the effective cover", len(E.poison_reads),
        U7_PIN["poison_reads"])
    row("CENSUS byte-identical with the cover poisoned", E.census_same,
        U7_PIN["census_identical"])
    row("LICENSED byte-identical with the cover poisoned", E.licensed_same,
        U7_PIN["licensed_identical"])
    row("control containers re-run UNPATCHED", len(E.control_seen),
        U7_PIN["control_containers"])
    row("...whose models re-derive IDENTICALLY", E.control_models,
        U7_PIN["control_models_agree"])
    row("...and whose 3 scope dumps match the memoised walk", E.control_dumps,
        U7_PIN["control_dumps_agree"])
    row("surface diffs of any kind", E.diffs, [])
    print("     the census and LICENSED surfaces are byte-identical on %d/%d containers with every "
          "`effective_cover` replaced by an object that RAISES on any access -- so 'the frozen "
          "surfaces are unmoved' is a STRUCTURAL property here and not a corpus fact"
          % (E.census_same, E.containers))
    print("     U7's walk: %d containers, %.0fs, ONE rasterisation each shared by five channel-scope "
          "surfaces (%s re-run unpatched as the memo's control)"
          % (E.containers, E.elapsed, ", ".join(E.control_seen[:4]) + ", ..."))


# --------------------------------------------------------------------------- runner
GATES = [
    ("U1", "THE READER -- 502/649/293, against an INDEPENDENT raw walker", u1_reader),
    ("U2", "THE POPULATION -- 52 cells / 29 containers / 47 open, re-derivation-pinned",
     u2_population),
    ("U3", "THE SUPERSET LAW -- 16 + 19 contained, 35/35, zero missed", u3_superset),
    ("U4", "THE CENSUS DEFAULT IS UNMOVED -- 187, the class silent, the field empty", u4_census),
    ("U5", "THE SHIPPED CASTS -- 7 clean, ef424 x448_y384 named, and the ODIN PAIR FROZEN",
     u5_shipped_casts),
    ("U6", "THE ACK AND THE CONSTANT -- literal boolean, and NO BYTE MOVES", u6_ack_and_constant),
    ("U7", "THE EFFECTIVE COVER -- the EDIT surface, 340/151/45/7/70/36/60/199 re-rolled",
     u7_effective_cover),
]
#: the gates that ride on :class:`Data`.  U7 builds its own walk, so `py u1_gates.py U7` must not pay
#: for a corpus pass it never reads -- and a board that costs 9 minutes to run one gate is a board
#: nobody runs.
DATA_GATES = frozenset(("U1", "U2", "U3", "U4", "U5", "U6"))


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                          # noqa: BLE001
        pass
    only = set(a.upper() for a in (argv or sys.argv[1:]) if a.upper().startswith("U"))
    print("W6b-3 (iii) DISCLOSED + (iv) ADOPTED -- THE SECOND ARRAY, as SHIPPED KIT BEHAVIOUR")
    print("corpus: %s" % CORPUS)
    print("THE LINE: THE SECOND ARRAY IS APPLIED.  THE READER JOIN IS TAKEN ON THE CELL THE HARDWARE "
          "SAMPLES;")
    print("          bytes move on the EDIT surface ONLY, and CENSUS + LICENSED stay byte-identical.")
    print("          (RETIRED at (iv): 'NOTHING IS MODELLED WITH IT, AND NO EMITTED BYTE MOVES.')")
    print("0.97 on ef038, GENERALISED on ef227 + ef446, operation ADD by value test . the labelling "
          "SETTLED (SWAPPED)")
    print("the v axis RESOLVED . FOUR riders still open, reach = the INCUMBENT records only")
    print("U7 measures the OTHER surface: RP.EDIT_CHANNELS, the one every author-facing entry point "
          "defaults to")
    print("=" * 78)
    running = [t for t, _, _ in GATES if not only or t in only]
    D = Data() if any(t in DATA_GATES for t in running) else None
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
