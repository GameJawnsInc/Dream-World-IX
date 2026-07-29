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


# --- the .eb whole-file budget (one definition; every site consumes THESE) ---

EB_FILE_BUDGET = 0xFFFF
"""Largest table-relative offset an `.eb` entry body may START at.

The entry table is u16-addressed, so an entry's ``off`` field (relative to
``ENTRY_TABLE_OFF``, not to byte 0) cannot exceed this. ENGINE-FIXED — no
compiler pass removes it. ⚠ It is an OFFSET budget, not a raw file-length
budget: use :func:`eb_budget_used`, never ``len(eb)``, or a meter will
disagree with the enforcement."""

EB_ENTRY_SIZE_MAX = 0xFFFF
"""Largest size one `.eb` entry body may declare.

A DIFFERENT limit from :data:`EB_FILE_BUDGET` that merely shares a value: this
one is the width of the slot record's own ``size`` field. Keep them distinct —
they would move independently if either field ever widened."""


def eb_budget_used(b) -> int:
    """Bytes of :data:`EB_FILE_BUDGET` an assembled `.eb` has spent.

    Exactly the quantity ``append_entry`` enforces (``len(b) - ENTRY_TABLE_OFF``)
    so no caller can disagree with the write-site check."""
    from .eb.model import ENTRY_TABLE_OFF   # deferred: eb.model imports this module
    return len(b) - ENTRY_TABLE_OFF


# --- pack (to bytes) ---

def pu8(v: int) -> bytes:
    """Pack an unsigned 8-bit value (STRICT, as :func:`pu16`)."""
    if not 0 <= v <= 0xFF:
        raise ValueError(f"pu8: {v} does not fit u8 (0-255)")
    return bytes((v,))


def pu16(v: int) -> bytes:
    """Pack an unsigned 16-bit little-endian value.

    STRICT, for the same reason :func:`set_u16` is: masking (``& 0xFFFF``) let an
    oversized value WRAP SILENTLY, producing a plausible-looking field with no
    error at the write site."""
    if not 0 <= v <= 0xFFFF:
        raise ValueError(f"pu16: {v} does not fit u16 — for an .eb entry "
                         f"offset this means the FILE passed the engine's "
                         f"64KB entry-table reach; trim the biggest bodies")
    return struct.pack("<H", v)


def pi16(v: int) -> bytes:
    """Pack a signed 16-bit little-endian value."""
    return struct.pack("<h", v)


def pu32(v: int) -> bytes:
    """Pack an unsigned 32-bit little-endian value (STRICT, as :func:`pu16`)."""
    if not 0 <= v <= 0xFFFFFFFF:
        raise ValueError(f"pu32: {v} does not fit u32")
    return struct.pack("<I", v)


# --- write (in place on a bytearray at an offset) ---

def set_u16(b: bytearray, o: int, v: int) -> None:
    """STRICT since the long-jump relaxation: masking (& 0xFFFF) let an
    oversized value WRAP SILENTLY — for an `.eb` entry-table offset that is a
    corrupted field with garbage function tags and no error at the write site
    (the condor round-3 find: bodies can now legally exceed the old ~32KB body
    wall, so the u16 FILE wall must fail loudly wherever it is hit)."""
    if not 0 <= v <= EB_FILE_BUDGET:
        raise ValueError(f"set_u16: {v} does not fit u16 — for an .eb entry "
                         f"offset this means the FILE passed the engine's "
                         f"64KB entry-table reach; trim the biggest bodies")
    struct.pack_into("<H", b, o, v)


def set_i16(b: bytearray, o: int, v: int) -> None:
    struct.pack_into("<h", b, o, v)
