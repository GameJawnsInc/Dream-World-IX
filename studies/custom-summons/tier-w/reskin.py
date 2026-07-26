r"""TIER W rung 4 -- THE RESKIN: recolour ef227's whole palette set in place, stock bytes untouched.

    py reskin.py plan   bahamut_reskin.toml     # resolve every target + print the numbers, write nothing
    py reskin.py build  bahamut_reskin.toml     # stage the container + the deploy/revert scripts + previews
    py reskin.py verify bahamut_reskin.toml     # re-check what is staged, as bytes

WHAT THIS IS
------------
W2 moved the camera, W3 moved the clocks; both proved a same-length in-place splice of a stock
summon container survives every gate and lands hot.  W4 spends that posture on the one lever the
recon (``w4-recon/A1..A4``) says is cleanest: **LEVER #1, the CLUT recolour**.  Not one texel moves.
The creature's six 256-entry palettes and the effect's own scenery palettes are decoded, rotated
through HSV, re-encoded to BGR555 and spliced back at the same offsets.

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
5. every changed byte must land inside a **named, derived palette** inside one of the four named
   spans; anything else is UNEXPLAINED and refuses the stage.

ORTHOGONALITY -- proved, not asserted
--------------------------------------
The self-check rebuilds **W2's rescore and W3's retime from their own specs** and intersects their
changed-offset sets with this rung's.  Empty intersection is the proof that W2/W3/W4 can ship in one
container.  On top of that it gates whole regions byte-identical: sector 0 (the resource table + the
sequence stream), both id-3 program images, every camera block, every GEOM block, the id-5 model
image, and the whole id-4 header+texel region -- i.e. the geometry and UVs a repaint would touch.

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

#: default staging root -- SCRATCH, never the repo, never the live game folder (build stages only)
SCRATCH_ROOT = os.environ.get("FF9_RESKIN_SCRATCH",
                              r"C:\gd\SCRATCH\summon-format\reskin-w4")

#: the on-disc override lane, shared with W2/W3 (extensionless: LoadFromDisc reads the raw path)
MOD_SUBPATH = R.MOD_SUBPATH                                  # "FF9_Data/SpecialEffects"

#: the whole-set ceiling A2's edit menu (c) states: 3,072 creature + 3,072 + 1,024 + 1,024 scenery
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

#: A2's attribution, keyed by the VRAM cell the CONTAINER'S OWN HEADER declares.  These are names
#: hung on derived coordinates -- if a coordinate ever stops existing, resolution refuses.  The
#: ``shared`` flag is A2 guard-rail 3: a palette read by more than one set piece may only be named
#: as its GROUP, never as one piece, so nobody recolours the sky gradient thinking it is the water.
ATTRIBUTION: Dict[Tuple[int, int], Tuple[str, bool, str]] = {
    (0, 244):   ("scenery.water_and_sky_gradient", True,
                 "SHARED 4bpp -- the water/ice sheet AND the sky gradient shell read this one"),
    (192, 244): ("scenery.cloud_bands", True,
                 "SHARED 4bpp -- cloud bands A, B and C read this one"),
    (0, 245):   ("scenery.sky_dome", False, "the sky dome, the largest scenery mesh"),
    (0, 246):   ("scenery.energy_rings", False, "the impact / energy rings"),
    (0, 248):   ("scenery.cloud_sheet", False, "the cloud sheet"),
    (0, 249):   ("scenery.aerial_ground", False, "the aerial ground plane (satellite-view terrain)"),
    (0, 251):   ("scenery.fire_column", False, "the fire column"),
}

#: the attributed 8bpp scenery pages, for the PREVIEW only -- (name -> the file runs that hold the
#: texels a palette actually colours).  Derived from the id-0 page rects + the id-9 slot map, both
#: re-read this rung; a preview that cannot resolve its page falls back to the swatch strip alone.
PREVIEW_PAGE: Dict[str, Tuple[str, int]] = {
    "scenery.sky_dome":       ("c0", 704),
    "scenery.energy_rings":   ("c0", 448),
    "scenery.aerial_ground":  ("c0", 576),
    "scenery.cloud_sheet":    ("id9", 832),
    "scenery.fire_column":    ("c1", 832),
}
#: id-9's six enabled slots, from A1 section 4 / A2 section 2.3 (info = 51 -> slots 0,1,2,3,6,7).
#: Only the (832, *) pair is a preview source here.
ID9_SLOT_FILE = {(832, 256): 0x03A000, (832, 384): 0x03E000}


class ReskinError(RuntimeError):
    pass


def _u16(b: bytes, o: int) -> int:
    return struct.unpack_from("<H", b, o)[0]


def _s32(b: bytes, o: int) -> int:
    return struct.unpack_from("<i", b, o)[0]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ============================================================ (1) THE PALETTE MAP -- all derived
@dataclass(frozen=True)
class Span:
    """One of A2's named byte spans -- the outer envelope every changed byte must land inside."""
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

    @property
    def nbytes(self) -> int:
        return self.entries * 2


@dataclass
class PaletteMap:
    spans: List[Span]
    palettes: List[Palette]

    def by_name(self, name: str) -> Palette:
        for p in self.palettes:
            if p.name == name:
                return p
        raise ReskinError("no palette named %r -- the container declares %s"
                          % (name, ", ".join(sorted(p.name for p in self.palettes))))

    def span(self, name: str) -> Span:
        for s in self.spans:
            if s.name == name:
                return s
        raise ReskinError("no span named %r" % name)


def clut_word_xy(word: int) -> Tuple[int, int]:
    """A PSX CLUT word -> its VRAM cell ``(x_entries, y_line)``.  ``x = (w & 0x3F) * 16``,
    ``y = w >> 6`` -- the same decode ``summons.texture.clut_row``/``clut_entry0`` perform against
    the creature strip's own base, written here without the strip bias because the scenery band
    sits at x = 0."""
    return ((word & 0x3F) * 16, word >> 6)


def id0_palettes(blob: bytes, chunk, chunk_tag: str) -> Tuple[List[Span], List[Palette]]:
    """Every palette one chunk's **id-0 payload header** declares, resolved to file bytes.

    The header (A1 section 3.1 / A2 section 2.2, both re-read against these bytes this rung)::

        P+0x00 s32 pageBlockRel   -> { s32 pixelDataRel, s32 nPageRects, Rect[nPageRects] }
        P+0x04 s32 inlineRel      -> nInline x { Rect, u16 pixels[w*h] }   -- the CLUT images
        P+0x08 s32 nInline
        P+0x0c u16 nClut4         -- 16-entry palettes that follow
        P+0x0e u16 nClut8         -- 256-entry palettes that follow
        P+0x10 u16 clutWord[nClut4 + nClut8]

    The self-check the derivation rests on is exact and is asserted here: the inline rect stream
    must end at precisely ``P + pixelDataRel``.  If it does not, the header is not what we think it
    is and nothing is resolved.
    """
    res = [r for r in chunk.resources if r.id == 0]
    if len(res) != 1:
        raise ReskinError("%s: expected exactly one id-0 resource, found %d" % (chunk_tag, len(res)))
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
                              (chunk_tag, k, x))
        for r in range(h):
            rows[y + r] = (data + r * w * 2, w, k)
        spans.append(Span("%s_clut_band%d" % (chunk_tag, k), data, data + w * h * 2,
                          "id-0 inline rect %d: VRAM (x=%d y=%d w=%d h=%d)" % (k, x, y, w, h)))
        cur = data + w * h * 2

    pix_rel = _s32(blob, P + page_rel)
    if cur != P + pix_rel:
        raise ReskinError("%s: the inline CLUT stream ends at %#x but the header's pixelDataRel "
                          "names %#x -- the id-0 layout is not what this tool decodes"
                          % (chunk_tag, cur, P + pix_rel))

    pals: List[Palette] = []
    for i, cw in enumerate(words):
        entries = 16 if i < n4 else 256
        x, y = clut_word_xy(cw)
        if y not in rows:
            raise ReskinError("%s: CLUT word %#06x names VRAM row %d, which no inline rect uploads"
                              % (chunk_tag, cw, y))
        row_off, row_w, rect = rows[y]
        if x + entries > row_w:
            raise ReskinError("%s: CLUT word %#06x -> x=%d + %d entries overruns the %d-entry row"
                              % (chunk_tag, cw, x, entries, row_w))
        name, shared, note = ATTRIBUTION.get(
            (x, y), ("spare.%s_x%d_y%d" % (chunk_tag, x, y), False,
                     "declared by the header, attributed to no GEOM model (A2 section 3.2)"))
        pals.append(Palette(name=name, off=row_off + x * 2, entries=entries, vram=(x, y),
                            span="%s_clut_band%d" % (chunk_tag, rect),
                            bpp=4 if entries == 16 else 8, shared=shared, note=note,
                            source="%s id-0 clutWord[%d] = %#06x" % (chunk_tag, i, cw)))
    return spans, pals


def creature_palettes(blob: bytes) -> Tuple[Span, List[Palette]]:
    """The creature's six rows, off the id-4 model-package header through the kit's OWN decoder.

    ``summons.texture.texture_check`` is the shipped, corpus-proven gate (24/24 packages): it
    refuses anything that is not the ``partCount`` x 0x4000 / ``clutRows`` x 0x200 8bpp layout, so a
    creature this tool cannot address is a refusal rather than a guess.
    """
    mp = KC.creature_package(blob)
    if mp is None:
        raise ReskinError("this container has no id-4 creature package -- nothing to recolour")
    chk = KT.texture_check(blob, mp)
    if not chk["decodable"]:
        raise ReskinError("the creature's texture block is not the 8bpp layout:\n  - "
                          + "\n  - ".join(chk["reasons"]))
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
                           % (p.clut, p.clut_row))
            for p in chk["parts"]]
    return span, pals


def palette_map(blob: bytes) -> PaletteMap:
    """Every palette ef227 declares, from the container's own headers.  Nothing tabulated."""
    c = EC.parse_header(blob, strict=True)
    span_c, pals = creature_palettes(blob)
    spans = [span_c]
    for ch in c.chunks:
        s, p = id0_palettes(blob, ch, "c%d" % ch.chunk_index)
        spans += s
        pals += p
    names = [p.name for p in pals]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        raise ReskinError("two palettes resolved to the same name: %s" % ", ".join(dupes))
    return PaletteMap(spans, pals)


def creature_pages(blob: bytes) -> Dict[str, int]:
    """``{palette name: page file offset}`` for the creature -- the preview's exact 1:1 page map."""
    mp = KC.creature_package(blob)
    chk = KT.texture_check(blob, mp)
    return {"creature.part%d" % p.index: p.page_offset for p in chk["parts"]}


def scenery_pages(blob: bytes) -> Dict[Tuple[str, int], Tuple[int, int]]:
    """``{(chunk tag, vram x): (file offset, nbytes)}`` for the streamed 64x256 page rects.

    Derived, again, from the id-0 page block: ``pixelDataRel`` is the stream base and the rect list
    gives the column order.  Each ``h == 256`` rect is TWO stacked 64x128 uploads (the streamer's
    own rule, A1 section 3.2), i.e. 0x8000 contiguous bytes = a 128x256 texel column at 8bpp.
    """
    c = EC.parse_header(blob, strict=True)
    out: Dict[Tuple[str, int], Tuple[int, int]] = {}
    for ch in c.chunks:
        tag = "c%d" % ch.chunk_index
        res = [r for r in ch.resources if r.id == 0][0]
        P = res.offset
        pb = P + _s32(blob, P)
        base = P + _s32(blob, pb)
        n = _s32(blob, pb + 4)
        cur = base
        for k in range(n):
            o = pb + 8 + 8 * k
            x, y, w, h = _u16(blob, o), _u16(blob, o + 2), _u16(blob, o + 4), _u16(blob, o + 6)
            out[(tag, x)] = (cur, w * h * 2)
            cur += w * h * 2
    return out


# ============================================================ (2) THE TRANSFORM
@dataclass(frozen=True)
class Transform:
    """One target's recolour.  ``hue`` is degrees on the wheel; ``sat``/``val`` are scales."""
    hue: float = 0.0
    sat: float = 1.0
    val: float = 1.0

    @property
    def identity(self) -> bool:
        return (self.hue % 360.0 == 0.0) and self.sat == 1.0 and self.val == 1.0

    def __str__(self) -> str:
        return "hue %+.1f deg  sat x%.2f  val x%.2f" % (self.hue, self.sat, self.val)


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
        zero_positions_held=all((w == 0) == (n == 0) for w, n in zip(sw, nw)))


# ============================================================ (3) THE BUILD
@dataclass
class Target:
    name: str
    enabled: bool
    t: Transform
    note: str
    pal: Palette
    result: Optional[PaletteResult] = None


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

    @property
    def enabled(self) -> List[Target]:
        return [t for t in self.targets if t.enabled]


def _transform_of(d: dict, defaults: dict, where: str) -> Transform:
    def num(key, dflt):
        v = d.get(key, defaults.get(key, dflt))
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise ReskinError("%s: `%s` must be a number, got %r" % (where, key, v))
        return float(v)
    t = Transform(hue=num("hue_rotate", 0.0), sat=num("saturation", 1.0), val=num("value", 1.0))
    if t.sat < 0 or t.val < 0:
        raise ReskinError("%s: saturation/value scales must be >= 0 (got %s)" % (where, t))
    if t.sat > 4 or t.val > 4:
        raise ReskinError("%s: a scale above 4x is refused -- 5-bit channels clip long before "
                          "that and A3's colorIntensity multiplies 1.5x/2x on top (got %s)"
                          % (where, t))
    return t


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
    sha_in = R.drift_guard(effect, blob, r.get("expect_sha256"))

    pmap = palette_map(blob)

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
        if "expect_entries" in d and int(d["expect_entries"]) != pal.entries:
            raise ReskinError("target %s: the spec guards %d entries, the header declares %d"
                              % (name, int(d["expect_entries"]), pal.entries))
        if "expect_vram" in d and tuple(d["expect_vram"]) != pal.vram:
            raise ReskinError("target %s: the spec guards VRAM %s, the header declares %s"
                              % (name, tuple(d["expect_vram"]), pal.vram))
        if "expect_offset" in d and int(d["expect_offset"]) != pal.off:
            raise ReskinError("target %s: the spec guards file %#x, the derivation says %#x"
                              % (name, int(d["expect_offset"]), pal.off))
        if pal.shared and not d.get("acknowledge_shared"):
            raise ReskinError(
                "target %s is a SHARED palette (%s).  A2 guard-rail 3: it may only be recoloured as "
                "the GROUP it is, so the spec must say `acknowledge_shared = true` to show the "
                "author knows more than one set piece moves." % (name, pal.note))
        targets.append(Target(name=name, enabled=bool(d.get("enabled", True)),
                              t=_transform_of(d, defaults, "target %s" % name),
                              note=str(d.get("note", "")), pal=pal))

    out = bytearray(blob)
    for t in targets:
        if not t.enabled:
            continue
        t.result = apply_palette(blob, t.pal, t.t)
        out[t.pal.off:t.pal.off + t.pal.nbytes] = t.result.new
    patched = bytes(out)
    if len(patched) != len(blob):                            # pragma: no cover - splice is in-place
        raise ReskinError("the splice changed the container length -- impossible by construction")

    return Build(effect=effect, label=str(r.get("label", "reskin")), spec_path=str(spec_path),
                 source=source, orig=blob, patched=patched, sha_in=sha_in, sha_out=_sha(patched),
                 pmap=pmap, targets=targets)


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
        tag = "c%d" % ch.chunk_index
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


def _orthogonality(b: Build, mine: set) -> List[Gate]:
    """Rebuild W2 and W3 from their OWN specs and intersect their edits with this rung's.

    This is the proof, not the assertion: if the three rungs' changed-offset sets are pairwise
    disjoint then all three can ship in one container, and W4 provably moved no camera, no clock
    and no program byte.
    """
    out: List[Gate] = []
    try:
        import rescore as _R
        s2 = _R.load_spec(os.path.join(_HERE, "bahamut_rescore.toml"))
        b2 = _R.build_patched(s2, "bahamut_rescore.toml")
        d2 = {i for i in range(len(b2.orig)) if b2.orig[i] != b2.patched[i]}
        out.append(Gate(not (d2 & mine), "W2's rescore edits are disjoint from W4's",
                        "W2 changes %d bytes (the camera Code at %s); intersection %d"
                        % (len(d2), ", ".join("%#x" % o for o in sorted(d2)), len(d2 & mine))))
    except Exception as e:                                   # pragma: no cover - spec-dependent
        out.append(Gate(False, "W2's rescore rebuilt for the disjointness proof", "FAILED: %s" % e))
    try:
        import retime as _RT
        s3 = _RT.load_spec(os.path.join(_HERE, "bahamut_retime.toml"))
        b3 = _RT.build_containers(s3, "bahamut_retime.toml")
        d3 = {i for i in range(len(b3.orig)) if b3.orig[i] != b3.aligned[i]}
        dm = {i for i in range(len(b3.orig)) if b3.orig[i] != b3.misretime[i]}
        out.append(Gate(not ((d3 | dm) & mine), "W3's retime edits are disjoint from W4's",
                        "W3 aligned changes %d bytes spanning %#x..%#x, mis-retime %d; "
                        "intersection with W4 %d"
                        % (len(d3), min(d3), max(d3), len(dm), len((d3 | dm) & mine))))
    except Exception as e:                                   # pragma: no cover - spec-dependent
        out.append(Gate(False, "W3's retime rebuilt for the disjointness proof", "FAILED: %s" % e))
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
        Gate(len(changed) <= WHOLE_SET_CEILING, "under A2's whole-set ceiling",
             "%d changed of the %d-byte four-span envelope (%.2f%% of the %d-byte container)"
             % (len(changed), WHOLE_SET_CEILING, 100.0 * len(changed) / len(b.orig), len(b.orig))),
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
    tex_same = (b.orig[mp_s.tex_file_offset:mp_s.tex_file_offset + mp_s.tex_bytes]
                == b.patched[mp_p.tex_file_offset:mp_p.tex_file_offset + mp_p.tex_bytes])
    regions.append(Gate(tex_same and KT.texture_check(b.patched, mp_p)["decodable"],
                        "the id-4 TEXEL region is untouched and still decodes",
                        "%d B of pages at %#x, bit-identical; texture_check passes on the patched "
                        "container" % (mp_s.tex_bytes, mp_s.tex_file_offset)))

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
    spages = scenery_pages(b.orig)

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

    # --- the scenery: the attributed 8bpp columns, where they resolve
    for t in b.enabled:
        src = PREVIEW_PAGE.get(t.name)
        if src is None or t.pal.entries != 256:
            continue
        tag, x = src
        if tag == "id9":
            px = (b.orig[ID9_SLOT_FILE[(x, 256)]:ID9_SLOT_FILE[(x, 256)] + 0x4000]
                  + b.orig[ID9_SLOT_FILE[(x, 384)]:ID9_SLOT_FILE[(x, 384)] + 0x4000])
        else:
            off, n = spages[(tag, x)]
            px = b.orig[off:off + n]
        pair(t.name, px, 128, 256, t.result, scale=2)

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
    """
    root = Path(R._refuse_repo_path(root or SCRATCH_ROOT))
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
        "note": "this artifact is STOCK + the W4 reskin; it REPLACES whatever container the mod "
                "folder holds (currently W2's camera override). The first-deploy snapshot restores "
                "it byte-for-byte.",
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
        "transforms": {t.name: {"hue_rotate": t.t.hue, "saturation": t.t.sat, "value": t.t.val,
                                "enabled": t.enabled, "offset": t.pal.off,
                                "entries": t.pal.entries, "vram": list(t.pal.vram)}
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

    py revert_summon_reskin_227.py [--root <mod folder>]

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
         "  stock sha256   : %s  (drift guard %s)"
         % (b.sha_in, "REGISTERED" if b.effect in R.EXPECTED_STOCK_SHA else "none -- unguarded"),
         "  reskin sha256  : %s" % b.sha_out,
         "  container      : %d B in, %d B out (same length -- every palette is spliced in place)"
         % (len(b.orig), len(b.patched)),
         "",
         "  THE DERIVED SPANS (from the container's own headers, not from a table)"]
    for s in b.pmap.spans:
        L.append("    %-22s %#08x..%#08x  %5d B   %s" % (s.name, s.lo, s.hi, s.size, s.source))
    L += ["", "  THE DERIVED PALETTES (%d declared)" % len(b.pmap.palettes)]
    for p in b.pmap.palettes:
        t = next((x for x in b.targets if x.name == p.name), None)
        state = "OFF" if t is None else ("ON " if t.enabled else "off")
        L.append("    [%s] %-34s %#08x  %3d entries %dbpp  VRAM %-10s %s"
                 % (state, p.name, p.off, p.entries, p.bpp, "(%d,%d)" % p.vram,
                    "SHARED" if p.shared else ""))
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
        L.append("         mean H %5.1f -> %5.1f   S %.2f -> %.2f   V %.2f -> %.2f   %s"
                 % (r.hue_before, r.hue_after, r.sat_before, r.sat_after,
                    r.val_before, r.val_after, t.note))
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
    L.append("    TOTAL %d bytes of %d (%.3f%%), ceiling %d"
             % (len(c.changed), len(b.orig), 100.0 * len(c.changed) / len(b.orig),
                WHOLE_SET_CEILING))
    return L


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
    ap.add_argument("verb", choices=("plan", "build", "verify"))
    ap.add_argument("spec", nargs="?", default=os.path.join(_HERE, "bahamut_reskin.toml"))
    ap.add_argument("--root", default=SCRATCH_ROOT,
                    help="staging root (default: SCRATCH; the repo and the install are refused)")
    ap.add_argument("--game", default=None)
    ap.add_argument("--previews", action="store_true",
                    help="plan: also render the previews (they are stock-derived, SCRATCH only)")
    ap.add_argument("--no-previews", action="store_true", help="build: skip the preview render")
    ap.add_argument("--live", action="store_true",
                    help="allow a --root INSIDE the game install. Off by default: W4 stages, and "
                         "the generated deploy script is what touches the install.")
    a = ap.parse_args(argv)

    spec = load_spec(a.spec)
    try:
        from ff9mapkit import config
        game_root = config.find_game_path(a.game)
    except Exception:                                        # pragma: no cover
        game_root = None

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
