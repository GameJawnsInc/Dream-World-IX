r"""TIER W rung W6b-3 (iii) -- THE SECOND ARRAY, DISCLOSED.  `py u1_gates.py` -> U1..U6.

★ A **NEW FILE**, and that is the point.  `w6b_gates` G6, `w6q_gates` G1/G16, `w6b2i_gates` I5 and
`w6b3i_gates` I6/I9 are RE-DERIVATION PINS over populations this rung must not move, so not one line
of them is edited: this board proves the new behaviour beside them, and the acceptance test for the
rung is **green BEFORE == green AFTER** on all four, plus green here.

    U1  THE READER -- `so_record["second"]` against an INDEPENDENT raw walker, 502/649/293
    U2  THE POPULATION -- 52 cells / 29 containers / 47 fully open, re-derivation-pinned
    U3  THE SUPERSET LAW -- the scoping's 16 SWAPPED + 19 ORIGINAL contained, zero missed
    U4  THE CENSUS DEFAULT IS UNMOVED -- the class silent, the field empty, the page set identical
    U5  THE SHIPPED CASTS -- four cast cells clean, and the ONE that fires named out loud
    U6  THE ACK AND THE CONSTANT -- literal boolean, registered key, and NO BYTE MOVES

★ THE LINE THIS RUNG IMPLEMENTS:

    THE SECOND ARRAY IS READ AND DISCLOSED.  NOTHING IS MODELLED WITH IT, AND NO EMITTED BYTE MOVES.

The evidence it discloses is cast-proven on ONE container at **0.84**; WHICH halfword displaces `u`
rides separately at **0.68**, so BOTH readings are printed and NEITHER is preferred; and the **v axis
is UNRESOLVED** and is not modelled at all.  All three ride IN the quotable constant
(`depth_attribution.U_DISPLACEMENT_CAVEAT`), which is spent at the refusal, the build gate, the
disclosure and the report block -- *a caveat nothing quotes is a wish.*

Reads the extracted corpus at C:\gd\SCRATCH\summon-format ONLY.  No install read, NO deploy, no
install write, no git commit; it writes nothing but its own stdout.  Budget: three rasterising passes
over the 372 containers.  ~6 min end to end on this machine.
"""
from __future__ import annotations

import glob
import os
import struct
import sys
from typing import Dict, List, Set, Tuple

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
    #: ⚠ THE PERMISSIVENESS OBLIGATION ON THE ARC'S OWN COMMITTED SPECS, SWEPT RATHER THAN TYPED.
    #: Both ef424 cast specs -- `odin_channel_a.toml` ROW 2 and its cast-C sibling
    #: `odin_channel_a_c.toml` ROW 2 -- target the one firing cast cell with `enabled = true`, so
    #: re-running EITHER now needs the ack.  Naming only one of them would have been the same class
    #: of omission this whole rung exists to prevent.
    "specs_needing_the_ack": 2,
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

    ★ SWEPT, NEVER TYPED.  This rung arms a build gate, and a build gate that fires on the arc's own
    committed cast records is a permissiveness change the OWNER has to decide about -- so the list of
    specs it touches is DERIVED at gate time from the specs themselves, through the same `texel_page`
    resolution a build makes.  A hand-written list is exactly how the cast-C sibling gets missed.
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
        cells = {p.name: p.cell for p in RP.scenery_texel_pages(blob, ef)}
        for t in rows:
            cell = cells.get(t.get("name"))
            if cell is not None and ("ef%03d" % ef, tuple(cell)) in firing:
                out.append(os.path.basename(path))
                break
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
    print("   %d conservative extras -- cells whose movers would not actually vacate them under "
          "either arithmetic; asking WOULD force the labelling choice at 0.68"
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
    chk("committed cast specs whose ENABLED row now needs the ack", len(specs),
        PIN["specs_needing_the_ack"])
    chk("...and they are BOTH ef424 casts", specs,
        ["odin_channel_a.toml", "odin_channel_a_c.toml"])
    for c, k in clean:
        print("      CLEAN  %-6s x%d_y%d" % (c, k[0], k[1]))
    for c, k in firing:
        note = D.fire[c][k]
        print("      FIRES  %-6s x%d_y%d  (%s)" % (c, k[0], k[1], note["source"]))
    print("   ★ ef424 `cell.s0.x448_y384` is the W6b-3ii ORDER RIDER -- its only incumbent reader "
          "carries A=0x0080/B=0, and under SWAPPED it reads column 512.  A LEAD, not a claim.")
    # ⚠ BOTH committed ef424 cast specs target it -- `odin_channel_a.toml` ROW 2 and its cast-C
    # sibling `odin_channel_a_c.toml` ROW 2 (cast B is VOID, so the SIBLING is the live one).  Swept
    # rather than typed: every `[reskin]` spec in this directory, resolved through `texel_page`.
    print("   ⚠ %d committed cast spec(s) target a firing cell with `enabled = true`: %s.  "
          "Re-running either cast now needs `%s = true` on that row.  They are committed CAST "
          "RECORDS and are NOT edited by this rung -- an owner call, stated rather than made "
          "silently." % (len(specs), ", ".join("`%s`" % s for s in specs), DA.ACK_MOVER_KEY))


def u6_ack_and_constant(D: Data) -> None:
    print("U6  THE ACK AND THE CONSTANT -- literal boolean, registered key, and NO BYTE MOVES")
    import hashlib
    import tempfile
    chk("the key is registered in _TEXEL_KEYS", DA.ACK_MOVER_KEY in RP._TEXEL_KEYS, True)
    chk("the class is NOT unaddressable", "second-array-mover" in RP._UNADDRESSABLE, False)
    chk("the class is NOT export-blocking", "second-array-mover" in RP._EXPORT_BLOCKING, False)
    chk("no literal `%` in the class text",
        "%" in RP._REFUSAL_TEXT["second-array-mover"].replace("%s", ""), False)
    for piece in ("0.84", "0.68", "UNRESOLVED", "cell.s0.x704_y256"):
        chk("the caveat carries %r" % piece, piece in DA.U_DISPLACEMENT_CAVEAT, True)
    chk("the refusal quotes the caveat", DA.U_DISPLACEMENT_CAVEAT
        in RP._REFUSAL_TEXT["second-array-mover"], True)
    chk("the ack warning quotes the caveat",
        DA.U_DISPLACEMENT_CAVEAT in DA.U_DISPLACEMENT_ACK_WARNING, True)

    # THE REAL BUILD PATH, on a real corpus firing cell.
    ef, cell = 424, "cell.s0.x448_y384"
    with open(os.path.join(CORPUS, "ef%03d.bytes" % ef), "rb") as fh:
        blob = fh.read()
    td = tempfile.mkdtemp(prefix="u1gates-")
    RP.export_art(blob, ef, out_dir=td, scaffold=True, overlays=False)
    row = {"name": cell, "enabled": True, "source": os.path.join(td, "%s.png" % cell),
           "expect_bpp": 8}
    spec = {"reskin": {"effect": ef, "label": "u1gates",
                       "expect_sha256": hashlib.sha256(blob).hexdigest(), "texel": [dict(row)]}}
    refused_by_name = False
    try:
        RP.build(spec, os.path.join(td, "s.toml"), blob=blob)
    except RP.RepaintError as e:
        refused_by_name = "THE SECOND-ARRAY GATE" in str(e)
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
    # ...and with it, the build succeeds and the bytes are what they were BEFORE the class existed
    good = {"reskin": dict(spec["reskin"], texel=[dict(row, **{DA.ACK_MOVER_KEY: True})])}
    with_ack = RP.build(good, os.path.join(td, "s.toml"), blob=blob)
    was = RP._gate_second_array
    try:
        RP._gate_second_array = lambda targets: {}
        before = RP.build(spec, os.path.join(td, "s.toml"), blob=blob)
    finally:
        RP._gate_second_array = was
    chk("EMISSION UNCHANGED: acknowledged bytes == pre-class bytes",
        with_ack.patched == before.patched, True)
    chk("...and this row is a NO-OP repaint, so it is also the stock container",
        with_ack.patched == blob, True)
    notes = " ".join(with_ack.targets[0].hazard_notes)
    chk("the acknowledged case STILL discloses", DA.U_DISPLACEMENT_ACK_WARNING in notes, True)
    with open(os.path.join(td, RP.SCAFFOLD_NAME), encoding="utf-8") as fh:
        scaffold = fh.read()
    chk("the scaffold emits the ack line on the firing row",
        "%s = false" % DA.ACK_MOVER_KEY in scaffold, True)
    chk("...exactly once", scaffold.count("%s = false" % DA.ACK_MOVER_KEY), 1)
    chk("the scaffold prints BOTH readings",
        "SWAPPED  reading" in scaffold and "ORIGINAL reading" in scaffold, True)
    print("   the build path on ef424 %s: refused BY NAME without the ack, built with it, and the "
          "patched bytes are IDENTICAL to the same row built with the gate stubbed out" % cell)
    print("   the caveat carries 0.84 / 0.68 / UNRESOLVED / cell.s0.x704_y256 and is quoted at the "
          "refusal, the gate, the disclosure and the report block")


# --------------------------------------------------------------------------- runner
GATES = [
    ("U1", "THE READER -- 502/649/293, against an INDEPENDENT raw walker", u1_reader),
    ("U2", "THE POPULATION -- 52 cells / 29 containers / 47 open, re-derivation-pinned",
     u2_population),
    ("U3", "THE SUPERSET LAW -- 16 + 19 contained, 35/35, zero missed", u3_superset),
    ("U4", "THE CENSUS DEFAULT IS UNMOVED -- 187, the class silent, the field empty", u4_census),
    ("U5", "THE SHIPPED CASTS -- 7 clean, and ef424 x448_y384 named out loud", u5_shipped_casts),
    ("U6", "THE ACK AND THE CONSTANT -- literal boolean, and NO BYTE MOVES", u6_ack_and_constant),
]


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                          # noqa: BLE001
        pass
    only = set(a.upper() for a in (argv or sys.argv[1:]) if a.upper().startswith("U"))
    print("W6b-3 (iii) GATES -- THE SECOND ARRAY, DISCLOSED, as SHIPPED KIT BEHAVIOUR")
    print("corpus: %s" % CORPUS)
    print("THE LINE: THE SECOND ARRAY IS READ AND DISCLOSED.  NOTHING IS MODELLED WITH IT, AND NO "
          "EMITTED BYTE MOVES.")
    print("0.84 on ONE container . the labelling at 0.68, BOTH readings printed . v UNRESOLVED")
    print("=" * 78)
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
