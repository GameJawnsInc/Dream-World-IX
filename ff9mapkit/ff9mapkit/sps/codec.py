"""Lossless codec for the FF9 field ``.sps`` (Special Particle System) effect binary -- parse -> model ->
re-serialize -> build, the foundation a future SPS browser / re-skin / creator reads from. An ``.sps`` is a
multi-frame cloud of 2D textured billboard quads ("prims"); the PIXELS live in the shared per-scene
``spt.tcb`` VRAM texture (a SEPARATE format -- the authoring gate), and the field ``.eb`` fires ``RunSPSCode``
to load + place + animate it. This module owns only the ``.sps`` GEOMETRY/ANIMATION bytes -- the half we
fully control. -> [[project-ff9-sps-authoring]].

PROVEN against the engine source (``SPSEffect.LoadSPS`` / ``_GenerateSPSPrims`` :148-247, the TPage/Clut
bitfields in ``TIMUtils``) and a 9-file Ice-Cavern corpus: ``serialize(parse(b)) == b`` byte-exact on 9/9
real donors, and ``build(...)`` (a from-scratch constructor that recomputes every offset) reproduces all 9
from high-level fields alone -- so the encoder needs no hand-authored offsets and a synthetic effect is
well-formed under the same code path the engine uses.

Format facts (all little-endian; frame-table values are ABSOLUTE file offsets):

* Header: ``header0 u16 @0`` -- ``frame_count = header0 & 0x7FFF``; bit 15 = a flag (never set in the corpus,
  carried opaque). ``tpage_raw u16 @2`` -- the TIM page word; the runtime OR-s the ABR blend bits (5-6) in
  from the SPS instance, so they are NOT stored here. ``clut_raw u16 @4`` -- the palette word.
  ``h_raw u8 @6`` / ``w_raw u8 @7`` -- the size byte does DOUBLE DUTY: quad half-size (world) = ``(raw-1)*2``,
  UV-cell half-size (px) = ``raw-1``.
* ``frame_offsets`` : ``u16[frame_count] @8`` -- each is the absolute offset of that frame's prim block.
* ``work_offset = frame_count*2 + 8`` : ``rgb_offset u16`` (== the UV-table entry count). Then
  ``pt = work_offset + 2`` (UV table base) and ``rgb = pt + rgb_offset*2 + 2`` (RGB table base; the ``+2``
  skips a constant ``0x0010`` separator word that sits between the two tables).
* UV table @ ``pt`` : ``rgb_offset`` x ``(u8 uvx, u8 uvy)``; a prim's UV cell = entry ``texpos & 0x0F``.
* RGB table @ ``rgb`` : stride-4 ``(u8 r, u8 g, u8 b, u8 pad)`` ramp colors; a prim's color = entry
  ``texpos >> 4`` (the runtime multiplies it by the instance ``fade``; ``pad`` is the PSX STP bit -- keep 0).
* Each frame block @ its offset: ``u8 prim_count`` then ``prim_count`` x 3-byte prim
  ``(i8 pos_x, i8 pos_y, u8 texpos)`` -- runtime world pos = ``pos << 2`` (so +-508 units), ``texpos`` packs
  the UV index (low nibble) + RGB index (high nibble).
* Canonical layout (what the real files use AND what ``build`` emits): header -> frame table -> rgb_offset
  word -> UV table -> separator -> RGB table -> frame blocks (contiguous, in index order) -> 0..3 tail pad
  bytes. ``parse`` captures the source frame offsets + tail verbatim, so ``serialize`` stays byte-exact even
  on an off-canonical layout.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field as _field


class SpsCodecError(ValueError):
    pass


# ----------------------------------------------------------------------------- texpos / size bit helpers
def pack_texpos(uv_index: int, rgb_index: int) -> int:
    """Pack a UV-cell index (0..15) + RGB-ramp index (0..15) into a prim ``texpos`` byte."""
    if not (0 <= uv_index <= 0x0F and 0 <= rgb_index <= 0x0F):
        raise SpsCodecError(f"uv/rgb index out of nibble range (0..15): {uv_index},{rgb_index}")
    return (rgb_index << 4) | uv_index


def make_tpage(*, tp: int = 0, ty: int = 0, tx: int = 0) -> int:
    """Build a ``tpage_raw`` word from its fields (TP = color mode 0=4bpp/1=8bpp/2=16bpp, TY*256/TX*64 =
    VRAM base). ABR (blend) is set at runtime via the ``.eb`` ABR op, not stored, so it is omitted here."""
    return ((tp & 3) << 7) | ((ty & 1) << 4) | (tx & 0x0F)


def make_clut(*, cluty: int = 0, clutx: int = 0) -> int:
    """Build a ``clut_raw`` word from its fields (ClutY = VRAM row, ClutX*16 = VRAM halfword x)."""
    return ((cluty & 0x1FF) << 6) | (clutx & 0x3F)


def _i8(v: int) -> int:
    if not -128 <= v <= 127:
        raise SpsCodecError(f"prim position {v} out of i8 range (-128..127)")
    return v


# ----------------------------------------------------------------------------- the model
@dataclass
class Prim:
    """One textured billboard quad in a frame. ``pos_*`` are signed i8 (runtime ``<<2``); ``texpos`` packs
    the UV-cell index (low nibble) + RGB-ramp index (high nibble)."""
    pos_x: int
    pos_y: int
    texpos: int

    @property
    def uv_index(self) -> int:
        return self.texpos & 0x0F

    @property
    def rgb_index(self) -> int:
        return (self.texpos >> 4) & 0x0F


def prim(pos_x: int, pos_y: int, uv_index: int, rgb_index: int) -> Prim:
    """Construct a :class:`Prim` from explicit UV + RGB indices (friendlier than a raw ``texpos`` byte)."""
    return Prim(pos_x, pos_y, pack_texpos(uv_index, rgb_index))


@dataclass
class Sps:
    """A parsed / authorable ``.sps`` effect: header + per-frame prim lists + the shared UV + RGB tables."""
    tpage_raw: int
    clut_raw: int
    h_raw: int
    w_raw: int
    frames: list[list[Prim]] = _field(default_factory=list)
    uv_table: list[tuple[int, int]] = _field(default_factory=list)
    rgb_table: list[tuple[int, int, int, int]] = _field(default_factory=list)
    flag_bit15: int = 0
    separator: int = 0x0010
    tail: bytes = b""
    # Captured source layout (set by parse). None for a from-scratch model -> serialize lays the frame
    # blocks out canonically (contiguous, after the RGB table).
    frame_offsets: list[int] | None = None

    # --- decoded conveniences (mirror SPSEffect) ---
    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def half_w(self) -> int:
        return (self.w_raw - 1) * 2

    @property
    def half_h(self) -> int:
        return (self.h_raw - 1) * 2

    @property
    def tpage(self) -> dict:
        v = self.tpage_raw
        return {"TP": (v >> 7) & 3, "ABR": (v >> 5) & 3, "TY": (v >> 4) & 1, "TX": v & 0x0F}

    @property
    def clut(self) -> dict:
        v = self.clut_raw
        return {"ClutY": (v >> 6) & 0x1FF, "ClutX": v & 0x3F}


# ----------------------------------------------------------------------------- parse
def parse(data: bytes) -> Sps:
    """Decode an ``.sps`` blob into an :class:`Sps`. Captures the frame offsets + trailing pad verbatim so
    :func:`serialize` round-trips byte-exact."""
    if len(data) < 8:
        raise SpsCodecError(f".sps too short: {len(data)} bytes")
    header0 = struct.unpack_from("<H", data, 0)[0]
    frame_count = header0 & 0x7FFF
    work_offset = frame_count * 2 + 8
    if work_offset + 2 > len(data):
        raise SpsCodecError(f"frame table ({frame_count} frames) overruns {len(data)}-byte file")
    s = Sps(
        tpage_raw=struct.unpack_from("<H", data, 2)[0],
        clut_raw=struct.unpack_from("<H", data, 4)[0],
        h_raw=data[6],
        w_raw=data[7],
        flag_bit15=(header0 >> 15) & 1,
    )
    s.frame_offsets = list(struct.unpack_from("<%dH" % frame_count, data, 8))
    rgb_offset = struct.unpack_from("<H", data, work_offset)[0]
    pt = work_offset + 2
    rgb = pt + rgb_offset * 2 + 2
    if rgb > len(data):
        raise SpsCodecError("UV/RGB table overruns file")
    # UV table = exactly rgb_offset entries, then the separator word.
    for k in range(rgb_offset):
        s.uv_table.append((data[pt + (k << 1)], data[pt + (k << 1) + 1]))
    s.separator = struct.unpack_from("<H", data, pt + rgb_offset * 2)[0]
    # Frame prim blocks.
    for fo in s.frame_offsets:
        prim_count = data[fo]
        prims: list[Prim] = []
        p = fo + 1
        for _ in range(prim_count):
            pos_x = struct.unpack_from("<b", data, p)[0]
            pos_y = struct.unpack_from("<b", data, p + 1)[0]
            prims.append(Prim(pos_x, pos_y, data[p + 2]))
            p += 3
        s.frames.append(prims)
    # RGB table spans rgb -> the first frame block (canonical) or EOF; stride 4.
    first_frame = min(s.frame_offsets) if s.frame_offsets else len(data)
    rgb_end = first_frame if first_frame > rgb else len(data)
    for k in range((rgb_end - rgb) // 4):
        base = rgb + (k << 2)
        s.rgb_table.append((data[base], data[base + 1], data[base + 2], data[base + 3]))
    # Tail = bytes after the last structural element (verbatim alignment padding).
    last_end = (max(fo + 1 + 3 * len(pr) for fo, pr in zip(s.frame_offsets, s.frames))
                if s.frames else rgb_end)
    struct_end = max(last_end, rgb + len(s.rgb_table) * 4, pt + rgb_offset * 2 + 2)
    s.tail = data[struct_end:]
    return s


# ----------------------------------------------------------------------------- serialize
def _layout(s: Sps):
    """Return ``(frame_offsets, work_offset, pt, rgb, struct_end)``. Reuses the captured frame offsets when
    present + consistent (byte-exact round-trip); else lays the frame blocks out canonically (contiguous,
    right after the RGB table, in index order)."""
    nframes = len(s.frames)
    rgb_offset = len(s.uv_table)
    work_offset = nframes * 2 + 8
    pt = work_offset + 2
    rgb = pt + rgb_offset * 2 + 2
    rgb_end = rgb + len(s.rgb_table) * 4
    if s.frame_offsets is not None and len(s.frame_offsets) == nframes:
        frame_offsets = list(s.frame_offsets)
    else:
        frame_offsets = []
        cur = rgb_end
        for prims in s.frames:
            frame_offsets.append(cur)
            cur += 1 + 3 * len(prims)
    last_end = (max(fo + 1 + 3 * len(pr) for fo, pr in zip(frame_offsets, s.frames))
                if s.frames else rgb_end)
    return frame_offsets, work_offset, pt, rgb, max(last_end, rgb_end)


def serialize(s: Sps) -> bytes:
    """Encode an :class:`Sps` back to ``.sps`` bytes (the inverse of :func:`parse`)."""
    if len(s.uv_table) > 0xFFFF:
        raise SpsCodecError("uv_table too large for a u16 rgb_offset")
    frame_offsets, work_offset, pt, rgb, struct_end = _layout(s)
    out = bytearray(struct_end + len(s.tail))
    header0 = (len(s.frames) & 0x7FFF) | ((s.flag_bit15 & 1) << 15)
    struct.pack_into("<H", out, 0, header0)
    struct.pack_into("<H", out, 2, s.tpage_raw & 0xFFFF)
    struct.pack_into("<H", out, 4, s.clut_raw & 0xFFFF)
    out[6] = s.h_raw & 0xFF
    out[7] = s.w_raw & 0xFF
    for i, fo in enumerate(frame_offsets):
        struct.pack_into("<H", out, 8 + i * 2, fo)
    struct.pack_into("<H", out, work_offset, len(s.uv_table))
    for k, (ux, uy) in enumerate(s.uv_table):
        out[pt + (k << 1)] = ux & 0xFF
        out[pt + (k << 1) + 1] = uy & 0xFF
    struct.pack_into("<H", out, pt + len(s.uv_table) * 2, s.separator & 0xFFFF)
    for k, (r, g, b, pad) in enumerate(s.rgb_table):
        base = rgb + (k << 2)
        out[base] = r & 0xFF
        out[base + 1] = g & 0xFF
        out[base + 2] = b & 0xFF
        out[base + 3] = pad & 0xFF
    for fo, prims in zip(frame_offsets, s.frames):
        out[fo] = len(prims) & 0xFF
        p = fo + 1
        for pr in prims:
            struct.pack_into("<b", out, p, _i8(pr.pos_x))
            struct.pack_into("<b", out, p + 1, _i8(pr.pos_y))
            out[p + 2] = pr.texpos & 0xFF
            p += 3
    if s.tail:
        out[struct_end:struct_end + len(s.tail)] = s.tail
    return bytes(out)


# ----------------------------------------------------------------------------- build (from-scratch)
def build(*, tpage_raw: int, clut_raw: int, h_raw: int, w_raw: int,
          uv_table, rgb_table, frames, flag_bit15: int = 0, separator: int = 0x0010,
          tail: bytes = b"") -> Sps:
    """Construct a from-scratch :class:`Sps` (no captured layout -> :func:`serialize` emits the canonical
    contiguous layout, recomputing every offset). ``frames`` is a list of prim lists; ``uv_table`` is
    ``(x, y)`` pairs; ``rgb_table`` is ``(r, g, b, pad)`` ramp colors."""
    return Sps(
        tpage_raw=tpage_raw, clut_raw=clut_raw, h_raw=h_raw, w_raw=w_raw,
        frames=[list(f) for f in frames],
        uv_table=[tuple(t) for t in uv_table],
        rgb_table=[tuple(t) for t in rgb_table],
        flag_bit15=flag_bit15, separator=separator, tail=tail,
    )
