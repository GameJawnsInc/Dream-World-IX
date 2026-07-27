r"""TIER W rungs 4+5 -- THE RESKIN: recolour ANY summon's palette set in place, stock bytes untouched.

    py reskin.py scaffold --ef 211              # read the container, EMIT a complete guarded toml
    py reskin.py plan   bahamut_reskin.toml     # resolve every target + print the numbers, write nothing
    py reskin.py build  bahamut_reskin.toml     # stage the container + the deploy/revert scripts + previews
    py reskin.py verify bahamut_reskin.toml     # re-check what is staged, as bytes

WHAT THIS IS
------------
W2 moved the camera, W3 moved the clocks; both proved a same-length in-place splice of a stock
summon container survives every gate and lands hot.  W4 spent that posture on the one lever the
recon (``w4-recon/A1..A4``) says is cleanest: **LEVER #1, the CLUT recolour**.  Not one texel moves.
The creature's 256-entry palettes and the effect's own scenery palettes are decoded, rotated through
HSV, re-encoded to BGR555 and spliced back at the same offsets.

W5 -- THE GENERALISATION -- took that tool off ef227 without moving one of ef227's bytes.  W4 worked
on exactly one effect and would have MISLED on the others; the eight things that were true of
Bahamut and not of the corpus are now derived, refused or disclosed:

* **names are keyed on chunk SLOT** (``pal.s{slot}.x{X}_y{Y}.e{entries}``), because ``chunk_index``
  is not unique -- ef381's nine chunks are ``[0,1,1,1,1,1,1,1,1]`` -- so W4's ``c{index}`` tag made
  two spans share a name and a TOML guard silently validate the wrong one.  ef227's own English and
  ``c{index}`` names still resolve, through an ALIAS map;
* **attribution and the SHARED flag are derived** from the container's own ``so`` bindings (magic
  ``0x6F73``) instead of a hand table keyed on bare VRAM cells, and un-attributed palettes below
  complete coverage are **shared-UNKNOWN**, not "private".  On ef227 the derivation reproduces the
  hand table exactly -- two shared cells, five single-bound, three unbound;
* **multi-writer and dual-depth CLUT cells** are detected and refused (ef381, ef447);
* the **texanim** region gates the creature scope outright (ef038/177/493/494/495);
* **headroom is measured per target** -- A3's "stock leaves headroom" is an ef227 measurement, and
  46 of the corpus's 93 creature rows peak at the 5-bit ceiling;
* the **whole-set envelope**, the **preview page columns** and the **id-9 slot map** are computed,
  not tabulated;
* a **scenery-only** reskin works on the 348 containers that carry no creature at all;
* and every effect stages into **its own** SCRATCH root.

Lever #2 (texel repaint) is DEFERRED and this module refuses to do it: A1's chunk-1 overwrite (six
VRAM slots written by two container regions) and A2's dual-depth packing at VRAM column 448 (the same
4,032 halfwords read as a 4bpp cloud band AND as 8bpp energy rings) are both repaint hazards, and
both are structurally invisible to a palette edit -- the two readings have separate palettes and the
time-shared columns share no CLUT.  A recolour is immune to the exact traps a repaint would hit.

WHY THE SPANS ARE DERIVED AND NOT TABULATED
-------------------------------------------
A2's edit menu names the byte spans.  This module does not copy them: it **re-derives every palette
from the container's own headers** and then asserts A2's map on top, so a spec that ever disagrees
with the bytes underneath refuses instead of splicing into the wrong place.

* the creature strip comes from the id-4 model-package header (``texOffset``/``texBytes``/
  ``clutBytes``) through the kit's own ``summons.texture`` decoder -- the shipped, corpus-proven one;
* the scenery palettes come from each chunk's **id-0 payload header**: ``nClut4``/``nClut8`` and the
  CLUT-word list at ``+0x10`` declare exactly which palettes exist and where in VRAM, and the inline
  rect stream at ``inlineRel`` says which file bytes each VRAM row is.  Both were re-read this rung.

That re-derivation settled the one A1-vs-A2 disagreement on the record: **chunk 1's id-0 declares
``nPageRects = 3``, not 1** (A2's reading).  The proof is the header's own arithmetic -- the inline
stream ends at exactly ``P + pixelDataRel`` in both chunks (c0 ``0x1470``, c1 ``0xa2850``), and three
64x256 page rects then fill the combined id-0+id-1 payload exactly.  The CLUT spans this module
writes are *upstream* of that pixel base in both chunks, so the disagreement never touched them --
but it is settled anyway, because a span derived from a header you have not read is a guess.

THE TRANSFORM, AND THE FIVE HARD RULES (each one a refusal here, not a note in a docstring)
-------------------------------------------------------------------------------------------
An entry is a little-endian **BGR555** halfword: bits 0-4 R, 5-9 G, 10-14 B, bit 15 = STP.

1. ``0x0000`` in, ``0x0000`` out -- byte-exact.  A3 measured it: STP-clear-and-RGB-zero is the
   OPAQUE shader's cutout, and every one of ef227's palettes uses it.  Drift either way punches a
   hole or fills one with solid black.
2. **bit 15 is carried, never recomputed.**  The STP population is compared stock-vs-patched per
   palette and a difference refuses the stage.
3. output channels are **clamped to 0..31**, and the clip that can actually happen is **counted per
   target and gated**.  The instrument here is the HSV clip, not the channel clamp: ``_clamp01``
   bounds ``s``/``v`` BEFORE ``hsv_to_rgb``, whose max component is exactly ``v``, so the channel
   clamp is structurally unreachable through this path (swept and pinned in
   ``test_apply_word_channel_clamp_bit_is_structurally_unreachable``) and a counter that cannot
   count is not an instrument.  What IS reachable is a knob asking for ``s * sat`` or ``v * val``
   past 1.0, which flattens that entry onto the ceiling -- so THAT is what is counted, split
   sat-vs-value, reported per target with its fraction of live entries and its worst overshoot, and
   FAILED at ``BLOWOUT_FRACTION``.  A3's headroom note (the effect's own ``colorIntensity``
   multiplies 1x/1.5x/2x over the palette) is why the spec keeps ``value`` near 1 on bright targets.
4. the transform runs in **RGB after the decode**, in HSV, and re-encodes to 5 bits.  Hue rotation
   is exact on the wheel; saturation and value are scales, so an achromatic palette is INVARIANT
   (measured: ef227's cloud bands are pure greyscale, S = 0.00 on all 15 live entries -- they cannot
   move under this transform and the report says so rather than pretending).
5. every changed byte must land inside a **named, derived palette** inside a derived span; anything
   else is UNEXPLAINED and refuses the stage.  The envelope those spans sum to is derived per
   effect, not the 8,192 B ef227 happens to declare.

THE REFUSALS W5 ADDED (each one a call-site check with a test, never a note in a docstring)
-------------------------------------------------------------------------------------------
* **no drift guard at all** -- no ``expect_sha256`` and no registered hash, unless ``allow_unguarded``;
* **texanim armed** -- creature scope refused outright, scenery scope needs ``acknowledge_texanim``;
* **dual-depth CLUT cell touched** -- refused outright, no key;
* **multi-writer CLUT cell touched** -- every writer must be named, and all of them with ``hue_to``;
* **shared palette enabled** without ``acknowledge_shared`` (now DERIVED, including the UNKNOWN case);
* **zero-headroom ``value`` lift** without ``acknowledge_headroom``;
* two target rows resolving to the **same derived palette** through different spellings.

A disabled row splices nothing, so it states an intent rather than an edit: its acknowledgements
become mandatory the moment it is switched on, which is what lets a scaffold ship every declared
palette pre-seeded off and still build clean.

ORTHOGONALITY -- proved, not asserted
--------------------------------------
The self-check rebuilds **W2's rescore and W3's retime from their own specs** and intersects their
changed-offset sets with this rung's.  Empty intersection is the proof that W2/W3/W4 can ship in one
container.  The sibling specs are chosen by the spec itself (``[reskin.orthogonality]``) and a
sibling that targets a DIFFERENT effect is skipped with that stated -- rebuilding Bahamut's camera
proves nothing about a reskin of ef211.  On top of that it gates whole regions byte-identical:
sector 0 (the resource table + the sequence stream), every id-3 program image, every camera block,
every GEOM block, the id-5 model image, and the whole id-4 header+texel region -- i.e. the geometry
and UVs a repaint would touch.

PROVENANCE
----------
The container is read at RUN TIME from ``resources.assets`` in the user's own install under the
registered sha256 drift guard.  Everything staged is SE-derived and lands under SCRATCH;
``_refuse_repo_path`` refuses the repo and ``_refuse_install_path`` refuses the install.  The
previews are DECODED STOCK ART and are SCRATCH-only for the same reason.  This file and its spec
carry offsets, counts, VRAM coordinates and transform scalars -- no run of stock bytes and no stock
palette.
"""
from __future__ import annotations

import argparse
import colorsys
import dataclasses
import hashlib
import json
import math
import os
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import rescore as R                                          # noqa: E402  (sets up sys.path)
import summon_camera as W                                    # noqa: E402
import ef_container as EC                                    # noqa: E402
from ff9mapkit.summons import container as KC                # noqa: E402
from ff9mapkit.summons import texture as KT                  # noqa: E402

try:                                                         # py3.11+ stdlib, else the backport
    import tomllib as _toml
except ModuleNotFoundError:                                  # pragma: no cover
    import tomli as _toml                                    # type: ignore

_STUDY = os.path.dirname(_HERE)                              # studies/custom-summons
_REPO = os.path.dirname(os.path.dirname(_STUDY))             # <repo>

#: W4's staging root -- ef227's, and ONLY ef227's.  Its ``mod/``, ``previews/``, ``live-snapshot/``
#: and ``revert_summon_reskin_227.py`` are a cast-proven, deployed artifact; W5 does not move them.
SCRATCH_W4_ROOT = os.environ.get("FF9_RESKIN_SCRATCH",
                                 r"C:\gd\SCRATCH\summon-format\reskin-w4")

#: W5's staging BASE -- every other effect gets ``<base>\ef%03d\``, so two effects staged in one
#: session can never collide on ``mod/``, ``previews/``, ``build_manifest.json`` or the ledger.
SCRATCH_W5_BASE = os.environ.get("FF9_RESKIN_SCRATCH_W5",
                                 r"C:\gd\SCRATCH\summon-format\reskin-w5")

#: kept as a NAME for the W4 gate runner and any caller that predates the split; it is ef227's root.
SCRATCH_ROOT = SCRATCH_W4_ROOT

#: the effect whose staging layout is frozen (W4 shipped and cast it); everything else is W5-lane.
LEGACY_STAGING_EFFECT = 227


def staging_root(effect: int) -> str:
    """The per-effect staging root.  ef227 keeps W4's exact layout; every other effect gets its own
    ``reskin-w5\\ef%03d`` directory (D11) -- the whole point being that a second effect staged in the
    same session cannot overwrite the first one's container, previews, manifest or revert script."""
    if int(effect) == LEGACY_STAGING_EFFECT:
        return SCRATCH_W4_ROOT
    return os.path.join(SCRATCH_W5_BASE, "ef%03d" % int(effect))


#: the on-disc override lane, shared with W2/W3 (extensionless: LoadFromDisc reads the raw path)
MOD_SUBPATH = R.MOD_SUBPATH                                  # "FF9_Data/SpecialEffects"

#: ef227's own whole-set envelope, kept as a documented FACT (3,072 creature + 3,072 + 1,024 + 1,024
#: scenery = A2's edit menu (c)).  It is NOT the gate any more: the envelope is derived per effect as
#: ``sum(span.size for span in pmap.spans)`` (``PaletteMap.envelope``), because the corpus spread is
#: enormous -- ef227 declares 4 spans, ef381 declares 15 and 73 scenery palettes.
WHOLE_SET_CEILING = 8192

#: the blow-out gate's sensitivity: the share of a palette's LIVE entries a target's knobs may flatten
#: onto the HSV ceiling before the build REFUSES.  A few clipped entries are normal and harmless --
#: an entry already at S = 1.00 or near the top of V simply cannot go further, and its neighbours
#: land 1-2 of 31 away, which is inside the 5-bit grid the palette already lives on.  A large share
#: is the real failure this gate exists for: a `value = 1.6` on an already-bright page crushes every
#: highlight onto one white and the gradient it belonged to stops existing.  10% leaves the shipping
#: spec (worst target 4.7%) a 2x margin while still catching that.  Retunable, deliberately: it is
#: the instrument's sensitivity, and the per-target census prints either way so the number is judged.
BLOWOUT_FRACTION = 0.10

#: THE ef227 NAMING OVERLAY -- and nothing but naming.  W4 hard-coded an English ATTRIBUTION table
#: keyed on BARE VRAM CELLS, which is the most dangerous ef227-ism in the lane: ``(0,245)`` exists on
#: most of the corpus and means something different on each one (ef038 binds it from 7 models, ef381
#: from 6).  W5 DERIVES both the attribution and the ``shared`` flag from the container's own
#: ``so`` bindings (:func:`attribution`), and the derivation reproduces this table EXACTLY on ef227:
#: ``(0,244)`` 2 binders and ``(192,244)`` 3 binders come back SHARED, the other five come back
#: single-bound, and the three unattributed cells come back with no binder at 100% ``so`` coverage.
#:
#: So this table survives only as ALIASES: it lets ``bahamut_reskin.toml`` keep saying
#: ``scenery.sky_dome`` where the derivation says ``pal.s0.x0_y245.e256``, and it supplies the
#: English note for the report.  It is applied ONLY when the spec's ``effect == 227``.
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

#: the id-9 alternate-page slot map, A1 section 4 / A2 section 2.3, as CODE rather than as ef227's
#: two measured offsets.  ``fn 0x3E4AB`` is an 8-slot loop; slot ``i`` is enabled by bit
#: ``ID9_SLOT_BIT[i]`` of the resource's own ``info`` byte and the payload cursor advances 0x4000
#: only on an enabled slot.  Preview-only: a wrong slot map draws a wrong picture, never a wrong byte.
ID9_SLOT_BIT = (0, 0, 1, 1, 2, 3, 4, 5)


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
#: the magic every non-creature GEOM block's binding record carries (A2 section 3.5 / A1 section 3.5).
SO_MAGIC = 0x6F73                                            # 'so', little-endian
#: PSX TPAGE colour-mode field (bits 7-8) -> bits per texel
SO_BPP = {0: 4, 1: 8, 2: 15, 3: 15}


def so_record(blob: bytes, geom_base: int) -> Optional[dict]:
    """The 8- or 16-byte binding record that immediately precedes a non-creature GEOM block.

    Ported VERBATIM from the A2 recon script that measured it (376 records / 340 textured / 340
    self-consistent corpus-wide) -- W4 left it in SCRATCH, which is why ``reskin.py`` had to hard-code
    an English attribution table instead of deriving one.  Layout::

        +0x00 u16 magic  == 0x6F73 ('so')
        +0x02 u16 textured    1 = carries tpage/clut, 0 = Gouraud/flat only
        +0x04 u16 geomOff     0x10 (textured) / 0x08 (untextured) -- record -> GEOM, and the length
        +0x06 u16 OPAQUE
        +0x08 u16 tpage       (textured only)
        +0x0a u16 clut        (textured only; 0 when the tpage says 15bpp direct colour)
        +0x0c u16 OPAQUE
        +0x0e u16 OPAQUE

    The acceptance test is the magic AND the self-describing length, so a coincidental ``0x6F73``
    two bytes before a GEOM block cannot be mistaken for a record.
    """
    for rec_len in (0x10, 0x08):
        o = geom_base - rec_len
        if o >= 0 and _u16(blob, o) == SO_MAGIC and _u16(blob, o + 4) == rec_len:
            rec = {"at": o, "len": rec_len, "textured": _u16(blob, o + 2)}
            if rec_len == 0x10:
                rec["tpage"] = _u16(blob, o + 8)
                rec["clut"] = _u16(blob, o + 0x0A)
            return rec
    return None


@dataclass(frozen=True)
class Binding:
    """One GEOM model's texture binding: which page it samples and which CLUT cell colours it."""
    geom: int
    chunk_slot: int
    tpage: int
    page: Tuple[int, int]        # tpage VRAM origin (x halfwords, y lines)
    bpp: int
    clut_word: int
    cell: Tuple[int, int]        # CLUT VRAM cell (x entries, y line)
    entries: int                 # 16 (4bpp) or 256 (8bpp)


@dataclass
class Attribution:
    """Who binds what, derived -- the replacement for W4's hard-coded ``ATTRIBUTION`` table.

    ``coverage`` is the honest instrument this rung insisted on: only 213 of 420 non-creature GEOM
    blocks across the 24 creature effects carry an ``so`` record (10 effects are at 0%), so an
    un-attributed palette is only "private" when coverage is COMPLETE.  Below that it is
    **shared-UNKNOWN** and the spec must acknowledge it -- never silently "not shared", which is
    exactly the failure mode W4's table had by construction on every effect but ef227.
    """
    bindings: List[Binding]
    geom_total: int
    geom_with_so: int

    @property
    def coverage(self) -> float:
        return 0.0 if not self.geom_total else self.geom_with_so / self.geom_total

    @property
    def complete(self) -> bool:
        """NO models found is NOT complete coverage -- it is NO EVIDENCE.

        222 of the 372 corpus containers declare zero non-creature GEOM blocks (they draw with
        sprites and particles, which carry no ``so`` record), so ``0/0`` is the common case and
        reading it as "100%, therefore nothing is shared" would hand back exactly the false
        confidence this derivation replaced.  It reads as UNKNOWN instead, and the spec has to say
        so per target."""
        return self.geom_total > 0 and self.geom_with_so == self.geom_total

    def binders(self, cell: Tuple[int, int], entries: int) -> List[Binding]:
        return [b for b in self.bindings if b.cell == cell and b.entries == entries]


def attribution(blob: bytes) -> Attribution:
    """Scan every non-creature GEOM block for its ``so`` record and join model -> (tpage, CLUT)."""
    mp = KC.creature_package(blob)
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
    total = with_so = 0
    for g in EC.scan_geom(blob):
        if creature_geom is not None and g.base == creature_geom:
            continue
        total += 1
        rec = so_record(blob, g.base)
        if rec is None:
            continue
        with_so += 1
        tp, cw = rec.get("tpage"), rec.get("clut")
        if tp is None or not cw:                             # untextured, or 15bpp direct (no CLUT)
            continue
        bpp = SO_BPP[(tp >> 7) & 3]
        if bpp == 15:                                        # direct colour: no palette to bind
            continue
        binds.append(Binding(geom=g.base, chunk_slot=owner_slot(g.base), tpage=tp,
                             page=((tp & 0x0F) * 64, ((tp >> 4) & 1) * 256), bpp=bpp,
                             clut_word=cw, cell=clut_word_xy(cw),
                             entries=16 if bpp == 4 else 256))
    return Attribution(bindings=binds, geom_total=total, geom_with_so=with_so)


# ============================================================ (1b) THE TEXANIM GATE
@dataclass(frozen=True)
class TexAnim:
    """The id-4 model image's texture-animation region -- the one W4 refusal that was only prose.

    The region is the byte range between the END of the GEOMETRY block (``+0x14 firstBlock``) and
    the FIRST motion clip (``+0x180 motionOffsets[]``), both header-relative.  ``firstBlock ==
    min(motionOffsets)`` means the region is empty; motion offsets are sorted on all 24 stock
    packages, so the comparison is exact.

    Corpus: 19 of 24 creature packages carry 0 bytes here.  The five that do not are **ef038** (116 B)
    and **ef177 / ef493 / ef494 / ef495** (364 B each) -- and ef038 is precisely the one effect whose
    programs call HLE op 12 ``Hi_StartSummonTexAnim``.  The table's internal format is UNREAD (A1
    section 8 item 1 lists it OPAQUE; neither 116 nor 364 divides by ``partCount * 0x18``), so
    whether a running texanim cycles the CLUT WORD, the texels/UV, or the CLUT CONTENTS is **not
    settled** -- and those three branches differ in whether a static recolour survives the cast.
    Refusal beats guessing.
    """
    present: bool                # the container has a decodable creature package at all
    armed: bool                  # ...and its texanim region is non-empty
    nbytes: int
    lo: int                      # absolute file offsets of the region (0,0 when absent)
    hi: int


def texanim_region(blob: bytes) -> TexAnim:
    mp = KC.creature_package(blob)
    if mp is None or not mp.motion_offsets:
        return TexAnim(present=mp is not None, armed=False, nbytes=0, lo=0, hi=0)
    lo = mp.to_file(mp.first_block)
    hi = mp.to_file(min(mp.motion_offsets))
    return TexAnim(present=True, armed=hi != lo, nbytes=max(0, hi - lo), lo=lo, hi=hi)


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
    ``(x, y)`` is what a model reading that cell sees.  Two rules, pure arithmetic on data the
    header derivation already returns:

    * more than one distinct FILE OFFSET writing the cell  => **multi-writer**.  ef381 is the fixture:
      a 9-chunk effect that streams a genuinely different palette into the same cell per phase (19
      cells, up to 5 writers, 480+ of 512 bytes different between writers).  Recolouring one writer
      leaves the others stock, so the cast flickers between two keys.  The only coherent authoring
      form is an ABSOLUTE hue (`hue_to`) applied to EVERY writer -- a `hue_rotate` delta lands each
      writer on a different hue, because each writer has its own mean.
    * more than one distinct ENTRY COUNT declared for the cell => **dual-depth**.  ef447's ``(0,242)``
      is the fixture: chunk slot 0 declares it a 16-entry 4bpp palette, chunk slot 2 declares it a
      256-entry 8bpp one.  Those are two different pictures over the same bytes and no evidence
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
        """The derived whole-set envelope: every declared CLUT span, summed.  ef227 = 8,192 B over
        4 spans (A2's edit menu (c) exactly); ef381 = 15 spans.  Replaces WHOLE_SET_CEILING."""
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
        """A spec-declared name -> the canonical derived name.  Legacy ``c{chunkIndex}``-tagged and
        ef227-overlay names resolve here, so a shipped spec keeps working after D1's rename."""
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
    """A PSX CLUT word -> its VRAM cell ``(x_entries, y_line)``.  ``x = (w & 0x3F) * 16``,
    ``y = w >> 6`` -- the same decode ``summons.texture.clut_row``/``clut_entry0`` perform against
    the creature strip's own base, written here without the strip bias because the scenery band
    sits at x = 0."""
    return ((word & 0x3F) * 16, word >> 6)


def chunk_tag(chunk) -> str:
    """THE D1 RENAME.  W4 tagged chunks ``c%d`` by ``chunk_index`` -- which is **not unique**:
    ef381's nine chunks are ``[0,1,1,1,1,1,1,1,1]`` and ef447's three are ``[0,1,1]``.  That made
    two different spans resolve to one name (``PaletteMap.span`` returned the first, so a TOML guard
    silently validated the wrong span) and made ef381 refuse outright on a duplicate-name clash that
    was a real hazard wearing an opaque error message.  ``slot`` is the resource table's own
    position and is unique by construction."""
    return "s%d" % chunk.slot


def palette_auto_name(slot: int, x: int, y: int, entries: int) -> str:
    """``pal.s{slot}.x{X}_y{Y}.e{entries}`` -- keyed on exactly the tuple A2 section 4.3 item 3 says
    the identity of a palette is: chunk SLOT, VRAM cell, and bit depth."""
    return "pal.s%d.x%d_y%d.e%d" % (slot, x, y, entries)


def span_auto_name(slot: int, k: int) -> str:
    return "s%d_clut_band%d" % (slot, k)


def id0_palettes(blob: bytes, chunk, tag: str) -> Tuple[List[Span], List[Palette]]:
    """Every palette one chunk's **id-0 payload header** declares, resolved to file bytes.

    The header (A1 section 3.1 / A2 section 2.2, both re-read against these bytes)::

        P+0x00 s32 pageBlockRel   -> { s32 pixelDataRel, s32 nPageRects, Rect[nPageRects] }
        P+0x04 s32 inlineRel      -> nInline x { Rect, u16 pixels[w*h] }   -- the CLUT images
        P+0x08 s32 nInline
        P+0x0c u16 nClut4         -- 16-entry palettes that follow
        P+0x0e u16 nClut8         -- 256-entry palettes that follow
        P+0x10 u16 clutWord[nClut4 + nClut8]

    The self-check the derivation rests on is exact and is asserted here: the inline rect stream
    must end at precisely ``P + pixelDataRel``.  If it does not, the header is not what we think it
    is and nothing is resolved.  Corpus: 385/385 id-0 resources across 372/372 containers decode
    clean, 490 inline rects, every one of them at VRAM x = 0.

    Names are AUTO and slot-keyed (D1); the attribution overlay, if any, is applied by
    :func:`palette_map` on top -- this function never invents an English name.
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
            # clutWord slots, not two palettes.  Record the extra slot, do not emit a duplicate.
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

    ``summons.texture.texture_check`` is the shipped, corpus-proven gate (24/24 packages): it
    refuses anything that is not the ``partCount`` x 0x4000 / ``clutRows`` x 0x200 8bpp layout.

    D9 -- CREATURE-OPTIONAL.  W4 RAISED here when there was no id-4, which made a scenery-only
    reskin of the **348 non-creature effects** impossible even though ``id0_palettes`` handles all
    372.  Now the absence is REPORTED (the third return value) and only becomes a refusal at the
    call site, when a spec actually names a ``creature.*`` target.
    """
    mp = KC.creature_package(blob)
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


def _apply_attribution(pals: List[Palette], attrib: Attribution) -> List[Palette]:
    """Hang the DERIVED ``shared`` flag and binder list on every scenery palette (D5).

    Three states, and the middle one is the whole point:

    * **bound by >1 GEOM model** -> ``shared = True``.  A2 guard-rail 3: it may only be recoloured
      as the GROUP it is, so the spec must acknowledge it.
    * **bound by no model, and ``so`` coverage is INCOMPLETE** -> ``shared = True``, reason UNKNOWN.
      We cannot tell "private" from "shared" because we could not read every model's binding; W4's
      table asserted ``shared = False`` here, which is the guard-rail defeated by construction.
    * **bound by no model at COMPLETE coverage** -> ``shared = False``, and the note says the honest
      thing: the header declares it, no GEOM model reads it, so something else (a sprite, a
      particle) does.
    """
    out: List[Palette] = []
    pct = 100.0 * attrib.coverage
    for p in pals:
        if p.slot < 0:                                       # the creature strip: not so-bound
            out.append(p)
            continue
        binders = attrib.binders(p.vram, p.entries)
        if len(binders) > 1:
            out.append(dataclasses.replace(
                p, shared=True, binders=tuple(sorted(b.geom for b in binders)),
                shared_reason="DERIVED SHARED: %d GEOM models bind this cell (%s)"
                              % (len(binders), ", ".join("%#x" % b.geom for b in sorted(
                                  binders, key=lambda x: x.geom))),
                note=p.note or "read by %d models" % len(binders)))
        elif len(binders) == 1:
            out.append(dataclasses.replace(
                p, shared=False, binders=(binders[0].geom,),
                shared_reason="DERIVED PRIVATE: exactly one GEOM model (%#x) binds this cell"
                              % binders[0].geom,
                note=p.note or "bound by GEOM %#x" % binders[0].geom))
        elif not attrib.complete:
            why = ("this container declares NO non-creature GEOM models at all, so attribution has "
                   "no evidence to work from (222 of the 372 corpus containers are in this class)"
                   if attrib.geom_total == 0 else
                   "only %d of %d GEOM blocks (%.1f%%) carry one"
                   % (attrib.geom_with_so, attrib.geom_total, pct))
            out.append(dataclasses.replace(
                p, shared=True,
                shared_reason="SHARED-UNKNOWN: no `so` record names this cell, and %s -- sharing "
                              "cannot be ruled out" % why,
                note=p.note or "UNATTRIBUTED at %.0f%% so-coverage" % pct))
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
    """Every palette a container declares, from its own headers.  Nothing tabulated.

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

    # ---- the legacy alias map.  W4 tagged by `chunk_index`; that tag is only unambiguous when the
    # container's chunk_index values are distinct (ef227 [0,1] yes; ef381 [0,1,1,1,1,1,1,1,1] no).
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
    if dupes:                                            # pragma: no cover - D1 rules it out
        raise ReskinError("two palettes resolved to the same name: %s" % ", ".join(dupes))
    return PaletteMap(spans, pals, aliases=aliases, span_aliases=span_aliases, attrib=attrib,
                      creature_error=cre_err, texanim=texanim_region(blob))


def creature_pages(blob: bytes) -> Dict[str, int]:
    """``{palette name: page file offset}`` for the creature -- the preview's exact 1:1 page map."""
    mp = KC.creature_package(blob)
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


def scenery_pages(blob: bytes) -> Dict[Tuple[str, int], PageRect]:
    """``{(chunk tag, vram x): PageRect}`` for the streamed page rects.

    Derived from the id-0 page block: ``pixelDataRel`` is the stream base and the rect list gives
    the column order.  W4 hard-coded ``128 x 256`` at the preview call site; the rects are NOT all
    that shape corpus-wide, so the dimensions come from the rect itself now.
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
            out[(tag, x)] = PageRect(source=tag, x=x, y=y, w=w, h=h, off=cur, nbytes=w * h * 2)
            cur += w * h * 2
    return out


def id9_pages(blob: bytes) -> Dict[Tuple[str, int], List[PageRect]]:
    """``{(chunk tag, vram x): [PageRect]}`` for the id-9 ALTERNATE page path (D6).

    Replaces W4's two measured ef227 offsets with the loop's own arithmetic: slot ``i`` is enabled
    by bit ``ID9_SLOT_BIT[i]`` of the resource's ``info`` byte, lands at :func:`id9_slot_vram`, is
    always 64 x 128 halfwords, and the payload cursor advances 0x4000 **per enabled slot**.
    Corpus: ``nbytes == enabledSlots * 0x4000`` on 37/37 id-9 resources.
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


def preview_source(blob: bytes, pal: Palette, attrib: Attribution) -> Optional[List[PageRect]]:
    """Which file bytes hold the texels a scenery palette colours -- the D5 (iii) replacement for
    the hard-coded ``PREVIEW_PAGE`` table.

    The ``so`` record that binds the palette also names the model's TPAGE, so the column is a
    by-product of attribution.  Which upload of that column to draw is the one judgement call: a
    column can be written by more than one chunk (A1's time-shared columns), so we prefer the
    binder's OWN chunk -- its id-0 page rect first, then its id-9 alternate blocks -- and fall back
    to any chunk that writes it.  On ef227 this reproduces W4's hand table exactly on all five
    attributed pages, including the two that disagree with the naive reading (energy_rings' binder
    is in chunk 1 but only chunk 0 uploads column 448; cloud_sheet's binder is in chunk 0 where
    column 832 exists only as id-9).
    """
    bind = attrib.binders(pal.vram, pal.entries)
    if len(bind) != 1:
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
    """One target's recolour.  ``hue`` is degrees on the wheel; ``sat``/``val`` are scales.

    ``hue_to`` (D8) is the ABSOLUTE authoring form: the spec names the hue it wants and the build
    computes ``hue = hue_to - the palette's own measured mean hue``.  ``bahamut_reskin.toml``
    already documents every one of its rotations that way in prose ("measured mean H 243.8 -> ~190
    deep teal"); this makes the tool do the subtraction instead of the author, which is what makes
    the artistic surface effect-INDEPENDENT.  It is also REQUIRED for a multi-writer co-transform:
    each writer of a cell has its own mean, so one shared ``hue_rotate`` delta lands them on
    different hues while one shared ``hue_to`` lands them on the same one.
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


#: ``apply_word``'s clip flags.  SAT and VAL are the REACHABLE ones: the target's own knob asked for
#: a saturation or value outside the HSV cube and ``_clamp01`` flattened that entry onto the ceiling
#: (or the floor).  That is the real, silent artistic failure -- several entries land on the same
#: colour and a gradient loses a step -- so it is what gets counted, per target, and gated.
#:
#: CHANNEL is the structural belt on rule 3 and is UNREACHABLE through this path: ``_clamp01`` bounds
#: ``s``/``v`` into ``[0,1]`` before ``hsv_to_rgb``, whose largest component is exactly ``v``, so
#: ``int(f * 31.0 + 0.5)`` tops out at ``int(31.5) == 31`` and never exceeds it.  Measured, not
#: argued: a dense sweep of the post-clamp ``(h,s,v)`` cube (including the exact ``1.0`` corners) and
#: 3.9M real ``apply_word`` calls at knobs up to the 4x refusal ceiling both top out at exactly 31,
#: and ``test_apply_word_channel_clamp_bit_is_structurally_unreachable`` pins it.  The branch stays
#: as a belt against a future reordering of the clamp -- but it is NOT the reported instrument,
#: because a counter that cannot count reports "all clear" for every input, including a ruinous one.
CLIP_SAT = 1
CLIP_VAL = 2
CLIP_CHANNEL = 4


def apply_word(word: int, t: Transform) -> Tuple[int, int]:
    """One BGR555+STP halfword through the transform.  Returns ``(new word, clip flags)``.

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
    """Rank correlation, ties averaged.  1.0 = the ordering survived exactly."""
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
        """31 - the stock peak: how much a brightening recolour can actually spend (D4).

        A3's headroom note ("stock leaves headroom", measured 28 of 31) is an **ef227 measurement,
        not a corpus law**: 46 of the 93 creature CLUT rows in the corpus peak at exactly 31, and 14
        of the 24 creature effects have at least one row already on the ceiling.  ef211 -- W5's
        second-proof target -- is all six rows at 31, i.e. ZERO headroom, where ef227 is one of the
        least saturated creatures in the whole set."""
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
        """Clipped share of the LIVE entries -- the number the blow-out gate judges.  A handful of
        already-at-the-ceiling entries is normal and harmless (they simply cannot go further); a
        large share means the knob is crushing a whole region of the palette onto one colour."""
        return self.clipped / self.live if self.live else 0.0


def _mean_hsv(words: Sequence[int]) -> Tuple[float, float, float]:
    """The saturation-weighted mean hue of the LIVE entries, plus mean S and V.

    Hue is circular, so it is averaged as a vector; weighting by S keeps a near-grey entry from
    dragging the answer to an arbitrary angle (A2's own caution about page-wide colour statistics,
    applied to the palette)."""
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
    """The brightest 5-bit channel over the LIVE entries -- the headroom instrument (D4)."""
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
    #: WHICH drift guard actually applied -- the ``rescore.Build.guard`` posture, adopted here
    #: because W5's ``describe`` printed "none -- unguarded" purely from
    #: ``effect in R.EXPECTED_STOCK_SHA``, i.e. it called every generalised effect unguarded even
    #: when its own spec pinned ``expect_sha256`` and :func:`build` had already ENFORCED it at
    #: :func:`R.drift_guard`.  On a tool whose normal case is "the spec carries the hash", a report
    #: that says "unguarded" about a guarded build is a lie in the direction that gets a guard
    #: removed.  Set once, at the same call site that computes ``sha_in``.
    guard: str = "none -- UNGUARDED"

    @property
    def enabled(self) -> List[Target]:
        return [t for t in self.targets if t.enabled]


def _transform_of(d: dict, defaults: dict, where: str, mean_hue: float = 0.0) -> Transform:
    def num(key, dflt):
        v = d.get(key, defaults.get(key, dflt))
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise ReskinError("%s: `%s` must be a number, got %r" % (where, key, v))
        return float(v)

    # D8: `hue_to` is absolute, `hue_rotate` is a delta; the row may declare exactly one of them.
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
                          "that and A3's colorIntensity multiplies 1.5x/2x on top (got %s)"
                          % (where, t))
    return t


def _gate_texanim(pmap: PaletteMap, targets: List["Target"], ack: bool) -> None:
    """D3 -- THE TEXANIM GATE, at the call site.

    W4-RESKIN.md mandated "refuse or warn on ef038 / ef177 / ef493-495 until the texanim table's
    internal format is read" and then shipped it as PROSE ONLY.  Here it is a refusal.

    The asymmetry is deliberate and is exactly what the evidence supports.  The arming ops
    (``Hi_StartSummonTexAnim``, HLE op 12) index ``SummonData+0x70`` at **stride 0x18 BY PART**, and
    ``Hi_RegisterSummonModel`` sources that table from ``model[+0x40]`` -- immediately past the
    per-part ``v_offset`` array.  So the record is PER CREATURE PART: a texanim can rewrite what a
    creature part reads, and a creature recolour on such an effect is refused OUTRIGHT.

    Scenery is a different question with a weaker answer.  Nothing in A1-A4 connects the per-part
    texanim table to the effect's own set, so a scenery-only recolour is *plausibly* orthogonal --
    but "plausibly" is not "provenly", and the table's internal format is unread, so a branch where
    it rewrites CLUT CONTENTS from a block inside the 116/364-byte region cannot be excluded.  That
    is what ``acknowledge_texanim = true`` states, in those words: scenery only, orthogonality
    assumed and not proven.
    """
    ta = pmap.texanim
    if ta is None or not ta.armed:
        return
    live = [t for t in targets if t.enabled]
    creature = [t.name for t in live if t.pal.slot < 0]
    if creature:
        raise ReskinError(
            "TEXANIM ARMED (%d bytes at %#x..%#x) and this spec recolours the CREATURE (%s).  The "
            "texanim record is PER PART (stride 0x18, sourced from model[+0x40] next to the per-part "
            "v_offset array) and its internal format is UNREAD, so a running animation may cycle the "
            "CLUT word, the texels/UVs, or the CLUT contents -- and only one of those three leaves a "
            "static recolour intact.  This is not a knob: read the table first.  (The corpus class is "
            "ef038 / ef177 / ef493 / ef494 / ef495.)"
            % (ta.nbytes, ta.lo, ta.hi, ", ".join(creature)))
    if live and not ack:
        raise ReskinError(
            "TEXANIM ARMED (%d bytes at %#x..%#x).  A scenery-only recolour is PLAUSIBLY orthogonal "
            "to it -- the texanim record is per CREATURE PART -- but nothing on the record proves the "
            "effect's own set is untouched, so the spec must say `acknowledge_texanim = true` at the "
            "[reskin] level to state exactly that: scenery scope only, orthogonality assumed, not "
            "proven." % (ta.nbytes, ta.lo, ta.hi))


def _gate_cells(pmap: PaletteMap, targets: List["Target"]) -> None:
    """D2 -- the multi-writer and dual-depth CLUT-cell refusals (see :class:`Cell`)."""
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
            "target %s is a SHARED palette.  %s.  A2 guard-rail 3: it may only be recoloured as the "
            "GROUP it is, so the spec must say `acknowledge_shared = true` to show the author knows "
            "more than one set piece moves." % (t.name, t.pal.shared_reason or t.pal.note))


def _gate_headroom(blob: bytes, t: "Target") -> None:
    """D4 -- the ZERO-HEADROOM refusal.

    A3's headroom note is an ef227 measurement, not a law (L5): 46 of the corpus's 93 creature CLUT
    rows peak at exactly **31 of 31**, where ef227's six peak at 28/28/24/22/28/27.  On a row that
    is already on the 5-bit ceiling there is PROVABLY no headroom at all, so any ``value > 1.0`` is
    pure flattening of the top of the ramp -- it cannot brighten anything.  That case refuses unless
    the spec says ``acknowledge_headroom = true``.

    Everything short of that (a peak of 30 under a 1.12 lift, say) is a MAGNITUDE question, not a
    yes/no one, and stays with the instrument that measures it: the HSV clip census and
    BLOWOUT_FRACTION.  ef227 clears this gate untouched -- its worst target, part4 at peak 28 under
    value 1.12, is exactly the 4.7%-of-live overshoot its own spec already documents.
    """
    if t.t.val <= 1.0 or t.ack_headroom:
        return
    peak = palette_peak(blob, t.pal)
    if peak >= 31:
        raise ReskinError(
            "target %s has ZERO HEADROOM: its brightest live 5-bit channel is already 31 of 31, so "
            "`value = %.3f` cannot brighten anything -- it can only flatten the top of the ramp onto "
            "one colour.  46 of the corpus's 93 creature CLUT rows are in this class (ef211 is all "
            "six), and A3's \"stock leaves headroom\" note is an ef227 measurement, not a law.  Do "
            "the work with hue and saturation, or say `acknowledge_headroom = true`."
            % (t.name, t.t.val))


def build(spec: dict, spec_path: str = "?", game=None, blob: Optional[bytes] = None) -> Build:
    """``blob`` lets a caller supply the container directly (test_rescore.py's / test_retime.py's
    ``build_patched(..., blob=...)`` posture) so the whole span-guard / per-target / shared-CLUT /
    drift-guard pipeline is exercised on synthetic bytes -- no install required.  Omitted, the
    container is read from the user's own install exactly as before."""
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
            "in rescore.EXPECTED_STOCK_SHA.  W4 merely printed \"unguarded\" here, which means a "
            "Steam/Moguri patch or another mod could move a span under the edit and nothing would "
            "notice.  Run `py reskin.py scaffold --ef %d` to emit the guard from your own install, "
            "or say `allow_unguarded = true` deliberately." % (effect, effect))
    sha_in = R.drift_guard(effect, blob, r.get("expect_sha256"))
    # Record WHICH guard matched, so `describe` can report the truth instead of inferring it from
    # the registry alone.  `R.drift_guard` prefers the spec's own hash over the registered one, and
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
                              ack_shared=bool(d.get("acknowledge_shared")),
                              ack_headroom=bool(d.get("acknowledge_headroom"))))

    # ---- the gates that only an ENABLED target can trip.  A disabled row splices nothing, so it
    # states an intent rather than an edit; its acknowledgements become mandatory the moment it is
    # switched on, and `plan` previews it through the transform it declares either way.
    _gate_texanim(pmap, targets, bool(r.get("acknowledge_texanim")))
    _gate_cells(pmap, targets)
    for t in targets:
        if not t.enabled:
            continue
        _gate_shared(t)
        _gate_headroom(blob, t)

    out = bytearray(blob)
    for t in targets:
        if not t.enabled:
            continue
        t.result = apply_palette(blob, t.pal, t.t)
        out[t.pal.off:t.pal.off + t.pal.nbytes] = t.result.new
    patched = bytes(out)
    if len(patched) != len(blob):                            # pragma: no cover - splice is in-place
        raise ReskinError("the splice changed the container length -- impossible by construction")

    orth = r.get("orthogonality") or {}
    return Build(effect=effect, label=str(r.get("label", "reskin")), spec_path=str(spec_path),
                 source=source, orig=blob, patched=patched, sha_in=sha_in, sha_out=_sha(patched),
                 pmap=pmap, targets=targets, guard=guard,
                 orth_specs=(orth.get("rescore"), orth.get("retime")))


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


def _regions(blob: bytes, effect: int) -> List[Tuple[str, int, int]]:
    """The regions W4 must not touch, resolved from the container itself.

    Everything a repaint, a retime or a reframe would move: sector 0 (the resource table and the
    binary sequence stream W3's E2 edits), both id-3 program images (W3's E1), every camera block
    (W2 and W3's E3), the id-5 model image, the whole id-4 header + texel region, and every GEOM
    block found by the corpus-selective scanner (the scenery's geometry and UVs).
    """
    c = EC.parse_header(blob, strict=True)
    out: List[Tuple[str, int, int]] = [("sector 0 (resource table + the sequence stream)", 0, 0x800)]
    mp = KC.creature_package(blob)
    for ch in c.chunks:
        tag = chunk_tag(ch)
        for r in ch.resources:
            if r.id == 3:
                out.append(("%s id-3 effect program image" % tag, r.offset, r.offset + r.nbytes))
            elif r.id == 5:
                out.append(("%s id-5 SUMMON_MODEL image" % tag, r.offset, r.offset + r.nbytes))
            elif r.id == 4 and mp is not None:
                out.append(("%s id-4 header + all %d texel pages" % (tag, mp.part_count),
                            r.offset, mp.tex_file_offset + mp.tex_bytes))
                out.append(("%s id-4 sector pad past the CLUT strip" % tag,
                            mp.tex_file_offset + mp.tex_bytes + mp.clut_bytes, r.offset + r.nbytes))
    ex = W.extract_shots(blob, "ef%03d" % effect)
    for s in ex.shots:
        out.append(("camera block slot %d idx %d" % (s.slot, s.index), s.lo, s.hi))
    for g in EC.scan_geom(blob):
        try:
            end = g.end
        except Exception:                                    # pragma: no cover - unresolved pool
            end = g.base + 0x10
        out.append(("GEOM block @%#x (geometry + UVs)" % g.base, g.base, end))
    return out


#: the sibling specs ``_orthogonality`` rebuilds when a spec does not name its own.  They are
#: DEFAULTS, not laws: rebuilding *Bahamut's* camera and clocks proves nothing about a reskin of
#: ef211, so a sibling that targets another effect is SKIPPED with the reason printed (D10).
DEFAULT_ORTH_SPECS = {"rescore": "bahamut_rescore.toml", "retime": "bahamut_retime.toml"}


def _sibling_effect(path: str, table: str) -> Optional[int]:
    """Which effect a sibling W2/W3 spec targets, without building it."""
    try:
        with open(path, "rb") as fh:
            doc = _toml.load(fh)
        return int((doc.get(table) or {})["effect"])
    except Exception:                                        # pragma: no cover - malformed sibling
        return None


def _orthogonality(b: Build, mine: set) -> List[Gate]:
    """Rebuild W2 and W3 from their OWN specs and intersect their edits with this rung's.

    This is the proof, not the assertion: if the three rungs' changed-offset sets are pairwise
    disjoint then all three can ship in one container, and this rung provably moved no camera, no
    clock and no program byte.

    D10 -- the spec chooses its own siblings::

        [reskin.orthogonality]
        rescore = "phoenix_rescore.toml"
        retime  = "phoenix_retime.toml"

    and a sibling whose own ``effect`` differs from this build's is SKIPPED with that stated, rather
    than silently "proving" disjointness against a different container's edits.
    """
    out: List[Gate] = []
    want = {"rescore": b.orth_specs[0] or DEFAULT_ORTH_SPECS["rescore"],
            "retime": b.orth_specs[1] or DEFAULT_ORTH_SPECS["retime"]}
    declared = {"rescore": b.orth_specs[0] is not None, "retime": b.orth_specs[1] is not None}

    for table, title in (("rescore", "W2's rescore edits are disjoint from this reskin's"),
                         ("retime", "W3's retime edits are disjoint from this reskin's")):
        path = want[table] if os.path.isabs(want[table]) else os.path.join(_HERE, want[table])
        if not os.path.isfile(path):
            out.append(Gate(not declared[table], title,
                            "SKIPPED: no %s spec at %s%s" % (table, path,
                                                             "" if not declared[table] else
                                                             " -- but the spec NAMED it")))
            continue
        ef = _sibling_effect(path, table)
        if ef != b.effect:
            out.append(Gate(True, title,
                            "SKIPPED: %s targets ef%s, this reskin targets ef%03d -- rebuilding "
                            "another effect's edits would prove nothing about this one"
                            % (os.path.basename(path), "%03d" % ef if ef is not None else "?",
                               b.effect)))
            continue
        try:
            if table == "rescore":
                import rescore as _R
                b2 = _R.build_patched(_R.load_spec(path), os.path.basename(path))
                d = {i for i in range(len(b2.orig)) if b2.orig[i] != b2.patched[i]}
                detail = ("W2 changes %d bytes (the camera Code at %s); intersection %d"
                          % (len(d), ", ".join("%#x" % o for o in sorted(d)), len(d & mine)))
            else:
                import retime as _RT
                b3 = _RT.build_containers(_RT.load_spec(path), os.path.basename(path))
                d3 = {i for i in range(len(b3.orig)) if b3.orig[i] != b3.aligned[i]}
                dm = {i for i in range(len(b3.orig)) if b3.orig[i] != b3.misretime[i]}
                d = d3 | dm
                detail = ("W3 aligned changes %d bytes spanning %#x..%#x, mis-retime %d; "
                          "intersection with this reskin %d"
                          % (len(d3), min(d3), max(d3), len(dm), len(d & mine)))
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
    # RULE 3's instrument.  It counts the clip that can ACTUALLY happen -- a knob asking for
    # `s * sat` or `v * val` outside [0,1], which flattens that entry onto the ceiling -- and not the
    # channel clamp, which `_clamp01` makes structurally unreachable (see CLIP_CHANNEL).  The census
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
                            + ".  A3 section 3.3: pull `value`/`saturation` back on that target, or "
                              "accept it deliberately by raising BLOWOUT_FRACTION.")),
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
    mp_s, mp_p = KC.creature_package(b.orig), KC.creature_package(b.patched)
    if mp_s is None or mp_p is None:
        # D9: 348 of the 372 containers have no id-4 at all.  A scenery-only reskin of one of them
        # is a legitimate build, and a gate that cannot run must SAY SO rather than crash or pass.
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

    # ---- (4) orthogonality with W2 / W3, proved by rebuilding them
    orth = _orthogonality(b, mine)

    # ---- (5) quality: contrast + the honest invariance report
    qual: List[Gate] = []
    worst = sorted(b.enabled, key=lambda t: t.result.luma_rho)[:3]
    lo_rho = min((t.result.luma_rho for t in b.enabled), default=1.0)
    qual.append(Gate(lo_rho >= 0.90, "relative luminance ordering survives inside every palette",
                     "min Spearman rho %.4f (%s)" % (lo_rho, ", ".join(
                         "%s %.3f" % (t.name, t.result.luma_rho) for t in worst))))
    # The 5-bit re-quantisation merges entries -- unavoidable, and mostly among near-black darks a
    # saturation scale pulls together, which is invisible.  The FLOOR is what matters: a palette that
    # lost 40% of its distinct colours has genuinely banded, and the previews would show it.  The
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
                     "rotation and a saturation scale; only a channel-mix (lever #2's vocabulary) "
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

    STOCK-DERIVED ART -- SCRATCH ONLY.  ``_refuse_repo_path`` guards the destination for the same
    reason ``summons/export.py``'s ``assert_local_only`` guards a decoded ``.glb``.
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
        sheet = _label(sheet, "CREATURE -- 6 pages through their own CLUTs.  LEFT stock, RIGHT reskin.")
        p = out / "creature-sheet.png"
        sheet.save(p)
        written.append(str(p))

    # --- the scenery: the 8bpp columns the `so` bindings resolve (D5 (iii) / D6), no table
    for t in b.enabled:
        if t.pal.slot < 0 or t.pal.entries != 256:
            continue
        rects = preview_source(b.orig, t.pal, attrib)
        if not rects:
            continue
        px = b"".join(b.orig[r.off:r.off + r.nbytes] for r in rects)
        w = rects[0].texel_size(8)[0]
        h = sum(r.texel_size(8)[1] for r in rects)
        if w <= 0 or h <= 0 or len(px) < w * h:              # pragma: no cover - malformed rect
            continue
        pair(t.pal.alias or t.name, px, w, h, t.result, scale=2)

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


def stage(b: Build, root=None, game_root=None, allow_install: bool = False,
          previews: bool = True) -> dict:
    """Write the patched container, the previews and the two ``--root``-aware live scripts.

    STAGE by default, exactly as W2/W3: ``_refuse_repo_path`` always, ``_refuse_install_path``
    unless ``--live``.  The generated scripts are stdlib-only and take ``--root``, so a sandbox test
    passes a temp folder INSTEAD of editing a path literal -- the W3 verifier incident rule.

    D11: ``root`` defaults to :func:`staging_root` -- ef227 keeps W4's cast-proven layout, every
    other effect gets ``reskin-w5\\ef%03d``.  W4 had ONE root, so two effects staged in one session
    silently overwrote each other's container, previews, manifest and revert script.
    """
    root = Path(R._refuse_repo_path(root or staging_root(b.effect)))
    if not allow_install:
        R._refuse_install_path(root, game_root)
    ledger = R._Ledger(root / "backups")
    rel = _rel_container(b.effect)
    dest = root.joinpath("mod", *rel.split("/"))
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

    manifest = {
        "spec": b.spec_path, "effect": b.effect, "label": b.label,
        "stock_sha256": b.sha_in, "patched_sha256": sha,
        "container": str(dest), "scripts": scripts, "previews": preview_files,
        "changed_bytes": len(b.check.changed) if b.check else None,
        "per_target_bytes": b.check.per_target if b.check else None,
        "staging_root": str(root),
        "transforms": {t.name: {"hue_rotate": t.t.hue, "saturation": t.t.sat, "value": t.t.val,
                                "enabled": t.enabled, "offset": t.pal.off,
                                "entries": t.pal.entries, "vram": list(t.pal.vram),
                                "hue_to": t.t.hue_to, "derived_name": t.pal.name}
                       for t in b.targets},
    }
    from ff9mapkit import fsutil
    fsutil.atomic_write_text(root / "build_manifest.json",
                             json.dumps(manifest, indent=2), encoding="utf-8", newline="\n")
    manifest["staged_files"] = len(ledger.files)
    return manifest


def _write_script(path: Path, template: str, plan: dict) -> Path:
    from ff9mapkit import fsutil
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
"""Auto-generated LIVE deploy for the TIER W4 summon reskin -- stdlib only, no ff9mapkit import.

    py deploy_reskin.py [--root <mod folder>]

Copies the staged, recoloured ef### container into a mod folder, taking a FIRST-DEPLOY SNAPSHOT of
whatever that folder held beforehand.  ``--root`` defaults to the live FF9CustomMap; pass a temp
folder to rehearse.  The snapshot is per-root and is written once and never overwritten, so a
re-deploy still reverts all the way back to the pre-W4 state.  Idempotent.
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
            print("FAIL: %s sha256 %s != the build's %s -- re-run `reskin.py build`."
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
                backup = snap_dir / ("%s.pre-w4" % dest.name)
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
"""Auto-generated revert for the TIER W4 summon reskin -- stdlib only, no ff9mapkit import.

    py revert_summon_reskin_<effect>.py [--root <mod folder>]

Restores whatever the mod folder held before the FIRST W4 deploy to that same root (currently W2's
camera override), or deletes the file if W4 created it.  Idempotent -- run it twice and it restores
the same bytes twice and reports the same verdict.
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
    print("mod root             : %s" % root)
    print("tree manifest pre-W4 : %s  (%d files)" % (snap["pre_manifest_hash"],
                                                     len(snap["pre_manifest"])))
    print("tree manifest now    : %s  (%d files)" % (manifest_hash(after), len(after)))
    print("verdict              : %s" % ("EXACT RESTORE" if same else "DRIFT -- see the two hashes"))
    print()
    print("the snapshot is KEPT so a re-deploy still reverts to the true pre-W4 state; delete")
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
    L += ["", "  THE TEXANIM GATE"]
    if ta is None or not ta.present:
        L.append("    no id-4 creature package -- scenery scope only (D9)")
    elif not ta.armed:
        L.append("    region is EMPTY (firstBlock == motionOffsets[0]) -- creature scope is open")
    else:
        L.append("    ARMED: %d bytes at %#x..%#x -- creature scope REFUSED outright, scenery scope "
                 "needs `acknowledge_texanim = true`" % (ta.nbytes, ta.lo, ta.hi))
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


# ============================================================ (8) THE SCAFFOLD  (D7)
def _toml_num(v: float) -> str:
    return ("%.1f" % v) if float(v).is_integer() else ("%g" % v)


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
    so a scaffold builds clean out of the box and every refusal this rung added has to be answered
    deliberately rather than defaulted away.
    """
    if blob is None:
        blob, source = R.read_stock_effect(effect, game)
    pmap = palette_map(blob, effect=effect)
    if not pmap.palettes:
        # 3 of the 372 corpus containers (ef252, ef253, ef302) declare an id-0 with an inline rect
        # and ZERO CLUT words -- no palette, no creature, nothing lever #1 can address.  Emitting a
        # target-less toml would produce a file that cannot load; say so instead.
        raise ReskinError(
            "ef%03d declares NO CLUT palettes at all (%d span%s, no creature package) -- there is "
            "nothing a recolour can address on this effect.  It draws with direct-colour or "
            "untextured primitives; lever #1 has no surface here."
            % (effect, len(pmap.spans), "" if len(pmap.spans) == 1 else "s"))
    ta, attrib = pmap.texanim, pmap.attrib
    sha = _sha(blob)

    L = ["# AUTO-SCAFFOLDED by `py reskin.py scaffold --ef %d`.  Every number below is DERIVED from"
         % effect,
         "# the container's own headers; every knob is at IDENTITY.  Two kinds of line only:",
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
    if ta is not None and ta.armed:
        L += ["",
              "# TEXANIM IS ARMED (%d bytes at %#x..%#x).  Creature targets below are REFUSED"
              % (ta.nbytes, ta.lo, ta.hi),
              "# outright and no key lifts that.  A scenery-only reskin needs the line below flipped",
              "# to true, which states: orthogonality ASSUMED, not proven (the table's format is",
              "# unread and its record is per creature PART).",
              "acknowledge_texanim = false"]
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
        if ta is not None and ta.armed:
            blocked.append("CREATURE under an armed texanim -- REFUSED outright, no key lifts it"
                           if p.slot < 0 else
                           "texanim is ARMED -- needs `acknowledge_texanim = true` at [reskin]")
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
        spec = _toml.load(fh)
    r = spec.get("reskin")
    if not isinstance(r, dict):
        raise ReskinError("%s has no [reskin] table" % path)
    for key in ("effect", "target"):
        if key not in r:
            raise ReskinError("[reskin] needs `%s`" % key)
    return spec


# ============================================================ CLI
def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("verb", choices=("plan", "build", "verify", "scaffold"))
    ap.add_argument("spec", nargs="?", default=None,
                    help="the *_reskin.toml (default: bahamut_reskin.toml); unused by `scaffold`")
    ap.add_argument("--root", default=None,
                    help="staging root (default: the per-effect SCRATCH root -- ef227 keeps W4's, "
                         "everything else gets reskin-w5/ef###; the repo and the install are refused)")
    ap.add_argument("--ef", type=int, default=None, help="scaffold: which effect to read")
    ap.add_argument("--from", dest="from_path", default=None,
                    help="scaffold: read this container file instead of the install (a corpus "
                         "ef###.bytes, for an effect the install cannot resolve)")
    ap.add_argument("--out", default=None, help="scaffold: write the toml here instead of stdout")
    ap.add_argument("--game", default=None)
    ap.add_argument("--previews", action="store_true",
                    help="plan: also render the previews (they are stock-derived, SCRATCH only)")
    ap.add_argument("--no-previews", action="store_true", help="build: skip the preview render")
    ap.add_argument("--live", action="store_true",
                    help="allow a --root INSIDE the game install. Off by default: this tool stages, "
                         "and the generated deploy script is what touches the install.")
    a = ap.parse_args(argv)

    try:
        from ff9mapkit import config
        game_root = config.find_game_path(a.game)
    except Exception:                                        # pragma: no cover
        game_root = None

    if a.verb == "scaffold":
        if a.ef is None:
            print("scaffold needs --ef N")
            return 2
        blob, src = (None, "")
        if a.from_path:
            with open(a.from_path, "rb") as fh:
                blob = fh.read()
            src = a.from_path
        text, _pmap = scaffold(a.ef, blob=blob, game=a.game, source=src)
        if a.out:
            from ff9mapkit import fsutil
            fsutil.atomic_write_text(a.out, text, encoding="utf-8", newline="\n")
            print("wrote %s (%d lines)" % (a.out, text.count("\n")))
        else:
            sys.stdout.write(text)
        return 0

    spec = load_spec(a.spec or os.path.join(_HERE, "bahamut_reskin.toml"))
    a.spec = a.spec or os.path.join(_HERE, "bahamut_reskin.toml")
    if a.root is None:
        a.root = staging_root(int(spec["reskin"]["effect"]))

    b = build(spec, a.spec, a.game)
    b.check = self_check(b)
    print("\n".join(describe(b)))
    print("\n".join(check_lines(b)))

    if a.verb == "plan":
        if a.previews:
            files = render_previews(b, Path(a.root) / "previews")
            print("\n  previews (stock-derived, SCRATCH only):")
            for f in files:
                print("    %s" % f)
        else:
            print("\nplan only -- nothing written.")
        return 0 if b.check.ok else 1

    if not b.check.ok:
        print("\nREFUSING TO STAGE -- the self-check failed (see above).")
        return 1

    if a.verb == "build":
        out = stage(b, a.root, game_root, allow_install=a.live, previews=not a.no_previews)
        print("\n  %s" % ("DEPLOYED (--live)" if a.live else "STAGED"))
        for k, v in out.items():
            if k in ("transforms", "per_target_bytes"):
                continue
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    print("    %-22s %s" % (k2, v2))
            elif isinstance(v, list):
                for v2 in v:
                    print("    %-22s %s" % (k, v2))
            else:
                print("    %-22s %s" % (k, v))
        return 0

    # verify: the staged bytes, re-checked as bytes (not as a rebuild)
    root = Path(a.root)
    mf = root / "build_manifest.json"
    if not mf.exists():
        print("\nVERIFY FAILED: no build manifest at %s" % mf)
        return 1
    man = json.loads(mf.read_text(encoding="utf-8"))
    ok = True
    p = Path(man["container"])
    if not p.exists():
        print("  VERIFY container   MISSING at %s" % p)
        ok = False
    else:
        got = p.read_bytes()
        same = got == b.patched
        ok = ok and same
        print("  VERIFY container   %d B sha %s -> %s"
              % (len(got), _sha(got)[:16], "MATCHES the rebuild" if same else "DIVERGES"))
        if man.get("patched_sha256") != _sha(got):
            print("  VERIFY manifest    sha in the manifest does not match the staged file")
            ok = False
    for name, sp in sorted((man.get("scripts") or {}).items()):
        exists = Path(sp).exists()
        ok = ok and exists
        print("  VERIFY %-11s %s" % (name, sp if exists else "MISSING: %s" % sp))
    missing = [f for f in (man.get("previews") or []) if not Path(f).exists()]
    print("  VERIFY previews    %d staged, %d missing"
          % (len(man.get("previews") or []), len(missing)))
    ok = ok and not missing
    for name, tr in sorted((man.get("transforms") or {}).items()):
        t = next((x for x in b.targets if x.name == name), None)
        if t is None or (t.t.hue, t.t.sat, t.t.val, t.enabled) != (
                tr["hue_rotate"], tr["saturation"], tr["value"], tr["enabled"]):
            print("  VERIFY transform   %s DIVERGES from the manifest" % name)
            ok = False
    print("\n  VERIFY: %s" % ("PASS" if ok and b.check.ok else "FAIL"))
    return 0 if ok and b.check.ok else 1


if __name__ == "__main__":                                   # pragma: no cover
    raise SystemExit(main())
