r"""CHANNEL D, EVERY DRAW -- `py screen_gates.py` prints C1..C9 with PASS/FAIL.

Channel D (``drawn_gates.py``) gives a cell the depth the render target's draw reads it at -- but the
routes census behind it ran ``--no-draw``, so it saw only the draws INTO the target, on 66 containers,
and booked them per CELL.  The draws straight to the SCREEN were never censused, and a cell is not a
picture: several writers upload into one cell over a cast, and the program copies bytes from cell to
cell.  The draw census (``raster.py routes --draw``, its source tracker armed) renders every frame of all
372 containers and books every fragment that SAMPLED a texel against the UPLOAD whose bytes it read --
followed through every copy -- before the cutout test and whether or not it changed a pixel, on the
screen and into the target, with the CLUT each was read through.  This runner charges each upload's
reads to the kit page holding those container bytes; the kit carries the result (``draw_census.py``)
and channel D reads it per page.  It checks:

C1  THE PAGE MAP.  Every 64 x 128 upload of container bytes the plugin made, against the kit's page cells
    (``reskin.page_cells``, THE UPLOAD WALK): the walk names the source of every one, by offset or, on a
    page of one repeated byte, by identical bytes.  THE FALSIFIER is the cursor the kit used before --
    ``w * h * 2`` straight through the id-0 sector pad -- run over the same uploads: it names fewer, and
    the cells the walk moved are counted, by container.
C2  THE RE-DERIVATION.  The census on disk (SCRATCH ``headless/raster/screen``, 372 containers, 0 errors)
    reproduces ``draw_census._READ_ROWS``, ``_READ_CLUT_ROWS`` and ``_COVERED_RANGES`` row for row; every
    page offset in the table is a page the kit derives; the reads it could not charge to one page are
    tallied by reason; and the target books, drawn this time, reproduce the ``--no-draw`` feeds
    (``render_target._FEED_ROWS``) row for row.
C3  THE CALIBRATION.  Every page and every refused cell of the default edit surface (the EDIT reading,
    no acknowledgement) against the reads of its own bytes: read at its own depth only, at its depth AND
    another, only at another, or never; a refusal by class and by how many depths read it.  Pinned, and
    every page read at another depth named -- what the drawn-conflict gate refuses.
C4  THE CHANNEL'S REACH.  Consulting channel D still moves no page and no refusal class on the default
    surface; with the acknowledgement every page it hands out is single-depth, keyed by a CLUT the
    container declares (or direct), measured, and new; the ``bound`` reading does not consult it.
C5  THE TARGET HALF, RE-READ.  The pages the per-cell feeds handed out (the census swapped out), against
    the per-page census: kept, now refused at two depths, re-depthed, or dropped because the feed was
    another record's bytes -- by name; and the render-target remedy recounted.
C6  THE PRE-RUN, AND ITS FALSIFIER.  ``drawn_feed_prerun.py --screen`` paints a page only the screen's
    draws give a depth to, builds it through the kit, and renders stock against the build: its own screen
    draws change frames.  The unedited build moves nothing.
C7  PROVENANCE.  The new tables carry ids, offsets, coordinates, depths and counts only.
C8  THE STAGED CASTS.  The two owner casts' specs (``leviathan_drawn.toml``: zebra on ef179's
    ``cell.s0.x576_y384``, a page only the draws give a depth; ``fenrir_conflict.toml``: parity zebra on
    ef226's ``cell.s0.x576_y384``, an 8bpp page every draw reads at 4bpp) each rebuild their pinned
    container, carry the pre-run's own mark byte for byte, refuse by name without their key, and are
    cast by exactly one bench row.  Proven able to fail: a wrong pin, a stock PNG and a missing row each
    fail it.
C9  THE CASTS RUN OFFLINE.  Each spec's pre-run, on the staged bytes: the drawn page ``DIRECT``, the
    conflict page ``SECOND-PICTURE`` (its two nibble-swapped inks one picture at band scale, the plain
    zebra's two inks not).  About 8 minutes.

Reads `C:\gd\SCRATCH\summon-format` ONLY and writes there -- no install read, no deploy, no commit.

    py screen_gates.py                 # the board
    py screen_gates.py --emit          # print the kit tables from the census on disk (to paste)
"""
from __future__ import annotations

import ast
import bisect
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS_STUDY                                        # noqa: E402,F401  (sets up sys.path)

_REPO = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))

CORPUS = r"C:\gd\SCRATCH\summon-format"
SCREEN = os.path.join(CORPUS, "headless", "raster", "screen")
PRERUN = os.path.join(_HERE, "drawn_feed_prerun.py")

_FAILS: List[str] = []


def chk(name: str, got, want) -> None:
    if got != want:
        _FAILS.append("%s: measured %r, pinned %r" % (name, got, want))


def _cell(k: str):
    m = re.match(r"x(\d+)_y(\d+)(?:@(\d+))?$", k)
    return tuple(int(g) for g in m.groups() if g is not None)


def _load(ef: int) -> bytes:
    with open(os.path.join(CORPUS, "ef%03d.bytes" % ef), "rb") as fh:
        return fh.read()


# --------------------------------------------------------------------------- the kit (imported late)
def _kit():
    from ff9mapkit.summons import depth_attribution as DA
    from ff9mapkit.summons import draw_census as DC
    from ff9mapkit.summons import render_target as RT
    from ff9mapkit.summons import repaint as RP
    from ff9mapkit.summons import reskin as RS
    assert os.path.normcase(os.path.abspath(DC.__file__)).startswith(
        os.path.normcase(os.path.join(_REPO, "ff9mapkit"))), DC.__file__
    return DA, DC, RT, RP, RS


def _pages(ef: int) -> Dict[int, object]:
    """The kit's page cells of one container, by container offset."""
    _DA, _DC, _RT, _RP, RS = _kit()
    pcs = RS.page_cells(_load(ef))
    out = {pc.off: pc for pc in pcs.values()}
    assert len(out) == len(pcs), "two page cells share an offset"
    return out


# --------------------------------------------------------------------------- the census on disk
#: the reads the re-derivation could not charge to a page, in fragments, by reason -- and, under its own
#: parenthesised name, the reads it charged to several pages at once because their bytes sit in each
UNCHARGED: Counter = Counter()
#: ``(effect, page offset) -> the last frame any draw read the page's bytes on`` -- C2's burst check:
#: every headless cast opens with a caster burst no in-game capture has (~f5-44)
LAST_READ: Dict[tuple, int] = {}
BURST_LAST = 45


def census() -> Tuple[dict, List[tuple], List[tuple], List[tuple]]:
    """(routes doc, read rows, CLUT rows, drawn-mode feed rows) -- re-derived from SCRATCH."""
    with open(os.path.join(SCREEN, "routes.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    UNCHARGED.clear()
    LAST_READ.clear()
    rows, cluts, feeds = [], [], []
    for e in sorted(doc["rows"]):
        if "error" in doc["rows"][e]:
            continue
        ef = int(e[2:])
        with open(os.path.join(SCREEN, e, "summary.json"), encoding="utf-8") as fh:
            s = json.load(fh)
        loads = s["loads"]
        blob = _load(ef)
        pages = _pages(ef)
        spans = sorted((off, off + pc.nbytes) for off, pc in pages.items())
        starts = [a for a, _b in spans]

        def page_of(lo: int, hi: int):
            j = bisect.bisect_right(starts, lo) - 1
            return spans[j][0] if j >= 0 and hi < spans[j][1] else None

        copies: Dict[int, List[int]] = {}
        agg: Dict[tuple, list] = {}
        for where in ("screen", "target"):
            for c, ups in sorted(s["read_sources"].get(where, {}).items()):
                cell = _cell(c)
                for key, v in sorted(ups.items(), key=lambda kv: tuple(int(x) for x in kv[0].split(":"))):
                    li = int(key.split(":")[0])
                    if li < 0 or loads[li][5] < 0 or v["lo"] < 0:
                        UNCHARGED["bytes no container upload supplied"] += v["reads"]
                        continue
                    o = loads[li][5]
                    if loads[li][6]:
                        # the uploaded bytes sit at several container offsets, and the census cannot say
                        # which one the program read: charge the read to EVERY page holding them
                        if li not in copies:
                            data, at, cs = blob[o:o + loads[li][3] * loads[li][4] * 2], 0, []
                            while True:
                                at = blob.find(data, at)
                                if at < 0:
                                    break
                                cs.append(at)
                                at += 1
                            copies[li] = cs
                        pgs = sorted({p for cc in copies[li]
                                      for p in [page_of(v["lo"] + cc - o, v["hi"] + cc - o)] if p is not None})
                        UNCHARGED["(charged to every page holding the same bytes)"] += v["reads"] if pgs else 0
                    else:
                        pgs = [p for p in [page_of(v["lo"], v["hi"])] if p is not None]
                    if not pgs:
                        UNCHARGED["container bytes outside any one page"] += v["reads"]
                        continue
                    for pg in pgs:
                        a = agg.setdefault((pg,) + cell, [0, 0, set(), 0, set(), Counter()])
                        if where == "screen":
                            a[0] += v["reads"]
                            a[1] += v["shown"]
                            a[2].update(v["frame_list"])
                        else:
                            a[3] += v["reads"]
                            a[4].update(v["frame_list"])
                        for k, n in v["cluts"].items():
                            a[5][_cell(k)] += n
                        LAST_READ[(ef, pg)] = max(LAST_READ.get((ef, pg), -1), v["frames"][1])
        for k in sorted(agg):
            sr, sh, sf, tr, tf, cl = agg[k]
            pg, x, y, bpp = k
            rows.append((ef, pg, x, y, bpp, sr, sh, len(sf), tr, len(tf)))
            for cc, n in sorted(cl.items()):
                cluts.append((ef, pg, x, y, bpp) + cc + (n,))
        for c, v in sorted(s["render_target_cells"].items()):
            feeds.append((ef,) + _cell(c) + (v["pixels"], v["n_frames"]))
    return doc, rows, cluts, feeds


def _ranges(ids) -> List[Tuple[int, int]]:
    out: List[list] = []
    for i in sorted(ids):
        if out and i == out[-1][1] + 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return [tuple(r) for r in out]


def emit() -> int:
    doc, rows, cluts, _f = census()

    def block(name: str, rs: List[tuple], per: int) -> str:
        out = ["%s: Tuple[Tuple[int, ...], ...] = (" % name]
        for i in range(0, len(rs), per):
            out.append("    " + " ".join("%r," % (r,) for r in rs[i:i + per]))
        out.append(")")
        return "\n".join(out)
    covered = _ranges(int(e[2:]) for e, r in doc["rows"].items() if "error" not in r)
    print(block("_READ_ROWS", rows, 3))
    print()
    print(block("_READ_CLUT_ROWS", cluts, 3))
    print()
    print(block("_COVERED_RANGES", covered, 8).replace("Tuple[Tuple[int, ...], ...]", "Tuple[Tuple[int, int], ...]"))
    print("\n# %d containers, %d read rows, %d CLUT rows; uncharged %s"
          % (doc["containers"], len(rows), len(cluts), dict(UNCHARGED)), file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- THE PINS (this runner's own walk)
PIN_PAGE_MAP = {'named by offset': 2448, 'named by identical bytes (a page of one repeated byte)': 200,
                'into a cell the kit has no page for': 93}
PIN_PAGE_MAP_OLD = {'named by offset': 1609, 'NOT NAMED': 914,
                    'named by identical bytes (a page of one repeated byte)': 125,
                    'into a cell the kit has no page for': 93}
PIN_MOVED = (943, 236)
PIN_ROWS = (2598, 3417)
PIN_UNCHARGED = {'(charged to every page holding the same bytes)': 199204812,
                 'bytes no container upload supplied': 573556309,
                 'container bytes outside any one page': 81203770}
PIN_PAGES = {'so-page, read at ONLY another depth': 8,
             'so-page, read at its depth AND another': 1,
             'so-page, read at its depth only': 11,
             'so-page, read at unread': 3,
             'so-uv, read at ONLY another depth': 47,
             'so-uv, read at its depth AND another': 33,
             'so-uv, read at its depth only': 160,
             'so-uv, read at unread': 26}
PIN_PAGES_ELSEWHERE = [(179, 'cell.s0.x704_y384', 8, 'so-page', (4,)),
                       (203, 'cell.s0.x576_y384', 15, 'so-uv', (8,)),
                       (203, 'cell.s0.x640_y384', 15, 'so-uv', (8,)),
                       (205, 'cell.s0.x448_y256', 8, 'so-uv', (4, 8)),
                       (205, 'cell.s0.x512_y384', 4, 'so-page', (8,)),
                       (225, 'cell.s0.x640_y384', 4, 'so-uv', (4, 8)),
                       (225, 'cell.s1.x448_y384', 8, 'so-uv', (4, 8)),
                       (225, 'cell.s1.x512_y384', 8, 'so-uv', (4, 8)),
                       (226, 'cell.s0.x576_y384', 8, 'so-page', (4,)),
                       (227, 'cell.id9.s0.x832_y384', 8, 'so-uv', (4, 8)),
                       (227, 'cell.s0.x512_y384', 4, 'so-uv', (4, 8)),
                       (227, 'cell.s1.x832_y384', 8, 'so-uv', (4, 8)),
                       (228, 'cell.s0.x512_y384', 8, 'so-page', (4,)),
                       (254, 'cell.s0.x448_y256', 8, 'so-uv', (4, 8)),
                       (255, 'cell.s0.x448_y256', 8, 'so-uv', (4, 8)),
                       (294, 'cell.s0.x512_y384', 8, 'so-page', (4,)),
                       (381, 'cell.id9.s0.x768_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.id9.s0.x768_y384', 4, 'so-uv', (8,)),
                       (381, 'cell.s0.x512_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s0.x512_y384', 4, 'so-uv', (8,)),
                       (381, 'cell.s0.x576_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s0.x640_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s0.x704_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s0.x704_y384', 15, 'so-uv', (8,)),
                       (381, 'cell.s1.x704_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s1.x704_y384', 15, 'so-uv', (4, 8)),
                       (381, 'cell.s1.x768_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s1.x768_y384', 4, 'so-uv', (8,)),
                       (381, 'cell.s1.x832_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s1.x832_y384', 4, 'so-uv', (8,)),
                       (381, 'cell.s2.x512_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s2.x512_y384', 4, 'so-uv', (8,)),
                       (381, 'cell.s2.x576_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s2.x576_y384', 4, 'so-uv', (4, 8)),
                       (381, 'cell.s2.x640_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s2.x640_y384', 8, 'so-uv', (4,)),
                       (381, 'cell.s3.x704_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s3.x704_y384', 15, 'so-uv', (8,)),
                       (381, 'cell.s3.x768_y256', 4, 'so-uv', (4, 8)),
                       (381, 'cell.s4.x512_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s4.x512_y384', 4, 'so-uv', (8,)),
                       (381, 'cell.s4.x576_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s4.x576_y384', 4, 'so-uv', (8,)),
                       (381, 'cell.s4.x640_y256', 4, 'so-uv', (4, 8)),
                       (381, 'cell.s4.x640_y384', 8, 'so-uv', (4, 8)),
                       (381, 'cell.s5.x448_y256', 8, 'so-uv', (4, 8)),
                       (381, 'cell.s5.x512_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s5.x512_y384', 4, 'so-uv', (8,)),
                       (381, 'cell.s5.x576_y256', 4, 'so-uv', (4, 8)),
                       (381, 'cell.s5.x576_y384', 4, 'so-uv', (8,)),
                       (381, 'cell.s6.x640_y384', 8, 'so-uv', (4, 8)),
                       (381, 'cell.s6.x704_y256', 4, 'so-uv', (4, 8)),
                       (381, 'cell.s6.x704_y384', 15, 'so-uv', (8,)),
                       (381, 'cell.s6.x768_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s7.x448_y384', 8, 'so-uv', (4,)),
                       (381, 'cell.s7.x832_y256', 4, 'so-uv', (4, 8)),
                       (381, 'cell.s8.x576_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s8.x576_y384', 4, 'so-uv', (8,)),
                       (381, 'cell.s8.x640_y256', 4, 'so-uv', (8,)),
                       (381, 'cell.s8.x704_y384', 15, 'so-uv', (4, 8)),
                       (381, 'cell.s8.x768_y384', 4, 'so-uv', (4, 8)),
                       (384, 'cell.s0.x512_y256', 8, 'so-uv', (4, 8)),
                       (384, 'cell.s0.x512_y384', 8, 'so-uv', (4, 8)),
                       (387, 'cell.s0.x576_y384', 8, 'so-uv', (4, 8)),
                       (387, 'cell.s0.x640_y384', 8, 'so-page', (4,)),
                       (387, 'cell.s0.x704_y256', 8, 'so-uv', (4, 8)),
                       (405, 'cell.s0.x512_y384', 8, 'so-uv', (4, 8)),
                       (405, 'cell.s0.x576_y384', 15, 'so-uv', (4,)),
                       (405, 'cell.s0.x704_y384', 4, 'so-uv', (4, 8)),
                       (424, 'cell.s0.x448_y256', 8, 'so-uv', (4, 8)),
                       (429, 'cell.s0.x448_y256', 15, 'so-uv', (8,)),
                       (429, 'cell.s0.x448_y384', 15, 'so-uv', (4,)),
                       (447, 'cell.s0.x640_y384', 8, 'so-uv', (4,)),
                       (447, 'cell.s1.x448_y384', 8, 'so-uv', (4,)),
                       (447, 'cell.s1.x832_y256', 4, 'so-uv', (4, 8)),
                       (447, 'cell.s2.x576_y256', 4, 'so-uv', (8,)),
                       (447, 'cell.s2.x640_y256', 4, 'so-uv', (8,)),
                       (447, 'cell.s2.x704_y384', 15, 'so-uv', (4, 8)),
                       (486, 'cell.s0.x448_y256', 8, 'so-uv', (4, 8)),
                       (490, 'cell.s0.x576_y384', 8, 'so-uv', (4, 8)),
                       (492, 'cell.s0.x512_y256', 8, 'so-uv', (4, 8)),
                       (492, 'cell.s0.x512_y384', 8, 'so-uv', (4, 8)),
                       (496, 'cell.s0.x448_y256', 8, 'so-uv', (4,)),
                       (498, 'cell.s0.x448_y384', 4, 'so-page', (4, 8)),
                       (498, 'cell.s0.x640_y256', 4, 'so-uv', (8,)),
                       (499, 'cell.s0.x704_y384', 4, 'so-page', (8,)),
                       (502, 'cell.s0.x448_y256', 8, 'so-uv', (4, 8)),
                       (502, 'cell.s0.x512_y384', 4, 'so-page', (8,)),
                       (510, 'cell.s0.x640_y384', 4, 'so-uv', (4, 8))]
PIN_REFUSED = {'array-dual-depth, read at no depth': 2,
               'array-dual-depth, read at one depth': 9,
               'array-dual-depth, read at two depths': 1,
               'array-vs-column-depth, read at one depth': 2,
               'depth-unknown, read at no depth': 386,
               'depth-unknown, read at one depth': 1665,
               'depth-unknown, read at two depths': 214,
               'displaced-readerless, read at no depth': 2,
               'displaced-readerless, read at one depth': 40,
               'displaced-readerless, read at two depths': 3,
               'displaced-readership-substituted, read at one depth': 9,
               'displaced-readership-substituted, read at two depths': 1,
               'displaced-vs-page-depth, read at two depths': 1,
               'program-dual-depth, read at no depth': 6,
               'program-dual-depth, read at one depth': 10,
               'program-dual-depth, read at two depths': 8}
PIN_BURST = [(389, 'cell.s0.x448_y256', 'page')]
PIN_REACH = (1665, 329, {4: 697, 8: 944, 15: 24})
PIN_OLD = (187, {'kept at the same depth': 145, 'refused': 41, 'dropped': 1})
PIN_OLD_MOVED = [(14, 'cell.s0.x640_y384', 8, 'refused: read at two depths (4, 8)'),
                 (14, 'cell.s0.x704_y256', 8, 'refused: read at two depths (4, 8)'),
                 (26, 'cell.s0.x576_y256', 8, 'refused: read at two depths (4, 8)'),
                 (26, 'cell.s0.x704_y256', 8, 'refused: read at two depths (4, 8)'),
                 (27, 'cell.s0.x576_y256', 8, 'refused: read at two depths (4, 8)'),
                 (42, 'cell.s0.x448_y256', 8, 'refused: read at two depths (4, 8)'),
                 (76, 'cell.s0.x576_y256', 8, 'refused: read at two depths (4, 8)'),
                 (78, 'cell.s0.x576_y256', 8, 'refused: read at two depths (4, 8)'),
                 (78, 'cell.s0.x704_y256', 8, 'refused: read at two depths (4, 8)'),
                 (87, 'cell.s0.x448_y256', 8, 'refused: read at two depths (4, 8)'),
                 (87, 'cell.s0.x448_y384', 8, 'refused: read at two depths (4, 8)'),
                 (90, 'cell.s0.x448_y384', 8, 'refused: read at two depths (4, 8)'),
                 (94, 'cell.s0.x512_y256', 8, 'refused: read at two depths (4, 8)'),
                 (125, 'cell.s0.x512_y256', 8, 'refused: read at two depths (4, 8)'),
                 (125, 'cell.s0.x576_y256', 4, 'refused: read at two depths (4, 8)'),
                 (127, 'cell.s0.x704_y256', 8, 'refused: read at two depths (4, 8)'),
                 (127, 'cell.s0.x704_y384', 8, 'refused: read at two depths (4, 8)'),
                 (129, 'cell.s0.x448_y256', 8, 'refused: read at two depths (4, 8)'),
                 (129, 'cell.s0.x448_y384', 8, 'refused: read at two depths (4, 8)'),
                 (129, 'cell.s0.x512_y256', 4, 'refused: read at two depths (4, 8)'),
                 (129, 'cell.s0.x512_y384', 4, 'refused: read at two depths (4, 8)'),
                 (140, 'cell.s0.x640_y384', 8, 'refused: read at two depths (4, 8)'),
                 (140, 'cell.s0.x704_y256', 8, 'refused: read at two depths (4, 8)'),
                 (145, 'cell.s0.x448_y384', 8, 'refused: read at two depths (4, 8)'),
                 (150, 'cell.s0.x512_y256', 8, 'refused: read at two depths (4, 8)'),
                 (154, 'cell.s0.x512_y256', 8, 'refused: read at two depths (4, 8)'),
                 (178, 'cell.s0.x448_y256', 8, 'refused: read at two depths (4, 8)'),
                 (201, 'cell.s0.x512_y384', 8, 'refused: read at two depths (4, 8)'),
                 (211, 'cell.s0.x448_y384', 8, 'refused: read at two depths (4, 8)'),
                 (223, 'cell.s0.x512_y256', 8, 'refused: read at two depths (4, 8)'),
                 (223, 'cell.s0.x576_y256', 4, 'refused: read at two depths (4, 8)'),
                 (236, 'cell.s0.x512_y256', 8, 'refused: read at two depths (4, 8)'),
                 (237, 'cell.s0.x512_y256', 8, 'refused: read at two depths (4, 8)'),
                 (251, 'cell.s0.x512_y384', 8, 'dropped: no read of its own bytes'),
                 (276, 'cell.id9.s0.x320_y256', 8, 'refused: read at two depths (4, 8)'),
                 (384, 'cell.s0.x704_y256', 8, 'refused: read at two depths (4, 8)'),
                 (392, 'cell.s0.x448_y384', 4, 'refused: read at two depths (4, 8)'),
                 (392, 'cell.s0.x512_y256', 8, 'refused: read at two depths (4, 8)'),
                 (436, 'cell.s0.x448_y256', 8, 'refused: read at two depths (4, 8)'),
                 (436, 'cell.s0.x512_y256', 8, 'refused: read at two depths (4, 8)'),
                 (492, 'cell.s0.x704_y256', 8, 'refused: read at two depths (4, 8)'),
                 (504, 'cell.s0.x448_y256', 8, 'refused: read at two depths (4, 8)')]
PIN_REMEDY = (2, 12,
              [(381, 'cell.s0.x704_y384'), (381, 'cell.s1.x704_y384'), (381, 'cell.s3.x704_y384'),
               (381, 'cell.s6.x704_y384'), (381, 'cell.s8.x704_y384'), (429, 'cell.s0.x448_y256'),
               (429, 'cell.s0.x448_y384'), (447, 'cell.s2.x704_y384')])
#: the screen pre-run's vehicle: the screen-only drawn page with the most shown fragments (37.5 M over
#: 36 frames) among the 1,248 the walk found that no other gate refuses -- zebra'd, it changes 36 of
#: 36 frames (1,312,817 px) through its own screen draws, none into a target
PRERUN_SCREEN = (383, "cell.s0.x448_y256")


# --------------------------------------------------------------------------- C1
def _old_cursor(blob: bytes) -> Dict[tuple, int]:
    """The page-cell offsets the kit derived BEFORE the upload walk: one cursor from the pixel stream's
    base advancing ``w * h * 2`` per rect, straight through the id-0 sector pad -- kept here, and only
    here, as C1's falsifier."""
    import struct
    from ff9mapkit.summons import container as EC
    _DA, _DC, _RT, _RP, RS = _kit()
    out: Dict[tuple, int] = {}
    for ch in EC.parse_header(blob, strict=True).chunks:
        res = [r for r in ch.resources if r.id == 0]
        if not res:
            continue
        tag = RS.chunk_tag(ch)
        P = res[0].offset
        pb = P + struct.unpack_from("<i", blob, P)[0]
        cur = P + struct.unpack_from("<i", blob, pb)[0]
        for k in range(struct.unpack_from("<i", blob, pb + 4)[0]):
            x, y, w, h = struct.unpack_from("<4H", blob, pb + 8 + 8 * k)
            for j in range(h // 128):
                out[(tag, x, y + 128 * j)] = cur + j * w * 256
            cur += w * h * 2
    return out


def c1_page_map() -> None:
    _DA, _DC, _RT, _RP, RS = _kit()
    with open(os.path.join(SCREEN, "routes.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    unit = 0x4000
    new, old, moved, moved_in, wrong = Counter(), Counter(), 0, set(), []
    for e in sorted(doc["rows"]):
        ef = int(e[2:])
        with open(os.path.join(SCREEN, e, "summary.json"), encoding="utf-8") as fh:
            loads = json.load(fh)["loads"]
        blob = _load(ef)
        pcs = list(RS.page_cells(blob).values())
        naive = _old_cursor(blob)
        for pc in pcs:
            if pc.kind == "id9":                     # an id-9 alternate block is its own resource
                naive[(pc.tag, pc.x, pc.y)] = pc.off
            elif naive[(pc.tag, pc.x, pc.y)] != pc.off:
                moved += 1
                moved_in.add(ef)
        at: Dict[tuple, List[tuple]] = defaultdict(list)
        for pc in pcs:
            at[pc.cell].append(((pc.tag, pc.x, pc.y), pc.off))
        for f, x, y, w, h, off, _amb in loads:
            if (w, h) != (64, 128) or off < 0:
                continue
            here = at.get((x, y))
            if not here:
                new["into a cell the kit has no page for"] += 1
                old["into a cell the kit has no page for"] += 1
                continue
            data = blob[off:off + unit]
            for book, offs in ((new, [o for _k, o in here]), (old, [naive[k] for k, _o in here])):
                if off in offs:
                    book["named by offset"] += 1
                elif any(blob[o:o + unit] == data for o in offs):
                    book["named by identical bytes (a page of one repeated byte)"] += 1
                else:
                    book["NOT NAMED"] += 1
                    if book is new:
                        wrong.append((ef, f, x, y, hex(off)))
    print("   the upload walk: %s" % dict(new))
    print("   the old cursor : %s" % dict(old))
    print("   the walk moves %d id-0 cell(s) in %d container(s)" % (moved, len(moved_in)))
    chk("C1 the upload walk names the source of every measured upload", wrong, [])
    chk("C1 the walk's tally", dict(new), PIN_PAGE_MAP)
    chk("C1 THE FALSIFIER: the old cursor fails to name uploads", dict(old), PIN_PAGE_MAP_OLD)
    chk("C1 the cells the walk moved", (moved, len(moved_in)), PIN_MOVED)


# --------------------------------------------------------------------------- C2
def c2_rederive() -> None:
    _DA, DC, RT, _RP, _RS = _kit()
    doc, rows, cluts, feeds = census()
    errs = sorted(e for e, r in doc["rows"].items() if "error" in r)
    print("   draw census: %d containers, %d errors; %d read rows, %d CLUT rows"
          % (doc["containers"], len(errs), len(rows), len(cluts)))
    for k, v in sorted(UNCHARGED.items()):
        print("     %12d fragment(s) -- %s" % (v, k))
    chk("C2 the census covers the corpus, 0 errors", (doc["containers"], errs), (DC.CENSUS_CONTAINERS, []))
    chk("C2 the census's containers are the kit's covered set and the routes census's corpus",
        ({int(e[2:]) for e in doc["rows"]} == set(DC.COVERED), set(DC.COVERED) == set(RT.CENSUS_IDS)),
        (True, True))
    chk("C2 the reads reproduce _READ_ROWS, ROW FOR ROW", tuple(rows), DC._READ_ROWS)
    chk("C2 the CLUT split reproduces _READ_CLUT_ROWS, ROW FOR ROW", tuple(cluts), DC._READ_CLUT_ROWS)
    chk("C2 the table sizes", (len(rows), len(cluts)), PIN_ROWS)
    chk("C2 the reads no page could be charged with, by reason", dict(UNCHARGED), PIN_UNCHARGED)
    bad = sorted({(r[0], r[1]) for r in rows if r[1] not in _pages(r[0])})
    chk("C2 every page offset in the table is a page the kit derives", bad, [])
    kit = {r[:4]: r[4:] for r in RT._FEED_ROWS}
    mine = {r[:4]: r[4:] for r in feeds}
    moved = sorted((k, kit.get(k), mine.get(k)) for k in set(kit) | set(mine) if kit.get(k) != mine.get(k))
    print("   target books drawn vs --no-draw feeds: %d of %d rows moved" % (len(moved), len(kit)))
    chk("C2 the feeds, re-derived with every frame drawn", moved, [])


# --------------------------------------------------------------------------- the walk (C2-C4)
_W: Dict[int, dict] = {}


def _walk() -> Dict[int, dict]:
    if _W:
        return _W
    _DA, DC, _RT, RP, RS = _kit()
    for ef in sorted(DC.COVERED):
        path = os.path.join(CORPUS, "ef%03d.bytes" % ef)
        if not os.path.exists(path):
            continue
        blob = _load(ef)
        base = RP.scenery_surface(blob, ef, channels=RP.EDIT_CHANNELS)
        nod = RP.scenery_surface(blob, ef, channels=tuple(c for c in RP.EDIT_CHANNELS if c != "drawn"))
        acked = RP.scenery_surface(blob, ef, channels=RP.EDIT_CHANNELS, drawn_depth=True)
        _W[ef] = {"blob": blob, "base": base, "nod": nod, "acked": acked,
                  "offs": {pc.name: pc.off for pc in RS.page_cells(blob).values()}}
    return _W


def _depths(RT, ef, cell, page) -> Tuple[int, ...]:
    d = RT.drawn_depth(ef, cell, page)
    return d.depths if d is not None else ()


# --------------------------------------------------------------------------- C3
def c3_calibration() -> None:
    _DA, _DC, RT, RP, _RS = _kit()
    if not LAST_READ:
        census()
    pg, rf, elsewhere, burst, flagged = Counter(), Counter(), [], [], []
    for ef, r in _walk().items():
        pages, refused = r["base"]
        for p in pages:
            dd = set(_depths(RT, ef, p.cell, p.page_offset))
            k = ("unread" if not dd else "its depth only" if dd == {p.bpp}
                 else "its depth AND another" if p.bpp in dd else "ONLY another depth")
            pg["%s, read at %s" % (p.depth_source, k)] += 1
            if dd and dd != {p.bpp}:
                elsewhere.append((ef, p.name, p.bpp, p.depth_source, tuple(sorted(dd))))
            if RP.drawn_conflict(p):
                flagged.append((ef, p.name))
            if dd and LAST_READ.get((ef, p.page_offset), 1 << 30) <= BURST_LAST:
                burst.append((ef, p.name, "page"))
        seen = {p.name for p in pages}
        for q in refused:
            if q.name in seen:
                continue
            seen.add(q.name)
            off = r["offs"].get(q.name)
            dd = _depths(RT, ef, q.cell, off) if off is not None else ()
            if dd and LAST_READ.get((ef, off), 1 << 30) <= BURST_LAST:
                burst.append((ef, q.name, q.klass))
            rf["%s, read at %s" % (q.klass, "no depth" if not dd else "one depth" if len(dd) == 1
                                   else "two depths")] += 1
    for k, v in sorted(pg.items()):
        print("   page    %5d  %s" % (v, k))
    for k, v in sorted(rf.items()):
        print("   refused %5d  %s" % (v, k))
    for e in elsewhere:
        print("     read elsewhere: ef%03d %s %dbpp (%s), read at %s" % e)
    for b in burst:
        print("     read only by f%d (the opening burst's window): ef%03d %s (%s)" % ((BURST_LAST,) + b))
    chk("C3 the pages", dict(pg), PIN_PAGES)
    chk("C3 every page read at another depth, by name", elsewhere, PIN_PAGES_ELSEWHERE)
    chk("C3 the drawn-conflict gate fires on exactly the indexed ones",
        flagged, [(e, n) for e, n, b, s, _d in elsewhere if b != 15 and s != "drawn"])
    chk("C3 the refused page records", dict(rf), PIN_REFUSED)
    chk("C3 the surface cells read only inside the opening burst's window, by name", burst, PIN_BURST)


def _ident(p):
    return (p.name, p.bpp, p.cell, p.depth_source, p.palette_name, p.clut_offset)


# --------------------------------------------------------------------------- C4
def c4_reach() -> None:
    _DA, _DC, RT, RP, _RS = _kit()
    moved, emitted, bad = [], [], []
    for ef, r in _walk().items():
        (bp, br), (np_, nr), (ap, _ar) = r["base"], r["nod"], r["acked"]
        if [_ident(p) for p in bp] != [_ident(p) for p in np_] or \
                sorted((q.name, q.klass) for q in br) != sorted((q.name, q.klass) for q in nr):
            moved.append(ef)
        base_names = {p.name for p in bp}
        for p in ap:
            if p.depth_source != "drawn":
                continue
            emitted.append((ef, p.name, p.bpp))
            dd = RT.drawn_depth(ef, p.cell, p.page_offset)
            keyed = p.bpp == 15 or bool(p.palette_name)
            if dd is None or dd.dual or dd.bpp != p.bpp or not keyed or p.name in base_names:
                bad.append((ef, p.name))
        if any(p.depth_source == "drawn" for p in bp):
            bad.append((ef, "a drawn page WITHOUT the ack"))
    by = Counter(b for _e, _n, b in emitted)
    print("   consulting channel D moved the default surface on %d container(s); with the ack it hands "
          "out %d page(s) in %d container(s) (%s)" % (
              len(moved), len(emitted), len({e for e, _n, _b in emitted}),
              ", ".join("%d at %dbpp" % (by[b], b) for b in sorted(by))))
    chk("C4 consulting moves no page and no refusal class", moved, [])
    chk("C4 every drawn page is single-depth, keyed, measured, and new", bad, [])
    chk("C4 the reach", (len(emitted), len({e for e, _n, _b in emitted}), dict(by)), PIN_REACH)
    w = _walk()[150]
    pb = RP.scenery_surface(w["blob"], 150, channels=RP.READINGS["bound"], drawn_depth=True)[0]
    chk("C4 the `bound` reading does not consult channel D", any(p.depth_source == "drawn" for p in pb),
        False)


# --------------------------------------------------------------------------- C5
_CLAIM = re.compile(r"`(cell\.[^`]+)`, refused as `[^`]+` -- paint it with "
                    r"((?:`[a-z_]+ = true`(?: and )?)+) and `expect_bpp = (\d+)`")


def c5_target_half() -> None:
    DA, DC, RT, RP, _RS = _kit()
    w = _walk()
    # THE OLD CHANNEL: the same acknowledged surface with the draw census swapped out, so channel D speaks
    # from the per-cell feeds alone -- what `export-art --acknowledge-drawn-depth` handed out before.
    keep = (DC.READS, DC.COVERED)
    try:
        DC.READS, DC.COVERED = {}, frozenset()
        old = {}
        for ef in sorted(RT.TARGETS):
            if ef in w:
                for p in RP.scenery_surface(w[ef]["blob"], ef, channels=RP.EDIT_CHANNELS,
                                            drawn_depth=True)[0]:
                    if p.depth_source == "drawn":
                        old[(ef, p.name)] = p.bpp
    finally:
        DC.READS, DC.COVERED = keep
    new = {(ef, p.name): p.bpp for ef in w for p in w[ef]["acked"][0] if p.depth_source == "drawn"}
    fate, moved = Counter(), []
    for k, b in sorted(old.items()):
        ef, name = k
        off = w[ef]["offs"][name]
        dd = RT.drawn_depth(ef, _cell(name.split(".")[-1])[:2], off)
        if k in new and new[k] == b:
            fate["kept at the same depth"] += 1
            continue
        why = ("refused: read at two depths %s" % (dd.depths,) if dd is not None and dd.dual
               else "re-depthed to %d" % new[k] if k in new
               else "dropped: no read of its own bytes" if dd is None else "dropped")
        fate[why.split(":")[0] if why.startswith(("refused", "dropped")) else "re-depthed"] += 1
        moved.append((ef, name, b, why))
    print("   the old channel handed out %d page(s): %s" % (len(old), dict(fate)))
    for m in moved:
        print("     ef%03d %s (was %dbpp): %s" % m)
    chk("C5 the old channel's pages, by fate", (len(old), dict(fate)), PIN_OLD)
    chk("C5 every old page that moved, by name", moved, PIN_OLD_MOVED)
    outright = keyed = 0
    blocked, wrong = [], []
    for ef in sorted(RT.TARGETS):
        r = w.get(ef)
        if r is None:
            continue
        for p in r["base"][0]:
            rt = p.hazards.render_route if p.hazards else None
            if p.bpp != 15 or rt is None or not rt.never_vram:
                continue
            rem = p.hazards.render_remedy
            claims = _CLAIM.findall(rem)
            if "in the indexed lane" in rem:
                outright += 1
            elif claims:
                keyed += 1
            else:
                blocked.append((ef, p.name))
            for name, keys, bpp in claims:
                kw = dict(allow_displaced_readerless=DA.ACK_MOVER_KEY in keys,
                          allow_drawn_depth=RT.DRAWN_ACK_KEY in keys)
                try:
                    q = RP.texel_page(r["blob"], name, ef, **kw)
                except RP.RepaintError as e:
                    wrong.append((ef, name, "refused: %s" % str(e)[:80]))
                    continue
                if q.bpp != int(bpp):
                    wrong.append((ef, name, "resolves at %dbpp" % q.bpp))
    print("   %d NEVER_VRAM refusals: %d paintable outright, %d behind stated keys, %d with no route"
          % (outright + keyed + len(blocked), outright, keyed, len(blocked)))
    for b in blocked:
        print("     no route: ef%03d %s" % b)
    chk("C5 every keyed claim resolves, with exactly its keys, at its depth", wrong, [])
    chk("C5 the remedy", (outright, keyed, blocked), PIN_REMEDY)
    chk("C5 the kit's own pins", (RT.SURFACE_15BPP_PAINTABLE_REMEDY, RT.SURFACE_15BPP_KEYED_REMEDY),
        (outright, keyed))


# --------------------------------------------------------------------------- C6
def c6_prerun() -> None:
    if PRERUN_SCREEN is None:
        _FAILS.append("C6 no pre-run vehicle pinned")
        return
    ef, cell = PRERUN_SCREEN
    reps = {}
    for tag, extra in (("paint", []), ("noop", ["--noop"])):
        cp = subprocess.run([sys.executable, PRERUN, "--screen", "--ef", str(ef), "--cell", cell] + extra,
                            capture_output=True, text=True, cwd=_HERE)
        try:
            reps[tag] = json.loads(cp.stdout[cp.stdout.index("{"):])
        except ValueError:
            _FAILS.append("C6 %s pre-run produced no report: %s" % (tag, (cp.stdout + cp.stderr)[-300:]))
            return
    p, n = reps["paint"], reps["noop"]
    print("   paint: ef%03d %s -- %s, %d of %d frames changed, %d px; the page drew the screen %s, the "
          "target %s" % (ef, cell, p["verdict"], p["frames_changed"], p["frames_drawn"],
                         p["screen_px_changed"], p["feeder_direct_to_screen_px"], p["feeder_into_target_px"]))
    print("   noop : %s -- %d bytes moved, %d frames changed" % (n["verdict"], n["bytes_moved"],
                                                                 n["frames_changed"]))
    chk("C6 the painted page changes the screen through its own draws",
        (p["verdict"], p["self_check"].split("/")[0] == p["self_check"].split("/")[1]), ("DIRECT", True))
    chk("C6 the falsifier: the unedited build moves no byte and no frame",
        (n["bytes_moved"], n["frames_changed"], n["verdict"]), (0, 0, "NOTHING"))


# --------------------------------------------------------------------------- C7
def c7_provenance() -> None:
    _DA, DC, _RT, _RP, _RS = _kit()
    with open(DC.__file__, encoding="utf-8") as fh:
        src = fh.read()
    tree = ast.parse(src)
    for name, width in (("_READ_ROWS", 10), ("_READ_CLUT_ROWS", 8), ("_COVERED_RANGES", 2)):
        node = next(n for n in ast.walk(tree)
                    if isinstance(n, ast.AnnAssign) and getattr(n.target, "id", "") == name)
        vals = ast.literal_eval(node.value)
        chk("C7 %s is integers only, %d to a row" % (name, width),
            all(len(r) == width and all(isinstance(v, int) for v in r) for r in vals), True)
    chk("C7 no bytes constant and no hex run in draw_census.py",
        (bool(re.search(r"\bb['\"]", src)), bool(re.search(r"[0-9a-fA-F]{32,}", src))), (False, False))


# --------------------------------------------------------------------------- C8
#: THE STAGED CASTS.  (spec, effect, page, half, the row key, the patched container's sha prefix).  Each
#: spec's art is the pre-run's own mark, stamped into an `export-art` directory by `--art` (SCRATCH).
CASTS = [
    ("leviathan_drawn.toml", 179, "cell.s0.x576_y384", "drawn", "acknowledge_drawn_depth", "8db2eefe"),
    ("fenrir_conflict.toml", 226, "cell.s0.x576_y384", "conflict", "acknowledge_drawn_conflict", "467c370d"),
]
BENCH = os.path.join(_REPO, "studies", "custom-summons", "rung8-epic", "bench", "rung8.field.toml")


def _bench_rows() -> List[dict]:
    import tomllib
    with open(BENCH, "rb") as fh:
        doc = tomllib.load(fh)
    rows = []
    for p in doc.get("playable", []):
        for cmd in (p.get("abilities") or {}).values():
            if isinstance(cmd, dict):
                rows.extend(r for r in cmd.get("abilities", []) if isinstance(r, dict))
    return rows


def c8_casts() -> None:
    _DA, _DC, _RT, RP, _RS = _kit()
    import drawn_feed_prerun as PRE
    rows = _bench_rows()
    for spec_name, ef, cell, half, key, sha in CASTS:
        path = os.path.join(_HERE, spec_name)
        spec = RP.load_spec(path)
        blob = _load(ef)
        row = spec["reskin"]["texel"][0]
        chk("C8 %s paints one page, %s, on ef%03d, with `%s`" % (spec_name, cell, ef, key),
            (spec["reskin"]["effect"], len(spec["reskin"]["texel"]), row["name"], row.get(key)),
            (ef, 1, cell, True))
        b = RP.build(spec, path, blob=blob)
        check = RP.self_check(b)
        print("   %s: ef%03d %s (%s half) builds %s..., self-check %d/%d, %d byte(s) moved" % (
            spec_name, ef, cell, half, b.sha_out[:8], sum(1 for g in check.gates if g.ok), len(check.gates),
            len(check.changed)))
        chk("C8 %s builds, self-check whole" % spec_name, all(g.ok for g in check.gates), True)
        if sha is None:
            _FAILS.append("C8 %s has no pinned sha (built %s)" % (spec_name, b.sha_out[:8]))
        else:
            chk("C8 %s rebuilds the staged container" % spec_name, b.sha_out[:len(sha)], sha)
        # the art IS the pre-run's mark, re-derived from the stock page
        if half == "drawn":
            page = RP.texel_page(blob, cell, ef, allow_drawn_depth=True)
            want = PRE.zebra(blob, page)
        else:
            page = RP.texel_page(blob, cell, ef)
            want = PRE.paint8(blob, page, *PRE.parity_pair(blob, ef, page))
        got = (RP.read_indexed4_png(row["source"], page.w, page.h) if page.bpp == 4
               else RP.read_indexed_png(row["source"], page.w, page.h, 256))
        chk("C8 %s's art is the pre-run's mark, byte for byte" % spec_name, got == want, True)
        # and without its key the row refuses, by name
        bare = json.loads(json.dumps(spec))
        bare["reskin"]["texel"][0].pop(key)
        try:
            RP.build(bare, path, blob=blob)
            why = "BUILT"
        except RP.RepaintError as exc:
            why = str(exc)
        want_why = "DRAWN AT ANOTHER DEPTH" if half == "conflict" else "DEPTH-UNKNOWN"
        chk("C8 %s refuses without `%s` (%s)" % (spec_name, key, want_why), want_why in why[:400], True)
        hits = [r for r in rows if r.get("vfx1") == ef and r.get("vfx2") == ef]
        chk("C8 the bench casts ef%03d structurally (one row, vfx1 = vfx2)" % ef, len(hits), 1)


# --------------------------------------------------------------------------- C9
#: what each staged cast's pre-run must say: the drawn page DIRECT, the conflict page SECOND-PICTURE
PRERUN_CASTS = {"drawn": ("DIRECT", ["--screen"]), "conflict": ("SECOND-PICTURE", ["--conflict"])}


def c9_cast_preruns() -> None:
    procs = {}
    for spec_name, ef, cell, half, _key, _sha in CASTS:
        want, extra = PRERUN_CASTS[half]
        procs[spec_name] = (want, half, subprocess.Popen(
            [sys.executable, PRERUN, "--ef", str(ef), "--cell", cell] + extra,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=_HERE))
    for spec_name, (want, half, p) in procs.items():
        log, _ = p.communicate()
        try:
            rep = json.loads(log[log.index("{"):])
        except ValueError:
            _FAILS.append("C9 %s pre-run produced no report: %s" % (spec_name, log[-300:]))
            continue
        line = "   %s: %s, %d of %d frames changed, %d px" % (
            spec_name, rep["verdict"], rep["frames_changed"], rep["frames_drawn"], rep["screen_px_changed"])
        if half == "conflict":
            line += "; band residual parity %.3f vs plain %.3f" % (rep["parity_residual"], rep["plain_residual"])
        print(line)
        chk("C9 %s's pre-run says %s" % (spec_name, want), rep["verdict"], want)
        sha = next(s for n, _e, _c, _h, _k, s in CASTS if n == spec_name)
        built = rep["build_sha256"]["parity"] if half == "conflict" else rep["build_sha256"]
        chk("C9 %s's pre-run renders the staged bytes" % spec_name, built[:len(sha)], sha)


GATES = [
    ("C1", "THE PAGE MAP -- the upload walk names every measured upload; the old cursor does not",
     c1_page_map),
    ("C2", "THE RE-DERIVATION -- the draw census reproduces the tables row for row", c2_rederive),
    ("C3", "THE CALIBRATION -- the default surface against the reads of its own bytes", c3_calibration),
    ("C4", "THE REACH -- reasons without the ack, single-depth keyed pages with it", c4_reach),
    ("C5", "THE TARGET HALF, RE-READ -- the per-cell channel's pages, per page; the remedy", c5_target_half),
    ("C6", "THE PRE-RUN -- a page only the screen reads, painted, changes the screen", c6_prerun),
    ("C7", "PROVENANCE -- ids, offsets, coordinates, depths and counts", c7_provenance),
    ("C8", "THE STAGED CASTS -- each spec rebuilds, carries the pre-run's mark, refuses without its key",
     c8_casts),
    ("C9", "THE CASTS RUN OFFLINE -- the drawn page DIRECT, the conflict page a second picture", c9_cast_preruns),
]


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if "--emit" in args:
        return emit()
    only = set(a.upper() for a in args if a.upper().startswith("C"))
    print("CHANNEL D, EVERY DRAW -- each read charged to the page whose bytes it sampled")
    print("corpus: %s" % CORPUS)
    print("=" * 72)
    board = []
    for tag, title, fn in GATES:
        if only and tag not in only:
            continue
        before = len(_FAILS)
        print("%s  %s" % (tag, title))
        try:
            fn()
            ok = len(_FAILS) == before
        except Exception as exc:                                   # a crashed gate is a red gate
            _FAILS.append("%s raised %s: %s" % (tag, type(exc).__name__, exc))
            ok = False
        board.append((tag, title, ok))
        print("   [%s] %s\n" % ("PASS" if ok else "FAIL", tag))
    print("=" * 72)
    for tag, title, ok in board:
        print("%-4s %s %s" % ("PASS" if ok else "FAIL", tag, title))
    for f in _FAILS:
        print("  FAIL  %s" % f)
    print("%d/%d gates pass" % (sum(1 for b in board if b[2]), len(board)))
    return 0 if all(b[2] for b in board) else 1


if __name__ == "__main__":
    sys.exit(main())
