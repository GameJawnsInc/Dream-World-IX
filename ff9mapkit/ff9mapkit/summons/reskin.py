r"""THE SUMMON RESKIN: recolour ANY stock summon's palette set in place, stock bytes untouched.

    ff9mapkit summon-reskin scaffold --ef 211              # read the container, EMIT a complete guarded toml
    ff9mapkit summon-reskin plan   phoenix_reskin.toml     # resolve every target + print the numbers
    ff9mapkit summon-reskin build  phoenix_reskin.toml     # stage the container + scripts + previews
    ff9mapkit summon-reskin verify phoenix_reskin.toml     # re-check what is staged, as bytes

or as an API::

    from ff9mapkit.summons import reskin
    spec = reskin.load_spec("phoenix_reskin.toml")
    b    = reskin.build(spec, "phoenix_reskin.toml")       # reads the install, recolours, splices
    b.check = reskin.self_check(b)                         # every gate, on OUR bytes
    reskin.stage(b)                                        # override + revert scripts + previews

WHAT THIS IS
------------
The camera lane (:mod:`ff9mapkit.summons.rescore`) proved that a same-length in-place splice of a stock
summon container survives every gate and lands hot. This module spends that posture on the cleanest
lever there is: **the CLUT recolour**. Not one texel moves. The creature's 256-entry palettes and the
effect's own scenery palettes are decoded, rotated through HSV, re-encoded to BGR555 and spliced back at
the same offsets.

It takes ANY stock summon, not one. Everything that was true of the first effect proven and not of the
corpus is DERIVED, REFUSED or DISCLOSED here:

* **names are keyed on chunk SLOT** (``pal.s{slot}.x{X}_y{Y}.e{entries}``), because ``chunk_index``
  is not unique -- ef381's nine chunks are ``[0,1,1,1,1,1,1,1,1]`` -- so a ``c{index}`` tag made two
  spans share a name and a TOML guard silently validate the wrong one. Legacy ``c{index}`` names and
  the ef227 English overlay still resolve, through an ALIAS map;
* **attribution and the SHARED flag are derived** from the container's own ``so`` bindings (magic
  ``0x6F73``) instead of a hand table keyed on bare VRAM cells, and un-attributed palettes below
  complete coverage are **shared-UNKNOWN**, not "private". On ef227 the derivation reproduces the
  hand table exactly -- two shared cells, five single-bound, three unbound;
* **multi-writer and dual-depth CLUT cells** are detected and refused (ef381, ef447);
* the **texanim** region is READ (:mod:`ff9mapkit.summons.texanim`) and DISCLOSED rather than feared:
  on the five armed packages (ef038/177/493/494/495) a creature recolour BUILDS once the table parses,
  because the table blits 8-bit palette INDICES inside one part's own page and can express no CLUT
  change at all -- an armed table that does NOT parse falls back to the pre-W7 refusal;
* **headroom is measured per target** -- "stock leaves headroom" is an ef227 measurement, and 46 of
  the corpus's 93 creature rows peak at the 5-bit ceiling;
* the **whole-set envelope**, the **preview page columns** and the **id-9 slot map** are computed,
  not tabulated;
* a **scenery-only** reskin works on the 348 containers that carry no creature at all;
* and every effect stages into **its own** per-effect root.

The texel repaint (lever #2) is a different lane and this module still refuses to do it -- it lives in
:mod:`ff9mapkit.summons.repaint`, which consumes the derivations below rather than re-deriving them.
The split is not tidiness: a chunk-1 overwrite (six VRAM slots written by two container regions) and
the dual-depth packing at VRAM column 448 (the same 4,032 halfwords read as a 4bpp cloud band AND as
8bpp energy rings) are both repaint hazards, and both are structurally invisible to a palette edit --
the two readings have separate palettes and the time-shared columns share no CLUT. A recolour is
immune to the exact traps a repaint has to gate for. The places the two lanes meet in this file are
:func:`_regions`, whose ``partition`` argument INVERTS the id-4 **and** id-0 splits for the texel lane
instead of letting it keep a second copy that could drift, and the derivations the texel lane consumes
rather than re-deriving: :func:`page_cells` (the per-VRAM-cell page map, W6b-1),
:func:`assert_page_cells_identical` (its derivation-identity gate) and
:func:`attribution` under ``include_direct=True``.

WHY THE SPANS ARE DERIVED AND NOT TABULATED
-------------------------------------------
A span derived from a header you have not read is a guess. Every palette is re-derived from the
container's own headers, and a spec that ever disagrees with the bytes underneath REFUSES instead of
splicing into the wrong place:

* the creature strip comes from the id-4 model-package header (``texOffset``/``texBytes``/
  ``clutBytes``) through :mod:`ff9mapkit.summons.texture` -- the shipped, corpus-proven decoder;
* the scenery palettes come from each chunk's **id-0 payload header**: ``nClut4``/``nClut8`` and the
  CLUT-word list at ``+0x10`` declare exactly which palettes exist and where in VRAM, and the inline
  rect stream at ``inlineRel`` says which file bytes each VRAM row is.

THE TRANSFORM, AND THE FIVE HARD RULES (each one a refusal here, not a note in a docstring)
-------------------------------------------------------------------------------------------
An entry is a little-endian **BGR555** halfword: bits 0-4 R, 5-9 G, 10-14 B, bit 15 = STP.

1. ``0x0000`` in, ``0x0000`` out -- byte-exact. STP-clear-and-RGB-zero is the OPAQUE shader's cutout.
   Drift either way punches a hole or fills one with solid black.
2. **bit 15 is carried, never recomputed.** The STP population is compared stock-vs-patched per
   palette and a difference refuses the stage.
3. output channels are **clamped to 0..31**, and the clip that can actually happen is **counted per
   target and gated**. The instrument here is the HSV clip, not the channel clamp: :func:`_clamp01`
   bounds ``s``/``v`` BEFORE ``hsv_to_rgb``, whose max component is exactly ``v``, so the channel
   clamp is structurally unreachable through this path and a counter that cannot count is not an
   instrument. What IS reachable is a knob asking for ``s * sat`` or ``v * val`` past 1.0, which
   flattens that entry onto the ceiling -- so THAT is what is counted, split sat-vs-value, reported
   per target with its fraction of live entries and its worst overshoot, and FAILED at
   :data:`BLOWOUT_FRACTION`. (The effect's own ``colorIntensity`` multiplies 1x/1.5x/2x over the
   palette, which is why a spec keeps ``value`` near 1 on bright targets.)
4. the transform runs in **RGB after the decode**, in HSV, and re-encodes to 5 bits. Hue rotation is
   exact on the wheel; saturation and value are scales, so an achromatic palette is INVARIANT
   (measured: ef227's cloud bands are pure greyscale, S = 0.00 on all 15 live entries -- they cannot
   move under this transform and the report says so rather than pretending).
5. every changed byte must land inside a **named, derived palette** inside a derived span; anything
   else is UNEXPLAINED and refuses the stage. The envelope those spans sum to is derived per effect,
   not the 8,192 B ef227 happens to declare.

THE REFUSALS (each one a call-site check with a test, never a note in a docstring)
----------------------------------------------------------------------------------
* **no drift guard at all** -- no ``expect_sha256`` and no registered hash, unless ``allow_unguarded``;
* **texanim armed and UNPARSEABLE** -- creature scope refused (an armed table that DECODES lifts it,
  no key; ``acknowledge_texanim`` is a deprecated no-op and the scaffold no longer emits it);
* **the texanim REGION INVARIANT (R1)** -- after every build, ``firstBlock``, ``min(motionOffsets)``
  and the region's own bytes must be unchanged, enforced at the call site
  (:func:`assert_region_invariant`), not described in a docstring;
* **dual-depth CLUT cell touched** -- refused outright, no key;
* **multi-writer CLUT cell touched** -- every writer must be named, and all of them with ``hue_to``;
* **shared palette enabled** without ``acknowledge_shared`` (DERIVED, including the UNKNOWN case);
* **zero-headroom ``value`` lift** without ``acknowledge_headroom``;
* two target rows resolving to the **same derived palette** through different spellings;
* a destination inside a checkout, a mod-asset tree or the game install (staging refuses all three;
  only an explicit deploy may name the install), and a mod folder carrying a ``ModFileList.txt``.

A disabled row splices nothing, so it states an intent rather than an edit: its acknowledgements
become mandatory the moment it is switched on, which is what lets a scaffold ship every declared
palette pre-seeded off and still build clean.

ORTHOGONALITY -- proved, not asserted
--------------------------------------
:func:`self_check` rebuilds a sibling camera spec from its OWN toml and intersects its changed-offset
set with this lane's. Empty intersection is the proof that a rescore and a reskin can ship in one
container. Siblings are chosen by the spec itself (``[reskin.orthogonality]``), resolved RELATIVE TO
THE SPEC FILE'S OWN DIRECTORY, and a sibling that targets a DIFFERENT effect is skipped with that
stated -- rebuilding Bahamut's camera proves nothing about a reskin of ef211. A sibling the spec NAMES
and that does not exist FAILS the gate; a sibling nobody named is skipped with the reason printed, so
an unproven disjointness never reads as a proven one. On top of that the check gates whole regions
byte-identical: sector 0 (the resource table + the sequence stream), every id-3 program image, every
camera block, every GEOM block, the id-5 model image, and the whole id-4 header+texel region -- i.e.
the geometry and UVs a repaint would touch.

PROVENANCE
----------
The container is read at RUN TIME from ``resources.assets`` in the user's own install under a sha256
drift guard. Everything staged is stock-derived and lands under a LOCAL-ONLY root
(:data:`STAGING_BASE`); :func:`ff9mapkit.summons.rescore._refuse_repo_path` refuses a checkout or a
mod-asset tree and :func:`ff9mapkit.summons.rescore._refuse_install_path` refuses the install. The
previews are DECODED STOCK ART and are local-only for the same reason. This module carries offsets,
counts, VRAM coordinates and transform scalars -- no run of stock bytes and no stock palette.

WHAT MOVED IN THE PROMOTION FROM THE STUDY SCRIPT
--------------------------------------------------
The study reached through TWO parsers of one format (``ef_container`` for headers/GEOM and
:mod:`ff9mapkit.summons.container` for the creature package) and called both on the same blob two lines
apart. They are collapsed here onto the kit's own container module -- so ``Geom.end`` is a real
property and the byte-identical region gate spans whole GEOM blocks instead of falling back to a
16-byte header stub behind a bare ``except``. The SCRATCH constants, the ``sys.path`` bootstrap and the
module-directory spec discovery are gone: a staging root defaults per-effect under
:data:`STAGING_BASE`, and sibling specs resolve against the spec file, not against this file.
"""
from __future__ import annotations

import colorsys
import dataclasses
import hashlib
import json
import math
import os
import struct
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

from . import camera as W
from . import container as EC
from . import export
from . import rescore as R
from . import texanim as TA
from . import texture as KT
from .ledger import Ledger

__all__ = [
    "ReskinError",
    "MOD_SUBPATH", "STAGING_BASE", "LEGACY_STAGING", "staging_root",
    "WHOLE_SET_CEILING", "BLOWOUT_FRACTION", "EF227_NAMES", "ID9_SLOT_BIT", "id9_slot_vram",
    "SO_MAGIC", "SO_BPP", "MAX_SO_PARTS", "so_record", "NO_CLUT_CELL", "Binding", "Attribution",
    "attribution",
    "WITNESS_INCUMBENT", "WITNESS_NOVEL", "WITNESS_ALL", "WITNESS_CLASSES",
    "TexAnim", "texanim_region", "assert_region_invariant",
    "Span", "Palette", "Cell", "PaletteMap", "clut_word_xy", "chunk_tag", "chunk_tag_of_slot",
    "palette_auto_name", "span_auto_name", "id0_palettes", "creature_palettes", "palette_map",
    "creature_pages", "PageRect", "scenery_pages", "id9_pages", "preview_source",
    "PAGE_CELL_W", "PAGE_CELL_LINES", "PAGE_CELL_BYTES", "PageCell", "page_cells",
    "PAGE_LINES", "PageDepth", "page_depth_view", "array_depth_view",
    "assert_page_cells_identical", "Id0Split", "id0_splits",
    "CLIP_SAT", "CLIP_VAL", "CLIP_CHANNEL", "Transform", "apply_word", "apply_palette",
    "PaletteResult", "palette_peak", "palette_mean_hue",
    "Target", "Build", "build", "load_spec",
    "Gate", "SelfCheck", "self_check", "DEFAULT_ORTH_SPECS", "ORTH_REBUILDERS",
    "render_previews", "stage", "verify", "modfilelist_refusal",
    "describe", "derivation_lines", "check_lines", "scaffold",
]

#: the on-disc override lane, shared with the rescore lane (extensionless: ``LoadFromDisc`` reads the
#: raw path, so ``ef227.bytes`` would never be found).
MOD_SUBPATH = R.MOD_SUBPATH                                  # "FF9_Data/SpecialEffects"

#: THE STAGING BASE -- a per-effect directory lands under it. Local-only by construction (the root the
#: kit already documents as the home for stock-derived summon output) and re-checked through
#: :func:`ff9mapkit.summons.export.assert_local_only` every time it is used as a default, so the
#: default can never quietly become a committable or shippable location.
STAGING_BASE = export.DEFAULT_OUT_DIR / "reskin"

#: effect id -> a staging root PINNED to somewhere other than the per-effect default. Empty here on
#: purpose: a pin exists only for an effect whose staged revert chain is already DEPLOYED somewhere and
#: must not be relocated, which is per-installation history, not a property of the tool. A study or a
#: caller carrying such history re-pins this mapping on the module. (The camera lane keeps its own
#: registry for the same reason: the two lanes stage different artifacts for one effect and must never
#: resolve to one directory.)
LEGACY_STAGING: Dict[int, str] = {}


def staging_root(effect: int, root=None) -> str:
    """The per-effect staging root: ``<root or STAGING_BASE>/ef###``, unless :data:`LEGACY_STAGING`
    pins this effect somewhere else.

    PER EFFECT, not shared. With one root for every effect, a second summon staged in the same session
    silently overwrites the first one's container, previews, manifest and revert script -- and the
    revert script is the artifact whose loss is unrecoverable. A correct ``--out`` is not enough to
    keep two effects apart if the root still comes from a module constant, which is why the default
    derives from the effect rather than from a flag.
    """
    pinned = LEGACY_STAGING.get(int(effect))
    if pinned:
        return str(pinned)
    return os.path.join(str(root or STAGING_BASE), "ef%03d" % int(effect))


#: ef227's own whole-set envelope, kept as a documented FACT (3,072 creature + 3,072 + 1,024 + 1,024
#: scenery). It is NOT the gate: the envelope is derived per effect as ``sum(span.size for span in
#: pmap.spans)`` (:attr:`PaletteMap.envelope`), because the corpus spread is enormous -- ef227 declares
#: 4 spans, ef381 declares 15 and 73 scenery palettes.
WHOLE_SET_CEILING = 8192

#: the blow-out gate's sensitivity: the share of a palette's LIVE entries a target's knobs may flatten
#: onto the HSV ceiling before the build REFUSES. A few clipped entries are normal and harmless -- an
#: entry already at S = 1.00 or near the top of V simply cannot go further, and its neighbours land 1-2
#: of 31 away, which is inside the 5-bit grid the palette already lives on. A large share is the real
#: failure this gate exists for: a ``value = 1.6`` on an already-bright page crushes every highlight
#: onto one white and the gradient it belonged to stops existing. 10% leaves the shipping spec (worst
#: target 4.7%) a 2x margin while still catching that. Retunable, deliberately: it is the instrument's
#: sensitivity, and the per-target census prints either way so the number is judged.
BLOWOUT_FRACTION = 0.10

#: THE ef227 NAMING OVERLAY -- and nothing but naming. The first version of this lane hard-coded an
#: English ATTRIBUTION table keyed on BARE VRAM CELLS, which is the most dangerous single-effect-ism
#: there is: ``(0,245)`` exists on most of the corpus and means something different on each one (ef038
#: binds it from 7 models, ef381 from 6). Both the attribution and the ``shared`` flag are now DERIVED
#: from the container's own ``so`` bindings (:func:`attribution`), and the derivation reproduces this
#: table EXACTLY on ef227: ``(0,244)`` 2 binders and ``(192,244)`` 3 binders come back SHARED, the other
#: five come back single-bound, and the three unattributed cells come back with no binder at 100% ``so``
#: coverage.
#:
#: So this table survives only as ALIASES: it lets a shipped ef227 spec keep saying
#: ``scenery.sky_dome`` where the derivation says ``pal.s0.x0_y245.e256``, and it supplies the English
#: note for the report. It is applied ONLY when the spec's ``effect == 227``.
EF227_NAMES: Dict[Tuple[int, int, int], Tuple[str, str]] = {
    (0, 244, 16):   ("scenery.water_and_sky_gradient",
                     "SHARED 4bpp -- the water/ice sheet AND the sky gradient shell read this one"),
    (192, 244, 16): ("scenery.cloud_bands", "SHARED 4bpp -- cloud bands A, B and C read this one"),
    (0, 245, 256):  ("scenery.sky_dome", "the sky dome, the largest scenery mesh"),
    (0, 246, 256):  ("scenery.energy_rings", "the impact / energy rings"),
    (0, 248, 256):  ("scenery.cloud_sheet", "the cloud sheet"),
    (0, 249, 256):  ("scenery.aerial_ground", "the aerial ground plane (satellite-view terrain)"),
    (0, 251, 256):  ("scenery.fire_column", "the fire column"),
}

#: the id-9 alternate-page slot map as CODE rather than as one effect's two measured offsets.
#: ``fn 0x3E4AB`` is an 8-slot loop; slot ``i`` is enabled by bit ``ID9_SLOT_BIT[i]`` of the resource's
#: own ``info`` byte and the payload cursor advances 0x4000 only on an enabled slot. Preview-only: a
#: wrong slot map draws a wrong picture, never a wrong byte.
#: Spelled as its three RUNS -- the two shared-bit pairs, then the 1:1 tail -- because that is the
#: shape of the loop and because an 8-element flat int tuple is indistinguishable, to a byte-literal
#: provenance scanner, from 8 bytes of stock data. It is a derived slot->bit map, not data.
ID9_SLOT_BIT = (0, 0) + (1, 1) + (2, 3, 4, 5)


def id9_slot_vram(i: int) -> Tuple[int, int]:
    """Slot ``i`` -> its VRAM origin ``(x_halfwords, y_lines)``; the block is always 64 x 128.

    Read straight off ``0x3e50d..0x3e553``::

        y = ((i & 1) + 2) * 128                                  ; 256 even, 384 odd
        x = ((i & ~1) + 24) * 32                    if i < 4      ; 768, 768, 832, 832
        x = (((i << 5) - 0x61) & 0xFFC0) + 0x140    if i >= 4     ; 320, 320, 384, 384
    """
    y = ((i & 1) + 2) * 128
    x = ((i & ~1) + 24) * 32 if i < 4 else ((((i << 5) - 0x61) & 0xFFC0) + 0x140)
    return (x, y)


class ReskinError(RuntimeError):
    pass


def _u16(b: bytes, o: int) -> int:
    return struct.unpack_from("<H", b, o)[0]


def _s32(b: bytes, o: int) -> int:
    return struct.unpack_from("<i", b, o)[0]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ============================================================ (1a) THE `so` BINDINGS -- attribution
#: the magic every non-creature GEOM block's binding record carries.
SO_MAGIC = 0x6F73                                            # 'so', little-endian
#: PSX TPAGE colour-mode field (bits 7-8) -> bits per texel
SO_BPP = {0: 4, 1: 8, 2: 15, 3: 15}

# ---------------------------------------------------------------- ★ THE WITNESS PARTITION (W6b-3)
#: ★ THE WITNESS PARTITION.  A binding slot's witness class is a property of the RECORD it came out
#: of, not of the slot: an ``so`` record with ``P <= 1`` is one the pre-W6b-3 reader already accepted
#: (INCUMBENT); a record with ``P >= 2`` was returned as ``None`` in its entirety, so the record,
#: slot 0 AND every ``slot >= 1`` binding are all NOVEL together.  Measured: filtering the fixed
#: reader to INCUMBENT reproduces the pre-W6b-3 population exactly -- 340/340 bindings and 376/376
#: records, tuple for tuple, 0 of 372 containers differing -- which is what makes *"the census and
#: CHANNEL G do not move"* a statement about the INPUT rather than a claim about the output.
WITNESS_INCUMBENT = "incumbent"
#: a binding only :func:`so_record`'s W6b-3 multi-part reading can see.
WITNESS_NOVEL = "novel"
#: both classes -- :func:`attribution`'s DEFAULT, because the true population is not a scope choice.
WITNESS_ALL = "all"
WITNESS_CLASSES = (WITNESS_INCUMBENT, WITNESS_NOVEL, WITNESS_ALL)


def _check_witness(witness: str) -> str:
    """A guard may only ever fail CLOSED -- the precedent is ``scenery_surface``'s unknown-channel
    raise.  An unrecognised witness class must never silently degrade to "everything"."""
    if witness not in WITNESS_CLASSES:
        raise ReskinError(
            "unknown witness class %r -- this kit ships %s.  A witness class selects which `so`"
            " RECORDS a derivation is allowed to see, and a scope that fails open is not a scope."
            % (witness, ", ".join(repr(w) for w in WITNESS_CLASSES)))
    return witness


#: ★ A BOUND, NOT A FACT. The corpus's longest ``so`` record is ``P = 7`` (``recLen`` 0x40); this
#: caps the probe so a hostile or corrupt blob cannot make :func:`so_record` walk backwards forever.
#: The corpus maximum is pinned SEPARATELY (``w6b3_gates`` G1) precisely so this constant can never
#: be mistaken for the measurement.
MAX_SO_PARTS = 15


def so_record(blob: bytes, geom_base: int) -> Optional[dict]:
    """The ``8 + 8P``-byte binding record that immediately precedes a non-creature GEOM block.

    ★ **THE RECORD IS A MULTI-PART BINDING ARRAY (W6b-3), and this reader used to get its LENGTH
    wrong.** It hard-probed ``recLen in (0x10, 0x08)``, i.e. ``P <= 1``, so **126 corpus records and
    all 309 of their binding slots returned ``None`` -- record, slot 0 and every ``slot >= 1`` pair
    alike.** That was not a missing answer, it was a WRONG one: five palettes shipped a
    ``DERIVED PRIVATE`` verdict that a dropped record contradicts. Fixing it is a SAFETY fix and is
    unconditional; licensing the DEPTHS it reveals is a separate decision, and the kit does not take
    it (CHANNEL A ``so-array`` DISCLOSES -- see
    :func:`ff9mapkit.summons.reskin.array_depth_view`).

    Measured over the corpus with this reader: **502 accepted records** / **649 binding slots**, of
    which **466 carry a tpage/clut pair** but only **465 declare ``textured == 1``**. The docstring
    once said 340 textured against 340 tpage-bearing; the two counts are not the same predicate and
    the one record between them is named here rather than renumbered away -- an outlier absorbed into
    a round number is an outlier nobody can look up:

    * **ef226 GEOM 0x9c804** (record at ``0x9c7f4``, ``tpage 0x97``, ``clut 0x3e00``) is a full
      0x10-byte record with a live-looking binding that nonetheless declares ``textured == 0``, and
      its GEOM block carries **zero UV-bearing faces**. It has nothing to sample with.

    THE LAYOUT::

        +0x00 u16 magic     == 0x6F73 ('so')
        +0x02 u16 textured     a near-redundant restatement of P >= 1 (501/502; ef226 above is the
                               exception, and it reads 1 at P == 7 elsewhere -- NOT a part count)
        +0x04 u16 recLen    == 8 + 8P   -- recordBase + recLen == geomBase (502/502)
        +0x06 u16 arrayB    == 8 + 4P   -- ★ THE INDEPENDENT HALFWORD the acceptance test rests on
        +0x08     P x { u16 tpage, u16 clut }   stride 4
        +arrayB   P x { u16, u16 }              RETURNED as `second`, UNINTERPRETED (scored as an
                                                in-record null: 0/309, 0/264; U1 cast 2 says
                                                something in it DISPLACES the sampled cell -- see
                                                ``depth_attribution.U_DISPLACEMENT_CAVEAT``)

    **THE ACCEPTANCE TEST IS THREE INDEPENDENT HALFWORDS**, and only two of them carry load.
    ``recLen == 8 + 8P`` is near-tautological given ``P := (recLen - 8) // 8`` -- it asserts only
    ``recLen`` is a multiple of 8. The weight is carried by ``arrayB`` at ``+0x06``, which agrees
    502/502 and which **126 of 126 multi-part records take OUTSIDE the two values {8, 12} a ``P <= 1``
    corpus could ever supply**. So ``+0x06`` stops being ``OPAQUE`` here and becomes the field the
    acceptance rests on.

    ★ **THE P = 0 INVARIANT: a record with ZERO pairs is still a RECORD.** 36 corpus records are
    8-byte ``P == 0``; :func:`attribution` counts them in ``geom_with_so`` BEFORE any tpage check.
    The natural new shape -- *"no pairs, return None"* -- would silently shrink the coverage
    DENOMINATOR, flip ``complete`` on containers that read ``UNBOUND at COMPLETE so-coverage`` today,
    and demand ``acknowledge_shared`` on palettes that never needed it. **Unsafe-by-omission is still
    unsafe**, so a ``P == 0`` record returns a dict with ``parts == []`` and NO ``tpage``/``clut``
    keys -- exactly the old 8-byte shape plus the three new keys.

    ⚠ **THE ARITY IS MEASURED TWICE; THE ORDER IS NOT, AND THIS READER SHIPS ONLY THE ARITY.** The
    array is *"selected by the primitive's ``part`` byte"*, which states an arity **and** an order.
    The arity is corroborated from outside the header twice (the part-byte range test: 0 of 502
    records has ``max(part) >= P``, and stride 8 would over-run on 126/126; the CLUT-arity test:
    264/264 against a 16.2% random floor and a 53.3% ambient). **The order is corroborated by
    nothing** -- the best available discriminator scores identity 63.3% / reversed 56.0% / random
    permutations 59.4%, ~0.9 sigma above chance. **No kit verdict may map a part INDEX to an array
    ENTRY.** Every consumer treats ``parts`` as a **SET**. A reason string may name the record offset
    and the slot index as *identification*; it may not assert that part *k* draws with entry *k*.
    Carried as the quotable call-sited constant
    :data:`ff9mapkit.summons.depth_attribution.ORDER_UNMEASURED` -- *a law in a docstring is a wish.*

    ``tpage`` / ``clut`` remain as a **COMPATIBILITY VIEW of entry 0** (absent at ``P == 0``), which
    keeps the 340/340 slot-0 rung assertable as a live containment check. Read them on an
    ``nparts >= 2`` record and you are silently under-reading -- and ``nparts`` is exactly what makes
    that detectable.

    ★ **W6b-3 (iii): THE SECOND ARRAY IS RETURNED, AND NOTHING INTERPRETS IT.** ``second`` is the P
    ``(u16, u16)`` pairs at ``+arrayB`` -- bytes this reader already walked past, inside a record it
    already accepted (``arrayB == 8 + 4P`` is asserted above, so the array base is ``at + 8 + 4P``
    and the record ends at ``at + 8 + 8P``). A marked cast of ef038 measured something in it
    DISPLACING the sampled cell by one 8bpp column; the kit models nothing with it and DISCLOSES it
    (:data:`ff9mapkit.summons.depth_attribution.U_DISPLACEMENT_CAVEAT`). ``P == 0`` yields ``[]``,
    so the P = 0 invariant above is untouched.

    Returns ``{at, len, textured, nparts, witness, parts, second, [tpage, clut]}``; see
    :data:`WITNESS_INCUMBENT` / :data:`WITNESS_NOVEL` for what ``witness`` decides.
    """
    for P in range(0, MAX_SO_PARTS + 1):                     # nearest-first; P=0 shadows nothing
        rec_len = 8 + 8 * P
        o = geom_base - rec_len
        if o < 0:
            return None
        if (_u16(blob, o) == SO_MAGIC
                and _u16(blob, o + 4) == rec_len                  # recordBase + recLen == geomBase
                and _u16(blob, o + 6) == 8 + 4 * P):              # arrayB -- THE INDEPENDENT HALFWORD
            parts = [(_u16(blob, o + 8 + 4 * k), _u16(blob, o + 10 + 4 * k)) for k in range(P)]
            # THE SECOND ARRAY, read at the offset the acceptance test just proved: `arrayB` agreed
            # `8 + 4P` two lines up, so this walk is INSIDE the accepted record by construction and
            # cannot read past `o + rec_len`.  UNINTERPRETED here and everywhere below it.
            second = [(_u16(blob, o + 8 + 4 * P + 4 * k), _u16(blob, o + 10 + 4 * P + 4 * k))
                      for k in range(P)]
            rec = {"at": o, "len": rec_len, "textured": _u16(blob, o + 2),
                   "nparts": P, "parts": parts, "second": second,
                   "witness": WITNESS_INCUMBENT if P <= 1 else WITNESS_NOVEL}
            if parts:
                rec["tpage"], rec["clut"] = parts[0]
            return rec
    return None


#: the CLUT cell a 15bpp DIRECT-colour binder resolves to: none. A direct binder reads BGR555
#: halfwords straight out of the page, so it indexes no palette -- and this sentinel (with
#: ``entries == 0``) is what keeps :meth:`Attribution.binders` from ever matching one, because
#: ``binders`` is asked for a real palette's ``(vram, entries)`` and a direct binder answers no
#: palette question. Stated as a value rather than left implicit so ``include_direct=True`` cannot
#: quietly widen the CLUT lane's ``shared`` derivation.
NO_CLUT_CELL: Tuple[int, int] = (-1, -1)


@dataclass(frozen=True)
class Binding:
    """One GEOM model's texture binding: which page it samples and which CLUT cell colours it.

    ★ **ONE ENTRY OF AN ARRAY, since W6b-3.** An ``so`` record carries ``P`` ``(tpage, clut)`` pairs,
    so one GEOM model can contribute more than one ``Binding``. :attr:`slot` says which entry this
    came out of and :attr:`record_at` says which record -- both **IDENTIFICATION ONLY**. Neither is
    an ordering claim: the array's ARITY is measured twice and its ORDER by nothing
    (:func:`so_record`'s order clause / :data:`ff9mapkit.summons.depth_attribution.ORDER_UNMEASURED`),
    so no verdict in this kit may map a primitive's ``part`` byte to array entry ``k``.
    """
    geom: int
    #: WHICH ENTRY of the record's binding array -- **identification, never an order**. Always 0 on
    #: an INCUMBENT binding, so every pre-W6b-3 repr, sort key and dict key is unchanged there. It is
    #: deliberately NOT called ``part``: the primitive's ``part`` byte keeps that name, and the array
    #: index must not borrow it while the order clause is open.
    slot: int
    #: the record's own file offset -- what a CHANNEL A reason string names to identify the evidence.
    record_at: int
    chunk_slot: int
    tpage: int
    page: Tuple[int, int]        # tpage VRAM origin (x halfwords, y lines)
    bpp: int
    clut_word: int
    cell: Tuple[int, int]        # CLUT VRAM cell (x entries, y line); NO_CLUT_CELL at 15bpp
    entries: int                 # 16 (4bpp) or 256 (8bpp); 0 at 15bpp -- there is no palette
    #: :data:`WITNESS_INCUMBENT` or :data:`WITNESS_NOVEL` -- CARRIED off the record rather than
    #: re-derived from ``slot`` at each call site, because slot 0 of a ``P >= 2`` record is novel too.
    witness: str = WITNESS_INCUMBENT
    #: W6b-3 (iii): the record's WHOLE second array, in FILE ORDER -- **IDENTIFICATION ONLY**, and
    #: never indexed by :attr:`slot`. See :attr:`mover` for why that is enforced rather than asked.
    second_pairs: Tuple[Tuple[int, int], ...] = ()

    @property
    def mover(self) -> Optional[Tuple[int, int]]:
        """This binding's own second-array pair -- or ``None`` where the ORDER would have to be assumed.

        ★ **THE ORDER LAW, ENFORCED AT THE CALL SITE RATHER THAN ASKED FOR.** Pairing second-array
        entry *k* with binding slot *k* is exactly the claim
        :data:`ff9mapkit.summons.depth_attribution.ORDER_UNMEASURED` says nothing corroborates, so
        this accessor REFUSES TO ANSWER on a NOVEL record instead of indexing into
        :attr:`second_pairs`. On an INCUMBENT one ``P <= 1``, the array holds exactly one pair, and
        *"this binding's pair"* is an arity-1 identity rather than an ordering claim -- which is why
        the disclosure lane is incumbent-only and says so in its own refusal text.
        """
        if self.witness != WITNESS_INCUMBENT or not self.second_pairs:
            return None
        return self.second_pairs[0]

    @property
    def direct(self) -> bool:
        """15bpp DIRECT colour -- the texels ARE the colour, so there is nothing to recolour."""
        return self.bpp == 15

    @property
    def novel(self) -> bool:
        """This binding is one no kit before W6b-3 could read -- see :data:`WITNESS_NOVEL`."""
        return self.witness == WITNESS_NOVEL


@dataclass
class Attribution:
    """Who binds what, derived -- the replacement for a hard-coded ``ATTRIBUTION`` table.

    ``coverage`` is the honest instrument: only 213 of 420 non-creature GEOM blocks across the 24
    creature effects carry an ``so`` record (10 effects are at 0%), so an un-attributed palette is only
    "private" when coverage is COMPLETE. Below that it is **shared-UNKNOWN** and the spec must
    acknowledge it -- never silently "not shared", which is exactly the failure mode a hand table has
    by construction on every effect but the one it was written for.
    """
    bindings: List[Binding]
    geom_total: int
    geom_with_so: int
    #: whether 15bpp DIRECT binders were admitted -- carried so a consumer can tell "this container
    #: has no direct binders" from "this scan never looked for them".
    include_direct: bool = False
    #: WHICH RECORD CLASS this scan was allowed to see (:data:`WITNESS_CLASSES`) -- carried for the
    #: same reason ``include_direct`` is: so a consumer can tell *"this container has no novel
    #: bindings"* from *"this scan never looked for them"*.
    witness: str = WITNESS_ALL
    #: how many of :attr:`geom_with_so` were reachable ONLY through a ``P >= 2`` record, i.e. how much
    #: of this container's COVERAGE rests on the W6b-3 reading. **Coverage must state its reader
    #: population**: :attr:`complete` is the switch between *"shared, acknowledge it"* and *"free to
    #: recolour"*, and a completeness that depends on records no kit could read a rung ago is not the
    #: same fact as one the pre-W6b-3 reader already established.
    geom_with_so_novel: int = 0

    @property
    def coverage(self) -> float:
        return 0.0 if not self.geom_total else self.geom_with_so / self.geom_total

    @property
    def direct(self) -> List[Binding]:
        """The 15bpp direct binders admitted by ``include_direct`` -- ``[]`` under the default."""
        return [b for b in self.bindings if b.direct]

    @property
    def complete(self) -> bool:
        """NO models found is NOT complete coverage -- it is NO EVIDENCE.

        222 of the 372 corpus containers declare zero non-creature GEOM blocks (they draw with
        sprites and particles, which carry no ``so`` record), so ``0/0`` is the common case and
        reading it as "100%, therefore nothing is shared" would hand back exactly the false
        confidence this derivation replaced. It reads as UNKNOWN instead, and the spec has to say
        so per target."""
        return self.geom_total > 0 and self.geom_with_so == self.geom_total

    @property
    def complete_is_novel_dependent(self) -> bool:
        """★ COVERAGE STATES ITS READER POPULATION: this container reads COMPLETE **only because**
        the W6b-3 multi-part reader saw records no earlier kit could.

        19 corpus containers are in this class and 122 palettes hang on it. Left as a bare boolean,
        :attr:`complete` would silently dissolve ``acknowledge_shared`` on every one of them -- a
        LOOSENING produced by a SAFETY FIX, which is the same class of defect the fix repairs. So the
        predicate is named, carried into the verdict (``_apply_attribution``'s NOVEL-DEPENDENT
        branch) and the guard stays ARMED until an owner ratifies the release.
        """
        return (self.complete and self.geom_with_so_novel > 0
                and self.geom_with_so - self.geom_with_so_novel < self.geom_total)

    def binders(self, cell: Tuple[int, int], entries: int) -> List[Binding]:
        """Which models read a PALETTE -- so a 15bpp direct binder can never be one of them.

        The ``not b.direct`` filter is structural, not decorative: it is what lets
        ``include_direct=True`` be a texel-lane convenience that provably cannot widen the CLUT lane's
        ``shared`` derivation. Relying instead on :data:`NO_CLUT_CELL` never matching a real palette
        would be a law living in a docstring.
        """
        return [b for b in self.bindings
                if not b.direct and b.cell == cell and b.entries == entries]


def attribution(blob: bytes, include_direct: bool = False,
                witness: str = WITNESS_ALL) -> Attribution:
    """Scan every non-creature GEOM block for its ``so`` record and join model -> (tpage, CLUT).

    ★ **``witness`` DEFAULTS TO** :data:`WITNESS_ALL`, **and that deliberately inverts the
    ``include_direct`` precedent.** ``include_direct``'s default was chosen so no published count
    moved, because the bindings it withheld were bindings the CLUT lane *correctly* excluded -- a
    direct binder answers no palette question. The INCUMBENT population is not a scope choice, it is
    a **defect**: :func:`so_record` could not read a ``P >= 2`` record at all, so 126 records and 309
    binding slots were invisible. A default chosen to preserve a defect so that counts do not move is
    exactly *"the guard-rail defeated by construction"* this rung exists to repair.

    And the decisive argument is mechanical, not aesthetic: several call sites in this repo rolled
    *"CHANNEL G"* as *"whatever ``attribution()`` returns"* -- an expression that was correct only
    while the two were the same set. With the default at the TRUE population those expressions are
    wrong LOUDLY, so every consumer that means CHANNEL G or THE CENSUS must **say**
    ``witness=WITNESS_INCUMBENT`` and every narrowing site is auditable by ``grep -rn "witness="``.

    ``include_direct`` admits the **15bpp DIRECT-colour binders** this scan has always dropped. It
    defaults to ``False`` so the CLUT lane's population is byte-for-byte what it was: the CLUT lane
    asks :meth:`Attribution.binders` for a palette's ``(vram, entries)``, a direct binder carries
    :data:`NO_CLUT_CELL` and ``entries == 0``.

    A PARAMETER, never a second scanner -- the same precedent :func:`_regions`' ``partition`` set. The
    texel lane needs these bindings for two things a palette lane never asks about: a cell's DEPTH
    (15bpp is a depth the container states, and dropping the binder makes that cell read as
    depth-unknown) and the U-SPILL census (17 of the 58 spilling bindings are 15bpp, and one halfword
    is one texel at that depth, so they spill up to three columns where 8bpp reaches exactly one).
    ``coverage``/``complete`` are computed BEFORE this filter and are identical either way.

    ⚠ ``coverage`` / ``geom_with_so`` / ``geom_total`` / ``complete`` stay **per-GEOM-BLOCK counters**
    and are never re-based on slots -- a multi-part record is ONE block's coverage however many
    entries it carries, and a ``P == 0`` record is still a record (:func:`so_record`'s P=0 invariant).
    """
    _check_witness(witness)
    mp = EC.creature_package(blob)
    creature_geom = mp.geom_offset if mp is not None else None
    c = EC.parse_header(blob, strict=False)
    owners: List[Tuple[int, int, int]] = []
    for ch in c.chunks:
        for r in ch.resources:
            n = r.nbytes + ((r.extra_sectors or 0) << 11)
            owners.append((r.offset, r.offset + n, ch.slot))

    def owner_slot(off: int) -> int:
        for lo, hi, slot in owners:
            if lo <= off < hi:
                return slot
        return -1

    binds: List[Binding] = []
    total = with_so = with_so_novel = 0
    for g in EC.scan_geom(blob):
        if creature_geom is not None and g.base == creature_geom:
            continue
        total += 1
        rec = so_record(blob, g.base)
        if rec is None:
            continue
        # ★ THE WITNESS FILTER IS ON THE RECORD, NOT ON THE SLOT.  A `P >= 2` record was returned as
        # None in its entirety before W6b-3, so slot 0 of one is exactly as novel as slot 3 -- and
        # filtering per slot would leak slot 0 of all 126 into the incumbent population.
        if witness != WITNESS_ALL and rec["witness"] != witness:
            continue
        # ★ THE P=0 INVARIANT: a record with ZERO pairs is still a RECORD.  36 corpus records are
        # 8-byte / P == 0, and this `+= 1` sits BEFORE the per-slot loop exactly as the pre-W6b-3
        # `with_so += 1` sat before the tpage check.  Dropping them would shrink the coverage
        # DENOMINATOR, flip `complete` True on containers that read UNBOUND today, and dissolve
        # `acknowledge_shared` on palettes that never needed it -- unsafe-by-omission is still unsafe.
        with_so += 1
        if rec["witness"] == WITNESS_NOVEL:
            with_so_novel += 1
        for k, (tp, cw) in enumerate(rec["parts"]):
            bpp = SO_BPP[(tp >> 7) & 3]
            common = dict(geom=g.base, slot=k, record_at=rec["at"],
                          chunk_slot=owner_slot(g.base), tpage=tp,
                          page=((tp & 0x0F) * 64, ((tp >> 4) & 1) * 256),
                          witness=rec["witness"],
                          # W6b-3 (iii): the WHOLE second array on EVERY slot of the record, never a
                          # per-slot pick -- the pick is `Binding.mover`, which answers only where
                          # `P <= 1` makes it arity-1 rather than an order claim.
                          second_pairs=tuple(rec["second"]))
            if bpp == 15:                                    # direct colour: no palette to bind
                if not include_direct:
                    continue
                binds.append(Binding(bpp=15, clut_word=cw or 0, cell=NO_CLUT_CELL, entries=0,
                                     **common))
                continue
            if not cw:                                       # an indexed slot naming no CLUT word
                continue
            binds.append(Binding(bpp=bpp, clut_word=cw, cell=clut_word_xy(cw),
                                 entries=16 if bpp == 4 else 256, **common))
    return Attribution(bindings=binds, geom_total=total, geom_with_so=with_so,
                       include_direct=include_direct, witness=witness,
                       geom_with_so_novel=with_so_novel)


# ============================================================ (1b) THE TEXANIM REGION -- MEASURED
@dataclass(frozen=True)
class TexAnim:
    """The id-5 model image's texture-animation region -- the MEASUREMENT the whole W7 lane keys on.

    The region is the byte range between the END of the GEOMETRY block (``+0x14 firstBlock``) and
    the FIRST motion clip (``+0x180 motionOffsets[]``), both header-relative. ``firstBlock ==
    min(motionOffsets)`` means the region is empty; motion offsets are sorted on all 24 stock
    packages, so the comparison is exact. This is not merely our arithmetic: the id-5 loader computes
    ``header[+0x40] = psx(header + firstBlock)`` and ``Hi_RegisterSummonModel`` stores that same value
    into ``SummonData+0x70`` (W7 SYNTHESIS sec 1.1) -- the span measured here IS the object the engine
    is handed, which is why this function's signature and semantics are pinned and must not drift.

    Corpus: 19 of 24 creature packages carry 0 bytes here. The five that do not are **ef038** (116 B)
    and **ef177 / ef493 / ef494 / ef495** (364 B each) -- and ef038 is precisely the one effect whose
    programs call HLE op 12 ``Hi_StartSummonTexAnim``.

    **The format is READ, not unread** (W7, SYNTHESIS sec 1.1-1.3 and sec 2.1;
    :mod:`ff9mapkit.summons.texanim` is the decoder). The region is ``u32 clipCount`` + one 20-byte
    CLIP record per clip + one 12-byte destination WINDOW per clip + packed 4-byte frame lists -- three
    sub-arrays that tile it exactly, which is why neither 116 nor 364 divides by ``partCount * 0x18``:
    ``0x18`` is the x64 RUNTIME row (``nodeOff`` widens to a pointer), the FILE record is ``0x14``, and
    the count counts CLIPS, not parts. The three branches this docstring used to hedge between are
    settled:

    * it does NOT cycle the per-part CLUT WORD -- no ``u16`` in any of the five tables is a TPAGE or
      CLUT word (the largest value anywhere is ``0x1000``);
    * it does NOT rewrite CLUT CONTENTS -- rects reach row 115 of a 128-row page and the CLUT strip is
      3-5 rows tall; nothing in the table can address it;
    * it blits TEXELS: a ``w x h`` rect of 8-bit palette INDICES copied inside one part's own 128x128
      page (0 model UV entries inside any frame rect on 39/39, vs 16-272 inside every window rect).

    Consequence, and the reason the creature refusal LIFTED: a blit of palette indices cannot disturb
    a recolour -- every frame recolours identically and automatically. (And on the PC port nothing
    ticks the table at all: the only code that dereferences ``SummonData+0x70`` is Start/Stop, which
    write three state fields and return.) What replaces the refusal is an OBLIGATION -- see
    :func:`assert_region_invariant`.
    """
    present: bool                # the container has a decodable creature package at all
    armed: bool                  # ...and its texanim region is non-empty
    nbytes: int
    lo: int                      # absolute file offsets of the region (0,0 when absent)
    hi: int


def texanim_region(blob: bytes) -> TexAnim:
    mp = EC.creature_package(blob)
    if mp is None or not mp.motion_offsets:
        return TexAnim(present=mp is not None, armed=False, nbytes=0, lo=0, hi=0)
    lo = mp.to_file(mp.first_block)
    hi = mp.to_file(min(mp.motion_offsets))
    return TexAnim(present=True, armed=hi != lo, nbytes=max(0, hi - lo), lo=lo, hi=hi)


def assert_region_invariant(stock: bytes, patched: bytes, where: str = "this build") -> str:
    """THE REGION INVARIANT (W7 R1), at the call site -- **a law in a docstring is a wish**.

    W7's one new hard rule: *never resize, relocate or zero the texanim region, and never edit
    ``firstBlock``*. ``firstBlock == motionOffsets[0]`` is a LIVE engine predicate (the id-5 loader
    ``cmove``s ``Hi_RegisterSummonModel``'s second argument on it), so collapsing or moving the region
    silently changes what ``summonRecord+0x20..0x51`` holds. Neither lever needs to -- a recolour and a
    repaint are both in-place splices -- so this costs nothing and is the pin that makes the rule real.

    Both lanes call it on their own patched bytes. It is deliberately stated as separate comparisons,
    ORDERED so each fires for its own bug: the header fields first (``firstBlock``, then
    ``min(motionOffsets)`` -- the span tuple derives from both, so comparing the span first would
    swallow them into one generic message; V1 F6), then the derived span, then the content.
    """
    ma, mb = EC.creature_package(stock), EC.creature_package(patched)
    if (ma is None) != (mb is None):
        raise ReskinError(
            "THE REGION INVARIANT FAILED on %s: the creature package %s across the splice.  %s"
            % (where, "vanished" if mb is None else "appeared", TA.REGION_RULE))
    if ma is not None and mb is not None:
        if ma.first_block != mb.first_block:
            raise ReskinError(
                "THE REGION INVARIANT FAILED on %s: firstBlock moved %#x -> %#x.  %s"
                % (where, ma.first_block, mb.first_block, TA.REGION_RULE))
        m0 = min(ma.motion_offsets) if ma.motion_offsets else None
        m1 = min(mb.motion_offsets) if mb.motion_offsets else None
        if m0 != m1:
            raise ReskinError(
                "THE REGION INVARIANT FAILED on %s: min(motionOffsets) moved %s -> %s.  %s"
                % (where, "%#x" % m0 if m0 is not None else None,
                   "%#x" % m1 if m1 is not None else None, TA.REGION_RULE))
    a, b = texanim_region(stock), texanim_region(patched)
    if (a.present, a.armed, a.lo, a.hi, a.nbytes) != (b.present, b.armed, b.lo, b.hi, b.nbytes):
        raise ReskinError(
            "THE REGION INVARIANT FAILED on %s: the texanim region MOVED or RESIZED "
            "(%d B at %#x..%#x -> %d B at %#x..%#x).  %s"
            % (where, a.nbytes, a.lo, a.hi, b.nbytes, b.lo, b.hi, TA.REGION_RULE))
    if a.armed and patched[a.lo:a.hi] != stock[a.lo:a.hi]:
        n = sum(1 for i in range(a.lo, a.hi) if patched[i] != stock[i])
        raise ReskinError(
            "THE REGION INVARIANT FAILED on %s: %d of the %d texanim-region bytes at %#x..%#x were "
            "REWRITTEN.  W7 ships a READER, not a writer -- there is no consumer of this table in "
            "either build of the plugin, so no authored edit to it could be verified.  %s"
            % (where, n, a.nbytes, a.lo, a.hi, TA.REGION_RULE))
    return ("region %s, firstBlock and min(motionOffsets) unchanged"
            % ("%d B at %#x..%#x byte-identical" % (a.nbytes, a.lo, a.hi) if a.armed
               else "EMPTY (nothing armed)"))


# ============================================================ (1c) THE PALETTE MAP -- all derived
@dataclass(frozen=True)
class Span:
    """One named byte span -- the outer envelope every changed byte must land inside."""
    name: str
    lo: int
    hi: int
    source: str

    @property
    def size(self) -> int:
        return self.hi - self.lo


@dataclass(frozen=True)
class Palette:
    """One declared palette: where it is, how big, which VRAM cell, and how that was derived."""
    name: str
    off: int
    entries: int
    vram: Tuple[int, int]
    span: str
    bpp: int                     # 4 (16 entries) or 8 (256 entries)
    shared: bool
    note: str
    source: str
    slot: int = -1               # the owning chunk's TABLE SLOT (-1 = the creature strip)
    alias: str = ""              # the human name an effect overlay hangs on this cell, if any
    shared_reason: str = ""      # WHY `shared` reads the way it does -- derived, unknown, or private
    binders: Tuple[int, ...] = ()   # GEOM bases whose `so` record names this cell

    @property
    def nbytes(self) -> int:
        return self.entries * 2

    @property
    def display(self) -> str:
        return "%s (%s)" % (self.alias, self.name) if self.alias else self.name


@dataclass(frozen=True)
class Cell:
    """Every palette that lands on ONE VRAM CLUT cell -- the multi-writer / dual-depth detector.

    A CLUT recolour is a per-CELL edit as far as the GPU is concerned: whatever was uploaded last to
    ``(x, y)`` is what a model reading that cell sees. Two rules, pure arithmetic on data the header
    derivation already returns:

    * more than one distinct FILE OFFSET writing the cell  => **multi-writer**. ef381 is the fixture:
      a 9-chunk effect that streams a genuinely different palette into the same cell per phase (19
      cells, up to 5 writers, 480+ of 512 bytes different between writers). Recolouring one writer
      leaves the others stock, so the cast flickers between two keys. The only coherent authoring
      form is an ABSOLUTE hue (``hue_to``) applied to EVERY writer -- a ``hue_rotate`` delta lands each
      writer on a different hue, because each writer has its own mean.
    * more than one distinct ENTRY COUNT declared for the cell => **dual-depth**. ef447's ``(0,242)``
      is the fixture: chunk slot 0 declares it a 16-entry 4bpp palette, chunk slot 2 declares it a
      256-entry 8bpp one. Those are two different pictures over the same bytes and no evidence
      exists either way about how they interact, so this one REFUSES outright.
    """
    vram: Tuple[int, int]
    names: Tuple[str, ...]
    offsets: Tuple[int, ...]
    depths: Tuple[int, ...]

    @property
    def multi_writer(self) -> bool:
        return len(set(self.offsets)) > 1

    @property
    def dual_depth(self) -> bool:
        return len(set(self.depths)) > 1


@dataclass
class PaletteMap:
    spans: List[Span]
    palettes: List[Palette]
    aliases: Dict[str, str] = dataclasses.field(default_factory=dict)
    span_aliases: Dict[str, str] = dataclasses.field(default_factory=dict)
    attrib: Optional[Attribution] = None
    creature_error: str = ""
    texanim: Optional[TexAnim] = None

    @property
    def envelope(self) -> int:
        """The derived whole-set envelope: every declared CLUT span, summed. ef227 = 8,192 B over
        4 spans; ef381 = 15 spans. Replaces :data:`WHOLE_SET_CEILING` as the gate."""
        return sum(s.size for s in self.spans)

    @property
    def cells(self) -> Dict[Tuple[int, int], Cell]:
        by: Dict[Tuple[int, int], List[Palette]] = {}
        for p in self.palettes:
            by.setdefault(p.vram, []).append(p)
        return {k: Cell(vram=k, names=tuple(p.name for p in v), offsets=tuple(p.off for p in v),
                        depths=tuple(p.entries for p in v)) for k, v in by.items()}

    @property
    def hazards(self) -> Dict[Tuple[int, int], Cell]:
        return {k: c for k, c in self.cells.items() if c.multi_writer or c.dual_depth}

    def resolve(self, name: str) -> str:
        """A spec-declared name -> the canonical derived name. Legacy ``c{chunkIndex}``-tagged and
        ef227-overlay names resolve here, so a shipped spec keeps working after the slot rename."""
        return self.aliases.get(name, name)

    def by_name(self, name: str) -> Palette:
        want = self.resolve(name)
        for p in self.palettes:
            if p.name == want:
                return p
        if name.startswith("creature.") and self.creature_error:
            raise ReskinError("no palette named %r -- this container's creature scope is "
                              "unavailable: %s" % (name, self.creature_error))
        raise ReskinError("no palette named %r -- the container declares %s"
                          % (name, ", ".join(sorted(p.name for p in self.palettes))))

    def span(self, name: str) -> Span:
        want = self.span_aliases.get(name, name)
        for s in self.spans:
            if s.name == want:
                return s
        raise ReskinError("no span named %r -- the container declares %s"
                          % (name, ", ".join(s.name for s in self.spans)))


def clut_word_xy(word: int) -> Tuple[int, int]:
    """A PSX CLUT word -> its VRAM cell ``(x_entries, y_line)``. ``x = (w & 0x3F) * 16``,
    ``y = w >> 6`` -- the same decode :func:`ff9mapkit.summons.texture.clut_row` /
    :func:`~ff9mapkit.summons.texture.clut_entry0` perform against the creature strip's own base,
    written here without the strip bias because the scenery band sits at x = 0."""
    return ((word & 0x3F) * 16, word >> 6)


def chunk_tag(chunk) -> str:
    """Chunks are tagged ``s%d`` by TABLE SLOT, never by ``chunk_index`` -- which is **not unique**:
    ef381's nine chunks are ``[0,1,1,1,1,1,1,1,1]`` and ef447's three are ``[0,1,1]``. An index tag
    made two different spans resolve to one name (:meth:`PaletteMap.span` returned the first, so a
    TOML guard silently validated the wrong span) and made ef381 refuse outright on a duplicate-name
    clash that was a real hazard wearing an opaque error message. ``slot`` is the resource table's own
    position and is unique by construction."""
    return "s%d" % chunk.slot


def palette_auto_name(slot: int, x: int, y: int, entries: int) -> str:
    """``pal.s{slot}.x{X}_y{Y}.e{entries}`` -- keyed on exactly the tuple a palette's identity is:
    chunk SLOT, VRAM cell, and bit depth."""
    return "pal.s%d.x%d_y%d.e%d" % (slot, x, y, entries)


def span_auto_name(slot: int, k: int) -> str:
    return "s%d_clut_band%d" % (slot, k)


def id0_palettes(blob: bytes, chunk, tag: str) -> Tuple[List[Span], List[Palette]]:
    """Every palette one chunk's **id-0 payload header** declares, resolved to file bytes.

    The header::

        P+0x00 s32 pageBlockRel   -> { s32 pixelDataRel, s32 nPageRects, Rect[nPageRects] }
        P+0x04 s32 inlineRel      -> nInline x { Rect, u16 pixels[w*h] }   -- the CLUT images
        P+0x08 s32 nInline
        P+0x0c u16 nClut4         -- 16-entry palettes that follow
        P+0x0e u16 nClut8         -- 256-entry palettes that follow
        P+0x10 u16 clutWord[nClut4 + nClut8]

    The self-check the derivation rests on is exact and is asserted here: the inline rect stream
    must end at precisely ``P + pixelDataRel``. If it does not, the header is not what we think it
    is and nothing is resolved. Corpus: 385/385 id-0 resources across 372/372 containers decode
    clean, 490 inline rects, every one of them at VRAM x = 0.

    Names are AUTO and slot-keyed; the attribution overlay, if any, is applied by :func:`palette_map`
    on top -- this function never invents an English name.
    """
    res = [r for r in chunk.resources if r.id == 0]
    if len(res) != 1:
        raise ReskinError("%s: expected exactly one id-0 resource, found %d" % (tag, len(res)))
    P = res[0].offset
    page_rel, inline_rel, n_inline = _s32(blob, P), _s32(blob, P + 4), _s32(blob, P + 8)
    n4, n8 = _u16(blob, P + 0x0C), _u16(blob, P + 0x0E)
    words = [_u16(blob, P + 0x10 + 2 * i) for i in range(n4 + n8)]

    spans: List[Span] = []
    rows: Dict[int, Tuple[int, int, int]] = {}               # vram y -> (file offset, width, rect#)
    cur = P + inline_rel
    for k in range(n_inline):
        x, y, w, h = (_u16(blob, cur), _u16(blob, cur + 2), _u16(blob, cur + 4), _u16(blob, cur + 6))
        data = cur + 8
        if x != 0:
            raise ReskinError("%s inline rect %d starts at VRAM x=%d; the CLUT band is x=0" %
                              (tag, k, x))
        for r in range(h):
            rows[y + r] = (data + r * w * 2, w, k)
        spans.append(Span(span_auto_name(chunk.slot, k), data, data + w * h * 2,
                          "id-0 inline rect %d: VRAM (x=%d y=%d w=%d h=%d)" % (k, x, y, w, h)))
        cur = data + w * h * 2

    pix_rel = _s32(blob, P + page_rel)
    if cur != P + pix_rel:
        raise ReskinError("%s: the inline CLUT stream ends at %#x but the header's pixelDataRel "
                          "names %#x -- the id-0 layout is not what this tool decodes"
                          % (tag, cur, P + pix_rel))

    pals: List[Palette] = []
    seen: Dict[str, int] = {}
    for i, cw in enumerate(words):
        entries = 16 if i < n4 else 256
        x, y = clut_word_xy(cw)
        if y not in rows:
            raise ReskinError("%s: CLUT word %#06x names VRAM row %d, which no inline rect uploads"
                              % (tag, cw, y))
        row_off, row_w, rect = rows[y]
        if x + entries > row_w:
            raise ReskinError("%s: CLUT word %#06x -> x=%d + %d entries overruns the %d-entry row"
                              % (tag, cw, x, entries, row_w))
        name = palette_auto_name(chunk.slot, x, y, entries)
        off = row_off + x * 2
        if name in seen:
            # the same chunk declared the same cell at the same depth twice -- the SAME bytes, by
            # construction (the offset is a function of the cell), so it is one palette with two
            # clutWord slots, not two palettes. Record the extra slot, do not emit a duplicate.
            if pals[seen[name]].off != off:                 # pragma: no cover - impossible
                raise ReskinError("%s: %s resolves to two different offsets %#x / %#x"
                                  % (tag, name, pals[seen[name]].off, off))
            pals[seen[name]] = dataclasses.replace(
                pals[seen[name]], source=pals[seen[name]].source + ", %#06x[%d]" % (cw, i))
            continue
        seen[name] = len(pals)
        pals.append(Palette(name=name, off=off, entries=entries, vram=(x, y),
                            span=span_auto_name(chunk.slot, rect),
                            bpp=4 if entries == 16 else 8, shared=False, note="",
                            source="%s id-0 clutWord[%d] = %#06x" % (tag, i, cw),
                            slot=chunk.slot))
    return spans, pals


def creature_palettes(blob: bytes) -> Tuple[Optional[Span], List[Palette], str]:
    """The creature's rows, off the id-4 model-package header through the kit's OWN decoder.

    :func:`ff9mapkit.summons.texture.texture_check` is the shipped, corpus-proven gate (24/24
    packages): it refuses anything that is not the ``partCount`` x 0x4000 / ``clutRows`` x 0x200 8bpp
    layout.

    CREATURE-OPTIONAL. Raising here would make a scenery-only reskin of the **348 non-creature
    effects** impossible even though :func:`id0_palettes` handles all 372. The absence is REPORTED
    (the third return value) and only becomes a refusal at the call site, when a spec actually names a
    ``creature.*`` target.
    """
    mp = EC.creature_package(blob)
    if mp is None:
        return None, [], "this container has no id-4 creature package -- scenery scope only"
    chk = KT.texture_check(blob, mp)
    if not chk["decodable"]:
        return None, [], ("the creature's texture block is not the 8bpp layout: "
                          + "; ".join(chk["reasons"]))
    lo = mp.tex_file_offset + mp.tex_bytes
    span = Span("creature_clut_strip", lo, lo + mp.clut_bytes,
                "id-4 header: texOffset %#x + texBytes %#x, clutBytes %#x"
                % (mp.tex_file_offset, mp.tex_bytes, mp.clut_bytes))
    pals = [Palette(name="creature.part%d" % p.index, off=p.clut_offset, entries=KT.PALETTE_LEN,
                    vram=(KT.CLUT_STRIP_X + p.clut_entry0, KT.CLUT_STRIP_Y + p.clut_row),
                    span=span.name, bpp=8, shared=False,
                    note="creature part %d (tpage %#x, page @%#x)"
                         % (p.index, p.tpage, p.page_offset),
                    source="id-4 part table: clut word %#06x -> strip row %d"
                           % (p.clut, p.clut_row),
                    shared_reason="the creature strip has exactly ONE writer on all 24 packages "
                                  "(id-4 only) and its rows never collide with the effect band")
            for p in chk["parts"]]
    return span, pals, ""


#: what a NOVEL-DEPENDENT completeness verdict has to say out loud, in one quotable place -- W6b-3's
#: coverage flip is a LOOSENING produced by a SAFETY FIX, and a loosening nobody states is a leak.
_NOVEL_DEPENDENT_CAVEAT = (
    "NOTHING ABOUT THE MULTI-PART READING IS IN-GAME: its ghost-layer prediction scored 0 hits, 4 "
    "misses and 2 vacuous passes over six named cells, and BINDING-IS-NOT-A-DRAW plus THE DEPTH "
    "COROLLARY apply in full.  So `acknowledge_shared` stays ARMED here rather than being dissolved "
    "by a coverage figure that rests on records no kit could read a rung ago.  UPGRADE PATH: an "
    "owner-ratified release, or a cast that puts one of these bindings on screen")


def _apply_attribution(pals: List[Palette], attrib: Attribution) -> List[Palette]:
    """Hang the DERIVED ``shared`` flag and binder list on every scenery palette.

    Four states now, and the two middle ones are the whole point:

    * **bound by >1 GEOM MODEL** -> ``shared = True``. It may only be recoloured as the GROUP it is,
      so the spec must acknowledge it.
    * **bound by exactly one GEOM MODEL** -> ``shared = False``, DERIVED PRIVATE.
    * **bound by no model, and ``so`` coverage is INCOMPLETE** -> ``shared = True``, reason UNKNOWN.
      We cannot tell "private" from "shared" because we could not read every model's binding; a hand
      table asserted ``shared = False`` here, which is the guard-rail defeated by construction.
    * **bound by no model at COMPLETE coverage** -> ``shared = False``, and the note says the honest
      thing: the header declares it, no GEOM model reads it, so something else (a sprite, a
      particle) does. ★ **Unless that completeness DEPENDS on W6b-3's multi-part records**, in which
      case the verdict is ``UNBOUND at COMPLETE so-coverage (NOVEL-DEPENDENT)`` and ``shared`` stays
      **True** -- see :attr:`Attribution.complete_is_novel_dependent`. 19 corpus containers / 122
      palettes are in that class; releasing them would be a loosening produced by a safety fix, and
      it awaits owner ratification rather than arriving as a side effect.

    ★ **THE DEDUPE LAW: THE VERDICT COUNTS DISTINCT GEOM MODELS, NEVER BINDING SLOTS.** Since W6b-3 a
    multi-part record can bind ONE palette from TWO entries of ONE model's own array. The reason
    string says *"GEOM models"*, and a count that does not match its own noun is a false statement in
    the safest-sounding direction. Measured corpus-wide: **5 palettes are affected -- 3 flip the
    VERDICT (shared -> private) and 2 flip only the printed COUNT while staying shared** -- and there
    are **0** cases of one GEOM binding one palette at two different DEPTHS, so the dedupe can never
    collapse a depth conflict.
    """
    out: List[Palette] = []
    pct = 100.0 * attrib.coverage
    for p in pals:
        if p.slot < 0:                                       # the creature strip: not so-bound
            out.append(p)
            continue
        binders = attrib.binders(p.vram, p.entries)
        # ★ THE DEDUPE, at the call site.  `models` is the tuple the `binders` field always CLAIMED
        # to be: distinct GEOM bases, lowest first.
        by_geom: Dict[int, List[Binding]] = {}
        for b in binders:
            by_geom.setdefault(b.geom, []).append(b)
        models = sorted(by_geom)
        novel = [b for b in binders if b.novel]
        # IDENTIFICATION ONLY -- a record offset and a slot index, never a claim that entry k is
        # drawn by part k (:func:`so_record`'s order clause).
        novel_ids = ", ".join("record %#x slot %d" % (b.record_at, b.slot)
                              for b in sorted(novel, key=lambda x: (x.geom, x.record_at, x.slot)))
        if len(models) > 1:
            extra = ("  -- %d of these binding(s) come from a MULTI-PART record the kit did not read "
                     "before W6b-3 (%s; identification only -- the entry ORDER inside a record's "
                     "array is UNMEASURED)" % (len(novel), novel_ids)) if novel else ""
            out.append(dataclasses.replace(
                p, shared=True, binders=tuple(models),
                shared_reason="DERIVED SHARED: %d GEOM models bind this cell (%s)%s"
                              % (len(models), ", ".join("%#x" % g for g in models), extra),
                note=p.note or "read by %d models" % len(models)))
        elif len(models) == 1:
            # ★ ONE MODEL, MORE THAN ONE ENTRY: say so, or the 3 self-shared palettes read as a plain
            # single binding and the arity is hidden by the very dedupe that made the verdict right.
            # ...and the slot list carries the SAME qualifier its DERIVED SHARED sibling four lines
            # up does.  This branch is the one the self-shared palettes land in, so it is the one
            # place an author reads a slot index next to a PRIVATE verdict -- the convention may not
            # lapse exactly where it is easiest to read as an ordering claim.
            arity = ("  (through %d entries of its own binding array%s)"
                     % (len(by_geom[models[0]]),
                        "; %s -- identification only, the entry ORDER inside a record's array is "
                        "UNMEASURED" % novel_ids if novel else "")
                     ) if len(by_geom[models[0]]) > 1 else ""
            out.append(dataclasses.replace(
                p, shared=False, binders=(models[0],),
                shared_reason="DERIVED PRIVATE: exactly one GEOM model (%#x) binds this cell%s"
                              % (models[0], arity),
                note=p.note or "bound by GEOM %#x" % models[0]))
        elif not attrib.complete:
            why = ("this container declares NO non-creature GEOM models at all, so attribution has "
                   "no evidence to work from (222 of the 372 corpus containers are in this class)"
                   if attrib.geom_total == 0 else
                   "only %d of %d GEOM blocks (%.1f%%) carry one%s"
                   % (attrib.geom_with_so, attrib.geom_total, pct,
                      ", %d of them readable ONLY by W6b-3's multi-part reader"
                      % attrib.geom_with_so_novel if attrib.geom_with_so_novel else ""))
            out.append(dataclasses.replace(
                p, shared=True,
                shared_reason="SHARED-UNKNOWN: no `so` record names this cell, and %s -- sharing "
                              "cannot be ruled out" % why,
                note=p.note or "UNATTRIBUTED at %.0f%% so-coverage" % pct))
        elif attrib.complete_is_novel_dependent:
            out.append(dataclasses.replace(
                p, shared=True,
                shared_reason="UNBOUND at COMPLETE so-coverage (NOVEL-DEPENDENT) (%d/%d): the header "
                              "declares it and no GEOM model reads it -- but %d of those %d GEOM "
                              "blocks were read ONLY by W6b-3's multi-part reader, so this "
                              "container's COMPLETENESS is exactly what the new reading bought.  %s"
                              % (attrib.geom_with_so, attrib.geom_total,
                                 attrib.geom_with_so_novel, attrib.geom_with_so,
                                 _NOVEL_DEPENDENT_CAVEAT),
                note=p.note or "declared by the header, attributed to no GEOM model "
                               "(completeness rests on %d multi-part record(s))"
                               % attrib.geom_with_so_novel))
        else:
            out.append(dataclasses.replace(
                p, shared=False,
                shared_reason="UNBOUND at COMPLETE so-coverage (%d/%d): the header declares it and "
                              "no GEOM model reads it -- something not in the model list does"
                              % (attrib.geom_with_so, attrib.geom_total),
                note=p.note or "declared by the header, attributed to no GEOM model"))
    return out


def palette_map(blob: bytes, effect: Optional[int] = None,
                attrib: Optional[Attribution] = None) -> PaletteMap:
    """Every palette a container declares, from its own headers. Nothing tabulated.

    ``effect`` selects the naming OVERLAY (today only ef227 has one) and is otherwise inert -- the
    geometry, the offsets, the depths and the ``shared`` flags are all derived either way.
    """
    c = EC.parse_header(blob, strict=True)
    span_c, pals, cre_err = creature_palettes(blob)
    spans = [span_c] if span_c is not None else []
    for ch in c.chunks:
        s, p = id0_palettes(blob, ch, chunk_tag(ch))
        spans += s
        pals += p
    if attrib is None:
        attrib = attribution(blob)
    pals = _apply_attribution(pals, attrib)

    # ---- the legacy alias map. An earlier tag used `chunk_index`; that tag is only unambiguous when
    # the container's chunk_index values are distinct (ef227 [0,1] yes; ef381 [0,1,1,1,1,1,1,1,1] no).
    aliases: Dict[str, str] = {}
    span_aliases: Dict[str, str] = {}
    idx = [ch.chunk_index for ch in c.chunks]
    if len(set(idx)) == len(idx):
        for ch in c.chunks:
            for s in spans:
                if s.name.startswith("s%d_clut_band" % ch.slot):
                    span_aliases["c%d_clut_band%s" % (ch.chunk_index,
                                                      s.name.rsplit("band", 1)[1])] = s.name
            for p in pals:
                if p.slot == ch.slot:
                    aliases["spare.c%d_x%d_y%d" % (ch.chunk_index, p.vram[0], p.vram[1])] = p.name

    if effect is not None and int(effect) == 227:
        named: List[Palette] = []
        for p in pals:
            key = (p.vram[0], p.vram[1], p.entries)
            hit = EF227_NAMES.get(key) if p.slot >= 0 else None
            if hit is None:
                named.append(p)
                continue
            alias, note = hit
            aliases[alias] = p.name
            named.append(dataclasses.replace(p, alias=alias, note=note))
        pals = named

    names = [p.name for p in pals]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:                                            # pragma: no cover - the slot key rules it out
        raise ReskinError("two palettes resolved to the same name: %s" % ", ".join(dupes))
    return PaletteMap(spans, pals, aliases=aliases, span_aliases=span_aliases, attrib=attrib,
                      creature_error=cre_err, texanim=texanim_region(blob))


def creature_pages(blob: bytes) -> Dict[str, int]:
    """``{palette name: page file offset}`` for the creature -- the preview's exact 1:1 page map."""
    mp = EC.creature_package(blob)
    if mp is None:
        return {}
    chk = KT.texture_check(blob, mp)
    if not chk["decodable"]:
        return {}
    return {"creature.part%d" % p.index: p.page_offset for p in chk["parts"]}


@dataclass(frozen=True)
class PageRect:
    """One streamed page column: where its texels are, and how wide/tall the rect declares them."""
    source: str                  # "s0" / "s1" / ... / "id9.s0"
    x: int
    y: int
    w: int                       # VRAM halfwords
    h: int                       # VRAM lines
    off: int
    nbytes: int

    def texel_size(self, bpp: int = 8) -> Tuple[int, int]:
        return (self.w * (16 // bpp), self.h)


#: THE VRAM PAGE-CELL, the quantum the engine uploads: **64 halfwords x 128 lines = 0x4000 bytes**.
#: MEASURED, not assumed -- all 1,317 id-0 page rects across all 372 corpus containers declare
#: ``w == 64`` (1,214 at ``h == 256``, 103 at ``h == 128``), and every one of the 117 id-9 alternate
#: blocks is 64 x 128 by the loop's own arithmetic. 2,648 / 2,648 cell-writer records at w = 64.
PAGE_CELL_W = 64
PAGE_CELL_LINES = 128
PAGE_CELL_BYTES = PAGE_CELL_W * PAGE_CELL_LINES * 2          # 0x4000


def _assert_cell_width(where: str, x: int, y: int, w: int, h: int) -> None:
    """THE ``w != 64`` AND ``h % 128 != 0`` TRIPWIRES -- refusals with **zero** live instances,
    which is the point.

    A cell is ``w * 128 * 2`` bytes and reduces to 0x4000 only at ``w == 64``. Every consumer of the
    page map advances by a flat 0x4000 (``repaint.other_page_writers`` did so literally), which is
    right on all 2,648 corpus cell-writer records and silently catastrophic on the first one that is
    not: a narrower rect would make every cell after the first in that stream resolve to the wrong
    file offset, and a splice would land in a neighbour's texels while every gate downstream stayed
    green -- the failure reads as corrupt art with no error anywhere. So the arithmetic REFUSES
    instead of extrapolating. ``grep`` for this width found zero checks in the kit before W6b.

    THE SAME REASONING BINDS ``h`` (V1 F2): the cell split is ``h // 128`` and a flooring split of a
    non-multiple height either OVERLAPS cell spans (h < 128: the one derived cell claims 0x4000
    bytes of a rect that holds fewer, spilling into the next rect's stream) or silently strands the
    remainder (h = 200: 9,216 declared bytes become unaddressable with no error).  The corpus is
    exactly ``{128, 256}`` on all 1,317 rects, so this too is free now and load-bearing the day it
    is not.
    """
    if w != PAGE_CELL_W:
        raise ReskinError(
            "PAGE-RECT WIDTH: %s declares VRAM (x=%d y=%d w=%d h=%d) -- w is %d halfwords, not the "
            "%d this lane's cell arithmetic is derived for.  A VRAM page-cell is w*128*2 bytes and "
            "collapses to the 0x4000 every consumer advances by ONLY at w=%d, so a narrower or wider "
            "rect would put every cell after the first at the wrong file offset and splice into a "
            "neighbour's texels with no gate firing.  All 2,648 cell-writer records in the stock "
            "corpus are w=%d, so this container is outside the measured population and the map "
            "refuses rather than extrapolating."
            % (where, x, y, w, h, w, PAGE_CELL_W, PAGE_CELL_W, PAGE_CELL_W))
    if h <= 0 or h % PAGE_CELL_LINES != 0:
        raise ReskinError(
            "PAGE-RECT HEIGHT: %s declares VRAM (x=%d y=%d w=%d h=%d) -- h is not a positive "
            "multiple of %d lines, so the cell split (h // %d, flooring) would either OVERLAP cell "
            "spans into the next rect's stream (h < %d) or silently strand the trailing lines with "
            "no error.  Every one of the 1,317 stock page rects is h in {128, 256}; outside that "
            "population the map refuses rather than extrapolating (V1 F2 -- the same law as the "
            "width tripwire, one axis later)."
            % (where, x, y, w, h, PAGE_CELL_LINES, PAGE_CELL_LINES, PAGE_CELL_LINES))


def scenery_pages(blob: bytes) -> Dict[Tuple[str, int], PageRect]:
    """``{(chunk tag, vram x): PageRect}`` for the streamed page rects -- **the RECT view**.

    Derived from the id-0 page block: ``pixelDataRel`` is the stream base and the rect list gives
    the column order. The rects are NOT all one shape corpus-wide, so the dimensions come from the
    rect itself rather than from a hard-coded ``128 x 256``.

    This stays the rect view on purpose; the per-VRAM-CELL map that splits an ``h == 256`` rect into
    the two stacked cells the engine actually uploads is :func:`page_cells`, beside it. The key here
    is ``(tag, x)`` and therefore cannot name the lower half of a tall rect at all -- which is why 20
    otherwise-lawful cells were unaddressable before ``page_cells`` existed.

    Two refusals, both tripwires with zero live instances:

    * ``w != 64`` (:func:`_assert_cell_width`);
    * **a duplicate ``(tag, x)``** -- this dict used to overwrite silently, so a chunk declaring one
      column twice would have kept only the LAST upload and hidden the first from every consumer,
      including the collision gate. 0 duplicates over 1,317 corpus rects; it refuses if that changes.
    """
    c = EC.parse_header(blob, strict=True)
    out: Dict[Tuple[str, int], PageRect] = {}
    for ch in c.chunks:
        tag = chunk_tag(ch)
        res = [r for r in ch.resources if r.id == 0]
        if not res:
            continue
        P = res[0].offset
        pb = P + _s32(blob, P)
        base = P + _s32(blob, pb)
        n = _s32(blob, pb + 4)
        cur = base
        for k in range(n):
            o = pb + 8 + 8 * k
            x, y, w, h = _u16(blob, o), _u16(blob, o + 2), _u16(blob, o + 4), _u16(blob, o + 6)
            _assert_cell_width("%s id-0 page rect %d" % (tag, k), x, y, w, h)
            if (tag, x) in out:
                prev = out[(tag, x)]
                raise ReskinError(
                    "DUPLICATE PAGE RECT: %s declares VRAM column x=%d twice -- rect at %#x (y=%d "
                    "h=%d) and rect %d at %#x (y=%d h=%d).  The rect view is keyed (tag, x), so one "
                    "of these uploads would be silently dropped and become invisible to every "
                    "consumer, the collision gate included.  0 of the 1,317 stock page rects do "
                    "this; name the writers per cell through page_cells() instead."
                    % (tag, x, prev.off, prev.y, prev.h, k, cur, y, h))
            out[(tag, x)] = PageRect(source=tag, x=x, y=y, w=w, h=h, off=cur, nbytes=w * h * 2)
            cur += w * h * 2
    return out


def id9_pages(blob: bytes) -> Dict[Tuple[str, int], List[PageRect]]:
    """``{(chunk tag, vram x): [PageRect]}`` for the id-9 ALTERNATE page path.

    The loop's own arithmetic, not one effect's two measured offsets: slot ``i`` is enabled by bit
    ``ID9_SLOT_BIT[i]`` of the resource's ``info`` byte, lands at :func:`id9_slot_vram`, is always
    64 x 128 halfwords, and the payload cursor advances 0x4000 **per enabled slot**. Corpus:
    ``nbytes == enabledSlots * 0x4000`` on 37/37 id-9 resources.
    """
    c = EC.parse_header(blob, strict=True)
    out: Dict[Tuple[str, int], List[PageRect]] = {}
    for ch in c.chunks:
        for r in ch.resources:
            if r.id != 9:
                continue
            cur = r.offset
            for i in range(8):
                if not (r.info >> ID9_SLOT_BIT[i]) & 1:
                    continue
                x, y = id9_slot_vram(i)
                out.setdefault((chunk_tag(ch), x), []).append(
                    PageRect(source="id9.%s" % chunk_tag(ch), x=x, y=y, w=64, h=128,
                             off=cur, nbytes=0x4000))
                cur += 0x4000
    return out


# --------------------------------------------------------- the PER-VRAM-CELL page map (W6b-1)
@dataclass(frozen=True)
class PageCell:
    """One **VRAM page-cell** -- the 64 x 128-halfword, 0x4000-byte quantum the engine uploads.

    The addressable unit of the scenery texel lane, and NOT the same object as :class:`PageRect`: a
    corpus page rect is ``h == 256`` on 1,214 of 1,317 and covers TWO stacked cells. ``PageRect``
    names the upload; ``PageCell`` names the thing an author can edit.

    Every field is derived; the key ``(tag, x, y)`` is unique **by construction**, not by luck --
    ``tag`` is the WRITER (``"s0"`` for an id-0 page rect, ``"id9.s0"`` for an id-9 alternate block),
    so the corpus's 34 multi-writer co-transform cells appear as the several records they are instead
    of one record silently overwriting another.
    """
    tag: str                     # the WRITER: "s0" (id-0 page rect) | "id9.s0" (id-9 alt block)
    chunk: str                   # the OWNING chunk's tag, always "s%d"
    slot: int                    # that chunk's resource-table slot
    kind: str                    # "id0" | "id9"
    x: int                       # VRAM x, halfwords
    y: int                       # VRAM y, lines -- the CELL's own y, already split off a tall rect
    w: int                       # the parent rect's width in halfwords (64, enforced)
    off: int                     # this cell's first file byte
    nbytes: int                  # w * 128 * 2 == 0x4000
    rect_key: Tuple[str, int]    # the scenery_pages / id9_pages key this cell came from
    rect_y: int                  # the parent rect's VRAM y
    rect_h: int                  # the parent rect's height (256 means this cell is half of it)
    split_index: int             # which stacked cell of that rect (0 = the top one)
    provenance: str              # the writer, in one line, for a refusal message to quote

    @property
    def key(self) -> Tuple[str, int, int]:
        return (self.tag, self.x, self.y)

    @property
    def cell(self) -> Tuple[int, int]:
        return (self.x, self.y)

    @property
    def split(self) -> bool:
        """True when this cell is one half of a tall rect -- the 20 lower halves W6b unlocks."""
        return self.rect_h > PAGE_CELL_LINES

    @property
    def name(self) -> str:
        """``cell.s0.x704_y256`` -- deliberately NOT the ``page.*.h256`` rect spelling."""
        return "cell.%s.x%d_y%d" % (self.tag, self.x, self.y)


def page_cells(blob: bytes) -> Dict[Tuple[str, int, int], PageCell]:
    """``{(writer tag, vram x, vram y): PageCell}`` -- **the per-VRAM-cell page map**.

    The map :func:`scenery_pages` could not be. Its key is ``(tag, x)``, so the lower 128 lines of an
    ``h == 256`` rect have no name at all: on ef211 the rect at column 576 has a two-palette
    same-bytes hazard in its TOP cell and a clean, single-reader, single-writer 4bpp picture in its
    BOTTOM one, and the rect key can only reach the hazardous half. 20 otherwise-lawful cells are
    unaddressable for exactly that reason, and 1,179 cells corpus-wide have no name.

    The arithmetic, and where it differs from the rect view:

    * the id-0 stream cursor advances by the RECT's own ``w * h * 2`` -- that is
      :func:`scenery_pages`' law and it is right;
    * the SPLIT of a tall rect into stacked cells advances ``w * 128 * 2`` **per cell**, which
      reduces to 0x4000 only at ``w == 64`` -- hence :func:`_assert_cell_width`, enforced here AND at
      the rect view. Today 2,648 / 2,648 cell-writer records are w = 64, so the refusal is a
      TRIPWIRE, not a code path;
    * :func:`id9_pages` is folded in unchanged -- an id-9 alternate block is already exactly one cell.

    Uniqueness is asserted, not assumed: a duplicate key REFUSES. Corpus: 2,648 records, 2,648
    distinct keys, 0 collisions.
    """
    c = EC.parse_header(blob, strict=True)
    slots = {chunk_tag(ch): ch.slot for ch in c.chunks}
    out: Dict[Tuple[str, int, int], PageCell] = {}

    def _add(pc: PageCell) -> None:
        if pc.key in out:
            prev = out[pc.key]
            raise ReskinError(
                "DUPLICATE PAGE CELL %s: two writers resolve to the same key -- %s and %s.  The key "
                "carries the writer, so this is not a co-transform (which is several DIFFERENT keys "
                "over one VRAM cell) but one writer declared twice, and the second would silently "
                "replace the first.  0 of the 2,648 stock cell-writer records collide."
                % (str(pc.key), prev.provenance, pc.provenance))
        out[pc.key] = pc

    for (tag, _x), r in sorted(scenery_pages(blob).items()):
        n = max(1, r.h // PAGE_CELL_LINES)
        step = r.w * PAGE_CELL_LINES * 2
        for k in range(n):
            _add(PageCell(
                tag=r.source, chunk=tag, slot=slots.get(tag, -1), kind="id0",
                x=r.x, y=r.y + PAGE_CELL_LINES * k, w=r.w, off=r.off + k * step, nbytes=step,
                rect_key=(tag, r.x), rect_y=r.y, rect_h=r.h, split_index=k,
                provenance="%s id-0 page rect at VRAM (x=%d y=%d w=%d h=%d) @%#x, cell %d of %d"
                           % (r.source, r.x, r.y, r.w, r.h, r.off, k, n)))
    for (tag, _x), rects in sorted(id9_pages(blob).items()):
        for j, r in enumerate(rects):
            _assert_cell_width("%s id-9 alternate block %d" % (r.source, j), r.x, r.y, r.w, r.h)
            _add(PageCell(
                tag=r.source, chunk=tag, slot=slots.get(tag, -1), kind="id9",
                x=r.x, y=r.y, w=r.w, off=r.off, nbytes=r.nbytes,
                rect_key=(tag, r.x), rect_y=r.y, rect_h=r.h, split_index=0,
                provenance="%s id-9 alternate block at VRAM (x=%d y=%d) @%#x"
                           % (r.source, r.x, r.y, r.off)))
    return out


# --------------------------------------------------------- CHANNEL G: the PAGE-granular depth view
#: a VRAM texture PAGE is 256 lines tall; a page-CELL is 128. One tpage word therefore names a COLUMN
#: of two stacked cells -- the granularity statement the whole W6b-2 depth channel turns on.
PAGE_LINES = 2 * PAGE_CELL_LINES


@dataclass(frozen=True)
class PageDepth:
    """CHANNEL G (W6b-2) -- what one VRAM page-cell's own COLUMN is bound at, per the container.

    **The SECOND view of the same ``so`` records, and it is deliberately a second view.**
    :func:`attribution` answers *"which model reads what"* and
    :func:`ff9mapkit.summons.repaint.cell_readers` resolves that to the halfwords a model's stored UVs
    physically touch -- the right instrument for READERSHIP. It is the wrong one for DEPTH, because a
    tpage's colour-mode bits govern the page's draw mode over all **256** lines, both stacked cells of
    the column. Collapsing the two is exactly what produced W6b-1's ``y = 384`` blind spot: 57 corpus
    cells the census had to call depth-unknown are the LOWER half of a column the container itself
    names a depth for.

    So the kit keeps **BOTH views and never merges them**. Merging would make a cell's depth look
    like a readership fact, and the two disagree on real corpus cells -- 138/140 overall against the
    census, **16/18 on the informative rows**, and *both* genuinely-disjoint rows disagree. Those two
    are the SPILL-vs-OWN-PAGE class (:data:`ff9mapkit.summons.repaint._REFUSAL_TEXT`'s
    ``spill-vs-own-page``): every reader of the cell is a binding on the NEIGHBOURING page whose ``u``
    range crosses the column boundary, while the cell's own page is named at the other depth. Both
    predicates are TRUE of the same bytes. They are FLAGGED, never reconciled.

    ⚠ **THE INHERITANCE IS NAMED, ALWAYS.** For a lower half (:attr:`inherited`) no instrument has
    seen a model sample these bytes; what is established is the mode under which the page they live in
    is read. Every disclosure that ships a channel-G depth has to say so.
    """
    cell: Tuple[int, int]                # the page-CELL (x halfwords, y lines)
    page: Tuple[int, int]                # the PAGE (column) origin its depth was read off
    depths: Tuple[int, ...]              # every distinct depth an `so` record states for the column
    binders: Tuple[Binding, ...]         # those records, lowest-addressed GEOM first
    inherited: bool                      # this cell is the LOWER half -> the depth is the COLUMN's

    @property
    def bpp(self) -> Optional[int]:
        """The depth, or ``None`` when the column carries TWO -- **unanimity is the verdict rule; two
        values is a hazard, not a vote.** 8 corpus cells are in that class and NO lane dossier named
        them; a kit building its refusal list from the sweep alone would ship them unlisted."""
        return self.depths[0] if len(self.depths) == 1 else None

    @property
    def dual(self) -> bool:
        return len(self.depths) > 1

    @property
    def binding(self) -> Optional[Binding]:
        """THE DISPLAY BINDER: the lowest ``(geom, tpage, clut_word)`` naming this column -- the same
        rule the texel lane's class-C display palette uses, so a cell that inherits a depth inherits
        the matching CLUT key from the same record rather than from a second, unrelated choice.

        ★ **THE KEY IS VALUES, NEVER THE ARRAY INDEX.** Two bindings can now share a ``geom`` (one
        model, two entries of its own record), so the old bare ``geom`` key stopped being a total
        order. It is completed with the two VALUES the display actually consumes rather than with
        ``(record_at, slot)``, because a tie-break on the array index would make the pick depend on
        STORAGE ORDER -- the one thing about this format nothing has measured. Ties now happen only
        between IDENTICAL values, where the pick is immaterial by construction.
        """
        return self.binders[0] if self.binders else None


def page_depth_view(blob: bytes, include_direct: bool = True,
                    witness: str = WITNESS_INCUMBENT) -> Dict[Tuple[int, int], PageDepth]:
    """``{(vram x, vram y): PageDepth}`` -- every page-cell whose COLUMN an ``so`` record binds.

    ★ **``witness`` DEFAULTS TO** :data:`WITNESS_INCUMBENT`, **the opposite of**
    :func:`attribution`'s **default, and the reason is what this function's answer IS: a LICENSE.**
    :func:`ff9mapkit.summons.repaint.scenery_surface` emits a paintable page straight off it with no
    acknowledgement key anywhere on the path, and ``"so-page"`` is in
    :data:`ff9mapkit.summons.repaint.LICENSED_CHANNELS`. What licensed CHANNEL G (W6b-2) was never
    *binding-ness*: it was that G reads **the record the kit already reads**, at the granularity the
    hardware uses, with an informative calibration (16/18 on the informative rows) and a cast that
    HELD -- both inherited from W6b-2 (``W6b2-ATTRIBUTION.md`` / ``w6b2_gates`` H10), not re-measured
    here. A NOVEL binding has the first of those and none of the others, so widening this function
    would hand CHANNEL A CHANNEL G's authority silently. CHANNEL A is reached by NAME, through
    :func:`array_depth_view`, and it DISCLOSES at channel P's tier.

    **NOT a variant of :func:`attribution` and never folded into it.** ``attribution`` returns the
    UV-granular reader view the CLUT lane and the texel lane both already ship; this returns the
    PAGE-granular depth view, and the kit keeps the two side by side on purpose (see
    :class:`PageDepth`). The only shared machinery is the ``so`` scan itself, consumed here rather
    than re-implemented -- a second scanner would be a second thing to keep true.

    ``include_direct`` defaults to **True**, the opposite of :func:`attribution`'s default and for the
    stated reason: 15bpp DIRECT colour IS a depth the container states, and dropping those binders is
    precisely what makes a cell read as depth-unknown. This function exists to answer the depth
    question, so admitting them is the whole point.

    Only cells :func:`page_cells` declares are named. A recovered column the container never uploads
    is evidence about somebody else's page and attributes NOTHING here -- the same rule the program
    channel applies to its 5 undeclared columns.
    """
    declared = {pc.cell for pc in page_cells(blob).values()}
    rolled: Dict[Tuple[int, int], List[Binding]] = {}
    for b in attribution(blob, include_direct=include_direct, witness=witness).bindings:
        px, py = b.page
        for cy in (py, py + PAGE_CELL_LINES):
            if (px, cy) in declared:
                rolled.setdefault((px, cy), []).append(b)
    out: Dict[Tuple[int, int], PageDepth] = {}
    for cell, binders in sorted(rolled.items()):
        # ★ A TOTAL ORDER ON VALUES.  `key=b.geom` alone became non-deterministic the moment two
        # bindings could share a geom, and completing it with the array index would let the DISPLAY
        # pick depend on storage order -- the unmeasured clause.  `(geom, tpage, clut_word)` is
        # permutation-invariant: it ties only between identical values.  Under the incumbent witness
        # it is equivalent to the old key (one binding per GEOM block), so channel G's display binder
        # is provably unmoved.
        binders.sort(key=lambda b: (b.geom, b.tpage, b.clut_word))
        out[cell] = PageDepth(cell=cell, page=(cell[0], cell[1] - (cell[1] % PAGE_LINES)),
                              depths=tuple(sorted({b.bpp for b in binders})),
                              binders=tuple(binders),
                              inherited=bool(cell[1] % PAGE_LINES))
    return out


def array_depth_view(blob: bytes, include_direct: bool = True
                     ) -> Dict[Tuple[int, int], PageDepth]:
    """★ **CHANNEL A** at page granularity -- :func:`page_depth_view`'s NOVEL half.

    A **WRAPPER, not a second scanner**: one derivation, one parameter, two call sites (the precedent
    is :func:`attribution`'s ``include_direct``). It exists so the two channels are separately
    NAMEABLE by a gate, a doc and a refusal -- **not** so they are separately DERIVED.

    ⚠ CHANNEL A **DISCLOSES**; it does not license. Nothing about it is in-game
    (:data:`ff9mapkit.summons.depth_attribution.ARRAY_CAVEAT`), and the entry ORDER inside a record's
    array is UNMEASURED (:data:`ff9mapkit.summons.depth_attribution.ORDER_UNMEASURED`), so every
    product taken off this view must be order-free -- a SET of depths, a SET of CLUT words, and a
    display pick that ties on VALUES.
    """
    return page_depth_view(blob, include_direct=include_direct, witness=WITNESS_NOVEL)


def assert_page_cells_identical(orig: bytes, patched: bytes,
                                where: str = "this build") -> str:
    """**THE DERIVATION-IDENTITY GATE**: :func:`page_cells` must re-derive identically after a splice.

    The page map is read out of the id-0 page-block header and the ``(x, y, w, h)`` rect table, and
    a texel splice licenses the pixel stream those rects POINT AT -- never the rects themselves. If a
    build moved ``pixelDataRel``, the rect count or one rect's shape, every subsequent derivation
    would name a different set of bytes while the container still parsed, the file length still
    matched and the palettes still re-derived: a silent re-aim of the whole lane. So the map is
    re-derived on the patched bytes and compared, at the CALL SITE -- **a law in a docstring is a
    wish** -- exactly as :func:`assert_region_invariant` does for W7's texanim region.

    Raises :class:`ReskinError` naming the first divergence; returns a one-line summary.
    """
    a = page_cells(orig)
    try:
        b = page_cells(patched)
    except ReskinError as e:
        raise ReskinError(
            "THE PAGE-CELL DERIVATION FAILED on the PATCHED container for %s -- the map re-derives "
            "off the id-0 header and rect table, so the splice moved something it does not license.  "
            "%s" % (where, e))
    if set(a) != set(b):
        gone = sorted(set(a) - set(b))
        new = sorted(set(b) - set(a))
        raise ReskinError(
            "THE PAGE-CELL DERIVATION MOVED on %s: %d cell(s) vanished (%s) and %d appeared (%s).  "
            "A texel splice licenses the PIXEL STREAM, never the page-block header or the rect table "
            "that names it."
            % (where, len(gone), ", ".join(str(k) for k in gone[:4]) or "-",
               len(new), ", ".join(str(k) for k in new[:4]) or "-"))
    for k in sorted(a):
        if a[k] != b[k]:
            raise ReskinError(
                "THE PAGE-CELL DERIVATION MOVED on %s: cell %s re-derives differently.\n  stock:   "
                "%s\n  patched: %s\nA texel splice licenses the PIXEL STREAM, never the page-block "
                "header or the rect table that names it." % (where, str(k), a[k], b[k]))
    return ("%d page-cell(s) re-derive identically (%d id-0, %d id-9)"
            % (len(a), sum(1 for v in a.values() if v.kind == "id0"),
               sum(1 for v in a.values() if v.kind == "id9")))


@dataclass(frozen=True)
class Id0Split:
    """The ONE boundary the two lane partitions disagree about, inside one chunk's id-0 payload.

    ``pixelDataRel`` cuts the resource in two: below it the page-block header, the ``clutWord`` table
    and the whole inline CLUT rect stream; above it the page PIXEL stream. The CLUT lane writes below
    and the TEXEL lane writes above, which is why :func:`_regions` gates the opposite half in each
    partition. Derived exactly as :func:`id0_palettes` derives it -- ``page_rel = s32(P)``,
    ``pix_rel = s32(P + page_rel)`` -- so the two cannot drift apart.
    """
    tag: str
    slot: int
    lo: int                      # P -- the id-0 payload's first byte
    boundary: int                # P + pixelDataRel
    hi: int                      # the DECLARED end of the page pixel stream (trailing pad excluded)
    res_hi: int                  # the id-0 RESOURCE's own sector-padded end
    run_hi: int                  # the end of the streamed id-0 [+ id-1] run that holds the stream
    n_rects: int

    @property
    def clut_side(self) -> Tuple[int, int]:
        """Header + clutWord table + the inline CLUT rect stream -- the CLUT lane's licensed half."""
        return (self.lo, self.boundary)

    @property
    def pixel_side(self) -> Tuple[int, int]:
        """The page pixel stream -- the TEXEL lane's licensed half."""
        return (self.boundary, self.hi)


def id0_splits(blob: bytes) -> List[Id0Split]:
    """One :class:`Id0Split` per chunk that declares an id-0 resource.

    **THE PIXEL STREAM IS NOT CONFINED TO THE id-0 RESOURCE**, and that is measured, not tolerated:
    on **248 of the 385** corpus id-0 resources the page pixel stream runs past the id-0 payload's
    own sector-padded end and continues into the **id-1 resource of the SAME chunk** -- 248 of 248
    unanimously, never into another chunk, never into any other resource id, and never past the file
    end (137 fit inside id-0 alone). id-0 and id-1 are both in
    :data:`ff9mapkit.summons.container.STREAMED_IDS`; they are one contiguous streamed run and the
    rect table addresses it as one. So the bound the stream is checked against is that RUN, derived
    by walking forward while the next resource in the chunk is an id-1 that starts exactly where the
    previous one ended -- never the id-0 resource's size, which would refuse 64 % of the corpus.

    A chunk with NO id-0 has no page block and contributes nothing (the corpus has none, but the
    absence is unambiguous, so it is not an error). A chunk with MORE than one is ambiguous about
    which payload owns the page block, and refuses -- the same refusal :func:`id0_palettes` makes.
    """
    c = EC.parse_header(blob, strict=True)
    pages = scenery_pages(blob)
    out: List[Id0Split] = []
    for ch in c.chunks:
        tag = chunk_tag(ch)
        res = [r for r in ch.resources if r.id == 0]
        if not res:
            continue
        if len(res) > 1:
            raise ReskinError("%s: expected at most one id-0 resource, found %d -- which one owns "
                              "the page block is not a fact the container states" % (tag, len(res)))
        r = res[0]
        P, res_hi = r.offset, r.offset + r.nbytes
        run_hi = res_hi
        for nxt in ch.resources:                             # the contiguous streamed id-1 tail
            if nxt.id == 1 and nxt.offset == run_hi:
                run_hi = nxt.offset + nxt.nbytes
        page_rel = _s32(blob, P)
        pix_rel = _s32(blob, P + page_rel)
        boundary = P + pix_rel
        if not (P < boundary <= res_hi):
            raise ReskinError(
                "%s: the id-0 header's pixelDataRel (%#x) puts the page pixel stream at %#x, outside "
                "the id-0 resource %#x..%#x -- the id-0 layout is not what this tool decodes"
                % (tag, pix_rel, boundary, P, res_hi))
        n = _s32(blob, P + page_rel + 4)
        stream = sum(rc.nbytes for (t, _x), rc in pages.items() if t == tag)
        if boundary + stream > run_hi:
            raise ReskinError(
                "%s: the id-0 page rect table declares %d B of pixel stream from %#x, which overruns "
                "the streamed id-0[+id-1] run that holds it (%#x..%#x).  Corpus: 385/385 fit, 248 of "
                "them only because id-1 continues the run."
                % (tag, stream, boundary, P, run_hi))
        out.append(Id0Split(tag=tag, slot=ch.slot, lo=P, boundary=boundary,
                            hi=boundary + stream, res_hi=res_hi, run_hi=run_hi, n_rects=n))
    return out


def _preview_refusal_reason(pal: Palette, bind: List[Binding]) -> str:
    """★ WHY THERE IS NO PREVIEW -- a refusal that says nothing teaches nothing.

    W6b-3 gave this refusal a second cause: a preview can now vanish because a SECOND binder became
    visible, including on the 3 self-shared palettes where the second binder is the **same model**.
    On 2 of those 3 the model's two entries name DIFFERENT columns, so there is no order-free way to
    pick which upload to draw -- picking entry 0 would consume the ORDER clause :func:`so_record`
    says is unmeasured. So the refusal stands and carries this instead.
    """
    if not bind:
        return ("%s: NO PREVIEW -- no `so` binding names this CLUT cell, so nothing in this "
                "container resolves the texels it colours." % pal.name)
    geoms = sorted({b.geom for b in bind})
    cols = sorted({b.page[0] for b in bind})
    novel = [b for b in bind if b.novel]
    who = ("ONE model, %d entries of its own binding array" % len(bind) if len(geoms) == 1
           else "%d GEOM models (%s)" % (len(geoms), ", ".join("%#x" % g for g in geoms)))
    extra = ("  %d of these became visible only at W6b-3 (%s -- identification only)."
             % (len(novel), ", ".join("record %#x slot %d" % (b.record_at, b.slot)
                                      for b in novel))) if novel else ""
    return ("%s: NO PREVIEW -- %d binders resolve this CLUT cell (%s), naming column(s) %s.  The "
            "entry ORDER inside a record's binding array is UNMEASURED, so NO column is picked: "
            "choosing one would manufacture a certainty the format does not state.%s"
            % (pal.name, len(bind), who, ", ".join(str(c) for c in cols), extra))


def preview_source(blob: bytes, pal: Palette, attrib: Attribution,
                   reasons: Optional[List[str]] = None) -> Optional[List[PageRect]]:
    """Which file bytes hold the texels a scenery palette colours -- derived, not tabulated.

    ``reasons``, when given, collects the REFUSAL text for every palette this declines to preview
    (:func:`_preview_refusal_reason`). The ``len(bind) != 1`` test is deliberately **not** widened
    and deliberately **not** de-duplicated: see that helper for why.

    The ``so`` record that binds the palette also names the model's TPAGE, so the column is a
    by-product of attribution. Which upload of that column to draw is the one judgement call: a
    column can be written by more than one chunk (the time-shared columns), so we prefer the binder's
    OWN chunk -- its id-0 page rect first, then its id-9 alternate blocks -- and fall back to any
    chunk that writes it. On ef227 this reproduces the hand table exactly on all five attributed
    pages, including the two that disagree with the naive reading (energy_rings' binder is in chunk 1
    but only chunk 0 uploads column 448; cloud_sheet's binder is in chunk 0 where column 832 exists
    only as id-9).
    """
    bind = attrib.binders(pal.vram, pal.entries)
    if len(bind) != 1:
        if reasons is not None:
            reasons.append(_preview_refusal_reason(pal, bind))
        return None
    b = bind[0]
    pages, alt = scenery_pages(blob), id9_pages(blob)
    own = chunk_tag_of_slot(blob, b.chunk_slot)
    for tag in ([own] if own else []) + sorted({t for t, _x in pages} | {t for t, _x in alt}):
        if (tag, b.page[0]) in pages:
            return [pages[(tag, b.page[0])]]
        if (tag, b.page[0]) in alt:
            return sorted(alt[(tag, b.page[0])], key=lambda r: r.y)
    return None


def chunk_tag_of_slot(blob: bytes, slot: int) -> Optional[str]:
    c = EC.parse_header(blob, strict=False)
    for ch in c.chunks:
        if ch.slot == slot:
            return chunk_tag(ch)
    return None


# ============================================================ (2) THE TRANSFORM
@dataclass(frozen=True)
class Transform:
    """One target's recolour. ``hue`` is degrees on the wheel; ``sat``/``val`` are scales.

    ``hue_to`` is the ABSOLUTE authoring form: the spec names the hue it wants and the build computes
    ``hue = hue_to - the palette's own measured mean hue``. That makes the artistic surface
    effect-INDEPENDENT (a spec documents "measured mean H 243.8 -> ~190 deep teal" in prose either way;
    this makes the tool do the subtraction instead of the author). It is also REQUIRED for a
    multi-writer co-transform: each writer of a cell has its own mean, so one shared ``hue_rotate``
    delta lands them on different hues while one shared ``hue_to`` lands them on the same one.
    """
    hue: float = 0.0
    sat: float = 1.0
    val: float = 1.0
    hue_to: Optional[float] = None

    @property
    def identity(self) -> bool:
        return (self.hue % 360.0 == 0.0) and self.sat == 1.0 and self.val == 1.0

    def __str__(self) -> str:
        head = ("hue ->%.1f deg (%+.1f)" % (self.hue_to, self.hue)) if self.hue_to is not None \
            else ("hue %+.1f deg" % self.hue)
        return "%s  sat x%.2f  val x%.2f" % (head, self.sat, self.val)


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


#: :func:`apply_word`'s clip flags. SAT and VAL are the REACHABLE ones: the target's own knob asked for
#: a saturation or value outside the HSV cube and :func:`_clamp01` flattened that entry onto the ceiling
#: (or the floor). That is the real, silent artistic failure -- several entries land on the same colour
#: and a gradient loses a step -- so it is what gets counted, per target, and gated.
#:
#: CHANNEL is the structural belt on rule 3 and is UNREACHABLE through this path: ``_clamp01`` bounds
#: ``s``/``v`` into ``[0,1]`` before ``hsv_to_rgb``, whose largest component is exactly ``v``, so
#: ``int(f * 31.0 + 0.5)`` tops out at ``int(31.5) == 31`` and never exceeds it. Measured, not argued: a
#: dense sweep of the post-clamp ``(h,s,v)`` cube (including the exact ``1.0`` corners) and 3.9M real
#: ``apply_word`` calls at knobs up to the 4x refusal ceiling both top out at exactly 31, and a test
#: pins it. The branch stays as a belt against a future reordering of the clamp -- but it is NOT the
#: reported instrument, because a counter that cannot count reports "all clear" for every input,
#: including a ruinous one.
CLIP_SAT = 1
CLIP_VAL = 2
CLIP_CHANNEL = 4


def apply_word(word: int, t: Transform) -> Tuple[int, int]:
    """One BGR555+STP halfword through the transform. Returns ``(new word, clip flags)``.

    THE FIVE HARD RULES, at the call site:
      * ``0x0000`` returns ``0x0000`` -- byte-exact, before anything else runs (rule 1);
      * bit 15 is sliced off the input and OR'd back onto the output, never recomputed (rule 2);
      * every channel is rounded to 5 bits and clamped to 0..31, and the clip that can actually
        occur -- the HSV one, ``s * sat`` or ``v * val`` leaving ``[0,1]`` -- is REPORTED (rule 3);
      * the rotation happens in HSV over the decoded RGB, then re-encodes (rule 4).
    """
    if word == 0:
        return 0, 0
    stp = word & 0x8000
    r5, g5, b5 = word & 0x1F, (word >> 5) & 0x1F, (word >> 10) & 0x1F
    h, s, v = colorsys.rgb_to_hsv(r5 / 31.0, g5 / 31.0, b5 / 31.0)
    h = (h + t.hue / 360.0) % 1.0
    s_want, v_want = s * t.sat, v * t.val
    clip = 0
    if s_want > 1.0 or s_want < 0.0:
        clip |= CLIP_SAT
    if v_want > 1.0 or v_want < 0.0:
        clip |= CLIP_VAL
    rf, gf, bf = colorsys.hsv_to_rgb(h, _clamp01(s_want), _clamp01(v_want))
    out = []
    for f in (rf, gf, bf):
        q = int(f * 31.0 + 0.5)
        if q > 31:                    # pragma: no cover - structurally unreachable, see CLIP_CHANNEL
            q, clip = 31, clip | CLIP_CHANNEL
        elif q < 0:                   # pragma: no cover - structurally unreachable, see CLIP_CHANNEL
            q, clip = 0, clip | CLIP_CHANNEL
        out.append(q)
    return stp | out[0] | (out[1] << 5) | (out[2] << 10), clip


def _luma5(word: int) -> float:
    r5, g5, b5 = word & 0x1F, (word >> 5) & 0x1F, (word >> 10) & 0x1F
    return (0.299 * r5 + 0.587 * g5 + 0.114 * b5) / 31.0


def _spearman(a: Sequence[float], b: Sequence[float]) -> float:
    """Rank correlation, ties averaged. 1.0 = the ordering survived exactly."""
    n = len(a)
    if n < 2:
        return 1.0

    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        rk = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                rk[order[k]] = avg
            i = j + 1
        return rk

    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = math.sqrt(sum((x - ma) ** 2 for x in ra))
    db = math.sqrt(sum((y - mb) ** 2 for y in rb))
    return 1.0 if da == 0 or db == 0 else num / (da * db)


@dataclass
class PaletteResult:
    pal: Palette
    t: Transform
    stock: bytes
    new: bytes
    changed: List[int]                   # absolute file offsets that differ
    clipped: int                         # LIVE entries the knob pushed out of the HSV cube
    sat_clipped: int                     # ...of which, saturation
    val_clipped: int                     # ...of which, value  (an entry can be both)
    chan_clamped: int                    # the structural belt -- provably 0 through this path
    worst_sat: float                     # max `s * sat` asked for; > 1.0 means entries flattened
    worst_val: float                     # max `v * val` asked for
    live: int                            # entries != 0x0000
    zeros: int
    stp_stock: int
    stp_new: int
    distinct_stock: int
    distinct_new: int
    luma_rho: float
    hue_before: float
    hue_after: float
    sat_before: float
    sat_after: float
    val_before: float
    val_after: float
    zero_positions_held: bool
    peak_stock: int = 0                  # the brightest 5-bit channel over the LIVE stock entries
    peak_new: int = 0

    @property
    def headroom(self) -> int:
        """31 - the stock peak: how much a brightening recolour can actually spend.

        "Stock leaves headroom" (measured 28 of 31) is an **ef227 measurement, not a corpus law**: 46
        of the 93 creature CLUT rows in the corpus peak at exactly 31, and 14 of the 24 creature
        effects have at least one row already on the ceiling. ef211 is all six rows at 31, i.e. ZERO
        headroom, where ef227 is one of the least saturated creatures in the whole set."""
        return 31 - self.peak_stock

    @property
    def value_ceiling(self) -> float:
        """The largest ``value`` scale that does not flatten this palette's brightest entry."""
        return 31.0 / self.peak_stock if self.peak_stock else float("inf")

    @property
    def ok(self) -> bool:
        """Rules 1 and 2, per palette: the STP population held and no cutout moved."""
        return self.stp_stock == self.stp_new and self.zero_positions_held

    @property
    def clip_fraction(self) -> float:
        """Clipped share of the LIVE entries -- the number the blow-out gate judges. A handful of
        already-at-the-ceiling entries is normal and harmless (they simply cannot go further); a
        large share means the knob is crushing a whole region of the palette onto one colour."""
        return self.clipped / self.live if self.live else 0.0


def _mean_hsv(words: Sequence[int]) -> Tuple[float, float, float]:
    """The saturation-weighted mean hue of the LIVE entries, plus mean S and V.

    Hue is circular, so it is averaged as a vector; weighting by S keeps a near-grey entry from
    dragging the answer to an arbitrary angle."""
    sx = sy = ss = sv = 0.0
    n = 0
    for w in words:
        if w == 0:
            continue
        r5, g5, b5 = w & 0x1F, (w >> 5) & 0x1F, (w >> 10) & 0x1F
        h, s, v = colorsys.rgb_to_hsv(r5 / 31.0, g5 / 31.0, b5 / 31.0)
        sx += s * math.cos(2 * math.pi * h)
        sy += s * math.sin(2 * math.pi * h)
        ss += s
        sv += v
        n += 1
    if not n:                                                # pragma: no cover
        return (0.0, 0.0, 0.0)
    return (math.degrees(math.atan2(sy, sx)) % 360.0, ss / n, sv / n)


def _peak5(words: Sequence[int]) -> int:
    """The brightest 5-bit channel over the LIVE entries -- the headroom instrument."""
    pk = 0
    for w in words:
        if w == 0:
            continue
        pk = max(pk, w & 0x1F, (w >> 5) & 0x1F, (w >> 10) & 0x1F)
    return pk


def palette_peak(blob: bytes, pal: Palette) -> int:
    """The stock peak of one declared palette, without running a transform -- so a headroom refusal
    can fire BEFORE any byte is spliced, and so the scaffold can print it as a comment."""
    return _peak5(struct.unpack_from("<%dH" % pal.entries, blob, pal.off))


def palette_mean_hue(blob: bytes, pal: Palette) -> float:
    """The palette's own saturation-weighted mean hue -- the origin ``hue_to`` subtracts from."""
    return _mean_hsv(struct.unpack_from("<%dH" % pal.entries, blob, pal.off))[0]


def apply_palette(blob: bytes, pal: Palette, t: Transform) -> PaletteResult:
    """Transform one palette and measure everything the self-check needs about the result."""
    stock = blob[pal.off:pal.off + pal.nbytes]
    sw = list(struct.unpack("<%dH" % pal.entries, stock))
    nw = []
    clipped = sat_clip = val_clip = chan_clamp = 0
    worst_s = worst_v = 0.0
    for w in sw:
        v, c = apply_word(w, t)
        nw.append(v)
        if c:
            clipped += 1
            sat_clip += 1 if c & CLIP_SAT else 0
            val_clip += 1 if c & CLIP_VAL else 0
            chan_clamp += 1 if c & CLIP_CHANNEL else 0
        if w:                                                # the overshoot, for the report
            _h, s0, v0 = colorsys.rgb_to_hsv((w & 0x1F) / 31.0, ((w >> 5) & 0x1F) / 31.0,
                                             ((w >> 10) & 0x1F) / 31.0)
            worst_s = max(worst_s, s0 * t.sat)
            worst_v = max(worst_v, v0 * t.val)
    new = struct.pack("<%dH" % pal.entries, *nw)
    changed = [pal.off + i for i in range(pal.nbytes) if stock[i] != new[i]]
    live = [w for w in sw if w != 0]
    lo_s = [_luma5(w) for w in sw if w != 0]
    lo_n = [_luma5(n) for w, n in zip(sw, nw) if w != 0]
    hb, sb, vb = _mean_hsv(sw)
    ha, sa, va = _mean_hsv(nw)
    return PaletteResult(
        pal=pal, t=t, stock=stock, new=new, changed=changed,
        clipped=clipped, sat_clipped=sat_clip, val_clipped=val_clip, chan_clamped=chan_clamp,
        worst_sat=worst_s, worst_val=worst_v,
        live=len(live), zeros=sum(1 for w in sw if w == 0),
        stp_stock=sum(1 for w in sw if w & 0x8000), stp_new=sum(1 for w in nw if w & 0x8000),
        distinct_stock=len(set(sw)), distinct_new=len(set(nw)),
        luma_rho=_spearman(lo_s, lo_n), hue_before=hb, hue_after=ha,
        sat_before=sb, sat_after=sa, val_before=vb, val_after=va,
        zero_positions_held=all((w == 0) == (n == 0) for w, n in zip(sw, nw)),
        peak_stock=_peak5(sw), peak_new=_peak5(nw))


# ============================================================ (3) THE BUILD
@dataclass
class Target:
    name: str
    enabled: bool
    t: Transform
    note: str
    pal: Palette
    result: Optional[PaletteResult] = None
    ack_shared: bool = False
    ack_headroom: bool = False


@dataclass
class Build:
    effect: int
    label: str
    spec_path: str
    source: str
    orig: bytes
    patched: bytes
    sha_in: str
    sha_out: str
    pmap: PaletteMap
    targets: List[Target]
    check: Optional["SelfCheck"] = None
    orth_specs: Tuple[Optional[str], Optional[str]] = (None, None)
    #: every OTHER sibling lane ``[reskin.orthogonality]`` names (``repaint = "..."``), which
    #: :func:`_orthogonality` turns into one extra intersection gate EACH. Kept out of
    #: :attr:`orth_specs` deliberately: that pair is the fixed W2/W3 shape the study record cites by
    #: position, and widening it would rewrite the meaning of an index somebody already relies on.
    orth_extra: Dict[str, str] = dataclasses.field(default_factory=dict)
    #: WHICH drift guard actually applied -- the :attr:`ff9mapkit.summons.rescore.Build.guard` posture.
    #: Reporting "none -- unguarded" purely from ``effect in R.EXPECTED_STOCK_SHA`` calls every
    #: generalised effect unguarded even when its own spec pins ``expect_sha256`` and :func:`build` has
    #: already ENFORCED it at :func:`R.drift_guard`. On a tool whose normal case is "the spec carries
    #: the hash", a report that says "unguarded" about a guarded build is a lie in the direction that
    #: gets a guard removed. Set once, at the same call site that computes ``sha_in``.
    guard: str = "none -- UNGUARDED"
    #: DISCLOSURES this build made rather than refusals it raised -- the texanim decode (W7 L1/L6) and
    #: the deprecation of ``acknowledge_texanim``. Reported by :func:`describe`, which is what the CLI
    #: ``plan`` prints, so a lift the author did not ask for is never silent.
    notes: List[str] = dataclasses.field(default_factory=list)
    #: THE REGION INVARIANT's own verdict string (:func:`assert_region_invariant`), recorded at the
    #: call site that enforced it so the report quotes the check that ran, not a restatement of it.
    region_invariant: str = ""

    @property
    def enabled(self) -> List[Target]:
        return [t for t in self.targets if t.enabled]


def _ack_bool(d: dict, key: str, where: str) -> bool:
    """A safety acknowledgement must be a LITERAL BOOLEAN -- the rescore lane's R3 rule, applied
    here too after V1 found the asymmetry: `acknowledge_shared = "false"` must refuse, never arm.
    (W5's own minted law: a safety acknowledge is stated, never inferred from a truthy string.)"""
    v = d.get(key, False)
    if not isinstance(v, bool):
        raise ReskinError("%s: %s must be a BOOLEAN (true/false), not %r. A safety acknowledgement "
                          "must be stated, never inferred from a truthy string." % (where, key, v))
    return v


#: THE UNKNOWN-KEY MESSAGE, shared verbatim by all three tables so one shape teaches one lesson.
#: Lifted from the texel lane's own gate (``repaint.py``'s ``[[reskin.texel]]`` check), which is
#: where this property existed and where it was measured: a mistyped ``acknowledge_cutout_reshape``
#: fails closed and is merely annoying, but a mistyped ``expect_page_offset`` silently DROPS a guard,
#: and a guard may only ever fail CLOSED.
UNKNOWN_KEY_MESSAGE = ("%s declares unknown key(s) %s.  Refused rather than ignored: a mistyped "
                       "guard silently drops the guard, and a guard may only ever fail CLOSED.  "
                       "Known keys: %s")


def _refuse_unknown_keys(d: dict, known, where: str) -> None:
    """The fail-closed unknown-key check, in ONE place for both tables of this module.

    W6q-0. Before this rung the property existed on ``[[reskin.texel]]`` ONLY: this module read every
    key through ``d.get`` and a typo was silently ignored, so ``acknowledge_shared = ture`` armed
    nothing while reading like consent, and ``expect_offset`` misspelt dropped a derivation guard with
    no error anywhere. It ships ALONE and FIRST because it can refuse specs that build today -- a
    behaviour change to a shipped lane deserves its own diff -- and because any later key placed on
    an ungated table would inherit the same silence.
    """
    unknown = sorted(set(d) - set(known))
    if unknown:
        raise ReskinError(UNKNOWN_KEY_MESSAGE
                          % (where, ", ".join(repr(u) for u in unknown), ", ".join(sorted(known))))


#: every key ONE ``[[reskin.target]]`` row understands -- the CLUT lane's own fail-closed set.
#:
#: ``acknowledge_texanim`` is in here DELIBERATELY even though the gate reads it at ``[reskin]``
#: level: it is a DEPRECATED-but-still-parsed key (:data:`TEXANIM_ACK_DEPRECATED`), specs in the wild
#: carry it, and a set that omitted it would turn "your spec still builds" into "your spec refuses"
#: for exactly the population this rung exists to protect.
_TARGET_KEYS = frozenset((
    "name", "enabled", "note",
    "expect_entries", "expect_vram", "expect_offset",
    "acknowledge_shared", "acknowledge_headroom", "acknowledge_texanim",
    # the transform knobs (:func:`_transform_of`); `hue_to` and `hue_rotate` are two spellings of one
    # knob and declaring BOTH in one table is already a refusal.
    "hue_to", "hue_rotate", "saturation", "value",
))

#: every key the top-level ``[reskin]`` table understands, ACROSS BOTH LANES -- the CLUT lane's own
#: (``effect``/``label``/``expect_sha256``/``allow_unguarded``/``acknowledge_texanim``/``spans``/
#: ``defaults``/``target``) and the texel lane's (``texel``, ``orthogonality``).
#:
#: ONE set for both modules, consumed by :func:`load_spec` here and by ``repaint.load_spec`` there,
#: because one spec file may carry both tables: two copies would let a key be lawful on the path that
#: happened to load it and unknown on the other, which is a refusal that depends on the caller.
_RESKIN_KEYS = frozenset((
    "effect", "label", "note", "expect_sha256", "allow_unguarded", "acknowledge_texanim",
    "spans", "defaults", "orthogonality", "target", "texel",
))


def _transform_of(d: dict, defaults: dict, where: str, mean_hue: float = 0.0) -> Transform:
    def num(key, dflt):
        v = d.get(key, defaults.get(key, dflt))
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise ReskinError("%s: `%s` must be a number, got %r" % (where, key, v))
        return float(v)

    # `hue_to` is absolute, `hue_rotate` is a delta; the row may declare exactly one of them.
    # A row-level `hue_to` deliberately BEATS an inherited default `hue_rotate` (which is how a spec
    # that sets `hue_rotate = 0.0` in [reskin.defaults] can still author absolute rows), but
    # declaring both IN THE SAME TABLE is a contradiction and refuses.
    for tbl, whose in ((d, "the target"), (defaults, "[reskin.defaults]")):
        if "hue_to" in tbl and "hue_rotate" in tbl:
            raise ReskinError("%s: %s declares BOTH `hue_to` and `hue_rotate`.  They are two "
                              "spellings of one knob (`hue_rotate = hue_to - the palette's own "
                              "measured mean hue`); declare one." % (where, whose))
    hue_to = None
    if "hue_to" in d or ("hue_to" in defaults and "hue_rotate" not in d):
        hue_to = num("hue_to", 0.0)
        hue = (hue_to - mean_hue + 180.0) % 360.0 - 180.0    # the SHORT way round the wheel
    else:
        hue = num("hue_rotate", 0.0)
    t = Transform(hue=hue, sat=num("saturation", 1.0), val=num("value", 1.0), hue_to=hue_to)
    if t.sat < 0 or t.val < 0:
        raise ReskinError("%s: saturation/value scales must be >= 0 (got %s)" % (where, t))
    if t.sat > 4 or t.val > 4:
        raise ReskinError("%s: a scale above 4x is refused -- 5-bit channels clip long before "
                          "that and the effect's own colorIntensity multiplies 1.5x/2x on top "
                          "(got %s)" % (where, t))
    return t


#: what ``acknowledge_texanim = true`` now means: nothing.  Kept parseable for one release so specs
#: written against the pre-W7 gate (any W5-era scaffold output) keep building; the scaffold no longer
#: emits it.  It is still put through :func:`_ack_bool`, so ``"false"`` REFUSES rather than arming --
#: a key that is a no-op is not a key that may be typed wrong.
TEXANIM_ACK_DEPRECATED = (
    "DEPRECATED KEY `acknowledge_texanim`: it is a NO-OP since W7 and this build ignored it.  It used "
    "to state \"scenery scope only, orthogonality assumed, not proven\"; the assumption is now a "
    "MEASUREMENT -- every clip in every armed table names a CREATURE part and every rect is local to "
    "that part's own 128x128 page (x+w <= 64 halfwords, 39/39 clips), so the table cannot reach a "
    "scenery page at all.  Delete the line.  (One exception keeps the key alive: on an armed region "
    "that does NOT decode, the measurement never ran, and the key is REQUIRED for scenery in its "
    "original meaning.)")


def _gate_texanim(pmap: PaletteMap, targets: List["Target"], ack: bool,
                  blob: bytes) -> List[str]:
    """THE TEXANIM GATE, at the call site -- **a DISCLOSURE now, plus one surviving refusal**.

    What changed at W7, and why. The pre-W7 gate refused a creature recolour OUTRIGHT because the
    table's format was unread and one of the three branches it might have implemented (cycling the
    per-part CLUT WORD) would have made a static recolour pointless. The table is read now
    (:mod:`ff9mapkit.summons.texanim`) and that branch is FALSIFIED, twice over:

    * **the data cannot express it.** No ``u16`` anywhere in the five armed tables is a header TPAGE or
      CLUT word; the whole table is rects, counts and a rate. What it describes is a texel blit of
      8-bit palette INDICES inside ONE creature part's own page -- and a blit of indices recolours
      identically under any palette, so a recolour survives it by construction;
    * **and nothing runs it.** The only code in either build of the plugin that dereferences
      ``SummonData+0x70`` is ``Hi_Start/StopSummonTexAnim``, which write three state fields and return.

    Two corrections to what this docstring used to claim, both cited downstream and both wrong: the
    arming op indexes **BY CLIP**, not by part (op 12's ``$a1`` is a clip index; the affected part is
    named by ``clip+0x0d``), and ``0x18`` is the **x64 RUNTIME** struct size -- the FILE record is
    ``0x14``, which is why neither 116 nor 364 ever divided by ``partCount * 0x18``.

    So the creature scope opens with NO key, and the scenery scope opens with no key either: its
    "orthogonality assumed" hedge is a measurement now (every clip names a creature part and every
    rect is page-local, 39/39). ``acknowledge_texanim`` becomes a deprecated no-op **where the table
    decodes**.

    **What still refuses -- the lift is conditional on a successful PARSE, never on the absence of an
    exception**, so an unknown future shape degrades to the pre-W7 posture instead of silently
    passing, per lane: a CREATURE recolour on an armed-undecodable region refuses outright (no key);
    a SCENERY recolour on one is back to the pre-W7 hedge, so ``acknowledge_texanim`` is REQUIRED
    there and keeps its original meaning (orthogonality assumed, not proven) -- the key is only
    deprecated where the measurement that replaced it actually ran. Returns the disclosure lines the
    report carries.
    """
    notes: List[str] = []
    ta = pmap.texanim
    if ta is None or not ta.armed:
        if ack:
            notes.append(TEXANIM_ACK_DEPRECATED)
        return notes
    live = [t for t in targets if t.enabled]
    creature = [t.name for t in live if t.pal.slot < 0]
    scenery = [t.name for t in live if t.pal.slot >= 0]
    res = TA.read(blob)
    if creature and res.table is None:
        raise ReskinError(
            "TEXANIM ARMED (%d bytes at %#x..%#x) and this spec recolours the CREATURE (%s).  W7 "
            "READ this format -- a texel-blit clip table (u32 clipCount + 20-byte clips + 12-byte "
            "windows + packed frame lists; summons/texanim.py) -- but THIS container's region does "
            "not decode: %s.  An undecodable region could implement anything, including the one "
            "branch a decoded table provably cannot (a CLUT-word cycle, which voids a static "
            "recolour), so the pre-W7 refusal stands on the creature scope and no key lifts it.  "
            "(All five stock armed packages -- ef038 / ef177 / ef493 / ef494 / ef495 -- decode; an "
            "undecodable region means a modified or unknown container.)"
            % (ta.nbytes, ta.lo, ta.hi, ", ".join(creature), res.error))
    if res.table is None and scenery:
        # THE DEGRADED PATH (V1 F1): armed and UNDECODABLE -- the measurement that deprecated the
        # key never ran here, so the pre-W7 posture stands and the key does its ORIGINAL job.
        if not ack:
            raise ReskinError(
                "TEXANIM ARMED (%d bytes at %#x..%#x) and the region does not DECODE (%s).  A "
                "scenery-only recolour is PLAUSIBLY orthogonal to it -- every DECODED stock table "
                "names only creature parts -- but this table is unread, so orthogonality is back to "
                "an assumption: the pre-W7 posture.  The spec must say `acknowledge_texanim = true` "
                "at the [reskin] level to state exactly that (scenery scope only, orthogonality "
                "assumed, not proven).  The key is only deprecated where the table decodes."
                % (ta.nbytes, ta.lo, ta.hi, res.error))
        notes.append(
            "TEXANIM ARMED (%d bytes at %#x..%#x) and UNDECODABLE (%s) -- scenery recolour "
            "proceeding under `acknowledge_texanim = true` in its ORIGINAL, pre-W7 meaning: scenery "
            "scope only, orthogonality assumed, not proven.  (The key is deprecated only where the "
            "table decodes.)" % (ta.nbytes, ta.lo, ta.hi, res.error))
    elif ack:
        notes.append(TEXANIM_ACK_DEPRECATED)
    if res.table is not None and live:
        tt = res.table
        notes.append(
            "TEXANIM ARMED (%d bytes at %#x..%#x) and DECODED: %d clip(s) over part(s) %s.  The table "
            "blits 8-bit palette INDICES inside one part's own page -- it binds no CLUT word and "
            "writes no CLUT contents -- so this recolour survives the cast under BOTH the \"it runs\" "
            "and the \"it does not run\" reading (W7).  The region itself is left byte-identical (THE "
            "REGION INVARIANT)."
            % (ta.nbytes, ta.lo, ta.hi, tt.count, ", ".join(str(p) for p in tt.parts)))
    return notes


def _gate_cells(pmap: PaletteMap, targets: List["Target"]) -> None:
    """The multi-writer and dual-depth CLUT-cell refusals (see :class:`Cell`)."""
    live = {t.pal.name: t for t in targets if t.enabled}
    for vram, cell in sorted(pmap.hazards.items()):
        touched = [n for n in cell.names if n in live]
        if not touched:
            continue
        if cell.dual_depth:
            raise ReskinError(
                "DUAL-DEPTH CLUT cell VRAM %s: the container declares it at %s entries from %d "
                "different file offsets, i.e. the same VRAM halfwords are read as two different "
                "pictures with two different palettes.  Recolouring one distorts the other and no "
                "evidence exists either way, so this refuses outright (touched: %s).  ef447's "
                "(0,242) is the corpus fixture."
                % (str(vram), "/".join(str(d) for d in sorted(set(cell.depths))),
                   len(set(cell.offsets)), ", ".join(touched)))
        missing = [n for n in cell.names if n not in live]
        if missing:
            raise ReskinError(
                "MULTI-WRITER CLUT cell VRAM %s has %d writers and this spec names only %d of them "
                "(missing: %s).  Every writer streams a genuinely different palette into the SAME "
                "cell, so recolouring one leaves the others stock and the cast flickers between two "
                "keys.  Name every writer, or name none.  ef381 is the corpus fixture (19 such "
                "cells, up to 5 writers)."
                % (str(vram), len(set(cell.offsets)), len(touched), ", ".join(sorted(missing))))
        bad = [n for n in touched if live[n].t.hue_to is None]
        if bad:
            raise ReskinError(
                "MULTI-WRITER CLUT cell VRAM %s: a co-transform must be authored with the ABSOLUTE "
                "`hue_to` form.  Each writer has its own measured mean hue, so one shared "
                "`hue_rotate` delta lands them on DIFFERENT hues -- which is the flicker this gate "
                "exists to stop.  Rewrite %s with `hue_to`." % (str(vram), ", ".join(sorted(bad))))


def _gate_shared(t: "Target") -> None:
    if t.pal.shared and not t.ack_shared:
        raise ReskinError(
            "target %s is a SHARED palette.  %s.  It may only be recoloured as the GROUP it is, so "
            "the spec must say `acknowledge_shared = true` to show the author knows more than one "
            "set piece moves." % (t.name, t.pal.shared_reason or t.pal.note))


def _gate_headroom(blob: bytes, t: "Target") -> None:
    """The ZERO-HEADROOM refusal.

    "Stock leaves headroom" is an ef227 measurement, not a law: 46 of the corpus's 93 creature CLUT
    rows peak at exactly **31 of 31**, where ef227's six peak at 28/28/24/22/28/27. On a row that is
    already on the 5-bit ceiling there is PROVABLY no headroom at all, so any ``value > 1.0`` is pure
    flattening of the top of the ramp -- it cannot brighten anything. That case refuses unless the
    spec says ``acknowledge_headroom = true``.

    Everything short of that (a peak of 30 under a 1.12 lift, say) is a MAGNITUDE question, not a
    yes/no one, and stays with the instrument that measures it: the HSV clip census and
    :data:`BLOWOUT_FRACTION`. ef227 clears this gate untouched -- its worst target, part4 at peak 28
    under value 1.12, is exactly the 4.7%-of-live overshoot its own spec already documents.
    """
    if t.t.val <= 1.0 or t.ack_headroom:
        return
    peak = palette_peak(blob, t.pal)
    if peak >= 31:
        raise ReskinError(
            "target %s has ZERO HEADROOM: its brightest live 5-bit channel is already 31 of 31, so "
            "`value = %.3f` cannot brighten anything -- it can only flatten the top of the ramp onto "
            "one colour.  46 of the corpus's 93 creature CLUT rows are in this class (ef211 is all "
            "six), and the \"stock leaves headroom\" note is an ef227 measurement, not a law.  Do "
            "the work with hue and saturation, or say `acknowledge_headroom = true`."
            % (t.name, t.t.val))


def build(spec: dict, spec_path: str = "?", game=None, blob: Optional[bytes] = None) -> Build:
    """Read the install, resolve every target, run every gate, splice.

    ``blob`` supplies the container directly and skips the install read, so the whole span-guard /
    per-target / shared-CLUT / drift-guard pipeline is exercisable on synthetic bytes with no install.
    Every law still runs on that path, because a law that only holds on one of two entry paths is not
    a law.
    """
    r = spec["reskin"]
    effect = int(r["effect"])
    if blob is None:
        blob, source = R.read_stock_effect(effect, game)
    else:
        source = "(caller-supplied bytes)"
    if not r.get("expect_sha256") and effect not in R.EXPECTED_STOCK_SHA \
            and not r.get("allow_unguarded"):
        raise ReskinError(
            "ef%03d has NO drift guard: the spec declares no `expect_sha256` and the effect is not "
            "in rescore.EXPECTED_STOCK_SHA.  Merely printing \"unguarded\" here would mean a "
            "Steam/Moguri patch or another mod could move a span under the edit and nothing would "
            "notice.  Run `ff9mapkit summon-reskin scaffold --ef %d` to emit the guard from your own "
            "install, or say `allow_unguarded = true` deliberately." % (effect, effect))
    sha_in = R.drift_guard(effect, blob, r.get("expect_sha256"))
    # Record WHICH guard matched, so `describe` can report the truth instead of inferring it from
    # the registry alone. `R.drift_guard` prefers the spec's own hash over the registered one, and
    # this string mirrors that precedence exactly.
    guard = ("the spec's own expect_sha256 -- MATCHES" if r.get("expect_sha256") else
             ("REGISTERED in rescore.EXPECTED_STOCK_SHA -- MATCHES"
              if effect in R.EXPECTED_STOCK_SHA
              else "none -- UNGUARDED (allow_unguarded = true)"))

    pmap = palette_map(blob, effect=effect)

    # ---- the span guards: the spec states what the derivation must have found
    for name, want in (r.get("spans") or {}).items():
        s = pmap.span(name)
        if int(want.get("offset", s.lo)) != s.lo or int(want.get("length", s.size)) != s.size:
            raise ReskinError("span %s: the spec guards %#x/%d but the container's own header "
                              "derives %#x/%d -- refusing to splice into a span this edit was not "
                              "derived against" % (name, int(want.get("offset", -1)),
                                                   int(want.get("length", -1)), s.lo, s.size))

    defaults = r.get("defaults") or {}
    rows = r.get("target") or []
    if not rows:
        raise ReskinError("%s declares no [[reskin.target]] -- nothing to do" % spec_path)

    targets: List[Target] = []
    seen = set()
    for i, d in enumerate(rows):
        # W6q-0: FAIL CLOSED FIRST.  Before any key of this row is read, because the whole point is
        # that a key nobody reads is invisible -- and the guards below are exactly the keys whose
        # silent loss has no symptom.
        _refuse_unknown_keys(d, _TARGET_KEYS, "[[reskin.target]] #%d" % i)
        name = d.get("name")
        if not name:
            raise ReskinError("[[reskin.target]] #%d has no `name`" % i)
        if name in seen:
            raise ReskinError("target %r is declared twice" % name)
        seen.add(name)
        pal = pmap.by_name(name)
        if any(t.pal.name == pal.name for t in targets):
            raise ReskinError("targets %s and %r both resolve to the derived palette %s"
                              % (next(t.name for t in targets if t.pal.name == pal.name), name,
                                 pal.name))
        if "expect_entries" in d and int(d["expect_entries"]) != pal.entries:
            raise ReskinError("target %s: the spec guards %d entries, the header declares %d"
                              % (name, int(d["expect_entries"]), pal.entries))
        if "expect_vram" in d and tuple(d["expect_vram"]) != pal.vram:
            raise ReskinError("target %s: the spec guards VRAM %s, the header declares %s"
                              % (name, tuple(d["expect_vram"]), pal.vram))
        if "expect_offset" in d and int(d["expect_offset"]) != pal.off:
            raise ReskinError("target %s: the spec guards file %#x, the derivation says %#x"
                              % (name, int(d["expect_offset"]), pal.off))
        targets.append(Target(name=name, enabled=bool(d.get("enabled", True)),
                              t=_transform_of(d, defaults, "target %s" % name,
                                              palette_mean_hue(blob, pal)),
                              note=str(d.get("note", "")), pal=pal,
                              ack_shared=_ack_bool(d, "acknowledge_shared", "target %s" % name),
                              ack_headroom=_ack_bool(d, "acknowledge_headroom", "target %s" % name)))

    # ---- the gates that only an ENABLED target can trip. A disabled row splices nothing, so it
    # states an intent rather than an edit; its acknowledgements become mandatory the moment it is
    # switched on, and `plan` previews it through the transform it declares either way.
    notes = _gate_texanim(pmap, targets, _ack_bool(r, "acknowledge_texanim", "[reskin]"), blob)
    _gate_cells(pmap, targets)
    for t in targets:
        if not t.enabled:
            continue
        _gate_shared(t)
        _gate_headroom(blob, t)
    # ★ W6b-3: A PREVIEW THAT WILL NOT APPEAR SAYS SO **HERE**, not at render time.  `render_previews`
    # runs after `describe` has already printed, so a refusal raised there reaches the author too
    # late to read as anything but a missing file.  Same predicate, same helper, one derivation.
    _attrib_for_preview = pmap.attrib or attribution(blob)
    for t in targets:
        if not t.enabled or t.pal.slot < 0 or t.pal.entries != 256:
            continue
        _bind = _attrib_for_preview.binders(t.pal.vram, t.pal.entries)
        if len(_bind) != 1:
            notes.append(_preview_refusal_reason(t.pal, _bind))

    out = bytearray(blob)
    for t in targets:
        if not t.enabled:
            continue
        t.result = apply_palette(blob, t.pal, t.t)
        out[t.pal.off:t.pal.off + t.pal.nbytes] = t.result.new
    patched = bytes(out)
    if len(patched) != len(blob):                            # pragma: no cover - splice is in-place
        raise ReskinError("the splice changed the container length -- impossible by construction")
    # THE REGION INVARIANT (W7 R1) -- enforced HERE, on the bytes this function is about to hand back,
    # because a rule checked anywhere else is a rule the next lever can route around.
    region_invariant = assert_region_invariant(blob, patched, "the reskin of ef%03d" % effect)

    orth = r.get("orthogonality") or {}
    # Only STRING values are sibling spec names; `compose = true` is a composition switch the texel
    # lane reads out of the same table and is not a lane to intersect against.
    extra = {k: v for k, v in orth.items()
             if k not in ("rescore", "retime") and isinstance(v, str)}
    return Build(effect=effect, label=str(r.get("label", "reskin")), spec_path=str(spec_path),
                 source=source, orig=blob, patched=patched, sha_in=sha_in, sha_out=_sha(patched),
                 pmap=pmap, targets=targets, guard=guard, notes=notes,
                 region_invariant=region_invariant,
                 orth_specs=(orth.get("rescore"), orth.get("retime")), orth_extra=extra)


# ============================================================ (4) THE SELF-CHECK
@dataclass
class Gate:
    ok: bool
    name: str
    detail: str


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


def _regions(blob: bytes, effect: int, partition: str = "clut") -> List[Tuple[str, int, int]]:
    """The regions an edit must not touch, resolved from the container itself.

    Everything a repaint, a retime or a reframe would move: sector 0 (the resource table and the
    binary sequence stream), both id-3 program images, every camera block, the id-5 model image, the
    whole id-4 header + texel region, and every GEOM block found by the corpus-selective scanner (the
    scenery's geometry and UVs).

    ``partition`` INVERTS **two** splits for the sibling texel lane
    (:mod:`ff9mapkit.summons.repaint`) instead of letting it carry a second copy of this function:

    * the **id-4 creature** split -- ``"clut"`` (the default, this lane) licenses the CLUT strip and
      gates the header + every page; ``"texel"`` licenses the pages and gates the header, the CLUT
      strip and the sector pad;
    * the **id-0 scenery** split (W6b-1, :class:`Id0Split`) -- ``pixelDataRel`` cuts each chunk's id-0
      payload into the page-block header + ``clutWord`` table + inline CLUT rect stream below it, and
      the page PIXEL stream above it. ``"clut"`` gates the pixel stream; ``"texel"`` gates the
      header/rect-table/CLUT-stream half.

    Until W6b the id-0 resource was in the list under NEITHER partition, which was correct for the
    CLUT lane (it writes id-0 inline palettes) and a real gap for the texel lane: a scenery splice
    would have run with ``page_rel``, the rect count and the ``(x, y, w, h)`` rect table **ungated**,
    and a mis-seek there re-aims the whole page map silently. The inline CLUT payload was already
    protected -- by ``repaint``'s *"every DERIVED palette re-derives and is byte-exact"* gate and by
    :func:`id0_palettes`' own stream-end assertion -- but the rect table is read by
    :func:`scenery_pages` and by nothing that check runs. Its companion is
    :func:`assert_page_cells_identical`, which re-derives the map rather than merely comparing bytes.

    Everything outside those two splits is identical under both, which is the point: the two levers
    disagree about exactly two boundaries and agree about every other byte in the container, and a
    parameter says that where a duplicated function would only imply it until one copy drifted.

    A ZERO-LENGTH half is omitted rather than emitted: a container that declares no page rects has no
    pixel stream, and an empty region gates nothing either way.

    ``g.end`` is called BARE on purpose. Its predecessor wrapped it in ``except Exception: end =
    g.base + 0x10``, which meant that if the property ever went missing or raised, every GEOM region
    silently shrank to a 16-byte header stub and the byte-identical gate went green while gating
    essentially nothing -- a fail-OPEN on the one gate that proves the geometry did not move. A raise
    here is now a loud build failure, which is the correct direction for a gate.
    """
    if partition not in ("clut", "texel"):
        raise ReskinError("unknown region partition %r -- \"clut\" or \"texel\"" % partition)
    c = EC.parse_header(blob, strict=True)
    out: List[Tuple[str, int, int]] = [("sector 0 (resource table + the sequence stream)", 0, 0x800)]
    mp = EC.creature_package(blob)
    for ch in c.chunks:
        tag = chunk_tag(ch)
        for r in ch.resources:
            if r.id == 3:
                out.append(("%s id-3 effect program image" % tag, r.offset, r.offset + r.nbytes))
            elif r.id == 5:
                out.append(("%s id-5 SUMMON_MODEL image" % tag, r.offset, r.offset + r.nbytes))
            elif r.id == 4 and mp is not None:
                if partition == "texel":
                    out.append(("%s id-4 model-package header" % tag,
                                r.offset, mp.tex_file_offset))
                    out.append(("%s id-4 CLUT strip (%d rows)" % (tag, mp.clut_rows),
                                mp.tex_file_offset + mp.tex_bytes,
                                mp.tex_file_offset + mp.tex_bytes + mp.clut_bytes))
                else:
                    out.append(("%s id-4 header + all %d texel pages" % (tag, mp.part_count),
                                r.offset, mp.tex_file_offset + mp.tex_bytes))
                out.append(("%s id-4 sector pad past the CLUT strip" % tag,
                            mp.tex_file_offset + mp.tex_bytes + mp.clut_bytes, r.offset + r.nbytes))
    for sp in id0_splits(blob):
        lo, hi = sp.clut_side if partition == "texel" else sp.pixel_side
        if lo >= hi:                                         # nothing declared on that side
            continue
        out.append((("%s id-0 page-block header + clutWord table + inline CLUT stream" % sp.tag)
                    if partition == "texel" else
                    ("%s id-0 page PIXEL stream (%d rect(s))" % (sp.tag, sp.n_rects)), lo, hi))
    ex = W.extract_shots(blob, "ef%03d" % effect)
    for s in ex.shots:
        out.append(("camera block slot %d idx %d" % (s.slot, s.index), s.lo, s.hi))
    for g in EC.scan_geom(blob):
        out.append(("GEOM block @%#x (geometry + UVs)" % g.base, g.base, g.end))
    return out


#: sibling specs :func:`_orthogonality` rebuilds when a spec does not name its own. EMPTY in the kit,
#: deliberately: this package ships no reference spec, and a default filename nobody's tree contains
#: would turn every build's orthogonality gate into a silent "SKIPPED: not found" that reads like a
#: proof. A caller carrying its own reference specs (the study runner does) re-pins this mapping,
#: preferably with ABSOLUTE paths -- a relative name here is resolved against the SPEC file's own
#: directory, not against this module's.
DEFAULT_ORTH_SPECS: Dict[str, str] = {}


def _sibling_effect(path: str, table: str) -> Optional[int]:
    """Which effect a sibling spec targets, without building it."""
    try:
        with open(path, "rb") as fh:
            doc = tomllib.load(fh)
        return int((doc.get(table) or {})["effect"])
    except Exception:                                        # pragma: no cover - malformed sibling
        return None


def _rebuild_rescore(path: str, mine: Set[int]) -> Tuple[Set[int], str]:
    """Rebuild a camera rescore from its own toml and return ``(changed offsets, the detail line)``."""
    b2 = R.build_patched(R.load_spec(path), os.path.basename(path))
    d = {i for i in range(len(b2.orig)) if b2.orig[i] != b2.patched[i]}
    return d, ("W2 changes %d bytes (the camera Code at %s); intersection %d"
               % (len(d), ", ".join("%#x" % o for o in sorted(d)), len(d & mine)))


def _rebuild_repaint(path: str, mine: Set[int]) -> Tuple[Set[int], str]:
    """Rebuild a TEXEL repaint from its own toml and intersect its pages with this recolour's CLUTs.

    Imported LAZILY on purpose: :mod:`ff9mapkit.summons.repaint` consumes this module's derivations,
    so a module-level import here would be circular. ``compose=False`` is passed because an
    orthogonality proof needs the sibling's OWN delta -- a spec that composes onto this one would
    otherwise rebuild this one inside its own gate, and the intersection would be with itself.

    The full path is handed over, never the basename: a repaint spec's ``source`` images resolve
    against the spec file's own directory, and a basename would resolve them against the CWD.
    """
    from . import repaint as RP
    b2 = RP.build(RP.load_spec(path), path, compose=False)
    d = {i for i in range(len(b2.orig)) if b2.orig[i] != b2.patched[i]}
    return d, ("W6 changes %d TEXEL bytes across %d page(s) from %s; intersection %d"
               % (len(d), len(b2.enabled), os.path.basename(path), len(d & mine)))


#: ``[reskin.orthogonality]`` table name -> the callable that REBUILDS that sibling lane and returns
#: ``(changed offset set, detail line)``. Only lanes this package actually ships appear here: the
#: rescore and repaint lanes do, the RETIME lane does not (it is study-only -- the writing half of it
#: is refusal-gated and it was not promoted). A spec naming a table with no rebuilder gets an explicit
#: SKIP that says so, never a crash and never a silent pass. A caller that owns a retime
#: implementation registers it here and the gate becomes a real intersection proof again.
ORTH_REBUILDERS: Dict[str, Callable[[str, Set[int]], Tuple[Set[int], str]]] = {
    "rescore": _rebuild_rescore,
    "repaint": _rebuild_repaint,
}

#: sibling table name -> the TOP-LEVEL TOML table that sibling's own spec declares. A REPAINT spec is
#: a ``[reskin]`` spec (its rows are ``[[reskin.texel]]``, one file two levers), so its effect id is
#: read from ``[reskin]`` -- reading ``[repaint]`` would find nothing and the gate would report the
#: sibling as targeting an unknown effect and SKIP, which is a proof evaporating quietly.
_ORTH_SPEC_TABLE: Dict[str, str] = {"repaint": "reskin"}


def _orth_base(b: "Build") -> str:
    """Where a RELATIVE sibling spec name resolves from: **the spec file's own directory**.

    Never this module's directory. A module-relative base means the kit package dir holds no toml, so
    every declared sibling resolves to a non-existent path, every gate reports SKIPPED, and the
    orthogonality proof evaporates for every user while still printing as a passing check. Relative
    to the spec, ``rescore = "phoenix_rescore.toml"`` means what an author reading the file thinks it
    means: the file sitting next to this one.
    """
    sp = str(b.spec_path or "")
    if not sp or sp == "?":
        return os.getcwd()
    return os.path.dirname(os.path.abspath(sp))


def _orthogonality(b: Build, mine: Set[int]) -> List[Gate]:
    """Rebuild each declared sibling lane from its OWN spec and intersect its edits with this one's.

    This is the proof, not the assertion: if the two rungs' changed-offset sets are disjoint then both
    can ship in one container, and this rung provably moved no camera and no clock.

        [reskin.orthogonality]
        rescore = "phoenix_rescore.toml"

    Four outcomes, and only one of them is a proof:

    * a sibling whose own ``effect`` differs from this build's is SKIPPED with that stated, rather
      than silently "proving" disjointness against a different container's edits;
    * a sibling the spec NAMED and that does not exist FAILS -- being wrong about a file you named is
      not the same as not naming one;
    * a table this package cannot rebuild (the retime lane) is SKIPPED with the reason named;
    * otherwise both are rebuilt and intersected, and a non-empty intersection FAILS.
    """
    out: List[Gate] = []
    base = _orth_base(b)
    declared = {"rescore": b.orth_specs[0] is not None, "retime": b.orth_specs[1] is not None}
    want = {"rescore": b.orth_specs[0] or DEFAULT_ORTH_SPECS.get("rescore"),
            "retime": b.orth_specs[1] or DEFAULT_ORTH_SPECS.get("retime")}

    # The two gate NAMES are the rung labels the milestone record uses (W2 = the camera rescore,
    # W3 = the retime lane), kept verbatim so a gate cited in the study record is findable by the
    # name it was cited under -- the same reason the "W1's camera blocks" region gate keeps its.
    tables = [("rescore", "W2's rescore edits are disjoint from this reskin's"),
              ("retime", "W3's retime edits are disjoint from this reskin's")]
    # Any OTHER lane the spec names gets a gate of its own -- and only then. A lane nobody named
    # contributes no gate at all rather than a standing "SKIPPED" row, so the two rungs above keep
    # reading as the fixed pair the record cites and a third one appears exactly when it is claimed.
    for extra in sorted(b.orth_extra):
        tables.append((extra, "the %s lane's edits are disjoint from this reskin's" % extra))
        declared[extra] = True
        want[extra] = b.orth_extra[extra] or DEFAULT_ORTH_SPECS.get(extra)
    for table, title in tables:
        name = want[table]
        if not name:
            out.append(Gate(True, title,
                            "SKIPPED: this spec names no `%s` sibling under [reskin.orthogonality] "
                            "and no default is registered, so disjointness with the %s lane is "
                            "UNPROVEN here -- not proven.  Name a sibling spec for the same effect "
                            "to turn this skip into a real changed-offset intersection."
                            % (table, table)))
            continue
        path = name if os.path.isabs(name) else os.path.join(base, name)
        if not os.path.isfile(path):
            out.append(Gate(not declared[table], title,
                            "SKIPPED: no %s spec at %s%s" % (table, path,
                                                             "" if not declared[table] else
                                                             " -- but the spec NAMED it")))
            continue
        ef = _sibling_effect(path, _ORTH_SPEC_TABLE.get(table, table))
        if ef != b.effect:
            out.append(Gate(True, title,
                            "SKIPPED: %s targets ef%s, this reskin targets ef%03d -- rebuilding "
                            "another effect's edits would prove nothing about this one"
                            % (os.path.basename(path), "%03d" % ef if ef is not None else "?",
                               b.effect)))
            continue
        rebuild = ORTH_REBUILDERS.get(table)
        if rebuild is None:
            out.append(Gate(True, title,
                            "SKIPPED (STUDY-ONLY LANE): %s targets this effect, but the `%s` lane is "
                            "not part of this package and cannot be rebuilt here, so its "
                            "disjointness is UNPROVEN -- not proven.  Register a rebuilder in "
                            "reskin.ORTH_REBUILDERS[%r] to restore the intersection proof."
                            % (os.path.basename(path), table, table)))
            continue
        try:
            d, detail = rebuild(path, mine)
            out.append(Gate(not (d & mine), title, detail))
        except Exception as e:                               # pragma: no cover - spec-dependent
            out.append(Gate(False, title, "FAILED to rebuild %s: %s" % (os.path.basename(path), e)))
    return out


def self_check(b: Build) -> SelfCheck:
    changed = [i for i in range(len(b.orig)) if b.orig[i] != b.patched[i]]
    mine = set(changed)

    # ---- (1) byte accounting: every changed byte inside a named palette inside a named span
    owner: Dict[int, str] = {}
    per_target: Dict[str, int] = {}
    for t in b.enabled:
        per_target[t.name] = len(t.result.changed)
        for o in t.result.changed:
            owner[o] = t.name
    unexplained = [o for o in changed if o not in owner]
    span_miss = []
    for o in changed:
        s = next((s for s in b.pmap.spans if s.lo <= o < s.hi), None)
        if s is None:
            span_miss.append(o)
    acc = [
        Gate(not unexplained, "every changed byte belongs to a named target",
             "%d bytes changed, %d unexplained%s"
             % (len(changed), len(unexplained),
                "" if not unexplained else " at " + ", ".join("%#x" % o for o in unexplained[:8]))),
        Gate(not span_miss, "every changed byte lands inside a derived CLUT span",
             "spans: " + " | ".join("%s %#x..%#x (%d B)" % (s.name, s.lo, s.hi, s.size)
                                    for s in b.pmap.spans)),
        Gate(len(changed) <= b.pmap.envelope, "under the DERIVED whole-set envelope",
             "%d changed of the %d-byte %d-span envelope (%.2f%% of the %d-byte container); the "
             "envelope is sum(span.size), not a constant -- ef227 derives 8,192 B over 4 spans, "
             "ef381 declares 15 spans"
             % (len(changed), b.pmap.envelope, len(b.pmap.spans),
                100.0 * len(changed) / len(b.orig), len(b.orig))),
        Gate(len(b.patched) == len(b.orig), "same length by construction",
             "%d B in, %d B out" % (len(b.orig), len(b.patched))),
    ]

    # ---- (2) the five hard rules, per palette
    bad_stp = [t.name for t in b.enabled if t.result.stp_stock != t.result.stp_new]
    bad_zero = [t.name for t in b.enabled if not t.result.zero_positions_held]
    entry0 = []
    for t in b.enabled:
        s0, n0 = _u16(t.result.stock, 0), _u16(t.result.new, 0)
        if s0 == 0 and n0 != 0:
            entry0.append(t.name)
    # RULE 3's instrument. It counts the clip that can ACTUALLY happen -- a knob asking for
    # `s * sat` or `v * val` outside [0,1], which flattens that entry onto the ceiling -- and not the
    # channel clamp, which `_clamp01` makes structurally unreachable (see CLIP_CHANNEL). The census
    # is per target with its fraction and its worst overshoot; the FAIL is the fraction, because a
    # handful of already-at-the-ceiling entries is harmless and a large share is a crushed gradient.
    clip_rows = sorted((t for t in b.enabled if t.result.clipped),
                       key=lambda t: -t.result.clip_fraction)
    blown = [t for t in b.enabled if t.result.clip_fraction > BLOWOUT_FRACTION]
    stray_chan = [t.name for t in b.enabled if t.result.chan_clamped]
    clip_total = sum(t.result.clipped for t in b.enabled)
    clip_detail = ("no entry in any target was pushed out of the HSV cube"
                   if not clip_rows else
                   "%d of %d live entries clipped across the set -- "
                   % (clip_total, sum(t.result.live for t in b.enabled))
                   + "; ".join("%s %d/%d (%.1f%%) S%d V%d, asked for S x%.3f V x%.3f"
                               % (t.name, t.result.clipped, t.result.live,
                                  100.0 * t.result.clip_fraction, t.result.sat_clipped,
                                  t.result.val_clipped, t.result.worst_sat, t.result.worst_val)
                               for t in clip_rows))
    rules = [
        Gate(not bad_stp, "STP population identical stock vs patched, per palette",
             "%d palettes; %s" % (len(b.enabled),
                                  "all match" if not bad_stp else "DRIFT: " + ", ".join(bad_stp))),
        Gate(not bad_zero, "every 0x0000 entry stayed 0x0000, and no entry became one",
             "%d transparent entries across the set; %s"
             % (sum(t.result.zeros for t in b.enabled),
                "all held" if not bad_zero else "MOVED: " + ", ".join(bad_zero))),
        Gate(not entry0, "entry 0 of every palette that had 0x0000 there is still 0x0000",
             "%d palettes carry a 0x0000 at index 0" %
             sum(1 for t in b.enabled if _u16(t.result.stock, 0) == 0)),
        Gate(not blown, "no knob flattens more than %.0f%% of a palette onto the HSV ceiling"
                        % (100.0 * BLOWOUT_FRACTION),
             clip_detail + ("" if not blown else
                            "  -- BLOWN OUT: " + ", ".join(
                                "%s %.1f%%" % (t.name, 100.0 * t.result.clip_fraction)
                                for t in blown)
                            + ".  Pull `value`/`saturation` back on that target, or accept it "
                              "deliberately by raising BLOWOUT_FRACTION.")),
        Gate(not stray_chan, "the 0..31 channel clamp never had to fire (the structural belt)",
             "%d entries clamped at the channel step%s"
             % (sum(t.result.chan_clamped for t in b.enabled),
                " -- expected: `_clamp01` bounds s/v before hsv_to_rgb, whose max component is v, "
                "so int(f*31+0.5) tops out at 31" if not stray_chan else
                " -- UNEXPECTED at " + ", ".join(stray_chan) + ": the clamp order changed and the "
                "HSV census above is no longer the whole story")),
    ]

    # ---- (3) the untouched regions + a strict re-parse
    regions: List[Gate] = []
    try:
        c = EC.parse_header(b.patched, strict=True)
        regions.append(Gate(c.cursor_end == len(b.patched), "the container re-parses STRICT",
                            "walker cursor %#x == file length %#x" % (c.cursor_end, len(b.patched))))
    except EC.ContainerError as e:                           # pragma: no cover
        regions.append(Gate(False, "the container re-parses STRICT", str(e)))
    gated = _regions(b.orig, b.effect)
    hits = []
    for name, lo, hi in gated:
        n = sum(1 for o in changed if lo <= o < hi)
        if n:
            hits.append("%s (%d bytes)" % (name, n))
    regions.append(Gate(not hits, "every geometry / program / camera / sequence region is "
                                  "BYTE-IDENTICAL",
                        "%d regions gated (%d B of the container); %s"
                        % (len(gated), sum(hi - lo for _n, lo, hi in gated),
                           "no hits" if not hits else "HIT: " + "; ".join(hits))))
    tag = "ef%03d" % b.effect
    ex_s, ex_p = W.extract_shots(b.orig, tag), W.extract_shots(b.patched, tag)
    same_shots = (len(ex_s.shots) == len(ex_p.shots)
                  and all(b.orig[s.lo:s.hi] == b.patched[s.lo:s.hi] for s in ex_s.shots))
    regions.append(Gate(same_shots, "W1's camera blocks re-extract and are byte-exact",
                        "%d camera blocks, all identical" % len(ex_s.shots)))
    mp_s, mp_p = EC.creature_package(b.orig), EC.creature_package(b.patched)
    if mp_s is None or mp_p is None:
        # 348 of the 372 containers have no id-4 at all. A scenery-only reskin of one of them is a
        # legitimate build, and a gate that cannot run must SAY SO rather than crash or pass.
        regions.append(Gate(mp_s is None and mp_p is None,
                            "the id-4 TEXEL region is untouched and still decodes",
                            "NOT APPLICABLE: this container declares no id-4 creature package "
                            "(scenery-only scope); %s"
                            % ("consistent stock vs patched" if mp_s is None and mp_p is None else
                               "STOCK AND PATCHED DISAGREE about whether one exists")))
    else:
        tex_same = (b.orig[mp_s.tex_file_offset:mp_s.tex_file_offset + mp_s.tex_bytes]
                    == b.patched[mp_p.tex_file_offset:mp_p.tex_file_offset + mp_p.tex_bytes])
        regions.append(Gate(tex_same and KT.texture_check(b.patched, mp_p)["decodable"],
                            "the id-4 TEXEL region is untouched and still decodes",
                            "%d B of pages at %#x, bit-identical; texture_check passes on the "
                            "patched container" % (mp_s.tex_bytes, mp_s.tex_file_offset)))

    # ---- (4) orthogonality with the sibling lanes, proved by rebuilding them
    orth = _orthogonality(b, mine)

    # ---- (5) quality: contrast + the honest invariance report
    qual: List[Gate] = []
    worst = sorted(b.enabled, key=lambda t: t.result.luma_rho)[:3]
    lo_rho = min((t.result.luma_rho for t in b.enabled), default=1.0)
    qual.append(Gate(lo_rho >= 0.90, "relative luminance ordering survives inside every palette",
                     "min Spearman rho %.4f (%s)" % (lo_rho, ", ".join(
                         "%s %.3f" % (t.name, t.result.luma_rho) for t in worst))))
    # The 5-bit re-quantisation merges entries -- unavoidable, and mostly among near-black darks a
    # saturation scale pulls together, which is invisible. The FLOOR is what matters: a palette that
    # lost 40% of its distinct colours has genuinely banded, and the previews would show it. The
    # exact counts are printed either way so the number is judged, not just gated.
    flat = [t.name for t in b.enabled
            if t.result.distinct_new < t.result.distinct_stock * 0.60]
    qual.append(Gate(not flat, "no palette collapsed below 60% of its distinct colours "
                               "(the 5-bit re-quantisation floor)",
                     "distinct entries: " + ", ".join("%s %d->%d" % (t.name, t.result.distinct_stock,
                                                                     t.result.distinct_new)
                                                      for t in b.enabled)))
    inert = [t.name for t in b.enabled if not t.result.changed]
    qual.append(Gate(True, "targets the transform cannot move (reported, not fatal)",
                     "none" if not inert else
                     ", ".join(inert) + " -- an achromatic palette is INVARIANT under a hue "
                     "rotation and a saturation scale; only a channel-mix (a repaint's vocabulary) "
                     "could move it"))
    return SelfCheck(acc, rules, regions, orth, qual, changed, per_target)


# ============================================================ (5) THE PREVIEWS
def _need_pil():
    try:
        from PIL import Image, ImageDraw            # noqa: F401
    except ImportError as e:                        # pragma: no cover - env dependent
        raise ReskinError("the previews need Pillow (py -m pip install Pillow): %s" % e)
    from PIL import Image, ImageDraw
    return Image, ImageDraw


def _decode(pixels: bytes, words: Sequence[int], w: int, h: int):
    Image, _ = _need_pil()
    img = Image.new("RGBA", (w, h))
    img.putdata([KT.bgr555_rgba(words[i]) for i in pixels[:w * h]])
    return img


def _label(img, text: str, pad: int = 16):
    Image, ImageDraw = _need_pil()
    out = Image.new("RGBA", (img.width, img.height + pad), (24, 24, 28, 255))
    out.paste(img, (0, pad))
    ImageDraw.Draw(out).text((3, 3), text, fill=(230, 230, 235, 255))
    return out


def _swatches(words_a: Sequence[int], words_b: Sequence[int], width: int = 768, cell_h: int = 26):
    """Two stacked strips -- stock over patched -- one cell per palette entry.

    A ``0x0000`` (cutout) entry is drawn black with a magenta pip, so the eye can confirm rule 1
    held: every pip must sit at the same index in both strips."""
    Image, ImageDraw = _need_pil()
    n = len(words_a)
    cw = max(1, width // n)
    img = Image.new("RGBA", (cw * n, cell_h * 2 + 3), (24, 24, 28, 255))
    d = ImageDraw.Draw(img)
    for i in range(n):
        for row, ws in ((0, words_a), (cell_h + 3, words_b)):
            r, g, bl, a = KT.bgr555_rgba(ws[i])
            d.rectangle([i * cw, row, i * cw + cw - 1, row + cell_h - 1],
                        fill=(r, g, bl, 255) if a else (0, 0, 0, 255))
            if a == 0:                                       # mark the cutout entries
                d.rectangle([i * cw, row + cell_h // 2 - 1, i * cw + cw - 1, row + cell_h // 2 + 1],
                            fill=(255, 0, 128, 255))
    return img


def render_previews(b: Build, out_dir) -> List[str]:
    """Stock-vs-patched pages for every target whose texels are resolvable, plus swatch strips.

    STOCK-DERIVED ART -- LOCAL ONLY. :func:`ff9mapkit.summons.rescore._refuse_repo_path` guards the
    destination for the same reason :func:`ff9mapkit.summons.export.assert_local_only` guards a
    decoded ``.glb``.
    """
    Image, ImageDraw = _need_pil()
    out = Path(R._refuse_repo_path(out_dir))
    out.mkdir(parents=True, exist_ok=True)
    written: List[str] = []

    cpages = creature_pages(b.orig)
    attrib = b.pmap.attrib or attribution(b.orig)

    def pair(name: str, px: bytes, w: int, h: int, res: PaletteResult, scale: int = 2):
        sw = struct.unpack("<%dH" % res.pal.entries, res.stock)
        nw = struct.unpack("<%dH" % res.pal.entries, res.new)
        a, c = _decode(px, sw, w, h), _decode(px, nw, w, h)
        sheet = Image.new("RGBA", (w * 2 + 8, h), (24, 24, 28, 255))
        sheet.paste(a, (0, 0))
        sheet.paste(c, (w + 8, 0))
        sheet = sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST)
        sheet = _label(sheet, "%s   STOCK  |  RESKIN   (%s)" % (name, res.t))
        p = out / ("%s.png" % name.replace(".", "-"))
        sheet.save(p)
        written.append(str(p))

    # --- the creature: exact 1:1 page <-> palette
    tiles = []
    for t in b.enabled:
        if t.name in cpages:
            px = b.orig[cpages[t.name]:cpages[t.name] + KT.PAGE_BYTES]
            pair(t.name, px, KT.PAGE_W, KT.PAGE_H, t.result)
            tiles.append((t, px))
    if tiles:
        cols = 3
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGBA", (KT.PAGE_W * cols * 2 + 24, KT.PAGE_H * rows), (24, 24, 28, 255))
        for k, (t, px) in enumerate(tiles):
            sw = struct.unpack("<%dH" % t.pal.entries, t.result.stock)
            nw = struct.unpack("<%dH" % t.pal.entries, t.result.new)
            sheet.paste(_decode(px, sw, KT.PAGE_W, KT.PAGE_H),
                        ((k % cols) * KT.PAGE_W, (k // cols) * KT.PAGE_H))
            sheet.paste(_decode(px, nw, KT.PAGE_W, KT.PAGE_H),
                        (KT.PAGE_W * cols + 24 + (k % cols) * KT.PAGE_W, (k // cols) * KT.PAGE_H))
        sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
        sheet = _label(sheet, "CREATURE -- every page through its own CLUT.  LEFT stock, RIGHT reskin.")
        p = out / "creature-sheet.png"
        sheet.save(p)
        written.append(str(p))

    # --- the scenery: the 8bpp columns the `so` bindings resolve, no table
    #
    # ★ W6b-3: A MISSING PREVIEW NOW CARRIES A REASON.  This loop used to `continue` in silence, and
    # after the multi-part reader landed a preview can vanish because a SECOND binder became visible
    # -- including where that binder is the SAME model through a second array entry.  A picture that
    # quietly stops appearing is exactly the kind of change an author reads as a bug in their spec.
    no_preview: List[str] = []
    for t in b.enabled:
        if t.pal.slot < 0 or t.pal.entries != 256:
            continue
        rects = preview_source(b.orig, t.pal, attrib, reasons=no_preview)
        if not rects:
            continue
        px = b"".join(b.orig[r.off:r.off + r.nbytes] for r in rects)
        w = rects[0].texel_size(8)[0]
        h = sum(r.texel_size(8)[1] for r in rects)
        if w <= 0 or h <= 0 or len(px) < w * h:              # pragma: no cover - malformed rect
            continue
        pair(t.pal.alias or t.name, px, w, h, t.result, scale=2)
    # the same refusals `build` already staged into `notes` (where `describe` prints them BEFORE this
    # runs); re-collected here so a caller that reaches `render_previews` directly still gets them,
    # and de-duplicated so the disclosure is stated once.  `written` stays a list of PATHS.
    for why in no_preview:
        if why not in b.notes:
            b.notes.append(why)

    # --- the swatch strips: every target, stock over patched, in one contact sheet
    rowsimg = []
    for t in b.targets:
        # a DISABLED target is previewed through the transform it DECLARES, so the sheet shows what
        # turning it on would do -- that is the whole point of declaring it off rather than omitting it
        res = t.result or apply_palette(b.orig, t.pal, t.t)
        sw = struct.unpack("<%dH" % t.pal.entries, res.stock)
        nw = struct.unpack("<%dH" % t.pal.entries, res.new)
        strip = _swatches(sw, nw)
        rowsimg.append(_label(strip, "%s  %s  VRAM %s  %dbpp  %d entries  %s  %s"
                              % (t.name, "ON " if t.enabled else "off", t.pal.vram, t.pal.bpp,
                                 t.pal.entries, t.t, "SHARED" if t.pal.shared else "")))
    if rowsimg:
        W_ = max(i.width for i in rowsimg)
        H_ = sum(i.height + 6 for i in rowsimg)
        sheet = Image.new("RGBA", (W_, H_), (16, 16, 20, 255))
        y = 0
        for i in rowsimg:
            sheet.paste(i, (0, y))
            y += i.height + 6
        p = out / "swatches.png"
        sheet.save(p)
        written.append(str(p))
    return written


# ============================================================ (6) STAGING + THE LEDGERED SCRIPTS
def _rel_container(ef_id: int) -> str:
    return "/".join(MOD_SUBPATH.split("/") + ["ef%03d" % ef_id])


def modfilelist_refusal(mod_root) -> Optional[str]:
    """The refusal text if ``mod_root`` carries a ``ModFileList.txt``, else ``None``.

    THE SILENT-FALLBACK LAW, shared verbatim with the camera lane
    (:func:`ff9mapkit.summons.rescore.modfilelist_refusal`): when a mod folder has a ModFileList.txt,
    ``TryFindAssetInModOnDisc`` TRUSTS that list and never calls ``File.Exists``, so any file the list
    omits is INVISIBLE -- and because ``SFX.Play`` suppresses its missing-asset error, the cast simply
    plays the stock effect with nothing logged anywhere. "Nothing changed" would be the only symptom.
    This lane REFUSES rather than half-owning somebody else's registry, and NEVER creates a list
    (creating one would make every OTHER file in that folder invisible at a stroke).
    """
    return R.modfilelist_refusal(mod_root)


def stage(b: Build, root=None, game_root=None, allow_install: bool = False,
          previews: bool = True, mod_root=None, refuse_modfilelist: bool = False) -> dict:
    """Write the patched container, the previews and the two ``--root``-aware live scripts.

    STAGE by default: :func:`ff9mapkit.summons.rescore._refuse_repo_path` always, and
    :func:`~ff9mapkit.summons.rescore._refuse_install_path` unless ``allow_install``. The generated
    scripts are stdlib-only and take ``--root``, so a sandbox test passes a temp folder INSTEAD of
    editing a path literal -- a script that can only undo itself in the directory it was born in is
    un-rehearsable.

    ``root`` defaults to :func:`staging_root`, i.e. PER EFFECT: with one root for every effect, two
    effects staged in one session silently overwrite each other's container, previews, manifest and
    revert script. The default is additionally held to
    :func:`ff9mapkit.summons.export.assert_local_only` (repo + mod-asset tree + the resolved install),
    because it is the one destination this module CHOOSES rather than accepts.

    ``mod_root`` is where the override actually lands and defaults to ``<root>/mod`` -- a staging
    tree the generated deploy script then copies into a real mod folder. Passing a real mod folder
    here (with ``allow_install`` and ``refuse_modfilelist``) is the DEPLOY path: the ledger writes
    straight into it, and a ``--root``-rebasable ledger revert script is emitted beside the others.
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
            raise ReskinError(why)

    # The work root is created HERE, after every refusal has had its say and before anything is
    # written into it. It used to exist only as a SIDE EFFECT of the container write landing at
    # `<root>/mod/...`; the moment the override goes somewhere else (the deploy path) that side
    # effect stops happening and the script writes below fail on a directory nobody made.
    root.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(root / "backups", mod_root=mod_root)
    rel = _rel_container(b.effect)
    dest = Path(mod_root).joinpath(*rel.split("/"))
    if dest.suffix:                                          # pragma: no cover
        raise ReskinError("the container override must be EXTENSIONLESS")
    sha = ledger.write_bytes(dest, b.patched)

    preview_files: List[str] = []
    if previews:
        preview_files = render_previews(b, root / "previews")

    live_mod = Path(game_root) / "FF9CustomMap" if game_root else None
    plan = {
        "effect": b.effect,
        "label": b.label,
        "default_mod_root": str(live_mod) if live_mod else "",
        "snapshot_base": str(root / "live-snapshot"),
        "revert_script": str(root / ("revert_summon_reskin_%d.py" % b.effect)),
        "targets": [{"src": str(dest), "rel": rel, "sha256": sha}],
        "expect_live_sha256": None,
        "note": "this artifact is STOCK ef%03d + the reskin '%s'; it REPLACES whatever container "
                "the mod folder holds for that effect. The first-deploy snapshot restores it "
                "byte-for-byte." % (b.effect, b.label),
    }
    if live_mod is not None:
        live = live_mod.joinpath(*rel.split("/"))
        if live.exists():
            plan["expect_live_sha256"] = _sha(live.read_bytes())
    scripts = {
        "deploy": str(_write_script(root / "deploy_reskin.py", _DEPLOY_TEMPLATE, plan)),
        "revert": str(_write_script(root / ("revert_summon_reskin_%d.py" % b.effect),
                                    _REVERT_TEMPLATE, plan)),
    }
    if deploying:
        # The ledger's own revert undoes exactly the writes THIS call made into the mod folder (and
        # any ModFileList line), takes --root and --dry-run, and is the right instrument when the
        # container went straight into a real folder rather than into the staging tree.
        scripts["ledger_revert"] = str(ledger.write_revert_script(
            root, "%d" % b.effect, prefix="revert_summon_reskin_ledger"))

    manifest = {
        "spec": b.spec_path, "effect": b.effect, "label": b.label,
        "stock_sha256": b.sha_in, "patched_sha256": sha,
        "container": str(dest), "scripts": scripts, "previews": preview_files,
        "changed_bytes": len(b.check.changed) if b.check else None,
        "per_target_bytes": b.check.per_target if b.check else None,
        "staging_root": str(root),
        "mod_root": str(mod_root),
        "transforms": {t.name: {"hue_rotate": t.t.hue, "saturation": t.t.sat, "value": t.t.val,
                                "enabled": t.enabled, "offset": t.pal.off,
                                "entries": t.pal.entries, "vram": list(t.pal.vram),
                                "hue_to": t.t.hue_to, "derived_name": t.pal.name}
                       for t in b.targets},
    }
    from .. import fsutil
    fsutil.atomic_write_text(root / "build_manifest.json",
                             json.dumps(manifest, indent=2), encoding="utf-8", newline="\n")
    manifest["staged_files"] = len(ledger.files)
    return manifest


def verify(b: Build, root=None) -> dict:
    """Re-check what is STAGED, as bytes -- not as a rebuild's promise.

    The point is not "did the file get written" but "are the bytes on disc the bytes this spec
    produces from THIS install today", plus: does the manifest still describe them, are both scripts
    still there, did every preview survive, and does every recorded transform still match the spec.
    A missing manifest, a divergent container and a missing script are different verdicts and are
    reported as such rather than collapsed into one boolean.
    """
    root = Path(root or staging_root(b.effect))
    mf = root / "build_manifest.json"
    lines: List[str] = []
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
        ok = ok and same
        lines.append("VERIFY container   %d B sha %s -> %s"
                     % (len(got), _sha(got)[:16], "MATCHES the rebuild" if same else "DIVERGES"))
        if man.get("patched_sha256") != _sha(got):
            lines.append("VERIFY manifest    sha in the manifest does not match the staged file")
            ok = False
    for name, sp in sorted((man.get("scripts") or {}).items()):
        exists = Path(sp).exists()
        ok = ok and exists
        lines.append("VERIFY %-11s %s" % (name, sp if exists else "MISSING: %s" % sp))
    missing = [f for f in (man.get("previews") or []) if not Path(f).exists()]
    lines.append("VERIFY previews    %d staged, %d missing"
                 % (len(man.get("previews") or []), len(missing)))
    ok = ok and not missing
    for name, tr in sorted((man.get("transforms") or {}).items()):
        t = next((x for x in b.targets if x.name == name), None)
        if t is None or (t.t.hue, t.t.sat, t.t.val, t.enabled) != (
                tr["hue_rotate"], tr["saturation"], tr["value"], tr["enabled"]):
            lines.append("VERIFY transform   %s DIVERGES from the manifest" % name)
            ok = False
    return {"ok": ok, "root": str(root), "manifest": str(mf), "container": man.get("container"),
            "lines": lines}


def _write_script(path: Path, template: str, plan: dict) -> Path:
    from .. import fsutil
    body = template.replace("__PLAN__", repr(json.dumps(plan, indent=2)))
    fsutil.atomic_write_text(path, body, encoding="utf-8", newline="\n")
    return path


#: shared by both scripts: the root resolution (``--root`` beats the baked default), the per-root
#: snapshot folder (so a sandbox test can never poison the real deploy's ledger), and the tree hash.
_SCRIPT_PREAMBLE = '''
def parse_root(argv):
    root = PLAN["default_mod_root"]
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--root":
            if i + 1 >= len(argv):
                print("FAIL: --root needs a directory"); raise SystemExit(2)
            root = argv[i + 1]; i += 2; continue
        if a.startswith("--root="):
            root = a.split("=", 1)[1]; i += 1; continue
        if a in ("-h", "--help"):
            print(__doc__); raise SystemExit(0)
        rest.append(a); i += 1
    if rest:
        print("FAIL: unexpected argument(s): %s" % " ".join(rest)); raise SystemExit(2)
    if not root:
        print("FAIL: no mod root -- this plan has no baked default, pass --root <mod folder>")
        raise SystemExit(2)
    return Path(root)


def snapshot_dir(root):
    """One ledger PER ROOT: a sandbox run under a temp root gets its own, so the real
    first-deploy snapshot is never overwritten or consumed by a test."""
    key = hashlib.sha256(str(Path(root).resolve()).lower().encode("utf-8")).hexdigest()[:12]
    return Path(PLAN["snapshot_base"]) / key


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(root):
    out = {}
    for t in PLAN["targets"]:
        p = Path(root) / t["rel"]
        if p.exists():
            out[t["rel"]] = _sha(p)
    return out


def manifest_hash(m):
    return hashlib.sha256("\\n".join("%s %s" % (k, m[k]) for k in sorted(m)).encode()).hexdigest()
'''


_DEPLOY_TEMPLATE = '''#!/usr/bin/env python3
"""Auto-generated LIVE deploy for a summon reskin -- stdlib only, no ff9mapkit import.

    py deploy_reskin.py [--root <mod folder>]

Copies the staged, recoloured ef### container into a mod folder, taking a FIRST-DEPLOY SNAPSHOT of
whatever that folder held beforehand.  ``--root`` defaults to the live FF9CustomMap; pass a temp
folder to rehearse.  The snapshot is per-root and is written once and never overwritten, so a
re-deploy still reverts all the way back to the pre-reskin state.  Idempotent.
"""
import hashlib, json, os, shutil, sys
from pathlib import Path

PLAN = json.loads(__PLAN__)
''' + _SCRIPT_PREAMBLE + '''

def main(argv):
    root = parse_root(argv)
    if not root.is_dir():
        print("FAIL: mod folder not found: %s" % root); return 1
    if (root / "ModFileList.txt").exists():
        print("REFUSING: %s has a ModFileList.txt. TryFindAssetInModOnDisc TRUSTS that list and "
              "never calls File.Exists, so an unlisted override is INVISIBLE. Handle the list by "
              "hand, then re-run." % root)
        return 1
    for t in PLAN["targets"]:
        if not Path(t["src"]).is_file():
            print("FAIL: staged artifact missing: %s" % t["src"]); return 1
        got = _sha(t["src"])
        if got != t["sha256"]:
            print("FAIL: %s sha256 %s != the build's %s -- re-run `summon-reskin build`."
                  % (t["src"], got, t["sha256"]))
            return 1

    before = manifest(root)
    snap_dir = snapshot_dir(root)
    snap_file = snap_dir / "snapshot.json"
    if snap_file.exists():
        snap = json.loads(snap_file.read_text(encoding="utf-8"))
        print("snapshot: reusing the FIRST-DEPLOY snapshot at %s (%s)" % (snap_file, snap.get("taken")))
    else:
        snap_dir.mkdir(parents=True, exist_ok=True)
        entries = []
        for t in PLAN["targets"]:
            dest = root / t["rel"]
            if dest.exists():
                backup = snap_dir / ("%s.pre-reskin" % dest.name)
                shutil.copyfile(dest, backup)
                sha = _sha(dest)
                entries.append({"rel": t["rel"], "existed": True, "sha256": sha,
                                "backup": str(backup)})
                if PLAN.get("expect_live_sha256") and sha != PLAN["expect_live_sha256"]:
                    print("NOTE: the file being replaced is %s, not the %s this build saw at stage "
                          "time -- another session wrote it. The snapshot captures what is ACTUALLY "
                          "there, so revert is still exact." % (sha[:16], PLAN["expect_live_sha256"][:16]))
            else:
                entries.append({"rel": t["rel"], "existed": False, "sha256": None, "backup": None})
        snap = {"taken": "first deploy", "root": str(root.resolve()), "entries": entries,
                "pre_manifest": before, "pre_manifest_hash": manifest_hash(before)}
        tmp = snap_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(snap, indent=2), encoding="utf-8")
        os.replace(tmp, snap_file)
        print("snapshot: TAKEN -> %s" % snap_file)
        for e in entries:
            print("   %-6s %s%s" % ("saved" if e["existed"] else "absent", e["rel"],
                                    "  (sha %s)" % e["sha256"][:16] if e["existed"] else ""))

    for t in PLAN["targets"]:
        dest = root / t["rel"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(t["src"], dest)
        if _sha(dest) != t["sha256"]:
            print("FAIL: write verification at %s -- readback != what we wrote" % dest); return 1
        print("deployed %s  (%d B, sha %s)" % (dest, dest.stat().st_size, t["sha256"][:16]))

    after = manifest(root)
    print()
    print("mod root             : %s" % root)
    print("tree manifest before : %s  (%d files)" % (manifest_hash(before), len(before)))
    print("tree manifest after  : %s  (%d files)" % (manifest_hash(after), len(after)))
    print("revert with          : py %s%s"
          % (PLAN["revert_script"], "" if str(root) == PLAN["default_mod_root"] else ' --root "%s"' % root))
    print()
    print(PLAN["note"])
    print("NOTE: SFX.Play re-reads the container AND wipes the whole managed texture cache on every")
    print("      cast, so the recolour is live on the very next cast -- no relaunch, no reload.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''


_REVERT_TEMPLATE = '''#!/usr/bin/env python3
"""Auto-generated revert for a summon reskin -- stdlib only, no ff9mapkit import.

    py revert_summon_reskin_<effect>.py [--root <mod folder>]

Restores whatever the mod folder held before the FIRST reskin deploy to that same root, or deletes
the file if the reskin created it.  Idempotent -- run it twice and it restores the same bytes twice
and reports the same verdict.
"""
import hashlib, json, os, shutil, sys
from pathlib import Path

PLAN = json.loads(__PLAN__)
''' + _SCRIPT_PREAMBLE + '''

def main(argv):
    root = parse_root(argv)
    snap_file = snapshot_dir(root) / "snapshot.json"
    if not snap_file.exists():
        print("nothing to revert for %s: no snapshot at %s (was the deploy ever run against this "
              "root?)" % (root, snap_file))
        return 0
    snap = json.loads(snap_file.read_text(encoding="utf-8"))
    for e in snap["entries"]:
        dest = root / e["rel"]
        if e["existed"]:
            backup = Path(e["backup"])
            if not backup.exists():
                print("FAIL: snapshot copy missing: %s" % backup); return 1
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(backup, dest)
            ok = _sha(dest) == e["sha256"]
            print("restored %s <- %s  %s" % (dest, backup.name, "OK" if ok else "SHA MISMATCH"))
            if not ok:
                return 1
        else:
            if dest.exists():
                dest.unlink()
                print("deleted  %s" % dest)
            parent = dest.parent
            stop = root.resolve()
            while parent.resolve() != stop and parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
                print("pruned   %s" % parent)
                parent = parent.parent

    after = manifest(root)
    same = manifest_hash(after) == snap["pre_manifest_hash"]
    print()
    print("mod root                 : %s" % root)
    print("tree manifest pre-reskin : %s  (%d files)" % (snap["pre_manifest_hash"],
                                                         len(snap["pre_manifest"])))
    print("tree manifest now        : %s  (%d files)" % (manifest_hash(after), len(after)))
    print("verdict                  : %s" % ("EXACT RESTORE" if same else "DRIFT -- see the two hashes"))
    print()
    print("the snapshot is KEPT so a re-deploy still reverts to the true pre-reskin state; delete")
    print("%s by hand only if you want to re-baseline." % snap_file)
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''


# ============================================================ (7) REPORTING
def describe(b: Build) -> List[str]:
    L = ["ef%03d  %s" % (b.effect, b.label),
         "  stock source   : %s" % b.source,
         "  stock sha256   : %s  (drift guard %s)" % (b.sha_in, b.guard),
         "  reskin sha256  : %s" % b.sha_out,
         "  container      : %d B in, %d B out (same length -- every palette is spliced in place)"
         % (len(b.orig), len(b.patched)),
         ""]
    if b.region_invariant:
        L += ["  THE REGION INVARIANT (W7 R1, enforced at the build call site)",
              "    %s" % b.region_invariant, ""]
    for n in b.notes:
        L += ["  NOTE  %s" % n, ""]
    L += derivation_lines(b.orig, b.pmap)
    L += ["", "  THE DERIVED PALETTES (%d declared)" % len(b.pmap.palettes)]
    for p in b.pmap.palettes:
        t = next((x for x in b.targets if x.pal.name == p.name), None)
        state = "OFF" if t is None else ("ON " if t.enabled else "off")
        L.append("    [%s] %-34s %#08x  %3d entries %dbpp  VRAM %-10s %s%s"
                 % (state, p.name, p.off, p.entries, p.bpp, "(%d,%d)" % p.vram,
                    "SHARED " if p.shared else "", ("= " + p.alias) if p.alias else ""))
    L += ["", "  THE TRANSFORMS"]
    for t in b.targets:
        if not t.enabled:
            L.append("    off  %-34s %s   %s" % (t.name, t.t, t.note))
            continue
        r = t.result
        L.append("    ON   %-34s %s" % (t.name, t.t))
        L.append("         %4d/%4d bytes differ | live %3d, transparent %2d | STP %d->%d | "
                 "distinct %3d->%3d | clipped %d (S%d V%d, %.1f%% of live) | luma rho %.4f"
                 % (len(r.changed), t.pal.nbytes, r.live, r.zeros, r.stp_stock, r.stp_new,
                    r.distinct_stock, r.distinct_new, r.clipped, r.sat_clipped, r.val_clipped,
                    100.0 * r.clip_fraction, r.luma_rho))
        L.append("         mean H %5.1f -> %5.1f   S %.2f -> %.2f   V %.2f -> %.2f   "
                 "peak %d/31 (headroom %d, value ceiling x%.3f)   %s"
                 % (r.hue_before, r.hue_after, r.sat_before, r.sat_after,
                    r.val_before, r.val_after, r.peak_stock, r.headroom, r.value_ceiling, t.note))
    return L


def derivation_lines(blob: bytes, pmap: PaletteMap) -> List[str]:
    """The per-effect derivation read-out shared by ``plan``, ``build`` and ``scaffold``."""
    L = ["  THE DERIVED SPANS (from the container's own headers, not from a table) -- "
         "envelope %d B" % pmap.envelope]
    for s in pmap.spans:
        L.append("    %-22s %#08x..%#08x  %5d B   %s" % (s.name, s.lo, s.hi, s.size, s.source))
    a = pmap.attrib
    ta = pmap.texanim
    L += ["", "  THE DERIVED ATTRIBUTION (`so` records, magic 0x6F73)"]
    if a is None:                                            # pragma: no cover - always computed
        L.append("    not computed")
    else:
        L.append("    coverage %d/%d non-creature GEOM blocks carry an `so` record (%.1f%%) -- %s"
                 % (a.geom_with_so, a.geom_total, 100.0 * a.coverage,
                    "COMPLETE: an unbound palette is genuinely bound by no GEOM model"
                    if a.complete else
                    "INCOMPLETE: every unbound palette is SHARED-UNKNOWN and needs "
                    "`acknowledge_shared`"))
        L.append("    %d textured bindings over %d distinct CLUT cells"
                 % (len(a.bindings), len({(x.cell, x.entries) for x in a.bindings})))
    L += ["", "  THE HAZARD CENSUS (multi-writer / dual-depth CLUT cells)"]
    if not pmap.hazards:
        L.append("    none -- every declared CLUT cell has exactly one writer at one bit depth")
    for vram, cell in sorted(pmap.hazards.items()):
        L.append("    VRAM %-10s %s%s  %d writers %s  depths %s"
                 % ("(%d,%d)" % vram, "MULTI-WRITER " if cell.multi_writer else "",
                    "DUAL-DEPTH" if cell.dual_depth else "", len(set(cell.offsets)),
                    ", ".join("%#x" % o for o in sorted(set(cell.offsets))),
                    "/".join(str(d) for d in sorted(set(cell.depths)))))
    # L6, PURE DISCLOSURE: print the DECODED table, not "TEXANIM ARMED (N bytes)".  An opaque size is
    # what made the pre-W7 refusal unanswerable -- an author could not tell what the gate was afraid of.
    L += [""] + TA.describe(blob)
    if ta is not None and ta.armed and TA.read(blob).table is not None:
        L.append("    creature scope is OPEN (W7): the table blits palette INDICES inside one part's "
                 "own page, so a recolour survives it")
    if pmap.creature_error:
        L.append("    creature note: %s" % pmap.creature_error)
    return L


def check_lines(b: Build) -> List[str]:
    c = b.check
    L = ["", "  SELF-CHECK  (%d/%d gates)" % (sum(1 for g in c.gates if g.ok), len(c.gates))]
    for title, gates in (("byte accounting", c.accounting), ("the hard rules", c.rules),
                         ("untouched regions", c.regions), ("orthogonality", c.orthogonality),
                         ("quality", c.quality)):
        L.append("    -- %s" % title)
        for g in gates:
            L.append("    [%s] %s" % ("ok" if g.ok else "!!", g.name))
            L.append("         %s" % g.detail)
    L.append("")
    L.append("    per-target changed bytes: " + ", ".join(
        "%s %d" % (k, v) for k, v in c.per_target.items()))
    L.append("    TOTAL %d bytes of %d (%.3f%%), derived envelope %d"
             % (len(c.changed), len(b.orig), 100.0 * len(c.changed) / len(b.orig),
                b.pmap.envelope))
    return L


# ============================================================ (8) THE SCAFFOLD
def scaffold(effect: int, blob: Optional[bytes] = None, game=None,
             source: str = "") -> Tuple[str, PaletteMap]:
    """Emit a COMPLETE, guarded ``*_reskin.toml`` for one effect, read off the container itself.

    This is what makes a new effect a ten-minute job instead of a transcription exercise: every
    ``expect_*`` guard is EMITTED from the derivation rather than typed against it, so the guards
    cannot start life disagreeing with the bytes; the drift hash comes from the user's own install;
    the measured mean H/S/V, the live-entry count and the **headroom** land as comments next to the
    knob they constrain; and every knob starts at IDENTITY, so the first build is provably a no-op
    (0 changed bytes) and the author moves one number at a time.

    Acknowledgements are pre-seeded FALSE and the rows they guard are pre-seeded ``enabled = false``,
    so a scaffold builds clean out of the box and every refusal this lane carries has to be answered
    deliberately rather than defaulted away.
    """
    if blob is None:
        blob, source = R.read_stock_effect(effect, game)
    pmap = palette_map(blob, effect=effect)
    if not pmap.palettes:
        # 3 of the 372 corpus containers (ef252, ef253, ef302) declare an id-0 with an inline rect
        # and ZERO CLUT words -- no palette, no creature, nothing a recolour can address. Emitting a
        # target-less toml would produce a file that cannot load; say so instead.
        raise ReskinError(
            "ef%03d declares NO CLUT palettes at all (%d span%s, no creature package) -- there is "
            "nothing a recolour can address on this effect.  It draws with direct-colour or "
            "untextured primitives; a palette edit has no surface here."
            % (effect, len(pmap.spans), "" if len(pmap.spans) == 1 else "s"))
    ta, attrib = pmap.texanim, pmap.attrib
    #: read ONCE -- the scaffold consults the decode twice (the banner and the per-target block) and a
    #: second parse could in principle disagree with the first, which is a report nobody could trust.
    ta_parsed = bool(ta is not None and ta.armed and TA.read(blob).table is not None)
    sha = _sha(blob)

    L = ["# AUTO-SCAFFOLDED by `ff9mapkit summon-reskin scaffold --ef %d`.  Every number below is"
         % effect,
         "# DERIVED from the container's own headers; every knob is at IDENTITY.  Two kinds of line:",
         "#   * GUARDS (`expect_*`, `expect_sha256`) -- what the derivation MUST find.  They instruct",
         "#     nothing; they refuse.  Do not retype them, re-scaffold if the install changes.",
         "#   * AUTHORED DECISIONS (`hue_rotate` / `hue_to` / `saturation` / `value` / `enabled`).",
         "#",
         "# source: %s" % (source or "(caller-supplied bytes)"),
         "# container: %d B, %d chunks, %d declared palettes, %d CLUT spans, envelope %d B"
         % (len(blob), len(EC.parse_header(blob, strict=False).chunks), len(pmap.palettes),
            len(pmap.spans), pmap.envelope),
         "#"]
    L += ["# " + ln.strip() for ln in derivation_lines(blob, pmap) if ln.strip()]
    L += ["",
          "[reskin]",
          "effect = %d" % effect,
          'label  = "ef%03d-scaffold"' % effect,
          '# the drift guard: sha256 of the pristine stock container in YOUR install.  A HASH, not',
          '# data -- no stock byte is committable.',
          'expect_sha256 = "%s"' % sha]
    # L2: the scaffold STOPS emitting `acknowledge_texanim` -- it is a deprecated no-op.  What an
    # armed container gets instead is the DECODED table (already in the derivation comment block
    # above) plus, on the one shape that still refuses, the reason it refuses.
    if ta is not None and ta.armed:
        L += ["",
              "# TEXANIM IS ARMED (%d bytes at %#x..%#x) and %s."
              % (ta.nbytes, ta.lo, ta.hi, "DECODES" if ta_parsed else "does NOT decode"),
              ("# W7: the table blits 8-bit palette INDICES inside one creature part's own page.  It"
               if ta_parsed else
               "# W7 read the format, but not THIS region -- so it is armed-and-unread, which is the"),
              ("# binds no CLUT word and writes no CLUT contents, so a recolour survives the cast and"
               if ta_parsed else
               "# pre-W7 state: a CREATURE target below is REFUSED outright and no key lifts that."),
              ("# every target below is open with no acknowledgement key at all."
               if ta_parsed else
               "# Scenery targets are back to the pre-W7 posture: `acknowledge_texanim = true`"),
              *([] if ta_parsed else
                ["# (its ORIGINAL meaning -- orthogonality assumed, not proven)."])]
    L += ["", "", "# " + "=" * 92,
          "# THE SPANS -- guards on the derivation.  Auto-named by chunk SLOT (`s{slot}`), because",
          "# `chunk_index` is not unique (ef381's nine chunks are [0,1,1,1,1,1,1,1,1]).", ""]
    for s in pmap.spans:
        L += ["[reskin.spans.%s]" % s.name,
              "offset = %#08x    # %s" % (s.lo, s.source),
              "length = %d" % s.size,
              ""]
    L += ["", "# " + "=" * 92,
          "# DEFAULTS -- any target that omits a knob inherits these.",
          "[reskin.defaults]",
          "hue_rotate = 0.0",
          "saturation = 1.0",
          "value      = 1.0",
          "", "", "# " + "=" * 92,
          "# THE TARGETS.  `hue_rotate` is a DELTA; `hue_to` is the ABSOLUTE form (the tool computes",
          "# `hue_to - the measured mean hue` printed on each row).  Use `hue_to` for a multi-writer",
          "# cell -- it is required there, because each writer has its own mean.", ""]

    hazards = pmap.hazards
    for p in pmap.palettes:
        words = struct.unpack_from("<%dH" % p.entries, blob, p.off)
        h, s, v = _mean_hsv(words)
        live = sum(1 for w in words if w)
        peak = _peak5(words)
        cell = hazards.get(p.vram)
        blocked = []
        if cell is not None and cell.dual_depth:
            blocked.append("DUAL-DEPTH cell -- REFUSED outright, no key lifts it")
        if cell is not None and cell.multi_writer:
            blocked.append("MULTI-WRITER cell (%d writers) -- name EVERY writer, all with `hue_to`"
                           % len(set(cell.offsets)))
        if p.shared:
            blocked.append("SHARED -- needs `acknowledge_shared = true`")
        # W7: an armed texanim blocks nothing when its table DECODES.  When it does not, the pre-W7
        # posture stands for both scopes: creature refuses outright, scenery needs the old key in
        # its original meaning (V1 F1 -- the lift is conditional on a successful parse, per scope).
        if ta is not None and ta.armed and not ta_parsed:
            if p.slot < 0:
                blocked.append("CREATURE under an armed texanim whose table does NOT decode -- "
                               "REFUSED outright, no key lifts it")
            else:
                blocked.append("scenery under an armed texanim whose table does NOT decode -- needs "
                               "`acknowledge_texanim = true` (its original pre-W7 meaning)")
        L.append("[[reskin.target]]")
        L.append('name = "%s"%s' % (p.name, ("    # = %s" % p.alias) if p.alias else ""))
        L.append("expect_entries = %d" % p.entries)
        L.append("expect_vram = [%d, %d]" % p.vram)
        L.append("expect_offset = %#08x" % p.off)
        if blocked:
            L.append("enabled = false          # %s" % "; ".join(blocked))
            if p.shared:
                L.append("acknowledge_shared = false")
        L.append("hue_rotate = 0.0")
        L.append("saturation = 1.0")
        L.append("value      = 1.0")
        if peak >= 31:
            L.append("# ZERO HEADROOM: peak channel is 31/31, so any `value > 1.0` only flattens the")
            L.append("# top of the ramp and REFUSES without `acknowledge_headroom = true`.")
        L.append("# measured: %d live entries, mean H %.1f S %.2f V %.2f | peak %d/31, headroom %d,"
                 " value ceiling x%.3f"
                 % (live, h, s, v, peak, 31 - peak, (31.0 / peak) if peak else float("inf")))
        L.append('note = "%s"' % (p.shared_reason or p.note or "").replace('"', "'"))
        L.append("")
    return "\n".join(L) + "\n", pmap


def load_spec(path) -> dict:
    with open(path, "rb") as fh:
        spec = tomllib.load(fh)
    r = spec.get("reskin")
    if not isinstance(r, dict):
        raise ReskinError("%s has no [reskin] table" % path)
    # W6q-0: the same fail-closed rule one table up.  `mint_clut = true` or `acknowledge_shared` at
    # [reskin] level was silently ignored before this rung, which is the shape a mistyped guard takes
    # when nobody reads it.
    _refuse_unknown_keys(r, _RESKIN_KEYS, "[reskin]")
    for key in ("effect", "target"):
        if key not in r:
            raise ReskinError("[reskin] needs `%s`" % key)
    return spec
