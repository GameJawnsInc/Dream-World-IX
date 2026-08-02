r"""THE SUMMON TEXEL REPAINT (lever #2): repaint a STOCK summon's own texture pages in place.

    ff9mapkit summon-reskin export-art --ef 227          # decode every creature page to a paintable PNG
    ff9mapkit summon-reskin plan   bahamut_emblem.toml   # resolve every texel target + run every gate
    ff9mapkit summon-reskin build  bahamut_emblem.toml   # stage the patched container + scripts + previews
    ff9mapkit summon-reskin verify bahamut_emblem.toml   # re-check what is staged, AS BYTES

or as an API::

    from ff9mapkit.summons import repaint
    spec = repaint.load_spec("bahamut_emblem.toml")
    b    = repaint.build(spec, "bahamut_emblem.toml")    # reads the install, splices the pages
    b.check = repaint.self_check(b)                      # every gate, on OUR bytes
    repaint.stage(b)                                     # override + revert scripts + previews

WHAT THIS IS, AND WHY IT IS A SIBLING RATHER THAN MORE ``reskin.py``
---------------------------------------------------------------------
:mod:`ff9mapkit.summons.reskin` is lever #1 -- a per-index COLOUR FUNCTION over the container's own
CLUTs. It can rotate a hue; it structurally cannot move a texel from one index to another, so it can
never change a shape, an edge or a silhouette. This module is lever #2: it rewrites the INDICES.
``reskin.py``'s own docstring earmarks itself as lever-#1-only and says the repaint "is a different
lane and this module refuses to do it" -- honoured here. What ``reskin.py`` already DERIVES is
consumed rather than re-derived (``creature_pages``, ``PaletteMap``, ``texanim_region``, ``_regions``,
``scenery_pages``/``id9_pages`` for the collision census), exactly the way ``reskin.py`` itself
consumes :mod:`~ff9mapkit.summons.container`.

THE SCOPE, W6a THEN W6b-1 -- TWO SURFACES, AND A LANE THAT IS ATTRIBUTION-LIMITED
---------------------------------------------------------------------------------
W6a shipped the id-4 CREATURE pages: the one texel class measurably free of every known hazard.
W6b-1 adds the SCENERY VRAM page-cells at 4 / 8 / 15 bpp -- and the honest shape of that surface is
an asymmetry, not a capability list. **The lane is not codec-limited; it is attribution-limited.**
Every depth round-trips byte-identically over the whole corpus, and **2,385 of the 2,572 scenery
cells (92.7%) have no ``so`` reader at all**, so their bit depth is not a fact the container states
and the probe built to guess it was FALSIFIED at 54.5% on a three-way choice. So the codec never
fails and the gate refuses 93% of the surface.

Three verdicts, kept apart on purpose, because collapsing them is how a tool starts lying:

* **REFUSE** -- depth-unknown, same-bytes-two-depths, program-VRAM WRITE (:func:`_gate_program_vram`)
  and a spilling model's unwritten column. No art fixes any of them (:data:`W6B_REASON`);
* **REMEDY** -- co-transform (:func:`_gate_cotransform`: name every writer, art for each, say the
  word) and u-spill (:func:`_gate_spill_columns`: name every column the model reads). Both mirror the
  CLUT lane's own multi-writer shape and neither has a bypass key;
* **DISCLOSE** -- shared read, multi-palette, the program-VRAM READ direction verdict and the lower
  half (:func:`_scenery_disclosures`). Refusing these would refuse a coherent edit; saying nothing
  would let an author change a model, or tune a colour, they never saw.

The creature surface's own argument, unchanged:

* **single-writer, 24/24.** Re-measured over the corpus this rung: 24 decodable creature packages,
  93 pages, **0 VRAM-cell collisions and 0 file-span collisions** against every scenery page rect and
  every id-9 alternate block. The creature owns VRAM ``x`` in ``[192, 384)`` (measured: every one of
  the 93 pages sits at x 192/256/320) and nothing else in the container writes there. That is
  CHECKED per target (:func:`_gate_collisions`), not assumed -- six corpus effects place id-9 slots
  at x = 320, precisely the ladder rungs their own ``partCount`` leaves unused, so the near miss is
  real and only a derived test can tell it from a hit.
* **uniform 8bpp.** ``texture_check`` reports the 128x128 / ``partCount * 0x4000`` layout decodable
  on 24/24. A 4bpp or 15bpp-direct page is a different codec and is refused.
* **one chunk's worth of writers.** The corpus's whole multi-writer page census is 34 cells in 5
  containers (ef225/227/251/381/447) and every one of them is SCENERY. The CO-TRANSFORM LAW is the
  multi-chunk law, and creature pages are outside it -- but the gate tests the cells, not the chunk
  count, because ef227 IS a two-chunk container and a chunk-count refusal would refuse the one
  effect this rung is proven on.

W6b-2 -- WHERE A DEPTH COMES FROM: TWO CHANNELS, TWO POSTURES, ONE LINE
------------------------------------------------------------------------
The lane above is attribution-limited, so W6b-2 asks whether the container states a cell's depth
SOMEWHERE ELSE. It does, in two places, and they do not carry the same authority:

> **CHANNEL G LICENSES. CHANNEL P DISCLOSES, and edits only behind an explicit acknowledgement.**

* **CHANNEL G** (:func:`ff9mapkit.summons.reskin.page_depth_view`) -- the container's OWN ``so``
  records, re-read at **PAGE** rather than **UV** granularity. *DEPTH is a property of the PAGE;
  READERSHIP is a property of the UVs*, and one 64x256 page word names a COLUMN of two stacked 64x128
  cells. **57 readerless cells** gain their column's depth; 55 of them are lower halves only the
  per-cell map can name. Not new evidence -- the same record at the granularity the hardware uses --
  so it is LICENSED, and it flows through every other gate unchanged (56 build, 1 refuses on a
  program write);
* **CHANNEL P** (:data:`ff9mapkit.summons.depth_attribution.PROGRAM_DEPTH`) -- the depth the effect's
  own id-3 program REGISTERS a page at, recovered as a constant. **189 cells**, and it is DISCLOSED
  rather than licensed for one measured reason: the channel's own written upgrade path was *"P earns
  a licence when a cast proves a program-derived depth on screen"*, **that trigger fired once and it
  FAILED** (ef251, tpage 312, registered 15bpp, drew at 4bpp). An edit unlocks only with
  ``acknowledge_program_derived_depth = true`` AND an ``expect_bpp`` that MATCHES the derivation.
* **Four new refusals** -- ``program-dual-depth`` (22 cells, 10 containers), ``channel-g-dual-depth``
  (8, named in no dossier), ``spill-vs-own-page`` (2, which protects nothing new and exists to
  carry the reason) and ``program-depth-no-palette``. Unanimity is the verdict rule; **two values is
  a hazard, not a vote**, and no acknowledgement lifts one. The last is the one an author meets most:
  channel P states a DEPTH and names no CLUT, so **134 of its 189 cells are indexed and none of them
  can be rendered** -- the acknowledgement's live surface is the 55 that are 15bpp DIRECT.
* **Two channel sets** (:data:`CENSUS_CHANNELS` / :data:`LICENSED_CHANNELS`) so no published W6b-1
  count moved under a caller that did not ask for the new channel -- the ``include_direct`` precedent.

W6b-3 -- CHANNEL A: THE SAME RECORD, READ AT ITS TRUE LENGTH
--------------------------------------------------------------
The ``so`` record is a MULTI-PART BINDING ARRAY and the reader hard-probed two lengths, so 126 records
and 309 binding slots were invisible. Repairing the reader is a SAFETY fix (it repaired five false
``DERIVED PRIVATE`` palette verdicts); licensing what it reveals is a separate decision, and it is
refused.

> **A IS FOR ARRAY, NOT ARCHIVE. CHANNEL A DISCLOSES -- at channel P's tier, for a harsher reason.**

* the census (``so-uv``) and CHANNEL G are held to the **INCUMBENT** witness, so every W6b-1/W6b-2
  count is byte-identical BY CONSTRUCTION AT ITS INPUT rather than by inspection;
* **CHANNEL A** (:func:`ff9mapkit.summons.reskin.array_depth_view`) discloses 65 cells and emits only
  behind :data:`ACK_ARRAY_DEPTH` plus a matching ``expect_bpp``. Channel P's one in-game trial FAILED;
  channel A has had none it passed (:data:`~ff9mapkit.summons.depth_attribution.ARRAY_CAVEAT`);
* ⚠ **its hazards hold VETO power and never emission power**, so ``array-dual-depth`` (12 cells) and
  ``array-vs-column-depth`` (2) can take away a page ``so-uv``/``so-page`` earned -- **the rung's one
  deliberate permissiveness regression, and it is confined to channel sets that name ``so-array``.**
  Every count in the W6b-2 section above is therefore a W6b-2-SCOPE count; the delta on the shipped
  set is stated by :data:`~ff9mapkit.summons.depth_attribution.A2_SCOPE_NOTE`, which every
  author-facing string quoting one of them carries;
* the array's ARITY is measured twice and its ORDER by nothing, so ``parts`` is a **SET** everywhere:
  a reason string names a record and a slot as IDENTIFICATION, and no verdict maps part *k* to entry
  *k* (:data:`~ff9mapkit.summons.depth_attribution.ORDER_UNMEASURED`).

W6b-3 (iii) -- THE SECOND ARRAY: A DISCLOSURE ABOUT **READERSHIP**, NOT A DEPTH
--------------------------------------------------------------------------------
Every channel above answers *"at what depth are these bytes read?"*. The ``so`` record's SECOND array
-- the ``P x {u16, u16}`` block the reader walked past until this rung -- raises a different question:
**is this cell read at all?** A stock log-only cast of ef038, read through the U1 s77 instrument,
MEASURED it as a **per-slot texel displacement** -- pair position 0 onto ``u``, pair position 1 onto
``v``, ``+128`` texels each (one 8bpp column, 640 -> 704) -- at **0.97 on ONE container**, with the
displacement baked into the submitted primitive and ABSENT from the container's stored UV pool. So
every span this module holds is the UNDISPLACED coordinate, and the kit still models NOTHING with it:

* :attr:`CellHazards.second_array` carries, per reader, the non-zero pair and both candidate
  effective columns -- purely informational, and empty wherever the caller did not consult;
* ``second-array-mover`` refuses -- **appended alongside, never displacing** -- a cell ALL of whose
  readers carry a non-zero pair (52 corpus cells in 29 containers, 47 of them fully open today). It
  is labelling-independent BY CONSTRUCTION -- it never asks which halfword moves which axis and never
  applies a displacement -- which is why the measurement moved none of those three numbers;
* it is in NEITHER ``_UNADDRESSABLE`` nor ``_EXPORT_BLOCKING``, and :data:`ACK_SECOND_ARRAY` pairs
  with **no** ``expect_bpp``. **The emission set does not move**: same pages, names, depths, bytes.
* the conditionality travels IN the constant
  (:data:`~ff9mapkit.summons.depth_attribution.U_DISPLACEMENT_CAVEAT`), quoted at the refusal, the
  build gate, the disclosure and the report block -- *a caveat nothing quotes is a wish.*

W6b-3 (iv) -- THE SECOND ARRAY, **ADOPTED**: THE EFFECTIVE COVER
------------------------------------------------------------------
Three more casts closed the two riders the disclosure above rode on. The mechanism GENERALISED
(ef227 -- key ISOLATED, tri ratio 1.00, control gate PASS -- and ef446, control gate PASS, with ef038
reproducing in the same log) and the OPERATION was settled by a decisive value test on ef227: its
answer slot's raw pool is ``{0, 25, 55, 85, 111}`` and the observed extremes were
``{16, 41, 101, 127}``, which are pool values PLUS 16. OR would read 25 and 85, XOR 9 and 69, and a
FLAG reading predicts a DISJOINT range. **The operation is LINEAR ADDITION**, and this rung applies
it. It is the first rung in this lane that deliberately changes behaviour.

> **READERSHIP IS EFFECTIVE. THE RECORD'S OWN STATEMENT IS BOUND. THE KIT KEEPS BOTH AND NAMES BOTH.**

* :func:`sampled_halfword` is the SEAM -- one arithmetic site, ``effective = stored + halfword`` per
  axis -- and :func:`assert_intra_page` is the LAW it is checked against, on every displaced binding,
  at the site that SPENDS the displacement (:func:`effective_cell_readers`) rather than at the
  rasteriser every scope walks: a tpage is cell-aligned and ``u, v`` are bytes, so a displaced read
  never leaves its own page (340/340). That is what makes LINEAR vs mod-256 WRAP degenerate, an
  arriving reader's depth non-extrapolated, and an off-VRAM read impossible. **A scope that declined
  ``so-displaced`` cannot fail on this law**, which is what makes the two frozen surfaces unmoved as
  a structural property and not as a fact about the stock corpus;
* :attr:`BoundModel.cover` / :func:`cell_readers` are UNMOVED and keep their meaning forever;
  :attr:`BoundModel.effective_cover` / :func:`effective_cell_readers` are the readership answer, and
  the two are the SAME OBJECT on every non-mover, so the undisplaced path is untouched BY
  CONSTRUCTION;
* **three classes**, all measured: ``displaced-readerless`` (45 cells / 26 containers, 41 of them
  previously LICENSED and paintable -- the silent-failure class this rung exists to close),
  ``displaced-readership-substituted`` (7, where a DISJOINT foreign set arrives instead) and
  ``displaced-vs-page-depth`` (1 VETO). The first two are lifted by the EXISTING
  :data:`ACK_SECOND_ARRAY`, which is the same key those rows already needed in order to build --
  **and it lifts the REFUSAL, not the guarantee**: over the 55 page NAMES the two cover, 39 return
  the identical picture, 6 return a DIFFERENT one (four of them 4bpp read back as 8bpp) and 10
  return NOTHING, falling through to ``depth-unknown`` or ``channel-g-dual-depth``;
* **the gain half is adopted by DEFAULT and behind no new key**: 70 declared cells acquire a reader,
  29 of them (30 page names) refused ``depth-unknown`` before. It is not a new channel -- it is the
  sampling arithmetic of one the licensed path already consults, at the same evidentiary tier.
  **DERIVABLE IS NOT DELIVERABLE:** 27 of the 30 hand back a paintable PNG (21 in the default
  indexed lane, 6 at 15bpp via ``direct15``); the other 3 are all ef038 and all carry the older
  ``program-vram-write`` refusal, which is why the deliverable worked case is ef038's twin ef407.
  ⚠ **AND THIS HALF IS THE RUNG'S HONEST LIMIT.** The loss half fails LOUDLY -- a refusal, with a
  stated key to argue with it. The gain half fails SILENTLY: the page is licensed on the derivation
  ALONE, nothing binds the cell to contradict it, and there is no key and no CLI way to decline. If
  ``linear-add-v1`` does not hold on a container, a perfect repaint of a gained cell is INVISIBLE IN
  GAME with no error anywhere -- the same failure the loss half refuses to let an author risk,
  pointing the other way. Every such cell is printed ``GAINED`` in the export scaffold, and a CAST is
  the only thing that closes it;
* **a third channel set**: :data:`CENSUS_CHANNELS` (frozen at W6b-1) / :data:`LICENSED_CHANNELS`
  (frozen at the W6b-3 scope every gate board is written about) / :data:`EDIT_CHANNELS` (what an
  author walks). The delta is a diff between two NAMED sets, never a number that moved under a
  constant's old name.

THE TEXANIM CO-TRANSFORM (W7) -- AN OBLIGATION, NOT A REFUSAL
--------------------------------------------------------------
On the five armed packages (ef038 / ef177 / ef493 / ef494 / ef495) this lane used to refuse outright,
with no key. W7 read the table (:mod:`ff9mapkit.summons.texanim`), so the hazard is now a KNOWN set of
rects instead of an opaque window: per clip, the live destination window plus every source frame it can
blit into it. Three outcomes, checked per target against the actual edit:

* the edit touches NO protected rect -> builds;
* the edit covers every rect of each clip family -> builds (a whole-page repaint lands here BY
  CONSTRUCTION, which is why L3 needs no key);
* the edit repaints SOME rects of a family and leaves siblings stock -> REFUSES, naming the clip and
  the exact rects left stock, unless the row says ``acknowledge_texanim_frames = true``.

An armed region the reader cannot DECODE still refuses exactly as it did pre-W7 -- the lift is
conditional on a successful parse, never on the absence of an exception. And under all of it sits
THE REGION INVARIANT (``reskin.assert_region_invariant``): ``firstBlock``, ``min(motionOffsets)`` and
the region's own bytes are asserted unchanged after every splice.

THE FORMAT OF RECORD: AN INDEXED (P-MODE) PNG, NOT RGBA
-------------------------------------------------------
Measured over all 93 stock pages: ``decode -> P-mode PNG (palette = the CLUT row, tRNS = entry 0) ->
reload -> indices`` is **byte-identical 93/93**. The RGBA lane is not: 8.31% of the corpus's palette
entries are duplicates of the full 16-bit word, so an identity RGBA round-trip already flips 1,844 of
16,384 texels on ef251 part 0 and byte-identity -- and with it the gate this whole lane rests on --
simply dies. So the indexed lane is the format of record, the PNG's palette is DISPLAY ONLY (the
container remains the palette authority and this lane writes zero CLUT bytes), and RGBA / quantize /
mint-CLUT are W6b and refuse by name.

THE CUTOUT LAW, AT THE TEXEL LEVEL
-----------------------------------
``texture.bgr555_rgba`` maps ``0x0000 -> (0,0,0,0)``: transparency is by VALUE, and the corpus puts
exactly one such entry in every row, always at index 0 (93/93; it is the only STP-clear entry in the
whole corpus, 93 of 23,808). A texel edit therefore controls the SILHOUETTE, which a palette edit
never could. So: a texel whose index crosses the transparent-entry boundary is counted **in both
directions** -- ``punch`` (opaque -> hole) and ``fill`` (hole -> opaque) -- and any non-zero count
REFUSES unless the row says ``acknowledge_cutout_reshape = true``. That is the one escape hatch this
lane needs and the CLUT lane does not: reshaping a torn wing edge is a legitimate texel-level move.
The transparent index set is DERIVED from the active palette, not assumed to be ``{0}``.

THE DEAD PAD -- REPORTED, NEVER FATAL
--------------------------------------
Only **64.0%** of the corpus's creature texels are sampled by any face (975,202 of 1,523,712); the
rest is pad. And >99.6% of a page's dead texels form ONE border-connected margin, so "paint inside
the island" is a complete instruction -- which is why every export ships a ``<name>.coverage.png``
whose green hatch is the never-sampled region, rasterised from the container's OWN uv pools
(:func:`coverage`). It cannot be derived from the pixels: ef227's dominant pad INDEX differs per part
(138/111/109/164/80/104) while all six decode to the same word, and the pad index also occurs inside
the sampled island. Editing dead texels is INERT, exactly the way a hue rotation is inert on
``reskin.py``'s achromatic cloud bands -- so it is reported with its count and never fails a build.

THE REGION PARTITION IS INVERTED, NOT COPIED
---------------------------------------------
``reskin.py``'s ``_regions`` gates "the id-4 header + all N texel pages" byte-identical -- correct for
a CLUT-only lane and exactly backwards for this one. It takes a ``partition`` parameter now: this
lane licenses ``[tex_file_offset, +tex_bytes)`` and gates the id-4 header, the CLUT strip, the sector
pad, sector 0, every id-3 program, the id-5 model image (which is where the texanim table and the
UVs live), every camera block and every GEOM block. One function, two partitions -- never a second
copy that drifts.

COMPOSITION WITH THE CLUT LANE
-------------------------------
The two levers are byte-disjoint by construction (palettes at ``[0x621a0, 0x62da0)`` on ef227, texel
pages at ``[0x4a1a0, 0x621a0)``) and the kit PROVES it rather than asserting it: this build's
changed-offset set is intersected with a rebuilt sibling's. Two composition routes, one artifact:

* **one spec, both tables** -- a spec carrying ``[[reskin.target]]`` AND ``[[reskin.texel]]`` builds
  the CLUT lane first and hands its patched bytes to this one (the CLI's own path);
* **``[reskin.orthogonality] reskin = "..."`` + ``compose = true``** -- a texel-only spec composes on
  a SHIPPED reskin spec's rebuild, so the palette half keeps exactly one source of truth instead of
  being copied into a second file that can drift.

Either way it is ONE container, ONE ledger and ONE revert, and the composed delta is gated disjoint.

HOT RELOAD
----------
Stronger here than for the CLUT lane: ``SFX.Play`` re-reads the container from disc every cast AND
calls ``PSXTextureMgr.Reset()`` unconditionally, and a PAGE upload is itself the event that
invalidates the decoded-texture cache. Recast to see it -- no ``~`` reload, no warp, no relaunch.

PROVENANCE
----------
The container is read at RUN TIME from the user's own install under a sha256 drift guard. **Every
exported page PNG is decoded Square-Enix content**: :func:`export_art` puts every destination through
:func:`ff9mapkit.summons.export.assert_local_only` (a git checkout, a ``StreamingAssets`` tree and
the resolved install are all refused, with no ``--force``), and the manifest carries the stock sha256
so a repaint can never be packed against a container it was not exported from. This module carries
offsets, counts and VRAM coordinates -- no run of stock bytes and no stock palette.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import struct
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

from . import container as EC
from . import depth_attribution as DA
from . import export
from . import rescore as R
from . import reskin as RS
from . import texanim as TA
from . import texture as KT
from .ledger import Ledger

__all__ = [
    "RepaintError", "W6B_REASON", "INDEXED_RGBA_REASON", "MINT_CLUT_REASON",
    "MOD_SUBPATH", "STAGING_BASE", "staging_root", "CREATURE_VRAM_X", "ART_MANIFEST",
    "TexelPage", "creature_texel_pages", "texel_page", "other_page_writers",
    # --- W6b-1: the scenery surface -------------------------------------------------------------
    "PROGRAM_VRAM_WRITE_IDS", "PROGRAM_VRAM_READ_IDS", "MOVEIMAGE_HARD_CELLS", "program_class",
    "CELL_LINES", "cell_texel_w", "BoundModel", "bound_models", "cell_readers",
    "CellWriter", "CellReader", "CellHazards", "CellRefusal",
    "scenery_surface", "scenery_texel_pages", "scenery_cell_refusals", "assert_expect_bpp",
    # --- W6b-2: the depth-attribution channels (P discloses, G licenses) ------------------------
    "ACK_PROGRAM_DEPTH", "ACK_ARRAY_DEPTH",
    "DEPTH_SOURCES", "CENSUS_CHANNELS", "LICENSED_CHANNELS",
    "clut_arity", "depth_attribution_lines",
    # --- W6b-3 (iii): the SECOND ARRAY, disclosed (a READERSHIP question, never a depth) ----------
    "ACK_SECOND_ARRAY", "SecondArrayRead",
    # --- W6b-3 (iv): the SECOND ARRAY, ADOPTED -- the effective cover ----------------------------
    "EDIT_CHANNELS", "DISPLACEMENT_MODEL", "sampled_halfword", "effective_cell",
    "assert_intra_page", "effective_cell_readers", "novel_displacement_reach",
    # --- W6b-1: the codecs ----------------------------------------------------------------------
    "pack4", "unpack4", "write_indexed4_png", "read_indexed4_png",
    "stp_sidecar_path", "write_direct_png", "read_direct_png", "direct_transparent",
    "texel_view", "transparent_values",
    "Coverage", "coverage", "coverage_mask", "border_flood",
    "palette_words", "transparent_indices", "png_palette",
    "write_indexed_png", "read_indexed_png", "write_coverage_png",
    # --- W6q: the PAINT (quantize) lane ---------------------------------------------------------
    "PAINT_RENDER_KEY", "CUBE_DIAG_SQ", "AlternateRow", "alternate_palette_rows",
    "write_paint_png", "write_swatch_png", "read_paint_png",
    "quantize_census", "census_record", "census_lines",
    "read_art_manifest", "art_came_out_of_base",
    "resolve_art_path", "absent_paint_line", "missing_paint_sources",
    "ART_LANES", "export_art", "scaffold_text", "scenery_lines",
    "TexelTarget", "TexelBuild", "load_spec", "build",
    "Gate", "SelfCheck", "self_check", "ORTH_REBUILDERS",
    "render_previews", "stage", "verify", "modfilelist_refusal",
    "describe", "derivation_lines", "check_lines",
]


class RepaintError(RuntimeError):
    """A refusal from the texel lane. A refusal is a RESULT of this tool, never an exception to hide."""


def _ack_bool(d: dict, key: str, where: str) -> bool:
    """A safety acknowledgement must be a LITERAL BOOLEAN -- W5's own minted law, re-stated here so a
    texel refusal raises a texel error. ``acknowledge_cutout_reshape = "false"`` must REFUSE, never
    arm: an acknowledgement is stated, never inferred from a truthy string."""
    v = d.get(key, False)
    if not isinstance(v, bool):
        raise RepaintError("%s: %s must be a BOOLEAN (true/false), not %r.  A safety acknowledgement "
                           "must be stated, never inferred from a truthy string." % (where, key, v))
    return v


#: THE OUT-OF-SCOPE REASON, quoted verbatim by every refusal that has to say what this lane still will
#: not do, so a report line names a measured surface instead of reading like a bug.
#:
#: **THE SUCCESSOR STRING (W6b-1).** The W6a wording named four clauses -- co-transform,
#: same-bytes-two-bindings, u-spill and 15bpp -- and THREE of them are now shipped mechanisms rather
#: than refusals: co-transform has the name-every-writer remedy (:func:`_gate_cotransform`, 16 corpus
#: cells), u-spill has the name-every-column remedy (:func:`_gate_spill_columns`, 70 UV-exact cells)
#: and 15bpp ships as the ``direct15`` lane (exhaustive 65,536/65,536 word identity). Leaving the old
#: string in place would have made every refusal quote three capabilities as excuses. What actually
#: remains, each clause with its own measurement:
#:
#: * **depth-unknown** -- 2,385 of 2,572 scenery cells (92.7%) declare no ``so`` reader, so their bit
#:   depth is not a fact the container states, and the probe built to guess it was FALSIFIED at 54.5%;
#: * **same-bytes-two-depths** -- 17 cells over 6 effects, two index arrays over one byte block;
#: * **program-VRAM WRITE** -- 175 cells over 15 containers, 3 of them refused by cell name;
#: * **unwritten-column spill** -- 10 bindings (all ef390, all 15bpp) sample a column no writer in
#:   their own container uploads: there is nothing there to repaint. ⚠ W6b-3 (iv) re-aimed this gate
#:   at the EFFECTIVE cover and the population is **11 over TWO containers** there -- the same 10 plus
#:   ef082 GEOM ``0x1dcd8`` (15bpp, pair ``(0,128)``), which reads unwritten VRAM *because the measured
#:   displacement put it there*, not because another effect left bytes behind.
#:
#: **THE W6b-2 SUCCESSOR CLAUSE, and only that clause moved.** The depth-unknown surface is no longer
#: 2,385: channel G (the container's own ``so`` records at PAGE granularity) LICENSES 57 of them and
#: channel P (the id-3 program's own registered tpage) DISCLOSES 189 more behind
#: :data:`ACK_PROGRAM_DEPTH`.
#:
#: ⚠ **TWO POPULATIONS, BOTH STATED, BECAUSE A FLAT LIST HERE DOUBLE-COUNTS.** The number the shipped
#: derivation actually refuses under the name ``depth-unknown`` on the EDIT surface is **2,298** --
#: W6b-1's 2,385 less channel G's 57 and less the 30 cells that now refuse under their own dual-depth
#: names. The record's residue of cells with **no depth on any channel** is **2,139**: those 2,298
#: less the 189 channel P discloses, plus the 30 dual-depth cells, which W6b2-ATTRIBUTION.md sec 2
#: places INSIDE the residue as a SUBSET and never as an addend. Both are printed below and the
#: arithmetic between them is spelled out, because this string is what an author is handed on an
#: unresolved name; ``w6b2i_gates.py`` I9 re-measures the first against the derivation rather than
#: matching it as a substring. The other three clauses are untouched W6b-1 measurements.
W6B_REASON = ("W6b-2 attributes 246 of W6b-1's 2,385 depth-unknown cells (189 program / 57 "
              "`so`-at-page); what still refuses on that surface is: DEPTH-UNKNOWN (2,298 cells "
              "refuse under this name on the edit surface, 189 of them DISCLOSING a program-derived "
              "depth an acknowledgement can unlock; take those 189 out and put the 30 dual-depth "
              "cells below back in -- they are a SUBSET of this population, never an addend -- and "
              "the residue with no depth on ANY channel is 2,139: 1,278 in containers that register "
              "nothing, 861 the lever does not cover; the guessing probe FALSIFIED at 54.5%) / "
              "DUAL-DEPTH BY ATTRIBUTION (22 program + 8 channel-G, both INSIDE the 2,139 above, + 2 "
              "spill-vs-own-page, which are OUTSIDE it entirely -- 32 cells, three populations, "
              "READ THE POPULATION AND DO NOT ADD THEM UP) / SAME-BYTES-TWO-DEPTHS (17) / "
              "PROGRAM-VRAM WRITE (175, 3 by cell) / a spilling model's UNWRITTEN COLUMN (10).  "
              + DA.A2_SCOPE_NOTE)

#: the W6b-2 acknowledgement's spec key, re-exported here so a caller never spells it as a literal.
ACK_PROGRAM_DEPTH = DA.ACK_KEY

#: the W6b-3 acknowledgement's spec key (CHANNEL A), re-exported for the same reason.
ACK_ARRAY_DEPTH = DA.ACK_ARRAY_KEY

#: the W6b-3 (iii) acknowledgement's spec key (THE SECOND ARRAY), re-exported for the same reason.
#: ⚠ Unlike the two above it admits **no depth** and pairs with **no** ``expect_bpp``: what it
#: acknowledges is a question about READERSHIP, and there is no number to check it against.
ACK_SECOND_ARRAY = DA.ACK_MOVER_KEY

#: where a scenery page's ``bpp`` came from -- carried on the page itself, because a depth that is
#: INHERITED FROM A COLUMN and a depth a model's own UVs declare are not the same kind of fact and a
#: disclosure that cannot tell them apart cannot say the second sentence W6b-2 requires.
#:
#: * ``"so-uv"``   -- an ``so`` reader whose stored UVs land in THIS cell states it (W6b-1, 187 cells);
#: * ``"so-page"`` -- CHANNEL G: no reader samples the cell, but its COLUMN carries exactly one
#:   ``so``-stated depth, so the depth is inherited from the page (57 cells; 55 of them lower halves
#:   addressable only through the per-cell map -- both counts at the W6b-2 channel scope, see
#:   :data:`ff9mapkit.summons.depth_attribution.A2_SCOPE_NOTE`). **LICENSED** -- it is the same
#:   record read at the granularity the hardware uses;
#: * ``"so-array"`` -- CHANNEL A (W6b-3): no reader samples the cell and no ``P <= 1`` record names
#:   its column, but an ENTRY of a MULTI-PART ``so`` record's binding array does (65 cells). It is
#:   the SAME record class channel G reads, read at its true length -- **not new evidence, an old
#:   reader repaired**. **DISCLOSED, and edits only behind** :data:`ACK_ARRAY_DEPTH` plus a matching
#:   ``expect_bpp``, at channel P's tier and for a harsher reason: channel P's one in-game trial
#:   FAILED, channel A has had none it passed
#:   (:data:`ff9mapkit.summons.depth_attribution.ARRAY_CAVEAT`);
#: * ``"program"`` -- CHANNEL P: the container's own id-3 program registers this page at a constant
#:   depth (189 cells). **DISCLOSED, and edits only behind** :data:`ACK_PROGRAM_DEPTH` plus a matching
#:   ``expect_bpp`` -- see :data:`ff9mapkit.summons.depth_attribution.REGISTRATION_CAVEAT`, which is
#:   an in-game refutation and not a caution.
#:
#: ⚠ **W6b-3 (iii) ADDS NO TOKEN HERE, DELIBERATELY.** The ``so`` record's SECOND array is not a
#: DEPTH channel -- it raises a READERSHIP question (:data:`ACK_SECOND_ARRAY`) -- and this tuple is
#: load-bearing in two guards that would both be wrong about it: :func:`scenery_surface`'s
#: unknown-channel check and :func:`assert_expect_bpp`'s ``_DEPTH_DERIVED_BY`` coverage assert.
DEPTH_SOURCES = ("so-uv", "so-page", "so-array", "program")

#: **THE CENSUS CHANNEL SET** -- W6b-1's own, and the DEFAULT of :func:`scenery_surface`.
#:
#: A PARAMETER, NEVER A SECOND DERIVATION -- the precedent
#: :func:`ff9mapkit.summons.reskin.attribution`'s ``include_direct`` set, and its stated reason
#: applies here word for word: the default is chosen so that **every published W6b-1 count is
#: byte-for-byte what it was**. `w6b_gates` G6 and `w6q_gates` G1/G16 pin that census (56 lawful,
#: 20 lower-half-only, 2,385 depth-unknown, the paint surface's texel totals), and a rung that
#: silently re-aimed the function those gates measure would have moved the thing they were written
#: about while every one of them still read green on a different population.
CENSUS_CHANNELS = ("so-uv",)

#: **THE LICENSED CHANNEL SET** -- the EDIT surface's, and the default of every author-facing entry
#: point (:func:`scenery_texel_pages`, :func:`scenery_cell_refusals`, :func:`texel_page`,
#: :func:`export_art`, :func:`scenery_lines`, :func:`build`).
#:
#: * ``"so-page"`` -- CHANNEL G is ADOPTED: 57 readerless cells gain their column's depth, and the
#:   8 cells whose column carries TWO depths refuse under their own name. ⚠ **That 57 is channel G's
#:   own count at the W6b-2 channel scope, and this set is no longer that scope** -- channel A, one
#:   bullet down, can withdraw a page channel G earned. The counts are not restated (A is disclosed,
#:   never adopted); the delta is stated in full by
#:   :data:`ff9mapkit.summons.depth_attribution.A2_SCOPE_NOTE`, which every author-facing string
#:   quoting one of those counts carries;
#: * ``"so-array"`` -- CHANNEL A is CONSULTED (W6b-3), at exactly channel P's tier: the
#:   depth-unknown reason gains the array's depth (a DISCLOSURE), emitting additionally needs
#:   ``array_depth=True`` i.e. :data:`ACK_ARRAY_DEPTH`, and the two array HAZARD classes refuse under
#:   their own names. ⚠ **CONSULTING CHANNEL A CAN TAKE A PAGE AWAY.** Its hazards hold **VETO**
#:   power and never emission power, so a cell whose column the array names at a depth that
#:   CONTRADICTS the incumbent one, or at two depths at once, refuses on this path even where
#:   ``so-uv`` or ``so-page`` would otherwise have served it. That is the rung's one deliberate
#:   permissiveness regression, and it is confined to this channel set: under
#:   :data:`CENSUS_CHANNELS` channel A is not consulted, so it can neither add nor withdraw a cell;
#: * ``"program"`` -- CHANNEL P is CONSULTED: the depth-unknown reason gains the program's registered
#:   depth (a DISCLOSURE) and a program-DUAL cell refuses under its own name. **Consulting is not
#:   adopting**: emitting a channel-P page additionally needs ``program_depth=True``, which is what
#:   :data:`ACK_PROGRAM_DEPTH` sets. A consumer states which KINDS of depth fact it accepts, and
#:   *"a depth a model's own UVs declare"*, *"a depth inherited from the column"*, *"a depth an ENTRY
#:   of the column's binding ARRAY states"* and *"a depth the program REGISTERS"* are four different
#:   kinds.
LICENSED_CHANNELS = ("so-uv", "so-page", "so-array", "program")

#: **THE EDIT SURFACE'S CHANNEL SET (W6b-3 (iv))** -- :data:`LICENSED_CHANNELS` plus the one token
#: this rung mints, and the default of every author-facing entry point
#: (:func:`scenery_texel_pages`, :func:`scenery_cell_refusals`, :func:`texel_page`,
#: :func:`export_art`, :func:`scenery_lines`, :func:`build`).
#:
#: * ``"so-displaced"`` -- **ADOPTED**: the reader join is taken on
#:   :attr:`BoundModel.effective_cover` instead of :attr:`BoundModel.cover`, i.e. on the cell the
#:   hardware SAMPLES rather than the cell the record BINDS. It requires ``"so-uv"`` in the same set
#:   (enforced at the call site, below) because it is not a new channel at all -- it is the SAMPLING
#:   ARITHMETIC of a channel this set already consults, and there is no coherent sense in which a
#:   caller consults ``so-uv`` while declining its correct arithmetic.
#:
#: ⚠ **AND :data:`LICENSED_CHANNELS` IS FROZEN AT THE W6b-3 SCOPE ON PURPOSE.** It is the population
#: ``u1_gates`` U2/U3/U5, ``w6q_gates`` G1/G16 and ``w6b3i_gates`` I4/I9 are written ABOUT, and two
#: boards DERIVE their own W6b-2 scope from it as ``tuple(c for c in RP.LICENSED_CHANNELS if c !=
#: "so-array")`` -- so appending a token to it would have silently re-aimed every number in those
#: files at a surface they were never measured on. This is the same two-scope device
#: :data:`CENSUS_CHANNELS` is, one channel later, and it is why the delta this rung emits is a
#: nameable diff between two named sets rather than a number that moved under a constant's old name.
EDIT_CHANNELS = LICENSED_CHANNELS + ("so-displaced",)

#: every token :func:`scenery_surface` accepts. **NOT** :data:`DEPTH_SOURCES`: ``"so-displaced"``
#: states no depth (it re-aims READERSHIP), so putting it in ``DEPTH_SOURCES`` would break both
#: guards that constant is load-bearing in -- the unknown-channel check here and
#: :func:`assert_expect_bpp`'s ``_DEPTH_DERIVED_BY`` coverage assert.
_CHANNEL_TOKENS = frozenset(DEPTH_SOURCES) | frozenset(("so-displaced",))

#: THE INDEXED LANE'S RGBA REFUSAL, in its own words -- deliberately NOT :data:`W6B_REASON`.
#:
#: That constant is about which SCENERY CELLS remain out of scope; this refusal is about EXACT
#: RECOVERY on the indexed lane and would still hold if every cell in the corpus were lawful. The two
#: were one string until W6b-1 and the RGBA sites quoted it only because it was the only one there.
#: Splitting them is what stops a SCOPE change from quietly rewriting an IDENTITY argument -- and the
#: identity argument itself (93/93 indexed, 1,844 texels moved by an RGBA no-op, 8.31% duplicate CLUT
#: words) is unchanged, verbatim, at both call sites.
INDEXED_RGBA_REASON = ("RGBA / quantize / mint-CLUT stay refused on the INDEXED lane and W6b-1 does "
                       "not touch that: the refusal is about EXACT RECOVERY, not about scope -- a "
                       "lane whose no-op is not a no-op cannot carry a byte-identity gate")

#: WHY `--mint-clut` (writing a NEW palette row fitted to the art) IS STILL DEFERRED -- quoted
#: verbatim by :data:`R12`'s refusal (a paint row asking for a hole on a row that has none) and by
#: ``docs/SUMMONS.md``.
#:
#: It is a constant with a CALL SITE, not a docstring: a reason nothing quotes is a wish. And it is
#: deliberately NOT :data:`INDEXED_RGBA_REASON` -- that one is about EXACT RECOVERY on the indexed
#: lane and is untouched by W6q; this one is about what a palette WRITER would still owe. The W6q
#: quantize lane writes INDICES ONLY and zero CLUT bytes, which is exactly why it could ship while
#: this stays deferred.
MINT_CLUT_REASON = (
    "MINT-CLUT (writing a NEW palette fitted to the art) stays deferred, and the reason is measured "
    "rather than architectural: the mechanism EXISTS -- a mint decomposes into a CLUT-lane row write "
    "and a texel-lane index write, each gated by the partition that already licenses exactly it.  "
    "What is missing is (1) STP is CARRIED, never recomputed, and gated as a per-palette POPULATION, "
    "and the blow-out and headroom gates key on a KNOB and a STOCK PEAK -- a minted entry has none of "
    "the three, so each needs a replacement LAW, not a replacement number; (2) MEASURED, the "
    "shared-read direction inverts and is unbounded -- 298 of 365 duplicate groups on 11 of 16 "
    "class-C cells already render DIFFERENTLY through the cell's other CLUT key, so an authored row "
    "binds N-1 readers whose pictures nobody has looked at, and measuring that radius is a playtest "
    "per reader rather than a gate.  The kit already HAS a palette writer that satisfies all of it: "
    "`[[reskin.target]]`, per-entry, cutout-preserving and gated.  Use it, or paint against the row "
    "you have with `source_paint` (W6q).")

#: the on-disc override lane, shared with both sibling lanes (extensionless -- ``LoadFromDisc`` reads
#: the raw path, so ``ef227.bytes`` would never be found).
MOD_SUBPATH = R.MOD_SUBPATH

#: THE STAGING BASE -- a per-effect directory lands under it, and it is re-checked through
#: :func:`ff9mapkit.summons.export.assert_local_only` every time it is used as a default. Distinct
#: from the reskin and rescore bases on purpose: a composed build stages a DIFFERENT container from a
#: plain reskin of the same effect, and two lanes sharing one root would have them overwrite each
#: other's ledger -- and the ledger is the artifact whose loss is unrecoverable.
STAGING_BASE = export.DEFAULT_OUT_DIR / "repaint"

#: the VRAM ``x`` band (in halfwords) the creature owns outright. MEASURED, not assumed: all 93 stock
#: creature pages sit at x 192, 256 or 320, and no scenery rect or id-9 block in the corpus declares a
#: cell inside the band. It is a DISCLOSURE used in refusal text; the actual gate is the per-target
#: cell/span intersection in :func:`_gate_collisions`, because a band test cannot see a collision that
#: a future container puts inside the band.
CREATURE_VRAM_X = (192, 384)

#: the sidecar every export writes and every import re-reads as a drift guard.
ART_MANIFEST = "art.manifest.json"

#: the scaffold an export drops beside the PNGs: a fully guarded, pre-seeded-OFF texel spec.
SCAFFOLD_NAME = "texel.scaffold.toml"


def staging_root(effect: int, root=None) -> str:
    """The per-effect staging root: ``<root or STAGING_BASE>/ef###``.

    PER EFFECT for the same reason ``reskin.staging_root`` is: with one root for every effect a second
    summon staged in the same session silently overwrites the first one's container, previews,
    manifest and revert script.
    """
    return os.path.join(str(root or STAGING_BASE), "ef%03d" % int(effect))


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ============================================================ (1) THE PAGE MAP -- all derived
@dataclass(frozen=True)
class TexelPage:
    """One addressable texel page: where its bytes are, what shape they decode to, and which CLUT row
    colours them. Every field is DERIVED from the container's own headers through the kit's shipped
    decoders -- a span derived from a header nobody read is a guess.

    TWO KINDS, ONE RECORD (W6b-1). ``kind == "creature"`` is the id-4 page W6a shipped: named by PART
    index, always 128x128 8bpp, with its own row of the id-4 CLUT strip. ``kind == "scenery"`` is a
    **VRAM page-cell** (:class:`ff9mapkit.summons.reskin.PageCell`): named by WRITER and cell,
    ``0x4000`` bytes at 4 / 8 / 15 bpp, and it owns **no palette of its own** -- a scenery cell's
    colours come from the id-0 inline CLUT stream, so ``clut_offset`` / ``clut_entries`` are
    ``Optional`` and the palette is resolved through the CLUT lane's own name in ``palette_name``.
    At 15bpp there is no palette at all and all three are ``None`` / ``""``.
    """
    name: str                    # "tex.part0" | "cell.s0.x704_y256" -- the texel namespace
    index: int
    page_offset: int
    page_bytes: int
    w: int                       # TEXEL width (128 creature; 256/128/64 scenery at 4/8/15 bpp)
    h: int
    bpp: int
    clut_offset: Optional[int]
    clut_entries: Optional[int]
    tpage: int
    clut: int
    v_offset: int
    vram: Tuple[int, int]
    palette_name: str            # the CLUT lane's own name for the row this page indexes into
    #: which surface this page belongs to -- ``"creature"`` (W6a) or ``"scenery"`` (W6b-1).
    kind: str = "creature"
    #: the VRAM page-cell ``(x, y)`` this page occupies. ``None`` on a CREATURE page, whose addressable
    #: unit is the id-4 PART (its ``vram`` is where that part happens to land, and the id-4 handler
    #: uploads it by part index, not by cell) -- so the two are deliberately not conflated.
    cell: Optional[Tuple[int, int]] = None
    #: every hazard the container states about this cell, as DATA for the gates to read. ``None`` on a
    #: creature page: W6a measured that surface hazard-free (0 collisions over 24 packages / 93 pages)
    #: and ``_gate_collisions`` re-checks it per target rather than trusting a field.
    hazards: Optional["CellHazards"] = None
    #: W6b-2: WHICH CHANNEL ``bpp`` CAME FROM -- one of :data:`DEPTH_SOURCES`. Never a decoration: the
    #: build path keys the acknowledgement ladder on it, and every disclosure that ships an INHERITED
    #: depth has to be able to say so in the same breath as the number.
    depth_source: str = "so-uv"
    #: W6b-3 (iv): ``"bound"`` or ``"displaced"`` -- whether any reader behind this page was routed
    #: here by the measured second-array displacement. **A SEPARATE FIELD, never an overload of**
    #: :attr:`depth_source`: *"what depth this page is read at"* and *"which reader, at which
    #: address"* are two kinds of fact, and this lane's whole posture is that collapsing two kinds of
    #: fact is how a tool starts lying. ``"bound"`` on every page from a caller that did not consult
    #: ``"so-displaced"``, so the field cannot claim a channel nobody asked for.
    readership: str = "bound"

    @property
    def wh(self) -> Tuple[int, int]:
        return (self.w, self.h)

    @property
    def depth_inherited(self) -> bool:
        """The depth is a property of the COLUMN, not of anything that names this cell -- true for
        every ``so-page`` and ``program`` cell. **No instrument has seen a model sample these bytes**;
        what is established is the mode under which the page they live in is read.

        ⚠ **NOT the "lower half" predicate, and one reviewer has already read it as one.** This asks
        *which kind of fact the depth is*; whether the depth also crossed a CELL BOUNDARY to reach
        this cell is ``cell[1] % PAGE_LINES``
        (:attr:`ff9mapkit.summons.depth_attribution.ProgramDepth.inherited`), and that is the one
        :func:`_scenery_disclosures` gates its inheritance clause on. They differ on every UPPER half
        of an attributed column.
        """
        return self.depth_source in ("so-page", "so-array", "program")

    @property
    def scenery(self) -> bool:
        return self.kind == "scenery"

    @property
    def direct(self) -> bool:
        """15bpp DIRECT colour -- the texels ARE the colour and index no palette."""
        return self.bpp == 15

    @property
    def depth_ambiguous(self) -> bool:
        """SAME-BYTES-TWO-DEPTHS: more than one ``so`` reader states a DIFFERENT depth for this one
        byte block. ``bpp`` is then the lowest of them and is NOT a fact -- 17 corpus cells over 6
        effects are in this class and no single index array exists for any of them."""
        return bool(self.hazards) and len(self.hazards.depths) > 1


def creature_texel_pages(blob: bytes) -> List[TexelPage]:
    """Every creature page of one container, or ``[]`` when it carries no decodable creature package.

    Consumes :func:`ff9mapkit.summons.texture.texture_check` rather than re-deriving the layout: the
    ``partCount * 0x4000`` / ``clutRows * 0x200`` / 8bpp laws are corpus-proven there, and a second
    implementation of them here would be a second thing to keep true.
    """
    mp = EC.creature_package(blob)
    if mp is None:
        return []
    chk = KT.texture_check(blob, mp)
    if not chk["decodable"]:
        return []
    out: List[TexelPage] = []
    for p in chk["parts"]:
        out.append(TexelPage(
            name="tex.part%d" % p.index, index=p.index, page_offset=p.page_offset,
            page_bytes=KT.PAGE_BYTES, w=KT.PAGE_W, h=KT.PAGE_H, bpp=8,
            clut_offset=p.clut_offset, clut_entries=KT.PALETTE_LEN, tpage=p.tpage, clut=p.clut,
            v_offset=p.v_offset, vram=p.vram, palette_name="creature.part%d" % p.index))
    return out


def creature_refusal(blob: bytes) -> str:
    """Why this container has no addressable creature page, in the author's terms (``""`` if it has)."""
    mp = EC.creature_package(blob)
    if mp is None:
        return ("this container declares no id-4 + id-5 creature package (348 of the corpus's 372 do "
                "not) -- there is no creature page to repaint.  %s" % W6B_REASON)
    chk = KT.texture_check(blob, mp)
    if not chk["decodable"]:
        return ("this container's creature texture block is not the 8bpp 128x128 page layout:\n  - "
                + "\n  - ".join(chk["reasons"]) + "\n  %s" % W6B_REASON)
    return ""


# --------------------------------------------------------- W6b-1: THE PROGRAM-VRAM CONSTANTS
#: Effects whose own id-3 PROGRAM writes VRAM, so a static texel edit there can be a LOST EDIT --
#: **15 ids, 175 scenery cells**. The one place this module carries a corpus list rather than a
#: derivation, and it is carried because the derivation is a MIPS reachability walk over 385 program
#: images (tier-r's const-folding ``ImageWalker``), which is not something a build can afford to
#: re-run per target. It is therefore RE-DERIVATION-PINNED: the study's ``w6b_gates`` re-walks the
#: corpus and compares this exact set, so the constant is a cache of a measurement, never a claim.
#:
#: THE DIRECTION LAW is what makes it 15 and not 22 (PSX libgpu, corroborated by the DLL's own stub
#: arities): ``LoadImage(RECT*, u_long*)`` is main RAM -> VRAM, a **write**; ``MoveImage(RECT*, x, y)``
#: is VRAM -> VRAM, a **write**; ``StoreImage(RECT*, u_long*)`` is VRAM -> main RAM, a **READ**, and a
#: read cannot clobber a repaint. Four corrections carried here against the pre-W6b record:
#:
#: * ``LoadImage u MoveImage u seq-op-0x07`` unions to 15 ids -- but one of them, **ef435, is a FALSE
#:   POSITIVE and comes OFF**: its ``@0x2dd8`` is a switch dispatch through the image's own pointer
#:   table (``lw $v0, 0($v0)`` with no ``base=*(+0x10)`` sentinel chain), and the walker read offset 0
#:   as HLE op 0. That matters beyond this lane -- ef435 is creature-bearing;
#: * the writer union is therefore **14**, and the 15th id here is **ef038**, whose ``HLE op 12``
#:   texanim arm is a genuine program VRAM write (and already an unconditional W6a/W7 refusal). The
#:   census's own ``hz_program_write`` flag is exactly this union: 14 writers + ef038;
#: * six containers join as **READ-only** -- see :data:`PROGRAM_VRAM_READ_IDS`;
#: * ``0 of 18 RECT*`` arguments const-fold, so the only PER-CELL verdict in the corpus is
#:   :data:`MOVEIMAGE_HARD_CELLS`.
PROGRAM_VRAM_WRITE_IDS = frozenset((1, 38, 87, 125, 134, 142, 143, 144, 149, 223, 224, 274, 308,
                                    381, 415))

#: Effects whose program touches VRAM only through ``StoreImage`` -- **12 ids, 113 scenery cells**.
#: A READ. It cannot overwrite a repainted cell, so these DISCLOSE rather than refuse, and that single
#: direction correction is what moves 113 cells out of the refusal set and makes **ef211** -- the
#: Phoenix fire field, whose upload path is already cast-proven -- reachable at all.
#: ef151/152/225/445/460/510 are the six the reachability walk never reached (mean reachability 0.905)
#: and a byte-level shape scan found; ef225@0x57c, ef151@0x584 and ef211@0x584 are byte-identical
#: ``StoreImage(&rect_on_stack, buf)`` boilerplate.
PROGRAM_VRAM_READ_IDS = frozenset((7, 72, 151, 152, 211, 214, 225, 276, 390, 445, 460, 510))

#: The **only per-cell program verdict in the corpus**: ``MoveImage``'s destination const-folds to
#: ``$a1 = 704, $a2 = 256`` on 3 of its 5 sites, and all three containers declare that cell. A static
#: repaint of it is overwritten at run time -- a lost edit with no symptom -- so it is a HARD refusal
#: BY CELL while every other cell in those three containers is untouched by the program.
MOVEIMAGE_HARD_CELLS: Dict[int, Tuple[int, int]] = {1: (704, 256), 142: (704, 256),
                                                    144: (704, 256)}


def program_class(effect: Optional[int]) -> Tuple[str, str]:
    """``(class, evidence)`` for one effect's program -- ``"write"`` / ``"read"`` / ``"clean"``, or
    ``"unknown"`` when no effect id was supplied.

    ``"unknown"`` is NOT a synonym for clean and any gate reading it must treat it as ``"write"``: the
    lists are keyed by effect id, so a derivation handed bare bytes with no id genuinely does not know,
    and reading silence as safety is how a refusal becomes a comment.
    """
    if effect is None:
        return ("unknown", "no effect id was supplied with these bytes, so the program-VRAM lists "
                           "(which are keyed by effect id) could not be consulted at all")
    ef = int(effect)
    if ef in PROGRAM_VRAM_WRITE_IDS:
        return ("write", "ef%03d is one of the %d containers whose id-3 program WRITES VRAM "
                         "(LoadImage / MoveImage / loader op 0x07 / the texanim arm)"
                % (ef, len(PROGRAM_VRAM_WRITE_IDS)))
    if ef in PROGRAM_VRAM_READ_IDS:
        return ("read", "ef%03d's program touches VRAM only through StoreImage (VRAM -> main RAM: a "
                        "READ -- it cannot clobber a repaint).  DISCLOSE, do not refuse." % ef)
    return ("clean", "ef%03d declares no VRAM-transfer call site and no loader op 0x07" % ef)


# --------------------------------------------------------- W6b-1: THE BOUND MODELS + THEIR UV COVER
#: one VRAM page-cell is 128 lines tall -- ``reskin``'s own constant, imported rather than re-typed.
CELL_LINES = RS.PAGE_CELL_LINES


def cell_texel_w(bpp: int, w_halfwords: int = RS.PAGE_CELL_W) -> int:
    """A page-cell's width in TEXELS at one depth. 256 / 128 / 64 at 4 / 8 / 15 bpp -- the same
    ``0x4000`` bytes read three ways, which is precisely why the depth may never be guessed."""
    if bpp not in KT.TEXELS_PER_HW:
        raise RepaintError("unknown texel depth %r -- the `so` record states 4, 8 or 15" % (bpp,))
    return w_halfwords * KT.TEXELS_PER_HW[bpp]


@dataclass
class BoundModel:
    """One ``so``-bound NON-creature model, with its UV cover resolved to VRAM cells.

    The join the whole scenery lane rests on: an ``so`` record states a model's TPAGE (hence its
    column and its DEPTH) and its CLUT word (hence its palette), and the model's own UV pool states
    which halfwords it actually samples. Depth is read off the record, never inferred from the pixels
    -- the coherence probe built to guess it was FALSIFIED at 54.5% on a 3-way choice.
    """
    geom: int
    slot: int
    tpage: int
    bpp: int
    clut_word: int
    clut_cell: Optional[Tuple[int, int]]
    clut_entries: int
    page: Tuple[int, int]                 # the tpage's own VRAM origin (x halfwords, y lines)
    faces: int = 0
    u: Tuple[int, int] = (0, 0)
    v: Tuple[int, int] = (0, 0)
    #: ``{(cell x, cell y): frozenset of ABSOLUTE VRAM halfword x}`` -- the UV-exact cover.
    cover: Dict[Tuple[int, int], Set[int]] = field(default_factory=dict)
    #: W6b-3 (iii): this binding's own SECOND-ARRAY pair, or ``None`` where the record's arity makes
    #: the pairing an ORDER claim. ⚠ **It comes off :attr:`ff9mapkit.summons.reskin.Binding.mover`
    #: and MUST NOT be indexed off any ``slot``** -- :attr:`slot` here is the container CHUNK slot,
    #: not the array index, and keying the pair off it silently drops readers (measured: ef381
    #: ``x384_y384``, chunk slot 3, ``P == 1``). PURELY INFORMATIONAL: nothing in the cover, the
    #: depth, the page or an emitted byte reads it.
    mover: Optional[Tuple[int, int]] = None
    #: the ``so`` record's own file offset -- **IDENTIFICATION ONLY**, carried off
    #: :attr:`ff9mapkit.summons.reskin.Binding.record_at` rather than re-derived as ``geom - 0x10``,
    #: because a disclosure that recomputes its own evidence's address is one arithmetic change away
    #: from naming the wrong bytes.
    record_at: int = -1

    #: W6b-3 (iv): where the hardware actually SAMPLES -- :attr:`cover` with this binding's own
    #: measured ``(du, dv)`` applied (:func:`sampled_halfword`). **It IS :attr:`cover`, the same
    #: object, on every binding whose :attr:`mover` is absent or zero**, which is 189 of the corpus's
    #: 340 incumbent readers -- so the undisplaced path is provably untouched rather than
    #: coincidentally equal, and the cost of the second rasterisation is proportional to the movers.
    effective_cover: Dict[Tuple[int, int], Set[int]] = field(default_factory=dict)

    @property
    def columns(self) -> Tuple[int, ...]:
        """The BOUND columns -- what the record says, ORDER-FREE OF THE DISPLACEMENT.

        ⚠ **Deliberately not re-aimed by W6b-3 (iv).** ``w6b_gates`` G6 pins ``spill_bindings 58``
        and the u-spill census off this property and off :attr:`spills`; the READERSHIP question is
        answered by :attr:`effective_columns` beside it. *Readership is EFFECTIVE; the record's own
        statement is BOUND, and a name that answers both answers neither.*
        """
        return tuple(sorted({cx for cx, _cy in self.cover}))

    @property
    def spills(self) -> bool:
        """The picture is wider than one page. 58 corpus bindings do this (41 at 8bpp, 17 at 15bpp,
        **0 at 4bpp** -- structurally: ``u <= 255`` at 4 texels/halfword is offset <= 63), and **0 of
        58** spill by <= 2%, so there is no marginal case to wave through."""
        return len(self.columns) > 1

    @property
    def effective_columns(self) -> Tuple[int, ...]:
        """The columns this binding's readers SAMPLE -- :attr:`columns` under the displacement."""
        return tuple(sorted({cx for cx, _cy in self.effective_cover}))

    @property
    def effective_spills(self) -> bool:
        """:attr:`spills`, asked of the EFFECTIVE cover -- what the NAME-EVERY-COLUMN obligation is
        owed against, because that gate is about which cells an author must supply art for."""
        return len(self.effective_columns) > 1

    @property
    def displaced(self) -> bool:
        """This binding carries a NON-ZERO measured displacement, so its two covers can differ."""
        return bool(self.mover) and bool(self.mover[0] or self.mover[1])


#: ★ THE ADOPTED MODEL'S NAME, stamped on every artifact this rung emits so a future measurement can
#: say WHICH arithmetic a manifest, a scaffold or a ledger row was written under. One name, not a
#: registry: exactly one model is settled, and a dispatch table with one entry is machinery
#: pretending to be evidence.
DISPLACEMENT_MODEL = "linear-add-v1"


def sampled_halfword(page: Tuple[int, int], u: int, v: int, per: int,
                     disp: Tuple[int, int] = (0, 0)) -> Tuple[int, int]:
    """★ **THE SEAM: the ABSOLUTE VRAM halfword a stored ``(u, v)`` actually SAMPLES.**

    ``effective = stored + halfword``, per axis, independently, LINEAR -- pair position 0 onto ``u``
    (TEXELS, converted to halfwords by this page's own ``per``) and pair position 1 onto ``v`` (VRAM
    LINES, depth-free). Every other effective-cell answer in this kit comes through here or through
    :func:`effective_cell`, which wraps it.

    **THE MEASUREMENT, ITS CONFIDENCE, ITS CONTAINERS AND ITS LIMITS**

    * WHAT: the ``so`` record's SECOND array (``P x (u16, u16)`` at ``arrayB = 8 + 4P``) is a PER-SLOT
      TEXEL DISPLACEMENT baked into the primitive stream the renderer submits, ABSENT from the
      container's stored UV pool.
    * CONFIDENCE / CONTAINERS: **0.97 on ef038** (the s77 UVR instrument -- per-mesh min/max of the
      primitives' OWN ``u, v`` bytes, joined one-to-one to the textured draw), all four cells of the
      ``(position 0, position 1)`` square on four disjoint reader populations, ZERO residue. Then
      GENERALISED on **ef227** (key ISOLATED, tri ratio 1.00, control gate PASS) and **ef446**
      (control gate PASS), with ef038 reproducing in the same log. Three containers, four casts.
    * THE OPERATION IS **ADDITION**, and the test was decisive rather than suggestive: ef227's answer
      slot has the raw pool ``{0, 25, 55, 85, 111}`` and the observed per-frame extremes were
      ``{16, 41, 101, 127}``. 41 and 101 are 25 and 85 PLUS 16. OR would read 25 and 85; XOR 9 and
      69; a FLAG reading predicts ``u`` in ``[128, 239]`` against an observed ``[16, 127]``, DISJOINT.
      ADD is the only surviving operation, refuted independently on ef227 and ef446.
    * LIMIT 1 -- **THE REACH IS THE INCUMBENT RECORDS ONLY.** ``Binding.mover`` returns ``None`` on a
      ``P >= 2`` record, so nothing here pairs array entry *k* with binding slot *k* and
      ``ORDER_UNMEASURED`` is untouched. 142 of the corpus's 309 novel slots carry a non-zero pair
      and NONE of them is modelled: the effective cover is a **LOWER BOUND** on readership, which is
      why no string in this lane may say *"nothing reads this cell"*.
    * LIMIT 2 -- **LINEAR vs mod-256 WRAP is DEGENERATE HERE, and the reason is structural, not
      statistical.** See :func:`assert_intra_page`: a tpage is cell-aligned, stored ``u, v <= 255``,
      and ``max(u) + du <= 255`` / ``max(v) + dv <= 255`` on **340 of 340** incumbent readers -- so
      the displacement moves a reader between cells of ITS OWN PAGE and never reaches the byte
      boundary. Linear and wrapping agree on every reader this kit can reach; the kit implements
      linear addition and does not have to choose.
    * LIMIT 3 -- **ARRAY-vs-BINDING is still open at P == 1.** No cast separates *"the array VALUE
      displaces"* from *"the BINDING selects a displaced source window and the array labels it"*.
      Both readings predict the SAME effective cell for every incumbent reader in the corpus, so the
      arithmetic is unaffected -- but every string this kit prints says *a reader carrying this pair
      samples at +V*, never *the halfword causes the displacement*.
    * LIMIT 4 -- **BINDING-IS-NOT-A-DRAW is unchanged.** Deriving that a reader samples a cell makes
      that cell DERIVABLE, never PROVEN VISIBLE.
    """
    return (page[0] + (u + disp[0]) // per, page[1] + v + disp[1])


def effective_cell(page: Tuple[int, int], u: int, v: int, bpp: int,
                   disp: Tuple[int, int] = (0, 0)) -> Tuple[int, int]:
    """The VRAM page-cell a reader's stored ``(u, v)`` SAMPLES -- :func:`sampled_halfword`, bucketed.

    ``per`` is re-derived from :data:`ff9mapkit.summons.texture.TEXELS_PER_HW` and
    :data:`ff9mapkit.summons.reskin.PAGE_CELL_W` rather than typed, because G1 (THE PAGE-SPAN GATE)
    is depth-dependent: ``+128`` texels is HALF a 4bpp cell, EXACTLY ONE 8bpp cell and TWO at 15bpp.
    """
    hx, vy = sampled_halfword(page, u, v, KT.TEXELS_PER_HW[bpp], disp)
    return ((hx // RS.PAGE_CELL_W) * RS.PAGE_CELL_W, (vy // CELL_LINES) * CELL_LINES)


def assert_intra_page(m: BoundModel) -> None:
    """★ **THE INTRA-PAGE LAW, ENFORCED AT THE CALL SITE** -- a displaced reader never leaves its page.

    A tpage origin is cell-aligned (``x`` a multiple of 64 halfwords, ``y`` in ``{0, 256}``) and
    stored ``u, v`` are BYTES, so one tpage spans ``{4bpp: 1, 8bpp: 2, 15bpp: 4}`` cells wide by
    exactly 2 stacked cells tall. Measured over all 372 containers: ``max(u) + du <= 255`` and
    ``max(v) + dv <= 255`` on **340 of 340** incumbent readers, and every effective cell lies inside
    the reader's own tpage span.

    That is what makes three separate claims safe rather than hopeful -- LINEAR and WRAPPING agree
    (nothing reaches the byte boundary), an arriving reader's DEPTH is its own tpage's depth applied
    to an address INSIDE that tpage (no extrapolation), and no displaced read can land off VRAM.

    So it is checked, not asserted in prose: *a law in a docstring is a wish.* It fails CLOSED --
    a container that breaks it refuses outright rather than being silently mis-attributed, because
    the day this fires is the day the linear model is wrong and every verdict downstream is void.

    ★ **AND THE CALL SITE IS THE SCOPE THAT CONSULTED THE CHANNEL, NOT THE RASTERISER.** It is spent
    in :func:`effective_cell_readers` -- the one function that turns effective covers into a
    readership answer -- and therefore only on a path that named ``so-displaced``. Firing it inside
    :func:`bound_models`, which every scope walks, gave a broken container a way to refuse under
    :data:`CENSUS_CHANNELS` and :data:`LICENSED_CHANNELS`: two frozen surfaces that never read
    :attr:`BoundModel.effective_cover`, sharing a failure mode with a channel they decline. *A
    channel a caller declined to consult must not appear to have spoken* -- and that includes
    speaking by raising.
    """
    if not m.displaced:
        return
    du, dv = m.mover
    # G1, THE PAGE-SPAN GATE, re-derived rather than typed: one cell holds `PAGE_CELL_W * per`
    # texels, and stored `u` is a BYTE, so a tpage spans `256 // (64 * per)` cells -- 1 / 2 / 4 at
    # 4 / 8 / 15 bpp -- by exactly 2 stacked cells (256 lines / 128).
    wide = 256 // (RS.PAGE_CELL_W * KT.TEXELS_PER_HW[m.bpp])
    span = {(m.page[0] + RS.PAGE_CELL_W * i, m.page[1] + CELL_LINES * j)
            for i in range(wide) for j in range(2)}
    out = sorted(c for c in m.effective_cover if c not in span)
    if m.u[1] + du > 255 or m.v[1] + dv > 255 or out:
        raise RepaintError(
            "THE INTRA-PAGE LAW IS BROKEN on GEOM %#x (record %#x): its stored span is u %d..%d / "
            "v %d..%d, its measured displacement is (%d, %d), and the effective read %s.  Every one "
            "of the 340 incumbent readers in the reference corpus satisfies `max(u) + du <= 255` "
            "and `max(v) + dv <= 255` and lands inside its own tpage's %d-cell span, which is what "
            "makes the LINEAR reading and a mod-256 WRAPPING one indistinguishable and what makes "
            "an arriving reader's depth its own tpage's depth rather than an extrapolation.  A "
            "container that breaks it refuses here rather than being attributed under a model this "
            "kit has no evidence for.  MODEL: %s."
            % (m.geom, m.record_at, m.u[0], m.u[1], m.v[0], m.v[1], du, dv,
               ("leaves that page at cell(s) %s" % ", ".join("x%d_y%d" % c for c in out)) if out
               else "reaches the byte boundary", len(span), DISPLACEMENT_MODEL))


def _cover_mark(m: BoundModel, u: int, v: int, per: int, disp: Tuple[int, int] = (0, 0)) -> None:
    """Mark one sampled texel in ABSOLUTE VRAM space, bucketed by page-cell.

    The stored value is the halfword's index WITHIN its cell (``line * 64 + x``, 0..8191), not its
    column: the column is the cell key already, and what the coverage number has to answer is *how
    much of this 0x4000 block is live art* -- ef211's fire field is 8,128 of 8,192, which is why it
    reads as a full-screen picture rather than a corner of one.

    ``disp`` defaults to the IDENTITY, so the BOUND cover is the same derivation it always was and
    the displaced one is the same derivation with the measured term -- one rasteriser, two answers.
    """
    hx, vy = sampled_halfword(m.page, u, v, per, disp)
    cell = ((hx // RS.PAGE_CELL_W) * RS.PAGE_CELL_W, (vy // CELL_LINES) * CELL_LINES)
    tgt = m.cover if disp == (0, 0) else m.effective_cover
    tgt.setdefault(cell, set()).add((vy - cell[1]) * RS.PAGE_CELL_W + (hx - cell[0]))


def _cover_tri(m: BoundModel, tri, per: int, disp: Tuple[int, int] = (0, 0)) -> None:
    (x0, y0), (x1, y1), (x2, y2) = [(p[0] + 0.5, p[1] + 0.5) for p in tri]
    d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if d == 0:
        return
    for py in range(int(min(y0, y1, y2)), int(max(y0, y1, y2)) + 1):
        cy = py + 0.5
        for px in range(int(min(x0, x1, x2)), int(max(x0, x1, x2)) + 1):
            cx = px + 0.5
            a = ((y1 - y2) * (cx - x2) + (x2 - x1) * (cy - y2)) / d
            bb = ((y2 - y0) * (cx - x2) + (x0 - x2) * (cy - y2)) / d
            if a >= -1e-9 and bb >= -1e-9 and (1.0 - a - bb) >= -1e-9:
                if 0 <= px < 256 and 0 <= py < 256:
                    _cover_mark(m, px, py, per, disp)


def bound_models(blob: bytes) -> List[BoundModel]:
    """Every ``so``-bound non-creature model, 15bpp DIRECT binders INCLUDED, with its UV cover.

    ``reskin.attribution(include_direct=True)`` supplies the bindings -- the parameter B1 added for
    exactly this, because the texel lane needs two things a palette lane never asks about: a cell's
    DEPTH (15bpp is a depth the container STATES, and dropping the binder makes that cell read as
    depth-unknown) and the u-spill census (17 of the 58 spilling bindings are 15bpp, where one
    halfword is one texel and the reach is up to three columns).

    The rasteriser is the same one :func:`coverage_mask` uses on creature pages -- centre-sampled
    polygon fill with the CORNERS OR-ed in, because a one-texel-thin face has no centre inside it at
    all -- lifted into ABSOLUTE VRAM halfword space so a cover can cross a column boundary, which is
    the whole point.

    ★ **W6b-3: THE CENSUS LANE IS INCUMBENT-ONLY, AND IT TAKES NO PARAMETER.** ``bound_models`` is
    the population ``w6b_gates`` G6, ``w6q_gates`` G1/G16 and ``w6b2i_gates`` I5 are written ABOUT,
    and ``so-uv`` LICENSES -- it emits a paintable page with no acknowledgement anywhere on the path.
    A rung that silently re-aimed it would have moved the thing those gates measure while every one
    of them still read green on a different population.

    And there is **no order-free way to make it correct otherwise**: rasterising a multi-part model's
    cover means routing each FACE to its part's array entry through the primitive ``part`` byte --
    precisely the ORDER clause nothing has measured -- and 82 of the 126 multi-part records name more
    than one distinct tpage, so an arbitrary pick mis-attributes the majority of them. A parameter
    with no correct second consumer is speculative generality; what the law needs is the ASSERTION
    below, at the call site, because *a law not enforced at the call site is not enforced.*

    ★★ **W6b-3 (iv): TWO COVERS, ONE WALK, AND THE INCUMBENT-ONLY REACH IS UNCHANGED.** Each model
    now carries :attr:`BoundModel.cover` (what the record BINDS -- the population every gate board
    above is written about, moved by nothing in this rung) and :attr:`BoundModel.effective_cover`
    (what the hardware SAMPLES, :func:`sampled_halfword`). They are the SAME OBJECT wherever
    :attr:`BoundModel.mover` is absent or zero, so the undisplaced path is untouched by construction
    rather than by inspection. ``Binding.mover`` still returns ``None`` on a ``P >= 2`` record, so
    the reach is EXACTLY the 340 incumbent readers / 151 movers and ``ORDER_UNMEASURED`` is
    untouched.

    ⚠ **AND THE RASTERISER DOES NOT ENFORCE THE INTRA-PAGE LAW -- :func:`effective_cell_readers`
    DOES.** This function is walked by every scope, including the two FROZEN ones that never read
    :attr:`BoundModel.effective_cover` at all, so asserting here would give a container that breaks
    the law a way to fail the CENSUS and LICENSED surfaces -- surfaces whose whole claim is that
    this rung cannot move them. On the stock 372 the assertion never fires either way (the law holds
    340/340), which is exactly why the leak was invisible: it made "the frozen surfaces are unmoved"
    a CORPUS FACT rather than a STRUCTURAL PROPERTY. The law is checked where the displacement is
    SPENT; see :func:`assert_intra_page` and :func:`effective_cell_readers`.
    """
    mp = EC.creature_package(blob)
    creature_geom = mp.geom_offset if mp is not None else None
    attrib = RS.attribution(blob, include_direct=True, witness=RS.WITNESS_INCUMBENT)
    by_geom = {b.geom: b for b in attrib.bindings}
    if len(by_geom) != len(attrib.bindings):                     # pragma: no cover - by construction
        raise RepaintError(
            "the incumbent `so` bindings are not 1:1 with GEOM blocks (%d bindings over %d blocks) --"
            " `by_geom` would silently keep the LAST one and drop the rest.  Under"
            " `witness=WITNESS_INCUMBENT` every record has P <= 1, so this cannot happen unless the"
            " witness narrowing above was removed or the reader changed shape."
            % (len(attrib.bindings), len(by_geom)))
    out: List[BoundModel] = []
    for g in EC.scan_geom(blob):
        if creature_geom is not None and g.base == creature_geom:
            continue
        b = by_geom.get(g.base)
        if b is None:
            continue
        m = BoundModel(geom=b.geom, slot=b.chunk_slot, tpage=b.tpage, bpp=b.bpp,
                       clut_word=b.clut_word,
                       clut_cell=(None if b.direct else b.cell), clut_entries=b.entries,
                       # ⚠ OFF `Binding.mover`, NEVER off a slot index -- `slot` above is
                       # `b.chunk_slot`, the CONTAINER CHUNK slot, and `second_pairs[m.slot]` is a
                       # different (and wrong) quantity that drops readers on chunk slots >= 1.
                       page=b.page, mover=b.mover, record_at=b.record_at)
        per = KT.TEXELS_PER_HW[b.bpp]
        # THE MEASURED TERM, taken ONCE per binding off the accessor that enforces the ORDER law.
        disp = m.mover if m.displaced else (0, 0)
        umin = vmin = 1 << 30
        umax = vmax = -1
        for mesh in g.meshes:
            pool = g.base + mesh.p_uv
            for prim in EC.iter_primitives(blob, g, mesh):
                uvs = prim.get("uv")
                if not uvs:
                    continue
                m.faces += 1
                pts = []
                for ui in uvs:
                    word = struct.unpack_from("<H", blob, pool + 2 * ui)[0]
                    u, v = word & 0xFF, (word >> 8) & 0xFF
                    umin, umax = min(umin, u), max(umax, u)
                    vmin, vmax = min(vmin, v), max(vmax, v)
                    pts.append((u, v))
                for t in _face_polys(pts):
                    _cover_tri(m, t, per)
                    if disp != (0, 0):
                        _cover_tri(m, t, per, disp)
                for (u, v) in pts:
                    _cover_mark(m, u, v, per)
                    if disp != (0, 0):
                        _cover_mark(m, u, v, per, disp)
        if m.faces:
            m.u, m.v = (umin, umax), (vmin, vmax)
        # ★ THE IDENTITY, NOT A COPY: on a binding with no measured displacement the two covers are
        # the SAME OBJECT, so "the displacement changed nothing here" is a fact about object identity
        # a gate can assert, not a set comparison that could pass for the wrong reason.
        if disp == (0, 0):
            m.effective_cover = m.cover
        out.append(m)
    return out


def novel_displacement_reach(blob: bytes) -> Tuple[int, int]:
    """``(novel records, novel slots carrying a NON-ZERO pair)`` -- **WHAT THIS KIT CANNOT MODEL.**

    Carried so that no string in this lane can say *"nothing reads this cell"* when what it means is
    *"no reader this kit can attribute samples here"*. :attr:`ff9mapkit.summons.reskin.Binding.mover`
    refuses to answer on a ``P >= 2`` record (``ORDER_UNMEASURED``), so a displacement on one of those
    slots is invisible to every predicate in this lane -- 142 of the corpus's 309 novel slots carry
    one. A silence that cannot tell ignorance from safety is the defect ``program-vram-unknown`` was
    minted to fix, and this is the number that lets the disclosure say which it is.
    """
    mp = EC.creature_package(blob)
    creature_geom = mp.geom_offset if mp is not None else None
    recs = pairs = 0
    for g in EC.scan_geom(blob):
        if creature_geom is not None and g.base == creature_geom:
            continue
        rec = RS.so_record(blob, g.base)
        if rec is None or rec["witness"] != RS.WITNESS_NOVEL:
            continue
        recs += 1
        pairs += sum(1 for (a, b) in rec["second"] if a or b)
    return recs, pairs


def cell_readers(blob: bytes, models: Optional[Sequence[BoundModel]] = None
                 ) -> Dict[Tuple[int, int], List[BoundModel]]:
    """``{VRAM cell: [BoundModel]}`` -- which models actually SAMPLE each cell.

    By UV COVER, never by tpage: a model whose picture is wider than its page reads a neighbouring
    column it never declares, and a tpage-keyed join would miss all 58 of them -- 6 of which spill
    into a column with a DIFFERENT writer set and 10 into a column nothing uploads at all.
    """
    models = bound_models(blob) if models is None else models
    out: Dict[Tuple[int, int], List[BoundModel]] = {}
    for m in models:
        for cell in m.cover:
            out.setdefault(cell, []).append(m)
    for v in out.values():
        v.sort(key=lambda m: m.geom)
    return out


def effective_cell_readers(blob: bytes, models: Optional[Sequence[BoundModel]] = None
                           ) -> Dict[Tuple[int, int], List[BoundModel]]:
    """``{VRAM cell: [BoundModel]}`` -- which models SAMPLE each cell, **under the measured
    displacement**. The W6b-3 (iv) twin of :func:`cell_readers`, same shape and same GEOM sort.

    ⚠ **It is a SECOND function, not a parameter on the first, and that is load-bearing.**
    :func:`cell_readers` is what ``w6b3i_gates`` I10 (THE CENSUS FREEZE) and I4 compare against a
    frozen snapshot, and every gate board under ``studies/`` calls it by its shipped signature -- so
    re-aiming it in place, or giving it a required keyword, would move what four other boards measure
    while every one of them still read green (or TypeError'd) on a different population. The join an
    author walks is switched BY NAME at exactly one line of :func:`scenery_surface`.

    Corpus-measured over 372 containers: 187 declared cells have at least one BOUND reader and 212
    have at least one EFFECTIVE one -- 45 of the 187 lose every reader they had, 7 more are read only
    by an arriving FOREIGN reader, and 70 declared cells acquire a reader they do not bind.

    ★ **AND THIS IS WHERE THE INTRA-PAGE LAW IS CHECKED, BECAUSE THIS IS WHERE THE DISPLACEMENT IS
    SPENT.** :func:`assert_intra_page` used to fire inside :func:`bound_models`, which rasterises
    both covers for every caller -- so a container that broke the law refused under
    :data:`CENSUS_CHANNELS` and :data:`LICENSED_CHANNELS` too, two scopes that never consult
    ``so-displaced`` and never read :attr:`BoundModel.effective_cover`. That made "the census
    surface is unmoved" a fact about the STOCK 372 (where the law holds 340/340 and the assertion
    never fires) rather than a structural property of the code, which is the weaker of the two
    claims and not the one the rung makes. The law now fires exactly where a caller has ASKED for
    the effective join -- here, and at the one line of :func:`scenery_surface` that names this
    function -- so a broken container refuses on the edit surface and the two frozen scopes keep
    the failure modes they shipped with. It still fails CLOSED, and it is still checked at a CALL
    SITE rather than asserted in prose: *a law in a docstring is a wish.*
    """
    models = bound_models(blob) if models is None else models
    out: Dict[Tuple[int, int], List[BoundModel]] = {}
    for m in models:
        # ⚠ ON THE MODELS THIS CALLER HANDED IN, never on a re-derivation -- a gate board that builds
        # its own `bound_models` and passes them here must be held to the same law as one that does
        # not, or the enforcement would be skippable by an argument.
        if m.displaced:
            assert_intra_page(m)
        for cell in m.effective_cover:
            out.setdefault(cell, []).append(m)
    for v in out.values():
        v.sort(key=lambda m: m.geom)
    return out


# --------------------------------------------------------- W6b-1: THE HAZARD RECORD (data, not gates)
@dataclass(frozen=True)
class CellWriter:
    """One uploader of one VRAM cell. Two or more of these on one cell IS the co-transform hazard --
    34 corpus cells in 5 containers, **0 of 156 writer pairs byte-identical**."""
    tag: str
    chunk: str
    slot: int
    kind: str                    # "id0" | "id9"
    off: int
    nbytes: int
    provenance: str


@dataclass(frozen=True)
class CellReader:
    """One model that SAMPLES this cell, and everything the container states about how."""
    geom: int
    slot: int
    tpage: int
    bpp: int
    clut_word: int
    clut_cell: Optional[Tuple[int, int]]
    clut_entries: int
    #: every id-0 upload of that CLUT cell, lowest file offset first. A LIST because a CLUT cell can
    #: itself be multi-writer, so "the palette" is only well defined per upload.
    palettes: Tuple[str, ...]
    palette_offset: Optional[int]
    faces: int
    u: Tuple[int, int]
    v: Tuple[int, int]
    halfwords_here: int          # how much of THIS cell it samples
    columns: Tuple[int, ...]     # every VRAM column its UVs reach -- the NAME-EVERY-COLUMN set
    own_column: bool             # its tpage's own column IS this cell's (False => it spills in here)
    #: W6b-3 (iii): this reader's SECOND-ARRAY pair, ``(0, 0)`` for *"no mover"*. Since W6b-3 (iv)
    #: it is APPLIED (:func:`sampled_halfword`) as well as counted, on the licensed edit surface.
    mover: Tuple[int, int] = (0, 0)
    #: the ``so`` record's own file offset -- IDENTIFICATION ONLY, so a displacement refusal can name
    #: the bytes its verdict came out of rather than making the author re-derive the address.
    record_at: int = -1
    #: the reader's own tpage VRAM origin ``(x halfwords, y line)`` -- BOUND, identification.
    page: Tuple[int, int] = (0, 0)
    #: the columns this reader's tpage BINDS, beside :attr:`columns`, which is what it SAMPLES. They
    #: differ on exactly the 151 corpus movers, and a disclosure that could only print one of them
    #: could not say *"GEOM X binds column 640; it samples cell.s0.x704_y384"*.
    bound_columns: Tuple[int, ...] = ()
    #: every cell this reader SAMPLES under the adopted displacement, so a refusal on the cell it
    #: LEFT can say where it went. Empty wherever ``"so-displaced"`` was not consulted.
    effective_cells: Tuple[Tuple[int, int], ...] = ()

    @property
    def palette_name(self) -> str:
        return self.palettes[0] if self.palettes else ""

    @property
    def displaced(self) -> bool:
        """This reader carries a NON-ZERO measured displacement."""
        return bool(self.mover[0] or self.mover[1])


@dataclass(frozen=True)
class SecondArrayRead:
    """One reader's NON-ZERO second-array pair and BOTH candidate effective columns.

    **PURELY INFORMATIONAL.** Nothing in this record feeds a depth, a cover, a page or a byte; the
    only predicate that reads it is :attr:`CellHazards.every_reader_moves`, which counts entries and
    never interprets one. U1's s77 read settled the labelling -- :attr:`a`, at pair position 0, is
    the one that displaces ``u`` (:data:`ff9mapkit.summons.depth_attribution.U_DISPLACEMENT_CAVEAT`)
    -- so :attr:`swapped_columns` is the MEASURED reading and :attr:`original_columns` is RETAINED,
    not preferred: it is the retired hypothesis's arithmetic, kept visible so a reader who met this
    disclosure before the cast can still reconcile what they were shown. Neither feeds a byte, so
    keeping the retired column costs nothing and dropping it would cost an audit trail.

    ⚠ :attr:`swapped_columns` / :attr:`original_columns` are a **SPAN**, derived from the reader's
    stored ``u`` RANGE rather than from a re-rasterised displaced cover -- because putting a
    displacement term into :func:`_cover_mark` would re-aim the whole census, which is a different
    (and larger) decision. Measured: the span equals the fully rasterised displaced column set on
    **302 of 302** incumbent reading comparisons over this corpus, so it is exact here; the name says
    SPAN so that a container where the two differ reads as a WIDER claim rather than a wrong one.
    """
    geom: int                     # identification
    record_at: int                # the `so` record's own file offset -- identification only
    a: int                        # the pair's halfword at position 0 (the container's "A") -- the
                                  # one U1 MEASURED onto u
    b: int                        # ...and at position 1, the one it measured onto v
    bpp: int
    u: Tuple[int, int]            # the reader's UNDISPLACED stored u range -- the file holds the raw
                                  # coordinate; the displacement is baked into the submitted prim
    bound_column: int             # the column its tpage names -- what the kit models today
    swapped_texels: int           # == a, the MEASURED reading's u displacement
    swapped_columns: Tuple[int, ...]
    original_texels: int          # == b, the REFUTED reading's -- b onto u, which the casts excluded
    original_columns: Tuple[int, ...]
    #: W6b-3 (iv): the cells this reader BINDS and the cells it SAMPLES, both fully rasterised -- the
    #: ADOPTED answer, beside the two candidate column SPANS above. Empty on a caller that consulted
    #: the disclosure without ``"so-displaced"``, because a channel nobody asked for says nothing.
    bound_cells: Tuple[Tuple[int, int], ...] = ()
    effective_cells: Tuple[Tuple[int, int], ...] = ()

    @property
    def swapped_moved(self) -> bool:
        return self.swapped_columns != (self.bound_column,)

    @property
    def original_moved(self) -> bool:
        return self.original_columns != (self.bound_column,)

    @property
    def moved_cells(self) -> bool:
        """The ADOPTED reading moves this reader off at least one cell it binds."""
        return bool(self.effective_cells) and self.effective_cells != self.bound_cells


def _effective_columns(page_x: int, u: Tuple[int, int], bpp: int, disp: int) -> Tuple[int, ...]:
    """The VRAM columns a reader's ``u`` span reaches under a ``disp``-texel u displacement.

    Re-derived from :data:`ff9mapkit.summons.reskin.PAGE_CELL_W` and
    :data:`ff9mapkit.summons.texture.TEXELS_PER_HW` rather than typed, so the texels-per-column
    arithmetic is the kit's own: a column is 64 halfwords, i.e. ``{4bpp: 256, 8bpp: 128, 15bpp: 64}``
    texels. ``+128`` is therefore half a 4bpp column, EXACTLY ONE at 8bpp (the cast's 640 -> 704) and
    two at 15bpp.

    **LINEAR, never mod-256**: cast 2 refuted cell-local u-wrap on ef038 (``u + 128`` landed in the
    NEXT column, not back on its own), and the wrap alternative changes 0 slots under the SWAPPED
    labelling anyway.
    """
    per = KT.TEXELS_PER_HW[bpp]
    lo = page_x + (u[0] + disp) // per
    hi = page_x + (u[1] + disp) // per
    return tuple(sorted({(x // RS.PAGE_CELL_W) * RS.PAGE_CELL_W for x in range(lo, hi + 1)}))


@dataclass(frozen=True)
class CellHazards:
    """Every hazard the CONTAINER states about one page-cell, as DATA -- the gates phase's input.

    Deliberately not a verdict. This record answers "what is true of these bytes"; whether that is a
    refusal, a disclosure or an obligation is :mod:`repaint`'s gate layer's decision, and keeping the
    two apart is what lets a refusal name its measurement instead of restating a flag.
    """
    cell: Tuple[int, int]
    writer: str                              # THIS page's own writer tag
    writers: Tuple[CellWriter, ...]          # every writer of the cell, this one included
    readers: Tuple[CellReader, ...]
    depths: Tuple[int, ...]                  # distinct reader depths; >1 == SAME-BYTES-TWO-DEPTHS
    #: distinct CLUT cells this page-cell is read through; >1 at one depth == class C. **AT THE SAME
    #: GRANULARITY AS THE DEPTH, and W6b-2 had to say so**: on a readerless cell the depth comes from
    #: the COLUMN (channel G), so the class-C evidence must come from the column's binders too. Filled
    #: from :attr:`readers` where there are readers and from :attr:`page_clut_cells` where there are
    #: not -- because a class-C predicate computed at one granularity and a depth at another would
    #: report ``multi_palette = False`` by CONSTRUCTION on the whole channel-G surface, i.e. would ship
    #: one of 2-3 renderings with no disclosure. 7 corpus channel-G cells are in that class.
    palette_cells: Tuple[Tuple[int, int], ...]
    spill_in: Tuple[CellReader, ...]         # foreign models reading here -- page scope is wrong
    spill_out: Tuple[int, ...]               # columns THIS cell's own readers also reach
    covered_halfwords: int
    program: str                             # "write" | "read" | "clean" | "unknown"
    program_evidence: str
    program_cell: bool                       # the const-folded MoveImage destination, by name
    #: THIS WRITER'S upload is the lower half of an ``h == 256`` id-0 rect -- the class the per-cell
    #: map exists for (20 corpus cells). Per WRITER, not per cell, and the difference is real: an id-9
    #: alternate block is a whole 0x4000 upload of its own, so it is never a lower half even when a
    #: DIFFERENT writer's tall rect makes the same VRAM cell one.
    lower_half: bool
    provenance: str
    # ---- W6b-2: the two ATTRIBUTION channels and the one NARROWING, as data ----------------------
    #: CHANNEL G -- every depth the container's own ``so`` records state for this cell's **COLUMN**
    #: (:func:`ff9mapkit.summons.reskin.page_depth_view`). Distinct from :attr:`depths`, which is the
    #: UV-granular reader view, and the kit keeps BOTH: *DEPTH is a property of the PAGE; READERSHIP
    #: is a property of the UVs.* Empty when no record names the column.
    page_depths: Tuple[int, ...] = ()
    #: the GEOM bases behind :attr:`page_depths`, lowest first.
    page_binders: Tuple[int, ...] = ()
    #: CHANNEL G's KEY evidence, at the SAME granularity as its depth: the distinct CLUT cells those
    #: binders name, **DISPLAY KEY FIRST** (the lowest-addressed record, mirroring the class-C
    #: display-palette rule). Empty on a 15bpp direct column, which indexes no palette at all, and
    #: empty wherever the caller did not consult channel G. This is what
    #: :func:`alternate_palette_rows` reads on a readerless cell -- a cell with no readers still has
    #: alternates, and reading them off :attr:`readers` would find none by construction.
    page_clut_cells: Tuple[Tuple[int, int], ...] = ()
    #: CHANNEL P -- every depth the container's own id-3 program registers this page at
    #: (:data:`ff9mapkit.summons.depth_attribution.PROGRAM_DEPTH`). Two values is a HAZARD, not a vote.
    program_depths: Tuple[int, ...] = ()
    #: how many op-22 call sites fold to a page word covering this cell.
    program_sites: int = 0
    #: CHANNEL H -- the container's own ``nClut4``/``nClut8`` arity, as a NARROWING (4 means
    #: "4bpp **or** 15bpp"). It attributes NOTHING and is carried only so a refusal can say WHICH of
    #: "the container states nothing" it means.
    bpp_hint: Optional[int] = None
    # ---- W6b-3: CHANNEL A, as data ---------------------------------------------------------------
    #: CHANNEL A -- every depth an ENTRY of a MULTI-PART ``so`` record's binding array states for this
    #: cell's **COLUMN** (:func:`ff9mapkit.summons.reskin.array_depth_view`). A **SET**: the entry
    #: ORDER inside a record's array is UNMEASURED, so nothing here may be read positionally. Empty
    #: wherever the caller did not consult ``"so-array"`` -- an unconsulted channel can SAY nothing.
    array_depths: Tuple[int, ...] = ()
    #: the GEOM bases behind :attr:`array_depths`, lowest first.
    array_binders: Tuple[int, ...] = ()
    #: CHANNEL A's KEY evidence at the SAME granularity as its depth -- the distinct CLUT cells those
    #: array entries name, DISPLAY KEY FIRST. The channel-A twin of :attr:`page_clut_cells`, and it
    #: has to be its own field: 65/65 channel-A cells are readerless AND unnamed by any ``P <= 1``
    #: record, so both of the older sources are empty there by construction.
    array_clut_cells: Tuple[Tuple[int, int], ...] = ()
    #: ``(record offset, slot index)`` for each contributing array entry -- **IDENTIFICATION ONLY**,
    #: quoted by the disclosure so an author can look the evidence up. Never an ordering claim.
    array_records: Tuple[Tuple[int, int], ...] = ()
    # ---- W6b-3 (iii): THE SECOND ARRAY, as data --------------------------------------------------
    #: the readers of this cell that carry a NON-ZERO second-array pair, with BOTH candidate
    #: effective columns. **PURELY INFORMATIONAL** -- it feeds no depth, no cover, no page and no
    #: byte -- and **EMPTY wherever the caller did not consult a W6b-2+ channel**, on the CHANNEL H
    #: rule above: an instrument nobody asked for says nothing.
    second_array: Tuple["SecondArrayRead", ...] = ()
    # ---- W6b-3 (iv): THE EFFECTIVE COVER, as data ------------------------------------------------
    #: whether the caller consulted ``"so-displaced"``. When it did, :attr:`readers` is the
    #: **EFFECTIVE** reader set (:func:`effective_cell_readers`) and :attr:`bound_readers` is what the
    #: records BIND; when it did not, the two are the same tuple and every W6b-3 predicate answers
    #: exactly what it answered before. *A channel a caller declined to consult must not appear to
    #: have spoken*, in both directions.
    displacement_adopted: bool = False
    #: the readers under the BOUND join -- **IDENTIFICATION AND AUDIT**, never the licensing
    #: predicate. This is what lets a refusal say WHICH reader left and where it went instead of
    #: reporting an empty set with no history.
    bound_readers: Tuple[CellReader, ...] = ()
    #: ``(novel records, novel slots carrying a non-zero pair)`` for this whole CONTAINER --
    #: :func:`novel_displacement_reach`. The effective cover is a LOWER BOUND on readership and this
    #: is the number that says by how much it could be wrong.
    novel_reach: Tuple[int, int] = (0, 0)

    @property
    def column_clut_cells(self) -> Tuple[Tuple[int, int], ...]:
        """The COLUMN's own CLUT keys, from whichever channel spoke for this cell's depth.

        Channel G's where a ``P <= 1`` record names the column, channel A's where only an array entry
        does. **One accessor, so the class-C evidence can never be taken at a different granularity
        from the depth** -- the defect W6b-2 had to repair for channel G, re-appearing verbatim for
        channel A if these two fields were read separately at each call site.
        """
        return self.page_clut_cells or self.array_clut_cells

    @property
    def co_transform(self) -> bool:
        return len(self.writers) > 1

    @property
    def two_depths(self) -> bool:
        return len(self.depths) > 1

    @property
    def multi_palette(self) -> bool:
        """Class E2 / C: one index array, two renderings. NOT a refusal -- the display-palette rule.

        ⚠ **It reads :attr:`palette_cells`, which W6b-2 had to re-source.** Built from readers alone
        this predicate is ``False`` BY CONSTRUCTION on every readerless cell, so the 57 cells channel G
        licenses would have shipped one of 2-3 renderings with no class-C line and no alternate PNG --
        *less* honest on the new licensed path than W6b-1 was on the old one, on identical evidence.
        7 of the 57 sit on a column bound with more than one CLUT (one with three). (Both counts are
        channel G's own, at the W6b-2 channel scope --
        :data:`ff9mapkit.summons.depth_attribution.A2_SCOPE_NOTE`.)
        """
        return len(self.palette_cells) > 1 and not self.two_depths

    @property
    def shared_read(self) -> bool:
        """Class E3: one edit changes >= 2 models. A DISCLOSURE naming them, not a refusal."""
        return len(self.readers) > 1

    @property
    def spills(self) -> bool:
        return bool(self.spill_in) or bool(self.spill_out)

    # ---- W6b-2: the three refusal classes this rung MINTS, as predicates -------------------------
    @property
    def program_dual(self) -> bool:
        """PROGRAM-DUAL-DEPTH: the container's own program names this column at TWO depths. **22
        corpus cells in 10 containers, and the census could not see this class at all.** Unanimity is
        the verdict rule; two values is a hazard, not a vote, and no acknowledgement lifts it."""
        return len(self.program_depths) > 1

    @property
    def channel_g_dual(self) -> bool:
        """CHANNEL-G-DUAL-DEPTH: no ``so`` reader samples this cell and its column carries TWO
        ``so``-stated depths. **8 corpus cells, NAMED IN NO LANE DOSSIER** -- found by the calibration
        refuter, which is why a kit building its refusal list from the sweep alone would ship them
        unlisted. Scoped to readerless cells on purpose: where a reader exists its UV-granular depth
        is the cell's own fact and the column is an aside."""
        return not self.readers and len(self.page_depths) > 1

    @property
    def array_dual(self) -> bool:
        """ARRAY-DUAL-DEPTH (W6b-3): this cell's COLUMN carries **more than one distinct depth across
        its NOVEL slots**. Set semantics, order-free. **12 corpus cells over 6 columns.**

        ⚠ **NOT scoped to readerless cells, and that is the whole posture.** ``channel_g_dual`` is
        scoped because where a reader exists its UV-granular depth is the cell's own fact and the
        column is an aside. Channel A is not a licensed instrument, so it may not ADD a depth to a
        cell -- but a contradiction it finds is still a contradiction about the same bytes, and the
        conservative reading of an unlicensed channel is a VETO, never an emission. 4 of the 12 sit
        on columns ``so-uv`` / ``so-page`` already serve, and on a path that consults ``so-array``
        those 4 lose their page.
        """
        return len(self.array_depths) > 1

    @property
    def array_in_reach(self) -> bool:
        """★ THE 8/4 SPLIT'S EXACT PREDICATE -- ``the column's INCUMBENT depth set is EMPTY``.

        **INFORMATIVE, NOT A POLICY.** The 8 in channel A's own reach were already refusing as
        ``depth-unknown``, so refusing them by this sharper name costs 0 addressability; the other 4
        DO lose a page. The split is derived and printed because a reader deserves to know which
        half a cell is in -- and the TREATMENT is uniform, because a hazard bites hardest exactly
        where another channel already covers the cell.
        """
        return self.array_dual and not self.page_depths

    @property
    def array_vs_column(self) -> bool:
        """ARRAY-vs-COLUMN-DEPTH (W6b-3): the column carries a UNANIMOUS incumbent depth (channel G
        would license it) **and** a UNANIMOUS novel depth, **and the two differ**. Order-free.

        ★ **THIS ONE WITHDRAWS A PAGE, AND THAT IS THE POINT.** 1 corpus column = 2 cells (ef184
        x448), the ONLY column in the corpus satisfying the predicate, and both cells are LICENSED
        today with no acknowledgement anywhere. Channel G's licence rests on being *the correct
        reading of the record the kit already reads*; here the SAME RECORD CLASS, read correctly,
        says the same texels are bound at another depth. When a licensed channel's own instrument
        contradicts itself on one column the licence is void FOR THAT COLUMN -- and silently keeping
        the incumbent number would manufacture a certainty neither predicate supports. *Both
        predicates true of the same bytes; the kit states both and picks neither.*
        """
        return (len(self.page_depths) == 1 and len(self.array_depths) == 1
                and self.page_depths[0] != self.array_depths[0])

    @property
    def spill_vs_own_page(self) -> bool:
        """SPILL-vs-OWN-PAGE: **both predicates are true of the same bytes.** Every reader of this
        cell is a binding on the NEIGHBOURING page whose ``u`` range crosses the column boundary,
        while the cell's OWN page is named at the other depth. *"A model whose UVs land here reads at
        N"* and *"this cell's page draws at M"* are different questions, and it is neither
        instrument's error -- 2 corpus cells, genuinely dual-depth, FLAGGED rather than reconciled.

        ⚠ **It adds 0 cells to the refused set as PROTECTION** -- both already refuse on
        :attr:`spill_in`'s own remedy gate. It is non-vacuous as a PREDICATE and exists to carry the
        REASON; a gate asserting it protects >= 1 new cell would fail.
        """
        return (bool(self.readers) and len(self.spill_in) == len(self.readers)
                and len(self.page_depths) == 1 and len(self.depths) == 1
                and self.page_depths[0] != self.depths[0])

    @property
    def every_reader_moves(self) -> bool:
        """SECOND-ARRAY MOVER ON EVERY READER -- W6b-3 (iii)'s predicate, and it is deliberately the
        CONSERVATIVE, LABELLING-INDEPENDENT one.

        It asks only *"does every `so` reader of this cell carry a NON-ZERO second-array pair?"*: it
        never asks which halfword moves which axis and it never applies a displacement, which is
        exactly why U1's s77 read -- which settled the labelling, and the ``v`` axis with it -- moved
        this number not at all. **52 corpus cells in 29 containers**
        (:data:`ff9mapkit.summons.depth_attribution.SECOND_ARRAY_MOVER_CELLS`), and re-rolling the
        MEASURED two-axis arithmetic over the same corpus reproduces that set exactly. What stays
        conservative is the ADOPTION, not the arithmetic: the mechanism is one container old, so this
        predicate discloses and refuses rather than displacing anything.

        ``bool(self.readers)`` is the same non-vacuity guard :attr:`spill_vs_own_page` uses and it is
        load-bearing: on a readerless channel-G / A / P cell the *"every reader"* quantifier would
        otherwise be vacuously true. And :attr:`second_array` is empty wherever the caller did not
        consult, so under :data:`CENSUS_CHANNELS` this is ``False`` BY CONSTRUCTION.

        THE GRANULARITY IS THE WHOLE READER SET, measured: ef038 ``cell.s0.x640_y256`` has 27
        readers -- 20 movers and SEVEN zero-pair controls -- and does NOT satisfy this. That 20/7
        split is exactly why U1 cast 1 read ``VISIBLE_UNBANDED`` rather than blank.

        ★★ **W6b-3 (iv) SUPERSEDES IT ON THE ADOPTED PATH, AND SAYS SO HERE RATHER THAN LEAVING IT
        TO BE NOTICED.** This class exists to disclose that *the kit names the reader HERE and the
        hardware may read THERE*. Once ``"so-displaced"`` is consulted the kit names the cell the
        hardware reads, so the premise is spent and there is nothing left to disclose -- the honest
        successors are :attr:`displaced_readerless` and :attr:`displaced_substituted`, which name the
        45 + 7 cells that END with no reader of their own rather than the 52 whose readers merely
        move. It therefore answers ``False`` under :data:`EDIT_CHANNELS` **by construction**, and
        keeps its full W6b-3 meaning (and its 52 / 29 / 47 population) under
        :data:`LICENSED_CHANNELS`, which is the scope its constants are written about.
        """
        return (not self.displacement_adopted and bool(self.readers)
                and len(self.second_array) == len(self.readers))

    # ---- W6b-3 (iv): the three classes THE EFFECTIVE COVER mints, as predicates -------------------
    @property
    def _bound_geoms(self) -> frozenset:
        return frozenset(r.geom for r in self.bound_readers)

    @property
    def _eff_geoms(self) -> frozenset:
        return frozenset(r.geom for r in self.readers)

    @property
    def displaced_readerless(self) -> bool:
        """**DISPLACED-READERLESS: every reader this kit can attribute has LEFT, and none arrives.**

        ⚠ **NOT a newly-caught silent failure -- the DESTINATION is what is new.** W6b-3 (iii)
        already refused the BUILD on every one of these rows behind THE SECOND-ARRAY GATE (measured:
        0 of 45 build clean without the ack), but it could only say THAT every reader carries a
        halfword, never WHERE they went -- the labelling and the operation were not measured yet.
        This rung names the destination and moves the refusal from the BUILD to RESOLUTION and
        EXPORT, so an author is told BEFORE painting rather than after. **45 corpus cells in 26
        containers**, of which 41 carry no other export-blocking refusal.

        ⚠ **45, not the 16 the impact scoping named.** That list was a u-ONLY model -- it applied one
        halfword to ``u`` and modelled ``v`` not at all -- and v-ONLY displacement is the single
        largest mover class (68 of 151). 8 of the 45 are 15bpp pages, invisible to any census that
        leaves ``attribution(include_direct=...)`` at its default.
        """
        return (self.displacement_adopted and bool(self.bound_readers) and not self.readers)

    @property
    def displaced_substituted(self) -> bool:
        """**DISPLACED-READERSHIP-SUBSTITUTED: every reader left AND a DISJOINT foreign set arrived.**

        7 corpus cells, and materially more dangerous than :attr:`displaced_readerless`, which is why
        it is a separate name rather than a footnote on one: *"paint here and a DIFFERENT model shows
        it"* is not *"nothing reads here"*, and on 4 of the 7 the arriving depth differs from the
        departing one as well.
        """
        return (self.displacement_adopted and bool(self.bound_readers) and bool(self.readers)
                and not (self._bound_geoms & self._eff_geoms))

    @property
    def displaced_gained(self) -> bool:
        """This cell binds no reader and a DISPLACED one samples it -- **the gain half.** 70 declared
        corpus cells, 29 of them refused ``depth-unknown`` before this rung."""
        return self.displacement_adopted and not self.bound_readers and bool(self.readers)

    @property
    def displaced_changed(self) -> bool:
        """The cell keeps a reader but not the SAME reader set -- the class nobody had named.

        Nothing refuses and the page is unchanged; what moves is WHICH models a shared-read or
        multi-palette disclosure names, and on some of them the LOWEST-ADDRESSED reader -- i.e. the
        class-C display binding, i.e. the key the exported PNG is in. A picture that comes back in a
        different key with no line saying so is the failure this predicate exists to make loud.
        """
        return (self.displacement_adopted and bool(self.bound_readers) and bool(self.readers)
                and self._bound_geoms != self._eff_geoms
                and bool(self._bound_geoms & self._eff_geoms))

    @property
    def display_binding_moved(self) -> bool:
        """The cell's LOWEST-ADDRESSED reader -- the class-C display binding, i.e. the key the
        exported PNG is in -- is not the one it was under the bound cover.

        ⚠ **NOT SCOPED TO :attr:`displaced_changed`, and the wording used to imply it was.** The
        predicate asks only that the cell had a reader, has one now, and that the lowest-addressed
        one differs -- which also holds on every :attr:`displaced_substituted` cell, whose bound and
        effective reader sets are DISJOINT by construction. Measured over the corpus's hazards it
        holds on **21** cells: the 14
        :data:`~ff9mapkit.summons.depth_attribution.DISPLACED_DISPLAY_BINDING_MOVED` counts inside
        the CHANGED class, plus the 7 SUBSTITUTED ones. The constant is right under its own stated
        scope; this predicate is deliberately wider, and the two are pinned separately (``u1_gates``
        U7d) so neither can drift into the other's number. Behaviourally the extra 7 never print
        here -- :func:`_scenery_disclosures` takes the substituted branch first.
        """
        return (self.displacement_adopted and bool(self.bound_readers) and bool(self.readers)
                and self.bound_readers[0].geom != self.readers[0].geom)

    @property
    def displaced_vs_page_depth(self) -> bool:
        """**DISPLACED-vs-PAGE-DEPTH: a gained cell's arriving reader contradicts CHANNEL G.**

        Scoped to :attr:`displaced_gained` deliberately. Where the cell already had a reader the
        column is an aside (that is ``spill_vs_own_page``'s territory, a DISCLOSURE); where the cell
        had none, channel G's page depth was the ONLY thing speaking and an arriving reader that
        states another depth is two overlapping tpages naming the same VRAM at two depths.
        **UNANIMITY IS THE VERDICT RULE; TWO VALUES IS A HAZARD, NOT A VOTE** -- so this VETOES
        rather than re-sourcing, on ``array_vs_column``'s precedent: both predicates true of the same
        bytes, the kit states both and picks neither. 1 corpus cell (ef447 ``x768_y384``, ``so-page``
        4bpp against a 15bpp arriving reader).
        """
        return (self.displaced_gained and len(self.page_depths) == 1 and len(self.depths) == 1
                and self.page_depths[0] != self.depths[0])

    @property
    def names(self) -> Tuple[str, ...]:
        """The hazard slugs that hold on this cell -- what a scaffold comment and a gate both quote."""
        out = []
        if self.co_transform:
            out.append("co-transform")
        if self.two_depths:
            out.append("same-bytes-two-depths")
        if self.program_dual:
            out.append("program-dual-depth")
        if self.channel_g_dual:
            out.append("channel-g-dual-depth")
        if self.array_vs_column:
            out.append("array-vs-column-depth")
        if self.array_dual:
            out.append("array-dual-depth")
        if self.spill_vs_own_page:
            out.append("spill-vs-own-page")
        if self.multi_palette:
            out.append("multi-palette")
        if self.shared_read:
            out.append("shared-read")
        if self.spill_in:
            out.append("spill-in")
        if self.spill_out:
            out.append("spill-out")
        if self.lower_half:
            out.append("lower-half")
        if self.program in ("write", "unknown"):
            out.append("program-vram-%s" % self.program)
        if self.program_cell:
            out.append("program-moveimage-cell")
        # ⚠ AND `second-array-mover` IS DELIBERATELY NOT IN THIS LIST.  `names` is the W6b HAZARD
        # vocabulary -- what the container states about these BYTES -- and the second array is a
        # DISCLOSURE about READERSHIP with its own field (`second_array`), its own refusal class and
        # its own key.  It is also an EXACT-TUPLE pin in six shipped places, so this is stated here
        # rather than left as an omission a reader has to notice: measured, none of those sites is a
        # firing cell today, so adding it would not go red -- it is left out on the vocabulary
        # argument, and putting it in is a one-line, reversible owner decision.
        return tuple(out)


@dataclass(frozen=True)
class CellRefusal:
    """A page-cell this rung does NOT hand the author an editable picture for, and WHY.

    Carried as a first-class result rather than an omission: 2,385 of the corpus's 2,572 scenery
    cells are depth-unknown, so the refusals ARE the surface, and a cell that merely failed to appear
    would teach nothing. :func:`scaffold_text` prints every one of these as a commented block, which
    is where a refusal teaches.
    """
    name: str
    cell: Tuple[int, int]
    klass: str
    reason: str


#: the refusal classes this rung emits, each with the corpus measurement that justifies it.
_REFUSAL_TEXT = {
    "depth-unknown": (
        "DEPTH-UNKNOWN: no `so` record binds this cell, so its BIT DEPTH is not a fact the container "
        "states -- and the same 0x4000 bytes are 256, 128 or 64 texels wide at 4 / 8 / 15 bpp.  "
        "2,385 of the corpus's 2,572 scenery cells are in this class (92.7%), and the coherence probe "
        "built to GUESS the depth was FALSIFIED at 54.5% agreement on a 3-way choice -- so this "
        "refuses rather than shipping a guess, and does not even disclose one."),
    "same-bytes-two-depths": (
        "SAME-BYTES-TWO-DEPTHS: %s.  Two `so` readers state DIFFERENT depths for one byte block, so "
        "there are two different INDEX ARRAYS over it and no PNG's edit is coherent under both.  This "
        "is not a palette question and refuses earlier than the palette logic; 17 cells over 6 "
        "effects, 3 of them triple-depth."),
    "program-vram-write": (
        "PROGRAM-VRAM WRITE: %s.  The effect's own id-3 program uploads VRAM at run time, and 0 of the "
        "18 RECT* arguments in the corpus const-fold, so which cell it lands on is unresolvable at "
        "this layer -- a repaint here can be a LOST EDIT with no symptom.  175 cells over 15 "
        "containers."),
    "program-moveimage-cell": (
        "PROGRAM-VRAM WRITE, BY CELL: %s.  MoveImage's destination const-folds to this exact cell on "
        "3 of its 5 corpus sites, and this container declares it -- the ONE per-cell program verdict "
        "in the corpus.  SHARPER, NOT NARROWER: every cell of ef001 / ef142 / ef144 is refused as a "
        "program-VRAM WRITE anyway (the census records all 30 of them as `write-moveimage-dest-known`), "
        "and what this verdict adds is that for THIS cell the destination is not merely unresolvable "
        "-- it is RESOLVED, and it is here."),
    "program-vram-unknown": (
        "PROGRAM-VRAM UNKNOWN: %s.  The lists are keyed by effect id, so silence here is ignorance, "
        "not safety -- pass the effect id and this becomes a real verdict."),
    "no-declared-clut": (
        "NO DECLARED PALETTE: the reader's `so` record names CLUT cell %s at %d entries, and no id-0 "
        "inline rect in this container uploads it.  An indexed picture cannot be rendered against a "
        "palette the container does not declare, and inventing one would put the author in a key the "
        "engine never applies."),
    # ---- W6b-2: the four classes the attribution rung mints, four DIFFERENT populations -----------
    #
    # ★ WHY CHANNEL P GETS ITS OWN CLASS INSTEAD OF REUSING `no-declared-clut`.  That text is written
    # ABOUT A READER -- "the reader's `so` record names CLUT cell X at N entries" -- and channel P
    # applies exactly where NO `so` reader samples the cell.  Formatted for a channel-P cell it printed
    # `None` and `0` as if they were measurements, and asserted the container declares no such palette
    # on containers that declare a dozen.  A reason may never drift from the predicate that produced
    # it, and this was the largest single population in the lane: 102 of channel P's 189 cells.
    "program-depth-no-palette": (
        "CHANNEL P STATES A DEPTH AND NOTHING ELSE: %s.  The container's own id-3 program registers "
        "this page's DRAW MODE, which is a fact about how the bytes are READ -- it names no CLUT, and "
        "no `so` record names one either, because no `so` reader samples this cell at all (that is the "
        "premise of the whole channel).  So an INDEXED picture here has no key to index into.  "
        "Inventing one would put the author in a key the engine never applies, and picking one of the "
        "container's own would be the kit CHOOSING a rendering -- the thing `expect_bpp` exists to "
        "stop it doing.  ** THE POPULATION, PLAINLY: 134 of channel P's 189 cells are indexed (4 or "
        "8 bpp) and NOT ONE of them can be rendered -- 102 reach this refusal and the other 32 refuse "
        "earlier on a program-VRAM verdict.  The acknowledgement's live surface is the 55 cells that "
        "are 15bpp DIRECT COLOUR, which index no palette by definition; 43 of those clear every other "
        "gate.  No acknowledgement and no `expect_bpp` reaches this class: the ack is a judgement "
        "about a DEPTH, and what is missing here is a KEY."),
    "program-dual-depth": (
        "PROGRAM-DUAL-DEPTH: %s.  No `so` reader samples this cell, and the container's own id-3 "
        "program registers its COLUMN at TWO different depths -- so the one channel that speaks here "
        "does not speak with one voice.  UNANIMITY IS THE VERDICT RULE; TWO VALUES IS A HAZARD, NOT A "
        "VOTE, and no acknowledgement lifts it: `" + DA.ACK_KEY + "` is the author's judgement about "
        "a SINGLE-valued derivation, and there is no single value here to judge.  22 cells in 10 "
        "containers -- a class the `so` census could not see at all, because it is silent here."),
    "channel-g-dual-depth": (
        "CHANNEL-G-DUAL-DEPTH: %s.  No `so` reader samples this cell, and the container's own `so` "
        "records name its COLUMN at TWO different depths -- the same hazard one channel up.  8 corpus "
        "cells, and they are NAMED IN NO LANE DOSSIER: a kit building its refusal list from the "
        "attribution sweep alone would ship all 8 unlisted, which is why this class is derived LIVE "
        "from the container rather than read off a table."),
    # ---- W6b-3: the two classes CHANNEL A mints.  Both DERIVED LIVE from the container, never
    # tabled and never enumerated in source -- the precedent is `channel-g-dual-depth`, which says in
    # its own words why: a kit building its refusal list from the attribution sweep alone would ship
    # every unlisted one.  Both carry `ARRAY_CAVEAT` because the page-withdrawing verdict is exactly
    # where "nothing about this channel is in-game" is most load-bearing.
    "array-dual-depth": (
        "ARRAY-DUAL-DEPTH: %s.  This cell's COLUMN is named at TWO different depths by the entries of "
        "the container's own MULTI-PART `so` records -- an array no kit before W6b-3 could read.  "
        "UNANIMITY IS THE VERDICT RULE; TWO VALUES IS A HAZARD, NOT A VOTE, and no acknowledgement "
        "lifts it: `" + DA.ACK_ARRAY_KEY + "` is the author's judgement about a SINGLE-valued "
        "derivation, and there is no single value here to judge.  12 corpus cells over 6 columns.  "
        "** STATED PLAINLY: the 12 split 8 + 4 on an EXACT predicate -- whether the column's "
        "INCUMBENT depth set is EMPTY.  The 8 were refusing as `depth-unknown` anyway, so naming "
        "them costs nothing; the other 4 sit on columns `so-uv` or `so-page` DOES serve, and on a "
        "path that consults `so-array` this refusal TAKES THAT PAGE AWAY.  That is deliberate: "
        "CHANNEL A holds VETO power and never emission power, so where it can only make the picture "
        "less certain it is allowed to, and where it could only make it MORE certain it is not.  The "
        "softer treatment -- state the hazard ALONGSIDE and keep the page -- was considered and NOT "
        "shipped: loosening later is cheap, tightening after shipping is not.  " + DA.ARRAY_CAVEAT
        + "  " + DA.DEPTH_COROLLARY),
    "array-vs-column-depth": (
        "ARRAY-vs-COLUMN-DEPTH: %s.  BOTH PREDICATES ARE TRUE OF THE SAME BYTES, and this one "
        "WITHDRAWS A PAGE THE LANE USED TO HAND BACK.  The column carries a UNANIMOUS depth from the "
        "records the kit has always read (CHANNEL G, which it LICENSES) and a UNANIMOUS, DIFFERENT "
        "depth from an ENTRY of a MULTI-PART record's binding array.  CHANNEL G's licence rests on "
        "being the CORRECT READING OF THE RECORD THE KIT ALREADY READS -- and here that same record "
        "class, read at its true length, says these texels are bound at another depth.  A LICENCE "
        "CONTRADICTED BY ITS OWN INSTRUMENT IS VOID FOR THAT COLUMN: keeping the incumbent number "
        "would manufacture a certainty neither predicate supports.  The kit states both and picks "
        "neither.  1 corpus column = 2 cells, and it is the ONLY column in the corpus satisfying the "
        "predicate.  ** STATED PLAINLY: this is the rung's ONE deliberate permissiveness "
        "regression -- these cells resolved to an editable picture before W6b-3 and do not now.  "
        + DA.ARRAY_CAVEAT + "  " + DA.DEPTH_COROLLARY),
    "spill-vs-own-page": (
        "SPILL-vs-OWN-PAGE: %s.  BOTH PREDICATES ARE TRUE OF THE SAME BYTES.  Every `so` reader of "
        "this cell is a binding on the NEIGHBOURING page whose u range crosses the column boundary, "
        "while this cell's OWN page is named at the other depth -- 'a model whose UVs land here reads "
        "at N' and 'this cell's page draws at M' are different questions and neither instrument is "
        "wrong.  Genuinely dual-depth; silently picking one number would manufacture a false "
        "certainty.  2 corpus cells.  ** STATED PLAINLY: this class adds ZERO cells to the refused "
        "set as PROTECTION -- both already refuse through the u-spill remedy gate.  It is non-vacuous "
        "as a PREDICATE and it exists to carry the REASON."),
    # ---- W6b-3 (iii): THE SECOND ARRAY.  Appended AFTER `spill-vs-own-page` and on exactly its
    # precedent -- a class that is a DIFFERENT QUESTION from the chain above, emitted ALONGSIDE the
    # refusal an author would otherwise be shown rather than in front of it.  ⚠ NO LITERAL `%`
    # ANYWHERE IN THIS TEXT: `_refusal` formats it with `txt % detail`, which is why the measured
    # share of the population is stated in the report block and not here.
    "second-array-mover": (
        "SECOND-ARRAY MOVER ON EVERY READER: %s.  THE PAGE IS NOT WITHDRAWN AND NOTHING ABOUT IT "
        "MOVES -- same name, same depth, same bytes, still exported.  What is disclosed is that "
        "EVERY `so` reader of this cell carries a NON-ZERO halfword in the record's SECOND array, "
        "and on ONE container a stock log-only cast MEASURED such a halfword displacing the texels "
        "its reader samples -- pair position 0 onto u, pair position 1 onto v, +128 texels each.  "
        "WHEREVER THAT MECHANISM HOLDS, this cell has NO effective reader at the coordinates this "
        "kit names -- and a perfectly built repaint of it would be INVISIBLE IN GAME with no error "
        "anywhere, which is the failure this class exists to make loud.  Both candidate effective "
        "columns are still stated per reader: SWAPPED is the MEASURED labelling, and ORIGINAL is "
        "RETAINED as the retired reading rather than offered as an alternative.  "
        "THE GRANULARITY IS THE WHOLE READER SET: one reader with a zero pair keeps the cell out of "
        "this class, which is why ef038 `cell.s0.x640_y256` -- 20 movers and SEVEN zero-pair "
        "controls -- is not in it.  AND THE REACH IS THE INCUMBENT RECORDS ONLY: a cell read solely "
        "through a MULTI-PART record cannot be tested here at all, because pairing an array entry to "
        "a binding slot is the ORDER this kit does not claim.  To paint it anyway say `"
        + DA.ACK_MOVER_KEY + " = true` on that row -- an acknowledgement is stated, never inferred, "
        "and the author carries the judgement the kit declines to make.  "
        + DA.U_DISPLACEMENT_CAVEAT),
    # ---- W6b-3 (iv): THE EFFECTIVE COVER.  Three classes, and the first two are the reason this
    # rung exists.  ⚠ NO LITERAL `%` IN ANY OF THEM -- `_refusal` formats with `txt % detail`.
    "displaced-readerless": (
        "DISPLACED-READERLESS: %s.  EVERY `so` reader this container binds to these bytes carries a "
        "NON-ZERO second-array halfword, and under the MEASURED displacement -- linear addition, "
        "pair position 0 onto u and pair position 1 onto v -- not one of them samples this cell.  "
        "WHAT THIS RUNG ADDS IS THE DESTINATION, NOT THE REFUSAL -- and the difference matters, "
        "because the honest version is the stronger one.  W6b-3 (iii) ALREADY refused the BUILD on "
        "every one of these rows behind THE SECOND-ARRAY GATE, measured 0 of 45 building clean "
        "without the ack; but all it could say was THAT every reader of the cell carries a "
        "halfword.  It could not say WHERE THEY WENT, because neither the labelling nor the "
        "operation had been measured yet.  This rung names the destination, and moves the refusal "
        "EARLIER -- from the build to resolution and export -- so an author is told BEFORE they "
        "paint rather than after.  45 corpus cells in 26 containers, 41 of "
        "them fully open before this rung.  ** AND THE NUMBER IS NOT THE IMPACT SCOPING'S 16: that "
        "list modelled u alone, while v-ONLY displacement is the largest mover class in the corpus "
        "(68 of 151) and moves the read into the OTHER STACKED CELL of the same column.  To paint "
        "it anyway say `" + DA.ACK_MOVER_KEY + " = true` on that row -- an acknowledgement is "
        "stated, never inferred.  ** BUT THE KEY LIFTS THE REFUSAL, NOT THE GUARANTEE, AND THE "
        "LEDGER IS MEASURED RATHER THAN PROMISED.  Over all 45 corpus names in this class, WITH the "
        "key: 35 come back and 10 COME BACK WITH NOTHING AT ALL -- 9 fall straight through to "
        "`depth-unknown` and 1 to `channel-g-dual-depth`, because the COLUMN that has to speak for a "
        "readerless cell does not always have an answer either, and when it has two that is a hazard "
        "and not a vote.  Of the 35 that do return, 34 are the SAME PICTURE at the SAME bit depth "
        "with only `depth_source` moving `so-uv` to `so-page`; the 35th, ef424 `cell.s0.x448_y384`, "
        "returns at the same 8 bpp through a DIFFERENT CLUT, because the departed reader's own key "
        "and its column's display key are not the same word.  So: acknowledge and you may be handed "
        "nothing, or the same bytes keyed to another palette.  " + DA.U_DISPLACEMENT_CAVEAT),
    "displaced-readership-substituted": (
        "DISPLACED-READERSHIP-SUBSTITUTED: %s.  Every reader this container binds here has been "
        "displaced OFF this cell, and a DISJOINT set of FOREIGN readers has been displaced ONTO it "
        "-- so the cell is still read, by models that do not name it, and possibly at another "
        "depth.  ** THAT IS A DIFFERENT WARNING FROM `displaced-readerless` AND IT GETS A DIFFERENT "
        "NAME: 'nothing reads here' and 'a DIFFERENT model shows what you paint here' need "
        "different decisions from an author, and 4 of these 7 corpus cells change effective depth "
        "as well.  The kit refuses rather than silently re-attributing, because handing back a "
        "picture keyed to a model the cell does not name is how an edit lands somewhere nobody "
        "looked.  To paint it anyway say `" + DA.ACK_MOVER_KEY + " = true` on that row.  "
        "** AND HERE TOO THE KEY LIFTS THE REFUSAL, NOT THE GUARANTEE -- MEASURED over all 10 corpus "
        "names in this class (the 7 cells, one of which four writer slots upload).  All 10 DO come "
        "back, because a foreign reader arrived and `so-uv` still speaks -- but 5 of them come back "
        "as a DIFFERENT PICTURE: the ARRIVING model's, not the departed one's.  FOUR flip 4 bpp to "
        "8 bpp -- ef179 `cell.id9.s0.x768_y256`, ef227 `cell.s0.x512_y256`, ef498 "
        "`cell.id9.s0.x832_y256`, ef498 `cell.s0.x576_y256` -- which is THE SAME 16,384 BYTES HANDED "
        "BACK AS A DIFFERENT PICTURE: half the texel width, through a 256-entry key instead of a "
        "16-entry one.  A fifth, ef226 `cell.s0.x512_y256`, keeps 8 bpp and changes CLUT.  The other "
        "5 names (2 cells) come back byte-for-byte what they were.  " + DA.U_DISPLACEMENT_CAVEAT),
    "displaced-vs-page-depth": (
        "DISPLACED-vs-PAGE-DEPTH: %s.  BOTH PREDICATES ARE TRUE OF THE SAME BYTES.  No `so` reader "
        "BINDS this cell, so CHANNEL G -- the column's own page word -- was the only instrument "
        "speaking for it and LICENSED a depth; and a reader from a DIFFERENT tpage is displaced "
        "onto these bytes and states another.  Two overlapping pages naming one block of VRAM at "
        "two depths is the classic hazard of this hardware: UNANIMITY IS THE VERDICT RULE, TWO "
        "VALUES IS A HAZARD, NOT A VOTE, and no acknowledgement lifts it -- there is no single "
        "value here to judge.  The softer treatment -- prefer the reader, on the grounds that a "
        "reader outranks a column -- was considered and NOT taken: it would manufacture a certainty "
        "neither predicate supports, which is the same call `array-vs-column-depth` makes on the "
        "same evidence shape.  1 corpus cell.  " + DA.U_DISPLACEMENT_CAVEAT),
}


#: the refusal classes that mean **there is no picture to hand back at all** -- a name that resolves
#: to one of these is answered by :func:`texel_page` with its own reason rather than with "unknown".
#: The program-VRAM classes are deliberately NOT here: they are about whether an edit SURVIVES the
#: cast, which is a gate's verdict on a resolved page, not a failure to resolve one. (And
#: ``program-vram-unknown`` is an artefact of being handed bare bytes with no effect id, which must
#: not make a container unaddressable.)
#:
#: **W6b-2 adds the two DUAL-DEPTH classes and deliberately NOT ``spill-vs-own-page``.** The first two
#: are sharper names for cells that were already unaddressable as ``depth-unknown`` -- addressability
#: delta 0, refusal QUALITY up. The third is a cell that HAS a depth and now has two: it already
#: refuses through the u-spill remedy gate, and putting it here would make the new class protect a
#: cell nothing else protected, which the record says plainly it must not.
#: ``program-depth-no-palette`` is here for the same reason ``no-declared-clut`` is -- there is no
#: picture to hand back -- and it is likewise NOT liftable: an acknowledgement is a judgement about a
#: DEPTH and what this class reports missing is a KEY.
#:
#: **W6b-3 adds BOTH channel-A classes, and their addressability deltas are NOT the same.**
#: ``array-dual-depth``'s 8 in-reach cells were already unaddressable as ``depth-unknown`` (delta 0,
#: refusal QUALITY up, the W6b-2 argument verbatim); its other 4, and both ``array-vs-column-depth``
#: cells, HAD a resolvable page and lose it -- **delta -6 on the licensed path, 0 on the census
#: path**. That is the one non-zero addressability decision in the rung and it is gated by a
#: counterfactual rather than asserted.
#:
#: **AND W6b-3 (iii) ADDS ``second-array-mover`` TO NEITHER SET, DELIBERATELY** -- stated here rather
#: than left as an omission, on the ``spill-vs-own-page`` precedent two paragraphs up. The class
#: DISCLOSES a readership question and withdraws nothing: :func:`texel_page` still resolves the name,
#: :func:`export_art` still writes the PNG, and the emitted bytes of a build that says the key are
#: identical to the bytes of the same build before the class existed. **Addressability delta 0,
#: export delta 0.** Export scope is a decision, never a side effect of adding a reason.
#: **AND W6b-3 (iv) ADDS ITS THREE, WHICH IS THE FIRST TIME THIS LANE HAS WITHDRAWN A PAGE FROM THE
#: ``so-uv`` CHANNEL ITSELF.** ``displaced-readerless`` and ``displaced-readership-substituted`` are
#: the only members of these sets an ACKNOWLEDGEMENT lifts, and the asymmetry is exact: every other
#: member reports a DEPTH the kit would have to invent, while these two report a READERSHIP one cast
#: settles. ``displaced-vs-page-depth`` is NOT liftable, for the reason every dual-depth class is
#: not -- there is no single value to judge. Addressability delta on the licensed edit surface is
#: measured, named cell by cell in the rung's ledger, and reported rather than left to be noticed.
_UNADDRESSABLE = frozenset(("depth-unknown", "same-bytes-two-depths", "no-declared-clut",
                            "program-dual-depth", "channel-g-dual-depth",
                            "program-depth-no-palette",
                            "array-dual-depth", "array-vs-column-depth",
                            "displaced-readerless", "displaced-readership-substituted",
                            "displaced-vs-page-depth"))

#: the refusal classes that also stop :func:`export_art` handing back a paintable PNG. It is
#: ``_UNADDRESSABLE`` plus the program-VRAM verdicts (a picture whose edit is overwritten at run time
#: is worse than no picture) -- and it is a SEPARATE set from ``_UNADDRESSABLE`` precisely so a new
#: refusal class with a lawful REMEDY (``spill-vs-own-page``: name every column, acknowledge) does not
#: silently withdraw art that W6b-1 exported. Export scope is a decision, never a side effect of
#: adding a reason.
_EXPORT_BLOCKING = _UNADDRESSABLE | frozenset(
    ("program-vram-write", "program-moveimage-cell", "program-vram-unknown"))


def _refusal(name: str, cell: Tuple[int, int], klass: str, detail: str = "",
             extra: str = "") -> CellRefusal:
    """One refusal record. ``extra`` is APPENDED after the class text is formatted, never through it:
    the depth-unknown text quotes measured percentages (``92.7%``, ``54.5%``) and a ``%``-format pass
    over it would either die or need those escaped, which is how a measurement quietly becomes a typo.
    """
    txt = _REFUSAL_TEXT[klass]
    reason = (txt % detail) if "%s" in txt or "%d" in txt else txt
    return CellRefusal(name=name, cell=cell, klass=klass,
                       reason=reason + ("  " + extra if extra else ""))


def _displacement_detail(hz: "CellHazards", cell: Tuple[int, int]) -> str:
    """WHO LEFT, WHERE THEY WENT, AND WHO ARRIVED -- the detail both LOSS refusals are formatted with.

    Names every departing reader by GEOM, record offset and measured ``(du, dv)``, and says which
    cell it samples INSTEAD -- the thing the pre-adoption refusal could not say, because it had only
    two candidate labellings and no applied arithmetic.
    """
    here = {x.geom for x in hz.readers}
    gone = [r for r in hz.bound_readers if r.geom not in here]
    L = ["GEOM %#x (record %#x, du=%d dv=%d, %dbpp) binds this cell and samples %s instead"
         % (r.geom, r.record_at, r.mover[0], r.mover[1], r.bpp,
            ", ".join("x%d_y%d" % c for c in r.effective_cells) or "nothing")
         for r in gone]
    if hz.readers:
        L.append("and %s displaced ONTO it instead"
                 % ", ".join("GEOM %#x (record %#x, du=%d dv=%d, %dbpp, binds column %d)"
                             % (r.geom, r.record_at, r.mover[0], r.mover[1], r.bpp, r.page[0])
                             for r in hz.readers))
    return "; ".join(L)


def _reach_line(hz: "CellHazards") -> str:
    """THE REACH BOUNDARY, appended to every displacement verdict -- *no reader THIS KIT CAN
    ATTRIBUTE*, never *nothing*. A silence that cannot tell ignorance from safety is the defect
    ``program-vram-unknown`` was minted to fix, and the effective cover is a LOWER BOUND: it models
    the INCUMBENT records only."""
    recs, pairs = hz.novel_reach
    if not pairs:
        return ("DISPLACEMENT REACH: this container declares no multi-part `so` record carrying a "
                "second-array pair, so the effective cover is complete for it.  MODEL: %s."
                % DISPLACEMENT_MODEL)
    return ("DISPLACEMENT REACH -- READ THIS AS A LOWER BOUND: this container also declares %d "
            "MULTI-PART `so` record(s) whose array carries %d non-zero pair(s), and NOTHING in this "
            "kit models those.  Pairing array entry k with binding slot k is the ORDER "
            "`ORDER_UNMEASURED` says nothing corroborates, so `Binding.mover` refuses to answer "
            "there and a reader displaced onto these bytes through one of them is invisible to "
            "every predicate in this lane.  The verdict above therefore says NO READER THIS KIT CAN "
            "ATTRIBUTE samples this cell -- never that nothing does.  MODEL: %s."
            % (recs, pairs, DISPLACEMENT_MODEL))


def _arity(pmap: "RS.PaletteMap") -> Tuple[int, int]:
    """``(nClut4, nClut8)`` off an already-resolved palette map -- ONE derivation, two call sites.

    ``palette_map(blob, effect=)``'s ``effect`` selects a NAMING overlay and is otherwise inert, so
    the arity is the same whichever way the map was built; sharing this helper is what keeps
    :func:`clut_arity` and :func:`scenery_surface`'s own hint from ever being two measurements.
    """
    pals = [p for p in pmap.palettes if p.slot >= 0]
    return (sum(1 for p in pals if p.entries == 16), sum(1 for p in pals if p.entries == 256))


def clut_arity(blob: bytes) -> Tuple[int, int]:
    """``(nClut4, nClut8)`` for the whole container's id-0 headers -- **CHANNEL H's raw material.**

    Counted off :func:`ff9mapkit.summons.reskin.palette_map`'s own non-creature palettes rather than
    re-reading the header here, so the two can never disagree; the creature strip (``slot < 0``) is
    excluded because it is the id-4 lane's, not the scenery one's.
    """
    return _arity(RS.palette_map(blob))


def _depth_evidence(hint: Optional[int], pd: Optional[DA.ProgramDepth], consulted: bool,
                    ad: Optional["RS.PageDepth"] = None,
                    a_records: Tuple[Tuple[int, int], ...] = ()) -> str:
    """The DISCLOSURE a depth refusal owes the author: what the container states ELSEWHERE.

    W6b-1's refusal said *"the container states nothing about this cell"*, and W6b-2 measured that
    this is FALSE for a large minority of them: 189 carry a program-registered depth, 334 of the
    remaining residue carry a CLUT-arity narrowing. So the reason names which of the two it means --
    and, when it names a program depth, it carries the in-game refutation with it in the same breath,
    because *a caveat that travels separately from the number is a caveat nobody reads*.

    ⚠ ``consulted`` is whether the CALLER asked for any W6b-2 channel, and it gates the whole block
    including :data:`~ff9mapkit.summons.depth_attribution.RESIDUE_LINE`. **A channel a caller declined
    to consult must not appear to have spoken** -- and a residue split is a W6b-2 measurement, so
    appending it unconditionally made ``scenery_surface``'s CENSUS default emit reasons W6b-1 never
    wrote while every count stayed identical and every gate stayed green. It is the same defect one
    layer down from the one this function exists to fix.

    ⚠ AND THE REMEDY SENTENCE IS CONDITIONAL, because for most of channel P there IS no remedy.
    Channel P states a depth and names no CLUT, so an INDEXED (4/8bpp) channel-P cell has no key to
    render against and refuses as ``program-depth-no-palette`` whatever the author acknowledges --
    134 of the 189. Promising the ack path there would state a sufficient condition that is not one.
    """
    if not consulted:
        return ""
    L: List[str] = []
    if pd is not None and not pd.dual:
        L.append("** BUT THE CONTAINER STATES A DEPTH ELSEWHERE (CHANNEL P, DISCLOSE): no `so` "
                 "reader samples this cell; %s.  %s  %s  %s"
                 % (pd.evidence, DA.REGISTRATION_CAVEAT, DA.DEPTH_COROLLARY,
                    ("To edit it anyway say `%s = true` AND state a matching `expect_bpp = %d` -- "
                     "the author carries the judgement, the kit carries the check."
                     % (DA.ACK_KEY, pd.bpp)) if pd.bpp == 15 else
                    ("** AND THE ACKNOWLEDGEMENT CANNOT REACH THIS CELL: `%s` admits a DEPTH, and at "
                     "%d bpp what is missing is a KEY -- channel P names no CLUT and no `so` record "
                     "names one here either, so this cell refuses as `program-depth-no-palette` with "
                     "the ack and a matching `expect_bpp = %d` in hand.  134 of channel P's 189 "
                     "cells are indexed and NONE of them render; the ack's live surface is the 55 "
                     "that are 15bpp DIRECT."
                     % (DA.ACK_KEY, pd.bpp, pd.bpp))))
    # W6b-3: CHANNEL A discloses on exactly the same terms -- a depth the container states that this
    # lane will not adopt.  ``ad`` is None unless the caller named ``"so-array"``, so an unconsulted
    # channel still says nothing; and the remedy sentence is UNconditional here (unlike channel P's)
    # because a channel-A binding carries its own CLUT word, so there is a key as well as a depth.
    if ad is not None and len(ad.depths) == 1:
        L.append("** AND THE CONTAINER STATES A DEPTH ELSEWHERE (CHANNEL A, DISCLOSE): no `so` reader "
                 "samples this cell and no record this kit could read before W6b-3 names its COLUMN, "
                 "but an ENTRY of a MULTI-PART `so` record's binding array binds that column at "
                 "%d bpp (%s -- identification only).  %s  %s  %s  To edit it anyway say `%s = true` "
                 "AND state a matching `expect_bpp = %d` -- the author carries the judgement, the kit "
                 "carries the check.  %s"
                 % (ad.depths[0],
                    ", ".join("record %#x slot %d" % r for r in a_records) or "an array entry",
                    DA.ARRAY_CAVEAT, DA.DEPTH_COROLLARY, DA.ORDER_UNMEASURED,
                    DA.ACK_ARRAY_KEY, ad.depths[0], DA.ARRAY_RESIDUE_LINE))
    if hint is not None:
        L.append("** AND THE CONTAINER NARROWS IT (CHANNEL H): %s -- a NARROWING, not a depth, so it "
                 "licenses no decode on its own and this cell stays refused; but 'the container "
                 "states nothing about this cell' is FALSE here, and 334 of the residue's cells are "
                 "in the same position."
                 % ("the container ships no 16-entry CLUT: 8bpp or 15bpp" if hint == 8 else
                    "the container ships no 8-entry-per-byte CLUT: 4bpp or 15bpp"))
    L.append(DA.RESIDUE_LINE)
    return "  ".join(L)


def scenery_surface(blob: bytes, effect: Optional[int] = None, *,
                    channels: Sequence[str] = CENSUS_CHANNELS,
                    program_depth: bool = False,
                    array_depth: bool = False,
                    displacement_ack: bool = False
                    ) -> Tuple[List[TexelPage], List[CellRefusal]]:
    """**THE SCENERY TEXEL SURFACE** -- one pass, two results: the pages, and the refusals by name.

    ONE derivation, deliberately. The refusals are not the complement of a filter applied somewhere
    else; they fall out of the same walk that emits the pages, so a cell can never be absent from both
    lists and a reason can never drift from the predicate that produced it.

    Built on B1's three derivations plus W6b-2's two attribution channels:

    * :func:`ff9mapkit.summons.reskin.page_cells` -- the per-VRAM-cell map, keyed ``(writer, x, y)``,
      which is what makes the 20 lower halves of tall rects addressable at all;
    * :func:`bound_models` (``attribution(include_direct=True)`` + the UV rasteriser) -- the
      **UV-granular** depth and the cover;
    * :func:`~ff9mapkit.summons.reskin.palette_map` -- the CLUT lane's own names, so a scenery cell's
      palette is named the way the sibling lever names it rather than invented here;
    * **CHANNEL G** :func:`~ff9mapkit.summons.reskin.page_depth_view` -- the SAME ``so`` records at
      PAGE granularity. **The kit keeps both views and never merges them**; this one is what licenses
      the 57 readerless cells whose own column the container binds (57 at the W6b-2 channel scope --
      channel A's veto below withdraws 2 of them on a set that names ``so-array``);
    * **CHANNEL A** :func:`~ff9mapkit.summons.reskin.array_depth_view` -- the SAME ``so`` records at
      page granularity again, but the entries of the MULTI-PART ones no reader before W6b-3 could
      read. Derived LIVE, like G, and for the same reason: it is one more read of a record the walk
      already performs;
    * **CHANNEL P** :data:`ff9mapkit.summons.depth_attribution.PROGRAM_DEPTH` -- the id-3 program's
      own registered tpage, cached and re-derivation-pinned.

    THE LINE, enforced here rather than described: **CHANNEL G LICENSES; CHANNELS P AND A DISCLOSE.**
    A cell is EMITTED when (a) an ``so`` reader samples it -- W6b-1's rule, unchanged; or (b)
    ``"so-page"`` is in ``channels`` and, with no reader, its COLUMN carries exactly one ``so``-stated
    depth (``depth_source="so-page"``); or (c) ``"so-array"`` is in ``channels`` **and**
    ``array_depth=True`` -- i.e. the row said :data:`ACK_ARRAY_DEPTH` -- and the column's novel array
    entries name exactly one depth (``depth_source="so-array"``); or (d) ``"program"`` is in
    ``channels`` **and** ``program_depth=True`` and the program names the column at exactly one depth.
    Everything else refuses by name, and the **DUAL / CONTRADICTED** cases refuse FIRST: a hazard
    outranks an acknowledgement, because the ack is a judgement about a single-valued derivation and
    there is no single value to judge.

    ★ **AND CHANNEL A's TWO HAZARDS OUTRANK EVEN ``so-uv``.** They are the only refusals in this lane
    that can take away a page an earlier rung emitted. The argument is the asymmetry in what an
    UNLICENSED channel is allowed to do: it may never ADD certainty, and it may always SUBTRACT it.
    Four of the 12 ``array-dual`` cells and both ``array-vs-column`` cells are served by ``so-uv`` or
    ``so-page`` today and are withdrawn on any path that consults ``so-array`` -- **-6 cells,
    measured, and 0 on the census path**, because :data:`CENSUS_CHANNELS` does not consult A at all.

    ★★ **AND W6b-3 (iv) RE-AIMS THE READER JOIN AT ONE LINE.** With ``"so-displaced"`` in
    ``channels`` the ``rds`` lookup below is taken on :func:`effective_cell_readers` -- the cell the
    hardware SAMPLES -- instead of :func:`cell_readers`, the cell the record BINDS. Every one of the
    thirty-odd derivations downstream (the depth set, the class-C keys, spill in / out, the covered
    halfword count, the display binding, the alternates, the disclosures, the manifest) inherits
    that switch without an edit of its own, because they all read the joined set. Three classes fall
    out of the difference between the two joins: ``displaced-readerless`` and
    ``displaced-readership-substituted`` (the LOSS half, which REFUSE by default and are lifted by
    :data:`ACK_SECOND_ARRAY` through ``displacement_ack``) and ``displaced-vs-page-depth`` (a VETO
    on a GAINED cell whose arriving reader contradicts channel G). The GAIN half needs no key: an
    arriving reader states its depth off its own ``so`` record, at the same tier as every other
    ``so-uv`` cell, and THE INTRA-PAGE LAW puts the effective address inside that same record's
    tpage, so there is nothing weaker being licensed.

    ``channels`` defaults to :data:`CENSUS_CHANNELS` -- **W6b-1's own set, so this function's output is
    byte-for-byte what it was** -- and every author-facing caller passes :data:`EDIT_CHANNELS`.
    A channel a caller does not name is not merely un-adopted: **its refusals are not stated either**,
    because a verdict from an instrument the caller declined to consult is a verdict it cannot check.
    """
    ch = frozenset(channels)
    unknown_ch = sorted(ch - _CHANNEL_TOKENS)
    if unknown_ch:                                       # a guard may only ever fail CLOSED
        raise RepaintError("unknown depth channel(s) %s -- this rung ships %s"
                           % (", ".join(repr(c) for c in unknown_ch),
                              ", ".join(sorted(_CHANNEL_TOKENS))))
    # ★ `so-displaced` DEPENDS ON `so-uv`, ENFORCED HERE RATHER THAN DESCRIBED, on exactly the
    # channel-A precedent below.  It is not a channel of its own: it is the SAMPLING ARITHMETIC of
    # `so-uv`, so asking for it without the channel it corrects would silently re-aim a join nobody
    # is consulting and every one of its three classes would answer on an empty reader set.  A guard
    # may only ever fail CLOSED.
    if "so-displaced" in ch and "so-uv" not in ch:
        raise RepaintError(
            "channel 'so-displaced' requires 'so-uv' in the same channel set.  It states no depth "
            "of its own -- it is the measured SAMPLING ARITHMETIC of the `so` reader join (MODEL "
            "%s), so without that join there is nothing for it to re-aim and its three classes "
            "would all answer on an empty set.  Pass %r (the shipped edit surface) or %r for the "
            "W6b-3 scope." % (DISPLACEMENT_MODEL, EDIT_CHANNELS, LICENSED_CHANNELS))
    # ★ CHANNEL A DEPENDS ON CHANNEL G, AND THE DEPENDENCY IS ENFORCED HERE RATHER THAN DESCRIBED.
    # Both of channel A's hazards compare the column's NOVEL reading against its INCUMBENT one, and
    # the incumbent half is `pdv` -- empty unless the caller named "so-page".  Asked for "so-array"
    # WITHOUT it, `array_vs_column` is False BY CONSTRUCTION, so ef184 x448 -- the ONE column in the
    # corpus whose licensed reading its own record class contradicts -- would be handed back at 4bpp
    # with the contradiction unstated, and `array_dual`'s refusal would mis-print all 12 cells as
    # having an EMPTY incumbent set.  That is the silent side-taking channel A exists to refuse, so
    # the combination is refused instead of served: *a law not enforced at the call site is not
    # enforced*, and a guard may only ever fail CLOSED.
    if "so-array" in ch and "so-page" not in ch:
        raise RepaintError(
            "channel 'so-array' requires 'so-page' in the same channel set.  CHANNEL A's two hazard "
            "classes are COMPARISONS -- `array-vs-column-depth` asks whether the column's incumbent "
            "depth and its novel one DIFFER, and `array-dual-depth` prints which half of the 8/4 "
            "split a cell is in -- and both read the incumbent side from CHANNEL G.  Without it the "
            "comparison silently answers 'no conflict' on the one corpus column that has one.  Pass "
            "%r (or %r for W6b-1's own surface)." % (LICENSED_CHANNELS, CENSUS_CHANNELS))
    cells = RS.page_cells(blob)
    models = bound_models(blob)
    bound_by_cell = cell_readers(blob, models)
    # ★★ THE ONE LINE WHERE THE ADOPTION HAPPENS.  `bound_by_cell` is what the records BIND and is
    # kept whatever the scope (the refusals below have to name which reader LEFT, and a set with no
    # history teaches nothing); `readers` is what the caller's channel set says the hardware READS.
    displaced = "so-displaced" in ch
    readers = effective_cell_readers(blob, models) if displaced else bound_by_cell
    novel_reach = novel_displacement_reach(blob) if displaced else (0, 0)
    pmap = RS.palette_map(blob, effect=effect)
    # CHANNEL G is derived LIVE from the container and never cached, and is consulted only when the
    # caller names it -- an unconsulted channel costs nothing and, more importantly, can SAY nothing.
    #
    # CHANNEL H has no token of its own and is deliberately not given one: it is a NARROWING
    # (``hint = 4`` means "4bpp OR 15bpp"), it attributes ZERO cells, and a token would invite a
    # caller to ask for a channel that can never answer the question the token is named after. It is
    # consulted exactly when the caller consults ANY W6b-2 channel, and it only ever adds a clause to
    # a refusal that was already going to fire.
    consulted = bool(ch - frozenset(CENSUS_CHANNELS))
    pdv = RS.page_depth_view(blob) if "so-page" in ch else {}
    # ★ THE CHANNEL-SCOPE GATE FOR CHANNEL A, EXPLICIT (and it is load-bearing, not symmetry for its
    # own sake).  Both channel-A hazards derive from `adv`, so gating it here is what makes them
    # unable to fire under CENSUS scope -- exactly as `channel_g_dual` cannot, because `pdv` is gated
    # on the line above.  Without this line the ef184 pair and the 4 covered `array-dual` cells would
    # reclassify under the census default and the containment headline (187 read / 2,385 depth-
    # unknown) would break while every narrowing in the kit was still in place.
    adv = RS.array_depth_view(blob) if "so-array" in ch else {}
    n4, n8 = _arity(pmap)
    hint = DA.clut_arity_hint(n4, n8) if consulted else None
    prog, prog_why = program_class(effect)
    hard_cell = MOVEIMAGE_HARD_CELLS.get(int(effect)) if effect is not None else None

    writers_by_cell: Dict[Tuple[int, int], List[CellWriter]] = {}
    for pc in sorted(cells.values(), key=lambda c: (c.x, c.y, c.off)):
        writers_by_cell.setdefault(pc.cell, []).append(CellWriter(
            tag=pc.tag, chunk=pc.chunk, slot=pc.slot, kind=pc.kind, off=pc.off, nbytes=pc.nbytes,
            provenance=pc.provenance))

    def _palettes(clut_cell, entries):
        return tuple(p for p in sorted(pmap.palettes, key=lambda q: q.off)
                     if p.vram == clut_cell and p.entries == entries)

    pages: List[TexelPage] = []
    refused: List[CellRefusal] = []
    for _key, pc in sorted(cells.items()):
        rds = readers.get(pc.cell, [])
        gpd = pdv.get(pc.cell)
        apd = adv.get(pc.cell)
        ppd = DA.program_depth(effect, pc.cell) if "program" in ch else None
        g_depths = gpd.depths if gpd is not None else ()
        g_binders = tuple(b.geom for b in gpd.binders) if gpd is not None else ()
        # CHANNEL G's KEY evidence, DISPLAY FIRST and de-duplicated in binder order (`binders` is
        # sorted on VALUES -- (geom, tpage, clut_word) -- which IS the class-C display rule and is
        # permutation-invariant).  A 15bpp direct binder names no CLUT and contributes nothing, so a
        # direct column yields ().
        g_keys: List[Tuple[int, int]] = []
        for b in (gpd.binders if gpd is not None else ()):
            if b.cell is not None and not b.direct and b.cell not in g_keys:
                g_keys.append(b.cell)
        # ...and CHANNEL A's, by exactly the same rule on exactly the same accessor.
        a_depths = apd.depths if apd is not None else ()
        a_binders = tuple(b.geom for b in apd.binders) if apd is not None else ()
        a_records = tuple((b.record_at, b.slot) for b in apd.binders) if apd is not None else ()
        a_keys: List[Tuple[int, int]] = []
        for b in (apd.binders if apd is not None else ()):
            if b.cell is not None and not b.direct and b.cell not in a_keys:
                a_keys.append(b.cell)
        p_depths = ppd.depths if ppd is not None else ()
        p_sites = ppd.call_sites if ppd is not None else 0

        crs: List[CellReader] = []
        #: W6b-3 (iii): the per-reader SECOND-ARRAY disclosure, built in this same loop -- no second
        #: walk, no new derivation. Since W6b-3 (iv) it also carries the ADOPTED answer (the bound
        #: and effective CELL sets) beside the two candidate column spans.
        sa_notes: List[SecondArrayRead] = []

        def _reader(m: BoundModel, cover: Dict[Tuple[int, int], Set[int]],
                    columns: Tuple[int, ...]) -> CellReader:
            """One `CellReader`, built the same way from whichever join the caller asked for."""
            pals = _palettes(m.clut_cell, m.clut_entries) if m.clut_cell is not None else ()
            return CellReader(
                geom=m.geom, slot=m.slot, tpage=m.tpage, bpp=m.bpp, clut_word=m.clut_word,
                clut_cell=m.clut_cell, clut_entries=m.clut_entries,
                palettes=tuple(p.name for p in pals),
                palette_offset=(pals[0].off if pals else None),
                faces=m.faces, u=m.u, v=m.v,
                halfwords_here=len(cover.get(pc.cell, ())), columns=columns,
                # ⚠ `own_column` KEEPS ITS BOUND MEANING -- "is this cell's column the one this
                # reader's tpage ORIGIN names?" -- and it is deliberately NOT re-cut as "is this the
                # reader's own page CELL".  A tpage is 256 lines, i.e. BOTH stacked cells of its
                # column, so a v displacement inside the page is not a spill; calling it one would
                # invent an unsatisfiable NAME-EVERY-COLUMN obligation on 129 of 340 readers.
                own_column=(m.page[0] == pc.x), mover=(m.mover or (0, 0)),
                record_at=m.record_at, page=m.page, bound_columns=m.columns,
                effective_cells=(tuple(sorted(m.effective_cover)) if displaced else ()))

        for m in rds:
            crs.append(_reader(m, m.effective_cover if displaced else m.cover,
                               m.effective_columns if displaced else m.columns))
            mv = m.mover or (0, 0)
            # SWAPPED is the ADOPTED reading (pair position 0 onto u) and ORIGINAL is the REFUTED
            # one -- the ef227 value test excluded OR, XOR, FLAG and NONE -- carried beside it so a
            # reader who met this disclosure before the casts can still reconcile what they were
            # shown. `bound_cells` / `effective_cells` are the answer the kit now ACTS on.
            if mv[0] or mv[1]:
                sa_notes.append(SecondArrayRead(
                    geom=m.geom, record_at=m.record_at, a=mv[0], b=mv[1], bpp=m.bpp,
                    u=m.u, bound_column=m.page[0],
                    swapped_texels=mv[0],
                    swapped_columns=_effective_columns(m.page[0], m.u, m.bpp, mv[0]),
                    original_texels=mv[1],
                    original_columns=_effective_columns(m.page[0], m.u, m.bpp, mv[1]),
                    bound_cells=(tuple(sorted(m.cover)) if displaced else ()),
                    effective_cells=(tuple(sorted(m.effective_cover)) if displaced else ())))
        # the BOUND readers, always -- IDENTIFICATION and AUDIT, never the licensing predicate.
        brs = (tuple(_reader(m, m.cover, m.columns) for m in bound_by_cell.get(pc.cell, []))
               if displaced else tuple(crs))
        depths = tuple(sorted({r.bpp for r in crs}))
        # ★ THE CLASS-C EVIDENCE IS TAKEN AT THE SAME GRANULARITY AS THE DEPTH.  Where readers exist
        # they are the cell's own fact; where there are none the depth comes from the COLUMN, so the
        # KEYS must come from the column too.  Reading `crs` in both cases makes `multi_palette` False
        # BY CONSTRUCTION on every readerless cell -- 7 corpus channel-G cells sit on a column bound
        # with 2-3 different CLUTs, and they would ship ONE of those renderings with no class-C line
        # and no alternate PNG, on evidence the kit already had in hand.
        # ...and W6b-3 extends the same law one channel further: where NEITHER a reader NOR a P<=1
        # record speaks, the depth comes from the column's NOVEL array entries, so the KEYS come from
        # them too.  65/65 channel-A cells are readerless AND unnamed by any incumbent record, so
        # `g_keys` is empty there by construction and the census's `hz_multi_palette` reads a VACUOUS
        # 0 -- 34 of the 65 sit on a column bound with 2-4 distinct CLUT words.
        if crs:
            pal_cells = tuple(sorted({r.clut_cell for r in crs if r.clut_cell is not None}))
        elif gpd is not None:
            pal_cells = tuple(sorted(g_keys))
        else:
            pal_cells = tuple(sorted(a_keys))
        spill_in = tuple(r for r in crs if not r.own_column)
        spill_out = tuple(sorted({c for r in crs if r.own_column for c in r.columns
                                  if c != pc.x}))
        covered = len({hw for m in rds
                       for hw in (m.effective_cover if displaced else m.cover).get(pc.cell, ())})
        hz = CellHazards(
            cell=pc.cell, writer=pc.tag, writers=tuple(writers_by_cell[pc.cell]), readers=tuple(crs),
            depths=depths, palette_cells=pal_cells, spill_in=spill_in, spill_out=spill_out,
            covered_halfwords=covered, program=prog, program_evidence=prog_why,
            program_cell=(hard_cell == pc.cell), lower_half=(pc.split and pc.split_index > 0),
            provenance=pc.provenance, page_depths=g_depths, page_binders=g_binders,
            page_clut_cells=tuple(g_keys), program_depths=p_depths, program_sites=p_sites,
            bpp_hint=hint,
            array_depths=a_depths, array_binders=a_binders, array_clut_cells=tuple(a_keys),
            array_records=a_records,
            # ★ GATED ON `consulted`, EXACTLY LIKE CHANNEL H.  The second array lives in the SAME
            # record `so-uv` already reads, so it would cost nothing to state under the census
            # default -- and stating it there would make `scenery_surface`'s CENSUS output no longer
            # byte-for-byte W6b-1's, which is the population `w6b_gates` G6, `w6q_gates` G1/G16 and
            # `w6b2i_gates` I5 are written ABOUT.  *A channel a caller declined to consult must not
            # appear to have spoken*, and every author-facing entry point passes LICENSED_CHANNELS.
            second_array=tuple(sa_notes) if consulted else (),
            displacement_adopted=displaced, bound_readers=brs, novel_reach=novel_reach)

        # ---- (1) WHICH CHANNEL, IF ANY, STATES A DEPTH.  Hazards first: a DUAL derivation is a
        # refusal no acknowledgement lifts, and the FOUR hazard classes are DISJOINT over the corpus
        # (22 program + 8 channel-G + 12 array-dual + 2 array-vs-column, pairwise overlap 0) so the
        # ordering is a STATEMENT, not a tie-break.
        #
        # ★ AND THE TWO CHANNEL-A HAZARDS SIT ABOVE `rds`.  Everything else in this chain answers
        # "which channel may SPEAK for this cell"; these two answer "does any channel still get to".
        # `array-vs-column` outranks `array-dual` because it is the sharper name: two unanimous
        # readings that CONTRADICT is a stronger statement than one reading that is multi-valued, and
        # a refusal must never drift from the predicate that produced it.
        source = ""
        binder = gpd.binding if gpd is not None else None
        a_binder = apd.binding if apd is not None else None
        if hz.array_vs_column:
            refused.append(_refusal(
                pc.name, pc.cell,
                "array-vs-column-depth",
                "the records this kit has always read bind its column at %d bpp (GEOM %s) and an "
                "entry of a MULTI-PART record binds the same column at %d bpp (GEOM %s; %s -- "
                "identification only)"
                % (g_depths[0], ", ".join("%#x" % g for g in g_binders),
                   a_depths[0], ", ".join("%#x" % g for g in a_binders),
                   ", ".join("record %#x slot %d" % r for r in a_records))))
            continue
        elif hz.array_dual:
            refused.append(_refusal(
                pc.name, pc.cell, "array-dual-depth",
                "its column is bound at %s bpp by the entries of MULTI-PART record(s) (GEOM %s; %s "
                "-- identification only), while the records this kit has always read state %s"
                % ("/".join(str(d) for d in a_depths),
                   ", ".join("%#x" % g for g in a_binders),
                   ", ".join("record %#x slot %d" % r for r in a_records),
                   # ★ THE SPLIT'S PREDICATE IS SPENT HERE, NOT RE-DERIVED HERE.  `hz.array_in_reach`
                   # IS `array_dual and not page_depths`; writing `if g_depths` inline would be a
                   # second copy of a law that already has a name, and a property with no call site
                   # is a law nothing enforces.
                   "NOTHING for it (the column's INCUMBENT depth set is EMPTY, so this cell was "
                   "already refusing as `depth-unknown` and the refusal costs no addressability)"
                   if hz.array_in_reach
                   else "%s bpp" % "/".join(str(d) for d in g_depths))))
            continue
        elif (hz.displaced_readerless or hz.displaced_substituted) and not displacement_ack:
            # ★★ THE FALLTHROUGH BLOCK, AND IT IS THE WHOLE RUNG.  Emptying the effective reader set
            # would otherwise drop these cells one branch down into `elif gpd: source = "so-page"` --
            # CHANNEL G, licensed, paintable, no acknowledgement -- because the COLUMN is still bound
            # (a displacement moves where a reader samples, never what the tpage word says).  The kit
            # would refuse a readerless cell and hand it straight back, and 35 of the 45 would go on
            # being paintable-and-silent, which is exactly the class this rung exists to close.  The
            # argument is `array_vs_column`'s, verbatim: when a licensed channel's own instrument
            # contradicts the readership its licence leans on, the licence is void FOR THAT CELL.
            # The acknowledgement is what re-opens the fallthrough, and it is the SAME key those rows
            # already needed to build, so no row that builds today stops building for want of a new
            # one -- what moves is that the refusal arrives at EXPORT time and names where the
            # readers went.
            klass = ("displaced-readerless" if hz.displaced_readerless
                     else "displaced-readership-substituted")
            refused.append(_refusal(pc.name, pc.cell, klass,
                                    _displacement_detail(hz, pc.cell), extra=_reach_line(hz)))
            continue
        elif hz.displaced_vs_page_depth:
            refused.append(_refusal(
                pc.name, pc.cell, "displaced-vs-page-depth",
                "no record binds this cell and its column is bound at %d bpp by GEOM %s (CHANNEL "
                "G), while %s displaced onto it from column %s at %d bpp"
                % (g_depths[0], ", ".join("%#x" % g for g in g_binders),
                   ", ".join("GEOM %#x (record %#x, du=%d dv=%d)"
                             % (r.geom, r.record_at, r.mover[0], r.mover[1]) for r in crs),
                   "/".join(str(c) for c in sorted({r.page[0] for r in crs})), depths[0]),
                extra=_reach_line(hz)))
            continue
        elif rds:
            source = "so-uv"
        elif hz.channel_g_dual:
            refused.append(_refusal(pc.name, pc.cell, "channel-g-dual-depth",
                                    "its column is bound at %s bpp by GEOM %s"
                                    % ("/".join(str(d) for d in g_depths),
                                       ", ".join("%#x" % g for g in g_binders))))
            continue
        elif len(p_depths) > 1:
            refused.append(_refusal(pc.name, pc.cell, "program-dual-depth", ppd.evidence))
            continue
        elif gpd is not None:
            source = "so-page"                           # CHANNEL G LICENSES
        elif apd is not None and array_depth:
            # CHANNEL A, behind the acknowledgement, at exactly CHANNEL P's tier.  `apd` is None
            # unless "so-array" is in ``channels``, so an ack alone can never reach here through a
            # census-scoped caller -- the same structure the program branch below relies on.
            source = "so-array"
        elif ppd is not None and program_depth:
            # CHANNEL P, behind the acknowledgement.  ``ppd`` is None unless "program" is in
            # ``channels``, so an ack alone can never reach here through a census-scoped caller.
            source = "program"
        else:
            refused.append(_refusal(pc.name, pc.cell, "depth-unknown",
                                    extra=_depth_evidence(hint, ppd, consulted, apd, a_records)))
            continue

        # ---- (2) THE PAGE ITSELF.  THE DISPLAY BINDING for a read cell is the LOWEST-ADDRESSED
        # reader (Sec 2.4's class-C rule); every other palette becomes a named read-only ALTERNATE
        # view of the SAME index bytes.  For a channel-G cell the display binding is the column's own
        # lowest-addressed record -- the depth AND the key come from ONE record rather than from a
        # depth here and a second, unrelated palette choice there -- and where that column carries
        # more than one key the OTHERS are named too, through `page_clut_cells`, exactly as a
        # multi-reader cell's are.  Channel P states a DEPTH and nothing else, so a P cell indexes no
        # declared palette and says so IN ITS OWN WORDS: `program-depth-no-palette` below, never the
        # reader-shaped `no-declared-clut`.
        if source == "so-uv":
            bpp, tpage, clut_word = depths[0], crs[0].tpage, crs[0].clut_word
            clut_off, clut_n, pal_name = crs[0].palette_offset, crs[0].clut_entries, \
                crs[0].palette_name
        elif source == "so-page":
            bpp, tpage, clut_word = g_depths[0], binder.tpage, binder.clut_word
            pals = _palettes(binder.cell, binder.entries) if not binder.direct else ()
            clut_off = pals[0].off if pals else None
            clut_n, pal_name = (binder.entries or None), (pals[0].name if pals else "")
        elif source == "so-array":
            # CHANNEL A's page is built exactly the way channel G's is, off the SAME accessor -- so
            # the depth AND the key come from ONE record's array rather than from a depth here and a
            # second, unrelated palette choice there.  `PageDepth.binding` ties on VALUES
            # ((geom, tpage, clut_word)), never on the array INDEX, so the display pick cannot depend
            # on storage order; every OTHER key on the column is named through `array_clut_cells` and
            # ships its own `.as-x{X}_y{Y}.png` alternate.
            bpp, tpage, clut_word = a_depths[0], a_binder.tpage, a_binder.clut_word
            pals = _palettes(a_binder.cell, a_binder.entries) if not a_binder.direct else ()
            clut_off = pals[0].off if pals else None
            clut_n, pal_name = (a_binder.entries or None), (pals[0].name if pals else "")
        else:
            bpp, tpage, clut_word = p_depths[0], 0, 0
            clut_off, clut_n, pal_name = None, None, ""
        pages.append(TexelPage(
            name=pc.name, index=-1, page_offset=pc.off, page_bytes=pc.nbytes,
            w=cell_texel_w(bpp, pc.w), h=CELL_LINES, bpp=bpp,
            clut_offset=clut_off, clut_entries=(clut_n or None),
            tpage=tpage, clut=clut_word, v_offset=0, vram=pc.cell,
            palette_name=pal_name, kind="scenery", cell=pc.cell, hazards=hz,
            depth_source=source,
            readership=("displaced" if (displaced and any(r.displaced for r in crs))
                        else "bound")))

        # ---- (3) THE REFUSALS THAT SURVIVE AN EMITTED PAGE, in sharpening order, unchanged from
        # W6b-1 -- the 57 channel-G cells flow through every one of them exactly as a read cell does
        # (measured: 56 clear, and ef038's does not, on hz_program_write).
        if len(depths) > 1:
            refused.append(_refusal(pc.name, pc.cell, "same-bytes-two-depths",
                                    "readers %s state depths %s"
                                    % (", ".join("%#x" % r.geom for r in crs),
                                       "/".join(str(d) for d in depths))))
        elif hz.program_cell:
            refused.append(_refusal(pc.name, pc.cell, "program-moveimage-cell", prog_why))
        elif prog == "write":
            refused.append(_refusal(pc.name, pc.cell, "program-vram-write", prog_why))
        elif prog == "unknown":
            refused.append(_refusal(pc.name, pc.cell, "program-vram-unknown", prog_why))
        elif bpp != 15 and clut_off is None and source == "program":
            # ★ CHANNEL P'S OWN CLASS, not `no-declared-clut`.  That text names "the reader's `so`
            # record" and a channel-P cell HAS NO READER -- formatting it here printed `None` at `0`
            # entries as if they were measurements, and told an author the container declares no such
            # palette on a container that may declare a dozen.  The population is not marginal: this
            # is 102 of channel P's 189 cells, i.e. the majority of the disclosure surface.
            refused.append(_refusal(
                pc.name, pc.cell, "program-depth-no-palette",
                "the program registers this page at %d bpp at %d call site(s), and this container's "
                "own id-0 headers ship %d 16-entry and %d 256-entry palette(s) -- none of them bound "
                "to THIS cell by anything" % (bpp, p_sites, n4, n8)))
        elif bpp != 15 and clut_off is None:
            # whichever binder actually spoke for this cell -- a channel-A page's key comes off its
            # OWN array entry, so naming channel G's (absent) record here would print `None` as if it
            # were a measurement, which is the exact defect channel P's own class was minted to fix.
            _b = crs[0] if crs else (binder if binder is not None else a_binder)
            refused.append(CellRefusal(
                name=pc.name, cell=pc.cell, klass="no-declared-clut",
                reason=_REFUSAL_TEXT["no-declared-clut"]
                % (str(_b.clut_cell if crs else (_b.cell if _b is not None else None)),
                   ((_b.clut_entries if crs else _b.entries) if _b is not None else 0) or 0)))

        # ---- (4) SPILL-vs-OWN-PAGE, appended ALONGSIDE rather than in the chain above.  It is a
        # different question from every one of them ("is this cell's depth contested?" rather than
        # "will this edit survive?"), it protects nothing new by construction, and its whole job is to
        # carry the reason -- so it must not displace the refusal an author would otherwise be shown.
        if hz.spill_vs_own_page:
            refused.append(_refusal(
                pc.name, pc.cell, "spill-vs-own-page",
                "every reader (%s) binds the neighbouring page at %dbpp; this cell's own page is "
                "named at %dbpp" % (", ".join("%#x" % r.geom for r in crs), depths[0],
                                    g_depths[0])))

        # ---- (5) SECOND-ARRAY MOVER, appended ALONGSIDE for the SAME reason (4) is.  It is a third
        # kind of question again -- not "is this cell's depth contested?" and not "will this edit
        # survive?" but "is this cell READ AT ALL?" -- so it must not displace the refusal an author
        # would otherwise be shown.  The page was appended at the top of (2) and stays appended: this
        # branch adds no `continue`, changes no branch above it, and the class is in NEITHER
        # `_UNADDRESSABLE` nor `_EXPORT_BLOCKING`, so addressability and export are both delta 0.
        #
        # ⚠ AND `every_reader_moves` IS FALSE BY CONSTRUCTION UNDER `so-displaced` (see its own
        # docstring): once the kit names the cell the hardware reads there is nothing left to
        # disclose, and the honest successors are the two LOSS classes above.  This branch is what
        # the W6b-3 scope still gets, so the class -- and its 52 / 29 / 47 population -- keeps
        # meaning exactly what it meant on the surface its constants were measured on.
        if consulted and hz.every_reader_moves:
            refused.append(_refusal(
                pc.name, pc.cell, "second-array-mover",
                "readers " + "; ".join(
                    "GEOM %#x (record %#x, A=%#06x B=%#06x, %dbpp, u %d..%d; SWAPPED -> column(s) "
                    "%s, ORIGINAL -> column(s) %s)"
                    % (n.geom, n.record_at, n.a, n.b, n.bpp, n.u[0], n.u[1],
                       "/".join(str(c) for c in n.swapped_columns),
                       "/".join(str(c) for c in n.original_columns))
                    for n in hz.second_array)))
    return pages, refused


def scenery_texel_pages(blob: bytes, effect: Optional[int] = None, *,
                        channels: Sequence[str] = EDIT_CHANNELS,
                        program_depth: bool = False,
                        array_depth: bool = False,
                        displacement_ack: bool = False) -> List[TexelPage]:
    """Every scenery page-cell whose DEPTH the container states -- **THE EDIT SURFACE**.

    Defaults to :data:`EDIT_CHANNELS`. It USED to default to :data:`LICENSED_CHANNELS` and the
    opening sentence still said so two rungs after it stopped being true -- corrected here rather
    than left to the ⚠ two paragraphs down, because a docstring's first sentence is the one anybody
    reads.

    ``LICENSED_CHANNELS``, the frozen half of that default, is the whole of what "channel G
    LICENSES" means in
    code: 57 readerless cells whose own COLUMN the container binds are handed back as editable pages
    here, and are absent from :func:`scenery_surface`'s CENSUS default. The split is deliberate and
    it is the same one :func:`ff9mapkit.summons.reskin.attribution` already makes -- one derivation,
    a parameter, and defaults chosen so a published count never moves under a caller that did not ask
    for the new channel.

    ⚠ **The 57 is CHANNEL G's own count, at the W6b-2 channel scope** -- since W6b-3 this default
    also consults CHANNEL A, whose hazards can withdraw a page, and 2 of the 57 are among what it
    withdraws. :data:`ff9mapkit.summons.depth_attribution.A2_SCOPE_NOTE` states that delta in full;
    the count is not restated here because channel A is DISCLOSED, never adopted.

    ⚠ **Since W6b-3 (iv) the default is :data:`EDIT_CHANNELS`, not :data:`LICENSED_CHANNELS`** --
    the reader join is taken on the cell the hardware SAMPLES. The two sets are both named and both
    live: ``LICENSED_CHANNELS`` is the W6b-3 scope every gate board is written about and is frozen
    there; ``EDIT_CHANNELS`` is what an author walks.
    """
    return scenery_surface(blob, effect, channels=channels, program_depth=program_depth,
                           array_depth=array_depth, displacement_ack=displacement_ack)[0]


def scenery_cell_refusals(blob: bytes, effect: Optional[int] = None, *,
                          channels: Sequence[str] = EDIT_CHANNELS,
                          program_depth: bool = False,
                          array_depth: bool = False,
                          displacement_ack: bool = False) -> List[CellRefusal]:
    """Every scenery page-cell this rung refuses an editable picture for, with its reason."""
    return scenery_surface(blob, effect, channels=channels, program_depth=program_depth,
                           array_depth=array_depth, displacement_ack=displacement_ack)[1]


#: how each depth channel is named in a guard failure -- so the message says WHICH derivation the
#: author is arguing with, and an INHERITED depth never reads as a direct one.
_DEPTH_DERIVED_BY = {
    "so-uv": "the container's own `so` record",
    "so-page": "the container's own `so` record for this cell's COLUMN (CHANNEL G -- the depth is "
               "INHERITED FROM THE COLUMN, never direct)",
    "so-array": "the container's own `so` record's BINDING ARRAY for this cell's COLUMN (CHANNEL A "
                "-- an array entry the kit could not read before W6b-3; the depth is INHERITED FROM "
                "THE COLUMN, the entry's ORDER within the array is UNMEASURED, and a BINDING is not "
                "a DRAW)",
    "program": "the container's own id-3 program's registered tpage (CHANNEL P -- a REGISTRATION, "
               "and registration is not a draw)",
}

# a source with no entry here raises `KeyError` inside `assert_expect_bpp`, i.e. the guard that is
# supposed to REFUSE would crash instead.  A guard may only ever fail CLOSED, so the coverage is
# asserted at import rather than left to a test somebody might not write.
assert set(_DEPTH_DERIVED_BY) == set(DEPTH_SOURCES), sorted(set(DEPTH_SOURCES)
                                                            - set(_DEPTH_DERIVED_BY))


def assert_expect_bpp(blob: bytes, page: TexelPage, stated: int, where: str) -> str:
    """``expect_bpp`` -- **STATED by the author, CHECKED against the derivation, never chosen.**

    W6b-2 widened *which* derivation without touching the law: a page's depth now comes from one of
    three channels (:data:`DEPTH_SOURCES`) and :data:`_DEPTH_DERIVED_BY` names the one this page's
    number was read off, in BOTH the failure and the success string. Saying "the ``so`` derivation" on
    a channel-P page would credit a record that does not exist -- the absence of any ``so`` reader is
    the premise of that channel.

    The depth is the one number this lane cannot get wrong quietly: the same 0x4000 bytes are a 256-,
    128- or 64-texel-wide picture at 4 / 8 / 15 bpp, so a wrong depth produces a PNG of the wrong shape
    that nonetheless packs to exactly the right byte count. So the author writes it down, and this
    refuses if the container disagrees. It is never inferred FROM the spec -- a guard may only ever
    fail closed.

    Guarded a second time against the container's own ``nClut4`` / ``nClut8`` (the counts
    :func:`~ff9mapkit.summons.reskin.id0_palettes` reads out of the id-0 header): an indexed depth
    whose palette class the owning chunk does not declare at all has nothing to index into, and that
    is a disagreement between two INDEPENDENT headers rather than a restatement of the first.
    """
    got = int(stated)
    if got not in KT.TEXELS_PER_HW:
        raise RepaintError("%s: expect_bpp = %r -- an `so` record states 4, 8 or 15" % (where, got))
    if page.depth_ambiguous:
        raise RepaintError(
            "%s: this cell has NO single depth to guard -- its `so` readers state %s.  Two index "
            "arrays over one byte block; no art is coherent under both, and stating one of them "
            "would pick a picture the other reader will never see."
            % (where, "/".join(str(d) for d in page.hazards.depths)))
    if got != page.bpp:
        raise RepaintError(
            "%s: the spec guards %dbpp, %s derives %dbpp.  At %d the "
            "cell is %d texels wide; at %d it is %d -- the SAME 0x4000 bytes, so a wrong depth packs "
            "to exactly the right byte count and produces the wrong picture with no gate firing.%s"
            % (where, got, _DEPTH_DERIVED_BY[page.depth_source], page.bpp, got, cell_texel_w(got),
               page.bpp, page.w,
               ("  This is the check `%s` exists to be paired with: the ack is your judgement that a "
                "REGISTERED depth is the drawn depth, and `expect_bpp` is the number the kit checks "
                "against the derivation.  It does not match." % DA.ACK_KEY)
               if page.depth_source == "program" else
               ("  This is the check `%s` exists to be paired with: the ack is your judgement that a "
                "depth read off an ENTRY of this column's `so` BINDING ARRAY is the drawn depth, and "
                "`expect_bpp` is the number the kit checks that judgement against.  It does not "
                "match." % DA.ACK_ARRAY_KEY)
               if page.depth_source == "so-array" else ""))
    if page.scenery and got != 15:
        want = 16 if got == 4 else 256
        slot = page.hazards.writers[0].slot if page.hazards and page.hazards.writers else -1
        n = sum(1 for p in RS.palette_map(blob).palettes
                if p.slot == slot and p.entries == want)
        if not n:
            raise RepaintError(
                "%s: the `so` record derives %dbpp, but chunk slot %d's id-0 header declares NO "
                "%d-entry palette (nClut%d == 0) -- there is nothing for a %dbpp index to point at.  "
                "Two independent headers disagree, so the depth is refused rather than believed."
                % (where, got, slot, want, got, got))
    return "expect_bpp %d MATCHES %s" % (got, _DEPTH_DERIVED_BY[page.depth_source])


def texel_page(blob: bytes, name: str, effect: Optional[int] = None, *,
               allow_program_depth: bool = False,
               allow_array_depth: bool = False,
               allow_displaced_readerless: bool = False) -> TexelPage:
    """Resolve a spec-declared texel name over BOTH namespaces, or REFUSE with the set named.

    ``tex.part0`` is the id-4 CREATURE page (W6a). ``cell.s0.x704_y256`` is a scenery VRAM PAGE-CELL
    (W6b-1), and the spelling is deliberate: it is NOT ``page.s0.x704_y256.h256``, because an
    ``h == 256`` rect is not an addressable unit -- it is TWO stacked cells that the engine uploads
    separately and that routinely differ in hazard class (on ef211 column 576 the top half is a
    two-palette refusal and the bottom half is clean single-reader 4bpp). The old rect spelling
    therefore keeps refusing, and now says what it splits into.

    A name that silently matched nothing would be a build that did nothing while reporting success --
    the exact silent failure this lane cannot afford -- so an unknown name always names the whole
    addressable set, and a REFUSED cell is answered with its own reason rather than with "unknown".

    ``allow_program_depth`` is the row's ``acknowledge_program_derived_depth``, passed DOWN rather
    than checked afterwards: channel P's cells are refused at RESOLUTION, so a caller that resolved
    first and consulted the ack second would have to un-refuse a page, and a refusal you can take back
    is not a refusal. It widens nothing else -- a program-DUAL cell stays unaddressable under it,
    because the hazard outranks the acknowledgement.

    ``allow_array_depth`` is the row's ``acknowledge_array_derived_depth`` and is threaded EXACTLY
    the same way, for exactly the same reason. It likewise widens nothing else: an ``array-dual`` or
    ``array-vs-column`` cell stays unaddressable under it.

    ``allow_displaced_readerless`` is the row's :data:`ACK_SECOND_ARRAY`, threaded the same way
    again -- W6b-3 (iv)'s two LOSS classes are refused at RESOLUTION, so the obligation lands where
    an author is about to spend bytes rather than after they have painted. It widens nothing else:
    a ``displaced-vs-page-depth`` cell stays unaddressable under it, because that class reports two
    depths and an acknowledgement is a judgement about a single-valued derivation.
    """
    pages = creature_texel_pages(blob)
    for p in pages:
        if p.name == name:
            return p
    scen: List[TexelPage] = []
    refused: List[CellRefusal] = []
    scen_error = ""
    try:
        scen, refused = scenery_surface(blob, effect, channels=EDIT_CHANNELS,
                                        program_depth=allow_program_depth,
                                        array_depth=allow_array_depth,
                                        displacement_ack=allow_displaced_readerless)
    except (RS.ReskinError, EC.ContainerError) as e:               # a derivation refusal, surfaced
        scen_error = "%s: %s" % (type(e).__name__, e)
    # the REFUSAL is consulted FIRST: a same-bytes-two-depths cell is still EMITTED (the gates phase
    # needs its hazard record), so resolving it before checking would hand back a page whose `bpp` is
    # not a fact -- the one thing this lane may never do quietly.
    hit = next((r for r in refused if r.name == name and r.klass in _UNADDRESSABLE), None)
    if hit is not None:
        raise RepaintError("texel cell %r is REFUSED, not unknown -- %s" % (name, hit.reason))
    for p in scen:
        if p.name == name:
            return p
    L = ["no texel page named %r." % name]
    if name.startswith("page.") and name.count(".") >= 3:
        stem = name.rsplit(".", 1)[0]                              # "page.s0.x576_y256"
        try:
            tag, xy = stem.split(".")[1], stem.split(".")[2]
            x, y = (int(v[1:]) for v in xy.split("_"))
            L.append("That names an h=256 page RECT, which is NOT an addressable unit -- the engine "
                     "uploads it as two stacked VRAM page-cells.  It splits into cell.%s.x%d_y%d and "
                     "cell.%s.x%d_y%d; name the half you mean." % (tag, x, y, tag, x, y + CELL_LINES))
        except (ValueError, IndexError):
            pass
    why = creature_refusal(blob)
    L.append("creature pages: %s" % (", ".join(p.name for p in pages) or "none -- %s" % why))
    L.append("scenery cells: %s" % (", ".join(p.name for p in scen) or
                                    (scen_error or "none whose depth this container states")))
    if refused:
        L.append("%d scenery cell(s) are REFUSED by name (run `export-art` for the reasons)"
                 % len(refused))
    L.append(W6B_REASON)
    raise RepaintError("\n  ".join(L))


def other_page_writers(blob: bytes) -> Dict[Tuple[int, int], List[Tuple[str, int, int]]]:
    """``{(vram x, vram y): [(source, file offset, nbytes)]}`` for every NON-creature page writer.

    Consumes :func:`ff9mapkit.summons.reskin.page_cells` -- the per-VRAM-cell map -- rather than
    re-splitting the rect stream here. The duplicated ``h // 128`` split this used to carry advanced
    by a flat ``k * 0x4000``, which is right on 2,648 of 2,648 corpus cell-writer records and silently
    catastrophic on the first one that is not ``w == 64``: every cell after the first would resolve to
    the wrong file offset while every gate downstream stayed green. ``page_cells`` advances
    ``w * 128 * 2`` and REFUSES ``w != 64`` outright, so the arithmetic is enforced in exactly one
    place instead of being right by coincidence in two.
    """
    out: Dict[Tuple[int, int], List[Tuple[str, int, int]]] = {}
    for _key, pc in sorted(RS.page_cells(blob).items()):
        label = ("%s id-0 page rect" if pc.kind == "id0" else "%s alternate block") % pc.tag
        out.setdefault(pc.cell, []).append((label, pc.off, pc.nbytes))
    return out


# ============================================================ (2) THE UV COVERAGE RASTERISER
def _fill_tri(mask: bytearray, w: int, h: int, tri) -> None:
    """Mark every texel whose CENTRE ``(x+0.5, y+0.5)`` lies inside the triangle."""
    (x0, y0), (x1, y1), (x2, y2) = tri
    ymin = max(0, int(min(y0, y1, y2)))
    ymax = min(h - 1, int(max(y0, y1, y2)) + 1)
    xmin = max(0, int(min(x0, x1, x2)))
    xmax = min(w - 1, int(max(x0, x1, x2)) + 1)
    d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if d == 0:
        return
    for py in range(ymin, ymax + 1):
        cy = py + 0.5
        for px in range(xmin, xmax + 1):
            cx = px + 0.5
            a = ((y1 - y2) * (cx - x2) + (x2 - x1) * (cy - y2)) / d
            bb = ((y2 - y0) * (cx - x2) + (x0 - x2) * (cy - y2)) / d
            c = 1.0 - a - bb
            if a >= -1e-9 and bb >= -1e-9 and c >= -1e-9:
                mask[py * w + px] = 1


def _face_polys(pts):
    """UV corner list -> triangles. A quad's four corners are Z-ORDERED -- the PSX GPU's own strip
    order (v0 v1 over v2 v3), NOT a perimeter walk -- so it fans ``(0,1,2) + (1,3,2)``, the same
    triangulation ``summons.build._mesh_tris`` emits. Measured, not assumed: scoring both fans for
    winding consistency over every 4-corner primitive in the 372-container corpus gives the Z fan
    29,725 of 29,986 textured quads (FT4+GT4, both families) against 13 for the perimeter fan
    ``(0,1,2) + (0,2,3)`` -- the rest degenerate -- and 0 of 612 quad-bearing geoms lean perimeter;
    the untextured G4/F4 buckets agree 3,521:1 in 3D. The perimeter fan on a Z-ordered quad is a
    BOWTIE: opposite winding per triangle, one half double-covered, a wedge uncovered -- on ef211's
    pool arc (geom 0x2ed7c) it under-counted the cover by 700 halfwords, 17.4%."""
    if len(pts) == 4:
        return [(pts[0], pts[1], pts[2]), (pts[1], pts[3], pts[2])]
    return [(pts[0], pts[1], pts[2])]


def coverage_mask(blob: bytes, part_index: int, *, page_w: int = KT.PAGE_W,
                  page_h: int = KT.PAGE_H) -> Tuple[bytearray, dict]:
    """The per-texel SAMPLED mask for one creature part, rasterised from the container's own uv pools.

    A UV-pool entry is ``u16 == u | v << 8`` (the same reading
    :func:`ff9mapkit.summons.texture.uv_texcoord` and ``summons.build._mesh_uvs`` use); ``v`` is used
    raw because the V-offset bake and the block's own VRAM placement cancel (measured: every stock
    part's ``v`` lands in ``[0, 127]``).

    Polygon fill at texel centres, then the CORNERS are OR-ed in. The corner-OR is not a nicety: a
    one-texel-thin face has no centre inside it at all, so a pure centre test would report its texels
    dead and the overlay would tell a painter to leave live geometry alone.
    """
    mask = bytearray(page_w * page_h)
    mp = EC.creature_package(blob)
    if mp is None:
        raise RepaintError("no creature package -- nothing to rasterise")
    g = EC.creature_geom(blob, mp)
    nf = 0
    umin = vmin = 1 << 30
    umax = vmax = -1
    corners: Set[int] = set()
    for mesh in g.meshes:
        pool = g.base + mesh.p_uv
        for prim in EC.iter_primitives(blob, g, mesh):
            if not prim.get("uv") or prim.get("part") != part_index:
                continue
            nf += 1
            pts = []
            for ui in prim["uv"]:
                word = struct.unpack_from("<H", blob, pool + 2 * ui)[0]
                u, v = word & 0xFF, (word >> 8) & 0xFF
                umin, umax = min(umin, u), max(umax, u)
                vmin, vmax = min(vmin, v), max(vmax, v)
                if 0 <= u < page_w and 0 <= v < page_h:
                    corners.add(v * page_w + u)
                pts.append((u + 0.5, v + 0.5))
            for t in _face_polys(pts):
                _fill_tri(mask, page_w, page_h, t)
    for i in corners:
        mask[i] = 1
    return mask, {"faces": nf, "u": (umin, umax) if nf else (0, 0),
                  "v": (vmin, vmax) if nf else (0, 0)}


def border_flood(mask: Sequence[int], w: int, h: int) -> bytearray:
    """Dead texels reachable from the page border THROUGH dead texels -- i.e. the outer pad.

    Whatever is dead and NOT in this set is an interior hole, which is the one case a painter has to
    be told about differently: a hole is enclosed by live geometry, so paint that lands in it is still
    invisible but sits in the middle of the picture rather than outside it.
    """
    seen = bytearray(w * h)
    stack: List[int] = []
    for x in range(w):
        for y in (0, h - 1):
            i = y * w + x
            if not mask[i] and not seen[i]:
                seen[i] = 1
                stack.append(i)
    for y in range(h):
        for x in (0, w - 1):
            i = y * w + x
            if not mask[i] and not seen[i]:
                seen[i] = 1
                stack.append(i)
    while stack:
        i = stack.pop()
        x, y = i % w, i // w
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            xx, yy = x + dx, y + dy
            if 0 <= xx < w and 0 <= yy < h:
                j = yy * w + xx
                if not mask[j] and not seen[j]:
                    seen[j] = 1
                    stack.append(j)
    return seen


@dataclass
class Coverage:
    """One page's sampled/dead census. ``available`` False is an honest verdict, not a failure: a
    container whose GEOM will not parse still has repaintable pages, it just cannot be told which
    texels are live -- so the dead-texel report says UNAVAILABLE instead of reporting zero."""
    available: bool
    reason: str = ""
    mask: Optional[bytearray] = None
    covered: int = 0
    dead: int = 0
    faces: int = 0
    interior_holes: int = 0
    u_range: Tuple[int, int] = (0, 0)
    v_range: Tuple[int, int] = (0, 0)
    total: int = KT.PAGE_W * KT.PAGE_H

    @property
    def covered_fraction(self) -> float:
        return (self.covered / self.total) if self.total else 0.0


def coverage(blob: bytes, part_index: int, *, holes: bool = True) -> Coverage:
    """:func:`coverage_mask` plus the pad/hole split, with every failure turned into a verdict."""
    try:
        mask, st = coverage_mask(blob, part_index)
    except Exception as e:                                       # geom drift / a synthetic container
        return Coverage(available=False, reason="%s: %s" % (type(e).__name__, e))
    total = len(mask)
    cov = sum(mask)
    dead = total - cov
    nholes = 0
    if holes and dead:
        pad = border_flood(mask, KT.PAGE_W, KT.PAGE_H)
        nholes = dead - sum(pad)
    return Coverage(available=True, mask=mask, covered=cov, dead=dead, faces=st["faces"],
                    interior_holes=nholes, u_range=st["u"], v_range=st["v"], total=total)


# ============================================================ (3) THE INDEXED CODEC
def palette_words(blob: bytes, page: TexelPage) -> Tuple[int, ...]:
    """The live CLUT row for one page, as raw BGR555 halfwords.

    REFUSES a page that indexes no palette rather than returning an empty tuple: at 15bpp the texels
    ARE the colour, so a caller that asked for "the palette" has a wrong model of the page in front of
    it, and handing back ``()`` would let it write an all-black picture and call it a round trip.
    """
    if page.clut_offset is None or not page.clut_entries:
        raise RepaintError(
            "%s indexes NO palette (%dbpp %s) -- the texels ARE the colour at direct depth, so there "
            "is no CLUT row to read.  Use write_direct_png / read_direct_png, whose format of record "
            "is RGBA + an explicit STP sidecar."
            % (page.name, page.bpp, "DIRECT colour" if page.direct else
               "and this container declares no upload of its CLUT cell"))
    return struct.unpack_from("<%dH" % page.clut_entries, blob, page.clut_offset)


def transparent_indices(words: Sequence[int]) -> Tuple[int, ...]:
    """Which palette indices decode to alpha 0 -- DERIVED, never assumed to be ``{0}``.

    ``bgr555_rgba`` makes exactly one word transparent: ``0x0000``. The corpus puts exactly one such
    word in every one of its 93 rows and always at index 0, but a gate that hard-coded index 0 would
    be asserting the corpus rather than reading the palette in front of it -- and under a composed
    CLUT edit the palette in front of it is not the stock one.
    """
    return tuple(i for i, w in enumerate(words) if w == 0)


def png_palette(words: Sequence[int]) -> bytes:
    """CLUT words -> a flat 768-byte PIL palette. DISPLAY ONLY -- the container stays the palette
    authority and this lane never writes a CLUT byte, which is exactly why the import re-reads only
    the INDICES and ignores whatever palette the returning PNG carries."""
    out = bytearray(768)
    for i, w in enumerate(words[:256]):
        r, g, b, _a = KT.bgr555_rgba(w)
        out[3 * i:3 * i + 3] = bytes((r, g, b))
    return bytes(out)


def _need_pil():
    try:
        from PIL import Image                     # noqa: F401
    except ImportError as e:                      # pragma: no cover - env dependent
        raise RepaintError("the texel lane needs Pillow (py -m pip install Pillow): %s" % e)
    from PIL import Image
    return Image


def _indexed_image(px: bytes, words: Sequence[int], w: int, h: int):
    Image = _need_pil()
    im = Image.frombytes("P", (w, h), bytes(px))
    im.putpalette(png_palette(words))
    return im


def write_indexed_png(px: bytes, words: Sequence[int], w: int, h: int, path) -> str:
    """One page -> a P-mode PNG whose pixels ARE the indices and whose ``tRNS`` marks the cutout.

    This is the format of record: the 93/93 byte-identical round trip is measured on exactly this
    encoding, and a painter who works in indices cannot accidentally destroy a silhouette or invent a
    fringe index the way an RGBA editor does.
    """
    im = _indexed_image(px, words, w, h)
    zeros = transparent_indices(words)
    kw = {"transparency": zeros[0]} if zeros else {}
    im.save(str(path), **kw)
    return str(path)


def encode_indexed_png(px: bytes, words: Sequence[int], w: int, h: int) -> bytes:
    """The same encoding, to memory -- what the round-trip identity gate re-reads."""
    im = _indexed_image(px, words, w, h)
    zeros = transparent_indices(words)
    buf = io.BytesIO()
    im.save(buf, format="PNG", **({"transparency": zeros[0]} if zeros else {}))
    return buf.getvalue()


def _read_indices(fp, where: str, w: int, h: int, palette_len: int) -> bytes:
    Image = _need_pil()
    with Image.open(fp) as im:
        mode, size = im.mode, im.size
        if mode != "P":
            raise RepaintError(
                "%s re-opens as mode %r, not \"P\".  This lane's format of record is an INDEXED PNG "
                "(the pixels ARE the palette indices).  An RGBA / quantize / mint-CLUT import is "
                "W6b: measured, an identity RGBA round trip already moves 1,844 of 16,384 texels on "
                "ef251 part 0, because 8.31%% of the corpus's palette entries are duplicate words -- "
                "so byte-identity, and with it this lane's whole gate, dies.  Re-export with "
                "`summon-reskin export-art` and edit the indices.  (%s)"
                % (where, mode, INDEXED_RGBA_REASON))
        if size != (w, h):
            raise RepaintError(
                "%s is %dx%d, but this page is %dx%d.  There is no rescale here on purpose: an index "
                "page has no meaningful resample (interpolating between two indices invents a third "
                "colour and can invent a cutout)." % (where, size[0], size[1], w, h))
        px = im.tobytes()
    if len(px) != w * h:                                         # pragma: no cover - PIL guarantees it
        raise RepaintError("%s decoded to %d bytes, expected %d" % (where, len(px), w * h))
    top = max(px) if px else 0
    if top >= palette_len:
        raise RepaintError(
            "%s uses palette index %d, but this page's CLUT row has only %d entries.  An index past "
            "the row samples another part's palette at run time." % (where, top, palette_len))
    return px


def read_indexed_png(path, w: int, h: int, palette_len: int) -> bytes:
    """Load an edited page back as raw indices, REFUSING anything the lane cannot honour."""
    p = Path(path)
    if not p.is_file():
        raise RepaintError("no such source image: %s" % p)
    return _read_indices(str(p), str(p), w, h, palette_len)


# ---- 4bpp: THE NIBBLE PACK -----------------------------------------------------------------------
#: translation tables so the nibble split is C-speed rather than a per-byte Python loop. A cell is
#: 16,384 bytes and the corpus has 2,648 of them, so the gate that checks every one of them has to be
#: able to run inside a test suite.
_LOW_NIBBLE = bytes(b & 0x0F for b in range(256))
_HIGH_NIBBLE = bytes(b >> 4 for b in range(256))
_SHIFT_NIBBLE = bytes((b & 0x0F) << 4 for b in range(256))


def unpack4(raw: bytes) -> bytes:
    """Packed 4bpp texels -> **one byte per texel**, values 0..15. ``out[2i] = raw[i] & 0x0F``.

    THE NIBBLE ORDER IS MEASURED, NOT ASSUMED -- and the prior proof the record cited has no surviving
    artifact, so it was re-proved at corpus scale (2,572 cells, 48 4bpp-bound pages). Byte identity is
    BLIND to the question (``pack4(unpack4(b)) == b`` holds for the swapped convention too), so a
    discriminator was needed: vertical neighbour disagreement is invariant under any within-row
    permutation and is therefore a free control for horizontal disagreement. Calibrated on the
    cast-proven 8bpp answer the instrument re-finds it **93/93 unanimously**; on the 4bpp question the
    low-nibble-first order wins **36/36 with signal** (the 4 dissenters separate by <= 0.00273 against
    a mean winning margin of 0.0616 and are diagnosed individually, not averaged away).

    The load-bearing argument is not statistical, though: the PSX rule is ONE rule at every depth --
    *lower-order bits hold the lower u* -- and its 8bpp instance is cast-proven on screen (W6a's
    emblem read correctly with byte *i* = texel *i*). Low-nibble-first is that same rule one level
    finer.
    """
    out = bytearray(2 * len(raw))
    out[0::2] = bytes(raw).translate(_LOW_NIBBLE)
    out[1::2] = bytes(raw).translate(_HIGH_NIBBLE)
    return bytes(out)


def pack4(indices: Sequence[int]) -> bytes:
    """One byte per texel (0..15) -> packed 4bpp. The exact inverse of :func:`unpack4`.

    REFUSES any index > 15 rather than masking it: at 4bpp a 16th colour does not exist, and masking
    would silently write index ``i & 0x0F`` -- a different, plausible colour with no error anywhere.
    An odd texel count refuses for the same reason (half a byte cannot be written).
    """
    n = len(indices)
    if n % 2:
        raise RepaintError("a 4bpp row is an even number of texels (two per byte); got %d" % n)
    try:
        buf = bytes(indices)
    except (ValueError, TypeError):
        bad = next((i for i, v in enumerate(indices) if not isinstance(v, int) or not 0 <= v <= 255),
                   -1)
        raise RepaintError("4bpp index %r at texel %d is not a byte value" % (indices[bad], bad)) \
            from None
    top = max(buf) if buf else 0
    if top > 15:
        i = buf.index(top)
        raise RepaintError(
            "4bpp index %d at texel %d is outside 0..15.  A 4bpp CLUT row has 16 entries, so a "
            "higher index samples another palette's colours at run time -- refused rather than "
            "masked to %d, which would write a different colour with no error anywhere."
            % (top, i, top & 0x0F))
    lo = int.from_bytes(buf[0::2], "big")
    hi = int.from_bytes(bytes(buf[1::2]).translate(_SHIFT_NIBBLE), "big")
    return (lo | hi).to_bytes(n // 2, "big")


def write_indexed4_png(raw: bytes, words: Sequence[int], w: int, h: int, path) -> str:
    """One packed 4bpp cell -> the P-mode PNG of record: **one byte per texel, values 0..15**.

    Never Pillow's ``bits=4``. The nibble packing is ours end to end, so no PNG bit-order convention
    can reach the container -- which honours the depth warning BY CONSTRUCTION rather than by care.
    """
    if len(raw) * 2 != w * h:
        raise RepaintError("a %dx%d 4bpp cell is %d packed bytes; got %d"
                           % (w, h, w * h // 2, len(raw)))
    return write_indexed_png(unpack4(raw), words, w, h, path)


def read_indexed4_png(path, w: int, h: int, palette_len: int = 16) -> bytes:
    """An edited 4bpp cell PNG -> PACKED bytes, refusing any index the 16-entry row cannot hold."""
    return pack4(read_indexed_png(path, w, h, palette_len))


# ---- 15bpp DIRECT: RGBA + AN EXPLICIT STP SIDECAR ------------------------------------------------
def stp_sidecar_path(path) -> Path:
    """``<cell>.png`` -> ``<cell>.stp.png``. One name, derived in one place, so the writer and the
    reader can never disagree about where bit 15 lives."""
    p = Path(path)
    return p.with_name(p.name[:-4] + ".stp.png" if p.name.lower().endswith(".png")
                       else p.name + ".stp.png")


def direct_transparent(raw: bytes) -> Tuple[int, ...]:
    """Which texel indices of a 15bpp cell are CUTOUTS -- ``{word == 0}``, DERIVED from the values.

    The indexed lane derives its transparent set from the active palette and never assumes ``{0}``;
    at direct colour there is no palette, so the same law lands in its palette-less form: derived from
    the values in front of us. Measured across the corpus's 15bpp cells the cutout share reaches 63%
    (ef429 x448 y384), which is why it must be visible in the picture the author opens.
    """
    n = len(raw) // 2
    return tuple(i for i, wd in enumerate(struct.unpack_from("<%dH" % n, raw, 0))
                 if wd == KT.DIRECT15_CUTOUT)


def write_direct_png(raw: bytes, w: int, h: int, path) -> Tuple[str, str]:
    """One 15bpp cell -> ``(<cell>.png RGBA8, <cell>.stp.png L)``. **Both files are the format.**

    ``0x8000`` (STP set, RGB 0) and ``0x0000`` (the cutout) are two DIFFERENT words that both render
    black, so one alpha channel structurally cannot carry both "this is a hole" and "this blends" --
    the competing single-file design is unimplementable, not merely worse. Therefore:

    * ``<cell>.png`` RGBA8 -- 5:5:5 colour in RGB (**authoritative on import**) and the cutout in
      ALPHA (**checked on import, never read**);
    * ``<cell>.stp.png`` L-mode 0/255 -- bit 15, per texel, **authoritative**.

    This is the exact mirror of the indexed lane, where the PALETTE is display-only and the import
    reads only the indices. One law, two lanes: *the container stays the authority; the PNG carries
    what the author must SEE.* The sidecar is load-bearing and measured -- the STP share ranges 0%
    (ef405, both cells) to 100% (ef150 col 576), so a lane that dropped bit 15 would flatten one whole
    panel and set the blend flag on every texel of the other.
    """
    if len(raw) != 2 * w * h:
        raise RepaintError("a %dx%d 15bpp cell is %d bytes; got %d" % (w, h, 2 * w * h, len(raw)))
    Image = _need_pil()
    words = struct.unpack_from("<%dH" % (w * h), raw, 0)
    rgba, stp = [], bytearray(w * h)
    for i, wd in enumerate(words):
        r, g, b, s = KT.direct15_split(wd)
        rgba.append((r, g, b, 0 if wd == KT.DIRECT15_CUTOUT else 255))
        stp[i] = 255 if s else 0
    im = Image.new("RGBA", (w, h))
    im.putdata(rgba)
    im.save(str(path))
    sp = stp_sidecar_path(path)
    sm = Image.frombytes("L", (w, h), bytes(stp))
    sm.save(str(sp))
    return (str(path), str(sp))


def read_direct_png(path, w: int, h: int) -> bytes:
    """``<cell>.png`` + ``<cell>.stp.png`` -> raw 15bpp halfwords, with the FOUR refusals.

    RGB and the sidecar are read; ALPHA is CHECKED and discarded. Each refusal names its fix, because
    every one of them is an author mistake with a one-line remedy and a silent correction here would
    be the tool choosing a colour:

    1. ``a not in {0, 255}`` -- alpha is a cutout FLAG, not a blend. (The blend is STP.)
    2. ``a == 0`` but RGB+STP encode a non-zero word -- the picture says hole, the colour says paint.
    3. ``a == 255`` but RGB+STP encode ``0x0000`` -- the hardware reads that as a CUTOUT whatever the
       author meant; nudge one channel to 8, or set STP.
    4. a sidecar value that is not 0 or 255 -- bit 15 is one bit.

    A MISSING sidecar refuses too: it is authoritative, so silently defaulting it to zero would clear
    the blend flag on every texel of a 100%-STP panel and report success.
    """
    p = Path(path)
    if not p.is_file():
        raise RepaintError("no such source image: %s" % p)
    sp = stp_sidecar_path(p)
    if not sp.is_file():
        raise RepaintError(
            "%s has no STP sidecar beside it (%s).  Bit 15 is AUTHORITATIVE and cannot be recovered "
            "from an RGBA picture -- 0x8000 (STP set, RGB 0) and 0x0000 (the cutout) are different "
            "words that both render black.  Re-export with `summon-reskin export-art --art-lane "
            "direct15`, which writes both files." % (p, sp.name))
    Image = _need_pil()
    with Image.open(str(p)) as im:
        if im.mode != "RGBA":
            raise RepaintError(
                "%s re-opens as mode %r, not \"RGBA\".  The 15bpp lane's format of record is RGBA8 "
                "(RGB authoritative, alpha checked) plus an L-mode STP sidecar -- a mode that dropped "
                "alpha would drop the cutout with it." % (p, im.mode))
        if im.size != (w, h):
            raise RepaintError("%s is %dx%d, but this cell is %dx%d.  There is no rescale here: "
                               "interpolating between two direct colours invents a third."
                               % (p, im.size[0], im.size[1], w, h))
        px = im.tobytes()                                 # RGBA8, 4 bytes per texel
    with Image.open(str(sp)) as sm:
        if sm.size != (w, h):
            raise RepaintError("%s is %dx%d, but this cell is %dx%d" % (sp, sm.size[0], sm.size[1],
                                                                        w, h))
        stp = sm.convert("L").tobytes()
    out = bytearray(2 * w * h)
    for i in range(w * h):
        r, g, b, a = px[4 * i], px[4 * i + 1], px[4 * i + 2], px[4 * i + 3]
        s = stp[i]
        if s not in (0, 255):
            raise RepaintError(
                "%s: texel %d (%d,%d) carries STP value %d.  The sidecar is ONE BIT per texel -- 0 or "
                "255 only.  Paint it as pure black / pure white, or re-export it."
                % (sp, i, i % w, i // w, s))
        word = KT.direct15_word(r, g, b, 1 if s else 0)
        if a not in (0, 255):
            raise RepaintError(
                "%s: texel %d (%d,%d) has alpha %d.  Alpha here is a CUTOUT FLAG, not a blend -- the "
                "hardware has no partial transparency at direct colour, and the blend selector is "
                "STP, which lives in %s.  Set it to 0 (a hole) or 255 (opaque)."
                % (p, i, i % w, i // w, a, sp.name))
        if a == 0 and word != KT.DIRECT15_CUTOUT:
            raise RepaintError(
                "%s: texel %d (%d,%d) is transparent in the picture but its colour encodes %#06x, not "
                "0x0000.  A hole at direct colour is the WORD 0x0000, so this texel would render as "
                "paint.  Either paint it pure black with STP clear, or make it opaque."
                % (p, i, i % w, i // w, word))
        if a == 255 and word == KT.DIRECT15_CUTOUT:
            raise RepaintError(
                "%s: texel %d (%d,%d) is opaque in the picture but encodes 0x0000 -- and THE HARDWARE "
                "READS 0x0000 AS A CUTOUT whatever was meant by it.  Nudge one channel to 8 (the "
                "smallest step the 5-bit encoding can see), or set STP on this texel."
                % (p, i, i % w, i // w))
        struct.pack_into("<H", out, 2 * i, word)
    return bytes(out)


# ---- THE PAINT (QUANTIZE) LANE -- RGBA in, INDICES out, ZERO CLUT bytes ---------------------------
#: the decode a ``<name>.paint.png`` is RENDERED with, recorded in the manifest and re-checked by
#: :func:`_gate_manifest`. The paint file's colours are only invertible under the decode they were
#: rendered with, so the key is DATA the export writes rather than a convention the reader assumes.
PAINT_RENDER_KEY = "bgr555_rgba"

#: the longest diagonal of the 5-bit BGR cube, in the squared metric this lane selects with:
#: ``3 * 31**2``. Every distance the census prints is quoted against it, so "worst d^2 57" is
#: readable as a fraction of the whole space rather than as a number with no scale.
CUBE_DIAG_SQ = 3 * 31 * 31


def _split5(word: int) -> Tuple[int, int, int]:
    """One BGR555 halfword -> its 5-bit ``(r, g, b)`` triple -- the space the selection happens in.

    The container is BGR555, so the quantizer measures in BGR555. A quantizer choosing in a different
    space than its census reports in produces a number nobody can judge.
    """
    return (word & 0x1F, (word >> 5) & 0x1F, (word >> 10) & 0x1F)


def _stp(word: int) -> int:
    return (word >> 15) & 1


@dataclass(frozen=True)
class AlternateRow:
    """One class-C cell's OTHER CLUT key: the VRAM cell, the derived palette's name, and its words.

    Read-only in every lane. It exists because a class-C cell is ONE byte array read through N
    palettes -- the export writes the other keys as ``.as-x{X}_y{Y}.png`` views, and the paint codec
    reads the same rows to decide whether a tie it is about to break is visible in a picture the
    author was never shown (:data:`R7`).
    """
    clut_cell: Tuple[int, int]
    palette_name: str
    words: Tuple[int, ...]


def alternate_palette_rows(blob: bytes, page: TexelPage,
                           pmap: "RS.PaletteMap") -> Tuple[AlternateRow, ...]:
    """Every OTHER CLUT key this page-cell is read through -- ONE derivation, two consumers.

    :func:`export_art` uses it to write the read-only ``.as-`` alternate views and to name them in the
    manifest; :func:`read_paint_png` uses it to decide the alternate-split refusal. A second copy of
    this join in the codec is exactly what ``reskin._regions(partition=)``'s own comment forbids by
    analogy: one function, N call sites, never two implementations that can drift.

    **CREATURE PAGES ARE STRUCTURALLY EMPTY HERE**, and that is stated rather than discovered: an
    id-4 page is uploaded by PART index and carries its own row of the id-4 CLUT strip, so it has no
    alternate key at all. 93 of the corpus's 240 lawful surfaces are therefore outside the
    alternate-split branch by construction, not by a measurement that might change.

    Also empty at 15bpp (no palette) and on a cell with one binding (class A / B).

    ★ **W6b-2: A READERLESS CELL STILL HAS ALTERNATES.** On a channel-G page no model's UVs land in
    the cell, so ``hz.readers`` is empty and this function used to return ``()`` by construction --
    the export would ship the display key's PNG alone for a cell the container reads through two or
    three. The keys therefore come from the same granularity the DEPTH did: :attr:`CellHazards.readers`
    where there are readers, :attr:`CellHazards.column_clut_cells` (display key first) where there are
    not. 7 corpus channel-G cells are in that class, one of them with three keys.

    ★ **W6b-3 extends that one accessor, not this branch**: on a channel-A page the column's keys come
    from the NOVEL array entries, and :attr:`CellHazards.column_clut_cells` picks the right source, so
    the 34 class-C cells of the channel-A surface each get their alternate PNGs by the same rule that
    already served channel G. **Every key in the set gets an alternate** -- which is what makes the
    display-binder CONVENTION safe while the array's entry ORDER stays unmeasured.
    """
    hz = page.hazards
    if hz is None or page.direct or not page.clut_entries:
        return ()
    if hz.readers:
        shown = hz.readers[0].clut_cell
        keys = {r.clut_cell for r in hz.readers if r.clut_cell is not None}
    else:
        col = hz.column_clut_cells
        shown = col[0] if col else None
        keys = set(col)
    out: List[AlternateRow] = []
    for other in sorted(k for k in keys if k != shown):
        pal = next((q for q in sorted(pmap.palettes, key=lambda z: z.off)
                    if q.vram == other and q.entries == (page.clut_entries or 0)), None)
        if pal is None:
            continue
        out.append(AlternateRow(clut_cell=other, palette_name=pal.name,
                                words=tuple(struct.unpack_from("<%dH" % pal.entries, blob, pal.off))))
    return tuple(out)


def quantize_census(page: TexelPage, words: Sequence[int], tallies: dict) -> dict:
    """The per-row quantize record -- a pure function of counts, so ``plan``, ``self_check``, the
    build manifest and the tests all read ONE derivation of the percentages.

    **THIS IS A DISCLOSURE AND NEVER A REFUSAL, and the reason is measured.** 9 thresholds x 6 pages
    x 3 edits found ``worst_hue40 >= min_unrepresentable`` at EVERY threshold: a fixed CLUT is a
    ~234-colour subset of a 32,768-colour cube, so any hue move leaves it -- and a hue move is this
    lane's own primary use case. No number separates a legitimate fixed-palette edit from an
    unrepresentable one, so a quantization-error threshold would refuse the feature. Any successor
    proposing one owes a separation sweep of that shape first.
    """
    d = dict(tallies)
    op = max(1, d.get("opaque", 0))
    ds = d.pop("_dists", []) or []
    # THE EXACT DISTRIBUTION, kept beside the summary statistics.  The preview's per-texel map is
    # CLAMPED for display; a separation sweep run on a clamped map would silently see every large
    # error as one value -- so the distribution is recorded unclamped, as a histogram.
    hist: Dict[int, int] = {}
    for v in ds:
        hist[v] = hist.get(v, 0) + 1
    d["d_hist"] = {str(k): hist[k] for k in sorted(hist)}
    d["entries"] = len(words)
    d["live_entries"] = sum(1 for w in words if w)
    d["distinct_colours"] = len({w & 0x7FFF for w in words if w})
    d["cube_diagonal_sq"] = CUBE_DIAG_SQ
    d["exact_pct"] = 100.0 * d.get("exact", 0) / op
    d["approximated_pct"] = 100.0 * d.get("approximated", 0) / op
    # the ambiguity share is over the WHOLE page: it is a fact about every texel of the container,
    # not about the opaque ones this edit happened to map.
    d["ambiguous_pct"] = 100.0 * d.get("ambiguous", 0) / max(1, d.get("texels", 0))
    d["tie_pct"] = 100.0 * d.get("nearest_tie", 0) / op
    if ds:
        ds = sorted(ds)
        d["mean_d2"] = sum(ds) / float(len(ds))
        d["p95_d2"] = ds[min(len(ds) - 1, int(0.95 * len(ds)))]
        d["worst_d2"] = ds[-1]
    else:
        d["mean_d2"], d["p95_d2"], d["worst_d2"] = 0.0, 0, 0
    d["page"] = page.name
    d["palette_name"] = page.palette_name
    return d


def census_record(census: dict) -> dict:
    """The JSON-safe half of a census -- everything except the per-texel error map."""
    return {k: v for k, v in (census or {}).items() if k != "dmap"}


def census_lines(census: dict) -> List[str]:
    """THE QUANTIZE CENSUS BLOCK, as ``plan`` prints it. Every number measured on THIS build."""
    if not census:
        return []
    c = census
    L = ["%s   QUANTIZE  %s opaque texels mapped onto %s (%d entries, %d live, %d distinct colours)"
         % (c["page"], "{:,}".format(c.get("opaque", 0)), c.get("palette_name") or "this page's row",
            c.get("entries", 0), c.get("live_entries", 0), c.get("distinct_colours", 0)),
         "  exact colour matches ......... %-7s (%5.2f%%)   -- the entry carried your colour exactly"
         % ("{:,}".format(c.get("exact", 0)), c["exact_pct"]),
         "  approximated ................. %-7s (%5.2f%%)   mean d^2 %.3f, p95 d^2 %d, worst d^2 %d "
         "(of a cube whose longest diagonal is d^2 = %d)"
         % ("{:,}".format(c.get("approximated", 0)), c["approximated_pct"], c["mean_d2"],
            c["p95_d2"], c["worst_d2"], c["cube_diagonal_sq"]),
         "  sitting on an AMBIGUOUS colour %-7s (%5.2f%% of the page) -- the stock index is NOT the "
         "sole claimant of its own colour; THE INCUMBENT LOCK is what decides those"
         % ("{:,}".format(c.get("ambiguous", 0)), c["ambiguous_pct"]),
         "  decided by a nearest-colour TIE %-6s (%5.2f%%)  -- >1 entry equidistant (%s of them at "
         "d^2 = 0, i.e. several entries carry your colour EXACTLY); the total order (incumbent, "
         "STP-matches-incumbent, lowest index) decided"
         % ("{:,}".format(c.get("nearest_tie", 0)), c["tie_pct"],
            "{:,}".format(c.get("exact_tie", 0))),
         "  incumbent NOT NAMEABLE by the row %-4s texels  -- FAIL-SAFE, corpus population 0: a page "
         "carrying an index its own row cannot name has no incumbent, so THE INCUMBENT LOCK cannot "
         "hold it and it moves like any other texel"
         % "{:,}".format(c.get("incumbent_unnameable", 0)),
         "  alternate-split checks ....... %-7s          -- FAIL-SAFE: %d passed, and a SPLIT would "
         "have REFUSED (R7).  %s"
         % ("{:,}".format(c.get("alt_checked", 0)), c.get("alt_checked", 0),
            "this surface has %d alternate key(s)" % c.get("alt_rows", 0) if c.get("alt_rows")
            else "structurally unreachable here: this page declares NO alternate CLUT key"),
         # TWO DIFFERENT FACTS, deliberately on two lines.  The first is about YOUR EDIT (an index
         # moved to one whose blend flag differs); the second is about THE TIE-BREAK's own STP term,
         # which is the labelled fail-safe and has a named population.  One line carrying both read
         # right and meant nothing.
         "  STP differs from the incumbent %-7s texels   -- a DISCLOSURE about this edit: the entry "
         "you landed on carries a different blend flag" % "{:,}".format(c.get("stp_changed", 0)),
         "  ...the STP TERM decided the pick %-5s texels   -- FAIL-SAFE: colour-equal/STP-differing "
         "entries number 0 on 93/93 creature rows and 38 groups on 4 of 3,095 scenery rows, so this "
         "term is structurally unreachable on the creature surface"
         % "{:,}".format(c.get("stp_decided", 0)),
         "  opaque black (RGB 0,0,0 @a=255) %-6s texels   -- 0x0000 is the container's cutout word BY "
         "VALUE, so these map to the nearest OPAQUE entry"
         % "{:,}".format(c.get("opaque_black", 0)),
         "  cutout: %d punched, %d filled                 -- ALPHA GOVERNS, so every crossing is one "
         "you drew" % (c.get("cutout_punch", 0), c.get("cutout_fill", 0)),
         "  DISCLOSURE: a fixed CLUT is a small subset of the 32,768-colour BGR555 cube, so a HUE or",
         "    VALUE shift of the WHOLE picture will always read as \"approximated\" here.  If that is",
         "    what you want, [[reskin.target]] does it EXACTLY and writes zero texel bytes.  Quantize",
         "    is for a SHAPE or DETAIL change the palette already has the colours for."]
    return L


def read_paint_png(src, page: TexelPage, words: Sequence[int], inc_tex: Sequence[int],
                   alt_rows: Sequence[AlternateRow] = ()) -> Tuple[bytes, dict]:
    """An RGBA painting -> this page's own PACKED index bytes, against the row the container carries.

    THE THREE PROPERTIES THIS LANE IS ALLOWED TO CLAIM, and each falls out of the shape below:

    1. **THE NO-OP IS EXACT.** An unedited export re-imported through this lane changes ZERO container
       bytes, on 240 of 240 lawful surfaces -- including the pages that are 100% ambiguous and the
       239-way tie. That is THE INCUMBENT LOCK: the container's own index at this texel is the FIRST
       term of the selection order, so wherever it is still a correct answer it wins. Without it the
       naive nearest rule moves **767,531 texels across 191 of 240 surfaces**, and exactly **1,844 of
       16,384** on ``ef251 tex.part0`` -- the published figure the ``rgba`` refusal quotes, which is
       why the lock is calibrated rather than plausible.
    2. **DETERMINISM IS STRUCTURAL.** A total order over UNIQUE indices, integer arithmetic only, no
       set or dict iteration in any decision path, and no floating point anywhere in the decision. The
       same ``(container bytes, PNG bytes)`` produce the same byte at every texel on every platform,
       every Pillow version and every ``PYTHONHASHSEED``.
    3. **THE APPROXIMATION IS DISCLOSED PER TEXEL.** The returned census counts every class, and
       ``--previews`` renders the per-texel error map beside it.

    What it explicitly does NOT claim, stated so no gate is asked to prove it: that a re-import of an
    EDITED paint file is exact. It never was on any lane. ``acknowledge_quantize`` is where the author
    says so.

    THE ALGORITHM, per texel, with incumbent ``s``:

    * **step 0, THE ALPHA GATE.** ``a`` must be 0 or 255 (R4). ``a == 0`` selects from the DERIVED
      transparent set ``Z`` (R12 if empty); ``a == 255`` selects from everything EXCEPT ``Z`` (R5 if
      empty). **ALPHA GOVERNS THE CUTOUT IN BOTH DIRECTIONS** -- without it a plain 40 degree hue
      slider on ``ef227 tex.part0`` sends 502 of 15,931 opaque texels onto the transparent index: 502
      holes the author never drew. With it: 0, across all 8 sampled pages;
    * **step 1**, the painted colour is READ with the SHIFT (``direct15_word``), while the file was
      RENDERED with the display decode (``bgr555_rgba``). Two different maps whose composition is the
      identity -- proven exhaustively, and load-bearing enough to have its own gate;
    * **step 2/3**, the EXACT class, else the NEAREST class by squared Euclidean distance over the
      5-bit triple;
    * **step 4**, ★ THE ALTERNATE-SPLIT REFUSAL (:data:`R7`), between the nearest class and the
      tie-break, because that is the only place the candidate set exists;
    * **step 5**, THE CHOICE, by the stated total order ``(incumbent, STP-matches-incumbent, lowest
      index)``. The STP term is a LABELLED FAIL-SAFE with a named population: unreachable on 93/93
      creature rows by construction, reachable only on 4 named scenery rows.

    **Opaque black is a DISCLOSURE, not a refusal.** ``0x0000`` is the container's cutout BY VALUE, so
    an index carrying it is in ``Z`` and is excluded from the opaque candidates -- an opaque black
    pixel therefore maps to the nearest OPAQUE entry and cannot accidentally punch a hole. The
    alpha-governs rule already removed the hazard a refusal would have existed for; refusing would
    block a legitimate paint. It is counted and named in the census instead.
    """
    p = Path(src)
    if not p.is_file():
        raise RepaintError("no such source image: %s" % p)
    Image = _need_pil()
    w, h = page.w, page.h
    with Image.open(str(p)) as im:
        if im.mode != "RGBA":
            raise RepaintError(                                            # R1
                "%s re-opens as mode %r, not \"RGBA\".  The paint lane's format of record is RGBA8: "
                "RGB approximated onto the row this container already carries, ALPHA AUTHORITATIVE.  "
                "A mode that dropped alpha would drop your cutout with it.  `%s.png` is the P-mode "
                "INDEXED export and belongs to `source`, not `source_paint`." % (p, im.mode,
                                                                                 page.name))
        if im.size != (w, h):
            raise RepaintError(                                            # R2
                "%s is %dx%d, this page is %dx%d.  No rescale here, ever: interpolating between two "
                "colours invents a third the palette may not carry, and interpolating across an alpha "
                "edge invents a partial hole." % (p, im.size[0], im.size[1], w, h))
        px = im.tobytes()                                                  # RGBA8, 4 bytes per texel
    n = w * h
    zset = frozenset(transparent_indices(words))
    c_op = tuple(i for i in range(len(words)) if i not in zset)
    if not c_op:
        raise RepaintError(                                                # R5
            "%s: this row has no opaque entry to land on -- every one of its %d entries decodes to "
            "the cutout, so an opaque texel has nowhere to go.  LABELLED A FAIL-SAFE: the corpus "
            "population of this class is 0 (a row with no live colour draws nothing), so it is stated "
            "rather than claimed as a proof." % (page.name, len(words)))
    c_z = tuple(sorted(zset))

    # --- the per-COLOUR memo.  A page is 16,384 texels over at most 256 entries, and the decision is
    # a pure function of (painted colour, alpha branch) -- so the palette scan runs once per DISTINCT
    # painted colour and the per-texel work is the incumbent-dependent tail.  This is a cache, not a
    # heuristic: it changes the cost, never the answer.
    memo: Dict[Tuple[int, int], Tuple[Tuple[int, ...], int]] = {}
    alt_memo: Dict[Tuple[int, ...], bool] = {}
    out = bytearray(n)
    t = {"texels": n, "opaque": 0, "cutout": 0, "exact": 0, "approximated": 0, "ambiguous": 0,
         "nearest_tie": 0, "exact_tie": 0, "alt_checked": 0, "stp_changed": 0, "stp_decided": 0,
         "opaque_black": 0, "cutout_punch": 0, "cutout_fill": 0, "partial_alpha": 0,
         "incumbent_unnameable": 0,
         "alt_rows": len(alt_rows), "_dists": []}
    dmap = bytearray(n)
    nwords = len(words)

    # PASS 0: the alpha gate, whole-page, BEFORE a single index is chosen.  Counting first means the
    # refusal can quote the population as well as the first offender -- law 2.
    bad = -1
    for i in range(n):
        a = px[4 * i + 3]
        if a != 0 and a != 255:
            t["partial_alpha"] += 1
            if bad < 0:
                bad = i
    if bad >= 0:
        raise RepaintError(                                                # R4
            "%s: texel (%d,%d) has alpha %d.  Alpha here is a CUTOUT FLAG, not a blend -- the "
            "hardware has no partial transparency, and the blend selector is STP, which lives in the "
            "CLUT and this lane does not write it.  %d texel(s) (%.2f%%) carry a partial alpha.  "
            "Flatten them to 0 or 255." % (p, bad % w, bad // w, px[4 * bad + 3],
                                           t["partial_alpha"], 100.0 * t["partial_alpha"] / max(1, n)))

    # THE AMBIGUITY CENSUS IS AN INCUMBENT-SIDE FACT ABOUT THE CONTAINER, not about the edit: how
    # many texels sit on an index that is NOT THE SOLE CLAIMANT OF ITS OWN COLOUR -- i.e. how many
    # the incumbent lock is what decides.  Corpus scale: 10.25% of creature texels and 39.75% of
    # lawful scenery ones, with pages at 100%.  Reported over the WHOLE page, since it is a property
    # of every texel and not only of the opaque ones.
    dup_count: Dict[int, int] = {}
    for wd in words:
        dup_count[wd] = dup_count.get(wd, 0) + 1
    dup_flag = tuple(dup_count[wd] > 1 for wd in words)
    # how many OPAQUE entries carry each 15-bit colour -- so the no-op fast path below can say
    # whether it was a tie without paying for the palette scan it exists to skip.
    col_count: Dict[int, int] = {}
    for i in c_op:
        k = words[i] & 0x7FFF
        col_count[k] = col_count.get(k, 0) + 1

    for i in range(n):
        s = inc_tex[i]
        r8, g8, b8, a = px[4 * i], px[4 * i + 1], px[4 * i + 2], px[4 * i + 3]
        s_ok = s < nwords                       # an index this row cannot name: the incumbent terms
        s_hole = s_ok and s in zset             # are simply False.  No crash, no silent choice.
        if not s_ok:
            # A LABELLED FAIL-SAFE WITH ITS OWN POPULATION, like R5 and the STP term.  A page carrying
            # an index its own row cannot name has no incumbent, so THE INCUMBENT LOCK cannot hold it
            # and the texel moves like any other.  The no-op is exact on 240 of 240 corpus surfaces
            # precisely because this class is EMPTY there -- so it is counted and named in the census
            # rather than left as the one unlabelled way a texel can move.
            t["incumbent_unnameable"] += 1
        if s_ok and dup_flag[s]:
            t["ambiguous"] += 1
        if a == 0:
            t["cutout"] += 1
            if not c_z:
                raise RepaintError(                                        # R12
                    "%s: you painted %d texel(s) transparent, but %s carries no 0x0000 entry, so "
                    "there is no index that renders as a hole.  MEASURED: 45 of 147 lawful scenery "
                    "rows are in this class and 0 of 93 creature rows.  A hole here needs a palette "
                    "WRITE.  %s"
                    % (p, sum(1 for k in range(n) if px[4 * k + 3] == 0),
                       page.palette_name or page.name, MINT_CLUT_REASON))
            # every member of Z already renders as a hole, so the EXACT class is the whole branch and
            # the incumbent wins outright whenever it is already a hole.
            if s_hole:
                out[i] = s
                continue
            # BOTH BRANCHES: an index that renders as a hole in the editable row need not render as
            # a hole in an alternate row, so a tie inside Z splits exactly the same way.
            if len(c_z) > 1 and alt_rows:
                t["alt_checked"] += 1
                _alt_split_check(c_z, alt_rows, alt_memo, p, page, i, w)
            pick = min(c_z, key=lambda k: (_stp(words[k]) != (_stp(words[s]) if s_ok else 0), k))
            out[i] = pick
            if pick != c_z[0]:
                t["stp_decided"] += 1                   # the STP TERM changed the pick
            if s_ok and not s_hole:                     # opaque -> hole is a PUNCH; hole -> hole is
                t["cutout_punch"] += 1                  # not a crossing at all

            if s_ok and _stp(words[pick]) != _stp(words[s]):
                t["stp_changed"] += 1
            continue

        # ---- the OPAQUE branch ----------------------------------------------------------------
        t["opaque"] += 1
        if r8 == 0 and g8 == 0 and b8 == 0:
            t["opaque_black"] += 1
        c15 = KT.direct15_word(r8, g8, b8, 0)
        # THE FAST PATH IS THE NO-OP PATH.  If the incumbent is opaque and already carries exactly
        # the painted colour it is in the exact class, so it wins by the first term of the order --
        # and an unedited page never touches the palette scan at all.
        if s_ok and not s_hole and (words[s] & 0x7FFF) == c15:
            out[i] = s
            t["exact"] += 1
            # A TIE AT d^2 = 0 IS STILL A TIE, and the census line's own words are ">1 entry
            # equidistant".  Counting it only in the `dist != 0` branch would leave the class the
            # INCUMBENT LOCK works hardest on -- several entries carrying the painted colour exactly
            # -- reported nowhere.  `col_count` answers it without re-running the scan.
            if col_count.get(c15, 0) > 1:
                t["nearest_tie"] += 1
                t["exact_tie"] += 1
            continue
        key = (c15, 1)
        cand, dist = memo.get(key) or _nearest(c15, c_op, words, memo, key)
        if dist == 0:
            t["exact"] += 1
        else:
            t["approximated"] += 1
            t["_dists"].append(dist)
            dmap[i] = dist if dist < 255 else 255
        if len(cand) > 1:
            t["nearest_tie"] += 1
            if dist == 0:
                t["exact_tie"] += 1
        if len(cand) > 1 and alt_rows and not (s_ok and s in cand):
            t["alt_checked"] += 1                       # EDIT-SCOPED: the incumbent did not survive
            _alt_split_check(cand, alt_rows, alt_memo, p, page, i, w)
        if s_ok and s in cand:
            out[i] = s
        else:
            s_stp = _stp(words[s]) if s_ok else 0
            out[i] = min(cand, key=lambda k: (_stp(words[k]) != s_stp, k))
            if out[i] != cand[0]:
                t["stp_decided"] += 1                   # the STP TERM changed the pick
        if s_ok and _stp(words[out[i]]) != _stp(words[s]):
            t["stp_changed"] += 1
        if s_hole:
            t["cutout_fill"] += 1

    raw = pack4(out) if page.bpp == 4 else bytes(out)
    cen = quantize_census(page, words, t)
    cen["dmap"] = bytes(dmap)
    return raw, cen


def _nearest(c15: int, cand: Sequence[int], words: Sequence[int],
             memo: dict, key) -> Tuple[Tuple[int, ...], int]:
    """``(the ascending nearest class, its squared distance)``.

    Integer arithmetic only and the candidate list is scanned in ASCENDING INDEX ORDER, so the class
    it returns is ordered and the caller's tie-break is a total order over unique indices.

    It returns the CLASS and not a verdict about it: the caller decides tie-ness from ``len(cand)``,
    which is the same question at every distance. (A third "was the exact class multi-membered"
    element used to be returned here and read by nobody -- a value no call site spends is a value that
    cannot be wrong, which is how the d^2 = 0 tie went uncounted.)
    """
    cr, cg, cb = c15 & 0x1F, (c15 >> 5) & 0x1F, (c15 >> 10) & 0x1F
    best = 1 << 30
    hits: List[int] = []
    for i in cand:
        wd = words[i]
        dr = (wd & 0x1F) - cr
        dg = ((wd >> 5) & 0x1F) - cg
        db = ((wd >> 10) & 0x1F) - cb
        d = dr * dr + dg * dg + db * db
        if d < best:
            best, hits = d, [i]
        elif d == best:
            hits.append(i)
    out = (tuple(hits), best)
    memo[key] = out
    return out


def _alt_split_check(cand: Sequence[int], alt_rows: Sequence[AlternateRow], alt_memo: dict,
                     src, page: TexelPage, texel: int, w: int) -> None:
    """★ THE ALTERNATE-SPLIT REFUSAL -- **no acknowledge key**, and four scopings that narrow it.

    *When the incumbent does NOT survive (so this texel is a genuine edit), the surviving candidate
    set has >= 2 members, this cell is read through >= 1 alternate CLUT key, and any alternate row
    renders those candidates as >= 2 distinct words -- REFUSE.*

    THE TIE-BREAK BEHIND IT: an author's own index choice is a choice, and it is disclosed. The
    TOOL's choice, in a picture the author was never shown, must not be silently wrong. Measured over
    the corpus, **298 of 365 duplicate groups on 11 of 16 class-C cells SPLIT** under some alternate
    key -- so a tool that resolved the tie inside the editable key would, on a class-C cell, be 81.6%
    likely to be choosing a visibly different colour in the other reader's picture. There is no
    evidence which colour that reader should get, so this refuses rather than choosing: the dual-depth
    rule, one level down.

    Four scopings, each of which both judges accepted and each of which is enforced at the call site:

    1. **EDIT-SCOPED** -- the caller only reaches here when the incumbent is NOT in the candidate set,
       so a no-op and every unchanged texel are structurally exempt. Without this the gate would fire
       on the corpus's own stock bytes;
    2. **CANDIDATE-SET-SCOPED**, not group-scoped: it asks about the entries actually in contention
       for THIS texel, not about every duplicate group in the row;
    3. **CREATURE-UNREACHABLE** -- ``alternate_palette_rows`` returns ``()`` on all 93 creature pages
       by construction, so the branch cannot fire on 93 of 240 surfaces;
    4. **BOTH BRANCHES** -- it applies to the cutout branch too. An index that renders as a hole in
       the editable row need not render as a hole in an alternate row, so a tie inside ``Z`` splits
       the same way.

    ⚠ IT IS BOUNDED BY WHAT THE CONTAINER DECLARES. ``alt_rows`` can only hold alternates the ``so`` /
    GEOM derivation states, so a non-GEOM reader (a sprite, a particle) is invisible to it -- which is
    BINDING-IS-NOT-A-DRAW arriving from the palette side. The refusal says so in its own terms.
    """
    ck = tuple(cand)
    bad = alt_memo.get(ck)
    if bad is None:
        bad = None
        for alt in alt_rows:                             # derivation order, never a set's
            seen = []
            for i in ck:
                wd = alt.words[i] if i < len(alt.words) else 0
                if wd not in seen:
                    seen.append(wd)
            if len(seen) > 1:
                bad = (alt, tuple(seen))
                break
        alt_memo[ck] = bad if bad is not None else False
    if not bad:
        return
    alt, seen = bad
    raise RepaintError(
        "ALTERNATE-SPLIT TIE, %s texel (%d,%d): the colour you painted has %d equally-near entries "
        "(%s) in the editable key %s, and they render as DIFFERENT words in the alternate key %s "
        "(%s).  This cell is read through %d CLUT cell(s) THAT THE CONTAINER DECLARES (class C); the "
        "picture you painted is one of them.  MEASURED over the corpus: 298 of 365 duplicate groups "
        "on 11 of 16 class-C cells split like this.  There is no evidence which colour the other "
        "reader should get, so this REFUSES rather than choosing -- the dual-depth rule, one level "
        "down, and there is no acknowledge key.  Paint an entry that is UNIQUE in this row (the "
        "swatch marks them), or use `source =` and the indexed lane and choose the index yourself."
        % (page.name, texel % w, texel // w, len(ck), ", ".join(str(i) for i in ck),
           str(page.hazards.readers[0].clut_cell) if page.hazards and page.hazards.readers else "-",
           str(alt.clut_cell), " vs ".join("%#06x" % v for v in seen), len(alt_rows) + 1))


def _round_trip_ok(px: bytes, words: Sequence[int], w: int, h: int) -> bool:
    """THE X0-CLASS GATE, in memory: encode -> decode -> the same bytes."""
    return _read_indices(io.BytesIO(encode_indexed_png(px, words, w, h)),
                         "(in-memory round trip)", w, h, len(words)) == px


def texel_view(page: TexelPage, raw: bytes) -> Sequence[int]:
    """One cell's raw bytes as ITS OWN texel sequence -- the space the cutout law has to count in.

    The three depths are three different readings of the same block and only one of them is the
    identity: 8bpp is byte *i* = texel *i*, 4bpp is two texels per byte (low nibble first), 15bpp is
    one halfword per texel. Counting a cutout crossing in BYTE space would, at 4bpp, call one changed
    byte one changed texel and miss the second nibble entirely -- and at 15bpp it would compare halves
    of colours.
    """
    if page.bpp == 15:
        return struct.unpack_from("<%dH" % (len(raw) // 2), raw, 0)
    if page.bpp == 4:
        return unpack4(raw)
    return raw


def transparent_values(blob: bytes, page: TexelPage) -> Tuple[Tuple[int, ...], str]:
    """The values that render as a HOLE on this page, DERIVED, plus how they were derived.

    Two lanes, one law. Indexed: the alpha-0 entries of the ACTIVE palette (never assumed to be
    ``{0}`` -- under a composed CLUT edit the palette in front of us is not the stock one). Direct:
    there is no palette, so the law lands in its palette-less form and the cutout is the WORD
    ``0x0000``, derived from the values themselves.
    """
    if page.direct:
        return ((KT.DIRECT15_CUTOUT,),
                "the word 0x0000 (at direct colour the cutout is a VALUE -- there is no palette)")
    words = palette_words(blob, page)
    zeros = transparent_indices(words)
    return (zeros, "palette index %s of %s, derived from the ACTIVE %d-entry row"
            % (",".join(str(z) for z in zeros) or "(none)", page.palette_name or "this page",
               len(words)))


def write_coverage_png(px: bytes, words: Sequence[int], mask: Sequence[int], w: int, h: int,
                       path) -> str:
    """The paintable page with its NEVER-SAMPLED region hatched: green = outer pad, red = interior
    hole. Sampled texels render verbatim so the two images line up texel for texel."""
    Image = _need_pil()
    rgba = [KT.bgr555_rgba(x) for x in words]
    pad = border_flood(mask, w, h)
    out = []
    for i in range(w * h):
        x, y = i % w, i // w
        r, g, b, _a = rgba[px[i]]
        if mask[i]:
            out.append((r, g, b, 255))
            continue
        hatch = ((x + y) % 8) < 3
        key = (0, 255, 0) if pad[i] else (255, 0, 0)
        out.append(key + (255,) if hatch else (r // 4, g // 4, b // 4, 255))
    im = Image.new("RGBA", (w, h))
    im.putdata(out)
    im.save(str(path))
    return str(path)


# ============================================================ (4) THE EXPORT LANE
#: the export lanes this rung ships. ``rgba`` is named so it can REFUSE by name rather than not exist
#: -- an author who asks for it gets the measurement that rules it out, not a usage error. ``direct15``
#: is the 15bpp DIRECT-colour surface (RGBA + an explicit STP sidecar): a real lane, PROVEN OFFLINE
#: and UNCAST -- exhaustive 65,536/65,536 word identity and 26/26 real cell views, over a write
#: surface of 4-5 corpus cells, none of which sits in a container reachable from an existing bench row.
#: ``paint`` is the W6q QUANTIZE lane: an RGBA render of the page beside the exact indexed PNG, read
#: back against the row the container already carries. It writes INDICES ONLY and zero CLUT bytes,
#: which is why it can ship while ``rgba`` (on the INDEXED lane) and ``--mint-clut`` still refuse --
#: its format of record is TWO FILES, the painting plus the container's own index page, which the
#: codec reads as the incumbent. That is the same move ``direct15`` already made with its STP sidecar.
ART_LANES = ("indexed", "rgba", "direct15", "paint")


def write_paint_png(px: Sequence[int], words: Sequence[int], w: int, h: int, path) -> str:
    """One page -> the EDITABLE RGBA8 file of the paint lane.

    RGB is the picture as the kit already renders it to the author (``bgr555_rgba`` -- the decode
    ``_cell_image``, ``write_coverage_png`` and every preview use), and **ALPHA IS THE CUTOUT and it
    is AUTHORITATIVE**: the codec selects from the transparent set when alpha is 0 and from everything
    else when it is 255, so every cutout crossing in the result is one the author drew.

    The file is rendered with the SCALE decode and read back with the SHIFT -- two different maps
    whose composition is the identity for all 32 five-bit values. That is not a coincidence to rely on
    quietly; it has its own gate and its own test, and the manifest records which decode was used.
    """
    Image = _need_pil()
    pal = [KT.bgr555_rgba(x) for x in words]
    im = Image.new("RGBA", (w, h))
    im.putdata([pal[i] if i < len(pal) else (0, 0, 0, 0) for i in px[:w * h]])
    im.save(str(path))
    return str(path)


def write_swatch_png(words: Sequence[int], path, *, alt_rows: Sequence["AlternateRow"] = (),
                     patch: int = 8, per_row: int = 16) -> str:
    """This page's palette as an 8x8 patch per entry, in INDEX ORDER -- the paint lane's own map.

    THE MARKS ARE THE POINT, and they name exactly the two classes the codec's refusals turn on:

    * a **UNIQUE** entry (no other entry in the row carries its word) gets a white border. Painting
      one of those colours can never produce a tie, so it can never trip the alternate-split refusal;
    * an entry in a duplicate group that **SPLITS under some alternate key** gets a magenta border.
      Those are precisely the entries :data:`R7` refuses a genuine edit onto;
    * everything else -- a duplicate that renders identically in every declared key -- is unmarked.

    A transparent entry is drawn as a checker rather than as black, because ``0x0000`` renders black
    and "the hole" and "an entry that happens to be black" are the one pair an author must not
    confuse.
    """
    Image = _need_pil()
    n = len(words)
    cols = min(per_row, n)
    rows = (n + cols - 1) // cols
    im = Image.new("RGBA", (cols * patch, rows * patch), (24, 24, 28, 255))
    dup: Dict[int, List[int]] = {}
    for i, wd in enumerate(words):
        dup.setdefault(wd, []).append(i)
    split: Set[int] = set()
    for wd, members in dup.items():
        if len(members) < 2:
            continue
        for alt in alt_rows:
            seen = {alt.words[i] if i < len(alt.words) else 0 for i in members}
            if len(seen) > 1:
                split.update(members)
                break
    px = im.load()
    for i, wd in enumerate(words):
        r, g, b, a = KT.bgr555_rgba(wd)
        x0, y0 = (i % cols) * patch, (i // cols) * patch
        mark = ((255, 255, 255, 255) if len(dup[wd]) == 1 else
                ((255, 0, 220, 255) if i in split else None))
        for dy in range(patch):
            for dx in range(patch):
                if a == 0:                               # the hole: a checker, never a black square
                    v = 60 if ((dx // 2 + dy // 2) % 2) else 110
                    c = (v, v, v, 255)
                else:
                    c = (r, g, b, 255)
                edge = dx in (0, patch - 1) or dy in (0, patch - 1)
                px[x0 + dx, y0 + dy] = (mark if (edge and mark) else c)
    im.save(str(path))
    return str(path)


def _cell_image(blob: bytes, page: TexelPage, words: Optional[Sequence[int]] = None):
    """One page-cell -> a PIL RGBA image in whatever key the page's own depth implies. Read-only
    rendering for previews; the EDITABLE files are written by the per-depth codecs."""
    Image = _need_pil()
    raw = blob[page.page_offset:page.page_offset + page.page_bytes]
    im = Image.new("RGBA", (page.w, page.h))
    if page.bpp == 15:
        im.putdata([KT.direct15_split(wd)[:3] + (0 if wd == KT.DIRECT15_CUTOUT else 255,)
                    for wd in struct.unpack_from("<%dH" % (page.w * page.h), raw, 0)])
        return im
    idx = unpack4(raw) if page.bpp == 4 else raw
    pal = [KT.bgr555_rgba(x) for x in (words if words is not None else palette_words(blob, page))]
    im.putdata([pal[i] if i < len(pal) else (0, 0, 0, 0) for i in idx[:page.w * page.h]])
    return im


def _spill_sheet(blob: bytes, m: BoundModel, by_cell: Dict[Tuple[int, int], TexelPage],
                 path) -> Tuple[str, List[str], List[str]]:
    """THE STITCHED PER-MODEL PREVIEW (read-only): the whole picture a spilling model reads, laid out
    over the cells it is made of.

    On a CO-TRANSFORM cell the sheet shows ONE writer's upload (the first in ``page_cells`` order),
    because several genuinely different pictures cannot occupy one preview -- the manifest's ``cells``
    list names every writer record, which is where that join stays lossless.

    The author *sees* the picture and *edits* the cells -- which is the honest shape of the constraint,
    because on the EFFECTIVE cover this sheet is stitched from, **58 of the 60 spilling bindings read
    a picture strictly wider than one page** (median ``u`` span 160 texels) and the two that do not
    still cross a page boundary. A column NOTHING uploads renders as a hatch-free dark block and
    is NAMED in the return value: **11 corpus bindings** sample VRAM no writer in their container
    fills -- 10 on ef390 (15bpp), where the residual is presumably another effect's, and one on ef082
    (GEOM ``0x1dcd8``) where the DISPLACEMENT put it there. Either way there is nothing to repaint.
    """
    Image = _need_pil()
    # W6b-3 (iv): the picture a model READS is its EFFECTIVE cover -- stitching the bound one
    # would hand a displaced author a preview of cells their model does not sample.
    cols = sorted({cx for cx, _cy in m.effective_cover})
    rows = sorted({cy for _cx, cy in m.effective_cover})
    tw = cell_texel_w(m.bpp)
    sheet = Image.new("RGBA", (len(cols) * tw, len(rows) * CELL_LINES), (18, 18, 22, 255))
    unwritten: List[str] = []
    unrendered: List[str] = []
    for cell in sorted(m.effective_cover):
        page = by_cell.get(cell)
        box = (cols.index(cell[0]) * tw, rows.index(cell[1]) * CELL_LINES)
        if page is None:
            unwritten.append("x%d_y%d" % cell)
            continue
        try:
            sheet.paste(_cell_image(blob, page), box)
        except RepaintError as e:                    # e.g. a reader naming an undeclared CLUT cell
            unrendered.append("%s (%s)" % (page.name, e))
    sheet.save(str(path))
    return (str(path), unwritten, unrendered)


def export_art(blob: bytes, effect: int, out_dir=None, *, source: str = "", lane: str = "indexed",
               overlays: bool = True, scaffold: bool = True,
               displacement_ack: bool = False) -> dict:
    """Decode every addressable page to a paintable PNG + its overlays + the manifest.

    TWO SURFACES SINCE W6b-1. The id-4 CREATURE pages (W6a, always 8bpp indexed) and the SCENERY
    page-cells whose depth the container states, at 4 / 8 bpp under ``lane="indexed"`` and at 15 bpp
    under ``lane="direct15"``. Everything the scenery derivation refuses is named in the manifest and
    printed as a commented block in the scaffold, because on this surface the refusals ARE the shape:
    2,385 of 2,572 corpus cells declare no reader at all.

    Three per-cell rules, each forced rather than chosen:

    * **the display palette** -- a cell read by N bindings at ONE depth through DIFFERENT CLUT cells
      (class C, 25 corpus cells; widest case 27 bindings over 2 CLUTs) is editable in the
      LOWEST-ADDRESSED binding's key, and every other key is written as a READ-ONLY
      ``<cell>.as-x{X}_y{Y}.png`` alternate view of the SAME index bytes. Both are NAMED in the
      manifest -- an author who never learns the second key would tune a colour they cannot see;
    * **the spill preview** -- a model whose picture crosses a column gets a stitched read-only
      ``spill.<geom>.png``, so the edit unit stays the CELL while the judgement unit is the picture;
    * **both directions of every join** -- the manifest records which cells a model reads AND which
      models read a cell, because a one-way index makes the second question a re-derivation.

    Every destination goes through :func:`ff9mapkit.summons.export.assert_local_only` -- decoded pages
    are Square-Enix content, so the repo, any ``StreamingAssets`` tree and the install are refused with
    no ``--force``. The manifest records the stock sha256 and, per page, every number a
    ``[[reskin.texel]]`` guard states; :func:`build` re-reads it and refuses a pack whose container is
    not the one the art came out of.
    """
    if lane not in ART_LANES:
        raise RepaintError("unknown art lane %r -- this rung ships %s"
                           % (lane, ", ".join(ART_LANES)))
    if lane == "rgba":
        raise RepaintError(
            "the `%s` export lane is W6b and refuses rather than half-works.  MEASURED over the 93 "
            "stock creature pages: the INDEXED round trip is byte-identical 93/93, while an RGBA "
            "round trip that painted nothing at all still moves 1,844 of 16,384 texels on ef251 part "
            "0 (8.31%% of the corpus's palette entries are duplicates of the full 16-bit word, STP "
            "included) -- and the exact-recovery rate ranges 88.75%%..99.24%% per page BEFORE anyone "
            "paints.  A lane whose no-op is not a no-op cannot carry a byte-identity gate.  (This "
            "refusal is about the INDEXED lane's exact recovery and is unchanged by W6b-1; the 15bpp "
            "DIRECT lane is a different question and ships as `direct15`.)  %s"
            % (lane, INDEXED_RGBA_REASON))
    # ⚠ THE LINE A NEW LANE MUST NOT FORGET.  A lane that left this reading `== "indexed"` would
    # silently export SCENERY ONLY -- no error, no empty directory, just 93 creature pages missing.
    pages = creature_texel_pages(blob) if lane in ("indexed", "paint") else []
    scen: List[TexelPage] = []
    refusals: List[CellRefusal] = []
    scen_error = ""
    try:
        scen, refusals = scenery_surface(blob, effect, channels=EDIT_CHANNELS,
                                        displacement_ack=displacement_ack)
    except (RS.ReskinError, EC.ContainerError) as e:               # surfaced, never swallowed
        scen_error = "the scenery derivation REFUSED on this container: %s: %s" % (type(e).__name__,
                                                                                   e)
    refused_names = {r.name for r in refusals if r.klass in _EXPORT_BLOCKING}
    want = (15,) if lane == "direct15" else (4, 8)
    cells = [p for p in scen if p.bpp in want and p.name not in refused_names]
    if not pages and not cells:
        raise RepaintError(
            "ef%03d exports no texel art in the `%s` lane -- %s\n  scenery: %d page-cell(s) declare a "
            "depth, %d refused by name, %d in this lane's depth(s) %s.%s"
            % (effect, lane, creature_refusal(blob) or "(creature pages are not in this lane)",
               len(scen), len(refusals), len(cells), "/".join(str(d) for d in want),
               ("  " + scen_error) if scen_error else ""))
    out = Path(export.assert_local_only(out_dir if out_dir else
                                        Path(staging_root(effect)) / "art"))
    out.mkdir(parents=True, exist_ok=True)
    stock_sha = _sha(blob)
    entries = []
    written: List[str] = []
    for p in pages:
        words = palette_words(blob, p)
        px = blob[p.page_offset:p.page_offset + p.page_bytes]
        png = out / ("%s.png" % p.name)
        written.append(write_indexed_png(px, words, p.w, p.h, png))
        # BOTH FORMATS SHIP SIDE BY SIDE, per page, because the choice is PER ROW and not per export:
        # a spec may paint one part in RGBA and hand-edit another in index space, and an author who
        # changes their mind flips a commented line instead of re-exporting.
        paint_png = swatch_png = ""
        if lane == "paint":
            paint_png = write_paint_png(px, words, p.w, p.h, out / ("%s.paint.png" % p.name))
            swatch_png = write_swatch_png(words, out / ("%s.swatch.png" % p.name))
            written += [paint_png, swatch_png]
        cov = coverage(blob, p.index) if overlays else Coverage(False, "overlays disabled")
        cov_png = ""
        if cov.available and overlays:
            cov_png = write_coverage_png(px, words, cov.mask, p.w, p.h,
                                         out / ("%s.coverage.png" % p.name))
            written.append(cov_png)
        zeros = transparent_indices(words)
        entries.append({
            "name": p.name, "index": p.index, "png": os.path.basename(str(png)),
            "paint_png": os.path.basename(paint_png) if paint_png else "",
            "swatch_png": os.path.basename(swatch_png) if swatch_png else "",
            "render_key": PAINT_RENDER_KEY if paint_png else "",
            "coverage_png": os.path.basename(cov_png) if cov_png else "",
            "page_offset": p.page_offset, "page_bytes": p.page_bytes, "wh": [p.w, p.h],
            "bpp": p.bpp, "clut_offset": p.clut_offset, "clut_entries": p.clut_entries,
            "palette_name": p.palette_name, "tpage": p.tpage, "clut": p.clut,
            "v_offset": p.v_offset, "vram": list(p.vram),
            "covered_texels": cov.covered if cov.available else None,
            "dead_texels": cov.dead if cov.available else None,
            "interior_holes": cov.interior_holes if cov.available else None,
            "coverage_available": cov.available,
            "coverage_reason": cov.reason,
            "faces": cov.faces if cov.available else None,
            "distinct_indices": len(set(px)),
            "transparent_indices": list(zeros),
            "index0_texels": sum(1 for x in px if x in zeros),
            "page_sha256": _sha(px),
        })
    # ---- the SCENERY page-cells (W6b-1) ----------------------------------------------------------
    _pm_cache: List[RS.PaletteMap] = []

    def _pmap() -> RS.PaletteMap:
        if not _pm_cache:                            # resolved once per export, never per alternate
            _pm_cache.append(RS.palette_map(blob, effect=effect))
        return _pm_cache[0]

    scen_entries: List[dict] = []
    #: VRAM cell -> the page RENDERED for it in a preview.  One writer per cell, the first in
    #: ``page_cells`` order -- a co-transform cell has several genuinely different pictures and a
    #: preview has to pick one; ``names_by_cell`` below keeps the join lossless.
    by_cell: Dict[Tuple[int, int], TexelPage] = {}
    names_by_cell: Dict[Tuple[int, int], List[str]] = {}
    for p in scen:
        by_cell.setdefault(p.cell, p)
        names_by_cell.setdefault(p.cell, []).append(p.name)
    for p in cells:
        hz = p.hazards
        raw = blob[p.page_offset:p.page_offset + p.page_bytes]
        png = out / ("%s.png" % p.name)
        alts: List[dict] = []
        paint_png = swatch_png = ""
        if p.bpp == 15:
            f_png, f_stp = write_direct_png(raw, p.w, p.h, png)
            written += [f_png, f_stp]
            zeros = direct_transparent(raw)
            stp_share = sum(1 for wd in struct.unpack_from("<%dH" % (p.w * p.h), raw, 0)
                            if wd >> 15) / float(p.w * p.h)
        else:
            words = palette_words(blob, p)
            if p.bpp == 4:
                written.append(write_indexed4_png(raw, words, p.w, p.h, png))
            else:
                written.append(write_indexed_png(raw, words, p.w, p.h, png))
            zeros = transparent_indices(words)
            stp_share = None
            # class C: every OTHER key this cell is read in, as a read-only view of the SAME bytes.
            # ONE derivation, shared with the build's alternate-split refusal -- a second copy here
            # would let the picture the author is shown and the picture the gate protects drift.
            alt_rows = alternate_palette_rows(blob, p, _pmap())
            for alt in alt_rows:
                ap = out / ("%s.as-x%d_y%d.png" % (p.name, alt.clut_cell[0], alt.clut_cell[1]))
                if p.bpp == 4:
                    written.append(write_indexed4_png(raw, alt.words, p.w, p.h, ap))
                else:
                    written.append(write_indexed_png(raw, alt.words, p.w, p.h, ap))
                alts.append({"clut_cell": list(alt.clut_cell), "palette_name": alt.palette_name,
                             "png": os.path.basename(str(ap)), "read_only": True})
            if lane == "paint":
                paint_png = write_paint_png(texel_view(p, raw), words, p.w, p.h,
                                            out / ("%s.paint.png" % p.name))
                swatch_png = write_swatch_png(words, out / ("%s.swatch.png" % p.name),
                                              alt_rows=alt_rows)
                written += [paint_png, swatch_png]
        scen_entries.append({
            "name": p.name, "cell": list(p.cell), "writer": hz.writer, "png": os.path.basename(
                str(png)),
            "stp_png": (os.path.basename(str(stp_sidecar_path(png))) if p.bpp == 15 else ""),
            "paint_png": os.path.basename(paint_png) if paint_png else "",
            "swatch_png": os.path.basename(swatch_png) if swatch_png else "",
            "render_key": PAINT_RENDER_KEY if paint_png else "",
            "alternates": alts,
            "page_offset": p.page_offset, "page_bytes": p.page_bytes, "wh": [p.w, p.h],
            "bpp": p.bpp, "clut_offset": p.clut_offset, "clut_entries": p.clut_entries,
            "palette_name": p.palette_name, "tpage": p.tpage, "clut": p.clut,
            "vram": list(p.vram),
            "covered_halfwords": hz.covered_halfwords,
            "transparent_texels": len(zeros),
            "stp_share": stp_share,
            "writers": [{"tag": w.tag, "kind": w.kind, "offset": w.off, "bytes": w.nbytes,
                         "provenance": w.provenance} for w in hz.writers],
            "readers": [{"geom": r.geom, "bpp": r.bpp, "clut_cell": (list(r.clut_cell)
                                                                    if r.clut_cell else None),
                         "palettes": list(r.palettes), "columns": list(r.columns),
                         "own_column": r.own_column, "halfwords_here": r.halfwords_here}
                        for r in hz.readers],
            "spill_in": [r.geom for r in hz.spill_in],
            "spill_out": list(hz.spill_out),
            # W6b-3 (iii): the SECOND-ARRAY disclosure, per reader -- the MEASURED `swapped` reading
            # and the RETIRED `original` one, both recorded, neither applied.
            # `second_array_all_readers` is the refusal's own predicate, recorded beside the evidence
            # so a manifest can be audited without re-deriving it.
            "second_array_all_readers": hz.every_reader_moves,
            # W6b-3 (iv): the ADOPTED answer, and the classes the effective cover mints.
            "displacement_model": DISPLACEMENT_MODEL,
            "readership": p.readership,
            "displaced_readerless": hz.displaced_readerless,
            "displaced_substituted": hz.displaced_substituted,
            "displaced_gained": hz.displaced_gained,
            "displaced_changed": hz.displaced_changed,
            "display_binding_moved": hz.display_binding_moved,
            "bound_readers": [r.geom for r in hz.bound_readers],
            "novel_reach": list(hz.novel_reach),
            "second_array": [
                {"geom": n.geom, "record_at": n.record_at, "a": n.a, "b": n.b, "bpp": n.bpp,
                 "u": list(n.u), "bound_column": n.bound_column, "du": n.a, "dv": n.b,
                 "bound_cells": [list(c) for c in n.bound_cells],
                 "effective_cells": [list(c) for c in n.effective_cells],
                 "swapped": {"texels": n.swapped_texels, "columns": list(n.swapped_columns),
                             "moved": n.swapped_moved},
                 "original": {"texels": n.original_texels, "columns": list(n.original_columns),
                              "moved": n.original_moved}}
                for n in hz.second_array],
            "program": hz.program, "program_evidence": hz.program_evidence,
            "program_cell": hz.program_cell,
            "lower_half": hz.lower_half, "provenance": hz.provenance,
            "hazards": list(hz.names),
            "page_sha256": _sha(raw),
        })

    # ---- the MODEL direction of the join, + the stitched spill previews --------------------------
    model_entries: List[dict] = []
    if scen:
        for m in bound_models(blob):
            if not m.effective_cover:
                continue
            # THE UNWRITTEN COLUMN, derived once and used by both the preview and the record: 11
            # corpus bindings on the EFFECTIVE cover (10 on ef390, one on ef082 that the measured
            # displacement moved onto unwritten VRAM) sample VRAM no writer in their own container
            # fills, so there is genuinely nothing there to repaint.
            unwritten = ["x%d_y%d" % c for c in sorted(m.effective_cover) if c not in by_cell]
            spill_png, unrendered = "", []
            if m.effective_spills:
                sp, unwritten, unrendered = _spill_sheet(
                    blob, m, by_cell, out / ("spill.geom%#x.png" % m.geom))
                written.append(sp)
                spill_png = os.path.basename(sp)
            model_entries.append({
                "geom": m.geom, "slot": m.slot, "tpage": m.tpage, "bpp": m.bpp,
                "clut_cell": (list(m.clut_cell) if m.clut_cell else None),
                "clut_entries": m.clut_entries, "faces": m.faces,
                "u": list(m.u), "v": list(m.v), "columns": list(m.columns),
                # EVERY writer record of every cell it reads -- a co-transform cell is several names
                # and naming one of them would make the second upload invisible from this side too
                # READERSHIP -> EFFECTIVE.  `columns` above is the record's own statement; these
                # are the cells the model SAMPLES, which is what an author has to supply art for.
                "cells": [n for c in sorted(m.effective_cover) for n in names_by_cell.get(c, ())],
                "effective_columns": list(m.effective_columns), "mover": list(m.mover or (0, 0)),
                "readership": ("displaced" if m.displaced else "bound"),
                "cells_no_writer": unwritten, "cells_not_rendered": unrendered,
                "spills": m.spills, "effective_spills": m.effective_spills,
                "spill_png": spill_png})

    # W7 L6 (V1 F4): the protected rect set belongs at PAINT time, not only at plan time -- the
    # workflow is export-art -> paint -> plan, and an author who first learns of the animated
    # window after painting learns it as a refusal.
    res_ta = TA.read(blob)
    prot = TA.protected_rects(blob) if res_ta.parsed else {}
    man = {"tool": "ff9mapkit summon-reskin export-art", "lane": lane, "effect": int(effect),
           "stock_sha256": stock_sha, "source": source or "(caller-supplied bytes)",
           "container_bytes": len(blob), "parts": entries,
           "scenery": scen_entries, "models": model_entries,
           "scenery_error": scen_error,
           "program": {"class": program_class(effect)[0], "evidence": program_class(effect)[1],
                       "moveimage_cell": (list(MOVEIMAGE_HARD_CELLS[int(effect)])
                                          if int(effect) in MOVEIMAGE_HARD_CELLS else None)},
           "refused": [{"name": r.name, "cell": list(r.cell), "class": r.klass, "reason": r.reason}
                       for r in refusals],
           "texanim": {"armed": res_ta.armed,
                       "decodes": (res_ta.parsed if res_ta.armed else None),
                       "lines": list(TA.describe(blob)),
                       "protected": {str(part): [[r.x, r.y, r.w, r.h] for r in rects]
                                     for part, rects in sorted(prot.items())}}}
    from .. import fsutil
    mpath = out / ART_MANIFEST
    fsutil.atomic_write_text(mpath, json.dumps(man, indent=2), encoding="utf-8", newline="\n")
    written.append(str(mpath))
    if scaffold:
        spath = out / SCAFFOLD_NAME
        fsutil.atomic_write_text(spath, scaffold_text(effect, stock_sha, entries, protected=prot,
                                                      texanim_armed=res_ta.armed,
                                                      scenery=scen_entries, models=model_entries,
                                                      refused=refusals, lane=lane, blob=blob),
                                 encoding="utf-8", newline="\n")
        written.append(str(spath))
    man["out_dir"] = str(out)
    man["files"] = written
    return man


def scaffold_text(effect: int, stock_sha: str, entries: Sequence[dict], *,
                  protected: Optional[Dict[int, list]] = None,
                  texanim_armed: bool = False,
                  scenery: Optional[Sequence[dict]] = None,
                  models: Optional[Sequence[dict]] = None,
                  refused: Optional[Sequence["CellRefusal"]] = None,
                  lane: str = "indexed", blob: bytes = b"") -> str:
    """A COMPLETE, guarded ``[[reskin.texel]]`` scaffold, emitted from the derivation.

    Every ``expect_*`` is emitted rather than typed, so a guard cannot start life disagreeing with the
    bytes; every row starts ``enabled = false``, so the first build is provably a no-op and the author
    switches on one page at a time.  ``protected`` (part -> texanim rects, W7 L6) is stated on the
    row it concerns, so the author reads it BEFORE painting, not as a later refusal.

    W6b-1 adds three things, and all three exist because **the scaffold is where a refusal teaches**:

    * per scenery row, ``expect_bpp`` and ``expect_cell`` -- the depth is STATED by the author and
      CHECKED against the ``so`` derivation (:func:`assert_expect_bpp`), never chosen, because the
      same 0x4000 bytes are three differently-shaped pictures;
    * the CO-TRANSFORM writer list on every multi-writer cell and the NAME-EVERY-COLUMN cell list on
      every spilling model -- the two obligations whose whole remedy is *name them all*;
    * a commented block naming **every REFUSED cell with its reason**. On this surface that block is
      the larger half by two orders of magnitude, and a cell that merely failed to appear would teach
      nothing at all.
    """
    protected = protected or {}
    paint = lane == "paint"

    def _src_lines(e: dict) -> List[str]:
        """The ``source`` / ``source_paint`` pair, with exactly ONE of them live.

        Both are emitted, one commented, so the lane is a one-character switch rather than a
        re-export -- and so `source` + `source_paint` on one row stays a *stateable* contradiction
        that refuses by name, which a boolean spelling could never be.
        """
        if not paint or not e.get("paint_png"):
            return ['source = "%s"' % e["png"]]
        return ['# source     = "%s"     # the EXACT lane: indices, byte-identical round trip'
                % e["png"],
                'source_paint = "%s"   # the QUANTIZE lane: RGBA, approximated onto THIS row'
                % e["paint_png"],
                "acknowledge_quantize = false   # \"I accept that my colours are APPROXIMATED\""]

    def _paint_notes(e: dict) -> List[str]:
        """The three MEASURED comment lines a paint row gets -- numbers from the container, never
        from a document. The scaffold is where a refusal teaches instead of blocking."""
        if not paint or not e.get("paint_png") or not blob or not e.get("clut_entries"):
            return []
        words = struct.unpack_from("<%dH" % e["clut_entries"], blob, e["clut_offset"])
        zeros = transparent_indices(words)
        live = sum(1 for w in words if w)
        distinct = len({w & 0x7FFF for w in words if w})
        dup = {}
        for i, wd in enumerate(words):
            dup.setdefault(wd, []).append(i)
        raw = blob[e["page_offset"]:e["page_offset"] + e["page_bytes"]]
        idx = unpack4(raw) if e["bpp"] == 4 else raw
        ntex = e["wh"][0] * e["wh"][1]
        on_dup = sum(1 for v in idx[:ntex] if v < len(words) and len(dup[words[v]]) > 1)
        out = ["# measured: %d live entries, %d distinct colours; a fixed CLUT is a subset of the "
               "32,768-colour cube" % (live, distinct)]
        if zeros:
            out.append("# measured: transparent entry at index %s (%d of %d) -- alpha 0 in your paint "
                       "file lands there" % (",".join(str(z) for z in zeros), len(zeros), len(words)))
        else:
            out += ["# ** NO TRANSPARENT ENTRY on this row.  Painting ANY texel alpha-0 REFUSES (R12):",
                    "#    there is no index that renders as a hole here.  MEASURED: 45 of 147 lawful",
                    "#    scenery rows are in this class and 0 of 93 creature rows.  A hole needs a",
                    "#    palette WRITE, and --mint-clut is deferred."]
        out += ["# measured: %d of %d texels (%.1f%%) sit on a DUPLICATE word -- repainting them"
                % (on_dup, ntex, 100.0 * on_dup / max(1, ntex)),
                "#           exactly keeps the stock index (THE INCUMBENT LOCK); repainting them to a",
                "#           NEW colour with >1 equally-near entry REFUSES on a class-C cell (R7)."]
        return out

    L = ["# AUTO-SCAFFOLDED by `ff9mapkit summon-reskin export-art --ef %d%s`."
         % (effect, " --art-lane paint" if paint else ""),
         "# Every number is DERIVED from the container's own id-4 header.  Two kinds of line only:",
         "#   * GUARDS (`expect_*`, `expect_sha256`) -- what the derivation MUST find.  They refuse;",
         "#     they instruct nothing.  Re-export rather than retyping them.",
         "#   * AUTHORED DECISIONS (`source` / `source_paint`, `enabled`, the acknowledgements).",
         "#"]
    if paint:
        L += ["# THE PAINT LANE.  Edit `<name>.paint.png` in any RGBA editor.  ALPHA IS THE CUTOUT and",
              "# it is authoritative (0 or 255 only).  COLOUR IS APPROXIMATED onto the row this",
              "# container already carries -- this lane writes ZERO CLUT bytes.  `<name>.png` (indexed)",
              "# is also here and is EXACT: use it, and `source =`, for precise work.",
              "# `<name>.swatch.png` marks the entries that are UNIQUE in the row (safe to repaint onto",
              "# anywhere) and, in magenta, the ones a class-C alternate key renders differently."]
    else:
        L += ["# Paint the `<name>.png` files IN INDEX SPACE (a P-mode editor), keeping the file name -",
              "# the name is the contract."]
    L += ["# `<name>.coverage.png` hatches the never-sampled pad: paint",
          "# inside the island, or the edit is inert (reported, never fatal).",
          "",
         "[reskin]",
         "effect = %d" % effect,
         'label  = "ef%03d-texel-scaffold"' % effect,
         '# the drift guard: sha256 of the pristine stock container in YOUR install.  A HASH, not',
         '# data -- no stock byte is committable.',
         'expect_sha256 = "%s"' % stock_sha,
         ""]
    for e in entries:
        cov = ("%d of %d texels sampled (%.1f%%), %d dead, %d interior hole(s)"
               % (e["covered_texels"], e["wh"][0] * e["wh"][1],
                  100.0 * e["covered_texels"] / max(1, e["wh"][0] * e["wh"][1]),
                  e["dead_texels"], e["interior_holes"])
               if e["coverage_available"] else "coverage UNAVAILABLE (%s)" % e["coverage_reason"])
        L += ["[[reskin.texel]]",
              'name = "%s"' % e["name"]]
        L += _src_lines(e)
        L += ["expect_page_offset = %#08x" % e["page_offset"],
              "expect_page_bytes  = %d" % e["page_bytes"],
              "expect_page_wh     = [%d, %d]" % tuple(e["wh"]),
              "enabled = false",
              "acknowledge_cutout_reshape = false",
              '# palette_from = "%s"   # optional cross-reference; omitted = the STOCK palette,'
              % e["palette_name"],
              "#                              0 CLUT bytes touched (this rung's default).",
              "# measured: %s" % cov,
              "# measured: %d distinct indices, %d transparent texels at index %s"
              % (e["distinct_indices"], e["index0_texels"],
                 ",".join(str(i) for i in e["transparent_indices"]) or "-")]
        L += _paint_notes(e)
        rects = protected.get(e["index"])
        if rects:
            L += ["# TEXANIM PROTECTED RECTS on this part (W7): %s -- one clip family = a live"
                  % "  ".join(str(r) for r in rects),
                  "# window + its source frames.  Reach ALL of a family or NONE of it, or the build",
                  "# refuses naming the siblings (`acknowledge_texanim_frames = true` overrides)."]
        elif texanim_armed:
            L += ["# texanim is armed on this container but names no rect on this part."]
        L += [""]

    for e in (scenery or []):
        L += ["[[reskin.texel]]",
              'name = "%s"' % e["name"]]
        L += _src_lines(e)
        L += ["expect_page_offset = %#08x" % e["page_offset"],
              "expect_page_bytes  = %d" % e["page_bytes"],
              "expect_page_wh     = [%d, %d]" % tuple(e["wh"]),
              "expect_bpp         = %d   # STATED by you, CHECKED against the container's own `so`"
              % e["bpp"],
              "#                        record.  The SAME %d bytes are %d texels wide at 4bpp, %d at"
              % (e["page_bytes"], cell_texel_w(4), cell_texel_w(8)),
              "#                        8bpp and %d at 15bpp -- a wrong depth packs to exactly the"
              % cell_texel_w(15),
              "#                        right byte count and paints the wrong picture.",
              "expect_cell        = [%d, %d]   # the VRAM page-cell this name resolves to"
              % tuple(e["cell"]),
              "enabled = false",
              "acknowledge_cutout_reshape = false"]
        # W6b-3 (iii): the ack is emitted ONLY on a firing row -- an acknowledgement offered on every
        # row of every container would be a key nobody reads by the third scaffold.
        if (e.get("second_array_all_readers") or e.get("displaced_readerless")
                or e.get("displaced_substituted")):
            L += ["%s = false" % DA.ACK_MOVER_KEY]
        if e["bpp"] == 15:
            L += ['# 15bpp DIRECT colour: no palette at all.  Edit "%s" (RGB authoritative, alpha =' %
                  e["png"],
                  '# the cutout, CHECKED not read) TOGETHER WITH "%s" (bit 15, authoritative).'
                  % e["stp_png"],
                  "# measured: %d of %d texels are cutouts (word 0x0000); STP set on %.1f%%"
                  % (e["transparent_texels"], e["wh"][0] * e["wh"][1],
                     100.0 * (e["stp_share"] or 0.0))]
        else:
            L += ['# palette_from = "%s"   # DISPLAY only -- this lane writes 0 CLUT bytes.'
                  % e["palette_name"]]
            for a in e["alternates"]:
                L += ["# ALSO READ IN CLUT %s (%s) -- read-only view of the SAME index bytes:"
                      % (str(tuple(a["clut_cell"])), a["palette_name"]),
                      "#   %s" % a["png"],
                      "#   An edit here changes BOTH pictures.  The editable file above is in the",
                      "#   LOWEST-ADDRESSED binding's key; this one only shows you the other."]
        L += _paint_notes(e)
        L += ["# measured: %d of %d halfwords in this cell are sampled by some model"
              % (e["covered_halfwords"], RS.PAGE_CELL_W * CELL_LINES),
              "# writer: %s" % e["provenance"]]
        if len(e["writers"]) > 1:
            L += ["# CO-TRANSFORM: %d writers upload this VRAM cell.  Name EVERY one with its own"
                  % len(e["writers"]),
                  "#   art and say `acknowledge_cotransform = true`; 0 of the corpus's 156 writer",
                  "#   pairs is byte-identical, so repainting one leaves the others stock and the",
                  "#   cast flickers between two pictures.  The writers:"]
            L += ["#     %s  @%#08x  (%d B)" % (w["tag"], w["offset"], w["bytes"])
                  for w in e["writers"]]
        for r in e["readers"]:
            L.append("# reader GEOM %#x  %dbpp  CLUT %s %s  %d halfword(s) here"
                     % (r["geom"], r["bpp"], str(tuple(r["clut_cell"])) if r["clut_cell"] else "-",
                        "/".join(r["palettes"]) or "(no declared upload)", r["halfwords_here"]))
            if not r["own_column"]:
                L.append("#   SPILLS IN: its own column is %d, so a PAGE-scope edit here silently"
                         % r["columns"][0])
                L.append("#   edits a model this cell does not name.  The edit unit is the MODEL.")
        if len(e["readers"]) > 1:
            L.append("# SHARED READ: this one edit changes %d models.  Disclosure, not a refusal."
                     % len(e["readers"]))
        if e["spill_out"]:
            L.append("# SPILL-OUT: this cell's own reader(s) also sample column(s) %s -- name every"
                     % ", ".join(str(c) for c in e["spill_out"]))
            L.append("#   one of them, or the author is handed half a picture.")
        # ---- W6b-3 (iii): THE SECOND-ARRAY DISCLOSURE.  Printed only where the class FIRES, the
        # MEASURED reading named as such beside the retired one, and the page unchanged -- the
        # sentence an author needs BEFORE they paint, not after the playtest.
        # ---- W6b-3 (iv): THE ADOPTED READING.  Printed on any row the effective cover moved,
        # and printed FIRST as a refusal an author must lift rather than a note they may skip.
        if e.get("displaced_readerless") or e.get("displaced_substituted"):
            L.append("# ** THIS CELL IS REFUSED AS `%s` AND YOU HAVE ACKNOWLEDGED IT."
                     % ("displaced-readerless" if e.get("displaced_readerless")
                        else "displaced-readership-substituted"))
            L.append("#   Under the MEASURED displacement (MODEL %s) no `so` reader this kit can"
                     % e.get("displacement_model", DISPLACEMENT_MODEL))
            L.append("#   attribute samples these bytes.  The bound reader(s) %s left; %s."
                     % (", ".join("GEOM %#x" % g for g in e.get("bound_readers", ()))
                        or "(none)",
                        ("%s displaced onto it instead"
                         % ", ".join("GEOM %#x" % r["geom"] for r in e["readers"]))
                        if e["readers"] else "nothing arrived"))
            _nr = e.get("novel_reach") or [0, 0]
            L.append("#   REACH: this container also carries %d non-zero pair(s) on MULTI-PART"
                     % _nr[1])
            L.append("#   record(s), which NOTHING here models -- so read the verdict as 'no reader")
            L.append("#   this kit can attribute', never as 'nothing reads it'.")
            # ★ THE ACK LEDGER, AT THE ONE PLACE AN AUTHOR MEETS THE ACKNOWLEDGED PAGE.  The key
            # lifts the REFUSAL, not the guarantee -- and the picture above is the FALLBACK's, which
            # is not always the picture the pre-adoption kit handed back.
            L.append("#   ** AND WHAT YOU ARE HOLDING IS THE FALLBACK, NOT YOUR PAGE BACK: the PNG")
            L.append("#   above is whatever channel still speaks for this cell, not the departed")
            L.append("#   reader's rendering.  MEASURED over the 55 corpus names in these two")
            L.append("#   classes: 39 come back IDENTICAL, 6 come back as a DIFFERENT PICTURE (four")
            L.append("#   of them 4bpp read back as 8bpp -- same bytes, half the width, a 256-entry")
            L.append("#   key instead of a 16-entry one), and 10 come back with NOTHING AT ALL.")
        elif e.get("readership") == "displaced":
            L.append("# READERSHIP: DISPLACED (MODEL %s).  At least one reader of this cell was"
                     % e.get("displacement_model", DISPLACEMENT_MODEL))
            L.append("#   routed here by the measured second array rather than by the cell its"
                     " own tpage names:")
            for n in e["second_array"]:
                L.append("#     GEOM %#x  record %#x  du=%d dv=%d  binds %s -> samples %s"
                         % (n["geom"], n["record_at"], n["du"], n["dv"],
                            " ".join("x%d_y%d" % tuple(c) for c in n["bound_cells"]) or "-",
                            " ".join("x%d_y%d" % tuple(c) for c in n["effective_cells"]) or "-"))
            if e.get("displaced_gained"):
                # ★ THE GAIN HALF, NAMED AS SUCH.  Every earlier kit refused or ignored this cell;
                # it is here because the derivation says so and nothing binds it, so the author is
                # told that BEFORE they paint, not in a doc.
                L.append("#   ** GAINED: this cell binds NO reader of its own.  Every model above")
                L.append("#   arrives from another column, so this page is licensed on the")
                L.append("#   DERIVATION ALONE and no key gates it.  If the model does not hold on")
                L.append("#   this container, a perfect repaint here is INVISIBLE IN GAME with no")
                L.append("#   error anywhere -- the loss half's failure, pointing the other way.")
            if e.get("display_binding_moved"):
                L.append("#   ** THE DISPLAY BINDING CHANGED HANDS: the PNG above is keyed to a"
                         " DIFFERENT")
                L.append("#   reader than the one a pre-W6b-3(iv) export would have used.")
            L += _wrap_comment(DA.DISPLACEMENT_DERIVATION, "#   ")
        if e.get("second_array_all_readers"):
            L.append("# SECOND-ARRAY MOVER on EVERY reader of this cell -- a DISCLOSURE, and the "
                     "page is unchanged.")
            for n in e["second_array"]:
                L.append("#   reader GEOM %#x (record %#x, slot identification only)  A=%#06x  B=%#06x"
                         % (n["geom"], n["record_at"], n["a"], n["b"]))
                for tag, why, half in (
                        ("SWAPPED ", "MEASURED: pair position 0 displaces u", n["swapped"]),
                        ("ORIGINAL", "RETIRED: pair position 1 onto u", n["original"])):
                    L.append("#     %s reading (%s): %+d texels -> column(s) %s%s"
                             % (tag, why, half["texels"],
                                ", ".join(str(c) for c in half["columns"]),
                                "" if half["moved"] else " (unmoved)"))
            L.append("#   SWAPPED is the MEASURED labelling (U1 s77 on ef038, 0.97); ORIGINAL is "
                     "the RETIRED reading,")
            L.append("#   kept beside it only so this disclosure stays auditable.  A non-zero pair "
                     "position 1 also")
            L.append("#   moves the read half a page, into the OTHER STACKED CELL of the column.")
            L.append("#   Wherever the mechanism holds this cell has NO effective reader and a")
            L.append("#   perfect repaint here is invisible in game.  To paint it anyway say")
            L.append("#     `%s = true`  (the key above)." % DA.ACK_MOVER_KEY)
            L += _wrap_comment(DA.U_DISPLACEMENT_CAVEAT, "#   ")
        L += [""]

    spillers = [m for m in (models or []) if m.get("effective_spills", m.get("spills"))]
    if spillers:
        L += ["# ---- THE NAME-EVERY-COLUMN GATE: models whose picture crosses a page ----",
              "# 60 spilling corpus bindings on the EFFECTIVE cover, 58 of them reading a picture",
              "# strictly wider than one page; the other two are exactly one page wide and cross the",
              "# boundary anyway, so there is no marginal case.  The edit unit is the CELL; the",
              "# JUDGEMENT unit is the model.  `spill.geom*.png` previews the whole picture."]
        for m in spillers:
            # THE COLUMNS PRINTED ARE THE ONES THE MODEL READS.  This block is selected on
            # `effective_spills`, so printing the BOUND `columns` beside it renders a crossing model
            # as a single column and reads as a kit bug.
            _cols = m.get("effective_columns") or m["columns"]
            L.append("#   GEOM %#x  %dbpp  %d texels wide  columns %s%s"
                     % (m["geom"], m["bpp"], (m["u"][1] - m["u"][0] + 1),
                        ", ".join(str(c) for c in _cols),
                        ("  (the record BINDS %s; the difference is the measured displacement)"
                         % ", ".join(str(c) for c in m["columns"]))
                        if list(_cols) != list(m["columns"]) else ""))
            L.append("#     cells: %s" % ("  ".join(m["cells"]) or "(none uploaded)"))
            if m["cells_no_writer"]:
                L.append("#     NO WRITER uploads %s -- nothing there to repaint"
                         % ", ".join(m["cells_no_writer"]))
        L += [""]

    if refused:
        by_class: Dict[str, List["CellRefusal"]] = {}
        for r in refused:
            by_class.setdefault(r.klass, []).append(r)
        L += ["# ---- REFUSED CELLS: named, with the reason.  A refusal is a RESULT of this tool. ----",
              "# %d of this container's page-cells get no editable picture.  They are listed rather"
              % len(refused),
              "# than omitted because on this surface the refusals ARE the shape -- corpus-wide,",
              "# 2,385 of 2,572 scenery cells declare no reader and therefore no depth."]
        for klass in sorted(by_class):
            rs = by_class[klass]
            L.append("#")
            L.append("#   [%s]  %d cell(s)" % (klass, len(rs)))
            for line in _wrap_comment(rs[0].reason, "#     "):
                L.append(line)
            L.append("#     %s" % "  ".join(r.name for r in rs))
        L += [""]
    return "\n".join(L) + "\n"


def _wrap_comment(text: str, prefix: str, width: int = 96) -> List[str]:
    """Wrap a refusal reason into fixed-width comment lines. The reasons are paragraphs on purpose --
    each carries its own measurement -- and a 400-character comment line is a reason nobody reads."""
    out, cur = [], prefix
    for word in text.split():
        if len(cur) + 1 + len(word) > width and cur != prefix:
            out.append(cur)
            cur = prefix
        cur += ("" if cur == prefix else " ") + word
    if cur != prefix:
        out.append(cur)
    return out


# ============================================================ (5) THE BUILD
#: every key one ``[[reskin.texel]]`` row understands. Unknown keys REFUSE rather than being ignored:
#: a mistyped ``acknowledge_cutout_reshape`` fails closed, which is fine, but a mistyped
#: ``expect_page_offset`` silently drops a guard -- and a guard may only ever fail CLOSED.
_TEXEL_KEYS = frozenset((
    "name", "source", "enabled", "note", "palette_from", "acknowledge_cutout_reshape",
    "acknowledge_texanim_frames",
    "expect_page_offset", "expect_page_bytes", "expect_page_wh",
    # W6b-1: the two guards a scenery CELL needs and a creature PART does not.
    "expect_bpp", "expect_cell",
    # W6b-1: the two REMEDY acknowledgements.  Both are literal-boolean-only (`_ack_bool`) and both
    # only ever ARM an obligation the author has already discharged by naming every writer / every
    # covered cell -- neither is a bypass, and there is no key that silences either gate on its own.
    "acknowledge_cotransform", "acknowledge_spill",
    # W6q: THE PAINT (QUANTIZE) LANE -- exactly three keys, and they sit on THIS table because it is
    # the one with a fail-closed unknown-key gate.  Note what is deliberately NOT here: `quantize`
    # and `mint_clut` remain UNKNOWN keys, so a spec spelling the concept the old way still refuses.
    # The shipped spelling is `source_paint`, which names a FILE OF A DIFFERENT KIND -- so the spec
    # is self-describing and `source` + `source_paint` on one row is a STATEABLE contradiction.
    "source_paint", "acknowledge_quantize", "acknowledge_recoloured_palette",
    # W6b-2: THE ONE NEW KEY.  Literal-boolean-only, and unlike every other acknowledgement in this
    # table it does not merely ARM an obligation the author already discharged -- it admits a depth
    # from a channel whose only in-game trial FAILED.  So it is the one key the build path also
    # requires a matching `expect_bpp` alongside; on its own it is refused BY NAME.
    DA.ACK_KEY,
    # W6b-3: CHANNEL A's key, on the same terms.  MANDATORY here -- an unregistered spec key fails
    # CLOSED two lines into `build`, which is correct behaviour and would also make the whole feature
    # unreachable.  A capability nobody can spell is not a capability.
    DA.ACK_ARRAY_KEY,
    # W6b-3 (iii): THE SECOND ARRAY's key, registered for exactly that reason -- and it is the one
    # acknowledgement in this table that pairs with NO `expect_bpp`, because it admits a question
    # about READERSHIP and there is no derived number for a guard to check it against.  Said in the
    # refusal text too, so it cannot read as a forgotten pair.
    DA.ACK_MOVER_KEY,
))


@dataclass
class TexelTarget:
    """One resolved texel row: its page, the art, and every census the gates read."""
    name: str
    enabled: bool
    source: str
    page: TexelPage
    note: str = ""
    palette_from: str = ""
    #: W6q: the RGBA painting, MUTUALLY EXCLUSIVE with ``source``. Its presence IS the lane switch --
    #: a file of a different kind, so the row is self-describing and the contradiction is stateable.
    source_paint: str = ""
    #: W6q: "I accept that my colours are APPROXIMATED". Every other import in this kit is a
    #: bijection; this one is not, and the tool cannot know how much the author will mind -- so it
    #: measures, prints, and makes them say the word. Literal boolean only.
    ack_quantize: bool = False
    #: W6q: "this art was painted against a row this same spec recolours, and I mean it".
    ack_recoloured: bool = False
    #: W6q: the quantize census (:func:`quantize_census`) -- a DISCLOSURE, never a gate.
    census: dict = field(default_factory=dict)
    ack_cutout: bool = False
    #: W7 L4's escape hatch -- a DELIBERATELY asymmetric strip (the window repainted, a source frame
    #: left stock, or the reverse). Literal boolean only, same law as every other acknowledgement.
    ack_texanim_frames: bool = False
    #: W6b-1: the CO-TRANSFORM remedy's word. Required on EVERY row of a multi-writer cell, and only
    #: reachable once every writer of that cell is named with its own art (:func:`_gate_cotransform`).
    ack_cotransform: bool = False
    #: W6b-1: the NAME-EVERY-COLUMN remedy's word, required once every cell a spilling model reads is
    #: named (:func:`_gate_spill_columns`).
    ack_spill: bool = False
    #: W6b-3: ``acknowledge_array_derived_depth`` -- CHANNEL A's word, recorded on the target and
    #: staged into the ledger beside ``depth_source`` so a build's own record says which judgement
    #: the author made. Literal boolean only; useless without a matching ``expect_bpp``.
    ack_array_depth: bool = False
    #: W6b-2: "this cell's depth comes from the container's own PROGRAM, not from any `so` reader, and
    #: I have read what happened the one time that was cast." Literal boolean only, and MEANINGLESS
    #: without a matching ``expect_bpp`` -- which the build path requires by name.
    ack_program_depth: bool = False
    #: W6b-3 (iii): ``acknowledge_second_array_displacement`` -- "every reader of this cell carries a
    #: non-zero second-array halfword, I have read what that may mean, and I judge the cell still
    #: read." Literal boolean only, and pairs with NO ``expect_bpp``: it admits no depth.
    ack_second_array: bool = False
    stock: bytes = b""
    new: bytes = b""
    changed: Tuple[int, ...] = ()
    cutout_punch: int = 0
    cutout_fill: int = 0
    dead_changed: int = 0
    live_changed: int = 0
    cov: Optional[Coverage] = None
    distinct_stock: int = 0
    distinct_new: int = 0
    round_trip: bool = True
    #: what the art-side drift guard had to say (see :func:`_gate_manifest`).
    manifest_note: str = ""
    #: what THE TEXANIM CO-TRANSFORM (:func:`_gate_texanim_frames`) found, per clip -- disclosure, so
    #: an author sees the protected set was checked even when it had nothing to say.
    texanim_note: str = ""
    #: W6b-1: every hazard verdict this SCENERY cell carries, in the author's terms -- the remedies
    #: that were discharged (:func:`_gate_cotransform`, :func:`_gate_spill_columns`), the program-VRAM
    #: direction verdict and the disclosures (:func:`_scenery_disclosures`). A creature target's list
    #: is empty, because W6a measured that surface hazard-free and re-checks it per target instead.
    hazard_notes: List[str] = field(default_factory=list)
    #: how many of this cell's 8,192 halfwords any model actually samples (scenery only).
    covered_halfwords: int = 0

    @property
    def cutout_flips(self) -> int:
        return self.cutout_punch + self.cutout_fill

    @property
    def art_source(self) -> str:
        """The file this row's art comes from, whichever lane it is on. One accessor, so a gate that
        reports "which file" cannot report the empty string for a paint row."""
        return self.source_paint or self.source

    @property
    def quantized(self) -> bool:
        return bool(self.source_paint)


@dataclass
class TexelBuild:
    effect: int
    label: str
    spec_path: str
    source: str
    #: the PRISTINE stock container the drift guard ran against.
    stock: bytes
    #: what THIS lane spliced into -- ``stock``, or a sibling lane's patched bytes when composed.
    orig: bytes
    patched: bytes
    sha_stock: str
    sha_out: str
    pages: List[TexelPage]
    targets: List[TexelTarget]
    pmap: RS.PaletteMap
    guard: str = "none -- UNGUARDED"
    #: how ``orig`` came to be: ``""`` when it is the stock container, else the sibling that made it.
    base_label: str = ""
    base_changed: Tuple[int, ...] = ()
    orth_specs: Dict[str, str] = field(default_factory=dict)
    #: THE REGION INVARIANT's own verdict (``reskin.assert_region_invariant``), recorded at the call
    #: site that enforced it so the report quotes the check that ran, not a restatement of it.
    region_invariant: str = ""
    check: Optional["SelfCheck"] = None

    @property
    def enabled(self) -> List[TexelTarget]:
        return [t for t in self.targets if t.enabled]

    @property
    def composed(self) -> bool:
        return bool(self.base_label)

    @property
    def sha_in(self) -> str:
        return _sha(self.orig)


def load_spec(path) -> dict:
    """Load a ``[reskin]`` spec that carries a texel table, a target table, or BOTH.

    ONE spec, two levers, deliberately: their byte spans are provably disjoint, so making an author
    keep two files in step for one container would invent a drift risk the format does not have.
    """
    with open(path, "rb") as fh:
        spec = tomllib.load(fh)
    r = spec.get("reskin")
    if not isinstance(r, dict):
        raise RepaintError("%s has no [reskin] table" % path)
    # W6q-0: THE TOP-LEVEL FAIL-CLOSED GATE, on the CLUT lane's own key set rather than a second copy
    # of it.  One spec file may carry both tables and this loader accepts target-only specs too, so a
    # private set here would make a key lawful on whichever loader happened to open the file --
    # a refusal that depends on the caller is not a refusal.  A texel refusal raises a texel error.
    unknown = sorted(set(r) - RS._RESKIN_KEYS)
    if unknown:
        raise RepaintError(RS.UNKNOWN_KEY_MESSAGE
                           % ("[reskin]", ", ".join(repr(u) for u in unknown),
                              ", ".join(sorted(RS._RESKIN_KEYS))))
    if "effect" not in r:
        raise RepaintError("[reskin] needs `effect`")
    if not r.get("texel") and not r.get("target"):
        raise RepaintError("%s declares neither [[reskin.target]] (the CLUT lever) nor "
                           "[[reskin.texel]] (the texel lever) -- nothing to do" % path)
    return spec


def _spec_dir(spec_path: str) -> str:
    """Where a RELATIVE ``source`` / sibling name resolves from: the SPEC FILE'S own directory.

    Never this module's -- a package directory holds no PNG, so a module-relative base would make
    every relative source a missing file for every user while reading like a lookup.
    """
    sp = str(spec_path or "")
    if not sp or sp == "?":
        return os.getcwd()
    return os.path.dirname(os.path.abspath(sp))


def _gate_collisions(blob: bytes, page: TexelPage) -> None:
    """THE CO-TRANSFORM REFUSAL for a CREATURE page, evaluated per target instead of assumed away.

    Two independent tests, because a VRAM cell and a file span are two different ways to collide:
    another writer declaring the SAME cell means the picture on screen is whichever upload ran last,
    and another writer whose FILE SPAN overlaps means one edit silently rewrites two pictures. The
    corpus answer for creature pages is 0 and 0 over 24 packages / 93 pages -- which is exactly why
    this is cheap to check and expensive to assume: six corpus effects park id-9 slots at x = 320,
    the ladder rung their own ``partCount`` leaves unused, so the near miss is one header field away.

    **CREATURE ONLY, and the split is not a convenience.** On the id-4 surface a second writer is an
    anomaly stock never produces, so the honest verdict is a flat refusal with no key. On the SCENERY
    surface a second writer is the normal shape of 34 corpus cells in 5 containers, and refusing them
    outright would refuse a class that has a lawful remedy -- so those go through
    :func:`_gate_cotransform` (name every writer, art for each, acknowledge) and this function's
    ``others``-based test would fire on a scenery cell's OWN writer record before any of it ran.
    """
    if page.scenery:                                             # -> _gate_cotransform / _gate_spans
        return
    others = other_page_writers(blob)
    hits = others.get(page.vram, [])
    if hits:
        raise RepaintError(
            "CO-TRANSFORM REFUSAL on %s: VRAM cell %s is ALSO written by %s.  Every multi-writer page "
            "pair in the corpus is genuinely different art shown at different cast phases (0 of 156 "
            "pairs is byte-identical), so repainting one writer leaves the others stock and the cast "
            "flickers between two pictures.  This is a CREATURE page, whose corpus answer is 0 "
            "collisions over 24 packages / 93 pages -- the multi-writer REMEDY (name every writer, "
            "art for each, `acknowledge_cotransform = true`) is the scenery lane's, and an id-4 page "
            "is uploaded by part index rather than by cell, so it cannot be expressed here.  %s"
            % (page.name, str(page.vram),
               "; ".join("%s @%#x" % (s, o) for s, o, _n in hits), W6B_REASON))
    lo, hi = page.page_offset, page.page_offset + page.page_bytes
    for cell, ws in sorted(others.items()):
        for src, off, nb in ws:
            if off < hi and lo < off + nb:
                raise RepaintError(
                    "CO-TRANSFORM REFUSAL on %s: its file span %#x..%#x overlaps %s (%#x..%#x, VRAM "
                    "%s).  One splice would rewrite two declared pictures.  %s"
                    % (page.name, lo, hi, src, off, off + nb, str(cell), W6B_REASON))


# --------------------------------------------------------- W6b-1: THE SCENERY HAZARD GATES
def _gate_program_vram(page: TexelPage, where: str) -> str:
    """THE PROGRAM-VRAM VERDICT, per cell -- **refuse a WRITE, DISCLOSE a READ.**

    THE DIRECTION LAW is the whole of it (PSX libgpu, corroborated by the DLL's own stub arities):
    ``LoadImage`` is main RAM -> VRAM and ``MoveImage`` is VRAM -> VRAM, both WRITES that can land on
    top of a static repaint at run time -- a LOST EDIT with no symptom, because the container on disc
    still holds the new art. ``StoreImage`` is VRAM -> main RAM, a **READ**, and a read cannot clobber
    anything; treating it as a hazard is what made ef211 -- the one cell in the corpus whose upload
    path is already cast-proven -- look unreachable. 113 cells over 12 containers move from refuse to
    disclose on that one correction.

    Three verdicts, in sharpening order:

    * ``program_cell`` -- ``MoveImage``'s destination CONST-FOLDS to this exact cell (the only per-cell
      program verdict in the corpus; 0 of 18 ``RECT*`` arguments resolve). HARD refusal BY NAME. It is
      the SHARPER verdict, not a narrower one: the census marks all 30 cells of ef001 / ef142 / ef144
      ``write-moveimage-dest-known``, so those containers refuse wholesale regardless, and what the
      per-cell verdict adds is that here the destination is RESOLVED rather than merely unknown;
    * ``write`` -- the container's program writes VRAM somewhere unresolvable. Refuse the whole
      surface;
    * ``unknown`` -- no effect id reached the derivation, so the lists could not be consulted. Refused
      as a WRITE, because reading silence as safety is how a refusal becomes a comment.

    Returns the DISCLOSURE line for the ``read`` and ``clean`` cases; raises otherwise.
    """
    hz = page.hazards
    if hz is None:                                               # creature: not the lists' unit
        return ""
    if hz.program_cell:
        raise RepaintError("%s: %s" % (where, _REFUSAL_TEXT["program-moveimage-cell"]
                                       % hz.program_evidence))
    if hz.program == "write":
        raise RepaintError("%s: %s" % (where, _REFUSAL_TEXT["program-vram-write"]
                                       % hz.program_evidence))
    if hz.program == "unknown":
        raise RepaintError("%s: %s" % (where, _REFUSAL_TEXT["program-vram-unknown"]
                                       % hz.program_evidence))
    if hz.program == "read":
        return ("program-VRAM READ (disclosure, not a refusal): %s" % hz.program_evidence)
    return "program-VRAM CLEAN: %s" % hz.program_evidence


def _gate_spans(blob: bytes, targets: Sequence["TexelTarget"]) -> None:
    """No two ENABLED targets may write the same file byte. That, exactly -- not "and nothing else
    overlaps", which is :func:`_gate_collisions`' job on the creature side and
    :func:`_gate_cotransform`'s on the scenery side.

    The scenery namespace is keyed by WRITER, so two rows can share a span only if the derivation
    itself is wrong -- but "only if the derivation is wrong" is precisely the class of thing a gate
    exists for, and the splice loop writes each target's span last-one-wins with no complaint at all.
    """
    live = [t for t in targets if t.enabled]
    for i, a in enumerate(live):
        alo, ahi = a.page.page_offset, a.page.page_offset + a.page.page_bytes
        for b in live[i + 1:]:
            blo, bhi = b.page.page_offset, b.page.page_offset + b.page.page_bytes
            if blo < ahi and alo < bhi:
                raise RepaintError(
                    "OVERLAPPING TARGETS: %s (%#x..%#x) and %s (%#x..%#x) write the same file bytes, "
                    "so the splice order would decide which picture survives and nothing would say "
                    "so." % (a.name, alo, ahi, b.name, blo, bhi))


def _gate_cotransform(blob: bytes, targets: Sequence["TexelTarget"]) -> Dict[str, str]:
    """**THE CO-TRANSFORM REMEDY** -- a multi-writer cell builds only when EVERY writer is named with
    its own art and the row says ``acknowledge_cotransform = true``.

    The hazard, measured: 34 corpus page-cells in 5 containers are uploaded by more than one writer,
    and **0 of the 156 writer pairs is byte-identical** -- the closest (ef381 x512 y384, ``s2`` vs
    ``s4``) still differs in 1.03% = 168 bytes. They are genuinely different pictures shown at
    different cast phases, so repainting one and leaving the others stock makes the cast flicker
    between the new art and the old, which is a mid-cast symptom only a playtest catches.

    So the remedy is the CLUT lane's own multi-writer shape (``reskin._gate_cells``), with ``writer``
    where that one has ``cell``: name them all, supply art for each, and say the word. Of the 34, only
    **16** are even expressible -- 8 are also SAME-BYTES-TWO-DEPTHS and 10 are read by nothing at all,
    and both of those refuse earlier, for reasons no naming fixes (ef251's Madeen has 6 shared cells
    and all 6 are unread, so a Madeen shared-column repaint is out of reach at any depth).

    **There is deliberately no "same art for all writers" shorthand.** A key that broadcast one PNG to
    N writers would be the tool asserting that the N uploads are interchangeable, which the corpus says
    they are not on 156 of 156 pairs. Two rows MAY name the same file -- that is an authored decision
    to unify the flicker -- and it is disclosed rather than silently accepted.

    Returns ``{target name: the disclosure line}``; raises naming the missing writers otherwise.
    """
    live = {t.page.cell: [] for t in targets if t.enabled and t.page.scenery}
    for t in targets:
        if t.enabled and t.page.scenery:
            live[t.page.cell].append(t)
    notes: Dict[str, str] = {}
    for cell, rows in sorted(live.items()):
        writers = rows[0].page.hazards.writers
        if len(writers) < 2:
            continue
        named = {t.page.hazards.writer for t in rows}
        missing = [w for w in writers if w.tag not in named]
        if missing:
            raise RepaintError(
                "THE CO-TRANSFORM REMEDY, %s: VRAM cell %s is uploaded by %d writers and this spec "
                "names %d of them (%s).  LEFT STOCK: %s.  0 of the corpus's 156 multi-writer pairs is "
                "byte-identical -- they are different pictures shown at different cast phases -- so "
                "repainting one leaves the others stock and the cast flickers between two pictures.  "
                "Add a [[reskin.texel]] row for %s with its OWN art, and say "
                "`acknowledge_cotransform = true` on every row of the cell.  There is no \"same art "
                "for all writers\" shorthand, on purpose: the closest corpus pair still differs in "
                "1.03%% of its bytes."
                % (", ".join(t.name for t in rows), str(cell), len(writers), len(named),
                   ", ".join(sorted(named)),
                   "; ".join("%s @%#x (%d B)" % (w.tag, w.off, w.nbytes) for w in missing),
                   ", ".join("cell.%s.x%d_y%d" % (w.tag, cell[0], cell[1]) for w in missing)))
        unack = [t.name for t in rows if not t.ack_cotransform]
        if unack:
            raise RepaintError(
                "THE CO-TRANSFORM REMEDY, %s: every writer of VRAM cell %s IS named (%s), which is the "
                "hard half -- but %s does not say `acknowledge_cotransform = true`.  Repainting N "
                "uploads of one cell is a deliberate, coordinated edit and this lane makes you state "
                "it, exactly as the CLUT lane does for a multi-writer palette: an acknowledgement is "
                "stated, never inferred."
                % (", ".join(t.name for t in rows), str(cell), ", ".join(sorted(named)),
                   ", ".join(unack)))
        same = {}
        for t in rows:
            same.setdefault(os.path.basename(t.art_source), []).append(t.name)
        dup = ["%s <- %s" % (", ".join(v), k) for k, v in sorted(same.items()) if len(v) > 1]
        for t in rows:
            notes[t.name] = (
                "CO-TRANSFORM: %d writers upload %s and all %d are named (%s), acknowledged%s"
                % (len(writers), str(cell), len(rows), ", ".join(sorted(named)),
                   "" if not dup else
                   ".  NOTE -- two writers share one source file (%s): that unifies pictures the "
                   "container declares as different, which is an authored decision, not a default"
                   % "; ".join(dup)))
    return notes


def _gate_spill_columns(blob: bytes, targets: Sequence["TexelTarget"],
                        models: Sequence[BoundModel]) -> Dict[str, str]:
    """**THE NAME-EVERY-COLUMN GATE** -- a spilling model's edit must name every cell that model reads.

    Measured ON THE POPULATION THIS GATE IS ACTUALLY TAKEN ON, which since W6b-3 (iv) is the
    EFFECTIVE cover: **60** spilling corpus bindings, **58 of them reading a picture strictly wider
    than one page** (median ``u`` span 160 texels). There is still no marginal case, but the reason
    is no longer a universal: the **2** exceptions are ef381 GEOM ``0x20727c`` and ef447 GEOM
    ``0xa2f74``, both 15bpp with a page-exact 64-texel span that the measured ``(32,128)`` pair
    pushes ACROSS the 704 -> 768 boundary. They are page-*wide* and still page-*crossing*, so a
    PAGE-scope edit of any of the 60 hands the author part of a picture, and the honest edit unit is
    the MODEL.

    ⚠ The BOUND figures this paragraph used to quote (**58 of 58** wider, **0 of 58** within 2 per
    cent) still hold of :attr:`BoundModel.spills`, which is where they now live. The "median 224
    texels" that stood here did NOT reproduce under any width metric on re-derivation (the bound
    median ``u`` span is 192) and was retired rather than restated.

    Same predicate shape as :func:`_gate_cotransform` with ``writer`` -> ``cell``: name every cell the
    model's own UVs cover, art for each, ``acknowledge_spill = true``. Three refusals fall out of it:

    * **SPILL-IN** -- a model whose own tpage column is elsewhere reads THIS cell. Page scope here
      silently edits a model this cell does not name, so the refusal NAMES the foreign model (36
      corpus cells; 6 of them cross two resources);
    * **an UNNAMED column** -- the model reads a cell this spec does not name. The obligation is
      *name them all*, and the message lists exactly which are missing;
    * **an UNWRITTEN column** -- the model reads a cell **no writer in this container uploads** (11
      corpus bindings on the effective cover: 10 on ef390, all 15bpp, presumably another effect's
      residual VRAM -- plus ef082 GEOM ``0x1dcd8``, 15bpp, pair ``(0,128)``, which reads unwritten
      VRAM *because this rung's own arithmetic moved it there*). The
      obligation is then unsatisfiable and no art exists to supply: *nothing uploads this cell, so
      there is nothing to repaint.*

    THE SET IS UV-EXACT, NOT RECT-CONSERVATIVE. A1 marks every stacked cell of a spilling rect (83
    cells); A2 restricts to the columns the model's own ``v`` range actually reaches (70), and A2's
    set is a strict subset with zero contradictions -- the 13-cell delta is entirely lower halves the
    model never samples. Gating on the superset would invent a false obligation, so the join here is
    :attr:`BoundModel.effective_cover`, the same UV rasterisation the depth derivation reads.

    ★ **W6b-3 (iv): THE OBLIGATION IS THE EFFECTIVE COVER, AND IT IS WRONG IN BOTH DIRECTIONS
    OTHERWISE.** This gate asks *"which cells does this model READ"*, which is a readership question,
    so on a displaced binding the bound cover would both DEMAND art for a cell the model does not
    effectively read and OMIT one it does. :attr:`BoundModel.columns` and :attr:`BoundModel.spills`
    stay BOUND (they are what ``w6b_gates`` G6's u-spill census is written about and they do not
    move); the obligation reads :attr:`BoundModel.effective_columns` /
    :attr:`BoundModel.effective_spills` beside them.

    AND THE TRIGGER IS A COLUMN CROSSING, NOT A CELL COUNT -- see the comment at the loop head. A
    picture tall enough to cover both stacked cells of its OWN column is not a spill and does not owe
    this obligation; ef211's ``0x33960`` is exactly that, and a cell-count trigger would refuse the
    rung's own cast 2.
    """
    # Keyed by CELL, holding EVERY writer target of that cell -- a plain dict here was V1 F1: on a
    # cell that is both co-transform and spilling, {cell: target} collapsed N writers to the last
    # row, so the ack was enforced on one writer and the verdict depended on TOML row order.
    # `_gate_cotransform` already keys lists; the two mirrored gates must not diverge.
    live: Dict[Tuple[int, int], List["TexelTarget"]] = {}
    for t in targets:
        if t.enabled and t.page.scenery:
            live.setdefault(t.page.cell, []).append(t)
    if not live:
        return {}
    by_geom = {m.geom: m for m in models}
    cells = RS.page_cells(blob)
    written = {pc.cell for pc in cells.values()}
    notes: Dict[str, str] = {}
    for cell, ts in sorted(live.items()):
        t = ts[0]                       # cell-level hazards are identical across a cell's writers
        hz = t.page.hazards
        # THE TRIGGER IS THE COLUMN, NOT THE CELL, and the difference is a whole cast.  A model whose
        # picture is TALL covers two STACKED cells of its own column -- ef211's `0x33960` reads both
        # halves of column 576 -- and that is not a spill: nothing crosses a page boundary, the rect
        # view names the same column, and the cast-2 plan edits the lower half alone on purpose.  The
        # u-spill hazard is a picture reaching a DIFFERENT column, which is what
        # `CellHazards.spill_in/spill_out` and `BoundModel.spills` both mean, so the gate keys on the
        # derivation's own definition instead of on "more than one cell", which would refuse the
        # rung's own second cast.
        if not hz.spills:
            continue
        spillers = [by_geom[r.geom] for r in hz.readers
                    if r.geom in by_geom and by_geom[r.geom].effective_spills]
        foreign = [r for r in hz.readers if not r.own_column]
        if not spillers:                                         # pragma: no cover - hz.spills implies
            continue
        for m in spillers:
            unwritten = sorted(c for c in m.effective_cover if c not in written)
            if unwritten:
                raise RepaintError(
                    "THE NAME-EVERY-COLUMN GATE, %s: GEOM %#x reads VRAM cell(s) %s that NO WRITER in "
                    "this container uploads -- nothing puts bytes there, so there is nothing to "
                    "repaint and the obligation to name every column this model reads cannot be "
                    "discharged.  11 corpus bindings do this on the EFFECTIVE cover: 10 on ef390 "
                    "(all 15bpp), where the residual is presumably another effect's leftover VRAM "
                    "and not this container's to edit -- plus ef082 GEOM 0x1dcd8, which reads "
                    "unwritten VRAM because the MEASURED DISPLACEMENT moved it there.  %s"
                    % (t.name, m.geom, ", ".join("x%d_y%d" % c for c in unwritten), W6B_REASON))
            missing = sorted(c for c in m.effective_cover if c not in live)
            if missing:
                where = ("GEOM %#x's own column is %d, so it SPILLS IN here" % (m.geom, m.page[0])
                         if any(r.geom == m.geom for r in foreign) else
                         "GEOM %#x reads this cell and spills OUT of it" % m.geom)
                raise RepaintError(
                    "THE NAME-EVERY-COLUMN GATE, %s: %s -- its picture covers %d VRAM cell(s) and "
                    "this spec names %d.  NOT NAMED: %s.  Of the 60 spilling corpus bindings this "
                    "gate is taken on, 58 read a picture strictly wider than one page (median u span "
                    "160 texels) and the other 2 are page-exact at 15bpp and cross the boundary "
                    "anyway, so a "
                    "PAGE-scope edit here hands you half a picture and silently changes a model this "
                    "cell does not name.  The edit unit is the MODEL: add a [[reskin.texel]] row for "
                    "%s with its own art (the read-only `spill.geom%#x.png` preview shows the whole "
                    "picture), and say `acknowledge_spill = true` on every row of it."
                    % (t.name, where, len(m.effective_cover),
                       len(m.effective_cover) - len(missing),
                       ", ".join("x%d_y%d" % c for c in missing),
                       ", ".join(_cell_name_at(cells, c) for c in missing), m.geom))
        # EVERY writer row of EVERY covered cell must ack -- N-1 of N is not "stated" (V1 F1).
        unack = [tt.name for m in spillers for c in sorted(m.effective_cover)
                 for tt in live.get(c, ()) if not tt.ack_spill]
        if unack:
            raise RepaintError(
                "THE NAME-EVERY-COLUMN GATE, %s: every cell GEOM %#x reads IS named, which is the hard "
                "half -- but %s does not say `acknowledge_spill = true`.  Editing a picture across a "
                "page boundary is a deliberate multi-cell edit and this lane makes you state it -- on "
                "EVERY writer row of every covered cell: an acknowledgement is stated, never inferred."
                % (t.name, spillers[0].geom, ", ".join(sorted(set(unack)))))
        note = ("SPILL: %s; every covered cell is named and acknowledged"
                % "; ".join("GEOM %#x covers %s" % (m.geom, " ".join(
                    "x%d_y%d" % c for c in sorted(m.effective_cover))) for m in spillers))
        for tt in ts:                   # the disclosure reaches every writer row, not the last one
            notes[tt.name] = note
    return notes


def _gate_second_array(targets: Sequence["TexelTarget"]) -> Dict[str, str]:
    """**THE SECOND-ARRAY GATE** -- an enabled edit on a cell whose every reader carries a mover must
    say so.

    Two layers, exactly the shape ``u``-spill already has: a refusal CLASS carries the REASON
    (``second-array-mover``, stated by :func:`scenery_surface` whether or not anyone builds), and this
    gate carries the OBLIGATION on the one path where an author is about to spend bytes. *A law not
    enforced at the call site is not enforced.*

    ⚠ **IT WITHDRAWS NOTHING AND CHANGES NO BYTE.** The page resolved, the depth is what it was, and a
    build that says :data:`ff9mapkit.summons.depth_attribution.ACK_MOVER_KEY` writes byte-for-byte
    what the same build wrote before this class existed. What the ack buys is that the author read the
    disclosure -- and what the disclosure says is that a mechanism MEASURED on ef038 puts this cell's
    readers somewhere other than where this kit names them, so wherever that mechanism holds the cell
    has no effective reader at all.

    ★★ **W6b-3 (iv) SPLIT ITS JOB IN TWO AND KEPT BOTH HALVES HERE.** On the ADOPTED path the
    obligation moves EARLIER -- ``displaced-readerless`` / ``displaced-readership-substituted`` are
    ``_UNADDRESSABLE``, so :func:`texel_page` refuses the row at RESOLUTION and an author who has not
    said the key never gets as far as painting. What survives at build time is the ACKNOWLEDGED case,
    which still has to SAY what was acknowledged: a disclosure that goes quiet the moment it is
    acknowledged is a disclosure nobody can audit afterwards. The pre-adoption branch below is not
    dead -- it is what a caller at the W6b-3 scope still gets, and it is the branch the class's
    52 / 29 / 47 population is measured on.
    """
    notes: Dict[str, str] = {}
    for t in targets:
        if not (t.enabled and t.page.scenery):
            continue
        hz = t.page.hazards
        if hz is None:
            continue
        if hz.displaced_readerless or hz.displaced_substituted:
            # Reaching here means `texel_page` resolved the name, which on these two classes means
            # the row said the key.  Record WHAT was admitted, with the arithmetic that produced it.
            notes[t.name] = (
                "DISPLACEMENT (%s), acknowledged: %s -- %s.  The page, its depth and its bytes are "
                "whatever the channel that still speaks for this cell says; what the ack admits is "
                "that no reader this kit can attribute samples it."
                % (DISPLACEMENT_MODEL,
                   "no reader this kit can attribute samples this cell" if hz.displaced_readerless
                   else "every bound reader left and a DISJOINT foreign set arrived",
                   _displacement_detail(hz, t.page.cell)))
            continue
        if not hz.every_reader_moves:
            continue
        # The MEASURED reading and the retired one, both in the message -- the same disclosure the
        # refusal and the scaffold carry, because an author who meets this at BUILD time must not get
        # a shorter version of it than one who met it at export time.
        detail = "; ".join(
            "GEOM %#x (record %#x, A=%#06x B=%#06x, %dbpp, u %d..%d): its tpage names column %d, "
            "SWAPPED reads column(s) %s and ORIGINAL reads column(s) %s"
            % (n.geom, n.record_at, n.a, n.b, n.bpp, n.u[0], n.u[1], n.bound_column,
               "/".join(str(c) for c in n.swapped_columns),
               "/".join(str(c) for c in n.original_columns))
            for n in hz.second_array)
        if not t.ack_second_array:
            raise RepaintError(
                "THE SECOND-ARRAY GATE, %s: EVERY `so` reader of VRAM cell %s carries a NON-ZERO "
                "second-array halfword -- %s.  Nothing about the page is withdrawn and no byte of "
                "this build would move; what the kit declines to do is let you spend a repaint on a "
                "cell that may have no effective reader without saying so first.  SWAPPED is the "
                "MEASURED labelling and ORIGINAL is stated above as the RETIRED reading, not as an "
                "alternative.  Say `%s = true` on this row if you judge the cell still read -- an "
                "acknowledgement is stated, never inferred, and this one pairs with NO `expect_bpp`: "
                "it admits no depth, so there is no number for a guard to check.  %s"
                % (t.name, list(t.page.cell) if t.page.cell else None, detail, DA.ACK_MOVER_KEY,
                   DA.U_DISPLACEMENT_CAVEAT))
        notes[t.name] = ("SECOND-ARRAY MOVER on every reader (%s), acknowledged -- the page, its "
                         "depth and its bytes are unchanged" % detail)
    return notes


def _cell_name_at(cells: Dict[Tuple[str, int, int], "RS.PageCell"], cell: Tuple[int, int]) -> str:
    """Every writer's name for one VRAM cell -- a co-transform cell is several names and naming one of
    them in a work order would send the author to a picture the other writer overwrites."""
    hits = [pc.name for pc in cells.values() if pc.cell == cell]
    return "/".join(sorted(hits)) or "x%d_y%d (no writer)" % cell


def _scenery_disclosures(t: "TexelTarget") -> List[str]:
    """The DISCLOSURES a scenery target owes its author -- never refusals, and never silence.

    Each is a fact the container states that an author cannot see in the PNG they are painting:

    * **SHARED READ** (class E3, 93 corpus cells over 38 effects) -- one edit changes >= 2 models, with
      no depth or palette signal to hint at it. The other models are NAMED;
    * **MULTI-PALETTE** (class C/E2, 25 cells; widest case 27 bindings over 2 CLUTs) -- the editable
      PNG is in the LOWEST-ADDRESSED binding's key and every other key ships as a read-only alternate
      view of the same index bytes. Both are named, because an author who never learns the second key
      tunes a colour they cannot see;
    * **LOWER HALF** -- this cell is the bottom half of an ``h = 256`` rect, i.e. one of the 20 the
      per-VRAM-cell map exists for. Worth saying out loud: the rect view cannot name it at all;
    * **COVER** -- how much of the 8,192-halfword cell any model actually samples. ef211's fire field
      reads 8,128, which is why it is a full-screen picture rather than a corner of one;
    * **W6b-2: THE DEPTH SOURCE** -- printed FIRST, because every other line is read through it. On a
      ``so-page`` or ``program`` cell no instrument has seen a model sample the bytes, so the depth
      can never be reported the way a direct one is -- and where the cell is the LOWER half of its
      256-line COLUMN (never of a writer's rect: they are different questions and the corpus has 10
      cells where they disagree) the disclosure says the depth crossed a cell boundary to get here;
    * **W6b-2: SPILL-vs-OWN-PAGE** -- two true predicates about one byte block, printed together.
    """
    hz = t.page.hazards
    if hz is None:
        return []
    L: List[str] = []
    # ★ THE INHERITANCE CLAUSE IS CONDITIONAL AND THE CONDITION IS THE **COLUMN**, NOT THE WRITER.
    # A page word names a PAGE, so the depth crossed a cell boundary exactly when this cell is the
    # LOWER half of its 256-line column -- which is `cell[1] % PAGE_LINES`, the predicate
    # `TexelPage.depth_inherited` and `ProgramDepth.inherited` both already use.  `hz.lower_half` is a
    # different question ("is this WRITER's rect split?") and answers False on the 10 corpus channel-P
    # cells that are id-9 ALTERNATE BLOCKS at y = 384: one whole 0x4000 upload, never a rect's lower
    # half, and still the bottom of a column whose depth was read off the top.  A disclosure that says
    # more than it measured is the same defect as one that says less -- and this said less.
    inherited = ("  " + DA.INHERITED_LINE) if t.page.cell and t.page.cell[1] % DA.PAGE_LINES else ""
    # W6b-2: WHERE THE DEPTH CAME FROM, first, because every other line below is read THROUGH it.
    # A depth inherited from a column is not the same kind of fact as one a model's own UVs declare,
    # and this lane's whole posture is that collapsing two kinds of fact is how a tool starts lying.
    if t.page.depth_source == "so-page":
        L.append("DEPTH FROM CHANNEL G (`so` AT PAGE GRANULARITY): no `so` reader samples this cell; "
                 "its COLUMN is bound at %dbpp by GEOM %s, and a page's draw mode governs all 256 "
                 "lines.%s  LICENSED -- it is the same record the lane already ships on, read at "
                 "the granularity the hardware uses; 57 corpus cells, 55 of them lower halves "
                 "addressable only through the per-cell map.  %s"
                 % (t.page.bpp, ", ".join("%#x" % g for g in hz.page_binders), inherited,
                    DA.A2_SCOPE_NOTE))
    elif t.page.depth_source == "so-array":
        # ★ CHANNEL A's disclosure says all four things in one breath: which ENTRY of which RECORD
        # (identification), which COLUMN the depth was inherited from, that the entry ORDER is
        # UNMEASURED, and the channel's in-game standing -- which is nothing.
        L.append("DEPTH FROM CHANNEL A (AN ENTRY OF THE COLUMN'S `so` BINDING ARRAY), acknowledged: "
                 "no `so` reader samples this cell and no record the kit could read before W6b-3 "
                 "names its COLUMN; %s binds the column at %dbpp (GEOM %s), and a page's draw mode "
                 "governs all 256 lines.%s  %s"
                 % (", ".join("record %#x slot %d" % r for r in hz.array_records)
                    or "an array entry", t.page.bpp,
                    ", ".join("%#x" % g for g in hz.array_binders), inherited, DA.ARRAY_ACK_WARNING))
    elif t.page.depth_source == "program":
        L.append("DEPTH FROM CHANNEL P (THE PROGRAM'S REGISTRATION), acknowledged: no `so` reader "
                 "samples this cell; the container's own program registers this page at %dbpp at %d "
                 "call site(s).%s  %s"
                 % (t.page.bpp, hz.program_sites, inherited, DA.ACK_WARNING))
    if hz.spill_vs_own_page:
        L.append("SPILL-vs-OWN-PAGE: this cell's readers bind the NEIGHBOURING page at %dbpp while "
                 "its own page is named at %dbpp -- both predicates true of the same bytes, FLAGGED "
                 "rather than reconciled.  2 corpus cells."
                 % (hz.depths[0], hz.page_depths[0]))
    # ---- W6b-3 (iv): the ADOPTED reading, printed on any target the effective cover moved.
    if hz.displaced_readerless or hz.displaced_substituted:
        L.append("DISPLACEMENT (MODEL %s), acknowledged: %s.  %s  %s"
                 % (DISPLACEMENT_MODEL, _displacement_detail(hz, t.page.cell),
                    _reach_line(hz), DA.U_DISPLACEMENT_ACK_WARNING))
    elif hz.displacement_adopted and any(r.displaced for r in hz.readers):
        # No refusal here: the kit names the cell the hardware reads.  It still SAYS so,
        # because a reader routed here by an arithmetic the author cannot see in the PNG is
        # exactly the class of fact this block exists for.
        # ★ AND THE GAIN HALF SAYS WHICH HALF IT IS.  A cell that KEPT readers and a cell that has
        # NONE of its own are two different claims, and printing one block for both hides the case
        # where the derivation is the ONLY thing speaking for the page.
        L.append("READERSHIP: DISPLACED (MODEL %s)%s -- %s.%s  %s"
                 % (DISPLACEMENT_MODEL,
                    (", GAINED: this cell binds NO reader of its own, so the page below is "
                     "licensed on the derivation ALONE, behind no key"
                     if hz.displaced_gained else ""),
                    "; ".join("GEOM %#x (record %#x, du=%d dv=%d) binds column(s) %s and "
                              "samples this cell"
                              % (r.geom, r.record_at, r.mover[0], r.mover[1],
                                 "/".join(str(c) for c in r.bound_columns))
                              for r in hz.readers if r.displaced),
                    ("  ** THE DISPLAY BINDING CHANGED HANDS: this cell's lowest-addressed "
                     "reader is GEOM %#x under the adopted derivation and was GEOM %#x under "
                     "the bound one, so the editable PNG is in a DIFFERENT palette key."
                     % (hz.readers[0].geom, hz.bound_readers[0].geom))
                    if hz.display_binding_moved else "",
                    DA.DISPLACEMENT_DERIVATION))
    if hz.every_reader_moves:
        # ★ THE ACKNOWLEDGED CASE STILL SAYS WHAT WAS ACKNOWLEDGED.  `_gate_second_array` has already
        # refused an unacknowledged row by the time this runs, so reaching here means the author said
        # the word -- and a disclosure that goes quiet the moment it is acknowledged is a disclosure
        # nobody can audit afterwards.  The MEASURED reading and the retired one, both named.
        L.append("SECOND-ARRAY MOVER on all %d reader(s): %s.  %s"
                 % (len(hz.readers),
                    "; ".join("GEOM %#x A=%#06x B=%#06x -> SWAPPED column(s) %s, ORIGINAL "
                              "column(s) %s"
                              % (n.geom, n.a, n.b,
                                 "/".join(str(c) for c in n.swapped_columns),
                                 "/".join(str(c) for c in n.original_columns))
                              for n in hz.second_array),
                    DA.U_DISPLACEMENT_ACK_WARNING))
    if hz.shared_read:
        L.append("SHARED READ (%d models): this one edit changes %s -- disclosure, not a refusal; "
                 "class E3 is 93 corpus cells over 38 effects and carries no depth or palette signal"
                 % (len(hz.readers), ", ".join("GEOM %#x" % r.geom for r in hz.readers)))
    if hz.multi_palette:
        # THE OTHER KEYS, NAMED -- from READERS where there are readers, and from the COLUMN's own
        # binders where there are none.  Naming them off `readers` alone printed an EMPTY list on a
        # channel-G cell, which is the class-C line disclosing that a second rendering exists and then
        # declining to say which: the author is told to look for a file it does not name.  A readerless
        # cell's alternates are keyed by VRAM CELL, which is exactly the `.as-x{X}_y{Y}.png` filename.
        others = (", ".join("%s (CLUT %s)" % (r.palette_name or "-", str(r.clut_cell))
                            for r in hz.readers[1:]) if hz.readers
                  else ", ".join("CLUT %s (its `.as-x%d_y%d.png` view)" % (c, c[0], c[1])
                                 for c in hz.column_clut_cells[1:]))
        L.append("MULTI-PALETTE (class C): one index array, %d renderings.  You are painting in %s; "
                 "the same bytes are ALSO shown in %s -- read-only alternate views ship beside the "
                 "editable PNG as `<cell>.as-x{X}_y{Y}.png`"
                 % (len(hz.palette_cells), t.page.palette_name or "(no declared key)", others))
    if hz.lower_half:
        L.append("LOWER HALF: this cell is the bottom 128 lines of an h=256 rect -- one of the 20 "
                 "cells the per-VRAM-cell map makes addressable at all; `scenery_pages`' (tag, x) key "
                 "can only ever reach the top half")
    L.append("COVER: %d of %d halfwords in this cell are sampled by some model"
             % (hz.covered_halfwords, RS.PAGE_CELL_W * CELL_LINES))
    return L


def _gate_texanim(blob: bytes, targets: Sequence[TexelTarget]) -> TA.ReadResult:
    """THE TEXANIM GATE, PASS 1 -- the one refusal that survived W7, raised before any art is read.

    ``reskin.py``'s own gate keys on ``Palette.slot < 0`` to spot a creature target; a texel target has
    no palette at all, so the predicate is re-implemented here rather than inherited -- an inherited
    one would simply never fire and the gate would be a comment.

    Pre-W7 this refused OUTRIGHT, with no key, on all five armed packages. W7 read the table
    (:mod:`ff9mapkit.summons.texanim`) and the refusal became an OBLIGATION instead: the region is a
    texel-blit clip table -- ``u32 clipCount``, 20-byte clip records, 12-byte destination windows,
    packed 4-byte frame lists -- so what a repaint has to worry about is not "the window" as an opaque
    hazard but a KNOWN, enumerable set of rects: each clip's live window plus every frame it can blit
    into that window. That set is what pass 2 (:func:`_gate_texanim_frames`) tests the edit against.
    Only ONE reading survived (a blit; the "moving sample window" reading is falsified -- every frame
    rect contains 0 model UV entries on 39/39 clips), and it only hurts a LOCALISED repaint.

    What still refuses here, unchanged and with no key: an armed region the reader cannot DECODE. The
    lift is conditional on a successful parse, never on the absence of an exception.

    **SCENERY TARGETS ARE UNDER THE SAME REFUSAL, and that is a measurement, not caution.** A2's
    ``p6_w7_interplay`` intersected all 39 protected clip rects plus the texanim region against all
    378 scenery cell-writer spans on the five armed containers and found **0 file-span intersections
    and 0 shared VRAM cells** -- the creature owns x in {192, 256, 320} and every scenery cell sits at
    x >= 384. That disjointness is what lets a scenery edit build under an armed table with no key
    (:func:`_gate_texanim_frames`). But it is a statement ABOUT A DECODED TABLE: on a region the
    reader cannot parse, the honest report is *"the table did not decode, so this disjointness was
    not measured for this container"*, and restating a corpus result over bytes nobody read would be
    exactly the guess this tier keeps refusing.
    """
    live = [t.name for t in targets if t.enabled]
    res = TA.read(blob)
    if not live or not res.armed:
        return res
    if res.table is None:
        kinds = sorted({("SCENERY cells" if t.page.scenery else "CREATURE pages")
                        for t in targets if t.enabled})
        raise RepaintError(
            "TEXANIM ARMED (%d bytes at %#x..%#x) and this spec repaints %s (%s).  W7 "
            "READ this format -- a texel-blit clip table whose only surviving reading is a same-page "
            "blit of palette indices (summons/texanim.py) -- but THIS container's region does not "
            "decode: %s.  An unread table's windows cannot be enumerated, so the co-transform "
            "obligation cannot even be stated; the pre-W7 refusal stands unchanged and no key lifts "
            "it.  (For a SCENERY cell the corpus measurement is DISJOINTNESS -- 0 of 378 file-span "
            "intersections over the five armed containers -- but that was measured on tables that "
            "DECODED, and quoting it over a region nobody could read would be restating a result "
            "instead of checking one.)  (All five stock armed packages -- ef038 / ef177 / ef493 / "
            "ef494 / ef495 -- decode; an undecodable region means a modified or unknown container.)"
            % (res.region.nbytes, res.region.lo, res.region.hi, " and ".join(kinds),
               ", ".join(live), res.error))
    return res


def _rect_touched(changed: Set[int], rect: "TA.Rect", page_w: int) -> int:
    """How many of ``rect``'s texels this edit moved.  One texel is one byte; a row is ``page_w``."""
    n = 0
    for y in range(rect.y, rect.y2):
        row = y * page_w
        for x in range(rect.x, rect.x2):
            if row + x in changed:
                n += 1
    return n


def _gate_texanim_frames(res: TA.ReadResult, t: TexelTarget) -> str:
    """THE TEXANIM GATE, PASS 2 -- **the co-transform obligation** (W7 L3/L4), per target.

    The unit is the CLIP FAMILY: one clip's live window plus every source frame it blits from. If the
    author repaints the window and leaves a source stock, then the first time that clip runs the window
    pops back to art the repaint never touched -- a mid-cast flicker only a playtest would catch. So
    the test is symmetry across the family, and it has exactly three outcomes:

    * **every rect of the family untouched** -- a repaint that stays out of the animated window
      entirely. Builds. (This is also every unarmed package, and every part the table does not name.)
    * **every rect of the family touched** -- the edit REACHED every rect. A dense whole-page repaint
      (a global recolour or filter) lands here in practice, which is why L3 needs no key -- but the
      predicate is *at least one changed texel per rect*, not *the edit spans the page*: a sparse
      page-wide remap can miss a rect and refuse (correctly -- that rect really is left stock), and
      one texel per rect satisfies it (V1 F2/F3: the tool checks REACH, not content equivalence).
    * **some touched, some left stock** -- the asymmetric case, and the only one with any exposure.
      REFUSED, naming the exact clip and the exact sibling rects left stock, so the message is a
      work order rather than a verdict. ``acknowledge_texanim_frames = true`` is the escape hatch for
      an author who WANTS an asymmetric strip.

    Rects are compared, never bounding boxes: the Carbuncle mouth-closed frames sit one row apart and
    share texels, and the box of that group would sweep in 500+ texels nobody asked to repaint.

    Note what this does NOT claim: that the same COLOUR transform reached every rect. Nothing in the
    file says what transform was intended, so inferring one would be a guess. It checks the property
    that is actually decidable from the bytes -- did the edit reach every rect of the family, or not.
    """
    if res.table is None or not res.armed:
        return ""
    if t.page.scenery:
        # THE W7 DISJOINTNESS LINE (A2 sec 5), quoted only where it was actually measured -- pass 1
        # has already refused the undecodable case, so reaching here means this container's table
        # parsed.  A clip's `part` indexes the id-4 PART ladder, which a scenery cell is not on at
        # all, so the family test below has nothing to test; the reason it has nothing to test is
        # the measurement, and stating it is the difference between "checked" and "skipped".
        return ("the SCENERY surface is DISJOINT from the protected set: 0 of 378 cell-writer "
                "file-span intersections and 0 shared VRAM cells over the five armed containers "
                "(creature x in {192, 256, 320}; every scenery cell sits at x >= 384), so W7's L4 "
                "co-transform obligation does not extend to this lane.  MEASURED, and conditional on "
                "the table DECODING -- which it did here (%d clip(s) read)"
                % len(res.table.clips))
    mine = [c for c in res.table.clips if c.part == t.page.index]
    if not mine:
        return ("part %d is not named by any clip in the table -- nothing to co-transform"
                % t.page.index)
    changed = set(t.changed)
    reports, asym, any_hit = [], [], False
    for c in mine:
        fam, seen = [], []
        for r in c.rects:                       # window first, then its sources, de-duplicated
            if r not in seen:
                seen.append(r)
                fam.append((r, _rect_touched(changed, r, t.page.w)))
        hit = [r for r, n in fam if n]
        miss = [r for r, n in fam if not n]
        any_hit = any_hit or bool(hit)
        reports.append("clip %d: %d/%d protected rect(s) repainted" % (c.index, len(hit), len(fam)))
        if hit and miss:
            asym.append((c, hit, miss))
    if asym and not t.ack_texanim_frames:
        c, hit, miss = asym[0]
        raise RepaintError(
            "THE TEXANIM CO-TRANSFORM, %s: this edit repaints %d of clip %d's %d protected rect(s) "
            "and leaves %d of them STOCK.  Repainted: %s.  LEFT STOCK: %s.  Those rects are one clip "
            "family -- the live window plus every frame it blits into that window -- so the moment "
            "the clip runs, the window shows art this edit never touched and the cast flickers "
            "between two pictures.  Repaint the sibling rect(s) too (the check is REACH -- at least "
            "one changed texel per protected rect -- so a dense page-wide repaint passes it while a "
            "sparse remap may not), or say "
            "`acknowledge_texanim_frames = true` on this row to state that the asymmetry is "
            "DELIBERATE.  (%d clip(s) name this page; %s.)"
            % (t.name, len(hit), c.index, len(hit) + len(miss), len(miss),
               " ".join(str(r) for r in hit), " ".join(str(r) for r in miss),
               len(mine), "; ".join(reports)))
    note = "; ".join(reports)
    if asym:
        note += "  -- ASYMMETRIC, acknowledged (`acknowledge_texanim_frames = true`)"
    elif any_hit:
        note += ("  -- every protected rect reached by this edit (the tool checks REACH; that the "
                 "same transform landed on each is the author's claim, not a measurement)")
    else:
        note += "  -- the edit stays clear of every protected rect"
    return note


def read_art_manifest(src: Path) -> Optional[dict]:
    """The :data:`ART_MANIFEST` beside a source image, or ``None`` -- ONE reader, several consumers.

    :func:`_gate_manifest` needs it for the drift guards and :func:`build` needs one field of it to
    decide whether R9's own named fix was taken. A second parse in the caller is how the guard and the
    thing it licenses drift apart, so this is the only place the file is opened.
    """
    mf = Path(src).parent / ART_MANIFEST
    if not mf.is_file():
        return None
    try:
        return json.loads(mf.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise RepaintError("%s is unreadable (%s) -- delete it or re-run export-art" % (mf, e))


def art_came_out_of_base(src: Path, base: bytes, blob: bytes) -> bool:
    """Did this art come out of THE COMPOSITION BASE rather than out of stock?

    This is R9's escape hatch and it is a MEASUREMENT, not a claim: the manifest records the sha256 of
    the whole container the export read, so equality with the composition base means the author
    literally re-exported against the recoloured row. That is precisely what R9's first named fix
    asks for -- *"build the CLUT half first and re-export with `--art-lane paint --from <the staged
    container>`"* -- and without this predicate that fix would land on the ART-DRIFT refusal instead,
    leaving `acknowledge_recoloured_palette` as the only way through. A refusal whose named fix does
    not clear it is a law-2 defect, so the fix is made reachable rather than the message reworded.
    """
    if base is blob or bytes(base) == bytes(blob):
        return False                                     # nothing composed: stock IS the base
    man = read_art_manifest(src)
    return bool(man) and man.get("stock_sha256") == _sha(bytes(base))


def _gate_manifest(blob: bytes, src: Path, target_name: str, page: TexelPage, *,
                   paint: bool = False, base_page: bytes = b"", base: bytes = b"") -> str:
    """THE STOCK-SHA DRIFT GUARD, applied where the ART is rather than where the spec is.

    ``export_art`` drops :data:`ART_MANIFEST` beside the PNGs it writes. When one is there, the pack
    refuses unless its ``stock_sha256`` is the container being patched and its record of this page
    agrees with the header's own derivation. Without it a re-exported page from a patched install
    would pack cleanly into a container it never came out of -- the silent failure with no symptom.
    Absent manifest = no extra guard (the spec's ``expect_sha256`` still ran); it is never fabricated.

    ★ ONE WIDENING, PAINT-ONLY AND MEASURED: on a paint row the manifest may also record **the
    COMPOSITION BASE** this build is quantizing onto, because that is the container R9's own named fix
    tells the author to export from. It is not a softening -- the claim the guard makes is *"the art
    came out of the bytes being patched"*, and on a composed paint build the bytes being patched ARE
    the base. The indexed lane keeps the shipped stock-only posture: there the pixels are indices, so
    which container they were rendered from decides nothing.
    """
    mf = src.parent / ART_MANIFEST
    man = read_art_manifest(src)
    if man is None:
        return "no %s beside %s -- the spec's own expect_sha256 is the only guard" % (ART_MANIFEST,
                                                                                      src.name)
    got = man.get("stock_sha256")
    want = _sha(blob)
    base_sha = _sha(bytes(base)) if (paint and base and bytes(base) != bytes(blob)) else ""
    if got != want and not (base_sha and got == base_sha):
        raise RepaintError(
            "ART DRIFT on %s: %s was exported from a container with sha256 %s, but the container "
            "being patched is %s%s.  The art and the bytes underneath it are not the same summon (a "
            "Steam/Moguri patch, another mod, or a stale export directory).  Re-run "
            "`summon-reskin export-art` against this install."
            % (target_name, mf, got, want,
               " (or its composition base %s)" % base_sha if base_sha else ""))
    from_base = bool(base_sha and got == base_sha)
    # BOTH surfaces, one manifest: `parts` holds the id-4 creature pages and `scenery` the VRAM
    # page-cells, and a lookup that read only the first would refuse every scenery pack as "no record"
    # -- a drift guard that fires on correct input is a guard nobody keeps.
    known = list(man.get("parts") or []) + list(man.get("scenery") or [])
    rec = next((e for e in known if e.get("name") == target_name), None)
    if rec is None:
        raise RepaintError("ART DRIFT on %s: %s carries no record for that page (it records %s)"
                           % (target_name, mf, ", ".join(e.get("name", "?") for e in known)))
    if page.scenery and list(rec.get("cell") or []) != list(page.cell):
        raise RepaintError("ART DRIFT on %s: %s records VRAM cell %s, the derivation says %s"
                           % (target_name, mf, rec.get("cell"), list(page.cell)))
    if page.scenery and rec.get("bpp") != page.bpp:
        raise RepaintError(
            "ART DRIFT on %s: %s exported this cell at %sbpp and the container's own `so` record now "
            "derives %dbpp -- the SAME 0x4000 bytes are a differently-shaped picture at each depth, so "
            "the PNG beside this manifest is not the picture this cell reads."
            % (target_name, mf, rec.get("bpp"), page.bpp))
    for key, mine in (("page_offset", page.page_offset), ("page_bytes", page.page_bytes)):
        if rec.get(key) != mine:
            raise RepaintError("ART DRIFT on %s: %s records %s %s, the header derives %s"
                               % (target_name, mf, key, rec.get(key), mine))
    if list(rec.get("wh") or []) != [page.w, page.h]:
        raise RepaintError("ART DRIFT on %s: %s records wh %s, the header derives %s"
                           % (target_name, mf, rec.get("wh"), [page.w, page.h]))
    if not paint:
        return "%s stock_sha256 MATCHES; page record agrees with the header" % ART_MANIFEST
    # ---- W6q: THE TWO PAINT-LANE GUARDS.  Split on purpose (see :func:`_gate_recoloured_palette`).
    #
    # (1) THE RENDER KEY.  A paint file's colours are only invertible under the decode they were
    # rendered with, so the decode is DATA the export records rather than a convention the reader
    # assumes.  A record carrying `paint_png` but no `render_key` came from a pre-W6q export or a
    # hand edit -- and an absent manifest keeps the shipped posture (no extra guard; never fabricated).
    got_key = rec.get("render_key") or ""
    if got_key != PAINT_RENDER_KEY:
        raise RepaintError(                                                # R11b
            "%s: %s records render_key %r for this page, and this lane inverts %r -- so it was "
            "exported before the render key was recorded (or was hand-edited).  The paint file's "
            "colours are only invertible under the decode they were rendered with.  Re-run "
            "`summon-reskin export-art --art-lane paint`."
            % (target_name, mf, got_key or "(none)", PAINT_RENDER_KEY))
    # (2) THE PAGE SHA.  Under THE INCUMBENT LOCK the container's own indices are an INPUT, so a page
    # that moved would silently lock onto different incumbents and the no-op would stop being a no-op
    # with nothing to see.  `page_sha256` stops being informational and becomes a guard.
    got_sha, want_sha = rec.get("page_sha256"), _sha(bytes(base_page))
    if got_sha != want_sha:
        raise RepaintError(                                                # R11
            "THE INCUMBENT IS NOT THE ONE YOUR ART CAME OUT OF, %s: %s records page_sha256 %s and the "
            "bytes this build quantizes against are %s.  This lane reads the container's own indices "
            "as the incumbent -- it is what makes an unedited re-import a byte-exact no-op -- so a "
            "page that moved would silently lock onto different ones.  Re-export."
            % (target_name, mf, got_sha, want_sha))
    return ("%s %s; page record agrees with the header; render_key %s and page_sha256 %s -- the "
            "incumbent IS the one this art came out of"
            % (ART_MANIFEST,
               "records THE COMPOSITION BASE (this art was re-exported against the recoloured row)"
               if from_base else "stock_sha256 MATCHES",
               PAINT_RENDER_KEY, want_sha[:16]))


def _clut_target_names(pmap: "RS.PaletteMap", rows: Sequence[dict], palette_name: str) -> List[str]:
    """Which of THIS SPEC's ``[[reskin.target]]`` rows recolour the row a given page indexes into.

    Names ONLY. The verdict (:func:`_gate_recoloured_palette`) is a BYTE comparison, so a row this
    resolver could not resolve costs the refusal a name and never costs it its measurement.
    """
    out: List[str] = []
    for d in rows:
        nm = d.get("name")
        # THE SAME PREDICATE THE CLUT LANE ITSELF USES (`reskin.py`, `enabled=bool(...)`).  `is False`
        # would have called `enabled = 0` live here and disabled there -- two readings of one key.
        if not nm or not bool(d.get("enabled", True)):
            continue
        try:
            if pmap.by_name(str(nm)).name == palette_name:
                out.append(str(nm))
        except (RS.ReskinError, KeyError):                       # an unresolvable name refuses in the
            continue                                             # CLUT lane's own loop, not here
    return out


def _gate_recoloured_palette(blob: bytes, base: bytes, t: "TexelTarget",
                             targets: Sequence[str], art_from_base: bool = False) -> str:
    """**R9 -- THE COMPOSED-PALETTE REFUSAL.** Art painted against the STOCK row, quantized onto a row
    this same build already recoloured, would be mapped onto colours the author never saw.

    The active-palette rule for the texel read is already decided and is not being changed here:
    ``palette_words(base, page)`` -- the COMPOSITION BASE, not stock. That is correct, and it is
    exactly why this gate exists: under the indexed lane the author authored INDICES, so a recoloured
    row simply recolours their picture; under quantize the author authored COLOURS, so a recoloured
    row silently re-decides which index each of them becomes.

    Deliberately split from the PAGE-SHA guard (R11) rather than folded into one string, because they
    are two different failures with two different fixes and law 2 requires each refusal to carry its
    OWN measurement: the PALETTE moved (build the CLUT half first and re-export with ``--from``, or
    say the word) versus the PAGE BYTES moved (re-export).

    ★ THE PREDICATE IS *"was the art rendered against the row it is being mapped onto"*, NOT *"did
    this spec's CLUT lane move the row"*. Those two coincide only when the art came out of stock;
    they diverge exactly on the workflow this refusal's own first fix names, and a refusal whose named
    fix does not clear it is a law-2 defect rather than a strictness. ``art_from_base`` carries the
    measurement (:func:`art_came_out_of_base` -- the export manifest's whole-container sha256 equals
    the composition base's), so re-exporting with ``--from <the staged container>`` CLEARS this gate
    and ``acknowledge_recoloured_palette`` stays what it is meant to be: the deliberate second answer,
    never the only one.

    Returns the disclosure line; raises naming N of M entries and the targets otherwise.
    """
    page = t.page
    if page.direct or not page.clut_entries:
        return ""
    stock_row = palette_words(blob, page)
    live_row = palette_words(base, page)
    moved = [i for i in range(min(len(stock_row), len(live_row))) if stock_row[i] != live_row[i]]
    if moved and art_from_base:
        return ("QUANTIZE base: %d of %s's %d entries differ from stock, and `%s` was RE-EXPORTED "
                "against those bytes (the export manifest records this build's own composition base) "
                "-- so the art was painted against the row it is being mapped onto"
                % (len(moved), page.palette_name or page.name, len(live_row),
                   os.path.basename(t.art_source)))
    if not moved:
        return ("QUANTIZE base: %s is BYTE-IDENTICAL to stock, so this art was painted against the "
                "row it is being mapped onto" % (page.palette_name or page.name))
    who = ("`[[reskin.target]] %s` IN THIS SPEC" % ", ".join(targets) if targets else
           "the sibling this build composes onto")
    if not t.ack_recoloured:
        raise RepaintError(
            "THE RECOLOURED-PALETTE REFUSAL, %s: %d of %s's %d entries are recoloured by %s, and `%s` "
            "was rendered against the STOCK row.  Quantize would map your colours onto colours you "
            "never saw -- the entries that moved are %s.  Either build the CLUT half first and "
            "re-export with `--art-lane paint --from <staged container>`, or say "
            "`acknowledge_recoloured_palette = true` on that row to map onto the new colours "
            "deliberately."
            % (t.name, len(moved), page.palette_name or page.name, len(live_row), who,
               os.path.basename(t.art_source),
               ", ".join(str(i) for i in moved[:12]) + (", ..." if len(moved) > 12 else "")))
    return ("QUANTIZE base: %d of %s's %d entries were recoloured by %s and this row says "
            "`acknowledge_recoloured_palette = true` -- the colours are mapped onto the NEW row"
            % (len(moved), page.palette_name or page.name, len(live_row), who))


def _resolve_base(spec: dict, spec_path: str, blob: bytes, game, compose: Optional[bool]):
    """The bytes this lane splices INTO, and the label saying where they came from.

    ``[reskin.orthogonality] reskin = "..."`` + ``compose = true`` rebuilds a SHIPPED CLUT spec and
    hands its patched container over, so a composed artifact keeps exactly one source of truth for the
    palette half instead of copying its rows into a second file that can drift out of step with it.
    """
    orth = (spec["reskin"].get("orthogonality") or {})
    want = bool(orth.get("compose", False)) if compose is None else bool(compose)
    sib = orth.get("reskin")
    if not want:
        return blob, "", ()
    if not sib:
        raise RepaintError("[reskin.orthogonality] says `compose = true` but names no `reskin` "
                           "sibling to compose onto")
    path = sib if os.path.isabs(sib) else os.path.join(_spec_dir(spec_path), sib)
    if not os.path.isfile(path):
        raise RepaintError("compose: no reskin sibling at %s" % path)
    b1 = RS.build(RS.load_spec(path), path, game, blob=blob)
    if b1.effect != int(spec["reskin"]["effect"]):
        raise RepaintError("compose: %s targets ef%03d, this repaint targets ef%03d -- composing "
                           "another effect's edits would corrupt this container"
                           % (os.path.basename(path), b1.effect, int(spec["reskin"]["effect"])))
    delta = tuple(i for i in range(len(blob)) if blob[i] != b1.patched[i])
    return b1.patched, ("composed on %s (%d CLUT bytes)" % (os.path.basename(path), len(delta))), delta


def build(spec: dict, spec_path: str = "?", game=None, blob: Optional[bytes] = None,
          base: Optional[bytes] = None, base_label: str = "",
          compose: Optional[bool] = None) -> TexelBuild:
    """Read the install, resolve every texel target, run every gate, splice the pages.

    ``blob`` supplies the STOCK container directly and skips the install read, so the whole guard /
    gate / drift pipeline is exercisable on synthetic bytes with no install -- a law that held on only
    one of two entry paths would not be one. ``base`` supplies already-patched bytes from a sibling
    lane (the CLI's one-spec composition); ``compose`` overrides the spec's own
    ``[reskin.orthogonality] compose`` (``False`` is what an orthogonality REBUILD passes, so a spec
    that composes onto its sibling can never recurse into rebuilding itself).
    """
    r = spec["reskin"]
    effect = int(r["effect"])
    if blob is None:
        blob, source = R.read_stock_effect(effect, game)
    else:
        source = "(caller-supplied bytes)"
    if not r.get("expect_sha256") and effect not in R.EXPECTED_STOCK_SHA \
            and not r.get("allow_unguarded"):
        raise RepaintError(
            "ef%03d has NO drift guard: the spec declares no `expect_sha256` and the effect is not in "
            "rescore.EXPECTED_STOCK_SHA.  A repaint splices at header-derived offsets; if a "
            "Steam/Moguri patch or another mod moved a page under the edit, nothing would notice.  "
            "Run `ff9mapkit summon-reskin export-art --ef %d` to emit the guard from your own "
            "install, or say `allow_unguarded = true` deliberately." % (effect, effect))
    sha_stock = R.drift_guard(effect, blob, r.get("expect_sha256"))
    guard = ("the spec's own expect_sha256 -- MATCHES" if r.get("expect_sha256") else
             ("REGISTERED in rescore.EXPECTED_STOCK_SHA -- MATCHES"
              if effect in R.EXPECTED_STOCK_SHA
              else "none -- UNGUARDED (allow_unguarded = true)"))

    if base is None:
        base, base_label, base_delta = _resolve_base(spec, spec_path, blob, game, compose)
    else:
        base_delta = tuple(i for i in range(len(blob)) if blob[i] != base[i])
        base_label = base_label or "composed on a caller-supplied build (%d bytes)" % len(base_delta)
    if len(base) != len(blob):                                   # pragma: no cover - by construction
        raise RepaintError("the composition base is a different length from the stock container")

    pmap = RS.palette_map(blob, effect=effect)
    pages = creature_texel_pages(blob)
    rows = r.get("texel") or []
    if not rows:
        raise RepaintError("%s declares no [[reskin.texel]] -- nothing for the texel lane to do"
                           % spec_path)

    targets: List[TexelTarget] = []
    seen: Set[str] = set()
    base_dir = _spec_dir(spec_path)
    for i, d in enumerate(rows):
        where = "[[reskin.texel]] #%d" % i
        unknown = sorted(set(d) - _TEXEL_KEYS)
        if unknown:
            raise RepaintError(
                "%s declares unknown key(s) %s.  Refused rather than ignored: a mistyped guard "
                "silently drops the guard, and a guard may only ever fail CLOSED.  Known keys: %s"
                % (where, ", ".join(repr(u) for u in unknown), ", ".join(sorted(_TEXEL_KEYS))))
        name = d.get("name")
        if not name:
            raise RepaintError("%s has no `name`" % where)
        if name in seen:
            raise RepaintError("texel target %r is declared twice" % name)
        seen.add(name)
        # W6b-2: THE ACK IS READ BEFORE THE RESOLVE.  A channel-P cell is refused AT RESOLUTION, so
        # the acknowledgement has to reach `texel_page`; reading it afterwards would mean un-refusing
        # a page, and a refusal a later line can take back is not a refusal.  `_ack_bool` makes
        # `"true"` fail here rather than arm -- an acknowledgement is stated, never inferred.
        ack_pd = _ack_bool(d, DA.ACK_KEY, where)
        # W6b-3: CHANNEL A's ack, read on exactly the same rung and for exactly the same reason.
        ack_ad = _ack_bool(d, DA.ACK_ARRAY_KEY, where)
        # W6b-3 (iv): THE DISPLACEMENT ACK, read on the same rung.  Its two classes are also refused
        # AT RESOLUTION, so it has to reach `texel_page` too -- and unlike the two above it pairs
        # with NO `expect_bpp`, because what it admits is a READERSHIP, and there is no number for a
        # guard to check.
        ack_sa = _ack_bool(d, DA.ACK_MOVER_KEY, where)
        page = texel_page(blob, name, effect, allow_program_depth=ack_pd,
                          allow_array_depth=ack_ad, allow_displaced_readerless=ack_sa)
        where = "texel target %s" % name
        # THE MANDATORY PAIR.  `expect_bpp` is STATED by the author and CHECKED against the derivation,
        # never chosen -- and on the one channel whose in-game trial FAILED the kit declines to accept
        # the ack alone.  The ack says "I judge this registered depth to be the drawn depth"; the
        # number is what makes that judgement checkable.  One without the other is a wish.
        if page.depth_source == "program" and "expect_bpp" not in d:
            raise RepaintError(
                "%s says `%s = true` but states NO `expect_bpp`.  The acknowledgement is your "
                "judgement that a REGISTERED depth is the depth the screen reads; `expect_bpp` is the "
                "number the kit checks that judgement against, and an ack with nothing to check is "
                "not a guard.  This cell's channel-P derivation is %dbpp at %d call site(s) -- write "
                "`expect_bpp = %d` if you mean it.  %s"
                % (where, DA.ACK_KEY, page.bpp, page.hazards.program_sites, page.bpp,
                   DA.REGISTRATION_CAVEAT))
        # ...and CHANNEL A's mandatory pair, on the same rung.  Channel A's tier is channel P's, and
        # its reason to be there is HARSHER: P's one in-game trial failed, A has had none it passed.
        if page.depth_source == "so-array" and "expect_bpp" not in d:
            _hz = page.hazards
            _ident = ", ".join("record %#x slot %d" % r for r in (_hz.array_records if _hz else ()))
            raise RepaintError(
                "%s says `%s = true` but states NO `expect_bpp`.  The acknowledgement is your "
                "judgement that a depth read off an entry of this column's `so` BINDING ARRAY is the "
                "depth the screen reads; `expect_bpp` is the number the kit checks that judgement "
                "against, and an ack with nothing to check is not a guard.  This cell's channel-A "
                "derivation is %dbpp, off %s (identification only) -- write `expect_bpp = %d` if you "
                "mean it.  %s  %s"
                % (where, DA.ACK_ARRAY_KEY, page.bpp, _ident or "the column's novel array entries",
                   page.bpp, DA.ORDER_UNMEASURED, DA.ARRAY_CAVEAT))
        if "expect_bpp" in d:
            assert_expect_bpp(blob, page, int(d["expect_bpp"]), where)
        if "expect_cell" in d:
            want_cell = tuple(int(v) for v in d["expect_cell"])
            if page.cell is None:
                raise RepaintError(
                    "%s: the spec guards VRAM cell %s, but this is a CREATURE page -- its addressable "
                    "unit is the id-4 PART, not a cell, and the id-4 handler uploads it by part index."
                    % (where, list(want_cell)))
            if want_cell != page.cell:
                raise RepaintError("%s: the spec guards VRAM cell %s, the derivation says %s"
                                   % (where, list(want_cell), list(page.cell)))
        if "expect_page_offset" in d and int(d["expect_page_offset"]) != page.page_offset:
            raise RepaintError("%s: the spec guards file %#x, the derivation says %#x"
                               % (where, int(d["expect_page_offset"]), page.page_offset))
        if "expect_page_bytes" in d and int(d["expect_page_bytes"]) != page.page_bytes:
            raise RepaintError("%s: the spec guards %d page bytes, the derivation says %d"
                               % (where, int(d["expect_page_bytes"]), page.page_bytes))
        if "expect_page_wh" in d and tuple(int(x) for x in d["expect_page_wh"]) != page.wh:
            raise RepaintError("%s: the spec guards %s, the derivation says %s"
                               % (where, list(d["expect_page_wh"]), list(page.wh)))
        pal_from = str(d.get("palette_from", "") or "")
        if pal_from:
            try:
                pal = pmap.by_name(pal_from)
            except RS.ReskinError as e:
                raise RepaintError("%s: `palette_from` -- %s" % (where, e)) from None
            if pal.name != page.palette_name:
                raise RepaintError(
                    "%s: `palette_from = %r` resolves to %s, but this page indexes into %s.  A page's "
                    "palette is a HEADER FACT (its own CLUT word), not a choice -- naming another "
                    "row would mean authoring indices against colours the engine will never apply "
                    "here." % (where, pal_from, pal.name, page.palette_name))
        src_paint = str(d.get("source_paint", "") or "")
        if src_paint and d.get("source"):
            raise RepaintError(                                            # R6
                "%s names BOTH `source` and `source_paint` -- two formats of record for one page.  "
                "The EXACT lane (indices, byte-identical) and the APPROXIMATING lane (RGBA, mapped "
                "onto the row this container carries) cannot both be authoritative; delete one.  The "
                "export writes both files precisely so this is a one-line switch." % where)
        targets.append(TexelTarget(
            name=name, enabled=bool(d.get("enabled", True)), source=str(d.get("source", "")),
            page=page, note=str(d.get("note", "")), palette_from=pal_from,
            source_paint=src_paint,
            ack_quantize=_ack_bool(d, "acknowledge_quantize", where),
            ack_recoloured=_ack_bool(d, "acknowledge_recoloured_palette", where),
            ack_cutout=_ack_bool(d, "acknowledge_cutout_reshape", where),
            ack_texanim_frames=_ack_bool(d, "acknowledge_texanim_frames", where),
            ack_cotransform=_ack_bool(d, "acknowledge_cotransform", where),
            ack_spill=_ack_bool(d, "acknowledge_spill", where),
            # W6b-3 (iii): read HERE and not up beside `ack_pd` / `ack_ad`.  Those two are read
            # BEFORE `texel_page` because they change RESOLUTION -- a channel-P / channel-A cell is
            # refused AT resolution.  This one resolves nothing: the page is emitted either way and
            # the ack arms a build-time obligation, exactly like `acknowledge_spill` beside it.
            ack_second_array=ack_sa,
            ack_program_depth=ack_pd, ack_array_depth=ack_ad))

    # ---- THE GATES THAT NEED NO ART, all of them before a single PNG is opened --------------------
    # An armed-and-unread table, a program-VRAM write, an unnamed co-transform writer and an unnamed
    # spill column are all decidable from the container plus the spec.  Making an author wait for an
    # art read to hear any of them would be theatre, and running them AFTER the read would let a
    # refused build still have touched the filesystem's error paths first.
    ta_read = _gate_texanim(blob, targets)
    _gate_spans(blob, targets)
    scenery_live = [t for t in targets if t.enabled and t.page.scenery]
    for t in targets:
        if t.enabled:
            t.hazard_notes = [n for n in [_gate_program_vram(t.page, "texel target %s" % t.name)]
                              if n]
    models = bound_models(blob) if scenery_live else []
    ct_notes = _gate_cotransform(blob, targets)
    sp_notes = _gate_spill_columns(blob, targets, models)
    sa_notes = _gate_second_array(targets)
    for t in scenery_live:
        t.covered_halfwords = t.page.hazards.covered_halfwords
        t.hazard_notes += [n for n in (ct_notes.get(t.name), sp_notes.get(t.name),
                                       sa_notes.get(t.name)) if n]
        t.hazard_notes += _scenery_disclosures(t)

    out = bytearray(base)
    for t in targets:
        if not t.enabled:
            continue
        clut_targets = _clut_target_names(pmap, r.get("target") or [], t.page.palette_name)
        _gate_collisions(blob, t.page)
        if not t.art_source:
            raise RepaintError("texel target %s is enabled but names no `source` (the exact indexed "
                               "lane) and no `source_paint` (the quantize lane) image" % t.name)
        src = resolve_art_path(base_dir, t.art_source)
        if t.quantized and t.page.direct:
            raise RepaintError(                                            # R8
                "texel target %s: `source_paint` on a 15bpp cell.  A 15bpp cell indexes NO palette "
                "-- and you do not need this lane there.  `--art-lane direct15` is ALREADY RGBA, and "
                "it is EXACT: 65,536/65,536 word identity, proven exhaustively rather than sampled.  "
                "Re-export with `--art-lane direct15` and edit `%s.png` together with `%s.stp.png`."
                % (t.name, t.name, t.name))                # BEFORE the art guard: a category error
        t.stock = bytes(base[t.page.page_offset:t.page.page_offset + t.page.page_bytes])
        t.manifest_note = _gate_manifest(blob, src, t.name, t.page,   # about the PAGE outranks a
                                         paint=t.quantized, base_page=t.stock,   # guard on the ART
                                         base=base)
        # THE ART READ, at THIS page's own depth.  Dispatching on the DERIVED depth (never on the
        # file's shape) is what makes a wrong `expect_bpp` a refusal rather than a differently-shaped
        # picture that packs to exactly the right byte count.
        #
        # ★ W6q ADDS EXACTLY ONE BRANCH, IN FRONT.  No existing codec path is modified -- which is
        # what makes "the four cast-proven shas still rebuild byte-exact" a claim rather than a hope:
        # if one of them moves, the change went into the wrong branch.
        if t.quantized:
            words = tuple(palette_words(base, t.page))
            rc_note = _gate_recoloured_palette(blob, base, t, clut_targets,
                                               art_came_out_of_base(src, base, blob))
            if rc_note:
                t.hazard_notes.append(rc_note)
            # THE ALTERNATE ROWS COME FROM THE COMPOSITION BASE, exactly as `words` does two lines
            # up.  R7 asks what the OTHER reader will see, and what that reader sees is the row the
            # engine will actually apply -- which on a composed build is the recoloured one.  Reading
            # them from pristine stock would judge (and, in `render_previews`, SHOW) the picture with
            # colours the engine never applies, on the one build shape the graft exists to protect.
            # The palette MAP is still derived from stock: the CLUT lane moves row CONTENTS, never
            # the header geometry the offsets come out of.
            t.new, t.census = read_paint_png(
                src, t.page, words, texel_view(t.page, t.stock),
                alternate_palette_rows(base, t.page, pmap))
            if not t.ack_quantize:
                raise RepaintError(                                        # R3
                    "QUANTIZE, %s: this lane APPROXIMATES.  Your colours are mapped onto the row the "
                    "container already carries, and it writes ZERO CLUT bytes.  MEASURED on THIS "
                    "art: %d of %d opaque texels matched an entry exactly (%.2f%%), %d were "
                    "approximated (mean d^2 %.3f, worst d^2 %d of a cube whose longest diagonal is "
                    "d^2 %d).  `plan` prints the whole census.  Say `acknowledge_quantize = true` on "
                    "that row -- an acknowledgement is stated, never inferred."
                    % (t.name, t.census.get("exact", 0), t.census.get("opaque", 0),
                       t.census.get("exact_pct", 0.0), t.census.get("approximated", 0),
                       t.census.get("mean_d2", 0.0), t.census.get("worst_d2", 0),
                       t.census.get("cube_diagonal_sq", CUBE_DIAG_SQ)))
        elif t.page.direct:
            t.new = read_direct_png(src, t.page.w, t.page.h)
            words: Tuple[int, ...] = ()
        else:
            words = tuple(palette_words(base, t.page))
            t.new = (read_indexed4_png(src, t.page.w, t.page.h, len(words)) if t.page.bpp == 4
                     else read_indexed_png(src, t.page.w, t.page.h, len(words)))
        if len(t.new) != t.page.page_bytes:                      # pragma: no cover - codec-enforced
            raise RepaintError("%s decoded to %d bytes, this cell is %d"
                               % (t.name, len(t.new), t.page.page_bytes))
        t.changed = tuple(i for i in range(len(t.stock)) if t.stock[i] != t.new[i])
        # THE CUTOUT LAW, counted in TEXEL space at every depth (see :func:`texel_view`).
        zeros, zeros_why = transparent_values(base, t.page)
        zset, st, nw = set(zeros), texel_view(t.page, t.stock), texel_view(t.page, t.new)
        moved = [i for i in range(len(st)) if st[i] != nw[i]]
        t.cutout_punch = sum(1 for i in moved if st[i] not in zset and nw[i] in zset)
        t.cutout_fill = sum(1 for i in moved if st[i] in zset and nw[i] not in zset)
        if t.cutout_flips and not t.ack_cutout:
            raise RepaintError(
                "THE CUTOUT LAW, %s: this edit moves %d texel(s) across the transparent boundary "
                "(%d punched opaque->hole, %d filled hole->opaque).  The transparent set here is %s, "
                "so those texels change the model's SILHOUETTE -- something the CLUT lever "
                "structurally cannot do, and therefore something this lane makes you say out loud.  "
                "Reshaping a torn wing edge is legitimate: say `acknowledge_cutout_reshape = true` on "
                "that row.  Painting through a hole by accident is not, and is what this catches."
                % (t.name, t.cutout_flips, t.cutout_punch, t.cutout_fill, zeros_why))
        t.texanim_note = _gate_texanim_frames(ta_read, t)
        # THE COVERAGE CENSUS, per surface.  A creature page's unit is the TEXEL (the id-4 uv pools
        # rasterised per part); a scenery cell's is the HALFWORD (the model's UV cover in absolute
        # VRAM space, which is the only unit that survives three depths).  Reporting one in the
        # other's units would be the kind of number that reads right and means nothing.
        if t.page.scenery:
            cover = {hw for m in models for hw in m.effective_cover.get(t.page.cell, ())}
            t.dead_changed = sum(1 for o in t.changed if (o // 2) not in cover)
            t.live_changed = len(t.changed) - t.dead_changed
        else:
            t.cov = coverage(blob, t.page.index)
            if t.cov.available:
                t.dead_changed = sum(1 for i in t.changed if not t.cov.mask[i])
                t.live_changed = len(t.changed) - t.dead_changed
            else:
                t.live_changed = len(t.changed)
        t.distinct_stock, t.distinct_new = len(set(st)), len(set(nw))
        t.round_trip = (all(KT.direct15_word(*KT.direct15_split(x)) == x for x in nw)
                        if t.page.direct else
                        _round_trip_ok(bytes(nw), words, t.page.w, t.page.h))
        out[t.page.page_offset:t.page.page_offset + t.page.page_bytes] = t.new
    patched = bytes(out)
    if len(patched) != len(base):                                # pragma: no cover - in-place splice
        raise RepaintError("the splice changed the container length -- impossible by construction")
    # THE REGION INVARIANT (W7 R1), against the PRISTINE stock rather than the composition base, so a
    # composed build proves the whole pipeline and not just this lane's own half of it.  Its W6b-1
    # sibling is THE PAGE-CELL DERIVATION IDENTITY: the scenery map is read out of the id-0 page-block
    # header and rect table, which this lane licenses NOTHING of, and a splice that moved one of them
    # would re-aim the whole map while the container still parsed, the length still matched and every
    # palette still re-derived.  Both run at the call site -- a law in a docstring is a wish.
    try:
        region_invariant = RS.assert_region_invariant(blob, patched,
                                                      "the repaint of ef%03d" % effect)
        region_invariant += "; " + RS.assert_page_cells_identical(
            blob, patched, "the repaint of ef%03d" % effect)
    except RS.ReskinError as e:                                  # a texel refusal must raise a texel
        raise RepaintError(str(e)) from None                     # error -- the CLI keys on the class

    orth = {k: v for k, v in (r.get("orthogonality") or {}).items() if isinstance(v, str)}
    return TexelBuild(effect=effect, label=str(r.get("label", "repaint")), spec_path=str(spec_path),
                      source=source, stock=blob, orig=bytes(base), patched=patched,
                      sha_stock=sha_stock, sha_out=_sha(patched), pages=pages, targets=targets,
                      pmap=pmap, guard=guard, base_label=base_label,
                      region_invariant=region_invariant,
                      base_changed=tuple(base_delta), orth_specs=orth)


# ============================================================ (6) THE SELF-CHECK
Gate = RS.Gate


@dataclass
class SelfCheck:
    accounting: List[Gate]
    rules: List[Gate]
    regions: List[Gate]
    orthogonality: List[Gate]
    quality: List[Gate]
    changed: List[int]
    per_target: Dict[str, int]

    @property
    def gates(self) -> List[Gate]:
        return self.accounting + self.rules + self.regions + self.orthogonality + self.quality

    @property
    def ok(self) -> bool:
        return all(g.ok for g in self.gates)


def _rebuild_reskin(path: str, mine: Set[int], blob: bytes) -> Tuple[Set[int], str]:
    """Rebuild a CLUT reskin from its own toml and return ``(changed offsets, the detail line)``."""
    b2 = RS.build(RS.load_spec(path), path, blob=blob)
    d = {i for i in range(len(b2.orig)) if b2.orig[i] != b2.patched[i]}
    return d, ("the CLUT lane changes %d bytes from %s; intersection %d"
               % (len(d), os.path.basename(path), len(d & mine)))


def _rebuild_rescore(path: str, mine: Set[int], blob: bytes) -> Tuple[Set[int], str]:
    b2 = R.build_patched(R.load_spec(path), path, blob=blob)
    d = {i for i in range(len(b2.orig)) if b2.orig[i] != b2.patched[i]}
    return d, ("W2 changes %d bytes (the camera Code at %s); intersection %d"
               % (len(d), ", ".join("%#x" % o for o in sorted(d)), len(d & mine)))


#: ``[reskin.orthogonality]`` table name -> the callable that REBUILDS that sibling lane. Same posture
#: as ``reskin.ORTH_REBUILDERS``: a table this package cannot rebuild gets an explicit SKIP naming the
#: reason, never a crash and never a silent pass that reads like a proof.
#:
#: The signature takes the STOCK BLOB as a third argument, which the reskin lane's own registry does
#: not. Two reasons, both load-bearing here and not there: a composed build already rebuilds a sibling
#: for its splice base, so re-reading ``resources.assets`` per gate would run a UnityPy load three
#: times for one command; and both halves of a composed proof MUST be intersected against the same
#: container -- re-reading the install per gate silently allows two different ones.
ORTH_REBUILDERS: Dict[str, Callable[[str, Set[int], bytes], Tuple[Set[int], str]]] = {
    "reskin": _rebuild_reskin,
    "rescore": _rebuild_rescore,
}

#: sibling table -> the TOP-LEVEL TOML table its own spec declares. A reskin spec's table is
#: ``[reskin]``; a rescore spec's is ``[rescore]``.
_ORTH_TABLE = {"reskin": "reskin", "rescore": "rescore", "retime": "retime"}


def _orthogonality(b: TexelBuild, mine: Set[int]) -> List[Gate]:
    """Rebuild each declared sibling lane from its OWN spec and intersect its edits with this one's.

    A gate exists for every sibling the spec NAMES, plus the CLUT lane always -- because that is the
    one this rung composes with, and a composed build whose two halves were never intersected would
    be shipping the disjointness as a claim.
    """
    out: List[Gate] = []
    base = _spec_dir(b.spec_path)
    for table in ["reskin"] + sorted(k for k in b.orth_specs if k != "reskin"):
        title = "the %s lane's edits are disjoint from this repaint's" % table
        name = b.orth_specs.get(table)
        if not name:
            out.append(Gate(True, title,
                            "SKIPPED: this spec names no `%s` sibling under [reskin.orthogonality], "
                            "so disjointness with the %s lane is UNPROVEN here -- not proven.  Name a "
                            "sibling spec for the same effect to turn this skip into a real "
                            "changed-offset intersection." % (table, table)))
            continue
        path = name if os.path.isabs(name) else os.path.join(base, name)
        if not os.path.isfile(path):
            out.append(Gate(False, title, "SKIPPED: no %s spec at %s -- but the spec NAMED it"
                            % (table, path)))
            continue
        ef = RS._sibling_effect(path, _ORTH_TABLE.get(table, table))
        if ef != b.effect:
            out.append(Gate(True, title,
                            "SKIPPED: %s targets ef%s, this repaint targets ef%03d -- rebuilding "
                            "another effect's edits would prove nothing about this one"
                            % (os.path.basename(path), "%03d" % ef if ef is not None else "?",
                               b.effect)))
            continue
        rebuild = ORTH_REBUILDERS.get(table)
        if rebuild is None:
            out.append(Gate(True, title,
                            "SKIPPED (LANE NOT IN THIS PACKAGE): %s targets this effect but the `%s` "
                            "lane cannot be rebuilt here, so its disjointness is UNPROVEN -- not "
                            "proven.  Register a rebuilder in repaint.ORTH_REBUILDERS[%r]."
                            % (os.path.basename(path), table, table)))
            continue
        try:
            d, detail = rebuild(path, mine, b.stock)
            out.append(Gate(not (d & mine), title, detail))
        except Exception as e:                                   # pragma: no cover - spec-dependent
            out.append(Gate(False, title, "FAILED to rebuild %s: %s" % (os.path.basename(path), e)))
    return out


def self_check(b: TexelBuild) -> SelfCheck:
    """Every gate, on OUR bytes -- the accounting, the hard rules, the inverted region partition, the
    sibling intersections and the quality census."""
    changed = [i for i in range(len(b.orig)) if b.orig[i] != b.patched[i]]
    mine = set(changed)

    # ---- (1) byte accounting: every changed byte inside a named target's own licensed page span
    owner: Dict[int, str] = {}
    per_target: Dict[str, int] = {}
    for t in b.enabled:
        per_target[t.name] = len(t.changed)
        for o in t.changed:
            owner[t.page.page_offset + o] = t.name
    unexplained = [o for o in changed if o not in owner]
    spans = [(t.page.name, t.page.page_offset, t.page.page_offset + t.page.page_bytes)
             for t in b.enabled]
    span_miss = [o for o in changed if not any(lo <= o < hi for _n, lo, hi in spans)]
    # THE ENVELOPE IS PER SURFACE.  For creature pages it is the id-4 header's own
    # ``partCount * 0x4000``; a SCENERY cell is not inside that block at all, so its 0x4000 has to be
    # added from the enabled targets or a scenery-only build would measure itself against an envelope
    # of zero and the gate would read "0 changed of 0" -- green, and about nothing.
    scen_env = sum(t.page.page_bytes for t in b.enabled if t.page.scenery)
    envelope = sum(p.page_bytes for p in b.pages) + scen_env
    acc = [
        Gate(not unexplained, "every changed byte belongs to a named texel target",
             "%d bytes changed, %d unexplained%s"
             % (len(changed), len(unexplained),
                "" if not unexplained else " at " + ", ".join("%#x" % o for o in unexplained[:8]))),
        Gate(not span_miss, "every changed byte lands inside a derived PAGE span",
             ("spans: " + " | ".join("%s %#x..%#x (%d B)" % (n, lo, hi, hi - lo)
                                     for n, lo, hi in spans)) if spans else
             "no enabled target -- this build splices nothing"),
        Gate(len(changed) <= envelope, "under the DERIVED texel envelope",
             "%d changed of the %d-byte envelope (%d creature page(s) at partCount * 0x4000 + %d "
             "scenery cell byte(s) at 0x4000 each), %.3f%% of the %d-byte container"
             % (len(changed), envelope, len(b.pages), scen_env,
                100.0 * len(changed) / max(1, len(b.orig)), len(b.orig))),
        Gate(len(b.patched) == len(b.orig), "same length by construction",
             "%d B in, %d B out" % (len(b.orig), len(b.patched))),
    ]

    # ---- (2) the hard rules of THIS lane
    bad_rt = [t.name for t in b.enabled if not t.round_trip]
    flips = [t for t in b.enabled if t.cutout_flips]
    unack = [t.name for t in flips if not t.ack_cutout]
    zero_law = []
    clut_hits = 0
    clut_rows: Set[int] = set()
    for t in b.enabled:
        if t.page.clut_offset is None or not t.page.clut_entries:
            # 15bpp DIRECT: there is no CLUT row to read and none to protect.  Skipped by DERIVATION
            # rather than by exception -- `palette_words` REFUSES a direct page on purpose, and
            # catching that refusal here to keep a loop going would turn a designed refusal into
            # control flow.
            continue
        z = transparent_indices(palette_words(b.orig, t.page))
        if list(z) != [0] and not t.page.scenery:
            zero_law.append("%s: transparent indices %s" % (t.name, list(z)))
        clut_rows.add(t.page.clut_offset)
        clut_hits += sum(1 for o in range(t.page.clut_offset,
                                          t.page.clut_offset + 2 * t.page.clut_entries)
                         if o in mine)
    shape = []
    for t in b.enabled:
        p = t.page
        ok = ((p.page_bytes == RS.PAGE_CELL_BYTES and p.h == CELL_LINES
               and p.w == cell_texel_w(p.bpp)) if p.scenery else
              (p.bpp == 8 and p.wh == (KT.PAGE_W, KT.PAGE_H) and p.page_bytes == KT.PAGE_BYTES))
        shape.append((ok, "%s %s %dx%d %dbpp %d B" % (t.name, p.kind, p.w, p.h, p.bpp,
                                                      p.page_bytes)))
    rules = [
        Gate(not bad_rt, "THE ROUND TRIP is byte-identical on every patched page, at its own depth",
             "%d page(s): the indexed ones re-encoded to a P-mode PNG and re-read as the same "
             "indices (4bpp through the nibble pack, one byte per texel); the 15bpp ones checked "
             "against the shift codec's own word identity, which is exhaustive over all 65,536 "
             "halfwords rather than sampled%s"
             % (len(b.enabled), "" if not bad_rt else " -- DRIFT at " + ", ".join(bad_rt))),
        Gate(not unack, "THE CUTOUT LAW: no unacknowledged index-0 boundary crossing",
             "no texel crossed the transparent-index boundary" if not flips else
             "; ".join("%s punched %d / filled %d (%s)"
                       % (t.name, t.cutout_punch, t.cutout_fill,
                          "ACKNOWLEDGED" if t.ack_cutout else "NOT acknowledged")
                       for t in flips)),
        Gate(True, "the transparent-index law (reported: exactly one alpha-0 entry, at index 0)",
             "holds on every patched CREATURE page (corpus: 93/93); a scenery cell's transparent set "
             "is DERIVED per palette and is not held to the id-4 shape, and a 15bpp cell has no "
             "palette at all (its cutout is the word 0x0000)" if not zero_law else
             "DEVIATES -- " + "; ".join(zero_law) + ".  The cutout census used the DERIVED set, so "
             "the gate is still correct; the note exists because a row that is not the corpus shape "
             "is worth knowing about before a cast."),
        Gate(all(ok for ok, _d in shape),
             "every patched page is its DERIVED shape at its DERIVED depth",
             ", ".join(d for _ok, d in shape) or "no enabled target"),
        Gate(clut_hits == 0, "this lane wrote ZERO CLUT bytes",
             "%d byte(s) of the %d row(s) this build's pages index into moved.  The palette is "
             "DISPLAY ONLY in the exported PNG; the container remains the palette authority, and "
             "the CLUT lever is `[[reskin.target]]`.%s"
             % (clut_hits, len(clut_rows),
                "" if len(clut_rows) == len([t for t in b.enabled]) else
                "  (%d enabled target(s) index no palette at all -- 15bpp DIRECT colour.)"
                % sum(1 for t in b.enabled if t.page.clut_offset is None))),
    ]

    # ---- (3) the INVERTED region partition + a strict re-parse
    regions: List[Gate] = []
    try:
        c = EC.parse_header(b.patched, strict=True)
        regions.append(Gate(c.cursor_end == len(b.patched), "the container re-parses STRICT",
                            "walker cursor %#x == file length %#x" % (c.cursor_end, len(b.patched))))
    except EC.ContainerError as e:                               # pragma: no cover
        regions.append(Gate(False, "the container re-parses STRICT", str(e)))
    gated = RS._regions(b.orig, b.effect, partition="texel")
    hits = []
    for name, lo, hi in gated:
        n = sum(1 for o in changed if lo <= o < hi)
        if n:
            hits.append("%s (%d bytes)" % (name, n))
    regions.append(Gate(not hits, "the CLUT strip, the id-4 header and every geometry / program / "
                                  "camera / sequence region are BYTE-IDENTICAL",
                        "%d regions gated (%d B of the container) under the TEXEL partition -- the "
                        "pages are licensed, everything else is not; %s%s"
                        % (len(gated), sum(hi - lo for _n, lo, hi in gated),
                           "no hits" if not hits else "HIT: " + "; ".join(hits),
                           "" if not b.composed else
                           ".  Measured on THIS LANE's delta: the CLUT strip is deliberately moved "
                           "by the sibling this build composes onto, and that the two never touch "
                           "the same byte is the COMPOSED HALVES gate below, not this one")))
    # ---- THE id-0 SPLIT (W6b-1): the half this lane licenses, and the half it must not have touched.
    # `_regions(partition="texel")` already gates the CLUT side above, so this gate exists to state
    # the boundary in the author's terms AND to prove the licensed half is where the edit actually
    # landed -- a scenery splice that wrote outside the pixel stream would otherwise only show up as
    # an "unexplained byte", which does not name the structure it broke.
    try:
        splits = RS.id0_splits(b.orig)
    except (RS.ReskinError, EC.ContainerError) as e:             # pragma: no cover - malformed id-0
        splits = []
        regions.append(Gate(False, "the id-0 page-block split derives", str(e)))
    if splits:
        head = [o for o in changed if any(sp.lo <= o < sp.boundary for sp in splits)]
        # ONLY an id-0 cell is inside the page pixel stream.  An id-9 ALTERNATE block is a whole
        # 0x4000 upload living in its own id-9 resource, so demanding it sit inside the id-0 stream
        # would fail every co-transform build -- the same per-writer / per-cell distinction the
        # lower-half divergence turns on.
        def _own_kind(t):
            hz = t.page.hazards
            w = next((w for w in hz.writers if w.tag == hz.writer), None) if hz else None
            return w.kind if w else "id0"

        id0_live = [t for t in b.enabled if t.page.scenery and _own_kind(t) == "id0"]
        scen_out = [t.name for t in id0_live
                    if not any(sp.boundary <= t.page.page_offset
                               and t.page.page_offset + t.page.page_bytes <= sp.hi
                               for sp in splits)]
        regions.append(Gate(
            not head and not scen_out,
            "the id-0 page-block header, clutWord table and inline CLUT stream are BYTE-IDENTICAL",
            "%d split(s): %s.  %d changed byte(s) below the pixelDataRel boundary%s; every id-0 "
            "scenery target's 0x4000 span sits inside the licensed PIXEL stream%s.  The rect table is "
            "what `page_cells` reads and what NOTHING else in this check would notice moving."
            % (len(splits),
               "; ".join("%s header %#x..%#x | pixels %#x..%#x (%d rect(s))"
                         % (sp.tag, sp.lo, sp.boundary, sp.boundary, sp.hi, sp.n_rects)
                         for sp in splits),
               len(head), "" if not head else " at " + ", ".join("%#x" % o for o in head[:8]),
               "" if not scen_out else " -- EXCEPT " + ", ".join(scen_out))))
    try:
        regions.append(Gate(True, "the page-cell map RE-DERIVES identically after the splice",
                            RS.assert_page_cells_identical(b.orig, b.patched,
                                                           "self_check(ef%03d)" % b.effect)))
    except RS.ReskinError as e:                                  # pragma: no cover - build gates it
        regions.append(Gate(False, "the page-cell map RE-DERIVES identically after the splice",
                            str(e)))
    mp_p = EC.creature_package(b.patched)
    if EC.creature_package(b.orig) is None:
        # A creature-less container is 348 of the corpus's 372 and now has a REAL texel surface, so
        # "the id-4 package still decodes" has to report that there is none rather than fail.  An
        # inverted pin: the same gate, the opposite verdict, for a reason it names.
        regions.append(Gate(mp_p is None, "the patched id-4 package still DECODES",
                            "SKIPPED: this container declares no id-4 + id-5 creature package (348 "
                            "of the corpus's 372 do not) -- and the patched container declares none "
                            "either, which is the half of it a splice could have broken"))
    else:
        ok_dec = mp_p is not None and KT.texture_check(b.patched, mp_p)["decodable"]
        regions.append(Gate(ok_dec, "the patched id-4 package still DECODES",
                            "texture_check passes on the patched container (%d parts)"
                            % (mp_p.part_count if mp_p else 0)))
    pm_s, pm_p = b.pmap, RS.palette_map(b.patched, effect=b.effect)
    same_pal = ([(p.name, p.off, p.entries) for p in pm_s.palettes]
                == [(p.name, p.off, p.entries) for p in pm_p.palettes]) and all(
        b.orig[p.off:p.off + p.nbytes] == b.patched[p.off:p.off + p.nbytes] for p in pm_p.palettes)
    regions.append(Gate(same_pal, "every DERIVED palette re-derives and is byte-exact",
                        "%d palettes, %d spans -- the CLUT lever's whole surface is untouched by this "
                        "lane" % (len(pm_p.palettes), len(pm_p.spans))))

    # ---- (4) orthogonality, and the composition's own disjointness
    orth = _orthogonality(b, mine)
    if b.composed:
        inter = set(b.base_changed) & mine
        orth.append(Gate(not inter, "THE COMPOSED HALVES ARE DISJOINT",
                         "%s; this lane changed %d texel bytes; intersection %d.  Union = %d bytes "
                         "vs stock (sha %s)"
                         % (b.base_label, len(changed), len(inter),
                            len(set(b.base_changed) | mine), b.sha_out[:16])))

    # ---- (5) quality: the dead-pad report, the coverage share, the index census
    qual: List[Gate] = []
    dead_rows = [t for t in b.enabled if t.dead_changed]
    qual.append(Gate(True, "texels the geometry never samples (reported, not fatal)",
                     "no edited texel is outside the sampled island" if not dead_rows else
                     "; ".join("%s %d of %d edited texels are in the never-sampled pad (%.1f%% of "
                               "the edit) -- inert at run time, exactly as a hue rotation is inert "
                               "on an achromatic palette"
                               % (t.name, t.dead_changed, len(t.changed),
                                  100.0 * t.dead_changed / max(1, len(t.changed)))
                               for t in dead_rows)))
    ran = "; ".join("%s %d/%d sampled (%.1f%%), %d interior hole(s), %d faces"
                    % (t.name, t.cov.covered, t.cov.total, 100.0 * t.cov.covered_fraction,
                       t.cov.interior_holes, t.cov.faces)
                    for t in b.enabled if t.cov and t.cov.available) or "no coverage computed"
    no_cov = [t.name for t in b.enabled if t.cov is not None and not t.cov.available]
    if no_cov:
        ran += ("  |  UNAVAILABLE for %s -- the dead-pad census cannot run there, so it reports "
                "nothing rather than reporting zero" % ", ".join(no_cov))
    scen_cov = "; ".join(
        "%s %d/%d halfwords sampled (%.1f%%), %d of %d edited byte(s) outside the cover"
        % (t.name, t.covered_halfwords, RS.PAGE_CELL_W * CELL_LINES,
           100.0 * t.covered_halfwords / float(RS.PAGE_CELL_W * CELL_LINES),
           t.dead_changed, len(t.changed))
        for t in b.enabled if t.page.scenery)
    if scen_cov:
        ran += ("  |  SCENERY (the unit is the HALFWORD, not the texel -- it is the only one that "
                "survives 4 / 8 / 15 bpp): " + scen_cov)
    qual.append(Gate(True, "the UV coverage instrument ran (reported, not fatal)", ran))

    # ---- THE HAZARD MATRIX, RE-MEASURED rather than restated ------------------------------------
    # The remedy gates are RUN AGAIN here, on the finished target list, instead of the notes build()
    # recorded being printed back.  A gate whose only evidence is a string an earlier pass wrote is a
    # gate that cannot fail, and this rung's whole argument is that a refusal is a measurement.
    hz_ok, hz_why = True, ""
    try:
        _gate_spans(b.stock, b.targets)
        _gate_cotransform(b.stock, b.targets)
        _gate_spill_columns(b.stock, b.targets,
                            bound_models(b.stock) if any(t.page.scenery for t in b.enabled) else [])
        for t in b.enabled:
            _gate_program_vram(t.page, "self_check %s" % t.name)
    except RepaintError as e:
        hz_ok, hz_why = False, str(e)
    rows = ["%s [%s] %s" % (t.name, ", ".join(t.page.hazards.names) or "clean",
                            " | ".join(t.hazard_notes) or "no hazard verdict")
            for t in b.enabled if t.page.scenery]
    qual.append(Gate(hz_ok, "every hazard this cell carries is REFUSED, remedied or DISCLOSED",
                     ("no scenery target -- the id-4 creature surface is measured hazard-free (0 "
                      "collisions over 24 packages / 93 pages) and `_gate_collisions` re-checks it "
                      "per target" if not rows else "  ||  ".join(rows))
                     if hz_ok else "RE-MEASURE FAILED: %s" % hz_why))
    qual.append(Gate(True, "index census (reported)",
                     ", ".join("%s distinct %d->%d, %d texels moved (%.2f%% of the page)"
                               % (t.name, t.distinct_stock, t.distinct_new, len(t.changed),
                                  100.0 * len(t.changed) / max(1, t.page.page_bytes))
                               for t in b.enabled) or "no enabled target"))
    # ---- W6q: THE QUANTIZE CENSUS, as a REPORT and never as a gate ------------------------------
    # 9 thresholds x 6 pages x 3 edits found total overlap between a legitimate hue edit's error and
    # an unrepresentable one's, at every threshold -- structurally, because a fixed CLUT is a small
    # subset of a 32,768-colour cube and a hue move is this lane's own primary use case.  So no
    # number here may refuse.  What DOES gate is already above: "this lane wrote ZERO CLUT bytes".
    qz = [t for t in b.enabled if t.quantized]
    if qz:
        qual.append(Gate(True, "the QUANTIZE census (a DISCLOSURE -- no threshold refuses here)",
                         "  ||  ".join(
                             "%s %s/%s opaque exact (%.2f%%), %s approximated, worst d^2 %d of %d, "
                             "%s on an ambiguous colour, %s nearest-ties, %d alternate-split check(s) "
                             "PASSED, %d STP change(s), acknowledged=%s"
                             % (t.name, "{:,}".format(t.census.get("exact", 0)),
                                "{:,}".format(t.census.get("opaque", 0)),
                                t.census.get("exact_pct", 0.0),
                                "{:,}".format(t.census.get("approximated", 0)),
                                t.census.get("worst_d2", 0), t.census.get("cube_diagonal_sq", 0),
                                "{:,}".format(t.census.get("ambiguous", 0)),
                                "{:,}".format(t.census.get("nearest_tie", 0)),
                                t.census.get("alt_checked", 0), t.census.get("stp_changed", 0),
                                t.ack_quantize)
                             for t in qz)))
    inert = [t.name for t in b.enabled if not t.changed]
    qual.append(Gate(True, "targets whose art matches the container already (reported, not fatal)",
                     "none" if not inert else ", ".join(inert)
                     + " -- an unedited re-export is a byte-exact no-op, which is the property that "
                       "makes a re-pack idempotent"))
    return SelfCheck(acc, rules, regions, orth, qual, changed, per_target)


# ============================================================ (7) THE PREVIEWS
def render_previews(b: TexelBuild, out_dir) -> List[str]:
    """Before / after / moved-texel sheets per enabled target, plus the coverage overlay.

    DECODED STOCK ART -- local-only for the same reason the export is, and written only under a root
    that has already passed the provenance guard.
    """
    Image = _need_pil()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: List[str] = []
    S = 3
    for t in b.enabled:
        w, h = t.page.w, t.page.h
        # THE PREVIEW IS RENDERED IN TEXEL SPACE, AT THIS PAGE'S OWN DEPTH.  A byte-indexed render
        # would show a 4bpp cell as half a picture of nonsense and a 15bpp cell as pairs of
        # half-colours -- and it would do it silently, because both still fill the frame.
        direct = t.page.direct
        rgba = ([] if direct else
                [KT.bgr555_rgba(x) for x in palette_words(b.orig, t.page)])

        def _img(raw, _rgba=rgba, _direct=direct, _p=t.page, _w=w, _h=h):
            vals = texel_view(_p, raw)
            im = Image.new("RGBA", (_w, _h))
            if _direct:
                im.putdata([KT.direct15_split(v)[:3] + (0 if v == KT.DIRECT15_CUTOUT else 255,)
                            for v in vals])
            else:
                im.putdata([_rgba[v] if v < len(_rgba) else (0, 0, 0, 0) for v in vals])
            bg = Image.new("RGBA", (_w, _h), (24, 24, 28, 255))
            return Image.alpha_composite(bg, im)

        before, after = _img(t.stock), _img(t.new)
        moved = Image.new("RGBA", (w, h), (18, 18, 22, 255))
        per = 1 if t.page.bpp == 8 else (2 if t.page.bpp == 4 else 0.5)   # texels per BYTE
        ch = {int(o * per) + k for o in t.changed
              for k in (range(2) if t.page.bpp == 4 else (0,))}
        moved.putdata([(255, 64, 200, 255) if i in ch else (24, 24, 28, 255)
                       for i in range(w * h)])
        panels = [before, after, moved]
        # ★ W6q: THE FOURTH PANEL -- the per-texel QUANTIZATION ERROR, which is precisely what the
        # census aggregates away.  It shows the author WHERE the palette could not follow them, and
        # it is what makes "use the CLUT lane instead" concrete rather than a sentence in a report.
        dmap = (t.census or {}).get("dmap")
        if dmap:
            # ★ THE RAMP IS NORMALISED TO THIS PAGE'S OWN WORST d^2, not to the cube's.  A fixed ramp
            # over a band that in practice runs d^2 1..57 moves ONE channel by ~22% and the panel then
            # reads as a second copy of the binary `moved` mask -- which is the one thing this panel
            # exists NOT to be.  The absolute numbers are not lost: the census keeps the UNCLAMPED
            # histogram and `plan` prints mean / p95 / worst against the cube diagonal.
            band = dmap[:w * h]
            hot = max(band) or 1
            span = float(hot - 1) if hot > 1 else 1.0
            err = Image.new("RGBA", (w, h))
            err.putdata([(0, 0, 0, 255) if not v else
                         (255, 220 - int(200 * ((v - 1) / span if hot > 1 else 1.0)), 40, 255)
                         for v in band])
            panels.append(err)
        sheet = Image.new("RGBA", (len(panels) * w * S, h * S), (12, 12, 14, 255))
        for k, im in enumerate(panels):
            sheet.paste(im.resize((w * S, h * S), Image.NEAREST), (k * w * S, 0))
        p = out / ("%s.repaint.png" % t.name)
        sheet.save(str(p))
        written.append(str(p))
        # ★ W6q D41: the class-C alternates, RE-RENDERED FROM THE NEW INDICES.  An author checking the
        # second key must see the RESULT, not the stock picture -- especially when R7 is the thing
        # they are trying to understand.
        # ``b.orig`` and NOT ``b.stock``: the row the engine will apply to the other reader is the
        # COMPOSED one, and this picture is the one R7 exists to protect -- rendering it from
        # pristine stock would show colours a composed build never puts on screen.  It is also the
        # same base the codec judged the split against, so the picture and the gate cannot disagree.
        if t.quantized and not t.page.direct and t.page.clut_entries:
            for alt in alternate_palette_rows(b.orig, t.page, b.pmap):
                ap = out / ("%s.as-x%d_y%d.after.png" % (t.name, alt.clut_cell[0], alt.clut_cell[1]))
                pal_a = [KT.bgr555_rgba(x) for x in alt.words]
                aim = Image.new("RGBA", (w, h))
                aim.putdata([pal_a[v] if v < len(pal_a) else (0, 0, 0, 0)
                             for v in texel_view(t.page, t.new)])
                Image.alpha_composite(Image.new("RGBA", (w, h), (24, 24, 28, 255)), aim).save(str(ap))
                written.append(str(ap))
        if t.cov is not None and t.cov.available:
            cp = out / ("%s.coverage.png" % t.name)
            write_coverage_png(t.new, palette_words(b.orig, t.page), t.cov.mask, w, h, cp)
            written.append(str(cp))
    return written


# ============================================================ (8) STAGING + THE LEDGERED SCRIPTS
def modfilelist_refusal(mod_root) -> Optional[str]:
    """THE SILENT-FALLBACK LAW, shared verbatim with both sibling lanes: a mod folder carrying a
    ``ModFileList.txt`` makes every unlisted override INVISIBLE and ``SFX.Play`` suppresses the
    missing-asset error, so "nothing changed" would be the only symptom. This lane REFUSES rather than
    half-owning somebody else's registry, and NEVER creates a list."""
    return R.modfilelist_refusal(mod_root)


def stage(b: TexelBuild, root=None, game_root=None, allow_install: bool = False,
          previews: bool = True, mod_root=None, refuse_modfilelist: bool = False) -> dict:
    """Write the patched container, the previews and the two ``--root``-aware live scripts.

    Deliberately the same shape as :func:`ff9mapkit.summons.reskin.stage` and driven by the SAME
    plan-rendered script templates: one deploy/revert implementation with a plan injected into it,
    never a second copy of a first-deploy snapshot scheme that can drift from the one that is proven.
    """
    if root is None:
        root = export.assert_local_only(staging_root(b.effect))
    root = Path(R._refuse_repo_path(root))
    if not allow_install:
        R._refuse_install_path(root, game_root)
    deploying = mod_root is not None
    mod_root = Path(R._refuse_repo_path(mod_root)) if deploying else root / "mod"
    if deploying and not allow_install:
        R._refuse_install_path(mod_root, game_root)
    if refuse_modfilelist:
        why = modfilelist_refusal(mod_root)
        if why:
            raise RepaintError(why)

    root.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(root / "backups", mod_root=mod_root)
    rel = "/".join(MOD_SUBPATH.split("/") + ["ef%03d" % b.effect])
    dest = Path(mod_root).joinpath(*rel.split("/"))
    sha = ledger.write_bytes(dest, b.patched)

    preview_files: List[str] = []
    if previews:
        preview_files = render_previews(b, root / "previews")

    live_mod = Path(game_root) / "FF9CustomMap" if game_root else None
    note = ("this artifact is STOCK ef%03d + the texel repaint '%s'%s; it REPLACES whatever container "
            "the mod folder holds for that effect.  The first-deploy snapshot restores it "
            "byte-for-byte." % (b.effect, b.label,
                                " composed on the CLUT lane (%s)" % b.base_label if b.composed
                                else ""))
    plan = {
        "effect": b.effect,
        "label": b.label,
        "default_mod_root": str(live_mod) if live_mod else "",
        "snapshot_base": str(root / "live-snapshot"),
        "revert_script": str(root / ("revert_summon_repaint_%d.py" % b.effect)),
        "targets": [{"src": str(dest), "rel": rel, "sha256": sha}],
        "expect_live_sha256": None,
        "note": note,
    }
    if live_mod is not None:
        live = live_mod.joinpath(*rel.split("/"))
        if live.exists():
            plan["expect_live_sha256"] = _sha(live.read_bytes())
    scripts = {
        "deploy": str(RS._write_script(root / "deploy_repaint.py", RS._DEPLOY_TEMPLATE, plan)),
        "revert": str(RS._write_script(root / ("revert_summon_repaint_%d.py" % b.effect),
                                       RS._REVERT_TEMPLATE, plan)),
    }
    if deploying:
        scripts["ledger_revert"] = str(ledger.write_revert_script(
            root, "%d" % b.effect, prefix="revert_summon_repaint_ledger"))

    # THE LANE IS PER ROW, so the manifest reports the rows rather than a constant: a paint build
    # whose record said `texel/indexed` would hand a cast report the wrong lane at the one moment
    # (after the fact, from the staged artifact) that the record is all anybody has.
    lanes = sorted({("paint" if t.quantized else ("direct15" if t.page.direct else "indexed"))
                    for t in b.enabled}) or ["indexed"]
    manifest = {
        "spec": b.spec_path, "effect": b.effect, "label": b.label,
        "lane": "texel/" + "+".join(lanes),
        "stock_sha256": b.sha_stock, "base_sha256": b.sha_in, "patched_sha256": sha,
        "composed": b.composed, "composed_on": b.base_label,
        "composed_base_bytes": len(b.base_changed),
        "container": str(dest), "scripts": scripts, "previews": preview_files,
        "changed_bytes": len(b.check.changed) if b.check else None,
        "per_target_bytes": b.check.per_target if b.check else None,
        "staging_root": str(root), "mod_root": str(mod_root),
        "texels": {t.name: {"enabled": t.enabled, "source": t.source,
                            # W6q: the quantize half, staged BESIDE the container so `verify`'s
                            # comparison is legible and a cast report can be audited after the fact.
                            "source_paint": t.source_paint,
                            "acknowledge_quantize": t.ack_quantize,
                            "acknowledge_recoloured_palette": t.ack_recoloured,
                            "quantize": census_record(t.census),
                            "kind": t.page.kind, "bpp": t.page.bpp,
                            # W6b-2: WHICH CHANNEL the depth came from, staged with the artifact.
                            # A cast that cannot say whether its depth was read off a model, off the
                            # column, or off a REGISTRATION cannot be read back as evidence about the
                            # channel -- which is the whole point of a channel-P cast.
                            "depth_source": t.page.depth_source,
                            DA.ACK_KEY: t.ack_program_depth,
                            # W6b-3: and CHANNEL A's word, staged beside `depth_source` for the same
                            # reason -- the ack IS the judgement a cast would be testing.
                            DA.ACK_ARRAY_KEY: t.ack_array_depth,
                            # W6b-3 (iii): and the SECOND-ARRAY word.  Not a depth judgement -- a
                            # READERSHIP one -- and a cast of a cell whose readers all carry a mover
                            # is exactly the cast that would test it, so the record has to say so.
                            DA.ACK_MOVER_KEY: t.ack_second_array,
                            # W6b-3 (iv): WHICH ARITHMETIC this row was staged under, and
                            # whether the reader it was attributed to was routed here by it.
                            # A cast record that cannot say which model it tested is a cast
                            # nobody can re-score later.
                            "displacement_model": DISPLACEMENT_MODEL,
                            "readership": t.page.readership,
                            "cell": (list(t.page.cell) if t.page.cell else None),
                            "page_offset": t.page.page_offset, "page_bytes": t.page.page_bytes,
                            "wh": list(t.page.wh), "changed": len(t.changed),
                            "cutout_punch": t.cutout_punch, "cutout_fill": t.cutout_fill,
                            "acknowledge_cutout_reshape": t.ack_cutout,
                            "acknowledge_cotransform": t.ack_cotransform,
                            "acknowledge_spill": t.ack_spill,
                            # the hazard verdicts, staged BESIDE the container: a cast report that
                            # cannot say which disclosures were live is a report nobody can audit
                            # after the fact.
                            "hazards": list(t.page.hazards.names) if t.page.hazards else [],
                            "hazard_notes": list(t.hazard_notes),
                            "covered_halfwords": t.covered_halfwords,
                            "dead_changed": t.dead_changed, "palette_from": t.palette_from}
                   for t in b.targets},
    }
    from .. import fsutil
    fsutil.atomic_write_text(root / "build_manifest.json",
                             json.dumps(manifest, indent=2), encoding="utf-8", newline="\n")
    manifest["staged_files"] = len(ledger.files)
    return manifest


def resolve_art_path(spec_dir: str, rel: str) -> Path:
    """An art path as the build resolves it: absolute as given, else relative to the SPEC's own
    directory. One resolver, three call sites (``build``, ``verify``, the CLI's verify pre-flight) --
    two spellings of "where the picture is" is how a guard and the thing it guards drift apart."""
    p = Path(rel)
    return p if p.is_absolute() else Path(spec_dir) / p


def absent_paint_line(name: str, src) -> str:
    """THE ABSENT-SOURCE SENTENCE, in one place because two call sites say it."""
    return ("VERIFY quantize    %s: THE PAINT SOURCE IS ABSENT (%s) -- this rebuild used bytes it "
            "can no longer re-read, so the container is verified and the ART is NOT" % (name, src))


def missing_paint_sources(spec: dict, spec_path: str) -> List[Tuple[str, Path]]:
    """Enabled ``source_paint`` rows whose file is GONE -- ``verify``'s pre-flight.

    ★ WITHOUT THIS THE ABSENT-SOURCE BRANCH IS DEAD AT THE ONLY ENTRY POINT A USER HAS. The CLI
    reaches :func:`verify` only *through* a rebuild, and a rebuild opens the art -- so a deleted paint
    file refuses inside ``build`` with the generic *"no such source image"* and the sentence that says
    *the container is verified and the ART is not* never prints. The check is a pure existence test on
    the same resolution :func:`build` uses; it decides nothing else and it never fabricates a pass.
    """
    out: List[Tuple[str, Path]] = []
    base_dir = _spec_dir(spec_path)
    for d in ((spec.get("reskin") or {}).get("texel") or []):
        if not bool(d.get("enabled", True)):
            continue
        rel = str(d.get("source_paint", "") or "")
        if not rel:
            continue
        src = resolve_art_path(base_dir, rel)
        if not src.is_file():
            out.append((str(d.get("name") or "?"), src))
    return out


def verify(b: TexelBuild, root=None) -> dict:
    """Re-check what is STAGED, as bytes -- not as a rebuild's promise."""
    root = Path(root or staging_root(b.effect))
    mf = root / "build_manifest.json"
    lines: List[str] = []
    container_same: Optional[bool] = None
    if not mf.exists():
        return {"ok": False, "root": str(root), "manifest": str(mf),
                "lines": ["VERIFY FAILED: no build manifest at %s" % mf]}
    man = json.loads(mf.read_text(encoding="utf-8"))
    ok = True
    p = Path(man["container"])
    if not p.exists():
        lines.append("VERIFY container   MISSING at %s" % p)
        ok = False
    else:
        got = p.read_bytes()
        same = got == b.patched
        container_same = same
        ok = ok and same
        lines.append("VERIFY container   %d B sha %s -> %s"
                     % (len(got), _sha(got)[:16], "MATCHES the rebuild" if same else "DIVERGES"))
        if man.get("patched_sha256") != _sha(got):
            lines.append("VERIFY manifest    sha in the manifest does not match the staged file")
            ok = False
    if man.get("stock_sha256") != b.sha_stock:
        lines.append("VERIFY stock       the manifest was built against %s, this rebuild reads %s"
                     % (str(man.get("stock_sha256"))[:16], b.sha_stock[:16]))
        ok = False
    for name, sp in sorted((man.get("scripts") or {}).items()):
        exists = Path(sp).exists()
        ok = ok and exists
        lines.append("VERIFY %-11s %s" % (name, sp if exists else "MISSING: %s" % sp))
    missing = [f for f in (man.get("previews") or []) if not Path(f).exists()]
    lines.append("VERIFY previews    %d staged, %d missing"
                 % (len(man.get("previews") or []), len(missing)))
    ok = ok and not missing
    for name, tr in sorted((man.get("texels") or {}).items()):
        t = next((x for x in b.targets if x.name == name), None)
        if t is None or (t.enabled, t.page.page_offset, len(t.changed)) != (
                tr["enabled"], tr["page_offset"], tr["changed"]):
            lines.append("VERIFY texel       %s DIVERGES from the manifest" % name)
            ok = False
    # ---- W6q: THE QUANTIZE LINE.  `verify` ALREADY re-derives -- the CLI rebuilds independently and
    # this function compares the staged bytes against that rebuild -- so nothing is re-derived here.
    # What is added is LEGIBILITY, plus the one genuinely new behaviour: THE ABSENT-SOURCE BRANCH.
    # A paint row whose source file has gone is reported as such rather than passing quietly, because
    # a verify that cannot re-read the art is not a verify of the art.
    for t in b.enabled:
        if not t.quantized:
            continue
        src = resolve_art_path(_spec_dir(b.spec_path), t.source_paint)
        if not src.is_file():
            lines.append(absent_paint_line(t.name, src))
            ok = False
            continue
        # MEASURED, NEVER ASSERTED -- both halves.  (a) the count is taken in TEXEL space, because
        # `t.changed` is a BYTE set and a 4bpp cell carries two texels per byte, so quoting it as
        # "texels" is off by up to 2x on exactly the depth this lane spends most of its time in;
        # (b) "differed from the staged container" is the verdict of the byte comparison at the top of
        # this function, not a literal -- in a lane whose whole posture is measure-never-assert, a
        # hard-coded 0 printed underneath a line that just said DIVERGES is the one asserted number.
        st, nw = texel_view(t.page, t.stock), texel_view(t.page, t.new)
        moved_texels = sum(1 for i in range(min(len(st), len(nw))) if st[i] != nw[i])
        lines.append("VERIFY quantize    %s: re-quantized from %s; %d texel(s) / %d byte(s) differed "
                     "from stock, and the staged container %s (%d exact / %d approximated, worst "
                     "d^2 %d)"
                     % (t.name, src.name, moved_texels, len(t.changed),
                        "MATCHES this re-quantize byte for byte" if container_same is True
                        else ("DIVERGES from it -- see the container line above"
                              if container_same is False else "was not readable"),
                        t.census.get("exact", 0), t.census.get("approximated", 0),
                        t.census.get("worst_d2", 0)))
    return {"ok": ok, "root": str(root), "manifest": str(mf), "container": man.get("container"),
            "lines": lines}


# ============================================================ (9) REPORTING
def scenery_lines(blob: bytes, effect: Optional[int] = None, *,
                  channels: Sequence[str] = EDIT_CHANNELS) -> List[str]:
    """The scenery page-cell census, as DISCLOSURE -- what the container states and what it does not.

    A derivation FAILURE is printed, never swallowed: a report that quietly showed zero cells because
    the map refused to derive would be the most expensive kind of quiet.

    ``channels`` is threaded to :func:`depth_attribution_lines` as well as to the surface, so the
    report and the surface it reports on are the SAME scope -- a channel the caller declined to
    consult must not appear in either half.
    """
    L = ["  THE DERIVED SCENERY PAGE-CELLS (W6b-1: keyed by WRITER and VRAM cell)"]
    try:
        pages, refused = scenery_surface(blob, effect, channels=channels)
    except (RS.ReskinError, EC.ContainerError) as e:
        return L + ["    THE DERIVATION REFUSED: %s: %s" % (type(e).__name__, e)]
    klass, why = program_class(effect)
    L.append("    program-VRAM: %s -- %s" % (klass.upper(), why))
    if not pages and not refused:
        return L + ["    none -- this container declares no page rects and no id-9 alternate block"]
    for p in sorted(pages, key=lambda q: (q.vram, q.name)):
        hz = p.hazards
        # W6b-3 (iv): the READERSHIP marker rides beside the depth source, never inside it --
        # "which depth" and "which reader, at which address" are two kinds of fact.
        L.append("    %-22s %#08x..%#08x  %dx%d %2dbpp[%-7s]%s  VRAM %-11s %-22s %s"
                 % (p.name, p.page_offset, p.page_offset + p.page_bytes, p.w, p.h, p.bpp,
                    p.depth_source, "*" if p.readership == "displaced" else " ",
                    "(%d,%d)" % p.vram,
                    p.palette_name or ("(direct colour)" if p.direct else "(no declared palette)"),
                    ", ".join(hz.names) or "clean"))
    disp = [p for p in pages if p.readership == "displaced"]
    if disp or "so-displaced" in frozenset(channels):
        L.append("    READERSHIP: %d page(s) marked * are read through the MEASURED "
                 "second-array displacement (MODEL %s) -- the cell the hardware SAMPLES, "
                 "not the cell the record BINDS" % (len(disp), DISPLACEMENT_MODEL))
    if refused:
        by: Dict[str, int] = {}
        for r in refused:
            by[r.klass] = by.get(r.klass, 0) + 1
        L.append("    REFUSED %d cell(s): %s"
                 % (len(refused), ", ".join("%s %d" % (k, by[k]) for k in sorted(by))))
    return L + depth_attribution_lines(blob, effect, pages, channels=channels)


def depth_attribution_lines(blob: bytes, effect: Optional[int],
                            pages: Sequence[TexelPage], *,
                            channels: Sequence[str] = EDIT_CHANNELS) -> List[str]:
    """W6b-2's own disclosure block: WHICH CHANNEL spoke, and what the one channel-P cast found.

    Printed for every container, including the ones where nothing spoke -- **a channel that is silent
    here has to say so**, because "no line about channel P" and "channel P states nothing" are the
    same output and only one of them is a measurement. 222 of the corpus's 372 containers declare no
    model at all and are silent by construction; that is the STRUCTURAL CEILING, not a shortfall.

    ⚠ **AND A CHANNEL THE CALLER DECLINED TO CONSULT SAYS NOTHING HERE EITHER.** Channel P's rows are
    already scoped by ``effect``; channel A's are scoped by the ``"so-array"`` token, exactly as
    :func:`scenery_surface` gates ``adv``. This block is report-only, so an ungated derivation moved
    no verdict -- but it was the one place in the module where channel A spoke without being asked,
    and *a law not enforced at every call site is not enforced*.
    """
    ch = frozenset(channels)
    by_src: Dict[str, int] = {s: 0 for s in DEPTH_SOURCES}
    for p in pages:
        by_src[p.depth_source] = by_src.get(p.depth_source, 0) + 1
    n4, n8 = clut_arity(blob)
    hint = DA.clut_arity_hint(n4, n8)
    prog = sorted(k for k in DA.PROGRAM_DEPTH if effect is not None and k[0] == int(effect))
    dual = [k for k in prog if DA.PROGRAM_DEPTH[k].dual]
    adv = RS.array_depth_view(blob) if "so-array" in ch else {}
    a_dual = sum(1 for v in adv.values() if len(v.depths) > 1)
    L = ["", "  THE DEPTH CHANNELS (W6b-2, W6b-3) -- %s" % DA.GRANULARITY_LAW,
         "    depth source: so-uv %d (a reader's own UVs) . so-page %d (CHANNEL G, INHERITED from "
         "the column -- LICENSED) . so-array %d (CHANNEL A, only behind `%s`) . program %d "
         "(CHANNEL P, only behind `%s`)"
         % (by_src["so-uv"], by_src["so-page"], by_src["so-array"], DA.ACK_ARRAY_KEY,
            by_src["program"], DA.ACK_KEY),
         "    CHANNEL P here: %d cell(s) this container's own id-3 program registers a depth for, "
         "%d of them at TWO depths (a REFUSAL, never a vote)" % (len(prog), len(dual)),
         ("    CHANNEL A here: %d cell(s) an entry of a MULTI-PART `so` record names a depth for, "
          "%d of them at TWO depths (a REFUSAL, and it can WITHDRAW a page)" % (len(adv), a_dual))
         if "so-array" in ch else
         "    CHANNEL A here: NOT CONSULTED -- this caller's channel set is %s, and a channel nobody "
         "asked for must not appear to have spoken" % (", ".join(sorted(ch)),),
         "    CHANNEL H here: nClut4 %d / nClut8 %d -> %s"
         % (n4, n8, "no narrowing (the container ships both palette classes)" if hint is None
            else ("4bpp or 15bpp" if hint == 4 else "8bpp or 15bpp") + " -- a NARROWING, not a depth"),
         "    %s" % DA.REGISTRATION_CAVEAT,
         "    %s" % DA.DEPTH_COROLLARY,
         "    %s" % DA.ORDER_UNMEASURED,
         "    %s" % DA.ARRAY_CAVEAT,
         "    %s" % DA.ARRAY_RESIDUE_LINE,
         # W6b-3 (iii): the REPORT-ONLY consumption site of the second-array caveat -- the last of
         # four, after the refusal class, the build gate and the acknowledged disclosure.  It sits in
         # this block rather than in a block of its own because the question it raises -- whether a
         # bound cell is the cell that is READ -- is read THROUGH every depth line above it.
         "    %s" % DA.U_DISPLACEMENT_CAVEAT]
    return L


def derivation_lines(blob: bytes, pages: Sequence[TexelPage]) -> List[str]:
    L = ["  THE DERIVED TEXEL PAGES (from the id-4 header, not from a table)"]
    if not pages:
        L.append("    none -- %s" % (creature_refusal(blob) or "no creature package"))
        return L
    others = other_page_writers(blob)
    for p in pages:
        clash = others.get(p.vram, [])
        L.append("    %-12s %#08x..%#08x  %dx%d %dbpp  VRAM %-11s CLUT row @%#08x (%s)%s"
                 % (p.name, p.page_offset, p.page_offset + p.page_bytes, p.w, p.h, p.bpp,
                    "(%d,%d)" % p.vram, p.clut_offset, p.palette_name,
                    "  ** %d OTHER WRITER(S)" % len(clash) if clash else ""))
    L += ["", "  THE PAGE-WRITER CENSUS (every non-creature page upload this container declares)",
          "    %d declared cell(s); creature band VRAM x [%d,%d) -- corpus: 0 collisions over 24 "
          "packages / 93 pages" % (len(others), CREATURE_VRAM_X[0], CREATURE_VRAM_X[1])]
    # L6, PURE DISCLOSURE: the DECODED table, not "TEXANIM ARMED (N bytes)".  For this lane the
    # protected rect set IS the actionable content -- it is exactly what a localised repaint must
    # co-transform -- so printing a byte count instead was withholding the one number that mattered.
    res = TA.read(blob)
    L += [""] + TA.describe(blob)
    if res.armed and res.table is not None:
        L.append("    creature texel scope is OPEN (W7): a repaint that leaves every protected rect "
                 "alone, or covers each clip family consistently, BUILDS with no key")
    return L


def describe(b: TexelBuild) -> List[str]:
    L = ["ef%03d  %s   [TEXEL REPAINT -- lever #2]" % (b.effect, b.label),
         "  stock source   : %s" % b.source,
         "  stock sha256   : %s  (drift guard %s)" % (b.sha_stock, b.guard),
         "  splice base    : %s" % (b.base_label or "the stock container"),
         "  repaint sha256 : %s" % b.sha_out,
         "  container      : %d B in, %d B out (same length -- every page is spliced in place)"
         % (len(b.orig), len(b.patched)),
         ""]
    if b.region_invariant:
        L += ["  THE REGION INVARIANT (W7 R1, enforced at the build call site)",
              "    %s" % b.region_invariant, ""]
    L += derivation_lines(b.stock, b.pages)
    L += [""] + scenery_lines(b.stock, b.effect)
    L += ["", "  THE TEXEL TARGETS"]
    for t in b.targets:
        if not t.enabled:
            L.append("    off  %-12s %s" % (t.name, t.note or "(disabled -- states an intent)"))
            continue
        cov = ("%d/%d halfwords sampled (%.1f%%)"
               % (t.covered_halfwords, RS.PAGE_CELL_W * CELL_LINES,
                  100.0 * t.covered_halfwords / float(RS.PAGE_CELL_W * CELL_LINES))
               if t.page.scenery else
               ("%d/%d sampled (%.1f%%)" % (t.cov.covered, t.cov.total,
                                            100.0 * t.cov.covered_fraction)
                if t.cov and t.cov.available else "coverage UNAVAILABLE"))
        L.append("    ON   %-12s <- %s  (%s, %dbpp%s)"
                 % (t.name, t.art_source, t.page.kind, t.page.bpp,
                    ", QUANTIZE lane -- indices written, 0 CLUT bytes" if t.quantized else ""))
        L.append("         %5d/%d bytes moved (%.2f%%) | live %d, unsampled %d | cutout punch %d "
                 "fill %d%s | distinct %d->%d | %s"
                 % (len(t.changed), t.page.page_bytes,
                    100.0 * len(t.changed) / max(1, t.page.page_bytes), t.live_changed,
                    t.dead_changed, t.cutout_punch, t.cutout_fill,
                    " (ACKNOWLEDGED)" if t.ack_cutout and t.cutout_flips else "",
                    t.distinct_stock, t.distinct_new, cov))
        for line in census_lines(t.census):
            L.append("         %s" % line)
        for line in t.hazard_notes:
            L.append("         hazard   : %s" % line)
        if t.texanim_note:
            L.append("         texanim  : %s" % t.texanim_note)
        if t.manifest_note:
            L.append("         art guard: %s" % t.manifest_note)
        if t.note:
            L.append("         %s" % t.note)
    return L


def check_lines(b: TexelBuild) -> List[str]:
    c = b.check
    L = ["", "  SELF-CHECK  (%d/%d gates)" % (sum(1 for g in c.gates if g.ok), len(c.gates))]
    for title, gates in (("byte accounting", c.accounting), ("the hard rules", c.rules),
                         ("untouched regions (TEXEL partition)", c.regions),
                         ("orthogonality", c.orthogonality), ("quality", c.quality)):
        L.append("    -- %s" % title)
        for g in gates:
            L.append("    [%s] %s" % ("ok" if g.ok else "!!", g.name))
            L.append("         %s" % g.detail)
    L.append("")
    L.append("    per-target changed bytes: " + (", ".join(
        "%s %d" % (k, v) for k, v in c.per_target.items()) or "none"))
    L.append("    TOTAL %d bytes of %d (%.4f%%)"
             % (len(c.changed), len(b.orig), 100.0 * len(c.changed) / max(1, len(b.orig))))
    return L
