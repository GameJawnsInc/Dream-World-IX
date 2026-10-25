r"""CHANNEL D -- `py drawn_gates.py` prints D1..D6 with PASS/FAIL.

A 15bpp read in a target-rendering effect samples the render target, never VRAM, so the kit refuses a
``direct15`` repaint there and names what the target is DRAWN from instead (``render_target.py``).  Of
the 22 default-surface refusals, 20 named nothing paintable: the static derivation gives most of the
target's feeders no depth.  The routes census MEASURES the depth each feeder is drawn at, and a second
run with the CLUT recorded per fragment says which palette -- so CHANNEL D (``"drawn"``) hands such a
cell out at that depth, behind ``acknowledge_drawn_depth`` + ``expect_bpp``.  This runner checks it:

D1  THE RE-DERIVATION.  The feeds census on disk (SCRATCH ``headless/raster/feeds``: the 66 target
    containers, 0 errors) reproduces ``render_target._FEED_ROWS`` row for row -- the same run, again --
    and its per-fragment CLUT split reproduces ``_FEED_CLUT_ROWS`` row for row, each feed's split
    summing to the feed.
D2  THE CALIBRATION ("diff the two before trusting either", headless README).  Every scenery feed
    cell against the static edit surface: where both speak, how often the depths agree, and every
    contradiction BY NAME; where only the census speaks, by refusal class.  Pinned.
D3  THE CHANNEL'S REACH.  Consulting channel D moves no page and no refusal class on the default
    surface -- it adds reasons, never pages; with the ack every cell it hands out is single-depth,
    keyed by a CLUT the container declares, and named in the census; no dual-depth cell ever emits;
    the ``bound`` reading does not consult it.
D4  THE REMEDY.  Every one of the default surface's 22 NEVER_VRAM 15bpp refusals is read: how many name
    a feeder paintable outright, how many one paintable behind stated keys -- and EVERY keyed claim is
    resolved through ``texel_page`` with exactly those keys, at the depth it names, export-unblocked.
D5  THE PRE-RUN, AND ITS FALSIFIER.  ``drawn_feed_prerun.py`` paints ef150's largest drawn feeder,
    builds it through the kit, and renders stock against the build headless: screen frames change while
    the feeder drew only into the target (``REACHES``).  The same run with the art UNEDITED moves no
    byte and no frame -- the instrument can say nothing.
D6  PROVENANCE.  The new table carries ids, coordinates, depths and counts only.

Reads `C:\gd\SCRATCH\summon-format` ONLY and writes there (the pre-run's art and frames) -- no install
read, no deploy, no install write, no commit.
"""
from __future__ import annotations

import ast
import glob
import json
import os
import re
import subprocess
import sys
from collections import Counter
from typing import Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS_STUDY                                        # noqa: E402,F401  (sets up sys.path)
from ff9mapkit.summons import depth_attribution as DA            # noqa: E402
from ff9mapkit.summons import render_target as RT                # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402
from ff9mapkit.summons import reskin as RS                       # noqa: E402

_REPO = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
assert os.path.normcase(os.path.abspath(RT.__file__)).startswith(
    os.path.normcase(os.path.join(_REPO, "ff9mapkit"))), RT.__file__

CORPUS = r"C:\gd\SCRATCH\summon-format"
FEEDS = os.path.join(CORPUS, "headless", "raster", "feeds")
PRERUN = os.path.join(_HERE, "drawn_feed_prerun.py")

# THE PINS, measured by this runner's own walk
#: every scenery cell the target's draw reads, against the static edit surface.  Where both speak the
#: depths agree on 13 and differ on 6; 5 of the 6 are a 15bpp reader (routed to the target, so never
#: reading VRAM at all) over bytes the target's draw reads at 8bpp -- the render-target lane's OWN FEED
#: -- and the other is ef499 x704_y384, a channel-G column bound at 4bpp that the draw reads at 8.
PIN_CALIBRATION = {
    "refused depth-unknown, drawn at one depth": 184, "refused depth-unknown, drawn at two": 19,
    "drawn, not a declared cell": 14, "page, depth agrees": 13, "page, depth differs": 6,
    "refused displaced-readerless, drawn at one depth": 9,
    "refused program-dual-depth, drawn at two": 4, "refused program-dual-depth, drawn at one depth": 3,
    "refused displaced-readership-substituted, drawn at one depth": 1,
    "refused displaced-readerless, drawn at two": 1,
    "refused displaced-vs-page-depth, drawn at one depth": 1,
}
PIN_CONTRADICTIONS = [
    (203, "x576_y384", (15,), ("so-uv",), (8,)), (203, "x640_y384", (15,), ("so-uv",), (8,)),
    (381, "x704_y384", (15,), ("so-uv",), (8,)), (381, "x768_y384", (4,), ("so-uv",), (8,)),
    (447, "x704_y384", (15,), ("so-uv",), (8,)), (499, "x704_y384", (4,), ("so-page",), (8,)),
]
#: (pages handed out behind the ack, containers) -- names, so a co-transform cell counts per writer.
#: (187, 52) on the feeds alone; with the draw census (screen_gates.py) every draw of these 66 target
#: containers is read, per page, and the reach here is (335, 62) -- the whole corpus is screen_gates C4's
PIN_REACH = (335, 62)
#: (outright, behind stated keys, total) of the 22 default-surface NEVER_VRAM 15bpp refusals
PIN_REMEDY = (2, 12, 22)
#: no route: a program-VRAM writer (ef381), a feeder drawn at TWO depths (ef429), a veto (ef447)
PIN_REMEDY_BLOCKED = [
    (381, "cell.s0.x704_y384"), (381, "cell.s1.x704_y384"), (381, "cell.s3.x704_y384"),
    (381, "cell.s6.x704_y384"), (381, "cell.s8.x704_y384"), (429, "cell.s0.x448_y256"),
    (429, "cell.s0.x448_y384"), (447, "cell.s2.x704_y384"),
]

_FAILS: List[str] = []


def chk(name: str, got, want) -> None:
    if got != want:
        _FAILS.append("%s: measured %r, pinned %r" % (name, got, want))


def _load(ef: int) -> bytes:
    with open(os.path.join(CORPUS, "ef%03d.bytes" % ef), "rb") as fh:
        return fh.read()


def _cell(k: str):
    m = re.match(r"x(\d+)_y(\d+)(?:@(\d+))?$", k)
    return tuple(int(g) for g in m.groups() if g is not None)


# --------------------------------------------------------------------------- D1
def d1_rederive() -> None:
    with open(os.path.join(FEEDS, "routes.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    errs = sorted(e for e, r in doc["rows"].items() if "error" in r)
    feed, clut = [], []
    for e in sorted(doc["rows"]):
        ef = int(e[2:])
        with open(os.path.join(FEEDS, e, "summary.json"), encoding="utf-8") as fh:
            s = json.load(fh)
        for c, v in sorted(s["render_target_cells"].items()):
            feed.append((ef,) + _cell(c) + (v["pixels"], v["n_frames"]))
        for c, d in sorted(s["render_target_cell_cluts"].items()):
            for k, n in sorted(d.items()):
                clut.append((ef,) + _cell(c) + _cell(k) + (n,))
    print("   feeds census: %d containers, %d errors; %d feeds, %d CLUT rows"
          % (doc["containers"], len(errs), len(feed), len(clut)))
    chk("D1 the feeds census covers the 66 target containers, 0 errors",
        ({int(e[2:]) for e in doc["rows"]}, errs), (set(RT.TARGETS), []))
    chk("D1 the feeds reproduce _FEED_ROWS, ROW FOR ROW", tuple(feed), RT._FEED_ROWS)
    chk("D1 the CLUT split reproduces _FEED_CLUT_ROWS, ROW FOR ROW", tuple(clut), RT._FEED_CLUT_ROWS)
    sums = Counter()
    for r in clut:
        sums[r[:4]] += r[6]
    chk("D1 every feed's CLUT split sums to the feed",
        all(sums[f[:4]] == f[4] for f in RT._FEED_ROWS), True)


# --------------------------------------------------------------------------- the walk (D2-D4)
_W: Dict[int, dict] = {}


def _walk() -> Dict[int, dict]:
    if _W:
        return _W
    for ef in sorted(RT.TARGETS):
        blob = _load(ef)
        base = RP.scenery_surface(blob, ef, channels=RP.EDIT_CHANNELS)
        nod = RP.scenery_surface(blob, ef, channels=tuple(c for c in RP.EDIT_CHANNELS if c != "drawn"))
        acked = RP.scenery_surface(blob, ef, channels=RP.EDIT_CHANNELS, drawn_depth=True)
        _W[ef] = {"blob": blob, "base": base, "nod": nod, "acked": acked,
                  "cells": {pc.cell for pc in RS.page_cells(blob).values()}}
    return _W


def _ident(p):
    return (p.name, p.bpp, p.cell, p.depth_source, p.palette_name, p.clut_offset)


# --------------------------------------------------------------------------- D2
def d2_calibration() -> None:
    w = _walk()
    tally, contra = Counter(), []
    for ef, r in w.items():
        pages, refused = r["base"]
        pg: Dict[tuple, set] = {}
        for p in pages:
            pg.setdefault(p.cell, set()).add((p.bpp, p.depth_source))
        rf: Dict[tuple, set] = {}
        for q in refused:
            rf.setdefault(q.cell, set()).add(q.klass)
        drawn: Dict[tuple, set] = {}
        for f in RT.feeders(ef):
            if f.cell[0] >= RT.BLUR_X:
                drawn.setdefault(f.cell, set()).add(f.bpp)
        for cell, bpps in sorted(drawn.items()):
            if cell not in r["cells"]:
                tally["drawn, not a declared cell"] += 1
            elif cell in pg:
                static = {b for b, _s in pg[cell]}
                if static == bpps:
                    tally["page, depth agrees"] += 1
                else:
                    tally["page, depth differs"] += 1
                    contra.append((ef, "x%d_y%d" % cell, tuple(sorted(static)),
                                   tuple(sorted({s for _b, s in pg[cell]})), tuple(sorted(bpps))))
            else:
                k = "+".join(sorted(rf.get(cell, {"(nothing)"})))
                tally["refused %s, drawn at %s" % (k, "one depth" if len(bpps) == 1 else "two")] += 1
    for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
        print("   %4d  %s" % (v, k))
    for c in contra:
        print("     differs: ef%03d %s static %s (%s) drawn %s" % c)
    chk("D2 the calibration", dict(tally), PIN_CALIBRATION)
    chk("D2 every contradiction by name", contra, PIN_CONTRADICTIONS)


# --------------------------------------------------------------------------- D3
def d3_reach() -> None:
    w = _walk()
    moved, emitted, bad = [], [], []
    for ef, r in w.items():
        (bp, br), (np_, nr), (ap, ar) = r["base"], r["nod"], r["acked"]
        if [_ident(p) for p in bp] != [_ident(p) for p in np_] or \
                sorted((q.name, q.klass) for q in br) != sorted((q.name, q.klass) for q in nr):
            moved.append(ef)
        base_names = {p.name for p in bp}
        for p in ap:
            if p.depth_source != "drawn":
                continue
            emitted.append((ef, p.name))
            dd = RT.drawn_depth(ef, p.cell, p.page_offset)
            keyed = p.bpp == 15 or bool(p.palette_name)       # a 15bpp drawn page is direct colour
            if (dd is None or dd.dual or dd.bpp != p.bpp or not keyed
                    or p.name in base_names):
                bad.append((ef, p.name))
        if any(p.depth_source == "drawn" for p in bp):
            bad.append((ef, "a drawn page WITHOUT the ack"))
    print("   consulting channel D moved the default surface on %d container(s); with the ack it hands "
          "out %d page(s) in %d container(s)" % (len(moved), len(emitted), len({e for e, _n in emitted})))
    chk("D3 consulting moves no page and no refusal class", moved, [])
    chk("D3 every drawn page is single-depth, keyed, measured, and new", bad, [])
    chk("D3 the reach", (len(emitted), len({e for e, _n in emitted})), PIN_REACH)
    blob = w[150]["blob"]
    pb = RP.scenery_surface(blob, 150, channels=RP.READINGS["bound"], drawn_depth=True)[0]
    chk("D3 the `bound` reading does not consult channel D",
        any(p.depth_source == "drawn" for p in pb), False)


# --------------------------------------------------------------------------- D4
_CLAIM = re.compile(r"`(cell\.[^`]+)`, refused as `[^`]+` -- paint it with "
                    r"((?:`[a-z_]+ = true`(?: and )?)+) and `expect_bpp = (\d+)`")


def d4_remedy() -> None:
    w = _walk()
    outright = keyed = 0
    blocked, wrong, checked = [], [], 0
    for ef, r in w.items():
        pages, refused = r["base"]
        for p in pages:
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
                checked += 1
                kw = dict(allow_displaced_readerless=DA.ACK_MOVER_KEY in keys,
                          allow_drawn_depth=RT.DRAWN_ACK_KEY in keys)
                try:
                    q = RP.texel_page(r["blob"], name, ef, **kw)
                except RP.RepaintError as e:
                    wrong.append((ef, name, "refused: %s" % str(e)[:80]))
                    continue
                if q.bpp != int(bpp):
                    wrong.append((ef, name, "resolves at %dbpp" % q.bpp))
    print("   22 NEVER_VRAM refusals: %d paintable outright, %d behind stated keys, %d with no route; "
          "%d keyed claim(s) resolved through texel_page" % (outright, keyed, len(blocked), checked))
    for b in blocked:
        print("     no route: ef%03d %s" % b)
    chk("D4 every keyed claim resolves, with exactly its keys, at its depth", wrong, [])
    chk("D4 the remedy", (outright, keyed, outright + keyed + len(blocked)), PIN_REMEDY)
    chk("D4 the cells with no route, by name", blocked, PIN_REMEDY_BLOCKED)
    chk("D4 the kit's own pins", (RT.SURFACE_15BPP_PAINTABLE_REMEDY, RT.SURFACE_15BPP_KEYED_REMEDY),
        (outright, keyed))


# --------------------------------------------------------------------------- D5
def d5_prerun() -> None:
    reps = {}
    for tag, extra in (("paint", []), ("noop", ["--noop"])):
        cp = subprocess.run([sys.executable, PRERUN] + extra, capture_output=True, text=True, cwd=_HERE)
        try:
            reps[tag] = json.loads(cp.stdout[cp.stdout.index("{"):])
        except ValueError:
            _FAILS.append("D5 %s pre-run produced no report: %s" % (tag, (cp.stdout + cp.stderr)[-300:]))
            return
    p, n = reps["paint"], reps["noop"]
    print("   paint: %s -- %d of %d frames changed, %d px; the feeder drew the target %s, the screen %s"
          % (p["verdict"], p["frames_changed"], p["frames_drawn"], p["screen_px_changed"],
             p["feeder_into_target_px"], p["feeder_direct_to_screen_px"]))
    print("   noop : %s -- %d bytes moved, %d frames changed" % (n["verdict"], n["bytes_moved"],
                                                                 n["frames_changed"]))
    chk("D5 the painted feeder reaches the screen through the target",
        (p["verdict"], p["self_check"].split("/")[0] == p["self_check"].split("/")[1]),
        ("REACHES", True))
    chk("D5 the falsifier: the unedited build moves no byte and no frame",
        (n["bytes_moved"], n["frames_changed"], n["verdict"]), (0, 0, "NOTHING"))


# --------------------------------------------------------------------------- D6
def d6_provenance() -> None:
    src = open(RT.__file__, encoding="utf-8").read()
    tree = ast.parse(src)
    rows = next(n for n in ast.walk(tree)
                if isinstance(n, ast.AnnAssign) and getattr(n.target, "id", "") == "_FEED_CLUT_ROWS")
    vals = ast.literal_eval(rows.value)
    chk("D6 the CLUT table is integers only, seven to a row",
        all(len(r) == 7 and all(isinstance(v, int) for v in r) for r in vals), True)
    chk("D6 no bytes constant and no hex run in render_target.py",
        (bool(re.search(r"\bb['\"]", src)), bool(re.search(r"[0-9a-fA-F]{32,}", src))), (False, False))


GATES = [
    ("D1", "THE RE-DERIVATION -- the feeds census reproduces both tables row for row", d1_rederive),
    ("D2", "THE CALIBRATION -- the census against the static derivation, pinned", d2_calibration),
    ("D3", "THE REACH -- reasons without the ack, keyed single-depth pages with it", d3_reach),
    ("D4", "THE REMEDY -- 22 refusals read, every keyed claim resolved", d4_remedy),
    ("D5", "THE PRE-RUN -- a painted feeder reaches the screen; the no-op does not", d5_prerun),
    ("D6", "PROVENANCE -- ids, coordinates, depths and counts", d6_provenance),
]


def main(argv=None) -> int:
    only = set(a.upper() for a in (argv or sys.argv[1:]) if a.upper().startswith("D"))
    print("CHANNEL D GATES -- the depth a cell is drawn at, read off the render target's draws")
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
    if _FAILS:
        print("-" * 72)
        for f in _FAILS:
            print("  FAIL  %s" % f)
    print("=" * 72)
    print("%d/%d gates pass" % (sum(1 for _, _, ok in board if ok), len(board)))
    return 1 if _FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
