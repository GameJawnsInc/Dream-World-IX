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
    # the entry table is u16-addressed and set_u16 MASKS (& 0xFFFF) — an
    # oversized file would otherwise register a silently-WRAPPED offset (a
    # black-screen generator now that long-jump relaxation permits huge bodies)
    if new_off > 0xFFFF:
        raise ValueError(
            f"entry slot {slot}: the file is too large — this entry would start at "
            f"table-relative offset {new_off} > 65535 (the .eb entry table is "
            f"u16-addressed; whole-file budget ≈ 64KB). Trim the biggest bodies.")
    if len(entry_bytes) > 0xFFFF:
        raise ValueError(f"entry slot {slot}: entry size {len(entry_bytes)} > 65535 "
                         f"(the entry-table size field is u16)")
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
    table_fixups = []                                       # (abs byte offset of a u16 reloffset, new value)
    if abs_ins > f.abs_start:
        from .disasm import decode_switch
        for j in eb.instrs(f):                              # the function's own relative jumps
            if j.op in (0x01, 0x02, 0x03) and not j.arg_is_expr[0]:
                raw = j.imm(0)
                if j.op == 0x02:                            # JMP_IFNOT: engine reads this UNSIGNED, forward-only
                    tgt = j.end + raw
                else:
                    tgt = j.end + (raw - 0x10000 if raw >= 0x8000 else raw)  # JMP / JMP_IF: signed int16
                # A jump whose endpoints sit on the SAME side of abs_ins shifts as a block (both or
                # neither move) -- valid untouched. tgt == abs_ins keeps the convergence semantics: the
                # jump lands on the FIRST inserted instruction and flows on into the original target
                # ("insert before instruction X" for every path reaching X) -- also untouched. A jump
                # STRADDLING the insert (endpoints on opposite sides, target not at the boundary) is
                # FIXED: exactly one endpoint shifts by len(ins), so the displacement grows by len(ins)
                # (forward: target shifted; backward: origin shifted -- same sign either way, since the
                # displacement's magnitude grows in both). The old code refused these; donor-field
                # patching (the Mognet letter-content splice) inserts into real functions whose head
                # guard legitimately jumps across the whole body.
                if (j.off >= abs_ins) != (tgt >= abs_ins) and tgt != abs_ins:
                    if j.op == 0x02:                        # unsigned forward-only
                        newraw = raw + len(ins)
                        if newraw > 0xFFFF:
                            raise ValueError(f"insert at {abs_ins}: fixed jump {j.off}->{tgt} "
                                             f"overflows the u16 displacement")
                    else:                                   # signed: forward grows +, backward grows -
                        disp = raw - 0x10000 if raw >= 0x8000 else raw
                        disp += len(ins) if tgt > abs_ins else -len(ins)
                        if not -0x8000 <= disp <= 0x7FFF:
                            raise ValueError(f"insert at {abs_ins}: fixed jump {j.off}->{tgt} "
                                             f"overflows the i16 displacement")
                        newraw = disp & 0xFFFF
                    # the displacement i16 sits at j.off+1 (jump ops carry no argflag byte); the site
                    # itself shifts when the jump's own origin is at/after the insert point
                    site = j.off + 1 + (len(ins) if j.off >= abs_ins else 0)
                    table_fixups.append((site, newraw))
            elif j.op in (0x06, 0x0B, 0x0D):
                # A jump TABLE straddled by the insert is FIXABLE (unlike an ordinary straddling jump,
                # which is refused above as ambiguous intent): every reloffset is unsigned forward-only
                # (engine EBin.cs; decode_switch is validated 100% boundary-aligned over all 5563
                # shipping switches), so a table whose anchor sits BEFORE the insert point simply grows
                # each reloffset whose target lands at/after it by len(ins). A target EXACTLY at
                # abs_ins keeps the ordinary-jump convergence semantics (it flows into the inserted
                # fragment first) and stays unchanged -- that is precisely how a guarded arm is
                # spliced into a switch's convergence point (the Mognet letter-content donor patch).
                info = decode_switch(j)
                if info is None:
                    raise ValueError(f"func {func_tag} has a jump table (op {j.op:#x}) with non-immediate "
                                     f"operands; mid-function insert unsupported")
                anchor = j.off + (4 if j.op == 0x06 else (2 if j.op == 0x0D else 1))
                if anchor >= abs_ins:
                    continue                                # whole table shifts as a block; offsets stay valid
                # operand k's u16 sits at j.off + 2 + 2k (flat 2-byte operands after op + count byte).
                # 0x06: reloffsets are operand 0 (default) + operands 2, 4, ... (each pair's second);
                # 0x0B/0x0D: operand 0 is the selector base -> reloffsets are operands 1..end.
                n_ops = len(j.args)
                rel_idx = ([0] + [2 + 2 * k for k in range((n_ops - 1) // 2)]) if j.op == 0x06 \
                    else list(range(1, n_ops))
                for k in rel_idx:
                    tgt = anchor + j.args[k]
                    if tgt > abs_ins:                       # target shifts, anchor doesn't -> grow the offset
                        table_fixups.append((j.off + 2 + 2 * k, j.args[k] + len(ins)))
    out = bytearray(insert_bytes(data, abs_ins, bytes(ins)))   # grows entry + later entries; fpos NOT fixed
    for off, val in table_fixups:                           # sites already adjusted for the shift where the
        set_u16(out, off, val)                              # owning instruction sits at/after abs_ins
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


# --------------------------------------------------------------------------- switch surgery

def find_switch(eb: EbScript, entry_index: int, func_tag: int, *, switch_base: int | None = None):
    """The first ``(func, instr, SwitchInfo)`` for a contiguous-range switch (0x0B/0x0D/0x06) in function
    ``func_tag`` of ``entry_index``, optionally filtered to ``switch_base`` (the lowest selector value of the
    0x0B/0x0D contiguous form). Raises if the function or a matching switch is absent."""
    from . import disasm as D
    f = eb.entry(entry_index).func_by_tag(func_tag)
    if f is None:
        raise ValueError(f"entry {entry_index} has no function tag {func_tag}")
    for ins in D.iter_code(eb.data, f.abs_start, f.abs_end):
        if ins.is_switch:
            si = D.decode_switch(ins)
            if si is not None and (switch_base is None or si.base == switch_base):
                return f, ins, si
    raise ValueError(f"entry {entry_index} func {func_tag} has no "
                     f"{'base-%d ' % switch_base if switch_base is not None else ''}switch")


def switch_case_reloff_pos(instr, si, case_value: int) -> int:
    """Absolute byte offset of the 2-byte little-endian reloffset for selector ``case_value`` in a decoded
    contiguous-range switch (``instr``/``si`` from :func:`find_switch`). The reloffset is an anchor-relative
    (anchor = ``off+1`` for 0x0B, ``off+2`` for 0x0D) forward jump; overwriting these two bytes repoints just
    that arm, length-preservingly. Layout: ``op | count | base | default | reloffset[0..n-1]`` -- the header
    is 2 bytes (0x0B) or 3 (0x0D), then 2-byte operands, so ``base`` is operand 0, ``default`` operand 1, and
    ``reloffset[k]`` (selector ``base+k``) operand ``2+k``. Raises for the explicit 0x06 form or an out-of-range
    case. (Cross-checked live vs WORLD09's base-2 switch @4033: case-53 reloffset at byte 4141.)"""
    if instr.op not in (0x0B, 0x0D):
        raise ValueError(f"switch reloffset patching supports only the contiguous form (0x0B/0x0D), not "
                         f"0x{instr.op:02X}")
    n = len(si.edges) - 1                                    # cases (edges minus the default arm)
    k = case_value - si.base
    if not 0 <= k < n:
        raise ValueError(f"case {case_value} out of the switch range [{si.base}..{si.base + n - 1}]")
    header = 3 if instr.op == 0x0D else 2                    # op(1) + count(1 or 2)
    return instr.off + header + 2 * (2 + k)                  # base=op0, default=op1, reloffset[k]=op(2+k)


def repoint_switch_case(data, entry_index: int, func_tag: int, case_value: int, handler: bytes,
                        *, switch_base: int | None = None):
    """Repoint a DEAD contiguous-switch arm to a freshly-appended handler, length-preservingly for the switch.

    Appends ``handler`` to the end of function ``func_tag`` (via :func:`replace_function_body`, so all later
    funcs/entries relocate correctly) and rewrites selector ``case_value``'s 2-byte reloffset to point at it.
    The arm MUST be DEAD -- its current target equal to the switch's ``default`` arm -- else this raises
    (repointing a LIVE case would break a real dispatch). The appended handler lands at the function's original
    ``abs_end`` (append-only: nothing before it shifts, so the switch + its reloffset table keep their offsets),
    so the new reloffset = ``handler_abs - anchor`` (anchor = ``off+1``/``off+2``) is a forward u16.

    Returns ``(new_bytes, info)`` where ``info`` = ``{handler_abs, anchor, reloff_pos, reloffset, switch_off}``.
    Round-trip identity (``EbScript.from_bytes(x).to_bytes() == x``) is asserted before returning."""
    eb = EbScript.from_bytes(data)
    f, ins, si = find_switch(eb, entry_index, func_tag, switch_base=switch_base)
    default_target = next(e.target for e in si.edges if e.is_default)
    edge = next((e for e in si.edges if e.value == case_value), None)
    if edge is None:
        raise ValueError(f"case {case_value} is not in the switch (base {si.base}, "
                         f"{len(si.edges) - 1} cases)")
    if edge.target != default_target:
        raise ValueError(f"case {case_value} is LIVE (arm -> {edge.target}, default {default_target}); "
                         f"refusing to repoint a mapped switch entrance")
    anchor = ins.off + (2 if ins.op == 0x0D else 1)
    reloff_pos = switch_case_reloff_pos(ins, si, case_value)
    handler_abs = f.abs_end                                  # append lands here (nothing earlier shifts)
    reloffset = handler_abs - anchor
    if not 0 < reloffset <= 0xFFFF:
        raise ValueError(f"handler reloffset {reloffset} out of the u16 forward-jump range")
    new_body = eb.data[f.abs_start:f.abs_end] + bytes(handler)
    out = replace_function_body(data, entry_index, func_tag, new_body)
    expect = eb.data[reloff_pos:reloff_pos + 2]              # the dead arm's old (== default) reloffset
    out = patch_bytes(out, reloff_pos, struct.pack("<H", reloffset), expect=expect)
    if EbScript.from_bytes(out).to_bytes() != out:
        raise ValueError("repoint_switch_case: round-trip identity broke after the surgery")
    return out, {"handler_abs": handler_abs, "anchor": anchor, "reloff_pos": reloff_pos,
                 "reloffset": reloffset, "switch_off": ins.off}


# --------------------------------------------------------------------------- locators

WAIT_OP = 0x22         # Wait(n) encodes as  22 00 nn  (op, argFlag=0, 1-byte count)
DEFINE_PC_OP = 0x2C    # DefinePlayerCharacter -- marks the player entry (activate after_player)
INIT_OBJECT_OP = 0x09  # InitObject(slot, arg) -- the player's Main_Init arming site


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


def _player_init_end(eb: EbScript):
    """Main_Init-relative offset just AFTER the player's arming ``InitObject`` -- the donor-convention
    insertion point for arming an INTERACTIVE entry (a region/object that handshakes with the player).
    None when it can't be located (no ``DefinePlayerCharacter`` entry, or Main_Init never ``InitObject``s
    it -- e.g. a verbatim donor Main that arms the player elsewhere)."""
    player_slot = None
    for e in eb.entries:                                  # the entry whose Init defines the player
        f = None if e.empty else e.func_by_tag(0)
        if f is not None and any(i.op == DEFINE_PC_OP for i in eb.instrs(f)):
            player_slot = e.index
            break
    if player_slot is None:
        return None
    main = eb.entry(0).func_by_tag(0)
    if main is None:
        return None
    for ins in eb.instrs(main):
        if ins.op == INIT_OBJECT_OP and ins.args and isinstance(ins.args[0], int) \
                and int(ins.args[0]) == player_slot:
            return ins.end - main.abs_start
    return None


def activate(data, init_bytes: bytes, *, spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0,
             after_player: bool = False) -> bytes:
    """Activate an appended entry from Main_Init with a 3-byte ``Init*`` call (``InitObject`` /
    ``InitRegion`` / ``InitCode``).

    Overwrites a Main_Init ``Wait(n)`` filler (shift-free) when one is free; otherwise INSERTS the
    call at the start of Main_Init. The blank field has only 2 Wait fillers, so a content-rich field
    (NPCs + gateways + events) overflows them -- the insert path lets any amount of content activate.
    The insert goes through :func:`insert_in_function` (the fpos-fixing insert), so it stays correct
    even when entry-0 has a REAL second function (a borrowed field's tag-1) and even across MANY
    sequential inserts -- the bug that previously left a 3rd+ region silently un-armed (raw
    ``insert_bytes`` left other funcs' ``fpos`` stale, corrupting the 2nd+ insertion). Within-budget
    fields hit the Wait path and stay byte-identical to before.

    ``after_player``: on the insert (overflow) path, place the ``Init*`` just AFTER the player's arming
    ``InitObject`` instead of at Main_Init's start. Creation order IS engine tick order, and for an entry
    that runs a synchronous player handshake (a door's ``RunScriptSync(player) -> SetWalkSpeed ->
    ExitField``) the donor convention *player first, regions after* is LOAD-BEARING: armed before the
    player, the door ticks first each frame, the handshake straddles a controller Update, and
    ``FieldMapActorController`` re-stamps ``actor.speed`` (60 while running) between the script's
    ``SetWalkSpeed(30)`` and ``ExitField``'s usercontrol=0 -- a sprint-entered exit then zooms at run
    speed into the walkmesh boundary instead of playing the stock walk-out. Falls back to the plain
    prepend when the player InitObject can't be found or the insert point is jump-straddled."""
    eb = EbScript.from_bytes(data)
    try:
        off = find_wait(eb, n=spawn_wait_n, occurrence=spawn_wait_occurrence)
    except ValueError:
        return activate_block(data, init_bytes, after_player=after_player)
    return patch_bytes(data, off, bytes(init_bytes), expect=bytes([WAIT_OP, 0x00, spawn_wait_n & 0xFF]))


def activate_block(data, block: bytes, *, after_player: bool = False) -> bytes:
    """Activate with an arbitrary-length Main_Init BLOCK -- always the fpos-fixing INSERT path (a
    multi-byte block cannot overwrite a 3-byte ``Wait`` filler). The lane for a GUARDED activation
    (:func:`ff9mapkit.content.region.guarded_call` around an ``InitObject`` -- the stock call-site
    story gate; see the OBJECT-INIT GATE LAW there). ``after_player`` as in :func:`activate`."""
    eb = EbScript.from_bytes(data)
    if eb.entry(0).func_by_tag(0) is None:
        raise ValueError("entry 0 has no Main_Init to activate from")
    if after_player:
        rel = _player_init_end(eb)
        if rel is not None:
            try:
                return insert_in_function(data, 0, 0, rel, bytes(block))
            except ValueError:
                pass                                       # jump-straddled insert point -> prepend fallback
    return insert_in_function(data, 0, 0, 0, bytes(block))


# --------------------------------------------------------------------------- jump safety (best effort)

# Engine truth (Memoria EBin.jumpToCommand): THREE relative jumps carry an i16 offset with
# target = instr.end + offset -- 0x01 JMP (unconditional, SIGNED offset: bra()), 0x02 JMP_IFNOT
# (conditional, UNSIGNED: beq() reads getUShortIP -> forward-only), 0x03 JMP_IF (conditional,
# SIGNED: bne()'s taken branch jumps via bra()). The condition rides the calc stack (pushed by a
# preceding 0x05 expression statement), not the instruction stream, so all three are 3-byte ops.
# (Until 2026-07-12 this scanned ONLY 0x03 and mislabeled it the unconditional jump.)
JMP_UNCOND_OP = 0x01
JMP_IFNOT_OP = 0x02
JMP_IF_OP = 0x03
_JUMP_OPS = (JMP_UNCOND_OP, JMP_IFNOT_OP, JMP_IF_OP)


def relative_jumps(eb: EbScript):
    """Every relative jump (unconditional 0x01 + conditional 0x02/0x03) as (src_off, src_end,
    target) tuples.

    Best effort: the recommended injection path (overwrite a Wait filler, or append an entry) is
    shift-free and needs no jump analysis; this helper is a safety net for the rarer case of
    inserting into a function with control flow.
    """
    out = []
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op in _JUMP_OPS and not ins.arg_is_expr[0]:
                    raw = ins.imm(0)
                    if raw is None:
                        continue
                    if ins.op == JMP_IFNOT_OP:
                        offset = raw                                      # beq: unsigned, forward-only
                    else:
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
