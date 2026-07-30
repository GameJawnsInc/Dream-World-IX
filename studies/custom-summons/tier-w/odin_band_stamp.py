r"""TIER W rung W6b-3 CAST B -- THE ODIN BANDS: the first depth-BEARING edit on a CHANNEL-A cell,
and the ORDER RIDER that comes free with it.

`odin_channel_a.toml` needs two indexed PNGs; this script writes both.  The vehicle is ef424
(`SpecialEffect.Odin__Short = 424`), reachable from bench row 203 "Stock Odin Short", and the two
targets are the two COLUMNS one multi-part `so` record names -- record 0x2f9a4, P = 2:

  * `cell.s0.x704_y384`  THE VERDICT.  Slot 1's column.  **Nothing else in the container binds it**
    (`page_depth_view` is ABSENT for both of its cells), so its 8 bpp is a fact only CHANNEL A states
    -- an entry of a MULTI-PART binding array the kit could not read before W6b-3.  A zero-write
    cannot test a depth (zeroing is depth-invariant); INK can, so what the screen shows judges the
    channel:

        clean bands           -> channel A's 8 bpp IS the draw depth
        pin-striped bands     -> the draw reads these bytes at 4 bpp (each ink byte splits into two
                                 nibble texels -- the ef446 "jittery" signature one level down)
        one solid WRONG hue   -> a 15 bpp read (byte pairs become direct words)

  * `cell.s0.x448_y384`  THE ORDER RIDER.  Slot 0's column, and SEVEN incumbent single-part records
    bind it too -- so it is licensed on the `so`-UV channel and carries NO acknowledgement key.  It
    gets a DIFFERENT band count, and the record's two parts are geometrically unconfusable (part 0 is
    a 32-prim square-section tube, part 1 a 68-prim flat billboard plane), so counting bands per
    SURFACE also reads which part sampled which entry.  **That read may not be promoted into a kit
    verdict**: `ORDER_UNMEASURED` (`summons/depth_attribution.py`) is a call-sited constant and
    lifting it is a separate, gated decision.  This script measures; it does not conclude.

TWO CELLS IN ONE RUN, WHICH IS THE ONE GENERALIZATION OVER `dome_band_stamp.py`.  The dome stamped a
single cell and the "one change per in-game test" rule was satisfied by the file being alone.  Here
the SECOND cell is not a second variable -- it is the CONTROL and the order instrument at once, and
the two marks are told apart by their COUNT (5 bands on the verdict cell, 3 on the order cell), which
is the whole reason the counts differ.  Splitting them across two deploys would cost a cast and answer
less.

THE FIGURES ARE TRANSLATION-INVARIANT ON PURPOSE (bands, never a shape).  The 704 pair has no
declared UV cover at all -- THE UV-SHREDDING BOUND -- so the offline flatness screen that licenses a
shape cannot clear it.  The 448 cell DOES have real cover (1,506 halfwords, geom 0x2ec34) and a shape
would be admissible there, but keeping both marks band-shaped keeps "count the bands" the single read.

WHERE THE ART COMES FROM, AND THE ONE PLACE THE SHIPPED EXPORT CANNOT REACH.
`summon-reskin export-art --ef 424` emits `cell.s0.x448_y384.png` and its `art.manifest.json` record,
so the 448 row is stamped from the SHIPPED export and rides the full ART-DRIFT guard.  It **refuses**
`cell.s0.x704_y384` by name (`depth-unknown`): `repaint.export_art` calls `scenery_surface` with no
`array_depth=True`, so the export lane has no channel-A acknowledgement and therefore no picture.
This script derives THAT cell itself, through the same shipped primitives with the ack threaded
(`repaint.texel_page(..., allow_array_depth=True)` -> `palette_words` -> `write_indexed_png`), and
writes it into a SEPARATE directory with NO manifest beside it -- because `_gate_manifest` refuses a
target the manifest carries no record for, and a manifest that cannot record the cell must not be
allowed to veto it.  The derivation is the kit's; only the ack is ours, and the spec states it.

The ink is DERIVED, never chosen: each cell's OWN display palette's max-luminance entry, taken from
that cell's own decoded palette.  Zero Square-Enix bytes live in this file; the art stays in SCRATCH.

Run AFTER `summon-reskin export-art --ef 424 --out <art dir>`:

    py odin_band_stamp.py --from C:\gd\SCRATCH\summon-format\ef424.bytes ^
       --art C:\gd\SCRATCH\summon-format\repaint-w6b\ef424-channel-a\art
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "ff9mapkit"))

from ff9mapkit.summons import repaint as RP                       # noqa: E402
from ff9mapkit.summons import reskin as RS                        # noqa: E402

EFFECT = 424
SCRATCH = os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format")
ROOT = os.path.join(SCRATCH, "repaint-w6b", "ef424-channel-a")
ART_DIR = os.path.join(ROOT, "art")
#: the channel-A cell's own art dir -- SEPARATE, and it must stay manifest-free (see the header).
ART_A_DIR = os.path.join(ROOT, "art-channel-a")
DEFAULT_CORPUS = os.path.join(SCRATCH, "ef%03d.bytes" % EFFECT)

VERDICT_CELL = "cell.s0.x704_y384"
ORDER_CELL = "cell.s0.x448_y384"

#: rows per band.  2x the census probe's 6-row zero stripe, exactly as the dome sized it, so the
#: screen names which INSTRUMENT drew even before it names which cell.
BAND_ROWS = 12
#: THE MARK IDENTITY IS THE COUNT.  5 on the verdict cell, 3 on the order cell -- and neither equals
#: the other or either cell's canonical zero-stripe k (10 and 2), which `odin_cell_probe.py` imports
#: from here and re-checks per run rather than restating.
BANDS = {VERDICT_CELL: 5, ORDER_CELL: 3}
PAGE_W = PAGE_H = 128

#: which cells need the CHANNEL-A acknowledgement to resolve at all.  A cell listed here gets its
#: base picture derived from the container by this script, because the shipped export refuses it.
ACK_ARRAY_DEPTH = {VERDICT_CELL: True, ORDER_CELL: False}

#: the suffix each stamped file takes, so a spec's `source` names the FIGURE and not just the cell.
SUFFIX = {VERDICT_CELL: "verdictbands", ORDER_CELL: "orderbands"}


def _fail(msg: str) -> "SystemExit":
    return SystemExit("REFUSED: " + msg)


#: THE SOURCE PIN.  What the two ladder cells MUST derive to on this vehicle, measured off ef424 and
#: re-checked on every run of both instruments.  ef130 -- the runbook's named fallback -- fails both
#: rows (its 704 cell is 4bpp, and its 448 cell REFUSES without an ack), which is the point.
SOURCE_PIN = {VERDICT_CELL: ("so-array", 8), ORDER_CELL: ("so-uv", 8)}


def pin_source(blob: bytes, path: str) -> str:
    """REFUSE a container that is not the effect these constants were measured on.

    ★ WHY THIS EXISTS, AND IT IS NOT TIDINESS.  ``EFFECT``, ``LADDER_CELLS``, ``BANDS`` and the probe's
    ``GAME_OVERRIDE`` destination are all MODULE CONSTANTS pinned to ef424, while ``--from`` is a free
    path.  Point ``--from`` at another container and every one of them silently keeps pointing at
    ef424: the probe stages a file named ``ef424.cellprobe`` holding the OTHER container's bytes and
    ``--deploy`` writes it to ``.../SpecialEffects/ef424``, and the stamp overwrites ef424's art with
    art derived from the other container -- which the kit's own guards do NOT catch, because
    ``expect_sha256`` guards the CONTAINER and the ART-DRIFT guard checks the manifest's stock sha,
    neither of which knows where a PNG's pixels came from.  The runbook's ef130 fallback says "same
    scripts with ``--from ef130.bytes`` and the cells re-pinned", and this is what makes "re-pinned"
    enforced instead of remembered.

    Two independent pins, because a name is a convention and a derivation is a fact:
      * the source's FILE NAME must name this module's ``EFFECT``;
      * both ladder cells must derive the depth AND the channel this ladder was measured on.
    """
    base = os.path.basename(path).lower()
    tag = "ef%03d" % EFFECT
    if tag not in base:
        raise _fail("--from names %r, which does not name this module's EFFECT (%s).  These scripts "
                    "pin ef%03d in EFFECT, %s, BANDS and the probe's GAME_OVERRIDE deploy path; "
                    "passing --from alone re-points the SOURCE and nothing else, so a probe built "
                    "from another container would be staged as `%s.cellprobe` and DEPLOYED over the "
                    "ef%03d override.  To run the ef130 fallback, re-pin EFFECT and the cells in BOTH "
                    "files (the runbook's section 5) -- not just --from."
                    % (base, tag, EFFECT, "VERDICT_CELL/ORDER_CELL", tag, EFFECT))
    out = []
    for cell, (want_src, want_bpp) in SOURCE_PIN.items():
        try:
            page = RP.texel_page(blob, cell, EFFECT,
                                 allow_array_depth=ACK_ARRAY_DEPTH.get(cell, False))
        except Exception as exc:                                    # noqa: BLE001
            raise _fail("%s does not resolve %s at all (%s: %s).  This is not the container these "
                        "constants were measured on." % (path, cell, type(exc).__name__,
                                                         str(exc).splitlines()[0][:160]))
        if (page.depth_source, page.bpp) != (want_src, want_bpp):
            raise _fail("%s resolves %s as %s/%dbpp, but this ladder was measured on %s/%dbpp.  A "
                        "different vehicle needs its own pins, not this one's."
                        % (path, cell, page.depth_source, page.bpp, want_src, want_bpp))
        out.append("%s %s/%dbpp" % (cell, want_src, want_bpp))
    return "source pin OK: %s names ef%03d and derives %s" % (base, EFFECT, "; ".join(out))


def evenly_spaced_tops(n: int, rows: int, lo: int, hi: int):
    """The TOP row of each of ``n`` evenly spaced ``rows``-row features inside the span ``lo..hi``.

    The census probe's own placement rule with the row count AND the span as parameters, so the two
    instruments space their marks identically and differ ONLY in count, duty and polarity -- three axes
    a video read can separate, where a fourth would just be noise.  ``lo=0, hi=127`` reproduces the
    ef211 whole-cell rule exactly.
    """
    span = hi - lo + 1
    out = []
    for s in range(n):
        centre = lo + int((s + 0.5) * span / n)
        out.append(max(lo, min(max(lo, hi - rows + 1), centre - rows // 2)))
    return out


def cover_span(blob: bytes, cell_xy):
    """The inclusive ``(lo, hi)`` LINE span every declared ``so`` reader of ``cell_xy`` samples, or None.

    ★ THE ONE GENERALIZATION OVER `dome_band_stamp.py`, AND IT IS NOT OPTIONAL HERE -- MEASURED.
    ef211's dome had no reader at all, so evenly spacing bands over all 128 lines could not miss.
    ef424's ORDER cell has a real reader whose cover is **rows 0..63 only** (geom 0x2ec34, 1,506
    halfwords).  The whole-cell rule would put its three band starts at 15 / 58 / 100 -- and the third
    lands where NOTHING samples, so the declared reader would show 2 bands where the mark says 3 and
    the ORDER READ (whose entire content is a count) would be silently wrong.  ef429's probe learned
    this same lesson the same way; the fix is the same one, lifted: when a cell HAS a cover, its bands
    are spread across the covered ROW SPAN; when it has none -- the channel-A verdict cell, where no
    prior exists -- they are spread across all 128 lines exactly as before.  THE COUNT SEMANTICS ARE
    UNTOUCHED; only where the count is drawn changes, and every cell's placement rule is printed.
    """
    rows = set()
    for m in RP.bound_models(blob):
        if cell_xy in m.cover:
            rows |= {hw // RS.PAGE_CELL_W for hw in m.cover[cell_xy]}
    return (min(rows), max(rows)) if rows else None


def placement_for(blob: bytes, cell: str, placement: str = "cover"):
    """``(lo, hi, rule)`` for ``cell`` -- its ``so`` cover span, or the whole cell."""
    page = RP.texel_page(blob, cell, EFFECT, allow_array_depth=ACK_ARRAY_DEPTH.get(cell, False))
    cov = cover_span(blob, page.cell) if placement == "cover" else None
    if cov is None:
        return 0, PAGE_H - 1, "whole-cell"
    return cov[0], cov[1], "so-cover"


def base_png(blob: bytes, cell: str, out_dir: str) -> str:
    """Decode ``cell`` to a paintable indexed PNG through the kit's own primitives.

    Only ever called for a cell the shipped `export-art` refuses.  ``allow_array_depth`` is passed
    because CHANNEL A is exactly what this cast tests: without it the cell has no derivable width and
    no picture at all, which is the refusal the spec then states out loud.
    """
    page = RP.texel_page(blob, cell, EFFECT, allow_array_depth=ACK_ARRAY_DEPTH.get(cell, False))
    words = RP.palette_words(blob, page)
    px = blob[page.page_offset:page.page_offset + page.page_bytes]
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, cell + ".png")
    RP.write_indexed_png(px, words, page.w, page.h, path)
    return path


def identity_gate(blob: bytes, cell: str, png: str) -> str:
    """THE NO-OP IDENTITY GATE: the PNG's index bytes must BE the container's cell bytes.

    Run on both sources BEFORE anything is drawn.  A depth experiment whose art lane silently
    re-quantized would produce a wrong picture that no gate downstream could distinguish from a wrong
    DEPTH -- the two failures look identical on screen, so the one that is checkable is checked here.
    """
    from PIL import Image

    page = RP.texel_page(blob, cell, EFFECT, allow_array_depth=ACK_ARRAY_DEPTH.get(cell, False))
    want = blob[page.page_offset:page.page_offset + page.page_bytes]
    got = Image.open(png).convert("P").tobytes()
    if got != want:
        bad = sum(1 for x, y in zip(got, want) if x != y)
        raise _fail("the indexed round trip is NOT a no-op on %s: %s decodes to %d index byte(s) "
                    "differing from the container's own %d (%d/%d moved).  A depth experiment cannot "
                    "ride an art lane whose identity is approximate."
                    % (cell, png, bad, len(want), bad, len(want)))
    return "no-op identity VERIFIED: %d index bytes match the container exactly" % len(want)


def stamp(blob: bytes, src: str, cell: str, out_path: str, placement: str = "cover") -> dict:
    """Ink ``BANDS[cell]`` bands into ``src`` and write ``out_path``.  Returns the census."""
    from PIL import Image

    img = Image.open(src)
    if img.mode != "P" or img.size != (PAGE_W, PAGE_H):
        raise _fail("%s is %s %r, expected an indexed P-mode (%d, %d) PNG.  The EXACT lane is the "
                    "format of record for a depth experiment -- no quantizer between the ink and the "
                    "bytes." % (src, img.mode, img.size, PAGE_W, PAGE_H))
    pal = img.getpalette()
    if not pal:
        raise _fail("%s carries no palette to derive an ink from" % src)
    lumas = [(2 * pal[3 * i] + 5 * pal[3 * i + 1] + pal[3 * i + 2], i) for i in range(256)]
    ink_luma, ink = max(lumas)

    # THE HOLE SET IS DERIVED FROM THE CONTAINER, NOT ASSUMED TO BE {0}.  On this vehicle the order
    # cell's palette row has a transparent TAIL (entries 100..255 are all 0x0000), so "skip index 0"
    # would be a rule that happens to be sufficient rather than one that is right.  Inking any
    # transparent index is a cutout FILL and would arm `acknowledge_cutout_reshape`; skipping the whole
    # derived set makes `= false` provable instead of lucky.
    page = RP.texel_page(blob, cell, EFFECT, allow_array_depth=ACK_ARRAY_DEPTH.get(cell, False))
    zeros = set(RP.transparent_indices(RP.palette_words(blob, page)))
    if ink in zeros:
        raise _fail("%s's brightest entry (index %d) is TRANSPARENT under this cell's own palette -- "
                    "refusing to ink with the cutout" % (src, ink))

    lo, hi, rule = placement_for(blob, cell, placement)
    cov = cover_span(blob, page.cell)
    cover_rows = set()
    for m in RP.bound_models(blob):
        if page.cell in m.cover:
            cover_rows |= {hw // RS.PAGE_CELL_W for hw in m.cover[page.cell]}

    px = img.load()
    starts = evenly_spaced_tops(BANDS[cell], BAND_ROWS, lo, hi)
    stamped = holes = already = other_holes = in_cover = 0
    per_band = []
    for y0 in starts:
        band = {"top": y0, "inked": 0, "holes": 0, "covered_rows": 0}
        for y in range(y0, min(y0 + BAND_ROWS, PAGE_H)):
            if y in cover_rows:
                band["covered_rows"] += 1
            for x in range(PAGE_W):
                v = px[x, y]
                # THE CUTOUT STAYS THE CUTOUT: a transparent texel is the model's silhouette, and
                # inking it would trip THE CUTOUT LAW (rightly).  A few pinholes in a 12-row band are
                # invisible at speed; a reshaped silhouette is a second variable.  On this vehicle
                # that is not a detail -- the verdict cell is 73.6% index-0.
                if v in zeros:
                    holes += 1
                    band["holes"] += 1
                    if v != 0:
                        other_holes += 1
                    continue
                if v == ink:
                    already += 1
                else:
                    stamped += 1
                band["inked"] += 1
                if y in cover_rows:
                    in_cover += 1
                px[x, y] = ink
        per_band.append(band)
    img.save(out_path)
    band_texels = len(starts) * BAND_ROWS * PAGE_W
    return {"cell": cell, "src": src, "out": out_path, "bands": BANDS[cell], "band_rows": BAND_ROWS,
            "starts": starts, "placement": rule, "span": [lo, hi],
            "cover_span": list(cov) if cov else None, "covered_rows": len(cover_rows),
            "ink": ink, "ink_luma": ink_luma,
            "ink_rgb": [pal[3 * ink], pal[3 * ink + 1], pal[3 * ink + 2]],
            "transparent_indices": sorted(zeros)[:4] + (["..."] if len(zeros) > 4 else []),
            "band_texels": band_texels, "inked": stamped + already, "changed": stamped,
            "already_ink": already, "holes": holes, "holes_not_index0": other_holes,
            "inked_in_cover": in_cover, "per_band": per_band,
            "hole_fraction": (holes / band_texels) if band_texels else 0.0,
            "duty_rows": len(starts) * BAND_ROWS,
            "duty_fraction": len(starts) * BAND_ROWS / float(PAGE_H)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from", dest="from_path", default=DEFAULT_CORPUS,
                    help="the STOCK container to derive the channel-A cell from (default the corpus)")
    ap.add_argument("--art", default=ART_DIR,
                    help="the `summon-reskin export-art` output dir -- where the `so`-UV cell's "
                         "exported PNG and its art.manifest.json live")
    ap.add_argument("--art-channel-a", default=ART_A_DIR,
                    help="where the CHANNEL-A cell's derived art goes.  MUST NOT hold an "
                         "art.manifest.json: the export lane cannot record a cell it refuses, and "
                         "_gate_manifest refuses a target its manifest has no record for")
    ap.add_argument("--placement", default="cover", choices=("cover", "whole-cell"),
                    help="where a COVERED cell's bands go: inside its `so` reader's own line span "
                         "(default -- ef424's order cell is covered on rows 0..63 only, so the "
                         "whole-cell rule would draw its third band where nothing samples and break "
                         "the count read), or evenly over all 128 lines (the ef211 rule -- the named "
                         "follow-up if the covered placement shows nothing, because a cell's UNBOUND "
                         "lines may be what actually reaches the screen)")
    a = ap.parse_args(argv)

    with open(a.from_path, "rb") as fh:
        blob = fh.read()
    pin = pin_source(blob, a.from_path)

    if os.path.exists(os.path.join(a.art_channel_a, RP.ART_MANIFEST)):
        raise _fail("%s holds an %s.  The shipped export REFUSES %s (`depth-unknown` -- export_art "
                    "passes no array_depth), so no manifest can carry a record for it, and "
                    "_gate_manifest refuses a target it has no record for.  Keep the channel-A art "
                    "in a manifest-free directory of its own."
                    % (a.art_channel_a, RP.ART_MANIFEST, VERDICT_CELL))

    # ---- the ORDER cell: stamped from the SHIPPED export, so the ART-DRIFT guard runs on it -------
    order_src = os.path.join(a.art, ORDER_CELL + ".png")
    if not os.path.exists(order_src):
        raise _fail("no exported cell at %s -- run `summon-reskin export-art --ef %d --out %s` first"
                    % (order_src, EFFECT, a.art))
    order_identity = identity_gate(blob, ORDER_CELL, order_src)
    order = stamp(blob, order_src, ORDER_CELL,
                  os.path.join(a.art, "%s.%s.png" % (ORDER_CELL, SUFFIX[ORDER_CELL])),
                  a.placement)
    order["manifest"] = os.path.exists(os.path.join(a.art, RP.ART_MANIFEST))
    order["identity"] = order_identity

    # ---- the VERDICT cell: derived HERE, because the shipped export refuses it --------------------
    verdict_src = base_png(blob, VERDICT_CELL, a.art_channel_a)
    verdict_identity = identity_gate(blob, VERDICT_CELL, verdict_src)
    verdict = stamp(blob, verdict_src, VERDICT_CELL,
                    os.path.join(a.art_channel_a, "%s.%s.png" % (VERDICT_CELL,
                                                                 SUFFIX[VERDICT_CELL])),
                    a.placement)
    verdict["manifest"] = False
    verdict["identity"] = verdict_identity

    rows = [verdict, order]
    print("odin_band_stamp -- ef%03d CAST B art written (2 cells, 1 run)" % EFFECT)
    print("  container       %s" % a.from_path)
    print("  %s" % pin)
    for r in rows:
        chan = "CHANNEL A (ack + expect_bpp)" if ACK_ARRAY_DEPTH[r["cell"]] else "so-UV (LICENSED)"
        print("")
        print("  %-22s %s" % (r["cell"], chan))
        print("    source        %s%s" % (r["src"],
                                          "" if r["manifest"] else "   (no art.manifest.json -- the "
                                                                   "spec's expect_* are the guard)"))
        print("    written       %s" % r["out"])
        print("    identity      %s" % r["identity"])
        print("    ink           index %d (this cell's own display palette max-luminance entry, "
              "luma %d)" % (r["ink"], r["ink_luma"]))
        print("    ink colour    rgb(%d, %d, %d) as rendered by the decode"
              % tuple(r["ink_rgb"]))
        print("    placement     %s, lines %d..%d%s"
              % (r["placement"], r["span"][0], r["span"][1],
                 ("   (so cover %d..%d, %d covered line(s))"
                  % (r["cover_span"][0], r["cover_span"][1], r["covered_rows"]))
                 if r["cover_span"] else "   (NO declared cover -- THE READERLESS BOUND)"))
        print("    bands         %d x %d rows (starts %r) -- duty %d/%d rows = %.1f%%"
              % (r["bands"], r["band_rows"], r["starts"], r["duty_rows"], PAGE_H,
                 100.0 * r["duty_fraction"]))
        print("    texels INKED  %d of %d band texels%s"
              % (r["inked"], r["band_texels"],
                 "  (+%d already the ink colour)" % r["already_ink"] if r["already_ink"] else ""))
        print("    cutout HOLES  %d SKIPPED (%.1f%% of the band, %d of them NOT index 0) -- the "
              "silhouette is not this cast's variable"
              % (r["holes"], 100.0 * r["hole_fraction"], r["holes_not_index0"]))
        if r["cover_span"]:
            print("    in the COVER  %d inked texel(s) land on a line some model declares it samples"
                  % r["inked_in_cover"])
            for b in r["per_band"]:
                print("      band @%3d   %4d inked, %2d/%d line(s) covered%s"
                      % (b["top"], b["inked"], b["covered_rows"], r["band_rows"],
                         "" if b["covered_rows"] else "   *** LOUD: THIS BAND IS INVISIBLE TO EVERY "
                                                      "DECLARED READER"))
            if any(not b["covered_rows"] for b in r["per_band"]):
                print("    *** LOUD: at least one band cannot be seen by any declared reader, so the "
                      "COUNT read is broken.")
                print("        Re-run with the default --placement cover, or accept that this cell's "
                      "mark identity is not %d." % r["bands"])
        if r["hole_fraction"] >= 0.5:
            print("    *** LOUD: MORE THAN HALF OF THIS CELL'S BAND AREA IS HARDWARE CUTOUT.  Only "
                  "%d texels carry ink," % r["inked"])
            print("        %.1f%% of the band and %.1f%% of the cell -- read the bands as a THINNING "
                  "of the surface's own"
                  % (100.0 * r["inked"] / r["band_texels"],
                     100.0 * r["inked"] / (PAGE_W * PAGE_H)))
            print("        structure at %d evenly spaced heights, not as %d solid stripes.  A NEGATIVE"
                  % (r["bands"], r["bands"]))
            print("        cast-B read on this cell is therefore only interpretable AFTER cast A "
                  "proved the cell drawn.")

    print("")
    print("  VERDICT KEY   clean bands = the channel's stated bpp IS the draw depth;")
    print("                pin-striped bands = a 4bpp read; one solid wrong hue = a 15bpp read.")
    print("  ORDER READ    %d bands on a surface = it sampled %s (record 0x2f9a4 slot 1);"
          % (BANDS[VERDICT_CELL], VERDICT_CELL))
    print("                %d bands = it sampled %s (slot 0).  ORDER_UNMEASURED stands either way: "
          % (BANDS[ORDER_CELL], ORDER_CELL))
    print("                the entry's ORDER within the array is NOT a kit verdict this cast may "
          "write.")

    man = {"effect": EFFECT, "container": a.from_path, "band_rows": BAND_ROWS,
           "bands": BANDS, "placement": a.placement, "rows": rows}
    # beside the art it describes, so a run with a non-default --art-channel-a cannot leave its
    # derivation record pointing at the default root's older one.
    derivation = os.path.join(os.path.dirname(os.path.abspath(a.art_channel_a)),
                              "bandstamp.derivation.json")
    with open(derivation, "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=1)
    print("")
    print("  derivation    %s" % derivation)
    return 0


if __name__ == "__main__":
    sys.exit(main())
