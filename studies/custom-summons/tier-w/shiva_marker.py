r"""TIER W rung W7 -- THE FRAME-STRIP MARKER GENERATOR.  The committed half of the texel discriminator.

    py shiva_marker.py                      # export ef038's art, stamp the marker, report the numbers
    py shiva_marker.py --root DIR           # stage somewhere else (still local-only guarded)
    py shiva_marker.py --from ef038.bytes   # read a corpus container instead of the install

WHAT THIS FILE IS
-----------------
W7 (`C:/gd/SCRATCH/summon-format/texanim-w7/SYNTHESIS.md` sec 5.4) ships ONE cast on ef038 (Shiva)
carrying BOTH of the rung's verdicts, so one capture answers both:

* **verdict 1 -- the LIFT.** A whole-creature CLUT recolour to magenta on the one effect in the whole
  corpus that arms op 12.  Judgeable in a single frame: Shiva is MAGENTA => the lift is correct.
* **verdict 2 -- the DISCRIMINATOR (this file).** Paint one flat SCREAMING index over the spare
  "eye CLOSED" source strip and leave the live eye window STOCK.  If the eye window EVER shows that
  marker mid-cast, something blits after all and W7's co-transform obligation becomes mandatory
  rather than prudential.  If it never does, A1's exhaustion holds.

THE ARTIFACT IS A REPAINTED 128x128 TEXTURE PAGE, AND THAT IS DECODED SQUARE-ENIX CONTENT.  It is not
committable at any resolution under any name.  So the proof ships as a GENERATOR -- exactly the
posture `emblem_stamp.py` (W6a) established: read the user's own install, re-derive every parameter
of the mark from the container in front of you, stamp in INDEX space, write the PNG into SCRATCH.
`shiva_reskin.toml`'s `[[reskin.texel]]` row then points at that PNG.  Re-running this on a fresh
machine reproduces the same art from that machine's own bytes.

EVERY PARAMETER IS DERIVED, NOT TYPED -- INCLUDING WHICH RECT
--------------------------------------------------------------
The brief names the rect `(78,0,22,12)`.  This file does not.  Typing it would make the generator a
transcription of somebody else's measurement, and it would silently paint the WRONG rect on any other
armed package.  Instead:

* **the part** is the part the table's own clips name (`clip+0x0d`), refused if the table names more
  than one -- one change per in-game test;
* **the window** is the clips' shared destination rect;
* **which source frame is the SPARE** is decided by MEASUREMENT, reproducing A2's own instrument
  (`A2-BYTES.md` sec 5.5): the resting window is a 90.5-97.6 % exact-texel duplicate of ONE named
  frame -- that one is the *resting spare* and must be left alone or the creature's resting eye
  changes.  The OTHER frame (16 % agreement on ef038) is the alternate state, and it is the one this
  marker takes.  So the choice is "the source frame LEAST like the live window", re-measured every
  run, never a coordinate;
* **the ink** is chosen the `emblem_stamp.py` way: from the indices the geometry actually SAMPLES on
  this page, minus every transparent entry -- so it costs **zero CLUT bytes** and is guaranteed to be
  a colour that exists on this creature.  The criterion is maximum Rec.601 luma **under the RECOLOURED
  palette**, because that is the palette the cast runs; the stock luma is reported beside it so the
  choice is visible rather than asserted.  The composed palette is REBUILT from `shiva_reskin.toml`'s
  own CLUT half, never read out of a mod folder -- a generator that read the live install would
  reproduce whatever happened to be deployed that day instead of what its own spec says.

THREE INVARIANTS THIS FILE ENFORCES AT ITS OWN CALL SITE (a law in a docstring is a wish)
-----------------------------------------------------------------------------------------
1. **THE WINDOW IS UNTOUCHED.**  Asserted as a texel count, not as a coordinate comparison: after the
   stamp, the number of changed texels inside the live window -- and inside the resting spare -- must
   be exactly 0.  `main` returns non-zero if it is not.
2. **THE INK IS ABSENT FROM THE ART IT MUST BE TOLD APART FROM.**  A marker painted in an index the
   resting eye already uses is not a discriminator; a frame showing it would be unreadable.  So the
   chosen ink must occur **zero** times inside the live window and zero times inside the resting
   spare, MEASURED, and the generator refuses rather than stamping a weak marker.  (On ef038 the
   brightest sampled index is 255 = `0xffff`, and it appears 0 times in any of the three rects.)
3. **THE ASYMMETRY IS THE POINT.**  The edit deliberately repaints some of a clip family's rects and
   not others, which is precisely what `repaint._gate_texanim_frames` refuses.  `shiva_reskin.toml`
   therefore carries `acknowledge_texanim_frames = true` with the reason written out.  This generator
   REPORTS the asymmetry it is about to create so the acknowledgement is evidenced, not assumed.

A PROPERTY OF THE CHOSEN INK WORTH NAMING, because it makes the two verdicts INDEPENDENT
-----------------------------------------------------------------------------------------
On ef038 the criterion lands on index 255 = `0xffff`, which is ACHROMATIC -- and a hue rotation
cannot move an achromatic colour, so the marker renders identically under the stock palette and under
the recoloured one.  Verdict 2 therefore does not depend on verdict 1 having landed: if the CLUT half
somehow did not take, the marker is still exactly as visible and still discriminates.  That is a
consequence of the derivation, not a design choice, and it is reported so a reader can see it held.

PROVENANCE
----------
No stock byte run appears in this file.  The container is read at run time under the kit's own sha256
drift guard; every destination goes through `ff9mapkit.summons.export.assert_local_only`, which
refuses a git checkout, a `StreamingAssets` tree and the resolved install with no `--force`.
"""
from __future__ import annotations

import argparse
import os
import struct
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                              # noqa: E402  (sets up sys.path)
from ff9mapkit.summons import export as EX                       # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402
from ff9mapkit.summons import texanim as TA                      # noqa: E402
from ff9mapkit.summons import texture as KT                      # noqa: E402

#: THE PROOF'S OWN STAGING ROOT.  `shiva_reskin.toml`'s `source` is an absolute path into
#: ``<root>/art``; re-point one and re-point the other, or the build refuses with "no such source
#: image" rather than silently packing yesterday's art.
DEFAULT_ROOT = os.environ.get("FF9_TEXANIM_W7_ROOT",
                              r"C:\gd\SCRATCH\summon-format\texanim-w7\ef038")

#: the spec whose CLUT half the ink has to read under.  ABSOLUTE for the same reason
#: `emblem_stamp.RESKIN_SPEC` is: a relative name resolves against the SPEC's own directory, and this
#: one must resolve to the study's own toml from wherever it was invoked.  On this rung the CLUT half
#: and the texel half live in ONE file (`repaint.py`'s "one spec, both tables" route), so the sibling
#: it rebuilds is the very spec that will consume its PNG -- which is fine and deliberate: `reskin.py`
#: never reads a `[[reskin.texel]]` row, so the rebuild does not depend on the art existing yet.
RESKIN_SPEC = os.path.join(_HERE, "shiva_reskin.toml")

#: which effect.  ef038 is the ONLY container in the 372-effect corpus that calls op 12
#: (`Hi_StartSummonTexAnim`) at all -- the maximal-risk member of the armed class, so a marker that
#: never moves here is evidence for all five.
EFFECT = 38


def _luma(word: int) -> float:
    """Rec.601 luma of one BGR555 palette word, through the kit's own decoder."""
    r, g, b, _a = KT.bgr555_rgba(word)
    return 0.299 * r + 0.587 * g + 0.114 * b


def composed_palette(stock: bytes, page, reskin_spec: str = RESKIN_SPEC) -> Tuple[int, ...]:
    """The CLUT row this page indexes into ONCE THE CAST RUNS -- rebuilt from the spec's CLUT half.

    Deliberately NO fallback to the stock row (the `emblem_stamp.composed_palette` law, restated
    because it is the one that silently ruins a cast): an unreadable spec RAISES.  Substituting the
    stock palette would choose an ink for contrast under a palette the cast never shows, and the
    marker could be invisible in game with nothing anywhere saying why -- which on THIS rung would
    read as "the blitter does not run", the exact false negative the cast exists to avoid.
    """
    b = RS.build(RS.load_spec(reskin_spec), reskin_spec, blob=stock)
    return struct.unpack_from("<%dH" % page.clut_entries, b.patched, page.clut_offset)


def exact_agreement(px: Sequence[int], w: int, a: "TA.Rect", b: "TA.Rect") -> float:
    """Share of texels that are byte-identical between two same-sized rects of one page.

    A2's own instrument (`A2-BYTES.md` sec 5.5), re-implemented on the kit's decoded page rather than
    cited: it is what separates the RESTING SPARE (0.905-0.976 across the corpus) from the alternate
    state (0.16 on ef038).  Rects of different sizes cannot be compared and raise.
    """
    if (a.w, a.h) != (b.w, b.h):                                 # pragma: no cover - format law
        raise SystemExit("rects %s and %s differ in size -- the table's own law says a frame "
                         "inherits its window's size, so this container did not decode" % (a, b))
    same = 0
    for dy in range(a.h):
        ra, rb = (a.y + dy) * w, (b.y + dy) * w
        for dx in range(a.w):
            same += 1 if px[ra + a.x + dx] == px[rb + b.x + dx] else 0
    return same / float(a.w * a.h)


def choose_rects(px: Sequence[int], w: int, table: "TA.TexAnimTable",
                 part: int) -> Tuple["TA.Rect", "TA.Rect", "TA.Rect", List[Tuple["TA.Rect", float]]]:
    """``(window, resting spare, the marker's rect, [(source, agreement)])`` -- all DERIVED.

    The window is the clips' shared destination.  Every distinct source frame is scored against it by
    exact-texel agreement; the highest is the resting spare (leave it stock -- repainting it would
    change the creature's *resting* eye and confound verdict 2 with an ordinary texel edit), the
    lowest is the alternate state and is what the marker takes.
    """
    clips = [c for c in table.clips if c.part == part]
    windows = {c.window for c in clips}
    if len(windows) != 1:
        raise SystemExit("part %d's clips name %d distinct destination windows (%s) -- this "
                         "generator marks ONE spare strip of ONE window; extend it deliberately "
                         "rather than letting it pick" % (part, len(windows),
                                                          " ".join(str(r) for r in sorted(
                                                              windows, key=lambda r: r.as_tuple()))))
    window = windows.pop()
    srcs: List["TA.Rect"] = []
    for c in clips:
        for s in c.sources:
            if s not in srcs:
                srcs.append(s)
    if len(srcs) < 2:
        raise SystemExit("part %d names %d source frame(s) -- with fewer than two there is no "
                         "'spare' to tell from the resting art, so the marker cannot be placed "
                         "without guessing" % (part, len(srcs)))
    scored = sorted(((s, exact_agreement(px, w, window, s)) for s in srcs), key=lambda t: -t[1])
    resting, mark = scored[0][0], scored[-1][0]
    if mark.intersects(window):                                  # pragma: no cover - corpus says no
        raise SystemExit("the chosen source rect %s overlaps the live window %s -- painting it "
                         "would move the window and destroy the discriminator" % (mark, window))
    return window, resting, mark, scored


def choose_ink(px: Sequence[int], mask: Sequence[int], stock_words: Sequence[int],
               live_words: Sequence[int], zeros: Sequence[int]) -> Tuple[int, List[int]]:
    """``(ink index, the sampled index set)`` -- `emblem_stamp.choose_ink`'s candidate law, one knob.

    The candidate set is the indices the GEOMETRY SAMPLES, minus every transparent entry: an ink from
    the whole 256-entry row could be a colour that appears nowhere on this creature, and an ink that
    is the cutout entry would punch a hole instead of painting a marker.  The criterion here is
    maximum luma under the COMPOSED palette (not `emblem_stamp`'s min-of-both): this mark exists to
    SCREAM under the palette the cast actually runs, and both halves ship in one container so the
    stock palette is never live.  The stock luma is reported by the caller regardless.
    """
    zs = set(zeros)
    live = sorted({px[i] for i in range(len(mask)) if mask[i]} - zs)
    if not live:                                                 # pragma: no cover - stock has 255
        raise SystemExit("no sampled, non-transparent index on this page -- nothing to ink with")
    return max(live, key=lambda i: _luma(live_words[i])), live


def stamp(px: Sequence[int], w: int, rect: "TA.Rect", ink: int) -> Tuple[bytearray, int]:
    """Fill ``rect`` flat with ``ink``.  A FLAT block, not a glyph, and that is the design.

    The mark has one job: be unmistakable in a captured frame if it ever appears somewhere it should
    not.  A flat 22x12 slab of the brightest colour on the creature cannot be confused with an eye at
    any resolution, under any blend, at any camera distance -- where a shape could be argued about.
    """
    out = bytearray(px)
    n = 0
    for dy in range(rect.h):
        row = (rect.y + dy) * w
        for dx in range(rect.w):
            i = row + rect.x + dx
            n += 1
            out[i] = ink
    return out, n


def _in_rect(changed: Sequence[int], rect: "TA.Rect", w: int) -> int:
    s = set(changed)
    return sum(1 for dy in range(rect.h) for dx in range(rect.w)
               if (rect.y + dy) * w + rect.x + dx in s)


def _index_count(px: Sequence[int], rect: "TA.Rect", w: int, idx: int) -> int:
    """How many texels of ``rect`` already carry ``idx`` -- invariant 2's instrument."""
    return sum(1 for dy in range(rect.h) for dx in range(rect.w)
               if px[(rect.y + dy) * w + rect.x + dx] == idx)


def generate(effect: int = EFFECT, root: Optional[str] = None, from_path: Optional[str] = None,
             game=None, reskin_spec: str = RESKIN_SPEC, export: bool = True) -> Dict[str, object]:
    """Export the effect's art, stamp the marker, and return every number the spec quotes."""
    if from_path:
        stock = Path(from_path).read_bytes()
        source = str(from_path)
    else:
        stock, source = RS.R.read_stock_effect(effect, game)

    res = TA.read(stock)
    if not res.armed:
        raise SystemExit("ef%03d carries no armed texanim region -- this generator marks a texanim "
                         "frame strip, and there is none here" % effect)
    if res.table is None:
        raise SystemExit("ef%03d's texanim region is ARMED but did not DECODE (%s) -- the pre-W7 "
                         "refusal stands and nothing may be placed from a table nobody read"
                         % (effect, res.error))
    parts = res.table.parts
    if len(parts) != 1:
        raise SystemExit("ef%03d's table names %d parts %s -- one change per in-game test; pick one "
                         "deliberately rather than letting this script choose"
                         % (effect, len(parts), parts))
    part = parts[0]

    root = Path(EX.assert_local_only(root or DEFAULT_ROOT))
    art = root / "art"
    if export:
        man = RP.export_art(stock, effect, art, source=source, lane="indexed")
        art = Path(man["out_dir"])

    page = next(p for p in RP.creature_texel_pages(stock) if p.index == part)
    w, h = page.wh
    px = stock[page.page_offset:page.page_offset + page.page_bytes]
    stock_words = RP.palette_words(stock, page)
    zeros = RP.transparent_indices(stock_words)

    cov = RP.coverage(stock, part)
    if not cov.available:                                        # pragma: no cover - geom drift
        raise SystemExit("coverage UNAVAILABLE on ef%03d part %d (%s) -- the ink candidate set is "
                         "the sampled index set, so there is nothing to derive from"
                         % (effect, part, cov.reason))
    live_words = composed_palette(stock, page, reskin_spec)
    ink, live_set = choose_ink(px, cov.mask, stock_words, live_words, zeros)
    window, resting, mark, scored = choose_rects(px, w, res.table, part)

    # INVARIANT 2, enforced BEFORE anything is stamped: an ink the resting art already uses cannot
    # discriminate, and a capture of it would be unreadable.  Refuse rather than ship a weak marker.
    ink_in_window = _index_count(px, window, w, ink)
    ink_in_resting = _index_count(px, resting, w, ink)
    if ink_in_window or ink_in_resting:
        raise SystemExit(
            "the derived ink (index %d) already occurs %d time(s) in the live window %s and %d "
            "time(s) in the resting spare %s.  A marker painted in a colour the resting eye already "
            "shows is not a discriminator -- a frame carrying it could not be read either way.  Pick "
            "the ink deliberately for this container instead of letting the brightest-sampled rule "
            "choose." % (ink, ink_in_window, window, ink_in_resting, resting))

    edited, filled = stamp(px, w, mark, ink)

    zs = set(zeros)
    changed = [i for i in range(len(px)) if px[i] != edited[i]]
    in_window = _in_rect(changed, window, w)
    in_resting = _in_rect(changed, resting, w)
    dead_moved = sum(1 for i in changed if not cov.mask[i])
    punch = sum(1 for i in changed if px[i] not in zs and edited[i] in zs)
    fill = sum(1 for i in changed if px[i] in zs and edited[i] not in zs)

    # the asymmetry this run is about to create, per clip -- the evidence for the acknowledgement
    fam: List[str] = []
    for c in (c for c in res.table.clips if c.part == part):
        seen: List["TA.Rect"] = []
        for r in c.rects:
            if r not in seen:
                seen.append(r)
        hit = [r for r in seen if _in_rect(changed, r, w)]
        fam.append("clip %d: %d/%d protected rect(s) repainted%s"
                   % (c.index, len(hit), len(seen),
                      "  <- ASYMMETRIC" if hit and len(hit) != len(seen) else ""))

    out_png = art / ("%s.png" % page.name)
    art.mkdir(parents=True, exist_ok=True)
    RP.write_indexed_png(bytes(edited), stock_words, w, h, out_png)

    return {
        "effect": effect, "part": part, "page": page.name, "source": source,
        "root": str(root), "art": str(art), "png": str(out_png),
        "page_offset": page.page_offset, "page_bytes": page.page_bytes, "wh": [w, h],
        "clut_offset": page.clut_offset,
        "region": [res.region.lo, res.region.hi, res.region.nbytes],
        "clips": len(res.table.clips),
        "window": window.as_tuple(), "resting": resting.as_tuple(), "mark": mark.as_tuple(),
        "agreement": [[r.as_tuple(), round(a, 4)] for r, a in scored],
        "covered": cov.covered, "dead": cov.dead, "faces": cov.faces,
        "sampled_indices": len(live_set),
        "ink": ink, "ink_stock": stock_words[ink], "ink_live": live_words[ink],
        "ink_achromatic": stock_words[ink] == live_words[ink],
        "ink_in_window": ink_in_window, "ink_in_resting": ink_in_resting,
        "ink_in_mark": _index_count(px, mark, w, ink),
        "filled": filled, "changed": len(changed),
        "changed_in_window": in_window, "changed_in_resting": in_resting,
        "dead_pad_moved": dead_moved, "cutout_punch": punch, "cutout_fill": fill,
        "families": fam, "transparent_indices": list(zeros),
    }


def report(d: Dict[str, object]) -> List[str]:
    return [
        "ef%03d %s  <- %s" % (d["effect"], d["page"], d["source"]),
        "  texanim       ARMED %d B at %#x..%#x, %d clip(s), all on part %d"
        % (d["region"][2], d["region"][0], d["region"][1], d["clips"], d["part"]),
        "  page          %#08x .. %#08x   %dx%d 8bpp   CLUT row @%#08x"
        % (d["page_offset"], d["page_offset"] + d["page_bytes"], d["wh"][0], d["wh"][1],
           d["clut_offset"]),
        "  DERIVED rects live window %s | resting spare %s | MARKED %s"
        % (d["window"], d["resting"], d["mark"]),
        "  exact-texel agreement with the window, per source frame (A2 sec 5.5's instrument):",
    ] + [
        "        %-18s %.4f%s" % (r, a, "   <- resting spare, LEFT STOCK" if i == 0 else
                                  ("   <- MARKED" if i == len(d["agreement"]) - 1 else ""))
        for i, (r, a) in enumerate(d["agreement"])
    ] + [
        "  ink   idx %3d  stock %#06x L=%.0f   composed %#06x L=%.0f  (of %d sampled indices)%s"
        % (d["ink"], d["ink_stock"], _luma(d["ink_stock"]), d["ink_live"], _luma(d["ink_live"]),
           d["sampled_indices"],
           "  -- ACHROMATIC: identical under both palettes, so verdict 2 does not depend on verdict 1"
           if d["ink_achromatic"] else ""),
        "  THE INK IS ABSENT from the art it must be told apart from: index %d occurs %d time(s) in "
        "the live window and %d time(s) in the resting spare (%d in the marked rect, now all %d)"
        % (d["ink"], d["ink_in_window"], d["ink_in_resting"], d["ink_in_mark"], d["filled"]),
        "  coverage      %d/%d texels sampled (%.1f%%), %d dead, %d faces"
        % (d["covered"], d["wh"][0] * d["wh"][1],
           100.0 * d["covered"] / (d["wh"][0] * d["wh"][1]), d["dead"], d["faces"]),
        "  MEASURED      %d texels filled, %d actually DIFFER | dead-pad bytes moved %d | "
        "index-0 cutout flips %d (punch %d / fill %d)"
        % (d["filled"], d["changed"], d["dead_pad_moved"],
           d["cutout_punch"] + d["cutout_fill"], d["cutout_punch"], d["cutout_fill"]),
        "  THE INVARIANT changed texels inside the LIVE WINDOW %s: %d   (inside the resting spare "
        "%s: %d)" % (d["window"], d["changed_in_window"], d["resting"], d["changed_in_resting"]),
        "  THE ASYMMETRY (what `acknowledge_texanim_frames = true` is acknowledging):",
    ] + ["        %s" % f for f in d["families"]] + [
        "  wrote         %s" % d["png"],
        "  CLUT bytes this marker needs: 0 -- the ink is already a live entry of the row.",
    ]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ef", type=int, default=EFFECT, help="the stock effect id (default 38)")
    ap.add_argument("--root", default=None,
                    help="staging root (default %s); the repo, a StreamingAssets tree and the "
                         "install are refused" % DEFAULT_ROOT)
    ap.add_argument("--from", dest="from_path", default=None,
                    help="read this container file instead of the install")
    ap.add_argument("--reskin", default=RESKIN_SPEC,
                    help="the spec whose CLUT half the ink must read under")
    ap.add_argument("--no-export", action="store_true",
                    help="skip `export-art` and stamp into an art directory that already exists")
    ap.add_argument("--game", default=None)
    a = ap.parse_args(argv)
    d = generate(a.ef, a.root, a.from_path, a.game, a.reskin, export=not a.no_export)
    print("\n".join(report(d)))
    # THE INVARIANT, enforced here and not merely described: the live window must be untouched, and
    # nothing may leave the marked rect.  Either failure destroys verdict 2 -- a marker inside the
    # window would show up in the capture whether or not anything blits -- so it is a non-zero exit,
    # not a warning.
    ok = (d["changed_in_window"] == 0 and d["changed_in_resting"] == 0
          and d["changed"] <= d["filled"])
    return 0 if ok else 1


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
