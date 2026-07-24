"""Offline decode of a summon creature's TEXTURE PAGES + CLUTs -- the W3 rung of the transplant ladder
(FORMAT.md section 4.3), the layer ``summons.build`` deliberately left out of scope until now.

A creature's pixels live in the **id-4** resource, ahead of the model image in the same 0x50000 arena:

    id4.offset + texOffset                        page 0 .. page partCount-1, 0x4000 bytes each
    id4.offset + texOffset + texBytes             the CLUT strip, clutRows x 0x200 bytes

The id-4 handler (``fn 0x3de37`` @0x3e272-0x3e34b, transcribed in ``D3-container-validate.md`` section 5.1)
DMAs the CLUT strip to VRAM rect ``{x=0x100, y=0xe6, w=0x100, h=clutRows}`` and then each page in turn to
``{x=(tpage & 0x0f)*64, y=((tpage & 0x10) << 4) + vOffset, w=64, h=128}`` -- 64 VRAM *halfwords* wide.
Every one of the 24 stock creature packages declares ``tpage`` colour mode **1 = 8bpp** (bits 7-8), so a
page's 64 halfwords are **128 texels** wide and its ``0x4000`` bytes are exactly a **128x128 8-bit indexed
image**; its palette is one full **256-entry** row of the strip (``0x200`` bytes), selected by the part's
own CLUT word. Corpus-verified on all 24 (``ef227`` = 6 parts / 6 clut rows / tp=1 / u,v <= 127).

THE V-OFFSET PRE-BAKE (FORMAT.md 2.3, M4 section 5.4) -- the one trap for an offline reader. At load the
engine walks the four textured buckets ONCE and does ``v_byte += partTable[part].v`` (the header's per-part
V-offset; the u term is 0 for summon models, ``Hi_RegisterSummonModel`` @0x16005). So:

    baked_v = raw_v + v_offset                    what live memory holds
    row     = baked_v - v_offset                  the block was UPLOADED at page line v_offset

i.e. the bake and the block's own VRAM placement cancel, and a **pre-bake** ``raw_v`` indexes the decoded
128-row page image directly. :func:`page_row` performs both steps explicitly rather than relying on the
cancellation, so a package whose block placement ever stops matching its V-offset is caught by the
bounds check instead of silently sampling the wrong rows.

Provenance: committable CODE. It reads a caller-supplied local blob (a stock ``ef###.bytes`` from the
user's OWN install), embeds no game bytes and writes nothing -- the only writer is ``summons/export.py``,
behind :func:`~ff9mapkit.summons.export.assert_local_only`. Decoded pixels are Square-Enix content and may
only reach a LOCAL-ONLY output.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

__all__ = [
    "TextureError", "PAGE_W", "PAGE_H", "PAGE_BYTES", "PALETTE_LEN", "CLUT_ROW_BYTES",
    "CLUT_STRIP_X", "CLUT_STRIP_Y", "CLUT_STRIP_W", "MODE_4BPP", "MODE_8BPP", "MODE_16BPP",
    "PartTexture", "tpage_mode", "tpage_origin", "clut_row", "clut_entry0", "bgr555_rgba",
    "page_row", "uv_texcoord", "part_textures", "texture_check", "read_palette",
    "decode_page_rgba", "decode_pages",
]

# --- the 8bpp page geometry (one 0x4000 block == 64 VRAM halfwords x 128 lines == 128x128 texels) ---------
PAGE_W = 128
PAGE_H = 128
PAGE_BYTES = 0x4000                 # == PAGE_W * PAGE_H at 8bpp; the header's `texBytes == partCount*0x4000`
PALETTE_LEN = 256                   # an 8bpp CLUT is 256 entries
CLUT_ROW_BYTES = 0x200              # == CLUT_STRIP_W * 2; the header's `clutBytes == clutRows*0x200`
CLUT_STRIP_X = 0x100                # the strip's VRAM x (halfwords)  -- rect @0x3e286
CLUT_STRIP_Y = 0xE6                 # the strip's VRAM y (lines)      -- rect @0x3e286
CLUT_STRIP_W = 0x100                # the strip's width in entries    -- rect @0x3e286
MODE_4BPP, MODE_8BPP, MODE_16BPP = 0, 1, 2


class TextureError(RuntimeError):
    """Raised when a package's texture block does not satisfy the decode laws (see :func:`texture_check`)."""


# --------------------------------------------------------------------------- TPAGE / CLUT word arithmetic
def tpage_mode(tpage: int) -> int:
    """PSX TPAGE colour mode, bits 7-8: 0 = 4bpp, 1 = 8bpp, 2 = 16bpp direct. All 24 stock creatures = 1."""
    return (tpage >> 7) & 3


def tpage_origin(tpage: int, v_offset: int = 0) -> Tuple[int, int]:
    """The uploaded block's VRAM origin ``(x_halfwords, y_lines)`` -- the id-4 handler's own rect math
    (@0x3e302-0x3e328), the same expression as ``container.vram_rect``."""
    return ((tpage & 0x0F) * 64, ((tpage & 0x10) << 4) + v_offset)


def clut_row(clut: int) -> int:
    """Which row of the CLUT strip a part's CLUT word selects (``y = clut >> 6``, strip base ``0xe6``)."""
    return (clut >> 6) - CLUT_STRIP_Y


def clut_entry0(clut: int) -> int:
    """The first palette ENTRY within that row (``x = (clut & 0x3f) * 16``, strip base ``0x100``). 0 on all
    24 stock creatures -- each 8bpp part owns a whole 256-entry row."""
    return (clut & 0x3F) * 16 - CLUT_STRIP_X


def bgr555_rgba(word: int) -> Tuple[int, int, int, int]:
    """One 16bpp PSX texel/CLUT entry -> ``(r, g, b, a)`` 0..255.

    Layout is BGR555 + STP: bits 0-4 R, 5-9 G, 10-14 B, bit 15 = the semi-transparency flag. PSX's own
    transparency rule is by VALUE, not by index: **``0x0000`` (black, STP clear) is the transparent texel**
    -- and that is exactly what stock uses (entry 0 of every one of ef227's six rows is ``0x0000`` and no
    other entry in any row is). STP itself only selects the blend equation for a primitive that is ALSO
    flagged semi-transparent (flag bit0); Bahamut's 2416 faces all carry ``flag == 0``, so STP is inert and
    every non-zero entry is opaque here. Alpha is therefore binary -- which is what the emitted material's
    ``alphaMode: MASK`` expects."""
    if word == 0:
        return (0, 0, 0, 0)
    r = (word & 0x1F) * 255 // 31
    g = ((word >> 5) & 0x1F) * 255 // 31
    b = ((word >> 10) & 0x1F) * 255 // 31
    return (r, g, b, 255)


# --------------------------------------------------------------------------- the UV bake
def page_row(raw_v: int, v_offset: int) -> int:
    """Pre-bake ``v`` byte -> the row inside the part's own decoded page image, via BOTH steps of the
    module docstring's law (bake, then subtract the block's placement). They cancel; doing it explicitly
    keeps the law visible and lets the caller's bounds check catch a package that ever breaks it."""
    return (raw_v + v_offset) - v_offset


def uv_texcoord(word: int, v_offset: int = 0, *, page_w: int = PAGE_W,
                page_h: int = PAGE_H) -> Tuple[float, float]:
    """One UV-pool entry -> a glTF-convention ``(u, v)`` in [0,1] sampling the TEXEL CENTRE.

    The pool entry is ``u16 == (u | v<<8)`` -- an inline PSX ``(u8 u, u8 v)`` pair (M4 line 275). The
    ``+0.5`` puts the coordinate on the texel's centre rather than its boundary, so the emitted NEAREST
    sampler can never land a corner one texel off through float rounding. ``v`` runs DOWNWARD from the top
    of the page, which is also glTF's texcoord convention (origin top-left), so no flip happens here."""
    u = word & 0xFF
    v = page_row((word >> 8) & 0xFF, v_offset)
    return ((u + 0.5) / page_w, (v + 0.5) / page_h)


# --------------------------------------------------------------------------- per-part resolution
@dataclass
class PartTexture:
    """One material part's resolved texture binding: where its page and palette live in the FILE, and the
    VRAM rect the engine would upload them to."""
    index: int
    tpage: int
    clut: int
    v_offset: int
    mode: int                    # tpage_mode -- 1 (8bpp) is the only decodable one
    vram: Tuple[int, int]        # the uploaded block's VRAM (x halfwords, y lines)
    clut_row: int                # row within the CLUT strip
    clut_entry0: int             # first palette entry within that row
    page_offset: int             # absolute FILE offset of the 0x4000 page block
    clut_offset: int             # absolute FILE offset of the 256-entry palette


def part_textures(mp) -> List[PartTexture]:
    """Resolve every part of a :class:`~ff9mapkit.summons.container.ModelPackage` to its file offsets. Pure
    arithmetic on the header -- no blob read, no validation (see :func:`texture_check`)."""
    clut_base = mp.tex_file_offset + mp.tex_bytes
    out: List[PartTexture] = []
    for i in range(mp.part_count):
        tp, cl = mp.tpage[i], mp.clut[i]
        voff = mp.v_offset[i]
        row, e0 = clut_row(cl), clut_entry0(cl)
        out.append(PartTexture(
            index=i, tpage=tp, clut=cl, v_offset=voff, mode=tpage_mode(tp),
            vram=tpage_origin(tp, voff), clut_row=row, clut_entry0=e0,
            page_offset=mp.tex_file_offset + i * PAGE_BYTES,
            clut_offset=clut_base + row * CLUT_ROW_BYTES + e0 * 2))
    return out


def texture_check(blob: bytes, mp) -> dict:
    """Every law the 8bpp decode rests on, evaluated on one package -- ``{"decodable", "reasons", "parts"}``.

    ``decodable`` False means SAY SO and fall back to an untextured export; it never means "guess". The
    laws (each corpus-verified 24/24 on the stock creature packages):

      * ``partCount >= 1`` and ``texBytes == partCount * 0x4000``   -- one 128x128 page per part
      * ``clutBytes == clutRows * 0x200``                           -- one 256-entry row per CLUT row
      * every part's TPAGE colour mode == 1 (8bpp)                  -- 4bpp/16bpp pages are NOT this layout
      * every part's CLUT row lands inside the strip, and its 256 entries fit the strip's width
      * the pages + strip lie inside the blob
    """
    reasons: List[str] = []
    parts = part_textures(mp)
    if mp.part_count < 1:
        reasons.append("partCount == 0 (the package declares no texture part)")
    if mp.tex_bytes != mp.part_count * PAGE_BYTES:
        reasons.append(f"texBytes {mp.tex_bytes:#x} != partCount*{PAGE_BYTES:#x} "
                       f"({mp.part_count * PAGE_BYTES:#x}) -- not the 128x128 8bpp page layout")
    if mp.clut_bytes != mp.clut_rows * CLUT_ROW_BYTES:
        reasons.append(f"clutBytes {mp.clut_bytes:#x} != clutRows*{CLUT_ROW_BYTES:#x} "
                       f"({mp.clut_rows * CLUT_ROW_BYTES:#x})")
    for p in parts:
        if p.mode != MODE_8BPP:
            reasons.append(f"part {p.index}: tpage {p.tpage:#x} colour mode {p.mode} "
                           f"({'4bpp' if p.mode == MODE_4BPP else '16bpp' if p.mode == MODE_16BPP else '?'})"
                           f" -- only 8bpp (mode 1) is the decoded layout")
        if not (0 <= p.clut_row < max(mp.clut_rows, 0)):
            reasons.append(f"part {p.index}: CLUT word {p.clut:#x} -> strip row {p.clut_row}, outside the "
                           f"{mp.clut_rows}-row strip")
        if p.clut_entry0 < 0 or p.clut_entry0 + PALETTE_LEN > CLUT_STRIP_W:
            reasons.append(f"part {p.index}: CLUT word {p.clut:#x} -> entry {p.clut_entry0}, its "
                           f"{PALETTE_LEN} entries do not fit the {CLUT_STRIP_W}-entry strip row")
    end = mp.tex_file_offset + mp.tex_bytes + mp.clut_bytes
    if end > len(blob):
        reasons.append(f"the texture block ends at {end:#x}, past the {len(blob):#x}-byte blob")
    return {"decodable": not reasons, "reasons": reasons, "parts": parts}


# --------------------------------------------------------------------------- the decode
def read_palette(blob: bytes, offset: int, count: int = PALETTE_LEN) -> List[Tuple[int, int, int, int]]:
    """``count`` BGR555 entries at an absolute file offset -> RGBA tuples."""
    return [bgr555_rgba(w) for w in struct.unpack_from(f"<{count}H", blob, offset)]


def decode_page_rgba(pixels: Sequence[int], palette: Sequence[Tuple[int, int, int, int]],
                     *, page_w: int = PAGE_W, page_h: int = PAGE_H) -> List[Tuple[int, int, int, int]]:
    """``page_w * page_h`` 8-bit indices + a palette -> a row-major RGBA list (pure; PIL-free, so the page
    math is testable without an imaging library). Row 0 is the block's TOP VRAM line, which is the row a
    pre-bake ``v`` of 0 addresses (see :func:`page_row`)."""
    n = page_w * page_h
    if len(pixels) < n:
        raise TextureError(f"page is {len(pixels)} bytes, need {n} for {page_w}x{page_h} at 8bpp")
    return [palette[i] for i in pixels[:n]]


def decode_pages(blob: bytes, mp) -> Dict[int, "object"]:
    """Every part's page -> ``{part index: PIL RGBA Image}`` (128x128). Raises :class:`TextureError` when
    :func:`texture_check` refuses the package, or when Pillow is missing.

    The returned images are decoded STOCK CONTENT: they may only be written to a LOCAL-ONLY destination
    (``summons/export.py``'s guard). This function itself writes nothing."""
    chk = texture_check(blob, mp)
    if not chk["decodable"]:
        raise TextureError("this creature's texture block is not the decoded 8bpp page layout:\n  - "
                           + "\n  - ".join(chk["reasons"]))
    try:
        from PIL import Image
    except ImportError as e:                                     # pragma: no cover - env-dependent
        raise TextureError("decoding summon texture pages needs Pillow (py -m pip install Pillow)") from e
    out: Dict[int, object] = {}
    for p in chk["parts"]:
        palette = read_palette(blob, p.clut_offset)
        px = blob[p.page_offset:p.page_offset + PAGE_BYTES]
        img = Image.new("RGBA", (PAGE_W, PAGE_H))
        img.putdata(decode_page_rgba(px, palette))
        out[p.index] = img
    return out


def summary(blob: bytes, mp) -> str:
    """A read-only listing of the texture block -- offsets, VRAM rects and the refusal reasons, never a
    pixel. The debug counterpart of ``container.summary`` (and what a future ``summon-inspect`` verb would
    print for this layer)."""
    chk = texture_check(blob, mp)
    lines = [f"  TEXTURE: parts={mp.part_count} clutRows={mp.clut_rows} texBytes={mp.tex_bytes:#x} "
             f"clutBytes={mp.clut_bytes:#x} decodable={chk['decodable']}"]
    for p in chk["parts"]:
        lines.append(f"    part{p.index}: tpage={p.tpage:#x} mode={p.mode} vram={p.vram} vOff={p.v_offset} "
                     f"clut={p.clut:#x} row={p.clut_row} page@{p.page_offset:#x} clut@{p.clut_offset:#x}")
    for r in chk["reasons"]:
        lines.append(f"    ! {r}")
    return "\n".join(lines)
