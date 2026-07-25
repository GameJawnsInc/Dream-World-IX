"""Little-endian struct helpers shared by every binary codec in the kit.

The original tools each redefined some variant of these (``u16``, ``i16``, ``w16``, inline
``struct.pack_into``); they are collected here so the ``.eb`` / ``.bgi`` / ``.bgx`` codecs
share one tested implementation. All multi-byte values in FF9 field binaries are
little-endian.
"""

from __future__ import annotations

import struct

# --- read (from bytes/bytearray at an offset) ---

def u8(b: bytes, o: int) -> int:
    return b[o]


def u16(b: bytes, o: int) -> int:
    """Unsigned 16-bit little-endian."""
    return b[o] | (b[o + 1] << 8)


def i16(b: bytes, o: int) -> int:
    """Signed 16-bit little-endian."""
    return struct.unpack_from("<h", b, o)[0]


def u32(b: bytes, o: int) -> int:
    return struct.unpack_from("<I", b, o)[0]


def i32(b: bytes, o: int) -> int:
    return struct.unpack_from("<i", b, o)[0]


# --- pack (to bytes) ---

def pu16(v: int) -> bytes:
    """Pack an unsigned 16-bit little-endian value."""
    return struct.pack("<H", v & 0xFFFF)


def pi16(v: int) -> bytes:
    """Pack a signed 16-bit little-endian value."""
    return struct.pack("<h", v)


def pu32(v: int) -> bytes:
    return struct.pack("<I", v & 0xFFFFFFFF)


# --- write (in place on a bytearray at an offset) ---

def set_u16(b: bytearray, o: int, v: int) -> None:
    """STRICT since the long-jump relaxation: masking (& 0xFFFF) let an
    oversized value WRAP SILENTLY — for an `.eb` entry-table offset that is a
    corrupted field with garbage function tags and no error at the write site
    (the condor round-3 find: bodies can now legally exceed the old ~32KB body
    wall, so the u16 FILE wall must fail loudly wherever it is hit)."""
    if not 0 <= v <= 0xFFFF:
        raise ValueError(f"set_u16: {v} does not fit u16 — for an .eb entry "
                         f"offset this means the FILE passed the engine's "
                         f"64KB entry-table reach; trim the biggest bodies")
    struct.pack_into("<H", b, o, v)


def set_i16(b: bytearray, o: int, v: int) -> None:
    struct.pack_into("<h", b, o, v)
