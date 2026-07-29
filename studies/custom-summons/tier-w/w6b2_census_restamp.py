r"""TIER W rung W6b-2, BUILD-LIST ROW 9 -- THE CENSUS RE-STAMP.  `py w6b2_census_restamp.py`.

W6b-1 shipped `reskin.page_cells` (keyed ``(writer tag, x, y)``), the per-VRAM-CELL map that names
the lower 128 lines of an ``h == 256`` id-0 page rect -- something the OLDER rect view
(``reskin.scenery_pages``, keyed ``(tag, x)``) structurally cannot do at all. `census/pages.json`
predates that map: it still stamps every such lower half's ``addressable_via`` with the STALE
string below, recording only what the PRE-W6b-1 rect key could name. `W6b2-ATTRIBUTION.md` sec 6
row 3 names the consequence in one sentence: **that stale field is why one instrument scored the
hand-off at 79 cells and another at 199, and it will keep regenerating the dispute until a census
refresh re-stamps it.** Sec 7 row 9 is the fix this file performs, and both of its predicates,
never reconciled into one number:

    93 = ALL program-gained y=384 cells the shipped per-cell map NAMES
         (this record's number, and the one the map is asked about)
    83 = the SUBSET of those 93 that carries the census's stale `hz_unaddressable_lower_half` flag
         (a mid-round audit's number -- fewer than 93 because some program-gained lower halves were
         ALREADY nameable pre-W6b-1, e.g. an id-9 alternate block, which is never a rect split)
    83 + 55 channel-G (independently re-derived here, never quoted) = 138, the y=384 hazard total
         `w6b2_gates.py` H6/H12 pin and print -- so this file's own numbers must land on a total the
         sibling gate already re-measures, or something here is wrong.

WHAT THIS FILE DOES, AND ONLY THIS -- IT NEVER TOUCHES ANOTHER FILE:

  (a) back up `census/pages.json` to `pages.json.pre-restamp` EXACTLY ONCE.  A second run finds the
      backup already there and REFUSES to overwrite it -- the one thing that must never happen is
      the pre-restamp snapshot getting silently replaced by an already-restamped file.
  (b) for every writer entry whose `addressable_via` still carries the STALE string, ask
      `reskin.page_cells` -- over the writer's own container, exactly as `w6b2_gates.py` H12 does --
      whether the SHIPPED map names that `(tag, x, y)` key.  If it does, the entry is re-stamped to
      name the map, in the census's own naming convention (`reskin.scenery_pages[('s0',448)]` /
      `reskin.id9_pages[('s0',832)]` -> `reskin.page_cells[('s0',704,384)]`).  The record's PRE-
      mutation `addressable_via` list is preserved verbatim in a NEW field, `addressable_via_pre_w6b1`
      -- nothing is destroyed, and a reader can always recover what the census said before this rung.
      `hz_unaddressable_lower_half` is NEVER touched: it is `w6b2_gates.py`'s own re-measured
      predicate (H6's 138, H12's 83) and this file must not move a number that gate re-derives.
  (c) print BOTH predicates sec 7 row 9 demands, computed here from the raw lane artifact and the
      corpus -- never quoted from a dossier, and never read back off the mutation this file just
      made (the 83 and the channel-G 55 both come from fields this script does not write).
  (d) BE SAFE TO RE-RUN: a second pass finds zero stale-and-nameable entries left (the mutation is
      the reason) and reports so in those words, then re-prints the same two predicates unchanged,
      because they are read from fields this file never mutates.

Reads the extracted corpus and the SCRATCH lane artifacts only -- no install read, no deploy, no
install write, no git commit.  Provenance: every number this file prints is a cell coordinate, a
writer tag, or a count -- never a stock byte.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                              # noqa: E402  (sets up sys.path)
import summon_camera as W                                         # noqa: E402

SCRATCH = W.SCRATCH_CORPUS
W6B = os.path.join(SCRATCH, "texel-w6b")
LANE = os.path.join(W6B, "w6b2")
CENSUS = os.path.join(W6B, "census", "pages.json")
BACKUP = CENSUS + ".pre-restamp"

#: THE STALE VALUE -- the pre-W6b-1 `(tag, x)` rect key's own words for a cell it could not name.
#: Quoted verbatim from `census/pages.json` and from `w6b2_gates.py` H12's own print line.
STALE = "UNADDRESSABLE (lower half of an h=256 rect)"

#: THE GRANULARITY STATEMENT (`W6b2-ATTRIBUTION.md` sec 1), mirrored byte-for-byte from
#: `w6b2_gates.py`'s own `dec`/`cover` so this file's channel re-derivation cannot silently drift
#: from the sibling gate's: one tpage word names a COLUMN of two stacked 128-line census cells.
PAGE_HW, PAGE_LINES, CELL_LINES = 64, 256, 128


def dec(tp: int) -> Tuple[int, int, int]:
    """(page_x, page_y, bpp) from a nine-bit PSX tpage word -- == `w6b2_gates.dec`."""
    return (tp & 0x0F) * PAGE_HW, ((tp >> 4) & 1) * PAGE_LINES, RS.SO_BPP[(tp >> 7) & 3]


def cover(px: int, py: int) -> List[Tuple[int, int]]:
    """A page covers BOTH stacked 128-line cells of its column -- == `w6b2_gates.cover`."""
    return [(px, py), (px, py + CELL_LINES)]


def verdict(cnt: Counter):
    """A depth is stated only if the evidence is UNANIMOUS -- == `w6b2_gates.verdict`."""
    return list(cnt)[0] if len(cnt) == 1 else None


def _load(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- (a) THE ONE-TIME BACKUP
def backup_once() -> bool:
    """Back up `pages.json` to `pages.json.pre-restamp` EXACTLY ONCE.

    Refuses to overwrite an existing backup -- a second run of this script must never let an
    already-restamped `pages.json` get copied over the one true pre-restamp snapshot.  Returns
    whether a NEW backup was made (False on every re-run after the first).
    """
    if os.path.exists(BACKUP):
        print("[backup] %s already exists -- NOT overwritten (this is a re-run)" % BACKUP)
        return False
    shutil.copy2(CENSUS, BACKUP)
    print("[backup] %s -> %s" % (CENSUS, BACKUP))
    return True


# --------------------------------------------------------------------------- reskin.page_cells, cached
class PageCellCache:
    """`reskin.page_cells` PER CONTAINER, asked directly and only once per `ef` -- exactly the
    question `w6b2_gates.py` H12 puts to `reskin` itself rather than assuming the shipped map covers
    what the census's stale flag says it cannot."""

    def __init__(self) -> None:
        self._m: Dict[int, dict] = {}

    def get(self, ef: int) -> dict:
        if ef not in self._m:
            path = os.path.join(SCRATCH, "ef%03d.bytes" % ef)
            try:
                with open(path, "rb") as fh:
                    blob = fh.read()
                self._m[ef] = RS.page_cells(blob)
            except Exception:
                self._m[ef] = {}          # unreadable/unparseable container -> names nothing; skip
        return self._m[ef]

    def names(self, ef: int, tag: str, x: int, y: int) -> bool:
        return (tag, x, y) in self.get(ef)

    def names_writer(self, ef: int, writer: dict, x: int, y: int) -> bool:
        """Same question, but resolving `PageCell`'s own key convention from a CENSUS writer record.

        `reskin.page_cells` keys an id-9 alternate block ``"id9.%s" % chunk_tag`` (see
        :func:`reskin.id9_pages`), but the census's own ``writers[i]["tag"]`` stores the PLAIN chunk
        tag for every writer kind alike. Matching `writer["tag"]` verbatim against an id-9 writer
        therefore MISSES the map's own entry -- exactly the 93-vs-83 gap (10 of the 93 program-gained
        y=384 cells are id-9-only, so they were never lower-half-flagged and were never STALE, but a
        naive tag match would still under-count how many the map names).
        """
        tag = ("id9.%s" % writer["tag"]) if writer.get("cls") == "id9" else writer["tag"]
        return self.names(ef, tag, x, y)


# --------------------------------------------------------------------------- (b) THE RE-STAMP
def restamp(census: List[dict], pc: PageCellCache) -> Tuple[int, int]:
    """Re-stamp every writer entry whose `addressable_via` is still STALE but which the SHIPPED
    per-cell map names.  Mutates `census` in place; returns (cells touched, entries re-stamped).

    Deliberately narrow: an entry that is STALE but which `page_cells` does NOT name (none exist
    today -- verified below -- but the check is the point) is left exactly as it was.  A restamp
    that silently claimed a name the map does not give would be worse than the bug it fixes.
    """
    cells = entries = 0
    for r in census:
        ef = r["ef"]
        writers = r["writers"]
        av = r["addressable_via"]
        touched_this_cell = False
        for i, val in enumerate(av):
            if val != STALE:
                continue
            w = writers[i]
            x, y = r["vram_x"], r["vram_y"]
            if not pc.names_writer(ef, w, x, y):
                continue                   # the map does not name it either -- leave the flag alone
            if not touched_this_cell:
                if "addressable_via_pre_w6b1" not in r:
                    r["addressable_via_pre_w6b1"] = list(av)     # THE ORIGINAL LIST, NEVER DESTROYED
                touched_this_cell = True
            # name it the way page_cells ACTUALLY keys it (the id-9 prefix included), not the
            # census's plain writer tag -- see PageCellCache.names_writer.
            key_tag = ("id9.%s" % w["tag"]) if w.get("cls") == "id9" else w["tag"]
            av[i] = "reskin.page_cells[(%r,%d,%d)]" % (key_tag, x, y)
            entries += 1
        if touched_this_cell:
            cells += 1
    return cells, entries


# --------------------------------------------------------------------------- (c) THE TWO PREDICATES
def _index(census: List[dict]) -> Dict[Tuple[int, int, int], dict]:
    return {(r["ef"], r["vram_x"], r["vram_y"]): r for r in census}


def _roll_program(C: Dict[Tuple[int, int, int], dict]
                   ) -> Dict[Tuple[int, int, int], Optional[int]]:
    """CHANNEL P re-rolled from `tpage_sweep.json`'s RAW hits at PAGE granularity -- `w6b2_gates.py`
    H2/H3's own method (`Data._roll_program` + `Data.pv`), reading the raw `sweep.hits`, NEVER L1's
    own per-cell rollup (`join.cells`)."""
    sweep = _load(os.path.join(LANE, "tpage_sweep.json"))["sweep"]
    prog: Dict[Tuple[int, int, int], Counter] = defaultdict(Counter)
    for h in sweep["hits"]:
        px, py, bpp = dec(h["value"])
        for c in cover(px, py):
            k = (h["ef"], c[0], c[1])
            if k in C:
                prog[k][bpp] += 1
    return {k: verdict(c) for k, c in prog.items()}


def _roll_so_page(C: Dict[Tuple[int, int, int], dict]
                   ) -> Dict[Tuple[int, int, int], Optional[int]]:
    """CHANNEL G -- the container's own `so` records re-read at PAGE granularity (`w6b2_gates.py`
    H3/H10's method: `reskin.attribution(..., include_direct=True)`), over the whole corpus."""
    import glob
    sopage: Dict[Tuple[int, int, int], Counter] = defaultdict(Counter)
    for p in sorted(glob.glob(os.path.join(SCRATCH, "ef*.bytes"))):
        ef = int(os.path.basename(p)[2:5])
        with open(p, "rb") as fh:
            blob = fh.read()
        try:
            # ★ W6b-3 NARROWING, DECLARED: the census artifact describes the SHIPPED census, and the
            # shipped census (`repaint.bound_models`) is INCUMBENT-only.  A future re-stamp left at
            # `attribution`'s post-W6b-3 default would silently re-aim `pages.json` onto a population
            # the kit does not emit -- and `w6b3i_gates` I10 verifies the freeze against this.
            a = RS.attribution(blob, include_direct=True, witness=RS.WITNESS_INCUMBENT)
        except Exception:
            continue
        for b in a.bindings:
            px, py, bpp = dec(b.tpage)
            for c in cover(px, py):
                k = (ef, c[0], c[1])
                if k in C:
                    sopage[k][bpp] += 1
    return {k: verdict(c) for k, c in sopage.items()}


def program_gained_y384(C: Dict[Tuple[int, int, int], dict],
                         pv: Dict[Tuple[int, int, int], Optional[int]]
                         ) -> List[Tuple[int, int, int]]:
    """The depth-unknown, non-creature, y=384 cells channel P names UNANIMOUSLY -- a multi-valued
    cell is the program-dual-depth hazard (22 cells, sec 2), not a verdict, and is excluded here."""
    out = []
    for k, v in pv.items():
        if v is None or k[2] != 384:
            continue
        r = C.get(k)
        if r is None or "creature" in r["classes"] or not r["hz_depth_unknown"]:
            continue
        out.append(k)
    return sorted(out)


def channel_g_gained_y384_flagged(C: Dict[Tuple[int, int, int], dict],
                                   pv: Dict[Tuple[int, int, int], Optional[int]],
                                   gv: Dict[Tuple[int, int, int], Optional[int]]) -> int:
    """Of the cells that gain ONLY from channel G (channel P silent there), the count that ALSO
    carries the census's stale `hz_unaddressable_lower_half` flag -- independent of
    `program_gained_y384` and of the restamp, so it is a genuine cross-check, not an echo."""
    flagged = 0
    for k, r in C.items():
        if "creature" in r["classes"] or not r["hz_depth_unknown"]:
            continue
        if k[2] != 384 or pv.get(k) is not None or gv.get(k) is None:
            continue                      # not y=384, or channel P already speaks, or G is silent
        if r["hz_unaddressable_lower_half"]:
            flagged += 1
    return flagged


# --------------------------------------------------------------------------- main
def main() -> int:
    backup_once()
    census = _load(CENSUS)
    pc = PageCellCache()

    cells, entries = restamp(census, pc)
    if cells:
        with open(CENSUS, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(census, indent=1))
        print("[restamp] %d cell(s) / %d writer entrie(s) re-stamped -- pages.json REWRITTEN"
              % (cells, entries))
    else:
        print("[restamp] 0 cells to re-stamp -- pages.json already current (safe re-run)")

    # ---------------------------------------------------------- SEC 7 ROW 9'S TWO PREDICATES
    C = _index(census)
    pv = _roll_program(C)
    gv = _roll_so_page(C)
    lower = program_gained_y384(C, pv)
    # "named": for THIS cell's own writer(s) -- never a different cell's tag -- does the SHIPPED
    # map resolve (tag, x, y)?  A tag from an unrelated writer resolving would be a false positive.
    named = sum(1 for k in lower
                if any(pc.names_writer(k[0], w, k[1], k[2]) for w in C[k]["writers"]))
    flagged83 = sum(1 for k in lower if C[k]["hz_unaddressable_lower_half"])
    g55 = channel_g_gained_y384_flagged(C, pv, gv)

    print()
    print("[predicates] W6b2-ATTRIBUTION.md sec 7 row 9, BOTH printed, neither reconciled away:")
    print("   93 = ALL program-gained y=384 cells the map names   -- measured %d" % len(lower))
    print("        ... of which named by the SHIPPED reskin.page_cells -- measured %d" % named)
    print("   83 = the subset carrying the census's stale hz_unaddressable_lower_half flag"
          "   -- measured %d" % flagged83)
    print("   83 + 55 channel-G = 138, the y=384 hazard total w6b2_gates.py H6/H12 pins"
          "   -- measured %d + %d = %d" % (flagged83, g55, flagged83 + g55))

    ok = (len(lower) == named == 93) and (flagged83 == 83) and (g55 == 55) and (flagged83 + g55 == 138)
    if not ok:
        print()
        print("!! SELF-VERIFICATION FAILED: the re-derived predicates do not match "
              "W6b2-ATTRIBUTION.md sec 7 row 9 / w6b2_gates.py's own pins.")
        return 1
    print()
    print("RESULT: 0/0 unexpected -- both predicates re-derived match the record and the sibling"
          " gate's own pins (H6 hz_lower_half=138, H12 prog_lower_halves=93/93).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
