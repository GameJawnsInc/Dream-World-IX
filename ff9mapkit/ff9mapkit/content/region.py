"""General conditional region triggers + the field-script flag/expression primitives.

This is the kit's first *authored-logic* injector. Every other content module stamps a canned
block (an exit, an NPC, an encounter); this one builds a region whose ``_Range`` trigger runs a
flag-gated body you compose -- the reusable primitive behind multi-camera switch zones (see
:mod:`ff9mapkit.content.camera`) and, by the same shape, chests / story flags / one-shot events
(``if (!done) { give...; set done = 1 }``).

Everything here is grounded BYTE-FOR-BYTE in real FF9 field bytecode -- decoded from the camera
switch regions of Gargan Roo/Passage (``evt_gargan_gr_lef_0``) + the field-109 exit region. The
field event "expression" sub-language (opcode ``0x05``) is a little RPN stack terminated by ``0x7F``:

    push a variable :  <class> <idx>            class 0xD5 = GlobUInt8, 0xC5 = GlobBool
    push a constant :  0x7D <i16>
    operators       :  0x0E = logical NOT, 0x20 = '==', 0x2C = '=' (assign)
    end             :  0x7F

So ``set V = k``  -> ``05 <cls> <idx> 7D <k:i16> 2C 7F``
   ``if (V)``     -> ``05 <cls> <idx> 7F``            (truthy)
   ``if (!V)``    -> ``05 <cls> <idx> 0E 7F``
   ``if (V == k)``-> ``05 <cls> <idx> 7D <k:i16> 20 7F``

Control flow uses two relative jumps whose operand is the byte length of the block they skip:
``0x02`` = jump-if-FALSE (the ``if`` skip), ``0x03`` = jump-if-TRUE (used by ``ifnot``). A region
entry is engine type ``1`` with an Init func (tag 0 = ``SetRegion`` polygon) and a Range func
(tag 2 = the trigger body, which only runs while ``usercontrol == 1``).
"""

from __future__ import annotations

import struct

from ..eb import EbScript, edit, opcodes

# --- expression var classes (the engine's variable namespaces) ---
GLOB_UINT8 = 0xD5     # VAR_GlobUInt8_*  (persists across fields)
GLOB_BOOL = 0xC5      # VAR_GlobBool_*
VAR_CLASSES = {"glob_uint8": GLOB_UINT8, "glob_bool": GLOB_BOOL}

# --- expression opcodes / tokens ---
EXPR_OP = 0x05        # expression statement (its single operand is a token stream)
T_CONST = 0x7D        # 0x7D <i16>
T_NOT = 0x0E
T_EQ = 0x20
T_ASSIGN = 0x2C
T_END = 0x7F
JMP_FALSE = 0x02      # jump-if-false  02 <skip:i16>
JMP_TRUE = 0x03       # jump-if-true   03 <skip:i16>
SETREGION_OP = 0x29
REGION_ENTRY_TYPE = 1
RANGE_TAG = 2         # the player-in-region trigger func


def _cls(var_class) -> int:
    if isinstance(var_class, str):
        return VAR_CLASSES[var_class]
    return int(var_class) & 0xFF


def _i16(v: int) -> bytes:
    return struct.pack("<h", int(v))


# --- expression statements (opcode 0x05 + token stream) ---
def set_var(var_class, idx: int, value: int) -> bytes:
    """``set VAR = value`` -> ``05 <cls> <idx> 7D <value:i16> 2C 7F``."""
    return bytes([EXPR_OP, _cls(var_class), idx & 0xFF, T_CONST]) + _i16(value) + bytes([T_ASSIGN, T_END])


def cond_truthy(var_class, idx: int) -> bytes:
    """``if (VAR)`` condition expr -> ``05 <cls> <idx> 7F``."""
    return bytes([EXPR_OP, _cls(var_class), idx & 0xFF, T_END])


def cond_not(var_class, idx: int) -> bytes:
    """``if (!VAR)`` condition expr -> ``05 <cls> <idx> 0E 7F``."""
    return bytes([EXPR_OP, _cls(var_class), idx & 0xFF, T_NOT, T_END])


def cond_eq(var_class, idx: int, value: int) -> bytes:
    """``if (VAR == value)`` condition expr -> ``05 <cls> <idx> 7D <value:i16> 20 7F``."""
    return bytes([EXPR_OP, _cls(var_class), idx & 0xFF, T_CONST]) + _i16(value) + bytes([T_EQ, T_END])


# --- control flow ---
# 'ifnot (IsMovementEnabled) { return }' -- the verbatim region-trigger prologue (gates the body on
# usercontrol, exactly like every real exit/switch region). 7a 02 = IsMovementEnabled builtin.
MOVEMENT_GATE = bytes([EXPR_OP, 0x7A, 0x02, T_END, JMP_TRUE, 0x01, 0x00, opcodes.RETURN[0]])


def if_block(cond: bytes, body: bytes) -> bytes:
    """``if (cond) { body }`` -> cond + ``02 <len(body):i16>`` (jump-if-false past body) + body."""
    return cond + bytes([JMP_FALSE]) + _i16(len(body)) + body


def flag_gate(var_class, idx: int, *, require_set: bool = True) -> bytes:
    """A story-flag PROLOGUE: ``ifnot (flag matches) { return }``. Prepend it to a function so the
    function only proceeds when the flag is in the required state (the way real FF9 gates NPCs /
    triggers by scenario). ``require_set`` True -> proceed only when the flag is SET; False -> only
    when CLEAR. Same shape as :data:`MOVEMENT_GATE` (push flag, conditional jump over an early
    ``return``)."""
    cond = cond_truthy(var_class, idx)               # pushes the flag's truth
    jmp = JMP_TRUE if require_set else JMP_FALSE      # skip the 'return' when the flag is in-state
    return cond + bytes([jmp]) + _i16(1) + opcodes.RETURN


# --- region entry assembly ---
def set_region(points) -> bytes:
    """``SetRegion`` polygon op: ``29 00 <count> <(x,z) i16 pairs>``. 4 convex corners is the
    real-field norm (the engine's IsInQuad fans consecutive triplets; a convex quad is safe)."""
    pts = [tuple(p) for p in points]
    if len(pts) < 3:
        raise ValueError("a region needs at least 3 points")
    out = bytes([SETREGION_OP, 0x00, len(pts) & 0xFF])
    for x, z in pts:
        out += _i16(x) + _i16(z)
    return out


def build_region_entry(zone, range_body: bytes) -> bytes:
    """Assemble a type-1 region entry: Init (tag 0 = SetRegion(zone); return) + Range (tag 2 = body)."""
    init_body = set_region(zone) + opcodes.RETURN
    funcs = [(0, init_body), (RANGE_TAG, range_body)]
    table_len = len(funcs) * 4
    table = bytearray()
    pos = table_len
    for tag, body in funcs:
        table += struct.pack("<HH", tag, pos)
        pos += len(body)
    return bytes([REGION_ENTRY_TYPE, len(funcs)]) + bytes(table) + b"".join(b for _, b in funcs)


def prepend_range_gate(data, slot: int, gate_bytes: bytes) -> bytes:
    """Insert ``gate_bytes`` at the start of the region in ``slot``'s Range (tag 2) function, so the
    trigger only runs when the gate passes. Safe via :func:`edit.insert_bytes`: Range is the entry's
    LAST function, so the gate just becomes its first bytes and no func-table ``fpos`` needs fixing."""
    eb = EbScript.from_bytes(data)
    rng = eb.entry(slot).func_by_tag(RANGE_TAG)
    if rng is None:
        raise ValueError(f"entry {slot} has no Range (tag {RANGE_TAG}) to gate")
    if rng.abs_end != eb.entry(slot).abs_end:
        raise ValueError(f"Range is not the last function of entry {slot}; cannot prepend safely")
    return edit.insert_bytes(data, rng.abs_start, gate_bytes)


def inject_region(data, zone, range_body: bytes, *, slot: int | None = None, activate: bool = True,
                  spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0):
    """Append a conditional region (Init=SetRegion(zone), Range=range_body) into a free slot.

    Returns ``(new_bytes, slot)``. If ``activate`` (default), the region is turned on at field load
    by overwriting a Main_Init ``Wait(n)`` filler with ``InitRegion(slot, 0)`` -- shift-free. Pass
    ``activate=False`` for a zone that another zone enables at runtime (the switch-pair toggle)."""
    eb = EbScript.from_bytes(data)
    if slot is None:
        slot = eb.first_free_slot()
    entry = build_region_entry(zone, range_body)
    out = edit.append_entry(data, slot, entry)
    if activate:
        out = edit.activate(out, opcodes.init_region(slot, 0), spawn_wait_n=spawn_wait_n,
                            spawn_wait_occurrence=spawn_wait_occurrence)
    return out, slot
