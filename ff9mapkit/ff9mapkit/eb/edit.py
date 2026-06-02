"""Structural edits on a FF9 field event script (``.eb``).

Every function here splices the *existing* bytes; none re-serialize from a parse. The two
load-bearing primitives:

  * :func:`insert_bytes` — insert bytes at an absolute offset and keep the entry table
    consistent (grow the containing entry, shift every later entry's offset). This is the
    relayout that was copy-pasted into ~5 of the original tools; it lives here once.
  * :func:`append_entry` — append a whole new entry body at end-of-file and register it in a
    free slot. Because it appends at the end, it never shifts existing bytecode.

Injecting behaviour into an existing function is done **shift-free** wherever possible by
overwriting a ``Wait(n)`` filler with an equal-length opcode (``InitObject`` / ``InitRegion``
/ ``InitCode`` are all 3 bytes, same as ``Wait`` ``22 00 nn``). :func:`find_wait` locates such
fillers. When a genuine insert is unavoidable, :func:`jumps_crossing` flags any relative jump
that would straddle the insert point (the one thing that makes an insert unsafe).

All functions accept either raw ``bytes`` or an :class:`~ff9mapkit.eb.model.EbScript` and
return raw ``bytes``.
"""

from __future__ import annotations

from ..binutils import set_u16, u16
from .model import ENTRY_SLOT_SIZE, ENTRY_TABLE_OFF, EbScript


def _as_bytes(data) -> bytes:
    return data.to_bytes() if isinstance(data, EbScript) else bytes(data)


# --------------------------------------------------------------------------- core relayout

def insert_bytes(data, abs_off: int, ins: bytes) -> bytes:
    """Insert ``ins`` at absolute offset ``abs_off``; keep the entry table consistent.

    Grows the entry that contains ``abs_off`` (so its declared size still covers its code) and
    bumps the table offset of every entry that starts after it. Entry-count aware. Internal
    func ``fpos`` values are relative to their entry, so they need no fixup.
    """
    b = bytearray(_as_bytes(data))
    n = b[3]
    target = None
    for i in range(n):
        so = ENTRY_TABLE_OFF + i * ENTRY_SLOT_SIZE
        off, sz = u16(b, so), u16(b, so + 2)
        if sz > 0 and ENTRY_TABLE_OFF + off <= abs_off < ENTRY_TABLE_OFF + off + sz:
            target = (i, off, sz)
            break
    if target is None:
        raise ValueError(f"no entry contains absolute offset {abs_off}")
    ti, toff, tsz = target
    set_u16(b, ENTRY_TABLE_OFF + ti * ENTRY_SLOT_SIZE + 2, tsz + len(ins))
    for j in range(n):
        if j == ti:
            continue
        so = ENTRY_TABLE_OFF + j * ENTRY_SLOT_SIZE
        off = u16(b, so)
        if off > toff:
            set_u16(b, so, off + len(ins))
    return bytes(b[:abs_off]) + bytes(ins) + bytes(b[abs_off:])


def append_entry(data, slot: int, entry_bytes: bytes) -> bytes:
    """Append ``entry_bytes`` at end-of-file and register it in entry-table ``slot``.

    The slot must currently be empty. Returns new bytes. Does not shift existing bytecode.
    """
    b = bytearray(_as_bytes(data))
    so = ENTRY_TABLE_OFF + slot * ENTRY_SLOT_SIZE
    if u16(b, so + 2) != 0:
        raise ValueError(f"entry slot {slot} is not empty (size={u16(b, so + 2)})")
    new_off = len(b) - ENTRY_TABLE_OFF
    b += entry_bytes
    set_u16(b, so, new_off)
    set_u16(b, so + 2, len(entry_bytes))
    b[so + 4] = 0  # loc
    b[so + 5] = 0  # flags
    b[so + 6] = 0  # pad
    b[so + 7] = 0
    return bytes(b)


def nop_range(data, abs_off: int, length: int) -> bytes:
    """Overwrite ``length`` bytes at ``abs_off`` with NOP (0x00). Length-preserving."""
    b = bytearray(_as_bytes(data))
    b[abs_off:abs_off + length] = bytes(length)
    return bytes(b)


def patch_bytes(data, abs_off: int, new: bytes, expect: bytes | None = None) -> bytes:
    """Overwrite ``len(new)`` bytes at ``abs_off``. If ``expect`` given, assert it matches first."""
    b = bytearray(_as_bytes(data))
    if expect is not None and bytes(b[abs_off:abs_off + len(expect)]) != expect:
        got = bytes(b[abs_off:abs_off + len(expect)])
        raise ValueError(f"patch @ {abs_off}: expected {expect.hex()} got {got.hex()}")
    b[abs_off:abs_off + len(new)] = new
    return bytes(b)


# --------------------------------------------------------------------------- locators

WAIT_OP = 0x22  # Wait(n) encodes as  22 00 nn  (op, argFlag=0, 1-byte count)


def find_entry_containing(eb: EbScript, abs_off: int):
    for e in eb.entries:
        if not e.empty and e.abs_start <= abs_off < e.abs_end:
            return e
    return None


def find_instrs(eb: EbScript, op: int, *, entry_index: int = 0, func_tag: int | None = None):
    """All instructions with opcode ``op`` in the given entry (optionally a single func)."""
    entry = eb.entry(entry_index)
    funcs = entry.funcs if func_tag is None else [f for f in entry.funcs if f.tag == func_tag]
    out = []
    for f in funcs:
        for ins in eb.instrs(f):
            if ins.op == op:
                out.append(ins)
    return out


def find_wait(eb: EbScript, *, n: int | None = None, entry_index: int = 0,
              func_tag: int | None = 0, occurrence: int = 0) -> int:
    """Absolute offset of a ``Wait(n)`` filler (default: in Main_Init, entry 0 func tag 0).

    ``n`` filters by the wait count; ``occurrence`` selects among multiple matches. This is the
    canonical shift-free injection site: overwrite the 3-byte ``Wait`` with an equal-length
    ``InitObject``/``InitRegion``/``InitCode``. Raises if no matching filler exists.
    """
    matches = [ins for ins in find_instrs(eb, WAIT_OP, entry_index=entry_index, func_tag=func_tag)
               if n is None or ins.imm(0) == n]
    if occurrence >= len(matches):
        raise ValueError(f"no Wait({n}) filler #{occurrence} in entry {entry_index} func {func_tag} "
                         f"(found {len(matches)})")
    return matches[occurrence].off


# --------------------------------------------------------------------------- jump safety (best effort)

JMP_OP = 0x03  # unconditional relative jump: operand is signed int16, target = instr.end + offset


def relative_jumps(eb: EbScript):
    """All unconditional relative jumps (op 0x03) as (src_off, src_end, target) tuples.

    Best effort: covers the unconditional JMP. The recommended injection path (overwrite a
    Wait filler, or append an entry) is shift-free and needs no jump analysis; this helper is
    a safety net for the rarer case of inserting into a function with control flow.
    """
    out = []
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op == JMP_OP and not ins.arg_is_expr[0]:
                    raw = ins.imm(0)
                    offset = raw - 0x10000 if raw >= 0x8000 else raw  # signed int16
                    out.append((ins.off, ins.end, ins.end + offset))
    return out


def jumps_crossing(eb: EbScript, abs_off: int):
    """Relative jumps that would straddle an insert at ``abs_off`` (i.e. become invalid).

    Empty list => inserting at ``abs_off`` is safe with respect to unconditional jumps.
    """
    crossing = []
    for src_off, src_end, target in relative_jumps(eb):
        lo, hi = sorted((src_end, target))
        if lo < abs_off < hi:
            crossing.append((src_off, target))
    return crossing
