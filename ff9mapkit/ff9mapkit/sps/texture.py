"""Decode the shared ``spt.tcb`` texture an ``.sps`` effect samples -- the read-only half of the SPS picture
(Tier 0 preview). An ``.sps`` carries only quad positions + UV/RGB indices; the PIXELS live in ``spt.tcb``,
a PSX-VRAM blit blob. This module replays the blits into a simulated VRAM and decodes a TPage (through its
CLUT) to RGBA, exactly as the engine does.

PORTED byte-for-byte from the engine (``PSXTextureMgr.LoadTCBInVram`` / ``LoadImageBin`` :109-449 and
``PSXTexture.CreateBufferColor32`` / ``ConvertABGR16toABGR32`` :42-132). No PIL / UnityPy needed -- pure
bytes in, RGBA bytes out (``render.py`` adds the PIL compositing for a preview image).

The model: VRAM is ``u16[1024*512]`` addressed ``vram[y*1024 + x]``. ``spt.tcb`` is two batches of
``(x, y, w, h)`` rectangle blits (BGR555 halfwords) -- both the indexed texture page AND the CLUT (palette)
rows live in that VRAM. An ``.sps``'s ``tpage_raw`` (TP color-mode / TX*64 / TY*256) selects a 256x256 texel
window; ``clut_raw`` (ClutX*16 / ClutY) selects the palette row. -> [[project-ff9-sps-authoring]].
"""
from __future__ import annotations

import struct
from array import array

VRAM_W = 1024
VRAM_H = 512
VRAM_SIZE = VRAM_W * VRAM_H  # 524288 u16


class SpsTextureError(ValueError):
    pass


def _load_image_bin(vram: array, x: int, y: int, w: int, h: int, data: bytes, off: int) -> int:
    """Blit a w*h rectangle of LE-u16 pixels into VRAM at (x, y). Returns the new read cursor. Mirrors
    ``PSXTextureMgr.LoadImageBin``."""
    for i in range(h):
        base = (y + i) * VRAM_W + x
        row = base
        for _ in range(w):
            lo = data[off]
            hi = data[off + 1]
            vram[row] = (hi << 8) | lo
            row += 1
            off += 2
    return off


def load_tcb_to_vram(tcb: bytes) -> array:
    """Replay a ``spt.tcb`` container into a fresh simulated VRAM (``array('H')`` of length 524288).
    Mirrors ``PSXTextureMgr.LoadTCBInVram``: a header (secondBatchOffset, firstBatchOffset, firstBatchCount)
    then two batches of rect blits -- the first carries an inline 8-byte rect header before each block's
    pixels, the second packs the rect headers and pixels in separate running cursors."""
    if len(tcb) < 12:
        raise SpsTextureError(f"spt.tcb too short: {len(tcb)} bytes")
    vram = array("H", bytes(VRAM_SIZE * 2))  # zero-initialised (unblitted texels read as transparent)
    second_batch_off, first_batch_off, first_batch_count = struct.unpack_from("<IIi", tcb, 0)
    try:
        # First batch: rect header is inline, immediately followed by its pixels.
        off = first_batch_off
        for _ in range(first_batch_count):
            x, y, w, h = struct.unpack_from("<hhhh", tcb, off)
            _load_image_bin(vram, x, y, w, h, tcb, off + 8)
            off += w * h * 2 + 8
        # Second batch: rect headers packed from second_batch_off+8, pixels from a separate img cursor.
        img_off, second_batch_count = struct.unpack_from("<Ii", tcb, second_batch_off)
        rect_off = second_batch_off + 8
        for _ in range(second_batch_count):
            x, y, w, h = struct.unpack_from("<hhhh", tcb, rect_off)
            img_off = _load_image_bin(vram, x, y, w, h, tcb, img_off)
            rect_off += 8
    except (struct.error, IndexError) as ex:
        raise SpsTextureError(f"malformed spt.tcb: {ex}") from ex
    return vram


def _abgr16_to_rgba(num: int) -> tuple[int, int, int, int]:
    """Expand a PSX BGR555 halfword to RGBA8. Black (0x0000) is transparent; the 0x8000 STP bit OR any colour
    bit makes it opaque. Mirrors ``PSXTexture.ConvertABGR16toABGR32``."""
    r = (num & 0x1F) << 3
    g = (num & 0x3E0) >> 2
    b = (num & 0x7C00) >> 7
    a = 255 if (num & 0x8000) or (num & 0x7FFF) else 0
    return r, g, b, a


def decode_page(vram: array, tpage_raw: int, clut_raw: int, w: int = 256, h: int = 256) -> bytes:
    """Decode a 256x256 (by default) RGBA texture window from VRAM for an ``.sps``'s ``tpage``/``clut``.
    Mirrors ``PSXTexture.CreateBufferColor32`` (TP 0=4bpp / 1=8bpp / 2=16bpp-direct). Returns ``w*h*4``
    bytes, row-major, top row first (the same uniIndex order the engine writes)."""
    tp = (tpage_raw >> 7) & 3
    tx = (tpage_raw & 0x0F) << 6   # VRAM x base (halfwords)
    ty = ((tpage_raw >> 4) & 1) << 8   # VRAM y base
    clut_x = clut_raw & 0x3F
    clut_y = (clut_raw >> 6) & 0x1FF
    clut_base = (clut_x << 4) + (clut_y << 10)
    out = bytearray(w * h * 4)
    o = 0

    def put(num: int):
        nonlocal o
        r, g, b, a = _abgr16_to_rgba(num)
        out[o] = r; out[o + 1] = g; out[o + 2] = b; out[o + 3] = a
        o += 4

    if tp == 0:          # 4bpp: 4 texels per halfword, low nibble first
        for y in range(h):
            vi = (ty + y) * VRAM_W + tx
            for _ in range(w >> 2):
                pi = vram[vi]
                put(vram[clut_base + (pi & 0xF)])
                put(vram[clut_base + ((pi >> 4) & 0xF)])
                put(vram[clut_base + ((pi >> 8) & 0xF)])
                put(vram[clut_base + (pi >> 12)])
                vi += 1
    elif tp == 1:        # 8bpp: 2 texels per halfword
        for y in range(h):
            vi = (ty + y) * VRAM_W + tx
            for _ in range(w >> 1):
                pi = vram[vi]
                put(vram[clut_base + (pi & 0xFF)])
                put(vram[clut_base + (pi >> 8)])
                vi += 1
    else:                # 16bpp direct (no CLUT)
        for y in range(h):
            vi = (ty + y) * VRAM_W + tx
            for _ in range(w):
                put(vram[vi])
                vi += 1
    return bytes(out)


def tcb_page_rgba(tcb: bytes, tpage_raw: int, clut_raw: int, w: int = 256, h: int = 256):
    """Convenience: load ``spt.tcb`` and decode the page an effect samples. Returns ``(w, h, rgba_bytes)``."""
    vram = load_tcb_to_vram(tcb)
    return w, h, decode_page(vram, tpage_raw, clut_raw, w, h)
