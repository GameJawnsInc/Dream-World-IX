"""Structured, byte-exact model of a FF9 field event script (``.eb``).

An :class:`EbScript` is a *parsed view* over the raw bytes. The raw bytes are always the
source of truth: parsing only derives structure for queries and locators, and every edit
(in :mod:`ff9mapkit.eb.edit`) splices the existing bytes rather than re-serializing from the
parse. So ``EbScript.from_bytes(x).to_bytes() == x`` holds for any valid input — the round
trip is the identity. (Verified across every shipped/room ``.eb`` in the Phase-1 tests.)

File layout (little-endian), reverse-engineered + confirmed against Memoria's EventEngine
and the project's existing tooling:

    [0x00] 'EV'                      magic
    [0x02] u8  unknown
    [0x03] u8  entryCount            number of entry-table slots
    [0x04..0x2B]                     header (opaque; preserved verbatim)
    [0x2C..0x7F]  84 bytes           PSX field-name string (FF9 text encoding; per-language,
                                     cosmetic/debug — the field is resolved by DictionaryPatch
                                     + filename, not by this string)
    [0x80]  entry table              entryCount * 8 bytes, each:
                                       off:u16  (entry start, RELATIVE to 0x80)
                                       sz :u16  (entry byte length; 0 = empty slot)
                                       loc:u8   flags:u8   pad:u16
    entry body (when sz > 0):
        type:u8  funcCount:u8
        funcCount * (tag:u16, fpos:u16)          func table; fpos RELATIVE to entryStart+2
        ... bytecode ...
      => a function's code starts at  entryStart + 2 + fpos  and runs to the next func's
         start (or the entry end). This "funcBasePos = entryStart + 2" convention is the one
         subtlety that trips up naive parsers.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..binutils import u16
from . import disasm

MAGIC = b"EV"
ENTRY_TABLE_OFF = 0x80          # 128
ENTRY_SLOT_SIZE = 8
NAME_OFF = 0x2C                 # 44
NAME_LEN = 84
HEADER_LEN = ENTRY_TABLE_OFF    # everything before the entry table (header + name)


@dataclass(frozen=True)
class Func:
    """One function within an entry."""

    index: int
    tag: int
    fpos: int          # relative to entryStart + 2
    abs_start: int     # absolute byte offset of this function's code
    abs_end: int       # absolute byte offset where it ends (next func / entry end)

    @property
    def length(self) -> int:
        return self.abs_end - self.abs_start


@dataclass(frozen=True)
class Entry:
    """One entry-table slot and (if non-empty) its parsed body."""

    index: int
    off: int           # relative to 0x80
    size: int
    loc: int
    flags: int
    abs_start: int     # 0x80 + off
    abs_end: int       # abs_start + size
    type: int | None
    func_count: int
    funcs: tuple[Func, ...]

    @property
    def empty(self) -> bool:
        return self.size == 0

    def func_by_tag(self, tag: int) -> Func | None:
        for f in self.funcs:
            if f.tag == tag:
                return f
        return None


class EbScript:
    """Parsed, byte-exact view of a ``.eb`` field script."""

    def __init__(self, data: bytes):
        self.data = bytes(data)
        if self.data[:2] != MAGIC:
            raise ValueError(f"not an .eb script (magic={self.data[:2]!r}, expected {MAGIC!r})")
        self.entry_count = self.data[3]
        self.entries: tuple[Entry, ...] = tuple(self._parse_entry(i) for i in range(self.entry_count))

    # -- construction / serialization --
    @classmethod
    def from_bytes(cls, data: bytes) -> "EbScript":
        return cls(data)

    @classmethod
    def from_file(cls, path) -> "EbScript":
        with open(path, "rb") as fh:
            return cls(fh.read())

    def to_bytes(self) -> bytes:
        return self.data

    # -- parsing --
    def _slot_off(self, i: int) -> int:
        return ENTRY_TABLE_OFF + i * ENTRY_SLOT_SIZE

    def _parse_entry(self, i: int) -> Entry:
        d = self.data
        so = self._slot_off(i)
        off = u16(d, so)
        size = u16(d, so + 2)
        loc = d[so + 4]
        flags = d[so + 5]
        abs_start = ENTRY_TABLE_OFF + off
        abs_end = abs_start + size
        if size == 0:
            return Entry(i, off, size, loc, flags, abs_start, abs_end, None, 0, ())
        etype = d[abs_start]
        fc = d[abs_start + 1]
        fbase = abs_start + 2
        raw_funcs = []
        q = fbase
        for _ in range(fc):
            tag = u16(d, q)
            fpos = u16(d, q + 2)
            raw_funcs.append((tag, fpos))
            q += 4
        funcs = []
        for fi, (tag, fpos) in enumerate(raw_funcs):
            fstart = fbase + fpos
            fend = (fbase + raw_funcs[fi + 1][1]) if fi + 1 < fc else abs_end
            funcs.append(Func(fi, tag, fpos, fstart, fend))
        return Entry(i, off, size, loc, flags, abs_start, abs_end, etype, fc, tuple(funcs))

    # -- convenient accessors --
    @property
    def name_region(self) -> bytes:
        """The 84-byte PSX field-name field (per-language; preserved across edits)."""
        return self.data[NAME_OFF:NAME_OFF + NAME_LEN]

    @property
    def main(self) -> Entry:
        """Entry 0 — the Main entry (Main_Init = its first function, tag 0)."""
        return self.entries[0]

    def entry(self, i: int) -> Entry:
        return self.entries[i]

    def free_slots(self) -> list[int]:
        """Indices of empty entry-table slots, in order."""
        return [e.index for e in self.entries if e.empty]

    def first_free_slot(self) -> int:
        """Index of the first empty entry-table slot. When the table is FULL, returns
        :attr:`entry_count` (the index one past the last slot) -- the signal for
        :func:`ff9mapkit.eb.edit.append_entry` to grow the table. Real fields run to ~30 entries, so a
        content-dense field (e.g. an Ice Cavern screen with 6 jumps) legitimately needs more than the
        blank template's 10 slots; growth is on-demand so fields that fit stay byte-identical."""
        for e in self.entries:
            if e.empty:
                return e.index
        return self.entry_count

    def instrs(self, func: Func):
        """Iterate decoded instructions of a function."""
        yield from disasm.iter_code(self.data, func.abs_start, func.abs_end)

    def __repr__(self) -> str:
        used = sum(1 for e in self.entries if not e.empty)
        return f"<EbScript {len(self.data)}B entries={self.entry_count} used={used}>"
