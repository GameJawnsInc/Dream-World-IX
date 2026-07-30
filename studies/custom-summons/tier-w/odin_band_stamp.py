r"""TIER W rung W6b-3 CASTS B *and* C -- THE ODIN BANDS: the first depth-BEARING edit on a CHANNEL-A
cell, the ORDER RIDER that comes free with it, and -- since the cast-B refutation -- THE DEPTH
DISCRIMINATOR the cast-B figure could not be.

★ WHY THIS FILE GREW AN INK-BYTE ARGUMENT.  Cast B inked with the cell's own max-luminance palette
entry, which on the verdict cell is index **255** -- byte `0xFF`.  An adversarial review of the cast-B
video then proved the figure CANNOT discriminate the depth, and the reason is arithmetic, not optics:

  * every one of the 2,311 changed bytes is `0xFF`, and at 4bpp that byte is nibbles **(15, 15) --
    TWO IDENTICAL TEXELS** -- so a 4bpp read renders the bands PERFECTLY SOLID.  "Clean vs
    pin-striped", the discriminator the cast-B header states below, was never a discriminator at all;
  * 87.4 % of the ink's 15bpp words are `0xFFFF` = pure white, so a 15bpp read gives WHITE bands at
    the SAME rows.  Colour does not separate 8 from 15 either;
  * band COUNT, ROW POSITION and SOLIDITY are DEPTH-INVARIANT by construction: the stamp writes whole
    byte ROWS, and a byte row is a texel row at 4, 8 and 15 bpp alike.

What survived was the cell IDENTITY (a threshold-free 2:1 in spatial frequency between cast A's k=10
and cast B's 5 on the same pixels) and the ordering.  The depth verdict survived only on an argument
about the SURROUNDING STOCK ART, which needed no ink at all.  So the ink must be re-chosen, and the
choice is the refuter's own: **byte `0xF0` instead of `0xFF`**, which the three depths cannot render
alike (all three numbers derived from the user's own container, never typed):

  ================  ==============================================================================
  8bpp              palette index 240 = `0xb9db` = **rgb(222,115,115) SALMON**.  It does NOT clip,
                    so its hue survives the additive blend (reads about (255,170,170) PINK).
  4bpp, CLUT base 0 nibbles (0, 15) -> index 0 = TRANSPARENT alternating with index 15 = `0x8403` =
                    rgb(24,0,8), luma 7.  A 50 %-duty 1-texel **TRANSPARENT COMB**: the surface
                    visibly THINS at five heights and no bright bar appears anywhere.
  15bpp             word `0xF0F0` = **rgb(131,57,230) VIOLET-BLUE**, and only 0.1 % of the javelin
                    body is blue -- unmissable.
  ================  ==============================================================================

THE COUNT STAYS FIVE.  Cast A gave 10 cycles and cast B 5 on the same pixels -- a threshold-free 2:1
that is what pins the cell.  Changing the count would spend that.  Cast C changes ONE thing, the ink
byte, which is the whole point of running it.

THE LITERAL-INK MODE TAKES THE BYTE LITERALLY AND REFUSES RATHER THAN SUBSTITUTING.  It does **not**
fall back to max-luminance the way the derived mode picks it: `--ink-byte` is a claim about a specific
palette ENTRY, and a mode that silently moved to a different entry would repaint the discriminator.
It refuses a byte that is not a lawful index in the cell's ACTIVE CLUT (the container's own entry
count, not PIL's padded 256), a byte whose entry is transparent under that CLUT (index 0 or any other
-- inking a transparent index is a cutout FILL and would arm `acknowledge_cutout_reshape`), and any
page whose derived depth is not 8 (where a BYTE is not an INDEX and "lawful index" has no meaning).

`odin_channel_a.toml` needs two indexed PNGs; this script writes both.  The vehicle is ef424
(`SpecialEffect.Odin__Short = 424`), reachable from bench row 203 "Stock Odin Short", and the two
targets are the two COLUMNS one multi-part `so` record names -- record 0x2f9a4, P = 2:

  * `cell.s0.x704_y384`  THE VERDICT.  Slot 1's column.  **Nothing else in the container binds it**
    (`page_depth_view` is ABSENT for both of its cells), so its 8 bpp is a fact only CHANNEL A states
    -- an entry of a MULTI-PART binding array the kit could not read before W6b-3.  A zero-write
    cannot test a depth (zeroing is depth-invariant); INK can, so what the screen shows judges the
    channel:

        ⚠⚠ THE THREE LINES BELOW ARE CAST B'S KEY AND ALL THREE ARE REFUTED.  Kept verbatim and
        labelled rather than deleted, because an instrument that quietly stops printing the claim it
        was read on cannot be audited.  With ink byte 0xFF none of them can occur -- see the ★ block
        at the top of this file, and use `--cast c`.

        clean bands           -> channel A's 8 bpp IS the draw depth        [VOID: solid at 4bpp too]
        pin-striped bands     -> the draw reads these bytes at 4 bpp (each ink byte splits into two
                                 nibble texels -- the ef446 "jittery" signature one level down)
                                                          [VOID: 0xFF is nibbles (15,15) -- IDENTICAL]
        one solid WRONG hue   -> a 15 bpp read (byte pairs become direct words)
                                                          [VOID: 0xFFFF is WHITE, same as index 255]

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

    py odin_band_stamp.py --cast c          # CAST C: the same 5 bands, ink byte 0xF0 on the verdict
                                            # cell; the order row is UNCHANGED and byte-identical
    py odin_band_stamp.py --cast c --emit-spec-guards      # the TOML guard lines, derived
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

#: ★ CAST C'S INK BYTE -- THE DEPTH DISCRIMINATOR, and the ONE constant that separates cast C from
#: cast B.  `0xF0` is not a taste: it is the unique small family of bytes whose three depth readings
#: are mutually exclusive AND all three visible (see the header table).  `0xFF` -- cast B's -- fails
#: on both counts at once, which is why cast B could not discriminate.
CAST_C_INK_BYTE = 0xF0

#: THE CAST PRESETS.  A cast is a MAP from cell to literal ink byte; a cell absent from the map keeps
#: TODAY'S behaviour (the cell's own display palette's max-luminance entry, derived).  `"b"` is
#: therefore the empty map BY CONSTRUCTION rather than by a flag -- which is what makes "cast B still
#: regenerates byte-identically" a property of the data instead of a promise in a docstring.
#:
#: ⚠ THE ORDER CELL IS DELIBERATELY ABSENT FROM CAST C, and it could not be present even if wanted:
#: index 240 is TRANSPARENT under `pal.s0.x0_y242.e256` (that palette's entries 100..255 are all
#: `0x0000`), so `--ink-byte cell.s0.x448_y384=0xF0` is REFUSED by name.  Cast C therefore moves
#: exactly ONE cell's bytes, which is the "one change per in-game test" rule spent where it counts:
#: cast C minus cast B is precisely the 2,311 verdict-cell ink bytes.
CASTS = {"b": {}, "c": {VERDICT_CELL: CAST_C_INK_BYTE}}


def _fail(msg: str) -> "SystemExit":
    return SystemExit("REFUSED: " + msg)


def palette_luma(pal, i: int) -> int:
    """The integer luma this module ranks palette entries by -- ONE definition, two call sites.

    Kept exactly as cast B computed it (`2R + 5G + B`, unnormalised) so the derived-ink path is
    bit-identical; a "better" luma here would silently re-pick cast B's ink and break the regeneration
    proof this file's whole default mode exists to keep.
    """
    return 2 * pal[3 * i] + 5 * pal[3 * i + 1] + pal[3 * i + 2]


def resolve_ink(pal, words, zeros, page, cell: str, src: str, literal=None):
    """``(index, luma, how)`` -- the ink this stamp will write, DERIVED or taken LITERALLY.

    ``literal is None`` reproduces cast B exactly: the cell's own display palette's max-luminance
    entry, refused if that entry is transparent.

    ``literal`` is CAST C, and it is a different KIND of statement -- a claim about one specific
    palette entry, made because the three candidate depths must render THAT entry differently.  So it
    is checked and refused, never adjusted:

    * **it is never re-picked as max-luminance.**  A mode that fell back would repaint the
      discriminator with cast B's own ink and the run would look like it had worked;
    * **the depth must be 8**, because at 4bpp a byte is TWO indices and at 15bpp it is half a colour
      -- "the byte 0xF0 is index 240" is only true at one depth, and stating it at another would be
      the same category error this cast exists to test for;
    * **the byte must be a lawful index in the cell's ACTIVE CLUT** -- ``page.clut_entries`` from the
      container's own header, never PIL's palette, which is padded to 256 whatever the row holds.  On
      a 16-entry row index 240 names nothing and the engine would read whatever follows the row;
    * **the entry must not be transparent** -- and the transparent set is DERIVED
      (:func:`RP.transparent_indices`), not assumed to be ``{0}``: on this vehicle the order cell's
      row has a transparent TAIL of 157 entries including 240 and 255, so "index 0" would be a rule
      that happened to be sufficient rather than one that is right.  Inking a transparent index is a
      cutout FILL, which would arm ``acknowledge_cutout_reshape`` and make the silhouette a second
      variable in a one-variable cast.
    """
    if literal is None:
        ink_luma, ink = max((palette_luma(pal, i), i) for i in range(256))
        if ink in zeros:
            raise _fail("%s's brightest entry (index %d) is TRANSPARENT under this cell's own palette "
                        "-- refusing to ink with the cutout" % (src, ink))
        return ink, ink_luma, "DERIVED (this cell's own display palette max-luminance entry)"

    ink = int(literal)
    if not 0 <= ink <= 255:
        raise _fail("--ink-byte %r on %s is not a byte (0..255).  A texel byte is what is written; "
                    "there is nothing else it could mean." % (literal, cell))
    if page.bpp != 8:
        raise _fail("--ink-byte 0x%02X names a palette INDEX, but %s derives %dbpp (%s).  A byte is "
                    "two indices at 4bpp and half a direct colour at 15bpp, so 'the byte 0x%02X is "
                    "index %d' is only true at 8 bpp.  The literal-ink mode refuses rather than "
                    "quietly meaning something else." % (ink, cell, page.bpp, page.depth_source, ink,
                                                         ink))
    entries = int(page.clut_entries or 0)
    if ink >= entries:
        raise _fail("--ink-byte 0x%02X = index %d is NOT a lawful index in %s's active CLUT: %s "
                    "declares %d entr%s (0..%d).  The engine would read whatever bytes follow the "
                    "row, which is not a colour anybody chose."
                    % (ink, ink, cell, page.palette_name or "the page's CLUT row", entries,
                       "y" if entries == 1 else "ies", max(0, entries - 1)))
    if ink in zeros:
        raise _fail("--ink-byte 0x%02X = index %d is TRANSPARENT under %s's own palette (%s): its "
                    "word is 0x0000, so inking with it is a cutout FILL, not a mark.  That would arm "
                    "`acknowledge_cutout_reshape` and make the SILHOUETTE a second variable in a cast "
                    "whose whole content is one variable.  This cell's transparent set is DERIVED and "
                    "holds %d entr%s (%s%s) -- it is not just index 0."
                    % (ink, ink, cell, page.palette_name or "its CLUT row", len(zeros),
                       "y" if len(zeros) == 1 else "ies",
                       ", ".join(str(z) for z in sorted(zeros)[:6]),
                       ", ..." if len(zeros) > 6 else ""))
    return ink, palette_luma(pal, ink), "LITERAL --ink-byte 0x%02X (taken as written; NOT re-picked)" % ink


def resolve_ink_map(cast: str, overrides) -> dict:
    """``{cell: literal ink byte}`` from a cast preset plus zero or more ``[CELL=]BYTE`` overrides.

    A cell ABSENT from the map keeps the derived max-luminance ink, so ``--cast b`` with no overrides
    is the empty map and cast B regenerates byte-for-byte.  A bare ``BYTE`` names every cell this
    script stamps, which is how the refusals are exercised: ``--ink-byte 0xF0`` alone is REFUSED on
    the order cell (index 240 is transparent under ``pal.s0.x0_y242.e256``), and that refusal is the
    honest answer rather than a silently skipped row.
    """
    out = dict(CASTS[cast])
    for spec in overrides or ():
        cell, _, raw = spec.rpartition("=")
        try:
            val = int(raw.strip(), 0)
        except ValueError:
            raise _fail("--ink-byte %r: %r is not an int literal (0xF0, 240, 0b11110000)"
                        % (spec, raw.strip()))
        if not cell:
            for c in BANDS:
                out[c] = val
        elif cell.strip() not in BANDS:
            raise _fail("--ink-byte %r names %r, which this script does not stamp.  The cells are: %s"
                        % (spec, cell.strip(), ", ".join(sorted(BANDS))))
        else:
            out[cell.strip()] = val
    return out


def other_depth_readings(blob: bytes, cell: str, byte: int, full: bool = False) -> list:
    """What the SAME ink byte becomes at the two depths this cast excludes -- DERIVED, never recalled.

    ★ THIS IS THE CAST'S WHOLE ARGUMENT, so it is computed from the container at run time instead of
    written into a table.  Cast B's verdict key WAS a written table, and it was wrong in both of its
    non-8bpp rows -- the 4bpp row claimed pin-striping from a byte whose two nibbles are IDENTICAL,
    and the 15bpp row claimed a wrong hue from a byte pair that is pure white.  A cast whose read is
    a colour must derive that colour.

    The three readings, all off the user's own bytes:

    * **8 bpp** -- the byte IS a palette index, coloured by the page's own CLUT row;
    * **4 bpp** -- the byte is TWO texels, ``low nibble first`` (:func:`RP.unpack4`'s measured order),
      indexing a 16-entry window of the same CLUT.  Two windows are reported: the NATURAL base 0 that
      an unchanged CLUT pointer selects, and the contrived ``base 240`` window -- the only window
      whose index 15 is cast B's own ink, and the one residue the cast-B refutation left undecidable;
    * **15 bpp** -- byte PAIRS become direct BGR555 words, so an all-``0xF0`` run is the word
      ``0xF0F0`` and the colour owes nothing to any palette.
    """
    from ff9mapkit.summons import texture as KT

    page = RP.texel_page(blob, cell, EFFECT, allow_array_depth=ACK_ARRAY_DEPTH.get(cell, False))
    w = RP.palette_words(blob, page)
    lo, hi = byte & 0x0F, byte >> 4                  # RP.unpack4: out[2i] = raw[i] & 0x0F

    def rgb(word):
        r, g, b, alpha = KT.bgr555_rgba(word)
        return ("TRANSPARENT (word 0x0000)" if not alpha
                else "rgb(%3d,%3d,%3d) word %#06x" % (r, g, b, word))

    def entry(i):
        return rgb(w[i]) if i < len(w) else "NO SUCH ENTRY (CLUT row holds %d)" % len(w)

    L = ["8bpp   -> index %d = %s" % (byte, entry(byte)),
         "4bpp   -> nibbles (%d, %d), low first; CLUT base 0   = %s  +  %s"
         % (lo, hi, entry(lo), entry(hi)),
         "          the same nibbles in the contrived base-240 window = %s  +  %s"
         % (entry(240 + lo), entry(240 + hi)),
         "15bpp  -> word %#06x = %s" % ((byte << 8) | byte, rgb((byte << 8) | byte))]
    if full:
        L += ["",
              "    SO THE SCREEN CANNOT REPORT TWO OF THESE AS THE SAME THING:",
              "      8bpp   a SALMON/PINK brightening at %d heights that does NOT clip, so its hue"
              % BANDS[cell],
              "             survives the additive blend (~(255,170,170) over a 40-70 luma backdrop);",
              "      4bpp   index %d is the CUTOUT and index %d is luma-7 near-black, so the bands are"
              % (lo, hi),
              "             a 50%-duty 1-texel TRANSPARENT COMB: the surface THINS, no bright bar;",
              "      15bpp  a saturated VIOLET-BLUE, on a javelin body that is 99.9% red-family and",
              "             0.1% blue.",
              "    Cast B could report none of them: its ink byte 0xFF is (15,15) at 4bpp -- two",
              "    IDENTICAL texels, hence SOLID -- and 0xFFFF at 15bpp -- pure WHITE at the same rows."]
    return L


def spec_guard_lines(blob: bytes, path: str, rows) -> list:
    """The spec's `expect_*` block, DERIVED from this container, for every stamped row.

    The guards exist to make a wrong page or a wrong depth a REFUSAL, so a guard copied from memory
    (or from a sibling spec) is a guard that can agree with the wrong thing.  Emitting them from the
    same `texel_page` derivation the build will re-run makes "derived, never typed" mechanical.
    """
    import hashlib

    sha = hashlib.sha256(blob).hexdigest()
    L = ["[reskin]", "effect = %d" % EFFECT, 'expect_sha256 = "%s"' % sha,
         "#   sha256 of %s" % path, ""]
    for r in rows:
        page = RP.texel_page(blob, r["cell"], EFFECT,
                             allow_array_depth=ACK_ARRAY_DEPTH.get(r["cell"], False))
        L += ["[[reskin.texel]]",
              'name = "%s"' % page.name,
              'source = "%s"' % r["out"].replace("\\", "/"),
              "expect_page_offset = %#07x" % page.page_offset,
              "expect_page_bytes  = %d" % page.page_bytes,
              "expect_page_wh     = [%d, %d]" % (page.w, page.h),
              "expect_bpp         = %d      # depth_source = %s" % (page.bpp, page.depth_source),
              "expect_cell        = [%d, %d]" % page.cell,
              'palette_from = "%s"' % page.palette_name,
              ("acknowledge_array_derived_depth = true" if page.depth_source == "so-array" else
               "# NO acknowledgement key on this row: depth_source = %s, which the kit LICENSES."
               % page.depth_source),
              ""]
    return L


def out_name(cell: str, literal=None) -> str:
    """The stamped file's name.  A literal ink puts its own byte in the name, so a cast-C run can
    never overwrite the cast-B figure that is live on the install and whose ledger is already taken."""
    if literal is None:
        return "%s.%s.png" % (cell, SUFFIX[cell])
    return "%s.%s.ink%02x.png" % (cell, SUFFIX[cell], int(literal))


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


def stamp(blob: bytes, src: str, cell: str, out_path: str, placement: str = "cover",
          literal=None) -> dict:
    """Ink ``BANDS[cell]`` bands into ``src`` and write ``out_path``.  Returns the census.

    ``literal is None`` is cast B (derived max-luminance ink); a byte is cast C.  Only the INK moves
    -- count, rows, placement rule and the cutout skip are the same code on both casts, which is what
    makes the two containers differ in exactly one thing.
    """
    from PIL import Image

    img = Image.open(src)
    if img.mode != "P" or img.size != (PAGE_W, PAGE_H):
        raise _fail("%s is %s %r, expected an indexed P-mode (%d, %d) PNG.  The EXACT lane is the "
                    "format of record for a depth experiment -- no quantizer between the ink and the "
                    "bytes." % (src, img.mode, img.size, PAGE_W, PAGE_H))
    pal = img.getpalette()
    if not pal:
        raise _fail("%s carries no palette to derive an ink from" % src)

    # THE HOLE SET IS DERIVED FROM THE CONTAINER, NOT ASSUMED TO BE {0}.  On this vehicle the order
    # cell's palette row has a transparent TAIL (entries 100..255 are all 0x0000), so "skip index 0"
    # would be a rule that happens to be sufficient rather than one that is right.  Inking any
    # transparent index is a cutout FILL and would arm `acknowledge_cutout_reshape`; skipping the whole
    # derived set makes `= false` provable instead of lucky.
    page = RP.texel_page(blob, cell, EFFECT, allow_array_depth=ACK_ARRAY_DEPTH.get(cell, False))
    words = RP.palette_words(blob, page)
    zeros = set(RP.transparent_indices(words))
    ink, ink_luma, ink_how = resolve_ink(pal, words, zeros, page, cell, src, literal)

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
            "ink": ink, "ink_luma": ink_luma, "ink_how": ink_how,
            "ink_literal": (None if literal is None else int(literal)),
            "ink_word": words[ink], "palette_name": page.palette_name,
            "clut_entries": page.clut_entries,
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
    ap.add_argument("--cast", default="b", choices=sorted(CASTS),
                    help="which CAST's ink map to use.  `b` (default) is TODAY: every cell takes its "
                         "own display palette's max-luminance entry, so the cast-B artifacts "
                         "regenerate byte-identically.  `c` is THE DEPTH DISCRIMINATOR: the verdict "
                         "cell takes the literal byte 0x%02X, whose 8 / 4 / 15 bpp readings are salmon "
                         "/ a transparent comb / violet-blue and cannot be confused.  The order cell "
                         "is in NO preset and stays derived." % CAST_C_INK_BYTE)
    ap.add_argument("--ink-byte", action="append", default=[], metavar="[CELL=]BYTE",
                    help="override the cast's ink map: `CELL=BYTE` for one cell, or a bare `BYTE` for "
                         "every stamped cell.  BYTE is any Python int literal (0xF0, 240, 0b11110000)."
                         "  Repeatable.  The byte is taken LITERALLY -- it is never re-picked as "
                         "max-luminance -- and is REFUSED if the cell's derived depth is not 8, if it "
                         "is not a lawful index in that cell's active CLUT, or if that entry is "
                         "transparent")
    ap.add_argument("--emit-spec-guards", action="store_true",
                    help="also print the TOML guard block (`expect_sha256`, `expect_page_offset`, "
                         "`expect_page_bytes`, `expect_page_wh`, `expect_bpp`, `expect_cell`) DERIVED "
                         "from this container for each stamped row, so a spec's guards are copied "
                         "from a derivation instead of typed from a memory of one")
    a = ap.parse_args(argv)

    with open(a.from_path, "rb") as fh:
        blob = fh.read()
    pin = pin_source(blob, a.from_path)
    ink_map = resolve_ink_map(a.cast, a.ink_byte)

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
                  os.path.join(a.art, out_name(ORDER_CELL, ink_map.get(ORDER_CELL))),
                  a.placement, ink_map.get(ORDER_CELL))
    order["manifest"] = os.path.exists(os.path.join(a.art, RP.ART_MANIFEST))
    order["identity"] = order_identity

    # ---- the VERDICT cell: derived HERE, because the shipped export refuses it --------------------
    verdict_src = base_png(blob, VERDICT_CELL, a.art_channel_a)
    verdict_identity = identity_gate(blob, VERDICT_CELL, verdict_src)
    verdict = stamp(blob, verdict_src, VERDICT_CELL,
                    os.path.join(a.art_channel_a, out_name(VERDICT_CELL,
                                                           ink_map.get(VERDICT_CELL))),
                    a.placement, ink_map.get(VERDICT_CELL))
    verdict["manifest"] = False
    verdict["identity"] = verdict_identity

    rows = [verdict, order]
    # The banner names the ACTUAL ink map, not just the preset -- an `--ink-byte` override that left
    # the banner saying "CAST B" would put a figure nobody cast under a name somebody trusts.
    print("odin_band_stamp -- ef%03d CAST %s%s art written (2 cells, 1 run)"
          % (EFFECT, a.cast.upper(),
             " + OVERRIDES" if ink_map != CASTS[a.cast] else ""))
    print("  container       %s" % a.from_path)
    print("  %s" % pin)
    print("  ink map         %s" % (", ".join("%s = 0x%02X (LITERAL)" % (c, v)
                                              for c, v in sorted(ink_map.items()))
                                    or "empty -- every cell DERIVES its own max-luminance ink "
                                       "(cast B, byte-for-byte)"))
    for r in rows:
        chan = "CHANNEL A (ack + expect_bpp)" if ACK_ARRAY_DEPTH[r["cell"]] else "so-UV (LICENSED)"
        print("")
        print("  %-22s %s" % (r["cell"], chan))
        print("    source        %s%s" % (r["src"],
                                          "" if r["manifest"] else "   (no art.manifest.json -- the "
                                                                   "spec's expect_* are the guard)"))
        print("    written       %s" % r["out"])
        print("    identity      %s" % r["identity"])
        print("    ink           index %d, luma %d -- %s" % (r["ink"], r["ink_luma"], r["ink_how"]))
        print("    ink colour    rgb(%d, %d, %d) as rendered by the decode  (word %#06x under %s, "
              "%d entries)"
              % (tuple(r["ink_rgb"]) + (r["ink_word"], r["palette_name"], r["clut_entries"])))
        if r["ink_literal"] is not None:
            print("    *** OTHER DEPTHS  the SAME byte 0x%02X read at the two depths this cast excludes:"
                  % r["ink_literal"])
            for line in other_depth_readings(blob, r["cell"], r["ink_literal"]):
                print("                    %s" % line)
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
    if ink_map.get(VERDICT_CELL) is None:
        # CAST B's key, and it is WRONG -- kept verbatim, labelled, because a refuted instrument that
        # quietly stops printing its own claim is an instrument nobody can audit.
        print("  *** VERDICT KEY (CAST B) -- REFUTED, DO NOT READ A DEPTH OFF IT.  It said: clean bands")
        print("    = the stated bpp IS the draw depth; pin-striped = 4bpp; one solid wrong hue = "
              "15bpp.")
        print("    All three rows are void with ink 0xFF: at 4bpp that byte is nibbles (15,15) = TWO")
        print("    IDENTICAL TEXELS so the bands are SOLID, and 87.4% of its 15bpp words are 0xFFFF =")
        print("    WHITE at the same rows.  Count, row position and solidity are DEPTH-INVARIANT -- a")
        print("    byte row is a texel row at every depth.  Run `--cast c` for a figure that CAN "
              "discriminate.")
    else:
        print("  *** VERDICT KEY (CAST C) -- three MUTUALLY EXCLUSIVE outcomes, derived above:")
        for line in other_depth_readings(blob, VERDICT_CELL, ink_map[VERDICT_CELL], full=True):
            print("    %s" % line)
    print("  ORDER READ    %d bands on a surface = it sampled %s (record 0x2f9a4 slot 1);"
          % (BANDS[VERDICT_CELL], VERDICT_CELL))
    print("                %d bands = it sampled %s (slot 0).  ORDER_UNMEASURED stands either way: "
          % (BANDS[ORDER_CELL], ORDER_CELL))
    print("                the entry's ORDER within the array is NOT a kit verdict this cast may "
          "write.")

    if a.emit_spec_guards:
        print("")
        print("  ---- SPEC GUARDS, DERIVED FROM THIS CONTAINER (copy into the spec; never type them) "
              "----")
        for line in spec_guard_lines(blob, a.from_path, rows):
            print("  %s" % line)

    man = {"effect": EFFECT, "container": a.from_path, "band_rows": BAND_ROWS,
           "bands": BANDS, "placement": a.placement, "cast": a.cast,
           "ink_map": {c: v for c, v in sorted(ink_map.items())}, "rows": rows}
    # beside the art it describes, so a run with a non-default --art-channel-a cannot leave its
    # derivation record pointing at the default root's older one.  AND the ink signature is in the
    # NAME, for the same reason `out_name` puts it in the figure's: a cast-C run must not overwrite
    # the derivation record of the cast-B container that is live on the install.
    sig = "".join(".%s-%02x" % (c.split(".")[-1], v) for c, v in sorted(ink_map.items()))
    derivation = os.path.join(os.path.dirname(os.path.abspath(a.art_channel_a)),
                              "bandstamp%s.derivation.json" % sig)
    with open(derivation, "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=1)
    print("")
    print("  derivation    %s" % derivation)
    return 0


if __name__ == "__main__":
    sys.exit(main())
