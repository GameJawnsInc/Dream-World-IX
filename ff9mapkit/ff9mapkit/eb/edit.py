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

import struct

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


ENTRY_GROW_CHUNK = 8            # slots added per growth (amortise the body reshuffle; real fields ~30)
ENTRY_TABLE_MAX = 255          # entry_count is a single header byte


def grow_entry_table(data, new_count: int) -> bytes:
    """Enlarge the entry table to ``new_count`` slots (a no-op if already that big).

    The table lives at :data:`ENTRY_TABLE_OFF` (128) as ``entry_count`` 8-byte slots, immediately
    followed by the entry bodies (whose slot ``off`` is relative to 128). Adding slots inserts
    ``(new-old)*8`` zero bytes right after the existing table -- pushing every body later -- so each
    EXISTING body's ``off`` is bumped by that amount; the new slots read as empty (off=size=0). The
    44-byte header (byte 3 = count) + 84-byte name precede the table and need no fixup beyond the
    count. ``InitRegion``/``InitObject`` reference a SLOT INDEX (not a byte offset) and func ``fpos``
    is entry-relative, so activations + internal jumps survive untouched."""
    b = bytearray(_as_bytes(data))
    old = b[3]
    if new_count <= old:
        return bytes(b)
    if new_count > ENTRY_TABLE_MAX:
        raise ValueError(f"entry table can hold at most {ENTRY_TABLE_MAX} slots (asked {new_count})")
    k = (new_count - old) * ENTRY_SLOT_SIZE
    for i in range(old):                              # bump every NON-empty body offset by the insert
        so = ENTRY_TABLE_OFF + i * ENTRY_SLOT_SIZE
        if u16(b, so + 2) > 0:                        # empty slots keep off=0
            set_u16(b, so, u16(b, so) + k)
    b[3] = new_count
    ins_at = ENTRY_TABLE_OFF + old * ENTRY_SLOT_SIZE  # right after the old table, before the bodies
    return bytes(b[:ins_at]) + bytes(k) + bytes(b[ins_at:])


def append_entry(data, slot: int, entry_bytes: bytes) -> bytes:
    """Append ``entry_bytes`` at end-of-file and register it in entry-table ``slot``.

    The slot must currently be empty. If ``slot`` is beyond the current table (``slot >= entry_count``
    -- what :meth:`EbScript.first_free_slot` returns when the table is full), the table is grown
    on-demand to accommodate it first. Returns new bytes. Does not shift existing bytecode.
    """
    b = bytearray(_as_bytes(data))
    if slot >= b[3]:                                  # table full -> grow (chunked) to fit this slot
        b = bytearray(grow_entry_table(b, max(slot + 1, b[3] + ENTRY_GROW_CHUNK)))
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


def insert_entry_at(data, at_index: int, entry_bytes: bytes) -> bytes:
    """Insert a NEW entry as slot ``at_index``, shifting the slot records at ``>= at_index`` up one index.

    Unlike :func:`append_entry` (fill an existing empty slot / grow the table at the END), this makes room
    for a new slot in the MIDDLE of the table: one 8-byte slot record is inserted before all entry bodies,
    so every existing body shifts down 8 bytes (its ``off`` += 8) and the records at ``>= at_index`` take a
    new, one-higher slot INDEX; the entry count (header byte 3) is bumped and the new body is appended at
    end-of-file. Returns new bytes; the inserted entry's slot index is ``at_index``.

    Because the existing entries at/after ``at_index`` are RENUMBERED, any bytecode that references them by
    raw slot/uid index is now stale -- the caller must remap those FIRST (see
    :func:`ff9mapkit.content.object.insert_entry_before_band`, which uses this to seat a new NPC just below
    the engine's reserved party-character band).
    """
    b = bytearray(_as_bytes(data))
    n = b[3]
    if not 0 <= at_index <= n:
        raise ValueError(f"at_index {at_index} out of range 0..{n}")
    if n + 1 > ENTRY_TABLE_MAX:
        raise ValueError(f"entry table already at the {ENTRY_TABLE_MAX}-slot max")
    for i in range(n):                                # one slot record inserted before the bodies ->
        so = ENTRY_TABLE_OFF + i * ENTRY_SLOT_SIZE    # every existing body moves down 8 bytes
        if u16(b, so + 2) > 0:
            set_u16(b, so, u16(b, so) + ENTRY_SLOT_SIZE)
    ins_pos = ENTRY_TABLE_OFF + at_index * ENTRY_SLOT_SIZE
    b[ins_pos:ins_pos] = bytes(ENTRY_SLOT_SIZE)       # the new (empty) record; pushes later records up one index
    b[3] = n + 1
    new_off = len(b) - ENTRY_TABLE_OFF                # the new body goes at EOF (after the just-grown table)
    b += entry_bytes
    set_u16(b, ins_pos, new_off)
    set_u16(b, ins_pos + 2, len(entry_bytes))
    b[ins_pos + 4] = 0  # loc
    b[ins_pos + 5] = 0  # flags
    b[ins_pos + 6] = 0  # pad
    b[ins_pos + 7] = 0
    return bytes(b)


def add_function(data, entry_index: int, tag: int, body: bytes) -> bytes:
    """Add a function ``(tag, body)`` to an EXISTING entry.

    Grows the entry's function table by one 4-byte slot (existing funcs' ``fpos += 4``), appends the
    body after the entry's code, and relocates every later entry's table offset by the growth. (The
    re-layout :mod:`ff9mapkit.content.reinit` does for the after-battle handler, generalized -- used by
    the ladder primitive to add the player's climb function.) Raises if ``tag`` already exists.
    """
    b = bytearray(_as_bytes(data))
    slot = ENTRY_TABLE_OFF + entry_index * ENTRY_SLOT_SIZE
    off, sz = u16(b, slot), u16(b, slot + 2)
    if sz == 0:
        raise ValueError(f"entry {entry_index} is empty")
    es = ENTRY_TABLE_OFF + off
    etype, fc = b[es], b[es + 1]
    fbase = es + 2
    funcs = [(u16(b, fbase + i * 4), u16(b, fbase + i * 4 + 2)) for i in range(fc)]
    if any(t == tag for t, _ in funcs):
        raise ValueError(f"entry {entry_index} already has a function with tag {tag}")
    code = bytes(b[fbase + fc * 4: es + sz])
    new_funcs = [(t, fp + 4) for t, fp in funcs] + [(tag, (fc + 1) * 4 + len(code))]
    new_entry = bytearray([etype, fc + 1])
    for t, fp in new_funcs:
        new_entry += struct.pack("<HH", t, fp)
    new_entry += code + body
    growth = len(new_entry) - sz
    out = bytearray(bytes(b[:es]) + bytes(new_entry) + bytes(b[es + sz:]))
    set_u16(out, slot + 2, len(new_entry))
    for i in range(b[3]):
        if i == entry_index:
            continue
        s2 = ENTRY_TABLE_OFF + i * ENTRY_SLOT_SIZE
        if u16(out, s2 + 2) > 0 and u16(out, s2) > off:
            set_u16(out, s2, u16(out, s2) + growth)
    return bytes(out)


def replace_function_body(data, entry_index: int, func_tag: int, new_body: bytes) -> bytes:
    """Replace function ``func_tag``'s body in ``entry_index`` with ``new_body`` (any length).

    Fixes the intra-entry ``fpos`` of every LATER function (shifted by the size delta), the entry's
    declared size, and every later entry's table offset. A full-body replace needs no jump analysis
    (the old body -- and any jumps inside it -- is discarded, and functions never jump into each other).
    Used to re-author a battle eb's ``Main_Init`` (entry 0, tag 0) to ``InitObject`` one enemy-AI object
    per spawned slot, so the eb's AI binding matches an edited spawn composition.
    """
    b = bytearray(_as_bytes(data))
    slot = ENTRY_TABLE_OFF + entry_index * ENTRY_SLOT_SIZE
    off, sz = u16(b, slot), u16(b, slot + 2)
    if sz == 0:
        raise ValueError(f"entry {entry_index} is empty")
    es = ENTRY_TABLE_OFF + off
    fc = b[es + 1]
    fbase = es + 2
    funcs = [(u16(b, fbase + i * 4), u16(b, fbase + i * 4 + 2)) for i in range(fc)]   # (tag, fpos)
    idx = next((i for i, (t, _) in enumerate(funcs) if t == func_tag), None)
    if idx is None:
        raise ValueError(f"entry {entry_index} has no function tag {func_tag}")
    body_start = fbase + funcs[idx][1]
    body_end = (fbase + funcs[idx + 1][1]) if idx + 1 < fc else (es + sz)
    delta = len(new_body) - (body_end - body_start)
    out = bytearray(bytes(b[:body_start]) + bytes(new_body) + bytes(b[body_end:]))
    for i in range(idx + 1, fc):                          # later funcs' bodies shifted by delta
        set_u16(out, fbase + i * 4 + 2, funcs[i][1] + delta)
    set_u16(out, slot + 2, sz + delta)                    # entry's declared size
    for i in range(b[3]):                                 # later entries' table offsets
        if i == entry_index:
            continue
        s2 = ENTRY_TABLE_OFF + i * ENTRY_SLOT_SIZE
        if u16(out, s2 + 2) > 0 and u16(out, s2) > off:
            set_u16(out, s2, u16(out, s2) + delta)
    return bytes(out)


def insert_in_function(data, entry_index: int, func_tag: int, rel_off: int, ins: bytes) -> bytes:
    """Insert ``ins`` into function ``func_tag``'s body at body offset ``rel_off`` (0 = prepend).

    Unlike :func:`insert_bytes` (which only fixes the entry table), this ALSO fixes the intra-entry
    function-table ``fpos`` of every *other* function whose body starts at/after the insert point --
    the gap that makes a raw insert into a non-last function corrupt the later funcs. So that the
    function's own relative jumps stay valid, a MID-function insert point must not be straddled by any
    of ``func_tag``'s jumps (raised otherwise; a 0x06 jump table can't be analysed, so a mid-function
    insert into one is refused). Inserting right after a setup opcode and before the function's tail
    (e.g. after the player's ``DefinePlayerCharacter``, before its ``EnableMove`` block) is safe: every
    tail jump and its target shift together. Used to place the ladder re-entry spawn inside the player
    Init, exactly as field 706 does (no warm-up, no base-position flash).

    A **prepend** (``rel_off == 0``) is ALWAYS safe -- even on a function with a 0x06/0x0B scenario
    jump table -- because the engine is uniformly IP-relative: moving the whole body wholesale keeps
    every relative offset valid (both endpoints shift together), and nothing can sit between the new
    start and a later target. This is the ``[startup]``/``activate`` path, and it now works on the ~11%
    of fields whose Main_Init switches on the ScenarioCounter (e.g. the interactive-ATE hub field 206)."""
    eb = EbScript.from_bytes(data)
    f = eb.entry(entry_index).func_by_tag(func_tag)
    if f is None:
        raise ValueError(f"entry {entry_index} has no function tag {func_tag}")
    abs_ins = f.abs_start + rel_off
    if not (f.abs_start <= abs_ins < f.abs_end):
        raise ValueError(f"insert offset {rel_off} is outside func {func_tag} body")
    # A prepend at the function's very start (abs_ins == f.abs_start, i.e. rel_off == 0) can NEVER
    # be straddled by the function's own control flow: the engine is uniformly IP-relative
    # (``s1.ip += offset`` -- bra/beq/bne AND the 0x06/0x0B switch tables, EBin.cs), so moving the
    # whole body wholesale preserves every relative offset (both endpoints shift together). Only a
    # genuine MID-function insert can split a jump from its target, so the (best-effort) jump-safety
    # analysis is needed only then. This is what lets [startup]/activate prepend onto the ~11% of
    # fields whose Main_Init switches on the ScenarioCounter via a 0x06 jump table (e.g. field 206,
    # the interactive-ATE hub) -- exactly the case inject_startup's docstring already promises is safe.
    if abs_ins > f.abs_start:
        for j in eb.instrs(f):                              # the function's own relative jumps
            if j.op in (0x01, 0x02, 0x03) and not j.arg_is_expr[0]:
                raw = j.imm(0)
                tgt = j.end + (raw - 0x10000 if raw >= 0x8000 else raw)
                # The insert keeps a relative jump valid only if BOTH its endpoints shift by the same amount, i.e.
                # the jump and its target are on the same side of abs_ins (a boundary-aware test -- the old
                # `min<abs_ins<max` was blind to an endpoint landing EXACTLY on abs_ins, silently corrupting a jump
                # whose end or target coincides with the insert). The one exception is tgt == abs_ins: the jump then
                # lands on the FIRST inserted instruction, which (the fragment having no terminator) flows on into
                # the original target -- the intended "insert before instruction X" semantics for every path
                # reaching X, so it is allowed.
                if (j.off >= abs_ins) != (tgt >= abs_ins) and tgt != abs_ins:
                    raise ValueError(f"insert at {abs_ins} straddles jump {j.off}->{tgt} in func {func_tag}")
            elif j.op == 0x06:
                raise ValueError(f"func {func_tag} has a jump table (0x06); mid-function insert "
                                 f"unsupported (a prepend at the function start IS supported)")
    out = bytearray(insert_bytes(data, abs_ins, bytes(ins)))   # grows entry + later entries; fpos NOT fixed
    so = ENTRY_TABLE_OFF + entry_index * ENTRY_SLOT_SIZE
    es = ENTRY_TABLE_OFF + u16(out, so)
    fc = out[es + 1]
    fbase = es + 2
    for i in range(fc):
        t = u16(out, fbase + i * 4)
        fp = u16(out, fbase + i * 4 + 2)
        if t != func_tag and fbase + fp >= abs_ins:        # other funcs whose body shifted
            set_u16(out, fbase + i * 4 + 2, fp + len(ins))
    return bytes(out)


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


CINEMATIC_OP = 0x28   # Cinematic(...) -- FMV / opening-movie playback
FIELD_OP = 0x2B       # Field(dest) -- a field warp


def nop_cinematics(data, *, entry_index: int = 0, func_tag: int = 0, before_op: int = FIELD_OP):
    """NOP every ``Cinematic`` (``0x28``, FMV playback) instruction in a function, up to the first
    ``before_op`` (default the first ``Field()`` warp, ``0x2B``). Length-preserving: each op is overwritten
    in place with ``0x00`` NOPs (engine-confirmed "do nothing" -- ``DoEventCode`` case ``NOP``), so no offsets
    shift and no jumps need fixing. Returns ``(new_data, n_nopped)``.

    Used to strip the opening movie from an opening-field override (e.g. field 70 ``EVT_ALEX1_TS_OPENING``,
    which plays 2 cinematics before warping to a custom field) so a New Game lands in the target field
    *instantly* -- a pure-mod, engine-independent change. See memory ``project-ff9-new-game-entry``."""
    src = _as_bytes(data)
    eb = EbScript.from_bytes(src)
    entry = eb.entry(entry_index)
    func = entry.func_by_tag(func_tag) if entry is not None else None
    if func is None:
        return src, 0
    ins = list(eb.instrs(func))
    stop = next((x.off for x in ins if x.op == before_op), None)
    out, n = src, 0
    for i, x in enumerate(ins):
        if x.op == CINEMATIC_OP and (stop is None or x.off < stop):
            end = ins[i + 1].off if i + 1 < len(ins) else func.abs_end
            out = nop_range(out, x.off, end - x.off)
            n += 1
    return out, n


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


def activate(data, init_bytes: bytes, *, spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0) -> bytes:
    """Activate an appended entry from Main_Init with a 3-byte ``Init*`` call (``InitObject`` /
    ``InitRegion`` / ``InitCode``).

    Overwrites a Main_Init ``Wait(n)`` filler (shift-free) when one is free; otherwise INSERTS the
    call at the start of Main_Init. The blank field has only 2 Wait fillers, so a content-rich field
    (NPCs + gateways + events) overflows them -- the insert path lets any amount of content activate.
    The insert goes through :func:`insert_in_function` (the fpos-fixing insert), so it stays correct
    even when entry-0 has a REAL second function (a borrowed field's tag-1) and even across MANY
    sequential inserts -- the bug that previously left a 3rd+ region silently un-armed (raw
    ``insert_bytes`` left other funcs' ``fpos`` stale, corrupting the 2nd+ insertion). Within-budget
    fields hit the Wait path and stay byte-identical to before."""
    eb = EbScript.from_bytes(data)
    try:
        off = find_wait(eb, n=spawn_wait_n, occurrence=spawn_wait_occurrence)
    except ValueError:
        if eb.entry(0).func_by_tag(0) is None:
            raise ValueError("entry 0 has no Main_Init to activate from")
        return insert_in_function(data, 0, 0, 0, bytes(init_bytes))
    return patch_bytes(data, off, bytes(init_bytes), expect=bytes([WAIT_OP, 0x00, spawn_wait_n & 0xFF]))


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
